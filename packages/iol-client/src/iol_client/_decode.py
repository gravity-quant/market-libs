"""The canonical per-field decode walker for iol-client (Phase 29, DEC-01).

Every response model in this paquete is built by walking the declared field
list and substituting a typed default whenever the wire disagrees with the
declaration. Until Phase 29 that substitution was silent: ``_coerce`` detected
the mismatch and threw the fact away. This module returns exactly the same
value and **additionally reports what it saw**, as a structured record on the
paquete logger.

Who imports it: **nothing in production yet.** ``iol_client`` has no ``models``
module until Phase 30, when the typed surface lands and its ``from_api``
delegates to :func:`walk_model`. The copy arriving *before* the models it will
serve is deliberate: Phase 30 inherits a working, tested decoder instead of
bootstrapping one mid-phase, and a package with no ``models`` module is the
strongest available evidence that the walker has no hidden coupling to one.
This module MUST NOT import ``models`` — that would be
an import cycle, and two of the five paquetes that receive this same file have
no ``models`` module at all. A nested model is therefore detected **duck-typed**
(:func:`_is_model`), the same predicate ``verification/safemodel_diff.py`` and
matriz's own converter already use.

The two behaviours the walker adds over ``_coerce``:

- **reporting** — a sink call immediately before every substituted default;
- **extra wire keys** — undetectable inside ``_coerce``, which never sees the
  payload's own key set. That capability lives in :func:`walk_model`.

Policy lives in :data:`POLICY`, transcribed from ``29-SEMANTICS-MATRIX.md``
Section 2. Record schema, dedupe triple, level map, strict-mode disposition and
emitter safety are the twelve locks of ``29-AGGREGATION-CONTRACT.md``.
``Literal`` membership is **never** enforced on a RESPONSE field — see
``29-DLOCK-RESPONSE-LITERAL.md`` (D-09).

This module is duplicated per paquete **by design** and is NOT importable from
``verification/`` (the "no shared internals between packages" constraint). The
only per-paquete deltas are the paquete name in this docstring, the
:data:`POLICY` assignment, the :data:`_LOGGER_NAME` literal and the decode
exception imported from ``exceptions``; Plan 09's intactness check normalizes
exactly those away.
"""

from __future__ import annotations

import contextlib
import logging
from contextvars import ContextVar
from dataclasses import dataclass, fields, is_dataclass
from functools import lru_cache
from types import NoneType, UnionType
from typing import Any, Literal, Union, cast, get_args, get_origin, get_type_hints

from iol_client.exceptions import IOLDecodeError

__all__ = [
    "DECODE_SCOPE",
    "POLICY",
    "SILENT_SINK",
    "STRICT_DECODE",
    "DecodePolicy",
    "DecodeScope",
    "current_sink",
    "hints_for",
    "open_request_scope",
    "walk_field",
    "walk_model",
]


# ---------------------------------------------------------------------------
# Record vocabulary (aggregation contract locks 1-3)
# ---------------------------------------------------------------------------

_LOGGER_NAME = "iol_client"
_LOGGER = logging.getLogger(_LOGGER_NAME)

# Lock 1: the message is a constant with no interpolation and no %-args — every
# variable part of the record travels in ``extra``.
_DIVERGENCE_MESSAGE = "decode divergence"

# Lock 1: six flat all-str keys, none of which is a reserved ``LogRecord``
# attribute. ``Logger.makeRecord`` raises ``KeyError`` on a collision, which
# would turn observable mode into fatal mode for every caller — the precise
# inversion of this phase. The two most natural names, ``module`` and ``name``,
# are both reserved.
_RECORD_KEYS = (
    "package",
    "divergence",
    "field_path",
    "declared_type",
    "observed_type",
    "model",
)

# Lock 3: an extra wire key is normal vendor growth, not a defect.
_INFO_KINDS = frozenset({"extra"})


