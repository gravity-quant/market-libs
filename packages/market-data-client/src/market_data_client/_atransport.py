"""AsyncRetryTransport — async httpx transport mirror of ``_transport.RetryTransport``.

Phase 20 market-data. CORE-MD-01 + D-10. Mirrors the sync ``RetryTransport``
semantics over ``httpx.AsyncHTTPTransport`` using ``tenacity.AsyncRetrying``
(``async for`` + ``async with``). Retry-After is honored via the shared
``_retry_after_or_jitter_wait`` strategy (WR-05 — never stacked on top of the
jitter backoff); ``AsyncRetrying`` awaits that wait through ``asyncio.sleep``
internally, so ``asyncio.CancelledError`` still propagates during the delay
(D-32 / Pitfall 16).

The retryable surfaces, sentinel, parsing helpers, and module-level constants
are imported from the sync ``_transport`` to avoid intra-package duplication.
This is a deliberate intra-package coupling — the "no shared internals
between packages" constraint applies at the **package** boundary, not the
**module** boundary. The same intra-package import pattern is used by iol.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
)

from market_data_client._transport import (
    _LOGGER_NAME,
    _RETRYABLE_EXC,
    _is_retryable_status,
    _parse_retry_after,
    _retry_after_or_jitter_wait,
    _RetryableStatus,
)

__all__ = ["AsyncRetryTransport"]


class AsyncRetryTransport(httpx.AsyncHTTPTransport):
    """``httpx.AsyncHTTPTransport`` subclass — async mirror of ``RetryTransport``.

    Uses ``AsyncRetrying`` (``async for attempt in ...``) and
    ``await asyncio.sleep`` so ``asyncio.CancelledError`` propagates naturally
    during the Retry-After honor sleep (D-32 / Pitfall 16).
    """

    def __init__(self, *, max_attempts: int = 2, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._max_attempts = max(max_attempts, 1)
        self._logger = logging.getLogger(_LOGGER_NAME)

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        # D-01 mutation gate.
        if not request.extensions.get("idempotent", False):
            return await super().handle_async_request(request)
        # D-19 bypass.
        if self._max_attempts <= 1:
            return await super().handle_async_request(request)

        request_id = request.extensions.get("request_id", "")
        endpoint_name = request.extensions.get("endpoint_name", "")
        account_id = request.extensions.get("account_id")
        # Phase 13 ERG-01: per-request override via with_options(max_retries=N) view.
        effective_max_attempts = request.extensions.get("max_attempts", self._max_attempts)
        start = time.monotonic()
        attempt_number = 0

        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(effective_max_attempts),
                wait=_retry_after_or_jitter_wait(),
                retry=(
                    retry_if_exception_type(_RETRYABLE_EXC)
                    | retry_if_exception_type(_RetryableStatus)
                ),
                reraise=True,
            ):
                with attempt:
                    attempt_number = attempt.retry_state.attempt_number
                    response = await super().handle_async_request(request)
                    await response.aread()  # body-consume async variant
                    if _is_retryable_status(response):
                        # WR-05: parse Retry-After and hand it to the sentinel so the
                        # shared wait strategy honors it INSTEAD OF jitter — no double
                        # sleep. AsyncRetrying awaits the wait via asyncio.sleep, so
                        # cancellation still propagates during the delay (D-32).
                        retry_after_header = response.headers.get("Retry-After")
                        retry_after_s: float | None = None
                        if retry_after_header is not None:
                            delay = _parse_retry_after(retry_after_header)
                            if delay is not None and delay > 0:
                                retry_after_s = delay
                        extra: dict[str, Any] = {
                            "package": _LOGGER_NAME,
                            "method": request.method,
                            "url": str(request.url),
                            "status_code": response.status_code,
                            "attempt": attempt_number,
                            "request_id": request_id,
                            "endpoint_name": endpoint_name,
                            "retry_reason": f"status_{response.status_code}",
                        }
                        if account_id:
                            extra["account_id"] = account_id
                        self._logger.warning("retry attempt", extra=extra)
                        raise _RetryableStatus(response, retry_after=retry_after_s)
                    return response
        except _RetryableStatus as exc:
            return exc.response
        except _RETRYABLE_EXC:
            duration_ms = int((time.monotonic() - start) * 1000)
            extra = {
                "package": _LOGGER_NAME,
                "method": request.method,
                "url": str(request.url),
                "status_code": None,
                "attempt": attempt_number,
                "duration_ms": duration_ms,
                "request_id": request_id,
                "endpoint_name": endpoint_name,
            }
            if account_id:
                extra["account_id"] = account_id
            self._logger.error(
                "retry exhausted (transport error)",
                extra=extra,
                exc_info=False,
            )
            raise

        raise RuntimeError(  # pragma: no cover
            "AsyncRetryTransport.handle_async_request fell through tenacity loop"
        )
