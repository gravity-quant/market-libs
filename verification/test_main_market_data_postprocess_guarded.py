"""D-09 regression guard -- ``main_market_data.py`` post-request processing MUST
run INSIDE each probe's ``try`` so a file-I/O / JSON-parse / ``append_finding``
failure degrades to a finding/SKIP instead of an uncaught crash that flips
``main_verify.py`` to FAILED.

Locks the fix for the phase-23 verification gap (23-REVIEW.md CR-01 /
23-VERIFICATION.md D-09 gap): the SHAPE-diff (``_emit_shape``) and write-once
schema snapshot (``_write_schema_snapshot``) helpers do file I/O, ``json.loads``
on a committed baseline, and call ``append_finding`` (which raises ``ValueError``
on a multi-line, server-controlled title). Before the fix these ran AFTER the
probe's ``try/except``, so a corrupt baseline (``JSONDecodeError``), a disk error
(``OSError``), or a newline in a SHAPE title (``ValueError``) propagated uncaught
-> non-zero exit -> ``market-data-client`` classified FAILED, the exact outcome
D-09 forbids.

This AST gate walks every ``probe_*`` function in the driver and asserts that
every call to a post-processing helper is lexically enclosed in the ``body`` of a
``try`` block within that same function. The lower-bound assertion keeps the gate
non-vacuous: if the driver were gutted (helpers removed), the count drops below
the floor and the test FAILS RED rather than passing trivially.
"""

from __future__ import annotations

import ast
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DRIVER = "main_market_data.py"

# Post-request helpers that touch the filesystem, parse committed baselines, and
# emit findings from server-controlled data -- any of which can raise and MUST be
# caught by the enclosing probe's D-09 exception ladder.
_GUARDED_HELPERS = frozenset({"_emit_shape", "_write_schema_snapshot"})

# Non-vacuity floor: the migrated driver invokes these helpers many times across
# its read probes (health x2, market-data, latest, instruments, segments,
# symbols, calendar x2, both sync + async). A count below this means the driver
# was gutted and the guard would be meaningless -- fail RED instead.
_MIN_GUARDED_CALLS = 10


def _protected_call_ids(func: ast.FunctionDef | ast.AsyncFunctionDef) -> set[int]:
    """Return ids of every ``Call`` node inside the ``body`` of some ``try`` in ``func``.

    Only the protected ``try`` body counts -- calls in ``except``/``else``/``finally``
    are deliberately excluded, since a helper failure there is not caught by the
    probe's D-09 ladder.
    """
    protected: set[int] = set()
    for node in ast.walk(func):
        if isinstance(node, ast.Try):
            for stmt in node.body:
                for descendant in ast.walk(stmt):
                    if isinstance(descendant, ast.Call):
                        protected.add(id(descendant))
    return protected


def test_main_market_data_postprocess_is_try_guarded() -> None:
    """AST walk: every ``_emit_shape`` / ``_write_schema_snapshot`` call in a
    ``probe_*`` function lives inside a ``try`` body (D-09 never-FAILED contract)."""
    tree = ast.parse((_REPO_ROOT / _DRIVER).read_text(encoding="utf-8"))

    guarded_call_count = 0
    unguarded: list[tuple[str, str, int]] = []

    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        if not func.name.startswith("probe_"):
            continue
        protected = _protected_call_ids(func)
        for node in ast.walk(func):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            name = fn.id if isinstance(fn, ast.Name) else None
            if name not in _GUARDED_HELPERS:
                continue
            guarded_call_count += 1
            if id(node) not in protected:
                unguarded.append((func.name, name, node.lineno))

    assert not unguarded, (
        f"{_DRIVER}: post-processing helper call(s) OUTSIDE a try (D-09 violation) -- "
        f"a file-I/O / json.loads / append_finding failure would crash the driver to "
        f"FAILED instead of degrading to a finding: {unguarded}"
    )
    assert guarded_call_count >= _MIN_GUARDED_CALLS, (
        f"{_DRIVER}: found only {guarded_call_count} guarded post-processing call(s) "
        f"(expected >= {_MIN_GUARDED_CALLS}); the driver may have been gutted -- "
        f"this guard is non-vacuous by design."
    )
