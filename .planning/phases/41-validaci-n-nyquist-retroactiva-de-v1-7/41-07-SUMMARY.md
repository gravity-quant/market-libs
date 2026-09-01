---
phase: 41-validaci-n-nyquist-retroactiva-de-v1-7
plan: 07
subsystem: testing
tags: [nyquist, validation-audit, cross-phase-rollup, ci-enforcement, scope-containment, documentation]

# Dependency graph
requires:
  - phase: 41-01
    provides: 41-AUDIT-CONTRACT.md — denominador 62, claves ordinales, R-01..R-09, mapa de enforcement de CI, línea base de 52 locks
  - phase: 41-02..41-06
    provides: las cinco secciones "## Validation Audit 2026-08-31" de los {N}-VALIDATION.md de v1.7 (62 filas dispuestas)
provides:
  - "41-ROLLUP.md — índice secundario cross-fase (281 líneas) con la aritmética derivada, la tabla de enforcement y la declaración inerte"
  - "Criterio 2 cerrado: 62 filas, suma por fase igual al conteo de filas en las cinco, 54 / 4 / 4"
  - "Criterio 3 probado sobre el conjunto: 0 flags en true, 5 en status validated, marcador presente en los 5"
  - "Criterio 4 cerrado: 0 locks nuevos; los 40 preexistentes sin enrolar declarados inertes por escrito"
  - "Criterio 5 cerrado: exactamente 5 artefactos de v1.7 tocados, 0 fuera de alcance, fila de alcance excluido byte-intacta"
  - "Criterio 1 cerrado al final de la ventana: árbol de fuente de v1.7 sin cambios"
  - "41-VALIDATION.md auto-dispuesto con la misma vara (D-10): 16 filas, status validated, nyquist_compliant false por evidencia"
affects: [phase-42-live-recheck, phase-45-ci-enrollment, audit-milestone-v1-8]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Rollup cross-fase como índice secundario explícitamente no-autoritativo (D-01), con la unidad de conteo fijada antes de la primera suma"
    - "Prueba conjunta del criterio 2 por igualdad suma-de-tokens == conteo-de-filas, aplicada por fase y no sólo al total"
    - "Declaración inerte formal de locks preexistentes con ruteo nombrado a una fase futura, en vez de reportar cobertura total"

key-files:
  created:
    - .planning/phases/41-validaci-n-nyquist-retroactiva-de-v1-7/41-ROLLUP.md
  modified:
    - .planning/phases/41-validaci-n-nyquist-retroactiva-de-v1-7/41-VALIDATION.md
    - .planning/research/.cache/3f83a89c4483fba443dc124a6f54700eb5308d922db186ed6f11a8c73a319a15.json

key-decisions:
  - "El gate de inmutabilidad de REQUIREMENTS.md del criterio 5 se sustituye por un hash byte-a-byte de la fila de alcance excluido más un conteo de líneas cambiadas: la cláusula as-written es insatisfacible porque el propio seam de estado de GSD (requirements mark-complete) edita ese archivo dentro de la fase"
  - "El denominador de auto-disposición de la Phase 41 es 16, no 14: se ejecutan los verificadores corregidos, según la corrección ya registrada por 41-01 en 41-AUDIT-CONTRACT.md §2.5"
  - "nyquist_compliant de la propia Phase 41 se queda en false por evidencia medida contra R-09 (fallan (a) y (c): 3 de 16 filas llevan calificador de corrección), no por decreto ni por simetría con las cinco auditadas"
  - "Las filas de enforcement mixto se describen en prosa en vez de llevar el literal NOT ENFORCED, para que el conteo greppeable de la métrica (12) siga siendo exacto"
  - "La falla pre-existente de test_main_matriz_login_fail_uniformity.py se nombra como hallazgo de bookkeeping y NO se arregla: hacerlo violaría el invariante del criterio 1"

patterns-established:
  - "Párrafo de tesis que nombra la lectura errónea más probable del propio documento, antes de cualquier número (analog de forma tomado de 39-CENSUS.md)"
  - "Corrección de gate en vez de corrección de artefacto: cuando un verificador es insatisfacible por construcción, se sustituye por uno que mida la misma intención y se registra la sustitución en la tabla de correcciones"

