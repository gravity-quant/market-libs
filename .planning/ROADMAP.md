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

- [x] **Phase 29: Decoder observable** *(load-bearing, PRIMERO)* — decoder único de política observable copiado verbatim 6×, divergencias emitidas estructuradas por el logger del paquete, modo estricto por `ContextVar`, decisión msgspec-vs-stdlib como artefacto, reconciliación de matriz y corrida de sizing — DEC-01 (completed 2026-08-19)
- [x] **Phase 30: `iol-client` tipado** — `models.py` nuevo + 16 firmas migradas + parsers de `_core.py` + `main_iol.py` a acceso por atributo; `mercado`/`plazo` quedan `str` (promoción a `Literal` diferida a F33) — TYP-01 (completed 2026-08-20)
- [x] **Phase 31: Endpoints de ops + estructura uniforme** — modelos para los 5 endpoints de ops (higyrus + market-data), request byte-idéntico probado para las 2 mutaciones ya publicadas, `models.py`/`types.py` presentes en los 6 paquetes — TYP-02, TYP-03 (completed 2026-08-25)
- [x] **Phase 32: Gates de homogeneidad + D-16** — gate AST de superficie como **job de CI nuevo** + test de paridad sync/async no-vacuo + cierre de D-16 reconciliando las **4** listas de enrollment — GATE-TYP-01 (completed 2026-08-25)
- [x] **Phase 33: Verificación en vivo en modo estricto + fixes** — drivers en modo estricto contra APIs reales, `Literal` cerrados con evidencia, divergencias corregidas in-cycle, cycle closure PASS por paquete — LIVE-TYP-01 (completed 2026-08-27)
- [ ] **Phase 34: Releases por paquete** — bumps sólo de los paquetes cuya superficie cambió, iol 0.2.0 → **0.3.0** y market-data 0.4.0 → **0.5.0**, ambos source-breaking con callout, `uv.lock` refrescado una sola vez, ops irreversibles detrás de doble gate humano — PUB-TYP-01

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

**Plans:** 10/10 plans complete

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
- [x] 29-06-PLAN.md — Fan-out matriz: copia verbatim con política propia + delegación preservando las 7 diferencias + `Literal` pass-through
- [x] 29-07-PLAN.md — Fan-out iol + ambito: copias verbatim en los 2 paquetes sin `models.py` + portador + fix del filter

**Wave 5** *(blocked on Wave 4 completion)*

- [x] 29-08-PLAN.md — Propagación explícita del modo al daemon thread de `ws_client` (D-04) + `test_ws_decode_mode.py`
- [x] 29-09-PLAN.md — `tools/check_decode_intactness.py` (normalize-then-hash + ban-list) + job `lint` de CI + exención documentada de wallets
- [x] 29-10-PLAN.md — Corrida de sizing sobre `.planning/verification/schemas/` (43 archivos) → `29-SIZING.md` con piso `≥ N` + ratificación

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

**Plans:** 13/13 plans complete

Plans:
**Wave 1**

- [x] 30-01-PLAN.md — TRACER: `get_quote` tipado end-to-end — `models.py` con `SafeModel`/`Punta`/`Cotizacion` + parser con scope per-response + 4 firmas + fixture RED de typecheck

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 30-02-PLAN.md — Expansión list-shaped: modelo `Titulo` + helper `_parse_list_or_raise` con guard que levanta + 8 firmas de serie histórica e instrumentos-por-tipo

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 30-03-PLAN.md — Modelo `Instrumento` + corrección de los 16 mocks a la forma del schema vivo + últimas 4 firmas (16/16 migradas)

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 30-04-PLAN.md — Driver a acceso por atributo + frontera `to_dict()` no-vacua hacia el harness + snapshot de superficie regenerado + README con changelog v0.3.0

**Wave 5 — cierre de gaps** *(30-VERIFICATION.md: 8/10, dos truths falsificados; ambos planes son independientes entre sí y corren en paralelo)*

- [x] 30-05-PLAN.md — CR-02: guards de forma en `parse_get_instruments_by_type_response` (envelope dict + valor `titulos` list) levantando `IOLAPIError`, con paridad sync/async probada
- [x] 30-06-PLAN.md — CR-01: los probes de drift leen el **wire crudo** en vez de la proyección del modelo (captura por endpoint + probes 12/13 recableados + lock de regresión offline), más WR-02 y WR-06

