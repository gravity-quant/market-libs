#!/usr/bin/env python3
"""Surface-type gate for the workspace packages (Phase 32, GATE-TYP-01).

Every name a package exports through ``__all__`` is part of a published wheel's
contract. This gate scans that contract along **two dimensions**.

**Return types** (Phase 32, GATE-TYP-01). No exported name's return type may be
untyped: a return annotation mentioning ``Any`` -- bare, inside
``dict[str, Any]``, inside ``list[dict[str, Any]]``, inside ``... | None`` -- or
missing altogether is a violation, subject to the DT-06 exemptions listed below.

**Field types** (Phase 37, NOBJ-MTZ-01). No field declared in the body of an
exported class may be annotated as an untyped mapping. The predicate here is
deliberately **narrow** and is not the return dimension's: it walks the
annotation's MAPPING spine and nothing else, so a bare ``Any``, an
unparameterised mapping base, and a mapping whose value parameter recursively
matches all redden -- with the optional wrapper (all three spellings) stripped
first. ``list[Any]`` is spared on purpose, and survives the recursion because a
list is not a mapping and is never descended into. See
:func:`_field_annotation_is_untyped_mapping` and :data:`_FIELD_EXEMPTIONS`,
which holds the single declared field exemption.

The recursion, the unparameterised base, the quoted annotation and the
``Union[X, None]`` spelling were all added by the Phase 37 **code review**
(CR-02), which executed the predicate and measured four provable false
negatives against the contract stated in this paragraph -- including
``dict[str, dict[str, Any]]``, the exact container shape 37-03 introduced.

The second dimension exists because the first one was not enough, and the gap
was measured rather than suspected. **Before Phase 37** this gate printed::

    surface types: 6 packages, 183 `__all__` names, 330 definitions scanned,
    13 constant/alias exports, 23 exempted (dunder 13, private-helper 1,
    serialize-out 9), 0 violations

-- zero violations, while five ``dict[str, Any]`` fields sat on one package's
exported model surface. The cause was structural, not a missing exemption:
``_candidates_for`` filtered a class body down to its member functions and
discarded every ``ast.AnnAssign``, so the gate could not see the thing it was
being read as checking. **After Phase 37**, over a tree whose fields have since
been typed::

    surface types: 6 packages, 186 `__all__` names, 330 definitions scanned,
    442 fields scanned, 13 constant/alias exports, 24 exempted (dunder 13,
    private-helper 1, serialize-out 9, ws-catch-all 1), 0 violations

The same green, now earned: 442 fields inspected and one named exemption
absorbing a real hit. ``packages/matriz-client/tests/test_surface_types_red.py``
is what keeps it earned, exactly as its iol sibling does for the first
dimension.

Run it as::

    uv run python tools/check_surface_types.py

It exits non-zero and prints a ``::error::``-annotated line on any failure,
matching the convention of the ``decode-intactness`` and ``uniform-structure``
gates it sits beside in the ``lint`` job of ``.github/workflows/ci.yml``.

**This gate is a ratchet, not a migration tool.** The six packages' exported
surfaces are clean today (research simulated this exact scan over 319
definitions and found 0 non-exempt hits). Its entire value is that it fails the
day someone adds ``Client.get_x() -> dict[str, Any]``. That makes non-vacuity
the deliverable, which is why ``packages/iol-client/tests/test_surface_types_red.py``
proves the red path automatically instead of a SUMMARY asserting it by hand.

WHY THIS IS A ``tools/`` SCRIPT IN THE ``lint`` JOB
===================================================

Two independent facts rule out the two obvious alternatives:

1. **It cannot live in the per-package ``test`` job.** The check is cross-package
   by nature -- its subject is the relationship *between* the six import roots,
   and its counts are only meaningful in aggregate. A per-package matrix leg sees
   one package and cannot state anything about the other five, let alone about a
   seventh appearing.
2. **It cannot live under ``verification/``.** The ``test`` job passes an explicit
   ``packages/${{ matrix.package }}`` path on the pytest command line, which
   overrides ``[tool.pytest.ini_options] testpaths``. That directory has
   consequently **never executed in CI**. A gate placed there would report
   nothing at all, which is strictly worse than no gate.

**D-05, recorded here so it does not read as an unresolved contradiction.**
``ROADMAP.md:25`` describes this work as a "job de CI nuevo", while Phase 31's
locked D-12 fixes the "step en ``lint``" pattern for cross-package gates. The
D-lock wins over the roadmap-summary prose: this ships as a *step* of the
existing ``lint`` job. A further argument for that reading -- adding a step does
not rename the job, so no branch-protection required-check name moves.

STDLIB-ONLY, ON PURPOSE
=======================

``ast``, ``sys``, ``pathlib``, ``dataclasses`` and ``collections.abc`` are the
only imports (D-12). ``uv lock --check`` is the first step of the ``lint`` job,
and a third-party helper here would move ``uv.lock`` to buy nothing this check
needs.

The gate reads source as **text** and parses it with ``ast.parse``. It never
imports a package module and never calls ``eval``/``exec``: ``import <pkg>``
would run ``load_dotenv()`` and construct HTTP clients at import time, which both
existing gates forbid by name in their own docstrings. An unparseable file is a
failure, never a skip.

THE ROSTER COMES FROM DISK
==========================

There is deliberately **no hardcoded list of package names** in this file. The
roster is ``packages/`` enumerated at run time, so a seventh package entering the
workspace is scanned automatically rather than silently exempted by omission.
For the same reason a package whose ``src/<import_name>/`` directory cannot be
resolved, whose ``__init__.py`` declares no module-level ``__all__``, or whose
``__all__`` is not a literal, is reported as a **problem**, never skipped -- and
an empty scan is itself a problem, so this gate cannot report green vacuously.

THE ROOT IS INJECTABLE (D-04)
=============================

``REPO_ROOT`` is a **default argument value only**; the scan threads a ``root:
Path`` parameter through its whole body. This is the one deliberate departure
from ``check_uniform_structure.py`` and ``check_decode_intactness.py``, both of
which reference the module-level constant directly -- and it is precisely why
neither of them has a test. The seam is what lets the RED fixture inject a
synthetic broken tree under ``tmp_path`` and observe a real failure.

WHAT IS EXEMPT, AND WHAT DT-06 CLAUSE IS SUBSUMED
=================================================

Three exemptions, matching the measured taxonomy (13 dunder / 1 underscore /
9 ``to_dict`` across the six packages today):

- ``dunder`` -- ``__reduce__``, ``__deepcopy__`` and friends implement protocols
  whose signatures this repo does not own.
- ``private-helper`` -- any single-underscore-prefixed member. Reachable only as
  a *method* of an exported class; no ``__all__`` in any package contains an
  underscore-prefixed name.
- ``serialize-out`` -- exactly ``to_dict``. Projecting a typed model back to the
  wire shape is the one place an untyped mapping is the correct return type.

Research's simulation measured **22** hits (12 dunder) because it flagged only
annotations *containing* ``Any``. This gate also treats a **missing** return
annotation as untyped, which adds exactly one dunder hit today -- an exception
class's ``__init__``, legitimately unannotated because mypy infers ``None`` for
an ``__init__`` with annotated parameters. The 23rd exemption is therefore a
consequence of the stricter rule, not of a broader exemption predicate.

No package name is named in this file, here or anywhere else: the roster is read
from disk, and a prose mention would read as a hardcoded roster to anyone
grepping for one.

**OQ-2 resolution.** DT-06 also names an exemption for ``_request`` returning
``httpx.Response``. Under criterion 1's literal ``Any``-only rule that clause is
dead letter: no ``_request`` reachable from any ``__all__`` returns ``Any``, and
every module-level one is underscore-prefixed and absent from every ``__all__``.
It is therefore **subsumed by the underscore rule** rather than forgotten. If a
second rule banning raw transport types on the exported surface is ever wanted,
that is a scope addition, not a bug fix.

**A red gate is never resolved by weakening the gate.** ``_is_exempt`` must not
be broadened -- from ``to_dict`` to any ``to_*`` name, say, or the underscore
rule widened -- to silence a real violation. The fix is to type the return
properly, or to add an exemption here WITH a stated reason.

RESOLUTION IS TRANSITIVE, AND UNRESOLVED IS A PROBLEM (Phase 32 CR-01)
======================================================================

The first cut of this gate mapped each ``__all__`` name to the submodule the
``__init__.py`` imported it from, then looked for a matching top-level ``def`` or
``class`` in that one file. When nothing matched, **nothing was recorded and
nothing was reported** -- the one unresolvable condition in this file that was a
silent skip rather than a problem. Three reachable shapes hit it and scanned
GREEN with the offending return type in place:

1. **Alias re-export.** ``from pkg.client import Client as PkgClient`` binds
   ``PkgClient``, but ``client.py`` defines ``Client``. Fixed by carrying the
   *source* name (``alias.name``) alongside the bound name (``alias.asname``)
   through resolution, so the definition is looked up under the name it was
   actually defined with.
2. **Conditionally-defined export.** A ``def``/``class`` under
   ``if sys.version_info >= (3, 12):`` or inside ``try:`` is not in
   ``tree.body``. Fixed by ``_module_level_statements``, which flattens the
   module-level statement containers (``if`` / ``try`` / ``with`` / ``match``)
   without ever descending into a function body.
3. **``__all__ +=``.** ``ast.AugAssign`` was never handled and the first
   ``__all__`` binding won outright. ``_all_names`` now accumulates every
   ``__all__`` binding in the module, augmented or not, and a non-``Constant``
   element (``*models.__all__``) is a failure rather than a silent drop.

**Re-export chains are followed rather than reported.** ``matriz`` publishes two
constants through ``ws_client``, which itself only re-imports them from
``types``. Stopping at the first hop and calling that a problem would redden a
correct tree; stopping at the first hop and calling it a skip is the CR-01 bug.
So ``_resolve_binding`` follows intra-package ``ImportFrom`` hops (cycle-guarded,
``_MAX_RESOLUTION_HOPS`` deep) until it reaches the module that actually binds
the name. A chain that dead-ends -- a name a resolved module neither defines,
assigns, nor re-exports -- is a **problem**, never a skip, because an export the
gate cannot inspect is exactly the hole this section documents.

A name whose chain ends at a module-level *assignment* (a constant, a ``Literal``
alias, ``__version__``) is resolved-but-not-a-definition. It carries no return
annotation to check, so it contributes to ``assignments`` and to nothing else.
That is a stated outcome, not a silent one.
"""

