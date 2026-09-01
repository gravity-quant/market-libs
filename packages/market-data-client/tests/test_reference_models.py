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

import dataclasses
from typing import Any

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


# ----------------------------------------------------------------------
# Instrument / Segment — reconciled against the FRESH live wire read of
# 2026-08-31 (SHAPE-01, Phase 43). Provenance: ``42-WIRE-READ.md`` section 2
# plus the two Phase 42 captures; findings F-205..F-218.
# ----------------------------------------------------------------------

# The exact row shape of ``GET /instruments`` — 50/50 measured rows carried this
# homogeneous ten-key set. Values are synthetic; only the KEY SET and the value
# TYPES come from the live read (``42-WIRE-READ.md`` section 2, F-205..F-218).
#
# The raw Phase 42 capture files are gitignored (``.gitignore:53`` — raw payloads
# may carry PII and are never committable). A test that opened one would pass on
# the executor's machine and fail in CI with ``FileNotFoundError``, so this
# fixture is hand-written: REAL key set, INVENTED values.
#
# Deliberately ABSENT: the ``marketId`` camelCase alias (the wire never sends it,
# and that absence is exactly what makes the D-04 mirror fire) and the removed
# camelCase instrument-type field.
_WIRE_INSTRUMENT_ROW: dict[str, Any] = {
    "active": None,
    "currency": "ARS",
    "days_to_maturity": 30,
    "expired": False,
    "market_id": "ROFX",
    "maturity": "2099-12-31",
    "outright": True,
    "segment": "SEG1",
    "subscribed": False,
    "symbol": "AAA1",
}

# The exact row shape of ``GET /instruments/segments`` — 4/4 measured rows.
# Values are synthetic; only the KEY SET and the value TYPES come from the live
# read (``42-WIRE-READ.md`` section 2, F-205..F-218). Same gitignored-capture
# rule as above.
_WIRE_SEGMENT_ROW: dict[str, Any] = {
    "segment": "SEG1",
    "live_instruments": 7,
}


def test_instrument_from_api_empty_dict_typed_zero_defaults() -> None:
    # Re-derived (NOT renamed) for the reconciled shape: the intent is unchanged
    # — an empty payload yields typed zeros and never raises — but it now covers
    # the six wire-only fields D-02 added and the nullable ``active`` of D-03.
    inst = Instrument.from_api({})
    assert inst.symbol == ""
    assert inst.marketId == ""
    assert inst.segment == ""
    assert inst.expired is False
    assert inst.market_id == ""
    assert inst.currency == ""
    assert inst.days_to_maturity == 0
    assert inst.maturity == ""
    assert inst.outright is False
    assert inst.subscribed is False
    # D-03: ``active`` is ``bool | None`` and the typed zero of an Optional is
    # ``None``, not ``False`` — the wire sent ``null`` on all 50 measured rows.
    assert inst.active is None


def test_segment_from_api_none_does_not_raise() -> None:
    # Re-derived (NOT renamed) for the D-06 replacement shape: the intent is
    # unchanged — a ``None`` payload yields typed zeros and never raises.
    seg = Segment.from_api(None)
    assert seg.segment == ""
    assert seg.live_instruments == 0


def test_instrument_field_set_matches_reconciled_wire() -> None:
    # D-01..D-05. ``test_instrument_from_api_populated_wire_row`` proves the six
    # added fields PARSE, but it would stay green if only some of them had been
    # added — and, worse, a silent REMOVAL of the published ``marketId`` alias
    # would also keep it green (every other assertion reads the new fields).
    # Only an exact field-set assertion proves both directions at once: the six
    # additions plus ``active`` landed AND the published alias survived (D-22 /
    # D-04 forbid the rename). The ``not hasattr`` half proves the D-05 removal:
    # a stale camelCase instrument-type field would just default to "" and keep
    # every other assertion in this file green.
    assert {f.name for f in dataclasses.fields(Instrument)} == {
        "symbol",
        "marketId",
        "segment",
        "expired",
        "market_id",
        "currency",
        "days_to_maturity",
        "maturity",
        "outright",
        "subscribed",
        "active",
    }
    assert not hasattr(Instrument.from_api({}), "instrumentType")


