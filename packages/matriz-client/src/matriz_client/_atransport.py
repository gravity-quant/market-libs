"""AsyncRetryTransport — async httpx transport mirror of ``_transport.RetryTransport``.

Phase 10 Plan 10-02 Task 1. RELY-01..04 + D-01/D-04/D-07/D-08/D-19/D-22/D-25/D-32.
Mirrors the sync ``RetryTransport`` semantics over ``httpx.AsyncHTTPTransport``
using ``tenacity.AsyncRetrying`` (``async for`` + ``async with``) and
``await asyncio.sleep`` for the Retry-After honor (D-32 — preserves
``asyncio.CancelledError`` propagation, Pitfall 16).

D-25 carve-out closure: Phase 8 Plan 5 deferred this module ("no ``_atransport.py``
in Phase 8") because matriz had no async REST surface yet (the Plan 06 stub didn't
need a retry transport). Plan 10-02 ships the async REST surface (``aio.AsyncClient``)
so the carve-out closes here.

The retryable surfaces, sentinel, parsing helpers, and module-level constants
are imported from the sync ``_transport`` to avoid intra-package duplication.
This is a deliberate intra-package coupling — the "no shared internals
between packages" constraint applies at the **package** boundary, not the
**module** boundary. The same intra-package import pattern is used by iol
and ámbito.

matriz delta vs iol ``_atransport.py``: this module propagates the
``request.extensions["auth_basic"]`` tuple into the log record extras as the
D-22 split (``auth_basic_user``/``auth_basic_password="***"``) so the matriz
Risk API §9 BasicAuth path gets the same log redaction as the sync
``_transport.py`` (CR-02 in Phase 8). iol has no equivalent because IOL has
no Risk API BasicAuth.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from matriz_client._transport import (
    _LOGGER_NAME,
    _RETRY_AFTER_CAP_S,
    _RETRYABLE_EXC,
    _is_retryable_status,
    _parse_retry_after,
    _RetryableStatus,
)

__all__ = ["AsyncRetryTransport"]


class AsyncRetryTransport(httpx.AsyncHTTPTransport):
    """``httpx.AsyncHTTPTransport`` subclass — async mirror of ``RetryTransport``.

    Uses ``AsyncRetrying`` (``async for attempt in ...``) and
    ``await asyncio.sleep`` so ``asyncio.CancelledError`` propagates naturally
    during the Retry-After honor sleep (D-32 / Pitfall 16). Matches the sync
    ``RetryTransport`` invariants 1:1 including the D-22 ``auth_basic`` log
    redaction split (matriz Risk API §9 carve-out).
    """

    def __init__(self, *, max_attempts: int = 2, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._max_attempts = max(max_attempts, 1)
        self._logger = logging.getLogger(_LOGGER_NAME)

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        # D-01 mutation gate: non-idempotent → pass-through with no retry loop.
        # CRITICAL for matriz: new_order / cancel_order / replace_order are HTTP
        # GET (Primary API quirk) but `idempotent=False` per Pitfall 4 / D-24.
        if not request.extensions.get("idempotent", False):
            return await super().handle_async_request(request)
        # D-19 bypass: max_attempts <= 1 → 1 outgoing request total.
        if self._max_attempts <= 1:
            return await super().handle_async_request(request)

        request_id = request.extensions.get("request_id", "")
        endpoint_name = request.extensions.get("endpoint_name", "")
        account_id = request.extensions.get("account_id")
        # Phase 13 ERG-01: per-request override via with_options(max_retries=N) view.
        effective_max_attempts = request.extensions.get("max_attempts", self._max_attempts)
        # D-22 (matriz delta vs iol): propagate the auth_basic tuple from the
        # shell so the log record extras carry the split user/password pair.
        auth_basic = request.extensions.get("auth_basic")
        start = time.monotonic()
        attempt_number = 0

        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(effective_max_attempts),
                wait=wait_exponential_jitter(initial=1.0, max=30.0, exp_base=2, jitter=1.0),
                retry=(
                    retry_if_exception_type(_RETRYABLE_EXC)
                    | retry_if_exception_type(_RetryableStatus)
                ),
                reraise=True,
            ):
                with attempt:
                    attempt_number = attempt.retry_state.attempt_number
                    response = await super().handle_async_request(request)
                    await response.aread()  # body-consume async variant (HTTP/2-safe)
                    if _is_retryable_status(response):
                        retry_after = response.headers.get("Retry-After")
                        if retry_after is not None:
                            delay = _parse_retry_after(retry_after)
                            if delay is not None and delay > 0:
                                # D-32: asyncio.sleep is cancellable; CancelledError
                                # propagates naturally to the awaiting caller.
                                await asyncio.sleep(min(delay, _RETRY_AFTER_CAP_S))
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
                        # D-22 split: include user (operational) + redacted
                        # password directly in the extras so the matriz
                        # RedactingFilter's tuple-split branch is exercised AND
                        # the records emitted by this transport never carry the
                        # raw password literal.
                        if (
                            auth_basic is not None
                            and isinstance(auth_basic, tuple)
                            and (len(auth_basic) == 2)
                        ):
                            user, _password = auth_basic
                            if isinstance(user, str):
                                extra["auth_basic_user"] = user
                                extra["auth_basic_password"] = "***"
                        self._logger.warning("retry attempt", extra=extra)
                        raise _RetryableStatus(response)
                    return response
        except _RetryableStatus as exc:
            # Retry exhausted on status — return last response unmolested (D-05).
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
            if auth_basic is not None and isinstance(auth_basic, tuple) and len(auth_basic) == 2:
                user, _password = auth_basic
                if isinstance(user, str):
                    extra["auth_basic_user"] = user
                    extra["auth_basic_password"] = "***"
            self._logger.error(
                "retry exhausted (transport error)",
                extra=extra,
                exc_info=False,
            )
            raise

        # Unreachable: tenacity reraise=True guarantees either return or raise above.
        raise RuntimeError(  # pragma: no cover
            "AsyncRetryTransport.handle_async_request fell through tenacity loop"
        )
