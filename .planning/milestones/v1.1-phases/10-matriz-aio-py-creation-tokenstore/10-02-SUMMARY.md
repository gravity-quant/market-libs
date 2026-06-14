---
phase: 10-matriz-aio-py-creation-tokenstore
plan: 02
subsystem: matriz-client
tags: [refac-04, async-rest, asyncretrytransport, pep-562, mutation-gate, token-store-consumer, d-25-carve-out-closed]
requires:
  - matriz_client._token_store.{TokenStore, build_token_store}  # Plan 10-01 primitive
  - matriz_client._transport.{_LOGGER_NAME, _RETRY_AFTER_CAP_S, _RETRYABLE_EXC, _is_retryable_status, _parse_retry_after, _RetryableStatus}  # sync transport intra-package import
  - matriz_client._core.{RequestSpec, raise_for_response, all builders/parsers}
  - matriz_client._state._ClientState (unchanged; Plan 10-03 will extend with `token_store` field)
  - matriz_client.client._validate_max_retries (re-used so the async validation matches sync 1:1)
provides:
  - matriz_client._atransport.AsyncRetryTransport  # async retry transport closing D-25 carve-out
  - matriz_client.aio.AsyncClient  # full async REST class (22 endpoints + lifecycle)
  - matriz_client.aio.{configure, login, aclose}  # module-level shims on default singleton
  - matriz_client.aio.{get_segments, get_all_instruments, get_instruments_details, get_instrument_detail, get_instruments_by_cfi, get_instruments_by_segment, new_order, replace_order, cancel_order, get_order_status, get_order_history, get_active_orders, get_filled_orders, get_all_orders, get_order_by_exec_id, get_market_data, get_trades, get_positions, get_detailed_positions, get_account_report}  # 20 endpoint delegators
  - PEP 562 shim: matriz_client.aio.{_token, _token_expires_at, _base_url, _client}
affects:
  - packages/matriz-client/src/matriz_client/__init__.py  # comment only: AsyncClient export comment updated from "stub" to "full surface"
  - packages/matriz-client/tests/conftest.py  # +_configure_async autouse fixture
  - packages/matriz-client/tests/test_client_class.py  # 1 test renamed + rewritten for full surface (was stub-only assertion)
  - verification/snapshots/matriz-client-surface.txt  # AsyncClient signature regenerated with max_retries + http_client kwargs (snapshot guard hard-requires)
tech-stack:
  added: []  # No new runtime deps. tenacity / httpx / pytest_httpx / pytest_asyncio all pre-existed.
  patterns:
    - "Async retry transport mirroring sync RetryTransport (AsyncRetrying + async for + await asyncio.sleep)"
    - "D-32 CancelledError-aware Retry-After honor (await asyncio.sleep, NOT time.sleep)"
    - "Pitfall 4 mutation gate in async (request.extensions['idempotent'] = False → exactly 1 wire request on 503)"
    - "D-22 auth_basic log split (user operational + password=***) propagated by the async transport"
    - "B8 lock-in: aio._raise_for_response IS client._raise_for_response IS _core.raise_for_response (same function object)"
    - "PEP 562 read-only shim (_token / _base_url / _token_expires_at / _client forwarded to _state)"
    - "Lazy TokenStore consumer (build_token_store called once per AsyncClient instance, with sync httpx.Client swap for MatrizRefresh)"
    - "401 re-auth-once flow with TokenStore.invalidate() trigger"
    - "Body-consume-then-raise async mirror (await resp.aread() before raise on 401)"
key-files:
  created:
    - packages/matriz-client/src/matriz_client/_atransport.py  # 173 LOC
    - packages/matriz-client/tests/test_atransport.py  # 276 LOC, 9 tests
    - packages/matriz-client/tests/test_async_auth.py  # 245 LOC, 11 tests
    - packages/matriz-client/tests/test_async_queries.py  # 339 LOC, 19 tests
    - packages/matriz-client/tests/test_async_mutations.py  # 164 LOC, 5 tests
  modified:
    - packages/matriz-client/src/matriz_client/aio.py  # 103 → 837 LOC (stub → full REST surface)
    - packages/matriz-client/src/matriz_client/__init__.py  # comment-only delta on AsyncClient export
    - packages/matriz-client/tests/conftest.py  # +_configure_async autouse fixture
    - packages/matriz-client/tests/test_client_class.py  # 1 test renamed (Phase 6 stub-only → Plan 10-02 full surface assertion)
    - verification/snapshots/matriz-client-surface.txt  # AsyncClient signature regen (max_retries + http_client kwargs added)
