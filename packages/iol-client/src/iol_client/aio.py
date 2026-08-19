"""Cliente HTTP asincrónico para Invertir Online (IOL).

API a nivel módulo (back-compat 100% con v1.0)::

    from iol_client import aio

    await aio.login()
    quote = await aio.get_quote("GGAL")
    await aio.aclose()

API basada en clase (Phase 6+)::

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
import de ``InstrumentType``.

B8 lock-in (D-04): ``_raise_for_response`` se importa desde
``iol_client._core`` — NO se duplica. Mismo objeto que en ``client.py``,
así el invariante ``aio._raise_for_response is client._raise_for_response``
se preserva (ambos aliases apuntan a ``_core.raise_for_response``).

CR-01: la política conditional refresh-token rotation (Phase 6 D-05) se
preserva en este transport shell: ``_login_unlocked()`` y
``_refresh_unlocked()`` actualizan ``self._state.refresh_token`` SOLO si
el parser retorna un valor non-None — el server puede omitir el nuevo
refresh_token en algunas respuestas y se preserva el cacheado.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import os
import time
import uuid
import warnings
from pathlib import Path
from typing import Any, Literal, Self

import httpx

from iol_client import _atransport, _core, _decode, _token_cache
from iol_client._core import RequestSpec

# B8 (D-04): import the shared, stateless helper from _core (NOT from
# client.py). Same import pattern as the InstrumentType alias which still
# lives in client.py. Explicit ``as _raise_for_response`` satisfies mypy
# strict ``implicit_reexport=False``.
from iol_client._core import raise_for_response as _raise_for_response
from iol_client._state import _REQUEST_TIMEOUT, _ClientState
from iol_client.client import InstrumentType, _validate_max_retries
from iol_client.exceptions import IOLAuthError

# Suppress ruff F401 for the deliberate re-export alias (consumed by tests
# via ``from iol_client.aio import _raise_for_response``).
_ = _raise_for_response


class AsyncClient:
    """Async client for the IOL REST API.

    Per-instance state lives in ``self._state`` (same :class:`_ClientState`
    dataclass shape as the sync ``Client``, but a different INSTANCE — NO
    shared mutable state between sync and async surfaces by construction).

    Locks (Pitfall #6): ``self._state.token_lock`` and
    ``self._state.client_lock`` are lazily created on first async use so
    they bind to whatever event loop is running. Creating an
    ``asyncio.Lock()`` inside ``__init__`` would bind it to the loop alive
    at construction time, which is fragile under ``asyncio.run`` patterns.

    Phase 13 WR-01 fix: ``client_lock`` lives on ``_state`` (mirror of
    ``token_lock``) so ``with_options`` views inherit the SAME lock instance
    as the parent — no second lock per view, no race on first
    ``_ensure_http_client`` materialization.

    Pickle / deepcopy contract (D-23): NOT supported (httpx.AsyncClient
    owns a TCP pool + SSL context tied to a specific event loop).

    Cleanup contract (D-16): caller-responsible. Use ``async with`` or
    ``await client.aclose()``.
    """

    __slots__ = ("_is_view", "_max_retries", "_state")

    def __init__(
        self,
        *,
        base_url: str | None = None,
        username: str | None = None,
        password: str | None = None,
        token: str | None = None,
        token_expires_at: float | None = None,
        refresh_token: str | None = None,
        token_cache_path: Path | None = None,
        max_retries: int = 2,
        http_client: httpx.AsyncClient | None = None,
        strict_decode: bool | None = None,
    ) -> None:
        # WR-06: validate max_retries early.
        _validate_max_retries(max_retries)
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
        # Phase 29 D-03 (sync mirror): ``None`` sentinel = "leave the state
        # default"; the flag lands on the SHARED ``_state``, never on
        # ``__slots__``, so a ``with_options`` view inherits it.
        if strict_decode is not None:
            self._state.strict_decode = strict_decode
        # Phase 14 BUG-03 (D-V3 sync mirror): seed in-memory refresh_token so a
        # cold instance can take the refresh path before any disk read (test
        # parity with the configure(refresh_token=...) surface).
        if refresh_token is not None:
            self._state.refresh_token = refresh_token
        # Phase 14 SEC-01 (D-T4 / D-V3 sync mirror): resolve token_cache_path
        # precedence — explicit kwarg > env-var override > platformdirs default
        # (None on CI=true per anti-Pitfall 10). Result may be None (disk
        # persistence disabled). Pure compute — NO async I/O in __init__.
        _env_cache_path = os.environ.get("IOL_TOKEN_CACHE_PATH")
        if token_cache_path is not None:
            self._state.token_cache_path = token_cache_path
        elif _env_cache_path:
            self._state.token_cache_path = Path(_env_cache_path)
        else:
            self._state.token_cache_path = _token_cache._resolve_default_path()
        # Phase 8 D-15 / D-19: max_retries=N → max_attempts=N+1.
        self._max_retries = max_retries
        # Phase 13 D-V1: normally-constructed AsyncClients are NOT views; with_options
        # sets this to True on the returned shallow clone.
        self._is_view = False
        # Phase 8 D-16: caller-supplied http_client used AS-IS.
        if http_client is not None:
            self._state.http_client = http_client
        # Phase 13 WR-01 fix: ``client_lock`` lives on ``self._state`` (lazy,
        # bound to the current event loop on first use). Hoisted off the
        # instance __slots__ so ``with_options`` views share the SAME lock
        # instance as the parent (mirror of ``token_lock``).

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
        """Release the underlying ``httpx.AsyncClient`` (idempotent).

        Phase 13 D-V1: views (constructed via ``with_options``) short-circuit
        here so ``view.aclose()`` / ``view.__aexit__`` never tear down the
        parent's shared TCP pool nor invalidate the parent's cached OAuth
        token (anti-Pitfall 13). ``getattr`` defensive for pre-Phase-13
        pickled or partially-initialized instances.
        """
        if getattr(self, "_is_view", False):
            return
        http_client = self._state.http_client
        if http_client is not None:
            assert isinstance(http_client, httpx.AsyncClient)
            await http_client.aclose()
            self._state.http_client = None

    def __repr__(self) -> str:
        # Phase 13: views surface a "view of " prefix for debug ergonomics
        # (Claude's Discretion per 13-CONTEXT.md <decisions>). The token/
        # password/refresh_token redaction stays intact.
        prefix = "view of " if getattr(self, "_is_view", False) else ""
        password_repr = "'***'" if self._state.password else "''"
        token_repr = "'***'" if self._state.token else "None"
        refresh_repr = "'***'" if self._state.refresh_token else "None"
        return (
            f"{prefix}IOLAsyncClient(base_url={self._state.base_url!r}, "
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
        """Lazily create the per-instance ``httpx.AsyncClient`` with AsyncRetryTransport.

        Phase 8 D-15 / D-19 / D-32: wraps ``AsyncRetryTransport`` so async
        requests benefit from bounded retries + native ``asyncio.sleep``
        backoff (CancelledError-aware). Preserves the Phase 6 double-checked
        locking pattern (``self._state.client_lock`` — Phase 13 WR-01 fix
        hoists from per-instance __slots__ onto shared _state so views and
        parent acquire the SAME lock) — instantiation runs INSIDE the
        lock-protected block so concurrent first-callers race a single
        ``AsyncClient`` allocation.
        """
        http_client = self._state.http_client
        if http_client is not None:
            assert isinstance(http_client, httpx.AsyncClient)
            return http_client
        client_lock = self._ensure_client_lock()
        async with client_lock:
            http_client = self._state.http_client
            if http_client is not None:
                assert isinstance(http_client, httpx.AsyncClient)
                return http_client
            new_client = httpx.AsyncClient(
                timeout=_REQUEST_TIMEOUT,
                transport=_atransport.AsyncRetryTransport(max_attempts=self._max_retries + 1),
            )
            self._state.http_client = new_client
            return new_client

    def _ensure_client_lock(self) -> asyncio.Lock:
        """Crea el lock de http-client lazy (bind to current loop).

        Phase 13 WR-01 fix: backed by ``self._state.client_lock`` (shared
        across parent and ``with_options`` views) instead of a per-instance
        ``__slots__`` attribute. Mirrors the existing ``token_lock`` pattern.
        """
        if self._state.client_lock is None:
            self._state.client_lock = asyncio.Lock()
        return self._state.client_lock

    def _ensure_token_lock(self) -> asyncio.Lock:
        if self._state.token_lock is None:
            self._state.token_lock = asyncio.Lock()
        return self._state.token_lock

    def with_options(self, *, max_retries: int) -> Self:
        """Return a new AsyncClient view with overridden ``max_retries``.

        Async mirror of :meth:`iol_client.Client.with_options`. The view shares
        this AsyncClient's ``_state`` (incl. cached ``token``, ``refresh_token``,
        ``token_expires_at``, ``token_lock``, and the underlying
        ``httpx.AsyncClient``). No re-auth, no second TCP connection pool —
        anti-Pitfall 13 (Phase 13 D-V1). Only the per-call ``max_retries``
        differs; the parent's ``_max_retries`` stays at its constructor value
        (D-V2 chaining truth).

        Use for one-off requests that need different retry behavior::

            # Bump retries for a flaky symbol (idempotent GET):
            quote = await client.with_options(max_retries=5).get_quote("RARE")

        Per Phase 8 D-19 the mapping is ``max_retries=N → max_attempts=N+1``.
        The view's ``_max_retries`` is threaded into the async ``_request``
        and ``_send_auth_request`` shells via ``request.extensions["max_attempts"]``
        so the ``AsyncRetryTransport`` honors it per-call. Auth-flow requests
        (login + refresh) carry ``idempotent=True`` (Phase 8 D-03) so the
        view's cap is honored for those calls too (per CONTEXT.md D-T6).

        IOL-specific 401 re-auth path: on a 401 response, the view's async
        ``_request`` shell re-authenticates through the SHARED
        ``state.token_lock`` (per-loop ``asyncio.Lock``) using the parent's
        shared ``_state.refresh_token``. The new token is written back to
        the shared ``_state.token`` — visible to the parent and any sibling
        views (INTENDED, shared ``_state`` semantics). There is NO per-view
        refresh-token tracking; the view's behavior under OAuth refresh is
        identical to the parent's.

        Phase 14 SEC-01 forward reference: when the IOL refresh-token disk
        persistence lands, the view will continue sharing ``_state`` (and
        therefore the disk-cached refresh_token) without modification.

        Lifecycle no-op: ``view.aclose()`` / ``view.__aexit__`` do NOT touch
        the shared ``http_client``. The parent (or letting the parent fall
        out of scope) owns the pool.

        Endpoint: N/A — this is a method on the ``AsyncClient`` instance,
        not an HTTP endpoint. The next endpoint call on the returned view
        executes the actual HTTP exchange with the per-call retry cap.
        """
        _validate_max_retries(max_retries)
        view = type(self).__new__(type(self))
        # SHARE — anti-Pitfall 13 (incl. ``client_lock``; Phase 13 WR-01 fix
        # moved the lock onto ``_state`` so view and parent acquire the SAME
        # ``asyncio.Lock`` on first ``_ensure_http_client``).
        view._state = self._state
        view._max_retries = max_retries  # OVERRIDE
        view._is_view = True  # FLAG for aclose()/__aexit__ no-op (D-V1)
        return view

    async def _send_auth_request(self, spec: RequestSpec) -> httpx.Response:
        """Send an auth-flow request through the AsyncRetryTransport with extensions.

        Phase 8 D-29 mirror: login + refresh go through the SAME
        AsyncRetryTransport as endpoint requests; ``request.extensions`` carries
        ``idempotent`` (True per D-03 for both) + ``request_id`` +
        ``endpoint_name`` so the transport's structured WARNING/ERROR records
        carry the canonical D-09 fields. NO ``Authorization`` header — auth-flow
        itself establishes the token.
        """
        http = await self._ensure_http_client()
        request_id = uuid.uuid4().hex
        req = http.build_request(
            spec.method,
            f"{self._state.base_url}{spec.path}",
            data=spec.data,
            headers=spec.headers,
        )
        req.extensions["idempotent"] = spec.idempotent
        req.extensions["request_id"] = request_id
        req.extensions["endpoint_name"] = spec.endpoint_name
        # Phase 13 ERG-01 (D-T6): auth-flow requests are ``idempotent=True``
        # (Phase 8 D-03), so the view's per-call cap MUST also apply to
        # login/refresh. Uniform path — parent or view both set this.
        req.extensions["max_attempts"] = self._max_retries + 1
        return await http.send(req)

    async def _login_unlocked(self) -> str:
        """Caller MUST hold ``self._state.token_lock``."""
        spec = _core.build_login_request(self._state)
        resp = await self._send_auth_request(spec)
        token, expires_at, refresh = _core.parse_login_response(resp)
        self._state.token = token
        self._state.token_expires_at = expires_at
        # CR-01 mirror: condicional, preserva refresh cacheado si server omite.
        if refresh is not None:
            self._state.refresh_token = refresh
        # Phase 14 SEC-01 (D-V3 sync mirror of Client.login): persist the fresh
        # refresh_token after a password grant (anti-Pitfall 8 — the post-401
        # fallback writes the FRESH token to disk in the same _aensure_token()
        # call). D-A1: the blocking fcntl + JSON write runs in an executor thread
        # via asyncio.to_thread; this call holds the token_lock (the caller's
        # critical section) but does NOT deadlock — the executor thread is
        # separate from the event loop and the awaiting coroutine is suspended.
        if self._state.token_cache_path is not None and self._state.refresh_token is not None:
            await asyncio.to_thread(
                _token_cache.save,
                self._state.token_cache_path,
                self._state.refresh_token,
                acquired_at=time.time(),
            )
        return token

    async def _refresh_unlocked(self) -> str:
        """Caller MUST hold ``self._state.token_lock``.

        Pitfall 6: NO llamar ``self._aensure_token()`` / ``self._login_unlocked()``
        / ``self._request(...)`` adentro — re-adquirirían el lock y causarían
        deadlock. Solo httpx send directo. ``_ensure_http_client`` usa un
        lock separado (``self._state.client_lock`` — Phase 13 WR-01 fix
        hoisted onto _state), sin conflicto.
        """
        spec = _core.build_refresh_request(self._state)
        resp = await self._send_auth_request(spec)
        token, expires_at, refresh = _core.parse_refresh_response(resp)
        self._state.token = token
        self._state.token_expires_at = expires_at
        if refresh is not None:
            self._state.refresh_token = refresh
        # Phase 14 SEC-01 (D-V3 sync mirror of Client._refresh): persist the
        # refresh_token after a successful refresh (rotated value or the
        # preserved cached one — both written so disk stays in sync with memory).
        # D-A1: blocking write dispatched via asyncio.to_thread; runs INSIDE the
        # token_lock critical section without deadlock (executor thread is
        # distinct from the event loop; the lock-holding coroutine suspends).
        if self._state.token_cache_path is not None and self._state.refresh_token is not None:
            await asyncio.to_thread(
                _token_cache.save,
                self._state.token_cache_path,
                self._state.refresh_token,
                acquired_at=time.time(),
            )
        return token

    async def login(self) -> str:
        lock = self._ensure_token_lock()
        async with lock:
            return await self._login_unlocked()

    async def _aensure_token(self) -> None:
        # Phase 14 SEC-01 (D-V3 sync mirror of Client._ensure_token): cold-start
        # disk load. Runs once per cold instance — subsequent calls see
        # state.refresh_token non-None and skip the read. Placed OUTSIDE the
        # token_lock: the disk read is per-cold-instance one-time work that does
        # not need the lock. D-A1: blocking fcntl + JSON read dispatched via
        # asyncio.to_thread.
        if self._state.refresh_token is None and self._state.token_cache_path is not None:
            loaded = await asyncio.to_thread(_token_cache.load, self._state.token_cache_path)
            if loaded is not None:
                self._state.refresh_token = loaded["refresh_token"]
        if _core.token_is_fresh(self._state):
            return
        lock = self._ensure_token_lock()
        async with lock:
            if _core.token_is_fresh(self._state):
                return
            if self._state.refresh_token:
                try:
                    await self._refresh_unlocked()
                except IOLAuthError:
                    # Phase 14 SEC-01 (anti-Pitfall 8, D-V3 sync mirror): the
                    # stale refresh_token is invalid — delete it from disk and
                    # clear in-memory BEFORE the password fallback so the disk
                    # never retains the stale token. D-A1: delete dispatched via
                    # asyncio.to_thread.
                    if self._state.token_cache_path is not None:
                        await asyncio.to_thread(_token_cache.delete, self._state.token_cache_path)
                    self._state.refresh_token = None
                else:
                    return
            await self._login_unlocked()

    async def _request(self, spec: RequestSpec) -> httpx.Response:
        """Dispatch an authenticated async request (Bearer) con 401 re-auth-once.

        Phase 8 D-02 + D-30 + RELY-04 async mirror: per-business-call UUID4
        ``request_id`` + extensions propagation; on 401 (``IOLAuthError`` from
        ``_raise_for_response``), the shell clears ``state.token``, calls
        ``_aensure_token()`` (which re-runs the login/refresh flow via the
        ``token_lock`` double-checked locking), then retries the request ONCE
        with the refreshed Authorization header. Second 401 raises directly
        (Pitfall 1 — no infinite loop). All non-401 error statuses raise their
        typed exceptions directly without re-auth.

        Phase 29 D-03 + aggregation-contract lock 6: the first two statements
        bind the decode mode and a fresh decode scope for this response. Each
        asyncio task carries its own copy of the context, so a concurrent task
        running in the other mode cannot clobber this bind.
        """
        # Phase 29 D-03 (sync mirror): bind the decode mode + a fresh decode
        # scope. There is deliberately NO reset and no try/finally — this
        # method returns the ``httpx.Response`` and the decode happens
        # AFTERWARDS, in the parser, which holds no reference to this client.
        _decode.STRICT_DECODE.set(self._state.strict_decode)
        _decode.open_request_scope()

        await self._aensure_token()
        lock = self._ensure_token_lock()
        async with lock:
            token = self._state.token
        assert token is not None

        request_id = uuid.uuid4().hex
        http = await self._ensure_http_client()
        url = f"{self._state.base_url}{spec.path}"
        headers = {"Authorization": f"Bearer {token}", **(spec.headers or {})}
        req = http.build_request(
            spec.method,
            url,
            params=spec.params,
            json=spec.json_body,
            headers=headers,
        )
        req.extensions["idempotent"] = spec.idempotent
        req.extensions["request_id"] = request_id
        req.extensions["endpoint_name"] = spec.endpoint_name
        # Phase 13 ERG-01: per-call override; parent or view's _max_retries
        # (Phase 8 D-19 N→N+1). Set uniformly (parent and view path).
        req.extensions["max_attempts"] = self._max_retries + 1
        resp = await http.send(req)
        try:
            _raise_for_response(resp)
        except IOLAuthError:
            # WR-02 hardening (async mirror): explicit body-consume before
            # re-auth path. httpx.AsyncClient.send already does response.aread()
            # by default (stream=False), but explicit aread() documents the
            # body-consume-then-raise contract (Phase 7 D-06) on the carve-out.
            await resp.aread()
            # D-02 exactly-one re-auth (async mirror).
            # WR-01 fix: token-clear + re-auth must be ATOMIC under the
            # token_lock. The previous version cleared self._state.token OUTSIDE
            # the lock, then called self._ensure_token() which takes the lock
            # internally — opening a race window where N concurrent coroutines
            # that all hit 401 would each clear the token and each enter
            # _ensure_token in serial, but the FIRST one to win the lock would
            # re-login, and subsequent ones would see token_is_fresh() True (good).
            # HOWEVER: between `self._state.token = None` and the lock acquire
            # inside _ensure_token, another coroutine on its INITIAL request
            # could read token=None before having a chance to enter _ensure_token,
            # causing it to ALSO race into a login attempt — defeating the
            # thundering-herd protection. The fix is to clear-then-re-auth
            # under a single lock acquisition by inlining the unlocked variants
            # (calling _ensure_token from within the lock would deadlock).
            async with lock:
                # Re-check inside lock: another coroutine may have already
                # cleared the token AND completed re-login. If so, just retry.
                if self._state.token is None or self._state.token == token:
                    self._state.token = None
                    if self._state.refresh_token:
                        try:
                            await self._refresh_unlocked()
                        except IOLAuthError:
                            await self._login_unlocked()
                    else:
                        await self._login_unlocked()
                new_token = self._state.token
            assert new_token is not None
            req.headers["Authorization"] = f"Bearer {new_token}"
            resp = await http.send(req)
            # WR-02 hardening: body-consume on second response BEFORE second raise.
            await resp.aread()
            _raise_for_response(resp)
        return resp

    # ------------------------------------------------------------------
    # Public endpoint methods (mirror sync Client) — 3-liner shells
    # ------------------------------------------------------------------

    async def get_quote(
        self,
        simbolo: str,
        *,
        mercado: str = "bcba",
        plazo: str = "t2",
    ) -> dict[str, Any]:
        """Cotización actual de un título (async)."""
        spec = _core.build_get_quote_request(self._state, simbolo, mercado=mercado, plazo=plazo)
        resp = await self._request(spec)
        return _core.parse_get_quote_response(resp)

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
        spec = _core.build_get_historical_quotes_request(
            self._state, simbolo, desde, hasta, mercado=mercado, ajustada=ajustada
        )
        resp = await self._request(spec)
        return _core.parse_get_historical_quotes_response(resp)

    async def get_instruments(self, pais: str = "argentina") -> Any:
        """Listado de instrumentos cotizando en ``pais`` (async)."""
        spec = _core.build_get_instruments_request(self._state, pais)
        resp = await self._request(spec)
        return _core.parse_get_instruments_response(resp)

    async def get_instruments_by_type(
        self,
        instrument_type: InstrumentType,
        *,
        pais: str = "argentina",
    ) -> list[dict[str, Any]]:
        """Listado de instrumentos por tipo y país (async)."""
        spec = _core.build_get_instruments_by_type_request(self._state, instrument_type, pais=pais)
        resp = await self._request(spec)
        return _core.parse_get_instruments_by_type_response(resp)


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
    max_retries: int | None = None,
    http_client: httpx.AsyncClient | None = None,
    strict_decode: bool | None = None,
) -> None:
    """Sobrescribe credenciales/URL en runtime con semántica carry-forward.

    Mirror del sync ``client.configure()``. Setting ``password=`` resetea
    token cacheado + refresh_token (v1.0 invariant). Otros kwargs ``None``
    se ignoran (carry-forward).

    Phase 8 D-15 / D-16: ``max_retries`` (default 2; ``0`` disables retries)
    and ``http_client`` (AsyncClient used AS-IS per D-16). Mutating either
    closes the prior cached ``httpx.AsyncClient`` so the next request
    re-creates it with the new transport. NOTE: configure() is synchronous,
    so the prior client is dropped without ``aclose()`` — callers should
    call ``await aclose()`` BEFORE reconfiguring the http client to avoid
    leaking the prior connection pool.

    Phase 29 D-03 mirror sync: ``strict_decode`` is a carry-forward kwarg —
    the ``None`` sentinel means "no cambiar", so a later
    ``configure(base_url=...)`` does NOT reset a previous strict opt-in.
    """
    # WR-06: validate max_retries (only when explicitly passed).
    if max_retries is not None:
        _validate_max_retries(max_retries)
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
    # Phase 29 D-03 (sync mirror): ``None`` = "no cambiar" (Pitfall 5).
    if strict_decode is not None:
        client._state.strict_decode = strict_decode
    # Phase 8 D-15: drop the cached httpx.AsyncClient when retry policy or the
    # caller-supplied client changes — next request will rebuild with the new
    # transport. Pitfall: configure() is sync; we cannot await prior.aclose()
    # here. Caller is expected to await aclose() before reconfiguring (D-16).
    if max_retries is not None:
        # WR-07: warn before dropping a live httpx.AsyncClient — its connection
        # pool + SSL context leak until garbage collection. The recommended
        # consumer pattern is `await aio.aclose()` BEFORE configure(...).
        if client._state.http_client is not None:
            warnings.warn(
                "iol_client.aio.configure(): replacing a live httpx.AsyncClient "
                "(via max_retries=) without awaiting aclose() leaks the "
                "connection pool. Call `await iol_client.aio.aclose()` before "
                "configure(...) to avoid the leak.",
                ResourceWarning,
                stacklevel=2,
            )
        client._max_retries = max_retries
        client._state.http_client = None
    if http_client is not None:
        # WR-07: same warning if caller is replacing a live client via http_client=.
        if client._state.http_client is not None and client._state.http_client is not http_client:
            warnings.warn(
                "iol_client.aio.configure(): replacing a live httpx.AsyncClient "
                "(via http_client=) without awaiting aclose() leaks the "
                "connection pool. Call `await iol_client.aio.aclose()` before "
                "configure(...) to avoid the leak.",
                ResourceWarning,
                stacklevel=2,
            )
        client._state.http_client = http_client


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
    """Top-level shim for legacy tests that call ``aio._request(...)``.

    Adapts the legacy (method, path, params=, json_body=) signature to the
    Phase 7 ``AsyncClient._request(spec)`` signature by constructing a
    transient ``RequestSpec`` on the fly. Mirrors the sync shim by
    raising the typed exception on error status (D-03 the new
    ``AsyncClient._request`` returns raw ``httpx.Response``; the legacy
    shim keeps the v1.0 raise-on-error semantic for tests that called
    ``iol_client.aio._request(...)`` directly).
    """
    spec = RequestSpec(method=method, path=path, params=params, json_body=json_body)
    resp = await _get_default()._request(spec)
    if resp.is_error:
        _raise_for_response(resp)
    return resp


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
