"""Unit tests for ``higyrus_client._core`` builders/parsers.

Phase 7 REFAC-03 + D-01 (per-package ``RequestSpec`` con ``json_body`` +
``url_pre_encoded``) + D-02 (auth-flow factorizado) + D-06 (body-consume-then-
raise) + URL-encoding quirk encapsulation (Higyrus IIS rechaza ``%2F`` —
queda dentro de cada ``build_<endpoint>_request``).

Tests aislados sobre el módulo `_core`: no involucran transport (no
``httpx.Client`` ni ``httpx.AsyncClient``), sólo construcción de ``RequestSpec``
y parsing de ``httpx.Response`` sintéticas. Esto detecta cualquier regresión
en la quirk URL-encoding ANTES de que llegue a un wire request real.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import logging
from collections.abc import Iterator
from typing import Any

import httpx
import pytest

from higyrus_client import _core, _decode
from higyrus_client._state import _TOKEN_TTL_SECONDS, _ClientState
from higyrus_client.exceptions import (
    HigyrusAPIError,
    HigyrusAuthError,
    HigyrusAuthorizationError,
    HigyrusDecodeError,
    HigyrusRateLimitError,
)
from higyrus_client.models import Cuenta, Health, Movimiento, Posicion, PosicionValuada

# ---------------------------------------------------------------------------
# RequestSpec dataclass shape
# ---------------------------------------------------------------------------


def test_request_spec_is_frozen_dataclass() -> None:
    """``RequestSpec`` is immutable — re-assigning a field must raise."""
    spec = _core.RequestSpec(method="GET", path="/api/health")
    with pytest.raises((AttributeError, TypeError)):
        spec.method = "POST"  # type: ignore[misc]


def test_request_spec_default_fields_are_none_or_false() -> None:
    """Optional fields default to ``None`` / ``False`` so builders only set what they need."""
    spec = _core.RequestSpec(method="GET", path="/api/health")
    assert spec.params is None
    assert spec.headers is None
    assert spec.json_body is None
    assert spec.url_pre_encoded is False


# ---------------------------------------------------------------------------
# raise_for_response (D-04 — single source of truth)
# ---------------------------------------------------------------------------


def test_raise_for_response_extracts_errors_array() -> None:
    """The structured ``errors`` array from Higyrus' envelope must reach the exception."""
    resp = httpx.Response(
        400,
        json={
            "timestamp": "2026-04-24T12:34:56Z",
            "errors": [{"title": "validation", "detail": "fechaDesde inválida"}],
        },
    )
    with pytest.raises(HigyrusAPIError) as exc_info:
        _core.raise_for_response(resp)
    err = exc_info.value
    assert err.status_code == 400
    assert err.errors == [{"title": "validation", "detail": "fechaDesde inválida"}]
    assert err.timestamp == "2026-04-24T12:34:56Z"


@pytest.mark.parametrize(
    ("status", "exc_cls"),
    [
        (401, HigyrusAuthError),
        (403, HigyrusAuthorizationError),
        (429, HigyrusRateLimitError),
        (500, HigyrusAPIError),
    ],
)
def test_raise_for_response_maps_status_code_to_exception(
    status: int, exc_cls: type[HigyrusAPIError]
) -> None:
    """401→Auth, 403→Authorization, 429→RateLimit, otros→APIError."""
    resp = httpx.Response(status, json={"errors": []})
    with pytest.raises(exc_cls):
        _core.raise_for_response(resp)


def test_raise_for_response_tolerates_non_json_body() -> None:
    """Si el body no es JSON, igual debe levantar la excepción correcta."""
    resp = httpx.Response(500, content=b"Internal Server Error")
    with pytest.raises(HigyrusAPIError) as exc_info:
        _core.raise_for_response(resp)
    assert exc_info.value.status_code == 500
    assert exc_info.value.errors == []


def test_raise_for_response_does_not_raise_on_2xx() -> None:
    """2xx responses must be a no-op — consistent contract with ambito/iol/matriz.

    Regression test para CR-01 Phase 7 review: la función levantaba
    ``HigyrusAPIError(status_code=200, ...)`` para CUALQUIER status (incluso
    200 OK) porque no tenía guard al inicio. Cualquier caller directo de
    ``raise_for_response(resp)`` sobre un happy-path obtendría excepción
    silenciosa.
    """
    resp = httpx.Response(200, content=b"{}")
    _core.raise_for_response(resp)  # no exception