**Wave 6 — segundo cierre de CR-01** *(30-VERIFICATION.md re-verificación: 6/7; CR-02 cerrado, CR-01 sustancialmente cerrado pero con un BLOCKER nuevo en el código de reemplazo)*

- [x] 30-07-PLAN.md — CR-01 (post-cierre): un body capturado como JSON `null` deja de ser indistinguible de una captura fallida — los probes 12/13 gatean por membresía en `raw_wire` en vez de por el centinela nulo, más el caso de regresión que el lock de 30-06 no cubría

**Wave 7 — cierre del BLOCKER de fuga** *(30-VERIFICATION.md 2026-08-21: 6/7, truth 6 cerrado; BLOCKER nuevo — `_capture_raw_wire` escribe el body crudo del error upstream en un artefacto git-trackeado)*

- [x] 30-08-PLAN.md — CR-01 (fuga por representación de la excepción): el handler de captura fallida reporta sólo clase de excepción + `status_code`, jamás el mensaje que `_core.raise_for_response` llenó con `resp.text`; primer test directo de `_capture_raw_wire` (marker-leak vía `httpx.MockTransport`), más los dos WARNING de calidad de test (WR-01 tautológico, WR-02 cementando el gap de vacuidad del probe 13)

**Wave 8 — cierre de la CLASE de fuga** *(30-VERIFICATION.md 2026-08-22, tercer ciclo: 6/7; el sitio de 30-08 quedó cerrado, pero la misma clase sigue viva en los otros 29 sitios de `main_iol.py` — descubierto por 30-REVIEW.md CR-01 después de que 30-08 fuera scopeado)*

- [x] 30-09-PLAN.md — CR-01 file-wide: `_redacted_exc` como **único** renderizador de excepciones del driver, aplicado a los 29 `actual` + los 2 `_auth_failure_reason` (WR-02), con `IOLDecodeError` exceptuado por T-29-36 (WR-03) y `status_code` no-entero descartado (WR-06); lock de regresión por AST con control positivo y negativo para que el patrón no pueda volver en un sitio 32

**Wave 9 — los dos BLOCKERs del cuarto ciclo** *(30-VERIFICATION.md 2026-08-23: 6/8; SC1-SC5 re-confirmados intactos y fuera de scope — los dos gaps abiertos son de integridad y de fuga en `main_iol.py`, hallados por 30-REVIEW.md CR-01/CR-02 y re-derivados por el verificador)*

- [x] 30-10-PLAN.md — CR-01 (integridad del harness) + CR-02 (fuga por la ruta de crash): `_seed_fid_counter()` sube el allocator por encima de los fids ya committeados (F-01 OPEN / F-02 FIXED) para que ninguna corrida sobrescriba un finding triageado ni pierda uno en silencio; y un `sys.excepthook` redactado rutea la excepción no capturada por `_redacted_exc` + traceback sin la línea de mensaje, preservando el crash no-cero de D-04

**Wave 10 — durabilidad del lock de regresión** *(30-VERIFICATION.md WARNING / 30-REVIEW.md WR-01 + WR-02: no hay fuga viva hoy, pero el lock no enforcea lo que 30-09-SUMMARY.md afirma que enforcea)*

- [x] 30-11-PLAN.md — WR-01 + WR-02: `_raw_exception_renders` se ensancha a las 11 formas de fuga de la tabla del review (lectura de atributo `.message`/`.args`, delegación fuera de la allow-list sancionada, `%`-format, `.format()`, `exc_info` en handler sin binding, alias de un nivel) y el conteo de renderers se reemplaza por un censo falsificable sobre string de fuente que matchea `AsyncFunctionDef` a cualquier scope — con la aserción de auto-detección que caza el bug del propio snippet del review

**Wave 11 — el BLOCKER del quinto ciclo: la ruta de crash falla ABIERTA** *(30-VERIFICATION.md 2026-08-23, quinto ciclo: 7/8; truth 7 cerrada, truth 8 sigue abierta — el hook que 30-10 construyó para suprimir el body upstream lo emite verbatim en cuanto algo adentro suyo falla, reproducido por subproceso real)*

