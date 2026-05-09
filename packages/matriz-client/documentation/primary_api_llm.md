# Primary API v1.21 — Markdown optimizado para LLMs

> Documento reconstruido a partir del PDF **Primary API v1.21**.
> Se eliminaron del contenido los **encabezados** y **pies de página** repetitivos.
> Formato pensado para lectura humana, RAG, chunking y consumo por LLMs.

---

## 1. Visión general

**Primary API** facilita la interoperabilidad de software de terceros con la plataforma de negociación electrónica **Primary Trading Platform (PTP)** de **MATBA ROFEX**.

La propuesta de valor es simplificar la integración reemplazando interfaces basadas en **FIX** por servicios más accesibles vía:

- **REST**: consultas sincrónicas y operaciones puntuales.
- **WebSocket**: eventos asíncronos, market data en tiempo real y execution reports.
- **Risk API**: posiciones y reportes de cuenta.

### Arquitectura conceptual

```text
Third Party Solution --> Primary API --> Primary Trading Platform (PTP)
```

---

## 2. Alcance funcional

### REST

- Segmentos.
- Instrumentos.
- Órdenes: alta, reemplazo, cancelación y consultas de estado.
- Market Data en tiempo real.
- Market Data histórica.
- Risk API.

### WebSocket

- Alta de órdenes.
- Cancelación de órdenes.
- Suscripción a execution reports.
- Suscripción a market data en tiempo real.

---

## 3. Autenticación

## 3.1 Obtener token

### Endpoint

```http
POST https://api.remarkets.primary.com.ar/auth/getToken
```

### Headers requeridos

- `X-Username`
- `X-Password`

### Header devuelto

- `X-Auth-Token`

### Observaciones

- El token tiene vigencia de **24 horas**.
- Luego debe reutilizarse en el resto de los métodos de Trading.

### Ejemplo cURL

```bash
curl -i -X POST "https://api.remarkets.primary.com.ar/auth/getToken" \
  -H "X-Username: TU_USUARIO" \
  -H "X-Password: TU_PASSWORD"
```

### Ejemplo Python

```python
import requests

resp = requests.post(
    "https://api.remarkets.primary.com.ar/auth/getToken",
    headers={
        "X-Username": "TU_USUARIO",
        "X-Password": "TU_PASSWORD"
    }
)

resp.raise_for_status()
token = resp.headers.get("X-Auth-Token")
print(token)
```

---

## 4. Segmentos

Los segmentos representan las ruedas o ambientes de negociación.

### Segmentos mencionados en la documentación

- `DDF`: Derivados Financieros.
- `DDA`: Derivados Agropecuarios.
- `DUAL`: Instrumentos listados en ambas divisiones.
- `MERV`: Instrumentos de mercados externos a MATBA ROFEX.

## 4.1 Listar segmentos disponibles

### Endpoint

```http
GET https://api.remarkets.primary.com.ar/rest/segment/all
```

### Parámetros

No recibe parámetros.

### Respuesta ejemplo

```json
{
  "status": "OK",
  "segments": [
    {"marketSegmentId": "DDA", "marketId": "ROFX"},
    {"marketSegmentId": "TEST", "marketId": "ROFX"},
    {"marketSegmentId": "DUAL", "marketId": "ROFX"},
    {"marketSegmentId": "MERV", "marketId": "ROFX"}
  ]
}
```

---

## 5. Instrumentos (Securities)

Los instrumentos representan los activos negociables. Se clasifican mediante **CFI Code** y poseen atributos como límites de precio, tamaño mínimo/máximo, vencimiento, moneda, tipos de orden soportados y TIFs soportados.

## 5.1 Listar todos los instrumentos

### Endpoint

```http
GET https://api.remarkets.primary.com.ar/rest/instruments/all
```

### Respuesta ejemplo

```json
{
  "status": "OK",
  "instruments": [
    {
      "instrumentId": {"marketId": "ROFX", "symbol": "TRI.ROS/DIC23 352 C"},
      "cficode": "OCAFXS"
    },
    {
      "instrumentId": {"marketId": "ROFX", "symbol": "DLR/DIC22"},
      "cficode": "FXXXSX"
    }
  ]
}
```

