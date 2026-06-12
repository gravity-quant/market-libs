---
quick_id: 260611-u0v
description: Fix CI failures on phase-06-compat-safety-net (snapshot trailing whitespace + iol-client tests mypy strict)
status: complete
created: 2026-06-11
completed: 2026-06-11
commits:
  - bc16e26
  - 2be4e90
  - 9360cf5
---

# Quick Task 260611-u0v: Fix CI failures on phase-06-compat-safety-net

## Outcome

CI run `27386420928` had two red jobs after the initial phase-06 push:

| Job | Failure | Cause |
|-----|---------|-------|
| Type check (mypy) — tests step | 15 errors on `iol_client._get_default()` + 1 on `from iol_client.aio import _raise_for_response` | PEP 562 shim is invisible to mypy `--strict` with `implicit_reexport=False` |
| pre-commit hooks | `trailing-whitespace` strippea espacios de 4 snapshots | snapshot formatter emite `Name : kind : ` (trailing space) cuando el símbolo no tiene signature |

Both bugs fixed as separate atomic commits. A third commit cleared pre-existing tech debt in the v1.0 archive that surfaced when `pre-commit run --all-files` was added to CI parity check.

## Commits

| Commit | Type | Description |
|--------|------|-------------|
| `bc16e26` | fix(verification) | Drop trailing space in empty-signature snapshot lines (+ regenerate 4 snapshots) |
| `2be4e90` | fix(iol-client/tests) | Qualify private helpers for strict mypy — 14 sites migrated from `iol_client._get_default()` → `iol_client.client._get_default()`, plus `from iol_client.aio import _raise_for_response` → `from iol_client.client import _raise_for_response` |
| `9360cf5` | chore(docs) | Apply pre-commit auto-fixes to v1.0 archive (trailing-whitespace in STACK.md + 6 missing final newlines) |

## Acceptance Gate Results

All green:

| Check | Exit | Detail |
|-------|------|--------|
| `uv run mypy --strict packages/iol-client/tests` | 0 | 5 source files, no issues |
| `uv run mypy --strict packages/iol-client/src packages/iol-client/tests` | 0 | 10 source files |
| `uv run mypy` (global, CI parity) | 0 | 30 source files |
| `uv run pytest -q` | 0 | 389 passed, 1 skipped, 1 deselected |
| `uv run ruff check .` | 0 | all checks passed |
| `uv run ruff format --check .` | 0 | 86 files clean |
| `uv run python verification/regen_snapshots.py && git diff --exit-code verification/snapshots/` | 0 | idempotent — no drift |
| `uv run pre-commit run --all-files` | 0 | trim-trailing-whitespace, end-of-file-fixer, check-yaml, check-toml, check-added-large-files, check-merge-conflicts, ruff, ruff-format, mypy — all Passed |

## Files Touched

**Source (Task 1 — bc16e26):**
- `verification/test_public_surface.py` — line 107 ternary fix (only emit trailing space when `sig` is non-empty)
- `verification/snapshots/ambito-financiero-client-surface.txt` (regenerated)
- `verification/snapshots/iol-client-surface.txt` (regenerated)
- `verification/snapshots/higyrus-client-surface.txt` (regenerated)
- `verification/snapshots/matriz-client-surface.txt` (regenerated)

**Source (Task 2 — 2be4e90):**
- `packages/iol-client/tests/conftest.py` — 1 site qualified
- `packages/iol-client/tests/test_client.py` — 7 sites qualified
- `packages/iol-client/tests/test_client_class.py` — 6 sites qualified + 1 import line changed

**Docs (Pre-existing tech debt — 9360cf5):**
- `.planning/research/STACK.md` — trailing whitespace stripped
- `.planning/milestones/v1.0-phases/03-iol-verification/03-{01,02,03}-PLAN.md` — final newlines added
- `.planning/milestones/v1.0-phases/05-matriz-verification/05-{01,02,03}-PLAN.md` — final newlines added

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| How to fix mypy `_get_default` errors | Qualify with `iol_client.client._get_default()` | Keeps `_get_default` private (no `__all__` change), explicit module path that mypy understands, consistent with the design intent that `_get_default` is implementation detail of the shim |
| Source of `_raise_for_response` for tests | Import from `iol_client.client` (canonical home) | Plan 03/04 B8 lock: `aio.py` imports it from `client.py`. Tests should also use the canonical location |
| Pre-existing v1.0 archive tech debt | Fixed in a separate atomic chore commit | Clean separation of scope; keeps phase-06 quick task focused, but unblocks CI |

## What Was NOT Touched (per constraints)

- `iol_client.__all__` — `_get_default`, `_ensure_token`, etc. remain private
- The PEP 562 shim itself — runtime behavior unchanged
- Snapshot generation logic beyond the whitespace bug
- No `# type: ignore` added (preferred explicit-path solution)

## Pre-existing Issues Surfaced (Out of Scope, addressed in 9360cf5)

The user-requested CI parity check (`pre-commit run --all-files`) surfaced 7 pre-existing tech-debt issues in `.planning/` archive files unrelated to phase-06. These were committed as a separate `chore(docs)` so the scope of phase-06 work remained clean.

## CI Status After Fix

Pending re-run after push. Expected outcome:
- Type check (mypy) → green
- pre-commit hooks → green
- All test matrix (3.12 × 3.13 × 5 packages) → green (was already green pre-fix)
- Lint y formato (ruff) → green (was already green pre-fix)

## Push Status

NOT pushed yet — per user constraint, awaiting manual review then `git push origin phase-06-compat-safety-net`.
