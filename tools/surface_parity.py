"""Sync/async surface parity helper for the six workspace clients (Phase 32, GATE-TYP-01).

This repository has **no shared code between packages, by design**, and the direct
consequence is that every client ships its request logic twice: once in
``client.py`` and once in ``aio.py``. ``CLAUDE.md``'s "Dual sync/async" constraint
says any logic fix must be mirrored in both. Two hand-maintained copies with no
gate is two copies that drift, and the drift gets discovered by a consumer rather
than by CI. This module is that gate.

It is the affirmative substitute for the twice-abandoned codegen requirement
(DT-04 / REFAC-06, shelved after two signed NO-GOs). Codegen would have made
divergence *impossible*; this makes it impossible to **keep**.

It is a **helper**, not a script. The six parity tests live in-package, as thin
files under ``packages/<pkg>/tests/test_surface_parity.py``, each delegating to
the one walker here (D-07). Six copies of the walker would recreate exactly the
drift ``tools/check_decode_intactness.py`` exists to prevent in ``_decode.py``.

Usage from an in-package test::

    from tools.surface_parity import assert_module_parity

    def test_module_surface_names_and_hints_agree() -> None:
        assert_module_parity("market_data_client")

THE METRIC, STATED ONCE
=======================

This section exists because the phase's two source decisions state the metric
**differently**, and wiring them together naively fails by exactly one in five of
the six packages (32-PATTERNS.md Pitfall 4).

A **public name** of a module is a name in ``dir(module)`` that does not start
with an underscore and whose object's ``__module__`` equals the module's own
``__name__``. The ``__module__`` filter is what drops re-exported third-party
objects (``httpx``, ``asyncio``) and imported submodules, which carry a foreign
``__module__`` or none at all.

That set has two variants, and they differ by the ``Client`` / ``AsyncClient``
class alone:

- **class-inclusive** — the set as defined above. CONTEXT's D-06 prescribes this
  filter, and it is what the *name comparison* uses, because a class that
  vanished from one surface is precisely the kind of drift this gate must catch.
- **class-exclusive** — the same set minus every member for which
  ``inspect.isclass`` is true. D-08's integers are these counts.

``MODULE_LOWER_BOUNDS`` below is expressed in the **class-exclusive** metric and
in that metric only. The class-inclusive counts are **never** pinned as a second
table of integers -- they are derived at runtime by ``public_names(...,
include_classes=True)``. One table of integers, one metric, both columns derived.
A future reader who "fixes" the bounds to match a class-inclusive count will
break five of six packages; that is why this paragraph is here.

THE NORMALIZATION
=================

These rules are the **only sanctioned place** to record a legitimate difference
between the sync and async surfaces of a package. A red gate means a surface
drifted; the fix is to revert the drift or to add a rule here with a stated
reason -- never to weaken the check into a vacuous one.

(That framing paragraph is copied from ``tools/check_decode_intactness.py:44-50``
with only its subject noun changed, because the failure mode it guards against is
identical: a gate quietly relaxed until it passes.)

The rules, each with its measured reason:

1. ``httpx.Client`` appearing in a sync hint is equivalent to
   ``httpx.AsyncClient`` appearing in the corresponding async hint. Reason: the
   async surface *must* accept an async transport; this is required correctness,
   not drift. Measured: it is the **only** hint divergence in five of the six
   packages, so without this rule the suite is red across the board and the one
   real defect is buried in the noise.
2. The name ``Client`` on the sync side is equivalent to ``AsyncClient`` on the
   async side, at both the module axis and the class axis. Reason: structural and
   uniform across all five class-bearing packages.
3. ``aclose`` is async-only and ``close`` is sync-only. At the **module** axis
   ``aclose`` has no sync counterpart at all -- verified: no module-level
   ``close`` shim exists on any sync surface -- so it is *dropped* from the async
   name set. At the **class** axis both sides have the member, so it is a
   *rename* rather than a drop.
4. Return types need no rule. An async function annotates the **awaited** type,
   so ``-> Cotizacion`` is already correct on both sides; verified that no
   ``Coroutine`` / ``Awaitable`` annotation appears anywhere in the twelve
   modules.

Anything beyond these four is drift.

WHY THIS HELPER IMPORTS PACKAGE MODULES
=======================================

The two sibling gates in this directory -- ``tools/check_surface_types.py`` and
``tools/check_uniform_structure.py`` -- read every file as **text** and never
import a package, precisely so that no import-time side effect (a
``load_dotenv()`` call, a client construction) ever runs inside a ``lint``-job
gate.

This module does the opposite **on purpose**. Runtime parity is a property of
resolved objects: ``typing.get_type_hints`` must import the modules to resolve
``from __future__ import annotations`` strings back into types, and an AST walk
cannot do it. That is exactly why this module is a *helper imported by in-package
tests* and is deliberately **not** wired into the ``lint`` job. A future reader
must not "fix" it into an AST gate -- doing so would silently downgrade the hint
comparison to string matching, which is the vacuity this phase exists to prevent.

A bonus worth naming: ``tools/*.py`` sits outside mypy's global ``files``, so it
is unchecked until a package test imports it. These tests enrol it in the
per-package strict loop by construction.

THE LOWER BOUNDS ARE PER-PACKAGE INTEGERS
=========================================

D-08 forbids a uniform threshold, and the reason is arithmetic: ``wallets`` is 1
and ``matriz`` is 22. A shared floor set low enough for wallets would make the
matriz assertion meaningless; set high enough for matriz it would falsely redden
wallets. The bounds are therefore per-package literals and must never be
collapsed.

The lower bound is the **non-vacuity guard**, in the shape of the analog at
``verification/test_main_matriz_uses_single_client_instance.py:78-99``: a
comparison that silently examined nothing passes every equality it is given, so
the count of things actually compared is itself asserted.

``wallets_client``'s floor is near-vacuous **by construction** -- its only public
module-level name is ``configure`` on the sync side and ``configure`` plus
``aclose`` on the async side, it is the one pre-Phase-7 package, and it has no
``Client`` / ``AsyncClient`` pair at all. That bound asserts almost nothing and
**must not be read as coverage**. Raising it is the job of whatever phase gives
wallets a ``Client``.
"""

