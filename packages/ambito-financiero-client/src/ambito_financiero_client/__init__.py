"""Cliente HTTP (sync y async) para Ámbito Financiero.

Sync (compat top-level)::

    import ambito_financiero_client as ambito
    precio = ambito.get_dollar_banco_nacion(date)

Sync (per-instance, v1.1+)::

    from ambito_financiero_client import Client
    with Client() as c:
        precio = c.get_dollar_banco_nacion(date)

Async::

    from ambito_financiero_client import aio
    precio = await aio.get_dollar_banco_nacion(date)
    await aio.aclose()
"""

# Phase 8 LOG-01: attach NullHandler + RedactingFilter to package logger BEFORE
# any other imports — library convention per Python Logging HOWTO. NEVER touches
# logging.root. The ``del`` cleanup prevents ``_logging_attach`` from leaking as a
# top-level package attribute (snapshot Pitfall 8 prevention).
from ambito_financiero_client import _logging as _logging_attach

_logging_attach.attach()
del _logging_attach

from ambito_financiero_client.aio import AsyncClient  # noqa: E402
from ambito_financiero_client.client import (  # noqa: E402
    Client,
    configure,
    get_dollar_banco_nacion,
)
from ambito_financiero_client.exceptions import (  # noqa: E402
    AmbitoFinancieroAPIError,
    AmbitoFinancieroAuthError,
    AmbitoFinancieroClientError,
    AmbitoFinancieroNoDataError,
    AmbitoFinancieroRateLimitError,
)

__all__ = [
    "AmbitoFinancieroAPIError",
    "AmbitoFinancieroAuthError",
    "AmbitoFinancieroClientError",
    "AmbitoFinancieroNoDataError",
    "AmbitoFinancieroRateLimitError",
    "AsyncClient",
    "Client",
    "configure",
    "get_dollar_banco_nacion",
]

__version__ = "0.2.0"
