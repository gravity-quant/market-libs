"""Cliente HTTP asincrónico para Ámbito Financiero — transport shell.

Phase 07 Plan 07-02 (REFAC-03, Task 2): mirror sync con ``await``. Consume
``_core``; endpoints colapsan a 3-liner; ``_request(spec)`` (D-03);
``_raise_for_response = _core.raise_for_response`` (D-04 mirror — identidad
``aio._raise_for_response is client._raise_for_response`` preservada). ``__all__``
lista el alias para satisfacer mypy strict ``implicit_reexport=False``::

    from ambito_financiero_client import aio
    precio = await aio.get_dollar_banco_nacion(date)
    await aio.aclose()

    from ambito_financiero_client import AsyncClient
    async with AsyncClient() as c:
        precio = await c.get_dollar_banco_nacion(date)

**B7 divergence:** ámbito sin auth → ``__slots__ = ("_state",)`` (sin
``_client_lock``). Concurrent first-call puede leakear UN ``httpx.AsyncClient``
por proceso (T-06-13), aceptable para FX-rate polling. PEP 562 shim
(D-01/D-02): sólo ``_client`` es forward.
"""

from __future__ import annotations

import datetime as dt
import uuid
import warnings
from typing import Any, Self

import httpx

from ambito_financiero_client import _atransport, _core
from ambito_financiero_client._state import _ClientState
from ambito_financiero_client.client import _validate_max_retries

# D-04 mirror alias — identidad B8 preservada vía shared _core source.
# Listado en __all__ para satisfacer mypy strict implicit_reexport=False.
_raise_for_response = _core.raise_for_response

__all__ = [
    "AsyncClient",
    "_raise_for_response",
    "_request",
    "aclose",
    "configure",
    "get_dollar_banco_nacion",
]

_REQUEST_TIMEOUT = 30.0


# --- Async Client class (Phase 6 skeleton preserved; endpoint bodies collapse) ---


