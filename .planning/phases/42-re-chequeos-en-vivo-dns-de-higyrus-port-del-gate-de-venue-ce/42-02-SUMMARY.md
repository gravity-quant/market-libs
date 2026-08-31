---
phase: 42-re-chequeos-en-vivo-dns-de-higyrus-port-del-gate-de-venue-ce
plan: 02
subsystem: verification
tags: [live-verification, matriz, literal-census, bbsa, read-only, d-lock, evidence]

# Dependency graph
requires:
  - phase: 42-01
    provides: "Gate de venue portado a igualdad exacta de hostname por import (D-01), `CENSUS-HEADER`/`CENSUS-DLOCK` emitidos antes de la primera request, flag `--matriz-only` (D-04), y la aprobación humana bloqueante transcrita verbatim que habilita el tráfico en vivo"
  - phase: 33-live-typ-01
    provides: "`scripts/literal_census_33.py` con el walker `collect_paths` y `_report`, y la mitad abierta del plan 33-06 (qué valores manda el vendor en los 5 campos RESPONSE con alias `Literal`)"
provides:
  - "`42-CENSUS.md`: primera medición en vivo del vocabulario RESPONSE de `matriz-client`, con venue (`bbsa`) y timestamp UTC en el encabezado — cierra el criterio 3 de la Phase 42 y LIVE-02"
  - "Evidencia medida de que el vendor emite **8 valores fuera de los alias `Literal` declarados** (6 en `CFICode`, 2 en `OrderType`) que el stream de divergencias NO reporta — el D-lock (b) pasa de justificado por principio a justificado por medición"
  - "Confirmación empírica de que `29-DLOCK-RESPONSE-LITERAL.md:140-142` es falso: 8 valores fuera de conjunto atravesaron el decoder sin emitir un solo record"
  - "Disposición campo por campo de los 5 campos del criterio 3: 4 `MEDIDO`, 1 `NO MEDIBLE EN ESTA CORRIDA` con causa medida"
  - "Los 5 dumps crudos en `.planning/verification/captures/matriz-census-*.json` (gitignored), base de evidencia para cualquier re-lectura"
affects: [42-06, 43-shape-01, 45-harn]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Medición-no-autorización: un artefacto de censo lleva su propia negación de alcance (D-lock reafirmado + advertencia de venue + sección 'qué NO cierra') emitida en runtime por el script, no escrita a posteriori"
    - "Causa medida sobre causa supuesta: un conjunto vacío se disputa inspeccionando la forma del payload capturado (`orders` presente con longitud 0) en vez de inferirla del reporte agregado"

key-files:
  created:
    - .planning/phases/42-re-chequeos-en-vivo-dns-de-higyrus-port-del-gate-de-venue-ce/42-CENSUS.md
  modified: []

key-decisions:
  - "Los 8 valores fuera de conjunto quedan REGISTRADOS, NO APLICADOS: ampliar `CFICode`/`OrderType` es un cambio de la forma declarada de un paquete publicado, necesita disposición de semver propia, y el plan acota `files_modified` a `42-CENSUS.md` — aplicarlo habría sido el cambio de contrato sin decisión que la Phase 33 ya rechazó una vez (T-33-44)"
  - "`ordType` se reporta `NO MEDIBLE EN ESTA CORRIDA` y NO se rellena: emitir una orden para fabricar una fila habría sido una mutación, y copiar el conjunto declarado como si fuera observado habría sido evidencia fabricada"
  - "El exit code se re-midió con una segunda corrida de sólo lectura en vez de inferirse del veredicto `matriz=RAN` — el plan pide el exit code REAL, y `${PIPESTATUS[0]}` es inexistente bajo zsh"

patterns-established:
  - "Todo `<verify>` de este proyecto que necesite el exit code de un comando pipeado debe asumir zsh: `PIPESTATUS` no existe, y un `echo $?` después de un `tee` mide el `tee`"

requirements-completed: [LIVE-02]

# Metrics
duration: 4min
completed: 2026-08-31
status: complete
---

# Phase 42 Plan 02: Censo `Literal` de RESPONSE de matriz en vivo contra `bbsa` Summary

**La mitad abierta del plan 33-06 quedó medida: `matriz-client` censó 8 paths sobre 3 endpoints contra `bbsa` detrás del gate portado, con venue y timestamp en el encabezado, y el resultado es lo contrario de un conjunto prolijo — el vendor emite 6 CFI codes y 2 tipos de orden que los alias declarados no contienen, así que el D-lock (b) de la Phase 29 sale de esta fase reafirmado con una razón medida en vez de una razón de principio.**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-08-31T21:10:54Z
- **Completed:** 2026-08-31T21:14:46Z
- **Tasks:** 2 (1 de medición en vivo + 1 de artefacto committeado)
- **Files modified:** 1 creado (más 5 dumps crudos gitignored)

