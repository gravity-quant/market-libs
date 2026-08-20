"""Smoke tests del cliente sincrónico de IOL (API a nivel módulo)."""

from __future__ import annotations

import datetime as dt

import pytest
from pytest_httpx import HTTPXMock

import iol_client
from iol_client import IOLAuthError, IOLRateLimitError
from iol_client.models import Cotizacion


def test_login_obtiene_access_token(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        json={"access_token": "tok-iol", "expires_in": 900},
    )
    assert iol_client.login() == "tok-iol"
    assert iol_client.client._token == "tok-iol"


def test_login_falla_sin_credenciales() -> None:
    iol_client.configure(username="", password="")
    with pytest.raises(IOLAuthError):
        iol_client.login()


def test_request_propaga_auth_error(httpx_mock: HTTPXMock) -> None:
    """Phase 8 D-02: 401 → re-auth-once → 401 still raises IOLAuthError.

    The shell ``_request()`` catches IOLAuthError on the initial response, clears
    the cached token, re-authenticates via ``_ensure_token()`` (login because
    fixture has no refresh_token), then retries the request once. If the retry
    also yields 401, IOLAuthError propagates (Pitfall 1: NO infinite loop).
    """
    httpx_mock.add_response(status_code=401, text="bad")
    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        json={"access_token": "FRESH", "expires_in": 900},
    )
    httpx_mock.add_response(status_code=401, text="bad again")
    with pytest.raises(IOLAuthError):
        iol_client.client._request("GET", "/api/anything")


