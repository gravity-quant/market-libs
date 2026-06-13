"""Cliente HTTP sincrónico para Invertir Online (IOL).

API a nivel módulo (back-compat 100% con v1.0)::

    import iol_client

    iol_client.login()
    quote = iol_client.get_quote("GGAL")

API basada en clase (Phase 6+)::

    from iol_client import Client

    with Client(username="alice", password="secret") as client:
        quote = client.get_quote("GGAL")

IOL usa OAuth 2.0 password grant: ``POST /token`` con
``grant_type=password&username=...&password=...`` devuelve
``{"access_token", "refresh_token", "expires_in"}``. Este cliente cachea
``access_token`` y lo refresca automáticamente antes del vencimiento, con
fallback al password grant si el refresh resulta inválido.

Variables de entorno (cargadas con ``python-dotenv``):

- ``IOL_USER`` (requerido)
- ``IOL_PASSWORD`` (requerido)
- ``IOL_BASE_URL`` (opcional, default ``https://api.invertironline.com``).

El módulo expone un shim PEP 562 (read-only) que forwarda lecturas legacy
de ``_token``, ``_token_expires_at``, ``_refresh_token`` y ``_client`` al
``_default_client._state.*`` para preservar back-compat con tests/drivers
existentes. El helper ``_raise_for_response`` es un alias module-level
(``= _core.raise_for_response`` — D-04) que mantiene la identidad B8
(``aio._raise_for_response is client._raise_for_response``) sin duplicar
lógica de mapeo de errores. La auth-flow + endpoint dispatch viven en
``iol_client._core`` (D-02).

CR-01: la política conditional refresh-token rotation (Phase 6 D-05) se
preserva en este transport shell: ``login()`` y ``_refresh()`` actualizan
``self._state.refresh_token`` SOLO si el parser retorna un valor
non-None — si el server omite el nuevo refresh_token, se mantiene el
cacheado.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Any, Literal, Self

import httpx
from dotenv import load_dotenv

from iol_client import _core, _transport
from iol_client._core import RequestSpec
from iol_client._state import _REQUEST_TIMEOUT, _ClientState
from iol_client.exceptions import IOLAuthError

InstrumentType = Literal[
    "obligacionesNegociables",
    "titulosPublicos",
    "cedears",
    "acciones",
    "letras",
    "cauciones",
]

load_dotenv()


# ----------------------------------------------------------------------
# Stateless helpers (D-04 alias — sourced from _core.py to preserve B8)
# ----------------------------------------------------------------------

# D-04: preserves B8 identity. Tests `aio._raise_for_response is
# client._raise_for_response` stay green because BOTH aliases reference
# the SAME object (_core.raise_for_response).
_raise_for_response = _core.raise_for_response


# WR-06 Phase 8 review fix: validate max_retries kwarg early. Duplicated 4x
# across packages per the "no shared internals" project constraint.
def _validate_max_retries(value: int) -> None:
    """Validate the ``max_retries`` kwarg.

    Phase 8 D-19: ``max_retries`` must be a non-negative ``int``. Negative
    values and non-int types (incl. ``float``, ``bool``) are rejected early
    with ``ValueError`` instead of crashing later inside tenacity.
    """
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


# ----------------------------------------------------------------------
# Client class
# ----------------------------------------------------------------------


class Client:
    """Sync client for the IOL REST API.

    Per-instance state lives in ``self._state`` (a :class:`_ClientState`
    dataclass). The class owns an ``httpx.Client`` lazily, the OAuth token
    cache, and the refresh-token rotation.

    Pickle / deepcopy contract (D-23): NOT supported. ``__reduce__`` and
    ``__deepcopy__`` raise ``TypeError`` to fail loud — the ``httpx.Client``
    owns a TCP connection pool + SSL context that cannot be cloned. Use
    ``multiprocessing``'s fork start method, or rebuild from
    ``iol_client.configure(...)`` inside the worker.

    Lifecycle: instances are context managers (``with Client() as c: ...``)
    and must be ``close()``d to release the underlying HTTP transport.
    ``close()`` is idempotent.
    """

    __slots__ = ("_max_retries", "_state")

    def __init__(
        self,
        *,
        base_url: str | None = None,
        username: str | None = None,
        password: str | None = None,
        token: str | None = None,
        token_expires_at: float | None = None,
        max_retries: int = 2,
        http_client: httpx.Client | None = None,
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
        # Phase 8 D-15 / D-19: max_retries=N → max_attempts=N+1 (1 initial + N retries).
        # max_retries=0 disables retries entirely per D-19 (max_attempts <= 1 bypass).
        self._max_retries = max_retries
        # Phase 8 D-16: caller-supplied http_client used AS-IS (no auto-wrap).
        if http_client is not None:
            self._state.http_client = http_client

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: object,
    ) -> None:
        self.close()

    def close(self) -> None:
        """Release the underlying ``httpx.Client`` (idempotent)."""
        http_client = self._state.http_client
        if http_client is not None:
            assert isinstance(http_client, httpx.Client)
            http_client.close()
            self._state.http_client = None

    def __repr__(self) -> str:
        # D-18 + T-06-05: redact password, token AND refresh_token.
        password_repr = "'***'" if self._state.password else "''"
        token_repr = "'***'" if self._state.token else "None"
        refresh_repr = "'***'" if self._state.refresh_token else "None"
        return (
            f"IOLClient(base_url={self._state.base_url!r}, "
            f"username={self._state.username!r}, "
            f"password={password_repr}, "
            f"token={token_repr}, "
            f"refresh_token={refresh_repr})"
        )

    def __reduce__(self) -> Any:  # D-23
        raise TypeError(
            "IOLClient is not picklable; use multiprocessing's fork start "
            "method or recreate in worker via iol_client.Client(...)"
        )

    def __deepcopy__(self, memo: dict[int, Any]) -> Client:  # D-23
        raise TypeError(
            "IOLClient is not deepcopy-safe (httpx.Client owns TCP pool + "
            "SSL context). Recreate from configure() in the "
            "target context instead."
        )

    # ------------------------------------------------------------------
    # HTTP transport + OAuth
    # ------------------------------------------------------------------

    def _ensure_http_client(self) -> httpx.Client:
        """Lazily create the per-instance ``httpx.Client``.

        Phase 8 D-15 / D-19: wraps ``RetryTransport`` so all requests (auth and
        endpoint) benefit from bounded retries + full-jitter backoff. The
        transport's mutation gate (D-01) honors ``request.extensions["idempotent"]``
        so non-idempotent specs pass through with no retry loop. ``max_attempts =
        max_retries + 1`` per the anthropic/openai SDK semantics (D-19).
        """
        http_client = self._state.http_client
        if http_client is not None:
            assert isinstance(http_client, httpx.Client)
            return http_client
        new_client = httpx.Client(
            timeout=_REQUEST_TIMEOUT,
            transport=_transport.RetryTransport(max_attempts=self._max_retries + 1),
        )
        self._state.http_client = new_client
        return new_client

    def _send_auth_request(self, spec: RequestSpec) -> httpx.Response:
        """Send an auth-flow request through the RetryTransport with extensions.

        Phase 8 D-29: login + refresh go through the SAME RetryTransport as
        endpoint requests so transient 5xx are retry-eable (D-03 marks the
        auth-flow builders ``idempotent=True``). The shell propagates
        ``request_id`` + ``endpoint_name`` via ``request.extensions`` so the
        transport's structured WARNING/ERROR records carry the canonical D-09
        fields. NO ``Authorization`` header — auth-flow itself establishes the
        token.
        """
        http = self._ensure_http_client()
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
        return http.send(req)

    def login(self) -> str:
        """Autentica contra ``POST /token`` (OAuth password grant)."""
        spec = _core.build_login_request(self._state)
        resp = self._send_auth_request(spec)
        token, expires_at, refresh = _core.parse_login_response(resp)
        self._state.token = token
        self._state.token_expires_at = expires_at
        # CR-01 conditional rotation preserved (Phase 6 D-05): solo escribir
        # state.refresh_token cuando el parser nos da un valor truthy.
        if refresh is not None:
            self._state.refresh_token = refresh
        return token

    def _refresh(self) -> str:
        """POST /token con ``grant_type=refresh_token`` (mirror de login())."""
        spec = _core.build_refresh_request(self._state)
        resp = self._send_auth_request(spec)
        token, expires_at, refresh = _core.parse_refresh_response(resp)
        self._state.token = token
        self._state.token_expires_at = expires_at
        # CR-01 conditional rotation preserved: server puede no rotar el
        # refresh_token en cada refresh — preservar el cacheado entonces.
        if refresh is not None:
            self._state.refresh_token = refresh
        return token

    def _ensure_token(self) -> None:
        if _core.token_is_fresh(self._state):
            return
        # D-IOL-10: si tenemos refresh_token, intentar refresh antes de password.
        if self._state.refresh_token:
            try:
                self._refresh()
            except IOLAuthError:
                # Refresh inválido (revocado, expirado) — fallback a password.
                pass
            else:
                return
        self.login()

    def _request(self, spec: RequestSpec) -> httpx.Response:
        """Ejecuta una request autenticada (Bearer) con 401 re-auth-once.

        Phase 8 D-02 + D-30 + RELY-04: per-business-call ``request_id`` (UUID4)
        propagated via ``request.extensions``; on 401 (``IOLAuthError`` raised
        by ``_raise_for_response``), the shell clears the cached token, calls
        ``_ensure_token()`` to obtain a fresh Bearer, then retries the request
        ONCE with the refreshed Authorization header. The transport NEVER sees
        IOLAuthError (D-07 invariant — only HTTP/transport signals trigger
        retry); the shell handles the auth-stale case explicitly.

        Second-401 case: if the retry also yields 401, ``_raise_for_response``
        on the second response re-raises IOLAuthError — NO recursion, NO
        infinite loop (Pitfall 1 prevention). All non-401 error statuses
        (429, 5xx, etc.) raise their typed exceptions directly without re-auth.
        """
        self._ensure_token()
        assert self._state.token is not None

        request_id = uuid.uuid4().hex
        http = self._ensure_http_client()
        url = f"{self._state.base_url}{spec.path}"
        headers = {"Authorization": f"Bearer {self._state.token}", **(spec.headers or {})}
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
        resp = http.send(req)
        try:
            _raise_for_response(resp)
        except IOLAuthError:
            # WR-02 hardening: explicit body-consume before re-auth path.
            # httpx.Client.send already calls response.read() by default
            # (stream=False), and _raise_for_response touches resp.text which
            # buffers the body; this resp.read() is therefore idempotent on the
            # in-memory buffer but documents the body-consume-then-raise
            # contract (Phase 7 D-06) explicitly for the carve-out path. Belt
            # and suspenders against future httpx auto-consume changes or
            # http2=True streaming responses.
            resp.read()
            # D-02 exactly-one re-auth: clear cached token, re-authenticate, retry once.
            # IOL has no Risk API → no auth_basic branch to skip (cf. matriz D-23).
            self._state.token = None
            self._ensure_token()
            assert self._state.token is not None
            req.headers["Authorization"] = f"Bearer {self._state.token}"
            resp = http.send(req)
            # WR-02 hardening: same body-consume on the second response BEFORE
            # _raise_for_response. If the second send returned a 401 still, the
            # AuthError that surfaces will already have a fully-consumed body.
            resp.read()
            _raise_for_response(resp)
        return resp

    # ------------------------------------------------------------------
    # Public endpoint methods — 3-liner shells consume _core builders/parsers
    # ------------------------------------------------------------------

    def get_quote(
        self,
        simbolo: str,
        *,
        mercado: str = "bcba",
        plazo: str = "t2",
    ) -> dict[str, Any]:
        """Cotización actual de un título.

        Endpoint: ``GET /api/v2/{mercado}/Titulos/{simbolo}/Cotizacion``.
        """
        spec = _core.build_get_quote_request(self._state, simbolo, mercado=mercado, plazo=plazo)
        resp = self._request(spec)
        return _core.parse_get_quote_response(resp)

    def get_historical_quotes(
        self,
        simbolo: str,
        desde: dt.date,
        hasta: dt.date,
        *,
        mercado: str = "bcba",
        ajustada: Literal["ajustada", "sinAjustar"] = "sinAjustar",
    ) -> list[dict[str, Any]]:
        """Serie histórica de cotizaciones diarias para ``[desde, hasta]``.

        Endpoint:
        ``GET /api/v2/{mercado}/Titulos/{simbolo}/Cotizacion/seriehistorica/{desde}/{hasta}/{ajustada}``.
        """
        spec = _core.build_get_historical_quotes_request(
            self._state, simbolo, desde, hasta, mercado=mercado, ajustada=ajustada
        )
        resp = self._request(spec)
        return _core.parse_get_historical_quotes_response(resp)

    def get_instruments(self, pais: str = "argentina") -> Any:
        """Listado de instrumentos cotizando en ``pais``.

        Endpoint: ``GET /api/v2/{pais}/Titulos/Cotizacion/Instrumentos``.
        """
        spec = _core.build_get_instruments_request(self._state, pais)
        resp = self._request(spec)
        return _core.parse_get_instruments_response(resp)

    def get_instruments_by_type(
        self,
        instrument_type: InstrumentType,
        *,
        pais: str = "argentina",
    ) -> list[dict[str, Any]]:
        """Listado de instrumentos filtrado por tipo y país.

        Endpoint: ``GET /api/v2/Cotizaciones/{instrument_type}/{pais}/Todos``.
        Devuelve la lista bajo la clave ``"titulos"`` del payload.
        """
        spec = _core.build_get_instruments_by_type_request(self._state, instrument_type, pais=pais)
        resp = self._request(spec)
        return _core.parse_get_instruments_by_type_response(resp)


# ----------------------------------------------------------------------
# Default-client lazy singleton + top-level shims (back-compat with v1.0)
# ----------------------------------------------------------------------


_default_client: Client | None = None


def _get_default() -> Client:
    """Lazy access to the module-level default Client (env-var constructed)."""
    global _default_client
    if _default_client is None:
        _default_client = Client()
    return _default_client


def configure(
    *,
    base_url: str | None = None,
    username: str | None = None,
    password: str | None = None,
    token: str | None = None,
    token_expires_at: float | None = None,
    refresh_token: str | None = None,
    max_retries: int | None = None,
    http_client: httpx.Client | None = None,
) -> None:
    """Sobrescribe credenciales/URL en runtime con semántica carry-forward.

    Carry-forward (RESEARCH.md Open Q #5): los campos ``None`` se ignoran;
    los demás sobrescriben en el ``_default_client._state``. La invariante
    legacy "configure() resetea token cacheado" se preserva pasando
    ``password=`` (lo cual invalida la auth): se resetea el ``token`` y
    el ``refresh_token`` cacheados.

    El kwarg ``refresh_token=`` es una extensión Pitfall #3 al D-13
    (que enumeraba solo ``token=``/``token_expires_at=``): la migración
    de tests legacy desde ``monkeypatch.setattr(..._refresh_token, X)``
    podría haber usado direct-state write, pero exponer el kwarg da una
    API simétrica (configure(token=X) ↔ configure(refresh_token=X)). El
    surface kwargs completo aterriza en Phase 9 BUG-03 (D-13).

    Phase 8 D-15 / D-16 / D-19: ``max_retries`` (default 2; ``0`` disables
    retries entirely per D-19) and ``http_client`` (used AS-IS without
    auto-wrapping with ``RetryTransport`` per D-16) are carry-forward
    kwargs. Mutating ``max_retries`` or ``http_client`` closes the prior
    cached ``httpx.Client`` so the next request re-creates it with the
    new transport.
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
        # Rotar credenciales invalida el token cacheado (semántica v1.0).
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
    # Phase 8 D-15: rebuild the cached httpx.Client when retry policy changes
    # so the new max_attempts takes effect on the next request.
    if max_retries is not None:
        client._max_retries = max_retries
        if client._state.http_client is not None:
            assert isinstance(client._state.http_client, httpx.Client)
            client._state.http_client.close()
            client._state.http_client = None
    if http_client is not None:
        if client._state.http_client is not None:
            assert isinstance(client._state.http_client, httpx.Client)
            client._state.http_client.close()
        # D-16: caller-supplied http_client used AS-IS (no auto-wrap).
        client._state.http_client = http_client


def login() -> str:
    """Top-level shim: delega al default Client."""
    return _get_default().login()


def get_quote(
    simbolo: str,
    *,
    mercado: str = "bcba",
    plazo: str = "t2",
) -> dict[str, Any]:
    """Top-level shim: delega al default Client."""
    return _get_default().get_quote(simbolo, mercado=mercado, plazo=plazo)


def get_historical_quotes(
    simbolo: str,
    desde: dt.date,
    hasta: dt.date,
    *,
    mercado: str = "bcba",
    ajustada: Literal["ajustada", "sinAjustar"] = "sinAjustar",
) -> list[dict[str, Any]]:
    """Top-level shim: delega al default Client."""
    return _get_default().get_historical_quotes(
        simbolo, desde, hasta, mercado=mercado, ajustada=ajustada
    )


def get_instruments(pais: str = "argentina") -> Any:
    """Top-level shim: delega al default Client."""
    return _get_default().get_instruments(pais)


def get_instruments_by_type(
    instrument_type: InstrumentType,
    *,
    pais: str = "argentina",
) -> list[dict[str, Any]]:
    """Top-level shim: delega al default Client."""
    return _get_default().get_instruments_by_type(instrument_type, pais=pais)


def _request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
) -> httpx.Response:
    """Top-level shim used by legacy tests calling ``iol_client.client._request``.

    Adapts the legacy (method, path, params=, json_body=) signature to the
    Phase 7 ``Client._request(spec)`` signature by constructing a transient
    ``RequestSpec`` on the fly. Preserves the v1.0 contract of "raise on
    error status before returning" — the new ``Client._request`` (D-03)
    returns the raw ``httpx.Response`` un-touched, but this top-level shim
    keeps the legacy semantic so tests that called the shim directly
    (e.g. ``iol_client.client._request("GET", "/api/anything")``) still
    see ``IOLAuthError`` / ``IOLRateLimitError`` / ``IOLAPIError`` raised
    on 4xx/5xx responses.
    """
    spec = RequestSpec(method=method, path=path, params=params, json_body=json_body)
    resp = _get_default()._request(spec)
    if resp.is_error:
        _raise_for_response(resp)
    return resp


