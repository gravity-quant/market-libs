---
phase: 17-final-live-re-verification-4-live-03
plan: 03
subsystem: testing
tags: [requirements-traceability, milestone-closure, ci-gate, pytest, ruff, mypy, lint-imports, audit-open]

# Dependency graph
requires:
  - phase: 17-final-live-re-verification-4-live-03 (Plan 17-02)
    provides: operator-approved 17-VALIDATION.md (status approved) authorizing the v1.2 closure flip
  - phase: 17-final-live-re-verification-4-live-03 (Plan 17-01)
    provides: deterministic-gate attestation + pytest >= 989 collection baseline
provides:
  - REQUIREMENTS.md traceability flipped Open -> Complete for REFAC-05/SEC-01/ERG-01/LIVE-03 (REFAC-06 stays Deferred)
  - 0-BLOCKER integration audit attestation (2 carried non-BLOCKER items enumerated)
  - CI gate set attestation at HEAD (collect 989/990; ruff check; ruff format; mypy strict; lint-imports; CI-scoped pytest green)
  - explicit D-04 no-ship boundary record (no /gsd-ship, no milestone archive, no PR branch, no tag/merge)
affects: [v1.2 milestone close, gsd-ship, gsd-complete-milestone]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Traceability flip cites the authorizing operator-approved gate doc (17-VALIDATION.md) inline in the status cell"
    - "CI-scope-aware attestation: CI gates packages/*/tests only; verification/ tree is out-of-CI-scope"

key-files:
  created:
    - .planning/phases/17-final-live-re-verification-4-live-03/17-03-SUMMARY.md
    - .planning/phases/17-final-live-re-verification-4-live-03/deferred-items.md
  modified:
    - .planning/REQUIREMENTS.md

key-decisions:
  - "Flipped exactly 4 traceability cells + the LIVE-03 inline checkbox; REFAC-06 left Deferred; widened the Status column to keep table alignment"
  - "Classified the pre-existing test_matriz_sweep_snapshot.py failures (pytest-httpx 0.36 strictness) as out-of-CI-scope, pre-existing, non-BLOCKER; logged to deferred-items.md, NOT fixed (scope boundary)"
  - "Honored D-04: stopped short of ship — no /gsd-ship, no milestone archive, no PR branch, no tag/merge"

patterns-established:
  - "Status-cell annotation idiom: `Complete (Phase 17 LIVE-03 gate, 17-VALIDATION.md)`"

requirements-completed: [LIVE-03]

# Metrics
duration: 40min
completed: 2026-06-25
status: complete
---

# Phase 17 Plan 03: v1.2 Milestone-Closure Landing Summary

**REQUIREMENTS.md traceability flipped to Complete for REFAC-05/SEC-01/ERG-01/LIVE-03 (citing the operator-approved 17-VALIDATION.md gate), with a 0-BLOCKER integration audit and a CI-gate attestation — stopping short of ship per D-04.**

## Performance

- **Duration:** 40 min
- **Started:** 2026-06-25T00:14:50Z
- **Completed:** 2026-06-25T00:55:19Z
- **Tasks:** 2
- **Files modified:** 1 (REQUIREMENTS.md) + 2 created (this SUMMARY, deferred-items.md)

## Accomplishments

- **Task 1 — Traceability flip:** REFAC-05, SEC-01, ERG-01, and LIVE-03 status cells flipped
  `Open` → `Complete (Phase 17 LIVE-03 gate, 17-VALIDATION.md)` in the REQUIREMENTS.md
  traceability table; the inline `LIVE-03` checklist line flipped `[ ]` → `[x]`. REFAC-06 row
  left exactly as-is (`Deferred (Phase 12 NO-GO 2026-06-14)`). Column alignment preserved
  (Status column widened uniformly so the table still renders). Verified: exactly **4 Complete**
  across those four REQ-IDs; `grep "LIVE-03.*Complete.*17-VALIDATION"` matches.
- **Task 2 — Closure attestation:** ran the integration audit + the full CI gate set and recorded
  results; wrote the explicit D-04 no-ship boundary note. No source files modified (read-only
  attestation by design).

## Task Commits

