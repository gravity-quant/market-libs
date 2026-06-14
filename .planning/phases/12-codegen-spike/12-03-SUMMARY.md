---
phase: 12-codegen-spike
plan: 03
status: complete
wave: "5+6"
tasks_completed: [12-03-01, 12-03-02, 12-03-04a, 12-03-04b]
tasks_skipped: [12-03-03]
checkpoint_type: decision
checkpoint_resolved_at: 12-03-02
decision: NO-GO
signoff_date: 2026-06-14
signoff_by: sebadlf
phase_16_status: DROPPED
phase_17_status: UNBLOCKED
files_created:
  - .planning/spikes/SPIKE-005-codegen-tool-choice/NO-GO.md
  - .planning/todos/pending/spike-codegen-libcst-v1.3.md
  - .claude/skills/spike-findings-codegen-market-libs/SKILL.md
  - .claude/skills/spike-findings-codegen-market-libs/references/unasync-failure-mode.md
  - .claude/skills/spike-findings-codegen-market-libs/references/matriz-construct-audit.md
  - .claude/skills/spike-findings-codegen-market-libs/references/libcst-v1.3-exploration-path.md
  - .claude/skills/spike-findings-codegen-market-libs/references/codegen-pitfalls.md
  - .claude/skills/spike-findings-codegen-market-libs/sources/001a-ambito-round-trip-FINDING.md
  - .claude/skills/spike-findings-codegen-market-libs/sources/001b-ambito-marker-future-compat-FINDING.md
  - .claude/skills/spike-findings-codegen-market-libs/sources/001c-matriz-construct-audit-FINDING.md
  - .claude/skills/spike-findings-codegen-market-libs/sources/001d-matriz-deny-list-config-FINDING.md
  - .claude/skills/spike-findings-codegen-market-libs/sources/evidence-checklist.txt
  - .claude/skills/spike-findings-codegen-market-libs/sources/DECISION.md
files_modified:
  - .planning/spikes/SPIKE-005-codegen-tool-choice/DECISION.md
  - .planning/spikes/SPIKE-005-codegen-tool-choice/README.md
  - .planning/spikes/MANIFEST.md
  - .planning/REQUIREMENTS.md
  - .planning/ROADMAP.md
  - CLAUDE.md
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
final_verdict: NO-GO
defer_to_milestone: v1.3
defer_to_pending_todo: .planning/todos/pending/spike-codegen-libcst-v1.3.md
commits:
  - 30791d6  # test(12-03): D-RIGOR-01 8-item evidence collection + DECISION.md draft (Task 12-03-01)
  - 3ab69a9  # docs(12-03): partial SUMMARY — Task 12-03-01 complete, checkpoint pending at 12-03-02 (now overwritten by this final)
  - 98c128c  # docs(12-03): operator signs NO-GO on SPIKE-005 DECISION.md (Task 12-03-02 resolution)
  - 7f90099  # docs(12-03-04a): SPIKE-005 NO-GO close-out — spike-local artifacts
  - TBD      # docs(12-03-04b): SPIKE-005 NO-GO project-state close-out (this commit)
duration_seconds: ~720
duration_minutes: ~12
completed: 2026-06-14
requirements: [REFAC-06]
tags: [spike, codegen, NO-GO, evidence-checklist, decision, libcst-handoff, phase-12, wave-5-6, FINAL]
---

# Phase 12 Plan 03 (FINAL): Codegen Spike Wave 5 + 6 Summary — NO-GO Close-Out

**One-liner:** Plan 12-03 close-out complete — D-RIGOR-01 8-item evidence checklist
re-run (5 PASS / 3 FAIL under strict reading; all 3 FAILs trace to single source-shape
asymmetry, Recipe-2 class 1/2/4 only, ZERO unfixable class-3 hunks); operator signed
**NO-GO** under strict D-RIGOR-01 on 2026-06-14; Task 12-03-03 (GO branch) SKIPPED per
precondition; Tasks 12-03-04a (spike-local artifacts: NO-GO.md + v1.3 libcst pending
todo + `spike-findings-codegen-market-libs` Skill + MANIFEST flip) and 12-03-04b
(project-state governance: REQUIREMENTS.md REFAC-06 deferred to v1.3, ROADMAP.md Phase
16 DROPPED + Phase 17 unblocked, CLAUDE.md auto-load Skill bullet) executed; REFAC-06
defers to v1.3 with dedicated libcst spike per D-NOGO-01; Phase 16 DROPPED from v1.2
schedule; Phase 17 (LIVE-03) unblocked to run immediately after Phases 14 + 15.

## Decision

