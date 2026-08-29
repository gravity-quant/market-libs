"""Tests for the tolerant ``market_data_client.models`` layer (Plan 21-01).

Pins the D-01/D-04/D-05 behaviors:

- ``MarketDataSnapshot.from_api`` tolerates ``{}`` / ``None`` / extra-key payloads
  without raising, substituting typed zero-defaults and ``entries == []``.
- ``received_at`` is a CLIENT-STAMPED field injected as a keyword; it must NOT be
  coerced from the payload — a decoy ``"received_at"`` payload key is ignored and
  the injected kwarg wins (D-01, the highest-risk fidelity point of the phase).
- ``entries`` deserializes as a tolerant ``list[str]`` of entry-type codes matching
  the real develop wire (LIVE-MD-01); the reconciled ``market_id``/``active``/
  ``market_data``/``staleness_seconds``/``note`` fields parse both the ``/marketdata``
  item shape and the ``/marketdata/latest`` no-data shape without raising.
- ``LatestRequest(...).to_dict()`` drops ``None``-valued optionals and keeps
  supplied values (D-05).

Phase 36 (NOBJ-MD-01 / NOBJ-MD-02) revokes the Phase 33 widening on the two
CHAIN LINKS: ``entries`` is ``list[str]`` again and ``market_data`` is the typed
Null Object ``MarketDataEntries``, so the assertions below read ``== []`` and a
chained attribute where they read ``is None`` and a subscript. The two LEAVES,
``staleness_seconds`` and ``note``, keep their ``| None`` and their assertions
are untouched. ``LatestRequest.entries`` follows the link (D-06): it defaults to
``[]`` and ``to_dict`` omits the key on an EMPTY list, not merely on ``None``.
"""

from __future__ import annotations

import dataclasses
from typing import Any, cast

import pytest

from market_data_client import _decode
from market_data_client import models as models_module
from market_data_client.exceptions import MarketDataError
from market_data_client.models import (
    HolidayIn,
    HolidaysIn,
    LatestRequest,
    MarketDataEntries,
    MarketDataSnapshot,
    MarketHoursIn,
    NewSymbol,
    NewSymbols,
    SafeModel,
    SymbolPatch,
)


def test_from_api_empty_dict_typed_zero_defaults() -> None:
    snap = MarketDataSnapshot.from_api({})
    assert snap.symbol == ""
    assert snap.market_id == ""
    assert snap.active is False
    assert snap.note is None
    # Phase 36 (D-04) REVOKES the Phase 33 widening on this link: ``entries`` is
    # ``list[str]`` again, so an absent key collapses to ``[]`` and the typed-zero
    # property this test exists for applies to it once more. The revocation is by
    # field ROLE — the two leaves (``staleness_seconds``, ``note``) keep ``| None``.
    assert snap.entries == []


def test_from_api_none_does_not_raise() -> None:
    snap = MarketDataSnapshot.from_api(None)
    # Phase 36 (D-04): the Phase 33 widening is revoked on this link — ``entries``
    # is ``list[str]`` again and never holds ``None``.
    assert snap.entries == []
    assert snap.received_at == 0.0


def test_from_api_extra_keys_ignored() -> None:
    snap = MarketDataSnapshot.from_api(
        {"symbol": "GGAL", "unknown_key": 123, "another": {"nested": True}}
    )
    assert snap.symbol == "GGAL"
    # Phase 36 (D-04): the Phase 33 widening is revoked on this link.
    assert snap.entries == []


def test_received_at_injected_wins_over_decoy_payload_key() -> None:
    # D-01: the client-supplied stamp is injected as a kwarg and MUST bypass
    # _coerce; a decoy "received_at" in the payload is ignored entirely.
    snap = MarketDataSnapshot.from_api({"symbol": "GGAL", "received_at": 999.0}, received_at=1234.5)
    assert snap.received_at == 1234.5
    assert snap.received_at != 999.0
    assert snap.received_at != 0.0


def test_received_at_defaults_to_zero_without_kwarg() -> None:
    # The parser (Plan 02) always supplies received_at; absent the kwarg the
    # field defaults to 0.0 rather than pulling a payload value.
    snap = MarketDataSnapshot.from_api({"symbol": "GGAL", "received_at": 999.0})
    assert snap.received_at == 0.0


