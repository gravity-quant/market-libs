"""Tests for ``RefreshPolicy`` + ``MatrizRefresh`` (Phase 10 Plan 10-01)."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable

import httpx
import pytest
from pytest_httpx import HTTPXMock

from matriz_client._refresh import MatrizRefresh
from matriz_client._refresh_errors import (
    PermanentRefreshError,
    RateLimitedRefreshError,
    RefreshError,
    TransientRefreshError,
)
from matriz_client._refresh_policy import RefreshPolicy

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------


def _make_scripted_refresh(*outcomes: object) -> Callable[[int], str]:
    """Build a refresh_fn that consumes ``outcomes`` in order.

    Outcome values:
    - ``"ok"`` → returns ``f"tok-{call_id}"``
    - ``"transient"`` → raises ``TransientRefreshError``
    - ``"perm"`` → raises ``PermanentRefreshError``
    - ``("rate", retry_after_s)`` → raises ``RateLimitedRefreshError``
    """
    q: deque[object] = deque(outcomes)
    call_log: list[int] = []

    def refresh(call_id: int) -> str:
        call_log.append(call_id)
        outcome = q.popleft()
        if isinstance(outcome, tuple) and outcome[0] == "rate":
            raise RateLimitedRefreshError(
                f"429 (call {call_id})", retry_after_seconds=float(outcome[1])
            )
        if outcome == "ok":
            return f"tok-{call_id}"
        if outcome == "transient":
            raise TransientRefreshError(f"503 (call {call_id})")
        if outcome == "perm":
            raise PermanentRefreshError(f"401 (call {call_id})")
        raise AssertionError(f"unknown outcome: {outcome!r}")

    refresh.log = call_log  # type: ignore[attr-defined]
    return refresh


def _record_sleeps() -> tuple[Callable[[float], None], list[float]]:
    """Return a ``(sleep_fn, sleeps)`` pair that records durations w/o sleeping."""
    sleeps: list[float] = []

    def sleep_fn(seconds: float) -> None:
        sleeps.append(seconds)

    return sleep_fn, sleeps


# ----------------------------------------------------------------------------
# RefreshPolicy tests (P1-P8)
# ----------------------------------------------------------------------------


def test_p1_wrap_returns_callable_with_call_id_signature() -> None:
    """``RefreshPolicy.wrap`` returns a ``(int) -> str`` callable."""
    sleep_fn, _ = _record_sleeps()
    policy = RefreshPolicy(max_retries=3, sleep_fn=sleep_fn)
    wrapped = policy.wrap(_make_scripted_refresh("ok"))
    assert callable(wrapped)
    assert wrapped(42) == "tok-42"


def test_p2_permanent_propagates_immediately_no_retry_no_sleep() -> None:
    """``PermanentRefreshError`` → no retry, no sleep, no fail-cache."""
    sleep_fn, sleeps = _record_sleeps()
    policy = RefreshPolicy(max_retries=3, sleep_fn=sleep_fn)
    refresh = _make_scripted_refresh("perm", "ok")  # "ok" never reached
    wrapped = policy.wrap(refresh)
    with pytest.raises(PermanentRefreshError):
        wrapped(1)
    assert sleeps == []
    assert refresh.log == [1]  # type: ignore[attr-defined]
    # Subsequent call must reach refresh_fn — fail-cache did NOT activate for
    # permanent errors (operator can fix creds and retry without waiting).
    assert wrapped(2) == "tok-2"
    assert refresh.log == [1, 2]  # type: ignore[attr-defined]


def test_p3_transient_retries_with_exponential_backoff() -> None:
    """``TransientRefreshError`` retries with exp backoff envelope."""
    sleep_fn, sleeps = _record_sleeps()
    policy = RefreshPolicy(
        max_retries=3,
        base_backoff_s=1.0,
        max_backoff_s=100.0,
        jitter=0.0,
        sleep_fn=sleep_fn,
    )
    refresh = _make_scripted_refresh("transient", "transient", "transient", "ok")
    wrapped = policy.wrap(refresh)
    assert wrapped(1) == "tok-1"
    # attempts 0, 1, 2 → backoffs 1.0, 2.0, 4.0 (no jitter).
    assert sleeps == [1.0, 2.0, 4.0]
    assert refresh.log == [1, 1, 1, 1]  # type: ignore[attr-defined]


def test_p4_rate_limited_honors_retry_after_seconds() -> None:
    """``RateLimitedRefreshError`` uses ``retry_after_seconds`` for the next sleep."""
    sleep_fn, sleeps = _record_sleeps()
    policy = RefreshPolicy(
        max_retries=3,
        base_backoff_s=1.0,
        max_backoff_s=30.0,
        jitter=0.0,
        sleep_fn=sleep_fn,
    )
    refresh = _make_scripted_refresh(("rate", 7.5), "ok")
    wrapped = policy.wrap(refresh)
    assert wrapped(1) == "tok-1"
    assert sleeps == [7.5]


def test_p4b_rate_limited_capped_at_max_backoff() -> None:
    """``RateLimitedRefreshError`` retry_after is capped at ``max_backoff_s``."""
    sleep_fn, sleeps = _record_sleeps()
    policy = RefreshPolicy(
        max_retries=2,
        base_backoff_s=1.0,
        max_backoff_s=10.0,
        jitter=0.0,
        sleep_fn=sleep_fn,
    )
    refresh = _make_scripted_refresh(("rate", 999.0), "ok")
    wrapped = policy.wrap(refresh)
    wrapped(1)
    assert sleeps == [10.0]  # capped


def test_p5_exhausted_retries_then_fail_cache_short_circuits() -> None:
    """After exhausting retries, subsequent callers hit the fail-cache."""
    sleep_fn, _ = _record_sleeps()
    policy = RefreshPolicy(
        max_retries=2,
        base_backoff_s=1.0,
        max_backoff_s=10.0,
        jitter=0.0,
        fail_cache_s=30.0,
        sleep_fn=sleep_fn,
    )
    # 3 transients → max_retries=2 means attempts 0, 1, 2 — total 3 — exhausted.
    refresh = _make_scripted_refresh("transient", "transient", "transient")
    wrapped = policy.wrap(refresh)
    with pytest.raises(TransientRefreshError):
        wrapped(1)
    assert refresh.log == [1, 1, 1]  # type: ignore[attr-defined]
    # Subsequent calls must NOT reach refresh_fn — fail-cache short-circuits.
    for caller_id in range(2, 12):
        with pytest.raises(TransientRefreshError):
            wrapped(caller_id)
    # 0 new refresh_fn invocations.
    assert refresh.log == [1, 1, 1]  # type: ignore[attr-defined]


def test_p6_permanent_error_is_NOT_fail_cached() -> None:
    """``PermanentRefreshError`` from first attempt does NOT enter fail-cache.

    Operator must be able to fix credentials and retry immediately.
    """
    sleep_fn, _ = _record_sleeps()
    policy = RefreshPolicy(
        max_retries=2,
        fail_cache_s=30.0,
        sleep_fn=sleep_fn,
    )
    refresh = _make_scripted_refresh("perm", "ok")
    wrapped = policy.wrap(refresh)
    with pytest.raises(PermanentRefreshError):
        wrapped(1)
    # Subsequent call must reach refresh_fn — fail-cache did NOT activate.
    assert wrapped(2) == "tok-2"
    assert refresh.log == [1, 2]  # type: ignore[attr-defined]


def test_p7_fail_cache_expires_then_resumes_calls() -> None:
    """After ``fail_cache_s`` elapses, calls resume invoking ``refresh_fn``."""
    sleep_fn, _ = _record_sleeps()
    policy = RefreshPolicy(
        max_retries=1,
        base_backoff_s=0.0,
        jitter=0.0,
        fail_cache_s=5.0,
        sleep_fn=sleep_fn,
    )
    refresh = _make_scripted_refresh("transient", "transient", "ok")
    wrapped = policy.wrap(refresh)
    with pytest.raises(TransientRefreshError):
        wrapped(1)
    # Simulate window expiry by rewinding cached_failure_at.
    import time as _time

    with policy._lock:
        assert policy._cached_failure_at is not None
        policy._cached_failure_at = _time.monotonic() - 1000.0
    assert wrapped(2) == "tok-2"
    assert refresh.log == [1, 1, 2]  # type: ignore[attr-defined]


def test_p8_transient_backoff_within_jitter_envelope() -> None:
    """Transient backoff sleeps fall within ``[base*2^attempt*(1-j), base*2^attempt*(1+j)]``."""
    sleep_fn, sleeps = _record_sleeps()
    policy = RefreshPolicy(
        max_retries=3,
        base_backoff_s=2.0,
        max_backoff_s=100.0,
        jitter=0.25,
        sleep_fn=sleep_fn,
    )
    refresh = _make_scripted_refresh("transient", "transient", "transient", "ok")
    wrapped = policy.wrap(refresh)
    wrapped(1)
    # attempts 0, 1, 2 → bases 2.0, 4.0, 8.0 (each ± 25%).
    expected_bases = [2.0, 4.0, 8.0]
    assert len(sleeps) == 3
    for actual, base in zip(sleeps, expected_bases, strict=True):
        lo = base * (1 - 0.25)
        hi = base * (1 + 0.25)
        assert lo <= actual <= hi, f"sleep {actual} outside [{lo}, {hi}] for base {base}"


def test_unknown_refresh_error_subclass_treated_as_transient() -> None:
    """Custom ``RefreshError`` subclass (not Permanent/Transient/RateLimited)
    treated as transient by default."""

    class CustomError(RefreshError):
        pass

    sleep_fn, sleeps = _record_sleeps()
    policy = RefreshPolicy(
        max_retries=2,
        base_backoff_s=1.0,
        jitter=0.0,
        sleep_fn=sleep_fn,
    )
    call_count = 0

    def refresh(call_id: int) -> str:
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise CustomError("boom")
        return f"tok-{call_id}"

    wrapped = policy.wrap(refresh)
    assert wrapped(1) == "tok-1"
    assert call_count == 3
    assert len(sleeps) == 2


# ----------------------------------------------------------------------------
# MatrizRefresh adapter tests (A1-A5)
# ----------------------------------------------------------------------------


def test_a1_matriz_refresh_constructor_signature() -> None:
    """``MatrizRefresh`` is constructible with keyword-only ``http_client``,
    ``base_url``, ``username``, ``password``."""
    with httpx.Client() as client:
        adapter = MatrizRefresh(
            http_client=client,
            base_url="https://api.test",
            username="u",
            password="p",
        )
    assert adapter is not None


def test_a2_matriz_refresh_posts_to_auth_get_token_with_creds_headers(
    httpx_mock: HTTPXMock,
) -> None:
    """``MatrizRefresh.__call__`` POSTs to ``{base_url}/auth/getToken`` with
    ``X-Username``/``X-Password`` headers."""
    httpx_mock.add_response(
        method="POST",
        url="https://api.test/auth/getToken",
        headers={"X-Auth-Token": "tok-abc"},
    )
    with httpx.Client() as client:
        adapter = MatrizRefresh(
            http_client=client,
            base_url="https://api.test",
            username="user-x",
            password="pass-y",
        )
        token = adapter(call_id=1)
    assert token == "tok-abc"
    request = httpx_mock.get_request()
    assert request is not None
    assert request.method == "POST"
    assert str(request.url) == "https://api.test/auth/getToken"
    assert request.headers["X-Username"] == "user-x"
    assert request.headers["X-Password"] == "pass-y"


def test_a3_status_401_raises_permanent(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(method="POST", url="https://api.test/auth/getToken", status_code=401)
    with httpx.Client() as client:
        adapter = MatrizRefresh(
            http_client=client, base_url="https://api.test", username="u", password="p"
        )
        with pytest.raises(PermanentRefreshError):
            adapter(call_id=1)


def test_a3b_status_403_raises_permanent(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(method="POST", url="https://api.test/auth/getToken", status_code=403)
    with httpx.Client() as client:
        adapter = MatrizRefresh(
            http_client=client, base_url="https://api.test", username="u", password="p"
        )
        with pytest.raises(PermanentRefreshError):
            adapter(call_id=1)


def test_a3c_status_429_with_retry_after_raises_rate_limited(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="POST",
        url="https://api.test/auth/getToken",
        status_code=429,
        headers={"Retry-After": "12"},
    )
    with httpx.Client() as client:
        adapter = MatrizRefresh(
            http_client=client, base_url="https://api.test", username="u", password="p"
        )
        with pytest.raises(RateLimitedRefreshError) as exc_info:
            adapter(call_id=1)
    assert exc_info.value.retry_after_seconds == 12.0


def test_a3d_status_503_raises_transient(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(method="POST", url="https://api.test/auth/getToken", status_code=503)
    with httpx.Client() as client:
        adapter = MatrizRefresh(
            http_client=client, base_url="https://api.test", username="u", password="p"
        )
        with pytest.raises(TransientRefreshError) as exc_info:
            adapter(call_id=1)
    # T-10-01-04 mitigation: status code only, no response.text echo.
    assert "503" in str(exc_info.value)


def test_a3e_success_with_x_auth_token_returns_string(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="POST",
        url="https://api.test/auth/getToken",
        headers={"X-Auth-Token": "tok-success-1"},
    )
    with httpx.Client() as client:
        adapter = MatrizRefresh(
            http_client=client, base_url="https://api.test", username="u", password="p"
        )
        assert adapter(call_id=1) == "tok-success-1"


def test_a4_timeout_raises_transient(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_exception(httpx.ReadTimeout("simulated timeout"))
    with httpx.Client() as client:
        adapter = MatrizRefresh(
            http_client=client, base_url="https://api.test", username="u", password="p"
        )
        with pytest.raises(TransientRefreshError) as exc_info:
            adapter(call_id=1)
    assert "timeout" in str(exc_info.value).lower()


def test_a4b_network_error_raises_transient(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_exception(httpx.ConnectError("simulated conn error"))
    with httpx.Client() as client:
        adapter = MatrizRefresh(
            http_client=client, base_url="https://api.test", username="u", password="p"
        )
        with pytest.raises(TransientRefreshError) as exc_info:
            adapter(call_id=1)
    assert "network" in str(exc_info.value).lower()


def test_a5_success_without_x_auth_token_raises_transient(httpx_mock: HTTPXMock) -> None:
    """Success status but no ``X-Auth-Token`` header → ``TransientRefreshError``."""
    httpx_mock.add_response(
        method="POST",
        url="https://api.test/auth/getToken",
        status_code=200,
        # No X-Auth-Token header set.
    )
    with httpx.Client() as client:
        adapter = MatrizRefresh(
            http_client=client, base_url="https://api.test", username="u", password="p"
        )
        with pytest.raises(TransientRefreshError) as exc_info:
            adapter(call_id=1)
    assert "X-Auth-Token" in str(exc_info.value)
