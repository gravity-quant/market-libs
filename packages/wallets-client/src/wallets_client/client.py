"""Cliente HTTP sincrónico para Wallets.

API a nivel módulo::

    import wallets_client

    # token y base_url se leen de las variables WALLETS_TOKEN, WALLETS_BASE_URL
    resp = wallets_client._request("GET", "/algun-endpoint")

Variables de entorno (cargadas con ``python-dotenv``):

- ``WALLETS_BASE_URL`` (requerido)
- ``WALLETS_TOKEN`` (requerido)
"""

from __future__ import annotations

import os
from typing import Any

import httpx
from dotenv import load_dotenv

from wallets_client.exceptions import (
    WalletsAPIError,
    WalletsAuthError,
    WalletsRateLimitError,
)

load_dotenv()

_REQUEST_TIMEOUT = 30.0

_base_url: str = os.getenv("WALLETS_BASE_URL", "https://api.wallets.example").rstrip("/")
_token: str = os.getenv("WALLETS_TOKEN", "")
_client = httpx.Client(timeout=_REQUEST_TIMEOUT)


def configure(*, base_url: str | None = None, token: str | None = None) -> None:
    """Sobrescribe ``base_url`` o ``token`` en runtime."""
    global _base_url, _token
    if base_url is not None:
        _base_url = base_url.rstrip("/")
    if token is not None:
        _token = token


def _raise_for_response(resp: httpx.Response) -> None:
    if resp.status_code in (401, 403):
        raise WalletsAuthError(resp.status_code, resp.text)
    if resp.status_code == 429:
        raise WalletsRateLimitError(resp.status_code, resp.text)
    if resp.is_error:
        raise WalletsAPIError(resp.status_code, resp.text)


def _request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
) -> httpx.Response:
    """Ejecuta una request autenticada (Bearer)."""
    headers = {"Authorization": f"Bearer {_token}"} if _token else {}
    resp = _client.request(
        method,
        f"{_base_url}{path}",
        params=params,
        json=json_body,
        headers=headers,
    )
    if resp.is_error:
        _raise_for_response(resp)
    return resp
