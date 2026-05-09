"""Smoke test del paquete `iol-client` (Invertir Online).

Uso::

    uv run --package iol-client python main_iol.py

Requiere las env vars IOL_USER e IOL_PASSWORD (por ejemplo en
``packages/iol-client/.env``). IOL_BASE_URL es opcional.
"""

from __future__ import annotations

import iol_client


def main() -> None:
    print(f"iol_client v{iol_client.__version__}")

    print("-> login()")
    token = iol_client.login()
    print(f"   token: {token[:12]}...")


if __name__ == "__main__":
    main()
