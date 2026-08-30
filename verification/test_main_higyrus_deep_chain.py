"""ROADMAP SC-1 regression guard -- ``main_higyrus.py`` MUST CONSUME the typed
``Posicion.parking`` chain at its two ``get_posiciones`` probe sites, every dereference
MUST sit inside the probe's own ``try`` **body**, and the chain MUST cost ZERO additional
HTTP calls.

D-04 states the asymmetry this module closes. The higyrus probes work almost entirely on
raw dicts obtained through ``_raw_request_sync`` / ``_raw_request_async``, so the typed
surface runs silently and no ``.model.field`` chain is ever walked -- unlike iol, matriz
and market-data, each of which already spends one. A probe whose body reads
``ProbeResult(name, "PASS", f"{len(raw)} items")`` passes green while every link in
``Posicion -> list[Parking] -> diasParking`` is broken, because ``len()`` never touches
``parking``. The only thing that turns "the chain type-checks" into "the chain is
exercised" is an actual dereference at the site, and the only thing that keeps a later
refactor from quietly reverting the dereference to a row count is this gate.

**Zero additional HTTP calls is the design, and it is asserted here.**
``SafeModel.from_api(payload)`` routes through the *same* walker
(``higyrus_client._decode.walk_model``), the *same* sink (``_decode.current_sink()``) and
the *same* emission path the client's own parser uses, and it inherits the strict-decode
``ContextVar`` bound inside ``Client._request`` -- which is deliberately never reset, so a
typed construction performed **after** the request and in the same context still sees
strict mode. Building the wrapper over the payload already in hand therefore emits exactly
the divergence records the typed function would have emitted, for free. That is what lets
this chain respect the driver's "one HTTP call per probe concept" convention without
loosening anything, and ``test_the_typed_chain_adds_no_http_call`` below is what stops a
future refactor from "fixing" the chain by adding a second call to the typed endpoint.

Why the ``try`` matters: the D-09 never-FAILED contract says a probe degrades to a FINDING
and never crashes ``main_verify.py`` to FAILED. A dereference placed after the exception
ladder -- or inside an ``except`` / ``else`` / ``finally`` clause -- is NOT covered by the
probe's ladder, so a broken link would propagate uncaught and take the whole
``higyrus-client`` package to FAILED instead of degrading to a finding. Only the ``try``
**body** counts here.

**The live half of higyrus is blocked.** The vendor host does not resolve by DNS (measured
in the Phase 39 research session; the inherited blocker ``LIVE-HIGY-33`` is still standing),
so a live run cannot produce a populated ``parking`` branch. Two further facts compound
that: the probes send ``incluirParking=False`` and plan 39-05 deliberately does NOT flip it
(flipping would change the response shape and burn the write-once schema baseline for
``get_posiciones`` through schema drift). Consequently **this structural lock plus the
mocked suite of plan 39-02** (``packages/higyrus-client/tests/test_deep_chain_edges.py``,
which pins the populated-``parking`` semantics a live run cannot reach) are the falsifiable
evidence of the chain in this phase. The census of plan 39-08 must record that as a
measured coverage limitation, not as an implementation detail.

The driver is **parsed, never imported**: ``main_higyrus.py`` has import-time side effects
(``load_dotenv`` and module-level constants read from the environment), and every sibling
driver lock in this directory parses for that reason.
"""

from __future__ import annotations

import ast
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DRIVER = "main_higyrus.py"

# The ``Parking`` field the driver's chain dereferences. ``Parking`` declares four slots
# (``monedaPosicion``, ``diasParking``, ``cantidadLiquidada``, ``observacion``); only the
# one the driver actually spends is listed. Widening this set -- the 39-04 decision,
# inherited verbatim -- would let a probe satisfy the floor below by reaching a field
# nobody reads.
_ALIAS_NAMES = frozenset({"diasParking"})

# The two ``get_posiciones`` probes. These names are a lock in their own right
# (LIVE-01 / REFAC-05: downstream findings are keyed on them), so a rename reddens here as
# well as at the probe-name gates.
_READ_PROBES = frozenset(
    {
        "probe_get_posiciones_sync",
        "probe_get_posiciones_async",
    }
)

