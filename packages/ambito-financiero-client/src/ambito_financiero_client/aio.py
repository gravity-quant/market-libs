"""Cliente HTTP asincrónico para Ámbito Financiero.

API a nivel módulo (state independiente del sync)::

    from ambito_financiero_client import aio
    import datetime as dt

    precio = await aio.get_dollar_banco_nacion(dt.date(2026, 4, 7))
    await aio.aclose()
"""

from __future__ import annotations

import asyncio
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

_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
_REQUEST_TIMEOUT = 30.0

_base_url: str = os.getenv("AMBITO_BASE_URL", "https://mercados.ambito.com").rstrip("/")
_user_agent: str = _DEFAULT_USER_AGENT
_client: httpx.AsyncClient | None = None
_client_lock = asyncio.Lock()


def configure(*, base_url: str | None = None, user_agent: str | None = None) -> None:
    """Sobrescribe la URL base o el User-Agent en runtime."""
    global _base_url, _user_agent
    if base_url is not None:
        _base_url = base_url.rstrip("/")
    if user_agent is not None:
        _user_agent = user_agent
        if _client is not None:
            _client.headers["User-Agent"] = user_agent


async def _ensure_http_client() -> httpx.AsyncClient:
    global _client
    if _client is not None:
        return _client
    async with _client_lock:
        if _client is not None:
            return _client
        _client = httpx.AsyncClient(
            timeout=_REQUEST_TIMEOUT,
            headers={"User-Agent": _user_agent},
        )
        return _client


async def aclose() -> None:
    global _client
    async with _client_lock:
        if _client is not None:
            await _client.aclose()
            _client = None


def _raise_for_response(resp: httpx.Response) -> None:
    if resp.status_code in (401, 403):
        raise AmbitoFinancieroAuthError(resp.status_code, resp.text)
    if resp.status_code == 429:
        raise AmbitoFinancieroRateLimitError(resp.status_code, resp.text)
    if resp.is_error:
        raise AmbitoFinancieroAPIError(resp.status_code, resp.text)


async def _request(method: str, path: str, **kwargs: Any) -> httpx.Response:
    client = await _ensure_http_client()
    resp = await client.request(method, f"{_base_url}{path}", **kwargs)
    _raise_for_response(resp)
    return resp


async def get_dollar_banco_nacion(date: dt.date) -> float:
    """Cotización vendedor del dólar Banco Nación para ``date`` (async)."""
    formatted = date.strftime("%Y-%m-%d")
    resp = await _request("GET", f"/dolarnacion/historico-general/{formatted}/{formatted}")
    rows: list[list[str]] = resp.json()
    if len(rows) < 2:
        raise AmbitoFinancieroNoDataError(f"Sin cotización del dólar Banco Nación para {formatted}")
    _, _, venta = rows[1]
    return parse_ar_decimal(venta)
