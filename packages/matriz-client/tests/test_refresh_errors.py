"""Tests for the refresh-policy exception hierarchy (Phase 10 Plan 10-01)."""

from __future__ import annotations

from matriz_client._refresh_errors import (
    PermanentRefreshError,
    RateLimitedRefreshError,
    RefreshError,
    TransientRefreshError,
)


def test_refresh_error_is_exception_subclass() -> None:
    """``RefreshError`` is a subclass of ``Exception`` and instantiable."""
    assert issubclass(RefreshError, Exception)
    exc = RefreshError("base failure")
    assert str(exc) == "base failure"


def test_permanent_refresh_error_is_refresh_error_subclass() -> None:
    """``PermanentRefreshError`` extends ``RefreshError``."""
    assert issubclass(PermanentRefreshError, RefreshError)
    exc = PermanentRefreshError("401 invalid creds")
    assert isinstance(exc, RefreshError)
    assert str(exc) == "401 invalid creds"


def test_transient_refresh_error_is_refresh_error_subclass() -> None:
    """``TransientRefreshError`` extends ``RefreshError``."""
    assert issubclass(TransientRefreshError, RefreshError)
    exc = TransientRefreshError("503 service unavailable")
    assert isinstance(exc, RefreshError)
    assert str(exc) == "503 service unavailable"


def test_rate_limited_refresh_error_is_transient_subclass() -> None:
    """``RateLimitedRefreshError`` extends ``TransientRefreshError`` and exposes
    ``retry_after_seconds``."""
    assert issubclass(RateLimitedRefreshError, TransientRefreshError)
    assert issubclass(RateLimitedRefreshError, RefreshError)
    exc = RateLimitedRefreshError("429 rate-limited", retry_after_seconds=15.0)
    assert isinstance(exc, TransientRefreshError)
    assert exc.retry_after_seconds == 15.0
    assert str(exc) == "429 rate-limited"


def test_rate_limited_retry_after_attribute_is_settable_via_constructor() -> None:
    """The ``retry_after_seconds`` attribute mirrors the constructor argument."""
    exc = RateLimitedRefreshError("429", retry_after_seconds=7.5)
    assert exc.retry_after_seconds == 7.5


def test_imports_succeed_from_module() -> None:
    """All 4 public names are importable from ``matriz_client._refresh_errors``."""
    # The imports at the top of this file already exercise the contract — the
    # test just asserts the names are bound and non-None to be explicit about
    # the smoke check.
    assert RefreshError is not None
    assert PermanentRefreshError is not None
    assert TransientRefreshError is not None
    assert RateLimitedRefreshError is not None
