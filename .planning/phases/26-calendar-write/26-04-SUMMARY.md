---
phase: 26-calendar-write
plan: 04
subsystem: testing
tags: [market-data-client, mutation-gate, no-retry, path-safety, public-surface, pytest-httpx, python]

# Dependency graph
requires:
  - phase: 26-calendar-write (Plan 01)
    provides: los 3 request models MarketHoursIn / HolidayIn / HolidaysIn
  - phase: 26-calendar-write (Plan 02)
    provides: los 5 builders, el parser tolerante, el guard D-18 e idempotent=False en add_holidays
  - phase: 26-calendar-write (Plan 03)
    provides: los 5 métodos en Client y AsyncClient, los 10 shims module-level y los dos archivos de test de calendar write
  - phase: 25-mutating-gate-symbols-write
    provides: el mutating-gate (_ensure_mutation_allowed), MarketDataMutationNotAllowedError y la red in-package de superficie pública
provides:
  - Matriz adversarial de refusal x5 x 2 shells con cero HTTP y cero round-trip a Auth0
  - Verificación end-to-end del guard de path-safety D-18 (ValueError + 0 requests)
  - Primer test dispatch-level de idempotent=False del paquete, con control positivo idempotente contrastante
  - Los 8 nombres nuevos re-exportados desde el namespace plano y cubiertos por la red in-package
affects: [27-live-verification, 28-release]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Refusal adversarial con token FORZADO-vencido: configure(token_expires_at=0.0) + assert get_requests() == [] prueba a la vez cero HTTP al servicio y cero grant a Auth0"
    - "Verificación end-to-end de un guard de path-safety: assertar la excepción Y la ausencia de request, porque el riesgo es el request que SÍ se ejecutaría"
    - "Test de no-retry a nivel dispatch con control positivo contrastante: mismo 503 repetido, mismo par de endpoints, sólo cambia el flag idempotent"

key-files:
  created: []
  modified:
    - packages/market-data-client/tests/test_calendar_write.py
    - packages/market-data-client/tests/test_calendar_write_async.py
    - packages/market-data-client/src/market_data_client/__init__.py
    - packages/market-data-client/tests/test_public_surface_market_data.py

key-decisions:
  - "El gate de verificación `uv run pytest -q` desde la raíz se sustituyó por `uv run pytest packages -q` + `uv run pytest tests -q`: la suite `verification/` alcanza APIs financieras en vivo y cuelga en un worktree sin credenciales. Sustitución instruida por las notas críticas de fase."
  - "Los 4 tests de shim module-level que el Plan 04 listaba como nuevos ya venían shipeados por el Plan 03 (2 sync + 2 async, cubriendo los 5 métodos). No se duplicaron; el criterio de aceptación se verificó sobre los existentes."
  - "Los tests de shim siguen despachando vía `market_data_client.client.*` en vez del namespace plano: la disponibilidad del nombre plano la enforcea la red de superficie pública, que es donde vive ese contrato."

patterns-established:
  - "Cero-round-trip a Auth0 como aserción de seguridad: forzar el token vencido convierte la lista vacía de requests en evidencia de que el gate corta ANTES de _ensure_token"
  - "preview_calendar_config gateado sin carve-out: un endpoint read-only pero POST se testea igual que un mutador real para que la excepción no aparezca por conveniencia"

requirements-completed: [MUT-MD-02]

# Metrics
duration: 13 min
completed: 2026-07-31
status: complete
---

# Phase 26 Plan 04: Contrato hostil y superficie pública de calendar write Summary

**Matriz adversarial de 16 tests que prueba refusal con cero HTTP y cero grant a Auth0 en los cinco métodos x dos shells, el guard D-18 verificado end-to-end (ValueError + 0 requests contra el retargeting a `DELETE /api/calendar/config`), el primer test dispatch-level de `idempotent=False` del paquete contra su control positivo, y los 8 nombres nuevos re-exportados con paridad sync/async enforceada.**

## Performance

