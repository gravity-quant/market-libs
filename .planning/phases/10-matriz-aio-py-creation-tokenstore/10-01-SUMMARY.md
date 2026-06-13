---
phase: 10-matriz-aio-py-creation-tokenstore
plan: 01
subsystem: matriz-client
tags: [refac-04, tokenstore, refresh-policy, concurrency, spike-port]
requires:
  - matriz-client._state._ClientState (read-only — Plan 10-03 will extend)
  - httpx.Client (passed in via state.http_client by build_token_store)
provides:
  - matriz_client._token_store.TokenStore (3-way concurrent token primitive)
  - matriz_client._token_store.TokenSnapshot (immutable read result)
  - matriz_client._token_store.build_token_store (factory composing adapter + policy)
  - matriz_client._refresh_policy.RefreshPolicy (retry/backoff/fail-cache decorator)
  - matriz_client._refresh.MatrizRefresh (httpx → token adapter)
  - matriz_client._refresh_errors.{RefreshError, PermanentRefreshError, TransientRefreshError, RateLimitedRefreshError}
affects: []  # Plan 10-01 is additive only — no consumer wiring yet.
tech-stack:
  added: []  # No new deps. random/threading/time/asyncio/dataclasses/collections.abc are stdlib; httpx + pytest_httpx already in matriz-client deps.
  patterns:
    - "Double-Checked Locking (threading.Lock + per-loop asyncio.Lock + asyncio.to_thread offload)"
    - "Retry policy with exception-class classification (Permanent / Transient / RateLimited)"
    - "Fail-cache DOS prevention (cached exception short-circuit)"
    - "Pluggable adapter contract: Callable[[int], str]"
    - "Frozen-slots dataclass for immutable snapshots"
    - "Lazy factory composition (build_token_store)"
key-files:
  created:
    - packages/matriz-client/src/matriz_client/_refresh_errors.py  # 39 LOC
    - packages/matriz-client/src/matriz_client/_refresh.py  # 88 LOC
    - packages/matriz-client/src/matriz_client/_refresh_policy.py  # 125 LOC
    - packages/matriz-client/src/matriz_client/_token_store.py  # 176 LOC
    - packages/matriz-client/tests/test_refresh_errors.py  # 61 LOC, 6 tests
    - packages/matriz-client/tests/test_refresh_policy.py  # 409 LOC, 20 tests
    - packages/matriz-client/tests/test_token_store.py  # 387 LOC, 13 tests
  modified:
    - .planning/codebase/CONCERNS.md  # +D-05 _async_locks process-lifetime leak tradeoff
decisions:
  - "D-01 honored: 4 new src files (errors / refresh / policy / store) — max cohesion, ruff-clean import-linter contracts"
  - "D-02 honored: TokenStore lives in _token_store.py, not _state.py"
  - "D-03 honored: only max_retries is exposed in build_token_store; base_backoff_s=1.0, max_backoff_s=30.0, jitter=0.25, fail_cache_s=30.0 hardcoded per spike defaults"
  - "D-04 honored: ttl_seconds=23*3600 hardcoded via _MATRIZ_TOKEN_TTL_SECONDS constant"
  - "D-05 honored: _async_locks process-lifetime leak documented in CONCERNS.md (v1.2 backlog if memory growth observed)"
  - "D-08 honored: 1 atomic commit (3cd0a80) for the full plan"
metrics:
  duration: ~70min (planning → implementation → CI green → SUMMARY)
  completed: 2026-06-13
  tests_added: 39
  tests_target: 20  # D-07 line 1008 baseline target
  test_overshoot_ratio: 1.95x
  loc_src_added: 428  # sum of 4 src files (39 + 88 + 125 + 176)
  loc_test_added: 857  # sum of 3 test files (61 + 409 + 387)
  commits: 1  # 3cd0a80
---

# Phase 10 Plan 01: TokenStore + RefreshPolicy Primitive Summary

**One-liner:** 4 standalone source modules (`_token_store`, `_refresh_policy`, `_refresh`, `_refresh_errors`) implementing the Spike 001c + 003 Double-Checked Locking token primitive plus retry/backoff/fail-cache policy plus pluggable httpx adapter — fully testable in isolation with 3-way concurrency stress (50 sync + 50 async + 5 daemon threads → exactly 1 refresh, 0 errors), with **NO** consumer wiring (`client.py` / `aio.py` / `ws_client.py` / `_state.py` untouched — that lands in Plan 10-03).

