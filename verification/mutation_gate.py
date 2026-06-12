"""Gate de mutaciones para el harness de verificación (HARN-02 / D-16).

Las llamadas que mutan estado en la API de Matriz (alta/cancelación de órdenes)
son destructivas, por lo que deben ser **inalcanzables** salvo que se cumplan
dos condiciones a la vez (doble gate, D-16):

1. el opt-in explícito ``VERIFY_MUTATING=1`` está presente, y
2. la base URL resuelta en vivo apunta al sandbox ``remarkets``.

Si cualquiera de las dos falla, ``mutating_allowed`` imprime la línea verbatim::

    SKIPPED (mutating, guard off)

y devuelve ``False``. La base URL se lee en el momento del guard desde el
estado de módulo resuelto de ``matriz_client`` (su ``_base_url``) y nunca desde
una constante hardcodeada, para que un ``configure(base_url=prod)`` en runtime
quede atrapado (Pitfall 5). El valor privado se lee sólo para decidir el gate
y nunca se imprime (A2).

Uso típico desde ``main_matriz.py``::

    from verification.mutation_gate import mutating_allowed

    if mutating_allowed():
        ...  # recién aquí es seguro ejercitar la superficie mutante
"""

from __future__ import annotations

import os
from urllib.parse import urlsplit

__all__ = ["mutating_allowed"]

# Único host donde es seguro mutar (alta/cancelación de órdenes): el sandbox
# remarkets de Primary. Producción es ``api.primary.com.ar``; cualquier otro host
# cae en fail-closed. Se compara contra el HOSTNAME exacto, nunca contra un
# substring de la URL (CR-02 / Pitfall 5).
_SANDBOX_HOST = "api.remarkets.primary.com.ar"


def mutating_allowed() -> bool:
    """Solo permite mutaciones con flag opt-in Y base URL remarkets (D-16)."""
    if os.getenv("VERIFY_MUTATING") != "1":
        print("SKIPPED (mutating, guard off)")
        return False
    # Import perezoso: `matriz_client` sólo está instalado en el entorno del
    # propio paquete (uv run --package matriz-client). Importarlo a nivel de
    # módulo rompería el import zero-config del barrel desde los otros drivers
    # (que corren en entornos donde matriz_client no está instalado). Se importa
    # aquí, en el único punto donde el gate realmente se evalúa (main_matriz.py),
    # garantizando que el módulo esté disponible.
    import matriz_client

    base = matriz_client.client._base_url  # estado resuelto en vivo; sólo lectura
    # HOSTNAME exacto, no substring: una URL con `remarkets` en host/path/query
    # (p.ej. `https://remarkets.attacker.example` o `.../?x=remarkets`) NO debe
    # habilitar mutaciones (CR-02). Host distinto del sandbox -> nunca mutar.
    if urlsplit(base).hostname != _SANDBOX_HOST:
        print("SKIPPED (mutating, guard off)")  # host no-sandbox -> nunca mutar
        return False
    return True