# Non-vacuity floor, PER PROBE. Each probe holds ONE fetched collection of position rows
# and spends ONE ``parking`` leaf off it: the ``diasParking`` of the first entry of the
# first row that carries a parking list.
#
# Phase 36 code review, WR-06 (inherited from the market-data analog): a single repo-wide
# aggregate can be met while ONE probe carries nothing -- 2 accesses spread 2/0 satisfies
# a sum and leaves the async mirror entirely unexercised, which is precisely the failure
# the CLAUDE.md sync/async mirror rule exists to prevent.
_MIN_CHAINED_ACCESSES_BY_PROBE = {
    "probe_get_posiciones_sync": 1,
    "probe_get_posiciones_async": 1,
}

# The aggregate, DERIVED rather than re-typed so the two numbers can never disagree.
_MIN_CHAINED_ACCESSES = sum(_MIN_CHAINED_ACCESSES_BY_PROBE.values())

# Which local collection of typed wrappers each probe must chain over, by the driver's own
# local name. A ``list[Posicion]`` consumed by ``len()`` alone ships its whole decode path
# unexercised while the probe still reports PASS (WR-06), so a comprehension iterating this
# name has to carry the ``parking.<alias>`` dereference.
_CHAINED_COLLECTIONS_BY_PROBE: dict[str, set[str]] = {
    "probe_get_posiciones_sync": {"posiciones"},
    "probe_get_posiciones_async": {"posiciones"},
}

# The typed constructor the chain is built on. CLAUDE.md: models are constructed
# EXCLUSIVELY via ``Model.from_api(payload)``, never ``Model(field=value)``.
_TYPED_CONSTRUCTOR = ("Posicion", "from_api")

# Every callee in the driver that issues an HTTP request for the positions concept: the two
# raw-request helpers plus the typed client method. Each probe may contain EXACTLY ONE of
# these -- the one it already had. This is the "zero additional HTTP calls" property that
# makes ``Posicion.from_api`` over the payload in hand the right design rather than a second
# round trip through the typed endpoint.
_HTTP_CALL_NAMES = frozenset(
    {
        "_raw_request_sync",
        "_raw_request_async",
        "get_posiciones",
    }
)
_MAX_HTTP_CALLS_PER_PROBE = 1


def _protected_node_ids(func: ast.FunctionDef | ast.AsyncFunctionDef) -> set[int]:
    """Return ids of every node reachable from the ``body`` of some ``try`` in ``func``.

    Only the protected ``try`` body counts -- nodes in ``except`` / ``else`` /
    ``finally`` are deliberately excluded, since a failure there is not caught by the
    probe's D-09 exception ladder.
    """
    protected: set[int] = set()
    for node in ast.walk(func):
        if isinstance(node, ast.Try):
            for stmt in node.body:
                for descendant in ast.walk(stmt):
                    protected.add(id(descendant))
    return protected


def _chain_reaches(node: ast.expr, attribute: str) -> bool:
    """True if the receiver chain under ``node`` passes through ``.<attribute>``.

    Walks ``Attribute``, ``Subscript`` and ``Call`` receivers, so the higyrus chain
    ``posicion.parking[0].diasParking`` -- which passes through a ``Subscript`` because
    ``Posicion.parking`` is a ``list[Parking]`` -- is accepted. Narrowing this to
    ``Attribute`` alone would silently stop seeing both probes.
    """
    current: ast.expr | None = node
    while current is not None:
        if isinstance(current, ast.Attribute):
            if current.attr == attribute:
                return True
            current = current.value
        elif isinstance(current, ast.Subscript):
            current = current.value
        elif isinstance(current, ast.Call):
            current = current.func
        else:
            return False
    return False


def _probe_functions(tree: ast.Module) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    """Map probe name -> its function node, for the two positions probes only."""
    found: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name in _READ_PROBES:
            found[node.name] = node
    return found


