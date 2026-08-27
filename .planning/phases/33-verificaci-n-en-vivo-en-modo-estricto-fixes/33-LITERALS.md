# 33-LITERALS.md — censo de valores RESPONSE de los campos `Literal`-aliased (criterio 3)

**Corrida:** 2026-08-27, UTC 01:15–01:20 (ARG 22:15–22:20, miércoles). Mercado ARG **cerrado**.
**Script:** `scripts/literal_census_33.py` (committeado, `5c36b5f`).
**Alcance:** los siete campos RESPONSE de `matriz-client` que llevan uno de cuatro alias
`Literal`, y los dos campos de `iol-client` que DT-07 tiene que disponer.

Este documento **registra evidencia; no actúa sobre ella.** Ningún alias se ensancha, se cierra
ni se pone bajo enforcement, y ningún campo gana un `Literal`. D-09 y D-10 lo prohíben en este
milestone, y cualquier cambio de esa clase sería su propia decisión con su propio artefacto
firmado.

---

## Method

### Por qué el stream de divergencias no puede producir este censo (D-08)

`DecodePolicy` declara `literal_enforced` como su séptimo campo, y las **cinco** constantes
`POLICY` del monorepo lo pasan en `False`:

```
packages/higyrus-client/src/higyrus_client/_decode.py:136         DecodePolicy("", 0, 0.0, False, "from_api_none", False, False)
packages/market-data-client/src/market_data_client/_decode.py:136 DecodePolicy("", 0, 0.0, False, "from_api_none", False, False)
packages/iol-client/src/iol_client/_decode.py:140                 DecodePolicy("", 0, 0.0, False, "from_api_none", False, False)
packages/ambito-financiero-client/src/ambito_financiero_client/_decode.py:141
                                                                  DecodePolicy("", 0, 0.0, False, "from_api_none", False, False)
packages/matriz-client/src/matriz_client/_decode.py:136           DecodePolicy(None, None, None, None, "empty_classmethod", True, False)
```

Con ese valor, la rama `Literal` de `walk_field`
(`packages/higyrus-client/src/higyrus_client/_decode.py:521-534`, idéntica en las cinco copias)
hace lo siguiente:

```python
    if origin is Literal:
        member_types = {type(arg) for arg in args}
        member_ok = value in args if policy.literal_enforced else True
        if member_ok and (not args or type(value) in member_types):
            return value
        sink(model, path, _kind_of(value), _name_of(hint), type(value).__name__)
```

`member_ok` queda **fijo en `True`**. Un valor fuera del conjunto declarado, con el tipo de
runtime correcto (que es el caso interesante: un `"XYZ"` donde el alias declara nueve códigos
CFI), toma el `return value` temprano y **el sink nunca se llama**. No se emite ningún record,
así que `DivergenceHandler.seen` no lo ve y el findings file no lo escribe. Lo único que esa
rama sí valida es el **tipo de runtime** de los miembros del alias.

`29-DLOCK-RESPONSE-LITERAL.md:140-142` afirma exactamente lo contrario:

> *Until then, the observable divergence stream is the census-gathering mechanism: every
> out-of-set value that shows up in a Phase 33 driver run is evidence about the real shape of
> the vendor's enums, accumulated at zero risk to callers.*

**El código shipeado es el autoritativo y el lock está equivocado en ese párrafo.** CONTEXT D-08
ya lo había detectado; esta corrida lo confirma leyendo el código. La consecuencia práctica es
que el `DIVERGENCES=0` de la corrida de 33-05 **no es evidencia de que los valores estén dentro
del conjunto declarado**: es evidencia de que nadie los miró.

`verification.schema.schema_of` tampoco sirve como fuente: reduce cada valor a su **nombre de
tipo**, que es la misma ceguera que `29-SIZING.md:313` documenta para el corpus de 43 archivos
(*"the corpus stores type names"*). Los ocho snapshots committeados de matriz no contienen ni un
solo valor.

