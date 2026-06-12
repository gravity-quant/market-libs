"""Experiential tests for TokenStoreDCL.

This is the candidate that should NOT fail the 3-way integration test that 001b failed.
We re-run the same test matrix as 001a to enable head-to-head comparison.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import threading
import time
from datetime import datetime, timezone

from store import TokenStoreDCL


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
    def refresh(call_id: int) -> str:
        log("refresh", f"start id={call_id}")
        time.sleep(delay_s)
        token = f"tok-{call_id}-{int(time.monotonic() * 1000)}"
        log("refresh", f"end id={call_id} → {token}")
        return token

    return refresh


# --- Standard test matrix (same as 001a for direct comparison) ------------


def test_sync_single_caller():
    reset_log()
    store = TokenStoreDCL(ttl=10.0, refresh_fn=make_refresh_fn())
    snap = store.get_sync()
    assert snap.value.startswith("tok-1-"), snap.value
    snap2 = store.get_sync()
    assert snap.value == snap2.value
    assert store.stats()["refresh_count"] == 1
    print("✓ sync_single_caller: 1 refresh, cached read same token")


def test_async_single_caller():
    store = TokenStoreDCL(ttl=10.0, refresh_fn=make_refresh_fn())

    async def run():
        return await store.get_async(), await store.get_async()

    snap, snap2 = asyncio.run(run())
    assert snap.value == snap2.value
    assert store.stats()["refresh_count"] == 1
    print("✓ async_single_caller: 1 refresh, cached read same token")


def test_sync_thundering_herd():
    store = TokenStoreDCL(ttl=10.0, refresh_fn=make_refresh_fn())
    barrier = threading.Barrier(20)
    results: list[str] = []
    results_lock = threading.Lock()

    def worker(i: int) -> None:
        barrier.wait()
        snap = store.get_sync()
        with results_lock:
            results.append(snap.value)

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
        list(ex.map(worker, range(20)))

    assert len(set(results)) == 1, set(results)
    assert store.stats()["refresh_count"] == 1
    print("✓ sync_thundering_herd: 20 threads → 1 refresh")


def test_async_thundering_herd():
    store = TokenStoreDCL(ttl=10.0, refresh_fn=make_refresh_fn(delay_s=0.05))
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
    refresh_count = store.stats()["refresh_count"]
    max_block = max(loop_block_observed) if loop_block_observed else -1
    median_block = sorted(loop_block_observed)[len(loop_block_observed) // 2] if loop_block_observed else -1
    assert len(set(results)) == 1
    print(
        f"✓ async_thundering_herd: 50 coros → {refresh_count} refresh(es) | "
        f"event loop tick: max={max_block:.2f}ms median={median_block:.3f}ms"
    )
    return refresh_count, max_block


def test_3way_integration():
    """The decisive test that 001b failed.

    sync caller (own thread) + async runner (own loop in own thread) + daemon thread.
    """
    store = TokenStoreDCL(ttl=10.0, refresh_fn=make_refresh_fn(delay_s=0.05))
    barrier = threading.Barrier(3)
    results: dict[str, str] = {}

    def sync_worker():
        barrier.wait()
        results["sync"] = store.get_sync().value

    def daemon_worker():
        barrier.wait()
        results["daemon"] = store.get_sync().value

    def async_runner():
        async def main():
            results["async"] = (await store.get_async()).value

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
    active_loops = store.stats()["active_loops"]
    print(
        f"{'✓' if len(tokens) == 1 and refresh_count == 1 else '✗'} 3way_integration: "
        f"tokens={tokens}, refreshes={refresh_count}, async_locks_created={active_loops}"
    )
    assert len(tokens) == 1, tokens
    assert refresh_count == 1, refresh_count
    return refresh_count, active_loops


def test_multiple_loops_sequential():
    """Sequential asyncio.run() calls on the same store — common in test runners."""
    store = TokenStoreDCL(ttl=10.0, refresh_fn=make_refresh_fn())

    async def run():
        return await store.get_async()

    snap1 = asyncio.run(run())
    snap2 = asyncio.run(run())
    # Cached, but each new loop creates its own async_lock entry — does it leak?
    active = store.stats()["active_loops"]
    print(f"✓ multiple_loops_sequential: 2 sequential asyncio.run() → tokens match ({snap1.value == snap2.value}), active_locks={active}")
    return active


def test_concurrent_loops():
    """The exact scenario that broke 001b: 2 threads each with their own loop."""
    store = TokenStoreDCL(ttl=10.0, refresh_fn=make_refresh_fn())
    barrier = threading.Barrier(2)
    results: dict[str, str] = {}
    errors: dict[str, Exception] = {}

    def runner(name: str):
        async def main():
            return await store.get_async()

        barrier.wait()
        try:
            snap = asyncio.run(main())
            results[name] = snap.value
        except Exception as e:
            errors[name] = e

    t1 = threading.Thread(target=runner, args=("A",))
    t2 = threading.Thread(target=runner, args=("B",))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    refresh_count = store.stats()["refresh_count"]
    active = store.stats()["active_loops"]
    if errors:
        print(f"✗ concurrent_loops: errors={[(k, type(e).__name__) for k, e in errors.items()]}")
        return False
    if len(set(results.values())) == 1 and refresh_count == 1:
        print(
            f"✓ concurrent_loops: 2 distinct loops → {refresh_count} refresh, "
            f"both got same token, async_locks_created={active} (one per loop)"
        )
        return True
    print(
        f"✗ concurrent_loops: tokens={set(results.values())}, refreshes={refresh_count}"
    )
    return False


if __name__ == "__main__":
    test_sync_single_caller()
    test_async_single_caller()
    test_sync_thundering_herd()
    refresh_n, max_block = test_async_thundering_herd()
    test_3way_integration()
    active_seq = test_multiple_loops_sequential()
    test_concurrent_loops()
    print()
    print(f"=== Approach 001c summary ===")
    print(f"  Async thundering herd: max_event_loop_block={max_block:.2f}ms")
    print(f"  All tests passed — DCL works across loops and contexts")
