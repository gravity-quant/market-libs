"""Unit tests for ``iol_client._core`` builders / parsers (Phase 7 REFAC-03).

Cubre:

- ``RequestSpec`` shape iol (con ``data`` field para OAuth form-encoded).
- ``raise_for_response`` mapping HTTP status → exception jerárquica.
- ``token_is_fresh`` invariante (token cacheado + not yet expired).
- Auth-flow primitives — ``build_login_request`` / ``parse_login_response``
  + ``build_refresh_request`` / ``parse_refresh_response``.
- **CR-01 conditional refresh-token rotation** (Phase 6 D-05 + Phase 7
  D-02): el parser retorna ``None`` en el slot de ``refresh_token`` cuando
  el response lo omite (o lo trae vacío / non-string). Una garantía
  estructural — el transport shell sólo escribe el state cuando el slot
  retorna non-None.
- Endpoint builders / parsers (path interpolation + JSON pass-through).

Cada test construye `_ClientState(...)` o `httpx.Response(...)` synthetic
directamente — no se interactúa con el ``_default_client`` que la
conftest autouse fixture (`packages/iol-client/tests/conftest.py:25-52`)
configura para los otros tests del paquete.
"""

from __future__ import annotations

import datetime as dt
import time

import httpx
import pytest

from iol_client import _core
from iol_client._state import _TOKEN_TTL_BUFFER_SECONDS, _ClientState
from iol_client.exceptions import IOLAPIError, IOLAuthError, IOLRateLimitError
from iol_client.models import Cotizacion

# ----------------------------------------------------------------------
# RequestSpec shape
# ----------------------------------------------------------------------


