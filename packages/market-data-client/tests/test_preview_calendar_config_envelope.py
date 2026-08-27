"""SC-1 / S-2 regression — the preview envelope is NOT a ``CalendarConfig``.

``29-SIZING.md`` predicted this one field-for-field: *"nine declared
``CalendarConfig`` fields ... absent ... while three real preview fields
(``valid``, ``requires_confirmation``, ``market_after``) are discarded"*. The
Phase 33 live run (33-05, gate de mutaciones ABIERTO) returned **exactly those
12 divergences** — ``F-124``..``F-132`` / ``F-155``..``F-163`` (nine ``missing``)
plus ``F-121``..``F-123`` / ``F-152``..``F-154`` (three ``extra``), on both
surfaces.

``POST /calendar/config/preview`` is a compute-only dry run: it answers *"would
this window be valid, and does it need a second opinion"*, not *"what is the
configuration"*. Reusing ``parse_calendar_config_response`` therefore threw away
all three answers and manufactured a ``CalendarConfig`` whose every field was a
typed zero — the exact silent substitution this milestone exists to remove.

Operator disposition (33-07 Task 1, ``fix-shape-now``): the envelope gets its own
model and the declared return type changes. That is SOURCE-BREAKING for
``market-data-client`` and moves it into Phase 34's bump set at **0.4.0 →
0.5.0**.

Shapes below come from the committed, PII-free baselines
``.planning/verification/schemas/market-data-client/preview-calendar-config-{sync,async}-response.json``
— SHAPE only, values synthesised (T-33-42). Both surfaces are exercised: the
parser lives in ``_core.py``, which ``client.py`` and ``aio.py`` both dispatch
through (C-3).

Each test asserts the VALUE first (``to_dict()`` against the wire body) and the
type second, so the fail-first run reports the manufactured typed zeros rather
than an ``AttributeError`` about a class that does not exist yet.
"""

from __future__ import annotations

from typing import Any

from pytest_httpx import HTTPXMock

import market_data_client
from market_data_client import MarketHoursIn, aio, models

_PREVIEW_ENVELOPE: dict[str, Any] = {
    "market_after": {
        "is_open": False,
        "local_time": "2099-01-01T21:00:00-03:00",
        "next_transition": "2099-01-02T11:00:00-03:00",
        "reason": "outside session",
        "session_close": "17:00",
        "session_open": "11:00",
        "state": "CLOSED",
    },
    "requires_confirmation": True,
    "valid": True,
    "warnings": ["ventana estrecha"],
}

_HOURS = MarketHoursIn(
    open_time="11:00", close_time="17:00", timezone="America/Argentina/Buenos_Aires"
)
_HOURS_WIRE = (
    b'{"open_time":"11:00","close_time":"17:00",'
    b'"timezone":"America/Argentina/Buenos_Aires",'
    b'"pre_open_minutes":10,"enabled":true,"updated_by":"","confirm":false}'
)


def _armed_sync() -> Any:
    """A default sync client with the mutation gate open (preview is gated)."""
    market_data_client.configure(mutating_allowed=True, expected_host="market-data-develop.test")
    return market_data_client.client._get_default()


def _armed_async() -> Any:
    """A default async client with the mutation gate open (preview is gated)."""
    aio.configure(mutating_allowed=True, expected_host="market-data-develop.test")
    return aio._get_default()


def test_preview_returns_the_preview_envelope(httpx_mock: HTTPXMock) -> None:
    """The three real answers survive; nothing is manufactured from a typed zero."""
    httpx_mock.add_response(method="POST", json=_PREVIEW_ENVELOPE)

    result = _armed_sync().preview_calendar_config(_HOURS)

    # Value first: before the fix this was a CalendarConfig of typed zeros.
    assert result.to_dict() == _PREVIEW_ENVELOPE
    assert isinstance(result, models.CalendarConfigPreview)
    assert result.valid is True
    assert result.requires_confirmation is True
    assert result.warnings == ["ventana estrecha"]
    assert isinstance(result.market_after, models.PreviewMarket)
    assert result.market_after.state == "CLOSED"
    assert result.market_after.is_open is False
    assert result.market_after.session_open == "11:00"


async def test_preview_returns_the_preview_envelope_async(httpx_mock: HTTPXMock) -> None:
    """Async twin of :func:`test_preview_returns_the_preview_envelope` (C-3)."""
    httpx_mock.add_response(method="POST", json=_PREVIEW_ENVELOPE)

    result = await _armed_async().preview_calendar_config(_HOURS)

    assert result.to_dict() == _PREVIEW_ENVELOPE
    assert isinstance(result, models.CalendarConfigPreview)
    assert result.valid is True
    assert result.requires_confirmation is True
    assert result.warnings == ["ventana estrecha"]
    assert isinstance(result.market_after, models.PreviewMarket)
    assert result.market_after.state == "CLOSED"
    assert result.market_after.is_open is False
    assert result.market_after.session_open == "11:00"


def test_preview_body_is_unchanged(httpx_mock: HTTPXMock) -> None:
    """RESPONSE-ONLY: the emitted request is untouched by this fix.

    ``POST /calendar/config/preview`` was published in v0.4.0. The shape change
    is on the way BACK, and this pins that claim mechanically rather than
    asserting it in prose — the same discipline ``test_v040_request_pin.py``
    applies to the two holiday mutations.
    """
    httpx_mock.add_response(method="POST", json=_PREVIEW_ENVELOPE)

    _armed_sync().preview_calendar_config(_HOURS)

    req = httpx_mock.get_requests()[0]
    assert req.method == "POST"
    assert req.url.path == "/api/calendar/config/preview"
    assert req.read() == _HOURS_WIRE


def test_preview_empty_body_stays_tolerant(httpx_mock: HTTPXMock) -> None:
    """A ``204``/empty body collapses to the all-default preview, never a raise."""
    httpx_mock.add_response(method="POST", status_code=204)

    result = _armed_sync().preview_calendar_config(_HOURS)

    assert result.to_dict() == {
        "market_after": {
            "is_open": False,
            "local_time": "",
            "next_transition": "",
            "reason": "",
            "session_close": "",
            "session_open": "",
            "state": "",
        },
        "requires_confirmation": False,
        "valid": False,
        "warnings": [],
    }
    assert isinstance(result, models.CalendarConfigPreview)


def test_get_calendar_config_still_returns_calendar_config(httpx_mock: HTTPXMock) -> None:
    """Non-regression: the READ endpoint keeps its ``CalendarConfig`` contract.

    Only ``preview`` moves. ``get_calendar_config`` / ``set_calendar_config`` /
    ``delete_calendar_config`` all keep returning ``CalendarConfig``, and their
    shared parser is untouched.
    """
    httpx_mock.add_response(
        method="GET",
        json={
            "open": "11:00",
            "close": "17:00",
            "enabled": True,
            "editable": True,
            "env_bypass": False,
            "pre_open_minutes": 15,
            "source": "db",
            "timezone": "America/Argentina/Buenos_Aires",
            "updated_by": "operator",
            "warnings": [],
            "updated_at": None,
        },
    )

    result = market_data_client.client._get_default().get_calendar_config()

    assert isinstance(result, models.CalendarConfig)
    assert result.open == "11:00"
    assert result.timezone == "America/Argentina/Buenos_Aires"
