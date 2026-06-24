"""CR-07 -- main_higyrus.py ``_capture_*_query_string`` thread-safety regression.

Invariante: invocaciones concurrentes cross-thread / cross-event-loop de
``_capture_sync_query_string`` y ``_capture_async_query_string`` NO deben
corromper el estado compartido ``httpx.Client.event_hooks`` /
``httpx.AsyncClient.event_hooks``.

Fix path (Phase 11 CR-07): los helpers serializan la mutacion in-place del
``event_hooks`` con ``threading.Lock`` (sync) y ``asyncio.Lock`` (async).
La alternativa "per-request hook injection" via ``http_client=`` kwarg
requiere reconstruir transport+auth interno del default Client y se descarto
por radio de impacto excesivo (per ``11-PATTERNS.md:277-285``).
"""

from __future__ import annotations

import asyncio
import datetime as dt
import re
from concurrent.futures import ThreadPoolExecutor

import main_higyrus
import pytest
from pytest_httpx import HTTPXMock

from higyrus_client import AsyncClient, Client

# Phase 15 (REFAC-05): the capture helpers now take a threaded ``Client`` /
# ``AsyncClient`` instance (single-Client migration) instead of reaching the
# module default via ``_get_default()``. These tests construct real instances
# seeded with the same dummy token/base_url the conftest applies to the module
# default, then assert the no-corruption invariant on THAT instance's
# materialized ``httpx`` client.
_BASE_URL = "https://api.test"
_NEVER_EXPIRES = 9_999_999_999.0


def _make_sync_client() -> Client:
    return Client(
        base_url=_BASE_URL,
        username="u",
        password="p",
        client_id="tenant",
        token="test-token",
        token_expires_at=_NEVER_EXPIRES,
    )


def _make_async_client() -> AsyncClient:
    return AsyncClient(
        base_url=_BASE_URL,
        username="u",
        password="p",
        client_id="tenant",
        token="test-token",
        token_expires_at=_NEVER_EXPIRES,
    )


@pytest.fixture
def movimientos_mock(httpx_mock: HTTPXMock) -> HTTPXMock:
    """Pre-mockea movimientos con respuesta reusable. El conftest precarga el
    token via ``configure(token=...)`` asi que ``_ensure_token`` no dispara login.

    ``is_optional=True`` evita el teardown-assert si por concurrencia uno de los
    threads termina antes de emitir el GET (la lock serializa pero el shutdown
    del ThreadPoolExecutor puede aplastar el flush).
    """
    httpx_mock.add_response(
        url=re.compile(r".*/movimientos.*"),
        method="GET",
        json=[],
        is_reusable=True,
        is_optional=True,
    )
    return httpx_mock


def test_concurrent_sync_capture_does_not_corrupt_event_hooks(
    movimientos_mock: HTTPXMock,
) -> None:
    """ThreadPoolExecutor x 2 invocaciones concurrentes preservan event_hooks."""
    cuenta = "ACC-1"
    fecha = dt.date(2026, 1, 1)
    # Phase 15: instancia threadeada (reemplaza el _get_default() module-level).
    client = _make_sync_client()
    # Forzar instanciacion del http_client lazy antes de capturar pre_hooks.
    http_client = client._ensure_http_client()
    pre_hooks_request = list(http_client.event_hooks.get("request", []))
    pre_hooks_response = list(http_client.event_hooks.get("response", []))

    with ThreadPoolExecutor(max_workers=2) as pool:
        futs = [
            pool.submit(main_higyrus._capture_sync_query_string, client, cuenta, fecha, fecha)
            for _ in range(2)
        ]
        results = [f.result() for f in futs]

    # No corruption -- los hooks post-test son byte-identicos a los pre-test.
    post_hooks_request = list(http_client.event_hooks.get("request", []))
    post_hooks_response = list(http_client.event_hooks.get("response", []))
    assert post_hooks_request == pre_hooks_request
    assert post_hooks_response == pre_hooks_response
    # Ambas invocaciones deben haber completado.
    assert len(results) == 2


async def test_concurrent_async_capture_does_not_corrupt_event_hooks(
    movimientos_mock: HTTPXMock,
) -> None:
    """asyncio.gather x 2 invocaciones concurrentes preservan event_hooks async."""
    cuenta = "ACC-1"
    fecha = dt.date(2026, 1, 1)
    # Phase 15: instancia threadeada (reemplaza el _get_default() module-level).
    aclient = _make_async_client()
    # Forzar instanciacion del cliente async antes de capturar pre_hooks.
    http_client = await aclient._ensure_http_client()
    pre_hooks_request = list(http_client.event_hooks.get("request", []))
    pre_hooks_response = list(http_client.event_hooks.get("response", []))

    try:
        results = await asyncio.gather(
            main_higyrus._capture_async_query_string(aclient, cuenta, fecha, fecha),
            main_higyrus._capture_async_query_string(aclient, cuenta, fecha, fecha),
        )

        post_hooks_request = list(http_client.event_hooks.get("request", []))
        post_hooks_response = list(http_client.event_hooks.get("response", []))
        assert post_hooks_request == pre_hooks_request
        assert post_hooks_response == pre_hooks_response
        assert len(results) == 2
    finally:
        await aclient.aclose()


def test_event_hooks_restored_after_single_sync_capture(
    movimientos_mock: HTTPXMock,
) -> None:
    """Sanity: incluso una sola invocacion restaura el estado pre-test."""
    cuenta = "ACC-1"
    fecha = dt.date(2026, 1, 1)
    # Phase 15: instancia threadeada (reemplaza el _get_default() module-level).
    client = _make_sync_client()
    http_client = client._ensure_http_client()
    pre_hooks_request = list(http_client.event_hooks.get("request", []))

    main_higyrus._capture_sync_query_string(client, cuenta, fecha, fecha)

    post_hooks_request = list(http_client.event_hooks.get("request", []))
    assert post_hooks_request == pre_hooks_request
