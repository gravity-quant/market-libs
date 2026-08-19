"""Behaviour contract for ``ambito_financiero_client._decode`` — the walker copy.

Phase 29 Plan 07 (DEC-01). ``ambito-financiero-client`` has **no models module
at all**, and — unlike iol, which receives one in Phase 30 — is expected never
to grow one: its entire public surface is a single function returning a
``float``. The walker copy here is therefore **dormant by design**, and this
suite is the only thing that will ever exercise it.

Dormant is not the same as unverified, and the distinction is the point of
this file. A copy nobody exercises rots quietly; the Plan 09 intactness gate
can prove this file is byte-identical to the canonical one, but only a
behaviour suite can prove the canonical one still *works* when it lands in a
package with no ``models.py`` beside it. That standalone-import property is in
turn the strongest available evidence that the walker has no hidden coupling
to a models module — which is what makes the verbatim-copy contract
enforceable in the three packages that do have one.

The model fixtures are declared module-locally as frozen slotted dataclasses
exposing a ``from_api`` classmethod that delegates to :func:`walk_model`. They
exist only here; nothing in ``src/`` constructs one.

Covered: the five divergence classes across both decode modes, the twelve
locks of ``29-AGGREGATION-CONTRACT.md``, the D-09 lock in
``29-DLOCK-RESPONSE-LITERAL.md``, and the D-03 mode carrier (state field, four
public entry points, two bind sites).
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
from typing import Any, Literal, Self

import pytest
from pytest_httpx import HTTPXMock

import ambito_financiero_client
from ambito_financiero_client import _decode, aio
from ambito_financiero_client import client as client_mod
from ambito_financiero_client._core import RequestSpec
from ambito_financiero_client._decode import POLICY, DecodeScope, walk_field, walk_model
from ambito_financiero_client._state import _ClientState
from ambito_financiero_client.aio import AsyncClient
from ambito_financiero_client.client import Client
from ambito_financiero_client.exceptions import (
    AmbitoFinancieroClientError,
    AmbitoFinancieroDecodeError,
)

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
#
# ámbito has no ``models.py`` and is not scheduled to grow one. These declare
# the canonical shape a typed surface would take — a frozen slotted dataclass
# whose ``from_api`` delegates to ``walk_model`` and constructs from the
# returned kwargs — so every walker branch is driven even though nothing in
# ``src/`` does. Declaring them here also exercises the walker's duck-typed
# ``_is_model`` predicate, which is the whole reason the module can stand
# alone without importing ``models``.
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _Model:
    """Base carrying the ``from_api`` shape a typed ámbito surface would take."""

    @classmethod
    def from_api(cls, payload: Any) -> Self:
        """Decode ``payload`` into an instance, reporting every divergence."""
        return cls(**walk_model(cls, payload, policy=POLICY))


@dataclass(frozen=True, slots=True)
class _Leaf(_Model):
    """Nested leaf used to exercise list-element path collapse."""

    simbolo: str
    dias: int


@dataclass(frozen=True, slots=True)
class _Scalars(_Model):
    """One field per scalar branch of the walker, in declaration order."""

    s: str
    i: int
    f: float
    b: bool


@dataclass(frozen=True, slots=True)
class _Nested(_Model):
    """A model carrying a ``list[Model]`` field."""

    titulo: str
    hojas: list[_Leaf]


@dataclass(frozen=True, slots=True)
class _WithLiteral(_Model):
    """A ``Literal`` RESPONSE field — D-09 territory."""

    lado: Literal["BUY", "SELL"] | None


@dataclass(frozen=True, slots=True)
class _Cotizacion(_Model):
    """The shape a typed ámbito surface would take, if it ever grew one.

    ``get_dollar_banco_nacion`` returns a bare ``float`` today; this is what
    the same endpoint's payload would look like modelled rather than parsed.
    """

    fecha: str
    ultimoPrecio: float
    variacion: int
    valores: list[_Leaf]


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
    with caplog.at_level(logging.DEBUG, logger="ambito_financiero_client"):
        kwargs = walk_model(
            cls, payload, policy=POLICY, sink=sink if sink is not None else DecodeScope()
        )
    return cls(**kwargs), _divergences(caplog)


def _tuples(records: list[logging.LogRecord]) -> list[tuple[str, str]]:
    return [(r.field_path, r.divergence) for r in records]  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Module surface + policy constant + the standalone-import property
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
    """``29-SEMANTICS-MATRIX.md`` Section 2, ámbito row — the higyrus constant.

    The matrix records that ámbito's value is **expected to stay inert
    indefinitely** — this paquete's single public function returns a ``float``,
    not a model — which is precisely why it must be pinned rather than assumed:
    nothing in production would fail if it silently drifted.
    """
    assert POLICY.missing_str == ""
    assert POLICY.missing_int == 0
    assert POLICY.missing_float == 0.0
    assert POLICY.missing_bool is False
    assert POLICY.non_dict_model == "from_api_none"
    assert POLICY.scalar_passthrough is False
    assert POLICY.literal_enforced is False


def test_logger_name_is_this_package() -> None:
    """One of the five normalized per-package lines — never higyrus's."""
    assert _decode._LOGGER_NAME == "ambito_financiero_client"


