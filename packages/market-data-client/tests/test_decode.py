"""Behaviour contract for ``market_data_client._decode`` — the fanned-out walker.

Phase 29 Plan 05 (DEC-01). market-data is the second package to receive the
canonical walker, and the first with model-level exemptions the ``DecodePolicy``
constant cannot express: :meth:`MarketDataSnapshot.from_api`'s ``received_at``
injection bypass and :meth:`Symbol.from_api`'s wire-key mirror plus its explicit
two-argument ``super()`` (``29-SEMANTICS-MATRIX.md`` Section 3(a) and 3(b)).

This suite pins the five divergence classes (``missing`` / ``type`` / ``extra`` /
``non_dict`` and the ``None``/204 shape) across the two decode modes, the twelve
locks of ``29-AGGREGATION-CONTRACT.md``, the D-09 ``Literal`` lock, the mode
carrier on the four public entry points and both ``_request`` bind sites — and
the two exemptions above, which a mechanical rewrite would silently break.

Model fixtures for the generic walker rows are declared module-locally so the
suite never depends on a shipped model's field list: a shipped model gaining or
losing a field must not be able to turn a walker regression green. The exemption
rows deliberately drive the REAL shipped classes, because the exemption IS the
shipped class's contract.
"""

from __future__ import annotations

import ast
import dataclasses
import inspect
import logging
import pathlib
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Literal, cast

import pytest
from pytest_httpx import HTTPXMock

import market_data_client
from market_data_client import _decode, aio, models
from market_data_client._decode import POLICY, DecodeScope, walk_field, walk_model
from market_data_client.aio import AsyncClient
from market_data_client.client import Client
from market_data_client.exceptions import MarketDataDecodeError, MarketDataError
from market_data_client.models import MarketDataSnapshot, SafeModel, Symbol

_MESSAGE = "decode divergence"
_BASE = "https://market-data-develop.test/api"

# Phase 31 (TYP-02): ``get_health`` is used below as a THROWAWAY endpoint whose
# only job is to drive a real ``_request`` and prove the mode is bound from the
# shared state. Now that it returns a typed ``Health``, the body must be the FULL
# live shape — a bare ``{"status": "ok"}`` omits ``auth`` and would raise
# ``MarketDataDecodeError`` under ``strict_decode=True``, failing those tests for
# a reason unrelated to their subject. Corrected on the TEST side (30-03
# precedent); the parser's guard is never loosened to accommodate a stale mock.
_HEALTH_BODY = {
    "status": "ok",
    "auth": {"configured": True, "enabled": True, "issuer": "https://auth.test/"},
}


@pytest.fixture(autouse=True)
def _pristine_decode_context() -> Iterator[None]:
    """Start every test in this module with an unbound decode mode and scope.

    Consequence of the D-03 ``.set()``-without-reset discipline: once ANY test
    in the session drives a real ``_request`` (this package's suite does, in the
    hundreds), the sync test context keeps that request's ``DECODE_SCOPE``
    bound. A later bare ``Model.from_api()`` would then join the stale scope and
    its already-seen ``(model, field_path, kind)`` triple would be deduped away
    — turning an assertion about a divergence record green-to-empty purely on
    test ORDER. In production the same discipline is correct and intended: every
    request rebinds a fresh scope before any decode from it happens.
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
    with caplog.at_level(logging.DEBUG, logger="market_data_client"):
        kwargs = walk_model(
            cls, payload, policy=POLICY, sink=sink if sink is not None else DecodeScope()
        )
    return cls(**kwargs), _divergences(caplog)


def _from_api(
    factory: Any, caplog: pytest.LogCaptureFixture, *args: Any, **kwargs: Any
) -> tuple[Any, list[logging.LogRecord]]:
    """Drive a real shipped ``from_api`` under a fresh scope, returning obj + records."""
    caplog.clear()
    _decode.open_request_scope()
    with caplog.at_level(logging.DEBUG, logger="market_data_client"):
        obj = factory(*args, **kwargs)
    return obj, _divergences(caplog)


def _tuples(records: list[logging.LogRecord]) -> list[tuple[str, str]]:
    return [(r.field_path, r.divergence) for r in records]  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Module surface + policy constant
# ---------------------------------------------------------------------------


def test_all_exports_the_eleven_public_names() -> None:
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
    """``29-SEMANTICS-MATRIX.md`` Section 2, market-data row — identical to higyrus's."""
    assert POLICY.missing_str == ""
    assert POLICY.missing_int == 0
    assert POLICY.missing_float == 0.0
    assert POLICY.missing_bool is False
    assert POLICY.non_dict_model == "from_api_none"
    assert POLICY.scalar_passthrough is False
    assert POLICY.literal_enforced is False


def test_logger_name_is_this_package() -> None:
    """One of the per-package deltas: records land on THIS package's logger."""
    assert _decode._LOGGER_NAME == "market_data_client"


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
    package_imports = {name for name in imported if name.startswith("market_data_client")}
    assert package_imports == {"market_data_client.exceptions"}


# ---------------------------------------------------------------------------
# Divergence class 1 — missing
# ---------------------------------------------------------------------------


