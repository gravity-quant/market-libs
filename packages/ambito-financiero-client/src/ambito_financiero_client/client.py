"""Cliente HTTP sincrónico para Ámbito Financiero.

API a nivel módulo::

    import ambito_financiero_client as ambito
    import datetime as dt

    precio = ambito.get_dollar_banco_nacion(dt.date(2026, 4, 7))

La API pública (``mercados.ambito.com``) no requiere autenticación. Sólo se
expone una variable de entorno opcional para sobreescribir el host:

- ``AMBITO_BASE_URL`` (default ``https://mercados.ambito.com``).
"""

from __future__ import annotations

import datetime as dt
import os
from typing import Any

import httpx
from dotenv import load_dotenv

from ambito_financiero_client._parsing import parse_ar_decimal
from ambito_financiero_client.exceptions import (
    AmbitoFinancieroAPIError,
    AmbitoFinancieroAuthError,
    AmbitoFinancieroNoDataError,
    AmbitoFinancieroRateLimitError,
)

load_dotenv()

# La API responde 403 con UA tipo `python-httpx/...`; usamos uno de browser.
_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
_REQUEST_TIMEOUT = 30.0

_base_url: str = os.getenv("AMBITO_BASE_URL", "https://mercados.ambito.com").rstrip("/")
_user_agent: str = _DEFAULT_USER_AGENT
_client = httpx.Client(timeout=_REQUEST_TIMEOUT, headers={"User-Agent": _user_agent})


def configure(*, base_url: str | None = None, user_agent: str | None = None) -> None:
    """Sobrescribe la URL base o el User-Agent en runtime."""
    global _base_url, _user_agent, _client
    if base_url is not None:
        _base_url = base_url.rstrip("/")
    if user_agent is not None:
        _user_agent = user_agent
        _client.headers["User-Agent"] = user_agent


def _raise_for_response(resp: httpx.Response) -> None:
    if resp.status_code in (401, 403):
        raise AmbitoFinancieroAuthError(resp.status_code, resp.text)
    if resp.status_code == 429:
        raise AmbitoFinancieroRateLimitError(resp.status_code, resp.text)
    if resp.is_error:
        raise AmbitoFinancieroAPIError(resp.status_code, resp.text)


def _request(method: str, path: str, **kwargs: Any) -> httpx.Response:
    resp = _client.request(method, f"{_base_url}{path}", **kwargs)
    _raise_for_response(resp)
    return resp


def get_dollar_banco_nacion(date: dt.date) -> float:
    """Cotización vendedor del dólar Banco Nación para ``date``.

    Endpoint: ``/dolarnacion/historico-general/<YYYY-MM-DD>/<YYYY-MM-DD>``.
    Respuesta: ``[["Fecha","Compra","Venta"], ["DD/MM/YYYY","compra","venta"], ...]``
    con precios en formato decimal argentino (``"1.415,00"``).

    Levanta :class:`AmbitoFinancieroNoDataError` si no hay cotización para la
    fecha (fin de semana, feriado o fecha futura).
    """
    formatted = date.strftime("%Y-%m-%d")
    resp = _request("GET", f"/dolarnacion/historico-general/{formatted}/{formatted}")
    rows: list[list[str]] = resp.json()
    if len(rows) < 2:
        raise AmbitoFinancieroNoDataError(f"Sin cotización del dólar Banco Nación para {formatted}")
    _, _, venta = rows[1]
    return parse_ar_decimal(venta)