- [x] 30-12-PLAN.md — Truth 8: el hook de crash falla **cerrado**. `_redacted_excepthook` no tenía manejo de errores propio, así que un fallo interno (renderer que levanta, stderr roto/cerrado, `IOLDecodeError` malformado) caía en el fallback de `PyErr_PrintEx` y CPython renderizaba la excepción ORIGINAL con el excepthook **default**: `[<status>] <resp.text>` completo a stderr. Se guarda la llamada al renderer con un placeholder estático y se guardan los dos sinks por separado, más un lock AST que impide que los guards se saquen en silencio

**Wave 12 — durabilidad del lock, segunda vuelta** *(30-VERIFICATION.md quinto ciclo WARNING: no hay fuga viva hoy, pero el lock ensanchado por 30-11 tiene tres bypasses nuevos, reproducidos llamando a los detectores directo sobre fuentes sintéticos)*

- [x] 30-13-PLAN.md — Los tres bypasses del quinto ciclo: la exención de `getattr` se adjudica sobre el **argumento de nombre de atributo** (marca `getattr(exc, "message", …)`, sigue permitiendo `getattr(exc, "status_code", None)`), `__dict__` entra al set de atributos con fuga, y el predicado del censo gana la regla de `%`-format que su detector hermano ya tenía más una regla genérica de delegación a callee no sancionado

### Phase 31: Endpoints de ops + estructura uniforme

**Goal**: Los 5 endpoints de ops que todavía devuelven `dict[str, Any]` devuelven modelos tipados, y los 6 paquetes presentan la misma estructura de archivos para que el próximo endpoint nazca con lugar donde vivir.
**Depends on**: Phase 29 (paraleliza con Phase 30 — ambas dependen sólo del decoder)
**Requirements**: TYP-02, TYP-03
**Success Criteria** (what must be TRUE):

  1. `higyrus.get_health` y `market-data.get_health` / `get_health_feed` / `add_holidays` / `delete_holiday` devuelven **modelos tipados** en sync y async — cero `dict[str, Any]` en esas firmas ni en sus shims.
  2. Para `add_holidays` y `delete_holiday` (mutaciones **ya publicadas en v0.4.0**) un test prueba que el **request emitido es byte-idéntico** al de v0.4.0 — método, URL, query string, headers y body — porque el cambio es estrictamente response-only.
  3. El mutating-gate queda intacto: `_ensure_mutation_allowed()` sigue siendo el **primer statement literal** de los 8 métodos de mutación (guard AST existente verde) y ningún builder cambia su flag `idempotent=`.
  4. Los **6 paquetes** tienen `models.py` + `types.py` presentes (mínimos, con docstring, en ámbito y wallets), verificable por un check de existencia que corre en CI.

> **Nota de planning (2026-08-23):** el criterio 3 dice "guard AST existente verde", pero **ese guard no
> existe** — ningún check AST del repo apunta a `client.py`/`aio.py` de market-data (D-07). Esta fase lo
> **construye** (plan 31-01), in-package y no-vacuo. Ambos builders de feriados llevan `idempotent=True`
> hoy (D-20, medido en vivo en la Phase 27); el criterio 3 significa que deben **seguir** en `True`.

**Plans**: 5/5 plans complete

Plans:
**Wave 1**

