# Deferred Items — Phase 07

## Plan 07-01

### Out-of-scope pre-existing ruff/format violations (NOT introduced by Plan 07-01)

- `.claude/skills/spike-findings-market-libs/sources/**/*.py` — ~54 ruff errors (I001, UP017, etc.) + format diff. Pre-exists on main (spike artifacts copied into skill).
- `.planning/spikes/003-tokenstore-refresh-policy/test_integration.py` y `test_policy.py` — ruff format diff. Pre-exists on main.

**Action:** Not fixed by Plan 07-01 (scope boundary — Plan 07-01 only touches `pyproject.toml`, `.github/workflows/ci.yml`, 4 `_core.py`, `verification/test_sync_async_isolation.py`).

**Note:** `uv run ruff check packages/` (scope: producible client packages) and `uv run ruff check verification/test_sync_async_isolation.py` both pass clean. Global `uv run ruff check .` only flags the spike/skill artifacts, which are documentation, not code under test.

**Recommended follow-up:** Track as a separate plan/quick task to either (a) exclude `.claude/skills/sources/` and `.planning/spikes/` from ruff scope in `pyproject.toml`, or (b) reformat those files in a single docs/style commit.
