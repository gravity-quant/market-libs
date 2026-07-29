"""Retry transport tests — Retry-After honoring without double-wait (WR-05).

Before the fix both transports slept for ``Retry-After`` INSIDE the attempt and
then let ``tenacity.wait_exponential_jitter`` add its own inter-attempt sleep —
the two delays stacked. The fix folds ``Retry-After`` into a shared tenacity
``wait`` strategy (``_retry_after_or_jitter_wait``) so exactly one sleep happens
between attempts: the server-directed delay when present (capped), else jitter.

The wait strategy is the single shared point between the sync and async
transports, so the unit tests below cover BOTH surfaces; the sync integration
test additionally proves the strategy is actually wired into ``RetryTransport``.
"""

from __future__ import annotations

import time

import httpx
import pytest
from pytest_httpx import HTTPXMock
from tenacity import Future, RetryCallState

import market_data_client
from market_data_client._transport import (
    _RETRY_AFTER_CAP_S,
    _retry_after_or_jitter_wait,
    _RetryableStatus,
)

_BASE = "https://market-data-develop.test/api"
_DUMMY_REQUEST = httpx.Request("GET", "http://t")


def _retry_state_with(exc: BaseException | None) -> RetryCallState:
    """Build a ``RetryCallState`` whose last outcome failed with ``exc``."""
    rcs = RetryCallState(retry_object=None, fn=None, args=(), kwargs={})  # type: ignore[arg-type]
    fut: Future = Future(attempt_number=1)
    if exc is not None:
        fut.set_exception(exc)
    else:
        fut.set_result(None)
    rcs.outcome = fut
    return rcs


# ----------------------------------------------------------------------
# _retry_after_or_jitter_wait — shared strategy (covers sync + async)
# ----------------------------------------------------------------------


def test_wait_returns_retry_after_when_present() -> None:
    """A ``_RetryableStatus.retry_after`` is honored verbatim (below the cap)."""
    wait = _retry_after_or_jitter_wait()
    resp = httpx.Response(503, request=_DUMMY_REQUEST)
    delay = wait(_retry_state_with(_RetryableStatus(resp, retry_after=5.0)))
    assert delay == 5.0


def test_wait_caps_retry_after() -> None:
    """A ``Retry-After`` above the 60 s cap is clamped to the cap."""
    wait = _retry_after_or_jitter_wait()
    resp = httpx.Response(503, request=_DUMMY_REQUEST)
    delay = wait(_retry_state_with(_RetryableStatus(resp, retry_after=999.0)))
    assert delay == _RETRY_AFTER_CAP_S


def test_wait_falls_back_to_jitter_when_no_retry_after() -> None:
    """No ``Retry-After`` → exponential-jitter backoff (initial=1, max=30, +1 jitter)."""
    wait = _retry_after_or_jitter_wait()
    resp = httpx.Response(503, request=_DUMMY_REQUEST)
    delay = wait(_retry_state_with(_RetryableStatus(resp, retry_after=None)))
    # First-attempt exponential base is 1.0 with up to 1.0 added jitter.
    assert 0.0 < delay <= 2.0


def test_wait_falls_back_to_jitter_on_non_status_exception() -> None:
    """A transport-level exception (no ``retry_after`` attr) → jitter, not crash."""
    wait = _retry_after_or_jitter_wait()
    delay = wait(_retry_state_with(httpx.ConnectError("boom")))
    assert 0.0 < delay <= 2.0


# ----------------------------------------------------------------------
# Integration — Retry-After honored exactly once, not stacked (sync)
# ----------------------------------------------------------------------


def test_retry_after_honored_once_not_stacked_sync(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A retryable 503+Retry-After then 200 sleeps EXACTLY once for Retry-After.

    Before WR-05 the transport would sleep once inline for ``Retry-After`` AND
    again for tenacity's jitter — two recorded sleeps. Now there is a single
    inter-attempt sleep equal to the parsed ``Retry-After``.
    """
    sleeps: list[float] = []
    monkeypatch.setattr(time, "sleep", lambda s: sleeps.append(s))

    httpx_mock.add_response(
        url=f"{_BASE}/health", method="GET", status_code=503, headers={"Retry-After": "3"}
    )
    httpx_mock.add_response(url=f"{_BASE}/health", method="GET", json={"status": "ok"})

    assert market_data_client.get_health() == {"status": "ok"}
    assert sleeps == [3.0]
