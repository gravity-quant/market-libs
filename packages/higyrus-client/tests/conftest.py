"""Fixtures compartidas para los tests de higyrus-client.

El cliente expone funciones a nivel módulo con state global. Los fixtures
``autouse`` configuran credenciales de prueba y, opcionalmente, precargan
un token cacheado para los tests que ejercitan endpoints autenticados sin
pasar por ``login()``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator

import pytest

import higyrus_client
from higyrus_client import aio


@pytest.fixture(autouse=True)
def _configure_sync(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Configura creds dummy y precarga un token para el módulo sync."""
    higyrus_client.configure(
        base_url="https://api.test",
        username="u",
        password="p",
        client_id="tenant",
    )
    monkeypatch.setattr(higyrus_client.client, "_token", "test-token", raising=False)
    monkeypatch.setattr(higyrus_client.client, "_token_ts", 9_999_999_999.0, raising=False)
    yield
    higyrus_client.configure(base_url="", username="", password="", client_id="")


@pytest.fixture(autouse=True)
async def _configure_async(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[None]:
    """Configura creds dummy y precarga un token para el módulo async."""
    aio.configure(
        base_url="https://api.test",
        username="u",
        password="p",
        client_id="tenant",
    )
    monkeypatch.setattr(aio, "_token", "test-token", raising=False)
    monkeypatch.setattr(aio, "_token_ts", 9_999_999_999.0, raising=False)
    yield
    await aio.aclose()
    aio.configure(base_url="", username="", password="", client_id="")
