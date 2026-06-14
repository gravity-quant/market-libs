---
phase: 11-harness-hardening-code-review-close-out-live-re-verification
slug: harness-hardening-code-review-close-out-live-re-verification
status: approved
nyquist_compliant: true
phase_status: ready_for_close
requirements_closed:
  - HARN-07
  - HARN-08
  - HARN-09
  - HARN-10
  - CR-01
  - CR-02
  - CR-04
  - CR-06
  - CR-07
  - CR-08
  - LIVE-01
operator_dispositions:
  ambito: no_new_findings
  iol: F-02 FIXED — PROBE_STALE inline fix (main_iol.py:1289 INT-01 idiom); re-run PASS
  higyrus: no_new_findings
  matriz: no_new_findings
baseline_commit: 4d48e07
head_commit_at_task_2: 71bf201
head_commit_at_pre_fill: 71bf201
created: 2026-06-14
updated: 2026-06-14
operator_signoff_date: 2026-06-14
operator_signoff_by: sebadlf (Sebastián de la Fuente)
operator_signoff_run_logs:
  - /tmp/phase11-live-ambito.log
  - /tmp/phase11-live-iol.log (pre-fix)
  - /tmp/phase11-live-higyrus.log
  - /tmp/phase11-live-matriz.log
  - /tmp/phase11-iol-post-fix.log (post-INT-01 idiom fix; F-02 → FIXED)
---

# Phase 11 — Validation Closure (Pre-Operator Pre-Fill)

> **STATUS: Pre-operator pre-fill produced by Plan 11-03 Task 3 (checkpoint:human-verify).**
> The executor has run preflight + 4 sequential live drivers, captured all evidence,
> and detected ZERO blocking regressions (sync/async URL isolation GREEN; credential
> leak GREEN; PASS→FAIL flips ZERO).
>
> 1 NEW FINDING surfaced: **iol F-02** (AUTH/sync OPEN — `_token_expires_at` not refreshed).
> Requires operator disposition (PASS / NEW-BUG-XX / EXPECTED / NO-FIX) before
> Task 4 finalises this file with `status: approved` + `nyquist_compliant: true`
> + `phase_status: ready_for_close`.
>
> See `## Operator Approval (Pending)` below for the resume signal.

---

## LIVE-01 Evidence

**Baseline:** commit `4d48e07` ("docs(05): baseline DRIFT-02 cycle closure (verification-cycle-2026-Q2)")
**Head at Task 2 commit:** `71bf201` ("test(11-03): live re-run × 3 packages — Task 2 sequential live runs")

**Run commands (per-package serial idiom — ámbito → iol → higyrus → matriz):**

- `uv run --package ambito-financiero-client python main_ambito_financiero.py`
- `uv run --package iol-client python main_iol.py`
- `uv run --package higyrus-client python main_higyrus.py`
- `uv run --package matriz-client python main_matriz.py`

**Acceptance bar (operator-gated per D-LIVE-01):**

| Package | Pre-baseline status | Post-run SUMMARY | NEW FIDs vs baseline | Operator disposition |
|---|---|---|---|---|
| ámbito-financiero-client | PASS (F-01 EXPECTED) | PASS=6 FAIL=0 SKIPPED=1 FINDING=0 | (none) | `no_new_findings` |
| iol-client | PASS (F-01 OPEN — pre-existing SHAPE finding) | PASS=12 FAIL=0 SKIPPED=1 FINDING=2 | **F-02 (AUTH/sync OPEN)** | **PENDING** — operator must choose |
| higyrus-client | PASS (F-01 EXPECTED + F-02 NO-FIX — Phase 9) | PASS=16 FAIL=0 SKIPPED=2 FINDING=1 | (none) | `no_new_findings` |
| matriz-client | F-01..F-10 (mix EXPECTED + OPEN; F-02+F-10 D-MATZ-27 prod-vs-remarkets EXPECTED) | PASS=31 FAIL=0 SKIPPED=18 FINDING=1 | (none) | `no_new_findings` |

**Per-package log artifacts:**

