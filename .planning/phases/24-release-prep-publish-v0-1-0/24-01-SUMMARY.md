---
phase: 24-release-prep-publish-v0-1-0
plan: 01
subsystem: infra
tags: [ci, release, uv, workspace, monorepo, documentation]

# Dependency graph
requires:
  - phase: 20-scaffold-auth0-client-credentials-fundaciones-de-transporte
    provides: market-data-client package scaffold (pyproject 0.1.0, workspace member)
  - phase: 23-verificaci-n-en-vivo-contra-develop-fixes
    provides: market-data-client offline verification apparatus + package public surface
provides:
  - market-data-client entry in the CI test matrix (py3.12 + py3.13 pytest+coverage)
  - CLAUDE.md documenting market-data-client as the 6th monorepo package
  - MEMORY index bullet + published pointer file for market-data-client v0.1.0
  - Committed uv.lock workspace-member registration (validated, not regenerated)
affects: [24-02 release PR + tag, future package-enumeration edits]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "6th-package fan-out: every package-enumeration surface (CI matrix, CLAUDE.md workspace list + count + component table, MEMORY index) gets a sibling entry copied verbatim in shape"

key-files:
  created:
    - .claude/projects/-Users-admin-development-market-libs/memory/market-data-client-v0.1.0-published.md
  modified:
    - .github/workflows/ci.yml
    - CLAUDE.md
    - .claude/projects/-Users-admin-development-market-libs/memory/MEMORY.md
    - uv.lock

key-decisions:
  - "Committed the pre-staged uv.lock workspace-member registration in this phase's PR (D-03/D-11 intent), validated with uv sync --frozen + uv lock --check rather than regenerating"
  - "Left global mypy files, importlinter root_packages, and the CI typecheck per-package loop untouched (recorded scope_decisions deferrals — coverage gaps, not CI failures)"

patterns-established:
  - "Package version alignment gate: pyproject version == __version__ == tag version (0.1.0) so release.yml version-match passes"

requirements-completed: [PUB-MD-01]

# Metrics
duration: 6min
completed: 2026-07-31
status: complete
---

# Phase 24 Plan 01: Release Prep — market-data-client v0.1.0 Summary

**Added market-data-client to the CI test matrix, documented it as the 6th monorepo package across CLAUDE.md + MEMORY, and committed the validated uv.lock workspace-member registration — no functional package code changed.**

## Performance

- **Duration:** ~6 min
- **Completed:** 2026-07-31
- **Tasks:** 3
- **Files modified:** 5 (4 modified + 1 created)

## Accomplishments
- CI test matrix now runs `market-data-client` (2 jobs: py3.12 + py3.13, pytest + coverage) — implements PUB-MD-01, D-01.
- CLAUDE.md documents the 6th package: Workspace Structure bullet, `6 packages` CI/CD count, `market_data_client` component-table row, and updated `<pkg>.aio` / `<pkg>.models` meta-rows — D-04.
- MEMORY index gains a published-package bullet + companion pointer file `market-data-client-v0.1.0-published.md` — D-05.
- Validated (not regenerated) the lockfile and version metadata and committed the `uv.lock` workspace-member registration — D-03/D-11/SC-1: `uv sync --frozen` and `uv lock --check` both exit 0; version aligned at 0.1.0 across pyproject + `__version__`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add market-data-client to the CI test matrix (D-01)** - `1f295b3` (ci)
2. **Task 2: Document market-data-client as the 6th package (D-04, D-05)** - `f781060` (docs)
3. **Task 3: Validate uv.lock / version alignment / workspace member (D-03, D-11, SC-1)** - `e8ff8e3` (chore — commits the validated uv.lock registration)

## Files Created/Modified
- `.github/workflows/ci.yml` - Appended `market-data-client` to the `test` job `matrix.package` list (only ci.yml block changed).
- `CLAUDE.md` - Workspace Structure bullet, CI/CD count 5→6, component-table row + meta-row updates.
- `.claude/projects/-Users-admin-development-market-libs/memory/MEMORY.md` - Added published-package index bullet.
- `.claude/projects/-Users-admin-development-market-libs/memory/market-data-client-v0.1.0-published.md` - New MEMORY pointer file (YAML frontmatter + prose; public metadata only, no credentials).
- `uv.lock` - Committed the pre-staged `market-data-client` editable workspace member + deps stanza.

## Decisions Made
- Followed the plan's `<scope_decisions>`: intentionally did NOT edit global mypy `files`, importlinter `root_packages`, or the CI `typecheck` per-package mypy loop. These are typecheck/import-linter coverage gaps, not CI failures — the new package's `pytest`+coverage runs via the matrix edit, so CI stays green. Out of D-01/D-11 scope.
- Committed `uv.lock` as part of Task 3 per the plan note that the pre-staged `M uv.lock` is the intended workspace-member registration for this phase's PR.

## Deviations from Plan

None affecting scope or code. One verify-command portability note (not a code change):

- Task 3's `<automated>` verify used bash process substitution `grep -qx '...' <(sed -n '3p' ...)`, which returns exit 1 under this environment's non-interactive zsh even though the underlying data is correct. Confirmed by re-running each assertion in isolation and via an equivalent pipe form (`sed -n '3p' ... | grep -qx '...'`), which prints `PASS`. All acceptance criteria are met: `uv sync --frozen` = 0, `uv lock --check` = 0, pyproject version = `0.1.0`, `__version__` = `0.1.0`, workspace member registered, `uv.lock` lists `market-data-client`.

## Issues Encountered
- `python3` in the environment lacks the `yaml` module for Task 1's YAML-parse assertion; used `uv run python` (which has PyYAML via the workspace) to confirm the matrix parses and contains `market-data-client`. No plan change.

## User Setup Required
None - no external service configuration required for release prep. (Phase 23 Wave 2 live verification remains paused pending Auth0 creds — tracked separately in `phase-23-wave2-pending-creds.md`, not resolved by this phase.)

## Next Phase Readiness
- Plan 02 can open the release PR and create the `market-data-client-v0.1.0` tag: CI now includes the package, docs reflect the 6th package, and the release.yml version-match gate will pass (version aligned at 0.1.0).
- No blockers for Plan 02.

## Self-Check: PASSED

All 5 target files exist on disk and all 3 task commits (`1f295b3`, `f781060`, `e8ff8e3`) are present in git history.

---
*Phase: 24-release-prep-publish-v0-1-0*
*Completed: 2026-07-31*
