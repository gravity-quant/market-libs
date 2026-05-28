"""Smoke test del paquete `iol-client` (Invertir Online).

Uso::

    uv run --package iol-client python main_iol.py

Requiere las env vars IOL_USER e IOL_PASSWORD (por ejemplo en
``packages/iol-client/.env``). IOL_BASE_URL es opcional.
"""

from __future__ import annotations

import sys

from verification import redact, require_env

import iol_client


def main() -> None:
    if not require_env("iol-client", ["IOL_USER", "IOL_PASSWORD"]):
        sys.exit(0)

    print(f"iol_client v{iol_client.__version__}")

    print("-> login()")
    token = iol_client.login()
    print(f"   token: {redact(token)}")


if __name__ == "__main__":
    main()