**NO-GO** — signed 2026-06-14 by sebadlf under strict D-RIGOR-01 reading.

| Metric | Value |
|--------|-------|
| Evidence items PASS | 5 / 8 (items 2, 3, 5, 7, 8) |
| Evidence items FAIL | 3 / 8 (items 1, 4, 6 — all source-shape asymmetry) |
| Matriz audit unresolved rows | 0 (D-SCOPE-02 satisfied) |
| Timebox status | WITHIN-CAP (~19 min cumulative; 24h cap) |
| Recipe-2 class-3 (unfixable) hunks | 0 |
| Strict D-RIGOR-01 verdict | NO-GO |
| Recipe-2-classified verdict (informative) | GO with Phase 16 source-migration prerequisite |
| Operator signoff | NO-GO (strict reading honored; libcst exploration deferred to v1.3 per D-NOGO-01) |

## Tasks Executed

### Task 12-03-01 — Evidence checklist + DECISION.md draft (commit `30791d6`)

Re-ran 8 D-RIGOR-01 items end-to-end:

| # | Item | Status | Notes |
|---|------|--------|-------|
| 1 | Byte-identical round-trip ámbito | **FAIL** | 10 hunks; Recipe-2: 7 class 4 + 2 class 1 + 1 semantic-consistent-extension; 0 class-3 NO-GO triggers |
| 2 | B8 identity preserved | **PASS** | `mod._raise_for_response is aio._raise_for_response is _core.raise_for_response` — all id 0x10694ade0; exit 0 |
| 3 | `uv run ruff format --check` clean | **PASS** | "1 file already formatted"; exit 0 |
| 4 | `uv run ruff check` clean | **FAIL** | 1 I001 import-order error (Recipe-2 class 1 cosmetic, inherited from hunk H3); 0 ASYNC1xx hits |
| 5 | `uv run mypy --strict` clean | **PASS** | "Success: no issues found in 1 source file" (canonical workspace-venv invocation) |
| 6 | Ámbito mocked suite green vs generated | **FAIL** | Circular import at collection — `from <pkg>.client import _validate_max_retries`; ~5 LOC Phase 16 source migration would fix |
| 7 | `uv run lint-imports` 4 contracts intact | **PASS** | 4 kept, 0 broken |
| 8 | `@generated` marker × `from __future__` | **PASS** | Marker grammar-neutral (PEP 263 / PEP 236); ast.parse PASS |

DECISION.md draft composed with `decision: TBD` + 8 evidence_checklist subkeys +
recommended verdict body (advisory: GO with Phase 16 source-migration prerequisite) +
per-package Rule config drafts × 4 + Phase 16 integration sketch.

### Task 12-03-02 — Operator signoff (commit `98c128c`)