def test_entries_wrong_type_tolerated_as_empty_list() -> None:
    # entries is a list[str] of entry-type codes — a non-list, non-None wire
    # value collapses to [] (SafeModel tolerance), never a raise. This arm has
    # now survived BOTH the Phase 33 widening (which admitted ``None`` and
    # nothing else) and the Phase 36 revocation (which took ``None`` back out):
    # a ``str`` is still a divergence and still substitutes, either way.
    snap = MarketDataSnapshot.from_api({"entries": "not-a-list"}, received_at=1.0)
    assert snap.entries == []


def test_from_api_marketdata_item_parses_new_fields() -> None:
    # Mirrors get-market-data.json items[0]: the reconciled wire shape parses in
    # full, market_data passes through untouched, and the decoy received_at loses.
    snap = MarketDataSnapshot.from_api(
        {
            "symbol": "GGAL",
            "market_id": "BCBA",
            "active": True,
            "entries": ["BI", "OF"],
            "market_data": {
                "BI": [{"price": 1, "size": 2}],
                "CL": {"date": 1, "price": 3},
                "HI": 4,
                "OI": None,
            },
            "staleness_seconds": 1.5,
            "received_at": "ignored",
        },
        received_at=42.0,
    )
    assert snap.symbol == "GGAL"
    assert snap.market_id == "BCBA"
    assert snap.active is True
    assert snap.entries == ["BI", "OF"]
    # Phase 36 (NOBJ-MD-01): ``market_data`` is the typed Null Object
    # :class:`MarketDataEntries`, so the row reads by CHAINED ATTRIBUTE rather
    # than by subscript. Two consequences are asserted verbatim here:
    #   * the wire ``int`` price arrives WIDENED to ``float`` (``1`` -> ``1.0``),
    #     silently — ``walk_field``'s float arm widens before consulting
    #     ``scalar_passthrough`` (36-RESEARCH F-3);
    #   * a ``null`` entry is the EMPTY EntryValue, never ``None``, so the
    #     question "did this entry carry anything?" is a truthiness question.
    assert bool(snap.market_data) is True
    assert snap.market_data.bids[0].price == 1.0
    assert bool(snap.market_data.open_interest) is False
    assert snap.market_data.open_interest.price is None
    assert snap.staleness_seconds == 1.5
    assert snap.received_at == 42.0
    assert snap.note is None


def test_marketdata_snapshot_field_set_matches_reconciled_wire() -> None:
    # LIVE-MD-01 / F-20: the reconciliation REMOVED the model-only camelCase
    # ``marketId`` in favour of the wire's snake_case ``market_id``. The
    # from_api tests above prove the surviving fields parse, but only an exact
    # field-set assertion proves the removed one is actually gone — a stale
    # ``marketId`` would silently default to "" and keep those tests green.
    assert {f.name for f in dataclasses.fields(MarketDataSnapshot)} == {
        "symbol",
        "market_id",
        "active",
        "entries",
        "market_data",
        "staleness_seconds",
        "received_at",
        "note",
    }
    assert not hasattr(MarketDataSnapshot.from_api({}), "marketId")

    # Phase 36 (D-04): the field SET is unchanged by the revocation — what
    # changed is two ANNOTATIONS, and only an assertion on the hints can catch a
    # future re-widening. The hint cache is the walker's own view of the class,
    # so this reads exactly what the decoder reads.
    hints = _decode.hints_for(cast(Any, MarketDataSnapshot))
    assert hints["entries"] == list[str]
    assert hints["market_data"] is MarketDataEntries
    # The two LEAVES keep their ``| None`` — the revocation is by field role.
    assert hints["staleness_seconds"] == (float | None)
    assert hints["note"] == (str | None)


