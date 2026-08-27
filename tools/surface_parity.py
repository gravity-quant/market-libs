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
with an underscore and that the **package owns**. Ownership, not authorship of
the containing file, is the criterion, and it is decided by
:func:`_is_package_owned` in three tests applied in order:

1. An imported submodule (any ``ModuleType`` value) is never surface.
2. A value whose ``__module__`` is absent, is the module's own ``__name__``, or
   lies inside the package's import root is owned. This admits module-level
   constants (a ``str``/``tuple``/``dict`` has no ``__module__`` at all) and
   every model, exception and helper the module re-exports from a sibling.
3. A value with a **foreign** ``__module__`` is owned only if the foreign module
   does not itself publish that same object under that same name. That single
   identity test separates ``Any``, ``Self``, ``Literal``, ``Sequence``,
   ``Path``, ``urlsplit``, ``load_dotenv`` and ``annotations`` -- which *are*
   ``typing.Any``, ``pathlib.Path``, ``dotenv.main.load_dotenv`` and so on --
   from ``InstrumentType = Literal[...]``, a ``Literal`` alias that carries
   ``__module__ == 'typing'`` because ``typing`` built the object, but that
   ``typing`` has never heard of and that the package alone publishes.

**Why the filter was widened (Phase 32 WR-02).** It used to be
``member.__module__ != module.__name__``, documented as dropping "re-exported
third-party objects (``httpx``, ``asyncio``) and imported submodules". It also
dropped every module-level constant, every ``Literal`` alias the package owns,
and every re-exported model and exception -- and with them three live
``client``/``aio`` name-set divergences that the gate reported green, including
``market_data_client.aio`` publishing ``RequestSpec`` where
``market_data_client.client`` did not.

**One exclusion is deliberate and is stated here rather than left implicit.**
A *third-party* name re-exported by one surface and not the other --
``matriz_client.client`` binds ``load_dotenv`` at module level and
``matriz_client.aio`` does not -- is **not** reported. Rule 3 drops it. Reporting
it would mean reporting every asymmetry in twelve modules' import lists
(``Any``, ``Self``, ``Path``, ``Sequence``, ``urlsplit``, ``annotations``), which
is noise that would bury the real signal -- the failure mode rule 1 of ``THE
NORMALIZATION`` was written to avoid. An import list is not a published surface;
if that judgement is ever revisited, revisit it here.

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
5. ``__init__`` is compared at the class axis despite the underscore filter, and
   it is the **only** dunder so compared. Reason: it is the largest keyword
   surface on either class and the likeliest drift site -- Phase 32 CR-02 found
   ``market_data_client.AsyncClient.__init__`` accepting ``token``,
   ``token_expires_at`` and ``http_client`` that ``Client.__init__`` did not,
   one call away from the ``aio.configure`` divergence this phase was written to
   close. Every other dunder implements a protocol this repo does not own
   (``__reduce__``, ``__deepcopy__``, ``__enter__``/``__aenter__``), where a
   sync/async difference is required correctness rather than drift; ``__init__``
   is the one whose signature the repo authors line by line.

Anything beyond these five is drift.

WHAT IS COMPARED: HINTS **AND** SIGNATURE SHAPE
===============================================

``typing.get_type_hints`` returns an **unordered ``name -> type`` mapping** and
nothing else. It carries no parameter *kind*, no *default*, no ``*args`` /
``**kwargs``, and no ordering. Phase 32 WR-01 demonstrated the consequence
against the shipped helper::

    def sync_f(a: str, b: int = 1) -> str: ...
    async def async_f(b: int, *, a: str = "x") -> str: ...
    # reordered, defaulted, and made keyword-only -- reported as AGREEING

So every callable is compared twice, and both halves are load-bearing:

- ``normalized_hints`` supplies the resolved annotation *values*, which
  ``inspect.signature`` cannot give under ``from __future__ import annotations``
  (it would hand back unresolved strings and degrade the comparison to string
  matching).
- ``signature_shape`` supplies the parameter *list in declaration order*, each
  one's ``kind`` and its ``default`` -- the shape the annotation mapping cannot
  see.

Annotations are deliberately **not** read off ``inspect.signature``: that is the
division of labour, and collapsing it back into one call is how the blind spot
returns.

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

