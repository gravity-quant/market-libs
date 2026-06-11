"""Cliente HTTP asincrónico para Ámbito Financiero.

Phase 06 Plan 06-03 (REFAC-02, Task 2): introduce la `AsyncClient` class con
estado por-instancia (`_ClientState`) y un shim PEP 562 read-only que preserva
la API top-level legacy (``aio.get_dollar_banco_nacion(...)``,
``aio.configure(...)``, ``aio.aclose()``) sin breaking changes.

API a nivel módulo (compat 100% con v1.0)::

    from ambito_financiero_client import aio
    import datetime as dt

    precio = await aio.get_dollar_banco_nacion(dt.date(2026, 4, 7))
    await aio.aclose()

API a nivel instancia (nuevo en v1.1)::

    from ambito_financiero_client import AsyncClient

    async with AsyncClient() as c:
        precio = await c.get_dollar_banco_nacion(dt.date(2026, 4, 7))

**B7 divergence (vs iol/higyrus/matriz):** ambito has NO auth and NO token
refresh race. The asyncio.Lock pattern used by iol/higyrus/matriz to
serialize token refresh is unnecessary here; `AsyncClient.__slots__` is
`("_state",)` only (no `_client_lock`), and `_ensure_http_client` lazy-creates
the underlying `httpx.AsyncClient` without locking. In the (rare) case of two
concurrent first-calls, the worst case is a single leaked `httpx.AsyncClient`
per process — acceptable for ambito's low-frequency FX-rate polling workload
(T-06-13 in the plan's threat model).

**B8 shared helper policy:** `_raise_for_response` is imported from
``ambito_financiero_client.client`` — NOT redefined here. The helper is
stateless and follows the same import pattern that ARCHITECTURE.md confirms
for `aio.py` importing shared types (e.g. `iol_client.aio` imports
`InstrumentType` from `iol_client.client`). The B8 invariant is enforced by
`test_aio_imports_raise_for_response_from_client` in
`tests/test_client_class.py`.

PEP 562 shim (D-01, D-02): reads of the legacy module-level global `_client`
forward to ``_get_default()._state.http_client``. NO other forwarded names —
`_base_url`, `_user_agent` are removed from the module namespace.
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Self

import httpx

from ambito_financiero_client._parsing import parse_ar_decimal
from ambito_financiero_client._state import _ClientState

# B8: shared, not duplicated. The explicit re-export alias (`as _raise_for_response`)
# satisfies mypy --strict's `implicit_reexport=False` so callers can import the
# helper directly via `from ambito_financiero_client.aio import _raise_for_response`.
from ambito_financiero_client.client import (
    _raise_for_response as _raise_for_response,
)
from ambito_financiero_client.exceptions import AmbitoFinancieroNoDataError

_REQUEST_TIMEOUT = 30.0


# ---------------------------------------------------------------------------
# Async Client class
# ---------------------------------------------------------------------------


class AsyncClient:
    """Async client para la API pública de Ámbito Financiero.

    Cada instancia mantiene su propio `_ClientState` (base_url, user_agent,
    http_client). Las instancias explícitas creadas por el caller NO son
    afectadas por `aio.configure(...)` (Pitfall #2 / D-14).

    Lifecycle (D-15, D-16):
    - `httpx.AsyncClient` se crea perezosamente en el primer `_request(...)`.
    - `aclose()` es idempotente (calling twice no-op).
    - `__aenter__`/`__aexit__` delegan a `aclose()` en salida.

    **B7 divergence:** `__slots__ = ("_state",)` only. No `_client_lock`.
    Ambito has no auth and no token refresh race; the asyncio.Lock used by
    iol/higyrus/matriz is unnecessary. See module docstring.

    Pickle / deepcopy contract (D-23): NOT supported. The underlying
    `httpx.AsyncClient` owns a TCP connection pool and an SSL context that
    are not safe to serialize. Both `__reduce__` and `__deepcopy__` raise
    `TypeError` loud and early.
    """

    __slots__ = ("_state",)

    def __init__(
        self,
        *,
        base_url: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        self._state = _ClientState()
        if base_url is not None:
            self._state.base_url = base_url.rstrip("/")
        if user_agent is not None:
            self._state.user_agent = user_agent

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: object,
        exc: object,
        tb: object,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Cierra el `httpx.AsyncClient` subyacente; idempotente (T-06-04)."""
        if self._state.http_client is not None:
            assert isinstance(self._state.http_client, httpx.AsyncClient)
            await self._state.http_client.aclose()
            self._state.http_client = None

    def __repr__(self) -> str:
        # D-18 mirror: same redaction as sync Client; ambito has no token /
        # credentials so the repr exposes only base_url, user_agent, and the
        # `client_open` boolean.
        return (
            f"AmbitoFinancieroAsyncClient("
            f"base_url={self._state.base_url!r}, "
            f"user_agent={self._state.user_agent!r}, "
            f"client_open={self._state.http_client is not None})"
        )

    def __reduce__(self) -> Any:  # D-23
        raise TypeError(
            "AmbitoFinancieroAsyncClient is not picklable; use multiprocessing's "
            "fork start method or recreate via ambito_financiero_client.AsyncClient(...)"
        )

    def __deepcopy__(self, memo: Any) -> Any:  # D-23
        raise TypeError(
            "AmbitoFinancieroAsyncClient is not deepcopy-safe "
            "(httpx.AsyncClient owns TCP pool + SSL context)"
        )

    # -- private --------------------------------------------------------

    def _ensure_http_client(self) -> httpx.AsyncClient:
        """Lazy-create the underlying `httpx.AsyncClient` on first use.

        **B7 lock-less rationale:** ambito has no auth and no token refresh
        race. The asyncio.Lock pattern used by iol/higyrus/matriz
        AsyncClient._ensure_http_client (PATTERNS.md Section 7) is
        unnecessary here — concurrent first-call would at worst leak one
        httpx.AsyncClient per accidental race per process (T-06-13). This is
        acceptable for ambito's low-frequency FX-rate polling workload and
        bounded by process lifetime.
        """
        if self._state.http_client is None:
            self._state.http_client = httpx.AsyncClient(
                timeout=_REQUEST_TIMEOUT,
                headers={"User-Agent": self._state.user_agent},
            )
        assert isinstance(self._state.http_client, httpx.AsyncClient)
        return self._state.http_client

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        client = self._ensure_http_client()
        resp = await client.request(method, f"{self._state.base_url}{path}", **kwargs)
        _raise_for_response(resp)
        return resp

    # -- endpoints ------------------------------------------------------

    async def get_dollar_banco_nacion(self, date: dt.date) -> float:
        """Cotización vendedor del dólar Banco Nación para ``date`` (async)."""
        formatted = date.strftime("%Y-%m-%d")
        resp = await self._request(
            "GET",
            f"/dolarnacion/historico-general/{formatted}/{formatted}",
        )
        rows: list[list[str]] = resp.json()
        if len(rows) < 2:
            raise AmbitoFinancieroNoDataError(
                f"Sin cotización del dólar Banco Nación para {formatted}"
            )
        _, _, venta = rows[1]
        return parse_ar_decimal(venta)


# ---------------------------------------------------------------------------
# Default AsyncClient + top-level delegators (back-compat with v1.0 module API)
# ---------------------------------------------------------------------------


_default_async_client: AsyncClient | None = None


def _get_default() -> AsyncClient:
    """Return the lazy default `AsyncClient`; constructs it on first access (D-15)."""
    global _default_async_client
    if _default_async_client is None:
        _default_async_client = AsyncClient()
    return _default_async_client


def configure(*, base_url: str | None = None, user_agent: str | None = None) -> None:
    """Sobrescribe la URL base o el User-Agent en runtime (async surface).

    Per RESEARCH.md Open Q #5: carry-forward semantics — campos con valor
    `None` se preservan del `_default_async_client` previo (si existe); campos
    con valor explícito reemplazan. Esto matchea la semántica de
    `client.configure(...)` y preserva la separación de state sync ↔ async
    (ARCHITECTURE.md "Dual sync/async surfaces con state independiente").

    Per CONTEXT.md D-19: este `configure` NO llama `load_dotenv()`; la única
    invocación de dotenv vive en `client.py`.
    """
    global _default_async_client
    prior_base_url: str | None = None
    prior_user_agent: str | None = None
    if _default_async_client is not None:
        prior_base_url = _default_async_client._state.base_url
        prior_user_agent = _default_async_client._state.user_agent
    new_base_url = base_url if base_url is not None else prior_base_url
    new_user_agent = user_agent if user_agent is not None else prior_user_agent
    _default_async_client = AsyncClient(base_url=new_base_url, user_agent=new_user_agent)


async def _request(method: str, path: str, **kwargs: Any) -> httpx.Response:
    """Module-level async delegator preserved for back-compat with v1.0 callers.

    Existing tests and drivers (e.g. ``main_ambito_financiero.py``) call
    ``await aio._request(...)`` directly. Post-refactor this delegates to
    ``_get_default()._request(...)`` so the call site keeps working without
    monkeypatch gymnastics. `monkeypatch.setattr(aio, "_request", mock)` still
    functions because it replaces this module-level binding.
    """
    return await _get_default()._request(method, path, **kwargs)


async def aclose() -> None:
    """Cierra el `httpx.AsyncClient` del default lazy (idempotente).

    Post-refactor: delega a ``_get_default().aclose()``. Si el default
    todavía no se instanció (caso de teardown sin haber hecho ninguna
    request), construye uno y aclose()-eando trivialmente — mantiene el
    contrato de "aclose es siempre seguro" del autouse fixture en conftest.
    """
    await _get_default().aclose()


async def get_dollar_banco_nacion(date: dt.date) -> float:
    """Cotización vendedor del dólar Banco Nación (async, delegador top-level).

    Endpoint: ``GET /dolarnacion/historico-general/<YYYY-MM-DD>/<YYYY-MM-DD>``.

    Levanta :class:`AmbitoFinancieroNoDataError` si no hay cotización para la
    fecha (fin de semana, feriado o fecha futura).
    """
    return await _get_default().get_dollar_banco_nacion(date)


# ---------------------------------------------------------------------------
# PEP 562 read-only shim (D-01, D-02)
# ---------------------------------------------------------------------------

# Ambito row of D-02: only `_client` is forwarded. The other v1.0 module-level
# globals (`_base_url`, `_user_agent`) are deliberately removed; reads of them
# raise `AttributeError`. T-06-01 mitigation enforced by
# `test_async_pep_562_shim_raises_for_unknown` in `tests/test_client_class.py`.

_FORWARDED_HTTP_CLIENT = "_client"


def __getattr__(name: str) -> Any:
    """PEP 562 read-only shim — forwards `_client` only.

    Reads of `_client` resolve to `_get_default()._state.http_client` (which
    may be `None` if no request has been made yet). Any other name raises
    `AttributeError`. No `DeprecationWarning` per D-03.
    """
    if name == _FORWARDED_HTTP_CLIENT:
        return _get_default()._state.http_client
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
