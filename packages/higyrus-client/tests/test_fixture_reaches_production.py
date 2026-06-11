"""Guard test: monkeypatched sentinel token reaches the wire-level Authorization header.

This file is the Pitfall #1 safety net for ``higyrus-client``: it proves that a sentinel
value written to the legacy module-level ``_token`` state actually ends up in the
``Authorization: Bearer <sentinel>`` header of an outgoing httpx request.

Phase 06 Plan 02 LEGACY pattern: this file uses ``monkeypatch.setattr(pkg.client,
"_token", sentinel, raising=False)`` against the PRE-refactor code. Plan 05 (higyrus)
will migrate this file in-place to ``higyrus_client.configure(token=...)``. The
expiry field is ``_token_ts`` in pre-refactor code; Plan 05 renames it to
``token_expires_at`` and this file's monkeypatch target updates accordingly.

See: .planning/phases/06-compat-safety-net-client-class-skeleton/06-RESEARCH.md Pitfall #1.
"""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

import higyrus_client


def test_higyrus_sync_sentinel_token_reaches_authorization_header(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SYNC: sentinel monkeypatched onto ``_token`` reaches the Authorization header."""
    monkeypatch.setattr(higyrus_client.client, "_token", "SYNC-sentinel-higyrus", raising=False)
    monkeypatch.setattr(higyrus_client.client, "_token_ts", 9_999_999_999.0, raising=False)

    httpx_mock.add_response(
        url="https://api.test/api/cuentas/listadoCuentas?estado=alta",
        json=[],
    )

    higyrus_client.get_listado_cuentas(estado="alta")

    [req] = httpx_mock.get_requests()
    assert req.headers["Authorization"] == "Bearer SYNC-sentinel-higyrus"


async def test_higyrus_async_sentinel_token_reaches_authorization_header(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ASYNC: sentinel monkeypatched onto ``aio._token`` reaches the Authorization header."""
    from higyrus_client import aio

    monkeypatch.setattr(aio, "_token", "ASYNC-sentinel-higyrus", raising=False)
    monkeypatch.setattr(aio, "_token_ts", 9_999_999_999.0, raising=False)

    httpx_mock.add_response(
        url="https://api.test/api/cuentas/listadoCuentas?estado=alta",
        json=[],
    )

    await aio.get_listado_cuentas(estado="alta")

    [req] = httpx_mock.get_requests()
    assert req.headers["Authorization"] == "Bearer ASYNC-sentinel-higyrus"
