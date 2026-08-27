# Phase 31: Endpoints de ops + estructura uniforme - Discussion Log (Assumptions Mode)

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-08-23
**Phase:** 31-endpoints-de-ops-estructura-uniforme
**Mode:** assumptions
**Areas analyzed:** Model design for the 5 ops endpoints, `_core` parser wiring and downstream
blast radius, Mutating-gate invariant and byte-identical-request test, Structural bootstrap of
`models.py`+`types.py` and CI existence check

## Assumptions Presented

### Model design for the 5 ops endpoints

| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| 5 response shapes derived from live schema snapshots; `add_holidays.days[]` reuses existing `CalendarDay` | Confident | `.planning/verification/schemas/market-data-client/add-holidays-sync-response.json` matches `CalendarDay` field set (`models.py:608-635`) |
| Each package extends its own existing `SafeModel` base verbatim; no `dict[...]` fields, no `received_at` | Confident | `market_data_client/models.py:137-146,160-179` mapping-policy top-level-only pin |
| `SafeModel.to_dict()` added to higyrus/market-data bases, copied from iol Phase 30 | Likely | `main_market_data.py:628-643,2381-2389`, `main_higyrus.py:670,685` call `len()`/`isinstance(dict)` on results |

### `_core` parser wiring and blast radius

| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Two shared parsers split into four, each decorated `@_decode._response_parser` | Confident | `_core.py:280-285` and `:1083-1114` currently serve two unrelated endpoints each |
| Phase is not zero-edit — mocks fixed to live wire shape (Phase 30-03 precedent) | Confident | `test_calendar_write.py:306-317` mocks `{created, skipped}` vs. live `{days, note, saved}` |
| higyrus keeps raise-on-non-dict + 204→zero-valued; market-data gains equivalent guard | Likely | `higyrus_client/_core.py:426-454`, pinned by `tests/test_core.py:412-415` |

### Mutating-gate and byte-identical-request test

| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| The AST guard ROADMAP.md assumes green does not exist — must be built or criterion restated | Confident | repo-wide grep for statement-order AST checks on client.py/aio.py returns nothing; only behavioural tests exist |
| No reusable byte-identical-request pattern exists — needs new raw-bytes capture-compare helper | Confident | existing tests compare via `json.loads`, never full header set or query string |

### Structural bootstrap and CI existence check

| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Criterion 4 is 7 new files (types.py ×5, models.py ×2), not 4 | Confident | `ls packages/*/src/*/` — only matriz has `types.py` |
| Wallets gets docstring-only models.py/types.py, no `_decode.py`/`_state.py` obligation | Confident | `tools/check_decode_intactness.py:625-662` Check D never inspects models.py/types.py |
| Existence check ships as new stdlib script in existing CI `lint` job (decode-intactness precedent) | Confident | `.github/workflows/ci.yml` decode-intactness step reasoning applies identically |
| 4 new market-data models not covered by CI mypy this phase (D-16 is Phase 32) | Confident | `pyproject.toml:97` files list and `ci.yml:85` loop both exclude market-data-client |

## Corrections Made

No corrections — all assumptions confirmed ("Yes, proceed").

## External Research

None performed — all decisions resolvable from committed schema snapshots, source, and CI config
in-repo.