from __future__ import annotations

import ast
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent  # default only -- see D-04 above

# Not a roster entry: this is the suffix a build artifact takes when a package
# has been built in place, and filtering it keeps the import-root lookup below a
# single-candidate resolution. Every package NAME still comes from disk.
_BUILD_ARTIFACT_SUFFIX = ".egg-info"

# The annotation token that makes an exported return type untyped. Matched
# structurally (``ast.Name`` id / ``ast.Attribute`` attr), never by substring on
# unparsed source, so ``Any``, ``t.Any``, ``dict[str, Any]``,
# ``list[dict[str, Any]]`` and ``Any | None`` are one predicate rather than five.
_ANY = "Any"

# The optional wrappers the FIELD predicate strips before matching. All THREE
# spellings are handled: the PEP 604 union (``X | None``), the legacy
# ``Optional[X]``, and ``Union[X, None]``. See
# ``_field_annotation_is_untyped_mapping``.
#
# Phase 37 code review, CR-02: only the first two were handled, so
# ``Union[dict[str, Any], None]`` -- the third legal spelling of the same thing
# -- passed the gate. That is precisely the ``| None`` one-token bypass
# ``_strip_optional``'s own docstring claimed to have closed. It also made the
# gate and the runtime disagree: ``models._strip_optional`` accepts
# ``typing.Union`` and always did.
_OPTIONAL = "Optional"
_UNION = "Union"

