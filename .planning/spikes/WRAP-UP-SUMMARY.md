# Spike Wrap-Up Summary

**Wrap-up sessions:**
- 2026-06-12 (initial): processed Spikes 001a, 001b, 001c, 002
- 2026-06-12 (append): processed Spike 003

**Spikes processed:** 5 total
**Feature areas:** 2 (TokenStore 3-way lock primitive · Refresh policy)
**Skill output:** `./.claude/skills/spike-findings-market-libs/` (SKILL.md + 2 references + 5 sources)

## Processed Spikes

| # | Name | Type | Verdict | Feature Area |
|---|------|------|---------|--------------|
| 001a | tokenstore-threading-lock-to_thread | comparison | ✓ VALIDATED | TokenStore 3-way (alt baseline) |
| 001b | tokenstore-asyncio-lock-run_threadsafe | comparison | ✗ INVALIDATED | TokenStore 3-way (landmine) |
| 001c | tokenstore-double-checked-locking | comparison | ✓ **WINNER (lock)** | TokenStore 3-way |
| 002 | tokenstore-3way-integration-stress | standard | ✓ VALIDATED | TokenStore 3-way (stress validation) |
| 003 | tokenstore-refresh-policy | standard | ✓ **WINNER (retry)** | Refresh policy |

## Key Findings

### 1. Lock primitive resolved for Phase 10 (Spikes 001a/b/c/002)

The TokenStore for matriz-client's 3-way concurrency model (sync REST + async REST + `ws_client` daemon thread) is built on a **Double-Checked Locking pattern**:

- `threading.Lock` as the cross-context atomicity source-of-truth (loop-agnostic, thread-safe)
- Per-loop `asyncio.Lock` instances created lazily (keyed by `id(loop)`) for intra-loop thundering-herd prevention
- Refresh function wrapped in `asyncio.to_thread` from async callers so the event loop stays free during network I/O

This combines:
- 001a's safety (works across loops and contexts)
- 001b's hot-path speed (cached reads ~5µs for async callers)
- Matriz-pattern continuity (the existing token refresh in matriz `aio.py` already uses DCL)

### 2. Refresh policy resolved for Phase 10 (Spike 003)

A `RefreshPolicy` decorator wraps `refresh_fn` and provides:

- **Transient/Permanent/RateLimited classification** via exception subclasses
- **Exponential backoff with jitter** (cap configurable)
- **Respect for `Retry-After` headers** on 429 responses
- **Fail-cache** after exhausted retries → prevents thundering-herd from DOSing the auth server

**Headline result**: 10 concurrent sync callers post-failure → **0 new auth server hits** (all served from fail-cache).

The policy is a separate concern from the TokenStore — they compose cleanly:
```python
store = TokenStore(ttl=23*3600, refresh_fn=RefreshPolicy(...).wrap(adapter))
```

### 3. Critical landmines documented

- **`asyncio.Lock` instances bind to the first event loop that touches them.** Any other loop accessing the same instance raises `RuntimeError: Task got Future attached to a different loop`. This means pure-asyncio approaches CANNOT work for the matriz 3-way scenario where AsyncClient users own their own loops. (Spike 001b)
- **Permanent errors must NOT fail-cache.** Caching them blocks recovery via `configure(username=..., password=...)` for the full `fail_cache_s` window — actively harmful. The policy short-circuits permanent errors without caching. (Spike 003)

### 4. Measurement methodology lesson

The naive metric "max event loop tick gap" conflates "loop is busy" with "loop is idle waiting on a Future". The correct measurement is: does **unrelated background work** progress during the operation?

- 001c with `asyncio.to_thread`: 115 ticks of background work during 100ms refresh = loop FREE
- Strawman (refresh blocks loop): 39 ticks in same window = loop BLOCKED

Documented in `sources/001c-tokenstore-double-checked-locking/test_loop_freedom.py` as the canonical pattern for future loop-blocking tests.

### 5. Performance validated at scale

Spike 002 stress test (205 concurrent callers across 2 phases):
- Total refreshes: 2 (one per TTL window — minimum possible)
- Errors: 0
- Phase 1 atomicity: 1 unique token across 205 callers
- Async cached-read P50: 0.001ms
- Sync cold-read P95: 57ms (= refresh duration; sync has no fast path)

Spike 003 fail-cache integration with TokenStore (10 concurrent sync callers post-failure):
- New auth server hits: 0 (all served from fail-cache)
- Cached error propagated to all 10 callers correctly

### 6. Out-of-scope items flagged for Phase 10 planning

- **`_async_locks` dict grows monotonically** — small leak (~200 bytes per loop). Phase 10 plan must decide: accept and document, bounded LRU, or `WeakValueDictionary` keyed by loop object.
- **Adapter location** — `_refresh.py` or inside `_token_store.py`?
- **Policy params via `configure()`** — should users override `max_retries` / `fail_cache_s`?
- **Recommended integration**: `TokenStore` lives inside `_ClientState` (Phase 6 skeleton) per-instance. `Client.get_X()` calls `state.token_store.get_sync()`; `AsyncClient.get_X()` calls `await state.token_store.get_async()`. `ws_client.py` already migrated to `_rest._get_default()._state.*` in Phase 6 — just changes the read path.
- **Sync caller behavior during retry sleeps**: holds `state_lock` for the full retry sequence. Worst case ~7s for `max_retries=3, base_backoff_s=1.0`. Acceptable for matriz frequency but document.

### 7. STATE.md research flag closed

> `[Phase 10]: TokenStore 3-way design is the highest-uncertainty item of v1.1; research flag triggered — spike must happen before /gsd-plan-phase 10.`

**Status: RESOLVED.** Both the lock primitive and the refresh policy are validated end-to-end. `/gsd-plan-phase 10` can proceed without architectural blockers. The skill auto-loads when planning runs and informs the planner's RESEARCH and PLAN outputs.

## Next Steps

1. **Run `/gsd-discuss-phase 7`** to plan Phase 7 (`_core.py` extraction) — this is the next phase in milestone v1.1 dependency order.
2. When Phase 7-9 are done and you arrive at Phase 10, the spike-findings skill auto-loads. The planner picks up the patterns AND constraints automatically.
3. Optional: run `/gsd-spike` (frontier mode) to propose additional spikes — 004 real httpx, 005 token expiry semantics, 006 cancellation during refresh, 007 weakref leak fix are all available candidates.