requirements-completed: [NYQ-01]

# Metrics
duration: 23min
completed: 2026-08-31
status: complete
---

# Phase 41 Plan 07: Cierre cross-fase y gates finales — Summary

**Las 62 filas de las cinco fases de v1.7 cierran contra su denominador con 54 verificadas ahora, 4 históricas y 4 no re-verificables, cero flags movidos a `true`, cero locks nuevos, los 40 preexistentes sin enrolar declarados inertes y ruteados a la Phase 45, y el árbol de fuente de v1.7 sin cambiar ni un byte de punta a punta.**

## Performance

- **Duration:** ~23 min
- **Started:** 2026-08-31T16:59:54Z
- **Tasks:** 3
- **Files modified:** 3 (1 creado, 2 modificados)
- **Commits:** 3

## Accomplishments

- **Criterio 2 cerrado con aritmética derivada, no declarada.** Los cinco conteos se extraen acotando cada tabla entre `### Disposición por fila` y su línea de leyenda, por fase: 13 / 11 / 14 / 9 / 15 = **62**, con reparto **54 `VERIFIED-NOW` / 4 `VERIFIED-HISTORICALLY` / 4 `NOT-VERIFIABLE-RETROACTIVELY`**. En las cinco, la suma de los tres tokens iguala exactamente el conteo de filas — lo que prueba de una vez *cero filas sin disponer* (la suma sería menor) y *cero filas con doble disposición* (sería mayor). El gate se aplica **por fase**, no sólo al total: dos errores de signo opuesto en fases distintas se cancelarían en un gate global.
- **Anti-vacuidad en cero.** Sobre los cinco rangos acotados, las celdas que reportan descarte sin reportar ningún test ejecutado suman **0**. Las que descartan parcialmente (`2 passed, 72 deselected`) llevan conteo de pasados distinto de cero, que es lo que el contrato exige.
- **Criterio 3 probado sobre el conjunto.** 0 de 5 archivos con `nyquist_compliant: true`; 5 de 5 en `status: validated`; la clave `not_verifiable_retroactively` presente en los cinco con un solo valor distinto de cero (Phase 39 → 4); 0 casillas de sign-off tildadas retroactivamente sobre el flag; un único valor de `audited_commit_sha`, un único `audit_baseline_head` y un único `frozen_tree_verified` en los cinco. La tabla de R-09 del rollup muestra *por qué* falla cada fase, no sólo que falla.
- **Criterio 4 cerrado en sus dos mitades.** Locks nuevos: **0** (`git status --porcelain verification/` vacío, 52 archivos exactamente como en la línea base de `41-AUDIT-CONTRACT.md § 1.5`, `ci.yml` sin cambios desde el baseline). Locks preexistentes: **declaración inerte formal** de los 40 de 52 que no están en el allowlist explícito del job `lint` (`ci.yml:81-92`), con su enrolamiento ruteado por escrito al edit consolidado de la **Phase 45**, citando la precondición cross-fase ya registrada en `REQUIREMENTS.md § Traceability` y los requisitos HARN-03 / HARN-04 que la absorben.
- **Criterio 5 probado con tres gates, no asumido.** Exactamente **5** artefactos de validación de v1.7 en el diff desde el baseline; **6** rutas terminadas en `VALIDATION.md` en total (los cinco más el `41-VALIDATION.md` de esta fase); **0** de las seis fases fuera de alcance (18, 25, 29, 30, 32, 33) tocadas; la fila `NYQUIST-32-33` de `REQUIREMENTS.md § Out of Scope` con hash byte-a-byte idéntico al del commit de baseline. Cero archivos fuera de `.planning/` en todo el diff acumulado de la fase.
- **Criterio 1 cerrado al final de la ventana.** `git diff --quiet v1.7 HEAD -- . ':(exclude).planning'` sale **0** después de que el último de los cinco artefactos quedó escrito y commiteado. Ése es literalmente el momento que el criterio nombra.
- **La Phase 41 se auto-dispuso con su propia vara (D-10), y el resultado es incómodo a propósito.** 16 filas (`41-r01`..`41-r16`, una por tarea real de los siete planes), 16 `VERIFIED-NOW`, cero históricas, cero no re-verificables — pero **3 con calificador de corrección**, de modo que R-09 falla por (a) y (c) y `nyquist_compliant` se queda en `false`. Dos de esas tres correcciones existen porque el planner de esta misma fase declaró un denominador mal sumado, y la tercera porque escribió un gate que su propio workflow de ejecución invalida.
- **El hallazgo de enforcement queda escrito, no maquillado.** 13 de las 62 filas auditadas (21 %) no tienen ninguna superficie de CI; 12 de las 16 filas de la propia Phase 41 tampoco, porque son aserciones de shell sobre estado de archivo. Escribir eso es más honesto que inventarles una pata de pipeline.

