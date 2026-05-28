"""Smoke test del paquete `higyrus-client`.

Uso::

    uv run --package higyrus-client python main_higyrus.py

Requiere las env vars HIGYRUS_BASE_URL, HIGYRUS_USER, HIGYRUS_PASSWORD
(y opcionalmente HIGYRUS_CLIENT_ID), por ejemplo en
``packages/higyrus-client/.env``.
"""

from __future__ import annotations

import os
import sys

from verification import require_env, safe_print

import higyrus_client


def main() -> None:
    if not require_env(
        "higyrus-client",
        ["HIGYRUS_USER", "HIGYRUS_PASSWORD", "HIGYRUS_BASE_URL"],
    ):
        sys.exit(0)

    # Credenciales resueltas, filtradas a valores no triviales (>= 4 chars): se
    # usan como segunda capa de defensa por si un payload crudo las reflejara.
    secrets = [
        v for v in (os.getenv("HIGYRUS_USER"), os.getenv("HIGYRUS_PASSWORD")) if v and len(v) >= 4
    ]

    print(f"higyrus_client v{higyrus_client.__version__}")

    print("-> get_health()  (login automático en la primera llamada)")
    safe_print(f"   {higyrus_client.get_health()}", secrets)

    print("-> get_listado_cuentas(estado='alta')")
    cuentas = higyrus_client.get_listado_cuentas()
    print(f"   {len(cuentas)} cuentas")
    if cuentas:
        safe_print(f"   primera: {cuentas[0]}", secrets)


if __name__ == "__main__":
    main()