**Surface size and compared-callable count are two different integers.** They
used to be one: ``MODULE_LOWER_BOUNDS[package][0]`` was both the floor on the
module's public-name count *and* the floor on ``compared_hints``. WR-02's widened
filter admits constants and ``Literal`` aliases, which are name-compared but have
no signature to diff, so the two numbers parted company (matriz: 31 public names,
23 compared callables). Conflating them again would mean either a name floor low
enough to be meaningless or a compared floor no tree can satisfy, so there are
now two measured tables:

- ``MODULE_LOWER_BOUNDS`` -- floor on the public-name count, class-exclusive.
- ``MODULE_COMPARED_LOWER_BOUNDS`` -- floor on ``compared_hints``, the count of
  callables whose hints AND signature were actually diffed.

THE ROSTER IS CROSS-CHECKED AGAINST DISK (Phase 32 WR-04)
=========================================================

Parity coverage used to be the intersection of two hand-maintained lists -- the
keys of ``MODULE_LOWER_BOUNDS`` and the six
``packages/*/tests/test_surface_parity.py`` files -- with neither derived from
disk and nothing cross-checking them. A seventh package could enter the workspace
with **no** parity test and **no** bounds entry, and every gate would stay green:
omission by silence, the exact failure mode this phase is written against.

The two sibling gates adopted the opposite discipline and say so in prose
(``tools/check_surface_types.py``'s ``THE ROSTER COMES FROM DISK``,
``tools/check_decode_intactness.py``'s Check D). Only this module skipped it.
:func:`assert_bounds_roster_matches_disk` closes that: it enumerates
``packages/*/src/<import_name>`` at run time and requires every package found to
carry an entry in **all four** bounds tables and an in-package hook file. A
package that leaves must have its entries removed; one that arrives must have
them measured.

