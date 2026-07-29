"""Token lifecycle (async): fetch → cache → TTL-expiry re-fetch — AUTH-MD-01 / SC2.

Espejo async de ``test_token_lifecycle.py`` sobre el default ``AsyncClient``.
Ejerce el double-checked locking (D-12) vía ``await client._aensure_token()``:
el grant corre DENTRO del ``token_lock`` per-loop creado lazy (Pitfall 2). El
contrato observable es idéntico al sync — un único grant ``client_credentials``,
sin token de rotación (D-05); re-autenticar ES el refresh.

Pitfall 3: body idéntico entre fetches → assert por COUNT, no por ordering.
"""

from __future__ import annotations

from pytest_httpx import HTTPXMock

from market_data_client import aio

_TOKEN_URL = "https://auth.test/oauth/token"
_GRANT_BODY = b"grant_type=client_credentials&client_id=cid&client_secret=csec&audience=aud"


async def test_async_token_fetch_cache_then_refetch_on_ttl_expiry(httpx_mock: HTTPXMock) -> None:
    """Fetch inicial cachea el token; forzar la expiry dispara un segundo grant (async).

    Ejerce ``_aensure_token()`` (double-checked lock). Mismo contrato que el
    sync: 1 POST tras el primer fetch, 2 POST tras forzar ``token_expires_at=0.0``.
    """
    client = aio._get_default()
    state = client._state
    state.token = None
    state.token_expires_at = 0.0

    httpx_mock.add_response(
        url=_TOKEN_URL,
        method="POST",
        match_content=_GRANT_BODY,
        json={"access_token": "TOK-1", "token_type": "Bearer", "expires_in": 3600},
        is_reusable=True,
    )

    # 1) Fetch inicial → token cacheado + exactamente 1 POST al token URL.
    await client._aensure_token()
    assert state.token == "TOK-1"
    token_posts = [
        r for r in httpx_mock.get_requests() if str(r.url) == _TOKEN_URL and r.method == "POST"
    ]
    assert len(token_posts) == 1

    # 2) Simula el vencimiento del TTL → segundo grant bajo el double-checked lock.
    state.token_expires_at = 0.0
    await client._aensure_token()
    assert state.token == "TOK-1"
    token_posts = [
        r for r in httpx_mock.get_requests() if str(r.url) == _TOKEN_URL and r.method == "POST"
    ]
    assert len(token_posts) == 2


async def test_async_token_not_refetched_while_fresh(httpx_mock: HTTPXMock) -> None:
    """Un token fresco corta en el fast-path del double-checked lock (no grant)."""
    client = aio._get_default()
    state = client._state
    state.token = "FRESH-TOK"
    state.token_expires_at = 9_999_999_999.0

    await client._aensure_token()

    token_posts = [
        r for r in httpx_mock.get_requests() if str(r.url) == _TOKEN_URL and r.method == "POST"
    ]
    assert token_posts == []
    assert state.token == "FRESH-TOK"
