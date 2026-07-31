"""Unit tests for ``market_data_client._core`` builders / parsers (Phase 20-02).

Cubre la superficie PURA del cliente market-data (Auth0 client-credentials):

- ``RequestSpec`` shape con el campo net-new ``authenticated: bool = True``
  (D-09) que en Wave 3 gatea la inyección del Bearer.
- ``raise_for_response`` mapping HTTP status → jerarquía de excepciones
  (401/403→Auth, 429→RateLimit, otro error→APIError) (D-14).
- ``token_is_fresh`` invariante (token cacheado + not yet expired) (T-20-03).
- Auth0 ``client_credentials`` grant — ``build_token_request`` (single grant,
  ``authenticated=False``, ``path=""``, form-encoded) + ``parse_token_response``
  (2-tuple ``(token, expires_at)``, buffer 60s, fallback 3600s) (D-05/D-06/D-07).
- Health builders anónimos (``/health`` y ``/health/feed``,
  ``authenticated=False``) + ``parse_health_response`` (D-08/D-09).

Cada test construye ``_ClientState(...)`` o ``httpx.Response(...)`` synthetic
directamente — no requiere conftest ni fixtures (imports puros).
"""

from __future__ import annotations

import time

import httpx
import pytest

from market_data_client import _core
from market_data_client._state import (
    _TOKEN_TTL_BUFFER_SECONDS,
    _TOKEN_TTL_FALLBACK_SECONDS,
    _ClientState,
)
from market_data_client.exceptions import (
    MarketDataAPIError,
    MarketDataAuthError,
    MarketDataRateLimitError,
)

_DUMMY_REQUEST = httpx.Request("GET", "http://t")


def _resp(status_code: int, *, json_body: dict[str, object] | None = None) -> httpx.Response:
    """Build a synthetic ``httpx.Response`` bound to a dummy request."""
    if json_body is not None:
        return httpx.Response(status_code, json=json_body, request=_DUMMY_REQUEST)
    return httpx.Response(status_code, request=_DUMMY_REQUEST)


# ----------------------------------------------------------------------
# RequestSpec shape
# ----------------------------------------------------------------------


def test_request_spec_has_authenticated_flag_default_true() -> None:
    """Net-new ``authenticated`` field defaults to True (D-09)."""
    spec = _core.RequestSpec(method="GET", path="/foo")
    assert spec.authenticated is True
    assert spec.idempotent is False
    assert spec.endpoint_name == ""
    assert spec.params is None
    assert spec.headers is None
    assert spec.json_body is None
    assert spec.data is None


def test_request_spec_is_frozen() -> None:
    """``RequestSpec`` is ``frozen=True`` — caller cannot mutate after build."""
    spec = _core.RequestSpec(method="GET", path="/foo")
    with pytest.raises((AttributeError, TypeError)):
        spec.method = "POST"  # type: ignore[misc]


# ----------------------------------------------------------------------
# build_token_request
# ----------------------------------------------------------------------


def test_build_token_request_shape() -> None:
    """Auth0 client_credentials grant: form-encoded, anonymous, idempotent."""
    state = _ClientState(
        client_id="cid",
        client_secret="csec",
        audience="aud",
        auth0_token_url="https://auth.test/oauth/token",
    )
    spec = _core.build_token_request(state)
    assert spec.method == "POST"
    assert spec.data == {
        "grant_type": "client_credentials",
        "client_id": "cid",
        "client_secret": "csec",
        "audience": "aud",
    }
    assert spec.headers == {"Content-Type": "application/x-www-form-urlencoded"}
    assert spec.idempotent is True
    assert spec.authenticated is False
    assert spec.endpoint_name == "token"
    # path="" intentional — Wave 3 dispatches to absolute auth0_token_url.
    assert spec.path == ""


def test_build_token_request_missing_client_id_raises() -> None:
    state = _ClientState(
        client_id="",
        client_secret="csec",
        audience="aud",
        auth0_token_url="https://auth.test/oauth/token",
    )
    with pytest.raises(MarketDataAuthError):
        _core.build_token_request(state)


def test_build_token_request_missing_client_secret_raises() -> None:
    state = _ClientState(
        client_id="cid",
        client_secret="",
        audience="aud",
        auth0_token_url="https://auth.test/oauth/token",
    )
    with pytest.raises(MarketDataAuthError):
        _core.build_token_request(state)


def test_build_token_request_missing_audience_raises() -> None:
    state = _ClientState(
        client_id="cid",
        client_secret="csec",
        audience="",
        auth0_token_url="https://auth.test/oauth/token",
    )
    with pytest.raises(MarketDataAuthError):
        _core.build_token_request(state)


