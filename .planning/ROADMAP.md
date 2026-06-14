# Roadmap: market-libs — Verificación en vivo de clientes

## Milestones

- ✅ **v1.0 Verification cycle** — Phases 1-5 (shipped 2026-06-10) — see [`milestones/v1.0-ROADMAP.md`](./milestones/v1.0-ROADMAP.md)
- ✅ **v1.1 Tech Debt Cleanup** — Phases 6-11 (shipped 2026-06-14) — see [`milestones/v1.1-ROADMAP.md`](./milestones/v1.1-ROADMAP.md)
- 📋 **v1.2 (next)** — planning via `/gsd-new-milestone`

## Phases

<details>
<summary>✅ v1.0 Verification cycle (Phases 1-5) — SHIPPED 2026-06-10</summary>

- [x] Phase 1: Safety Harness & Verification Infrastructure (4/4 plans) — completed 2026-05-28
- [x] Phase 2: Ámbito Verification (3/3 plans) — completed 2026-06-05
- [x] Phase 3: IOL Verification (3/3 plans) — completed 2026-06-06
- [x] Phase 4: Higyrus Verification (4/4 plans) — completed 2026-06-08
- [x] Phase 5: Matriz Verification (4/4 plans) — completed 2026-06-10 (DRIFT-02 cycle closure baseline `verification-cycle-2026-Q2`)

Full details: [`milestones/v1.0-ROADMAP.md`](./milestones/v1.0-ROADMAP.md)
Requirements archive: [`milestones/v1.0-REQUIREMENTS.md`](./milestones/v1.0-REQUIREMENTS.md)
Audit: [`milestones/v1.0-MILESTONE-AUDIT.md`](./milestones/v1.0-MILESTONE-AUDIT.md)

</details>

<details>
<summary>✅ v1.1 Tech Debt Cleanup (Phases 6-11) — SHIPPED 2026-06-14</summary>

- [x] Phase 6: Compat Safety Net + Client Class Skeleton (7/7 plans) — completed 2026-06-11 — `Client`/`AsyncClient` per package + PEP 562 compat shim; REFAC-01/02
- [x] Phase 7: `_core.py` Extraction — Sync/Async Logic Dedup (6/6 plans) — completed 2026-06-12 — pure builders/parsers + import-linter contracts; REFAC-03 + CR-03/05
- [x] Phase 8: Retries, Backoff, Structured Logging (6/6 plans) — completed 2026-06-13 — `tenacity` full-jitter + mutation gate + `RedactingFilter`; RELY-01..04 + LOG-01..03
- [x] Phase 9: Deferred Bug Fixes (4/4 plans) — completed 2026-06-13 — BUG-01..04 (2 operator overrides)
- [x] Phase 10: matriz `aio.py` Creation + TokenStore (4/4 plans) — completed 2026-06-14 — 852 LOC async REST + `TokenStore` 3-way concurrency + `_atransport.py`; REFAC-04 + LIVE-02
- [x] Phase 11: Harness Hardening + Code Review Close-out + Live Re-verification (3/3 plans) — completed 2026-06-14 — append-only findings + idempotent dedupe + LIVE-01 final gate × 4 packages (iol F-02 fixed inline); HARN-07..10 + CR-01/02/04/06/07/08 + LIVE-01

Full details: [`milestones/v1.1-ROADMAP.md`](./milestones/v1.1-ROADMAP.md)
Requirements archive: [`milestones/v1.1-REQUIREMENTS.md`](./milestones/v1.1-REQUIREMENTS.md)
Audit: [`milestones/v1.1-MILESTONE-AUDIT.md`](./milestones/v1.1-MILESTONE-AUDIT.md)
Phase artifacts: [`milestones/v1.1-phases/`](./milestones/v1.1-phases/)

</details>

### 📋 v1.2 (planning)

Start with `/gsd-new-milestone` to define scope, requirements, and roadmap.

## Progress

| Phase                                                       | Milestone | Plans | Status   | Completed  |
|-------------------------------------------------------------|-----------|-------|----------|------------|
| 1. Safety Harness & Verification Infrastructure             | v1.0      | 4/4   | Complete | 2026-05-28 |
| 2. Ámbito Verification                                      | v1.0      | 3/3   | Complete | 2026-06-05 |
| 3. IOL Verification                                         | v1.0      | 3/3   | Complete | 2026-06-06 |
| 4. Higyrus Verification                                     | v1.0      | 4/4   | Complete | 2026-06-08 |
| 5. Matriz Verification                                      | v1.0      | 4/4   | Complete | 2026-06-10 |
| 6. Compat Safety Net + Client Class Skeleton                | v1.1      | 7/7   | Complete | 2026-06-11 |
| 7. `_core.py` Extraction — Sync/Async Logic Dedup           | v1.1      | 6/6   | Complete | 2026-06-12 |
| 8. Retries, Backoff, Structured Logging                     | v1.1      | 6/6   | Complete | 2026-06-13 |
| 9. Deferred Bug Fixes                                       | v1.1      | 4/4   | Complete | 2026-06-13 |
| 10. matriz `aio.py` Creation + TokenStore                   | v1.1      | 4/4   | Complete | 2026-06-14 |
| 11. Harness Hardening + Code Review + Live Re-verification  | v1.1      | 3/3   | Complete | 2026-06-14 |

## Backlog

*(Candidate items for next milestone; see `.planning/todos/pending/` + v1.0/v1.1 milestone audits deferred sections)*

### Deferred to v1.2+ (from v1.1 planning)

- prod-vs-remarkets verification (D-MATZ-27 REQUIRED handoff)
- `matriz_client.ws_client` live verification (WebSocket streaming en daemon thread)
- IOL refresh_token disk persistence (secure token storage)
- Generated-code parity tooling (one source, dual emit via unasync/codegen)
- Automatic `Idempotency-Key` header para retried POSTs
- `findings.toml` machine-readable side-file
- `client.with_options(max_retries=N)` per-call override (anthropic/openai pattern)
- `Client.from_env()` classmethod for explicit env-reading
- `request_id` UUID per `_request()` invocation threaded through retry log records
- `max_elapsed_seconds` retry budget cap as belt-and-suspenders
- Extender alcance de verificación a `wallets-client` (cuando tenga endpoints reales)
- ERR-01 (mocked 403/429/5xx mapping), ERR-02 (mocked token TTL refresh) — v2 requirements del v1.0 backlog

### Deferred from v1.1 close (operator-accepted, see audit)

- LOC drop residual (iol -5.1%, matriz client.py -20% vs target ≥30%) — back-compat shims; closes when drivers migrate to the `Client`/`AsyncClient` class directly (v1.2 driver migration target)
- v1.1 Phase 7/8/9 human verification items (CI matrix Python 3.13 confirmation × 3 phases, live retry smoke, log legibility subjective UX) — operator-acknowledged at v1.1 close in STATE.md `Deferred Items`