def test_context_var_names_are_package_prefixed() -> None:
    """Two more normalized lines: a shared name would alias across packages."""
    assert _decode.STRICT_DECODE.name == "ambito_financiero_client_strict_decode"
    assert _decode.DECODE_SCOPE.name == "ambito_financiero_client_decode_scope"


def test_context_var_declarations_are_reflowed_by_the_formatter() -> None:
    """Plan 09 hand-off: the ContextVar name substitution changes LINE COUNT.

    ``ambito_financiero_client`` is the LONGEST of the five package names, so
    ``ruff format`` splits the ``STRICT_DECODE`` assignment that higyrus /
    market-data / matriz all carry on one line into three. ``iol_client`` is
    the shortest, and gets the opposite treatment on ``DECODE_SCOPE``: three
    lines collapsed into one (asserted by the sibling ``iol-client`` test).

    The reflow cuts both ways, which is the finding. A Plan 09 normalizer that
    substitutes the package name and then compares byte-for-byte would report a
    false divergence on BOTH of these copies, in opposite directions, for
    reasons that have nothing to do with the walker. It must compare
    semantically, or re-format both sides before comparing.
    """
    source = pathlib.Path(inspect.getfile(_decode)).read_text(encoding="utf-8")
    lines = source.splitlines()
    strict = next(i for i, line in enumerate(lines) if line.startswith("STRICT_DECODE: ContextVar"))
    scope = next(i for i, line in enumerate(lines) if line.startswith("DECODE_SCOPE: ContextVar"))

    # STRICT_DECODE: one line in the canonical body, three here.
    assert lines[strict] == "STRICT_DECODE: ContextVar[bool] = ContextVar("
    assert lines[strict + 1] == '    "ambito_financiero_client_strict_decode", default=False'
    assert lines[strict + 2] == ")"
    # DECODE_SCOPE: three lines in the canonical body, three here — unchanged.
    assert lines[scope] == "DECODE_SCOPE: ContextVar[DecodeScope | None] = ContextVar("
    assert lines[scope + 1] == '    "ambito_financiero_client_decode_scope", default=None'
    assert lines[scope + 2] == ")"
    assert all(len(line) <= 100 for line in lines)


def test_decode_module_never_imports_models() -> None:
    """``_decode`` must stand alone: two of the five copies have no ``models.py``.

    ámbito is one of those two, so this is not a hypothetical here — the module
    imports cleanly in a package where ``models`` does not exist at all and is
    not scheduled to.
    """
    source = pathlib.Path(inspect.getfile(_decode)).read_text(encoding="utf-8")
    imported: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert not any("models" in name for name in imported), imported
    package_imports = {name for name in imported if name.startswith("ambito_financiero_client")}
    assert package_imports == {"ambito_financiero_client.exceptions"}


