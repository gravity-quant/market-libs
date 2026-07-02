---
gsd_state_version: 1.0
milestone: v1.3
milestone_name: Codegen Single-Source
current_phase: 18
current_phase_name: libcst Codegen Tool-Choice Spike — SPIKE-006
status: planning
stopped_at: Phase 18 context gathered (assumptions mode)
last_updated: "2026-07-02T23:32:09.878Z"
last_activity: 2026-07-02
last_activity_desc: v1.3 roadmap created (Phases 18-19, spike-gated REFAC-06)
progress:
  total_phases: 2
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-07-02 for v1.3)

**Core value:** Cada divergencia entre un cliente y su API en vivo debe ser detectada, documentada y corregida. (v1.3 layer: cerrar el único unknown arquitectónico residual — eliminar la duplicación estructural sync/async de los transport shells `client.py`/`aio.py` × 4 paquetes vía codegen single-source con `libcst`, resolviendo o descartando definitivamente el NO-GO de unasync de v1.2 Phase 12.)

**Current focus:** v1.3 roadmap created (2026-07-02). 2 phases: Phase 18 (SPIKE-006 libcst spike, ALWAYS runs → signed GO/NO-GO) + Phase 19 (REFAC-06 codegen single-source × 4, CONDITIONAL on Phase 18 GO — DROPPED if NO-GO). Next: plan Phase 18 via `/gsd-plan-phase 18`.

## Current Position

Phase: 18 (libcst Codegen Tool-Choice Spike — SPIKE-006) — Not started
Plan: —
Status: Roadmap created, awaiting phase planning
Last activity: 2026-07-02 — v1.3 roadmap created (Phases 18-19, spike-gated REFAC-06)

## Performance Metrics

**Velocity (v1.0 archived):**

- Total plans completed: 57 (v1.0)
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

**By Phase (v1.2 shipped 2026-06-25):**

| Phase | Plans | Status   | Notes |
|-------|-------|----------|-------|
| 12    | 4/3   | Complete | Codegen tool-choice spike (unasync vs libcst) — **NO-GO** (3/8 D-RIGOR-01 FAIL, source-shape asymmetry); REFAC-06 → v1.3; REFAC-06 (spike) |
| 13    | 5     | Complete | `with_options(max_retries=N)` × 4 packages; CRITICAL matriz mutation-gate merge gate (new_order under 503 = exactly 1 request); ERG-01 |
| 14    | 3     | Complete | IOL `_token_cache.py` + platformdirs + fcntl.flock + 0600 + caplog no-leak + failed-refresh cleanup; SEC-01 |
| 15    | 5/4   | Complete | Driver migration × 4; ONE Client per main() AST guard; probe-name stability vs LIVE-01 71bf201; REFAC-05 |
| 16    | -     | Dropped  | Codegen Single-Source — DROPPED per Phase 12 NO-GO; REFAC-06 → v1.3 |
| 17    | 3     | Complete | Final LIVE-01-equivalent gate × 4 packages; cycle closure × 4 PASS; 0-BLOCKER audit; LIVE-03 |

- v1.2 duration: 2026-06-14 → 2026-06-25 (5 phases, 18 plans, 40 tasks); shipped via PR #2
- Test suite: 907 (v1.1 close) → ≥989 (v1.2 close) on Python 3.12 + 3.13

**By Phase (v1.3 planned):**