``wallets_client``'s floors are near-vacuous **by construction** -- its only
public module-level name is ``configure`` on the sync side and ``configure`` plus
``aclose`` on the async side, it is the one pre-Phase-7 package, and it has no
``Client`` / ``AsyncClient`` pair at all. Those bounds assert almost nothing and
**must not be read as coverage**. Raising them is the job of whatever phase gives
wallets a ``Client``.
"""

from __future__ import annotations

import importlib
import inspect
import re
import sys
import typing
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

#: Repository root, derived from this file's location. A **default argument
#: value only** -- every roster function threads a ``root`` parameter, which is
#: the seam that lets the RED suite inject a synthetic workspace.
REPO_ROOT = Path(__file__).resolve().parent.parent

#: Directory names under ``packages/<pkg>/src/`` that are build or tooling
#: artifacts rather than the package's import root.
_NON_IMPORT_ROOTS = ("__pycache__",)
_BUILD_ARTIFACT_SUFFIX = ".egg-info"

#: The in-package hook every workspace package owes the parity axes.
_HOOK_RELATIVE_PATH = Path("tests") / "test_surface_parity.py"

# Per-package literal bounds (D-08), in the CLASS-EXCLUSIVE metric defined in
# `THE METRIC, STATED ONCE` above -- (client_min, aio_min). The class-inclusive
# counts are each of these +1 for the five class-bearing packages, and are
# derived at runtime rather than pinned here.
#
# RE-MEASURED for Phase 32 WR-02: the widened ownership filter admits every
# module-level constant, `Literal` alias and package-owned re-export the old
# `__module__` test dropped. matriz moves 22 -> 31, iol 6 -> 7. Leaving the old
# integers in place would have kept a floor that no longer bounds anything.
MODULE_LOWER_BOUNDS: dict[str, tuple[int, int]] = {
    "ambito_financiero_client": (2, 3),
    "iol_client": (7, 8),
    "higyrus_client": (7, 8),
    "matriz_client": (31, 32),
    "market_data_client": (19, 20),
    # NEAR-VACUOUS BY CONSTRUCTION -- see `THE LOWER BOUNDS` section. Do not read
    # this floor as coverage, and do not collapse the table to one threshold to
    # accommodate it.
    "wallets_client": (1, 2),
}

# Floor on `compared_hints` at the MODULE axis: how many callables actually had
# both halves of the comparison run against them. A separate table from
# MODULE_LOWER_BOUNDS because a constant is name-compared but not diffed -- see
# `THE LOWER BOUNDS ARE PER-PACKAGE INTEGERS`. Measured, per package, never
# uniform.
MODULE_COMPARED_LOWER_BOUNDS: dict[str, int] = {
    "ambito_financiero_client": 2,
    "iol_client": 6,
    "higyrus_client": 7,
    "matriz_client": 23,
    "market_data_client": 19,
    # NEAR-VACUOUS BY CONSTRUCTION -- `configure` is the one compared callable.
    "wallets_client": 1,
}

# Phase 32 WR-03. The CLASS axis used a hard-coded `compared_hints < 1`, in the
# same module that spends `THE LOWER BOUNDS ARE PER-PACKAGE INTEGERS` arguing a
# shared floor is arithmetically wrong -- and it applied that shared floor of 1
# where matriz's `Client` carries 23 public members. Two classes that collapsed
# in lockstep to a single shared method agreed with each other perfectly and
# passed. `ParityReport.sync_count` / `async_count` were populated on this axis
# and asserted against nothing.
#
# (sync_min, async_min) public members of `Client` / `AsyncClient`.
CLASS_LOWER_BOUNDS: dict[str, tuple[int, int]] = {
    "ambito_financiero_client": (3, 3),
    "iol_client": (7, 7),
    "higyrus_client": (8, 8),
    "matriz_client": (23, 23),
    "market_data_client": (20, 20),
    # NO CLASS PAIR AT ALL -- wallets is the one pre-Phase-7 package; its request
    # functions are module-level. The entry exists, at (0, 0) and with this
    # reason stated, so the roster cross-check has something to find rather than
    # a hole it cannot tell from an oversight. `assert_class_parity` still
    # RAISES for wallets; the absence is asserted explicitly in its hook file.
    "wallets_client": (0, 0),
}

# Floor on `compared_hints` at the CLASS axis -- members whose hints AND
# signature were diffed, `__init__` included (rule 5). Measured per package for
# the same arithmetic reason as every other table here.
CLASS_COMPARED_LOWER_BOUNDS: dict[str, int] = {
    "ambito_financiero_client": 4,
    "iol_client": 8,
    "higyrus_client": 9,
    "matriz_client": 24,
    "market_data_client": 21,
    # NO CLASS PAIR -- see CLASS_LOWER_BOUNDS.
    "wallets_client": 0,
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
#: Sentinel for "the foreign module has no such attribute". A dedicated object
#: rather than ``None``, because ``None`` is a perfectly plausible attribute
#: value and would make the identity test below silently wrong.
_UNSET = object()
#: Rendered stand-in for a parameter with no default, so "no default" and
#: "default is None" can never compare equal.
_NO_DEFAULT = "<NO-DEFAULT>"

_RULE_REMINDER = (
    "  Fix this by reverting the drift, or by adding a rule with a stated reason to the\n"
    "  numbered table in tools/surface_parity.py's `THE NORMALIZATION` docstring section.\n"
    "  Never by weakening the comparison, lowering a bound, or excluding a package."
)


@dataclass(frozen=True, slots=True)
class _Parameter:
    """One parameter's *shape*: what a ``name -> type`` mapping cannot express.

    ``kind`` is ``inspect.Parameter.kind.name`` (``POSITIONAL_OR_KEYWORD``,
    ``KEYWORD_ONLY``, ``VAR_KEYWORD``, ...) and ``default`` is the ``repr`` of
    the default value, or ``_NO_DEFAULT``. The annotation is deliberately absent
    -- see :func:`signature_shape`.
    """

    name: str
    kind: str
    default: str


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


def _import_root(module: ModuleType) -> str:
    """The top-level package name of ``module`` (``matriz_client.aio`` -> ``matriz_client``)."""
    return module.__name__.split(".", 1)[0]


def _is_package_owned(module: ModuleType, name: str, member: object) -> bool:
    """Whether ``name`` is part of ``module``'s published surface.

    The three ordered tests are stated in full in ``THE METRIC, STATED ONCE``.
    Summarised: submodules never count; anything owned by this package counts,
    including annotation-less constants; and a foreign-owned value counts only
    when the foreign module does not publish that same object under that same
    name -- which is what tells a package's ``Literal`` alias apart from
    ``typing.Any`` itself.
    """
    if isinstance(member, ModuleType):
        return False
    owner = getattr(member, "__module__", None)
    if owner is None or owner == module.__name__:
        return True
    root = _import_root(module)
    if owner == root or owner.startswith(f"{root}."):
        return True
    foreign = sys.modules.get(owner)
    if foreign is None:
        # The owning module is not imported, so it cannot be re-exporting this
        # object under this name. Treat as owned rather than silently dropping
        # it: an unreadable attribution must not narrow the compared surface.
        return True
    return getattr(foreign, name, _UNSET) is not member


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
        if not _is_package_owned(module, name, member):
            continue
        if not include_classes and inspect.isclass(member):
            continue
        names.add(name)
    return frozenset(names)


#: Rule 5: the one dunder whose signature this repo owns, and therefore the one
#: the underscore filter must not hide. See ``THE NORMALIZATION`` rule 5.
_COMPARED_DUNDER = "__init__"


def _public_member_names(cls: type) -> frozenset[str]:
    """Return the non-underscore members of ``cls``, callable or not.

    Non-callable public attributes are deliberately included: an attribute that
    exists on one surface and not the other is drift regardless of whether it can
    be called. Only the *hint* comparison narrows to callables.

    ``__init__`` is excluded here by the underscore filter and re-added by rule 5
    in :func:`class_parity_report`; it is a *name* both classes always have, so
    only its hints are worth comparing.
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


