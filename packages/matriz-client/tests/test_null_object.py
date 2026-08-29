"""Null Object contract for ``matriz_client.models`` — NOBJ-01, Phase 35.

This paquete is the one hierarchy that already carried ``empty()`` before this
phase (Phase 29 shipped it), so Phase 35's source change here is ``__bool__``
alone. The suite pins five things:

1. Every shipped :class:`~matriz_client.models._SafeModel` subclass is **falsy**
   when it carries nothing, and ``Model.from_api(None) == Model.empty()``
   (ROADMAP Phase 35 criterio 1).
2. Every one of those classes becomes **truthy** the moment a single field
   differs from its empty value — truthiness is a field-level emptiness test,
   never a snapshot-level one.
3. ``empty()`` emits **zero** divergence records (T-29-33): it does not decode
   wire data, so it must not report substituted defaults.
4. :class:`~matriz_client.models.UnknownFrame` answers the same question the
   same way even though it sits OUTSIDE the base hierarchy — see the two
   dedicated cases at the bottom and the reasoning written there (D-08).
5. A read-only ``@property`` alias declared next to the wire fields of a
   ``frozen=True`` dataclass is **invisible** to :func:`typing.get_type_hints`
   and therefore to the walker — the invariant phases 36-38 depend on when they
   add ``last`` / ``bids`` aliases (ROADMAP Phase 35 criterio 5, D-16).

The class roster is obtained by **introspection of the real module**, never
from a hand-written fixture list (D-15): a fixture roster would keep passing on
the day a shipped model stops honouring the contract.

Both helpers below (``_safemodel_classes`` and ``_perturb``) and the two alias
fixture dataclasses are **module-local copies on purpose**. This monorepo has
no shared internal package by design, and the copies must not be replaced by an
import from another paquete nor from the repo-root harness: a helper shared
across paquetes would introduce exactly the cross-package coupling repo policy
forbids.

The alias fixtures are declared ``frozen=True`` **without** ``slots``, because
that is this paquete's convention (semantics matrix row 5, difference 5) and
criterio 5 has to be proven on the shape this paquete actually ships.
"""

from __future__ import annotations

import dataclasses
import inspect
import logging
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any, get_type_hints

import pytest

from matriz_client import _decode, models
from matriz_client._decode import POLICY, DecodeScope, walk_model
from matriz_client.models import UnknownFrame, _SafeModel

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
    """Every shipped ``_SafeModel`` subclass of THIS paquete, by introspection.

    The base is private here and the filter references it directly rather than
    duck-typing around the leading underscore: this module lives inside the
    paquete, so reaching for the real base is the honest test, and a duck-typed
    predicate would also sweep in :class:`UnknownFrame`, which is covered
    separately and deliberately.

    The defining-module filter in the last condition is load-bearing: without
    it any subclass merely re-exported into ``models``' namespace would enter
    the roster and be asserted against as if this paquete shipped it.
    """
    return sorted(
        (
            obj
            for _, obj in inspect.getmembers(models, inspect.isclass)
            if issubclass(obj, _SafeModel)
            and obj is not _SafeModel
            and dataclasses.is_dataclass(obj)
            and obj.__module__ == models.__name__
        ),
        key=lambda c: c.__name__,
    )


def _perturb(empty: Any) -> Any:
    """Return a copy of ``empty`` differing from it in exactly one field.

    Branch order is load-bearing, and this is the paquete where it earns its
    keep: nearly every field declared here is Optional with a ``None`` default,
    so a helper that dispatched on ``str`` first would fall through on almost
    the whole roster and cover it vacuously. ``cur is None`` is therefore
    tested FIRST.

    The trailing nested-model branch handles the other half of the same
    problem: a nested-model field's empty value is a nested empty INSTANCE, not
    ``None`` (``Instrument.instrumentId`` is this paquete's example), so those
    are perturbed recursively.

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
        if isinstance(cur, _SafeModel):
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

    Driving the walker directly rather than through ``from_api`` keeps the
    record list the WALKER's, so a ``from_api`` override could not quietly
    change what this module measures.
    """
    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="matriz_client"):
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


@dataclass(frozen=True)
class _Leaf(_SafeModel):
    """Nested leaf shared by both halves of the alias pair."""

    price: float | None = None
    size: int | None = None


@dataclass(frozen=True)
class _AliasShaped(_SafeModel):
    """The exact shape phases 36-38 introduce: wire fields + a read-only alias."""

    LA: _Leaf = field(default_factory=_Leaf.empty)
    BI: list[_Leaf] = field(default_factory=list)

    @property
    def last(self) -> _Leaf:
        """Human-facing alias over the wire-named field (D-16)."""
        return self.LA


