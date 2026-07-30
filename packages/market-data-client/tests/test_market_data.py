"""Pure unit tests for the market-data read builders + parsers (Phase 21-02).

Cubre la superficie PURA del layer ``_core`` para los tres endpoints de
lectura de market data (D-06) y el helper ``drop_none`` (D-07):

- ``drop_none`` dropea SÓLO claves con valor ``None`` y preserva los falsy
  legítimos (``False`` / ``0`` / ``""``).
- ``build_market_data_request`` / ``build_latest_request`` /
  ``build_latest_batch_request`` retornan ``RequestSpec(authenticated=True,
  idempotent=True)`` — ``authenticated=True`` gatea la inyección del Bearer en
  Wave 3, ``idempotent=True`` habilita reintentos sobre los reads.
- ``parse_market_data_response`` / ``parse_latest_response`` estampan
  ``received_at`` UNA sola vez por response (D-01) y lo hilan hacia cada
  ``MarketDataSnapshot``; los collection parsers retornan ``[]`` ante un body
  ``null``/vacío y delegan el status-check a ``raise_for_response``.

Tests PUROS a nivel ``_core`` — NO pasan por el shell del client (la
serialización end-to-end de params httpx la cubren los Plans 03/04). Cada test
construye ``_ClientState`` / ``httpx.Response`` sintéticos directamente.
"""

from __future__ import annotations

import time
from typing import Any

import httpx
import pytest

from market_data_client import _core
from market_data_client._params import drop_none
from market_data_client._state import _ClientState
from market_data_client.exceptions import MarketDataAuthError
from market_data_client.models import LatestRequest, MarketDataSnapshot

_DUMMY_REQUEST = httpx.Request("GET", "http://t")


def _resp(status_code: int, *, json_body: Any = None) -> httpx.Response:
    """Build a synthetic ``httpx.Response`` bound to a dummy request.

    Accepts any JSON-serializable body (list, dict, ``None``) so the collection
    parsers can be exercised against a JSON array and a JSON ``null``.
    """
    if json_body is not None:
        return httpx.Response(status_code, json=json_body, request=_DUMMY_REQUEST)
    return httpx.Response(status_code, request=_DUMMY_REQUEST)


# ----------------------------------------------------------------------
# drop_none (D-07)
# ----------------------------------------------------------------------


def test_drop_none_drops_none_keeps_falsy() -> None:
    """None dropped; False / 0 / "" preserved (legit API inputs)."""
    assert drop_none({"a": None, "b": False, "c": 0, "d": ""}) == {"b": False, "c": 0, "d": ""}


def test_drop_none_empty_when_all_none() -> None:
    assert drop_none({"a": None, "b": None}) == {}


# ----------------------------------------------------------------------
# build_market_data_request (D-06)
# ----------------------------------------------------------------------


def test_build_market_data_request_shape_and_params() -> None:
    """GET /marketdata; authenticated+idempotent; falsy filters preserved."""
    state = _ClientState()
    spec = _core.build_market_data_request(state, market_id="M", active=False, offset=0)
    assert spec.method == "GET"
    assert spec.path == "/marketdata"
    assert spec.authenticated is True
    assert spec.idempotent is True
    assert spec.endpoint_name == "market_data"
    assert spec.params is not None
    assert spec.params["market_id"] == "M"
    assert spec.params["active"] is False
    assert spec.params["offset"] == 0
    # Untouched None optionals must NOT appear.
    assert "prefix" not in spec.params
    assert "limit" not in spec.params


def test_build_market_data_request_all_none_params_collapse_to_none() -> None:
    """All optionals None → empty dict collapses to params=None."""
    state = _ClientState()
    spec = _core.build_market_data_request(state)
    assert spec.params is None


# ----------------------------------------------------------------------
# build_latest_request (D-06)
# ----------------------------------------------------------------------


def test_build_latest_request_shape() -> None:
    state = _ClientState()
    spec = _core.build_latest_request(state, symbol="S", market_id="M")
    assert spec.method == "GET"
    assert spec.path == "/marketdata/latest"
    assert spec.authenticated is True
    assert spec.idempotent is True
    assert spec.endpoint_name == "latest"
    assert spec.params == {"symbol": "S", "market_id": "M"}


# ----------------------------------------------------------------------
# build_latest_batch_request (D-05 / D-06)
# ----------------------------------------------------------------------


def test_build_latest_batch_request_posts_serialized_body() -> None:
    """POST /marketdata/latest; json_body == LatestRequest.to_dict()."""
    state = _ClientState()
    req = LatestRequest(symbols=["A", "B"])
    spec = _core.build_latest_batch_request(state, req)
    assert spec.method == "POST"
    assert spec.path == "/marketdata/latest"
    assert spec.authenticated is True
    assert spec.idempotent is True
    assert spec.endpoint_name == "latest_batch"
    assert spec.json_body == req.to_dict()
    assert spec.json_body == {"symbols": ["A", "B"]}


# ----------------------------------------------------------------------
# parse_market_data_response (D-01)
# ----------------------------------------------------------------------


def test_parse_market_data_response_stamps_received_at_once() -> None:
    """Both snapshots share the SAME received_at (one stamp per response) and > 0."""
    before = time.time()
    body = [
        {"symbol": "AAA", "marketId": "M", "entries": []},
        {"symbol": "BBB", "marketId": "M", "entries": []},
    ]
    resp = _resp(200, json_body=body)
    snapshots = _core.parse_market_data_response(resp)
    after = time.time()
    assert len(snapshots) == 2
    assert all(isinstance(s, MarketDataSnapshot) for s in snapshots)
    assert snapshots[0].received_at == snapshots[1].received_at
    assert snapshots[0].received_at > 0
    assert before <= snapshots[0].received_at <= after
    assert snapshots[0].symbol == "AAA"
    assert snapshots[1].symbol == "BBB"


def test_parse_market_data_response_null_body_returns_empty() -> None:
    """A JSON ``null`` body AND an empty body → [] (collection guard)."""
    null_resp = httpx.Response(200, content=b"null", request=_DUMMY_REQUEST)
    assert _core.parse_market_data_response(null_resp) == []
    empty_resp = httpx.Response(204, request=_DUMMY_REQUEST)
    assert _core.parse_market_data_response(empty_resp) == []


def test_parse_market_data_response_401_raises_auth() -> None:
    resp = _resp(401)
    with pytest.raises(MarketDataAuthError):
        _core.parse_market_data_response(resp)


# ----------------------------------------------------------------------
# parse_latest_response (D-01)
# ----------------------------------------------------------------------


def test_parse_latest_response_stamps_received_at_once() -> None:
    before = time.time()
    body = [
        {"symbol": "AAA", "marketId": "M", "entries": []},
        {"symbol": "BBB", "marketId": "M", "entries": []},
    ]
    resp = _resp(200, json_body=body)
    snapshots = _core.parse_latest_response(resp)
    after = time.time()
    assert len(snapshots) == 2
    assert snapshots[0].received_at == snapshots[1].received_at
    assert before <= snapshots[0].received_at <= after


def test_parse_latest_response_null_body_returns_empty() -> None:
    null_resp = httpx.Response(200, content=b"null", request=_DUMMY_REQUEST)
    assert _core.parse_latest_response(null_resp) == []
    empty_resp = httpx.Response(204, request=_DUMMY_REQUEST)
    assert _core.parse_latest_response(empty_resp) == []