## 5.2 Listar instrumentos detallados

### Endpoint

```http
GET https://api.remarkets.primary.com.ar/rest/instruments/details
```

### Campos relevantes del detalle

- `segment.marketSegmentId`
- `lowLimitPrice`
- `highLimitPrice`
- `minPriceIncrement`
- `minTradeVol`
- `maxTradeVol`
- `tickSize`
- `contractMultiplier`
- `roundLot`
- `priceConvertionFactor`
- `maturityDate`
- `currency`
- `orderTypes`
- `timesInForce`
- `instrumentPricePrecision`
- `instrumentSizePrecision`
- `securityDescription`
- `tickPriceRanges`
- `cficode`
- `instrumentId.marketId`
- `instrumentId.symbol`

## 5.3 Obtener detalle de un instrumento

### Endpoint

```http
GET https://api.remarkets.primary.com.ar/rest/instruments/detail
```

### Parámetros

- `marketId`: mercado. Valor documentado: `ROFX`.
- `symbol`: símbolo del instrumento.

### Ejemplo

```http
GET https://api.remarkets.primary.com.ar/rest/instruments/detail?symbol=DLR/NOV23&marketId=ROFX
```

## 5.4 Listar instrumentos por CFI Code

### Endpoint

```http
GET https://api.remarkets.primary.com.ar/rest/instruments/byCFICode
```

### Parámetro

- `CFICode`

### Códigos documentados

- `ESXXXX`: acción.
- `DBXXXX`: bono.
- `OCASPS`: opción call sobre acción.
- `OPASPS`: opción put sobre acción.
- `FXXXSX`: futuro.
- `OPAFXS`: opción put sobre futuro.
- `OCAFXS`: opción call sobre futuro.
- `EMXXXX`: CEDEAR.
- `DBXXFR`: obligaciones negociables.

### Ejemplo

```http
GET https://api.remarkets.primary.com.ar/rest/instruments/byCFICode?CFICode=FXXXSX
```

## 5.5 Listar instrumentos por segmento

### Endpoint

```http
GET https://api.remarkets.primary.com.ar/rest/instruments/bySegment
```

### Parámetros

- `MarketSegmentID`: `DDF`, `DDA`, `DUAL`, `U-DDF`, `U-DDA`, `U-DUAL`, `MERV`.
- `MarketID`: `ROFX`.

### Ejemplo

```http
GET https://api.remarkets.primary.com.ar/rest/instruments/bySegment?MarketSegmentID=DDF&MarketID=ROFX
```

### Ejemplo Python

```python
import requests

resp = requests.get(
    "https://api.remarkets.primary.com.ar/rest/instruments/bySegment",
    headers={"X-Auth-Token": "TU_TOKEN"},
    params={"MarketSegmentID": "DDF", "MarketID": "ROFX"}
)

print(resp.json())
```

---

## 6. Órdenes

## 6.1 Conceptos clave

### `clOrdId` vs `orderId`

- **`clOrdId`**: identifica el request enviado al mercado.
- **`orderId`**: identifica la orden en el mercado.

Una misma orden puede tener varios requests asociados. Por ejemplo:

1. alta de orden con un `clOrdId`
2. cancelación con otro `clOrdId`
3. ambos referencian al mismo `orderId`

## 6.2 Flujo recomendado al enviar una orden

1. Enviar la orden.
2. Si la respuesta tiene `status = OK`, consultar luego el estado.
3. Confirmar si quedó en:
   - `NEW`
   - `REJECTED`

## 6.3 Alta de orden por REST

### Endpoint

```http
GET https://api.remarkets.primary.com.ar/rest/order/newSingleOrder
```

### Parámetros

- `marketId`
- `symbol`
- `price`
- `orderQty`
- `ordType`: `LIMIT` o `MARKET`
- `side`: `SELL` o `BUY`
- `timeInForce`: `DAY`, `IOC`, `FOK`, `GTD`
- `account`
- `cancelPrevious` (opcional)
- `iceberg` (opcional)
- `expireDate` (opcional, requerido para `GTD`)
- `displayQty` (opcional, iceberg)