# The mapping bases the FIELD predicate recognises. ``dict`` is the only one in
# the tree today; the aliases are listed so the ratchet cannot be bypassed by
# spelling the same untyped mapping as ``Mapping[str, Any]``. Matched through
# ``_base_name``, so ``typing.Dict`` and ``collections.abc.Mapping`` are the same
# entry as their bare forms.
#
# Phase 37 code review, CR-02: ``defaultdict`` / ``DefaultDict`` / ``OrderedDict``
# joined the set for the same stated reason the abc aliases are here -- they are
# mappings that say exactly as little as ``dict`` about their values, so leaving
# them out left the bypass open under a different import.
_MAPPING_BASES = frozenset(
    {
        "dict",
        "Dict",
        "Mapping",
        "MutableMapping",
        "defaultdict",
        "DefaultDict",
        "OrderedDict",
    }
)

# ---------------------------------------------------------------------------
# THE ONE DECLARED FIELD EXEMPTION (Phase 37, D-01c)
# ---------------------------------------------------------------------------
#
# Keyed on the QUALIFIED ``Class.field`` name, never on the bare member name.
# That is the whole point: ``_is_exempt`` attributes by the *simple* name by its
# own documented design, so an entry for ``raw`` placed there would spare every
# member named ``raw`` in all six packages. This table is consulted first and
# holds exactly one entry.
#
# The entry is the WebSocket catch-all frame's raw payload. That class exists to
# preserve frames whose ``type`` this repo does not model, so callers can still
# inspect forward-compatible keys without losing information; its own docstring
# already carries that justification, and Phase 29's semantics matrix exempts it
# from the decode walker for the same reason. An untyped mapping is the correct
# annotation for a payload whose shape is by definition unknown -- this is the
# one place in the phase where that is true, and it is the phase's single
# declared exemption.
#
# BLAST-RADIUS NOTE (Phase 37 research finding F-9), recorded here rather than
# left to be rediscovered by a red CI run: an AST scan over every ``ClassDef``
# body in all six packages' ``src/`` trees found that the internal request-spec
# dataclass declares an optional untyped mapping field (``params``, and in three
# packages ``json_body``/``data`` as well) in EVERY one of them. Those fields
# match this predicate exactly. They are unreachable today for one reason only:
# that dataclass appears in no package's ``__all__``, and this gate resolves its
# candidates from the exported surface outward. Exporting it would turn all six
# packages red at once. Anyone who adds it to an ``__all__`` must re-check this
# gate first -- and the remedy is to type those fields, not to widen this table.
_FIELD_EXEMPTIONS: dict[str, str] = {
    "UnknownFrame.raw": "ws-catch-all",
}

# Depth limit for the intra-package re-export chase (see the CR-01 section of the
# module docstring). The deepest real chain in the workspace today is two hops
# (`__init__` -> `ws_client` -> `types`); this bound exists so a pathological or
# cyclic tree fails loudly instead of looping.
_MAX_RESOLUTION_HOPS = 8

#: The submodule label for the package's own ``__init__.py``.
_INIT = "__init__"


class CheckFailure(Exception):
    """Raised by a check with a fully formed, operator-readable message."""


def _fail(message: str) -> CheckFailure:
    return CheckFailure(message)


@dataclass(frozen=True, slots=True)
class ScanResult:
    """What one scan of a tree saw, in enough detail to prove it was not vacuous.

    ``exempted`` counts *hits* the exemptions absorbed -- definitions that would
    have been violations -- not every dunder or underscore member encountered.
    That is what makes it comparable to the measured baseline of 22.

    ``assignments`` counts exported names that resolved to a module-level
    *assignment* rather than to a ``def``/``class`` -- constants and ``Literal``
    aliases. They carry no return annotation, so they are reported as a stated
    outcome rather than absorbed into silence (Phase 32 CR-01).

    ``fields`` counts annotated field declarations found in the bodies of
    exported classes -- the second scanning dimension, added in Phase 37. It is
    a *scanned* count, not a hit count: it is the denominator that proves the
    dimension looked at something. Before Phase 37 this number did not exist and
    would have been 0, which is exactly how the gate reported green with five
    untyped mapping fields sitting on an exported surface.
    """

    packages: int
    all_names: int
    definitions: int
    fields: int
    assignments: int
    exempted: int
    exempted_by_reason: tuple[tuple[str, int], ...]
    violations: tuple[str, ...]


