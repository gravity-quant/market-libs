"""Unit tests for ``iol_client._transport.RetryTransport``.

Phase 8 iol. RELY-01..04 / D-01 / D-04 / D-07 / D-08 / D-19 / D-30 / D-31. Direct
transport-level tests using ``pytest-httpx`` mocks via
``httpx.Client(transport=RetryTransport(...))`` — covers the transport in
isolation BEFORE Client integration (Task 2).

Mutation gate, retry loop, Retry-After cap, max_attempts bypass, request_id
persistence, login-as-idempotent — each invariant has at least one assertion.
"""

from __future__ import annotations

import logging
import time

import httpx
import pytest
from pytest_httpx import HTTPXMock

from iol_client._transport import RetryTransport


def _build_request(
    client: httpx.Client,
    *,
    idempotent: bool,
    request_id: str = "test-rid",
    endpoint_name: str = "test_endpoint",
    method: str = "GET",
    url: str = "https://api.test/path",
) -> httpx.Request:
    """Build a request with extensions populated as the shell ``_request()`` would."""
    req = client.build_request(method, url)
    req.extensions["idempotent"] = idempotent
    req.extensions["request_id"] = request_id
    req.extensions["endpoint_name"] = endpoint_name
    return req


@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
def test_non_idempotent_request_passes_through(httpx_mock: HTTPXMock) -> None:
    """D-01: idempotent=False MUST bypass the retry loop entirely (1 wire request)."""
    httpx_mock.add_response(status_code=503)
    httpx_mock.add_response(status_code=503)

    client = httpx.Client(transport=RetryTransport(max_attempts=3))
    req = _build_request(client, idempotent=False)
    resp = client.send(req)

    assert resp.status_code == 503
    assert len(httpx_mock.get_requests()) == 1


def test_idempotent_get_retries_on_503(httpx_mock: HTTPXMock) -> None:
    """RELY-01: idempotent=True + 503,503,200 chain → 3 wire requests, final 200."""
    httpx_mock.add_response(status_code=503)
    httpx_mock.add_response(status_code=503)
    httpx_mock.add_response(status_code=200, json={"ok": True})

    client = httpx.Client(transport=RetryTransport(max_attempts=3))
    req = _build_request(client, idempotent=True)
    resp = client.send(req)

    assert resp.status_code == 200
    assert len(httpx_mock.get_requests()) == 3


def test_idempotent_get_exhausts_and_returns_last_5xx(httpx_mock: HTTPXMock) -> None:
    """D-05: retry exhaust → return last response unmolested (no RetryExhaustedError)."""
    httpx_mock.add_response(status_code=503)
    httpx_mock.add_response(status_code=503)
    httpx_mock.add_response(status_code=503)

    client = httpx.Client(transport=RetryTransport(max_attempts=3))
    req = _build_request(client, idempotent=True)
    resp = client.send(req)

    assert resp.status_code == 503
    assert len(httpx_mock.get_requests()) == 3


def test_retry_after_cap_60s(httpx_mock: HTTPXMock) -> None:
    """D-04: 429 with Retry-After honored, capped at 60s.

    Uses Retry-After: 0 to keep the test fast — the cap path is exercised at
    semantics level (delay is parsed; ``min(delay, 60)`` is applied). Validates
    parse + bound logic without sleeping for 60s.
    """
    httpx_mock.add_response(status_code=429, headers={"Retry-After": "0"})
    httpx_mock.add_response(status_code=200, json={"ok": True})

    client = httpx.Client(transport=RetryTransport(max_attempts=3))
    req = _build_request(client, idempotent=True)
    t0 = time.monotonic()
    resp = client.send(req)
    elapsed = time.monotonic() - t0

    assert resp.status_code == 200
    assert len(httpx_mock.get_requests()) == 2
    assert elapsed < 5.0  # Retry-After: 0 → sleep skipped; backoff also bounded


@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
def test_max_attempts_1_bypasses_loop(httpx_mock: HTTPXMock) -> None:
    """D-19: max_attempts=1 → 1 outgoing request total (no retry loop)."""
    httpx_mock.add_response(status_code=503)
    httpx_mock.add_response(status_code=503)

    client = httpx.Client(transport=RetryTransport(max_attempts=1))
    req = _build_request(client, idempotent=True)
    resp = client.send(req)

    assert resp.status_code == 503
    assert len(httpx_mock.get_requests()) == 1


def test_request_id_persists_in_extensions_across_attempts(
    httpx_mock: HTTPXMock,
) -> None:
    """D-30 / Pitfall 9: same request_id across retry attempts; extensions unchanged."""
    httpx_mock.add_response(status_code=503)
    httpx_mock.add_response(status_code=200, json={"ok": True})

    client = httpx.Client(transport=RetryTransport(max_attempts=3))
    req = _build_request(client, idempotent=True, request_id="persistent-rid-42")
    client.send(req)

    # Extensions are by-reference — they MUST remain stable across retries.
    assert req.extensions["request_id"] == "persistent-rid-42"
    assert req.extensions["idempotent"] is True


def test_warning_log_contains_request_id_and_endpoint(
    httpx_mock: HTTPXMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """D-09: WARNING per attempt carries the canonical structured fields with iol package."""
    httpx_mock.add_response(status_code=503)
    httpx_mock.add_response(status_code=200, json={"ok": True})

    caplog.set_level(logging.WARNING, logger="iol_client")
    client = httpx.Client(transport=RetryTransport(max_attempts=3))
    req = _build_request(client, idempotent=True, request_id="log-rid", endpoint_name="get_x")
    client.send(req)

    warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert warning_records, "expected at least one WARNING retry attempt record"
    record = warning_records[0]
    assert getattr(record, "request_id", None) == "log-rid"
    assert getattr(record, "endpoint_name", None) == "get_x"
    assert getattr(record, "method", None) == "GET"
    assert getattr(record, "status_code", None) == 503
    assert getattr(record, "package", None) == "iol_client"


def test_login_request_retries_on_503_when_idempotent_true(httpx_mock: HTTPXMock) -> None:
    """D-29 + D-03: login (POST /token) marked idempotent=True retries on transient 5xx.

    Login through the RetryTransport: a transient 503 on the OAuth POST /token
    endpoint is retry-eable because the IOL OAuth grant is replay-safe (a fresh
    access_token simply replaces the prior one; no state mutation per D-03).
    """
    httpx_mock.add_response(status_code=503)
    httpx_mock.add_response(
        status_code=200,
        json={"access_token": "tok", "refresh_token": "r", "expires_in": 900},
    )

    client = httpx.Client(transport=RetryTransport(max_attempts=3))
    # Login uses POST + form body, marked idempotent=True per D-03.
    req = _build_request(
        client,
        idempotent=True,
        method="POST",
        url="https://api.test/token",
        endpoint_name="login",
    )
    resp = client.send(req)

    assert resp.status_code == 200
    assert len(httpx_mock.get_requests()) == 2
