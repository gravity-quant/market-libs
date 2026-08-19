# Roadmap: market-libs — Verificación en vivo de clientes

## Milestones

- ✅ **v1.0 Verification cycle** — Phases 1-5 (shipped 2026-06-10) — see [`milestones/v1.0-ROADMAP.md`](./milestones/v1.0-ROADMAP.md)
- ✅ **v1.1 Tech Debt Cleanup** — Phases 6-11 (shipped 2026-06-14) — see [`milestones/v1.1-ROADMAP.md`](./milestones/v1.1-ROADMAP.md)
- ✅ **v1.2 Architecture + Auth/Ergonomics Carry-forwards** — Phases 12-17 (shipped 2026-06-25) — see [`milestones/v1.2-ROADMAP.md`](./milestones/v1.2-ROADMAP.md)
- ✅ **v1.3 Codegen Single-Source (libcst)** — Phases 18-19 (closed 2026-07-03 on signed SPIKE-006 NO-GO; Phase 19 REFAC-06 dropped) — see [`milestones/v1.3-ROADMAP.md`](./milestones/v1.3-ROADMAP.md)
- ✅ **v1.4 market-data-client** — Phases 20-24 (shipped 2026-07-31) — nuevo paquete cliente (solo lectura) contra la API primary-extractor con Auth0 client-credentials, verificado en vivo y publicado v0.1.0 — see [`milestones/v1.4-ROADMAP.md`](./milestones/v1.4-ROADMAP.md)
- ✅ **v1.5 market-data-client · mutaciones** — Phases 25-28 (shipped 2026-08-17) — superficie de **escritura** (symbols + calendar) detrás de mutating-gate default-refuse, verificada en vivo (create→verify→revert) y publicada `market-data-client-v0.4.0` — see [`milestones/v1.5-ROADMAP.md`](./milestones/v1.5-ROADMAP.md)

## Phases

### 🚧 v1.6 Tipado homogéneo de la superficie pública (Phases 29-34) — IN PROGRESS

**Milestone Goal:** Que las seis librerías expongan un **contrato de tipos idéntico y verificable por máquina** — cero `Any`/`dict[str, Any]` en la superficie pública de datos, una única decodificación de política **observable** (nunca silenciosa), parámetros de dominio como `Literal` cerrados con evidencia, y gates de CI que sostengan la homogeneidad sin código compartido entre paquetes.

> **Nota de sizing (leer antes de planificar).**
> **Phase 29 es load-bearing y está ~3× sub-dimensionada respecto del "copiar un decoder" naive**: 14 de los 25 pitfalls identificados por el research aterrizan ahí, y varios D-locks de los que dependen las fases 30-34 (semánticas divergentes de matriz, política de `Literal` en campos de RESPONSE, contrato de agregación anti-log-spam, fix del `RedactingFilter`, test de intactness 6-way, decisión msgspec-vs-stdlib) deben ser **artefactos explícitos de la Phase 29**, no supuestos implícitos.
> **El scope de la Phase 33 es provisional** hasta que corra la **corrida exploratoria de sizing** del final de la Phase 29 (walker por-campo sobre `verification/snapshots/`, nunca un pase strict de msgspec, que sub-cuenta por construcción). El número que salga es un **piso** ("≥ N"), no una estimación.

