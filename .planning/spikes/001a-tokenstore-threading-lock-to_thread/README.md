---
spike: 001a
name: tokenstore-threading-lock-to_thread
type: comparison
validates: "Given a TokenStore with threading.Lock + asyncio.to_thread for async callers, when sync REST + async REST + daemon thread call get_token() concurrently with expired token, then exactly 1 refresh happens and event loop is not blocked > 5ms"
verdict: VALIDATED
related: [001b, 001c, 002]
tags: [concurrency, threading, asyncio, tokenstore, matriz]
---

# Spike 001a: TokenStore with threading.Lock + asyncio.to_thread

## What This Validates

**Given** un `TokenStore` cuyo único lock primitivo es `threading.Lock`, y cuyos callers async usan `await asyncio.to_thread(self.get_sync)` para offloadear la operación lockeada al thread pool.

**When** sync REST (main thread), async REST (event loop), y un daemon thread (simulando `ws_client`) llaman `get_token()` concurrentemente — incluyendo el caso de N callers compitiendo durante un token expirado.

**Then** ocurre **exactamente 1 refresh** y los 3 contextos reciben el **mismo token**, sin bloquear el event loop > 5ms.

## Research

**Approach overview:**

| Question | Answer |
|----------|--------|
| Lock primitive | `threading.Lock` (stdlib) |
| How sync callers acquire | `with self._lock:` directly |
| How async callers acquire | `await asyncio.to_thread(self.get_sync)` (Python 3.9+, native stdlib) |
| Does `asyncio.to_thread` yield the event loop? | Yes — the coroutine awaits a Future bound to a worker thread; loop runs other coroutines meanwhile |
| Does `threading.Lock` block the thread that holds it? | Yes — but a thread-pool worker holding the lock does not block the main event loop thread |
| Thread pool used | `loop.run_in_executor(None, ...)` — default executor (typically 32 workers in CPython 3.12) |

