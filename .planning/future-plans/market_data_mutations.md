# Plan de milestone — `v1.5 · market-data-client · mutaciones`

> Plan futuro (no ejecutado). Fuente: OpenAPI 3.1 de `https://market-data-develop.bbsa.com.ar/api/openapi.json`
> (title "primary-extractor"). Redactado 2026-07-31. Continúa el paquete `market-data-client`
> publicado en v0.2.0 (v1.4 = superficie de **lectura**; v1.5 = superficie de **escritura**).

**Objetivo:** extender `market-data-client` con la superficie de **mutación** de la API
primary-extractor —symbols (create/batch/patch) y calendar (config + holidays)— detrás de un
**mutating-gate de seguridad** espejando el patrón de `matriz-client`, verificarla en vivo contra
develop de forma segura (sin corromper estado), y publicar **v0.3.0** por el pipeline de tags.

**Core value:** que las mutaciones del cliente reflejen fielmente el contrato de la API develop y
sean **imposibles de disparar por accidente** (opt-in explícito + gate de entorno + no-retry de
operaciones no idempotentes), con la misma calidad (dual sync/async, modelos/params tipados,
logging redactado, tests, verificación en vivo) que el resto del monorepo.

## Superficie de la API (mutaciones — referencia verificada contra el OpenAPI vivo)

Server base `/api`. Todas requieren **Auth0** (`security: Auth0`).

### Symbols
| Método | Path | Request body | Resp | Notas |
|--------|------|--------------|------|-------|
| POST | `/symbols` | `NewSymbol` | 201/422 | crear un símbolo. Idempotente (dice el spec) |
| POST | `/symbols/batch` | `NewSymbols` (1–500) | 200/422 | crear varios. **Idempotente** — evita reconnects del ingestor |
| PATCH | `/symbols/{symbol_id}` | `SymbolPatch` | 200/422 | actualizar (activar/desactivar) |

### Calendar
| Método | Path | Request body | Resp | Notas |
|--------|------|--------------|------|-------|
| PUT | `/calendar/config` | `MarketHoursIn` | 200/422 | setear horario de mercado. Tiene flag `confirm` |
| DELETE | `/calendar/config` | — | 200 | resetear config |
| POST | `/calendar/config/preview` | `MarketHoursIn` | 200/422 | **preview** — no persiste (POST pero es de sólo cálculo) |
| POST | `/calendar/holidays` | `HolidaysIn` | 200/422 | agregar feriados |
| DELETE | `/calendar/holidays/{day}` | — | 200/422 | borrar un feriado (`day` en el path) |

### Schemas de request (a modelar como request-models tipados)
```jsonc
NewSymbol   = { symbol: str(1-255, req, ej "DLR/DIC26"), market_id: str(default "ROFX") }
NewSymbols  = { symbols: [NewSymbol] (1-500, req) }
SymbolPatch = { active: bool (req) }
MarketHoursIn = { open_time: "HH:MM"(req, ej "10:00"), close_time: "HH:MM"(req, ej "17:00"),
                  timezone: str(req, ej "America/Argentina/Buenos_Aires"),
                  pre_open_minutes: int(default 10), enabled: bool(default True),
                  updated_by: str(default ""), confirm: bool(default False) }
HolidayIn   = { day: str(req), closed: bool(default True), open_time: str|None,
                close_time: str|None, description: str(default "") }
HolidaysIn  = { days: [HolidayIn] (req) }
```

## Decisiones bloqueadas (D-locks)

