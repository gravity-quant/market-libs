---
phase: 06-compat-safety-net-client-class-skeleton
plan: 07
subsystem: testing
tags: [ci, pytest, ruff, mypy, snapshot, mutation-gate, python-3.13, python-3.12, audit]

requires:
  - phase: 06-01
    provides: snapshot test harness (`verification/test_public_surface.py`, `verification/regen_snapshots.py`)
  - phase: 06-02
    provides: 8 fixture-reaches-production guard tests across the 4 in-scope packages
  - phase: 06-03
    provides: ambito Client/AsyncClient skeleton + PEP 562 shim
  - phase: 06-04
    provides: iol Client/AsyncClient skeleton + PEP 562 shim (refresh_token)
  - phase: 06-05
    provides: higyrus Client/AsyncClient skeleton + PEP 562 shim
  - phase: 06-06
    provides: matriz Client + stub AsyncClient + PEP 562 shim (incl. `_base_url`)
provides:
  - End-to-end CI green proof on Python 3.12 + 3.13 of Plans 03-06 (4 packages refactored) plus Plans 01-02 (safety net)
  - mutation_gate audit (B6) confirming `verification/mutation_gate.py` works unchanged via the matriz PEP 562 `_base_url` shim
  - Driver py_compile smoke (W4 replacement for the fragile `exec(...split('if __name__')[0])` idiom)
  - Closure of REFAC-01 success criteria 1-2 and REFAC-02 success criteria 3-5
affects: [phase-07-core-extraction, phase-08-retries-logging, phase-09-deferred-bugs, phase-10-matriz-aio, phase-11-harness-final]

tech-stack:
  added: []
  patterns:
    - "Phase verification = full stack (pytest + ruff + mypy + snapshot + driver py_compile + cross-package audit) on BOTH Python 3.12 AND 3.13"
    - "Audit-only plan: B6 mutation_gate audit owns no production edits if the gate works unchanged"
    - "Driver smoke = `python -m py_compile` (W4) — single safe syntax check, no execution"

key-files:
  created:
    - .planning/phases/06-compat-safety-net-client-class-skeleton/06-07-SUMMARY.md
  modified: []  # verification/mutation_gate.py audited — no edit required (audit PASSED)

key-decisions:
  - "Audit-only outcome: mutation_gate.py works unchanged via matriz `_base_url` shim — no edit applied"
  - "B4 closure: Python 3.13 explicitly verified for pytest AND mypy in Task 1 automation"
  - "B6 closure: Plan 06 left mutation_gate.py untouched; Plan 07 owned the audit and confirmed PASS"
  - "W4 closure: driver smoke uses `python -m py_compile` not `exec(...split('if __name__')[0])`"

patterns-established:
  - "Multi-version CI gate plan: run the full stack twice (3.12 + 3.13) inside a single executor task and produce a structured pass/fail report for the operator checkpoint"
  - "Audit-only plan as a first-class atomic commit: `files_modified` may end up empty after the audit if the audit passes"

requirements-completed: [REFAC-01, REFAC-02]

duration: ~8 min
completed: 2026-06-11
---

# Phase 6 Plan 07: CI Green Gate Summary

**Phase 6 CI matrix proven green end-to-end on Python 3.12 AND 3.13 (389 passed, 1 skipped on each) — mutation_gate audit PASSED unchanged.**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-06-11T03:03:10Z (executor start)
- **Completed:** 2026-06-11T03:11:00Z (approx)
- **Tasks executed:** 1 of 2 (Task 1 automated; Task 2 is the operator checkpoint — see "Checkpoint" below)
- **Files modified:** 0 (audit-only outcome — `verification/mutation_gate.py` works unchanged)

## Accomplishments