def test_segment_field_set_matches_reconciled_wire() -> None:
    # D-06: the declared key set and the measured wire key set were DISJOINT, so
    # ``Segment`` is replaced wholesale rather than extended. The exact set proves
    # the two real fields landed; the three ``not hasattr`` assertions prove the
    # three model-only fields are gone — each of them would otherwise default to
    # "" and keep an ``isinstance``-only test vacuously green.
    assert {f.name for f in dataclasses.fields(Segment)} == {"segment", "live_instruments"}
    seg = Segment.from_api({})
    assert not hasattr(seg, "marketSegmentId")
    assert not hasattr(seg, "marketId")
    assert not hasattr(seg, "description")


def test_instrument_market_id_alias_mirrors_wire_snake_case() -> None:
    # D-04, cloned from ``test_symbol_market_id_alias_mirrors_wire_snake_case``:
    # ``marketId`` was model-only while ``market_id`` is wire-only. The alias is
    # kept (published surface, D-22) but is no longer dead — ``from_api`` mirrors
    # the wire value into it. Before this fix a real payload left it permanently "".
    inst = Instrument.from_api(_WIRE_INSTRUMENT_ROW)
    assert inst.marketId == "ROFX"
    assert inst.marketId == inst.market_id
    assert inst.marketId != ""


def test_instrument_explicit_camel_case_payload_key_still_wins() -> None:
    # T-43-01 (Tampering). The mirror only FILLS an absent key. An older fixture
    # or hand-built dict that sends ``marketId`` explicitly keeps its own value,
    # and the snake_case value stays in its own field.
    inst = Instrument.from_api({"symbol": "AAA1", "marketId": "LEGACY", "market_id": "ROFX"})
    assert inst.marketId == "LEGACY"
    assert inst.market_id == "ROFX"


def test_instrument_from_api_populated_wire_row() -> None:
    # Every one of the ten measured keys lands on a real field — no data is
    # dropped. Before this fix six of them (``currency``, ``days_to_maturity``,
    # ``maturity``, ``outright``, ``subscribed``, ``market_id``) were silently
    # discarded on every catalogue read.
    inst = Instrument.from_api(_WIRE_INSTRUMENT_ROW)
    assert inst.symbol == "AAA1"
    assert inst.segment == "SEG1"
    assert inst.expired is False
    assert inst.market_id == "ROFX"
    assert inst.currency == "ARS"
    assert inst.days_to_maturity == 30
    assert inst.maturity == "2099-12-31"
    assert inst.outright is True
    assert inst.subscribed is False
    assert inst.active is None


def test_segment_from_api_populated_wire_row() -> None:
    # D-06: the row comes back POPULATED. Against the old declaration every
    # segment row was three empty strings, whatever the server sent.
    seg = Segment.from_api(_WIRE_SEGMENT_ROW)
    assert seg.segment == "SEG1"
    assert seg.live_instruments == 7


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


def test_calendar_config_field_set_matches_reconciled_wire() -> None:
    # LIVE-MD-01 / F-08 / F-26: the reconciliation REMOVED the model-only
    # ``businessDays`` field (it never existed on the develop wire) and added the
    # ten real ones. ``test_calendar_config_from_api_populated`` proves the added
    # fields parse, but a stale ``businessDays`` would just default to [] and keep
    # it green — only an exact field-set assertion proves the removal.
    assert {f.name for f in dataclasses.fields(CalendarConfig)} == {
        "open",
        "close",
        "enabled",
        "editable",
        "env_bypass",
        "pre_open_minutes",
        "source",
        "timezone",
        "updated_by",
        "warnings",
        "updated_at",
    }
    assert not hasattr(CalendarConfig.from_api({}), "businessDays")


@pytest.mark.parametrize("model", [m for m in _ALL_MODELS if m is not Symbol])
def test_reference_models_have_no_received_at(model: type[SafeModel]) -> None:
    # D-05: reference-data models are unstamped — no client-side received_at.
    # ``Symbol`` is parametrized OUT because it declares a ``received_at`` that is
    # a WIRE field, not a client stamp; ``test_symbol_received_at_is_a_wire_field``
    # below pins that distinction instead of waiving it.
    instance = model.from_api({})
    assert not hasattr(instance, "received_at")


# ----------------------------------------------------------------------
# Symbol — reconciled against the first populated row ever observed
# (LIVE-MUT-01, armed run 2026-08-01). F-42..F-47 / F-52..F-57.
# ----------------------------------------------------------------------

