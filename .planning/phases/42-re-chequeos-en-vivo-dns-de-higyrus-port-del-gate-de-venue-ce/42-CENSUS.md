# 42-CENSUS.md — censo en vivo de los valores `Literal` de RESPONSE de `matriz-client`

**Qué es este documento:** una **MEDICIÓN** de qué valores emite el vendor en los cinco campos
RESPONSE de `matriz-client` que llevan un alias `Literal`, tomada contra la venue `bbsa` detrás del
gate de venue portado en el plan 42-01. Satisface el **criterio 3** de la Phase 42 y cierra la mitad
abierta que el plan 33-06 dejó sin medir.

**Qué NO es:** una autorización para promover ningún campo RESPONSE a `Literal` cerrado. Ver
§ 5 (D-lock (b)) y § 6 (alcance de venue).

---

## 1. Encabezado de la medición

Transcripción **verbatim** de las dos primeras líneas de stdout de la corrida — emitidas *antes* de
la primera request, con el venue derivado de `_venue_token(base)` y nunca hardcodeado:

```
CENSUS-HEADER venue=bbsa captured_at=2026-08-31T21:11:53.196947+00:00 allowlist_size=2
CENSUS-DLOCK: el D-lock (b) de la Phase 29 SIGUE EN VIGOR — los campos RESPONSE NO se cierran como Literal. Este inventario es una MEDICIÓN de una sola venue, no una autorización de promoción.
```

| Campo | Valor |
|---|---|
| Venue medido | `bbsa` (token del allowlist, no un hostname resuelto — T-39-04 / C-4) |
| `captured_at` (UTC) | `2026-08-31T21:11:53.196947+00:00` |
| `allowlist_size` | `2` (conteo de la política, no su contenido) |
| Comando exacto | `uv run python scripts/literal_census_33.py --matriz-only` |
| Exit code de la corrida | `0` (medido con `$?` directo, no el de `tee`) |
| Veredicto final | `CENSUS: matriz=RAN iol=NOT-REQUESTED (--matriz-only)` |

El venue del encabezado **no puede mentir**: sale del mismo `_venue_token` que decidió el gate
(`main_matriz.py`, importado — D-01), así que "contra qué se midió" y "contra qué se autorizó
medir" son literalmente el mismo objeto.

**Invocación de archivo `.py` real, no `python -c` (P-10).** Bajo `-c`, `find_dotenv()` cae a
`os.getcwd()`, no encuentra el `.env` del paquete, y el `Client()` apuntaría al default
**remarkets** en vez de a `bbsa` — el censo habría medido la venue equivocada reportando un venue
distinto del real.

---

## 2. Alcance y no-alcance de la corrida

- **Sólo lectura.** Cinco endpoints GET: `get_segments`, `get_all_instruments`,
  `get_instruments_details`, `get_active_orders`, `get_all_orders`. **Cero órdenes emitidas, cero
  mutaciones.** `VERIFY_MUTATING` no se seteó en ninguna variante de la invocación, y
  `verification/mutation_gate.py` quedó byte-idéntico (`6bdaec006cc16f7c8dbfac41701712a9085c691b`),
  verificado antes y después.
- **Sin barrido de 4xx.** El barrido deliberado de códigos de error para enumerar el conjunto de
  entrada aceptado sigue **prohibido** (D-10 / P-05). Este censo mide lo que el vendor *emite*, no
  lo que *acepta*.
- **`census_iol()` NO corrió (D-04).** El flag `--matriz-only` toma un retorno temprano y nunca lo
  invoca; el log no contiene ninguna línea `iol-client `. La razón es que la evidencia RESPONSE de
  iol (`Titulo.mercado` / `Titulo.plazo`) ya cerró DT-07 en la Phase 33 y re-correrla sería tráfico
  en vivo sin pregunta abierta detrás. El veredicto de iol se reporta como `NOT-REQUESTED`, que
  **no** es lo mismo que `SKIPPED`.
- **El payload crudo no está acá.** Los cinco dumps viven exclusivamente en
  `.planning/verification/captures/matriz-census-*.json`, que es gitignored (`.gitignore:53`). Lo
  único que cruza a git son conjuntos de vocabulario enum-like, conteos y nombres de path
  (C-4 / D-11 / T-33-32).

---

## 3. Inventario por path observado

Transcripción de las líneas de `_report()`. La unidad es el **path**, no el nombre de clave suelto:
`segments[].marketId`, `instruments[].instrumentId.marketId` e `instruments[].segment.marketId` son
tres modelos distintos que comparten una clave de wire y no se mezclan en una fila.

