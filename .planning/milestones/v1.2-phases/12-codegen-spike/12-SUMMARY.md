---
gsd_state_version: 1.0
phase: 12
phase_name: Codegen Spike
status: complete
decision: NO-GO
spike_directory: .planning/spikes/SPIKE-005-codegen-tool-choice/
skill_produced: .claude/skills/spike-findings-codegen-market-libs/
signoff_date: 2026-06-14
signoff_by: sebadlf
next_phase: 13
phase_16_status: DROPPED
phase_17_status: UNBLOCKED
defer_to_milestone: v1.3
root_cause: "Source-shape asymmetry — aio.py authored sync-first in v1.1 Phase 7 vs unasync codegen direction async-first. 3 of 8 D-RIGOR-01 items FAIL (1 byte-identical, 4 ruff check, 6 ámbito pytest); 0 Recipe-2 class-3 (unfixable) hunks. Strict D-RIGOR-01 reading triggers NO-GO; operator honored gate per D-NOGO-01."
evidence_checklist:
  item_1_byte_identical_ambito: FAIL
  item_2_b8_identity: PASS
  item_3_ruff_format_check: PASS
  item_4_ruff_check: FAIL
  item_5_mypy_strict: PASS
  item_6_ambito_pytest_green: FAIL
  item_7_lint_imports: PASS
  item_8_marker_future_compat: PASS
matriz_audit_unresolved_rows: 0
timebox_status: WITHIN-CAP
total_duration_minutes: ~28
plans:
  - 12-01-PLAN (Wave 0 + Wave 1): bootstrap + ámbito round-trip canary
  - 12-02-PLAN (Wave 2 + 3 + 4): marker compat + matriz audit + deny-list intactness
  - 12-03-PLAN (Wave 5 + 6): evidence checklist + operator signoff + NO-GO close-out
plan_summaries:
  - .planning/phases/12-codegen-spike/12-01-SUMMARY.md
  - .planning/phases/12-codegen-spike/12-02-SUMMARY.md
  - .planning/phases/12-codegen-spike/12-03-SUMMARY.md
carry_forwards:
  pending_todos:
    - .planning/todos/pending/spike-codegen-libcst-v1.3.md
  quick_tasks_to_create:
    - name: mypy-precommit-v1.1-techdebt
      reason: "Pre-existing v1.1 tech debt isolated to tests/ + verification/ (6 mypy errors, pre-commit auto-fix). Defer-until-Phase-12-closes per operator decision in 12-01-SUMMARY; Phase 12 is now closed."
      scope: "packages/matriz-client/tests/test_core.py (3× type: ignore unused), test_async_auth.py (2× implicit_reexport, 1× type: ignore unused); verification/test_retry_401_reauth.py (ruff auto-fix line-wrap)"
requirements: [REFAC-06]
tags: [spike, codegen, NO-GO, libcst-handoff, v1.3, phase-12, FINAL]
---

# Phase 12: Codegen Spike — Summary (NO-GO)

**Decision:** NO-GO — signed 2026-06-14 by sebadlf under strict D-RIGOR-01 reading.
**Outcome:** REFAC-06 deferred to v1.3 with dedicated libcst spike per D-NOGO-01;
Phase 16 DROPPED from v1.2 schedule; Phase 17 (LIVE-03) unblocked to run immediately
after Phases 14 + 15.

## Phase Goal vs Outcome

**Goal (per ROADMAP v1.2 §"Phase 12: Codegen Spike"):** Decide whether unasync/codegen
single-source is feasible for v1.2 transport shells (`client.py`/`aio.py`) and capture
the per-package configuration the eventual Phase 16 will consume — OR return NO-GO and
defer REFAC-06 to v1.3.

**Outcome:** NO-GO. The unasync 0.6.0 token-replacement approach is structurally sound
(B8 identity preserved, marker design PEP-compliant, matriz construct audit clean,
deny-list intactness via `fpath_list` scope confirmed), but the canary round-trip on
ámbito fails the strict byte-identical contract due to source-shape asymmetry between
the v1.1-authored aio.py (sync-first; sync was primary, async mirrored) and the codegen
direction (async-first; aio.py is canonical, client.py is generated). The path to GO
under unasync would be a ~30 LOC source migration on aio.py (move
`_validate_max_retries`, alphabetize imports, normalize docstring shape, etc.) — the
operator chose to honor strict D-RIGOR-01 instead of soft-relaxing the gate, and defers
the AST-level approach (libcst, which can detect-and-rewrite source-shape asymmetries
natively) to a dedicated v1.3 spike.

