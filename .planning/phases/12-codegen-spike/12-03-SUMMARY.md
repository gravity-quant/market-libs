---
phase: 12-codegen-spike
plan: 03
status: in_progress_at_checkpoint
wave: 5
tasks_completed: [12-03-01]
tasks_pending: [12-03-02, 12-03-03, 12-03-04a, 12-03-04b]
checkpoint_type: decision
checkpoint_task: 12-03-02
files_created:
  - .planning/spikes/SPIKE-005-codegen-tool-choice/evidence-checklist.txt
  - .planning/spikes/SPIKE-005-codegen-tool-choice/DECISION.md
files_modified: []
evidence_checklist:
  item_1_byte_identical_ambito: FAIL
  item_2_b8_identity: PASS
  item_3_ruff_format_check: PASS
  item_4_ruff_check: FAIL
  item_5_mypy_strict: PASS
  item_6_ambito_pytest_green: FAIL
  item_7_lint_imports: PASS
  item_8_marker_future_compat: PASS
items_pass: 5
items_fail: 3
matriz_audit_unresolved_rows: 0
timebox_status: WITHIN-CAP
strict_d_rigor_01_verdict: NO-GO
recipe_2_classified_verdict: GO_with_phase_16_source_migration_prerequisite
recommended_verdict: GO_with_phase_16_source_migration_prerequisite
commits:
  - 30791d6  # test(12-03): D-RIGOR-01 8-item evidence collection + DECISION.md draft
duration_seconds_so_far: ~360
completed: TBD  # plan is paused at checkpoint 12-03-02
requirements: [REFAC-06]
tags: [spike, codegen, evidence-checklist, decision-draft, checkpoint, phase-12, wave-5]
---

# Phase 12 Plan 03 (PARTIAL): Codegen Spike Wave 5 — Evidence Checklist + DECISION.md Draft

**One-liner (partial run):** Task 12-03-01 complete — D-RIGOR-01 8-item evidence checklist
re-run against current spike artifacts (3 FAIL / 5 PASS under strict reading; all 3 FAILs
trace to a single root cause: aio.py not yet shaped for codegen-friendly direction, Recipe-2
class 1/2/4 only, zero NO-GO triggers); DECISION.md draft composed with `decision: TBD` plus
recommended verdict body (GO with Phase 16 source-migration prerequisite, ~30 LOC of aio.py
edits); plan **PAUSED at Task 12-03-02 operator GO/NO-GO checkpoint**. A continuation agent
will resume after operator signoff to execute Task 12-03-03 (GO branch) or Tasks 12-03-04a +
12-03-04b (NO-GO branch).

## Status

**Plan 12-03 is paused at Task 12-03-02 (checkpoint:decision).** This SUMMARY.md is a partial
run record; the FINAL Plan 03 SUMMARY (status: complete) will be produced by the continuation
agent that resumes after operator signoff.

The continuation agent MUST overwrite this file at the end of the GO or NO-GO branch with
the full Plan 03 SUMMARY (covering all 4 tasks).

## Task 12-03-01 — Completed

**Action:** D-RIGOR-01 8-item evidence collection + 1-day timebox check + draft DECISION.md.

**Artifacts produced:**

- `.planning/spikes/SPIKE-005-codegen-tool-choice/evidence-checklist.txt` — full re-run transcript
  of all 8 D-RIGOR-01 items + TIMEBOX CHECK + AGGREGATE VERDICT (Final: NO-GO under strict reading).
- `.planning/spikes/SPIKE-005-codegen-tool-choice/DECISION.md` — draft with `decision: TBD`
  frontmatter + 8 evidence_checklist subkeys + matriz_audit_unresolved_rows: 0 + timebox_status:
  WITHIN-CAP + recommended_verdict: GO_with_phase_16_source_migration_prerequisite + body with
  Evidence Checklist Summary table, Decision placeholder, Per-Package Rule Config Drafts × 4
  (ámbito verified, matriz audited, iol/higyrus inferred per D-SCOPE-01), Phase 16 Production
  Integration Recommendation (marker syntax, pre-commit hook, Makefile codegen + codegen-check
  targets, CI lint-codegen job sketch, pyproject.toml dev-dep addition), Routing After Signoff
  section (GO → Task 12-03-03; NO-GO → 12-03-04a + 12-03-04b).

