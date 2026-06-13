"""Unit tests for ``matriz_client._atransport.AsyncRetryTransport``.

Phase 10 Plan 10-02 Task 1. D-25 carve-out closure: async mirror of the sync
``RetryTransport`` tests in ``test_transport.py`` covering the retry semantics,
mutation gate (Pitfall 4), Retry-After honor via ``await asyncio.sleep``
(CancelledError-aware per D-32), and the D-22 ``auth_basic`` log split.
"""

from __future__ import annotations

import asyncio
import logging

import httpx
import pytest
from pytest_httpx import HTTPXMock

from matriz_client._atransport import AsyncRetryTransport


def _build_request(
    client: httpx.AsyncClient,
    *,
    idempotent: bool,
    method: str = "GET",
    url: str = "https://api.test/path",
    request_id: str = "test-rid",
    endpoint_name: str = "test_endpoint",
    account_id: str | None = None,
    auth_basic: tuple[str, str] | None = None,
) -> httpx.Request:
    """Build an async request with extensions populated as the shell would."""
    req = client.build_request(method, url)
    req.extensions["idempotent"] = idempotent
    req.extensions["request_id"] = request_id
    req.extensions["endpoint_name"] = endpoint_name
    if account_id is not None:
        req.extensions["account_id"] = account_id
    if auth_basic is not None:
        req.extensions["auth_basic"] = auth_basic
    return req


# ---------------------------------------------------------------------------
# T1: constructibility
# ---------------------------------------------------------------------------


async def test_transport_constructible_and_subclasses_async_http_transport() -> None:
    """T1: AsyncRetryTransport is constructible and is an httpx.AsyncHTTPTransport."""
    t = AsyncRetryTransport(max_attempts=2)
    assert isinstance(t, httpx.AsyncHTTPTransport)
    # Cleanup the underlying pool.
    await t.aclose()


# ---------------------------------------------------------------------------
# T2: idempotent retry on 503
# ---------------------------------------------------------------------------


async def test_idempotent_request_retries_on_503(httpx_mock: HTTPXMock) -> None:
    """T2: idempotent=True with 503,200 → 2 wire requests, final 200."""
    httpx_mock.add_response(status_code=503)
    httpx_mock.add_response(status_code=200, json={"ok": True})

    async with httpx.AsyncClient(transport=AsyncRetryTransport(max_attempts=2)) as client:
        req = _build_request(client, idempotent=True)
        resp = await client.send(req)

    assert resp.status_code == 200
    assert len(httpx_mock.get_requests()) == 2


# ---------------------------------------------------------------------------
# T3: MUTATION GATE — Pitfall 4
# ---------------------------------------------------------------------------


@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
async def test_mutation_gate_does_not_retry_on_503(httpx_mock: HTTPXMock) -> None:
    """T3 / Pitfall 4 — CRITICAL duplicate-order prevention.

    Async mirror of the sync ``test_new_order_POST_does_NOT_retry_on_503``:
    idempotent=False against 503 mocked twice → EXACTLY 1 outgoing request.
    """
    httpx_mock.add_response(status_code=503)
    httpx_mock.add_response(status_code=503)

    async with httpx.AsyncClient(transport=AsyncRetryTransport(max_attempts=3)) as client:
        req = _build_request(
            client,
            idempotent=False,
            method="GET",
            url="https://api.test/rest/order/newSingleOrder",
            endpoint_name="new_order",
        )
        resp = await client.send(req)

    assert resp.status_code == 503
    assert len(httpx_mock.get_requests()) == 1, (
        "matriz async new_order MUST NOT retry on 503 — duplicate-order risk"
    )


# ---------------------------------------------------------------------------
# T4: Retry-After honored via await asyncio.sleep
# ---------------------------------------------------------------------------