## 4 Sub-Experiment Outcomes

| Sub | Name | Wave | Plan | Verdict | Key Finding |
|-----|------|------|------|---------|-------------|
| 001a | ambito-round-trip | 1 | 12-01 | **FAIL** (strict byte-identical) | 10 hunks; Recipe-2 classification: 7 class 4 (inherent asymmetry — source-shape) + 2 class 1 (cosmetic — single-line import order, constant placement; ruff format does NOT converge) + 1 semantic-consistent-extension (close() module delegator); **0 class 3 NO-GO triggers**. B8 identity PASS (`mod._raise_for_response is aio._raise_for_response is _core.raise_for_response`). Format-stable PASS. |
| 001b | ambito-marker-future-compat | 2 | 12-02 | **PASS** | `@generated` marker is grammar-neutral per PEP 263 / PEP 236; marker-neutral on all 4 verification commands (ruff check, ruff format --check, mypy --strict, ast.parse). Per-command exit codes IDENTICAL between unmarked baseline and marked file; only diff is line numbers shifted +3 by the 3-line marker block. |
| 001c | matriz-construct-audit | 3 | 12-02 | **PASS** | stdlib `ast.walk` over matriz aio.py 852 LOC enumerates 109 async-only constructs: 106 manual-sync-proof + 3 comment-only (docstring mentions at lines 42, 235, 267) + **0 REVIEW / 0 TBD / 0 DENY-LIST-VIOLATION**. D-SCOPE-02 merge gate satisfied automatically. Critical observation: matriz aio.py has ZERO bare `asyncio.<attr>` in code body — async primitives entirely encapsulated in `_token_store.py` (deny-listed). |
| 001d | matriz-deny-list-config | 4 | 12-02 | **PASS** | sha256 pre/post against simulated `unasync.unasync_files(fpath_list=[aio.py])`: 4 of 4 deny-listed files (`_token_store.py`, `_refresh_policy.py`, `_refresh.py`, `ws_client.py`) byte-identical; aio.py sha256-different (transformed). `fpath_list` scope mechanism structurally sufficient (unasync 0.6.0 has no `exclude=` param). |

**Aggregate trajectory:** 3 of 4 sub-experiments PASS unconditionally; 001a FAIL on
strict byte-identical contract has **zero NO-GO-triggering hunks** (all 10 classify as
Recipe-2 class 1, 2, or 4 — cosmetic, inherent-asymmetry, or semantic-consistent-extension).

## D-RIGOR-01 8-Item Evidence Checklist

| # | Item | Verdict |
|---|------|---------|
| 1 | Byte-identical round-trip ámbito | **FAIL** |
| 2 | B8 identity preserved on generated | **PASS** |
| 3 | `uv run ruff format --check` clean | **PASS** |
| 4 | `uv run ruff check` clean (incl. ASYNC1xx) | **FAIL** |
| 5 | `uv run mypy --strict` clean | **PASS** |
| 6 | Ámbito mocked suite green vs generated | **FAIL** |
| 7 | `uv run lint-imports` 4 contracts intact | **PASS** |
| 8 | `@generated` marker × `from __future__ import annotations` | **PASS** |

**Aggregate:**
- Items PASS: 5 / 8
- Items FAIL: 3 / 8 (items 1, 4, 6 — all source-shape asymmetry, single root cause)
- Matriz audit unresolved rows: 0 (D-SCOPE-02 satisfied)
- Timebox status: WITHIN-CAP (~19 min cumulative wall-clock; 24h cap)
- Recipe-2 class-3 (unfixable) hunks: 0

**Strict D-RIGOR-01 verdict:** NO-GO (any FAIL → NO-GO per protocol).
**Recipe-2-classified verdict (informative):** GO with Phase 16 source-migration prerequisite.
**Operator signoff:** NO-GO under strict reading (honor gate, defer libcst to v1.3 per D-NOGO-01).

## Spike Directory

**Path:** `.planning/spikes/SPIKE-005-codegen-tool-choice/`

Contents:
- `README.md` — spike entry, verdict frontmatter NO-GO.
- `DECISION.md` — operator-signed NO-GO + 8-item evidence summary + per-package Rule
  config drafts (informative — captured before signoff for reference; libcst v1.3
  analogue is per-package CSTTransformer) + Phase 16 production integration
  recommendation (informative — v1.3 inherits the marker design + pre-commit hook +
  Makefile + CI shape).