**Commit:** 30791d6 — `test(12-03): D-RIGOR-01 8-item evidence collection + DECISION.md draft`.

### Item-by-item evidence

| # | Item | Status | Notes |
|---|------|--------|-------|
| 1 | Byte-identical round-trip ámbito | **FAIL** | 10 hunks; Recipe-2 classification: 7 class 4 + 2 class 1 + 1 semantic-consistent-extension; 0 class-3 NO-GO triggers |
| 2 | B8 identity preserved | **PASS** | `mod._raise_for_response is aio._raise_for_response is _core.raise_for_response` — all id `0x10694ade0`; assertion exit 0 |
| 3 | `uv run ruff format --check` clean | **PASS** | "1 file already formatted", exit 0 |
| 4 | `uv run ruff check` clean | **FAIL** | 1 I001 import-order error (Recipe-2 class 1 cosmetic, inherited from hunk H3); 0 ASYNC1xx hits |
| 5 | `uv run mypy --strict` clean | **PASS** | "Success: no issues found in 1 source file" (workspace venv resolves; 001b's spike-location import-not-found noise does not surface under canonical D-RIGOR-01 invocation) |
| 6 | Ámbito mocked suite green vs generated | **FAIL** | Circular import at collection — `from ambito_financiero_client.client import _validate_max_retries` (Recipe-2 class 4 H4/H5 inherent-asymmetry); ~5 LOC source migration in Phase 16 eliminates |
| 7 | `uv run lint-imports` 4 contracts intact | **PASS** | 4 kept, 0 broken (4× `_core does not depend on transport modules`) |
| 8 | `@generated` marker × `from __future__` | **PASS** | Marker grammar-neutral (PEP 263/PEP 236); ast.parse exit 0; ruff format exit 0; ruff check exit 1 only by line-shift of inherited I001 |

### Timebox check

| Property | Value |
|----------|-------|
| Method | `stat -f %m` on `SPIKE-005-codegen-tool-choice/README.md` (Plan 01 Task 12-01-02 created it) vs `date +%s` |
| README.md mtime | 1781468506 (Sun Jun 14 17:21:46 -03 2026) |
| Now | 1781468731 (Sun Jun 14 17:25:31 -03 2026) |
| Elapsed | 225 seconds = 0h 3m (this worktree) |
| Cumulative (Plans 01+02 per SUMMARY frontmatter `duration_seconds`) | 610 + 540 = 1150 sec ≈ 19 min wall-clock |
| Cap (D-SCOPE-03) | 24h (86400s) |
| Status | **WITHIN-CAP** |

### Aggregate

- Items PASS: 5/8
- Items FAIL: 3/8 (items 1, 4, 6 — ALL trace to a single root cause: aio.py source-of-truth shape vs codegen-friendly shape)
- Matriz audit unresolved rows: 0 (D-SCOPE-02 satisfied; 001c MERGE GATE PASS sentinel present)
- Timebox status: WITHIN-CAP

**Strict D-RIGOR-01 verdict:** Final: NO-GO (any FAIL → NO-GO per D-RIGOR-01 protocol).
**Recipe-2-classified verdict (informative):** GO with Phase 16 source-migration prerequisite.

## Task 12-03-02 — Checkpoint (PAUSED)

**Type:** `checkpoint:decision`
**Gate:** blocking
**Awaiting:** operator GO/NO-GO signoff on DECISION.md

The operator must review:

1. `.planning/spikes/SPIKE-005-codegen-tool-choice/evidence-checklist.txt` — full transcript.
2. `.planning/spikes/SPIKE-005-codegen-tool-choice/DECISION.md` — draft with recommended verdict
   body + per-package Rule config drafts + Phase 16 integration sketch.
3. The 4 sub-experiment FINDING.md files (001a/b/c/d).

**Resume signal expected:** `(GO|NO-GO) YYYY-MM-DD <operator-name>`.

Per the decision artifact:

- **GO** → commits to Phase 16 in v1.2 with a source-migration prerequisite (~30 LOC of aio.py
  edits per 001a/FINDING.md). Next agent runs Task 12-03-03 (wrap-up Skill + CLAUDE.md auto-load +
  12-SUMMARY.md GO).
- **NO-GO** → defers REFAC-06 to v1.3, drops Phase 16 from v1.2. Next agent runs Tasks 12-03-04a
  (NO-GO.md + libcst pending todo + Skill NO-GO flavor + MANIFEST flip) then 12-03-04b
  (REQUIREMENTS.md + ROADMAP.md + CLAUDE.md auto-load + 12-SUMMARY.md NO-GO).

## Anti-Pitfall Compliance (in this partial run)

- **Anti-Pitfall 1 (timebox slip):** addressed via the TIMEBOX CHECK section in
  evidence-checklist.txt. Both the mtime-based check (0h 3m elapsed in this worktree) and the
  cumulative wall-clock from Plans 01+02 SUMMARY frontmatter (~19 min) are well under the 24h
  cap. NO-GO auto-trigger is NOT activated by timebox.
- **Anti-Pitfall 2 (spike creeping into packages/):** verified after the commit via
  `git status --porcelain packages/ | wc -l` returning 0. Item 6 used the `mktemp -d` sandbox
  recipe (Anti-Pitfall 2 compliance): copied ámbito-financiero-client + verification/ + main_*.py
  + pyproject.toml + uv.lock + the other 4 packages into `/tmp/spike-005-ambito-test-*`, overwrote
  the sandbox client.py with client_generated.py, ran pytest from the sandbox. Sandbox cleaned up
  at task end (`rm -rf /tmp/spike-005-ambito-test-*` returns zero matching dirs).
- **Anti-Pitfall 4 (B8 skip):** B8 identity assertion re-executed inline against the spike's
  generated file via importlib + `is` chain check; PASS confirmed at id `0x10694ade0` (matches
  001a Step 6 modulo process-restart memory layout).
- **Anti-Pitfall 5 (matriz audit TBD soft-relax):** confirmed via 001c/FINDING.md MERGE GATE
  PASS sentinel + audit-run.log + grep gate. The audit's classifier resolved every row
  deterministically — zero REVIEW, zero TBD, zero DENY-LIST-VIOLATION.

## Deviations from Plan

### Auto-resolved (none — Task 12-03-01 executed as planned)

No Rule 1/2/3 deviations occurred during this task. The plan's recipe (Step 1–5) was followed
verbatim:
- Step 1 (timebox check via `stat -f %m`): executed; status WITHIN-CAP.
- Step 2 (build evidence-checklist.txt with 8 sections): executed; each item has a re-run
  command, exit code, verdict, and source artifact pointer.
- Step 3 (TIMEBOX CHECK + AGGREGATE VERDICT blocks): executed; Final: NO-GO present.
- Step 4 (draft DECISION.md): executed with frontmatter `decision: TBD` + 8 evidence_checklist
  subkeys + body sections.
- Step 5 (Recommended decision line): executed in DECISION.md `## Recommendation` section
  (advisory: GO with Phase 16 source-migration prerequisite).

### Documented (informational)

**1. Item 5 (`mypy --strict`) PASS in canonical D-RIGOR-01 invocation despite 001b/FINDING.md
recording a per-command exit 1 in its standalone-file context.**

- 001b's transcript captured `mypy --strict` exit 1 because the marker test invoked mypy on a
  spike-location file outside the workspace package path; mypy could not resolve the
  `ambito_financiero_client` package and emitted 3× import-not-found errors.
- In the canonical D-RIGOR-01 invocation (`uv run mypy --strict <generated>` from the worktree
  root with the workspace venv synced), mypy resolves the workspace package and the file
  type-checks clean. Item 5 PASS is the correct verdict for D-RIGOR-01.
- This is informational — 001b's PASS verdict was on the marker-neutral delta (line-shift only,
  no new diagnostics), not on absolute mypy exit code. The two readings are consistent.