- [x] 31-01-PLAN.md — Red de seguridad primero: guard AST no-vacuo del mutating-gate + aserción directa de `idempotent=True` en ambos builders + pin del request v0.4.0 en bytes crudos (sync + async). Verde contra fuente sin tocar. [wave 1]
- [x] 31-02-PLAN.md — TYP-03: `tools/check_uniform_structure.py` (stdlib-only, roster leído del disco) + step nuevo en el job `lint` + los 7 módulos docstring-only que ponen el gate en verde. RED observado antes del GREEN. [wave 1]
- [x] 31-03-PLAN.md — **Tracer slice**: `higyrus.get_health` → `Health` de punta a punta (modelo, `to_dict()`, parser decorado con su guard intacto, 4 firmas, re-export, golden de superficie regenerado). Único paquete de la fase con mypy en CI. [wave 1]

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 31-04-PLAN.md — market-data health: 6 modelos (3 niveles de nesting), `parse_health_response` dividido en dos parsers decorados y guardados, 8 firmas, exports + roster de superficie, probes del driver capturando wire crudo. **Checkpoint bloqueante** sobre la nulabilidad de 9 campos sub-determinados. [wave 2]

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 31-05-PLAN.md — market-data feriados: `AddHolidaysResult` (reusa `CalendarDay`) + `DeleteHolidayResult`, `parse_calendar_write_response` dividido preservando su tolerancia T-26-13, 8 firmas, docstring stale de `idempotent=` corregido (G-6), ~96 líneas re-mockeadas. El pin y el guard de 31-01 se re-corren tras cada task. [wave 3]

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

**Plans:** 6/6 plans complete

Plans:

**Wave 0**

- [x] 32-01-PLAN.md — Baseline CI verde: reparar los 33 errores de mypy pre-existentes (matriz 29, higyrus 2, ambito 2) en los tests de la Phase 29 que bloquean el criterio 5

**Wave 1** *(blocked on Wave 0 completion)*

- [x] 32-02-PLAN.md — TRACER: gate AST de superficie `tools/check_surface_types.py` con raíz inyectable + fixture RED automatizada + step nuevo en el job `lint` (D-04/D-05, criterios 1-2)
- [x] 32-03-PLAN.md — Gate de reversibilidad: `checkpoint:decision` sobre D-09 (cambio one-way de la superficie pública de `market_data_client.aio.configure`)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 32-04-PLAN.md — Helper de paridad sync/async compartido (métrica única, tabla de 4 reglas, lower bounds por paquete) + piloto market-data que RED-prueba el drift D-09 + su fix (criterio 3)
- [x] 32-05-PLAN.md — Cierre de D-16 en commit atómico (mypy `files` + 2 exclusiones documentadas) + prueba RED automatizada del contrato import-linter de `market_data_client._core` (criterio 4)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 32-06-PLAN.md — Fan-out de paridad a los 5 paquetes restantes (wallets con ausencia aserida, nunca skip) + reproducción local completa de la matriz de CI (criterio 5)

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

**Plans:** 7/7 plans complete

Plans:
**Wave 1**

- [x] 33-01-PLAN.md — TRACER: `verification/divergences.py` (handler + endpoint/surface ContextVars + install CM + probe decorator) wired end-to-end through higyrus `get_health`, hardening tests for the three silent-loss channels, y baseline rojo de `verification/`

**Wave 2** *(blocked on Wave 1 completion; los tres planes son independientes entre sí y corren en paralelo)*

- [x] 33-02-PLAN.md — Los dos drivers AST-gated que hoy MUEREN en modo estricto: matriz (46 probes + `_seed_fid_counter` sobre `F-10`) y higyrus (17 probes restantes)
- [x] 33-03-PLAN.md — iol (15 probes + rama `IOLDecodeError` como `SHAPE` delante del handler ancho) y ámbito (7 probes + `_seed_fid_counter`, smoke D-12)
- [x] 33-04-PLAN.md — market-data: `_ENDPOINT_TEMPLATES` nuevo (D-03), clasificación `SHAPE` centralizada en `_finding_for_exc` (un edit cubre los 43 sitios), 43 probes decorados

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 33-05-PLAN.md — Gates pre-run (cobertura AST sobre los 130 probes, consistencia fid/finding, pre-flight de autenticación real) + corridas en vivo de dos pasadas × 5 paquetes + `33-CENSUS.md` contra el piso `≥96` con re-scope nombrado

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 33-06-PLAN.md — Censo de `Literal` sobre wire crudo (7 campos RESPONSE de matriz sin ampliar ningún alias + `Titulo.mercado`/`plazo` de iol) → `33-LITERALS.md` y cierre de DT-07 como `str` permanente con evidencia

**Wave 5** *(blocked on Wave 4 completion)*

- [x] 33-07-PLAN.md — Triage + fixes in-cycle espejados sync/async con test de regresión mockeado por fix bajo `packages/**/tests/` + `verify_cycle_closure` PASS **no-vacuo** con piso numérico por paquete