def test_missing_scalars_return_typed_zeros_and_report(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A declared scalar absent from the payload: same default, now reported."""
    obj, records = _walk(_Scalars, {}, caplog)

    assert obj == _Scalars("", 0, 0.0, False)
    assert _tuples(records) == [(".s", "missing"), (".i", "missing"), (".f", "missing"), (".b", "missing")]  # fmt: skip


def test_missing_list_field_returns_empty_list_and_reports(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A missing ``list[X]`` still substitutes ``[]`` — and now says so."""
    obj, records = _walk(_Nested, {"titulo": "t"}, caplog)

    assert obj.hojas == []
    assert _tuples(records) == [(".hojas", "missing")]


# ---------------------------------------------------------------------------
# Divergence class 2 — type
# ---------------------------------------------------------------------------


def test_wrong_typed_scalar_returns_default_and_reports_type(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A wrong runtime type substitutes the typed zero and reports ``type``."""
    obj, records = _walk(_Scalars, {"s": 12, "i": "x", "f": "y", "b": "z"}, caplog)

    assert obj == _Scalars("", 0, 0.0, False)
    assert {kind for _, kind in _tuples(records)} == {"type"}
    assert [path for path, _ in _tuples(records)] == [".s", ".i", ".f", ".b"]


def test_bool_payload_never_collapses_into_an_int_field(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The ``bool``-is-``int`` guard survives the fan-out (matrix row 2, ``size=True``)."""
    obj, records = _walk(_Scalars, {"s": "a", "i": True, "f": 1, "b": True}, caplog)

    assert obj.i == 0
    assert obj.b is True
    assert _tuples(records) == [(".i", "type")]


# ---------------------------------------------------------------------------
# Divergence class 3 — extra wire key
# ---------------------------------------------------------------------------


def test_extra_wire_key_reports_at_info_and_leaves_the_model_untouched(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Lock 3: vendor growth is INFO-level information, never a defect."""
    payload = {"s": "a", "i": 1, "f": 1.0, "b": True, "vendorNuevo": 7}
    obj, records = _walk(_Scalars, payload, caplog)

    assert obj == _Scalars("a", 1, 1.0, True)
    assert _tuples(records) == [(".vendorNuevo", "extra")]
    assert records[0].levelno == logging.INFO
    assert records[0].declared_type == "-"  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Divergence classes 4 + 5 — non-dict payload and the None/204 body
# ---------------------------------------------------------------------------


def test_non_dict_payload_emits_one_record_and_suppresses_per_field_missing(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Lock 8: ``non_dict`` is terminal for reporting — one record, not one per field."""
    obj, records = _walk(_Scalars, "not-a-dict", caplog)

    assert obj == _Scalars("", 0, 0.0, False)
    assert _tuples(records) == [("", "non_dict")]
    assert records[0].observed_type == "str"  # type: ignore[attr-defined]


def test_none_payload_behaves_as_non_dict(caplog: pytest.LogCaptureFixture) -> None:
    """A ``null`` body / 204 emits ONE record, not one per declared field."""
    obj, records = _walk(_Scalars, None, caplog)

    assert obj == _Scalars("", 0, 0.0, False)
    assert _tuples(records) == [("", "non_dict")]


def test_empty_dict_is_a_dict_and_reports_per_field_missing(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """``{}`` is still a dict: the per-field ``missing`` records DO fire."""
    _, records = _walk(_Scalars, {}, caplog)

    assert {kind for _, kind in _tuples(records)} == {"missing"}
    assert len(records) == 4


# ---------------------------------------------------------------------------
# Lock 1 — record shape (T-29-22)
# ---------------------------------------------------------------------------


def test_record_is_flat_all_str_and_carries_no_wire_value(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Lock 1 + T-29-22: type-not-value, six flat str keys, no containers.

    market-data payloads carry symbol and account identifiers, so the record
    naming a field but never its value is the primary information-disclosure
    control — not the redaction filter, whose regexes are marker-anchored.
    """
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
        assert record.package == "market_data_client"  # type: ignore[attr-defined]
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
    """T-29-22: drive a real ``logger.warning(..., extra=...)``, not ``setattr``.

    ``LogRecord.__init__`` cannot reproduce the failure — only
    ``Logger.makeRecord`` refuses to overwrite an existing attribute.
    """
    logger = logging.getLogger("market_data_client")
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
    """Lock 9: a handler exception must not reach the caller."""
    logger = logging.getLogger("market_data_client")
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
# Locks 5-7 — dedupe triple and deterministic ordering
# ---------------------------------------------------------------------------


def test_list_elements_collapse_under_an_index_free_path(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Lock 5: 5,000 identically-diverging catalogue rows emit ONE record."""
    payload = {"titulo": "t", "hojas": [{"nombre": "n"} for _ in range(50)]}
    obj, records = _walk(_Nested, payload, caplog)

    assert len(obj.hojas) == 50
    assert _tuples(records) == [(".hojas[].dias", "missing")]


def test_distinct_kinds_at_the_same_path_stay_distinct(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Lock 5: ``missing`` and ``type`` at one path are two different facts."""
    payload = {"titulo": "t", "hojas": [{"dias": "x"}, {}]}
    _, records = _walk(_Nested, payload, caplog)

    assert set(_tuples(records)) == {
        (".hojas[].nombre", "missing"),
        (".hojas[].dias", "type"),
        (".hojas[].dias", "missing"),
    }


def test_one_scope_shared_across_two_walks_emits_once(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Lock 6: every model decoded from ONE response shares ONE scope."""
    scope = DecodeScope()
    _, first = _walk(_Scalars, {}, caplog, sink=scope)
    _, second = _walk(_Scalars, {}, caplog, sink=scope)

    assert len(first) == 4
    assert second == []


def test_emission_order_is_extras_sorted_then_declaration_order(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Lock 7: extras first in sorted key order, then ``fields()`` order."""
    payload = {"zeta": 1, "alfa": 2}
    _, records = _walk(_Scalars, payload, caplog)

    assert [path for path, _ in _tuples(records)] == [
        ".alfa",
        ".zeta",
        ".s",
        ".i",
        ".f",
        ".b",
    ]


# ---------------------------------------------------------------------------
# Lock 4 — strict mode
# ---------------------------------------------------------------------------


def test_strict_mode_raises_with_the_exact_field_path_and_no_wire_value() -> None:
    """T-29-23: the message carries the path and the type names, never a value."""
    token = _decode.STRICT_DECODE.set(True)
    try:
        with pytest.raises(MarketDataDecodeError) as excinfo:
            walk_model(
                _Scalars,
                {"s": "a", "i": "SENTINEL-WIRE-VALUE", "f": 1.0, "b": True},
                policy=POLICY,
                sink=DecodeScope(),
            )
    finally:
        _decode.STRICT_DECODE.reset(token)

    err = excinfo.value
    assert isinstance(err, MarketDataError)
    assert err.field_path == ".i"
    assert err.declared_type == "int"
    assert err.observed_type == "str"
    assert err.model == "_Scalars"
    assert "SENTINEL-WIRE-VALUE" not in str(err)


def test_strict_mode_raises_on_missing() -> None:
    """Lock 4: ``missing`` is fatal under strict mode."""
    token = _decode.STRICT_DECODE.set(True)
    try:
        with pytest.raises(MarketDataDecodeError) as excinfo:
            walk_model(_Scalars, {}, policy=POLICY, sink=DecodeScope())
    finally:
        _decode.STRICT_DECODE.reset(token)

    assert excinfo.value.field_path == ".s"


def test_strict_mode_raises_on_non_dict() -> None:
    """Lock 4: a ``null``/204 body is fatal under strict mode, at the root path."""
    token = _decode.STRICT_DECODE.set(True)
    try:
        with pytest.raises(MarketDataDecodeError) as excinfo:
            walk_model(_Scalars, None, policy=POLICY, sink=DecodeScope())
    finally:
        _decode.STRICT_DECODE.reset(token)

    assert excinfo.value.field_path == ""
    assert excinfo.value.observed_type == "NoneType"


def test_strict_mode_never_raises_on_an_extra_wire_key(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Lock 4, signed: vendor growth arrives on the vendor's schedule, not ours."""
    token = _decode.STRICT_DECODE.set(True)
    caplog.clear()
    try:
        with caplog.at_level(logging.DEBUG, logger="market_data_client"):
            kwargs = walk_model(
                _Scalars,
                {"s": "a", "i": 1, "f": 1.0, "b": True, "vendorNuevo": 7},
                policy=POLICY,
                sink=DecodeScope(),
            )
    finally:
        _decode.STRICT_DECODE.reset(token)

    assert _Scalars(**kwargs) == _Scalars("a", 1, 1.0, True)
    assert _tuples(_divergences(caplog)) == [(".vendorNuevo", "extra")]


# ---------------------------------------------------------------------------
# D-09 — Literal membership is never enforced
# ---------------------------------------------------------------------------


def test_literal_membership_is_never_enforced(caplog: pytest.LogCaptureFixture) -> None:
    """``29-DLOCK-RESPONSE-LITERAL.md``: an out-of-set value rides through unchanged."""
    obj, records = _walk(_WithLiteral, {"lado": "zzz"}, caplog)

    assert obj.lado == "zzz"
    assert records == []


def test_literal_reports_a_wrong_runtime_type(caplog: pytest.LogCaptureFixture) -> None:
    """What IS validated is the runtime type of the literal's members."""
    _, records = _walk(_WithLiteral, {"lado": 7}, caplog)

    assert _tuples(records) == [(".lado", "type")]


def test_literal_membership_is_not_enforced_under_strict_mode() -> None:
    """The D-09 lock holds in strict mode too — vendor enum growth is never fatal."""
    token = _decode.STRICT_DECODE.set(True)
    try:
        kwargs = walk_model(_WithLiteral, {"lado": "zzz"}, policy=POLICY, sink=DecodeScope())
    finally:
        _decode.STRICT_DECODE.reset(token)

    # ``cast`` is the ASSERTION's point, not a workaround: the declared type is
    # ``Literal["BUY", "SELL"] | None``, so mypy calls the comparison
    # non-overlapping — which is exactly the lock being pinned. The walker lets
    # an off-Literal member through at RUNTIME, and that runtime fact is what
    # this test measures.
    assert cast(Any, _WithLiteral(**kwargs).lado) == "zzz"


def test_optional_field_stays_none_without_a_divergence(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """``T | None`` is an explicit opt-in to nullable — absence is not a divergence."""
    obj, records = _walk(_WithLiteral, {}, caplog)

    assert obj.lado is None
    assert records == []


# ---------------------------------------------------------------------------
# Delegation — ``models.py`` routes through the walker
# ---------------------------------------------------------------------------


def test_safemodel_from_api_keeps_its_single_positional_parameter() -> None:
    """The preserved public contract: exactly one positional argument."""
    assert list(inspect.signature(SafeModel.from_api).parameters) == ["payload"]


def test_safemodel_from_api_delegates_to_the_walker() -> None:
    """``models.py`` carries no second copy of the coercion logic."""
    source = pathlib.Path(inspect.getfile(models)).read_text(encoding="utf-8")
    assert "_decode.walk_model" in source
    assert "_decode.walk_field" in source


def test_coerce_is_still_callable_with_identical_return_values() -> None:
    """The back-compat shim keeps its two-positional signature and its returns."""
    assert list(inspect.signature(models._coerce).parameters) == ["value", "hint"]
    assert models._coerce(None, str) == ""
    assert models._coerce(None, int) == 0
    assert models._coerce(None, float) == 0.0
    assert models._coerce(None, bool) is False
    assert models._coerce(None, list[str]) == []
    assert models._coerce(None, str | None) is None
    assert models._coerce(True, int) == 0
    assert models._coerce(3, float) == 3.0


def test_real_reference_model_missing_field_defaults_and_now_reports(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A shipped reference model still substitutes — and now says so."""
    obj, records = _from_api(models.Instrument.from_api, caplog, {"symbol": "DLR/DIC26"})

    assert obj.symbol == "DLR/DIC26"
    assert obj.marketId == ""
    assert obj.expired is False
    assert (".marketId", "missing") in _tuples(records)


def test_real_model_extra_wire_key_reports_and_builds_unchanged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Extra-key detection is the capability ``_coerce`` structurally could not have."""
    payload = {
        "marketSegmentId": "DDF",
        "marketId": "ROFX",
        "description": "d",
        "vendorNuevo": 1,
    }
    obj, records = _from_api(models.Segment.from_api, caplog, payload)

    assert obj.marketSegmentId == "DDF"
    assert (".vendorNuevo", "extra") in _tuples(records)


def test_no_call_site_exempt_safemodel_appears_as_a_nested_field_type() -> None:
    """Plan 02's carried-forward finding, discharged structurally for market-data.

    ``walk_field`` walks a nested model through ``walk_model`` directly rather
    than ``hint.from_api(value)``, so that a nested path stays dotted from the
    decode root. The consequence is that any CALL-SITE-EXEMPT behaviour — a
    ``from_api`` OVERRIDE, or ``models._apply_mapping_policy``'s post-walk pass
    over a ``dict[...]``-declaring model — would be BYPASSED for a model reached
    as another model's field type. This test asserts the precondition that makes
    the bypass moot: no model carrying such an exemption is ever declared as
    another model's field type. If a future plan nests one, this test fails and
    the walker needs an explicit hook.

    **Phase 31 (TYP-02) NARROWING.** Until Phase 31 this was stated as the blanket
    "no shipped ``SafeModel`` is EVER a nested field type", because at the time no
    shipped market-data model had a nested-model field at all, so the blanket and
    the precise forms were indistinguishable. Phase 31 declares the six health
    models, four of which (:class:`~market_data_client.models.HealthAuth`,
    :class:`~market_data_client.models.FeedMarket`,
    :class:`~market_data_client.models.FeedPipeline`,
    :class:`~market_data_client.models.FeedIngestor`) legitimately ARE nested
    field types — and none of them carries an exemption, so nothing is bypassed.
    The guard is therefore narrowed to the invariant it actually protects, NOT
    relaxed: the two companion tests below
    (``test_no_mapping_carrying_model_is_ever_a_nested_field_type`` and
    ``test_models_with_a_from_api_override_are_never_a_nested_field_type``) pin
    the same two exemption sets independently, so a regression on either axis
    still fails in three places.
    """
    shipped = [
        obj
        for obj in vars(models).values()
        if isinstance(obj, type) and issubclass(obj, SafeModel) and obj is not SafeModel
    ]
    assert shipped, "no shipped SafeModel subclasses found — the guard would be vacuous"
    exempt = [
        obj
        for obj in shipped
        if obj.__dict__.get("from_api") is not None
        or any(models._is_mapping(h) for h in _decode.hints_for(cast(Any, obj)).values())
    ]
    assert exempt, "no call-site-exempt model found — the guard would be vacuous"
    for cls in shipped:
        # ``cast(Any, cls)`` mirrors the ``exempt`` comprehension four lines
        # above and ``_decode.py``'s own discipline: ``hints_for`` is
        # ``lru_cache``-wrapped, so its parameter is ``Hashable``, which
        # ``type[SafeModel]``'s inherited ``__hash__`` signature does not satisfy.
        hints = _decode.hints_for(cast(Any, cls))
        for field in dataclasses.fields(cls):  # type: ignore[arg-type]
            rendered = str(hints[field.name])
            for other in exempt:
                assert other.__name__ not in rendered, (cls.__name__, field.name, rendered)


# ---------------------------------------------------------------------------
# Exemption (a) — ``MarketDataSnapshot.received_at`` injection bypass
# ---------------------------------------------------------------------------


def test_snapshot_signature_preserved() -> None:
    """Matrix row 3: the extended signature survives the delegation rewrite."""
    signature = inspect.signature(MarketDataSnapshot.from_api)
    assert list(signature.parameters) == ["payload", "received_at"]
    received_at = signature.parameters["received_at"]
    assert received_at.kind is inspect.Parameter.KEYWORD_ONLY
    assert received_at.default == 0.0


def test_snapshot_received_at_not_walked(caplog: pytest.LogCaptureFixture) -> None:
    """T-29-24: the client stamp wins over a conflicting wire value, silently.

    Matrix Section 3(a): ``received_at`` is a CLIENT-SIDE stamp, not a wire
    field. Routing it through the walker would let a wire-supplied value win
    over the client's own timestamp — a spoofing surface — and would collapse
    the stamp to ``0.0`` whenever the payload omits the key.
    """
    payload = {
        "symbol": "DLR/DIC26",
        "market_id": "ROFX",
        "active": True,
        "entries": ["BI"],
        "market_data": {},
        "staleness_seconds": 1.0,
        # The decoy: a wire value that must NEVER win.
        "received_at": 999.0,
    }
    obj, records = _from_api(MarketDataSnapshot.from_api, caplog, payload, received_at=123.5)

    assert obj.received_at == 123.5
    assert [path for path, _ in _tuples(records)] == []


def test_snapshot_received_at_absent_from_payload_still_takes_the_stamp(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The field is skipped entirely: no walk, no ``missing`` record, no ``0.0``."""
    payload = {
        "symbol": "DLR/DIC26",
        "market_id": "ROFX",
        "active": True,
        "entries": ["BI"],
        "market_data": {},
        "staleness_seconds": 1.0,
    }
    obj, records = _from_api(MarketDataSnapshot.from_api, caplog, payload, received_at=7.25)

    assert obj.received_at == 7.25
    assert ".received_at" not in [path for path, _ in _tuples(records)]


def test_snapshot_wrong_typed_wire_received_at_emits_no_divergence(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Even a garbage wire ``received_at`` produces no record — the key is not read."""
    payload = {
        "symbol": "DLR/DIC26",
        "market_id": "ROFX",
        "active": True,
        "entries": ["BI"],
        "market_data": {},
        "staleness_seconds": 1.0,
        "received_at": "not-a-float",
    }
    obj, records = _from_api(MarketDataSnapshot.from_api, caplog, payload, received_at=4.5)

    assert obj.received_at == 4.5
    assert ".received_at" not in [path for path, _ in _tuples(records)]


def test_snapshot_received_at_is_never_fatal_under_strict_mode() -> None:
    """A client-stamped field cannot be the reason a strict driver run fails."""
    token = _decode.STRICT_DECODE.set(True)
    try:
        snapshot = MarketDataSnapshot.from_api(
            {
                "symbol": "DLR/DIC26",
                "market_id": "ROFX",
                "active": True,
                "entries": ["BI"],
                "market_data": {},
                "staleness_seconds": 1.0,
            },
            received_at=11.0,
        )
    finally:
        _decode.STRICT_DECODE.reset(token)

    assert snapshot.received_at == 11.0


def test_snapshot_other_fields_still_report(caplog: pytest.LogCaptureFixture) -> None:
    """The exemption is scoped to ONE field: every other field still walks."""
    _, records = _from_api(MarketDataSnapshot.from_api, caplog, {}, received_at=1.0)

    paths = [path for path, _ in _tuples(records)]
    assert ".symbol" in paths
    # Phase 33 SC-2 widened ``.staleness_seconds`` to ``float | None``, so it no
    # longer reports on an absent key. ``.active`` is still declared
    # non-Optional and carries the same evidence: the exemption is scoped to
    # ``received_at`` and every OTHER declared field still walks and still
    # reports.
    assert ".active" in paths
    assert ".received_at" not in paths


def test_symbol_received_at_is_a_wire_field_not_a_stamp(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Matrix Section 3(a) near-miss: the exemption is class-keyed, not name-keyed.

    :class:`Symbol` declares a ``received_at`` too, but there it is the SERVER's
    ingest timestamp read straight off the payload. A field-name-keyed exemption
    would silently break it.
    """
    obj, _ = _from_api(
        Symbol.from_api,
        caplog,
        {"symbol": "S", "market_id": "ROFX", "active": True, "received_at": "2026-08-19T00:00:00Z"},
    )

    assert obj.received_at == "2026-08-19T00:00:00Z"


# ---------------------------------------------------------------------------
# Exemption (b) — ``Symbol.from_api`` mirror + two-argument ``super()``
# ---------------------------------------------------------------------------


def test_symbol_market_id_mirror_preserved(caplog: pytest.LogCaptureFixture) -> None:
    """Matrix Section 3(b): the wire's snake_case key fills the deprecated alias.

    The mirror runs BEFORE the walker sees the payload, so after it ``marketId``
    is a declared field with a present key — no ``extra`` record fires for the
    mirrored source key, which is correct: the client synthesized it, the vendor
    did not send it.
    """
    obj, records = _from_api(
        Symbol.from_api, caplog, {"symbol": "S", "market_id": "ROFX", "active": True}
    )

    assert obj.marketId == "ROFX"
    assert obj.market_id == "ROFX"
    kinds = _tuples(records)
    assert (".marketId", "extra") not in kinds
    assert (".market_id", "extra") not in kinds
    assert (".marketId", "missing") not in kinds


def test_symbol_explicit_market_id_still_wins(caplog: pytest.LogCaptureFixture) -> None:
    """The mirror only FILLS an absent key — it never overwrites."""
    obj, _ = _from_api(
        Symbol.from_api,
        caplog,
        {"symbol": "S", "marketId": "EXPLICIT", "market_id": "ROFX", "active": True},
    )

    assert obj.marketId == "EXPLICIT"


def test_symbol_uses_two_arg_super() -> None:
    """Matrix Section 3(b): a zero-argument ``super()`` raises under the slots rebuild.

    ``@dataclass(slots=True)`` REBUILDS the class object, so the implicit
    ``__class__`` cell a zero-argument ``super()`` captures still points at the
    pre-slots class and raises ``TypeError: obj must be an instance or subtype
    of type``. Exercising the override is the runtime half of the proof; the
    source grep is the half that survives a refactor that happens to work.
    """
    source = pathlib.Path(inspect.getfile(models)).read_text(encoding="utf-8")
    assert "super(Symbol, cls)" in source

    # The runtime half: this call is what a zero-arg ``super()`` would break.
    obj = Symbol.from_api({"symbol": "S", "market_id": "ROFX", "active": True})
    assert isinstance(obj, Symbol)
    assert obj.symbol == "S"


def test_symbol_non_dict_payload_survives_the_mirror_guard() -> None:
    """The mirror's ``isinstance(payload, dict)`` guard keeps the non-dict path alive."""
    obj = Symbol.from_api(None)

    assert obj.symbol == ""
    assert obj.marketId == ""


# ---------------------------------------------------------------------------
# D-03 — the mode carrier on the four public entry points
# ---------------------------------------------------------------------------


def test_strict_mode_from_sync_constructor() -> None:
    """Entry point 1: ``Client(strict_decode=True)``."""
    with Client(strict_decode=True) as client:
        assert client._state.strict_decode is True
    with Client() as client:
        assert client._state.strict_decode is False


def test_strict_mode_from_async_constructor() -> None:
    """Entry point 2: ``AsyncClient(strict_decode=True)``."""
    client = AsyncClient(strict_decode=True)
    assert client._state.strict_decode is True
    assert AsyncClient()._state.strict_decode is False


def test_strict_mode_from_sync_configure() -> None:
    """Entry point 3 + Pitfall 5: a later unrelated ``configure`` must not reset it."""
    market_data_client.configure(strict_decode=True)
    assert market_data_client.client._get_default()._state.strict_decode is True

    market_data_client.configure(base_url=_BASE)
    assert market_data_client.client._get_default()._state.strict_decode is True

    market_data_client.configure(strict_decode=False)
    assert market_data_client.client._get_default()._state.strict_decode is False


def test_strict_mode_from_async_configure() -> None:
    """Entry point 4 + Pitfall 5, on the independent async singleton."""
    aio.configure(strict_decode=True)
    assert aio._get_default()._state.strict_decode is True

    aio.configure(base_url=_BASE)
    assert aio._get_default()._state.strict_decode is True

    aio.configure(strict_decode=False)
    assert aio._get_default()._state.strict_decode is False


def test_strict_mode_is_not_env_backed() -> None:
    """T-29-16: a plain ``bool = False``, never a ``field(default_factory=...)``."""
    from market_data_client._state import _ClientState

    field = next(f for f in dataclasses.fields(_ClientState) if f.name == "strict_decode")
    assert field.default is False
    assert field.default_factory is dataclasses.MISSING


def test_strict_mode_view_inherits() -> None:
    """T-29-17: the flag lives on the SHARED ``_ClientState``, never in ``__slots__``."""
    with Client(strict_decode=True) as parent:
        view = parent.with_options(max_retries=5)
        assert view._state is parent._state
        assert view._state.strict_decode is True

        parent._state.strict_decode = False
        assert view._state.strict_decode is False

    assert "strict_decode" not in Client.__slots__
    assert "strict_decode" not in AsyncClient.__slots__


# ---------------------------------------------------------------------------
# D-03 — the two bind sites
# ---------------------------------------------------------------------------


def test_strict_mode_bound_by_sync_request(httpx_mock: HTTPXMock) -> None:
    """``Client._request`` binds the mode from the shared state."""
    httpx_mock.add_response(url=f"{_BASE}/health", method="GET", json=_HEALTH_BODY)

    with Client(base_url=_BASE, strict_decode=True) as client:
        client.get_health()

    assert _decode.STRICT_DECODE.get() is True


async def test_strict_mode_bound_by_async_request(httpx_mock: HTTPXMock) -> None:
    """``AsyncClient._request`` binds the mode too — the dual-surface mirror."""
    httpx_mock.add_response(url=f"{_BASE}/health", method="GET", json=_HEALTH_BODY)

    client = AsyncClient(base_url=_BASE, strict_decode=True)
    try:
        await client.get_health()
    finally:
        await client.aclose()

    assert _decode.STRICT_DECODE.get() is True


def test_no_reset_after_request(httpx_mock: HTTPXMock) -> None:
    """The absence of a reset is the invariant: the decode happens AFTER the return.

    Also lock 6's stronger claim: the scope bound during ``_request`` is the
    SAME object after the method returns, which is what makes the dedupe
    collapse fire across every element of a top-level ``list[Model]`` parse.
    """
    httpx_mock.add_response(url=f"{_BASE}/health", method="GET", json={"status": "ok"})

    with Client(base_url=_BASE, strict_decode=True) as client:
        spec = market_data_client._core.build_health_request(client._state)
        client._request(spec)
        scope = _decode.DECODE_SCOPE.get()

    assert _decode.STRICT_DECODE.get() is True
    assert scope is not None
    assert _decode.DECODE_SCOPE.get() is scope


def test_request_binds_a_fresh_scope_per_response(httpx_mock: HTTPXMock) -> None:
    """Lock 6: a process-lifetime scope is explicitly rejected."""
    httpx_mock.add_response(url=f"{_BASE}/health", method="GET", json={"status": "ok"})
    httpx_mock.add_response(url=f"{_BASE}/health", method="GET", json={"status": "ok"})

    with Client(base_url=_BASE) as client:
        client.get_health()
        first = _decode.DECODE_SCOPE.get()
        client.get_health()
        second = _decode.DECODE_SCOPE.get()

    assert first is not None
    assert second is not None
    assert first is not second


# ---------------------------------------------------------------------------
# Scope plumbing + ``hints_for`` cache
# ---------------------------------------------------------------------------


def test_hints_for_is_cache_backed() -> None:
    """The 89%-of-decode-cost win: stringified annotations resolve once per class."""
    _decode.hints_for(_Scalars)
    before = _decode.hints_for.cache_info().hits
    _decode.hints_for(_Scalars)
    _decode.hints_for(_Scalars)

    assert _decode.hints_for.cache_info().hits > before


def test_silent_sink_records_nothing_emits_nothing_and_never_raises(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """``SILENT_SINK`` is inert even under strict mode."""
    token = _decode.STRICT_DECODE.set(True)
    caplog.clear()
    try:
        with caplog.at_level(logging.DEBUG, logger="market_data_client"):
            _decode.SILENT_SINK("M", ".x", "missing", "str", "NoneType")
    finally:
        _decode.STRICT_DECODE.reset(token)

    assert _divergences(caplog) == []


def test_current_sink_without_a_bound_scope_returns_a_fresh_per_call_scope() -> None:
    """Lock 6: never a process-lifetime scope."""
    _decode.DECODE_SCOPE.set(None)

    assert _decode.current_sink() is not _decode.current_sink()


def test_open_request_scope_binds_a_scope_that_current_sink_reuses() -> None:
    """The bind is what makes one response's decodes share one dedupe set."""
    scope = _decode.open_request_scope()

    assert _decode.current_sink() is scope
    assert _decode.DECODE_SCOPE.get() is scope


def test_walk_field_preserves_every_coercion_return_value() -> None:
    """The merge gate in miniature: substitution behaviour is byte-unchanged."""
    sink = DecodeScope()
    kwargs: dict[str, Any] = {"path": "", "model": "M", "policy": POLICY, "sink": sink}

    assert walk_field(None, str, **kwargs) == ""
    assert walk_field(None, int, **kwargs) == 0
    assert walk_field(None, float, **kwargs) == 0.0
    assert walk_field(None, bool, **kwargs) is False
    assert walk_field(None, list[str], **kwargs) == []
    assert walk_field(None, str | None, **kwargs) is None
    assert walk_field(True, int, **kwargs) == 0
    assert walk_field(3, float, **kwargs) == 3.0
    assert walk_field("keep", str, **kwargs) == "keep"


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
        with caplog.at_level(logging.DEBUG, logger="market_data_client"):
            for _ in range(2):
                with pytest.raises(MarketDataDecodeError) as excinfo:
                    walk_model(_Scalars, payload, policy=POLICY, sink=scope)
                assert excinfo.value.field_path == ".s"
    finally:
        _decode.STRICT_DECODE.reset(token)

    # The record survives the raise, on BOTH attempts: a strict run still leaves
    # the divergence on the paquete logger (lock 9 — ``_emit`` never raises).
    paths = [r.field_path for r in _divergences(caplog)]  # type: ignore[attr-defined]
    assert paths == [".s", ".s"]


# ---------------------------------------------------------------------------
# Phase 29 code review, CR-04 — a wire key is payload content (lock 11)
# ---------------------------------------------------------------------------


def test_extra_key_with_a_newline_cannot_forge_a_log_line(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """CR-04: a control character in a wire key never reaches ``field_path``."""
    payload = {"s": "a", "i": 1, "f": 1.0, "b": True, "a\nWARNING:root: forged": "x"}
    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="market_data_client"):
        walk_model(_Scalars, payload, policy=POLICY, sink=DecodeScope())

    paths = [r.field_path for r in _divergences(caplog)]  # type: ignore[attr-defined]
    assert paths == [".a?WARNING?root??forged"]
    assert all("\n" not in p for p in paths)


def test_extra_key_length_is_bounded(caplog: pytest.LogCaptureFixture) -> None:
    """CR-04: key length is payload-controlled, so it is truncated (lock 11)."""
    payload = {"s": "a", "i": 1, "f": 1.0, "b": True, "X" * 200: "x"}
    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="market_data_client"):
        walk_model(_Scalars, payload, policy=POLICY, sink=DecodeScope())

    (record,) = _divergences(caplog)
    assert record.field_path == "." + "X" * 64 + "..."  # type: ignore[attr-defined]


def test_extra_key_that_is_not_a_string_is_stringified_and_sanitized(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """CR-04: a hand-built dict can carry a non-``str`` key; the sort stays total."""
    payload: dict[Any, Any] = {"s": "a", "i": 1, "f": 1.0, "b": True, 7: "x", ("t",): "y"}
    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="market_data_client"):
        walk_model(_Scalars, payload, policy=POLICY, sink=DecodeScope())

    paths = {r.field_path for r in _divergences(caplog)}  # type: ignore[attr-defined]
    assert paths == {".7", ".??t???"}


# ---------------------------------------------------------------------------
# Phase 29 code review, CR-03 — the mapping axis reaches market-data too
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _RequiredMapping(SafeModel):
    """Module-local carrier for CR-03's REQUIRED-mapping property (Phase 33 SC-2).

    CR-03's contract — a ``dict[...]``-declared field is never a silent ``None``:
    it substitutes ``{}`` and REPORTS — used to be pinned against
    ``MarketDataSnapshot.market_data``. Phase 33 SC-2 widened that field to
    ``dict[str, Any] | None`` because the vendor sends ``null`` legitimately on
    the no-data row, which left no shipped model declaring a required mapping.

    The property is unchanged; only its carrier moved. Restating it here keeps
    the mapping pass under test the day a future model declares a required
    mapping again — the alternative, deleting the rows, would have retired a
    live contract because its example changed.
    """

    payload: dict[str, Any]


def test_absent_required_mapping_field_reports_missing_and_substitutes_the_empty_dict(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """CR-03: a REQUIRED ``dict[...]`` field is never a silent ``None``."""
    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="market_data_client"):
        obj = _RequiredMapping.from_api({})

    assert obj.payload == {}
    kinds = {(r.field_path, r.divergence) for r in _divergences(caplog)}  # type: ignore[attr-defined]
    assert (".payload", "missing") in kinds


def test_optional_mapping_field_keeps_none_and_reports_nothing(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Phase 33 SC-2: under ``dict[...] | None`` a ``null`` is the declared shape.

    The mapping pass unwraps ``Optional`` to decide whether a field is a mapping
    at all, so without an explicit guard it kept substituting ``{}`` and kept
    reporting ``missing`` one line after the walker had correctly honoured the
    ``| None``. This is the row that fails if that guard is removed.
    """
    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="market_data_client"):
        snap = MarketDataSnapshot.from_api(
            {"symbol": "GGAL", "market_id": "M", "active": True, "market_data": None},
            received_at=1.0,
        )

    assert snap.market_data is None
    paths = {r.field_path for r in _divergences(caplog)}  # type: ignore[attr-defined]
    assert ".market_data" not in paths


def test_wrong_typed_mapping_field_reports_type_and_substitutes_the_empty_dict(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """CR-03: a non-mapping wire value is a ``type`` divergence, not a pass-through."""
    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="market_data_client"):
        snap = MarketDataSnapshot.from_api(
            {
                "symbol": "GGAL",
                "market_id": "M",
                "active": True,
                "entries": [],
                "market_data": ["not", "a", "mapping"],
                "staleness_seconds": 0.0,
            },
            received_at=1.0,
        )

    assert snap.market_data == {}
    kinds = {(r.field_path, r.divergence) for r in _divergences(caplog)}  # type: ignore[attr-defined]
    assert (".market_data", "type") in kinds


def test_strict_mode_raises_on_an_absent_required_mapping_field() -> None:
    """CR-03: lock 4 applies to the mapping axis exactly as to every other axis."""
    token = _decode.STRICT_DECODE.set(True)
    try:
        with pytest.raises(MarketDataDecodeError) as excinfo:
            _RequiredMapping.from_api({})
    finally:
        _decode.STRICT_DECODE.reset(token)

    assert excinfo.value.field_path == ".payload"
    assert excinfo.value.declared_type == "dict"


def test_strict_mode_does_not_raise_on_a_null_optional_mapping_field() -> None:
    """Phase 33 SC-2: the strict raise the 33-05 run measured stops firing.

    This is the arm with teeth — the fix's whole point is that a legitimate
    vendor ``null`` is not fatal, while a wrong-typed value still is (see
    ``test_snapshot_no_data_row.py``).
    """
    token = _decode.STRICT_DECODE.set(True)
    try:
        snap = MarketDataSnapshot.from_api(
            {"symbol": "GGAL", "market_id": "M", "active": True, "market_data": None},
            received_at=1.0,
        )
    finally:
        _decode.STRICT_DECODE.reset(token)

    assert snap.market_data is None


def test_mapping_pass_is_silent_under_a_non_dict_payload(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Lock 8: ``non_dict`` stays terminal — the mapping pass adds no second record."""
    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="market_data_client"):
        snap = MarketDataSnapshot.from_api(None, received_at=1.0)

    # Phase 33 SC-2: the VALUE is now ``None`` (the field is ``| None``), but the
    # property under test is the RECORD SET — lock 8 says ``non_dict`` is
    # terminal and the mapping pass adds no second record. That is unchanged.
    assert snap.market_data is None
    kinds = [(r.field_path, r.divergence) for r in _divergences(caplog)]  # type: ignore[attr-defined]
    assert kinds == [("", "non_dict")]


def test_no_mapping_carrying_model_is_ever_a_nested_field_type() -> None:
    """Precondition that makes the call-site mapping pass complete (CR-03 / WR-03).

    ``walk_field`` recurses into a nested model through ``walk_model`` directly,
    so ``models.py``'s post-walk mapping pass — and every other ``from_api``
    override — is bypassed for a model reached as another model's field type.
    That is harmless only while no mapping-carrying model is ever declared as a
    field type. This mirrors matriz's test of the same name.
    """
    shipped = [
        obj
        for obj in vars(models).values()
        if isinstance(obj, type) and dataclasses.is_dataclass(obj) and issubclass(obj, SafeModel)
    ]
    carriers = {
        cls.__name__
        for cls in shipped
        if any(models._is_mapping(h) for h in _decode.hints_for(cast(Any, cls)).values())
    }
    assert carriers == {"MarketDataSnapshot"}

    nested_types: set[str] = set()
    for cls in shipped:
        for hint in _decode.hints_for(cast(Any, cls)).values():
            inner = models._strip_optional(hint)
            for candidate in (inner, *getattr(inner, "__args__", ())):
                if (
                    isinstance(candidate, type)
                    and dataclasses.is_dataclass(candidate)
                    and issubclass(candidate, SafeModel)
                ):
                    nested_types.add(candidate.__name__)

    assert carriers & nested_types == set()


def test_models_with_a_from_api_override_are_never_a_nested_field_type() -> None:
    """WR-03: every ``from_api`` exemption of the semantics matrix is top-level only.

    ``MarketDataSnapshot.from_api`` injects ``received_at`` (D-01) and
    ``Symbol.from_api`` mirrors ``market_id`` onto the deprecated ``marketId``
    alias. The walker builds a nested model with ``hint(**walk_model(...))`` and
    never calls ``from_api``, so both exemptions would be silently skipped for a
    nested occurrence. matriz pins the same precondition for its mapping axis;
    this is market-data's counterpart, and it fails loudly the day someone nests
    one of the two overriding models.
    """
    shipped = [
        obj
        for obj in vars(models).values()
        if isinstance(obj, type) and dataclasses.is_dataclass(obj) and issubclass(obj, SafeModel)
    ]
    overriding = {
        cls.__name__
        for cls in shipped
        if cls.__dict__.get("from_api") is not None  # declared on the class itself
    }
    assert overriding == {"MarketDataSnapshot", "Symbol"}

    nested_types: set[str] = set()
    for cls in shipped:
        for hint in _decode.hints_for(cast(Any, cls)).values():
            inner = models._strip_optional(hint)
            for candidate in (inner, *getattr(inner, "__args__", ())):
                if (
                    isinstance(candidate, type)
                    and dataclasses.is_dataclass(candidate)
                    and issubclass(candidate, SafeModel)
                ):
                    nested_types.add(candidate.__name__)

    assert overriding & nested_types == set()


# ---------------------------------------------------------------------------
# Phase 29 code review, CR-01 — a response's scope dies with its response
# ---------------------------------------------------------------------------


def test_a_retired_response_scope_never_serves_a_later_standalone_decode() -> None:
    """CR-01, lock 6: the scope ``_request`` binds is retired by its response's parse.

    ``_request`` binds without a reset (D-03), so before the fix the scope stayed
    bound for the rest of the thread's life and ``current_sink``'s per-call
    fallback was dead after the first HTTP call in the process: every standalone
    ``Model.from_api()`` reused that one request's dedupe set.
    """
    scope = _decode.open_request_scope()
    assert _decode.current_sink() is scope

    with _decode._response_scope() as owned:
        # Every model of ONE response — including every element of a top-level
        # ``list[Model]`` parse — still shares one scope, so lock 5 collapses.
        assert owned is scope
        assert _decode.current_sink() is scope
        assert _decode.current_sink() is scope

    assert scope.closed is True
    first = _decode.current_sink()
    second = _decode.current_sink()
    assert first is not scope
    assert second is not scope
    assert first is not second


def test_response_scope_retires_once_when_parsers_nest() -> None:
    """Re-entrancy: a parser delegating to another retires the scope on the outer exit."""
    _decode.open_request_scope()
    with _decode._response_scope() as outer:
        with _decode._response_scope() as inner:
            assert inner is outer
        assert outer.closed is False
    assert outer.closed is True


def test_response_scope_creates_its_own_when_no_request_bound_one() -> None:
    """A parser driven directly, with no preceding request, still owns a scope."""
    _decode.DECODE_SCOPE.set(None)
    with _decode._response_scope() as scope:
        assert _decode.DECODE_SCOPE.get() is scope
    assert scope.closed is True
    assert _decode.current_sink() is not scope


def test_two_standalone_from_api_calls_after_a_response_parse_both_report(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """CR-01: the false pass lock 6 rejects, reproduced and closed.

    Before the fix the second call decoded a divergent payload silently clean,
    because it inherited the previous response's dedupe set.
    """
    payload = {"vendorNewKey": 1}
    _decode.open_request_scope()
    with _decode._response_scope():
        Symbol.from_api(payload)

    with caplog.at_level(logging.DEBUG, logger="market_data_client"):
        caplog.clear()
        Symbol.from_api(payload)
        first = len(_divergences(caplog))
        caplog.clear()
        Symbol.from_api(payload)
        second = len(_divergences(caplog))

    assert first > 0
    assert second == first


# ---------------------------------------------------------------------------
# Phase 29 code review, WR-02 — an absent nested-model key is `missing`
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _CarriesNested(SafeModel):
    """A model whose declared field type is another model (WR-02)."""

    titulo: str
    hoja: _Leaf


def test_absent_nested_model_key_is_missing_on_the_outer_model(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """WR-02: lock 2's definition of ``missing``, and lock 1's ``model`` pairing.

    The walker used to recurse unconditionally, so an absent key whose declared
    type is a nested model reached ``walk_model`` as ``payload=None`` and was
    emitted as ``non_dict`` — attributed to the NESTED class at a path rooted in
    the OUTER decode. That pair names a decode site that does not exist, and
    lock 10 freezes it into a Phase 33 finding identity.
    """
    instance, records = _walk(_CarriesNested, {"titulo": "t"}, caplog)

    assert instance == _CarriesNested("t", _Leaf("", 0))
    triples = [(r.model, r.field_path, r.divergence) for r in records]  # type: ignore[attr-defined]
    assert triples == [("_CarriesNested", ".hoja", "missing")]


def test_non_dict_nested_payload_keeps_the_nested_attribution(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """WR-02: only ``None`` reclassifies — a real non-dict is still ``non_dict``."""
    _, records = _walk(_CarriesNested, {"titulo": "t", "hoja": "garbage"}, caplog)

    triples = [(r.model, r.field_path, r.divergence) for r in records]  # type: ignore[attr-defined]
    assert triples == [("_Leaf", ".hoja", "non_dict")]


def test_wrong_typed_list_field_still_reports_type(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """ROADMAP Phase 35 criterio 2, falsification half: the list site still reports.

    A ``str`` where a ``list[Model]`` is declared is NOT the legitimate-null case
    Phase 35 blesses: it is a wrong-typed value and it must keep emitting a
    ``type`` record, with the same ``[]`` return value it has today.

    This test is GREEN before plan 35-05 edits the walker and must stay GREEN
    after it. Its whole job is to redden if that edit's silencing over-reaches
    from ``value is None`` to every non-list value. The assertion is an EQUALITY
    against a one-element list rather than a membership check, so a second,
    spurious record would fail it too.
    """
    obj, records = _walk(_Nested, {"titulo": "t", "hojas": "garbage"}, caplog)

    assert obj.hojas == []
    triples = [(r.model, r.field_path, r.divergence) for r in records]  # type: ignore[attr-defined]
    assert triples == [("_Nested", ".hojas", "type")]
    assert records[0].declared_type == "list"  # type: ignore[attr-defined]
    assert records[0].observed_type == "str"  # type: ignore[attr-defined]


def test_strict_mode_still_raises_on_a_wrong_typed_list() -> None:
    """ROADMAP Phase 35 criterio 2: the list site stays FATAL under strict mode.

    The other half of the same falsification argument. Reporting and fatality
    are two separate dispositions in this walker — ``_INFO_KINDS`` exempts
    ``extra`` from the raise while still emitting it — so a walker edit could
    conceivably keep the record and lose the raise. Both are pinned.

    Green before plan 35-05's edit, and required to stay green after it. The
    assertion reaches into the exception's attributes rather than settling for
    its type, because an exception raised for a DIFFERENT divergence of the same
    payload would satisfy a bare check on the exception class alone.
    """
    token = _decode.STRICT_DECODE.set(True)
    try:
        with pytest.raises(MarketDataDecodeError) as excinfo:
            walk_model(
                _Nested,
                {"titulo": "t", "hojas": "garbage"},
                policy=POLICY,
                sink=DecodeScope(),
            )
    finally:
        _decode.STRICT_DECODE.reset(token)

    assert excinfo.value.field_path == ".hojas"
    assert excinfo.value.declared_type == "list"
    assert excinfo.value.observed_type == "str"
    assert excinfo.value.model == "_Nested"
