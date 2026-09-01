# market-data-client

Cliente HTTP (sync y async) para la API de market data (primary-extractor,
`https://market-data-develop.bbsa.com.ar/api`), con autenticación **Auth0
client-credentials** (grant `client_credentials`, token cacheado y refrescado por TTL).

## Instalación

> **Este paquete NO está publicado en PyPI.** El pipeline de release sólo crea GitHub Releases
> (wheel + sdist). Un `uv add market-data-client` a secas falla — y si algún día ese nombre
> aparece en PyPI, no sería este paquete.

```bash
# git, pineado al tag (recomendado)
uv add "market-data-client @ git+https://github.com/gravity-quant/market-libs.git@market-data-client-v0.7.0#subdirectory=packages/market-data-client"

# o, dentro del workspace:
uv sync
```

Alternativa, wheel de la GitHub Release:

```bash
pip install "https://github.com/gravity-quant/market-libs/releases/download/market-data-client-v0.7.0/market_data_client-0.7.0-py3-none-any.whl"
```

## Uso

### Sync

```python
import market_data_client

snapshots = market_data_client.get_market_data()
```

### Async

```python
from market_data_client import aio

snapshots = await aio.get_market_data()
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

## Mutaciones (opt-in)

Además de la superficie de lectura, el paquete expone una superficie de **escritura**:

- **symbols** (v0.3.0): `create_symbol` (`NewSymbol`), `create_symbols` (batch 1–500,
  `NewSymbols`) y `update_symbol` (`SymbolPatch`).
- **calendar** (v0.4.0): `set_calendar_config`, `delete_calendar_config`,
  `preview_calendar_config` (`MarketHoursIn`), `add_holidays` (`HolidaysIn` / `HolidayIn`) y
  `delete_holiday`.

Todas existen en sync y async, y **todas están cerradas por default**.

### Los dos gates

1. **`mutating_allowed`** — un `Client()` / `AsyncClient()` por default **rehúsa toda mutación**
   con `MarketDataMutationNotAllowedError` (⊂ `MarketDataError`), **sin emitir ni un request HTTP
   ni un round-trip a Auth0**. Se habilita explícitamente con `mutating_allowed=True` (constructor
   o `configure()`).
2. **`expected_host`** — segundo gate: el hostname de `base_url` debe coincidir **exactamente**
   con `expected_host` (match exacto, nunca substring), para que una mutación no pueda dispararse
   contra un entorno inesperado. Dejarlo en `None` deshabilita **sólo** esta segunda pata.

Si cualquiera de las dos falla, la llamada levanta `MarketDataMutationNotAllowedError` antes de
tocar la red.

```python
from market_data_client import Client, MarketHoursIn

with Client(
    mutating_allowed=True,
    expected_host="market-data-develop.bbsa.com.ar",
) as c:
    config = MarketHoursIn(
        open_time="11:00",
        close_time="17:00",
        timezone="America/Argentina/Buenos_Aires",
    )
    preview = c.preview_calendar_config(config)
    # inspeccionar preview.warnings; si el servidor pide segunda opinión,
    # re-emitir con confirm=True:
    #   c.set_calendar_config(dataclasses.replace(config, confirm=True))
    c.set_calendar_config(config)
