# Roadmap: market-libs — Verificación en vivo de clientes

## Milestones

- ✅ **v1.0 Verification cycle** — Phases 1-5 (shipped 2026-06-10) — see [`milestones/v1.0-ROADMAP.md`](./milestones/v1.0-ROADMAP.md)
- ✅ **v1.1 Tech Debt Cleanup** — Phases 6-11 (shipped 2026-06-14) — see [`milestones/v1.1-ROADMAP.md`](./milestones/v1.1-ROADMAP.md)
- ✅ **v1.2 Architecture + Auth/Ergonomics Carry-forwards** — Phases 12-17 (shipped 2026-06-25) — see [`milestones/v1.2-ROADMAP.md`](./milestones/v1.2-ROADMAP.md)

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

<details>
<summary>✅ v1.2 Architecture + Auth/Ergonomics Carry-forwards (Phases 12-17) — SHIPPED 2026-06-25</summary>

- [x] Phase 12: Codegen Spike (4/3 plans) — completed 2026-06-14 — SPIKE-005 unasync vs libcst on ámbito canary + matriz worst-case; **NO-GO** (strict D-RIGOR-01 reading, 3/8 items FAIL, source-shape asymmetry, 0 unfixable hunks); REFAC-06 deferred to v1.3; REFAC-06 (spike-gated)
- [x] Phase 13: Cross-Package Ergonomics `with_options(max_retries=N)` (5/5 plans) — completed 2026-06-15 — shared-view clone + `request.extensions["max_attempts"]`; CRITICAL matriz mutation-gate merge gate (new_order under 503 = exactly 1 request); ERG-01
- [x] Phase 14: IOL Disk Persistence (3/3 plans) — completed 2026-06-24 — `_token_cache.py` + `platformdirs` + atomic write + `fcntl.flock` + 0600 + failed-refresh cleanup + caplog no-leak; SEC-01
- [x] Phase 15: Driver Migration × 4 (5/4 plans) — completed 2026-06-24 — ONE `Client()`/`AsyncClient()` per `main()` + AST regression-guard × 4 + probe-name stability vs LIVE-01 `71bf201`; REFAC-05
- ~~Phase 16: Codegen Single-Source — DROPPED 2026-06-14 (Phase 12 NO-GO); REFAC-06 → v1.3~~
- [x] Phase 17: Final Live Re-verification × 4 (3/3 plans) — completed 2026-06-25 — operator dispositions ambito/iol/higyrus/matriz + cycle closure × 4 PASS + traceability flip + 0-BLOCKER integration audit; LIVE-03

Full details: [`milestones/v1.2-ROADMAP.md`](./milestones/v1.2-ROADMAP.md)
Requirements archive: [`milestones/v1.2-REQUIREMENTS.md`](./milestones/v1.2-REQUIREMENTS.md)

</details>

## Progress

| Phase                                                       | Milestone | Plans | Status      | Completed  |
|-------------------------------------------------------------|-----------|-------|-------------|------------|
| 1. Safety Harness & Verification Infrastructure             | v1.0      | 4/4   | Complete    | 2026-05-28 |
| 2. Ámbito Verification                                      | v1.0      | 3/3   | Complete    | 2026-06-05 |
| 3. IOL Verification                                         | v1.0      | 3/3   | Complete    | 2026-06-06 |
| 4. Higyrus Verification                                     | v1.0      | 4/4   | Complete    | 2026-06-08 |
| 5. Matriz Verification                                      | v1.0      | 4/4   | Complete    | 2026-06-10 |
| 6. Compat Safety Net + Client Class Skeleton                | v1.1      | 7/7   | Complete    | 2026-06-11 |
| 7. `_core.py` Extraction — Sync/Async Logic Dedup           | v1.1      | 6/6   | Complete    | 2026-06-12 |
| 8. Retries, Backoff, Structured Logging                     | v1.1      | 6/6   | Complete    | 2026-06-13 |
| 9. Deferred Bug Fixes                                       | v1.1      | 4/4   | Complete    | 2026-06-13 |
| 10. matriz `aio.py` Creation + TokenStore                   | v1.1      | 4/4   | Complete    | 2026-06-14 |
| 11. Harness Hardening + Code Review + Live Re-verification  | v1.1      | 3/3   | Complete    | 2026-06-14 |
| 12. Codegen Spike                                           | v1.2      | 4/3   | Complete    | 2026-06-14 |
| 13. Cross-Package Ergonomics (`with_options`)               | v1.2      | 5/5   | Complete    | 2026-06-15 |
| 14. IOL Disk Persistence                                    | v1.2      | 3/3   | Complete    | 2026-06-24 |
| 15. Driver Migration × 4                                    | v1.2      | 5/4   | Complete    | 2026-06-24 |
| 16. Codegen Single-Source (DROPPED — Phase 12 NO-GO)        | v1.2      | -     | Dropped     | 2026-06-14 |
| 17. Final Live Re-verification × 4                          | v1.2      | 3/3   | Complete    | 2026-06-25 |

## Backlog

*(Candidate items for next milestone; see `.planning/todos/pending/` + v1.0/v1.1 milestone audits deferred sections)*

### Deferred to v1.3+ (from v1.2 close)

- **REFAC-06** — unasync/codegen single-source for `client.py`/`aio.py` transport shells × 4 packages. Phase 12 NO-GO 2026-06-14 (source-shape asymmetry). Re-evaluate via a v1.3 `libcst >=1.8.0,<2` spike (AST-level codemod preserves whitespace/comments + can rewrite source-shape asymmetry). See `.planning/spikes/SPIKE-005-codegen-tool-choice/NO-GO.md` + `.planning/todos/pending/spike-codegen-libcst-v1.3.md`.
- prod-vs-remarkets verification (D-MATZ-27 REQUIRED handoff — still deferred)
- `matriz_client.ws_client` live verification (WebSocket streaming en daemon thread)
- `cryptography.fernet` token encryption at-rest (operator authorization required; threat-boundary expansion)

### Deferred to v1.2+ (from v1.1 planning — REFAC-05/SEC-01/ERG-01 now shipped in v1.2)

- Automatic `Idempotency-Key` header para retried POSTs
- `findings.toml` machine-readable side-file
- `Client.from_env()` classmethod for explicit env-reading (SKIPPED v1.2 — industry survey found ZERO SDKs with this pattern; implicit env fallback already exists)
- `request_id` UUID per `_request()` invocation threaded through retry log records
- `max_elapsed_seconds` retry budget cap as belt-and-suspenders
- Extender alcance de verificación a `wallets-client` (cuando tenga endpoints reales)
- ERR-01 (mocked 403/429/5xx mapping), ERR-02 (mocked token TTL refresh) — v2 requirements del v1.0 backlog