decisions:
  - "D-01 honored: 1 new src file (_atransport.py) + aio.py full replace; atomic per-task commits (Task 1 + Task 2)"
  - "D-02 honored: TokenStore consumed via lazy build_token_store (Plan 10-01 primitive); per-instance _token_store_local stash (Plan 10-03 migrates to _state.token_store)"
  - "D-03 honored: max_retries propagated from AsyncClient(__init__) → build_token_store(state, max_retries=...) → RefreshPolicy"
  - "D-04 honored: matriz 23h TTL applied to state.token_expires_at after every TokenStore refresh (mirror of sync token_is_fresh contract)"
  - "D-08 honored: 2 separate commits per task within the plan (Task 1: AsyncRetryTransport; Task 2: AsyncClient REST surface). Plan-level atomicity preserved at the wave boundary."
  - "D-22 honored: AsyncRetryTransport extras carry auth_basic_user (operational) + auth_basic_password='***' (redacted) by splitting the tuple INSIDE the transport, not relying on the RedactingFilter post-emission"
  - "D-25 carve-out closed: matriz_client._atransport.py shipped per Phase 8 Plan 5 deferral note"
  - "D-32 honored: await asyncio.sleep used for Retry-After (CancelledError-aware); explicitly tested in T6"
  - "B8 D-04 lock-in preserved: aio imports raise_for_response from _core (not from client.py); identity invariant test landed"
  - "Plan-level deviation: snapshot regen included in Task 2 commit (matriz only — iol/higyrus/ambito unchanged) because test_snapshot_regen_is_idempotent hard-guards against drift; plan's 'no regen' note is superseded by the CI guard. iol/higyrus/ambito/wallets snapshots zero-diff confirmed."
metrics:
  duration: ~23 min (planning + implementation + CI green + SUMMARY)
  completed: 2026-06-13
  tests_added: 44  # 9 transport + 11 auth + 19 queries + 5 mutations
  tests_target: 30  # CONTEXT D-07 line 1009 target
  test_overshoot_ratio: 1.47x
  loc_src_added: 173  # _atransport.py
  loc_src_grown: 734  # aio.py: 103 → 837 (delta = +734)
  loc_test_added: 1024  # sum of 4 new test files
  commits: 2  # ea1ddab (Task 1) + d516306 (Task 2)
---

# Phase 10 Plan 10-02: matriz AsyncClient + AsyncRetryTransport Summary

**One-liner:** Matriz `aio.py` 103-LOC stub grown into 837-LOC `AsyncClient` exposing all 22 REST endpoints (mirroring sync `Client` 1:1) + module-level delegators + PEP 562 shim + lazy `TokenStore` consumer; new `_atransport.py` (173 LOC) closes Phase 8 D-25 carve-out with `AsyncRetryTransport` (async mirror of sync `RetryTransport` honoring Pitfall 4 mutation gate, D-32 CancelledError-safe Retry-After, and D-22 `auth_basic` log redaction).

## What Was Built

### Task 1 — `_atransport.py` (173 LOC) — `AsyncRetryTransport`

Subclass of `httpx.AsyncHTTPTransport` that mirrors the sync `_transport.RetryTransport` over `tenacity.AsyncRetrying`:

- **Mutation gate (Pitfall 4 / D-01)** — `request.extensions["idempotent"] = False` bypasses the retry loop entirely. CRITICAL for `new_order` / `cancel_order` / `replace_order` which are HTTP GET (Primary API quirk) but semantically mutations.
- **Idempotent retry** — 408 / 409 / 429 / 5xx retried per `_is_retryable_status`; `_RETRYABLE_EXC` (httpx ConnectError / ConnectTimeout / ReadTimeout) retried via `tenacity` exception filter.
- **D-32 Retry-After honor** — `await asyncio.sleep(min(delay, _RETRY_AFTER_CAP_S))` so `asyncio.CancelledError` propagates naturally during the sleep (Pitfall 16).
- **D-22 `auth_basic` log redaction split** — the transport splits the `(user, password)` tuple from `request.extensions["auth_basic"]` into `auth_basic_user` (operational) + `auth_basic_password="***"` (redacted) BEFORE passing to the log record extras. This means the WARNING/ERROR records emitted by the async transport NEVER carry the raw password literal, even if the `matriz_client` logger's `RedactingFilter` is bypassed.
- **D-19 bypass** — `max_attempts=1` short-circuits the tenacity loop entirely (1 wire request total).