### Ejemplo LIMIT DAY

```http
GET https://api.remarkets.primary.com.ar/rest/order/newSingleOrder?marketId=ROFX&symbol=DLR/DIC23&side=BUY&timeInForce=DAY&orderQty=100&ordType=LIMIT&account=REM6771&cancelPrevious=False&iceberg=False&price=210.5
```

### Respuesta ejemplo

```json
{
  "status": "OK",
  "order": {
    "clientId": "21581341758",
    "proprietary": "PBCP"
  }
}
```

### Ejemplo Iceberg

```http
GET https://api.remarkets.primary.com.ar/rest/order/newSingleOrder?marketId=ROFX&symbol=DLR/DIC23&side=BUY&timeInForce=DAY&orderQty=100&ordType=LIMIT&account=REM6771&cancelPrevious=False&iceberg=true&price=210.5&displayQty=5
```

### Ejemplo GTD

```http
GET https://api.remarkets.primary.com.ar/rest/order/newSingleOrder?marketId=ROFX&symbol=DLR/DIC23&side=BUY&timeInForce=GTD&orderQty=100&ordType=LIMIT&account=REM2747&cancelPrevious=False&iceberg=False&price=182.5&expireDate=20230505
```

### Ejemplo Python

```python
import requests

params = {
    "marketId": "ROFX",
    "symbol": "DLR/DIC23",
    "side": "BUY",
    "timeInForce": "DAY",
    "orderQty": 100,
    "ordType": "LIMIT",
    "account": "REM6771",
    "cancelPrevious": "False",
    "iceberg": "False",
    "price": 210.5,
}

resp = requests.get(
    "https://api.remarkets.primary.com.ar/rest/order/newSingleOrder",
    headers={"X-Auth-Token": "TU_TOKEN"},
    params=params,
)

print(resp.json())
```

## 6.4 Alta de orden por WebSocket

### Mensaje básico

```json
{
  "type": "no",
  "product": {
    "marketId": "ROFX",
    "symbol": "DLR/DIC23"
  },
  "price": 185,
  "quantity": 23,
  "side": "BUY",
  "account": "20",
  "iceberg": false
}
```

### Contrato Todo o Nada

```json
{
  "type": "no",
  "product": {
    "marketId": "ROFX",
    "symbol": "DLR/DIC23A"
  },
  "price": 185,
  "quantity": 3000,
  "side": "BUY",
  "account": "20",
  "iceberg": false
}
```

### Orden con identificador `wsClOrdId`

```json
{
  "type": "no",
  "product": {
    "marketId": "ROFX",
    "symbol": "DLR/DIC23"
  },
  "price": 185,
  "quantity": 23,
  "side": "BUY",
  "account": "20",
  "iceberg": false,
  "wsClOrdId": "asdjuej213n1"
}
```

### Primer execution report esperado

```json
{
  "type": "or",
  "timestamp": 1537212212623,
  "orderReport": {
    "orderId": null,
    "clOrdId": "275772212000001",
    "proprietary": "test",
    "accountId": {"id": "100"},
    "instrumentId": {"marketId": "ROFX", "symbol": "DLR/DIC23"},
    "price": 40,
    "orderQty": 1,
    "ordType": "LIMIT",
    "side": "BUY",
    "timeInForce": "DAY",
    "transactTime": "20180917-16:23:32",
    "status": "PENDING_NEW",
    "text": "Enviada",
    "wsClOrdId": "12345678fz"
  }
}
```

### Notas sobre `wsClOrdId`

- Sirve para identificar la orden enviada por WebSocket.
- Solo aparece en el primer execution report (`PENDING_NEW` o `REJECT`).
- Luego debe mapearse con `clOrdId` para seguir el ciclo de vida de la orden.
- La API no valida que sea único.

### Iceberg por WebSocket

