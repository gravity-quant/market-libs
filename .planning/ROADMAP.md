# Roadmap: market-libs — Verificación en vivo de clientes

## Milestones

- ✅ **v1.0 Verification cycle** — Phases 1-5 (shipped 2026-06-10) — see [`milestones/v1.0-ROADMAP.md`](./milestones/v1.0-ROADMAP.md)
- ✅ **v1.1 Tech Debt Cleanup** — Phases 6-11 (shipped 2026-06-14) — see [`milestones/v1.1-ROADMAP.md`](./milestones/v1.1-ROADMAP.md)
- ✅ **v1.2 Architecture + Auth/Ergonomics Carry-forwards** — Phases 12-17 (shipped 2026-06-25) — see [`milestones/v1.2-ROADMAP.md`](./milestones/v1.2-ROADMAP.md)
- ✅ **v1.3 Codegen Single-Source (libcst)** — Phases 18-19 (closed 2026-07-03 on signed SPIKE-006 NO-GO; Phase 19 REFAC-06 dropped) — see [`milestones/v1.3-ROADMAP.md`](./milestones/v1.3-ROADMAP.md)
- ✅ **v1.4 market-data-client** — Phases 20-24 (shipped 2026-07-31) — nuevo paquete cliente (solo lectura) contra la API primary-extractor con Auth0 client-credentials, verificado en vivo y publicado v0.1.0 — see [`milestones/v1.4-ROADMAP.md`](./milestones/v1.4-ROADMAP.md)
- ✅ **v1.5 market-data-client · mutaciones** — Phases 25-28 (shipped 2026-08-17) — superficie de **escritura** (symbols + calendar) detrás de mutating-gate default-refuse, verificada en vivo (create→verify→revert) y publicada `market-data-client-v0.4.0` — see [`milestones/v1.5-ROADMAP.md`](./milestones/v1.5-ROADMAP.md)
- ✅ **v1.6 Tipado homogéneo de la superficie pública** — Phases 29-34 (shipped 2026-08-27) — contrato de tipos idéntico y verificable por máquina en los 6 paquetes: decodificación por-campo observable, `iol-client` y los endpoints de ops tipados, gates de CI que sostienen la homogeneidad, verificación en vivo en modo estricto, y publicación de `iol-client-v0.3.0` + `market-data-client-v0.5.0` — see [`milestones/v1.6-ROADMAP.md`](./milestones/v1.6-ROADMAP.md)
- ✅ **v1.7 API tipada con Null Objects** — Phases 35-40 (shipped 2026-08-30) — patrón Null Object en los 6 paquetes: ningún eslabón de cadena puede ser `None`, `dict[str, Any]` desaparece de los campos de modelos públicos, y 4 paquetes publicados con bump breaking + tabla de migración — see [`milestones/v1.7-ROADMAP.md`](./milestones/v1.7-ROADMAP.md)

## Phases

<details>
<summary>✅ v1.7 API tipada con Null Objects (Phases 35-40) — SHIPPED 2026-08-30</summary>

- [x] Phase 35: Fundación Null Object — `__bool__` + política del walker (5/5 plans) — completed 2026-08-29
- [x] Phase 36: `market-data-client` — `market_data` tipado (3/3 plans) — completed 2026-08-29
- [x] Phase 37: `matriz-client` — dicts residuales + alias (5/5 plans) — completed 2026-08-29
- [x] Phase 38: `iol-client` + auditoría higyrus/ámbito/wallets (4/4 plans) — completed 2026-08-29
- [x] Phase 39: Verificación en vivo del encadenamiento profundo (8/8 plans) — completed 2026-08-30
- [x] Phase 40: Releases breaking coordinados (3/3 plans) — completed 2026-08-30

Full detail: [`milestones/v1.7-ROADMAP.md`](./milestones/v1.7-ROADMAP.md)

</details>

<details>
<summary>✅ v1.6 Tipado homogéneo de la superficie pública (Phases 29-34) — SHIPPED 2026-08-27</summary>

- [x] Phase 29: Decoder observable (10/10 plans) — completed 2026-08-19
- [x] Phase 30: `iol-client` tipado (13/13 plans) — completed 2026-08-23
- [x] Phase 31: Endpoints de ops + estructura uniforme (5/5 plans) — completed 2026-08-25
- [x] Phase 32: Gates de homogeneidad + D-16 (6/6 plans) — completed 2026-08-25
- [x] Phase 33: Verificación en vivo en modo estricto + fixes (7/7 plans) — completed 2026-08-27
- [x] Phase 34: Releases por paquete (3/3 plans) — completed 2026-08-27

Full detail: [`milestones/v1.6-ROADMAP.md`](./milestones/v1.6-ROADMAP.md)

</details>

## Progress

