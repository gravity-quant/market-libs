# Roadmap: market-libs — Verificación en vivo de clientes

## Milestones

- ✅ **v1.0 Verification cycle** — Phases 1-5 (shipped 2026-06-10) — see [`milestones/v1.0-ROADMAP.md`](./milestones/v1.0-ROADMAP.md)
- ✅ **v1.1 Tech Debt Cleanup** — Phases 6-11 (shipped 2026-06-14) — see [`milestones/v1.1-ROADMAP.md`](./milestones/v1.1-ROADMAP.md)
- ✅ **v1.2 Architecture + Auth/Ergonomics Carry-forwards** — Phases 12-17 (shipped 2026-06-25) — see [`milestones/v1.2-ROADMAP.md`](./milestones/v1.2-ROADMAP.md)
- ✅ **v1.3 Codegen Single-Source (libcst)** — Phases 18-19 (closed 2026-07-03 on signed SPIKE-006 NO-GO; Phase 19 REFAC-06 dropped) — see [`milestones/v1.3-ROADMAP.md`](./milestones/v1.3-ROADMAP.md)
- 🚧 **v1.4 market-data-client** — Phases 20-24 (in progress; started 2026-07-29) — nuevo paquete cliente (solo lectura) contra la API primary-extractor con Auth0 client-credentials, verificado en vivo y publicado v0.1.0

## Phases

### 🚧 v1.4 market-data-client (Phases 20-24) — IN PROGRESS

**Milestone goal:** Crear el paquete `market-data-client` (import `market_data_client`) que exponga la superficie de **lectura** de la API primary-extractor (`https://market-data-develop.bbsa.com.ar/api`, OpenAPI 3.1) con Auth0 client-credentials, replicando las decisiones arquitectónicas de los paquetes existentes, verificarlo en vivo contra develop y publicarlo como `v0.1.0` por el pipeline de tags. Plan fuente: [`.future_plans/market_data.md`](../../.future_plans/market_data.md).

- [x] Phase 20: Scaffold + Auth0 client-credentials + fundaciones de transporte (AUTH-MD-01, CORE-MD-01) (completed 2026-07-29)
- [ ] Phase 21: Market data (lectura) + modelos (MD-01)
- [ ] Phase 22: Instruments + symbols(read) + calendar(read) + modelos (REF-MD-01)
- [ ] Phase 23: Verificación en vivo contra develop + fixes (LIVE-MD-01)
- [ ] Phase 24: Release prep + publish v0.1.0 (PUB-MD-01)

Detalle por fase: ver **## Phase Details (v1.4)** más abajo. **Diferido a v1.5+:** mutaciones (symbols/calendar), streaming SSE `GET /marketdata/stream`, cache de token en disco, validación de firma JWT (REQUIREMENTS.md § v2).

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

## Phase Details (v1.4)

### Phase 20: Scaffold + Auth0 client-credentials + fundaciones de transporte

**Goal:** Levantar el paquete `market-data-client` espejando la estructura de `iol-client`, con autenticación Auth0 client-credentials (token cache TTL + refresh, dual sync/async) y las fundaciones de transporte (retries, logging redactado, exceptions, `configure()`, health).

**Requirements:** AUTH-MD-01, CORE-MD-01
**Depends on:** — (primera fase del milestone)
**Plans:** 6/6 plans complete

Plans:
**Wave 1**

- [x] 20-01-PLAN.md — Wave 1: package scaffold + exceptions + `_state` + transport pair (verbatim)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 20-02-PLAN.md — Wave 2 (tdd): `_core.py` pure Auth0 builders/parsers + `raise_for_response` + health builders
- [x] 20-03-PLAN.md — Wave 2 (tdd): `_logging.py` RedactingFilter + `attach()` (client_secret patterns)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 20-04-PLAN.md — Wave 3: `client.py` sync shell (absolute token URL, single-grant lifecycle, anonymous health)
- [x] 20-05-PLAN.md — Wave 3: `aio.py` async shell (per-loop double-checked lock, single-grant lifecycle)

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 20-06-PLAN.md — Wave 4: `__init__.py` + `conftest.py` + lifecycle/health tests + 4-gate run

**Success criteria:**

