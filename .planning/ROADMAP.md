# Roadmap: market-libs — Verificación en vivo de clientes

## Milestones

- ✅ **v1.0 Verification cycle** — Phases 1-5 (shipped 2026-06-10) — see [`milestones/v1.0-ROADMAP.md`](./milestones/v1.0-ROADMAP.md)
- ✅ **v1.1 Tech Debt Cleanup** — Phases 6-11 (shipped 2026-06-14) — see [`milestones/v1.1-ROADMAP.md`](./milestones/v1.1-ROADMAP.md)
- ✅ **v1.2 Architecture + Auth/Ergonomics Carry-forwards** — Phases 12-17 (shipped 2026-06-25) — see [`milestones/v1.2-ROADMAP.md`](./milestones/v1.2-ROADMAP.md)
- ✅ **v1.3 Codegen Single-Source (libcst)** — Phases 18-19 (closed 2026-07-03 on signed SPIKE-006 NO-GO; Phase 19 REFAC-06 dropped) — see [`milestones/v1.3-ROADMAP.md`](./milestones/v1.3-ROADMAP.md)
- ✅ **v1.4 market-data-client** — Phases 20-24 (shipped 2026-07-31) — nuevo paquete cliente (solo lectura) contra la API primary-extractor con Auth0 client-credentials, verificado en vivo y publicado v0.1.0 — see [`milestones/v1.4-ROADMAP.md`](./milestones/v1.4-ROADMAP.md)
- 🚧 **v1.5 market-data-client · mutaciones** — Phases 25-28 (in progress) — extiende `market-data-client` (v0.2.0, lectura) con la superficie de **escritura** (symbols + calendar) detrás de un mutating-gate de seguridad, verificada en vivo de forma segura, y publicada v0.3.0

## Phases

### 🚧 v1.5 market-data-client · mutaciones (Phases 25-28) — IN PROGRESS

- [x] **Phase 25: Mutating-gate + Symbols write** — safety gate load-bearing (opt-in `mutating_allowed` + env gate + no-retry de no-idempotentes) + `POST /symbols`, `POST /symbols/batch`, `PATCH /symbols/{id}` — GATE-MD-01 + MUT-MD-01 (completed 2026-07-31)
- [ ] **Phase 26: Calendar write** — `PUT`/`DELETE /calendar/config`, `POST /calendar/config/preview`, `POST /calendar/holidays`, `DELETE /calendar/holidays/{day}` con `confirm` guardrail — MUT-MD-02
- [ ] **Phase 27: Verificación en vivo segura + fixes** — probes de mutación detrás del gate contra develop (create→verify→revert), revalida idempotencia DM-03, fixes in-cycle — LIVE-MUT-01
- [ ] **Phase 28: Release prep + publish v0.3.0** — bump minor + README changelog + PR → tag `market-data-client-v0.3.0` → GitHub Release — PUB-MUT-01

<details>
<summary>✅ v1.4 market-data-client (Phases 20-24) — SHIPPED 2026-07-31</summary>

- [x] Phase 20: Scaffold + Auth0 client-credentials + fundaciones de transporte (6/6 plans) — completed 2026-07-29 — AUTH-MD-01 + CORE-MD-01
- [x] Phase 21: Market data (lectura) + modelos (4/4 plans) — completed 2026-07-30 — MD-01
- [x] Phase 22: Instruments + symbols(read) + calendar(read) + modelos (2/2 plans) — completed 2026-07-30 — REF-MD-01
- [x] Phase 23: Verificación en vivo contra develop + fixes (2/2 plans) — completed 2026-07-31 — LIVE-MD-01 (apparatus verified; real credentialed sweep deferred to v1.5+)
- [x] Phase 24: Release prep + publish v0.1.0 (2/2 plans) — completed 2026-07-31 — PUB-MD-01 (`market-data-client-v0.1.0` published)

Full details: [`milestones/v1.4-ROADMAP.md`](./milestones/v1.4-ROADMAP.md)
Requirements archive: [`milestones/v1.4-REQUIREMENTS.md`](./milestones/v1.4-REQUIREMENTS.md)

</details>

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

<details>
<summary>✅ v1.3 Codegen Single-Source (libcst) (Phases 18-19) — CLOSED 2026-07-03 on signed NO-GO</summary>

