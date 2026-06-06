"""Smoke tests del cliente sincrónico de IOL (API a nivel módulo)."""

from __future__ import annotations

import datetime as dt

import pytest
from pytest_httpx import HTTPXMock

import iol_client
from iol_client import IOLAuthError, IOLRateLimitError


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
    httpx_mock.add_response(status_code=401, text="bad")
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
    assert quote["ultimoPrecio"] == 1234.5


def test_get_quote_acepta_mercado_custom(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://api.test/api/v2/nyse/Titulos/KO/Cotizacion?model.mercado=nyse&model.simbolo=KO&model.plazo=t1",
        json={"ultimoPrecio": 60.1},
    )
    quote = iol_client.get_quote("KO", mercado="nyse", plazo="t1")
    assert quote["ultimoPrecio"] == 60.1


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
    """Phase 3: locking URL exacta de get_quote + ultimoPrecio numeric (IOL-02 + IOL-04)."""
    httpx_mock.add_response(
        url="https://api.test/api/v2/bcba/Titulos/GGAL/Cotizacion?model.mercado=bcba&model.simbolo=GGAL&model.plazo=t2",
        json={"ultimoPrecio": 1234.5, "simbolo": "GGAL"},
    )
    quote = iol_client.get_quote("GGAL")
    assert quote["ultimoPrecio"] == 1234.5
    assert isinstance(quote["ultimoPrecio"], int | float)
    assert quote["simbolo"] == "GGAL"


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


def test_refresh_token_success_path(httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch) -> None:
    """Regression: IOL-07 — refresh path actualiza _token sin re-disparar password (finding F-NN).

    El autouse fixture precarga _token; el monkeypatch lo limpia y setea
    _refresh_token para forzar la rama refresh en _ensure_token.
    """
    monkeypatch.setattr(iol_client.client, "_token", None, raising=False)
    monkeypatch.setattr(iol_client.client, "_token_expires_at", 0.0, raising=False)
    monkeypatch.setattr(iol_client.client, "_refresh_token", "refresh-cached", raising=False)

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


def test_refresh_fails_falls_back_to_password(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression: IOL-07 — refresh inválido cae al password grant (finding F-NN)."""
    monkeypatch.setattr(iol_client.client, "_token", None, raising=False)
    monkeypatch.setattr(iol_client.client, "_token_expires_at", 0.0, raising=False)
    monkeypatch.setattr(iol_client.client, "_refresh_token", "refresh-stale", raising=False)

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


def test_refresh_and_password_both_fail(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression: IOL-07 — ambos refresh y password fallan → IOLAuthError (finding F-NN)."""
    monkeypatch.setattr(iol_client.client, "_token", None, raising=False)
    monkeypatch.setattr(iol_client.client, "_token_expires_at", 0.0, raising=False)
    monkeypatch.setattr(iol_client.client, "_refresh_token", "refresh-stale", raising=False)

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


def test_login_captures_refresh_token(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression: IOL-07 — login() captura refresh_token del payload (finding F-NN)."""
    monkeypatch.setattr(iol_client.client, "_token", None, raising=False)
    monkeypatch.setattr(iol_client.client, "_refresh_token", None, raising=False)

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


def test_login_preserves_cached_refresh_token_when_server_omits(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression CR-01: login() preserva _refresh_token cacheado si el server lo omite.

    Escenario: el cliente tiene ``_refresh_token = "refresh-original"`` cacheado de
    un login previo; ahora se llama ``login()`` otra vez (e.g., fallback tras
    refresh inválido) pero el server NO incluye ``refresh_token`` en el payload
    del password grant. El comportamiento ANTES del fix era resetear a ``None``,
    contradiciendo la política condicional de ``_refresh()`` (Pitfall 3). El fix
    alinea ambas funciones: si el payload omite, MANTENER el cached.
    """
    monkeypatch.setattr(iol_client.client, "_token", None, raising=False)
    monkeypatch.setattr(iol_client.client, "_token_expires_at", 0.0, raising=False)
    monkeypatch.setattr(iol_client.client, "_refresh_token", "refresh-original", raising=False)

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
