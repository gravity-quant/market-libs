"""Guard test: monkeypatched sentinel token reaches the wire-level X-Auth-Token header.

This file is the Pitfall #1 safety net for ``matriz-client``: it proves that a sentinel
value written to the legacy module-level ``_token`` state actually ends up in the
``X-Auth-Token: <sentinel>`` header of an outgoing httpx request. Note matriz uses
``X-Auth-Token``, NOT ``Authorization: Bearer`` (per the MATBA ROFEX Primary API spec).

Phase 06 Plan 02 LEGACY pattern: this file uses ``monkeypatch.setattr(pkg.client,
"_token", sentinel, raising=False)`` against the PRE-refactor code. Plan 06 (matriz)
will migrate this file in-place to ``matriz_client.configure(token=...)`` and rename
``_token_ts`` to ``token_expires_at``.

The async guard at the bottom is a permanent ``pytest.skip`` pointing at Phase 10
REFAC-04 (matriz aio.py + TokenStore). When Plan 06 ships the stub ``AsyncClient``,
the skip stays; only Phase 10 removes it once the real async path exists.

See: .planning/phases/06-compat-safety-net-client-class-skeleton/06-RESEARCH.md Pitfall #1
and Open Q #1 (matriz aio.py deferral).
"""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

import matriz_client


def test_matriz_sync_sentinel_token_reaches_x_auth_token_header(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SYNC: sentinel monkeypatched onto ``_token`` reaches the X-Auth-Token header."""
    monkeypatch.setattr(matriz_client.client, "_token", "SYNC-sentinel-matriz", raising=False)
    monkeypatch.setattr(matriz_client.client, "_token_ts", 9_999_999_999.0, raising=False)

    httpx_mock.add_response(
        url="https://api.test/rest/segment/all",
        json={"status": "OK", "segments": []},
    )

    matriz_client.get_segments()

    [req] = httpx_mock.get_requests()
    assert req.headers["X-Auth-Token"] == "SYNC-sentinel-matriz"
