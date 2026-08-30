---
phase: 38-iol-client-auditor-a-de-higyrus-mbito-wallets
plan: 04
subsystem: docs
tags: [audit, census, null-object, nobj-aud-01, evidence, ast-introspection, phase-39-handoff]

# Dependency graph
requires:
  - phase: 38-iol-client-auditor-a-de-higyrus-mbito-wallets
    plan: "02"
    provides: "El gate ensanchado cuya línea de resumen ejecutada es la evidencia que cita cada celda de disposición del censo, y el grep de cierre SC-3 ya en 10 líneas"
  - phase: 38-iol-client-auditor-a-de-higyrus-mbito-wallets
    plan: "03"
    provides: "El `## Phase 38 addendum` en `35-RETIRED-TRIPLES.md` que el censo referencia para la contabilidad de triples retiradas en vez de duplicarla, y el puntero adelantado a `38-CENSUS.md` que este plan cierra desde el otro lado"
  - phase: 35-null-object-nobj
    provides: "`35-RETIRED-TRIPLES.md` como plantilla de forma D-07 y como fuente citada de la ausencia enumerada de ámbito/wallets"
provides:
  - "`38-CENSUS.md` — el censo NOBJ-AUD-01 con disposición en cada fila: 142 campos de higyrus en 15 clases, 11 filas por-campo + 16 agregados por-clase, más la mitad de retornos públicos en ambas superficies"
  - "Los dos ceros declarados por enumeración con su causa nombrada, y la condición de stub de wallets registrada explícitamente (SC-4)"
  - "La evidencia de cierre SC-3 como comando ejecutado con su salida verbatim — 10 líneas, todas hojas de alias `Literal` de matriz"
  - "Cuatro discrepancias contra artefactos previos nombradas y resueltas hacia el número medido, no absorbidas"
  - "El cruce asimétrico cerrado: el censo cita el addendum de Phase 38 para la aritmética de triples en vez de restatarla"
affects: [39-verificacion-en-vivo-encadenamiento-profundo, 40-bump-breaking-coordinado]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Censo por transcripción de corrida, no por lectura de fuente: cada celda de disposición cita la línea de resumen del gate ejecutado, y el gate se corre además scopeado a un solo paquete (semilla D-04) para obtener el conteo por-paquete que hace real el cross-check"
    - "Introspección de una sola vez con `ast` de stdlib sobre el archivo, nunca importando el paquete — importar corre `load_dotenv()` y construye un cliente HTTP; misma disciplina que el gate se impone a sí mismo"
    - "Clasificación AST de los hits de un grep por su `ClassDef`/`FunctionDef` contenedor, para separar campo real de variable local — el patrón de indentación no puede distinguirlos y un transcript sin separar sobre-reporta"
    - "Cero por enumeración como categoría de reporte distinta de cero por limpieza, con la población vacía y su causa nombradas en el mismo párrafo"

key-files:
  created:
    - .planning/phases/38-iol-client-auditor-a-de-higyrus-mbito-wallets/38-CENSUS.md
  modified: []

key-decisions:
  - "El paquete de ámbito/wallets se cita en `35-RETIRED-TRIPLES.md:169-180`, no en el `:184-197` que manda el propio plan — 184 es el heading `## How Phase 39 should use this`; la cita ya estaba stale cuando se escribió (pre-38-03 el párrafo arrancaba en 161)"
  - "Las anotaciones con unión PEP-604 se sacaron de las celdas de tabla y se pusieron en un bloque de código verbatim: un `|` dentro de una celda rompe el conteo de columnas del `awk` de verificación del propio plan"
  - "Se agregó una 11ª fila por-campo para `Movimiento.idMovimientos: list[int]` y una 12ª que declara el cero de campos mapping — sin ellas el único candidato de colección tipada y la categoría mapping caían silenciosamente en el agregado escalar"
  - "El cross-check contra `fields scanned` se hizo scopeando el gate a un solo paquete en vez de comparar 142 contra el total workspace de 442, que no habría sido un cross-check"

patterns-established:
  - "Tabla de discrepancias como sección propia: cada fila lleva qué dice el artefacto previo, qué se midió, qué escribe el censo y el comando que lo zanja"

requirements-completed: [NOBJ-AUD-01]

