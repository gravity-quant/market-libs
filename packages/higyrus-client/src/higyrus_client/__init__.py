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

# Phase 8 LOG-01: attach NullHandler + RedactingFilter to package logger BEFORE
# any other imports — library convention per Python Logging HOWTO. NEVER touches
# logging.root. The ``del`` cleanup prevents ``_logging_attach`` from leaking as a
# top-level package attribute (snapshot Pitfall 8 prevention).
from higyrus_client import _logging as _logging_attach

_logging_attach.attach()
del _logging_attach

from higyrus_client.aio import AsyncClient  # noqa: E402
from higyrus_client.client import (  # noqa: E402
    Client,
    configure,
    get_health,
    get_listado_cuentas,
    get_movimientos,
    get_posicion_valuada,
    get_posiciones,
    login,
)
from higyrus_client.client import (  # noqa: E402
    _get_default as _get_default,
)
from higyrus_client.exceptions import (  # noqa: E402
    HigyrusAPIError,
    HigyrusAuthError,
    HigyrusAuthorizationError,
    HigyrusClientError,
    HigyrusDecodeError,
    HigyrusRateLimitError,
)
from higyrus_client.models import (  # noqa: E402
    Administrador,
    Agente,
    Cuenta,
    CuentaBancaria,
    DisposicionesGenerales,
    Domicilio,
    Health,
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
    "AsyncClient",
    "Client",
    "Cuenta",
    "CuentaBancaria",
    "DisposicionesGenerales",
    "Domicilio",
    "Health",
    "HigyrusAPIError",
    "HigyrusAuthError",
    "HigyrusAuthorizationError",
    "HigyrusClientError",
    "HigyrusDecodeError",
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

__version__ = "0.2.0"