## El encabezado de la medición (exigido por `<output>`)

Transcripción verbatim de la línea `CENSUS-HEADER` de la corrida autoritativa:

```
CENSUS-HEADER venue=bbsa captured_at=2026-08-31T21:11:53.196947+00:00 allowlist_size=2
```

**Comando exacto ejecutado:**

```
uv run python scripts/literal_census_33.py --matriz-only
```

**Exit code de la corrida: `0`** (medido con `$?` directo sobre la invocación, no sobre `tee`).
**Veredicto final:** `CENSUS: matriz=RAN iol=NOT-REQUESTED (--matriz-only)`.

El `venue=bbsa` del encabezado no es un literal del plan: sale de `_venue_token(base)`, el mismo
objeto importado de `main_matriz.py` que decidió el gate (D-01), así que "contra qué se midió" y
"contra qué se autorizó medir" son estructuralmente lo mismo.

## Conteo de paths y disposición de los 5 campos (exigido por `<output>`)

**8 paths reportados** sobre **3 de los 5 endpoints** ejercitados:

| Endpoint | Paths | `rows` |
|---|---:|---|
| `get_segments` | 1 | 7 |
| `get_all_instruments` | 2 | 9675 cada uno |
| `get_instruments_details` | 5 | 9675 (×4) + 29380 (`orderTypes[]`) |
| `get_active_orders` | 0 | `NO TARGET FIELD PRESENT IN PAYLOAD` |
| `get_all_orders` | 0 | `NO TARGET FIELD PRESENT IN PAYLOAD` |

Disposición resumida — **cero filas sin disponer**:

| Campo | Disposición | Observados |
|---|---|---|
| `marketId` | **MEDIDO** | 1 valor (`ROFX`), sobre 3 modelos distintos que comparten la clave de wire |
| `cficode` | **MEDIDO** | **15** valores |
| `currency` | **MEDIDO** | 2 valores (`ARS`, `USD`) |
| `orderTypes` | **MEDIDO** | **6** valores |
| `ordType` | **NO MEDIBLE EN ESTA CORRIDA** | — |

### El único campo no medible, con su causa

**`ordType` — causa medida, no supuesta.** Los dos endpoints que devuelven órdenes respondieron
`status: OK` con la colección `orders` **presente y de longitud 0**: la cuenta bbsa no tenía órdenes
—ni activas ni históricas— en la ventana de la corrida. Se verificó inspeccionando la forma del
payload capturado, no infiriéndola del reporte agregado, precisamente para distinguir tres cosas que
el `NO TARGET FIELD PRESENT IN PAYLOAD` colapsa en una sola línea: colección vacía, campo ausente de
un payload poblado, y SKIP del gate. Es la primera. `PRIMARY_ACCOUNT` estaba presente y **los dos
endpoints sí se ejercitaron** — lo que faltaron fueron filas que inspeccionar.

El criterio 3 admite explícitamente esta vía. **No se rellenó con nada:** no se emitió una orden para
fabricar una fila (habría sido una mutación) ni se copió el conjunto declarado como si fuera
observado.

## Accomplishments

- **LIVE-02 medido.** La pregunta que el plan 33-06 dejó abierta desde 2026-08-27 —*qué valores manda
  el vendor*— tiene respuesta por primera vez. El gate portado en 42-01 es lo que la hizo posible: en
  HEAD anterior el script habría salteado **en silencio** contra `bbsa`.
- **Hallazgo material, y no era el esperado.** El vendor emite **8 valores fuera de los alias
  declarados**: 6 en `CFICode` (`DYXTXR`, `FXXXXX`, `MRIXXX`, `OCEFXS`, `OPEFXS`, `RPXXXX` — 15
  observados contra 9 declarados) y 2 en `OrderType` (`MARKET_TO_LIMIT`, `PREVIOUSLY_QUOTED` — 6
  contra 4). Ninguno de los conjuntos declarados tuvo miembros no observados. `MarketId` y `Currency`
  coincidieron exactamente.
- **El D-lock (b) sale reforzado, no erosionado.** El riesgo que el lock previene dejó de ser
  hipotético: si `CFICode` y `OrderType` hubieran estado cerrados con enforcement, **una sola corrida
  de lectura habría fallado sobre 9675 instrumentos**. El artefacto declara el lock EN VIGOR y
  explicita que no lo revoca; el script además lo emite en runtime (`CENSUS-DLOCK`) antes de la
  primera request, para que la declaración no dependa de que alguien la escriba después.
