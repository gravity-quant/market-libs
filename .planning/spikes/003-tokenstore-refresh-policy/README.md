---
spike: 003
name: tokenstore-refresh-policy
type: standard
validates: "Given a RefreshPolicy decorator (retry + exp backoff + fail-cache + transient/permanent classification) wrapping a refresh_fn, when composed with the TokenStoreDCL from 001c, then sustained refresh failures do NOT DOS the auth server, permanent failures propagate without retry, and transient failures recover gracefully"
verdict: VALIDATED
related: [001c, 002]
tags: [refresh-policy, retry, backoff, fail-cache, dos-prevention, phase-10-ready]
---

# Spike 003: TokenStore Refresh Policy

## What This Validates

**Given** una `RefreshPolicy` decorator que envuelve `refresh_fn` con:
- Retry hasta N veces para `TransientRefreshError` (5xx, timeouts)
- NO retry para `PermanentRefreshError` (401, 403)
- Respeto del `Retry-After` para `RateLimitedRefreshError` (429)
- Exponential backoff con jitter (cap configurable)
- **Fail-cache**: después de exhausted retries, cachea el último error por N segundos para prevenir thundering-herd contra el auth server

**When** se compone con `TokenStoreDCL` del Spike 001c (el winner del trio):
```python
policy = RefreshPolicy(max_retries=3, base_backoff_s=1.0, fail_cache_s=30.0)
wrapped = policy.wrap(raw_refresh)
store = TokenStoreDCL(ttl_seconds=23*3600, refresh_fn=wrapped)
```

**Then** el sistema completo (lock primitive + retry policy):
- Maneja transient failures sin propagar al caller
- Propaga permanent failures inmediatamente
- Previene DOS del auth server bajo failures sustenidas (fail-cache)
- Mantiene la propiedad "1 refresh por TTL window" del Spike 002

## Research

**Approach overview:**

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Where the policy lives | Decorator over `refresh_fn` | Separation of concerns — TokenStore is about lock semantics, policy is about retry semantics. Compose cleanly. |
| Error taxonomy | `Permanent` / `Transient` / `RateLimited` (subclass of Transient) | Maps cleanly to HTTP status code groups. `refresh_fn` adapter at integration time decides classification. |
| Backoff formula | `min(base × 2^attempt, max_backoff) + jitter` | Standard exp backoff; jitter prevents synchronized retries from multiple Client instances |
| Fail-cache window | Configurable (e.g., 30s for matriz) | Long enough that auth server has time to recover, short enough that user-facing errors clear quickly |
| Permanent errors fail-cache? | **NO** | Permanent errors will keep failing forever; caching them just delays the inevitable AND blocks any legitimate state change (credential update) for `fail_cache_s` seconds |
| Internal thread safety | `threading.Lock` | Same primitive as TokenStore; policy may be called from any context |

## How to Run

```bash
cd .planning/spikes/003-tokenstore-refresh-policy
python3 test_policy.py        # 9 isolation tests for the policy alone
python3 test_integration.py   # 7 integration tests with TokenStoreDCL
```

All tests use `FakeSleep` so they run instantly (~100ms total).

## What to Expect

`test_policy.py`:
```
✓ happy_path_no_retry: 1 attempt, 0 retries, 0 sleep calls
✓ transient_then_success: 1 retry, backoff=1.0s
✓ permanent_no_retry: raises immediately, no retry, no fail-cache
✓ exp_backoff_growth: [1.0, 2.0, 4.0]
✓ exp_backoff_capped: [10.0, 15.0, 15.0]
✓ rate_limited_uses_retry_after: backoff=7.5s (from server hint)
✓ exhausted_then_fail_cache: 3 attempts, 2 backoffs, next call short-circuited
✓ fail_cache_expires: after window, retry succeeds
✓ concurrent_callers_share_fail_cache: 10 threads → 10 cached errors, 0 new refresh calls
```

`test_integration.py`:
```
✓ happy_path_sync
✓ transient_then_success_sync
✓ permanent_propagates
✓ fail_cache_protects_against_thundering (10 sync callers → 0 new auth server hits)
✓ async_caller_path_works_with_policy
✓ recovery_after_fail_cache_expires
✓ 3way_with_policy_under_failure: 1 retry sequence, 3 contexts agree
```

## Investigation Trail

### Iteration 1 — Built the policy in isolation

