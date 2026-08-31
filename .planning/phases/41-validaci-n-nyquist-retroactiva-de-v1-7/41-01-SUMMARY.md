---
phase: 41-validaci-n-nyquist-retroactiva-de-v1-7
plan: 01
subsystem: testing
tags: [nyquist, validation-audit, git-attribution, ci-enforcement, documentation]

# Dependency graph
requires:
  - phase: 35-39 (v1.7)
    provides: los cinco {N}-VALIDATION.md en status draft que esta fase audita
  - phase: 41 (research/patterns/context)
    provides: la medición de las 62 filas, el mapa de enforcement de CI y los precedentes de formato
provides:
  - "41-AUDIT-CONTRACT.md — contrato autoritativo de la fase (8 secciones, 716 líneas)"
  - "Identidad del árbol auditado probada: audited_commit_sha + audit_baseline_head + diff vacío"
  - "Denominador 62 fijado con desglose 13/11/14/9/15 y los dos denominadores erróneos rechazados"
  - "Esquema de claves de fila {N}-r{NN} / {N}-m{NN} que hace contable el criterio 2"
  - "Reglas de disposición R-01..R-08 mutuamente excluyentes + regla de front-matter R-09"
  - "Resolución escrita de las dos Open Questions de RESEARCH.md, con rationale"
  - "Esqueleto exacto de la sección '## Validation Audit 2026-08-31' que los 5 planes de Wave 2 copian"
  - "Mapa de enforcement de CI re-verificado contra ci.yml en HEAD (4ª columna, D-07)"
  - "Las tres prohibiciones de workflow escritas, no implícitas"
  - "41-VALIDATION.md realineado a los 7 planes / 16 tareas reales, con wave_0_complete: true"
affects: [41-02, 41-03, 41-04, 41-05, 41-06, 41-07, phase-45-ci-enrollment]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Contrato de auditoría compartido como artefacto de Wave 1 que elimina decisiones de formato en Wave 2"
    - "Clave ordinal de fila ({N}-r{NN}) como unidad contable cuando los Task IDs no son únicos"
    - "Front-matter key not_verifiable_retroactively como marcador del criterio 3b"

key-files:
  created:
    - .planning/phases/41-validaci-n-nyquist-retroactiva-de-v1-7/41-AUDIT-CONTRACT.md
  modified:
    - .planning/phases/41-validaci-n-nyquist-retroactiva-de-v1-7/41-VALIDATION.md

key-decisions:
  - "OQ#1 resuelta: las 4 filas manual-only de la Phase 39 se disponen NOT-VERIFIABLE-RETROACTIVELY (R-07), honrando el ejemplo explícito de D-04 por sobre la recomendación del researcher; la evidencia parcial se nombra pero no alcanza a re-derivar la conducta (sub-declarar antes que sobre-declarar, D-10)"
  - "OQ#2 resuelta: ni la Phase 36 ni la 37 cierran limpias — 36-r11 sólo cierra con un comando redactado retroactivamente y 37-r11 con un selector corregido; R-09 incluye por eso la condición (c) 'cero calificadores de corrección', y las cinco fases quedan en nyquist_compliant: false por evidencia, no por decreto"
  - "Marcador del criterio 3b: clave entera not_verifiable_retroactively presente en los cinco archivos (incluso donde vale 0); se descarta nyquist_compliant: partial porque D-09 fija false y partial es un one-off del repo"
  - "Denominador del criterio 2 fijado en 62 (13/11/14/9/15); rechazados 51 (as-declared) y 25 (criterios de ROADMAP)"
  - "audit_baseline_head se captura una sola vez en el contrato (6dd83cf4) y se copia literal; no se re-captura por plan"
  - "Criterio 1 declarado invariante continuo: se re-verifica por plan y por tarea en Waves 2 y 3, no es un gate de una sola vez"

patterns-established:
  - "Contrato de fase: un artefacto de Wave 1 que fija formato, vocabulario y reglas de decisión para que N ejecutores paralelos produzcan artefactos idénticos en forma"
  - "Gate aritmético acotado: las tablas de disposición se cuentan entre '### Disposición por fila' y la línea de leyenda, lo que obliga a un orden de bloques fijo (métricas ANTES de la tabla)"
  - "Anti-vacuidad de evidencia: toda celda VERIFIED-NOW debe llevar conteo de tests pasados distinto de cero; deselect total (pytest exit 5) cae en R-02 o se escala"

