"""Smoke tests del cliente asincrónico de Wallets (submódulo aio)."""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from wallets_client import WalletsAuthError, aio


async def test_async_request_propaga_auth_error(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(status_code=401, text="bad")
    with pytest.raises(WalletsAuthError):
        await aio._request("GET", "/api/anything")
