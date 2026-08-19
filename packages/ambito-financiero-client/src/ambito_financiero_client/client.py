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

from ambito_financiero_client import _core, _decode, _transport
from ambito_financiero_client._state import _ClientState

load_dotenv()

_REQUEST_TIMEOUT = 30.0

# D-04 alias — preserves B8 identity (aio._raise_for_response is client._raise_for_response).
# Listed in `__all__` to satisfy mypy --strict's implicit_reexport=False.
_raise_for_response = _core.raise_for_response


# WR-06 Phase 8 review fix: validate max_retries kwarg early. Duplicated 4x
# across packages per the "no shared internals" project constraint.
def _validate_max_retries(value: int) -> None:
    """Validate the ``max_retries`` kwarg accepted by ``Client.__init__`` / ``configure()``.

    Phase 8 D-19: ``max_retries`` is a non-negative ``int`` (``0`` disables
    retries entirely). Negative values, floats, and non-int types are rejected
    early with a clean ``ValueError`` instead of being silently accepted and
    crashing later inside tenacity with a less actionable message.
    """
    # Reject bool explicitly: bool is a subclass of int in Python, so a bare
    # ``isinstance(value, int)`` would pass ``True``/``False`` silently. The
    # resulting transport would still work (True coerces to 1) but accepting it
    # masks a likely caller error (e.g. ``max_retries=True`` instead of ``=1``).
    if isinstance(value, bool):
        raise ValueError(
            f"max_retries must be a non-negative int, got {value!r} (bool not accepted)"
        )
    if not isinstance(value, int):
        raise ValueError(
            f"max_retries must be a non-negative int, got {value!r} (type={type(value).__name__})"
        )
    if value < 0:
        raise ValueError(f"max_retries must be a non-negative int, got {value!r}")


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

    __slots__ = ("_is_view", "_max_retries", "_state")

    def __init__(
        self,
        *,
        base_url: str | None = None,
        user_agent: str | None = None,
        max_retries: int = 2,
        http_client: httpx.Client | None = None,
        strict_decode: bool | None = None,
    ) -> None:
        # WR-06: validate max_retries early so the surfacing error is
        # a clean ValueError, not a confusing tenacity error later.
        _validate_max_retries(max_retries)
        self._state = _ClientState()
        if base_url is not None:
            self._state.base_url = base_url.rstrip("/")
        if user_agent is not None:
            self._state.user_agent = user_agent
        # Phase 29 D-03: ``None`` sentinel = "leave the state default"; the
        # flag lands on the SHARED ``_state``, never on ``__slots__``, so a
        # ``with_options`` view inherits it.
        if strict_decode is not None:
            self._state.strict_decode = strict_decode
        # Phase 8 D-15 / D-19: max_retries=N → max_attempts=N+1 (1 initial + N retries).
        # max_retries=0 means no retries (bypass retry loop entirely per D-19).
        self._max_retries = max_retries
        # Phase 13 D-V1: False for normally-constructed Clients; True for views
        # returned by with_options(). Views' close()/__exit__ are no-op so the
        # parent's shared http_client TCP pool is not accidentally torn down.
        self._is_view = False
        # Phase 8 D-16: caller-supplied http_client used AS-IS (no auto-wrap with RetryTransport).
        if http_client is not None:
            self._state.http_client = http_client

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def close(self) -> None:
        # Phase 13 D-V1: views don't own the http_client (shared _state with parent);
        # short-circuit so view.close()/__exit__ never tear down the parent's TCP pool
        # (anti-Pitfall 13). getattr defensive for pre-Phase-13 pickled or partially-
        # initialized instances.
        if getattr(self, "_is_view", False):
            return
        if self._state.http_client is not None:
            assert isinstance(self._state.http_client, httpx.Client)
            self._state.http_client.close()
            self._state.http_client = None

    def __repr__(self) -> str:
        # D-18: ambito has no credentials; repr exposes only non-secret state.
        # Phase 13: views surface a "view of " prefix for debug ergonomics
        # (Claude's Discretion per 13-CONTEXT.md <decisions>).
        prefix = "view of " if getattr(self, "_is_view", False) else ""
        return (
            f"{prefix}AmbitoFinancieroClient("
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

    def with_options(self, *, max_retries: int) -> Self:
        """Return a new Client view with overridden ``max_retries``.

        The view shares this Client's ``_state`` and underlying ``httpx.Client``
        (no re-auth, no connection pool fragmentation — Phase 13 D-V1, anti-
        Pitfall 13). Only the per-call ``max_retries`` differs; the parent's
        ``_max_retries`` stays at its constructor value (D-V2 chaining truth).

        Use for one-off requests that need different retry behavior::

            # Bump retries for a flaky symbol (idempotent GET):
            precio = client.with_options(max_retries=5).get_dollar_banco_nacion(date)

            # Disable retries entirely for debug iteration:
            precio = client.with_options(max_retries=0).get_dollar_banco_nacion(date)

        Per Phase 8 D-19 the mapping is ``max_retries=N → max_attempts=N+1``
        (1 initial + N retries). The view's ``_max_retries`` is threaded into
        the shell's ``_request()`` via ``request.extensions["max_attempts"]`` so
        the ``RetryTransport`` honors it per-call. The mutation gate (Phase 8
        D-01) remains the absolute authority — non-idempotent calls always
        pass through to a single outgoing request, even from a view with
        ``max_retries=10``.

        Lifecycle no-op: ``view.close()`` / ``view.__exit__`` / ``view.aclose()``
        / ``view.__aexit__`` do NOT touch the shared ``http_client``. The
        parent (or letting the parent fall out of scope) owns the pool.

        Chaining returns a fresh view each call; the inner call wins (D-V2)::

            client.with_options(5).with_options(10)._max_retries  # 10
            client._max_retries                                    # 2 (intact)

        D-V4 configure-invariance: ``configure()`` called AFTER ``with_options()``
        replaces the module ``_default_client`` with a NEW ``Client`` that has
        its own ``_state``. Existing views still point at the original
        ``_state`` instance — they are snapshots of the parent at view-
        construction time.

        Endpoint: N/A — this is a method on the ``Client`` instance, not an
        HTTP endpoint. The next endpoint call on the returned view executes
        the actual HTTP exchange with the per-call retry cap.
        """
        # WR-06 Phase 8 carry-forward: validate early so the surfacing error is
        # a clean ValueError before view construction (D-V3 parity with async).
        _validate_max_retries(max_retries)
        view = type(self).__new__(type(self))
        view._state = self._state  # SHARE — anti-Pitfall 13
        view._max_retries = max_retries  # OVERRIDE
        view._is_view = True  # FLAG for close()/__exit__ no-op (D-V1)
        return view

    def _request(self, spec: _core.RequestSpec) -> httpx.Response:
        """Transport shell — dispatch HTTP only (D-03). Status / body handled by ``_core``.

        Phase 8 D-30: generates a per-business-call ``request_id`` (UUID4) and
        propagates ``idempotent`` + ``endpoint_name`` via ``request.extensions``
        so the ``RetryTransport`` mutation gate (D-01) + structured logs (D-09)
        see them. ámbito has no auth → no 401 re-auth branch (D-02 N/A).

        Phase 29 D-03 + aggregation-contract lock 6: the first two statements
        bind the decode mode and a fresh decode scope for this response.
        """
        # Phase 29 D-03: bind the decode mode + a fresh decode scope. There is
        # deliberately NO reset and no try/finally — this method returns the
        # ``httpx.Response`` and the decode happens AFTERWARDS, in the parser,
        # which holds no reference to this Client. A reset in a ``finally``
        # would unbind the mode before the decoder ever reads it. The bind is
        # unconditional even though this paquete's parsers return a ``float``
        # today: the two statements are the copy's contract, not a shortcut.
        _decode.STRICT_DECODE.set(self._state.strict_decode)
        _decode.open_request_scope()

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
        # Phase 13 ERG-01: per-call override; parent or view's _max_retries
        # (Phase 8 D-19 N→N+1). Set uniformly — uniform path keeps the cross-
        # cutting test shape simple and eliminates shell branches.
        req.extensions["max_attempts"] = self._max_retries + 1
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
    strict_decode: bool | None = None,
) -> None:
    """Sobrescribe URL base / User-Agent runtime (carry-forward, D-14).

    Reemplaza ``_default_client``. Instancias ``Client()`` explícitas NO se afectan.

    Phase 8 D-15: ``max_retries`` (default 2; ``0`` disables retries entirely
    per D-19; subject to tuning in future minor versions per D-20) and
    ``http_client`` (used AS-IS without auto-wrapping with ``RetryTransport``
    per D-16) are carry-forward kwargs.

    Phase 29 D-03: ``strict_decode`` is a carry-forward kwarg too — the ``None``
    sentinel means "no cambiar", so a later ``configure(base_url=...)`` does NOT
    silently reset a previous strict opt-in. Because this ``configure`` builds a
    NEW ``Client`` rather than mutating the current one in place, the carry
    forward reads the prior client's state explicitly.
    """
    # WR-06: validate max_retries before any state mutation.
    _validate_max_retries(max_retries)
    global _default_client
    prior_base_url: str | None = None
    prior_user_agent: str | None = None
    prior_strict_decode: bool | None = None
    if _default_client is not None:
        prior_base_url = _default_client._state.base_url
        prior_user_agent = _default_client._state.user_agent
        prior_strict_decode = _default_client._state.strict_decode
    new_base_url = base_url if base_url is not None else prior_base_url
    new_user_agent = user_agent if user_agent is not None else prior_user_agent
    new_strict_decode = strict_decode if strict_decode is not None else prior_strict_decode
    _default_client = Client(
        base_url=new_base_url,
        user_agent=new_user_agent,
        max_retries=max_retries,
        http_client=http_client,
        strict_decode=new_strict_decode,
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