def _import_root(package_dir: Path) -> Path | None:
    """The single ``src/<import_name>/`` directory of a package, or ``None``.

    Resolved from disk rather than derived from the directory name: that is what
    makes ``ambito-financiero-client`` -> ``ambito_financiero_client`` correct
    without a mapping table that could go stale. ``None`` means "unresolvable",
    and the caller turns that into a problem line -- never into a skip.
    """
    src = package_dir / "src"
    if not src.is_dir():
        return None
    candidates = [
        child
        for child in sorted(src.iterdir())
        if child.is_dir() and not child.name.endswith(_BUILD_ARTIFACT_SUFFIX)
    ]
    if len(candidates) != 1:
        return None
    return candidates[0]


def _parse(path: Path) -> ast.Module:
    """``ast.parse`` a source file, turning any failure into a ``CheckFailure``.

    Never ``eval``/``exec``: the gate only ever reads the shape of the source.
    An unparseable file is a failure rather than a skip, because a gate that
    quietly ignores the file it cannot read is a gate that reports green on the
    exact tree it should redden.
    """
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:  # pragma: no cover - unreadable file in a clean tree
        raise _fail(f"cannot read `{path}`: {exc}") from exc
    try:
        return ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        raise _fail(f"cannot parse `{path}`: {exc}") from exc


def _module_level_statements(body: list[ast.stmt]) -> Iterator[ast.stmt]:
    """Yield ``body``'s statements, flattening module-level statement containers.

    A ``def`` or ``class`` guarded by ``if sys.version_info >= (3, 12):`` or
    written inside ``try: ... except ImportError:`` is still part of the exported
    surface, but it is not in ``tree.body``. Iterating ``tree.body`` alone is what
    made shape 2 of CR-01 invisible.

    Function and class *bodies* are deliberately NOT descended into here -- a
    nested helper is not module-level, and D-03 already scopes class members to
    the direct children of an exported class.
    """
    for node in body:
        yield node
        if isinstance(node, ast.If):
            yield from _module_level_statements(node.body)
            yield from _module_level_statements(node.orelse)
        elif isinstance(node, ast.With | ast.AsyncWith):
            yield from _module_level_statements(node.body)
        elif isinstance(node, ast.Try | ast.TryStar):
            yield from _module_level_statements(node.body)
            for handler in node.handlers:
                yield from _module_level_statements(handler.body)
            yield from _module_level_statements(node.orelse)
            yield from _module_level_statements(node.finalbody)
        elif isinstance(node, ast.Match):
            for case in node.cases:
                yield from _module_level_statements(case.body)


def _all_names(tree: ast.Module, label: str) -> list[str]:
    """Every module-level ``__all__`` string literal, or a ``CheckFailure``.

    A missing binding, or one whose value is not a list/tuple literal, is a
    problem: the gate cannot know what a package exports and must not guess that
    the answer is "nothing".

    **Every** ``__all__`` binding in the module is accumulated, not just the
    first, and ``ast.AugAssign`` (``__all__ += [...]``) counts as one -- that
    shape used to add names the gate then never scanned and never reported
    (CR-01 shape 3). A non-``Constant`` element (``*models.__all__``) is likewise
    a failure and not a silent drop: it makes the exported surface unreadable
    statically, which is the same class of problem as a non-literal ``__all__``.
    """
    names: list[str] = []
    found = False
    for node in _module_level_statements(tree.body):
        if isinstance(node, ast.Assign):
            targets: list[ast.expr] = list(node.targets)
        elif isinstance(node, ast.AnnAssign | ast.AugAssign):
            targets = [node.target]
        else:
            continue
        if not any(isinstance(target, ast.Name) and target.id == "__all__" for target in targets):
            continue
        value = node.value
        if not isinstance(value, ast.List | ast.Tuple):
            raise _fail(
                f"    package `{label}` declares `__all__` as something other than a "
                f"list/tuple literal -- the exported surface is not statically readable"
            )
        for element in value.elts:
            if not (isinstance(element, ast.Constant) and isinstance(element.value, str)):
                raise _fail(
                    f"    package `{label}` has a non-literal element in `__all__` "
                    f"(`{ast.unparse(element)}`) -- the exported surface is not "
                    f"statically readable"
                )
            names.append(element.value)
        found = True
    if not found:
        raise _fail(
            f"    package `{label}` has no module-level `__all__` -- a package with no "
            f"statically readable exported surface is a problem, never a skip"
        )
    return names


@dataclass(frozen=True, slots=True)
class _Binding:
    """Where one module-level name comes from.

    ``submodule`` is the intra-package submodule the name was imported from, or
    ``None`` when the name is bound in this module itself. ``source_name`` is the
    name to look up at the next hop -- it differs from the bound name exactly
    when an ``as`` alias is in play, which is CR-01 shape 1. ``node`` is set only
    for a local ``def``/``class``; a local assignment leaves it ``None``.
    """

    submodule: str | None
    source_name: str
    node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef | None


