"""Cliente HTTP (sync y async) para la API de Higyrus.

API a nivel módulo: las funciones se llaman directamente sobre el paquete::

    import higyrus_client

    higyrus_client.login()
    cuentas = higyrus_client.get_listado_cuentas(estado="alta")

Para la versión asincrónica usar el submódulo :mod:`higyrus_client.aio`,
que expone las mismas funciones con ``async def`` y mantiene state propio::

    from higyrus_client import aio

    await aio.login()
    cuentas = await aio.get_listado_cuentas(estado="alta")
    await aio.aclose()

Las credenciales se leen de variables de entorno (``HIGYRUS_BASE_URL``,
``HIGYRUS_USER``, ``HIGYRUS_PASSWORD``, ``HIGYRUS_CLIENT_ID``) cargadas con
``python-dotenv`` al import. Para sobrescribirlas en runtime usar
:func:`configure`.
"""

from higyrus_client.client import (
    configure,
    get_health,
    get_listado_cuentas,
    get_movimientos,
    get_posicion_valuada,
    get_posiciones,
    login,
)
from higyrus_client.exceptions import (
    HigyrusAPIError,
    HigyrusAuthError,
    HigyrusAuthorizationError,
    HigyrusClientError,
    HigyrusRateLimitError,
)
from higyrus_client.models import (
    Administrador,
    Agente,
    Cuenta,
    CuentaBancaria,
    DisposicionesGenerales,
    Domicilio,
    MedioComunicacion,
    Movimiento,
    Operador,
    Parking,
    PersonaRelacionada,
    Posicion,
    PosicionValuada,
    SafeModel,
    Sucursal,
)

__all__ = [
    "Administrador",
    "Agente",
    "Cuenta",
    "CuentaBancaria",
    "DisposicionesGenerales",
    "Domicilio",
    "HigyrusAPIError",
    "HigyrusAuthError",
    "HigyrusAuthorizationError",
    "HigyrusClientError",
    "HigyrusRateLimitError",
    "MedioComunicacion",
    "Movimiento",
    "Operador",
    "Parking",
    "PersonaRelacionada",
    "Posicion",
    "PosicionValuada",
    "SafeModel",
    "Sucursal",
    "configure",
    "get_health",
    "get_listado_cuentas",
    "get_movimientos",
    "get_posicion_valuada",
    "get_posiciones",
    "login",
]

__version__ = "0.1.1"
