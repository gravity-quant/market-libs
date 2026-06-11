"""Public-surface snapshot test (cross-package safety net).

Plan 06-01 Task 2 — REFAC-01 safety net BEFORE any per-package Client class
refactor (Plans 03-06). Enumerates the public API (``__all__`` symbols + kind
+ signature) of the 4 target packages, serializes to a deterministic text
format, and compares each line against a committed snapshot under
``verification/snapshots/<pkg-with-dashes>-surface.txt``.

Golden-file test contract (D-06, D-08, D-09, D-10, D-11):

- The snapshot files are the source of truth for the PRE-refactor public
  surface. Any drift caused by Wave 1 (per-package skeletons) shows up as
  a failing assertion and a forensic-localizable git diff.
- The test is strictly read-only — it never writes to the snapshot files.
- To accept an intentional surface change, run ``python
  verification/regen_snapshots.py`` (Plan 06-01 Task 3) and commit the diff
  alongside the source change that justifies it.

Snapshot file format (W3 pinning):

- First 8 lines each start with ``#``.
- Line 8 is exactly ``#`` alone (header/body separator).
- Body lines: ``<name> : <kind> : <signature>``, sorted alphabetically by
  ``name``. Terminating newline at end of file.
- ``kind`` is one of ``"class"``, ``"function"``, ``"coroutine"``,
  ``"module"``, or a type-name fallback (e.g. ``"_GenericAlias"`` for
  ``typing.Literal`` type aliases).
- ``signature`` is the ``str(inspect.signature(obj))`` value, or ``""``
  when ``inspect.signature`` raises ``TypeError``/``ValueError`` (RESEARCH.md
  Pitfall 9) or when ``kind`` is not callable.

Usage::

    uv run pytest verification/test_public_surface.py -q
"""

from __future__ import annotations

import importlib
import inspect
from pathlib import Path
from typing import Any

import pytest

_PACKAGES = [
    "ambito_financiero_client",
    "iol_client",
    "higyrus_client",
    "matriz_client",
]
_SNAPSHOT_DIR = Path(__file__).parent / "snapshots"
_HEADER_LINE_COUNT = 8


def _kind(obj: Any) -> str:
    """Return a stable, deterministic kind label for an object.

    Order matters: ``iscoroutinefunction`` is checked BEFORE ``isfunction``
    because async functions also satisfy ``isfunction`` (RESEARCH.md
    Pattern 5 adaptation note).
    """
    if inspect.isclass(obj):
        return "class"
    if inspect.iscoroutinefunction(obj):
        return "coroutine"
    if inspect.isfunction(obj) or inspect.ismethod(obj):
        return "function"
    if inspect.ismodule(obj):
        return "module"
    return type(obj).__name__


def _stringify_signature(obj: Any) -> str:
    """Wrap ``inspect.signature`` in try/except per RESEARCH.md Pitfall 9.

    Returns an empty string when the object is not introspectable (e.g.,
    builtins, ``typing.Literal`` aliases, C-implemented callables without
    a Python signature).
    """
    try:
        sig = inspect.signature(obj)
    except (TypeError, ValueError):
        return ""
    return str(sig)


def _enumerate_surface(pkg_name: str) -> list[str]:
    """Build the body lines for ``pkg_name``'s public surface snapshot.

    Returns one ``"<name> : <kind> : <signature>"`` line per name in
    ``sorted(getattr(pkg, "__all__", []))``. The list is the body of the
    snapshot file — the 8-line ``#`` header is NOT included here (it lives
    in the snapshot file and the regen script).
    """
    pkg = importlib.import_module(pkg_name)
    names = sorted(getattr(pkg, "__all__", []))
    lines: list[str] = []
    for name in names:
        obj = getattr(pkg, name)
        kind = _kind(obj)
        sig = _stringify_signature(obj) if kind in ("class", "function", "coroutine") else ""
        lines.append(f"{name} : {kind} : {sig}")
    return lines


def _snapshot_path(pkg_name: str) -> Path:
    """Map a Python module name to its snapshot file path.

    Uses dashes instead of underscores in the filename (e.g.
    ``iol_client`` → ``iol-client-surface.txt``) to mirror the package
    distribution name.
    """
    slug = pkg_name.replace("_", "-")
    return _SNAPSHOT_DIR / f"{slug}-surface.txt"


def _strip_header(expected: str, pkg_name: str) -> str:
    """Validate the 8-line header invariant and return the body.

    Asserts (W3 pinning):
    - Snapshot file has at least 8 lines.
    - First 8 lines each start with ``#``.
    - Line 8 is exactly ``#`` (no trailing text) — the header/body separator.

    Returns the substring after the 8-line header so the body can be
    compared against the enumerated public surface.
    """
    lines = expected.splitlines(keepends=True)
    assert len(lines) >= _HEADER_LINE_COUNT, (
        f"Snapshot for {pkg_name} has fewer than {_HEADER_LINE_COUNT} lines; "
        f"header invariant (W3) violated. Re-run "
        f"`python verification/regen_snapshots.py` to repair."
    )
    for i in range(_HEADER_LINE_COUNT):
        assert lines[i].startswith("#"), (
            f"Snapshot for {pkg_name} line {i + 1} does not start with '#'; "
            f"header invariant (W3) violated."
        )
    # Line 8 must be exactly `#` followed by a newline (no trailing text).
    assert lines[_HEADER_LINE_COUNT - 1].rstrip("\n") == "#", (
        f"Snapshot for {pkg_name} line 8 is "
        f"{lines[_HEADER_LINE_COUNT - 1]!r}, expected '#\\n' (header/body "
        f"separator). Header invariant (W3) violated."
    )
    return "".join(lines[_HEADER_LINE_COUNT:])


@pytest.mark.parametrize("pkg_name", _PACKAGES)
def test_public_surface_matches_snapshot(pkg_name: str) -> None:
    """Golden-file test: assert package public surface matches committed snapshot.

    Regenerate via ``python verification/regen_snapshots.py`` AFTER
    verifying the change is intentional (D-11). The header comment block
    is stripped before comparison, so editing the header content does not
    mask body drift — but the 8-line invariant is still validated (W3).
    """
    actual = "\n".join(_enumerate_surface(pkg_name)) + "\n"
    expected_full = _snapshot_path(pkg_name).read_text()
    expected_body = _strip_header(expected_full, pkg_name)
    assert actual == expected_body, (
        f"\nPublic surface of {pkg_name} drifted from snapshot at "
        f"{_snapshot_path(pkg_name)}.\n"
        f"Run `python verification/regen_snapshots.py` to refresh "
        f"AFTER verifying the change is intentional.\n"
    )
