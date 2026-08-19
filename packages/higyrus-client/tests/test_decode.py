"""Behaviour contract for ``higyrus_client._decode`` — the canonical walker.

Phase 29 Plan 02 (DEC-01). This suite is the tracer slice: it pins the five
divergence classes (``missing`` / ``type`` / ``extra`` / ``non_dict`` and the
``None``/204 shape) across the two decode modes (observable and strict), plus
the twelve locks of ``29-AGGREGATION-CONTRACT.md`` and the D-09 lock in
``29-DLOCK-RESPONSE-LITERAL.md``.

Model fixtures are declared module-locally so the suite never depends on a
shipped model's field list — a shipped model gaining or losing a field must
not be able to turn a walker regression green.
"""

from __future__ import annotations

import ast
import contextlib
import dataclasses
import inspect
import logging
import pathlib
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Literal

import pytest
from pytest_httpx import HTTPXMock

import higyrus_client
from higyrus_client import _decode, aio, models
from higyrus_client import client as client_mod
from higyrus_client._core import RequestSpec
from higyrus_client._decode import POLICY, DecodeScope, walk_field, walk_model
from higyrus_client.aio import AsyncClient
from higyrus_client.client import Client
from higyrus_client.exceptions import HigyrusClientError, HigyrusDecodeError
from higyrus_client.models import Parking, Posicion, PosicionValuada, SafeModel

_MESSAGE = "decode divergence"


@pytest.fixture(autouse=True)
def _pristine_decode_context() -> Iterator[None]:
    """Start every test in this module with an unbound decode mode and scope.

    Consequence of the D-03 ``.set()``-without-reset discipline: once ANY test
    in the session drives a real ``_request`` (``test_client.py`` does, dozens
    of times), the sync test context keeps that request's ``DECODE_SCOPE``
    bound. A later bare ``Model.from_api()`` would then join the stale scope
    and its already-seen ``(model, field_path, kind)`` triple would be deduped
    away — turning an assertion about a divergence record green-to-empty purely
    on test ORDER. In production the same discipline is correct and intended:
    every request rebinds a fresh scope before any decode from it happens.
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


_CONTRACT_KEYS = (
    "package",
    "divergence",
    "field_path",
    "declared_type",
    "observed_type",
    "model",
)


# ---------------------------------------------------------------------------
# Module-local model fixtures
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _Leaf(SafeModel):
    """Nested leaf used to exercise list-element path collapse."""

    nombre: str
    dias: int


@dataclass(frozen=True, slots=True)
class _Scalars(SafeModel):
    """One field per scalar branch of the walker, in declaration order."""

    s: str
    i: int
    f: float
    b: bool


@dataclass(frozen=True, slots=True)
class _Nested(SafeModel):
    """A model carrying a ``list[Model]`` field."""

    titulo: str
    hojas: list[_Leaf]


@dataclass(frozen=True, slots=True)
class _WithLiteral(SafeModel):
    """A ``Literal`` RESPONSE field — D-09 territory."""

    lado: Literal["BUY", "SELL"] | None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _divergences(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    """Every divergence record captured so far, in emission order."""
    return [r for r in caplog.records if r.getMessage() == _MESSAGE]


def _walk(
    cls: type,
    payload: Any,
    caplog: pytest.LogCaptureFixture,
    *,
    sink: DecodeScope | None = None,
) -> tuple[Any, list[logging.LogRecord]]:
    """Walk ``payload`` into ``cls`` with a fresh scope, returning instance + records."""
    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="higyrus_client"):
        kwargs = walk_model(
            cls, payload, policy=POLICY, sink=sink if sink is not None else DecodeScope()
        )
    return cls(**kwargs), _divergences(caplog)


def _tuples(records: list[logging.LogRecord]) -> list[tuple[str, str]]:
    return [(r.field_path, r.divergence) for r in records]  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Module surface + policy constant
# ---------------------------------------------------------------------------


def test_all_exports_the_ten_public_names() -> None:
    """The module's ``__all__`` is the frozen public surface of every copy."""
    assert sorted(_decode.__all__) == [
        "DECODE_SCOPE",
        "DecodePolicy",
        "DecodeScope",
        "POLICY",
        "SILENT_SINK",
        "STRICT_DECODE",
        "current_sink",
        "hints_for",
        "open_request_scope",
        "walk_field",
        "walk_model",
    ]