Operator signed **NO-GO** on 2026-06-14 under strict D-RIGOR-01 reading (3 of 8 items
FAIL → any FAIL → NO-GO per protocol). DECISION.md frontmatter updated: `decision: NO-GO`,
`signoff_date: 2026-06-14`, `signoff_by: sebadlf`, `phase_16_status: DROPPED`. DECISION.md
body updated with operator signoff section (rationale: honor strict gate, defer libcst to
v1.3 per D-NOGO-01). SPIKE-005 README.md frontmatter `verdict: TBD` → `verdict: NO-GO` +
signoff date/by. MANIFEST.md flip handled in Task 12-03-04a (where it logically belongs
per WARNING #5 split).

### Task 12-03-03 — SKIPPED (precondition not met)

Per precondition in 12-03-PLAN.md: this task only runs if `decision: GO`. With NO-GO
signed, the task SKIPPED. Documented here for trace completeness. The GO branch
artifacts (`spike-findings-codegen-market-libs` SKILL.md GO flavor) are NOT produced; the
NO-GO flavor is produced in Task 12-03-04a instead.

### Task 12-03-04a — Spike-local NO-GO close-out (commit `7f90099`)

Spike-local artifacts (no project-state governance edits):

- **NO-GO.md** — root cause analysis: 3 of 8 items FAIL (1 byte-identical, 4 ruff check,
  6 ámbito pytest); all trace to source-shape asymmetry (aio.py authored sync-first in
  v1.1 Phase 7, codegen direction is async-first); 0 Recipe-2 class-3 hunks. What was
  learned: B8 PASS, marker PASS, matriz audit PASS, deny-list PASS. v1.3 libcst handoff
  scope captured.
- **`.planning/todos/pending/spike-codegen-libcst-v1.3.md`** — v1.3 libcst spike pending
  todo with frontmatter (target_milestone: v1.3, priority: high, area: codegen) + scope
  (libcst CSTTransformer pattern) + validation target (~30 LOC ámbito source-migration
  sketch from 001a/FINDING.md) + inherited evidence (B8, marker, matriz audit,
  deny-list) + D-RIGOR-02 8+2 item gate proposal + acceptance criteria.
- **MANIFEST.md** — SPIKE-005 row verdict TBD → ✗ NO-GO with footnote pointing to
  NO-GO.md + v1.3 pending todo + Skill.
- **`.claude/skills/spike-findings-codegen-market-libs/`** — NEW Skill (NO-GO flavor)
  with SKILL.md (auto-load description + context/requirements/findings_index/
  integration_blueprint/metadata sections) + 4 references/ files
  (unasync-failure-mode.md, matriz-construct-audit.md, libcst-v1.3-exploration-path.md,
  codegen-pitfalls.md) + 6 sources/ files (4 sub-experiment FINDINGs + evidence-checklist.txt
  + DECISION.md for self-contained reference).

### Task 12-03-04b — Project-state governance NO-GO close-out (this commit)

Project-state governance edits (NOT spike-local):

- **`.planning/REQUIREMENTS.md`** — REFAC-06 entry REMOVED from v1.2 active
  ("Arquitectura sync/async dedup (REFAC)" section); ADDED as first bullet to "Future
  Requirements (Defer to v1.3+)" with full deferral rationale + links to NO-GO.md and
  v1.3 pending todo. Traceability table: REFAC-06 row → `Defer to v1.3` / `Deferred
  (Phase 12 NO-GO 2026-06-14)`. Coverage line updated: 4/5 requirements mapped to v1.2
  phases (REFAC-05, SEC-01, ERG-01, LIVE-03); REFAC-06 deferred. Milestone goal at top
  updated to remove "codegen single-source" from v1.2 scope; references Phase 12 NO-GO.
  Removed orphaned "libcst AST-level rewrites" entry from Future Requirements (now
  superseded by the explicit REFAC-06 deferred entry).
- **`.planning/ROADMAP.md`** — Summary checklist Phase 12 row marked [x] complete
  (NO-GO); Phase 16 row strikethrough with "DROPPED per Phase 12 NO-GO 2026-06-14;
  REFAC-06 deferred to v1.3"; Phase 17 row appended "Unblocked early per SPIKE-005 NO-GO
  2026-06-14 — runs immediately after Phases 14 + 15 with no Phase 16 gate". Phase 16
  detailed subsection rewritten: "Status: DROPPED" + root cause + links. Phase 17
  detailed subsection updated with unblocked note. Progress table: Phase 12 row → 3/3
  Complete (NO-GO) 2026-06-14; Phase 16 row → DROPPED 2026-06-14; Phase 17 row → "Not
  started (unblocked)".
- **`CLAUDE.md`** — Auto-loaded Knowledge section: added new bullet for
  `Skill("spike-findings-codegen-market-libs")` with NO-GO context.
- **`12-03-SUMMARY.md`** (THIS FILE) — overwrites the partial SUMMARY at commit `3ab69a9`
  with full 4-task coverage + final verdict + signoff + all carry-forwards.
- **`12-SUMMARY.md`** (Phase-level, NOT plan-level) — operator-readable phase close-out
  covering all 3 plans of Phase 12; produced in this same commit per Task 12-03-04b
  scope.

## Inherited Operator Pre-Gate Caveat (from 12-01-SUMMARY)

Per Plan 01 SUMMARY's "Operator pre-gate response" section, Task 12-01-01 (operational
pre-gate, CI 3.13 confirmation) was pre-resolved with **approved-with-caveat** status:

- **Test matrix CI**: GREEN on Python 3.12 + 3.13 across all 5 packages on `a9c24aa`
  (origin/main HEAD, post-v1.1-archive); 10/10 jobs pass. Anti-Pitfall 17 satisfied at
  test-matrix level — any 3.13 break during v1.2 is unambiguously v1.2-attributable.
- **Known v1.1 tech debt isolated under `tests/` and `verification/`** (NOT shipped library
  code under `src/`, NOT 3.13-specific):
  - mypy RED with 6 errors, all in `packages/matriz-client/tests/`:
    - `test_core.py:375-377`: 3× unused `type: ignore[list-item]` (mypy version drift).
    - `test_async_auth.py:223-224`: 2× `Module "matriz_client.aio" does not explicitly
      export attribute "_raise_for_response"` (PEP 562 shim).
    - `test_async_auth.py:245`: 1× unused `type: ignore[attr-defined]` for `_does_not_exist`.
  - pre-commit hooks RED — ruff format auto-fixes applied to
    `verification/test_retry_401_reauth.py` (assertion-message line-wrapping) not committed
    in v1.1.

