"""Jerarquía de excepciones del cliente market-data."""

from __future__ import annotations


class MarketDataError(Exception):
    """Excepción base para errores del cliente market-data."""


class MarketDataAPIError(MarketDataError):
    """La API devolvió un status de error."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(f"[{status_code}] {message}")
        self.status_code = status_code
        self.message = message


class MarketDataAuthError(MarketDataAPIError):
    """Error de autenticación (401/403)."""


class MarketDataRateLimitError(MarketDataAPIError):
    """Se excedió el rate limit (429)."""
