---
phase: 42-re-chequeos-en-vivo-dns-de-higyrus-port-del-gate-de-venue-ce
plan: 04
subsystem: testing
tags: [market-data-client, wire-capture, schema-snapshot, auth0, live-verification, pii-boundary, shape-diff]

# Dependency graph
requires:
  - phase: 42-re-chequeos-en-vivo-dns-de-higyrus-port-del-gate-de-venue-ce
    plan: "01"
    provides: "Aprobación humana explícita del operador (verbatim `Approved`, `gate=\"blocking-human\"`) que habilita el tráfico en vivo de este plan"
  - phase: 33-live-typ-01
    provides: "`_write_schema_snapshot` write-once (D-25) y los baselines `get-instruments.json` / `get-segments.json` fechados 2026-07-31; `verification/capture.py` como único hogar legal del payload crudo (D-11)"
  - phase: 23-market-data-driver
    provides: "`main_market_data.py` con `_ENDPOINT_TEMPLATES` (D-03), la ladder D-09 por probe y el gate de mutaciones de dos patas (LIVE-MUT-01)"
provides:
  - "Lectura FRESCA y FECHADA del wire de `/instruments` y `/segments` (`captured_at` 2026-08-31T21:27Z), producida por una corrida en vivo real contra `develop`"
  - "`42-WIRE-READ.md`: artefacto COMMITTEADO y PII-free que sobrevive a otro clone / worktree / `git clean -xdf` — la evidencia que la Phase 43 cita para SHAPE-01"
  - "Marca explícita de NO AUTORITATIVIDAD del baseline del 2026-07-31 para SHAPE-01, con la razón mecánica (write-once, D-25)"
  - "Delta medido contra el baseline: VACÍO en los dos endpoints — el wire no se movió en un mes, y la descripción de `SHAPE-MD-REF-33` queda re-validada en vivo"
  - "28 findings de disposición campo por campo de `Instrument`/`Segment` (F-205…F-218 sync, F-229…F-242 async), nuevos en el ledger, que alimentan el criterio 1 de la Phase 43"
  - "D42-DEF-02: descubrimiento de que el SHAPE-diff del driver está INERTE para `Instrument`/`Segment` — riesgo de falso verde para el criterio 2 de la Phase 43"
affects: [42-05, 42-06, 43-shape-01, 43-harn-02, 45-harn-01]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Envelope timestampeado sobre `capture()`: el payload crudo se envuelve en `{captured_at, endpoint, client_function, base_url, n_rows, schema, payload}`, espejando la forma de `_write_schema_snapshot` — la captura gitignored deja de depender del mtime del filesystem para su fecha"
    - "Evidencia de dos mitades para criterios que exigen 'lectura fresca': la captura cruda va al staging gitignored y un artefacto markdown COMMITTEADO lleva `captured_at` + `schema_of()`, porque sólo la segunda mitad sobrevive a otro clone"
    - "Aserción programática de PII-freeness antes de commitear evidencia derivada del wire: parsear los bloques JSON del markdown y verificar que TODA hoja pertenece al conjunto de nombres de tipo"

key-files:
  created:
    - .planning/phases/42-re-chequeos-en-vivo-dns-de-higyrus-port-del-gate-de-venue-ce/42-WIRE-READ.md
  modified:
    - main_market_data.py
    - .planning/verification/market-data-client-findings.md
    - .planning/phases/42-re-chequeos-en-vivo-dns-de-higyrus-port-del-gate-de-venue-ce/deferred-items.md

