"""Refresh-policy exception classification (Phase 10 REFAC-04).

Internal exception hierarchy used by ``RefreshPolicy`` + ``MatrizRefresh``.

These DO NOT inherit from ``matriz_client.exceptions.MatrizClientError`` because
they are an INTERNAL classification used only by the refresh path. The wider
package surfaces ``AuthenticationError`` / ``PrimaryAPIError`` to callers
(unwrap happens at the wiring site in Plan 10-03).
"""

from __future__ import annotations


class RefreshError(Exception):
    """Base class for refresh failures."""


class PermanentRefreshError(RefreshError):
    """Auth-level failure that retrying will not fix (401, 400, 403)."""


class TransientRefreshError(RefreshError):
    """Server/network failure that may succeed on retry (5xx, network timeout)."""


class RateLimitedRefreshError(TransientRefreshError):
    """429 Too Many Requests — retry MUST respect the ``Retry-After`` header."""

    def __init__(self, message: str, retry_after_seconds: float) -> None:
        super().__init__(message)
        self.retry_after_seconds: float = retry_after_seconds


__all__ = [
    "PermanentRefreshError",
    "RateLimitedRefreshError",
    "RefreshError",
    "TransientRefreshError",
]