def test_request_spec_has_iol_specific_data_field() -> None:
    """iol-specific: ``data`` field para OAuth form-encoded body (D-01)."""
    spec = _core.RequestSpec(
        method="POST",
        path="/token",
        data={"grant_type": "password"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert spec.method == "POST"
    assert spec.path == "/token"
    assert spec.data == {"grant_type": "password"}
    assert spec.headers == {"Content-Type": "application/x-www-form-urlencoded"}
    assert spec.params is None
    assert spec.json_body is None


def test_request_spec_is_frozen() -> None:
    """``RequestSpec`` is ``frozen=True`` — caller cannot mutate after build."""
    spec = _core.RequestSpec(method="GET", path="/foo")
    with pytest.raises((AttributeError, TypeError)):
        spec.method = "POST"  # type: ignore[misc]


# ----------------------------------------------------------------------
# raise_for_response (D-04 moved helper)
# ----------------------------------------------------------------------


def test_raise_for_response_401_raises_auth_error() -> None:
    resp = httpx.Response(401, content=b"unauthorized")
    with pytest.raises(IOLAuthError):
        _core.raise_for_response(resp)


def test_raise_for_response_403_raises_auth_error() -> None:
    resp = httpx.Response(403, content=b"forbidden")
    with pytest.raises(IOLAuthError):
        _core.raise_for_response(resp)


def test_raise_for_response_429_raises_rate_limit_error() -> None:
    resp = httpx.Response(429, content=b"slow down")
    with pytest.raises(IOLRateLimitError):
        _core.raise_for_response(resp)


def test_raise_for_response_500_raises_api_error() -> None:
    resp = httpx.Response(500, content=b"server err")
    with pytest.raises(IOLAPIError):
        _core.raise_for_response(resp)


def test_raise_for_response_2xx_is_noop() -> None:
    resp = httpx.Response(200, content=b"{}")
    _core.raise_for_response(resp)  # no raise


# ----------------------------------------------------------------------
# token_is_fresh
# ----------------------------------------------------------------------


def test_token_is_fresh_true_when_cached_and_not_expired() -> None:
    state = _ClientState(token="t", token_expires_at=time.time() + 1000)
    assert _core.token_is_fresh(state) is True


def test_token_is_fresh_false_when_expired() -> None:
    state = _ClientState(token="t", token_expires_at=time.time() - 1)
    assert _core.token_is_fresh(state) is False


def test_token_is_fresh_false_when_no_token() -> None:
    state = _ClientState(token=None, token_expires_at=time.time() + 1000)
    assert _core.token_is_fresh(state) is False


# ----------------------------------------------------------------------
# Auth flow — build_login_request
# ----------------------------------------------------------------------


def test_build_login_request_raises_on_missing_credentials() -> None:
    """Mensaje exacto Phase 6 preserve."""
    state = _ClientState(username="", password="")
    with pytest.raises(IOLAuthError, match="IOL_USER y IOL_PASSWORD son requeridos"):
        _core.build_login_request(state)


def test_build_login_request_raises_on_missing_password() -> None:
    state = _ClientState(username="u", password="")
    with pytest.raises(IOLAuthError, match="IOL_USER y IOL_PASSWORD son requeridos"):
        _core.build_login_request(state)


def test_build_login_request_returns_form_encoded_spec() -> None:
    state = _ClientState(username="alice", password="secret")
    spec = _core.build_login_request(state)
    assert spec.method == "POST"
    assert spec.path == "/token"
    assert spec.data == {
        "username": "alice",
        "password": "secret",
        "grant_type": "password",
    }
    assert spec.headers == {"Content-Type": "application/x-www-form-urlencoded"}


# ----------------------------------------------------------------------
# Auth flow — parse_login_response
# ----------------------------------------------------------------------


def test_parse_login_response_extracts_token_and_expires() -> None:
    body = b'{"access_token": "T", "expires_in": 900, "refresh_token": "R"}'
    resp = httpx.Response(200, content=body)
    before = time.time()
    token, expires_at, refresh = _core.parse_login_response(resp)
    after = time.time()

    assert token == "T"
    assert refresh == "R"
    # expires_at == now + 900 - buffer (60)
    expected_low = before + 900 - _TOKEN_TTL_BUFFER_SECONDS
    expected_high = after + 900 - _TOKEN_TTL_BUFFER_SECONDS
    assert expected_low <= expires_at <= expected_high


def test_parse_login_response_refresh_token_none_when_missing() -> None:
    """CR-01 prevention: server omite ``refresh_token`` → parser retorna None.

    El transport shell, viendo None, DEBE preservar el cached
    ``refresh_token`` en lugar de sobrescribirlo. Es la propiedad
    estructural que cierra CR-01 (Phase 6 D-05).
    """
    body = b'{"access_token": "T", "expires_in": 900}'
    resp = httpx.Response(200, content=body)
    token, _expires_at, refresh = _core.parse_login_response(resp)
    assert token == "T"
    assert refresh is None


def test_parse_login_response_refresh_token_none_when_empty_string() -> None:
    """CR-01 prevention: ``refresh_token`` truthy-empty → parser retorna None."""
    body = b'{"access_token": "T", "expires_in": 900, "refresh_token": ""}'
    resp = httpx.Response(200, content=body)
    _token, _expires_at, refresh = _core.parse_login_response(resp)
    assert refresh is None


def test_parse_login_response_refresh_token_none_when_non_string() -> None:
    """CR-01 prevention: ``refresh_token`` non-string → parser retorna None."""
    body = b'{"access_token": "T", "expires_in": 900, "refresh_token": 12345}'
    resp = httpx.Response(200, content=body)
    _token, _expires_at, refresh = _core.parse_login_response(resp)
    assert refresh is None


def test_parse_login_response_raises_on_missing_access_token() -> None:
    body = b'{"expires_in": 900}'
    resp = httpx.Response(200, content=body)
    with pytest.raises(IOLAuthError, match="No access_token in response"):
        _core.parse_login_response(resp)


def test_parse_login_response_raises_on_non_string_access_token() -> None:
    body = b'{"access_token": 123, "expires_in": 900}'
    resp = httpx.Response(200, content=body)
    with pytest.raises(IOLAuthError, match="No access_token in response"):
        _core.parse_login_response(resp)


def test_parse_login_response_propagates_401_via_raise_for_response() -> None:
    resp = httpx.Response(401, content=b"unauthorized")
    with pytest.raises(IOLAuthError):
        _core.parse_login_response(resp)


def test_parse_login_response_defaults_expires_in_to_900_when_missing() -> None:
    body = b'{"access_token": "T"}'
    resp = httpx.Response(200, content=body)
    before = time.time()
    _token, expires_at, _refresh = _core.parse_login_response(resp)
    after = time.time()
    expected_low = before + 900 - _TOKEN_TTL_BUFFER_SECONDS
    expected_high = after + 900 - _TOKEN_TTL_BUFFER_SECONDS
    assert expected_low <= expires_at <= expected_high


# ----------------------------------------------------------------------
# Auth flow — build_refresh_request / parse_refresh_response
# ----------------------------------------------------------------------


def test_build_refresh_request_raises_without_cached_refresh() -> None:
    state = _ClientState(username="u", password="p", refresh_token=None)
    with pytest.raises(IOLAuthError, match="No refresh_token cached"):
        _core.build_refresh_request(state)


def test_build_refresh_request_raises_with_empty_string_refresh() -> None:
    state = _ClientState(username="u", password="p", refresh_token="")
    with pytest.raises(IOLAuthError, match="No refresh_token cached"):
        _core.build_refresh_request(state)


def test_build_refresh_request_returns_form_encoded_spec() -> None:
    state = _ClientState(username="u", password="p", refresh_token="R0")
    spec = _core.build_refresh_request(state)
    assert spec.method == "POST"
    assert spec.path == "/token"
    assert spec.data == {"refresh_token": "R0", "grant_type": "refresh_token"}
    assert spec.headers == {"Content-Type": "application/x-www-form-urlencoded"}


def test_parse_refresh_response_returns_none_refresh_when_omitted() -> None:
    """CR-01 mirror para refresh: si el server no devuelve nuevo refresh_token,
    el parser retorna None y el caller preserva el cached. Critical para que
    el refresh-chain no se invalide por una respuesta minimal."""
    body = b'{"access_token": "T2", "expires_in": 900}'
    resp = httpx.Response(200, content=body)
    token, _expires_at, refresh = _core.parse_refresh_response(resp)
    assert token == "T2"
    assert refresh is None


def test_parse_refresh_response_returns_new_refresh_when_provided() -> None:
    body = b'{"access_token": "T2", "expires_in": 900, "refresh_token": "R2"}'
    resp = httpx.Response(200, content=body)
    token, _expires_at, refresh = _core.parse_refresh_response(resp)
    assert token == "T2"
    assert refresh == "R2"


# ----------------------------------------------------------------------
# Endpoint builders — path interpolation
# ----------------------------------------------------------------------


def test_build_get_quote_request_returns_correct_path_and_params() -> None:
    state = _ClientState(token="t")
    spec = _core.build_get_quote_request(state, "GGAL")
    assert spec.method == "GET"
    assert spec.path == "/api/v2/bcba/Titulos/GGAL/Cotizacion"
    assert spec.params == {
        "model.mercado": "bcba",
        "model.simbolo": "GGAL",
        "model.plazo": "t2",
    }


def test_build_get_quote_request_honors_mercado_and_plazo_kwargs() -> None:
    state = _ClientState(token="t")
    spec = _core.build_get_quote_request(state, "AAPL", mercado="nyse", plazo="ci")
    assert spec.path == "/api/v2/nyse/Titulos/AAPL/Cotizacion"
    assert spec.params == {
        "model.mercado": "nyse",
        "model.simbolo": "AAPL",
        "model.plazo": "ci",
    }


def test_build_get_historical_quotes_request_formats_dates_iso() -> None:
    state = _ClientState(token="t")
    spec = _core.build_get_historical_quotes_request(
        state,
        "GGAL",
        dt.date(2026, 1, 2),
        dt.date(2026, 6, 7),
    )
    assert spec.method == "GET"
    assert spec.path == (
        "/api/v2/bcba/Titulos/GGAL/Cotizacion/seriehistorica/2026-01-02/2026-06-07/sinAjustar"
    )


def test_build_get_instruments_request_default_pais() -> None:
    state = _ClientState(token="t")
    spec = _core.build_get_instruments_request(state)
    assert spec.method == "GET"
    assert spec.path == "/api/v2/argentina/Titulos/Cotizacion/Instrumentos"


def test_build_get_instruments_by_type_request_correct_path() -> None:
    state = _ClientState(token="t")
    spec = _core.build_get_instruments_by_type_request(state, "acciones", pais="argentina")
    assert spec.method == "GET"
    assert spec.path == "/api/v2/Cotizaciones/acciones/argentina/Todos"


# ----------------------------------------------------------------------
# Endpoint parsers
# ----------------------------------------------------------------------


def test_parse_get_quote_response_returns_a_cotizacion() -> None:
    """Plan 30-01: the parser now builds a model, not a dict.

    The previous form asserted equality against ``{"simbolo": ..., "precio":
    ...}`` — neither key is a field of :class:`Cotizacion` and neither appears
    in the committed ``get-quote.json`` corpus, so the payload is rewritten
    with a real corpus key.
    """
    resp = httpx.Response(200, content=b'{"ultimoPrecio": 1234.5}')
    data = _core.parse_get_quote_response(resp)
    assert isinstance(data, Cotizacion)
    assert data.ultimoPrecio == 1234.5


def test_parse_get_quote_response_propagates_429() -> None:
    resp = httpx.Response(429, content=b"slow down")
    with pytest.raises(IOLRateLimitError):
        _core.parse_get_quote_response(resp)


def test_parse_get_historical_quotes_response_returns_list() -> None:
    resp = httpx.Response(200, content=b'[{"fecha": "2026-01-02"}, {"fecha": "2026-01-03"}]')
    data = _core.parse_get_historical_quotes_response(resp)
    assert data == [{"fecha": "2026-01-02"}, {"fecha": "2026-01-03"}]


def test_parse_get_instruments_response_passthrough() -> None:
    resp = httpx.Response(200, content=b'{"instrumentos": [{"simbolo": "GGAL"}]}')
    data = _core.parse_get_instruments_response(resp)
    assert data == {"instrumentos": [{"simbolo": "GGAL"}]}


def test_parse_get_instruments_by_type_response_extracts_titulos_key() -> None:
    resp = httpx.Response(
        200,
        content=b'{"titulos": [{"simbolo": "GGAL"}, {"simbolo": "YPFD"}]}',
    )
    data = _core.parse_get_instruments_by_type_response(resp)
    assert data == [{"simbolo": "GGAL"}, {"simbolo": "YPFD"}]


def test_parse_get_instruments_by_type_response_returns_empty_list_when_missing() -> None:
    resp = httpx.Response(200, content=b"{}")
    data = _core.parse_get_instruments_by_type_response(resp)
    assert data == []
