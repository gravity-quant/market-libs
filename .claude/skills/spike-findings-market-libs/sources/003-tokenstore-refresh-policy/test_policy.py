"""Test RefreshPolicy in isolation (no TokenStore yet)."""

from __future__ import annotations

import threading
from collections import deque
from typing import Callable

from errors import (
    PermanentRefreshError,
    RateLimitedRefreshError,
    TransientRefreshError,
)
from policy import RefreshPolicy


# Mock sleep to make tests fast — record durations instead of actually sleeping
class FakeSleep:
    def __init__(self) -> None:
        self.calls: list[float] = []
        self.cumulative: float = 0.0

    def __call__(self, duration: float) -> None:
        self.calls.append(duration)
        self.cumulative += duration


def make_scripted_refresh(*outcomes) -> Callable[[int], str]:
    """outcomes: tuple of ("ok", "transient", "perm", "rate", ("rate", seconds))
    Each call_id consumes one outcome from the deque.
    """
    q = deque(outcomes)
    call_log: list[tuple[int, str]] = []

    def refresh(call_id: int) -> str:
        outcome = q.popleft()
        call_log.append((call_id, str(outcome)))
        if isinstance(outcome, tuple) and outcome[0] == "rate":
            raise RateLimitedRefreshError(f"429 (call {call_id})", retry_after_seconds=outcome[1])
        if outcome == "ok":
            return f"tok-{call_id}"
        if outcome == "transient":
            raise TransientRefreshError(f"500 (call {call_id})")
        if outcome == "perm":
            raise PermanentRefreshError(f"401 (call {call_id})")
        raise AssertionError(f"unknown outcome: {outcome}")

    refresh.log = call_log  # type: ignore[attr-defined]
    return refresh


def test_happy_path_no_retry():
    sleep = FakeSleep()
    policy = RefreshPolicy(max_retries=3, sleep_fn=sleep)
    wrapped = policy.wrap(make_scripted_refresh("ok"))
    assert wrapped(1) == "tok-1"
    assert sleep.calls == []
    assert policy.stats()["attempts"] == 1
    assert policy.stats()["retries"] == 0
    print("✓ happy_path_no_retry: 1 attempt, 0 retries, 0 sleep calls")


def test_transient_then_success():
    sleep = FakeSleep()
    policy = RefreshPolicy(max_retries=3, base_backoff_s=1.0, jitter=0.0, sleep_fn=sleep)
    wrapped = policy.wrap(make_scripted_refresh("transient", "ok"))
    assert wrapped(1) == "tok-1"
    assert len(sleep.calls) == 1
    assert sleep.calls[0] == 1.0  # base backoff, attempt 0
    assert policy.stats()["attempts"] == 2
    assert policy.stats()["retries"] == 1
    print(f"✓ transient_then_success: 1 retry, backoff={sleep.calls[0]:.1f}s")


def test_permanent_no_retry():
    sleep = FakeSleep()
    policy = RefreshPolicy(max_retries=3, sleep_fn=sleep)
    wrapped = policy.wrap(make_scripted_refresh("perm", "ok"))  # second "ok" should never be reached
    try:
        wrapped(1)
        assert False, "expected PermanentRefreshError"
    except PermanentRefreshError:
        pass
    assert sleep.calls == []
    assert policy.stats()["attempts"] == 1
    assert policy.stats()["retries"] == 0
    assert not policy.stats()["fail_cache_active"]  # permanent does NOT fail-cache
    print("✓ permanent_no_retry: raises immediately, no retry, no fail-cache")


def test_exp_backoff_growth():
    sleep = FakeSleep()
    policy = RefreshPolicy(
        max_retries=3, base_backoff_s=1.0, max_backoff_s=100.0, jitter=0.0, sleep_fn=sleep
    )
    wrapped = policy.wrap(make_scripted_refresh("transient", "transient", "transient", "ok"))
    assert wrapped(1) == "tok-1"
    # attempts: 0, 1, 2 → backoffs: 1.0, 2.0, 4.0
    assert sleep.calls == [1.0, 2.0, 4.0], sleep.calls
    print(f"✓ exp_backoff_growth: {sleep.calls}")


def test_exp_backoff_capped():
    sleep = FakeSleep()
    policy = RefreshPolicy(
        max_retries=5, base_backoff_s=10.0, max_backoff_s=15.0, jitter=0.0, sleep_fn=sleep
    )
    wrapped = policy.wrap(make_scripted_refresh("transient", "transient", "transient", "ok"))
    wrapped(1)
    # attempts: 0, 1, 2 → uncapped 10, 20, 40 → capped 10, 15, 15
    assert sleep.calls == [10.0, 15.0, 15.0], sleep.calls
    print(f"✓ exp_backoff_capped: {sleep.calls}")


