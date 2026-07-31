"""Async ``with_options(max_retries=N)`` shared-view-clone behavior (D-08).

Phase 21 Wave 4 (Plan 04) mirrors the sync ``test_with_options.py`` onto the
``aio.AsyncClient`` surface (CLAUDE.md dual sync/async constraint):

- **Retry propagation by request count (Pitfall 1 regression):** async
  ``with_options`` is a SILENT NO-OP unless ``req.extensions["max_attempts"] =
  _max_retries + 1`` is threaded into the async dispatch. This suite asserts the
  NUMBER of outgoing ``/marketdata`` requests equals ``max_retries + 1`` (assert
  by COUNT, not ordering — Pitfall 5), which can only pass if the extension is
  actually wired into BOTH ``_request`` and ``_send_auth_request``.
- **Shared-view-clone:** a view shares the parent ``_state`` (cached token +
  ``httpx.AsyncClient`` transport + the per-loop ``asyncio.Lock``s);
  ``view.aclose()`` is a no-op so it never tears down the parent's transport
  (anti-Pitfall 13).
- **Input validation:** invalid ``max_retries`` (negative / ``bool``) is rejected
  with ``ValueError`` BEFORE view construction (T-21-03-01 mitigation).

The default ``AsyncClient`` seeded by ``conftest`` carries a fresh (non-expiring)
token, so the authenticated ``/marketdata`` reads dispatch WITHOUT a token grant.
The inter-attempt backoff wait is neutralized by patching the transport's
``_retry_after_or_jitter_wait`` to ``tenacity.wait.wait_none`` so the retry loop
runs instantly (``await asyncio.sleep(0)``).
"""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock
from tenacity.wait import wait_none

from market_data_client import MarketDataAPIError, aio
from market_data_client import _atransport as _atransport_mod

_BASE = "https://market-data-develop.test/api"


@pytest.fixture(autouse=True)
def _no_backoff(monkeypatch: pytest.MonkeyPatch) -> None:
    """Neutralize the inter-attempt backoff so retry-count tests run instantly.

    The ``AsyncRetryTransport`` builds ``wait=_retry_after_or_jitter_wait()`` at
    construction; patching that factory to ``wait_none`` makes every awaited
    sleep ``asyncio.sleep(0)`` — the retry COUNT (the thing under test) is
    unaffected.
    """
    monkeypatch.setattr(_atransport_mod, "_retry_after_or_jitter_wait", wait_none)


async def test_async_with_options_retry_count_equals_max_retries_plus_one(
    httpx_mock: HTTPXMock,
) -> None:
    """D-08 / Pitfall 1: an async ``max_retries=5`` view issues EXACTLY 6 requests.

    Queue six transient ``503`` responses for ``GET /marketdata``; the view's
    per-call cap (``max_attempts = 5 + 1 = 6``) must drive exactly six outgoing
    requests before the exhausted retry surfaces as ``MarketDataAPIError``. If
    the ``max_attempts`` extension were NOT threaded into the async dispatch, the
    transport would fall back to the constructor default and this count would be
    wrong — the test IS the Pitfall-1 regression guard for the async surface.
    """
    for _ in range(6):
        httpx_mock.add_response(
            url=f"{_BASE}/marketdata", method="GET", status_code=503, text="down"
        )

    view = aio._get_default().with_options(max_retries=5)
    with pytest.raises(MarketDataAPIError):
        await view.get_market_data()

    marketdata_requests = [r for r in httpx_mock.get_requests() if r.url.path == "/api/marketdata"]
    assert len(marketdata_requests) == 6


async def test_async_with_options_max_retries_zero_issues_single_request(
    httpx_mock: HTTPXMock,
) -> None:
    """D-19: an async ``max_retries=0`` view issues EXACTLY 1 request (retries disabled)."""
    httpx_mock.add_response(url=f"{_BASE}/marketdata", method="GET", status_code=503, text="down")

    view = aio._get_default().with_options(max_retries=0)
    with pytest.raises(MarketDataAPIError):
        await view.get_market_data()

    marketdata_requests = [r for r in httpx_mock.get_requests() if r.url.path == "/api/marketdata"]
    assert len(marketdata_requests) == 1


async def test_async_with_options_shares_state_and_aclose_is_noop(httpx_mock: HTTPXMock) -> None:
    """D-08 / anti-Pitfall 13: view shares parent ``_state``; ``view.aclose()`` is a no-op.

    A view constructed via ``with_options`` shares the SAME ``_state`` object as
    its parent (incl. the cached ``httpx.AsyncClient``). Closing the view MUST
    NOT tear down the parent's transport — the parent stays usable afterward.
    """
    httpx_mock.add_response(url=f"{_BASE}/health", method="GET", json={"status": "ok"})
    httpx_mock.add_response(url=f"{_BASE}/health", method="GET", json={"status": "ok2"})

    client = aio._get_default()
    assert await client.get_health() == {"status": "ok"}
    parent_http = client._state.http_client
    assert parent_http is not None

    view = client.with_options(max_retries=5)
    assert view._state is client._state  # SHARED — no deep copy

    await view.aclose()  # MUST be a no-op
    assert client._state.http_client is parent_http
    assert client._state.http_client is not None  # parent's transport still open

    # Parent still usable after the view's aclose().
    assert await client.get_health() == {"status": "ok2"}


async def test_async_with_options_invalid_max_retries_raises_value_error() -> None:
    """T-21-03-01: negative / ``bool`` ``max_retries`` rejected BEFORE view construction."""
    client = aio._get_default()
    with pytest.raises(ValueError, match="max_retries"):
        client.with_options(max_retries=-1)
    with pytest.raises(ValueError, match="max_retries"):
        client.with_options(max_retries=True)
