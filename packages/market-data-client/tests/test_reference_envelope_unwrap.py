"""S-1 regression — ``/instruments`` and ``/instruments/segments`` envelopes (LIVE-TYP-01).

The Phase 33 live run (33-05, 2026-08-27) confirmed the finding ``29-SIZING.md``
raised as S-1 and could not close from the corpus alone: the develop wire wraps
both reference catalogues in an OBJECT envelope, and both parsers iterated that
object directly.

Iterating a ``dict`` yields its KEYS, so every parser call produced one
all-default model per envelope key — measured live as four ``non_dict``
divergence records (``F-82``/``F-102`` for ``Instrument``, ``F-83``/``F-103`` for
``Segment``, both surfaces) and, under ``MARKET_LIBS_STRICT_DECODE=1``, four
raises::

    PROBE instruments_sync:  FINDING SHAPE [sync]  MarketDataDecodeError model=Instrument path= declared=Instrument observed=str
    PROBE segments_sync:     FINDING SHAPE [sync]  MarketDataDecodeError model=Segment    path= declared=Segment    observed=str

The envelope key sets below are taken from the committed, PII-free baselines
``.planning/verification/schemas/market-data-client/get-instruments.json`` and
``get-segments.json`` — SHAPE only. Every identifier in the fixtures is
synthesised (``AAA1``, ``ZZZ``), never a captured live value (T-33-42).

Both surfaces are exercised: the fix lives in ``_core.py``, which ``client.py``
and ``aio.py`` both dispatch through, so the async twin is the evidence that the
mirror is real rather than duplicated (C-3).
"""

from __future__ import annotations

from typing import Any

from pytest_httpx import HTTPXMock

import market_data_client
from market_data_client import Instrument, Segment, aio

# ``GET /instruments`` — envelope {catalogue, count, items[], limit, offset, total}.
_INSTRUMENTS_ENVELOPE: dict[str, Any] = {
    "catalogue": {
        "age_seconds": 12.5,
        "instruments": 2,
        "last_error": None,
        "stale": False,
    },
    "count": 1,
    "items": [
        {
            "symbol": "AAA1",
            "segment": "SEG1",
            "expired": False,
            "market_id": "ZZZ",
            "currency": "ARS",
            "days_to_maturity": 30,
            "maturity": "2099-12-31",
            "outright": True,
            "subscribed": False,
            "active": None,
        }
    ],
    "limit": 100,
    "offset": 0,
    "total": 1,
}

# ``GET /instruments/segments`` — envelope {catalogue, segments[]}.
_SEGMENTS_ENVELOPE: dict[str, Any] = {
    "catalogue": {"age_seconds": 12.5, "instruments": 2},
    "segments": [{"segment": "SEG1", "live_instruments": 7}],
}


def test_get_instruments_unwraps_the_items_envelope(httpx_mock: HTTPXMock) -> None:
    """One real row comes back — not one all-default row per envelope key."""
    httpx_mock.add_response(method="GET", json=_INSTRUMENTS_ENVELOPE)

    result = market_data_client.client._get_default().get_instruments()

    # Before the fix this was 6 — one all-default ``Instrument`` per top-level
    # envelope key (catalogue, count, items, limit, offset, total).
    assert len(result) == 1
    assert isinstance(result[0], Instrument)
    assert result[0].symbol == "AAA1"
    assert result[0].segment == "SEG1"
    assert result[0].expired is False


async def test_get_instruments_unwraps_the_items_envelope_async(httpx_mock: HTTPXMock) -> None:
    """Async twin of :func:`test_get_instruments_unwraps_the_items_envelope` (C-3)."""
    httpx_mock.add_response(method="GET", json=_INSTRUMENTS_ENVELOPE)

    result = await aio._get_default().get_instruments()

    assert len(result) == 1
    assert isinstance(result[0], Instrument)
    assert result[0].symbol == "AAA1"
    assert result[0].segment == "SEG1"
    assert result[0].expired is False


def test_get_segments_unwraps_the_segments_envelope(httpx_mock: HTTPXMock) -> None:
    """One real row comes back — not one all-default row per envelope key."""
    httpx_mock.add_response(method="GET", json=_SEGMENTS_ENVELOPE)

    result = market_data_client.client._get_default().get_segments()

    # Before the fix this was 2 — one all-default ``Segment`` per top-level key.
    assert len(result) == 1
    assert isinstance(result[0], Segment)


async def test_get_segments_unwraps_the_segments_envelope_async(httpx_mock: HTTPXMock) -> None:
    """Async twin of :func:`test_get_segments_unwraps_the_segments_envelope` (C-3)."""
    httpx_mock.add_response(method="GET", json=_SEGMENTS_ENVELOPE)

    result = await aio._get_default().get_segments()

    assert len(result) == 1
    assert isinstance(result[0], Segment)


def test_bare_list_bodies_still_parse(httpx_mock: HTTPXMock) -> None:
    """The pre-envelope shape must NOT regress — a bare list is still accepted."""
    httpx_mock.add_response(
        method="GET",
        json=[
            {
                "symbol": "AAA1",
                "marketId": "ZZZ",
                "segment": "SEG1",
                "instrumentType": "E",
                "expired": False,
            }
        ],
    )

    result = market_data_client.client._get_default().get_instruments()

    assert len(result) == 1
    assert result[0].symbol == "AAA1"
    assert result[0].marketId == "ZZZ"


def test_envelope_with_non_list_items_collapses_to_empty(httpx_mock: HTTPXMock) -> None:
    """Collection guard: a non-list ``items`` yields ``[]``, never a ``TypeError``."""
    httpx_mock.add_response(method="GET", json={"count": 0, "items": None})

    assert market_data_client.client._get_default().get_instruments() == []
