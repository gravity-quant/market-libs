"""ROADMAP SC-1 regression guard -- ``main_matriz.py`` MUST CONSUME the six
``MarketDataSnapshot`` alias properties at its two market-data probe sites, on BOTH of
its real surfaces, every dereference MUST sit inside the probe's own ``try`` **body**,
and the chain MUST cost ZERO additional HTTP calls.

Phase 37 / ``NOBJ-MTZ-02`` added six human-facing read-only aliases over
``MarketDataSnapshot``'s wire-named slots (``bids``, ``offers``, ``last``,
``settlement``, ``close``, ``open_interest``) -- the exact same six names the
``market-data-client`` analog declares over ``MarketDataEntries``, which is why
``_ALIAS_NAMES`` below is copied verbatim from
``test_main_market_data_deep_chain.py`` rather than re-typed. D-05 requires the driver
to SPEND that shape. A probe whose body reads
``ProbeResult(name, "PASS", f"entries={len(md)}")`` passes green while every link is
broken, because ``len()`` on a raw dict never touches a single alias. The only thing
that turns "the chain type-checks" into "the chain is exercised" is an actual
dereference at the site, and the only thing that keeps a later refactor from quietly
reverting the dereference to an entry count is this gate.

**"Both surfaces" for matriz means ``client.py`` + ``aio.py`` -- NOT REST + WebSocket.**
``39-CONTEXT.md`` justified D-05 by claiming ``matriz_client`` has no ``aio.py``. That
justification is stale and the plan's RESEARCH re-measured it against HEAD:
``packages/matriz-client/src/matriz_client/aio.py`` exists with a full ``AsyncClient``,
including ``get_market_data``, which returns an already-typed ``MarketDataSnapshot``;
``main_matriz.py`` already runs ~19 async probes; and the driver imports ``ws_client``
**zero** times. The DECISION D-05 (spend the six aliases on both surfaces) stands
unchanged -- only its rationale had expired. ``test_the_driver_never_imports_ws_client``
below exists so a future reader who finds the stale CONTEXT sentence cannot
"restore" a WebSocket path into this driver without reddening a test.

**Zero additional HTTP calls is the design, and it is asserted here.** The sync probe
builds the wrapper with ``MarketDataSnapshot.from_api`` over the ``marketData`` sub-dict
it ALREADY fetched -- the very payload
``matriz_client._core.parse_get_market_data_response`` feeds to the same constructor --
so it routes through the same walker, the same sink and the same strict-decode context
as the client's own parser, for free. The async probe gets its snapshot from
``AsyncClient.get_market_data``, which is already typed, so it needs no construction at
all. ``test_neither_probe_adds_an_http_call`` requires EXACTLY one request-issuing call
per probe: it stops a refactor from "fixing" the sync chain by calling the typed
endpoint a second time (which would double the request count for the market-data
concept and double divergence emission), and it simultaneously pins that the async
probe really does obtain its snapshot from the typed client call rather than
reconstructing one.

**Why the six dereferences cannot move the divergence count.** The aliases are
read-only ``@property`` views, and properties are invisible to
:func:`typing.get_type_hints` and to :func:`dataclasses.fields` (Phase 35 criterio 5,
D-16), hence invisible to ``_decode.walk_model``. Reaching one adds no decode path and
cannot fabricate a ``missing``. Spending them is pure observation.

Why the ``try`` matters: the D-09 never-FAILED contract says a probe degrades to a
FINDING and never crashes ``main_verify.py`` to FAILED. A dereference placed after the
exception ladder -- or inside an ``except`` / ``else`` / ``finally`` clause -- is NOT
covered by the probe's ladder, so a broken link would propagate uncaught and take the
whole ``matriz-client`` package to FAILED instead of degrading to a finding (T-39-22).
Only the ``try`` **body** counts here.

**Where this lock diverges from its two siblings, and why.** The market-data and
higyrus analogs both carry a ``_CHAINED_COLLECTIONS_BY_PROBE`` test, because each of
their probes fetches one or more *collections* of typed wrappers and a second
collection could be consumed by ``len()`` alone (WR-06). Matriz's market-data probes
fetch exactly ONE snapshot each -- there is no second collection to leave unexercised,
so that test has no subject here. It is replaced by
``test_every_alias_is_spent_in_every_probe``, which asserts the structural property
that actually is at risk for a single-object chain: that all six alias names appear at
least once in EACH probe, so a probe cannot reach its numeric floor by dereferencing
``last`` six times and leaving ``open_interest`` unexercised.

The driver is **parsed, never imported**: ``main_matriz.py`` has import-time side
effects (``load_dotenv`` and module-level constants read from the environment), and
every sibling driver lock in this directory parses for that reason.
"""

