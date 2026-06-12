# Spike Wrap-Up Summary

**Date:** 2026-06-12
**Spikes processed:** 4
**Feature areas:** TokenStore 3-way (sync REST + asyncio REST + ws_client daemon thread)
**Skill output:** `./.claude/skills/spike-findings-market-libs/`

## Processed Spikes

| # | Name | Type | Verdict | Feature Area |
|---|------|------|---------|--------------|
| 001a | tokenstore-threading-lock-to_thread | comparison | ✓ VALIDATED | TokenStore 3-way |
| 001b | tokenstore-asyncio-lock-run_threadsafe | comparison | ✗ INVALIDATED (landmine) | TokenStore 3-way |
| 001c | tokenstore-double-checked-locking | comparison | ✓ **WINNER** | TokenStore 3-way |
| 002 | tokenstore-3way-integration-stress | standard | ✓ VALIDATED | TokenStore 3-way |

## Key Findings

### 1. Lock primitive resolved for Phase 10

The TokenStore for matriz-client's 3-way concurrency model (sync REST + async REST + `ws_client` daemon thread) is built on a **Double-Checked Locking pattern**:

- `threading.Lock` as the cross-context atomicity source-of-truth (loop-agnostic, thread-safe)
- Per-loop `asyncio.Lock` instances created lazily (keyed by `id(loop)`) for intra-loop thundering-herd prevention
- Refresh function wrapped in `asyncio.to_thread` from async callers so the event loop stays free during network I/O

This combines:
- 001a's safety (works across loops and contexts)
- 001b's hot-path speed (cached reads ~5µs for async callers)
- Matriz-pattern continuity (the existing token refresh in matriz `aio.py` already uses DCL)

### 2. Critical landmine documented

`asyncio.Lock` instances **bind to the first event loop that touches them**. Any other loop accessing the same instance raises `RuntimeError: Task got Future attached to a different loop`. This means pure-asyncio approaches CANNOT work for the matriz 3-way scenario where AsyncClient users own their own loops.

This is a Python stdlib design constraint, not fixable with effort. Documented in `.claude/skills/spike-findings-market-libs/references/tokenstore-3way.md` under "Landmine #1".

### 3. Measurement methodology lesson

The naive metric "max event loop tick gap" conflates "loop is busy" with "loop is idle waiting on a Future". The correct measurement is: does **unrelated background work** progress during the operation?

- 001c with `asyncio.to_thread`: 115 ticks of background work during 100ms refresh = loop FREE
- Strawman (refresh blocks loop): 39 ticks in same window = loop BLOCKED

Documented in `sources/001c-tokenstore-double-checked-locking/test_loop_freedom.py` as the canonical pattern for future loop-blocking tests.

### 4. Performance validated at scale

Spike 002 stress test results (205 concurrent callers across 2 phases):
- Total refreshes: 2 (one per TTL window — minimum possible)
- Errors: 0
- Phase 1 atomicity: 1 unique token across 205 callers
- Async cached-read P50: 0.001ms
- Sync cold-read P95: 57ms (= refresh duration; sync has no fast path)

### 5. Out-of-scope items flagged for Phase 10 planning

- **`_async_locks` dict grows monotonically** — small leak (~200 bytes per loop). Phase 10 plan must decide: accept and document, bounded LRU, or `WeakValueDictionary` keyed by loop object.
- **Refresh policy** (retry / backoff / fail-cache) is a separate concern. Recommendation: wrap `refresh_fn` in a `RefreshPolicy` decorator before it lands in `TokenStore`.
- **Recommended integration**: `TokenStore` lives inside `_ClientState` (Phase 6 skeleton) per-instance. `Client.get_X()` calls `state.token_store.get_sync()`; `AsyncClient.get_X()` calls `await state.token_store.get_async()`. `ws_client.py` already migrated to `_rest._get_default()._state.*` in Phase 6 — just changes the read path.

### 6. STATE.md research flag closed

> `[Phase 10]: TokenStore 3-way design is the highest-uncertainty item of v1.1; research flag triggered — spike must happen before /gsd-plan-phase 10.`

**Status: RESOLVED.** `/gsd-plan-phase 10` can now proceed without architectural blockers. The skill will auto-load when planning runs and inform the planner's RESEARCH and PLAN outputs.

## Next Steps

1. Run `/gsd-discuss-phase 7` to plan Phase 7 (`_core.py` extraction) — this is the next phase in milestone v1.1 dependency order.
2. When Phase 7-9 are done and you arrive at Phase 10, the spike-findings skill auto-loads and the planner picks up the patterns and constraints automatically.
3. Optional: run `/gsd-spike` (frontier mode) to propose additional spikes — refresh policy is a natural next candidate.
