"""Behaviour contract for ``matriz_client._decode`` — matriz's divergent policy.

Phase 29 Plan 06 (DEC-01). matriz is the package whose decode semantics
genuinely differ from higyrus / market-data, and this suite is where the
"never harmonized in silence" requirement is actually tested. A mechanical
rewrite that made matriz behave like higyrus would pass a naive suite and
silently change published behaviour for every matriz consumer.

The seven documented differences of ``29-SEMANTICS-MATRIX.md`` row 5, each
with a dedicated test below:

1. a missing scalar stays ``None`` (never a typed zero);
2. a non-dict payload yields ``cls.empty()`` (never ``{}``-substitution);
3. a missing nested model yields that model's ``empty()``;
4. scalars pass through unvalidated (``scalar_passthrough=True``);
5. models carry no ``slots``;
6. ``empty()`` exists at all, and is silent;
7. ``UnknownFrame`` is not a ``_SafeModel`` and is exempt from extra-key
   reporting.

Plus the matriz-only **mapping axis**: a ``dict``-declared field falls back to
``{}``. The canonical walker has no ``dict`` branch (higyrus and market-data
declare no mapping fields), so that axis lives in ``models.py`` at the call
site — see ``_apply_mapping_policy`` and the tests under "Mapping axis".

Model fixtures are declared module-locally so the suite never depends on a
shipped model's field list — a shipped model gaining or losing a field must not
be able to turn a walker regression green. The exceptions are the tests that
are *about* a shipped class's contract (``UnknownFrame``, the nine
``types.py`` aliases, the nesting precondition), which drive the real classes.
"""

from __future__ import annotations

import ast
import dataclasses
import inspect
import logging
import pathlib
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

import pytest
from pytest_httpx import HTTPXMock

import matriz_client
from matriz_client import _decode, aio, models
from matriz_client._decode import POLICY, DecodeScope, walk_field, walk_model
from matriz_client.aio import AsyncClient
from matriz_client.client import Client
from matriz_client.exceptions import MatrizClientError, MatrizDecodeError
from matriz_client.models import UnknownFrame, _SafeModel
from matriz_client.types import (
    CFICode,
    Currency,
    MarketDataEntry,
    MarketId,
    OrderStatus,
    OrderType,
    SegmentId,
    Side,
    TimeInForce,
)

_MESSAGE = "decode divergence"

_CONTRACT_KEYS = (
    "package",
    "divergence",
    "field_path",
    "declared_type",
    "observed_type",
    "model",
)


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


# ---------------------------------------------------------------------------
# Module-local model fixtures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Leaf(_SafeModel):
    """Nested leaf with bare (non-Optional) scalar declarations."""

    name: str
    count: int


@dataclass(frozen=True)
class _Bare(_SafeModel):
    """One bare declaration per scalar policy axis."""

    s: str
    i: int
    f: float
    b: bool


@dataclass(frozen=True)
class _Mapping(_SafeModel):
    """The matriz-only mapping axis the canonical walker cannot express."""

    meta: dict[str, Any] = field(default_factory=dict)
    label: str | None = None


@dataclass(frozen=True)
class _Nested(_SafeModel):
    """Nested model + list-of-model, matriz's ``empty()``-flavoured defaults."""

    leaf: _Leaf = field(default_factory=_Leaf.empty)
    rows: list[_Leaf] = field(default_factory=list)
    tag: str | None = None


@dataclass(frozen=True)
class _Literals(_SafeModel):
    """Five of the nine published ``types.py`` aliases (D-09)."""

    side: Side | None = None
    ordType: OrderType | None = None
    marketId: MarketId | None = None
    status: OrderStatus | None = None
    currency: Currency | None = None


