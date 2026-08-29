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

# Non-vacuity floor, PER PROBE. Each probe dereferences the six aliases off
# ``market_data`` (``last``, ``bids``, ``offers``, ``settlement``, ``close``,
# ``open_interest``) ONCE PER FETCHED COLLECTION. The two ``latest`` probes fetch
# TWO independent collections of ``MarketDataSnapshot`` -- ``latest`` (GET) and
# ``batch`` (the POST body) -- so they are held to 12, not 6.
#
# Phase 36 code review, WR-06: the floor used to be a single repo-wide 24 and the
# guard counted accesses per FUNCTION, not per fetched collection. ``batch`` was
# consumed by ``len()`` alone -- precisely the pattern this module's docstring
# forbids -- while the guard reported the probe as covered, because ``latest``'s
# six dereferences were enough to satisfy a function-scoped count. A per-probe
# floor plus ``test_every_fetched_snapshot_collection_is_chained`` below closes
# that: a second collection cannot be added and left unexercised.
_MIN_CHAINED_ACCESSES_BY_PROBE = {
    "probe_market_data_sync": 6,
    "probe_latest_sync": 12,
    "probe_market_data_async": 6,
    "probe_latest_async": 12,
}

# Kept as the aggregate the original SC-5 lock stated, derived rather than
# re-typed so the two can never disagree.
_MIN_CHAINED_ACCESSES = sum(_MIN_CHAINED_ACCESSES_BY_PROBE.values())

# How many independent ``MarketDataSnapshot`` collections each probe fetches, and
# therefore how many distinct comprehension iterables must carry a chained
# access. Names are the driver's own locals.
_CHAINED_COLLECTIONS_BY_PROBE = {
    "probe_market_data_sync": {"snapshots"},
    "probe_latest_sync": {"latest", "batch"},
    "probe_market_data_async": {"snapshots"},
    "probe_latest_async": {"latest", "batch"},
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
        f"(expected >= {_MIN_CHAINED_ACCESSES}, i.e. all six aliases once per fetched "
        f"collection). The consumption was thinned out -- this guard is non-vacuous by design."
    )


def test_each_probe_meets_its_own_floor() -> None:
    """WR-06: the aggregate can be met while ONE probe carries almost nothing.

    24 accesses spread 18/2/2/2 satisfies the repo-wide sum and leaves three
    probes effectively unexercised. The per-probe floor is what makes the count
    a statement about each site.
    """
    found = _probe_functions(_driver_ast())

    short = {
        name: (len(_chained_accesses(func)), _MIN_CHAINED_ACCESSES_BY_PROBE[name])
        for name, func in found.items()
        if len(_chained_accesses(func)) < _MIN_CHAINED_ACCESSES_BY_PROBE[name]
    }

    assert not short, (
        f"{_DRIVER}: probe(s) below their own deep-chain floor (got, expected): {short}. "
        f"A ``latest`` probe is held to 12 because it fetches TWO independent collections "
        f"of MarketDataSnapshot -- ``latest`` (GET) and ``batch`` (POST body)."
    )


def test_every_fetched_snapshot_collection_is_chained() -> None:
    """WR-06: a second fetched collection may not be consumed by ``len()`` alone.

    The counting guards above are function-scoped, so a probe that fetches two
    collections and chains only one still reaches its numeric floor. This asserts
    the structural fact instead: for EVERY collection the probe fetches, some
    comprehension iterating it must carry a ``market_data.<alias>`` dereference.
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
                and _chain_reaches(node.value, "market_data")
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
        f"{_DRIVER}: fetched MarketDataSnapshot collection(s) with NO deep-chain access "
        f"{unchained}. A collection consumed by ``len()`` alone ships its whole decode path "
        f"unexercised while the probe still reports PASS -- WR-06, the exact defect this "
        f"module's docstring describes, one level up from a single probe."
    )