def test_build_token_request_missing_auth0_token_url_raises() -> None:
    """WR-03: ``auth0_token_url`` is required alongside the three credentials.

    Without it the grant would POST to an empty URL and surface a confusing deep
    httpx error instead of a clean ``MarketDataAuthError``.
    """
    state = _ClientState(
        client_id="cid",
        client_secret="csec",
        audience="aud",
        auth0_token_url="",
    )
    with pytest.raises(MarketDataAuthError):
        _core.build_token_request(state)


# ----------------------------------------------------------------------
# parse_token_response
# ----------------------------------------------------------------------


def test_parse_token_response_derives_expiry() -> None:
    """expires_at ≈ now + expires_in - buffer; token echoed verbatim."""
    before = time.time()
    resp = _resp(200, json_body={"access_token": "TOK", "token_type": "Bearer", "expires_in": 3600})
    token, expires_at = _core.parse_token_response(resp)
    after = time.time()
    assert token == "TOK"
    assert before + 3600 - _TOKEN_TTL_BUFFER_SECONDS <= expires_at
    assert expires_at <= after + 3600 - _TOKEN_TTL_BUFFER_SECONDS


def test_parse_token_response_uses_present_expires_in_not_fallback() -> None:
    """A present ``expires_in`` must NOT be overridden by the 3600 fallback."""
    before = time.time()
    resp = _resp(200, json_body={"access_token": "TOK", "expires_in": 120})
    _token, expires_at = _core.parse_token_response(resp)
    after = time.time()
    assert before + 120 - _TOKEN_TTL_BUFFER_SECONDS <= expires_at
    assert expires_at <= after + 120 - _TOKEN_TTL_BUFFER_SECONDS
    # Sanity: clearly below the fallback-derived expiry.
    assert expires_at < before + _TOKEN_TTL_FALLBACK_SECONDS - _TOKEN_TTL_BUFFER_SECONDS


def test_parse_token_response_fallback_when_expires_in_absent() -> None:
    """No ``expires_in`` → derive from _TOKEN_TTL_FALLBACK_SECONDS (D-07)."""
    before = time.time()
    resp = _resp(200, json_body={"access_token": "TOK"})
    _token, expires_at = _core.parse_token_response(resp)
    after = time.time()
    assert before + _TOKEN_TTL_FALLBACK_SECONDS - _TOKEN_TTL_BUFFER_SECONDS <= expires_at
    assert expires_at <= after + _TOKEN_TTL_FALLBACK_SECONDS - _TOKEN_TTL_BUFFER_SECONDS


def test_parse_token_response_null_expires_in_uses_fallback() -> None:
    """WR-02: a present-but-null ``expires_in`` must fall back, not crash.

    ``dict.get("expires_in", default)`` only substitutes the default on an ABSENT
    key; ``{"expires_in": null}`` returns None and ``float(None)`` raised
    TypeError before the fix. Now None coerces to the fallback TTL.
    """
    before = time.time()
    resp = _resp(200, json_body={"access_token": "TOK", "expires_in": None})
    _token, expires_at = _core.parse_token_response(resp)
    after = time.time()
    assert before + _TOKEN_TTL_FALLBACK_SECONDS - _TOKEN_TTL_BUFFER_SECONDS <= expires_at
    assert expires_at <= after + _TOKEN_TTL_FALLBACK_SECONDS - _TOKEN_TTL_BUFFER_SECONDS


def test_parse_token_response_non_numeric_expires_in_uses_fallback() -> None:
    """WR-02: a non-numeric ``expires_in`` string coerces to the fallback TTL."""
    before = time.time()
    resp = _resp(200, json_body={"access_token": "TOK", "expires_in": "soon"})
    _token, expires_at = _core.parse_token_response(resp)
    after = time.time()
    assert before + _TOKEN_TTL_FALLBACK_SECONDS - _TOKEN_TTL_BUFFER_SECONDS <= expires_at
    assert expires_at <= after + _TOKEN_TTL_FALLBACK_SECONDS - _TOKEN_TTL_BUFFER_SECONDS


def test_parse_token_response_missing_access_token_raises() -> None:
    resp = _resp(200, json_body={})
    with pytest.raises(MarketDataAuthError):
        _core.parse_token_response(resp)


def test_parse_token_response_non_str_access_token_raises() -> None:
    resp = _resp(200, json_body={"access_token": 12345})
    with pytest.raises(MarketDataAuthError):
        _core.parse_token_response(resp)


def test_parse_token_response_empty_access_token_raises() -> None:
    resp = _resp(200, json_body={"access_token": ""})
    with pytest.raises(MarketDataAuthError):
        _core.parse_token_response(resp)


# ----------------------------------------------------------------------
# raise_for_response
# ----------------------------------------------------------------------


def test_raise_for_response_401_raises_auth() -> None:
    with pytest.raises(MarketDataAuthError):
        _core.raise_for_response(_resp(401))


