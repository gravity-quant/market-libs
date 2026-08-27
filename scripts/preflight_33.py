#!/usr/bin/env python
"""Pre-flight de autenticación en vivo para la Phase 33 (D-13, T-33-28).

Antes de contar una sola divergencia, este script **mide** —no asume— que cada
paquete en scope puede autenticarse contra su vendor real. La distinción importa
porque un censo producido con credenciales vencidas no se lee como un error: se
lee como un paquete limpio. Ese es exactamente el modo de falla de repudio que
T-33-28 nombra, y la única defensa es medir la autenticación antes de que exista
cualquier número.

Contrato (extiende el de ``verification/env_gate.py:32-41`` de presencia de
variables a autenticación real):

- Imprime **exactamente una línea por paquete**, con una de tres formas::

      <pkg>: AUTH OK
      <pkg>: AUTH FAIL <NombreDeClaseDeExcepción>
      <pkg>: n/a (sin auth por diseño)

- **Nunca** imprime el cuerpo de una excepción: sólo ``type(exc).__name__``.
  ``str(exc)`` / ``repr(exc)`` quedan prohibidos porque los cuerpos de error de
  estos vendors cargan plausiblemente identificadores de cuenta; es el mismo
  criterio que ``main_iol.py::_redacted_exc`` ya aplica en el harness.
- **Nunca** imprime una credencial, ni un token, ni una URL resuelta.
- **Nunca** levanta hacia afuera: un paquete que falla no puede impedir que se
  mida el siguiente.
- Sale con código distinto de cero si alguno de los cuatro paquetes credencializados
  imprimió ``AUTH FAIL``, para que el runner corte antes de contar.

Por qué es un archivo ``.py`` real y no un ``python -c``: ``find_dotenv()`` de
``python-dotenv`` arranca desde el frame que lo llama y **cae a ``os.getcwd()``
cuando ``__main__`` no tiene ``__file__``**. Con ``-c`` y sin ``.env`` en la raíz
del repo, la búsqueda termina en el cwd, no encuentra nada, y el script reporta
todas las credenciales ausentes: un ``AUTH FAIL`` fabricado por el modo de
invocación (P-10, reproducido en ejecución).

Un paquete que imprime ``AUTH FAIL`` NO se cuenta como cero divergencias: se
registra en ``33-CENSUS.md`` como ``SKIPPED — credenciales`` y se rutea al
fallback de operador de la Phase 23.

Uso::

    uv run python scripts/preflight_33.py
"""

from __future__ import annotations

import contextlib
import importlib
import sys

# (slug del paquete, módulo importable, nombre del método de auth del Client).
#
# ``market-data-client`` no expone un ``login()``: su grant de client-credentials
# de Auth0 corre dentro de ``_ensure_token()``, que es el punto donde el token se
# pide de verdad. Se usa ese nombre a propósito — un chequeo que no dispare el
# round trip real sería justamente el verde que no inspecciona nada.
_CREDENTIALED: tuple[tuple[str, str, str], ...] = (
    ("higyrus-client", "higyrus_client", "login"),
    ("iol-client", "iol_client", "login"),
    ("matriz-client", "matriz_client", "login"),
    ("market-data-client", "market_data_client", "_ensure_token"),
)

# Ámbito Financiero es scraping público: no tiene auth por diseño (D-12), así que
# no tiene nada que medir acá. Se lista igual para que la salida tenga una línea
# por cada paquete en scope y la ausencia de una línea sea siempre un error.
_NO_AUTH: tuple[str, ...] = ("ambito-financiero-client",)


def _check(module_name: str, auth_method: str) -> str | None:
    """Autentica una vez. Devuelve ``None`` si salió bien, o el nombre de la clase.

    Todo el cuerpo corre dentro de un ``try`` único: importar el paquete,
    construir el ``Client`` por defecto y disparar el grant son tres puntos de
    falla distintos y cualquiera de los tres significa lo mismo para el llamador
    —este paquete no puede autenticarse— así que los tres se reportan igual.

    Sólo se extrae ``type(exc).__name__``. Nada más de la excepción se toca.
    """
    client = None
    try:
        module = importlib.import_module(module_name)
        client = module.Client()
        getattr(client, auth_method)()
    except Exception as exc:
        # Cualquier falla —import, construcción o grant— significa lo mismo:
        # este paquete no autentica. Sólo se extrae el nombre de la clase.
        return type(exc).__name__
    finally:
        close = getattr(client, "close", None)
        if callable(close):
            # Cerrar es best-effort: un fallo acá no cambia el veredicto de auth
            # y no debe convertirse en un AUTH FAIL fabricado.
            with contextlib.suppress(Exception):
                close()
    return None


def main() -> int:
    """Imprime una línea de estado por paquete; devuelve 1 si alguna falló."""
    failed = False
    for slug, module_name, auth_method in _CREDENTIALED:
        error_class = _check(module_name, auth_method)
        if error_class is None:
            print(f"{slug}: AUTH OK")
        else:
            print(f"{slug}: AUTH FAIL {error_class}")
            failed = True
    for slug in _NO_AUTH:
        print(f"{slug}: n/a (sin auth por diseño)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
