"""Cliente HTTP sincrónico para Ámbito Financiero — transport shell.

Phase 07 Plan 07-02 (REFAC-03): consume ``_core`` (puros). Skeleton Phase 6
preservado; sólo cambian endpoints (3-liner), ``_request(spec)`` (D-03) y
``_raise_for_response = _core.raise_for_response`` (D-04 alias, B8 identity)::

    import ambito_financiero_client as ambito
    precio = ambito.get_dollar_banco_nacion(date)

    from ambito_financiero_client import Client
    with Client() as c:
        precio = c.get_dollar_banco_nacion(date)

Env: ``AMBITO_BASE_URL`` (default ``https://mercados.ambito.com``). ``load_dotenv()``
sólo aquí (D-19). PEP 562 shim (D-01/D-02): sólo ``_client`` forward (T-06-01).
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Any, Self

import httpx
from dotenv import load_dotenv

from ambito_financiero_client import _core, _transport
from ambito_financiero_client._state import _ClientState

load_dotenv()

_REQUEST_TIMEOUT = 30.0

# D-04 alias — preserves B8 identity (aio._raise_for_response is client._raise_for_response).
# Listed in `__all__` to satisfy mypy --strict's implicit_reexport=False.
_raise_for_response = _core.raise_for_response

__all__ = [
    "Client",
    "_raise_for_response",
    "_request",
    "configure",
    "get_dollar_banco_nacion",
]


# --- Sync Client class (Phase 6 skeleton preserved; endpoint bodies collapse) ---


class Client:
    """Sync client para Ámbito Financiero (estado per-instancia ``_ClientState``).

    ``close()`` idempotente (T-06-04); pickle/deepcopy raise ``TypeError``
    (D-23). Instancias explícitas NO afectadas por ``configure()`` (D-14).
    """

    __slots__ = ("_max_retries", "_state")

    def __init__(
        self,
        *,
        base_url: str | None = None,
        user_agent: str | None = None,
        max_retries: int = 2,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._state = _ClientState()
        if base_url is not None:
            self._state.base_url = base_url.rstrip("/")
        if user_agent is not None:
            self._state.user_agent = user_agent
        # Phase 8 D-15 / D-19: max_retries=N → max_attempts=N+1 (1 initial + N retries).
        # max_retries=0 means no retries (bypass retry loop entirely per D-19).
        self._max_retries = max_retries
        # Phase 8 D-16: caller-supplied http_client used AS-IS (no auto-wrap with RetryTransport).
        if http_client is not None:
            self._state.http_client = http_client

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def close(self) -> None:
        if self._state.http_client is not None:
            assert isinstance(self._state.http_client, httpx.Client)
            self._state.http_client.close()
            self._state.http_client = None

    def __repr__(self) -> str:
        # D-18: ambito has no credentials; repr exposes only non-secret state.
        return (
            f"AmbitoFinancieroClient("
            f"base_url={self._state.base_url!r}, "
            f"user_agent={self._state.user_agent!r}, "
            f"client_open={self._state.http_client is not None})"
        )

    def __reduce__(self) -> Any:  # D-23 — httpx.Client owns TCP pool + SSL context
        raise TypeError("AmbitoFinancieroClient is not picklable; recreate via Client(...)")

    def __deepcopy__(self, memo: Any) -> Any:  # D-23
        raise TypeError("AmbitoFinancieroClient is not deepcopy-safe (httpx.Client TCP pool)")

    def _ensure_http_client(self) -> httpx.Client:
        if self._state.http_client is None:
            # Phase 8 D-15 / D-19: wrap with RetryTransport.
            # max_retries=N → max_attempts=N+1 (1 initial + N retries).
            self._state.http_client = httpx.Client(
                timeout=_REQUEST_TIMEOUT,
                headers={"User-Agent": self._state.user_agent},
                transport=_transport.RetryTransport(max_attempts=self._max_retries + 1),
            )
        assert isinstance(self._state.http_client, httpx.Client)
        return self._state.http_client

    def _request(self, spec: _core.RequestSpec) -> httpx.Response:
        """Transport shell — dispatch HTTP only (D-03). Status / body handled by ``_core``.

        Phase 8 D-30: generates a per-business-call ``request_id`` (UUID4) and
        propagates ``idempotent`` + ``endpoint_name`` via ``request.extensions``
        so the ``RetryTransport`` mutation gate (D-01) + structured logs (D-09)
        see them. ámbito has no auth → no 401 re-auth branch (D-02 N/A).
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
        return http.send(req)

    def get_dollar_banco_nacion(self, date: dt.date) -> float:
        """Cotización vendedor del dólar Banco Nación para ``date``.

        Endpoint: ``/dolarnacion/historico-general/<YYYY-MM-DD>/<YYYY-MM-DD>``.
        """
        spec = _core.build_get_dollar_banco_nacion_request(self._state, date)
        resp = self._request(spec)
        return _core.parse_get_dollar_banco_nacion_response(resp)


# --- Default Client + module-level delegators (back-compat con v1.0) ---


_default_client: Client | None = None


def _get_default() -> Client:
    """Lazy default ``Client`` (D-15)."""
    global _default_client
    if _default_client is None:
        _default_client = Client()
    return _default_client


def configure(
    *,
    base_url: str | None = None,
    user_agent: str | None = None,
    max_retries: int = 2,
    http_client: httpx.Client | None = None,
) -> None:
    """Sobrescribe URL base / User-Agent runtime (carry-forward, D-14).

    Reemplaza ``_default_client``. Instancias ``Client()`` explícitas NO se afectan.

    Phase 8 D-15: ``max_retries`` (default 2; ``0`` disables retries entirely
    per D-19; subject to tuning in future minor versions per D-20) and
    ``http_client`` (used AS-IS without auto-wrapping with ``RetryTransport``
    per D-16) are carry-forward kwargs.
    """
    global _default_client
    prior_base_url: str | None = None
    prior_user_agent: str | None = None
    if _default_client is not None:
        prior_base_url = _default_client._state.base_url
        prior_user_agent = _default_client._state.user_agent
    new_base_url = base_url if base_url is not None else prior_base_url
    new_user_agent = user_agent if user_agent is not None else prior_user_agent
    _default_client = Client(
        base_url=new_base_url,
        user_agent=new_user_agent,
        max_retries=max_retries,
        http_client=http_client,
    )


def _request(method: str, path: str, **kwargs: Any) -> httpx.Response:
    """Module-level delegator back-compat: retorna ``httpx.Response`` con
    ``_raise_for_response`` ya aplicado. NO consume body (mocks del driver
    hacen ``resp.json()`` directo)."""
    spec = _core.RequestSpec(
        method=method,
        path=path,
        params=kwargs.get("params"),
        headers=kwargs.get("headers"),
    )
    resp = _get_default()._request(spec)
    _raise_for_response(resp)
    return resp


def get_dollar_banco_nacion(date: dt.date) -> float:
    """Cotización vendedor del dólar Banco Nación (delegador top-level).

    Endpoint: ``GET /dolarnacion/historico-general/<YYYY-MM-DD>/<YYYY-MM-DD>``.
    Levanta :class:`AmbitoFinancieroNoDataError` si no hay cotización.
    """
    return _get_default().get_dollar_banco_nacion(date)


# --- PEP 562 read-only shim (D-01, D-02 — only `_client` forwarded) ---

_FORWARDED_HTTP_CLIENT = "_client"


def __getattr__(name: str) -> Any:
    """PEP 562 shim — forwards ``_client``; otherwise ``AttributeError`` (T-06-01)."""
    if name == _FORWARDED_HTTP_CLIENT:
        return _get_default()._state.http_client
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
