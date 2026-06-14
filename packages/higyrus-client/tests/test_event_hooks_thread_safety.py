"""CR-07 — main_higyrus.py ``_capture_*_query_string`` thread-safety regression.

Invariante: invocaciones concurrentes cross-thread / cross-event-loop de
``_capture_sync_query_string`` y ``_capture_async_query_string`` NO deben
corromper el estado compartido ``httpx.Client.event_hooks`` /
``httpx.AsyncClient.event_hooks``.

Fix path (Phase 11 CR-07): los helpers serializan la mutación in-place del
``event_hooks`` con ``threading.Lock`` (sync) y ``asyncio.Lock`` (async).
La alternativa "per-request hook injection" via ``http_client=`` kwarg
requiere reconstruir transport+auth interno del default Client y se descartó
por radio de impacto excesivo (per ``11-PATTERNS.md:277-285``).
"""

from __future__ import annotations

import asyncio
import datetime as dt
import re
from concurrent.futures import ThreadPoolExecutor

import pytest
from pytest_httpx import HTTPXMock

import higyrus_client
import main_higyrus
from higyrus_client import aio


@pytest.fixture
def _movimientos_mock(httpx_mock: HTTPXMock) -> HTTPXMock:
    """Pre-mockea login + movimientos con respuestas reusables (is_reusable=True)."""
    httpx_mock.add_response(
        url=re.compile(r".*/api/login.*"),
        method="POST",
        json={"username": "u", "token": "tok-thread-safety", "expiresIn": 86400},
        is_reusable=True,
    )
    httpx_mock.add_response(
        url=re.compile(r".*/movimientos.*"),
        method="GET",
        json=[],
        is_reusable=True,
    )
    return httpx_mock


def test_concurrent_sync_capture_does_not_corrupt_event_hooks(
    _movimientos_mock: HTTPXMock,
) -> None:
    """ThreadPoolExecutor × 2 invocaciones concurrentes preservan event_hooks."""
    cuenta = "ACC-1"
    fecha = dt.date(2026, 1, 1)
    # Forzar instanciación del http_client lazy antes de capturar pre_hooks.
    higyrus_client.client._get_default()._ensure_http_client()
    client = higyrus_client.client._client
    assert client is not None
    pre_hooks_request = list(client.event_hooks.get("request", []))
    pre_hooks_response = list(client.event_hooks.get("response", []))

    with ThreadPoolExecutor(max_workers=2) as pool:
        futs = [
            pool.submit(main_higyrus._capture_sync_query_string, cuenta, fecha, fecha)
            for _ in range(2)
        ]
        results = [f.result() for f in futs]

    # No corruption — los hooks post-test son byte-identicos a los pre-test.
    post_hooks_request = list(client.event_hooks.get("request", []))
    post_hooks_response = list(client.event_hooks.get("response", []))
    assert post_hooks_request == pre_hooks_request
    assert post_hooks_response == pre_hooks_response
    # Ambas invocaciones deben haber completado.
    assert len(results) == 2


async def test_concurrent_async_capture_does_not_corrupt_event_hooks(
    _movimientos_mock: HTTPXMock,
) -> None:
    """asyncio.gather × 2 invocaciones concurrentes preservan event_hooks async."""
    cuenta = "ACC-1"
    fecha = dt.date(2026, 1, 1)
    # Forzar instanciación del cliente async antes de capturar pre_hooks.
    await aio._get_default()._ensure_http_client()
    assert aio._client is not None
    client = aio._client
    pre_hooks_request = list(client.event_hooks.get("request", []))
    pre_hooks_response = list(client.event_hooks.get("response", []))

    results = await asyncio.gather(
        main_higyrus._capture_async_query_string(cuenta, fecha, fecha),
        main_higyrus._capture_async_query_string(cuenta, fecha, fecha),
    )

    post_hooks_request = list(client.event_hooks.get("request", []))
    post_hooks_response = list(client.event_hooks.get("response", []))
    assert post_hooks_request == pre_hooks_request
    assert post_hooks_response == pre_hooks_response
    assert len(results) == 2


def test_event_hooks_restored_after_single_sync_capture(
    _movimientos_mock: HTTPXMock,
) -> None:
    """Sanity: incluso una sola invocación restaura el estado pre-test."""
    cuenta = "ACC-1"
    fecha = dt.date(2026, 1, 1)
    higyrus_client.client._get_default()._ensure_http_client()
    client = higyrus_client.client._client
    assert client is not None
    pre_hooks_request = list(client.event_hooks.get("request", []))

    main_higyrus._capture_sync_query_string(cuenta, fecha, fecha)

    post_hooks_request = list(client.event_hooks.get("request", []))
    assert post_hooks_request == pre_hooks_request
