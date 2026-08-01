---
phase: 26-calendar-write
plan: 02
subsystem: api
tags: [market-data-client, request-builders, parser, path-safety, calendar, python, httpx]

# Dependency graph
requires:
  - phase: 20-market-data-client
    provides: "RequestSpec (con authenticated/idempotent/endpoint_name), raise_for_response, el patrón body-consume-then-raise de los parsers"
  - phase: 25-symbols-write
    provides: "el template de builder con body YA serializado (build_create_symbol_request) y el precedente de ValueError pelado para validación client-side"
provides:
  - "build_set_calendar_config_request — PUT /calendar/config, idempotent=True"
  - "build_delete_calendar_config_request — DELETE /calendar/config, sin json_body"
  - "build_preview_calendar_config_request — POST /calendar/config/preview, idempotent=True"
  - "build_add_holidays_request — POST /calendar/holidays, idempotent=False (primero del paquete)"
  - "build_delete_holiday_request — DELETE /calendar/holidays/{day} con guard de path-safety D-18"
  - "parse_calendar_write_response — passthrough dict tolerante para el par de feriados"
  - "6 entradas nuevas en _core.__all__ (32 nombres, ASCII-ordenado)"
affects: [26-03 (shells sync/async), 26-04 (superficie pública + test no-retry dispatch-level), 27-live-verification]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Guard de path-safety en un builder: rechaza en lugar de sanitizar (D-18) — SIN análogo previo en el repo"
    - "Parser passthrough tolerante: body ausente/null/list/escalar degrada a {} en lugar de levantar json.JSONDecodeError"
    - "Primer builder idempotent=False del paquete, escrito explícito pese al default de RequestSpec"

key-files:
  created: []
  modified:
    - packages/market-data-client/src/market_data_client/_core.py
    - packages/market-data-client/tests/test_core.py

key-decisions:
  - "Un solo parser (parse_calendar_write_response) sirve a add_holidays y delete_holiday — mismo contrato, misma tolerancia, menos superficie (resuelve la discreción 'uno o dos' de CONTEXT.md a favor de uno)"
  - "El guard D-18 se implementa con una tupla de tokens a nivel de módulo (_PATH_SEGMENT_ESCAPES = ('/', '?', '#', '..')) y una comprobación explícita, no con regex ni percent-encoding"
  - "El docstring del guard evita el literal 'urllib' para mantener limpio el grep de disciplina D-18 del plan, sin perder la explicación de por qué NO se usa quoting"
  - "parse_health_response NO se reusó (levanta sobre body vacío y su anotación miente para null/list); se copió sólo su orden body-consume-then-raise"
  - "REQUIREMENTS.md no se tocó: MUT-MD-02 abarca los 4 planes de la fase y sólo queda completo tras el Plan 04 — el orchestrator lo marca centralmente"

patterns-established:
  - "Path-param guard: validar el segmento ANTES de interpolar; ValueError pelado (jerarquía MarketData* reservada a errores de contrato del servidor)"
  - "Tolerant passthrough parser: read → raise_for_response → guard de content vacío → guard de isinstance(dict) → return"
  - "Idempotencia load-bearing: escribir idempotent=False explícito aunque el dataclass ya lo defaultee, para que sea visible en el diff"

requirements-completed: [MUT-MD-02]

# Metrics
duration: 12min
completed: 2026-07-31
status: complete
---

# Phase 26 Plan 02: Calendar Write Builders + Tolerant Parser Summary

**Cinco builders puros de calendar write en `_core.py` — con el único `idempotent=False` del paquete, dos DELETE sin body ni `Content-Type`, y un guard de path-safety que corta el retargeting de request verificado (`day="../config"` → `DELETE /api/calendar/config`) — más un parser passthrough tolerante que degrada a `{}` en vez de levantar `json.JSONDecodeError`.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-08-01T01:10:00Z
- **Completed:** 2026-08-01T01:22:00Z
- **Tasks:** 3 (todas TDD: RED → GREEN)
- **Files modified:** 2

## Accomplishments