| Phase | Plans | Status      | Requirements | Notes |
|-------|-------|-------------|--------------|-------|
| 18    | ?     | Not started | CODEGEN-01 (spike) | **RESEARCH FLAG / spike-before-plan.** SPIKE-006 evaluates `libcst >=1.8.0,<2` against the D-RIGOR-02 10-item gate on the ámbito v1.2-head canary (NOT migrated) + matriz audit/deny-list inheritance → signed GO/NO-GO. ALWAYS runs; guaranteed milestone deliverable. Items 1/4/6 are GO-determining. |
| 19    | ?     | Not started | REFAC-06 | **CONDITIONAL — DROPPED if Phase 18 NO-GO.** Single-source `client.py`/`aio.py` shells × 4 (ámbito → iol → higyrus → matriz) via libcst; `@generated` marker + CI `lint-codegen` verify-clean + B8 identity + mocked suites green vs generated + deny-list intact. |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [v1.3 Roadmap]: Phase numbering CONTINUES from v1.2 (last phase = 17) — v1.3 starts at Phase 18 (does NOT reset). Sequential `phase_naming` per config.json.
- [v1.3 Roadmap]: Spike-gated conditional structure mirrors v1.2 (Phase 12 spike + conditional Phase 16). Phase 18 (SPIKE-006) is spike-before-plan and the guaranteed deliverable; Phase 19 (REFAC-06) is CONDITIONAL — DROPPED entirely if Phase 18 returns NO-GO, in which case REFAC-06 is shelved permanently per D-NOGO-01 and the milestone closes on the signed NO-GO.
- [v1.3 Roadmap]: The 3 GO-determining gate items are D-RIGOR-02 item 1 (byte-identical round-trip, no source migration), item 4 (ruff check clean incl. single-line import-order), item 6 (mocked suite green vs generated, no circular self-import) — all trace to the single unasync root cause (source-shape asymmetry). libcst must close all 3 for GO.
- [v1.3 Roadmap]: No standalone milestone-close / live re-verification phase. Per the in-cycle verification convention, byte-identical generated output means wire behavior is unchanged by construction; the D-RIGOR-02 item-1 + item-6 gates fold verification into Phase 19. Milestone kept tight (REFAC-06-only) — other v1.3 candidates (prod-vs-remarkets, ws_client live, token encryption) stay in backlog.
- [v1.3 Roadmap]: Matriz deny-list (`_token_store.py`/`_refresh_policy.py`/`_refresh.py`/`ws_client.py`) is OUT of codegen scope in BOTH phases — the spike CONFIRMS (sha256-byte-identical under MetadataWrapper), it does NOT renegotiate. Codegen applies ONLY to `client.py`/`aio.py` transport shells.

### Pending Todos

[From .planning/todos/pending/ — ideas captured during sessions]

- spike-codegen-libcst-v1.3.md — the fully-scoped SPIKE-006 spec + D-RIGOR-02 10-item gate; consumed by Phase 18 planning.

### Blockers/Concerns

[Issues that affect future work]

- [Phase 18]: SPIKE-006 is the single architectural unknown remaining in the codebase; spike-before-plan flag active. Its GO/NO-GO output gates Phase 19. Inherits the 8 SPIKE-005 PASS/FAIL learnings via `Skill("spike-findings-codegen-market-libs")` — items 2/3/5/7/8 expected-PASS; items 1/4/6 are the gap libcst must close.
- [Phase 18]: If items 1/4/6 FAIL again under libcst, REFAC-06 is shelved PERMANENTLY (duplicate shells accepted as structural feature) and the milestone closes on the signed NO-GO — this is a valid, guaranteed milestone outcome, not a failure.
- [Phase 19]: Pitfall 4 (codegen breaks B8 identity) — `aio._raise_for_response is client._raise_for_response is _core.raise_for_response` MUST survive codegen; test runs FIRST in CI (no thunk-wrapper).
- [Phase 19]: Pitfall 5 (codegen overwrites hand-edit) — `@generated` marker + CI `lint-codegen` verify-clean (`git diff --exit-code`) mandatory.
- [Phase 19]: Matriz deny-list intactness — the 4 concurrency-primitive files must stay sha256-identical; only `client.py`/`aio.py` are regenerated.

### Quick Tasks Completed