```json
{
  "type": "no",
  "product": {
    "marketId": "ROFX",
    "symbol": "DLR/DIC22"
  },
  "price": 185,
  "quantity": 20,
  "side": "BUY",
  "account": "20",
  "iceberg": true,
  "displayQuantity": 8
}
```

### GTD por WebSocket

```json
{
  "type": "no",
  "product": {
    "marketId": "ROFX",
    "symbol": "DLR/DIC23"
  },
  "price": 185,
  "quantity": 23,
  "side": "BUY",
  "account": "20",
  "timeInForce": "GTD",
  "expireDate": "20231010"
}
```

## 6.5 Reemplazar una orden

### Endpoint

```http
GET https://api.remarkets.primary.com.ar/rest/order/replaceById
```

### Parámetros

- `clOrdId`
- `proprietary`
- `orderQty`
- `price`

### Ejemplo

```http
GET https://api.remarkets.primary.com.ar/rest/order/replaceById?clOrdId=user144733478280357&proprietary=api&price=17&orderQty=10
```

## 6.6 Cancelar una orden por REST

### Endpoint

```http
GET https://api.remarkets.primary.com.ar/rest/order/cancelById
```

### Ejemplo

```http
GET https://api.remarkets.primary.com.ar/rest/order/cancelById?clOrdId=ajduj3l13ieci2jr4ck&proprietary=PBCP
```

## 6.7 Cancelar una orden por WebSocket

```json
{
  "type": "co",
  "clientId": "user114121092035207",
  "proprietary": "PBCP"
}
```

## 6.8 Consultar último estado por `clOrdId`

### Endpoint

```http
GET https://api.remarkets.primary.com.ar/rest/order/id
```

### Parámetros

- `clOrdId`
- `proprietary`

### Respuesta ejemplo

```json
{
  "status": "OK",
  "order": {
    "orderId": "1130835",
    "clOrdId": "user1145712381052053",
    "proprietary": "PBCP",
    "execId": "160229133429-fix1-493",
    "accountId": {"id": "10"},
    "instrumentId": {"marketId": "ROFX", "symbol": "DLR/DIC23"},
    "price": 183,
    "orderQty": 10,
    "ordType": "LIMIT",
    "side": "BUY",
    "timeInForce": "DAY",
    "transactTime": "20160304-17:37:35",
    "avgPx": 0,
    "lastPx": 0,
    "lastQty": 0,
    "cumQty": 0,
    "leavesQty": 10,
    "status": "NEW",
    "text": "Aceptada"
  }
}
```

## 6.9 Consultar todos los estados por `clOrdId`

### Endpoint

```http
GET https://api.remarkets.primary.com.ar/rest/order/allById
```

Devuelve todos los estados recorridos por el request identificado por ese `clOrdId`.

## 6.10 Consultar órdenes activas

### Endpoint

```http
GET https://api.remarkets.primary.com.ar/rest/order/actives?accountId=10
```

## 6.11 Consultar órdenes operadas

### Endpoint

```http
GET https://api.remarkets.primary.com.ar/rest/order/filleds?accountId=10
```

## 6.12 Consultar último estado de requests por cuenta

### Endpoint

```http
GET https://api.remarkets.primary.com.ar/rest/order/all?accountId=30
```

## 6.13 Consultar orden por Execution ID

### Endpoint

```http
GET https://api.remarkets.primary.com.ar/rest/order/byExecId?execId=T1234567
```

---

## 7. Execution Reports por WebSocket

## 7.1 Suscripción para una cuenta

```json
{
  "type": "os",
  "account": {
    "id": "40"
  }
}
```

## 7.2 Suscripción para varias cuentas

```json
{
  "type": "os",
  "accounts": [
    {"id": "40"},
    {"id": "4000"}
  ]
}
```

## 7.3 Suscripción para todas las cuentas

```json
{
  "type": "os"
}
```

## 7.4 Snapshot solo de órdenes activas

```json
{
  "type": "os",
  "snapshotOnlyActive": true
}
```

## 7.5 Mensaje de execution report recibido

