"""Guard test: ``configure(token=...)`` reaches the wire-level Authorization header.

This file is the Pitfall #1 safety net for ``iol-client``: it proves that a
sentinel value injected via ``iol_client.configure(token=...)`` (sync) and
``aio.configure(token=...)`` (async) actually ends up in the
``Authorization: Bearer <sentinel>`` header of an outgoing httpx request.

Phase 06 Plan 04 MIGRATED pattern: this file was previously using
``monkeypatch.setattr(pkg.client, "_token", sentinel, raising=False)``
(Plan 02 LEGACY pattern). Plan 04 (this plan) migrates it in-place to the
``configure(token=...)`` pattern as part of the per-package refactor commit.
The legacy pattern would silently land on the module dict after the
Client-class refactor (the PEP 562 shim is read-only by spec) — the
configure() pattern reaches ``_default_client._state.token``, which is
what the production read path consults.

B3 ownership: this plan owns this file exclusively in Wave 1. No other
plan in Wave 1 touches it.

See: .planning/phases/06-compat-safety-net-client-class-skeleton/06-RESEARCH.md Pitfall #1.
"""

from __future__ import annotations

from pytest_httpx import HTTPXMock

import iol_client
from iol_client import aio


def test_iol_sync_sentinel_token_reaches_authorization_header(httpx_mock: HTTPXMock) -> None:
    """SYNC: sentinel injected via ``configure(token=...)`` reaches the Authorization header."""
    iol_client.configure(
        base_url="https://api.test",
        username="u",
        password="p",
        token="SYNC-sentinel-iol",
        token_expires_at=9_999_999_999.0,
    )

    httpx_mock.add_response(
        url="https://api.test/api/v2/argentina/Titulos/Cotizacion/Instrumentos",
        json={"instrumentos": []},
    )

    iol_client.get_instruments("argentina")

    [req] = httpx_mock.get_requests()
    assert req.headers["Authorization"] == "Bearer SYNC-sentinel-iol"


async def test_iol_async_sentinel_token_reaches_authorization_header(httpx_mock: HTTPXMock) -> None:
    """ASYNC: sentinel injected via ``aio.configure(token=...)`` reaches the Authorization header."""
    aio.configure(
        base_url="https://api.test",
        username="u",
        password="p",
        token="ASYNC-sentinel-iol",
        token_expires_at=9_999_999_999.0,
    )

    httpx_mock.add_response(
        url="https://api.test/api/v2/argentina/Titulos/Cotizacion/Instrumentos",
        json={"instrumentos": []},
    )

    await aio.get_instruments("argentina")

    [req] = httpx_mock.get_requests()
    assert req.headers["Authorization"] == "Bearer ASYNC-sentinel-iol"
