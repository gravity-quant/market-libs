"""Regression tests para los 4 paths del lifecycle de ``_state.refresh_token`` (async mirror).

Mirror de ``test_refresh_token_lifecycle.py`` para la superficie async (``aio``):

- Path 1: refresh→success path. ``AsyncClient`` con ``state.refresh_token``
  cacheado dispara refresh grant dentro del ``state.token_lock``; server
  responde con nuevo ``access_token`` + ``refresh_token`` rotado; state
  actualizado. Exactly 2 outgoing requests (refresh + endpoint).
- Path 2: refresh→401→password fallback. Refresh revocado → 401 → catch
  interno (``_ensure_token`` line 269-270 ``except IOLAuthError: pass``) →
  password grant inmediato dentro del MISMO lock → success. NO
  ``IOLAuthError`` raised al caller. Exactly 3 outgoing requests.
- Path 3: CR-01 conditional rotation, server NO rota. Refresh succeed pero
  el JSON omite el campo ``refresh_token``. El ``parse_refresh_response``
  retorna ``None`` en la 3ra posición; el shell guard en ``aio.py:250``
  (``if refresh is not None:``) NO se ejecuta → cached preserved.
- Path 4: CR-01 conditional rotation, server SÍ rota. Refresh succeed con
  nuevo ``refresh_token`` field → parser retorna el nuevo valor → guard
  se ejecuta → state actualizado al nuevo valor.

Diferencias mecánicas vs sync:
- ``async def test_async_<name>`` (forensic-distinct vs sync).
- ``state = aio._get_default()._state`` (no ``iol_client.client._get_default()``).
- ``await aio.get_instruments("argentina")`` (no llamada sync).
- ``pytest-asyncio`` mode auto (config en root ``pyproject.toml``); NO
  hace falta el decorator pytest-asyncio (mode auto lo aplica implícito).

El token_lock async lifecycle se ejercita end-to-end con single coroutine — el
flow del refresh DENTRO del lock es el behaviour bajo test. Si una race
condition se "comiera" la rotación CR-01, el path 3 fallaría con
``state.refresh_token == None`` o ``"NEW-TOK"`` en vez de ``"STABLE-REFRESH"``.

El code path bajo test vive en ``packages/iol-client/src/iol_client/aio.py``
líneas 225-273 (``_login_unlocked``, ``_refresh_unlocked``, ``_ensure_token``
con ``token_lock`` double-checked locking).
"""

from __future__ import annotations

import time

from pytest_httpx import HTTPXMock

from iol_client import aio


async def test_async_refresh_token_success_path_rotates(httpx_mock: HTTPXMock) -> None:
    """Path 1 (async): refresh succeed con server rotation → state actualizado.

    Seed: refresh_token cacheado, token vencido.
    Wire: refresh grant 200 con nuevo access_token + nuevo refresh_token →
    endpoint downstream 200. Exactly 2 outgoing requests (refresh + endpoint).
    """
    state = aio._get_default()._state
    state.token = None
    state.token_expires_at = 0.0
    state.refresh_token = "seed-refresh-XYZ"

    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        match_content=b"refresh_token=seed-refresh-XYZ&grant_type=refresh_token",
        json={
            "access_token": "NEW-TOK",
            "refresh_token": "ROTATED-REFRESH",
            "expires_in": 900,
        },
    )
    httpx_mock.add_response(
        url="https://api.test/api/v2/argentina/Titulos/Cotizacion/Instrumentos",
        json={"instrumentos": []},
    )

    await aio.get_instruments("argentina")

    assert state.token == "NEW-TOK"
    assert state.refresh_token == "ROTATED-REFRESH"
    assert state.token_expires_at > time.time()
    assert len(httpx_mock.get_requests()) == 2


