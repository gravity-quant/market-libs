"""Fixtures compartidas para wallets_client."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator

import pytest

import wallets_client
from wallets_client import aio


@pytest.fixture(autouse=True)
def _configure_sync(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    wallets_client.configure(base_url="https://api.test")
    monkeypatch.setattr(wallets_client.client, "_token", "test-token", raising=False)
    yield
    wallets_client.configure(base_url="https://api.test", token="")


@pytest.fixture(autouse=True)
async def _configure_async(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[None]:
    aio.configure(base_url="https://api.test")
    monkeypatch.setattr(aio, "_token", "test-token", raising=False)
    yield
    await aio.aclose()
    aio.configure(base_url="https://api.test", token="")