| Phase                                                        | Milestone | Plans | Status      | Completed  |
|--------------------------------------------------------------|-----------|-------|-------------|------------|
| 35. Fundación Null Object — `__bool__` + política del walker | v1.7      | 5/5 | Complete    | 2026-08-29 |
| 36. `market-data-client` — `market_data` tipado              | v1.7      | 3/3 | Complete    | 2026-08-29 |
| 37. `matriz-client` — dicts residuales + alias               | v1.7      | 5/5 | Complete    | 2026-08-29 |
| 38. `iol-client` + auditoría higyrus/ámbito/wallets          | v1.7      | 4/4 | Complete    | 2026-08-29 |
| 39. Verificación en vivo del encadenamiento profundo         | v1.7      | 8/8 | Complete    | 2026-08-30 |
| 40. Releases breaking coordinados                            | v1.7      | 3/3 | Complete    | 2026-08-30 |

*(Fases 1-34: ver las tablas de progreso en `milestones/v1.0-…v1.6-ROADMAP.md`.)*

## Backlog

*(Candidate items for next milestone; see `.planning/todos/pending/` + v1.0/v1.1/v1.2/v1.3 milestone audits deferred sections)*

### Deferred to v1.8+ (from v1.7)

- **NYQUIST-35-39 — correr `/gsd-validate-phase` en las Phases 35-39** — sólo la Phase 40 llegó a `nyquist_compliant: true`; las otras cinco tienen Nyquist configurado activo pero nunca ejecutado (`VALIDATION.md` status `draft`). Gap de cobertura, no de compliance — flagged por el audit de cierre del milestone v1.7 (`v1.7-MILESTONE-AUDIT.md`).
- **RESPONSE-Literal value census de matriz (S-4 + los 7 campos alias)** — ver la entrada `LIVE-MATZ-33` arriba: Phase 39 desbloqueó y midió S-3/S-5 pero no tocó el censo de valores `Literal` de RESPONSE que el plan 33-06 dejó abierto (`marketId`/`cficode`/`currency`/`orderTypes`/`ordType`); `scripts/literal_census_33.py` ya tiene el gate remarkets-only listo para correr contra el sandbox `bbsa` ahora desbloqueado.
- **Cosmético Phase 37** — `IN-01` comentario stale del gate ("330 definitions scanned", medido 336); `IN-05` `matriz_client/__init__.py` sigue sin `__version__` (gap pre-existente); `IN-06` `verification/test_public_surface.py` sigue fuera de la lista explícita del job de lint de CI (pre-existente). Ninguno bloqueante.
- **Deuda documentada in-code de Phase 39 (D39-01..04, WR-02)** — respuestas 204/vacías escapan las jerarquías `IOLClientError`/`MatrizClientError` (decisión de alcance deliberada, aseverada por tests de regresión); `verification/findings.py::append_finding` no es content-addressed cross-run para hallazgos de probe no-terminales (deuda de harness, operator-approved fuera de alcance, junto a `HARN-VERIF-01`); un mock de matriz codificaba una forma de instrumento anidada que el vendor nunca emite; higyrus no captura `httpx.ConnectTimeout` en la rama vendor-unreachable (límite de alcance documentado en el propio código). Ninguno silencioso — todos documentados con destino nombrado.

### Deferred to v1.7+ (from v1.6)

- **HARN-VERIF-01 — reparar las firmas de probe stale de `main_matriz.py` en `verification/`** — paquete: `matriz-client`. Archivos: `verification/test_matriz_sweep_snapshot.py` (17 FAILED + 17 ERROR) y `verification/test_main_matriz_login_fail_uniformity.py` (2 FAILED + 2 ERROR). Causa raíz única: ambos llaman a los probes de `main_matriz.py` sin argumentos (`TypeError: probe_get_segments() missing 1 required positional argument: 'client'`), firma pre-migración REFAC-05 de la Phase 15; cada caso cuenta doble porque el teardown de `pytest_httpx` asevera que la respuesta mockeada fue pedida. Explica el **100%** del rojo de `verification/` (19 failed / 19 errors, medido en `33-BASELINE.md` sobre `0a9fdae`). Incluye el gap gemelo de **43 errores de `uv run mypy verification` en 8 archivos**: `verification/` está fuera del `files` de mypy y del scope `^packages/.*/src/` del hook de pre-commit. Es rot **invisible por construcción** — `verification/` nunca corrió en CI (el job `test` pasa una ruta explícita que anula `testpaths`) — no un CI failure. Excluido por escrito del scope de LIVE-TYP-01 (P-13) y deliberadamente NO absorbido en la Phase 34 (releases), que ya rechazó una vez expandir el diff del PR de release por el mismo motivo (ver D-16). Precaución al repararlo: estos dos archivos son el **canario** del refactor de `probe_context` de los planes 33-02/33-03, porque invocan los probes directamente y no vía `main()`.

