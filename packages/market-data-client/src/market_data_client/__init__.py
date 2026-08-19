"""Cliente HTTP (sync y async) para la API de market-data (primary-extractor).

Auth0 ``client_credentials`` (machine-to-machine): el cliente cachea el
``access_token`` y lo refresca re-corriendo el mismo grant antes del
vencimiento — re-autenticar ES el refresh, sin token de rotación (D-05).

Sync (API a nivel módulo — delega al default Client)::

    import market_data_client

    health = market_data_client.get_health()

Sync (API basada en clase)::

    from market_data_client import Client

    with Client() as client:
        health = client.get_health()

Async::

    from market_data_client import aio

    async with aio.AsyncClient() as client:
        health = await client.get_health()
"""

# Phase 20 CORE-MD-01 / LOG-01: attach NullHandler + RedactingFilter to the
# package logger BEFORE any other import — library convention per Python Logging
# HOWTO. So no credential (Bearer / client_secret / access_token) can reach a
# downstream handler before the redaction filter is installed. NEVER touches
# logging.root. The ``del`` cleanup prevents ``_logging_attach`` from leaking as
# a top-level package attribute.
from market_data_client import _logging as _logging_attach

_logging_attach.attach()
del _logging_attach

from market_data_client.aio import AsyncClient  # noqa: E402
from market_data_client.client import (  # noqa: E402
    Client,
    _get_default,
    add_holidays,
    configure,
    create_symbol,
    create_symbols,
    delete_calendar_config,
    delete_holiday,
    get_calendar,
    get_calendar_config,
    get_health,
    get_health_feed,
    get_instruments,
    get_latest,
    get_latest_batch,
    get_market_data,
    get_segments,
    get_symbols,
    preview_calendar_config,
    set_calendar_config,
    update_symbol,
)
from market_data_client.exceptions import (  # noqa: E402
    MarketDataAPIError,
    MarketDataAuthError,
    MarketDataDecodeError,
    MarketDataError,
    MarketDataMutationNotAllowedError,
    MarketDataRateLimitError,
)
from market_data_client.models import (  # noqa: E402
    CalendarConfig,
    CalendarDay,
    HolidayIn,
    HolidaysIn,
    Instrument,
    LatestRequest,
    MarketDataSnapshot,
    MarketHoursIn,
    NewSymbol,
    NewSymbols,
    Segment,
    Symbol,
    SymbolPatch,
)

# ``_get_default`` is intentionally re-exported (private name with leading
# underscore — NOT in ``__all__``) so tests and helpers can access it via
# ``market_data_client._get_default()`` without reaching into ``.client``.
__all__ = [
    "AsyncClient",
    "CalendarConfig",
    "CalendarDay",
    "Client",
    "HolidayIn",
    "HolidaysIn",
    "Instrument",
    "LatestRequest",
    "MarketDataAPIError",
    "MarketDataAuthError",
    "MarketDataDecodeError",
    "MarketDataError",
    "MarketDataMutationNotAllowedError",
    "MarketDataRateLimitError",
    "MarketDataSnapshot",
    "MarketHoursIn",
    "NewSymbol",
    "NewSymbols",
    "Segment",
    "Symbol",
    "SymbolPatch",
    "add_holidays",
    "configure",
    "create_symbol",
    "create_symbols",
    "delete_calendar_config",
    "delete_holiday",
    "get_calendar",
    "get_calendar_config",
    "get_health",
    "get_health_feed",
    "get_instruments",
    "get_latest",
    "get_latest_batch",
    "get_market_data",
    "get_segments",
    "get_symbols",
    "preview_calendar_config",
    "set_calendar_config",
    "update_symbol",
]

# Suppress ruff F401 for the deliberate private re-export.
_ = _get_default

__version__ = "0.4.0"
