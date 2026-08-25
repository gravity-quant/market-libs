#!/usr/bin/env python3
"""Surface-type gate for the workspace packages (Phase 32, GATE-TYP-01).

Every name a package exports through ``__all__`` is part of a published wheel's
contract. This gate asserts that no such name's *return type* is untyped: a
return annotation mentioning ``Any`` -- bare, inside ``dict[str, Any]``, inside
``list[dict[str, Any]]``, inside ``... | None`` -- or missing altogether is a
violation, subject to the DT-06 exemptions listed below.

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

``ast``, ``sys``, ``pathlib`` and ``dataclasses`` are the only imports (D-12).
``uv lock --check`` is the first step of the ``lint`` job, and a third-party
helper here would move ``uv.lock`` to buy nothing this check needs.

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
"""

from __future__ import annotations

import ast
import sys
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
    """

    packages: int
    all_names: int
    definitions: int
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


def _all_names(tree: ast.Module, label: str) -> list[str]:
    """The module-level ``__all__`` string literals, or a ``CheckFailure``.

    A missing binding, or one whose value is not a list/tuple literal, is a
    problem: the gate cannot know what a package exports and must not guess that
    the answer is "nothing".
    """
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets: list[ast.expr] = list(node.targets)
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        for target in targets:
            if not (isinstance(target, ast.Name) and target.id == "__all__"):
                continue
            value = node.value
            if not isinstance(value, ast.List | ast.Tuple):
                raise _fail(
                    f"    package `{label}` declares `__all__` as something other than a "
                    f"list/tuple literal -- the exported surface is not statically readable"
                )
            return [
                element.value
                for element in value.elts
                if isinstance(element, ast.Constant) and isinstance(element.value, str)
            ]
    raise _fail(
        f"    package `{label}` has no module-level `__all__` -- a package with no "
        f"statically readable exported surface is a problem, never a skip"
    )


def _definition_sites(tree: ast.Module, import_name: str) -> dict[str, str]:
    """Map each name bound in ``__init__.py`` to the submodule that defines it.

    ``ast.walk`` rather than a first-match-wins shortcut: matriz and higyrus each
    carry **two separate** ``ImportFrom`` blocks from ``.client``, and matriz
    imports from eight distinct submodules.

    Names defined directly in ``__init__.py`` (a ``def``, a ``class``, or a
    module-level assignment such as ``__version__``) resolve to ``__init__``
    itself, so a locally-bound export is resolved rather than reported missing.
    """
    sites: dict[str, str] = {}
    prefix = f"{import_name}."
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith(prefix):
            submodule = node.module[len(prefix) :]
            for alias in node.names:
                sites[alias.asname or alias.name] = submodule
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            sites.setdefault(node.name, "__init__")
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    sites.setdefault(target.id, "__init__")
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            sites.setdefault(node.target.id, "__init__")
    return sites


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


def _module_path(import_root: Path, submodule: str) -> Path:
    """The file backing a dotted submodule name, preferring ``<name>.py``."""
    parts = submodule.split(".")
    flat = import_root.joinpath(*parts).with_suffix(".py")
    if flat.is_file():
        return flat
    return import_root.joinpath(*parts) / "__init__.py"


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

        init_tree = _parse(init_path)
        exported = _all_names(init_tree, package_dir.name)
        all_names_total += len(exported)
        sites = _definition_sites(init_tree, import_root.name)

        by_submodule: dict[str, set[str]] = {}
        for name in exported:
            submodule = sites.get(name)
            if submodule is None:
                problems.append(
                    f"    package `{package_dir.name}` exports `{name}` but no import in "
                    f"`__init__.py` resolves it to a definition site"
                )
                continue
            by_submodule.setdefault(submodule, set()).add(name)

        for submodule, wanted in sorted(by_submodule.items()):
            module_path = _module_path(import_root, submodule)
            if not module_path.is_file():
                problems.append(
                    f"    package `{package_dir.name}` resolves an export to "
                    f"`{submodule}`, which has no source file on disk"
                )
                continue
            module_tree = init_tree if module_path == init_path else _parse(module_path)

            candidates: list[tuple[str, str, ast.FunctionDef | ast.AsyncFunctionDef]] = []
            for node in module_tree.body:
                if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                    if node.name in wanted:
                        candidates.append((node.name, node.name, node))
                elif isinstance(node, ast.ClassDef) and node.name in wanted:
                    # D-03: the likeliest regression is a method of an exported
                    # class, not a module-level function. Direct children only --
                    # a nested helper class is not part of the exported surface.
                    for member in node.body:
                        if isinstance(member, ast.FunctionDef | ast.AsyncFunctionDef):
                            candidates.append((f"{node.name}.{member.name}", member.name, member))

            definitions_total += len(candidates)
            for qualified_name, member_name, func_node in candidates:
                reason, violation = _adjudicate(
                    qualified_name, member_name, func_node, package_dir.name
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
        elif definitions_total == 0:
            problems.append(
                "    zero definitions were scanned -- a gate that inspects nothing "
                "cannot report green"
            )

    if problems:
        raise _fail("surface-type scan could not complete:\n" + "\n".join(problems))

    return ScanResult(
        packages=len(package_dirs),
        all_names=all_names_total,
        definitions=definitions_total,
        exempted=sum(exempt_counts.values()),
        exempted_by_reason=tuple(sorted(exempt_counts.items())),
        violations=tuple(violations),
    )


def check_surface_types(root: Path = REPO_ROOT) -> str:
    """Assert no exported name returns an untyped value; report the counts."""
    result = scan_surface_types(root)

    if result.violations:
        raise _fail("the exported surface has untyped returns:\n" + "\n".join(result.violations))

    taxonomy = ", ".join(f"{reason} {count}" for reason, count in result.exempted_by_reason)
    return (
        f"surface types: {result.packages} packages, {result.all_names} `__all__` names, "
        f"{result.definitions} definitions scanned, {result.exempted} exempted "
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
