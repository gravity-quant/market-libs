# Refresh Policy (retry + exp backoff + fail-cache)

Implementation blueprint for a `RefreshPolicy` decorator that wraps `refresh_fn`
to handle transient/permanent failures, exponential backoff with jitter, and
fail-cache to prevent auth-server DOS under sustained failures.

**Composition**: This is a **decorator over `refresh_fn`**, NOT a modification of
the TokenStore (from `tokenstore-3way.md`). The TokenStore stays unchanged; it
just receives a smarter `refresh_fn`.

**Target consumer**: Phase 10 (matriz `_token_store.py`) and Phase 9 (IOL
refresh_token BUG-03 — same retry/backoff pattern applies, exception classes
differ).

---

## Requirements (non-negotiable)

These emerged from spiking and apply to any production refresh in `market-libs`:

1. **No retry for permanent errors (401/403/400)**. Retrying wrong credentials never succeeds and wastes the auth server's time. The policy must propagate `PermanentRefreshError` immediately.
2. **Retry for transient errors (5xx, network timeouts)** with bounded attempts (default: 3 retries, configurable).
3. **Respect server's Retry-After header for 429**. `RateLimitedRefreshError` carries `retry_after_seconds`; the policy uses that instead of exp backoff for the next sleep.
4. **Fail-cache after exhausted retries**. Cache the last exception for a configurable window (default: 30s). Subsequent calls within the window raise the cached exception WITHOUT calling `refresh_fn`. This is the DOS prevention.
5. **Permanent errors do NOT fail-cache**. By design — caching them just delays the inevitable AND blocks credential-update recovery for `fail_cache_s` seconds.
6. **Thread-safe**. The policy uses `threading.Lock` for internal state, making it safe across the 3-way concurrency model (sync REST + async REST + daemon thread).
7. **Stdlib only** (`random`, `threading`, `time`, `typing`).

---

## How to Build It

### Error taxonomy

```python
class RefreshError(Exception):
    """Base for all refresh failures."""


class PermanentRefreshError(RefreshError):
    """401, 403, 400 — retrying won't help."""


class TransientRefreshError(RefreshError):
    """5xx, timeouts, network errors — retry may succeed."""


class RateLimitedRefreshError(TransientRefreshError):
    """429 — retry MUST respect server's Retry-After."""

    def __init__(self, message: str, retry_after_seconds: float) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds
```

These live in `_refresh_errors.py` (Phase 10 — recommended location). The adapter layer (`_refresh.py`) maps httpx exceptions to these.

### The Policy

```python
import random
import threading
import time
from typing import Callable

from ._refresh_errors import (
    PermanentRefreshError,
    RateLimitedRefreshError,
    RefreshError,
    TransientRefreshError,
)


class RefreshPolicy:
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

    def _read_fail_cache(self) -> BaseException | None:
        with self._lock:
            if self._cached_failure_at is None or self._cached_failure_exc is None:
                return None
            if (time.monotonic() - self._cached_failure_at) > self.fail_cache_s:
                self._cached_failure_at = None
                self._cached_failure_exc = None
                return None
            return self._cached_failure_exc

    def _store_fail_cache(self, exc: BaseException) -> None:
        if self.fail_cache_s <= 0:
            return
        with self._lock:
            self._cached_failure_at = time.monotonic()
            self._cached_failure_exc = exc

    def _compute_backoff(self, attempt: int, rate_limit_hint: float | None) -> float:
        if rate_limit_hint is not None:
            return rate_limit_hint
        backoff = min(self.base_backoff_s * (2 ** attempt), self.max_backoff_s)
        return backoff + random.uniform(0, self.jitter)

    def wrap(self, refresh_fn: Callable[[int], str]) -> Callable[[int], str]:
        def wrapped(call_id: int) -> str:
            cached = self._read_fail_cache()
            if cached is not None:
                raise cached

            last_exc: BaseException | None = None
            for attempt in range(self.max_retries + 1):
                try:
                    return refresh_fn(call_id)
                except PermanentRefreshError:
                    # No retry, no fail-cache. Propagate immediately.
                    raise
                except RateLimitedRefreshError as exc:
                    last_exc = exc
                    if attempt < self.max_retries:
                        self._sleep(self._compute_backoff(attempt, exc.retry_after_seconds))
                        continue
                    break
                except (TransientRefreshError, RefreshError) as exc:
                    last_exc = exc
                    if attempt < self.max_retries:
                        self._sleep(self._compute_backoff(attempt, None))
                        continue
                    break

            assert last_exc is not None
            self._store_fail_cache(last_exc)
            raise last_exc

        return wrapped
```