def test_this_package_really_has_no_models_module() -> None:
    """The precondition that makes the standalone-import evidence meaningful."""
    package_dir = pathlib.Path(inspect.getfile(client_mod)).parent

    assert not (package_dir / "models.py").exists()
    with pytest.raises(ModuleNotFoundError):
        __import__("ambito_financiero_client.models")


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
    """The ``bool``-is-``int`` guard survives the copy and is reported."""
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
    """Lock 1 + T-29-36: type-not-value, six flat str keys, no containers.

    iol payloads carry account and instrument identifiers, so this is the
    assertion that keeps them out of the record.
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
        assert record.package == "ambito_financiero_client"  # type: ignore[attr-defined]
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
    """T-29-36: drive a real ``logger.warning(..., extra=...)``, not ``setattr``.

    ``LogRecord.__init__`` cannot reproduce the failure — only
    ``Logger.makeRecord`` refuses to overwrite an existing attribute.
    """
    logger = logging.getLogger("ambito_financiero_client")
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
    """Lock 9 / T-29-41: a handler exception must not reach the caller."""
    logger = logging.getLogger("ambito_financiero_client")
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
        "hojas": [{"simbolo": "a"}, {"simbolo": "b"}, {"simbolo": "c"}],
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
        "hojas": [{"simbolo": "a"}, {"simbolo": "b", "dias": "x"}],
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
    with caplog.at_level(logging.DEBUG, logger="ambito_financiero_client"):
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
        "hojas": [{"simbolo": "a"}, {"dias": "x"}],
    }
    _, first = _walk(_Nested, payload, caplog)
    _, second = _walk(_Nested, payload, caplog)

    assert _tuples(first) == _tuples(second)


# ---------------------------------------------------------------------------
# Strict mode
# ---------------------------------------------------------------------------


def test_strict_mode_raises_with_the_exact_field_path_and_no_wire_value() -> None:
    """Lock 4 / T-29-36: strict raises on ``type`` carrying only type names."""
    token = _decode.STRICT_DECODE.set(True)
    try:
        with pytest.raises(AmbitoFinancieroDecodeError) as excinfo:
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
    assert isinstance(excinfo.value, AmbitoFinancieroClientError)
    assert excinfo.value.field_path == ".i"
    assert excinfo.value.declared_type == "int"
    assert excinfo.value.observed_type == "str"
    assert excinfo.value.model == "_Scalars"


def test_strict_mode_raises_on_missing() -> None:
    """Lock 4: ``missing`` is fatal under strict mode."""
    token = _decode.STRICT_DECODE.set(True)
    try:
        with pytest.raises(AmbitoFinancieroDecodeError, match=r"\.s"):
            walk_model(_Scalars, {}, policy=POLICY, sink=DecodeScope())
    finally:
        _decode.STRICT_DECODE.reset(token)


def test_strict_mode_raises_on_non_dict() -> None:
    """Lock 4: ``non_dict`` is fatal under strict mode."""
    token = _decode.STRICT_DECODE.set(True)
    try:
        with pytest.raises(AmbitoFinancieroDecodeError, match="_Scalars"):
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
        with caplog.at_level(logging.DEBUG, logger="ambito_financiero_client"):
            kwargs = walk_model(_Scalars, payload, policy=POLICY, sink=DecodeScope())
    finally:
        _decode.STRICT_DECODE.reset(token)

    records = _divergences(caplog)
    assert _Scalars(**kwargs) == _Scalars("a", 1, 1.0, True)
    assert _tuples(records) == [(".sobrante", "extra")]
    assert records[0].levelno == logging.INFO


def test_decode_error_is_not_an_api_error_nor_a_no_data_error() -> None:
    """The HTTP response succeeded; it is the payload shape that failed.

    The second half matters only in this paquete: ``AmbitoFinancieroNoDataError``
    already signals "the request was fine, the answer is empty" (weekend,
    holiday, future date). A decode divergence is a *different* fact — a
    malformed payload — and conflating the two would make a shape bug look like
    a market-calendar gap.
    """
    error = AmbitoFinancieroDecodeError(".ultimoPrecio", "float", "str", "_Cotizacion")

    assert isinstance(error, AmbitoFinancieroClientError)
    assert not isinstance(error, ambito_financiero_client.AmbitoFinancieroAPIError)
    assert not isinstance(error, ambito_financiero_client.AmbitoFinancieroNoDataError)
    assert not hasattr(error, "status_code")


# ---------------------------------------------------------------------------
# D-09 — Literal is never closed on RESPONSE fields
# ---------------------------------------------------------------------------


def test_literal_membership_is_never_enforced(caplog: pytest.LogCaptureFixture) -> None:
    """D-09 (a): an out-of-set value is returned byte-for-byte unchanged."""
    obj, records = _walk(_WithLiteral, {"lado": "zzz"}, caplog)

    assert obj.lado == "zzz"
    assert [r for r in records if r.divergence == "type"] == []  # type: ignore[attr-defined]


def test_literal_out_of_set_value_is_returned_by_identity() -> None:
    """D-09: a coercion that happened to produce an equal string still fails this."""
    wire_value = "".join(["z", "z", "z"])
    returned = walk_field(
        wire_value,
        Literal["BUY", "SELL"],
        path=".lado",
        model="_WithLiteral",
        policy=POLICY,
        sink=_decode.SILENT_SINK,
    )

    assert returned is wire_value


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
        with caplog.at_level(logging.DEBUG, logger="ambito_financiero_client"):
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
# The Phase 30 shape — a ``from_api`` classmethod delegating to the walker
# ---------------------------------------------------------------------------


def _full_payload(cls: type) -> dict[str, Any]:
    """A type-correct wire payload covering every declared field of ``cls``."""
    filler: dict[Any, Any] = {str: "x", int: 1, float: 1.0, bool: True}
    hints = _decode.hints_for(cls)
    return {f.name: filler.get(hints[f.name], []) for f in dataclasses.fields(cls)}  # type: ignore[arg-type]


def test_from_api_shape_decodes_a_clean_payload_without_a_single_record(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The copy is functional, not merely present: a clean payload is silent."""
    payload = _full_payload(_Cotizacion)

    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="ambito_financiero_client"):
        obj = _Cotizacion.from_api(payload)

    assert obj == _Cotizacion("x", 1.0, 1, [])
    assert _divergences(caplog) == []