- [x] Phase 18: libcst Codegen Tool-Choice Spike (SPIKE-006) (3/3 plans) — completed 2026-07-03 — evaluated `libcst >=1.8.0,<2` against the `D-RIGOR-02` 10-item gate on the un-migrated ámbito v1.2-head canary + matriz audit/deny-list inheritance → **signed NO-GO** (`sebadlf` 2026-07-03; 7 PASS / 3 FAIL, items 1/3/6 — content-absence / source-shape asymmetry, same root cause as SPIKE-005). libcst closes item 4 (`ruff check` I001 + ASYNC1xx) that unasync could not — partial gain, not regression — but cannot cross the content-absence boundary without a forbidden source migration (D-02). Guaranteed milestone deliverable; CODEGEN-01
- ~~Phase 19: Codegen Single-Source × 4 Packages (REFAC-06) — DROPPED 2026-07-03 (Phase 18 NO-GO); REFAC-06 permanently shelved, duplicate `client.py`/`aio.py` shells accepted as a structural feature~~

Full details: [`milestones/v1.3-ROADMAP.md`](./milestones/v1.3-ROADMAP.md)
Requirements archive: [`milestones/v1.3-REQUIREMENTS.md`](./milestones/v1.3-REQUIREMENTS.md)

</details>

## Phase Details (v1.5)

### Phase 25: Mutating-gate + Symbols write

**Goal**: El consumidor puede crear/actualizar symbols detrás de un gate de seguridad opt-in que hace **imposible disparar una mutación por accidente** — el gate es load-bearing y se construye primero; symbols es la primera superficie de mutación que lo ejercita.
**Depends on**: Phase 24 (v1.4 read surface v0.2.0 — el paquete base con `_core.py`, transporte, auth Auth0)
**Requirements**: GATE-MD-01, MUT-MD-01
**Success Criteria** (what must be TRUE):

  1. Un `Client()` / `AsyncClient()` por default **rehúsa toda mutación** con un `MarketDataMutationNotAllowedError` tipado (⊂ `MarketDataError`) — no se emite request HTTP alguno.
  2. Con `mutating_allowed=True` (constructor o `configure()`) **y** el host/base_url esperado, el consumidor puede `create_symbol` (`NewSymbol`), `create_symbols` (batch 1–500, `NewSymbols`) y `update_symbol` (`SymbolPatch`) en sync y async.
  3. Los request-bodies serializan desde modelos tipados a JSON; las respuestas `201`/`200` parsean a `SafeModel` tolerantes y `422` levanta un error tipado.
  4. Las operaciones no idempotentes se despachan con `request.extensions["idempotent"]=False` per DM-03, de modo que el transporte de retries **nunca** las reintenta.
  5. Paridad sync/async: idéntico comportamiento en `client.py` y `aio.py`, dispatch vía builders `_core.py`; 4 gates verdes (ruff/format/mypy-strict/pytest).

**Plans**: 3/3 plans complete
**Wave 1**

- [x] 25-01-PLAN.md — Mutating-gate infrastructure: `MarketDataMutationNotAllowedError`, `_ClientState` gate fields, `_ensure_mutation_allowed()` + opt-in params (dual sync/async), conftest reset, adversarial gate tests (Wave 1)
- [x] 25-02-PLAN.md — Request models (`NewSymbol`/`NewSymbols`/`SymbolPatch`, 1–500 `ValueError`) + 3 pure `_core` builders (idempotent=True) with unit tests (Wave 1)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 25-03-PLAN.md — Symbols-write dispatch (`create_symbol`/`create_symbols`/`update_symbol` methods + shims, dual sync/async) + `__init__` re-exports + wire/refusal/parity tests (Wave 2)

### Phase 26: Calendar write

