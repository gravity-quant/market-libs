"""CR-02 -- main_matriz.py ``probe_login_sync`` returns 'FINDING' (not 'FAIL').

Pre-Phase-11, ``probe_login_sync`` returns ``ProbeResult.status='FAIL'`` on
auth failure (lines 411 + 428). The rest of the matriz driver uses 'FINDING'
for the equivalent diagnostic taxonomy (e.g. ``probe_get_segments`` ERROR-MAP
path, ``probe_error_bogus_symbol`` etc.). The inconsistency was flagged as
WR-02 / CR-02 in the code review.

Phase 11 CR-02 fix: change both return ProbeResult sites in
``probe_login_sync`` from 'FAIL' to 'FINDING'. The ``_auth_failed = True``
cascade-SKIPPED behaviour is preserved (downstream probes still skip on
auth failure).
"""

from __future__ import annotations

from pathlib import Path

import main_matriz
import pytest
from pytest_httpx import HTTPXMock

import matriz_client
from verification import findings as findings_module


@pytest.fixture(autouse=True)
def _isolate_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Aisla findings dir + reset state del driver entre tests."""
    monkeypatch.setattr(findings_module, "_FINDINGS_DIR", tmp_path)
    matriz_client.configure(
        base_url="https://api.test",
        username="user",
        password="pass",
    )
    main_matriz._auth_failed = False
    main_matriz._auth_failure_reason = ""
    main_matriz._fid_counter = 0
    yield
    main_matriz._auth_failed = False
    main_matriz._auth_failure_reason = ""


def test_probe_login_sync_returns_FINDING_on_authentication_error(
    httpx_mock: HTTPXMock,
) -> None:
    """Caso AuthenticationError (401): debe retornar status='FINDING', NO 'FAIL'."""
    httpx_mock.add_response(
        url="https://api.test/auth/getToken",
        method="POST",
        status_code=401,
    )
    result = main_matriz.probe_login_sync()
    assert result.name == "login_sync"
    assert result.status == "FINDING", (
        f"expected 'FINDING' for uniformity with driver taxonomy, got {result.status!r}"
    )
    # Cascade SKIPPED preserved.
    assert main_matriz._auth_failed is True


def test_probe_login_sync_returns_FINDING_on_unexpected_exception(
    httpx_mock: HTTPXMock,
) -> None:
    """Caso non-AuthenticationError: debe retornar status='FINDING', NO 'FAIL'.

    Un 500 con JSON malformado triggers el non-AuthenticationError path: la
    cliente lo mapea a PrimaryAPIError (no a AuthenticationError) y el except
    residual atrapa el caso. El fix debe homogeneizar ambos sites del probe.
    """
    httpx_mock.add_response(
        url="https://api.test/auth/getToken",
        method="POST",
        status_code=500,
        json={"status": "ERROR", "description": "internal server error"},
        is_reusable=True,
    )
    result = main_matriz.probe_login_sync()
    assert result.name == "login_sync"
    assert result.status == "FINDING", (
        f"expected 'FINDING' for uniformity with driver taxonomy, got {result.status!r}"
    )
    # Cascade SKIPPED preserved on the unexpected path too.
    assert main_matriz._auth_failed is True