- Ran the full Phase 6 verification stack twice (Python 3.12 and Python 3.13) and confirmed identical green results: 389 passed, 1 skipped (matriz async stub), 1 deselected — same on both interpreters.
- Validated `ruff check` + `ruff format --check` clean across the workspace (86 files).
- Validated `mypy --strict` clean on Python 3.12 AND 3.13 across the 4 in-scope package src/ trees (`ambito-financiero-client`, `iol-client`, `higyrus-client`, `matriz-client`) — 26 source files, 0 issues each run.
- Confirmed snapshot regen idempotency: `verification/regen_snapshots.py` produces zero diff against the committed snapshots (4 packages: ambito 9 symbols, iol 13 symbols, higyrus 29 symbols, matriz 64 symbols).
- All 4 in-scope drivers `python -m py_compile` cleanly; `main_wallets.py` (optional, out of scope) also compiles cleanly.
- Audited `verification/mutation_gate.py` (B6): sandbox host → `mutating_allowed() == True`, prod host → `mutating_allowed() == False`, missing `VERIFY_MUTATING` → `False`. Matriz PEP 562 `_base_url` shim returns the configured URL correctly. **No edit applied** — the file works unchanged after the matriz refactor.

## Task 1 Pass/Fail Report

```
Phase 6 verification report
============================
[PASS] uv run pytest -q                                        (3.12, 389 tests passed, 1 skipped, 1 deselected)
[PASS] uv run --python 3.13 pytest -q                          (3.13, 389 tests passed, 1 skipped, 1 deselected)
[PASS] uv run ruff check .                                     (All checks passed)
[PASS] uv run ruff format --check .                            (86 files already formatted)
[PASS] uv run mypy --strict packages/*/src                     (3.12, 26 source files, 0 issues)
[PASS] uv run --python 3.13 mypy --strict packages/*/src       (3.13, 26 source files, 0 issues)
[PASS] Snapshot regen idempotent                                (regen + git diff --exit-code, exit 0)
[PASS] python -m py_compile main_iol.py main_higyrus.py main_matriz.py main_ambito_financiero.py
[PASS] python -m py_compile main_wallets.py                    (optional / out of phase scope — also clean)
[PASS] mutation_gate audit (sandbox=True / prod=False)         (B6 — sandbox=True, prod=False, no VERIFY_MUTATING=False)
[PASS] verification/mutation_gate.py edits required             (PASS = no edits required after audit)
```

All 11 checks PASS, BOTH 3.12 AND 3.13 pytest+mypy lines PASS (B4 satisfied).

## Exit codes (per command)

| Command | Exit | Notes |
|---------|------|-------|
| `uv run pytest -q` (3.12) | 0 | 389 passed, 1 skipped, 1 deselected, 1.19s |
| `uv run --python 3.13 pytest -q` | 0 | 389 passed, 1 skipped, 1 deselected, 1.26s |
| `uv run ruff check .` | 0 | All checks passed |
| `uv run ruff format --check .` | 0 | 86 files already formatted |
| `uv run mypy --strict packages/*/src` (3.12) | 0 | 26 source files, 0 issues, ~4s |
| `uv run --python 3.13 mypy --strict packages/*/src` | 0 | 26 source files, 0 issues, ~3s |
| `uv run python verification/regen_snapshots.py` | 0 | Wrote 4 snapshots, total 115 symbols |
| `git diff --exit-code verification/snapshots/` | 0 | No drift vs committed |
| `uv run python -m py_compile main_iol.py main_higyrus.py main_matriz.py main_ambito_financiero.py` | 0 | All 4 in-scope drivers parse |
| `uv run python -m py_compile main_wallets.py` | 0 | Out-of-scope but clean |
| mutation_gate audit (ad-hoc script) | 0 | Sandbox=True, Prod=False, no-flag=False |

## Mutation gate audit detail (B6)

```
  Shim _base_url after configure(sandbox) -> 'https://api.remarkets.primary.com.ar'
  mutating_allowed() with sandbox host = True
  Shim _base_url after configure(prod) -> 'https://api.primary.com.ar'
SKIPPED (mutating, guard off)
  mutating_allowed() with prod host = False
SKIPPED (mutating, guard off)
  mutating_allowed() with sandbox host but no VERIFY_MUTATING = False

AUDIT PASSED: mutation_gate.py works correctly with matriz shim (sandbox=True, prod=False).
```