**Goal**: El consumidor puede administrar la configuración de calendario y los feriados detrás del mismo mutating-gate, con el guardrail `confirm` del servidor expuesto explícitamente.
**Depends on**: Phase 25 (necesita el mutating-gate; 25 es prerequisito — no paraleliza con nada antes del gate)
**Requirements**: MUT-MD-02
**Success Criteria** (what must be TRUE):

  1. Detrás del gate, el consumidor puede `set_calendar_config` (`PUT`, `MarketHoursIn`), `delete_calendar_config` (`DELETE`), `preview_calendar_config` (`POST` preview), `add_holidays` (`POST`, `HolidaysIn`) y `delete_holiday(day)` (`DELETE`) en sync y async.
  2. `set_calendar_config` expone `confirm` con **default `False`** (guardrail del servidor) y respeta el resto de defaults de `MarketHoursIn`.
  3. Los request-models tipados `MarketHoursIn`/`HolidayIn`/`HolidaysIn` serializan a JSON reusando `_params.drop_none`; el `preview` pasa por el gate (es POST) pero **no persiste** — la excepción read-safe queda documentada.
  4. La idempotencia por-endpoint se setea per DM-03 (`POST /calendar/holidays` con `idempotent=False` → no retry; el resto retry-safe).
  5. Paridad sync/async y enforcement del gate idénticos a Phase 25; tests mockeados (gate, serialización, defaults, `confirm`, `422`, paridad) y 4 gates verdes.

**Plans**: 4/4 plans complete

Plans:
**Wave 1**

- [x] 26-01-PLAN.md — request-models `MarketHoursIn`/`HolidayIn`/`HolidaysIn` (defaults OpenAPI, `confirm=False`, `drop_none`, bound 1–500) [wave 1]
- [x] 26-02-PLAN.md — 5 builders puros en `_core.py` + guard de path-safety D-18 + parser passthrough tolerante [wave 1]

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 26-03-PLAN.md — los 5 métodos gated + 10 shims en `client.py`/`aio.py` + tests de dispatch y serialización [wave 2]

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 26-04-PLAN.md — matriz adversarial del gate + no-retry D-15 + re-exports/paridad + 4 gates verdes [wave 3]

### Phase 27: Verificación en vivo segura + fixes

**Goal**: Toda la superficie de mutación (sync + async) se ejercita en vivo contra develop de forma **destructiva pero segura** (create→verify→revert), la idempotencia asumida se revalida, y toda divergencia se corrige en el mismo ciclo.
**Depends on**: Phases 25 y 26 (necesita ambas superficies de mutación construidas)
**Requirements**: LIVE-MUT-01
**Success Criteria** (what must be TRUE):

  1. `main_market_data.py` ejercita todas las mutaciones (symbols + calendar) sync+async **detrás del mutating-gate** (`mutating_allowed=True` sólo bajo env-gate explícito + host develop exacto, patrón `verification/mutation_gate.py`).
  2. Cada probe destructivo usa **identificadores de prueba dedicados** y completa un ciclo de cleanup (crear→verificar→revertir con el DELETE/PATCH correspondiente); la config real de mercado **nunca** se toca sin `confirm`.
  3. La idempotencia por-endpoint (DM-03) se **revalida contra el comportamiento en vivo** antes de confiar el retry-behavior; retry-safety confirmado o corregido.
  4. Toda divergencia (shape de respuesta, códigos, idempotencia real) se documenta en findings y se corrige in-cycle, espejada sync/async, con un test de regresión mockeado por fix.
  5. Cycle closure PASS.

**Plans**: TBD

### Phase 28: Release prep + publish v0.3.0

**Goal**: `market-data-client` se publica como `v0.3.0` (minor bump, no breaking sobre la superficie de lectura v0.2.0) por el pipeline de tags.
**Depends on**: Phase 27 (la superficie de mutación verificada en vivo)
**Requirements**: PUB-MUT-01
**Success Criteria** (what must be TRUE):

  1. Versión bumpeada a `0.3.0` en `pyproject` + `__version__`; README changelog documenta las nuevas mutaciones + el opt-in del gate; `uv.lock` refrescado.
  2. PR abierto; los 15 checks de CI verdes (incl. los jobs de `market-data-client` en la matrix py3.12 + py3.13).
  3. Merge a `main`; tag `market-data-client-v0.3.0` empujado → `release.yml` (unedited) → GitHub Release con wheel + sdist.
  4. El bump es minor no-breaking: la superficie de lectura v0.2.0 permanece 100% compatible.

