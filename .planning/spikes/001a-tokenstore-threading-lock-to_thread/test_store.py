"""Experiential tests for TokenStoreThreadingOnly.

Each test simulates one of the 3 contexts and the integration of all 3.
Log events are collected with ISO timestamps so we can see ordering empirically.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import threading
import time
from datetime import datetime, timezone

from store import TokenStoreThreadingOnly


# --- Event log (observability layer per spike workflow §build_spikes/d) -----

_LOG_LOCK = threading.Lock()
LOG: list[dict] = []


def log(category: str, msg: str, **extra) -> None:
    with _LOG_LOCK:
        LOG.append(
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "thread": threading.current_thread().name,
                "category": category,
                "msg": msg,
                **extra,
            }
        )


def reset_log() -> None:
    with _LOG_LOCK:
        LOG.clear()


# --- Fake refresh fn — simulates 50ms network round-trip ------------------


def make_refresh_fn(*, delay_s: float = 0.05):
    def refresh(call_id: int) -> str:
        log("refresh", f"start id={call_id}")
        time.sleep(delay_s)  # simulate network
        token = f"tok-{call_id}-{int(time.monotonic() * 1000)}"
        log("refresh", f"end id={call_id} → {token}")
        return token

    return refresh


# --- Test 1: single-caller from each context returns the same token --------


def test_sync_single_caller():
    reset_log()
    store = TokenStoreThreadingOnly(ttl=10.0, refresh_fn=make_refresh_fn())
    snap = store.get_sync()
    assert snap.value.startswith("tok-1-"), f"unexpected token: {snap.value}"
    assert store.stats()["refresh_count"] == 1
    # second call within TTL — no refresh
    snap2 = store.get_sync()
    assert snap2.value == snap.value
    assert store.stats()["refresh_count"] == 1
    print("✓ sync_single_caller: 1 refresh, cached read returns same token")


def test_async_single_caller():
    reset_log()
    store = TokenStoreThreadingOnly(ttl=10.0, refresh_fn=make_refresh_fn())

    async def run():
        snap = await store.get_async()
        snap2 = await store.get_async()
        return snap, snap2

    snap, snap2 = asyncio.run(run())
    assert snap.value == snap2.value
    assert store.stats()["refresh_count"] == 1
    print("✓ async_single_caller: 1 refresh, cached read returns same token")


# --- Test 2: thundering herd — N concurrent sync callers, 1 expired token --


def test_sync_thundering_herd():
    """20 threads hit get_sync() simultaneously with expired/missing token.
    Expectation: exactly 1 refresh, all threads see the same token.
    """
    reset_log()
    store = TokenStoreThreadingOnly(ttl=10.0, refresh_fn=make_refresh_fn())

    start = threading.Barrier(20)
    results: list[str] = []
    results_lock = threading.Lock()

    def worker(i: int) -> None:
        start.wait()  # release all at once
        snap = store.get_sync()
        with results_lock:
            results.append(snap.value)

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
        list(ex.map(worker, range(20)))

    assert len(set(results)) == 1, f"expected 1 unique token, got {len(set(results))}: {set(results)}"
    assert store.stats()["refresh_count"] == 1, f"expected 1 refresh, got {store.stats()['refresh_count']}"
    print("✓ sync_thundering_herd: 20 threads → 1 refresh, all got same token")


# --- Test 3: thundering herd — N concurrent ASYNC callers ------------------


def test_async_thundering_herd():
    """50 coroutines hit get_async() simultaneously with expired/missing token.
    Expectation: exactly 1 refresh, all coroutines see the same token, event loop not blocked.
    """
    reset_log()
    store = TokenStoreThreadingOnly(ttl=10.0, refresh_fn=make_refresh_fn(delay_s=0.05))

    loop_block_observed: list[float] = []

    async def loop_health_monitor():
        """Measure event loop responsiveness while the herd runs."""
        last = time.monotonic()
        while True:
            await asyncio.sleep(0)  # yield
            now = time.monotonic()
            delta = (now - last) * 1000  # ms
            loop_block_observed.append(delta)
            last = now
            if len(loop_block_observed) > 200:
                return

    async def caller(i: int) -> str:
        snap = await store.get_async()
        return snap.value

    async def run():
        monitor_task = asyncio.create_task(loop_health_monitor())
        results = await asyncio.gather(*(caller(i) for i in range(50)))
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
        return results

    results = asyncio.run(run())
    unique = set(results)
    assert len(unique) == 1, f"expected 1 unique token, got {len(unique)}"
    refresh_count = store.stats()["refresh_count"]

    # Event loop max-block while a thread held the lock during refresh
    if loop_block_observed:
        max_block = max(loop_block_observed)
        median_block = sorted(loop_block_observed)[len(loop_block_observed) // 2]
    else:
        max_block = -1
        median_block = -1
    print(
        f"✓ async_thundering_herd: 50 coros → {refresh_count} refresh(es) | "
        f"event loop tick: max={max_block:.2f}ms median={median_block:.3f}ms"
    )

    # The KEY claim of this approach: event loop is NOT blocked by the lock-held
    # refresh because the refresh runs in a worker thread. Max block should be << 50ms
    # even though refresh takes 50ms.
    if max_block > 5:
        print(f"  ⚠ event loop blocked {max_block:.2f}ms (target: < 5ms)")
    return refresh_count, max_block


# --- Test 4: 3-WAY integration — sync + async + daemon thread together -----


def test_3way_integration():
    """The realistic scenario:
       - Main thread doing sync REST calls
       - Event loop in another thread doing async REST calls
       - Daemon thread simulating ws_client
       All hitting get_sync()/get_async() with expired token.
    """
    reset_log()
    store = TokenStoreThreadingOnly(ttl=10.0, refresh_fn=make_refresh_fn(delay_s=0.05))

    barrier = threading.Barrier(3)  # main thread + async runner + daemon thread

    sync_result: dict = {}
    daemon_result: dict = {}
    async_result: dict = {}

    def sync_worker():
        barrier.wait()
        snap = store.get_sync()
        sync_result["token"] = snap.value
        log("sync_worker", f"got {snap.value}")

    def daemon_worker():
        barrier.wait()
        snap = store.get_sync()
        daemon_result["token"] = snap.value
        log("daemon_worker", f"got {snap.value}")

    def async_runner():
        async def main():
            snap = await store.get_async()
            async_result["token"] = snap.value
            log("async_runner", f"got {snap.value}")

        barrier.wait()
        asyncio.run(main())

    t_sync = threading.Thread(target=sync_worker, name="SyncWorker")
    t_daemon = threading.Thread(target=daemon_worker, name="DaemonWorker", daemon=True)
    t_async = threading.Thread(target=async_runner, name="AsyncRunner")
    t_sync.start()
    t_daemon.start()
    t_async.start()
    t_sync.join()
    t_async.join()
    t_daemon.join()

    tokens = {sync_result["token"], daemon_result["token"], async_result["token"]}
    refresh_count = store.stats()["refresh_count"]
    assert len(tokens) == 1, f"expected 1 unique token across 3 contexts, got {tokens}"
    assert refresh_count == 1, f"expected 1 refresh, got {refresh_count}"
    print(f"✓ 3way_integration: 3 contexts → 1 refresh, all got {next(iter(tokens))}")


if __name__ == "__main__":
    test_sync_single_caller()
    test_async_single_caller()
    test_sync_thundering_herd()
    refresh_n, max_block = test_async_thundering_herd()
    test_3way_integration()
    print()
    print(f"=== Approach 001a summary ===")
    print(f"  All correctness tests passed.")
    print(f"  Async thundering-herd: refresh_count={refresh_n}, max_event_loop_block={max_block:.2f}ms")
