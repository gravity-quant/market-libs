"""Regression tests para los 4 paths del lifecycle de ``_state.refresh_token`` (sync).

BUG-03 (Phase 9, D-06) — lockea el contrato observable de la rotación
condicional del ``refresh_token`` cacheado en ``Client._state``:

- Path 1: refresh→success path. El cliente con ``state.refresh_token`` cacheado
  hace ``POST /token`` con ``grant_type=refresh_token``; el server responde con
  un nuevo ``access_token`` + ``refresh_token`` rotado; ambos quedan
  actualizados en el state. Exactly 2 outgoing requests (refresh + endpoint).
- Path 2: refresh→401→password fallback. El ``refresh_token`` cacheado está
  revocado → 401 → catch silencioso → password grant inmediato → 200 con
  credenciales frescas. NO se propaga ``IOLAuthError`` al caller. Exactly 3
  outgoing requests (refresh + password + endpoint).
- Path 3: CR-01 conditional rotation, server NO rota. El refresh succeed pero
  la respuesta omite el campo ``refresh_token``. El ``parse_login_response``
  retorna ``None`` en la 3ra posición y el shell guard ``if refresh is not
  None:`` en ``client.py`` NO se ejecuta → el cached ``refresh_token`` queda
  intacto (NOT cleared, NOT replaced with None).
- Path 4: CR-01 conditional rotation, server SÍ rota. El refresh succeed con
  un nuevo ``refresh_token`` field → parser retorna el nuevo valor → shell
  guard se ejecuta → state se actualiza al nuevo refresh_token.

Phase 6 D-IOL-10 + Phase 7 D-04 alias ya implementan estos paths; este file
lockea el contrato para detectar regresiones futuras del CR-01 conditional
rotation guard, del refresh→password fallback, y del double-checked locking.

El code path bajo test vive en ``packages/iol-client/src/iol_client/client.py``
líneas 251-289 (``login``, ``_refresh``, ``_ensure_token``).
"""

from __future__ import annotations

import time

from pytest_httpx import HTTPXMock

import iol_client


def test_refresh_token_success_path_rotates(httpx_mock: HTTPXMock) -> None:
    """Path 1: refresh succeed con server rotation → state.token + state.refresh_token actualizados.

    Seed: refresh_token cacheado, token vencido (``token_expires_at=0.0``).
    Wire: refresh grant 200 con nuevo access_token + nuevo refresh_token →
    endpoint downstream 200. Exactly 2 outgoing requests (refresh + endpoint —
    NO password fallback).
    """
    state = iol_client.client._get_default()._state
    state.token = None
    state.token_expires_at = 0.0
    state.refresh_token = "seed-refresh-XYZ"

    # Refresh grant — match_content distingue del password grant por body.
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

    iol_client.get_instruments("argentina")

    assert state.token == "NEW-TOK"
    assert state.refresh_token == "ROTATED-REFRESH"
    assert state.token_expires_at > time.time()
    # Exactly 2 outgoing: refresh + endpoint. NO password fallback.
    assert len(httpx_mock.get_requests()) == 2


def test_refresh_401_falls_back_to_password(httpx_mock: HTTPXMock) -> None:
    """Path 2: refresh_token revocado → 401 → password grant fallback → success.

    Seed: refresh_token cacheado pero revocado en el server.
    Wire: refresh grant 401 → password grant 200 con credenciales frescas →
    endpoint downstream 200. NO ``IOLAuthError`` raised al caller (catch
    silencioso en ``_ensure_token``). Exactly 3 outgoing requests (refresh +
    password + endpoint).

    CRÍTICO: ``match_content`` literal distingue los 2 mocks sobre el mismo
    URL ``/token`` — sin ``match_content`` los mocks colisionan en orden FIFO
    (Pitfall 3 de RESEARCH.md).
    """
    state = iol_client.client._get_default()._state
    state.token = None
    state.token_expires_at = 0.0
    state.refresh_token = "REVOKED-REFRESH"

    # 1) Refresh grant → 401 (revocado).
    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        match_content=b"refresh_token=REVOKED-REFRESH&grant_type=refresh_token",
        status_code=401,
        text="invalid_grant",
    )
    # 2) Password fallback → 200 con credenciales frescas.
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
    # 3) Endpoint downstream.
    httpx_mock.add_response(
        url="https://api.test/api/v2/argentina/Titulos/Cotizacion/Instrumentos",
        json={"instrumentos": []},
    )

    # NO raise — el fallback es silencioso (Phase 6 D-IOL-10).
    iol_client.get_instruments("argentina")

    assert state.token == "NEW-TOK"
    assert state.refresh_token == "FRESH-REFRESH"
    # Exactly 3 outgoing: refresh + password + endpoint.
    assert len(httpx_mock.get_requests()) == 3


def test_refresh_preserves_token_when_server_omits_refresh_field(
    httpx_mock: HTTPXMock,
) -> None:
    """Path 3 (CR-01 rama FALSE): server omite ``refresh_token`` → cached preserved.

    Seed: refresh_token cacheado.
    Wire: refresh grant 200 SIN campo ``refresh_token`` en el JSON → endpoint
    downstream 200. El parser ``parse_login_response`` retorna ``None`` en
    la 3ra posición; el shell guard ``if refresh is not None:`` (client.py:273)
    NO se ejecuta → ``state.refresh_token`` queda intacto al seed.

    Si alguien edita el guard accidentalmente (e.g., removing the conditional y
    siempre asignando ``state.refresh_token = refresh``), este test falla con
    ``state.refresh_token is None`` en vez de ``"STABLE-REFRESH"``.
    """
    state = iol_client.client._get_default()._state
    state.token = None
    state.token_expires_at = 0.0
    state.refresh_token = "STABLE-REFRESH"

    # Refresh grant 200 SIN campo refresh_token (key ausente — NO null, NO "").
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

    iol_client.get_instruments("argentina")

    assert state.token == "NEW-TOK"
    # CR-01: cached refresh_token preservado (NOT cleared a None, NOT rotated).
    assert state.refresh_token == "STABLE-REFRESH"
    # Exactly 2 outgoing: refresh + endpoint.
    assert len(httpx_mock.get_requests()) == 2


def test_refresh_rotates_when_server_provides_new_field(
    httpx_mock: HTTPXMock,
) -> None:
    """Path 4 (CR-01 rama TRUE): server rota → state.refresh_token actualizado.

    Seed: refresh_token cacheado.
    Wire: refresh grant 200 CON nuevo ``refresh_token`` field → endpoint
    downstream 200. El parser retorna el nuevo valor; el shell guard se ejecuta
    y ``state.refresh_token`` queda asignado al nuevo valor rotado.

    Forma el "opposite branch" del Path 3 — juntos los dos paths lockean
    bidireccionalmente el CR-01 conditional rotation guard.
    """
    state = iol_client.client._get_default()._state
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

    iol_client.get_instruments("argentina")

    assert state.token == "NEW-TOK"
    # CR-01: server provee refresh_token → guard se ejecuta → state rotated.
    assert state.refresh_token == "NEW-ROTATED-REFRESH"
    # Exactly 2 outgoing: refresh + endpoint.
    assert len(httpx_mock.get_requests()) == 2


# Pitfall 6 note: si tests pasan en isolation pero fallan en suite, podría
# ser contaminación cross-test de ``state.refresh_token`` (autouse fixture en
# conftest.py:25-38 cierra el http_client pero NO resetea explícitamente el
# state.refresh_token; sin embargo, cada test acá lo setea explícitamente al
# inicio, así que el riesgo está mitigado). NO modificar conftest.py en este
# plan (modificación cross-cutting) — defer si emerge.