# The exact row shape of ``get-symbols-probe-prefix-sync.json``. Values are
# synthetic; only the KEY SET and the value TYPES come from the live baseline.
_WIRE_SYMBOL_ROW = {
    "active": False,
    "created_at": "2026-08-01T15:54:36.123456",
    "id": 8123,
    "market_id": "ROFX",
    "received_at": None,
    "symbol": "GSDPROBE/P27-SYNC",
    "updated_at": "2026-08-01T15:54:38.654321",
}


def test_symbol_field_set_matches_reconciled_wire() -> None:
    # F-43..F-47 / F-53..F-57 are wire-only field findings: the wire sends five
    # keys ``Symbol`` did not declare. ``test_symbol_from_api_populated_wire_row``
    # proves the added fields PARSE, but it would stay green if only some of them
    # had been added — and, worse, a silent REMOVAL of the published ``marketId``
    # alias would also keep it green (every other assertion reads the new fields).
    # Only an exact field-set assertion proves both directions at once: the five
    # additions landed AND the published alias survived (D-22 forbids the rename).
    assert {f.name for f in dataclasses.fields(Symbol)} == {
        "symbol",
        "marketId",
        "active",
        "id",
        "market_id",
        "created_at",
        "updated_at",
        "received_at",
    }


def test_symbol_from_api_populated_wire_row() -> None:
    # Every key of the live row lands on a real field — no data is dropped.
    sym = Symbol.from_api(_WIRE_SYMBOL_ROW)
    assert sym.symbol == "GSDPROBE/P27-SYNC"
    assert sym.market_id == "ROFX"
    assert sym.active is False
    assert sym.id == 8123
    assert sym.created_at == "2026-08-01T15:54:36.123456"
    assert sym.updated_at == "2026-08-01T15:54:38.654321"
    assert sym.received_at is None


def test_symbol_from_api_partial_leaves_row_id_at_typed_default() -> None:
    # A partial payload must not raise: ``id`` falls back to the typed zero, which
    # is what makes the field safe to add to a published model.
    sym = Symbol.from_api({"symbol": "GGAL"})
    assert sym.symbol == "GGAL"
    assert sym.id == 0
    assert sym.market_id == ""
    assert sym.received_at is None


def test_symbol_row_id_is_an_int_not_a_string() -> None:
    # The id feeds ``PATCH /symbols/{symbol_id}``, whose live spec types the path
    # parameter as an INTEGER. A str-typed id would have kept the client's old
    # ``symbol_id: str`` looking correct.
    sym = Symbol.from_api(_WIRE_SYMBOL_ROW)
    assert isinstance(sym.id, int)
    assert not isinstance(sym.id, bool)


def test_symbol_market_id_alias_mirrors_wire_snake_case() -> None:
    # F-42 / F-52: ``marketId`` was model-only while ``market_id`` was wire-only in
    # the SAME diff. The alias is kept (published surface, D-22) but is no longer
    # dead: ``from_api`` mirrors the wire value into it. Before this fix a real
    # payload left it permanently "".
    sym = Symbol.from_api(_WIRE_SYMBOL_ROW)
    assert sym.marketId == "ROFX"
    assert sym.marketId == sym.market_id


def test_symbol_explicit_camel_case_payload_key_still_wins() -> None:
    # The mirror only FILLS an absent key. An older fixture or hand-built dict
    # that sends ``marketId`` explicitly keeps its own value.
    sym = Symbol.from_api({"symbol": "GGAL", "marketId": "LEGACY", "market_id": "ROFX"})
    assert sym.marketId == "LEGACY"
    assert sym.market_id == "ROFX"


def test_symbol_received_at_is_a_wire_field_not_a_client_stamp() -> None:
    # Same name as ``MarketDataSnapshot.received_at``, opposite provenance: this
    # one is read off the payload by the inherited ``_coerce``, never injected by
    # the client. An absent key stays ``None`` (it is ``str | None``), and a wire
    # value is preserved verbatim rather than collapsed to a float.
    assert Symbol.from_api({}).received_at is None
    assert Symbol.from_api({"received_at": "2026-08-01T16:00:00"}).received_at == (
        "2026-08-01T16:00:00"
    )
