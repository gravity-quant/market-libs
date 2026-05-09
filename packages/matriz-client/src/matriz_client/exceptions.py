"""Exception hierarchy for Primary API errors."""

from __future__ import annotations


class PrimaryAPIError(Exception):
    """Error returned by the Primary API.

    Raised when a response comes back with ``status == "ERROR"``. The
    original ``description``/``message`` fields from the API payload are
    preserved as attributes for programmatic inspection.

    Attributes:
        status: Always ``"ERROR"`` for failed responses.
        description: Human-readable description from the API, if present.
        api_message: Lower-level message string from the API, if present.
    """

    def __init__(self, status: str, description: str | None = None, message: str | None = None):
        self.status = status
        self.description = description
        self.api_message = message
        detail = description or message or status
        super().__init__(detail)


class AuthenticationError(PrimaryAPIError):
    """Raised when authentication fails or no token is returned by the API."""