- **Duration:** 13 min
- **Started:** 2026-07-31T22:29:00-03:00 (aprox.)
- **Completed:** 2026-07-31T22:42:00-03:00
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- **Refusal x5 x 2 shells con cero efecto colateral (D-14 / T-26-04 / T-26-06).** Cada uno de `set_calendar_config` / `delete_calendar_config` / `preview_calendar_config` / `add_holidays` / `delete_holiday` levanta `MarketDataMutationNotAllowedError` con `httpx_mock.get_requests() == []` después de haber forzado el token vencido con `configure(token_expires_at=0.0)`. La lista vacía es evidencia simultánea de cero HTTP al servicio **y** cero round-trip al servidor de auth: si el gate no cortara como primera sentencia, `_ensure_token` habría disparado un POST a Auth0 y ese POST aparecería. `preview_calendar_config` está incluido explícitamente — es la prueba de que el dry-run no tiene carve-out.
- **Host mismatch en ambos shells (T-26-05).** Gate ON con `expected_host` distinto del host que siembra el conftest ⇒ rechazo con 0 requests.
- **Guard D-18 cerrado end-to-end (T-26-01).** Con el gate **abierto**, `delete_holiday("../config")` levanta `ValueError` y emite cero requests. Esta es la mitad que el Plan 02 no podía cubrir: el `ValueError` unitario prueba que el builder rechaza, pero sólo el test end-to-end prueba que ningún `DELETE` sale al cable — y en particular que el `DELETE /api/calendar/config` (reset de la configuración de mercado, otro endpoint de esta misma fase) al que httpx normalizaría el path nunca se dispara. Se cubren además `""` y `"2026-12-25?x=1"`.
- **Primer test dispatch-level de `idempotent=False` del paquete (D-15 / T-26-07).** Con tres 503 encolados, `add_holidays` emite **exactamente 1** request saliente y registra **0** sleeps. El control positivo contrastante `delete_holiday` (`idempotent=True`), con el mismo 503 repetido, agota los 3 intentos (`max_retries` default 2 → `max_attempts` 3) con 2 sleeps — lo que atribuye el corte al flag y no al mock.
- **Superficie pública cerrada (D-17 / T-26-10).** Los 8 nombres nuevos son importables desde `market_data_client` y están en `__all__` (que sigue ordenado); las variantes async siguen viviendo sólo bajo `aio`. Las cuatro pruebas genéricas de la red in-package cubren ahora automáticamente la superficie de calendar write vía las dos tuplas extendidas.
- **Los 4 gates verdes** y `MUT-MD-02` cerrado.

## Task Commits

Cada tarea se commiteó atómicamente:

1. **Task 1: Matriz adversarial del gate (refusal x5 x 2 shells, host mismatch, D-18 end-to-end)** — `ac5fac6` (test)
2. **Task 2: No-retry dispatch-level de add_holidays (D-15) + control positivo** — `9ee09a0` (test)
3. **Task 3: Re-exports en `__init__.py` + red de superficie pública + los 4 gates** — `c92861b` (feat)

## Files Created/Modified

- `packages/market-data-client/tests/test_calendar_write.py` — +5 tests de refusal-by-default, +1 de host mismatch, +2 de path-safety D-18, +1 de no-retry y +1 de control positivo idempotente; docstring de módulo reescrito para describir la matriz adversarial (29 tests en total).
- `packages/market-data-client/tests/test_calendar_write_async.py` — espejo async de los 5 refusals, el host mismatch y los 2 tests de path-safety (25 tests en total).
- `packages/market-data-client/src/market_data_client/__init__.py` — import de los 3 request models y los 5 shims sync, cada uno insertado en orden ASCII; los 8 nombres agregados a `__all__`. `__version__` intacto en `0.3.1`.
- `packages/market-data-client/tests/test_public_surface_market_data.py` — `_NEW_PUBLIC_NAMES` +8 y `_MUTATION_METHODS` +5, agrupados por fase con comentarios; docstring actualizado para reflejar que la red cubre las dos superficies de escritura.

## Decisions Made

- **Sustitución del gate `uv run pytest -q`.** El criterio de aceptación del Plan 03 pedía la suite completa desde la raíz, pero `verification/` alcanza APIs financieras en vivo y cuelga sin credenciales en un worktree. Se corrieron en su lugar `uv run pytest packages -q` (**1041 passed**, 90.77 s) y `uv run pytest tests -q` (**2 passed**), que es la cobertura equivalente sin red externa. Sustitución instruida explícitamente por las notas críticas de fase.
- **No se duplicaron los tests de shim.** El `<behavior>` de la Task 2 listaba 4 tests de shim module-level como nuevos, pero el Plan 03 ya había shipeado `test_config_trio_module_shims_dispatch` y `test_holiday_pair_module_shims_dispatch` en cada archivo — 2 sync + 2 async, cubriendo los 5 métodos. El criterio de aceptación ("existen 2 shim sync y 2 shim async") se verificó sobre los existentes en vez de crear duplicados.
- **`RUF003` y el signo de multiplicación.** Los comentarios de sección usaban `×` (U+00D7), que ruff marca como carácter ambiguo. Se reemplazó por `x` ASCII.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Dev dependencies ausentes en el worktree fresco**
- **Found during:** arranque, antes de la Task 1
- **Issue:** el worktree arranca sin las dependencias de desarrollo instaladas; `pytest` no se puede spawnear (mismo blocker que reportaron los tres ejecutores previos de la fase).
- **Fix:** `uv sync --all-packages --all-extras --dev --frozen` — no toca archivos del repo ni `uv.lock`.
- **Files modified:** ninguno (`uv lock --check` verde después).
- **Verification:** baseline reproducido — 269 passed in 0.47s.
- **Committed in:** N/A (sin cambios en el repo)

