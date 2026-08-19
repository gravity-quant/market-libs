"""Exception hierarchy for Primary API errors."""

from __future__ import annotations


class MatrizClientError(Exception):
    """Base class for all matriz-client errors."""


class PrimaryAPIError(MatrizClientError):
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


class MatrizDecodeError(MatrizClientError):
    """Modo estricto (Fase 29, DEC-01): una divergencia de decode es fatal.

    Se levanta desde el walker (:mod:`matriz_client._decode`) cuando
    ``strict_decode`` está activo y el payload diverge del modelo por
    ``missing``, ``type`` o ``non_dict``. **Nunca** se levanta por una clave
    extra del wire: el crecimiento del vendor no es un defecto (lock 4 de
    ``29-AGGREGATION-CONTRACT.md``). Tampoco se levanta por un valor fuera del
    conjunto de un ``Literal`` de :mod:`matriz_client.types` — D-09
    (``29-DLOCK-RESPONSE-LITERAL.md``) prohíbe cerrar los nueve alias de
    RESPONSE, y el walker jamás verifica pertenencia.

    No es una subclase de :class:`PrimaryAPIError` — la respuesta HTTP fue
    exitosa y su envelope decía ``status == "OK"``; lo que falla es la forma
    del payload, no el transporte ni la aplicación.

    Atributos (T-29-29: tipos y rutas, **jamás** un valor del wire):
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
