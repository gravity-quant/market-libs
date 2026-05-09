"""Cliente HTTP sincrónico para Invertir Online (IOL).

API a nivel módulo::

    import iol_client

    iol_client.login()
    # ... métodos específicos a implementar contra los endpoints de IOL

IOL usa OAuth 2.0 password grant: ``POST /token`` con
``grant_type=password&username=...&password=...`` devuelve
``{"access_token", "refresh_token", "expires_in"}``. Este cliente cachea
``access_token`` y lo refresca automáticamente antes del vencimiento.

Variables de entorno (cargadas con ``python-dotenv``):

- ``IOL_USER`` (requerido)
- ``IOL_PASSWORD`` (requerido)
- ``IOL_BASE_URL`` (opcional, default ``https://api.invertironline.com``).
"""

from __future__ import annotations

import datetime as dt
import os
import time
from typing import Any, Literal

import httpx
from dotenv import load_dotenv

from iol_client.exceptions import IOLAPIError, IOLAuthError, IOLRateLimitError

InstrumentType = Literal[
    "obligacionesNegociables",
    "titulosPublicos",
    "cedears",
    "acciones",
    "letras",
    "cauciones",
]

load_dotenv()

DEFAULT_BASE_URL = "https://api.invertironline.com"
_REQUEST_TIMEOUT = 30.0
# Refrescamos un poco antes del vencimiento documentado (15 min).
_TOKEN_TTL_BUFFER_SECONDS = 60

_base_url: str = os.getenv("IOL_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
_user: str = os.getenv("IOL_USER", "")
_password: str = os.getenv("IOL_PASSWORD", "")
_token: str | None = None
_token_expires_at: float = 0.0
_client = httpx.Client(timeout=_REQUEST_TIMEOUT)


def configure(
    *,
    base_url: str | None = None,
    username: str | None = None,
    password: str | None = None,
) -> None:
    """Sobrescribe credenciales/URL en runtime y resetea el token cacheado."""
    global _base_url, _user, _password, _token, _token_expires_at
    if base_url is not None:
        _base_url = base_url.rstrip("/")
    if username is not None:
        _user = username
    if password is not None:
        _password = password
    _token = None
    _token_expires_at = 0.0


def _raise_for_response(resp: httpx.Response) -> None:
    if resp.status_code in (401, 403):
        raise IOLAuthError(resp.status_code, resp.text)
    if resp.status_code == 429:
        raise IOLRateLimitError(resp.status_code, resp.text)
    if resp.is_error:
        raise IOLAPIError(resp.status_code, resp.text)


def login() -> str:
    """Autentica contra ``POST /token`` (OAuth password grant) y cachea el token."""
    global _token, _token_expires_at

    if not _user or not _password:
        raise IOLAuthError(0, "IOL_USER y IOL_PASSWORD son requeridos")

    resp = _client.post(
        f"{_base_url}/token",
        data={"username": _user, "password": _password, "grant_type": "password"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if resp.is_error:
        _raise_for_response(resp)

    data: dict[str, Any] = resp.json()
    access_token = data.get("access_token")
    expires_in = data.get("expires_in", 900)  # IOL devuelve 900 s típicamente
    if not isinstance(access_token, str) or not access_token:
        raise IOLAuthError(resp.status_code, "No access_token in response")

    _token = access_token
    _token_expires_at = time.time() + float(expires_in) - _TOKEN_TTL_BUFFER_SECONDS
    return access_token


def _ensure_token() -> None:
    if _token and time.time() < _token_expires_at:
        return
    login()


def _request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
) -> httpx.Response:
    """Ejecuta una request autenticada (Bearer)."""
    _ensure_token()
    assert _token is not None

    resp = _client.request(
        method,
        f"{_base_url}{path}",
        params=params,
        json=json_body,
        headers={"Authorization": f"Bearer {_token}"},
    )
    if resp.is_error:
        _raise_for_response(resp)
    return resp


def get_quote(
    simbolo: str,
    *,
    mercado: str = "bcba",
    plazo: str = "t2",
) -> dict[str, Any]:
    """Cotización actual de un título.

    Endpoint: ``GET /api/v2/{mercado}/Titulos/{simbolo}/Cotizacion``.
    """
    resp = _request(
        "GET",
        f"/api/v2/{mercado}/Titulos/{simbolo}/Cotizacion",
        params={
            "model.mercado": mercado,
            "model.simbolo": simbolo,
            "model.plazo": plazo,
        },
    )
    data: dict[str, Any] = resp.json()
    return data


def get_historical_quotes(
    simbolo: str,
    desde: dt.date,
    hasta: dt.date,
    *,
    mercado: str = "bcba",
    ajustada: Literal["ajustada", "sinAjustar"] = "sinAjustar",
) -> list[dict[str, Any]]:
    """Serie histórica de cotizaciones diarias para ``[desde, hasta]``.

    Endpoint:
    ``GET /api/v2/{mercado}/Titulos/{simbolo}/Cotizacion/seriehistorica/{desde}/{hasta}/{ajustada}``.
    """
    resp = _request(
        "GET",
        f"/api/v2/{mercado}/Titulos/{simbolo}/Cotizacion/seriehistorica/"
        f"{desde:%Y-%m-%d}/{hasta:%Y-%m-%d}/{ajustada}",
    )
    data: list[dict[str, Any]] = resp.json()
    return data


def get_instruments(pais: str = "argentina") -> Any:
    """Listado de instrumentos cotizando en ``pais``.

    Endpoint: ``GET /api/v2/{pais}/Titulos/Cotizacion/Instrumentos``.
    """
    resp = _request("GET", f"/api/v2/{pais}/Titulos/Cotizacion/Instrumentos")
    return resp.json()


def get_instruments_by_type(
    instrument_type: InstrumentType,
    *,
    pais: str = "argentina",
) -> list[dict[str, Any]]:
    """Listado de instrumentos filtrado por tipo y país.

    Endpoint: ``GET /api/v2/Cotizaciones/{instrument_type}/{pais}/Todos``.
    Devuelve la lista bajo la clave ``"titulos"`` del payload.
    """
    resp = _request("GET", f"/api/v2/Cotizaciones/{instrument_type}/{pais}/Todos")
    data: dict[str, Any] = resp.json()
    titulos: list[dict[str, Any]] = data.get("titulos", [])
    return titulos
