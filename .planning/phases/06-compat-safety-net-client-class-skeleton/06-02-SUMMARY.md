---
phase: 06-compat-safety-net-client-class-skeleton
plan: 02
subsystem: testing

tags: [pytest, pytest-httpx, monkeypatch, sentinel-tokens, guard-tests, safety-net, sync-async, fixture-reaches-production, pitfall-1]

# Dependency graph
requires:
  - phase: 06-compat-safety-net-client-class-skeleton
    provides: Plan 06-01 ROADMAP/CONTEXT artifacts naming the per-package guard placement (RESEARCH.md Architectural Responsibility Map; VALIDATION.md Wave 0 Gaps)
provides:
  - "Per-package guard test files at packages/<pkg>/tests/test_fixture_reaches_production.py for all 4 verifiable packages (ambito, iol, higyrus, matriz)"
  - "Pitfall #1 safety net: each guard proves a sentinel monkeypatched onto module-level _token reaches the wire-level Authorization (iol/higyrus) or X-Auth-Token (matriz) header, and configured base_url reaches the wire URL (ambito)"
  - "Sync + async coverage: 4 sync + 3 async tests run green; matriz async is a permanent pytest.skip pointing at Phase 10 REFAC-04"
  - "Per-package ownership of guard files (no shared verification/ file) — eliminates Wave 1 write conflict so Plans 03/04/05/06 each migrate their OWN guard file independently"
affects:
  - 06-03-PLAN (ambito refactor) — must keep ambito guard green after Client class skeleton
  - 06-04-PLAN (iol refactor) — must migrate iol guard in-place to configure(token=...) and keep it green
  - 06-05-PLAN (higyrus refactor) — must migrate higyrus guard in-place and rename _token_ts → token_expires_at field reference
  - 06-06-PLAN (matriz refactor) — must migrate matriz sync guard in-place; async stub-skip stays until Phase 10
  - Phase 7 (_core.py dedup) — same SYNC-/ASYNC-sentinel naming reused
  - Phase 10 (matriz aio.py / TokenStore) — removes the matriz async pytest.skip

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-package guard file at packages/<pkg>/tests/test_fixture_reaches_production.py"
    - "SYNC-sentinel-<pkg> / ASYNC-sentinel-<pkg> naming so failing test localizes to sync vs async surface immediately"
    - "Lazy `from <pkg> import aio` inside the async test body (keeps sync collection clean)"
    - "Wire-level header assertion via `[req] = httpx_mock.get_requests(); assert req.headers['<header>'] == '<expected>'`"
    - "Deferred-work documentation via permanent `pytest.skip` with reason string pointing at the future phase"

key-files:
  created:
    - "packages/ambito-financiero-client/tests/test_fixture_reaches_production.py"
    - "packages/iol-client/tests/test_fixture_reaches_production.py"
    - "packages/higyrus-client/tests/test_fixture_reaches_production.py"
    - "packages/matriz-client/tests/test_fixture_reaches_production.py"
  modified: []

key-decisions:
  - "LEGACY pattern monkeypatch.setattr(pkg.client, '_token', ..., raising=False) — Plan 02 must run green against PRE-refactor code where configure(token=...) does NOT yet exist (RESEARCH.md Open Q #2)"
  - "Per-package file placement instead of shared verification/test_fixture_reaches_production.py — resolves checker B1/B2/B3 by giving each Wave 1 plan exclusive ownership of its guard file (no shared-file write conflict)"
  - "Matriz async guard is a permanent pytest.skip with explicit Phase 10 REFAC-04 reason — collection still counts 1 skipped, giving a discoverable CI reminder of the deferred async surface (RESEARCH.md Open Q #1)"
  - "Sentinel naming SYNC-sentinel-<pkg> / ASYNC-sentinel-<pkg> — a failed assertion immediately localizes the broken surface (sync vs async) and the package without grepping"
  - "Endpoint choice mirrors existing tests in each package: iol.get_instruments('argentina'), higyrus.get_listado_cuentas(estado='alta'), matriz.get_segments(), ambito.get_dollar_banco_nacion(dt.date(2026, 1, 2)) — keeps mock URLs aligned with conftest base_url='https://api.test'"