- **Cinco builders puros nuevos** en `_core.py`, todos `authenticated=True`, todos state-independent (`del state`), todos IO-free: `build_set_calendar_config_request` (PUT `/calendar/config`), `build_delete_calendar_config_request` (DELETE `/calendar/config`), `build_preview_calendar_config_request` (POST `/calendar/config/preview`), `build_add_holidays_request` (POST `/calendar/holidays`) y `build_delete_holiday_request` (DELETE `/calendar/holidays/{day}`).
- **Idempotencia per DM-03 / D-04 (ROADMAP SC#4):** `True` para los cuatro replay-safe; `False` EXPLÍCITO sólo para `POST /calendar/holidays` — el primer consumidor `idempotent=False` del paquete, que corta el loop de `RetryTransport` en su primera línea y evita feriados duplicados por reintento (T-26-07).
- **Guard de path-safety D-18 (T-26-01), sin análogo previo en el repo:** `build_delete_holiday_request` levanta un `ValueError` PELADO si `day` es vacío o contiene `/`, `?`, `#` o `..`, ANTES de construir el `RequestSpec`. Rechaza en lugar de sanitizar, así que D-03 (interpolación RAW byte a byte) sigue valiendo para toda fecha ISO legítima y D-13 sigue valiendo (`"2026-13-45"` pasa el guard y va al `422` del servidor).
- **Los dos builders DELETE omiten `json_body` por completo** (queda en su default `None`): con httpx 0.28.1 eso emite `content == b""` y ningún header `Content-Type`, mientras que `json={}` emitiría `b"{}"` + `Content-Type: application/json` (D-02 / T-26-08).
- **`parse_calendar_write_response` nuevo y tolerante (D-06/D-07, T-26-13):** body vacío, `null`, lista o escalar degradan a `{}`; el orden body-consume-then-raise se preserva, así que 401/403 → `MarketDataAuthError`, 429 → `MarketDataRateLimitError` y 422 → `MarketDataAPIError` siguen mapeados por `raise_for_response` sin manejo nuevo.
- **25 tests nuevos** en `test_core.py` (36 → 56 en el archivo; 191 → 216 en el paquete), incluidos los cinco inputs hostiles del guard parametrizados y una aserción de que el mensaje del `ValueError` no filtra `base_url`, token ni `client_secret` (T-26-14).
- **`_core.__all__` extendido con seis nombres** insertados en orden ASCII (32 entradas), sin disparar `RUF022`.

## Task Commits

Cada task se commiteó atómicamente siguiendo el ciclo TDD (RED → GREEN):

1. **Task 1: Cuatro builders de calendar write** — `6a9bb86` (test, RED) → `ef62bb7` (feat, GREEN)
2. **Task 2: build_delete_holiday_request + guard D-18** — `f76ac52` (test, RED) → `92f3286` (feat, GREEN)
3. **Task 3: parse_calendar_write_response + `_core.__all__`** — `58f27ac` (test, RED) → `5ac9eaa` (feat, GREEN)

_No hizo falta un paso REFACTOR: los cuerpos GREEN ya salieron en la forma final del template._

## Files Created/Modified

- `packages/market-data-client/src/market_data_client/_core.py` — sección nueva «Calendar write builders (MUT-MD-02)» con los cinco builders y la constante `_PATH_SEGMENT_ESCAPES`; `parse_calendar_write_response` junto a `parse_calendar_config_response`; seis entradas nuevas en `__all__`.
- `packages/market-data-client/tests/test_core.py` — tres secciones nuevas (builders de calendar write, guard de path-safety, parser passthrough) con 25 tests; import de `MarketDataError` agregado para la aserción de jerarquía.

## Decisions Made

- **Un solo parser para el par de feriados.** `add_holidays` y `delete_holiday` comparten contrato (`200` declarado como `object` sin schema en la OpenAPI en vivo) y tolerancia, así que se escribió una sola función en lugar de dos — menos superficie que mantener hasta que Phase 27 (LIVE-MUT-01) capture la forma real.
- **Guard implementado como tupla de tokens + comprobación explícita**, no regex ni `quote()`: `_PATH_SEGMENT_ESCAPES = ("/", "?", "#", "..")` a nivel de módulo con `any(token in day for token in ...)`. Mantiene el guard estrictamente más angosto que un escape de quoting, que es lo que preserva D-03.
- **El docstring del guard evita el literal `urllib`.** El plan define un grep de disciplina (`_core.py` no debe contener `urllib`); el docstring explica igual por qué NO se percent-encodea, redactado como «estrictamente más angosto que un escape de quoting». Cero llamadas a `urllib.parse.quote` y el grep queda limpio.
- **`parse_health_response` NO se reusó.** Se copió sólo su orden `resp.read()` → `raise_for_response(resp)`; sus guards ausentes (levanta `json.JSONDecodeError` sobre body vacío, anotación que miente para `null`/lista) son exactamente lo que D-07 corrige.
- **`CalendarDay` y `parse_calendar_response` no aparecen en el diff** (D-16): el par de lectura está roto contra el wire real y el retorno del par de feriados es `dict[str, Any]`.
- **`REQUIREMENTS.md` no se modificó.** `MUT-MD-02` abarca los cuatro planes de la fase; marcarlo completo desde este worktree sería prematuro y conflictivo en paralelo. El orchestrator lo marca centralmente al cerrar la fase.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `pytest.raises(ValueError)` sin `match=` disparaba ruff PT011**

- **Found during:** Task 2 (`build_delete_holiday_request` + guard D-18)
- **Issue:** Dos tests del guard usaban `pytest.raises(ValueError) as exc_info` sin el parámetro `match`. El ruleset `PT` del repo marca eso como `PT011` («too broad»), lo que rompía `uv run ruff check` — un gate de aceptación de la propia task.
- **Fix:** Se agregó `match="day"` a ambos `pytest.raises`. Refuerza además la aserción: verifica que el mensaje nombra el parámetro rechazado, que es parte de la mitigación T-26-14.
- **Files modified:** `packages/market-data-client/tests/test_core.py`
- **Verification:** `uv run ruff check packages/market-data-client` → «All checks passed!»; los 11 tests de la task siguen verdes.
- **Committed in:** `92f3286` (commit GREEN de la Task 2)

**2. [Rule 3 - Blocking] El venv del worktree arrancó sin las dev-dependencies**

- **Found during:** Baseline previo a la Task 1
- **Issue:** `uv run --package market-data-client pytest ...` falló con `Failed to spawn: pytest`. El grupo `dev` vive en el `[dependency-groups]` del root del workspace, y el `.venv` recién creado del worktree se había resuelto sólo con las deps runtime del paquete.
- **Fix:** `uv sync --all-packages --all-extras --dev --frozen` (el comando de setup documentado en CLAUDE.md). Ningún cambio de archivos; `uv.lock` intacto (`--frozen`).
- **Files modified:** ninguno (sólo el `.venv/`, no versionado)
- **Verification:** Baseline reproducido exactamente — «191 passed in 0.24s», el número que el plan declara como baseline de la fase.
- **Committed in:** N/A (sin cambios en el repo)

**3. [Rule 2 - Missing Critical] Test de no-filtración del mensaje del guard (T-26-14)**

- **Found during:** Task 2
- **Issue:** El bloque `<behavior>` de la task no listaba una aserción para T-26-14, pero el `<threat_model>` del plan le asigna disposición **mitigate** y dice explícitamente «Testeable: aserción de que el mensaje no contiene el `base_url` ni el token del state configurado». Una mitigación del threat register sin test es un requisito de corrección ausente.
- **Fix:** Se agregó `test_build_delete_holiday_request_guard_message_leaks_no_state`, que construye un `_ClientState` con `base_url`, `token` y `client_secret` marcados y asserta que ninguno aparece en `str(exc)`.
- **Files modified:** `packages/market-data-client/tests/test_core.py`
- **Verification:** Test verde; el guard levanta antes del `del state` y sólo formatea `day!r`.
- **Committed in:** `f76ac52` (RED) / `92f3286` (GREEN)

---

**Total deviations:** 3 auto-fixed (2 blocking, 1 missing critical)
**Impact on plan:** Ninguna alteró el contrato del plan. Las dos blocking eran de entorno/lint y las resolvió el comando documentado del propio repo; la de Rule 2 cubre una mitigación que el threat model ya exigía. Sin scope creep: cero archivos fuera de los dos declarados en `files_modified`.

## Issues Encountered

- **`uv run --package <pkg>` en un worktree fresco no hereda el grupo `dev` del root.** Documentado arriba como deviation 2. Vale la pena saberlo para los otros ejecutores en worktree de esta misma wave: correr `uv sync --all-packages --all-extras --dev --frozen` una vez antes de cualquier gate.
- Nada más. El resto del plan se ejecutó exactamente como estaba escrito: paths, `endpoint_name`s, idempotencias y el shape del parser salieron tal cual de 26-PATTERNS.md.

## Verification Evidence

| Gate | Comando | Resultado |
|---|---|---|
| Suite del paquete | `uv run --package market-data-client pytest packages/market-data-client/tests -q` | **216 passed in 0.25s** (baseline 191 + 25 nuevos, cero regresiones) |
| Lint | `uv run ruff check .` | All checks passed! |
| Format | `uv run ruff format --check .` | 191 files already formatted |
| Typecheck | `uv run mypy packages/market-data-client/src` | Success: no issues found in 11 source files |
| `__all__` | `assert want <= set(_core.__all__)` + `list(...) == sorted(...)` | ok (32 nombres, ASCII-ordenado) |
| Disciplina IO-free | inspección de source de los 5 builders: contienen `del state`, sin `httpx.` / `self.` / `_ensure_` | ok |
| Disciplina D-18 | `grep -c urllib packages/market-data-client/src/market_data_client/_core.py` | **0** (el guard rechaza, no sanitiza) |
| D-16 | `grep -n CalendarDay _core.py` | sólo en el código pre-existente; cero apariciones en el diff de la fase |

## Threat Mitigations Verified

| Threat ID | Mitigación | Evidencia en este plan |
|---|---|---|
| T-26-01 (Tampering) | Guard D-18 sobre `day` | 5 inputs hostiles parametrizados con `pytest.raises(ValueError, match="day")`; el guard corre ANTES del `RequestSpec`. La prueba end-to-end de CERO requests HTTP queda para el Plan 04 Task 1 (requiere el shell). |
| T-26-07 (Tampering) | `idempotent=False` en `build_add_holidays_request` | `assert spec.idempotent is False`. La prueba dispatch-level de exactamente 1 request contra 503 repetido queda para el Plan 04 Task 2 (D-15). |
| T-26-08 (Tampering) | Los dos DELETE omiten `json_body` | `assert spec.json_body is None` en ambos. La verificación en el wire queda para el Plan 03. |
| T-26-13 (DoS) | Parser tolerante | 4 tests de degradación a `{}` (vacío, `null`, lista, escalar) + 3 de mapeo de error. |
| T-26-14 (Info Disclosure) | Mensaje del guard sin secretos | Test dedicado con `base_url`/`token`/`client_secret` marcados (deviation 3). |
| T-26-SC | Sin instalaciones de paquetes | Cero deps nuevas; `uv.lock` intacto (sync con `--frozen`). |

## Known Stubs

Ninguno. Los cinco builders y el parser están completamente implementados y ejercitados; no hay valores hardcodeados ni placeholders. El retorno `dict[str, Any]` del par de feriados no es un stub sino una decisión de contrato (D-06/D-07): la OpenAPI en vivo declara los cinco `200` como `object` sin schema, y Phase 27 (LIVE-MUT-01) capturará la forma real.

## Threat Flags

Ninguno. No se introdujo superficie de seguridad fuera del `<threat_model>` del plan: `_core.py` sigue IO-free, no abre red, no toca disco y no lee estado vivo.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **Wave 2 (Plan 03 — shells sync/async) desbloqueada:** los cinco builders y el parser están exportados en `_core.__all__` y listos para consumo. Recordatorio para el Plan 03: **serializar el modelo en el shell** (`to_dict()` antes de llamar al builder), precedente Phase 25 — los builders reciben el dict ya serializado.
- **Plan 04** hereda dos pruebas que este plan sólo pudo cubrir a nivel builder: (a) cero requests HTTP para `day="../config"` end-to-end (Task 1) y (b) exactamente 1 request contra un 503 repetido para `add_holidays` (Task 2, D-15).
- **Sin cambios en:** `_state.py`, `exceptions.py`, `_transport.py`, `_atransport.py`, `_params.py`, `_logging.py`, `tests/conftest.py`, `pyproject.toml`, `uv.lock`, `__version__` (sigue en **v0.3.1** — el release es Phase 28).
- **Sin blockers.**

---
*Phase: 26-calendar-write*
*Completed: 2026-07-31*