## What Was Built

### 1. `_refresh_errors.py` (39 LOC) — Exception Hierarchy

4-class hierarchy ported verbatim from Spike 003 `errors.py`:

```
RefreshError (Exception)
├── PermanentRefreshError    — 401, 400, 403 (no retry, no cache)
└── TransientRefreshError    — 5xx, network timeout (retry with backoff)
    └── RateLimitedRefreshError(retry_after_seconds: float) — 429 (honor Retry-After)
```

Intentionally does **NOT** inherit from `MatrizClientError` — this is an
internal classification used only by the refresh path. The wider package
surfaces `AuthenticationError` / `PrimaryAPIError` to callers (unwrap will
happen at the wiring site in Plan 10-03).

### 2. `_refresh.py` (88 LOC) — `MatrizRefresh` Adapter

`Callable[[int], str]` contract that:

1. Issues `POST {base_url}/auth/getToken` with `X-Username` / `X-Password`
   credential headers (matches the canonical builder in
   `_core.build_login_request`, Phase 6 D-04).
2. Maps httpx exceptions and HTTP status codes to the refresh-policy hierarchy:
   - `httpx.TimeoutException` / `httpx.NetworkError` → `TransientRefreshError`
   - 400 / 401 / 403 → `PermanentRefreshError`
   - 429 → `RateLimitedRefreshError(retry_after_seconds=...)`
   - 5xx → `TransientRefreshError` (status code only — **T-10-01-04** mitigation)
   - 2xx without `X-Auth-Token` → `TransientRefreshError`
3. Returns the bearer token from the `X-Auth-Token` response header.

**Security:** Per T-10-01-04 mitigation (ASVS V8.3.4), error messages embed
only the status code, never the response body — preventing credential echo
via auth-server reflection bugs. Verified by acceptance grep
`grep "response.text" _refresh.py | wc -l == 0`.

### 3. `_refresh_policy.py` (125 LOC) — `RefreshPolicy` Decorator

Ported from Spike 003 `policy.py`. Wraps a `refresh_fn(call_id: int) -> str`
with:

| Exception type            | Behavior                                                  |
|---------------------------|-----------------------------------------------------------|
| `PermanentRefreshError`   | Propagate immediately. NO retry. NO fail-cache.           |
| `TransientRefreshError`   | Retry with exp backoff `base * 2^attempt` + jitter.       |
| `RateLimitedRefreshError` | Retry honoring `retry_after_seconds` (capped at max).     |
| Exhausted budget          | Cache exception for `fail_cache_s` (DOS prevention).      |

Internal `threading.Lock` makes the wrapped callable safe to call from sync
threads, the WS daemon thread, and from inside `asyncio.to_thread` offloads.
`sleep_fn` is injectable so tests run with zero wall-clock delay.

### 4. `_token_store.py` (176 LOC) — `TokenStore` + `TokenSnapshot` + `build_token_store`

The **3-way concurrent token primitive** ported from Spike 001c:

- **`threading.Lock`** (`_state_lock`) — guards token state cross-context:
  sync REST, ws_client daemon thread, and `asyncio.to_thread` offload all
  converge under the same lock for true atomicity.
- **Per-loop `asyncio.Lock`** (`_async_locks: dict[int, asyncio.Lock]`,
  keyed by `id(loop)`) — prevents thundering herd within a single event loop.
- **`asyncio.to_thread`** — refresh runs in a worker thread; the event loop
  is NOT blocked during the (potentially slow) network call.

**Public API:**

```python
class TokenStore:
    def __init__(self, *, ttl_seconds: int, refresh_fn: Callable[[int], str]) -> None: ...
    def get_sync(self) -> TokenSnapshot:        # sync REST, ws daemon
    async def get_async(self) -> TokenSnapshot:  # async REST surface
    def invalidate(self) -> None:                # Plan 10-03 401 re-auth-once consumer

@dataclass(frozen=True, slots=True)
class TokenSnapshot:
    value: str
    refreshed_at: float
    refresh_call_id: int

def build_token_store(state: _ClientState, *, max_retries: int) -> TokenStore:
    """Composes MatrizRefresh + RefreshPolicy into a wired TokenStore.
    Hardcodes ttl_seconds=23*3600 (D-04) and the 4 non-max_retries knobs
    (D-03 — spike-validated defaults)."""
```

