"""Inyección de transporte: validación de tipo y la carrera `aclose` / `configure`.

Fase 32 WR-07 y CR-02. Dos defectos distintos sobre el mismo campo,
``_ClientState.http_client``:

CR-02 -- ``http_client`` (junto con ``token`` / ``token_expires_at``) existía en
``AsyncClient.__init__`` y en ambos ``configure()``, pero **no** en
``Client.__init__``. Un consumidor que escribía código sync/async simétrico se
comía un ``TypeError: unexpected keyword argument 'http_client'`` del lado sync.

WR-07 -- el campo se muta bajo ``_state.client_lock`` en
``_ensure_http_client``, pero ``configure(http_client=...)`` lo escribía suelto
desde un ``def`` plano, y ``aclose()`` lo ponía en ``None`` DESPUÉS de un
``await``. La ventana entre ese ``await`` y esa escritura es real::

    task A: await client.aclose()
            -> lee el transporte viejo
            -> await http_client.aclose()        # <-- punto de suspensión
    task B: aio.configure(http_client=NUEVO)     # _state.http_client = NUEVO
    task A:    _state.http_client = None         # NUEVO descartado, sin cerrar

El ``NUEVO`` quedaba en el piso y el próximo request construía un tercer
cliente: justo el leak de connection pool que el ``ResourceWarning`` de
``configure()`` existe para advertir, causado por el código que lo emite. El
remedio que documentaba el docstring ("llamá ``aclose()`` antes de
``configure(...)``") sólo cubre el orden inverso.

El segundo defecto de WR-07 es de tipos: ``http_client`` es una entrada pública
alcanzable desde un caller sin anotaciones, y el único chequeo en runtime sobre
el objeto guardado era un ``assert isinstance`` en ``aclose()`` /
``_ensure_http_client()``. Bajo ``python -O`` esos asserts desaparecen y un
``httpx.Client`` entregado a ``aio.configure`` reaparecía como
``AttributeError: 'Client' object has no attribute 'aclose'``, lejos de la
llamada culpable. Las cuatro entradas (dos ``configure``, dos ``__init__``)
validan ahora con ``TypeError``.
"""

from __future__ import annotations

import httpx
import pytest

import market_data_client
from market_data_client import Client, aio


class _SuspendingAsyncClient(httpx.AsyncClient):
    """Un ``httpx.AsyncClient`` cuyo ``aclose()`` corre un callback y cede el loop.

    Es la única forma de materializar la ventana de WR-07 de manera
    determinística: el callback corre EXACTAMENTE en el punto de suspensión que
    ``aclose()`` de ``AsyncClient`` tiene sobre ``await http_client.aclose()``.
    """

    def __init__(self) -> None:
        super().__init__()
        self.on_close: object = None

    async def aclose(self) -> None:
        callback = self.on_close
        if callable(callback):
            callback()
        await super().aclose()


async def test_aclose_does_not_discard_a_transport_injected_mid_await() -> None:
    """WR-07: el ``= None`` final de ``aclose()`` no debe pisar un reemplazo.

    Sin el guard de identidad, el transporte que la task B inyectó mientras la
    task A esperaba quedaba descartado y sin cerrar.
    """
    old = _SuspendingAsyncClient()
    replacement = httpx.AsyncClient()
    client = aio._get_default()
    client._state.http_client = old

    # Corre DENTRO de `await old.aclose()`, que es el punto de suspensión.
    old.on_close = lambda: aio.configure(http_client=replacement)

    try:
        await client.aclose()

        assert client._state.http_client is replacement, (
            "aclose() descartó el transporte inyectado durante su propio await; "
            "el reemplazo queda sin cerrar y el próximo request construye un tercero"
        )
    finally:
        client._state.http_client = None
        await replacement.aclose()


async def test_aclose_still_clears_the_transport_it_closed() -> None:
    """El complemento: sin interleaving, ``aclose()`` sigue limpiando el campo.

    Sin esta pata, un guard de identidad roto (que nunca limpiara) sería
    indistinguible del correcto, y ``aclose()`` dejaría de ser idempotente.
    """
    client = aio._get_default()
    client._state.http_client = httpx.AsyncClient()

    await client.aclose()

    assert client._state.http_client is None


def test_sync_configure_rejects_an_async_transport() -> None:
    """WR-07: el chequeo de tipo es un ``TypeError``, no un ``assert``."""
    wrong = httpx.AsyncClient()
    with pytest.raises(TypeError, match=r"httpx\.Client"):
        market_data_client.configure(http_client=wrong)  # type: ignore[arg-type]


def test_async_configure_rejects_a_sync_transport() -> None:
    """WR-07, la pata que el review midió: un ``httpx.Client`` en la superficie async.

    Test SÍNCRONO a propósito: ``aio.configure`` es un ``def`` plano, y es
    justamente por eso que un caller sync puede entregarle el transporte
    equivocado sin que nada lo detenga hasta el primer ``await``.
    """
    with httpx.Client() as wrong, pytest.raises(TypeError, match=r"httpx\.AsyncClient"):
        aio.configure(http_client=wrong)  # type: ignore[arg-type]


def test_sync_client_constructor_accepts_an_injected_transport() -> None:
    """CR-02: ``Client.__init__`` acepta los tres kwargs que sólo tenía el async."""
    with httpx.Client() as transport:
        client = Client(
            token="seeded",
            token_expires_at=1.0,
            http_client=transport,
        )
        assert client._state.http_client is transport
        assert client._state.token == "seeded"
        assert client._state.token_expires_at == 1.0


def test_sync_client_constructor_rejects_an_async_transport() -> None:
    """CR-02 + WR-07: el constructor valida con el mismo ``TypeError``."""
    wrong = httpx.AsyncClient()
    with pytest.raises(TypeError, match=r"httpx\.Client"):
        Client(http_client=wrong)  # type: ignore[arg-type]


def test_async_client_constructor_rejects_a_sync_transport() -> None:
    """La imagen espejo, exigida por el constraint dual sync/async de CLAUDE.md."""
    with httpx.Client() as wrong, pytest.raises(TypeError, match=r"httpx\.AsyncClient"):
        aio.AsyncClient(http_client=wrong)  # type: ignore[arg-type]