**Operator decision (carried forward):** Tracked as follow-up quick-task
`mypy-precommit-v1.1-techdebt` to be created AFTER Phase 12 completes (now ripe for
creation — Phase 12 is closed). Captured here in the FINAL 12-03-SUMMARY and again in
12-SUMMARY.md so the next phase planner picks it up as a pending action.

## Anti-Pitfall Compliance

- **Anti-Pitfall 1 (timebox slip):** addressed — cumulative ~19 min wall-clock across
  Plans 01 + 02 + 03 (well under D-SCOPE-03 24h cap). NO-GO auto-trigger NOT activated by
  timebox; operator signed NO-GO on strict D-RIGOR-01 reading, not timebox overrun.
- **Anti-Pitfall 2 (spike creeping into `packages/`):** verified after every commit via
  `git status --porcelain packages/ | wc -l` returning 0. Zero mutations under
  packages/ across all 4 task commits in Plan 03 (DECISION.md signoff, 12-03-04a, 12-03-04b).
- **Anti-Pitfall 4 (B8 skip):** B8 identity assertion re-executed in evidence-checklist
  item 2 — PASS at id 0x10694ade0.
- **Anti-Pitfall 5 (matriz audit TBD soft-relax):** confirmed via 001c/FINDING.md MERGE
  GATE PASS sentinel + audit-run.log + grep gate (0 unresolved). Audit classifier
  resolves every row deterministically — soft-relax is impossible.
- **Anti-Pitfall 6 (matriz deny-list breach):** confirmed via 001d/FINDING.md — 4 of 4
  deny-listed files sha256-byte-identical pre/post simulated codegen run. `fpath_list`
  scope mechanism structurally sufficient.

## Deviations from Plan

### Auto-resolved (none in Plan 03 final execution)

The plan was executed exactly as specified for the NO-GO branch:

- Step 2 (DECISION.md frontmatter flip + body update + Operator Signoff section) executed
  verbatim per Task 12-03-02 acceptance criteria.
- Step 3 (Task 12-03-04a — NO-GO.md + v1.3 pending todo + MANIFEST flip + Skill) executed
  per Task 12-03-04a action steps.
- Step 4 (Task 12-03-04b — REQUIREMENTS.md + ROADMAP.md + CLAUDE.md + 12-03-SUMMARY.md +
  12-SUMMARY.md) executed per Task 12-03-04b action steps.

### Documented (informational)

**1. SPIKE-005 README.md verdict frontmatter flipped during Task 12-03-02 (DECISION
signoff commit), not Task 12-03-04a.**

