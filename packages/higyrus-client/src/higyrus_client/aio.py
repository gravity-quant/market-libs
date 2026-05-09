"""Cliente HTTP asincrónico para la API de Higyrus.

API a nivel módulo, equivalente al sync pero ``async``::

    from higyrus_client import aio

    cuentas = await aio.get_listado_cuentas(estado="alta")
    await aio.aclose()

El login se dispara automáticamente en la primera llamada que lo necesite;
``aio.login()`` está expuesto por si querés validar credenciales temprano,
pero no es obligatorio. State independiente del módulo sync
(``higyrus_client.client``): hacer login en uno no afecta el otro. Llamar
:func:`aclose` al cerrar para liberar la pool de conexiones de ``httpx``.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import os
import time
from typing import Any

import httpx
from dotenv import load_dotenv

from higyrus_client._params import drop_none, format_bool, format_date
from higyrus_client.exceptions import (
    HigyrusAPIError,
    HigyrusAuthError,
    HigyrusAuthorizationError,
    HigyrusRateLimitError,
)
from higyrus_client.models import Cuenta, Movimiento, Posicion, PosicionValuada

load_dotenv()

_base_url: str = os.getenv("HIGYRUS_BASE_URL", "").rstrip("/")
_client_id: str = os.getenv("HIGYRUS_CLIENT_ID", "")
_user: str = os.getenv("HIGYRUS_USER", "")
_password: str = os.getenv("HIGYRUS_PASSWORD", "")
_token: str | None = None
_token_ts: float = 0.0
_TOKEN_TTL_SECONDS = 23 * 60 * 60
_REQUEST_TIMEOUT = 30.0
_client: httpx.AsyncClient | None = None
_token_lock = asyncio.Lock()
_client_lock = asyncio.Lock()


def configure(
    *,
    base_url: str | None = None,
    username: str | None = None,
    password: str | None = None,
    client_id: str | None = None,
) -> None:
    """Sobrescribe credenciales/URL en runtime y resetea el token cacheado."""
    global _base_url, _user, _password, _client_id, _token, _token_ts
    if base_url is not None:
        _base_url = base_url.rstrip("/")
    if username is not None:
        _user = username
    if password is not None:
        _password = password
    if client_id is not None:
        _client_id = client_id
    _token = None
    _token_ts = 0.0


# ---------------------------------------------------------------------------
# HTTP client lifecycle
# ---------------------------------------------------------------------------


async def _ensure_http_client() -> httpx.AsyncClient:
    """Crea ``httpx.AsyncClient`` lazy en el primer uso (necesita event loop)."""
    global _client
    if _client is not None:
        return _client
    async with _client_lock:
        if _client is not None:
            return _client
        _client = httpx.AsyncClient(timeout=_REQUEST_TIMEOUT)
        return _client


async def aclose() -> None:
    """Cierra ``httpx.AsyncClient`` si fue inicializado.

    Llamar al cerrar la app/event loop para liberar pool de conexiones y
    DNS cache limpiamente.
    """
    global _client
    async with _client_lock:
        if _client is not None:
            await _client.aclose()
            _client = None


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


async def _login_unlocked() -> str:
    """Login sin tomar el lock (asume que el caller ya lo tiene)."""
    global _token, _token_ts

    if not _base_url:
        raise HigyrusAuthError(0, [{"title": "config", "detail": "HIGYRUS_BASE_URL must be set"}])
    if not _user or not _password:
        raise HigyrusAuthError(
            0,
            [{"title": "config", "detail": "HIGYRUS_USER and HIGYRUS_PASSWORD must be set"}],
        )

    client = await _ensure_http_client()
    resp = await client.post(
        f"{_base_url}/api/login",
        json={"clientId": _client_id, "username": _user, "password": _password},
    )
    if resp.status_code == 401:
        _raise_for_response(resp)
    resp.raise_for_status()

    data: dict[str, Any] = resp.json()
    token = data.get("token")
    if not isinstance(token, str) or not token:
        raise HigyrusAuthError(
            resp.status_code,
            [{"title": "auth", "detail": "No token in login response"}],
        )

    _token = token
    _token_ts = time.time()
    return token


async def login() -> str:
    """Autentica contra ``POST /api/login`` y cachea el token.

    La mayoría de los callers no necesitan invocarla: el primer request a
    cualquier endpoint dispara el login automáticamente y los subsiguientes
    lo refrescan antes del vencimiento.
    """
    async with _token_lock:
        return await _login_unlocked()


async def _ensure_token() -> None:
    if _token and (time.time() - _token_ts) < _TOKEN_TTL_SECONDS:
        return
    async with _token_lock:
        # Double-check tras esperar el lock — otro coroutine pudo refrescar.
        if _token and (time.time() - _token_ts) < _TOKEN_TTL_SECONDS:
            return
        await _login_unlocked()


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _raise_for_response(resp: httpx.Response) -> None:
    try:
        payload: dict[str, Any] = resp.json()
    except ValueError:
        payload = {}

    errors = payload.get("errors") if isinstance(payload, dict) else None
    timestamp = payload.get("timestamp") if isinstance(payload, dict) else None

    exc_cls: type[HigyrusAPIError]
    if resp.status_code == 401:
        exc_cls = HigyrusAuthError
    elif resp.status_code == 403:
        exc_cls = HigyrusAuthorizationError
    elif resp.status_code == 429:
        exc_cls = HigyrusRateLimitError
    else:
        exc_cls = HigyrusAPIError

    raise exc_cls(resp.status_code, errors, timestamp)


async def _request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
) -> dict[str, Any] | list[Any] | None:
    await _ensure_token()
    async with _token_lock:
        token = _token
    assert token is not None

    client = await _ensure_http_client()
    resp = await client.request(
        method,
        f"{_base_url}{path}",
        params=drop_none(params) if params else None,
        json=json_body,
        headers={"Authorization": f"Bearer {token}"},
    )

    if not resp.is_success:
        _raise_for_response(resp)

    if resp.status_code == 204 or not resp.content:
        return None

    body: dict[str, Any] | list[Any] = resp.json()
    return body


async def _get(path: str, **params: Any) -> dict[str, Any] | list[Any] | None:
    return await _request("GET", path, params=params)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


async def get_health() -> dict[str, Any]:
    """Estado del servidor vía ``GET /api/health`` (requiere Bearer)."""
    raw = await _request("GET", "/api/health")
    assert isinstance(raw, dict)
    return raw


# ---------------------------------------------------------------------------
# Cuentas
# ---------------------------------------------------------------------------


async def get_movimientos(
    id_cuenta: str,
    fecha_desde: dt.date,
    fecha_hasta: dt.date,
    *,
    especie: str | None = None,
    tipo_titulo: str | None = None,
    tipo_titulo_agente: str | None = None,
    movimiento: str | None = None,
) -> list[Movimiento]:
    """Movimientos de una cuenta en un rango de fechas (async)."""
    raw = await _get(
        f"/api/cuentas/{id_cuenta}/movimientos",
        fechaDesde=format_date(fecha_desde),
        fechaHasta=format_date(fecha_hasta),
        especie=especie,
        tipoTitulo=tipo_titulo,
        tipoTituloAgente=tipo_titulo_agente,
        movimiento=movimiento,
    )
    if raw is None:
        return []
    assert isinstance(raw, list)
    return [Movimiento.from_api(item) for item in raw]


async def get_posicion_valuada(
    id_cuenta: str,
    tipo_cuenta: str,
    nivel: str,
    desde: dt.date,
    hasta: dt.date,
    *,
    lugar: str | None = None,
    estado: str | None = None,
    tipo_titulo: str | None = None,
    extracto: str | None = None,
    ocultar_cerradas: bool | None = None,
    especie: str | None = None,
    concertacion: bool | None = None,
    actualizar: bool | None = None,
) -> list[PosicionValuada]:
    """Posición valuada de una cuenta en un rango de fechas (async)."""
    raw = await _get(
        f"/api/cuentas/{id_cuenta}/posicionValuada",
        tipoCuenta=tipo_cuenta,
        nivel=nivel,
        desde=format_date(desde),
        hasta=format_date(hasta),
        lugar=lugar,
        estado=estado,
        tipoTitulo=tipo_titulo,
        extracto=extracto,
        ocultarCerradas=format_bool(ocultar_cerradas),
        especie=especie,
        concertacion=format_bool(concertacion),
        actualizar=format_bool(actualizar),
    )
    if raw is None:
        return []
    assert isinstance(raw, list)
    return [PosicionValuada.from_api(item) for item in raw]


async def get_listado_cuentas(
    *,
    id_cuenta: list[str] | None = None,
    tipo_cuenta: str | None = None,
    estado: str | None = None,
    fecha_desde: dt.date | None = None,
    fecha_hasta: dt.date | None = None,
) -> list[Cuenta]:
    """Listado completo de cuentas, filtrable (async)."""
    raw = await _get(
        "/api/cuentas/listadoCuentas",
        idCuenta=id_cuenta,
        tipoCuenta=tipo_cuenta,
        estado=estado,
        fechaDesde=format_date(fecha_desde),
        fechaHasta=format_date(fecha_hasta),
    )
    if raw is None:
        return []
    assert isinstance(raw, list)
    return [Cuenta.from_api(item) for item in raw]


async def get_posiciones(
    id_cuenta: str,
    fecha: dt.date,
    *,
    especie: str | None = None,
    incluir_parking: bool = False,
) -> list[Posicion]:
    """Resumen de posiciones de una cuenta a una fecha (async)."""
    raw = await _get(
        f"/api/cuentas/{id_cuenta}/posiciones",
        fecha=format_date(fecha),
        especie=especie,
        incluirParking=format_bool(incluir_parking),
    )
    if raw is None:
        return []
    assert isinstance(raw, list)
    return [Posicion.from_api(item) for item in raw]