key-decisions:
  - "`n_rows` salió `null` en los DOS endpoints y NO se 'arregló': el wire devuelve un sobre paginado (`dict`), no un array desnudo, y `len(raw) if isinstance(raw, list) else None` se comportó exactamente como el plan lo especificó. Cambiar el cómputo habría exigido una segunda corrida en vivo para regenerar el mismo dato; el conteo real (50 / 4) se reporta derivado de `items` / `segments` en `42-WIRE-READ.md § 1`"
  - "El delta vacío contra el baseline se reporta como un RESULTADO de la re-medición, no como una excusa para no haberla hecho — y NO revierte la marca de no-autoritatividad: lo autoritativo es la medición de hoy, que resulta coincidir"
  - "D42-DEF-02 (SHAPE-diff inerte) se difiere en vez de arreglarse: es preexistente, no hubo pérdida de evidencia (el censo de divergencias produjo los 28 findings), y arreglarlo exigía otra corrida en vivo contra un servicio de terceros sin producir un hecho nuevo"

patterns-established:
  - "Todo criterio de fase que pida 'evidencia fresca en disco' se satisface con un artefacto committeado, nunca sólo con un archivo bajo un directorio gitignored: la evidencia gitignored no existe para la fase consumidora"
  - "Antes de commitear cualquier markdown derivado de un payload en vivo, se corre una aserción de que las hojas de los bloques JSON son nombres de tipo y de que el bloque es byte-igual al `schema` del envelope — la PII-freeness se verifica, no se afirma"

requirements-completed: [LIVE-02]

# Metrics
duration: 7min
completed: 2026-08-31
status: complete
---

# Phase 42 Plan 04: Lectura fresca del wire de `/instruments` y `/segments` Summary

**`main_market_data.py` instrumentado con `capture()` + envelope timestampeado en los dos probe sites de reference, corrido en vivo contra `develop` (exit 0, `MARKET_DATA_VERIFY_MUTATING` sin setear), produciendo dos capturas fechadas `2026-08-31T21:27Z` en el staging gitignored y `42-WIRE-READ.md` committeado y PII-free que marca el baseline del 2026-07-31 como NO AUTORITATIVO para SHAPE-01 — con el baseline write-once intacto y el payload crudo fuera de git.**

## Performance

- **Duration:** ~7 min
- **Started:** 2026-08-31T21:26:39Z
- **Completed:** 2026-08-31T21:33:26Z
- **Tasks:** 3
- **Files modified:** 4 (1 creado, 3 modificados)

## Accomplishments

- **Criterio 5 del ROADMAP satisfecho en sus DOS mitades (D-08).** La mitad barata —envelope con `captured_at` sobre `capture()`— resuelve la fecha; la mitad que importa —`42-WIRE-READ.md` committeado— resuelve la *supervivencia*. `42-RESEARCH.md § Pitfall 6` había medido que sin esa segunda mitad la "lectura fresca" existiría sólo en el working tree del ejecutor, y desaparecería en otro clone, otro worktree o un `git clean -xdf`.
- **La corrida en vivo salió limpia:** `SUMMARY: PASS=23 FAIL=0 SKIPPED=18 FINDING=2 DIVERGENCES=18 HANDLER_ERRORS=0`, exit code **0**, con `PROBE instruments_sync: PASS instruments=50` y `PROBE segments_sync: PASS segments=4`. Ningún probe de los dos endpoints devolvió `FINDING`, así que la captura salió de una lectura real y no hubo que escalar nada (T-42-16: fabricarla a mano estaba explícitamente prohibido).
- **T-42-15 verificado, no asumido.** Los dos baselines siguen con `captured_at` del **2026-07-31** después de la corrida y ninguno aparece en `git status --porcelain`. El write-once de D-25 se comportó exactamente como su contrato dice, que es la razón por la que `42-WIRE-READ.md` existe como artefacto aparte en vez de ser un refresh del baseline.
- **T-42-14 verificado.** `git status --porcelain -- .planning/verification/captures/` quedó **vacío** tras la corrida: el payload crudo aterrizó exclusivamente en el staging gitignored (`.gitignore:53`) y no rozó git.
- **T-42-05 verificado programáticamente, no por inspección visual.** Se parsearon los dos bloques JSON de `42-WIRE-READ.md` y se asertó que **toda** hoja pertenece a `{str, int, float, bool, NoneType, dict, list}` (resultado: cero hojas no-conformes) y que cada bloque es **byte-igual** al `schema` de su envelope. La clave `payload` no se transcribió.
- **T-42-02 intacto.** `MARKET_DATA_VERIFY_MUTATING` no se seteó en ninguna invocación; los 18 probes mutantes salieron `SKIPPED (mutating, guard off)` y `mutation_gate_refusal_sync`/`_async` confirmaron el rechazo con `0 HTTP, 0 Auth0`. `git hash-object verification/mutation_gate.py` = `6bdaec006cc16f7c8dbfac41701712a9085c691b` al cierre.
- **Descubrimiento de alto valor para la Phase 43 (D42-DEF-02):** el SHAPE-diff del driver (`_emit_shape`) está **inerte** para `Instrument` y `Segment`. Detalle en § Issues Encountered.