All retryable surfaces / parsing helpers / module-level constants imported from `matriz_client._transport` (intra-package coupling — same pattern iol uses).

### Task 2 — `aio.py` (103 → 837 LOC) — `AsyncClient` full REST surface

**`AsyncClient` class** with `__slots__ = ("_max_retries", "_refresh_sync_client", "_state", "_token_store_local")`:

- Lifecycle: `__init__`, `__aenter__`, `__aexit__`, `aclose` (idempotent — closes the underlying `httpx.AsyncClient` AND the INTERIM per-instance sync refresh client), `__repr__` (redacted), `__reduce__` / `__deepcopy__` (raise `TypeError`).
- HTTP plumbing: `_ensure_http_client` (lazy `httpx.AsyncClient(transport=AsyncRetryTransport(...))`), `_aensure_token` (lazy `build_token_store` + fast-path token_is_fresh short-circuit + Plan 10-02 INTERIM sync httpx.Client swap for `MatrizRefresh`), `login` (explicit eager async login).
- Transport shell `_request`: mirrors sync `client._request` semantics 1:1 — Risk API BasicAuth path (no re-auth per D-23, body-consume on 401), Token path (X-Auth-Token + 401 re-auth-once with `TokenStore.invalidate()`).
- **22 endpoint methods** matching sync `Client` signatures exactly: `get_segments`, `get_all_instruments`, `get_instruments_details`, `get_instrument_detail`, `get_instruments_by_cfi`, `get_instruments_by_segment`, `new_order`, `replace_order`, `cancel_order`, `get_order_status`, `get_order_history`, `get_active_orders`, `get_filled_orders`, `get_all_orders`, `get_order_by_exec_id`, `get_market_data`, `get_trades`, `get_positions`, `get_detailed_positions`, `get_account_report` + `login` + `aclose`.

**Module-level surface:**
- `_default_async_client: AsyncClient | None` lazy singleton with `_get_default()` accessor.
- `configure(...)` runtime override (mirrors sync `client.configure` semantics + Plan 10-02 additions: `password=` resets `_token_store_local`; `max_retries=` drops both the cached `httpx.AsyncClient` AND `_token_store_local`).
- 22 module-level `async def X(...)` delegators that `await _get_default().X(...)`.
- PEP 562 `__getattr__` shim forwarding `_token` / `_token_expires_at` / `_base_url` / `_client` to `_state`.

### Test scaffolding

- `tests/conftest.py` — added `_configure_async` autouse fixture mirroring iol-client pattern.
- `tests/test_atransport.py` (9 tests) — T1-T8 + matriz-specific request_id/account_id propagation.
- `tests/test_async_auth.py` (11 tests) — AA1-AA8 + B8 lock-in + PEP 562 shim coverage.
- `tests/test_async_queries.py` (19 tests) — AQ1-AQ17 + CFI guard + 200-OK status=ERROR propagation.
- `tests/test_async_mutations.py` (5 tests) — AM1-AM4 + idempotent GET contrast.

## How It Was Verified

| Check                              | Result                                                                                              |
|------------------------------------|-----------------------------------------------------------------------------------------------------|
| `pytest` (Plan 10-02 files only)   | **44 passed** in ~6s (target ≥ 30 per CONTEXT D-07)                                                 |
| `pytest` (matriz-client full)      | **297 passed, 1 skipped** in ~25s (1 skip = `test_fixture_reaches_production.py:64` — Plan 10-04)   |
| `pytest` (workspace full)          | **865 passed, 3 skipped, 1 deselected** in ~160s (3 skips = forward-references to Plan 10-04)       |
| `mypy --strict`                    | clean (3 src files: `_atransport.py`, `aio.py`, `__init__.py`)                                      |
| `ruff check`                       | clean (3 src + 5 test files + conftest)                                                             |
| `ruff format --check`              | clean (all 8 files)                                                                                 |
| `lint-imports` (import-linter)     | **4 contracts kept, 0 broken**                                                                       |
| `lint-logging` grep                | 0 forbidden `logging.basicConfig` / `logging.root` in `aio.py` / `_atransport.py`                    |
| Snapshot test                      | `test_snapshot_regen_is_idempotent` passes (matriz `AsyncClient` signature snapshot updated; iol/higyrus/ambito/wallets zero-diff) |
| B8 lock-in (D-04)                  | `aio._raise_for_response is client._raise_for_response is _core.raise_for_response` ✓               |
| Pitfall 4 mutation gate (CRITICAL) | `test_async_new_order_503_does_not_retry` / `test_async_cancel_order_503_does_not_retry` / `test_async_replace_order_503_does_not_retry` — EXACTLY 1 wire request on 503 each ✓ |
| D-22 auth_basic redaction          | `test_auth_basic_tuple_split_in_warning_log_record` — `auth_basic_user="operator-u"` + `auth_basic_password="***"`; password literal never in any record ✓ |
| D-32 CancelledError                | `test_cancelled_error_propagates_during_retry_after_sleep` — `task.cancel()` during Retry-After sleep raises `asyncio.CancelledError` ✓ |
| Untouched invariants               | `client.py` / `_state.py` / `ws_client.py` — `git diff` returns 0 lines for all three              |