patterns-established:
  - "Pitfall #1 guard pattern: monkeypatch a unique sentinel onto module-level _token, call a real pkg.get_*(), assert req.headers[<auth-header>] matches the sentinel — proves the test fixture reaches the wire and fails LOUD if a refactor breaks the address."
  - "Async test imports the aio submodule INSIDE the test body (lazy), not at module top — keeps sync test collection self-contained even if aio.py changes shape."

requirements-completed: [REFAC-01]

# Metrics
duration: 4min
completed: 2026-06-11
---

# Phase 06 Plan 02: Compat Safety Net — Per-package fixture-reaches-production Guards Summary

**Per-package guard tests proving that a sentinel monkeypatched onto each module-level `_token` reaches the wire-level `Authorization` (iol/higyrus) / `X-Auth-Token` (matriz) header — and that `configure(base_url=...)` reaches the wire URL for the no-auth ambito case — with 7 passing + 1 matriz-async permanent skip.**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-06-11T02:34:22Z
- **Completed:** 2026-06-11T02:38:04Z
- **Tasks:** 2
- **Files created:** 4

## Accomplishments

- Pitfall #1 safety net is now in place per package: the legacy `monkeypatch.setattr(pkg.client, "_token", sentinel, raising=False)` pattern is exercised end-to-end and the assertion fails LOUD if the sentinel doesn't reach the outgoing httpx request's auth header (or URL, for ambito).
- All 4 packages own their guard file exclusively under `packages/<pkg>/tests/test_fixture_reaches_production.py` — no shared `verification/` artifact, so Wave 1 Plans 03/04/05/06 can each migrate their OWN guard file in-place without coordination (resolves checker B1/B2/B3 write-conflict risk).
- 4 sync + 3 async = 7 active tests pass against the PRE-refactor code; the matriz async case is a permanent `pytest.skip` carrying the explicit `"matriz aio.py is Phase 10 REFAC-04; stub AsyncClient ships in Plan 06 with no REST methods"` reason so CI emits a discoverable reminder of the deferred work.
- Baseline 277 tests remain green: full suite reports `284 passed, 1 skipped` (277 baseline + 7 new active = 284; +1 matriz async skip).

## Task Commits

Each task was committed atomically:

1. **Task 1: Per-package sync guard tests (4 files, one per package)** — `dcecd16` (test)
2. **Task 2: Append per-package async guards (3 real + 1 matriz skip)** — `26aab5d` (test)

## Files Created/Modified

- `packages/ambito-financiero-client/tests/test_fixture_reaches_production.py` — sync + async guard: `configure(base_url=...)` reaches wire URL (no auth). 47 lines.
- `packages/iol-client/tests/test_fixture_reaches_production.py` — sync + async guard: sentinel reaches `Authorization: Bearer` header. 60 lines.
- `packages/higyrus-client/tests/test_fixture_reaches_production.py` — sync + async guard: sentinel reaches `Authorization: Bearer` header (uses `_token_ts` pre-refactor field). 56 lines.
- `packages/matriz-client/tests/test_fixture_reaches_production.py` — sync guard: sentinel reaches `X-Auth-Token` header. Async is permanent `pytest.skip` pointing at Phase 10 REFAC-04. 60 lines.

## Decisions Made

