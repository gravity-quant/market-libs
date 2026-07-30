"""Health (anónimo) + mapping de excepciones al dispatch (async) — SC3.

Espejo async de ``test_client.py`` sobre el default ``AsyncClient``. El health
path es anónimo (sin Bearer, sin grant al token URL) y un health 401 levanta
``MarketDataAuthError`` sin re-auth (T-20-08). El mapping fino ya está
unit-tested en Plan 02; acá se asserta al nivel de dispatch async.
"""

from __future__ import annotations

import json as _json

import pytest
from pytest_httpx import HTTPXMock

from market_data_client import (
    LatestRequest,
    MarketDataAPIError,
    MarketDataAuthError,
    MarketDataRateLimitError,
    MarketDataSnapshot,
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


async def test_async_configure_base_url_invalidates_cached_token() -> None:
    """WR-01: rotating ``base_url`` alone invalidates the cached token (async).

    Mirrors the sync surface (``client.configure``). Before the fix, async
    ``configure(base_url=...)`` left the cached token intact — a dual sync/async
    divergence. The conftest seeds a fresh token; a bare rotation must drop it.
    """
    client = aio._get_default()
    assert client._state.token == "test-token"
    aio.configure(base_url="https://market-data-other.test/api")
    assert client._state.token is None
    assert client._state.token_expires_at == 0.0


async def test_async_configure_base_url_keeps_token_when_seeded() -> None:
    """WR-01: an explicit ``token`` override survives a ``base_url`` rotation."""
    client = aio._get_default()
    aio.configure(
        base_url="https://market-data-other.test/api",
        token="seeded",
        token_expires_at=9_999_999_999.0,
    )
    assert client._state.token == "seeded"


# ----------------------------------------------------------------------
# D-10 async 401 re-auth sequences (assert by COUNT — Pitfall 5)
# ----------------------------------------------------------------------


async def test_async_authenticated_401_reauths_once_then_succeeds(httpx_mock: HTTPXMock) -> None:
    """D-10 (async): authenticated 401 → clear token → re-auth ONCE → retry → 200.

    Mirrors the sync ``test_authenticated_401_reauths_once_then_succeeds``. The
    conftest seeds a fresh token, so the FIRST ``GET /marketdata`` dispatches with
    that Bearer and receives a 401. The async carve-out clears the cached token,
    re-runs the Auth0 grant EXACTLY ONCE (one token POST), then retries the SAME
    request with the fresh Bearer and gets the 200. Assert by COUNT.
    """
    httpx_mock.add_response(url=f"{_BASE}/marketdata", method="GET", status_code=401, text="stale")
    httpx_mock.add_response(
        url=_TOKEN_URL, method="POST", json={"access_token": "fresh-token", "expires_in": 3600}
    )
    httpx_mock.add_response(
        url=f"{_BASE}/marketdata",
        method="GET",
        json=[{"symbol": "GGAL", "marketId": "ROFX", "entries": []}],
    )

    result = await aio._get_default().get_market_data()

    assert len(result) == 1
    assert isinstance(result[0], MarketDataSnapshot)
    assert result[0].symbol == "GGAL"
    # Exactly one re-auth — no infinite loop, no double grant.
    assert len(_token_posts(httpx_mock)) == 1


async def test_async_authenticated_persistent_401_reraises_with_single_reauth(
    httpx_mock: HTTPXMock,
) -> None:
    """D-10 (async): a second consecutive 401 re-raises ``MarketDataAuthError`` (no loop).

    Two 401s in a row: the first triggers the exactly-once re-auth (one token
    POST); the retry also yields 401, so ``_raise_for_response`` on the second
    response re-raises — NO recursion, NO infinite re-auth (Pitfall 4). Assert
    the grant fired exactly once.
    """
    httpx_mock.add_response(url=f"{_BASE}/marketdata", method="GET", status_code=401, text="stale")
    httpx_mock.add_response(
        url=_TOKEN_URL, method="POST", json={"access_token": "fresh-token", "expires_in": 3600}
    )
    httpx_mock.add_response(url=f"{_BASE}/marketdata", method="GET", status_code=401, text="still")

    with pytest.raises(MarketDataAuthError):
        await aio._get_default().get_market_data()

    assert len(_token_posts(httpx_mock)) == 1


# ----------------------------------------------------------------------
# D-09 header precedence (async) — the token ALWAYS wins over spec.headers
# ----------------------------------------------------------------------


async def test_async_authenticated_token_wins_over_decoy_spec_header(
    httpx_mock: HTTPXMock,
) -> None:
    """D-09 (async): a decoy ``spec.headers['Authorization']`` NEVER shadows the token.

    Before the D-09 reorder the async header build was
    ``{"Authorization": f"Bearer {token}", **(spec.headers or {})}`` — the spec
    spread LAST, letting a stray ``Authorization`` in ``spec.headers`` shadow the
    fresh token (T-21-04-01, high severity). This test dispatches an
    authenticated ``RequestSpec`` carrying a decoy ``Authorization`` header and
    asserts the SENT ``Authorization`` equals the fresh conftest token — the
    regression that sync and async agree on (token spread LAST → wins).
    """
    spec = _core.RequestSpec(
        method="GET",
        path="/data",
        idempotent=False,
        endpoint_name="data",
        authenticated=True,
        headers={"Authorization": "Bearer DECOY-should-not-win", "X-Trace": "keep-me"},
    )
    httpx_mock.add_response(url=f"{_BASE}/data", method="GET", json={"ok": True})

    await aio._get_default()._request(spec)

    req = httpx_mock.get_requests()[0]
    assert req.headers["Authorization"] == "Bearer test-token"
    # Non-Authorization spec headers still ride along.
    assert req.headers["X-Trace"] == "keep-me"


# ----------------------------------------------------------------------
# End-to-end async read serialization — Bearer + param/body encoding
# ----------------------------------------------------------------------


async def test_async_get_market_data_sends_bearer_and_encodes_params(
    httpx_mock: HTTPXMock,
) -> None:
    """Async ``get_market_data`` injects the Bearer, drops ``None``, encodes bools.

    The fresh conftest token dispatches with no grant. Bool filters use httpx's
    native ``True → "true"`` / ``False → "false"`` encoding; ``None`` optionals
    are dropped from the query string.
    """
    httpx_mock.add_response(
        method="GET", json=[{"symbol": "GGAL", "marketId": "ROFX", "entries": []}]
    )

    result = await aio._get_default().get_market_data(
        market_id="ROFX", active=False, with_data=True, limit=10, prefix=None
    )

    assert len(result) == 1
    assert isinstance(result[0], MarketDataSnapshot)
    assert result[0].symbol == "GGAL"
    req = httpx_mock.get_requests()[0]
    assert req.headers["Authorization"] == "Bearer test-token"
    assert req.url.path == "/api/marketdata"
    assert req.url.params.get("market_id") == "ROFX"
    assert req.url.params.get("active") == "false"
    assert req.url.params.get("with_data") == "true"
    assert req.url.params.get("limit") == "10"
    assert "prefix" not in req.url.params


async def test_async_get_latest_sends_bearer_and_params(httpx_mock: HTTPXMock) -> None:
    """Async ``get_latest`` dispatches an authenticated ``GET /marketdata/latest``."""
    httpx_mock.add_response(
        method="GET", json=[{"symbol": "GGAL", "marketId": "ROFX", "entries": []}]
    )

    result = await aio._get_default().get_latest(symbol="GGAL")

    assert len(result) == 1
    assert result[0].symbol == "GGAL"
    req = httpx_mock.get_requests()[0]
    assert req.url.path == "/api/marketdata/latest"
    assert req.headers["Authorization"] == "Bearer test-token"
    assert req.url.params.get("symbol") == "GGAL"


async def test_async_get_latest_batch_sends_bearer_and_body(httpx_mock: HTTPXMock) -> None:
    """Async ``get_latest_batch`` POSTs the serialized ``LatestRequest`` with the Bearer."""
    httpx_mock.add_response(
        method="POST", json=[{"symbol": "GGAL", "marketId": "ROFX", "entries": []}]
    )

    latest_request = LatestRequest(symbols=["GGAL", "YPFD"], marketId="ROFX")
    result = await aio._get_default().get_latest_batch(latest_request)

    assert len(result) == 1
    req = httpx_mock.get_requests()[0]
    assert req.method == "POST"
    assert req.url.path == "/api/marketdata/latest"
    assert req.headers["Authorization"] == "Bearer test-token"
    assert _json.loads(req.content) == {"symbols": ["GGAL", "YPFD"], "marketId": "ROFX"}