- **LIVE-MATZ-33 — censo en vivo de `matriz-client` + disposición de S-3/S-4/S-5 — PARCIALMENTE RESUELTO en v1.7 Phase 39 (2026-08-30).** El gate D-MATZ-33 se amplió de substring-match a un allowlist explícito de hostname que admite `bbsa.matrizoms.com.ar` (checkpoint humano D-02, `39-01-PLAN.md`), desbloqueando la primera corrida en vivo real de matriz desde v1.0. **S-3** y **S-5** quedaron medidos y contabilizados en `39-CENSUS.md` (la resta 14−5−2=7 los incluye); la corrida encontró y corrigió in-cycle el bug real de `byCFICode`/`bySegment` (identificador de instrumento descartado en silencio, ~9160 instrumentos). **Sigue abierto:** el censo de valores `Literal` de RESPONSE (**S-4** y los 7 campos con alias) mencionado más abajo (Ampliación plan 33-06) — Phase 39 no lo tocó. Texto original de la Phase 33 preservado abajo para contexto histórico.

- **LIVE-MATZ-33 (histórico, Phase 33) — censo en vivo de `matriz-client` + disposición de S-3/S-4/S-5** — paquete: `matriz-client`. El pase observable de la Phase 33 (plan 33-05, 2026-08-27) **no pudo correr**: `main_matriz.py` aborta en el assert de hostname **D-MATZ-33** (`:2550`) porque `PRIMARY_BASE_URL` apunta a `api.demo.matrizoms.com.ar`, que no es el sandbox remarkets al que la política de seguridad de la Phase 5 restringe la verificación. Las credenciales **sí** autentican (`preflight_33.py` → `AUTH OK`); el bloqueo es de política, no de auth, y **no se debe rodear** (la superficie de matriz incluye entrada de órdenes; prohibición P-05 de 33-05). Queda sin contrastar el piso `≥24` de `29-SIZING.md` (equivalente en triples distintos: 14) y quedan **COULD-NOT-DECIDE** las tres estructurales del paquete: **S-3** (`Instrument.instrumentId` ausente en byCFICode/bySegment, con `marketId`/`symbol` llegando aplanados y descartados como `extra` — *"the highest-consequence finding in the set"* según `29-SIZING.md`), **S-4** (`InstrumentDetail` no declara 7 claves del wire) y **S-5** (`MarketDataSnapshot.LA/.SE/.OI/.CL` no-`Optional` llegando `null`). **Requisito de ventana horaria:** el pase observable tiene que correr **dentro de una sesión de trading de ARG** o S-5 sigue siendo indecidible — un `null` de mercado cerrado no se distingue de un error de modelado (P-12). Colateral: las **nueve** entradas de `_SCHEMA_FILES` declaradas y ausentes en disco (orders / positions / account-report) sólo toman su rama write-once en una corrida exitosa. Detalle completo en `33-CENSUS.md`. **Ampliación (plan 33-06, 2026-08-27):** el mismo gate bloqueó el **censo de valores de los siete campos RESPONSE con alias `Literal`** — `marketId` (`Segment`, `InstrumentId`), `cficode` (`Instrument`, `InstrumentDetail`), `currency` y `orderTypes` (`InstrumentDetail`) y `ordType` (`Order`). Los cuatro alias (`MarketId`, `CFICode`, `Currency`, `OrderType`) quedan confirmados como **decodificando sin enforcement** (`POLICY` de matriz pasa `literal_enforced=False` y `scalar_passthrough=True`, `_decode.py:136`), pero **qué valores manda el vendor sigue sin medirse**: es la mitad abierta del criterio 3. `scripts/literal_census_33.py` ya lleva el gate remarkets-only y corre el censo completo apenas haya un `PRIMARY_BASE_URL` de remarkets con credenciales emitidas para ese host. Colateral del mismo desbloqueo: corregir el párrafo `29-DLOCK-RESPONSE-LITERAL.md:140-142`, que afirma que el stream de divergencias es el mecanismo de censo — la rama `Literal` de `walk_field` (`_decode.py:521-534`) retorna temprano con `literal_enforced=False` y nunca llama al sink, así que no lo es. El lock está firmado, así que la corrección es del firmante. Detalle en `33-LITERALS.md`.

