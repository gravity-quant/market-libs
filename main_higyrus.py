"""Smoke test del paquete `higyrus-client`.

Uso::

    uv run --package higyrus-client python main_higyrus.py

Requiere las env vars HIGYRUS_BASE_URL, HIGYRUS_USER, HIGYRUS_PASSWORD
(y opcionalmente HIGYRUS_CLIENT_ID), por ejemplo en
``packages/higyrus-client/.env``.
"""

from __future__ import annotations

import higyrus_client


def main() -> None:
    print(f"higyrus_client v{higyrus_client.__version__}")

    print("-> get_health()  (login automático en la primera llamada)")
    print(f"   {higyrus_client.get_health()}")

    print("-> get_listado_cuentas(estado='alta')")
    cuentas = higyrus_client.get_listado_cuentas()
    print(f"   {len(cuentas)} cuentas")
    if cuentas:
        print(f"   primera: {cuentas[0]}")


if __name__ == "__main__":
    main()
