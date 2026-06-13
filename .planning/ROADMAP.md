# Roadmap: market-libs — Verificación en vivo de clientes

## Milestones

- ✅ **v1.0 Verification cycle** — Phases 1-5 (shipped 2026-06-10) — see [`milestones/v1.0-ROADMAP.md`](./milestones/v1.0-ROADMAP.md)
- 🟢 **v1.1 Tech Debt Cleanup** — Phases 6-11 (planned 2026-06-10)

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

### v1.1 Tech Debt Cleanup (Phases 6-11)

- [x] **Phase 6: Compat Safety Net + Client Class Skeleton** — Golden public-surface snapshot, fixture-reaches-production guard, then `Client`/`AsyncClient` per package with PEP 562 compat shim (no breaking change). (completed 2026-06-11)
- [x] **Phase 7: `_core.py` Extraction — Sync/Async Logic Dedup** — Pure builders/parsers per package; `client.py` and `aio.py` collapse to transport shells; import-linter rule blocks `_core.py` from importing `client.py`/`aio.py`. (completed 2026-06-12)
- [x] **Phase 8: Retries, Backoff, Structured Logging** — `tenacity` with full-jitter backoff and `Retry-After` cap (60 s); mutating-aware retry gate via `RequestSpec.idempotent`; per-package `getLogger` + `NullHandler` + `RedactingFilter`. (completed 2026-06-13)
- [ ] **Phase 9: Deferred Bug Fixes** — F-09 matriz ERROR-MAP, F-02 higyrus `get_listado_cuentas=0`, IOL refresh_token in-instance persistence, HIGY multi-account iteration; each lands once in `_core.py` and propagates to both surfaces.
- [ ] **Phase 10: matriz `aio.py` Creation + TokenStore** — Full async REST surface for matriz; `TokenStore` with `threading.Lock` callable from sync, asyncio, and ws_client daemon thread. **Research flag**: TokenStore spike before plan.
- [ ] **Phase 11: Harness Hardening + Code Review Close-out + Live Re-verification** — `verification/findings.py` append-only with BEGIN/END zone parser, content-addressed dedup, operator-field preservation; WR-01..02, WR-04, WR-06..08 close-out; live `main_*.py --live × 4` final gate including matriz async.

## Phase Details

### Phase 6: Compat Safety Net + Client Class Skeleton

**Goal**: Establecer red de seguridad antes del refactor y entregar la clase `Client`/`AsyncClient` por paquete con la API top-level intacta vía compat layer.
**Depends on**: Nothing (first phase of v1.1; v1.0 is archived)
**Requirements**: REFAC-01, REFAC-02
**Success Criteria** (what must be TRUE):

  1. `verification/test_public_surface.py` existe y snapshotea cada atributo público y signature de los 4 paquetes; el test corre verde antes del primer refactor y sigue verde después.
  2. Por cada paquete, el "fixture-reaches-production" guard test (`monkeypatch.setattr(pkg.client, "_token", "sentinel"); pkg.get_X(...)`) verifica que el sentinel aparece en el header `Authorization` del wire request.
  3. Los 4 paquetes exponen `Client` (sync) y `AsyncClient` (async) con `close()`/`aclose()` y context managers (`with`/`async with`); estado `base_url`/credenciales/token/http_client/refresh_token vive en `_ClientState` por instancia.
  4. La API top-level (`pkg.get_X(...)`, `pkg.configure(...)`) sigue funcionando 100% sin cambios para callers; los 277 tests mockeados pasan verde después del refactor (conftest migrado a `configure(token=..., token_expires_at=...)` donde aplique).
  5. `ruff` + `mypy strict` + `pytest` corren verde en CI al finalizar la phase para ambos Python 3.12 y 3.13.**Plans**: 7 plans

**Wave 1**