### Composition with TokenStore (from tokenstore-3way.md)

```python
# packages/matriz-client/src/matriz_client/_token_store.py (Phase 10)
from ._refresh_policy import RefreshPolicy
from ._refresh import MatrizRefresh
from ._refresh_errors import (
    PermanentRefreshError, TransientRefreshError, RateLimitedRefreshError
)


def build_token_store(state, *, max_retries=3, fail_cache_s=30.0):
    adapter = MatrizRefresh(
        http_client=state.http_client,
        base_url=state.base_url,
        username=state.username,
        password=state.password,
    )
    policy = RefreshPolicy(
        max_retries=max_retries,
        base_backoff_s=1.0,
        max_backoff_s=30.0,
        jitter=0.25,
        fail_cache_s=fail_cache_s,
    )
    return TokenStore(ttl_seconds=23 * 3600, refresh_fn=policy.wrap(adapter))
```

### Adapter (Phase 10 — maps httpx exceptions to RefreshError subclasses)

```python
# packages/matriz-client/src/matriz_client/_refresh.py (Phase 10)
import httpx

from ._refresh_errors import (
    PermanentRefreshError, TransientRefreshError, RateLimitedRefreshError
)


class MatrizRefresh:
    def __init__(self, http_client, base_url, username, password):
        self._http_client = http_client
        self._base_url = base_url
        self._username = username
        self._password = password

    def __call__(self, call_id: int) -> str:
        try:
            response = self._http_client.post(
                f"{self._base_url}/auth/getToken",
                json={"username": self._username, "password": self._password},
                timeout=10.0,
            )
        except httpx.TimeoutException as exc:
            raise TransientRefreshError("timeout during /auth/getToken") from exc
        except httpx.NetworkError as exc:
            raise TransientRefreshError(f"network error: {exc}") from exc

        if response.status_code == 401:
            raise PermanentRefreshError("invalid credentials (401)")
        if response.status_code == 403:
            raise PermanentRefreshError("forbidden (403)")
        if response.status_code == 429:
            retry_after = float(response.headers.get("Retry-After", "10"))
            raise RateLimitedRefreshError(
                f"rate-limited (429); Retry-After={retry_after}",
                retry_after_seconds=retry_after,
            )
        if 500 <= response.status_code < 600:
            raise TransientRefreshError(f"server error {response.status_code}: {response.text[:200]}")
        response.raise_for_status()  # other 4xx — uncommon, propagates as httpx.HTTPStatusError

        # Matriz puts the bearer in the response header
        token = response.headers.get("X-Auth-Token")
        if not token:
            raise TransientRefreshError("response missing X-Auth-Token header")
        return token
```

---

## What to Avoid

### Don't fail-cache permanent errors

If `PermanentRefreshError` is cached, every caller within the fail-cache window
gets the SAME 401 — even after the operator fixes the credentials via
`configure(username=..., password=...)`. Permanent errors are caller-fixable;
caching them blocks recovery.

The policy already gets this right (`PermanentRefreshError` short-circuits the
loop and re-raises immediately). Do NOT add `permanent_fail_cache_s` "for
symmetry" — it's actively harmful.

### Don't retry inside `refresh_fn`

The adapter (`MatrizRefresh.__call__`) should NEVER catch and retry. That's
the policy's job. If the adapter retries, the policy's accounting breaks
(it sees one "attempt" when the adapter actually did three).