**2. Operational pre-gate caveat from Plan 01 (mypy + pre-commit tech debt in `tests/` and
`verification/`) — to be carried forward into the final Plan 03 SUMMARY by the continuation
agent.**

Per Plan 01 SUMMARY's "Operator pre-gate response" section, the operator pre-resolved Task
12-01-01 with an approved-with-caveat status: known v1.1 tech debt isolated to `tests/` and
`verification/` (NOT shipped library code under `src/`, NOT 3.13-specific). The follow-up
quick-task `mypy-precommit-v1.1-techdebt` is to be created AFTER Phase 12 completes (not before).
The continuation agent that writes the final Plan 03 SUMMARY MUST include this caveat in the
SUMMARY's deviations section and reference it in 12-SUMMARY.md (Plan 03 Task 12-03-03 GO branch
or 12-03-04b NO-GO branch).

## Self-Check (partial run)

Verified before returning to orchestrator.

- [x] `.planning/spikes/SPIKE-005-codegen-tool-choice/evidence-checklist.txt` exists.
- [x] evidence-checklist.txt has 8 D-RIGOR-01 sections (`grep -cE '^=== D-RIGOR-01 item [1-8]:'` → 8).
- [x] evidence-checklist.txt has TIMEBOX CHECK + AGGREGATE VERDICT sections.
- [x] evidence-checklist.txt has `Final: (GO|NO-GO)$` line (NO-GO under strict reading).
- [x] `.planning/spikes/SPIKE-005-codegen-tool-choice/DECISION.md` exists.
- [x] DECISION.md has `^spike: 005$` + `^decision: TBD$` + `^timebox_status: WITHIN-CAP$` frontmatter lines.
- [x] DECISION.md has body sections: Evidence Checklist Summary, Decision (TBD placeholder),
      Per-Package Rule Config Drafts × 4, Phase 16 Production Integration Recommendation,
      Routing After Signoff, Linkage.