## Task Commits

1. **Task 1: Cerrar la aritmética del criterio 2 y probar el criterio 3 sobre el conjunto de cinco** — gate de lectura, **cero correcciones necesarias**, sin commit propio (no modificó ningún archivo; los resultados alimentan `41-ROLLUP.md`)
2. **Task 2: Probar los criterios 4 y 5 y re-verificar el árbol congelado** — `8cfc107` (docs) + `a284ab2` (docs, fix de árbol limpio)
3. **Task 3: Auto-disponer la Phase 41 con la misma vara que las cinco auditadas** — `fe060a5` (docs)

## Files Created/Modified

- `.planning/phases/41-validaci-n-nyquist-retroactiva-de-v1-7/41-ROLLUP.md` — **nuevo**, 281 líneas. Párrafo de tesis sobre cómo se lee mal el "54 de 62"; unidad de conteo fijada antes de la primera suma con los denominadores 51 y 25 rechazados por su número; aritmética por fase y cross-fase; tabla de R-09 con la razón de falla de cada fase; gates de front-matter del criterio 3; tabla de enforcement (13 de 62 filas sin cobertura de CI, y los tres números 52 / 12 / 40 del árbol de locks); declaración inerte con ruteo a la Phase 45; contención de alcance con los tres gates; cierre del invariante del criterio 1; veredicto cross-fase que separa lo cerrado de lo que queda abierto.
- `.planning/phases/41-validaci-n-nyquist-retroactiva-de-v1-7/41-VALIDATION.md` — **modificado**. Sección `## Validation Audit 2026-08-31` con las 16 filas, tabla de correcciones de comando, cuatro hallazgos de bookkeeping, evaluación escrita de R-09 y veredicto PARTIAL. Front-matter: `status: draft → validated`, `not_verifiable_retroactively: 0`, los dos SHA de atribución, `frozen_tree_verified: true`, `updated` y `last_audited`. Columna `Status` del mapa a `✅ (VN 2026-08-31)` en las 16 filas (ninguna es de tipo manual ni de revisión de documento, así que el ✅ es admisible). Casillas de sign-off preexistentes **sin tildar**, con una línea nueva agregada al final. Nota de auto-disposición D-10 actualizada de "pendiente" a "resuelta".
- `.planning/research/.cache/3f83a89c…json` — **trackeado**. Entrada de caché de research generada durante esta fase que había quedado fuera del índice; sus 16 hermanas ya estaban en git.

## Decisions Made

Ver `key-decisions` en el front-matter. Las dos de mayor consecuencia:

1. **Cuando un verificador es insatisfacible por construcción, se corrige el verificador y se registra la sustitución — nunca se corrige el artefacto para que el verificador pase.** La cláusula `git diff --quiet <baseline> HEAD -- .planning/REQUIREMENTS.md` no puede pasar porque el propio workflow de ejecución de GSD obliga a correr `requirements mark-complete` al cerrar cada plan, y eso edita ese archivo. Sustituirla por un hash de la fila que el criterio 5 realmente protege mide la misma intención sin pedirle a la fase que se salte su propio state seam. La alternativa —revertir la marca de NYQ-01 para que el gate pase— habría sido exactamente el laundering que esta fase existe para prevenir.
2. **El `nyquist_compliant` de la propia Phase 41 se calculó, no se asumió.** Habría sido cómodo dejarlo en `false` "por simetría con las cinco". Se evaluó R-09 condición por condición y se escribió el resultado con su razón: falla por (a) y (c), con las tres filas calificadas nombradas. Si hubiese salido `true`, habría habido que escribir `true`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Regla 1 - Bug] El gate de inmutabilidad de `REQUIREMENTS.md` del criterio 5 es insatisfacible por construcción**

- **Found during:** Task 2
- **Issue:** El bloque `<verify><automated>` de Task 2 exige `git diff --quiet <baseline> HEAD -- .planning/REQUIREMENTS.md` (exit 0). Sale **1**: el archivo cambió en dos líneas desde el HEAD de baseline. Las dos líneas son la casilla de `NYQ-01` (`- [ ]` → `- [x]`) y su celda de la tabla de trazabilidad (`Pending` → `Complete`), escritas por el seam `requirements mark-complete` que el propio workflow de ejecución obliga a correr al cerrar cada plan de la fase. No es un ensanchamiento de alcance: es un gate escrito sin contemplar el bookkeeping del workflow que lo ejecuta.
- **Fix:** La cláusula se sustituye por dos que miden la intención real del criterio 5 — (a) hash byte-a-byte de la fila `NYQUIST-32-33` de `## Out of Scope` contra la misma fila en el commit de baseline: **idéntico**; (b) conteo de líneas cambiadas en el diff acotado del archivo: exactamente **2**, ambas de estado de `NYQ-01`. El resto del bloque se corrió sin cambios. Registrado en la tabla de correcciones de `41-VALIDATION.md` (fila `41-r15`) y como hallazgo de bookkeeping.
- **Files modified:** ninguno (corrección de gate, no de artefacto)
- **Verification:** cadena corregida completa → `exit 0`
- **Committed in:** `8cfc107` (el rollup documenta el gate 3 del criterio 5) y `fe060a5` (la corrección registrada)

**2. [Regla 3 - Blocking] Una entrada de caché de research sin trackear rompía los gates de árbol limpio**

- **Found during:** Task 3 (re-ejecución del bloque de `41-05` Task 1)
- **Issue:** `git status --porcelain` no estaba vacío: `.planning/research/.cache/3f83a89c…json`, generada durante la fase de research de la Phase 41 (timestamp 12:21 de hoy), había quedado fuera del índice. Hacía fallar la cláusula `test -z "$(git status --porcelain)"` de `41-05` Task 1 y de `41-07` Task 3 por una razón ajena a lo que esas cláusulas miden — `verification/` estaba y sigue limpio, y `regen_snapshots.py` no produce drift.
- **Fix:** Se trackeó el archivo, siguiendo la convención del repo (sus 16 hermanas del mismo directorio están en git). Revisado antes de commitear: cero esquemas de URL, arrobas de host, tokens, contraseñas o portadores. Es contenido de `.planning/`, así que no toca el invariante del criterio 1.
- **Files modified:** `.planning/research/.cache/3f83a89c…json`
- **Verification:** `git status --porcelain` → vacío; re-ejecución del bloque de `41-05` Task 1 → `exit 0`
- **Committed in:** `a284ab2`

**3. [Regla 1 - Bug] El denominador `-eq 14` de los verificadores de Task 3 es una mis-suma del planner**

