"""Jerarquía de excepciones del cliente Higyrus.

El envelope de error de la API tiene la forma::

    {"timestamp": "2026-04-24T12:34:56Z", "errors": [{"title": ..., "detail": ...}]}

Esta info se preserva en `errors` y `timestamp` para inspección programática.
"""

from __future__ import annotations

from typing import Any


class HigyrusClientError(Exception):
    """Excepción base de la librería higyrus-client."""


class HigyrusAPIError(HigyrusClientError):
    """La API devolvió una respuesta no-2xx.

    Atributos:
        status_code: HTTP status devuelto.
        errors: Lista de ``{"title": ..., "detail": ...}`` del envelope.
        timestamp: Timestamp del servidor incluido en el envelope.
    """

    def __init__(
        self,
        status_code: int,
        errors: list[dict[str, Any]] | None = None,
        timestamp: str | None = None,
    ) -> None:
        self.status_code = status_code
        self.errors = errors or []
        self.timestamp = timestamp

        if self.errors:
            first = self.errors[0]
            detail = first.get("detail") or first.get("title") or f"HTTP {status_code}"
        else:
            detail = f"HTTP {status_code}"
        super().__init__(detail)


class HigyrusAuthError(HigyrusAPIError):
    """401: credenciales faltantes/inválidas o token vencido."""


class HigyrusAuthorizationError(HigyrusAPIError):
    """403: el usuario autenticado no tiene permisos para el recurso.

    Distinto de :class:`HigyrusAuthError` (401) porque la causa operativa
    es otra: hay que pedir al admin que habilite el permiso del endpoint
    en la plataforma Higyrus, no rotar credenciales.
    """


class HigyrusRateLimitError(HigyrusAPIError):
    """429: se excedió el rate limit."""
