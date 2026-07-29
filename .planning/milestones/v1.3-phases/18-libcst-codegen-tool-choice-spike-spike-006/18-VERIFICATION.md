---
phase: 18-libcst-codegen-tool-choice-spike-spike-006
verified: 2026-07-03T12:17:10Z
status: passed
score: 10/10 must-haves verified
behavior_unverified: 0
overrides_applied: 0
gaps_remediated_in_cycle:
  - truth: "evidence-checklist.txt records a filled PASS/FAIL transcript (with exit codes) for every one of the 10 D-RIGOR-02 items"
    original_status: partial
    resolution: >
      Closed in-cycle by commit 02cb9f5. The 8 stale "Verdict: TBD (Plan 02 — 001a)" per-item lines
      (items 1,2,3,4,5,6,7,9) were overwritten with the actual PASS/FAIL + one-line rationale already
      recorded in the same file's AGGREGATE VERDICT section (item 1 FAIL, 2 PASS, 3 FAIL, 4 PASS,
      5 PASS, 6 FAIL, 7 PASS, 9 PASS). README.md frontmatter `signoff_date`/`signoff_by` synced to
      DECISION.md's signed values (2026-07-03 / sebadlf). Confirmed zero residual `TBD` markers; the
      fix is documentation-only and did not touch any experiment, transcript, or the signed decision.
---

# Phase 18: libcst Codegen Tool-Choice Spike (SPIKE-006) Verification Report

**Phase Goal:** Produce a signed GO/NO-GO decision on whether `libcst >=1.8.0,<2` (AST-level codemod)
can single-source the sync/async transport shells — evaluated against the D-RIGOR-02 10-item gate on
the ámbito canary in its v1.2-head shape (NOT migrated) plus inheritance of the matriz construct audit
+ deny-list intactness. Spike-before-plan / RESEARCH FLAG phase — the SIGNED DECISION (GO or NO-GO) is
the guaranteed deliverable; a NO-GO is a valid success, NOT a failure.

**Verified:** 2026-07-03T12:17:10Z
**Status:** passed (10/10 — the one documentation-completeness gap found at initial verification was
remediated in-cycle by commit 02cb9f5; the decision itself is sound, signed, and evidence-backed)
**Re-verification:** No — initial verification + in-cycle gap remediation