**Por eso el censo lee el payload crudo**, con el transporte del propio cliente y sin agregar una
capa HTTP nueva: `_core.build_*_request(...)` → `Client._request(spec)` → `resp.json()`.

### No-vacuidad del extractor

Un extractor roto y un endpoint sin datos producen la misma tabla vacía. `--selftest` ejercita el
walker offline contra payloads sintéticos con la forma de los dos vendors, sin red y sin
credenciales, y verifica los ocho paths esperados:

```
$ uv run python scripts/literal_census_33.py --selftest
selftest-matriz synthetic details[].currency: rows=1 types=['str'] distinct=['ARS']
selftest-matriz synthetic details[].orderTypes[]: rows=2 types=['str'] distinct=['LIMIT', 'MARKET']
selftest-matriz synthetic instruments[].cficode: rows=2 types=['str'] distinct=['FXXXSX', 'ZZZZZZ']
selftest-matriz synthetic instruments[].instrumentId.marketId: rows=2 types=['str'] distinct=['ROFX']
selftest-matriz synthetic orders[].ordType: rows=2 types=['str'] distinct=['LIMIT', 'MARKET']
selftest-matriz synthetic segments[].marketId: rows=1 types=['str'] distinct=['ROFX']
selftest-iol synthetic titulos[].mercado: rows=2 types=['str'] distinct=['bCBA', 'bcba']
selftest-iol synthetic titulos[].plazo: rows=2 types=['str'] distinct=['t1', 't2']
SELFTEST: PASS
```

El caso `ZZZZZZ` del payload sintético es deliberado: es un valor **fuera** del conjunto
declarado de `CFICode`, y el censo lo reporta — que es precisamente lo que el stream de
divergencias no haría. El caso `bCBA` / `bcba` prueba que el censo **no** normaliza mayúsculas,
lo cual es load-bearing para la conclusión de DT-07 más abajo.

### Endpoints y volumen realmente leídos

| Paquete | Endpoint | Filas inspeccionadas | Payload crudo |
|---|---|---:|---|
| `iol-client` | `GET /api/v2/Cotizaciones/{tipo}/argentina/Todos` × 6 tipos | **2 191** filas `titulos[]` | `captures/iol-census-instruments-by-type-*.json` |
| `iol-client` | `GET /api/v2/{mercado}/Titulos/{simbolo}/Cotizacion` (eco, **no-evidencia**) | 1 | `captures/iol-census-quote-echo.json` |
| `matriz-client` | `/rest/segment/all`, `/rest/instruments/all`, `/rest/instruments/details`, `/rest/order/actives`, `/rest/order/all` | **0 — SKIPPED** | — |

Los seis tipos de instrumento son los que `main_iol.py::_ALL_INSTRUMENT_TYPES` ya ejercita:
`obligacionesNegociables`, `titulosPublicos`, `cedears`, `acciones`, `letras`, `cauciones`.

**Todo payload crudo aterrizó en `.planning/verification/captures/`**, gitignored en
`.gitignore:51`, y en ningún otro lado (C-4 / D-11 / T-33-32):

```
$ git status --porcelain .planning/verification/captures/
(vacío)
```

Lo único derivado del wire que llega a este documento son los conjuntos de valores distintos de
los nueve campos nombrados —vocabulario enum-like, no identificadores— más nombres de modelo,
paths de campo, plantillas de endpoint y conteos.

---

## matriz RESPONSE fields (D-09)

### El resultado: `SKIPPED — base URL fuera de política`, no cero

El censo **no midió ni un valor de matriz**, y la causa es la misma que bloqueó el driver en
33-05: `PRIMARY_BASE_URL` apunta a un host que no es el sandbox de remarkets, al que la política
de seguridad de la Phase 5 (**D-MATZ-33**, `main_matriz.py:2550`) restringe toda verificación de
este paquete.

`scripts/literal_census_33.py` lleva **el mismo gate**, y lo aplica **antes** del login: un SKIP
no cuesta ni un round trip contra un host fuera de política.

