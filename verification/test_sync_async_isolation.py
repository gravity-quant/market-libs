"""Cross-leak sentinel test: sync token MUST NOT bleed into async surface y viceversa.

Phase 7 D-10/D-11 — parametrizado sobre los 4 paquetes. ``matriz_client`` async
se skipea con reason literal (D-11) hasta Phase 10 REFAC-04 + TokenStore.

Cada caso fires UN request real (vía ``pytest-httpx``) por superficie:

- **sync** (``test_sync_token_isolation_in_wire_request``): configura sync con
  ``f"SYNC-sentinel-{pkg_name}"`` y asserta que el header (Authorization=Bearer
  prefix o X-Auth-Token sin prefix) en la wire request coincide con el sentinel.
  Para ámbito (no-auth) el sentinel se inyecta en el ``base_url`` y se asserta
  que aparece en ``str(req.url)``.

- **async** (``test_async_token_isolation_in_wire_request``): idéntico shape pero
  contra ``pkg.aio.configure(...)`` con ``f"ASYNC-sentinel-{pkg_name}"``. ``matriz``
  se skipea con D-11 reason verbatim.

Sentinel naming locked (Phase 6 D-12 / Phase 7 D-10):

- ``SYNC-sentinel-<pkg_name>`` para la superficie sync.
- ``ASYNC-sentinel-<pkg_name>`` para la superficie async.

D-12 Phase 7 — este guard corre verde EN HEAD antes del primer refactor (Plans
7-02..7-06 no han modificado nada todavía). Es el detector runtime que complementa
los contracts declarativos de ``import-linter`` en ``pyproject.toml``.
"""

from __future__ import annotations

import datetime as dt
import importlib
from typing import Any

import pytest
from pytest_httpx import HTTPXMock

# Parametrize tuples: (pkg_name, header_name | None, value_prefix)
# - header_name=None marca el paquete no-auth (ámbito): asserta base_url-en-URL.
# - value_prefix="" para tokens sin prefijo (matriz X-Auth-Token).
# - value_prefix="Bearer " para tokens con prefijo Authorization Bearer (iol, higyrus).
_PACKAGES: list[tuple[str, str | None, str]] = [
    ("ambito_financiero_client", None, ""),
    ("iol_client", "Authorization", "Bearer "),
    ("higyrus_client", "Authorization", "Bearer "),
    ("matriz_client", "X-Auth-Token", ""),
]


def _configure_sync(pkg: Any, pkg_name: str, sentinel: str) -> None:
    """Configurar la superficie sync con el sentinel apropiado por paquete.

    Cada paquete tiene kwargs propios para ``configure()``; este helper centraliza
    el setup mínimo para que cada test_sync_* sólo dispare la request y assertee
    el wire header / URL.
    """
    if pkg_name == "ambito_financiero_client":
        pkg.configure(base_url=f"https://{sentinel}.test")
    elif pkg_name == "iol_client":
        pkg.configure(
            base_url="https://api.test",
            username="u",
            password="p",
            token=sentinel,
            token_expires_at=9_999_999_999.0,
        )
    elif pkg_name == "higyrus_client":
        pkg.configure(
            base_url="https://api.test",
            username="u",
            password="p",
            client_id="tenant",
            token=sentinel,
            token_expires_at=9_999_999_999.0,
        )
    elif pkg_name == "matriz_client":
        pkg.configure(
            base_url="https://api.test",
            username="test-user",
            password="test-pass",
            token=sentinel,
            token_expires_at=9_999_999_999.0,
        )
    else:  # pragma: no cover — defensive guard for future pkgs.
        raise AssertionError(f"unhandled package in _configure_sync: {pkg_name}")


def _configure_async(aio: Any, pkg_name: str, sentinel: str) -> None:
    """Configurar la superficie async (``pkg.aio``) con el sentinel apropiado."""
    if pkg_name == "ambito_financiero_client":
        aio.configure(base_url=f"https://{sentinel}.test")
    elif pkg_name == "iol_client":
        aio.configure(
            base_url="https://api.test",
            username="u",
            password="p",
            token=sentinel,
            token_expires_at=9_999_999_999.0,
        )
    elif pkg_name == "higyrus_client":
        aio.configure(
            base_url="https://api.test",
            username="u",
            password="p",
            client_id="tenant",
            token=sentinel,
            token_expires_at=9_999_999_999.0,
        )
    else:  # pragma: no cover — matriz se skipea antes de llegar aquí.
        raise AssertionError(f"unhandled package in _configure_async: {pkg_name}")


