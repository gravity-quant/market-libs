"""Smoke tests del cliente asincrónico de IOL (submódulo aio)."""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from iol_client import IOLAuthError, aio


async def test_async_login_obtiene_access_token(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        json={"access_token": "tok-iol", "expires_in": 900},
    )
    assert await aio.login() == "tok-iol"


async def test_async_request_propaga_auth_error(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(status_code=401, text="bad")
    with pytest.raises(IOLAuthError):
        await aio._request("GET", "/api/anything")
