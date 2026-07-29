"""Token lifecycle (sync): fetch → cache → TTL-expiry re-fetch — AUTH-MD-01 / SC2.

Auth0 ``client_credentials`` grant (D-05): re-autenticar ES el refresh (sin
token de rotación). Este módulo lockea el contrato observable end-to-end sobre
el default sync ``Client``:

1. Con ``token=None`` + ``token_expires_at=0.0`` un ``_ensure_token()`` dispara
   UN ``POST`` al ``auth0_token_url`` ABSOLUTO (Pitfall 1 — NO ``base_url``);
   el ``access_token`` queda cacheado en ``state.token``.
2. Forzando ``token_expires_at=0.0`` (simula el vencimiento del TTL) un segundo
   ``_ensure_token()`` dispara un SEGUNDO ``POST`` al token URL.

Pitfall 3: el body del grant es idéntico en ambos fetches (mismas credenciales)
→ se asserta por COUNT de requests, NO por ordering. El mock usa
``is_reusable=True`` para servir ambos POST.

Pitfall 4: el health path es anónimo (no dispara token) — NO se usa para
ejercer el flujo de auth.
"""

from __future__ import annotations

from pytest_httpx import HTTPXMock

import market_data_client

_TOKEN_URL = "https://auth.test/oauth/token"
# Dict-insertion order del grant (client.py/_core.build_token_request):
# grant_type, client_id, client_secret, audience.
_GRANT_BODY = b"grant_type=client_credentials&client_id=cid&client_secret=csec&audience=aud"


def test_token_fetch_cache_then_refetch_on_ttl_expiry(httpx_mock: HTTPXMock) -> None:
    """Fetch inicial cachea el token; forzar la expiry dispara un segundo grant.

    Seed: ``token=None`` + ``token_expires_at=0.0`` fuerza el fetch inicial.
    Wire: token grant 200 (``is_reusable=True``, ``match_content`` sobre el body
    client_credentials). Se asserta por COUNT (Pitfall 3): 1 POST tras el primer
    ``_ensure_token()``, 2 POST tras forzar ``token_expires_at=0.0`` y re-driver.
    """
    client = market_data_client.client._get_default()
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
    client._ensure_token()
    assert state.token == "TOK-1"
    token_posts = [
        r for r in httpx_mock.get_requests() if str(r.url) == _TOKEN_URL and r.method == "POST"
    ]
    assert len(token_posts) == 1

    # 2) Simula el vencimiento del TTL → segundo grant (re-auth ES el refresh).
    state.token_expires_at = 0.0
    client._ensure_token()
    assert state.token == "TOK-1"
    token_posts = [
        r for r in httpx_mock.get_requests() if str(r.url) == _TOKEN_URL and r.method == "POST"
    ]
    assert len(token_posts) == 2


def test_token_not_refetched_while_fresh(httpx_mock: HTTPXMock) -> None:
    """Un token fresco NO dispara un grant — ``_ensure_token()`` es no-op.

    Seed: token cacheado con expiry lejano (el conftest ya lo siembra, pero se
    fija explícito para self-containment — Pitfall 6). Con el token fresco, un
    ``_ensure_token()`` NO debe emitir ningún POST al token URL.
    """
    client = market_data_client.client._get_default()
    state = client._state
    state.token = "FRESH-TOK"
    state.token_expires_at = 9_999_999_999.0

    client._ensure_token()

    token_posts = [
        r for r in httpx_mock.get_requests() if str(r.url) == _TOKEN_URL and r.method == "POST"
    ]
    assert token_posts == []
    assert state.token == "FRESH-TOK"
