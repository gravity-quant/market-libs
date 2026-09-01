"""Pure unit tests for the reference-data read builders + parsers (Plan 22-01).

Covers the PURE ``_core`` surface for the five reference-data read endpoints
(D-01/D-02/D-06/D-07):

- Builders emit ``RequestSpec(method="GET", authenticated=True, idempotent=True)``
  with a distinct ``endpoint_name`` (D-01); ``None`` optionals are dropped via
  ``_params.drop_none`` while legitimate falsy filters (``active=False``,
  ``offset=0``) are preserved, and an empty dict collapses to ``params=None``
  (D-02).
- Collection parsers (``instruments``/``segments``/``symbols``/``calendar``)
  return ``[]`` on a 204 or ``null`` body and capture NO ``received_at`` (D-05/D-06).
- ``parse_calendar_response`` unwraps the develop envelope
  ``{config, coverage, days[], market}`` via ``days`` (D-12), still accepts a bare
  list, and collapses every other body shape to ``[]`` (T-27-11).
- ``parse_calendar_config_response`` returns a single ``CalendarConfig`` and
  falls back to ``CalendarConfig.from_api(None)`` on an empty body, never raising
  (D-07).

Tests are PURE at the ``_core`` level — they do NOT pass through the client
shell. Each test constructs a synthetic ``_ClientState`` / ``httpx.Response``.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from market_data_client import _core
from market_data_client._state import _ClientState
from market_data_client.exceptions import (
    MarketDataAPIError,
    MarketDataAuthError,
    MarketDataRateLimitError,
)
from market_data_client.models import (
    CalendarConfig,
    CalendarDay,
    Instrument,
    Segment,
    Symbol,
)

_DUMMY_REQUEST = httpx.Request("GET", "http://t")


def _resp(status_code: int, *, json_body: Any = None) -> httpx.Response:
    """Build a synthetic ``httpx.Response`` bound to a dummy request."""
    if json_body is not None:
        return httpx.Response(status_code, json=json_body, request=_DUMMY_REQUEST)
    return httpx.Response(status_code, request=_DUMMY_REQUEST)


# The real ``GET /calendar`` body — shape (never values) copied from the committed
# PII-free baseline .planning/verification/schemas/market-data-client/get-calendar.json
# (D-12/T-27-13). The rows live under ``days``, NOT at the top level.
_CALENDAR_ENVELOPE: dict[str, Any] = {
    "config": {"open": "11:00", "close": "17:00", "timezone": "America/Argentina/Buenos_Aires"},
    "coverage": {"current_year_covered": True, "warning": None, "years": [2099]},
    "days": [
        {
            "day": "2099-12-29",
            "closed": True,
            "open_time": None,
            "close_time": None,
            "description": "GSD phase27 probe",
        },
        {
            "day": "2099-12-30",
            "closed": False,
            "open_time": "11:00",
            "close_time": "17:00",
            "description": "media rueda",
        },
    ],
    "market": {"is_open": False, "state": "CLOSED", "last_business_day": "2099-12-28"},
}


# ----------------------------------------------------------------------
# Builders (D-01 / D-02)
# ----------------------------------------------------------------------


def test_builder_instruments_falsy_preserved_none_dropped() -> None:
    """GET /instruments; authenticated+idempotent; falsy filters preserved."""
    state = _ClientState()
    spec = _core.build_instruments_request(state, include_expired=False, offset=0, q="GGAL")
    assert spec.method == "GET"
    assert spec.path == "/instruments"
    assert spec.authenticated is True
    assert spec.idempotent is True
    assert spec.endpoint_name == "instruments"
    assert spec.params is not None
    assert spec.params["include_expired"] is False
    assert spec.params["offset"] == 0
    assert spec.params["q"] == "GGAL"
    assert "segment" not in spec.params
    assert "limit" not in spec.params


def test_builder_instruments_all_none_collapses_to_none() -> None:
    """All optionals None → empty dict collapses to params=None."""
    state = _ClientState()
    spec = _core.build_instruments_request(state)
    assert spec.params is None


def test_builder_segments_no_params() -> None:
    state = _ClientState()
    spec = _core.build_segments_request(state)
    assert spec.method == "GET"
    assert spec.path == "/instruments/segments"
    assert spec.authenticated is True
    assert spec.idempotent is True
    assert spec.endpoint_name == "segments"
    assert spec.params is None


def test_builder_symbols_preserves_active_false() -> None:
    state = _ClientState()
    spec = _core.build_symbols_request(state, active=False)
    assert spec.method == "GET"
    assert spec.path == "/symbols"
    assert spec.authenticated is True
    assert spec.idempotent is True
    assert spec.endpoint_name == "symbols"
    assert spec.params == {"active": False}


def test_builder_calendar_year_param() -> None:
    state = _ClientState()
    spec = _core.build_calendar_request(state, year=2026)
    assert spec.method == "GET"
    assert spec.path == "/calendar"
    assert spec.authenticated is True
    assert spec.idempotent is True
    assert spec.endpoint_name == "calendar"
    assert spec.params == {"year": 2026}


def test_builder_calendar_config_no_params() -> None:
    state = _ClientState()
    spec = _core.build_calendar_config_request(state)
    assert spec.method == "GET"
    assert spec.path == "/calendar/config"
    assert spec.authenticated is True
    assert spec.idempotent is True
    assert spec.endpoint_name == "calendar_config"
    assert spec.params is None


# ----------------------------------------------------------------------
# Collection parsers (D-06) — [] guards, no received_at
# ----------------------------------------------------------------------


def test_parse_instruments_response_null_and_204_return_empty() -> None:
    null_resp = httpx.Response(200, content=b"null", request=_DUMMY_REQUEST)
    assert _core.parse_instruments_response(null_resp) == []
    empty_resp = httpx.Response(204, request=_DUMMY_REQUEST)
    assert _core.parse_instruments_response(empty_resp) == []


def test_parse_instruments_response_returns_list_of_models() -> None:
    # Re-derived (Phase 43, SHAPE-01) to the measured ten-key wire row. The old
    # body sent the camelCase ``marketId`` EXPLICITLY, which suppresses the D-04
    # mirror — so the fixture was stale against a wire that only ever sends
    # ``market_id``. Values synthetic, key set real.
    body = [
        {
            "symbol": "GGAL",
            "segment": "DDF",
            "expired": False,
            "market_id": "ROFX",
            "currency": "ARS",
            "days_to_maturity": 30,
            "maturity": "2099-12-31",
            "outright": True,
            "subscribed": False,
            "active": None,
        },
        {
            "symbol": "YPFD",
            "segment": "DDF",
            "expired": False,
            "market_id": "ROFX",
            "currency": "ARS",
            "days_to_maturity": 60,
            "maturity": "2099-12-31",
            "outright": True,
            "subscribed": False,
            "active": None,
        },
    ]
    result = _core.parse_instruments_response(_resp(200, json_body=body))
    assert len(result) == 2
    assert all(isinstance(i, Instrument) for i in result)
    assert result[0].symbol == "GGAL"
    assert result[0].market_id == "ROFX"
    assert result[0].marketId == result[0].market_id


def test_parse_segments_response_null_and_204_return_empty() -> None:
    null_resp = httpx.Response(200, content=b"null", request=_DUMMY_REQUEST)
    assert _core.parse_segments_response(null_resp) == []
    empty_resp = httpx.Response(204, request=_DUMMY_REQUEST)
    assert _core.parse_segments_response(empty_resp) == []


def test_parse_segments_response_returns_list_of_models() -> None:
    # Re-derived (Phase 43, D-06) to the measured two-key wire row. Until now the
    # declared and wire key sets were DISJOINT, so this test passed VACUOUSLY: an
    # ``isinstance`` check over a row of three empty strings. The value assertions
    # are what make it fail if the row ever comes back unpopulated again.
    body = [{"segment": "DDF", "live_instruments": 7}]
    result = _core.parse_segments_response(_resp(200, json_body=body))
    assert len(result) == 1
    assert isinstance(result[0], Segment)
    assert result[0].segment == "DDF"
    assert result[0].live_instruments == 7


def test_parse_symbols_response_null_and_204_return_empty() -> None:
    null_resp = httpx.Response(200, content=b"null", request=_DUMMY_REQUEST)
    assert _core.parse_symbols_response(null_resp) == []
    empty_resp = httpx.Response(204, request=_DUMMY_REQUEST)
    assert _core.parse_symbols_response(empty_resp) == []


def test_parse_symbols_response_returns_list_of_models() -> None:
    body = [{"symbol": "GGAL", "active": True}]
    result = _core.parse_symbols_response(_resp(200, json_body=body))
    assert len(result) == 1
    assert isinstance(result[0], Symbol)
    assert result[0].active is True


# ----------------------------------------------------------------------
# parse_symbols_response — mutation bodies (D-11 / D-22). F-41 / F-51.
# ----------------------------------------------------------------------
#
# Shapes copied verbatim from the committed LIVE-MUT-01 baselines
# (create-symbol-*-response.json, create-symbols-batch-*-response.json,
# update-symbol-*-response.json). Values are synthetic; the KEY SETS are real.

_CREATE_SYMBOL_BODY = {
    "active": True,
    "created": True,
    "id": 8123,
    "market_id": "ROFX",
    "note": "created",
    "symbol": "GSDPROBE/P27-SYNC",
}

_UPDATE_SYMBOL_BODY = {
    "active": False,
    "id": 8123,
    "market_id": "ROFX",
    "note": "updated",
    "symbol": "GSDPROBE/P27-SYNC",
}

_CREATE_SYMBOLS_BATCH_BODY = {
    "created": 2,
    "items": [
        {"active": True, "created": True, "id": 8124, "market_id": "ROFX", "symbol": "A"},
        {"active": True, "created": False, "id": 8125, "market_id": "ROFX", "symbol": "B"},
    ],
    "note": "batch",
    "reactivated": 0,
    "requested": 2,
}


def test_parse_symbols_response_unwraps_flat_create_body() -> None:
    # D-11: POST /symbols returns a FLAT symbol object. Iterating it yielded one
    # all-default Symbol per KEY — six blanks for a six-key body, measured live.
    result = _core.parse_symbols_response(_resp(200, json_body=_CREATE_SYMBOL_BODY))
    assert len(result) == 1
    assert result[0].symbol == "GSDPROBE/P27-SYNC"
    assert result[0].id == 8123
    assert result[0].market_id == "ROFX"
    assert result[0].active is True


def test_parse_symbols_response_unwraps_flat_patch_body() -> None:
    # PATCH /symbols/{symbol_id} returns the same flat shape, one key shorter.
    result = _core.parse_symbols_response(_resp(200, json_body=_UPDATE_SYMBOL_BODY))
    assert len(result) == 1
    assert result[0].id == 8123
    assert result[0].active is False


def test_parse_symbols_response_unwraps_batch_items_envelope() -> None:
    # POST /symbols/batch returns {created, items[], note, reactivated, requested}
    # — the same envelope shape parse_latest_response already unwraps via `items`.
    result = _core.parse_symbols_response(_resp(200, json_body=_CREATE_SYMBOLS_BATCH_BODY))
    assert len(result) == 2
    assert [row.symbol for row in result] == ["A", "B"]
    assert [row.id for row in result] == [8124, 8125]


def test_parse_symbols_response_no_longer_yields_all_default_rows() -> None:
    # The exact live signature of the bug: a six-key object produced SIX Symbols,
    # all blank. Asserting only "len == 1" above would also pass if the parser
    # returned one blank row, so pin the absence of blanks explicitly.
    result = _core.parse_symbols_response(_resp(200, json_body=_CREATE_SYMBOL_BODY))
    assert len(result) != len(_CREATE_SYMBOL_BODY)
    assert [row for row in result if row.symbol == ""] == []


def test_parse_symbols_response_read_path_is_unregressed() -> None:
    # The GET /symbols bare-list path was never the defect; the unwrap ladder must
    # not have broken it. Row shape from get-symbols-probe-prefix-sync.json.
    body = [
        {
            "active": False,
            "created_at": "2026-08-01T15:54:36",
            "id": 8123,
            "market_id": "ROFX",
            "received_at": None,
            "symbol": "GSDPROBE/P27-SYNC",
            "updated_at": "2026-08-01T15:54:38",
        }
    ]
    result = _core.parse_symbols_response(_resp(200, json_body=body))
    assert len(result) == 1
    assert result[0].symbol == "GSDPROBE/P27-SYNC"
    assert result[0].created_at == "2026-08-01T15:54:36"


def test_parse_symbols_response_dict_without_rows_returns_empty() -> None:
    # Collection guard: a dict with neither `items` nor `symbol` → [] rather than
    # one blank Symbol per key.
    assert _core.parse_symbols_response(_resp(200, json_body={"note": "nothing here"})) == []


def test_parse_symbols_response_non_list_items_returns_empty() -> None:
    # Second guard: a scalar or object `items` value collapses to [].
    assert _core.parse_symbols_response(_resp(200, json_body={"items": "nope"})) == []
    assert _core.parse_symbols_response(_resp(200, json_body={"items": {"a": 1}})) == []


def test_parse_symbols_response_scalar_body_returns_empty() -> None:
    scalar_resp = httpx.Response(200, content=b"42", request=_DUMMY_REQUEST)
    assert _core.parse_symbols_response(scalar_resp) == []


def test_parse_symbols_response_items_wins_over_flat_symbol_key() -> None:
    # Discrimination is by key and the precedence is explicit: an envelope that
    # also happens to carry a top-level `symbol` is still read through `items`.
    body = {"items": [{"symbol": "A"}], "symbol": "DECOY"}
    result = _core.parse_symbols_response(_resp(200, json_body=body))
    assert [row.symbol for row in result] == ["A"]


def test_parse_calendar_response_null_and_204_return_empty() -> None:
    null_resp = httpx.Response(200, content=b"null", request=_DUMMY_REQUEST)
    assert _core.parse_calendar_response(null_resp) == []
    empty_resp = httpx.Response(204, request=_DUMMY_REQUEST)
    assert _core.parse_calendar_response(empty_resp) == []


def test_parse_calendar_response_unwraps_days_envelope() -> None:
    # D-12: develop returns {config, coverage, days[], market}; iterating the body
    # as a list yields the FOUR envelope KEYS, not the days. Shape copied from the
    # committed .planning/verification/schemas/.../get-calendar.json baseline.
    body = _CALENDAR_ENVELOPE
    result = _core.parse_calendar_response(_resp(200, json_body=body))
    assert len(result) == 2
    assert all(isinstance(row, CalendarDay) for row in result)
    assert result[0].day == "2099-12-29"
    assert result[0].closed is True
    assert result[0].description == "GSD phase27 probe"
    assert result[0].open_time is None
    assert result[1].day == "2099-12-30"
    assert result[1].closed is False
    assert result[1].open_time == "11:00"
    assert result[1].close_time == "17:00"


def test_parse_calendar_response_bare_list_still_parses() -> None:
    # Backwards tolerance: a bare list of day dicts is still accepted as-is.
    body = [{"day": "2026-07-30", "closed": True}]
    result = _core.parse_calendar_response(_resp(200, json_body=body))
    assert len(result) == 1
    assert isinstance(result[0], CalendarDay)
    assert result[0].day == "2026-07-30"
    assert result[0].closed is True


def test_parse_calendar_response_dict_without_days_returns_empty() -> None:
    # Collection guard: no `days` key → [] (no KeyError, no key-iteration rows).
    assert _core.parse_calendar_response(_resp(200, json_body={"config": {}})) == []


def test_parse_calendar_response_non_list_days_returns_empty() -> None:
    # Second guard: a scalar or object `days` value collapses to [] (T-27-11).
    assert _core.parse_calendar_response(_resp(200, json_body={"days": "nope"})) == []
    assert _core.parse_calendar_response(_resp(200, json_body={"days": {"a": 1}})) == []


def test_parse_calendar_response_scalar_body_returns_empty() -> None:
    scalar_resp = httpx.Response(200, content=b"42", request=_DUMMY_REQUEST)
    assert _core.parse_calendar_response(scalar_resp) == []


def test_parse_calendar_response_401_raises_auth() -> None:
    # Body-consume-then-raise order is unchanged: error statuses still raise.
    with pytest.raises(MarketDataAuthError):
        _core.parse_calendar_response(_resp(401))


def test_parse_calendar_response_429_raises_rate_limit() -> None:
    with pytest.raises(MarketDataRateLimitError):
        _core.parse_calendar_response(_resp(429))


def test_parse_calendar_response_422_raises_api_error() -> None:
    with pytest.raises(MarketDataAPIError):
        _core.parse_calendar_response(_resp(422))


def test_parse_instruments_response_401_raises_auth() -> None:
    with pytest.raises(MarketDataAuthError):
        _core.parse_instruments_response(_resp(401))


# ----------------------------------------------------------------------
# Single-object parser (D-07) — calendar/config
# ----------------------------------------------------------------------


def test_parse_calendar_config_response_empty_body_tolerant_default() -> None:
    # D-07: empty body → CalendarConfig.from_api(None), never a raise.
    empty_resp = httpx.Response(200, content=b"", request=_DUMMY_REQUEST)
    result = _core.parse_calendar_config_response(empty_resp)
    assert result == CalendarConfig.from_api(None)
    assert isinstance(result, CalendarConfig)


def test_parse_calendar_config_response_returns_single_object() -> None:
    body: dict[str, Any] = {
        "open": "11:00",
        "close": "17:00",
        "timezone": "America/Argentina/Buenos_Aires",
        "warnings": [],
        "updated_at": None,
    }
    result = _core.parse_calendar_config_response(_resp(200, json_body=body))
    assert isinstance(result, CalendarConfig)
    assert not isinstance(result, list)
    assert result.timezone == "America/Argentina/Buenos_Aires"
    assert result.open == "11:00"
    assert result.updated_at is None


def test_parse_calendar_config_response_401_raises_auth() -> None:
    with pytest.raises(MarketDataAuthError):
        _core.parse_calendar_config_response(_resp(401))