### Phase 34: Releases por paquete

**Goal**: Los paquetes cuya superficie pública cambió quedan publicados por el pipeline de tags, con la ruptura dict→modelo declarada en el changelog y toda operación irreversible detrás de un gate humano.
**Depends on**: Phase 33
**Requirements**: PUB-TYP-01
**Success Criteria** (what must be TRUE):

  1. **Sólo** los paquetes cuya superficie pública cambió se bumpean y publican; `iol-client` 0.2.0 → **0.3.0** con el callout source-breaking (dict→modelo, incluido el flip de truthiness) **primero** en el changelog (DT-08); los paquetes sin cambios NO se re-publican. **Ampliación registrada por el plan 33-07 (2026-08-27):** `market-data-client` 0.4.0 → **0.5.0**, también **source-breaking**, por las tres disposiciones `fix-shape-now` que el operator lockeó en el checkpoint 33-07 Task 1 — (a) `preview_calendar_config` pasa de `-> CalendarConfig` a `-> CalendarConfigPreview` en las dos superficies y en los dos shims module-level; (b) `MarketDataSnapshot.entries` / `.market_data` / `.staleness_seconds` pasan a `| None`; (c) `Symbol.created_at` / `.updated_at` pasan de `str = ""` a `str | None = None`. `__version__` y `pyproject` **no se movieron** en la Phase 33 a propósito: la opción elegida es explícitamente *"que la Phase 34 cargue la consecuencia de semver"*. Los dos paquetes source-breaking necesitan callout de changelog, no uno solo.
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
| 29. Decoder observable                                      | v1.6      | 10/10 | Complete    | 2026-08-19 |
| 30. `iol-client` tipado                                     | v1.6      | 13/13 | Complete    | 2026-08-23 |
| 31. Endpoints de ops + estructura uniforme                  | v1.6      | 5/5 | Complete    | 2026-08-25 |
| 32. Gates de homogeneidad + D-16                            | v1.6      | 6/6 | Complete    | 2026-08-25 |
| 33. Verificación en vivo en modo estricto + fixes           | v1.6      | 7/7 | Complete   | 2026-08-27 |
| 34. Releases por paquete                                    | v1.6      | 0/? | Not started | -          |

## Backlog

*(Candidate items for next milestone; see `.planning/todos/pending/` + v1.0/v1.1/v1.2/v1.3 milestone audits deferred sections)*

### Deferred to v1.7+ (from v1.6)

- **HARN-VERIF-01 — reparar las firmas de probe stale de `main_matriz.py` en `verification/`** — paquete: `matriz-client`. Archivos: `verification/test_matriz_sweep_snapshot.py` (17 FAILED + 17 ERROR) y `verification/test_main_matriz_login_fail_uniformity.py` (2 FAILED + 2 ERROR). Causa raíz única: ambos llaman a los probes de `main_matriz.py` sin argumentos (`TypeError: probe_get_segments() missing 1 required positional argument: 'client'`), firma pre-migración REFAC-05 de la Phase 15; cada caso cuenta doble porque el teardown de `pytest_httpx` asevera que la respuesta mockeada fue pedida. Explica el **100%** del rojo de `verification/` (19 failed / 19 errors, medido en `33-BASELINE.md` sobre `0a9fdae`). Incluye el gap gemelo de **43 errores de `uv run mypy verification` en 8 archivos**: `verification/` está fuera del `files` de mypy y del scope `^packages/.*/src/` del hook de pre-commit. Es rot **invisible por construcción** — `verification/` nunca corrió en CI (el job `test` pasa una ruta explícita que anula `testpaths`) — no un CI failure. Excluido por escrito del scope de LIVE-TYP-01 (P-13) y deliberadamente NO absorbido en la Phase 34 (releases), que ya rechazó una vez expandir el diff del PR de release por el mismo motivo (ver D-16). Precaución al repararlo: estos dos archivos son el **canario** del refactor de `probe_context` de los planes 33-02/33-03, porque invocan los probes directamente y no vía `main()`.

