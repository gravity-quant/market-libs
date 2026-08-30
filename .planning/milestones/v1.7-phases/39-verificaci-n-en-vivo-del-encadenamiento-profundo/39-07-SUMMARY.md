---
phase: 39-verificaci-n-en-vivo-del-encadenamiento-profundo
plan: 07
subsystem: testing
tags: [live-verification, matriz-client, iol-client, higyrus-client, ambito-financiero-client, null-object, wire-shape, bbsa, httpx]

# Dependency graph
requires:
  - phase: 39-01
    provides: "rama de skip con causa medida y destino nombrado; retítulo del finding terminal de matriz; ampliación D-02 del allowlist D-MATZ-33 a bbsa"
  - phase: 39-02
    provides: "suites mockeadas de bordes de cadena profunda por paquete — la mitad que cubre los casos límite que la corrida en vivo no pudo producir"
  - phase: 39-03
    provides: "sobres de evidencia de corrida (verification/run_evidence.py) escritos también en los caminos de skip"
  - phase: 39-06
    provides: "baselines de schema de matriz segregados por venue — sin esto la primera corrida bbsa producía deriva espuria contra líneas base de remarkets"
provides:
  - "La primera corrida en vivo de los 4 drivers en alcance con todas las cadenas profundas aterrizadas: iol RAN, ambito RAN, matriz RAN contra bbsa, higyrus SKIPPED con causa medida"
  - "14 baselines de schema del venue bbsa, incluidos los DOS endpoints Risk que ninguna fase anterior pudo capturar"
  - "Un bug real de pérdida de datos encontrado sólo por la corrida en vivo y corregido in-cycle: _core._normalize_instrument_element"
  - "Los 4 ledgers de findings con disposición argumentada por finding y cero OPEN sin destino nombrado"
  - "Firma del operador sobre los findings diferidos, con destino nombrado para cada aplazamiento (D-08)"
affects: [39-08, cierre-de-ciclo, censo-de-verificacion, release-matriz-client]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Normalización de la forma del elemento en el sitio único de _core, que ambos shells (client.py y aio.py) atraviesan por REFAC-03 — el espejo sync/async sale gratis"
    - "Una sola corrida autoritativa por paquete: el harness re-emite findings por corrida (D39-03), así que correr dos veces contamina el ledger"

