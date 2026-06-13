"""RetryTransport — sync httpx transport with bounded retries + full-jitter backoff.

Phase 8 RELY-01..04 + D-01/D-04/D-07/D-08/D-19/D-31. ámbito canary delivery of the
canonical RetryTransport pattern that iol/higyrus/matriz will duplicate.

Invariants:

- Mutation gate (D-01 / RELY-03): ``request.extensions["idempotent"]`` set by the
  shell ``_request()`` from ``RequestSpec.idempotent``. Non-idempotent requests
  pass through with no retry loop — critical for matriz Primary API HTTP-GET-for-
  mutation quirk (``new_order`` is method=GET but idempotent=False).
- Retryable surfaces (D-07): HTTP status ``408/409/429/5xx`` + transport-level
  ``httpx.ConnectError`` / ``ConnectTimeout`` / ``ReadTimeout``. Domain exceptions
  (``<Pkg>APIError``/``AuthError``) NEVER reach this layer.
- Backoff (D-08): full-jitter exponential — ``initial=1s, max=30s, exp_base=2``
  via ``tenacity.wait_exponential_jitter``.
- ``Retry-After`` (D-04): honored with cap at 60 s; supports RFC 9110 §10.2.3
  delta-seconds AND HTTP-date (parsed via stdlib ``parsedate_to_datetime``).
- ``max_attempts <= 1`` (D-19): retry loop bypassed entirely → 1 outgoing request.

The transport emits ``WARNING`` per retry attempt and ``ERROR`` on terminal
transport failures with the structured field set defined in D-09. All log records
flow through ``logging.getLogger("ambito_financiero_client")`` which has the
``RedactingFilter`` attached at ``__init__.py`` (LOG-02).
"""

from __future__ import annotations

import logging
import time
from email.utils import parsedate_to_datetime
from typing import Any

import httpx
from tenacity import (
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

__all__ = ["RetryTransport"]


# ---------------------------------------------------------------------------
# Module-level constants (D-07 / D-04)
# ---------------------------------------------------------------------------

_RETRYABLE_EXC: tuple[type[Exception], ...] = (
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
)
_RETRYABLE_STATUS: frozenset[int] = frozenset({408, 409, 429, *range(500, 600)})
_RETRY_AFTER_CAP_S: float = 60.0
_LOGGER_NAME = "ambito_financiero_client"


# ---------------------------------------------------------------------------
# Internal sentinel + parsing helpers
# ---------------------------------------------------------------------------


class _RetryableStatus(Exception):
    """Internal sentinel signaling a retryable HTTP status to the tenacity loop.

    NOT a subclass of ``AmbitoFinancieroAPIError`` — keeps D-07 invariant
    (domain exceptions never in ``retry_on=``). Carries the ``response`` so
    the outer ``except _RetryableStatus`` block can return the final response
    unmolested when retries exhaust (D-05).
    """

    def __init__(self, response: httpx.Response) -> None:
        super().__init__(f"retryable status: {response.status_code}")
        self.response = response


def _is_retryable_status(response: httpx.Response | None) -> bool:
    """Return True iff response status code is in the locked retryable set (D-07)."""
    return response is not None and response.status_code in _RETRYABLE_STATUS


def _parse_retry_after(value: str) -> float | None:
    """Parse RFC 9110 §10.2.3 Retry-After (delta-seconds OR HTTP-date).

    Returns the number of seconds to wait (clamped at ``>= 0``), or ``None`` if
    the header value is malformed. Callers apply the 60-second cap separately.
    """
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            target = parsedate_to_datetime(value).timestamp()
            return max(0.0, target - time.time())
        except (TypeError, ValueError):
            return None


# ---------------------------------------------------------------------------
# RetryTransport (D-01 / D-31)
# ---------------------------------------------------------------------------


class RetryTransport(httpx.HTTPTransport):
    """``httpx.HTTPTransport`` subclass with bounded retries + full-jitter backoff.

    See module docstring for invariants. ``max_attempts`` is the total number of
    outgoing requests when retries are exhausted (1 initial + N-1 retries).
    Callers map their ``max_retries=N`` to ``max_attempts=N+1`` (anthropic/openai
    SDK semantics; D-19).
    """

    def __init__(self, *, max_attempts: int = 2, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._max_attempts = max(max_attempts, 1)
        self._logger = logging.getLogger(_LOGGER_NAME)

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        # D-01 mutation gate: non-idempotent → pass-through with no retry loop.
        if not request.extensions.get("idempotent", False):
            return super().handle_request(request)
        # D-19 bypass: max_attempts <= 1 → 1 outgoing request total.
        if self._max_attempts <= 1:
            return super().handle_request(request)

        request_id = request.extensions.get("request_id", "")
        endpoint_name = request.extensions.get("endpoint_name", "")
        account_id = request.extensions.get("account_id")
        start = time.monotonic()
        attempt_number = 0

        try:
            for attempt in Retrying(
                stop=stop_after_attempt(self._max_attempts),
                wait=wait_exponential_jitter(initial=1.0, max=30.0, exp_base=2, jitter=1.0),
                retry=(
                    retry_if_exception_type(_RETRYABLE_EXC)
                    | retry_if_exception_type(_RetryableStatus)
                ),
                reraise=True,
            ):
                with attempt:
                    attempt_number = attempt.retry_state.attempt_number
                    response = super().handle_request(request)
                    response.read()  # body-consume before status check (Phase 7 D-06)
                    if _is_retryable_status(response):
                        retry_after = response.headers.get("Retry-After")
                        if retry_after is not None:
                            delay = _parse_retry_after(retry_after)
                            if delay is not None and delay > 0:
                                time.sleep(min(delay, _RETRY_AFTER_CAP_S))
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
            self._logger.error(
                "retry exhausted (transport error)",
                extra=extra,
                exc_info=False,
            )
            raise

        # Unreachable: tenacity reraise=True guarantees either return or raise above.
        raise RuntimeError(  # pragma: no cover
            "RetryTransport.handle_request fell through tenacity loop"
        )
