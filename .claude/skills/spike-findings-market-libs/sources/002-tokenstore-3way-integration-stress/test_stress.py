"""Spike 002: stress test the winner (001c DCL) at realistic Phase 10 scale.

Scenario:
- 100 sync REST callers (concurrent threads, simulating high-throughput API usage)
- 100 async REST callers (concurrent coroutines on a single user-owned loop)
- 5 daemon threads simulating ws_client background work

All compete for `get_token()`. The token starts with a very short TTL — half the
callers fire BEFORE TTL expiry (cache hit), half fire AFTER (refresh path).

Measurements:
- Total refreshes (target: 1-2; ideally 1)
- Errors per context
- Wall-clock duration
- Per-call latency (P50, P95, P99) for cached reads
- Memory growth in _async_locks
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import statistics
import threading
import time
from store import TokenStoreDCL


REFRESH_DELAY_S = 0.05  # simulated network call


def make_refresh_fn():
    refresh_log: list[tuple[int, float, float]] = []
    refresh_log_lock = threading.Lock()

    def refresh(call_id: int) -> str:
        t0 = time.monotonic()
        time.sleep(REFRESH_DELAY_S)
        t1 = time.monotonic()
        with refresh_log_lock:
            refresh_log.append((call_id, t0, t1))
        return f"tok-{call_id}-{int(t1 * 1000)}"

    return refresh, refresh_log


def sync_caller(store: TokenStoreDCL, n: int, latencies: list[float]) -> str | None:
    """Simulate sync REST: call get_sync(), return token."""
    try:
        t0 = time.monotonic()
        snap = store.get_sync()
        t1 = time.monotonic()
        latencies.append((t1 - t0) * 1000)
        return snap.value
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"


def daemon_caller(store: TokenStoreDCL, latencies: list[float]) -> str | None:
    """Simulate ws_client daemon thread."""
    try:
        t0 = time.monotonic()
        snap = store.get_sync()
        t1 = time.monotonic()
        latencies.append((t1 - t0) * 1000)
        return snap.value
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"


async def async_caller(store: TokenStoreDCL, latencies: list[float]) -> str | None:
    """Simulate async REST coroutine."""
    try:
        t0 = time.monotonic()
        snap = await store.get_async()
        t1 = time.monotonic()
        latencies.append((t1 - t0) * 1000)
        return snap.value
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"


def main():
    print("=" * 70)
    print("Spike 002: TokenStore 3-way integration stress test")
    print("=" * 70)
    refresh_fn, refresh_log = make_refresh_fn()
    # TTL of 0.5s — long enough that the first batch hits cache,
    # short enough that after a brief delay we force expiry.
    store = TokenStoreDCL(ttl=0.5, refresh_fn=refresh_fn)

    sync_latencies: list[float] = []
    daemon_latencies: list[float] = []
    async_latencies: list[float] = []

    NUM_SYNC = 100
    NUM_ASYNC = 100
    NUM_DAEMON = 5

    barrier = threading.Barrier(2)  # main thread + async runner thread (sync workers run in pool)

    sync_results: list[str | None] = []
    daemon_results: list[str | None] = []
    async_results: list[str | None] = []

    sync_results_lock = threading.Lock()
    daemon_results_lock = threading.Lock()

    def run_sync_pool():
        """Run 100 sync callers concurrently via ThreadPoolExecutor."""
        with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_SYNC) as ex:
            futures = [ex.submit(sync_caller, store, i, sync_latencies) for i in range(NUM_SYNC)]
            for f in concurrent.futures.as_completed(futures):
                with sync_results_lock:
                    sync_results.append(f.result())

    def daemon_worker():
        result = daemon_caller(store, daemon_latencies)
        with daemon_results_lock:
            daemon_results.append(result)

    def run_daemon_threads():
        """Run 5 daemon-thread callers concurrently."""
        threads = [
            threading.Thread(target=daemon_worker, name=f"Daemon-{i}", daemon=True)
            for i in range(NUM_DAEMON)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    def run_async_runner():
        """Run 100 async callers in a single user-owned loop."""

        async def main():
            results = await asyncio.gather(
                *(async_caller(store, async_latencies) for _ in range(NUM_ASYNC))
            )
            return results

        results = asyncio.run(main())
        async_results.extend(results)

    print(f"\nPhase 1: cold start — {NUM_SYNC} sync + {NUM_ASYNC} async + {NUM_DAEMON} daemon all hit empty store")
    t_start = time.monotonic()

    # Launch all three workloads concurrently in different threads.
    t_sync = threading.Thread(target=run_sync_pool, name="SyncPoolDriver")
    t_daemon = threading.Thread(target=run_daemon_threads, name="DaemonDriver")
    t_async = threading.Thread(target=run_async_runner, name="AsyncDriver")
    t_sync.start()
    t_daemon.start()
    t_async.start()
    t_sync.join()
    t_async.join()
    t_daemon.join()

    duration_1 = time.monotonic() - t_start
    refresh_count_1 = store.stats()["refresh_count"]

    print(f"  Duration: {duration_1*1000:.1f}ms")
    print(f"  Refreshes: {refresh_count_1}")
    print(f"  Total callers: {len(sync_results) + len(async_results) + len(daemon_results)}")
    print(f"  Errors: {sum(1 for r in sync_results + async_results + daemon_results if r and r.startswith('ERROR'))}")

    # Print unique tokens — should all be the same after cold start refresh
    all_results = sync_results + async_results + daemon_results
    unique_tokens = {r for r in all_results if r and not r.startswith("ERROR")}
    print(f"  Unique tokens: {len(unique_tokens)}")
    if len(unique_tokens) == 1:
        print(f"  ✓ All {len(all_results)} callers got identical token")
    else:
        print(f"  ✗ {len(unique_tokens)} unique tokens — atomicity broken: {unique_tokens}")

    print(f"\nPhase 2: TTL expiry — wait 0.6s, then fire the same workload again")
    time.sleep(0.6)  # let TTL expire

    sync_latencies_2: list[float] = []
    async_latencies_2: list[float] = []
    daemon_latencies_2: list[float] = []
    sync_results_2: list[str | None] = []
    async_results_2: list[str | None] = []
    daemon_results_2: list[str | None] = []
    sync_results_2_lock = threading.Lock()
    daemon_results_2_lock = threading.Lock()

    def run_sync_pool_2():
        with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_SYNC) as ex:
            futures = [
                ex.submit(sync_caller, store, i, sync_latencies_2) for i in range(NUM_SYNC)
            ]
            for f in concurrent.futures.as_completed(futures):
                with sync_results_2_lock:
                    sync_results_2.append(f.result())

    def daemon_worker_2():
        result = daemon_caller(store, daemon_latencies_2)
        with daemon_results_2_lock:
            daemon_results_2.append(result)

    def run_daemon_threads_2():
        threads = [
            threading.Thread(target=daemon_worker_2, name=f"Daemon2-{i}", daemon=True)
            for i in range(NUM_DAEMON)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    def run_async_runner_2():
        async def main():
            return await asyncio.gather(
                *(async_caller(store, async_latencies_2) for _ in range(NUM_ASYNC))
            )

        async_results_2.extend(asyncio.run(main()))

    t_start_2 = time.monotonic()
    t_sync_2 = threading.Thread(target=run_sync_pool_2, name="SyncPoolDriver2")
    t_daemon_2 = threading.Thread(target=run_daemon_threads_2, name="DaemonDriver2")
    t_async_2 = threading.Thread(target=run_async_runner_2, name="AsyncDriver2")
    t_sync_2.start()
    t_daemon_2.start()
    t_async_2.start()
    t_sync_2.join()
    t_async_2.join()
    t_daemon_2.join()

    duration_2 = time.monotonic() - t_start_2
    refresh_count_2 = store.stats()["refresh_count"]
    refresh_delta = refresh_count_2 - refresh_count_1

    all_results_2 = sync_results_2 + async_results_2 + daemon_results_2
    unique_tokens_2 = {r for r in all_results_2 if r and not r.startswith("ERROR")}

    print(f"  Duration: {duration_2*1000:.1f}ms")
    print(f"  Refreshes in this phase: {refresh_delta}")
    print(f"  Total refreshes so far: {refresh_count_2}")
    print(f"  Errors: {sum(1 for r in all_results_2 if r and r.startswith('ERROR'))}")
    print(f"  Unique tokens in phase 2: {len(unique_tokens_2)}")

    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)

    def stats(name: str, lats: list[float]):
        if not lats:
            return
        lats_sorted = sorted(lats)
        p50 = lats_sorted[len(lats_sorted) // 2]
        p95 = lats_sorted[int(len(lats_sorted) * 0.95)]
        p99 = lats_sorted[int(len(lats_sorted) * 0.99)]
        print(f"  {name:25s} N={len(lats):4d}  P50={p50:.3f}ms  P95={p95:.3f}ms  P99={p99:.3f}ms  max={max(lats):.2f}ms")

    print("\nLatency — Phase 1 (cold start, includes 1 refresh ~50ms):")
    stats("  sync REST", sync_latencies)
    stats("  async REST", async_latencies)
    stats("  daemon thread", daemon_latencies)

    print("\nLatency — Phase 2 (after TTL expiry):")
    stats("  sync REST", sync_latencies_2)
    stats("  async REST", async_latencies_2)
    stats("  daemon thread", daemon_latencies_2)

    print(f"\nRefresh count: {refresh_count_2} total across 2 phases")
    print(f"  Phase 1: {refresh_count_1}")
    print(f"  Phase 2: {refresh_delta}")
    print(f"\nActive async_locks (one per asyncio.run loop): {store.stats()['active_loops']}")

    # Assert pass criteria
    print("\n" + "-" * 70)
    print("Pass criteria:")
    p1 = refresh_count_2 <= 4  # 2 phases × max 2 refreshes each (allow some slop)
    print(f"  {'✓' if p1 else '✗'} Total refreshes ≤ 4 (got {refresh_count_2})")

    total_errors = sum(
        1 for r in all_results + all_results_2 if r and r.startswith("ERROR")
    )
    p2 = total_errors == 0
    print(f"  {'✓' if p2 else '✗'} Zero errors (got {total_errors})")

    p3 = len(unique_tokens) == 1
    print(f"  {'✓' if p3 else '✗'} Phase 1 atomicity (1 unique token)")

    # Phase 2 atomicity: callers might get different tokens IF refresh happened during the wave
    # (some cache the old one before refresh, some get the new one). Acceptable as long as
    # all tokens are valid (i.e., from one of the actual refreshes).
    p4 = len(unique_tokens_2) <= 2
    print(f"  {'✓' if p4 else '✗'} Phase 2 atomicity (≤ 2 unique tokens; refresh may interleave with herd)")

    p5_target = 5.0
    if async_latencies_2:
        async_p95 = sorted(async_latencies_2)[int(len(async_latencies_2) * 0.95)]
        p5 = async_p95 < 100  # P95 for cached read should be << refresh time
        print(f"  {'✓' if p5 else '✗'} Async cached-read P95 < 100ms (got {async_p95:.2f}ms)")

    print("\n" + "=" * 70)
    overall = all([p1, p2, p3, p4])
    print(f"  Spike 002 verdict: {'VALIDATED ✓' if overall else 'PARTIAL ⚠'}")
    print("=" * 70)


if __name__ == "__main__":
    main()