## Task Commits

Cada task se committeó atómicamente:

1. **Task 1: Instrumentar `main_market_data.py` con `capture()` y envelope timestampeado (D-07 / D-08)** — `b267bea` (feat)
   `main_market_data.py` (+34, **un solo archivo** como exigía el criterio de aceptación)
2. **Task 2: Corrida en vivo — lectura fresca del wire** — `8d584b2` (chore)
   `.planning/verification/market-data-client-findings.md` (+361/−1); las dos capturas son gitignored por diseño y no aparecen en el commit
3. **Task 3: `42-WIRE-READ.md` — evidencia committeada, PII-free, baseline no-autoritativo** — `cac158a` (docs)
   `42-WIRE-READ.md` (creado, 286 líneas), `deferred-items.md` (+D42-DEF-02)

**Plan metadata:** ver el commit `docs(42-04)` que acompaña a este SUMMARY.

_Sin gates TDD: las tres tasks son `type="auto"` sin `tdd="true"`. Ninguna es behavior-adding sobre código de paquete — la Task 1 instrumenta un driver de verificación de la raíz, no una librería publicable._

## Datos exigidos explícitamente por el `<output>` del plan

### `captured_at` verbatim de los dos envelopes y `n_rows` de cada endpoint

| Endpoint | `client_function` | `captured_at` (verbatim) | `n_rows` | Filas realmente medidas |
|----------|-------------------|--------------------------|----------|-------------------------|
| `/instruments` | `get_instruments` | `2026-08-31T21:27:42.854194+00:00` | `null` | `50` (`len(items)`) |
| `/instruments/segments` | `get_segments` | `2026-08-31T21:27:43.256969+00:00` | `null` | `4` (`len(segments)`) |

Los dos envelopes contienen las **siete** claves exigidas: `captured_at`, `endpoint`, `client_function`, `base_url`, `n_rows`, `schema`, `payload`.

**Por qué `n_rows` es `null`:** el wire de estos dos endpoints devuelve un **sobre paginado** (`dict` con `items` / `segments` adentro), no un array desnudo, así que `len(raw) if isinstance(raw, list) else None` —la fórmula que el plan especificó literalmente— evalúa a `None`. No es un defecto de la implementación: es una **propiedad de forma del wire** que el plan anticipó con su rama `else None`, y que resulta ser información útil para la Phase 43 (ver D42-DEF-02). El conteo real de filas está reportado en `42-WIRE-READ.md § 1` y coincide con lo que el driver imprimió (`instruments=50`, `segments=4`).

### Confirmación de write-once (los dos baselines siguen en 2026-07-31)

| Archivo | `captured_at` post-corrida | En `git status`? |
|---------|----------------------------|------------------|
| `.planning/verification/schemas/market-data-client/get-instruments.json` | `2026-07-31T16:49:30.691111+00:00` | **No** |
| `.planning/verification/schemas/market-data-client/get-segments.json` | `2026-07-31T16:49:31.056229+00:00` | **No** |

**Write-once respetado (D-25).** `_write_schema_snapshot` no se modificó ni se le agregó un modo overwrite. Cero regresiones de D-25 que escalar.

### Bloques `### F-` nuevos apendeados al ledger de market-data

