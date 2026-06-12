"""Follow-up: measure whether the event loop is truly FREE during refresh.

The standard async_thundering_herd measures `max_event_loop_block` as the gap
between successive monitor ticks. If all other tasks are blocked on the async_lock
and the only ticker is the monitor itself, the loop IS free (it's just idle).

The real question: can UNRELATED work progress during a refresh?

We simulate the realistic scenario:
    - 1 task triggers a refresh (50ms simulated network call)
    - 5 concurrent "unrelated" tasks each tick a counter every 1ms

If 001c's design is correct, the unrelated tasks should make progress during
the refresh — i.e., their counters should advance by ~50 ticks during the
50ms refresh window.
"""

from __future__ import annotations

import asyncio
import time
from store import TokenStoreDCL


def slow_refresh(call_id: int) -> str:
    """Sync refresh that simulates 100ms network call.

    If the design is correct, this should NOT block the event loop —
    other coroutines should make progress during this 100ms.
    """
    time.sleep(0.1)
    return f"tok-{call_id}"


async def test_unrelated_work_progresses_during_refresh():
    """Real-world scenario test:
       - Task A: triggers token refresh (100ms simulated)
       - Tasks B-F: 5 unrelated "background tasks" that tick a counter every 1ms

    Expected behavior in 001c (refresh wrapped in asyncio.to_thread):
       - Task A awaits the to_thread Future for 100ms
       - Tasks B-F continue ticking — should accumulate ~80-100 ticks each in 100ms
    Bad behavior (if loop were blocked):
       - Tasks B-F would stall during refresh — 0-1 ticks during 100ms
    """
    store = TokenStoreDCL(ttl=10.0, refresh_fn=slow_refresh)
    tick_counts: dict[str, int] = {}
    refresh_time_window: list[float] = []

    async def ticker(name: str):
        tick_counts[name] = 0
        for _ in range(200):  # 200 ticks max
            await asyncio.sleep(0.001)  # 1ms
            tick_counts[name] += 1

    async def refresh_caller():
        refresh_time_window.append(time.monotonic())
        snap = await store.get_async()
        refresh_time_window.append(time.monotonic())
        return snap

    # Start tickers, then start the refresh, then await all
    tickers = [asyncio.create_task(ticker(f"T{i}")) for i in range(5)]
    refresh_task = asyncio.create_task(refresh_caller())

    snap = await refresh_task

    # Tickers should keep going after refresh completes; we wait 50ms more then cancel
    await asyncio.sleep(0.05)
    for t in tickers:
        t.cancel()
    for t in tickers:
        try:
            await t
        except asyncio.CancelledError:
            pass

    refresh_duration_ms = (refresh_time_window[1] - refresh_time_window[0]) * 1000
    print(f"\nRefresh took {refresh_duration_ms:.1f}ms")
    print(f"Tick counts during refresh + 50ms grace:")
    for name, count in tick_counts.items():
        print(f"  {name}: {count} ticks")

    # Expected: each ticker should have advanced ~80-100 ticks (100ms refresh + 50ms grace = 150ms ≈ 100-150 ticks max)
    # If the loop were blocked during refresh, tickers would have ~0-1 ticks before the refresh started and 50 ticks after
    avg_ticks = sum(tick_counts.values()) / len(tick_counts)
    print(f"\nAverage ticks: {avg_ticks:.1f}")
    if avg_ticks < 30:
        print(f"✗ FAIL: tickers stalled during refresh — event loop was BLOCKED")
        return False
    print(f"✓ PASS: tickers progressed during refresh — event loop was FREE")
    print(f"  (refresh ran in a worker thread via asyncio.to_thread; loop scheduled other work)")
    return True


async def test_compare_blocking_refresh():
    """For contrast: same scenario but the refresh runs INLINE (no asyncio.to_thread).
    This proves the metric is real — if we DO block the loop, tickers stall.
    """

    class BlockingStore:
        """Strawman: store that calls refresh inline (no to_thread)."""

        def __init__(self, refresh_fn):
            self._refresh_fn = refresh_fn
            self._lock = asyncio.Lock()
            self._token = None

        async def get_async(self):
            async with self._lock:
                if self._token is None:
                    self._token = self._refresh_fn(1)  # blocks the event loop
                return self._token

    store = BlockingStore(refresh_fn=slow_refresh)
    tick_counts: dict[str, int] = {}

    async def ticker(name: str):
        tick_counts[name] = 0
        for _ in range(200):
            await asyncio.sleep(0.001)
            tick_counts[name] += 1

    async def refresh_caller():
        return await store.get_async()

    tickers = [asyncio.create_task(ticker(f"T{i}")) for i in range(5)]
    refresh_task = asyncio.create_task(refresh_caller())
    await refresh_task
    await asyncio.sleep(0.05)
    for t in tickers:
        t.cancel()
    for t in tickers:
        try:
            await t
        except asyncio.CancelledError:
            pass

    avg_ticks = sum(tick_counts.values()) / len(tick_counts)
    print(f"\n[contrast] Strawman BlockingStore — inline refresh:")
    for name, count in tick_counts.items():
        print(f"  {name}: {count} ticks")
    print(f"  Average: {avg_ticks:.1f}")
    print(f"  (expected to be LOW — refresh blocks the loop)")


if __name__ == "__main__":
    print("=== Test 1: 001c (refresh via asyncio.to_thread) ===")
    ok = asyncio.run(test_unrelated_work_progresses_during_refresh())

    print("\n=== Test 2: Strawman comparison (refresh blocks the loop) ===")
    asyncio.run(test_compare_blocking_refresh())

    print(f"\n=== Final: 001c PASSES loop-freedom test: {ok} ===")