| # | Endpoint | Path | `rows` | `types` | `distinct` |
|---|---|---|---:|---|---|
| 1 | `get_segments` | `segments[].marketId` | 7 | `['str']` | `['ROFX']` |
| 2 | `get_all_instruments` | `instruments[].cficode` | 9675 | `['str']` | 15 valores (ver § 4) |
| 3 | `get_all_instruments` | `instruments[].instrumentId.marketId` | 9675 | `['str']` | `['ROFX']` |
| 4 | `get_instruments_details` | `instruments[].cficode` | 9675 | `['str']` | 15 valores (ver § 4) |
| 5 | `get_instruments_details` | `instruments[].currency` | 9675 | `['str']` | `['ARS', 'USD']` |
| 6 | `get_instruments_details` | `instruments[].instrumentId.marketId` | 9675 | `['str']` | `['ROFX']` |
| 7 | `get_instruments_details` | `instruments[].orderTypes[]` | 29380 | `['str']` | 6 valores (ver § 4) |
| 8 | `get_instruments_details` | `instruments[].segment.marketId` | 9675 | `['str']` | `['ROFX']` |

**8 paths reportados** sobre **3 de los 5 endpoints**. Los otros dos:

```
matriz-client get_active_orders: NO TARGET FIELD PRESENT IN PAYLOAD
matriz-client get_all_orders: NO TARGET FIELD PRESENT IN PAYLOAD
```

Causa medida, no supuesta: ambos respondieron `status: OK` con la colección `orders` **presente y
de longitud 0**. No es un error, no es un campo ausente de un payload poblado, y no es un SKIP del
gate: es una cuenta sin órdenes en la ventana de corrida. `PRIMARY_ACCOUNT` estaba presente, así
que los dos endpoints de órdenes **sí se ejercitaron** — lo que faltó fueron filas que inspeccionar.

---

## 4. Disposición de los cinco campos del criterio 3

Cada campo tiene **exactamente una** disposición. Cero filas sin disponer.

| Campo | Alias declarado | Disposición | Valores observados | Filas |
|---|---|---|---|---:|
| `marketId` | `MarketId = Literal["ROFX"]` | **MEDIDO** | `ROFX` (1 valor, sobre 3 paths distintos: `Segment`, `InstrumentId`, `InstrumentDetail.segment`) | 7 + 9675 + 9675 + 9675 |
| `cficode` | `CFICode` (9 miembros) | **MEDIDO** | `DBXXFR`, `DBXXXX`, `DYXTXR`, `EMXXXX`, `ESXXXX`, `FXXXSX`, `FXXXXX`, `MRIXXX`, `OCAFXS`, `OCASPS`, `OCEFXS`, `OPAFXS`, `OPASPS`, `OPEFXS`, `RPXXXX` (**15 valores**) | 9675 × 2 endpoints |
| `currency` | `Currency = Literal["ARS", "USD"]` | **MEDIDO** | `ARS`, `USD` (2 valores) | 9675 |
| `orderTypes` | `OrderType` (4 miembros) | **MEDIDO** | `LIMIT`, `MARKET`, `MARKET_TO_LIMIT`, `PREVIOUSLY_QUOTED`, `STOP_LIMIT`, `STOP_LIMIT_MERVAL` (**6 valores**) | 29380 |
| `ordType` | `OrderType` (4 miembros) | **NO MEDIBLE EN ESTA CORRIDA** | — | 0 |

