---
phase: 41-validaci-n-nyquist-retroactiva-de-v1-7
plan: 03
subsystem: testing
tags: [nyquist-audit, validation, retroactive-audit, market-data-client, pytest, mypy, ast-lock, ci-enforcement]

# Dependency graph
requires:
  - phase: 41-01
    provides: "41-AUDIT-CONTRACT.md — denominador 62, claves de fila {N}-r{NN}, reglas R-01..R-09 (en particular R-04 y R-09(c)), esqueleto de ocho bloques, higiene de evidencia, tabla de lookup de CI, y los dos SHA de atribución"
  - phase: 41-02
    provides: "Precedente de forma vivo: la sección de auditoría de 35-VALIDATION.md, con el estilo de celda de evidencia, la nota de escape de pipes en celdas de tabla y el patrón de rationale de R-09"
  - phase: 36-market-data-client-market-data-tipado-revocaci-n-de-la-fase
    provides: "El ## Per-Task Verification Map de 11 filas, los once archivos de test citados, y verification/test_main_market_data_deep_chain.py"
provides:
  - "Sección ## Validation Audit 2026-08-31 en 36-VALIDATION.md con 11 disposiciones (11 VERIFIED-NOW / 0 VERIFIED-HISTORICALLY / 0 NOT-VERIFIABLE-RETROACTIVELY), 4 columnas incl. superficie de enforcement de CI"
  - "La única aplicación de R-04 de toda la fase, documentada: 36-r11 shipeó sin comando declarado y la auditoría redactó uno tras leer el cuerpo del lock"
  - "Front-matter de la Phase 36 transformado: status validated, not_verifiable_retroactively: 0, ambos SHA de atribución, frozen_tree_verified"
  - "El único conteo de 0 filas NOT ENFORCED de las cinco fases auditadas — dato de contraste para el cierre 41-07 y para la Phase 45"
affects: [41-04, 41-05, 41-06, 41-07, audit-milestone]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Disposición R-04: una fila sin comando declarado se resuelve leyendo el CUERPO del lock candidato (no su nombre) antes de redactar el comando, y el calificador queda explícito en la celda"
    - "La celda de evidencia de una fila R-04 declara de forma inequívoca que el mapa no traía comando, para que la redacción no se lea como si hubiera estado ahí"
    - "Bookkeeping de plan-time contradicho por la medición se nombra y NO se corrige: las celdas File Exists y wave_0_complete quedan intactas porque su contradicción es el hallazgo"

key-files:
  created: []
  modified:
    - .planning/milestones/v1.7-phases/36-market-data-client-market-data-tipado-revocaci-n-de-la-fase-/36-VALIDATION.md

key-decisions:
  - "36-r11 (36-03-03) se dispone VERIFIED-NOW (comando redactado retroactivamente) por R-04, y la fila sin contrato de verificación se nombra como el hallazgo principal de la fase — no el VERIFIED-NOW, que es sólo el estado de la conducta."
  - "Antes de disponer 36-r11 se leyó el cuerpo completo de verification/test_main_market_data_deep_chain.py (6 tests, AST sobre main_market_data.py) y se confirmó que asserta la conducta SC-5 declarada por la fila y no otra (Assumptions Log A1: no basta el nombre)."
  - "Las tres celdas File Exists que dicen ❌ W0 NO se corrigen y wave_0_complete se deja en false: son bookkeeping de plan-time y su contradicción con la realidad medida es el hallazgo que D-04 pone en alcance; corregirlas lo borraría."
  - "nyquist_compliant se queda en false con rationale escrito: R-09 falla por (c) — una fila con calificador de corrección — y en consecuencia también por (a), 10 de 11 planos. (b) sí se satisface. Cero flags flipeados."
  - "El conteo de 0 filas NOT ENFORCED se escribe en la prosa como resultado ATÍPICO y no como default, siguiendo la instrucción del plan: es la única de las cinco fases con cobertura de CI de punta a punta."

patterns-established:
  - "Guardia anti-vacuidad verificada mecánicamente: los cinco deselects medidos son parciales; ninguna celda menciona descartes sin mencionar pasados (gate awk devuelve 0 líneas)"
  - "Re-verificación del invariante de árbol congelado (`git diff --quiet v1.7 HEAD -- . ':(exclude).planning'`) al inicio del plan y al final de cada tarea — exit 0 las tres veces"
  - "Escaneo del diff buscando ://, @, token, password, Bearer antes de cada commit"

# Metrics
metrics:
  duration: "~13 min"
  completed: 2026-08-31
  tasks: 2
  files-modified: 1
  files-created: 0
  commits: 2

