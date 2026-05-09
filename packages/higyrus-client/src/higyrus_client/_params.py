"""Helpers for building Higyrus API query params.

The Higyrus API has consistent conventions that differ from the ``requests``
defaults, so every endpoint wrapper funnels its kwargs through these helpers
before handing them to :func:`higyrus_client.client._request`:

- **Dates** are serialized as ``dd/mm/yyyy`` (not ISO). Applies to
  ``fechaDesde``/``fechaHasta`` in ``/movimientos``, ``desde``/``hasta`` in
  ``/posicionValuada`` and ``/informeAuditoriaDetalle``, and any other
  date-range parameter.
- **Booleans** travel as capitalized ``"True"`` / ``"False"`` (Python's
  ``str(bool)`` output), not JavaScript-style ``true``/``false``.
- ``None`` values are dropped from the query entirely so optional params
  simply don't appear in the URL.

See the corresponding domain note in the vault:
``higyrus-vault/projects/higyrus-client/domain/Convenciones de query params.md``.
"""

from __future__ import annotations

from datetime import date
from typing import Any

__all__ = ["drop_none", "format_bool", "format_date"]


def format_date(value: date | None) -> str | None:
    """Serialize ``value`` as ``dd/mm/yyyy`` for Higyrus date params.

    Accepts :class:`datetime.date` (or its subclass :class:`datetime.datetime`)
    and ``None``. Strings are **not** accepted — the client always owns
    the formatting so the wire shape stays consistent.
    """
    if value is None:
        return None
    return value.strftime("%d/%m/%Y")


def format_bool(value: bool | None) -> str | None:
    """Serialize a Python ``bool`` as the capitalized Higyrus wire format.

    ``True`` → ``"True"``, ``False`` → ``"False"``, ``None`` → ``None``.
    Equivalent to ``str(value)`` but with the ``None`` short-circuit so
    callers can wire it directly into a params dict and let :func:`drop_none`
    strip unset values.
    """
    if value is None:
        return None
    return str(value)


def drop_none(params: dict[str, Any]) -> dict[str, Any]:
    """Return ``params`` without keys whose value is ``None``.

    Preserves falsy-but-not-None values (``False``, ``0``, ``""``) because
    those are legitimate API inputs.
    """
    return {k: v for k, v in params.items() if v is not None}
