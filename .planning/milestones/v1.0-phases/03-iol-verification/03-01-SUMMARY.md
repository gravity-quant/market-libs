---
phase: 03-iol-verification
plan: 01
subsystem: auth
tags: [oauth2, refresh-token, dual-sync-async, asyncio-lock, pytest-httpx, regression-tests]

# Dependency graph
requires:
  - phase: 02-mbito-verification
    provides: "Phase 2 driver + Regressions section convention; pytest-httpx match_content body discrimination pattern (Pitfall 5 mirror)"
  - phase: 01-safety-harness-verification-infrastructure
    provides: "verification.findings.append_finding helper, verification.schema.schema_of primitive, safe_print secrets gate (consumed by Plan 03-02 driver, not directly by 03-01)"
provides:
  - "iol_client.client._refresh_token: str | None module-level singleton (sync)"
  - "iol_client.client._refresh() private helper: POST /token with grant_type=refresh_token (sync)"
  - "iol_client.client._ensure_token() with refresh→password fallback (sync, D-IOL-10)"
  - "iol_client.aio._refresh_token: str | None module-level singleton (async mirror)"
  - "iol_client.aio._refresh_unlocked() private coroutine: caller must hold _token_lock (async, anti-deadlock Pitfall 6)"
  - "iol_client.aio._ensure_token() with double-checked locking preserved + refresh branch inside the same _token_lock"
  - "4 sync regression tests + 4 async mirror tests in `# ------ Regressions ------` section of test_client.py + test_async_client.py"
  - "Conditional refresh_token rotation pattern (Pitfall 3): only update _refresh_token if server returns a non-empty str"
