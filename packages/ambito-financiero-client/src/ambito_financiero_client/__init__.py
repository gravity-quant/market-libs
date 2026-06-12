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

from ambito_financiero_client.aio import AsyncClient
from ambito_financiero_client.client import (
    Client,
    configure,
    get_dollar_banco_nacion,
)
from ambito_financiero_client.exceptions import (
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

__version__ = "0.1.1"
