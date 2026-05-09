"""Jerarquía de excepciones del cliente Wallets."""

from __future__ import annotations


class WalletsClientError(Exception):
    """Excepción base para errores del cliente Wallets."""


class WalletsAPIError(WalletsClientError):
    """La API devolvió un status de error."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(f"[{status_code}] {message}")
        self.status_code = status_code
        self.message = message


class WalletsAuthError(WalletsAPIError):
    """Error de autenticación (401/403)."""


class WalletsRateLimitError(WalletsAPIError):
    """Se excedió el rate limit (429)."""
