"""Null Object contract for ``market_data_client.models`` — NOBJ-01, Phase 35.

The market-data copy of the contract the tracer paquete pinned first (plan
35-01). It asserts the same four things, over this paquete's own shipped
classes:

1. Every shipped :class:`~market_data_client.models.SafeModel` subclass is
   **falsy** when it carries nothing, and ``Model.from_api(None) ==
   Model.empty()`` (ROADMAP Phase 35 criterio 1).
2. Every one of those classes becomes **truthy** the moment a single field
   differs from its empty value — truthiness is a field-level emptiness test,
   never a snapshot-level one.
3. ``empty()`` emits **zero** divergence records (T-29-33): it does not decode
   wire data, so it must not report substituted defaults.
4. A read-only ``@property`` alias declared next to the wire fields of a
   ``frozen=True, slots=True`` dataclass is **invisible** to
   :func:`typing.get_type_hints` and therefore to the walker — the invariant
   Phase 36 depends on when it gives ``MarketDataEntries`` / ``BookLevel``
   their ``last`` / ``bids`` aliases (ROADMAP Phase 35 criterio 5, D-16).

market-data takes **form B** of D-07: this paquete's ``from_api`` carries a
mapping pass, so its ``empty()`` carries the same pass with a silent sink. That
delta against the form-A paquetes is a declared per-paquete policy axis
(``29-SEMANTICS-MATRIX.md``, "never harmonize"), not a divergence to close.

The roster is obtained by **introspection of the real module**, never from a
hand-written fixture list (D-15). The filter is also what keeps the seven
serialize-OUT request dataclasses (``LatestRequest``, ``NewSymbol``,
``NewSymbols``, ``SymbolPatch``, ``MarketHoursIn``, ``HolidayIn``,
``HolidaysIn``) out of scope without a hand-maintained deny-list: none of them
subclasses the base, because they are input, not output (D-08).

Both helpers below (``_safemodel_classes`` and ``_perturb``) and the two alias
fixture dataclasses are **module-local copies on purpose**. This monorepo has
no shared internal package by design, and the copies must not be replaced by an
import from another paquete nor from the repo-root harness — the same rationale
``safemodel_diff`` states in its own docstring: a helper shared across paquetes
would introduce exactly the cross-package coupling repo policy forbids.
"""

from __future__ import annotations

import dataclasses
import inspect
import logging
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, get_type_hints

import pytest

from market_data_client import _decode, models
from market_data_client._decode import POLICY, DecodeScope, walk_model
from market_data_client.models import SafeModel

_MESSAGE = "decode divergence"


@pytest.fixture(autouse=True)
def _pristine_decode_context() -> Iterator[None]:
    """Start every test in this module with an unbound decode mode and scope.

    Copied from ``test_decode.py`` for the same reason it exists there: once any
    test in the session drives a real ``_request``, the sync test context keeps
    that request's ``DECODE_SCOPE`` (and possibly ``STRICT_DECODE``) bound, and
    a later bare ``Model.from_api(None)`` would either join a stale dedupe set
    or raise under an inherited strict mode — turning assertions in this module
    green-or-red purely on test ORDER.
    """
    mode = _decode.STRICT_DECODE.get()
    scope = _decode.DECODE_SCOPE.get()
    _decode.STRICT_DECODE.set(False)
    _decode.DECODE_SCOPE.set(None)
    try:
        yield
    finally:
        _decode.STRICT_DECODE.set(mode)
        _decode.DECODE_SCOPE.set(scope)


# ---------------------------------------------------------------------------
# Roster + perturbation helpers (module-local copies — see module docstring)
# ---------------------------------------------------------------------------


def _safemodel_classes() -> list[type]:
    """Every shipped ``SafeModel`` subclass of THIS paquete, by introspection.

    The defining-module filter in the last condition below is load-bearing:
    without it any ``SafeModel`` subclass merely re-exported into ``models``'
    namespace would enter the roster and be asserted against as if it were
    shipped by this paquete.
    """
    return sorted(
        (
            obj
            for _, obj in inspect.getmembers(models, inspect.isclass)
            if issubclass(obj, models.SafeModel)
            and obj is not models.SafeModel
            and dataclasses.is_dataclass(obj)
            and obj.__module__ == models.__name__
        ),
        key=lambda c: c.__name__,
    )


