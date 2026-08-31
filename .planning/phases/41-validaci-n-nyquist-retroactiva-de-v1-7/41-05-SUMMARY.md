---
phase: 41-validaci-n-nyquist-retroactiva-de-v1-7
plan: 05
subsystem: testing
tags: [nyquist-audit, validation, retroactive-audit, pytest, mypy, snapshot, iol-client, doc-review, markdown]

# Dependency graph
requires:
  - phase: 41-01
    provides: "41-AUDIT-CONTRACT.md — denominador 62 (13/11/14/9/15), claves ordinales {N}-r{NN} y {N}-m{NN}, reglas R-01..R-09 (acá R-01 y R-06), front-matter objetivo, esqueleto de ocho bloques, higiene de evidencia, lookup de enforcement de CI, y los dos SHA de atribución"
provides:
  - "38-VALIDATION.md auditado: 9 filas dispuestas bajo clave ordinal 38-r01..38-r08 + 38-m01, 7 VERIFIED-NOW plano, 2 VERIFIED-HISTORICALLY, 0 NOT-VERIFIABLE-RETROACTIVELY, 0 correcciones de comando"
  - "Primera aplicación de R-06 en la Phase 41: dos filas de revisión de documento dispuestas contra la confirmación humana fechada 2026-08-29T22:04:57Z registrada en el front-matter de 38-VERIFICATION.md"
  - "Primeras 3 filas NOT ENFORCED del conjunto (regen_snapshots.py + las dos de doc review), ruteadas al edit consolidado de ci.yml de la Phase 45"
  - "Front-matter de la Phase 38 transformado: status draft → validated, nyquist_compliant intacto en false, not_verifiable_retroactively: 0, más los tres campos de atribución"
affects: [41-06, 41-07]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "R-06 aplicada citando el timestamp ISO literal de human_verification[0].confirmed en vez de re-hacer la revisión del documento"
    - "Fila que muta el árbol de trabajo verificada con doble control post-corrida: git diff --stat sobre el directorio de snapshots + git status --porcelain acotado, antes de transcribir la evidencia"

key-files:
  created: []
  modified:
    - ".planning/milestones/v1.7-phases/38-iol-client-auditor-a-de-higyrus-mbito-wallets/38-VALIDATION.md"

key-decisions:
  - "38-r08 y 38-m01 se disponen VERIFIED-HISTORICALLY citando la confirmación humana fechada existente (2026-08-29T22:04:57Z), NO re-abriendo 38-CENSUS.md con criterio de esta sesión: repetir la lectura produciría un juicio de 2026-08-31 presentado como la verificación original, que es la sustitución que R-06 prohíbe"
  - "Las dos filas de revisión son la misma conducta declarada desde dos tablas distintas (SC-2), y aun así se cuentan por separado: el denominador de la §2.1 del contrato cuenta filas, no conductas; fusionarlas dejaría una fila del artefacto sin disposición"
  - "El Status de 38-05-01 queda en ⬜ histórico y nunca en ✅: §5.5 del contrato prohíbe la marca verde sobre una fila de tipo doc review aunque la disposición sea correcta"
  - "nyquist_compliant se queda en false por la condición (b) de R-09 — dos filas VERIFIED-HISTORICALLY — pese a que esta es la única de las cinco fases cuyo contrato de verificación corrió intacto, sin una sola corrección de comando ni de ruta"
  - "Las celdas File Exists ❌ W0 de las filas 38-01-01/38-01-02 y wave_0_complete: false no se tocan: su contradicción con la realidad medida es el hallazgo"

patterns-established:
  - "Fila que escribe al árbol (regen_snapshots.py): correr, comprobar diff vacío sobre el archivo citado Y sobre el directorio entero, comprobar porcelain vacío, y sólo entonces transcribir; el hecho de que la fila escriba se nombra como hallazgo de bookkeeping porque el mapa no lo señala"
  - "Bloque de prosa dedicado a por qué las filas manual-only siguen siendo manuales, siguiendo la forma de 09-VALIDATION.md pero con veredicto PARTIAL en vez de 'remains compliant'"