# Metrics
duration: 8min
completed: 2026-08-29
status: complete
---

# Phase 38 Plan 04: `38-CENSUS.md` — el censo NOBJ-AUD-01 de higyrus/ámbito/wallets — Summary

**Los tres paquetes miden `0` violaciones, que es exactamente la situación en la que un reporte tiene más chance de no valer nada: el censo enumera la población candidata completa —142 campos de higyrus en 15 clases, cada uno con disposición— y los dos ceros que vienen de no tener modelos se reportan como cero por enumeración con la causa nombrada, nunca como limpieza.**

## Performance

- **Duration:** 8 min
- **Started:** 2026-08-29T21:01:14Z
- **Completed:** 2026-08-29T21:09:29Z
- **Tasks:** 2 (1 read-only sin commit, 1 con commit)
- **Files created:** 1

## Accomplishments

- **El cross-check de los 142 campos es real, no una comparación contra un total.** Se corrió `scan_surface_types(root)` con un root que contiene sólo `packages/higyrus-client` (la semilla inyectable D-04 de Phase 32): el contador propio del gate reporta `fields = 142` para higyrus solo. El inventario `ast` independiente suma **142** en **15** clases portadoras de campos. Los dos números coinciden exacto — no hubo desacuerdo que reportar. Comparar 142 contra el `442 fields scanned` del workspace no habría sido un cross-check.
- **El grep de cierre SC-3 devuelve 10 líneas, todas matriz**, pegadas verbatim en el censo con su comando literal. Cero hits en higyrus, ámbito o wallets. Las 8 aliases involucradas (`MarketId`, `SegmentId`, `CFICode`, `Currency`, `OrderType`, `Side`, `TimeInForce`, `OrderStatus`) son hojas de conjunto escalar permitidas por D-NO-03.
- **El grep de mapping sobre-reporta por 6, y el censo lo separa en vez de transcribirlo crudo.** Los 11 hits se clasificaron por AST resolviendo el `ClassDef`/`FunctionDef` contenedor de cada línea: 3 campos con parámetro de valor tipado, 1 `ClassVar` dunder, 1 exención declarada (`UnknownFrame.raw`), y **6 que no son campos** — 4 variables locales dentro de `to_dict` y 2 dentro de las funciones module-level `_mapping_value` / `_apply_mapping_policy` de matriz. Ninguno de los 11 es un campo mapping en los tres paquetes auditados.
- **La segunda mitad de SC-3 quedó verificada por enumeración de retornos, no por afirmación:** ningún retorno público de los tres paquetes expone `dict[str, Any]` ni `list[dict[str, Any]]`. El único retorno con un brazo de mapping sin tipar es `_request` de higyrus (`dict[str, Any] | list[Any] | None`, ambas superficies), y está **fuera del conjunto de candidatos del gate** — ausente de todo `__all__`.
- **Los seis `_request` module-level se registran como inalcanzables, no como exentos.** Es la corrección de RESEARCH F-9 a CONTEXT D-09: la taxonomía real del gate tiene cuatro razones (`dunder 13, private-helper 1, serialize-out 9, ws-catch-all 1`) y ningún bucket `×2` para shims `_request`; el único `private-helper` es un **método** de matriz. Confundir inalcanzable con exento sobre-declara cuánto adjudicó el gate.
- **La condición de stub de wallets quedó escrita, no insinuada:** `__all__` (`__init__.py:22-28`) con 4 excepciones y `configure` y ni una función de dominio; exención de decoder de Phase 29 con su path resuelto (`.planning/milestones/v1.6-phases/29-decoder-observable/29-WALLETS-EXEMPTION.md`); sin `_decode.py`; y los 10 tests que pasan ejercitan plumbing de config y excepciones únicamente. El scan por-paquete lo confirma desde el otro lado: `definitions = 2`, `fields = 0`, `exempted = 0`.
- **Ningún ledger auto-generado se tocó.** `git status --porcelain .planning/verification/` vacío después del commit (D-07), y el diff del commit nombra exactamente un archivo.

## Task Commits

1. **Task 1: captura de evidencia medida (dos greps, resumen del gate, inventario de campos de higyrus, inventario de retornos públicos, cuatro baselines de suite)** — sin commit propio (read-only; no produce cambio de archivo, como registra la tabla de reversibilidad del plan)
2. **Task 2: escritura de `38-CENSUS.md`** — `decc002` (docs)

