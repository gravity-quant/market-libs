"""Cliente HTTP sincrónico para Ámbito Financiero.

Phase 06 Plan 06-03 (REFAC-02): introduce la `Client` class con estado
por-instancia (`_ClientState`) y un shim PEP 562 read-only que preserva la
API top-level legacy (`ambito_financiero_client.get_dollar_banco_nacion(...)`,
`ambito_financiero_client.configure(...)`) sin breaking changes.

API a nivel módulo (compat 100% con v1.0)::

    import ambito_financiero_client as ambito
    import datetime as dt

    precio = ambito.get_dollar_banco_nacion(dt.date(2026, 4, 7))

API a nivel instancia (nuevo en v1.1)::

    from ambito_financiero_client import Client

    with Client(base_url="https://mercados.ambito.com") as c:
        precio = c.get_dollar_banco_nacion(dt.date(2026, 4, 7))

La API pública (``mercados.ambito.com``) no requiere autenticación. Sólo se
expone una variable de entorno opcional para sobreescribir el host:

- ``AMBITO_BASE_URL`` (default ``https://mercados.ambito.com``).

`load_dotenv()` corre solo en este módulo (D-19); `aio.py` y `_state.py` NO
re-importan dotenv.

PEP 562 shim (D-01, D-02): reads of the legacy module-level global `_client`
forward to `_get_default()._state.http_client` so existing tests / drivers
that read it (e.g. `main_higyrus.py` mutates `_client.event_hooks`) keep
working. NO other forwarded names — `_base_url`, `_user_agent` are removed
from the module namespace.
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Self

import httpx
from dotenv import load_dotenv

from ambito_financiero_client._parsing import parse_ar_decimal
from ambito_financiero_client._state import _ClientState
from ambito_financiero_client.exceptions import (
    AmbitoFinancieroAPIError,
    AmbitoFinancieroAuthError,
    AmbitoFinancieroNoDataError,
    AmbitoFinancieroRateLimitError,
)

load_dotenv()

_REQUEST_TIMEOUT = 30.0


# ---------------------------------------------------------------------------
# Stateless helpers (also imported by ambito_financiero_client.aio per B8)
# ---------------------------------------------------------------------------


def _raise_for_response(resp: httpx.Response) -> None:
    if resp.status_code in (401, 403):
        raise AmbitoFinancieroAuthError(resp.status_code, resp.text)
    if resp.status_code == 429:
        raise AmbitoFinancieroRateLimitError(resp.status_code, resp.text)
    if resp.is_error:
        raise AmbitoFinancieroAPIError(resp.status_code, resp.text)


# ---------------------------------------------------------------------------
# Sync Client class
# ---------------------------------------------------------------------------


class Client:
    """Sync client para la API pública de Ámbito Financiero.

    Cada instancia mantiene su propio `_ClientState` (base_url, user_agent,
    http_client). Las instancias explícitas creadas por el caller NO son
    afectadas por `ambito_financiero_client.configure(...)` (Pitfall #2 /
    D-14).

    Lifecycle (D-15, D-16):
    - `httpx.Client` se crea perezosamente en el primer `_request(...)`.
    - `close()` es idempotente (calling twice no-op).
    - `__enter__`/`__exit__` delegan a `close()` en salida.

    Pickle / deepcopy contract (D-23): NOT supported. The underlying
    `httpx.Client` owns a TCP connection pool and an SSL context that are
    not safe to serialize; pickling a `Client` would silently fail in
    `multiprocessing.spawn` workers. Both `__reduce__` and `__deepcopy__`
    raise `TypeError` loud and early.
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

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: object,
        exc: object,
        tb: object,
    ) -> None:
        self.close()

    def close(self) -> None:
        """Cierra el `httpx.Client` subyacente; idempotente (T-06-04)."""
        if self._state.http_client is not None:
            assert isinstance(self._state.http_client, httpx.Client)
            self._state.http_client.close()
            self._state.http_client = None

    def __repr__(self) -> str:
        # D-18: ambito has no token / credentials; the repr only exposes
        # the base_url (non-secret), the user_agent (non-secret), and the
        # `client_open` boolean flag.
        return (
            f"AmbitoFinancieroClient("
            f"base_url={self._state.base_url!r}, "
            f"user_agent={self._state.user_agent!r}, "
            f"client_open={self._state.http_client is not None})"
        )

    def __reduce__(self) -> Any:  # D-23
        raise TypeError(
            "AmbitoFinancieroClient is not picklable; use multiprocessing's "
            "fork start method or recreate via ambito_financiero_client.Client(...)"
        )

    def __deepcopy__(self, memo: Any) -> Any:  # D-23
        raise TypeError(
            "AmbitoFinancieroClient is not deepcopy-safe (httpx.Client owns TCP pool + SSL context)"
        )

    # -- private --------------------------------------------------------

    def _ensure_http_client(self) -> httpx.Client:
        """Lazy-create the underlying `httpx.Client` on first use."""
        if self._state.http_client is None:
            self._state.http_client = httpx.Client(
                timeout=_REQUEST_TIMEOUT,
                headers={"User-Agent": self._state.user_agent},
            )
        assert isinstance(self._state.http_client, httpx.Client)
        return self._state.http_client

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        client = self._ensure_http_client()
        resp = client.request(method, f"{self._state.base_url}{path}", **kwargs)
        _raise_for_response(resp)
        return resp

    # -- endpoints ------------------------------------------------------

    def get_dollar_banco_nacion(self, date: dt.date) -> float:
        """Cotización vendedor del dólar Banco Nación para ``date``.

        Endpoint: ``/dolarnacion/historico-general/<YYYY-MM-DD>/<YYYY-MM-DD>``.
        """
        formatted = date.strftime("%Y-%m-%d")
        resp = self._request("GET", f"/dolarnacion/historico-general/{formatted}/{formatted}")
        rows: list[list[str]] = resp.json()
        if len(rows) < 2:
            raise AmbitoFinancieroNoDataError(
                f"Sin cotización del dólar Banco Nación para {formatted}"
            )
        _, _, venta = rows[1]
        return parse_ar_decimal(venta)