requirements-completed: [NYQ-01]

# Metrics
duration: 19min
completed: 2026-08-31
status: complete
---

# Phase 41 Plan 05: Auditoría Nyquist retroactiva de la Phase 38 Summary

**Las 9 filas de la Phase 38 —8 de mapa más 1 manual-only— quedan dispuestas 7 / 2 / 0: siete con evidencia re-ejecutada esta sesión contra el árbol congelado de v1.7, y dos de revisión de documento sostenidas por la confirmación humana fechada `2026-08-29T22:04:57Z` que ya existía en disco, no por un juicio nuevo; el regenerador de snapshots se corrió y dejó el árbol byte-idéntico; `nyquist_compliant` sigue en `false` por la condición (b) de R-09.**

## Performance

- **Duration:** ~19 min
- **Started:** 2026-08-31T17:00:00Z
- **Completed:** 2026-08-31T17:19:00Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- **9/9 filas dispuestas, cero sin disponer y cero con doble disposición.** Claves ordinales `38-r01`..`38-r08` sobre las 8 filas del mapa en su orden de aparición (`38-01-01`, `38-01-02`, `38-02-01`, `38-02-02`, `38-03-01`, `38-03-02`, `38-04-01`, `38-05-01`) más `38-m01` sobre la única fila de `## Manual-Only Verifications`. El gate acotado entre `### Disposición por fila` y la línea de leyenda mide 9 filas y 9 tokens: 7 `VERIFIED-NOW`, 2 `VERIFIED-HISTORICALLY`, 0 `NOT-VERIFIABLE-RETROACTIVELY`.
- **Las 7 filas automatizadas se re-corrieron esta sesión, todas verdes con exit 0.** `-k optional_model_field` → `1 passed, 15 deselected in 0.01s`; `-k optional_literal_alias` → `1 passed, 15 deselected in 0.01s`; `-k puntas` → `5 passed, 21 deselected in 0.01s`; `-k round_trip` → `4 passed, 22 deselected in 0.01s`; `uv run mypy packages/iol-client` → `Success: no issues found in 31 source files`; el regenerador de snapshots exit 0 con salida byte-idéntica; matriz `test_surface_types_red.py` → `19 passed in 0.22s`. Los cuatro deselects son **parciales**, con pasados ≠ 0 en los cuatro casos — el guardia anti-vacuidad de la §6.2 no se disparó ninguna vez.
- **La fila que muta el árbol de trabajo (`38-r06`) se verificó, no se asumió.** `verification/regen_snapshots.py` reescribió los cuatro snapshots (`ambito-financiero-client` 10 símbolos, `iol-client` 19, `higyrus-client` 31, `matriz-client` 68) y la salida fue byte-idéntica: `git diff --stat verification/snapshots/iol-client-surface.txt` sin ninguna línea, `git diff --stat verification/snapshots/` sin ninguna línea, `git status --porcelain verification/` vacío. El invariante del criterio 1 se sostuvo.
- **Primera aplicación de R-06 del conjunto, con la evidencia leída del disco y transcrita literal.** `38-r08` y `38-m01` citan `human_verification[0].confirmed: 2026-08-29T22:04:57Z` del front-matter de `38-VERIFICATION.md`, cuyo `<expected>` enumera lo que el lector confirmó, más `38-CENSUS.md` en disco (426 líneas) y el cruce con `38-VERIFICATION.md` truth #4 y truth #14. **No se re-hizo la revisión del censo.**
- **Cero correcciones de comando.** Es la única de las cinco fases auditadas cuyo contrato de verificación corrió intacto: ningún selector muerto (R-02), ninguna ruta invalidada por la mudanza del milestone (R-03), ninguna celda de comando delegada al planner (R-04). La sección `### Correcciones de comando` dice `Ninguna.`
- **Primeras 3 filas `NOT ENFORCED` del conjunto**, con motivo escrito en la celda: `regen_snapshots.py` no aparece en `.github/workflows/ci.yml` (ni siquiera en el allowlist de 12 archivos de `ci.yml:81-92`), y las dos de revisión de documento no son automatizables por naturaleza. Son superficies **preexistentes**, no locks producidos por esta auditoría; su destino queda ruteado al edit consolidado de `ci.yml` de la Phase 45.
- **Invariante de criterio 1 sostenido de punta a punta**: `git diff --quiet v1.7 HEAD -- . ':(exclude).planning'` salió 0 antes de empezar, al cerrar cada tarea y al terminar. `ls verification/test_*.py | wc -l` sigue en 52. Cero archivos de test nuevos, cero ediciones a `packages/`, cero ediciones a `.github/`.

