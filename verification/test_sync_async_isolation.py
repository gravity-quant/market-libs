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
    elif pkg_name == "matriz_client":
        # Phase 10 Plan 10-04 (REFAC-04 + LIVE-02): matriz aio.py REST surface +
        # TokenStore landed (Plan 10-02 + 10-03); cross-leak sentinel now extended.
        aio.configure(
            base_url="https://api.test",
            username="test-user",
            password="test-pass",
            token=sentinel,
            token_expires_at=9_999_999_999.0,
        )
    else:  # pragma: no cover — defensive guard for future pkgs.
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

    Phase 10 Plan 10-04 (REFAC-04 + LIVE-02): matriz ``aio.py`` REST surface +
    TokenStore landed (Plan 10-02 + 10-03); matriz branch is now active.
    """
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
    elif pkg_name == "matriz_client":
        httpx_mock.add_response(
            url="https://api.test/rest/segment/all",
            json={"status": "OK", "segments": []},
        )
        await aio.get_segments()

    req = httpx_mock.get_requests()[-1]
    assert header_name is not None
    assert req.headers.get(header_name) == f"{value_prefix}{sentinel}"


async def test_matriz_sync_async_state_and_token_store_instance_isolation(
    httpx_mock: HTTPXMock,
) -> None:
    """Phase 10 Plan 10-04 (REFAC-04) — matriz cross-leak sentinel extension.

    The cross-leak sentinel above proves SENTINEL VALUES don't bleed across the
    sync↔async wire path. This guard EXTENDS that contract to prove the
    underlying STATE OBJECTS (``_ClientState`` + ``_ClientState.token_store``)
    are distinct INSTANCES per surface — i.e., a refresh on the sync side does
    NOT mutate the async side's ``token_store`` and vice versa. This is the
    matriz-specific guarantee that Plan 10-03 wiring enables (sync ``Client``,
    ``AsyncClient`` and ``ws_client`` daemon thread each have their own
    ``_ClientState.token_store`` lazy instance per state).

    The assertion targets the matriz-specific REFAC-04 invariant:

    - ``matriz_client.client._get_default()._state`` is NOT the same instance as
      ``matriz_client.aio._get_default()._state``.
    - When both surfaces' ``token_store`` slots are populated by Plan 10-03's
      ``build_token_store`` factory, the two instances are DISTINCT — not aliased.
      We populate them explicitly (the lazy fast-path skips ``build_token_store``
      when ``configure(token=..., token_expires_at=...)`` is fresh, so we trigger
      the wiring path the way Plan 10-03 intended).
    - The configured sentinel TOKEN value is preserved on each surface (no
      mid-test mutation by the other surface — re-asserts the cross-leak
      invariant on the state objects themselves, not just the wire headers).
    """
    import matriz_client
    from matriz_client import aio as matriz_aio
    from matriz_client._token_store import build_token_store

    sync_sentinel = "SYNC-MATRIZ-sentinel"
    async_sentinel = "ASYNC-MATRIZ-sentinel"

    matriz_client.configure(
        base_url="https://api.test",
        username="test-user",
        password="test-pass",
        token=sync_sentinel,
        token_expires_at=9_999_999_999.0,
    )
    matriz_aio.configure(
        base_url="https://api.test",
        username="test-user",
        password="test-pass",
        token=async_sentinel,
        token_expires_at=9_999_999_999.0,
    )

    # Exercise the live wire path so the sentinel hits a real outgoing request
    # on each surface — re-validates the value-level cross-leak invariant.
    httpx_mock.add_response(
        url="https://api.test/rest/segment/all",
        json={"status": "OK", "segments": []},
    )
    httpx_mock.add_response(
        url="https://api.test/rest/segment/all",
        json={"status": "OK", "segments": []},
    )
    matriz_client.get_segments()
    await matriz_aio.get_segments()

    sync_state = matriz_client.client._get_default()._state
    async_state = matriz_aio._get_default()._state

    # _state instance isolation (Plan 10-03 contract).
    assert sync_state is not async_state, (
        "sync and async matriz default clients MUST own distinct _ClientState "
        "instances (Plan 10-03 cross-leak isolation)"
    )

    # Configured sentinel tokens preserved on each surface — no cross-leak.
    assert sync_state.token == sync_sentinel
    assert async_state.token == async_sentinel
    assert sync_state.token != async_state.token

    # token_store instance isolation (Plan 10-04 matriz-specific extension).
    # Plan 10-03 wired ``token_store`` as a per-``_state`` lazy slot built by
    # ``build_token_store``. ``_ensure_token`` short-circuits via
    # ``token_is_fresh`` when ``configure(token=..., token_expires_at=...)``
    # is set, so the lazy path is bypassed for pre-seeded tokens; populate
    # the slot here the way the refresh path would (Plan 10-03 factory),
    # then prove the two surfaces produce DISTINCT ``TokenStore`` instances.
    sync_state.token_store = build_token_store(sync_state, max_retries=2)
    async_state.token_store = build_token_store(async_state, max_retries=2)
    assert sync_state.token_store is not None
    assert async_state.token_store is not None
    assert sync_state.token_store is not async_state.token_store, (
        "sync and async matriz default clients MUST own distinct token_store "
        "instances — Plan 10-03 wiring lives on _state.token_store, so distinct "
        "_state instances MUST yield distinct token_store instances "
        "(matriz REFAC-04 cross-leak extension)"
    )