from __future__ import annotations

import importlib
import inspect
import re
import typing
from dataclasses import dataclass
from types import ModuleType

# Per-package literal bounds (D-08), in the CLASS-EXCLUSIVE metric defined in
# `THE METRIC, STATED ONCE` above -- (client_min, aio_min). The class-inclusive
# counts are each of these +1 for the five class-bearing packages, and are
# derived at runtime rather than pinned here.
MODULE_LOWER_BOUNDS: dict[str, tuple[int, int]] = {
    "ambito_financiero_client": (2, 3),
    "iol_client": (6, 7),
    "higyrus_client": (7, 8),
    "matriz_client": (22, 23),
    "market_data_client": (19, 20),
    # NEAR-VACUOUS BY CONSTRUCTION -- see `THE LOWER BOUNDS` section. Do not read
    # this floor as coverage, and do not collapse the table to one threshold to
    # accommodate it.
    "wallets_client": (1, 2),
}

#: Axis label for a report over module-level names (``client`` vs ``aio``).
MODULE_AXIS = "module"
#: Axis label for a report over ``Client`` vs ``AsyncClient`` public members.
CLASS_AXIS = "class"
#: Axis label returned when the package has no ``Client``/``AsyncClient`` pair.
#: The report is *marked*, never silently emptied, so a caller can assert the
#: absence loudly instead of passing vacuously.
CLASS_AXIS_ABSENT = "class(absent)"

# Rule 2 at the module axis: the async name maps onto its sync counterpart.
_MODULE_ASYNC_TO_SYNC = {"AsyncClient": "Client"}
_MODULE_SYNC_TO_ASYNC = {sync: aio for aio, sync in _MODULE_ASYNC_TO_SYNC.items()}
# Rule 3 at the module axis: async-only, dropped (no sync counterpart exists).
_MODULE_ASYNC_ONLY = frozenset({"aclose"})

# Rule 3 at the class axis: both sides have the member, so it is a rename.
_CLASS_ASYNC_TO_SYNC = {"aclose": "close"}
_CLASS_SYNC_TO_ASYNC = {sync: aio for aio, sync in _CLASS_ASYNC_TO_SYNC.items()}

