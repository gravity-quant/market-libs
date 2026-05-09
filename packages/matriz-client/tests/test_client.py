"""Tests for the REST client (API a nivel módulo)."""

from __future__ import annotations

import time

import pytest
from pytest_httpx import HTTPXMock

import matriz_client
from matriz_client import client as _client
from matriz_client.exceptions import AuthenticationError, PrimaryAPIError

# ------------------------------------------------------------------
# Auth
# ------------------------------------------------------------------


def test_login_requires_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_client, "_user", "")
    monkeypatch.setattr(_client, "_password", "")
    monkeypatch.setattr(_client, "_token", None)
    with pytest.raises(AuthenticationError):
        _client.login()


def test_login_stores_token_from_header(
    monkeypatch: pytest.MonkeyPatch, httpx_mock: HTTPXMock
) -> None:
    monkeypatch.setattr(_client, "_token", None)
    monkeypatch.setattr(_client, "_token_ts", 0.0)
    httpx_mock.add_response(
        url="https://api.test/auth/getToken",
        method="POST",
        headers={"X-Auth-Token": "tkn-123"},
    )
    token = _client.login()
    assert token == "tkn-123"
    assert _client._token == "tkn-123"
    assert _client._token_ts > 0


def test_login_raises_when_header_missing(
    monkeypatch: pytest.MonkeyPatch, httpx_mock: HTTPXMock
) -> None:
    monkeypatch.setattr(_client, "_token", None)
    httpx_mock.add_response(
        url="https://api.test/auth/getToken",
        method="POST",
        headers={},
    )
    with pytest.raises(AuthenticationError):
        _client.login()


def test_ensure_token_skips_when_fresh(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_client, "_token", "fresh")
    monkeypatch.setattr(_client, "_token_ts", time.time())
    called = {"n": 0}

    def fake_login() -> str:
        called["n"] += 1
        return "new"

    monkeypatch.setattr(_client, "login", fake_login)
    _client._ensure_token()
    assert called["n"] == 0


def test_ensure_token_refreshes_when_stale(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_client, "_token", "old")
    monkeypatch.setattr(_client, "_token_ts", time.time() - (24 * 60 * 60))
    called = {"n": 0}

    def fake_login() -> str:
        called["n"] += 1
        return "new"

    monkeypatch.setattr(_client, "login", fake_login)
    _client._ensure_token()
    assert called["n"] == 1


# ------------------------------------------------------------------
# Request plumbing
# ------------------------------------------------------------------


def test_request_raises_on_error_payload(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        json={"status": "ERROR", "description": "bad symbol", "message": "x"},
    )
    with pytest.raises(PrimaryAPIError) as exc:
        _client._request("GET", "/rest/anything")
    assert exc.value.description == "bad symbol"


def test_request_sends_auth_header(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://api.test/rest/anything?symbol=DLR%2FDIC23",
        match_headers={"X-Auth-Token": "test-token"},
        json={"status": "OK"},
    )
    _client._request("GET", "/rest/anything", params={"symbol": "DLR/DIC23"})


def test_request_with_basic_auth_skips_token(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={"status": "OK"})
    _client._request("GET", "/rest/risk/x", auth_basic=("u", "p"))
    [request] = httpx_mock.get_requests()
    # No mandamos X-Auth-Token cuando va Basic Auth.
    assert "x-auth-token" not in {h.lower() for h in request.headers}
    # httpx serializa Basic Auth automáticamente al header Authorization.
    assert request.headers.get("Authorization", "").startswith("Basic ")


def test_get_filters_none_params(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://api.test/rest/x?symbol=ABC&bar=1",
        json={"status": "OK"},
    )
    _client._get("/rest/x", symbol="ABC", foo=None, bar=1)


# ------------------------------------------------------------------
# Endpoint wrappers
# ------------------------------------------------------------------


def test_get_segments(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://api.test/rest/segment/all",
        json={"status": "OK", "segments": [{"marketSegmentId": "DDF", "marketId": "ROFX"}]},
    )
    segments = matriz_client.get_segments()
    assert len(segments) == 1
    assert segments[0].marketSegmentId == "DDF"
    assert segments[0].marketId == "ROFX"


def test_get_instrument_detail_passes_symbol(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://api.test/rest/instruments/detail?symbol=DLR%2FDIC23&marketId=ROFX",
        json={
            "status": "OK",
            "instrument": {"instrumentId": {"marketId": "ROFX", "symbol": "DLR/DIC23"}},
        },
    )
    result = matriz_client.get_instrument_detail("DLR/DIC23")
    assert result.instrumentId.symbol == "DLR/DIC23"


def test_new_order_builds_params(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        json={"status": "OK", "order": {"clientId": "abc", "proprietary": "PBCP"}},
    )
    matriz_client.new_order(
        symbol="DLR/DIC23",
        side="BUY",
        qty=10,
        account="ACC1",
        price=123.5,
    )
    [request] = httpx_mock.get_requests()
    params = dict(request.url.params)
    assert params["symbol"] == "DLR/DIC23"
    assert params["side"] == "BUY"
    assert params["orderQty"] == "10"
    assert params["account"] == "ACC1"
    assert params["price"] == "123.5"
    assert params["ordType"] == "LIMIT"
    assert params["timeInForce"] == "DAY"
    assert params["cancelPrevious"] == "False"
    assert params["iceberg"] == "False"


def test_new_order_omits_optional_fields(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={"status": "OK", "order": {}})
    matriz_client.new_order(symbol="S", side="SELL", qty=1, account="A")
    [request] = httpx_mock.get_requests()
    params = request.url.params
    assert "price" not in params
    assert "displayQty" not in params
    assert "expireDate" not in params


def test_get_market_data_defaults(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={"status": "OK", "marketData": {"LA": {}}})
    matriz_client.get_market_data("DLR/DIC23")
    [request] = httpx_mock.get_requests()
    params = request.url.params
    assert params["entries"] == "BI,OF,LA,OP,CL,SE,OI"
    assert params["marketId"] == "ROFX"
    assert "depth" not in params


def test_get_positions_uses_basic_auth(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={"status": "OK", "positions": []})
    matriz_client.get_positions("ACC1")
    [request] = httpx_mock.get_requests()
    assert request.url.path == "/rest/risk/position/getPositions/ACC1"
    assert "x-auth-token" not in {h.lower() for h in request.headers}
    assert request.headers.get("Authorization", "").startswith("Basic ")
