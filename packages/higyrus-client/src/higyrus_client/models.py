"""Safe-access frozen dataclasses for Higyrus API responses.

All response models inherit from :class:`SafeModel` and are constructed via
:meth:`SafeModel.from_api`, which tolerates partial or missing fields and
substitutes safe defaults per type:

- ``str`` -> ``""``
- ``int`` / ``float`` -> ``0`` / ``0.0``
- ``bool`` -> ``False``
- ``list[X]`` -> ``[]``
- nested ``SafeModel`` -> ``X.from_api(None)`` (empty instance)
- ``X | None`` -> ``None`` when missing (explicit opt-in to nullable)

Extra keys in the payload are ignored; missing keys fall back to defaults.
Chained access like ``posicion.parking[0].diasParking`` never raises — the
worst case is a final ``None`` or a zero-valued primitive.

Field names follow the wire format (camelCase) verbatim so JSON parsing
can stay declarative. This module is exempt from the ``N815`` naming rule
(see ``[tool.ruff.lint.per-file-ignores]`` in ``pyproject.toml``).
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from types import NoneType, UnionType
from typing import Any, Self, Union, cast, get_args, get_origin, get_type_hints


class SafeModel:
    """Base class for Higyrus API response models.

    Subclasses must be frozen dataclasses. Construct instances via
    :meth:`from_api` to tolerate partial or missing fields.
    """

    @classmethod
    def from_api(cls, payload: Any) -> Self:
        """Build an instance from an API payload, with safe defaults."""
        data: dict[str, Any] = payload if isinstance(payload, dict) else {}
        hints = get_type_hints(cls)
        kwargs: dict[str, Any] = {}
        for field in fields(cast(Any, cls)):
            kwargs[field.name] = _coerce(data.get(field.name), hints[field.name])
        return cls(**kwargs)


def _coerce(value: Any, hint: Any) -> Any:
    """Coerce ``value`` to match ``hint``, substituting safe defaults for ``None``."""
    origin = get_origin(hint)
    args = get_args(hint)

    # Optional[T] / T | None: explicit opt-in to nullable — a missing value
    # stays None instead of collapsing to a typed zero.
    if origin is Union or origin is UnionType:
        if value is None:
            return None
        non_none = [a for a in args if a is not NoneType]
        if len(non_none) == 1:
            return _coerce(value, non_none[0])
        return value

    if origin is list:
        if not isinstance(value, list):
            return []
        inner = args[0] if args else Any
        return [_coerce(item, inner) for item in value]

    if isinstance(hint, type) and issubclass(hint, SafeModel):
        return hint.from_api(value)

    if hint is str:
        return value if isinstance(value, str) else ""
    if hint is bool:
        return value if isinstance(value, bool) else False
    if hint is int:
        # bool is a subclass of int in Python — exclude it so bool payloads
        # don't collapse into "cantidad=True".
        if isinstance(value, bool):
            return 0
        return value if isinstance(value, int) else 0
    if hint is float:
        if isinstance(value, bool):
            return 0.0
        if isinstance(value, int | float):
            return float(value)
        return 0.0

    return value


@dataclass(frozen=True, slots=True)
class PosicionValuada(SafeModel):
    """Valued position row returned by ``GET /api/cuentas/{idCuenta}/posicionValuada``.

    See ``documentation/higyrus-docs.pdf`` pp. 49-52. Shape-compatible with
    the multi-account endpoint ``POST /api/cuentas/posicionValuada``
    (p. 103+), which additionally surfaces ``idMovimiento`` — already
    included here so the same model covers both endpoints.

    Verified against sandbox on 2026-04-24:

    - The PDF renders some keys with Spanish accents (``información``,
      ``fechaCotización``, ``valuación``, ``sesión``). The live wire
      uses **ASCII without accents** on every key, so those four were
      always doc/OCR artifacts and this model is already correct.
    - ``cantidad`` arrives as a float (e.g. ``-2788.35``). Modeled as
      ``float``.
    - ``tipoTitulo``, ``monedaCotizacion`` and ``idMovimiento`` are
      extra keys not documented in the PDF for this endpoint but
      present on every row; added here.
    """

    cuenta: str
    operador: str
    unidad: str
    lugar: str
    estado: str
    uso: str
    fecha: str
    comprobante: str
    informacion: str
    cantidad: float
    fechaCotizacion: str
    precio: float
    valuacion: float
    administrador: str
    cartera: str
    mercado: str
    segmento: str
    sesion: str
    tipoTitulo: str
    monedaCotizacion: str
    idMovimiento: str


@dataclass(frozen=True, slots=True)
class Parking(SafeModel):
    """Parking entry nested inside a :class:`Posicion`.

    See ``documentation/higyrus-docs.pdf`` pp. 33-36.
    """

    monedaPosicion: str
    diasParking: int
    cantidadLiquidada: int
    observacion: str


@dataclass(frozen=True, slots=True)
class Movimiento(SafeModel):
    """Account movement row returned by ``GET /api/cuentas/{idCuenta}/movimientos``.

    See ``documentation/higyrus-docs.pdf`` pp. 26-30. Verified against
    sandbox on 2026-04-24.

    Notes on wire shape discovered at that verification:

    - ``fecha`` and ``fechaConcertacion`` are not ISO 8601 despite the
      PDF stub; they come as ``"dd/mm/yyyy HH:MM:SS"`` / ``"dd/mm/yyyy"``
      (or ``null``). Stored verbatim; no client-side parsing.
    - ``cantidad`` arrives as a float (e.g. ``-21936.48``) even though
      the PDF labels it as ``0`` (implying int). Modeled as ``float``.
    - ``idMovimientos`` is the list of internal transaction IDs that
      compose the movement.
    """

    cuenta: str
    fechaDesde: str
    fechaHasta: str
    fechaConcertacion: str
    tipoTitulo: str
    tipoTituloAgente: str
    especie: str
    simboloLocal: str
    lugar: str
    estado: str
    fecha: str
    tipoOperacion: str
    comprobante: str
    informacion: str
    subCuenta: str
    cantidad: float
    tipoEspecie: str
    movimiento: str
    valuacion: float
    factorizacion: str
    concepto: str
    idMovimientos: list[int]


@dataclass(frozen=True, slots=True)
class Posicion(SafeModel):
    """Account position row returned by ``GET /api/cuentas/{idCuenta}/posiciones``.

    See ``documentation/higyrus-docs.pdf`` pp. 33-36. The
    ``disponibleAjustado`` field is only populated for FCI instruments when
    the Higyrus parameter ``irmo.fci.rescate_estadoSolicitudesAdescontar``
    is active; if absent, the safe-access default (``0.0``) is used.
    """

    cuenta: str
    fecha: str
    tipoTitulo: str
    tipoTituloAgente: str
    codigoISIN: str
    especie: str
    nombreEspecie: str
    simboloLocal: str
    lugar: str
    subCuenta: str
    estado: str
    disponibleAjustado: float
    cantidadLiquidada: int
    cantidadPendienteLiquidar: int
    precio: float
    precioUnitario: float
    monedaCotizacion: str
    fechaPrecio: str
    informacion: str
    parking: list[Parking]


# ---------------------------------------------------------------------------
# /api/cuentas/listadoCuentas
#
# Field names are modeled in ASCII without diacritics. The PDF (pp. 79-83)
# renders some keys with Spanish accents (``categoría``, ``denominación``,
# ``autorización``, ``derivación``, ``vinculación``, ``país``, ``dirección``)
# but the same artifact pattern appeared in ``PosicionValuada`` and the live
# wire turned out to use ASCII. Pending sandbox verification — if any field
# stays empty in real responses, re-check the wire key.
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DisposicionesGenerales(SafeModel):
    """``disposicionesGenerales`` block nested inside :class:`Cuenta`."""

    vigenciaDesde: str
    vigenciaHasta: str
    condicionesGenerales: str
    autorizacionGeneral: str
    fondosDisponibles: str
    cuentaFCI: str
    derivacionBYMA: str
    instruccionesFondos: str
    tipoCliente: str
    horizonteInversion: str
    perfilInversion: str
    actividadEsperada: str
    operatoria: str
    vinculacionAgente: str
    derivacionMAV: str


@dataclass(frozen=True, slots=True)
class Domicilio(SafeModel):
    """Address entry inside :class:`Cuenta` ``domicilios``."""

    uso: str
    pais: str
    provincia: str
    codigoPostal: str
    ciudad: str
    direccion: str


@dataclass(frozen=True, slots=True)
class PersonaRelacionada(SafeModel):
    """Related-person entry inside :class:`Cuenta` ``personasRelacionadas``."""

    tipoRelacion: str
    persona: str
    tipoId: str
    id: str
    orden: str
    desde: str
    hasta: str
    realizarSeguimiento: str
    limitaAccesoCuenta: str
    participacionFondeo: str
    descripcion: str
    limitaOperacion: str
    limitaExtraccion: str


@dataclass(frozen=True, slots=True)
class MedioComunicacion(SafeModel):
    """Communication method entry inside :class:`Cuenta` ``mediosComunicacion``."""

    tipo: str
    medio: str
    vigenciaDesde: str
    vigenciaHasta: str
    uso: str
    principal: str
    notas: str


@dataclass(frozen=True, slots=True)
class CuentaBancaria(SafeModel):
    """Bank account entry inside :class:`Cuenta` ``cuentasBancarias``."""

    cbu: str
    banco: str
    moneda: str
    vigenteDesde: str
    vigenteHasta: str


@dataclass(frozen=True, slots=True)
class Agente(SafeModel):
    """Agent reference inside :class:`Administrador`."""

    codigo: str
    denominacion: str


@dataclass(frozen=True, slots=True)
class Operador(SafeModel):
    """Operator reference inside :class:`Administrador`."""

    nombre: str
    nombreReal: str
    idExterno: str


@dataclass(frozen=True, slots=True)
class Sucursal(SafeModel):
    """Branch reference inside :class:`Administrador`."""

    codigo: str
    denominacion: str


@dataclass(frozen=True, slots=True)
class Administrador(SafeModel):
    """``administrador`` block nested inside :class:`Cuenta`."""

    agente: Agente
    operador: Operador
    sucursal: Sucursal


@dataclass(frozen=True, slots=True)
class Cuenta(SafeModel):
    """Account row returned by ``GET /api/cuentas/listadoCuentas``.

    See ``documentation/higyrus-docs.pdf`` pp. 79-83. Mirrors the fields
    surfaced by the "Administración de cuentas" window in the Higyrus
    desktop client.
    """

    id: str
    tipo: str
    cartera: str
    categoria: str
    clase: str
    fechaAlta: str
    denominacion: str
    alias: str
    titular: str
    tipoTitular: str
    estado: str
    nota: str
    disposicionesGenerales: DisposicionesGenerales
    domicilios: list[Domicilio]
    personasRelacionadas: list[PersonaRelacionada]
    mediosComunicacion: list[MedioComunicacion]
    cuentasBancarias: list[CuentaBancaria]
    administrador: Administrador