## Files Created/Modified

- `.planning/phases/38-iol-client-auditor-a-de-higyrus-mbito-wallets/38-CENSUS.md` — **426 líneas**, nuevo. Sigue la forma D-07 de `35-RETIRED-TRIPLES.md` con sus cuatro elementos estructurales copiados: tabla principal donde cada fila lleva columna de disposición, párrafo de procedencia "no number in this file is an estimate", ceros declarados bajo sub-headings en negrita en vez de por silencio, y sección de cierre "how Phase 39 should use this" que nombra el modo de falla que el artefacto previene. Secciones: alcance (con la tabla de los tres paquetes auditados en otra parte, para que la omisión no se lea como hueco), la corrida del gate que citan todas las disposiciones más la tabla por-paquete, tabla principal A (11 filas por-campo de links y colecciones), tabla principal B (16 agregados por-clase de hojas escalares) con la aritmética `10 + 1 + 131 = 142` escrita, la mitad de retornos públicos (21 filas, ambas superficies), la tabla de exentos citados y la de fuera-del-conjunto-de-candidatos, los dos ceros enumerados, la evidencia SC-3 con ambos greps y su salida, la tabla de cuatro discrepancias, método y límites, y la sección de handoff a Phase 39.

## Decisions Made

- **La cita de `35-RETIRED-TRIPLES.md` se escribió `:169-180`, no el `:184-197` que manda el plan.** Ver Deviations — es el único punto donde este plan se aparta de su propia instrucción, y apartarse era la única lectura consistente con el criterio de verdad del plan ("Where any number you measure disagrees with a number in CONTEXT.md, record BOTH and name the discrepancy").
- **Las uniones PEP-604 se sacaron de toda celda de tabla.** El criterio de aceptación del plan verifica el conteo de columnas con `awk -F'|'`, que parte por el carácter `|` sin importar el escape markdown: una celda con `dict[str, Any] | list[Any] | None` habría inflado `NF` para esa fila y roto la uniformidad que el criterio exige. Las dos firmas de `_request` se pusieron en un bloque de código verbatim inmediatamente debajo de la tabla, que es además más fiel que una celda. Distribución de `NF` resultante: 4 valores distintos (`5`, `6`, `7`, `9`), uno por forma de tabla (3, 4, 5 y 7 columnas), sin filas irregulares.
- **Se agregaron dos filas que el plan no enumera explícitamente**: `Movimiento.idMovimientos: list[int]` como candidato de colección tipada, y una fila que declara el cero de campos mapping de higyrus como medición. Sin la primera, el único `list[...]` no-de-modelo del paquete habría caído en el agregado "escalar" sin decirlo; sin la segunda, la categoría mapping habría desaparecido de la tabla por omisión — exactamente la forma de silencio que D-08 prohíbe. La aritmética sigue cerrando en 142.
- **El cross-check se hizo scopeando el gate por paquete.** El plan pide comparar la suma por-clase contra "the gate's own `fields scanned` figure", que es un total de 6 paquetes. Se usó la semilla `REPO_ROOT` inyectable con un root de un solo paquete para obtener la cifra comparable, y se registraron también las cifras de ámbito (`fields = 0`, `exempted = 4`, todos `dunder`) y wallets (`fields = 0`, `exempted = 0`) — que son la confirmación del cero desde el lado del gate, no desde el docstring.
- **La disposición D-NO-03 se cita en cada fila escalar pero se dice explícitamente que no es load-bearing acá.** El scan reporta `optional-bearing fields: []`: ni un campo de higyrus lleva brazo opcional en ninguna de las tres grafías legales. Citar la política sin esa aclaración habría sugerido que el paquete se apoya en una excepción que no usa.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] La cita `35-RETIRED-TRIPLES.md:184-197` está stale**