def _module_bindings(tree: ast.Module, import_name: str) -> dict[str, _Binding]:
    """Map every module-level name bound in ``tree`` to its :class:`_Binding`.

    ``ast.walk`` for the imports rather than a first-match-wins shortcut: matriz
    and higyrus each carry **two separate** ``ImportFrom`` blocks from
    ``.client``, and matriz imports from eight distinct submodules.

    ``alias.asname or alias.name`` is the *bound* name and ``alias.name`` is the
    *source* name; both are recorded, so ``from pkg.client import Client as C``
    resolves ``C`` to the ``ClassDef`` actually named ``Client`` instead of
    silently matching nothing.
    """
    bindings: dict[str, _Binding] = {}
    prefix = f"{import_name}."
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith(prefix):
            submodule = node.module[len(prefix) :]
            for alias in node.names:
                bindings[alias.asname or alias.name] = _Binding(
                    submodule=submodule, source_name=alias.name, node=None
                )
    for node in _module_level_statements(tree.body):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            bindings.setdefault(node.name, _Binding(None, node.name, node))
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    bindings.setdefault(target.id, _Binding(None, target.id, None))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            bindings.setdefault(node.target.id, _Binding(None, node.target.id, None))
    return bindings


def _is_exempt(name: str) -> str | None:
    """Return the DT-06 exemption reason for a member name, or ``None``.

    Attribution is by the **simple** member name, never the qualified
    ``Class.member`` form, so a method and a module-level function of the same
    name are exempted for the same stated reason.
    """
    if name.startswith("__") and name.endswith("__"):
        return "dunder"
    if name.startswith("_"):
        return "private-helper"
    if name == "to_dict":
        return "serialize-out"
    return None


def _annotation_mentions_any(annotation: ast.expr) -> bool:
    """Whether ``Any`` occurs anywhere in a return-annotation subtree."""
    for node in ast.walk(annotation):
        if isinstance(node, ast.Name) and node.id == _ANY:
            return True
        if isinstance(node, ast.Attribute) and node.attr == _ANY:
            return True
    return False


def _base_name(node: ast.expr) -> str | None:
    """The trailing identifier of ``Name``/``Attribute``, or ``None``.

    Collapses ``Any``/``t.Any``/``typing.Any`` and ``dict``/``typing.Dict``/
    ``collections.abc.Mapping`` to one comparison, structurally rather than by
    substring on unparsed source.
    """
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _is_any(node: ast.expr) -> bool:
    """Whether this annotation node *is* ``Any`` -- not merely mentions it."""
    return _base_name(node) == _ANY


def _is_none(node: ast.expr) -> bool:
    """Whether this annotation node is the ``None`` arm of an optional union."""
    if isinstance(node, ast.Constant) and node.value is None:
        return True
    return _base_name(node) == "None"


def _strip_optional(annotation: ast.expr) -> ast.expr:
    """Peel an optional wrapper off an annotation, or return it unchanged.

    ``X | None``, ``Optional[X]`` and ``Union[X, None]`` all yield ``X``.
    RESEARCH A2/F-9 asked for this explicitly: no exported field carries
    ``dict[str, Any] | None`` today, so the choice is unobservable on the real
    tree and only makes the ratchet stricter -- but leaving the hole open would
    have made ``| None`` a one-token bypass of the whole field dimension.

    Phase 37 code review, CR-02: the ``Union[X, None]`` arm was MISSING, so the
    claim in the paragraph above was false for the third spelling. The runtime
    counterpart ``matriz_client.models._strip_optional`` accepts
    ``typing.Union`` and always did, so gate and runtime disagreed on what
    "optional" means.

    A union with two non-``None`` arms is NOT an optional wrapper and is
    returned unchanged, so ``str | dict[str, Any]`` and
    ``Union[str, dict[str, Any]]`` are both judged on their own shape.
    """
    if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
        if _is_none(annotation.right):
            return _strip_optional(annotation.left)
        if _is_none(annotation.left):
            return _strip_optional(annotation.right)
        return annotation
    if isinstance(annotation, ast.Subscript) and _base_name(annotation.value) == _OPTIONAL:
        return _strip_optional(annotation.slice)
    if isinstance(annotation, ast.Subscript) and _base_name(annotation.value) == _UNION:
        arms = (
            annotation.slice.elts if isinstance(annotation.slice, ast.Tuple) else [annotation.slice]
        )
        non_none = [arm for arm in arms if not _is_none(arm)]
        if len(non_none) == 1:
            return _strip_optional(non_none[0])
    return annotation