## How It Was Verified

| Check                         | Result                                                |
|-------------------------------|-------------------------------------------------------|
| `pytest` (Plan 10-01 files)   | **39 passed** in 0.38s (target ≥ 20)                  |
| `pytest` (matriz-client full) | **253 passed, 1 skipped** in 17.83s (1 skip is forward-ref to Phase 10 Plan 10-02/03 — expected) |
| `pytest` (workspace full)     | **821 passed, 3 skipped, 1 deselected** in 154.70s (3 skips are forward-refs to Plan 10-02/03 — expected) |
| `mypy --strict`               | clean (4 src files)                                   |
| `ruff check`                  | clean (4 src + 3 test files)                          |
| `ruff format --check`         | clean                                                 |
| `lint-imports` (import-linter)| **4 contracts kept, 0 broken**                        |
| `lint-logging` grep           | 0 forbidden `logging.basicConfig` / `logging.root`    |
| Isolation grep                | 0 imports of new modules from `client.py` / `aio.py` / `ws_client.py` / `_state.py` (Plan 10-01 is additive only) |

### Specific stress assertions landed

- **U3** sync thundering herd: 10 sync threads, 50ms refresh delay → exactly 1 refresh.
- **U4** async thundering herd: 10 coroutines in one loop → exactly 1 refresh.
- **U5** multi-loop reuse: 2 sequential `asyncio.run` invocations → same token, 1 refresh.
- **U6** event-loop budget: 100ms blocking refresh → max loop gap < 50ms (well under 100ms; spike measured < 5ms).
- **S1** 3-way concurrent stress: **50 sync + 50 async + 5 daemon = 105 callers → exactly 1 refresh, 0 errors, all 105 receive `"TOKEN-1"`**.
- **S2** P95 cached read latency: 100 cached reads → P95 < 5ms (spike measured < 0.01ms).
- **P5** fail-cache DOS prevention: 10 callers post-exhaustion → 0 new `refresh_fn` invocations.
- **P6** permanent escape hatch: `PermanentRefreshError` does **NOT** enter fail-cache.

## Decisions Honored

| Decision | What it meant                                                           | Where landed                                                                                       |
|----------|-------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------|
| **D-01** | 4 new src files (errors / refresh / policy / store)                     | `_refresh_errors.py` + `_refresh.py` + `_refresh_policy.py` + `_token_store.py`                    |
| **D-02** | TokenStore lives in `_token_store.py`, NOT `_state.py`                  | `packages/matriz-client/src/matriz_client/_token_store.py` (176 LOC). `_state.py` untouched.       |
| **D-03** | Only `max_retries` exposed in `build_token_store`; other knobs hardcoded | `build_token_store(state, *, max_retries)` — base_backoff=1.0, max_backoff=30.0, jitter=0.25, fail_cache=30.0 hardcoded inside |
| **D-04** | `ttl_seconds = 23 * 3600` hardcoded                                     | `_MATRIZ_TOKEN_TTL_SECONDS: int = 23 * 3600` constant at module top                                |
| **D-05** | Accept-and-document `_async_locks` process-lifetime leak                | New section in `.planning/codebase/CONCERNS.md` "Documented Tradeoffs"                              |
| **D-08** | 1 commit atómico per plan                                               | Commit `3cd0a80` — 8 files changed, 1312 insertions(+), 1 deletion(-)                              |

## Out of Scope (Plan 10-02 / 10-03)

Per plan objective and verification line `grep -r "from matriz_client._token_store|from matriz_client._refresh" client.py aio.py ws_client.py _state.py returns 0 matches`:

- `client.py` `_ensure_token()` migration → **Plan 10-03**
- `aio.py` full REST surface + `_aensure_token()` wiring → **Plan 10-02** + **Plan 10-03**
- `ws_client.py` `_ensure_token()` → `state.token_store.get_sync()` swap → **Plan 10-03**
- `_state.py` `+1 token_store: TokenStore | None = None` field → **Plan 10-03**

