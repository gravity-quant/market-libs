"""Safe-access models for the Primary API v1.21 client.

Each model is a frozen dataclass that exposes the wire payload through
attribute access with always-defined defaults: missing list keys become
``[]``, missing nested-model keys become an empty model instance, missing
scalars become ``None``, missing dicts become ``{}``. Chained access like
``snapshot.SE.price`` never raises ``KeyError`` or ``AttributeError`` —
the worst case is a final ``None`` for an absent scalar.

Construct an instance from a raw dict via ``Model.from_api(payload)``;
``Model.empty()`` builds a default instance with all attributes at their
safe defaults. Instances are frozen to discourage mutation of API
responses.
"""

from __future__ import annotations

import types
from dataclasses import dataclass, field, fields
from typing import Any, ClassVar, Self, Union, get_args, get_origin, get_type_hints

from matriz_client.types import (
    CFICode,
    Currency,
    MarketId,
    OrderStatus,
    OrderType,
    SegmentId,
    Side,
    TimeInForce,
)

__all__ = [
    "AccountId",
    "AccountReport",
    "DetailedPosition",
    "ExecutionReportFrame",
    "Instrument",
    "InstrumentDetail",
    "InstrumentId",
    "MarketDataEntryValue",
    "MarketDataFrame",
    "MarketDataLevel",
    "MarketDataSnapshot",
    "NewOrderResponse",
    "Order",
    "OrderReport",
    "Position",
    "PrimaryWsMessage",
    "Segment",
    "Trade",
    "UnknownFrame",
]


# ----------------------------------------------------------------------
# Type-hint introspection helpers
# ----------------------------------------------------------------------


def _strip_optional(tp: Any) -> Any:
    """Return ``T`` from ``T | None`` / ``Optional[T]``; pass through otherwise."""
    if get_origin(tp) in (Union, types.UnionType):
        args = [a for a in get_args(tp) if a is not type(None)]
        if len(args) == 1:
            return args[0]
    return tp


def _is_model(tp: Any) -> bool:
    return isinstance(tp, type) and issubclass(tp, _SafeModel)


def _convert(tp: Any, value: Any) -> Any:
    """Coerce ``value`` to the shape declared by ``tp``, applying safe defaults."""
    inner = _strip_optional(tp)
    origin = get_origin(inner)

    if origin is list:
        items = value if isinstance(value, list) else []
        (item_tp,) = get_args(inner)
        if _is_model(item_tp):
            return [item_tp.from_api(v) for v in items]
        return list(items)

    if origin is dict:
        return value if isinstance(value, dict) else {}

    if _is_model(inner):
        return inner.from_api(value) if isinstance(value, dict) else inner.empty()

    return value


# ----------------------------------------------------------------------
# Base
# ----------------------------------------------------------------------


class _SafeModel:
    """Mixin providing safe ``from_api``/``empty`` constructors for dataclasses."""

    # Declared so pyright accepts ``cls`` as a dataclass; populated by ``@dataclass``.
    __dataclass_fields__: ClassVar[dict[str, Any]]

    @classmethod
    def from_api(cls, data: Any) -> Self:
        if not isinstance(data, dict):
            return cls.empty()
        hints = get_type_hints(cls)
        return cls(**{f.name: _convert(hints[f.name], data.get(f.name)) for f in fields(cls)})

    @classmethod
    def empty(cls) -> Self:
        hints = get_type_hints(cls)
        return cls(**{f.name: _convert(hints[f.name], None) for f in fields(cls)})


# ----------------------------------------------------------------------
# Identifiers
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class InstrumentId(_SafeModel):
    """Canonical identifier for an instrument (§5.1)."""

    marketId: MarketId | None = None
    symbol: str | None = None


@dataclass(frozen=True)
class AccountId(_SafeModel):
    """Account wrapper used by WebSocket subscriptions (§7.1)."""

    id: str | None = None


# ----------------------------------------------------------------------
# Segments and instruments
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class Segment(_SafeModel):
    """Market segment descriptor (§4.1)."""

    marketSegmentId: SegmentId | None = None
    marketId: MarketId | None = None


@dataclass(frozen=True)
class Instrument(_SafeModel):
    """Instrument header returned by list endpoints (§5.1)."""

    instrumentId: InstrumentId = field(default_factory=InstrumentId.empty)
    cficode: CFICode | None = None


@dataclass(frozen=True)
class InstrumentDetail(_SafeModel):
    """Full instrument detail (§5.2).

    The Primary API omits many fields depending on segment/CFI; safe defaults
    keep attribute access non-throwing.
    """

    instrumentId: InstrumentId = field(default_factory=InstrumentId.empty)
    cficode: CFICode | None = None
    segment: Segment = field(default_factory=Segment.empty)
    lowLimitPrice: float | None = None
    highLimitPrice: float | None = None
    minPriceIncrement: float | None = None
    minTradeVol: float | None = None
    maxTradeVol: float | None = None
    tickSize: float | None = None
    contractMultiplier: float | None = None
    roundLot: float | None = None
    priceConvertionFactor: float | None = None
    maturityDate: str | None = None
    currency: Currency | None = None
    orderTypes: list[OrderType] = field(default_factory=list)
    timesInForce: list[TimeInForce] = field(default_factory=list)
    instrumentPricePrecision: int | None = None
    instrumentSizePrecision: int | None = None
    securityDescription: str | None = None
    tickPriceRanges: dict[str, Any] = field(default_factory=dict)


# ----------------------------------------------------------------------
# Orders
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class NewOrderResponse(_SafeModel):
    """Identifiers returned by ``newSingleOrder`` / ``replaceById`` / ``cancelById`` (§6.3)."""

    clientId: str | None = None
    proprietary: str | None = None


