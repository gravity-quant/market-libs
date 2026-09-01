---
phase: 41-validaci-n-nyquist-retroactiva-de-v1-7
plan: 04
subsystem: testing
tags: [nyquist-audit, validation, retroactive-audit, pytest, mypy, matriz-client, markdown]

# Dependency graph
requires:
  - phase: 41-01
    provides: "41-AUDIT-CONTRACT.md — denominador 62 (13/11/14/9/15), claves ordinales {N}-r{NN}, reglas R-01..R-09, front-matter objetivo, esqueleto de ocho bloques, higiene de evidencia, lookup de enforcement de CI, y los dos SHA de atribución"
provides:
  - "37-VALIDATION.md auditado: 14 filas dispuestas bajo clave ordinal 37-r01..37-r14, 14 VERIFIED-NOW (1 con calificador `comando corregido`), 0 VERIFIED-HISTORICALLY, 0 NOT-VERIFIABLE-RETROACTIVELY"
  - "La primera de las dos correcciones R-02 autorizadas en toda la Phase 41 (37-r11); la segunda queda para la Phase 39"
  - "Front-matter de la Phase 37 transformado: status draft → validated, nyquist_compliant intacto en false, not_verifiable_retroactively: 0, más los tres campos de atribución"
affects: [41-05, 41-06, 41-07]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Clave ordinal obligatoria cuando los Task ID del mapa no son únicos (§2.3 del contrato aplicada por primera vez a un mapa con IDs repetidos de verdad)"
    - "R-02 aplicada con lectura del cuerpo del test sustituto, no de su nombre (Assumptions Log A1)"

key-files:
  created: []
  modified:
    - ".planning/milestones/v1.7-phases/37-matriz-client-dicts-residuales-tipados-alias/37-VALIDATION.md"

key-decisions:
  - "La clave ordinal 37-r01..37-r14 es la unidad de conteo del criterio 2 en esta fase: los Task ID del mapa se reparten sólo cuatro etiquetas (37-01-xx ×3, 37-03-xx ×5, 37-04-xx ×3, 37-xx ×2) entre catorce filas, de modo que 'exactamente una disposición por fila' no era computable con la clave original"
  - "37-r11 dispuesta VERIFIED-NOW (comando corregido) tras leer el cuerpo de los dos tests sustitutos y confirmar que assertan identidad (`is`) de los seis alias sobre una instantánea parseada por REST y otra por frame de WS — la conducta declarada, no otra"
  - "nyquist_compliant se queda en false pese a 14/14 verdes: R-09 falla por su condición (c), una fila con calificador de corrección; certificar cumplimiento total sobre un contrato que la propia auditoría reescribió sería grading contra lo que shipeó"
  - "Las celdas File Exists y la columna Task ID del mapa NO se tocan: su contradicción con la realidad medida es el hallazgo, y corregirlas lo borraría"

patterns-established:
  - "Corrección R-02 documentada con ambos comandos: el original con su exit 5 y cero pasados, y el corregido con su conteo de pasados, en la celda de evidencia y en la sección `### Correcciones de comando`"
  - "El hallazgo de bookkeeping se enumera de forma exhaustiva y verificable (6 celdas ❌ Wave 0 + 4 celdas que declaran extensión pendiente + 4 celdas limpias = 14) en vez de dar un número redondo"

requirements-completed: [NYQ-01]

# Metrics
duration: 24min
completed: 2026-08-31
status: complete
---

# Phase 41 Plan 04: Auditoría Nyquist retroactiva de la Phase 37 Summary

**Las 14 filas del mapa de la Phase 37 quedan dispuestas bajo clave ordinal `37-r01`..`37-r14` con evidencia re-ejecutada esta sesión contra el árbol congelado de v1.7; el selector muerto `-k alias_surfaces` (0 de 74 seleccionados, exit 5) queda re-apuntado a los dos tests que sí cubren la conducta, con ambos comandos escritos; `nyquist_compliant` sigue en `false` con rationale que dice por qué 14 verdes no bastan.**

