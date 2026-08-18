---
phase: 26-calendar-write
plan: 03
subsystem: api
tags: [market-data-client, mutation, dispatch, calendar, sync-async-parity, python, httpx]

# Dependency graph
requires:
  - phase: 26-calendar-write
    provides: "Plan 01 — MarketHoursIn / HolidayIn / HolidaysIn con to_dict() ruteado por drop_none"
  - phase: 26-calendar-write
    provides: "Plan 02 — los 5 builders de calendar write + parse_calendar_write_response + guard D-18"
  - phase: 25-symbols-write
    provides: "_ensure_mutation_allowed() (gate GATE-MD-01) y el template de método gated que serializa en el shell"
provides:
  - "Client.set_calendar_config / delete_calendar_config / preview_calendar_config / add_holidays / delete_holiday — los 5 métodos sync gated"
  - "AsyncClient.<los mismos 5> — espejo async línea a línea"
  - "10 shims module-level (5 sync en client.py, 5 async en aio.py)"
  - "tests/test_calendar_write.py + tests/test_calendar_write_async.py — 38 tests de contrato de wire"
affects: [26-04-public-surface, 27-live-verification]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Gate-first verificado por AST (no por grep): la sentencia inmediatamente posterior al docstring es self._ensure_mutation_allowed() en los 10 cuerpos"
    - "Excepción read-safe DOCUMENTADA en el docstring en vez de implementada como carve-out del gate (preview_calendar_config)"
    - "Serialización en el shell (config.to_dict() antes del builder) — precedente Phase 25, no el de Phase 20"

key-files:
  created:
    - packages/market-data-client/tests/test_calendar_write.py
    - packages/market-data-client/tests/test_calendar_write_async.py
  modified:
    - packages/market-data-client/src/market_data_client/client.py
    - packages/market-data-client/src/market_data_client/aio.py

key-decisions:
  - "D-14 aplicado sin excepciones: preview_calendar_config lleva el gate igual que los dos que persisten; su naturaleza compute-only vive sólo en el docstring"
  - "D-05: el trío de config reusa parse_calendar_config_response SIN modificarlo; D-06: el par de feriados retorna dict vía parse_calendar_write_response"
  - "Sin manejo de status nuevo en ningún método — el 422 fluye por _core.raise_for_response"
  - "Las 4 divergencias sync/async permitidas se respetaron exactamente: async def, await self._request, gate NO-awaited, docstrings en castellano en aio.py"
  - "REQUIREMENTS.md no se tocó: MUT-MD-02 abarca los 4 planes; el orchestrator lo marca al cerrar la fase"

patterns-established:
  - "Verificación de disciplina de gate por AST: parsear el módulo, ubicar los métodos por nombre y assertar ast.unparse(body[1]) == 'self._ensure_mutation_allowed()' — prueba lo que el grep sólo sugiere"
  - "Helper de test `_hours(**overrides)` para construir el caso canónico del ROADMAP con un solo punto de cambio"

requirements-completed: [MUT-MD-02]

# Metrics
duration: 22min
completed: 2026-07-31
status: complete
---

# Phase 26 Plan 03: Calendar Write Shells (sync + async) Summary

**Los cinco métodos de calendar write cableados sobre ambos shells con el gate de Phase 25 como primera sentencia literal verificada por AST en los 10 cuerpos, más 10 shims module-level y 38 tests que pinean el contrato de wire: `confirm: false` por default en el `PUT`, las horas `None` ausentes del `POST` de feriados, y los dos `DELETE` saliendo con `content == b""` y sin `Content-Type`.**

## Performance

- **Duration:** ~22 min
- **Tasks:** 2 (ambas TDD: RED → GREEN)
- **Files created:** 2 · **Files modified:** 2
- **Suite del paquete:** 231 → **269 tests** (+38), cero regresiones

## Accomplishments

