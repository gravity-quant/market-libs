"""Cliente HTTP (sync y async) para Wallets.

Sync::

    import wallets_client
    # configurar via env vars o wallets_client.configure(...)

Async::

    from wallets_client import aio
    await aio.aclose()
"""

from wallets_client.client import configure
from wallets_client.exceptions import (
    WalletsAPIError,
    WalletsAuthError,
    WalletsClientError,
    WalletsRateLimitError,
)

__all__ = [
    "WalletsAPIError",
    "WalletsAuthError",
    "WalletsClientError",
    "WalletsRateLimitError",
    "configure",
]

__version__ = "0.1.0"
