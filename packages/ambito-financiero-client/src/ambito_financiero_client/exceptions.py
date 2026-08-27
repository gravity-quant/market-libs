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


class AmbitoFinancieroDecodeError(AmbitoFinancieroClientError):
    """Modo estricto (Fase 29, DEC-01): una divergencia de decode es fatal.

    Se levanta desde el walker (:mod:`ambito_financiero_client._decode`) cuando
    ``strict_decode`` está activo y el payload diverge del modelo por
    ``missing``, ``type`` o ``non_dict``. **Nunca** se levanta por una clave
    extra del wire: el crecimiento del vendor no es un defecto (lock 4 de
    ``29-AGGREGATION-CONTRACT.md``).

    No es una subclase de :class:`AmbitoFinancieroAPIError` — la respuesta HTTP
    fue exitosa; lo que falla es la forma del payload, no el transporte. Por eso
    tampoco lleva ``status_code``. Tampoco se relaciona con
    :class:`AmbitoFinancieroNoDataError`, que señala una consulta sin datos
    (fin de semana / feriado), no un payload malformado.

    Hoy es inalcanzable en producción: la superficie pública de este paquete
    devuelve un ``float``, no un modelo, así que el walker está dormido acá
    (ver el docstring de ``_decode``). Existe para que las cinco copias sean
    verbatim y para que una superficie tipada futura la herede.

    Atributos (T-29-36: tipos y rutas, **jamás** un valor del wire):
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