**IMPORTANT CONTEXT FOR THE READER:** This report does **not** penalize the phase for its NO-GO
verdict or for items 1/3/6 failing byte-identity/format/pytest-green — per D-04/D-08 that honest FAIL
IS the deliverable. The single gap found below is a cosmetic/audit-trail inconsistency in one evidence
file (stale placeholder text not overwritten with data that already exists correctly elsewhere in the
same file and in other artifacts) — it does not change, weaken, or cast doubt on the signed decision.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Operator holds a signed `DECISION.md` with per-item verdict for all 10 D-RIGOR-02 items | ✓ VERIFIED | `DECISION.md` frontmatter: all 10 `evidence_checklist` keys PASS/FAIL (no TBD); `decision: NO-GO`, `signoff_by: sebadlf`, `signoff_date: 2026-07-03`; "Operator Signoff" section filled |
| 2 | The 3 GO-determining items (1 byte-identical, 4 ruff-check, 6 mocked-suite-green) each have a captured PASS/FAIL transcript vs the **un-migrated** ámbito v1.2-head canary | ✓ VERIFIED | `001a/run_log.txt` — item 1: `diff` exit 1, 13 hunks/383 lines, regenerated vs CURRENT `client.py` (not stale SPIKE-005 baseline); item 4: `ruff check` exit 0 "All checks passed!"; item 6: pytest sandbox `ImportError` circular self-import transcript captured verbatim. `001a/diff_vs_current_client.txt` (383 lines) is the item-1 evidence file. |
| 3 | 8 inherited SPIKE-005 items + 2 new libcst items (9, 10) each have a recorded verdict | ✓ VERIFIED | Items 2,3,5,7,8,9,10a,10b verdicts present in `DECISION.md`, `001a/FINDING.md`, `001b/FINDING.md` (+ `verification_transcripts.txt`), `001c/FINDING.md` (+ `audit-run.log`), `001d/FINDING.md` (+ sha256 files) |
| 4 | Matriz deny-list files re-verified sha256-byte-identical pre/post — confirmed OUT of scope | ✓ VERIFIED | `sha256_before.txt`/`sha256_after.txt`: `_token_store.py`, `_refresh_policy.py`, `_refresh.py`, `ws_client.py` digests identical pre/post; `aio.py` digest differs (proves scope, not a no-op) |
| 5 | On GO: transformer drafts promoted for Phase 19. On NO-GO: REFAC-06 marked permanently shelved, milestone closes on signed NO-GO | ✓ VERIFIED | NO-GO (3 FAILs) → `NO-GO.md` present and marked EFFECTIVE; `REQUIREMENTS.md` REFAC-06 line: "PERMANENTEMENTE ARCHIVADO / DROPPED"; `ROADMAP.md` Phase 19 marked DROPPED 2026-07-03 |
| 6 | Aggregate verdict follows D-04 strictly: any item FAIL → NO-GO | ✓ VERIFIED | Items 1/3/6 FAIL, 7/10 PASS → `NO-GO` computed mechanically; no operator discretion softened a FAIL (explicit in DECISION.md "Operator Signoff": "No FAIL is softened into a GO") |
| 7 | D-SCOPE-03 24h timebox status recorded; over-cap forces AUTO-NO-GO | ✓ VERIFIED | `timebox_status: WITHIN-CAP` in `DECISION.md` frontmatter and `evidence-checklist.txt` (~28 min elapsed, well under 24h cap); NO-GO here is evidence-driven, not timebox-driven |
| 8 | Zero production footprint: no `packages/` mutation, `uv.lock` unchanged, no `.env` exposed | ✓ VERIFIED | `git diff --exit-code packages/` → exit 0 (clean); `git diff --exit-code uv.lock` → exit 0 (clean); `git status --porcelain packages/ uv.lock` empty; no `.env` reference in any spike artifact |
| 9 | CODEGEN-01 requirement traceability: present in all 3 plans' frontmatter, reconciled in REQUIREMENTS.md | ✓ VERIFIED | `requirements: [CODEGEN-01]` in `18-01-PLAN.md`, `18-02-PLAN.md`, `18-03-PLAN.md`; `REQUIREMENTS.md` traceability table: `CODEGEN-01 \| Phase 18 ... \| Complete (NO-GO signed 2026-07-03)` |
| 10 | evidence-checklist.txt records a filled PASS/FAIL transcript (with exit codes) per item | ✓ VERIFIED (remediated in-cycle) | Initially FAILED — 8 per-item sections read `Verdict: TBD`. Closed by commit 02cb9f5: the 8 per-item verdicts were synced to the file's own aggregate section (1 FAIL, 2 PASS, 3 FAIL, 4 PASS, 5 PASS, 6 FAIL, 7 PASS, 9 PASS); zero residual `TBD` confirmed. |

