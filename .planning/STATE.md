---
gsd_state_version: 1.0
milestone: v1.2
milestone_name: Architecture + Auth/Ergonomics Carry-forwards
status: ready_to_plan
last_updated: 2026-06-14T20:52:30.433Z
last_activity: 2026-06-14 -- Phase 12 execution started
progress:
  total_phases: 6
  completed_phases: 0
  total_plans: 3
  completed_plans: 4
  percent: 0
stopped_at: Phase 12 complete (4/3) — ready to discuss Phase 13
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-14 for v1.2)

**Core value:** Cada divergencia entre un cliente y su API en vivo debe ser detectada, documentada y corregida. (v1.2 layer: cerrar la deuda arquitectónica residual de v1.1 — driver migration × 4 a `Client`/`AsyncClient` directos + unasync/codegen single-source sync/async [spike-gated] + IOL refresh_token disk persistence + `client.with_options(max_retries=N)` × 4.)

**Current focus:** Phase 13 — cross package ergonomics (`with_options(max_retries=n)`)

## Current Position

Phase: 13
Plan: Not started
Status: Ready to plan
Last activity: 2026-06-14

**Operational gate before Phase 12 starts:** v1.1 head `71bf201` MUST be confirmed CI-green on Python 3.13 (closes 3 deferred human-verification items from v1.1 Phases 7/8/9; anti-Pitfall 17). If CI red, fix lands as quick-task before Phase 12 planning commits.

## Performance Metrics

**Velocity (v1.0 archived):**

- Total plans completed: 41 (v1.0)
- Total tasks completed: 27 (v1.0)
- v1.0 duration: 2026-05-28 → 2026-06-10 (~13 days, 5 phases)

**By Phase (v1.0):**

| Phase | Plans | Status   | Notes |
|-------|-------|----------|-------|
| 01    | 4     | Complete | Safety harness baseline |
| 02    | 3     | Complete | Ámbito (smallest blast radius) |
| 03    | 3     | Complete | IOL (OAuth refresh_token) |
| 04    | 4     | Complete | Higyrus (largest surface; 24+ regressions) |
| 05    | 4     | Complete | Matriz (sync only; 19 regressions; DRIFT-02 closure) |

**By Phase (v1.1 shipped 2026-06-14):**

| Phase | Plans | Status   | Notes |
|-------|-------|----------|-------|
| 06    | 7     | Complete | Compat safety net + Client/AsyncClient classes + PEP 562 shim (REFAC-01/02) |
| 07    | 6     | Complete | `_core.py` extraction + import-linter contracts (REFAC-03 + CR-03/05; LOC drop partial, v1.2 carry-forward) |
| 08    | 6     | Complete | `tenacity` retries + full-jitter backoff + mutation gate + `RedactingFilter` (RELY-01..04 + LOG-01..03) |
| 09    | 4     | Complete | 4 deferred bug fixes (BUG-01..04, 2 operator overrides) |
| 10    | 4     | Complete | matriz `aio.py` 852 LOC + TokenStore 3-way + `_atransport.py` (REFAC-04 + LIVE-02) |
| 11    | 3     | Complete | findings.py append-only + 6 CR fixes + LIVE-01 final gate × 4 packages (HARN-07..10 + CR-01/02/04/06/07/08 + LIVE-01) |

- v1.1 duration: 2026-06-11 → 2026-06-14 (~3.5 days, 6 phases, 30 plans, 52 tasks)
- v1.1 git stats: 179 commits, 307 files changed, +76,286 / −3,538 LOC
- Test suite: 277 (v1.0 close) → 907/908 (v1.1 close) on Python 3.12 local
- Quick tasks: 3 (260611-u0v, 260613-nwb, 260614-de5)

**By Phase (v1.2 planned):**