## Task Commits

1. **Task 1: Re-ejecutar las 7 filas automatizadas de la Phase 38 y reunir la evidencia histórica de las dos de revisión** — `0b9e9ec` (docs)
2. **Task 2: Escribir la sección de auditoría de la Phase 38 y transformar su front-matter** — `9f55cf9` (docs)

## Files Created/Modified

- `.planning/milestones/v1.7-phases/38-iol-client-auditor-a-de-higyrus-mbito-wallets/38-VALIDATION.md` — sección `## Validation Audit 2026-08-31` con los ocho bloques del contrato (párrafo de procedencia, par de encabezados en negrita, bloque de métricas, tabla de disposición de 9 filas y 4 columnas, `Ninguna.` en correcciones de comando, bloque de prosa sobre por qué las dos filas de revisión siguen siendo manuales, dos hallazgos de bookkeeping, escalaciones, veredicto + rationale); columna `Status` de las 8 filas del mapa actualizada (7 a `✅ (VN 2026-08-31)`, la de doc review a `⬜ histórico`) con la leyenda extendida; una línea nueva tildada en `## Validation Sign-Off` (las preexistentes quedan sin tildar, incluida `nyquist_compliant: true`); front-matter con `status: validated`, `nyquist_compliant: false`, `not_verifiable_retroactively: 0`, `audited_commit_sha`, `audit_baseline_head`, `frozen_tree_verified: true`, `updated`, `last_audited`.

## Decisions Made

- **La evidencia de las dos filas de revisión se cita, no se re-deriva.** La conducta declarada (`38-CENSUS.md` sin ninguna fila sin disposición, SC-2) ya fue verificada por un lector humano el 2026-08-29 con timestamp registrado, y el verificador de plan-time la cruzó con un re-derivado independiente por AST que coincidió número por número. Volver a abrir el censo hoy para juzgar si sus disposiciones son "reales o de relleno" produciría un juicio de 2026-08-31 sobre un artefacto de 2026-08-29 y lo presentaría como la verificación original — la sustitución que R-06 prohíbe y que el registro STRIDE del plan nombra como T-41-05-03.
- **Las dos filas de revisión se cuentan por separado aunque declaren la misma conducta.** El mapa la registra como `doc review` resuelta por `checkpoint:human-verify`; la tabla manual-only la registra otra vez con su justificación. El denominador de la §2.1 cuenta filas, no conductas: fusionarlas dejaría una fila del artefacto sin disposición y rompería el criterio 2.
- **Ningún `✅` sobre la fila `doc review`.** `38-05-01` recibe `⬜ histórico`. §5.5 del contrato lo prohíbe explícitamente: un ✅ sobre una fila manual es staleness laundering aunque la disposición sea correcta (T-41-05-04).
- **`nyquist_compliant` se queda en `false` por la condición (b) de R-09.** La condición (c) se cumple sin reservas —cero correcciones de cualquier tipo—, pero la fase retiene dos filas `VERIFIED-HISTORICALLY`, y (a) falla junto con (b) por las mismas dos: 7 de 9 disponen `VERIFIED-NOW` plano. El rationale escrito en el artefacto aclara qué **no** significa ese `false`: no es duda sobre la conducta —que está mejor documentada que casi ninguna otra de la fase—, sino la constatación de que dos de nueve filas dependen de una lectura humana que no se re-deriva y una tercera sólo se comprueba corriendo a mano un script que CI no ejecuta.
- **`not_verifiable_retroactively: 0` se escribe explícito.** La fase no conserva ningún ítem de esa clase; el cero afirma eso, mientras que su ausencia no afirmaría nada (§4.3).
- **Ni las celdas `File Exists` ni `wave_0_complete` se tocan.** Su contradicción con la realidad medida es el hallazgo; corregirlas lo borraría.