Wrote `RefreshPolicy.wrap(refresh_fn)` that returns a wrapped callable. The wrapped callable:
1. Checks fail-cache → raise cached exception if active
2. Attempts up to `max_retries + 1` times
3. Classifies each exception (`Permanent` → raise immediately; `RateLimited` → use `retry_after_seconds`; `Transient` → exp backoff)
4. On exhausted retries, stores the last exception in fail-cache and raises

All 9 isolation tests passed first try.

### Iteration 2 — Built integration tests with TokenStoreDCL

Composed policy with TokenStore. Discovered that `tok-N` naming in my test assertions was wrong: I'd assumed `call_id` increments per underlying refresh call, but actually the policy preserves `call_id` through retries (it comes from TokenStore's `_refresh_count`, set ONCE per call to wrapped refresh).

This is the CORRECT design — `call_id` is "this is the Nth refresh attempt the TokenStore has tried", not "this is the Nth time refresh_fn has been called". If you want per-underlying-call IDs, that's a concern for the refresh adapter (e.g., for logging), not the policy.

Fixed test assertions to use the correct expected values. All 7 integration tests then passed.

### Iteration 3 — Verified the DOS-prevention scenario explicitly

`test_fail_cache_protects_against_thundering_after_failure`:
1. Set TTL to 0.001s (effectively always refresh — simulates the worst case)
2. Set fail_cache_s to 60s
3. First TokenStore call: 3 transient attempts → exhausted → fail-cache populated
4. 10 concurrent threads call `store.get_sync()` afterwards
5. **Observed: 0 new underlying refresh calls.** All 10 threads got the cached `TransientRefreshError` immediately.
6. `policy.stats()["fail_cache_hits"] == 10`

This is the headline result of this spike: **the auth server is protected**.

### Iteration 4 — Verified async path + 3-way works

Composed with `store.get_async()` (which uses `asyncio.to_thread` for refresh):
- The policy's `time.sleep` (replaced by `FakeSleep` in tests) runs in the worker thread → event loop NOT blocked during backoff sleeps
- Retry logic flows through `to_thread` correctly

3-way integration (sync + async + daemon, all hitting expired-token):
- Only 1 retry sequence happens (TokenStore lock serializes the refresh attempts)
- All 3 contexts receive the same final token
- The wrapped refresh was called exactly 2 times (1 transient + 1 ok)

### Edge case considered but not implemented as a test

**What if the refresh adapter raises an UNEXPECTED exception** (not a `RefreshError` subclass)?
Current code: `except RefreshError` catches subclasses only; anything else propagates up unchanged.

For Phase 10, the adapter layer (httpx → exception) should be strict about always raising `RefreshError` subclasses. If something leaks through (e.g., `httpx.NetworkError` from a misconfigured adapter), the policy will pass it through without retry, which is the safe-but-strict behavior.

## Results

**Verdict: VALIDATED ✓**

### Pass criteria (all met)

| Behavior | Test | Status |
|----------|------|--------|
| Happy path (no retry) | `test_happy_path_no_retry` | ✓ |
| Transient → retry → success | `test_transient_then_success` | ✓ |
| Permanent → no retry → propagate | `test_permanent_no_retry` | ✓ |
| Exp backoff growth | `test_exp_backoff_growth` | ✓ [1.0, 2.0, 4.0] |
| Backoff capping | `test_exp_backoff_capped` | ✓ [10.0, 15.0, 15.0] |
| Rate-limit respect | `test_rate_limited_uses_retry_after` | ✓ uses server hint |
| Exhausted retries fail-cache | `test_exhausted_retries_then_fail_cache` | ✓ |
| Fail-cache expires correctly | `test_fail_cache_expires_then_retry_succeeds` | ✓ |
| Concurrent callers share fail-cache | `test_concurrent_callers_share_fail_cache` | ✓ 10 threads → 0 new calls |
| TokenStore + policy happy | `test_happy_path_sync` | ✓ |
| TokenStore + policy retry | `test_transient_then_success_sync` | ✓ |
| TokenStore + policy permanent | `test_permanent_propagates_through_store` | ✓ |
| **DOS protection via fail-cache through TokenStore** | `test_fail_cache_protects_against_thundering_after_failure` | ✓ **headline** |
| Async path with policy | `test_async_caller_path_works_with_policy` | ✓ |
| Recovery after fail-cache window | `test_recovery_after_fail_cache_expires` | ✓ |
| 3-way under failure | `test_3way_with_policy_under_failure` | ✓ |

