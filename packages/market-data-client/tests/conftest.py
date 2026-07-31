"""Fixtures compartidas para market-data-client.

Pitfall 6 (contaminación cross-test del singleton a nivel módulo): cada test
arranca con un default ``Client`` / ``AsyncClient`` sembrado con credenciales
dummy + un token no-vencido, y al teardown cierra el transport para que el
siguiente test reciba un ``httpx.Client`` fresco que ``httpx_mock`` pueda
interceptar (el patch de pytest-httpx opera sobre el transport subyacente).

El sentinel ``NEVER_EXPIRES`` (``9_999_999_999.0`` ≈ año 2286) mantiene el token
sembrado "fresco" para todo test que NO ejerza el flujo de auth; los tests de
lifecycle fuerzan ``token_expires_at=0.0`` explícitamente para disparar un
re-fetch (Pitfall 3 — assert por COUNT, no por ordering).
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator

import pytest

import market_data_client
from market_data_client import aio

# Sentinel para el "non-expiring token" usado en toda la suite. Los sites de
# lifecycle sobrescriben ``token_expires_at`` con ``0.0`` para forzar el grant.
NEVER_EXPIRES = 9_999_999_999.0


@pytest.fixture(autouse=True)
def _configure_sync() -> Iterator[None]:
    market_data_client.configure(
        base_url="https://market-data-develop.test/api",
        client_id="cid",
        client_secret="csec",
        audience="aud",
        auth0_token_url="https://auth.test/oauth/token",
        token="test-token",
        token_expires_at=NEVER_EXPIRES,
    )
    yield
    # Cierre del transport: cada test arranca con un httpx.Client fresco que
    # ``httpx_mock`` intercepta vía el patch de Transport.
    market_data_client.client._get_default().close()
    # Pitfall 6: resetea también los campos del gate en el singleton default para
    # que un test que abrió el gate (``mutating_allowed=True``) no contamine al
    # siguiente. ``expected_host`` vuelve al host develop default (constante).
    market_data_client.configure(
        base_url="https://market-data-develop.test/api",
        client_id="",
        client_secret="",
        audience="",
        auth0_token_url="https://auth.test/oauth/token",
        mutating_allowed=False,
        expected_host="market-data-develop.bbsa.com.ar",
    )


@pytest.fixture(autouse=True)
async def _configure_async() -> AsyncIterator[None]:
    aio.configure(
        base_url="https://market-data-develop.test/api",
        client_id="cid",
        client_secret="csec",
        audience="aud",
        auth0_token_url="https://auth.test/oauth/token",
        token="test-token",
        token_expires_at=NEVER_EXPIRES,
    )
    yield
    await aio._get_default().aclose()
    # Pitfall 6 (async): mismo reset del gate en el singleton async default.
    aio.configure(
        base_url="https://market-data-develop.test/api",
        client_id="",
        client_secret="",
        audience="",
        auth0_token_url="https://auth.test/oauth/token",
        mutating_allowed=False,
        expected_host="market-data-develop.bbsa.com.ar",
    )