def _perturb(empty: Any) -> Any:
    """Return a copy of ``empty`` differing from it in exactly one field.

    Branch order is load-bearing. ``cur is None`` is tested FIRST because a
    class whose every field is Optional-with-``None``-default has no non-``None``
    value to dispatch on, and every later branch would fall through, covering
    the class vacuously.

    The trailing nested-model branch is carried over from the 35-01 tracer
    (deviation 1): a nested-model field's empty value in these paquetes is a
    nested empty INSTANCE rather than ``None``, so a class whose only fields are
    nested models offers nothing the earlier branches can dispatch on.

    Falling off the end raises rather than returning ``empty`` unchanged: a
    class this helper cannot perturb must fail loudly instead of silently
    turning ``test_every_shipped_model_is_truthy_when_populated`` vacuous.
    """
    for f in dataclasses.fields(empty):
        cur = getattr(empty, f.name)
        if cur is None:
            return dataclasses.replace(empty, **{f.name: "SENTINEL"})
        if isinstance(cur, str):
            return dataclasses.replace(empty, **{f.name: "SENTINEL"})
        if isinstance(cur, bool):
            return dataclasses.replace(empty, **{f.name: not cur})
        if isinstance(cur, int | float):
            return dataclasses.replace(empty, **{f.name: cur + 1})
        if isinstance(cur, list):
            return dataclasses.replace(empty, **{f.name: ["SENTINEL"]})
        if isinstance(cur, dict):
            return dataclasses.replace(empty, **{f.name: {"k": "v"}})
        if isinstance(cur, SafeModel):
            return dataclasses.replace(empty, **{f.name: _perturb(cur)})
    raise AssertionError(f"no perturbable field on {type(empty).__name__}")


def _divergences(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    """Every divergence record captured so far, in emission order."""
    return [r for r in caplog.records if r.getMessage() == _MESSAGE]


def _walk(
    cls: type,
    payload: Any,
    caplog: pytest.LogCaptureFixture,
) -> tuple[Any, list[logging.LogRecord]]:
    """Walk ``payload`` into ``cls`` with a fresh scope, returning instance + records.

    Copied from ``test_decode.py``. Driving the walker directly rather than
    through ``from_api`` keeps the record list the WALKER's, so a ``from_api``
    override could not quietly change what this module measures.
    """
    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="market_data_client"):
        kwargs = walk_model(cls, payload, policy=POLICY, sink=DecodeScope())
    return cls(**kwargs), _divergences(caplog)


def _records(records: list[logging.LogRecord]) -> list[tuple[str, str, str, str]]:
    """Project records onto the four class-independent contract keys.

    The ``model`` key is deliberately excluded: the criterio-5 pair below
    compares an alias-carrying class against its alias-free twin, and those two
    necessarily disagree on their own class name and on nothing else.
    """
    return [
        (r.field_path, r.divergence, r.declared_type, r.observed_type)  # type: ignore[attr-defined]
        for r in records
    ]


# ---------------------------------------------------------------------------
# Module-local fixtures for the criterio-5 pair (D-16)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _Leaf(SafeModel):
    """Nested leaf shared by both halves of the alias pair."""

    nombre: str
    dias: int


@dataclass(frozen=True, slots=True)
class _AliasShaped(SafeModel):
    """The exact shape Phase 36 introduces: wire fields + a read-only alias."""

    LA: _Leaf
    BI: list[_Leaf]

    @property
    def last(self) -> _Leaf:
        """Human-facing alias over the wire-named field (D-16)."""
        return self.LA


@dataclass(frozen=True, slots=True)
class _AliasFree(SafeModel):
    """The identical wire fields, with no property alias — the control."""

    LA: _Leaf
    BI: list[_Leaf]


# ---------------------------------------------------------------------------
# Criterio 1 — the roster is real
# ---------------------------------------------------------------------------


def test_the_model_roster_is_not_vacuous() -> None:
    """An empty roster would make every parametrized test below pass vacuously.

    ``>= 16`` rather than ``== 16``: 16 is the count measured for market-data in
    ``35-RESEARCH.md`` F-1, and Phase 36 legitimately adds three more classes
    (``MarketDataEntries``, ``BookLevel``, ``EntryValue``). Every class is also
    asserted individually, so the guard only has to catch the catastrophic case
    where introspection returns nothing at all.
    """
    assert len(_safemodel_classes()) >= 16


