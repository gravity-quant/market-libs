"""Integration: RefreshPolicy + TokenStoreDCL (winner from 001c).

The Phase 10 deliverable composes these:
    wrapped_refresh = RefreshPolicy(...).wrap(raw_refresh)
    store = TokenStoreDCL(ttl_seconds=23*3600, refresh_fn=wrapped_refresh)

Tests verify the policy's behavior survives intact when called from inside
TokenStore's lock — i.e., that fail-cache prevents thundering-herd from being
amplified by TokenStore's lock-and-retry behavior.
"""

from __future__ import annotations

import asyncio
import threading
from collections import deque

from errors import PermanentRefreshError, TransientRefreshError
from policy import RefreshPolicy
from store import TokenStoreDCL


class FakeSleep:
    def __init__(self) -> None:
        self.calls: list[float] = []

    def __call__(self, duration: float) -> None:
        self.calls.append(duration)


def make_scripted(*outcomes):
    q = deque(outcomes)
    log: list[tuple[int, str]] = []

    def refresh(call_id: int) -> str:
        outcome = q.popleft()
        log.append((call_id, str(outcome)))
        if outcome == "ok":
            return f"tok-{call_id}"
        if outcome == "transient":
            raise TransientRefreshError(f"500 (call {call_id})")
        if outcome == "perm":
            raise PermanentRefreshError(f"401 (call {call_id})")
        raise AssertionError(outcome)

    refresh.log = log  # type: ignore[attr-defined]
    return refresh


def test_happy_path_sync():
    sleep = FakeSleep()
    policy = RefreshPolicy(max_retries=3, sleep_fn=sleep)
    refresh = make_scripted("ok")
    store = TokenStoreDCL(ttl=10.0, refresh_fn=policy.wrap(refresh))
    snap = store.get_sync()
    assert snap.value == "tok-1"
    assert store.stats()["refresh_count"] == 1
    print("✓ happy_path_sync: TokenStore + policy = 1 refresh, returns token")


def test_transient_then_success_sync():
    sleep = FakeSleep()
    policy = RefreshPolicy(max_retries=3, base_backoff_s=1.0, jitter=0.0, sleep_fn=sleep)
    refresh = make_scripted("transient", "ok")
    store = TokenStoreDCL(ttl=10.0, refresh_fn=policy.wrap(refresh))
    snap = store.get_sync()
    # Policy preserves call_id through retries (call_id is from TokenStore's
    # perspective, not policy's). So both underlying calls had call_id=1.
    assert snap.value == "tok-1"
    # TokenStore's refresh_count is incremented once per call to the WRAPPED refresh,
    # not per retry. So we should see refresh_count=1 (the wrapped call), and
    # the underlying refresh was called twice (1 transient + 1 ok).
    assert store.stats()["refresh_count"] == 1
    assert len(refresh.log) == 2
    assert sleep.calls == [1.0]
    print(
        f"✓ transient_then_success_sync: policy retried inside lock; "
        f"TokenStore saw 1 successful refresh"
    )


def test_permanent_propagates_through_store():
    sleep = FakeSleep()
    policy = RefreshPolicy(max_retries=3, sleep_fn=sleep)
    refresh = make_scripted("perm")
    store = TokenStoreDCL(ttl=10.0, refresh_fn=policy.wrap(refresh))
    try:
        store.get_sync()
        raise AssertionError("expected PermanentRefreshError")
    except PermanentRefreshError:
        pass
    # Important: TokenStore's refresh_count IS incremented because
    # _do_refresh_if_needed runs _refresh_count += 1 BEFORE calling refresh_fn.
    # This is fine — the count is "attempts at refresh", not "successful refreshes".
    assert store.stats()["refresh_count"] == 1
    print("✓ permanent_propagates: PermanentRefreshError surfaces to caller")


def test_fail_cache_protects_against_thundering_after_failure():
    """The scenario this whole spike is about:
       - First caller triggers refresh that exhausts retries
       - Subsequent N callers should NOT all hit the auth server
       - They should get the cached error immediately
    """
    sleep = FakeSleep()
    policy = RefreshPolicy(
        max_retries=2, base_backoff_s=0.0, jitter=0.0, fail_cache_s=60.0, sleep_fn=sleep
    )
    refresh = make_scripted("transient", "transient", "transient")
    store = TokenStoreDCL(ttl=0.001, refresh_fn=policy.wrap(refresh))  # TTL effectively 0 — always refresh

    # First call: 3 attempts → fail
    try:
        store.get_sync()
        raise AssertionError
    except TransientRefreshError:
        pass
    assert len(refresh.log) == 3
    assert policy.stats()["fail_cache_active"]

    # Now 10 concurrent callers — all should get the cached error WITHOUT new refresh attempts
    results: list[Exception | str] = []
    results_lock = threading.Lock()

    def worker(i: int):
        try:
            snap = store.get_sync()
            with results_lock:
                results.append(snap.value)
        except Exception as e:
            with results_lock:
                results.append(e)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # No new refresh calls — fail-cache held
    assert len(refresh.log) == 3, f"expected 3 (no new), got {len(refresh.log)}"
    transient_count = sum(1 for r in results if isinstance(r, TransientRefreshError))
    assert transient_count == 10, results
    assert policy.stats()["fail_cache_hits"] == 10
    print(
        "✓ fail_cache_protects_against_thundering: 10 sync callers post-failure → 10 cached errors, "
        "0 new auth server calls"
    )