```

Sobre `confirm`: es un **campo de `MarketHoursIn`** (default `False`) y viaja sólo en
`set_calendar_config` / `preview_calendar_config`. **No es un gate de persistencia** — es la
segunda opinión que el servidor exige cuando la ventana pedida produce warnings; una config sin
warnings se persiste igual con `confirm=False`. `delete_calendar_config`, `add_holidays` y
`delete_holiday` **no tienen** `confirm`: para esas tres, los dos gates de arriba son el único
resguardo.

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

### v0.6.0

**`market_data` deja de ser un diccionario y pasa a ser un Null Object tipado, y
`entries` pierde su `| None`** (breaking, minor bump en línea 0.x — todo consumidor
que lea `market_data` por clave necesita migrar). En la misma tanda, las dos hojas
`market_id` y `active` se ensanchan a nullables (D-12).

| Antes (0.5.0 publicado) | Ahora (0.6.0) |
| --- | --- |
| `snapshot.market_data["LA"]["price"]` | `snapshot.market_data.last.price` |
| `snapshot.market_data["BI"]` | `snapshot.market_data.bids` (`list[BookLevel]`) |
| `if snapshot.market_data is None:` | `if not snapshot.market_data:` |
| `snapshot.entries is None` | `snapshot.entries == []` (nunca `None`) |
| `LatestRequest(entries=None)` | `LatestRequest(entries=[])` (default; la clave `entries` sigue sin viajar cuando la lista está vacía) |
| `snapshot.market_id` era `str` / `snapshot.active` era `bool` (`""` / `False` manufacturados sobre la fila no-data) | `str \| None` / `bool \| None` — el `null` del wire sobrevive como `None`; chequear `is None` |

`market_data` pasó de `dict[str, Any] | None` al Null Object tipado
`MarketDataEntries` (con `BookLevel` / `EntryValue` y los alias `bids`, `offers`,
`last`, `settlement`, `close`, `open_interest`), así que la indexación por clave
levanta `TypeError: 'MarketDataEntries' object is not subscriptable`. `entries` —
tanto en `MarketDataSnapshot` como en `LatestRequest` — perdió su `| None`.

La divergencia que la 0.5.0 arrastraba sobre la fila no-data de
`GET /marketdata/latest` queda **corregida** en esta versión: `market_id` y `active`
llegaban `null` sobre declaraciones no-`Optional`, así que el walker sustituía
`""` / `False` y `strict_decode` levantaba en `.market_id`. Ahora ambos son hojas
nullables y la baseline medida decodifica entera sin emitir una sola divergencia.

### v0.5.0

**Cuatro endpoints de ops dejan de devolver diccionarios y pasan a devolver
modelos tipados** (breaking, minor bump en línea 0.x — mismo criterio y misma
forma que la ruptura dict→modelo de `iol-client` v0.3.0).

| Función | Antes | Ahora |
|---|---|---|
| `get_health` | `dict[str, Any]` | `Health` |
| `get_health_feed` | `dict[str, Any]` | `HealthFeed` |
| `add_holidays` | `dict[str, Any]` | `AddHolidaysResult` |
| `delete_holiday` | `dict[str, Any]` | `DeleteHolidayResult` |

Las cuatro cambian en sus **dos superficies** (método de clase y shim de módulo)
y en **sync y async**. El acceso pasa de `health["status"]` a `health.status`; un
acceso por clave sobre el resultado levanta `TypeError` (los modelos no son
subscriptables). Vale acá el mismo **flip de truthiness** que documenta el
changelog de `iol-client`: un dict vacío es falso, una instancia de dataclass es
verdadera siempre, y el typechecker no atrapa esa rama.

- **Ocho modelos nuevos exportados:** `Health`, `HealthAuth`, `HealthFeed`,
  `FeedIngestor`, `FeedMarket`, `FeedPipeline`, `AddHolidaysResult` y
  `DeleteHolidayResult`, todos en el `__all__` del paquete y en el de
  `market_data_client.models`. Frozen + `slots`, construidos vía
  `SafeModel.from_api()`.
- **Escape hatch:** `to_dict()` reproyecta cualquiera de ellos al dict plano.
  Sirve para call sites de `len()` / `isinstance`; **no** es una entrada válida
  para un snapshot de schema, porque el walker ya coercionó cada campo declarado
  y descartó toda clave no declarada.
- **Tolerancia preservada en las dos mutaciones:** un body ausente, `null`, lista
  o escalar en `add_holidays` / `delete_holiday` sigue degradando al resultado
  zero-valued en lugar de levantar — también bajo `strict_decode`, para que una
  mutación ya publicada nunca responda a un ACK anómalo con una excepción
  levantada después de que la escritura se commiteó. La divergencia se registra
  igual en el logger `market_data_client`.

**Tres fixes de forma sobre modelos ya publicados** (breaking, verificados en vivo
contra develop en la Phase 33 — SC-1, SC-2 y SC-3). Sumados a los cuatro endpoints
de ops de arriba, **esta versión trae siete rupturas de fuente en total**: cuatro
cambios dict→modelo y tres cambios de forma sobre modelos que ya existían.

**SC-1 — `preview_calendar_config` devuelve un sobre de preview dedicado**

- Estaba declarada `-> CalendarConfig`, pero `POST /calendar/config/preview` no
  devuelve una configuración: devuelve un sobre de dry-run distinto. **Nueve** de
  los campos que `CalendarConfig` declara estaban ausentes del wire y se poblaban
  con el zero-value, y **tres campos reales** del sobre —`valid`,
  `requires_confirmation` y `market_after`— se descartaban por no estar
  declarados. El único que coincidía por nombre era `warnings`, que es
  justamente el que hacía el defecto invisible en review.

  | Función | Antes | Ahora |
  |---|---|---|
  | `preview_calendar_config` | `CalendarConfig` | `CalendarConfigPreview` |

- Cambia en sus **dos superficies** (método de clase y shim de módulo) y en
  **sync y async** — cuatro sitios de declaración. `CalendarConfigPreview` es un
  nombre público nuevo, en el `__all__` del paquete y en el de
  `market_data_client.models`, junto con `PreviewMarket`, el modelo anidado que
  tipa `market_after`.
- Todo consumidor que anote el resultado como `CalendarConfig` ahora falla en
  mypy. Todo consumidor que leyera uno de los nueve campos fantasma venía leyendo
  un zero-value y ahora lee el sobre real. El flujo previsto no cambia:
  previsualizar, mirar `warnings`, reemitir `set_calendar_config(...)` con
  `confirm=True` — pero el veredicto llega tipado en vez de reconstruido.

**SC-2 — `MarketDataSnapshot.entries`, `.market_data` y `.staleness_seconds` pasan
a `| None`**

- Los tres estaban declarados no-opcionales y llegan `null` en la fila **no-data**
  de `GET /marketdata/latest`: para un símbolo que el feed nunca entregó, el
  servidor responde con `symbol` y `note` poblados y `null` en todo lo demás. Los
  tres campos de `MarketDataSnapshot` estaban simplemente sobre-declarados.
- `entries`, `market_data` y `staleness_seconds` siguen siendo argumentos
  requeridos del constructor y conservan su posición: sólo se ensancha la
  anotación, no se mueve ningún campo ni aparece un default que tape una clave
  ausente.
- Código que indexara o iterara `entries` / `market_data` sin chequear `None`
  ahora falla en mypy, y en runtime el valor puede ser legítimamente `None` en
  vez de un cero tipado; `staleness_seconds` deja de ser seguro para aritmética
  directa. El ensanchamiento admite `None` y nada más: un valor de tipo
  equivocado sigue siendo divergencia y sigue siendo fatal bajo `strict_decode`.

**SC-3 — `Symbol.created_at` y `.updated_at` pasan a `str | None`**

- Estaban declarados `str = ""`. `Symbol` sirve cuatro endpoints con tres formas
  de body distintas y sólo una las trae: `GET /symbols` manda ambos timestamps,
  mientras que los acks de `POST /symbols`, `POST /symbols/batch` y
  `PATCH /symbols/{symbol_id}` no mandan ninguno.
- La declaración vieja fabricaba dos strings vacíos en cada escritura, que el
  consumidor no podía distinguir de una fila real con timestamps en blanco, y
  volvía fatal toda escritura bajo `strict_decode`. `None` dice la verdad: esa
  forma de respuesta no trae el campo.
- Un consumidor que trate `created_at` o `updated_at` como `str` no opcional
  ahora falla en mypy.

### v0.4.0

**Nueva superficie de escritura: calendar, más los fixes verificados en vivo contra develop**
(features nuevas, minor bump — la superficie de lectura v0.2.0 sigue intacta **excepto
`CalendarDay`**, que reemplaza campos; ver "Reemplazo de campos de `CalendarDay`" abajo).

- **Calendar write (MUT-MD-02):** ocho nombres públicos nuevos en el `__all__` plano — los
  request-models `MarketHoursIn`, `HolidayIn` y `HolidaysIn`, y las funciones
  `set_calendar_config`, `delete_calendar_config`, `preview_calendar_config`, `add_holidays` y
  `delete_holiday` — sobre los endpoints `PUT /calendar/config`, `DELETE /calendar/config`,
  `POST /calendar/config/preview`, `POST /calendar/holidays` y `DELETE /calendar/holidays/{day}`.
  Las cinco funciones tienen contraparte async en `market_data_client.aio`
  (`set_calendar_config`, `delete_calendar_config`, `preview_calendar_config`, `add_holidays`,
  `delete_holiday`; shims a nivel de módulo, no re-exportados al namespace plano según la
  convención del monorepo). `confirm` es un **campo de `MarketHoursIn`** (default `False`), así
  que sólo viaja en `set_calendar_config` / `preview_calendar_config`. **No es un gate de
  persistencia**: es una *segunda opinión* que el servidor exige únicamente cuando la ventana
  pedida produce warnings — una config sin warnings se persiste igual con `confirm=False`.
  `delete_calendar_config`, `add_holidays` y `delete_holiday` **no tienen** argumento `confirm`.
  El guard real de toda la superficie — y el único de esas tres — es el mutating-gate opt-in ya
  existente (`mutating_allowed=True` + `expected_host`).
- **Fixes verificados en vivo (LIVE-MUT-01):** `update_symbol(symbol_id)` fue **ensanchado** de
  `str` a `int | str` en los cuatro routes (el builder de `_core`, `Client`, `AsyncClient` y
  ambos shims de módulo); `Symbol` gana cinco campos **con default** (`id`, `market_id`,
  `created_at`, `updated_at`, `received_at`); `Symbol.marketId` se **preserva** como alias
  deprecado, espejado desde el `market_id` del wire vía override de `from_api`; y el envelope de
  las respuestas de symbols-write se desenvuelve preservando `list[Symbol]`. Todos son cambios
  estrictamente aditivos o de ensanchamiento — **no rompen** a ningún consumidor v0.3.1.

**Reemplazo de campos de `CalendarDay`** (breaking en sentido estricto, documentado y shippeado
dentro de un minor en línea 0.x — el porqué, abajo):

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
