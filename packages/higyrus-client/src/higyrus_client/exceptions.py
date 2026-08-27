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
        status_code: HTTP status devuelto, o 0 si el error fue detectado
            client-side (e.g., shape mismatch tras un 2xx exitoso).
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


class HigyrusDecodeError(HigyrusClientError):
    """Modo estricto (Fase 29, DEC-01): una divergencia de decode es fatal.

    Se levanta desde el walker (:mod:`higyrus_client._decode`) cuando
    ``strict_decode`` está activo y el payload diverge del modelo por
    ``missing``, ``type`` o ``non_dict``. **Nunca** se levanta por una clave
    extra del wire: el crecimiento del vendor no es un defecto (lock 4 de
    ``29-AGGREGATION-CONTRACT.md``).

    No es una subclase de :class:`HigyrusAPIError` — la respuesta HTTP fue
    exitosa; lo que falla es la forma del payload, no el transporte.

    Atributos (T-29-07: tipos y rutas, **jamás** un valor del wire):
        field_path: Ruta punteada desde la raíz del decode al campo divergente.
        declared_type: Nombre del tipo declarado por el modelo.
        observed_type: Nombre del tipo runtime del valor recibido.
        model: Nombre simple (no calificado) de la clase que se estaba decodificando.
    """

    def __init__(
        self,
        field_path: str,
        declared_type: str,
        observed_type: str,
        model: str,
    ) -> None:
        self.field_path = field_path
        self.declared_type = declared_type
        self.observed_type = observed_type
        self.model = model
        super().__init__(
            f"decode divergence in {model}{field_path}: "
            f"declared {declared_type}, observed {observed_type}"
        )
