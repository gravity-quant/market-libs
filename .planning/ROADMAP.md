# Roadmap: market-libs — Verificación en vivo de clientes

## Milestones

- ✅ **v1.0 Verification cycle** — Phases 1-5 (shipped 2026-06-10) — see [`milestones/v1.0-ROADMAP.md`](./milestones/v1.0-ROADMAP.md)

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

### 📋 v1.1 / next milestone (not yet planned)

To be defined via `/gsd-new-milestone`. Carry-over candidates documented in `milestones/v1.0-MILESTONE-AUDIT.md` deferred section and `.planning/todos/pending/`:

- prod-vs-remarkets verification (D-MATZ-27 REQUIRED handoff)
- F-09 matriz ERROR-MAP fix + regression
- higyrus F-02 (get_listado_cuentas=0) investigation
- IOL refresh_token persistence between invocations
- HIGY multi-account iteration
- matriz_client.ws_client live verification
- matriz async surface (sync-only by design currently)
- v2 Requirements: ERR-01 (mocked 403/429/5xx mapping) + ERR-02 (mocked token TTL refresh)
- Driver bug bundle: D-MATZ-27 dedupe + findings file append-only (affects all 4 drivers)
- Code review WR-02..WR-07 quality concerns

## Progress

| Phase                                              | Milestone | Plans Complete | Status   | Completed  |
| -------------------------------------------------- | --------- | -------------- | -------- | ---------- |
| 1. Safety Harness & Verification Infrastructure    | v1.0      | 4/4            | Complete | 2026-05-28 |
| 2. Ámbito Verification                             | v1.0      | 3/3            | Complete | 2026-06-05 |
| 3. IOL Verification                                | v1.0      | 3/3            | Complete | 2026-06-06 |
| 4. Higyrus Verification                            | v1.0      | 4/4            | Complete | 2026-06-08 |
| 5. Matriz Verification                             | v1.0      | 4/4            | Complete | 2026-06-10 |

## Backlog

*(Candidate items for next milestone; see `.planning/todos/pending/` + v1.0-MILESTONE-AUDIT.md deferred section)*