**Causa de la única fila no medible.** `ordType` sólo aparece en `Order`, y los dos endpoints que
devuelven órdenes (`get_active_orders`, `get_all_orders`) respondieron `status: OK` con
`orders` vacío: la cuenta bbsa no tenía órdenes —ni activas ni históricas— en la ventana de la
corrida. El criterio 3 admite explícitamente esta vía ("o declara explícitamente qué campo no se
pudo medir y por qué"); lo que no admite es el silencio. **No se rellenó con nada**: no se emitió
una orden para fabricar una fila (eso sería una mutación), ni se copió el conjunto declarado como si
fuera observado.

### 4.1 Hallazgo material: el vendor emite 8 valores fuera de los conjuntos declarados

Comparación de lo observado contra los alias declarados en
`packages/matriz-client/src/matriz_client/types.py`:

| Alias | Declarados | Observados | Observados **fuera** del alias | Declarados no observados |
|---|---:|---:|---|---|
| `MarketId` (`:44`) | 1 | 1 | — (ninguno) | — |
| `Currency` (`:95`) | 2 | 2 | — (ninguno) | — |
| `CFICode` (`:50-60`) | 9 | 15 | **6**: `DYXTXR`, `FXXXXX`, `MRIXXX`, `OCEFXS`, `OPEFXS`, `RPXXXX` | — (los 9 declarados aparecieron) |
| `OrderType` (`:38`) vía `orderTypes` | 4 | 6 | **2**: `MARKET_TO_LIMIT`, `PREVIOUSLY_QUOTED` | — (los 4 declarados aparecieron) |

**Esto es exactamente lo que el stream de divergencias NO habría reportado** — y es la razón por la
que el censo lee el wire crudo (D-08). La rama `Literal` de `walk_field` retorna temprano cuando
`policy.literal_enforced` es `False`, y lo es de forma permanente en las cinco copias
(`_decode.py:140` → `POLICY(..., scalar_passthrough=True, literal_enforced=False)`), así que un
valor fuera del conjunto **no produce ningún record de divergencia**: se devuelve byte por byte sin
tocar. El comentario de `_decode.py:541-545` ya lo anticipaba —*"vendor enum growth must not be
fatal"*— y esta corrida es la primera vez que ese crecimiento queda **medido** en vez de previsto.

**No se cambió ningún alias en esta fase.** Ampliar `CFICode` u `OrderType` es un cambio de la forma
declarada de un paquete publicado, no una consecuencia automática de una medición; queda ruteado en
§ 8.

---

## 5. Reafirmación del D-lock (b) — el censo NO lo revoca

El **D-lock (b) de la Phase 29** (`29-DLOCK-RESPONSE-LITERAL.md`) — *los campos de RESPONSE **no**
se cierran como `Literal`* — **SIGUE EN VIGOR**. La existencia de este censo **no lo revoca, no lo
debilita y no abre una excepción**.

La razón operativa, ahora respaldada por medición y no sólo por principio: cerrar un campo RESPONSE
haría **fatal** un valor no visto del vendor, y esta corrida acaba de encontrar **8 valores que el
vendor emite hoy y que los alias declarados no contienen** (§ 4.1). Si `CFICode` y `OrderType`
hubieran estado cerrados con enforcement, esta única corrida de lectura habría fallado sobre 9675
instrumentos. Un censo que vuelve con un conjunto chico y prolijo invita precisamente a la promoción
que el lock prohíbe; este censo vuelve con lo contrario, y aun si hubiera vuelto prolijo la
conclusión sería la misma: **un conjunto observado es una muestra, nunca el dominio.**

El propio script emite esta declaración en runtime (línea `CENSUS-DLOCK`, transcrita en § 1), antes
de la primera request, para que no dependa de que alguien la escriba después.

---

## 6. Advertencia de alcance de venue — este vocabulario es el de `bbsa`

`bbsa` es un sandbox **distinto** de remarkets. El vocabulario de la § 4 es el vocabulario **de
`bbsa` en la ventana `captured_at`**, y nada más:

- Reportarlo como "el vocabulario RESPONSE de `matriz-client`" sería **sobre-generalizar desde una
  sola venue**. Otra venue puede emitir CFI codes, monedas o tipos de orden que ésta no emite.
- **Ésta es la razón exacta por la que el criterio 3 exige el venue en el encabezado**: sin ese
  token, un lector futuro no puede saber que el conjunto está acotado a un sandbox.
- El conjunto tampoco es estable en el tiempo dentro de la misma venue: `distinct` depende del
  catálogo vigente y, para `ordType`, de si la cuenta tiene órdenes.

---

## 7. Corrección adeudada — ruteada, **no absorbida por esta fase**

`29-DLOCK-RESPONSE-LITERAL.md:140-142` afirma que el **stream de divergencias es el mecanismo del
censo**. Es **falso**, y esta corrida lo confirma empíricamente: los 8 valores fuera de conjunto de
la § 4.1 atravesaron el decoder sin emitir un solo record, porque la rama `Literal` de `walk_field`
retorna temprano con `literal_enforced=False` y **nunca llama al sink** (`_decode.py:540-549`).

Ese párrafo vive en un artefacto **firmado**, así que la corrección **pertenece al firmante** y
queda **fuera del alcance de esta fase**. Se nombra acá para que no se pierda, no para absorberla.

---

## 8. Qué NO cierra este censo

LIVE-02 pide **la medición**. Esto la entrega. No entrega, y nadie debe leer "criterio 3 cumplido"
como si lo entregara:

- **`LIVE-MATZ-33` no queda cerrado.** Siguen abiertos los ítems estructurales **S-3**
  (`Instrument.instrumentId` en `byCFICode`/`bySegment` — corregido in-cycle en la Phase 39),
  **S-4** (`InstrumentDetail` no declara 7 claves del wire) y **S-5**
  (`MarketDataSnapshot.LA/.SE/.OI/.CL` no-`Optional` llegando `null`), y sigue sin contrastar el
  piso **`≥24`** de `29-SIZING.md` (equivalente en triples distintos: 14). Este censo no cuenta
  triples de divergencia: cuenta valores de vocabulario. Son unidades distintas y no se restan
  entre sí.
- **No amplía ningún alias.** Los 8 valores fuera de conjunto de la § 4.1 quedan **registrados, no
  aplicados**. Ampliar `CFICode` u `OrderType` es un cambio de la forma declarada de un paquete
  publicado y necesita su propia disposición de semver, igual que `SHAPE-MD-REF-33`.
- **No mide `ordType`.** Queda pendiente para una corrida con órdenes en la cuenta (§ 4).
- **No dice nada de remarkets ni de producción.** Ver § 6.
- **No toca el gate de mutación.** `verification/mutation_gate.py` sigue byte-idéntico y el order
  entry sigue fail-closed bajo `bbsa` **sin cambio de código** (criterio 4).

---

*Phase: 42-re-chequeos-en-vivo-dns-de-higyrus-port-del-gate-de-venue-ce — plan 42-02 (LIVE-02)*
*Corrida: 2026-08-31T21:11:53Z UTC · venue `bbsa` · exit `0` · cero mutaciones*
