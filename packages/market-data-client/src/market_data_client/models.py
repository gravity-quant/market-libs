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
collapse it to ``0.0``). Nested :class:`MarketDataEntry` rows carry no
``received_at``.

This module is a package-local copy of the higyrus ``SafeModel`` / ``_coerce``
implementation (D-03): the no-shared-internals constraint forbids importing any
symbol from ``higyrus_client``.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from types import NoneType, UnionType
from typing import Any, Self, Union, cast, get_args, get_origin, get_type_hints

__all__ = ["LatestRequest", "MarketDataEntry", "MarketDataSnapshot", "SafeModel"]


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
class MarketDataEntry(SafeModel):
    """A single market-data entry row nested inside a :class:`MarketDataSnapshot`.

    PROVISIONAL shape (A1/A2 — OpenAPI not vendored; Phase 23 reconciles field
    names against real payloads). A plain :class:`SafeModel` subclass: it carries
    NO ``received_at`` (only the top-level snapshot is client-stamped).
    """

    entryType: str
    price: float
    size: float


@dataclass(frozen=True, slots=True)
class MarketDataSnapshot(SafeModel):
    """A market-data snapshot returned by the ``/marketdata`` read endpoints.

    PROVISIONAL wire shape (A1/A2 — OpenAPI not vendored; Phase 23 reconciles).
    ``received_at`` is a first-class, CLIENT-STAMPED field (D-01): it is injected
    by :meth:`from_api` as a keyword and never coerced from the payload.
    """

    symbol: str
    marketId: str
    entries: list[MarketDataEntry]
    received_at: float

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