@dataclass(frozen=True)
class Order(_SafeModel):
    """Single order status record (§6.8).

    ``orderId`` is ``None`` until the exchange accepts the order (§13).
    """

    orderId: str | None = None
    clOrdId: str | None = None
    proprietary: str | None = None
    execId: str | None = None
    accountId: str | None = None
    instrumentId: InstrumentId = field(default_factory=InstrumentId.empty)
    price: float | None = None
    orderQty: float | None = None
    ordType: OrderType | None = None
    side: Side | None = None
    timeInForce: TimeInForce | None = None
    transactTime: str | None = None
    avgPx: float | None = None
    lastPx: float | None = None
    lastQty: float | None = None
    cumQty: float | None = None
    leavesQty: float | None = None
    status: OrderStatus | None = None
    text: str | None = None


@dataclass(frozen=True)
class OrderReport(Order):
    """Execution report (§7.5) — superset of :class:`Order`."""

    wsClOrdId: str | None = None


# ----------------------------------------------------------------------
# Market data
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class MarketDataLevel(_SafeModel):
    """Price level inside an order-book entry (``BI`` / ``OF``)."""

    price: float | None = None
    size: int | None = None


@dataclass(frozen=True)
class MarketDataEntryValue(_SafeModel):
    """Scalar market-data entry (``LA``, ``SE``, ``OI`` …) per §8.1."""

    price: float | None = None
    size: int | None = None
    date: int | None = None


@dataclass(frozen=True)
class MarketDataSnapshot(_SafeModel):
    """Market-data response (§8.1).

    Each entry is optional in the wire payload; missing entries fall back
    to safe defaults so chained access (``snapshot.SE.price``) never
    raises.
    """

    BI: list[MarketDataLevel] = field(default_factory=list)
    OF: list[MarketDataLevel] = field(default_factory=list)
    LA: MarketDataEntryValue = field(default_factory=MarketDataEntryValue.empty)
    SE: MarketDataEntryValue = field(default_factory=MarketDataEntryValue.empty)
    OI: MarketDataEntryValue = field(default_factory=MarketDataEntryValue.empty)
    # CL viene como objeto {price, size, date} en la wire format (§8.1),
    # igual que LA/SE/OI. OP en cambio es escalar. Ver issue #102.
    CL: MarketDataEntryValue = field(default_factory=MarketDataEntryValue.empty)
    OP: float | None = None
    HI: float | None = None
    LO: float | None = None
    TV: float | None = None
    IV: float | None = None
    EV: float | None = None
    NV: float | None = None
    ACP: float | None = None


@dataclass(frozen=True)
class Trade(_SafeModel):
    """Historical trade record (§8.4)."""

    symbol: str | None = None
    servertime: int | None = None
    size: int | None = None
    price: float | None = None
    datetime: str | None = None


# ----------------------------------------------------------------------
# Risk API
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class Position(_SafeModel):
    """Aggregated position per symbol for an account (§9.1)."""

    symbol: str | None = None
    buySize: float | None = None
    buyPrice: float | None = None
    sellSize: float | None = None
    sellPrice: float | None = None
    totalDailyDiff: float | None = None
    totalDiff: float | None = None
    tradingSymbol: str | None = None


@dataclass(frozen=True)
class DetailedPosition(_SafeModel):
    """Detailed position aggregated per account (§9.2)."""

    account: str | None = None
    totalDailyDiffPlain: float | None = None
    totalMarketValue: float | None = None
    report: dict[str, Any] = field(default_factory=dict)
    lastCalculation: str | None = None


@dataclass(frozen=True)
class AccountReport(_SafeModel):
    """Full account report with cash, margins and portfolio (§9.3)."""

    accountName: str | None = None
    marketMember: str | None = None
    marketMemberIdentity: str | None = None
    collateral: float | None = None
    margin: float | None = None
    availableToCollateral: float | None = None
    detailedAccountReports: dict[str, Any] = field(default_factory=dict)
    portfolio: dict[str, Any] = field(default_factory=dict)
    ordersMargin: float | None = None
    currentCash: float | None = None
    dailyDiff: float | None = None
    uncoveredMargin: float | None = None


# ----------------------------------------------------------------------
# WebSocket frames
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class MarketDataFrame(_SafeModel):
    """Market-data WebSocket frame (``type == "Md"``, §8.2)."""

    type: str | None = None
    timestamp: int | None = None
    instrumentId: InstrumentId = field(default_factory=InstrumentId.empty)
    marketData: MarketDataSnapshot = field(default_factory=MarketDataSnapshot.empty)


@dataclass(frozen=True)
class ExecutionReportFrame(_SafeModel):
    """Execution-report WebSocket frame (``type == "or"``, §7.5)."""

    type: str | None = None
    timestamp: int | None = None
    orderReport: OrderReport = field(default_factory=OrderReport.empty)


@dataclass(frozen=True)
class UnknownFrame:
    """Catch-all for WebSocket frames whose ``type`` is not modeled.

    Preserves the raw payload in :attr:`raw` so callers can still inspect
    forward-compatible fields without losing information. Implements the
    ``from_api``/``empty`` duck-typed contract so the WS dispatcher can
    treat it like any other frame model.
    """

    type: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_api(cls, data: Any) -> Self:
        if not isinstance(data, dict):
            return cls()
        return cls(type=data.get("type"), raw=dict(data))

    @classmethod
    def empty(cls) -> Self:
        return cls()


PrimaryWsMessage = MarketDataFrame | ExecutionReportFrame | UnknownFrame
"""Union of inbound WebSocket frame variants surfaced to user callbacks."""
