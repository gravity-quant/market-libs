"""Health (anónimo) + mapping de excepciones al dispatch (async) — SC3.

Espejo async de ``test_client.py`` sobre el default ``AsyncClient``. El health
path es anónimo (sin Bearer, sin grant al token URL) y un health 401 levanta
``MarketDataAuthError`` sin re-auth (T-20-08). El mapping fino ya está
unit-tested en Plan 02; acá se asserta al nivel de dispatch async.
"""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from market_data_client import (
    MarketDataAPIError,
    MarketDataAuthError,
    MarketDataRateLimitError,
    _core,
    aio,
)

_BASE = "https://market-data-develop.test/api"
_TOKEN_URL = "https://auth.test/oauth/token"


def _token_posts(httpx_mock: HTTPXMock) -> list[object]:
    return [r for r in httpx_mock.get_requests() if str(r.url) == _TOKEN_URL and r.method == "POST"]


async def test_async_get_health_anonymous(httpx_mock: HTTPXMock) -> None:
    """``aio.get_health()`` devuelve el dict y despacha SIN Authorization ni grant."""
    httpx_mock.add_response(url=f"{_BASE}/health", method="GET", json={"status": "ok"})

    assert await aio.get_health() == {"status": "ok"}

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    assert requests[0].url.path == "/api/health"
    assert "Authorization" not in requests[0].headers
    assert _token_posts(httpx_mock) == []


async def test_async_get_health_feed_anonymous(httpx_mock: HTTPXMock) -> None:
    """``aio.get_health_feed()`` es igualmente anónimo sobre ``/health/feed``."""
    httpx_mock.add_response(url=f"{_BASE}/health/feed", method="GET", json={"status": "ok"})

    assert await aio.get_health_feed() == {"status": "ok"}

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    assert requests[0].url.path == "/api/health/feed"
    assert "Authorization" not in requests[0].headers
    assert _token_posts(httpx_mock) == []


async def test_async_health_401_raises_auth_without_reauth(httpx_mock: HTTPXMock) -> None:
    """Un health 401 async levanta ``MarketDataAuthError`` con CERO token POSTs (T-20-08)."""
    httpx_mock.add_response(url=f"{_BASE}/health", method="GET", status_code=401, text="nope")

    with pytest.raises(MarketDataAuthError):
        await aio.get_health()

    assert _token_posts(httpx_mock) == []


async def test_async_authenticated_429_raises_rate_limit(httpx_mock: HTTPXMock) -> None:
    """Dispatch autenticado async: 429 → ``MarketDataRateLimitError`` (D-14)."""
    spec = _core.RequestSpec(
        method="GET", path="/data", idempotent=False, endpoint_name="data", authenticated=True
    )
    httpx_mock.add_response(url=f"{_BASE}/data", method="GET", status_code=429, text="slow down")

    with pytest.raises(MarketDataRateLimitError):
        await aio._get_default()._request(spec)


async def test_async_authenticated_500_raises_api_error(httpx_mock: HTTPXMock) -> None:
    """Dispatch autenticado async: otro status de error → ``MarketDataAPIError`` (D-14)."""
    spec = _core.RequestSpec(
        method="GET", path="/data", idempotent=False, endpoint_name="data", authenticated=True
    )
    httpx_mock.add_response(url=f"{_BASE}/data", method="GET", status_code=500, text="boom")

    with pytest.raises(MarketDataAPIError):
        await aio._get_default()._request(spec)