**Score:** 10/10 truths verified (the 1 documentation-completeness gap was remediated in-cycle; 0 present-but-behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `SPIKE-006/DECISION.md` | Signed 10-item verdict map, `decision:` GO/NO-GO, signoff | ✓ VERIFIED | All 10 keys filled, no TBD; `decision: NO-GO`; `signoff_by: sebadlf`; `signoff_date: 2026-07-03`; Operator Signoff section present |
| `SPIKE-006/evidence-checklist.txt` | Filled 10-item transcript aggregating 001a/001b/001c/001d | ✓ VERIFIED (remediated) | AGGREGATE VERDICT section correct for all 10 items; the 8 per-item sections synced to match via commit 02cb9f5 — no residual "Verdict: TBD" |
| `SPIKE-006/NO-GO.md` | NO-GO close-out — REFAC-06 permanently shelved | ✓ VERIFIED | Present, frontmatter `status: NO-GO (SIGNED — effective 2026-07-03)`, root-cause analysis + transcripts + impact section complete |
| `SPIKE-006/README.md` | Spike entry, `verdict:` updated from TBD | ✓ VERIFIED (remediated) | `verdict: NO-GO`; `signoff_date: 2026-07-03` / `signoff_by: sebadlf` synced to DECISION.md via commit 02cb9f5 |
| `001a/experiment.py` + `transformers/*.py` | Impure driver + 5 pure CSTTransformer subclasses | ✓ VERIFIED | 5 transformer files (37–66 lines each, substantive), driver present, 14 passing unit tests in `test_transformers.py` |
| `001a/output/client_generated.py` | Generated sync transport shell (item-1 subject) | ✓ VERIFIED | Present, referenced by the regenerated diff |
| `001a/diff_vs_current_client.txt` | Item-1 diff vs CURRENT (not stale) `client.py` | ✓ VERIFIED | 383 lines, dated 2026-07-02, diffed against `packages/.../client.py` (mtime 2026-06-23, i.e., current v1.2-head, not the SPIKE-005 v1.1 baseline) |
| `001b/experiment.py` + transcripts | libcst `Module.header` marker insertion + 4-command neutrality transcript | ✓ VERIFIED | `verification_transcripts.txt`: ruff check/format/mypy/ast.parse all exit 0, marker + baseline both clean |
| `001c/audit.py` + `matriz-aio-constructs.md` | Matriz construct audit, MERGE GATE PASS sentinel | ✓ VERIFIED | `audit-run.log` + `matriz-aio-constructs.md` show "Total rows: 110", "Unresolved: 0", "**MERGE GATE PASS:** zero unresolved rows." |
| `001d/experiment.py` + sha256 files | Deny-list sha256 pre/post harness | ✓ VERIFIED | `sha256_before.txt`/`sha256_after.txt` — 4 deny-list files identical, `aio.py` differs |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `DECISION.md` | `001a/FINDING.md`, `001b/FINDING.md`, `001c/FINDING.md`, `001d/FINDING.md` | per-item verdict map aggregates 4 sub-experiment findings | ✓ WIRED | Every item in `DECISION.md`'s evidence table cites its source sub-experiment; verdicts match the underlying FINDING.md files exactly |
| `DECISION.md` (verdict) | `REQUIREMENTS.md` CODEGEN-01 / REFAC-06 | NO-GO shelves REFAC-06 permanently | ✓ WIRED | `REQUIREMENTS.md` CODEGEN-01 marked resolved-NO-GO, REFAC-06 marked "PERMANENTEMENTE ARCHIVADO / DROPPED", citing `sebadlf 2026-07-03` and the same 7 PASS/3 FAIL breakdown |
| `001c-matriz-construct-audit/audit.py` | `packages/matriz-client/src/matriz_client/aio.py` | `SOURCE` constant points at current matriz aio.py (959 LOC) | ✓ WIRED | `audit-run.log` shows 110 rows against the current 959-LOC file; audit.py is byte-identical to SPIKE-005's verbatim copy per its own FINDING.md |
| `001d/experiment.py` | `packages/matriz-client/src/matriz_client` (sandbox copy) | `shutil.copytree` → sha256 pre/post; only `aio.py` handed to libcst | ✓ WIRED | sha256 digests confirm scope; `git diff --exit-code packages/` clean after run |
| `001a/experiment.py` | `packages/ambito-financiero-client/.../aio.py` | `cst.parse_module` reads `aio.py` as sole source, not edited | ✓ WIRED | `git diff --exit-code .../aio.py` clean (confirmed in `001a/FINDING.md` "Integrity witnesses") |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| CODEGEN-01 | 18-01, 18-02, 18-03 | Evaluate libcst as AST-level codegen tool; sign binary GO/NO-GO against D-RIGOR-02 | ✓ SATISFIED | Signed NO-GO in `DECISION.md`; `REQUIREMENTS.md` marks CODEGEN-01 "RESUELTO: NO-GO firmado"; traceability table `Complete (NO-GO signed 2026-07-03)` |

No orphaned requirements — `REQUIREMENTS.md`'s traceability table maps exactly 2 v1.3 requirements (CODEGEN-01 → Phase 18 Complete; REFAC-06 → Phase 19 DROPPED), matching the phase's declared `requirements: [CODEGEN-01]`.

### Anti-Patterns Found

| File | Line(s) | Pattern | Severity | Impact |
|------|---------|---------|----------|--------|
| `evidence-checklist.txt` | 27, 37, 48, 57, 66, 81, 90, 120 | Unreferenced `TBD` placeholder — RESOLVED by commit 02cb9f5 (per-item verdicts synced to aggregate) | ✓ Resolved | Was documentation-completeness only; no residual `TBD` remains |
| `README.md` (spike root) | 7–8 | Unreferenced `TBD` signoff fields — RESOLVED by commit 02cb9f5 (synced to DECISION.md) | ✓ Resolved | `signoff_by: sebadlf` / `signoff_date: 2026-07-03` now mirror DECISION.md |

No residual TBD/FIXME/XXX/placeholder/hardcoded-empty patterns remain in the spike deliverables (confirmed post-remediation). `001a/transformers/*.py` are substantive (37–66 LOC each, not stubs); `001a/experiment.py` runs to completion producing real output; `001c/audit.py` is a verbatim, non-trivial stdlib-`ast` walker.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Production footprint clean | `git diff --exit-code packages/` | exit 0 | ✓ PASS |
| Lockfile unchanged | `git diff --exit-code uv.lock` | exit 0 | ✓ PASS |
| No untracked mutation in packages/uv.lock | `git status --porcelain packages/ uv.lock` | empty | ✓ PASS |
| Matriz audit sentinel present | `grep 'MERGE GATE PASS' matriz-aio-constructs.md` | found, "zero unresolved rows" | ✓ PASS |
| Deny-list sha256 identity | diff of `sha256_before.txt` vs `sha256_after.txt` for the 4 deny-listed files | identical for all 4; `aio.py` differs | ✓ PASS |
| Item-8 marker neutrality | `verification_transcripts.txt` — 4 commands on marked file + 4 on baseline | all 8 exit 0 | ✓ PASS |

Not independently re-run (would require an ephemeral `uv run --with libcst` install and would not add new evidence beyond the already-captured transcripts): item-1 `diff`, item-3 `ruff format --check`, item-4 `ruff check`, item-5 `mypy --strict`, item-6 sandbox pytest, item-9 purity assertions — all have full command + exit-code transcripts already captured in `001a/run_log.txt`, cross-checked above for internal consistency against `FINDING.md` and `DECISION.md`.

### Probe Execution

Not applicable — this is a research-spike phase producing planning/decision artifacts, not a migration/tooling phase with `scripts/*/tests/probe-*.sh` conventions. No probes declared in any of the three plans.

### Human Verification Required

None. Both blocking `checkpoint:human-verify` gates in this phase were cleared: the libcst supply-chain legitimacy gate (18-01 Task 1) and the operator sign-off (18-03 Task 2, evidenced by the filled `signoff_by`/`signoff_date` in `DECISION.md` and commit `0849433`).

### Gaps Summary

The phase's actual goal — a **signed, evidence-backed GO/NO-GO decision** — is achieved. `DECISION.md`
is fully filled (all 10 items, no TBD) and operator-signed; `NO-GO.md` is effective; `REQUIREMENTS.md`
and `ROADMAP.md` governance is correctly updated; zero production footprint is confirmed by direct
`git diff` checks (not just SUMMARY.md claims); the matriz deny-list is independently re-verified
byte-identical. The 3 GO-determining items (1/4/6) and the aggregate D-04 NO-GO computation are
correct and honestly derived (no gate-softening, no `aio.py` edit, no `client.py`-donor read).

One gap was found at initial verification, confined to a single evidence-artifact's internal
completeness: `evidence-checklist.txt` showed "Verdict: TBD" in 8 of its 10 per-item sections, even
though the correct PASS/FAIL was already recorded (a) in the same file's own aggregate section, (b) in
`001a/run_log.txt`'s full transcripts, and (c) in the signed `DECISION.md`; and `README.md`'s
`signoff_date`/`signoff_by` frontmatter fields were not synced to the signed values.

**This gap was remediated in-cycle (commit 02cb9f5)** — the 8 per-item verdict lines were overwritten
with the actual PASS/FAIL already stated in the aggregate section, and `README.md`'s signoff fields were
synced to `DECISION.md` (`sebadlf` / `2026-07-03`). Zero residual `TBD` markers were confirmed, and the
fix was documentation-only (no experiment re-run, no change to the signed decision). Final score: 10/10.

---

*Verified: 2026-07-03T12:17:10Z*
*Verifier: Claude (gsd-verifier)*
