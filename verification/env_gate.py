"""Gate de variables de entorno para el harness de verificación (HARN-01 / D-15).

Antes de ejercitar un cliente contra su API en vivo, el driver comprueba que
las credenciales necesarias estén presentes. Si falta alguna, ``require_env``
imprime la línea verbatim::

    SKIPPED <pkg>: missing IOL_USER, IOL_PASSWORD

y devuelve ``False`` **sin interrumpir el proceso**. Es el driver quien decide
salir limpiamente (código 0) para que el runner agregado / un loop de shell
registre el SKIP y continúe con el resto de los paquetes (D-14/D-15, Pitfall 6).

Uso típico desde un ``main_*.py``: el driver chequea el booleano y, si es
``False``, hace una salida limpia con código 0 para que el batch continúe con
el próximo paquete en lugar de cortar todo el lote.

Variables esperadas por paquete (de cada ``.env.example``):

- ``iol-client``: ``IOL_USER``, ``IOL_PASSWORD``
- ``higyrus-client``: ``HIGYRUS_USER``, ``HIGYRUS_PASSWORD``, ``HIGYRUS_BASE_URL``
- ``matriz-client``: ``PRIMARY_USER``, ``PRIMARY_PASSWORD``
- ``ambito-financiero-client``: ninguna (sin auth)
"""

from __future__ import annotations

import os

__all__ = ["require_env"]


def require_env(pkg: str, names: list[str]) -> bool:
    """True si todas las vars existen; si faltan, imprime SKIPPED y devuelve False.

    Nunca interrumpe el proceso: el caller controla la salida (Pitfall 6).
    """
    missing = [n for n in names if not os.getenv(n)]
    if missing:
        print(f"SKIPPED {pkg}: missing {', '.join(missing)}")
        return False
    return True