| Phase | Plans | Status      | Requirements | Notes |
|-------|-------|-------------|--------------|-------|
| 12    | ?     | Not started | REFAC-06 (spike) | Codegen tool-choice spike (unasync vs libcst); go/no-go output for Phase 16 — RESEARCH FLAG |
| 13    | ?     | Not started | ERG-01 | `with_options(max_retries=N)` × 4 packages; mutation-gate invariant preserved (CRITICAL test: matriz new_order under 503 exactly 1 request) |
| 14    | ?     | Not started | SEC-01 | IOL `_token_cache.py` + platformdirs + fcntl.flock + 0600 + caplog no-leak + failed-refresh cleanup — parallel-eligible with Phase 15 |
| 15    | ?     | Not started | REFAC-05 | Driver migration × 4 (ámbito → iol → higyrus → matriz); ONE Client per main() AST guard; probe-name stability vs LIVE-01 71bf201 |
| 16    | ?     | Not started | REFAC-06 | CONDITIONAL — DROPPED if Phase 12 NO-GO; otherwise unasync codegen × 4 transport shells with @generated marker + CI verify-clean |
| 17    | ?     | Not started | LIVE-03 | Final LIVE-01-equivalent gate × 4 packages; milestone audit |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [v1.2 Roadmap]: Phase order derived from research SUMMARY.md dependency DAG: Phase 12 spike-before-plan → Phase 13 ergonomics (drivers consume `with_options` in Phase 15) → Phase 14 IOL disk + Phase 15 driver migration in parallel waves → Phase 16 codegen (CONDITIONAL on Phase 12) → Phase 17 LIVE-03 final gate.
- [v1.2 Roadmap]: REFAC-06 is mapped to Phase 16 as CONDITIONAL — DROPPED entirely if Phase 12 spike returns NO-GO; defers REFAC-06 to v1.3 in that case. All other 4 requirements (REFAC-05, SEC-01, ERG-01, LIVE-03) are mandatory.
- [v1.2 Roadmap]: Driver migration (REFAC-05, Phase 15) MUST run BEFORE codegen (REFAC-06, Phase 16) — driver migration surfaces public method surface gaps locally; codegen-after would mask them cross-phase. Per ARCHITECTURE §2.6 reason #4.
- [v1.2 Roadmap]: Per-package serial ordering within phases: ámbito → iol → higyrus → matriz (REFAC-05, SEC-01, LIVE-03 follow this); ERG-01 (Phase 13) uses ámbito → higyrus → matriz → iol (iol LAST because it interacts with SEC-01 disk cache in Phase 14).
- [v1.2 Roadmap]: HIGHEST-RISK pitfall test gates encoded as merge-gate success criteria — Phase 13 anti-Pitfall 14 (matriz `new_order` exactly 1 request under 503); Phase 14 anti-Pitfall 7/8/9 (caplog no-leak + failed-refresh cleanup + fcntl race); Phase 15 anti-Pitfall 1/15 (AST single-Client guard + probe-name stability); Phase 16 anti-Pitfall 4/5 (B8 identity + @generated marker verify-clean).
- [v1.2 Roadmap]: Operational pre-gate — v1.1 head `71bf201` confirmed CI-green on Python 3.13 BEFORE Phase 12 starts; anti-Pitfall 17 (prevents v1.1-vs-v1.2 attribution ambiguity).

### Pending Todos

[From .planning/todos/pending/ — ideas captured during sessions]

- matriz-driver-findings-file-handling (deferred from v1.0 — addressed in Phase 11 via HARN-07/HARN-08/HARN-10)

### Blockers/Concerns

[Issues that affect future work]