requirements-completed: [NYQ-01]

# Metrics
duration: 8min
completed: 2026-08-31
status: complete
---

# Phase 41 Plan 01: Precondición de atribución y contrato de auditoría — Summary

**Contrato de auditoría de 8 secciones que fija denominador 62, claves ordinales de fila, nueve reglas de disposición y el esqueleto exacto de la sección `## Validation Audit`, sobre un árbol de v1.7 probado idéntico al tag (`37a83fe6`) con diff vacío.**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-08-31T16:01:20Z
- **Completed:** 2026-08-31T16:09:12Z
- **Tasks:** 3
- **Files modified:** 2 (1 creado, 1 reescrito)

## Accomplishments

- **Criterio 1 probado, no asumido.** `git rev-parse v1.7^{commit}` → `37a83fe693a303a551f4374f48fe6fc5521804f7` (el commit, no el objeto-tag), HEAD de la sesión `6dd83cf4c8b2837e320da9c8c91bc1b15ac41fa5`, y `git diff --quiet v1.7 HEAD -- . ':(exclude).planning'` con exit 0. Declarado por escrito como **invariante continuo**, con los tres puntos de re-verificación nombrados.
- **El contrato elimina el juicio de la Wave 2.** Las cinco auditorías paralelas ya no deciden formato ni disposición: el denominador, el esquema de claves, las nueve reglas, el front-matter objetivo, el esqueleto de sección, la higiene de evidencia y el mapa de enforcement de CI están escritos. Un ejecutor de la Wave 2 puede producir su artefacto leyendo sólo el contrato más su propio `{N}-VALIDATION.md`.
- **Las dos Open Questions quedaron resueltas con rationale, no diferidas.** OQ#1 contra la recomendación del researcher y a favor del ejemplo lockeado de D-04; OQ#2 desmontando la premisa de que 36 y 37 cierran limpias — la condición (c) de R-09 (cero calificadores de corrección) es consecuencia directa de esa resolución.
- **La prohibición más peligrosa quedó escrita.** El §3 del workflow project-local pone `nyquist_compliant: true` cuando no hay gaps, y la medición dice que efectivamente no hay gaps: correrlo sin modificar flipearía los cinco flags en silencio. Queda deshabilitado por escrito, con warning signs concretos para el diff.
- **Las dos Wave 0 gaps de `41-VALIDATION.md` cerradas antes del primer artefacto**, y su mapa realineado de 8 filas hipotéticas a las **16 tareas reales** de los siete planes, con los comandos `<automated>` verdaderos.

## Task Commits

1. **Task 1: Probar el árbol congelado y capturar los dos SHA de atribución** — `9876464` (docs)
2. **Task 2: Escribir el contrato de disposición (secciones 2-8)** — `506a710` (docs)
3. **Task 3: Cerrar las dos Wave 0 gaps y realinear el mapa a los 7 planes reales** — `532c441` (docs)

## Files Created/Modified

- `.planning/phases/41-validaci-n-nyquist-retroactiva-de-v1-7/41-AUDIT-CONTRACT.md` — **nuevo**, 716 líneas. Contrato autoritativo: §1 identidad del árbol (dos SHA, prueba de diff vacío, versiones medidas, línea base de 52 locks), §2 denominador 62 + claves `{N}-r{NN}`, §3 reglas R-01..R-08 + resolución de OQ#1/OQ#2, §4 regla R-09 y front-matter objetivo, §5 esqueleto de la sección de auditoría + regla de la columna `Status`, §6 higiene de evidencia, §7 mapa de enforcement de CI, §8 prohibiciones de workflow.
- `.planning/phases/41-validaci-n-nyquist-retroactiva-de-v1-7/41-VALIDATION.md` — **reescrito**. `wave_0_complete: true`, mapa de 16 filas alineado a los planes reales, sección nueva de denominador, versiones de herramienta corregidas, Manual-Only con la disposición de OQ#1 ya resuelta. `status`/`nyquist_compliant` deliberadamente **sin tocar** (D-10: la auto-disposición es trabajo de 41-07).

