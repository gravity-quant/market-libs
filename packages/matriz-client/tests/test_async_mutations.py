"""Async mutation tests for ``matriz_client.aio`` (Phase 10 Plan 10-02 Task 2).

CRITICAL — Pitfall 4 / D-01 / D-24: matriz mutating endpoints (``new_order`` /
``cancel_order`` / ``replace_order``) are HTTP GET (Primary API quirk) but
MUST set ``idempotent=False`` so the AsyncRetryTransport mutation gate
prevents duplicate-order risk on transient 503.

These tests assert EXACTLY 1 outgoing request against a 503 mock chain — if
the gate ever breaks, the test fails loudly.
"""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from matriz_client import aio
from matriz_client.models import NewOrderResponse

# ---------------------------------------------------------------------------
# AM1: new_order happy path — verify idempotent=False is propagated as extension
# ---------------------------------------------------------------------------


async def test_async_new_order_happy_path_returns_parsed_response(httpx_mock: HTTPXMock) -> None:
    """AM1 / AM5: new_order against 200 OK returns parsed NewOrderResponse."""
    httpx_mock.add_response(
        url="https://api.test/rest/order/newSingleOrder?marketId=ROFX&symbol=DLR/MAR26&side=BUY&orderQty=1&ordType=LIMIT&timeInForce=DAY&account=ACC-1&cancelPrevious=False&iceberg=False&price=1000.0",
        method="GET",
        json={"status": "OK", "order": {"clientId": "cl-1", "proprietary": "PBCP"}},
    )
    resp = await aio.new_order("DLR/MAR26", "BUY", 1, "ACC-1", price=1000.0)
    assert isinstance(resp, NewOrderResponse)
    assert resp.clientId == "cl-1"
    assert resp.proprietary == "PBCP"


# ---------------------------------------------------------------------------
# AM2: MUTATION GATE — new_order on 503 → EXACTLY 1 request
# ---------------------------------------------------------------------------


@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
async def test_async_new_order_503_does_not_retry(httpx_mock: HTTPXMock) -> None:
    """AM2 / Pitfall 4 — CRITICAL: new_order against 503 → EXACTLY 1 wire request.

    Mutation gate ``idempotent=False`` (set by ``_core.build_new_order_request``)
    MUST prevent the AsyncRetryTransport from looping on 503 — otherwise we
    duplicate broker orders. This is the most important matriz async invariant.
    """
    httpx_mock.add_response(status_code=503)
    httpx_mock.add_response(status_code=503)
    httpx_mock.add_response(status_code=503)

    # Use max_retries=3 explicitly so the default transport WOULD retry if the
    # mutation gate were broken — proves the gate is honored, not the budget.
    aio.configure(
        base_url="https://api.test",
        username="u",
        password="p",
        token="seed",
        token_expires_at=9_999_999_999.0,
        max_retries=3,
    )

    # 503 surfaces as PrimaryAPIError via raise_for_response after parse.
    from matriz_client.exceptions import PrimaryAPIError

    with pytest.raises(PrimaryAPIError):
        await aio.new_order("DLR/MAR26", "BUY", 1, "ACC-1", price=1000.0)

    assert len(httpx_mock.get_requests()) == 1, (
        "matriz async new_order MUST NOT retry on 503 — duplicate-order risk"
    )


# ---------------------------------------------------------------------------
# AM3: MUTATION GATE — cancel_order on 503 → EXACTLY 1 request
# ---------------------------------------------------------------------------


@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
async def test_async_cancel_order_503_does_not_retry(httpx_mock: HTTPXMock) -> None:
    """AM3: cancel_order against 503 → EXACTLY 1 request (mutation gate)."""
    httpx_mock.add_response(status_code=503)
    httpx_mock.add_response(status_code=503)

    aio.configure(
        base_url="https://api.test",
        username="u",
        password="p",
        token="seed",
        token_expires_at=9_999_999_999.0,
        max_retries=3,
    )

    from matriz_client.exceptions import PrimaryAPIError

    with pytest.raises(PrimaryAPIError):
        await aio.cancel_order("cl-cancel-1", "PBCP")

    assert len(httpx_mock.get_requests()) == 1, "matriz async cancel_order MUST NOT retry on 503"


# ---------------------------------------------------------------------------
# AM4: MUTATION GATE — replace_order on 503 → EXACTLY 1 request
# ---------------------------------------------------------------------------


@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
async def test_async_replace_order_503_does_not_retry(httpx_mock: HTTPXMock) -> None:
    """AM4: replace_order against 503 → EXACTLY 1 request (mutation gate)."""
    httpx_mock.add_response(status_code=503)
    httpx_mock.add_response(status_code=503)

    aio.configure(
        base_url="https://api.test",
        username="u",
        password="p",
        token="seed",
        token_expires_at=9_999_999_999.0,
        max_retries=3,
    )

    from matriz_client.exceptions import PrimaryAPIError

    with pytest.raises(PrimaryAPIError):
        await aio.replace_order("cl-replace-1", "PBCP", 2, 1010.0)

    assert len(httpx_mock.get_requests()) == 1, "matriz async replace_order MUST NOT retry on 503"


# ---------------------------------------------------------------------------
# AM5 bonus: contrast — idempotent GET (get_segments) IS retried on 503
# ---------------------------------------------------------------------------


async def test_async_idempotent_get_segments_IS_retried_on_503(httpx_mock: HTTPXMock) -> None:
    """AM5 contrast: idempotent=True get_segments DOES retry on 503 → eventually succeeds."""
    httpx_mock.add_response(
        url="https://api.test/rest/segment/all",
        method="GET",
        status_code=503,
    )
    httpx_mock.add_response(
        url="https://api.test/rest/segment/all",
        method="GET",
        json={"status": "OK", "segments": []},
    )

    aio.configure(
        base_url="https://api.test",
        username="u",
        password="p",
        token="seed",
        token_expires_at=9_999_999_999.0,
        max_retries=3,
    )

    segments = await aio.get_segments()
    assert segments == []
    # Both mocks consumed → at least 2 requests, proving retry IS allowed.
    endpoint_calls = [r for r in httpx_mock.get_requests() if r.url.path == "/rest/segment/all"]
    assert len(endpoint_calls) >= 2