```
$ uv run python scripts/literal_census_33.py
matriz-client: SKIPPED — base URL fuera de política (D-MATZ-33: la verificación es remarkets-only)
```

**No se rodeó el assert y no se reapuntó `PRIMARY_BASE_URL` a remarkets.** Es la decisión de
33-05, por las dos mismas razones, y ninguna cambió en este plan: (a) la superficie de matriz
incluye entrada de órdenes, y el gate remarkets-only es el mecanismo que impide que una
verificación toque una venue que no es la acordada — la prohibición P-05 de `33-06-PLAN.md`
protege exactamente eso; (b) las credenciales del `.env` fueron emitidas para el host demo, y
mandarlas a un host de terceros distinto sería una fuga de credenciales disfrazada de fix de
configuración.

Las credenciales **sí** autentican (`preflight_33.py` → `matriz-client: AUTH OK`). Esto **no** es
un `SKIPPED — credenciales`: la distinción decide el camino de reparación y por eso el marcador
dice otra cosa.

### La tabla

Una fila por campo. `Rows inspected = 0` en las siete, y **ninguna celda dice cero valores
observados**: el conjunto observado es `SKIPPED`, que es un resultado distinto de un conjunto
vacío (T-33-37).

| Field | Model | Alias | Declared member set | Observed value set | Rows inspected | Endpoint | In-set? | Disposition |
|---|---|---|---|---|---:|---|---|---|
| `marketId` | `Segment` (`models.py:283`) | `MarketId` (`types.py:44`) | `ROFX` | **SKIPPED — base URL fuera de política** | 0 | `/rest/segment/all` | no medido | Decodifica sin enforcement (confirmado por lectura de código, no por wire). Sin valores registrados. **No se ensancha, no se cierra, no se enforcea.** |
| `marketId` | `InstrumentId` (`models.py:262`) | `MarketId` (`types.py:44`) | `ROFX` | **SKIPPED — base URL fuera de política** | 0 | `/rest/instruments/all`, `/rest/instruments/details` | no medido | Ídem. |
| `cficode` | `Instrument` (`models.py:291`) | `CFICode` (`types.py:50`) | `ESXXXX`, `DBXXXX`, `OCASPS`, `OPASPS`, `FXXXSX`, `OPAFXS`, `OCAFXS`, `EMXXXX`, `DBXXFR` | **SKIPPED — base URL fuera de política** | 0 | `/rest/instruments/all` | no medido | Ídem. |
| `cficode` | `InstrumentDetail` (`models.py:303`) | `CFICode` (`types.py:50`) | ídem 9 miembros | **SKIPPED — base URL fuera de política** | 0 | `/rest/instruments/details` | no medido | Ídem. |
| `currency` | `InstrumentDetail` (`models.py:315`) | `Currency` (`types.py:95`) | `ARS`, `USD` | **SKIPPED — base URL fuera de política** | 0 | `/rest/instruments/details` | no medido | Ídem. |
| `orderTypes` | `InstrumentDetail` (`models.py:316`) | `list[OrderType]` (`types.py:38`) | `LIMIT`, `MARKET`, `STOP_LIMIT`, `STOP_LIMIT_MERVAL` | **SKIPPED — base URL fuera de política** | 0 | `/rest/instruments/details` | no medido | Ídem. |
| `ordType` | `Order` (`models.py:352`) | `OrderType` (`types.py:38`) | `LIMIT`, `MARKET`, `STOP_LIMIT`, `STOP_LIMIT_MERVAL` | **SKIPPED — base URL fuera de política** | 0 | `/rest/order/actives`, `/rest/order/all`, `/rest/order/id` | no medido | Ídem. |

**Ninguna de estas siete filas cambió una línea de código.**

```
$ git diff --stat packages/matriz-client/src/matriz_client/types.py packages/matriz-client/src/matriz_client/models.py
(vacío)
```

### Lo que este ciclo sí puede afirmar sobre los cuatro alias

