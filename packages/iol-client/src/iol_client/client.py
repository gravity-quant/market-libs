"""Cliente HTTP sincrónico para Invertir Online (IOL).

API a nivel módulo (back-compat 100% con v1.0)::

    import iol_client

    iol_client.login()
    quote = iol_client.get_quote("GGAL")

API basada en clase (nueva en Phase 6)::

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
existentes. El helper ``_raise_for_response`` se mantiene a nivel módulo
porque es stateless y ``aio.py`` lo importa directamente (B8 — sin
duplicación; consistente con el patrón actual de ``aio.py`` importando
``InstrumentType`` desde ``client.py``).
"""

from __future__ import annotations

import datetime as dt
import time
from typing import Any, Literal, Self

import httpx
from dotenv import load_dotenv

from iol_client._state import (
    _REQUEST_TIMEOUT,
    _TOKEN_TTL_BUFFER_SECONDS,
    _ClientState,
)
from iol_client.exceptions import IOLAPIError, IOLAuthError, IOLRateLimitError

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
# Stateless helpers
# ----------------------------------------------------------------------


def _raise_for_response(resp: httpx.Response) -> None:
    """Map an HTTP error response to the package's exception hierarchy.

    Shared with ``aio.py`` — imported there; not duplicated (B8).
    """
    if resp.status_code in (401, 403):
        raise IOLAuthError(resp.status_code, resp.text)
    if resp.status_code == 429:
        raise IOLRateLimitError(resp.status_code, resp.text)
    if resp.is_error:
        raise IOLAPIError(resp.status_code, resp.text)


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

    __slots__ = ("_state",)

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
            "SSL context). Recreate the client from configure() in the "
            "target context instead."
        )

    # ------------------------------------------------------------------
    # HTTP transport + OAuth
    # ------------------------------------------------------------------

    def _ensure_http_client(self) -> httpx.Client:
        """Lazily create the per-instance ``httpx.Client``."""
        http_client = self._state.http_client
        if http_client is not None:
            assert isinstance(http_client, httpx.Client)
            return http_client
        new_client = httpx.Client(timeout=_REQUEST_TIMEOUT)
        self._state.http_client = new_client
        return new_client

    def login(self) -> str:
        """Autentica contra ``POST /token`` (OAuth password grant)."""
        if not self._state.username or not self._state.password:
            raise IOLAuthError(0, "IOL_USER y IOL_PASSWORD son requeridos")

        client = self._ensure_http_client()
        resp = client.post(
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
        # CR-01: política condicional simétrica con _refresh() (Pitfall 3).
        # Si el server NO incluye refresh_token, MANTENER el cached.
        new_refresh = data.get("refresh_token")
        if isinstance(new_refresh, str) and new_refresh:
            self._state.refresh_token = new_refresh
        self._state.token_expires_at = time.time() + float(expires_in) - _TOKEN_TTL_BUFFER_SECONDS
        return access_token

    def _refresh(self) -> str:
        """POST /token con ``grant_type=refresh_token`` (mirror de login())."""
        # Local copy para mypy narrowing (Pitfall 4): el field es Optional.
        refresh_token = self._state.refresh_token
        if not refresh_token:
            raise IOLAuthError(0, "No refresh_token cached")

        client = self._ensure_http_client()
        resp = client.post(
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
        # Rotación condicional (Pitfall 3): si el server retorna nuevo
        # refresh_token, lo cacheamos; si no, mantenemos el existente.
        new_refresh = data.get("refresh_token")
        if isinstance(new_refresh, str) and new_refresh:
            self._state.refresh_token = new_refresh
        self._state.token_expires_at = time.time() + float(expires_in) - _TOKEN_TTL_BUFFER_SECONDS
        return access_token

    def _ensure_token(self) -> None:
        if self._state.token and time.time() < self._state.token_expires_at:
            return
        # D-IOL-10: si tenemos refresh_token, intentar refresh antes de password.
        if self._state.refresh_token:
            try:
                self._refresh()
                return
            except IOLAuthError:
                # Refresh inválido (revocado, expirado) — fallback a password.
                pass
        self.login()

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Ejecuta una request autenticada (Bearer)."""
        self._ensure_token()
        assert self._state.token is not None

        client = self._ensure_http_client()
        resp = client.request(
            method,
            f"{self._state.base_url}{path}",
            params=params,
            json=json_body,
            headers={"Authorization": f"Bearer {self._state.token}"},
        )
        if resp.is_error:
            _raise_for_response(resp)
        return resp

    # ------------------------------------------------------------------
    # Public endpoint methods
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
        resp = self._request(
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
        resp = self._request(
            "GET",
            f"/api/v2/{mercado}/Titulos/{simbolo}/Cotizacion/seriehistorica/"
            f"{desde:%Y-%m-%d}/{hasta:%Y-%m-%d}/{ajustada}",
        )
        data: list[dict[str, Any]] = resp.json()
        return data

    def get_instruments(self, pais: str = "argentina") -> Any:
        """Listado de instrumentos cotizando en ``pais``.

        Endpoint: ``GET /api/v2/{pais}/Titulos/Cotizacion/Instrumentos``.
        """
        resp = self._request("GET", f"/api/v2/{pais}/Titulos/Cotizacion/Instrumentos")
        return resp.json()

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
        resp = self._request("GET", f"/api/v2/Cotizaciones/{instrument_type}/{pais}/Todos")
        data: dict[str, Any] = resp.json()
        titulos: list[dict[str, Any]] = data.get("titulos", [])
        return titulos


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
    """
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
    """Top-level shim used by legacy tests calling ``iol_client.client._request``."""
    return _get_default()._request(method, path, params=params, json_body=json_body)


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
