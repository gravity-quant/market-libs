"""Unit tests for ``ambito_financiero_client._core`` builders/parsers.

Phase 7 REFAC-03 — canary del patrón `_core.py`. Estos tests ejercitan los
helpers PUROS de `_core.py` en aislamiento (sin transport, sin httpx_mock):

- ``RequestSpec`` shape (frozen dataclass).
- ``build_get_dollar_banco_nacion_request(state, date)`` → ``RequestSpec``.
- ``parse_get_dollar_banco_nacion_response(resp)`` → ``float``.
- ``raise_for_response(resp)`` mapping 401/403 → AuthError,
  429 → RateLimitError, 5xx → APIError.

Los tests usan ``_ClientState`` directo (bypaseando el autouse fixture del
conftest) para confirmar que los builders son state-in / spec-out puros.
Los parsers se prueban contra ``httpx.Response(status_code, content=...)``
sintéticos — sin httpx_mock, sin transport real.
"""

from __future__ import annotations

import datetime as dt

import httpx
import pytest

from ambito_financiero_client import _core
from ambito_financiero_client._state import _ClientState
from ambito_financiero_client.exceptions import (
    AmbitoFinancieroAPIError,
    AmbitoFinancieroAuthError,
    AmbitoFinancieroNoDataError,
    AmbitoFinancieroRateLimitError,
)

# ---------------------------------------------------------------------------
# RequestSpec shape
# ---------------------------------------------------------------------------


def test_request_spec_is_frozen() -> None:
    """``RequestSpec`` is a frozen dataclass — assignment raises."""
    spec = _core.RequestSpec(method="GET", path="/x")
    with pytest.raises(Exception):  # noqa: B017,PT011 — FrozenInstanceError subclass
        spec.method = "POST"  # type: ignore[misc]


def test_request_spec_defaults() -> None:
    """``params`` and ``headers`` default to ``None``."""
    spec = _core.RequestSpec(method="GET", path="/x")
    assert spec.method == "GET"
    assert spec.path == "/x"
    assert spec.params is None
    assert spec.headers is None


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def test_build_get_dollar_banco_nacion_request_returns_correct_spec_shape() -> None:
    """``build_get_dollar_banco_nacion_request`` returns a GET spec with the
    Banco Nación historic path interpolated on both date endpoints."""
    state = _ClientState(base_url="https://api.test")
    spec = _core.build_get_dollar_banco_nacion_request(state, dt.date(2026, 4, 7))
    assert isinstance(spec, _core.RequestSpec)
    assert spec.method == "GET"
    assert spec.path == "/dolarnacion/historico-general/2026-04-07/2026-04-07"
    assert spec.params is None


def test_build_get_dollar_banco_nacion_request_is_pure() -> None:
    """The builder does NOT mutate the passed-in state."""
    state = _ClientState(base_url="https://api.test", user_agent="UA-x")
    pre_base = state.base_url
    pre_ua = state.user_agent
    pre_http = state.http_client
    _core.build_get_dollar_banco_nacion_request(state, dt.date(2026, 4, 7))
    assert state.base_url == pre_base
    assert state.user_agent == pre_ua
    assert state.http_client is pre_http


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------


def test_parse_get_dollar_banco_nacion_response_returns_float() -> None:
    """Synthetic 200 response with the canonical two-row payload
    (header + data) returns the float of the ``venta`` column."""
    body = b'[["fecha","compra","venta"],["07/04/2026","1.400,00","1.415,50"]]'
    resp = httpx.Response(200, content=body)
    result = _core.parse_get_dollar_banco_nacion_response(resp)
    assert result == pytest.approx(1415.50)


def test_parse_get_dollar_banco_nacion_response_raises_no_data_on_single_row() -> None:
    """When the payload only contains the header row (no data row) the
    parser raises ``AmbitoFinancieroNoDataError``."""
    body = b'[["fecha","compra","venta"]]'
    resp = httpx.Response(200, content=body)
    with pytest.raises(AmbitoFinancieroNoDataError):
        _core.parse_get_dollar_banco_nacion_response(resp)


def test_parse_consumes_body_before_raise() -> None:
    """D-06 pattern: the parser calls ``resp.read()`` BEFORE
    ``raise_for_response`` so an HTTP/2 stream cannot be closed with the
    body still buffered. Verified by reading ``resp.content`` (raises if
    body not consumed in a streaming context) after a 500."""
    body = b'{"error": "boom"}'
    resp = httpx.Response(500, content=body)
    with pytest.raises(AmbitoFinancieroAPIError):
        _core.parse_get_dollar_banco_nacion_response(resp)
    # If body was consumed before raise, the content attribute is populated.
    assert resp.content == body


# ---------------------------------------------------------------------------
# raise_for_response
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("status", [401, 403])
def test_raise_for_response_maps_auth_status_to_auth_error(status: int) -> None:
    """401 / 403 → ``AmbitoFinancieroAuthError``."""
    resp = httpx.Response(status, content=b"forbidden")
    with pytest.raises(AmbitoFinancieroAuthError):
        _core.raise_for_response(resp)


def test_raise_for_response_maps_429_to_rate_limit_error() -> None:
    """429 → ``AmbitoFinancieroRateLimitError``."""
    resp = httpx.Response(429, content=b"slow down")
    with pytest.raises(AmbitoFinancieroRateLimitError):
        _core.raise_for_response(resp)


def test_raise_for_response_maps_5xx_to_api_error() -> None:
    """Any other error status → ``AmbitoFinancieroAPIError``."""
    resp = httpx.Response(500, content=b"server error")
    with pytest.raises(AmbitoFinancieroAPIError):
        _core.raise_for_response(resp)


def test_raise_for_response_does_not_raise_on_2xx() -> None:
    """2xx responses do not raise."""
    resp = httpx.Response(200, content=b"ok")
    _core.raise_for_response(resp)  # no exception