# Rule 1: rewrite the async transport type to the sync one so both sides are
# compared in a single vocabulary. Applied to the RENDERED hint string.
_ASYNC_TRANSPORT = re.compile(r"\bhttpx\.AsyncClient\b")
_SYNC_TRANSPORT = "httpx.Client"

_MISSING = "<MISSING>"

_RULE_REMINDER = (
    "  Fix this by reverting the drift, or by adding a rule with a stated reason to the\n"
    "  numbered table in tools/surface_parity.py's `THE NORMALIZATION` docstring section.\n"
    "  Never by weakening the comparison, lowering a bound, or excluding a package."
)


@dataclass(frozen=True, slots=True)
class ParityReport:
    """The result of comparing one sync surface against its async counterpart.

    ``sync_count`` / ``async_count`` are stated in the **class-exclusive** metric
    on the module axis (so they are directly comparable to
    ``MODULE_LOWER_BOUNDS``) and are public-member counts on the class axis.
    ``compared_hints`` is how many callables the hint comparison actually
    examined -- a report where that is zero compared nothing, however green its
    name sets look.
    """

    package: str
    axis: str
    sync_only: tuple[str, ...]
    async_only: tuple[str, ...]
    hint_mismatches: tuple[str, ...]
    sync_count: int
    async_count: int
    compared_hints: int


# ---------------------------------------------------------------------------
# Introspection primitives
# ---------------------------------------------------------------------------


def public_names(module: ModuleType, *, include_classes: bool) -> frozenset[str]:
    """Return ``module``'s public names under the metric stated in the docstring.

    ``include_classes=True`` yields the **class-inclusive** variant (D-06's
    filter, used for the name comparison); ``False`` yields the
    **class-exclusive** variant (D-08's metric, used for the bounds).
    """
    names: set[str] = set()
    for name in dir(module):
        if name.startswith("_"):
            continue
        member = getattr(module, name)
        if getattr(member, "__module__", None) != module.__name__:
            continue
        if not include_classes and inspect.isclass(member):
            continue
        names.add(name)
    return frozenset(names)


def _public_member_names(cls: type) -> frozenset[str]:
    """Return the non-underscore members of ``cls``, callable or not.

    Non-callable public attributes are deliberately included: an attribute that
    exists on one surface and not the other is drift regardless of whether it can
    be called. Only the *hint* comparison narrows to callables.
    """
    return frozenset(name for name in dir(cls) if not name.startswith("_"))


def _render_hint(value: object) -> str:
    """Render one resolved hint to a stable, comparable string.

    Plain classes render as ``module.QualName`` rather than ``<class '...'>``, so
    a failure message reads as a declaration rather than as a repr.
    """
    if isinstance(value, type):
        return f"{value.__module__}.{value.__qualname__}"
    return repr(value)


def normalized_hints(obj: object, *, surface: str) -> dict[str, str]:
    """Resolve ``obj``'s annotations and render them under rule 1.

    Uses ``typing.get_type_hints`` and never raw ``__annotations__``: every module
    in this repo carries ``from __future__ import annotations``, so
    ``__annotations__`` yields unresolved *strings* and the comparison would
    silently degrade into string matching.

    Resolution failures are allowed to **propagate**. Research resolved 347 of 347
    public callables with zero failures, so a failure now is a real signal --
    a ``TYPE_CHECKING``-only import, say -- and swallowing it would empty the
    comparison, which is the exact vacuity this gate exists to prevent.
    """
    if surface not in {"sync", "async"}:
        raise ValueError(f"surface must be 'sync' or 'async', got {surface!r}")
    rendered = {key: _render_hint(value) for key, value in typing.get_type_hints(obj).items()}
    if surface == "async":
        # Rule 1: the async transport is equivalent to the sync one.
        rendered = {
            key: _ASYNC_TRANSPORT.sub(_SYNC_TRANSPORT, value) for key, value in rendered.items()
        }
    return rendered


