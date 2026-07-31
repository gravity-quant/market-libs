---
phase: 21-market-data-lectura-modelos
plan: 02
subsystem: api
tags: [httpx, market-data, request-builders, response-parsers, safemodel, received-at, drop-none, tdd]

# Dependency graph
requires:
  - phase: 21-01
    provides: "MarketDataSnapshot.from_api(payload, *, received_at=...), MarketDataEntry, LatestRequest.to_dict(), SafeModel/_coerce"
  - phase: 20-scaffold-auth0-client-credentials
    provides: "RequestSpec dataclass, raise_for_response, build_health_request template, _ClientState, _core IO-free boundary"
provides:
  - "drop_none helper (_params.py) — package-local copy, drops None and preserves False/0/''"
  - "build_market_data_request / build_latest_request / build_latest_batch_request — RequestSpec(authenticated=True, idempotent=True)"
  - "parse_market_data_response / parse_latest_response — client-stamp received_at once per response, [] on null/empty body"
affects: [21-03, 21-04, 22-reference-data, 23-live-verification]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Package-local drop_none copy (no cross-package import) funnels optional GET filters"
    - "Read builders set authenticated=True (Bearer injection in Wave 3) + idempotent=True (retry-eligible reads incl. read-shaped batch POST)"
    - "Parser captures received_at = time.time() ONCE between resp.read() and raise_for_response, threaded into every snapshot (D-01)"
    - "Collection parsers guard both empty body (204) and JSON null → []"

key-files:
  created:
    - packages/market-data-client/src/market_data_client/_params.py
    - packages/market-data-client/tests/test_market_data.py
  modified:
    - packages/market-data-client/src/market_data_client/_core.py

key-decisions:
  - "drop_none copied verbatim from higyrus into a new _params.py; format_date/format_bool intentionally NOT copied (bool wire-encoding deferred to Phase 23, D-07)"
  - "parse_latest_response returns list[MarketDataSnapshot] (provisional) — batch POST naturally returns many symbols; single-symbol GET shape reconciled in Phase 23, absorbed by from_api tolerance"
  - "build_latest_batch_request marks idempotent=True — a read expressed as POST is replay-safe (mirrors build_token_request)"

patterns-established:
  - "one-stamp-per-response received_at fidelity (D-01/D-02): the client owns the wall-clock stamp; live reconciliation deferred to Phase 23"
  - "params or None: an empty drop_none dict collapses to params=None so anonymous GETs carry no query string"

requirements-completed: [MD-01]

# Metrics
duration: 2min
completed: 2026-07-30
status: complete
---

# Phase 21 Plan 02: Market-data read builders + parsers Summary

**Three `RequestSpec(authenticated=True, idempotent=True)` read builders plus two received_at-stamping list parsers on the IO-free `_core` layer, backed by a package-local `drop_none` copy.**

## Performance

- **Duration:** 2 min
- **Started:** 2026-07-30T02:05:09Z
- **Completed:** 2026-07-30T02:07Z
- **Tasks:** 2 (TDD RED + GREEN)
- **Files modified:** 3 (2 created, 1 modified)

## Accomplishments
- `_params.drop_none` — package-local copy of higyrus's helper (no cross-package import); drops only `None`, preserves `False`/`0`/`""`.
- Three pure builders (`build_market_data_request`, `build_latest_request`, `build_latest_batch_request`) each returning `RequestSpec(authenticated=True, idempotent=True)` — GET `/marketdata`, GET `/marketdata/latest`, POST `/marketdata/latest` (batch body from `LatestRequest.to_dict()`).
- Two parsers (`parse_market_data_response`, `parse_latest_response`) that stamp `received_at = time.time()` exactly once per response (between `resp.read()` and `raise_for_response`) and thread it into every `MarketDataSnapshot`; return `[]` on null/empty body; delegate status mapping to `raise_for_response`.
- Import boundary preserved: `_core` imports only in-package `_params` + `models`, nothing from `client`/`aio`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Write failing builder + parser tests (RED)** - `21ee861` (test)
2. **Task 2: Create _params.py drop_none + add _core.py builders and parsers (GREEN)** - `e648c44` (feat)