def _field_annotation_is_untyped_mapping(annotation: ast.expr) -> bool:
    """Whether an exported class FIELD is annotated as an untyped mapping (D-01b).

    This is deliberately **not** :func:`_annotation_mentions_any`, the wide
    predicate the return dimension uses. It walks the annotation's own MAPPING
    spine and nothing else, and these shapes match once the optional wrapper is
    stripped:

    1. a bare ``Any`` -- the degenerate untyped surface;
    2. an unparameterised mapping base (``dict``, ``Mapping``, ...), which says
       strictly LESS than ``dict[str, Any]``;
    3. a two-parameter mapping subscript whose **value** parameter itself
       matches this predicate -- so ``dict[str, Any]``, ``dict[str, "Any"]`` and
       ``dict[str, dict[str, Any]]`` all match.

    Phase 37 code review, CR-02, which measured four provable false negatives
    against the docstring this replaces:

    - **the recursion** (shape 3). The predicate used to test only
      ``_is_any(parameters[1])``, so ``dict[str, dict[str, Any]]`` -- the exact
      container shape 37-03 introduced for ``DetailedPosition.report`` -- shipped
      green. Typing the outer level and leaving the inner one ``Any`` is the
      single most likely partial migration and was the single least caught.
    - **the bare base** (shape 2). The predicate required an ``ast.Subscript``,
      so a field annotated plain ``dict`` was spared while stating less than the
      shape that was caught. WR-02 covers what that spelling also does at runtime.
    - **quoted annotations**. ``payload: "dict[str, Any]"`` parses to
      ``ast.Constant``; ``_base_name`` answered ``None`` and the predicate
      short-circuited. Legal Python, ordinary for forward refs. The string is now
      re-parsed and judged; an UNPARSEABLE string is treated as a violation,
      because an annotation this gate cannot inspect is exactly what the gate
      exists to refuse.
    - **``Union[X, None]``**, handled one level down in :func:`_strip_optional`.

    Everything else is spared, and one case in particular is spared **on
    purpose**: ``list[Any]``. Widening this predicate to any mention of ``Any``
    would immediately redden two *exported* ``list[Any]`` fields in a package
    Phase 37 declared disjoint and out of scope. Ratchet discipline says a red
    gate is never resolved by weakening the gate; D-01b adds the corollary that
    an out-of-scope red is resolved by NARROWING this predicate, never by
    exempting the foreign field and never by editing the foreign package.

    **The recursion does not disturb that contract**, and the shape of the
    recursion is why: it descends ONLY through the value parameter of a mapping
    base. ``list[Any]`` is not a mapping, so it is not descended into and not
    matched -- neither at the top level nor as ``dict[str, list[Any]]``.
    ``test_a_list_of_any_field_is_spared_...`` still holds, and the real tree
    stays at ``0 violations``.

    The key parameter is not constrained to ``str``: the observed shape is
    string-keyed, but a mapping keyed by anything else says just as little about
    its values, and constraining the key would leave ``dict[int, Any]`` as a
    trivially reachable hole.
    """
    inner = _strip_optional(annotation)
    if isinstance(inner, ast.Constant) and isinstance(inner.value, str):
        try:
            inner = _strip_optional(ast.parse(inner.value, mode="eval").body)
        except SyntaxError:
            return True  # an uninspectable annotation is not a spared one
    if _is_any(inner):
        return True
    if isinstance(inner, ast.Name | ast.Attribute) and _base_name(inner) in _MAPPING_BASES:
        return True  # bare `dict` says less than `dict[str, Any]`
    if not isinstance(inner, ast.Subscript):
        return False
    if _base_name(inner.value) not in _MAPPING_BASES:
        return False
    parameters = inner.slice.elts if isinstance(inner.slice, ast.Tuple) else [inner.slice]
    return len(parameters) == 2 and _field_annotation_is_untyped_mapping(parameters[1])


def _module_path(import_root: Path, submodule: str) -> Path:
    """The file backing a dotted submodule name, preferring ``<name>.py``."""
    parts = submodule.split(".")
    flat = import_root.joinpath(*parts).with_suffix(".py")
    if flat.is_file():
        return flat
    return import_root.joinpath(*parts) / "__init__.py"


def _bindings_for(
    import_root: Path,
    submodule: str,
    cache: dict[str, dict[str, _Binding] | None],
) -> dict[str, _Binding] | None:
    """The module-level bindings of one submodule, or ``None`` if it has no file.

    Cached per package because the re-export chase revisits the same modules --
    matriz's eight submodules back 178 exported names.
    """
    if submodule not in cache:
        path = _module_path(import_root, submodule)
        cache[submodule] = (
            _module_bindings(_parse(path), import_root.name) if path.is_file() else None
        )
    return cache[submodule]


def _resolve_export(
    import_root: Path,
    package: str,
    name: str,
    cache: dict[str, dict[str, _Binding] | None],
) -> tuple[str, _Binding] | str:
    """Follow ``name`` from ``__init__`` to the module that actually binds it.

    Returns ``(submodule_label, binding)`` where ``binding.submodule is None``,
    or a fully formed problem line. **Every** unresolvable outcome returns a
    problem: a dead-ended chain, a missing file, a cycle, and an over-deep chain
    alike. There is deliberately no path through this function that returns
    "nothing to look at" -- that silent third outcome was CR-01.
    """
    module, current = _INIT, name
    seen = {(module, current)}
    for _ in range(_MAX_RESOLUTION_HOPS):
        bindings = _bindings_for(import_root, module, cache)
        if bindings is None:
            return (
                f"    package `{package}` resolves `{name}` to `{module}`, which has "
                f"no source file on disk"
            )
        binding = bindings.get(current)
        if binding is None:
            if module == _INIT:
                return (
                    f"    package `{package}` exports `{name}` but no import in "
                    f"`__init__.py` resolves it to a definition site"
                )
            return (
                f"    package `{package}` resolves `{name}` to `{module}`, which contains "
                f"no top-level definition, assignment or re-export of `{current}` -- an "
                f"export the gate cannot inspect is a problem, never a skip"
            )
        if binding.submodule is None:
            return module, binding
        step = (binding.submodule, binding.source_name)
        if step in seen:
            return (
                f"    package `{package}` resolves `{name}` through a cyclic re-export "
                f"chain that revisits `{binding.submodule}.{binding.source_name}`"
            )
        seen.add(step)
        module, current = step
    return (
        f"    package `{package}` resolves `{name}` through more than "
        f"{_MAX_RESOLUTION_HOPS} re-export hops -- the chain is unreadable, which is a "
        f"problem, never a skip"
    )