- **LIVE-MATZ-33 — censo en vivo de `matriz-client` + disposición de S-3/S-4/S-5** — paquete: `matriz-client`. El pase observable de la Phase 33 (plan 33-05, 2026-08-27) **no pudo correr**: `main_matriz.py` aborta en el assert de hostname **D-MATZ-33** (`:2550`) porque `PRIMARY_BASE_URL` apunta a `api.demo.matrizoms.com.ar`, que no es el sandbox remarkets al que la política de seguridad de la Phase 5 restringe la verificación. Las credenciales **sí** autentican (`preflight_33.py` → `AUTH OK`); el bloqueo es de política, no de auth, y **no se debe rodear** (la superficie de matriz incluye entrada de órdenes; prohibición P-05 de 33-05). Queda sin contrastar el piso `≥24` de `29-SIZING.md` (equivalente en triples distintos: 14) y quedan **COULD-NOT-DECIDE** las tres estructurales del paquete: **S-3** (`Instrument.instrumentId` ausente en byCFICode/bySegment, con `marketId`/`symbol` llegando aplanados y descartados como `extra` — *"the highest-consequence finding in the set"* según `29-SIZING.md`), **S-4** (`InstrumentDetail` no declara 7 claves del wire) y **S-5** (`MarketDataSnapshot.LA/.SE/.OI/.CL` no-`Optional` llegando `null`). **Requisito de ventana horaria:** el pase observable tiene que correr **dentro de una sesión de trading de ARG** o S-5 sigue siendo indecidible — un `null` de mercado cerrado no se distingue de un error de modelado (P-12). Colateral: las **nueve** entradas de `_SCHEMA_FILES` declaradas y ausentes en disco (orders / positions / account-report) sólo toman su rama write-once en una corrida exitosa. Detalle completo en `33-CENSUS.md`. **Ampliación (plan 33-06, 2026-08-27):** el mismo gate bloqueó el **censo de valores de los siete campos RESPONSE con alias `Literal`** — `marketId` (`Segment`, `InstrumentId`), `cficode` (`Instrument`, `InstrumentDetail`), `currency` y `orderTypes` (`InstrumentDetail`) y `ordType` (`Order`). Los cuatro alias (`MarketId`, `CFICode`, `Currency`, `OrderType`) quedan confirmados como **decodificando sin enforcement** (`POLICY` de matriz pasa `literal_enforced=False` y `scalar_passthrough=True`, `_decode.py:136`), pero **qué valores manda el vendor sigue sin medirse**: es la mitad abierta del criterio 3. `scripts/literal_census_33.py` ya lleva el gate remarkets-only y corre el censo completo apenas haya un `PRIMARY_BASE_URL` de remarkets con credenciales emitidas para ese host. Colateral del mismo desbloqueo: corregir el párrafo `29-DLOCK-RESPONSE-LITERAL.md:140-142`, que afirma que el stream de divergencias es el mecanismo de censo — la rama `Literal` de `walk_field` (`_decode.py:521-534`) retorna temprano con `literal_enforced=False` y nunca llama al sink, así que no lo es. El lock está firmado, así que la corrección es del firmante. Detalle en `33-LITERALS.md`.

- **LIVE-HIGY-33 — censo en vivo de `higyrus-client` (piso `≥22` sin contrastar)** — paquete: `higyrus-client`. El pre-flight de la Phase 33 (plan 33-05, 2026-08-27) imprimió `AUTH FAIL ConnectError`. Diagnóstico acotado: las tres variables (`HIGYRUS_BASE_URL`, `HIGYRUS_USER`, `HIGYRUS_PASSWORD`) están presentes y el esquema es `https`, pero el hostname **no resuelve por DNS** (`socket.gaierror`) desde la red de desarrollo — es alcanzabilidad de red (host plausiblemente interno/VPN), no rechazo de credenciales. Por D-13 el paquete se registró como `SKIPPED — vendor inalcanzable`, **nunca como cero**. Quedan sin contrastar los 22 triples `missing` del piso: `Movimiento` (9), `PosicionValuada` (11), `Posicion` (2). Al desbloquearlo, el camino es el de operador-corre-y-pega de la Phase 23. Detalle completo en `33-CENSUS.md`.

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