def _chained_accesses(
    func: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[ast.Attribute]:
    """Every ``<...>.parking<...>.<alias>`` attribute node inside ``func``."""
    return [
        node
        for node in ast.walk(func)
        if isinstance(node, ast.Attribute)
        and node.attr in _ALIAS_NAMES
        and _chain_reaches(node.value, "parking")
    ]


def _typed_constructor_calls(func: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.Call]:
    """Every ``Posicion.from_api(...)`` call inside ``func``."""
    owner, method = _TYPED_CONSTRUCTOR
    return [
        node
        for node in ast.walk(func)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == method
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == owner
    ]


def _http_calls(func: ast.FunctionDef | ast.AsyncFunctionDef) -> list[tuple[str, int]]:
    """Every call inside ``func`` whose callee name issues an HTTP request."""
    calls: list[tuple[str, int]] = []
    for node in ast.walk(func):
        if not isinstance(node, ast.Call):
            continue
        callee = node.func
        name = (
            callee.id
            if isinstance(callee, ast.Name)
            else callee.attr
            if isinstance(callee, ast.Attribute)
            else None
        )
        if name in _HTTP_CALL_NAMES:
            calls.append((str(name), node.lineno))
    return calls


def _driver_ast() -> ast.Module:
    return ast.parse((_REPO_ROOT / _DRIVER).read_text(encoding="utf-8"))


def test_the_two_positions_probes_are_present_by_name() -> None:
    """Probe-name stability (LIVE-01 / REFAC-05): a rename reddens this lock too."""
    found = _probe_functions(_driver_ast())

    missing = sorted(_READ_PROBES - set(found))
    assert not missing, (
        f"{_DRIVER}: positions probe(s) {missing} not found by name. Probe names are keyed "
        f"by downstream findings (LIVE-01 / REFAC-05) and must not be renamed; if a probe "
        f"was genuinely retired, this lock and the findings ledger both need updating."
    )


def test_every_positions_probe_builds_the_typed_wrapper() -> None:
    """D-04: the chain is built with ``Posicion.from_api`` over the payload in hand.

    CLAUDE.md forbids ``Model(field=value)``; ``from_api`` is also what routes the
    construction through the shared walker and sink, which is the whole reason the chain
    is free of an extra request.
    """
    found = _probe_functions(_driver_ast())

    barren = sorted(name for name, func in found.items() if not _typed_constructor_calls(func))
    assert not barren, (
        f"{_DRIVER}: positions probe(s) {barren} never call ``Posicion.from_api``. D-04 "
        f"requires the typed wrapper to be built on the payload the probe ALREADY fetched, "
        f"and CLAUDE.md requires models to be constructed exclusively via ``from_api``."
    )


def test_every_positions_probe_consumes_the_parking_chain() -> None:
    """SC-1: each positions probe dereferences ``parking`` down to a ``Parking`` field.

    Counting rows would pass while the chain was broken; only a real dereference
    exercises the ``Posicion -> list[Parking] -> diasParking`` links.
    """
    found = _probe_functions(_driver_ast())

    barren = sorted(name for name, func in found.items() if not _chained_accesses(func))
    assert not barren, (
        f"{_DRIVER}: positions probe(s) {barren} carry NO deep-chain access "
        f"(expected at least one attribute reached through ``parking`` and one of "
        f"{sorted(_ALIAS_NAMES)}). ROADMAP SC-1 requires the driver to EXERCISE the typed "
        f"chain at its real sites -- a probe that only counts rows with ``len(raw)`` would "
        f"ship the whole ``Parking`` decode path unexercised while reporting PASS."
    )


def test_every_chained_access_sits_inside_the_probe_try_body() -> None:
    """D-09 never-FAILED contract: a broken link degrades to a FINDING, never a crash."""
    found = _probe_functions(_driver_ast())

    unguarded: list[tuple[str, str, int]] = []
    for name, func in found.items():
        protected = _protected_node_ids(func)
        for node in _chained_accesses(func):
            if id(node) not in protected:
                unguarded.append((name, node.attr, node.lineno))

    assert not unguarded, (
        f"{_DRIVER}: deep-chain access(es) OUTSIDE a ``try`` body (D-09 / T-39-16 "
        f"violation) -- a broken link there would propagate uncaught, flip higyrus-client "
        f"to FAILED and lose the whole run instead of degrading to a finding: {unguarded}"
    )


def test_the_deep_chain_lock_is_not_vacuous() -> None:
    """A thinned-out consumption must redden here rather than pass on a token access."""
    found = _probe_functions(_driver_ast())
    total = sum(len(_chained_accesses(func)) for func in found.values())

    assert total >= _MIN_CHAINED_ACCESSES, (
        f"{_DRIVER}: found only {total} deep-chain access(es) across the two positions "
        f"probes (expected >= {_MIN_CHAINED_ACCESSES}: one ``parking`` leaf per probe). "
        f"The consumption was thinned out -- this guard is non-vacuous by design."
    )


def test_each_probe_meets_its_own_floor() -> None:
    """WR-06: the aggregate can be met while ONE probe carries nothing.

    2 accesses spread 2/0 satisfies the repo-wide sum and leaves the async mirror
    entirely unexercised -- exactly what the CLAUDE.md sync/async mirror rule forbids.
    The per-probe floor is what makes the count a statement about each site.
    """
    found = _probe_functions(_driver_ast())

    short = {
        name: (len(_chained_accesses(func)), _MIN_CHAINED_ACCESSES_BY_PROBE[name])
        for name, func in found.items()
        if len(_chained_accesses(func)) < _MIN_CHAINED_ACCESSES_BY_PROBE[name]
    }

    assert not short, (
        f"{_DRIVER}: probe(s) below their own deep-chain floor (got, expected): {short}. "
        f"Each positions probe holds ONE fetched collection of rows and must spend ONE "
        f"``parking`` leaf off it."
    )


def test_every_fetched_position_collection_is_chained() -> None:
    """WR-06: a fetched ``list[Posicion]`` may not be consumed by ``len()`` alone.

    The counting guards above are function-scoped, so a probe that fetches a collection
    and chains only a scalar still reaches its numeric floor. This asserts the structural
    fact instead: for EVERY collection named in ``_CHAINED_COLLECTIONS_BY_PROBE``, some
    comprehension iterating it must carry a ``parking.<alias>`` dereference.
    """
    found = _probe_functions(_driver_ast())

    unchained: list[tuple[str, str]] = []
    for name, func in found.items():
        chained_over: set[str] = set()
        for comp in ast.walk(func):
            if not isinstance(comp, ast.ListComp | ast.SetComp | ast.GeneratorExp):
                continue
            if not any(
                isinstance(node, ast.Attribute)
                and node.attr in _ALIAS_NAMES
                and _chain_reaches(node.value, "parking")
                for node in ast.walk(comp)
            ):
                continue
            for generator in comp.generators:
                if isinstance(generator.iter, ast.Name):
                    chained_over.add(generator.iter.id)
        unchained.extend(
            (name, collection)
            for collection in sorted(_CHAINED_COLLECTIONS_BY_PROBE[name] - chained_over)
        )

    assert not unchained, (
        f"{_DRIVER}: fetched ``list[Posicion]`` collection(s) with NO deep-chain access "
        f"{unchained}. A collection consumed by ``len()`` alone ships its whole decode path "
        f"unexercised while the probe still reports PASS -- WR-06, the exact defect this "
        f"module's docstring describes, one level up from a single probe."
    )


def test_the_typed_chain_adds_no_http_call() -> None:
    """D-04's load-bearing property: the typed chain costs ZERO additional requests.

    This is the test that makes ``Posicion.from_api`` over the payload already in hand the
    RIGHT design rather than a convenience. The driver's convention is one HTTP call per
    probe concept; a refactor that "fixed" the chain by calling the typed endpoint a second
    time would double the request count for the positions concept, double the divergence
    emission, and quietly break that convention while every other test in this module
    stayed green. Each probe therefore keeps EXACTLY the one request-issuing call it
    already had.
    """
    found = _probe_functions(_driver_ast())

    excess = {
        name: _http_calls(func)
        for name, func in found.items()
        if len(_http_calls(func)) > _MAX_HTTP_CALLS_PER_PROBE
    }

    assert not excess, (
        f"{_DRIVER}: positions probe(s) issue MORE than {_MAX_HTTP_CALLS_PER_PROBE} "
        f"request-issuing call (name, lineno): {excess}. The typed chain must be built on "
        f"the payload the probe ALREADY fetched -- ``SafeModel.from_api`` routes through "
        f"the same walker, the same sink and the same strict-decode context as the "
        f"client's own parser, so it costs nothing. Calling {sorted(_HTTP_CALL_NAMES)} a "
        f"second time would break the driver's one-call-per-probe-concept convention."
    )
