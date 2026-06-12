"""Experiential tests for TokenStoreAsyncioOnly + LoopAwareSyncBridge."""

from __future__ import annotations

import asyncio
import concurrent.futures
import threading
import time
from datetime import datetime, timezone

from store import LoopAwareSyncBridge, TokenStoreAsyncioOnly


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


def make_refresh_fn(*, delay_s: float = 0.05):
    """Async refresh fn — simulates 50ms network round-trip via asyncio.sleep."""

    async def refresh(call_id: int) -> str:
        log("refresh", f"start id={call_id}")
        await asyncio.sleep(delay_s)
        token = f"tok-{call_id}-{int(time.monotonic() * 1000)}"
        log("refresh", f"end id={call_id} → {token}")
        return token

    return refresh


# --- Test 1: async single caller -----------------------------------------


def test_async_single_caller():
    reset_log()
    store = TokenStoreAsyncioOnly(ttl=10.0, refresh_fn=make_refresh_fn())

    async def run():
        snap = await store.get_async()
        snap2 = await store.get_async()
        return snap, snap2

    snap, snap2 = asyncio.run(run())
    assert snap.value == snap2.value
    assert store.stats()["refresh_count"] == 1
    print("✓ async_single_caller: 1 refresh, cached read returns same token")


# --- Test 2: async thundering herd ---------------------------------------


def test_async_thundering_herd():
    reset_log()
    store = TokenStoreAsyncioOnly(ttl=10.0, refresh_fn=make_refresh_fn(delay_s=0.05))
    loop_block_observed: list[float] = []

    async def monitor():
        last = time.monotonic()
        while True:
            await asyncio.sleep(0)
            now = time.monotonic()
            loop_block_observed.append((now - last) * 1000)
            last = now
            if len(loop_block_observed) > 200:
                return

    async def caller(i: int) -> str:
        snap = await store.get_async()
        return snap.value

    async def run():
        m = asyncio.create_task(monitor())
        results = await asyncio.gather(*(caller(i) for i in range(50)))
        m.cancel()
        try:
            await m
        except asyncio.CancelledError:
            pass
        return results

    results = asyncio.run(run())
    unique = set(results)
    refresh_count = store.stats()["refresh_count"]
    max_block = max(loop_block_observed) if loop_block_observed else -1
    median_block = sorted(loop_block_observed)[len(loop_block_observed) // 2] if loop_block_observed else -1
    assert len(unique) == 1, f"expected 1 unique token, got {len(unique)}"
    print(
        f"✓ async_thundering_herd: 50 coros → {refresh_count} refresh(es) | "
        f"event loop tick: max={max_block:.2f}ms median={median_block:.3f}ms"
    )
    return refresh_count, max_block


# --- Test 3: sync caller via bridge --------------------------------------


def test_sync_via_bridge_single():
    reset_log()
    store = TokenStoreAsyncioOnly(ttl=10.0, refresh_fn=make_refresh_fn())
    bridge = LoopAwareSyncBridge(store)
    bridge.start()
    try:
        snap = bridge.get_sync()
        snap2 = bridge.get_sync()
        assert snap.value == snap2.value
        assert store.stats()["refresh_count"] == 1
        print(f"✓ sync_via_bridge_single: 1 refresh via background loop")
    finally:
        bridge.stop()


def test_sync_via_bridge_thundering_herd():
    """20 sync threads call get_sync() simultaneously via the bridge."""
    reset_log()
    store = TokenStoreAsyncioOnly(ttl=10.0, refresh_fn=make_refresh_fn())
    bridge = LoopAwareSyncBridge(store)
    bridge.start()
    try:
        start = threading.Barrier(20)
        results: list[str] = []
        results_lock = threading.Lock()

        def worker(i: int) -> None:
            start.wait()
            snap = bridge.get_sync()
            with results_lock:
                results.append(snap.value)

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
            list(ex.map(worker, range(20)))

        unique = set(results)
        assert len(unique) == 1, f"expected 1 unique token, got {unique}"
        assert store.stats()["refresh_count"] == 1, store.stats()
        print(
            f"✓ sync_via_bridge_thundering_herd: 20 sync threads through bridge → 1 refresh"
        )
    finally:
        bridge.stop()


# --- Test 4: 3-way integration -------------------------------------------


def test_3way_integration():
    """Sync caller (own thread) + async runner (own thread + own loop) + daemon thread
    (own thread). All routed through the same TokenStore.

    The bridge is shared. Async runner uses store directly; sync + daemon go via bridge.
    """
    reset_log()
    store = TokenStoreAsyncioOnly(ttl=10.0, refresh_fn=make_refresh_fn(delay_s=0.05))
    bridge = LoopAwareSyncBridge(store)
    bridge.start()
    try:
        barrier = threading.Barrier(3)
        results: dict[str, str] = {}

        def sync_worker():
            barrier.wait()
            snap = bridge.get_sync()
            results["sync"] = snap.value

        def daemon_worker():
            barrier.wait()
            snap = bridge.get_sync()
            results["daemon"] = snap.value

        def async_runner():
            async def main():
                # NOTE: this runs in a SEPARATE loop from the bridge's loop.
                # The store is now being accessed concurrently from 2 different loops.
                # asyncio.Lock instances are loop-bound — this can break!
                snap = await store.get_async()
                results["async"] = snap.value

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

        tokens = {results["sync"], results["daemon"], results["async"]}
        refresh_count = store.stats()["refresh_count"]
        print(
            f"{'✓' if len(tokens) == 1 and refresh_count == 1 else '✗'} "
            f"3way_integration: tokens={tokens}, refreshes={refresh_count}"
        )
        if len(tokens) != 1 or refresh_count != 1:
            print(f"  ⚠ FAIL — see investigation trail in README")
            return False
        return True
    finally:
        bridge.stop()


if __name__ == "__main__":
    test_async_single_caller()
    refresh_n, max_block = test_async_thundering_herd()
    test_sync_via_bridge_single()
    test_sync_via_bridge_thundering_herd()
    ok = test_3way_integration()
    print()
    print(f"=== Approach 001b summary ===")
    print(f"  Async thundering herd: refresh_count={refresh_n}, max_event_loop_block={max_block:.2f}ms")
    print(f"  3-way integration: {'PASS' if ok else 'FAIL — async runner has own loop, asyncio.Lock breaks'}")