status: complete
---

# Phase 41 Plan 03: Auditoría Nyquist retroactiva de la Phase 36 Summary

Las 11 filas de la Phase 36 disponen 11 VERIFIED-NOW con evidencia re-ejecutada esta sesión, cero
filas fuera de CI, y la única fila que shipeó sin comando declarado queda resuelta por R-04 y nombrada
como el hallazgo principal — con `nyquist_compliant` intacto en `false`.

## What Was Built

`.planning/milestones/v1.7-phases/36-market-data-client-market-data-tipado-revocaci-n-de-la-fase-/36-VALIDATION.md`
recibió la sección `## Validation Audit 2026-08-31` con los ocho bloques del §5 del contrato, la
columna `Status` de sus 11 filas actualizada, la leyenda extendida, una línea nueva tildada en
`## Validation Sign-Off`, y el front-matter transformado. Cero fuente de producto tocada; cero
archivos nuevos.

### Disposición medida — coincide exactamente con la §2.4 del contrato

| Métrica | Valor |
|---------|-------|
| Filas auditadas | 11 |
| VERIFIED-NOW | 11 (de los cuales 1 con calificador R-04) |
| VERIFIED-HISTORICALLY | 0 |
| NOT-VERIFIABLE-RETROACTIVELY | 0 |
| Correcciones de comando | 1 (redacción R-04) |
| Archivos de test nuevos | 0 |
| Filas NOT ENFORCED en CI | 0 |
| Suite de la fase | `711 passed in 1.09s` |

Las once salidas medidas esta sesión coinciden fila por fila con las referencias del researcher:
38 · mypy limpio (49 source files) · 2 · 61 · 1 · 3 · 8 · 1 · 1 · gate exit 0 · 6. Cero divergencias
materiales que escalar.

### El hallazgo principal: una fila que shipeó sin contrato de verificación

La celda `Automated Command` de `36-03-03` no contiene un comando sino una decisión de diseño
pendiente: *"planner decide: AST reutilizando precedente 30-09, o assertion en el plan"*. Una fila así
no es auditable como está — no hay nada que re-correr, y no distingue "la conducta no se verificó" de
"se verificó por un medio que nadie anotó". La auditoría encontró lo segundo: el planner tomó
efectivamente la rama AST y entregó `verification/test_main_market_data_deep_chain.py`, pero sin
volver a escribir el comando en el mapa.

Antes de disponer se leyó el **cuerpo** del lock, no su nombre. Sus 6 tests parsean
`main_market_data.py` por AST y assertan: las cuatro read probes presentes por nombre; que cada una
dereferencia `market_data.<alias>` sobre lo que fetcheó; que cada dereferencia vive dentro del `try`
de la probe (contrato never-FAILED de D-09); un piso agregado de 36 accesos; un piso por probe
(6/12/6/12); y que toda colección fetcheada está encadenada (WR-06). Es exactamente la conducta SC-5
que la fila declara. Ejecutado: `6 passed in 0.10s`. Enrolado en CI: `ci.yml:81`, primero de los 12
del allowlist explícito de `verification/`.

La celda de evidencia dice de forma inequívoca que el mapa **no** declaraba comando y que el que
aparece fue redactado por esta auditoría. Ese es el punto de T-41-03-02 del registro STRIDE:
presentarlo como si hubiera estado ahí sería repudiation.

### El resultado atípico: cero filas NOT ENFORCED

La Phase 36 es la única de las cinco cuyas filas tienen cobertura de CI real de punta a punta: ocho al
job `test` (`ci.yml:133-166`), una al `typecheck` por sus dos tramos (`ci.yml:122-123` para `src`,
`ci.yml:124-131` para el bucle de tests por paquete), una al step `decode-intactness` del job `lint`
(`ci.yml:55`), y la undécima al allowlist de `verification/` (`ci.yml:81-92`). La prosa lo dice como
resultado atípico y no como default, porque en las otras cuatro fases el `NOT ENFORCED` viene de
aserciones sobre markdown de `.planning/`, de `regen_snapshots.py`, de `surface_parity.py` como
script y de las filas manual/doc-review.

### Por qué `nyquist_compliant` sigue en `false`

R-09 falla por **(c)**: una fila con calificador de corrección (`36-r11`). En consecuencia también
falla **(a)**: 10 de 11 planos, no 11. **(b)** sí se satisface (cero VH, cero NVR) — es la única de
las cinco fases donde se cumple. El rationale queda escrito junto al veredicto siguiendo el modelo de
prosa de `07-VALIDATION.md`, sin adoptar su valor `partial`. Confirma la §3.2 del contrato por
evidencia medida y no por decreto: la Phase 36 **no** cierra limpia.