1. **Task 1: Flip REQUIREMENTS.md traceability (REFAC-05/SEC-01/ERG-01/LIVE-03)** — `8ce2157` (docs)
2. **Task 2: 0-BLOCKER audit + CI-gate attestation + D-04 boundary** — read-only attestation,
   recorded in this SUMMARY (no source commit; the SUMMARY + deferred-items are committed with the
   plan-metadata commit).

## Files Created/Modified

- `.planning/REQUIREMENTS.md` — 4 traceability status cells flipped to Complete (citing 17-VALIDATION.md); LIVE-03 inline checkbox flipped to `[x]`; Status column re-padded.
- `.planning/phases/17-final-live-re-verification-4-live-03/deferred-items.md` — logs the out-of-scope, pre-existing `verification/test_matriz_sweep_snapshot.py` failure (DEF-17-01).
- `.planning/phases/17-final-live-re-verification-4-live-03/17-03-SUMMARY.md` — this file.

## Integration Audit (audit-open) — 0 BLOCKER

`node .claude/gsd-core/bin/gsd-tools.cjs query audit-open` reported **2 items**, both
**non-BLOCKER for v1.2 close** (the exact two carried items the plan named):

| Item | Type | Classification |
|------|------|----------------|
| Phase 15 `15-HUMAN-UAT.md` [partial] — 4 pending scenarios | UAT gap | **Non-BLOCKER** — operator-driven, carried per the v1.1 deferred pattern |
| `spike-codegen-libcst-v1.3.md` [codegen] (high) | Pending todo | **Non-BLOCKER** — explicitly deferred to v1.3 per Phase 12 NO-GO; unrelated to LIVE-03 |

**BLOCKER count for v1.2 close: 0.**

## CI Gate Set at HEAD (`8ce2157`)

