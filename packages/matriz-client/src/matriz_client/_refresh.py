"""MatrizRefresh — pluggable adapter for the matriz token endpoint (Phase 10).

Contract: ``Callable[[int], str]``. POSTs to ``{base_url}{_AUTH_PATH}`` with
``X-Username``/``X-Password`` credential headers (matches
``_core.build_login_request``), maps httpx exceptions and HTTP status codes
to the refresh-policy hierarchy, returns the ``X-Auth-Token`` response header.

T-10-01-04 mitigation: error messages embed ``status_code`` ONLY, never the
response body (ASVS V8.3.4).
"""

from __future__ import annotations

import httpx

from matriz_client._refresh_errors import (
    PermanentRefreshError,
    RateLimitedRefreshError,
    TransientRefreshError,
)

__all__ = ["MatrizRefresh"]

_AUTH_PATH = "/auth/getToken"
_REQUEST_TIMEOUT = 10.0
_DEFAULT_RETRY_AFTER = 10.0
_PERMANENT_STATUSES: dict[int, str] = {
    400: "bad request (400)",
    401: "invalid credentials (401)",
    403: "forbidden (403)",
}


class MatrizRefresh:
    """Pluggable adapter — exercises the matriz token endpoint."""

    def __init__(
        self,
        *,
        http_client: httpx.Client,
        base_url: str,
        username: str,
        password: str,
    ) -> None:
        self._http_client = http_client
        self._base_url = base_url
        self._username = username
        self._password = password

    def __call__(self, call_id: int) -> str:
        url = f"{self._base_url}{_AUTH_PATH}"
        headers = {"X-Username": self._username, "X-Password": self._password}
        try:
            response = self._http_client.post(url, headers=headers, timeout=_REQUEST_TIMEOUT)
        except httpx.TimeoutException as exc:
            raise TransientRefreshError("timeout during token request") from exc
        except httpx.NetworkError as exc:
            raise TransientRefreshError(f"network error during token request: {exc!s}") from exc

        status = response.status_code
        if status in _PERMANENT_STATUSES:
            raise PermanentRefreshError(_PERMANENT_STATUSES[status])
        if status == 429:
            retry_after = self._parse_retry_after(response.headers.get("Retry-After"))
            raise RateLimitedRefreshError(
                f"rate-limited (429); Retry-After={retry_after}",
                retry_after_seconds=retry_after,
            )
        if 500 <= status < 600:
            # T-10-01-04: status code only — never the body.
            raise TransientRefreshError(f"server error {status}")
        if status >= 400:
            raise TransientRefreshError(f"unexpected client error {status}")

        token: str | None = response.headers.get("X-Auth-Token")
        if not token:
            raise TransientRefreshError("response missing X-Auth-Token header")
        return token

    @staticmethod
    def _parse_retry_after(raw: str | None) -> float:
        """Parse ``Retry-After`` header; default to ``_DEFAULT_RETRY_AFTER``."""
        if raw is None:
            return _DEFAULT_RETRY_AFTER
        try:
            return float(raw)
        except ValueError:
            return _DEFAULT_RETRY_AFTER
