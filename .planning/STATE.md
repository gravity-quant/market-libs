---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: Tech Debt Cleanup
status: completed
last_updated: "2026-06-14T02:58:27.729Z"
last_activity: 2026-06-14 -- Phase 10 marked complete
progress:
  total_phases: 6
  completed_phases: 5
  total_plans: 30
  completed_plans: 27
  percent: 83
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-10 for v1.1)

**Core value:** Cada divergencia entre un cliente y su API en vivo debe ser detectada, documentada y corregida. (v1.1 layer: saldar la deuda arquitectónica que vino a la luz durante el ciclo de verificación v1.0 — refactor Client class, sync/async dedup, matriz aio.py, retries/backoff, structured logging, deferred fixes, harness hardening.)

**Current focus:** Phase 10 — matriz-aio-py-creation-tokenstore

## Current Position

Phase: 10 — COMPLETE
Plan: 1 of 4
Status: Phase 10 complete
Last activity: 2026-06-14 -- Phase 10 marked complete

## Performance Metrics

**Velocity (v1.0 archived):**

- Total plans completed: 34 (v1.0)
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

**v1.1 (upcoming):**

| Phase | Plans | Status      |
|-------|-------|-------------|
| 06    | TBD   | Not started |
| 07    | TBD   | Not started |
| 08    | TBD   | Not started |
| 09    | TBD   | Not started |
| 10    | TBD   | Not started |
| 11    | TBD   | Not started |
| Phase 08 P01 | 15 | 2 tasks | 13 files |
| Phase 08 P02 | 10 | 2 tasks | 12 files |
| Phase 08 P03 | 20 | 2 tasks | 13 files |
| Phase 08 P04 | 25 | 2 tasks | 12 files |
| Phase 08 P05 | 30 | 2 tasks | 8 files |
| Phase 08 P06 | 25 | 1 tasks | 4 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [v1.1 Roadmap]: Phase order is dependency-driven (research-mandated): Phase 6 safety net BEFORE refactor → Phase 7 `_core.py` dedup → Phase 8 retries+logging (parallel after `_core.py`) → Phase 9 deferred bugs (single-site fix via `_core.py`) → Phase 10 matriz aio.py (needs `_core.py` + retries/logging infra) → Phase 11 harness + code review + live re-verification.
- [v1.1 Roadmap]: Per-package serial pattern (v1.0 lesson) — within Phase 6 and Phase 7, process order: ámbito → iol → higyrus → matriz; each package independent (no shared internals — refactors replicate 4x).
- [v1.1 Roadmap]: Non-breaking via PEP 562 `__getattr__` shim + `configure(token=..., token_expires_at=...)` extension for conftest migration; 277 tests baseline must stay green after EVERY phase.
- [v1.1 Roadmap]: Mutation gate is mandatory — `RequestSpec.idempotent` defaults False; POST/PATCH NEVER retry without explicit `idempotent=True`; `AuthError`/`PrimaryAPIError`/`HigyrusAPIError` NEVER in `retry_on=` tuple.
- [v1.1 Research Flag]: Phase 10 (matriz `aio.py` + TokenStore) requires phase-level research spike before planning — the 3-way concurrent token store (sync REST + async REST + ws_client daemon thread with `threading.Lock` callable from asyncio context) is the single architectural unknown in v1.1.
- [Phase ?]: Phase 8 Plan 1: Wave 1 cross-cutting scaffolding landed — tenacity 9.1.4 dep + 6 guard tests (14 RED awaiting Plans 2-5) + ruff LOG + CI grep step (D-15, D-21, D-26, D-27)
- [Phase ?]: Phase 8 Plan 2 (ámbito canary): RetryTransport + AsyncRetryTransport + RedactingFilter wired; pattern verified for Plan 3 replication
- [Phase ?]: Phase 8 Plan 3 (iol): RetryTransport+AsyncRetryTransport+RedactingFilter mirrored from ámbito + 401 re-auth-once at shell tier (D-02) + OAuth refresh_token URL+JSON redaction (D-10). Auth-paquete pattern established for Plans 4 (higyrus) and 5 (matriz).
- [Phase ?]: Plan 8-01 cross-cutting test bug fixed: test_idempotent_get_retries_on_503 expected_count corrected from 2 to 3 — Plan 8-01 author had a notation slip; canonical default is max_retries=2 = 3 attempts per D-15+D-19. Unblocks Plans 4+5 too.
- [Phase ?]: Phase 8 Plan 4 (higyrus)
- [Phase ?]: Phase 8 Plan 5 (matriz): Wave 5 closure. RetryTransport sync + RedactingFilter D-22 (auth_basic split) + Risk API no-401-reauth (D-23) + status=ERROR no-retry (D-24) + mutation gate on Primary order GETs (Pitfall 4 — duplicate-order prevention). matriz aio.py UNCHANGED (103 LOC stub per D-25 — Phase 10 REFAC-04 territory).
- [Phase ?]: Phase 8 Plan 6 green-gate consolidation complete; nyquist_compliant=true; 627 pytest pass + 3 skip (D-25); 5 ROADMAP success criteria backward-verified; Pitfall 4 GREEN; D-25 matriz aio.py preserved 103 LOC; CI lint-logging grep refined for docstring false-positive (Rule 1 fix)
- [Phase 8]: Plan 6 Task 2 operator checkpoint closed 2026-06-13 — approval signal delivered via 08-VALIDATION.md frontmatter edit (status=approved, nyquist_compliant=true, wave_0_complete=true, phase_status=ready_for_verify); 6 close-out spot-checks all PASS (matriz aio.py=103, matriz _atransport.py ABSENT, Pitfall 4 matriz_new_order PASS, tenacity 9.1.4 confirmed, 5 atomic feat commits + Plan 6 ci+docs present, green-gate evidence sections complete)

### Pending Todos

[From .planning/todos/pending/ — ideas captured during sessions]

- matriz-driver-findings-file-handling (deferred from v1.0 — addressed in Phase 11 via HARN-07/HARN-08/HARN-10)

### Blockers/Concerns

[Issues that affect future work]

- [Phase 6]: Pitfall #1 (monkeypatch silent breakage) — the "fixture reaches production" guard test MUST exist and pass BEFORE the first Client class refactor lands per-package.
- [Phase 7]: Pitfall #3 (re-coupling sync/async via `_core.py` imports) — import-linter rule + distinct sync/async sentinels in conftest are gates for merge.
- [Phase 8]: Pitfall #4 (retry of mutating POST) — regression test asserting exactly 1 outgoing request per POST mockeado contra 503 is mandatory before enabling retry decorator.
- [Phase 8]: Pitfall #6 (library logging.basicConfig) — CI grep rule + regression test for `logging.root.handlers` unchanged after import is mandatory.
- [Phase 10]: TokenStore 3-way design is the highest-uncertainty item of v1.1; research flag triggered — spike must happen before `/gsd-plan-phase 10`.

### Quick Tasks Completed

| # | Description | Date | Commits | Directory |
|---|-------------|------|---------|-----------|
| 260611-u0v | Fix CI failures on phase-06-compat-safety-net (snapshot trailing whitespace + iol tests mypy strict + v1.0 archive whitespace) | 2026-06-11 | bc16e26, 2be4e90, 9360cf5 | [260611-u0v-fix-ci-failures-on-phase-06-compat-safet](./quick/260611-u0v-fix-ci-failures-on-phase-06-compat-safet/) |
| 260613-nwb | Fix INT-01: replace denied `_base_url` with `_get_default()._state.base_url` in main_iol.py (15 probes) — closes INT-01, unblocks LIVE-01 (Phase 11) | 2026-06-13 | 3de1940 | [260613-nwb-fix-int-01-main-iol-py-crashea-con-attri](./quick/260613-nwb-fix-int-01-main-iol-py-crashea-con-attri/) |

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
| deferred_cap | IOL refresh_token persistence | DEFERRED in v1.0 Phase 3 | Resolved in Phase 9 (BUG-03, in-instance only; disk persistence deferred to v1.2) |
| deferred_cap | HIGY multi-account iteration | DEFERRED in v1.0 Phase 4 | Resolved in Phase 9 (BUG-04) |

See `.planning/milestones/v1.0-MILESTONE-AUDIT.md` for the full v1.0 audit context.

## Session Continuity

Last session: 2026-06-14T02:58:27.721Z
Stopped at: Phase 11 planning complete
Resume file: .planning/phases/11-harness-hardening-code-review-close-out-live-re-verification/11-01-PLAN.md

## Operator Next Steps

1. Review the v1.1 roadmap in `.planning/ROADMAP.md` and the traceability table in `.planning/REQUIREMENTS.md`.
2. (Recommended) Before `/gsd-plan-phase 10`, run the research spike on the 3-way TokenStore design (sync + asyncio + threading) — flagged in Phase 10's research flag.
3. Start Phase 6 planning with `/gsd-plan-phase 6`.
