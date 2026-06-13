"""Unit tests for ``matriz_client._core``.

Phase 7 Plan 05 — CR-03 cierre (body-consume-then-raise) + envelope shape +
risk probes + auth-flow primitives. El test crítico es
``test_parse_envelope_consumes_body_before_raise`` (D-06 / Pitfall 3): si el
parser intentara ``raise_for_response`` antes de ``resp.read()``, futuro
``httpx.Client(http2=True)`` introduciría stream leaks en el connection pool.

NO importa de ``matriz_client.client`` ni ``matriz_client.aio`` — solo
``matriz_client._core``, ``matriz_client._state``, ``matriz_client.exceptions``.
"""

from __future__ import annotations

import time
from typing import Any

import httpx
import pytest

from matriz_client import _core
from matriz_client._state import _ClientState
from matriz_client.exceptions import AuthenticationError, PrimaryAPIError


def _make_response(
    *,
    status_code: int = 200,
    json_body: Any | None = None,
    headers: dict[str, str] | None = None,
    text: str | None = None,
    url: str = "https://api.test/x",
) -> httpx.Response:
    """Construye un ``httpx.Response`` reproducible para tests unitarios.

    Usa el constructor directo (sin servidor) para que podamos manipular el
    ciclo de vida del body (closed/streamed/etc.) en ``test_parse_envelope_*``.
    El ``request`` queda asociado para que ``raise_for_status`` no falle con
    ``RuntimeError`` cuando los tests ejercitan códigos 4xx/5xx.
    """
    request = httpx.Request("GET", url)
    if text is not None:
        return httpx.Response(
            status_code=status_code,
            headers=headers or {},
            text=text,
            request=request,
        )
    return httpx.Response(
        status_code=status_code,
        headers=headers or {},
        json=json_body if json_body is not None else {},
        request=request,
    )


# ----------------------------------------------------------------------
# CR-03 CRITICAL guard — body MUST be consumed before any raise
# ----------------------------------------------------------------------


def test_parse_envelope_consumes_body_before_raise() -> None:
    """CR-03 guard (Pitfall 3 / D-06): body se consume ANTES del raise.

    Si ``parse_envelope_response`` raise un ``PrimaryAPIError`` por
    ``status == "ERROR"``, el body DEBE estar buffered en memoria (i.e.
    ``resp.read()`` ya se ejecutó). Sin esto, un futuro
    ``httpx.Client(http2=True)`` deja streams abiertos hasta GC del response
    object, agotando el connection pool.

    Verificación: tras el raise, ``resp.content`` (el buffer interno) está
    accesible sin lanzar ``ResponseNotRead`` — proof de que ``resp.read()``
    corrió. Sin la fix CR-03, ``resp.content`` levantaría ``ResponseNotRead``
    cuando el response viene en streaming mode (httpx default para responses
    sin ``content=...`` pre-cargado).
    """
    # Response con status=ERROR en el envelope body (200 OK HTTP, pero
    # status="ERROR" en el JSON — caso real Primary API).
    resp = _make_response(
        status_code=200,
        json_body={"status": "ERROR", "description": "boom", "message": "bad"},
    )

    with pytest.raises(PrimaryAPIError) as exc_info:
        _core.parse_envelope_response(resp, "/x")

    # CRITICAL: tras el raise, el body debe estar buffered (no ResponseNotRead).
    # `resp.content` lanza httpx.ResponseNotRead si nunca se llamó resp.read().
    # Si el orden CR-03 estuviera mal (raise antes de read), este access
    # explotaría con ResponseNotRead.
    assert resp.content is not None
    assert b"boom" in resp.content  # body presente en buffer
    # Y el exception es el esperado:
    assert exc_info.value.description == "boom"
    assert exc_info.value.api_message == "bad"


def test_parse_envelope_response_returns_dict_on_success() -> None:
    """Happy path: status OK + body dict → retorna el dict."""
    resp = _make_response(json_body={"status": "OK", "segments": [{"x": 1}]})
    data = _core.parse_envelope_response(resp, "/rest/segment/all")
    assert data["status"] == "OK"
    assert data["segments"] == [{"x": 1}]


def test_parse_envelope_response_raises_on_non_dict_root() -> None:
    """Shape check: body NO es dict → PrimaryAPIError tipado."""
    resp = _make_response(json_body=[1, 2, 3])
    with pytest.raises(PrimaryAPIError) as exc_info:
        _core.parse_envelope_response(resp, "/oops")
    assert "expected JSON object body" in (exc_info.value.description or "")
    assert "list" in (exc_info.value.description or "")


