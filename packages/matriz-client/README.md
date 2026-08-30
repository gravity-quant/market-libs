# matriz-client

Cliente Python para la **MATBA ROFEX [Primary API v1.21](./documentation/primary_api_llm.md)** — API REST + WebSocket para trading electrónico en el mercado de derivados y valores de Argentina. Envuelve los endpoints públicos (segments, instruments, orders, market data, risk) en funciones tipadas con manejo automático del token.

## Instalación

```bash
uv add matriz-client
# o, dentro del workspace:
uv sync
```

## Configuración

El cliente lee credenciales desde variables de entorno (cargadas con `python-dotenv`):

| Variable | Descripción |
|---|---|
| `PRIMARY_USER` | Usuario de la API (requerido) |
| `PRIMARY_PASSWORD` | Password de la API (requerido) |
| `PRIMARY_BASE_URL` | URL base REST. Default: `https://api.remarkets.primary.com.ar` (sandbox reMarkets). |

Si usás `.env`, cargalo en tu app antes de instanciar — la librería ya llama a `load_dotenv()` al import.

## Uso — REST

El cliente hace login automáticamente en la primera llamada que requiera token y lo refresca antes de su expiración (24 h server-side). No es necesario llamar a `login()` explícitamente — solo está expuesto por si querés validar credenciales temprano.

```python
import matriz_client as primary

segments = primary.get_segments()
instruments = primary.get_instruments_by_segment("DDF")

snapshot = primary.get_market_data("DLR/DIC23", depth=5)
print(snapshot.BI, snapshot.OF)

resp = primary.new_order(
    symbol="DLR/DIC23",
    side="BUY",
    qty=10,
    account="REM6771",
    price=210.5,
)
print(resp.clientId, resp.proprietary)
```

## Uso — WebSocket

```python
import matriz_client as primary
from matriz_client import (
    ExecutionReportFrame,
    MarketDataFrame,
    PrimaryWsMessage,
    UnknownFrame,
)


def on_msg(msg: PrimaryWsMessage) -> None:
    if isinstance(msg, MarketDataFrame):
        print(msg.instrumentId.symbol, msg.marketData.BI, msg.marketData.OF)
    elif isinstance(msg, ExecutionReportFrame):
        print(msg.orderReport.clOrdId, msg.orderReport.status)
    elif isinstance(msg, UnknownFrame):
        print("unhandled frame:", msg.type, msg.raw)


primary.ws_connect(on_message=on_msg)  # login automático si hace falta
primary.ws_subscribe_market_data(["DLR/DIC23"], depth=5)
```

## Endpoints disponibles

REST (auth con `X-Auth-Token`, salvo Risk API que usa Basic):

| Función | Endpoint |
|---|---|
| `login()` | `POST /auth/getToken` |
| `get_segments()` | `GET /rest/segment/all` |
| `get_all_instruments()` / `get_instruments_details()` | `GET /rest/instruments/{all,details}` |
| `get_instrument_detail(symbol, market_id)` | `GET /rest/instruments/detail` |
| `get_instruments_by_cfi(cfi_code)` | `GET /rest/instruments/byCFICode` |
| `get_instruments_by_segment(segment_id, market_id)` | `GET /rest/instruments/bySegment` |
| `new_order(...)` / `replace_order(...)` / `cancel_order(...)` | `GET /rest/order/{newSingleOrder,replaceById,cancelById}` |
| `get_order_status` / `get_order_history` / `get_order_by_exec_id` | `GET /rest/order/{id,allById,byExecId}` |
| `get_active_orders` / `get_filled_orders` / `get_all_orders` | `GET /rest/order/{actives,filleds,all}` |
| `get_market_data(symbol, ...)` | `GET /rest/marketdata/get` |
| `get_trades(symbol, ...)` | `GET /rest/data/getTrades` |
| `get_positions(account)` (Risk, Basic Auth) | `GET /rest/risk/position/getPositions/...` |
| `get_detailed_positions(account)` (Risk) | `GET /rest/risk/detailedPosition/...` |
| `get_account_report(account)` (Risk) | `GET /rest/risk/accountReport/...` |

WebSocket:

| Función | Mensaje |
|---|---|
| `ws_connect(on_message, on_error, on_close)` | — |
| `ws_disconnect()` / `ws_is_connected()` | — |
| `ws_subscribe_market_data(symbols, ...)` | `{"type": "smd", ...}` |
| `ws_subscribe_order_reports(account, ...)` | `{"type": "os", ...}` |
| `ws_new_order(...)` / `ws_cancel_order(...)` | `{"type": "no" / "co", ...}` |

## Modelos tipados

`matriz_client` exporta `Literal` aliases (`Side`, `OrderType`, `TimeInForce`, `MarketId`, `SegmentId`, `CFICode`, `MarketDataEntry`, `OrderStatus`, `Currency`) y dataclasses safe-access (`SafeModel.from_api()`) para cada response. Los campos faltantes caen a defaults seguros (`[]`, modelo vacío, `None`, `{}`), por lo que `snapshot.SE.price` nunca lanza:

```python
from matriz_client import Side, OrderType, TimeInForce, Order, MarketDataSnapshot
```

Modelos públicos: `Segment`, `Instrument`, `InstrumentDetail`, `InstrumentId`, `Order`, `OrderReport`, `NewOrderResponse`, `MarketDataSnapshot`, `MarketDataLevel`, `MarketDataEntryValue`, `Trade`, `Position`, `DetailedPosition`, `AccountReport`, `MarketDataFrame`, `ExecutionReportFrame`, `UnknownFrame`, `PrimaryWsMessage`, `AccountId`.