**+40 bloques** (143 → 183), FIDs **F-202 … F-245**. Desglose:

| Cantidad | Clase | Contenido | ¿Duplicado cosmético? |
|----------|-------|-----------|------------------------|
| 10 | `SHAPE` | `schema drift en {get_health_feed, get_market_data, get_latest, get_calendar, get_calendar_config}` × sync/async | **Sí** — el título ya existía en HEAD |
| 28 | `SHAPE` | Disposición campo por campo de `Instrument` (9 triples) y `Segment` (5 triples) × sync/async | **No** — nuevos en el ledger |
| 2 | `NO-DATA` | `market_data vacío para prefix '__no_such_symbol__'` sync/async | **Sí** — el título ya existía en HEAD |

**12 de los 40 son duplicados cosméticos.** Ese churn es el ruido conocido y aceptado por `42-RESEARCH.md` Assumptions Log A4 / `ROADMAP.md:53` ("ruidoso pero no lossy"); el ledger se commiteó **tal cual salió**, sin edición manual. El dedupe es la Phase 45 (HARN-01), por decisión de orden explícita del milestone.

**Cero findings de `schema drift en get_instruments` o `en get_segments`** — consistente con el delta vacío de abajo, y evidencia independiente de que el write-once no tuvo nada que reescribir.

### Delta de claves contra el baseline

**VACÍO en los dos modelos.** Recorriendo el árbol completo del `schema` (incluidas las claves anidadas bajo `catalogue`, `items[]` y `segments[]`):

| Modelo | Fresco − baseline | Baseline − fresco | Tipos en claves compartidas |
|--------|-------------------|-------------------|------------------------------|
| `Instrument` (`/instruments`) | ∅ | ∅ | sin cambios |
| `Segment` (`/instruments/segments`) | ∅ | ∅ | sin cambios |

El schema fresco es **idéntico** al del 2026-07-31 en los dos endpoints.

**Qué significa:** el wire no se movió en un mes, así que la descripción del backlog `SHAPE-MD-REF-33` queda re-validada en vivo — `Instrument` declara `marketId`/`instrumentType` que el wire no manda y omite siete claves que sí manda; `Segment` y el wire son **conjuntos disjuntos**. La Phase 43 puede trabajar sobre esa base sin re-medir.

**Qué NO significa:** que los baselines pasen a ser autoritativos. Lo autoritativo es la medición de **hoy**, que resulta coincidir. Un delta vacío es un resultado de la re-medición, no un sustituto de haberla hecho — y la Phase 43 necesita poder citar una fecha de esta sesión, que es precisamente el punto del criterio 5.

## Verificación del plan — resultados medidos

| # | Chequeo | Resultado |
|---|---------|-----------|
| 1 | Checkpoint de 42-01 aprobado y transcrito verbatim | **Sí** — `Approved`, confirmado antes de la primera llamada de red |
| 2 | `uv run --frozen ruff check .` | `All checks passed!` |
| 2 | `uv run --frozen ruff format --check .` | `279 files already formatted` |
| 2 | `uv run --frozen mypy` | `Success: no issues found in 75 source files` |
| 3 | 8 locks de `verification/test_main_market_data_*.py` | **27 passed**, 0 failed — idéntico al baseline de HEAD |
| 3 | `verification/test_cycle_closure_market_data.py` | 2 passed |
| 4 | Capturas con `captured_at` de hoy | **Sí** — `2026-08-31T21:27:42Z` / `21:27:43Z` |
| 4 | Baselines siguen en `2026-07-31` | **Sí** — los dos |
| 5 | `git status --porcelain -- .planning/verification/captures/` | **Vacío** |
| 6 | `42-WIRE-READ.md` con `NO AUTORITATIVO` y los dos schemas | **Sí** — 286 líneas, 2 bloques JSON |
| 6 | Hojas JSON no-conformes a nombre de tipo | **Cero** (aserción programática) |
| 7 | `git hash-object verification/mutation_gate.py` | `6bdaec006cc16f7c8dbfac41701712a9085c691b` |

