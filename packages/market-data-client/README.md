# market-data-client

Cliente HTTP (sync y async) para la API de market data (primary-extractor,
`https://market-data-develop.bbsa.com.ar/api`), con autenticación **Auth0
client-credentials** (grant `client_credentials`, token cacheado y refrescado por TTL).

## Instalación

```bash
uv add market-data-client
# o, dentro del workspace:
uv sync
```

## Uso

### Sync

```python
import market_data_client

snapshots = market_data_client.get_marketdata()
```

### Async

```python
from market_data_client import aio

snapshots = await aio.get_marketdata()
```

## Autenticación

El paquete obtiene un token de Auth0 vía grant `client_credentials` en la primera
llamada, lo cachea y lo refresca antes de expirar. Las credenciales se leen de
variables de entorno (ver `.env.example`):

- `MARKET_DATA_CLIENT_ID`
- `MARKET_DATA_CLIENT_SECRET`
- `MARKET_DATA_AUDIENCE`
- `MARKET_DATA_AUTH0_TOKEN_URL`
- `MARKET_DATA_BASE_URL` (opcional; default `https://market-data-develop.bbsa.com.ar/api`)

Nunca commitear el archivo `.env` con credenciales reales.

## Desarrollo

```bash
# Tests sólo de este paquete
uv run --package market-data-client pytest packages/market-data-client

# Lint
uv run ruff check packages/market-data-client

# Type checking
uv run mypy packages/market-data-client
```

## Changelog

### v0.4.0

**Nueva superficie de escritura: calendar, más los fixes verificados en vivo contra develop**
(features nuevas, minor bump — la superficie de lectura v0.2.0 sigue intacta).

- **Calendar write (MUT-MD-02):** ocho nombres públicos nuevos en el `__all__` plano — los
  request-models `MarketHoursIn`, `HolidayIn` y `HolidaysIn`, y las funciones
  `set_calendar_config`, `delete_calendar_config`, `preview_calendar_config`, `add_holidays` y
  `delete_holiday` — sobre los endpoints `PUT /calendar/config`, `DELETE /calendar/config`,
  `POST /calendar/config/preview`, `POST /calendar/holidays` y `DELETE /calendar/holidays/{day}`.
  Las cinco funciones tienen contraparte async en `market_data_client.aio`
  (`set_calendar_config`, `delete_calendar_config`, `preview_calendar_config`, `add_holidays`,
  `delete_holiday`; shims a nivel de módulo, no re-exportados al namespace plano según la
  convención del monorepo). El guardrail `confirm` se expone explícitamente con default `False`,
  así que nunca se persiste configuración real de mercado de forma implícita. Toda la superficie
  vive detrás del mutating-gate opt-in ya existente (`mutating_allowed=True` + `expected_host`).
- **Fixes verificados en vivo (LIVE-MUT-01):** `update_symbol(symbol_id)` fue **ensanchado** de
  `str` a `int | str` en los cuatro routes (el builder de `_core`, `Client`, `AsyncClient` y
  ambos shims de módulo); `Symbol` gana cinco campos **con default** (`id`, `market_id`,
  `created_at`, `updated_at`, `received_at`); `Symbol.marketId` se **preserva** como alias
  deprecado, espejado desde el `market_id` del wire vía override de `from_api`; y el envelope de
  las respuestas de symbols-write se desenvuelve preservando `list[Symbol]`. Todos son cambios
  estrictamente aditivos o de ensanchamiento — **no rompen** a ningún consumidor v0.3.1.

**Breaking changes** (semver minor bump en línea 0.x) — reemplazo de campos de `CalendarDay`:

- `CalendarDay` **removió** `date`, `marketId` e `isBusinessDay` (sin aliases de compatibilidad)
  y los reemplazó por `day`, `closed`, `description`, `open_time` y `close_time`, reconciliados
  contra el wire real de develop.
- Se shippea dentro de un minor bump porque `parse_calendar_response` iteraba las claves del
  envelope en vez de `days[]`: ningún consumidor publicado pudo haber tenido nunca una instancia
  poblada de `CalendarDay`, de modo que los campos viejos no eran legibles en la práctica. Aun
  así se documenta explícitamente acá para que el reemplazo sea descubrible y no silencioso.

### v0.3.1

**Bugfix (patch):** `get_latest_batch` devolvía snapshots vacíos.

- `parse_latest_response` asumía que `POST /marketdata/latest` (batch) devolvía una lista bare,
  pero el servidor devuelve un envelope `{"requested", "count", "not_found", "server_time", "items": [...]}`.
  Iteraba las claves del dict en vez de `items[]`, produciendo N `MarketDataSnapshot` vacíos. Ahora
  desenvuelve `items` (igual que su hermano `parse_market_data_response`) preservando el path bare-list
  del single `get_latest`; un dict sin `items` degrada a `[]`. Sync y async (fix en `_core.py` compartido).

### v0.3.0

**Nueva superficie de escritura: symbols detrás de un mutating-gate de seguridad**
(features nuevas, minor bump — no rompe la superficie de lectura v0.2.0).

- **Mutating-gate opt-in (GATE-MD-01):** por default `Client()`/`AsyncClient()` rehúsan toda
  mutación con `MarketDataMutationNotAllowedError` (⊂ `MarketDataError`) **sin emitir request
  HTTP ni token Auth0**. Habilitación explícita vía `mutating_allowed=True` (constructor o
  `configure()`), más un segundo **gate de host exacto** (`expected_host`, comparación exacta
  de hostname — nunca substring) que impide mutar contra un `base_url` inesperado. El flag vive
  en el estado compartido, así que las vistas de `with_options()` lo heredan; `configure()` usa
  centinela `bool | None` para no resetear un opt-in previo al reconfigurar `base_url`.
- **Symbols write (MUT-MD-01):** `create_symbol` (`NewSymbol`), `create_symbols`
  (batch 1–500, `NewSymbols`) y `update_symbol` (`SymbolPatch`), en sync y async, con
  request-models tipados serializados a JSON y respuestas `SafeModel` tolerantes; `422`
  levanta error tipado. Las tres operaciones se despachan como idempotentes
  (`request.extensions["idempotent"]=True`) según el spec.

### v0.2.0

**Breaking changes** (semver minor bump en línea 0.x) — reconciliación del cliente
contra la API en vivo tras la verificación `LIVE-MD-01`:

- `get_latest(symbol=...)` ahora es **requerido** (la API devuelve 422 sin él).
- `MarketDataSnapshot` reconciliado contra el wire de develop: `marketId` → `market_id`;
  agregados `active`, `market_data`, `staleness_seconds`, `note`; se retiró el
  `MarketDataEntry` inventado.
- `CalendarConfig` reconciliado: se eliminó `businessDays`; se agregaron `open`, `close`,
  `enabled`, `editable`, `env_bypass`, `pre_open_minutes`, `source`, `updated_at`,
  `updated_by`, `warnings`.
- Corregido el envelope-unwrap de `parse_market_data_response` (`get_market_data` ahora
  lee `items[]`).