## Performance

- **Duration:** ~24 min
- **Started:** 2026-08-31T16:31:00Z
- **Completed:** 2026-08-31T16:55:00Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- **14/14 filas dispuestas, cero sin disponer y cero con doble disposición**, pese a que los Task ID originales del mapa se reparten sólo cuatro etiquetas entre catorce filas. La clave ordinal `37-r01`..`37-r14` (§2.3 del contrato) es única — la lista ordenada y deduplicada tiene 14 elementos — y la celda `Row` lleva clave + Task ID original + posición en el mapa, de modo que las cinco filas que comparten `37-03-xx` quedan individualmente identificadas.
- **Las 13 filas con comando ejecutable se re-corrieron esta sesión**, todas verdes con conteo de pasados distinto de cero y exit 0: `test_surface_types_red.py` 19 pasados, `-k exempt` 3, el gate verde sobre el árbol real en iol 1, `-k envelope` 10, `-k tickPriceRange` 3, `-k portfolio` 3, `-k extra` 9, `-k mapping` 24, `-k convert` 4, `-k alias` 11, el test nominal de divergencia 1, las dos suites de WS 35 entre ambas, y `uv run mypy packages/matriz-client/src` → `Success: no issues found in 17 source files`.
- **`37-r11` re-apuntada por R-02 con verificación del cuerpo, no del nombre.** El comando original del mapa se ejecutó y se documentó con su resultado real (`74 deselected in 0.01s`, **exit 5**, cero pasados, ninguna línea de falla). Antes de re-apuntar se leyeron los cuerpos de `test_each_alias_returns_the_identical_object_on_a_rest_parsed_snapshot` y de `…_on_a_ws_frame_parsed_snapshot`: el primero asserta los seis alias con `is` (identidad, no igualdad) contra su campo de wire sobre `MarketDataSnapshot.from_api(_REST_MARKET_DATA)`; el segundo repite las seis identidades sobre `MarketDataFrame.from_api(_WS_FRAME).marketData` más `isinstance(..., MarketDataSnapshot)`. Es exactamente la conducta que la fila declara. El comando corregido reporta `2 passed, 72 deselected in 0.01s`, exit 0.
- **Ninguna segunda fila de selección vacía.** El guardia anti-vacuidad de la §6.2 se disparó exactamente una vez, el número que `41-RESEARCH.md` había medido para esta fase. Los ocho deselects restantes son parciales y todos reportan pasados ≠ 0. No hubo nada que escalar.
- **Cero filas `NOT ENFORCED`**: las trece de pytest caen bajo el job `test` (`ci.yml:133-166`, paso en `154-160`) y la de mypy bajo `typecheck` (`ci.yml:122-123`, step `mypy (src global)`). La Phase 37 declara cero verificaciones manual-only y ninguna de sus filas asserta sobre markdown de `.planning/`.
- **Invariante de criterio 1 sostenido de punta a punta**: `git diff --quiet v1.7 HEAD -- . ':(exclude).planning'` salió 0 antes de empezar, al cerrar cada tarea y al terminar. `git status --porcelain verification/` vacío; `ls verification/test_*.py | wc -l` sigue en 52. Cero archivos de test nuevos, cero ediciones a `packages/`, cero ediciones a `.github/`.

## Task Commits

1. **Task 1: Re-ejecutar las 14 filas de la Phase 37 y re-apuntar el selector que no selecciona nada** — `3f4f597` (docs)
2. **Task 2: Escribir la sección de auditoría de la Phase 37 y transformar su front-matter** — `cd16db9` (docs)

## Files Created/Modified