- [x] 06-01-PLAN.md — Public surface snapshot harness + regen script + 4 baseline snapshot files (REFAC-01)
- [x] 06-02-PLAN.md — Fixture-reaches-production guard tests (4 sync + 3 async + 1 matriz-async-skip) using legacy monkeypatch pattern (REFAC-01)
- [x] 06-03-PLAN.md — ambito-financiero-client skeleton: _state.py + Client + AsyncClient + PEP 562 shim + conftest migration + snapshot update (REFAC-02)
- [x] 06-04-PLAN.md — iol-client skeleton: _state.py + Client + AsyncClient with OAuth refresh + Pitfall #3 shim addendum + 15+ inline monkeypatch migrations + snapshot + guard migration (REFAC-02)
- [x] 06-05-PLAN.md — higyrus-client skeleton: _state.py + Client + AsyncClient + _token_ts→token_expires_at rename mapping + URL-encoding preservation + snapshot + guard migration (REFAC-02)
- [x] 06-06-PLAN.md — matriz-client skeleton: _state.py + Client (X-Auth-Token header) + stub AsyncClient + _base_url shim extension (Open Q #4) + ws_client.py + cross-package mutation_gate test migration + snapshot + guard migration (REFAC-02)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 06-07-PLAN.md — CI green gate: full pytest + ruff + mypy strict + snapshot diff + driver smoke + operator checkpoint on CI 3.12 + 3.13 matrix (REFAC-01, REFAC-02)

**Cross-cutting constraints:**

- D-05: 1 commit atómico por paquete (`_state.py` + `Client`/`AsyncClient` + shim PEP 562 + migración de conftest del paquete + remoción de globals legacy).

### Phase 7: `_core.py` Extraction — Sync/Async Logic Dedup

**Goal**: Eliminar la duplicación de lógica entre `client.py` y `aio.py` por paquete; ambos quedan como shells de transporte sobre helpers puros en `_core.py`.
**Depends on**: Phase 6
**Requirements**: REFAC-03, CR-03, CR-05
**Success Criteria** (what must be TRUE):

  1. Por cada paquete, `_core.py` contiene los builders `build_X_request(...) → RequestSpec` y parsers `parse_X_response(json) → typed result` para cada endpoint, más `raise_for_response`, `unwrap_envelope` y los auth-flow primitives; `_core.py` no importa nada de `httpx.Client`/`httpx.AsyncClient` ni de `client.py`/`aio.py`.
  2. CI rule (import-linter o equivalente grep) bloquea el merge si `_core.py` importa de `client.py`/`aio.py`; regression test con sentinels distintos sync vs async (`SYNC-sentinel` vs `ASYNC-sentinel`) detecta cualquier re-coupling.
  3. `client.py` y `aio.py` de cada paquete miden ≤30-50 LOC por endpoint group (LOC drop ≥30% vs baseline Phase 6); las bodies sync/async son idénticas excepto por la línea de transporte (`self._http.request(...)` vs `await self._http.request(...)`).
  4. CR-03 cerrado: el `_request` de matriz consume el response body explícitamente antes de raise cuando `data.status=="ERROR"` (no más resource leak potencial con HTTP/2).
  5. CR-05 cerrado: las 18 sweep probes de `main_matriz.py` refactorizadas a un helper único `_envelope_probe(envelope_key=...)` que preserva las 2 risk probes sin envelope (`envelope_key=None`); todos los 277+ tests siguen verde.

**Plans**: 6 plans

**Wave 1**

- [x] 07-01-PLAN.md — CI gates infrastructure: import-linter v2.11 setup + 4 forbidden contracts + 4 `_core.py` placeholders + cross-leak sentinel test parametrizado en `verification/test_sync_async_isolation.py` (matriz skip) + CI step `lint-imports` (REFAC-03)

**Wave 2** *(blocked on Wave 1 completion; 4 plans can run in parallel — no file overlap)*

- [x] 07-02-PLAN.md — ámbito canary: `ambito_financiero_client/_core.py` + transport shells + tests/test_core.py + B8 D-04 alias + LOC drop ≥30% (REFAC-03)
- [x] 07-03-PLAN.md — iol: `iol_client/_core.py` + auth-flow primitives + CR-01 conditional refresh_token rotation preserved + transport shells + LOC drop ≥30% (REFAC-03)
- [x] 07-04-PLAN.md — higyrus: `higyrus_client/_core.py` + URL-encoding quirk encapsulated in builders + transport shells + LOC drop ≥30% (REFAC-03)
- [x] 07-05-PLAN.md — matriz ATOMIC: `matriz_client/_core.py` + CR-03 closure (`parse_envelope_response` body-consume-then-raise) + CR-05 closure (`_envelope_probe` x18 in `main_matriz.py`) + snapshot guard + back-compat wrapper (REFAC-03, CR-03, CR-05)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 07-06-PLAN.md — Green gate consolidation: full pytest matrix Python 3.12 + 3.13 + ruff + mypy strict + lint-imports + cross-leak sentinel + matriz sweep snapshot + Phase 6 public-surface snapshot (zero diff) + `07-VALIDATION.md` con `nyquist_compliant: true` + operator checkpoint (REFAC-03)

### Phase 8: Retries, Backoff, Structured Logging

**Goal**: Reliability via retries transparentes con jitter y mutation gate + observability vía logging estructurado redactado por paquete.
**Depends on**: Phase 7
**Requirements**: RELY-01, RELY-02, RELY-03, RELY-04, LOG-01, LOG-02, LOG-03
**Success Criteria** (what must be TRUE):

  1. Por cada paquete, `RetryTransport`/`AsyncRetryTransport` retrya en 408/409/429/≥500 + `httpx.ConnectError`/`ConnectTimeout`/`ReadTimeout` con default `max_attempts=2` y backoff exponencial full-jitter; honra `Retry-After` (delta-seconds + HTTP-date) con cap 60 s; regression test mockea 429+`Retry-After:30` y verifica delay aplicado.
  2. Mutation-aware retry gate funciona end-to-end: `RequestSpec.idempotent: bool` default `False`; GET endpoints lo marcan `True`; regression test con POST mockeado contra 503 verifica EXACTAMENTE 1 outgoing request (no retry). `AuthError`/`PrimaryAPIError`/`HigyrusAPIError` NUNCA están en el `retry_on=` de tenacity.
  3. Manejo explícito de 401 en `_request()` con exactly-one re-auth attempt (clear token → `_ensure_token()` → retry once); regression test con 401→200 verifica 2 outgoing requests con headers refrescados; 401→401 verifica exactly 2 requests y `AuthError` raised.
  4. Por cada paquete, `logging.getLogger("<pkg>")` configurado con `NullHandler` en `__init__.py`; CI grep rule bloquea `logging.basicConfig` y `logging.root` en `packages/*/src/`; regression test verifica `logging.root.handlers` unchanged tras `import <pkg>`.
  5. `RedactingFilter` por paquete redacta Bearer/X-Auth-Token/`password=`/IOL refresh_token/Higyrus JSON password aunque el consumer habilite DEBUG; regression test con `caplog` verifica que el token literal NO aparece en ningún `record.getMessage()` ni `record.args`. Convención de niveles (DEBUG/INFO/WARNING/ERROR) y campos estructurados (`package`, `method`, `url`, `status_code`, `attempt`, `duration_ms`, `account_id` cuando aplique) aplicada en `_transport.py`/`_atransport.py`/`client.py`/`aio.py`.

**Plans**: 6 plans

**Wave 1**

- [x] 08-01-PLAN.md — Cross-cutting infra (tests-first): tenacity dep + 6 cross-cutting guard tests in verification/ + CI grep lint-logging + ruff LOG ruleset; NO packages/<pkg>/src/ touched (RELY-01..04, LOG-01..03)

**Wave 2** *(blocked on Wave 1)*

- [x] 08-02-PLAN.md — ámbito canary: _transport.py + _atransport.py + _logging.py + Client/AsyncClient/configure() 2 new kwargs (max_retries, http_client) + snapshot update; no 401 re-auth (no auth) (RELY-01..04, LOG-01..03)

**Wave 3** *(blocked on Wave 2)*

- [x] 08-03-PLAN.md — iol: mirror ámbito + OAuth refresh_token URL/JSON RedactingFilter patterns + 401 re-auth-once flow in shell _request() per RESEARCH §Pattern 3; CR-01 conditional refresh_token rotation preserved (RELY-01..04, LOG-01..03)

**Wave 4** *(blocked on Wave 3)*

- [x] 08-04-PLAN.md — higyrus: mirror iol + RequestSpec.account_id propagation (D-11) + RedactingFilter JSON password + JSON token + cuit query (PII); URL-encoding quirk preserved (RELY-01..04, LOG-01..03)

**Wave 5** *(blocked on Wave 4)*

- [x] 08-05-PLAN.md — matriz ATOMIC sync-only: _transport.py ONLY (NO _atransport.py per D-25 — Phase 10 territory); _logging.py with D-22 auth_basic redaction; shell _request() with Risk API branch (no re-auth per D-23) + token path 401 re-auth-once; mutating builders (new_order, cancel_order, replace_order) KEEP idempotent=False (Pitfall 4 / D-24 — duplicate-order prevention); aio.py UNCHANGED (Phase 6 stub 103 LOC); CR-03 + CR-05 preserved (RELY-01..04, LOG-01..03)

**Wave 6** *(blocked on Waves 2-5)*

- [x] 08-06-PLAN.md — Green gate consolidation: full pytest matrix Python 3.12 + 3.13 + ruff + ruff LOG ruleset + ruff format + mypy strict + lint-imports + CI grep lint-logging + 6 cross-cutting guard tests GREEN + matriz sweep snapshot (CR-05) + parse_envelope_consumes_body (CR-03) + Phase 6 public surface snapshot (zero diff except 2 new kwargs per signature) + matriz aio.py == 103 LOC + matriz _atransport.py absent + tenacity 9.1.4 verified + Pitfall 18 statement + operator checkpoint (RELY-01..04, LOG-01..03)

**Cross-cutting constraints:**

- D-21: Per-package serial idiom (ámbito → iol → higyrus → matriz) — Phase 6/7 baseline lesson; matriz LAST due to max surface + Risk API + status=ERROR specials
- D-21: 1 commit atómico por paquete (Plans 2-5 each); Plan 1 single commit; Plan 6 validation file only
- D-25: matriz aio.py NOT touched in Phase 8 (Phase 10 REFAC-04 territory); matriz _atransport.py NOT created
- D-26: 6 cross-cutting guard tests in verification/ tests-first (RED in HEAD; turn GREEN as Plans 2-5 land)
- D-28: Snapshot updates per-plan atomic (each per-package plan updates its own snapshot)
- security_enforcement=true: each plan has STRIDE threat_model block; T-8-01..T-8-06 cross-package threats addressed

### Phase 9: Deferred Bug Fixes

**Goal**: Saldar los 4 hallazgos diferidos de v1.0 aprovechando que cada fix vive en `_core.py` (single-site, cubre sync+async).
**Depends on**: Phase 7 (necesita `_core.py`); recomendable después de Phase 8 para integrar logging de los fixes
**Requirements**: BUG-01, BUG-02, BUG-03, BUG-04
**Success Criteria** (what must be TRUE):

  1. BUG-01 (F-09 matriz ERROR-MAP) fixeado en `_core.raise_for_response()` de matriz; regression test mockeado verifica el mapping correcto; el FAIL de `verify_cycle_closure` para matriz cierra cuando se re-corre el cycle.
  2. BUG-02 (F-02 higyrus `get_listado_cuentas=0`) investigado y resuelto en `_core.py` de higyrus (single-site, cubre sync+async); regression test mockeado bloquea el bug; re-verificación live documenta si era FINDING o FIXED según root cause.
  3. BUG-03 (IOL refresh_token persistence in-instance) implementado vía `_ClientState.refresh_token` por instancia; regression tests cubren refresh→success path y refresh→password fallback en el lifecycle de una sola instancia `Client`.
  4. BUG-04 (HIGY multi-account iteration) habilitado vía `Client(account_id=X)` por cuenta O `client.get_X(account_id=Y)` per-call (operator decision en planning); regression test live con ≥2 cuentas verifica iteración correcta.
  5. Todos los tests anteriores (277+ baseline + nuevos regressions) siguen verde; ruff + mypy strict + pytest CI green para Python 3.12 y 3.13.

**Plans**: 4 plans

**Wave 1** *(parallel-safe — paquetes independientes)*

- [ ] 09-01-PLAN.md — iol BUG-03 refresh_token lifecycle regression tests (sync + async, 8 tests) (BUG-03)
- [ ] 09-02-PLAN.md — higyrus BUG-02 quick triage + BUG-04 multi-account per-call regression + cross-pkg `_state.account_id` cleanup (higyrus + iol) (BUG-02, BUG-04)

**Wave 2** *(blocked on Wave 1)*

- [ ] 09-03-PLAN.md — matriz BUG-01 hybrid Literal+regex CFI guard + cycle_closure FAIL→PASS (BUG-01)

**Wave 3** *(blocked on Wave 2)*

- [ ] 09-04-PLAN.md — Green gate consolidation: full pytest matrix + ruff + mypy strict + lint-imports + cross-leak sentinel + snapshot zero-diff + operator checkpoint (BUG-01..04)

**Cross-cutting constraints:**

- D-11: 4 planes en 3 waves (Wave 1 paralelo, Wave 2 matriz LAST per-package serial idiom, Wave 3 green gate)
- D-12: 1 commit atómico por plan (no per-bug — Plan 09-02 cubre 2 bugs + cross-pkg cleanup atomic)
- D-13: Live re-verification bug-driven (Plan 09-02 main_higyrus.py live, Plan 09-03 main_matriz.py live; full 4-pkg live es Phase 11 LIVE-01)
- security_enforcement=true: each plan has STRIDE threat_model block; T-9-XX threats addressed per plan

### Phase 10: matriz `aio.py` Creation + TokenStore

**Goal**: Crear la superficie async REST de matriz-client espejando `client.py` y resolver el 3-way token sharing (sync REST + async REST + ws_client daemon thread).
**Depends on**: Phase 7 (necesita `_core.py` de matriz) + Phase 8 (necesita infra retries/logging para no copy-paste tech debt)
**Requirements**: REFAC-04, LIVE-02
**Success Criteria** (what must be TRUE):

  1. `packages/matriz-client/src/matriz_client/aio.py` existe con `AsyncClient` mirroring full REST surface de `client.py` (mismas signatures); usa `_core.py` para builders/parsers (no duplica `_unwrap`/`_raise_for_response`/auth-flow); estado `_state` async independiente del sync.
  2. `TokenStore` (en `_state.py` o `_token_store.py`) con `threading.Lock` accesible desde sync `Client`, async `AsyncClient` (vía `asyncio.to_thread` o equivalente) y desde `ws_client.py` daemon thread; regression test verifica que un thread holding the refresh-lock for 100ms hace que un async `_ensure_token()` await wait y retorne el mismo token refrescado (no stale).
  3. `main_matriz.py --async` (o `verify_async()` en mismo script) ejercita los mismos probes de la superficie sync contra la API live; live re-verification reporta paridad sync↔async (mismo set de PASS/FINDING/SKIPPED).
  4. `ws_client.py` migrado a leer del `TokenStore` (vía `_default().state.token_store` o equivalente); el shim PEP 562 sigue funcionando como red de seguridad para callers que aún lean `_rest._token`.
  5. CI green: 277+ baseline tests + nuevos async tests matriz (≥30 según estimación research) pasan en Python 3.12 y 3.13; pytest-asyncio fixtures siguen el patrón de iol-client conftest.

**Plans**: TBD
**Research flag**: yes — TokenStore threading design spike requerido antes del planning de la phase (el 3-way concurrent token store es el único architectural unknown de v1.1).

### Phase 11: Harness Hardening + Code Review Close-out + Live Re-verification

**Goal**: Cerrar los hallazgos del code review final de Phase 5 v1.0, hacer el harness `verification/findings.py` append-only idempotente, y correr live re-verification × 4 paquetes como gate final del milestone.
**Depends on**: Phase 10 (necesita matriz aio.py para live re-verification de LIVE-02; harness changes pueden empezar en paralelo)
**Requirements**: HARN-07, HARN-08, HARN-09, HARN-10, CR-01, CR-02, CR-04, CR-06, CR-07, CR-08, LIVE-01
**Success Criteria** (what must be TRUE):

  1. `verification/findings.py` append-only con BEGIN/END zone parser; lee archivo existente + merge + write atómico; unit test verifica que contenido fuera de la zona (operator content arriba/abajo) sobrevive a re-runs; los campos `Classification:`/`Rationale:`/`Regression:`/`Resolution:` añadidos por operador sobreviven verbatim a N re-runs (regression test re-run N veces vs estado inicial).
  2. Content-addressed dedupe by finding ID funciona end-to-end en los 4 drivers (`main_iol.py`, `main_higyrus.py`, `main_matriz.py`, `main_ambito_financiero.py`); D-MATZ-27 cerrado: re-run del driver produce git-clean diff (idempotent). HARN-10: `main_matriz.py` dedupe de `D-MATZ-27 EXPECTED` terminal funciona en 1 run, no requiere N re-runs.
  3. Code review concerns cerrados con regression tests donde aplique: CR-01 (`main_matriz.py` snapshot path vs sample_params alignment), CR-02 (`probe_login_sync` unifica a `FINDING`), CR-04 (`_first_dict` distingue no_data/wrong_type/ok), CR-06 (bare `except Exception` narrowed con stack trace logging en outer catch-all), CR-07 (`_capture_*_query_string` usa lock O per-request hook injection, no muta `event_hooks` shared), CR-08 (line lengths ≤100 cols en `main_higyrus.py:767`).
  4. LIVE-01: `main_*.py --live` × 4 paquetes (iol, higyrus, ambito, matriz) pasa sin regresiones contra baseline `verification-cycle-2026-Q2`; `verify_cycle_closure × 4 pkgs` reporta PASS para los 3 limpios + estado actualizado para matriz post-BUG-01 (F-09 fixed).
  5. CI green final: ruff + mypy strict + pytest para Python 3.12/3.13; los 277 tests baseline + todos los regressions sumados durante v1.1 (Phase 6 fixture-reaches-production + Phase 7 dedup sentinels + Phase 8 retry/logging + Phase 9 bug regressions + Phase 10 matriz async) pasan verde.

**Plans**: TBD

## Progress

| Phase                                                              | Milestone | Plans Complete | Status      | Completed  |
| ------------------------------------------------------------------ | --------- | -------------- | ----------- | ---------- |
| 1. Safety Harness & Verification Infrastructure                    | v1.0      | 4/4            | Complete    | 2026-05-28 |
| 2. Ámbito Verification                                             | v1.0      | 3/3            | Complete    | 2026-06-05 |
| 3. IOL Verification                                                | v1.0      | 3/3            | Complete    | 2026-06-06 |
| 4. Higyrus Verification                                            | v1.0      | 4/4            | Complete    | 2026-06-08 |
| 5. Matriz Verification                                             | v1.0      | 4/4            | Complete    | 2026-06-10 |
| 6. Compat Safety Net + Client Class Skeleton                       | v1.1      | 7/7 | Complete   | 2026-06-11 |
| 7. `_core.py` Extraction — Sync/Async Logic Dedup                  | v1.1      | 6/6 | Complete    | 2026-06-12 |
| 8. Retries, Backoff, Structured Logging                            | v1.1      | 6/6 | Complete    | 2026-06-13 |
| 9. Deferred Bug Fixes                                              | v1.1      | 0/4            | Planning    | -          |
| 10. matriz `aio.py` Creation + TokenStore                          | v1.1      | 0/?            | Not started | -          |
| 11. Harness Hardening + Code Review + Live Re-verification         | v1.1      | 0/?            | Not started | -          |

## Backlog

*(Candidate items for next milestone; see `.planning/todos/pending/` + v1.0-MILESTONE-AUDIT.md deferred section)*

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
