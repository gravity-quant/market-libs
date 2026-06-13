"""Cross-thread refresh regression for matriz Phase 10 Plan 10-03 TokenStore.

Validates that a sync caller holding the refresh-lock blocks an async caller
from issuing a redundant refresh — both observe the SAME refreshed token
(no stale, no duplicate refresh). This is REFAC-04 success criterion #2.

The 3-way concurrent test (I3) extends the same property to 5 sync + 5 async
+ 1 simulated daemon thread → exactly 1 refresh, 0 errors. Closes the
canonical 10-PATTERNS.md cross-thread contract.

I4 wires the real ``MatrizRefresh`` adapter via ``pytest-httpx`` to prove the
full ``build_token_store(state, ...)`` composition agrees with the same
contract end-to-end.
"""

from __future__ import annotations

import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import httpx
from pytest_httpx import HTTPXMock

from matriz_client._state import _ClientState
from matriz_client._token_store import TokenStore, build_token_store


async def test_async_caller_waits_for_concurrent_sync_refresh() -> None:
    """I1 — Sync thread holds refresh-lock for 100ms; async caller awaits.

    Both receive ``TOKEN-1``; ``refresh_count == 1`` (canonical REFAC-04
    success criterion #2).
    """
    refresh_count = 0
    refresh_started = threading.Event()

    def refresh_fn(call_id: int) -> str:
        nonlocal refresh_count
        refresh_started.set()
        time.sleep(0.1)  # simulate 100ms network call holding the lock
        refresh_count += 1
        return f"TOKEN-{refresh_count}"

    store = TokenStore(ttl_seconds=10, refresh_fn=refresh_fn)

    sync_token_holder: list[str] = []

    def sync_caller() -> None:
        sync_token_holder.append(store.get_sync().value)

    t = threading.Thread(target=sync_caller, daemon=True)
    t.start()
    # Wait until the thread has entered refresh_fn (acquired the lock).
    assert refresh_started.wait(timeout=1.0), "sync caller did not start refresh"

    # Async caller now races; it should AWAIT until the sync refresh completes.
    async_snap = await store.get_async()
    t.join(timeout=2.0)
    assert not t.is_alive(), "sync thread did not finish"

    assert async_snap.value == sync_token_holder[0] == "TOKEN-1"
    assert refresh_count == 1


async def test_sync_caller_waits_for_concurrent_async_refresh() -> None:
    """I2 — Inverse direction. Async caller acquires first; sync awaits.

    A separate sync thread starts AFTER the async caller has begun, races
    for the same lock, and both observe the same refreshed token.
    """
    refresh_count = 0
    refresh_started = threading.Event()

    def refresh_fn(call_id: int) -> str:
        nonlocal refresh_count
        refresh_started.set()
        time.sleep(0.1)
        refresh_count += 1
        return f"TOKEN-{refresh_count}"

    store = TokenStore(ttl_seconds=10, refresh_fn=refresh_fn)

    sync_token_holder: list[str] = []

    def sync_caller() -> None:
        sync_token_holder.append(store.get_sync().value)

    # Kick the async caller first; it offloads refresh via asyncio.to_thread
    # which acquires the state_lock in a worker thread.
    async_task = asyncio.create_task(store.get_async())
    # Wait until the refresh actually started inside the worker thread. The
    # event is a threading.Event because it is set by the worker thread; we
    # offload the blocking wait via asyncio.to_thread so the loop stays live.
    await asyncio.to_thread(refresh_started.wait, 1.0)
    assert refresh_started.is_set(), "async caller did not start refresh"

    # Now start the sync caller — it must wait for the state_lock.
    t = threading.Thread(target=sync_caller, daemon=True)
    t.start()

    async_snap = await async_task
    t.join(timeout=2.0)
    assert not t.is_alive(), "sync thread did not finish"

    assert async_snap.value == sync_token_holder[0] == "TOKEN-1"
    assert refresh_count == 1