async def test_async_refresh_401_falls_back_to_password(httpx_mock: HTTPXMock) -> None:
    """Path 2 (async): refresh revocado → 401 → password fallback dentro del lock.

    Seed: refresh_token revocado.
    Wire: refresh grant 401 → password grant 200 con credenciales frescas →
    endpoint downstream 200. NO ``IOLAuthError`` al caller. Exactly 3 outgoing.

    El ``_ensure_token`` async (aio.py:259-273) maneja el catch dentro del
    ``async with lock:`` → la transición refresh→password sucede atomically;
    otras coroutines que entren al lock después ven el state ya con
    ``token_is_fresh``.
    """
    state = aio._get_default()._state
    state.token = None
    state.token_expires_at = 0.0
    state.refresh_token = "REVOKED-REFRESH"

    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        match_content=b"refresh_token=REVOKED-REFRESH&grant_type=refresh_token",
        status_code=401,
        text="invalid_grant",
    )
    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        match_content=b"username=u&password=p&grant_type=password",
        json={
            "access_token": "NEW-TOK",
            "refresh_token": "FRESH-REFRESH",
            "expires_in": 900,
        },
    )
    httpx_mock.add_response(
        url="https://api.test/api/v2/argentina/Titulos/Cotizacion/Instrumentos",
        json={"instrumentos": []},
    )

    # NO raise — el fallback silencioso vive dentro del lock (D-IOL-09).
    await aio.get_instruments("argentina")

    assert state.token == "NEW-TOK"
    assert state.refresh_token == "FRESH-REFRESH"
    assert len(httpx_mock.get_requests()) == 3


async def test_async_refresh_preserves_token_when_server_omits_refresh_field(
    httpx_mock: HTTPXMock,
) -> None:
    """Path 3 async (CR-01 rama FALSE): server omite refresh_token → cached preserved.

    Mirror del sync Path 3. El shell guard en ``aio.py:250``
    (``if refresh is not None:``) preserva el cached ``state.refresh_token``
    cuando el parser retorna None. Si una race condition o un edit accidental
    bypass el guard, este test falla con ``state.refresh_token == None``.
    """
    state = aio._get_default()._state
    state.token = None
    state.token_expires_at = 0.0
    state.refresh_token = "STABLE-REFRESH"

    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        match_content=b"refresh_token=STABLE-REFRESH&grant_type=refresh_token",
        json={"access_token": "NEW-TOK", "expires_in": 900},
    )
    httpx_mock.add_response(
        url="https://api.test/api/v2/argentina/Titulos/Cotizacion/Instrumentos",
        json={"instrumentos": []},
    )

    await aio.get_instruments("argentina")

    assert state.token == "NEW-TOK"
    assert state.refresh_token == "STABLE-REFRESH"
    assert len(httpx_mock.get_requests()) == 2


async def test_async_refresh_rotates_when_server_provides_new_field(
    httpx_mock: HTTPXMock,
) -> None:
    """Path 4 async (CR-01 rama TRUE): server rota → state.refresh_token actualizado.

    Mirror del sync Path 4. Forma el "opposite branch" del Path 3 async —
    juntos lockean bidireccionalmente el CR-01 conditional rotation guard en
    el ``_refresh_unlocked`` async (aio.py:237-252).
    """
    state = aio._get_default()._state
    state.token = None
    state.token_expires_at = 0.0
    state.refresh_token = "OLD-REFRESH"

    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        match_content=b"refresh_token=OLD-REFRESH&grant_type=refresh_token",
        json={
            "access_token": "NEW-TOK",
            "refresh_token": "NEW-ROTATED-REFRESH",
            "expires_in": 900,
        },
    )
    httpx_mock.add_response(
        url="https://api.test/api/v2/argentina/Titulos/Cotizacion/Instrumentos",
        json={"instrumentos": []},
    )

    await aio.get_instruments("argentina")

    assert state.token == "NEW-TOK"
    assert state.refresh_token == "NEW-ROTATED-REFRESH"
    assert len(httpx_mock.get_requests()) == 2
