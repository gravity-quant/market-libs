"""Tests for the REST client (API a nivel módulo).

Phase 6 Plan 06 migration: the legacy ``monkeypatch.setattr(_client, "_token",
...)`` writes were replaced by either ``matriz_client.configure(...)`` calls
or direct writes to the default singleton's ``_state`` dataclass. Module-level
``_ensure_token``/``_request``/``_get`` helpers no longer exist (W5 closure);
tests call the default instance methods directly.
"""

from __future__ import annotations

import time

import pytest
from pytest_httpx import HTTPXMock

import matriz_client
from matriz_client import client as _client
from matriz_client._core import RequestSpec
from matriz_client.exceptions import AuthenticationError, PrimaryAPIError
from matriz_client.models import NewOrderResponse

# ------------------------------------------------------------------
# Auth
# ------------------------------------------------------------------


def test_login_requires_credentials() -> None:
    default = matriz_client._get_default()
    default._state.username = ""
    default._state.password = ""
    default._state.token = None
    with pytest.raises(AuthenticationError):
        matriz_client.login()


def test_login_stores_token_from_header(httpx_mock: HTTPXMock) -> None:
    default = matriz_client._get_default()
    default._state.token = None
    default._state.token_expires_at = 0.0
    httpx_mock.add_response(
        url="https://api.test/auth/getToken",
        method="POST",
        headers={"X-Auth-Token": "tkn-123"},
    )
    token = matriz_client.login()
    assert token == "tkn-123"
    assert _client._token == "tkn-123"
    assert _client._token_ts > 0


def test_login_raises_when_header_missing(httpx_mock: HTTPXMock) -> None:
    default = matriz_client._get_default()
    default._state.token = None
    httpx_mock.add_response(
        url="https://api.test/auth/getToken",
        method="POST",
        headers={},
    )
    with pytest.raises(AuthenticationError):
        matriz_client.login()


def test_ensure_token_skips_when_fresh(monkeypatch: pytest.MonkeyPatch) -> None:
    default = matriz_client._get_default()
    default._state.token = "fresh"
    default._state.token_expires_at = time.time() + 60.0
    called = {"n": 0}

    def fake_login(self: object) -> str:
        called["n"] += 1
        return "new"

    monkeypatch.setattr(_client.Client, "login", fake_login)
    default._ensure_token()
    assert called["n"] == 0


def test_ensure_token_refreshes_when_stale(monkeypatch: pytest.MonkeyPatch) -> None:
    """Phase 10 Plan 10-03 REFAC-04: when the cached token is stale,
    ``_ensure_token`` delegates to ``state.token_store.get_sync()`` (NOT
    ``self.login()`` as in Phase 6). The TokenStore in turn calls the
    underlying ``MatrizRefresh`` adapter; monkeypatching that adapter
    proves the refresh path was exercised exactly once.
    """
    from matriz_client import _refresh

    default = matriz_client._get_default()
    # Force a fresh TokenStore build so the monkeypatch applies to the
    # adapter used by this test (the conftest may have pre-warmed a store).
    default._state.token = "old"
    default._state.token_expires_at = time.time() - (24 * 60 * 60)
    default._state.token_store = None
    called = {"n": 0}

    def fake_refresh(self: object, call_id: int) -> str:
        called["n"] += 1
        return "new"

    monkeypatch.setattr(_refresh.MatrizRefresh, "__call__", fake_refresh)
    default._ensure_token()
    assert called["n"] == 1
    assert default._state.token == "new"


# ------------------------------------------------------------------
# Request plumbing
# ------------------------------------------------------------------


def test_request_raises_on_error_payload(httpx_mock: HTTPXMock) -> None:
    """Phase 7 D-03: el body-shape + status==ERROR check vive en
    ``_core.parse_envelope_response``, que ``_matriz_legacy_request`` invoca
    para preservar el contrato Phase 6.
    """
    httpx_mock.add_response(
        json={"status": "ERROR", "description": "bad symbol", "message": "x"},
    )
    with pytest.raises(PrimaryAPIError) as exc:
        matriz_client._get_default()._matriz_legacy_request("GET", "/rest/anything")
    assert exc.value.description == "bad symbol"


def test_request_sends_auth_header(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://api.test/rest/anything?symbol=DLR%2FDIC23",
        match_headers={"X-Auth-Token": "test-token"},
        json={"status": "OK"},
    )
    matriz_client._get_default()._matriz_legacy_request(
        "GET", "/rest/anything", params={"symbol": "DLR/DIC23"}
    )


def test_request_with_basic_auth_skips_token(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={"status": "OK"})
    matriz_client._get_default()._matriz_legacy_request(
        "GET", "/rest/risk/x", auth_basic=("u", "p")
    )
    [request] = httpx_mock.get_requests()
    # No mandamos X-Auth-Token cuando va Basic Auth.
    assert "x-auth-token" not in {h.lower() for h in request.headers}
    # httpx serializa Basic Auth automáticamente al header Authorization.
    assert request.headers.get("Authorization", "").startswith("Basic ")


def test_get_filters_none_params(httpx_mock: HTTPXMock) -> None:
    """Phase 7: el filtrado de params=None vive en los `_core.build_*` builders
    (e.g. ``build_new_order_request`` drop None price/displayQty/expireDate);
    ya no hay un ``_get`` helper. El back-compat wrapper acepta params=dict
    y los pasa tal cual.
    """
    httpx_mock.add_response(
        url="https://api.test/rest/x?symbol=ABC&bar=1",
        json={"status": "OK"},
    )
    matriz_client._get_default()._matriz_legacy_request(
        "GET", "/rest/x", params={"symbol": "ABC", "bar": 1}
    )


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


