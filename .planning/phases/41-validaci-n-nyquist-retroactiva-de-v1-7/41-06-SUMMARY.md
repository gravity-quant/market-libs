---
phase: 41-validaci-n-nyquist-retroactiva-de-v1-7
plan: 06
subsystem: testing
tags: [nyquist-audit, validation, pytest, retroactive-audit, ci-enforcement, not-verifiable-retroactively]

# Dependency graph
requires:
  - phase: 41-01
    provides: "41-AUDIT-CONTRACT.md — denominador 62, claves ordinales, reglas R-01..R-09, forma de sección, mapa de enforcement de CI, resolución escrita de OQ#1"
  - phase: 39-verificaci-n-en-vivo-del-encadenamiento-profundo
    provides: "39-VALIDATION.md (11 filas de mapa + 4 manual-only), 39-CENSUS.md, 39-VERIFICATION.md, los 4 envelopes de run-evidence, las 7 suites de verification/ y su enrolamiento en CI (fix WR-01)"
provides:
  - "Sección `## Validation Audit 2026-08-31` en `39-VALIDATION.md` con 15 disposiciones (10 VERIFIED-NOW / 1 VERIFIED-HISTORICALLY / 4 NOT-VERIFIABLE-RETROACTIVELY)"
  - "El marcador del criterio 3b: `not_verifiable_retroactively: 4` en front-matter — la única de las cinco fases auditadas con valor distinto de cero"
  - "La segunda y última corrección R-02 de la Phase 41 (`39-r03`), con ambos comandos transcritos y el cuerpo de los tres locks sustitutos resumido"
  - "Hallazgo transversal de enforcement cuantificado: 52 locks de verification/, 12 enrolados, 40 sin correr en CI — ruteado por escrito a la Phase 45"
  - "Cuarta fila de bookkeeping no anticipada por el plan: el node-id de `39-r08` nombra un helper privado, no un test (exit 4, no exit 5)"
affects: [41-07, 45]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Disposición retroactiva de 3 vías contra árbol congelado, con evidencia por fila y cero tráfico de red"
    - "Sub-declaración deliberada en auditoría: ante duda entre VERIFIED-HISTORICALLY y NOT-VERIFIABLE-RETROACTIVELY, gana el segundo"

key-files:
  created: []
  modified:
    - ".planning/milestones/v1.7-phases/39-verificaci-n-en-vivo-del-encadenamiento-profundo/39-VALIDATION.md"

key-decisions:
  - "Las 4 filas manual-only de la Phase 39 quedan NOT-VERIFIABLE-RETROACTIVELY (R-07), contra la recomendación de 41-RESEARCH.md de partir el bloque 3/1: D-04 las nombra por su nombre como el arquetipo del marcador, y en auditoría la dirección segura es sub-declarar. La evidencia parcial (4 envelopes fechados, 39-07-SUMMARY.md, dos secciones de 39-CENSUS.md, el sign-off del operador) queda nombrada en cada celda con su límite explicado."
  - "El node-id `::_ambito_declares_zero_models` de la fila 39-r08 NO consume una tercera corrección R-02: R-02 se dispara con selector `-k` que colecciona 0 tests y exit 5; acá el node-id nombra un helper privado y pytest sale exit 4 (error de uso). La fila se dispone VERIFIED-NOW plano y el defecto se registra como cuarto hallazgo de bookkeeping."
  - "Se agrega una columna `Status` a la tabla `## Manual-Only Verifications`, que no la tenía: sin ella las 4 filas manual-only no podían recibir disposición visible. Las cuatro reciben `⬜ no re-verificable`, ninguna `✅`."
  - "El único hit del grep de higiene de credenciales es el identificador literal de pytest `test_venue_token_resolves_by_exact_hostname`. Se mantiene textual: mutilar el nombre de un test para satisfacer un grep sería exactamente el laundering que esta fase existe para prevenir. Cero URLs, cero hostnames de venue, cero credenciales escritas."

patterns-established:
  - "Celda de evidencia de fila no re-verificable: artefacto fechado nombrado + frase explícita de por qué la evidencia parcial no alcanza (un envelope prueba que la corrida ocurrió, no que la conducta sea reproducible)"
  - "Hallazgo transversal reportado con números y ruteado a una fase futura, nunca arreglado in situ cuando el arreglo rompería el invariante de árbol congelado"

