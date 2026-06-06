"""Smoke tests del cliente asincrónico de IOL (submódulo aio)."""

from __future__ import annotations

import datetime as dt

import pytest
from pytest_httpx import HTTPXMock

from iol_client import IOLAuthError, aio


async def test_async_login_obtiene_access_token(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        json={"access_token": "tok-iol", "expires_in": 900},
    )
    assert await aio.login() == "tok-iol"


async def test_async_request_propaga_auth_error(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(status_code=401, text="bad")
    with pytest.raises(IOLAuthError):
        await aio._request("GET", "/api/anything")


async def test_async_get_quote(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://api.test/api/v2/bcba/Titulos/GGAL/Cotizacion?model.mercado=bcba&model.simbolo=GGAL&model.plazo=t2",
        json={"ultimoPrecio": 1234.5},
    )
    quote = await aio.get_quote("GGAL")
    assert quote["ultimoPrecio"] == 1234.5


async def test_async_get_historical_quotes(httpx_mock: HTTPXMock) -> None:
    desde = dt.date(2026, 4, 1)
    hasta = dt.date(2026, 4, 5)
    httpx_mock.add_response(
        url="https://api.test/api/v2/bcba/Titulos/GGAL/Cotizacion/seriehistorica/2026-04-01/2026-04-05/sinAjustar",
        json=[{"ultimoPrecio": 999.9}],
    )
    serie = await aio.get_historical_quotes("GGAL", desde, hasta)
    assert serie[-1]["ultimoPrecio"] == 999.9


async def test_async_get_instruments_by_type(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://api.test/api/v2/Cotizaciones/cedears/argentina/Todos",
        json={"titulos": [{"simbolo": "AAPL"}]},
    )
    titulos = await aio.get_instruments_by_type("cedears")
    assert titulos[0]["simbolo"] == "AAPL"


# ------ Regressions ------


async def test_async_refresh_token_success_path(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression: IOL-07 — refresh path async actualiza _token (finding F-NN, mirror del sync).

    El autouse fixture precarga _token; el monkeypatch lo limpia y setea
    _refresh_token para forzar la rama refresh en _ensure_token dentro del _token_lock.
    """
    monkeypatch.setattr(aio, "_token", None, raising=False)
    monkeypatch.setattr(aio, "_token_expires_at", 0.0, raising=False)
    monkeypatch.setattr(aio, "_refresh_token", "refresh-cached", raising=False)

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

    await aio.get_instruments("argentina")

    assert aio._token == "tok-after-refresh"
    assert aio._refresh_token == "refresh-rotated"


async def test_async_refresh_fails_falls_back_to_password(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression: IOL-07 — refresh inválido cae al password grant async (finding F-NN, mirror)."""
    monkeypatch.setattr(aio, "_token", None, raising=False)
    monkeypatch.setattr(aio, "_token_expires_at", 0.0, raising=False)
    monkeypatch.setattr(aio, "_refresh_token", "refresh-stale", raising=False)

    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        match_content=b"refresh_token=refresh-stale&grant_type=refresh_token",
        status_code=401,
        text="invalid_grant",
    )
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

    await aio.get_instruments("argentina")

    assert aio._token == "tok-from-password"
    assert aio._refresh_token == "refresh-fresh"


async def test_async_refresh_and_password_both_fail(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression: IOL-07 — ambos fallan async → IOLAuthError (finding F-NN, mirror)."""
    monkeypatch.setattr(aio, "_token", None, raising=False)
    monkeypatch.setattr(aio, "_token_expires_at", 0.0, raising=False)
    monkeypatch.setattr(aio, "_refresh_token", "refresh-stale", raising=False)

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
        await aio.get_instruments("argentina")

    assert excinfo.value.status_code == 401


async def test_async_login_captures_refresh_token(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression: IOL-07 — async login() captura refresh_token (finding F-NN, mirror)."""
    monkeypatch.setattr(aio, "_token", None, raising=False)
    monkeypatch.setattr(aio, "_refresh_token", None, raising=False)

    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        json={
            "access_token": "tok-x",
            "refresh_token": "refresh-captured",
            "expires_in": 900,
        },
    )

    await aio.login()

    assert aio._token == "tok-x"
    assert aio._refresh_token == "refresh-captured"
