"""Guard test: a sentinel token configured via ``configure()`` reaches the wire-level
Authorization header.

This file is the Pitfall #1 safety net for ``higyrus-client``: it proves that a sentinel
value set via the new ``configure(token=..., token_expires_at=...)`` API actually ends up
in the ``Authorization: Bearer <sentinel>`` header of an outgoing httpx request, both
for the sync and async surfaces.

Phase 06 Plan 05 MIGRATED pattern: the legacy ``monkeypatch.setattr(pkg.client,
"_token", sentinel)`` no longer reaches per-instance state after the REFAC-02
restructure (Pitfall #1 — module dict writes don't hit ``_ClientState``).
This file owned exclusively by Plan 05 in Wave 1 (B3) and is rewritten to use
``higyrus_client.configure(token=...)`` / ``aio.configure(token=...)``.

See: .planning/phases/06-compat-safety-net-client-class-skeleton/06-RESEARCH.md
Pitfall #1, and 06-05-PLAN.md B3 ownership note.
"""

from __future__ import annotations

from pytest_httpx import HTTPXMock

import higyrus_client


def test_higyrus_sync_sentinel_token_reaches_authorization_header(
    httpx_mock: HTTPXMock,
) -> None:
    """SYNC: sentinel configurado vía ``configure(token=...)`` llega al Authorization header."""
    higyrus_client.configure(
        base_url="https://api.test",
        username="u",
        password="p",
        client_id="tenant",
        token="SYNC-sentinel-higyrus",
        token_expires_at=9_999_999_999.0,
    )

    httpx_mock.add_response(
        url="https://api.test/api/cuentas/listadoCuentas?estado=alta",
        json=[],
    )

    higyrus_client.get_listado_cuentas(estado="alta")

    [req] = httpx_mock.get_requests()
    assert req.headers["Authorization"] == "Bearer SYNC-sentinel-higyrus"


async def test_higyrus_async_sentinel_token_reaches_authorization_header(
    httpx_mock: HTTPXMock,
) -> None:
    """ASYNC: sentinel configurado vía ``aio.configure(token=...)`` llega al Authorization header."""
    from higyrus_client import aio

    aio.configure(
        base_url="https://api.test",
        username="u",
        password="p",
        client_id="tenant",
        token="ASYNC-sentinel-higyrus",
        token_expires_at=9_999_999_999.0,
    )

    httpx_mock.add_response(
        url="https://api.test/api/cuentas/listadoCuentas?estado=alta",
        json=[],
    )

    await aio.get_listado_cuentas(estado="alta")

    [req] = httpx_mock.get_requests()
    assert req.headers["Authorization"] == "Bearer ASYNC-sentinel-higyrus"