def test_async_caller_path_works_with_policy():
    """Verify the async path still flows correctly with the policy."""
    sleep = FakeSleep()
    policy = RefreshPolicy(max_retries=3, base_backoff_s=0.0, jitter=0.0, sleep_fn=sleep)
    refresh = make_scripted("transient", "ok")
    store = TokenStoreDCL(ttl=10.0, refresh_fn=policy.wrap(refresh))

    async def run():
        return await store.get_async()

    snap = asyncio.run(run())
    assert snap.value == "tok-1"  # call_id preserved through retry
    assert len(refresh.log) == 2  # 1 transient + 1 ok
    print("✓ async_caller_path_works_with_policy: 1 transient + retry succeeds via to_thread")


def test_recovery_after_fail_cache_expires():
    """After the fail-cache window, the next caller can succeed."""
    sleep = FakeSleep()
    policy = RefreshPolicy(
        max_retries=1, base_backoff_s=0.0, jitter=0.0, fail_cache_s=5.0, sleep_fn=sleep
    )
    refresh = make_scripted("transient", "transient", "ok")  # 2 failures then ok
    store = TokenStoreDCL(ttl=0.001, refresh_fn=policy.wrap(refresh))

    # First call: fails (1 attempt + 1 retry = 2 attempts, both transient)
    try:
        store.get_sync()
        raise AssertionError
    except TransientRefreshError:
        pass
    assert len(refresh.log) == 2

    # Expire the fail-cache by monkey-patching the timestamp
    import time

    with policy._lock:
        policy._cached_failure_at = time.monotonic() - 100.0

    # Now the next call should re-attempt — and since the scripted refresh has "ok"
    # left in the queue, it succeeds. TokenStore's _refresh_count is now 2 (this is
    # the 2nd time TokenStore called the wrapped refresh).
    snap = store.get_sync()
    assert snap.value == "tok-2", snap.value
    assert len(refresh.log) == 3, refresh.log
    print("✓ recovery_after_fail_cache_expires: post-window call succeeds → store has valid token")


def test_3way_with_policy_under_failure():
    """3-way integration: sync + async + daemon all hit a refresh that fails twice
    then succeeds. The policy retries; the TokenStore lock prevents concurrent
    retry sequences.
    """
    sleep = FakeSleep()
    policy = RefreshPolicy(
        max_retries=3, base_backoff_s=0.0, jitter=0.0, sleep_fn=sleep
    )
    # Scripted: first refresh sequence sees transient → ok (so 2 underlying calls).
    # Second caller hits the cache from TokenStore — they don't trigger refresh.
    refresh = make_scripted("transient", "ok")
    store = TokenStoreDCL(ttl=10.0, refresh_fn=policy.wrap(refresh))

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

    t_sync = threading.Thread(target=sync_worker, name="Sync")
    t_daemon = threading.Thread(target=daemon_worker, name="Daemon", daemon=True)
    t_async = threading.Thread(target=async_runner, name="Async")
    t_sync.start()
    t_daemon.start()
    t_async.start()
    t_sync.join()
    t_async.join()
    t_daemon.join()

    tokens = {results["sync"], results["daemon"], results["async"]}
    assert len(tokens) == 1, tokens
    # Underlying refresh called 2 times (1 transient + 1 ok); TokenStore lock prevented
    # the other 2 contexts from triggering a separate retry sequence
    assert len(refresh.log) == 2, refresh.log  # type: ignore[attr-defined]
    print(
        f"✓ 3way_with_policy_under_failure: 1 retry sequence, 3 contexts got same token = "
        f"{next(iter(tokens))}"
    )


if __name__ == "__main__":
    test_happy_path_sync()
    test_transient_then_success_sync()
    test_permanent_propagates_through_store()
    test_fail_cache_protects_against_thundering_after_failure()
    test_async_caller_path_works_with_policy()
    test_recovery_after_fail_cache_expires()
    test_3way_with_policy_under_failure()
    print()
    print("=== RefreshPolicy + TokenStore integration: ALL PASS ===")
