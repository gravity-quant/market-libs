---
phase: 22-instruments-symbols-read-calendar-read-modelos
plan: 02
subsystem: api
tags: [market-data-client, reference-data, dual-parity, httpx, shims, pytest-httpx]

# Dependency graph
requires:
  - phase: 22-instruments-symbols-read-calendar-read-modelos
    plan: 01
    provides: 5 reference SafeModel dataclasses + 5 builders + 5 parsers in _core.py
  - phase: 20-scaffold-auth0-client-credentials-fundaciones-de-transporte
    provides: _request authenticated gating + Bearer injection + with_options retry cap
provides:
  - 5 sync Client methods (get_instruments/get_segments/get_symbols/get_calendar/get_calendar_config)
  - 5 async AsyncClient methods (await-only twins)
  - 10 module-level shims (5 sync + 5 async)
  - __init__ re-exports (5 sync shims + 5 model classes)
affects: [23-live-verification (reconciles provisional model shapes against real payloads)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Public method = strict 3-line dispatch: build spec via _core.build_* -> _request -> parse via _core.parse_* (D-08)"
    - "Dual sync/async parity: aio twin differs only by await (D-08); logic duplicated by design, builders/parsers shared from _core"
    - "Single-object return for calendar/config (D-07); the other four return list[Model]"

key-files:
  created:
    - packages/market-data-client/tests/test_reference_client.py
    - packages/market-data-client/tests/test_reference_async_client.py
  modified:
    - packages/market-data-client/src/market_data_client/client.py
    - packages/market-data-client/src/market_data_client/aio.py
    - packages/market-data-client/src/market_data_client/__init__.py

key-decisions:
  - "5 sync + 5 async reference methods each dispatch through the Plan 01 _core builders/parsers exactly as get_market_data does (D-08)"
  - "get_calendar_config returns a single CalendarConfig (D-07); the other four return list[Model]"
  - "Async shims live on aio and are NOT added to the package __all__ (mirrors existing get_market_data treatment — only sync shim re-exported)"

patterns-established:
  - "Pattern: reference public method = _core.build_<name>_request(self._state, **filters) -> resp = [await] self._request(spec) -> return _core.parse_<name>_response(resp)"
  - "Pattern: end-to-end param-encoding test asserts Bearer + httpx-native bool ('true'/'false') + falsy preserved (offset=0/active=False) + None dropped"

requirements-completed: [REF-MD-01]

# Metrics
duration: 3min
completed: 2026-07-30
status: complete
---

# Phase 22 Plan 02: Reference-data public sync/async surface Summary

**Five reference-read methods (`get_instruments`, `get_segments`, `get_symbols`, `get_calendar`, `get_calendar_config`) exposed on both `Client` and `AsyncClient` with matching module-level shims and `__init__` re-exports — each a strict 3-line dispatch through the Plan 01 `_core` builders/parsers, proven by mocked sync/async parity + param-encoding tests, all four CI gates green.**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-07-30T11:34:29Z
- **Completed:** 2026-07-30T11:37:51Z
- **Tasks:** 3
- **Files modified:** 5 (2 created, 3 modified)

## Accomplishments
- Added 5 sync methods to `Client` + 5 module-level sync shims in `client.py`, each a build→`_request`→parse triple mirroring `get_market_data` (D-08). `get_calendar_config` returns a single `CalendarConfig` (D-07); the other four return `list[Model]`.
- Added the exact `await`-only async twins (5 `AsyncClient` methods + 5 async shims) in `aio.py` with signature-for-signature parity (D-08 dual parity); builders/parsers shared from `_core`, only the dispatch surface duplicated per the no-shared-internals constraint.
- Re-exported the 5 sync shims + 5 model classes (`Instrument`, `Segment`, `Symbol`, `CalendarDay`, `CalendarConfig`) in `__init__.py`'s sorted `__all__`; async shims stay on `aio` (mirrors existing `get_market_data`).
- Wrote 10 end-to-end tests (5 sync + 5 async twins) proving Bearer injection, httpx-native bool encoding (`"true"`/`"false"`), falsy preservation (`offset=0`, `active=False` present in the query), `None` dropped, no-param endpoints, and the single-object calendar/config shape. Package suite grew 124 → 134 tests.
- `with_options(max_retries=N)` threads through these calls for free via the unchanged `_request` (verified by the existing suite staying green).

## Task Commits

1. **Task 1: Add 5 sync methods + 5 sync shims to client.py** - `b91c3de` (feat)
2. **Task 2: Add 5 async methods + 5 async shims to aio.py (dual parity)** - `9cee57a` (feat)
3. **Task 3: Re-export in __init__.py + sync/async parity tests + 4 CI gates** - `191a2ca` (feat)

## Files Created/Modified
- `packages/market-data-client/src/market_data_client/client.py` - Added 5 `Client` reference methods + 5 sync shims; expanded the `models` import.
- `packages/market-data-client/src/market_data_client/aio.py` - Added 5 `AsyncClient` reference methods + 5 async shims (await-only twins); expanded the `models` import.
- `packages/market-data-client/src/market_data_client/__init__.py` - Re-exported the 5 sync shims + 5 model classes in a sorted `__all__`.
- `packages/market-data-client/tests/test_reference_client.py` - Sync end-to-end Bearer + param-encoding tests for the 5 reference endpoints.
- `packages/market-data-client/tests/test_reference_async_client.py` - Async twins of every sync test (sync/async parity).

## Decisions Made
None beyond the locked context decisions (D-01..D-09). Executor discretion applied within plan bounds:
- Async shims intentionally excluded from the package `__all__`, matching the pre-existing `get_market_data` treatment (only the sync shim is flat-namespace re-exported; async lives under `aio`).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- The two new test files carried long inline JSON literals that exceeded the 100-char line; `ruff format` reflowed them into multi-line dict/list forms (applied only to the two new test files). All four gates green afterward.

## Known Stubs
None. Model field shapes remain PROVISIONAL (A1/A2 — OpenAPI not vendored) and are reconciled against real develop payloads in Phase 23; `from_api` tolerance bounds the blast radius. This is a documented cross-phase follow-up, not a stub blocking REF-MD-01.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- REF-MD-01 is complete: the consumer can read instruments, segments, symbols, calendar, and calendar/config as typed models in both sync and async, inheriting the `with_options` retry cap for free.
- Phase 23 (live verification) reconciles the provisional model shapes against real develop payloads.

## Self-Check: PASSED

All 5 created/modified files verified present on disk; all 3 task commits (`b91c3de`, `9cee57a`, `191a2ca`) verified in git history. Four CI gates (ruff check + ruff format --check + mypy strict + pytest 134 passed) all green for `packages/market-data-client`.

---
*Phase: 22-instruments-symbols-read-calendar-read-modelos*
*Completed: 2026-07-30*