- [x] `git status --porcelain packages/ | wc -l` returns 0 (Anti-Pitfall 2 verified).
- [x] `/tmp/spike-005-ambito-test-*` sandbox dirs cleaned (`ls` returns empty).
- [x] Commit 30791d6 visible in `git log --oneline`.
- [x] No modifications to STATE.md or ROADMAP.md (worktree mode + objective explicitly forbids).

## Next Steps

→ **Task 12-03-02 (operator signoff checkpoint) — PAUSED.** Orchestrator surfaces:

  1. evidence-checklist.txt
  2. DECISION.md draft
  3. 4 sub-experiment FINDING.md files

  to the operator and captures `(GO|NO-GO) YYYY-MM-DD <operator-name>`.

→ **Continuation agent** (spawned by orchestrator after operator signoff):

  - Apply signoff to DECISION.md frontmatter (decision + signoff_date + signoff_by + phase_16_status).
  - Flip SPIKE-005 README.md frontmatter verdict + MANIFEST.md SPIKE-005 row Verdict column.
  - If GO: run Task 12-03-03 (wrap-up Skill + CLAUDE.md auto-load + 12-SUMMARY.md GO).
  - If NO-GO: run Task 12-03-04a (NO-GO.md + pending todo + Skill NO-GO flavor + MANIFEST flip)
    then Task 12-03-04b (REQUIREMENTS.md + ROADMAP.md + CLAUDE.md auto-load + 12-SUMMARY.md NO-GO).
  - Overwrite THIS partial SUMMARY with the final Plan 03 SUMMARY covering all 4 tasks.

## Self-Check: PASSED (for Task 12-03-01 only — checkpoint pending)
