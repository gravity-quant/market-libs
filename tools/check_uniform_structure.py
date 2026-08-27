#!/usr/bin/env python3
"""Uniform-structure gate for the workspace packages (Phase 31, TYP-03).

This repository has **no shared code between packages, by design**. Six packages
therefore evolve six independent file layouts, and the only thing that stops them
diverging over three releases is a committed gate. This script is the cheap half
of that gate: it asserts that every package under ``packages/`` carries both
``models.py`` and ``types.py`` inside its import root, so the next endpoint is
born with somewhere to live instead of inventing a new home per package.

Run it as::

    uv run python tools/check_uniform_structure.py

It exits non-zero and prints a ``::error::``-annotated line on any failure,
matching the convention of the ``decode-intactness`` gate it sits beside in the
``lint`` job of ``.github/workflows/ci.yml``. It reads the **filesystem only** and
never imports a package module, so no package import-time side effect (a
``load_dotenv()`` call, a network client construction) ever runs inside the gate.

WHY THIS IS A ``tools/`` SCRIPT IN THE ``lint`` JOB
===================================================

Two independent facts rule out the two obvious alternatives:

1. **It cannot live in the per-package ``test`` job.** The check is cross-package
   by nature -- its whole subject is the relationship *between* the six import
   roots. A per-package matrix leg sees one package and cannot state anything
   about the other five, let alone about a seventh appearing.
2. **It cannot live under ``verification/``.** The ``test`` job passes an explicit
   ``packages/${{ matrix.package }}`` path on the pytest command line, which
   overrides ``[tool.pytest.ini_options] testpaths``. That directory has
   consequently **never executed in CI**. A gate placed there would report
   nothing at all, which is strictly worse than no gate.

STDLIB-ONLY, ON PURPOSE
=======================

``pathlib`` and ``sys`` are the only imports (D-12). ``uv lock --check`` is the
first step of the ``lint`` job, and a third-party helper here would move
``uv.lock`` to buy nothing this check needs.

THE ROSTER COMES FROM DISK
==========================

There is deliberately **no hardcoded list of package names** in this file. The
roster is ``packages/`` enumerated at run time, so a seventh package entering the
workspace is checked automatically rather than silently exempted by omission
(criterion 4). For the same reason, a package whose ``src/<import_name>/``
directory cannot be resolved is reported as a **problem**, never skipped -- and an
empty scan is itself a problem, so this gate cannot report green vacuously.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# The two modules every package's import root must present. This is a list of
# MODULE names, not of package names -- the package roster is read from disk.
REQUIRED_MODULES = ("models.py", "types.py")

# Not a roster entry either: this is the suffix a build artifact takes when a
# package has been built in place, and filtering it keeps the import-root lookup
# below a single-candidate resolution. Every package NAME still comes from disk.
_BUILD_ARTIFACT_SUFFIX = ".egg-info"


class CheckFailure(Exception):
    """Raised by a check with a fully formed, operator-readable message."""


def _fail(message: str) -> CheckFailure:
    return CheckFailure(message)


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


def check_uniform_structure() -> str:
    """Assert both required modules exist in every package's import root."""
    problems: list[str] = []

    packages_dir = REPO_ROOT / "packages"
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
                f"{package_dir.relative_to(REPO_ROOT)}/src/"
            )
            continue
        for module in REQUIRED_MODULES:
            candidate = import_root / module
            if not candidate.is_file():
                problems.append(
                    f"    package `{package_dir.name}` is missing "
                    f"{candidate.relative_to(REPO_ROOT)}"
                )

    if problems:
        raise _fail("uniform structure is incomplete:\n" + "\n".join(problems))

    required = ", ".join(f"`{module}`" for module in REQUIRED_MODULES)
    return (
        f"uniform structure: all {len(package_dirs)} packages under `packages/` carry "
        f"{required} in their import root"
    )


def main() -> int:
    checks = (check_uniform_structure,)
    failures = 0
    for check in checks:
        try:
            print(check())
        except CheckFailure as exc:
            failures += 1
            print(f"::error::Phase 31 TYP-03 uniform structure -- {exc}", file=sys.stderr)
    if failures:
        print(
            f"::error::uniform-structure gate FAILED ({failures} of {len(checks)} checks)",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