_TDD gate: `test(...)` RED commit precedes the `feat(...)` GREEN commit._

## Files Created/Modified
- `packages/market-data-client/src/market_data_client/_params.py` - New; `drop_none` only (D-07).
- `packages/market-data-client/src/market_data_client/_core.py` - Added 3 builders + 2 parsers; imports `_params` + `models`; `__all__` extended and re-sorted.
- `packages/market-data-client/tests/test_market_data.py` - New; 11 pure unit tests covering drop_none, builder shape/flags/param-drop, batch body serialization, and the one-stamp received_at invariant + null/empty-body guard.

## Decisions Made
- **`parse_latest_response` returns a list** (provisional): the batch POST returns multiple symbols, so a list is the common shape for both the single-symbol GET and the batch; `from_api` tolerance absorbs a Phase-23 correction to a single-snapshot GET shape if confirmed.
- **`drop_none` copied, not shared**: honors the no-shared-internals CLAUDE.md constraint; `format_date`/`format_bool` deliberately omitted (bool wire-encoding deferred to Phase 23).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Empty-body (204) guard added to both collection parsers**
- **Found during:** Task 2 (GREEN)
- **Issue:** The plan's `if raw is None: return []` guard handles a JSON `null` body but NOT an empty/204 body — `resp.json()` on empty content raises `JSONDecodeError`. The plan `must_haves` require `[]` on a "null/empty body".
- **Fix:** Added `if not resp.content: return []` before `resp.json()` in both `parse_market_data_response` and `parse_latest_response`; adjusted the null-body tests to exercise a real JSON `null` body (`content=b"null"`) plus a 204 empty body.
- **Files modified:** `_core.py`, `tests/test_market_data.py`
- **Verification:** `test_parse_market_data_response_null_body_returns_empty` and `test_parse_latest_response_null_body_returns_empty` green.
- **Committed in:** `e648c44` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** The guard is required to satisfy the plan's own "null/empty body → []" must_have. No scope creep.

## Issues Encountered
- `httpx.Response(json=None)` produces an empty body rather than a JSON `null` document, so the initial null-body tests hit `JSONDecodeError`. Resolved by testing with `content=b"null"` (true JSON null) and adding the empty-body guard above.

## TDD Gate Compliance
- RED: `21ee861` `test(21-02): ...` — module failed at collection (`ModuleNotFoundError: market_data_client._params`).
- GREEN: `e648c44` `feat(21-02): ...` — 11/11 target tests pass; full package suite 76/76.
- No REFACTOR commit needed.

## Verification
- `uv run --package market-data-client pytest packages/market-data-client -q` → 76 passed.
- `uv run mypy packages/market-data-client/src` → Success, no issues (11 source files).
- `uv run ruff check packages/market-data-client` → All checks passed.
- `uv run ruff format --check packages/market-data-client` → 21 files already formatted.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- The IO-free read surface is ready for the Wave-3 transport shells (Plans 03/04) to dispatch: shells inject the Bearer when `spec.authenticated=True` and set `extensions["max_attempts"]` for the `idempotent=True` retry gate.
- Response field names and `parse_latest_response`'s list-vs-single shape remain PROVISIONAL — reconciled against real develop payloads in Phase 23 (bounded by `from_api` tolerance).

## Self-Check: PASSED
- FOUND: `packages/market-data-client/src/market_data_client/_params.py`
- FOUND: `packages/market-data-client/src/market_data_client/_core.py`
- FOUND: `packages/market-data-client/tests/test_market_data.py`
- FOUND commit: `21ee861` (RED)
- FOUND commit: `e648c44` (GREEN)

---
*Phase: 21-market-data-lectura-modelos*
*Completed: 2026-07-30*