from __future__ import annotations

import ast
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DRIVER = "main_matriz.py"

# The six read-only ``@property`` aliases ``MarketDataSnapshot`` declares over its
# wire-named entry fields (Phase 37 / NOBJ-MTZ-02, D-16). Copied VERBATIM from
# ``test_main_market_data_deep_chain.py``: the two models expose the same six names, and
# re-typing the set is how the two locks would silently drift apart.
#
# ``OP`` / ``HI`` / ``LO`` / ``TV`` (and matriz's extra ``IV`` / ``EV`` / ``NV`` /
# ``ACP``) deliberately have NO alias -- they arrive as bare scalars rather than
# ``{price, size, date}`` entry objects (issue #102) -- so this set is exhaustive, not a
# subset someone forgot to finish.
_ALIAS_NAMES = frozenset({"bids", "offers", "last", "settlement", "close", "open_interest"})

# The two market-data probes, one per real surface. These names are a lock in their own
# right (LIVE-01 / REFAC-05: downstream findings are keyed on them), so a rename reddens
# here as well as at the probe-name gates.
_READ_PROBES = frozenset(
    {
        "probe_get_market_data",
        "probe_get_market_data_async",
    }
)

# The driver's own local name for the ``MarketDataSnapshot`` under test. Deliberately the
# SAME name on both surfaces so the lock is symmetric: an asymmetric pair of local names
# would need two chain roots and would let one surface drift out of the guard's sight.
_SNAPSHOT_LOCAL = "snapshot"

# Non-vacuity floor, PER PROBE: the six aliases, once each. Each probe holds exactly ONE
# snapshot, so the floor is the alias count itself.
#
# Phase 36 code review, WR-06 (inherited from the market-data analog): a single repo-wide
# aggregate can be met while ONE probe carries nothing -- 12 accesses spread 12/0
# satisfies the sum and leaves the async mirror entirely unexercised, which is precisely
# what the CLAUDE.md sync/async mirror rule exists to prevent.
_MIN_CHAINED_ACCESSES_BY_PROBE = {
    "probe_get_market_data": 6,
    "probe_get_market_data_async": 6,
}

# The aggregate, DERIVED rather than re-typed so the two numbers can never disagree.
_MIN_CHAINED_ACCESSES = sum(_MIN_CHAINED_ACCESSES_BY_PROBE.values())

# The typed constructor the SYNC chain is built on. CLAUDE.md: models are constructed
# EXCLUSIVELY via ``Model.from_api(payload)``, never ``Model(field=value)``. The ASYNC
# probe needs no constructor -- ``AsyncClient.get_market_data`` already returns the typed
# snapshot -- which is why this is asserted for the sync probe only.
_TYPED_CONSTRUCTOR = ("MarketDataSnapshot", "from_api")
_TYPED_CONSTRUCTOR_PROBES = frozenset({"probe_get_market_data"})

# Every callee in the driver that issues an HTTP request for the market-data concept: the
# sync raw-request helper plus the typed async client method. Each probe must contain
# EXACTLY ONE of these -- the one it already had.
_HTTP_CALL_NAMES = frozenset(
    {
        "_sync_matriz_request",
        "get_market_data",
    }
)
_HTTP_CALLS_PER_PROBE = 1

# The module whose absence from the driver's imports this lock pins. See the module
# docstring: the REST+WS reading of "both surfaces" is superseded, and no plan in this
# phase opens a WebSocket path (T-39-23).
_FORBIDDEN_IMPORT = "ws_client"


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


def _chain_rooted_at(node: ast.expr, name: str) -> bool:
    """True if the receiver chain under ``node`` bottoms out at the local ``name``.

    The sibling locks use ``_chain_reaches(node, attribute)`` because their chains pass
    through an intermediate ATTRIBUTE (``.market_data`` / ``.parking``). Matriz's six
    aliases hang directly off the snapshot, so the root of the chain is a bare
    ``ast.Name`` and an attribute-seeking walk would never match. ``Attribute``,
    ``Subscript`` and ``Call`` receivers are all walked through, so
    ``snapshot.bids[0].price`` and ``snapshot.last.price`` both resolve to ``snapshot``.
    """
    current: ast.expr | None = node
    while current is not None:
        if isinstance(current, ast.Name):
            return current.id == name
        if isinstance(current, ast.Attribute | ast.Subscript):
            current = current.value
        elif isinstance(current, ast.Call):
            current = current.func
        else:
            return False
    return False


