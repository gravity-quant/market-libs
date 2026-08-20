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

# Phase 8 LOG-01: attach NullHandler + RedactingFilter to package logger BEFORE
# any other imports — library convention per Python Logging HOWTO. NEVER touches
# logging.root. The ``del`` cleanup prevents ``_logging_attach`` from leaking as a
# top-level package attribute (snapshot Pitfall 8 prevention).
from iol_client import _logging as _logging_attach

_logging_attach.attach()
del _logging_attach

from iol_client.aio import AsyncClient  # noqa: E402
from iol_client.client import (  # noqa: E402
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
from iol_client.exceptions import (  # noqa: E402
    IOLAPIError,
    IOLAuthError,
    IOLClientError,
    IOLDecodeError,
    IOLRateLimitError,
)
from iol_client.models import (  # noqa: E402
    Cotizacion,
    Punta,
    SafeModel,
    Titulo,
)

# ``_get_default`` is intentionally re-exported (private name with leading
# underscore — NOT in ``__all__``) so tests and snapshot-helpers can access
# it via ``iol_client._get_default()`` without reaching into ``.client``.
__all__ = [
    "AsyncClient",
    "Client",
    "Cotizacion",
    "IOLAPIError",
    "IOLAuthError",
    "IOLClientError",
    "IOLDecodeError",
    "IOLRateLimitError",
    "InstrumentType",
    "Punta",
    "SafeModel",
    "Titulo",
    "configure",
    "get_historical_quotes",
    "get_instruments",
    "get_instruments_by_type",
    "get_quote",
    "login",
]

# Suppress ruff F401 for the deliberate private re-export.
_ = _get_default

__version__ = "0.2.0"