def test_from_api_latest_nodata_item() -> None:
    # Mirrors get-latest.json: a /marketdata/latest no-data row collapses the null
    # fields tolerantly while note carries the message and received_at stays injected.
    snap = MarketDataSnapshot.from_api(
        {
            "symbol": "GGAL",
            "note": "no data",
            "active": None,
            "market_data": None,
            "market_id": None,
            "received_at": None,
            "staleness_seconds": None,
        },
        received_at=7.0,
    )
    assert snap.symbol == "GGAL"
    assert snap.note == "no data"
    assert snap.active is False
    # Phase 33 SC-2: this row is the REASON the three fields widened. The 33-05
    # live run measured all three as ``missing`` divergences, so the null was
    # ruled the legitimate shape and the annotation over-declared.
    #
    # Phase 36 (D-04) revokes that widening BY FIELD ROLE. ``market_data`` and
    # ``entries`` are CHAIN LINKS and go back to required: a Null Object never
    # needs ``None``, and the NOBJ-02 policy (Phase 35) collapses their null to
    # the empty instance / ``[]`` with NO divergence — so the loud shape the
    # widening was fixing cannot come back. ``staleness_seconds`` is a LEAF and
    # keeps its ``| None`` untouched.
    assert bool(snap.market_data) is False
    assert snap.market_data == MarketDataEntries.empty()
    assert snap.market_data.last.price is None
    assert snap.staleness_seconds is None
    assert snap.entries == []
    # ``market_id`` stays non-Optional and still collapses to its typed zero.
    assert snap.market_id == ""
    assert snap.received_at == 7.0


def test_latest_request_to_dict_drops_none_optionals() -> None:
    req = LatestRequest(symbols=["GGAL", "YPFD"])
    assert req.to_dict() == {"symbols": ["GGAL", "YPFD"]}


def test_latest_request_to_dict_keeps_supplied_optionals() -> None:
    req = LatestRequest(symbols=["GGAL"], marketId="BCBA", entries=["BID", "OFFER"])
    assert req.to_dict() == {
        "symbols": ["GGAL"],
        "marketId": "BCBA",
        "entries": ["BID", "OFFER"],
    }


def test_latest_request_to_dict_omits_an_explicitly_empty_entries_list() -> None:
    # Phase 36 (D-06): ``entries`` is ``list[str]`` defaulting to ``[]`` now, so
    # the ``is not None`` guard would have started emitting a literal
    # ``{"entries": []}`` on EVERY request. The guard tests truthiness instead:
    # the wire semantics "key absent = every entry type" is preserved, and there
    # is no evidence in this repo that the server distinguishes an explicit
    # empty list from absence. This is the boundary that pins the distinction.
    assert LatestRequest(symbols=["GGAL"], entries=[]).to_dict() == {"symbols": ["GGAL"]}


def test_the_mapping_machinery_left_the_module_without_taking_anything_else() -> None:
    """SC-5 / D-05: the four mapping helpers are gone — asserted NON-VACUOUSLY.

    ``not hasattr(models, "_mapping_value")`` on its own is a vacuous green: it
    would pass just as happily against an empty module, against a typo'd import,
    or against a module that failed to define anything at all. Following the
    33-07 criterio-4 precedent — a zero floor is declared by STRUCTURAL PROPERTY,
    never by a ``>= 0`` — the absence is paired here with three positive
    assertions that only a live, complete ``models`` can satisfy:

    1. ``MarketDataSnapshot.from_api`` still stamps the client-side
       ``received_at`` over a decoy payload key. That injection sits one line
       below the call site this plan deleted and is the single easiest thing in
       the phase to destroy by accident (36-RESEARCH Pitfall 5).
    2. ``MarketDataEntries`` declares exactly its ten-key roster (D-02).
    3. The ``SafeModel`` roster reachable by introspection is exactly nineteen —
       the sixteen measured pre-phase plus the three this plan adds.
    """
    machinery = ("_mapping_value", "_apply_mapping_policy", "_is_mapping", "_strip_optional")
    assert [name for name in machinery if hasattr(models_module, name)] == []

    # (1) the adjacent survivor
    assert (
        MarketDataSnapshot.from_api({"received_at": "decoy"}, received_at=42.0).received_at == 42.0
    )

    # (2) the container roster
    assert {f.name for f in dataclasses.fields(MarketDataEntries)} == {
        "BI",
        "CL",
        "HI",
        "LA",
        "LO",
        "OF",
        "OI",
        "OP",
        "SE",
        "TV",
    }

    # (3) the module still ships its whole model roster
    roster = {
        name
        for name, obj in vars(models_module).items()
        if isinstance(obj, type)
        and dataclasses.is_dataclass(obj)
        and issubclass(obj, SafeModel)
        and obj.__module__ == models_module.__name__
    }
    assert len(roster) == 19, sorted(roster)
    assert {"BookLevel", "EntryValue", "MarketDataEntries"} <= roster


