"""Snapshot de esquema: claves + tipos, nunca valores (D-12).

``schema_of`` reduce cualquier payload a su *estructura* — el conjunto de claves
y los nombres de tipo de cada hoja— sin incluir ningún valor. Esa propiedad lo
hace PII-free *por construcción*: un snapshot del esquema es directamente
committeable (el primero se commitea en la Fase 2, DRIFT-01) y la detección de
drift es estructural (claves + tipos), no por valores.

Uso::

    from verification.schema import schema_of

    schema_of({"b": "1.415,00", "a": 5})   # -> {"a": "int", "b": "str"}
    schema_of([{"x": 1}])                    # -> [{"x": "int"}]
    schema_of([])                            # -> []

El archivo de snapshot es el JSON pretty-printed de ``schema_of(raw)``.
"""

from __future__ import annotations

from typing import Any

__all__ = ["schema_of"]


def schema_of(payload: Any) -> Any:
    """Reduce un payload a su estructura: claves + tipos, nunca valores.

    - ``dict`` -> ``{clave: schema_of(valor)}`` con claves ordenadas.
    - ``list`` -> ``[schema_of(primer_elemento)]`` si no está vacía, si no ``[]``.
    - escalar -> el nombre de su tipo (``"str"`` | ``"int"`` | ``"float"`` |
      ``"bool"`` | ``"NoneType"`` | ...).
    """
    if isinstance(payload, dict):
        return {k: schema_of(v) for k, v in sorted(payload.items())}
    if isinstance(payload, list):
        # Tipo del primer elemento como muestra; lista vacía -> [].
        return [schema_of(payload[0])] if payload else []
    return type(payload).__name__