affects: [03-02-PLAN, 03-03-PLAN, "Phase 4 higyrus (precedent for refresh-token pattern), Phase 5 matriz"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "OAuth2 refresh-token grant fallback to password grant (dual sync/async mirror)"
    - "asyncio.Lock-protected refresh-unlocked coroutine — caller-must-hold-lock contract documented inline (anti-deadlock Pitfall 6)"
    - "mypy strict narrowing via local variable copy + isinstance gate (Pitfall 4)"
    - "Conditional singleton rotation: update only on non-empty str (Pitfall 3)"
    - "pytest-httpx match_content=b\"...\" bytes-literal body discrimination for FIFO-bypass safety with 2 POSTs to same URL (Pitfall 5)"

key-files:
  created: []
  modified:
    - "packages/iol-client/src/iol_client/client.py (sync: _refresh_token global, _refresh() helper, _ensure_token fallback, login() captures refresh_token)"
    - "packages/iol-client/src/iol_client/aio.py (async mirror: _refresh_token global, _refresh_unlocked() coroutine inside _token_lock, double-checked locking preserved)"
    - "packages/iol-client/tests/test_client.py (added # ------ Regressions ------ section with 4 sync tests)"
    - "packages/iol-client/tests/test_async_client.py (added # ------ Regressions ------ section with 4 async mirror tests)"

key-decisions:
  - "Used ruff-suggested ternary `_refresh_token = new_refresh if isinstance(new_refresh, str) and new_refresh else None` instead of if/else block in login() — flake8-simplify SIM enforces ternary in this shape; semantics identical to PATTERNS.md sample"
  - "In _refresh() (sync) and _refresh_unlocked() (async), rotation is conditional: only update _refresh_token if server returns a new non-empty str — preserves existing cached refresh_token if server does not rotate (Pitfall 3). In login() the behavior is different: _refresh_token is RESET to None if server omits — login is the first/fresh capture point"
  - "Test 4 (test_login_captures_refresh_token) does NOT use match_content because the test only registers one POST /token mock — no need to discriminate. Tests 1/2/3 use match_content=b\"...\" because they register 2 mocks for the same URL"
  - "deferred-items.md logged: pre-existing `uv run mypy .` whole-repo failure on packages/higyrus-client/tests/conftest.py (not caused by IOL-07; out of scope for plan 03-01)"

patterns-established:
  - "OAuth refresh-token fallback in dual sync/async surface (template for higyrus-client and matriz-client when their refresh paths are added)"
  - "Pitfall 6 anti-deadlock idiom for asyncio.Lock-protected helpers: `_<verb>_unlocked` suffix + inline `# Caller must hold ..._lock` docstring + body uses only client.post directly (never _request / _ensure_token / re-entrant calls)"
  - "Regressions section convention (D-IOL-12 / D-07): docstring `Regression: IOL-NN — <behavior> (finding F-NN)` — F-NN to be backfilled when driver run in Plan 03-02 assigns concrete fids"

requirements-completed: [IOL-07]

# Metrics
duration: 5min
completed: 2026-06-06
---

# Phase 3 Plan 01: IOL-07 Refresh-Token Fix (Sync + Async + Regressions) Summary

**OAuth2 `grant_type=refresh_token` with fallback to password grant implemented in IOL client `client.py` + `aio.py` dual surfaces, plus 4+4 pytest-httpx regression tests locking the four code paths (login capture, refresh success, refresh→password fallback, both fail).**

## Performance

- **Duration:** ~5 min execution (3 atomic commits)
- **Started:** 2026-06-06T14:21:26Z (first task commit)
- **Completed:** 2026-06-06T14:26:18Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- Sync surface (`packages/iol-client/src/iol_client/client.py`):
  - New module-level singleton `_refresh_token: str | None = None`
  - `configure()` resets `_refresh_token` alongside `_token` (D-IOL-8)
  - `login()` captures `refresh_token` from OAuth payload with isinstance gate (D-IOL-9, Pitfall 3)
  - New private `_refresh()` helper: `POST /token` with `grant_type=refresh_token` body, reuses `_raise_for_response`, conditional rotation, mypy-strict local-copy narrowing (Pitfall 4)
  - `_ensure_token()` now tries `_refresh()` before falling back to `login()` (D-IOL-10)
- Async surface (`packages/iol-client/src/iol_client/aio.py`): semantically identical mirror
  - `_refresh_unlocked()` coroutine with docstring "Caller must hold `_token_lock`"
  - Anti-deadlock (Pitfall 6) verified by introspection: `_refresh_unlocked` body contains no `_request(`, `_ensure_token(`, or `_login_unlocked(` calls — only direct `await client.post(...)` via `_ensure_http_client()` (which uses the disjoint `_client_lock`)
  - `_ensure_token()` preserves double-checked locking; refresh branch added INSIDE the same `_token_lock` so the rollback to `_login_unlocked` does not require a second lock acquisition
- Regression tests (`packages/iol-client/tests/test_client.py` + `test_async_client.py`):
  - Section divider `# ------ Regressions ------` appended at end of each file
  - 4 sync tests + 4 async mirror tests (8 total)
  - All use pytest-httpx `match_content=b"..."` bytes-literal body discrimination so 2 POSTs to `/token` route to the right mock regardless of FIFO order (Pitfall 5)
- All gates pass on `packages/iol-client/*`: mypy strict (Success: no issues found in 7 source files), ruff check (All checks passed!), ruff format --check (7 files already formatted), pytest (22 passed). Whole-repo suite: 189 passed, 1 deselected.

## Task Commits

Each task was committed atomically:

1. **Task 1.1: Sync surface — `_refresh_token` + `_refresh()` + `_ensure_token` fallback in `client.py`** — `7e2f3aa` (feat)
2. **Task 1.2: Async surface — mirror `_refresh_token` + `_refresh_unlocked()` + `_ensure_token` fallback in `aio.py`** — `35b02ad` (feat)
3. **Task 1.3: `# ------ Regressions ------` section with 4+4 IOL-07 tests** — `1ad22b5` (test)

_Note: Pre-existing tests (9 sync + 5 async = 14) remain unmodified; new section appended at end of each file._

## Files Created/Modified

- `packages/iol-client/src/iol_client/client.py` — sync surface fix: `_refresh_token` global, `_refresh()` helper, `_ensure_token()` fallback, `login()` capture (+50 lines, -2)
- `packages/iol-client/src/iol_client/aio.py` — async mirror: `_refresh_token` global, `_refresh_unlocked()` coroutine, `_ensure_token()` refresh branch inside `_token_lock`, `_login_unlocked()` capture (+53 lines, -2)
- `packages/iol-client/tests/test_client.py` — appended `# ------ Regressions ------` section with 4 sync tests (+~130 lines)
- `packages/iol-client/tests/test_async_client.py` — appended `# ------ Regressions ------` section with 4 async mirror tests (+~120 lines)
- `.planning/phases/03-iol-verification/deferred-items.md` — created to log pre-existing whole-repo mypy issue (out of scope for plan 03-01)

## Decisions Made

- **Ternary form for ruff SIM compliance in `login()` refresh-token capture:** the plan's PATTERNS.md sample uses an `if/else` block to assign `_refresh_token`, but ruff SIM (flake8-simplify) flags it and demands the ternary `_refresh_token = new_refresh if isinstance(new_refresh, str) and new_refresh else None`. Semantics identical; chose ternary for ruff-clean output. This applies to `login()` only — in `_refresh()` / `_refresh_unlocked()` the conditional rotation uses `if isinstance(new_refresh, str) and new_refresh: _refresh_token = new_refresh` (NO else branch — preserves existing on no-rotation per Pitfall 3).
- **Rotation semantics differ between `login()` and `_refresh()`:** in `login()`, the captured `refresh_token` is the fresh anchor, so a missing/invalid value resets to `None` (driver Plan 03-02 detects and emits finding AUTH OPEN per D-IOL-9). In `_refresh()` / `_refresh_unlocked()`, the server may legitimately omit the refresh in a 200 response (no rotation), so the existing cached value is preserved (Pitfall 3 anti-pattern: "do not set `_refresh_token = None` after a successful refresh just because the server omitted it").
- **Test 4 (`test_login_captures_refresh_token`) does NOT use `match_content`:** only one POST /token mock is registered per test, so body discrimination is unnecessary. Tests 1/2/3 register TWO mocks (refresh + password) and require `match_content=b"refresh_token=..."` vs `match_content=b"username=..."` to discriminate (Pitfall 5).
- **`raising=False` on every `monkeypatch.setattr` in regression tests:** the autouse fixture preloads `_token = "test-token"` and `_token_expires_at = 9_999_999_999.0`, so `monkeypatch.setattr(iol_client.client, "_token", None)` would normally succeed. But `_refresh_token` starts as a module global with value `None`, and `monkeypatch.setattr` with default `raising=True` is conservative on missing attrs across test ordering; `raising=False` makes the tests robust to any autouse fixture changes.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] ruff SIM103 rejected the plan's `if/else` block for refresh_token capture in `login()`**
- **Found during:** Task 1.1 (sync surface — ruff format gate)
- **Issue:** PATTERNS.md sample used `if isinstance(new_refresh, str) and new_refresh: _refresh_token = new_refresh; else: _refresh_token = None` — ruff SIM (flake8-simplify) flags this with `if-else-block-instead-of-if-exp` and demands the ternary form. Without the fix, `uv run ruff check packages/iol-client/src/iol_client/client.py` exits with 1 error.
- **Fix:** Replaced with `_refresh_token = new_refresh if isinstance(new_refresh, str) and new_refresh else None` (semantically identical). Mirrored in `_login_unlocked()` of aio.py preventively.
- **Files modified:** `packages/iol-client/src/iol_client/client.py`, `packages/iol-client/src/iol_client/aio.py`
- **Verification:** ruff check + ruff format --check + mypy strict + pytest all pass.
- **Committed in:** `7e2f3aa` (Task 1.1), `35b02ad` (Task 1.2)