- `verification/mutation_gate.py:55` reads `matriz_client.client._base_url` — this is the PEP 562 shim point installed by Plan 06 Open Q #4.
- Shim returns the live `_get_default()._state.base_url` value (verified via `configure(base_url=...)` round-trip).
- Both sandbox-positive and prod-negative cases produce the expected `mutating_allowed()` outcome.
- Conclusion: **no edits to `verification/mutation_gate.py` required**; Plan 07's `files_modified` entry is a no-op audit record (allowed by plan text line 91: "If no inconsistency, the file is left untouched and this plan's `files_modified` entry is a no-op audit record.").

## Task Commits

This plan produced no source-code commits — the audit outcome (B6) was a no-op. The only artifact committed by this plan is this SUMMARY.md (plan metadata commit at the end).

1. **Task 1: Automated phase verification** — no commit (audit pass = no file edits to `verification/mutation_gate.py`).
2. **Task 2: Operator checkpoint** — see CHECKPOINT REACHED block; awaiting operator approval.

**Plan metadata commit:** committed at executor exit with SUMMARY.md only (worktree mode excludes STATE.md and ROADMAP.md — orchestrator owns those post-merge).

## Files Created/Modified

- **Created:** `.planning/phases/06-compat-safety-net-client-class-skeleton/06-07-SUMMARY.md` (this file)
- **Modified:** none — `verification/mutation_gate.py` audited and left untouched (audit PASSED)

## Decisions Made

- **No edit to `verification/mutation_gate.py`** — the matriz PEP 562 `_base_url` shim (installed by Plan 06) forwards correctly to `_get_default()._state.base_url`; the existing `urlsplit(base).hostname != _SANDBOX_HOST` check still produces the expected sandbox=True / prod=False outcome. Per Plan 06-07 line 91, this is the intended audit-pass outcome and `files_modified` is a no-op record.
- **B4 closure:** Python 3.13 verified explicitly via `uv run --python 3.13 pytest` and `uv run --python 3.13 mypy --strict` — identical results to 3.12 (389 passed, 1 skipped; 0 mypy issues).

## Deviations from Plan

None — plan executed exactly as written. The audit-only outcome (no edit to `verification/mutation_gate.py`) is the explicitly-documented PASS path in the plan (Task 1 step 8: "If the audit PASSES, leave `verification/mutation_gate.py` untouched and record 'audit-only, no edits required' in the SUMMARY.").

## Issues Encountered

- **uv venv recreation across Python versions:** Each time the active Python version switched (3.12 → 3.13 → 3.12), `uv run` re-created `.venv/` and dropped the workspace packages. Resolved by re-running `uv sync --all-packages --all-extras --dev --frozen` after each switch. Not a defect — expected uv behavior when the interpreter pin changes.

## Known Stubs

None added by this plan. Pre-existing: matriz `AsyncClient` is intentionally stub-only (REFAC-04, Phase 10) and produces the single `1 skipped` test (`packages/matriz-client/tests/test_fixture_reaches_production.py:64`).

## Threat Flags

None — this plan does not modify production code or introduce new network surface. The mutation_gate audit confirmed the existing sandbox/prod gate logic still holds end-to-end.

## Self-Check

- [x] `.planning/phases/06-compat-safety-net-client-class-skeleton/06-07-SUMMARY.md` exists (this file).
- [x] No edits to `verification/mutation_gate.py` (confirmed via `git status --short` clean and `git diff verification/mutation_gate.py` empty).
- [x] Task 1 pass/fail report 11/11 PASS (recorded above).
- [x] Both Python 3.12 AND Python 3.13 explicitly run for pytest and mypy (B4).
- [x] Driver py_compile smoke uses `python -m py_compile` (W4 replacement).
- [x] mutation_gate audit ran end-to-end via matriz shim (B6 closure).
- [x] Snapshot regen produces zero diff against committed state (D-06 additive-only invariant preserved).

## Self-Check: PASSED

## Next Phase Readiness