# ---------------------------------------------------------------------------
# Policy (29-SEMANTICS-MATRIX.md Section 2)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DecodePolicy:
    """The seven declared semantic axes of one paquete's ``from_api``.

    The class body is identical in all five copies; only :data:`POLICY`'s value
    differs. Every per-paquete difference is a *declared* axis with a
    ``file:line`` citation in the matrix — never an inconsistency awaiting
    cleanup. There is no unparameterized path in the walker, so harmonizing a
    cell requires editing a named constant in a named paquete, which is visible
    in review.
    """

    missing_str: str | None
    missing_int: int | None
    missing_float: float | None
    missing_bool: bool | None
    non_dict_model: str
    scalar_passthrough: bool
    literal_enforced: bool


# higyrus-client row of 29-SEMANTICS-MATRIX.md Section 2. One of the four lines
# Plan 09's intactness check normalizes away.
POLICY = DecodePolicy("", 0, 0.0, False, "from_api_none", False, False)


# ---------------------------------------------------------------------------
# Emission
# ---------------------------------------------------------------------------


def _emit(model: str, path: str, kind: str, declared: str, observed: str) -> None:
    """Emit one divergence record. Lock 9: NEVER raises into the decode path."""
    extra = {
        "package": _LOGGER_NAME,
        "divergence": kind,
        "field_path": path,
        "declared_type": declared,
        "observed_type": observed,
        "model": model,
    }
    # Lock 9: a failure inside ``logging``, inside a consumer handler or inside
    # a consumer filter must never propagate. A library that previously
    # substituted silently must not begin crashing on the divergences it was
    # added to merely report — least of all from third-party handler code.
    with contextlib.suppress(Exception):
        if kind in _INFO_KINDS:
            _LOGGER.info(_DIVERGENCE_MESSAGE, extra=extra)
        else:
            _LOGGER.warning(_DIVERGENCE_MESSAGE, extra=extra)


class DecodeScope:
    """Dedupe collector for one decode scope (locks 5-7).

    Holds the set of ``(model, field_path, kind)`` triples already reported.
    The list index is deliberately excluded from ``field_path``, so N
    identically-diverging rows of an unbounded catalogue read collapse into one
    record. Distinct kinds at the same path stay distinct: those are two
    different facts about the model.

    Emission is eager at first occurrence — there is no flush, no buffer and no
    ``occurrences`` counter (lock 7).
    """

    __slots__ = ("_seen",)

    def __init__(self) -> None:
        self._seen: set[tuple[str, str, str]] = set()

    def __call__(self, model: str, path: str, kind: str, declared: str, observed: str) -> None:
        """Report one divergence, unless its triple was already seen in this scope."""
        triple = (model, path, kind)
        if triple in self._seen:
            return
        # Lock 4, signed: strict mode raises on ``missing`` / ``type`` /
        # ``non_dict`` and NEVER on ``extra``. An extra key arrives on the
        # vendor's release schedule, not ours; making it fatal would fail a
        # strict driver run on every legitimate new field.
        strict = kind not in _INFO_KINDS and STRICT_DECODE.get()
        # Phase 29 review CR-02: the triple is marked seen ONLY once this call has
        # actually DISPOSED of the divergence by reporting it. Marking it ahead of
        # the strict raise left the triple recorded while nothing had been
        # reported, so any second decode of the same divergence inside one scope
        # took the ``return`` branch above: no raise, no record, and the policy
        # default substituted silently. That is a strict-mode escape, and
        # ``ws_client``'s caught-and-continue frame handler is a path of exactly
        # that shape.
        if not strict:
            self._seen.add(triple)
        # Emitted BEFORE the raise so a strict run still leaves the record on the
        # paquete logger. ``_emit`` never raises (lock 9), so it cannot mask the
        # strict disposition that follows it.
        _emit(model, path, kind, declared, observed)
        if strict:
            raise IOLDecodeError(path, declared, observed, model)


class _SilentScope(DecodeScope):
    """A sink that records nothing, emits nothing and never raises."""

    __slots__ = ()

    def __call__(self, model: str, path: str, kind: str, declared: str, observed: str) -> None:
        """Discard the divergence — no dedupe entry, no record, no raise."""
        return


# Used by constructors that build an all-defaults instance without decoding
# wire data: matriz's ``empty()`` classmethod walks every field with a ``None``
# value **by design**, and routing that through an emitting sink would produce
# one spurious ``missing`` record per field on every nested-model default. It is
# also how lock 8 suppresses the per-field records under a non-dict payload.
# higyrus has no ``empty()`` today, so the constant is otherwise unreferenced
# here — it must still be present so the five copies stay byte-identical.
SILENT_SINK = _SilentScope()