```json
{
  "type": "or",
  "orderReport": {
    "orderId": "1128056",
    "clOrdId": "user14545967430231",
    "proprietary": "PBCP",
    "execId": "160127155448-fix1-1368",
    "accountId": {"id": "30"},
    "instrumentId": {"marketId": "ROFX", "symbol": "DLR/DIC23"},
    "price": 189,
    "orderQty": 10,
    "ordType": "LIMIT",
    "side": "BUY",
    "timeInForce": "DAY",
    "transactTime": "20230204-11:41:54",
    "avgPx": 0,
    "lastPx": 0,
    "lastQty": 0,
    "cumQty": 0,
    "leavesQty": 10,
    "status": "CANCELLED",
    "text": "Reemplazada"
  }
}
```

---

## 8. Market Data

## 8.1 Market Data en tiempo real por REST

### Endpoint

```http
GET https://api.remarkets.primary.com.ar/rest/marketdata/get
```

### Parámetros

- `marketId`
- `symbol`
- `entries`
- `depth` (opcional)

### Entries documentados

- `BI`: Bid.
- `OF`: Offer.
- `LA`: Last.
- `OP`: Open.
- `CL`: Close.
- `SE`: Settlement.
- `OI`: Open Interest.
- `ACP`: Auction Price.

### Ejemplo

```http
GET https://api.remarkets.primary.com.ar/rest/marketdata/get?marketId=ROFX&symbol=DLR/DIC23&entries=BI,OF,LA,OP,CL,SE,OI&depth=3
```

### Respuesta ejemplo

```json
{
  "status": "OK",
  "marketData": {
    "SE": {"price": 180.3, "size": null, "date": 1669852800000},
    "LA": {"price": 179.85, "size": 4, "date": 1669995044232},
    "OI": {"price": null, "size": 217596, "date": 1664150400000},
    "OF": [
      {"price": 179.8, "size": 1000},
      {"price": 180.35, "size": 1000}
    ],
    "OP": 180.35,
    "CL": {"price": 180.35, "size": null, "date": 1669852800000},
    "BI": [
      {"price": 179.75, "size": 275},
      {"price": 178.95, "size": 514}
    ]
  },
  "depth": 2,
  "aggregated": true
}
```

### Ejemplo Python

```python
import requests

resp = requests.get(
    "https://api.remarkets.primary.com.ar/rest/marketdata/get",
    headers={"X-Auth-Token": "TU_TOKEN"},
    params={
        "marketId": "ROFX",
        "symbol": "DLR/DIC23",
        "entries": "BI,OF,LA,OP,CL,SE,OI",
        "depth": 2,
    },
)

print(resp.json())
```

## 8.2 Market Data por WebSocket

### Suscripción

```json
{
  "type": "smd",
  "level": 1,
  "entries": ["OF"],
  "products": [
    {"symbol": "DLR/DIC23", "marketId": "ROFX"},
    {"symbol": "SOJ.ROS/MAY23", "marketId": "ROFX"}
  ],
  "depth": 2
}
```

### Mensaje recibido

```json
{
  "type": "Md",
  "instrumentId": {
    "marketId": "ROFX",
    "symbol": "DLR/DIC23"
  },
  "marketData": {
    "OF": [
      {"price": 189, "size": 21},
      {"price": 188, "size": 13}
    ]
  }
}
```

## 8.3 Entries ampliados

- `BI`: mejor oferta de compra.
- `OF`: mejor oferta de venta.
- `LA`: último precio operado.
- `OP`: precio de apertura.
- `CL`: precio de cierre de la rueda anterior.
- `SE`: precio de ajuste.
- `HI`: máximo de la rueda.
- `LO`: mínimo de la rueda.
- `TV`: volumen operado.
- `OI`: interés abierto.
- `IV`: valor de índice.
- `EV`: volumen efectivo negociado.
- `NV`: volumen nominal negociado.
- `ACP`: precio de cierre del día corriente.

### Nota importante

- `EV` y `NV` aplican a instrumentos de **ByMA**.
- Para MATBA ROFEX, el volumen se consulta con `TV`.

## 8.4 Market Data histórica

