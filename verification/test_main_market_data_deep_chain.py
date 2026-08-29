"""ROADMAP SC-5 regression guard -- ``main_market_data.py`` MUST CONSUME the typed
``market_data`` chain at its real read-probe sites, and every dereference MUST sit
inside the probe's own ``try``.

SC-5 has two halves. Plan 36-02 delivered the first: ``MarketDataSnapshot.market_data``
is a ``MarketDataEntries`` Null Object carrying ``BookLevel`` / ``EntryValue`` children
plus six read-only aliases (``bids``, ``offers``, ``last``, ``settlement``, ``close``,
``open_interest``), and the mapping machinery is gone without moving the ``_decode.py``
digest. This module locks the second half: the driver that will run against develop in
Phase 39 has to SPEND that shape, not merely count rows.

Why a structural lock rather than a review note: a probe whose body reads
``ProbeResult(name, "PASS", f"snapshots={len(snapshots)}")`` passes green while every
link in the chain is broken -- ``len()`` never touches ``market_data``. The only thing
that turns "the chain type-checks" into "the chain is exercised" is an actual
dereference at the site, and the only thing that keeps a later refactor from quietly
reverting the dereference to a row count is this gate.

Why the ``try`` matters: the D-09 never-FAILED contract says a probe degrades to a
FINDING and never crashes ``main_verify.py`` to FAILED. A dereference placed after the
``except`` -- or inside an ``except`` / ``else`` / ``finally`` clause -- is NOT covered
by the probe's exception ladder, so a broken link would propagate uncaught. Only the
``try`` **body** counts here, for exactly the reason
``test_main_market_data_postprocess_guarded.py`` states for its own helpers.

The driver is **parsed, never imported**: ``main_market_data.py`` has import-time side
effects (it reads the environment and builds module-level constants), and every sibling
driver lock in this directory parses for that reason.
"""

from __future__ import annotations

import ast
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DRIVER = "main_market_data.py"

# The six read-only ``@property`` aliases ``MarketDataEntries`` declares over its
# wire-named slots (Plan 36-02). Reaching one of these off a ``market_data`` attribute
# is what "consuming the chain" means concretely.
_ALIAS_NAMES = frozenset({"bids", "offers", "last", "settlement", "close", "open_interest"})

# The four read probes that receive ``MarketDataSnapshot`` rows. These names are a lock
# in their own right (LIVE-01 / REFAC-05: downstream findings are keyed on them), so a
# rename reddens here as well as at the probe-name gates.
_READ_PROBES = frozenset(
    {
        "probe_market_data_sync",
        "probe_latest_sync",
        "probe_market_data_async",
        "probe_latest_async",
    }
)

# Non-vacuity floor: each of the four probes dereferences six aliases off
# ``market_data`` (``last``, ``bids``, ``offers``, ``settlement``, ``close``,
# ``open_interest``) => 4 x 6 = 24. A count below this means the consumption was
# thinned out, and the gate would start passing on a token dereference -- fail RED
# instead.
_MIN_CHAINED_ACCESSES = 24


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
    """True if the receiver chain under ``node`` passes through ``.<attribute>``."""
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
    """Map probe name -> its function node, for the four read probes only."""
    found: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name in _READ_PROBES:
            found[node.name] = node
    return found


def _chained_accesses(
    func: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[ast.Attribute]:
    """Every ``<...>.market_data.<alias>`` attribute node inside ``func``."""
    return [
        node
        for node in ast.walk(func)
        if isinstance(node, ast.Attribute)
        and node.attr in _ALIAS_NAMES
        and _chain_reaches(node.value, "market_data")
    ]


def _driver_ast() -> ast.Module:
    return ast.parse((_REPO_ROOT / _DRIVER).read_text(encoding="utf-8"))


def test_the_four_read_probes_are_present_by_name() -> None:
    """Probe-name stability (LIVE-01 / REFAC-05): a rename reddens this lock too."""
    found = _probe_functions(_driver_ast())

    missing = sorted(_READ_PROBES - set(found))
    assert not missing, (
        f"{_DRIVER}: read probe(s) {missing} not found by name. Probe names are keyed by "
        f"downstream findings (LIVE-01 / REFAC-05) and must not be renamed; if a probe was "
        f"genuinely retired, this lock and the findings ledger both need updating."
    )


def test_every_read_probe_consumes_the_typed_market_data_chain() -> None:
    """SC-5: each read probe dereferences ``market_data.<alias>`` on what it fetched.

    Counting rows would pass while the chain was broken; only a real dereference
    exercises the ``MarketDataEntries`` / ``BookLevel`` / ``EntryValue`` links that
    Plan 36-02 introduced.
    """
    found = _probe_functions(_driver_ast())

    barren = sorted(name for name, func in found.items() if not _chained_accesses(func))
    assert not barren, (
        f"{_DRIVER}: read probe(s) {barren} carry NO deep-chain access "
        f"(expected at least one attribute reached through ``market_data`` and one of "
        f"{sorted(_ALIAS_NAMES)}). ROADMAP SC-5 requires the driver to EXERCISE the typed "
        f"chain at its real sites -- a probe that only counts rows would ship a broken link."
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
        f"``None`` link there would propagate uncaught, flip market-data-client to FAILED "
        f"and lose the whole run instead of degrading to a finding: {unguarded}"
    )


def test_the_deep_chain_lock_is_not_vacuous() -> None:
    """A thinned-out consumption must redden here rather than pass on a token access."""
    found = _probe_functions(_driver_ast())
    total = sum(len(_chained_accesses(func)) for func in found.values())

    assert total >= _MIN_CHAINED_ACCESSES, (
        f"{_DRIVER}: found only {total} deep-chain access(es) across the four read probes "
        f"(expected >= {_MIN_CHAINED_ACCESSES}, i.e. all six aliases at each of the four "
        f"sites). The consumption was thinned out -- this guard is non-vacuous by design."
    )