async def test_retry_after_honored_via_asyncio_sleep(
    httpx_mock: HTTPXMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T4: 429 with Retry-After: 1 triggers ONE await asyncio.sleep(1.0) before retry."""
    httpx_mock.add_response(status_code=429, headers={"Retry-After": "1"})
    httpx_mock.add_response(status_code=200, json={"ok": True})

    sleeps: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    monkeypatch.setattr("matriz_client._atransport.asyncio.sleep", fake_sleep)

    async with httpx.AsyncClient(transport=AsyncRetryTransport(max_attempts=2)) as client:
        req = _build_request(client, idempotent=True)
        resp = await client.send(req)

    assert resp.status_code == 200
    assert 1.0 in sleeps  # at least the Retry-After: 1 sleep happened.


# ---------------------------------------------------------------------------
# T5: Retry-After cap at 60s
# ---------------------------------------------------------------------------


async def test_retry_after_capped_at_60_seconds(
    httpx_mock: HTTPXMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T5: 429 with Retry-After: 120 sleeps capped at _RETRY_AFTER_CAP_S (60s)."""
    httpx_mock.add_response(status_code=429, headers={"Retry-After": "120"})
    httpx_mock.add_response(status_code=200, json={"ok": True})

    sleeps: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    monkeypatch.setattr("matriz_client._atransport.asyncio.sleep", fake_sleep)

    async with httpx.AsyncClient(transport=AsyncRetryTransport(max_attempts=2)) as client:
        req = _build_request(client, idempotent=True)
        resp = await client.send(req)

    assert resp.status_code == 200
    # The 120s Retry-After value must be capped at 60s before the sleep call.
    assert any(s == 60.0 for s in sleeps), f"expected a 60.0 cap sleep; got {sleeps!r}"


# ---------------------------------------------------------------------------
# T6: CancelledError propagation (D-32 / Pitfall 16)
# ---------------------------------------------------------------------------


@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
async def test_cancelled_error_propagates_during_retry_after_sleep(
    httpx_mock: HTTPXMock,
) -> None:
    """T6 / D-32: CancelledError raised during Retry-After sleep propagates to caller."""
    httpx_mock.add_response(status_code=429, headers={"Retry-After": "30"})
    httpx_mock.add_response(status_code=200, json={"ok": True})

    async with httpx.AsyncClient(transport=AsyncRetryTransport(max_attempts=2)) as client:
        req = _build_request(client, idempotent=True)
        task = asyncio.create_task(client.send(req))
        # Yield control so the request can be sent + the sleep starts.
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task


# ---------------------------------------------------------------------------
# T7: max_attempts=1 bypass
# ---------------------------------------------------------------------------


@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
async def test_max_attempts_1_bypasses_retry_loop(httpx_mock: HTTPXMock) -> None:
    """T7 / D-19: max_attempts=1 → 1 outgoing request total (no retry loop)."""
    httpx_mock.add_response(status_code=503)
    httpx_mock.add_response(status_code=503)

    async with httpx.AsyncClient(transport=AsyncRetryTransport(max_attempts=1)) as client:
        req = _build_request(client, idempotent=True)
        resp = await client.send(req)

    assert resp.status_code == 503
    assert len(httpx_mock.get_requests()) == 1


# ---------------------------------------------------------------------------
# T8: auth_basic log split (D-22)
# ---------------------------------------------------------------------------


async def test_auth_basic_tuple_split_in_warning_log_record(
    httpx_mock: HTTPXMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """T8 / D-22: WARNING retry record carries auth_basic_user + auth_basic_password=***."""
    httpx_mock.add_response(status_code=503)
    httpx_mock.add_response(status_code=200, json={"ok": True})

    caplog.set_level(logging.WARNING, logger="matriz_client")

    async with httpx.AsyncClient(transport=AsyncRetryTransport(max_attempts=2)) as client:
        req = _build_request(
            client,
            idempotent=True,
            method="GET",
            url="https://api.test/rest/risk/accountReport/acc",
            endpoint_name="get_account_report",
            auth_basic=("operator-u", "super-secret-p"),
        )
        resp = await client.send(req)

    assert resp.status_code == 200
    warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert warning_records, "expected at least one WARNING retry record"
    record = warning_records[0]
    assert getattr(record, "auth_basic_user", None) == "operator-u"
    assert getattr(record, "auth_basic_password", None) == "***"
    # The password literal must NOT appear in the formatted log message either.
    for r in caplog.records:
        assert "super-secret-p" not in r.getMessage(), (
            f"password literal leaked in record: {r.getMessage()!r}"
        )


# ---------------------------------------------------------------------------
# Additional matriz-specific coverage: request_id + account_id propagation
# ---------------------------------------------------------------------------


async def test_warning_log_carries_request_id_and_account_id(
    httpx_mock: HTTPXMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """D-09 + D-11 (async mirror): WARNING record carries request_id + account_id."""
    httpx_mock.add_response(status_code=503)
    httpx_mock.add_response(status_code=200, json={"ok": True})

    caplog.set_level(logging.WARNING, logger="matriz_client")

    async with httpx.AsyncClient(transport=AsyncRetryTransport(max_attempts=2)) as client:
        req = _build_request(
            client,
            idempotent=True,
            request_id="persistent-rid-42",
            endpoint_name="get_active_orders",
            account_id="ACC-ASYNC-42",
        )
        await client.send(req)

    warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert warning_records
    record = warning_records[0]
    assert getattr(record, "request_id", None) == "persistent-rid-42"
    assert getattr(record, "endpoint_name", None) == "get_active_orders"
    assert getattr(record, "account_id", None) == "ACC-ASYNC-42"
    assert getattr(record, "package", None) == "matriz_client"
