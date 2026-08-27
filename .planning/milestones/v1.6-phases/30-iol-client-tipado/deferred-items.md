# Deferred items — Phase 30

Hallazgos fuera del alcance de esta fase, registrados sin corregir (SCOPE
BOUNDARY: sólo se auto-corrige lo que causan directamente los cambios de la
tarea en curso).

## DEF-30-01 — `verification/` tiene 19 tests de matriz rotos desde Phase 15

**Descubierto en:** Plan 30-04, verificación paso 9 (`uv run pytest -q`, suite
completa del monorepo).

**Síntoma:** `19 failed, 1840 passed, 19 errors` en la corrida completa. Los 19
son todos de matriz, en dos archivos:

| Archivo | Tests | Causa raíz |
|---|---|---|
| `verification/test_matriz_sweep_snapshot.py` | 17 | `TypeError: probe_get_segments() missing 1 required positional argument: 'client'` |
| `verification/test_main_matriz_login_fail_uniformity.py` | 2 | misma familia — el probe no se ejecuta, y `pytest_httpx` falla en teardown por respuestas mockeadas y nunca pedidas |

Los 19 "errors" son teardowns de `httpx_mock` derivados de las mismas fallas, no
fallas independientes.

**Por qué es pre-existente y no de esta fase:** `main_matriz.py` fue refactorizado
en `1fbc83f` (**2026-06-24**, Plan 15-05, "route matriz sync sweep probes through
threaded Client") para que cada probe reciba un `Client` por parámetro. Los dos
archivos de test que los invocan datan de `9314e6e` (2026-06-12) y `bc4acc1`
(2026-06-14) y siguen llamándolos sin argumento. Llevan **dos meses** rotos sin
que nadie lo viera porque `verification/` **nunca corre en CI** (el workflow pasa
una ruta de paquete explícita que anula `testpaths` — descubierto en Phase 29,
Plan 29-09).

**Por qué no se corrige acá:** Phase 30 no toca `matriz-client` ni `main_matriz.py`.
Corregirlo requiere decidir cómo threadear la instancia en cada test, que es
trabajo de matriz, no de iol.

**Evidencia de que el resto está verde:** excluyendo estos dos archivos (y el
lento `test_with_options.py`), la suite completa sale **1824 passed, 0 failed**.

**Dónde cae naturalmente:** Phase 32 es la que arregla el gap de CI de
`verification/`. Ese es el momento en que estos 19 dejarían de ser invisibles y
tendrían que estar verdes — conviene resolverlos ahí, o antes, pero como trabajo
de matriz.