def test_policy_constant_matches_the_semantics_matrix() -> None:
    """``29-SEMANTICS-MATRIX.md`` Section 2, higyrus row — verbatim."""
    assert POLICY.missing_str == ""
    assert POLICY.missing_int == 0
    assert POLICY.missing_float == 0.0
    assert POLICY.missing_bool is False
    assert POLICY.non_dict_model == "from_api_none"
    assert POLICY.scalar_passthrough is False
    assert POLICY.literal_enforced is False


def test_decode_module_never_imports_models() -> None:
    """``_decode`` must stand alone: two of the five copies have no ``models.py``."""
    source = pathlib.Path(inspect.getfile(_decode)).read_text(encoding="utf-8")
    imported: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert not any("models" in name for name in imported), imported
    package_imports = {name for name in imported if name.startswith("higyrus_client")}
    assert package_imports == {"higyrus_client.exceptions"}


# ---------------------------------------------------------------------------
# Divergence class 1 — missing
# ---------------------------------------------------------------------------


def test_missing_scalars_return_typed_zeros_and_report(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A declared scalar absent from the payload: same default, now reported."""
    obj, records = _walk(_Scalars, {}, caplog)

    assert (obj.s, obj.i, obj.f, obj.b) == ("", 0, 0.0, False)
    assert {
        (r.field_path, r.divergence, r.declared_type, r.observed_type)  # type: ignore[attr-defined]
        for r in records
    } == {
        (".s", "missing", "str", "NoneType"),
        (".i", "missing", "int", "NoneType"),
        (".f", "missing", "float", "NoneType"),
        (".b", "missing", "bool", "NoneType"),
    }
    assert all(r.levelno == logging.WARNING for r in records)


def test_missing_list_field_returns_empty_list_and_reports(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A ``list[X]`` field absent from the payload stays ``[]`` and reports once."""
    obj, records = _walk(_Nested, {"titulo": "t"}, caplog)

    assert obj.hojas == []
    assert _tuples(records) == [(".hojas", "missing")]


# ---------------------------------------------------------------------------
# Divergence class 2 — wrong type
# ---------------------------------------------------------------------------


def test_wrong_typed_scalar_returns_default_and_reports_type(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A declared ``str`` carrying an ``int`` returns ``""`` and reports ``type``."""
    obj, records = _walk(_Scalars, {"s": 7, "i": 1, "f": 1.0, "b": True}, caplog)

    assert obj.s == ""
    assert _tuples(records) == [(".s", "type")]
    assert records[0].declared_type == "str"  # type: ignore[attr-defined]
    assert records[0].observed_type == "int"  # type: ignore[attr-defined]


def test_bool_payload_never_collapses_into_an_int_field(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The ``bool``-is-``int`` guard survives the rewrite and is now reported."""
    obj, records = _walk(_Scalars, {"s": "a", "i": True, "f": 1.0, "b": True}, caplog)

    assert obj.i == 0
    assert _tuples(records) == [(".i", "type")]
    assert records[0].observed_type == "bool"  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Divergence class 3 — extra wire key
# ---------------------------------------------------------------------------


def test_extra_wire_key_reports_at_info_and_leaves_the_model_untouched(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Lock 3: an extra key is vendor growth — INFO, never WARNING."""
    payload = {"s": "a", "i": 1, "f": 1.0, "b": True, "sobrante": "x"}
    obj, records = _walk(_Scalars, payload, caplog)

    assert obj == _Scalars("a", 1, 1.0, True)
    assert len(records) == 1
    assert records[0].divergence == "extra"  # type: ignore[attr-defined]
    assert records[0].field_path == ".sobrante"  # type: ignore[attr-defined]
    assert records[0].declared_type == "-"  # type: ignore[attr-defined]
    assert records[0].observed_type == "str"  # type: ignore[attr-defined]
    assert records[0].levelno == logging.INFO


# ---------------------------------------------------------------------------
# Divergence class 4 — non-dict payload (and class 5 — None / 204)
# ---------------------------------------------------------------------------


def test_non_dict_payload_emits_one_record_and_suppresses_per_field_missing(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Lock 8: ``non_dict`` is terminal for reporting."""
    obj, records = _walk(_Scalars, ["not", "a", "dict"], caplog)

    assert obj == _Scalars("", 0, 0.0, False)
    assert _tuples(records) == [("", "non_dict")]
    assert records[0].observed_type == "list"  # type: ignore[attr-defined]
    assert records[0].model == "_Scalars"  # type: ignore[attr-defined]


def test_none_payload_behaves_as_non_dict(caplog: pytest.LogCaptureFixture) -> None:
    """``from_api(None)`` and a null/204 body are the same shape error."""
    obj, records = _walk(_Scalars, None, caplog)

    assert obj == _Scalars("", 0, 0.0, False)
    assert _tuples(records) == [("", "non_dict")]
    assert records[0].observed_type == "NoneType"  # type: ignore[attr-defined]


def test_empty_dict_is_a_dict_and_reports_per_field_missing(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Lock 8: ``{}`` is a dict — a per-field modelling signal, not a shape error."""
    _, records = _walk(_Scalars, {}, caplog)

    assert [r.divergence for r in records] == ["missing"] * 4  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Lock 1 — record shape
# ---------------------------------------------------------------------------


def test_record_is_flat_all_str_and_carries_no_wire_value(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Lock 1 + T-29-06: type-not-value, six flat str keys, no containers."""
    payload = {
        "s": 12345,
        "i": "SENTINEL-WIRE-I",
        "f": "SENTINEL-WIRE-F",
        "b": "SENTINEL-WIRE-B",
        "sobrante": "SENTINEL-WIRE-EXTRA",
    }
    _, records = _walk(_Scalars, payload, caplog)
    wire_values = {str(v) for v in payload.values()}

    assert records
    # ``message``/``asctime`` are injected by whichever formatter renders the
    # record (caplog's, here) — they are not part of the emitted ``extra``.
    baseline = set(logging.LogRecord("n", logging.INFO, "p", 0, "m", None, None).__dict__) | {
        "message",
        "asctime",
    }
    for record in records:
        assert set(record.__dict__) - baseline == set(_CONTRACT_KEYS)
        for key in _CONTRACT_KEYS:
            value = getattr(record, key)
            assert isinstance(value, str), (key, value)
            assert not isinstance(value, dict | list | tuple)
            assert value not in wire_values, (key, value)
        assert record.package == "higyrus_client"  # type: ignore[attr-defined]
        assert record.model == "_Scalars"  # type: ignore[attr-defined]


def test_contract_keys_avoid_every_reserved_logrecord_attribute() -> None:
    """Lock 1: ``makeRecord`` raises ``KeyError`` on a reserved ``extra`` key."""
    reserved = set(logging.LogRecord("n", logging.INFO, "p", 0, "m", None, None).__dict__) | {
        "message",
        "asctime",
    }

    assert set(_CONTRACT_KEYS).isdisjoint(reserved)
    assert set(_decode._RECORD_KEYS) == set(_CONTRACT_KEYS)


def test_reserved_keys_emission_through_a_real_logger_call_does_not_raise() -> None:
    """T-29-08: drive a real ``logger.warning(..., extra=...)``, not ``setattr``.

    ``LogRecord.__init__`` cannot reproduce the failure — only
    ``Logger.makeRecord`` refuses to overwrite an existing attribute.
    """
    logger = logging.getLogger("higyrus_client")
    extra = dict.fromkeys(_CONTRACT_KEYS, "x")

    logger.warning(_MESSAGE, extra=extra)
    logger.info(_MESSAGE, extra=extra)


# ---------------------------------------------------------------------------
# Lock 9 — emitter safety
# ---------------------------------------------------------------------------


class _ExplodingHandler(logging.Handler):
    """A consumer handler that raises on every record."""

    def emit(self, record: logging.LogRecord) -> None:
        raise RuntimeError("consumer handler exploded")


def test_emitter_never_raises_into_the_decode_return_path() -> None:
    """Lock 9 / T-29-09: a handler exception must not reach the caller."""
    logger = logging.getLogger("higyrus_client")
    handler = _ExplodingHandler()
    previous_level = logger.level
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    try:
        kwargs = walk_model(_Scalars, {"sobrante": 1}, policy=POLICY, sink=DecodeScope())
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)

    assert _Scalars(**kwargs) == _Scalars("", 0, 0.0, False)


# ---------------------------------------------------------------------------
# Lock 5 — dedupe triple
# ---------------------------------------------------------------------------


def test_list_elements_collapse_under_an_index_free_path(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Lock 5: the list path segment is ``[]`` with no index."""
    payload = {
        "titulo": "t",
        "hojas": [{"nombre": "a"}, {"nombre": "b"}, {"nombre": "c"}],
    }
    obj, records = _walk(_Nested, payload, caplog)

    assert len(obj.hojas) == 3
    assert _tuples(records) == [(".hojas[].dias", "missing")]


def test_distinct_kinds_at_the_same_path_stay_distinct(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Lock 5: ``missing`` and ``type`` at one path are two facts, not one."""
    payload = {
        "titulo": "t",
        "hojas": [{"nombre": "a"}, {"nombre": "b", "dias": "x"}],
    }
    _, records = _walk(_Nested, payload, caplog)

    assert _tuples(records) == [
        (".hojas[].dias", "missing"),
        (".hojas[].dias", "type"),
    ]


def test_one_scope_shared_across_two_walks_emits_once(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Lock 6: the dedupe set lives in the scope, so a shared scope collapses."""
    scope = DecodeScope()
    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="higyrus_client"):
        walk_model(_Scalars, {}, policy=POLICY, sink=scope)
        walk_model(_Scalars, {}, policy=POLICY, sink=scope)

    assert len(_divergences(caplog)) == 4


# ---------------------------------------------------------------------------
# Lock 7 — deterministic ordering
# ---------------------------------------------------------------------------


def test_emission_order_is_extras_sorted_then_declaration_order(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Lock 7: extras first in sorted key order, then declared fields in order."""
    _, records = _walk(_Scalars, {"zeta": 1, "alfa": 2}, caplog)

    assert _tuples(records) == [
        (".alfa", "extra"),
        (".zeta", "extra"),
        (".s", "missing"),
        (".i", "missing"),
        (".f", "missing"),
        (".b", "missing"),
    ]


def test_emission_order_is_stable_across_repeated_decodes(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Lock 7: two runs over one payload produce the same record sequence."""
    payload = {
        "titulo": "t",
        "extra_uno": 1,
        "hojas": [{"nombre": "a"}, {"dias": "x"}],
    }
    _, first = _walk(_Nested, payload, caplog)
    _, second = _walk(_Nested, payload, caplog)

    assert _tuples(first) == _tuples(second)


# ---------------------------------------------------------------------------
# Strict mode
# ---------------------------------------------------------------------------


def test_strict_mode_raises_with_the_exact_field_path_and_no_wire_value() -> None:
    """Lock 4 / T-29-07: strict raises on ``type`` carrying only type names."""
    token = _decode.STRICT_DECODE.set(True)
    try:
        with pytest.raises(HigyrusDecodeError) as excinfo:
            walk_model(
                _Scalars,
                {"s": "ok", "i": "SENTINEL-WIRE-VALUE", "f": 1.0, "b": True},
                policy=POLICY,
                sink=DecodeScope(),
            )
    finally:
        _decode.STRICT_DECODE.reset(token)

    message = str(excinfo.value)
    assert ".i" in message
    assert "SENTINEL-WIRE-VALUE" not in message
    assert isinstance(excinfo.value, HigyrusClientError)
    assert excinfo.value.field_path == ".i"
    assert excinfo.value.declared_type == "int"
    assert excinfo.value.observed_type == "str"
    assert excinfo.value.model == "_Scalars"


def test_strict_mode_raises_on_missing() -> None:
    """Lock 4: ``missing`` is fatal under strict mode."""
    token = _decode.STRICT_DECODE.set(True)
    try:
        with pytest.raises(HigyrusDecodeError, match=r"\.s"):
            walk_model(_Scalars, {}, policy=POLICY, sink=DecodeScope())
    finally:
        _decode.STRICT_DECODE.reset(token)


def test_strict_mode_raises_on_non_dict() -> None:
    """Lock 4: ``non_dict`` is fatal under strict mode."""
    token = _decode.STRICT_DECODE.set(True)
    try:
        with pytest.raises(HigyrusDecodeError, match="_Scalars"):
            walk_model(_Scalars, None, policy=POLICY, sink=DecodeScope())
    finally:
        _decode.STRICT_DECODE.reset(token)


def test_strict_mode_never_raises_on_an_extra_wire_key(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Lock 4, the signed decision: an extra key is never fatal."""
    payload = {"s": "a", "i": 1, "f": 1.0, "b": True, "sobrante": "x"}
    token = _decode.STRICT_DECODE.set(True)
    caplog.clear()
    try:
        with caplog.at_level(logging.DEBUG, logger="higyrus_client"):
            kwargs = walk_model(_Scalars, payload, policy=POLICY, sink=DecodeScope())
    finally:
        _decode.STRICT_DECODE.reset(token)

    records = _divergences(caplog)
    assert _Scalars(**kwargs) == _Scalars("a", 1, 1.0, True)
    assert _tuples(records) == [(".sobrante", "extra")]
    assert records[0].levelno == logging.INFO


# ---------------------------------------------------------------------------
# D-09 — Literal is never closed on RESPONSE fields
# ---------------------------------------------------------------------------


def test_literal_membership_is_never_enforced(caplog: pytest.LogCaptureFixture) -> None:
    """D-09 (a): an out-of-set value is returned byte-for-byte unchanged."""
    obj, records = _walk(_WithLiteral, {"lado": "zzz"}, caplog)

    assert obj.lado == "zzz"
    assert [r for r in records if r.divergence == "type"] == []  # type: ignore[attr-defined]


def test_literal_reports_a_wrong_runtime_type(caplog: pytest.LogCaptureFixture) -> None:
    """D-09 (b): a wire ``int`` where every member is ``str`` is a real divergence."""
    obj, records = _walk(_WithLiteral, {"lado": 7}, caplog)

    assert obj.lado == POLICY.missing_str
    assert _tuples(records) == [(".lado", "type")]
    assert records[0].observed_type == "int"  # type: ignore[attr-defined]


def test_literal_membership_is_not_enforced_under_strict_mode() -> None:
    """D-09: an out-of-set value is never fatal, even in strict mode."""
    token = _decode.STRICT_DECODE.set(True)
    try:
        kwargs = walk_model(_WithLiteral, {"lado": "zzz"}, policy=POLICY, sink=DecodeScope())
    finally:
        _decode.STRICT_DECODE.reset(token)

    assert kwargs["lado"] == "zzz"


def test_optional_field_stays_none_without_a_divergence(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """``T | None`` is an explicit opt-in to nullable — not a divergence."""
    obj, records = _walk(_WithLiteral, {"lado": None}, caplog)

    assert obj.lado is None
    assert records == []


# ---------------------------------------------------------------------------
# hints_for cache
# ---------------------------------------------------------------------------


def test_hints_for_is_cache_backed() -> None:
    """The single highest-leverage change: stringified annotations resolved once."""
    _decode.hints_for.cache_clear()
    walk_model(_Scalars, {}, policy=POLICY, sink=_decode.SILENT_SINK)
    before = _decode.hints_for.cache_info()
    walk_model(_Scalars, {}, policy=POLICY, sink=_decode.SILENT_SINK)
    after = _decode.hints_for.cache_info()

    assert after.hits > before.hits
    assert _decode.hints_for(_Scalars)["s"] is str


# ---------------------------------------------------------------------------
# SILENT_SINK + scope plumbing
# ---------------------------------------------------------------------------


def test_silent_sink_records_nothing_emits_nothing_and_never_raises(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """``SILENT_SINK`` is inert for every kind, including under strict mode."""
    token = _decode.STRICT_DECODE.set(True)
    caplog.clear()
    try:
        with caplog.at_level(logging.DEBUG, logger="higyrus_client"):
            for kind in ("missing", "type", "extra", "non_dict"):
                assert _decode.SILENT_SINK("M", ".campo", kind, "str", "int") is None
            kwargs = walk_model(_Scalars, None, policy=POLICY, sink=_decode.SILENT_SINK)
    finally:
        _decode.STRICT_DECODE.reset(token)

    assert _divergences(caplog) == []
    assert _Scalars(**kwargs) == _Scalars("", 0, 0.0, False)


def test_open_request_scope_binds_a_scope_that_current_sink_reuses() -> None:
    """Lock 6: ``_request`` binds once; every decode beneath it shares the scope."""
    previous = _decode.DECODE_SCOPE.get()
    try:
        scope = _decode.open_request_scope()
        assert isinstance(scope, DecodeScope)
        assert _decode.current_sink() is scope
        assert _decode.current_sink() is scope
    finally:
        _decode.DECODE_SCOPE.set(previous)


def test_current_sink_without_a_bound_scope_returns_a_fresh_per_call_scope() -> None:
    """Lock 6: a bare ``Model.from_api()`` gets a per-call scope, never a global."""
    previous = _decode.DECODE_SCOPE.get()
    _decode.DECODE_SCOPE.set(None)
    try:
        first = _decode.current_sink()
        second = _decode.current_sink()
        assert isinstance(first, DecodeScope)
        assert first is not second
    finally:
        _decode.DECODE_SCOPE.set(previous)


# ---------------------------------------------------------------------------
# walk_field direct surface
# ---------------------------------------------------------------------------


def test_walk_field_preserves_every_coercion_return_value() -> None:
    """The walker changes reporting only — never a returned value."""
    sink = _decode.SILENT_SINK
    kw: dict[str, Any] = {"path": "", "model": "M", "policy": POLICY, "sink": sink}

    assert walk_field(None, str, **kw) == ""
    assert walk_field("x", str, **kw) == "x"
    assert walk_field(None, int, **kw) == 0
    assert walk_field(True, int, **kw) == 0
    assert walk_field(3, int, **kw) == 3
    assert walk_field(None, float, **kw) == 0.0
    assert walk_field(True, float, **kw) == 0.0
    assert walk_field(3, float, **kw) == 3.0
    assert walk_field(None, bool, **kw) is False
    assert walk_field(True, bool, **kw) is True
    assert walk_field(None, list[int], **kw) == []
    assert walk_field([1, 2], list[int], **kw) == [1, 2]
    assert walk_field(None, str | None, **kw) is None
    assert walk_field("x", str | None, **kw) == "x"


# ---------------------------------------------------------------------------
# Delegation — models.py routes through the walker without moving a value
# ---------------------------------------------------------------------------


def _full_payload(cls: type) -> dict[str, Any]:
    """A type-correct wire payload covering every declared field of ``cls``."""
    filler: dict[Any, Any] = {str: "x", int: 1, float: 1.0, bool: True}
    hints = _decode.hints_for(cls)
    return {f.name: filler.get(hints[f.name], []) for f in dataclasses.fields(cls)}  # type: ignore[arg-type]


def test_from_api_keeps_its_single_positional_parameter() -> None:
    """The 872-test zero-edit merge gate: the public contract may not move."""
    params = list(inspect.signature(SafeModel.from_api).parameters.values())

    assert [p.name for p in params] == ["payload"]
    assert params[0].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_from_api_delegates_to_the_walker() -> None:
    """``models.py`` must route through ``_decode``, not keep a second copy."""
    source = pathlib.Path(inspect.getfile(models)).read_text(encoding="utf-8")

    assert "_decode.walk_model" in source
    assert "_decode.walk_field" in source


def test_coerce_is_still_callable_with_identical_return_values() -> None:
    """Back-compat shim: two positional args, same values as before the rewrite."""
    coerce = models._coerce
    params = list(inspect.signature(coerce).parameters.values())

    assert [p.name for p in params] == ["value", "hint"]
    assert all(p.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD for p in params)
    assert coerce(None, str) == ""
    assert coerce(7, str) == ""
    assert coerce("x", str) == "x"
    assert coerce(None, int) == 0
    assert coerce(True, int) == 0
    assert coerce(5, int) == 5
    assert coerce(None, float) == 0.0
    assert coerce(True, float) == 0.0
    assert coerce(3, float) == 3.0
    assert coerce(None, bool) is False
    assert coerce(True, bool) is True
    assert coerce(None, list[int]) == []
    assert coerce([1, 2], list[int]) == [1, 2]
    assert coerce(None, str | None) is None
    assert coerce("x", str | None) == "x"
    assert coerce(None, Parking) == Parking.from_api(None)
    assert coerce({"diasParking": 3}, Parking) == Parking.from_api({"diasParking": 3})


def test_real_model_missing_float_still_defaults_and_now_reports(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The exact pairing that is silent today: ``0.0`` returned AND reported."""
    payload = _full_payload(PosicionValuada)
    del payload["precio"]

    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="higyrus_client"):
        obj = PosicionValuada.from_api(payload)

    assert obj.precio == 0.0
    assert obj.valuacion == 1.0
    assert _tuples(_divergences(caplog)) == [(".precio", "missing")]


def test_real_model_extra_wire_key_reports_and_builds_unchanged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """An undeclared wire key on a shipped model: one INFO record, model intact."""
    payload = _full_payload(PosicionValuada)
    expected = PosicionValuada.from_api(dict(payload))
    payload["nuevoCampoDelVendor"] = "v"

    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="higyrus_client"):
        obj = PosicionValuada.from_api(payload)

    records = _divergences(caplog)
    assert obj == expected
    assert _tuples(records) == [(".nuevoCampoDelVendor", "extra")]
    assert records[0].levelno == logging.INFO


def test_real_nested_model_path_is_dotted_from_the_decode_root(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """``.parking[].diasParking`` — the aggregation contract's worked example."""
    payload = _full_payload(Posicion)
    payload["parking"] = [{"monedaPosicion": "ARS"}, {"monedaPosicion": "USD"}]

    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="higyrus_client"):
        obj = Posicion.from_api(payload)

    assert len(obj.parking) == 2
    assert (".parking[].diasParking", "missing") in _tuples(_divergences(caplog))


# ---------------------------------------------------------------------------
# Phase 29 Plan 03 — strict_decode carrier: state field, four public entry
# points, two bind sites (D-03)
# ---------------------------------------------------------------------------


@contextlib.contextmanager
def _restored_decode_context() -> Iterator[None]:
    """Save/restore both ContextVars around a test that drives a real ``_request``.

    ``_request`` binds with ``.set()`` and deliberately never resets (D-03), so
    a sync test would otherwise leak its mode into every later test in the same
    context. Async tests do not need this — each task gets its own context copy
    — but they use it too so the two mirrors read identically.
    """
    mode = _decode.STRICT_DECODE.get()
    scope = _decode.DECODE_SCOPE.get()
    try:
        yield
    finally:
        _decode.STRICT_DECODE.set(mode)
        _decode.DECODE_SCOPE.set(scope)


@contextlib.contextmanager
def _restored_default_clients() -> Iterator[None]:
    """Reset the module-level ``strict_decode`` opt-in on both default clients.

    ``configure`` carries ``strict_decode`` forward (the ``None`` sentinel means
    "no cambiar"), so a test that opts in must opt back out or the conftest's
    autouse ``configure`` calls would carry the opt-in into every later test.
    """
    try:
        yield
    finally:
        higyrus_client.configure(strict_decode=False)
        aio.configure(strict_decode=False)


def _spec() -> RequestSpec:
    return RequestSpec(method="GET", path="/api/health", endpoint_name="get_health")


def test_strict_mode_from_constructor() -> None:
    """D-03: ``Client(strict_decode=True)`` reaches the shared ``_ClientState``."""
    assert Client()._state.strict_decode is False
    assert Client(strict_decode=True)._state.strict_decode is True
    assert Client(strict_decode=False)._state.strict_decode is False
    assert AsyncClient()._state.strict_decode is False
    assert AsyncClient(strict_decode=True)._state.strict_decode is True


def test_strict_mode_from_configure() -> None:
    """D-03: sync and async ``configure(strict_decode=True)`` reach the default client."""
    with _restored_default_clients():
        higyrus_client.configure(strict_decode=True)
        aio.configure(strict_decode=True)
        assert client_mod._get_default()._state.strict_decode is True
        assert aio._get_default()._state.strict_decode is True
        # Sentinel ``None`` = "no cambiar": an unrelated configure() call must
        # NOT silently reset a previous opt-in.
        higyrus_client.configure(base_url="https://api.test")
        assert client_mod._get_default()._state.strict_decode is True


def test_strict_mode_view_inherits() -> None:
    """D-14: the flag lives on the shared state, never in ``Client.__slots__``."""
    parent = Client(strict_decode=True)
    view = parent.with_options(max_retries=5)
    assert view._state is parent._state
    assert view._state.strict_decode is True
    # A later mutation on the parent is visible through the view — proof the
    # flag was never copied into the view's __slots__.
    parent._state.strict_decode = False
    assert view._state.strict_decode is False
    assert "strict_decode" not in Client.__slots__
    assert "strict_decode" not in AsyncClient.__slots__


def test_strict_mode_bound_by_request(httpx_mock: HTTPXMock) -> None:
    """The bind happens at the top of ``Client._request``, from ``_state``."""
    httpx_mock.add_response(json={"status": "ok"})
    with _restored_decode_context():
        _decode.STRICT_DECODE.set(False)
        _decode.DECODE_SCOPE.set(None)
        with Client(
            base_url="https://api.test",
            token="t",
            token_expires_at=9_999_999_999.0,
            strict_decode=True,
        ) as c:
            c._request(_spec())
        assert _decode.STRICT_DECODE.get() is True
        assert isinstance(_decode.DECODE_SCOPE.get(), DecodeScope)


def test_strict_mode_bound_by_module_shim(httpx_mock: HTTPXMock) -> None:
    """The module-level ``_request`` shim delegates THROUGH the bound method.

    This is the evidence that binding on the method alone covers every path:
    no bind is needed (or wanted) in the shim itself.
    """
    httpx_mock.add_response(json={"status": "ok"})
    with _restored_decode_context(), _restored_default_clients():
        _decode.STRICT_DECODE.set(False)
        _decode.DECODE_SCOPE.set(None)
        # ``configure`` does NOT carry the token forward (only credentials and
        # base_url), so it is re-seeded here exactly as conftest does.
        higyrus_client.configure(
            strict_decode=True, token="test-token", token_expires_at=9_999_999_999.0
        )
        client_mod._request("GET", "/api/health")
        assert _decode.STRICT_DECODE.get() is True
        assert isinstance(_decode.DECODE_SCOPE.get(), DecodeScope)


async def test_async_request_binds_mode(httpx_mock: HTTPXMock) -> None:
    """Dual sync/async parity: ``AsyncClient._request`` mirrors the bind verbatim."""
    httpx_mock.add_response(json={"status": "ok"})
    with _restored_decode_context():
        _decode.STRICT_DECODE.set(False)
        _decode.DECODE_SCOPE.set(None)
        async with AsyncClient(
            base_url="https://api.test",
            token="t",
            token_expires_at=9_999_999_999.0,
            strict_decode=True,
        ) as c:
            await c._request(_spec())
            assert _decode.STRICT_DECODE.get() is True
            assert isinstance(_decode.DECODE_SCOPE.get(), DecodeScope)


def test_no_reset_after_request(httpx_mock: HTTPXMock) -> None:
    """D-03: no reset, no try/finally — the decode has not happened yet.

    ``_request`` returns the ``httpx.Response``; the parser decodes it
    afterwards and holds no reference to the Client. A reset in a ``finally``
    would unbind the mode before the decoder ever reads it.
    """
    httpx_mock.add_response(json={"status": "ok"})
    with _restored_decode_context():
        _decode.STRICT_DECODE.set(False)
        _decode.DECODE_SCOPE.set(None)
        with Client(
            base_url="https://api.test",
            token="t",
            token_expires_at=9_999_999_999.0,
            strict_decode=True,
        ) as c:
            resp = c._request(_spec())
            scope_during = _decode.DECODE_SCOPE.get()
        assert resp.status_code == 200
        # Still bound after the method returned, and it is the SAME scope, so
        # every model decoded from this response dedupes together (lock 6).
        assert _decode.STRICT_DECODE.get() is True
        assert _decode.DECODE_SCOPE.get() is scope_during


def test_request_binds_a_fresh_scope_per_response(httpx_mock: HTTPXMock) -> None:
    """Lock 6: a process-lifetime scope is rejected — each response gets its own."""
    httpx_mock.add_response(json={"status": "ok"})
    httpx_mock.add_response(json={"status": "ok"})
    with _restored_decode_context():
        _decode.DECODE_SCOPE.set(None)
        with Client(base_url="https://api.test", token="t", token_expires_at=9_999_999_999.0) as c:
            c._request(_spec())
            first = _decode.DECODE_SCOPE.get()
            c._request(_spec())
            second = _decode.DECODE_SCOPE.get()
        assert first is not None
        assert first is not second


# ---------------------------------------------------------------------------
# Phase 29 code review, CR-02 — strict mode must survive a re-decode
# ---------------------------------------------------------------------------


def test_strict_mode_raises_on_every_visit_of_one_divergence_in_one_scope(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """CR-02: a caught-and-retried decode inside one scope is still fatal.

    The dedupe triple is recorded only once the divergence has actually been
    reported. Before the fix it was marked seen ahead of the strict raise, so a
    second decode of the same divergence inside the same scope took the "already
    reported" branch: no raise, no record, and the policy default substituted
    silently.
    """
    scope = DecodeScope()
    payload = {"s": 7, "i": 1, "f": 1.0, "b": True}
    token = _decode.STRICT_DECODE.set(True)
    caplog.clear()
    try:
        with caplog.at_level(logging.DEBUG, logger="higyrus_client"):
            for _ in range(2):
                with pytest.raises(HigyrusDecodeError) as excinfo:
                    walk_model(_Scalars, payload, policy=POLICY, sink=scope)
                assert excinfo.value.field_path == ".s"
    finally:
        _decode.STRICT_DECODE.reset(token)

    # The record survives the raise, on BOTH attempts: a strict run still leaves
    # the divergence on the paquete logger (lock 9 — ``_emit`` never raises).
    paths = [r.field_path for r in _divergences(caplog)]  # type: ignore[attr-defined]
    assert paths == [".s", ".s"]
