"""Exception classification primitives for refresh policy.

The policy decides retry vs. propagate based on these classes. Real production
code will map HTTP status codes / network errors to these in the refresh_fn
adapter layer.
"""

from __future__ import annotations


class RefreshError(Exception):
    """Base class for refresh failures."""


class PermanentRefreshError(RefreshError):
    """Auth-level failure that retrying won't fix (401, 400, 403).

    Examples in matriz context:
    - 401 Unauthorized — wrong credentials
    - 400 Bad Request — malformed credentials payload
    - 403 Forbidden — account disabled / scope missing
    """


class TransientRefreshError(RefreshError):
    """Server/network failure that may succeed on retry (5xx, network timeout).

    Examples:
    - 502 Bad Gateway
    - 503 Service Unavailable
    - 504 Gateway Timeout
    - ConnectionError, TimeoutError from httpx
    """


class RateLimitedRefreshError(TransientRefreshError):
    """429 Too Many Requests — retry MUST respect the Retry-After header.

    The attribute `retry_after_seconds` carries the server's hint.
    """

    def __init__(self, message: str, retry_after_seconds: float) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds
