---
phase: quick-260731-jim
plan: 01
subsystem: market-data-client
tags: [reconciliation, safemodel, wire-fidelity, LIVE-MD-01]
status: complete
requires:
  - .planning/verification/schemas/market-data-client/get-market-data.json
  - .planning/verification/schemas/market-data-client/get-latest.json
  - .planning/verification/schemas/market-data-client/get-calendar-config.json
provides:
  - Reconciled MarketDataSnapshot (real /marketdata + /marketdata/latest wire)
  - Reconciled CalendarConfig (real /calendar/config wire)
  - Envelope-aware parse_market_data_response (items[] unwrap)
affects:
  - packages/market-data-client
  - main_market_data.py (SHAPE probe)
tech-stack:
  added: []
  patterns:
    - SafeModel tolerant deserialization against captured live wire snapshots
    - Endpoint-union field suppression in the SHAPE-diff probe (note/entries)
key-files:
  created: []
  modified:
    - packages/market-data-client/src/market_data_client/models.py
    - packages/market-data-client/src/market_data_client/__init__.py
    - packages/market-data-client/src/market_data_client/_core.py
    - main_market_data.py
    - packages/market-data-client/tests/test_models.py
    - packages/market-data-client/tests/test_reference_models.py
    - packages/market-data-client/tests/test_market_data.py
    - packages/market-data-client/tests/test_reference_client.py
    - packages/market-data-client/tests/test_reference_async_client.py
    - packages/market-data-client/tests/test_reference_core.py
decisions:
  - Retired the invented MarketDataEntry model; wire `entries` is a list[str] of entry-type codes
  - Retired CalendarConfig.businessDays; adopted the real config field set
  - mypy gate run as `uv run mypy packages/market-data-client/src` from repo root (the plan's `cd pkg && mypy src` form hits a module-resolution collision because market-data-client/src is absent from the root mypy `files` list)
metrics:
  duration: ~15m
  completed: 2026-07-31
---

# Phase quick-260731-jim Plan 01: Reconcile market-data-client MarketDataSnapshot + CalendarConfig Summary

Reconciled the market-data-client `MarketDataSnapshot` and `CalendarConfig` SafeModels against the real develop wire payloads captured in the LIVE-MD-01 schema snapshots, retired the invented `MarketDataEntry` model, and fixed the `parse_market_data_response` envelope-unwrap bug — closing the 36 SHAPE findings from the first credentialed live sweep.

## What Was Built

### Task 1 — MarketDataSnapshot reconciled, MarketDataEntry retired, envelope unwrapped (commit 0852d43)
- Replaced the `MarketDataSnapshot` field block with the real wire shape: `symbol`, `market_id` (was `marketId`), `active`, `entries: list[str]` (was `list[MarketDataEntry]`), `market_data: dict[str, Any]` passthrough, `staleness_seconds`, `received_at`, `note: str | None`.
- Deleted the invented `MarketDataEntry` dataclass and removed it from models `__all__` and from `__init__.py` (import + `__all__`). Updated the module-docstring prose that referenced it.
- `parse_market_data_response` now unwraps the develop envelope `{count, items:[...], ...}` via `items`, still tolerates a bare-list body, and collapses null/empty/other bodies to `[]`.
- Preserved the `received_at` client-stamp injection override verbatim (D-01): a wire/decoy `received_at` never overrides the injected stamp.

### Task 2 — CalendarConfig reconciled (commit 45c1885)
- Replaced the `CalendarConfig` field block (dropped invented `businessDays`) with the real config shape: `open`, `close`, `enabled`, `editable`, `env_bypass`, `pre_open_minutes`, `source`, `timezone`, `updated_by`, `warnings: list[Any]`, `updated_at: str | None`.
- Kept it a plain frozen SafeModel subclass with no `from_api` override and no `received_at` (D-05); `from_api(None)` still yields tolerant defaults (D-07).

### Task 3 — SHAPE probe + regression tests (commit 8c8e494)
- `main_market_data.py`: removed the `MarketDataEntry` import; added `_ENDPOINT_OPTIONAL = frozenset({"note", "entries"})` and extended the `_emit_shape` model-only skip to `_CLIENT_STAMPED | _ENDPOINT_OPTIONAL`; both sync and async market-data probes now unwrap the envelope `items[]` before sampling and no longer diff a nested entry model.
- `test_models.py`, `test_reference_models.py`, `test_market_data.py`: pinned the reconciled shapes against payloads mirroring the captured snapshots (new-field parse, latest no-data collapse, decoy `received_at`, envelope items[] parse + bare-list backward-compat, full CalendarConfig wire).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Broken tests from in-scope model change] Three additional CalendarConfig tests referenced the retired `businessDays` field**
- **Found during:** Task 3 (pytest gate)
- **Issue:** `test_reference_client.py`, `test_reference_async_client.py`, and `test_reference_core.py` asserted `result.businessDays == [...]` against the old CalendarConfig shape — not enumerated in the plan's Task 3 file list, but directly broken by the Task 2 model reconciliation.
- **Fix:** Updated all three to feed and assert the real `/calendar/config` wire shape (`open`/`close`/`timezone`/`warnings`/`updated_at`).
- **Files modified:** packages/market-data-client/tests/test_reference_client.py, test_reference_async_client.py, test_reference_core.py
- **Commit:** 8c8e494

**2. [Rule 3 - Gate invocation] mypy `cd pkg && mypy src` form fails with a module-resolution collision**
- **Issue:** market-data-client/src is not in the root `[tool.mypy] files` list, so `cd packages/market-data-client && mypy src` reports "Source file found twice under different module names".
- **Fix:** Ran the equivalent `uv run mypy packages/market-data-client/src` from the repo root (matches how CI invokes mypy) — strict, 11 files, no issues. No config file was changed (out of scope: CODE/TEST only).

## Verification

All gates green for market-data-client:
- `ruff check .` — All checks passed
- `ruff format --check .` — 187 files already formatted
- `uv run mypy packages/market-data-client/src` — Success: no issues found in 11 source files
- `pytest packages/market-data-client/tests -q` — **139 passed**
- `main_market_data.py` imports and parses without `MarketDataEntry`; `_ENDPOINT_OPTIONAL` present (AST-checked)

Operator follow-up (not part of this plan, no creds needed here): re-run `uv run --package market-data-client python main_market_data.py` against develop and confirm the SHAPE findings for MarketDataSnapshot and CalendarConfig drop to ~0.

## Deferred Issues (out of scope)

- `verification/test_matriz_sweep_snapshot.py::test_matriz_probe_envelope_shape_preserved[probe_get_market_data-...]` fails with `probe_get_market_data() missing 1 required positional argument: 'client'`. This is a **matriz** package sweep test (matched here only by a `-k market_data` filter) — it targets matriz's `main_matriz.py` probe signature, not this plan's `main_market_data.py`. It is pre-existing (present at the base commit) and none of this plan's three commits touch any matriz file. Left untouched per the scope boundary.

## Self-Check: PASSED

- Files: models.py, __init__.py, _core.py, main_market_data.py, SUMMARY.md — all FOUND.
- Commits: 0852d43, 45c1885, 8c8e494 — all FOUND.
- market-data-client tests: 139 passed. market-data verification guards: 2 passed.

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, or trust-boundary surface introduced. The reconciliation stays within the existing `develop API -> SafeModel.from_api` boundary, and `_coerce` tolerance (T-qmd-01) is preserved unchanged.