- [Phase 12]: Codegen tool choice (unasync vs libcst) is the single architectural unknown in v1.2; spike-before-plan flag activated per PROJECT.md and SUMMARY.md. Phase 12 GO/NO-GO output gates Phase 16.
- [Phase 13]: Pitfall 14 (`with_options(max_retries=10).new_order(...)` bypassing mutation gate) — duplicate-order money-on-the-line; the CRITICAL test must land BEFORE Phase 13 merge — matriz Primary `new_order` under 503 mock must execute EXACTLY 1 outgoing request.
- [Phase 14]: Pitfall 7 (new disk log sites bypass `RedactingFilter`) — token-write logger MUST be under `iol_client.*` namespace; `caplog` regression test required.
- [Phase 14]: Pitfall 8 (stale-token-after-OOB-rotation) — failed-refresh path MUST delete disk token before password fallback; regression test required.
- [Phase 14]: Pitfall 9 (multi-process race) — `fcntl.flock` required around disk writes; regression test with 20 concurrent threads required.
- [Phase 15]: Pitfall 1 (state leak between probes / per-instance state defeats singleton expectation) — ONE Client per main() run invariant enforced by AST regression-guard per driver.
- [Phase 15]: Pitfall 15 (probe-name stability) — finding IDs/titles MUST stay constant vs LIVE-01 baseline `71bf201`; only probe BODIES change.
- [Phase 16]: Pitfall 4 (codegen breaks B8 identity) — `aio._raise_for_response is client._raise_for_response is _core.raise_for_response` MUST survive codegen; test runs FIRST in CI.
- [Phase 16]: Pitfall 5 (codegen overwrites hand-edit) — `@generated` marker + CI `lint-codegen` verify-clean job mandatory.

### Quick Tasks Completed

| # | Description | Date | Commits | Directory |
|---|-------------|------|---------|-----------|
| 260611-u0v | Fix CI failures on phase-06-compat-safety-net (snapshot trailing whitespace + iol tests mypy strict + v1.0 archive whitespace) | 2026-06-11 | bc16e26, 2be4e90, 9360cf5 | [260611-u0v-fix-ci-failures-on-phase-06-compat-safet](./quick/260611-u0v-fix-ci-failures-on-phase-06-compat-safet/) |
| 260613-nwb | Fix INT-01: replace denied `_base_url` with `_get_default()._state.base_url` in main_iol.py (15 probes) — closes INT-01, unblocks LIVE-01 (Phase 11) | 2026-06-13 | 3de1940 | [260613-nwb-fix-int-01-main-iol-py-crashea-con-attri](./quick/260613-nwb-fix-int-01-main-iol-py-crashea-con-attri/) |
| 260614-de5 | Fix DOC-01..04 before completing milestone v1.1 — backfill 4 SUMMARY frontmatters + flip REQUIREMENTS.md traceability table 18 rows Open→Complete + emit Phase 10/11 VERIFICATION shims + remove ORP-01 dead `account_id` field from matriz `_state.py` | 2026-06-14 | 9d01d7f, cd946a3 | [260614-de5-fix-doc-01-04-before-completing-mileston](./quick/260614-de5-fix-doc-01-04-before-completing-mileston/) |

## Deferred Items

Items acknowledged and carried forward from v1.0 milestone close on 2026-06-10:

| Category | Item | Status | Resolution in v1.1 |
|----------|------|--------|---------------------|
| todo | matriz-driver-findings-file-handling | low priority — driver dedupe + append-only bugs | Resolved in Phase 11 (HARN-07/08/10) |
| uat_gap | 03-HUMAN-UAT.md | partial — legacy HUMAN-UAT from Phase 3 close | N/A — archived under v1.0 |
| uat_gap | 05-HUMAN-UAT.md | partial — 2 ítems satisfied via operator re-run 2026-06-10T15Z | N/A — archived under v1.0 |
| verification_gap | 03-VERIFICATION.md | human_needed — operator-driven validation | N/A — archived under v1.0 |
| verification_gap | 05-VERIFICATION.md | human_needed — operator-driven validation satisfied via re-run | N/A — archived under v1.0 |
| deferred_bug | F-09 matriz ERROR-MAP | DEFERRED in v1.0 Phase 5 | Resolved in Phase 9 (BUG-01) |
| deferred_bug | F-02 higyrus get_listado_cuentas=0 | DEFERRED in v1.0 Phase 4 | Resolved in Phase 9 (BUG-02) |
| deferred_cap | IOL refresh_token persistence | DEFERRED in v1.0 Phase 3 | Resolved in Phase 9 (BUG-03, in-instance only; disk persistence deferred to v1.2 — now Phase 14 SEC-01) |
| deferred_cap | HIGY multi-account iteration | DEFERRED in v1.0 Phase 4 | Resolved in Phase 9 (BUG-04) |

