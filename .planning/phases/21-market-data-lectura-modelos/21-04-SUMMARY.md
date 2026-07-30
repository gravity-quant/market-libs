---
phase: 21-market-data-lectura-modelos
plan: 04
subsystem: api
tags: [httpx, async, asyncio, auth0, tenacity, market-data, with_options]

# Dependency graph
requires:
  - phase: 21-market-data-lectura-modelos (Plan 03)
    provides: sync with_options shared-view clone, market-data read methods, _core builders/parsers, LatestRequest/MarketDataSnapshot/MarketDataEntry models
provides:
  - "aio.AsyncClient.with_options(max_retries=N) shared-view clone (retry count verified by request count)"
  - "aio.AsyncClient.get_market_data / get_latest / get_latest_batch async reads returning SafeModel results"
  - "async module-level shims: aio.get_market_data / aio.get_latest / aio.get_latest_batch"
  - "D-09 async header fix: authenticated Authorization token always wins over spec.headers"
  - "D-10 async 401 re-auth (exactly-once) + persistent-401 re-raise, asserted by token-POST count"
  - "__init__ re-exports: MarketDataSnapshot/MarketDataEntry/LatestRequest + sync read methods"
affects: [phase-23-wire-contract-reconciliation, market-data-client-consumers]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Dual sync/async parity: every Plan-03 sync logic change mirrored onto aio.py (CLAUDE.md constraint)"
    - "with_options shared-view clone on the async surface (view shares _state incl. per-loop asyncio.Locks; aclose() no-op)"
    - "max_attempts threading via req.extensions in BOTH _request and _send_auth_request (load-bearing for with_options)"
    - "Header precedence: authenticated Authorization token spread LAST so it always wins (D-09)"

key-files:
  created:
    - packages/market-data-client/tests/test_with_options_async.py
  modified:
    - packages/market-data-client/src/market_data_client/aio.py
    - packages/market-data-client/src/market_data_client/__init__.py
    - packages/market-data-client/tests/test_async_client.py

key-decisions:
  - "Committed the async with_options plumbing (Task 2) separately from the async read methods (Task 3); the retry-count tests require the async get_market_data method, so they turn green at Task 3 while Task 2's grep-level acceptance criteria (slots, D-09 header order, max_attempts x2, _DEFAULT_MAX_ATTEMPTS removed) are fully satisfied."
  - "Neutralized the inter-attempt backoff in the async retry-count test by patching _atransport._retry_after_or_jitter_wait -> tenacity.wait.wait_none (awaited sleep becomes asyncio.sleep(0)); the retry COUNT under test is unaffected. Chosen over patching tenacity internals (_portable_async_sleep) for robustness."
  - "_validate_max_retries duplicated module-level in aio.py (no cross-module import) per the no-shared-internals project constraint."

patterns-established:
  - "Async shared-view clone: type(self).__new__ + share _state + override _max_retries + _is_view flag; aclose() short-circuits for views."
  - "Async header-precedence regression test: dispatch an authenticated RequestSpec with a decoy Authorization and assert the sent header equals the fresh token."

requirements-completed: [MD-01]

# Metrics
duration: 4min
completed: 2026-07-30
status: complete
---

# Phase 21 Plan 04: Async with_options + D-09 header fix + async read methods Summary

**Mirrored the Plan-03 sync surface onto `aio.AsyncClient` — shared-view `with_options` clone with per-call `max_attempts` threading, the D-09 token-wins header reorder, three async market-data read methods + shims, and `__init__` re-exports — completing dual sync/async parity for MD-01.**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-07-30T02:22:49Z
- **Completed:** 2026-07-30T02:26:51Z
- **Tasks:** 3
- **Files modified:** 4 (1 created, 3 modified)

## Accomplishments
- Async `with_options(max_retries=N)` is a real shared-view clone: the view shares the parent `_state` (cached token, `httpx.AsyncClient`, and the per-loop `asyncio.Lock`s), `aclose()` is a view no-op, and the per-call cap is threaded via `req.extensions["max_attempts"]` in BOTH `_request` and `_send_auth_request` — proven by request-count (`max_retries=5` → 6 outgoing `/marketdata` requests; `max_retries=0` → 1).
- D-09 fix applied on the async surface: the authenticated header build now spreads `spec.headers` FIRST and the `Authorization` token LAST, so a decoy `spec.headers["Authorization"]` can never shadow the fresh token (regression-tested; sync and async now agree).
- Three async read methods (`get_market_data`, `get_latest`, `get_latest_batch`) + matching async module-level shims dispatch authenticated reads and return `SafeModel` results.
- D-10 async 401 sequences: authenticated 401 → re-auth exactly once → retry → succeed, and persistent-401 re-raises — both asserted by token-POST count.
- `__init__.py` re-exports `MarketDataSnapshot` / `MarketDataEntry` / `LatestRequest` and the sync read methods; `__all__` kept alpha-sorted.