- [ ] **Phase 29: Decoder observable** *(load-bearing, PRIMERO)* — decoder único de política observable copiado verbatim 6×, divergencias emitidas estructuradas por el logger del paquete, modo estricto por `ContextVar`, decisión msgspec-vs-stdlib como artefacto, reconciliación de matriz y corrida de sizing — DEC-01
- [ ] **Phase 30: `iol-client` tipado** — `models.py` nuevo + 16 firmas migradas + parsers de `_core.py` + `main_iol.py` a acceso por atributo; `mercado`/`plazo` quedan `str` (promoción a `Literal` diferida a F33) — TYP-01
- [ ] **Phase 31: Endpoints de ops + estructura uniforme** — modelos para los 5 endpoints de ops (higyrus + market-data), request byte-idéntico probado para las 2 mutaciones ya publicadas, `models.py`/`types.py` presentes en los 6 paquetes — TYP-02, TYP-03
- [ ] **Phase 32: Gates de homogeneidad + D-16** — gate AST de superficie como **job de CI nuevo** + test de paridad sync/async no-vacuo + cierre de D-16 reconciliando las **4** listas de enrollment — GATE-TYP-01
- [ ] **Phase 33: Verificación en vivo en modo estricto + fixes** — drivers en modo estricto contra APIs reales, `Literal` cerrados con evidencia, divergencias corregidas in-cycle, cycle closure PASS por paquete — LIVE-TYP-01
- [ ] **Phase 34: Releases por paquete** — bumps sólo de los paquetes cuya superficie cambió, iol 0.2.0 → **0.3.0** source-breaking con callout, `uv.lock` refrescado una sola vez, ops irreversibles detrás de doble gate humano — PUB-TYP-01

## Phase Details (v1.6)

### Phase 29: Decoder observable

**Goal**: Ninguna sustitución de campo vuelve a ser silenciosa — todo consumidor de las 6 libs recibe cada divergencia entre el modelo y el wire como un registro estructurado del logger del paquete, y los drivers pueden pedir modo estricto sin cambiar el comportamiento tolerante del runtime.
**Depends on**: Nothing (primera fase de v1.6; parte del head de v1.5)
**Requirements**: DEC-01
**Success Criteria** (what must be TRUE):

  1. Un payload con campo faltante, tipo equivocado, campo extra, no-dict o `None`/204 decodifica **sin levantar** en modo observable y emite **exactamente un registro estructurado por campo divergente** por `logging.getLogger("<pkg>")`; el registro es **plano, all-str, top-level, type-not-value** y jamás contiene el valor del wire, y un sentinel `caplog` por paquete (6, precedente SEC-01) prueba que no filtra credenciales — el fix del `RedactingFilter` que lo habilita viaja a las 6 copias de `_logging.py`.
  2. En **modo estricto** la misma divergencia levanta con la ruta exacta del campo; el modo viaja por un `ContextVar` bindeado desde `_ClientState` al tope de `_request` (nunca env var, nunca global de módulo), y un test de concurrencia prueba que sobrevive tareas async interleaved y el daemon thread de `ws_client` de matriz sin clobbering.
  3. Las suites de los 3 paquetes con `SafeModel` siguen verdes **sin editar un solo test** — `from_api(payload)` conserva firma y contrato público (DT-05) — y **matriz conserva sus semánticas propias** (missing → `None`, sin `slots`, `empty()`, escalares pass-through), reconciliadas mediante una **tabla 3-way escrita como artefacto de fase antes de escribir código de decoder** y una política parametrizada por paquete; nunca "harmonizadas" en silencio.
  4. Quedan firmados como artefactos de la fase, con evidencia de ambos lados, los dos D-locks que gatean las fases siguientes: **(a)** msgspec dos-motores (fast-path + walker) vs stdlib-only un-motor — el walker es load-bearing en cualquier caso; **(b)** los campos de **RESPONSE nunca** se cierran como `Literal` en este milestone (se decodifican como `str` y el valor fuera de set se reporta como divergencia), lo cual alcanza retroactivamente a los `CFICode`/`MarketId`/`OrderType`/`Currency` pre-existentes de matriz.
  5. El helper de decode existe **copiado verbatim en los 6 paquetes** con un test de intactness 6-way por hash + ban-list grep (`strict=False`, `msgspec.field()`), y una **corrida exploratoria de sizing con el walker por-campo** sobre `verification/snapshots/` publica un **piso por paquete** (`≥ N` divergencias, nunca `N`) que se convierte en el presupuesto declarado de la Phase 33.

**Plans:** 5/10 plans executed

Plans:
**Wave 1**