def test_from_api_shape_reports_a_missing_float_and_still_substitutes(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The pairing a dormant copy must still get right: ``0.0`` AND a record."""
    payload = _full_payload(_Cotizacion)
    del payload["ultimoPrecio"]

    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="ambito_financiero_client"):
        obj = _Cotizacion.from_api(payload)

    assert obj.ultimoPrecio == 0.0
    assert obj.fecha == "x"
    assert _tuples(_divergences(caplog)) == [(".ultimoPrecio", "missing")]


def test_from_api_shape_nested_path_is_dotted_from_the_decode_root(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """``.valores[].dias`` — the aggregation contract's worked example, here."""
    payload = _full_payload(_Cotizacion)
    payload["valores"] = [{"simbolo": "USD"}, {"simbolo": "EUR"}]

    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="ambito_financiero_client"):
        obj = _Cotizacion.from_api(payload)

    assert len(obj.valores) == 2
    assert _tuples(_divergences(caplog)) == [(".valores[].dias", "missing")]


def test_from_api_shape_is_fatal_under_strict_mode() -> None:
    """Both modes reachable from the shape a typed surface would take."""
    payload = _full_payload(_Cotizacion)
    del payload["ultimoPrecio"]

    token = _decode.STRICT_DECODE.set(True)
    try:
        with pytest.raises(AmbitoFinancieroDecodeError, match=r"\.ultimoPrecio"):
            _Cotizacion.from_api(payload)
    finally:
        _decode.STRICT_DECODE.reset(token)


# ---------------------------------------------------------------------------
# Phase 29 D-03 — strict_decode carrier: state field, four public entry
# points, two bind sites
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
        ambito_financiero_client.configure(strict_decode=False)
        aio.configure(strict_decode=False)


def _spec() -> RequestSpec:
    """ámbito's ``RequestSpec`` is the minimal one: no auth, no body (D-01)."""
    return RequestSpec(
        method="GET",
        path="/dolarnacion/historico-general/2026-08-18/2026-08-18",
        endpoint_name="get_dollar_banco_nacion",
    )


def test_strict_mode_is_not_env_backed() -> None:
    """T-29-16: a plain default, never a ``field(default_factory=_env_...)``.

    Both fields beside it on this state ARE env-backed factories, which is why
    the assertion is worth making mechanically rather than by reading.
    """
    (declared,) = [f for f in dataclasses.fields(_ClientState) if f.name == "strict_decode"]

    assert declared.default is False
    assert declared.default_factory is dataclasses.MISSING


def test_state_still_has_no_token_fields() -> None:
    """The B7 divergence is untouched: no auth here, so no token and no lock.

    Phase 29 adds exactly one field to this state. If a future change to the
    decode carrier ever dragged the token shape across from iol/higyrus/matriz,
    this fails.
    """
    names = {f.name for f in dataclasses.fields(_ClientState)}

    assert names == {"base_url", "user_agent", "strict_decode", "http_client"}