def test_raise_for_response_403_raises_auth() -> None:
    with pytest.raises(MarketDataAuthError):
        _core.raise_for_response(_resp(403))


def test_raise_for_response_429_raises_ratelimit() -> None:
    with pytest.raises(MarketDataRateLimitError):
        _core.raise_for_response(_resp(429))


def test_raise_for_response_500_raises_apierror() -> None:
    with pytest.raises(MarketDataAPIError):
        _core.raise_for_response(_resp(500))


def test_raise_for_response_200_does_not_raise() -> None:
    _core.raise_for_response(_resp(200))  # must not raise


# ----------------------------------------------------------------------
# token_is_fresh
# ----------------------------------------------------------------------


def test_token_is_fresh_true_when_set_and_future() -> None:
    state = _ClientState(token="TOK", token_expires_at=time.time() + 3600)
    assert _core.token_is_fresh(state) is True


def test_token_is_fresh_false_when_token_none() -> None:
    state = _ClientState(token=None, token_expires_at=time.time() + 3600)
    assert _core.token_is_fresh(state) is False


def test_token_is_fresh_false_when_expired() -> None:
    state = _ClientState(token="TOK", token_expires_at=time.time() - 1)
    assert _core.token_is_fresh(state) is False


# ----------------------------------------------------------------------
# health builders + parser
# ----------------------------------------------------------------------


def test_build_health_request_anonymous() -> None:
    state = _ClientState()
    spec = _core.build_health_request(state)
    assert spec.method == "GET"
    assert spec.path == "/health"
    assert spec.authenticated is False
    assert spec.idempotent is True
    assert spec.endpoint_name == "health"


def test_build_health_feed_request_anonymous() -> None:
    state = _ClientState()
    spec = _core.build_health_feed_request(state)
    assert spec.method == "GET"
    assert spec.path == "/health/feed"
    assert spec.authenticated is False
    assert spec.idempotent is True
    assert spec.endpoint_name == "health_feed"


def test_parse_health_response_returns_dict() -> None:
    resp = _resp(200, json_body={"status": "ok"})
    data = _core.parse_health_response(resp)
    assert data == {"status": "ok"}


def test_parse_health_response_raises_on_error_status() -> None:
    resp = _resp(500, json_body={"status": "down"})
    with pytest.raises(MarketDataAPIError):
        _core.parse_health_response(resp)


# ----------------------------------------------------------------------
# symbols write builders (Plan 25-02, MUT-MD-01) — POST/PATCH, idempotent=True
# ----------------------------------------------------------------------


def test_build_create_symbol_request_posts_serialized_body() -> None:
    state = _ClientState()
    body = {"symbol": "DLR/DIC26", "market_id": "ROFX"}
    spec = _core.build_create_symbol_request(state, body)
    assert spec.method == "POST"
    assert spec.path == "/symbols"
    assert spec.json_body == body
    assert spec.idempotent is True
    assert spec.authenticated is True
    assert spec.endpoint_name == "create_symbol"


def test_build_create_symbols_request_posts_batch_body() -> None:
    state = _ClientState()
    body = {"symbols": [{"symbol": "A", "market_id": "ROFX"}]}
    spec = _core.build_create_symbols_request(state, body)
    assert spec.method == "POST"
    assert spec.path == "/symbols/batch"
    assert spec.json_body == body
    assert spec.idempotent is True
    assert spec.authenticated is True
    assert spec.endpoint_name == "create_symbols"


def test_build_update_symbol_request_patches_id_path() -> None:
    state = _ClientState()
    body = {"active": False}
    spec = _core.build_update_symbol_request(state, "DLR/DIC26", body)
    assert spec.method == "PATCH"
    assert spec.path == "/symbols/DLR/DIC26"
    assert spec.json_body == body
    assert spec.idempotent is True
    assert spec.authenticated is True
    assert spec.endpoint_name == "update_symbol"


def test_symbols_write_builders_are_state_independent() -> None:
    """Same payload yields identical specs for a fresh vs a configured state."""
    fresh = _ClientState()
    configured = _ClientState(
        base_url="https://other.test/api",
        token="TOK",
        client_id="cid",
    )
    create_body = {"symbol": "DLR/DIC26", "market_id": "ROFX"}
    batch_body = {"symbols": [{"symbol": "A", "market_id": "ROFX"}]}
    patch_body = {"active": True}
    assert _core.build_create_symbol_request(
        fresh, create_body
    ) == _core.build_create_symbol_request(configured, create_body)
    assert _core.build_create_symbols_request(
        fresh, batch_body
    ) == _core.build_create_symbols_request(configured, batch_body)
    assert _core.build_update_symbol_request(
        fresh, "X", patch_body
    ) == _core.build_update_symbol_request(configured, "X", patch_body)
