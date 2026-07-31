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
    day = CalendarDay.from_api({"date": "2026-07-30"})
    assert day.date == "2026-07-30"
    assert day.marketId == ""
    assert day.isBusinessDay is False


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
