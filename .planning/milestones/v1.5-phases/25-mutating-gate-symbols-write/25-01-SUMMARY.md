---
phase: 25-mutating-gate-symbols-write
plan: 01
subsystem: security
tags: [mutation-gate, market-data-client, python, httpx, auth0, urlsplit]

# Dependency graph
requires:
  - phase: 20-24 (market-data-client read surface)
    provides: "_ClientState (slots), Client/AsyncClient shells, configure() carry-forward, with_options shared-state views, MarketDataError hierarchy"
provides:
  - "MarketDataMutationNotAllowedError(MarketDataError) — client-side policy refusal, no status_code"
  - "_ClientState.mutating_allowed (refuse-by-default) + expected_host (+ _DEFAULT_EXPECTED_HOST)"
  - "IO-free _ensure_mutation_allowed() gate on Client and AsyncClient (exact-host, zero HTTP/Auth0)"
  - "mutating_allowed/expected_host bool|None sentinel params on __init__ + configure (both shells)"
  - "conftest teardown reset of the gate singleton fields"
affects: [25-02, 25-03, 26-mutating-gate-calendar, 27-live-verification]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Load-bearing gate: IO-free pure state read raised as FIRST statement of a mutation method"
    - "Exact-hostname match via urllib.parse.urlsplit(base_url).hostname == expected_host (never substring/endswith)"
    - "bool|None sentinel carry-forward so configure(base_url=...) cannot silently reset a prior opt-in"

key-files:
  created:
    - packages/market-data-client/tests/test_mutation_gate.py
  modified:
    - packages/market-data-client/src/market_data_client/exceptions.py
    - packages/market-data-client/src/market_data_client/_state.py
    - packages/market-data-client/src/market_data_client/client.py
    - packages/market-data-client/src/market_data_client/aio.py
    - packages/market-data-client/src/market_data_client/__init__.py
    - packages/market-data-client/tests/conftest.py

key-decisions:
  - "MarketDataMutationNotAllowedError subclasses MarketDataError directly (client-side refusal, no status_code) per D-16/A6"
  - "expected_host FIELD defaults to _DEFAULT_EXPECTED_HOST (develop host); a field value of None disables ONLY the host leg (helper: `if expected is not None`)"
  - "Constructor/configure use bool|None=None + str|None=None sentinels applied under `if x is not None:`; gate params never set the token-invalidating `rotated` flag"
  - "expected_host=None host-leg-disable is reachable only by direct _state assignment (the None sentinel means 'no change' in constructor/configure) — tested at helper level"

patterns-established:
  - "Gate helper: refuse-by-default flag leg THEN exact-host leg, both raising MarketDataMutationNotAllowedError, zero IO"
  - "Gate fields live only on shared _ClientState so with_options views inherit gate state with zero extra code (D-14)"

requirements-completed: [GATE-MD-01]

# Metrics
duration: ~10min
completed: 2026-07-31
status: complete
---

# Phase 25 Plan 01: Mutating-gate (GATE-MD-01) Summary

**IO-free, exact-hostname, refuse-by-default mutation gate on both market-data-client shells — raises MarketDataMutationNotAllowedError with zero HTTP and zero Auth0 round-trip, propagates to with_options views via shared _ClientState, and cannot be silently reset by a configure() that omits the flag.**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-07-31T17:16:00-03:00
- **Completed:** 2026-07-31T17:25:19-03:00
- **Tasks:** 3
- **Files modified:** 6 (1 created, 5 modified) + 1 test file created

## Accomplishments
- Added `MarketDataMutationNotAllowedError(MarketDataError)` (no status_code) + an `__all__` to `exceptions.py`, re-exported through `__init__.py`.
- Added `mutating_allowed` (refuse-by-default) and `expected_host` gate fields plus `_DEFAULT_EXPECTED_HOST` to `_ClientState` — living only on the shared state so views inherit the gate for free.
- Implemented the `_ensure_mutation_allowed()` helper identically on `Client` and `AsyncClient`: a pure state read (no `await`, no IO) with a flag leg and an exact-hostname leg (`urlsplit(...).hostname !=`, never substring/`endswith`).
- Wired `bool|None`/`str|None` sentinel opt-in params into both `__init__`s and both `configure()`s without setting the token-invalidating `rotated` flag.
- Extended both conftest teardowns to reset the new singleton gate fields (Pitfall 6), and added 14 adversarial helper tests (sync + async) including the `...bbsa.com.ar.attacker.example` superstring rejection.

