"""Jerarquía de excepciones del cliente Ámbito Financiero."""

from __future__ import annotations


class AmbitoFinancieroClientError(Exception):
    """Excepción base para errores del cliente Ámbito Financiero."""


class AmbitoFinancieroAPIError(AmbitoFinancieroClientError):
    """La API devolvió un status de error."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(f"[{status_code}] {message}")
        self.status_code = status_code
        self.message = message


class AmbitoFinancieroAuthError(AmbitoFinancieroAPIError):
    """Error de autenticación (401/403)."""


class AmbitoFinancieroRateLimitError(AmbitoFinancieroAPIError):
    """Se excedió el rate limit (429)."""


class AmbitoFinancieroNoDataError(AmbitoFinancieroClientError):
    """No hay datos para la consulta (típicamente fin de semana, feriado o fecha futura)."""
