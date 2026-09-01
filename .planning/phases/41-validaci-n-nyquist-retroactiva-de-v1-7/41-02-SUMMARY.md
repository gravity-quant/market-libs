---
phase: 41-validaci-n-nyquist-retroactiva-de-v1-7
plan: 02
subsystem: testing
tags: [nyquist-audit, validation, retroactive-audit, tdd-red, pytest, mypy, ruff, ci-enforcement]

# Dependency graph
requires:
  - phase: 41-01
    provides: "41-AUDIT-CONTRACT.md — denominador 62, claves de fila {N}-r{NN}/{N}-m{NN}, reglas R-01..R-09, esqueleto de ocho bloques, higiene de evidencia, tabla de lookup de CI, y los dos SHA de atribución"
  - phase: 35-fundaci-n-null-object-bool-pol-tica-del-walker
    provides: "los cinco 35-0N-PLAN.md con sus 12 bloques <verify><automated>, 35-01-SUMMARY.md, 35-VERIFICATION.md, 35-RETIRED-TRIPLES.md"
provides:
  - "35-VALIDATION.md con el ## Per-Task Verification Map reconstruido: 12 filas reales (35-01-01..35-05-02) más la fila placeholder conservada y marcada como superada"
  - "Sección ## Validation Audit 2026-08-31 con 13 disposiciones (12 VERIFIED-NOW / 1 VERIFIED-HISTORICALLY / 0 NOT-VERIFIABLE-RETROACTIVELY), 4 columnas incl. superficie de enforcement de CI"
  - "Front-matter de la Phase 35 transformado: status validated, not_verifiable_retroactively: 0, ambos SHA de atribución, frozen_tree_verified"
  - "Precedente de forma para los cuatro artefactos hermanos de la Wave 2 (41-03..41-06)"
affects: [41-03, 41-04, 41-05, 41-06, 41-07, audit-milestone]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Reconstrucción de mapa de verificación desde bloques <verify><automated>, con la fila placeholder conservada como evidencia del hueco"
    - "Disposición R-05: un paso RED de TDD se dispone históricamente, nunca se re-ejecuta ni se 'arregla'"
    - "Disposición R-03: la ruta se corrige en el comando ejecutado, no en el archivo de plan histórico"
    - "Celda de enforcement de CI parcial: una fila con 9 tramos se desglosa en enforced / NOT ENFORCED en vez de colapsar a un veredicto"

key-files:
  created: []
  modified:
    - .planning/milestones/v1.7-phases/35-fundaci-n-null-object-bool-pol-tica-del-walker/35-VALIDATION.md

key-decisions:
  - "El paso RED de TDD 35-r01 se dispone VERIFIED-HISTORICALLY (R-05) sin re-ejecutarlo: su cadena lleva `&& !` sobre tres tests que hoy pasan, así que sale 1 por diseño; leerlo como rojo llevaría a 'arreglar' un test que está bien."
  - "Las dos rutas muertas de 35-02 (35-r04, 35-r05) se corrigen en el comando EJECUTADO y se disponen VERIFIED-NOW (ruta corregida) (R-03); 35-02-PLAN.md queda sin tocar como registro histórico y la ruta stale se nombra en Hallazgos de bookkeeping."
  - "La fila manual-only de identidad byte-a-byte de snapshots (35-m01) se dispone VERIFIED-NOW (R-01), no históricamente: sus Test Instructions son un comando ejecutable, no un checkpoint humano; re-corrido esta sesión con resultado byte-idéntico y árbol limpio."
  - "nyquist_compliant se queda en false con rationale escrito: R-09 falla por (b) — una fila VERIFIED-HISTORICALLY — y por (c) — dos calificadores de corrección. Cero flags flipeados."
  - "La celda de enforcement de 35-r12 no colapsa a un solo veredicto: los tres gates de tools/ y pytest packages sí corren en CI; tools/surface_parity.py COMO SCRIPT y regen_snapshots.py no."