def test_rate_limited_uses_retry_after():
    sleep = FakeSleep()
    policy = RefreshPolicy(
        max_retries=3, base_backoff_s=1.0, jitter=0.0, sleep_fn=sleep
    )
    wrapped = policy.wrap(make_scripted_refresh(("rate", 7.5), "ok"))
    wrapped(1)
    assert sleep.calls == [7.5], sleep.calls
    print("✓ rate_limited_uses_retry_after: backoff=7.5s (from server hint)")


def test_exhausted_retries_then_fail_cache():
    sleep = FakeSleep()
    policy = RefreshPolicy(
        max_retries=2, base_backoff_s=1.0, jitter=0.0, fail_cache_s=30.0, sleep_fn=sleep
    )
    refresh = make_scripted_refresh("transient", "transient", "transient")
    wrapped = policy.wrap(refresh)
    try:
        wrapped(1)
        assert False, "expected TransientRefreshError"
    except TransientRefreshError:
        pass
    # 3 attempts, 2 backoffs
    assert policy.stats()["attempts"] == 3
    assert policy.stats()["retries"] == 2
    assert policy.stats()["fail_cache_active"]
    # Fail-cache: next call should raise immediately without invoking refresh_fn
    try:
        wrapped(2)  # would consume nothing from the scripted refresh
        assert False, "expected cached TransientRefreshError"
    except TransientRefreshError:
        pass
    # Refresh was NOT called again (no new entry in log)
    assert len(refresh.log) == 3, refresh.log  # type: ignore[attr-defined]
    assert policy.stats()["attempts"] == 3  # unchanged — fail-cache short-circuited
    assert policy.stats()["fail_cache_hits"] == 1
    print(
        f"✓ exhausted_then_fail_cache: 3 attempts, 2 backoffs, "
        f"next call short-circuited (fail_cache_hits=1)"
    )


def test_fail_cache_expires_then_retry_succeeds():
    """Use FakeSleep to simulate the fail-cache window expiring."""
    sleep = FakeSleep()
    policy = RefreshPolicy(
        max_retries=1, base_backoff_s=0.0, jitter=0.0, fail_cache_s=5.0, sleep_fn=sleep
    )
    refresh = make_scripted_refresh("transient", "transient", "ok")
    wrapped = policy.wrap(refresh)
    try:
        wrapped(1)
        assert False
    except TransientRefreshError:
        pass
    # Now monkey-patch the policy's _cached_failure_at to simulate window expiry
    import time

    with policy._lock:
        assert policy._cached_failure_at is not None
        policy._cached_failure_at = time.monotonic() - 100.0  # >> fail_cache_s
    # Next call should re-attempt and succeed
    result = wrapped(2)
    assert result == "tok-2"
    print("✓ fail_cache_expires: after window, retry succeeds (refresh called again)")


def test_concurrent_callers_share_fail_cache():
    """Multiple threads hit the same wrapped policy after fail-cache is set.
    All should see the cached exception without re-calling refresh_fn.
    """
    sleep = FakeSleep()
    policy = RefreshPolicy(
        max_retries=1, base_backoff_s=0.0, jitter=0.0, fail_cache_s=30.0, sleep_fn=sleep
    )
    refresh = make_scripted_refresh("transient", "transient")
    wrapped = policy.wrap(refresh)
    # Initial failure populates the cache
    try:
        wrapped(0)
    except TransientRefreshError:
        pass
    base_call_count = len(refresh.log)  # type: ignore[attr-defined]
    assert base_call_count == 2

    # 10 threads hit concurrently — all should get the cached error
    results: list[Exception | str] = []
    results_lock = threading.Lock()

    def worker(i: int):
        try:
            r = wrapped(100 + i)
            with results_lock:
                results.append(r)
        except Exception as e:
            with results_lock:
                results.append(e)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # No new refresh calls — all got the cached error
    assert len(refresh.log) == base_call_count, refresh.log  # type: ignore[attr-defined]
    transient_count = sum(1 for r in results if isinstance(r, TransientRefreshError))
    assert transient_count == 10, results
    assert policy.stats()["fail_cache_hits"] == 10
    print(
        f"✓ concurrent_callers_share_fail_cache: 10 threads → 10 cached errors, "
        f"0 new refresh calls"
    )


if __name__ == "__main__":
    test_happy_path_no_retry()
    test_transient_then_success()
    test_permanent_no_retry()
    test_exp_backoff_growth()
    test_exp_backoff_capped()
    test_rate_limited_uses_retry_after()
    test_exhausted_retries_then_fail_cache()
    test_fail_cache_expires_then_retry_succeeds()
    test_concurrent_callers_share_fail_cache()
    print()
    print("=== RefreshPolicy isolation tests: ALL PASS ===")