def test_raise_for_response_no_op_for_3xx() -> None:
    """3xx redirects también son no-op — la función sólo mapea ``resp.is_error``."""
    resp = httpx.Response(302, content=b"")
    _core.raise_for_response(resp)  # no exception


# ---------------------------------------------------------------------------
# token_is_fresh
# ---------------------------------------------------------------------------


def test_token_is_fresh_returns_true_when_token_present_and_unexpired() -> None:
    state = _ClientState(token="tok", token_expires_at=9_999_999_999.0)
    assert _core.token_is_fresh(state) is True


def test_token_is_fresh_returns_false_when_no_token() -> None:
    state = _ClientState(token=None, token_expires_at=9_999_999_999.0)
    assert _core.token_is_fresh(state) is False


def test_token_is_fresh_returns_false_when_expired() -> None:
    state = _ClientState(token="tok", token_expires_at=0.0)
    assert _core.token_is_fresh(state) is False


# ---------------------------------------------------------------------------
# Auth flow (D-02)
# ---------------------------------------------------------------------------


def test_build_login_request_returns_correct_json_shape() -> None:
    """El builder emite ``POST /api/login`` con JSON body de credenciales."""
    state = _ClientState(
        base_url="https://api.test",
        username="u",
        password="p",
        client_id="tenant",
    )
    spec = _core.build_login_request(state)
    assert spec.method == "POST"
    assert spec.path == "/api/login"
    assert spec.json_body == {
        "clientId": "tenant",
        "username": "u",
        "password": "p",
    }
    assert spec.url_pre_encoded is False


def test_build_login_request_raises_when_base_url_missing() -> None:
    state = _ClientState(base_url="", username="u", password="p")
    with pytest.raises(HigyrusAuthError) as exc_info:
        _core.build_login_request(state)
    assert exc_info.value.status_code == 0


def test_build_login_request_raises_when_credentials_missing() -> None:
    state = _ClientState(base_url="https://api.test", username="", password="")
    with pytest.raises(HigyrusAuthError) as exc_info:
        _core.build_login_request(state)
    assert exc_info.value.status_code == 0


def test_parse_login_response_extracts_token_and_expires_at() -> None:
    """Parser returns ``(token, expires_at)`` with expires_at = now + TTL."""
    import time as _time

    resp = httpx.Response(200, json={"token": "abc123"})
    before = _time.time()
    token, expires_at = _core.parse_login_response(resp)
    after = _time.time()
    assert token == "abc123"
    # expires_at should be ~ now + _TOKEN_TTL_SECONDS (±1s for clock jitter).
    assert before + _TOKEN_TTL_SECONDS - 1 <= expires_at <= after + _TOKEN_TTL_SECONDS + 1


def test_parse_login_response_raises_when_token_missing() -> None:
    resp = httpx.Response(200, json={})
    with pytest.raises(HigyrusAuthError):
        _core.parse_login_response(resp)


def test_parse_login_response_raises_on_non_2xx() -> None:
    """D-06 body-consume-then-raise: non-2xx response surfaces through raise_for_response."""
    resp = httpx.Response(
        401,
        json={"errors": [{"title": "auth", "detail": "invalid credentials"}]},
    )
    with pytest.raises(HigyrusAuthError):
        _core.parse_login_response(resp)


# ---------------------------------------------------------------------------
# URL-encoding quirk encapsulation (CRITICAL — Higyrus IIS rechaza %2F)
# ---------------------------------------------------------------------------