patterns-established:
  - "Guardia anti-vacuidad verificada mecánicamente: ninguna celda de evidencia menciona tests descartados sin mencionar también tests pasados (gate awk devuelve 0 líneas)"
  - "Recorte de salida a línea de resumen antes de commitear, con escaneo previo del diff buscando ://, @, token, password, Bearer"
  - "Re-verificación del invariante de árbol congelado (`git diff --quiet v1.7 HEAD -- . ':(exclude).planning'`) al inicio del plan y al final de cada tarea"

requirements-completed: [NYQ-01]

# Metrics
duration: 22min
completed: 2026-08-31
status: complete
---

# Phase 41 Plan 02: Auditoría Nyquist retroactiva de la Phase 35 Summary

**Las 13 filas de la Phase 35 quedan dispuestas con evidencia nombrada — el mapa que shipeó con una sola fila placeholder se reconstruyó en 12 filas reales desde los cinco archivos de plan, se re-ejecutaron 11 de ellas más la manual-only contra el árbol congelado de v1.7 (todas verdes), el único paso RED de TDD se dispuso históricamente en vez de reportarse como rojo, y `nyquist_compliant` sigue en `false` por evidencia medida.**

## Performance

- **Duration:** ~22 min
- **Started:** 2026-08-31T16:30Z (aprox.)
- **Completed:** 2026-08-31T16:52Z (aprox.)
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- **La fila placeholder deja de ser la unidad de disposición.** `## Per-Task Verification Map` shipeó con una única fila `(filled by planner)`; disponerla habría certificado "1/1, 100%" sin auditar nada. Se reconstruyeron sus **12** bloques `<verify><automated>` reales desde `35-01..05-PLAN.md` (3 + 2 + 2 + 3 + 2, medido con `grep -c`), con Task ID único `35-01-01`..`35-05-02`, wave y requirement leídos del front-matter de cada plan, y el comando transcrito literal. La placeholder se **conserva**, marcada como superada — borrarla habría borrado la evidencia del hueco.
- **13 disposiciones, exactamente una por fila:** 12 `VERIFIED-NOW` (de las cuales 2 con `(ruta corregida)`) + 1 `VERIFIED-HISTORICALLY` + 0 `NOT-VERIFIABLE-RETROACTIVELY`. Coincide exactamente con la distribución esperada de la §2.4 del contrato.
- **Los tres comandos no re-ejecutables tal como fueron escritos quedaron tratados por regla explícita, no reportados como rojo.** El paso RED (`35-r01`) por R-05, citando `35-01-SUMMARY.md` / commit `ece3a3c` / verdad #2 de `35-VERIFICATION.md`; las dos rutas muertas (`35-r04`, `35-r05`) por R-03, con ambos comandos —viejo y corregido— transcritos en la celda de evidencia.
- **Once filas re-ejecutadas verdes sobre el árbol congelado**, incluidas las dos más caras: `35-r11` → `2152 passed, 1 deselected in 86.96s` y `35-r12` (gate de fase de 9 tramos, incluida la regeneración de snapshots) → todos exit 0. No se sustituyeron por versiones reducidas.
- **Cero contaminación del árbol.** `verification/regen_snapshots.py` se corrió dos veces (en `35-r12` y en `35-m01`); las cuatro salidas fueron byte-idénticas, `git status --porcelain verification/` quedó vacío y `ls verification/test_*.py | wc -l` sigue en **52**. El invariante del criterio 1 (`git diff --quiet v1.7 HEAD -- . ':(exclude).planning'` → 0) se re-verificó al inicio y al cierre de cada tarea.
- **Cinco filas `NOT ENFORCED` en CI, con precisión.** La celda de `35-r12` no colapsa a un solo veredicto: nombra los cuatro tramos que sí corren (`ci.yml:55`, `:60`, `:66`, job `test` `:133-166`) y separa `tools/surface_parity.py` **como script** de los seis `packages/*/tests/test_surface_parity.py`, que sí corren.
- **Cuatro hallazgos de bookkeeping nombrados, ninguno corregido en silencio.**

## Task Commits

1. **Task 1: Reconstruir el mapa de verificación de la Phase 35 — 12 filas desde los cinco archivos de plan** — `c55b5b9` (docs)
2. **Task 2: Re-ejecutar las 10 filas re-ejecutables, disponer las 13, y escribir la sección de auditoría con el front-matter transformado** — `1ee48df` (docs)