The adapter MUST:
1. Make ONE HTTP request
2. Map the result to either a return value or a `RefreshError` subclass
3. Return / raise

### Don't put policy inside the TokenStore

Same separation-of-concerns argument as the TokenStore-vs-policy split.
The TokenStore is about **lock semantics** ("exactly 1 refresh under thundering
herd, cross-context-safe"). The policy is about **retry semantics** ("retry on
5xx, not on 401, with backoff"). Combining them in one class makes both harder
to reason about and harder to test.

If you find yourself wanting to put retry logic inside `TokenStoreDCL`, stop —
that's the policy's job. The decorator pattern works for a reason.

### Don't let `call_id` become a unique-nonce contract

`call_id` is "the Nth refresh attempt from TokenStore's perspective". It does NOT
change between policy retries — both attempts inside one `wrapped(call_id)`
call see the same `call_id`. This is correct design.

If your auth API needs a unique nonce per HTTP request (e.g., to prevent
replay), the adapter MUST generate that nonce internally. Don't rely on
`call_id` being unique per HTTP request.

### Don't make `fail_cache_s` longer than the TTL

For matriz (TTL 23h), `fail_cache_s` of 30s is fine. But for very short TTLs
(say, a 5-minute access token), a `fail_cache_s` of 30s means 10% of the time
the cache is useless because the TTL already expired. Rough rule: keep
`fail_cache_s <= ttl / 10`.

---

## Constraints

### Sync caller behavior during retry sleeps

When a sync caller (`Client.get_X()`) triggers a refresh that needs to retry,
the TokenStore holds `state_lock` for the duration of all retries + backoffs.
Other sync callers WAIT until the retry sequence completes.

For matriz's typical config (max_retries=3, base_backoff_s=1.0), the worst-case
wait is roughly `1 + 2 + 4 = 7 seconds` + jitter (max_backoff caps it). This
is acceptable for token refresh frequency (~once per 23h) but **document it
clearly in matriz's docs** so users aren't surprised.

### Async caller behavior during retry sleeps

The refresh runs in `asyncio.to_thread` (per TokenStore's `get_async`), so
backoff `time.sleep` happens in a worker thread → **event loop is NOT blocked**.
Other coroutines continue progressing. This is the asymmetric benefit of using
DCL with `asyncio.to_thread`.

### `time.sleep` is the default — inject for tests

`RefreshPolicy(sleep_fn=fake_sleep)` lets tests run instantly. The default is
`time.sleep` for production use. Don't try to use `asyncio.sleep` here — the
policy runs in a sync context (it's called from inside the state_lock).

### Backoff is uniform-jittered, not decorrelated-jittered

The `random.uniform(0, jitter)` adds up to `jitter` seconds (default 0.25s).
This is enough decorrelation for single-instance use. If multiple matriz Client
instances run in the same process (unlikely but possible), correlated retries
COULD cluster. For Phase 11+ (multi-Client scenarios), consider switching to
decorrelated jitter: `sleep = random.uniform(base, prev_sleep * 3)`.

### Policy stats are not exposed in production code yet

The policy has `.stats()` returning `{attempts, retries, fail_cache_hits, fail_cache_active}`.
This is useful for debugging and for `gsd-debug` sessions but is NOT routed
to logging/metrics yet. Phase 11 (harness hardening + structured logging) is
the natural place to add Prometheus/opentelemetry hooks.

---

## Origin

Synthesized from spike: **003-tokenstore-refresh-policy** (VALIDATED).

Composes with the WINNER from `tokenstore-3way.md` (Spike 001c).

The integration test `sources/003-tokenstore-refresh-policy/test_integration.py`
validates the end-to-end Phase 10 scenario:
- 7 integration tests covering happy path, transient retry, permanent
  propagation, fail-cache DOS prevention, async path, recovery, and 3-way
  under failure.
- **Headline result**: 10 concurrent sync callers post-failure → **0 new
  auth server hits** (all served from fail-cache).
