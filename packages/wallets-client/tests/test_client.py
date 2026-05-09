"""Smoke tests del cliente sincrónico de Wallets (API a nivel módulo)."""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

import wallets_client
from wallets_client import WalletsAuthError, WalletsRateLimitError


def test_request_envia_bearer(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://api.test/api/anything",
        match_headers={"Authorization": "Bearer test-token"},
        json={"ok": True},
    )
    resp = wallets_client.client._request("GET", "/api/anything")
    assert resp.json() == {"ok": True}


def test_request_propaga_auth_error(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(status_code=401, text="bad")
    with pytest.raises(WalletsAuthError):
        wallets_client.client._request("GET", "/api/anything")


def test_request_propaga_rate_limit(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(status_code=429, text="too many")
    with pytest.raises(WalletsRateLimitError):
        wallets_client.client._request("GET", "/api/anything")