- `.planning/milestones/v1.7-phases/37-matriz-client-dicts-residuales-tipados-alias/37-VALIDATION.md` — sección `## Validation Audit 2026-08-31` con los ocho bloques del contrato (párrafo de procedencia, par de encabezados en negrita, bloque de métricas, tabla de disposición de 14 filas y 4 columnas, una corrección de comando, dos hallazgos de bookkeeping, escalaciones, veredicto + rationale); columna `Status` de las 14 filas del mapa a `✅ (VN 2026-08-31)` con la leyenda extendida; una línea nueva tildada en `## Validation Sign-Off` (las preexistentes quedan sin tildar); front-matter con `status: validated`, `nyquist_compliant: false`, `not_verifiable_retroactively: 0`, `audited_commit_sha`, `audit_baseline_head`, `frozen_tree_verified: true`, `updated`, `last_audited`.

## Decisions Made

- **La clave ordinal no es cosmética en esta fase, es la precondición del criterio 2.** El mapa de la Phase 37 no tiene identificadores de fila: tiene formas con sufijo genérico que se repiten. Sin la clave `37-rNN` no hay forma mecánica de probar "exactamente una disposición por fila", y una tabla de disposición indexada por `37-03-xx` no distinguiría cuál de las cinco filas se dispuso.
- **`nyquist_compliant` se queda en `false` aunque las catorce filas corran verde hoy.** R-09 falla por (c) — una fila con calificador de corrección — y por (a) — 13 de 14 disponen `VERIFIED-NOW` plano. La condición (b) sí se cumple. El rationale escrito en el artefacto dice explícitamente por qué 14 verdes no bastan: una de esas catorce sólo corre verde después de que la auditoría le corrigiera el comando, y certificar cumplimiento total sobre un contrato de verificación que la propia auditoría reescribió sería grading contra lo que shipeó en vez de contra el criterio.
- **La corrección de `37-r11` se enmarca explícitamente como bookkeeping, no como gap de cobertura.** La conducta estaba cubierta desde la Wave 0 de la fase; el selector del mapa era el que estaba mal.
- **No se tocan ni las celdas `File Exists` ni la columna `Task ID`.** Ambas contradicen la realidad medida, y esa contradicción es el hallazgo; corregirlas lo borraría. `wave_0_complete` se deja en `false` por el mismo motivo.

## Deviations from Plan

Una divergencia de medición, sin impacto en ninguna disposición.

**1. [Rule 2 — precisión de la medición] El conteo de celdas `File Exists` contradictorias es 10, no 8**

- **Found during:** Task 2 (escritura del segundo hallazgo de bookkeeping)
- **Issue:** El plan instruye escribir *"que ocho celdas de `File Exists` del mapa afirman que el archivo de test falta o necesita extensión"*. La enumeración real de las catorce celdas da otro reparto: **6** dicen `❌ Wave 0` (el archivo no existe: filas 1, 2, 4, 5, 10 y 11 del mapa), **4** dicen que el archivo existente no alcanza (`✅ (floors only)`, `✅ exists, assertion flips`, `✅ mechanism tested; needs new-model case`, `✅ exists, must be extended`), y **4** son afirmaciones limpias de existencia (`✅ exists, must keep passing`, `✅ exists — do not rewrite`, `✅ exists`, `✅ green today`). 6 + 4 + 4 = 14.
- **Fix:** Se escribió el reparto **medido** (10 celdas contradictorias, desglosadas en 6 + 4) en vez del número del plan, tal como el propio plan manda para el reparto de disposiciones (*"Si la medición da otro reparto, escribir el medido y anotar la divergencia en el SUMMARY"*). El desglose queda enumerado en el artefacto para que sea re-contable.
- **Files modified:** `.planning/milestones/v1.7-phases/37-matriz-client-dicts-residuales-tipados-alias/37-VALIDATION.md`
- **Verification:** Enumeración directa de la columna `File Exists` de las 14 filas del mapa; la suma cierra contra el denominador.
- **Committed in:** `cd16db9` (commit de la Task 2)

---

