"""Unit + stress tests for ``matriz_client._token_store.TokenStore``.

Coverage targets (Plan 10-01 D-07: +20 tests across Plan 10-01):

- U1-U7: single caller, thundering herd sync/async, multi-loop, event-loop
  budget, ``TokenSnapshot`` shape.
- S1, S2: 3-way concurrent stress (50 sync + 50 async + 5 daemon), P95 cached
  read latency.
- F1, F2: ``build_token_store`` factory hardcoded TTL + composition.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import statistics
import threading
import time

import httpx
import pytest

from matriz_client._state import _ClientState
from matriz_client._token_store import (
    TokenSnapshot,
    TokenStore,
    build_token_store,
)

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------


def _make_counting_refresh(
    *, delay_s: float = 0.0, lock: threading.Lock | None = None
) -> tuple[object, threading.Lock]:
    """Return a refresh_fn closure and the lock that guards its counter.

    The returned callable: ``refresh(cid: int) -> str`` increments ``count``
    and returns ``f"TOKEN-{count}"`` (NOT ``f"TOKEN-{cid}"`` — the test
    matrix asserts on call sequence, not call id).
    """
    actual_lock = lock or threading.Lock()
    counter = {"n": 0}

    def refresh(cid: int) -> str:
        if delay_s > 0:
            time.sleep(delay_s)
        with actual_lock:
            counter["n"] += 1
            return f"TOKEN-{counter['n']}"

    refresh.counter = counter  # type: ignore[attr-defined]
    return refresh, actual_lock


# ----------------------------------------------------------------------------
# U1 — single caller refresh once
# ----------------------------------------------------------------------------


def test_u1_single_caller_refresh_once() -> None:
    refresh, _ = _make_counting_refresh()
    store = TokenStore(ttl_seconds=10, refresh_fn=refresh)  # type: ignore[arg-type]
    snap = store.get_sync()
    assert isinstance(snap, TokenSnapshot)
    assert snap.value == "TOKEN-1"
    assert snap.refresh_call_id == 1
    # Within TTL — no additional refresh.
    snap2 = store.get_sync()
    assert snap2.value == "TOKEN-1"
    assert snap2.refresh_call_id == 1
    assert refresh.counter["n"] == 1  # type: ignore[attr-defined]


# ----------------------------------------------------------------------------
# U2 — TTL expiration triggers fresh refresh
# ----------------------------------------------------------------------------


def test_u2_ttl_expiry_triggers_fresh_refresh(monkeypatch: pytest.MonkeyPatch) -> None:
    refresh, _ = _make_counting_refresh()
    store = TokenStore(ttl_seconds=10, refresh_fn=refresh)  # type: ignore[arg-type]

    # Fake monotonic clock — advance past TTL between calls.
    clock = {"t": 1000.0}

    def fake_monotonic() -> float:
        return clock["t"]

    monkeypatch.setattr("matriz_client._token_store.time.monotonic", fake_monotonic)

    snap1 = store.get_sync()
    assert snap1.refresh_call_id == 1

    clock["t"] += 11.0  # > ttl_seconds (10)
    snap2 = store.get_sync()
    assert snap2.refresh_call_id == 2
    assert snap2.value == "TOKEN-2"


# ----------------------------------------------------------------------------
# U3 — thundering herd sync
# ----------------------------------------------------------------------------


def test_u3_thundering_herd_sync_yields_exactly_one_refresh() -> None:
    """10 sync threads concurrent → exactly 1 refresh; all see same token."""
    refresh, _ = _make_counting_refresh(delay_s=0.05)
    store = TokenStore(ttl_seconds=10, refresh_fn=refresh)  # type: ignore[arg-type]
    barrier = threading.Barrier(10)
    results: list[str] = []
    results_lock = threading.Lock()

    def worker() -> None:
        barrier.wait()
        snap = store.get_sync()
        with results_lock:
            results.append(snap.value)

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        list(ex.map(lambda _: worker(), range(10)))

    assert len(results) == 10
    assert len(set(results)) == 1
    assert results[0] == "TOKEN-1"
    assert refresh.counter["n"] == 1  # type: ignore[attr-defined]


# ----------------------------------------------------------------------------
# U4 — thundering herd async (single event loop)
# ----------------------------------------------------------------------------


async def test_u4_thundering_herd_async_yields_exactly_one_refresh() -> None:
    refresh, _ = _make_counting_refresh(delay_s=0.05)
    store = TokenStore(ttl_seconds=10, refresh_fn=refresh)  # type: ignore[arg-type]

    async def caller() -> str:
        snap = await store.get_async()
        return snap.value

    results = await asyncio.gather(*(caller() for _ in range(10)))
    assert len(set(results)) == 1
    assert results[0] == "TOKEN-1"
    assert refresh.counter["n"] == 1  # type: ignore[attr-defined]


# ----------------------------------------------------------------------------
# U5 — multi-event-loop reuses cached token
# ----------------------------------------------------------------------------


def test_u5_multiple_sequential_loops_reuse_cached_token() -> None:
    """Two sequential ``asyncio.run`` invocations reuse the cached token."""
    refresh, _ = _make_counting_refresh()
    store = TokenStore(ttl_seconds=10, refresh_fn=refresh)  # type: ignore[arg-type]

    async def run_once() -> TokenSnapshot:
        return await store.get_async()

    snap1 = asyncio.run(run_once())
    snap2 = asyncio.run(run_once())
    assert snap1.value == snap2.value == "TOKEN-1"
    assert refresh.counter["n"] == 1  # type: ignore[attr-defined]
    # Each loop registered its own asyncio.Lock entry (D-05 accept).
    assert len(store._async_locks) >= 1


# ----------------------------------------------------------------------------
# U6 — event loop unblocked during refresh (asyncio.to_thread offload)
# ----------------------------------------------------------------------------


async def test_u6_event_loop_not_blocked_during_refresh() -> None:
    """100ms blocking refresh must NOT block the event loop > 5ms.

    Tracks the longest gap between heartbeats on the loop. With
    ``asyncio.to_thread`` offload, the gap stays well under the 100ms
    refresh duration.
    """
    refresh, _ = _make_counting_refresh(delay_s=0.1)
    store = TokenStore(ttl_seconds=10, refresh_fn=refresh)  # type: ignore[arg-type]

    max_gap_ms = {"v": 0.0}
    stop_heartbeat = asyncio.Event()

    async def heartbeat() -> None:
        last = time.monotonic()
        while not stop_heartbeat.is_set():
            await asyncio.sleep(0.001)
            now = time.monotonic()
            gap_ms = (now - last) * 1000.0
            if gap_ms > max_gap_ms["v"]:
                max_gap_ms["v"] = gap_ms
            last = now

    hb_task = asyncio.create_task(heartbeat())
    snap = await store.get_async()
    stop_heartbeat.set()
    await hb_task

    assert snap.value == "TOKEN-1"
    # Loop should keep ticking — gap < refresh duration (100ms).
    # Spike measured < 5ms; allow 50ms slack for CI noise.
    assert max_gap_ms["v"] < 50.0, f"event loop blocked for {max_gap_ms['v']:.1f}ms"


# ----------------------------------------------------------------------------
# U7 — TokenSnapshot shape
# ----------------------------------------------------------------------------


def test_u7_token_snapshot_has_value_refreshed_at_and_call_id() -> None:
    snap = TokenSnapshot(value="tok", refreshed_at=1.5, refresh_call_id=3)
    assert snap.value == "tok"
    assert snap.refreshed_at == 1.5
    assert snap.refresh_call_id == 3
    # frozen=True means setattr raises.
    with pytest.raises(AttributeError):
        snap.value = "other"  # type: ignore[misc]


# ----------------------------------------------------------------------------
# S1 — 3-way concurrent stress (50 sync + 50 async + 5 daemon threads)
# ----------------------------------------------------------------------------


def test_3way_concurrent_sync_async_daemon() -> None:
    """50 sync threads + 50 async coroutines + 5 daemon threads → exactly 1 refresh.

    Mirrors Spike 002 (trimmed from 205 to 105 callers for CI speed).
    """
    refresh, _ = _make_counting_refresh(delay_s=0.05)
    store = TokenStore(ttl_seconds=10, refresh_fn=refresh)  # type: ignore[arg-type]

    n_sync = 50
    n_async = 50
    n_daemon = 5
    total = n_sync + n_async + n_daemon

    barrier = threading.Barrier(total)
    results: list[str] = []
    results_lock = threading.Lock()

    def sync_worker() -> None:
        barrier.wait()
        snap = store.get_sync()
        with results_lock:
            results.append(snap.value)

    def daemon_worker() -> None:
        barrier.wait()
        snap = store.get_sync()
        with results_lock:
            results.append(snap.value)

    def async_runner() -> None:
        async def gather_caller() -> None:
            barrier.wait()
            snap = await store.get_async()
            with results_lock:
                results.append(snap.value)

        asyncio.run(gather_caller())

    # Spawn sync threads.
    sync_threads = [threading.Thread(target=sync_worker) for _ in range(n_sync)]
    # Spawn async threads (each carries its own event loop).
    async_threads = [threading.Thread(target=async_runner) for _ in range(n_async)]
    # Spawn daemon threads.
    daemon_threads = [threading.Thread(target=daemon_worker, daemon=True) for _ in range(n_daemon)]

    for t in sync_threads + async_threads + daemon_threads:
        t.start()
    for t in sync_threads + async_threads:
        t.join(timeout=10.0)
    # Daemons may still be waiting on barrier — join with timeout.
    for t in daemon_threads:
        t.join(timeout=10.0)

    assert len(results) == total
    assert len(set(results)) == 1, f"divergent tokens: {set(results)}"
    assert results[0] == "TOKEN-1"
    assert refresh.counter["n"] == 1, refresh.counter["n"]  # type: ignore[attr-defined]


# ----------------------------------------------------------------------------
# S2 — P95 cached read latency sanity bound
# ----------------------------------------------------------------------------


def test_s2_p95_cached_read_latency_under_5ms() -> None:
    """After warmup, 100 sequential cached reads complete with P95 < 5ms.

    Spike measured < 0.01ms; the 5ms bound here is a generous CI noise floor.
    """
    refresh, _ = _make_counting_refresh()
    store = TokenStore(ttl_seconds=10, refresh_fn=refresh)  # type: ignore[arg-type]
    # Warmup — populate the cache.
    store.get_sync()

    durations_ms: list[float] = []
    for _ in range(100):
        t0 = time.perf_counter()
        store.get_sync()
        durations_ms.append((time.perf_counter() - t0) * 1000.0)

    p95 = statistics.quantiles(durations_ms, n=20)[18]  # 95th percentile.
    assert p95 < 5.0, f"P95 cached read latency {p95:.3f}ms exceeds 5ms"
    assert refresh.counter["n"] == 1  # type: ignore[attr-defined]


# ----------------------------------------------------------------------------
# Factory tests (F1, F2)
# ----------------------------------------------------------------------------


def test_f1_build_token_store_returns_token_store_instance() -> None:
    """``build_token_store`` returns a ``TokenStore`` without performing a refresh."""
    state = _ClientState()
    state.base_url = "https://api.test"
    state.username = "u"
    state.password = "p"
    state.http_client = httpx.Client()
    try:
        ts = build_token_store(state, max_retries=2)
        assert isinstance(ts, TokenStore)
        # No refresh performed on construction — token cache is empty.
        assert ts._token is None
    finally:
        assert isinstance(state.http_client, httpx.Client)
        state.http_client.close()


def test_f2_build_token_store_uses_hardcoded_matriz_ttl() -> None:
    """``build_token_store`` hardcodes ``ttl_seconds = 23 * 3600`` per D-04."""
    state = _ClientState()
    state.base_url = "https://api.test"
    state.username = "u"
    state.password = "p"
    state.http_client = httpx.Client()
    try:
        ts = build_token_store(state, max_retries=2)
        assert ts._ttl == 23 * 3600
    finally:
        assert isinstance(state.http_client, httpx.Client)
        state.http_client.close()


# ----------------------------------------------------------------------------
# Importability smoke test
# ----------------------------------------------------------------------------


def test_module_importable_without_raising() -> None:
    """The 3 public names import cleanly from ``matriz_client._token_store``."""
    from matriz_client._token_store import (
        TokenSnapshot as _TokenSnapshot,
    )
    from matriz_client._token_store import (
        TokenStore as _TokenStore,
    )
    from matriz_client._token_store import (
        build_token_store as _build_token_store,
    )

    assert _TokenSnapshot is not None
    assert _TokenStore is not None
    assert _build_token_store is not None


# ----------------------------------------------------------------------------
# Invalidate API
# ----------------------------------------------------------------------------


def test_invalidate_forces_next_get_sync_to_refresh() -> None:
    refresh, _ = _make_counting_refresh()
    store = TokenStore(ttl_seconds=10, refresh_fn=refresh)  # type: ignore[arg-type]
    snap1 = store.get_sync()
    assert snap1.refresh_call_id == 1
    store.invalidate()
    snap2 = store.get_sync()
    assert snap2.refresh_call_id == 2
    assert snap2.value == "TOKEN-2"