- **Found during:** Task 2, al leer el archivo para copiar la forma D-07 (que el `read_first` del propio plan ordena: "Read it in full")
- **Issue:** El plan (acción de Task 2, punto 4) y RESEARCH F-8 (`38-RESEARCH.md:461`) mandan citar `35-RETIRED-TRIPLES.md` **lines 184-197** para el párrafo de ausencia enumerada de ámbito/wallets. Contra HEAD, la línea **184** es el heading `## How Phase 39 should use this` y el rango 184-197 cae íntegro dentro de la sección de mecánica de Phase 39 — no menciona ámbito ni wallets. El párrafo real, que arranca con `**`ambito-financiero-client` and `wallets-client` — absent by enumeration, not by cleanliness.**`, está en **169-180**. Verificado además que la cita ya era incorrecta antes de esta fase: en `fd809fb^` (pre-38-03) el párrafo arrancaba en la línea **161**, así que el `184` nunca resolvió.
- **Fix:** Se escribió `169-180`, verificado leyendo el archivo con números de línea antes de escribir. Se registró además como fila 3 de la tabla de discrepancias del censo, con el comando que lo zanja. Escribir `184-197` habría metido en un artefacto de auditoría exactamente el defecto que el plan 38-03 de esta misma fase existe para arreglar — un ledger citando líneas que no resuelven — y habría violado el `must_haves.truth` de este plan ("No number in the census is an estimate: each is quoted from a cited artifact line").
- **Files modified:** `.planning/phases/38-iol-client-auditor-a-de-higyrus-mbito-wallets/38-CENSUS.md`
- **Commit:** `decc002`

**2. [Rule 1 - Bug] La cita `packages/iol-client/README.md:150-161` está stale**

- **Issue:** CONTEXT D-09 (`38-CONTEXT.md:103`) y el `read_first` de Task 2 ("around lines 150-165") ubican ahí el escape hatch documentado de `to_dict()`. Contra HEAD la sección `**Escape hatch: `to_dict()`**` está en **189-199**: el plan 38-03 insertó el callout `## Unreleased — BREAKING` en la línea 5 del README, corriendo 39 líneas hacia abajo todo lo que estaba debajo.
- **Fix:** El censo cita `packages/iol-client/README.md:189-199` y registra la discrepancia como fila 4 de su tabla de discrepancias. Misma clase de defecto que la anterior: una referencia de línea medida en un HEAD y citada en otro.
- **Files modified:** `.planning/phases/38-iol-client-auditor-a-de-higyrus-mbito-wallets/38-CENSUS.md`
- **Commit:** `decc002`

### Discrepancias que el plan ya anticipaba (registradas, no arregladas — son de artefactos previos)

Las dos que RESEARCH ya había encontrado se escribieron en la tabla de discrepancias del censo con el número medido y el comando:

- **CONTEXT D-11 dice 11 hojas `Literal` de matriz; el grep y el scan AST cuentan 10.** El propio D-11 (`38-CONTEXT.md:128`) lista exactamente 10 números de línea a continuación de la palabra "11". El censo escribe **10** con la salida del grep pegada.
- **CONTEXT D-09 describe la taxonomía como "`to_dict()` serialize-out ×9, shims legacy `_request` ×2".** La taxonomía real de la corrida tiene cuatro razones y ningún bucket para `_request`. El censo reproduce la línea verbatim y explica que los `_request` module-level están fuera del conjunto de candidatos.

Fuera de esos cuatro puntos de referencia, el plan se ejecutó tal como está escrito. Todos los criterios numéricos salieron exactos sin ajuste.

## Issues Encountered

Uno de forma, resuelto en el momento: la primera escritura dejó **un espacio en blanco al final de la línea 326** (una celda de tabla). El hook de pre-commit `trailing-whitespace` lo habría enrojecido. Se detectó con `grep -nP '[ \t]+$'` antes de stagear y se corrigió; el commit pasó los hooks sin `--no-verify`.

Ninguno bloqueante. Ninguna corrida tuvo que repetirse por resultado inesperado.

## Verification Results

### Task 1 — criterios de aceptación

