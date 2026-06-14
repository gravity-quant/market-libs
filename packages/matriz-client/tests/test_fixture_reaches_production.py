"""Guard test: configured sentinel token reaches the wire-level X-Auth-Token header.

This file is the Pitfall #1 safety net for ``matriz-client``: it proves that a sentinel
value pushed through ``matriz_client.configure(token=...)`` (or
``matriz_client.aio.configure(token=...)``) actually ends up in the
``X-Auth-Token: <sentinel>`` header of an outgoing httpx request. Note matriz uses
``X-Auth-Token``, NOT ``Authorization: Bearer`` (per the MATBA ROFEX Primary API spec).

Phase 06 Plan 06 migration (B3 — this plan exclusively owns this file in Wave 1):
``monkeypatch.setattr(pkg.client, "_token", sentinel, raising=False)`` was replaced
by ``matriz_client.configure(token=..., token_expires_at=...)``. The ``_token_ts``
field was renamed to ``token_expires_at`` (D-04) and is now part of the singleton
``_state`` dataclass instead of a module global.

Phase 10 Plan 10-04 — REFAC-04 + LIVE-02 closure: the async guard below is FLIPPED
from a permanent ``pytest.skip`` to an active wire-level assertion. ``matriz_client.aio``
ships a full REST surface (Plan 10-02 AsyncClient + 22 module-level async delegators)
backed by the 3-way TokenStore (Plan 10-03). The async wire path is now exercised by
the same Pitfall #1 sentinel idiom used by the sync guard above.

See: .planning/phases/06-compat-safety-net-client-class-skeleton/06-RESEARCH.md
Pitfall #1 (sync surface) and .planning/phases/10-matriz-aio-py-creation-tokenstore/
10-CONTEXT.md (async surface promotion).
"""

from __future__ import annotations

from pytest_httpx import HTTPXMock

import matriz_client
from matriz_client import aio


def test_matriz_sync_sentinel_token_reaches_x_auth_token_header(
    httpx_mock: HTTPXMock,
) -> None:
    """SYNC: sentinel pushed via ``configure(token=...)`` reaches the X-Auth-Token header."""
    matriz_client.configure(
        base_url="https://api.test",
        username="test-user",
        password="test-pass",
        token="SYNC-sentinel-matriz",
        token_expires_at=9_999_999_999.0,
    )

    httpx_mock.add_response(
        url="https://api.test/rest/segment/all",
        json={"status": "OK", "segments": []},
    )

    matriz_client.get_segments()

    [req] = httpx_mock.get_requests()
    assert req.headers["X-Auth-Token"] == "SYNC-sentinel-matriz"


async def test_matriz_async_sentinel_token_reaches_x_auth_token_header(
    httpx_mock: HTTPXMock,
) -> None:
    """ASYNC: sentinel pushed via ``aio.configure(token=...)`` reaches the X-Auth-Token header.

    Phase 10 Plan 10-04 (REFAC-04 + LIVE-02 closure): the async surface mirrors the
    sync wire path — the configured token MUST appear verbatim in the outgoing
    ``X-Auth-Token`` header. Mirror of the sync sentinel test above.
    """
    aio.configure(
        base_url="https://api.test",
        username="test-user",
        password="test-pass",
        token="ASYNC-sentinel-matriz",
        token_expires_at=9_999_999_999.0,
    )

    httpx_mock.add_response(
        url="https://api.test/rest/segment/all",
        json={"status": "OK", "segments": []},
    )

    await aio.get_segments()

    [req] = httpx_mock.get_requests()
    assert req.headers["X-Auth-Token"] == "ASYNC-sentinel-matriz"