def _candidates_for(
    binding: _Binding,
) -> list[tuple[str, str, ast.FunctionDef | ast.AsyncFunctionDef]]:
    """The definitions one resolved export contributes to the scan.

    A function contributes itself. A class contributes its direct member
    functions (D-03: the likeliest regression is a method of an exported class,
    and a nested helper class is not part of the exported surface). Conditionally
    defined members are included via :func:`_module_level_statements`.
    """
    node = binding.node
    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
        return [(node.name, node.name, node)]
    if isinstance(node, ast.ClassDef):
        return [
            (f"{node.name}.{member.name}", member.name, member)
            for member in _module_level_statements(node.body)
            if isinstance(member, ast.FunctionDef | ast.AsyncFunctionDef)
        ]
    return []


def _adjudicate(
    qualified: str,
    member: str,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    package: str,
) -> tuple[str | None, str | None]:
    """Classify one candidate definition as ``(exemption_reason, violation)``.

    At most one element is non-``None``. A definition with **no** return
    annotation is a violation too: an unannotated exported return is exactly the
    untyped surface this ratchet exists to prevent.
    """
    annotation = node.returns
    if annotation is not None and not _annotation_mentions_any(annotation):
        return None, None
    reason = _is_exempt(member)
    if reason is not None:
        return reason, None
    if annotation is None:
        detail = "has no return annotation"
    else:
        detail = f"returns `{ast.unparse(annotation)}`"
    return None, f"    `{package}.{qualified}` {detail} on the exported surface"


def _field_candidates_for(binding: _Binding) -> list[tuple[str, str, ast.AnnAssign]]:
    """The annotated field declarations one resolved export contributes.

    The mirror image of :func:`_candidates_for`, and deliberately the same
    ``(qualified, simple, node)`` triple over the same
    :func:`_module_level_statements` traversal -- so a field declared under an
    ``if`` inside a class body is included for the same reason a conditionally
    defined method is (CR-01 shape 2).

    Only a class binding contributes fields. A function binding contributes
    none: a local annotated variable inside a function body is not on the
    exported surface, and :func:`_module_level_statements` never descends into
    a function body anyway.

    An ``AnnAssign`` whose target is not a plain name (``self.x: int``,
    ``obj.attr: int``) is skipped: it declares nothing on the class.
    """
    node = binding.node
    if not isinstance(node, ast.ClassDef):
        return []
    return [
        (f"{node.name}.{member.target.id}", member.target.id, member)
        for member in _module_level_statements(node.body)
        if isinstance(member, ast.AnnAssign) and isinstance(member.target, ast.Name)
    ]


def _adjudicate_field(
    qualified: str,
    member: str,
    node: ast.AnnAssign,
    package: str,
) -> tuple[str | None, str | None]:
    """Classify one candidate field as ``(exemption_reason, violation)``.

    The same two-slot contract as :func:`_adjudicate`, with two differences the
    field dimension forces:

    - The predicate is the NARROW :func:`_field_annotation_is_untyped_mapping`
      (D-01b), not the wide return predicate.
    - There is no "has no annotation" arm. An ``ast.AnnAssign`` carries an
      annotation by construction, so a field analogue of that branch would be
      unreachable code rather than a check.

    :data:`_FIELD_EXEMPTIONS` is consulted **before** :func:`_is_exempt`,
    because it is keyed on the qualified ``Class.field`` pair while
    ``_is_exempt`` attributes by the simple member name. Both reasons flow into
    the same ``exempted_by_reason`` accumulator, so an exemption that never
    absorbs a real hit is visible as a missing count rather than as silence.
    """
    if not _field_annotation_is_untyped_mapping(node.annotation):
        return None, None
    reason = _FIELD_EXEMPTIONS.get(qualified) or _is_exempt(member)
    if reason is not None:
        return reason, None
    detail = f"is annotated `{ast.unparse(node.annotation)}`"
    return None, f"    `{package}.{qualified}` {detail} on the exported surface"