def _divergences(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [r for r in caplog.records if r.getMessage() == _MESSAGE]


def _pairs(caplog: pytest.LogCaptureFixture) -> list[tuple[str, str]]:
    return [(r.field_path, r.divergence) for r in _divergences(caplog)]


# ---------------------------------------------------------------------------
# Module surface + the policy constant (D-02 / D-07)
# ---------------------------------------------------------------------------


def test_all_exports_the_eleven_public_names() -> None:
    """The copy carries the canonical export list, unmodified."""
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


def test_policy_constant_is_matriz_row_of_the_semantics_matrix() -> None:
    """D-07: five of the seven axes differ from higyrus's constant, by design."""
    assert POLICY.missing_str is None
    assert POLICY.missing_int is None
    assert POLICY.missing_float is None
    assert POLICY.missing_bool is None
    assert POLICY.non_dict_model == "empty_classmethod"
    assert POLICY.scalar_passthrough is True
    assert POLICY.literal_enforced is False


def test_policy_is_not_the_higyrus_constant() -> None:
    """The 'never harmonize' guard, stated as an assertion rather than a comment."""
    higyrus_row = (
        "",
        0,
        0.0,
        False,
        "from_api_none",
        False,
        False,
    )
    matriz_row = dataclasses.astuple(POLICY)
    assert matriz_row != higyrus_row


def test_logger_name_is_this_package() -> None:
    assert _decode._LOGGER_NAME == "matriz_client"
    assert _decode._LOGGER.name == "matriz_client"


def test_context_var_names_are_package_prefixed() -> None:
    assert _decode.STRICT_DECODE.name == "matriz_client_strict_decode"
    assert _decode.DECODE_SCOPE.name == "matriz_client_decode_scope"


def test_decode_module_never_imports_models() -> None:
    """The import-cycle prohibition, checked on the AST rather than at runtime."""
    src = pathlib.Path(_decode.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    package_imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module is not None
        and node.module.startswith("matriz_client")
    }
    assert package_imports == {"matriz_client.exceptions"}


def test_matriz_decode_error_is_a_client_error_not_an_api_error() -> None:
    err = MatrizDecodeError(".precio", "float", "str", "Trade")
    assert isinstance(err, MatrizClientError)
    assert not isinstance(err, matriz_client.PrimaryAPIError)
    assert (err.field_path, err.declared_type, err.observed_type, err.model) == (
        ".precio",
        "float",
        "str",
        "Trade",
    )


# ---------------------------------------------------------------------------
# The five divergence classes in observable mode
# ---------------------------------------------------------------------------


def test_missing_scalar_is_none(caplog: pytest.LogCaptureFixture) -> None:
    """Difference 1: a missing declared ``str`` returns ``None``, NOT ``""``.

    This is the single most tempting cell to "fix" toward higyrus. Every
    published matriz consumer that checks ``if model.field is None`` depends
    on it.
    """
    with caplog.at_level(logging.DEBUG, logger="matriz_client"):
        obj = _Bare.from_api({})

    assert obj.s is None
    assert obj.i is None
    assert obj.f is None
    assert obj.b is None
    # And explicitly NOT the higyrus typed zeros.
    assert obj.s != ""
    assert obj.i != 0
    assert obj.f != 0.0
    assert obj.b is not False

    assert _pairs(caplog) == [
        (".s", "missing"),
        (".i", "missing"),
        (".f", "missing"),
        (".b", "missing"),
    ]


def test_wrong_typed_scalar_passes_through_and_reports(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Difference 4: ``scalar_passthrough`` — the wire value is returned as-is."""
    with caplog.at_level(logging.DEBUG, logger="matriz_client"):
        obj = _Bare.from_api({"s": 7, "i": "nope", "f": "nope", "b": "nope"})

    assert obj.s == 7
    assert obj.i == "nope"
    assert obj.f == "nope"
    assert obj.b == "nope"
    assert _pairs(caplog) == [
        (".s", "type"),
        (".i", "type"),
        (".f", "type"),
        (".b", "type"),
    ]


def test_bool_payload_never_collapses_into_an_int_field(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """``bool`` is an ``int`` subclass; the guard reports it and still passes through."""
    with caplog.at_level(logging.DEBUG, logger="matriz_client"):
        obj = _Bare.from_api({"s": "ok", "i": True, "f": 1.5, "b": True})

    assert obj.i is True
    assert (".i", "type") in _pairs(caplog)
    observed = {r.field_path: r.observed_type for r in _divergences(caplog)}
    assert observed[".i"] == "bool"


def test_int_into_a_float_field_widens_and_is_not_reported() -> None:
    """The ONE behavioural delta the seven policy axes do not cover.

    ``walk_field``'s ``float`` branch returns ``float(value)`` for any
    ``int | float``, *before* it consults ``scalar_passthrough``. matriz's old
    ``_convert`` had no scalar branch at all, so a wire ``10`` for a
    ``float``-declared field used to come back as the ``int`` ``10``; it now
    comes back as ``10.0``. Numerically identical (``10 == 10.0``), and it
    agrees with the field's own annotation — but it IS a type change on
    published surface, so it is pinned here rather than left to be discovered.

    Plan 02 signed this branch off deliberately: widening is a coercion, not a
    substituted default, which is why no divergence is reported for it.
    """
    order = models.Order.from_api({"orderQty": 10, "lastQty": 3})
    assert order.orderQty == 10
    assert isinstance(order.orderQty, float)
    assert order.lastQty == 3.0
    # An ``int`` into an ``int``-declared field is untouched, as before.
    assert models.MarketDataLevel.from_api({"size": 1000}).size == 1000
    assert isinstance(models.MarketDataLevel.from_api({"size": 1000}).size, int)


def test_missing_list_field_returns_empty_list_and_reports(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.DEBUG, logger="matriz_client"):
        obj = _Nested.from_api({"leaf": {"name": "n", "count": 1}})

    assert obj.rows == []
    assert (".rows", "missing") in _pairs(caplog)


def test_extra_wire_key_reports_at_info_and_leaves_the_model_untouched(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Lock 3: vendor growth is INFO-level information, never a defect."""
    with caplog.at_level(logging.DEBUG, logger="matriz_client"):
        obj = _Mapping.from_api({"meta": {}, "label": "x", "brandNewField": 1})

    assert not hasattr(obj, "brandNewField")
    extras = [r for r in _divergences(caplog) if r.divergence == "extra"]
    assert [r.field_path for r in extras] == [".brandNewField"]
    assert extras[0].levelno == logging.INFO
    assert extras[0].declared_type == "-"


def test_non_dict_returns_empty(caplog: pytest.LogCaptureFixture) -> None:
    """Difference 2 + lock 8: ``cls.empty()``, and exactly ONE record."""
    with caplog.at_level(logging.DEBUG, logger="matriz_client"):
        obj = _Nested.from_api("garbage")

    assert obj == _Nested.empty()
    records = _divergences(caplog)
    assert len(records) == 1
    assert (records[0].field_path, records[0].divergence) == ("", "non_dict")
    assert records[0].observed_type == "str"
    # No per-field ``missing`` records leaked out from under the non-dict path.
    assert [r.divergence for r in records] == ["non_dict"]


def test_none_payload_behaves_as_non_dict(caplog: pytest.LogCaptureFixture) -> None:
    """A 204 / ``null`` body emits one record, not one per declared field."""
    with caplog.at_level(logging.DEBUG, logger="matriz_client"):
        obj = _Bare.from_api(None)

    assert obj == _Bare.empty()
    records = _divergences(caplog)
    assert len(records) == 1
    assert records[0].divergence == "non_dict"
    assert records[0].observed_type == "NoneType"


def test_empty_dict_is_a_dict_and_reports_per_field_missing(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """``{}`` is still a dict: per-field ``missing`` records, no ``non_dict``."""
    with caplog.at_level(logging.DEBUG, logger="matriz_client"):
        _Bare.from_api({})

    kinds = {r.divergence for r in _divergences(caplog)}
    assert kinds == {"missing"}


def test_nested_missing_model_is_empty(caplog: pytest.LogCaptureFixture) -> None:
    """Difference 3: a missing nested model yields that model's ``empty()``."""
    with caplog.at_level(logging.DEBUG, logger="matriz_client"):
        obj = _Nested.from_api({"rows": [], "tag": "t"})

    assert obj.leaf == _Leaf.empty()
    assert obj.leaf.name is None
    assert obj.leaf.count is None


def test_nested_field_paths_are_dotted_and_index_free(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.DEBUG, logger="matriz_client"):
        _Nested.from_api({"leaf": {"name": "n"}, "rows": [{"name": "a"}, {"name": "b"}]})

    paths = [p for p, _ in _pairs(caplog)]
    assert ".leaf.count" in paths
    assert ".rows[].count" in paths
    assert not any("[0]" in p or "[1]" in p for p in paths)


# ---------------------------------------------------------------------------
# Mapping axis — matriz-only, lives at the call site (see models.py)
# ---------------------------------------------------------------------------


def test_dict_hint_branch(caplog: pytest.LogCaptureFixture) -> None:
    """A mapping-declared field with a non-mapping wire value returns ``{}``."""
    with caplog.at_level(logging.DEBUG, logger="matriz_client"):
        obj = _Mapping.from_api({"meta": "not-a-mapping", "label": "x"})

    assert obj.meta == {}
    assert (".meta", "type") in _pairs(caplog)
    declared = {r.field_path: r.declared_type for r in _divergences(caplog)}
    observed = {r.field_path: r.observed_type for r in _divergences(caplog)}
    assert declared[".meta"] == "dict"
    assert observed[".meta"] == "str"


def test_dict_hint_missing_key_returns_empty_mapping(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.DEBUG, logger="matriz_client"):
        obj = _Mapping.from_api({"label": "x"})

    assert obj.meta == {}
    assert (".meta", "missing") in _pairs(caplog)


def test_dict_hint_present_mapping_is_returned_verbatim(
    caplog: pytest.LogCaptureFixture,
) -> None:
    payload_meta = {"a": 1, "b": {"c": 2}}
    with caplog.at_level(logging.DEBUG, logger="matriz_client"):
        obj = _Mapping.from_api({"meta": payload_meta, "label": "x"})

    assert obj.meta == payload_meta
    assert [p for p, _ in _pairs(caplog)] == []


def test_shipped_mapping_fields_still_default_to_empty_dict() -> None:
    """The four shipped mapping fields — the ones ``test_models.py`` pins."""
    assert models.InstrumentDetail.from_api({}).tickPriceRanges == {}
    assert models.DetailedPosition.from_api({"account": "x"}).report == {}
    report = models.AccountReport.from_api({"accountName": "x"})
    assert report.portfolio == {}
    assert report.detailedAccountReports == {}


def test_no_mapping_carrying_model_is_ever_a_nested_field_type() -> None:
    """Precondition that makes the call-site mapping pass complete.

    ``walk_field`` recurses into a nested model through ``walk_model``
    directly, so ``models.py``'s post-walk mapping pass is bypassed for a model
    reached as another model's field. That is harmless only while no
    mapping-carrying model is ever declared as a field type. If a future plan
    nests one, this test fails and the pass needs to move into the walker.
    """
    shipped = [
        obj
        for obj in vars(models).values()
        if isinstance(obj, type) and dataclasses.is_dataclass(obj) and issubclass(obj, _SafeModel)
    ]
    carriers = {
        cls.__name__
        for cls in shipped
        if any(models._is_mapping(h) for h in _decode.hints_for(cls).values())
    }
    assert carriers, "expected at least InstrumentDetail / DetailedPosition / AccountReport"

    nested_types: set[str] = set()
    for cls in shipped:
        for hint in _decode.hints_for(cls).values():
            inner = models._strip_optional(hint)
            for candidate in (inner, *getattr(inner, "__args__", ())):
                if (
                    isinstance(candidate, type)
                    and dataclasses.is_dataclass(candidate)
                    and issubclass(candidate, _SafeModel)
                ):
                    nested_types.add(candidate.__name__)

    assert carriers & nested_types == set()


# ---------------------------------------------------------------------------
# ``empty()`` is silent (T-29-33)
# ---------------------------------------------------------------------------


def test_empty_emits_nothing(caplog: pytest.LogCaptureFixture) -> None:
    """Difference 6: ``empty()`` builds defaults, it does not decode wire data."""
    _decode.STRICT_DECODE.set(True)
    with caplog.at_level(logging.DEBUG, logger="matriz_client"):
        obj = _Nested.empty()
        bare = _Bare.empty()
        mapping = _Mapping.empty()

    assert _divergences(caplog) == []
    assert obj.leaf == _Leaf.empty()
    assert obj.rows == []
    assert bare.s is None
    assert mapping.meta == {}


def test_empty_is_silent_even_as_a_default_factory(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """``empty()`` is used as a ``default_factory`` on shipped models."""
    _decode.STRICT_DECODE.set(True)
    with caplog.at_level(logging.DEBUG, logger="matriz_client"):
        snapshot = models.MarketDataSnapshot.empty()
        detail = models.InstrumentDetail.empty()

    assert _divergences(caplog) == []
    assert models.MarketDataEntryValue.empty() == snapshot.SE
    assert detail.tickPriceRanges == {}


def test_non_dict_path_reuses_the_empty_shape() -> None:
    """The early-return ``empty()`` behaviour survives the delegation."""
    assert models.NewOrderResponse.from_api("garbage") == models.NewOrderResponse.empty()
    assert models.NewOrderResponse.from_api(123) == models.NewOrderResponse.empty()
    assert models.MarketDataSnapshot.from_api(None) == models.MarketDataSnapshot.empty()
    assert models.Order.from_api(None) == models.Order.empty()


# ---------------------------------------------------------------------------
# D-09 — the nine RESPONSE ``Literal`` aliases
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("field_name", "wire_value"),
    [
        ("side", "SIDEWAYS"),
        ("ordType", "ICEBERG"),
        ("marketId", "BYMA"),
        ("status", "SUSPENDED"),
        ("currency", "BRL"),
    ],
)
def test_literal_out_of_set_passes_through(
    field_name: str, wire_value: str, caplog: pytest.LogCaptureFixture
) -> None:
    """D-09: membership is NEVER enforced; the value comes back byte-identical."""
    with caplog.at_level(logging.DEBUG, logger="matriz_client"):
        obj = _Literals.from_api({field_name: wire_value})

    returned = getattr(obj, field_name)
    assert returned == wire_value
    assert returned is wire_value
    # No ``type`` divergence for a merely out-of-set value.
    assert (f".{field_name}", "type") not in _pairs(caplog)


@pytest.mark.parametrize(
    ("field_name", "wire_value"),
    [
        ("side", "SIDEWAYS"),
        ("marketId", "BYMA"),
        ("status", "SUSPENDED"),
    ],
)
def test_literal_out_of_set_does_not_raise_under_strict_mode(
    field_name: str, wire_value: str
) -> None:
    """The sharpest form of D-09: an out-of-set value is not fatal, ever."""
    _decode.STRICT_DECODE.set(True)
    _decode.open_request_scope()
    obj = _Literals.from_api({field_name: wire_value})
    assert getattr(obj, field_name) == wire_value


def test_literal_wrong_runtime_type_reports(caplog: pytest.LogCaptureFixture) -> None:
    """The asymmetry: an ``int`` where every member is a ``str`` IS a divergence."""
    with caplog.at_level(logging.DEBUG, logger="matriz_client"):
        obj = _Literals.from_api({"side": 7})

    assert obj.side == 7
    assert (".side", "type") in _pairs(caplog)
    declared = {r.field_path: r.declared_type for r in _divergences(caplog)}
    assert declared[".side"] == "Literal"


def test_literal_enforcement_is_off_for_all_nine_published_aliases() -> None:
    """All nine ``types.py`` aliases are ``str``-valued and left open (D-09)."""
    aliases = (
        Side,
        OrderType,
        TimeInForce,
        MarketId,
        SegmentId,
        CFICode,
        MarketDataEntry,
        OrderStatus,
        Currency,
    )
    assert len(aliases) == 9
    for alias in aliases:
        assert all(isinstance(member, str) for member in alias.__args__)
        out_of_set = "definitely-not-a-member"
        assert (
            walk_field(
                out_of_set,
                alias,
                path=".x",
                model="M",
                policy=POLICY,
                sink=_decode.SILENT_SINK,
            )
            is out_of_set
        )


# ---------------------------------------------------------------------------
# ``UnknownFrame`` — exempt by matrix Section 3(c)
# ---------------------------------------------------------------------------


def test_unknown_frame_untouched(caplog: pytest.LogCaptureFixture) -> None:
    """T-29-34: the WS catch-all retains the whole payload and emits nothing."""
    payload = {"type": "zz", "alpha": 1, "beta": {"nested": True}, "gamma": [1, 2]}
    with caplog.at_level(logging.DEBUG, logger="matriz_client"):
        frame = UnknownFrame.from_api(payload)

    assert frame.type == "zz"
    assert frame.raw == payload
    assert frame.raw is not payload
    assert _divergences(caplog) == []


def test_unknown_frame_is_not_a_safe_model() -> None:
    assert not issubclass(UnknownFrame, _SafeModel)
    assert UnknownFrame.empty() == UnknownFrame()
    assert UnknownFrame.from_api("garbage") == UnknownFrame()


def test_unknown_frame_still_does_not_report_under_strict_mode() -> None:
    _decode.STRICT_DECODE.set(True)
    _decode.open_request_scope()
    frame = UnknownFrame.from_api({"type": "zz", "anything": "at-all"})
    assert frame.raw == {"type": "zz", "anything": "at-all"}


# ---------------------------------------------------------------------------
# Record shape, reserved keys, emitter safety (locks 1-2, 9)
# ---------------------------------------------------------------------------


def test_record_is_flat_all_str_and_carries_no_wire_value(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """T-29-29: no emitted value is ever a value from the payload."""
    sentinels = {
        "s": "wire-sentinel-alpha",
        "i": "wire-sentinel-beta",
        "vendorSecret": "wire-sentinel-gamma",
    }
    with caplog.at_level(logging.DEBUG, logger="matriz_client"):
        _Bare.from_api(dict(sentinels))

    records = _divergences(caplog)
    assert records
    # ``message`` and ``asctime`` are added by ``Logger.makeRecord`` /
    # ``caplog``'s formatter, not by the emitter (aggregation-contract lock 1).
    baseline = set(vars(logging.LogRecord("n", 0, "p", 0, "m", None, None))) | {
        "message",
        "asctime",
    }
    for record in records:
        emitted = set(record.__dict__) - baseline
        assert emitted == set(_CONTRACT_KEYS)
        for key in _CONTRACT_KEYS:
            value = getattr(record, key)
            assert isinstance(value, str)
            assert value not in sentinels.values()
        assert record.package == "matriz_client"


def test_contract_keys_avoid_every_reserved_logrecord_attribute() -> None:
    reserved = set(vars(logging.LogRecord("n", 0, "p", 0, "m", None, None)))
    assert reserved.isdisjoint(_CONTRACT_KEYS)
    assert "module" in reserved
    assert "name" in reserved


def test_reserved_keys_emission_through_a_real_logger_call_does_not_raise(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.DEBUG, logger="matriz_client"):
        _decode._emit("M", ".f", "type", "str", "int")
    assert len(_divergences(caplog)) == 1


def test_emitter_never_raises_into_the_decode_return_path() -> None:
    """Lock 9: a third-party handler blowing up cannot invert observable mode."""

    class _Exploding(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            raise RuntimeError("consumer handler exploded")

    logger = logging.getLogger("matriz_client")
    handler = _Exploding()
    previous_level = logger.level
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    try:
        obj = _Bare.from_api({})
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)

    assert obj == _Bare.empty()


# ---------------------------------------------------------------------------
# Aggregation + ordering (locks 5-7)
# ---------------------------------------------------------------------------


def test_list_elements_collapse_under_an_index_free_path(
    caplog: pytest.LogCaptureFixture,
) -> None:
    rows = [{"name": f"row-{n}"} for n in range(50)]
    with caplog.at_level(logging.DEBUG, logger="matriz_client"):
        _Nested.from_api({"leaf": {"name": "n", "count": 1}, "rows": rows, "tag": "t"})

    collapsed = [p for p, kind in _pairs(caplog) if p == ".rows[].count"]
    assert len(collapsed) == 1


def test_distinct_kinds_at_the_same_path_stay_distinct(
    caplog: pytest.LogCaptureFixture,
) -> None:
    scope = DecodeScope()
    with caplog.at_level(logging.DEBUG, logger="matriz_client"):
        scope("M", ".f", "missing", "str", "NoneType")
        scope("M", ".f", "type", "str", "int")
        scope("M", ".f", "missing", "str", "NoneType")
    assert _pairs(caplog) == [(".f", "missing"), (".f", "type")]


def test_one_scope_shared_across_two_walks_emits_once(
    caplog: pytest.LogCaptureFixture,
) -> None:
    scope = _decode.open_request_scope()
    assert _decode.current_sink() is scope
    with caplog.at_level(logging.DEBUG, logger="matriz_client"):
        _Bare.from_api({})
        _Bare.from_api({})
    assert len(_divergences(caplog)) == 4


def test_emission_order_is_extras_sorted_then_declaration_order(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.DEBUG, logger="matriz_client"):
        _Bare.from_api({"zeta": 1, "alpha": 2})

    assert _pairs(caplog) == [
        (".alpha", "extra"),
        (".zeta", "extra"),
        (".s", "missing"),
        (".i", "missing"),
        (".f", "missing"),
        (".b", "missing"),
    ]


def test_current_sink_returns_a_fresh_scope_when_none_is_bound() -> None:
    """Lock 6: a process-lifetime scope is explicitly rejected."""
    _decode.DECODE_SCOPE.set(None)
    first = _decode.current_sink()
    second = _decode.current_sink()
    assert isinstance(first, DecodeScope)
    assert first is not second


def test_open_request_scope_binds_a_fresh_scope_each_time() -> None:
    first = _decode.open_request_scope()
    second = _decode.open_request_scope()
    assert first is not second
    assert _decode.current_sink() is second


# ---------------------------------------------------------------------------
# Strict mode (lock 4)
# ---------------------------------------------------------------------------


def test_strict_mode_raises_on_missing_with_the_exact_field_path() -> None:
    _decode.STRICT_DECODE.set(True)
    _decode.open_request_scope()
    with pytest.raises(MatrizDecodeError) as exc_info:
        _Bare.from_api({})
    err = exc_info.value
    assert err.field_path == ".s"
    assert err.declared_type == "str"
    assert err.observed_type == "NoneType"
    assert err.model == "_Bare"


def test_strict_mode_raises_on_type() -> None:
    _decode.STRICT_DECODE.set(True)
    _decode.open_request_scope()
    with pytest.raises(MatrizDecodeError) as exc_info:
        _Bare.from_api({"s": 7, "i": 1, "f": 1.0, "b": True})
    assert exc_info.value.field_path == ".s"
    assert exc_info.value.observed_type == "int"


def test_strict_mode_raises_on_non_dict() -> None:
    _decode.STRICT_DECODE.set(True)
    _decode.open_request_scope()
    with pytest.raises(MatrizDecodeError) as exc_info:
        _Bare.from_api("garbage")
    assert exc_info.value.field_path == ""
    assert exc_info.value.model == "_Bare"
    assert exc_info.value.observed_type == "str"


def test_strict_mode_never_raises_on_an_extra_wire_key(
    caplog: pytest.LogCaptureFixture,
) -> None:
    _decode.STRICT_DECODE.set(True)
    _decode.open_request_scope()
    with caplog.at_level(logging.DEBUG, logger="matriz_client"):
        obj = _Mapping.from_api({"meta": {}, "label": "x", "brandNew": 1})
    assert obj.label == "x"
    assert [p for p, kind in _pairs(caplog) if kind == "extra"] == [".brandNew"]


def test_strict_mode_raises_on_a_missing_mapping_field() -> None:
    """The call-site mapping pass honours strict mode like any other axis."""
    _decode.STRICT_DECODE.set(True)
    _decode.open_request_scope()
    with pytest.raises(MatrizDecodeError) as exc_info:
        _Mapping.from_api({"label": "x"})
    assert exc_info.value.field_path == ".meta"
    assert exc_info.value.declared_type == "dict"


def test_strict_mode_does_not_make_empty_fatal() -> None:
    """T-29-33: ``empty()`` walks the silent sink, so strict mode cannot reach it."""
    _decode.STRICT_DECODE.set(True)
    _decode.open_request_scope()
    assert _Nested.empty().rows == []
    assert _Mapping.empty().meta == {}


# ---------------------------------------------------------------------------
# Delegation contract — the shape ``models.py`` must keep
# ---------------------------------------------------------------------------


def test_models_delegate_to_the_walker() -> None:
    src = pathlib.Path(models.__file__).read_text(encoding="utf-8")
    assert "_decode.walk_model" in src
    assert "_decode.walk_field" in src
    assert "_decode.SILENT_SINK" in src


def test_from_api_signature_is_a_single_positional_parameter() -> None:
    params = list(inspect.signature(_SafeModel.from_api).parameters)
    assert len(params) == 1
    assert params == ["data"]


def test_convert_argument_order_is_unchanged() -> None:
    """``_convert(tp, value)`` is REVERSED relative to the other two packages."""
    params = list(inspect.signature(models._convert).parameters)
    assert params == ["tp", "value"]


def test_convert_shim_still_coerces(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.DEBUG, logger="matriz_client"):
        assert models._convert(list[_Leaf], None) == []
        assert models._convert(dict[str, Any], None) == {}
        assert models._convert(_Leaf, None) == _Leaf.empty()
        assert models._convert(str | None, None) is None
        assert models._convert(Side | None, "SIDEWAYS") == "SIDEWAYS"


def test_models_carry_no_slots() -> None:
    """Difference 5: matriz models are frozen with NO ``slots``."""
    for cls in (models.Order, models.InstrumentId, models.MarketDataSnapshot, UnknownFrame):
        assert "__slots__" not in vars(cls)
        assert "__dict__" in dir(cls())  # instances keep a __dict__


def test_walk_model_returns_kwargs_not_an_instance() -> None:
    kwargs = walk_model(_Leaf, {"name": "n", "count": 1}, policy=POLICY, sink=_decode.SILENT_SINK)
    assert kwargs == {"name": "n", "count": 1}
    assert _Leaf(**kwargs) == _Leaf.from_api({"name": "n", "count": 1})


def test_hints_for_is_cache_backed() -> None:
    _decode.hints_for(_Leaf)
    before = _decode.hints_for.cache_info().hits
    _decode.hints_for(_Leaf)
    assert _decode.hints_for.cache_info().hits > before


# ---------------------------------------------------------------------------
# The mode carrier (D-03)
# ---------------------------------------------------------------------------


@pytest.fixture
def _reset_strict_decode_opt_in() -> Iterator[None]:
    """``configure(strict_decode=True)`` carries forward — undo it after the test."""
    try:
        yield
    finally:
        matriz_client.configure(strict_decode=False)
        aio.configure(strict_decode=False)


def test_strict_mode_from_sync_constructor() -> None:
    assert Client()._state.strict_decode is False
    assert Client(strict_decode=True)._state.strict_decode is True
    assert Client(strict_decode=False)._state.strict_decode is False


def test_strict_mode_from_async_constructor() -> None:
    assert AsyncClient()._state.strict_decode is False
    assert AsyncClient(strict_decode=True)._state.strict_decode is True


@pytest.mark.usefixtures("_reset_strict_decode_opt_in")
def test_strict_mode_from_sync_configure() -> None:
    matriz_client.configure(strict_decode=True)
    assert matriz_client._get_default()._state.strict_decode is True
    # Pitfall 5: an unrelated configure() must NOT reset a security opt-in.
    matriz_client.configure(base_url="https://api.test")
    assert matriz_client._get_default()._state.strict_decode is True


@pytest.mark.usefixtures("_reset_strict_decode_opt_in")
def test_strict_mode_from_async_configure() -> None:
    aio.configure(strict_decode=True)
    assert aio._get_default()._state.strict_decode is True
    aio.configure(base_url="https://api.test")
    assert aio._get_default()._state.strict_decode is True


def test_strict_mode_is_not_env_backed() -> None:
    """T-29-16: a plain ``bool = False``, no ``default_factory``."""
    from matriz_client._state import _ClientState

    (declared,) = [f for f in dataclasses.fields(_ClientState) if f.name == "strict_decode"]
    assert declared.default is False
    assert declared.default_factory is dataclasses.MISSING


def test_strict_mode_view_inherits() -> None:
    """T-29-17: a ``with_options`` view can never run a different mode."""
    parent = Client(strict_decode=True)
    view = parent.with_options(max_retries=0)
    assert view._state is parent._state
    assert view._state.strict_decode is True
    parent._state.strict_decode = False
    assert view._state.strict_decode is False
    assert "strict_decode" not in Client.__slots__
    assert "strict_decode" not in AsyncClient.__slots__


def test_sync_request_binds_the_mode_and_a_fresh_scope(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://api.test/rest/segment/all",
        json={"status": "OK", "segments": [{"marketSegmentId": "DDF", "marketId": "ROFX"}]},
    )
    client = Client(
        base_url="https://api.test",
        token="test-token",
        token_expires_at=9_999_999_999.0,
        strict_decode=True,
    )
    assert _decode.STRICT_DECODE.get() is False
    client.get_segments()
    # No reset: the decode happens after ``_request`` returns, in the parser.
    assert _decode.STRICT_DECODE.get() is True
    assert isinstance(_decode.DECODE_SCOPE.get(), DecodeScope)


async def test_async_request_binds_the_mode_and_a_fresh_scope(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://api.test/rest/segment/all",
        json={"status": "OK", "segments": [{"marketSegmentId": "DDF", "marketId": "ROFX"}]},
    )
    client = AsyncClient(
        base_url="https://api.test",
        token="test-token",
        token_expires_at=9_999_999_999.0,
        strict_decode=True,
    )
    try:
        assert _decode.STRICT_DECODE.get() is False
        await client.get_segments()
        assert _decode.STRICT_DECODE.get() is True
        first = _decode.DECODE_SCOPE.get()
        httpx_mock.add_response(
            url="https://api.test/rest/segment/all",
            json={"status": "OK", "segments": []},
        )
        await client.get_segments()
        assert _decode.DECODE_SCOPE.get() is not first
    finally:
        await client.aclose()


def test_divergence_on_a_real_response_reaches_the_package_logger(
    httpx_mock: HTTPXMock, caplog: pytest.LogCaptureFixture
) -> None:
    """End to end: a wrong-typed wire field on a live parse emits a record."""
    httpx_mock.add_response(
        url="https://api.test/rest/segment/all",
        json={"status": "OK", "segments": [{"marketSegmentId": 7, "vendorNew": "x"}]},
    )
    with caplog.at_level(logging.DEBUG, logger="matriz_client"):
        segments = matriz_client.get_segments()

    assert segments[0].marketSegmentId == 7
    kinds = {(r.field_path, r.divergence) for r in _divergences(caplog)}
    assert (".marketSegmentId", "type") in kinds
    assert (".vendorNew", "extra") in kinds


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
        with caplog.at_level(logging.DEBUG, logger="matriz_client"):
            for _ in range(2):
                with pytest.raises(MatrizDecodeError) as excinfo:
                    walk_model(_Bare, payload, policy=POLICY, sink=scope)
                assert excinfo.value.field_path == ".s"
    finally:
        _decode.STRICT_DECODE.reset(token)

    # The record survives the raise, on BOTH attempts: a strict run still leaves
    # the divergence on the paquete logger (lock 9 — ``_emit`` never raises).
    paths = [r.field_path for r in _divergences(caplog)]  # type: ignore[attr-defined]
    assert paths == [".s", ".s"]