@dataclass(frozen=True)
class _AliasFree(_SafeModel):
    """The identical wire fields, with no property alias — the control."""

    LA: _Leaf = field(default_factory=_Leaf.empty)
    BI: list[_Leaf] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Criterio 1 — the roster is real
# ---------------------------------------------------------------------------


def test_the_model_roster_is_not_vacuous() -> None:
    """An empty roster would make every parametrized test below pass vacuously.

    ``>= 17`` rather than ``== 17``: 17 is the count measured for this paquete
    in ``35-RESEARCH.md`` F-1, and phases 36-38 may legitimately add classes.
    Every class is also asserted individually, so the guard only has to catch
    the catastrophic case where introspection returns nothing at all.
    """
    assert len(_safemodel_classes()) >= 17


@pytest.mark.parametrize("cls", _safemodel_classes(), ids=lambda c: c.__name__)
def test_every_shipped_model_is_falsy_when_empty(cls: type) -> None:
    """NOBJ-01: a model carrying nothing answers ``False`` to ``bool()``."""
    assert bool(cls.from_api(None)) is False  # type: ignore[attr-defined]
    assert cls.from_api(None) == cls.empty()  # type: ignore[attr-defined]


@pytest.mark.parametrize("cls", _safemodel_classes(), ids=lambda c: c.__name__)
def test_every_shipped_model_is_truthy_when_populated(cls: type) -> None:
    """NOBJ-01, the falsification half: one differing field is enough."""
    assert bool(_perturb(cls.empty())) is True  # type: ignore[attr-defined]


@pytest.mark.parametrize("cls", _safemodel_classes(), ids=lambda c: c.__name__)
def test_empty_emits_nothing(cls: type, caplog: pytest.LogCaptureFixture) -> None:
    """T-29-33 / D-07: ``empty()`` does not decode wire data, so it reports nothing."""
    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="matriz_client"):
        instance = cls.empty()  # type: ignore[attr-defined]

    assert instance is not None
    assert _divergences(caplog) == []


# ---------------------------------------------------------------------------
# Criterio 1, the outlier — `UnknownFrame` is outside the roster ON PURPOSE
# ---------------------------------------------------------------------------
#
# `UnknownFrame` does not inherit the base, so the introspection filter above
# cannot see it — and that exclusion is correct, not a bug in the filter. The
# class is exempt from the walker entirely (semantics matrix Section 3(c)):
# under a naive extra-key rule every key of an unmodelled frame would be
# "extra", but those keys are a deliberate catch-all. What it is NOT exempt
# from is the truthiness contract: it is a member of the public
# `PrimaryWsMessage` union, so `if frame:` has to read the same for every
# variant a caller can receive (D-08). Hence a hand-written `__bool__` on the
# class and the two by-name cases below. A future reader tempted to "fix" the
# roster filter so it swallows this class should read this comment first.


def test_UnknownFrame_is_falsy_when_empty() -> None:
    """D-08: the union's catch-all variant answers ``False`` when it carries nothing."""
    assert bool(UnknownFrame.empty()) is False
    assert bool(UnknownFrame.from_api(None)) is False
    assert UnknownFrame.from_api(None) == UnknownFrame.empty()


def test_UnknownFrame_is_truthy_when_it_carries_a_frame_type() -> None:
    """D-08: a frame that preserved a real payload is truthy, like every sibling."""
    frame = UnknownFrame.from_api({"type": "brandNew", "someField": 1})

    assert frame.type == "brandNew"
    assert bool(frame) is True


# ---------------------------------------------------------------------------
# Criterio 5 — @property aliases are invisible to the walker (D-16)
# ---------------------------------------------------------------------------


def test_property_aliases_are_invisible_to_get_type_hints() -> None:
    """``get_type_hints`` reports every DECLARED annotation, and the alias is not one.

    One adaptation this paquete forces and the tracer did not: its base declares
    ``__dataclass_fields__`` as a ``ClassVar`` so the type-checker will accept
    ``cls`` as a dataclass. That annotation is real, so ``get_type_hints``
    reports it, while ``dataclasses.fields`` correctly omits it — and the walker
    enumerates the latter. The subtraction below is therefore pinned as an
    equality against that one known name rather than waved away: if a second
    non-field annotation ever appears on the base, this test says so.

    The property is in neither collection, which is the invariant phases 36-38
    depend on.
    """
    hints = get_type_hints(_AliasShaped)
    declared = {f.name for f in dataclasses.fields(_AliasShaped)}

    assert declared <= set(hints)
    assert set(hints) - declared == {"__dataclass_fields__"}
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
