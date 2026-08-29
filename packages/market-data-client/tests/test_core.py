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

import dataclasses
import json
import logging
import pathlib
import time
from collections.abc import Iterator
from typing import Any, cast

import httpx
import pytest

from market_data_client import _core, _decode, models
from market_data_client._state import (
    _TOKEN_TTL_BUFFER_SECONDS,
    _TOKEN_TTL_FALLBACK_SECONDS,
    _ClientState,
)
from market_data_client.exceptions import (
    MarketDataAPIError,
    MarketDataAuthError,
    MarketDataDecodeError,
    MarketDataError,
    MarketDataRateLimitError,
)
from market_data_client.models import (
    AddHolidaysResult,
    CalendarDay,
    DeleteHolidayResult,
    FeedIngestor,
    FeedMarket,
    FeedPipeline,
    Health,
    HealthAuth,
    HealthFeed,
    SafeModel,
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


def test_parse_health_response_returns_health_model() -> None:
    """Phase 31 TYP-02: the parser returns a typed ``Health``, not a mapping."""
    resp = _resp(200, json_body={"status": "ok"})
    health = _core.parse_health_response(resp)
    assert isinstance(health, Health)
    assert health.status == "ok"


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


def test_build_update_symbol_request_accepts_int_row_id() -> None:
    """D-09/D-22: el builder acepta el id ENTERO y lo interpola sin encodear."""
    spec = _core.build_update_symbol_request(_ClientState(), 8123, {"active": False})
    assert spec.path == "/symbols/8123"


def test_build_update_symbol_request_int_and_str_forms_agree() -> None:
    """El ensanche no bifurca: ``8123`` y ``"8123"`` producen el mismo path."""
    body = {"active": False}
    assert (
        _core.build_update_symbol_request(_ClientState(), 8123, body).path
        == _core.build_update_symbol_request(_ClientState(), "8123", body).path
    )


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


# ----------------------------------------------------------------------
# calendar write builders (Plan 26-02, MUT-MD-02) — D-01 / D-02 / D-04
# ----------------------------------------------------------------------


def test_build_set_calendar_config_request_puts_serialized_body() -> None:
    state = _ClientState()
    body = {"market_hours": [{"weekday": 1, "open": "10:00", "close": "17:00"}]}
    spec = _core.build_set_calendar_config_request(state, body)
    assert spec.method == "PUT"
    assert spec.path == "/calendar/config"
    assert spec.json_body == body
    assert spec.idempotent is True
    assert spec.authenticated is True
    assert spec.endpoint_name == "set_calendar_config"


def test_build_preview_calendar_config_request_posts_serialized_body() -> None:
    state = _ClientState()
    body: dict[str, Any] = {"market_hours": []}
    spec = _core.build_preview_calendar_config_request(state, body)
    assert spec.method == "POST"
    assert spec.path == "/calendar/config/preview"
    assert spec.json_body == body
    assert spec.idempotent is True
    assert spec.authenticated is True
    assert spec.endpoint_name == "preview_calendar_config"


def test_build_add_holidays_request_is_idempotent() -> None:
    """CORRECTED on measurement: the endpoint UPSERTS by date (D-20 / F-49 / F-59).

    Phase 26 declared this the package's only ``idempotent=False`` builder,
    reasoning that a replayed append would duplicate days. The LIVE-MUT-01 armed
    run measured the opposite by ROW COUNT: two identical POSTs left exactly one
    row per date on both surfaces. D-20 makes the measurement authoritative over
    the reasoning, so the flag is now ``True``.
    """
    state = _ClientState()
    body = {"days": [{"day": "2026-12-25", "description": "Navidad"}]}
    spec = _core.build_add_holidays_request(state, body)
    assert spec.method == "POST"
    assert spec.path == "/calendar/holidays"
    assert spec.json_body == body
    assert spec.idempotent is True
    assert spec.authenticated is True
    assert spec.endpoint_name == "add_holidays"


def test_build_delete_calendar_config_request_has_no_body() -> None:
    """``json_body`` stays ``None`` so httpx emits b"" and no Content-Type (D-02)."""
    state = _ClientState()
    spec = _core.build_delete_calendar_config_request(state)
    assert spec.method == "DELETE"
    assert spec.path == "/calendar/config"
    assert spec.json_body is None
    assert spec.idempotent is True
    assert spec.authenticated is True
    assert spec.endpoint_name == "delete_calendar_config"


def test_calendar_write_builders_are_state_independent() -> None:
    """Same payload yields identical specs for a fresh vs a configured state."""
    fresh = _ClientState()
    configured = _ClientState(
        base_url="https://other.test/api",
        token="TOK",
        client_id="cid",
    )
    config_body = {"market_hours": [{"weekday": 1}]}
    holidays_body = {"days": [{"day": "2026-12-25"}]}
    assert _core.build_set_calendar_config_request(
        fresh, config_body
    ) == _core.build_set_calendar_config_request(configured, config_body)
    assert _core.build_preview_calendar_config_request(
        fresh, config_body
    ) == _core.build_preview_calendar_config_request(configured, config_body)
    assert _core.build_add_holidays_request(
        fresh, holidays_body
    ) == _core.build_add_holidays_request(configured, holidays_body)
    assert _core.build_delete_calendar_config_request(
        fresh
    ) == _core.build_delete_calendar_config_request(configured)


# ----------------------------------------------------------------------
# build_delete_holiday_request + path-safety guard (Plan 26-02, D-18 / T-26-01)
# ----------------------------------------------------------------------


def test_build_delete_holiday_request_shape() -> None:
    state = _ClientState()
    spec = _core.build_delete_holiday_request(state, "2026-12-25")
    assert spec.method == "DELETE"
    assert spec.path == "/calendar/holidays/2026-12-25"
    assert spec.json_body is None
    assert spec.idempotent is True
    assert spec.authenticated is True
    assert spec.endpoint_name == "delete_holiday"


def test_build_delete_holiday_request_interpolates_day_raw() -> None:
    """A legit ISO day rides the path byte-for-byte — no percent-encoding (D-03)."""
    spec = _core.build_delete_holiday_request(_ClientState(), "2026-01-02")
    assert spec.path == "/calendar/holidays/2026-01-02"
    assert "%" not in spec.path


@pytest.mark.parametrize(
    "hostile_day",
    [
        "",
        "../config",
        "a/b",
        "2026-12-25?x=1",
        "2026-12-25#frag",
        # CR-01: a LONE dot. RFC 3986 dot-segment removal deletes the segment at
        # httpx ``build_request``, collapsing the URL onto the holidays COLLECTION.
        ".",
        "..",
        "...",
        # CR-02: percent-encoded escapes. httpx does not double-encode these, so
        # they reach the wire and the server decodes them back into the tokens the
        # old enumeration thought it had blocked.
        "%2e",
        "%2E%2E%2Fconfig",
        "%2e%2e%2fconfig",
        "%2Fconfig",
        "config%3Fx=1",
        "2026-12-25%23frag",
        # Backslash: WHATWG-normalizing proxies read it as ``/``.
        "a\\b",
        # Whitespace / control characters never belong in a path segment.
        " 2026-12-25 ",
        "2026-12-25\n",
        "2026-12-25\ttail",
    ],
)
def test_build_delete_holiday_request_rejects_path_escapes(hostile_day: str) -> None:
    """D-18: a ``day`` able to escape the path segment never builds a spec.

    Without the guard, ``day="../config"`` normalizes to ``DELETE /api/calendar/config``
    (a market-config reset) and ``day="X?a=1"`` injects a query string (T-26-01).
    The guard is a charset allow-list, so it also refuses every percent-encoded
    spelling of those tokens (CR-02) and the lone ``.`` that RFC 3986 dot-segment
    removal would otherwise erase, retargeting the collection endpoint (CR-01).
    """
    with pytest.raises(ValueError, match="single path segment"):
        _core.build_delete_holiday_request(_ClientState(), hostile_day)


@pytest.mark.parametrize(
    "non_str_day",
    [
        None,
        20261225,
        ["2026-12-25"],
        ("2026-12-25",),
        {"day": "2026-12-25"},
        object(),
    ],
)
def test_build_delete_holiday_request_rejects_non_str_day(non_str_day: Any) -> None:
    """WR-04: a non-``str`` ``day`` is a path-safety refusal, not a ``TypeError``.

    The old containment guard needed ``day`` to support ``in``: an ``int`` blew up
    with ``TypeError: argument of type 'int' is not iterable`` from INSIDE the
    guard, and a ``list`` passed it outright (``"/" in ["2026-12-25"]`` is
    ``False``) so its ``repr`` got interpolated into the path. Untyped callers —
    notebooks, ``main_*.py``, a date read from JSON as an int — reach here without
    mypy in the loop, so both must land on the same ``ValueError``.
    """
    with pytest.raises(ValueError, match="single path segment"):
        _core.build_delete_holiday_request(_ClientState(), non_str_day)


def test_build_delete_holiday_request_guard_raises_plain_value_error() -> None:
    """The guard is a client-side rejection: plain ValueError, NOT MarketDataError."""
    with pytest.raises(ValueError, match="day") as exc_info:
        _core.build_delete_holiday_request(_ClientState(), "../config")
    assert type(exc_info.value) is ValueError
    assert not isinstance(exc_info.value, MarketDataError)


def test_build_delete_holiday_request_guard_message_leaks_no_state() -> None:
    """T-26-14: the message names only ``day`` and its value — no creds, no base_url."""
    configured = _ClientState(
        base_url="https://secret-host.test/api",
        token="SUPERSECRET",
        client_secret="SHHH",
    )
    with pytest.raises(ValueError, match="day") as exc_info:
        _core.build_delete_holiday_request(configured, "../config")
    message = str(exc_info.value)
    assert "secret-host.test" not in message
    assert "SUPERSECRET" not in message
    assert "SHHH" not in message


def test_build_delete_holiday_request_does_not_validate_date_format() -> None:
    """D-13: the guard rejects escapes, not bad dates — 422 stays the server's job.

    ``%`` is out of the allow-list because it introduces percent-encoding (CR-02),
    NOT because the segment has to look like a date. A structurally impossible
    ISO date is still the server's ``422`` to issue: no client-side scalar or
    format validation lives here.
    """
    spec = _core.build_delete_holiday_request(_ClientState(), "2026-13-45")
    assert spec.path == "/calendar/holidays/2026-13-45"


@pytest.mark.parametrize("legit_day", ["2026-12-25", "2026-13-45", "2026-01-02"])
def test_build_delete_holiday_request_passes_legit_day_byte_for_byte(legit_day: str) -> None:
    """D-03 intact: an allowed ``day`` reaches the path unencoded and unaltered."""
    spec = _core.build_delete_holiday_request(_ClientState(), legit_day)
    assert spec.path == f"/calendar/holidays/{legit_day}"
    assert "%" not in spec.path


def test_build_delete_holiday_request_is_state_independent() -> None:
    fresh = _ClientState()
    configured = _ClientState(
        base_url="https://other.test/api",
        token="TOK",
        client_id="cid",
    )
    assert _core.build_delete_holiday_request(
        fresh, "2026-12-25"
    ) == _core.build_delete_holiday_request(configured, "2026-12-25")


# ----------------------------------------------------------------------
# The calendar-write parser SPLIT (Plan 26-02 → Phase 31 D-05, T-26-13)
# ----------------------------------------------------------------------
#
# ``parse_calendar_write_response`` served BOTH holiday endpoints until Phase 31,
# because the live OpenAPI declared both ``200``s as a bare schema-less
# ``object``. Phase 27's capture showed the two live shapes are UNRELATED
# (``{days, note, saved}`` versus ``{day, deleted}``), so the sharing ends:
# ``parse_add_holidays_response -> AddHolidaysResult`` and
# ``parse_delete_holiday_response -> DeleteHolidayResult``.
#
# G-4, RESOLVED TOWARD TOLERANCE. The T-26-13 tolerance of the replaced function
# is PRESERVED in both halves: an absent body, a ``null``, a JSON list and a JSON
# scalar all collapse to the ZERO-VALUED model instance and NONE of them raises.
# This deliberately differs from the disposition the two
# health parsers took in plan 31-04 (non-dict → raise): those serve READS, while
# these two serve mutations already PUBLISHED in v0.4.0, and turning tolerance
# into a raise would be a behaviour change that criterion 2's response-only
# framing does not authorize. ``parse_calendar_config_response`` is the direct
# in-package precedent for the empty-body → zero-valued-instance shape.
#
# WR-01: the collapse is in the VALUE only. The payload itself reaches
# ``from_api`` verbatim, so the ``non_dict`` divergence record still names the
# type the vendor really sent (``list`` / ``str`` / ``int``), which is what
# ``test_calendar_write_parsers_record_the_type_actually_observed`` pins.
#
# CR-02: "NONE of them raises" was only true in the DEFAULT decode mode when it
# was first written. Under ``STRICT_DECODE`` — the mode Phase 33 runs the driver
# in — the terminal ``non_dict`` record made all four branches raise
# ``MarketDataDecodeError``, on a mutation whose write the server had already
# committed. The parsers now silence the strict DISPOSITION for that one branch,
# so the claim holds in BOTH modes; the record is still emitted either way.
# ``test_calendar_write_parsers_do_not_raise_under_strict_decode`` pins the
# tolerance and ``..._still_raise_under_strict_when_a_field_diverges`` pins its
# scope — a well-shaped dict body with a divergent FIELD keeps raising.


def _raw_resp(status_code: int, content: bytes) -> httpx.Response:
    """Build a synthetic ``httpx.Response`` from a RAW body (no json= helper)."""
    return httpx.Response(status_code, content=content, request=_DUMMY_REQUEST)


def test_parse_add_holidays_response_builds_from_the_captured_body() -> None:
    """The captured ``POST /calendar/holidays`` body decodes into a populated model."""
    resp = _resp(200, json_body=_CAPTURED_ADD_HOLIDAYS)
    out = _core.parse_add_holidays_response(resp)
    assert isinstance(out, AddHolidaysResult)
    assert out.saved == 1
    assert out.note == "upsert ok"
    assert out.days[0].day == "2099-12-29"


def test_parse_delete_holiday_response_builds_from_the_captured_body() -> None:
    """The captured ``DELETE /calendar/holidays/{day}`` body decodes into a populated model."""
    resp = _resp(200, json_body=_CAPTURED_DELETE_HOLIDAY)
    out = _core.parse_delete_holiday_response(resp)
    assert isinstance(out, DeleteHolidayResult)
    assert out.day == "2099-12-29"
    assert out.deleted is True


@pytest.mark.parametrize(
    ("parser_name", "model_cls"),
    [
        ("parse_add_holidays_response", AddHolidaysResult),
        ("parse_delete_holiday_response", DeleteHolidayResult),
    ],
)
@pytest.mark.parametrize(
    ("branch", "body"),
    [
        ("absent body", b""),
        ("null body", b"null"),
        ("list body", b"[]"),
        ("scalar body", b'"texto"'),
    ],
)
def test_calendar_write_parsers_preserve_the_t2613_tolerance(
    parser_name: str, model_cls: type[SafeModel], branch: str, body: bytes
) -> None:
    """G-4: all four tolerance branches collapse to the zero-valued model, none raises.

    This is the T-26-13 tolerance of the replaced shared parser, carried forward
    verbatim and merely re-expressed through the type: what used to be ``{}`` is
    now ``Model.from_api(None)``. Turning any of these four into a raise would be
    a behaviour change on a mutation already published in v0.4.0.
    """
    parser = getattr(_core, parser_name)
    out = parser(_raw_resp(200, body))
    assert out == model_cls.from_api(None), branch


@pytest.mark.usefixtures("pristine_decode_context")
@pytest.mark.parametrize(
    ("parser_name", "model_name"),
    [
        ("parse_add_holidays_response", "AddHolidaysResult"),
        ("parse_delete_holiday_response", "DeleteHolidayResult"),
    ],
)
@pytest.mark.parametrize(
    ("body", "observed"),
    [
        (b"", "NoneType"),
        (b"null", "NoneType"),
        (b"[]", "list"),
        (b'"texto"', "str"),
        (b"7", "int"),
    ],
)
def test_calendar_write_parsers_record_the_type_actually_observed(
    parser_name: str,
    model_name: str,
    body: bytes,
    observed: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """WR-01: tolerating the shape must not erase WHAT the vendor sent.

    The parsers used to hand ``from_api`` a literal ``None`` on every non-dict
    branch, so ``walk_model``'s ``non_dict`` record — whose ``observed_type`` is
    ``type(payload).__name__`` — stamped a JSON list, a JSON string and a JSON
    number all three as ``NoneType``. Phase 33 freezes the
    ``(model, field_path, kind)`` identity of these records into its census, so
    the erasure would have been frozen with it. The payload now flows through
    verbatim; only ``NoneType`` for the genuinely absent/``null`` bodies is a
    true ``NoneType``.
    """
    parser = getattr(_core, parser_name)
    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="market_data_client"):
        parser(_raw_resp(200, body))
    records = [r for r in caplog.records if r.getMessage() == _MESSAGE]
    assert [(r.model, r.divergence, r.observed_type) for r in records] == [  # type: ignore[attr-defined]
        (model_name, "non_dict", observed)
    ]


@pytest.mark.usefixtures("pristine_decode_context")
@pytest.mark.parametrize(
    ("parser_name", "model_cls"),
    [
        ("parse_add_holidays_response", AddHolidaysResult),
        ("parse_delete_holiday_response", DeleteHolidayResult),
    ],
)
@pytest.mark.parametrize(
    ("branch", "body"),
    [
        ("absent body", b""),
        ("null body", b"null"),
        ("list body", b"[]"),
        ("scalar body", b'"texto"'),
    ],
)
def test_calendar_write_parsers_do_not_raise_under_strict_decode(
    parser_name: str,
    model_cls: type[SafeModel],
    branch: str,
    body: bytes,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """CR-02, MEASURED: the T-26-13 tolerance holds in the mode Phase 33 runs in.

    ``test_calendar_write_parsers_preserve_the_t2613_tolerance`` above never
    enables ``STRICT_DECODE``, so it pinned the tolerance only in the default
    mode. It was FALSE in strict mode: all four branches reach ``walk_model``'s
    non-dict arm, ``non_dict`` is not an ``_INFO_KIND``, and the strict sink
    raised ``MarketDataDecodeError`` — on a MUTATION, after the server had
    already committed the write, so the caller lost the acknowledgement and could
    not tell whether the holiday was upserted. ``ROADMAP.md`` schedules Phase 33
    to run ``main_market_data.py`` in strict mode against develop, which made it
    imminent rather than hypothetical.

    The parsers now silence the strict DISPOSITION for that one branch. The
    divergence record is still emitted (``_emit`` runs before the disposition),
    which is what this test also asserts: the tolerance costs the census nothing.
    """
    expected = model_cls.from_api(None)  # built while the mode is still default
    parser = getattr(_core, parser_name)
    _decode.STRICT_DECODE.set(True)
    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="market_data_client"):
        out = parser(_raw_resp(200, body))
    assert out == expected, branch
    records = [r for r in caplog.records if r.getMessage() == _MESSAGE]
    assert [r.divergence for r in records] == ["non_dict"], branch  # type: ignore[attr-defined]


@pytest.mark.usefixtures("pristine_decode_context")
@pytest.mark.parametrize(
    ("parser_name", "json_body"),
    [
        ("parse_add_holidays_response", {"days": "not-a-list", "note": "x", "saved": 1}),
        ("parse_delete_holiday_response", {"day": "2099-12-29", "deleted": 1}),
    ],
)
def test_calendar_write_parsers_still_raise_under_strict_when_a_field_diverges(
    parser_name: str, json_body: dict[str, object]
) -> None:
    """CR-02 SCOPE: the strict silence covers the terminal non-dict branch ONLY.

    A well-shaped ``dict`` acknowledgement whose FIELDS diverge is a genuine
    typing divergence on a body the server did send, not an anomalous ACK shape,
    so it keeps the strict disposition every other parser in this file has.
    """
    parser = getattr(_core, parser_name)
    _decode.STRICT_DECODE.set(True)
    with pytest.raises(MarketDataDecodeError):
        parser(_resp(200, json_body=json_body))


@pytest.mark.parametrize(
    "parser_name", ["parse_add_holidays_response", "parse_delete_holiday_response"]
)
@pytest.mark.parametrize(
    ("status_code", "exc_type"),
    [
        (422, MarketDataAPIError),
        (401, MarketDataAuthError),
        (429, MarketDataRateLimitError),
    ],
)
def test_calendar_write_parsers_raise_before_decoding(
    parser_name: str, status_code: int, exc_type: type[Exception]
) -> None:
    """Body-consume-then-raise order (Phase 7 D-06) survives the split, on both halves."""
    parser = getattr(_core, parser_name)
    resp = _raw_resp(status_code, b'{"detail": "nope"}')
    with pytest.raises(exc_type):
        parser(resp)


@pytest.mark.parametrize(
    "parser_name", ["parse_add_holidays_response", "parse_delete_holiday_response"]
)
def test_calendar_write_parsers_carry_the_response_scope_decorator(parser_name: str) -> None:
    """D-05: both halves are model-building parsers, so both open their own decode scope.

    The replaced shared parser was UNdecorated — it returned a raw mapping and
    built no model, so it had no divergences to scope.
    """
    parser = getattr(_core, parser_name)
    assert getattr(parser, "__wrapped__", None) is not None


def test_core_all_exports_calendar_write_surface_in_order() -> None:
    """One shared parser name was swapped for two; ``__all__`` stays ASCII-sorted (RUF022)."""
    expected = {
        "build_add_holidays_request",
        "build_delete_calendar_config_request",
        "build_delete_holiday_request",
        "build_preview_calendar_config_request",
        "build_set_calendar_config_request",
        "parse_add_holidays_response",
        "parse_delete_holiday_response",
    }
    assert expected <= set(_core.__all__)
    assert "parse_calendar_write_response" not in _core.__all__
    assert not hasattr(_core, "parse_calendar_write_response")
    assert list(_core.__all__) == sorted(_core.__all__)


# ----------------------------------------------------------------------
# Phase 31 (TYP-02) — the six health models
# ----------------------------------------------------------------------
#
# Field sets come from the two COMMITTED LIVE CAPTURES (D-01), never from a
# mock and never from the OpenAPI. ``_CAPTURED_HEALTH`` / ``_CAPTURED_HEALTH_FEED``
# below are payloads whose per-leaf TYPES reproduce those captures exactly, and
# ``test_captured_payloads_match_the_committed_live_schemas`` proves it by
# reducing each payload with the same keys+types projection the drivers use.
# So these tests are evidence about the WIRE, not about the author.

_SCHEMAS_DIR = (
    pathlib.Path(__file__).resolve().parents[3]
    / ".planning"
    / "verification"
    / "schemas"
    / "market-data-client"
)

_MESSAGE = "decode divergence"

_CAPTURED_HEALTH: dict[str, Any] = {
    "auth": {"configured": True, "enabled": True, "issuer": "https://auth.test/"},
    "status": "ok",
}

_CAPTURED_HEALTH_FEED: dict[str, Any] = {
    "active_symbols": 42,
    "ingestor": {
        "connected": True,
        "frames_total": 1234,
        "heartbeat_age_seconds": 0.5,
        "last_error": None,
        "last_frame_age_seconds": 0.25,
        "last_frame_at": "2026-07-31T16:00:35+00:00",
        "market": {
            "enabled": True,
            "is_open": True,
            "last_business_day": "2026-07-30",
            "local_time": "2026-07-31T13:00:35-03:00",
            "next_transition": "2026-07-31T17:00:00-03:00",
            "reason": "session open",
            "session_close": "17:00",
            "session_open": "11:00",
            "state": "open",
        },
        "pipeline": {
            "batch_interval_ms": 500,
            "conserved": True,
            "flushes": 88,
            "frames_accepted": 1200,
            "frames_coalesced": 30,
            "frames_unknown_symbol": 4,
            "last_flush_ms": 12.5,
            "last_write_at": "2026-07-31T16:00:35+00:00",
            "last_write_error": None,
            "pending": 0,
            "pending_peak": 17,
            "rows_skipped_stale": 2,
        },
        "present": True,
        "reason": "connected",
        "reconnects": 1,
        "rows_written": 1198,
        "started_at": "2026-07-31T11:00:00+00:00",
        "state": "running",
        "symbols_subscribed": 42,
        "uptime_seconds": 18035,
    },
    "newest_received_at": "2026-07-31T16:00:35+00:00",
    "oldest_received_at": "2026-07-31T15:59:35+00:00",
    "staleness_seconds": 0.9,
    "status": "ok",
    "symbols_with_data": 40,
}


def _schema_of(payload: Any) -> Any:
    """Keys + type names, never values — the same projection ``verification.schema`` uses."""
    if isinstance(payload, dict):
        return {k: _schema_of(v) for k, v in sorted(payload.items())}
    if isinstance(payload, list):
        return [_schema_of(payload[0])] if payload else []
    return type(payload).__name__


@pytest.fixture
def pristine_decode_context() -> Iterator[None]:
    """Start the test with an unbound decode mode and scope (31-03 deviation 3).

    Opt-in, NOT autouse: it must not perturb this file's existing tests. Without
    it, once any earlier test in the session drives a real ``_request`` the sync
    context keeps that request's ``DECODE_SCOPE`` bound, a later bare
    ``Model.from_api()`` joins the stale scope, and its already-seen
    ``(model, field_path, kind)`` triple is deduped away — flipping a divergence
    assertion green-to-empty purely on test ORDER.
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


def _from_api(
    factory: Any, caplog: pytest.LogCaptureFixture, payload: Any
) -> tuple[Any, list[logging.LogRecord]]:
    """Drive a shipped ``from_api`` under a FRESH scope, returning obj + divergence records."""
    caplog.clear()
    _decode.open_request_scope()
    with caplog.at_level(logging.DEBUG, logger="market_data_client"):
        obj = factory(payload)
    return obj, [r for r in caplog.records if r.getMessage() == _MESSAGE]


def test_captured_payloads_match_the_committed_live_schemas() -> None:
    """The two in-test payloads reproduce the committed captures leaf-for-leaf (D-01)."""
    for filename, payload in (
        ("get-health.json", _CAPTURED_HEALTH),
        ("get-health-feed.json", _CAPTURED_HEALTH_FEED),
    ):
        committed = json.loads((_SCHEMAS_DIR / filename).read_text(encoding="utf-8"))
        assert _schema_of(payload) == committed["schema"], filename


def test_health_from_api_populates_the_nested_auth_model() -> None:
    """``Health`` carries ``status`` plus a nested ``HealthAuth`` with all three fields."""
    health = Health.from_api(_CAPTURED_HEALTH)
    assert health.status == "ok"
    assert isinstance(health.auth, HealthAuth)
    assert health.auth.configured is True
    assert health.auth.enabled is True
    assert health.auth.issuer == "https://auth.test/"


@pytest.mark.usefixtures("pristine_decode_context")
def test_health_from_api_missing_auth_yields_zero_valued_nested_model(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A declared non-optional nested model is NEVER ``None`` — it is the zero instance."""
    health, records = _from_api(Health.from_api, caplog, {"status": "ok"})
    assert health.status == "ok"
    assert health.auth == HealthAuth(configured=False, enabled=False, issuer="")
    assert [(r.field_path, r.divergence) for r in records] == []  # type: ignore[attr-defined]


def test_health_feed_from_api_reaches_all_three_nesting_levels() -> None:
    """The full captured payload is reachable at every level without a raise."""
    feed = HealthFeed.from_api(_CAPTURED_HEALTH_FEED)
    assert feed.status == "ok"
    assert feed.active_symbols == 42
    assert feed.symbols_with_data == 40
    assert feed.staleness_seconds == 0.9
    assert feed.newest_received_at == "2026-07-31T16:00:35+00:00"
    assert feed.oldest_received_at == "2026-07-31T15:59:35+00:00"
    # level 2
    assert isinstance(feed.ingestor, FeedIngestor)
    assert feed.ingestor.connected is True
    assert feed.ingestor.state == "running"
    assert feed.ingestor.uptime_seconds == 18035
    assert feed.ingestor.last_error is None
    # level 3 — market
    assert isinstance(feed.ingestor.market, FeedMarket)
    assert feed.ingestor.market.state == "open"
    assert feed.ingestor.market.session_open == "11:00"
    # level 3 — pipeline
    assert isinstance(feed.ingestor.pipeline, FeedPipeline)
    assert feed.ingestor.pipeline.pending == 0
    assert feed.ingestor.pipeline.last_flush_ms == 12.5
    assert feed.ingestor.pipeline.last_write_error is None


@pytest.mark.usefixtures("pristine_decode_context")
def test_health_feed_from_api_none_is_the_zero_instance_plus_one_non_dict_record(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The 204 / empty-body carve-out shape: zero-valued instance, ONE terminal record."""
    feed, records = _from_api(HealthFeed.from_api, caplog, None)
    assert feed.status == ""
    assert feed.active_symbols == 0
    assert feed.ingestor.market.state == ""
    assert feed.ingestor.pipeline.pending == 0
    assert [(r.field_path, r.divergence) for r in records] == [("", "non_dict")]  # type: ignore[attr-defined]


@pytest.mark.usefixtures("pristine_decode_context")
def test_health_feed_from_api_drops_an_undeclared_key_and_reports_it_once(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """An undeclared top-level key is dropped and reported ``extra`` — exactly once."""
    payload = {**_CAPTURED_HEALTH_FEED, "brand_new_wire_key": "surprise"}
    feed, records = _from_api(HealthFeed.from_api, caplog, payload)
    assert not hasattr(feed, "brand_new_wire_key")
    assert [(r.field_path, r.divergence) for r in records] == [  # type: ignore[attr-defined]
        (".brand_new_wire_key", "extra")
    ]


def test_health_to_dict_round_trips_to_a_plain_nested_dict() -> None:
    """``to_dict()`` flattens nested models back to the plain wire mapping."""
    wire = Health.from_api(_CAPTURED_HEALTH).to_dict()
    assert wire == _CAPTURED_HEALTH
    assert isinstance(wire["auth"], dict)


def test_health_feed_to_dict_round_trips_all_three_levels() -> None:
    """The deep tree round-trips too, ``None`` holes KEPT (a model reproduces the wire)."""
    wire = HealthFeed.from_api(_CAPTURED_HEALTH_FEED).to_dict()
    assert wire == _CAPTURED_HEALTH_FEED
    assert wire["ingestor"]["last_error"] is None
    assert wire["ingestor"]["pipeline"]["last_write_error"] is None


@pytest.mark.parametrize(
    "model_cls", [Health, HealthAuth, HealthFeed, FeedIngestor, FeedMarket, FeedPipeline]
)
def test_health_models_are_frozen(model_cls: type[SafeModel]) -> None:
    """Every one of the six is immutable: attribute assignment raises."""
    obj = model_cls.from_api(None)
    field_name = dataclasses.fields(obj)[0].name  # type: ignore[arg-type]
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(obj, field_name, "mutated")


@pytest.mark.parametrize(
    "model_cls", [Health, HealthAuth, HealthFeed, FeedIngestor, FeedMarket, FeedPipeline]
)
def test_health_models_declare_no_from_api_override(model_cls: type[SafeModel]) -> None:
    """Shape carve-outs live in the PARSER — the walker never calls a nested ``from_api``."""
    assert model_cls.__dict__.get("from_api") is None


@pytest.mark.parametrize(
    "model_cls", [Health, HealthAuth, HealthFeed, FeedIngestor, FeedMarket, FeedPipeline]
)
def test_health_models_declare_no_mapping_field_and_no_received_at(
    model_cls: type[SafeModel],
) -> None:
    """No ``dict[...]`` field (4 of the 6 are nested field types) and no staleness stamp."""
    # ``cast(Any, ...)`` is the walker's own mypy-strict discipline for
    # ``get_type_hints``-driven code (``models._apply_mapping_policy`` does the same).
    hints = _decode.hints_for(cast(Any, model_cls))
    assert "received_at" not in hints
    assert not any(models._is_mapping(h) for h in hints.values())


def test_health_models_declare_exactly_the_two_locked_optionals() -> None:
    """Checkpoint verdict option-b: ONLY the two CONTEXT D-01 error fields are nullable.

    ``walk_field``'s union-with-``None`` branch returns ``None`` WITHOUT emitting a
    divergence record, so an over-declared Optional silently erases exactly the
    signal this milestone exists to surface (T-31-17). This test pins the verdict:
    a seventh Optional cannot be added to these six models without failing here.
    """
    optionals = {
        f"{cls.__name__}.{name}"
        for cls in (Health, HealthAuth, HealthFeed, FeedIngestor, FeedMarket, FeedPipeline)
        for name, hint in _decode.hints_for(cls).items()
        if models._strip_optional(hint) is not hint
    }
    assert optionals == {"FeedIngestor.last_error", "FeedPipeline.last_write_error"}


def test_safe_model_to_dict_exists_on_the_market_data_base() -> None:
    """``to_dict()`` is on the BASE (D-02), so every shipped model inherits it."""
    assert callable(SafeModel.__dict__.get("to_dict"))


# ----------------------------------------------------------------------
# Phase 31 (TYP-02) — the health parser SPLIT (D-05) and its new guard (D-04)
# ----------------------------------------------------------------------
#
# One shared parser served both endpoints until Phase 31. Their live shapes are
# unrelated, so the sharing ends: ``parse_health_response -> Health`` and
# ``parse_health_feed_response -> HealthFeed``, each named by exactly one
# endpoint, both decorated with ``@_decode._response_parser``, and both gaining
# a non-dict shape guard the shared one never had.


def test_parse_health_response_builds_from_the_captured_body() -> None:
    """The captured ``/health`` body decodes into a fully populated ``Health``."""
    resp = _resp(200, json_body=_CAPTURED_HEALTH)
    health = _core.parse_health_response(resp)
    assert isinstance(health, Health)
    assert health.status == "ok"
    assert health.auth.issuer == "https://auth.test/"


def test_parse_health_feed_response_builds_from_the_captured_body() -> None:
    """The captured ``/health/feed`` body decodes into a three-level ``HealthFeed``."""
    resp = _resp(200, json_body=_CAPTURED_HEALTH_FEED)
    feed = _core.parse_health_feed_response(resp)
    assert isinstance(feed, HealthFeed)
    assert feed.status == "ok"
    assert feed.ingestor.market.state == "open"
    assert feed.ingestor.pipeline.pending == 0


@pytest.mark.parametrize(
    ("parser_name", "body", "expected_type_name"),
    [
        ("parse_health_response", b"[]", "list"),
        ("parse_health_feed_response", b"[]", "list"),
        ("parse_health_response", b'"texto"', "str"),
        ("parse_health_feed_response", b"3", "int"),
    ],
)
def test_health_parsers_raise_on_a_non_dict_body(
    parser_name: str, body: bytes, expected_type_name: str
) -> None:
    """D-04: a 200 whose body is not a mapping raises, naming the TYPE only.

    T-31-19 / T-29-36 / ASVS V7: market-data payloads carry symbol and account
    identifiers, so the message carries ``type(raw).__name__`` and NEVER the
    value or a repr of it.
    """
    parser = getattr(_core, parser_name)
    resp = _raw_resp(200, body)
    with pytest.raises(MarketDataAPIError) as excinfo:
        parser(resp)
    assert excinfo.value.status_code == 0
    assert excinfo.value.message == f"expected dict, got {expected_type_name}"
    assert body.decode() not in str(excinfo.value)


@pytest.mark.parametrize(
    ("parser_name", "model_cls"),
    [("parse_health_response", Health), ("parse_health_feed_response", HealthFeed)],
)
@pytest.mark.parametrize(("status_code", "body"), [(204, b""), (200, b"")])
def test_health_parsers_collapse_an_empty_body_to_the_zero_instance(
    parser_name: str, model_cls: type[SafeModel], status_code: int, body: bytes
) -> None:
    """The zero-valued carve-out: a 204 / empty body NEVER raises (parse_calendar_config shape)."""
    parser = getattr(_core, parser_name)
    out = parser(_raw_resp(status_code, body))
    assert out == model_cls.from_api(None)


def test_parse_health_feed_response_raises_on_error_status() -> None:
    """Body-consume-then-raise order is preserved: an error status raises before decode."""
    resp = _resp(500, json_body={"status": "down"})
    with pytest.raises(MarketDataAPIError):
        _core.parse_health_feed_response(resp)


@pytest.mark.parametrize("parser_name", ["parse_health_response", "parse_health_feed_response"])
def test_health_parsers_carry_the_response_scope_decorator(parser_name: str) -> None:
    """D-05: every model-building parser opens its own decode scope."""
    parser = getattr(_core, parser_name)
    assert getattr(parser, "__wrapped__", None) is not None


def test_core_all_exports_the_split_health_parsers_in_order() -> None:
    """``__all__`` gains ``parse_health_feed_response`` and stays ASCII-sorted (RUF022)."""
    assert "parse_health_feed_response" in _core.__all__
    assert "parse_health_response" in _core.__all__
    assert list(_core.__all__) == sorted(_core.__all__)


# ----------------------------------------------------------------------
# Phase 31 (TYP-02) — the two calendar-WRITE mutation results (plan 31-05)
# ----------------------------------------------------------------------
#
# Field sets come from the FOUR COMMITTED LIVE CAPTURES (D-01) —
# ``add-holidays-{sync,async}-response.json`` and
# ``delete-holiday-{sync,async}-response.json`` — never from a mock and never
# from the OpenAPI (which declares both ``200``s as a bare, schema-less
# ``object``). The sync and async captures of each endpoint are BYTE-IDENTICAL;
# ``test_captured_mutation_payloads_match_all_four_committed_schemas`` proves
# both halves — that the in-test payloads reproduce the wire, AND that the two
# surfaces agree — with the same keys+types projection the drivers use.
#
# These two endpoints are already PUBLISHED as mutations in v0.4.0, so the
# change they undergo here is RESPONSE-ONLY: no request byte moves (pinned by
# ``test_v040_request_pin.py``) and the mutating gate is untouched (pinned by
# ``test_mutation_gate_ast.py``).

_CAPTURED_ADD_HOLIDAYS: dict[str, Any] = {
    "days": [
        {
            "close_time": None,
            "closed": True,
            "day": "2099-12-29",
            "description": "probe",
            "open_time": None,
        }
    ],
    "note": "upsert ok",
    "saved": 1,
}

_CAPTURED_DELETE_HOLIDAY: dict[str, Any] = {"day": "2099-12-29", "deleted": True}


def test_captured_mutation_payloads_match_all_four_committed_schemas() -> None:
    """The two in-test payloads reproduce all FOUR committed captures leaf-for-leaf.

    Four files, two payloads: the sync and async captures of each endpoint are
    byte-identical, and asserting the SAME payload against both files is that
    surface-parity evidence stated as a test rather than as prose.
    """
    for filename, payload in (
        ("add-holidays-sync-response.json", _CAPTURED_ADD_HOLIDAYS),
        ("add-holidays-async-response.json", _CAPTURED_ADD_HOLIDAYS),
        ("delete-holiday-sync-response.json", _CAPTURED_DELETE_HOLIDAY),
        ("delete-holiday-async-response.json", _CAPTURED_DELETE_HOLIDAY),
    ):
        committed = json.loads((_SCHEMAS_DIR / filename).read_text(encoding="utf-8"))
        assert _schema_of(payload) == committed["schema"], filename


def test_add_holidays_result_reuses_the_shipped_calendar_day() -> None:
    """``days[]`` decodes into the SHIPPED ``CalendarDay``, both hour fields ``None``."""
    result = AddHolidaysResult.from_api(_CAPTURED_ADD_HOLIDAYS)
    assert result.note == "upsert ok"
    assert result.saved == 1
    assert len(result.days) == 1
    day = result.days[0]
    assert isinstance(day, CalendarDay)
    assert day.day == "2099-12-29"
    assert day.closed is True
    assert day.description == "probe"
    assert day.open_time is None
    assert day.close_time is None


@pytest.mark.usefixtures("pristine_decode_context")
def test_add_holidays_result_from_api_none_is_zero_valued_plus_one_non_dict(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The tolerance shape, seen from the model: zero-valued instance, ONE terminal record."""
    result, records = _from_api(AddHolidaysResult.from_api, caplog, None)
    assert result.days == []
    assert result.note == ""
    assert result.saved == 0
    assert [(r.field_path, r.divergence) for r in records] == [("", "non_dict")]  # type: ignore[attr-defined]


@pytest.mark.usefixtures("pristine_decode_context")
def test_add_holidays_result_non_list_days_degrades_to_empty_and_reports(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The walker's collection guard governs ``days`` — no model-side override."""
    payload = {**_CAPTURED_ADD_HOLIDAYS, "days": "not-a-list"}
    result, records = _from_api(AddHolidaysResult.from_api, caplog, payload)
    assert result.days == []
    assert result.note == "upsert ok"
    assert (".days", "type") in [(r.field_path, r.divergence) for r in records]  # type: ignore[attr-defined]


def test_delete_holiday_result_decodes_the_captured_boolean() -> None:
    """The live wire sends a BOOLEAN ``deleted``; the declaration answers to it."""
    result = DeleteHolidayResult.from_api(_CAPTURED_DELETE_HOLIDAY)
    assert result.day == "2099-12-29"
    assert result.deleted is True


@pytest.mark.usefixtures("pristine_decode_context")
def test_delete_holiday_result_integer_deleted_is_not_widened_and_is_reported(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """MEASURED, not reasoned: an ``int`` arriving for a ``bool`` field is NOT widened.

    ``{"deleted": 1}`` is the shape the pre-Phase-31 mock in
    ``test_calendar_write.py`` asserted; the live capture says ``bool``. Running
    it (rather than assuming) shows ``walk_field``'s ``hint is bool`` branch takes
    the ``isinstance(value, bool)`` check — which an ``int`` fails — emits a
    ``type`` divergence ``declared=bool / observed=int``, and substitutes
    ``policy.missing_bool`` because ``POLICY.scalar_passthrough is False``.

    OBSERVED OUTCOME (2026-08-25, market-data ``POLICY``): ``deleted is False``
    plus exactly one ``(".deleted", "type")`` record. So the integer is neither
    silently absorbed nor truthy-coerced — it is RECORDED and zeroed. Contrast
    Phase 29's matriz finding, where an ``int`` arriving for a ``float``-declared
    field DOES widen; the two branches differ and this one had to be measured.
    """
    result, records = _from_api(
        DeleteHolidayResult.from_api, caplog, {"day": "2099-12-29", "deleted": 1}
    )
    assert result.day == "2099-12-29"
    assert result.deleted is False
    assert [(r.field_path, r.divergence) for r in records] == [(".deleted", "type")]  # type: ignore[attr-defined]
    assert [(r.declared_type, r.observed_type) for r in records] == [("bool", "int")]  # type: ignore[attr-defined]


@pytest.mark.usefixtures("pristine_decode_context")
def test_delete_holiday_result_from_api_none_is_zero_valued_plus_one_non_dict(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The tolerance shape for the delete: zero-valued instance, ONE terminal record."""
    result, records = _from_api(DeleteHolidayResult.from_api, caplog, None)
    assert result.day == ""
    assert result.deleted is False
    assert [(r.field_path, r.divergence) for r in records] == [("", "non_dict")]  # type: ignore[attr-defined]


def test_mutation_results_to_dict_round_trip_to_plain_nested_dicts() -> None:
    """``to_dict()`` flattens the nested ``CalendarDay`` rows back to the wire mapping."""
    add_wire = AddHolidaysResult.from_api(_CAPTURED_ADD_HOLIDAYS).to_dict()
    assert add_wire == _CAPTURED_ADD_HOLIDAYS
    assert isinstance(add_wire["days"][0], dict)
    assert DeleteHolidayResult.from_api(_CAPTURED_DELETE_HOLIDAY).to_dict() == (
        _CAPTURED_DELETE_HOLIDAY
    )


@pytest.mark.parametrize("model_cls", [AddHolidaysResult, DeleteHolidayResult])
def test_mutation_result_models_are_frozen(model_cls: type[SafeModel]) -> None:
    """Both mutation results are immutable: attribute assignment raises."""
    obj = model_cls.from_api(None)
    field_name = dataclasses.fields(obj)[0].name  # type: ignore[arg-type]
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(obj, field_name, "mutated")


@pytest.mark.parametrize("model_cls", [AddHolidaysResult, DeleteHolidayResult])
def test_mutation_result_models_declare_no_from_api_override(
    model_cls: type[SafeModel],
) -> None:
    """A shape carve-out belongs in the PARSER — a nested override is silently skipped."""
    assert model_cls.__dict__.get("from_api") is None


@pytest.mark.parametrize("model_cls", [AddHolidaysResult, DeleteHolidayResult])
def test_mutation_result_models_declare_no_mapping_field_no_received_at_no_optional(
    model_cls: type[SafeModel],
) -> None:
    """No ``dict[...]`` field, no staleness stamp, and no Optional on either model.

    A mutation acknowledgement is not a snapshot, so ``received_at`` has no
    meaning here; and every field of both models came back populated and
    non-nullable in all four captures, so declaring one nullable would hide it
    from the divergence census for nothing (T-31-17, the 31-04 option-b logic).
    """
    hints = _decode.hints_for(cast(Any, model_cls))
    assert "received_at" not in hints
    assert not any(models._is_mapping(h) for h in hints.values())
    assert not any(models._strip_optional(h) is not h for h in hints.values())


def test_add_holidays_result_declares_days_as_the_shipped_calendar_day() -> None:
    """D-01: ``days`` is ``list[CalendarDay]`` — no parallel element model exists."""
    assert _decode.hints_for(AddHolidaysResult)["days"] == list[CalendarDay]
