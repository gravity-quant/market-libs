"""Fixtures compartidas para los tests de matriz-client."""

from __future__ import annotations

import time
from collections.abc import Iterator

import pytest

import matriz_client
from matriz_client import client as _client


@pytest.fixture(autouse=True)
def _configure_sync(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Configura creds dummy y precarga un token cacheado.

    El token se setea con un timestamp ``fresh`` para que ``_ensure_token``
    no dispare un login real durante los tests de endpoints autenticados.
    """
    matriz_client.configure(
        base_url="https://api.test",
        username="test-user",
        password="test-pass",
    )
    monkeypatch.setattr(_client, "_token", "test-token", raising=False)
    monkeypatch.setattr(_client, "_token_ts", time.time(), raising=False)
    yield
    matriz_client.configure(base_url="https://api.test", username="", password="")