# ---------------------------------------------------------------------------
# Mode + scope carriers (D-03 ``.set()``-without-reset discipline)
# ---------------------------------------------------------------------------

STRICT_DECODE: ContextVar[bool] = ContextVar("iol_client_strict_decode", default=False)
DECODE_SCOPE: ContextVar[DecodeScope | None] = ContextVar("iol_client_decode_scope", default=None)


def open_request_scope() -> DecodeScope:
    """Bind a fresh :class:`DecodeScope` for one HTTP response. Called from ``_request``.

    Every model decoded from one response shares this scope — including every
    element of a top-level ``list[Model]`` parse, which is what makes the
    dedupe collapse actually fire.
    """
    scope = DecodeScope()
    DECODE_SCOPE.set(scope)
    return scope


def current_sink() -> DecodeScope:
    """Return the bound scope, or a fresh per-call scope when none is bound.

    Lock 6: a process-lifetime scope is explicitly rejected — it would make the
    second identical response decode silently clean, which is the false pass
    this milestone exists to eliminate.
    """
    scope = DECODE_SCOPE.get()
    if scope is None:
        return DecodeScope()
    return scope


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _is_model(hint: Any) -> bool:
    """Duck-typed nested-model predicate — no ``models`` import (see module docstring)."""
    return (
        isinstance(hint, type) and is_dataclass(hint) and callable(getattr(hint, "from_api", None))
    )


def _kind_of(value: Any) -> str:
    """``missing`` when the payload carried no usable value, ``type`` otherwise."""
    if value is None:
        return "missing"
    return "type"


def _name_of(hint: Any) -> str:
    """Declared-type name in the ``verification/schema.py::schema_of`` vocabulary (D-06)."""
    if isinstance(hint, type):
        return hint.__name__
    origin = get_origin(hint)
    if origin is Literal:
        return "Literal"
    if origin is Union or origin is UnionType:
        return " | ".join(_name_of(arg) for arg in get_args(hint))
    if isinstance(origin, type):
        return origin.__name__
    return str(hint)


def _scalar_default(hint: Any, policy: DecodePolicy) -> Any:
    """The policy substitution for a scalar declared type."""
    if hint is str:
        return policy.missing_str
    if hint is bool:
        return policy.missing_bool
    if hint is int:
        return policy.missing_int
    if hint is float:
        return policy.missing_float
    return None


@lru_cache(maxsize=512)
def hints_for(cls: Any) -> dict[str, Any]:
    """Resolved type hints for ``cls``, cached per class.

    With ``from __future__ import annotations`` mandatory repo-wide every
    annotation is a string that :func:`typing.get_type_hints` re-evaluates on
    each uncached call — roughly 89% of today's total decode cost.
    """
    return get_type_hints(cls)


# ---------------------------------------------------------------------------
# The walker
# ---------------------------------------------------------------------------


