"""End-to-end sync reference-read serialization — Bearer + param encoding (D-09).

Mirrors ``test_get_market_data_sends_bearer_and_encodes_params`` for the five
reference endpoints (instruments, segments, symbols, calendar, calendar/config).
The conftest seeds a non-expiring token so no auth grant is issued; the mocked
``httpx_mock`` transport asserts (a) the request path, (b) ``Authorization:
Bearer`` injection, (c) httpx-native bool encoding (``True → "true"`` /
``False → "false"``) with falsy values PRESERVED (D-03: ``offset=0`` /
``active=False`` not dropped), and (d) ``None`` filters absent from the query.
"""

from __future__ import annotations

from pytest_httpx import HTTPXMock

import market_data_client
from market_data_client import CalendarConfig, CalendarDay, Instrument, Segment, Symbol


def test_get_instruments_sends_bearer_and_encodes_params(httpx_mock: HTTPXMock) -> None:
    """``get_instruments`` injects the Bearer, encodes bools, preserves ``offset=0``."""
    httpx_mock.add_response(
        method="GET",
        json=[
            {
                "symbol": "GGAL",
                "marketId": "ROFX",
                "segment": "DDF",
                "instrumentType": "E",
                "expired": False,
            }
        ],
    )

    result = market_data_client.client._get_default().get_instruments(
        q="GGA",
        include_expired=True,
        only_outright=False,
        offset=0,
        subscribed=None,
    )

    assert len(result) == 1
    assert isinstance(result[0], Instrument)
    assert result[0].symbol == "GGAL"
    req = httpx_mock.get_requests()[0]
    assert req.headers["Authorization"] == "Bearer test-token"
    assert req.url.path == "/api/instruments"
    assert req.url.params.get("q") == "GGA"
    assert req.url.params.get("include_expired") == "true"
    assert req.url.params.get("only_outright") == "false"
    assert req.url.params.get("offset") == "0"
    assert "subscribed" not in req.url.params


def test_get_segments_sends_bearer_no_params(httpx_mock: HTTPXMock) -> None:
    """``get_segments`` dispatches an authenticated ``GET /instruments/segments`` with no params."""
    httpx_mock.add_response(
        method="GET",
        json=[{"marketSegmentId": "DDF", "marketId": "ROFX", "description": "Dolar"}],
    )

    result = market_data_client.client._get_default().get_segments()

    assert len(result) == 1
    assert isinstance(result[0], Segment)
    assert result[0].marketSegmentId == "DDF"
    req = httpx_mock.get_requests()[0]
    assert req.headers["Authorization"] == "Bearer test-token"
    assert req.url.path == "/api/instruments/segments"
    assert not req.url.params


def test_get_symbols_sends_bearer_and_preserves_false(httpx_mock: HTTPXMock) -> None:
    """``get_symbols`` preserves a falsy ``active=False`` in the query string (D-03)."""
    httpx_mock.add_response(
        method="GET",
        json=[{"symbol": "GGAL", "marketId": "ROFX", "active": False}],
    )

    result = market_data_client.client._get_default().get_symbols(
        active=False, prefix="GG", market_id=None
    )

    assert len(result) == 1
    assert isinstance(result[0], Symbol)
    assert result[0].symbol == "GGAL"
    req = httpx_mock.get_requests()[0]
    assert req.headers["Authorization"] == "Bearer test-token"
    assert req.url.path == "/api/symbols"
    assert req.url.params.get("active") == "false"
    assert req.url.params.get("prefix") == "GG"
    assert "market_id" not in req.url.params


def test_get_calendar_sends_bearer_and_year(httpx_mock: HTTPXMock) -> None:
    """``get_calendar`` encodes the ``year`` filter and dispatches ``GET /calendar``."""
    httpx_mock.add_response(
        method="GET",
        json=[{"date": "2026-01-02", "marketId": "ROFX", "isBusinessDay": True}],
    )

    result = market_data_client.client._get_default().get_calendar(year=2026)

    assert len(result) == 1
    assert isinstance(result[0], CalendarDay)
    assert result[0].date == "2026-01-02"
    req = httpx_mock.get_requests()[0]
    assert req.headers["Authorization"] == "Bearer test-token"
    assert req.url.path == "/api/calendar"
    assert req.url.params.get("year") == "2026"


def test_get_calendar_config_returns_single_object(httpx_mock: HTTPXMock) -> None:
    """``get_calendar_config`` returns a single ``CalendarConfig`` (D-07), not a list."""
    httpx_mock.add_response(
        method="GET",
        json={
            "open": "11:00",
            "close": "17:00",
            "timezone": "America/Argentina/Buenos_Aires",
            "warnings": [],
            "updated_at": None,
        },
    )

    result = market_data_client.client._get_default().get_calendar_config()

    assert isinstance(result, CalendarConfig)
    assert result.timezone == "America/Argentina/Buenos_Aires"
    assert result.open == "11:00"
    assert result.warnings == []
    assert result.updated_at is None
    req = httpx_mock.get_requests()[0]
    assert req.headers["Authorization"] == "Bearer test-token"
    assert req.url.path == "/api/calendar/config"
