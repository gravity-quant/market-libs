"""Jerarquía de excepciones del cliente market-data."""

from __future__ import annotations

__all__ = [
    "MarketDataAPIError",
    "MarketDataAuthError",
    "MarketDataError",
    "MarketDataMutationNotAllowedError",
    "MarketDataRateLimitError",
]


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


class MarketDataMutationNotAllowedError(MarketDataError):
    """Mutación rechazada por política del cliente (D-05/D-16).

    Se lanza cuando ``mutating_allowed`` es ``False`` O cuando el host de
    ``base_url`` no coincide EXACTAMENTE con ``expected_host``. Es un rechazo
    del lado del cliente, NO un error del servidor: subclasa ``MarketDataError``
    directamente (no ``MarketDataAPIError``) y no lleva ``status_code``. La
    verificación garantiza cero request HTTP y cero round-trip a Auth0.
    """