- **`29-DLOCK-RESPONSE-LITERAL.md:140-142` confirmado falso, empíricamente.** Los 8 valores fuera de
  conjunto atravesaron el decoder **sin emitir un solo record de divergencia**, porque la rama
  `Literal` de `walk_field` retorna temprano con `literal_enforced=False` (`_decode.py:540-549`,
  `POLICY` en `:140`). El comentario in-code ya lo anticipaba —*"vendor enum growth must not be
  fatal"*— y esta corrida es la primera vez que ese crecimiento queda medido. La corrección del
  párrafo firmado queda **ruteada al firmante y fuera de alcance**, nombrada en § 7 del artefacto.
- **Criterio 4 intacto.** `verification/mutation_gate.py` sigue en
  `6bdaec006cc16f7c8dbfac41701712a9085c691b`, medido antes y después de la corrida. Cero órdenes,
  cero mutaciones, `VERIFY_MUTATING` sin setear, y sin barrido de 4xx (D-10 / P-05).
- **D-04 respetado.** `census_iol()` no corrió: el log no contiene ninguna línea `iol-client `. El
  veredicto de iol se reporta `NOT-REQUESTED`, que no es lo mismo que `SKIPPED`.
- **Frontera de datos respetada (T-42-05).** El artefacto committeado no contiene payload crudo, ni
  URL de vendor (`grep -c 'https://'` = 0, `grep -c 'matrizoms\|primary\.com\.ar'` = 0), ni
  identificador de cuenta. `PRIMARY_ACCOUNT` aparece una vez **como nombre de variable, sin valor**.
  Los 11,6 MB de payload crudo viven sólo en `.planning/verification/captures/` (gitignored).

## Task Commits

1. **Task 1: Corrida en vivo del censo de matriz contra bbsa (`--matriz-only`, D-04)** — **sin
   commit, por diseño**. Todos los `<files>` de la task son gitignored (`.gitignore:53`): los 5
   dumps `matriz-census-*.json` y el log en `/tmp`. `git status --porcelain` quedó **vacío** al
   terminar la task y ningún `.py` cambió — que es exactamente lo que su `<acceptance_criteria>`
   exige. Mismo patrón que la Task 3 del plan 42-01.
2. **Task 2: `42-CENSUS.md` — inventario committeado con venue, timestamp y D-lock reafirmado** —
   `30898ff` (docs), 210 líneas, un solo archivo.

## Verificación del plan — resultados medidos

| # | Chequeo | Resultado |
|---|---------|-----------|
| 1 | Checkpoint de 42-01 aprobado y transcrito verbatim | Sí — `42-01-SUMMARY.md:99` → `Approved` (verificado **antes** de la primera llamada de red) |
| 2 | `CENSUS-HEADER venue=bbsa captured_at=<hoy>` + `CENSUS-DLOCK` en el log, cero líneas `iol-client ` | PASS (`<verify>` de la Task 1, exit `0`) |
| 3 | `42-CENSUS.md` con los 5 campos dispuestos, D-lock (b) y advertencia de venue | PASS (`<verify>` de la Task 2, exit `0`) |
| 4 | `git hash-object verification/mutation_gate.py` | `6bdaec006cc16f7c8dbfac41701712a9085c691b` — byte-idéntico |
| 5 | `git status --porcelain .planning/milestones/` + `pytest verification/test_cycle_closure_phase33.py` | Vacío · **21 passed** en 0.08s |
| 6 | `git status --porcelain .planning/verification/captures/` | Vacío (gitignored), y los **5** `matriz-census-*.json` existen en disco |
| 7 | Mutaciones / órdenes emitidas | **Cero** |
| 8 | Líneas del artefacto vs. `min_lines: 60` | **210** |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] El exit code de la corrida no era medible con la invocación del plan**

- **Found during:** Task 1
- **Issue:** El `<action>` especifica `… | tee /tmp/42-census-run.log` y "registrar el exit code
  **real** de la corrida (no el de `tee`)". El shell de esta sesión es **zsh**, donde `PIPESTATUS`
  no existe (zsh usa `$pipestatus`, minúscula y 1-indexado), así que `${PIPESTATUS[0]}` expandió a
  vacío. Inferir `0` del veredicto `matriz=RAN` habría sido derivar del código fuente un valor que
  el plan pide **medir**.
- **Fix:** Se preservó el log de la primera corrida como `/tmp/42-census-run.attempt1.log` y se
  re-corrió el censo con redirección directa (`> log 2>&1; echo $?`), obteniendo el exit code
  medido `0`. El log autoritativo y su exit code provienen ahora de **la misma corrida**, que es la
  condición que hace transcribible el encabezado.
- **Costo:** una segunda pasada de sólo lectura sobre los mismos 5 endpoints GET. Dentro del
  alcance autorizado (cero mutaciones, cero órdenes, sin barrido de 4xx); no se tocó el allowlist,
  ni `PRIMARY_BASE_URL`, ni el gate.