## Decisions Made

Ver `key-decisions` en el front-matter. Las dos de mayor consecuencia aguas abajo:

1. **R-09 tiene tres condiciones, no dos.** Además de "100% VERIFIED-NOW" y "cero VH/NVR", exige **cero calificadores de corrección**. Sin esa tercera condición, las Phases 36 y 37 calificarían para `nyquist_compliant: true` — y una fase cuyo contrato de verificación tuvo que ser reparado por su propio auditor para poder correr no es Nyquist-compliant, es una fase cuyo bookkeeping estaba roto.
2. **La distribución de disposiciones esperada (§2.4) es un control de sanidad, no una cuota.** 54 VN / 4 VH / 4 NVR. Si un ejecutor de la Wave 2 mide otra cosa, eso **es** un hallazgo y se escala; el contrato dice explícitamente que no se fuerza el número.

## Deviations from Plan

### Auto-fixed Issues

**1. [Regla 1 - Bug] Mis-suma del planner: el denominador de tareas de la Phase 41 es 16, no 14**

- **Found during:** Task 3 (realineación del mapa de `41-VALIDATION.md`)
- **Issue:** El plan enumera explícitamente 16 IDs de tarea (`41-01-01`..`41-07-03`) y luego declara `3 + 2 + 2 + 2 + 2 + 2 + 3 = 14`. La suma real es 16. El bloque `<verify><automated>` de 41-01 Task 3 exige `-eq 14`, lo que contradice la lista enumerada del mismo bloque. `41-07` Task 3 arrastra el mismo `14`.
- **Fix:** Medido con `grep -c '<task '` sobre los siete planes: 3, 2, 2, 2, 2, 2, 3 → **16**. Se escribieron las 16 filas reales. La corrección quedó registrada en `41-AUDIT-CONTRACT.md § 2.5` y en `41-VALIDATION.md § Denominador`, para que el ejecutor de 41-07 no la re-descubra y no falle contra un `-eq 14` imposible.
- **Files modified:** `41-AUDIT-CONTRACT.md`, `41-VALIDATION.md`
- **Verification:** `grep -c '^| 41-0[1-7]-0[0-9] ' 41-VALIDATION.md` → 16; el resto de la cadena de verificación de Task 3 pasa.
- **Committed in:** `506a710` (§2.5) y `532c441` (mapa)

**2. [Regla 3 - Blocking] El verify de Task 3 se auto-falsificaba al transcribir sus propios literales**

- **Found during:** Task 3
- **Issue:** El plan pide poner en la columna `Automated Command` el comando `<automated>` real de cada tarea. El de 41-01 Task 3 contiene `! grep -q '<row selector>'` y `! grep -q 'pytest 8'` — transcribirlo verbatim mete esos literales en el archivo y hace que sus propias aserciones negativas fallen. Verificado: tras la primera escritura, la cadena de verificación falló por auto-referencia.
- **Fix:** Esa celda transcribe las aserciones positivas verbatim y describe las dos negativas ("cero placeholders de selector, cero declaraciones stale del runner") apuntando a `41-01-PLAN.md` Task 3 para la cadena literal. Además se reformularon dos frases de la sección `## Test Infrastructure` para nombrar la versión stale como "serie 8.x / 8.3" sin el literal prohibido.
- **Files modified:** `41-VALIDATION.md`
- **Verification:** cadena completa de Task 3 verde con `-eq 16`; `grep -c 'pytest 8'` → 0; `grep -c '<row selector>'` → 0.
- **Committed in:** `532c441`

**3. [Regla 1 - Bug] Rangos de línea de `ci.yml` corregidos contra el archivo real**