def test_request_propaga_rate_limit(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(status_code=429, text="too many")
    with pytest.raises(IOLRateLimitError):
        iol_client.client._request("GET", "/api/anything")


def test_get_quote_arma_url_y_params(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://api.test/api/v2/bcba/Titulos/GGAL/Cotizacion?model.mercado=bcba&model.simbolo=GGAL&model.plazo=t2",
        json={"ultimoPrecio": 1234.5, "simbolo": "GGAL"},
    )
    quote = iol_client.get_quote("GGAL")
    assert isinstance(quote, Cotizacion)
    assert quote.ultimoPrecio == 1234.5


def test_get_quote_acepta_mercado_custom(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://api.test/api/v2/nyse/Titulos/KO/Cotizacion?model.mercado=nyse&model.simbolo=KO&model.plazo=t1",
        json={"ultimoPrecio": 60.1},
    )
    quote = iol_client.get_quote("KO", mercado="nyse", plazo="t1")
    assert isinstance(quote, Cotizacion)
    assert quote.ultimoPrecio == 60.1


def test_get_historical_quotes_arma_path(httpx_mock: HTTPXMock) -> None:
    desde = dt.date(2026, 4, 1)
    hasta = dt.date(2026, 4, 5)
    httpx_mock.add_response(
        url="https://api.test/api/v2/bcba/Titulos/GGAL/Cotizacion/seriehistorica/2026-04-01/2026-04-05/sinAjustar",
        json=[{"fechaHora": "2026-04-04T17:00:00", "ultimoPrecio": 999.9}],
    )
    serie = iol_client.get_historical_quotes("GGAL", desde, hasta)
    assert serie[-1]["ultimoPrecio"] == 999.9


def test_get_instruments_devuelve_payload(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://api.test/api/v2/argentina/Titulos/Cotizacion/Instrumentos",
        json={"instrumentos": ["acciones", "cedears"]},
    )
    payload = iol_client.get_instruments()
    assert payload == {"instrumentos": ["acciones", "cedears"]}


def test_get_instruments_by_type_extrae_titulos(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://api.test/api/v2/Cotizaciones/acciones/argentina/Todos",
        json={"titulos": [{"simbolo": "GGAL"}, {"simbolo": "PAMP"}]},
    )
    titulos = iol_client.get_instruments_by_type("acciones")
    assert [t["simbolo"] for t in titulos] == ["GGAL", "PAMP"]


# ------ Verified live (Phase 3) ------


def test_get_quote_url_exacta_con_query_string(httpx_mock: HTTPXMock) -> None:
    """Phase 3: locking URL exacta de get_quote + ultimoPrecio numeric (IOL-02 + IOL-04).

    Plan 30-01: the assertion on the ``simbolo`` key was **removed**, not
    migrated — ``simbolo`` is not among the 20 keys the live corpus
    records for this endpoint (``get-quote.json``, captured 2026-06-06), so it
    is not a field of :class:`Cotizacion` and the mock key now decodes as an
    ``extra`` divergence. The key stays in the mock precisely to exercise that
    tolerance.
    """
    httpx_mock.add_response(
        url="https://api.test/api/v2/bcba/Titulos/GGAL/Cotizacion?model.mercado=bcba&model.simbolo=GGAL&model.plazo=t2",
        json={"ultimoPrecio": 1234.5, "simbolo": "GGAL"},
    )
    quote = iol_client.get_quote("GGAL")
    assert isinstance(quote, Cotizacion)
    assert quote.ultimoPrecio == 1234.5
    assert isinstance(quote.ultimoPrecio, int | float)


def test_get_instruments_by_type_unwraps_titulos(httpx_mock: HTTPXMock) -> None:
    """Phase 3: locking del unwrap data['titulos'] (IOL-04 envelope).

    Si el wire deja de emitir 'titulos', el cliente devuelve [] silenciosamente —
    drift detectado por probe_field_type_map in-vivo (Pitfall 2), no por este test.
    """
    httpx_mock.add_response(
        url="https://api.test/api/v2/Cotizaciones/acciones/argentina/Todos",
        json={"titulos": [{"simbolo": "GGAL"}, {"simbolo": "PAMP"}]},
    )
    titulos = iol_client.get_instruments_by_type("acciones")
    assert isinstance(titulos, list)
    assert len(titulos) == 2
    assert all(isinstance(t, dict) for t in titulos)
    assert [t["simbolo"] for t in titulos] == ["GGAL", "PAMP"]


def test_get_historical_quotes_url_dia_gt_12(httpx_mock: HTTPXMock) -> None:
    """Phase 3: locking del formato YYYY-MM-DD del path histórico (IOL-04).

    Día > 12 descarta ambigüedad DD/MM vs MM/DD estructuralmente.
    """
    desde = dt.date(2026, 4, 15)
    hasta = dt.date(2026, 4, 20)
    httpx_mock.add_response(
        url="https://api.test/api/v2/bcba/Titulos/GGAL/Cotizacion/seriehistorica/2026-04-15/2026-04-20/sinAjustar",
        json=[{"fechaHora": "2026-04-18T17:00:00", "ultimoPrecio": 999.9}],
    )
    serie = iol_client.get_historical_quotes("GGAL", desde, hasta)
    assert isinstance(serie, list)
    assert len(serie) >= 1
    assert serie[-1]["ultimoPrecio"] == 999.9


# ------ Regressions ------


def test_refresh_token_success_path(httpx_mock: HTTPXMock) -> None:
    """Regression: IOL-07 — refresh path actualiza _token sin re-disparar password (finding F-NN).

    El autouse fixture precarga _token; este test lo limpia y setea
    _refresh_token para forzar la rama refresh en _ensure_token. Phase 6
    migration: writes hit el ``_default_client._state`` directamente
    porque el shim PEP 562 es read-only (Pitfall #1).
    """
    state = iol_client.client._get_default()._state
    state.token = None
    state.token_expires_at = 0.0
    state.refresh_token = "refresh-cached"

    # Pitfall 5: match_content bind respuestas a bodies específicos (bytes literal).
    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        match_content=b"refresh_token=refresh-cached&grant_type=refresh_token",
        json={
            "access_token": "tok-after-refresh",
            "refresh_token": "refresh-rotated",
            "expires_in": 900,
        },
    )
    httpx_mock.add_response(
        url="https://api.test/api/v2/argentina/Titulos/Cotizacion/Instrumentos",
        json={"instrumentos": []},
    )

    iol_client.get_instruments("argentina")

    assert iol_client.client._token == "tok-after-refresh"
    assert iol_client.client._refresh_token == "refresh-rotated"


def test_refresh_fails_falls_back_to_password(httpx_mock: HTTPXMock) -> None:
    """Regression: IOL-07 — refresh inválido cae al password grant (finding F-NN)."""
    state = iol_client.client._get_default()._state
    state.token = None
    state.token_expires_at = 0.0
    state.refresh_token = "refresh-stale"

    # 1. Refresh attempt → 401
    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        match_content=b"refresh_token=refresh-stale&grant_type=refresh_token",
        status_code=401,
        text="invalid_grant",
    )
    # 2. Fallback al password grant → success
    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        match_content=b"username=u&password=p&grant_type=password",
        json={
            "access_token": "tok-from-password",
            "refresh_token": "refresh-fresh",
            "expires_in": 900,
        },
    )
    httpx_mock.add_response(
        url="https://api.test/api/v2/argentina/Titulos/Cotizacion/Instrumentos",
        json={"instrumentos": []},
    )

    iol_client.get_instruments("argentina")

    assert iol_client.client._token == "tok-from-password"
    assert iol_client.client._refresh_token == "refresh-fresh"