| Check | Comando | Resultado |
|---|---|---|
| Grep opcional SC-3 = 10, todas matriz | grep de F-9 sobre `packages/*/src/*/models.py` | `10` líneas, todas `matriz_client/models.py` en 532/552/553/561/607/619/660/661/662/669 |
| Gate exit 0, taxonomía y cotas exactas | `uv run python tools/check_surface_types.py` | exit `0` — `442 fields scanned`, `24 exempted (dunder 13, private-helper 1, serialize-out 9, ws-catch-all 1)`, `0 violations` |
| Cero clases en los dos `models.py` vacíos | `grep -c '^class '` | `0` y `0` |
| ~27 líneas cada uno | `wc -l` | `27` y `27` |
| Tokens `class` en prosa de ámbito | `grep -n 'class'` | 2 hits (líneas 11 y 16), ambos prosa; wallets: **cero hits** |
| Inventario higyrus: 142 campos / 15 clases / 0 opcionales / 0 mappings | snippet `ast` de stdlib | `TOTAL fields: 142`, `field-carrying classes: 15`, `optional-bearing fields: []`, `mapping fields: []` |
| Consistencia con la cifra propia del gate | `scan_surface_types` scopeado a higyrus | `fields = 142` — **coincidencia exacta** |
| Suite iol | `pytest packages/iol-client -q` | `292 passed` |
| Suite higyrus | `pytest packages/higyrus-client -q` | `289 passed` |
| Suite ámbito | `pytest packages/ambito-financiero-client -q` | `208 passed, 1 deselected` |
| Suite wallets | `pytest packages/wallets-client -q` | `10 passed` |
| Inventario por `ast`, no por import | snippet en scratchpad fuera del repo | ningún `import higyrus_client`, ningún `get_type_hints`, ningún `.env` leído |
| Task 1 no escribe nada | `git status --porcelain` | vacío |

### Task 2 — criterios de aceptación

| Check | Comando | Resultado |
|---|---|---|
| Existe y ≥ 80 líneas | `wc -l 38-CENSUS.md` | `426` |
| Forma de columnas uniforme por tabla | `awk -F'\|' '/^\|/ && !/^\|[- :]*\|/ {print NF}' \| sort \| uniq -c` | `9×NF=5`, `5×NF=6`, `17×NF=7`, `56×NF=9` — 4 formas de tabla, ninguna fila irregular |
| Ninguna celda vacía | `grep -nE '\|\s*\|'` | sin coincidencias |
| `zero by enumeration` ≥ 2 | `grep -c` | `4` |
| `out of the gate` ≥ 1 | `grep -c` | `2` |
| `29-WALLETS-EXEMPTION.md` ≥ 1 | `grep -c` | `1` |
| `35-RETIRED-TRIPLES.md` ≥ 2 | `grep -c` | `6` |
| Taxonomía verbatim | `grep -c '24 exempted (dunder 13, private-helper 1, serialize-out 9, ws-catch-all 1)'` | `1` |
| `0 violations` presente | `grep -c` | `33` (una por celda de evidencia, más la línea de resumen) |
| Ledgers auto-generados intactos (D-07) | `git status --porcelain .planning/verification/` | vacío |
| Los tres gates siguen en verde | `check_surface_types` + `check_decode_intactness` + `check_uniform_structure` | los tres exit `0` |
| Sin trailing whitespace | `grep -nP '[ \t]+$'` | sin coincidencias |

### Whole-plan checks

| # | Check | Resultado |
|---|---|---|
| 1 | Archivo existe con ≥ 80 líneas | `426` |
| 2 | Cada fila con disposición y evidencia | pendiente de cosecha en `38-UAT.md` (`human_verify_mode = end-of-phase`); el `<human-check>` del plan queda para el verificador |
| 3 | Ambos greps SC-3 presentes como comando literal + salida; el opcional muestra 10, todas matriz | ✔ |
| 4 | Gate en `0 violations`, taxonomía sin cambio | ✔ |
| 5 | `git status --porcelain .planning/verification/` vacío | ✔ |
| 6 | `git diff --name-only HEAD~..HEAD` nombra sólo `38-CENSUS.md` | ✔ |

Chequeo adicional de borrados: `git diff --diff-filter=D --name-only HEAD~1 HEAD` no devuelve nada — el commit es puramente aditivo.

## Threat Mitigations Verified