**2. [Rule 1 - Bug] `RUF003` en los comentarios de sección nuevos**
- **Found during:** Task 1 (gate de ruff previo al commit)
- **Issue:** los encabezados de sección usaban `×` (MULTIPLICATION SIGN), que ruff rechaza como carácter ambiguo en comentarios.
- **Fix:** reemplazado por `x` ASCII en ambos archivos.
- **Files modified:** `packages/market-data-client/tests/test_calendar_write.py`, `packages/market-data-client/tests/test_calendar_write_async.py`
- **Verification:** `uv run ruff check .` → All checks passed!
- **Committed in:** `ac5fac6` (commit de la Task 1)

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug de lint)
**Impact on plan:** ninguno sobre el alcance. Ambos fixes son de entorno/estilo; no se tocó código de producción fuera de los re-exports planificados, ni se arreglaron los errores mypy pre-existentes de Phase 25, ni el bug de lectura D-16 (ambos siguen fuera de scope por prohibición explícita del plan).

## Verification Results

Los 4 gates, en orden:

| Gate | Comando | Resultado |
|------|---------|-----------|
| 1 | `uv run ruff check .` | All checks passed! |
| 2 | `uv run ruff format --check .` | 193 files already formatted |
| 3 | `uv run mypy packages/market-data-client/src` | Success: no issues found in 11 source files |
| 4 | `uv run --package market-data-client pytest packages/market-data-client/tests -q` | **287 passed in 0.39s** (baseline 269 → +18) |

Verificaciones adicionales del plan:

- `uv run pytest packages -q` → **1041 passed, 1 deselected in 90.77s** (sustituye el `uv run pytest -q` de raíz; ver Decisions).
- `uv run pytest tests -q` → **2 passed**.
- `uv lock --check` → Resolved 48 packages, sin cambios.
- `uv run lint-imports` → Contracts: 4 kept, 0 broken.
- `pytest -k "refused or mismatch or path_safety or guard"` → **30 passed, 255 deselected** (el criterio pedía ≥16).
- `--durations=5` sobre la suite del paquete → las 5 más lentas por debajo de 0,005 s; ningún test individual supera 1 s (evidencia de que no se duerme jitter real).
- Los 8 nombres importables + presentes en `__all__`; `list(__all__) == sorted(__all__)`; los 5 shims async presentes bajo `aio`; `__version__ == '0.3.1'` — todos verificados en un one-liner de Python.
- Grep de disciplina de logging sobre los archivos tocados: sin `logging.basicConfig` ni `logging.root.` (la única coincidencia es un comentario pre-existente en `__init__.py` que documenta precisamente que NUNCA se toca `logging.root`).

## Issues Encountered

Ninguno. Los tests de refusal y host mismatch pasaron en verde de entrada, confirmando que el Plan 03 dejó `_ensure_mutation_allowed()` como primera sentencia literal en los diez métodos (cinco por shell); no hizo falta corregir código de producción.

## Threat Flags

Ninguna superficie de seguridad nueva fuera del `<threat_model>` del plan. Este plan no agrega endpoints, rutas de auth ni accesos a archivos: sólo tests y re-exports.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **MUT-MD-02 cerrado.** La superficie de calendar write está completa, gateada, testeada de forma adversarial y exportada. Phase 26 termina acá (último plan de la fase).
- **Phase 27 (LIVE-MUT-01)** puede ejercitar los cinco métodos en vivo contra develop. Recordar que el gate exige opt-in explícito **y** que `expected_host` coincida con el host de `base_url`.
- **Finding abierto para Phase 27 (D-16):** el par de lectura `get_calendar` / `parse_calendar_response` está roto contra el wire real. Esta fase lo evitó por diseño (el par de feriados retorna `dict` passthrough) y NO lo arregló, por prohibición explícita del plan. Debe atacarse en Phase 27.
- **Phase 28 (PUB-MUT-01):** `__version__` sigue en `0.3.1` a propósito. El bump y el release son de esa fase.
- **Deuda pre-existente sin tocar:** los errores mypy de `test_reference_core.py` y `test_mutation_gate.py` documentados como deferred de Phase 25 siguen abiertos; no bloquean CI (el gate de mypy apunta a `src`, no a `tests`).

## Self-Check: PASSED

- Archivos modificados presentes en disco: `test_calendar_write.py`, `test_calendar_write_async.py`, `__init__.py`, `test_public_surface_market_data.py` — 4/4 FOUND.
- Commits presentes en el historial: `ac5fac6`, `9ee09a0`, `c92861b` — 3/3 FOUND sobre la base `8278f25`.
- Todos los criterios de aceptación de las tres tareas re-ejecutados y en verde (ver Verification Results).

---
*Phase: 26-calendar-write*
*Completed: 2026-07-31*