- **LIVE-HIGY-33 — censo en vivo de `higyrus-client` (piso `≥22` sin contrastar)** — paquete: `higyrus-client`. El pre-flight de la Phase 33 (plan 33-05, 2026-08-27) imprimió `AUTH FAIL ConnectError`. Diagnóstico acotado: las tres variables (`HIGYRUS_BASE_URL`, `HIGYRUS_USER`, `HIGYRUS_PASSWORD`) están presentes y el esquema es `https`, pero el hostname **no resuelve por DNS** (`socket.gaierror`) desde la red de desarrollo — es alcanzabilidad de red (host plausiblemente interno/VPN), no rechazo de credenciales. Por D-13 el paquete se registró como `SKIPPED — vendor inalcanzable`, **nunca como cero**. Quedan sin contrastar los 22 triples `missing` del piso: `Movimiento` (9), `PosicionValuada` (11), `Posicion` (2). Al desbloquearlo, el camino es el de operador-corre-y-pega de la Phase 23. Detalle completo en `33-CENSUS.md`. **Sigue abierto tras v1.7 Phase 39** — el driver reportó `SKIPPED` con la misma causa medida (DNS aún sin resolver).

- **TYP-MD-EXTRA-33 — tipar las 8 claves `extra` en vivo de `market-data-client`** — paquete: `market-data-client`. Ocho triples de especie `extra` medidos en vivo contra `develop` el 2026-08-27 (plan 33-05) que el plan 33-07 **no** corrige: `HealthFeed.symbols_never_delivered` (`int`), `FeedIngestor.ingestor.last_error_age_seconds` (`int`), `.ingestor.last_error_at` (`str`), `.ingestor.subscription` (`dict`), `Symbol.note` (`str`), y las tres del sobre de preview `CalendarConfig.market_after` / `.requires_confirmation` / `.valid`. **Actualización (plan 33-07, 2026-08-27): esas tres YA NO están abiertas** — S-2 se cerró in-cycle dándole al preview su propio modelo (`CalendarConfigPreview` + `PreviewMarket`), que declara las tres, así que este ítem baja de 8 triples a **5**: los cuatro `extra` de `HealthFeed`/`FeedIngestor` más `Symbol.note`. `extra` es **informativo por política** (locks 3 y 4 de la Phase 29: se emite a `INFO` y nunca levanta), así que esto es trabajo de cobertura de superficie, no reparación de defecto. Cuatro de los ocho son **TYP-02**: son visibles porque `Health`/`HealthFeed` se tiparon recién en la Phase 31.

- **SHAPE-MD-REF-33 — corregir la forma declarada de `Instrument` y `Segment` (`market-data-client`)** — paquete: `market-data-client`. Es la **mitad de S-1 que el plan 33-07 deliberadamente NO cerró**, y la razón está registrada: 33-07 arregló el desenvolvimiento del sobre (los parsers iteraban las CLAVES del envelope y devolvían un modelo all-default por clave; findings `F-82`/`F-83`/`F-102`/`F-103`, ya `FIXED`), pero corregir los CAMPOS declarados es un cambio de forma de un modelo **publicado** desde v0.2.0, y el checkpoint bloqueante 33-07 Task 1 existe exactamente para esa clase de cambio. El operator autorizó **tres** cambios de forma (SC-1 preview, SC-2 `MarketDataSnapshot`, SC-3 `Symbol`) y éste **no estaba entre ellos**; aplicarlo igual habría sido el cambio de contrato sin decisión que T-33-44 prohíbe. Lo que queda por corregir, contra los baselines committeados `get-instruments.json` y `get-segments.json`: **`Instrument`** declara `marketId` e `instrumentType`, que el wire no manda, y no declara `market_id`, `currency`, `days_to_maturity`, `maturity`, `outright`, `subscribed` ni `active`, que sí manda (3 de 5 campos declarados —`symbol`, `segment`, `expired`— sí coinciden); **`Segment`** declara `marketSegmentId`, `marketId` y `description`, y el wire manda `segment` y `live_instruments` — **conjuntos disjuntos**, así que hoy toda fila de `get_segments()` sale con sus tres campos vacíos. **Estado post-33-07: la divergencia es VISIBLE, no silenciosa** — antes se escondía detrás de un único `non_dict` terminal por modelo y ahora el walker la reporta campo por campo y levanta bajo `strict_decode`, que es estrictamente mejor pero no es el fix. Requiere disposición de semver: es source-breaking y se suma al bump de la Phase 34 si se hace antes del release, o abre su propio ciclo si se hace después.

- **HARN-DRIFT-33 — deduplicar los findings de `schema drift` por título** — paquete: harness (`main_market_data.py` y los otros cuatro drivers). `_write_or_check_schema` llama a `append_finding` **sin** `idempotent_by_title=True`, así que un mismo drift escribe un bloque `### F-` nuevo por superficie y por pase, con títulos byte-idénticos: la corrida de dos pases del plan 33-05 produjo **22 bloques** de drift para **8 snapshots distintos** (`get_health_feed` ×4, `get_calendar` ×4, `get_calendar_config` ×4, y ×2 los otros cinco). No hay pérdida de censo —nada se descarta— pero infla el archivo de findings y hace que el triage vea duplicados. La rama comparte además el allocator de fids, así que está cubierta por la aserción de consistencia de `verification/test_finding_count_consistency.py`.

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
