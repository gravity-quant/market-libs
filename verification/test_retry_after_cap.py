"""Cross-cutting Retry-After cap guard — 60s ceiling honored even when server suggests 600s.

Phase 8 D-04, D-26, RELY-02 / Pitfall 13. Wave 1 tests-first guard; fails RED in
HEAD (no retry loop). Plans 2-5 turn it GREEN — uses iol_client as the witness
package since it has a quick GET endpoint with clean Bearer auth.

Invariant: if the server responds 429 with ``Retry-After: <delta-seconds>`` larger
than 60, the RetryTransport caps the sleep at 60s and retries. The test mocks
``Retry-After: 600`` (10 minutes — would block indefinitely without a cap) and
asserts the entire business call completes in < 65s. Failure means the cap is
missing — production callers would hang for ten minutes per 429.
"""

from __future__ import annotations

import contextlib
import time

import pytest
from pytest_httpx import HTTPXMock


@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
def test_retry_after_capped_at_60s(httpx_mock: HTTPXMock) -> None:
    """RELY-02: Retry-After > 60s is capped to 60s; retry happens; total elapsed < 65s.

    Wire sequence:
      1. GET → 429 with ``Retry-After: 600`` header
      2. RetryTransport sleeps min(600, 60) = 60s (capped per D-04)
      3. GET retry → 200 with payload

    Assertions:
      - elapsed time < 65s (60s cap + tolerance for jitter + executing the retry)
      - exactly 2 wire requests (initial 429 + 1 retry)

    RED in HEAD: no retry transport exists, so the 429 surfaces immediately and
    elapsed << 65s but the request count is 1, not 2. Plan 3 (iol) turns this GREEN.

    NOTE: This is a SLOW test by design — it can sleep up to ~60s on success.
    Plan 6's CI green gate accepts the cost; local devs can opt out via
    ``pytest -m "not slow_retry"`` once Plan 6 adds the marker.
    """
    import iol_client

    iol_client.configure(
        base_url="https://api.test",
        username="u",
        password="p",
        token="test-token",
        token_expires_at=9_999_999_999.0,
    )

    httpx_mock.add_response(
        url="https://api.test/api/v2/argentina/Titulos/Cotizacion/Instrumentos",
        status_code=429,
        headers={"Retry-After": "600"},
    )
    httpx_mock.add_response(
        url="https://api.test/api/v2/argentina/Titulos/Cotizacion/Instrumentos",
        json={"instrumentos": []},
    )

    t0 = time.monotonic()
    # In HEAD (no retry transport), the first 429 raises IOLRateLimitError directly.
    # Post-Plan-3, the retry happens and the call may succeed or surface a final error.
    with contextlib.suppress(iol_client.IOLClientError):
        iol_client.get_instruments("argentina")
    elapsed = time.monotonic() - t0

    assert elapsed < 65.0, (
        f"Retry-After cap broken: elapsed={elapsed:.1f}s. Expected < 65s "
        f"(cap=60s per D-04 + retry execution overhead)."
    )
    assert len(httpx_mock.get_requests()) == 2, (
        f"Expected 2 wire requests (1 initial 429 + 1 retry after cap), got "
        f"{len(httpx_mock.get_requests())}. RED in HEAD until Phase 8 lands "
        f"RetryTransport with Retry-After handling."
    )
