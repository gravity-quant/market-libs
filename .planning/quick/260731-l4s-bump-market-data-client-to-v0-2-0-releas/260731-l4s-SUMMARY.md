---
quick_id: 260731-l4s
title: Bump market-data-client to v0.2.0 (release prep)
status: complete
tasks_completed: 1
tasks_total: 1
files_created: []
files_modified:
  - packages/market-data-client/pyproject.toml
  - packages/market-data-client/src/market_data_client/__init__.py
  - CLAUDE.md
  - packages/market-data-client/README.md
  - uv.lock
commits:
  - 73dda1c: chore(260731-l4s) bump market-data-client to v0.2.0
completed: 2026-07-31
---

# Quick Task 260731-l4s: Bump market-data-client to v0.2.0 Summary

Version-identity bump of `market-data-client` from `0.1.0` to `0.2.0` (semver minor
for breaking changes on the 0.x line) so a new tag/release can publish the LIVE-MD-01
bug fixes already merged to `main`. No client logic changed — pure version + docs edits.

## What Was Done

- `pyproject.toml`: `version = "0.1.0"` → `"0.2.0"`.
- `src/market_data_client/__init__.py`: `__version__ = "0.1.0"` → `"0.2.0"`.
- `CLAUDE.md`: workspace bullet for `packages/market-data-client/` now reads `v0.2.0`.
- `README.md`: added a `## Changelog` section with a `v0.2.0` entry documenting the four
  breaking changes (required `get_latest(symbol=...)`, `MarketDataSnapshot` field
  reconciliation, `CalendarConfig` field reconciliation, `parse_market_data_response`
  envelope-unwrap).
- `uv.lock`: refreshed via `uv lock` (recorded `market-data-client v0.1.0 -> v0.2.0`).

## Verification

- `grep '^version' pyproject.toml` → `version = "0.2.0"` ✓
- `grep __version__ __init__.py` → `__version__ = "0.2.0"` ✓
- `uv lock --check` → exit 0 (clean) ✓
- `uv run --package market-data-client ruff check` → All checks passed ✓
- `uv run --package market-data-client pytest -q` → **139 passed in 0.26s** ✓

## Deviations from Plan

None — plan executed exactly as written.

## Scope Adherence

- Did NOT edit `release.yml` or `ci.yml`.
- Did NOT create a git tag.
- Did NOT touch `ROADMAP.md` or any `.planning/` file other than this SUMMARY.
- Staged only the five edited files via explicit paths (no `git add -A`).

## Self-Check: PASSED

- Commit 73dda1c present in git history ✓
- All five modified files staged and committed ✓
- Version reads `0.2.0` in both pyproject and `__version__` ✓