## Task Commits

Each task committed atomically (hooks ran, no `--no-verify`):

1. **Task 1: refusal error + _ClientState gate fields** - `6fdb6e6` (feat)
2. **Task 2 (TDD RED): failing adversarial gate tests** - `43c4866` (test)
3. **Task 2 (TDD GREEN): IO-free exact-host gate on both shells** - `4079cf8` (feat)
4. **Task 3: conftest gate-field reset** - `3778963` (test)

_TDD: Task 2 followed RED (`43c4866`, 14 failing) → GREEN (`4079cf8`, 14 passing). No refactor commit needed._

## Files Created/Modified
- `packages/market-data-client/src/market_data_client/exceptions.py` - New `MarketDataMutationNotAllowedError` + module `__all__`.
- `packages/market-data-client/src/market_data_client/_state.py` - `_DEFAULT_EXPECTED_HOST` constant + `mutating_allowed`/`expected_host` fields on `_ClientState`.
- `packages/market-data-client/src/market_data_client/client.py` - Sync `_ensure_mutation_allowed()`, gate params on `__init__` + `configure()`.
- `packages/market-data-client/src/market_data_client/aio.py` - Async mirror (identical helper, params).
- `packages/market-data-client/src/market_data_client/__init__.py` - Re-export the new exception in `__all__`.
- `packages/market-data-client/tests/conftest.py` - Teardown reset of the gate singleton fields (sync + async).
- `packages/market-data-client/tests/test_mutation_gate.py` - 14 helper-level adversarial tests (created).

## Decisions Made
- **`expected_host=None` semantics:** The plan's helper (`if expected is not None`) treats a `_ClientState.expected_host` of `None` as "host leg disabled", while the FIELD default is the concrete develop host and the constructor/configure `None` is the "no change" sentinel. Consequence: the disable-only-host-leg path is reachable only via direct `_state.expected_host = None`, so the corresponding test sets the field directly (helper-level). This satisfies both the plan's behavior (e) and the D-13 spirit that a default/fresh client always enforces the develop host.

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
- **Pre-existing mypy error (out of scope):** `packages/market-data-client/tests/test_reference_core.py:208` reports `Need type annotation for "body" [var-annotated]`. Confirmed present on HEAD `57cb64e` before any Phase 25 work (via `git stash`). It is a test file, so the pre-commit mypy hook (`^packages/.*/src/`) does not touch it and commits pass; only the full-suite `uv run mypy packages/market-data-client` surfaces it. Logged to `deferred-items.md`, not fixed (unrelated to the gate). `uv run mypy packages/market-data-client/src` exits 0.

## Verification
- `uv run --package market-data-client pytest packages/market-data-client/tests -q` → **153 passed** (incl. 14 new gate tests); order-independent across two runs.
- `uv run ruff check packages/market-data-client` → All checks passed.
- `uv run ruff format --check packages/market-data-client` → 28 files already formatted.
- `uv run mypy packages/market-data-client/src` → Success, no issues in 11 source files.
- Grep guard: gate logic uses only `!=` exact comparison on `urlsplit(...).hostname`; `endswith`/substring appear only in docstrings describing what NOT to do.

## Known Stubs
None - the gate is fully wired. It is intentionally not yet CALLED by any mutation method (no mutation surface exists in this plan); Plan 03 inserts `_ensure_mutation_allowed()` as the first statement of each symbols mutation method, and the end-to-end zero-request-on-refusal proof through `create_symbol` lands there.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- The gate mechanics (refuse-by-default, exact-host, zero-IO, sentinel carry-forward, view inheritance) are complete and adversarially tested — GATE-MD-01 satisfied at the mechanism level.
- Plan 25-02 (request models `NewSymbol`/`NewSymbols`/`SymbolPatch` + `_core` builders) and Plan 25-03 (symbols mutation methods that call `_ensure_mutation_allowed()` first) can proceed. The end-to-end zero-HTTP/zero-Auth0 refusal-through-`create_symbol` proof is a Plan 03 deliverable.

## Self-Check: PASSED

- Created files verified on disk: `test_mutation_gate.py`, `exceptions.py`, `25-01-SUMMARY.md`.
- Task commits verified in git log: `6fdb6e6`, `43c4866`, `4079cf8`, `3778963`.

---
*Phase: 25-mutating-gate-symbols-write*
*Completed: 2026-07-31*