- `/tmp/phase11-live-ambito.log` (352 bytes)
- `/tmp/phase11-live-iol.log` (937 bytes)
- `/tmp/phase11-live-higyrus.log` (1139 bytes)
- `/tmp/phase11-live-matriz.log` (3865 bytes)
- `/tmp/phase11-live-diff-<pkg>.log` (per-package diff vs 4d48e07)
- `/tmp/phase11-live-new-findings.log` (NEW FIDs enumeration)
- `/tmp/phase11-live-blockers.log` (EMPTY — zero blocking regressions)
- `/tmp/phase11-preflight.log` (Task 1 preflight)

**Blocking regressions (NO operator gate — block close if non-zero):**

| Gate | D-LIVE-01 § | Test / Detection | Result |
|---|---|---|---|
| (a) Wire URL changes sync vs async | regresión bloqueante (a) | `verification/test_sync_async_isolation.py` | **GREEN** (9 passed) |
| (b) Probe outcome flips PASS→FAIL (PRE-baseline FIDs) | regresión bloqueante (b) | Diff scan over `/tmp/phase11-live-diff-<pkg>.log` | **ZERO** (blockers log empty) |
| (c) Credential leak in logs | regresión bloqueante (c) | `verification/test_logging_no_token_leak.py` + grep | **GREEN** (5 passed; grep clean) |

---

## NEW FINDING — iol F-02 (operator review required)

**Title:** `_token_expires_at no se renovó tras refresh path`
**Class / Surface / Status:** `AUTH` / `sync` / `OPEN`
**Probe origin:** `probe_refresh_token` in `main_iol.py:1261-1362`
**Expected:** `_token_expires_at > <now>` after `_refresh()` exercised the refresh branch.
**Actual:** `_token_expires_at = 0.0` (unchanged from the simulated expiry written at line 1289).
**Diff (operator-friendly):** the refresh path completed successfully (`get_instruments("argentina")` returned 200 OK and `_token` rotated), but `_token_expires_at` was not updated. Either (a) `_refresh()` is missing the expiry write after a successful refresh, or (b) the path fell back to password (line ~1330) but the fallback omits the expiry write.

**Why it appears NEW vs baseline 4d48e07:**

The baseline (`verification-cycle-2026-Q2`, Phase 5) ran before Phase 6 IOL refactors (CR-01/CR-02 login() preservation) and before Phase 9 BUG-03 in-instance lifecycle work. The probe was reworked in those phases; in this Phase 11 re-run the probe successfully exercises the refresh branch in vivo (via simulated expiry at line 1289) and the assertion at line 1348 (`if expires_at_after <= time.time():`) trips.

The finding is NEW because:

1. Pre-Phase-6, the probe likely did not exercise the same code path (or fell back to a different branch).
2. Pre-Phase-9 BUG-03, `_refresh_token` was process-global (not in `_state`); the assertion semantics differed.
3. Post-Phase-9 BUG-03, `_refresh_token` is in-instance; the probe now consistently reaches the assertion site.

**Suggested operator dispositions** (operator to choose ONE — Phase 9 BUG-02 NO-FIX pattern):

- **NEW-BUG-XX** — actionable bug in `iol_client._refresh()` (or fallback path): missing `_token_expires_at = time.time() + 900` after the successful refresh response. Quick task or v1.2 backlog. Annotation to add to `iol-client-findings.md` F-02 section:
  ```markdown
  Classification: NEW-BUG-XX
  Rationale: refresh path in iol_client._refresh()/fallback does not update _token_expires_at; allows downstream consumers to read a stale 0.0 even though _token is valid.
  Regression: TBD — file under .planning/todos/pending/ if v1.2.
  ```
- **NO-FIX** — out-of-scope for v1.1 close; track in v1.2 backlog. Same annotation but `Classification: NO-FIX` + rationale citing scope.
- **EXPECTED** — acknowledged divergence (e.g., if the design intentionally leaves expiry at 0.0 after refresh because `_ensure_token()` re-checks token freshness on every call regardless). Unlikely fit.
- **PASS** — false positive (e.g., probe assertion is stale post-Phase-9 refactor). Operator can patch the probe (`main_iol.py:1348`) to read the expected expiry from a different signal, OR keep finding section with rationale.

**Operator next step:**

