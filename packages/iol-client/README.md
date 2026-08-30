# iol-client

Cliente HTTP (sync y async) para la API de [Invertir Online (IOL)](https://www.invertironline.com/).

## Instalación

```bash
uv add iol-client
# o, dentro del workspace:
uv sync
```

## Configuración

Las credenciales se leen del entorno (vía `python-dotenv`, con un `.env` por paquete):

| Variable | Requerida | Default |
|---|---|---|
| `IOL_USER` | sí | — |
| `IOL_PASSWORD` | sí | — |
| `IOL_BASE_URL` | no | `https://api.invertironline.com` |

También pueden pasarse por constructor o por `configure()`, sin tocar el entorno.

## Uso

Las cuatro funciones públicas devuelven **modelos tipados** con acceso por
atributo (ver el Changelog de v0.3.0):

| Función | Devuelve |
|---|---|
| `get_quote(simbolo)` | `Cotizacion` |
| `get_historical_quotes(simbolo, desde, hasta)` | `list[Cotizacion]` |
| `get_instruments(pais)` | `list[Instrumento]` |
| `get_instruments_by_type(instrument_type)` | `list[Titulo]` |

### Sync — shim de nivel superior

El camino más corto: estado de módulo, credenciales del entorno. El token se
cachea en el primer `login()` y se renueva solo.

```python
import iol_client

iol_client.login()
quote = iol_client.get_quote("GGAL")
print(quote.ultimoPrecio, quote.fechaHora)
```

### Sync — cliente basado en clase

Recomendado para código que maneja su propio ciclo de vida o más de un juego de
credenciales. Como context manager, cierra el transporte HTTP al salir.

```python
import datetime as dt

from iol_client import Client

with Client(username="alice", password="secret") as client:
    quote = client.get_quote("GGAL")
    print(quote.ultimoPrecio)

    hasta = dt.date.today()
    serie = client.get_historical_quotes("GGAL", hasta - dt.timedelta(days=7), hasta)
    for row in serie:
        print(row.fechaHora, row.ultimoPrecio)

    for titulo in client.get_instruments_by_type("acciones"):
        print(titulo.simbolo, titulo.ultimoPrecio)
```

### Async

Misma superficie, con cierre explícito. El shim de módulo `aio` tiene su propio
estado, independiente del sync; `AsyncClient` funciona además como async context
manager.

```python
from iol_client import aio

await aio.login()
quote = await aio.get_quote("GGAL")
print(quote.ultimoPrecio)
await aio.aclose()
```

```python
from iol_client import AsyncClient

async with AsyncClient(username="alice", password="secret") as client:
    instrumentos = await client.get_instruments("argentina")
    for i in instrumentos:
        print(i.instrumento, i.pais)
```

## Desarrollo

```bash
# Tests sólo de este paquete
uv run --package iol-client pytest packages/iol-client

# Lint
uv run ruff check packages/iol-client

# Type checking
uv run mypy packages/iol-client
```

## Changelog

### v0.4.0

**Los dos links de libro de órdenes pierden su `| None`** (breaking, minor bump en
línea 0.x — todo consumidor que ramifique por `is None` sobre estos campos necesita
migrar). `Cotizacion` pasa a exponer siempre una lista y `Titulo` siempre un modelo
`Punta`, nunca el valor nulo del lenguaje.

| Antes (0.3.0 publicado) | Ahora (0.4.0) |
| --- | --- |
| `quote.puntas is None` / `quote.puntas or []` | `quote.puntas == []` — el fallback `or []` ya no hace falta: `puntas` es siempre una lista |
| `titulo.puntas is None` | `not titulo.puntas` (o, más estricto, `titulo.puntas == Punta.empty()`) |

`Cotizacion.puntas` pasó de `list[Punta] | None` a `list[Punta]`, y `Titulo.puntas`
de `Punta | None` a `Punta`. Las dos filas **no son simétricas**, y la asimetría es
exactamente la parte que el typechecker NO atrapa — la misma clase de ruptura que el
flip de truthiness de v0.3.0 documentado más abajo:

- **`Cotizacion.puntas`: `None` → `[]`.** Falsy antes, falsy después: ninguna rama
  de truthiness (`if quote.puntas:`) cambia de comportamiento. Sólo se movió el tipo
  declarado. `quote.puntas or []` sigue dando el mismo valor; simplemente ya no hace
  falta escribirlo.
- **`Titulo.puntas`: `None` → `Punta.empty()`.** Sigue siendo falsy, porque
  `SafeModel.__bool__` reporta vacuidad — pero **ya no es el valor nulo del
  lenguaje**. Un consumidor que ramifique por identidad contra la nada
  (`if titulo.puntas is None:`, `assert titulo.puntas is None`, `titulo.puntas or
  fallback` escrito para atrapar el `None`) **deja de tomar esa rama, en silencio**:
  no levanta, no rompe el build y mypy no dice una palabra, porque el tipo declarado
  ahora es correcto. Es la mitad de la ruptura que ninguna herramienta atrapa —
  revisar a mano cada chequeo `is None` sobre este campo antes de actualizar.

A cambio, el acceso encadenado queda siempre válido y sin guard de nulidad:
`titulo.puntas.precioCompra` typechequea bajo `mypy --strict` y devuelve `0.0`
cuando el wire no mandó libro, y `quote.puntas[0].precioCompra` ya no necesita un
`is not None` previo (sigue necesitando, como siempre, que la lista no esté vacía).
Un `puntas` **mal tipado** no cambia en nada: sigue emitiendo su registro de
divergencia y sigue levantando bajo `strict_decode`.

### v0.3.0

**Las respuestas dejan de ser diccionarios y pasan a ser modelos tipados**
(breaking, minor bump en línea 0.x — todo consumidor que lea las respuestas por
clave necesita migrar).

- **Tipos nuevos exportados:** `Cotizacion`, `Instrumento`, `Punta`, `Titulo` y
  la base `SafeModel`, los cinco en el `__all__` del paquete. Son dataclasses
  *frozen* con `slots`, así que un atributo mal escrito es un error duro en
  las dos direcciones: mypy lo rechaza estáticamente y el runtime levanta
  `AttributeError`. Los nombres de campo siguen el wire (camelCase) tal cual.

**Ruptura: dict → modelo**

- Las cuatro funciones públicas devuelven modelos en sus **dos superficies**
  (método de clase y shim de módulo) y en **sync y async** — 16 firmas en total:

  | Función | Antes | Ahora |
  |---|---|---|
  | `get_quote` | `dict[str, Any]` | `Cotizacion` |
  | `get_historical_quotes` | `list[dict[str, Any]]` | `list[Cotizacion]` |
  | `get_instruments` | sin tipar | `list[Instrumento]` |
  | `get_instruments_by_type` | `list[dict[str, Any]]` | `list[Titulo]` |

- El acceso pasa de `quote["ultimoPrecio"]` a `quote.ultimoPrecio`. Un acceso
  por clave sobre el resultado levanta `TypeError` (los modelos no son
  subscriptables).

**Flip de truthiness — la parte que el typechecker NO atrapa**

- Un diccionario vacío es **falso**; una instancia de dataclass es **verdadera
  siempre**. Cualquier consumidor que ramifique sobre la verdad del resultado
  —`if quote:`, `or {}`, `assert not quote`— cambia de comportamiento aunque el
  código compile y aunque mypy no diga nada. Una respuesta sin datos ya no se
  distingue por truthiness: hay que mirar el campo que interesa. Es la parte de
  la ruptura que más fácil pasa desapercibida; revisar cada rama de ese tipo
  antes de actualizar.

**Escape hatch: `to_dict()`**

- Todos los modelos exponen `to_dict()`, que devuelve un diccionario plano
  equivalente al payload del wire (los modelos anidados se aplanan también). Es
  la ruta de migración para el código que necesita seguir viendo dicts:
  `quote.to_dict()["ultimoPrecio"]` funciona igual que antes.
- **Pérdida conocida y aceptada:** el round-trip es *lossy* en dos casos. Un
  valor nulo del wire decodificado a un campo opcional, y cualquier clave que
  el modelo no declare, **no sobreviven** la ida y vuelta — `to_dict()`
  reproduce la forma *declarada*, no la recibida. Es un blind spot documentado,
  a contrastar contra la API en vivo.

**Cambio de forma en el listado de instrumentos**

- `get_instruments` devuelve una **lista al tope**: es lo que la API responde de
  verdad. Una respuesta con cualquier otra forma ahora **levanta**
  `IOLAPIError` en vez de degradar silenciosamente a lista vacía. Una lista
  vacía legítima sigue siendo válida.

**Lo que NO cambia**

- Los campos de respuesta siguen siendo **texto libre**: ningún campo gana un
  conjunto cerrado de valores en este release, aunque el vocabulario observado
  sea chico (`moneda`, `plazo`, `tendencia`, `instrumento`, `pais`…).
- Los parámetros de **mercado** y **plazo** siguen siendo `str`, con los mismos
  defaults (`"bcba"` / `"t2"`).
- Autenticación, refresh de token, reintentos, manejo de errores y las firmas de
  entrada de las cuatro funciones quedan igual.