| ID | Decisión |
|----|----------|
| DM-01 | Extiende el paquete existente `market-data-client` (v0.2.0) — NO un paquete nuevo. Import/dist sin cambios. |
| DM-02 | **Mutating-gate de seguridad** espejando `matriz-client`: las mutaciones sólo disparan si el consumidor opta explícitamente (p.ej. `Client(mutating_allowed=True)` o `configure(mutating_allowed=True)`); por default el cliente rehúsa toda mutación con un error tipado claro. Segundo gate: verificación de host/entorno (no mutar contra un base_url inesperado). Espeja `verification/mutation_gate.py`. |
| DM-03 | **Idempotencia por-endpoint** (load-bearing para retries): `idempotent=True` (retry-safe) para `POST /symbols`, `POST /symbols/batch` (spec lo declara idempotente), `PATCH /symbols/{id}` (set de bool), `PUT`/`DELETE /calendar/config`, `DELETE /calendar/holidays/{day}` (semántica HTTP idempotente) y `POST /calendar/config/preview` (sólo cálculo). `idempotent=False` (NO retry) para `POST /calendar/holidays` (append no idempotente) salvo que se confirme lo contrario en vivo. Se revalida en la fase de verificación. |
| DM-04 | Requests con **dataclasses/params tipados** (`NewSymbol`/`NewSymbols`/`SymbolPatch`/`MarketHoursIn`/`HolidayIn`/`HolidaysIn`) serializados a JSON; respuestas siguen con `SafeModel` tolerante (`from_api`). Reutiliza `_params.drop_none`. |
| DM-05 | Todo fix/lógica se **espeja sync (`client.py`) + async (`aio.py`)**, dispatch por `_core.py` builders (constraint del monorepo). |
| DM-06 | La verificación en vivo (Phase 27) usa **símbolos/feriados de prueba dedicados** y hace **cleanup** (crear→verificar→revertir con el DELETE correspondiente); NUNCA toca config real de mercado sin `confirm`. Sólo develop; el mutating-gate impide prod. |
| DM-07 | Mutaciones = features nuevas → **minor bump v0.3.0** (no breaking sobre la superficie de lectura v0.2.0). Publicación por tag `market-data-client-v0.3.0` (mismo flujo que v0.2.0). |
| DM-08 | Fuera de alcance de v1.5 (siguen en backlog v2): streaming SSE `GET /marketdata/stream`, cache de token en disco (`SEC-MD-01`), validación de firma JWT (`SEC-MD-02`). |

## Requisitos → fases

| Req | Descripción | Fase |
|-----|-------------|------|
| GATE-MD-01 | Mutating-gate de seguridad (opt-in `mutating_allowed` + gate de entorno + no-retry de no-idempotentes), dual sync/async | 25 |
| MUT-MD-01 | Symbols write: `POST /symbols`, `POST /symbols/batch`, `PATCH /symbols/{symbol_id}` + request-models | 25 |
| MUT-MD-02 | Calendar write: `PUT`/`DELETE /calendar/config`, `POST /calendar/config/preview`, `POST /calendar/holidays`, `DELETE /calendar/holidays/{day}` + request-models | 26 |
| LIVE-MUT-01 | Verificación en vivo (segura, con cleanup) de toda la superficie de mutación contra develop + fixes in-cycle | 27 |
| PUB-MUT-01 | Publicación `market-data-client-v0.3.0` (README/changelog, versión, PR, tag, GitHub Release) | 28 |

## Roadmap (4 fases — continúa la numeración de v1.4; empieza en Phase 25)

### Phase 25 — Mutating-gate + Symbols write (GATE-MD-01, MUT-MD-01)
- **Mutating-gate (GATE-MD-01):** `mutating_allowed` opt-in en `Client`/`AsyncClient` (`__init__` + `configure()`); toda mutación chequea el flag ANTES del dispatch y levanta un error tipado nuevo (`MarketDataMutationNotAllowedError` ⊂ `MarketDataError`) si no está habilitado. Segundo gate de entorno (host/base_url esperado). El flag por-call `request.extensions["idempotent"]` ya existe en el transporte v1.1+; los builders de mutación lo setean per DM-03.
- **Symbols (MUT-MD-01):** `create_symbol(NewSymbol)`, `create_symbols(NewSymbols)` (batch), `update_symbol(symbol_id, SymbolPatch)` en sync+async, vía 3 builders `_core` + parsers tolerantes; request-models `NewSymbol`/`NewSymbols`/`SymbolPatch`.
- Tests mockeados (pytest-httpx): gate ON/OFF (rehúsa sin opt-in), serialización de body, `201`/`200` parse, `422` → error tipado, no-retry de no-idempotentes, paridad sync/async.
- 4 gates verdes (ruff/format/mypy-strict/pytest).

