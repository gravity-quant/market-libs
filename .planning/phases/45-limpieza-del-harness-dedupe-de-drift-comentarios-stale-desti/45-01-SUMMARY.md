---
phase: 45-limpieza-del-harness-dedupe-de-drift-comentarios-stale-desti
plan: 01
subsystem: testing
tags: [harness, mypy, ruff, docstring, roadmap, market-data-client, surface-gate]

# Dependency graph
requires:
  - phase: 43-market-data-client-forma-de-instrument-segment-5-claves-extr
    provides: "El nuevo field set de `Segment` (`segment` / `live_instruments`) que dejó stale el dereference del driver, y la medición de `43-DISPOSITION.md § 5` de por qué ningún gate estático lo detecta"
  - phase: 40-release-v1-7
    provides: "`matriz_client.__version__` — el símbolo cuya existencia en HEAD justifica el retiro de `IN-05`"
  - phase: 37-nobj-mtz
    provides: "El bloque de cifras del docstring de `tools/check_surface_types.py` que esta fase re-mide y fecha"
provides:
  - "Docstring del gate de superficie reproducible: bloque histórico pinneado a `00ffb2f~1` con sus cifras intactas + bloque vigente fechado con las 3 cifras medidas hoy (187 / 337 / 467)"
  - "`probe_parity` de `main_market_data.py` comparando de verdad (`s.segment`), con `uv run mypy main_market_data.py` limpio"
  - "`IN-05` retirado del backlog del ROADMAP con la verificación de código pegada; criterio 4 de la Phase 45 con la cifra medida; `DRV-MD-SEG-43` anotado como cerrado"
