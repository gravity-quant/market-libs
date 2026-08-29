"""SC-1 — the consumer chain ``snapshot.market_data.last.price``, stated as a matrix.

Phase 36 (NOBJ-MD-01 / NOBJ-MD-02) turns :attr:`MarketDataSnapshot.market_data`
from a ``dict[str, Any] | None`` passthrough into the typed Null Object
:class:`~market_data_client.models.MarketDataEntries`, and revokes the Phase 33
widening (33-07 Task 1, ``fix-shape-now``) on the two CHAIN LINKS — ``entries``
and ``market_data`` — while leaving it standing on the two LEAVES,
``staleness_seconds`` and ``note`` (D-04, source plan
``.future_plans/api-tipada-null-objects.md``).

This module is the phase goal expressed as assertions. It asserts the FOUR
payloads the vendor can actually produce, on BOTH surfaces (C-3):

1. the real ``/marketdata`` wire item, mirroring the committed baseline
   ``.planning/verification/schemas/market-data-client/get-market-data.json``;
2. ``market_data`` absent from the row entirely;
3. ``market_data`` explicitly ``null`` — the no-data row of
   ``.planning/verification/schemas/market-data-client/get-latest.json``;
4. ``market_data`` present but empty (``{}``).

Every expected value below is MEASURED in ``36-RESEARCH.md`` § "Key Measured
Findings" F-1 and F-3 — they are asserted here, not recomputed. In particular
F-3: the wire sends ``int`` for every ``price``, and ``walk_field``'s ``float``
arm widens ``int`` to ``float`` BEFORE consulting ``scalar_passthrough``, so a
wire ``10`` arrives as ``10.0`` with NO divergence record.

Every identifier in this module is synthesised. No real symbol and no real
account id appears here (C-4).
"""

from __future__ import annotations

import dataclasses
import logging
from typing import Any

import pytest
from pytest_httpx import HTTPXMock

import market_data_client
from market_data_client import (
    BookLevel,
    EntryValue,
    LatestRequest,
    MarketDataEntries,
    MarketDataSnapshot,
    aio,
)

_MESSAGE = "decode divergence"

_BASE_URL = "https://market-data-develop.test/api"
_NEVER_EXPIRES = 9_999_999_999.0


# ---------------------------------------------------------------------------
# Divergence projection helpers — module-local copies on purpose
# ---------------------------------------------------------------------------
#
# Copied from ``test_null_object.py:143-175`` / ``test_decode.py``. This monorepo
# has no shared internal package by design (DT-03), and the test-side helpers
# are kept module-local deliberately: a helper shared across modules would
# introduce exactly the coupling repo policy forbids.


