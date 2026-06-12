---
spike: 001b
name: tokenstore-asyncio-lock-run_threadsafe
type: comparison
validates: "Given a TokenStore with asyncio.Lock + persistent loop, when sync REST + async REST + daemon thread call concurrently, then exactly 1 refresh happens without sync callers needing to know about the loop"
verdict: INVALIDATED
related: [001a, 001c, 002]
tags: [concurrency, asyncio, event-loop, loop-binding, landmine]
---

# Spike 001b: TokenStore with asyncio.Lock + run_coroutine_threadsafe

## What This Validates

**Given** un `TokenStore` cuyo lock primitivo es `asyncio.Lock`, y un wrapper `LoopAwareSyncBridge` que corre un loop dedicado en background thread y enruta sync callers vía `asyncio.run_coroutine_threadsafe(...)`.

**When** sync REST + async REST + daemon thread llaman concurrentemente.

**Then** *(esperado)* exactamente 1 refresh y todos los callers reciben el mismo token, sin que los sync callers necesiten conocer el loop directamente.

## Research

**Approach overview:**

| Question | Answer |
|----------|--------|
| Lock primitive | `asyncio.Lock` (stdlib, loop-bound) |
| How async callers acquire | `async with self._lock:` natively, no thread hop |
| How sync callers acquire | `asyncio.run_coroutine_threadsafe(coro, loop).result()` via bridge |
| Loop lifecycle | Bridge owns a long-lived loop in a daemon thread, started/stopped externally |
| Hot path latency (async) | Native asyncio — no thread hop, minimal overhead |
| Hot path latency (sync) | Thread → loop → wakeup → coroutine execution → result. Worse than 001a's `to_thread`. |

