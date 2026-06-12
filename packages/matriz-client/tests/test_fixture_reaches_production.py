"""Guard test: configured sentinel token reaches the wire-level X-Auth-Token header.

This file is the Pitfall #1 safety net for ``matriz-client``: it proves that a sentinel
value pushed through ``matriz_client.configure(token=...)`` actually ends up in the
``X-Auth-Token: <sentinel>`` header of an outgoing httpx request. Note matriz uses
``X-Auth-Token``, NOT ``Authorization: Bearer`` (per the MATBA ROFEX Primary API spec).

Phase 06 Plan 06 migration (B3 — this plan exclusively owns this file in Wave 1):
``monkeypatch.setattr(pkg.client, "_token", sentinel, raising=False)`` was replaced
by ``matriz_client.configure(token=..., token_expires_at=...)``. The ``_token_ts``
field was renamed to ``token_expires_at`` (D-04) and is now part of the singleton
``_state`` dataclass instead of a module global.

The async guard at the bottom is a permanent ``pytest.skip`` pointing at Phase 10
REFAC-04 (matriz async REST surface + ``TokenStore``). Plan 06 ships a stub
``AsyncClient`` with lifecycle only (Open Q #1), so REST-level assertions still
need to wait for Phase 10.

See: .planning/phases/06-compat-safety-net-client-class-skeleton/06-RESEARCH.md
Pitfall #1 and Open Q #1 (matriz aio.py deferral).
"""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

import matriz_client


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


async def test_matriz_async_skipped_until_phase_10() -> None:
    """ASYNC: matriz async REST surface is deferred to Phase 10 REFAC-04.

    Plan 06 ships a stub ``AsyncClient`` (lifecycle only — ``__init__``/
    ``__aenter__``/``__aexit__``/``aclose``/``__repr__``). It has no REST
    methods (Open Q #1). The real async guard activates in Phase 10 once
    the matriz async REST surface lands on the ``TokenStore``. Keeping this
    test as a permanent ``pytest.skip`` gives a discoverable reminder in CI
    output (1 skipped + reason string).
    """
    pytest.skip(
        "matriz async REST surface is Phase 10 REFAC-04; "
        "stub AsyncClient ships in Plan 06 with no REST methods"
    )