### Phase 26 — Calendar write (MUT-MD-02) *(paraleliza con 25 tras el gate; depende de GATE-MD-01)*
- `set_calendar_config(MarketHoursIn)` (PUT), `delete_calendar_config()` (DELETE),
  `preview_calendar_config(MarketHoursIn)` (POST preview), `add_holidays(HolidaysIn)` (POST),
  `delete_holiday(day)` (DELETE) en sync+async, vía builders `_core` + parsers.
- Request-models `MarketHoursIn`/`HolidayIn`/`HolidaysIn`; respeta `confirm`/defaults.
- El `preview` es sólo-cálculo → puede clasificarse read-safe pero igual pasa por el gate (POST); documentar la excepción.
- Tests mockeados (gate, serialización, defaults, `confirm`, `422`, paridad).

### Phase 27 — Verificación en vivo segura + fixes (LIVE-MUT-01)
- Extiende `main_market_data.py` con probes de mutación **detrás del mutating-gate** (`mutating_allowed=True` sólo bajo env-gate explícito + host develop exacto, patrón `verification/mutation_gate.py`).
- **Ciclo seguro con cleanup** (DM-06): crear símbolo de prueba → `GET /symbols` confirma → `PATCH active=false` → verificar; feriado de prueba → `POST` → `GET /calendar` confirma → `DELETE /calendar/holidays/{day}`; `preview` sin persistir; `PUT /calendar/config` sólo con `confirm=false`/preview salvo autorización operator explícita.
- Toda divergencia (shape de respuesta, idempotencia real, códigos) documentada en findings y corregida in-cycle, espejada sync/async. Revalida DM-03.
- Cycle closure PASS; cada fix con test de regresión mockeado.

### Phase 28 — Release prep + publish v0.3.0 (PUB-MUT-01)
- Bump a `0.3.0` (pyproject + `__version__`); README changelog (nuevas mutaciones + el opt-in del gate); `uv.lock` refresh.
- PR → CI (los 15 checks) verde → merge → tag `market-data-client-v0.3.0` → `release.yml` → GitHub Release con wheel + sdist.

## Riesgos / notas

- **Seguridad de mutación:** el riesgo central es disparar una mutación no deseada (crear símbolos basura, romper la config de calendario). El mutating-gate (opt-in + env-gate) es la mitigación primaria y es load-bearing — es la primera cosa a construir (Phase 25) y a testear adversarialmente.
- **Verificación en vivo destructiva:** a diferencia de v1.4 (sólo lectura), estas probes CREAN/MODIFICAN estado en develop. El cleanup y el uso de identificadores de prueba dedicados son obligatorios (DM-06). Confirmar con el operator qué es seguro tocar en develop antes de Phase 27.
- **Idempotencia real:** el spec declara idempotentes los POST de symbols, pero conviene verificarlo en vivo (Phase 27) antes de confiar el retry-behavior — un POST no idempotente reintentado duplicaría estado.
- **`confirm` en `PUT /calendar/config`:** es un guardrail del servidor; el cliente debe exponerlo explícitamente y defaultearlo a `False`.

## Fuera de alcance de v1.5 (backlog v2)
- Streaming SSE `GET /marketdata/stream` (`STREAM-MD-01`) — transporte dedicado tipo `ws_client` de matriz.
- Cache de token Auth0 en disco (`SEC-MD-01`) — platformdirs + atomic + flock + 0600.
- Validación de firma JWT RS256 contra el JWKS de Auth0 (`SEC-MD-02`).