class AsyncClient:
    """Async client para Ámbito Financiero (estado per-instancia ``_ClientState``).

    ``aclose()`` idempotente (T-06-04); pickle/deepcopy raise ``TypeError`` (D-23).
    Instancias explícitas NO afectadas por ``configure()`` (D-14). B7: ``__slots__
    = ("_state",)`` — sin ``_client_lock``.
    """

    __slots__ = ("_max_retries", "_state")

    def __init__(
        self,
        *,
        base_url: str | None = None,
        user_agent: str | None = None,
        max_retries: int = 2,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        # WR-06: validate max_retries early (mirror sync Client).
        _validate_max_retries(max_retries)
        self._state = _ClientState()
        if base_url is not None:
            self._state.base_url = base_url.rstrip("/")
        if user_agent is not None:
            self._state.user_agent = user_agent
        # Phase 8 D-15 / D-19: max_retries=N → max_attempts=N+1 (1 initial + N retries).
        self._max_retries = max_retries
        # Phase 8 D-16: caller-supplied http_client used AS-IS (no auto-wrap).
        if http_client is not None:
            self._state.http_client = http_client

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._state.http_client is not None:
            assert isinstance(self._state.http_client, httpx.AsyncClient)
            await self._state.http_client.aclose()
            self._state.http_client = None

    def __repr__(self) -> str:
        # D-18 mirror: ambito has no credentials; repr exposes only non-secret state.
        return (
            f"AmbitoFinancieroAsyncClient("
            f"base_url={self._state.base_url!r}, "
            f"user_agent={self._state.user_agent!r}, "
            f"client_open={self._state.http_client is not None})"
        )

    def __reduce__(self) -> Any:  # D-23 — httpx.AsyncClient owns TCP pool + SSL context
        raise TypeError(
            "AmbitoFinancieroAsyncClient is not picklable; recreate via AsyncClient(...)"
        )

    def __deepcopy__(self, memo: Any) -> Any:  # D-23
        raise TypeError(
            "AmbitoFinancieroAsyncClient is not deepcopy-safe (httpx.AsyncClient TCP pool)"
        )

    def _ensure_http_client(self) -> httpx.AsyncClient:
        if self._state.http_client is None:
            # Phase 8 D-15 / D-19: wrap with AsyncRetryTransport.
            self._state.http_client = httpx.AsyncClient(
                timeout=_REQUEST_TIMEOUT,
                headers={"User-Agent": self._state.user_agent},
                transport=_atransport.AsyncRetryTransport(max_attempts=self._max_retries + 1),
            )
        assert isinstance(self._state.http_client, httpx.AsyncClient)
        return self._state.http_client

    async def _request(self, spec: _core.RequestSpec) -> httpx.Response:
        """Transport shell async — dispatch HTTP only (D-03 mirror).

        Phase 8 D-30 mirror: per-business-call ``request_id`` + extensions.
        ámbito has no auth → no 401 re-auth branch.
        """
        http = self._ensure_http_client()
        request_id = uuid.uuid4().hex
        req = http.build_request(
            spec.method,
            f"{self._state.base_url}{spec.path}",
            params=spec.params,
            headers=spec.headers,
        )
        req.extensions["idempotent"] = spec.idempotent
        req.extensions["request_id"] = request_id
        req.extensions["endpoint_name"] = spec.endpoint_name
        return await http.send(req)

    async def get_dollar_banco_nacion(self, date: dt.date) -> float:
        """Cotización vendedor del dólar Banco Nación para ``date`` (async)."""
        spec = _core.build_get_dollar_banco_nacion_request(self._state, date)
        resp = await self._request(spec)
        return _core.parse_get_dollar_banco_nacion_response(resp)


# --- Default AsyncClient + module-level delegators (back-compat con v1.0) ---


_default_async_client: AsyncClient | None = None


def _get_default() -> AsyncClient:
    """Lazy default ``AsyncClient`` (D-15)."""
    global _default_async_client
    if _default_async_client is None:
        _default_async_client = AsyncClient()
    return _default_async_client


def configure(
    *,
    base_url: str | None = None,
    user_agent: str | None = None,
    max_retries: int = 2,
    http_client: httpx.AsyncClient | None = None,
) -> None:
    """Sobrescribe URL base / User-Agent runtime (carry-forward, D-14).

    Reemplaza ``_default_async_client``. Instancias explícitas NO se afectan.
    D-19: NO llama ``load_dotenv()``.

    Phase 8 D-15: ``max_retries`` / ``http_client`` mirror sync ``configure``.
    """
    # WR-06: validate max_retries before any state mutation.
    _validate_max_retries(max_retries)
    global _default_async_client
    prior_base_url: str | None = None
    prior_user_agent: str | None = None
    # WR-07: warn if we're about to drop a live httpx.AsyncClient without
    # awaiting aclose() (configure is sync, so we cannot await here). The
    # connection pool + SSL context of the prior client leak until garbage
    # collection; for long-running processes with rotating credentials this
    # accumulates unbounded. The recommended consumer pattern is
    # ``await aio.aclose()`` BEFORE calling aio.configure(...).
    if _default_async_client is not None:
        prior_base_url = _default_async_client._state.base_url
        prior_user_agent = _default_async_client._state.user_agent
        prior_http_client = _default_async_client._state.http_client
        if prior_http_client is not None:
            warnings.warn(
                "ambito_financiero_client.aio.configure(): replacing a live "
                "httpx.AsyncClient without awaiting aclose() leaks the connection "
                "pool. Call `await ambito_financiero_client.aio.aclose()` before "
                "configure(...) to avoid the leak.",
                ResourceWarning,
                stacklevel=2,
            )
    new_base_url = base_url if base_url is not None else prior_base_url
    new_user_agent = user_agent if user_agent is not None else prior_user_agent
    _default_async_client = AsyncClient(
        base_url=new_base_url,
        user_agent=new_user_agent,
        max_retries=max_retries,
        http_client=http_client,
    )


async def _request(method: str, path: str, **kwargs: Any) -> httpx.Response:
    """Module-level async delegator back-compat (mirror sync ``client._request``)."""
    spec = _core.RequestSpec(
        method=method,
        path=path,
        params=kwargs.get("params"),
        headers=kwargs.get("headers"),
    )
    resp = await _get_default()._request(spec)
    _raise_for_response(resp)
    return resp


async def aclose() -> None:
    """Cierra el ``httpx.AsyncClient`` del default lazy (idempotente)."""
    await _get_default().aclose()


async def get_dollar_banco_nacion(date: dt.date) -> float:
    """Cotización vendedor del dólar Banco Nación (async delegador top-level)."""
    return await _get_default().get_dollar_banco_nacion(date)


# --- PEP 562 read-only shim (D-01, D-02 — only `_client` forwarded) ---

_FORWARDED_HTTP_CLIENT = "_client"


def __getattr__(name: str) -> Any:
    """PEP 562 shim — forwards ``_client``; otherwise ``AttributeError``."""
    if name == _FORWARDED_HTTP_CLIENT:
        return _get_default()._state.http_client
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