# ----------------------------------------------------------------------
# Serialize-OUT request models (Plan 25-02, MUT-MD-01): NewSymbol, NewSymbols,
# SymbolPatch. NOT SafeModel subclasses — they serialize OUT via to_dict().
# ----------------------------------------------------------------------


def test_new_symbol_to_dict_defaults_market_id_rofx() -> None:
    """market_id defaults to "ROFX" and is ALWAYS sent explicitly (D-10)."""
    out = NewSymbol("DLR/DIC26").to_dict()
    assert out == {"symbol": "DLR/DIC26", "market_id": "ROFX"}


def test_new_symbol_to_dict_uses_snake_case_market_id_wire_key() -> None:
    """Wire key is snake_case ``market_id`` per source-plan schema (Pitfall 3 / A2),
    intentionally different from LatestRequest's camelCase ``marketId``."""
    out = NewSymbol("DLR/DIC26").to_dict()
    assert "market_id" in out
    assert "marketId" not in out


def test_new_symbol_to_dict_explicit_market_id() -> None:
    out = NewSymbol("GGAL", market_id="ROFX").to_dict()
    assert out == {"symbol": "GGAL", "market_id": "ROFX"}


def test_new_symbols_to_dict_wraps_each_symbol() -> None:
    out = NewSymbols([NewSymbol("A"), NewSymbol("B")]).to_dict()
    assert out == {
        "symbols": [
            {"symbol": "A", "market_id": "ROFX"},
            {"symbol": "B", "market_id": "ROFX"},
        ]
    }


def test_symbol_patch_to_dict_active_false() -> None:
    assert SymbolPatch(active=False).to_dict() == {"active": False}


def test_symbol_patch_to_dict_active_true() -> None:
    assert SymbolPatch(active=True).to_dict() == {"active": True}


def test_new_symbols_empty_raises_value_error() -> None:
    """Lower-bound guard: an empty batch raises a plain ValueError (NOT a
    MarketData* error) before any dispatch (D-11)."""
    with pytest.raises(ValueError, match="1-500"):
        NewSymbols([])


def test_new_symbols_over_500_raises_value_error() -> None:
    """Upper-bound guard: 501 symbols raises a plain ValueError before dispatch."""
    with pytest.raises(ValueError, match="1-500"):
        NewSymbols([NewSymbol(f"S{i}") for i in range(501)])


def test_new_symbols_boundary_1_and_500_construct() -> None:
    """Exactly 1 and exactly 500 symbols construct successfully."""
    one = NewSymbols([NewSymbol("ONLY")])
    assert len(one.symbols) == 1
    full = NewSymbols([NewSymbol(f"S{i}") for i in range(500)])
    assert len(full.symbols) == 500


# ----------------------------------------------------------------------
# Calendar write request models (Plan 26-01, MUT-MD-02): MarketHoursIn,
# HolidayIn, HolidaysIn. NOT SafeModel subclasses — they serialize OUT via
# to_dict(), routed through ``_params.drop_none`` (D-08 / D-11).
# ----------------------------------------------------------------------

_TZ = "America/Argentina/Buenos_Aires"


def test_market_hours_in_to_dict_openapi_defaults_verbatim() -> None:
    """All 7 keys emitted with the live-OpenAPI defaults; confirm is False (D-10)."""
    out = MarketHoursIn("10:00", "17:00", _TZ).to_dict()
    assert out == {
        "open_time": "10:00",
        "close_time": "17:00",
        "timezone": _TZ,
        "pre_open_minutes": 10,
        "enabled": True,
        "updated_by": "",
        "confirm": False,
    }


def test_market_hours_in_confirm_opt_in_is_true() -> None:
    """``confirm`` is a model field the consumer must opt into on purpose (D-09)."""
    assert MarketHoursIn("10:00", "17:00", _TZ, confirm=True).to_dict()["confirm"] is True


