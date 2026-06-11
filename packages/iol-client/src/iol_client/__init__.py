"""Cliente HTTP (sync y async) para Invertir Online (IOL).

Sync (top-level shim, back-compat 100%)::

    import iol_client
    iol_client.login()
    quote = iol_client.get_quote("GGAL")

Sync (class-based, Phase 6+)::

    from iol_client import Client
    with Client(username="alice", password="secret") as c:
        quote = c.get_quote("GGAL")

Async::

    from iol_client import aio
    await aio.login()
    quote = await aio.get_quote("GGAL")
    await aio.aclose()
"""

from iol_client.client import (
    Client,
    InstrumentType,
    _get_default,
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

# ``_get_default`` is intentionally re-exported (private name with leading
# underscore — NOT in ``__all__``) so tests and snapshot-helpers can access
# it via ``iol_client._get_default()`` without reaching into ``.client``.
__all__ = [
    "Client",
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

# Suppress ruff F401 for the deliberate private re-export.
_ = _get_default

__version__ = "0.1.1"
