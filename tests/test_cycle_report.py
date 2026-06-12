"""Regression tests for ``verification.cycle_report``.

This file lives in the repo-level ``tests/`` directory because
``verification/`` is a project-internal harness module — it is not a publishable
client package and has no per-package ``tests/`` folder of its own. The
``tests/`` testpath is registered in the root ``pyproject.toml``.

Cubre las regresiones de hallazgos del code review de Phase 5:

- CR-02 (Critical): ``_regression_is_resolvable`` + ``verify_cycle_closure`` no
  guardaban ``read_text(encoding="utf-8")`` contra ``OSError``. Un path
  controlado por el findings file que resolviera a un archivo existente pero
  no-leíble crasheaba el probe mid-summary y abortaba el driver.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import verification.cycle_report as cr_module
from verification.cycle_report import verify_cycle_closure


@pytest.fixture
def isolated_findings_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Redirect ``verification.cycle_report.findings_path`` to a tmp dir.

    Lets each test build its own ``<pkg>-findings.md`` without touching the real
    repo verification artifacts.
    """
    findings_dir = tmp_path / "verification"
    findings_dir.mkdir(parents=True)
    monkeypatch.setattr(cr_module, "findings_path", lambda pkg: findings_dir / f"{pkg}-findings.md")
    return findings_dir


def test_verify_cycle_closure_reports_missing_when_regression_file_is_unreadable(
    isolated_findings_dir: Path,
    tmp_path: Path,
) -> None:
    """Regression CR-02: read_text con OSError debe marcar la regresión como missing.

    Sin el ``try/except OSError`` en ``verify_cycle_closure``, una regression que
    resuelve a un archivo existente pero no-leíble (permisos retirados) corta el
    probe con un ``PermissionError`` no-mapeado y aborta el driver. Con el
    guard, el fid queda en la lista de missing — comportamiento equivalente al
    de un archivo inexistente.
    """
    if os.name == "nt":
        pytest.skip("permission-denied read_text path is POSIX-only")

    pkg_tests = tmp_path / "pkg" / "tests"
    pkg_tests.mkdir(parents=True)
    locked_file = pkg_tests / "test_locked.py"
    locked_file.write_text("def test_locked():\n    pass\n", encoding="utf-8")

    original_root = cr_module._REPO_ROOT
    cr_module._REPO_ROOT = tmp_path
    try:
        # Strip read permission. If running as root the read still succeeds; skip.
        os.chmod(locked_file, 0o000)
        try:
            locked_file.read_text(encoding="utf-8")
            pytest.skip("running as a user that can read despite mode 000 (e.g., root)")
        except PermissionError:
            pass

        findings_md = isolated_findings_dir / "pkg-findings.md"
        findings_md.write_text(
            "## Findings\n\n"
            "### F-01 -- something CONFIRMED\n"
            "**Class:** `ERROR-MAP` . **Surface:** `sync` . **Status:** `CONFIRMED`\n"
            "- Regression: pkg/tests/test_locked.py::test_locked\n",
            encoding="utf-8",
        )

        ok, missing = verify_cycle_closure("pkg")
        # The fid must be marked missing because the file cannot be read —
        # the OSError guard converts the permission failure into a missing
        # entry instead of letting it propagate.
        assert ok is False
        assert missing == ["F-01"]
    finally:
        # Restore permissions so tmp_path cleanup works.
        os.chmod(locked_file, 0o644)
        cr_module._REPO_ROOT = original_root


def test_verify_cycle_closure_passes_when_regression_file_is_readable(
    isolated_findings_dir: Path,
    tmp_path: Path,
) -> None:
    """Baseline (positive control): readable regression file with matching ``def`` → PASS.

    Verifies the happy path is unchanged after the CR-02 guard. Without this
    control, the regression above could pass trivially if the helper always
    returned ``ok=False``.
    """
    pkg_tests = tmp_path / "pkg" / "tests"
    pkg_tests.mkdir(parents=True)
    test_file = pkg_tests / "test_ok.py"
    test_file.write_text("def test_envelope_check():\n    pass\n", encoding="utf-8")

    original_root = cr_module._REPO_ROOT
    cr_module._REPO_ROOT = tmp_path
    try:
        findings_md = isolated_findings_dir / "pkg-findings.md"
        findings_md.write_text(
            "## Findings\n\n"
            "### F-01 -- something CONFIRMED\n"
            "**Class:** `ERROR-MAP` . **Surface:** `sync` . **Status:** `CONFIRMED`\n"
            "- Regression: pkg/tests/test_ok.py::test_envelope_check\n",
            encoding="utf-8",
        )

        ok, missing = verify_cycle_closure("pkg")
        assert ok is True
        assert missing == []
    finally:
        cr_module._REPO_ROOT = original_root