Aunque no haya wire, hay una afirmación que **no** depende de la corrida y que vale la pena
dejar escrita, porque es la mitad del criterio 3 que sí se puede cerrar por lectura:

**Los cuatro alias (`MarketId`, `CFICode`, `Currency`, `OrderType`) decodifican sin
enforcement, hoy, en producción, y un valor fuera de su conjunto declarado se devuelve
byte-por-byte inalterado.** La razón es estructural y está probada por dos vías: `POLICY` de
matriz pasa `literal_enforced=False` **y** `scalar_passthrough=True`
(`packages/matriz-client/src/matriz_client/_decode.py:136`), así que ni el chequeo de membresía
corre ni el fallback de escalar se toma nunca. Los 84 casos de
`packages/matriz-client/tests/test_decode.py` + `test_types.py` siguen verdes y pinean ese
comportamiento.

Lo que **falta** —y es lo que el SKIP se llevó— es *qué valores manda el vendor*. Esa es la mitad
del criterio 3 que queda abierta, y va ruteada abajo.

### Por qué esto no se "arregla" ensanchando ni cerrando

D-09 y `29-DLOCK-RESPONSE-LITERAL.md` prohíben, en este milestone, ensanchar o cerrar cualquiera
de estos alias. El lock es explícito: si un censo sobre respuestas reales muestra que el conjunto
de un alias está genuinamente cerrado, *"it can be closed **then**, as its own decision with its
own artifact and its own signature, with the census as evidence"*. No hay censo, así que no hay
decisión que tomar; y aun con censo, la decisión sería otro artefacto, no éste.

Un valor observado fuera del conjunto declarado tampoco se normalizaría acá: se nombraría y se
rutearía a un destino, como hallazgo real sobre la exactitud del alias. **No hubo ninguno que
nombrar porque no hubo ninguna observación.**

---

## iol `mercado` / `plazo` — DT-07 closure (D-10)

### Lo observado

Fuente: `GET /api/v2/Cotizaciones/{tipo}/argentina/Todos`, que devuelve **todos** los
instrumentos del tipo pedido en la plaza. El conjunto es genuinamente emitido por el vendor, no
un eco de lo que el llamador mandó.

| Field | Model | Declarado | Conjunto observado | Tipo de runtime | Filas | Endpoint |
|---|---|---|---|---:|---|---|
| `mercado` | `Titulo` (`models.py:228`) | `str` | **`{"1"}`** | `str` | **2 191** | `GET /api/v2/Cotizaciones/{tipo}/argentina/Todos` |
| `plazo` | `Titulo` (`models.py:231`) | `str` | **`{"T0", "T1"}`** | `str` | **2 191** | ídem |

Desglose por tipo de instrumento (transcripción verbatim del stdout):

```
iol-client get_instruments_by_type[obligacionesNegociables] titulos[].mercado: rows=883 types=['str'] distinct=['1']
iol-client get_instruments_by_type[obligacionesNegociables] titulos[].plazo:   rows=883 types=['str'] distinct=['T1']
iol-client get_instruments_by_type[titulosPublicos]         titulos[].mercado: rows=207 types=['str'] distinct=['1']
iol-client get_instruments_by_type[titulosPublicos]         titulos[].plazo:   rows=207 types=['str'] distinct=['T1']
iol-client get_instruments_by_type[cedears]                 titulos[].mercado: rows=972 types=['str'] distinct=['1']
iol-client get_instruments_by_type[cedears]                 titulos[].plazo:   rows=972 types=['str'] distinct=['T1']
iol-client get_instruments_by_type[acciones]                titulos[].mercado: rows=99  types=['str'] distinct=['1']
iol-client get_instruments_by_type[acciones]                titulos[].plazo:   rows=99  types=['str'] distinct=['T1']
iol-client get_instruments_by_type[letras]                  titulos[].mercado: rows=29  types=['str'] distinct=['1']
iol-client get_instruments_by_type[letras]                  titulos[].plazo:   rows=29  types=['str'] distinct=['T1']
iol-client get_instruments_by_type[cauciones]               titulos[].mercado: rows=1   types=['str'] distinct=['1']
iol-client get_instruments_by_type[cauciones]               titulos[].plazo:   rows=1   types=['str'] distinct=['T0']
--- iol agregado sobre los 6 tipos ---
iol-client get_instruments_by_type[TOTAL] titulos[].mercado: rows=2191 types=['str'] distinct=['1']
iol-client get_instruments_by_type[TOTAL] titulos[].plazo:   rows=2191 types=['str'] distinct=['T0', 'T1']
```

