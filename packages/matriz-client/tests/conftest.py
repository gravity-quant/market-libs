"""Fixtures compartidas para los tests de matriz-client.

Phase 6 Plan 06 migration: ``configure(token=..., token_expires_at=...)``
extiende los kwargs (D-04) y reemplaza el monkeypatching directo de
``_token``/``_token_ts`` por la API pública. Esto evita Pitfall #4 (tests
escribiendo a globals que el refactor mueve a estado de instancia).

Phase 10 Plan 10-02 addition: ``_configure_async`` autouse fixture mirrors
the sync fixture for the AsyncClient default singleton, mirroring iol-client's
conftest pattern. Closes the test isolation for the async REST surface.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator

import pytest

import matriz_client
from matriz_client import aio

# Phase 13 IN-03: symbolic name for the "non-expiring token" sentinel used
# throughout the matriz test suite. ``9_999_999_999.0`` is Unix epoch
# ~year 2286 (well beyond any test horizon). New test sites SHOULD use
# this constant; legacy sites that still embed the literal are kept until
# v1.3 sweep.
NEVER_EXPIRES = 9_999_999_999.0


@pytest.fixture(autouse=True)
def _configure_sync() -> Iterator[None]:
    """Configura creds dummy y precarga un token cacheado.

    El token se setea con un ``token_expires_at`` muy futuro para que
    ``_ensure_token`` no dispare un login real durante los tests de endpoints
    autenticados.
    """
    matriz_client.configure(
        base_url="https://api.test",
        username="test-user",
        password="test-pass",
        token="test-token",
        token_expires_at=NEVER_EXPIRES,
    )
    yield
    # base_url/username/password change without explicit token kwargs resets
    # the token cache to force re-auth on the next test (D-04).
    matriz_client.configure(
        base_url="https://api.test",
        username="",
        password="",
    )


@pytest.fixture(autouse=True)
async def _configure_async() -> AsyncIterator[None]:
    """Configura creds dummy + token precargado para el default AsyncClient.

    Phase 10 Plan 10-02 mirror del ``_configure_sync`` arriba. Cierra el
    ``httpx.AsyncClient`` en teardown para que el próximo test arranque con un
    transport fresco que ``httpx_mock`` pueda interceptar (mismo pattern que
    iol-client conftest).
    """
    aio.configure(
        base_url="https://api.test",
        username="test-user",
        password="test-pass",
        token="test-token",
        token_expires_at=NEVER_EXPIRES,
    )
    yield
    await aio._get_default().aclose()
    aio.configure(base_url="https://api.test", username="", password="")
