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

Phase 29 (DEC-01): the per-field coercion now lives in
:mod:`higyrus_client._decode`, the canonical walker shared in verbatim copies
across the paquetes. **The substitution behaviour above is unchanged** — every
default listed is still the default, and :meth:`SafeModel.from_api` still takes
exactly one positional argument and returns the same instance it always did.
What is new is *reporting*: each substitution now emits a structured divergence
record on the ``higyrus_client`` logger, and an undeclared wire key — which
``_coerce`` structurally could not see, since it never received the payload's
own key set — is reported too.

Phase 31 (D-03): :meth:`SafeModel.to_dict` is the Phase 30 D-08 escape hatch,
carried into higyrus by a **verbatim copy** of iol's method — never a
cross-package import (C-2: this monorepo has no shared internal package by
design). It is also the adapter the verification harness feeds to
``verification.schema.schema_of``, with one caveat that Phase 30 CR-01 pins: a
``schema_of`` fed from ``to_dict()`` is a function of the DECLARATION rather
than of the wire — the walker has already coerced every non-optional field to
its declared type and dropped every undeclared key — so it is **not** the right
input at a drift-detection site.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import Any, Self, cast

from higyrus_client import _decode


class SafeModel:
    """Base class for Higyrus API response models.

    Subclasses must be frozen dataclasses. Construct instances via
    :meth:`from_api` to tolerate partial or missing fields.
    """

    @classmethod
    def from_api(cls, payload: Any) -> Self:
        """Build an instance from an API payload, with safe defaults."""
        kwargs = _decode.walk_model(
            cls, payload, policy=_decode.POLICY, sink=_decode.current_sink()
        )
        return cls(**kwargs)

    def to_dict(self) -> dict[str, Any]:
        """Re-project the model as the plain wire dict (D-08).

        Escape hatch for the dict -> model break of Phase 30: use it for
        ``len()`` / ``isinstance`` call sites ONLY. It is **NOT** a valid input
        to ``verification.schema.schema_of`` (WR-04). The walker has already
        coerced every non-optional field to its declared type and dropped every
        undeclared key, so a type change, an added key and a removed key are all
        three invisible in this projection (Phase 30 CR-01) — every driver
        schema-snapshot site must keep feeding RAW WIRE, as the module docstring
        above spells out. Nested models are flattened to dicts; ``None`` keys are
        **kept** — a response model must reproduce the declared shape, holes
        included.

        ``cast(Any, self)`` follows ``_decode.py``'s existing mypy-strict
        discipline: :class:`SafeModel` itself is not a dataclass — every
        concrete subclass is — so ``asdict``'s ``DataclassInstance`` overload
        cannot be satisfied by the base's ``self``.
        """
        wire: dict[str, Any] = dataclasses.asdict(cast(Any, self))
        return wire


def _coerce(value: Any, hint: Any) -> Any:
    """Coerce ``value`` to match ``hint``, substituting safe defaults for ``None``.

    Back-compat shim over :func:`higyrus_client._decode.walk_field`. Kept with
    its original two-positional-argument signature and identical return values
    so any existing caller keeps working; new code should reach for the walker.
    """
    return _decode.walk_field(
        value,
        hint,
        path="",
        model="",
        policy=_decode.POLICY,
        sink=_decode.DecodeScope(),
    )


# ---------------------------------------------------------------------------
# /api/health
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Health(SafeModel):
    """Liveness payload returned by ``GET /api/health`` (Phase 31 D-01).

    Reconciled against the committed live capture
    ``.planning/verification/schemas/higyrus-client/get-health.json``, captured
    2026-06-08 against ``https://becerra.aunesa.com/Irmo``, whose entire content
    is a single ``status`` string. That capture is the sole source of truth for
    the field set: nothing else is declared here.

    ``status`` is declared ``str``, deliberately **not** ``str | None`` (D-02).
    The capture shows a populated string, and an over-declared Optional would
    cost observability: ``walk_field``'s union-with-``None`` branch returns
    ``None`` WITHOUT emitting a divergence record, so a genuine null arriving on
    the wire would be absorbed silently — erasing exactly the signal this
    milestone exists to surface. It also carries no ``received_at``: health is a
    liveness answer, not a snapshot, and has no staleness dimension.
    """

    status: str


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
