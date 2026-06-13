"""Cross-cutting WR-07 regression guard — ``aio.configure()`` warns on http_client drop.

Phase 8 code review WR-07 flagged that ``aio.configure()`` silently dropped
the prior ``httpx.AsyncClient`` without ``aclose()``. Every call after the
first leaked a TCP pool + SSL context. Not blocking for short-lived tests
but unbounded for long-running processes with rotating credentials.

The fix emits a ``ResourceWarning`` when overwriting a live
``_state.http_client`` so consumers see the leak signal and the recommended
``await aio.aclose()`` pre-step in the warning text.

Production code MUST NOT call ``aclose()`` automatically because
``configure()`` is synchronous and there's no event loop guaranteed at that
point. The warning is the only sensible signal.

Parametrized over the 3 packages with async support; matriz async is a stub
per D-25 (no configure() support).
"""

from __future__ import annotations

import asyncio
import importlib

import pytest

_ASYNC_PACKAGES = ["ambito_financiero_client", "iol_client", "higyrus_client"]


@pytest.mark.parametrize("pkg_name", _ASYNC_PACKAGES)
async def test_aio_configure_warns_when_replacing_live_http_client(pkg_name: str) -> None:
    """WR-07: ``aio.configure()`` emits ResourceWarning when overwriting a live client.

    Steps:
      1. Configure the async default client + force lazy http_client creation
         via _ensure_http_client (which sets _state.http_client to a real
         httpx.AsyncClient).
      2. Call aio.configure(...) a second time. The pre-existing
         http_client is live → ResourceWarning must fire with text mentioning
         the recommended `await aclose()` pre-step.
    """
    pkg = importlib.import_module(pkg_name)

    # First configure (no prior http_client → no warning expected on this call).
    # The kwargs differ per package; build_kwargs returns the minimal valid set.
    if pkg_name == "ambito_financiero_client":
        kw1 = {"base_url": "https://api.test"}
        kw2 = {"base_url": "https://api2.test"}
    elif pkg_name == "iol_client":
        kw1 = {"base_url": "https://api.test", "username": "u", "password": "p"}
        kw2 = {"max_retries": 5}
    elif pkg_name == "higyrus_client":
        kw1 = {
            "base_url": "https://api.test",
            "username": "u",
            "password": "p",
            "client_id": "tenant",
        }
        kw2 = {"base_url": "https://api2.test"}
    else:  # pragma: no cover
        raise AssertionError(f"unhandled pkg: {pkg_name}")

    pkg.aio.configure(**kw1)
    # Force lazy creation of the underlying httpx.AsyncClient. ambito's
    # _ensure_http_client is sync (no lock); iol/higyrus are async.
    client = pkg.aio._get_default()
    if asyncio.iscoroutinefunction(client._ensure_http_client):
        await client._ensure_http_client()
    else:
        client._ensure_http_client()
    assert client._state.http_client is not None, (
        "test setup error: failed to instantiate underlying httpx.AsyncClient"
    )

    # Second configure: should emit ResourceWarning since the previous
    # http_client is live.
    with pytest.warns(ResourceWarning, match="aclose"):
        pkg.aio.configure(**kw2)

    # Clean up: aclose the new client to avoid leaking into other tests.
    await pkg.aio.aclose()


@pytest.mark.parametrize("pkg_name", _ASYNC_PACKAGES)
async def test_aio_configure_no_warning_when_no_prior_http_client(pkg_name: str) -> None:
    """WR-07: configure() does NOT warn when there is no live prior http_client."""
    pkg = importlib.import_module(pkg_name)

    # Aclose to ensure no live http_client (idempotent).
    await pkg.aio.aclose()

    if pkg_name == "ambito_financiero_client":
        kw = {"base_url": "https://api.test"}
    elif pkg_name == "iol_client":
        kw = {"base_url": "https://api.test", "username": "u", "password": "p"}
    elif pkg_name == "higyrus_client":
        kw = {
            "base_url": "https://api.test",
            "username": "u",
            "password": "p",
            "client_id": "tenant",
        }
    else:  # pragma: no cover
        raise AssertionError(f"unhandled pkg: {pkg_name}")

    import warnings as _warnings

    with _warnings.catch_warnings(record=True) as caught:
        _warnings.simplefilter("always")
        pkg.aio.configure(**kw)
        # ResourceWarning from our package's aio.configure should not fire
        # when there's no live http_client to drop.
        relevant = [
            w
            for w in caught
            if issubclass(w.category, ResourceWarning) and pkg_name in str(w.message)
        ]
        assert len(relevant) == 0, (
            f"WR-07: expected no ResourceWarning when no prior http_client, "
            f"got {len(relevant)}: {[str(w.message) for w in relevant]}"
        )