async def test_3way_race_after_ttl_expiry() -> None:
    """I3 — 5 sync threads + 5 async coroutines + 1 daemon thread race.

    All 11 callers contend for the first refresh after a fresh TokenStore.
    Exactly 1 refresh fires; all 11 receive the same token; no errors.
    """
    refresh_count = 0

    def refresh_fn(call_id: int) -> str:
        nonlocal refresh_count
        # Sleep so the herd can pile up on the lock during the call.
        time.sleep(0.05)
        refresh_count += 1
        return f"TOKEN-{refresh_count}"

    store = TokenStore(ttl_seconds=10, refresh_fn=refresh_fn)
    start_gate = threading.Event()

    tokens_received: list[str] = []
    tokens_lock = threading.Lock()

    def sync_worker() -> None:
        start_gate.wait()
        tok = store.get_sync().value
        with tokens_lock:
            tokens_received.append(tok)

    async def async_worker() -> None:
        # All async workers wait for the cross-thread gate via
        # ``asyncio.to_thread`` (the gate is a threading.Event because the
        # sync workers also wait on it; using to_thread keeps the event loop
        # responsive and avoids spin-polling).
        await asyncio.to_thread(start_gate.wait, 5.0)
        snap = await store.get_async()
        with tokens_lock:
            tokens_received.append(snap.value)

    # Set up 5 sync threads.
    sync_pool = ThreadPoolExecutor(max_workers=5)
    sync_futures = [sync_pool.submit(sync_worker) for _ in range(5)]
    # Set up 1 simulated daemon thread.
    daemon = threading.Thread(target=sync_worker, daemon=True)
    daemon.start()
    # Set up 5 async coroutines.
    async_tasks = [asyncio.create_task(async_worker()) for _ in range(5)]

    # Release all 11 callers simultaneously.
    start_gate.set()

    # Wait for everyone.
    await asyncio.gather(*async_tasks)
    for fut in sync_futures:
        fut.result(timeout=5.0)
    sync_pool.shutdown(wait=True)
    daemon.join(timeout=5.0)
    assert not daemon.is_alive(), "daemon thread did not finish"

    assert refresh_count == 1, f"expected 1 refresh, got {refresh_count}"
    assert len(tokens_received) == 11
    assert set(tokens_received) == {"TOKEN-1"}


async def test_build_token_store_integration_with_matriz_refresh(
    httpx_mock: HTTPXMock,
) -> None:
    """I4 — Real ``MatrizRefresh`` adapter integration.

    Wires ``state`` with a sync ``httpx.Client`` (so ``MatrizRefresh`` issues
    a real POST through the pytest-httpx transport mock), builds the
    TokenStore via ``build_token_store``, and races a sync + async caller.
    The mock answers exactly once; both callers receive the same token.
    """
    httpx_mock.add_response(
        url="https://api.test/auth/getToken",
        method="POST",
        headers={"X-Auth-Token": "INTEGRATION-TOKEN"},
    )

    state = _ClientState()
    state.base_url = "https://api.test"
    state.username = "test-user"
    state.password = "test-pass"
    # MatrizRefresh requires a sync httpx.Client; the pytest-httpx mock
    # intercepts all httpx.Client transactions in the test process.
    sync_http = httpx.Client()
    state.http_client = sync_http
    try:
        store = build_token_store(state, max_retries=2)

        sync_token_holder: list[str] = []

        def sync_caller() -> None:
            sync_token_holder.append(store.get_sync().value)

        t = threading.Thread(target=sync_caller, daemon=True)
        t.start()
        # Concurrent async caller.
        async_snap = await store.get_async()
        t.join(timeout=5.0)
        assert not t.is_alive(), "sync caller did not finish"

        assert async_snap.value == "INTEGRATION-TOKEN"
        assert sync_token_holder[0] == "INTEGRATION-TOKEN"
        # Exactly one wire request — proves the lock coalesced both callers.
        assert len(httpx_mock.get_requests()) == 1
    finally:
        # close() is blocking; offload to a worker thread so we are not
        # blocking the event loop here (ASYNC212).
        await asyncio.to_thread(sync_http.close)