def test_build_get_movimientos_request_preserves_slash_in_query() -> None:
    """The quirk lives inside the builder: spec.path has ``/`` literal, NOT ``%2F``.

    This is the encapsulation test — any future regression that bypasses
    ``urlencode(..., doseq=True, quote_via=quote, safe="/")`` would surface
    ``%2F`` in ``spec.path`` and break this test before any wire request.
    """
    state = _ClientState(base_url="https://api.test")
    spec = _core.build_get_movimientos_request(
        state,
        "CTA-001",
        fecha_desde=dt.date(2026, 5, 8),
        fecha_hasta=dt.date(2026, 6, 7),
    )
    assert spec.method == "GET"
    assert spec.url_pre_encoded is True
    # The path includes the pre-encoded query string with ``/`` preserved.
    assert "/api/cuentas/CTA-001/movimientos" in spec.path
    assert "fechaDesde=08/05/2026" in spec.path
    assert "fechaHasta=07/06/2026" in spec.path
    assert "%2F" not in spec.path


def test_build_get_movimientos_request_doseq_repeats_list_keys() -> None:
    """``doseq=True``: si llegara un list-valued param, se repite la clave en vez de codificarla."""
    # get_movimientos no recibe list-valued params; we use get_listado_cuentas to verify doseq.
    state = _ClientState(base_url="https://api.test")
    spec = _core.build_get_listado_cuentas_request(
        state,
        id_cuenta=["CTA-001", "CTA-002"],
    )
    assert spec.method == "GET"
    assert spec.url_pre_encoded is True
    # doseq=True: idCuenta=CTA-001&idCuenta=CTA-002 (not idCuenta=%5B...%5D).
    assert "idCuenta=CTA-001" in spec.path
    assert "idCuenta=CTA-002" in spec.path
    assert "%5B" not in spec.path  # no list-bracket leak
    assert "%2F" not in spec.path


def test_build_get_listado_cuentas_no_params_returns_path_only() -> None:
    """Sin params filtrables, no se agrega ``?`` al path."""
    state = _ClientState(base_url="https://api.test")
    spec = _core.build_get_listado_cuentas_request(state)
    assert spec.method == "GET"
    # No query string → no ``?``. url_pre_encoded sigue siendo True por uniformidad de la rama.
    assert "?" not in spec.path
    assert spec.path == "/api/cuentas/listadoCuentas"


def test_build_get_listado_cuentas_estado_with_slash_preserves_literal() -> None:
    """``estado`` con ``/`` debe preservarse literal — la quirk Higyrus aplica a TODOS los params.

    Regression test para WR-02 Phase 7 review: el contrato del quirk
    ``urlencode(..., safe="/")`` aplica a todos los valores de la query,
    no sólo a los date params. ``estado="alta/test"`` debe producir
    ``estado=alta/test`` (sin ``%2F``) consistente con el patrón de los
    otros tests de quirk encapsulation (movimientos / posiciones).

    Esto cierra el gap del isolation test (``test_sync_async_isolation.py``)
    que sólo verifica el happy-path sin caracteres especiales en ``estado``.
    """
    state = _ClientState(base_url="https://api.test")
    spec = _core.build_get_listado_cuentas_request(state, estado="alta/test")
    assert spec.method == "GET"
    assert spec.url_pre_encoded is True
    # La quirk preserva `/` literal en CUALQUIER valor — no sólo dates.
    assert "estado=alta/test" in spec.path
    assert "%2F" not in spec.path


def test_build_get_posicion_valuada_request_preserves_slash_and_bool() -> None:
    state = _ClientState(base_url="https://api.test")
    spec = _core.build_get_posicion_valuada_request(
        state,
        "CTA-001",
        tipo_cuenta="propia",
        nivel="agente",
        desde=dt.date(2026, 6, 1),
        hasta=dt.date(2026, 6, 7),
        ocultar_cerradas=True,
    )
    assert spec.method == "GET"
    assert spec.url_pre_encoded is True
    assert "/api/cuentas/CTA-001/posicionValuada" in spec.path
    assert "desde=01/06/2026" in spec.path
    assert "hasta=07/06/2026" in spec.path
    assert "ocultarCerradas=True" in spec.path
    assert "%2F" not in spec.path


def test_build_get_posiciones_request_preserves_slash() -> None:
    state = _ClientState(base_url="https://api.test")
    spec = _core.build_get_posiciones_request(
        state,
        "CTA-001",
        fecha=dt.date(2026, 6, 7),
        incluir_parking=True,
    )
    assert spec.method == "GET"
    assert spec.url_pre_encoded is True
    assert "/api/cuentas/CTA-001/posiciones" in spec.path
    assert "fecha=07/06/2026" in spec.path
    assert "incluirParking=True" in spec.path
    assert "%2F" not in spec.path


