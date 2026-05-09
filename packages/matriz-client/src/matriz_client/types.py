"""Shared type vocabulary for the Primary API v1.21 client.

Exports :class:`~typing.Literal` aliases for enum-like parameters
(``Side``, ``OrderType`` …) and the market-data entry catalogues used by
both the REST and WebSocket clients. Payload shapes live in
:mod:`matriz_client.models` as safe-access dataclasses; this module
intentionally only carries the small enum-like vocabulary.
"""

from __future__ import annotations

from typing import Literal

__all__ = [
    # Constants
    "DEFAULT_MARKET_DATA_ENTRIES",
    "MARKET_DATA_ENTRIES",
    # Literals
    "CFICode",
    "Currency",
    "MarketDataEntry",
    "MarketId",
    "OrderStatus",
    "OrderType",
    "SegmentId",
    "Side",
    "TimeInForce",
]


# ----------------------------------------------------------------------
# Literals
# ----------------------------------------------------------------------

Side = Literal["BUY", "SELL"]
"""Order side (§6.3, §12.5)."""

OrderType = Literal["LIMIT", "MARKET", "STOP_LIMIT", "STOP_LIMIT_MERVAL"]
"""Order type (§12.5)."""

TimeInForce = Literal["DAY", "IOC", "FOK", "GTD"]
"""Order time-in-force (§6.3)."""

MarketId = Literal["ROFX"]
"""Market identifier (§12.1 — ``ROFX`` is the only documented value)."""

SegmentId = Literal["DDF", "DDA", "DUAL", "MERV", "U-DDF", "U-DDA", "U-DUAL"]
"""Market segment identifier (§5.5)."""

CFICode = Literal[
    "ESXXXX",
    "DBXXXX",
    "OCASPS",
    "OPASPS",
    "FXXXSX",
    "OPAFXS",
    "OCAFXS",
    "EMXXXX",
    "DBXXFR",
]
"""ISO 10962 CFI code accepted by ``/rest/instruments/byCFICode`` (§5.4)."""

MarketDataEntry = Literal[
    "BI",
    "OF",
    "LA",
    "OP",
    "CL",
    "SE",
    "HI",
    "LO",
    "TV",
    "OI",
    "IV",
    "EV",
    "NV",
    "ACP",
]
"""Market-data entry code (§8.3)."""

OrderStatus = Literal[
    "NEW",
    "PENDING_NEW",
    "PENDING_REPLACE",
    "PENDING_CANCEL",
    "REJECTED",
    "PENDING_APPROVAL",
    "CANCELLED",
    "REPLACED",
    "FILLED",
    "PARTIALLY_FILLED",
]
"""Order life-cycle status (§11)."""

Currency = Literal["ARS", "USD"]
"""Currency observed in instrument detail responses."""


# ----------------------------------------------------------------------
# Market-data entry catalogues (§8.3)
# ----------------------------------------------------------------------

MARKET_DATA_ENTRIES: tuple[MarketDataEntry, ...] = (
    "BI",  # best bid
    "OF",  # best offer
    "LA",  # last traded price
    "OP",  # open price
    "CL",  # previous close
    "SE",  # settlement
    "HI",  # session high
    "LO",  # session low
    "TV",  # traded volume
    "OI",  # open interest
    "IV",  # index value
    "EV",  # effective volume (ByMA)
    "NV",  # nominal volume (ByMA)
    "ACP",  # today's close
)
"""Full catalogue of market-data entry codes recognised by the Primary API."""

DEFAULT_MARKET_DATA_ENTRIES: tuple[MarketDataEntry, ...] = (
    "BI",
    "OF",
    "LA",
    "OP",
    "CL",
    "SE",
    "OI",
)
"""Default subset used when the caller does not specify ``entries``."""