## Deviations from Plan

Una desviación, de forma del comando de verificación, sin impacto en ninguna disposición.

**1. [Rule 3 — comando de verificación bloqueado por estado preexistente] `test -z "$(git status --porcelain)"` re-acotado con `':(exclude).planning'`**

- **Found during:** Task 1 (ejecución del bloque `<verify><automated>`)
- **Issue:** El bloque de verificación de la Task 1 exige `test -z "$(git status --porcelain)"` **después** de correr el regenerador de snapshots, para probar que el script no ensucia el árbol. Corrido tal cual, el comando falla siempre por una razón ajena: `.planning/research/.cache/3f83a89c…json` figura como untracked desde antes de este plan (lo dejó la sesión de planning de la Phase 41; el plan 41-04 lo registró con el mismo diagnóstico). Es exactamente el mismo modo de falla que la §1.2 del contrato resuelve para la prueba de identidad del árbol, y por el mismo motivo: `.planning/` churnea legítimamente durante toda la fase.
- **Fix:** Se ejecutó `test -z "$(git status --porcelain -- . ':(exclude).planning')"`, que es la forma que mide lo que la fila afirma (el regenerador no tocó nada fuera de `.planning/`), y se lo complementó con los dos controles que el plan ya pedía sin ambigüedad y que **sí** se corrieron literales: `git status --porcelain verification/` → vacío, y `git diff --stat verification/snapshots/` → sin ninguna línea. El archivo untracked no se commiteó ni se borró: no es producto de este plan.
- **Files modified:** ninguno (cambio de forma del comando de verificación, no del artefacto)
- **Verification:** Cadena completa de la Task 1 con el pathspec acotado → exit 0; `git status --porcelain verification/` vacío; `git diff --quiet v1.7 HEAD -- . ':(exclude).planning'` → exit 0.
- **Committed in:** —

---

**Total deviations:** 1 auto-fixed (1 corrección de forma de comando de verificación)
**Impact on plan:** Ninguna disposición cambia. El reparto medido (7 / 2 / 0) coincide **exactamente** con la §2.4 del contrato, y también el conteo esperado de 3 filas `NOT ENFORCED` y de 0 correcciones de comando. Cero scope creep.

## Issues Encountered

- **Ninguna fila de selección vacía en esta fase**, tal como `41-RESEARCH.md` había medido. Las dos correcciones R-02 autorizadas en toda la Phase 41 siguen siendo `37-r11` (consumida por el plan 41-04) y `39-r03` (pendiente para el 41-06).
- **Pre-existente, fuera de alcance:** `.planning/research/.cache/3f83a89c…json` sigue untracked desde la sesión de planning. No se commiteó ni se borró — no es producto de este plan y tocarlo sería alcance ajeno. Tercer plan consecutivo que lo registra con el mismo diagnóstico.
- **`uv run pytest packages/iol-client -q` da hoy `311 passed`, no los `293 passed` que registró `38-VERIFICATION.md` truth #9.** No es una discrepancia: la Phase 39 agregó tests al mismo paquete dentro de v1.7, y el árbol congelado que se audita es el del tag, posterior a ambas. Las siete filas del mapa de la Phase 38 son la unidad de conteo, no el total del paquete; el número se transcribió como métrica de suite de la sesión, sin tratarlo como hallazgo.