- `NO-GO.md` — root cause analysis + what was learned + v1.3 libcst handoff scope.
- `evidence-checklist.txt` — 8-item re-run transcripts.
- `001a-ambito-round-trip/` — canary FAIL, 10 hunks Recipe-2 classified.
- `001b-ambito-marker-future-compat/` — marker PASS, marker-neutral on 4 commands.
- `001c-matriz-construct-audit/` — 852 LOC audit, 109 rows 0 unresolved.
- `001d-matriz-deny-list-config/` — 4/4 deny-listed files sha256 byte-identical.

## Skill Produced

**Path:** `.claude/skills/spike-findings-codegen-market-libs/`

NO-GO flavor — auto-loaded via CLAUDE.md `## Auto-loaded Knowledge` Skill bullet. Carries
the unasync evaluation learnings into:
- v1.3 libcst spike planning (the failure modes libcst must address).
- Any future codegen revisit (the marker design, matriz construct audit, deny-list
  scope, B8 identity preservation pattern, Pitfalls 1-8 — all carry forward unchanged).

Contents:
- `SKILL.md` — auto-load description + context/requirements/findings_index/
  integration_blueprint/metadata sections.
- `references/unasync-failure-mode.md` — what unasync 0.6.0 CAN/CAN'T do; concrete
  failure transcripts.
- `references/matriz-construct-audit.md` — 109-row classification + structural
  deny-list self-enforcement observation.
- `references/libcst-v1.3-exploration-path.md` — strategic direction for v1.3 spike.
- `references/codegen-pitfalls.md` — Pitfalls 1-8 with mitigations.
- `sources/` — copies of 4 sub-experiment FINDINGs + evidence-checklist.txt +
  DECISION.md (self-contained reference).

## Operational Pre-Gate (Inherited from Plan 01)

**Status:** approved-with-caveat (pre-resolved by operator before executor was spawned).

**Caveat:** Test matrix CI on `a9c24aa` (origin/main HEAD, post-v1.1-archive) is GREEN
on Python 3.12 + 3.13 across all 5 packages (10/10 jobs pass), satisfying Anti-Pitfall 17
at the test-matrix level — any 3.13-specific break during v1.2 is unambiguously
v1.2-attributable for the test suite.

**Known v1.1 tech debt isolated under `tests/` and `verification/`** (NOT shipped library
code under `src/`, NOT 3.13-specific; should NOT block downstream phases):

- **mypy:** RED with 6 errors, all in `packages/matriz-client/tests/`:
  - `test_core.py:375-377`: 3× unused `type: ignore[list-item]` (mypy version drift).
  - `test_async_auth.py:223-224`: 2× `Module "matriz_client.aio" does not explicitly
    export attribute "_raise_for_response"` (PEP 562 shim from v1.1 Phase 10).
  - `test_async_auth.py:245`: 1× unused `type: ignore[attr-defined]`.
- **pre-commit:** RED — ruff format auto-fixes applied to
  `verification/test_retry_401_reauth.py` (assertion-message line-wrapping) not committed
  in v1.1.

**Operator decision (carried forward):** Track as follow-up quick-task
`mypy-precommit-v1.1-techdebt` — create AFTER Phase 12 closes per the operator's
decision in 12-01-SUMMARY. Phase 12 is now closed (NO-GO 2026-06-14), so this quick-task
is ripe for creation before the next phase planning kickoff (Phase 13 or directly Phase
17 — see Next Steps).

## v1.2 Roadmap Impact

| Phase | Status before Phase 12 | Status after Phase 12 NO-GO |
|-------|------------------------|------------------------------|
| 12 | Not started (research flag) | **Complete (NO-GO 2026-06-14)** |
| 13 | Not started | Not started (unchanged; next per recommended order) |
| 14 | Not started (parallel-eligible with 15) | Not started (unchanged) |
| 15 | Not started (parallel-eligible with 14) | Not started (unchanged) |
| 16 | Not started (CONDITIONAL on Phase 12) | **DROPPED (Phase 12 NO-GO)** |
| 17 | Not started (gated by Phase 16) | **Unblocked — runs after 14 + 15** |

**REQUIREMENTS.md impact:**
- REFAC-06 moved from v1.2 active → v1.2 "Future Requirements (Defer to v1.3+)".
- Traceability: REFAC-06 row → `Defer to v1.3` / `Deferred (Phase 12 NO-GO 2026-06-14)`.
- Coverage: 4/5 requirements mapped to v1.2 phases (REFAC-05, SEC-01, ERG-01, LIVE-03).