1. Open `.planning/verification/iol-client-findings.md` and locate the `### F-02 -- _token_expires_at no se renovó tras refresh path` section (post live-run, idempotent_by_title-flagged).
2. Append the chosen `Classification:` + `Rationale:` operator field bullets right after the existing `- **Diff:** el refresh path no actualizó el expiry` line (Plan 11-01 HARN-09 ensures these survive future re-runs).
3. Type `approved` (or your preferred resume signal) in the conversation to release the checkpoint and trigger Task 4 (which will finalise this file with `status: approved`, `nyquist_compliant: true`, `phase_status: ready_for_close`, and `operator_dispositions.iol: <your choice>`).

---

## HARN-07/08/09/10 Closure Evidence (Plan 11-01)

| Req | Mechanism | Commit | Verification |
|---|---|---|---|
| HARN-07 | `verification/findings.py` BEGIN/END zone parser + 3-zone state machine; 4 baseline files migrated | `967b868` (parser), `e8307a6` (migration) | `verification/test_findings_append_only.py` (4 tests, 4 cases) GREEN |
| HARN-08 | `append_finding(idempotent_by_title=True)` kwarg + 4 driver adoption at EXPECTED terminals | `967b868` (kwarg), `8b157ae` (drivers) | `verification/test_findings_dedupe_by_title.py` (12 cases) GREEN |
| HARN-09 | Operator field preservation across N re-runs (`Classification:`/`Rationale:`/`Regression:`/`Resolution:`) | `8b157ae` (ART block refresh in operator_prefix path) | `verification/test_findings_append_only.py` (N=3 re-run preservation) GREEN |
| HARN-10 | matriz `D-MATZ-27` EXPECTED terminal dedupe in 1 run via `idempotent_by_title=True` flip at `main_matriz.py:2117` | `8b157ae` | Pre/post live-run count: baseline `4d48e07` has 2 occurrences (F-02 + F-10 — different findings sharing title); Plan 11-03 Task 2 re-run kept count at 2 (no 3rd duplicate added) — flag works as designed. See `/tmp/phase11-harn10-clarification.log`. |

---

## CR-01/02/04/06/07/08 Closure Evidence (Plan 11-02)

| CR | Test file | Source file edits | Commit(s) |
|---|---|---|---|
| CR-07 | `packages/higyrus-client/tests/test_event_hooks_thread_safety.py` (3 tests) | `main_higyrus.py` lock-wrap of `_capture_*_query_string` | `c855666` (RED) + `f0ca84d` (GREEN) |
| CR-06 | `verification/test_main_drivers_bare_except.py` (2 cases parametric) | `main_matriz.py` (10 sites narrowed) + `main_higyrus.py` (17 sites narrowed) | `9e0e611` (RED) + `2d1b920` (GREEN matriz) + `0c26bd5` (GREEN higyrus) |
| CR-04 | `verification/test_main_matriz_first_dict.py` (5 tests) | `main_matriz.py:182-189` `_first_dict` 3-branch + `fname=` kwarg | `aa41a83` (RED+GREEN single) |
| CR-02 | `verification/test_main_matriz_login_fail_uniformity.py` (2 tests) | `main_matriz.py:411,428` `probe_login_sync` FAIL→FINDING + `PrimaryAPIError` in `_RESIDUAL_PROBE_EXCEPTIONS` (Rule 1 deviation) | `bc4acc1` (RED+GREEN single, includes Rule 1 fix) |
| CR-01 | `verification/test_main_matriz_schema_snapshot_alignment.py` (3 tests) | `main_matriz.py:1297-1321` placeholder-everywhere `sample_params` | `383d000` (RED+GREEN single) |
| CR-08 | n/a (ruff-only gate per D-CR-02) | `pyproject.toml [tool.ruff] extend-exclude` for spike artifacts | `023dd29` (chore) |

**Net change (Plan 11-02):** +15 test cases, 27 bare except sites → 0, 108 pre-existing ruff errors → 0.

---

## Phase 6-10 Carry-Forward Invariants (must stay GREEN)

All gates re-verified against worktree HEAD (`71bf201`, Plan 11-03 Task 2 commit).