def _divergences(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    """Every divergence record captured so far, in emission order."""
    return [r for r in caplog.records if r.getMessage() == _MESSAGE]


def _records(caplog: pytest.LogCaptureFixture) -> list[tuple[str, str, str]]:
    """Project the captured records onto ``(model, field_path, divergence)``."""
    return [
        (r.model, r.field_path, r.divergence)  # type: ignore[attr-defined]
        for r in _divergences(caplog)
    ]


# ---------------------------------------------------------------------------
# The four payloads (provenance in each comment)
# ---------------------------------------------------------------------------

# Row 1 — the real ``/marketdata`` item. Field set and TYPES taken from the
# committed live capture ``.../schemas/market-data-client/get-market-data.json``
# (captured 2026-07-31 against market-data-develop): every ``price`` / ``size`` /
# ``date`` arrives as a wire ``int``, ``OI`` and ``TV`` arrive as ``null``.
# Identifiers synthesised.
_WIRE_REAL: dict[str, Any] = {
    "symbol": "AAA1",
    "market_id": "ZZZ",
    "active": True,
    "entries": ["BI"],
    "market_data": {
        "BI": [{"price": 10, "size": 1}],
        "CL": {"date": 20990101, "price": 9},
        "HI": 12,
        "LA": {"date": 20990101, "price": 10, "size": 1},
        "LO": 8,
        "OF": [{"price": 11, "size": 2}],
        "OI": None,
        "OP": 9,
        "SE": {"price": 10},
        "TV": None,
    },
    "staleness_seconds": 1.5,
    "note": None,
}

# Row 2 — the ``market_data`` key is absent from the row entirely.
_MD_ABSENT: dict[str, Any] = {
    "symbol": "AAA1",
    "market_id": "ZZZ",
    "active": True,
    "entries": ["BI"],
    "staleness_seconds": None,
    "note": None,
}

# Row 3 — ``market_data: null``, the shape of the no-data row of
# ``.../schemas/market-data-client/get-latest.json`` (which also carries no
# ``entries`` value at all).
_MD_NULL: dict[str, Any] = {
    "symbol": "AAA1",
    "market_id": "ZZZ",
    "active": False,
    "entries": None,
    "market_data": None,
    "staleness_seconds": None,
    "note": "sin datos para el simbolo",
}

# Row 4 — ``market_data`` present but empty.
_MD_EMPTY: dict[str, Any] = {
    "symbol": "AAA1",
    "market_id": "ZZZ",
    "active": True,
    "entries": ["BI"],
    "market_data": {},
    "staleness_seconds": None,
    "note": None,
}

# Expected leaf values per row — RESEARCH F-1, asserted not recomputed.
_REAL_EXPECT: dict[str, Any] = {
    "last_price": 10.0,
    "bids": [BookLevel(price=10.0, size=1)],
    "offers": [BookLevel(price=11.0, size=2)],
    "settlement_price": 10.0,
    "close_price": 9.0,
    "open_interest_price": None,
}

_EMPTY_EXPECT: dict[str, Any] = {
    "last_price": None,
    "bids": [],
    "offers": [],
    "settlement_price": None,
    "close_price": None,
    "open_interest_price": None,
}

_MATRIX = [
    pytest.param(_WIRE_REAL, ["BI"], True, _REAL_EXPECT, id="wire-real"),
    pytest.param(_MD_ABSENT, ["BI"], False, _EMPTY_EXPECT, id="market-data-absent"),
    pytest.param(_MD_NULL, [], False, _EMPTY_EXPECT, id="market-data-null"),
    pytest.param(_MD_EMPTY, ["BI"], False, _EMPTY_EXPECT, id="market-data-empty-dict"),
]

_EMPTY_ROWS = [
    pytest.param(_MD_ABSENT, id="market-data-absent"),
    pytest.param(_MD_NULL, id="market-data-null"),
    pytest.param(_MD_EMPTY, id="market-data-empty-dict"),
]


def _assert_chain(
    row: MarketDataSnapshot,
    expected_entries: list[str],
    truthy: bool,
    expect: dict[str, Any],
) -> None:
    """Evaluate the WHOLE chain — every link, every leaf — and compare to F-1.

    Reading any of these attributes on a row whose ``market_data`` collapsed
    would raise ``AttributeError`` on ``None``; the fact that this function
    returns at all is half of what SC-1 asserts.
    """
    assert row.entries == expected_entries
    assert bool(row.market_data) is truthy
    assert row.market_data.last.price == expect["last_price"]
    assert row.market_data.bids == expect["bids"]
    assert row.market_data.offers == expect["offers"]
    assert row.market_data.settlement.price == expect["settlement_price"]
    assert row.market_data.close.price == expect["close_price"]
    assert row.market_data.open_interest.price == expect["open_interest_price"]


# ---------------------------------------------------------------------------
# The 4 x 2 matrix (SC-1)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("payload", "expected_entries", "truthy", "expect"), _MATRIX)
def test_chain_is_reachable_and_silent(
    payload: dict[str, Any],
    expected_entries: list[str],
    truthy: bool,
    expect: dict[str, Any],
    httpx_mock: HTTPXMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """SC-1 sync: the full chain answers a value or ``None`` and reports nothing."""
    httpx_mock.add_response(method="GET", json={"count": 1, "items": [payload]})

    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="market_data_client"):
        rows = market_data_client.client._get_default().get_market_data()

    assert len(rows) == 1
    _assert_chain(rows[0], expected_entries, truthy, expect)
    assert _records(caplog) == []


@pytest.mark.parametrize(("payload", "expected_entries", "truthy", "expect"), _MATRIX)
async def test_chain_is_reachable_and_silent_async(
    payload: dict[str, Any],
    expected_entries: list[str],
    truthy: bool,
    expect: dict[str, Any],
    httpx_mock: HTTPXMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Async twin of :func:`test_chain_is_reachable_and_silent` (C-3)."""
    httpx_mock.add_response(method="GET", json={"count": 1, "items": [payload]})

    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="market_data_client"):
        rows = await aio._get_default().get_market_data()

    assert len(rows) == 1
    _assert_chain(rows[0], expected_entries, truthy, expect)
    assert _records(caplog) == []


@pytest.mark.parametrize(("payload", "expected_entries", "truthy", "expect"), _MATRIX)
def test_chain_survives_strict_decode(
    payload: dict[str, Any],
    expected_entries: list[str],
    truthy: bool,
    expect: dict[str, Any],
    httpx_mock: HTTPXMock,
) -> None:
    """SC-1 strict sync: none of the four rows is fatal under ``strict_decode``.

    The three empty rows are LEGITIMATE vendor shapes (NOBJ-02, Phase 35): a
    ``null`` or absent value on a non-optional nested-model link collapses to
    the empty instance without emitting anything, so strict mode has nothing to
    raise on.
    """
    httpx_mock.add_response(method="GET", json={"count": 1, "items": [payload]})

    with market_data_client.Client(
        base_url=_BASE_URL,
        token="test-token",
        token_expires_at=_NEVER_EXPIRES,
        strict_decode=True,
    ) as client:
        rows = client.get_market_data()

    _assert_chain(rows[0], expected_entries, truthy, expect)


@pytest.mark.parametrize(("payload", "expected_entries", "truthy", "expect"), _MATRIX)
async def test_chain_survives_strict_decode_async(
    payload: dict[str, Any],
    expected_entries: list[str],
    truthy: bool,
    expect: dict[str, Any],
    httpx_mock: HTTPXMock,
) -> None:
    """Async twin of :func:`test_chain_survives_strict_decode` (C-3)."""
    httpx_mock.add_response(method="GET", json={"count": 1, "items": [payload]})

    async with aio.AsyncClient(
        base_url=_BASE_URL,
        token="test-token",
        token_expires_at=_NEVER_EXPIRES,
        strict_decode=True,
    ) as client:
        rows = await client.get_market_data()

    _assert_chain(rows[0], expected_entries, truthy, expect)


# ---------------------------------------------------------------------------
# EDGE boundary / roster — the eleventh key (NOBJ-MD-01, D-02)
# ---------------------------------------------------------------------------


_ELEVENTH_KEY_ROW: dict[str, Any] = {
    **_WIRE_REAL,
    "market_data": {**_WIRE_REAL["market_data"], "ZZ": 1},
}


def test_an_undeclared_market_data_key_is_one_extra_record_on_the_container(
    httpx_mock: HTTPXMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """D-02: the roster is the ten measured keys; an eleventh is a non-fatal ``extra``.

    The declared ten produce NOTHING (the matrix above asserts that). A key
    outside the roster produces exactly ONE record, attributed to
    :class:`MarketDataEntries` at the nested path — never to the snapshot, and
    never a raise. Phase 39 corrects such a key in-cycle if the live run finds one.
    """
    httpx_mock.add_response(method="GET", json={"count": 1, "items": [_ELEVENTH_KEY_ROW]})

    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="market_data_client"):
        rows = market_data_client.client._get_default().get_market_data()

    assert _records(caplog) == [("MarketDataEntries", ".market_data.ZZ", "extra")]
    # The chain is untouched by the stray key.
    _assert_chain(rows[0], ["BI"], True, _REAL_EXPECT)


async def test_an_undeclared_market_data_key_is_one_extra_record_on_the_container_async(
    httpx_mock: HTTPXMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Async twin of :func:`...on_the_container` (C-3)."""
    httpx_mock.add_response(method="GET", json={"count": 1, "items": [_ELEVENTH_KEY_ROW]})

    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="market_data_client"):
        rows = await aio._get_default().get_market_data()

    assert _records(caplog) == [("MarketDataEntries", ".market_data.ZZ", "extra")]
    _assert_chain(rows[0], ["BI"], True, _REAL_EXPECT)


def test_an_undeclared_market_data_key_is_not_fatal_under_strict_decode(
    httpx_mock: HTTPXMock,
) -> None:
    """``extra`` is an INFO kind — vendor field growth never breaks a strict run.

    Signed Phase 29 decision (sebadlf, 2026-08-18): strict decode raises on
    missing / type / non_dict but NEVER on an undeclared wire key.
    """
    httpx_mock.add_response(method="GET", json={"count": 1, "items": [_ELEVENTH_KEY_ROW]})

    with market_data_client.Client(
        base_url=_BASE_URL,
        token="test-token",
        token_expires_at=_NEVER_EXPIRES,
        strict_decode=True,
    ) as client:
        rows = client.get_market_data()

    assert bool(rows[0].market_data) is True


# ---------------------------------------------------------------------------
# EDGE adjacency / alias — the six aliases never shadow a wire slot (D-03)
# ---------------------------------------------------------------------------


def test_the_six_aliases_and_the_ten_wire_fields_are_disjoint() -> None:
    """No alias may collide with a declared slot of a ``frozen=True, slots=True`` class.

    A colliding name would either shadow the field or fail at class creation.
    The wire roster is asserted exactly, so an accidental eleventh field or a
    renamed one reddens here rather than silently widening the surface.
    """
    field_names = {f.name for f in dataclasses.fields(MarketDataEntries)}
    alias_names = {"bids", "offers", "last", "settlement", "close", "open_interest"}

    assert field_names == {"BI", "CL", "HI", "LA", "LO", "OF", "OI", "OP", "SE", "TV"}
    assert field_names & alias_names == set()
    # And the class still constructs under frozen+slots.
    assert MarketDataEntries.empty() is not None


def test_each_alias_returns_the_identical_object_the_wire_field_returns() -> None:
    """The aliases are plain read-only views — no copy, no cache, no transformation."""
    entries = MarketDataEntries.from_api(_WIRE_REAL["market_data"])

    assert entries.bids is entries.BI
    assert entries.offers is entries.OF
    assert entries.last is entries.LA
    assert entries.settlement is entries.SE
    assert entries.close is entries.CL
    assert entries.open_interest is entries.OI


# ---------------------------------------------------------------------------
# EDGE empty — the three empty payloads converge on ``MarketDataEntries.empty()``
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("payload", _EMPTY_ROWS)
def test_every_empty_payload_yields_the_empty_container(
    payload: dict[str, Any],
    httpx_mock: HTTPXMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Absent, ``null`` and ``{}`` are the SAME container, with zero records."""
    httpx_mock.add_response(method="GET", json={"count": 1, "items": [payload]})

    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="market_data_client"):
        rows = market_data_client.client._get_default().get_market_data()

    assert rows[0].market_data == MarketDataEntries.empty()
    assert rows[0].market_data.last == EntryValue.empty()
    assert rows[0].market_data.last.price is None
    assert rows[0].market_data.bids == []
    assert _records(caplog) == []


@pytest.mark.parametrize("payload", _EMPTY_ROWS)
async def test_every_empty_payload_yields_the_empty_container_async(
    payload: dict[str, Any],
    httpx_mock: HTTPXMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Async twin of :func:`test_every_empty_payload_yields_the_empty_container` (C-3)."""
    httpx_mock.add_response(method="GET", json={"count": 1, "items": [payload]})

    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="market_data_client"):
        rows = await aio._get_default().get_market_data()

    assert rows[0].market_data == MarketDataEntries.empty()
    assert rows[0].market_data.settlement == EntryValue.empty()
    assert rows[0].market_data.offers == []
    assert _records(caplog) == []


# ---------------------------------------------------------------------------
# EDGE ordering — the walker never sorts, dedupes or reorders a list field
# ---------------------------------------------------------------------------


def test_two_book_levels_with_the_same_price_both_survive_in_wire_order() -> None:
    """A book with a repeated price is not a set — both levels are kept, in order."""
    entries = MarketDataEntries.from_api(
        {
            "BI": [
                {"price": 10, "size": 1},
                {"price": 10, "size": 7},
                {"price": 9, "size": 3},
            ]
        }
    )

    assert entries.bids == [
        BookLevel(price=10.0, size=1),
        BookLevel(price=10.0, size=7),
        BookLevel(price=9.0, size=3),
    ]


def test_entries_reproduces_wire_order_verbatim() -> None:
    """``["OF", "BI"]`` stays ``["OF", "BI"]`` — never sorted, never deduped."""
    snap = MarketDataSnapshot.from_api({"entries": ["OF", "BI", "OF"]}, received_at=1.0)

    assert snap.entries == ["OF", "BI", "OF"]


# ---------------------------------------------------------------------------
# EDGE precision — the silent int -> float widening (RESEARCH F-3)
# ---------------------------------------------------------------------------


def test_a_wire_int_widens_to_float_silently_and_int_slots_stay_int(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """F-3: ``walk_field`` widens ``int`` BEFORE consulting ``scalar_passthrough``.

    ``price`` on both :class:`BookLevel` and :class:`EntryValue`, plus the
    ``HI`` / ``LO`` / ``OP`` / ``TV`` leaves, are declared ``float | None`` and
    the wire sends ``int`` for all of them. That widening emits NOTHING. The
    ``int``-declared slots ``size`` and ``date`` are NOT widened.
    """
    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="market_data_client"):
        entries = MarketDataEntries.from_api(_WIRE_REAL["market_data"])

    assert entries.last.price == 10.0
    assert isinstance(entries.last.price, float)
    assert isinstance(entries.bids[0].price, float)
    assert entries.HI == 12.0
    assert isinstance(entries.HI, float)
    assert entries.LO == 8.0
    assert entries.OP == 9.0
    # The int-declared slots keep their type — no widening, no divergence.
    assert entries.last.size == 1
    assert isinstance(entries.last.size, int)
    assert not isinstance(entries.last.size, float)
    assert entries.last.date == 20990101
    assert isinstance(entries.last.date, int)
    assert _records(caplog) == []


# ---------------------------------------------------------------------------
# EDGE empty / entries — the revoked link is a list, never ``None`` (NOBJ-MD-02)
# ---------------------------------------------------------------------------


# Complete rows varying ONLY ``entries``, so the record-set assertion below can
# stay global: a partial payload would emit one ``missing`` per omitted field and
# drown the single record the probe is about.
_ENTRIES_BASE: dict[str, Any] = {
    "symbol": "AAA1",
    "market_id": "ZZZ",
    "active": False,
    "market_data": None,
    "staleness_seconds": None,
    "note": None,
}


@pytest.mark.parametrize(
    ("payload", "expected_records"),
    [
        pytest.param(_ENTRIES_BASE, [], id="entries-absent"),
        pytest.param({**_ENTRIES_BASE, "entries": None}, [], id="entries-null"),
        pytest.param({**_ENTRIES_BASE, "entries": []}, [], id="entries-empty-list"),
        pytest.param(
            {**_ENTRIES_BASE, "entries": "not-a-list"},
            [("MarketDataSnapshot", ".entries", "type")],
            id="entries-non-list-scalar",
        ),
    ],
)
def test_entries_is_always_a_list_and_only_a_wrong_type_reports(
    payload: dict[str, Any],
    expected_records: list[tuple[str, str, str]],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """D-04: ``entries`` never holds ``None`` again — and a wrong type still diverges."""
    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="market_data_client"):
        snap = MarketDataSnapshot.from_api(payload, received_at=1.0)

    assert snap.entries == []
    assert _records(caplog) == expected_records


# ---------------------------------------------------------------------------
# EDGE adjacency / request — ``LatestRequest`` keeps absent-means-all (D-06)
# ---------------------------------------------------------------------------


def test_latest_request_omits_the_entries_key_when_the_list_is_empty() -> None:
    """D-06: the literal ``{"entries": []}`` must never reach the wire.

    The current semantics is "key absent = every entry type"; there is no
    evidence in the repo that the server distinguishes an explicit empty list,
    so the default must serialise as absence, not as emptiness.
    """
    assert LatestRequest(symbols=["AAA1"]).to_dict() == {"symbols": ["AAA1"]}
    assert LatestRequest(symbols=["AAA1"], entries=[]).to_dict() == {"symbols": ["AAA1"]}


def test_latest_request_emits_the_entries_key_when_the_list_is_populated() -> None:
    """The falsification half: a populated list is emitted verbatim."""
    assert LatestRequest(symbols=["AAA1"], entries=["BI"]).to_dict() == {
        "symbols": ["AAA1"],
        "entries": ["BI"],
    }
