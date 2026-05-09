"""Smoke test del paquete `wallets-client`.

Uso::

    uv run --package wallets-client python main_wallets.py

Requiere las env vars WALLETS_BASE_URL y WALLETS_TOKEN (por ejemplo en
``packages/wallets-client/.env``).
"""

from __future__ import annotations

import wallets_client


def main() -> None:
    print(f"wallets_client v{wallets_client.__version__}")

    # Reconfigurar si se quisiera sobrescribir env vars en runtime:
    # wallets_client.configure(base_url="https://api.wallets.example", token="...")

    print("-> _request('GET', '/health')")
    try:
        resp = wallets_client._request("GET", "/health")  # type: ignore[attr-defined]
        print(f"   {resp.status_code} {resp.text[:200]}")
    except wallets_client.WalletsClientError as exc:
        print(f"   error: {exc}")


if __name__ == "__main__":
    main()
