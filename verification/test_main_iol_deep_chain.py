"""ROADMAP SC-1 regression guard -- ``main_iol.py`` MUST CONSUME the typed ``puntas``
chain at its real typed-probe sites, and every dereference MUST sit inside the probe's
own ``try``.

SC-1 has two halves. Phase 38 delivered the first: ``Cotizacion.puntas`` is a
``list[Punta]`` (NOBJ-02 collapse arm -- always a list, never ``None``) and
``Titulo.puntas`` is a **singular** ``Punta`` Null Object (declared without ``| None``,
so ``titulo.puntas.precioCompra`` never raises and the "did a book arrive?" question is
asked by truthiness, not by a ``None`` guard). This module locks the second half: the
driver that runs against the live IOL API has to SPEND that shape, not merely count rows.

Why a structural lock rather than a review note: a probe whose body reads
``ProbeResult(name, "PASS", f"len={len(rows)}")`` passes green while every link in the
chain is broken -- ``len()`` never touches ``puntas``. The only thing that turns "the
chain type-checks" into "the chain is exercised" is an actual dereference at the site,
and the only thing that keeps a later refactor from quietly reverting the dereference to
a row count is this gate. The per-probe floor is what makes the count a statement about
each site rather than about the file.

Why the ``try`` matters: the D-09 never-FAILED contract says a probe degrades to a
FINDING and never crashes ``main_verify.py`` to FAILED. A dereference placed after the
exception ladder -- or inside an ``except`` / ``else`` / ``finally`` clause -- is NOT
covered by the probe's ladder, so a broken link would propagate uncaught and take the
whole ``iol-client`` package to FAILED instead of degrading to a finding. Only the
``try`` **body** counts here.

**Do not "fix" ``_chain_reaches`` to handle only one shape.** The two IOL models spell
the same wire key differently (models.py D-02), so the chain has two legal forms:

- ``quote.puntas[0].precioCompra`` -- ``Cotizacion.puntas`` is a **list**, so the chain
  passes through an ``ast.Subscript``.
- ``titulo.puntas.precioCompra`` -- ``Titulo.puntas`` is a **singular** Null Object, so
  the chain is a direct attribute walk.

``_chain_reaches`` walks ``Attribute``, ``Subscript`` **and** ``Call`` receivers, so it
accepts both without modification. Narrowing it to ``Attribute`` alone would silently
stop seeing the two ``get_quote`` probes.

The driver is **parsed, never imported**: ``main_iol.py`` has import-time side effects
(``load_dotenv`` and module-level constants read from the environment), and every sibling
driver lock in this directory parses for that reason.
"""

from __future__ import annotations

import ast
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DRIVER = "main_iol.py"

# The ``Punta`` fields the driver's chain dereferences. ``Punta`` declares four decimal
# slots (``cantidadCompra``, ``cantidadVenta``, ``precioCompra``, ``precioVenta``);
# reaching one of these off a ``puntas`` receiver is what "consuming the chain" means
# concretely. Only the two the driver actually spends are listed -- widening this set
# would let a probe satisfy the floor with a field nobody reads.
_ALIAS_NAMES = frozenset({"precioCompra", "precioVenta"})

# The four typed probes that receive ``Cotizacion`` / ``list[Titulo]`` rows. These names
# are a lock in their own right (LIVE-01 / REFAC-05: downstream findings are keyed on
# them), so a rename reddens here as well as at the probe-name gates.
_READ_PROBES = frozenset(
    {
        "probe_get_quote_sync",
        "probe_get_quote_async",
        "probe_get_instruments_by_type_sync",
        "probe_get_instruments_by_type_async",
    }
)

# Non-vacuity floor, PER PROBE.
#
# The two ``get_quote`` probes hold a ``Cotizacion`` whose ``puntas`` is a **list** of
# order-book levels, so both sides of the top level are reachable and both are spent:
# ``precioCompra`` and ``precioVenta`` -> 2.
#
# The two ``get_instruments_by_type`` probes hold ``list[Titulo]``, whose ``puntas`` is
# the **singular** Null Object: one bid price off the book of each row -> 1.
#
# Phase 36 code review, WR-06 (inherited from the market-data analog): a single repo-wide
# aggregate can be met while ONE probe carries almost nothing -- 6 accesses spread 5/1/0/0
# satisfies a sum and leaves two probes entirely unexercised. The per-probe floor is what
# closes that.
_MIN_CHAINED_ACCESSES_BY_PROBE = {
    "probe_get_quote_sync": 2,
    "probe_get_quote_async": 2,
    "probe_get_instruments_by_type_sync": 1,
    "probe_get_instruments_by_type_async": 1,
}

# The aggregate, DERIVED rather than re-typed so the two numbers can never disagree.
_MIN_CHAINED_ACCESSES = sum(_MIN_CHAINED_ACCESSES_BY_PROBE.values())

# Which fetched collections each probe must chain over, by the driver's own local name.
#
# The ``get_instruments_by_type`` probes fetch ``wrapper_result`` (``list[Titulo]``) and
# must carry a comprehension over it that dereferences the singular ``Punta`` -- a
# collection consumed by ``len()`` alone ships its whole decode path unexercised while
# the probe still reports PASS (WR-06).
#
# The ``get_quote`` probes are deliberately EMPTY here: what they fetch is a single
# ``Cotizacion``, and the collection they walk (``quote.puntas``) is reached by subscript
# off the model, not by iterating a local ``Name``. Their coverage is asserted by the
# per-probe floor above, not by this structural test. Adding a name here that the probe
# never binds would make the test unfalsifiable-red rather than meaningful.
_CHAINED_COLLECTIONS_BY_PROBE: dict[str, set[str]] = {
    "probe_get_quote_sync": set(),
    "probe_get_quote_async": set(),
    "probe_get_instruments_by_type_sync": {"wrapper_result"},
    "probe_get_instruments_by_type_async": {"wrapper_result"},
}


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

    Walks ``Attribute``, ``Subscript`` and ``Call`` receivers so that BOTH legal shapes
    of the IOL chain are accepted -- see the module docstring before narrowing this.
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
    """Map probe name -> its function node, for the four typed probes only."""
    found: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name in _READ_PROBES:
            found[node.name] = node
    return found