| # | Description | Date | Commits | Directory |
|---|-------------|------|---------|-----------|
| 260611-u0v | Fix CI failures on phase-06-compat-safety-net (snapshot trailing whitespace + iol tests mypy strict + v1.0 archive whitespace) | 2026-06-11 | bc16e26, 2be4e90, 9360cf5 | [260611-u0v-fix-ci-failures-on-phase-06-compat-safet](./quick/260611-u0v-fix-ci-failures-on-phase-06-compat-safet/) |
| 260613-nwb | Fix INT-01: replace denied `_base_url` with `_get_default()._state.base_url` in main_iol.py (15 probes) — closes INT-01, unblocks LIVE-01 (Phase 11) | 2026-06-13 | 3de1940 | [260613-nwb-fix-int-01-main-iol-py-crashea-con-attri](./quick/260613-nwb-fix-int-01-main-iol-py-crashea-con-attri/) |
| 260614-de5 | Fix DOC-01..04 before completing milestone v1.1 — backfill 4 SUMMARY frontmatters + flip REQUIREMENTS.md traceability table 18 rows Open→Complete + emit Phase 10/11 VERIFICATION shims + remove ORP-01 dead `account_id` field from matriz `_state.py` | 2026-06-14 | 9d01d7f, cd946a3 | [260614-de5-fix-doc-01-04-before-completing-mileston](./quick/260614-de5-fix-doc-01-04-before-completing-mileston/) |
| 260614-r1x | Fix v1.1 CI mypy + pre-commit tech debt (mypy-precommit-v1.1-techdebt) — Bucket A: 4 unused `# type: ignore` dropped + `_raise_for_response` added to `aio.__all__`; Bucket B+C: bump `ruff-pre-commit` v0.7.4→v0.15.12; Bucket D: add `tenacity>=9.1.0,<10` to pre-commit mypy `additional_dependencies` | 2026-06-14 | e5ad1c1, 73cb578, c7bf9e9, 2b8ec4a | [260614-r1x-fix-v1-1-ci-mypy-pre-commit-tech-debt-cl](./quick/260614-r1x-fix-v1-1-ci-mypy-pre-commit-tech-debt-cl/) |

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
| deferred_cap | IOL refresh_token persistence | DEFERRED in v1.0 Phase 3 | Resolved in Phase 9 (BUG-03, in-instance only; disk persistence Phase 14 SEC-01) |
| deferred_cap | HIGY multi-account iteration | DEFERRED in v1.0 Phase 4 | Resolved in Phase 9 (BUG-04) |

See `.planning/milestones/v1.0-MILESTONE-AUDIT.md` for the full v1.0 audit context.

### Acknowledged at v1.2 close on 2026-06-25

Items surfaced by `gsd-sdk query audit-open` (6 total) and acknowledged by operator at v1.2 milestone close ("Acknowledge & proceed"). All are intentional deferrals or stale history — none are real blockers:

| Category | Item | Status | Carry-forward |
|----------|------|--------|---------------|
| quick_task | 260611-u0v / 260613-nwb / 260614-de5 / 260614-r1x | SDK reports "missing" — v1.1-era tasks, work landed in git history | False-positive (SDK parser heuristic) — no action |
| todo | spike-codegen-libcst-v1.3.md | pending (high) → **now active** | Became the v1.3 codegen spike (Phase 18 SPIKE-006) per Phase 12 NO-GO (D-NOGO-01) |
| uat_gap | 15-HUMAN-UAT.md | partial — 4 operator-driven live scenarios | Superseded by Phase 17 LIVE-03 final gate (dispositions × 4 in 17-VALIDATION.md) |

See `.planning/milestones/v1.2-ROADMAP.md` and the MILESTONES.md v1.2 entry for full close context.

## Session Continuity

Last session: 2026-07-02T23:32:09.874Z
Stopped at: Phase 18 context gathered (assumptions mode)
Resume file: .planning/phases/18-libcst-codegen-tool-choice-spike-spike-006/18-CONTEXT.md

## Operator Next Steps

- Plan the first v1.3 phase with `/gsd-plan-phase 18` (SPIKE-006 libcst codegen spike — spike-before-plan / RESEARCH FLAG).