## Decisions Honored

| Decision | What it meant                                                                                 | Where landed                                                                                                                |
|----------|-----------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------|
| **D-01** | Atomic per-task commits within the plan                                                       | Commits `ea1ddab` (Task 1 _atransport.py) + `d516306` (Task 2 aio.py)                                                       |
| **D-02** | TokenStore consumed via lazy `build_token_store`; per-instance stash for Plan 10-02 INTERIM   | `aio.AsyncClient._aensure_token` lines 256-302; `self._token_store_local` slot removed in Plan 10-03 Task 1                  |
| **D-03** | `max_retries` propagated from AsyncClient kwarg → `build_token_store` → `RefreshPolicy`        | `aio.AsyncClient.__init__` line 137; `_aensure_token` line 281 (`build_token_store(state, max_retries=self._max_retries)`) |
| **D-04** | 23h matriz TTL applied to `state.token_expires_at` after every TokenStore refresh             | `aio.AsyncClient._aensure_token` line 302 (`state.token_expires_at = time.time() + 23 * 3600`)                              |
| **D-08** | Per-task commits inside the plan, atomic at wave boundary                                     | 2 commits within wave 2, atomic at the wave merge                                                                            |
| **D-22** | `auth_basic` log split (user op + password=***) by the async transport                        | `_atransport.AsyncRetryTransport.handle_async_request` lines 124-137 + `_async_replace_order` parallel ERROR path           |
| **D-25** | Carve-out closure: matriz async retry transport delivered alongside the async REST surface     | `packages/matriz-client/src/matriz_client/_atransport.py` (new file, 173 LOC)                                                |
| **D-32** | `await asyncio.sleep` (NOT `time.sleep`) so `asyncio.CancelledError` propagates                | `_atransport.AsyncRetryTransport.handle_async_request` line 109                                                              |
| **B8 (D-04)** | `aio._raise_for_response is client._raise_for_response is _core.raise_for_response` | `from matriz_client._core import raise_for_response as _raise_for_response` (aio.py line 70); test `test_b8_aio_raise_for_response_lock_in` |

## Deviations from Plan

### 1. [Rule 3 — Blocking issue] Updated `test_matriz_module_aio_exists_and_exports_async_client_only`

- **Found during:** Task 2 baseline regression check
- **Issue:** Pre-existing test asserted the Phase 6 stub contract (`aio.__all__ == ["AsyncClient"]`; `not hasattr(aio_mod, "configure")`; etc.). Plan 10-02 explicitly grows that surface — the test is now incompatible with the spec.
- **Fix:** Renamed to `test_matriz_module_aio_exposes_full_rest_surface` and rewrote assertions to verify the post-Plan-10-02 reality: 22 delegators + `configure` + `login` + `aclose` + `_get_default` all present.
- **Files modified:** `packages/matriz-client/tests/test_client_class.py`
- **Commit:** `d516306`

### 2. [Rule 3 — Blocking issue] Snapshot regen included in Task 2 commit