**Auto-loaded knowledge (CLAUDE.md):**
- Added: `Skill("spike-findings-codegen-market-libs")` — auto-loaded for v1.3 libcst
  spike planning + any future codegen revisit.

## Anti-Pitfall Compliance (Phase-Level)

- **Anti-Pitfall 1 (timebox slip):** cumulative ~28 min wall-clock across 3 plans
  (~10 min + ~9 min + ~9 min); well under the D-SCOPE-03 24h cap.
- **Anti-Pitfall 2 (spike creeping into `packages/`):** verified after every commit
  across all 3 plans. Zero `packages/` mutations.
- **Anti-Pitfall 4 (B8 skip):** B8 identity assertion embedded inline in 001a Step 6;
  re-executed in Plan 03 evidence checklist item 2; PASS confirmed.
- **Anti-Pitfall 5 (matriz audit TBD soft-relax):** confirmed via 001c programmatic
  merge gate (grep on REVIEW/TBD/DENY-LIST-VIOLATION returns 0); operator triage was
  not even needed because audit classifier resolves every row deterministically.
- **Anti-Pitfall 6 (matriz deny-list breach):** confirmed via 001d sha256 — 4 of 4
  deny-listed files byte-identical pre/post.
- **Anti-Pitfall 17 (CI 3.13 attribution):** addressed via operator pre-gate response
  (CI green on 3.12 + 3.13 across all 5 packages on `a9c24aa`).

## Carry-Forwards

### Pending todos (v1.3+)

- **`.planning/todos/pending/spike-codegen-libcst-v1.3.md`** — v1.3 libcst spike scope
  (the formal handoff for REFAC-06).

### Quick-tasks to create AFTER this phase closes

- **`mypy-precommit-v1.1-techdebt`** — closes the pre-gate caveat from Plan 01. Scope:
  6 mypy errors in `packages/matriz-client/tests/` (unused `type: ignore` + PEP 562
  shim re-export) + 1 pre-commit auto-fix in `verification/test_retry_401_reauth.py`.
  Run as quick-task BEFORE the next phase planning kickoff so v1.2 phases start from a
  CI-clean baseline. (Plan 01 SUMMARY captured this as the operator-deferred action.)

## Next Steps

Per the v1.2 ROADMAP (post-NO-GO):

1. **`/gsd-quick mypy-precommit-v1.1-techdebt`** — close the inherited v1.1 tech debt
   first (CI green on 3.12 + 3.13 for tests/ and verification/).
2. **`/gsd-execute-phase 13`** — Cross-Package Ergonomics (`client.with_options(max_retries=N)`).
   Natural next phase per ROADMAP serial order.
3. **`/gsd-execute-phase 14`** + **`/gsd-execute-phase 15`** in parallel (per ROADMAP
   parallel-eligible designation) — IOL disk persistence + driver migration × 4.
4. **`/gsd-execute-phase 17`** — Final live re-verification × 4 (LIVE-03). Now
   unblocked early (Phase 16 DROPPED). Runs immediately after 14 + 15 complete.

Phase 16 is permanently DROPPED from v1.2 schedule; the v1.2 milestone audit will
record this NO-GO + the v1.3 libcst defer.

For v1.3 milestone planning (future), the `spike-codegen-libcst-v1.3.md` pending todo
is ready to surface as the first codegen-related action.

## Linkage

- Plan 01 SUMMARY: `.planning/phases/12-codegen-spike/12-01-SUMMARY.md`
- Plan 02 SUMMARY: `.planning/phases/12-codegen-spike/12-02-SUMMARY.md`
- Plan 03 SUMMARY (FINAL): `.planning/phases/12-codegen-spike/12-03-SUMMARY.md`
- Spike directory: `.planning/spikes/SPIKE-005-codegen-tool-choice/`
- Auto-loaded Skill: `.claude/skills/spike-findings-codegen-market-libs/SKILL.md`
- v1.3 libcst pending todo: `.planning/todos/pending/spike-codegen-libcst-v1.3.md`
- v1.2 REQUIREMENTS REFAC-06 deferred: `.planning/REQUIREMENTS.md` §"Future Requirements (Defer to v1.3+)"
- v1.2 ROADMAP Phase 16 DROPPED: `.planning/ROADMAP.md` §Phase 16
- Operational pre-gate origin: `.planning/phases/12-codegen-spike/12-01-SUMMARY.md` §"Operator pre-gate response"