- [x] 29-01-PLAN.md — Artefactos de política: tabla 6-way de semánticas (D-07), contrato de agregación (resuelve strict-on-extra y la clave de dedupe), D-lock `Literal` en RESPONSE (D-09) + firma

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 29-02-PLAN.md — TRACER: walker canónico `_decode.py` + delegación de `models.py` de higyrus + merge gate zero-edit (872 tests)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 29-03-PLAN.md — TRACER cont.: portador `strict_decode` (state + 4 entry points + bind en ambos `_request`) + fix del `RedactingFilter` + sentinel caplog
- [x] 29-04-PLAN.md — Spike de timing de 3 brazos + `29-DLOCK-MSGSPEC.md` firmado

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 29-05-PLAN.md — Fan-out market-data: copia verbatim + delegación preservando `received_at` y el mirror de `Symbol` + test de concurrencia async
- [ ] 29-06-PLAN.md — Fan-out matriz: copia verbatim con política propia + delegación preservando las 7 diferencias + `Literal` pass-through
- [ ] 29-07-PLAN.md — Fan-out iol + ambito: copias verbatim en los 2 paquetes sin `models.py` + portador + fix del filter

**Wave 5** *(blocked on Wave 4 completion)*

- [ ] 29-08-PLAN.md — Propagación explícita del modo al daemon thread de `ws_client` (D-04) + `test_ws_decode_mode.py`
- [ ] 29-09-PLAN.md — `tools/check_decode_intactness.py` (normalize-then-hash + ban-list) + job `lint` de CI + exención documentada de wallets
- [ ] 29-10-PLAN.md — Corrida de sizing sobre `.planning/verification/schemas/` (43 archivos) → `29-SIZING.md` con piso `≥ N` + ratificación

### Phase 30: `iol-client` tipado

**Goal**: El consumidor de `iol-client` accede a cotizaciones, series históricas e instrumentos por **atributo tipado** — un typo lo caza mypy en el editor, no el servidor en producción.
**Depends on**: Phase 29 (necesita el decoder; es la primera superficie que lo ejercita end-to-end)
**Requirements**: TYP-01
**Success Criteria** (what must be TRUE):

  1. `iol-client` tiene `models.py` nuevo con los modelos de cotización, serie histórica e instrumentos derivados de los **schemas ya capturados en vivo** (`.planning/verification/schemas/iol-client/*.json`), con el `puntas` polimórfico resuelto explícitamente y campos wire en camelCase verbatim.
  2. Las **16 firmas** (4 funciones × método/shim × sync/async) devuelven modelos o `list[modelo]` — cero `Any`/`dict[str, Any]` — despachando por parsers de `_core.py`; `mypy --strict` limpio sobre el paquete y `ruff`/`ruff-format` verdes.
  3. `main_iol.py` lee resultados por **acceso por atributo** en sus 2 sitios reales de consumo (no 6 — corrección del research), y una fixture RED prueba que un typo de atributo **falla** el typecheck.
  4. `mercado` y `plazo` se envían en `str` en esta fase, con carry-forward documentado: la promoción a `Literal` se decide en la Phase 33 con censo vivo (DT-07). Ningún campo de RESPONSE gana `Literal`.
  5. Cada modelo nuevo expone `to_dict()` como escape hatch de migración **en el mismo release** que la ruptura dict→modelo, y el README de iol registra la ruptura (incluido el flip de truthiness) alimentando el bump 0.2.0 → 0.3.0 de DT-08.

**Plans**: TBD

### Phase 31: Endpoints de ops + estructura uniforme