- REFAC-01 fully met: snapshot test green + 8 fixture-reaches-production guards (4 sync + 3 async + 1 matriz async skip) green across 4 packages + Phase 6 entry-baseline already committed (Plan 01 Task 4).
- REFAC-02 fully met: 4 packages expose `Client` + `AsyncClient` (matriz async is stub-only per scope), 277-test baseline + Phase 6 new tests all green, CI matrix on 3.12 + 3.13 proven green by this plan.
- Phase 7 (`_core.py` extraction) can launch: the 4 in-scope packages have a clean Client/AsyncClient skeleton that Phase 7 will dedupe; matriz async is deferred to Phase 10 (REFAC-04) per scope.
- **Operator checkpoint pending:** Task 2 awaits operator approval after CI matrix on push goes green on both 3.12 and 3.13.

## CHECKPOINT REACHED

**Type:** human-verify
**Plan:** 06-07
**Progress:** 1/2 tasks complete (Task 1 PASS; Task 2 awaiting operator approval)

### Completed Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Automated phase verification on Python 3.12 AND 3.13 (audit pass) | (no source commit — audit-only) | `verification/mutation_gate.py` audited unchanged |

### Current Task

**Task 2:** Operator verifies CI green on push (Python 3.12 + 3.13 matrix) + reviews snapshot diff
**Status:** awaiting verification
**Blocked by:** operator approval

### Checkpoint Details

**Task 1 pass/fail report (verbatim, copy-paste for Task 2 step 1):**

```
Phase 6 verification report
============================
[PASS] uv run pytest -q                                        (3.12, 389 tests passed, 1 skipped, 1 deselected)
[PASS] uv run --python 3.13 pytest -q                          (3.13, 389 tests passed, 1 skipped, 1 deselected)
[PASS] uv run ruff check .                                     (All checks passed)
[PASS] uv run ruff format --check .                            (86 files already formatted)
[PASS] uv run mypy --strict packages/*/src                     (3.12, 26 source files, 0 issues)
[PASS] uv run --python 3.13 mypy --strict packages/*/src       (3.13, 26 source files, 0 issues)
[PASS] Snapshot regen idempotent                                (regen + git diff --exit-code, exit 0)
[PASS] python -m py_compile main_iol.py main_higyrus.py main_matriz.py main_ambito_financiero.py
[PASS] python -m py_compile main_wallets.py                    (optional / out of phase scope — also clean)
[PASS] mutation_gate audit (sandbox=True / prod=False)         (B6 — sandbox=True, prod=False, no VERIFY_MUTATING=False)
[PASS] verification/mutation_gate.py edits required             (PASS = no edits required after audit)
```

**How to verify (Task 2 steps):**

1. Confirm the report above shows 11 PASS lines (no FAIL) — including BOTH 3.12 and 3.13 pytest + mypy lines (B4).
2. Review the snapshot diff: `git diff verification/snapshots/` — should be empty (regen produced zero drift). Each `<pkg>-surface.txt` has only additive `Client : class : ...` / `AsyncClient : class : ...` entries vs the pre-Phase-6 baseline (D-06 invariant); each snapshot still has the 8-line `#` header with line 8 == `#` (W3 invariant).
3. Review the baseline: `git show HEAD verification/baselines/phase-06-baseline.txt` — confirm `test_count:`, `coverage_total:`, `git_sha:` lines (B5 invariant from Plan 01 Task 4).
4. Push the worktree branch to its target and watch the CI Actions tab:
   - lint job: green
   - typecheck job: green
   - tests × Python 3.12 × 5 packages: green
   - tests × Python 3.13 × 5 packages: green
5. Optional manual smoke (operator-driven, not required): `uv run --package higyrus-client python main_higyrus.py --help` — confirm no `AttributeError` on `pkg.client._client` (validates the D-21 shim contract for `_client.event_hooks` mutation).
6. Sanity check: `uv run python -c "import iol_client; print(type(iol_client.Client).__name__, type(iol_client.AsyncClient).__name__); print(type(iol_client._get_default()).__name__)"` — already verified by this executor; prints `type type` + `Client`.

### Awaiting

Operator types **"approved"** if CI matrix on 3.12 + 3.13 is green and snapshot diff is additive-only, or describes any failures (e.g., "ruff complains about UP032 in iol/client.py line 88" → Plan 04 needs a fix).

---

*Phase: 06-compat-safety-net-client-class-skeleton*
*Plan: 07 (CI green gate)*
*Completed: 2026-06-11 (Task 1 automated; Task 2 awaiting operator approval)*