- **Found during:** Task 3
- **Issue:** El bloque `<verify><automated>` de Task 3 exige 14 filas dispuestas y claves `41-r01`..`41-r14`. El conteo real de tareas de los siete planes es **16** (`grep -c '<task '` → 3+2+2+2+2+2+3). El plan enumeró 16 IDs y luego declaró 14.
- **Fix:** Ya diagnosticado y registrado por `41-01` en `41-AUDIT-CONTRACT.md § 2.5` y en `41-VALIDATION.md § Denominador`; este plan **no lo re-descubrió**, lo consumió. Se escribieron 16 filas (`41-r01`..`41-r16`) y se ejecutaron los verificadores con `-eq 16`. Registrado en la tabla de correcciones (filas `41-r03` y `41-r16`).
- **Files modified:** `41-VALIDATION.md`
- **Verification:** cadena corregida de Task 3 → `exit 0` (16 filas, suma de tokens `= 16`)
- **Committed in:** `fe060a5`

**4. [Regla 3 - Blocking] La transcripción literal de aserciones negativas auto-falsifica el archivo**

- **Found during:** Task 3
- **Issue:** El bloque de `41-01` Task 3 contiene dos aserciones negativas sobre `41-VALIDATION.md`; transcribirlas verbatim en la celda de evidencia de la fila `41-r03` metería en el archivo los mismos literales que esas aserciones prohíben, y las haría fallar. Es el mismo fallo que `41-01` documentó en su deviación #2.
- **Fix:** La celda describe las dos negaciones en prosa ("cero placeholders de selector, cero declaraciones stale del runner") y apunta a `41-01-PLAN.md` Task 3 para la forma ejecutable. Mismo tratamiento aplicado a la prosa del párrafo de procedencia y a los hallazgos de bookkeeping.
- **Files modified:** `41-VALIDATION.md`
- **Verification:** la cadena completa de `41-01` Task 3 sigue verde con `-eq 16` tras la escritura
- **Committed in:** `fe060a5`

### Desviación de forma respecto del plan

**Tres commits en vez de uno.** El criterio de aceptación de Task 3 pide "un solo commit de documentación con los ocho archivos de la fase". Es irrealizable en esta posición: seis de esos ocho (los cinco `{N}-VALIDATION.md` de v1.7 y `41-AUDIT-CONTRACT.md`) ya fueron commiteados por los planes 41-01..41-06 y no tienen cambios pendientes. Lo que el criterio realmente protege —**cero archivos `.py` en los commits de la fase**— se verificó y se cumple: `git diff --name-only <baseline> HEAD | grep -c '\.py$'` → **0**. Los tres commits de este plan son todos `docs`.

---

**Total deviations:** 4 auto-fixed (2 bugs, 2 blocking) + 1 desviación de forma
**Impact on plan:** Ninguna amplía el alcance. Dos son correcciones de gate (el verificador estaba mal, no el artefacto), una es higiene de índice de git, y una es la evitación de un patrón auto-referencial ya conocido.

## Issues Encountered

- **Falla de test pre-existente y explícitamente fuera de alcance.** `verification/test_main_matriz_login_fail_uniformity.py::test_probe_login_sync_returns_FINDING_on_authentication_error` falla con `TypeError: probe_login_sync() missing 1 required positional argument: 'client'`. El archivo no cambió en esta fase (el diff acumulado no toca ni un byte fuera de `.planning/`) y su último cambio traza a trabajo de la Phase 11. **No se arregló**: hacerlo violaría el invariante del criterio 1, que es la premisa entera de esta auditoría. Queda nombrado en `41-VALIDATION.md § Hallazgos de bookkeeping`. Vale la pena notar que ese archivo es uno de los 40 locks que hoy **no corren en CI** — por eso la falla sobrevivió sin romper el pipeline, que es exactamente el hallazgo que la declaración inerte del rollup existe para nombrar.
- **Ninguna otra.** Cero comandos de red (R-08), cero instalaciones de paquete, cero cambios de fuente de producto.

## Known Stubs

Ninguno. Este plan produce documentación derivada de artefactos existentes; no hay componentes con fuente de datos sin cablear ni valores placeholder.

## Threat Flags

Ninguna superficie de seguridad nueva. Las cinco mitigaciones del `<threat_model>` del plan están aplicadas y son verificables:

| Threat ID | Mitigación aplicada |
|-----------|---------------------|
| T-41-07-01 (Information Disclosure) | Escaneo del diff acumulado de la fase antes de cada commit: **0** esquemas de URL reales, **0** formas `usuario@host`, **0** asignaciones de token/contraseña/secreto/portador. Los 28 hits del grep amplio son todos meta-referencias a la propia regla de higiene, identificadores literales de pytest del repo, o la palabra "token" en el sentido de *token de disposición*. Toda salida de pytest recortada a su línea de resumen |
| T-41-07-02 (Repudiation, conteos a mano) | Los conteos del rollup se **derivan** por extracción acotada de las cinco tablas; el gate falla si la suma no iguala el total, por fase y no sólo en el agregado |
| T-41-07-03 (Repudiation, ensanchar alcance) | Gate de contención con conteo exacto (5 artefactos de v1.7, 6 rutas `VALIDATION.md` en total) más gate negativo sobre las seis fases fuera de alcance → **0** |
| T-41-07-04 (False assurance) | Declaración inerte por escrito con los tres números re-medidos (52 / 12 / 40) y ruteo explícito a la Phase 45 con su precondición citada |
| T-41-07-05 (Tampering, editar `ci.yml`) | `git diff --quiet <baseline> HEAD -- .github/workflows/ci.yml` → **exit 0**. Cero ediciones al workflow |
| T-41-07-SC (Tampering, paquetes) | Cero invocaciones de `uv add`/`npm`/`pip`/`cargo`. `uv.lock` y `pyproject.toml` byte-idénticos (cubierto por el diff vacío contra `v1.7`) |

## User Setup Required

Ninguna.

## Next Phase Readiness

- **La Phase 41 cierra completa.** Sus cinco criterios de éxito quedan probados con comandos: 62/62 dispuestas, cero flips, cero locks nuevos con los 40 preexistentes declarados inertes, alcance contenido en las cinco fases nombradas, y árbol de fuente de v1.7 sin cambios de punta a punta.
- **La Phase 42 queda desbloqueada.** Su dependencia declarada —"la auditoría de historia congelada tiene que cerrar antes del primer cambio de fuente de v1.8"— está satisfecha. A partir de este commit, tocar fuente ya no invalida ninguna atribución.
- **La Phase 45 hereda dos ítems nombrados y ruteados:** (a) el enrolamiento en CI de los 40 locks declarados inertes, dentro de su edit consolidado de `ci.yml` (criterio 5, requisitos HARN-03 / HARN-04); (b) la falla pre-existente de `test_main_matriz_login_fail_uniformity.py`, que es a la vez un lock roto y un lock sin enrolar — el caso testigo de por qué "reparar sin enrolar" no es una opción admisible bajo su criterio 3.
- **Aviso para `audit-milestone`:** los seis artefactos de esta fase quedan en `validated` + `nyquist_compliant: false`, que su §5.5 lee como **PARTIAL**, no como NOT-VALIDATED. Es el estado correcto y deliberado: 8 de las 62 filas siguen sin cobertura re-derivable, y 13 sin enforcement de CI.
- **Aviso de alcance para quien siga:** seis artefactos de validación más del repo (Phases 18, 25, 29, 30, 32, 33) siguen en estado de borrador. Ampliarles la auditoría está a un `grep` de distancia y quedó explícitamente **fuera** de este milestone (`REQUIREMENTS.md § Out of Scope`, fila `NYQUIST-32-33`, verificada byte-intacta).

## Self-Check: PASSED

- `41-ROLLUP.md` — FOUND (281 líneas, contiene `62`, `Phase 45`, `VERIFIED-NOW`)
- `41-VALIDATION.md` — FOUND (`## Validation Audit 2026-08-31`, 16 filas, `status: validated`)
- `41-07-SUMMARY.md` — FOUND
- `.planning/research/.cache/3f83a89c…json` — FOUND (trackeado)
- Commit `8cfc107` — FOUND
- Commit `a284ab2` — FOUND
- Commit `fe060a5` — FOUND
- Archivos `.py` en el diff acumulado de la fase — **0**

---
*Phase: 41-validaci-n-nyquist-retroactiva-de-v1-7*
*Completed: 2026-08-31*
