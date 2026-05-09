"""Cliente HTTP asincrónico para Invertir Online (IOL).

API a nivel módulo (state independiente del sync)::

    from iol_client import aio

    await aio.login()
    # ... métodos específicos a implementar
    await aio.aclose()
"""

from __future__ import annotations

import asyncio
import os
import time
from typing import Any

import httpx
from dotenv import load_dotenv

from iol_client.exceptions import IOLAPIError, IOLAuthError, IOLRateLimitError

load_dotenv()

DEFAULT_BASE_URL = "https://api.invertironline.com"
_REQUEST_TIMEOUT = 30.0
_TOKEN_TTL_BUFFER_SECONDS = 60

_base_url: str = os.getenv("IOL_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
_user: str = os.getenv("IOL_USER", "")
_password: str = os.getenv("IOL_PASSWORD", "")
_token: str | None = None
_token_expires_at: float = 0.0
_client: httpx.AsyncClient | None = None
_token_lock = asyncio.Lock()
_client_lock = asyncio.Lock()


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
        raise IOLAuthError(resp.status_code, resp.text)
    if resp.status_code == 429:
        raise IOLRateLimitError(resp.status_code, resp.text)
    if resp.is_error:
        raise IOLAPIError(resp.status_code, resp.text)


async def _login_unlocked() -> str:
    global _token, _token_expires_at

    if not _user or not _password:
        raise IOLAuthError(0, "IOL_USER y IOL_PASSWORD son requeridos")

    client = await _ensure_http_client()
    resp = await client.post(
        f"{_base_url}/token",
        data={"username": _user, "password": _password, "grant_type": "password"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if resp.is_error:
        _raise_for_response(resp)

    data: dict[str, Any] = resp.json()
    access_token = data.get("access_token")
    expires_in = data.get("expires_in", 900)
    if not isinstance(access_token, str) or not access_token:
        raise IOLAuthError(resp.status_code, "No access_token in response")

    _token = access_token
    _token_expires_at = time.time() + float(expires_in) - _TOKEN_TTL_BUFFER_SECONDS
    return access_token


async def login() -> str:
    """Autentica contra ``POST /token`` y cachea el token."""
    async with _token_lock:
        return await _login_unlocked()


async def _ensure_token() -> None:
    if _token and time.time() < _token_expires_at:
        return
    async with _token_lock:
        if _token and time.time() < _token_expires_at:
            return
        await _login_unlocked()


async def _request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
) -> httpx.Response:
    await _ensure_token()
    async with _token_lock:
        token = _token
    assert token is not None

    client = await _ensure_http_client()
    resp = await client.request(
        method,
        f"{_base_url}{path}",
        params=params,
        json=json_body,
        headers={"Authorization": f"Bearer {token}"},
    )
    if resp.is_error:
        _raise_for_response(resp)
    return resp