## Files Created/Modified

- `.planning/milestones/v1.7-phases/35-fundaci-n-null-object-bool-pol-tica-del-walker/35-VALIDATION.md` — mapa de verificación reconstruido (12 filas + placeholder conservada), nota de reconstrucción, columna `Status` actualizada y leyenda extendida con los dos valores nuevos, sección `## Validation Audit 2026-08-31` con los ocho bloques del contrato, línea nueva tildada en `## Validation Sign-Off`, y front-matter transformado.

**Cero archivos creados.** Cero locks nuevos en `verification/`. Cero ediciones a `.github/workflows/ci.yml`. Cero ediciones a los cinco `35-0N-PLAN.md`. Cero fuente de producto tocada.

## Decisions Made

Todas las decisiones estaban pre-tomadas por `41-AUDIT-CONTRACT.md`; el plan no requirió juicio propio del ejecutor. Las aplicadas:

- **`35-r01` → `VERIFIED-HISTORICALLY` (R-05).** El escaneo de negaciones previo a cualquier ejecución encontró exactamente una fila con `&& !` — la esperada. Los tres tests negados (`falsy_when_empty`, `truthy_when_populated`, `empty_emits_nothing`) hoy pasan, así que la cadena sale 1 por diseño. No se ejecutó y no se tocó ningún test.
- **`35-r04` / `35-r05` → `VERIFIED-NOW (ruta corregida)` (R-03).** Confirmado que `.planning/phases/35-…/35-RETIRED-TRIPLES.md` ya no existe (`test -f` → falso) y que el archivo archivado tiene **58** filas `^| `, por encima del piso `-ge 35`. Los tres literales de `35-r05` están presentes (9 / 4 / 23 hits).
- **`35-m01` → `VERIFIED-NOW` (R-01), no históricamente.** Sus `Test Instructions` son un comando ejecutable; se re-corrió esta sesión. No se le puso `✅` en ninguna columna `Status` porque la tabla `## Manual-Only Verifications` no tiene esa columna — el warning sign de Pitfall 4 no aplica.
- **`nyquist_compliant` sin cambiar, con rationale escrito.** R-09 falla por (b) y por (c). Se escribió el párrafo modelo tomado de la prosa de `07-VALIDATION.md`, reformulado como `nyquist_compliant sigue en false porque …`. Las seis casillas preexistentes del sign-off quedaron sin tildar, en particular `nyquist_compliant: true`.
- **`Test Type` compuesto para las cadenas de paquete.** El vocabulario del repo (`unit`, `static`, `snapshot`, `unit (RED fixture)`, `doc review`) no tiene un token para "pytest + mypy + ruff en una cadena". Se compuso desde ese vocabulario (`unit + static`, `unit + static + snapshot`) en vez de inventar un token nuevo. `unit (RED fixture)` aparece exactamente una vez, como exige el criterio.

## Deviations from Plan

Ninguna — el plan se ejecutó exactamente como fue escrito. Cero deviation rules disparadas, cero auto-fixes, cero escalaciones.

**Divergencias de medición contra los valores esperados del plan: ninguna.** Los cuatro números que el plan mandaba comparar coincidieron con lo medido:

| Valor | Esperado por el plan | Medido | ¿Coincide? |
|-------|----------------------|--------|------------|
| Bloques `<verify><automated>` en los cinco planes | 12 (D-05 decía "~14") | 12 | sí |
| Reparto de disposiciones | 12 VN / 1 VH / 0 NVR | 12 / 1 / 0 | sí |
| Filas `NOT ENFORCED` en CI | 5 | 5 | sí |
| Archivos de test nuevos | 0 | 0 | sí |

Las líneas de `ci.yml` citadas por la §7 del contrato se re-verificaron una por una en HEAD (`:36-39` ruff, `:55` / `:60` / `:66` los tres gates de `tools/`, `:122-123` mypy global, `:133-166` job `test`) — todas correctas. Se confirmó además por grep que `surface_parity`, `regen_snapshots` y `test_null_object` **no** aparecen en `ci.yml`, que es lo que sostiene las cinco celdas `NOT ENFORCED`.

