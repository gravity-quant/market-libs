"""Unit tests for ``matriz_client._transport.RetryTransport``.

Phase 8 matriz Plan 5. RELY-01..04 / D-01 / D-04 / D-07 / D-08 / D-11 / D-19 /
D-23 / D-24 / D-30 / D-31. Direct transport-level tests using ``pytest-httpx``
mocks via ``httpx.Client(transport=RetryTransport(...))`` — covers the
transport in isolation BEFORE Client integration (Task 2).

matriz-specific tests cover:

- ``test_new_order_POST_does_NOT_retry_on_503`` (Pitfall 4 / D-01 / D-24):
  matriz mutating builders use HTTP GET (Primary API quirk) BUT explicit
  ``idempotent=False`` MUST prevent retry → exactly 1 wire request even with
  503 mocked twice. CRITICAL duplicate-order prevention.
- ``test_risk_api_auth_basic_in_extensions_does_NOT_retry_401`` (D-23):
  401 is NEVER in ``_RETRYABLE_STATUS`` — transport returns 401 unchanged, shell
  branches on ``spec.auth_basic`` to decide whether to re-auth.
"""

from __future__ import annotations

import logging
import time

import httpx
import pytest
from pytest_httpx import HTTPXMock

from matriz_client._transport import RetryTransport


def _build_request(
    client: httpx.Client,
    *,
    idempotent: bool,
    request_id: str = "test-rid",
    endpoint_name: str = "test_endpoint",
    method: str = "GET",
    url: str = "https://api.test/path",
    account_id: str | None = None,
) -> httpx.Request:
    """Build a request with extensions populated as the shell ``_request()`` would."""
    req = client.build_request(method, url)
    req.extensions["idempotent"] = idempotent
    req.extensions["request_id"] = request_id
    req.extensions["endpoint_name"] = endpoint_name
    if account_id is not None:
        req.extensions["account_id"] = account_id
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
    """D-04: 429 with Retry-After honored, capped at 60s."""
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

    assert req.extensions["request_id"] == "persistent-rid-42"
    assert req.extensions["idempotent"] is True