def test_refresh_and_password_both_fail(httpx_mock: HTTPXMock) -> None:
    """Regression: IOL-07 — ambos refresh y password fallan → IOLAuthError (finding F-NN)."""
    state = iol_client.client._get_default()._state
    state.token = None
    state.token_expires_at = 0.0
    state.refresh_token = "refresh-stale"

    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        match_content=b"refresh_token=refresh-stale&grant_type=refresh_token",
        status_code=401,
        text="refresh_revoked",
    )
    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        match_content=b"username=u&password=p&grant_type=password",
        status_code=401,
        text="bad_creds",
    )

    with pytest.raises(IOLAuthError) as excinfo:
        iol_client.get_instruments("argentina")

    assert excinfo.value.status_code == 401


def test_login_captures_refresh_token(httpx_mock: HTTPXMock) -> None:
    """Regression: IOL-07 — login() captura refresh_token del payload (finding F-NN)."""
    state = iol_client.client._get_default()._state
    state.token = None
    state.refresh_token = None

    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        json={
            "access_token": "tok-x",
            "refresh_token": "refresh-captured",
            "expires_in": 900,
        },
    )

    iol_client.login()

    assert iol_client.client._token == "tok-x"
    assert iol_client.client._refresh_token == "refresh-captured"


def test_login_preserves_cached_refresh_token_when_server_omits(httpx_mock: HTTPXMock) -> None:
    """Regression CR-01: login() preserva _refresh_token cacheado si el server lo omite.

    Escenario: el cliente tiene ``_refresh_token = "refresh-original"`` cacheado de
    un login previo; ahora se llama ``login()`` otra vez (e.g., fallback tras
    refresh inválido) pero el server NO incluye ``refresh_token`` en el payload
    del password grant. El comportamiento ANTES del fix era resetear a ``None``,
    contradiciendo la política condicional de ``_refresh()`` (Pitfall 3). El fix
    alinea ambas funciones: si el payload omite, MANTENER el cached.
    """
    state = iol_client.client._get_default()._state
    state.token = None
    state.token_expires_at = 0.0
    state.refresh_token = "refresh-original"

    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        # Server NO incluye refresh_token en el payload.
        json={"access_token": "tok-new", "expires_in": 900},
    )

    iol_client.login()

    assert iol_client.client._token == "tok-new"
    # Cached refresh_token preservado tras el login (CR-01 fix).
    assert iol_client.client._refresh_token == "refresh-original"


def test_configure_resets_refresh_token_but_direct_password_mutation_preserves_it() -> None:
    """Regression CR-03: locking del invariante que motiva CR-03 fix.

    ``iol_client.configure(password=...)`` resetea ``_refresh_token = None`` —
    comportamiento intencional para rotación de credenciales pero peligroso si
    se usa en probe_auth_401 finally restore (leakaría el cached fuera del
    set ``secrets`` del SUMMARY). El fix CR-03 evita ``configure()`` y muta
    ``_password`` directamente, preservando ``_refresh_token``.

    Este test verifica AMBOS comportamientos para lockear la invariante. Phase 6
    migration: en lugar de un direct-write a la atribute legacy del módulo (que
    ahora hit el módulo dict por el shim PEP 562 read-only), se muta
    ``_get_default()._state.password`` directamente — preserva la semántica de
    "rotar password bypassing configure() preserves refresh_token".
    """
    state = iol_client.client._get_default()._state

    # Setup: precargar un refresh_token cacheado.
    state.refresh_token = "refresh-cached"

    # Branch 1: configure() resetea (regresión sería si NO lo reseteara).
    iol_client.configure(password="dummy")
    assert iol_client.client._refresh_token is None

    # Branch 2: mutación directa de _password preserva refresh_token.
    state.refresh_token = "refresh-cached-2"
    state.password = "another"
    assert iol_client.client._refresh_token == "refresh-cached-2"


# ---- WR-02 Phase 8 review fix: body-consume-then-raise on 401 carve-outs ----