### Pros

- **Clean separation of concerns**: TokenStore (lock semantics) + RefreshPolicy (retry semantics) compose without coupling.
- **DOS protection works at the integration level**: validated with 10 concurrent post-failure callers → 0 new auth server hits.
- **Permanent vs. transient classification is explicit and pluggable** via exception types.
- **`Retry-After` support** lets the policy respect server hints — important for 429 responses.
- **Fail-cache window is configurable** — different services can pick different durations.
- **Stdlib only** (`random`, `threading`, `time`, `typing`) — no new deps.

### Cons / open issues

1. **Permanent errors don't fail-cache** — this is by design but worth re-thinking. If matriz's auth server returns 401 forever after a credential change, every TokenStore caller pays the round-trip cost for at most 1 attempt each. Could add a "permanent fail-cache" with its own (shorter?) window to mitigate, but adds API surface.

2. **The retry sleep happens INSIDE the TokenStore state_lock** when called from a sync context. This is correct (single retry sequence) but means sync callers wait for the full retry sequence including backoffs. For matriz's typical 1-3 retry budget with 1-4s backoffs, this is acceptable. Could surprise users — flag for Phase 10 documentation.

3. **Async retry waits also happen via `asyncio.to_thread`** — backoff sleep is in a worker thread, so event loop is free. ✓

4. **Jitter is uniform 0..jitter, not the typical "decorrelated jitter"** — simple is fine, but if multiple matriz Client instances are sharing the same auth server (unlikely), correlated retries could cluster. Phase 10 plan can decide.

5. **No metric export** — the policy has `.stats()` but no Prometheus / opentelemetry hooks. Phase 11 (harness hardening) is the natural place to add this.

## Impact on Remaining Spikes

- **Spike 004 (real httpx)** can now use this policy directly — the adapter layer just needs to map `httpx.HTTPStatusError` to the right `RefreshError` subclass.
- **Spike 005 (token expiry semantics)** is independent — it's about TTL handling, not refresh policy.
- **Spike 006 (cancellation during refresh)** becomes more interesting now: what happens if a coroutine cancels during a backoff sleep? Test gap.

## Phase 10 Implementation Guidance

This pattern is **production-ready for Phase 10's `_token_store.py`**.

Recommended composition:
```python
# packages/matriz-client/src/matriz_client/_token_store.py
from ._refresh_policy import RefreshPolicy
from ._refresh_errors import PermanentRefreshError, TransientRefreshError, RateLimitedRefreshError

class _MatrizRefresh:
    """Adapter that maps matriz's auth API to (Permanent|Transient|RateLimited)RefreshError."""
    def __init__(self, http_client, base_url, username, password):
        ...
    def __call__(self, call_id: int) -> str:
        try:
            r = self._http_client.post(f"{self._base_url}/auth/getToken", json={...})
        except httpx.TimeoutException as e:
            raise TransientRefreshError(...) from e
        except httpx.NetworkError as e:
            raise TransientRefreshError(...) from e
        if r.status_code == 401:
            raise PermanentRefreshError("invalid credentials")
        if r.status_code == 429:
            retry_after = float(r.headers.get("Retry-After", "10"))
            raise RateLimitedRefreshError(f"429: {r.text}", retry_after_seconds=retry_after)
        if 500 <= r.status_code < 600:
            raise TransientRefreshError(f"{r.status_code}: {r.text}")
        r.raise_for_status()  # any other 4xx → propagates (rare)
        return r.headers["X-Auth-Token"]


# In Client.__init__:
adapter = _MatrizRefresh(state.http_client, state.base_url, ...)
policy = RefreshPolicy(max_retries=3, base_backoff_s=1.0, fail_cache_s=30.0)
state.token_store = TokenStore(ttl_seconds=23*3600, refresh_fn=policy.wrap(adapter))
```

The adapter, policy, and store are three separate concerns. Phase 10 plan must:
1. Decide adapter location (`_refresh.py`? `_token_store.py`?)
2. Decide policy params (max_retries=3? base_backoff_s=1.0? fail_cache_s=30.0?) — likely configurable via `configure()`
3. Document the contract that custom adapters must classify exceptions correctly