def signature_shape(obj: Callable[..., object]) -> tuple[_Parameter, ...]:
    """The parameter list of ``obj`` in declaration order, with kind and default.

    Annotations are deliberately excluded -- under ``from __future__ import
    annotations`` ``inspect.signature`` yields unresolved *strings*, and
    :func:`normalized_hints` already owns the annotation half of the comparison.
    What this adds is exactly what a ``name -> type`` mapping cannot express:
    order, ``kind`` (positional-vs-keyword-only, ``*args``, ``**kwargs``) and
    default value (WR-01).

    Failures are allowed to **propagate**, for the same reason
    :func:`normalized_hints` lets resolution failures propagate: an object whose
    signature cannot be read is a real signal, and swallowing it would empty the
    comparison.
    """
    return tuple(
        _Parameter(
            name=parameter.name,
            kind=parameter.kind.name,
            default=(
                _NO_DEFAULT
                if parameter.default is inspect.Parameter.empty
                else repr(parameter.default)
            ),
        )
        for parameter in inspect.signature(obj).parameters.values()
    )


def _diff_signatures(
    qualified_name: str, sync: tuple[_Parameter, ...], aio: tuple[_Parameter, ...]
) -> list[str]:
    """Render every signature-shape disagreement as a line that reads as a bug report."""
    lines: list[str] = []
    sync_order = tuple(parameter.name for parameter in sync)
    async_order = tuple(parameter.name for parameter in aio)
    if sync_order != async_order:
        lines.append(
            f"  {qualified_name}(): parameter list differs -- "
            f"sync declares {list(sync_order)}, async declares {list(async_order)}"
        )
    sync_by_name = {parameter.name: parameter for parameter in sync}
    async_by_name = {parameter.name: parameter for parameter in aio}
    for name in sorted(set(sync_by_name) & set(async_by_name)):
        sync_param, async_param = sync_by_name[name], async_by_name[name]
        if sync_param.kind != async_param.kind:
            lines.append(
                f"  {qualified_name}(): parameter {name!r} kind differs -- "
                f"sync is {sync_param.kind}, async is {async_param.kind}"
            )
        if sync_param.default != async_param.default:
            lines.append(
                f"  {qualified_name}(): parameter {name!r} default differs -- "
                f"sync declares {sync_param.default}, async declares {async_param.default}"
            )
    return lines


