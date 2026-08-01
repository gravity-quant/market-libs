"""Tolerance tests for the reference-data ``SafeModel`` dataclasses (Plan 22-01).

Pins the D-04/D-05 behaviors for the five reference models
(``Instrument``, ``Segment``, ``Symbol``, ``CalendarDay``, ``CalendarConfig``):

- ``from_api({})`` returns an instance with typed-zero defaults (``str -> ""``,
  ``bool -> False``, ``list -> []``) and never raises.
- ``from_api(None)`` does not raise and returns a fully-defaulted instance
  (the D-07 empty-body fallback for ``CalendarConfig``).
- Extra payload keys are ignored; legitimate falsy values (``active=False``)
  are preserved.
- NONE of the reference models carry a client-stamped ``received_at`` (D-05) —
  unlike ``MarketDataSnapshot``, they are plain ``SafeModel`` subclasses built
  via the INHERITED ``from_api`` (no override, no stamp).
"""

from __future__ import annotations

import pytest

from market_data_client.models import (
    CalendarConfig,
    CalendarDay,
    Instrument,
    SafeModel,
    Segment,
    Symbol,
)

_ALL_MODELS: list[type[SafeModel]] = [
    Instrument,
    Segment,
    Symbol,
    CalendarDay,
    CalendarConfig,
]


def test_instrument_from_api_empty_dict_typed_zero_defaults() -> None:
    inst = Instrument.from_api({})
    assert inst.symbol == ""
    assert inst.marketId == ""
    assert inst.segment == ""
    assert inst.instrumentType == ""
    assert inst.expired is False


def test_segment_from_api_none_does_not_raise() -> None:
    seg = Segment.from_api(None)
    assert seg.marketSegmentId == ""
    assert seg.marketId == ""
    assert seg.description == ""


def test_symbol_from_api_extra_keys_ignored_and_false_preserved() -> None:
    sym = Symbol.from_api({"active": False, "extraKey": 1})
    assert sym.active is False
    assert not hasattr(sym, "extraKey")


def test_calendar_day_from_api_partial_fills_typed_zeros() -> None:
    # D-12: the wire row is the HolidayIn shape — `day`, not `date`.
    day = CalendarDay.from_api({"day": "2026-07-30"})
    assert day.day == "2026-07-30"
    assert day.closed is False
    assert day.description == ""
    assert day.open_time is None
    assert day.close_time is None


def test_calendar_day_from_api_populated_wire_row() -> None:
    # D-12: shape copied from the committed get-calendar.json baseline —
    # a closed holiday sends both hour fields as wire `null`.
    day = CalendarDay.from_api(
        {
            "day": "2099-12-29",
            "closed": True,
            "open_time": None,
            "close_time": None,
            "description": "GSD phase27 probe",
        }
    )
    assert day.day == "2099-12-29"
    assert day.closed is True
    assert day.description == "GSD phase27 probe"
    assert day.open_time is None
    assert day.close_time is None


def test_calendar_day_from_api_session_hours_populate_str_fields() -> None:
    # An open day with custom session hours carries both times as strings.
    day = CalendarDay.from_api(
        {"day": "2026-07-30", "closed": False, "open_time": "11:00", "close_time": "17:00"}
    )
    assert day.closed is False
    assert day.open_time == "11:00"
    assert day.close_time == "17:00"


def test_calendar_day_from_api_none_and_non_dict_return_defaults() -> None:
    # SafeModel tolerance: neither a None nor a scalar payload may raise.
    for payload in (None, "not-a-dict"):
        day = CalendarDay.from_api(payload)
        assert day.day == ""
        assert day.closed is False
        assert day.description == ""
        assert day.open_time is None
        assert day.close_time is None


def test_calendar_day_from_api_extra_keys_ignored() -> None:
    day = CalendarDay.from_api({"day": "2026-07-30", "extraKey": 1})
    assert day.day == "2026-07-30"
    assert not hasattr(day, "extraKey")


def test_calendar_config_from_api_none_returns_defaulted_instance() -> None:
    # D-07: an empty/None body collapses to a tolerant default, never a raise.
    cfg = CalendarConfig.from_api(None)
    assert cfg.timezone == ""
    assert cfg.open == ""
    assert cfg.enabled is False
    assert cfg.pre_open_minutes == 0
    assert cfg.warnings == []
    assert cfg.updated_at is None


def test_calendar_config_from_api_populated() -> None:
    # Mirrors get-calendar-config.json: the full reconciled wire shape parses,
    # including the wire null updated_at -> None.
    cfg = CalendarConfig.from_api(
        {
            "open": "11:00",
            "close": "17:00",
            "enabled": True,
            "editable": False,
            "env_bypass": False,
            "pre_open_minutes": 10,
            "source": "db",
            "timezone": "America/Argentina/Buenos_Aires",
            "updated_by": "sys",
            "warnings": [],
            "updated_at": None,
        }
    )
    assert cfg.open == "11:00"
    assert cfg.close == "17:00"
    assert cfg.enabled is True
    assert cfg.editable is False
    assert cfg.env_bypass is False
    assert cfg.pre_open_minutes == 10
    assert cfg.source == "db"
    assert cfg.timezone == "America/Argentina/Buenos_Aires"
    assert cfg.updated_by == "sys"
    assert cfg.warnings == []
    assert cfg.updated_at is None


@pytest.mark.parametrize("model", _ALL_MODELS)
def test_reference_models_have_no_received_at(model: type[SafeModel]) -> None:
    # D-05: reference-data models are unstamped — no client-side received_at.
    instance = model.from_api({})
    assert not hasattr(instance, "received_at")