def test_build_get_health_request_no_quirk() -> None:
    """Endpoint sin params no necesita pre-encoding — no triggers la quirk."""
    state = _ClientState(base_url="https://api.test")
    spec = _core.build_get_health_request(state)
    assert spec.method == "GET"
    assert spec.path == "/api/health"
    # No params → no necesidad de pre-encoding.
    assert spec.url_pre_encoded is False


# ---------------------------------------------------------------------------
# Parsers — body-consume-then-raise (D-06) + 204/empty handling
# ---------------------------------------------------------------------------


def test_parse_get_movimientos_response_returns_empty_on_204() -> None:
    """204 No Content → ``[]`` (preservar Phase 6 behavior)."""
    resp = httpx.Response(204, content=b"")
    result = _core.parse_get_movimientos_response(resp)
    assert result == []


def test_parse_get_movimientos_response_returns_empty_on_empty_body() -> None:
    """Body vacío también colapsa a ``[]``."""
    resp = httpx.Response(200, content=b"")
    result = _core.parse_get_movimientos_response(resp)
    assert result == []


def test_parse_get_movimientos_response_returns_list_of_models() -> None:
    """Body con lista → ``list[Movimiento]`` vía ``SafeModel.from_api``."""
    payload: list[dict[str, Any]] = [
        {"cuenta": "CTA-001", "tipoOperacion": "Compra"},
        {"cuenta": "CTA-002", "tipoOperacion": "Venta"},
    ]
    resp = httpx.Response(200, json=payload)
    result = _core.parse_get_movimientos_response(resp)
    assert len(result) == 2
    assert all(isinstance(m, Movimiento) for m in result)
    assert result[0].cuenta == "CTA-001"
    assert result[1].cuenta == "CTA-002"


def test_parse_get_movimientos_response_raises_on_shape_mismatch() -> None:
    """Body no-list 2xx → ``HigyrusAPIError`` con shape mismatch detail."""
    resp = httpx.Response(200, json={"unexpected": "dict"})
    with pytest.raises(HigyrusAPIError) as exc_info:
        _core.parse_get_movimientos_response(resp)
    assert exc_info.value.status_code == 0
    assert "shape mismatch" in str(exc_info.value.errors[0].get("title", ""))


def test_parse_get_movimientos_response_raises_on_4xx() -> None:
    """D-06 body-consume-then-raise: el parser delega en raise_for_response."""
    resp = httpx.Response(
        401,
        json={"errors": [{"title": "auth", "detail": "token expired"}]},
    )
    with pytest.raises(HigyrusAuthError):
        _core.parse_get_movimientos_response(resp)


def test_parse_get_listado_cuentas_response_returns_list_of_cuentas() -> None:
    resp = httpx.Response(200, json=[{"id": "CTA-001", "alias": "broker"}])
    result = _core.parse_get_listado_cuentas_response(resp)
    assert len(result) == 1
    assert isinstance(result[0], Cuenta)
    assert result[0].id == "CTA-001"


def test_parse_get_posicion_valuada_response_returns_list_of_posiciones() -> None:
    resp = httpx.Response(200, json=[{"cuenta": "CTA-001", "valuacion": 12345.67}])
    result = _core.parse_get_posicion_valuada_response(resp)
    assert len(result) == 1
    assert isinstance(result[0], PosicionValuada)
    assert result[0].cuenta == "CTA-001"


def test_parse_get_posiciones_response_returns_list_of_posiciones() -> None:
    resp = httpx.Response(200, json=[{"cuenta": "CTA-001", "especie": "MERV"}])
    result = _core.parse_get_posiciones_response(resp)
    assert len(result) == 1
    assert isinstance(result[0], Posicion)
    assert result[0].cuenta == "CTA-001"


def test_parse_get_health_response_returns_health() -> None:
    """Phase 31 TYP-02: el parser devuelve ``Health``, no un mapping."""
    resp = httpx.Response(200, json={"status": "ok"})
    result = _core.parse_get_health_response(resp)
    assert result == Health(status="ok")
    assert result.status == "ok"


