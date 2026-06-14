# Phase 8 — Deferred Items

Pre-existing out-of-scope issues encountered during Phase 8 execution. These are
not caused by Phase 8 changes and must NOT be fixed inside Phase 8 (scope boundary
per executor deviation rules).

## Pre-existing ruff violations in spike research files (Plan 1)

**Discovered:** 2026-06-13 during Plan 1 Task 1 (ruff LOG ruleset addition).

**Issue:** Running `uv run ruff check .` from repo root reports **108 errors** in:
- `.claude/skills/spike-findings-market-libs/sources/00{1a,1b,1c,2,3}-*/` — 9 files
- `.planning/spikes/00{1a,1b,1c,2,3}-*/` — 9 files

The violations use rules ALREADY ENABLED before Phase 8 (F401, F541, F841, B011,
I001, PT015, RET504, RUF003, RUF059, SIM105, UP017, UP035 — NOT from the new "LOG"
ruleset). Verified by checking out HEAD pyproject.toml (without LOG) and re-running
ruff: still 108 errors.

**Why not fixed in Plan 1:** Out-of-scope — these spike artifacts were committed
in `ba83b38` and `5db0a0d` (post-Phase 7) and are research analysis files, not
production source code. The Phase 8 plan explicitly scopes its ruff verification
to `uv run ruff check verification/` (Task 1 verify line 188) and `uv run ruff
check packages/` — both PASS cleanly with the new LOG ruleset.

**Verified:**
- `uv run ruff check verification/` -> `All checks passed!`
- `uv run ruff check packages/` -> `All checks passed!`
- New LOG rule does NOT contribute to the 108 errors (pre-existing).

**Resolution path:** Address in a separate quick task (or Phase 11 harness
hardening) — either:
- (a) Fix the spike files with `ruff check --fix .` + manual cleanup for unfixable rules
- (b) Add `extend-exclude = [".planning/spikes/", ".claude/skills/spike-findings-market-libs/sources/"]` to `[tool.ruff]` (recommended — research artifacts should not be linted)

Both routes are outside Phase 8 scope (retries+logging infra). The CI step
`uv run ruff check .` may currently be red for the same reason — verify against
the latest CI run on `main`.