### Endpoint

```http
GET https://api.remarkets.primary.com.ar/rest/data/getTrades
```

### Parámetros

- `marketId`
- `symbol`
- `date`
- `dateFrom`
- `dateTo`
- `external` (opcional)
- `environment` (en reMarkets: `REMARKETS`)

### Ejemplo

```http
GET https://api.remarkets.primary.com.ar/rest/data/getTrades?marketId=ROFX&symbol=DLR/DIC23&date=2023-08-05
```

### Respuesta ejemplo

```json
{
  "status": "OK",
  "symbol": "DLR/DIC23",
  "market": "ROFX",
  "trades": [
    {
      "symbol": "DLR/DIC23",
      "servertime": 1659714475948,
      "size": 25,
      "price": 183.6,
      "datetime": "2023-08-05 15:47:55.948"
    },
    {
      "symbol": "DLR/DIC23",
      "servertime": 1659715021103,
      "size": 1,
      "price": 183.56,
      "datetime": "2023-08-05 15:57:01.103"
    }
  ]
}
```

---

## 9. Primary Risk API

La Risk API se comunica con **RIMA (Risk Manager)**.

### Métodos documentados

- posiciones por cuenta
- detalle de posiciones
- reporte de cuenta

### Autenticación

El PDF indica **HTTP Basic Authentication** para este bloque.

## 9.1 Consultar posiciones de una cuenta

### Endpoint

```http
GET https://api.remarkets.primary.com.ar/rest/risk/position/getPositions/{accountName}
```

### Ejemplo

```http
GET https://api.remarkets.primary.com.ar/rest/risk/position/getPositions/REM7374
```

### Campos frecuentes de respuesta

- `symbol`
- `buySize`
- `buyPrice`
- `sellSize`
- `sellPrice`
- `totalDailyDiff`
- `totalDiff`
- `tradingSymbol`

## 9.2 Consultar detalle de posiciones

### Endpoint

```http
GET https://api.remarkets.primary.com.ar/rest/risk/detailedPosition/{accountName}
```

### Ejemplo

```http
GET https://api.remarkets.primary.com.ar/rest/risk/detailedPosition/REM7374
```

### Campos relevantes

- `account`
- `totalDailyDiffPlain`
- `totalMarketValue`
- `report`
- `lastCalculation`

## 9.3 Consultar reporte de cuenta

### Endpoint

```http
GET https://api.remarkets.primary.com.ar/rest/risk/accountReport/{accountName}
```

### Ejemplo

```http
GET https://api.remarkets.primary.com.ar/rest/risk/accountReport/REM7374
```

### Campos relevantes

- `accountName`
- `marketMember`
- `marketMemberIdentity`
- `collateral`
- `margin`
- `availableToCollateral`
- `detailedAccountReports`
- `portfolio`
- `ordersMargin`
- `currentCash`
- `dailyDiff`
- `uncoveredMargin`

### Ejemplo Python

```python
import requests
from requests.auth import HTTPBasicAuth

resp = requests.get(
    "https://api.remarkets.primary.com.ar/rest/risk/accountReport/REM7374",
    auth=HTTPBasicAuth("TU_USUARIO", "TU_PASSWORD")
)

print(resp.json())
```

---

## 10. Errores documentados

## 10.1 Sin acceso a la cuenta

```json
{
  "status": "ERROR",
  "description": "No tiene acceso a la cuenta 30",
  "message": null
}
```

## 10.2 Cancelar orden inexistente

```json
{
  "status": "ERROR",
  "description": "Order user1144733478:api doesn't exist",
  "message": null
}
```

## 10.3 Instrumento inexistente

```json
{
  "status": "ERROR",
  "description": "Product DOEne15:ROFX doesn't exist",
  "message": null
}
```

## 10.4 Acceso denegado o ruta inválida

```json
{
  "status": "ERROR",
  "message": "Access Denied"
}
```

```json
{
  "status": "ERROR",
  "description": "Ruta invalida",
  "message": ""
}
```

---

## 11. Estados de orden relevantes

