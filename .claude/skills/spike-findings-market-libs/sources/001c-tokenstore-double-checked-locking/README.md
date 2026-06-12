---
spike: 001c
name: tokenstore-double-checked-locking
type: comparison
validates: "Given a TokenStore with threading.Lock (state) + per-loop asyncio.Lock (coord) in DCL pattern, when sync REST + async REST + daemon thread call concurrently across multiple loops, then exactly 1 refresh + no deadlocks + event loop free during refresh"
verdict: VALIDATED
related: [001a, 001b, 002]
tags: [concurrency, dcl, threading, asyncio, matriz-pattern, winner-candidate]
---

# Spike 001c: TokenStore with Double-Checked Locking

## What This Validates

**Given** un `TokenStore` con DCL: `threading.Lock` para protección de estado + un `asyncio.Lock` creado lazily por loop (keyed por `id(loop)`) para coordinación dentro de cada loop.

**When** sync REST + async REST + daemon thread llaman concurrentemente, incluyendo el caso de múltiples loops simultáneos (e.g., async caller en su loop + bridge en su propio loop).

**Then** **exactamente 1 refresh** ocurre, todos los callers reciben el mismo token, **no hay deadlocks**, y el **event loop NO se bloquea** durante el refresh.

## Research

**Approach overview:**

| Question | Answer |
|----------|--------|
| Cross-loop atomicity | `threading.Lock` (loop-agnostic) |
| Per-loop coordination | `asyncio.Lock`, created lazily, keyed by `id(loop)` |
| How sync callers acquire | `with self._state_lock:` directly |
| How async callers acquire | DCL: fast check → `async with async_lock:` → re-check → `await asyncio.to_thread(refresh_under_state_lock)` |
| Event loop blocking during refresh | NONE — refresh runs in worker thread via `asyncio.to_thread` |
| Continuity with existing matriz code | High — current matriz `client.py`/`aio.py` already uses DCL for token refresh |

**Critical design points:**

1. **`threading.Lock` is the source of truth** for atomicity. It's loop-agnostic, thread-safe, and works identically from sync, async, and daemon-thread contexts.
2. **`asyncio.Lock` is only used to prevent thundering herd WITHIN a single loop.** It is created lazily per-loop and never shared across loops (avoids the 001b landmine).
3. **The refresh function itself runs in `asyncio.to_thread`** from async callers, so the event loop is free during the (potentially slow) refresh.

**Source documentation consulted:**
- Same as 001a/001b — Python 3.12 stdlib docs for `threading.Lock`, `asyncio.Lock`, `asyncio.to_thread`.
- Inspired by matriz_client's existing pattern: `_ensure_token` in `aio.py` uses DCL with `asyncio.Lock`.

## How to Run

```bash
cd .planning/spikes/001c-tokenstore-double-checked-locking
python3 test_store.py             # standard test matrix + 3-way integration
python3 test_loop_freedom.py      # rigorous "is the loop actually free?" test
```

## What to Expect

`test_store.py`:
```
✓ sync_single_caller: 1 refresh, cached read same token
✓ async_single_caller: 1 refresh, cached read same token
✓ sync_thundering_herd: 20 threads → 1 refresh
✓ async_thundering_herd: 50 coros → 1 refresh(es) | event loop tick: max≈57ms median≈0.09ms
✓ 3way_integration: 3 contexts → 1 refresh, all got same token, async_locks_created=1
✓ multiple_loops_sequential: 2 sequential asyncio.run() → tokens match, active_locks=2
✓ concurrent_loops: 2 distinct loops → 1 refresh, both got same token, async_locks_created=2 (one per loop)
```

`test_loop_freedom.py`:
```
=== Test 1: 001c (refresh via asyncio.to_thread) ===
Refresh took ~105ms
Tickers: 115 ticks each → loop FREE during refresh ✓

=== Test 2: Strawman (refresh blocks the loop) ===
Tickers: 39 ticks each → loop BLOCKED (contrast)
```

## Investigation Trail

### Iteration 1 — Built DCL store with state_lock + per-loop async_locks

Implemented `TokenStoreDCL`:
- `_state_lock: threading.Lock` for state atomicity
- `_async_locks: dict[int, asyncio.Lock]` keyed by `id(loop)`
- `get_sync()`: just `with self._state_lock:` (no async machinery)
- `get_async()`: fast check → `async with per_loop_lock` → re-check → refresh under `state_lock`

All standard tests passed. The 3-way integration test (which BROKE 001b) **passed cleanly** — 1 refresh, 1 token across all 3 contexts.

### Iteration 2 — Initial "loop blocked 60ms!" alarm (turned out to be measurement noise)

`test_async_thundering_herd` reported `max_event_loop_block=60.43ms`. This looked like a violation of Requirement #4 ("loop no bloqueado > 5ms"). Investigated.

Initial hypothesis: the refresh runs **inside** the `state_lock`, which is a `threading.Lock`. When `get_async` does `with self._state_lock:` then calls `self._refresh_fn(...)`, the refresh blocks the event loop thread for 50ms (the simulated network delay).

### Iteration 3 — Fix: wrap refresh in asyncio.to_thread

Refactored `get_async` to call `await asyncio.to_thread(self._refresh_under_state_lock)` instead of inlining the refresh. This moves the entire state_lock acquisition + refresh to a worker thread.

