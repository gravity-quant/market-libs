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