requirements-completed: [NYQ-01]

# Metrics
duration: 21min
completed: 2026-08-31
status: complete
---

# Phase 41 Plan 06: Auditoría Nyquist retroactiva de la Phase 39 Summary

**Las 15 filas de la Phase 39 dispuestas 10/1/4 contra el árbol congelado de v1.7 con cero tráfico de red, y el criterio 3b anclado por `not_verifiable_retroactively: 4` — la única de las cinco fases que declara en su propio front-matter que retiene ítems no re-verificables.**

## Performance

- **Duration:** ~21 min
- **Tasks:** 2
- **Files modified:** 1
- **Tests re-ejecutados:** 78 (7 suites de `verification/`) + 13 (`packages/matriz-client/`) + 50 (edges ×3) + 2 (selector de ámbito), sin una sola falla

## Accomplishments

- **15 filas dispuestas, exactamente una disposición cada una**, con claves ordinales únicas `39-r01`..`39-r11` más `39-m01`..`39-m04`. Reparto medido **10 VERIFIED-NOW / 1 VERIFIED-HISTORICALLY / 4 NOT-VERIFIABLE-RETROACTIVELY**, idéntico al predicho por §2.4 del contrato.
- **Las 4 filas manual-only quedan `NOT-VERIFIABLE-RETROACTIVELY`** con su evidencia parcial superviviente nombrada por fila (los 4 envelopes con sus sondas ejecutadas — iol 15, matriz 50, ámbito 7, higyrus 0 con causa medida —, las transcripciones de `39-07-SUMMARY.md`, `39-CENSUS.md` §§ "Casos límite de D-12" y "El split que SC-4 exige", y el sign-off del operador de `main_matriz.py:118-121`), cada una con la frase explícita de por qué no basta para `VERIFIED-HISTORICALLY`.
- **`39-r03` re-apuntada por R-02**, la segunda y última corrección autorizada de la fase: el `-k allowlist` del mapa sale **exit 5** con `9 deselected in 0.01s` y **cero** pasados; el sustituto `verification/test_main_matriz_skip_line_shape.py` corre `19 passed in 0.06s`. Se leyó el **cuerpo** de los tres locks de allowlist antes de re-apuntar y se resumió lo que asserta cada uno (dos hosts exactos y ninguno más; 13 casos parametrizados con superstring de sufijo y userinfo rechazados; aserción por AST de que no vuelve el chequeo por substring).
- **Cero tráfico de red.** Ningún `main_*.py` fue ejecutado. Las conductas que la Phase 39 verificó en vivo se dispusieron contra artefactos fechados en disco (R-08).
- **Hallazgo transversal cuantificado y ruteado:** 52 archivos `verification/test_*.py`, 12 enrolados en `ci.yml:81-92`, **40 sin correr en CI**. Reportado con números; el edit consolidado del workflow queda ruteado a la **Phase 45** (HARN-04). `.github/workflows/ci.yml` sin tocar.
- **Invariante de árbol congelado verificado 4 veces** (inicio, fin de cada tarea, cierre): `git diff --quiet v1.7 HEAD -- . ':(exclude).planning'` → exit 0 siempre.

## Task Commits

1. **Task 1: Re-ejecutar las 10 filas automatizadas, re-apuntar el selector vacío, reunir evidencia de las 5 no automatizadas** — `59e604e` (docs)
2. **Task 2: Escribir la sección de auditoría y transformar el front-matter con el marcador del criterio 3b** — `d77d43a` (docs)

## Files Created/Modified

- `.planning/milestones/v1.7-phases/39-verificaci-n-en-vivo-del-encadenamiento-profundo/39-VALIDATION.md` — sección `## Validation Audit 2026-08-31` con los 8 bloques del contrato más una subsección propia para las 4 filas no re-verificables; columna `Status` actualizada en las 11 filas del mapa; columna `Status` **agregada** a la tabla manual-only con sus 4 valores; leyenda extendida; línea nueva tildada en `## Validation Sign-Off`; front-matter transformado.

## Decisions Made

