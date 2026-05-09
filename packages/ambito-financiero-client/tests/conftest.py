"""Fixtures compartidas para ambito-financiero-client."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

import ambito_financiero_client as ambito
from ambito_financiero_client import aio


@pytest.fixture(autouse=True)
def _configure_sync() -> None:
    ambito.configure(base_url="https://mercados.ambito.com")
    return


@pytest.fixture(autouse=True)
async def _configure_async() -> AsyncIterator[None]:
    aio.configure(base_url="https://mercados.ambito.com")
    yield
    await aio.aclose()