# ----------------------------------------------------------------------
# PEP 562 read-only shim (D-01, D-02 + Pitfall #3 addendum)
# ----------------------------------------------------------------------

# Read-only forwarding for legacy global names. NO __setattr__ — writes
# from test bodies that go through ``module.X = Y`` hit the module dict
# directly (research Pitfall #1, #4) and are migrated to direct-state
# mutation in the per-package commit.
_FORWARDED_TO_STATE: dict[str, str] = {
    "_token": "token",
    "_token_expires_at": "token_expires_at",
    # Pitfall #3 addendum to D-02: _refresh_token MUST be in this allowlist
    # for IOL or 13+ test sites that read iol_client.client._refresh_token
    # would receive AttributeError after the refactor.
    "_refresh_token": "refresh_token",
}

_FORWARDED_HTTP_CLIENT = "_client"  # D-02 exception for main_higyrus.py shape

# Sentinel deny-list documented as exact AttributeError targets (T-06-01).
# These globals existed in v1.0 (_user, _password, _base_url) but are
# intentionally NOT forwarded — reads receive AttributeError. Writes via
# the PEP 562 shim are impossible (read-only by spec).
_DENIED_LEGACY: frozenset[str] = frozenset({"_user", "_password", "_base_url"})


def __getattr__(name: str) -> Any:
    """PEP 562 read-only shim (D-01).

    - Forwarded names (``_FORWARDED_TO_STATE`` + ``_client``) resolve to
      the default Client's state.
    - Denied legacy names (``_user``, ``_password``, ``_base_url``) raise
      ``AttributeError`` explicitly.
    - Unknown names raise the standard module-level ``AttributeError``.
    """
    if name in _FORWARDED_TO_STATE:
        return getattr(_get_default()._state, _FORWARDED_TO_STATE[name])
    if name == _FORWARDED_HTTP_CLIENT:
        return _get_default()._state.http_client
    if name in _DENIED_LEGACY:
        raise AttributeError(
            f"module {__name__!r} has no attribute {name!r} "
            f"(legacy global removed in Phase 6; use iol_client.configure() "
            f"or iol_client._get_default()._state.{name.lstrip('_')} instead)"
        )
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