El tipo de runtime observado es `str` en las 2 191 filas de los dos campos, coincidiendo con lo
declarado. **Eso explica —y valida— el `DIVERGENCES=0` de iol de 33-05**: no había nada de tipo
que reportar. Lo que ese cero no podía decir, y esta tabla sí, es *qué valores* llegaron.

### `Cotizacion.plazo` de `get_quote` — **NO-EVIDENCIA**, registrado a propósito

```
iol-client get_quote plazo: NO-EVIDENCIA (eco de los defaults enviados) distinct=['T2']
```

El llamador mandó `plazo="t2"` (el default de `Client.get_quote`) y la respuesta trae `"T2"`.
**Esto no es un censo**: es el eco del parámetro que el driver eligió, sobre una sola fila. Un
lector que lo tomara como evidencia concluiría que el conjunto de `plazo` incluye `T2`, cuando
lo único que se probó es que el vendor devuelve lo que se le mandó. Queda etiquetado en el stdout
del script y acá, para que nadie pueda confundirlo.

**Pero el eco sí prueba una cosa, y es decisiva:** se envió `"t2"` en minúscula y volvió `"T2"`
en mayúscula. El vendor **normaliza la caja** entre lo que acepta y lo que emite.

### La disposición: `str`, permanente, cerrado con evidencia

**DT-07 queda CERRADO. `Titulo.mercado` y `Titulo.plazo` se quedan en `str`, de forma
permanente.** No es un diferimiento y no es un carry-forward: es una decisión tomada, con el
censo detrás.

El razonamiento, completo:

**1. El conjunto que un vendor EMITE no es demostrablemente el conjunto que ACEPTA como
parámetro de entrada.** El censo es RESPONSE-side por construcción. Variantes de caja, alias y
valores deprecados-pero-todavía-aceptados son todos posibles, y ninguno es observable sin el
barrido deliberado de 4xx que D-10 rechaza por generar tráfico de error intencional contra una
cuenta de brokerage viva.

**2. En este caso la brecha no es hipotética: está medida en las dos direcciones.**

- **`plazo`**: el conjunto RESPONSE es `{"T0", "T1"}` en mayúscula, más `"T2"` del eco. El
  parámetro de entrada que el propio cliente manda por default es `"t2"`, **en minúscula**
  (`client.py:520`, `aio.py`, y los cuatro shims top-level). Un `Literal["T0","T1","T2"]`
  derivado de la respuesta rechazaría en mypy el default que la librería usa hoy en todas sus
  firmas. Un `Literal` en minúscula derivado de las firmas no describiría ni un valor de la
  respuesta. Los dos conjuntos son **disjuntos por caja**, y sólo uno de los dos lados está
  observado.
- **`mercado`**: el conjunto RESPONSE es `{"1"}` — un **código numérico**. El parámetro de
  entrada `mercado` que el cliente manda por default es `"bcba"`
  (`client.py:519`, y `"bcba"` es también el default de `get_historical_quotes`). El campo de
  respuesta y el parámetro de entrada comparten el nombre y **no comparten un solo valor**. La
  evidencia RESPONSE de `mercado` no dice absolutamente nada sobre el dominio de entrada.