**Goal**: Los 5 endpoints de ops que todavía devuelven `dict[str, Any]` devuelven modelos tipados, y los 6 paquetes presentan la misma estructura de archivos para que el próximo endpoint nazca con lugar donde vivir.
**Depends on**: Phase 29 (paraleliza con Phase 30 — ambas dependen sólo del decoder)
**Requirements**: TYP-02, TYP-03
**Success Criteria** (what must be TRUE):

  1. `higyrus.get_health` y `market-data.get_health` / `get_health_feed` / `add_holidays` / `delete_holiday` devuelven **modelos tipados** en sync y async — cero `dict[str, Any]` en esas firmas ni en sus shims.
  2. Para `add_holidays` y `delete_holiday` (mutaciones **ya publicadas en v0.4.0**) un test prueba que el **request emitido es byte-idéntico** al de v0.4.0 — método, URL, query string, headers y body — porque el cambio es estrictamente response-only.
  3. El mutating-gate queda intacto: `_ensure_mutation_allowed()` sigue siendo el **primer statement literal** de los 8 métodos de mutación (guard AST existente verde) y ningún builder cambia su flag `idempotent=`.
  4. Los **6 paquetes** tienen `models.py` + `types.py` presentes (mínimos, con docstring, en ámbito y wallets), verificable por un check de existencia que corre en CI.

**Plans**: TBD

### Phase 32: Gates de homogeneidad + D-16

**Goal**: CI falla si la homogeneidad se degrada — sin código compartido entre paquetes, los gates son lo único que impide que las seis superficies diverjan en tres releases.
**Depends on**: Phases 30 y 31 (la mitad D-16 es independiente y puede adelantarse a la Phase 29)
**Requirements**: GATE-TYP-01
**Success Criteria** (what must be TRUE):

  1. Un script **stdlib-ast-only** (`tools/check_surface_types.py`) recorre `__all__` de los 6 paquetes y **falla** ante cualquier `Any`/`dict[str, Any]` anotado como retorno de función exportada, con las exenciones DT-06 explícitas (dunders, helpers `_` incluido `_matriz_legacy_request`, `_request` que devuelve `httpx.Response`, `to_dict()` serialize-out); corre en un **job de CI real** — `verification/` nunca corrió en CI porque `ci.yml` pasa un path per-package que pisa `testpaths`.
  2. El gate de superficie es **no-vacuo**: una fixture RED con una regresión introducida a propósito lo hace fallar, y el test lo prueba.
  3. El test de **paridad sync/async por introspección** (sustituto afirmativo de REFAC-06, DT-04) corre **in-package** sobre la matrix existente 6×2, compara nombres públicos y `get_type_hints()` entre `client.py` y `aio.py`, y es **no-vacuo con lower bounds** (N nombres mínimos por paquete + fixture RED): los `aio.py` sin `__all__` no pueden saltearse en silencio (precedente Phase 15 WR-01/WR-02).
  4. **D-16 cerrado** reconciliando las **4** listas de enrollment en un commit atómico — mypy `files`, import-linter `root_packages`, el loop mypy-tests de `ci.yml:85` y `verification/test_public_surface._PACKAGES` — con el contrato import-linter de `market_data_client._core` **RED-probado**, la inclusión (o exclusión) de `wallets_client` decidida explícitamente, y la exclusión **deliberada** de market-data en `_PACKAGES` (ya tiene su test in-package desde Phase 25) documentada como intencional, no "arreglada".
  5. La matriz completa de CI (6 paquetes × py3.12 + py3.13) queda verde con los gates nuevos activos.

**Plans**: TBD

### Phase 33: Verificación en vivo en modo estricto + fixes

**Goal**: La nueva decodificación queda verificada contra las APIs reales — este es el momento donde aparecen las divergencias que la tolerancia silenciosa venía ocultando, y todas se documentan y corrigen en el mismo ciclo.
**Depends on**: Phases 30, 31 y 32
**Requirements**: LIVE-TYP-01
**Success Criteria** (what must be TRUE):

  1. Los 4 drivers verificables + `main_market_data.py` corren en **modo estricto** contra sus APIs reales (ámbito, iol, higyrus, matriz; market-data contra develop con las creds Auth0 del operator) y cada divergencia entra al pipeline de findings existente vía un handler de logging (`verification/divergences.py`), con endpoint + FQN del modelo + superficie (sync|async).
  2. Cada divergencia confirmada se corrige **in-cycle**, espejada sync/async, con un test de regresión mockeado por fix (convención v1.0-v1.5).
  3. Los `Literal` se cierran **con evidencia real**: los de entrada de iol (`mercado`/`plazo`) se promueven o se documentan como `str` permanente, y los de RESPONSE pre-existentes de matriz (`CFICode`/`MarketId`/`OrderType`/`Currency`) se resuelven según el D-lock de la Phase 29 con el censo vivo.
  4. `verify_cycle_closure` PASS por paquete y los schema snapshots quedan reconciliados contra el baseline.
  5. El volumen real de divergencias se **contrasta contra el piso de sizing de la Phase 29**; si lo excede, el re-scope es explícito (findings diferidos documentados con su fase destino, nunca silenciados).