key-files:
  created:
    - packages/matriz-client/tests/test_instruments_flat_identifier_shape.py
    - .planning/verification/run-evidence/{iol,higyrus,matriz,ambito-financiero}-client.json
    - .planning/verification/schemas/matriz-client/*.bbsa.json (14 baselines)
  modified:
    - packages/matriz-client/src/matriz_client/_core.py
    - .planning/verification/matriz-client-findings.md
    - .planning/verification/iol-client-findings.md

key-decisions:
  - "La divergencia CONFIRMED del identificador plano de byCFICode/bySegment se corrige in-cycle en _core, no en cada shell: sitio único, espejo sync/async garantizado por construcción"
  - "MATRIZ_SAMPLE_SYMBOL se pasa explícito por CLI porque el valor de .env (AL30) es de la era remarkets y no existe en bbsa — medido: 0 coincidencias sobre 9684 instrumentos"
  - "F-11 queda NO-FIX medido a medias con destino nombrado LIVE-POS-39: el contenedor quedó confirmado y sólo la hoja sigue sin medir, por ausencia de posiciones en la cuenta"
  - "F-01 de iol se mantiene OPEN arrastrado con destino LIVE-NOBJ-01: promover un finding a terminal es firma del operador, y el operador no la firmó"
  - "Los identificadores de orden de muestra quedan sin redactar en los ledgers, con el precedente ya vigente (HIGYRUS_SAMPLE_CUENTA=5208)"

patterns-established:
  - "Disposición argumentada por finding con los ceros declarados por enumeración: un paquete sin findings nuevos dice su causa, nunca deja la fila vacía"
  - "Toda regresión de una divergencia en vivo vive bajo packages/<pkg>/tests/, nunca bajo verification/ — ese árbol sólo corre por allowlist"

requirements-completed: [LIVE-NOBJ-01]

# Metrics
duration: 1h 25m
completed: 2026-08-30
status: complete
---

# Phase 39 Plan 07: Corrida en vivo de los 4 drivers + fix in-cycle Summary

**Los cuatro drivers en alcance corrieron contra sus APIs reales (iol/ambito/matriz RAN, higyrus SKIPPED por DNS con destino nombrado), y la corrida encontró un bug de pérdida total de datos que ninguna suite mockeada podía ver: `/rest/instruments/byCFICode` y `/bySegment` devuelven el identificador plano, y la política Null Object lo colapsaba en silencio — 9160 instrumentos sin símbolo, corregido in-cycle en `_core` con espejo sync/async y 13 regresiones.**

## Performance

- **Duration:** ~1h 25m (corrida + triage + fix + disposición + checkpoint)
- **Started:** 2026-08-30T02:41:17Z (sábado 2026-08-29 23:34 ART)
- **Completed:** 2026-08-30
- **Tasks:** 3 (2 auto + 1 checkpoint bloqueante)
- **Files modified:** 23

## Accomplishments

- **Las cuatro corridas en vivo, con clasificación honesta y cero errores de handler.** Ningún paquete quedó `FAILED`; el único `SKIPPED` viene con causa medida y destino nombrado.
- **Una divergencia CONFIRMED encontrada y corregida dentro del mismo ciclo** (F-43/F-44), con espejo sync/async y regresión mockeada que CI sí corre.
- **Los dos endpoints Risk de matriz quedaron capturados por primera vez.** `LIVE-MATZ-33` era la causa bloqueante que F-11 y F-12 nombraban desde la Phase 37; ambos recibieron su medición.
- **Los 28 findings nuevos quedaron dispositionados uno por uno**, y el ledger de matriz cerró con **cero OPEN**.
- **Checkpoint de disposición firmado por el operador**, con destino nombrado para todo lo diferido.

## Transcripción de las cuatro corridas (Task 1)

Ventana horaria declarada: **sábado 2026-08-29 23:34 ART — mercado cerrado**, fuera de toda sesión de negociación ARG (D-12 / A5). El discriminador usado es el de D-MATZ-5, no se inventó otro: `/rest/marketdata/get` devolvió las siete entradas (`BI,OF,LA,OP,CL,SE,OI`) en `null`, así que `LA` no es dict y la rama de antigüedad de `LA.date` no se ejecutó — el camino que aplicó es el de `LA` ausente/nula.

Re-sondeo DNS de la sesión (A2 de RESEARCH, leyendo sólo **nombres** de variables de entorno, nunca sus valores): tres de los cuatro hosts resolvieron; el de higyrus **no**, confirmando que la mitad en vivo de D-04 sigue sin ser ejecutable.

| Paquete | Clasificación | Línea `SUMMARY` verbatim | Probes | Errores de handler |
|---|---|---|---|---|
| iol-client | **RAN** | `SUMMARY: PASS=14 FAIL=0 SKIPPED=1 FINDING=0 DIVERGENCES=0 HANDLER_ERRORS=0` | 15 | **0** |
| ambito-financiero-client | **RAN** | `SUMMARY: PASS=6 FAIL=0 SKIPPED=1 FINDING=0 DIVERGENCES=0 HANDLER_ERRORS=0` | 7 | **0** |
| matriz-client | **RAN** (venue bbsa) | `SUMMARY: PASS=39 FAIL=0 SKIPPED=4 FINDING=7 DIVERGENCES=9 HANDLER_ERRORS=0` → post-fix `DIVERGENCES=7` | 50 | **0** |
| higyrus-client | **SKIPPED** | `SKIPPED higyrus-client: vendor host unreachable (DNS) — LIVE-HIGY-33` | 0 | n/a |

**El gate duro de la Task 1 se cumplió:** el conteo de errores del handler de divergencias fue **cero** en las tres corridas que produjeron `SUMMARY`. El censo no se construyó sobre un pipeline que falló en silencio.

Los cuatro sobres de evidencia existen bajo `.planning/verification/run-evidence/`, uno por slug, incluido el del camino de skip. `main_market_data.py` no aparece en `git diff --name-only` del plan (D-07 respetado). Los 8 baselines de remarkets quedaron byte-idénticos; los 14 nuevos llevan el token de venue `bbsa`.

**Casos límite de D-12 forzados intencionalmente y qué produjo cada uno realmente:**

- Colección vacía sobre datos reales: `get_trades` devolvió `[]` (F-13), `get_positions` devolvió 0 posiciones, `get_all_orders` devolvió 0 órdenes.
- Cadena profunda sobre eslabones nulos: los seis alias de `MarketDataSnapshot` se desreferenciaron con las siete entradas en `null` — `last=None bids=0 offers=0 settlement=None close=None oi=None`, idéntico en `client.py` y `aio.py`, sin una sola excepción. **SC-2 demostrado en vivo, no contra fixtures.**
- Casos **no** observados: los bordes que requieren mercado abierto (fila con datos parciales, `LA` presente pero rancio) quedaron cubiertos por la mitad mockeada del plan 39-02. El censo declara cuál mitad cubrió cada caso.

## Task Commits

1. **Task 1: Pre-vuelo medido + corrida en vivo de los 4 drivers** — `3280cd2` (chore)
2. **Task 2 (RED): la forma plana que el cliente descartaba** — `5674da1` (test)
3. **Task 2 (GREEN): normalización del identificador plano** — `9453acc` (fix)
4. **Task 2 (disposición): los 28 findings argumentados** — `19f8265` (docs)
5. **Task 2 (deuda fuera de alcance): D39-03 y D39-04** — `7ce1fa5` (docs)
6. **Task 3: firma del operador sobre los findings diferidos** — `eeefe73` (docs)

## El fix in-cycle (Task 2, TDD)

**Divergencia CONFIRMED:** `/rest/instruments/byCFICode` y `/rest/instruments/bySegment` devuelven el identificador **plano** (`{marketId, symbol}`), no anidado bajo `instrumentId` como `/rest/instruments/all`. Sobre esa forma la política Null Object (Phase 35 / NOBJ-02) colapsaba el eslabón ausente a `InstrumentId.empty()` **sin emitir divergencia**, y los únicos datos que el wire traía se descartaban como `extra`.

**Medido:** 386 y 9160 objetos `Instrument` con `marketId=None, symbol=None, cficode=None` — el **100% del payload de dos métodos públicos**, perdido en silencio en las cuatro superficies. Confirmado en los **dos** venues del allowlist (baseline remarkets 2026-06-10 y captura bbsa 2026-08-30): no es deriva entre venues, es un defecto del cliente.

- **RED** (`5674da1`): 4/9 tests fallando contra la forma real.
- **GREEN** (`9453acc`): `_core._normalize_instrument_element` — sitio único que ambos shells atraviesan por REFAC-03, mismo mecanismo de espejo sync/async que cerró F-09. 13/13 verde.
- La regresión vive en `packages/matriz-client/tests/test_instruments_flat_identifier_shape.py` (bajo `packages/`, que CI corre por paquete y por versión de Python — **no** bajo `verification/`), y pinea las cuatro superficies afectadas más el control poblado de la forma anidada, la tolerancia forward-compat y seis bordes degenerados.
- Post-fix la corrida en vivo baja de `DIVERGENCES=9` a `DIVERGENCES=7` y los 9160 instrumentos llegan con su símbolo real. **La baja es por corrección real, no por colapso de política.**

Cero dependencias nuevas (T-39-SC respetado). Ningún módulo compartido ni import cruzado entre paquetes.

## Tabla de disposición de findings — ceros declarados por enumeración

| Paquete | Findings nuevos | Disposición |
|---|---|---|
| **matriz-client** | 28 (F-13..F-35, F-43, F-44, F-63..F-65) | 2 FIXED (F-43/F-44, corregidos in-cycle), 6 EXPECTED (F-14/F-15/F-16 + espejos async F-63/F-64/F-65 — identificadores de la era remarkets inexistentes en bbsa; el cliente mapeó el error del vendor fielmente), 20 NO-FIX (F-13 colección vacía por mercado cerrado; F-17..F-27 y F-29..F-35 wire-superset tolerado por diseño y reportado como `extra` no-fatal). Ledger completo: **40 findings, cero OPEN** (3 FIXED, 7 EXPECTED, 30 NO-FIX). |
| **iol-client** | **0** — y la causa está medida | El driver **RAN** limpio (`FINDING=0 DIVERGENCES=0`) y la zona AUTO-GENERATED quedó byte-idéntica. F-01 se arrastra OPEN con destino nombrado; ver el ítem A abajo. |
| **higyrus-client** | **0** — y la causa está medida | **No corrió**: host del vendor irresoluble por DNS, re-sondeado en esta sesión. Ledger byte-idéntico. Destino `LIVE-HIGY-33`. |
| **ambito-financiero-client** | **0** — y la causa está medida | **Corrió limpio**: `PASS=6 FINDING=0 DIVERGENCES=0`. Ledger byte-idéntico. Cero por ausencia de divergencias, no por ausencia de observación. |

**Finding terminal superseded de matriz (Pitfall 5) — disposicionado, no borrado:** F-02 y F-10 (`prod-vs-remarkets divergence acknowledged`) quedaron en el ledger porque la deduplicación por título creó uno nuevo cuando D-02 amplió el allowlist. Ambos quedan **NO-FIX SUPERSEDED**, nombrando explícitamente a **F-28** (`prod-vs-sandbox divergence acknowledged`, EXPECTED) como su reemplazo.

## Task 3 — Checkpoint bloqueante: disposición firmada por el operador

**Respuesta del operador, verbatim:**

> Approved

El operador aprobó el checkpoint tal como fue presentado: aceptar todos los valores por defecto propuestos. La aprobación **no** se derivó de `auto_advance` ni de ningún `mode: yolo` — fue una respuesta explícita en esta sesión, como exige D-08. Resolución punto por punto:

| Ítem | Finding | Resolución firmada |
|---|---|---|
| **A** | iol F-01 (`missing simbolo` en `get_quote`) | **OPEN arrastrado**, destino nombrado **`LIVE-NOBJ-01`**, con su fundamento preexistente citado. El operador **no** firmó la promoción a terminal, que era la lectura alternativa planteada: la evidencia favorecía que la divergencia está materialmente resuelta (la Phase 30 retiró `simbolo` de `_ASSUMED_QUOTE_FIELDS` y del modelo `Cotizacion`), pero promover un finding a terminal es firma del operador, no del ejecutor. Registrado como `Operator signoff: sebadlf, 2026-08-30`. |
| **B** | matriz F-24 / F-25 (`AccountReport.hasError` / `.lastCalculation`) | **NO-FIX terminal**, wire-superset tolerado, **sin ruteo a Phase 40**. No hay divergencia real que diferir —el superset es tolerado por diseño y la divergencia quedó reportada, no silenciada—, así que D-08 no exige destino nombrado. |
| **C** | matriz F-11 (`DetailedPosition.report`, roster de la hoja aún sin medir) | **NO-FIX, medido a medias**, con destino nombrado **`LIVE-POS-39`**. El contenedor quedó CONFIRMADO en vivo (`report` es un mapa, vacío porque la cuenta no tiene posiciones en bbsa); sólo el roster de la hoja `InstrumentPositionReport` sigue UNMEASURED, y la causa cambió de política a datos. El nombre se eligió entre las dos opciones que el propio checkpoint ofreció, siguiendo la convención `LIVE-<PKG>-<NN>` ya usada por `LIVE-HIGY-33` / `LIVE-MATZ-33` / `LIVE-NOBJ-01` — es una etiqueta de bookkeeping, no una decisión nueva de alcance o seguridad. |
| **D** | D39-03 (duplicación de findings al re-correr) y D39-04 (mock con una forma que el vendor no emite) | **Fuera de alcance** de la Phase 39, tracked en `deferred-items.md` junto a `HARN-VERIF-01`. Son propiedades del harness de verificación, no divergencias entre cliente y API, así que D-08 no aplica. Se mantiene la mitigación de procedimiento ya aplicada: una sola corrida autoritativa por paquete. |
| **Redacción** | identificadores de orden de muestra en los ledgers | **Sin redactar**, tal como quedaron committeados. Coincide con el precedente ya vigente en los ledgers (`HIGYRUS_SAMPLE_CUENTA=5208`). No son credenciales: `safe_print(..., secrets=[...])` sigue redactando usuario, contraseña, token e identificador de cuenta en todo el stdout de driver (T-39-25). |

Los seis puntos de `how-to-verify` del checkpoint quedaron confirmados: tabla de disposición completa con ceros por enumeración (1), destino nombrado para cada aplazamiento (2), ningún `SKIPPED` escondiendo un fallo real (3), finding terminal superseded disposicionado (4), errores de handler en cero (5), y ventana horaria declarada con el discriminador de antigüedad de `LA.date` documentado (6).

## Files Created/Modified

- `packages/matriz-client/src/matriz_client/_core.py` — `_normalize_instrument_element`: normaliza la forma plana del identificador de `byCFICode`/`bySegment` en el sitio único que ambos shells atraviesan
- `packages/matriz-client/tests/test_instruments_flat_identifier_shape.py` — 13 casos que pinean las cuatro superficies afectadas, el control poblado de la forma anidada, la tolerancia forward-compat y seis bordes degenerados
- `.planning/verification/run-evidence/{iol,higyrus,matriz,ambito-financiero}-client.json` — un sobre por slug, con conteo de probes, timestamp y triples distintas
- `.planning/verification/schemas/matriz-client/*.bbsa.json` — 14 baselines del venue bbsa, incluidos los dos endpoints Risk
- `.planning/verification/matriz-client-findings.md` — 28 findings dispositionados, Run Context con ventana horaria y run params, sección de cierre de ciclo de la Phase 39
- `.planning/verification/iol-client-findings.md` — F-01 arrastrado con el hecho nuevo medido y la firma del operador
- `.planning/phases/39-.../deferred-items.md` — D39-03 y D39-04 registrados con su resolución

## Decisions Made

Ver `key-decisions` en el frontmatter. La decisión de fondo: **la corrida en vivo encontró algo que ninguna suite mockeada podía encontrar.** D39-04 lo deja medido — `test_get_instruments_by_segment_url_invariant_phase5` mockeaba el elemento anidado y pasaba en verde mientras el método perdía el 100% de su payload contra el servicio real. Ése es exactamente el modo de falla que justifica la fase.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `MATRIZ_SAMPLE_SYMBOL` de `.env` no existe en el venue bbsa**
- **Found during:** Task 1 (corrida en vivo de matriz)
- **Issue:** El valor de `.env` (`AL30`) es de la era remarkets. Medido: **0 coincidencias sobre 9684 instrumentos** en bbsa. Sin override, `get_instrument_detail` / `get_market_data` y sus espejos async fallaban y la cadena profunda de D-05 quedaba sin ejercitar — es decir, el objetivo literal del plan no se podía medir.
- **Fix:** Se pasó `MATRIZ_SAMPLE_SYMBOL='MERV - XMEV - XLC - CI'` explícito por CLI, exactamente el símbolo que el driver auto-resuelve en bbsa sin override (`instruments[0].instrumentId.symbol`, D-MATZ-1). Precedente: el bloque análogo de `higyrus-client-findings.md`. Registrado en el Run Context del ledger.
- **Verification:** La cadena profunda de `MarketDataSnapshot` corrió en las dos superficies; `PASS=39 FAIL=0`.
- **Committed in:** `3280cd2`

**2. [Rule 3 - Blocking] El harness duplica findings al re-correr un driver**
- **Found during:** Task 1 (el plan pide correr cada driver individualmente **y después** `main_verify.py`, que los vuelve a correr a todos)
- **Issue:** El plan afirma que "la deduplicación por título es content-addressed cross-run". **Premisa falsificada y medida:** `verification/findings.py:597` declara `idempotent_by_title: bool = False` y los ~40 call sites de probe usan el default. Dos corridas consecutivas del driver de matriz produjeron **16 bloques duplicados por título**; una corrida de `main_verify.py` agregó 40+ bloques `OPEN` duplicados al ledger de `market-data-client`, un paquete que D-07 declara fuera de alcance.
- **Fix:** Los ledgers se restauraron a su estado previo y se produjo **una sola corrida autoritativa por paquete**, de modo que el censo del 39-08 no herede duplicados que son un artefacto del procedimiento y no una medición. El ledger de `market-data-client` quedó byte-idéntico (D-07 respetado).
- **Verification:** `git diff` de los ledgers muestra sólo bloques de la corrida autoritativa; `main_market_data.py` y su ledger byte-idénticos.
- **Committed in:** `3280cd2`, documentado como D39-03 en `7ce1fa5`

---

**Total deviations:** 2 auto-fixed (ambas Rule 3 - blocking). Ninguna arquitectónica; ninguna requirió Rule 4.
**Impact on plan:** Ambas eran prerrequisitos para que la corrida produjera evidencia honesta en vez de basura — que es literalmente el propósito declarado del plan. Sin la primera, la cadena profunda de matriz no se ejercitaba; sin la segunda, el censo del 39-08 heredaba duplicados fabricados por el procedimiento de ejecución. Cero scope creep: no se tocó `main_market_data.py`, no se reparó la suite rota de `verification/` (`HARN-VERIF-01`), y no se introdujo ninguna dependencia.

## Issues Encountered

- **`LIVE-HIGY-33` sigue bloqueando a higyrus.** El re-sondeo DNS de esta sesión (A2 de RESEARCH exigía re-sondear, no asumir) confirmó que el host del vendor sigue irresoluble. La rama de skip del plan 39-01 funcionó: produjo la línea `SKIPPED` con causa medida y destino nombrado, y su sobre de evidencia, en vez de un cero silencioso. **Resuelto según diseño, no pendiente.**
- **Un mock codificaba una forma que el vendor no emite** (D39-04). Descubierto al escribir la regresión de F-43/F-44. No se corrigió en este plan porque su aserción declarada es la URL, no la forma del elemento, y la forma real ya quedó pinneada contra las capturas. Registrado con destino sugerido: un barrido de mocks contra los baselines committeados cerraría esta clase entera.

## Known Stubs

Ninguno. El único roster que queda sin medir es el de la hoja `InstrumentPositionReport` (F-11), y no es un stub: es una medición imposible sin posiciones abiertas en la cuenta, documentada con destino nombrado `LIVE-POS-39` y firmada por el operador.

## Threat Flags

Ninguna superficie de seguridad nueva. El único cambio de código (`_core._normalize_instrument_element`) es una normalización de forma sobre payload ya recibido: no agrega endpoints, ni rutas de auth, ni accesos a disco, ni cambios de esquema en un límite de confianza. `verification/mutation_gate.py` quedó **byte-idéntico** (T-39-26): bajo bbsa las mutaciones siguen fail-closed, y la lista de probes del sweep no contiene ninguna alta, reemplazo ni cancelación de orden.

## User Setup Required

None — no external service configuration required. Las credenciales ya vivían en los `.env` por paquete; no se leyó ni se transcribió ningún valor de `.env` (sólo **nombres** de variables), y todo el stdout transcrito es el redactado por `safe_print`.

## Next Phase Readiness

- **Listo para el 39-08 (censo y cierre de ciclo):** los cuatro sobres de evidencia, los cuatro ledgers dispositionados con cero OPEN sin destino, y la sección de cierre de ciclo `verification-cycle-2026-Q3-nobj` en el ledger de matriz están en disco.
- El censo debe contabilizar explícitamente que **F-01 de iol persiste OPEN y no fue re-emitido**: su permanencia no es una regresión nueva, y su no-re-emisión no es un fix declarado.
- **Deuda que el 39-08 encontrará predicha, no la redescubrirá:** D39-01, D39-02, D39-03 y D39-04 en `deferred-items.md`, más `LIVE-HIGY-33` y `LIVE-POS-39` como destinos nombrados vivos.

## Self-Check: PASSED

- `packages/matriz-client/src/matriz_client/_core.py` — FOUND
- `packages/matriz-client/tests/test_instruments_flat_identifier_shape.py` — FOUND
- `.planning/verification/run-evidence/` — FOUND (4 sobres, uno por slug)
- `.planning/verification/schemas/matriz-client/` — FOUND (14 baselines bbsa; los 8 de remarkets byte-idénticos)
- Commits `3280cd2`, `5674da1`, `9453acc`, `19f8265`, `7ce1fa5`, `eeefe73` — FOUND
- `uv run --frozen python -m pytest -q verification/test_cycle_closure_phase33.py` → **21 passed**
- `main_market_data.py` ausente de `git diff --name-only` del plan — CONFIRMED (D-07)

---
*Phase: 39-verificaci-n-en-vivo-del-encadenamiento-profundo*
*Completed: 2026-08-30*