def test_warning_log_contains_request_id_and_endpoint(
    httpx_mock: HTTPXMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """D-09: WARNING per attempt carries the canonical structured fields with matriz package."""
    httpx_mock.add_response(status_code=503)
    httpx_mock.add_response(status_code=200, json={"ok": True})

    caplog.set_level(logging.WARNING, logger="matriz_client")
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
    assert getattr(record, "package", None) == "matriz_client"


def test_login_request_retries_on_503_when_idempotent_true(httpx_mock: HTTPXMock) -> None:
    """D-29 + D-03: login (POST /auth/getToken) marked idempotent=True retries on 5xx.

    matriz Primary login is replay-safe — the new X-Auth-Token simply replaces
    the prior one server-side. Transient 5xx during auth are retry-eable.
    """
    httpx_mock.add_response(status_code=503)
    httpx_mock.add_response(
        status_code=200,
        headers={"X-Auth-Token": "tok-matriz"},
    )

    client = httpx.Client(transport=RetryTransport(max_attempts=3))
    req = _build_request(
        client,
        idempotent=True,
        method="POST",
        url="https://api.test/auth/getToken",
        endpoint_name="login",
    )
    resp = client.send(req)

    assert resp.status_code == 200
    assert len(httpx_mock.get_requests()) == 2


# ---------------------------------------------------------------------------
# matriz-specific tests — D-01 / D-23 / D-24 (CRITICAL)
# ---------------------------------------------------------------------------


@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
def test_new_order_POST_does_NOT_retry_on_503(httpx_mock: HTTPXMock) -> None:
    """Pitfall 4 / D-01 / D-24 — CRITICAL duplicate-order prevention.

    matriz Primary API uses HTTP GET for ``new_order`` (Primary quirk). The
    mutation gate ``request.extensions["idempotent"] = False`` MUST prevent
    the retry transport from looping on 503 — otherwise we duplicate broker
    orders. This is the most important matriz-specific invariant.
    """
    httpx_mock.add_response(status_code=503)
    httpx_mock.add_response(status_code=503)

    client = httpx.Client(transport=RetryTransport(max_attempts=3))
    # Simulate what the shell does for build_new_order_request: HTTP method GET
    # but idempotent=False because this is semantically a mutation.
    req = _build_request(
        client,
        idempotent=False,
        method="GET",
        url="https://api.test/rest/order/newSingleOrder",
        endpoint_name="new_order",
    )
    resp = client.send(req)

    assert resp.status_code == 503
    assert len(httpx_mock.get_requests()) == 1, (
        "matriz new_order MUST NOT retry on 503 — duplicate-order risk per Pitfall 4 / D-24"
    )


@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
def test_risk_api_auth_basic_in_extensions_does_NOT_retry_401(
    httpx_mock: HTTPXMock,
) -> None:
    """D-23: 401 is NEVER in retryable status set — transport returns 401 unchanged.

    The shell ``_request()`` decides whether to re-auth based on
    ``spec.auth_basic``: Risk API (auth_basic set) → raise AuthError; Token path
    → re-auth-once. The transport ITSELF must not retry 401 regardless of
    idempotent flag. This guard verifies that invariant at the transport level.
    """
    httpx_mock.add_response(status_code=401)

    client = httpx.Client(transport=RetryTransport(max_attempts=3))
    req = _build_request(
        client,
        idempotent=True,
        method="GET",
        url="https://api.test/rest/risk/position/getPositions/acc",
        endpoint_name="get_positions",
    )
    # auth_basic propagated as an extension for the log filter (D-22).
    req.extensions["auth_basic"] = ("u", "p")
    resp = client.send(req)

    assert resp.status_code == 401
    assert len(httpx_mock.get_requests()) == 1, (
        "401 MUST NOT trigger transport retry (D-23) — shell handles re-auth"
    )


def test_risk_api_auth_basic_in_extensions_retries_on_503(
    httpx_mock: HTTPXMock,
) -> None:
    """D-23: Risk API still benefits from 5xx retries — transport YES, 401 no-reauth NO.

    The shell-level skip-re-auth is the 401 carve-out per D-23; transient 5xx
    on Risk endpoints ARE retried as on any other idempotent GET.
    """
    httpx_mock.add_response(status_code=503)
    httpx_mock.add_response(status_code=200, json={"ok": True})

    client = httpx.Client(transport=RetryTransport(max_attempts=3))
    req = _build_request(
        client,
        idempotent=True,
        method="GET",
        url="https://api.test/rest/risk/accountReport/acc",
        endpoint_name="get_account_report",
    )
    req.extensions["auth_basic"] = ("u", "p")
    resp = client.send(req)

    assert resp.status_code == 200
    assert len(httpx_mock.get_requests()) == 2


def test_account_id_propagates_to_extensions(httpx_mock: HTTPXMock) -> None:
    """D-11: account_id set in request.extensions reaches the wire and is preserved."""
    httpx_mock.add_response(status_code=200, json={"ok": True})

    client = httpx.Client(transport=RetryTransport(max_attempts=3))
    req = _build_request(
        client,
        idempotent=True,
        endpoint_name="get_active_orders",
        account_id="ACC-MATZ-1",
    )
    client.send(req)

    assert req.extensions["account_id"] == "ACC-MATZ-1"


def test_account_id_in_warning_record_when_retrying(
    httpx_mock: HTTPXMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """D-09 + D-11: WARNING record carries account_id as a structured extra field."""
    httpx_mock.add_response(status_code=503)
    httpx_mock.add_response(status_code=200, json={"ok": True})

    caplog.set_level(logging.WARNING, logger="matriz_client")
    client = httpx.Client(transport=RetryTransport(max_attempts=3))
    req = _build_request(
        client,
        idempotent=True,
        endpoint_name="get_active_orders",
        account_id="ACC-MATZ-2",
    )
    client.send(req)

    warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert warning_records, "expected WARNING retry attempt record"
    assert getattr(warning_records[0], "account_id", None) == "ACC-MATZ-2"
