"""Bidirectional SafeModel-vs-wire diff helper (D-MATZ-18, D-HIGY-4 promoted).

Promoted from the inline copy that lived in ``main_higyrus.py`` (Phase 4) to a
shared module under ``verification/`` so any Phase 5+ driver can import it
directly. The single behavioural difference vs. the inline original is
**duck-typed cross-package compatibility**: rather than importing the
``higyrus_client.SafeModel`` base class to detect nested models, the helper
relies on the structural triple
``(isinstance(cls, type), dataclasses.is_dataclass(cls), callable(cls.from_api))``.
This lets the same helper diff both ``higyrus_client.SafeModel`` and
``matriz_client._SafeModel`` instances without introducing cross-package
coupling between paquetes-cliente (forbidden by repo policy).

Direction semantics (mirror Phase 4 D-HIGY-5):

- ``'model-only'`` -- key declared by the model but absent on the wire payload.
  This is a FALSE PASS risk: ``Model.from_api(payload)`` substitutes a typed
  default and never raises, so the driver caller must surface this as a
  ``SHAPE`` finding.
- ``'wire-only'`` -- key present on the wire but absent from the model. Info
  only; the upstream API may have added a field.

Recursion follows nested SafeModel-like dataclasses, ``list[SafeModel-like]`` and
``Mapping[str, ...]`` -- including a mapping of mappings -- sampling one element
per container, consistent with :func:`verification.schema.schema_of`.

**The mapping arm was added by the Phase 37 code review (WR-06).** Without it
``_nested_safemodel_class`` handled bare models, ``list[Model]`` and
``Optional[...]`` and nothing else, so every model that phase introduced --
``TickPriceRange``, ``InstrumentPositionReport``, ``DetailedAccountReport``, all
three of them sitting behind a mapping -- was structurally invisible to this
helper, and therefore to probe 20 of ``main_matriz.py``. Those models' own
docstrings meanwhile pointed at a live run as the mechanism that would eventually
MEASURE their deferred subtrees. This was the mechanism, and it could not see
them.

**LINK vs LEAF (Phase 36 code review, CR-01).** ``'model-only'`` is a false-pass
signal only for a scalar LEAF, where the walker really does substitute a typed
zero the caller cannot distinguish from data. A non-optional field whose declared
type is a nested SafeModel-like or ``list[SafeModel-like]`` is a Null Object LINK,
and Phase 35's NOBJ-02 policy makes its ``null``/absent value a legitimate payload
shape that collapses to the empty instance / ``[]`` and emits NOTHING. Recursion
turning on for such a field must therefore not manufacture a divergence the
decoder itself declares not to be one -- otherwise the differ and the walker
disagree about the same fact. This became load-bearing when
``MarketDataSnapshot.market_data`` stopped being an opaque ``dict`` (which
suppressed recursion by accident) and became the typed
``MarketDataEntries``, six of whose ten roster fields are non-optional links.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Iterator, Mapping
from types import NoneType, UnionType
from typing import Any, Union, get_args, get_origin, get_type_hints

__all__ = ["diff_safemodel_bidirectional"]


def _is_optional(hint: Any) -> bool:
    """Return True if ``hint`` is ``Optional[T]`` / ``T | None``.

    Optional fields opt explicitly into nullability — their absence on the wire
    is the intended representation, not a divergence.
    """
    origin = get_origin(hint)
    if origin is Union or origin is UnionType:
        return any(a is NoneType for a in get_args(hint))
    return False


def _is_safemodel_like(cls: Any) -> bool:
    """Duck-typed check: ``cls`` is a SafeModel-like dataclass.

    True iff ``cls`` is a type, is a dataclass, and exposes a callable
    ``from_api`` classmethod. This admits both
    ``higyrus_client.models.SafeModel`` subclasses and
    ``matriz_client.models._SafeModel`` subclasses without importing either
    package (cross-package coupling is forbidden by repo policy).
    """
    return (
        isinstance(cls, type)
        and dataclasses.is_dataclass(cls)
        and callable(getattr(cls, "from_api", None))
    )


def _nested_safemodel_class(hint: Any) -> type | None:
    """Return the nested SafeModel-like class for ``hint`` or None.

    Handles both bare ``SafeModelLike`` and ``list[SafeModelLike]`` shapes.
    Unwraps ``Optional[T]`` first so ``segment: Segment | None`` still recurses.
    """
    origin = get_origin(hint)
    if origin is Union or origin is UnionType:
        for arg in get_args(hint):
            if arg is NoneType:
                continue
            nested = _nested_safemodel_class(arg)
            if nested is not None:
                return nested
        return None
    if _is_safemodel_like(hint):
        return hint  # type: ignore[no-any-return]
    if origin is list:
        args = get_args(hint)
        if args and _is_safemodel_like(args[0]):
            return args[0]  # type: ignore[no-any-return]
    return None


def _is_list_of_safemodel(hint: Any) -> bool:
    """Return True if ``hint`` is ``list[X]`` with ``X`` SafeModel-like."""
    return get_origin(hint) is list and _nested_safemodel_class(hint) is not None


def _strip_optional(hint: Any) -> Any:
    """Return ``T`` from ``T | None`` / ``Optional[T]``; pass through otherwise."""
    if _is_optional(hint):
        args = [a for a in get_args(hint) if a is not NoneType]
        if len(args) == 1:
            return args[0]
    return hint


def _mapping_value_hint(hint: Any) -> Any | None:
    """The declared VALUE hint of a mapping annotation, or ``None``.

    Phase 37 code review, WR-06. ``_nested_safemodel_class`` handles bare models,
    ``list[Model]`` and ``Optional[...]`` and had **no mapping branch**, so all
    three models Phase 37 introduced -- ``TickPriceRange``,
    ``InstrumentPositionReport`` and ``DetailedAccountReport``, every one of them
    sitting behind a mapping -- were structurally invisible to
    :func:`diff_safemodel_bidirectional`, i.e. to probe 20 of the live driver.
    Their own docstrings meanwhile promised that "widening the roster is the
    right answer once a live run MEASURES one of those keys": the differ was the
    only mechanism that could ever measure them, and it could not see them.

    Deliberately a SEPARATE function from ``_nested_safemodel_class`` rather than
    a branch inside it, because the two answers are used for different decisions
    and only one of them transfers. ``_nested_safemodel_class`` also gates the
    direction-A skip, whose justification (Phase 36 CR-01 / NOBJ-02) is that an
    absent LINK collapses to its empty instance and emits **NOTHING** -- so
    reporting it would contradict the decoder. That justification does NOT hold
    for a mapping: matriz's mapping axis emits a ``missing`` divergence for an
    absent mapping field, so an absent mapping IS a divergence both halves agree
    on, and the differ must keep reporting it. Folding the mapping branch into
    ``_nested_safemodel_class`` would have silently suppressed those.

    Recognises the same vocabulary the runtime axis does (``dict``, ``Mapping``,
    ``MutableMapping``, ``defaultdict``, ...) via a subclass test, for the reason
    WR-01 gives: two hardcoded lists drift, a structural test cannot.
    """
    inner = _strip_optional(hint)
    origin = get_origin(inner)
    if not (isinstance(origin, type) and issubclass(origin, Mapping)):
        return None
    args = get_args(inner)
    return args[1] if len(args) == 2 else None


def _descend(payload: Any, hint: Any, path: str) -> Iterator[tuple[str, str, str]]:
    """Diff ``payload`` against whatever SafeModel-like sits under ``hint``.

    One entry point for all three container shapes the differ descends, so a
    fourth shape is added in one place instead of three. Each container samples
    ONE element, consistent with :func:`verification.schema.schema_of` and with
    the ``list[Model]`` behaviour that predates this function.

    The mapping segment is rendered ``{}`` -- index-free, matching both the
    ``[0]`` convention here and the decode walker's own ``{}`` marker for mapping
    elements (models.py ``_mapping_value``, WR-04). A key sampled out of an
    open-keyed payload is data, not schema, and putting it in the path would make
    the same structural finding read as N different ones.
    """
    value_hint = _mapping_value_hint(hint)
    if value_hint is not None:
        if isinstance(payload, dict) and payload:
            first = next(iter(payload.values()))
            yield from _descend(first, value_hint, f"{path}{{}}")
        # Empty mapping: nothing to sample, no finding — same as an empty list.
        return

    nested_cls = _nested_safemodel_class(hint)
    if nested_cls is None:
        return
    if _is_list_of_safemodel(hint):
        if isinstance(payload, list) and payload:
            yield from diff_safemodel_bidirectional(payload[0], nested_cls, f"{path}[0]")
        # Empty list: no recursion, no finding.
        return
    yield from diff_safemodel_bidirectional(payload, nested_cls, path)


def diff_safemodel_bidirectional(
    payload: Any,
    model_cls: type,
    path: str = "",
) -> Iterator[tuple[str, str, str]]:
    """Yield ``(path, direction, key)`` tuples for each model<->wire divergence.

    ``direction`` is one of:

    - ``'model-only'`` (FALSE PASS risk): key declared by the model but absent
      on the wire payload. ``SafeModel.from_api`` substitutes a typed default
      and never raises, so the driver should surface this as a ``SHAPE``
      finding with the ``(FALSE PASS riesgo)`` prefix. Emitted for scalar
      LEAVES only -- a non-optional Null Object LINK (nested SafeModel-like or
      ``list[SafeModel-like]``) is skipped, per NOBJ-02; see the module
      docstring.
    - ``'wire-only'`` (info): key present on the wire but absent from the
      model. Likely a new field added upstream.

    Recursion descends nested SafeModel-like dataclasses and
    ``list[SafeModel-like]`` (sampling the first element, consistent with
    :func:`verification.schema.schema_of`).

    Non-dict payloads short-circuit silently — :meth:`SafeModel.from_api`
    would also substitute ``{}`` without diffing in that case.
    """
    if not isinstance(payload, dict):
        return

    # Restringimos las keys del model a los instance fields del dataclass
    # (excluye ClassVar y atributos declarados a nivel de clase, como el
    # ``__dataclass_fields__: ClassVar[...]`` que ``matriz_client._SafeModel``
    # declara para pyright). Sin este filtro, el diff emitiria
    # ``model-only=__dataclass_fields__`` cross-package, un falso positivo.
    hints = get_type_hints(model_cls)
    field_names = {f.name for f in dataclasses.fields(model_cls)}
    model_keys = field_names & hints.keys()
    wire_keys = set(payload.keys())

    # Direction A: model declara, wire no emite -- FALSE PASS riesgo.
    for key in sorted(model_keys - wire_keys):
        hint = hints[key]
        # Optional[T] / T | None es opt-in explicito a nullable; ausencia es la
        # representacion intencional. NO emitir direction A para opcionales.
        if _is_optional(hint):
            continue
        # NOBJ-02 (Phase 35): un LINK Null Object -- campo NO opcional cuyo tipo
        # declarado es un SafeModel-like anidado o ``list[SafeModel-like]`` --
        # colapsa a su instancia vacia / ``[]`` SIN emitir nada en el walker.
        # Una ausencia ahi es una forma de payload legitima, no una divergencia,
        # asi que reportarla seria un FALSE-PASS fabricado que contradice la
        # politica que el propio decoder aplica. Solo las HOJAS escalares pueden
        # ser un false pass: el walker SI les sustituye un cero tipado.
        if _nested_safemodel_class(hint) is not None:
            continue
        yield (path, "model-only", key)

    # Direction B: wire emite, model no declara -- info only.
    for key in sorted(wire_keys - model_keys):
        yield (path, "wire-only", key)

    # Recursion: descender en nested SafeModel-like, list[SafeModel-like] y
    # -- desde el code review de la Phase 37 (WR-06) -- mapping[str, ...],
    # incluido el anidado a dos niveles. Toda la dispatch vive en ``_descend``.
    for key in model_keys & wire_keys:
        yield from _descend(payload[key], hints[key], f"{path}.{key}")