Ver `key-decisions` en el front-matter. Las cuatro, resumidas:

1. **R-07 para las cuatro filas manual-only**, contra la recomendación del researcher. D-04 las nombra por su nombre; ante conflicto entre decisión lockeada e inferencia posterior, gana la decisión. Además, un `VERIFIED-HISTORICALLY` de más es una garantía falsa que se propaga aguas abajo; un `NOT-VERIFIABLE-RETROACTIVELY` de más sólo pide trabajo futuro. El rationale quedó **escrito en el artefacto** para que no se re-litigue.
2. **`39-r08` no es una tercera R-02.** Su defecto es de otra clase (node-id que nombra un helper, exit 4 de error de uso) y la conducta sí está cubierta. Se dispuso `VERIFIED-NOW` plano y el defecto se registró como hallazgo de bookkeeping, preservando el "cero escalaciones" del contrato con la explicación de por qué.
3. **Columna `Status` agregada a la tabla manual-only.** Era la única forma de darle disposición visible a las 4 filas sin `✅` sobre una fila manual (Pitfall 4).
4. **El nombre del test se mantiene textual** pese al hit del grep de higiene.

## Deviations from Plan

Ninguna que requiriera desviarse de una regla. Cuatro **divergencias de medición** respecto de números que el plan anticipó, todas resueltas escribiendo el medido, como el plan indica:

**1. [Medición] El plan esperaba "8 celdas `File Exists`" stale; medidas 9**
- **Found during:** Task 2
- **Issue:** El plan dice que ocho celdas `File Exists` afirman que el archivo falta. Contadas: **9** de las 11 están en `❌` (`Wave 0` ×3, `Wave 1` ×4, `Wave 2` ×1, `per-fix` ×1); las 2 restantes ya decían `✅ exists`.
- **Fix:** Se escribió el número medido (9) y se aclaró que las **once** superficies existen hoy y corren verde — ocho suites de test más el artefacto `39-CENSUS.md`.
- **Committed in:** `d77d43a`

**2. [Medición] El plan esperaba 14 parámetros en el test de resolución por hostname exacto; medidos 13**
- **Found during:** Task 1
- **Issue:** El `@pytest.mark.parametrize` del lock sustituto tiene **13** casos, no 14. El total del archivo (19 collected = 4 + 1 + 13 + 1) confirma el 13.
- **Fix:** Se escribió 13 en la sección `### Correcciones de comando`. Las dos variantes que el plan exige nombrar —superstring de sufijo y userinfo— están ambas presentes y verificadas en el cuerpo del test.
- **Committed in:** `59e604e`

**3. [Hallazgo no anticipado] El node-id de `39-r08` nombra un helper privado, no un test**
- **Found during:** Task 1
- **Issue:** El mapa declara `verification/test_cycle_closure_phase33.py::_ambito_declares_zero_models`; esa función es un helper del módulo. pytest sale **exit 4** con `no tests ran in 0.01s`. El plan lo listaba como una de las 10 filas automatizadas con "2 pasados", sin anticipar que el comando literal del mapa no corre.
- **Fix:** Evaluado explícitamente contra el disparador de R-02 (selector `-k`, exit 5, selección vacía) — **no lo satisface**, así que no consume la tercera corrección que el contrato prohíbe. La fila se dispuso `VERIFIED-NOW` plano ejecutando el selector de archivo `-k ambito` → `2 passed, 19 deselected in 0.01s`, tras confirmar que los dos casos parametrizados seleccionados atraviesan ese mismo helper y assertan la conducta declarada (0 clases de modelo, `__all__` vacío). Registrado como cuarto hallazgo de bookkeeping con su razonamiento completo.
- **Committed in:** `59e604e` (disposición) y `d77d43a` (hallazgo)

**4. [Estructura] La tabla `## Manual-Only Verifications` no tenía columna `Status`**
- **Found during:** Task 2
- **Issue:** El plan exige actualizar la columna `Status` de las 15 filas; la tabla manual-only no la tenía.
- **Fix:** Columna agregada de forma aditiva, con las 4 filas en `⬜ no re-verificable` y una línea de leyenda propia que declara cuándo y por qué se agregó. Ninguna fila manual lleva `✅`.
- **Committed in:** `d77d43a`

