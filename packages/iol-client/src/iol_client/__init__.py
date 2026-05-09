"""Cliente HTTP (sync y async) para Invertir Online (IOL).

Sync::

    import iol_client
    iol_client.login()

Async::

    from iol_client import aio
    await aio.login()
    await aio.aclose()
"""

from iol_client.client import configure, login
from iol_client.exceptions import (
    IOLAPIError,
    IOLAuthError,
    IOLClientError,
    IOLRateLimitError,
)

__all__ = [
    "IOLAPIError",
    "IOLAuthError",
    "IOLClientError",
    "IOLRateLimitError",
    "configure",
    "login",
]

__version__ = "0.1.0"