**Source documentation consulted:**
- Python 3.12 stdlib: [`asyncio.Lock`](https://docs.python.org/3/library/asyncio-sync.html#asyncio.Lock) — "the loop with which this object is associated will be the loop that creates the lock" (the binding rule)
- Python 3.12 stdlib: [`asyncio.run_coroutine_threadsafe`](https://docs.python.org/3/library/asyncio-task.html#asyncio.run_coroutine_threadsafe) — "Submit a coroutine to the given event loop. Thread-safe."

**Chosen approach:** Single design tested.

## How to Run

```bash
cd .planning/spikes/001b-tokenstore-asyncio-lock-run_threadsafe
python3 test_store.py             # primary test suite (will fail on 3-way integration)
python3 test_followup_loop_binding.py   # follow-up: characterize the failure mode
```

## What to Expect

```
✓ async_single_caller: 1 refresh, cached read returns same token
✓ async_thundering_herd: 50 coros → 1 refresh(es) | event loop tick: max≈0.12ms (19× faster than 001a)
✓ sync_via_bridge_single: 1 refresh via background loop
✓ sync_via_bridge_thundering_herd: 20 sync threads through bridge → 1 refresh
✗ 3way_integration: RuntimeError "Future attached to a different loop"
```

The first 4 tests pass beautifully. The 3-way integration test **fails fundamentally**.

## Investigation Trail

### Iteration 1 — Build store + bridge

Wrote `TokenStoreAsyncioOnly` with `asyncio.Lock` created lazily on first `get_async()` call. Built `LoopAwareSyncBridge` that spawns a dedicated daemon thread running `asyncio.new_event_loop()` + `loop.run_forever()`. Sync callers go through the bridge: `asyncio.run_coroutine_threadsafe(store.get_async(), bridge_loop).result()`.

### Iteration 2 — Single-context tests all pass

- `test_async_single_caller`: 1 refresh, cached read same token. ✓
- `test_async_thundering_herd`: 50 coros on 1 loop → 1 refresh, **max event loop block = 0.12ms** (vs 001a's 2.27ms — ~19× faster on the hot path, as expected, because there's no thread hop).
- `test_sync_via_bridge_single`: 1 refresh via background loop. ✓
- `test_sync_via_bridge_thundering_herd`: 20 sync threads through bridge → 1 refresh. ✓

**This was the moment I thought 001b might win** — pure-asyncio is genuinely faster on the hot path.

### Iteration 3 — 3-way integration test BLEW UP

```
RuntimeError: Task <Task pending ...> got Future <Future pending> attached to a different loop
```

The async runner creates its own loop (via `asyncio.run(main())`). The bridge has its OWN loop in its background thread. Both try to use the SAME `asyncio.Lock` instance — but `asyncio.Lock` binds to the first loop that touches it. The second loop fails.

### Iteration 4 — Follow-up: characterize the failure (test_followup_loop_binding.py)

**case_two_loops_break:** 2 threads each with their own `asyncio.run()` calling the same store. Result: one thread succeeds (whichever ran first), the other raises `RuntimeError: ... attached to a different loop`. **Confirms the binding rule.**

**case_single_loop_works:** 20 coroutines on 1 single loop. Result: 1 refresh, all coros get same token. **asyncio.Lock works fine when there's only one loop.**

**case_real_world_matriz_pattern:** Sequential `asyncio.run()` calls (loop A closes, loop B opens). Result: BOTH calls succeed, returning the cached token. This is misleading — it works because:
1. First run populates `_token`.
2. Second run hits the cache path inside `with self._lock:` — and `asyncio.Lock` has an "uncontended fast path" that may or may not enforce loop binding (depending on Python version + waiter queue state).
3. If a refresh had to happen on the second run with the lock bound to a now-closed loop, it would likely fail.

This is a **fragile workaround at best**, and absolutely not safe under contention.

### Conclusion of the investigation trail

`asyncio.Lock` is **fundamentally not cross-loop safe** for any scenario with concurrent loops. Sequential loops can sometimes work in cache-hit paths but cannot be relied on.

## Results

**Verdict: INVALIDATED ✗** (for the matriz 3-way use case)

### Why this is INVALIDATED, not PARTIAL

The Requirement from MANIFEST.md is explicit: the TokenStore must safely serve **3 concurrent contexts**, one of which is a user-owned event loop (matriz's `AsyncClient` exposes a real async API to user code). User code controls that loop.

Mitigations considered and rejected:

| Mitigation | Why it fails |
|------------|--------------|
| Force all callers through the bridge's loop | Defeats the purpose of exposing a real `async def` API to user code — AsyncClient becomes a fake-async facade over a background thread's loop, with all the latency of 001a but worse complexity |
| Detect current loop at `get_async` time and create per-loop lock | Defeats atomicity — each loop has its own lock, multiple refreshes can happen concurrently |
| Document the constraint "share your loop with us" | Hostile to user code; doesn't scale to multi-loop apps; failure mode is a confusing RuntimeError, not a clear error |

### Pros (despite invalidation)

- **Hot-path latency for async callers is excellent** — ~19× faster event-loop responsiveness than 001a in the single-loop case.
- Native asyncio semantics — looks idiomatic to async Python developers.
- No thread pool dependency.

### Cons

- **`asyncio.Lock` cannot be safely shared across loops.** This is a Python stdlib design constraint, not a fix-with-effort.
- **Bridge complexity:** sync callers need a start/stop lifecycle for the bridge. ws_client daemon thread would need to know when the bridge is running. The matriz_client.Client constructor would have to manage this — adding API surface.
- **Multi-loop scenarios (user-owned loop + bridge's loop) are concretely broken** — not theoretically, demonstrated with `RuntimeError`.

## Impact on Remaining Spikes

- **001c (double-checked-locking with both lock types)** now becomes the leading candidate. The key question for 001c: can the `asyncio.Lock` be **lazily created per-loop** while the `threading.Lock` provides the cross-loop atomicity guarantee? This is exactly the pattern matriz's existing async code uses for token refresh — strong continuity argument.

- **002 (integration stress)** must NOT use 001b. Run with 001c (or fall back to 001a).

- **Frontier consideration:** approach D (`aiologic` library) gains weight — it's specifically designed for this exact problem. If 001c also has unacceptable trade-offs, reconsider D.

## Forward Lessons for Phase 10

1. **`asyncio.Lock` is loop-local** — never share an `asyncio.Lock` instance across loops, even if "no contention is expected".
2. **The token store must use a primitive that's loop-agnostic** — `threading.Lock` is the canonical choice for shared mutable state across mixed sync/async/threaded code.
3. **Any async wrapper that needs to coordinate with the store should create its `asyncio.Lock` lazily and per-loop**, treating it as event-loop-scoped coordination only (e.g., to prevent thundering herd within ONE loop).
