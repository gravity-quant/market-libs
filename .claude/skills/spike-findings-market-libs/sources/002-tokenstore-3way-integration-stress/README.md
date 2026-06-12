---
spike: 002
name: tokenstore-3way-integration-stress
type: standard
validates: "Given the 001c DCL TokenStore, when 100 sync + 100 async + 5 daemon callers compete concurrently across 2 phases (cold start + TTL expiry), then refreshes ≤ 2, zero errors, single atomic token per phase, cached-read latency P95 < 100ms"
verdict: VALIDATED
related: [001a, 001b, 001c]
tags: [stress, integration, dcl, validation, phase-10-ready]
---

# Spike 002: TokenStore 3-way Integration Stress Test

## What This Validates

**Given** el patrón DCL del Spike 001c (`threading.Lock` + per-loop `asyncio.Lock` + refresh via `asyncio.to_thread`).

**When** se aplica el escenario realista de Phase 10:
- 100 sync REST callers (ThreadPoolExecutor)
- 100 async REST callers (single asyncio.run loop)
- 5 daemon threads (simulando ws_client)
- Todos arrancan con barrier sync
- Fase 1: cold-start con store vacío → fuerza 1 refresh
- Fase 2: TTL expira (sleep 0.6s entre fases) → fuerza 1 refresh adicional

**Then** se verifican 5 pass criteria:
1. Total refreshes ≤ 4 (ideal: 2)
2. Zero errors
3. Phase 1 atomicity: 1 unique token entre 205 callers
4. Phase 2 atomicity: ≤ 2 unique tokens (allowing interleave)
5. Async cached-read P95 < 100ms

## How to Run

```bash
cd .planning/spikes/002-tokenstore-3way-integration-stress
python3 test_stress.py
```

`store.py` es una copia textual de 001c — esto valida el winner intacto, no una re-implementación.

## What to Expect

```
Phase 1: 205 callers → 1 refresh, 0 errors, 1 unique token, ~60ms duration
Phase 2: 205 callers → 1 refresh, 0 errors, 1 unique token, ~60ms duration

Async cached-read latency:
  P50 = 0.001ms  ← cached reads bypass all locking via the fast path
  P95 = 0.001ms  ← idem
  P99 = ~58ms    ← coroutine que coincidió con el refresh in-flight

Sync REST latency:
  P50 = ~57ms    ← todos los syncs esperan el refresh (no fast path para sync)
  P95 = ~58ms    ← idem
```

## Results

**Verdict: VALIDATED ✓**

Output del run actual:

```
Phase 1: cold start — 100 sync + 100 async + 5 daemon all hit empty store
  Duration: 63.2ms
  Refreshes: 1
  Total callers: 205
  Errors: 0
  Unique tokens: 1
  ✓ All 205 callers got identical token

Phase 2: TTL expiry — wait 0.6s, then fire the same workload again
  Duration: 57.7ms
  Refreshes in this phase: 1
  Total refreshes so far: 2
  Errors: 0
  Unique tokens in phase 2: 1

Latency — Phase 1:
    sync REST       N=100  P50=56.6ms   P95=57.6ms   P99=59.4ms   max=59.4ms
    async REST      N=100  P50=0.001ms  P95=0.001ms  P99=58.6ms   max=58.6ms
    daemon thread   N=  5  P50=58.9ms   P95=59.0ms   P99=59.0ms   max=59.0ms

Latency — Phase 2:
    sync REST       N=100  P50=51.8ms   P95=52.6ms   P99=53.2ms   max=53.2ms
    async REST      N=100  P50=0.001ms  P95=0.001ms  P99=52.5ms   max=52.5ms
    daemon thread   N=  5  P50=53.0ms   P95=54.3ms   P99=54.3ms   max=54.3ms

Active async_locks: 2 (1 per asyncio.run loop — bridge loop NOT used in this test)
```

### Pass criteria

