"""Sync ``with_options(max_retries=N)`` shared-view-clone behavior (D-08).

Phase 21 Wave 3 (Plan 03) mirrors the iol Phase-13 ``with_options`` view:

- **Retry propagation by request count (Pitfall 1 regression):** ``with_options``
  is a SILENT NO-OP unless ``req.extensions["max_attempts"] = _max_retries + 1``
  is threaded into the dispatch. This suite asserts the NUMBER of outgoing
  ``/marketdata`` requests equals ``max_retries + 1`` (assert by COUNT, not
  ordering — Pitfall 5), which can only pass if the extension is actually wired.
- **Shared-view-clone:** a view shares the parent ``_state`` (cached token +
  ``httpx.Client`` transport); ``view.close()`` is a no-op so it never tears
  down the parent's transport (anti-Pitfall 13).
- **Input validation:** invalid ``max_retries`` (negative / ``bool``) is rejected
  with ``ValueError`` BEFORE view construction (T-21-03-01 mitigation).

The default ``Client`` seeded by ``conftest`` carries a fresh (non-expiring)
token, so the authenticated ``/marketdata`` reads dispatch WITHOUT a token grant.
"""

from __future__ import annotations

import time

import pytest
from pytest_httpx import HTTPXMock

import market_data_client
from market_data_client import MarketDataAPIError

_BASE = "https://market-data-develop.test/api"


def test_with_options_retry_count_equals_max_retries_plus_one(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D-08 / Pitfall 1: a ``max_retries=5`` view issues EXACTLY 6 requests.

    Queue six transient ``503`` responses for ``GET /marketdata``; the view's
    per-call cap (``max_attempts = 5 + 1 = 6``) must drive exactly six outgoing
    requests before the exhausted retry surfaces as ``MarketDataAPIError``. If
    the ``max_attempts`` extension were NOT threaded, the transport would fall
    back to the constructor default and this count would be wrong — the test
    IS the Pitfall-1 regression guard.
    """
    monkeypatch.setattr(time, "sleep", lambda *_a, **_k: None)
    for _ in range(6):
        httpx_mock.add_response(
            url=f"{_BASE}/marketdata", method="GET", status_code=503, text="down"
        )

    view = market_data_client.client._get_default().with_options(max_retries=5)
    with pytest.raises(MarketDataAPIError):
        view.get_market_data()

    marketdata_requests = [
        r for r in httpx_mock.get_requests() if r.url.path == "/api/marketdata"
    ]
    assert len(marketdata_requests) == 6


def test_with_options_max_retries_zero_issues_single_request(httpx_mock: HTTPXMock) -> None:
    """D-19: a ``max_retries=0`` view issues EXACTLY 1 request (retries disabled)."""
    httpx_mock.add_response(url=f"{_BASE}/marketdata", method="GET", status_code=503, text="down")

    view = market_data_client.client._get_default().with_options(max_retries=0)
    with pytest.raises(MarketDataAPIError):
        view.get_market_data()

    marketdata_requests = [
        r for r in httpx_mock.get_requests() if r.url.path == "/api/marketdata"
    ]
    assert len(marketdata_requests) == 1


def test_with_options_shares_state_and_close_is_noop(httpx_mock: HTTPXMock) -> None:
    """D-08 / anti-Pitfall 13: view shares parent ``_state``; ``view.close()`` is a no-op.

    A view constructed via ``with_options`` shares the SAME ``_state`` object as
    its parent (incl. the cached ``httpx.Client``). Closing the view MUST NOT
    tear down the parent's transport — the parent stays usable afterward.
    """
    httpx_mock.add_response(url=f"{_BASE}/health", method="GET", json={"status": "ok"})
    httpx_mock.add_response(url=f"{_BASE}/health", method="GET", json={"status": "ok2"})

    client = market_data_client.client._get_default()
    assert client.get_health() == {"status": "ok"}
    parent_http = client._state.http_client
    assert parent_http is not None

    view = client.with_options(max_retries=5)
    assert view._state is client._state  # SHARED — no deep copy

    view.close()  # MUST be a no-op
    assert client._state.http_client is parent_http
    assert client._state.http_client is not None  # parent's transport still open

    # Parent still usable after the view's close().
    assert client.get_health() == {"status": "ok2"}


def test_with_options_invalid_max_retries_raises_value_error() -> None:
    """T-21-03-01: negative / ``bool`` ``max_retries`` rejected BEFORE view construction."""
    client = market_data_client.client._get_default()
    with pytest.raises(ValueError, match="max_retries"):
        client.with_options(max_retries=-1)
    with pytest.raises(ValueError, match="max_retries"):
        client.with_options(max_retries=True)