**Total deviations:** 1 auto-fixed (1 corrección de precisión de medición)
**Impact on plan:** Ninguna disposición cambia; el reparto de disposiciones medido (14 / 0 / 0) coincide **exactamente** con la §2.4 del contrato, y también el conteo esperado de 0 filas `NOT ENFORCED`. La divergencia es sólo un número de prosa en un hallazgo de bookkeeping. Cero scope creep.

## Issues Encountered

- **Los exit codes de la primera corrida quedaron enmascarados por un pipe.** El primer script de re-ejecución capturaba `$?` después de un pipeline a `tail`, de modo que reportaba el código de `tail`, no el de `pytest` — el mismo tipo de falso verde que la §6.2 del contrato existe para prevenir. Se re-corrieron las diez filas con el patrón sin pipe (`out=$(uv run "$@" -q 2>&1); rc=$?`) antes de transcribir cualquier evidencia. Los códigos escritos al artefacto son los de esa segunda corrida.
- **`zsh` no hace word-splitting de parámetros sin comillas**, así que un bucle de re-verificación escrito con `$spec` sin comillas pasaba la línea entera como un solo argumento y pytest salía con código 4 (error de uso). Se resolvió corriendo la re-verificación desde `bash` con `"$@"`. Sin efecto sobre el artefacto: ninguna de esas corridas fallidas se transcribió.
- **Pre-existente, fuera de alcance:** `.planning/research/.cache/3f83a89c…json` aparece como untracked desde antes de este plan (sesión de planning). No se commiteó ni se borró — no es producto de este plan y tocarlo sería alcance ajeno.

## User Setup Required

None — la auditoría no toca servicios externos, no abre red y no lee ningún `.env`.

## Next Phase Readiness

- **Tres de las cinco fases auditadas cerradas:** 35 (13 filas), 36 (11) y 37 (14) = **38 de las 62** filas del denominador dispuestas. Quedan 38 (9 filas) y 39 (15).
- **La primera de las dos correcciones R-02 autorizadas queda consumida.** La segunda pertenece a `39-r03` (`-k allowlist` → 0 de 9). El ejecutor del plan 41-06 debe saber que una tercera fila de selección vacía en cualquier parte de la fase es un hallazgo real a escalar, no algo a re-apuntar.
- **La predicción de la §4.2 del contrato se confirma por evidencia también para la Phase 37**: R-09 no se satisface, `nyquist_compliant` no cambia. Tres de tres hasta acá; cero flags movidos en toda la fase.
- **Nota para el ejecutor del cierre (41-07):** el gate aritmético acotado entre `### Disposición por fila` y `*Disposiciones:` mide en este archivo 14 filas y 14 tokens (14 `VERIFIED-NOW`, 0 `VERIFIED-HISTORICALLY`, 0 `NOT-VERIFIABLE-RETROACTIVELY`), con 0 `NOT ENFORCED` y 0 celdas de evidencia vacua. Las líneas de la tabla empiezan con `| 37-rNN · …`, sin prefijo, tal como la §2.3 exige.

## Self-Check: PASSED

- `.planning/milestones/v1.7-phases/37-matriz-client-dicts-residuales-tipados-alias/37-VALIDATION.md` — existe, con `## Validation Audit 2026-08-31`
- `.planning/phases/41-validaci-n-nyquist-retroactiva-de-v1-7/41-04-SUMMARY.md` — existe
- Commits `3f4f597` y `cd16db9` — presentes en `git log`
- Gates: 14 filas / 14 tokens / 0 `NOT ENFORCED` / 0 evidencia vacua / 14 claves únicas / 1 corrección (`37-r11`); front-matter `status: validated` ×1, `nyquist_compliant: false` ×1, `not_verifiable_retroactively: 0` ×1, `audited_commit_sha` ×1, `audit_baseline_head` ×1; `- [x] … nyquist_compliant: true` ×0
- `git diff --quiet v1.7 HEAD -- . ':(exclude).planning'` → exit 0; `git status --porcelain verification/` vacío

---
*Phase: 41-validaci-n-nyquist-retroactiva-de-v1-7*
*Completed: 2026-08-31*