def walk_field(
    value: Any,
    hint: Any,
    *,
    path: str,
    model: str,
    policy: DecodePolicy,
    sink: DecodeScope,
) -> Any:
    """Coerce ``value`` to ``hint``, reporting every substituted default.

    Branch order is ``_coerce``'s, verbatim and load-bearing, with one new
    ``Literal`` branch inserted before the bare pass-through. Every branch's
    return value is unchanged; the only additions are the sink call before a
    substitution and the ``path`` threaded through the recursion.
    """
    origin = get_origin(hint)
    args = get_args(hint)

    # Optional[T] / T | None: explicit opt-in to nullable — a missing value
    # stays None instead of collapsing to a typed zero, and is NOT a divergence.
    if origin is Union or origin is UnionType:
        if value is None:
            return None
        non_none = [a for a in args if a is not NoneType]
        if len(non_none) == 1:
            return walk_field(value, non_none[0], path=path, model=model, policy=policy, sink=sink)
        return value

    if origin is list:
        if not isinstance(value, list):
            sink(model, path, _kind_of(value), _name_of(hint), type(value).__name__)
            return []
        inner = args[0] if args else Any
        # Lock 5: the element path segment carries no index, so identical
        # divergences across elements collapse under the dedupe triple.
        return [
            walk_field(item, inner, path=f"{path}[]", model=model, policy=policy, sink=sink)
            for item in value
        ]

    if _is_model(hint):
        return hint(**walk_model(hint, value, path=path, policy=policy, sink=sink))

    if hint is str:
        if isinstance(value, str):
            return value
        sink(model, path, _kind_of(value), "str", type(value).__name__)
        return value if policy.scalar_passthrough else policy.missing_str

    if hint is bool:
        if isinstance(value, bool):
            return value
        sink(model, path, _kind_of(value), "bool", type(value).__name__)
        return value if policy.scalar_passthrough else policy.missing_bool

    if hint is int:
        # bool is a subclass of int in Python — exclude it so bool payloads
        # don't collapse into "cantidad=True".
        if isinstance(value, bool):
            sink(model, path, "type", "int", "bool")
            return value if policy.scalar_passthrough else policy.missing_int
        if isinstance(value, int):
            return value
        sink(model, path, _kind_of(value), "int", type(value).__name__)
        return value if policy.scalar_passthrough else policy.missing_int

    if hint is float:
        if isinstance(value, bool):
            sink(model, path, "type", "float", "bool")
            return value if policy.scalar_passthrough else policy.missing_float
        if isinstance(value, int | float):
            return float(value)
        sink(model, path, _kind_of(value), "float", type(value).__name__)
        return value if policy.scalar_passthrough else policy.missing_float

    if origin is Literal:
        # D-09 / 29-DLOCK-RESPONSE-LITERAL.md: a RESPONSE field is never closed.
        # ``policy.literal_enforced`` is False in all five copies, permanently,
        # so membership is never checked and an out-of-set value is returned
        # byte-for-byte unchanged — vendor enum growth must not be fatal. What
        # IS validated is the runtime type of the literal's members.
        member_types = {type(arg) for arg in args}
        member_ok = value in args if policy.literal_enforced else True
        if member_ok and (not args or type(value) in member_types):
            return value
        sink(model, path, _kind_of(value), _name_of(hint), type(value).__name__)
        if policy.scalar_passthrough:
            return value
        return _scalar_default(member_types.pop() if len(member_types) == 1 else None, policy)

    return value


def walk_model(
    cls: type[Any],
    payload: Any,
    *,
    path: str = "",
    policy: DecodePolicy,
    sink: DecodeScope | None = None,
) -> dict[str, Any]:
    """Walk ``payload`` into the constructor kwargs of ``cls``, reporting divergences.

    The new capability over ``_coerce`` is extra-key detection: both legacy
    ``from_api`` implementations iterate ``dataclasses.fields(cls)`` and call
    ``data.get(name)``, so the payload's own key set is never enumerated.

    Ordering is the determinism guarantee (lock 7): extra keys first in sorted
    key order, then declared fields in ``dataclasses.fields()`` declaration
    order, recursing depth-first as each declared field is reached.
    """
    scope = sink if sink is not None else current_sink()
    # ``cast(Any, cls)`` is the file's existing mypy-strict discipline for
    # ``get_type_hints``-driven code — no type-ignore comment is introduced.
    target = cast(Any, cls)
    model = cls.__name__
    hints = hints_for(target)
    declared = fields(target)

    if isinstance(payload, dict):
        data: dict[str, Any] = payload
        field_sink = scope
        names = {f.name for f in declared}
        for key in sorted(set(data) - names):
            scope(model, f"{path}.{key}", "extra", "-", type(data[key]).__name__)
    else:
        # Lock 8: ``non_dict`` is terminal for reporting. The walker still
        # returns the per-paquete default shape (``policy.non_dict_model``);
        # only the per-field ``missing`` records are suppressed, because a 204
        # or a null body would otherwise emit one WARNING per declared field.
        data = {}
        field_sink = SILENT_SINK
        scope(model, path, "non_dict", model, type(payload).__name__)

    return {
        f.name: walk_field(
            data.get(f.name),
            hints[f.name],
            path=f"{path}.{f.name}",
            model=model,
            policy=policy,
            sink=field_sink,
        )
        for f in declared
    }
