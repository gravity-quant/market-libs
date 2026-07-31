---
phase: 21-market-data-lectura-modelos
plan: 03
subsystem: api
tags: [market-data-client, with_options, retry-transport, auth0, httpx, tenacity, max_attempts]

# Dependency graph
requires:
  - phase: 21-02
    provides: "_core builders/parsers (build_market_data_request, build_latest_request, build_latest_batch_request, parse_market_data_response, parse_latest_response) + _params.drop_none"
  - phase: 21-01
    provides: "models (MarketDataSnapshot, MarketDataEntry, LatestRequest, SafeModel)"
  - phase: 20
    provides: "sync Client shell (_request/_send_auth_request/_ensure_token, RetryTransport, Auth0 client_credentials, D-09 header precedence)"
provides:
  - "Sync Client.with_options(max_retries=N) shared-view clone (shares _state; view close() is a no-op)"
  - "req.extensions['max_attempts']=self._max_retries+1 threaded into both _request and _send_auth_request (D-08 load-bearing)"
  - "Client.get_market_data / get_latest / get_latest_batch read methods + module-level shims"
  - "D-10 sync 401 regression tests (re-auth-once-then-succeed + persistent-401 re-raise, asserted by token-POST count)"
  - "Pitfall-1 retry-propagation-by-request-count regression test"
affects: [21-04, phase-23-live-verification]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "iol Phase-13 with_options shared-view-clone mirrored per-package (NOT imported — no-shared-internals constraint)"
    - "Per-call retry cap via request.extensions['max_attempts'] consumed by RetryTransport (_transport.py:169)"
    - "Read method 3-liner shape: build spec → self._request(spec) → _core.parse_*_response(resp)"

key-files:
  created:
    - packages/market-data-client/tests/test_with_options.py
  modified:
    - packages/market-data-client/src/market_data_client/client.py
    - packages/market-data-client/tests/test_client.py

key-decisions:
  - "with_options threads max_attempts uniformly in BOTH _request and _send_auth_request (auth-flow is idempotent=True, so the view cap applies to grants too) — matches iol"
  - "_validate_max_retries copied verbatim into client.py (no cross-package import) per no-shared-internals constraint"
  - "Module-level read shims added in client.py but NOT re-exported in __init__ (files_modified scoped to client.py + 2 test files; package-level export deferred to keep the plan's file scope intact)"
  - "Added get_latest / get_latest_batch smoke tests (Bearer + params/body) beyond the plan's get_market_data-only behavior spec — the three read methods ship together"

patterns-established:
  - "Retry-count asserted by COUNT of outgoing /marketdata requests (== max_retries+1), never by ordering (Pitfall 5)"
  - "401 re-auth asserted by COUNT of token POSTs (exactly one) to prove no infinite re-auth loop"

requirements-completed: [MD-01]

# Metrics
duration: 4min
completed: 2026-07-30
status: complete
---

# Phase 21 Plan 03: Sync with_options + market-data read methods Summary

**Sync `Client.with_options(max_retries=N)` is now a real shared-view clone whose per-call retry cap is threaded via `request.extensions["max_attempts"]`, plus the three authenticated read methods (`get_market_data`/`get_latest`/`get_latest_batch`) and permanent D-10 401 regression tests.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-07-30T02:14:08Z
- **Completed:** 2026-07-30T02:18:26Z
- **Tasks:** 3
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments
- `with_options(max_retries=N)` shared-view clone: shares `_state` (cached token + transport), view `close()` is a no-op, invalid input rejected with `ValueError` before construction.
- THE LOAD-BEARING STEP (D-08): `req.extensions["max_attempts"] = self._max_retries + 1` set in BOTH `_request` and `_send_auth_request` — the retry cap is now honored per-call (previously a silent no-op). Retry count verified by outgoing-request count (6 for `max_retries=5`, 1 for `max_retries=0`).
- Three authenticated read methods + module-level shims dispatching through `_core` builders/parsers, returning `list[MarketDataSnapshot]`.
- D-10 sync 401 regression tests: authenticated 401 → clear token → re-auth exactly once → retry → succeed, AND persistent-401 re-raise — both asserted by token-POST count (no infinite loop).
- `_DEFAULT_MAX_ATTEMPTS` module constant + its stale Phase-21-deferral comment removed.