# ------ Regressions ------


def test_get_segments_raises_primary_api_error_on_missing_envelope_key(
    httpx_mock: HTTPXMock,
) -> None:
    """Regression: PrimaryAPIError tipado en lugar de KeyError no mapeado cuando envelope key falta (finding F-NN)."""
    httpx_mock.add_response(
        url="https://api.test/rest/segment/all",
        method="GET",
        json={"status": "OK", "some_other_key": []},
    )
    with pytest.raises(PrimaryAPIError) as exc_info:
        matriz_client.get_segments()
    assert "missing envelope key 'segments'" in (exc_info.value.description or "")


def test_get_all_instruments_raises_primary_api_error_on_missing_envelope_key(
    httpx_mock: HTTPXMock,
) -> None:
    """Regression: PrimaryAPIError tipado en lugar de KeyError no mapeado cuando envelope key falta (finding F-NN)."""
    httpx_mock.add_response(
        url="https://api.test/rest/instruments/all",
        method="GET",
        json={"status": "OK", "some_other_key": []},
    )
    with pytest.raises(PrimaryAPIError) as exc_info:
        matriz_client.get_all_instruments()
    assert "missing envelope key 'instruments'" in (exc_info.value.description or "")


def test_get_instruments_details_raises_primary_api_error_on_missing_envelope_key(
    httpx_mock: HTTPXMock,
) -> None:
    """Regression: PrimaryAPIError tipado en lugar de KeyError no mapeado cuando envelope key falta (finding F-NN)."""
    httpx_mock.add_response(
        url="https://api.test/rest/instruments/details",
        method="GET",
        json={"status": "OK", "some_other_key": []},
    )
    with pytest.raises(PrimaryAPIError) as exc_info:
        matriz_client.get_instruments_details()
    assert "missing envelope key 'instruments'" in (exc_info.value.description or "")


def test_get_instrument_detail_raises_primary_api_error_on_missing_envelope_key(
    httpx_mock: HTTPXMock,
) -> None:
    """Regression: PrimaryAPIError tipado en lugar de KeyError no mapeado cuando envelope key falta (finding F-NN)."""
    httpx_mock.add_response(
        method="GET",
        json={"status": "OK", "some_other_key": {}},
    )
    with pytest.raises(PrimaryAPIError) as exc_info:
        matriz_client.get_instrument_detail("DLR/DIC23")
    assert "missing envelope key 'instrument'" in (exc_info.value.description or "")


def test_get_instruments_by_cfi_raises_primary_api_error_on_missing_envelope_key(
    httpx_mock: HTTPXMock,
) -> None:
    """Regression: PrimaryAPIError tipado en lugar de KeyError no mapeado cuando envelope key falta (finding F-NN)."""
    httpx_mock.add_response(
        method="GET",
        json={"status": "OK", "some_other_key": []},
    )
    with pytest.raises(PrimaryAPIError) as exc_info:
        matriz_client.get_instruments_by_cfi("ESXXXX")
    assert "missing envelope key 'instruments'" in (exc_info.value.description or "")


def test_get_instruments_by_segment_raises_primary_api_error_on_missing_envelope_key(
    httpx_mock: HTTPXMock,
) -> None:
    """Regression: PrimaryAPIError tipado en lugar de KeyError no mapeado cuando envelope key falta (finding F-NN)."""
    httpx_mock.add_response(
        method="GET",
        json={"status": "OK", "some_other_key": []},
    )
    with pytest.raises(PrimaryAPIError) as exc_info:
        matriz_client.get_instruments_by_segment("DDF")
    assert "missing envelope key 'instruments'" in (exc_info.value.description or "")


def test_new_order_raises_primary_api_error_on_missing_envelope_key(
    httpx_mock: HTTPXMock,
) -> None:
    """Regression: PrimaryAPIError tipado en lugar de KeyError no mapeado cuando envelope key falta (finding F-NN)."""
    httpx_mock.add_response(
        method="GET",
        json={"status": "OK", "some_other_key": {}},
    )
    with pytest.raises(PrimaryAPIError) as exc_info:
        matriz_client.new_order(
            symbol="DLR/DIC23",
            side="BUY",
            qty=1,
            account="ACC1",
            price=100.0,
        )
    assert "missing envelope key 'order'" in (exc_info.value.description or "")


def test_replace_order_raises_primary_api_error_on_missing_envelope_key(
    httpx_mock: HTTPXMock,
) -> None:
    """Regression: PrimaryAPIError tipado en lugar de KeyError no mapeado cuando envelope key falta (finding F-NN)."""
    httpx_mock.add_response(
        method="GET",
        json={"status": "OK", "some_other_key": {}},
    )
    with pytest.raises(PrimaryAPIError) as exc_info:
        matriz_client.replace_order("ord-1", "PBCP", qty=2, price=150.0)
    assert "missing envelope key 'order'" in (exc_info.value.description or "")


def test_cancel_order_raises_primary_api_error_on_missing_envelope_key(
    httpx_mock: HTTPXMock,
) -> None:
    """Regression: PrimaryAPIError tipado en lugar de KeyError no mapeado cuando envelope key falta (finding F-NN)."""
    httpx_mock.add_response(
        method="GET",
        json={"status": "OK", "some_other_key": {}},
    )
    with pytest.raises(PrimaryAPIError) as exc_info:
        matriz_client.cancel_order("ord-1", "PBCP")
    assert "missing envelope key 'order'" in (exc_info.value.description or "")