- **Found during:** Task 2 (§7, mapa de enforcement)
- **Issue:** `41-RESEARCH.md` declara `job test, ci.yml:133-165`. El bloque real del job `test` es **133-166** y el paso de tests concreto está en **154-160**.
- **Fix:** El contrato declara `ci.yml:133-166` (con el paso en 154-160) y registra explícitamente la corrección, tal como el plan pedía ("re-verificar los números de línea contra el `ci.yml` actual"). Los demás rangos (36-39, 40-41, 55, 60, 66, 81-92, 122-123, 124-131) se re-verificaron y coinciden.
- **Files modified:** `41-AUDIT-CONTRACT.md`
- **Verification:** `grep -n 'verification/test_main_market_data_deep_chain.py' .github/workflows/ci.yml` → línea 81, dentro del rango declarado 81-92.
- **Committed in:** `506a710`

---

**Total deviations:** 3 auto-fixed (2 bugs, 1 blocking)
**Impact on plan:** Ninguna amplía el alcance. Las tres son correcciones de exactitud sobre artefactos de documentación; la #1 y la #2 desbloquean planes aguas abajo que de otro modo fallarían contra aserciones imposibles.

## Issues Encountered

- **Auto-referencia del gate de verificación** (ver deviación #2): un artefacto que asserta sobre su propio contenido no puede transcribir literalmente los patrones que prohíbe. Resuelto describiendo las aserciones negativas y apuntando al plan para la forma ejecutable. Vale la pena tenerlo presente en 41-07 Task 3, que asserta sobre el mismo archivo.
- **Ninguna otra.** Cero comandos de red, cero instalaciones de paquetes, cero cambios de fuente de producto.

## Threat Flags

Ninguna superficie de seguridad nueva. Las tres mitigaciones del `<threat_model>` del plan están aplicadas y son verificables:

| Threat ID | Mitigación aplicada |
|-----------|---------------------|
| T-41-01 (Information Disclosure) | `41-AUDIT-CONTRACT.md § 6.3` fija la regla de recorte a línea de resumen y la revisión del diff por `://`, `@`, `token`, `password`, `Bearer`. Ningún comando de este plan leyó `.env` ni abrió red |
| T-41-02 (Repudiation, SHA mal resuelto) | `git rev-parse v1.7^{commit}` usado en todo momento; verificado que el SHA del objeto-tag **no aparece** en el contrato (`grep -c` → 0) |
| T-41-03 (Repudiation, flip mecánico) | R-09 escrita (§4.1) + §8(c) deshabilita explícitamente la rama §3 del workflow project-local, con warning signs para el diff |
| T-41-SC (Tampering, paquetes) | Cero invocaciones de `npm`/`pip`/`cargo`/`uv add`. `uv.lock` y `pyproject.toml` byte-idénticos (cubierto por el diff vacío contra `v1.7`) |

## User Setup Required

Ninguna — no hay configuración de servicios externos.

## Next Phase Readiness

- **Wave 2 desbloqueada.** Los cinco planes (41-02..41-06) pueden correr en paralelo: cada uno tiene su denominador, sus reglas de disposición, su front-matter objetivo, su esqueleto de sección y su columna de enforcement, todo en un solo archivo.
- **Invariante en pie al cierre de este plan:** `git diff --quiet v1.7 HEAD -- . ':(exclude).planning'` → exit 0; `git status --porcelain verification/` vacío; `ls verification/test_*.py | wc -l` → 52.
- **Dos avisos para 41-07:** (a) su gate de `41-[rm]NN` debe contar **16**, no 14 (deviación #1); (b) su verificación asserta sobre `41-VALIDATION.md`, el mismo archivo que edita — cuidado con la auto-referencia (deviación #2).
- **Cero cambios fuera de `.planning/phases/41-*/`.** Los cinco `{N}-VALIDATION.md` de v1.7 siguen intactos: eso es trabajo de la Wave 2, por diseño.

## Self-Check: PASSED

- `41-AUDIT-CONTRACT.md` — FOUND (716 líneas, 8 secciones numeradas, 9 reglas R-01..R-09)
- `41-VALIDATION.md` — FOUND (`wave_0_complete: true`, 16 filas de tarea)
- Commit `9876464` — FOUND
- Commit `506a710` — FOUND
- Commit `532c441` — FOUND

---
*Phase: 41-validaci-n-nyquist-retroactiva-de-v1-7*
*Completed: 2026-08-31*
