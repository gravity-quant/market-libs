"""Safe-access frozen dataclasses for market-data API responses.

All response models inherit from :class:`SafeModel` and are constructed via
:meth:`SafeModel.from_api`, which tolerates partial or missing fields and
substitutes safe defaults per type:

- ``str`` -> ``""``
- ``int`` / ``float`` -> ``0`` / ``0.0``
- ``bool`` -> ``False``
- ``list[X]`` -> ``[]``
- nested ``SafeModel`` -> ``X.from_api(None)`` (empty instance)
- ``X | None`` -> ``None`` when missing (explicit opt-in to nullable)

Extra keys in the payload are ignored; missing keys fall back to defaults.
Chained access like ``snapshot.entries[0].price`` never raises — the worst
case is a final ``None`` or a zero-valued primitive.

Field names follow the wire format (camelCase) verbatim so JSON parsing can
stay declarative. They are PROVISIONAL: the OpenAPI is not vendored (A1/A2),
so shapes are reconciled against real payloads in Phase 23; ``from_api``
tolerance bounds the blast radius of a wrong guess. This module is exempt from
the ``N815`` naming rule (see ``[tool.ruff.lint.per-file-ignores]`` in the root
``pyproject.toml``).

``received_at`` is a first-class, CLIENT-STAMPED field on
:class:`MarketDataSnapshot` (D-01): it records when the client received the
response, NOT a payload value. :meth:`MarketDataSnapshot.from_api` injects it
directly as a keyword and never routes it through ``_coerce`` (which would
collapse it to ``0.0``). Only :class:`MarketDataSnapshot` is client-stamped;
every other :class:`SafeModel` subclass carries no ``received_at``.

This module is a package-local copy of the higyrus ``SafeModel`` / ``_coerce``
implementation (D-03): the no-shared-internals constraint forbids importing any
symbol from ``higyrus_client``.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from types import NoneType, UnionType
from typing import Any, Self, Union, cast, get_args, get_origin, get_type_hints

from market_data_client import _params

__all__ = [
    "CalendarConfig",
    "CalendarDay",
    "Instrument",
    "LatestRequest",
    "MarketDataSnapshot",
    "NewSymbol",
    "NewSymbols",
    "SafeModel",
    "Segment",
    "Symbol",
    "SymbolPatch",
]


class SafeModel:
    """Base class for market-data API response models.

    Subclasses must be frozen dataclasses. Construct instances via
    :meth:`from_api` to tolerate partial or missing fields.
    """

    @classmethod
    def from_api(cls, payload: Any) -> Self:
        """Build an instance from an API payload, with safe defaults."""
        data: dict[str, Any] = payload if isinstance(payload, dict) else {}
        hints = get_type_hints(cls)
        kwargs: dict[str, Any] = {}
        for field in fields(cast(Any, cls)):
            kwargs[field.name] = _coerce(data.get(field.name), hints[field.name])
        return cls(**kwargs)


def _coerce(value: Any, hint: Any) -> Any:
    """Coerce ``value`` to match ``hint``, substituting safe defaults for ``None``."""
    origin = get_origin(hint)
    args = get_args(hint)

    # Optional[T] / T | None: explicit opt-in to nullable — a missing value
    # stays None instead of collapsing to a typed zero.
    if origin is Union or origin is UnionType:
        if value is None:
            return None
        non_none = [a for a in args if a is not NoneType]
        if len(non_none) == 1:
            return _coerce(value, non_none[0])
        return value

    if origin is list:
        if not isinstance(value, list):
            return []
        inner = args[0] if args else Any
        return [_coerce(item, inner) for item in value]

    if isinstance(hint, type) and issubclass(hint, SafeModel):
        return hint.from_api(value)

    if hint is str:
        return value if isinstance(value, str) else ""
    if hint is bool:
        return value if isinstance(value, bool) else False
    if hint is int:
        # bool is a subclass of int in Python — exclude it so bool payloads
        # don't collapse into "size=True".
        if isinstance(value, bool):
            return 0
        return value if isinstance(value, int) else 0
    if hint is float:
        if isinstance(value, bool):
            return 0.0
        if isinstance(value, int | float):
            return float(value)
        return 0.0

    return value


@dataclass(frozen=True, slots=True)
class MarketDataSnapshot(SafeModel):
    """A market-data snapshot returned by the ``/marketdata`` read endpoints.

    Reconciled against the real develop wire (LIVE-MD-01): ``/marketdata`` items
    carry ``symbol``, ``market_id``, ``active``, ``entries`` (a list of entry-type
    code strings, e.g. ``["BI", "OF"]``), ``market_data`` (a dict passthrough of
    per-entry-type rows), ``staleness_seconds``, and — on ``/marketdata/latest``
    no-data rows — a ``note`` string. ``received_at`` is a first-class,
    CLIENT-STAMPED field (D-01): it is injected by :meth:`from_api` as a keyword
    and never coerced from the payload (a wire/decoy ``received_at`` never wins).
    """

    symbol: str
    market_id: str
    active: bool
    entries: list[str]
    market_data: dict[str, Any]
    staleness_seconds: float
    received_at: float
    note: str | None = None

    @classmethod
    def from_api(cls, payload: Any, *, received_at: float = 0.0) -> Self:
        """Build a snapshot, injecting the client-supplied ``received_at`` stamp.

        Every field except ``received_at`` is deserialized tolerantly via
        ``_coerce``. ``received_at`` is set DIRECTLY from the keyword argument,
        bypassing ``_coerce`` (which would otherwise collapse it to ``0.0``) —
        this is the D-01 fidelity contract: a payload ``"received_at"`` key is
        ignored and the injected stamp always wins.
        """
        data: dict[str, Any] = payload if isinstance(payload, dict) else {}
        hints = get_type_hints(cls)
        kwargs: dict[str, Any] = {}
        for field in fields(cls):
            if field.name == "received_at":
                kwargs[field.name] = received_at  # INJECT — skip _coerce (D-01)
            else:
                kwargs[field.name] = _coerce(data.get(field.name), hints[field.name])
        return cls(**kwargs)


@dataclass(frozen=True, slots=True)
class LatestRequest:
    """Typed request body for the batch ``POST /marketdata/latest`` endpoint (D-05).

    NOT a :class:`SafeModel` — this dataclass serializes OUT via :meth:`to_dict`.
    PROVISIONAL field names (A1/A2 — Phase 23 reconciles). :meth:`to_dict` drops
    ``None``-valued optionals so the wire body stays minimal and Phase 23 can
    adjust field names in one place.
    """

    symbols: list[str]
    marketId: str | None = None
    entries: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a wire dict, dropping ``None``-valued optional fields."""
        out: dict[str, Any] = {"symbols": self.symbols}
        if self.marketId is not None:
            out["marketId"] = self.marketId
        if self.entries is not None:
            out["entries"] = self.entries
        return out