Adicionalmente: `grep -c 'wire-instruments-42'` = **1** y `grep -c 'wire-segments-42'` = **1** (una sola llamada por endpoint, sólo en la superficie sync — los espejos async no se instrumentaron, por decisión del plan); `git diff --stat` de la Task 1 tocó **un solo archivo**; y el scan de credenciales sobre el diff del ledger y sobre `42-WIRE-READ.md` no encontró ningún patrón (`secret`, `token`, `bearer`, `password`, `client_secret`, `api_key`).

## Files Created/Modified

- `main_market_data.py` *(modificado, +34)* — `from verification.capture import capture` (import top-level, sin `# noqa`, en orden alfabético antes de `verification.cycle_report`); llamada a `capture("market-data", "wire-instruments-42", …)` en `probe_instruments_sync` y su espejo `"wire-segments-42"` en `probe_segments_sync`, ambas **dentro del `try`** (D-09) y con el `endpoint` tomado de `_ENDPOINT_TEMPLATES` en vez del literal repetido. `_write_schema_snapshot` **sin tocar**.
- `.planning/phases/42-…/42-WIRE-READ.md` *(creado, 286 líneas)* — las seis secciones que el plan pedía, en orden: sobre de la lectura (tabla + comando + exit code), schema medido (2 bloques JSON verbatim), marca de **NO AUTORITATIVO** con su razón mecánica, delta contra el baseline (+ la subsección 4.1 sobre el origen real de la disposición campo por campo), dónde vive el crudo y por qué no está acá, y qué NO decide este documento.
- `.planning/verification/market-data-client-findings.md` *(modificado, +361/−1)* — salida de la corrida, sin editar a mano.
- `.planning/phases/42-…/deferred-items.md` *(modificado)* — entrada **D42-DEF-02**.

## Decisions Made

- **No "arreglar" `n_rows`.** Ver § Datos exigidos. La fórmula se comportó como el plan la especificó; corregirla habría exigido una segunda corrida en vivo contra un servicio de terceros para regenerar un dato que ya está reportado.
- **Reportar el delta vacío como resultado, no como atenuante.** El texto de `42-WIRE-READ.md § 4` dice explícitamente que un delta vacío **no** revierte la marca de no-autoritatividad, precisamente para que un lector apurado de la Phase 43 no concluya "el baseline coincide, entonces puedo usar el baseline".
- **Diferir D42-DEF-02 en vez de arreglarlo.** Preexistente, sin pérdida de evidencia, y el fix requiere otra corrida en vivo. Se documentó con las dos vías de resolución para que la Phase 43 elija por escrito.

## Deviations from Plan

None — plan executed exactly as written. Cero deviaciones bajo las Reglas 1-3, cero escalaciones bajo la Regla 4.

**Total deviations:** 0
**Impact on plan:** Ninguno. Las tres tasks corrieron con la forma exacta especificada, incluidos los conteos de archivos por task y la prohibición de tocar `_write_schema_snapshot`.

El hallazgo D42-DEF-02 **no** es una deviación: es una condición preexistente descubierta durante la Task 2, fuera del alcance de este plan por el límite de alcance (sólo se auto-corrige lo que las tasks de esta fase causaron), y se ruteó a `deferred-items.md` como manda el procedimiento.

## Issues Encountered

**El SHAPE-diff del driver está inerte para `Instrument` y `Segment` (→ D42-DEF-02).**

Al reconciliar de dónde salían los 28 findings de disposición campo por campo, la forma de sus títulos no coincidía con la que `_emit_shape` produce (`f"{direction} field {key} en {model_name}"`). Rastreado: salen del **censo de divergencias del decode** (`verification/divergences.py:176`, la línea `DIVERGENCES=18` del SUMMARY), no del SHAPE-diff del driver.