| Gate | Command | Result |
|------|---------|--------|
| pytest collection | `uv run pytest -q --collect-only` | **989/990 collected** (1 deselected) — meets the Phase 15 ≥ 989 floor (SC#5) |
| ruff lint | `uv run ruff check .` | **PASS** — All checks passed |
| ruff format | `uv run ruff format --check .` | **PASS for this plan's change**; 4 pre-existing files flagged (see Deviations / DEF note) |
| mypy strict | `uv run mypy --strict` | **PASS** — no issues found in 51 source files |
| import contracts | `uv run lint-imports` | **PASS** — 4 contracts kept, 0 broken |
| CI-scoped tests | `uv run pytest -q packages/` | **GREEN — 754 passed, 1 deselected** (this is exactly what CI gates) |

**Workspace install:** `uv sync --all-packages --all-extras --dev --frozen` (frozen lockfile;
NO new packages installed; `uv.lock` unchanged). The worktree venv lacked the editable workspace
packages on entry (`ModuleNotFoundError`), so the frozen sync was required to run the gates — a
Rule 3 environment-readiness step, not a dependency change.

The plan's machine-checkable Task 2 verify block
(`--collect-only ≥ 989 && ruff check && mypy --strict`) = **PASS**.

## D-04 No-Ship Boundary (honored)

Per D-04, this phase **STOPS short of the actual PR/merge ship**:

- `/gsd-ship` — **NOT run**.
- `gsd-complete-milestone` / milestone archive — **NOT performed**.
- PR branch — **NOT created**.
- Tag / merge — **NONE** (`git tag --points-at HEAD` empty; only commit since base is the Task 1 docs commit `8ce2157`).

These remain deliberately downstream, informed by the operator-approved `17-VALIDATION.md`.

## Decisions Made

- Widened the REQUIREMENTS.md Status column uniformly (39 → 50 inner chars) so the longer
  `Complete (... 17-VALIDATION.md)` annotation keeps the markdown table aligned and rendering.
- Treated the `test_matriz_sweep_snapshot.py` failures as out-of-scope, pre-existing, and
  non-BLOCKER (see Deviations) rather than fixing them — the file is unchanged since Phase 07,
  is never executed by CI, and the fix is a test-only change best handled as a dedicated quick-task.

## Deviations from Plan

### Auto-handled (Rule 3 — blocking environment readiness)

**1. [Rule 3 - Blocking] Synced the workspace into the worktree venv**
- **Found during:** Task 2 (running the gate set).
- **Issue:** The worktree's `.venv` had no editable workspace packages installed, so
  `pytest --collect-only` raised `ModuleNotFoundError: No module named 'iol_client'` (etc.).
- **Fix:** `uv sync --all-packages --all-extras --dev --frozen` — installs only from the existing
  frozen lockfile (no new/substituted packages; `uv.lock` unchanged). Per the plan threat model
  (T-17-SC), no package-manager install of a *new* package occurred.
- **Verification:** collection then reported 989/990; `uv.lock` is `git status` clean.
- **Committed in:** N/A (no tracked file changed by the sync).

### Out-of-scope discovery (logged, NOT fixed — scope boundary)

**2. Pre-existing `verification/test_matriz_sweep_snapshot.py` failures under pytest-httpx 0.36.2 (DEF-17-01)**
- **Found during:** Task 2 (full-tree `uv run pytest -q`): **19 failed + 19 errors**, ALL confined to
  `verification/test_matriz_sweep_snapshot.py::test_matriz_probe_envelope_shape_preserved`. Rest of the
  full tree green (`19 failed, 970 passed, 1 deselected, 19 errors`).
- **Root cause:** locked `pytest-httpx==0.36.2` enforces *assert-all-responses-were-requested* at
  fixture teardown; the test registers mock responses the probe never requests
  (*"responses are mocked but not requested"*).
- **Why out-of-scope / non-BLOCKER:**
  - The file is **unchanged since Phase 07 (`9314e6e`)** — pre-existing, not touched by this plan
    (this plan only edited `.planning/REQUIREMENTS.md`).
  - **CI never runs it.** `.github/workflows/ci.yml` scopes the test job to
    `pytest packages/${matrix.package}` (per-package suites only); the top-level `verification/`
    tree is not on any CI path. The operator-confirmed CI matrix (3.12/3.13) is unaffected, and the
    CI-scoped suite is green here (754 passed).
  - It is dev-tooling (test-fixture strictness) drift, not v1.2 product code.
- **Disposition:** Logged to `deferred-items.md` (DEF-17-01) for a future test-hardening quick-task;
  NOT fixed here per the executor SCOPE BOUNDARY. Does not gate v1.2 milestone close.

---

**Total deviations:** 1 Rule-3 environment-readiness step (no file change) + 1 out-of-scope
discovery logged-not-fixed. **Impact:** none on the plan's deliverable — the traceability flip,
the 0-BLOCKER audit, the machine-checkable gate, and the CI-scoped suite are all satisfied; the
deferred item is pre-existing and out of CI scope.

## Issues Encountered

- The worktree venv was not pre-provisioned with workspace packages; resolved with a frozen
  `uv sync` (above).
- Discovered the `verification/` tree is **not** covered by CI; reconciled the plan's
  "full pytest green" intent with the CI-scoped reality — recorded both the full-tree result
  (transparently) and the authoritative CI-scoped result (green).

## Next Phase Readiness

- v1.2 requirement traceability is closed (4/5 Complete; REFAC-06 deferred to v1.3).
- Integration audit is 0-BLOCKER (2 carried non-BLOCKER items enumerated).
- CI gate set + CI-scoped suite green at HEAD; pytest collection ≥ 989.
- **Ready for the downstream ship workflow** (`/gsd-ship` → `gsd-complete-milestone`), which is
  deliberately NOT performed in this phase (D-04). Operator may run it informed by `17-VALIDATION.md`.
- **Carry-forward for v1.3 / a quick-task:** DEF-17-01 (test_matriz_sweep_snapshot pytest-httpx 0.36
  strictness) and the 4 pre-existing `ruff format` files in `verification/` + `main_ambito_financiero.py`.

## Self-Check: PASSED

- FOUND: `.planning/REQUIREMENTS.md` (4 cells Complete; LIVE-03 cites 17-VALIDATION.md)
- FOUND: `.planning/phases/17-final-live-re-verification-4-live-03/17-03-SUMMARY.md`
- FOUND: `.planning/phases/17-final-live-re-verification-4-live-03/deferred-items.md`
- FOUND commit: `8ce2157` (Task 1 traceability flip)

---
*Phase: 17-final-live-re-verification-4-live-03*
*Completed: 2026-06-25*