---

**Total deviations:** 4 (2 correcciones de número medido, 1 hallazgo no anticipado, 1 ajuste estructural). Ninguna tocó fuente de producto.
**Impact on plan:** Nulo sobre el resultado. El reparto 10/1/4, el conteo de 5 `NOT ENFORCED`, la única corrección de comando y `not_verifiable_retroactively: 4` salieron exactamente como el contrato predijo.

## Security

- **Cero tráfico de red.** Ningún `main_*.py` fue ejecutado por esta auditoría (T-41-06-02 mitigado). Los únicos comandos ejecutados fueron `git`, `ls`, `grep` y `uv run pytest` sobre suites locales.
- **Higiene de credenciales (T-41-06-01):** `grep -cE '://|@[a-z0-9.-]+\.(com|ar|example)|[Tt]oken|[Pp]assword|Bearer'` sobre la sección de auditoría escrita da **1**, y ese único hit es el identificador literal de pytest `test_venue_token_resolves_by_exact_hostname` — un nombre de función del repo, de la misma clase que una ruta de archivo, sin ningún valor de credencial. **Cero** URLs con esquema, **cero** hostnames de venue transcritos (las variantes de spoofing se describen en prosa, nunca se pegan), **cero** ids de cuenta, **cero** portadores. Toda salida de pytest fue recortada a su línea de resumen.
- **T-41-06-03 mitigado:** las 4 filas manual-only no se lavaron como cubiertas; `not_verifiable_retroactively: 4` está en front-matter.
- **T-41-06-04 mitigado:** el lock de allowlist de hostname no se certificó a ciegas — se leyó el cuerpo de los tres tests sustitutos y ambos comandos quedaron transcritos.
- **T-41-06-05 mitigado:** el conteo 52/12/40 está reportado con números en la sección de hallazgos.
- **T-41-06-SC:** cero instalaciones de paquetes.

## Issues Encountered

Ninguno bloqueante. El único punto que exigió juicio fue si `39-r08` constituía la tercera corrección R-02 que el contrato marca como hallazgo escalable; se resolvió contra la letra del disparador de R-02 (exit 4 vs exit 5, node-id vs `-k`) y se documentó el razonamiento en el propio artefacto para que sea auditable.

## Known Stubs

Ninguno.

## User Setup Required

None.

## Next Phase Readiness

- **41-07 (cierre) tiene todo lo que necesita de este plan:** la quinta y última tabla de disposición está escrita con la forma que sus gates aritméticos esperan (`^\| 39-[rm][0-9]` acotado entre `### Disposición por fila` y `*Disposiciones:`), y aporta **15** al denominador de 62. Con 41-02..41-06 cerrados, el total acumulado es **62/62** filas dispuestas: **54 VERIFIED-NOW / 4 VERIFIED-HISTORICALLY / 4 NOT-VERIFIABLE-RETROACTIVELY**, exactamente el reparto medido de §2.4.
- **Los cinco `nyquist_compliant` quedan en `false`**, ninguno flippeado. Phase 39 falla R-09 por (b) y (c) a la vez.
- **Los cinco `not_verifiable_retroactively` quedan escritos**, cuatro en `0` y éste en `4` — el conjunto es uniforme y greppeable, que es lo que el criterio 3b pide.
- **Línea base del criterio 4 intacta:** 52 archivos `verification/test_*.py`, `git status --porcelain verification/` vacío, cero archivos de test nuevos. 41-07 la re-mide.
- **Ruteo abierto a la Phase 45:** 40 locks sin enrolar en el allowlist de CI, con el conteo escrito y el destino nombrado.

## Self-Check: PASSED

- `59e604e` presente en git log — Task 1
- `d77d43a` presente en git log — Task 2
- `.planning/phases/41-.../41-06-SUMMARY.md` existe en disco
- `.planning/milestones/v1.7-phases/39-.../39-VALIDATION.md` existe y contiene la sección de auditoría
- `git diff --quiet v1.7 HEAD -- . ':(exclude).planning'` → exit 0 al cierre

---
*Phase: 41-validaci-n-nyquist-retroactiva-de-v1-7*
*Completed: 2026-08-31*