- **Found during:** Workspace baseline regression
- **Issue:** Plan line 489 says "Snapshot diff NOT regenerated in Plan 10-02 (Plan 10-04 owns snapshot regen)". But `verification/test_phase06_nyquist_gaps.py::test_snapshot_regen_is_idempotent` is a HARD guard that runs `regen_snapshots.py` and asserts `git diff --exit-code verification/snapshots/` is 0. Plan 10-02 grew `AsyncClient` kwargs (`max_retries`, `http_client`) → `regen_snapshots.py` produces a 1-line diff that the test refuses.
- **Fix:** Regenerated `verification/snapshots/matriz-client-surface.txt` and committed in Task 2. Only matriz changed (iol/higyrus/ambito/wallets snapshots zero-diff — consistent with the plan's "matriz-only growth" claim).
- **Files modified:** `verification/snapshots/matriz-client-surface.txt`
- **Commit:** `d516306`

### 3. [Rule 2 — Missing critical functionality] Token freshness short-circuit in `_aensure_token`

- **Found during:** Task 2 first test run — every `get_*` call attempted a fresh TokenStore refresh via `asyncio.to_thread` even when the conftest pre-seeded a valid token, breaking ALL query/mutation tests.
- **Issue:** The plan's `_aensure_token` spec (line 354 of PLAN.md) called `build_token_store` + `get_async()` unconditionally on every request. But the sync `client._ensure_token` short-circuits on `_core.token_is_fresh(self._state)` — the async path MUST mirror that to honor the `configure(token=..., token_expires_at=...)` pre-seed contract that the conftest fixture + callers rely on.
- **Fix:** Added the `if _core.token_is_fresh(self._state): return` fast-path at the top of `_aensure_token` (after `_ensure_http_client`). When the refresh DOES run via TokenStore, the result is mirrored back to `state.token` + `state.token_expires_at = time.time() + 23 * 3600` so subsequent calls take the fast path until the matriz 23h TTL elapses.
- **Files modified:** `packages/matriz-client/src/matriz_client/aio.py`
- **Commit:** `d516306`

## Plan 10-02 INTERIM Strategy Documentation

The Plan documents INTERIM stashes that **Plan 10-03 Task 1 will remove**:

1. **`self._token_store_local: TokenStore | None`** — per-instance TokenStore stash. Plan 10-03 migrates to `self._state.token_store` (new field on `_ClientState`) so the sync `Client`, the async `AsyncClient`, and the WebSocket daemon thread all share ONE store. The `_token_store_local` slot is dropped from `__slots__`.

2. **`self._refresh_sync_client: httpx.Client | None`** — per-instance sync `httpx.Client` required by `MatrizRefresh` (which runs inside `asyncio.to_thread` per the Plan 10-01 contract). Plan 10-03 Task 1 replaces this per-instance client with the SYNC default `Client`'s `_state.http_client` (unified connection pool), removing the swap dance in `_aensure_token`.

3. **The swap dance in `_aensure_token`** — currently:
   ```python
   saved = self._state.http_client
   self._state.http_client = self._refresh_sync_client
   try:
       self._token_store_local = build_token_store(self._state, max_retries=self._max_retries)
   finally:
       self._state.http_client = saved
   ```
   Required because `build_token_store` reads `state.http_client` to wire `MatrizRefresh`. Plan 10-03 removes this dance entirely.

## Out of Scope (Plan 10-03 / 10-04 territory)

- `client.py` sync `_ensure_token()` migration to consume the unified `_state.token_store` → **Plan 10-03**
- `_state.py` `+1 token_store: TokenStore | None` field → **Plan 10-03**
- `ws_client.py` REST-token consumer (lines 145-147) swap to `state.token_store.get_sync()` → **Plan 10-03**
- Cross-thread integration tests (sync + async + ws_client all hitting one TokenStore) → **Plan 10-03**
- Flip the 3 forward-reference skips (`test_fixture_reaches_production.py:64`, `verification/test_async_cancellation.py:82`, `verification/test_sync_async_isolation.py:176`) → **Plan 10-04**
- Phase 10 final snapshot regen (if any further surface changes land in 10-03/10-04) → **Plan 10-04**

## Threat Model — Mitigations Landed

| Threat ID    | Mitigation Landed In                                                                                                                                  |
|--------------|--------------------------------------------------------------------------------------------------------------------------------------------------------|
| T-10-02-01   | `AsyncClient.__repr__` returns `password='***'` + `token='***'`; `test_repr_redacts_password_and_token` (AA4) verifies neither literal appears        |
| T-10-02-02   | `__reduce__` / `__deepcopy__` raise `TypeError`; AA5 / AA6 tests cover pickle + `copy.deepcopy`                                                       |
| T-10-02-03   | `AsyncRetryTransport` splits `auth_basic` tuple INSIDE the transport into `auth_basic_user` + `auth_basic_password="***"`; T8 caplog test verifies     |
| T-10-02-04   | `await resp.aread()` before raising `AuthenticationError` on 401 (both Risk API and Token paths) — see `aio._request` lines 350 + 388                  |
| T-10-02-05   | NO new dependencies — Package Legitimacy Gate not triggered                                                                                            |
| T-10-02-06   | `_atransport.handle_async_request` reads `request.extensions.get("idempotent", False)`; mutation tests AM2/AM3/AM4 prove EXACTLY 1 wire request on 503 |
| T-10-02-07   | `AsyncRetryTransport(max_attempts=N+1)` cap + `_RETRY_AFTER_CAP_S=60` cap combined with Plan 10-01's `RefreshPolicy.fail_cache_s` prevent retry storms |
| T-10-02-08   | `await asyncio.sleep` (NOT `time.sleep`); T6 test explicitly cancels a task during Retry-After sleep and asserts `asyncio.CancelledError` propagates  |
| T-10-02-09   | `req.extensions["request_id"] = uuid.uuid4().hex` set in `aio._request` + `aio.login` + `aio._send_*`; transport propagates to log records             |
| T-10-02-10   | Plan 10-02 + Plan 10-03 ship in the same phase merge cycle; 10-04 green-gate gates phase merge                                                          |
| T-10-02-11   | `test_b8_aio_raise_for_response_lock_in` asserts identity invariant                                                                                    |

## Snapshot Diff (Matriz-only)

```diff
- AsyncClient : class : (*, base_url: 'str | None' = None, username: 'str | None' = None, password: 'str | None' = None, token: 'str | None' = None, token_expires_at: 'float | None' = None) -> 'None'
+ AsyncClient : class : (*, base_url: 'str | None' = None, username: 'str | None' = None, password: 'str | None' = None, token: 'str | None' = None, token_expires_at: 'float | None' = None, max_retries: 'int' = 2, http_client: 'httpx.AsyncClient | None' = None) -> 'None'
```

iol-client / higyrus-client / ambito-financiero-client / wallets-client snapshots: **zero diff** (confirmed via `git diff --stat verification/snapshots/`).

## Commit Hashes

- **Task 1** (`_atransport.py` + tests): **`ea1ddab`** — `feat(10-02): AsyncRetryTransport closes D-25 carve-out (Plan 10-02 Task 1)`
- **Task 2** (`aio.py` full REST surface + tests + snapshot regen): **`d516306`** — `feat(10-02): AsyncClient full REST mirror + PEP 562 shim (Plan 10-02 Task 2)`

## Self-Check: PASSED

- [x] `packages/matriz-client/src/matriz_client/_atransport.py` — exists, 173 LOC.
- [x] `packages/matriz-client/src/matriz_client/aio.py` — exists, 837 LOC (grew from 103-LOC stub).
- [x] `packages/matriz-client/src/matriz_client/__init__.py` — AsyncClient re-exported (comment delta only).
- [x] `packages/matriz-client/tests/conftest.py` — `_configure_async` autouse fixture present.
- [x] `packages/matriz-client/tests/test_atransport.py` — 9 tests pass.
- [x] `packages/matriz-client/tests/test_async_auth.py` — 11 tests pass.
- [x] `packages/matriz-client/tests/test_async_queries.py` — 19 tests pass.
- [x] `packages/matriz-client/tests/test_async_mutations.py` — 5 tests pass.
- [x] `verification/snapshots/matriz-client-surface.txt` — AsyncClient signature regenerated; iol/higyrus/ambito/wallets unchanged.
- [x] Commit `ea1ddab` (Task 1) exists in `git log`.
- [x] Commit `d516306` (Task 2) exists in `git log`.
- [x] `client.py` UNTOUCHED — `git diff packages/matriz-client/src/matriz_client/client.py` returns 0 lines.
- [x] `_state.py` UNTOUCHED — `git diff packages/matriz-client/src/matriz_client/_state.py` returns 0 lines.
- [x] `ws_client.py` UNTOUCHED — `git diff packages/matriz-client/src/matriz_client/ws_client.py` returns 0 lines.
- [x] `uv run mypy --strict packages/matriz-client/src/matriz_client/{_atransport,aio,__init__}.py` exits 0.
- [x] `uv run ruff check` exits 0 on 3 src + 5 test files + conftest.
- [x] `uv run lint-imports` reports 4 contracts kept, 0 broken.
- [x] Workspace baseline: 865 passed, 3 skipped (forward-references), 1 deselected — green.

## Next: Plan 10-03

Migrate `_token_store_local` → `_state.token_store`, remove per-instance `_refresh_sync_client`, swap `ws_client.py` REST-token consumer to `state.token_store.get_sync()`, add cross-thread integration tests (sync REST + async REST + ws daemon all coordinating through one TokenStore).

---

*Generated: 2026-06-13 (Phase 10 Plan 10-02)*
*Commits: ea1ddab (Task 1) + d516306 (Task 2)*
