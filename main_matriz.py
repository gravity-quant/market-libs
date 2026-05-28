"""Smoke test del paquete `matriz-client` (Primary API / MATBA ROFEX).

Uso::

    uv run --package matriz-client python main_matriz.py

Requiere las env vars PRIMARY_USER y PRIMARY_PASSWORD (por ejemplo en
``packages/matriz-client/.env``). PRIMARY_BASE_URL es opcional y por
defecto apunta a remarkets (sandbox).
"""

from __future__ import annotations

import os
import sys

from verification import mutating_allowed, require_env, safe_print

import matriz_client as primary


def main() -> None:
    if not require_env("matriz-client", ["PRIMARY_USER", "PRIMARY_PASSWORD"]):
        sys.exit(0)

    # Credenciales resueltas, filtradas a valores no triviales (>= 4 chars).
    secrets = [
        v for v in (os.getenv("PRIMARY_USER"), os.getenv("PRIMARY_PASSWORD")) if v and len(v) >= 4
    ]

    print("-> get_segments()  (login automático en la primera llamada)")
    segments = primary.get_segments()
    print(f"   {len(segments)} segments")
    for seg in segments[:3]:
        safe_print(f"   - {seg}", secrets)

    print("-> get_all_instruments()  [primeros 3]")
    instruments = primary.get_all_instruments()
    print(f"   total: {len(instruments)}")
    for inst in instruments[:3]:
        safe_print(f"   - {inst}", secrets)

    # Superficie mutante (alta/cancelación de órdenes): doble compuerta (HARN-02/
    # D-16). Por defecto inalcanzable -> imprime `SKIPPED (mutating, guard off)`.
    # NOTE: por REQUIREMENTS Out of Scope, el alta de órdenes nunca se ejecuta en
    # vivo (ni en sandbox); esta rama es el cableado belt-and-suspenders que prueba
    # que el gate es alcanzable desde el driver, no una mutación real.
    print("-> superficie mutante (órdenes)  [gateada por mutating_allowed()]")
    if mutating_allowed():
        # Inalcanzable salvo VERIFY_MUTATING=1 + base URL remarkets. Aun así, no
        # se ejercita el alta real de órdenes (Out of Scope): sólo se marca como
        # la rama donde recién sería seguro hacerlo.
        print("   (guard ON) — alta de órdenes deshabilitada por scope; no se muta")


if __name__ == "__main__":
    main()