affects: [45-02, 45-03, 45-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Cita histórica pinneada a commit: un bloque de salida congelada se conserva byte-idéntico y se le agrega el pin del árbol que lo produjo, en vez de reescribir sus dígitos"
    - "Bloque de salida vigente fechado + pinneado (`**Measured YYYY-MM-DD** (commit ...)`) para que un lector pueda reproducir o falsificar la cifra"

key-files:
  created: []
  modified:
    - tools/check_surface_types.py
    - main_market_data.py
    - .planning/ROADMAP.md

key-decisions:
  - "Las tres cifras del bloque vigente se copiaron de una corrida hecha en la tarea (187 / 337 / 467), no de `45-RESEARCH.md` ni de `45-PATTERNS.md` — coinciden con lo que ambos midieron, pero la medición es propia (D-05 ENMENDADA lo exige literalmente)"
  - "El `442` de la prosa 'now earned' se actualizó a `467` en la misma tarea: era la misma cifra stale en prosa, y corregir el bloque dejando la prosa contradiciéndolo reproduce el defecto que la tarea cierra"
  - "`DRV-MD-SEG-43` NO se borra del backlog: su medición de por qué ningún gate lo detectó es la evidencia que cita la declaración de Q5, así que se anota como cerrado y se conserva"
  - "El gap de gate de mypy sobre los drivers `main_*.py` de la raíz NO se cierra acá (no se apunta mypy a los drivers): es scope creep de tamaño no medido, ruteado a la declaración por escrito de Q5 en el plan 45-05"

patterns-established:
  - "Retiro de backlog justificado por el código y no por el reporte: el retiro de `IN-05` se ejecutó sólo después de correr el import y pegar su salida (`0.3.0`) en el propio ROADMAP"

requirements-completed: []  # HARN-03 queda PARCIAL, no completo — ver § Requirements abajo
requirements-partial:
  - "HARN-03 — 2 de sus 3 partes cerradas acá (comentario stale D-05 + retiro de `IN-05` D-07); la tercera (`IN-06`, D-06) la cierra el plan 45-05, así que el checkbox de `REQUIREMENTS.md` se deja abierto a propósito"

# Metrics
duration: 2min
completed: 2026-09-01
status: complete
---

# Phase 45 Plan 01: HARN-03 mecánico + fold-in `DRV-MD-SEG-43` Summary

**El docstring del gate de superficie pasa de tres cifras congeladas a un registro reproducible (histórico pinneado a `00ffb2f~1`, vigente fechado 187 / 337 / 467), `probe_parity` vuelve a comparar segments en vez de salir siempre por la rama de excepción, e `IN-05` deja de figurar como deuda pendiente.**

## Performance

- **Duration:** 2 min
- **Started:** 2026-09-01T15:16:58Z
- **Completed:** 2026-09-01T15:18:48Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- **El gate de superficie dejó de mentir en prosa.** El bloque "Before Phase 37" conserva sus dígitos (`183` / `330` / `13` / `23`) byte-idénticos y ahora dice de qué árbol salieron (`00ffb2f~1`); el bloque vigente dejó de leerse como "lo que el gate imprime desde la Phase 37" y pasó a `**Measured 2026-09-01** (commit ``fe323d6``)` con las tres cifras que el gate imprime hoy.
- **El probe de paridad de market-data dejó de estar ciego.** `probe_parity` dereferenciaba `Segment.marketSegmentId`, campo que la Phase 43 removió, así que el `AttributeError` se disparaba **siempre** y el probe salía por la rama de excepción antes de comparar nada. Ahora compara `s.segment` y `uv run mypy main_market_data.py` pasó de 2 errores `attr-defined` a limpio.
- **El ROADMAP dejó de arrastrar una deuda ya resuelta y una cifra falsa.** `IN-05` figura como resuelto en la Phase 40 con la verificación de código pegada; el criterio 4 dice `337` (medido) en vez de `336` (medido antes de las Phases 43/44).

## Mediciones pedidas por el `<output>` del plan

**`uv run python tools/check_surface_types.py` (idéntica antes y después — se tocó el docstring, no el gate; exit 0):**

```
surface types: 6 packages, 187 `__all__` names, 337 definitions scanned, 467 fields scanned, 13 constant/alias exports, 24 exempted (dunder 13, private-helper 1, serialize-out 9, ws-catch-all 1), 0 violations
```

Esa línea es la fuente de las tres cifras escritas en el docstring. Comparación exigida por el criterio de aceptación, pegando ambas:

| Cifra | Salida del gate | Docstring (`tools/check_surface_types.py:59-60`) |
|---|---|---|
| `__all__` names | `187` | `187` |
| definitions scanned | `337` | `337` |
| fields scanned | `467` | `467` |

Y la prosa que sigue al bloque (`:63`) dice `The same green, now earned: 467 fields inspected` — el mismo `467` del bloque, ya no `442`.

**`uv run mypy main_market_data.py` — ANTES (línea base, exit 1):**

```
main_market_data.py:1541: error: "Segment" has no attribute "marketSegmentId"  [attr-defined]
            ids_sync = sorted(s.marketSegmentId for s in seg_sync)
                              ^~~~~~~~~~~~~~~~~
main_market_data.py:1542: error: "Segment" has no attribute "marketSegmentId"  [attr-defined]
            ids_async = sorted(s.marketSegmentId for s in seg_async)
                               ^~~~~~~~~~~~~~~~~
Found 2 errors in 1 file (checked 1 source file)
```

**`uv run mypy main_market_data.py` — DESPUÉS (exit 0):**

```
Success: no issues found in 1 source file
```

**`uv run python -c "import matriz_client; print(matriz_client.__version__)"` (exit 0):**

```
0.3.0
```

## Task Commits

Cada tarea se commiteó atómicamente:

1. **Task 1: Docstring del gate — pin histórico + re-medición (D-05 ENMENDADA)** — `587641f` (docs)
2. **Task 2: `DRV-MD-SEG-43` — `probe_parity` vuelve a comparar segments (D-09)** — `4039551` (fix)
3. **Task 3: ROADMAP — retiro de `IN-05` (D-07), cifra del criterio 4, cierre de `DRV-MD-SEG-43`** — `a1a8beb` (docs)

## Files Created/Modified

- `tools/check_surface_types.py` — docstring: pin `00ffb2f~1` en el bloque histórico (dígitos intactos), bloque vigente re-medido y fechado, prosa "now earned" alineada a `467`. La lógica del gate, el bloque `Run it as::` y la nota sobre `test_surface_types_red.py` no se tocaron.
- `main_market_data.py` — dos líneas dentro del `try` de `probe_parity` (`:1541-1542`): `s.marketSegmentId` → `s.segment`. Sin lógica nueva, sin espejo sync/async (es un dereference de driver, no de `client.py`/`aio.py`).
- `.planning/ROADMAP.md` — tres ediciones acotadas (`git diff --numstat` = `3 3`, una línea por zona): entrada de backlog "Cosmético Phase 37", criterio de éxito 4 de la Phase 45, entrada de backlog `DRV-MD-SEG-43`.

## Verificación del contrato de la ladder D-09

Criterio de aceptación explícito de la Task 2 — leído y confirmado: el `except Exception` sigue presente en `probe_parity`, inmediatamente después de las dos líneas cambiadas:

```
1541:        ids_sync = sorted(s.segment for s in seg_sync)
1542:        ids_async = sorted(s.segment for s in seg_async)
1543:    except Exception as exc:  # D-09: la comparación nunca crashea el driver
```

El contrato "una divergencia de forma degrada a finding, nunca a crash" quedó intacto.

## Decisions Made

- **No se tocaron los dígitos del bloque histórico.** `45-RESEARCH.md` Hallazgo 4 los reconstruyó con `git worktree` sobre `00ffb2f~1`; son byte-idénticos a lo que ese árbol imprimía. `grep -c '330 definitions scanned'` devuelve exactamente `1` y es esa cita. El defecto de `IN-01` nunca fue el dígito histórico: era la ausencia de fecha/pin en el bloque vigente.
- **`DRV-MD-SEG-43` se anota, no se borra.** Su medición de por qué ningún gate estático lo detecta (mypy del root scoped a `packages/*/src`, pre-commit scoped a `^packages/.*/src/`, `test_main_market_data_deep_chain.py` parseando por AST sin importar) es la evidencia que la declaración de Q5 va a citar en el plan 45-05.
- **El gap de gate no se cierra en esta fase.** Apuntar mypy a los 5 drivers de la raíz es scope creep no medido (Q5 lo rutea a declaración escrita + backlog v1.9). Se arregló el sitio, no el gate.

## Deviations from Plan

None — plan executed exactly as written. Sin auto-fixes bajo Rules 1-3; sin instalación de paquetes (consistente con `T-45-SC`: la fase no instala nada).

## Issues Encountered

- **Tensión menor entre dos criterios de aceptación de la Task 3, resuelta a favor del criterio inequívoco.** El criterio de grep pide que `IN-05` sólo aparezca en líneas que lo describan como resuelto; quedan 3 líneas que lo mencionan fuera de la entrada de backlog editada: `:62` (entrada de la Phase 45 en la lista del roadmap — "`IN-05` retirado"), `:206` (listado del propio plan 45-01 — "retiro de `IN-05` (D-07)") y `:249` (nota de ruteo — "con `IN-05` a retirar"). Las tres son descripciones del **trabajo de retiro** que este plan acaba de ejecutar, no ítems de deuda pendiente; la entrada de backlog real (`:278`) sí dice ahora `RETIRADO ... resuelto en la Phase 40`. Editarlas habría violado el otro criterio de la misma tarea (`git diff --stat` mostrando cambios sólo en las tres zonas nombradas) y la instrucción literal "tres ediciones, nunca reescribir el archivo entero". Se conservaron.

## Requirements

**`HARN-03` queda PARCIAL — su checkbox en `REQUIREMENTS.md` se deja abierto deliberadamente.** El requisito tiene tres partes (`REQUIREMENTS.md:31`): (1) corregir el comentario stale de la Phase 37, (2) cerrar `IN-06` metiendo `verification/test_public_surface.py` en el allowlist explícito de CI, (3) retirar `IN-05`. Este plan cerró (1) y (3); (2) es D-06 y pertenece al plan 45-05, que además tiene que llegar dentro del edit consolidado único de `ci.yml` (D-11).

Marcarlo completo acá afirmaría en el ledger de requisitos exactamente el tipo de cosa que esta fase existe para eliminar — un estado escrito que el código todavía no respalda. Por eso `requirements-completed` va vacío y `requirements mark-complete` **no** se corrió; el plan 45-05 es el que cierra `HARN-03`.

## User Setup Required

None — no external service configuration required. Esta fase no corre drivers en vivo ni lee ningún `.env`.

## Next Phase Readiness

- **`main_market_data.py` queda tocado y verde ANTES del dedupe**, que es exactamente el propósito de ordenamiento declarado en el objetivo del plan: el diff que el plan 45-02 va a producir sobre este archivo es puro dedupe, sin arrastrar el fix del dereference.
- **Deuda ruteada, no silenciada:** Q5 (gap de gate de mypy sobre los 5 drivers de la raíz) queda esperando su declaración por escrito en el plan 45-05, con la entrada `DRV-MD-SEG-43` del ROADMAP ya apuntando ahí.
- **Sin bloqueos.** `uv run ruff check . && uv run ruff format --check .` limpio sobre 279 archivos; `git status --porcelain verification/ .planning/verification/` vacío (ningún artefacto de findings tocado, como exige la verificación del plan).
- Resto de HARN-03 (`IN-06`, D-06) pendiente en el plan 45-05, dentro del edit consolidado único de `ci.yml` (D-11).

## Self-Check: PASSED

- `tools/check_surface_types.py` — FOUND (modificado, gate verde)
- `main_market_data.py` — FOUND (modificado, mypy limpio)
- `.planning/ROADMAP.md` — FOUND (modificado, 3 líneas)
- Commit `587641f` — FOUND
- Commit `4039551` — FOUND
- Commit `a1a8beb` — FOUND

---
*Phase: 45-limpieza-del-harness-dedupe-de-drift-comentarios-stale-desti*
*Completed: 2026-09-01*