def test_401_carve_out_body_consumed_before_raise(httpx_mock: HTTPXMock) -> None:
    """WR-02 regression: 401 re-auth flow consumes body before raising IOLAuthError.

    The shell ``_request()`` catches IOLAuthError on the initial response, runs
    the re-auth-once flow, retries, and on the second 401 raises IOLAuthError.
    WR-02 hardens both raise paths with explicit ``resp.read()`` so the
    body-consume-then-raise contract (Phase 7 D-06) is preserved on the
    carve-out path (where ``_raise_for_response`` already buffers the body via
    ``resp.text``, but the explicit read documents the contract and guards
    against future httpx auto-consume behavior changes or http2=True streaming).

    Mock: 401 (with non-empty body) → login 200 → 401 (with non-empty body).
    Assert IOLAuthError raised + exactly 3 wire requests.
    """
    iol_client.configure(
        base_url="https://api.test",
        username="u",
        password="p",
        token="STALE",
        token_expires_at=9_999_999_999.0,
    )
    httpx_mock.add_response(
        url="https://api.test/api/anything",
        status_code=401,
        content=b'{"error":"unauthorized"}',
    )
    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        json={"access_token": "FRESH", "expires_in": 900},
    )
    httpx_mock.add_response(
        url="https://api.test/api/anything",
        status_code=401,
        content=b'{"error":"still unauthorized"}',
    )
    with pytest.raises(IOLAuthError):
        iol_client.client._request("GET", "/api/anything")
    # 3 wire requests = initial 401 + login 200 + retry 401 (D-02 exactly once).
    assert len(httpx_mock.get_requests()) == 3


# ----------------------------------------------------------------------
# Phase 13 ERG-01 — with_options view shape tests (D-V1..D-V4 + iol-specific
# 401-re-auth-with-view test). Plan 13-05.
# ----------------------------------------------------------------------


def test_with_options_close_is_noop(httpx_mock: HTTPXMock) -> None:
    """Phase 13 D-V1: view.close() MUST NOT close parent's http_client.

    Anti-Pitfall 13: a view shares ``_state.http_client`` with the parent;
    closing the view would tear down the parent's TCP pool. The lifecycle
    no-op guard (``if getattr(self, "_is_view", False): return``) prevents
    this. Also asserts the parent's cached OAuth token survives (no
    re-auth) — iol-specific because iol caches OAuth access tokens.
    """
    httpx_mock.add_response(
        url="https://api.test/api/v2/bcba/Titulos/GGAL/Cotizacion?model.mercado=bcba&model.simbolo=GGAL&model.plazo=t2",
        json={"ultimoPrecio": 100.0},
    )
    client = iol_client.Client(
        base_url="https://api.test",
        username="u",
        password="p",
        token="test-token",
        token_expires_at=9_999_999_999.0,
    )
    # Force lazy init of http_client via an actual call.
    client.get_quote("GGAL")
    parent_http = client._state.http_client
    assert parent_http is not None
    assert client._state.token == "test-token"

    view = client.with_options(max_retries=5)
    view.close()  # MUST be no-op
    assert client._state.http_client is parent_http
    assert client._state.http_client is not None  # parent's pool still open
    assert client._state.token == "test-token"  # no re-auth triggered


def test_with_options_exit_is_noop(httpx_mock: HTTPXMock) -> None:
    """``with view:`` block exits without tearing down parent's http_client."""
    httpx_mock.add_response(
        url="https://api.test/api/v2/bcba/Titulos/GGAL/Cotizacion?model.mercado=bcba&model.simbolo=GGAL&model.plazo=t2",
        json={"ultimoPrecio": 100.0},
    )
    client = iol_client.Client(
        base_url="https://api.test",
        username="u",
        password="p",
        token="test-token",
        token_expires_at=9_999_999_999.0,
    )
    client.get_quote("GGAL")
    parent_http = client._state.http_client
    assert parent_http is not None

    view = client.with_options(max_retries=5)
    with view:
        pass  # exit triggers __exit__ → close() → no-op guard

    assert client._state.http_client is parent_http
    assert client._state.http_client is not None
    assert client._state.token == "test-token"


def test_with_options_chaining_inner_wins_local() -> None:
    """D-V2: ``c.with_options(5).with_options(10)._max_retries == 10``."""
    client = iol_client.Client(
        base_url="https://api.test",
        username="u",
        password="p",
        token="test-token",
        token_expires_at=9_999_999_999.0,
    )
    view = client.with_options(max_retries=5).with_options(max_retries=10)
    assert view._max_retries == 10
    assert client._max_retries == 2
    assert view._state is client._state