def _diff_callable(
    qualified_name: str, sync_obj: Callable[..., object], async_obj: Callable[..., object]
) -> list[str]:
    """Compare one sync callable against its async counterpart, both halves.

    The two halves are complementary and neither alone is a comparison: hints
    without a signature miss order/kind/default (WR-01); a signature without
    resolved hints degrades to string matching under ``from __future__ import
    annotations``.
    """
    return _diff_hints(
        qualified_name,
        normalized_hints(sync_obj, surface="sync"),
        normalized_hints(async_obj, surface="async"),
    ) + _diff_signatures(qualified_name, signature_shape(sync_obj), signature_shape(async_obj))


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
        if not (inspect.isroutine(sync_obj) and inspect.isroutine(async_obj)):
            # A constant or a `Literal` alias has no signature and no hints. It
            # is still NAME-compared above -- that is what WR-02's widened filter
            # bought -- but there is nothing here to diff. `isroutine` rather
            # than `callable`: a `Literal[...]` alias IS callable and would blow
            # up `inspect.signature`.
            continue
        compared += 1
        if sync_obj is async_obj:
            # Both surfaces re-export the IDENTICAL object from a shared sibling
            # module (`matriz_client._token_store.build_token_store`). Identity
            # is the strongest agreement there is, so this counts as compared --
            # and resolving its hints in the re-exporting module's namespace
            # would raise on a `TYPE_CHECKING`-only import that is perfectly
            # resolvable where the function is defined.
            continue
        mismatches.extend(_diff_callable(name, sync_obj, async_obj))

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
        mismatches.extend(_diff_callable(f"{sync_cls.__name__}.{name}", sync_obj, async_obj))

    # Rule 5: `__init__` is hidden from the loop above by the underscore filter,
    # but it is the largest keyword surface on either class and the likeliest
    # drift site (Phase 32 CR-02). Compared explicitly, and counted, so it can
    # never be the thing the gate quietly stopped looking at.
    compared += 1
    mismatches.extend(
        _diff_callable(
            f"{sync_cls.__name__}.{_COMPARED_DUNDER}", sync_cls.__init__, async_cls.__init__
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


def _compared_floor_for(package: str) -> int:
    if package not in MODULE_COMPARED_LOWER_BOUNDS:
        raise AssertionError(
            f"{package!r} has no entry in MODULE_COMPARED_LOWER_BOUNDS. A package "
            f"without a stated per-package floor on the number of callables actually "
            f"diffed cannot be asserted non-vacuously; add its measured integer rather "
            f"than reusing another package's."
        )
    return MODULE_COMPARED_LOWER_BOUNDS[package]


def _class_bounds_for(package: str) -> tuple[int, int]:
    if package not in CLASS_LOWER_BOUNDS:
        raise AssertionError(
            f"{package!r} has no entry in CLASS_LOWER_BOUNDS. A package without a "
            f"stated per-package floor on its Client/AsyncClient member counts cannot "
            f"be asserted non-vacuously; add its measured (sync_min, async_min), or "
            f"(0, 0) WITH the reason if it has no class pair."
        )
    return CLASS_LOWER_BOUNDS[package]


def _class_compared_floor_for(package: str) -> int:
    if package not in CLASS_COMPARED_LOWER_BOUNDS:
        raise AssertionError(
            f"{package!r} has no entry in CLASS_COMPARED_LOWER_BOUNDS. A package "
            f"without a stated per-package floor on the number of members actually "
            f"diffed cannot be asserted non-vacuously; add its measured integer rather "
            f"than reusing another package's."
        )
    return CLASS_COMPARED_LOWER_BOUNDS[package]


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

    Also asserts ``compared_hints >= MODULE_COMPARED_LOWER_BOUNDS[package]``. A
    comparison that silently examined nothing agrees with everything, and that
    vacuity is the failure mode this phase exists to prevent -- so the count of
    callables actually examined is asserted alongside the agreement itself.

    That floor is its **own** measured table, not ``MODULE_LOWER_BOUNDS[0]``: a
    module-level constant is name-compared but has no signature to diff, so the
    public-name count and the compared-callable count are different integers
    (WR-02).
    """
    report = module_parity_report(package)
    problems = _name_and_hint_problems(report)
    floor = _compared_floor_for(package)
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

    The three floors are all per-package measured integers
    (``CLASS_LOWER_BOUNDS``, ``CLASS_COMPARED_LOWER_BOUNDS``), never a shared
    threshold. The shared threshold this replaces was ``compared_hints < 1``,
    which two classes collapsed in lockstep to a single shared method would
    satisfy (WR-03).
    """
    report = class_parity_report(package)
    if report.axis == CLASS_AXIS_ABSENT:
        raise AssertionError(
            f"{package} has no Client/AsyncClient pair, so the class axis cannot be "
            f"asserted here. Passing would be vacuous. Call class_parity_report({package!r}) "
            f"and assert axis == CLASS_AXIS_ABSENT explicitly, with the reason stated."
        )
    problems = _name_and_hint_problems(report)
    compared_floor = _class_compared_floor_for(package)
    if report.compared_hints < compared_floor:
        problems.append(
            f"  VACUOUS: only {report.compared_hints} member(s) had their hints and "
            f"signature compared, below the per-package floor of {compared_floor}. The "
            f"comparison examined too little to mean anything."
        )
    sync_min, async_min = _class_bounds_for(package)
    if report.sync_count < sync_min:
        problems.append(
            f"  {package}.client's Client exposes {report.sync_count} public member(s), "
            f"below the measured floor of {sync_min} -- the two surfaces may agree "
            f"because BOTH collapsed"
        )
    if report.async_count < async_min:
        problems.append(
            f"  {package}.aio's AsyncClient exposes {report.async_count} public member(s), "
            f"below the measured floor of {async_min} -- the two surfaces may agree "
            f"because BOTH collapsed"
        )
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


# ---------------------------------------------------------------------------
# Roster cross-check (WR-04)
# ---------------------------------------------------------------------------


def workspace_packages(root: Path = REPO_ROOT) -> dict[str, Path]:
    """Map every workspace package's import name to its package directory.

    Enumerated from ``packages/*/src/`` at run time, never from a literal list:
    a seventh package entering the workspace must be *found*, not silently
    exempted by omission. Every structural surprise -- no ``packages/``, an empty
    roster, a ``src/`` with zero or several candidate import roots -- raises with
    the offending candidates named, rather than being dropped from the result.
    """
    packages_dir = root / "packages"
    if not packages_dir.is_dir():
        raise AssertionError(
            f"there is no `packages/` directory under {root} -- that is a broken "
            f"checkout, not a workspace with no packages"
        )

    found: dict[str, Path] = {}
    problems: list[str] = []
    for package_dir in sorted(packages_dir.iterdir()):
        if not package_dir.is_dir() or package_dir.name.startswith("."):
            continue
        src = package_dir / "src"
        if not src.is_dir():
            problems.append(f"  `{package_dir.name}` has no `src/` directory")
            continue
        candidates = [
            child
            for child in sorted(src.iterdir())
            if child.is_dir()
            and not child.name.startswith(".")
            and child.name not in _NON_IMPORT_ROOTS
            and not child.name.endswith(_BUILD_ARTIFACT_SUFFIX)
        ]
        if len(candidates) != 1:
            problems.append(
                f"  `{package_dir.name}` has {len(candidates)} candidate import roots under "
                f"src/ (expected exactly 1): {[c.name for c in candidates]}"
            )
            continue
        found[candidates[0].name] = package_dir

    if problems:
        raise AssertionError(
            "the workspace roster could not be read from disk:\n" + "\n".join(problems)
        )
    if not found:
        raise AssertionError(
            f"`{packages_dir}` holds zero resolvable packages -- an empty roster is a "
            f"broken checkout, and a roster check over nothing passes vacuously"
        )
    return found


def assert_bounds_roster_matches_disk(root: Path = REPO_ROOT) -> None:
    """Assert every package on disk has all four floors and an in-package hook.

    See ``THE ROSTER IS CROSS-CHECKED AGAINST DISK``. Without this, parity
    coverage is the intersection of two hand-maintained lists that nothing
    reconciles, and a package can join the workspace with neither -- staying
    green by being invisible.
    """
    on_disk = workspace_packages(root)
    problems: list[str] = []

    tables: tuple[tuple[str, frozenset[str], str], ...] = (
        (
            "MODULE_LOWER_BOUNDS",
            frozenset(MODULE_LOWER_BOUNDS),
            "its measured (client_min, aio_min) public-name floor",
        ),
        (
            "MODULE_COMPARED_LOWER_BOUNDS",
            frozenset(MODULE_COMPARED_LOWER_BOUNDS),
            "its measured floor on the number of module-level callables diffed",
        ),
        (
            "CLASS_LOWER_BOUNDS",
            frozenset(CLASS_LOWER_BOUNDS),
            "its measured (sync_min, async_min) Client/AsyncClient member floor, "
            "or (0, 0) WITH a stated reason if it has no class pair",
        ),
        (
            "CLASS_COMPARED_LOWER_BOUNDS",
            frozenset(CLASS_COMPARED_LOWER_BOUNDS),
            "its measured floor on the number of class members diffed",
        ),
    )
    for label, keys, what in tables:
        for missing in sorted(frozenset(on_disk) - keys):
            problems.append(
                f"  `{missing}` is in the workspace but absent from {label} -- add {what}"
            )
        for stale in sorted(keys - frozenset(on_disk)):
            problems.append(
                f"  `{stale}` has an entry in {label} but is not in the workspace -- "
                f"remove the stale floor rather than leaving it to rot"
            )

    for import_name, package_dir in sorted(on_disk.items()):
        hook = package_dir / _HOOK_RELATIVE_PATH
        if not hook.is_file():
            problems.append(
                f"  `{import_name}` has no in-package parity hook at "
                f"{hook.relative_to(root)} -- a floor with no test that calls it "
                f"asserts nothing"
            )

    if problems:
        raise AssertionError(
            "the parity roster and the workspace disagree:\n"
            + "\n".join(problems)
            + "\n  A package that enters or leaves the workspace must enter or leave the\n"
            "  bounds tables with it. Silence here is the omission-by-omission failure\n"
            "  mode this gate exists to prevent."
        )