## Deviations from Plan

### Divergencias de conteo respecto de la prosa del plan (anotadas, no ajustadas)

**1. [Rule 1 - Bug] El plan dice "las nueve filas de pytest sobre `packages/market-data-client/tests/`"; son ocho**
- **Found during:** Task 2, al llenar la cuarta columna
- **Issue:** El `<action>` de Task 2 instruye mapear *"las nueve filas de pytest sobre
  `packages/market-data-client/tests/`"* al job `test`. La medición del mapa da **ocho**: `36-r01`,
  `36-r03`..`36-r09`. La novena fila de pytest de la fase es `36-r11`, pero corre sobre
  `verification/`, no sobre `packages/`, y su enforcement es el allowlist del job `lint`, no el job
  `test`. Nueve es el total de filas de pytest de la fase (8 + 1), no el de filas que van al job
  `test`.
- **Fix:** Se escribió el mapeo **medido** (8 al job `test`, 1 al allowlist de `lint`), no el
  declarado. El plan manda explícitamente escribir lo medido y anotar la divergencia acá.
- **Files modified:** `36-VALIDATION.md` (cuarta columna de la tabla de disposición)
- **Commit:** `3ef2fe4`

Ninguna otra desviación. Ninguna fila quedó sin regla aplicable: R-01 cubre las diez con comando
declarado y R-04 la única sin él. No apareció una tercera fila de selección vacía. Cero escalaciones.

### Nota sobre el escape de pipes

El aviso de 41-02 sobre escapar `|` como `\|` dentro de celdas de tabla **no aplicó**: ninguno de los
once comandos de la Phase 36 contiene un pipe literal (a diferencia de los `grep -c '^| '` de la
Phase 35). Las celdas se transcribieron verbatim sin escape.

## Out of Scope / Deferred

- `.planning/research/.cache/3f83a89c….json` quedó untracked al terminar. Es cache del tooling de
  research (mismo directorio que `fb4c178` ya versiona), anterior a este plan y ajeno a sus dos
  tareas. No se commiteó ni se borró — SCOPE BOUNDARY. `git status --porcelain verification/` sí está
  vacío, y bajo `.planning/milestones/v1.7-phases/` el único archivo modificado es `36-VALIDATION.md`,
  como exige el criterio de aceptación.

## Verification

Gates de Task 1 (todos exit 0):

- `uv run pytest packages/market-data-client/tests/test_market_data_chain.py -x -q` → verde
- `uv run pytest verification/test_main_market_data_deep_chain.py -q` → `6 passed in 0.10s`
- `uv run python tools/check_decode_intactness.py` → exit 0
- `grep -c 'verification/test_main_market_data_deep_chain.py' .github/workflows/ci.yml` → `1`
- `git diff --quiet v1.7 HEAD -- . ':(exclude).planning'` → exit 0
- `git status --porcelain verification/` → vacío; `ls verification/test_*.py | wc -l` → **52**

Gates de Task 2 (todos exit 0):

- Tabla acotada entre `### Disposición por fila` y `*Disposiciones:` → **11** filas
- Suma de los tres tokens dentro del rango → **11** (11 / 0 / 0)
- Filas con calificador `comando redactado retroactivamente` → **1**, y es `36-r11`
- Celdas con `deselected` y sin `passed` dentro del rango → **0**
- `NOT ENFORCED` dentro del rango → **0**
- `^status: validated` → 1 · `^nyquist_compliant: false` → 1 · `^not_verifiable_retroactively: 0` → 1
- `^audited_commit_sha: 37a83fe693a303a551f4374f48fe6fc5521804f7` → 1 ·
  `^audit_baseline_head: [0-9a-f]{40}` → 1
- `Cero archivos de test nuevos; cero escalaciones.` → 1
- `^- \[x\] .*nyquist_compliant: true` → **0** (la casilla preexistente quedó sin tildar)
- Columna `Status` con `✅ (VN 2026-08-31)` → 11 filas
- Escaneo de credenciales del diff (`://`, `@`, `token`, `password`, `Bearer`) → limpio

## Commits

| Task | Commit | Descripción |
|------|--------|-------------|
| 1 | `bee3446` | Re-ejecutar las 11 filas y resolver la fila sin comando declarado |
| 2 | `3ef2fe4` | Escribir la sección de auditoría y transformar el front-matter |

## Self-Check: PASSED

- `36-VALIDATION.md` existe en la ruta declarada — FOUND
- `bee3446` — FOUND en `git log`
- `3ef2fe4` — FOUND en `git log`