def test_with_options_repr_shows_view_prefix() -> None:
    """View's ``__repr__`` is prefixed with ``"view of "``. D-18 redaction preserved (password, token, refresh_token)."""
    client = iol_client.Client(
        base_url="https://api.test",
        username="u",
        password="SECRET-PASSWORD-DO-NOT-LEAK",
        token="SECRET-TOKEN-DO-NOT-LEAK",
        token_expires_at=9_999_999_999.0,
    )
    client._state.refresh_token = "SECRET-REFRESH-DO-NOT-LEAK"
    view = client.with_options(max_retries=5)
    assert repr(view).startswith("view of IOLClient(")
    assert not repr(client).startswith("view of ")
    # D-18 + T-06-05 redaction must still apply on views (password, token, refresh_token).
    assert "SECRET-PASSWORD-DO-NOT-LEAK" not in repr(view)
    assert "SECRET-TOKEN-DO-NOT-LEAK" not in repr(view)
    assert "SECRET-REFRESH-DO-NOT-LEAK" not in repr(view)


def test_with_options_invalid_max_retries_raises_value_error() -> None:
    """WR-06 carry-forward: invalid ``max_retries`` rejected BEFORE view construction."""
    client = iol_client.Client(
        base_url="https://api.test",
        username="u",
        password="p",
        token="test-token",
        token_expires_at=9_999_999_999.0,
    )
    with pytest.raises(ValueError, match="max_retries"):
        client.with_options(max_retries=-1)
    with pytest.raises(ValueError, match="max_retries"):
        client.with_options(max_retries=True)
    with pytest.raises(ValueError, match="max_retries"):
        client.with_options(max_retries=1.5)  # type: ignore[arg-type]


def test_with_options_view_401_triggers_reauth_via_shared_refresh_token(
    httpx_mock: HTTPXMock,
) -> None:
    """Phase 13 iol-specific: view's 401 path uses parent's shared refresh_token.

    The view shares ``_state`` with the parent (anti-Pitfall 13 extended to
    OAuth refresh flow). On a 401 from the view's request:

    1. ``_request`` clears the SHARED ``_state.token``.
    2. ``_ensure_token()`` reads the SHARED ``_state.refresh_token`` and
       triggers ``_refresh()`` (POST /token with grant_type=refresh_token).
    3. The new ``access_token`` (and rotated ``refresh_token``) are written
       back to the SHARED ``_state`` — visible to the parent.
    4. The view retries the original request ONCE with the new Bearer.

    Mock sequence: stale-GET (401) → /token refresh (200) → fresh-GET (200).

    iol Client kwargs are ``username``/``password`` (NOT ``client_id``/
    ``client_secret``); ``refresh_token`` is a ``_state`` field set
    post-construction (NOT a constructor kwarg) — verified at
    ``packages/iol-client/src/iol_client/client.py:127-137``.
    """
    client = iol_client.Client(
        base_url="https://api.test",
        username="u",
        password="p",
        token="stale-token",
        token_expires_at=9_999_999_999.0,
    )
    # refresh_token is a _state field, NOT a Client constructor kwarg.
    client._state.refresh_token = "fresh-refresh"

    view = client.with_options(max_retries=5)

    # 1. GET → 401 (stale token).
    httpx_mock.add_response(
        url="https://api.test/api/v2/bcba/Titulos/GGAL/Cotizacion?model.mercado=bcba&model.simbolo=GGAL&model.plazo=t2",
        status_code=401,
        text="unauthorized",
    )
    # 2. POST /token refresh → 200 with new tokens.
    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        match_content=b"refresh_token=fresh-refresh&grant_type=refresh_token",
        json={
            "access_token": "new-token",
            "refresh_token": "new-refresh",
            "expires_in": 900,
        },
    )
    # 3. GET → 200 with quote.
    httpx_mock.add_response(
        url="https://api.test/api/v2/bcba/Titulos/GGAL/Cotizacion?model.mercado=bcba&model.simbolo=GGAL&model.plazo=t2",
        json={"ultimoPrecio": 123.45},
    )

    quote = view.get_quote("GGAL")

    # The returned quote is the success body, now decoded as a model.
    assert isinstance(quote, Cotizacion)
    assert quote.ultimoPrecio == 123.45
    # Parent's state updated by view's re-auth path — SHARED _state semantics.
    assert client._state.token == "new-token"
    assert client._state.refresh_token == "new-refresh"
    # Shared throughout: view._state is the SAME object as client._state.
    assert view._state is client._state
    # 3 wire requests: initial 401 + /token refresh + retry GET.
    assert len(httpx_mock.get_requests()) == 3
