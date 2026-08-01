---
phase: 26-calendar-write
plan: 01
subsystem: api
tags: [market-data-client, request-models, serialization, calendar, python, dataclasses]

# Dependency graph
requires:
  - phase: 25-symbols-write
    provides: "NewSymbol / NewSymbols / SymbolPatch — el template de request-model frozen con to_dict() a mano y bound 1-500 en __post_init__"
  - phase: 21-models
    provides: "models.py con SafeModel/_coerce y LatestRequest; _params.drop_none en _params.py"
provides:
  - "MarketHoursIn — request model del PUT /calendar/config y POST /calendar/config/preview, con defaults verbatim de la OpenAPI en vivo y el guardrail confirm: bool = False siempre emitido"
  - "HolidayIn — request model de un feriado, primer modelo del paquete con campos nullable (open_time/close_time) que desaparecen del wire vía drop_none"
  - "HolidaysIn — wrapper {\"days\": [...]} con bound client-side 1-500 que corta con ValueError pelado antes de cualquier dispatch"
  - "Primer import intra-paquete de models.py (market_data_client._params) — cadena _core → models → _params sin ciclo"
  - "models.__all__ +3 entradas en orden ASCII"
affects: [26-02-builders, 26-03-client-methods, 26-04-public-surface, 27-live-verification]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Request models serialize-OUT (frozen+slots, NO SafeModel) ruteados por _params.drop_none"
    - "Guardrail booleano como campo defaulteado del modelo (confirm), no como kwarg del método"
    - "Bound de batch client-side con ValueError pelado en __post_init__ de un frozen dataclass"

key-files:
  created: []
  modified:
    - packages/market-data-client/src/market_data_client/models.py
    - packages/market-data-client/tests/test_models.py

key-decisions:
  - "D-08 aplicado: los tres modelos nuevos son @dataclass(frozen=True, slots=True) sin base — NO heredan de SafeModel porque serializan HACIA AFUERA"
  - "D-09: confirm es un campo de MarketHoursIn con default False, siempre emitido en el wire; el consumidor tiene que escribir confirm=True a propósito"
  - "D-11: MarketHoursIn.to_dict() rutea por _params.drop_none aunque sea no-op (consistencia); en HolidayIn es load-bearing y en HolidaysIn no se usa (wrapper puro)"
  - "D-12: el bound 1-500 levanta ValueError pelado, no una subclase de MarketDataError — esa jerarquía queda reservada para errores de contrato del servidor"
  - "D-13: ningún bound escalar se valida client-side (pre_open_minutes 0-120, timezone 1-64, updated_by <=200, description <=500, formato de hora) — van al 422 del servidor"

patterns-established:
  - "Import first-party en models.py: `from market_data_client import _params` en bloque propio tras los stdlib (ruff I001), sin ciclo porque _params sólo importa typing"
  - "Mensaje de bound con el substring literal `1-500` para que los tests matcheen por ahí (mismo criterio que NewSymbols)"

requirements-completed: [MUT-MD-02]

# Metrics
duration: 18min
completed: 2026-08-01
status: complete
---

# Phase 26 Plan 01: Calendar write request models Summary

**Tres request-models frozen (`MarketHoursIn`, `HolidayIn`, `HolidaysIn`) que serializan hacia afuera con los defaults verbatim de la OpenAPI en vivo, el guardrail `confirm=False` siempre en el wire, ruteo por `_params.drop_none` y el bound 1-500 cortando client-side con `ValueError` pelado.**

## Performance

- **Duration:** ~18 min
- **Started:** 2026-08-01T00:58:00Z (aprox.)
- **Completed:** 2026-08-01T01:16:29Z
- **Tasks:** 2 (ambas TDD: RED → GREEN)
- **Files modified:** 2

## Accomplishments