@pytest.mark.parametrize("cls", _safemodel_classes(), ids=lambda c: c.__name__)
def test_every_shipped_model_is_falsy_when_empty(cls: type) -> None:
    """NOBJ-01: a model carrying nothing answers ``False`` to ``bool()``.

    One case in this roster carries a caveat that the assertion deliberately
    does NOT weaken (D-09, RESEARCH Pitfall 8). ``MarketDataSnapshot`` is falsy
    here only because its ``from_api`` defaults the client-stamped
    ``received_at`` to ``0.0`` on this code path; the shipped client always
    passes a wall-clock stamp, so a snapshot decoded in production differs from
    its ``empty()`` and is truthy even when the wire carried nothing. The green
    below is therefore **structural, not semantic**: it pins that the walker
    substitutes nothing extra, and callers asking "is this snapshot empty?" must
    ask it of the FIELD (``snapshot.entries``, ``snapshot.market_data``), never
    of the envelope.
    """
    assert bool(cls.from_api(None)) is False  # type: ignore[attr-defined]
    assert cls.from_api(None) == cls.empty()  # type: ignore[attr-defined]


@pytest.mark.parametrize("cls", _safemodel_classes(), ids=lambda c: c.__name__)
def test_every_shipped_model_is_truthy_when_populated(cls: type) -> None:
    """NOBJ-01, the falsification half: one differing field is enough."""
    assert bool(_perturb(cls.empty())) is True  # type: ignore[attr-defined]


@pytest.mark.parametrize("cls", _safemodel_classes(), ids=lambda c: c.__name__)
def test_empty_emits_nothing(cls: type, caplog: pytest.LogCaptureFixture) -> None:
    """T-29-33 / D-07: ``empty()`` does not decode wire data, so it reports nothing.

    Form B is the reason this test earns its keep in this paquete specifically:
    ``empty()`` here runs a mapping pass on top of the walk, and that pass has
    its own sink argument. Handing it anything but the silent sink would emit one
    ``missing`` record per mapping-declared field on every call.
    """
    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="market_data_client"):
        instance = cls.empty()  # type: ignore[attr-defined]

    assert instance is not None
    assert _divergences(caplog) == []


def test_empty_and_from_api_agree_on_every_mapping_declared_field() -> None:
    """Form B's whole point: the two constructors cannot disagree on a dict field.

    ``MarketDataSnapshot`` is the one shipped class declaring a mapping-typed
    field. If ``empty()`` skipped the mapping pass that ``from_api`` runs, the
    two would produce different values for that field and every ``__bool__``
    comparison against it would answer on the delta rather than on the payload.
    """
    assert models.MarketDataSnapshot.empty().market_data == (
        models.MarketDataSnapshot.from_api(None).market_data
    )


# ---------------------------------------------------------------------------
# Criterio 5 — @property aliases are invisible to the walker (D-16)
# ---------------------------------------------------------------------------


def test_property_aliases_are_invisible_to_get_type_hints() -> None:
    """``get_type_hints`` returns the declared fields and nothing else."""
    hints = get_type_hints(_AliasShaped)

    assert set(hints) == {f.name for f in dataclasses.fields(_AliasShaped)}
    assert "last" not in hints


def test_adding_a_property_alias_does_not_change_the_divergence_count(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The alias cannot fabricate a divergence nor suppress one (criterio 5).

    The invariant asserted is EQUALITY between the alias-carrying class and its
    alias-free twin, never an absolute record count: plan 35-05 changes what the
    walker emits for a non-optional link carrying nothing, and this test must
    survive that change untouched. If it ever reddens, the alias itself became
    visible to the walker — which is the only thing it is here to detect.
    """
    shaped, shaped_records = _walk(_AliasShaped, {}, caplog)
    free, free_records = _walk(_AliasFree, {}, caplog)

    assert _records(shaped_records) == _records(free_records)
    assert shaped.LA == free.LA
    assert shaped.BI == free.BI
    assert shaped.last is shaped.LA