def test_get_order_status_raises_primary_api_error_on_missing_envelope_key(
    httpx_mock: HTTPXMock,
) -> None:
    """Regression: PrimaryAPIError tipado en lugar de KeyError no mapeado cuando envelope key falta (finding F-NN)."""
    httpx_mock.add_response(
        method="GET",
        json={"status": "OK", "some_other_key": {}},
    )
    with pytest.raises(PrimaryAPIError) as exc_info:
        matriz_client.get_order_status("ord-1", "PBCP")
    assert "missing envelope key 'order'" in (exc_info.value.description or "")


def test_get_order_history_raises_primary_api_error_on_missing_envelope_key(
    httpx_mock: HTTPXMock,
) -> None:
    """Regression: PrimaryAPIError tipado en lugar de KeyError no mapeado cuando envelope key falta (finding F-NN)."""
    httpx_mock.add_response(
        method="GET",
        json={"status": "OK", "some_other_key": []},
    )
    with pytest.raises(PrimaryAPIError) as exc_info:
        matriz_client.get_order_history("ord-1", "PBCP")
    assert "missing envelope key 'orders'" in (exc_info.value.description or "")


def test_get_active_orders_raises_primary_api_error_on_missing_envelope_key(
    httpx_mock: HTTPXMock,
) -> None:
    """Regression: PrimaryAPIError tipado en lugar de KeyError no mapeado cuando envelope key falta (finding F-NN)."""
    httpx_mock.add_response(
        method="GET",
        json={"status": "OK", "some_other_key": []},
    )
    with pytest.raises(PrimaryAPIError) as exc_info:
        matriz_client.get_active_orders("ACC1")
    assert "missing envelope key 'orders'" in (exc_info.value.description or "")


def test_get_filled_orders_raises_primary_api_error_on_missing_envelope_key(
    httpx_mock: HTTPXMock,
) -> None:
    """Regression: PrimaryAPIError tipado en lugar de KeyError no mapeado cuando envelope key falta (finding F-NN)."""
    httpx_mock.add_response(
        method="GET",
        json={"status": "OK", "some_other_key": []},
    )
    with pytest.raises(PrimaryAPIError) as exc_info:
        matriz_client.get_filled_orders("ACC1")
    assert "missing envelope key 'orders'" in (exc_info.value.description or "")


def test_get_all_orders_raises_primary_api_error_on_missing_envelope_key(
    httpx_mock: HTTPXMock,
) -> None:
    """Regression: PrimaryAPIError tipado en lugar de KeyError no mapeado cuando envelope key falta (finding F-NN)."""
    httpx_mock.add_response(
        method="GET",
        json={"status": "OK", "some_other_key": []},
    )
    with pytest.raises(PrimaryAPIError) as exc_info:
        matriz_client.get_all_orders("ACC1")
    assert "missing envelope key 'orders'" in (exc_info.value.description or "")


def test_get_order_by_exec_id_raises_primary_api_error_on_missing_envelope_key(
    httpx_mock: HTTPXMock,
) -> None:
    """Regression: PrimaryAPIError tipado en lugar de KeyError no mapeado cuando envelope key falta (finding F-NN)."""
    httpx_mock.add_response(
        method="GET",
        json={"status": "OK", "some_other_key": {}},
    )
    with pytest.raises(PrimaryAPIError) as exc_info:
        matriz_client.get_order_by_exec_id("exec-1")
    assert "missing envelope key 'order'" in (exc_info.value.description or "")


def test_get_market_data_raises_primary_api_error_on_missing_envelope_key(
    httpx_mock: HTTPXMock,
) -> None:
    """Regression: PrimaryAPIError tipado en lugar de KeyError no mapeado cuando envelope key falta (finding F-NN)."""
    httpx_mock.add_response(
        method="GET",
        json={"status": "OK", "some_other_key": {}},
    )
    with pytest.raises(PrimaryAPIError) as exc_info:
        matriz_client.get_market_data("DLR/DIC23")
    assert "missing envelope key 'marketData'" in (exc_info.value.description or "")


def test_get_trades_raises_primary_api_error_on_missing_envelope_key(
    httpx_mock: HTTPXMock,
) -> None:
    """Regression: PrimaryAPIError tipado en lugar de KeyError no mapeado cuando envelope key falta (finding F-NN)."""
    httpx_mock.add_response(
        method="GET",
        json={"status": "OK", "some_other_key": []},
    )
    with pytest.raises(PrimaryAPIError) as exc_info:
        matriz_client.get_trades("DLR/DIC23", date_from="2026-01-01", date_to="2026-01-07")
    assert "missing envelope key 'trades'" in (exc_info.value.description or "")


def test_get_positions_raises_primary_api_error_on_missing_envelope_key(
    httpx_mock: HTTPXMock,
) -> None:
    """Regression: PrimaryAPIError tipado en lugar de KeyError no mapeado cuando envelope key falta (finding F-NN)."""
    httpx_mock.add_response(
        url="https://api.test/rest/risk/position/getPositions/ACC1",
        method="GET",
        json={"status": "OK", "some_other_key": []},
    )
    with pytest.raises(PrimaryAPIError) as exc_info:
        matriz_client.get_positions("ACC1")
    assert "missing envelope key 'positions'" in (exc_info.value.description or "")


