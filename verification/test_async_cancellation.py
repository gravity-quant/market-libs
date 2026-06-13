"""Cross-cutting async cancellation guard — asyncio.CancelledError propagates during retry sleep.

Phase 8 D-32, D-26, RELY-01 / Pitfall 16. Wave 1 tests-first guard; fails RED in
HEAD (no AsyncRetryTransport yet). Plans 2-4 turn it GREEN as ámbito/iol/higyrus
ship ``_atransport.py``. matriz async is deferred to Phase 10 REFAC-04 (D-25);
matriz branch is skipped with the verbatim reason from Phase 7 D-11.

Invariant: when a caller cancels an in-flight async request DURING the
retry-backoff sleep, ``asyncio.CancelledError`` (resp. ``asyncio.TimeoutError``
via ``asyncio.wait_for``) MUST propagate within the cancel window — NOT wait for
the full retry budget. tenacity's ``AsyncRetrying`` uses ``asyncio.sleep`` by
default, which IS cancellable. The guard ensures the implementation didn't
accidentally swap in ``time.sleep`` (blocks event loop) or swallow
``BaseException`` in a misguided ``except Exception:``.

The test mocks 503→503 (would normally trigger backoff sleep ~1-2s with
``wait_exponential_jitter`` defaults), then wraps the call in
``asyncio.wait_for(..., timeout=0.5)``. After Plans 2-4 land:
- TimeoutError raised in < 1.0s (well before the full retry budget elapses)

In HEAD (no retry transport): the 503 surfaces immediately and the test FAILS
because no TimeoutError raises — the call completes (with APIError) in << 0.5s.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import importlib
import time
from typing import Any

import pytest
from pytest_httpx import HTTPXMock

# Async paquetes. matriz skipped per D-25 + Phase 7 D-11 (matriz aio.py REST
# surface is stub until Phase 10 REFAC-04 + TokenStore).
_ASYNC_PACKAGES = ["ambito_financiero_client", "iol_client", "higyrus_client", "matriz_client"]


def _configure_async(aio: Any, pkg_name: str) -> None:
    if pkg_name == "ambito_financiero_client":
        aio.configure(base_url="https://api.test")
    elif pkg_name == "iol_client":
        aio.configure(
            base_url="https://api.test",
            username="u",
            password="p",
            token="test-token",
            token_expires_at=9_999_999_999.0,
        )
    elif pkg_name == "higyrus_client":
        aio.configure(
            base_url="https://api.test",
            username="u",
            password="p",
            client_id="tenant",
            token="test-token",
            token_expires_at=9_999_999_999.0,
        )
    else:  # pragma: no cover
        raise AssertionError(f"unhandled pkg in _configure_async: {pkg_name}")


@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
@pytest.mark.parametrize("pkg_name", _ASYNC_PACKAGES)
async def test_cancellation_propagates_during_retry_backoff(
    pkg_name: str,
    httpx_mock: HTTPXMock,
) -> None:
    """RELY-01 + Pitfall 16: asyncio.wait_for cancels in-flight retry within deadline.

    Mocks 503→503 (would trigger backoff sleep with retry transport active).
    Wraps the call in ``asyncio.wait_for(..., timeout=0.5)``. Asserts:
    - ``asyncio.TimeoutError`` raised within deadline (or shortly after — < 1.0s)
    - elapsed time < 1.0s (cancellation interrupted the backoff sleep)

    Guard test; RED in HEAD until Plans 2-4 add AsyncRetryTransport. matriz async
    is skipped per D-25 with the verbatim Phase 7 D-11 reason.
    """
    if pkg_name == "matriz_client":
        pytest.skip("matriz aio.py REST stub hasta Phase 10 REFAC-04 + TokenStore")

    pkg = importlib.import_module(pkg_name)
    aio = pkg.aio
    _configure_async(aio, pkg_name)

    # 503 chain — would trigger backoff sleep post-Phase-8 RetryTransport.
    httpx_mock.add_response(status_code=503)
    httpx_mock.add_response(status_code=503)

    if pkg_name == "ambito_financiero_client":
        coro = aio.get_dollar_banco_nacion(dt.date(2026, 1, 2))
    elif pkg_name == "iol_client":
        coro = aio.get_instruments("argentina")
    elif pkg_name == "higyrus_client":
        coro = aio.get_listado_cuentas(estado="alta")
    else:  # pragma: no cover
        raise AssertionError(f"unhandled pkg: {pkg_name}")

    t0 = time.monotonic()
    with pytest.raises((TimeoutError, asyncio.TimeoutError)):
        await asyncio.wait_for(coro, timeout=0.5)
    elapsed = time.monotonic() - t0

    assert elapsed < 1.0, (
        f"{pkg_name}: cancellation took {elapsed:.2f}s > 1.0s budget. "
        f"asyncio.sleep MUST be cancellable — verify AsyncRetryTransport uses "
        f"tenacity AsyncRetrying (which calls asyncio.sleep, not time.sleep). "
        f"RED in HEAD until Plans 2-4 land AsyncRetryTransport (Pitfall 16)."
    )