## Excepciones

- `PrimaryAPIError(status, description, message)` — payload con `status == "ERROR"`.
- `AuthenticationError` — credenciales faltantes o respuesta de login sin `X-Auth-Token`.

## Referencia de la API

- [`documentation/primary_api_llm.md`](./documentation/primary_api_llm.md) — markdown LLM-friendly (26 KB).
- [`documentation/Primary-API.md`](./documentation/Primary-API.md) — markdown completo (60 KB).
- [`documentation/Primary-API.pdf`](./documentation/Primary-API.pdf) — PDF original (604 KB).

Conceptos clave:

- `clOrdId` identifica un request; `orderId` identifica la orden en la bolsa.
- Segmentos: `DDF` (derivados financieros), `DDA` (agro), `DUAL`, `MERV` (mercados externos).
- Entries de market data: `BI` (bid), `OF` (offer), `LA` (last), `OP` (open), `CL` (close), `SE` (settlement), `OI` (open interest).

## Desarrollo

```bash
uv run pytest packages/matriz-client
uv run ruff check packages/matriz-client
uv run mypy packages/matriz-client/src
```

## Changelog

### v0.3.0

**Cuatro campos `dict[str, Any]` de los modelos de riesgo pasan a tipos concretos, y
`get_detailed_positions`/`get_account_report` dejan de decodificar desde el nivel de
anidamiento equivocado** (breaking, minor bump en línea 0.x — todo consumidor que lea
estos campos por clave necesita migrar).

**Ruptura: acceso por clave → atributo tipado**

| Antes (0.2.0 publicado) | Ahora (0.3.0) |
| --- | --- |
| `report.portfolio` era `dict[str, Any]` (siempre `{}` en la práctica) | `report.portfolio` es `float \| None` — chequear `is None`, no `== {}` |
| `detail.tickPriceRanges["0"]["tick"]` | `detail.tickPriceRanges["0"].tick` (`dict[str, TickPriceRange]`) |
| `pos.report["<acct>"]["<sym>"]["instrumentCurrentSize"]` | `pos.report["<acct>"]["<sym>"].instrumentCurrentSize` (`dict[str, dict[str, InstrumentPositionReport]]` — **dos** niveles) |
| `acct.detailedAccountReports["<k>"]["settlementDate"]` | `acct.detailedAccountReports["<k>"].settlementDate` (`dict[str, DetailedAccountReport]` — **un** nivel) |

Los cuatro campos afectados son `portfolio` y `detailedAccountReports` sobre
`AccountReport`, `tickPriceRanges` sobre `InstrumentDetail`, y `report` sobre
`DetailedPosition`.

`tickPriceRanges`, `report` y `detailedAccountReports` conservan el `dict` externo (la
clave sigue siendo el número de cuenta, el símbolo o el índice del rango, que viaja
como dato); lo que deja de ser `dict` es la **hoja**. Un acceso por clave sobre esa
hoja levanta `TypeError`: los modelos son dataclasses *frozen* con `slots` y no son
subscriptables.

**Corrección de comportamiento: unwrap del envelope de Risk**

`get_detailed_positions` y `get_account_report` decodificaban desde el nivel de
anidamiento equivocado y devolvían modelos con **todos** los campos en su default —
un `DetailedPosition` o un `AccountReport` vacío, sin error y sin registro de
divergencia. La corrección desenvuelve las claves de envelope del proveedor
`detailedPosition` y `accountData` antes de decodificar.

Bajo la disposición `strict-unwrap`, un body de Risk **plano** (sin envelope) ahora
**levanta** en lugar de decodificar en silencio. El efecto para el consumidor es de
dos caras: quien venía tolerando modelos de Risk todos-en-default ahora ve datos
reales — o un `PrimaryAPIError` donde antes veía un modelo vacío. Es un cambio de
comportamiento, no sólo de tipo, y no aparece en la tabla de arriba.

**Flip de truthiness — la parte que el typechecker NO atrapa**

`portfolio`, sobre `AccountReport`, era un `dict` que en la práctica llegaba
**siempre** `{}`, y
un dict vacío es falsy. Ahora es un escalar `float | None`. Un consumidor que ramifique
por comparación contra el dict vacío (`if report.portfolio == {}:`, `if not
report.portfolio:` escrito para atrapar ese `{}`) **deja de tomar esa rama, en
silencio**: no levanta, no rompe el build y mypy no dice una palabra, porque el tipo
declarado ahora es correcto. Revisar a mano cada chequeo sobre este campo antes de
actualizar, y migrar a `is None`.

**Aditivo, no breaking**

Nada de lo que sigue rompe código existente; se lista aparte de la tabla de migración
a propósito.

- **Seis alias `@property` sobre `MarketDataSnapshot`**, vistas de sólo lectura sobre
  las claves de wire ya existentes: `bids`/`offers` → `list[MarketDataLevel]` sobre
  `BI`/`OF`, y `last`/`settlement`/`close`/`open_interest` → `MarketDataEntryValue`
  sobre `LA`/`SE`/`CL`/`OI`. El acceso por clave sigue funcionando igual que antes.
  `OP` y los siete escalares extra de matriz quedaron **deliberadamente excluidos**.
- **Tipos nuevos en `__all__`:** `TickPriceRange`, `InstrumentPositionReport`,
  `DetailedAccountReport` y `MatrizDecodeError`.
- **Parámetro keyword-only `strict_decode`** (`bool | None`) en `Client`, `AsyncClient`
  y `configure`.
