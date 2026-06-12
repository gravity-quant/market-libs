"""RefreshPolicy decorator: retry + exp backoff + fail-cache around a refresh_fn.

Composition with TokenStore (from 001c):
    raw_refresh = lambda cid: httpx_post("/auth/token", ...)  # raises on failure
    policy = RefreshPolicy(max_retries=3, base_backoff_s=1.0, fail_cache_s=30.0)
    wrapped = policy.wrap(raw_refresh)
    store = TokenStoreDCL(ttl_seconds=23 * 3600, refresh_fn=wrapped)

The TokenStore is unchanged — it just sees a refresh_fn that's smarter.

Design choices:
- **PermanentRefreshError** → no retry, immediate propagation. Wrong credentials
  don't get better with retries.
- **TransientRefreshError** → retry up to max_retries with exp backoff + jitter.
- **RateLimitedRefreshError** → respect server's Retry-After; counts as 1 retry.
- **Fail-cache**: after max_retries exhausted, store the failure timestamp + class.
  Subsequent calls within `fail_cache_s` raise the cached error immediately
  WITHOUT calling refresh_fn — this is the DOS prevention.
- **Thread safety**: the policy itself uses a `threading.Lock` for its internal
  state (fail_cache, last_failure_at). This makes it safe to use across the
  3-way scenario from inside TokenStore's state_lock.

The policy does NOT manage clocks — it uses `time.monotonic()` consistently.
"""

from __future__ import annotations

import random
import threading
import time
from typing import Callable

from errors import (
    PermanentRefreshError,
    RateLimitedRefreshError,
    RefreshError,
    TransientRefreshError,
)


class RefreshPolicy:
    """Wraps a refresh_fn with retry + exp backoff + fail-cache.

    Parameters
    ----------
    max_retries : int
        Maximum retry attempts for transient failures. 0 = no retries (raise on first failure).
    base_backoff_s : float
        Initial backoff in seconds. Doubles each retry (capped at max_backoff_s).
    max_backoff_s : float
        Upper bound on backoff between retries.
    jitter : float
        Random jitter added to backoff (uniform 0..jitter seconds).
    fail_cache_s : float
        After all retries exhausted, cache the failure for this many seconds.
        Subsequent calls within the window raise the cached exception immediately.
        Set to 0 to disable fail-cache.
    sleep_fn : Callable[[float], None]
        Sleep function (injectable for tests). Defaults to time.sleep.
    """

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
        self._sleep = sleep_fn

        self._lock = threading.Lock()
        self._cached_failure_at: float | None = None
        self._cached_failure_exc: BaseException | None = None
        # Observability
        self._attempts: int = 0
        self._retries: int = 0
        self._fail_cache_hits: int = 0

    def _compute_backoff(self, attempt: int, rate_limit_hint: float | None) -> float:
        if rate_limit_hint is not None:
            # Server explicitly told us how long to wait
            return rate_limit_hint
        backoff = min(self.base_backoff_s * (2 ** attempt), self.max_backoff_s)
        backoff += random.uniform(0, self.jitter)
        return backoff

    def _read_fail_cache(self) -> BaseException | None:
        with self._lock:
            if self._cached_failure_at is None or self._cached_failure_exc is None:
                return None
            now = time.monotonic()
            if (now - self._cached_failure_at) > self.fail_cache_s:
                # Window expired — clear cache and let retry happen
                self._cached_failure_at = None
                self._cached_failure_exc = None
                return None
            self._fail_cache_hits += 1
            return self._cached_failure_exc

    def _store_fail_cache(self, exc: BaseException) -> None:
        if self.fail_cache_s <= 0:
            return
        with self._lock:
            self._cached_failure_at = time.monotonic()
            self._cached_failure_exc = exc

    def wrap(self, refresh_fn: Callable[[int], str]) -> Callable[[int], str]:
        """Return a wrapped refresh_fn that applies the policy."""

        def wrapped(call_id: int) -> str:
            # Fail-cache short-circuit
            cached = self._read_fail_cache()
            if cached is not None:
                raise cached

            last_exc: BaseException | None = None
            for attempt in range(self.max_retries + 1):
                with self._lock:
                    self._attempts += 1
                try:
                    return refresh_fn(call_id)
                except PermanentRefreshError as exc:
                    # No retry — propagate immediately. Do NOT fail-cache:
                    # permanent errors will keep failing forever; caller code
                    # should not be DOSed by repeated raise-cached-error after
                    # already getting a clear permanent signal.
                    raise
                except RateLimitedRefreshError as exc:
                    last_exc = exc
                    if attempt < self.max_retries:
                        with self._lock:
                            self._retries += 1
                        backoff = self._compute_backoff(attempt, exc.retry_after_seconds)
                        self._sleep(backoff)
                        continue
                    break
                except TransientRefreshError as exc:
                    last_exc = exc
                    if attempt < self.max_retries:
                        with self._lock:
                            self._retries += 1
                        backoff = self._compute_backoff(attempt, None)
                        self._sleep(backoff)
                        continue
                    break
                except RefreshError as exc:
                    # Unknown subclass — treat as transient by default
                    last_exc = exc
                    if attempt < self.max_retries:
                        with self._lock:
                            self._retries += 1
                        backoff = self._compute_backoff(attempt, None)
                        self._sleep(backoff)
                        continue
                    break

            # Exhausted retries — fail-cache the last exception
            assert last_exc is not None
            self._store_fail_cache(last_exc)
            raise last_exc

        return wrapped

    def stats(self) -> dict:
        with self._lock:
            return {
                "attempts": self._attempts,
                "retries": self._retries,
                "fail_cache_hits": self._fail_cache_hits,
                "fail_cache_active": self._cached_failure_at is not None,
            }