def _diff_hints(qualified_name: str, sync: dict[str, str], aio: dict[str, str]) -> list[str]:
    """Render every hint disagreement as a line that reads as a bug report."""
    lines: list[str] = []
    for key in sorted(set(sync) | set(aio)):
        sync_decl = sync.get(key, _MISSING)
        async_decl = aio.get(key, _MISSING)
        if sync_decl == async_decl:
            continue
        label = "return type" if key == "return" else f"parameter {key!r}"
        lines.append(
            f"  {qualified_name}(): {label} differs -- "
            f"sync declares {sync_decl}, async declares {async_decl}"
        )
    return lines


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------


def module_parity_report(package: str) -> ParityReport:
    """Compare ``<package>.client`` against ``<package>.aio`` at the module axis."""
    sync_mod = importlib.import_module(f"{package}.client")
    async_mod = importlib.import_module(f"{package}.aio")

    sync_names = public_names(sync_mod, include_classes=True)
    async_names = public_names(async_mod, include_classes=True)
    # Rules 2 and 3 applied to the async name set.
    normalized_async = frozenset(
        _MODULE_ASYNC_TO_SYNC.get(name, name)
        for name in async_names
        if name not in _MODULE_ASYNC_ONLY
    )

    mismatches: list[str] = []
    compared = 0
    for name in sorted(sync_names & normalized_async):
        sync_obj = getattr(sync_mod, name)
        if inspect.isclass(sync_obj):
            # The class axis owns classes; here they are name-compared only.
            continue
        async_obj = getattr(async_mod, _MODULE_SYNC_TO_ASYNC.get(name, name))
        compared += 1
        mismatches.extend(
            _diff_hints(
                name,
                normalized_hints(sync_obj, surface="sync"),
                normalized_hints(async_obj, surface="async"),
            )
        )

    return ParityReport(
        package=package,
        axis=MODULE_AXIS,
        sync_only=tuple(sorted(sync_names - normalized_async)),
        async_only=tuple(sorted(normalized_async - sync_names)),
        hint_mismatches=tuple(mismatches),
        # Class-EXCLUSIVE, so these are directly comparable to MODULE_LOWER_BOUNDS.
        sync_count=len(public_names(sync_mod, include_classes=False)),
        async_count=len(public_names(async_mod, include_classes=False)),
        compared_hints=compared,
    )


def class_parity_report(package: str) -> ParityReport:
    """Compare ``Client`` against ``AsyncClient`` at the class axis.

    When the package has no such pair, returns a report whose ``axis`` is
    ``CLASS_AXIS_ABSENT`` rather than raising, so a caller can assert the absence
    explicitly (``wallets_client`` is the one such package today).
    """
    sync_mod = importlib.import_module(f"{package}.client")
    async_mod = importlib.import_module(f"{package}.aio")
    sync_cls = getattr(sync_mod, "Client", None)
    async_cls = getattr(async_mod, "AsyncClient", None)

    if not (inspect.isclass(sync_cls) and inspect.isclass(async_cls)):
        return ParityReport(
            package=package,
            axis=CLASS_AXIS_ABSENT,
            sync_only=(),
            async_only=(),
            hint_mismatches=(),
            sync_count=0,
            async_count=0,
            compared_hints=0,
        )

    sync_names = _public_member_names(sync_cls)
    async_names = _public_member_names(async_cls)
    # Rule 3 at the class axis is a RENAME, not a drop.
    normalized_async = frozenset(_CLASS_ASYNC_TO_SYNC.get(name, name) for name in async_names)

    mismatches: list[str] = []
    compared = 0
    for name in sorted(sync_names & normalized_async):
        sync_obj = getattr(sync_cls, name)
        async_obj = getattr(async_cls, _CLASS_SYNC_TO_ASYNC.get(name, name))
        if not (callable(sync_obj) and callable(async_obj)):
            continue
        compared += 1
        mismatches.extend(
            _diff_hints(
                f"{sync_cls.__name__}.{name}",
                normalized_hints(sync_obj, surface="sync"),
                normalized_hints(async_obj, surface="async"),
            )
        )

    return ParityReport(
        package=package,
        axis=CLASS_AXIS,
        sync_only=tuple(sorted(sync_names - normalized_async)),
        async_only=tuple(sorted(normalized_async - sync_names)),
        hint_mismatches=tuple(mismatches),
        sync_count=len(sync_names),
        async_count=len(async_names),
        compared_hints=compared,
    )