- `MarketHoursIn` emite las 7 claves de la OpenAPI en vivo con sus defaults exactos (`pre_open_minutes=10`, `enabled=True`, `updated_by=""`, `confirm=False`) — el guardrail `confirm` es un campo del modelo, no un kwarg suelto, así que overwritear una config con warnings exige un opt-in explícito (ROADMAP SC#2, mitigación T-26-02).
- `HolidayIn` es el primer request model del paquete con campos nullable: `open_time`/`close_time` DESAPARECEN del wire cuando son `None` vía `_params.drop_none`, mientras `closed=True` y `description=""` (falsy pero no-`None`) siguen viajando (ROADMAP SC#3).
- `HolidaysIn` envuelve la lista tipada y corta client-side fuera de 1–500 con un `ValueError` pelado en `__post_init__`, antes de construir cualquier spec o tocar HTTP (mitigación T-26-03, ASVS V5).
- `models.py` gana su primer import intra-paquete (`from market_data_client import _params`); la cadena queda `_core → models → _params` y `import market_data_client` sigue limpio (sin ciclo).
- Suite del paquete: **191 → 206 tests** (+15), todos en verde; ruff, ruff-format y mypy strict limpios.

## Task Commits

Cada tarea se commiteó atómicamente siguiendo el ciclo TDD:

1. **Task 1: MarketHoursIn + HolidayIn (frozen, to_dict vía drop_none)**
   - `7597ad8` (test — RED)
   - `cd913f0` (feat — GREEN)
2. **Task 2: HolidaysIn (wrapper + bound 1-500 ValueError) + models.__all__**
   - `36526b6` (test — RED)
   - `5f793f3` (feat — GREEN)

No hizo falta commit de REFACTOR: la implementación entró en forma final siguiendo el template de Phase 25.

## Files Created/Modified

- `packages/market-data-client/src/market_data_client/models.py` — +3 clases (`MarketHoursIn`, `HolidayIn`, `HolidaysIn`) bajo un divisor de sección propio ubicado entre `SymbolPatch` y los reference models; import nuevo de `_params`; `__all__` +3 en orden ASCII.
- `packages/market-data-client/tests/test_models.py` — +15 tests: serialización con defaults verbatim, opt-in de `confirm`, preservación de falsy-no-`None`, drop de las horas nullable, no-herencia de `SafeModel`, inmutabilidad (`FrozenInstanceError`), wrapper anidado, bounds vacío/501/boundary 1 y 500, tipo exacto del error del bound y contenido de `models.__all__`.

## Decisions Made

Ninguna decisión nueva — se aplicaron las decisiones ya lockeadas en 26-CONTEXT.md (D-08 a D-13) tal como las bajó el plan. Dos detalles de implementación menores:

- El mensaje del bound quedó `"HolidaysIn requires 1-500 days, got {n}"` — conserva el substring `1-500` exigido por el plan (espeja el de `NewSymbols`).
- El orden de campos de `MarketHoursIn` sigue el de la tabla de la OpenAPI (`open_time`, `close_time`, `timezone`, `pre_open_minutes`, `enabled`, `updated_by`, `confirm`), y `to_dict()` emite las claves en ese mismo orden.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- El worktree arrancó sin las dev-dependencies instaladas (`uv run --package market-data-client pytest` fallaba con `Failed to spawn: pytest`). Se resolvió corriendo el paso estándar de bootstrap del repo, `uv sync --all-packages --all-extras --dev --frozen`; no implicó cambio de código ni de `uv.lock`. Baseline confirmado en 191 passed antes de tocar nada.

## Known Stubs

None — los tres modelos están completos y ejercitados por tests.

## Threat Flags

Ninguna superficie nueva fuera del `<threat_model>` del plan. Las mitigaciones asignadas quedaron cubiertas y testeadas:

- **T-26-02** (Tampering — overwrite salteando el warning del servidor): `confirm: bool = False` como campo siempre emitido; `test_market_hours_in_to_dict_openapi_defaults_verbatim` pinea `confirm: False` por default y `test_market_hours_in_confirm_opt_in_is_true` el opt-in.
- **T-26-03** (DoS / Input Validation — batch vacío o sobredimensionado): `ValueError` client-side 1–500 antes de cualquier HTTP; cubierto por los tests de vacío / 501 / boundary y por el test de tipo exacto del error.
- **T-26-11** (Tampering — claves de wire): los tres modelos emiten snake_case verbatim y los tests assertan el dict completo clave por clave. Confirmación final contra develop queda para Phase 27 (LIVE-MUT-01).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- La capa de serialización de MUT-MD-02 está lista para que Plan 02 construya los cinco builders y el parser en `_core.py` consumiendo `MarketHoursIn.to_dict()` / `HolidaysIn.to_dict()`.
- Plan 04 debe agregar `HolidayIn`, `HolidaysIn` y `MarketHoursIn` a `__init__.__all__` (este plan sólo tocó `models.__all__`).
- `__version__` sigue en `"0.3.1"` — el bump es Phase 28, como manda el plan.
- Assumption abierta A3 (dropear la clave vs. mandar `null` para `open_time`/`close_time`): se revalida en vivo en Phase 27.

## Self-Check: PASSED

- Archivos verificados en disco: `packages/market-data-client/src/market_data_client/models.py`, `packages/market-data-client/tests/test_models.py`, `.planning/phases/26-calendar-write/26-01-SUMMARY.md`.
- Commits verificados en `git log`: `7597ad8`, `cd913f0`, `36526b6`, `5f793f3`, `c25b8b1`.
- Working tree limpio; sin cambios en STATE.md ni ROADMAP.md (worktree mode — los escribe el orquestador).

---
*Phase: 26-calendar-write*
*Completed: 2026-08-01*