**Plans**: TBD

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
| 18. libcst Codegen Tool-Choice Spike (SPIKE-006)            | v1.3      | 3/3   | Complete    | 2026-07-03 |
| 19. Codegen Single-Source × 4 (DROPPED — Phase 18 NO-GO)    | v1.3      | -     | Dropped     | 2026-07-03 |
| 20. Scaffold + Auth0 client-credentials + transport         | v1.4      | 6/6   | Complete    | 2026-07-29 |
| 21. Market data (read) + models                             | v1.4      | 4/4   | Complete    | 2026-07-30 |
| 22. Instruments/segments/symbols/calendar (read) + models   | v1.4      | 2/2   | Complete    | 2026-07-30 |
| 23. Live verification against develop + fixes               | v1.4      | 2/2   | Complete    | 2026-07-31 |
| 24. Release prep + publish v0.1.0                           | v1.4      | 2/2   | Complete    | 2026-07-31 |
| 25. Mutating-gate + Symbols write                           | v1.5      | 3/3 | Complete    | 2026-07-31 |
| 26. Calendar write                                          | v1.5      | 4/4 | Complete   | 2026-08-01 |
| 27. Safe live verification + fixes                          | v1.5      | 0/?   | Not started | -          |
| 28. Release prep + publish v0.3.0                           | v1.5      | 0/?   | Not started | -          |

## Backlog

*(Candidate items for next milestone; see `.planning/todos/pending/` + v1.0/v1.1/v1.2/v1.3 milestone audits deferred sections)*

### Deferred to v1.5+ (from v1.4 — market-data-client v2 requirements)

- **MUT-MD-01 / MUT-MD-02** — market-data-client mutations: symbols (`POST /symbols`, `POST /symbols/batch`, `PATCH /symbols/{id}`) + calendar (`PUT/DELETE /calendar/config`, `POST /calendar/config/preview`, `POST /calendar/holidays`, `DELETE /calendar/holidays/{day}`) — require the security mutating-gate
- **STREAM-MD-01** — market-data-client SSE streaming (`GET /marketdata/stream`, `interval` param) via a dedicated transport (matriz `ws_client` pattern)
- **SEC-MD-01** — market-data-client Auth0 token disk cache (`_token_cache.py` + platformdirs, atomic + flock + 0600)
- **SEC-MD-02** — market-data-client JWT signature validation (RS256 against Auth0 JWKS)
- **LIVE-MD-01 real credentialed sweep** — the apparatus is verified; the actual live run against `market-data-develop.bbsa.com.ar` still awaits Auth0 creds + VPN/allowlist

### Deferred to v1.4+ (from v1.3 planning)

- prod-vs-remarkets verification (D-MATZ-27 REQUIRED handoff — still deferred through v1.0/v1.1/v1.2/v1.3/v1.4)
- `matriz_client.ws_client` live verification (WebSocket streaming en daemon thread)
- `cryptography.fernet` token encryption at-rest (operator authorization required; threat-boundary expansion)
- Code-review CR-01 v1.2 Phase 14 (`configure()` no limpia el on-disk token cache de IOL)
- Extender alcance de verificación a `wallets-client` (cuando tenga endpoints reales)

### Resolved in v1.3 — REFAC-06 permanently shelved

- **REFAC-06** — codegen single-source for `client.py`/`aio.py` transport shells × 4 packages. **Permanently shelved 2026-07-03**: two dedicated spikes (unasync SPIKE-005 in v1.2 Phase 12, libcst SPIKE-006 in v1.3 Phase 18) both returned a signed NO-GO for the same content-absence / source-shape-asymmetry root cause under the un-migrated D-02 bar. The duplicate `client.py`/`aio.py` shells are now an **accepted structural feature** of the codebase (the known dual-surface duplication documented in CLAUDE.md). Do not re-open without a new tool class that can synthesize content-absent constructs, or a decision to relax the no-source-migration constraint (D-02). See `.planning/spikes/SPIKE-006-libcst-codegen-tool-choice/DECISION.md` + `Skill("spike-findings-codegen-market-libs")`.

### Deferred to v1.2+ (from v1.1 planning — REFAC-05/SEC-01/ERG-01 shipped in v1.2)

- Automatic `Idempotency-Key` header para retried POSTs
- `findings.toml` machine-readable side-file
- `Client.from_env()` classmethod for explicit env-reading (SKIPPED v1.2 — industry survey found ZERO SDKs with this pattern; implicit env fallback already exists)
- `request_id` UUID per `_request()` invocation threaded through retry log records
- `max_elapsed_seconds` retry budget cap as belt-and-suspenders
- ERR-01 (mocked 403/429/5xx mapping), ERR-02 (mocked token TTL refresh) — v2 requirements del v1.0 backlog
