"""Fixtures compartidas para los tests de higyrus-client.

Phase 06 Plan 05 — REFAC-02 migration: el cliente sigue exponiendo
funciones a nivel módulo (vía un default-client perezoso) pero el state
vive en ``_ClientState`` por instancia. Los fixtures ``autouse``
configuran credenciales de prueba y precargan el token vía
``configure(token=..., token_expires_at=...)`` en lugar de
``monkeypatch.setattr(pkg.client, "_token", ...)`` (Pitfall #1 + #4: los
monkeypatches al módulo ya no llegan al state desde el refactor).
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator

import pytest

import higyrus_client
from higyrus_client import aio

# Phase 13 IN-03: symbolic name for the "non-expiring token" sentinel used
# throughout the higyrus test suite. ``9_999_999_999.0`` is Unix epoch
# ~year 2286 (well beyond any test horizon). New test sites SHOULD use
# this constant; legacy sites that still embed the literal are kept until
# v1.3 sweep.
NEVER_EXPIRES = 9_999_999_999.0


@pytest.fixture(autouse=True)
def _configure_sync() -> Iterator[None]:
    """Configura creds dummy y precarga un token para el módulo sync."""
    higyrus_client.configure(
        base_url="https://api.test",
        username="u",
        password="p",
        client_id="tenant",
        token="test-token",
        token_expires_at=NEVER_EXPIRES,
    )
    yield
    higyrus_client.configure(base_url="", username="", password="", client_id="")


@pytest.fixture(autouse=True)
async def _configure_async() -> AsyncIterator[None]:
    """Configura creds dummy y precarga un token para el módulo async."""
    aio.configure(
        base_url="https://api.test",
        username="u",
        password="p",
        client_id="tenant",
        token="test-token",
        token_expires_at=NEVER_EXPIRES,
    )
    yield
    await aio.aclose()
    aio.configure(base_url="", username="", password="", client_id="")