**Plans**: TBD

### Phase 34: Releases por paquete

**Goal**: Los paquetes cuya superficie pública cambió quedan publicados por el pipeline de tags, con la ruptura dict→modelo declarada en el changelog y toda operación irreversible detrás de un gate humano.
**Depends on**: Phase 33
**Requirements**: PUB-TYP-01
**Success Criteria** (what must be TRUE):

  1. **Sólo** los paquetes cuya superficie pública cambió se bumpean y publican; `iol-client` 0.2.0 → **0.3.0** con el callout source-breaking (dict→modelo, incluido el flip de truthiness) **primero** en el changelog (DT-08); los paquetes sin cambios NO se re-publican.
  2. `uv.lock` global se refresca **exactamente una vez** para todos los bumps; el set final de paquetes depende de la decisión msgspec de la Phase 29, y si msgspec entró como dependencia de runtime el README declara que los wheels dejan de ser un closure puro-Python.
  3. PR → CI verde (6 paquetes × py3.12 + py3.13) → merge con **merge commit real** (nunca squash — orfanaría los SHAs que los SUMMARY cross-referencian, D-11) → tag por paquete → `release.yml` **sin editar** → GitHub Release con wheel + sdist por paquete.
  4. Cada operación irreversible (merge y push de tag) queda detrás de un checkpoint humano **independiente**; los dos gates **nunca** se colapsan (precedente D-18 de v1.5).

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
| 26. Calendar write                                          | v1.5      | 4/4 | Complete    | 2026-08-01 |
| 27. Safe live verification + fixes                          | v1.5      | 7/7 | Complete   | 2026-08-01 |
| 28. Release prep + publish v0.3.0                           | v1.5      | 3/3 | Complete    | 2026-08-12 |
| 29. Decoder observable                                      | v1.6      | 5/10 | In Progress|  |
| 30. `iol-client` tipado                                     | v1.6      | 0/? | Not started | -          |
| 31. Endpoints de ops + estructura uniforme                  | v1.6      | 0/? | Not started | -          |
| 32. Gates de homogeneidad + D-16                            | v1.6      | 0/? | Not started | -          |
| 33. Verificación en vivo en modo estricto + fixes           | v1.6      | 0/? | Not started | -          |
| 34. Releases por paquete                                    | v1.6      | 0/? | Not started | -          |

## Backlog

*(Candidate items for next milestone; see `.planning/todos/pending/` + v1.0/v1.1/v1.2/v1.3 milestone audits deferred sections)*

### Deferred to v1.6+ (from v1.5)

- **D-16 — enrolar `market-data-client` en el typecheck global** — el paquete sigue ausente de tres listas: el `files` de mypy del root (`pyproject.toml:97`, hoy 5 paquetes), el `root_packages` de import-linter (`pyproject.toml:141-146`, hoy 4) y el loop mypy-tests per-package de `ci.yml:85` (hoy 5). Enrolarlo requiere además **escribir un contrato de import-linter** para `market_data_client._core` (los otros 4 paquetes ya tienen el suyo). Es un gap de **COBERTURA de typecheck, no un CI failure**: todos los checks package-scoped están verdes hoy, y la cobertura real de mypy sobre este paquete la da el hook de pre-commit scoped `files: ^packages/.*/src/` (`.pre-commit-config.yaml:32`). Diferido desde Phase 24 y re-confirmado en Phase 28 (**rechazado** enrolarlo en el PR de release: expandiría el diff). Se archiva acá explícitamente para que deje de rodar en silencio release tras release.

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
