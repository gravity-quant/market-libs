# Phase 17: Final Live Re-verification × 4 (LIVE-03) - Context

**Gathered:** 2026-06-24 (assumptions mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

LIVE-01-equivalent live re-verification gate run AFTER the v1.2 migrations (Phase 14 IOL
disk persistence + Phase 15 driver migration to `Client()`/`AsyncClient()`). Phase 16
(codegen) was DROPPED per SPIKE-005 NO-GO — there is NO codegen prerequisite.

The phase confirms that an operator running `main_*.py --live × 4` post-migration finds
no new findings outside the in-cycle classified set vs baseline `verification-cycle-2026-Q2`
+ v1.1 LIVE-01 head `71bf201`, and lands the v1.2 milestone-closure truths (cycle-closure
markers, traceability flip, integration audit). It does NOT add new client capabilities,
does NOT re-open terminal findings, and does NOT perform the PR/merge ship.

Scope: 4 verifiable packages — ambito / iol / higyrus / matriz. Out of scope (carried from
the cycle): wallets-client (stub), matriz prod (remarkets sandbox only), matriz async/WS live.
</domain>

<decisions>
## Implementation Decisions

### Gate execution & SKIP disposition
- **D-01:** This phase is operator-driven (`autonomous: false`). The operator provisions live
  credentials in per-package `.env` files, runs each `main_*.py` live (sequentially; the
  aggregate `main_verify.py` runner is the cross-check, not the sole vehicle), and captures
  operator dispositions in a `17-VALIDATION.md` mirroring the Phase 11 LIVE-01 structure.
- **D-02:** A package that SKIPs (missing creds, market closed, sandbox unavailable) is
  dispositioned as a **documented EXPECTED exception** carrying forward the cycle's existing
  out-of-scope policy — a SKIP does NOT block the gate and does NOT fail the milestone. The
  disposition must be explicitly recorded so Success Criterion #1 ("dispositions captured for
  all 4 packages") is met even when a package SKIPs. (Note: ámbito needs no auth and will RUN
  even with no `.env`; iol/higyrus/matriz SKIP without provisioned credentials.)

### Phase scope boundary — gate + closure, not ship
- **D-03:** The phase runs the live gate AND lands the v1.2 milestone-closure truths:
  cycle-closure markers updated, `verify_cycle_closure × 4` PASS, schema snapshot comparison
  vs `verification-cycle-2026-Q2` clean, REQUIREMENTS.md traceability flipped to Complete for
  REFAC-05/SEC-01/ERG-01/LIVE-03, and a 0-BLOCKER integration audit.
- **D-04:** The phase STOPS short of the actual PR/merge. `/gsd-ship` and the milestone
  archive (`gsd-complete-milestone`) remain separate, downstream of this phase, informed by
  `17-VALIDATION.md`.

### Pre-existing OPEN findings treatment
- **D-05:** The only finding still OPEN at gate time is **iol F-01** (`missing assumed key
  'simbolo' in get_quote`). It is **re-confirmed OPEN as a documented baseline carry-forward**
  — NOT required to be resolved in this phase. (Correction to a stale brief: higyrus F-02 was
  already transitioned to terminal `NO-FIX` in Phase 9; matriz/ambito carry no OPEN findings.)
  Do NOT re-open terminal findings — `append_finding`'s human-status preservation would refuse
  the revert anyway.

### Finding-title stability verification vs baseline `71bf201`
- **D-06:** Title/probe-name stability across the Phase 15 driver migration is verified by a
  **STATIC `git diff 71bf201..HEAD`** scoped to `title=`/`fid=`/`class_=` literals in the four
  drivers — NOT a full live-data diff (live `actual=`/`diff=` bytes are non-deterministic).
  This follows Phase 15 D-06/D-07. The gate currently passes clean (drivers changed
  +584/-344 lines, zero changed title/fid/class literals).
- **D-07:** Any genuinely NEW finding surfaced live is dispositioned in-phase: classified
  CONFIRMED / FIXED / EXPECTED / NO-FIX, and for CONFIRMED/FIXED a regression test is landed in
  THIS same phase (v1.0/v1.1 in-cycle pattern). Otherwise `verify_cycle_closure` returns
  `(False, [fid])` and Success Criterion #2 fails.

### Claude's Discretion
- Exact ordering of the live runs and the precise `17-VALIDATION.md` layout are left to the
  planner, provided the Phase 11 LIVE-01 disposition structure is mirrored.