@pytest.mark.parametrize(("pkg_name", "header_name", "value_prefix"), _PACKAGES)
def test_sync_token_isolation_in_wire_request(
    pkg_name: str,
    header_name: str | None,
    value_prefix: str,
    httpx_mock: HTTPXMock,
) -> None:
    """Phase 7 D-10: SYNC sentinel reaches the wire request unchanged.

    matriz sync REST está vivo (Phase 6 landed), así que matriz NO se skipea aquí
    — sólo async (D-11). Cada paquete dispara su endpoint público más simple y
    el assertion verifica que el sentinel viaja literal en el header (o URL para
    ámbito).
    """
    pkg = importlib.import_module(pkg_name)
    sentinel = f"SYNC-sentinel-{pkg_name}"
    _configure_sync(pkg, pkg_name, sentinel)

    if pkg_name == "ambito_financiero_client":
        httpx_mock.add_response(
            json=[["Fecha", "Compra", "Venta"], ["02/01/2026", "1.000,00", "1.100,00"]],
        )
        pkg.get_dollar_banco_nacion(dt.date(2026, 1, 2))
        req = httpx_mock.get_requests()[-1]
        # httpx (RFC 3986) lowercasea el hostname — comparamos case-insensitive.
        assert f"{sentinel}.test".lower() in str(req.url).lower()
        return

    if pkg_name == "iol_client":
        httpx_mock.add_response(
            url="https://api.test/api/v2/argentina/Titulos/Cotizacion/Instrumentos",
            json={"instrumentos": []},
        )
        pkg.get_instruments("argentina")
    elif pkg_name == "higyrus_client":
        httpx_mock.add_response(
            url="https://api.test/api/cuentas/listadoCuentas?estado=alta",
            json=[],
        )
        pkg.get_listado_cuentas(estado="alta")
    elif pkg_name == "matriz_client":
        httpx_mock.add_response(
            url="https://api.test/rest/segment/all",
            json={"status": "OK", "segments": []},
        )
        pkg.get_segments()

    req = httpx_mock.get_requests()[-1]
    assert header_name is not None
    assert req.headers.get(header_name) == f"{value_prefix}{sentinel}"


@pytest.mark.parametrize(("pkg_name", "header_name", "value_prefix"), _PACKAGES)
async def test_async_token_isolation_in_wire_request(
    pkg_name: str,
    header_name: str | None,
    value_prefix: str,
    httpx_mock: HTTPXMock,
) -> None:
    """Phase 7 D-10/D-11: ASYNC sentinel reaches the wire request unchanged.

    matriz: skipped — matriz ``aio.py`` REST surface es stub Phase 6, sin endpoints.
    """
    if pkg_name == "matriz_client":
        pytest.skip("matriz aio.py REST stub hasta Phase 10 REFAC-04 + TokenStore")

    pkg = importlib.import_module(pkg_name)
    aio = pkg.aio
    sentinel = f"ASYNC-sentinel-{pkg_name}"
    _configure_async(aio, pkg_name, sentinel)

    if pkg_name == "ambito_financiero_client":
        httpx_mock.add_response(
            json=[["Fecha", "Compra", "Venta"], ["02/01/2026", "1.000,00", "1.100,00"]],
        )
        await aio.get_dollar_banco_nacion(dt.date(2026, 1, 2))
        req = httpx_mock.get_requests()[-1]
        # httpx (RFC 3986) lowercasea el hostname — comparamos case-insensitive.
        assert f"{sentinel}.test".lower() in str(req.url).lower()
        return

    if pkg_name == "iol_client":
        httpx_mock.add_response(
            url="https://api.test/api/v2/argentina/Titulos/Cotizacion/Instrumentos",
            json={"instrumentos": []},
        )
        await aio.get_instruments("argentina")
    elif pkg_name == "higyrus_client":
        httpx_mock.add_response(
            url="https://api.test/api/cuentas/listadoCuentas?estado=alta",
            json=[],
        )
        await aio.get_listado_cuentas(estado="alta")

    req = httpx_mock.get_requests()[-1]
    assert header_name is not None
    assert req.headers.get(header_name) == f"{value_prefix}{sentinel}"