def _chained_accesses(
    func: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[ast.Attribute]:
    """Every ``<...>.puntas<...>.<alias>`` attribute node inside ``func``."""
    return [
        node
        for node in ast.walk(func)
        if isinstance(node, ast.Attribute)
        and node.attr in _ALIAS_NAMES
        and _chain_reaches(node.value, "puntas")
    ]


def _driver_ast() -> ast.Module:
    return ast.parse((_REPO_ROOT / _DRIVER).read_text(encoding="utf-8"))


def test_the_four_typed_probes_are_present_by_name() -> None:
    """Probe-name stability (LIVE-01 / REFAC-05): a rename reddens this lock too."""
    found = _probe_functions(_driver_ast())

    missing = sorted(_READ_PROBES - set(found))
    assert not missing, (
        f"{_DRIVER}: typed probe(s) {missing} not found by name. Probe names are keyed by "
        f"downstream findings (LIVE-01 / REFAC-05) and must not be renamed; if a probe was "
        f"genuinely retired, this lock and the findings ledger both need updating."
    )


def test_every_typed_probe_consumes_the_puntas_chain() -> None:
    """SC-1: each typed probe dereferences ``puntas`` down to a ``Punta`` field.

    Counting rows would pass while the chain was broken; only a real dereference
    exercises the ``Cotizacion.puntas`` list / ``Titulo.puntas`` Null Object links that
    Phase 38 introduced.
    """
    found = _probe_functions(_driver_ast())

    barren = sorted(name for name, func in found.items() if not _chained_accesses(func))
    assert not barren, (
        f"{_DRIVER}: typed probe(s) {barren} carry NO deep-chain access "
        f"(expected at least one attribute reached through ``puntas`` and one of "
        f"{sorted(_ALIAS_NAMES)}). ROADMAP SC-1 requires the driver to EXERCISE the typed "
        f"chain at its real sites -- a probe that only counts rows would ship a broken link. "
        f"Both shapes count: ``quote.puntas[0].precioCompra`` (list) and "
        f"``titulo.puntas.precioCompra`` (singular Null Object)."
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
        f"{_DRIVER}: deep-chain access(es) OUTSIDE a ``try`` body (D-09 violation) -- a "
        f"broken link there would propagate uncaught, flip iol-client to FAILED and lose "
        f"the whole run instead of degrading to a finding: {unguarded}"
    )


def test_the_deep_chain_lock_is_not_vacuous() -> None:
    """A thinned-out consumption must redden here rather than pass on a token access."""
    found = _probe_functions(_driver_ast())
    total = sum(len(_chained_accesses(func)) for func in found.values())

    assert total >= _MIN_CHAINED_ACCESSES, (
        f"{_DRIVER}: found only {total} deep-chain access(es) across the four typed probes "
        f"(expected >= {_MIN_CHAINED_ACCESSES}: both sides of the book in each ``get_quote`` "
        f"probe, one bid off the singular ``Punta`` in each ``get_instruments_by_type`` "
        f"probe). The consumption was thinned out -- this guard is non-vacuous by design."
    )


def test_each_probe_meets_its_own_floor() -> None:
    """WR-06: the aggregate can be met while ONE probe carries almost nothing.

    6 accesses spread 5/1/0/0 satisfies the repo-wide sum and leaves two probes
    effectively unexercised. The per-probe floor is what makes the count a
    statement about each site.
    """
    found = _probe_functions(_driver_ast())

    short = {
        name: (len(_chained_accesses(func)), _MIN_CHAINED_ACCESSES_BY_PROBE[name])
        for name, func in found.items()
        if len(_chained_accesses(func)) < _MIN_CHAINED_ACCESSES_BY_PROBE[name]
    }

    assert not short, (
        f"{_DRIVER}: probe(s) below their own deep-chain floor (got, expected): {short}. "
        f"A ``get_quote`` probe is held to 2 because ``Cotizacion.puntas`` is a LIST of "
        f"order-book levels and both sides of the top level are reachable; an "
        f"``get_instruments_by_type`` probe is held to 1 because ``Titulo.puntas`` is a "
        f"SINGULAR ``Punta`` Null Object."
    )


def test_every_fetched_titulo_collection_is_chained() -> None:
    """WR-06: a fetched ``list[Titulo]`` may not be consumed by ``len()`` alone.

    The counting guards above are function-scoped, so a probe that fetches a
    collection and chains only a scalar still reaches its numeric floor. This
    asserts the structural fact instead: for EVERY collection named in
    ``_CHAINED_COLLECTIONS_BY_PROBE``, some comprehension iterating it must carry a
    ``puntas.<alias>`` dereference.
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
                and _chain_reaches(node.value, "puntas")
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
        f"{_DRIVER}: fetched ``list[Titulo]`` collection(s) with NO deep-chain access "
        f"{unchained}. A collection consumed by ``len()`` alone ships its whole decode path "
        f"unexercised while the probe still reports PASS -- WR-06, the exact defect this "
        f"module's docstring describes, one level up from a single probe."
    )
