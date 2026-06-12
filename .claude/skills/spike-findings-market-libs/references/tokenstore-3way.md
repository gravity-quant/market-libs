# TokenStore 3-way (sync REST + asyncio REST + ws_client daemon thread)

Implementation blueprint for a shared bearer-token store that can be safely
accessed from 3 concurrent contexts: sync REST callers, async REST callers
(possibly on user-owned event loops), and a background daemon thread (ws_client).

**Target consumer:** `packages/matriz-client/` (Phase 10 milestone v1.1).
**Pattern is also reusable** for IOL `refresh_token` in Phase 9 (BUG-03), with state-shape adjustments.

---

## Requirements (non-negotiable)

These emerged during spiking and must be honored in the real Phase 10 build:

1. **stdlib only** — no third-party concurrency primitives. `threading`, `asyncio`, `dataclasses` are the toolbox. Do NOT add `aiologic`/`aiotools`/etc. to `matriz-client`'s `pyproject.toml` (publishable wheel — minimal deps).
2. **Sync callers must NOT need to know about the asyncio loop.** `Client.get_X(...)` from the main thread, and `ws_client`'s daemon thread, both call `store.get_sync()` directly — no `asyncio.run_coroutine_threadsafe`, no loop reference passed in.
3. **Exactly 1 refresh** ante N callers concurrentes con token expirado. Atomicity guaranteed even across multiple event loops.
4. **Event loop NOT blocked > 5ms** during refresh. The refresh is sync (~50ms+ for real network calls); it must not starve the loop.
5. **No cross-loop sharing of `asyncio.Lock`.** This is a Python stdlib design constraint (see Pattern: Landmine #1).

---

## How to Build It

### Pattern: Double-Checked Locking (DCL) with two lock types

```python
import asyncio
import threading
import time
from dataclasses import dataclass
from typing import Callable

@dataclass
class TokenSnapshot:
    value: str
    refreshed_at: float
    refresh_call_id: int


class TokenStore:
    """3-way safe token store.

    - threading.Lock guards the actual state (cross-context atomicity).
    - asyncio.Lock instances are created lazily per event loop (intra-loop
      thundering-herd prevention).
    - Refresh runs in a worker thread via asyncio.to_thread to free the event
      loop during network I/O.
    """

    def __init__(self, ttl_seconds: float, refresh_fn: Callable[[int], str]) -> None:
        self._state_lock = threading.Lock()
        self._ttl = ttl_seconds
        self._refresh_fn = refresh_fn  # sync; must NOT acquire state_lock
        self._token: str | None = None
        self._refreshed_at: float = 0.0
        self._refresh_count: int = 0
        # Per-loop asyncio.Lock cache, keyed by id(loop).
        # NOTE: this grows monotonically — see "Constraints" section.
        self._async_locks: dict[int, asyncio.Lock] = {}

    def _read_state(self) -> tuple[str | None, float, int]:
        with self._state_lock:
            return self._token, self._refreshed_at, self._refresh_count

    def _refresh_under_state_lock(self) -> TokenSnapshot:
        """Helper for asyncio.to_thread — acquires state_lock + refreshes."""
        with self._state_lock:
            now = time.monotonic()
            if self._token is None or (now - self._refreshed_at) > self._ttl:
                self._refresh_count += 1
                self._token = self._refresh_fn(self._refresh_count)
                self._refreshed_at = time.monotonic()
            return TokenSnapshot(
                value=self._token,
                refreshed_at=self._refreshed_at,
                refresh_call_id=self._refresh_count,
            )

    def get_sync(self) -> TokenSnapshot:
        """Sync API — used by sync REST + ws_client daemon thread."""
        return self._refresh_under_state_lock()

    def _get_async_lock(self, loop: asyncio.AbstractEventLoop) -> asyncio.Lock:
        """Get or create the per-loop asyncio.Lock. Thread-safe initialization."""
        key = id(loop)
        lock = self._async_locks.get(key)
        if lock is not None:
            return lock
        with self._state_lock:
            lock = self._async_locks.get(key)
            if lock is None:
                lock = asyncio.Lock()
                self._async_locks[key] = lock
        return lock

    async def get_async(self) -> TokenSnapshot:
        """Async API — used by async REST callers."""
        loop = asyncio.get_running_loop()
        async_lock = self._get_async_lock(loop)

        # Fast path: token already valid? Skip the async lock entirely.
        token, refreshed_at, _ = self._read_state()
        now = time.monotonic()
        if token is not None and (now - refreshed_at) <= self._ttl:
            return TokenSnapshot(value=token, refreshed_at=refreshed_at,
                                 refresh_call_id=self._refresh_count)

        # Slow path: acquire per-loop asyncio.Lock to prevent thundering herd.
        async with async_lock:
            # Double-check under the lock — another coroutine may have refreshed.
            token, refreshed_at, _ = self._read_state()
            now = time.monotonic()
            if token is not None and (now - refreshed_at) <= self._ttl:
                return TokenSnapshot(value=token, refreshed_at=refreshed_at,
                                     refresh_call_id=self._refresh_count)

            # Refresh: offload to worker thread so the loop is NOT blocked.
            # threading.Lock inside _refresh_under_state_lock provides
            # cross-loop / cross-thread atomicity.
            return await asyncio.to_thread(self._refresh_under_state_lock)
```

### Integration with matriz `_ClientState` (Phase 6 skeleton)

The TokenStore should live inside `_ClientState`. Phase 6 already established `_ClientState` per Client instance; Phase 10 adds the store to it:

```python
# packages/matriz-client/src/matriz_client/_state.py (extending Phase 6)
from matriz_client._token_store import TokenStore

@dataclass(slots=True)
class _ClientState:
    base_url: str
    username: str | None
    password: str | None
    token: str | None
    token_expires_at: float | None
    http_client: httpx.Client | None
    # NEW in Phase 10:
    token_store: TokenStore | None  # lazy-init on first get_token() call
```

### Integration with `ws_client.py` (Phase 6 already migrated this)

Phase 6 already migrated `ws_client.py` from module-level globals to `_rest._get_default()._state.*`. Phase 10 changes this to read from `state.token_store.get_sync()`:

```python
# packages/matriz-client/src/matriz_client/ws_client.py
def _wait_token() -> str:
    state = _rest._get_default()._state
    snap = state.token_store.get_sync()
    return snap.value
```

### How to call from sync `Client.get_X(...)` methods

```python
def _get(self, path: str) -> dict:
    snap = self._state.token_store.get_sync()
    headers = {"X-Auth-Token": snap.value}
    response = self._state.http_client.get(f"{self._state.base_url}{path}", headers=headers)
    return response.json()
```

### How to call from async `AsyncClient.get_X(...)` methods

```python
async def _get(self, path: str) -> dict:
    snap = await self._state.token_store.get_async()
    headers = {"X-Auth-Token": snap.value}
    response = await self._state.http_client.get(f"{self._state.base_url}{path}", headers=headers)
    return response.json()
```

---

## What to Avoid

### Landmine #1: `asyncio.Lock` shared across loops

Invalidated in Spike 001b. The first event loop that touches an `asyncio.Lock` binds it; any other loop accessing it raises `RuntimeError: Task got Future attached to a different loop`. The DCL pattern above sidesteps this by:
- Using `threading.Lock` (loop-agnostic) for the atomicity guarantee
- Creating `asyncio.Lock` instances **lazily per loop**, never sharing

Never do this:
```python
# BROKEN in multi-loop scenarios (e.g., user-owned loop + bridge loop):
self._lock = asyncio.Lock()  # binds to first-touching loop, breaks for any other
async def get_async(self):
    async with self._lock:
        ...
```

### Landmine #2: Sync refresh inside the event loop thread

A `time.sleep(0.05)` (or any sync network call) inside `with self._state_lock:` blocks the event loop for the duration. Even if you wrap `get_async()` in `asyncio.Lock` to prevent thundering herd, the event loop is still starved during refresh.

Always wrap the sync refresh in `asyncio.to_thread`:
```python
# CORRECT — loop is free during refresh:
return await asyncio.to_thread(self._refresh_under_state_lock)

# WRONG — loop is blocked 50-500ms during refresh:
with self._state_lock:
    return self._do_refresh_if_needed()
```

### Landmine #3: Letting `refresh_fn` acquire `state_lock`

The refresh function runs inside `state_lock` (via `_refresh_under_state_lock`). If the refresh function recursively tries to acquire `state_lock`, it deadlocks. Document this contract clearly:

> `refresh_fn` must NOT call any method that acquires `state_lock`. It can only do "the network call to fetch a new token and return the string".

If the refresh needs to read other state, pass it in via closure or argument before calling.

### Landmine #4: Measuring "loop blocked" with a single monitor coroutine

The naive metric `await asyncio.sleep(0)` in a monitor coroutine measures "gap between successive scheduler ticks". If all OTHER tasks are blocked on `async with async_lock:`, the monitor sees a long tick gap — but the loop isn't actually blocked, it's just IDLE waiting for the `to_thread` Future.

Use unrelated background workload as the metric:
- Start 5 tasks that increment counters every 1ms
- Trigger the refresh
- Verify the counters advanced ~100 ticks during a 100ms refresh window

See `sources/001c-tokenstore-double-checked-locking/test_loop_freedom.py` for the canonical implementation.

### Anti-pattern: Lambda + `or` chain for thread targets

```python
# DEADLOCKS — __enter__ returns truthy, or-chain short-circuits, lock never released:
threading.Thread(target=lambda: lock.__enter__() or results.append(...) or lock.__exit__(...))
```

Use a named function with `with lock:` instead. (Discovered in Spike 002 iteration 1.)

---

## Constraints

### Performance characteristics (validated under 205-caller stress)

| Property | Measured value |
|----------|----------------|
| Refreshes per TTL window (205 callers, 100 sync + 100 async + 5 daemon) | exactly 1 |
| Sync caller latency P95 (cold) | ~57ms (refresh duration) |
| Sync caller latency P95 (warm, cached) | < 1ms |
| Async caller latency P50 (warm, cached) | ~0.001ms (1µs — fast path) |
| Async caller latency P99 (cold) | ~58ms (1 coroutine pays the refresh) |
| Errors under stress | 0 |

### Memory: `_async_locks` dict leak

The `_async_locks` dict grows monotonically as new event loops touch the store. Each entry is ~200 bytes (an `asyncio.Lock` instance).

Phase 10 planning decision required:
- **Option A (recommended)**: accept the leak, document it. For realistic matriz usage (1-10 distinct loops over a Client's lifetime), this is < 2KB total.
- **Option B**: bounded LRU (e.g., max 100 entries, oldest evicted). Adds ~20 LOC. Only needed if Client instances live across many distinct loops (test runners, hot-reload).
- **Option C**: `weakref.WeakValueDictionary` keyed by the loop object itself. CPython's `asyncio.AbstractEventLoop` IS weak-referenceable as of 3.12, so this works. Cleaner than LRU but trickier to reason about.

### Python version

Requires Python 3.9+ for `asyncio.to_thread`. The project's `pyproject.toml` already pins 3.12+ — no compatibility concern.

### Refresh policy is OUT OF SCOPE

The TokenStore primitive validated by these spikes handles **lock semantics only**. The following must be planned separately in Phase 10:

- **Retry policy** for refresh failures (don't infinite-loop)
- **Exponential backoff** between retries
- **Failure caching** (after N failed refreshes in window, return cached failure for M seconds to avoid DOSing auth server)

Recommended approach: wrap `refresh_fn` in a `RefreshPolicy` decorator that handles these concerns BEFORE the call lands in `TokenStore`. Keeps `TokenStore` itself purely focused on the lock-and-cache contract.

---

## Origin

Synthesized from spikes: 001a, 001b, 001c, 002.

| Spike | Verdict | Role in this blueprint |
|-------|---------|------------------------|
| 001a (threading.Lock + asyncio.to_thread) | VALIDATED | Baseline — simpler alternative; shows `asyncio.to_thread` works |
| 001b (asyncio.Lock + bridge) | INVALIDATED | Landmine #1 (cross-loop lock binding) — informs the "what to avoid" section |
| 001c (DCL) | VALIDATED (winner) | THE PATTERN above; combines 001a's safety with 001b's fast-path performance |
| 002 (3-way stress) | VALIDATED | Validates 001c under 205-caller load; produces the performance numbers |

Source files preserved in `sources/` for each spike. The `store.py` files in 001c and 002 are functionally identical — 002 copies 001c's winner verbatim and exercises it under load.

---

## Quick reference: what to extract from spike source files when building Phase 10

- `sources/001c-tokenstore-double-checked-locking/store.py` — the canonical TokenStore implementation. Copy the PATTERN (not the literal class) into `packages/matriz-client/src/matriz_client/_token_store.py`.
- `sources/001c-tokenstore-double-checked-locking/test_store.py` — the 7 test scenarios (single caller, thundering herd, 3-way integration, multiple loops, concurrent loops). Translate these to `packages/matriz-client/tests/test_token_store.py`.
- `sources/002-tokenstore-3way-integration-stress/test_stress.py` — the 205-caller stress test. Phase 10 verification should include a similar test (possibly trimmed to 50+50+5 for CI speed).
- `sources/001c-.../test_loop_freedom.py` — the rigorous "is the loop blocked?" measurement. Include a version in Phase 10's tests as a regression guard.