## Threat Model — Mitigations Landed

| Threat ID    | Mitigation                                                                                                   |
|--------------|--------------------------------------------------------------------------------------------------------------|
| T-10-01-01   | `_refresh.py` 5xx exception message uses `f"server error {status}"` only — never `response.text`. **Verified** by `grep "response.text" _refresh.py | wc -l == 0`. |
| T-10-01-02   | Cached exceptions in `RefreshPolicy` inherit T-10-01-01 — no credential leakage transitively.                |
| T-10-01-03   | Plaintext token in process memory — accepted (matches Phase 6+ baseline).                                    |
| T-10-01-04   | Adapter does NOT log directly in Plan 10-01 (no `logging.getLogger` call). RedactingFilter coverage lands when adapter is wired into transport (Plan 10-02/03). |
| T-10-01-05   | Fail-cache (`fail_cache_s=30.0`) prevents 10+ concurrent callers from each issuing `max_retries+1` requests. **Verified** by test P5. |
| T-10-01-06   | `PermanentRefreshError` bypasses fail-cache by design — operator escape hatch. **Verified** by test P6.       |
| T-10-01-07   | NO new third-party deps. `httpx` already in matriz-client deps. Package Legitimacy Gate NOT triggered.        |
| T-10-01-08   | 3-way `threading.Lock` + per-loop `asyncio.Lock` + `asyncio.to_thread`. **Verified** by 3-way stress S1.      |
| T-10-01-09   | `TokenSnapshot.refresh_call_id` carries an audit trail; Plan 10-02 transport will correlate via log records.  |

## Deviations from Plan

**None — plan executed exactly as written.**

The only minor adaptations made during execution (all in the spirit of the
plan's spec):

- `_refresh.py` LOC budget was tighter than expected; docstrings were
  trimmed (without sacrificing T-10-01-04 mitigation documentation) to land
  at 88 LOC ≤ 90 LOC acceptance bound.
- `_token_store.py` LOC trimmed via section-divider compaction to land at
  176 LOC ≤ 180 LOC.
- Added `_PERMANENT_STATUSES: dict[int, str]` lookup table in `_refresh.py`
  consolidating 3 sequential `if status == N` branches (400 / 401 / 403)
  — pure refactor, same behavior.
- Added 1 `test_unknown_refresh_error_subclass_treated_as_transient` test
  in `test_refresh_policy.py` exercising the "unknown `RefreshError`
  subclass" defensive branch — not in the plan's stated test list but
  exercises a defensive path the policy code contains.
- Added 1 `test_invalidate_forces_next_get_sync_to_refresh` test in
  `test_token_store.py` validating `TokenStore.invalidate()` (the method
  is in the plan's `<action>` step but the test was not enumerated in
  `<behavior>` — added for completeness ahead of Plan 10-03's 401
  re-auth-once consumer).

These do **not** change the plan's contracts — only add safety nets.

## Self-Check: PASSED

- [x] `packages/matriz-client/src/matriz_client/_refresh_errors.py` — exists, 39 LOC.
- [x] `packages/matriz-client/src/matriz_client/_refresh.py` — exists, 88 LOC.
- [x] `packages/matriz-client/src/matriz_client/_refresh_policy.py` — exists, 125 LOC.
- [x] `packages/matriz-client/src/matriz_client/_token_store.py` — exists, 176 LOC.
- [x] `packages/matriz-client/tests/test_refresh_errors.py` — exists, 6 tests pass.
- [x] `packages/matriz-client/tests/test_refresh_policy.py` — exists, 20 tests pass.
- [x] `packages/matriz-client/tests/test_token_store.py` — exists, 13 tests pass.
- [x] `.planning/codebase/CONCERNS.md` — D-05 `_async_locks` entry added.
- [x] Commit `3cd0a80` exists in `git log`.

## Next: Plan 10-02

`AsyncRetryTransport` (`_atransport.py`) + full `AsyncClient` REST surface
(`aio.py`) — see `.planning/phases/10-matriz-aio-py-creation-tokenstore/10-02-PLAN.md`.

---

*Generated: 2026-06-13 (Phase 10 Plan 10-01)*
*Commit: 3cd0a80*
