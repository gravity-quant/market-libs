"""Smoke test del paquete `matriz-client` (Primary API / MATBA ROFEX).

Uso::

    uv run --package matriz-client python main_matriz.py

Requiere las env vars PRIMARY_USER y PRIMARY_PASSWORD (por ejemplo en
``packages/matriz-client/.env``). PRIMARY_BASE_URL es opcional y por
defecto apunta a remarkets (sandbox).
"""

from __future__ import annotations

import matriz_client as primary


def main() -> None:
    print("-> get_segments()  (login automático en la primera llamada)")
    segments = primary.get_segments()
    print(f"   {len(segments)} segments")
    for seg in segments[:3]:
        print(f"   - {seg}")

    print("-> get_all_instruments()  [primeros 3]")
    instruments = primary.get_all_instruments()
    print(f"   total: {len(instruments)}")
    for inst in instruments[:3]:
        print(f"   - {inst}")


if __name__ == "__main__":
    main()
