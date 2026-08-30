---
phase: quick-260731-t9o
plan: 01
subsystem: market-data-client
status: complete
tags: [bugfix, parser, envelope-unwrap, regression-tests]
requires:
  - packages/market-data-client/src/market_data_client/models.py (MarketDataSnapshot.from_api)
provides:
  - parse_latest_response items-envelope unwrap (batch POST + single GET, one parser)
affects:
  - Client.get_latest_batch (sync)
  - aio get_latest_batch (async mirror)
tech-stack:
  added: []
  patterns: [items-envelope-unwrap, tolerant-parse, dual-sync-async-via-shared-core]
key-files:
  created: []
  modified:
    - packages/market-data-client/src/market_data_client/_core.py
    - packages/market-data-client/tests/test_market_data.py
    - packages/market-data-client/tests/test_client.py
    - packages/market-data-client/tests/test_async_client.py
decisions:
  - "not_found handling is out of scope — no model fields added, return type unchanged"
  - "Single parser (_core.parse_latest_response) covers sync + async; one fix covers both surfaces"
metrics:
  duration: ~6m
  completed: 2026-07-31
  tasks: 2
  files: 4
---

# Phase quick-260731-t9o Plan 01: Fix get_latest_batch Empty Snapshots Summary

Fixed `parse_latest_response` to unwrap the batch `POST /marketdata/latest`
`items` envelope (mirroring `parse_market_data_response`), so `get_latest_batch`
returns populated `MarketDataSnapshot`s instead of N empty ones — while preserving
the single-symbol GET bare-list path.

## What Was Built

**Task 1 — parser fix (`_core.py`):** Replaced the bare `for item in raw`
comprehension in `parse_latest_response` with the shape-branching unwrap used by
the already-fixed sibling `parse_market_data_response`: `dict → raw.get("items", [])`,
`list → raw`, `else → []`, plus a `not isinstance(rows, list)` guard. Root cause
was that iterating a dict yields its 5 string keys, each collapsing via
`MarketDataSnapshot.from_api(<str>)` to defaults → N empty snapshots. The stale
PROVISIONAL docstring (referencing unvendored OpenAPI shapes / Phase 23 reconciliation)
was replaced with the confirmed live shapes: single GET returns a bare list; batch
POST returns `{requested, count, not_found, server_time, items:[...]}`; other bodies
collapse to `[]`. Since `_core.py` is shared by `client.py` + `aio.py`, one change
covers sync AND async. Committed: `7d58b3f`.

**Task 2 — regression tests:** Added `test_parse_latest_response_batch_envelope_parses`
(real envelope → 2 populated snapshots, asserting `symbol`/`market_id` non-empty) and
`test_parse_latest_response_dict_without_items_returns_empty` (dict lacking `items` → `[]`,
no KeyError). Fixed the previously mis-mocked client-level batch tests
(`test_get_latest_batch_sends_bearer_and_body` sync + `test_async_...` async) — they
mocked the WRONG bare-list `json=[{...}]` shape (why the bug was never caught); now they
mock the real envelope and assert `result[0].symbol == "GGAL"`. Existing bare-list and
null-body tests kept unchanged (single-GET path still proven). Committed: `f1f051b`.

## Verification

All four package gates green:
- `uv run --package market-data-client pytest packages/market-data-client/tests -q` → 191 passed
- `uv run ruff check .` → All checks passed
- `uv run ruff format --check .` → 191 files already formatted
- `uv run mypy packages/market-data-client/src` → no issues (11 source files)

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- FOUND: packages/market-data-client/src/market_data_client/_core.py (isinstance(raw, dict) branch present)
- FOUND commit 7d58b3f (Task 1 fix)
- FOUND commit f1f051b (Task 2 tests)