Los estados visibles o mencionados en la documentación incluyen:

- `NEW`
- `PENDING_NEW`
- `PENDING_REPLACE`
- `PENDING_CANCEL`
- `REJECTED`
- `PENDING_APPROVAL`
- `CANCELLED`
- `REPLACED`
- `FILLED`
- `PARTIALLY_FILLED`

---

## 12. Diccionario de campos consolidado

## 12.1 Identificadores

- `accountName`: nombre de la cuenta.
- `clOrdId`: ID del request de una orden.
- `orderId`: ID de la orden.
- `execId`: ID de ejecución.
- `marketId`: identificador del mercado (`ROFX`, `MERV`).
- `marketSegmentId`: identificador del segmento.
- `securityId`: ID del security.
- `symbol`: nombre del contrato.
- `wsclOrdId`: ID del request enviado vía WebSocket.

## 12.2 Precios, cantidades y volumen

- `avgPx`: precio promedio operado.
- `price`: precio de orden o de market data.
- `lastPx`: último precio operado.
- `lastQty`: última cantidad operada.
- `cumQty`: cantidad acumulada operada.
- `leavesQty`: remanente de la orden.
- `size`: cantidad en market data.
- `orderQty`: tamaño de la orden.
- `displayQty`: cantidad a divulgar en iceberg.
- `displayQuantity`: cantidad visible de iceberg.
- `minTradeVol`: volumen mínimo.
- `maxTradeVol`: volumen máximo.
- `tick`: tick de precio.
- `tickSize`: incremento de cantidad.
- `minPriceIncrement`: incremento mínimo de precio.
- `roundLot`: multiplicador.
- `contractMultiplier`: tamaño del contrato.
- `priceConvertionFactor`: factor de conversión de precio.

## 12.3 Fechas y tiempo

- `dateFrom`: fecha desde.
- `dateTo`: fecha hasta.
- `datetime`: fecha y hora del trade.
- `expireDate`: vencimiento de orden GTD.
- `maturityDate`: vencimiento o maduración del contrato.
- `serverTime`: timestamp del evento.
- `timestamp`: marca de tiempo del registro.
- `transactTime`: fecha y hora de transacción.

## 12.4 Instrumento y mercado

- `cficode`: código CFI.
- `currency`: moneda de liquidación.
- `highLimitPrice`: límite máximo.
- `lowLimitPrice`: límite mínimo.
- `lowerLimit`: límite inferior del rango de tick dinámico.
- `upperLimit`: límite superior del rango de tick dinámico.
- `instrumentPricePrecision`: precisión de decimales en precio.
- `instrumentSizePrecision`: precisión de decimales en cantidad.
- `orderTypes`: órdenes soportadas por el contrato.
- `securityDescription`: descripción del instrumento.
- `securityType`: tipo del security.
- `segments`: listado de segmentos.
- `settlType`: tipo de liquidación.
- `tickPriceRanges`: rangos dinámicos de ticks.
- `timeInForce`: vigencia de la orden.
- `timeInForces`: TIFs soportados.

## 12.5 Estado y control

- `iceberg`: indica si la orden es iceberg.
- `id`: en execution report, cuenta involucrada.
- `ordType`: tipo de orden (`LIMIT`, `MARKET`, `STOP_LIMIT`, `STOP_LIMIT_MERVAL`).
- `proprietary`: usuario FIX que envió la orden.
- `side`: `BUY` o `SELL`.
- `status`: estado de la orden.
- `text`: texto asociado al estado.
- `depth`: profundidad de market data, valores documentados `1` a `5`.

---

## 13. Buenas prácticas derivadas del documento

1. Persistir `clOrdId`, `orderId` y `execId` por separado.
2. No asumir que `status=OK` implica orden definitivamente aceptada.
3. Consultar luego el estado o suscribirse a execution reports.
4. Mapear `wsClOrdId` con `clOrdId` cuando se usa WebSocket.
5. Validar símbolos y cuentas antes de operar.
6. Diferenciar autenticación de Trading y autenticación de Risk.
7. Usar `depth` solo cuando realmente se necesite profundidad de book.
8. Tratar `orderId = null` como caso transitorio o rechazo, según contexto.