Per Task 12-03-02 acceptance criteria: "SPIKE-005 README.md frontmatter `verdict:` is
flipped from `TBD` to `GO` or `NO-GO`." This was done in commit `98c128c` alongside the
DECISION.md flip, NOT in 12-03-04a. The MANIFEST.md row flip was deferred to 12-03-04a
(commit `7f90099`) per the same task's separate MANIFEST acceptance criteria, and
because the footnote linking to NO-GO.md + v1.3 todo + Skill only makes sense once those
artifacts exist (which is 12-03-04a's output). No rule deviation; this is the natural
artifact-ordering — README is a self-contained verdict marker, MANIFEST is a registry that
points to downstream artifacts.

**2. CLAUDE.md edited within the `<!-- GSD:knowledge-start -->` ... `<!-- GSD:knowledge-end -->`
sentinel block** (preserves GSD-managed section integrity for any future regeneration).

**3. Operator pre-gate caveat carry-forward.** The mypy + pre-commit v1.1 tech debt is
captured here in 12-03-SUMMARY (this file) and in 12-SUMMARY.md (phase-level). A
follow-up quick-task `mypy-precommit-v1.1-techdebt` should be created AFTER Phase 12
closes per Plan 01 SUMMARY operator decision.

## Linkage

- DECISION.md: `.planning/spikes/SPIKE-005-codegen-tool-choice/DECISION.md` (NO-GO signed)
- NO-GO.md: `.planning/spikes/SPIKE-005-codegen-tool-choice/NO-GO.md`
- v1.3 libcst pending todo: `.planning/todos/pending/spike-codegen-libcst-v1.3.md`
- Auto-loaded Skill: `.claude/skills/spike-findings-codegen-market-libs/SKILL.md`
- Evidence checklist: `.planning/spikes/SPIKE-005-codegen-tool-choice/evidence-checklist.txt`
- Sub-experiment FINDINGs: `.planning/spikes/SPIKE-005-codegen-tool-choice/001a..001d/FINDING.md`
- Phase 12 close artifact: `.planning/phases/12-codegen-spike/12-SUMMARY.md` (produced in same commit)
- v1.2 REQUIREMENTS REFAC-06 deferred: `.planning/REQUIREMENTS.md` §"Future Requirements (Defer to v1.3+)"
- v1.2 ROADMAP Phase 16 DROPPED: `.planning/ROADMAP.md` §Phase 16

## Self-Check

Verified before returning to orchestrator.

- [x] `.planning/spikes/SPIKE-005-codegen-tool-choice/DECISION.md` frontmatter:
      `decision: NO-GO`, `signoff_date: 2026-06-14`, `signoff_by: sebadlf`,
      `phase_16_status: DROPPED`.
- [x] DECISION.md has `## Operator Signoff` section with verdict + date + rationale.
- [x] `.planning/spikes/SPIKE-005-codegen-tool-choice/README.md` frontmatter
      `verdict: NO-GO` with `signoff_date` + `signoff_by`.
- [x] `.planning/spikes/SPIKE-005-codegen-tool-choice/NO-GO.md` exists with Root Cause
      Analysis section + concrete failure transcripts.
- [x] `.planning/todos/pending/spike-codegen-libcst-v1.3.md` exists with
      `target_milestone: v1.3` + libcst scope + inherited evidence references.
- [x] `.claude/skills/spike-findings-codegen-market-libs/SKILL.md` exists with
      NO-GO-flavor description + 5 body sections.
- [x] Skill has 4 references/ files + 6 sources/ files.
- [x] `.planning/spikes/MANIFEST.md` SPIKE-005 row Verdict column = `✗ **NO-GO**` with
      footnote + SPIKE-005 Forward References section appended.
- [x] `.planning/REQUIREMENTS.md`: REFAC-06 REMOVED from v1.2 active; ADDED to "Future
      Requirements (Defer to v1.3+)"; Traceability row updated to Deferred; Coverage
      line updated to 4/5 mapped.
- [x] `.planning/ROADMAP.md`: Summary checklist Phase 12 marked complete; Phase 16
      strikethrough DROPPED; Phase 17 unblocked note; Phase 16 detailed subsection
      Status: DROPPED; Progress table Phase 16 row Dropped 2026-06-14; Phase 12 row
      Complete (NO-GO) 2026-06-14.
- [x] `CLAUDE.md` `## Auto-loaded Knowledge`: new bullet for
      `Skill("spike-findings-codegen-market-libs")` added inside GSD sentinel block.
- [x] STATE.md NOT modified (orchestrator owns).
- [x] No `packages/` mutations across all 4 task commits (`git status --porcelain
      packages/ | wc -l` returns 0 after each commit).
- [x] Commits 30791d6 + 98c128c + 7f90099 visible in `git log --oneline`; final
      12-03-04b commit pending.

## Self-Check: PASSED

## Next Steps

→ **Phase 13: Cross-Package Ergonomics** (`client.with_options(max_retries=N)` × 4
packages) — `/gsd-execute-phase 13` is the natural next phase per the v1.2 ROADMAP serial
order (12 → 13 → 14 ∥ 15 → 17, with Phase 16 dropped per this NO-GO).

→ **OR Phase 17: Final Live Re-verification × 4** — `/gsd-execute-phase 17` is now
unblocked early per this NO-GO. It still requires Phases 14 + 15 complete first
(REFAC-05 driver migration + SEC-01 IOL disk persistence) before it can run, but the
Phase 16 dependency is removed.

→ **Recommended ordering:** 13 → 14 ∥ 15 → 17 (parallel 14 + 15 per ROADMAP plan, then
17 final).

→ **Follow-up quick-task to create (operator pre-gate caveat carry-forward):**
`mypy-precommit-v1.1-techdebt` — closes the known v1.1 tech debt in
`packages/matriz-client/tests/` (6 mypy errors) and `verification/test_retry_401_reauth.py`
(pre-commit auto-fix). Runs as a quick-task BEFORE the next phase planning kickoff so
v1.2 phases start from a CI-clean baseline. Plan 01 SUMMARY captured the operator's
decision to defer this until after Phase 12 closes; Phase 12 is now closed.

→ **v1.3 follow-up:** the `spike-codegen-libcst-v1.3.md` pending todo is ready for v1.3
milestone planning. When the v1.3 milestone kicks off, `/gsd-todo-promote` (or equivalent)
should surface this todo as the first codegen-related action.