# ---------------------------------------------------------------------------
# Assertions
#
# These raise `AssertionError` with a FULLY FORMED message. pytest's assertion
# rewriting does not apply inside a non-test module, so the message must stand on
# its own -- the shape of the analog at
# `verification/test_main_matriz_uses_single_client_instance.py:97-99`.
# ---------------------------------------------------------------------------


def _bounds_for(package: str) -> tuple[int, int]:
    if package not in MODULE_LOWER_BOUNDS:
        raise AssertionError(
            f"{package!r} has no entry in MODULE_LOWER_BOUNDS. A package without a "
            f"stated per-package floor cannot be asserted non-vacuously; add its "
            f"measured (client_min, aio_min) rather than reusing another package's."
        )
    return MODULE_LOWER_BOUNDS[package]


def _fail(report: ParityReport, problems: list[str]) -> None:
    raise AssertionError(
        f"sync/async {report.axis.upper()} parity FAILED for {report.package} "
        f"({report.package}.client vs {report.package}.aio):\n"
        + "\n".join(problems)
        + f"\n  [compared {report.compared_hints} callable(s); "
        f"sync={report.sync_count}, async={report.async_count}]\n" + _RULE_REMINDER
    )


def _name_and_hint_problems(report: ParityReport) -> list[str]:
    problems: list[str] = []
    if report.sync_only:
        problems.append(
            f"  present on the SYNC surface only (after rules 2-3): {list(report.sync_only)}"
        )
    if report.async_only:
        problems.append(
            f"  present on the ASYNC surface only (after rules 2-3): {list(report.async_only)}"
        )
    problems.extend(report.hint_mismatches)
    return problems


def assert_module_parity(package: str) -> None:
    """Assert the module axis: name sets agree AND every shared hint agrees.

    Also asserts ``compared_hints >= MODULE_LOWER_BOUNDS[package][0]``. A
    comparison that silently examined nothing agrees with everything, and that
    vacuity is the failure mode this phase exists to prevent -- so the count of
    callables actually examined is asserted alongside the agreement itself.
    """
    report = module_parity_report(package)
    problems = _name_and_hint_problems(report)
    floor = _bounds_for(package)[0]
    if report.compared_hints < floor:
        problems.append(
            f"  VACUOUS: only {report.compared_hints} callable(s) had their hints compared, "
            f"below the per-package floor of {floor}. The comparison examined too little "
            f"to mean anything."
        )
    if problems:
        _fail(report, problems)


def assert_class_parity(package: str) -> None:
    """Assert the class axis: ``Client`` and ``AsyncClient`` agree by rule 3.

    Raises for a package with **no** class pair rather than passing vacuously.
    Such a package must call :func:`class_parity_report` and assert the absence
    explicitly, with a stated reason -- an explicit skip, never a silent one.
    """
    report = class_parity_report(package)
    if report.axis == CLASS_AXIS_ABSENT:
        raise AssertionError(
            f"{package} has no Client/AsyncClient pair, so the class axis cannot be "
            f"asserted here. Passing would be vacuous. Call class_parity_report({package!r}) "
            f"and assert axis == CLASS_AXIS_ABSENT explicitly, with the reason stated."
        )
    problems = _name_and_hint_problems(report)
    if report.compared_hints < 1:
        problems.append(f"  VACUOUS: {report.compared_hints} method(s) had their hints compared.")
    if problems:
        _fail(report, problems)


def assert_module_lower_bound(package: str) -> None:
    """Assert both module surfaces still expose at least their measured floor.

    The bound is stated in the CLASS-EXCLUSIVE metric (see ``THE METRIC, STATED
    ONCE``). It catches the failure a parity comparison cannot: two surfaces that
    agree with each other because both collapsed.
    """
    report = module_parity_report(package)
    client_min, aio_min = _bounds_for(package)
    problems: list[str] = []
    if report.sync_count < client_min:
        problems.append(
            f"  {package}.client exposes {report.sync_count} public non-class name(s), "
            f"below the measured floor of {client_min}"
        )
    if report.async_count < aio_min:
        problems.append(
            f"  {package}.aio exposes {report.async_count} public non-class name(s), "
            f"below the measured floor of {aio_min}"
        )
    if problems:
        _fail(report, problems)