`_emit_shape` **no corrió** para estos dos endpoints. Los probes derivan su muestra con `sample = raw[0] if isinstance(raw, list) and raw else None` (`main_market_data.py:1001` / `:1041` sync, `:1381` / `:1407` async); como `raw` es el sobre paginado (`dict`), `sample` queda en `None` y el diff se saltea en silencio. Corroborado en el ledger: hay findings con el formato de `_emit_shape` para `MarketDataSnapshot`, `Symbol` y `CalendarConfig`, y **cero** para `Instrument` o `Segment`.

**Resuelto como:** documentado en `42-WIRE-READ.md § 4.1` y en `deferred-items.md` D42-DEF-02, con el riesgo concreto nombrado para la Phase 43 — si usa `_emit_shape` como la medición del "después" del criterio 2, va a ver cero findings **haya arreglado el modelo o no**, que es un falso verde. No se arregló acá por las tres razones de § Decisions Made. La evidencia no se perdió: el censo de divergencias la produjo completa y está tabulada por FID.

## Known Stubs

Ninguno. No hay valores hardcodeados vacíos, texto placeholder ni componentes sin fuente de datos en los archivos de este plan. El único `null` del entregable (`n_rows`) es un valor **medido**, no un placeholder, y está explicado en dos artefactos.

## Threat Flags

Ninguno. Los archivos tocados no introducen superficie de seguridad fuera del `<threat_model>` del plan: no hay endpoints de red nuevos, ni rutas de auth nuevas, ni cambios de schema en fronteras de confianza. El único patrón de acceso a archivos nuevo —`capture()` escribiendo dos rutas— cae íntegramente dentro del staging gitignored que T-42-14 ya cubría, y se verificó vacío en `git status`.

## User Setup Required

None — no external service configuration required. Las credenciales Auth0 de `market-data-client` ya estaban configuradas desde la Phase 23; este plan no las modificó ni las expuso.

## Next Phase Readiness

**Listo para 42-05 y 42-06.** Este plan no bloquea ninguno: no cambió el gate de mutación (hash intacto), no tocó `main_higyrus.py` ni `scripts/literal_census_33.py`, y dejó el árbol con ruff/mypy/locks verdes.

**Lo que la Phase 43 recibe:**

- `42-WIRE-READ.md` committeado — citable sin depender del working tree de nadie, con `captured_at` de esta sesión, el `schema_of` de los dos endpoints y la marca **NO AUTORITATIVO** sobre el baseline del 2026-07-31.
- El delta vacío, que le ahorra re-medir: la descripción de `SHAPE-MD-REF-33` sigue siendo fiel al wire de hoy.
- La tabla de FIDs de la disposición campo por campo (F-205…F-218 sync, F-229…F-242 async) — insumo directo del criterio 1.
- **La advertencia de D42-DEF-02**, que es lo más accionable de este plan: el camino de medición que parece obvio para demostrar el criterio 2 (`_emit_shape`) hoy no reporta nada para estos dos modelos.

**Vigilar:** si la Phase 43 necesita los **valores** del wire (no la forma), tiene que re-correr el driver en vivo con su propia autorización humana — el crudo está en `captures/`, gitignored, y no es recuperable de git por diseño (C-4 / D-11). Y el ledger sigue creciendo con churn cosmético en cada corrida (+12 duplicados esta vez); eso se limpia en la Phase 45 (HARN-01), no antes, por la decisión de orden del milestone.

## Self-Check: PASSED

- `main_market_data.py` — FOUND
- `.planning/phases/42-…/42-WIRE-READ.md` — FOUND
- `.planning/phases/42-…/deferred-items.md` — FOUND
- `.planning/verification/captures/market-data-wire-instruments-42.json` — FOUND (gitignored, working tree)
- `.planning/verification/captures/market-data-wire-segments-42.json` — FOUND (gitignored, working tree)
- Commit `b267bea` — FOUND en `git log`
- Commit `8d584b2` — FOUND en `git log`
- Commit `cac158a` — FOUND en `git log`

---
*Phase: 42-re-chequeos-en-vivo-dns-de-higyrus-port-del-gate-de-venue-ce*
*Completed: 2026-08-31*
