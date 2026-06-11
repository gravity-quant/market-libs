"""Fixtures compartidas para los tests de matriz-client.

Phase 6 Plan 06 migration: ``configure(token=..., token_expires_at=...)``
extiende los kwargs (D-04) y reemplaza el monkeypatching directo de
``_token``/``_token_ts`` por la API pública. Esto evita Pitfall #4 (tests
escribiendo a globals que el refactor mueve a estado de instancia) y prepara
el camino para Phase 10 REFAC-04.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

import matriz_client


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
        token_expires_at=9_999_999_999.0,
    )
    yield
    # base_url/username/password change without explicit token kwargs resets
    # the token cache to force re-auth on the next test (D-04).
    matriz_client.configure(
        base_url="https://api.test",
        username="",
        password="",
    )
