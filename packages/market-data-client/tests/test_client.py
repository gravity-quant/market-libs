"""Health (anónimo) + mapping de excepciones al dispatch (sync) — SC3.

Cubre el contrato observable del default sync ``Client`` para los endpoints
públicos ``GET /health`` y ``GET /health/feed`` (CORE-MD-01, anónimos) y el
mapping de status al nivel de dispatch (``_request``):

- Health path ANÓNIMO (Pitfall 4 / T-20-02): la request NO lleva header
  ``Authorization`` y NINGUNA request pega al token URL — health nunca dispara
  un grant.
- Health 401 (T-20-08): un 401 sobre un endpoint anónimo levanta
  ``MarketDataAuthError`` INMEDIATAMENTE, con CERO token POSTs — un health 401 es
  un error real, no una señal de token stale (el carve-out ``if not
  authenticated: raise`` corta antes del re-auth).
- Dispatch autenticado: 429 → ``MarketDataRateLimitError``; otro error →
  ``MarketDataAPIError`` (el mapping fino ya está unit-tested en Plan 02; acá se
  asserta una vez al nivel de dispatch).
"""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

import market_data_client
from market_data_client import (
    MarketDataAPIError,
    MarketDataAuthError,
    MarketDataRateLimitError,
    _core,
)

_BASE = "https://market-data-develop.test/api"
_TOKEN_URL = "https://auth.test/oauth/token"


def _token_posts(httpx_mock: HTTPXMock) -> list[object]:
    return [r for r in httpx_mock.get_requests() if str(r.url) == _TOKEN_URL and r.method == "POST"]


def test_get_health_anonymous(httpx_mock: HTTPXMock) -> None:
    """``get_health()`` devuelve el dict y despacha SIN Authorization ni token grant."""
    httpx_mock.add_response(url=f"{_BASE}/health", method="GET", json={"status": "ok"})

    assert market_data_client.get_health() == {"status": "ok"}

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    health_req = requests[0]
    assert health_req.url.path == "/api/health"
    # Pitfall 4: anónimo — sin Bearer, sin grant al token URL.
    assert "Authorization" not in health_req.headers
    assert _token_posts(httpx_mock) == []


def test_get_health_feed_anonymous(httpx_mock: HTTPXMock) -> None:
    """``get_health_feed()`` es igualmente anónimo sobre ``/health/feed``."""
    httpx_mock.add_response(url=f"{_BASE}/health/feed", method="GET", json={"status": "ok"})

    assert market_data_client.get_health_feed() == {"status": "ok"}

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    assert requests[0].url.path == "/api/health/feed"
    assert "Authorization" not in requests[0].headers
    assert _token_posts(httpx_mock) == []


def test_health_401_raises_auth_without_reauth(httpx_mock: HTTPXMock) -> None:
    """Un health 401 levanta ``MarketDataAuthError`` con CERO token POSTs (T-20-08)."""
    httpx_mock.add_response(url=f"{_BASE}/health", method="GET", status_code=401, text="nope")

    with pytest.raises(MarketDataAuthError):
        market_data_client.get_health()

    # No re-auth: el carve-out anónimo corta antes de cualquier grant.
    assert _token_posts(httpx_mock) == []


def test_authenticated_429_raises_rate_limit(httpx_mock: HTTPXMock) -> None:
    """Dispatch autenticado: 429 → ``MarketDataRateLimitError`` (D-14).

    El token sembrado por el conftest está fresco, así que ``_ensure_token()`` es
    no-op y no dispara grant. ``idempotent=False`` evita el retry loop del
    transport (429 sería retryable si fuese idempotente).
    """
    spec = _core.RequestSpec(
        method="GET", path="/data", idempotent=False, endpoint_name="data", authenticated=True
    )
    httpx_mock.add_response(url=f"{_BASE}/data", method="GET", status_code=429, text="slow down")

    with pytest.raises(MarketDataRateLimitError):
        market_data_client.client._get_default()._request(spec)


def test_authenticated_500_raises_api_error(httpx_mock: HTTPXMock) -> None:
    """Dispatch autenticado: otro status de error → ``MarketDataAPIError`` (D-14)."""
    spec = _core.RequestSpec(
        method="GET", path="/data", idempotent=False, endpoint_name="data", authenticated=True
    )
    httpx_mock.add_response(url=f"{_BASE}/data", method="GET", status_code=500, text="boom")

    with pytest.raises(MarketDataAPIError):
        market_data_client.client._get_default()._request(spec)


def test_configure_base_url_invalidates_cached_token() -> None:
    """WR-01: rotating ``base_url`` alone invalidates the cached token (sync).

    Mirrors the async surface (``aio.configure``) — the dual sync/async constraint
    requires both surfaces to invalidate on a ``base_url`` change. The conftest
    seeds a fresh token; a bare ``configure(base_url=...)`` must drop it.
    """
    client = market_data_client.client._get_default()
    assert client._state.token == "test-token"
    market_data_client.configure(base_url="https://market-data-other.test/api")
    assert client._state.token is None
    assert client._state.token_expires_at == 0.0


def test_configure_base_url_keeps_token_when_seeded() -> None:
    """WR-01: an explicit ``token`` override survives a ``base_url`` rotation."""
    client = market_data_client.client._get_default()
    market_data_client.configure(
        base_url="https://market-data-other.test/api",
        token="seeded",
        token_expires_at=9_999_999_999.0,
    )
    assert client._state.token == "seeded"
