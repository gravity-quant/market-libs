"""Structural validation of CONFIRMED/FIXED → regression-test linkage (D-MATZ-28).

Reads ``.planning/verification/<pkg>-findings.md`` (the canonical findings file
maintained by :mod:`verification.findings.append_finding`) and verifies that
each finding in status ``CONFIRMED`` or ``FIXED`` references an existing
regression test via a ``Regression: <file>.py::<test_name>`` field.

The check is **structural** (regex over markdown + regex over the test file
text) — it does not import pytest, does not execute collection, and does not
import any client package. This means it can be invoked from any verification
driver (Phase 5+) regardless of which test plugins are installed.

Usage::

    from verification.cycle_report import verify_cycle_closure
    ok, missing_fids = verify_cycle_closure("matriz-client")
    if not ok:
        # emit ERROR-MAP finding listing the missing regression links

Return contract: ``(True, [])`` when nothing is wrong (including the case where
the findings file does not yet exist — there is nothing to validate). ``(False,
[fid, ...])`` listing the offending finding IDs otherwise.

Convention (forward-looking): drivers calling
:func:`verification.findings.append_finding` should populate the ``regression``
parameter as ``"<pkg>/tests/<file>.py::<test_name>"`` when marking a finding
``FIXED``. Findings without the field, or with paths pointing to nonexistent
files / tests, are reported as missing.
"""

from __future__ import annotations

import re
from pathlib import Path

from verification.findings import findings_path

__all__ = ["verify_cycle_closure"]

# Repo root = the directory containing the ``verification/`` package.
_REPO_ROOT = Path(__file__).resolve().parent.parent

# Strict regex for the regression field value: <relative-path>.py::<test_name>.
# Rejects absolute paths (no leading ``/``) and path-traversal components are
# additionally validated below (``..`` is not part of a valid Python identifier
# but could appear in a directory segment, e.g. ``foo/../bar/test.py``).
_REGRESSION_RE = re.compile(r"^([^:\s]+\.py)::([A-Za-z_][A-Za-z0-9_]*)$")

# Markdown parsing regexes for the structural finding scan.
_FINDING_BLOCK_HEADER_RE = re.compile(r"^### (F-[^\s]+)\b", re.MULTILINE)
_STATUS_RE = re.compile(r"\*\*Status:\*\*\s*`?(\w+)`?")
# Match a bullet like ``- **Regression:** packages/matriz-client/tests/test_client.py::test_x``
# or any prose that contains the same path::testname token.
_REGRESSION_BULLET_RE = re.compile(
    r"(?:Regression|regression)[^\n]*?([\w\-/.]+\.py::[A-Za-z_][\w]*)"
)


def _iter_findings(text: str) -> list[tuple[str, str, str | None]]:
    """Parse ``text`` (a findings markdown) into ``(fid, status, regression?)``.

    Strategy: split the ``## Detalle por hallazgo`` section into per-finding
    blocks using ``### F-NN`` headers, then extract ``**Status:**`` and an
    optional regression path from each block. Findings appearing only in the
    Index (without a detail block) are not returned because they have no
    Regression context anyway — the helper conservatively treats their status
    as ``OPEN`` (irrelevant to the CONFIRMED/FIXED filter).
    """
    # Find header positions.
    headers = list(_FINDING_BLOCK_HEADER_RE.finditer(text))
    out: list[tuple[str, str, str | None]] = []
    for idx, match in enumerate(headers):
        fid = match.group(1).strip()
        start = match.end()
        end = headers[idx + 1].start() if idx + 1 < len(headers) else len(text)
        block = text[start:end]

        status_match = _STATUS_RE.search(block)
        status = status_match.group(1).strip() if status_match else "OPEN"

        regression_match = _REGRESSION_BULLET_RE.search(block)
        regression: str | None = (
            regression_match.group(1).strip() if regression_match is not None else None
        )

        out.append((fid, status, regression))
    return out


def _regression_is_resolvable(regression: str | None) -> tuple[bool, Path | None, str | None]:
    """Validate ``regression`` syntactically and resolve it to a file path.

    Returns ``(ok, file_abs, test_name)``. ``ok`` is True only if:

    1. ``regression`` is not None.
    2. It matches :data:`_REGRESSION_RE` (no absolute path, no whitespace, ends
       in ``.py``, test name is a valid Python identifier).
    3. The relative path contains no ``..`` component (path-traversal defence
       per threat T-5-06).
    4. The resolved absolute path stays inside :data:`_REPO_ROOT`.
    """
    if not regression:
        return (False, None, None)
    match = _REGRESSION_RE.match(regression)
    if match is None:
        return (False, None, None)
    test_file_rel, test_name = match.group(1), match.group(2)

    rel_path = Path(test_file_rel)
    if rel_path.is_absolute() or ".." in rel_path.parts:
        return (False, None, None)

    test_file_abs = (_REPO_ROOT / rel_path).resolve()
    # Boundary safety: the resolved path must stay under _REPO_ROOT.
    try:
        test_file_abs.relative_to(_REPO_ROOT)
    except ValueError:
        return (False, None, None)

    return (True, test_file_abs, test_name)


def verify_cycle_closure(pkg: str) -> tuple[bool, list[str]]:
    """Return ``(ok, missing_fids)`` for the cycle-closure check on ``pkg``.

    Reads ``.planning/verification/<pkg>-findings.md`` and validates that
    every finding in status ``CONFIRMED`` or ``FIXED`` references an existing
    regression test via a ``Regression: <file>.py::<test_name>`` field where:

    - The path is relative to the repo root (no ``..``, not absolute).
    - The file exists on disk.
    - The file's text contains ``def <test_name>(`` (matches both ``def`` and
      ``async def`` via substring).

    Returns:
        ``(True, [])`` if every applicable finding is properly linked, or if
        the findings file does not exist (nothing to validate).
        ``(False, [fid, ...])`` listing finding IDs missing/broken regression
        links.
    """
    path = findings_path(pkg)
    if not path.exists():
        return (True, [])

    text = path.read_text(encoding="utf-8")
    missing: list[str] = []

    for fid, status, regression in _iter_findings(text):
        # Filter: only CONFIRMED and FIXED participate in the check.
        if status not in ("CONFIRMED", "FIXED"):
            continue

        ok, test_file_abs, test_name = _regression_is_resolvable(regression)
        if not ok or test_file_abs is None or test_name is None:
            missing.append(fid)
            continue

        if not test_file_abs.exists():
            missing.append(fid)
            continue

        content = test_file_abs.read_text(encoding="utf-8")
        # Match both ``def test_x(`` and ``async def test_x(`` via substring.
        if f"def {test_name}(" not in content:
            missing.append(fid)

    return (not missing, missing)
