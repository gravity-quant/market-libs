---
phase: 21-market-data-lectura-modelos
plan: 01
subsystem: market-data-client models
tags: [models, safemodel, received_at, tdd, deserialization]
requires:
  - packages/higyrus-client SafeModel/_coerce (template, copied not imported)
provides:
  - market_data_client.models.SafeModel
  - market_data_client.models._coerce
  - market_data_client.models.MarketDataEntry
  - market_data_client.models.MarketDataSnapshot (received_at first-class)
  - market_data_client.models.LatestRequest (to_dict)
affects:
  - market_data_client/_core.py (Plan 02 parsers build on these models)
  - market_data_client/client.py + aio.py (Plans 03/04 read methods)
tech-stack:
  added: []
  patterns:
    - Tolerant SafeModel.from_api with typed-zero safe defaults
    - received_at client-stamp injection bypassing _coerce (D-01)
    - frozen slots dataclasses, camelCase wire-verbatim provisional fields
    - request dataclass with to_dict dropping None optionals (D-05)
key-files:
  created:
    - packages/market-data-client/src/market_data_client/models.py
    - packages/market-data-client/tests/test_models.py
  modified:
    - pyproject.toml
decisions:
  - "D-01: received_at injected as kwarg on MarketDataSnapshot.from_api, never routed through _coerce; decoy payload key ignored"
  - "D-03: SafeModel + _coerce copied verbatim into market_data_client.models, no cross-package import from higyrus_client"
  - "D-04: N815 per-file-ignore added to ROOT pyproject.toml (no-op under current select set; forward-safety)"
  - "D-05: LatestRequest is a plain frozen dataclass (not SafeModel) with explicit to_dict dropping None optionals"
  - "A1/A2: model field names PROVISIONAL (OpenAPI not vendored); Phase 23 reconciles against real payloads; from_api tolerance bounds blast radius"
metrics:
  duration_minutes: 1
  completed: 2026-07-30
  tasks: 3
  files: 3
status: complete
---

# Phase 21 Plan 01: Market-data models + received_at injection Summary

Net-new tolerant `models.py` for `market-data-client` — a package-local `SafeModel`/`_coerce` copy, a `MarketDataSnapshot` with a nested `MarketDataEntry` list and a client-stamped `received_at` first-class field (injected without coercion), and a `LatestRequest` request dataclass — built TDD (RED→GREEN) with the D-04 N815 per-file-ignore added to the root pyproject.

## What Was Built

- **`market_data_client/models.py`** (net-new): module docstring mirroring higyrus (safe-default table, camelCase rationale, N815 note, D-01 received_at contract); `SafeModel` base + `_coerce` helper copied verbatim from `higyrus_client/models.py` (no import, D-03); `MarketDataEntry` and `MarketDataSnapshot` frozen/slots dataclasses with provisional camelCase wire fields; `MarketDataSnapshot.from_api(payload, *, received_at=0.0)` overridden to inject `received_at` directly and route every other field through `_coerce`; `LatestRequest` frozen dataclass with `to_dict()` dropping `None` optionals; explicit `__all__`.
- **`tests/test_models.py`** (net-new): 9 tests covering `{}`/`None`/extra-key tolerance, typed-zero defaults, `received_at` injection winning over a decoy `{"received_at": 999.0}` payload key, `received_at` defaulting to `0.0` without the kwarg, nested entry deserialization with no `received_at` attribute, wrong-type entries collapsing to `[]`, and `LatestRequest.to_dict` drop/keep behavior.
- **root `pyproject.toml`**: added `"packages/market-data-client/src/market_data_client/models.py" = ["N815"]` under `[tool.ruff.lint.per-file-ignores]`.

## Task Commits

| Task | Name | Type | Commit |
| ---- | ---- | ---- | ------ |
| 1 | Write failing model tests (RED) | test | 15abfaa |
| 2 | Create models.py — SafeModel copy + snapshot/entry + LatestRequest (GREEN) | feat | 1229859 |
| 3 | Add N815 per-file-ignore for models.py (D-04) | chore | 22d0f6b |

## TDD Gate Compliance

- RED gate: `test(21-01)` commit 15abfaa — import failed (`ModuleNotFoundError: market_data_client.models`), confirming RED before implementation.
- GREEN gate: `feat(21-01)` commit 1229859 — 9/9 model tests pass.
- REFACTOR: none needed.

## Verification Results

- `uv run --package market-data-client pytest packages/market-data-client -q` → 65 passed (full package suite, no regressions).
- `uv run --package market-data-client pytest packages/market-data-client/tests/test_models.py -q` → 9 passed.
- `uv run mypy packages/market-data-client/src` → Success, no issues in 10 source files.
- `uv run ruff check packages/market-data-client` → all checks passed.
- `uv run ruff format --check packages/market-data-client` → 19 files already formatted.
- No `import` of any `higyrus_client` symbol in `models.py` (grep found only docstring mentions).

## Threat Mitigations

- **T-21-01-01 (Tampering — malformed/partial payload)**: mitigated. `SafeModel.from_api` + `_coerce` never raise on `None`/non-dict/partial/extra-key payloads; substitute typed zero-values. Pinned by the tolerance tests.
- **T-21-01-02 (Info Disclosure)**: accepted per plan — read-only market-data models carry no credentials.
- **T-21-01-SC (supply chain)**: no new packages installed this plan; no checkpoint required.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] ruff-format applied to test_models.py**
- **Found during:** Task 2 pre-commit gate check.
- **Issue:** `test_models.py` (committed in Task 1) had a multi-line call ruff wanted collapsed onto one line, failing `ruff format --check`.
- **Fix:** ran `uv run ruff format` on the file; folded the one-line reformat into the Task 2 GREEN commit so the lint gate stays green.
- **Files modified:** packages/market-data-client/tests/test_models.py
- **Commit:** 1229859

## Known Stubs

The `MarketDataEntry` / `MarketDataSnapshot` / `LatestRequest` field names are PROVISIONAL by design (A1/A2 — OpenAPI not vendored). This is not a blocking stub: `from_api` tolerance bounds the blast radius and Phase 23 reconciles the exact wire shape against real payloads. Documented as a known blocker in STATE.md (Phases 21-22 risk).

## Self-Check: PASSED

- FOUND: packages/market-data-client/src/market_data_client/models.py
- FOUND: packages/market-data-client/tests/test_models.py
- FOUND: pyproject.toml N815 entry
- FOUND commit: 15abfaa (test RED)
- FOUND commit: 1229859 (feat GREEN)
- FOUND commit: 22d0f6b (chore N815)