def scan_surface_types(root: Path) -> ScanResult:
    """Scan every package under ``root/packages`` and report what was found.

    Structural problems (no ``packages/``, an empty roster, an unresolvable
    import root, a missing or non-literal ``__all__``, an unparseable file, a
    scan that resolved nothing) raise ``CheckFailure``. Surface-type violations
    are *returned* in the result so callers can inspect them; turning them into
    a failure is ``check_surface_types``'s job.
    """
    problems: list[str] = []
    violations: list[str] = []
    exempt_counts: dict[str, int] = {}
    all_names_total = 0
    definitions_total = 0
    fields_total = 0
    assignments_total = 0

    packages_dir = root / "packages"
    package_dirs: list[Path] = []
    if not packages_dir.is_dir():
        problems.append(
            "    there is no `packages/` directory to scan -- that is a broken "
            "checkout, not a clean tree"
        )
    else:
        package_dirs = [child for child in sorted(packages_dir.iterdir()) if child.is_dir()]
        if not package_dirs:
            problems.append(
                "    `packages/` holds zero package directories -- an empty scan is a "
                "broken checkout, not a clean tree"
            )

    for package_dir in package_dirs:
        import_root = _import_root(package_dir)
        if import_root is None:
            problems.append(
                f"    package `{package_dir.name}` has no resolvable import root -- "
                f"expected exactly one package directory under "
                f"{package_dir.name}/src/"
            )
            continue

        init_path = import_root / "__init__.py"
        if not init_path.is_file():
            problems.append(
                f"    package `{package_dir.name}` has no `__init__.py` in its import "
                f"root -- its exported surface is unreadable, which is a problem, "
                f"never a skip"
            )
            continue

        exported = _all_names(_parse(init_path), package_dir.name)
        all_names_total += len(exported)

        # Bindings are parsed once per submodule and reused across the whole
        # package: the re-export chase revisits the same handful of modules for
        # every one of the package's exported names.
        bindings_cache: dict[str, dict[str, _Binding] | None] = {}
        for name in exported:
            resolved = _resolve_export(import_root, package_dir.name, name, bindings_cache)
            if isinstance(resolved, str):
                problems.append(resolved)
                continue
            _, binding = resolved
            candidates = _candidates_for(binding)
            field_candidates = _field_candidates_for(binding)
            if not candidates and not field_candidates and binding.node is None:
                # Resolved to a module-level assignment: a constant or a
                # `Literal` alias. It has no return annotation to check, so it
                # is a stated outcome rather than a silent skip.
                assignments_total += 1
                continue

            definitions_total += len(candidates)
            for qualified_name, member_name, func_node in candidates:
                reason, violation = _adjudicate(
                    qualified_name, member_name, func_node, package_dir.name
                )
                if reason is not None:
                    exempt_counts[reason] = exempt_counts.get(reason, 0) + 1
                if violation is not None:
                    violations.append(violation)

            # The second dimension (Phase 37, D-01a). Adjudicated in the same
            # loop, against the same package label, into the same two
            # accumulators -- so a field violation and a return violation are
            # indistinguishable to every caller downstream of here.
            fields_total += len(field_candidates)
            for qualified_name, member_name, field_node in field_candidates:
                reason, violation = _adjudicate_field(
                    qualified_name, member_name, field_node, package_dir.name
                )
                if reason is not None:
                    exempt_counts[reason] = exempt_counts.get(reason, 0) + 1
                if violation is not None:
                    violations.append(violation)

    # Anti-vacuity: a scan that saw nothing must never read as a clean tree.
    if not problems:
        if all_names_total == 0:
            problems.append(
                "    zero `__all__` names resolved across the whole scan -- a surface "
                "with nothing on it is a broken checkout, not a clean tree"
            )
        elif definitions_total == 0 and fields_total == 0:
            # Phase 37 widened this guard from "zero definitions" to "zero of
            # EITHER dimension". Not a weakening: a package that exports only
            # dataclasses -- no methods at all -- was inspected, and reporting
            # it as a broken checkout would be false. The condition that still
            # has to fail loudly is a scan that inspected *nothing at all*.
            #
            # Worth naming for the same reason the definitions clause is: a
            # scan that reports zero fields across six packages of
            # dataclass-heavy model modules is a blind gate, not a clean tree.
            # That was literally the state of this file before Phase 37, and
            # the floor assertion in the RED fixture is what pins it now --
            # here it can only be a lower bound of one, because the synthetic
            # single-function trees the fixtures inject legitimately have none.
            problems.append(
                "    zero definitions and zero fields were scanned -- a gate that "
                "inspects nothing cannot report green"
            )

    if problems:
        raise _fail("surface-type scan could not complete:\n" + "\n".join(problems))

    return ScanResult(
        packages=len(package_dirs),
        all_names=all_names_total,
        definitions=definitions_total,
        fields=fields_total,
        assignments=assignments_total,
        exempted=sum(exempt_counts.values()),
        exempted_by_reason=tuple(sorted(exempt_counts.items())),
        violations=tuple(violations),
    )


def check_surface_types(root: Path = REPO_ROOT) -> str:
    """Assert nothing on the exported surface is untyped; report the counts."""
    result = scan_surface_types(root)

    if result.violations:
        raise _fail(
            "the exported surface has untyped returns or fields:\n" + "\n".join(result.violations)
        )

    taxonomy = ", ".join(f"{reason} {count}" for reason, count in result.exempted_by_reason)
    return (
        f"surface types: {result.packages} packages, {result.all_names} `__all__` names, "
        f"{result.definitions} definitions scanned, {result.fields} fields scanned, "
        f"{result.assignments} constant/alias exports, {result.exempted} exempted "
        f"({taxonomy or 'none'}), 0 violations"
    )


def main() -> int:
    checks = (check_surface_types,)
    failures = 0
    for check in checks:
        try:
            print(check())
        except CheckFailure as exc:
            failures += 1
            print(f"::error::Phase 32 GATE-TYP-01 surface types -- {exc}", file=sys.stderr)
    if failures:
        print(
            f"::error::surface-types gate FAILED ({failures} of {len(checks)} checks)",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