See `.planning/milestones/v1.0-MILESTONE-AUDIT.md` for the full v1.0 audit context.

### Acknowledged at v1.1 close on 2026-06-14

Items surfaced by `gsd-sdk query audit-open` and acknowledged by operator at milestone close (per v1.1-MILESTONE-AUDIT.md `human_verification_pending:` block):

| Category | Item | Status | Carry-forward |
|----------|------|--------|---------------|
| uat_gap | 07-HUMAN-UAT.md | partial — test 1 pending (CI matrix Python 3.13 remote confirmation); test 2 accepted 2026-06-14 (SC#3 LOC drop disposition signed off) | Human-only — requires push + observe GitHub Actions matrix; **PRE-PHASE-12 OPERATIONAL GATE** |
| uat_gap | 08-HUMAN-UAT.md | partial — 4 pending: live retry smoke under real transients, log legibility subjective UX, CI 3.13 matrix, deferred review-item tracking | Human-only; deferred-review-tracking actually closed by Phase 11 (HARN scope), other 3 remain operator-confirm; **CI 3.13 matrix is PRE-PHASE-12 OPERATIONAL GATE** |
| uat_gap | 09-HUMAN-UAT.md | partial — test 1 pending (CI matrix Python 3.13 remote confirmation) | Human-only — same as Phase 07 test 1; **PRE-PHASE-12 OPERATIONAL GATE** |
| quick_task | 260611-u0v-fix-ci-failures-on-phase-06-compat-safet | SDK reports "missing" — SUMMARY frontmatter `status: complete`, 3 commits in git history | False-positive (SDK parser heuristic) |
| quick_task | 260613-nwb-fix-int-01-main-iol-py-crashea-con-attri | SDK reports "missing" — SUMMARY frontmatter `status: complete`, 1 commit in git history | False-positive (SDK parser heuristic) |
| quick_task | 260614-de5-fix-doc-01-04-before-completing-mileston | SDK reports "missing" — SUMMARY frontmatter `status: complete`, 2 commits in git history | False-positive (SDK parser heuristic) |

Cleaned up inline before milestone close:

- Pending todo `matriz-driver-findings-file-handling.md` moved to `.planning/todos/completed/` (resolved by Phase 11 HARN-07/08/10).
- Phase 07 UAT test 2 (SC#3 LOC drop disposition) flipped from `[pending]` to `[accepted]` (operator signoff captured in 07-VERIFICATION.md frontmatter on 2026-06-14).

## Session Continuity

Last session: 2026-06-14T17:53:04.411Z
Stopped at: Phase 12 context gathered
Resume file: .planning/phases/12-codegen-spike/12-CONTEXT.md

## Operator Next Steps

1. **Pre-Phase-12 operational gate:** push v1.1 head `71bf201` to remote (if not already) and confirm GitHub Actions matrix green on Python 3.12 + 3.13. If red, file as quick-task before Phase 12.
2. **Start Phase 12 discussion:** `/gsd-discuss-phase 12` — codegen tool-choice spike (unasync vs libcst on ámbito canary + matriz worst case). RESEARCH FLAG active.
3. **Phase 12 output gates Phase 16:** if NO-GO, REFAC-06 defers to v1.3 and Phase 16 is DROPPED from the schedule; Phase 17 (LIVE-03) runs directly after Phase 14 + 15.
