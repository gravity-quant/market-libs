---
phase: 25-mutating-gate-symbols-write
plan: 02
subsystem: api
tags: [market-data-client, request-models, serialization, dataclass, python, tdd]

# Dependency graph
requires:
  - phase: 21-market-data-models-core
    provides: LatestRequest serialize-OUT to_dict() template + SafeModel base (contrast)
  - phase: 20-market-data-core-transport
    provides: RequestSpec dataclass + build_latest_batch_request POST builder template
provides:
  - "NewSymbol / NewSymbols / SymbolPatch frozen serialize-OUT request models with to_dict()"
  - "NewSymbols.__post_init__ client-side 1-500 plain-ValueError batch guard (D-11)"
  - "build_create_symbol_request / build_create_symbols_request / build_update_symbol_request pure _core builders (idempotent=True, authenticated=True)"
affects: [25-03, symbols-write-dispatch, phase-27-live-reconciliation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Serialize-OUT request model: frozen slotted @dataclass (NOT SafeModel) + hand-written to_dict()"
    - "Client-side validation via __post_init__ raising plain ValueError on a frozen dataclass (read-only, no object.__setattr__)"
    - "Pure POST/PATCH _core builder: del state, json_body = model.to_dict(), no gate/IO"

key-files:
  created: []
  modified:
    - packages/market-data-client/src/market_data_client/models.py
    - packages/market-data-client/src/market_data_client/_core.py
    - packages/market-data-client/tests/test_models.py
    - packages/market-data-client/tests/test_core.py

key-decisions:
  - "market_id emitted as snake_case wire key (NOT camelCase marketId) per source-plan schema — intentionally divergent from LatestRequest; confirmed live in Phase 27 (A2)"
  - "Batch 1-500 guard raises plain ValueError, never a MarketData* error (that hierarchy is reserved for server contract errors, D-11)"
  - "All three symbols builders idempotent=True per DM-03 (retry-safe; revalidated live in Phase 27, may flip to False)"
  - "symbol_id interpolated RAW into PATCH path — percent-encoding for ids with '/' deferred to Phase 27 (D-08 / Pitfall 4)"

patterns-established:
  - "Serialize-OUT request models mirror LatestRequest (frozen slotted, to_dict, not SafeModel)"
  - "Pure symbols write builders mirror build_latest_batch_request (del state, idempotent=True, authenticated=True)"

requirements-completed: [MUT-MD-01]

# Metrics
duration: 4min
completed: 2026-07-31
status: complete
---

# Phase 25 Plan 02: Symbols request-models + _core builders Summary

**Three frozen serialize-OUT request models (NewSymbol/NewSymbols/SymbolPatch with snake_case market_id and a client-side 1-500 ValueError guard) plus three pure POST/PATCH `_core` builders (idempotent=True, authenticated=True) — the IO-free MUT-MD-01 foundation Plan 03 wires together.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-07-31T20:28:32Z
- **Completed:** 2026-07-31T20:32:18Z
- **Tasks:** 2 (both TDD)
- **Files modified:** 4

## Accomplishments
- `NewSymbol`, `NewSymbols`, `SymbolPatch` — frozen slotted request models (NOT SafeModel) with hand-written `to_dict()`; `NewSymbol` always emits snake_case `market_id` (default `"ROFX"`).
- `NewSymbols.__post_init__` enforces the 1-500 batch bound with a plain `ValueError` before any dispatch (T-25-07 mitigation).
- `build_create_symbol_request` (POST `/symbols`), `build_create_symbols_request` (POST `/symbols/batch`), `build_update_symbol_request` (PATCH `/symbols/{id}`) — pure, state-independent, `idempotent=True` + `authenticated=True`, no gate/IO.
- `__all__` updated in both `models.py` and `_core.py`; unit tests for serialization, batch bounds, builder specs, and state-independence.

## Task Commits

Each task was committed atomically (TDD RED folded into each task's GREEN commit as tests+impl landed together after the RED run):

1. **Task 1: Three frozen request models with to_dict() + NewSymbols 1-500 ValueError** - `e24e501` (feat)
2. **Task 2: Three pure _core builders for the symbols write endpoints** - `f639283` (feat)

**Plan metadata:** (this SUMMARY + STATE/ROADMAP commit)

_Note: RED was run and confirmed failing before each implementation (ImportError for models; 4 AttributeError failures for builders), then GREEN implemented and committed._

## Files Created/Modified
- `packages/market-data-client/src/market_data_client/models.py` - Added NewSymbol, NewSymbols, SymbolPatch serialize-OUT models + `__all__` entries.
- `packages/market-data-client/src/market_data_client/_core.py` - Added three pure symbols write builders + `__all__` entries.
- `packages/market-data-client/tests/test_models.py` - to_dict serialization tests + NewSymbols 1/500 bounds + ValueError cases.
- `packages/market-data-client/tests/test_core.py` - 4 builder tests (method/path/json_body/idempotent/authenticated + state-independence).

## Decisions Made
- **snake_case `market_id`:** `NewSymbol.to_dict()` emits `market_id` (not camelCase `marketId`) per the source-plan schema — deliberately different from `LatestRequest`; test asserts `"marketId" not in out` (T-25-08 partial mitigation). Real key confirmed live in Phase 27 (A2).
- **Plain ValueError for batch bounds:** the 1-500 guard raises a bare `ValueError` in `__post_init__`, not a `MarketData*` error, per D-11 (the typed hierarchy is reserved for server contract errors).
- **idempotent=True (DM-03):** all three builders mark the writes retry-safe; revalidated live in Phase 27 (A3), flips to False there if a retried POST duplicates state.
- **Raw symbol_id in PATCH path (D-08):** percent-encoding for ids containing `/` (e.g. `"DLR/DIC26"`) is explicitly deferred to Phase 27.

## Deviations from Plan

None - plan executed exactly as written. Two minor tool-driven adjustments during the same task commits (not scope changes):
- Added `match="1-500"` to the two `pytest.raises(ValueError, ...)` calls to satisfy ruff PT011 (too-broad raises).
- Replaced two EN-DASH characters ("1–500") with ASCII hyphens in `models.py` docstrings to satisfy ruff RUF002.

## Issues Encountered
- **Pre-existing full-suite mypy errors (out of scope):** `uv run mypy packages/market-data-client` reports 9 strict-mode errors in test files NOT touched by this plan — 8 in `tests/test_mutation_gate.py` (Plan 25-01, `_ensure_mutation_allowed() does not return a value`) and 1 in `tests/test_reference_core.py:208` (prior phase). The pre-commit mypy hook only scans `^packages/.*/src/`, so these do NOT block commits, and this plan's own source (`models.py`, `_core.py`) is mypy-clean. Logged to `deferred-items.md`; left unfixed per the executor scope boundary.

## User Setup Required
None - no external service configuration required (pure additive dataclass/builder code, no package installs).

## Next Phase Readiness
- MUT-MD-01 pure foundation complete: request models + builders ready for Plan 25-03 to wire into the gated dispatch methods on both shells (`client.py` / `aio.py`).
- Live reconciliation flags carried forward to Phase 27: A2 (snake_case `market_id` wire key), A3 (idempotency of the write endpoints), D-08 (percent-encoding of `/`-bearing symbol ids in the PATCH path).

## Verification
- `uv run --package market-data-client pytest packages/market-data-client/tests -q` → 166 passed.
- `uv run ruff check packages/market-data-client` → All checks passed.
- `uv run ruff format --check packages/market-data-client` → 28 files already formatted.
- `uv run mypy` on the two produced source files → clean (pre-commit src-scope hook green on both commits).
- Grep guard: `class NewSymbol` / `class NewSymbols` / `class SymbolPatch` are plain classes — none subclass SafeModel.

## Self-Check: PASSED
- Files modified exist: models.py, _core.py, test_models.py, test_core.py (all FOUND).
- Commits exist: e24e501, f639283 (both FOUND in git log).

---
*Phase: 25-mutating-gate-symbols-write*
*Completed: 2026-07-31*
