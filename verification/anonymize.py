"""Anonimización de PII que preserva el formato (HARN-06/D-10).

Segunda etapa del pipeline de dos fases (D-11): tras la captura cruda al staging
gitignored, ``anonymize`` reemplaza los valores de las claves PII (definidas por
un :class:`Denylist` por paquete) por valores sintéticos de la *misma forma*,
mientras conserva verbatim los valores no-PII relevantes para el formato.

Esto es crítico (D-10): el decimal AR ``"1.415,00"``, los números-vs-string del
JSON y las claves de envelope deben preservarse para que el fixture anonimizado
**todavía reproduzca el bug**. Sólo las CLAVES denylisted reciben un sintético.

Sólo stdlib (``dataclasses``, ``re``) — sin dependencias de datos-falsos (A4).

Tras esta etapa hay una **revisión humana obligatoria** antes de commitear cualquier
fixture bajo ``packages/<pkg>/tests/`` (ver la plantilla de hallazgos).

Uso::

    from verification.anonymize import Denylist, anonymize

    deny = Denylist("higyrus", frozenset({"idCuenta", "cuit", "titular"}))
    fixture = anonymize(raw_payload, deny)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

__all__ = ["Denylist", "anonymize"]


@dataclass(frozen=True, slots=True)
class Denylist:
    """Claves PII por paquete + reemplazos sintéticos que preservan formato.

    - ``pkg``: paquete al que aplica (etiqueta, p.ej. ``"higyrus"``).
    - ``keys``: conjunto de claves consideradas PII (p.ej. ``{"idCuenta", "cuit"}``).
    - ``replacements``: reemplazo explícito por clave; si falta, se genera un
      sintético de la misma forma. Preserva longitud/forma, no realismo.
    """

    pkg: str
    keys: frozenset[str]
    replacements: dict[str, str] = field(default_factory=dict)


def anonymize(payload: Any, deny: Denylist) -> Any:
    """Reemplaza los valores de las claves PII; conserva forma y formatos no-PII.

    Para un ``dict``: por cada clave, si está en ``deny.keys`` usa
    ``deny.replacements.get(k, _synthetic(k, v))``; si no, recurre. Para una
    ``list`` recurre elemento a elemento. Cualquier otro valor se devuelve igual
    (así el decimal AR ``"1.415,00"`` bajo una clave no-PII sobrevive intacto).
    """
    if isinstance(payload, dict):
        return {
            k: (
                deny.replacements.get(k, _synthetic(k, v)) if k in deny.keys else anonymize(v, deny)
            )
            for k, v in payload.items()
        }
    if isinstance(payload, list):
        return [anonymize(x, deny) for x in payload]
    return payload


def _synthetic(key: str, value: Any) -> Any:
    """Genera un valor sintético del mismo tipo/forma que ``value``."""
    if isinstance(value, bool):
        # bool es subclase de int — chequear antes que int para no colapsar a 0.
        return value
    if isinstance(value, str):
        # Misma forma: dígitos->0, letras (ASCII)->x; el resto (puntuación) se mantiene.
        return re.sub(r"\d", "0", re.sub(r"[A-Za-z]", "x", value))
    if isinstance(value, int):
        return 0
    if isinstance(value, float):
        return 0.0
    return value