1. `import market_data_client` y `from market_data_client import aio` funcionan; `__version__ == "0.1.0"`; `pyproject.toml` con hatchling + deps (httpx, python-dotenv, tenacity) y `py.typed`.
2. La autenticación client_credentials obtiene y cachea el token (mock) y lo refresca cuando expira el TTL, en sync y async (`asyncio.Lock` double-checked).
3. `GET /health` y `GET /health/feed` responden vía el transporte con retries; la jerarquía de excepciones tipadas mapea 401/403→Auth, 429→RateLimit, otros→APIError.
4. Cero fugas de credencial en logs (test caplog con `RedactingFilter`).
5. Los 4 gates (ruff, ruff format, mypy strict, pytest) verdes para el paquete.

### Phase 21: Market data (lectura) + modelos

**Goal:** Implementar la superficie de lectura de market data (`GET /marketdata`, `GET|POST /marketdata/latest`) con modelos `SafeModel` y paridad `with_options`.

**Requirements:** MD-01
**Depends on:** Phase 20

**Success criteria:**

1. `get_market_data(...)`, `get_latest(...)` y `get_latest_batch(...)` (o nombres equivalentes) existen en sync y async, con todos los query params del OpenAPI serializados correctamente.
2. Las respuestas se deserializan a dataclasses `SafeModel` con `received_at` como campo de primera clase; `from_api` tolera payloads parciales/None sin romper.
3. `client.with_options(max_retries=N)` se propaga a estas llamadas como shared-view clone, sync y async.
4. Tests mockeados (pytest-httpx) cubren serialización de params + tolerancia de modelos, verdes.

### Phase 22: Instruments + symbols(read) + calendar(read) + modelos

**Goal:** Cubrir la superficie de datos de referencia de lectura (instruments, segments, symbols, calendar) con modelos tipados.

**Requirements:** REF-MD-01
**Depends on:** Phase 20 (paraleliza con Phase 21)

**Success criteria:**

1. `GET /instruments` (con todos sus filtros), `GET /instruments/segments`, `GET /symbols`, `GET /calendar`, `GET /calendar/config` implementados en sync y async.
2. Cada endpoint devuelve modelos tipados adecuados (colecciones con guardas de 204/None → `[]`).
3. Tests mockeados verdes; paridad sync/async verificada.

### Phase 23: Verificación en vivo contra develop + fixes

**Goal:** Ejercitar toda la superficie pública (sync + async) en vivo contra develop, detectar divergencias cliente-vs-servicio y corregirlas en el ciclo.

**Requirements:** LIVE-MD-01
**Depends on:** Phases 21, 22

**Success criteria:**

1. `main_market_data.py` construye una `Client()` + una `AsyncClient()` y threadea cada probe; ejercita health + market data + reference read contra develop con credenciales Auth0.
2. Reutiliza la infra `verification/` (split live/offline con `--live`, redacción de credenciales); sin mutating-gate (solo lectura).
3. Toda divergencia (campos de modelo, semántica de `received_at`/staleness, manejo de params) se documenta en `market-data-findings.md` y se corrige in-cycle, espejada sync/async.
4. Cycle closure PASS (patrón DRIFT); cada fix con test de regresión mockeado.

### Phase 24: Release prep + publish v0.1.0

**Goal:** Publicar `market-data-client-v0.1.0` por el mismo pipeline que el resto de los paquetes.

**Requirements:** PUB-MD-01
**Depends on:** Phase 23

**Success criteria:**

1. README del paquete (uso, env vars, auth Auth0); `version="0.1.0"` + `__version__` alineados; `market-data-client` agregado a `matrix.package` en `ci.yml`; `uv.lock` regenerado.
2. CLAUDE.md (listado de paquetes + tablas de arquitectura) y MEMORY actualizados.
3. PR → CI verde (los 13 checks incluyendo el nuevo paquete) → merge → tag `market-data-client-v0.1.0`.
4. GitHub Release creado con wheel + sdist; el paquete es instalable vía git subdir / wheel.

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

## Backlog

*(Candidate items for next milestone; see `.planning/todos/pending/` + v1.0/v1.1/v1.2/v1.3 milestone audits deferred sections)*

### Deferred to v1.4+ (from v1.3 planning)

- prod-vs-remarkets verification (D-MATZ-27 REQUIRED handoff — still deferred through v1.0/v1.1/v1.2/v1.3)
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
