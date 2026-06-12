"""Cliente HTTP asincrónico para Invertir Online (IOL).

API a nivel módulo (back-compat 100% con v1.0)::

    from iol_client import aio

    await aio.login()
    quote = await aio.get_quote("GGAL")
    await aio.aclose()

API basada en clase (nueva en Phase 6)::

    from iol_client import AsyncClient

    async with AsyncClient(username="alice", password="secret") as c:
        quote = await c.get_quote("GGAL")

El módulo expone un shim PEP 562 (read-only) que forwarda lecturas legacy
de ``_token``, ``_token_expires_at``, ``_refresh_token``, ``_token_lock``
y ``_client`` al ``_default_async_client._state.*``.

Cleanup contract (D-16): caller-responsible. El ``AsyncClient`` implementa
``aclose()`` + ``__aenter__/__aexit__``. NO hay ``atexit`` ni
``__del__``-driven cleanup (Pitfall #12). NO se llama ``load_dotenv()``
acá — eso vive en ``client.py`` (D-19) y se ejecuta como side effect del
import de ``InstrumentType``/``_raise_for_response``.

B8 lock-in: ``_raise_for_response`` se importa desde ``iol_client.client``
— NO se duplica. Replica el patrón ya documentado en ARCHITECTURE.md de
``aio.py`` importando ``InstrumentType`` desde ``client.py``.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import time
from typing import Any, Literal, Self

import httpx

from iol_client._state import (
    _REQUEST_TIMEOUT,
    _TOKEN_TTL_BUFFER_SECONDS,
    _ClientState,
)

# B8: import the shared, stateless helper + the InstrumentType alias from
# the sync module. Same import pattern already documented for
# InstrumentType in ARCHITECTURE.md; ``_raise_for_response`` follows the
# same shape (no shared state involved).
from iol_client.client import InstrumentType, _raise_for_response
from iol_client.exceptions import IOLAuthError


class AsyncClient:
    """Async client for the IOL REST API.

    Per-instance state lives in ``self._state`` (same :class:`_ClientState`
    dataclass shape as the sync ``Client``, but a different INSTANCE — NO
    shared mutable state between sync and async surfaces by construction).

    Locks (Pitfall #6): ``self._state.token_lock`` and
    ``self._client_lock`` are lazily created on first async use so they
    bind to whatever event loop is running. Creating an ``asyncio.Lock()``
    inside ``__init__`` would bind it to the loop alive at construction
    time, which is fragile under ``asyncio.run`` patterns.

    Pickle / deepcopy contract (D-23): NOT supported (httpx.AsyncClient
    owns a TCP pool + SSL context tied to a specific event loop).

    Cleanup contract (D-16): caller-responsible. Use ``async with`` or
    ``await client.aclose()``.
    """

    __slots__ = ("_client_lock", "_state")

    def __init__(
        self,
        *,
        base_url: str | None = None,
        username: str | None = None,
        password: str | None = None,
        token: str | None = None,
        token_expires_at: float | None = None,
    ) -> None:
        self._state = _ClientState()
        if base_url is not None:
            self._state.base_url = base_url.rstrip("/")
        if username is not None:
            self._state.username = username
        if password is not None:
            self._state.password = password
        if token is not None:
            self._state.token = token
        if token_expires_at is not None:
            self._state.token_expires_at = token_expires_at
        # Lazy — created in _ensure_http_client on first async use.
        self._client_lock: asyncio.Lock | None = None

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: object,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Release the underlying ``httpx.AsyncClient`` (idempotent)."""
        http_client = self._state.http_client
        if http_client is not None:
            assert isinstance(http_client, httpx.AsyncClient)
            await http_client.aclose()
            self._state.http_client = None

    def __repr__(self) -> str:
        password_repr = "'***'" if self._state.password else "''"
        token_repr = "'***'" if self._state.token else "None"
        refresh_repr = "'***'" if self._state.refresh_token else "None"
        return (
            f"IOLAsyncClient(base_url={self._state.base_url!r}, "
            f"username={self._state.username!r}, "
            f"password={password_repr}, "
            f"token={token_repr}, "
            f"refresh_token={refresh_repr})"
        )

    def __reduce__(self) -> Any:  # D-23
        raise TypeError(
            "IOLAsyncClient is not picklable; httpx.AsyncClient owns a TCP "
            "pool + SSL context bound to an event loop. Recreate in worker."
        )

    def __deepcopy__(self, memo: dict[int, Any]) -> AsyncClient:  # D-23
        raise TypeError(
            "IOLAsyncClient is not deepcopy-safe (httpx.AsyncClient owns "
            "TCP pool + SSL context). Recreate from configure() in the "
            "target context instead."
        )

    # ------------------------------------------------------------------
    # HTTP transport + OAuth (async, double-checked locking)
    # ------------------------------------------------------------------

    async def _ensure_http_client(self) -> httpx.AsyncClient:
        http_client = self._state.http_client
        if http_client is not None:
            assert isinstance(http_client, httpx.AsyncClient)
            return http_client
        if self._client_lock is None:
            self._client_lock = asyncio.Lock()
        async with self._client_lock:
            http_client = self._state.http_client
            if http_client is not None:
                assert isinstance(http_client, httpx.AsyncClient)
                return http_client
            new_client = httpx.AsyncClient(timeout=_REQUEST_TIMEOUT)
            self._state.http_client = new_client
            return new_client

    def _ensure_token_lock(self) -> asyncio.Lock:
        if self._state.token_lock is None:
            self._state.token_lock = asyncio.Lock()
        return self._state.token_lock

    async def _login_unlocked(self) -> str:
        """Caller MUST hold ``self._state.token_lock``."""
        if not self._state.username or not self._state.password:
            raise IOLAuthError(0, "IOL_USER y IOL_PASSWORD son requeridos")

        client = await self._ensure_http_client()
        resp = await client.post(
            f"{self._state.base_url}/token",
            data={
                "username": self._state.username,
                "password": self._state.password,
                "grant_type": "password",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if resp.is_error:
            _raise_for_response(resp)

        data: dict[str, Any] = resp.json()
        access_token = data.get("access_token")
        expires_in = data.get("expires_in", 900)
        if not isinstance(access_token, str) or not access_token:
            raise IOLAuthError(resp.status_code, "No access_token in response")

        self._state.token = access_token
        # CR-01 mirror: condicional, preserva refresh cacheado si server omite.
        new_refresh = data.get("refresh_token")
        if isinstance(new_refresh, str) and new_refresh:
            self._state.refresh_token = new_refresh
        self._state.token_expires_at = time.time() + float(expires_in) - _TOKEN_TTL_BUFFER_SECONDS
        return access_token

    async def _refresh_unlocked(self) -> str:
        """Caller MUST hold ``self._state.token_lock``.

        Pitfall 6: NO llamar ``self._ensure_token()`` / ``self._login_unlocked()``
        / ``self._request(...)`` adentro — re-adquirirían el lock y causarían
        deadlock. Solo httpx.post directo. ``_ensure_http_client`` usa un lock
        separado (``self._client_lock``), sin conflicto.
        """
        refresh_token = self._state.refresh_token
        if not refresh_token:
            raise IOLAuthError(0, "No refresh_token cached")

        client = await self._ensure_http_client()
        resp = await client.post(
            f"{self._state.base_url}/token",
            data={"refresh_token": refresh_token, "grant_type": "refresh_token"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if resp.is_error:
            _raise_for_response(resp)

        data: dict[str, Any] = resp.json()
        access_token = data.get("access_token")
        expires_in = data.get("expires_in", 900)
        if not isinstance(access_token, str) or not access_token:
            raise IOLAuthError(resp.status_code, "No access_token in refresh response")

        self._state.token = access_token
        new_refresh = data.get("refresh_token")
        if isinstance(new_refresh, str) and new_refresh:
            self._state.refresh_token = new_refresh
        self._state.token_expires_at = time.time() + float(expires_in) - _TOKEN_TTL_BUFFER_SECONDS
        return access_token

    async def login(self) -> str:
        lock = self._ensure_token_lock()
        async with lock:
            return await self._login_unlocked()

    async def _ensure_token(self) -> None:
        if self._state.token and time.time() < self._state.token_expires_at:
            return
        lock = self._ensure_token_lock()
        async with lock:
            if self._state.token and time.time() < self._state.token_expires_at:
                return
            if self._state.refresh_token:
                try:
                    await self._refresh_unlocked()
                    return
                except IOLAuthError:
                    pass
            await self._login_unlocked()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> httpx.Response:
        await self._ensure_token()
        lock = self._ensure_token_lock()
        async with lock:
            token = self._state.token
        assert token is not None

        client = await self._ensure_http_client()
        resp = await client.request(
            method,
            f"{self._state.base_url}{path}",
            params=params,
            json=json_body,
            headers={"Authorization": f"Bearer {token}"},
        )
        if resp.is_error:
            _raise_for_response(resp)
        return resp

    # ------------------------------------------------------------------
    # Public endpoint methods (mirror sync Client)
    # ------------------------------------------------------------------

    async def get_quote(
        self,
        simbolo: str,
        *,
        mercado: str = "bcba",
        plazo: str = "t2",
    ) -> dict[str, Any]:
        """Cotización actual de un título (async)."""
        resp = await self._request(
            "GET",
            f"/api/v2/{mercado}/Titulos/{simbolo}/Cotizacion",
            params={
                "model.mercado": mercado,
                "model.simbolo": simbolo,
                "model.plazo": plazo,
            },
        )
        data: dict[str, Any] = resp.json()
        return data

    async def get_historical_quotes(
        self,
        simbolo: str,
        desde: dt.date,
        hasta: dt.date,
        *,
        mercado: str = "bcba",
        ajustada: Literal["ajustada", "sinAjustar"] = "sinAjustar",
    ) -> list[dict[str, Any]]:
        """Serie histórica de cotizaciones diarias (async)."""
        resp = await self._request(
            "GET",
            f"/api/v2/{mercado}/Titulos/{simbolo}/Cotizacion/seriehistorica/"
            f"{desde:%Y-%m-%d}/{hasta:%Y-%m-%d}/{ajustada}",
        )
        data: list[dict[str, Any]] = resp.json()
        return data

    async def get_instruments(self, pais: str = "argentina") -> Any:
        """Listado de instrumentos cotizando en ``pais`` (async)."""
        resp = await self._request("GET", f"/api/v2/{pais}/Titulos/Cotizacion/Instrumentos")
        return resp.json()

    async def get_instruments_by_type(
        self,
        instrument_type: InstrumentType,
        *,
        pais: str = "argentina",
    ) -> list[dict[str, Any]]:
        """Listado de instrumentos por tipo y país (async)."""
        resp = await self._request("GET", f"/api/v2/Cotizaciones/{instrument_type}/{pais}/Todos")
        data: dict[str, Any] = resp.json()
        titulos: list[dict[str, Any]] = data.get("titulos", [])
        return titulos


# ----------------------------------------------------------------------
# Default-async-client lazy singleton + top-level shims
# ----------------------------------------------------------------------


_default_async_client: AsyncClient | None = None


def _get_default() -> AsyncClient:
    """Lazy access to the module-level default AsyncClient."""
    global _default_async_client
    if _default_async_client is None:
        _default_async_client = AsyncClient()
    return _default_async_client


def configure(
    *,
    base_url: str | None = None,
    username: str | None = None,
    password: str | None = None,
    token: str | None = None,
    token_expires_at: float | None = None,
    refresh_token: str | None = None,
) -> None:
    """Sobrescribe credenciales/URL en runtime con semántica carry-forward.

    Mirror del sync ``client.configure()``. Setting ``password=`` resetea
    token cacheado + refresh_token (v1.0 invariant). Otros kwargs ``None``
    se ignoran (carry-forward).
    """
    client = _get_default()
    if base_url is not None:
        client._state.base_url = base_url.rstrip("/")
    if username is not None:
        client._state.username = username
    if password is not None:
        client._state.password = password
        client._state.token = None
        client._state.refresh_token = None
        client._state.token_expires_at = 0.0
    if token is not None:
        client._state.token = token
    if token_expires_at is not None:
        client._state.token_expires_at = token_expires_at
    if refresh_token is not None:
        client._state.refresh_token = refresh_token


async def login() -> str:
    """Top-level async shim: delega al default AsyncClient."""
    return await _get_default().login()


async def aclose() -> None:
    """Top-level async shim: cierra el default AsyncClient (idempotente)."""
    await _get_default().aclose()


async def get_quote(
    simbolo: str,
    *,
    mercado: str = "bcba",
    plazo: str = "t2",
) -> dict[str, Any]:
    return await _get_default().get_quote(simbolo, mercado=mercado, plazo=plazo)


async def get_historical_quotes(
    simbolo: str,
    desde: dt.date,
    hasta: dt.date,
    *,
    mercado: str = "bcba",
    ajustada: Literal["ajustada", "sinAjustar"] = "sinAjustar",
) -> list[dict[str, Any]]:
    return await _get_default().get_historical_quotes(
        simbolo, desde, hasta, mercado=mercado, ajustada=ajustada
    )


async def get_instruments(pais: str = "argentina") -> Any:
    return await _get_default().get_instruments(pais)


async def get_instruments_by_type(
    instrument_type: InstrumentType,
    *,
    pais: str = "argentina",
) -> list[dict[str, Any]]:
    return await _get_default().get_instruments_by_type(instrument_type, pais=pais)


async def _request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
) -> httpx.Response:
    """Top-level shim for legacy tests that call ``aio._request(...)``."""
    return await _get_default()._request(method, path, params=params, json_body=json_body)


# ----------------------------------------------------------------------
# PEP 562 read-only shim (D-01 + D-02 aio addendum)
# ----------------------------------------------------------------------

_FORWARDED_TO_STATE: dict[str, str] = {
    "_token": "token",
    "_token_expires_at": "token_expires_at",
    # Pitfall #3 addendum for IOL: 13+ async test sites read aio._refresh_token.
    "_refresh_token": "refresh_token",
    # D-02 aio: _token_lock forwards to the per-instance asyncio.Lock.
    "_token_lock": "token_lock",
}

_FORWARDED_HTTP_CLIENT = "_client"

_DENIED_LEGACY: frozenset[str] = frozenset({"_user", "_password", "_base_url"})


def __getattr__(name: str) -> Any:
    """PEP 562 read-only shim (D-01)."""
    if name in _FORWARDED_TO_STATE:
        return getattr(_get_default()._state, _FORWARDED_TO_STATE[name])
    if name == _FORWARDED_HTTP_CLIENT:
        return _get_default()._state.http_client
    if name in _DENIED_LEGACY:
        raise AttributeError(
            f"module {__name__!r} has no attribute {name!r} "
            f"(legacy global removed in Phase 6; use iol_client.aio.configure() "
            f"or iol_client.aio._get_default()._state.{name.lstrip('_')} instead)"
        )
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