- **Los cinco métodos despachan correctamente en sync y async (ROADMAP SC#1):** `set_calendar_config` → `PUT /api/calendar/config`, `delete_calendar_config` → `DELETE /api/calendar/config`, `preview_calendar_config` → `POST /api/calendar/config/preview`, `add_holidays` → `POST /api/calendar/holidays`, `delete_holiday(day)` → `DELETE /api/calendar/holidays/{day}` — método, path, Bearer y body verificados sobre el request real que sale por `httpx_mock`.
- **`confirm: false` viaja por default (ROADMAP SC#2):** un test assertea literalmente el dict de 7 claves del `PUT`, y otro pinea el opt-in explícito `confirm=True`. El guardrail sigue siendo un campo del modelo, no un kwarg suelto (D-09).
- **`drop_none` en el wire (ROADMAP SC#3):** `add_holidays(HolidaysIn([HolidayIn("2026-12-25")]))` emite `{"days": [{"day": "2026-12-25", "closed": True, "description": ""}]}` — sin `open_time`/`close_time`, mientras que un `HolidayIn` que sí las trae emite ambas claves.
- **D-14 sin carve-out y verificado por AST, no por grep:** en los 10 cuerpos de método (5 × 2 shells) la sentencia inmediatamente posterior al docstring es `self._ensure_mutation_allowed()`. `preview_calendar_config` pasa por el gate igual que los dos que persisten; su naturaleza compute-only queda documentada en el docstring, que es exactamente lo que pedía la decisión.
- **Los dos `DELETE` salen limpios (D-02 / T-26-08):** `req.content == b""` y `"content-type" not in req.headers`, verificado en el wire en ambos shells — la contraparte end-to-end de lo que el Plan 02 sólo podía assertar a nivel `RequestSpec`.
- **Paridad sync/async estricta (D-17):** los cinco nombres existen como `def` en `Client` y `async def` en `AsyncClient`; los 10 shims existen y son coroutine-function sólo del lado `aio`. Las divergencias son exactamente las cuatro permitidas.
- **Serialización en el shell:** `config.to_dict()` / `holidays.to_dict()` se llaman en el método y el dict ya aplanado llega al builder (precedente Phase 25). Ningún builder serializa.

## Task Commits

Cada task siguió el ciclo TDD completo (RED → GREEN):

1. **Task 1: Trío de config (set / delete / preview) + 6 shims**
   - `b286b2d` (test — RED, 20 failed verificados)
   - `3eb77cb` (feat — GREEN, 251 passed)
2. **Task 2: Par de feriados (add_holidays / delete_holiday) + 4 shims**
   - `41171ec` (test — RED, 18 failed nuevos)
   - `bc3a21d` (feat — GREEN, 269 passed)

No hizo falta un paso REFACTOR: los cuerpos GREEN salieron en su forma final siguiendo el template de Phase 25.

## Files Created/Modified

- `packages/market-data-client/src/market_data_client/client.py` — sección nueva «Public endpoint methods — calendar writes (gated, MUT-MD-02 / GATE-MD-01)» con los 5 métodos; `MarketHoursIn` y `HolidaysIn` agregados al import block de `models`; 5 shims module-level junto a los de Phase 25.
- `packages/market-data-client/src/market_data_client/aio.py` — espejo idéntico: misma sección, mismos 5 métodos en `async def`, mismos imports, 5 shims async.
- `packages/market-data-client/tests/test_calendar_write.py` — **nuevo**, 19 tests sync.
- `packages/market-data-client/tests/test_calendar_write_async.py` — **nuevo**, 19 tests async (espejo).

## Decisions Made

Ninguna decisión nueva — se aplicaron las ya lockeadas en `26-CONTEXT.md`. Tres detalles de implementación:

- **La verificación de D-14 se hizo por AST, no por grep.** El plan pedía «verificado leyendo el cuerpo de cada método». Se escribió un check que parsea `client.py` y `aio.py`, ubica los 5 métodos en la clase y assertea `ast.unparse(body[1]) == "self._ensure_mutation_allowed()"` (con `body[0]` siendo el docstring). Prueba la posición literal, que es lo que un grep de presencia no puede distinguir de una llamada tardía.
- **Los tests viven en dos archivos, uno por shell**, tal como los pidió el plan, con constantes duplicadas (`_BASE`, `_TOKEN_URL`, `_CONFTEST_HOST`, `_CONFIG_200`, `_HOURS_BODY`) siguiendo el precedente de `test_symbols_write*.py`. La duplicación es deliberada: espeja el constraint «sin código compartido» del repo a nivel de test.
- **El mock del `200` del trío de config usa la forma de wire REAL** capturada en `.planning/verification/schemas/market-data-client/get-calendar-config.json` (11 claves, `updated_at: null`, `warnings` como lista), no un dict inventado.

## Deviations from Plan

None - plan executed exactly as written.

_El worktree arrancó sin dev-dependencies, igual que reportaron los dos ejecutores de Wave 1. Se resolvió con el comando de setup documentado en CLAUDE.md (`uv sync --all-packages --all-extras --dev --frozen`) antes de tocar código: cero cambios de archivos, `uv.lock` intacto, baseline reproducido exactamente en 231 passed. No se registra como deviation porque es el paso de bootstrap estándar del repo, no una desviación del plan._

## Verification Evidence

| Gate | Comando | Resultado |
|---|---|---|
| Suite del paquete | `uv run --package market-data-client pytest packages/market-data-client/tests -q` | **269 passed in 0.37s** (baseline 231 + 38, cero regresiones) |
| Tests del plan | `pytest tests/test_calendar_write.py tests/test_calendar_write_async.py -q` | **38 passed** |
| Lint | `uv run ruff check .` | All checks passed! |
| Format | `uv run ruff format --check .` | 193 files already formatted |
| Typecheck | `uv run mypy packages/market-data-client/src` | Success: no issues found in 11 source files |
| D-14 (AST, 10 cuerpos) | `ast.unparse(body[1]) == "self._ensure_mutation_allowed()"` × 5 métodos × 2 shells | ok — ninguna llamada a `_core.build_`, `self._request` ni `_ensure_token` la precede |
| D-17 paridad | `hasattr` + `asyncio.iscoroutinefunction` sobre `Client` / `AsyncClient` / `client` / `aio` | ok — 5 métodos y 10 shims, async sólo del lado `aio` |
| Sin re-exports planos | `not any(hasattr(market_data_client, n) for n in los 5)` | ok — el namespace plano lo puebla el Plan 04 |
| Disciplina de logging | `grep -c "logging.basicConfig\|logging.root\." client.py aio.py` | **0 / 0** |
| `__version__` | `grep __version__ __init__.py` | `"0.3.1"` — sin bump (el release es Phase 28) |
| Deleciones | `git diff --diff-filter=D --name-only 02ec688 HEAD` | vacío |

## Threat Mitigations Verified

| Threat ID | Mitigación | Evidencia en este plan |
|---|---|---|
| T-26-04 (Tampering) | Gate como primera sentencia en los 5 métodos × 2 shells | Verificación por AST de los 10 cuerpos (arriba). La prueba adversarial de CERO requests es del Plan 04 Task 1, como asignó el plan. |
| T-26-05 (Spoofing/Tampering) | Pata de host exacto del gate heredado | Consumida sin cambios; corre antes de cualquier dispatch. Test de host mismatch → 0 requests: Plan 04. |
| T-26-08 (Tampering) | Los dos DELETE sin body ni `Content-Type` | Verificado EN EL WIRE en ambos shells: `req.content == b""` y `"content-type" not in req.headers`. |
| T-26-09 (Info Disclosure) | accept — no regresionar | Los 10 métodos/shims nuevos no loguean nada: `logging.basicConfig` / `logging.root.` cuentan 0 en ambos archivos. `updated_by` no aparece en ningún mensaje de error. |
| T-26-15 (Tampering) | accept — parsers tolerantes como hedge | Tests de `200` con body vacío: `CalendarConfig` de defaults tipados para el trío, `{}` para el par de feriados. Forma real: Phase 27 (LIVE-MUT-01). |
| T-26-SC | accept — sin instalaciones | Cero deps nuevas; `uv.lock` intacto. |

## Known Stubs

Ninguno. Los cinco métodos, los diez shims y los treinta y ocho tests están completos y ejercitados. El retorno `dict[str, Any]` del par de feriados no es un stub sino la decisión de contrato D-06/D-07 (la OpenAPI en vivo declara los cinco `200` como `object` sin schema).

## Threat Flags

Ninguno. No se introdujo superficie de seguridad fuera del `<threat_model>` del plan: no hay endpoints nuevos más allá de los cinco planificados, no se tocó el gate, ni el `RedactingFilter`, ni el `__repr__` redactor, ni los constructores de `Client`/`AsyncClient`.

## Issues Encountered

- **El worktree arrancó sin dev-dependencies** (`Failed to spawn: pytest`), exactamente como reportaron los Planes 01 y 02. Resuelto con `uv sync --all-packages --all-extras --dev --frozen`. Vale la pena que el orchestrator lo agregue al preámbulo de los ejecutores en worktree de la próxima wave.
- Nada más. El resto salió tal cual del plan: firmas, builders, parsers y las cuatro divergencias sync/async.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **Plan 04 desbloqueado.** Hereda, tal como asignó este plan, las tres pruebas que sólo tienen sentido a su nivel: (a) la matriz adversarial de refusals con CERO requests para los cinco métodos, (b) el zero-HTTP end-to-end de `delete_holiday("../config")` (D-18/T-26-01) y (c) el no-retry dispatch-level de `add_holidays` contra un 503 repetido (D-15/T-26-07).
- **Plan 04 debe agregar 8 nombres a `__init__.__all__`:** los 5 shims sync (`set_calendar_config`, `delete_calendar_config`, `preview_calendar_config`, `add_holidays`, `delete_holiday`) más los 3 modelos del Plan 01. Los shims async NO se re-exportan — viven bajo `aio` y hoy el namespace plano no los tiene (verificado).
- **Sin cambios en:** `_core.py`, `models.py`, `_state.py`, `exceptions.py`, `_transport.py`, `_atransport.py`, `_params.py`, `_logging.py`, `tests/conftest.py`, `pyproject.toml`, `uv.lock`, `__init__.py`, `REQUIREMENTS.md`, `STATE.md`, `ROADMAP.md`.
- **`__version__` sigue en `"0.3.1"`** — el bump es Phase 28.
- **Sin blockers.**

## Self-Check: PASSED

- `packages/market-data-client/src/market_data_client/client.py` — FOUND (modificado)
- `packages/market-data-client/src/market_data_client/aio.py` — FOUND (modificado)
- `packages/market-data-client/tests/test_calendar_write.py` — FOUND (creado)
- `packages/market-data-client/tests/test_calendar_write_async.py` — FOUND (creado)
- Commits `b286b2d`, `3eb77cb`, `41171ec`, `bc3a21d` — FOUND en `git log`
- Cero deleciones de archivos tracked en el rango del plan
- Sin modificaciones a STATE.md ni ROADMAP.md (worktree mode — los escribe el orchestrator)

## TDD Gate Compliance

Ambas tasks siguieron el ciclo completo: cada una tiene su commit `test(...)` (RED, con los fallos verificados antes de implementar — 20 y 18 respectivamente) seguido de su commit `feat(...)` (GREEN). No hubo commits `refactor(...)` porque no quedó limpieza pendiente.

---
*Phase: 26-calendar-write*
*Completed: 2026-07-31*