## Task Commits

Each task was committed atomically (TDD RED → GREEN):

1. **Task 1: Failing async with_options + D-10 401 + D-09 header tests (RED)** - `0456981` (test)
2. **Task 2: with_options plumbing + D-09 fix + max_attempts threading in aio.py (GREEN)** - `d6e3c50` (feat)
3. **Task 3: Async read methods + async shims + __init__ re-exports (GREEN)** - `2501291` (feat)

_Note: Task 2 is the GREEN for the with_options plumbing; the retry-count tests (which call the async `get_market_data`) turn green at Task 3._

## Files Created/Modified
- `packages/market-data-client/tests/test_with_options_async.py` - Async `with_options` retry-count-by-request-count test + shared-view `aclose()` no-op + `ValueError` validation; autouse fixture neutralizes backoff via `wait_none`.
- `packages/market-data-client/src/market_data_client/aio.py` - Added module-level `_validate_max_retries`; `__slots__` → `(_is_view, _max_retries, _state)`; `max_retries` `__init__` kwarg (validate-first); `with_options` shared-view clone; view-aware `aclose()` no-op; `AsyncRetryTransport(max_attempts=self._max_retries+1)` (removed `_DEFAULT_MAX_ATTEMPTS`); `max_attempts` threading in both dispatch methods; D-09 header reorder; three async read methods + three async shims.
- `packages/market-data-client/src/market_data_client/__init__.py` - Re-export models (`MarketDataSnapshot`/`MarketDataEntry`/`LatestRequest`) + sync read methods (`get_market_data`/`get_latest`/`get_latest_batch`); `__all__` alpha-sorted.
- `packages/market-data-client/tests/test_async_client.py` - Added D-10 async 401 sequences (by count), D-09 decoy-header precedence, and end-to-end async read serialization (Bearer + param drop/bool encoding + batch body).

## Decisions Made
See `key-decisions` in frontmatter. In short: split the plumbing (Task 2) from the read methods (Task 3) so the retry-count tests go green when their dependency (`get_market_data`) lands at Task 3; neutralized async backoff with `wait_none` for a deterministic, fast retry-count assertion; duplicated `_validate_max_retries` per the no-shared-internals constraint.

## Deviations from Plan

None - plan executed exactly as written. No deviation rules (1-4) were triggered; no auth gates; no new dependencies.

## Issues Encountered
- **Task 2 verify sequencing:** the plan's Task 2 automated verify (`pytest test_with_options_async.py -q` exit 0) cannot fully pass in isolation because the two retry-count tests exercise the async `get_market_data` method that is introduced in Task 3. Resolved by committing the plumbing at Task 2 (its grep-level acceptance criteria are fully met and the shared-view / validation tests pass) and achieving full green at Task 3 — the standard TDD progression for this plan. No code change was needed to work around it.

## User Setup Required
None - no external service configuration required.

## Verification
- `uv run --package market-data-client pytest packages/market-data-client -q` → **95 passed** (full suite: sync + async, with_options both surfaces, D-09, D-10 both surfaces).
- `uv run ruff check packages/market-data-client` → All checks passed.
- `uv run ruff format --check packages/market-data-client` → 23 files already formatted.
- `uv run mypy packages/market-data-client/src` → Success: no issues found in 11 source files.
- `import market_data_client` resolves `MarketDataSnapshot`, `MarketDataEntry`, `LatestRequest`, and the sync + async read surfaces.

## Threat Model
- **T-21-04-01 (Spoofing/Elevation — mitigated):** async header build reordered so the token always wins; regression test asserts the sent `Authorization` equals the fresh token even with a decoy spec header.
- **T-21-04-02 (DoS — mitigated):** `_validate_max_retries` bounds N; `max_attempts=N+1` gated on idempotent specs; exactly-once re-auth under the token lock.
- **T-21-04-03 (Info Disclosure — mitigated):** no raw-header/token log statements added; existing redaction preserved.
- No new security surface introduced (reuses existing `_core` builders/parsers; zero new dependencies).

## Next Phase Readiness
- Dual sync/async parity for MD-01 is complete; both surfaces expose `with_options`, the three read methods, and identical D-09/D-10 semantics.
- Phase 21 (all four plans) is done. Wire field names remain PROVISIONAL (A1/A2) — Phase 23 reconciles model shapes against real payloads; `SafeModel.from_api` tolerance bounds the blast radius until then.

---
*Phase: 21-market-data-lectura-modelos*
*Completed: 2026-07-30*
