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
import inspect
import logging
import pathlib
from dataclasses import dataclass
from typing import Any, Literal

import pytest

from higyrus_client import _decode
from higyrus_client._decode import POLICY, DecodeScope, walk_field, walk_model
from higyrus_client.exceptions import HigyrusClientError, HigyrusDecodeError
from higyrus_client.models import SafeModel

_MESSAGE = "decode divergence"

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