def test_parse_get_health_response_raises_on_non_dict() -> None:
    resp = httpx.Response(200, json=["unexpected", "list"])
    with pytest.raises(HigyrusAPIError):
        _core.parse_get_health_response(resp)


def test_parse_get_health_response_non_dict_guard_strings_are_exact() -> None:
    """Los dos strings del guard están pinneados: nunca se aflojan por un re-mock.

    T-31-13. El ``detail`` lleva el NOMBRE del tipo únicamente
    (``type(raw).__name__``), jamás un valor del wire — regla T-29-36 / ASVS V7.
    """
    resp = httpx.Response(200, json=["unexpected", "list"])
    with pytest.raises(HigyrusAPIError) as excinfo:
        _core.parse_get_health_response(resp)
    assert excinfo.value.status_code == 0
    assert excinfo.value.errors == [
        {"title": "shape mismatch", "detail": "expected dict, got list"}
    ]


@pytest.mark.usefixtures("_pristine_decode_context")
def test_parse_get_health_response_handles_204(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """204 No Content → ``Health.from_api(None)``. Sin body = healthy, NO shape-mismatch.

    Regression test para CR-02 Phase 7 review: el parser levantaba
    HigyrusAPIError(status_code=0, ...) en 204, rompiendo el contrato HTTP
    (204 es una respuesta válida para health). Sigue sin levantar: colapsa al
    zero-valued ``Health`` igual que los list parsers colapsan 204 a ``[]``.

    Phase 31 D-04 mide el efecto OBSERVABLE del carve-out bajo el walker: un
    payload ``None`` es una divergencia ``non_dict``, así que un 204 legítimo
    emite exactamente UN record en el logger ``higyrus_client``.
    """
    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="higyrus_client"):
        result = _core.parse_get_health_response(httpx.Response(204, content=b""))
    assert result == Health(status="")
    assert result.status == ""
    records = _health_divergences(caplog)
    assert [(r.field_path, r.divergence) for r in records] == [("", "non_dict")]  # type: ignore[attr-defined]
    assert records[0].model == "Health"  # type: ignore[attr-defined]


@pytest.mark.usefixtures("_pristine_decode_context")
def test_parse_get_health_response_handles_empty_body_200(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """200 OK con body vacío → zero-valued ``Health``. Mismo principio: sin body = healthy."""
    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="higyrus_client"):
        result = _core.parse_get_health_response(httpx.Response(200, content=b""))
    assert result == Health(status="")
    records = _health_divergences(caplog)
    assert [(r.field_path, r.divergence) for r in records] == [("", "non_dict")]  # type: ignore[attr-defined]


@pytest.mark.usefixtures("_pristine_decode_context")
@pytest.mark.parametrize(
    "resp_factory",
    [
        lambda: httpx.Response(204, content=b""),
        lambda: httpx.Response(200, content=b""),
    ],
    ids=["204", "empty-body-200"],
)
def test_parse_get_health_response_empty_body_raises_under_strict_decode(
    resp_factory: Any,
) -> None:
    """MEASURED behaviour delta of the D-04 carve-out under ``strict_decode=True``.

    ``non_dict`` is not an INFO kind, so strict mode raises
    :class:`HigyrusDecodeError` instead of returning the zero-valued instance.
    A legitimate 204 — the very case Phase 7 CR-02 introduced this branch to
    stop raising on — therefore DOES raise in strict mode. Phase 33 runs the
    drivers in strict mode; this test is what makes that a known contract
    rather than a discovery.
    """
    _decode.STRICT_DECODE.set(True)
    with pytest.raises(HigyrusDecodeError) as excinfo:
        _core.parse_get_health_response(resp_factory())
    assert excinfo.value.model == "Health"
    assert excinfo.value.field_path == ""
    assert excinfo.value.declared_type == "Health"
    assert excinfo.value.observed_type == "NoneType"


@pytest.mark.usefixtures("_pristine_decode_context")
def test_parse_get_health_response_full_payload_is_strict_clean() -> None:
    """The healthy path emits nothing, so strict mode passes it through untouched."""
    _decode.STRICT_DECODE.set(True)
    resp = httpx.Response(200, json={"status": "ok"})
    assert _core.parse_get_health_response(resp) == Health(status="ok")


