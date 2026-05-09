"""Cliente HTTP asincrónico para Wallets.

API a nivel módulo (state independiente del sync)::

    from wallets_client import aio

    resp = await aio._request("GET", "/algun-endpoint")
    await aio.aclose()
"""

from __future__ import annotations

import asyncio
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
_client: httpx.AsyncClient | None = None
_client_lock = asyncio.Lock()


def configure(*, base_url: str | None = None, token: str | None = None) -> None:
    """Sobrescribe ``base_url`` o ``token`` en runtime."""
    global _base_url, _token
    if base_url is not None:
        _base_url = base_url.rstrip("/")
    if token is not None:
        _token = token


async def _ensure_http_client() -> httpx.AsyncClient:
    global _client
    if _client is not None:
        return _client
    async with _client_lock:
        if _client is not None:
            return _client
        _client = httpx.AsyncClient(timeout=_REQUEST_TIMEOUT)
        return _client


async def aclose() -> None:
    global _client
    async with _client_lock:
        if _client is not None:
            await _client.aclose()
            _client = None


def _raise_for_response(resp: httpx.Response) -> None:
    if resp.status_code in (401, 403):
        raise WalletsAuthError(resp.status_code, resp.text)
    if resp.status_code == 429:
        raise WalletsRateLimitError(resp.status_code, resp.text)
    if resp.is_error:
        raise WalletsAPIError(resp.status_code, resp.text)


async def _request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
) -> httpx.Response:
    headers = {"Authorization": f"Bearer {_token}"} if _token else {}
    client = await _ensure_http_client()
    resp = await client.request(
        method,
        f"{_base_url}{path}",
        params=params,
        json=json_body,
        headers=headers,
    )
    if resp.is_error:
        _raise_for_response(resp)
    return resp