**Source documentation consulted:**
- Python 3.12 stdlib: [`asyncio.to_thread`](https://docs.python.org/3/library/asyncio-task.html#asyncio.to_thread) — "Asynchronously run function func in a separate thread."
- Python 3.12 stdlib: [`threading.Lock`](https://docs.python.org/3/library/threading.html#lock-objects) — "If the lock is locked, then the calling thread blocks until the other thread releases it."
- `concurrent.futures.ThreadPoolExecutor` default size: `min(32, (os.cpu_count() or 1) + 4)` — adequate for token-refresh workload (rare bursts, not sustained).

**Chosen approach:** This single approach (no internal comparison).

## How to Run

```bash
cd .planning/spikes/001a-tokenstore-threading-lock-to_thread
python3 test_store.py
```

Requires only stdlib (Python 3.12). No deps.

## What to Expect

All 5 tests pass with these observable outcomes:

```
✓ sync_single_caller: 1 refresh, cached read returns same token
✓ async_single_caller: 1 refresh, cached read returns same token
✓ sync_thundering_herd: 20 threads → 1 refresh, all got same token
✓ async_thundering_herd: 50 coros → 1 refresh(es) | event loop tick: max=<5ms median<1ms
✓ 3way_integration: 3 contexts → 1 refresh, all got tok-1-XXXX
```

## Observability

The test file maintains an event log array (thread-safe) capturing:
- `category`: `refresh`, `sync_worker`, `daemon_worker`, `async_runner`
- `thread`: current thread name
- `ts`: ISO timestamp
- `msg`: free-text

This is not exercised explicitly in test output but is available for runtime introspection during development.

Additionally, `test_async_thundering_herd` includes an `loop_health_monitor` coroutine that measures event loop tick latency (max ms between successive `asyncio.sleep(0)` resumptions). This is the canonical measure of "is the event loop blocked".

## Investigation Trail

### Iteration 1 — Initial implementation

Wrote `TokenStoreThreadingOnly` with `threading.Lock` and an `async def get_async()` that delegates to `asyncio.to_thread(self.get_sync)`. The refresh function (`_refresh_fn`) is called **inside** the lock — this is the simplest possible design.

### Iteration 2 — Thundering herd

Tested 20 concurrent threads calling `get_sync()` with no cached token. Result: exactly 1 refresh, all 20 threads got the same token. The first thread to acquire the lock does the refresh; the next 19 see `_token != None` and `now - _refreshed_at < ttl`, so they hit the cache path inside the lock.

### Iteration 3 — Async thundering herd

Tested 50 concurrent coroutines calling `get_async()`. Critical: measured event loop tick latency with a monitor coroutine running concurrently.

**Result:** `max_event_loop_block = 2.27ms`, well below the 5ms target. Why so low?
- The 50 coroutines all spawn `to_thread` calls almost simultaneously
- Workers serialize on the lock; first acquires + refreshes (50ms simulated)
- Workers 2-50 acquire the lock briefly (microseconds — cache hit)
- The event loop is NEVER blocked by the refresh — the main thread is free to schedule the monitor coroutine

This validates the central claim: **`asyncio.to_thread` decouples the lock-held duration from the event loop**.

### Iteration 4 — 3-way integration

Spawned 3 worker threads simultaneously: sync REST caller, async REST runner (own event loop), and daemon thread. Used a `threading.Barrier(3)` to release all at once. Result: 1 refresh, all 3 contexts got the same token.

### Edge case considered but not implemented as a test

**Refresh failure semantics:** If `_refresh_fn` raises, `self._token` is NOT updated (raised before assignment). The lock is released. Next caller retries refresh. This means:
- If `_token` was previously valid (just expired): we keep retrying. ✓ correct.
- If `_token` was `None`: we keep retrying. **Could DOS the auth server under sustained failures.** This is a refinement concern (retry policy, backoff, cached failure) that is **orthogonal to the lock primitive choice**. Flagged for Phase 10 planning.

## Results

**Verdict: VALIDATED ✓**

Approach 001a satisfies all 4 explicit Requirements from MANIFEST.md:
1. ✓ No new dependencies (stdlib only)
2. ✓ Sync callers don't need to know about the asyncio loop
3. ✓ Exactly 1 refresh under thundering herd (validated in 3 test scenarios)
4. ✓ Event loop not blocked > 5ms (measured: 2.27ms max under 50 concurrent async callers)

### Pros

- **Simplest possible implementation** (~40 LOC for the store).
- Stdlib-only.
- Sync callers (REST + ws_client daemon thread) acquire the lock directly — no async machinery to learn.
- `asyncio.to_thread` works out of the box; no need to manage an event loop for sync callers.
- Refresh semantics are clean: caller-blocking, atomic per caller.

### Cons

- **Every async call is a thread-hop.** For cached-token reads (the hot path), this is ~10-50µs of extra latency vs. a pure-asyncio approach (001b). For matriz's workload (token refresh ~once/23h, cached reads for thousands of API calls between refreshes), this overhead matters.
- Thread pool exhaustion is theoretically possible if many async callers attempt `get_async()` simultaneously and the pool is also being used by other code. Default pool size is 32 — for our workload (one TokenStore per `matriz_client` Client/AsyncClient instance), unlikely to be a real risk.
- Refresh fn runs **inside** the lock — long refreshes block all callers. Mitigation: don't do anything heavy in the refresh fn beyond the network call.

### Hot-path benchmark (cached read)

Not measured in detail (would require pytest-benchmark or timeit comparison with 001b/001c). Reasoned estimate from `asyncio.to_thread` source:
- 1 future allocation
- 1 thread pool submit
- 1 context switch (yield) + thread wake
- 1 lock acquire/release (uncontended → fast path)
- Total: ~20-100µs per cached-token read in `get_async`

Compared to expected pure-asyncio overhead (001b): ~1-5µs. **~20× slower on the hot path**, but absolute number is small enough to be acceptable for matriz's expected throughput.

## Impact on Remaining Spikes

- **001b** must demonstrate enough hot-path advantage to justify its added complexity (event loop awareness from sync callers).
- **001c** must demonstrate either better hot-path perf OR cleaner semantics OR matriz-pattern continuity (the existing matriz `client.py` async lock uses DCL).
- **002** (integration stress test) should use this approach as the baseline — if 001a passes a 100+100+5 stress test, it's the leading candidate.
