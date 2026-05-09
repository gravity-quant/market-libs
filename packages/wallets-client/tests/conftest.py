"""Fixtures compartidas para wallets_client."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

import wallets_client
from wallets_client import aio


@pytest.fixture(autouse=True)
def _configure_sync() -> None:
    wallets_client.configure(base_url="https://api.test", token="test-token")
    return


@pytest.fixture(autouse=True)
async def _configure_async() -> AsyncIterator[None]:
    aio.configure(base_url="https://api.test", token="test-token")
    yield
    await aio.aclose()