def test_market_hours_in_to_dict_keeps_falsy_non_none_values() -> None:
    """drop_none preserves falsy-but-not-None: pre_open_minutes=0 / enabled=False."""
    out = MarketHoursIn(
        "10:00", "17:00", "TZ", pre_open_minutes=0, enabled=False, updated_by="ops"
    ).to_dict()
    assert out["pre_open_minutes"] == 0
    assert out["enabled"] is False
    assert out["updated_by"] == "ops"


def test_holiday_in_to_dict_drops_none_hours() -> None:
    """open_time/close_time DISAPPEAR when None; closed=True and description="" stay (D-11)."""
    out = HolidayIn("2026-12-25").to_dict()
    assert out == {"day": "2026-12-25", "closed": True, "description": ""}
    assert "open_time" not in out
    assert "close_time" not in out


def test_holiday_in_to_dict_custom_hours_all_five_keys() -> None:
    out = HolidayIn(
        "2026-12-24",
        closed=False,
        open_time="10:00",
        close_time="13:00",
        description="Nochebuena",
    ).to_dict()
    assert out == {
        "day": "2026-12-24",
        "closed": False,
        "open_time": "10:00",
        "close_time": "13:00",
        "description": "Nochebuena",
    }


def test_calendar_write_models_are_not_safe_models() -> None:
    """D-08: these serialize OUT — they must NOT inherit SafeModel nor expose from_api."""
    assert not issubclass(MarketHoursIn, SafeModel)
    assert not issubclass(HolidayIn, SafeModel)
    assert not hasattr(MarketHoursIn, "from_api")
    assert not hasattr(HolidayIn, "from_api")


def test_market_hours_in_is_frozen() -> None:
    hours = MarketHoursIn("10:00", "17:00", _TZ)
    with pytest.raises(dataclasses.FrozenInstanceError):
        hours.open_time = "11:00"  # type: ignore[misc]


def test_holiday_in_is_frozen() -> None:
    holiday = HolidayIn("2026-12-25")
    with pytest.raises(dataclasses.FrozenInstanceError):
        holiday.day = "2026-12-26"  # type: ignore[misc]


def test_holidays_in_to_dict_wraps_each_day() -> None:
    """Pure wrapper: ``{"days": [each element's to_dict()]}`` — no drop_none (D-11)."""
    out = HolidaysIn([HolidayIn("2026-12-25")]).to_dict()
    assert out == {"days": [{"day": "2026-12-25", "closed": True, "description": ""}]}


def test_holidays_in_to_dict_nests_per_day_drop_none() -> None:
    """Each nested to_dict() keeps its own drop_none effect."""
    out = HolidaysIn(
        [
            HolidayIn("2026-12-25"),
            HolidayIn("2026-12-24", closed=False, open_time="10:00"),
        ]
    ).to_dict()
    assert len(out["days"]) == 2
    second = out["days"][1]
    assert second["open_time"] == "10:00"
    assert "close_time" not in second


def test_holidays_in_empty_raises_value_error() -> None:
    """Lower-bound guard: an empty batch raises before any dispatch (D-12)."""
    with pytest.raises(ValueError, match="1-500"):
        HolidaysIn([])


def test_holidays_in_over_500_raises_value_error() -> None:
    """Upper-bound guard: 501 days raises before any dispatch (D-12)."""
    with pytest.raises(ValueError, match="1-500"):
        HolidaysIn([HolidayIn(f"2026-01-{i:02d}") for i in range(501)])


def test_holidays_in_boundary_1_and_500_construct() -> None:
    """Exactly 1 and exactly 500 days construct successfully."""
    one = HolidaysIn([HolidayIn("2026-12-25")])
    assert len(one.days) == 1
    full = HolidaysIn([HolidayIn(f"2026-01-{i:02d}") for i in range(500)])
    assert len(full.days) == 500


def test_holidays_in_bound_error_is_plain_value_error() -> None:
    """The bound error is a BARE ValueError — the MarketData* hierarchy stays
    reserved for server contract errors (D-12)."""
    with pytest.raises(ValueError) as excinfo:  # noqa: PT011
        HolidaysIn([])
    assert type(excinfo.value) is ValueError
    assert not isinstance(excinfo.value, MarketDataError)


def test_calendar_write_models_exported_in_models_all() -> None:
    assert {"HolidayIn", "HolidaysIn", "MarketHoursIn"} <= set(models_module.__all__)
    assert list(models_module.__all__) == sorted(models_module.__all__)
