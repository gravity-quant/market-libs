"""RefreshPolicy — retry / exp backoff / fail-cache decorator (Phase 10 REFAC-04).

Wraps a ``refresh_fn(call_id: int) -> str`` with:

- ``PermanentRefreshError`` → propagate immediately (no retry, no fail-cache).
- ``TransientRefreshError`` → retry up to ``max_retries`` with exp backoff
  envelope ``base_backoff_s * 2**attempt`` capped at ``max_backoff_s``, plus
  symmetric jitter in ``[-jitter, +jitter]``.
- ``RateLimitedRefreshError`` → retry honoring ``retry_after_seconds``
  (capped at ``max_backoff_s``, no jitter).
- Exhausted budget → cache the last exception for ``fail_cache_s`` seconds
  (auth-server DOS prevention).

Thread safety: an internal ``threading.Lock`` guards the fail-cache state,
so the wrapped callable is safe to call from sync threads, the WS daemon
thread, and from inside ``asyncio.to_thread`` offloads. ``sleep_fn`` is
injectable so tests can run with zero wall-clock delay.
"""

from __future__ import annotations

import random
import threading
import time
from collections.abc import Callable

from matriz_client._refresh_errors import (
    PermanentRefreshError,
    RateLimitedRefreshError,
    RefreshError,
    TransientRefreshError,
)

__all__ = ["RefreshPolicy"]


class RefreshPolicy:
    """Decorator over a ``refresh_fn`` applying retry + backoff + fail-cache."""

    def __init__(
        self,
        *,
        max_retries: int = 3,
        base_backoff_s: float = 1.0,
        max_backoff_s: float = 30.0,
        jitter: float = 0.25,
        fail_cache_s: float = 30.0,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self.max_retries = max_retries
        self.base_backoff_s = base_backoff_s
        self.max_backoff_s = max_backoff_s
        self.jitter = jitter
        self.fail_cache_s = fail_cache_s
        self._sleep_fn = sleep_fn
        self._lock = threading.Lock()
        self._cached_failure_at: float | None = None
        self._cached_failure_exc: BaseException | None = None

    def _compute_backoff(self, attempt: int, retry_after: float | None) -> float:
        """Compute backoff for ``attempt``; honors ``retry_after`` server hint."""
        if retry_after is not None:
            return min(retry_after, self.max_backoff_s)
        base = min(self.base_backoff_s * (2**attempt), self.max_backoff_s)
        jitter_factor: float = 1.0 + float(random.uniform(-self.jitter, self.jitter))
        return float(base * jitter_factor)

    def _read_fail_cache(self) -> BaseException | None:
        """Return the cached exception if the fail-cache window is still active."""
        with self._lock:
            if self._cached_failure_at is None or self._cached_failure_exc is None:
                return None
            if (time.monotonic() - self._cached_failure_at) >= self.fail_cache_s:
                self._cached_failure_at = None
                self._cached_failure_exc = None
                return None
            return self._cached_failure_exc

    def _store_fail_cache(self, exc: BaseException) -> None:
        """Cache the exhaustion exception for ``fail_cache_s`` seconds."""
        if self.fail_cache_s <= 0:
            return
        with self._lock:
            self._cached_failure_at = time.monotonic()
            self._cached_failure_exc = exc

    def wrap(self, refresh_fn: Callable[[int], str]) -> Callable[[int], str]:
        """Return a wrapped callable that applies the retry/backoff/fail-cache policy."""

        def wrapped(call_id: int) -> str:
            cached = self._read_fail_cache()
            if cached is not None:
                raise cached  # DOS prevention.

            last_exc: BaseException | None = None
            for attempt in range(self.max_retries + 1):
                try:
                    return refresh_fn(call_id)
                except PermanentRefreshError:
                    raise  # NO retry, NO fail-cache.
                except RateLimitedRefreshError as exc:
                    last_exc = exc
                    if attempt < self.max_retries:
                        self._sleep_fn(self._compute_backoff(attempt, exc.retry_after_seconds))
                        continue
                    break
                except TransientRefreshError as exc:
                    last_exc = exc
                    if attempt < self.max_retries:
                        self._sleep_fn(self._compute_backoff(attempt, None))
                        continue
                    break
                except RefreshError as exc:
                    # Unknown RefreshError subclass → treat as transient.
                    last_exc = exc
                    if attempt < self.max_retries:
                        self._sleep_fn(self._compute_backoff(attempt, None))
                        continue
                    break

            assert last_exc is not None
            self._store_fail_cache(last_exc)
            raise last_exc

        return wrapped