# ----------------------------------------------------------------------
# Symbols write request models (D-09 / D-10 / D-11) — serialize-OUT
# ----------------------------------------------------------------------
#
# These three request models feed the ``POST /symbols``, ``POST /symbols/batch``
# and ``PATCH /symbols/{id}`` write endpoints (MUT-MD-01). Like
# :class:`LatestRequest`, they are NOT :class:`SafeModel` subclasses — they
# serialize OUT via a hand-written :meth:`to_dict`, they do not deserialize IN.


@dataclass(frozen=True, slots=True)
class NewSymbol:
    """Typed request body element for a symbol create (D-09 / D-10).

    NOT a :class:`SafeModel` — this dataclass serializes OUT via :meth:`to_dict`.
    ``market_id`` is defaulted, non-nullable, and ALWAYS emitted (D-10). The wire
    key is snake_case ``market_id`` per the source-plan schema — INTENTIONALLY
    different from :class:`LatestRequest`'s camelCase ``marketId`` (Pitfall 3 /
    A2; the real key is confirmed live in Phase 27).
    """

    symbol: str
    market_id: str = "ROFX"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a wire dict — both keys always present (D-10)."""
        return {"symbol": self.symbol, "market_id": self.market_id}


@dataclass(frozen=True, slots=True)
class NewSymbols:
    """Typed request body for the batch ``POST /symbols/batch`` endpoint (D-09).

    NOT a :class:`SafeModel` — serializes OUT via :meth:`to_dict`. Enforces the
    client-side 1-500 batch-size guard in :meth:`__post_init__`, raising a plain
    :class:`ValueError` (NOT a ``MarketData*`` error — that hierarchy is reserved
    for server contract errors, D-11) before any spec build or HTTP dispatch. The
    ``ValueError``-only ``__post_init__`` reads but never mutates fields, so it is
    valid on a frozen dataclass without ``object.__setattr__``.
    """

    symbols: list[NewSymbol]

    def __post_init__(self) -> None:
        """Enforce the 1-500 batch-size bound (D-11) — plain ValueError."""
        if not 1 <= len(self.symbols) <= 500:
            raise ValueError(f"NewSymbols requires 1-500 symbols, got {len(self.symbols)}")

    def to_dict(self) -> dict[str, Any]:
        """Serialize to ``{"symbols": [each element's to_dict()]}``."""
        return {"symbols": [s.to_dict() for s in self.symbols]}


@dataclass(frozen=True, slots=True)
class SymbolPatch:
    """Typed request body for the ``PATCH /symbols/{id}`` endpoint (D-09).

    NOT a :class:`SafeModel` — serializes OUT via :meth:`to_dict`. Carries the
    single ``active`` toggle the update endpoint accepts.
    """

    active: bool

    def to_dict(self) -> dict[str, Any]:
        """Serialize to ``{"active": self.active}``."""
        return {"active": self.active}


# ----------------------------------------------------------------------
# Calendar write request models (D-08 .. D-13) — serialize-OUT
# ----------------------------------------------------------------------
#
# These three request models feed the ``PUT /calendar/config``,
# ``POST /calendar/config/preview`` and ``POST /calendar/holidays`` write
# endpoints (MUT-MD-02). Like the symbols write models above they are NOT
# :class:`SafeModel` subclasses (D-08) — they serialize OUT via a hand-written
# :meth:`to_dict`, they never deserialize IN. Field names, defaults and bounds
# are verbatim from the live OpenAPI (re-fetched 2026-07-31); the scalar bounds
# it declares are deliberately NOT enforced client-side (D-13) — they surface as
# the server's ``422``.


@dataclass(frozen=True, slots=True)
class MarketHoursIn:
    """Typed request body for the calendar-config write endpoints (D-08 / D-09).

    NOT a :class:`SafeModel` — this dataclass serializes OUT via :meth:`to_dict`.
    Field order, wire keys and defaults are verbatim from the live OpenAPI
    (D-10): ``open_time`` / ``close_time`` / ``timezone`` are required, the rest
    default to ``pre_open_minutes=10``, ``enabled=True``, ``updated_by=""`` and
    ``confirm=False``.

    ``confirm`` is a FIELD of this model, not a loose method kwarg (D-09): it is
    the exact analogue of :attr:`NewSymbol.market_id` — defaulted, non-nullable
    and ALWAYS emitted. It is the "second opinion" guardrail the server demands
    when a legal-but-suspicious window produces warnings (see
    ``POST /calendar/config/preview``), so the consumer has to write
    ``confirm=True`` on purpose to overwrite a warned-about config.

    The scalar bounds the OpenAPI declares (``pre_open_minutes`` 0-120,
    ``timezone`` 1-64 chars, ``updated_by`` <= 200 chars, and the ``format: time``
    shape of the hour strings) are NOT validated client-side (D-13): a client-side
    regex would produce false negatives because ``format: time`` also admits
    ``"10:00:00"``. Out-of-range values ride to the server's ``422``.
    """

    open_time: str
    close_time: str
    timezone: str
    pre_open_minutes: int = 10
    enabled: bool = True
    updated_by: str = ""
    confirm: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a wire dict — all 7 keys always present (D-10).

        Routed through ``_params.drop_none`` for consistency with
        :meth:`HolidayIn.to_dict` (D-11); here it is a no-op because no field is
        nullable, so every key — including ``confirm: False`` — always travels.
        """
        return _params.drop_none(
            {
                "open_time": self.open_time,
                "close_time": self.close_time,
                "timezone": self.timezone,
                "pre_open_minutes": self.pre_open_minutes,
                "enabled": self.enabled,
                "updated_by": self.updated_by,
                "confirm": self.confirm,
            }
        )


@dataclass(frozen=True, slots=True)
class HolidayIn:
    """Typed request body element for a holiday create (D-08 / D-10 / D-11).

    NOT a :class:`SafeModel` — this dataclass serializes OUT via :meth:`to_dict`.
    ``day`` is the required ISO ``YYYY-MM-DD`` date; ``closed`` defaults to
    ``True`` (``False`` = open with custom hours) and ``description`` to ``""``,
    both verbatim from the live OpenAPI (D-10).

    This is the FIRST request model of the package with nullable fields, so
    ``_params.drop_none`` is load-bearing here (D-11): ``open_time`` /
    ``close_time`` DISAPPEAR from the wire when they are ``None`` (the OpenAPI
    documents ``null`` as "configured default", and the field default is ``None``
    too, so dropping the key is semantically equivalent — assumption A3,
    revalidated live in Phase 27), while the falsy-but-not-``None`` ``closed`` and
    ``description=""`` are still emitted.

    As with :class:`MarketHoursIn`, the declared scalar bounds (``description``
    <= 500 chars, the ``format: date`` / ``format: time`` shapes) are NOT checked
    client-side (D-13) — they surface as the server's ``422``.
    """

    day: str
    closed: bool = True
    open_time: str | None = None
    close_time: str | None = None
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a wire dict, dropping the ``None``-valued hour pair (D-11)."""
        return _params.drop_none(
            {
                "day": self.day,
                "closed": self.closed,
                "open_time": self.open_time,
                "close_time": self.close_time,
                "description": self.description,
            }
        )


# ----------------------------------------------------------------------
# Reference-data models (D-04 / D-05) — plain SafeModel, no received_at
# ----------------------------------------------------------------------
#
# These five catalog models follow the ``SafeModel`` base precedent: they are
# built via the INHERITED ``SafeModel.from_api`` (no override) and carry NO
# client-stamped ``received_at`` (D-05) — reference data is slow-moving with no
# ``max_staleness_seconds`` companion to justify a receipt-time stamp. Shapes
# are PROVISIONAL (A1/A2 — OpenAPI not vendored); Phase 23 reconciles field
# names/types against real develop payloads, and ``from_api`` tolerance bounds
# the blast radius of a wrong guess.


@dataclass(frozen=True, slots=True)
class Instrument(SafeModel):
    """An instrument row from ``GET /instruments``.

    PROVISIONAL shape (A1/A2 — OpenAPI not vendored; Phase 23 reconciles). A
    plain :class:`SafeModel` subclass built via the inherited ``from_api``: it
    carries NO ``received_at`` (D-05 — reference data is unstamped).
    """

    symbol: str
    marketId: str
    segment: str
    instrumentType: str
    expired: bool


@dataclass(frozen=True, slots=True)
class Segment(SafeModel):
    """A market segment row from ``GET /instruments/segments``.

    PROVISIONAL shape (A1/A2 — OpenAPI not vendored; Phase 23 reconciles). A
    plain :class:`SafeModel` subclass built via the inherited ``from_api``: it
    carries NO ``received_at`` (D-05 — reference data is unstamped).
    """

    marketSegmentId: str
    marketId: str
    description: str


@dataclass(frozen=True, slots=True)
class Symbol(SafeModel):
    """A symbol row from ``GET /symbols``.

    PROVISIONAL shape (A1/A2 — OpenAPI not vendored; Phase 23 reconciles). A
    plain :class:`SafeModel` subclass built via the inherited ``from_api``: it
    carries NO ``received_at`` (D-05 — reference data is unstamped).
    """

    symbol: str
    marketId: str
    active: bool


@dataclass(frozen=True, slots=True)
class CalendarDay(SafeModel):
    """A calendar day row from ``GET /calendar`` (flat list item, D-06).

    PROVISIONAL shape (A1/A2 — OpenAPI not vendored; Phase 23 reconciles). A
    plain :class:`SafeModel` subclass built via the inherited ``from_api``: it
    carries NO ``received_at`` (D-05 — reference data is unstamped).
    """

    date: str
    marketId: str
    isBusinessDay: bool


@dataclass(frozen=True, slots=True)
class CalendarConfig(SafeModel):
    """The single calendar configuration object from ``GET /calendar/config`` (D-07).

    Reconciled against the real develop wire (LIVE-MD-01): ``open``/``close`` trading
    times (str); ``enabled``/``editable``/``env_bypass`` flags (bool);
    ``pre_open_minutes`` (int); ``source``/``timezone``/``updated_by`` (str);
    ``warnings`` (list, wire sends ``[]``); ``updated_at`` (str | None, wire sends
    ``null``). The ONE non-collection reference model (D-07): an empty/None body
    collapses to ``CalendarConfig.from_api(None)`` (tolerant default), never a raise.
    A plain :class:`SafeModel` subclass built via the inherited ``from_api``: it
    carries NO ``received_at`` (D-05 — reference data is unstamped).
    """

    open: str
    close: str
    enabled: bool
    editable: bool
    env_bypass: bool
    pre_open_minutes: int
    source: str
    timezone: str
    updated_by: str
    warnings: list[Any]
    updated_at: str | None = None
