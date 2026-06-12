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

    Para un ``dict``: por cada clave, si NO está en ``deny.keys`` se recurre
    (conservando formatos no-PII como el decimal AR ``"1.415,00"``). Si está en
    ``deny.keys`` se reemplaza: con ``deny.replacements[k]`` si hay reemplazo
    explícito; si no y el valor es un contenedor (``dict``/``list``), se sanea el
    subárbol **completo** vía :func:`_scrub` (una clave PII nunca devuelve su
    contenedor verbatim — CR-01); y si es escalar, con un sintético de la misma
    forma. Para una ``list`` se recurre elemento a elemento.
    """
    if isinstance(payload, dict):
        out: dict[str, Any] = {}
        for k, v in payload.items():
            if k not in deny.keys:
                out[k] = anonymize(v, deny)
            elif k in deny.replacements:
                out[k] = deny.replacements[k]
            elif isinstance(v, dict | list):
                # Contenedor bajo clave PII: TODO el subárbol es PII por
                # transitividad. Sanear cada hoja; nunca devolverlo intacto.
                out[k] = _scrub(v)
            else:
                out[k] = _synthetic(k, v)
        return out
    if isinstance(payload, list):
        return [anonymize(x, deny) for x in payload]
    return payload


def _scrub(value: Any) -> Any:
    """Saneo total de un subárbol PII: sintetiza cada hoja escalar, preserva forma.

    A diferencia de :func:`anonymize`, no consulta el denylist: bajo una clave PII
    todo el contenido es PII, así que cada hoja escalar se reemplaza por un
    sintético de la misma forma. Garantiza que ningún ``dict``/``list`` sobreviva
    con PII original (CR-01 / HARN-06).
    """
    if isinstance(value, dict):
        return {k: _scrub(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_scrub(x) for x in value]
    return _synthetic("", value)


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