**3. Un `Literal` cerrado sobre un conjunto incompleto rompe llamadas legítimas, que es
estrictamente peor que `str`.** Es la regla escrita de DT-07 (*"El conjunto de valores sale de la
verificación en vivo, nunca de suposiciones — un `Literal` incompleto rompe llamadas
legítimas"*) y el riesgo nombrado en `tipado_homogeneo.md:172-173`. Acá el conjunto no sólo
sería incompleto: sería **el conjunto equivocado**.

**4. La cobertura RESPONSE, además, es angosta por razones de mercado.** Las 2 191 filas se
tomaron con el mercado ARG **cerrado** (miércoles 22:15 ARG). `T0` aparece en una sola fila, la
única caución del listado. Un plazo `T3` o un mercado distinto de `"1"` podrían existir
perfectamente en otra ventana o en otra plaza y este censo no los vería. Incluso como censo
RESPONSE, el conjunto observado es un **piso**, no un dominio.

**Esto es "cerrado con evidencia de que la evidencia es insuficiente para cerrar un
`Literal`"** — una posición materialmente más fuerte que cerrar por ausencia de evidencia. La
diferencia es que un lector futuro no tiene que volver a preguntarse si alguien miró: sí se
miró, sobre 2 191 filas de las seis clases de instrumento, y lo que se encontró es la razón
positiva para dejarlo en `str`.

**Lo que este cierre NO hace:** no toca `iol_client.InstrumentType`, que es un `Literal` sobre un
parámetro de **entrada** (`client.py:63`) y una pregunta distinta —`29-DLOCK-RESPONSE-LITERAL.md`
lo dice explícitamente: *"`Literal` on **input** parameters … is a different question and is not
decided here"*. `InstrumentType` sigue exactamente como está.

`packages/iol-client/src/iol_client/types.py` queda como placeholder deliberado, con `__all__`
vacío y sin un solo alias `Literal`; lo único que cambia es que su docstring **deja de apuntar
hacia adelante** a una decisión que ya se tomó.

---

## Carry-forward

| # | Qué queda abierto | Destino |
|---|---|---|
| 1 | **El censo de valores de los siete campos `Literal`-aliased de matriz.** Los cuatro alias quedan confirmados como decodificando sin enforcement (por lectura de código y por los 84 tests verdes), pero **qué valores manda el vendor sigue sin medirse**. Es la mitad del criterio 3 que este ciclo no cierra. | **`LIVE-MATZ-33`** (`ROADMAP.md` § Backlog → *Deferred to v1.7+*), ampliado en este plan con el requisito del censo de valores. Se desbloquea con lo mismo que S-3/S-4/S-5: una corrida contra el sandbox de remarkets con credenciales emitidas para ese host. |
| 2 | **La corrección de `29-DLOCK-RESPONSE-LITERAL.md:140-142`.** El párrafo afirma que el stream de divergencias es el mecanismo de censo, y el código shipeado lo falsifica. El lock está **firmado** (sebadlf, 2026-08-18), así que este plan no lo edita: corregir un artefacto firmado es una decisión del firmante, no del ejecutor. | **`LIVE-MATZ-33`**, que es donde el censo de matriz se retoma y donde el párrafo vuelve a ser load-bearing. La corrección queda registrada acá con su evidencia (`_decode.py:521-534` + las cinco `POLICY`) para que el firmante no tenga que re-derivarla. |
| 3 | **El dominio de ENTRADA de `mercado` / `plazo`.** Sólo observable con el barrido deliberado de 4xx que D-10 rechaza. **No es un carry-forward pendiente**: es una decisión de no hacerlo, tomada, y se re-abre únicamente si aparece una fuente que no requiera tráfico de error contra una cuenta viva (documentación verificable del vendor, o un endpoint de catálogo de plazos). | Ninguno — deliberadamente sin destino. Diferirlo a un ticket lo haría parecer trabajo pendiente cuando es scope rechazado. |

**Nada de lo de arriba dice `TBD`, `later` ni `a futuro`.**

`higyrus-client` no aparece en esta tabla y la ausencia es correcta: no tiene ningún campo
RESPONSE con alias `Literal` ni ninguno de los dos campos de DT-07, así que el SKIP de
`LIVE-HIGY-33` no le quita nada a este censo.
