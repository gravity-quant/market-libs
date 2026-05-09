"""Jerarquía de excepciones del cliente IOL."""

from __future__ import annotations


class IOLClientError(Exception):
    """Excepción base para errores del cliente IOL."""


class IOLAPIError(IOLClientError):
    """La API devolvió un status de error."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(f"[{status_code}] {message}")
        self.status_code = status_code
        self.message = message


class IOLAuthError(IOLAPIError):
    """Error de autenticación (401/403)."""


class IOLRateLimitError(IOLAPIError):
    """Se excedió el rate limit (429)."""
