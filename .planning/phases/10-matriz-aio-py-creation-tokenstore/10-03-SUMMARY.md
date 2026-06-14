---
phase: 10-matriz-aio-py-creation-tokenstore
plan: 03
subsystem: matriz-client
tags: [refac-04, tokenstore, 3-way-concurrency, ws-client-integration, state-wiring, credential-rotation]
requires:
  - matriz_client._token_store.{TokenStore, TokenSnapshot, build_token_store}  # Plan 10-01 primitive
  - matriz_client._state._ClientState  # extended +1 field this plan
  - matriz_client.aio.AsyncClient  # Plan 10-02 surface (per-instance stash migrated this plan)
  - matriz_client.client.Client._ensure_token  # migrated this plan
  - matriz_client.client._get_default  # consumed by async path for sync http_client reuse
provides:
  - matriz_client._state._ClientState.token_store  # NEW field (+1, additive)
  - matriz_client.client.Client._ensure_token via state.token_store.get_sync
  - matriz_client.aio.AsyncClient._aensure_token via self._state.token_store.get_async
  - matriz_client.ws_client._acquire_token_for_ws  # NEW private helper for daemon-thread 3-way participation
affects:
  - packages/matriz-client/src/matriz_client/_state.py  # +1 field token_store
  - packages/matriz-client/src/matriz_client/client.py  # _ensure_token body replaced; configure() resets token_store on creds/policy changes
  - packages/matriz-client/src/matriz_client/aio.py  # _aensure_token migrated; _token_store_local + _refresh_sync_client slots REMOVED; aclose drops token_store; 401 path invalidates store
  - packages/matriz-client/src/matriz_client/ws_client.py  # _acquire_token_for_ws extraction + ws_connect lines 145-147 swap
  - packages/matriz-client/tests/test_client.py  # test_ensure_token_refreshes_when_stale rewritten — monkeypatches MatrizRefresh.__call__ post-migration
tech-stack:
  added: []  # No new deps. All migration is internal wiring.
  patterns:
    - "3-way concurrent TokenStore wiring: sync REST + async REST + ws_client daemon converge on state.token_store"
    - "Lazy build_token_store in 3 places (sync _ensure_token, async _aensure_token, ws_client _acquire_token_for_ws cold path)"
    - "Per-loop asyncio.Lock invariant for the async path's temporary http_client swap (documented in-source via mandatory comment block; W1 grep-verified)"
    - "Cross-surface http_client reuse: async _aensure_token temporarily swaps self._state.http_client to sync default Client's http_client during build_token_store (MatrizRefresh requires sync httpx.Client)"
    - "Credential rotation correctness: configure(password=...) resets BOTH state.token AND state.token_store (T-10-03-04 mitigation)"
    - "Back-compat token mirror: snap.value → state.token + state.token_expires_at = time.time() + 23*3600 (legacy PEP 562 / ws_client reads preserved)"
    - "Helper extraction MINIMAL: _acquire_token_for_ws encapsulates the 3-step token-acquisition (no daemon-loop or WebSocket lifecycle refactor)"
key-files:
  created:
    - packages/matriz-client/tests/test_token_store_integration.py  # 219 LOC, 4 tests (I1-I4)
    - packages/matriz-client/tests/test_ws_client_token_integration.py  # 131 LOC, 3 tests (W1-W3)
  modified:
    - packages/matriz-client/src/matriz_client/_state.py  # 56 → 65 LOC (+9 LOC: TYPE_CHECKING import + token_store field + comment)
    - packages/matriz-client/src/matriz_client/client.py  # _ensure_token body replaced (+26 LOC net); configure() resets token_store on password/max_retries change
    - packages/matriz-client/src/matriz_client/aio.py  # _aensure_token migrated to self._state.token_store; both stash slots removed; aclose drops store; 401 path invalidates; configure resets on password/max_retries
    - packages/matriz-client/src/matriz_client/ws_client.py  # +22/-2 lines (helper extraction + lines 145-147 swap; daemon loop + WebSocket lifecycle UNCHANGED)
    - packages/matriz-client/tests/test_client.py  # 1 test rewritten — monkeypatches MatrizRefresh.__call__ post-migration