def test_strict_mode_from_constructor() -> None:
    """D-03: ``Client(strict_decode=True)`` reaches the shared ``_ClientState``."""
    assert Client()._state.strict_decode is False
    assert Client(strict_decode=True)._state.strict_decode is True
    assert Client(strict_decode=False)._state.strict_decode is False
    assert AsyncClient()._state.strict_decode is False
    assert AsyncClient(strict_decode=True)._state.strict_decode is True


def test_strict_mode_from_configure() -> None:
    """D-03: sync and async ``configure(strict_decode=True)`` reach the default client.

    ámbito's ``configure`` REPLACES the default client rather than mutating it
    in place, so the ``None``-sentinel carry-forward has to read the prior
    client's state explicitly — the second half of this test is what proves it
    does.
    """
    with _restored_default_clients():
        ambito_financiero_client.configure(strict_decode=True)
        aio.configure(strict_decode=True)
        assert client_mod._get_default()._state.strict_decode is True
        assert aio._get_default()._state.strict_decode is True
        # Sentinel ``None`` = "no cambiar" (Pitfall 5): an unrelated configure()
        # call must NOT silently reset a previous opt-in, even though it builds
        # a brand-new Client.
        ambito_financiero_client.configure(base_url="https://api.test")
        aio.configure(base_url="https://api.test")
        assert client_mod._get_default()._state.strict_decode is True
        assert aio._get_default()._state.strict_decode is True


def test_strict_mode_view_inherits() -> None:
    """The flag lives on the shared state, never in ``Client.__slots__``."""
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
        with Client(base_url="https://api.test", strict_decode=True) as c:
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
        ambito_financiero_client.configure(base_url="https://api.test", strict_decode=True)
        client_mod._request("GET", "/dolarnacion/historico-general/2026-08-18/2026-08-18")
        assert _decode.STRICT_DECODE.get() is True
        assert isinstance(_decode.DECODE_SCOPE.get(), DecodeScope)


async def test_async_request_binds_mode(httpx_mock: HTTPXMock) -> None:
    """Dual sync/async parity: ``AsyncClient._request`` mirrors the bind verbatim.

    ámbito's AsyncClient creates its transport WITHOUT the token-lock
    serialization the other paquetes use (the deliberate B7 divergence); the
    bind is a plain pair of statements and adds no locking of its own.
    """
    httpx_mock.add_response(json={"status": "ok"})
    with _restored_decode_context():
        _decode.STRICT_DECODE.set(False)
        _decode.DECODE_SCOPE.set(None)
        async with AsyncClient(base_url="https://api.test", strict_decode=True) as c:
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
        with Client(base_url="https://api.test", strict_decode=True) as c:
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
        with Client(base_url="https://api.test") as c:
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
        with caplog.at_level(logging.DEBUG, logger="ambito_financiero_client"):
            for _ in range(2):
                with pytest.raises(AmbitoFinancieroDecodeError) as excinfo:
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
    with caplog.at_level(logging.DEBUG, logger="ambito_financiero_client"):
        walk_model(_Scalars, payload, policy=POLICY, sink=DecodeScope())

    paths = [r.field_path for r in _divergences(caplog)]  # type: ignore[attr-defined]
    assert paths == [".a?WARNING?root??forged"]
    assert all("\n" not in p for p in paths)


def test_extra_key_length_is_bounded(caplog: pytest.LogCaptureFixture) -> None:
    """CR-04: key length is payload-controlled, so it is truncated (lock 11)."""
    payload = {"s": "a", "i": 1, "f": 1.0, "b": True, "X" * 200: "x"}
    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="ambito_financiero_client"):
        walk_model(_Scalars, payload, policy=POLICY, sink=DecodeScope())

    (record,) = _divergences(caplog)
    assert record.field_path == "." + "X" * 64 + "..."  # type: ignore[attr-defined]


def test_extra_key_that_is_not_a_string_is_stringified_and_sanitized(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """CR-04: a hand-built dict can carry a non-``str`` key; the sort stays total."""
    payload: dict[Any, Any] = {"s": "a", "i": 1, "f": 1.0, "b": True, 7: "x", ("t",): "y"}
    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="ambito_financiero_client"):
        walk_model(_Scalars, payload, policy=POLICY, sink=DecodeScope())

    paths = {r.field_path for r in _divergences(caplog)}  # type: ignore[attr-defined]
    assert paths == {".7", ".??t???"}


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


# ---------------------------------------------------------------------------
# Phase 29 code review, WR-02 — an absent nested-model key is `missing`
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _CarriesNested(_Model):
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