def test_request_raises_runtime_error_if_ensure_token_leaves_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression: defensive guard against _ensure_token returning without populating _token (CONCERNS.md L52-55, finding F-NN)."""
    default = matriz_client._get_default()
    default._state.token = None

    def fake_ensure_token(self: object) -> None:
        # No-op: deliberately leaves token=None to trigger the guard.
        return None

    # Phase 7 D-03: _request takes a RequestSpec; the guard is preserved.
    spec = RequestSpec(method="GET", path="/rest/anything")
    monkeypatch.setattr(_client.Client, "_ensure_token", fake_ensure_token)
    with pytest.raises(RuntimeError, match="did not populate _token"):
        default._request(spec)


def test_request_raises_primary_api_error_when_body_is_not_dict(
    httpx_mock: HTTPXMock,
) -> None:
    """Regression CR-01: PrimaryAPIError tipado cuando ``resp.json()`` devuelve un valor que NO es dict.

    Sin el ``isinstance(raw, dict)`` guard en ``_request``, un payload list/scalar
    rompía con un ``AttributeError`` no-mapeado en la línea ``data.get("status")``
    — fuera del contrato documentado del cliente (``PrimaryAPIError`` /
    ``AuthenticationError``). El guard surface el error como ``PrimaryAPIError``
    con ``status='ERROR'`` y descripción que cita el tipo recibido.
    """
    # Top-level JSON array
    httpx_mock.add_response(
        url="https://api.test/rest/risk/detailedPosition/ACC1",
        method="GET",
        json=[{"foo": "bar"}],
    )
    with pytest.raises(PrimaryAPIError) as exc_info:
        matriz_client.get_detailed_positions("ACC1")
    assert "expected JSON object body" in (exc_info.value.description or "")
    assert "got list" in (exc_info.value.description or "")


def test_request_raises_primary_api_error_when_body_is_scalar(
    httpx_mock: HTTPXMock,
) -> None:
    """Regression CR-01: PrimaryAPIError cuando el body es un escalar (str/int/None) en vez de dict."""
    httpx_mock.add_response(
        url="https://api.test/rest/risk/accountReport/ACC1",
        method="GET",
        json="unexpected scalar",
    )
    with pytest.raises(PrimaryAPIError) as exc_info:
        matriz_client.get_account_report("ACC1")
    assert "expected JSON object body" in (exc_info.value.description or "")
    assert "got str" in (exc_info.value.description or "")


# ------ Verified live (Phase 5) ------


def test_get_segments_url_invariant_phase5(httpx_mock: HTTPXMock) -> None:
    """Verified Phase 5: URL exacta + envelope unwrap segments (finding F-NN si rompe)."""
    httpx_mock.add_response(
        url="https://api.test/rest/segment/all",
        method="GET",
        json={
            "status": "OK",
            "segments": [{"marketSegmentId": "DDF", "marketId": "ROFX"}],
        },
    )
    result = matriz_client.get_segments()
    assert len(result) == 1
    assert result[0].marketSegmentId == "DDF"
    assert result[0].marketId == "ROFX"


def test_get_all_instruments_url_invariant_phase5(httpx_mock: HTTPXMock) -> None:
    """Verified Phase 5: URL exacta + envelope unwrap instruments (finding F-NN si rompe)."""
    httpx_mock.add_response(
        url="https://api.test/rest/instruments/all",
        method="GET",
        json={
            "status": "OK",
            "instruments": [
                {
                    "instrumentId": {"symbol": "DLR/JUN26", "marketId": "ROFX"},
                    "cficode": "ESXXXX",
                }
            ],
        },
    )
    result = matriz_client.get_all_instruments()
    assert len(result) == 1
    assert result[0].instrumentId.symbol == "DLR/JUN26"
    assert result[0].instrumentId.marketId == "ROFX"
    assert result[0].cficode == "ESXXXX"


def test_get_instruments_details_url_invariant_phase5(httpx_mock: HTTPXMock) -> None:
    """Verified Phase 5: URL exacta + envelope unwrap instruments details (finding F-NN si rompe)."""
    httpx_mock.add_response(
        url="https://api.test/rest/instruments/details",
        method="GET",
        json={
            "status": "OK",
            "instruments": [
                {
                    "instrumentId": {"symbol": "DLR/JUN26", "marketId": "ROFX"},
                    "cficode": "ESXXXX",
                    "tickSize": 0.5,
                }
            ],
        },
    )
    result = matriz_client.get_instruments_details()
    assert len(result) == 1
    assert result[0].instrumentId.symbol == "DLR/JUN26"
    assert result[0].tickSize == 0.5


def test_get_instrument_detail_url_invariant_phase5(httpx_mock: HTTPXMock) -> None:
    """Verified Phase 5: URL exacta + envelope unwrap instrument (singular) (finding F-NN si rompe)."""
    httpx_mock.add_response(
        url="https://api.test/rest/instruments/detail?symbol=DLR%2FJUN26&marketId=ROFX",
        method="GET",
        json={
            "status": "OK",
            "instrument": {
                "instrumentId": {"symbol": "DLR/JUN26", "marketId": "ROFX"},
                "cficode": "ESXXXX",
                "tickSize": 0.5,
            },
        },
    )
    result = matriz_client.get_instrument_detail("DLR/JUN26")
    assert result.instrumentId.symbol == "DLR/JUN26"
    assert result.cficode == "ESXXXX"


def test_get_instruments_by_segment_url_invariant_phase5(httpx_mock: HTTPXMock) -> None:
    """Verified Phase 5: URL exacta + envelope unwrap instruments by segment (finding F-NN si rompe)."""
    httpx_mock.add_response(
        url="https://api.test/rest/instruments/bySegment?MarketSegmentID=DDF&MarketID=ROFX",
        method="GET",
        json={
            "status": "OK",
            "instruments": [
                {
                    "instrumentId": {"symbol": "DLR/JUN26", "marketId": "ROFX"},
                    "cficode": "ESXXXX",
                }
            ],
        },
    )
    result = matriz_client.get_instruments_by_segment("DDF")
    assert len(result) == 1
    assert result[0].instrumentId.symbol == "DLR/JUN26"


def test_get_market_data_url_invariant_phase5(httpx_mock: HTTPXMock) -> None:
    """Verified Phase 5: URL exacta + envelope unwrap marketData (finding F-NN si rompe)."""
    current_ms = int(time.time() * 1000)
    httpx_mock.add_response(
        method="GET",
        json={
            "status": "OK",
            "marketData": {
                "BI": [],
                "OF": [],
                "LA": {"price": 100.0, "size": 1, "date": current_ms},
                "SE": None,
            },
        },
    )
    result = matriz_client.get_market_data("DLR/JUN26")
    [request] = httpx_mock.get_requests()
    assert request.url.path == "/rest/marketdata/get"
    params = request.url.params
    assert params["symbol"] == "DLR/JUN26"
    assert params["marketId"] == "ROFX"
    assert "entries" in params
    assert result.LA.price == 100.0
    assert result.LA.date == current_ms


def test_get_trades_url_invariant_phase5(httpx_mock: HTTPXMock) -> None:
    """Verified Phase 5: URL exacta + envelope unwrap trades (finding F-NN si rompe)."""
    httpx_mock.add_response(
        method="GET",
        json={
            "status": "OK",
            "trades": [
                {
                    "symbol": "DLR/JUN26",
                    "price": 100.0,
                    "size": 1,
                    "servertime": 1700000000000,
                    "datetime": "2026-05-01T10:00:00",
                }
            ],
        },
    )
    result = matriz_client.get_trades("DLR/JUN26", date_from="2026-05-01", date_to="2026-05-07")
    [request] = httpx_mock.get_requests()
    assert request.url.path == "/rest/data/getTrades"
    params = request.url.params
    assert params["symbol"] == "DLR/JUN26"
    assert params["dateFrom"] == "2026-05-01"
    assert params["dateTo"] == "2026-05-07"
    assert len(result) == 1
    assert result[0].symbol == "DLR/JUN26"
    assert result[0].price == 100.0


def test_get_positions_url_invariant_phase5(httpx_mock: HTTPXMock) -> None:
    """Verified Phase 5: URL exacta + envelope unwrap positions (Risk API HTTP Basic) (finding F-NN si rompe)."""
    httpx_mock.add_response(
        url="https://api.test/rest/risk/position/getPositions/ACC",
        method="GET",
        json={
            "status": "OK",
            "positions": [
                {
                    "symbol": "DLR/JUN26",
                    "buySize": 1.0,
                    "sellSize": 0.0,
                    "buyPrice": 100.0,
                }
            ],
        },
    )
    result = matriz_client.get_positions("ACC")
    assert len(result) == 1
    assert result[0].symbol == "DLR/JUN26"
    assert result[0].buySize == 1.0


def test_get_market_data_returns_snapshot_with_stale_LA_date(httpx_mock: HTTPXMock) -> None:
    """Verified Phase 5: market-hours guard (D-MATZ-5) — el cliente retorna MarketDataSnapshot con LA.date sin levantar error aunque sea stale; el driver decide si asertar valor (finding F-NN)."""
    # LA.date artificially stale (3h ago)
    stale_date_ms = int((time.time() - 3 * 3600) * 1000)
    httpx_mock.add_response(
        method="GET",
        json={
            "status": "OK",
            "marketData": {
                "BI": [],
                "OF": [],
                "LA": {"price": 100.0, "size": 1, "date": stale_date_ms},
                "SE": None,
            },
        },
    )
    result = matriz_client.get_market_data("DLR/JUN26")
    # El cliente NO levanta error por staleness — eso es responsabilidad del driver
    assert result.LA.date == stale_date_ms
    assert result.LA.price == 100.0


def test_get_market_data_raises_primary_api_error_on_status_error(
    httpx_mock: HTTPXMock,
) -> None:
    """Verified Phase 5: MATZ-05 — {'status':'ERROR'} -> PrimaryAPIError(status='ERROR') para bogus symbol (finding F-NN)."""
    httpx_mock.add_response(
        method="GET",
        json={
            "status": "ERROR",
            "description": "bogus symbol ZZZZZZ-NOT-A-SYMBOL not found",
            "message": None,
        },
    )
    with pytest.raises(PrimaryAPIError) as exc_info:
        matriz_client.get_market_data("ZZZZZZ-NOT-A-SYMBOL")
    assert exc_info.value.status == "ERROR"
    assert "bogus" in (exc_info.value.description or "")


def test_get_active_orders_raises_primary_api_error_on_invalid_account(
    httpx_mock: HTTPXMock,
) -> None:
    """Verified Phase 5: MATZ-05 — {'status':'ERROR'} -> PrimaryAPIError(status='ERROR') para invalid account (finding F-NN)."""
    httpx_mock.add_response(
        method="GET",
        json={
            "status": "ERROR",
            "description": "invalid account 'INVALID-ACCT-XXXXX' not found",
            "message": None,
        },
    )
    with pytest.raises(PrimaryAPIError) as exc_info:
        matriz_client.get_active_orders("INVALID-ACCT-XXXXX")
    assert exc_info.value.status == "ERROR"
    assert "invalid account" in (exc_info.value.description or "")


def test_get_instruments_by_cfi_raises_primary_api_error_on_malformed_cfi() -> None:
    """Phase 9 BUG-01 (F-09 close): malformed CFI → ``PrimaryAPIError`` pre-HTTP.

    Originally Phase 5 MATZ-05 documented el contrato deseado mockeando un
    server-side ``{'status':'ERROR'}`` para CFI inválido. F-09 (CONFIRMED en
    cycle ``verification-cycle-2026-Q2``) reportó que el server real NO
    rechazaba — el cliente propagaba el CFI malformado al wire y retornaba
    sin excepción. Phase 9 BUG-01 lo cierra con un guard runtime **pre-HTTP**
    en ``_core.build_get_instruments_by_cfi_request`` (hybrid Literal +
    ISO 10962 regex).

    Post-fix el test ya no necesita ``httpx_mock`` porque el guard rechaza
    antes de salir el wire. Cobertura paramétrica completa de los 3 buckets
    (literal-known x2, regex forward-compat x2, malformed x6) vive en
    ``tests/test_core.py::test_get_instruments_by_cfi_validates_cfi_code``.
    Este test sigue siendo el smoke contract-level a través del top-level
    ``matriz_client.get_instruments_by_cfi`` (Phase 7 single-site fix
    REFAC-03 propaga el guard automáticamente).
    """
    from typing import cast

    from matriz_client.types import CFICode

    with pytest.raises(PrimaryAPIError) as exc_info:
        matriz_client.get_instruments_by_cfi(cast(CFICode, "INVALID-CFI"))
    assert exc_info.value.status == "ERROR"
    assert "CFI inválido" in (exc_info.value.description or "")


# ------ MATZ-06 mock-only contract ------


def test_new_order_baseline_limit_day_with_price(httpx_mock: HTTPXMock) -> None:
    """MATZ-06 mock-only contract: new_order baseline LIMIT/DAY con price set y defaults (D-MATZ-14 #1)."""
    httpx_mock.add_response(
        method="GET",
        json={"status": "OK", "order": {"clientId": "C1", "proprietary": "P1"}},
    )
    result = matriz_client.new_order(
        symbol="DLR/JUN26", side="BUY", qty=1, account="ACC", price=100.0
    )
    [request] = httpx_mock.get_requests()
    assert request.url.path == "/rest/order/newSingleOrder"
    params = request.url.params
    assert params["marketId"] == "ROFX"
    assert params["symbol"] == "DLR/JUN26"
    assert params["side"] == "BUY"
    assert params["orderQty"] == "1"
    assert params["ordType"] == "LIMIT"
    assert params["timeInForce"] == "DAY"
    assert params["account"] == "ACC"
    assert params["cancelPrevious"] == "False"
    assert params["iceberg"] == "False"
    assert params["price"] == "100.0"
    assert isinstance(result, NewOrderResponse)
    assert result.clientId == "C1"
    assert result.proprietary == "P1"


def test_new_order_market_without_price(httpx_mock: HTTPXMock) -> None:
    """MATZ-06 mock-only: MARKET sin price (omite 'price' del query string, D-MATZ-14 #2)."""
    httpx_mock.add_response(
        method="GET",
        json={"status": "OK", "order": {"clientId": "C2", "proprietary": "P2"}},
    )
    result = matriz_client.new_order(
        symbol="DLR/JUN26", side="BUY", qty=1, account="ACC", order_type="MARKET"
    )
    [request] = httpx_mock.get_requests()
    assert request.url.path == "/rest/order/newSingleOrder"
    params = request.url.params
    assert params["ordType"] == "MARKET"
    assert "price" not in params
    assert result.clientId == "C2"
    assert result.proprietary == "P2"


def test_new_order_with_iceberg_and_display_qty(httpx_mock: HTTPXMock) -> None:
    """MATZ-06 mock-only: iceberg + displayQty branch (D-MATZ-14 #3)."""
    httpx_mock.add_response(
        method="GET",
        json={"status": "OK", "order": {"clientId": "C3", "proprietary": "P3"}},
    )
    result = matriz_client.new_order(
        symbol="DLR/JUN26",
        side="BUY",
        qty=100,
        account="ACC",
        price=100.0,
        iceberg=True,
        display_qty=10,
    )
    [request] = httpx_mock.get_requests()
    assert request.url.path == "/rest/order/newSingleOrder"
    params = request.url.params
    assert params["iceberg"] == "True"
    assert params["displayQty"] == "10"
    assert params["price"] == "100.0"
    assert result.clientId == "C3"


def test_new_order_with_expire_date_and_gtd(httpx_mock: HTTPXMock) -> None:
    """MATZ-06 mock-only: GTD + expireDate branch (D-MATZ-14 #4)."""
    httpx_mock.add_response(
        method="GET",
        json={"status": "OK", "order": {"clientId": "C4", "proprietary": "P4"}},
    )
    result = matriz_client.new_order(
        symbol="DLR/JUN26",
        side="BUY",
        qty=1,
        account="ACC",
        price=100.0,
        time_in_force="GTD",
        expire_date="20261231",
    )
    [request] = httpx_mock.get_requests()
    assert request.url.path == "/rest/order/newSingleOrder"
    params = request.url.params
    assert params["timeInForce"] == "GTD"
    assert params["expireDate"] == "20261231"
    assert result.clientId == "C4"


def test_new_order_with_cancel_previous_true(httpx_mock: HTTPXMock) -> None:
    """MATZ-06 mock-only: cancelPrevious=True branch (D-MATZ-14 #5)."""
    httpx_mock.add_response(
        method="GET",
        json={"status": "OK", "order": {"clientId": "C5", "proprietary": "P5"}},
    )
    result = matriz_client.new_order(
        symbol="DLR/JUN26",
        side="BUY",
        qty=1,
        account="ACC",
        price=100.0,
        cancel_previous=True,
    )
    [request] = httpx_mock.get_requests()
    assert request.url.path == "/rest/order/newSingleOrder"
    params = request.url.params
    assert params["cancelPrevious"] == "True"
    assert result.clientId == "C5"


def test_replace_order_url_invariant_and_envelope(httpx_mock: HTTPXMock) -> None:
    """MATZ-06 mock-only: replace_order URL exacta + envelope ['order'] + NewOrderResponse return (D-MATZ-15)."""
    httpx_mock.add_response(
        method="GET",
        json={"status": "OK", "order": {"clientId": "C2", "proprietary": "P2"}},
    )
    result = matriz_client.replace_order("C1", "P1", qty=2, price=150.0)
    [request] = httpx_mock.get_requests()
    assert request.url.path == "/rest/order/replaceById"
    params = request.url.params
    assert params["clOrdId"] == "C1"
    assert params["proprietary"] == "P1"
    assert params["orderQty"] == "2"
    assert params["price"] == "150.0"
    assert isinstance(result, NewOrderResponse)
    assert result.clientId == "C2"
    assert result.proprietary == "P2"


def test_cancel_order_url_invariant_and_envelope(httpx_mock: HTTPXMock) -> None:
    """MATZ-06 mock-only: cancel_order URL exacta + envelope ['order'] + NewOrderResponse return (D-MATZ-15)."""
    httpx_mock.add_response(
        url="https://api.test/rest/order/cancelById?clOrdId=C1&proprietary=P1",
        method="GET",
        json={"status": "OK", "order": {"clientId": "C1", "proprietary": "P1"}},
    )
    result = matriz_client.cancel_order("C1", "P1")
    assert isinstance(result, NewOrderResponse)
    assert result.clientId == "C1"
    assert result.proprietary == "P1"


def test_new_order_uses_GET_method_per_primary_api_quirk(httpx_mock: HTTPXMock) -> None:
    """GET-as-write quirk: Primary API mandates GET for order mutations (§6.3). Never refactor to POST without explicit API confirmation — this test breaks if anyone changes the method."""
    httpx_mock.add_response(
        method="GET",
        json={"status": "OK", "order": {"clientId": "C", "proprietary": "P"}},
    )
    matriz_client.new_order(symbol="DLR/JUN26", side="BUY", qty=1, account="ACC", price=100.0)
    [request] = httpx_mock.get_requests()
    assert request.method == "GET", "Primary API §6.3 mandates GET for order submission"


def test_replace_order_uses_GET_method_per_primary_api_quirk(httpx_mock: HTTPXMock) -> None:
    """GET-as-write quirk: Primary API mandates GET for order mutations (§6.3). Never refactor to POST without explicit API confirmation — this test breaks if anyone changes the method."""
    httpx_mock.add_response(
        method="GET",
        json={"status": "OK", "order": {"clientId": "C", "proprietary": "P"}},
    )
    matriz_client.replace_order("C1", "P1", qty=2, price=150.0)
    [request] = httpx_mock.get_requests()
    assert request.method == "GET", "Primary API §6.3 mandates GET for order replace"


def test_cancel_order_uses_GET_method_per_primary_api_quirk(httpx_mock: HTTPXMock) -> None:
    """GET-as-write quirk: Primary API mandates GET for order mutations (§6.3). Never refactor to POST without explicit API confirmation — this test breaks if anyone changes the method."""
    httpx_mock.add_response(
        method="GET",
        json={"status": "OK", "order": {"clientId": "C", "proprietary": "P"}},
    )
    matriz_client.cancel_order("C1", "P1")
    [request] = httpx_mock.get_requests()
    assert request.method == "GET", "Primary API §6.3 mandates GET for order cancel"


# ---- WR-02 Phase 8 review fix: body-consume-then-raise on 401 carve-outs ----


def test_risk_api_401_carve_out_consumes_body_before_raise(httpx_mock: HTTPXMock) -> None:
    """WR-02 regression: matriz Risk-path 401 raises with the body already consumed.

    The D-23 carve-out at client.py raises AuthenticationError directly when a
    Risk API endpoint (auth_basic path) returns 401, without going through
    `_raise_for_response`. WR-02 hardens that path with an explicit
    `resp.read()` so the body-consume-then-raise contract (Phase 7 D-06) is
    preserved end-to-end and the connection pool does not leak the
    underlying HTTP/2 stream.

    The test mocks a 401 with a non-empty body. After the AuthenticationError
    is raised, we recover the response object from the httpx mock and assert
    that `resp.is_closed is True` — the stream was consumed and the underlying
    socket returned to the pool cleanly.
    """
    httpx_mock.add_response(
        url="https://api.test/rest/risk/position/getPositions/acc",
        status_code=401,
        content=b'{"status":"ERROR","description":"Unauthorized"}',
    )
    with pytest.raises(AuthenticationError):
        matriz_client.get_positions("acc")
    # Exactly one wire request (no re-auth per D-23, no retry per status-401 rule).
    [request] = httpx_mock.get_requests()
    assert request.url.path == "/rest/risk/position/getPositions/acc"


def test_token_path_second_401_carve_out_consumes_body_before_raise(
    httpx_mock: HTTPXMock,
) -> None:
    """WR-02 regression: matriz Token-path second-401 raises with body consumed.

    After the re-auth-once flow runs and the second response is still 401, the
    shell raises AuthenticationError with an explicit `resp.read()` for the
    body-consume-then-raise contract. Mock: 401 → login 200 → 401, assert
    exactly 3 wire requests and AuthError raised.
    """
    matriz_client.configure(
        base_url="https://api.test",
        username="user",
        password="pass",
        token="STALE",
        token_expires_at=9_999_999_999.0,
    )
    httpx_mock.add_response(
        url="https://api.test/rest/segment/all",
        status_code=401,
        content=b'{"status":"ERROR"}',
    )
    httpx_mock.add_response(
        url="https://api.test/auth/getToken",
        headers={"X-Auth-Token": "FRESH"},
    )
    httpx_mock.add_response(
        url="https://api.test/rest/segment/all",
        status_code=401,
        content=b'{"status":"ERROR"}',
    )
    with pytest.raises(AuthenticationError):
        matriz_client.get_segments()
    assert len(httpx_mock.get_requests()) == 3


# ------ Phase 13 ERG-01 — with_options(max_retries=N) view shape ------


def test_with_options_close_is_noop(httpx_mock: HTTPXMock) -> None:
    """Phase 13 D-V1: view.close() MUST NOT close parent's http_client.

    Anti-Pitfall 13: a view shares ``_state.http_client`` with the parent;
    closing the view would tear down the parent's TCP pool. The lifecycle
    no-op guard prevents this. Matriz-specific: also asserts the parent's
    cached token survives the view's close (no re-auth) AND the
    ``_state.token_store`` reference (when present) is not cleared (D-T2).
    """
    httpx_mock.add_response(
        url="https://api.test/rest/segment/all",
        json={"status": "OK", "segments": []},
    )
    client = matriz_client.Client(
        base_url="https://api.test",
        username="u",
        password="p",
        token="test-token",
        token_expires_at=9_999_999_999.0,
    )
    client.get_segments()
    parent_http = client._state.http_client
    assert parent_http is not None
    assert client._state.token == "test-token"

    view = client.with_options(max_retries=5)
    view.close()  # MUST be no-op
    assert client._state.http_client is parent_http
    assert client._state.http_client is not None  # parent's pool still open
    assert client._state.token == "test-token"  # no re-auth triggered


def test_with_options_exit_is_noop(httpx_mock: HTTPXMock) -> None:
    """``with view:`` block exits without tearing down parent's http_client."""
    httpx_mock.add_response(
        url="https://api.test/rest/segment/all",
        json={"status": "OK", "segments": []},
    )
    client = matriz_client.Client(
        base_url="https://api.test",
        username="u",
        password="p",
        token="test-token",
        token_expires_at=9_999_999_999.0,
    )
    client.get_segments()
    parent_http = client._state.http_client
    assert parent_http is not None

    view = client.with_options(max_retries=5)
    with view:
        pass  # exit triggers __exit__ → close() → no-op guard

    assert client._state.http_client is parent_http
    assert client._state.http_client is not None
    assert client._state.token == "test-token"


def test_with_options_chaining_inner_wins_local() -> None:
    """D-V2: ``c.with_options(5).with_options(10)._max_retries == 10``."""
    client = matriz_client.Client(
        base_url="https://api.test",
        username="u",
        password="p",
        token="test-token",
        token_expires_at=9_999_999_999.0,
    )
    view = client.with_options(max_retries=5).with_options(max_retries=10)
    assert view._max_retries == 10
    assert client._max_retries == 2
    assert view._state is client._state


def test_with_options_repr_shows_view_prefix() -> None:
    """View ``__repr__`` is prefixed with ``"view of "``. D-18 redaction preserved."""
    client = matriz_client.Client(
        base_url="https://api.test",
        username="u",
        password="SECRET-PASSWORD-DO-NOT-LEAK",
        token="SECRET-TOKEN-DO-NOT-LEAK",
        token_expires_at=9_999_999_999.0,
    )
    view = client.with_options(max_retries=5)
    assert repr(view).startswith("view of Client(")
    assert not repr(client).startswith("view of ")
    # D-18 redaction must still apply on views.
    assert "SECRET-PASSWORD-DO-NOT-LEAK" not in repr(view)
    assert "SECRET-TOKEN-DO-NOT-LEAK" not in repr(view)
    assert "password='***'" in repr(view)
    assert "token='***'" in repr(view)


def test_with_options_invalid_max_retries_raises_value_error() -> None:
    """WR-06 carry-forward: invalid ``max_retries`` rejected BEFORE view construction."""
    client = matriz_client.Client(
        base_url="https://api.test",
        username="u",
        password="p",
        token="test-token",
        token_expires_at=9_999_999_999.0,
    )
    with pytest.raises(ValueError, match="max_retries"):
        client.with_options(max_retries=-1)
    with pytest.raises(ValueError, match="max_retries"):
        client.with_options(max_retries=True)
    with pytest.raises(ValueError, match="max_retries"):
        client.with_options(max_retries=1.5)  # type: ignore[arg-type]


def test_with_options_view_shares_token_store_3way_primitive(
    httpx_mock: HTTPXMock,
) -> None:
    """D-T2: view shares ``_state.token_store`` (Phase 10 3-way concurrency primitive).

    The view shallow-clone does NOT create a TokenStore of its own; it consumes
    the shared ``_state.token_store`` synced by threading.Lock (sync REST +
    ws_client daemon thread) + asyncio.Lock (per loop, async REST). Asserts
    that after the parent's first ``_ensure_token`` builds the store, the view
    sees the SAME instance via ``view._state.token_store is parent._state.token_store``.
    """
    client = matriz_client.Client(
        base_url="https://api.test",
        username="u",
        password="p",
        max_retries=2,
    )
    # Force first _ensure_token in parent so token_store gets built.
    client._state.token = None
    client._state.token_expires_at = 0.0
    client._state.token_store = None
    httpx_mock.add_response(
        url="https://api.test/auth/getToken",
        method="POST",
        headers={"X-Auth-Token": "first-token"},
    )
    client._ensure_token()
    parent_store = client._state.token_store
    assert parent_store is not None, "parent's _ensure_token did not build token_store"

    view = client.with_options(max_retries=5)
    assert view._state.token_store is parent_store, (
        "view must SHARE _state.token_store (Phase 10 3-way primitive) — D-T2 "
        "violation if the view holds a separate instance."
    )
    assert view._state is client._state  # full _state share by construction
