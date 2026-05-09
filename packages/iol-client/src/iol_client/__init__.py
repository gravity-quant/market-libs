"""Cliente HTTP (sync y async) para Invertir Online (IOL).

Sync::

    import iol_client
    iol_client.login()
    quote = iol_client.get_quote("GGAL")

Async::

    from iol_client import aio
    await aio.login()
    quote = await aio.get_quote("GGAL")
    await aio.aclose()
"""

from iol_client.client import (
    InstrumentType,
    configure,
    get_historical_quotes,
    get_instruments,
    get_instruments_by_type,
    get_quote,
    login,
)
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
    "InstrumentType",
    "configure",
    "get_historical_quotes",
    "get_instruments",
    "get_instruments_by_type",
    "get_quote",
    "login",
]

__version__ = "0.1.1"
