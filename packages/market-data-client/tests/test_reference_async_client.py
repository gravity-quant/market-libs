"""End-to-end async reference-read serialization — mirrors the sync suite (D-09).

Async twin of ``test_reference_client.py``: every sync test is reproduced as its
``async`` counterpart awaiting the async shims on the default ``AsyncClient`` to
prove full sync/async parity (D-08). Same assertions: Bearer injection,
httpx-native bool encoding, falsy preservation (``offset=0`` / ``active=False``),
``None`` dropped, and the single-object calendar/config shape.
"""

from __future__ import annotations

from pytest_httpx import HTTPXMock

from typing import Any

from market_data_client import CalendarConfig, CalendarDay, Instrument, Segment, Symbol, aio

# Async twin of ``_CALENDAR_ENVELOPE`` in ``test_reference_client.py`` — the real
# ``GET /calendar`` body whose rows live under ``days`` (D-12).
_CALENDAR_ENVELOPE: dict[str, Any] = {
    "config": {"open": "11:00", "close": "17:00"},
    "coverage": {"current_year_covered": True, "years": [2026]},
    "days": [
        {
            "day": "2026-01-02",
            "closed": True,
            "open_time": None,
            "close_time": None,
            "description": "Ano Nuevo",
        }
    ],
    "market": {"is_open": False, "state": "CLOSED"},
}


async def test_async_get_instruments_sends_bearer_and_encodes_params(httpx_mock: HTTPXMock) -> None:
    """Async ``get_instruments`` injects the Bearer, encodes bools, preserves ``offset=0``."""
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

    result = await aio._get_default().get_instruments(
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


async def test_async_get_segments_sends_bearer_no_params(httpx_mock: HTTPXMock) -> None:
    """Async ``get_segments`` dispatches ``GET /instruments/segments`` with no params."""
    httpx_mock.add_response(
        method="GET",
        json=[{"marketSegmentId": "DDF", "marketId": "ROFX", "description": "Dolar"}],
    )

    result = await aio._get_default().get_segments()

    assert len(result) == 1
    assert isinstance(result[0], Segment)
    assert result[0].marketSegmentId == "DDF"
    req = httpx_mock.get_requests()[0]
    assert req.headers["Authorization"] == "Bearer test-token"
    assert req.url.path == "/api/instruments/segments"
    assert not req.url.params


async def test_async_get_symbols_sends_bearer_and_preserves_false(httpx_mock: HTTPXMock) -> None:
    """Async ``get_symbols`` preserves a falsy ``active=False`` in the query (D-03)."""
    httpx_mock.add_response(
        method="GET",
        json=[{"symbol": "GGAL", "marketId": "ROFX", "active": False}],
    )

    result = await aio._get_default().get_symbols(active=False, prefix="GG", market_id=None)

    assert len(result) == 1
    assert isinstance(result[0], Symbol)
    assert result[0].symbol == "GGAL"
    req = httpx_mock.get_requests()[0]
    assert req.headers["Authorization"] == "Bearer test-token"
    assert req.url.path == "/api/symbols"
    assert req.url.params.get("active") == "false"
    assert req.url.params.get("prefix") == "GG"
    assert "market_id" not in req.url.params


async def test_async_get_calendar_sends_bearer_and_year(httpx_mock: HTTPXMock) -> None:
    """Async ``get_calendar`` encodes ``year`` and dispatches ``GET /calendar``."""
    httpx_mock.add_response(method="GET", json=_CALENDAR_ENVELOPE)

    result = await aio._get_default().get_calendar(year=2026)

    assert len(result) == 1
    assert isinstance(result[0], CalendarDay)
    assert result[0].day == "2026-01-02"
    req = httpx_mock.get_requests()[0]
    assert req.headers["Authorization"] == "Bearer test-token"
    assert req.url.path == "/api/calendar"
    assert req.url.params.get("year") == "2026"


async def test_async_get_calendar_unwraps_days_envelope(httpx_mock: HTTPXMock) -> None:
    """Async ``get_calendar`` returns populated rows from the develop envelope (D-12)."""
    httpx_mock.add_response(method="GET", json=_CALENDAR_ENVELOPE)

    result = await aio._get_default().get_calendar()

    assert [row.day for row in result] == ["2026-01-02"]
    assert result[0].closed is True
    assert result[0].description == "Ano Nuevo"
    assert result[0].open_time is None
    assert result[0].close_time is None
    assert "year" not in httpx_mock.get_requests()[0].url.params


async def test_async_get_calendar_config_returns_single_object(httpx_mock: HTTPXMock) -> None:
    """Async ``get_calendar_config`` returns a single ``CalendarConfig`` (D-07), not a list."""
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

    result = await aio._get_default().get_calendar_config()

    assert isinstance(result, CalendarConfig)
    assert result.timezone == "America/Argentina/Buenos_Aires"
    assert result.open == "11:00"
    assert result.warnings == []
    assert result.updated_at is None
    req = httpx_mock.get_requests()[0]
    assert req.headers["Authorization"] == "Bearer test-token"
    assert req.url.path == "/api/calendar/config"