| Criterion | Threshold | Actual | Status |
|-----------|-----------|--------|--------|
| Total refreshes | ≤ 4 | 2 | ✓ minimum possible |
| Errors | 0 | 0 | ✓ |
| Phase 1 atomicity | 1 unique token | 1 | ✓ |
| Phase 2 atomicity | ≤ 2 tokens | 1 | ✓ |
| Async cached P95 | < 100ms | 0.001ms | ✓ way under threshold |

### Key insights from the stress test

1. **The DCL fast path for cached reads is essentially zero-cost** — async callers hitting a valid cached token return in 1µs. This is the hot-path advantage that 001c inherits from 001b's pure-asyncio design, without paying 001b's cross-loop landmine.

2. **Sync callers all wait for the refresh** — there's no fast-path opportunity for sync because they acquire `state_lock` directly. The P95 of ~58ms = refresh duration. This is correct: sync callers don't have async machinery to yield, so they block until the refresh thread completes.

3. **Only 1 refresh per TTL window even under 205-caller stress** — this is the headline result. The DCL pattern's atomicity guarantee scales.

4. **No deadlocks** across the 3 concurrent locking layers (state_lock, per-loop async_lock, ThreadPoolExecutor worker pool). The lock ordering (state_lock is always the innermost) prevents the classic AB-BA deadlock.

5. **`active_loops` count grew to 2** — one for the async runner's `asyncio.run` loop. (The original main script's loop doesn't exist because `asyncio.run` is called from a worker thread, which doesn't have a default loop.) This is the `_async_locks` dict leak surface for long-running apps.

## Investigation Trail

### Iteration 1 — Initial stress test had a deadlock bug

Implemented the test with a lambda hack for daemon-thread spawning:
```python
threading.Thread(target=lambda: lock.__enter__() or results.append(...) or lock.__exit__(...))
```

The `or` chain short-circuits when `__enter__` returns a truthy value, leaving the lock held and never released. The script hung indefinitely (killed at 60s+).

**Fix:** Replace lambda with a named function that uses `with lock:` properly. Pure Python hygiene issue, no bearing on the TokenStore primitive.

### Iteration 2 — Clean run with the fix

All 5 pass criteria met on first clean run. No flakiness across multiple invocations.

## Recommendations for Phase 10

The DCL pattern is **production-ready for Phase 10's TokenStore**, with these refinements still TBD in planning:

1. **Naming + location:** Recommend `packages/matriz-client/src/matriz_client/_token_store.py` (private module). Class name: `TokenStore` (no DCL/Lock suffix — the implementation detail is hidden).

2. **API surface:** `get_sync() → TokenSnapshot` and `async get_async() → TokenSnapshot`. Matches what we tested.

3. **Refresh function injection:** Constructor takes `refresh_fn: Callable[[int], str]` (sync). Async callers benefit from `asyncio.to_thread` automatically.

4. **Address `_async_locks` leak in Phase 10 plan:** Either accept (document) or use a bounded LRU (max 100 entries, oldest evicted). The leak is microscopic (≈200 bytes per entry) so accepting it is reasonable for most use cases.

5. **Refresh policy is a separate concern** — out of scope for this spike. Phase 10 plan must address: retry-on-failure, exponential backoff, fail-cache (don't re-retry for N seconds after a failure to avoid DOSing auth server).

6. **Lock convention to document in Phase 10's `_token_store.py`**: "state_lock is the source of truth; never call code that may acquire state_lock from within state_lock; refresh_fn runs under state_lock so must NOT acquire state_lock or any async lock."

## Code Reuse Notice

`store.py` is a verbatim copy of `001c-tokenstore-double-checked-locking/store.py`. **DO NOT** copy this file to `packages/matriz-client/src/`. Phase 10's plan will produce a fresh implementation tailored to matriz's conventions (uses `_ClientState`, integrates with existing `Client`/`AsyncClient` skeletons from Phase 6, exposes the API matriz callers expect). The spike's code is reference-only.
