"""Phase 6 Nyquist gap-fill tests.

Covers the three open questions from the Phase 6 validation audit
(2026-06-11) that had no dedicated pytest assertion:

  Q1 (task 6-04-02): W2 grep gate -- no legacy monkeypatch write sites
     exist in packages/iol-client/tests/test_client.py after the
     monkeypatch-migration landed in Plan 04. Without this test, someone
     could accidentally re-introduce a monkeypatch.setattr(_token, ...)
     write and the CI would not catch it.

  Q2 (task 6-01-03): Snapshot regen idempotency -- running regen_snapshots.py
     produces zero diff against the committed baselines. The Plan 07 CI gate
     runs this as a shell command; this test brings it into the pytest suite
     so it runs on every `uv run pytest -q` invocation.

  Q3 (task 6-01-04): Phase-06 baseline file has required keys (test_count
     and coverage_total). The Plan 01 Task 4 verify command is a bash one-
     liner; this test makes it a permanent pytest assertion.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent


def test_w2_iol_test_client_has_no_legacy_monkeypatch_write_sites() -> None:
    """Q1 (6-04-02): W2 migration permanent guard.

    Asserts that packages/iol-client/tests/test_client.py does not contain
    any legacy monkeypatch.setattr(..., "_token" / "_refresh_token" /
    "_password") write sites targeting the module-level state that no longer
    exists after Plan 04's refactor. State writes must go through
    iol_client.client._get_default()._state.<field> instead.
    """
    source = (_REPO_ROOT / "packages/iol-client/tests/test_client.py").read_text()
    bad_patterns = [
        'monkeypatch.setattr(iol_client.client, "_token"',
        "monkeypatch.setattr(iol_client.client, '_token'",
        'monkeypatch.setattr(iol_client.client, "_refresh_token"',
        "monkeypatch.setattr(iol_client.client, '_refresh_token'",
        'monkeypatch.setattr(iol_client.client, "_password"',
        "monkeypatch.setattr(iol_client.client, '_password'",
    ]
    for pat in bad_patterns:
        assert pat not in source, (
            f"Legacy monkeypatch write site found in packages/iol-client/tests/test_client.py:\n"
            f"  pattern: {pat!r}\n"
            "All state writes must go through "
            "iol_client.client._get_default()._state.<field> after Plan 04 migration."
        )


def test_snapshot_regen_is_idempotent() -> None:
    """Q2 (6-01-03): Regen idempotency as a self-enforcing pytest.

    Runs verification/regen_snapshots.py and asserts that the committed
    snapshot files are unchanged (git diff --exit-code exits 0). This
    catches unintentional public-surface drift that was regenerated but
    not committed, as well as regen script bugs that produce non-deterministic
    output.
    """
    regen = subprocess.run(
        ["uv", "run", "python", "verification/regen_snapshots.py"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert regen.returncode == 0, (
        f"regen_snapshots.py exited non-zero:\nstdout: {regen.stdout}\nstderr: {regen.stderr}"
    )
    diff = subprocess.run(
        ["git", "diff", "--exit-code", "verification/snapshots/"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert diff.returncode == 0, (
        "verification/snapshots/ drifted after running regen_snapshots.py.\n"
        "The snapshot files are NOT idempotent with the current public surface.\n"
        "Either:\n"
        "  (a) an intentional __all__ change was not committed with its snapshot, or\n"
        "  (b) the regen script produces non-deterministic output.\n"
        f"Diff:\n{diff.stdout}"
    )


def test_phase_06_baseline_has_required_keys() -> None:
    """Q3 (6-01-04): Phase 06 baseline file exists with required REFAC-01 keys.

    The REFAC-01 requirement demands test_count and coverage_total be
    recorded in the entry-baseline before any refactor. This test asserts
    those keys are present and non-empty so the baseline cannot silently
    regress to an empty or key-less state.
    """
    baseline_path = _REPO_ROOT / "verification/baselines/phase-06-baseline.txt"
    assert baseline_path.exists(), (
        f"Phase 06 baseline file missing at {baseline_path}. "
        "This file is required by REFAC-01 (B5) to anchor test_count and coverage%."
    )
    content = baseline_path.read_text()
    body_lines = [
        line
        for line in content.splitlines()
        if not line.startswith("#") and ":" in line and line.strip()
    ]
    keys_found = {line.split(":", 1)[0].strip() for line in body_lines}
    assert "test_count" in keys_found, (
        f"'test_count' key missing from {baseline_path}.\nKeys found: {keys_found}"
    )
    assert "coverage_total" in keys_found, (
        f"'coverage_total' key missing from {baseline_path}.\nKeys found: {keys_found}"
    )
    # Also verify the values are non-empty
    key_values = {
        line.split(":", 1)[0].strip(): line.split(":", 1)[1].strip() for line in body_lines
    }
    assert key_values.get("test_count", ""), "'test_count' value is empty in the baseline file."
    assert key_values.get("coverage_total", ""), (
        "'coverage_total' value is empty in the baseline file."
    )
