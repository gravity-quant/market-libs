# higyrus-client

Cliente HTTP (sync y async) para la **API de Higyrus** — operaciones financieras (comprobantes, cuentas, posiciones, movimientos, contabilidad, unidades, operaciones). El cliente envuelve los endpoints REST en métodos tipados y maneja el ciclo de vida del token Bearer (24 h, refresh automático).

## Instalación

```bash
uv add higyrus-client
# o, dentro del workspace:
uv sync
```

## Configuración

El cliente acepta credenciales por kwargs explícitos o leídas de variables de entorno (`from_env()`). Si usás `.env`, cargalo en tu app antes de instanciar — la librería no depende de `python-dotenv`.

| Variable | Descripción |
|---|---|
| `HIGYRUS_BASE_URL` | URL hasta el prefijo `/api`. Ej: `https://cliente.aunesa.com/Irmo` (requerido) |
| `HIGYRUS_USER` | Usuario de la API (requerido) |
| `HIGYRUS_PASSWORD` | Password de la API (requerido) |
| `HIGYRUS_CLIENT_ID` | Identificador de tenant (opcional, default `""`) |

## Uso

### Sync

```python
from datetime import date
from higyrus_client import HigyrusClient

with HigyrusClient.from_env() as client:
    # El token se obtiene en el primer request — login() es opcional.
    cuentas = client.get_listado_cuentas(estado="alta")
    movs = client.get_movimientos(
        id_cuenta=cuentas[0].id,
        fecha_desde=date(2026, 1, 1),
        fecha_hasta=date(2026, 1, 31),
    )
```

### Async

```python
import asyncio
from datetime import date
from higyrus_client import AsyncHigyrusClient

async def main() -> None:
    async with AsyncHigyrusClient.from_env() as client:
        posiciones = await client.get_posiciones(
            id_cuenta="123",
            fecha=date.today(),
            incluir_parking=True,
        )
        for p in posiciones:
            print(p.especie, p.cantidadLiquidada, p.precio)

asyncio.run(main())
```

### Construcción explícita

```python
client = HigyrusClient(
    base_url="https://cliente.aunesa.com/Irmo",
    username="usuario",
    password="secreto",
    client_id="tenant-1",     # opcional
    timeout=30.0,
)
```

## Métodos disponibles

| Método | Endpoint | Permiso Higyrus |
|---|---|---|
| `login()` | `POST /api/login` | — |
| `get_health()` | `GET /api/health` | — (requiere Bearer) |
| `get_listado_cuentas(...)` | `GET /api/cuentas/listadoCuentas` | `[API] Cuenta - Listado de Cuentas` |
| `get_movimientos(id_cuenta, fecha_desde, fecha_hasta, ...)` | `GET /api/cuentas/{id}/movimientos` | `[API] Cuenta - Consulta de movimientos de una cuenta a partir de una fecha` |
| `get_posiciones(id_cuenta, fecha, ...)` | `GET /api/cuentas/{id}/posiciones` | `[API] Cuenta - Resumen de posiciones` |
| `get_posicion_valuada(id_cuenta, tipo_cuenta, nivel, desde, hasta, ...)` | `GET /api/cuentas/{id}/posicionValuada` | `[API] Consulta de posición valuada` |

Convenciones de query params (manejadas internamente):

- Fechas → `dd/mm/yyyy` (no ISO).
- Booleanos → `"True"` / `"False"` capitalizados.
- `None` → se omite el query param.

## Excepciones

- `HigyrusClientError` — base.
- `HigyrusAPIError(status_code, errors, timestamp)` — non-2xx genérico.
  - `HigyrusAuthError` — `401` (token faltante/inválido).
  - `HigyrusAuthorizationError` — `403` (al usuario le falta el permiso del endpoint en la plataforma Higyrus, distinto de "credenciales rotas").
  - `HigyrusRateLimitError` — `429`.

`errors` y `timestamp` se preservan del envelope del servidor para inspección programática.

## Modelos

Todas las respuestas se modelan con frozen dataclasses sobre `SafeModel.from_api()`, que tolera campos faltantes con defaults seguros (`""`, `0`, `0.0`, `False`, `[]`). Encadenamientos como `posicion.parking[0].diasParking` nunca lanzan: en el peor caso devuelven el default del tipo. Los nombres siguen el wire format (camelCase) verbatim.

Modelos públicos: `Cuenta`, `Health`, `Movimiento`, `Posicion`, `PosicionValuada`, `Parking`, `Administrador`, `Agente`, `CuentaBancaria`, `DisposicionesGenerales`, `Domicilio`, `MedioComunicacion`, `Operador`, `PersonaRelacionada`, `Sucursal`.

## Referencia de la API

El PDF completo de la API está en [`documentation/higyrus-docs.pdf`](./documentation/higyrus-docs.pdf) (143 páginas). Conceptos clave:

- `POST /api/login` devuelve un Bearer válido por 24 h. Sólo un token activo por usuario — generar uno nuevo invalida el anterior.
- Cada endpoint requiere permisos específicos en la plataforma Higyrus; `403` indica permiso faltante.
- Grupos de endpoints: `comprobantes`, `cuentas`, `personas`, `operaciones`, `contabilidad`, `unidades`, `health`.

## Desarrollo

```bash
# Tests sólo de este paquete
uv run pytest packages/higyrus-client

# Lint y format
uv run ruff check packages/higyrus-client
uv run ruff format packages/higyrus-client

# Type checking
uv run mypy packages/higyrus-client/src
```

## Changelog

### v0.3.0 — sin publicar todavía

El bump de `pyproject.toml` y el tag los hace la Phase 34; esta entrada existe
para que la ruptura quede registrada en el momento en que se introduce y no en
el momento en que se publica. **Cualquiera que compile desde HEAD obtiene una
rueda cuya metadata dice `0.2.0` y cuya API es incompatible con la `0.2.0`
publicada** — hasta el bump, esa es la advertencia operativa.

**`get_health()` deja de devolver un diccionario y pasa a devolver un modelo
tipado** (breaking, minor bump en línea 0.x — mismo criterio y misma forma que la
ruptura dict→modelo de `iol-client` v0.3.0).

| Función | Antes | Ahora |
|---|---|---|
| `get_health` | `dict[str, Any]` | `Health` |

- Cambia en sus **dos superficies** (método de clase y shim de módulo) y en
  **sync y async**: cuatro firmas.
- El acceso pasa de `health["status"]` a `health.status`; un acceso por clave
  sobre el resultado levanta `TypeError` (los modelos no son subscriptables).
- **Flip de truthiness:** un dict vacío es falso, una instancia de dataclass es
  verdadera siempre. Cualquier consumidor que ramifique sobre la verdad del
  resultado cambia de comportamiento aunque el código compile y aunque mypy no
  diga nada. Es la parte de la ruptura que más fácil pasa desapercibida.
- **Modelo nuevo exportado:** `Health` (un solo campo, `status: str`), en el
  `__all__` del paquete. Frozen + `slots`, construido vía `SafeModel.from_api()`.
- **Escape hatch:** `health.to_dict()` reproyecta el modelo al dict plano. Sirve
  para call sites de `len()` / `isinstance`; **no** es una entrada válida para un
  snapshot de schema, porque el walker ya coercionó cada campo declarado y
  descartó toda clave no declarada.
- Un body vacío / `204` colapsa al `Health` zero-valued; bajo `strict_decode` esa
  misma shape levanta `HigyrusDecodeError`.