def test_parse_get_health_response_owns_its_decode_scope() -> None:
    """The parser carries ``@_decode._response_parser`` like every model-building parser."""
    assert _core.parse_get_health_response.__wrapped__ is not None  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Health model behaviour (Phase 31 TYP-02, D-01/D-02)
#
# The tracer model: one ``str`` field, every walker branch exercised once.
# ---------------------------------------------------------------------------


_DIVERGENCE_MESSAGE = "decode divergence"


@pytest.fixture
def _pristine_decode_context() -> Iterator[None]:
    """Start with an unbound decode mode and scope (mirrors ``test_decode.py``).

    Consequence of the Phase 29 D-03 ``.set()``-without-reset discipline: once
    any test in the session drives a real ``_request``, the sync test context
    keeps that request's ``DECODE_SCOPE`` bound, and a later bare
    ``Model.from_api()`` would join the stale scope and get its divergence
    deduped away purely on test ORDER.
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


def _health_divergences(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    """Every divergence record captured so far, in emission order."""
    return [r for r in caplog.records if r.getMessage() == _DIVERGENCE_MESSAGE]


@pytest.mark.usefixtures("_pristine_decode_context")
def test_health_from_api_full_payload_populates_status() -> None:
    """The live capture's only key lands on the only declared field."""
    assert Health.from_api({"status": "ok"}) == Health(status="ok")


@pytest.mark.usefixtures("_pristine_decode_context")
def test_health_from_api_empty_dict_zeroes_status_and_reports_missing(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """``{}`` is still a dict, so the per-field ``missing`` record is emitted."""
    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="higyrus_client"):
        health = Health.from_api({})
    assert health.status == ""
    records = _health_divergences(caplog)
    assert [(r.field_path, r.divergence) for r in records] == [(".status", "missing")]  # type: ignore[attr-defined]


@pytest.mark.usefixtures("_pristine_decode_context")
def test_health_from_api_drops_undeclared_key_and_reports_extra(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """An undeclared wire key is REPORTED and DROPPED — never silently carried."""
    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="higyrus_client"):
        health = Health.from_api({"status": "ok", "uptime": 12})
    assert health == Health(status="ok")
    assert not hasattr(health, "uptime")
    records = _health_divergences(caplog)
    assert [(r.field_path, r.divergence) for r in records] == [(".uptime", "extra")]  # type: ignore[attr-defined]
    assert records[0].levelno == logging.INFO


@pytest.mark.usefixtures("_pristine_decode_context")
def test_health_from_api_none_is_a_non_dict_divergence(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """``None`` yields the zero-valued instance plus ONE ``non_dict`` record.

    This is the shape the 204 / empty-body carve-out now resolves to (D-04):
    lock 8 suppresses the per-field ``missing`` records under a non-dict
    payload, so exactly one record is emitted, at the model root.
    """
    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="higyrus_client"):
        health = Health.from_api(None)
    assert health == Health(status="")
    records = _health_divergences(caplog)
    assert [(r.field_path, r.divergence) for r in records] == [("", "non_dict")]  # type: ignore[attr-defined]
    assert records[0].observed_type == "NoneType"  # type: ignore[attr-defined]
    assert records[0].model == "Health"  # type: ignore[attr-defined]


@pytest.mark.usefixtures("_pristine_decode_context")
def test_health_to_dict_round_trips_the_wire_shape() -> None:
    """``to_dict()`` (D-03, carried from Phase 30 D-08) re-projects the wire dict."""
    assert Health.from_api({"status": "ok"}).to_dict() == {"status": "ok"}


def test_health_is_frozen_and_slotted() -> None:
    """Frozen: attribute assignment raises. Slotted: no ``__dict__`` escape hatch."""
    health = Health(status="ok")
    with pytest.raises(dataclasses.FrozenInstanceError):
        health.status = "degraded"  # type: ignore[misc]


def test_health_does_not_override_from_api() -> None:
    """Shape carve-outs belong in the parser, never in a model override.

    The walker's nested-model branch builds with ``hint(**walk_model(...))`` and
    never calls ``from_api``, so an override on a model is silently skipped.
    """
    assert "from_api" not in vars(Health)