**2. [Rule 1 - Bug] ruff format reformatted `test_refresh_token_success_path` signature**
- **Found during:** Task 1.3 (test file format gate)
- **Issue:** I wrote the multi-line signature `def test_refresh_token_success_path(\n    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch\n) -> None:` — ruff format collapsed it to single-line because it fits within 100 chars. Pre-existing formatter behavior, not a semantic issue.
- **Fix:** Ran `uv run ruff format` to apply the reformat. No manual change required.
- **Files modified:** `packages/iol-client/tests/test_client.py`
- **Verification:** `uv run ruff format --check` exits 0 after the format.
- **Committed in:** `1ad22b5` (Task 1.3)

---

**Total deviations:** 2 auto-fixed (both ruff/format-driven — Rule 1 since ruff is the project linter and reflects correctness against the codified style guide)
**Impact on plan:** Both are stylistic — semantics unchanged. No scope creep; both required for ruff gate pass.

## Pitfalls Honored (verbatim verification)

- **Pitfall 3 (conditional rotation):** in `_refresh()` and `_refresh_unlocked()`, the rotation gate is `if isinstance(new_refresh, str) and new_refresh: _refresh_token = new_refresh` — no `else` branch. Verified by inspection.
- **Pitfall 4 (mypy strict narrowing):** local copy `refresh_token = _refresh_token` followed by `if not refresh_token: raise IOLAuthError(...)` then `data={"refresh_token": refresh_token, ...}` (local var, not the `_refresh_token: str | None` global). mypy passes strict on 7 source files.
- **Pitfall 5 (FIFO bypass via match_content):** all regression tests with 2 POSTs to `/token` use `match_content=b"..."` bytes literal: `b"refresh_token=...&grant_type=refresh_token"` (refresh) and `b"username=u&password=p&grant_type=password"` (password). Verified empirically that httpx serializes `data={...}` in dict insertion order with `&` separator (test 1: `refresh body: b'refresh_token=r1&grant_type=refresh_token'`).
- **Pitfall 6 (anti-deadlock in async refresh):** verified via `inspect.getsource(aio._refresh_unlocked)` that the body contains no `_request(`, `_ensure_token(`, or `_login_unlocked(` calls — only `await client.post(...)` directly. `_ensure_http_client` uses the disjoint `_client_lock`, not `_token_lock`.

