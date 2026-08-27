"""SC-3 regression — a symbols write ACK carries no row timestamps.

The Phase 33 live run (33-05) measured, on both surfaces, ``F-141``/``F-110``
(``Symbol.created_at``) and ``F-142``/``F-111`` (``Symbol.updated_at``) as
``missing``.

The three write acknowledgements and the catalogue read return DIFFERENT field
sets, and the committed baselines say so:

* ``GET /symbols`` → ``{active, created_at, id, market_id, received_at, symbol,
  updated_at}`` (``get-symbols.json``);
* ``POST /symbols`` → ``{active, created, id, market_id, note, symbol}``
  (``create-symbol-sync-response.json``);
* ``POST /symbols/batch`` items → the same minus ``note``;
* ``PATCH /symbols/{id}`` → ``{active, id, market_id, note, symbol}``.

Neither timestamp rides any ACK. Declaring them ``str = ""`` made every write
manufacture two empty strings that a caller could not tell apart from a real
row whose timestamps happened to be blank — and under ``strict_decode`` it made
every write fatal.

Operator disposition (33-07 Task 1, ``SC-3 = fix-shape-now``): retype both to
``str | None = None``. SOURCE-BREAKING for ``market-data-client``; Phase 34
carries the 0.4.0 → 0.5.0 bump.

Both surfaces are exercised; the fix is in ``models.py``, which both shells
reach through ``_core.parse_symbols_response`` (C-3). Fixtures are synthesised
to the baseline SHAPE — ``GSDPROBE``-style identifiers, never a captured live
value (T-33-42).
"""

from __future__ import annotations

from typing import Any

from pytest_httpx import HTTPXMock

import market_data_client
from market_data_client import NewSymbol, Symbol, aio

_CREATE_ACK: dict[str, Any] = {
    "symbol": "AAA1",
    "market_id": "ZZZ",
    "active": True,
    "id": 4242,
    "created": True,
    "note": "creado",
}

_CATALOGUE_ROW: dict[str, Any] = {
    "symbol": "AAA1",
    "market_id": "ZZZ",
    "active": True,
    "id": 4242,
    "created_at": "2099-01-01T00:00:00Z",
    "updated_at": "2099-01-02T00:00:00Z",
    "received_at": None,
}

_NEW = NewSymbol(symbol="AAA1", market_id="ZZZ")


def _armed_sync() -> Any:
    market_data_client.configure(mutating_allowed=True, expected_host="market-data-develop.test")
    return market_data_client.client._get_default()


def _armed_async() -> Any:
    aio.configure(mutating_allowed=True, expected_host="market-data-develop.test")
    return aio._get_default()


def test_create_ack_leaves_the_timestamps_absent(httpx_mock: HTTPXMock) -> None:
    """The two timestamps come back ``None``, not two manufactured empty strings."""
    httpx_mock.add_response(method="POST", json=_CREATE_ACK)

    rows = _armed_sync().create_symbol(_NEW)

    assert len(rows) == 1
    row = rows[0]
    assert isinstance(row, Symbol)
    assert row.created_at is None
    assert row.updated_at is None
    # Everything the ACK DOES carry is untouched.
    assert row.symbol == "AAA1"
    assert row.market_id == "ZZZ"
    assert row.id == 4242


async def test_create_ack_leaves_the_timestamps_absent_async(httpx_mock: HTTPXMock) -> None:
    """Async twin of :func:`test_create_ack_leaves_the_timestamps_absent` (C-3)."""
    httpx_mock.add_response(method="POST", json=_CREATE_ACK)

    rows = await _armed_async().create_symbol(_NEW)

    assert len(rows) == 1
    row = rows[0]
    assert isinstance(row, Symbol)
    assert row.created_at is None
    assert row.updated_at is None
    assert row.symbol == "AAA1"
    assert row.market_id == "ZZZ"
    assert row.id == 4242


def test_create_ack_is_not_fatal_under_strict_decode(httpx_mock: HTTPXMock) -> None:
    """Under strict decode a write ACK stops raising — the ACK shape is legitimate.

    Before the retype this body raised ``MarketDataDecodeError`` on
    ``.created_at``, which would have made every strict-mode write unusable.
    """
    httpx_mock.add_response(method="POST", json=_CREATE_ACK)

    with market_data_client.Client(
        base_url="https://market-data-develop.test/api",
        token="test-token",
        token_expires_at=9_999_999_999.0,
        mutating_allowed=True,
        expected_host="market-data-develop.test",
        strict_decode=True,
    ) as client:
        rows = client.create_symbol(_NEW)

    assert rows[0].created_at is None


async def test_create_ack_is_not_fatal_under_strict_decode_async(httpx_mock: HTTPXMock) -> None:
    """Async twin of :func:`test_create_ack_is_not_fatal_under_strict_decode` (C-3)."""
    httpx_mock.add_response(method="POST", json=_CREATE_ACK)

    async with aio.AsyncClient(
        base_url="https://market-data-develop.test/api",
        token="test-token",
        token_expires_at=9_999_999_999.0,
        mutating_allowed=True,
        expected_host="market-data-develop.test",
        strict_decode=True,
    ) as client:
        rows = await client.create_symbol(_NEW)

    assert rows[0].created_at is None


def test_catalogue_row_still_carries_real_timestamps(httpx_mock: HTTPXMock) -> None:
    """Non-regression: ``GET /symbols`` DOES send both, and both survive typed."""
    httpx_mock.add_response(method="GET", json=[_CATALOGUE_ROW])

    rows = market_data_client.client._get_default().get_symbols()

    assert len(rows) == 1
    assert rows[0].created_at == "2099-01-01T00:00:00Z"
    assert rows[0].updated_at == "2099-01-02T00:00:00Z"