| Threat ID | Verificación |
|---|---|
| T-38-15 (Repudiation / el censo como registro de auditoría) | Cada disposición cita la línea de resumen del gate ejecutado; los dos greps están en el archivo como comando literal seguido de su salida pegada, no como afirmación; el párrafo de procedencia nombra las cuatro corridas (gate + 3 invocaciones por-paquete, los dos greps, las cuatro suites, el inventario `ast`). Ningún número es una estimación. |
| T-38-16 (Repudiation / el verde vacuo) | El censo enumera los 142 campos, no las 0 violaciones: 11 filas por-campo + 16 agregados por-clase + 21 filas de retorno público. Los dos ceros llevan sub-heading propio con la palabra "zero by enumeration" y su causa medida (0 clases, 27 líneas de docstring). El verde de wallets sale con las tres partes de su calificación de stub. |
| T-38-17 (Tampering / ledgers auto-generados) | `git status --porcelain .planning/verification/` vacío después del commit; el diff del commit nombra exactamente un archivo, bajo el directorio de esta fase. |
| T-38-18 (Info Disclosure / credenciales en `.env`, ASVS V14) | El inventario se produjo con `ast` de stdlib sobre el archivo, nunca importando el paquete. El snippet vivió en el scratchpad de sesión fuera del repo y no se commiteó (`git status --porcelain` vacío antes y después). Ningún valor de credencial aparece en el censo. |
| T-38-19 (Tampering / conteos sin fuente propagados) | Cuatro discrepancias nombradas en una tabla propia con el número medido y el comando que lo zanja: 10-vs-11 de matriz, la taxonomía de D-09, y las dos citas de línea stale (`35-RETIRED-TRIPLES.md` y el README de iol). Ninguna se absorbió en silencio. |
| T-38-SC (supply chain) | Aceptado. Cero instalaciones de paquetes, cero tooling commiteado, `uv.lock` sin tocar. |

## Known Stubs

Ninguno en el artefacto. El censo describe un paquete que **es** un stub (`wallets-client`), y esa condición está registrada explícitamente como el hallazgo que SC-4 exige, no como una omisión.

El snippet `ast` de introspección es deliberadamente descartable y no commiteado, tal como manda la tabla "Artifacts this phase produces" del plan: este repo ya tiene tres gates en `tools/` y no necesita un cuarto para un conteo de una sola vez. No es un stub — es una decisión declarada.

## Threat Flags

Ninguna superficie nueva. Este plan creó un archivo markdown y corrió comandos read-only: cero cambios de código, cero endpoints, cero caminos de auth, cero dependencias movidas, cero llamadas de red.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **Phase 38 queda completa**: los cuatro planes ejecutados, NOBJ-IOL-01 (38-01/38-03) y NOBJ-AUD-01 (38-02/38-04) cerrados. El `<human-check>` de este plan queda pendiente de cosecha en `38-UAT.md` por el verificador, según `workflow.human_verify_mode = end-of-phase`.
- **Phase 39** tiene ahora sus dos insumos y el cruce cerrado en ambas direcciones: `38-CENSUS.md` da la **población de partida** estática (higyrus 142 campos / 15 clases / 10 links / 0 opcionales; ámbito 0; wallets 0 por enumeración) y `35-RETIRED-TRIPLES.md ## Phase 38 addendum` da el **término medio** de la resta (2 filas agregadas, 0 triples retiradas, middle term sin mover). El censo advierte explícitamente que un cero vivo de ámbito o wallets no confirma nada.
- **Phase 40** sigue siendo dueña del bump: este plan no tocó `pyproject.toml`, `__version__` ni `uv.lock`.
- Sin blockers.

## Self-Check: PASSED

- `.planning/phases/38-iol-client-auditor-a-de-higyrus-mbito-wallets/38-CENSUS.md` verificado en disco: `426` líneas.
- Commit `decc002` verificado con `git log --oneline` y su scope confirmado con `git diff --name-only HEAD~..HEAD` (un solo archivo).
- Los 10 números de línea de matriz, los 142 campos, las 15 clases y los cuatro conteos de suite re-verificados ejecutando los comandos, no transcritos de RESEARCH ni de CONTEXT.
- Las cuatro citas de línea que el censo escribe (`35-RETIRED-TRIPLES.md:169-180`, `iol-client/README.md:189-199`, `wallets_client/__init__.py:22-28`, `tools/check_surface_types.py:304-313`) verificadas leyendo cada archivo fuente.

---
*Phase: 38-iol-client-auditor-a-de-higyrus-mbito-wallets*
*Completed: 2026-08-29*