def test_parse_envelope_response_raises_on_status_error() -> None:
    """``status == "ERROR"`` → ``PrimaryAPIError`` con description + message."""
    resp = _make_response(
        json_body={"status": "ERROR", "description": "bad symbol", "message": "x"}
    )
    with pytest.raises(PrimaryAPIError) as exc_info:
        _core.parse_envelope_response(resp, "/x")
    assert exc_info.value.description == "bad symbol"
    assert exc_info.value.api_message == "x"


def test_parse_envelope_response_raises_on_http_error_status() -> None:
    """HTTP 5xx → ``PrimaryAPIError`` via raise_for_response (WR-08 Phase 8 review).

    Previously this returned stdlib ``httpx.HTTPStatusError``; the WR-08 fix
    maps 4xx/5xx to typed ``PrimaryAPIError`` (mirror iol/higyrus) so callers
    can ``except MatrizClientError:`` to catch all matriz failures.
    """
    resp = _make_response(status_code=500, json_body={"status": "ERROR"})
    with pytest.raises(PrimaryAPIError) as exc_info:
        _core.parse_envelope_response(resp, "/x")
    assert "HTTP 500" in (exc_info.value.description or "")


def test_raise_for_response_maps_401_to_authentication_error() -> None:
    """WR-08: 401/403 → ``AuthenticationError`` (PrimaryAPIError subclass)."""
    resp = _make_response(status_code=401, json_body={})
    with pytest.raises(AuthenticationError):
        _core.raise_for_response(resp)


def test_raise_for_response_maps_403_to_authentication_error() -> None:
    """WR-08: 403 → ``AuthenticationError`` (same as 401)."""
    resp = _make_response(status_code=403, json_body={})
    with pytest.raises(AuthenticationError):
        _core.raise_for_response(resp)


def test_raise_for_response_maps_500_to_primary_api_error() -> None:
    """WR-08: 5xx → ``PrimaryAPIError``."""
    resp = _make_response(status_code=503, json_body={})
    with pytest.raises(PrimaryAPIError) as exc_info:
        _core.raise_for_response(resp)
    assert "HTTP 503" in (exc_info.value.description or "")


def test_raise_for_response_noop_on_2xx() -> None:
    """WR-08: 2xx returns without raising — consistent with iol/higyrus."""
    resp = _make_response(status_code=200, json_body={"ok": True})
    _core.raise_for_response(resp)  # no raise


# ----------------------------------------------------------------------
# unwrap helper
# ----------------------------------------------------------------------


def test_unwrap_raises_on_missing_key() -> None:
    """Envelope key ausente → ``PrimaryAPIError`` tipado (D-MATZ-9)."""
    with pytest.raises(PrimaryAPIError) as exc_info:
        _core.unwrap({"some_other_key": []}, "segments", "/rest/segment/all")
    assert "missing envelope key 'segments'" in (exc_info.value.description or "")


def test_unwrap_returns_value_when_key_present() -> None:
    """Envelope key presente → retorna el value."""
    value = _core.unwrap({"segments": [{"x": 1}]}, "segments", "/rest/segment/all")
    assert value == [{"x": 1}]


# ----------------------------------------------------------------------
# Auth-flow primitives
# ----------------------------------------------------------------------


def test_build_login_request_includes_username_password_headers() -> None:
    """``build_login_request`` emite RequestSpec POST con headers de creds."""
    state = _ClientState()
    state.username = "u"
    state.password = "p"
    spec = _core.build_login_request(state)
    assert spec.method == "POST"
    assert spec.path == "/auth/getToken"
    assert spec.headers == {"X-Username": "u", "X-Password": "p"}
    assert spec.auth_basic is None
    assert spec.params is None


def test_build_login_request_raises_on_empty_credentials() -> None:
    """``build_login_request`` con creds vacías → ``AuthenticationError`` antes de I/O."""
    state = _ClientState()
    state.username = ""
    state.password = ""
    with pytest.raises(AuthenticationError):
        _core.build_login_request(state)


def test_parse_login_response_extracts_x_auth_token_header() -> None:
    """``parse_login_response`` extrae el token del response header ``X-Auth-Token``.

    D-22 Phase 6: Primary API retorna el token en el response header, NO en
    el body. ``expires_at`` es ``time.time() + _TOKEN_TTL`` (23h).
    """
    resp = _make_response(status_code=200, headers={"X-Auth-Token": "tkn-abc"})
    before = time.time()
    token, expires_at = _core.parse_login_response(resp)
    after = time.time()
    assert token == "tkn-abc"
    # _TOKEN_TTL = 23 * 60 * 60 = 82800 segundos
    assert before + 82800 - 1 <= expires_at <= after + 82800 + 1