## User Setup Required

None — la auditoría no toca servicios externos, no abre red y no lee ningún `.env`. Se revisó el diff de los dos commits buscando `://`, `Bearer`, `password` y formas de host/usuario: cero coincidencias.

## Next Phase Readiness

- **Cuatro de las cinco fases auditadas cerradas:** 35 (13 filas), 36 (11), 37 (14) y 38 (9) = **47 de las 62** filas del denominador dispuestas. Queda la Phase 39 (15 filas), la más pesada del conjunto: 10 automatizadas, 1 con selector muerto (`39-r03`, la segunda y última corrección R-02 autorizada), 1 `VERIFIED-HISTORICALLY` (`39-r11`) y 4 `NOT-VERIFIABLE-RETROACTIVELY` (`39-m01`..`39-m04`, resolución de OQ#1 en la §3.1 del contrato).
- **El ejecutor del 41-06 hereda el patrón de R-06 ya aplicado**: citar el artefacto fechado con su ruta y su fecha, sin re-derivar. Para `39-r11` el artefacto es `39-CENSUS.md`, citado por `39-VERIFICATION.md` truth #8. Para las cuatro filas manual-only, la celda `Evidence` **no** queda vacía: nombra los cuatro `run-evidence/*.json` del 2026-08-29, `39-07-SUMMARY.md`, `39-CENSUS.md` § "Casos límite de D-12" y el sign-off del operador, calificados como evidencia parcial insuficiente para re-derivar la conducta.
- **La predicción de la §4.2 del contrato se confirma por evidencia también para la Phase 38**: R-09 no se satisface, `nyquist_compliant` no cambia. Cuatro de cuatro hasta acá; cero flags movidos en toda la fase.
- **Nota para el ejecutor del cierre (41-07):** el gate aritmético acotado entre `### Disposición por fila` y `*Disposiciones:` mide en este archivo 9 filas y 9 tokens (7 `VERIFIED-NOW`, 2 `VERIFIED-HISTORICALLY`, 0 `NOT-VERIFIABLE-RETROACTIVELY`), con **3** `NOT ENFORCED` y 0 celdas de evidencia vacua. Las líneas de la tabla empiezan con `| 38-rNN · …` y `| 38-m01 · …`, sin prefijo. Acumulado de `NOT ENFORCED` del conjunto tras cuatro fases: 35 aporta la fila de `surface_parity.py` como script, 36 y 37 aportan 0, y 38 aporta 3.

## Self-Check: PASSED

- `.planning/milestones/v1.7-phases/38-iol-client-auditor-a-de-higyrus-mbito-wallets/38-VALIDATION.md` — existe, con `## Validation Audit 2026-08-31`
- `.planning/phases/41-validaci-n-nyquist-retroactiva-de-v1-7/41-05-SUMMARY.md` — existe
- Commits `0b9e9ec` y `9f55cf9` — presentes en `git log`
- Gates: 9 filas / 9 tokens (7 / 2 / 0) / 3 `NOT ENFORCED` / 0 evidencia vacua / 9 claves únicas / 0 correcciones de comando; front-matter `status: validated` ×1, `nyquist_compliant: false` ×1, `not_verifiable_retroactively: 0` ×1, `audited_commit_sha: 37a83fe…` ×1, `audit_baseline_head` de 40 hex ×1; `- [x] … nyquist_compliant: true` ×0
- `git diff --quiet v1.7 HEAD -- . ':(exclude).planning'` → exit 0; `git status --porcelain verification/` vacío; `ls verification/test_*.py | wc -l` → 52

---
*Phase: 41-validaci-n-nyquist-retroactiva-de-v1-7*
*Completed: 2026-08-31*