---

## 14. Ejemplo de flujo de integración

### Paso 1: token

```python
import requests

auth_resp = requests.post(
    "https://api.remarkets.primary.com.ar/auth/getToken",
    headers={
        "X-Username": "TU_USUARIO",
        "X-Password": "TU_PASSWORD"
    }
)

token = auth_resp.headers["X-Auth-Token"]
```

### Paso 2: listar instrumentos por segmento

```python
inst_resp = requests.get(
    "https://api.remarkets.primary.com.ar/rest/instruments/bySegment",
    headers={"X-Auth-Token": token},
    params={"MarketSegmentID": "DDF", "MarketID": "ROFX"}
)

print(inst_resp.json())
```

### Paso 3: enviar una orden

```python
order_resp = requests.get(
    "https://api.remarkets.primary.com.ar/rest/order/newSingleOrder",
    headers={"X-Auth-Token": token},
    params={
        "marketId": "ROFX",
        "symbol": "DLR/DIC23",
        "side": "BUY",
        "timeInForce": "DAY",
        "orderQty": 10,
        "ordType": "LIMIT",
        "account": "REM6771",
        "cancelPrevious": "False",
        "iceberg": "False",
        "price": 210.5,
    }
)

print(order_resp.json())
```

### Paso 4: consultar estado posterior

```python
status_resp = requests.get(
    "https://api.remarkets.primary.com.ar/rest/order/id",
    headers={"X-Auth-Token": token},
    params={
        "clOrdId": "CLORD_DEVUELTO_POR_EL_ALTA",
        "proprietary": "PBCP"
    }
)

print(status_resp.json())
```

---

## 15. Notas para procesamiento por LLMs

### Unidades semánticas recomendadas para chunking

- Autenticación.
- Segmentos.
- Instrumentos.
- Órdenes REST.
- Órdenes WebSocket.
- Consultas de estado.
- Execution Reports.
- Market Data REST.
- Market Data WebSocket.
- Market Data histórica.
- Risk API.
- Errores.
- Diccionario de campos.

### Claves de extracción sugeridas

- `endpoint`
- `method`
- `params`
- `response_fields`
- `examples`
- `errors`
- `states`
- `auth_type`
- `message_type`

---

## 16. Limitaciones y observaciones

- El PDF documenta claramente formatos de mensajes WebSocket, pero en las páginas revisadas no explicita una URL única de conexión WebSocket.
- La documentación muestra ejemplos de requests como `GET` incluso para operaciones transaccionales como alta, reemplazo y cancelación.
- Existen algunos errores tipográficos menores en el PDF original, por ejemplo en nombres o cortes de líneas, que aquí fueron normalizados cuando no afectaban el sentido técnico.

---

## 17. Historial resumido del documento

- **v1.0 (2015-11-03):** versión inicial.
- **v1.2:** se agregan segmentos, instrumentos detallados e instrumentos por CFI.
- **v1.5:** se agregan descripciones y ejemplos de WebSocket.
- **v1.7:** se agrega profundidad para market data REST y WebSocket, vencimiento de instrumentos, instrumentos por segmento, órdenes por ID, activas y operadas.
- **v1.8:** se agrega `cancelPrevious` y soporte multimoneda en reporte de cuentas.
- **v1.10:** se agrega `snapshotOnlyActive`.
- **v1.11:** se agregan órdenes Iceberg, `displayQty`, `GTD` y `expireDate`.
- **v1.14:** se agrega replace por `clOrdId`.
- **v1.15:** se agrega autenticación por token.
- **v1.16:** se agrega consulta por `Execution ID`.
- **v1.18:** se agregan `dateFrom` y `dateTo` para market data histórica.
- **v1.20:** se agrega `wsClOrdId` y parámetro `allOrNone` para contratos mayoristas por WebSocket.
- **v1.21:** nuevo formato, mejor estructura, enlaces a herramientas del ecosistema y diccionario de campos.

