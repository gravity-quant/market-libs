"""Smoke tests del cliente sincrónico de IOL (API a nivel módulo)."""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

import iol_client
from iol_client import IOLAuthError, IOLRateLimitError


def test_login_obtiene_access_token(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        json={"access_token": "tok-iol", "expires_in": 900},
    )
    assert iol_client.login() == "tok-iol"
    assert iol_client.client._token == "tok-iol"


def test_login_falla_sin_credenciales() -> None:
    iol_client.configure(username="", password="")
    with pytest.raises(IOLAuthError):
        iol_client.login()


def test_request_propaga_auth_error(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(status_code=401, text="bad")
    with pytest.raises(IOLAuthError):
        iol_client.client._request("GET", "/api/anything")


def test_request_propaga_rate_limit(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(status_code=429, text="too many")
    with pytest.raises(IOLRateLimitError):
        iol_client.client._request("GET", "/api/anything")