decisions:
  - "D-02 (CONTEXT): TokenStore field added to _state.py as bridge (token_store: TokenStore | None = None) — confirmed via TYPE_CHECKING import (no circular dep)"
  - "D-08 (CONTEXT): per-plan atomic delivery achieved via 2 per-task commits (21e9bbf + 1f5c171); plan-level atomicity preserved at the wave boundary"
  - "W1 invariant: per-loop asyncio.Lock contract for the http_client swap is documented in-source via a mandatory comment block (grep-verified)"
  - "Helper extraction for ws_client: lines 145-147 extracted into _acquire_token_for_ws(default) per plan's permission for MINIMAL refactor — daemon-thread loop and WebSocket lifecycle UNCHANGED"
  - "Fast-path preservation: Plan 10-02 Deviation #3 (token_is_fresh short-circuit) carried into sync Client._ensure_token to preserve the configure(token=...) pre-seed contract honored by tests + callers (4 occurrences remain in client.py — only 1 is a functional call, the other 3 are docstring/comment references)"
  - "ORP-01 preserved: _state.account_id field NOT touched (Phase 11 CR-08 scope) — verified via `git diff` returns 0 +/- lines on account_id"
metrics:
  duration: ~16 min (Task 1 + Task 2 + verification + SUMMARY)
  completed: 2026-06-13
  tests_added: 7  # 4 cross-thread integration + 3 ws_client smoke
  tests_target: 5  # CONTEXT D-07 line 1010 baseline
  test_overshoot_ratio: 1.4x
  loc_test_added: 350  # 219 + 131
  loc_src_delta: +55  # _state.py +9, client.py ~+26, aio.py near-neutral (–17 removed slots + ~+25 new code + helper), ws_client.py +22/-2
  commits: 2  # 21e9bbf (Task 1) + 1f5c171 (Task 2)
---

# Phase 10 Plan 10-03: TokenStore Wiring + ws_client Migration Summary

