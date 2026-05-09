"""Cliente HTTP (sync y async) para Ámbito Financiero.

Sync::

    import ambito_financiero_client as ambito
    precio = ambito.get_dollar_banco_nacion(date)

Async::

    from ambito_financiero_client import aio
    precio = await aio.get_dollar_banco_nacion(date)
    await aio.aclose()
"""

from ambito_financiero_client.client import (
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
    "configure",
    "get_dollar_banco_nacion",
]

__version__ = "0.1.1"
