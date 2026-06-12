"""Fixtures compartidas para iol-client.

Phase 6 — migración Pitfall #1: el patrón legacy de
``monkeypatch.setattr(pkg.client, "_token", X, raising=False)`` deja de
funcionar porque el shim PEP 562 es read-only — los writes hit el
módulo dict, no ``_state``. El sentinel se inyecta vía
``configure(token=..., token_expires_at=...)`` (extensión de la signature
de ``configure()`` aterrizada en este mismo plan).

Las fixtures cierran el ``http_client`` del default Client al teardown
para que cada test arranque con un transport fresco que ``httpx_mock``
pueda interceptar.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator

import pytest

import iol_client
from iol_client import aio


@pytest.fixture(autouse=True)
def _configure_sync() -> Iterator[None]:
    iol_client.configure(
        base_url="https://api.test",
        username="u",
        password="p",
        token="test-token",
        token_expires_at=9_999_999_999.0,
    )
    yield
    # Cierre del transport: cada test arranca con un httpx.Client fresco
    # que ``httpx_mock`` intercepta vía el patch de Transport.
    iol_client.client._get_default().close()
    iol_client.configure(base_url="https://api.test", username="", password="")


@pytest.fixture(autouse=True)
async def _configure_async() -> AsyncIterator[None]:
    aio.configure(
        base_url="https://api.test",
        username="u",
        password="p",
        token="test-token",
        token_expires_at=9_999_999_999.0,
    )
    yield
    await aio._get_default().aclose()
    aio.configure(base_url="https://api.test", username="", password="")