## Test Counts

- `packages/iol-client/tests/test_client.py`: 13 sync tests (9 pre-existing + 4 new in Regressions). Target was 12 (8+4) but pre-existing count was 9, not 8 — both pass.
- `packages/iol-client/tests/test_async_client.py`: 9 async tests (5 pre-existing + 4 new). Target was 10 (6+4) but pre-existing count was 5, not 6 — both pass.
- Whole-package: 22 passed in 0.07s
- Whole-repo: 189 passed, 1 deselected in 0.47s

## Issues Encountered

- **Whole-repo `uv run mypy .` reports a pre-existing error on `packages/higyrus-client/tests/conftest.py`** (duplicate module / package-base mismatch). This is unrelated to IOL-07 and reproducible from main HEAD. Logged in `.planning/phases/03-iol-verification/deferred-items.md`. The per-package gate `uv run mypy packages/iol-client` (which is what plan 03-01 requires) passes cleanly.

## Self-Check: PASSED

All claimed files exist and all commits are reachable:

- `packages/iol-client/src/iol_client/client.py` — modified, `_refresh_token` global at L55, `_refresh()` at L92, `_ensure_token()` fallback at L131
- `packages/iol-client/src/iol_client/aio.py` — modified, `_refresh_token` global at L37, `_refresh_unlocked()` at L116, `_ensure_token()` fallback inside `_token_lock`
- `packages/iol-client/tests/test_client.py` — modified, `# ------ Regressions ------` divider + 4 tests appended after line 87
- `packages/iol-client/tests/test_async_client.py` — modified, `# ------ Regressions ------` divider + 4 tests appended after line 55
- `.planning/phases/03-iol-verification/deferred-items.md` — created
- Commits: `7e2f3aa` (Task 1.1), `35b02ad` (Task 1.2), `1ad22b5` (Task 1.3) — all present in `git log --oneline -3`

## Next Phase Readiness

- Plan 03-02 (driver rewrite of `main_iol.py` with 15 probes) can read `iol_client.client._refresh_token` / `iol_client.aio._refresh_token` directly per D-IOL-11; the singletons exist and reset on `configure()`.
- Plan 03-03 (Verified-live section + IOL-04 invariants) can extend the same test files (the `# ------ Regressions ------` divider is in place; a `# ------ Verified live (Phase 3) ------` divider would be appended BEFORE Regressions per D-IOL-21).
- No blockers introduced; safety harness untouched (Phase 1 lockedado preserved).
- Whole-repo suite passes (189 tests).

---
*Phase: 03-iol-verification*
*Plan: 01*
*Completed: 2026-06-06*
