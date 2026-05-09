"""Fixtures compartidas para ambito-financiero-client."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator

import pytest

import ambito_financiero_client as ambito
from ambito_financiero_client import aio

_DEFAULT_BASE_URL = "https://mercados.ambito.com"


@pytest.fixture(autouse=True)
def _configure_sync() -> Iterator[None]:
    ambito.configure(base_url=_DEFAULT_BASE_URL)
    yield
    ambito.configure(base_url=_DEFAULT_BASE_URL)


@pytest.fixture(autouse=True)
async def _configure_async() -> AsyncIterator[None]:
    aio.configure(base_url=_DEFAULT_BASE_URL)
    yield
    await aio.aclose()
    aio.configure(base_url=_DEFAULT_BASE_URL)