## Issues Encountered

- **El `grep -c '^| ' ` original contiene un pipe literal**, que rompería la tabla markdown al transcribir el comando de `35-r04` a una celda. Se transcribió con el escape estándar de markdown `\|` y se dejó una nota explícita en el mapa aclarando que el `\|` es sólo el escape, no parte del comando original. La transcripción sigue siendo literal en todo lo demás.
- **`HEAD` de esta sesión (`79f23a3`) no es el `audit_baseline_head` del contrato (`6dd83cf`).** Esto es esperado y correcto: el contrato (§1.1) fija que el valor se captura **una sola vez** en 41-01 y los planes de la Wave 2 lo **copian literal**, precisamente para que los seis artefactos no declaren seis HEADs distintos. Se copió el literal. Lo que sí se re-verificó en vivo fue el invariante que importa: `git diff --quiet v1.7 HEAD -- . ':(exclude).planning'` → exit 0, y `git rev-parse v1.7^{commit}` → `37a83fe…`, idéntico al declarado.

## Deferred Items

- **`.planning/research/.cache/3f83a89c…json` sin trackear.** Presente en el árbol desde antes de que este plan arrancara; es un artefacto de caché del researcher, fuera del alcance de este plan (que sólo modifica `35-VALIDATION.md`). No se commiteó ni se gitignoreó — commitear caché o tocar `.gitignore` habría sido scope creep en una fase cuyo invariante central es no mover nada fuera de `.planning/`. Candidato a `.gitignore` en el barrido de harness de la Phase 45.
- **Los dos hallazgos de bookkeeping stale de `## Test Infrastructure`** (pytest 8.3 declarado vs 9.0.3 real; 1749 tests declarados vs 2152 reales) quedan **nombrados, no corregidos**, por instrucción explícita del contrato. Si alguna fase futura decide refrescar esa tabla, la constancia del cambio ya está escrita.

## User Setup Required

None — la auditoría corre enteramente offline. Ningún comando de este plan abrió un socket, leyó un `.env` ni invocó un gestor de paquetes (R-08 respetada).

## Next Phase Readiness

- **Los cuatro planes hermanos de la Wave 2 (41-03..41-06) tienen ahora un precedente de forma concreto en disco**, además del esqueleto del contrato: colocación de la sección tras `## Validation Sign-Off`, orden de los ocho bloques con el bloque de métricas **antes** de `### Disposición por fila` (imprescindible para que el gate aritmético de 41-07 no doble-cuente), forma de la celda `Row` (`{clave} · {Task ID}`), y forma de la celda de enforcement parcial.
- **La aritmética del cierre avanza 13 de 62.** 41-07 sumará las cinco tablas; la de la Phase 35 aporta 13 filas que el gate `^\| 35-[rm][0-9]` acotado entre `### Disposición por fila` y `*Disposiciones:` cuenta correctamente (verificado).
- **La línea base del criterio 4 sigue intacta:** 52 archivos `verification/test_*.py`, `git status --porcelain verification/` vacío. Un 53 en el cierre seguiría siendo la señal de que la contingencia de D-08 se disparó — y no se disparó aquí.
- **Sin blockers.** El árbol de v1.7 sigue congelado; la ventana de validez de la atribución sigue abierta para 41-03..41-07.

## Self-Check: PASSED

- `.planning/milestones/v1.7-phases/35-fundaci-n-null-object-bool-pol-tica-del-walker/35-VALIDATION.md` — FOUND
- Commit `c55b5b9` (Task 1) — FOUND
- Commit `1ee48df` (Task 2) — FOUND
- Gate de la tarea 1 (12 bloques `<automated>`, 12 filas, placeholder viva, árbol congelado) — exit 0
- Gate de la tarea 2 (13 filas, suma de tokens 13, front-matter completo, literal de D-08, `verification/` limpio, árbol congelado) — exit 0

---
*Phase: 41-validaci-n-nyquist-retroactiva-de-v1-7*
*Completed: 2026-08-31*