- **Beneficio colateral no buscado:** las dos corridas salieron **idénticas salvo `captured_at`** —
  mismos 8 paths, mismos `rows`, mismos `distinct`. Es evidencia de estabilidad del catálogo en la
  ventana, que una sola corrida no habría dado.
- **Files modified:** ninguno (ambas corridas escriben sólo a `/tmp` y a `captures/` gitignored).
- **Commit:** ninguno (Task 1 no commitea, por diseño).

**Total deviations:** 1 (Regla 3). Cero escalaciones bajo la Regla 4.
**Impact on plan:** Ninguno sobre el alcance ni sobre los artefactos. La `<verify>` de la Task 1
pasó sobre el log de la corrida autoritativa.

### Decisión deliberada de NO desviarse

Los 8 valores fuera de conjunto de la § 4.1 son un hallazgo real y tentador de arreglar en el
mismo ciclo. **No se aplicó ningún cambio a `types.py`.** Razones, en orden:

1. Ampliar `CFICode`/`OrderType` es un cambio de la **forma declarada de un paquete publicado** —
   la misma clase de cambio que el checkpoint bloqueante de 33-07 existe para gobernar, y que
   `SHAPE-MD-REF-33` dejó explícitamente esperando una disposición de semver.
2. No es una Regla 1/2: no hay bug ni falta de funcionalidad crítica. Con
   `literal_enforced=False` + `scalar_passthrough=True`, un valor fuera de conjunto se devuelve
   **byte por byte sin tocar**; nada se rompe hoy.
3. El `files_modified` del plan es exactamente un archivo. Un censo que además muta la superficie
   que está midiendo deja de ser una medición.

Queda registrado en § 4.1 y ruteado en § 8 del artefacto.

## Issues Encountered

Ninguno del lado del vendor: los cinco endpoints respondieron `status: OK`, sin timeouts, sin
rate limits y sin errores de auth. El gate **pasó** (no salteó), así que no hubo que escalar por
ampliación de allowlist.

## Known Stubs

Ninguno. El artefacto no contiene placeholders, TODOs ni filas sin disponer — la ausencia de datos
de `ordType` está **dispuesta explícitamente** con su causa medida, que es lo contrario de un stub.

## Threat Flags

Ninguno. Este plan no introdujo superficie de seguridad nueva: cero archivos de fuente modificados,
cero endpoints nuevos, cero rutas de auth nuevas, cero cambios de schema. Los tres cruces de
frontera del `<threat_model>` se comportaron como estaba previsto — el gate de venue decidió
(T-42-01), el gate de mutación quedó byte-idéntico (T-42-02), y la frontera crudo/committeado se
respetó en las dos direcciones (T-42-05 / T-42-04).

## Next Phase Readiness

**Listo para 42-06 (gate de cierre) y para la Phase 43.**

- El criterio 3 de la Phase 42 queda **satisfecho y auditable**: `42-CENSUS.md` lleva venue y
  timestamp medidos, disposición completa de los 5 campos, y las tres secciones de contención
  (D-lock, alcance de venue, qué NO cierra).
- **Vigilar en 42-06:** `verification/mutation_gate.py` debe seguir en `6bdaec00…` al cierre de la
  fase; esta corrida lo dejó intacto.
- **Insumo para la Phase 43 (SHAPE-01):** los 8 valores fuera de conjunto son un ítem de disposición
  de forma, no de esta fase. Si la Phase 43 abre `types.py` de matriz, esa es la ventana natural
  para decidir *ampliar vs. aceptar* con presupuesto declarado — nunca como efecto lateral.
- **Sigue abierto de `LIVE-MATZ-33`:** S-3/S-4/S-5 y el piso `≥24` de `29-SIZING.md` (equivalente en
  triples distintos: 14). Este censo cuenta **valores de vocabulario**, no triples de divergencia:
  son unidades distintas y no se restan entre sí. Nadie debe leer "criterio 3 cumplido" como
  "`LIVE-MATZ-33` cerrado" — el artefacto lo dice en su § 8.
- **Sigue sin medir:** `ordType`, hasta una corrida con órdenes en la cuenta.

## Self-Check: PASSED

- `.planning/phases/42-…/42-CENSUS.md` — FOUND (210 líneas)
- `.planning/verification/captures/matriz-census-get_segments.json` — FOUND
- `.planning/verification/captures/matriz-census-get_all_instruments.json` — FOUND
- `.planning/verification/captures/matriz-census-get_instruments_details.json` — FOUND
- `.planning/verification/captures/matriz-census-get_active_orders.json` — FOUND
- `.planning/verification/captures/matriz-census-get_all_orders.json` — FOUND
- Commit `30898ff` — FOUND en `git log`

---
*Phase: 42-re-chequeos-en-vivo-dns-de-higyrus-port-del-gate-de-venue-ce*
*Completed: 2026-08-31*