| Phase | Invariant | Test | Result |
|---|---|---|---|
| 6 | Public surface snapshot zero diff (post-Plan-11-02 driver edits NOT in scope) | `verification/test_public_surface.py` | **4 passed** |
| 6 | Fixture-reaches-production guard × 4 packages | `packages/*/tests/test_fixture_reaches_production.py` | **8 passed** |
| 7 | `_core.py` import-linter contracts (transport not imported) | `uv run lint-imports` | **4 kept, 0 broken** |
| 7+10 | Cross-leak sentinel (sync vs async tokens; matriz async extension) | `verification/test_sync_async_isolation.py` | **9 passed** |
| 8 | Mutation gate (Pitfall #4 — no retry on POST) | `verification/test_retry_mutation_gate.py` | **passed** (within 10-passed bundle) |
| 8 | RedactingFilter (no token leak) | `verification/test_logging_no_token_leak.py` | **5 passed** |
| 8 | `logging.basicConfig` / `logging.root` clean | `verification/test_logging_root_unchanged.py` | **passed** (within 10-passed bundle) |
| 9 | BUG-01..04 regression (matriz CFI / higyrus listado_cuentas / iol refresh_token / higyrus multi-account) | `packages/matriz-client/tests/`, `packages/higyrus-client/tests/`, `packages/iol-client/tests/` | **576 passed** (full per-package suite) |
| 10 | matriz aio.py = AsyncClient + 22 endpoints | (included in 576-passed bundle above) | **PASS** |
| 10 | matriz cross-leak sentinel async extension | `verification/test_sync_async_isolation.py::test_matriz_*` | **PASS** (within 9-passed bundle) |
| 11-01 | Findings append-only + idempotent_by_title (16 cases) | `verification/test_findings_append_only.py` + `verification/test_findings_dedupe_by_title.py` | **16 passed** |
| 11-02 | 5 CR regression tests (15 cases) | `verification/test_main_*.py` + `packages/higyrus-client/tests/test_event_hooks_thread_safety.py` | **15 passed** |

---

## CI Green Final Matrix

All gates run against worktree HEAD `71bf201`.

| Gate | Command | Result |
|---|---|---|
| ruff check (full repo) | `uv run ruff check .` | **All checks passed!** |
| ruff format check | `uv run ruff format --check .` | **148 files already formatted** |
| mypy strict | `uv run mypy --strict` | **Success: no issues found in 50 source files** |
| import-linter | `uv run lint-imports` | **Contracts: 4 kept, 0 broken** |
| pytest Python 3.12 | `uv run pytest -q` | **907 passed, 1 deselected in 166.46s** |
| pytest Python 3.13 | `UV_PYTHON=3.13 uv run pytest -q` | **907 passed, 1 deselected in 166.67s** |

---

## Phase 11 Atomic Commit Log

| Plan | Task / CR | Commit type | Commit SHA |
|---|---|---|---|
| 11-01 | Task 1 — `findings.py` BEGIN/END parser + `idempotent_by_title` | feat | `967b868` |
| 11-01 | Task 2 — 4 baseline `<pkg>-findings.md` migration | docs | `e8307a6` |
| 11-01 | Task 3 — 4 driver adoptions + ART refresh (Rule 1) | feat | `8b157ae` |
| 11-01 | SUMMARY | docs | `5b689d0` |
| 11-02 | CR-07 RED | test | `c855666` |
| 11-02 | CR-07 GREEN | fix | `f0ca84d` |
| 11-02 | CR-06 RED | test | `9e0e611` |
| 11-02 | CR-06 GREEN matriz | fix | `2d1b920` |
| 11-02 | CR-06 GREEN higyrus | fix | `0c26bd5` |
| 11-02 | CR-04 (RED+GREEN single) | fix | `aa41a83` |
| 11-02 | CR-02 (RED+GREEN single + Rule 1 PrimaryAPIError) | fix | `bc4acc1` |
| 11-02 | CR-01 (RED+GREEN single) | fix | `383d000` |
| 11-02 | CR-08 (chore + spike housekeeping) | chore | `023dd29` |
| 11-02 | SUMMARY | docs | `b8f424a` |
| 11-03 | Task 2 — 3 live re-run findings.md mutations (`iol` + `higyrus` + `matriz`) | test | `71bf201` |
| 11-03 | Task 4 — `11-VALIDATION.md` + `CYCLE-REPORT.md` Q#6 update | ci | `<PENDING TASK 4>` |
| 11-03 | Task 5 — `11-03-SUMMARY.md` close-out | docs | `<PENDING TASK 5>` |

---

## Operator Approval (Granted 2026-06-14)

**Operator:** sebadlf (Sebastián de la Fuente)
**Date:** 2026-06-14
**Disposition for iol F-02:** **FIX INLINE (Recommended option)** — fix applied + re-run PASS confirmed; F-02 marked FIXED in iol-client-findings.md with PROBE_STALE classification + Resolution + Regression operator-content bullets (HARN-09 preserves these across N re-runs).

**Resolution applied:**

1. Root cause analysis (during Task 3 checkpoint): the probe at `main_iol.py:1289` wrote `iol_client.client._token_expires_at = 0.0` which CREATED a module attribute that SHADOWED the PEP 562 `__getattr__` forward to `state.token_expires_at`. Post-`_refresh()`, the read `iol_client.client._token_expires_at` returned the cached `0.0` from the module, not the state value. Client code (`packages/iol-client/src/iol_client/client.py:270`) was correct all along.

2. INT-01 idiom fix applied to `main_iol.py:1289`:
   ```python
   # Before (creates module attribute shadowing PEP 562):
   iol_client.client._token_expires_at = 0.0
   # After (INT-01 idiom — quick task 260613-nwb pattern):
   iol_client.client._get_default()._state.token_expires_at = 0.0
   ```

3. Re-run `uv run --package iol-client python main_iol.py` post-fix → `PROBE refresh_token: PASS refresh path verified — token rotated`. SUMMARY: PASS=13 / FAIL=0 / SKIPPED=1 / FINDING=1 (only F-01 field_type_map — pre-existing OPEN, not Phase 11 regression).

4. `.planning/verification/iol-client-findings.md` F-02 manually edited:
   - Status: OPEN → FIXED (in Index table + per-finding section)
   - Operator fields added BELOW `<!-- END AUTO-GENERATED -->` marker (HARN-09 contract):
     - Classification: PROBE_STALE (not a client bug)
     - Rationale (probe shadowing PEP 562 forward)
     - Resolution (INT-01 idiom fix applied)
     - Regression (re-run PASS evidence)
     - Operator signoff (sebadlf, 2026-06-14)

**LIVE-01 acceptance bar PASSED:**
- All 4 packages' findings files have FIDs disposition matching D-LIVE-01 rules:
  - ámbito: no_new_findings ✅
  - iol: F-02 FIXED inline ✅ (operator-gated disposition + Resolution bullet)
  - higyrus: no_new_findings ✅
  - matriz: no_new_findings ✅
- Zero blocking regressions: sync/async URL isolation ✅, credential leaks ✅, PASS→FAIL flips ✅
- CI green final matrix: 907 passed × 3.12+3.13 ✅; ruff 0 errors ✅; mypy strict ✅; lint-imports 4/4 ✅

**Phase 11 ready for atomic closure commit + 11-03-SUMMARY.md (Tasks 4+5 by orchestrator inline since fix is in main checkout).**

---

## Pre-Operator Evidence Index

| Item | Path |
|---|---|
| Plan | `.planning/phases/11-harness-hardening-code-review-close-out-live-re-verification/11-03-PLAN.md` |
| Plan 11-01 SUMMARY | `.planning/phases/11-harness-hardening-code-review-close-out-live-re-verification/11-01-SUMMARY.md` |
| Plan 11-02 SUMMARY | `.planning/phases/11-harness-hardening-code-review-close-out-live-re-verification/11-02-SUMMARY.md` |
| Preflight log (Task 1) | `/tmp/phase11-preflight.log` |
| Live run logs (Task 2) | `/tmp/phase11-live-{ambito,iol,higyrus,matriz}.log` |
| Per-package diffs vs baseline | `/tmp/phase11-live-diff-{ambito,iol,higyrus,matriz}-client.log` |
| NEW FIDs enumeration | `/tmp/phase11-live-new-findings.log` |
| Blockers log (must be empty) | `/tmp/phase11-live-blockers.log` |
| HARN-10 invariant clarification | `/tmp/phase11-harn10-clarification.log` |
| CI gates log | `/tmp/phase11-gate.log` |
| Run summary | `/tmp/phase11-live-summary.log` |

---

*Pre-operator pre-fill generated 2026-06-14 by Plan 11-03 Task 3 (worktree-agent-ad234f93b83ad32ab, commit `71bf201`). Task 4 will finalise the frontmatter after operator approval; Task 5 will produce the closure atomic commit + SUMMARY.*
