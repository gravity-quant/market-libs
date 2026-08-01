"""Gate de mutaciones para el harness de verificación (HARN-02 / D-16 / D-01).

Las llamadas que mutan estado en una API en vivo son destructivas, por lo que
deben ser **inalcanzables** salvo que se cumplan dos condiciones a la vez (doble
gate):

1. el opt-in explícito de entorno está presente con el valor literal ``"1"``, y
2. el hostname de la base URL resuelta es EXACTAMENTE el del entorno seguro.

Si cualquiera de las dos falla se imprime la línea verbatim :data:`_SKIP_LINE`::

    SKIPPED (mutating, guard off)

y se devuelve ``False``. La línea NO lleva dos puntos a propósito: el
clasificador de ``main_verify.py`` (``^SKIPPED \\S.*:``) marcaría el paquete
ENTERO como SKIPPED, convirtiendo un read sweep exitoso en un skip. El único
emisor legítimo de esa forma con dos puntos es ``verification/env_gate.py``.

Dos funciones, una decisión
---------------------------

:func:`mutating_allowed_for` es la forma **package-agnostic**: recibe las tres
entradas de la decisión (nombre de la variable de entorno, base URL resuelta y
host esperado) y no importa ningún paquete cliente.

:func:`mutating_allowed` es el wrapper de compatibilidad para ``main_matriz.py``:
mantiene el nombre de variable ``VERIFY_MUTATING``, la lectura en vivo de
``matriz_client`` y el sandbox remarkets, y delega la decisión.

**Por qué un driver NO puede reusar el gate de otro paquete.** La segunda pata de
:func:`mutating_allowed` valida la base URL de *matriz*. Invocada desde cualquier
otro driver esa pata es **vacua**: el host de matriz no tiene nada que ver con el
target del driver que llama, así que la variable de entorno sola alcanzaría para
habilitar escrituras contra cualquier base URL. Cada driver debe llamar a
:func:`mutating_allowed_for` con SU host esperado y SU variable de entorno
(scoped por paquete: ``main_verify.py`` corre los seis drivers en un lote, así que
reusar un nombre de variable armaría dos gates a la vez).

Uso típico desde un driver::

    from verification.mutation_gate import mutating_allowed_for

    gate = mutating_allowed_for(
        env_var="MARKET_DATA_VERIFY_MUTATING",
        base_url=_env_base_url(),
        expected_host="market-data-develop.bbsa.com.ar",
    )
    if gate:
        ...  # recién aquí es seguro ejercitar la superficie mutante

La base URL se lee en el momento del guard desde el estado resuelto en vivo y
nunca desde una constante hardcodeada, para que un ``configure(base_url=prod)`` en
runtime quede atrapado (Pitfall 5). El valor se usa sólo para decidir el gate y
NUNCA se imprime (A2 / T-27-19).
"""

from __future__ import annotations

import os
from urllib.parse import urlsplit

__all__ = ["mutating_allowed", "mutating_allowed_for"]

# Línea de rechazo verbatim, compartida por ambos gates para que no puedan
# derivar. Es load-bearing: la asertan los tests de back-compat de ambito y la
# consume (por su AUSENCIA de dos puntos) el clasificador de ``main_verify.py``.
_SKIP_LINE = "SKIPPED (mutating, guard off)"

# Único host donde es seguro mutar en matriz (alta/cancelación de órdenes): el
# sandbox remarkets de Primary. Producción es ``api.primary.com.ar``; cualquier
# otro host cae en fail-closed. Se compara contra el HOSTNAME exacto, nunca
# contra un substring de la URL (CR-02 / Pitfall 5).
_SANDBOX_HOST = "api.remarkets.primary.com.ar"


def mutating_allowed_for(*, env_var: str, base_url: str, expected_host: str) -> bool:
    """Doble gate package-agnostic: opt-in de entorno Y hostname exacto (D-01).

    Puro salvo por ``os.getenv`` y el ``print`` de rechazo; no construye clientes,
    no emite HTTP y no importa ningún paquete.

    Pata 1 — ``os.environ[env_var]`` debe ser el literal ``"1"``. ``"true"``,
    ``"yes"``, ``"0"`` y ``""`` NO habilitan (T-27-14).

    Pata 2 — ``urlsplit(base_url).hostname`` debe ser IGUAL a ``expected_host``.
    Nunca ``in``, nunca ``endswith``: un ``…bbsa.com.ar.attacker.example`` pasaría
    un substring-match, y un ``https://host-esperado@attacker.example`` mete el
    host esperado en el userinfo, no en el authority (T-27-02). Una URL malformada
    (``hostname is None``, o un parse que levanta ``ValueError`` por brackets IPv6
    desbalanceados) cae en fail-closed.
    """
    if os.getenv(env_var) != "1":
        print(_SKIP_LINE)
        return False
    try:
        actual_host = urlsplit(base_url).hostname
    except ValueError:
        # URL imparseable (p.ej. `https://[oops/api`): fail closed, nunca crash.
        print(_SKIP_LINE)
        return False
    if actual_host != expected_host:
        print(_SKIP_LINE)  # host inesperado (o None) -> nunca mutar
        return False
    return True


def mutating_allowed() -> bool:
    """Back-compat matriz: ``VERIFY_MUTATING=1`` Y base URL remarkets (D-16).

    Wrapper delgado sobre :func:`mutating_allowed_for` que conserva las partes
    matriz-específicas. La pata del entorno se evalúa ANTES del import del
    cliente, de modo que un driver sin ``matriz_client`` instalado rechace
    limpiamente en lugar de levantar ``ImportError``.
    """
    if os.getenv("VERIFY_MUTATING") != "1":
        print(_SKIP_LINE)
        return False
    # Import perezoso: `matriz_client` sólo está instalado en el entorno del
    # propio paquete (uv run --package matriz-client). Importarlo a nivel de
    # módulo rompería el import zero-config del barrel desde los otros drivers
    # (que corren en entornos donde matriz_client no está instalado). Se importa
    # aquí, en el único punto donde el gate realmente se evalúa (main_matriz.py),
    # garantizando que el módulo esté disponible.
    import matriz_client

    base = matriz_client.client._base_url  # estado resuelto en vivo; sólo lectura
    return mutating_allowed_for(
        env_var="VERIFY_MUTATING",
        base_url=base,
        expected_host=_SANDBOX_HOST,
    )