# ---------------------------------------------------------------------------
# Default Client + top-level delegators (back-compat with v1.0 module API)
# ---------------------------------------------------------------------------


_default_client: Client | None = None


def _get_default() -> Client:
    """Return the lazy default `Client`; constructs it on first access (D-15)."""
    global _default_client
    if _default_client is None:
        _default_client = Client()
    return _default_client


def configure(*, base_url: str | None = None, user_agent: str | None = None) -> None:
    """Sobrescribe la URL base o el User-Agent en runtime.

    Per RESEARCH.md Open Q #5: campos con valor `None` se carry-forward del
    `_default_client` previo (si existe); campos con valor explícito reemplazan.
    Esto preserva la semántica v1.0 donde `configure(base_url="X")` sin
    `user_agent=` no clobbeaba el user_agent previamente seteado.

    Per CONTEXT.md D-14: reemplaza el `_default_client` con una nueva instancia.
    Instancias `Client()` explícitas creadas por el caller NO se ven afectadas.
    """
    global _default_client
    prior_base_url: str | None = None
    prior_user_agent: str | None = None
    if _default_client is not None:
        prior_base_url = _default_client._state.base_url
        prior_user_agent = _default_client._state.user_agent
    new_base_url = base_url if base_url is not None else prior_base_url
    new_user_agent = user_agent if user_agent is not None else prior_user_agent
    _default_client = Client(base_url=new_base_url, user_agent=new_user_agent)


def _request(method: str, path: str, **kwargs: Any) -> httpx.Response:
    """Module-level delegator preserved for back-compat with v1.0 callers.

    Existing tests and drivers (e.g. ``main_ambito_financiero.py``) call
    ``ambito.client._request(...)`` directly. Post-refactor this delegates to
    ``_get_default()._request(...)`` so the call site keeps working without
    monkeypatching gymnastics. `monkeypatch.setattr(ambito.client, "_request",
    mock)` still functions because it replaces this module-level binding.
    """
    return _get_default()._request(method, path, **kwargs)


def get_dollar_banco_nacion(date: dt.date) -> float:
    """Cotización vendedor del dólar Banco Nación (delegador top-level).

    Endpoint: ``GET /dolarnacion/historico-general/<YYYY-MM-DD>/<YYYY-MM-DD>``.

    Levanta :class:`AmbitoFinancieroNoDataError` si no hay cotización para la
    fecha (fin de semana, feriado o fecha futura).
    """
    return _get_default().get_dollar_banco_nacion(date)


# ---------------------------------------------------------------------------
# PEP 562 read-only shim (D-01, D-02)
# ---------------------------------------------------------------------------

# Ambito row of D-02: only `_client` is forwarded. The other v1.0 module-level
# globals (`_base_url`, `_user_agent`) are deliberately removed; reads of them
# raise `AttributeError`. T-06-01 mitigation enforced by
# `test_pep_562_shim_raises_for_unknown` in `tests/test_client_class.py`.

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