def _probe_functions(tree: ast.Module) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    """Map probe name -> its function node, for the two market-data probes only."""
    found: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name in _READ_PROBES:
            found[node.name] = node
    return found


def _chained_accesses(
    func: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[ast.Attribute]:
    """Every ``snapshot.<alias>`` attribute node inside ``func``."""
    return [
        node
        for node in ast.walk(func)
        if isinstance(node, ast.Attribute)
        and node.attr in _ALIAS_NAMES
        and _chain_rooted_at(node.value, _SNAPSHOT_LOCAL)
    ]


def _typed_constructor_calls(func: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.Call]:
    """Every ``MarketDataSnapshot.from_api(...)`` call inside ``func``."""
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


def test_the_two_market_data_probes_are_present_by_name() -> None:
    """Probe-name stability (LIVE-01 / REFAC-05): a rename reddens this lock too."""
    found = _probe_functions(_driver_ast())

    missing = sorted(_READ_PROBES - set(found))
    assert not missing, (
        f"{_DRIVER}: market-data probe(s) {missing} not found by name. Probe names are "
        f"keyed by downstream findings (LIVE-01 / REFAC-05) and must not be renamed; if a "
        f"probe was genuinely retired, this lock and the findings ledger both need updating."
    )


def test_the_sync_probe_builds_the_snapshot_over_the_payload_in_hand() -> None:
    """D-05: the sync chain is built with ``MarketDataSnapshot.from_api``, not re-fetched.

    CLAUDE.md forbids ``Model(field=value)``; ``from_api`` is also what routes the
    construction through the shared walker and sink -- the same call
    ``_core.parse_get_market_data_response`` makes over the same ``marketData``
    sub-dict -- which is the whole reason the chain costs no extra request.
    """
    found = _probe_functions(_driver_ast())

    barren = sorted(
        name
        for name, func in found.items()
        if name in _TYPED_CONSTRUCTOR_PROBES and not _typed_constructor_calls(func)
    )
    assert not barren, (
        f"{_DRIVER}: sync market-data probe(s) {barren} never call "
        f"``{_TYPED_CONSTRUCTOR[0]}.{_TYPED_CONSTRUCTOR[1]}``. D-05 requires the typed "
        f"wrapper to be built on the ``marketData`` sub-dict the probe ALREADY fetched, "
        f"and CLAUDE.md requires models to be constructed exclusively via ``from_api``."
    )


def test_every_market_data_probe_consumes_the_alias_chain() -> None:
    """SC-1 / D-05: each market-data probe dereferences the snapshot aliases.

    Counting entries would pass while the chain was broken; only a real dereference
    exercises the ``MarketDataSnapshot -> MarketDataEntryValue / MarketDataLevel`` links.
    """
    found = _probe_functions(_driver_ast())

    barren = sorted(name for name, func in found.items() if not _chained_accesses(func))
    assert not barren, (
        f"{_DRIVER}: market-data probe(s) {barren} carry NO deep-chain access "
        f"(expected attributes from {sorted(_ALIAS_NAMES)} reached off the local "
        f"``{_SNAPSHOT_LOCAL}``). ROADMAP SC-1 requires the driver to EXERCISE the typed "
        f"chain at its real sites -- a probe that only reports ``entries={{len(md)}}`` "
        f"ships the whole alias surface unexercised while reporting PASS."
    )


def test_every_chained_access_sits_inside_the_probe_try_body() -> None:
    """D-09 never-FAILED contract (T-39-22): a broken link degrades to a FINDING."""
    found = _probe_functions(_driver_ast())

    unguarded: list[tuple[str, str, int]] = []
    for name, func in found.items():
        protected = _protected_node_ids(func)
        for node in _chained_accesses(func):
            if id(node) not in protected:
                unguarded.append((name, node.attr, node.lineno))

    assert not unguarded, (
        f"{_DRIVER}: deep-chain access(es) OUTSIDE a ``try`` body (D-09 / T-39-22 "
        f"violation) -- a broken link there would propagate uncaught, flip matriz-client "
        f"to FAILED and lose the whole run instead of degrading to a finding: {unguarded}"
    )


def test_the_deep_chain_lock_is_not_vacuous() -> None:
    """A thinned-out consumption must redden here rather than pass on a token access."""
    found = _probe_functions(_driver_ast())
    total = sum(len(_chained_accesses(func)) for func in found.values())

    assert total >= _MIN_CHAINED_ACCESSES, (
        f"{_DRIVER}: found only {total} deep-chain access(es) across the two market-data "
        f"probes (expected >= {_MIN_CHAINED_ACCESSES}, i.e. all six aliases once per "
        f"probe). The consumption was thinned out -- this guard is non-vacuous by design."
    )


def test_each_probe_meets_its_own_floor() -> None:
    """WR-06: the aggregate can be met while ONE probe carries nothing.

    12 accesses spread 12/0 satisfies the repo-wide sum and leaves the async mirror
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
        f"Each market-data probe holds ONE snapshot and must spend all six aliases off it."
    )


def test_every_alias_is_spent_in_every_probe() -> None:
    """The single-object analogue of the siblings' WR-06 collection test.

    The counting guards above are function-scoped and alias-blind, so a probe could reach
    its floor of six by dereferencing ``last`` six times while ``open_interest`` -- the
    alias whose wire field ``OI`` a closed segment is most likely to omit -- ships
    unexercised. Matriz's probes fetch ONE snapshot, not a collection, so the siblings'
    ``_CHAINED_COLLECTIONS_BY_PROBE`` test has no subject here; this asserts the property
    that actually is at risk instead. Decision recorded in the module docstring.
    """
    found = _probe_functions(_driver_ast())

    unspent: list[tuple[str, str]] = []
    for name, func in found.items():
        spent = {node.attr for node in _chained_accesses(func)}
        unspent.extend((name, alias) for alias in sorted(_ALIAS_NAMES - spent))

    assert not unspent, (
        f"{_DRIVER}: market-data probe(s) leave alias(es) unspent {unspent}. D-05 requires "
        f"ALL SIX aliases on BOTH surfaces -- a probe that spends one alias six times "
        f"reaches the numeric floor while shipping five decode paths unexercised."
    )


def test_the_driver_never_imports_ws_client() -> None:
    """T-39-23: no WebSocket path is opened by this phase, and none may be reintroduced.

    ``39-CONTEXT.md`` claims ``matriz_client`` has no ``aio.py`` and therefore that "both
    surfaces" must mean REST + WS. HEAD falsifies the premise: ``aio.py`` exists with a
    full ``AsyncClient`` and this driver already runs ~19 async probes. A future reader
    who finds only the stale sentence could "restore" the WS surface here; this reddens
    if they do. ``ws_client.py`` itself stays byte-identical in this phase.
    """
    tree = _driver_ast()

    offenders: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            offenders.extend(
                (alias.name, node.lineno) for alias in node.names if _FORBIDDEN_IMPORT in alias.name
            )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if _FORBIDDEN_IMPORT in module:
                offenders.append((module, node.lineno))
            offenders.extend(
                (f"{module}.{alias.name}", node.lineno)
                for alias in node.names
                if _FORBIDDEN_IMPORT in alias.name
            )

    assert not offenders, (
        f"{_DRIVER}: imports ``{_FORBIDDEN_IMPORT}`` at {offenders}. Phase 39 opens NO "
        f"WebSocket path: 'both surfaces' for matriz is ``client.py`` + ``aio.py``, "
        f"exactly as for iol and higyrus. See this module's docstring for the measurement "
        f"that superseded the REST+WS reading of D-05."
    )


def test_neither_probe_adds_an_http_call() -> None:
    """The load-bearing property: the six dereferences cost ZERO additional requests.

    Two failure modes at once. On the SYNC side, a refactor that "fixed" the chain by
    calling the typed endpoint a second time would double the request count for the
    market-data concept, double the divergence emission, and break the driver's
    one-call-per-probe-concept convention while every other test in this module stayed
    green -- so the sync probe keeps exactly the ``_sync_matriz_request`` it already had
    and builds the wrapper over the payload in hand. On the ASYNC side, requiring exactly
    one pins the opposite direction: the probe must actually obtain its snapshot from
    ``AsyncClient.get_market_data`` rather than reconstructing one from a raw payload it
    never fetched.
    """
    found = _probe_functions(_driver_ast())

    wrong = {
        name: _http_calls(func)
        for name, func in found.items()
        if len(_http_calls(func)) != _HTTP_CALLS_PER_PROBE
    }

    assert not wrong, (
        f"{_DRIVER}: market-data probe(s) do not issue EXACTLY "
        f"{_HTTP_CALLS_PER_PROBE} request-issuing call (name, lineno): {wrong}. Expected "
        f"callees: {sorted(_HTTP_CALL_NAMES)}. ``MarketDataSnapshot.from_api`` over the "
        f"payload already in hand routes through the same walker, the same sink and the "
        f"same strict-decode context as the client's own parser, so the sync chain costs "
        f"nothing; the async surface returns the typed snapshot directly."
    )