def test_parse_login_response_raises_on_missing_header() -> None:
    """``parse_login_response`` sin ``X-Auth-Token`` header → ``AuthenticationError``."""
    resp = _make_response(status_code=200, headers={})
    with pytest.raises(AuthenticationError):
        _core.parse_login_response(resp)


def test_token_is_fresh_returns_true_when_token_set_and_unexpired() -> None:
    """``token_is_fresh`` True cuando hay token + expires_at en el futuro."""
    state = _ClientState()
    state.token = "abc"
    state.token_expires_at = time.time() + 60.0
    assert _core.token_is_fresh(state) is True


def test_token_is_fresh_returns_false_when_no_token() -> None:
    """``token_is_fresh`` False cuando no hay token cacheado."""
    state = _ClientState()
    state.token = None
    state.token_expires_at = time.time() + 60.0
    assert _core.token_is_fresh(state) is False


def test_token_is_fresh_returns_false_when_expired() -> None:
    """``token_is_fresh`` False cuando expires_at quedó en el pasado."""
    state = _ClientState()
    state.token = "abc"
    state.token_expires_at = time.time() - 1.0
    assert _core.token_is_fresh(state) is False


# ----------------------------------------------------------------------
# Risk API builders (auth_basic — D-07)
# ----------------------------------------------------------------------


def test_build_get_detailed_positions_request_uses_auth_basic() -> None:
    """Risk API: ``auth_basic=(state.username, state.password)`` (D-07)."""
    state = _ClientState()
    state.username = "risk-user"
    state.password = "risk-pass"
    spec = _core.build_get_detailed_positions_request(state, "ACC1")
    assert spec.method == "GET"
    assert spec.path == "/rest/risk/detailedPosition/ACC1"
    assert spec.auth_basic == ("risk-user", "risk-pass")


def test_build_get_account_report_request_uses_auth_basic() -> None:
    """Risk API ``accountReport``: ``auth_basic`` populated (D-07)."""
    state = _ClientState()
    state.username = "u"
    state.password = "p"
    spec = _core.build_get_account_report_request(state, "ACC1")
    assert spec.path == "/rest/risk/accountReport/ACC1"
    assert spec.auth_basic == ("u", "p")


def test_build_get_positions_request_uses_auth_basic() -> None:
    """Risk API ``getPositions``: ``auth_basic`` populated (envelope via _unwrap)."""
    state = _ClientState()
    state.username = "u"
    state.password = "p"
    spec = _core.build_get_positions_request(state, "ACC1")
    assert spec.path == "/rest/risk/position/getPositions/ACC1"
    assert spec.auth_basic == ("u", "p")


# ----------------------------------------------------------------------
# Endpoint builders sanity
# ----------------------------------------------------------------------


def test_build_get_segments_request_is_get_method() -> None:
    """Sanity: segments builder retorna GET /rest/segment/all sin params/headers."""
    spec = _core.build_get_segments_request(_ClientState())
    assert spec.method == "GET"
    assert spec.path == "/rest/segment/all"
    assert spec.params is None
    assert spec.auth_basic is None


def test_build_get_market_data_request_joins_entries() -> None:
    """Market data: ``entries`` se serializa con ``,`` join."""
    spec = _core.build_get_market_data_request(
        _ClientState(), "DLR/DIC23", entries=("BI", "OF", "LA"), depth=5
    )
    assert spec.params is not None
    assert spec.params["entries"] == "BI,OF,LA"
    assert spec.params["depth"] == 5


def test_build_new_order_request_omits_optional_params() -> None:
    """new_order: ``price``/``displayQty``/``expireDate`` omitidos cuando None."""
    spec = _core.build_new_order_request(_ClientState(), "S", "SELL", 1, "A")
    assert spec.params is not None
    assert "price" not in spec.params
    assert "displayQty" not in spec.params
    assert "expireDate" not in spec.params


def test_parse_get_detailed_positions_response_returns_model() -> None:
    """Risk parser: payload raíz → ``DetailedPosition`` (NO envelope unwrap)."""
    resp = _make_response(
        json_body={
            "account": "ACC1",
            "totalDailyDiffPlain": 1.5,
            "totalMarketValue": 1000.0,
            "lastCalculation": "2025-01-01T00:00:00Z",
        }
    )
    result = _core.parse_get_detailed_positions_response(resp, "ACC1")
    assert result.account == "ACC1"
    assert result.totalDailyDiffPlain == 1.5
