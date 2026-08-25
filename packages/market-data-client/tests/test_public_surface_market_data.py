"""In-package public-surface + sync/async parity net for the write APIs.

Cubre las DOS superficies de escritura del paquete: symbols-write (Phase 25,
MUT-MD-01) y calendar-write (Phase 26, MUT-MD-02 — el trío de config
``set`` / ``delete`` / ``preview`` más el par de feriados ``add_holidays`` /
``delete_holiday``, con sus tres modelos de request).

The cross-package ``verification/test_public_surface.py`` and
``verification/test_sync_async_isolation.py`` EXCLUDE ``market_data_client`` (its
name is absent from their ``_PACKAGES`` lists), so neither guards this package's
export surface nor its sync/async name parity. This in-package net fills that gap
(RESEARCH Pitfall 2 / T-25-09 / T-26-10):

(a) each new public name is importable from ``market_data_client`` AND present in
    ``market_data_client.__all__``;
(b) sync ``Client`` and async ``AsyncClient`` expose identically-named mutation
    callables for both write surfaces;
(c) the module-level sync shims live on ``market_data_client`` and the async
    shims live on ``market_data_client.aio`` (async methods are NOT flat-namespace
    re-exported).

Cuatro de las pruebas de abajo son genéricas sobre las dos tuplas: extender
``_NEW_PUBLIC_NAMES`` / ``_MUTATION_METHODS`` extiende automáticamente la red.
La quinta (WR-02) NO usa lista alguna: deriva el conjunto esperado del propio
``models``, porque el modo de fallo que cubre es exactamente el de un nombre
nuevo que nadie se acordó de agregar a una lista.
"""

from __future__ import annotations

import market_data_client
from market_data_client import aio, models

_NEW_PUBLIC_NAMES = (
    # Phase 25 — symbols write (MUT-MD-01)
    "MarketDataMutationNotAllowedError",
    "NewSymbol",
    "NewSymbols",
    "SymbolPatch",
    "create_symbol",
    "create_symbols",
    "update_symbol",
    # Phase 26 — calendar write (MUT-MD-02)
    "HolidayIn",
    "HolidaysIn",
    "MarketHoursIn",
    "add_holidays",
    "delete_calendar_config",
    "delete_holiday",
    "preview_calendar_config",
    "set_calendar_config",
    # Phase 31 — ops endpoints (TYP-02)
    "AddHolidaysResult",
    "DeleteHolidayResult",
    "FeedIngestor",
    "FeedMarket",
    "FeedPipeline",
    "Health",
    "HealthAuth",
    "HealthFeed",
)

_MUTATION_METHODS = (
    # Phase 25 — symbols write (MUT-MD-01)
    "create_symbol",
    "create_symbols",
    "update_symbol",
    # Phase 26 — calendar write (MUT-MD-02)
    "add_holidays",
    "delete_calendar_config",
    "delete_holiday",
    "preview_calendar_config",
    "set_calendar_config",
)


# (a) export presence + __all__ membership -----------------------------------


def test_new_public_names_importable() -> None:
    """Each new public name is a real attribute of ``market_data_client``."""
    for name in _NEW_PUBLIC_NAMES:
        assert hasattr(market_data_client, name), f"{name} not importable from market_data_client"


def test_new_public_names_in_dunder_all() -> None:
    """Each new public name is declared in ``__all__`` (the export contract)."""
    for name in _NEW_PUBLIC_NAMES:
        assert name in market_data_client.__all__, f"{name} missing from __all__"


def test_models_dunder_all_covers_every_safemodel_subclass() -> None:
    """WR-02: ``models.__all__`` declares EVERY ``SafeModel`` subclass in the module.

    The two tests above only inspect the PACKAGE ``__all__``, so
    ``AddHolidaysResult`` and ``DeleteHolidayResult`` shipped absent from
    ``models.__all__`` while present in ``market_data_client.__all__`` — a
    ``from market_data_client.models import *`` silently omitted the two classes
    that this package's own ``_core`` and tests import by name. CONVENTIONS
    mandates an explicit ``__all__`` with ALL public names, so the check is
    derived from the module rather than from a second hand-maintained list.
    """
    declared = set(models.__all__)
    subclasses = {
        name
        for name, obj in vars(models).items()
        if isinstance(obj, type)
        and issubclass(obj, models.SafeModel)
        and obj.__module__ == models.__name__
    }
    assert subclasses <= declared, f"missing from models.__all__: {sorted(subclasses - declared)}"


# (b) sync/async method name parity ------------------------------------------


def test_sync_async_method_name_parity() -> None:
    """``Client`` and ``AsyncClient`` expose the same-named mutation callables."""
    for name in _MUTATION_METHODS:
        assert callable(getattr(market_data_client.Client, name, None)), (
            f"Client.{name} missing or not callable"
        )
        assert callable(getattr(aio.AsyncClient, name, None)), (
            f"AsyncClient.{name} missing or not callable"
        )


# (c) shim placement: sync flat namespace + async under aio ------------------


def test_sync_shims_on_flat_namespace() -> None:
    """The module-level sync shims are callable on ``market_data_client``."""
    for name in _MUTATION_METHODS:
        assert callable(getattr(market_data_client, name, None)), (
            f"module-level sync shim {name} missing or not callable"
        )


def test_async_shims_under_aio() -> None:
    """The async shims live under ``aio``; they are NOT flat-namespace re-exported."""
    for name in _MUTATION_METHODS:
        assert callable(getattr(aio, name, None)), f"aio.{name} missing or not callable"
    # Async methods must NOT leak into the flat namespace as the SAME object as
    # the async shim (the flat names are the SYNC shims — distinct objects).
    for name in _MUTATION_METHODS:
        assert getattr(market_data_client, name) is not getattr(aio, name), (
            f"{name}: flat-namespace shim must be the sync shim, not the async one"
        )