- **LEGACY pattern over `configure(token=...)`** — Plan 02 must run green against PRE-refactor code; the `configure(token=...)` API does not exist yet (lands in Plans 03-06 per-package). Each per-package plan migrates its OWN guard atomically in Wave 1.
- **Per-package guard placement** — RESEARCH.md Architectural Responsibility Map and VALIDATION.md Wave 0 Gaps both place these tests inside each package's own `tests/` directory; a shared `verification/test_fixture_reaches_production.py` would force Plans 03/04/05/06 to mutate the same file concurrently in Wave 1.
- **Endpoint choice per package** — used the simplest authed GET that already has fixtures: `iol.get_instruments('argentina')`, `higyrus.get_listado_cuentas(estado='alta')`, `matriz.get_segments()`, `ambito.get_dollar_banco_nacion(dt.date(2026, 1, 2))`. Mock URLs align with each conftest's `base_url='https://api.test'` (or `https://configured.test` for the ambito override case).
- **Matriz async as permanent skip** — `pytest.skip` with the explicit Phase 10 reason gives a permanent, discoverable CI reminder of the deferred matriz aio.py work (RESEARCH.md Open Q #1).

## Deviations from Plan

None — plan executed exactly as written. The 4 sync + 3 async + 1 matriz-async-skip layout matches the `<behavior>` map verbatim, the LEGACY `monkeypatch.setattr` pattern was used as specified (per RESEARCH.md Open Q #2), and verification (`uv run pytest .../test_fixture_reaches_production.py -q` → 7 passed + 1 skipped) succeeded on the first run.

Ruff format added consistent line-wrapping to 3 of the 4 files (the matriz/iol/higyrus files were initially written with multi-line monkeypatch calls that ruff format collapsed to single lines). This is project-policy formatting, not a deviation — the formatter's output is the canonical form per CLAUDE.md.

## Issues Encountered

- Initial `uv run pytest` failed with `ModuleNotFoundError: No module named 'ambito_financiero_client'` because the worktree's `.venv` was empty. Resolved by running `uv sync --all-packages --all-extras --dev --frozen` once at the start. Standard worktree setup step; not a regression.
- Initial `mypy --strict packages/*/tests/test_fixture_reaches_production.py` reported "Duplicate module named test_fixture_reaches_production" when all 4 files were passed in one invocation. Resolved by running mypy per-package, which is how the project's CI matrix runs it (`packages/<pkg>` is the per-package source root). All 4 packages pass `mypy --strict` cleanly when invoked per package.

## Verification

- `uv run pytest packages/*/tests/test_fixture_reaches_production.py -q` → **7 passed, 1 skipped**.
- `uv run pytest -q` → **284 passed, 1 skipped, 1 deselected** (baseline 277 + 7 new = 284; the skip is the matriz async stub).
- `uv run ruff check packages/*/tests/test_fixture_reaches_production.py` → **All checks passed**.
- `uv run ruff format --check packages/*/tests/test_fixture_reaches_production.py` → **4 files already formatted**.
- `uv run mypy --strict packages/<pkg>/tests/test_fixture_reaches_production.py` (per package) → **Success: no issues found** for each of the 4 packages.
- `git ls-files 'packages/*/tests/test_fixture_reaches_production.py' | wc -l` → **4** (one per package; no shared file).

## User Setup Required

None — no external service configuration required. The plan declared `user_setup: []` and that holds: this plan ships test-only artifacts that run entirely against `httpx_mock`.

## Next Phase Readiness

- Wave 1 (Plans 03/04/05/06) is unblocked: each per-package plan owns exactly one guard file under its own `tests/` tree and can migrate the LEGACY `monkeypatch.setattr` pattern to `pkg.configure(token=...)` atomically as part of the per-package refactor commit.
- Sentinel naming convention (`SYNC-sentinel-<pkg>` / `ASYNC-sentinel-<pkg>`) is established and reusable in Phase 7 `_core.py` dedup guard tests.
- The matriz async stub-skip is the single permanent deferred-work marker carried into Phase 10; no other guards are deferred.

## Threat Flags

None — this plan adds test-only files exercising existing wire surfaces. No new endpoints, auth paths, or schema changes. The STRIDE threat T-06-01 disposition (mitigate) is satisfied: the guard tests are the explicit mitigation for Pitfall #1.

## Self-Check: PASSED

Verified after writing the SUMMARY:

- `packages/ambito-financiero-client/tests/test_fixture_reaches_production.py` → FOUND
- `packages/iol-client/tests/test_fixture_reaches_production.py` → FOUND
- `packages/higyrus-client/tests/test_fixture_reaches_production.py` → FOUND
- `packages/matriz-client/tests/test_fixture_reaches_production.py` → FOUND
- Commit `dcecd16` (Task 1 sync guards) → FOUND in `git log`
- Commit `26aab5d` (Task 2 async guards) → FOUND in `git log`

---
*Phase: 06-compat-safety-net-client-class-skeleton*
*Completed: 2026-06-11*