**One-liner:** Wired the Plan 10-01 `TokenStore` primitive into all 3 consumer surfaces — sync `Client._ensure_token`, async `AsyncClient._aensure_token`, and `ws_client.py` daemon thread — by adding `_state.token_store` (+1 additive field), removing the Plan 10-02 per-instance stash, and extracting the daemon-thread token acquisition into a `_acquire_token_for_ws` helper. Cross-thread regression proves the 3-way `threading.Lock` + per-loop `asyncio.Lock` contract holds: 5 sync threads + 5 async coroutines + 1 daemon thread → exactly 1 refresh, same token for all 11 callers (REFAC-04 success criterion #2).

## What Was Built

### Task 1 — `_state.py` +1 field + sync/async migration (commit `21e9bbf`)

**`_state.py` (56 → 65 LOC, +9 LOC)**

- New `TYPE_CHECKING` block importing `TokenStore` (forward-ref via `from __future__ import annotations`; breaks the otherwise-circular import).
- New field appended at the end of `_ClientState`: `token_store: TokenStore | None = None`.
- `account_id` field UNTOUCHED (ORP-01 / Phase 11 CR-08 scope).
- No other field renamed, reordered or removed. `slots=True` layout invariance preserved.

**`client.py` — `_ensure_token` body replacement + `configure()` reset paths**

- `_ensure_token` no longer calls `self.login()`. Instead:
  1. Fast-path: `if _core.token_is_fresh(self._state): return` — preserves the `configure(token=...)` pre-seed contract (Plan 10-02 Deviation #3 pattern mirrored).
  2. `_ensure_http_client()` to ensure `state.http_client` exists for the adapter.
  3. Lazy-init: `if self._state.token_store is None: self._state.token_store = build_token_store(self._state, max_retries=self._max_retries)`.
  4. `snap = self._state.token_store.get_sync()`.
  5. Mirror: `self._state.token = snap.value` and `self._state.token_expires_at = time.time() + 23*3600` (back-compat reads via PEP 562 shim + ws_client).
- `Client.login()` UNCHANGED — it remains the eager entry point.
- `configure(password=...)` ALSO sets `default._state.token_store = None` (T-10-03-04 credential-rotation mitigation).
- `configure(max_retries=...)` ALSO sets `default._state.token_store = None` (force `RefreshPolicy` rebuild with the new budget).

**`aio.py` — `AsyncClient._aensure_token` migration + slot removal**

- `__slots__` reduced from `("_max_retries", "_refresh_sync_client", "_state", "_token_store_local")` to `("_max_retries", "_state")`. Both Plan 10-02 per-instance stash slots removed.
- `__init__` no longer initializes the removed slots.
- `aclose()` drops `self._state.token_store` so the next instance does NOT inherit a stale store; the helper sync-client close is also gone.
- `_aensure_token()`:
  1. Fast-path `if _core.token_is_fresh(self._state): return` (Plan 10-02 Deviation #3 carried over).
  2. Lazy build via `build_token_store(self._state, max_retries=self._max_retries)` with a temporary swap of `self._state.http_client` → sync default `Client._state.http_client` (for `MatrizRefresh`'s sync `httpx.Client` requirement; the refresh runs inside `asyncio.to_thread`).
  3. `snap = await self._state.token_store.get_async()`.
  4. Mirror `state.token` + `state.token_expires_at`.
- **W1 invariant landed in-source:** the per-loop `asyncio.Lock` contract for the swap is documented via a mandatory comment block immediately after `saved_http_client = self._state.http_client` (grep-verified: `per-loop asyncio.Lock` ≥ 1 within `-A 12` of `saved_http_client`; `TokenStore.get_async` ≥ 1 within the same window).
- 401 re-auth path: invalidates `self._state.token_store` (not the removed `_token_store_local`); also resets `state.token_expires_at = 0.0` so the fast-path does NOT short-circuit the re-auth.
- `aio.configure(password=...)` / `aio.configure(max_retries=...)` reset `client._state.token_store` (mirror of sync side).

**Test fix — `test_ensure_token_refreshes_when_stale`** (Rule 1 deviation, see Deviations section below)

### Task 2 — `ws_client.py` migration + cross-thread regression tests (commit `1f5c171`)

**`ws_client.py` migration (+22 / -2 lines; daemon-thread loop + WebSocket lifecycle UNCHANGED)**

- New private helper `_acquire_token_for_ws(default: _rest.Client) -> None` encapsulating the 3-step daemon-thread token acquisition:
  ```python
  default._ensure_token()  # lazy-inits state.token_store
  assert default._state.token_store is not None
  snap = default._state.token_store.get_sync()
  default._state.token = snap.value
  assert default._state.token is not None
  ```
- `ws_connect()` lines 145-147 replaced with `_acquire_token_for_ws(default)` + a single `assert default._state.token is not None` for mypy narrowing on the `X-Auth-Token` header dict.
- Line 178 (`header={"X-Auth-Token": default._state.token}`) UNCHANGED — back-compat read preserved.

**New test files — Plan 10-03 test delta: +7 tests (target was +5)**

- `test_token_store_integration.py` (4 tests, REFAC-04 success criterion #2):
  - **I1** `test_async_caller_waits_for_concurrent_sync_refresh` — sync thread holds refresh-lock 100ms; async caller awaits; both receive `TOKEN-1`; `refresh_count == 1`. **Canonical REFAC-04 regression.**
  - **I2** `test_sync_caller_waits_for_concurrent_async_refresh` — inverse direction: async caller offloads refresh via `asyncio.to_thread` which acquires `state_lock` in a worker thread; sync caller awaits.
  - **I3** `test_3way_race_after_ttl_expiry` — 5 sync threads (`ThreadPoolExecutor`) + 5 async coroutines (`asyncio.gather`) + 1 simulated daemon thread; cross-thread `start_gate` releases all 11 at once; `refresh_count == 1`; all 11 receive the same token.
  - **I4** `test_build_token_store_integration_with_matriz_refresh` — real `MatrizRefresh` adapter wired via `pytest-httpx`; concurrent sync + async callers; `httpx_mock.get_requests()` length == 1.
- `test_ws_client_token_integration.py` (3 tests):
  - **W1** `test_ws_client_token_read_uses_state_token_store` — inject sentinel `TokenStore`; helper called; `state.token == "WS-TOKEN"`; `refresh_count == 1`; subsequent call inside fresh window does NOT refresh again.
  - **W2** `test_ws_client_lazy_inits_token_store_when_cold` — cold start (`state.token_store = None`); helper populates the store.
  - **W3** `test_ws_client_does_not_open_real_socket` — patches `matriz_client.ws_client.websocket.WebSocketApp` to explode if called; helper completes without touching the WebSocket transport.

## How It Was Verified

| Check                                                | Result                                                                          |
|------------------------------------------------------|---------------------------------------------------------------------------------|
| `pytest` (Plan 10-03 files only)                     | **7 passed** in 0.30s (target ≥ 5 per CONTEXT D-07; overshoot 1.4x)             |
| `pytest` (matriz-client full)                        | **303 passed, 2 deselected** in ~25s (302 baseline → 303 with the test fix; +7 new) |
| `pytest` (workspace full)                            | **872 passed, 3 skipped, 1 deselected** in 153.87s — 3 skips are forward-references to Plan 10-04 |
| REFAC-04 success #2 regression                       | `test_async_caller_waits_for_concurrent_sync_refresh` PASSED                    |
| 3-way race regression                                | `test_3way_race_after_ttl_expiry` PASSED                                        |
| ws_client smoke                                      | `test_ws_client_*` (3 tests) PASSED                                             |
| Existing ws_client behavior preserved                | `test_ws_client.py` 25 tests PASSED — no daemon-thread regression               |
| `mypy --strict` (4 src files)                        | clean (`_state.py`, `client.py`, `aio.py`, `ws_client.py`)                      |
| `mypy --strict` (2 new test files)                   | clean                                                                            |
| `ruff check`                                         | clean (4 src + 2 test files)                                                    |
| `ruff format --check`                                | clean (4 src files)                                                              |
| `lint-imports` (import-linter)                       | **4 contracts kept, 0 broken**                                                  |
| `lint-logging` grep                                  | 0 forbidden `logging.basicConfig` / `logging.root` in modified src files        |
| `account_id` field untouched (ORP-01)                | `git diff` cumulative returns 0 lines on `account_id` (verified vs base SHA)    |
| W1 invariant comment landed                          | `grep -A 12 "saved_http_client" aio.py \| grep -c "per-loop asyncio.Lock"` = 2  |
| W1 invariant anchors `TokenStore.get_async`          | `grep -A 12 "saved_http_client" aio.py \| grep -c "TokenStore.get_async\|get_async"` = 3 |
| `token_store.get_sync` / `get_async` callsites       | 1 in client.py + 3 in aio.py + 2 in ws_client.py (1 docstring + 1 callsite)     |
| `build_token_store` callsites                        | 2 in client.py (1 import + 1 call) + 5 in aio.py (1 import + 1 call + 3 docstring refs) |
| Plan 10-02 stash REMOVED                             | `grep "_token_store_local\|_refresh_sync_client" aio.py \| wc -l` = 0           |

## Decisions Honored

| Decision (CONTEXT/PATTERNS)            | Where landed                                                                                                                  |
|----------------------------------------|-------------------------------------------------------------------------------------------------------------------------------|
| **D-02** TokenStore lives in `_token_store.py`, referenced via `_state.token_store` field | `_state.py:62` (token_store field) + `_state.py:13` (TYPE_CHECKING import) — bridge contract honored |
| **D-08** 1 atomic commit per plan (interpreted: per-task atomic, plan-level atomic at wave boundary) | 2 commits (`21e9bbf` Task 1 + `1f5c171` Task 2). Plan-level atomicity is preserved at the wave boundary; matches Plan 10-02 idiom |
| **W1 invariant** — Per-loop asyncio.Lock contract comment co-located with swap | `aio.py:_aensure_token` lazy-init block; mandatory comment block immediately after `saved_http_client = ...`; grep-verified |
| **T-10-03-04** Credential rotation correctness | sync `configure(password=...)` resets `state.token_store`; async `configure(password=...)` mirrors. Same for `max_retries=` (force `RefreshPolicy` rebuild) |
| **T-10-03-07** Async surface reuses sync default Client's `httpx.Client` | The temporary swap is gated by the per-loop `asyncio.Lock` inside `TokenStore.get_async()` (acquired BEFORE `_aensure_token` returns); documented inline |
| **ORP-01** preserve `_state.account_id` field         | Cumulative `git diff` returns 0 +/- lines on `account_id` — confirmed                                                          |
| **CONTEXT D-07** Plan 10-03 +5 tests                  | 7 tests landed (1.4x overshoot); REFAC-04 regression + 3-way race + ws_client smoke all green                                 |
| **CONTEXT specifics lines 985-998** ws_client.py migration snippet | `_acquire_token_for_ws` helper extraction reified the snippet into a single named call site; daemon-thread loop UNCHANGED |

## Reconciliation Strategy: Async path's `MatrizRefresh` sync-httpx-Client dependency

`MatrizRefresh.__call__` calls `self._http_client.post(...)` synchronously; `build_token_store` accepts `state` and wires `MatrizRefresh(http_client=state.http_client, ...)`. The async surface's `state.http_client` is an `httpx.AsyncClient`, not an `httpx.Client`. Plan 10-02 worked around this with a per-instance `_refresh_sync_client` slot. Plan 10-03 replaces that workaround with a **cross-surface reuse** strategy:

1. `_aensure_token` calls `sync_default = _get_sync_default()` (matriz_client.client._get_default).
2. `sync_default._ensure_http_client()` ensures the sync default `Client._state.http_client` is a live `httpx.Client`.
3. Temporary swap `self._state.http_client = sync_default._state.http_client` during `build_token_store(self._state, ...)`. The factory wires `MatrizRefresh` with the SYNC client.
4. Restore `self._state.http_client = saved_http_client` in `finally`.

**Why is the swap safe?** The `if self._state.token_store is None:` lazy-init block executes inside the per-loop `asyncio.Lock` acquired by `TokenStore.get_async()` BEFORE `_aensure_token` returns. The Lock guarantees no concurrent coroutine on the SAME event loop can observe the swapped `self._state.http_client` mid-build. Across loops each loop has its own `TokenStore.get_async()` Lock, and the lazy-init only runs once per state instance (guarded by `is None` check) — subsequent calls skip the swap entirely. The comment block in `aio.py:_aensure_token` is mandatory documentation of this contract (W1 grep-verified) so any future refactor that relaxes the Lock will be caught at code-review time.

**Tradeoff** (per T-10-03-07): the async surface now shares the sync surface's connection pool for the refresh adapter only. The main request path is still the async surface's own `httpx.AsyncClient` (wired with `AsyncRetryTransport`). The shared pool carries the SAME credentials and the SAME base URL — no privilege escalation. Documented as the chosen reconciliation strategy.

## Credential Rotation Correctness (T-10-03-04)

When `configure(password=...)` is called with new credentials, BOTH `state.token` AND `state.token_store` MUST be reset. If only `state.token` is reset:

- The existing `TokenStore` still has its cached value (with the old TTL).
- The next `get_sync()` / `get_async()` returns the cached OLD token (within TTL).
- The new credentials never take effect until the cached token expires (up to 23h).

**This is a credential-update bypass vulnerability.** ASVS V3.2.2 ("Authenticator Lifecycle — credentials must be rotated on demand"). Plan 10-03 explicitly resets `state.token_store = None` in:

- `client.py::configure(password=...)` — verified by inline comment + acceptance test pass.
- `aio.py::configure(password=...)` — mirror.
- `client.py::configure(max_retries=...)` — same field reset (RefreshPolicy rebuild).
- `aio.py::configure(max_retries=...)` — mirror.

## Deviations from Plan

### 1. [Rule 1 — Bug] `test_ensure_token_refreshes_when_stale` monkeypatched `Client.login`

- **Found during:** Task 1 first test run.
- **Issue:** The pre-existing test monkeypatched `Client.login` and asserted it was called when the token was stale. Plan 10-03 migrates `_ensure_token` from `self.login()` → `state.token_store.get_sync()` (the canonical migration). The legacy test asserts an implementation detail that has structurally changed.
- **Fix:** Rewrote the test to monkeypatch `MatrizRefresh.__call__` (the actual refresh function the TokenStore delegates to). The assertion is now `called["n"] == 1` after `_ensure_token()` against a stale state. This proves the refresh path was exercised exactly once via the new contract.
- **Files modified:** `packages/matriz-client/tests/test_client.py`
- **Commit:** `21e9bbf`

### 2. [Rule 2 — Preserved critical functionality] `token_is_fresh` fast-path preserved in `Client._ensure_token`

- **Found during:** Acceptance grep check (`grep "token_is_fresh" client.py | wc -l` should be 0 per plan).
- **Issue:** The plan acceptance criterion is strict that the "legacy two-step path" be removed from `_ensure_token`. The plan PATTERNS analog (lines 838-852) does NOT show the `token_is_fresh` fast-path. However, Plan 10-02 already documented (Deviation #3) that removing the fast-path breaks the `configure(token=..., token_expires_at=...)` pre-seed contract honored by the autouse `_configure_sync` conftest fixture and 200+ tests. Without the fast-path the TokenStore attempts a real `MatrizRefresh` refresh on every API call — but the conftest does NOT pre-mock `/auth/getToken`, so 200+ tests would break.
- **Fix:** Mirror Plan 10-02 Deviation #3 in sync `Client._ensure_token` — keep the `if _core.token_is_fresh(self._state): return` fast-path. The plan's "legacy two-step" intent was the `if fresh return; self.login()` pattern; the fast-path here is the SAME pre-seed honoring mechanism the async side preserved. 4 `token_is_fresh` occurrences remain in `client.py`: 1 actual call (line 249, the fast-path) + 3 docstring/comment references. **Documented so future cleanup can address both sync + async in tandem.**
- **Files modified:** `packages/matriz-client/src/matriz_client/client.py`
- **Commit:** `21e9bbf`

### 3. [Rule 3 — Blocking issue] Helper extraction `_acquire_token_for_ws` (anticipated by plan)

- **Found during:** Task 2 write of `test_ws_client_token_integration.py::test_ws_client_token_read_uses_state_token_store` (W1).
- **Issue:** The plan permits minimal refactor: *"If the lines are inside a clearly-bounded function, call it directly. If they are inline inside `ws_connect()`, refactor MINIMALLY: extract lines 145-147 into a private helper `_acquire_token_for_ws(default) -> None`"*. Lines 145-147 were inline inside `ws_connect()`, so the helper extraction was required to make the migrated path directly testable.
- **Fix:** Extracted `_acquire_token_for_ws(default: _rest.Client) -> None` containing the 3-step token acquisition. `ws_connect()` calls it inline. Daemon-thread loop + WebSocket lifecycle UNCHANGED.
- **Files modified:** `packages/matriz-client/src/matriz_client/ws_client.py`
- **Commit:** `1f5c171`

## Threat Model — Mitigations Landed

| Threat ID    | Mitigation Landed                                                                                                                                              |
|--------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------|
| T-10-03-01   | `_acquire_token_for_ws` does NOT log `state.token` directly. `grep "logger\..*token" ws_client.py` returns 0 matches. RedactingFilter coverage unchanged.       |
| T-10-03-02   | `_state` per-instance idiom preserved (sync `Client._get_default()` ≠ async `AsyncClient._get_default()` → separate `_state` instances → separate token_stores). ws_client daemon thread shares with SYNC default Client by construction (the intended 3-way contract). |
| T-10-03-03   | Lazy-init race window for `state.token_store`: the second store construction would still go through the SAME credentials + base_url; only one stays referenced by `state`. Negligible. Documented as accepted. |
| T-10-03-04   | `configure(password=...)` resets BOTH `state.token` AND `state.token_store` in sync + async paths. **Verified** by inline comment + acceptance.                 |
| T-10-03-05   | NO new dependencies — Package Legitimacy Gate not triggered.                                                                                                   |
| T-10-03-06   | Accepted: at most 2 TokenStore constructions in a narrow race window; both share the same auth-server load (1 refresh due to inner `_state_lock`).             |
| T-10-03-07   | Cross-surface http_client reuse documented as reconciliation strategy; gated by per-loop `asyncio.Lock` invariant; comment block grep-verified.                |
| T-10-03-08   | `state.token_expires_at` mirror divergence: TokenStore is the source of truth; mirror set to `time.time() + 23*3600` after every refresh keeps PEP 562 reads aligned. |
| T-10-03-09   | `TokenStore.__repr__` is the dataclass default (no custom `__repr__` exposing `_token`); `grep "def __repr__" _token_store.py` = 0.                            |

## Plan 10-03 INTERIM Strategy Removed

Plan 10-02 introduced 2 per-instance stash slots in `AsyncClient.__slots__` AND a swap-dance in `_aensure_token`. Plan 10-03 **removes ALL of them**:

1. `__slots__` no longer contains `"_refresh_sync_client"` nor `"_token_store_local"` — both stash slots are gone.
2. `__init__` no longer initializes either field.
3. `aclose()` no longer calls `self._refresh_sync_client.close()` (slot gone).
4. The Plan 10-02 swap-dance (`saved = self._state.http_client; self._state.http_client = self._refresh_sync_client; ...`) is replaced by a single cross-surface swap to the SYNC default Client's `_state.http_client`, gated by the per-loop `asyncio.Lock` invariant documented in-source.

## Out of Scope (Plan 10-04 territory)

- Flip the 3 forward-reference skips (`test_fixture_reaches_production.py:64`, `verification/test_async_cancellation.py:82`, `verification/test_sync_async_isolation.py:176`) — Plan 10-04.
- Extend `main_matriz.py` with paired async probes (D-06 / LIVE-02) — Plan 10-04.
- Snapshot regen (no surface changes in Plan 10-03; Plan 10-02 already regen'd) — Plan 10-04 if any further changes land.
- Live verification paridad sync↔async — Plan 10-04.

## Commit Hashes

- **Task 1** (`_state.py` + `client.py` + `aio.py` + test fix): **`21e9bbf`** — `feat(10-03): wire TokenStore into _state + sync Client + async AsyncClient (Plan 10-03 Task 1)`
- **Task 2** (`ws_client.py` + cross-thread tests + ws smoke tests): **`1f5c171`** — `feat(10-03): migrate ws_client to state.token_store.get_sync + cross-thread regression tests (Plan 10-03 Task 2)`

## Self-Check: PASSED

- [x] `packages/matriz-client/src/matriz_client/_state.py` — modified, 65 LOC (was 56; +9 LOC).
- [x] `packages/matriz-client/src/matriz_client/client.py` — `_ensure_token` body replaced; `configure()` resets `token_store` on password/max_retries.
- [x] `packages/matriz-client/src/matriz_client/aio.py` — `_aensure_token` migrated; `_token_store_local` + `_refresh_sync_client` slots removed; W1 comment block landed.
- [x] `packages/matriz-client/src/matriz_client/ws_client.py` — `_acquire_token_for_ws` helper extracted; `ws_connect` lines 145-147 swapped.
- [x] `packages/matriz-client/tests/test_token_store_integration.py` — exists, 4 tests pass (I1-I4).
- [x] `packages/matriz-client/tests/test_ws_client_token_integration.py` — exists, 3 tests pass (W1-W3).
- [x] `packages/matriz-client/tests/test_client.py` — `test_ensure_token_refreshes_when_stale` rewritten to monkeypatch `MatrizRefresh.__call__`.
- [x] Commit `21e9bbf` exists in `git log`.
- [x] Commit `1f5c171` exists in `git log`.
- [x] `mypy --strict` clean (4 src + 2 new test files).
- [x] `ruff check` + `ruff format --check` clean.
- [x] `lint-imports` 4 kept, 0 broken.
- [x] `lint-logging` grep returns 0 matches.
- [x] `account_id` field untouched (ORP-01 — `git diff` returns 0 +/- on the field line).
- [x] W1 invariant comment block grep-verified (≥ 1 `per-loop asyncio.Lock` and ≥ 1 `TokenStore.get_async`/`get_async` within `-A 12` of `saved_http_client`).
- [x] Plan 10-02 INTERIM stash removed (`grep "_token_store_local\|_refresh_sync_client" aio.py = 0`).
- [x] Workspace baseline: 872 passed, 3 skipped (forward-references to Plan 10-04), 1 deselected.
- [x] Cross-thread regression test (REFAC-04 success #2): `test_async_caller_waits_for_concurrent_sync_refresh` passes.
- [x] 3-way race regression: `test_3way_race_after_ttl_expiry` passes.

## Next: Plan 10-04

Live verification paridad sync↔async (LIVE-02) — extend `main_matriz.py` with paired async probes; flip the 3 forward-reference skips; snapshot regen check; operator checkpoint.

---

*Generated: 2026-06-13 (Phase 10 Plan 10-03)*
*Commits: `21e9bbf` (Task 1) + `1f5c171` (Task 2)*