### Folded Todos
None folded.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/ROADMAP.md` (lines 206-218 — Phase 17 goal + 5 Success Criteria)
- `verification/findings.py` (append-only, BEGIN/END zone parser, human-status preservation, content-addressed title dedupe)
- `verification/cycle_report.py` (`verify_cycle_closure` — CONFIRMED/FIXED→regression-link contract)
- `verification/schema.py` (`schema_of` PII-free structural snapshot) + `verification/regen_snapshots.py`
- `verification/env_gate.py` (SKIP semantics — drivers `sys.exit(0)` on missing creds; ambito needs none)
- `main_verify.py` (aggregate runner, RAN/SKIPPED/FAILED classification, redaction)
- `.planning/verification/iol-client-findings.md`, `.planning/verification/higyrus-client-findings.md`, `.planning/verification/matriz-client-findings.md`, `.planning/verification/ambito-financiero-client-findings.md` (current disposition state + cycle-closure markers)
- `.planning/verification/CYCLE-REPORT.md` (baseline `verification-cycle-2026-Q2`, out-of-scope policy, open questions)
- `.planning/phases/15-driver-migration-4-refac-05/15-CONTEXT.md` (D-06/D-07 title-stability gate mechanics + baseline anchor `71bf201`)
- `.planning/milestones/v1.1-phases/11-harness-hardening-code-review-close-out-live-re-verification/11-03-PLAN.md` and `11-VALIDATION.md` (LIVE-01 precedent — operator-gated disposition structure to mirror)
- `.planning/REQUIREMENTS.md` (lines 143-156 — v1.2 traceability table still showing REFAC-05/SEC-01/ERG-01/LIVE-03 as `Open`; must flip to Complete for Success Criterion #4)
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `main_verify.py` — aggregate runner over all 5 drivers in isolated subprocesses; classifies
  RAN/SKIPPED/FAILED; never re-emits child stdout (redaction); `_ENV_SKIP` regex distinguishes
  missing-creds SKIP from mutation-gate SKIP.
- `verification/findings.py` — `append_finding` (append-only, content-addressed title dedupe,
  human-promoted status preservation), `new_findings`, `write_findings`. BEGIN/END auto-zones
  are byte-identical for unchanged titles → preserves v1.1 dispositions.
- `verification/cycle_report.py` — `verify_cycle_closure(pkg) -> (ok, missing_fids)` gates only
  CONFIRMED/FIXED for regression links; OPEN/EXPECTED/NO-FIX are non-gating.
- `verification/schema.py` (`schema_of`) + `regen_snapshots.py` — structural, PII-free schema
  snapshots under `.planning/verification/schemas/{pkg}/` for drift comparison.
- `verification/env_gate.py` / `mutation_gate.py` / `redaction.py` / `anonymize.py` — SKIP gating,
  mutation guard, leak-safe output.

### Established Patterns
- Operator-gated `NN-VALIDATION.md` with `autonomous: false` frontmatter (Phase 11 precedent).
- In-cycle disposition: new findings classified + regression landed in the same phase.
- Per-package `.env`; missing creds → `sys.exit(0)` SKIP, never FAILED.
- Static, title-scoped finding-stability diff vs the frozen baseline `71bf201`.

### Integration Points
- Migrated drivers (`main_iol.py`, `main_higyrus.py`, `main_matriz.py`,
  `main_ambito_financiero.py`) now construct ONE `Client()`/`AsyncClient()` per `main()` run
  (Phase 15) and feed `verification/findings.py`.
- REQUIREMENTS.md traceability table + milestone audit consume `17-VALIDATION.md` to close v1.2.
</code_context>

<specifics>
## Specific Ideas

Mirror the Phase 11 LIVE-01 `11-VALIDATION.md` disposition structure (operator frontmatter,
per-package RAN/SKIPPED + disposition, cycle-closure marker updates) for `17-VALIDATION.md`.
</specifics>

<deferred>
## Deferred Ideas

- prod-vs-remarkets matriz verification (REQUIRED handoff D-MATZ-27) — future milestone, not v1.2.
- iol F-01 `get_quote` SHAPE root-cause investigation — out of scope; stays a documented OPEN.
- higyrus F-02 sandbox account-list root cause — already terminal NO-FIX; future-milestone curiosity only.

### Reviewed Todos (not folded)
- `spike-codegen-libcst-v1.3.md` (libcst AST-level codegen for sync/async parity, match score 0.9)
  — explicitly deferred to v1.3 per Phase 12 SPIKE-005 NO-GO; unrelated to a live verification
  gate. Not folded.
</deferred>