## Task Commits

Each task was committed atomically (TDD RED → GREEN):

1. **Task 1: Write failing sync with_options + D-10 401 tests (RED)** - `83590af` (test)
2. **Task 2: with_options plumbing + max_attempts threading (GREEN)** - `fdc2cc0` (feat)
3. **Task 3: Sync read methods + module shims (GREEN)** - `bce4fb2` (feat)

## Files Created/Modified
- `packages/market-data-client/src/market_data_client/client.py` - `_validate_max_retries`, `__slots__` → `(_is_view, _max_retries, _state)`, `max_retries` `__init__` kwarg, `with_options`, view-aware `close()`, `max_attempts` threading in `_request` + `_send_auth_request`, `get_market_data`/`get_latest`/`get_latest_batch` methods + module shims; removed `_DEFAULT_MAX_ATTEMPTS`.
- `packages/market-data-client/tests/test_with_options.py` (created) - retry-count-by-request-count (Pitfall 1 regression), `max_retries=0` single request, shared-view + close no-op, ValueError on bad input.
- `packages/market-data-client/tests/test_client.py` - D-10 401 re-auth-once + persistent-401 re-raise (assert by token-POST count) + end-to-end Bearer/param/body serialization for the three read methods.

## Decisions Made
- Threaded `max_attempts` uniformly in both dispatch methods (auth-flow specs are `idempotent=True`, so a view's cap applies to grants too) — mirrors iol Phase-13.
- `_validate_max_retries` duplicated verbatim into `client.py` (no cross-package import) per the no-shared-internals constraint.
- Module-level read shims live in `client.py` but were NOT re-exported in `__init__.py`, honoring the plan's `files_modified` scope (client.py + the two test files). Package-level export of the read shims / models can be a follow-up; callers can reach them via `market_data_client.client.*` or the class methods today.

## Deviations from Plan

### Scope additions (Rule 2 - missing critical coverage)

**1. [Rule 2 - Missing Critical Coverage] Added get_latest / get_latest_batch smoke tests**
- **Found during:** Task 1 (RED test authoring)
- **Issue:** The plan's `<behavior>` block detailed only `get_market_data` end-to-end cases, but Task 3 ships all three read methods together; `get_latest` and `get_latest_batch` would otherwise land untested.
- **Fix:** Added `test_get_latest_sends_bearer_and_params` and `test_get_latest_batch_sends_bearer_and_body` (Bearer injection + query-param / JSON-body serialization).
- **Files modified:** packages/market-data-client/tests/test_client.py
- **Verification:** Both pass in the full package suite (85 passed).
- **Committed in:** `83590af` (Task 1 RED) / satisfied in `bce4fb2` (Task 3 GREEN)

---

**Total deviations:** 1 scope addition (test coverage for the two sibling read methods).
**Impact on plan:** Strengthens coverage of the read surface shipped by Task 3. No production-code scope creep; `files_modified` respected.

## Issues Encountered
- Task 2's dedicated with_options tests are 4 total; the 2 retry-count cases dispatch through `get_market_data`, which only exists after Task 3. During the Task 2 gate they failed on `AttributeError` (expected TDD ordering) — the with_options plumbing itself (shared-state, close no-op, ValueError) was green at Task 2, and all 4 turned green once Task 3 added the read methods. Full package suite: 85 passed.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Sync surface (`client.py`) is the D-09 header-precedence + with_options + read-methods reference that Plan 04 mirrors onto `aio.py` (async surface). All logic added here is clean and mirror-able.
- Gates green against the package path: pytest (85 passed), `ruff check`, `ruff format --check`, `mypy packages/market-data-client/src`.
- Open follow-up (non-blocking): package-level re-export of the read shims / model types in `__init__.py` if a flat public read API is desired.

---
*Phase: 21-market-data-lectura-modelos*
*Completed: 2026-07-30*

## Self-Check: PASSED

All created/modified files present on disk; all three task commits (`83590af`, `fdc2cc0`, `bce4fb2`) found in git history.
