"""Fixtures compartidas para iol-client."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator

import pytest

import iol_client
from iol_client import aio


@pytest.fixture(autouse=True)
def _configure_sync(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    iol_client.configure(
        base_url="https://api.test",
        username="u",
        password="p",
    )
    # Precargamos un token para evitar disparar login en endpoints autenticados.
    monkeypatch.setattr(iol_client.client, "_token", "test-token", raising=False)
    monkeypatch.setattr(iol_client.client, "_token_expires_at", 9_999_999_999.0, raising=False)
    yield
    iol_client.configure(base_url="https://api.test", username="", password="")


@pytest.fixture(autouse=True)
async def _configure_async(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[None]:
    aio.configure(base_url="https://api.test", username="u", password="p")
    monkeypatch.setattr(aio, "_token", "test-token", raising=False)
    monkeypatch.setattr(aio, "_token_expires_at", 9_999_999_999.0, raising=False)
    yield
    await aio.aclose()
    aio.configure(base_url="https://api.test", username="", password="")
