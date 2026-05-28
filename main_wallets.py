"""Smoke test del paquete `wallets-client`.

Uso::

    uv run --package wallets-client python main_wallets.py

Requiere las env vars WALLETS_BASE_URL y WALLETS_TOKEN (por ejemplo en
``packages/wallets-client/.env``).
"""

from __future__ import annotations

import os
import sys

from verification import require_env, safe_print

import wallets_client


def main() -> None:
    if not require_env("wallets-client", ["WALLETS_TOKEN", "WALLETS_BASE_URL"]):
        sys.exit(0)

    # Token resuelto, filtrado a valor no trivial (>= 4 chars): si la respuesta
    # cruda lo reflejara, safe_print lo enmascara.
    secrets = [v for v in (os.getenv("WALLETS_TOKEN"),) if v and len(v) >= 4]

    print(f"wallets_client v{wallets_client.__version__}")

    # Reconfigurar si se quisiera sobrescribir env vars en runtime:
    # wallets_client.configure(base_url="https://api.wallets.example", token="...")

    print("-> _request('GET', '/health')")
    try:
        resp = wallets_client._request("GET", "/health")  # type: ignore[attr-defined]
        safe_print(f"   {resp.status_code} {resp.text[:200]}", secrets)
    except wallets_client.WalletsClientError as exc:
        safe_print(f"   error: {exc}", secrets)


if __name__ == "__main__":
    main()