Re-ran tests. `max_event_loop_block` was STILL 57ms. Same value. The fix appeared to do nothing.

### Iteration 4 — The metric was wrong, not the code

Wrote `test_loop_freedom.py`: instead of measuring monitor-tick gaps (which conflate "loop is busy" with "loop is idle"), measure whether unrelated background work makes progress during the refresh window.

Result:
- 001c (`asyncio.to_thread` refresh): unrelated tickers got **115 ticks** during the 100ms refresh + 50ms grace window. Loop is genuinely FREE.
- Strawman (inline blocking refresh): unrelated tickers got **39 ticks** in the same window. Loop is BLOCKED.

The earlier 57ms "max_block" reading was an artifact: when all the herd's coroutines are queued behind `async with async_lock:` and only the monitor is runnable, the monitor yields and the loop has nothing else to schedule. The loop SLEEPS waiting for the `to_thread` Future to complete. The monitor's tick gap measures the sleep duration, not loop blocking.

**Lesson:** measuring "blocked vs free" requires concurrent independent workload, not just self-measurement.

### Iteration 5 — Multiple concurrent loops work correctly

`test_concurrent_loops`: 2 threads, each running `asyncio.run(get_async())`. The exact scenario that BROKE 001b.

Result: ✓ 1 refresh, both threads got same token, 2 async_locks created (1 per loop). **No `RuntimeError: Task got Future attached to a different loop`.** The `threading.Lock` serves as the cross-loop atomicity guarantee; each loop creates its own asyncio.Lock without conflict.

## Results

**Verdict: VALIDATED ✓** — Strong candidate for Phase 10's TokenStore primitive.

### All 4 Requirements satisfied

1. ✓ No new dependencies (stdlib only — `threading`, `asyncio`, `dataclasses`).
2. ✓ Sync callers don't need to know about the asyncio loop (use `get_sync()` directly).
3. ✓ Exactly 1 refresh under thundering herd (validated in sync, async, 3-way, and multi-loop scenarios).
4. ✓ Event loop FREE during refresh (validated rigorously via `test_loop_freedom.py` — 115 ticks vs strawman's 39 ticks).

### Pros

- **Works in all 3 contexts with no special wrapper** — sync callers call `get_sync()`, async callers call `get_async()`. No bridge, no loop ownership questions.
- **Cross-loop safe** — `threading.Lock` is loop-agnostic, and per-loop `asyncio.Lock` instances are isolated.
- **Event loop never blocked** — refresh runs in `asyncio.to_thread`.
- **Matriz-pattern continuity** — the existing matriz `client.py`/`aio.py` uses DCL for token refresh; Phase 10's TokenStore can follow the same idiom.
- **Stdlib-only** — no dep ergonomics or version-compatibility burden.

### Cons / open issues

1. **`_async_locks` dict grows monotonically** as new loops touch the store. In long-running apps with hot-reload, test runners, or repeated `asyncio.run()` calls, this is a slow leak. **Mitigation for Phase 10:** either (a) accept the leak (each entry is a single `asyncio.Lock` ~200 bytes, negligible at scale of <1000 unique loops), or (b) use `weakref.WeakValueDictionary` keyed by the loop object itself (cleaner but tricky — `asyncio.AbstractEventLoop` may not be weak-referenceable in all CPython builds). **Decision can be deferred to Phase 10 planning.**

2. **Refresh policy (retry / backoff / fail-cache) is NOT solved.** Same as 001a — if refresh raises, the lock releases and the next caller retries. Sustained refresh failures could DOS the auth server. Out of scope for the lock primitive selection. **Flag for Phase 10.**

3. **The pattern is slightly more complex** than 001a (~80 LOC vs 001a's ~40 LOC). The extra LOC buys: per-loop thundering-herd prevention (negligible for matriz's expected workload) and the satisfying conceptual clarity that asyncio coordination stays in asyncio-land.

### Performance summary

| Approach | Hot-path async latency | Loop-free during refresh | 3-way integration | Cross-loop safe |
|----------|-----------------------|--------------------------|-------------------|-----------------|
| 001a (threading.Lock + to_thread) | ~50µs (thread hop) | ✓ | ✓ | ✓ |
| 001b (asyncio.Lock + bridge) | ~5µs (native) | ✓ | ✗ **fails** | ✗ |
| 001c (DCL) | ~5µs cached / ~50µs refresh-path | ✓ | ✓ | ✓ |

**001c offers 001b's hot-path speed for cached reads (the common case) AND 001a's cross-context safety. Best of both.**

## Impact on Remaining Spikes

- **002 (integration stress)** should use 001c. The test should validate that under 100+100+5 concurrent callers competing for an expired-token refresh, exactly 1 refresh happens and latency is acceptable.

- **Approach D (`aiologic`) is NOT needed** as a fallback. 001c is a clean stdlib solution.

- **For Phase 10 planning**, this becomes the recommended pattern. The PATTERN, not the literal code — the spike's `store.py` should NOT be copied to `packages/matriz-client/src/...`. Phase 10 plans a fresh implementation that:
  - Aligns with matriz_client's `_ClientState` convention
  - Handles the `_async_locks` leak concern (decide accept-or-fix)
  - Adds the refresh policy layer (retry/backoff/fail-cache)
  - Surfaces the right API for matriz's `Client` and `AsyncClient` (likely something like `state.token_store.get()` and `await state.token_store.get_async()`)
