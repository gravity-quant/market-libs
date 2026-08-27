"""Pure builders and parsers for the iol-client REST client.

Phase 7 REFAC-03 + D-01 (per-package ``RequestSpec``) + D-02 (auth-flow
factorizado en builder/parser) + D-03 (transport shell consume ``httpx.Response``)
+ D-04 (alias module-level preserva B8 identity) + D-06 (body-consume-then-raise
en parsers).

All functions are PURE: state in → ``RequestSpec`` (builders) or
``httpx.Response`` in → typed result (parsers). NO I/O dispatch
(``httpx.Client.request``/``await httpx.AsyncClient.request`` lives en
``client.py``/``aio.py``). NO imports from ``iol_client.client`` ni
``iol_client.aio`` (enforced by ``import-linter`` contract en
``pyproject.toml [tool.importlinter]``).

Usage from a transport shell (e.g. ``client.py``)::

    from iol_client import _core

    def login(self) -> str:
        spec = _core.build_login_request(self._state)
        http = self._ensure_http_client()
        resp = http.post(
            f"{self._state.base_url}{spec.path}",
            data=spec.data,
            headers=spec.headers,
        )
        token, expires_at, refresh = _core.parse_login_response(resp)
        self._state.token = token
        self._state.token_expires_at = expires_at
        if refresh is not None:
            # CR-01 conditional refresh rotation preserved: solo actualizar
            # el ``refresh_token`` cacheado cuando el server provee uno truthy.
            self._state.refresh_token = refresh
        return token

CR-01 honesty flag — IOL OAuth refresh-token rotation is CONDITIONAL: if the
server omits ``refresh_token`` in a login/refresh response, the transport
shell MUST keep the previously cached value. ``parse_login_response`` and
``parse_refresh_response`` return ``None`` in the refresh slot when the
response lacks (or has a non-string/empty) ``refresh_token`` field; the
caller MUST check ``if refresh is not None: state.refresh_token = refresh``
to preserve the cached value. See Phase 6 D-05 / Phase 7 D-02 + CR-01.
"""

from __future__ import annotations

import datetime as dt
import time
from dataclasses import dataclass
from typing import Any, Literal

import httpx

from iol_client import _decode
from iol_client._state import _TOKEN_TTL_BUFFER_SECONDS, _ClientState
from iol_client.exceptions import IOLAPIError, IOLAuthError, IOLRateLimitError
from iol_client.models import Cotizacion, Instrumento, Titulo

__all__ = [
    "RequestSpec",
    "build_get_historical_quotes_request",
    "build_get_instruments_by_type_request",
    "build_get_instruments_request",
    "build_get_quote_request",
    "build_login_request",
    "build_refresh_request",
    "parse_get_historical_quotes_response",
    "parse_get_instruments_by_type_response",
    "parse_get_instruments_response",
    "parse_get_quote_response",
    "parse_login_response",
    "parse_refresh_response",
    "raise_for_response",
    "token_is_fresh",
]


# ----------------------------------------------------------------------
# RequestSpec
# ----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RequestSpec:
    """Pure description of an HTTP request — no transport coupling.

    Per-package shape (D-01 / no shared internals): iol-specific ``data``
    field for OAuth ``POST /token`` form-encoded body
    (``application/x-www-form-urlencoded``, NOT JSON).

    Phase 8 extensions (D-09 / D-13): ``idempotent`` drives the
    ``RetryTransport`` mutation gate (``request.extensions["idempotent"]``);
    ``endpoint_name`` flows into structured log records
    (``extra["endpoint_name"]``). Both default to safe values (``False`` for
    idempotent — mutation gate prevents retry of unmarked specs; ``""`` for
    endpoint_name — empty string is a valid identifier in the log extra).
    """

    method: str
    path: str
    params: dict[str, Any] | None = None
    headers: dict[str, str] | None = None
    json_body: dict[str, Any] | None = None
    data: dict[str, Any] | None = None
    idempotent: bool = False
    endpoint_name: str = ""


# ----------------------------------------------------------------------
# Stateless helpers (D-04 — moved from client.py; alias preserved there)
# ----------------------------------------------------------------------


def raise_for_response(resp: httpx.Response) -> None:
    """Map an HTTP error response to the package's exception hierarchy.

    Shared with sync ``client.py`` and async ``aio.py`` via module-level
    alias ``_raise_for_response = _core.raise_for_response`` (D-04). The
    aliases reference the SAME object so the B8 identity invariant
    ``aio._raise_for_response is client._raise_for_response`` stays True.
    """
    if resp.status_code in (401, 403):
        raise IOLAuthError(resp.status_code, resp.text)
    if resp.status_code == 429:
        raise IOLRateLimitError(resp.status_code, resp.text)
    if resp.is_error:
        raise IOLAPIError(resp.status_code, resp.text)


def token_is_fresh(state: _ClientState) -> bool:
    """Pure helper: True iff ``state.token`` is set AND not yet expired.

    Used by the transport shells' ``_ensure_token()`` (sync + async) to
    decide whether to skip the auth flow on a given request.
    """
    return bool(state.token and time.time() < state.token_expires_at)


# ----------------------------------------------------------------------
# Auth flow primitives (D-02)
# ----------------------------------------------------------------------


def build_login_request(state: _ClientState) -> RequestSpec:
    """Pure: build the OAuth password-grant login request spec.

    Endpoint: ``POST /token`` with ``grant_type=password``.

    Phase 8 D-03 / D-29: ``idempotent=True`` — OAuth password grant is
    replay-safe (a transient 5xx during login can be retried; a successful
    re-issue just overwrites the prior access_token in state). Marks the
    transport mutation gate to allow retry. 401 from the auth endpoint is
    NEVER retry-eable (D-02 / Pitfall 1).
    """
    if not state.username or not state.password:
        raise IOLAuthError(0, "IOL_USER y IOL_PASSWORD son requeridos")
    return RequestSpec(
        method="POST",
        path="/token",
        data={
            "username": state.username,
            "password": state.password,
            "grant_type": "password",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        idempotent=True,
        endpoint_name="login",
    )


def parse_login_response(resp: httpx.Response) -> tuple[str, float, str | None]:
    """Pure: parse the OAuth login response → ``(token, expires_at, refresh|None)``.

    Order (D-06 body-consume-then-raise):

    1. ``resp.read()`` — explicit body consume (HTTP/2-safe).
    2. ``raise_for_response(resp)`` — status check after body consumed.
    3. ``resp.json()`` — decode (raises ``ValueError`` if malformed).
    4. Extract ``access_token`` / ``expires_in`` / ``refresh_token``.

    CR-01 conditional rotation: the refresh slot returns ``None`` when the
    response lacks (or has a non-string/empty) ``refresh_token`` field.
    The caller (transport shell) is responsible for writing to state ONLY
    when the value is non-None — preserves the cached ``refresh_token``
    when the IOL server omits it.
    """
    resp.read()
    raise_for_response(resp)
    data: dict[str, Any] = resp.json()
    access_token = data.get("access_token")
    expires_in = data.get("expires_in", 900)
    if not isinstance(access_token, str) or not access_token:
        raise IOLAuthError(resp.status_code, "No access_token in response")
    new_refresh = data.get("refresh_token")
    refresh_out = new_refresh if isinstance(new_refresh, str) and new_refresh else None
    expires_at = time.time() + float(expires_in) - _TOKEN_TTL_BUFFER_SECONDS
    return access_token, expires_at, refresh_out


def build_refresh_request(state: _ClientState) -> RequestSpec:
    """Pure: build the OAuth refresh-token request spec.

    Endpoint: ``POST /token`` with ``grant_type=refresh_token``.

    Phase 8 D-03 / D-29: ``idempotent=True`` — refresh grant is replay-safe.
    Same retry semantics as login (5xx retry-eable, 401 raises immediately
    so the shell falls back to password grant per ``_ensure_token`` body).
    """
    refresh_token = state.refresh_token
    if not refresh_token:
        raise IOLAuthError(0, "No refresh_token cached")
    return RequestSpec(
        method="POST",
        path="/token",
        data={"refresh_token": refresh_token, "grant_type": "refresh_token"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        idempotent=True,
        endpoint_name="refresh",
    )


def parse_refresh_response(resp: httpx.Response) -> tuple[str, float, str | None]:
    """Pure: parse the OAuth refresh response → ``(token, expires_at, refresh|None)``.

    Same response shape as ``parse_login_response`` per the IOL OAuth
    server contract — alias to keep the CR-01 honesty flag in one place.
    """
    return parse_login_response(resp)


# ----------------------------------------------------------------------
# Endpoint builders
# ----------------------------------------------------------------------


def build_get_quote_request(
    state: _ClientState,
    simbolo: str,
    *,
    mercado: str = "bcba",
    plazo: str = "t2",
) -> RequestSpec:
    """Pure: build spec for ``GET /api/v2/{mercado}/Titulos/{simbolo}/Cotizacion``.

    Phase 8 D-03 / RELY-03: ``idempotent=True`` — GET endpoints are retry-safe.
    """
    del state  # state-independent (path interpolated from args)
    return RequestSpec(
        method="GET",
        path=f"/api/v2/{mercado}/Titulos/{simbolo}/Cotizacion",
        params={
            "model.mercado": mercado,
            "model.simbolo": simbolo,
            "model.plazo": plazo,
        },
        idempotent=True,
        endpoint_name="get_quote",
    )


def build_get_historical_quotes_request(
    state: _ClientState,
    simbolo: str,
    desde: dt.date,
    hasta: dt.date,
    *,
    mercado: str = "bcba",
    ajustada: Literal["ajustada", "sinAjustar"] = "sinAjustar",
) -> RequestSpec:
    """Pure: build spec for the seriehistorica endpoint.

    Endpoint: ``GET /api/v2/{mercado}/Titulos/{simbolo}/Cotizacion/seriehistorica/{desde}/{hasta}/{ajustada}``.

    Phase 8 D-03 / RELY-03: ``idempotent=True`` — historical data retrieval is GET.
    """
    del state
    return RequestSpec(
        method="GET",
        path=(
            f"/api/v2/{mercado}/Titulos/{simbolo}/Cotizacion/seriehistorica/"
            f"{desde:%Y-%m-%d}/{hasta:%Y-%m-%d}/{ajustada}"
        ),
        idempotent=True,
        endpoint_name="get_historical_quotes",
    )


def build_get_instruments_request(
    state: _ClientState,
    pais: str = "argentina",
) -> RequestSpec:
    """Pure: build spec for ``GET /api/v2/{pais}/Titulos/Cotizacion/Instrumentos``.

    Phase 8 D-03 / RELY-03: ``idempotent=True`` — GET instrument listing.
    """
    del state
    return RequestSpec(
        method="GET",
        path=f"/api/v2/{pais}/Titulos/Cotizacion/Instrumentos",
        idempotent=True,
        endpoint_name="get_instruments",
    )


def build_get_instruments_by_type_request(
    state: _ClientState,
    instrument_type: str,
    *,
    pais: str = "argentina",
) -> RequestSpec:
    """Pure: build spec for ``GET /api/v2/Cotizaciones/{instrument_type}/{pais}/Todos``.

    Phase 8 D-03 / RELY-03: ``idempotent=True`` — GET instrument-by-type listing.
    """
    del state
    return RequestSpec(
        method="GET",
        path=f"/api/v2/Cotizaciones/{instrument_type}/{pais}/Todos",
        idempotent=True,
        endpoint_name="get_instruments_by_type",
    )


# ----------------------------------------------------------------------
# Endpoint parsers
# ----------------------------------------------------------------------


@_decode._response_parser
def parse_get_quote_response(resp: httpx.Response) -> Cotizacion:
    """Pure: parse cotización response → :class:`~iol_client.models.Cotizacion`.

    Plan 30-01 (TYP-01): the wire dict becomes a typed model here, so the whole
    ``get_quote`` surface — method and shim, sync and async — is attribute
    access verified by mypy. ``@_response_parser`` makes this frame the owner
    of the response's :class:`~iol_client._decode.DecodeScope`, which is what
    keeps one divergence per field per HTTP response instead of one per model.
    """
    resp.read()
    raise_for_response(resp)
    return Cotizacion.from_api(resp.json())


@_decode._response_parser
def _parse_list_or_raise(resp: httpx.Response, model_cls: type[Any]) -> list[Any]:
    """Shared body for every parser whose wire shape is a **top-level list**.

    Owns the response's :class:`~iol_client._decode.DecodeScope` (lock 6), so a
    list of N rows emits at most one divergence record per field instead of N.
    The decorator lives **here**; the one-line parsers that delegate stay
    undecorated, and nesting would be safe anyway (the scope retires once, when
    the outermost decorated frame returns).

    T-30-06 / D-06 / ASVS V5: a body that is not a list **raises**. It never
    degrades to ``[]`` — silent degradation masks a changed or compromised
    upstream, which is the exact regression this milestone exists to remove.

    Three deliberate departures from the higyrus original this was copied from:
    iol has no ``_consume_and_check``, so the ``resp.read()`` +
    ``raise_for_response`` pair its own parsers already use is what runs here
    (copying higyrus' helper would smuggle in 204/empty-body tolerance iol does
    not have today — a behavior change out of this plan's scope);
    :class:`~iol_client.exceptions.IOLAPIError` takes **two positionals**, not
    higyrus' error-list signature; and ``status_code=0`` marks a shape error
    rather than an HTTP one — the transport succeeded, the payload did not.
    """
    resp.read()
    raise_for_response(resp)
    raw = resp.json()
    if not isinstance(raw, list):
        raise IOLAPIError(0, f"shape mismatch: expected list, got {type(raw).__name__}")
    return [model_cls.from_api(item) for item in raw]


def parse_get_historical_quotes_response(resp: httpx.Response) -> list[Cotizacion]:
    """Pure: parse seriehistorica response → ``list[Cotizacion]``.

    Every row carries the same 20 keys as ``get_quote`` and differs only in
    which arrive ``null`` (D-01), so the same model covers both. The annotated
    local is load-bearing: the helper returns a generic list and this is what
    narrows it for mypy strict.
    """
    result: list[Cotizacion] = _parse_list_or_raise(resp, Cotizacion)
    return result


def parse_get_instruments_response(resp: httpx.Response) -> list[Instrumento]:
    """Pure: parse instruments listing response → ``list[Instrumento]``.

    Phase 6 typed this return as ``Any`` on the premise that "the upstream
    payload shape varies". The 2026-06-06 capture
    (``.planning/verification/schemas/iol-client/get-instruments.json``) settles
    it: the wire is a **top-level list** of two-key objects. It is not the
    single-key envelope 16 test mocks were asserting — those mocks were
    validating a world the endpoint does not return, and Plan 30-03 corrected
    them against the capture.

    D-06 / T-30-08 / ASVS V5: the guard inside :func:`_parse_list_or_raise`
    **raises** on any other shape. It does not degrade to ``[]`` and it does
    **not** get a dict-or-list tolerance to accommodate the old mocks — either
    would reintroduce the silent-empty bug this milestone exists to remove, and
    would mask a changed or compromised upstream. An empty list still parses
    fine: the guard discriminates shape, not cardinality.

    The annotated local is load-bearing — the helper returns a generic list and
    this is what narrows it for mypy strict.
    """
    result: list[Instrumento] = _parse_list_or_raise(resp, Instrumento)
    return result


@_decode._response_parser
def parse_get_instruments_by_type_response(resp: httpx.Response) -> list[Titulo]:
    """Pure: parse instruments-by-type response → ``list[Titulo]``.

    Keeps its own body rather than delegating to :func:`_parse_list_or_raise`,
    because the top-level wire shape here is a **dict envelope**, not a list.
    The ``titulos`` unwrap is a raw-dict step that runs **before** any model is
    built: the envelope is transport shape, not domain shape, and is therefore
    never modelled (D-06).

    CR-02 / D-06 / ASVS V5 — **two** shape guards, for the two levels this wire
    shape has. The envelope guard rejects a body that is not a dict (a top-level
    list used to reach ``.get`` and raise a bare ``AttributeError``, escaping the
    :class:`~iol_client.exceptions.IOLClientError` hierarchy every documented
    caller catches). The value guard rejects a ``titulos`` that is not a list (a
    string or a dict used to be *iterated*, manufacturing one all-default
    :class:`~iol_client.models.Titulo` per character or per key — synthetic
    financial rows indistinguishable from real instruments). Both raise
    :class:`~iol_client.exceptions.IOLAPIError` with ``status_code=0``, the same
    convention :func:`_parse_list_or_raise` established: the transport
    succeeded, the payload did not. The message carries the received **type
    name** only — never a wire value (T-30-05-04).

    The two behaviors this function now distinguishes, stated together because
    they look adjacent and are not:

    - **Missing key yields ``[]``.** The body *is* the expected dict, it just has
      no rows. That is the pre-existing behavior and D-06 preserves it on
      purpose; the ``.get("titulos", [])`` default runs *before* the value guard,
      so this path never raises.
    - **Wrong-typed value raises.** The body does not have the expected shape at
      all. Degrading it silently — to ``[]`` or, worse, to fabricated rows —
      would mask a changed or compromised upstream, which is the exact
      regression this milestone exists to remove.

    The guards discriminate **shape, not cardinality**: ``{"titulos": []}`` is a
    legitimate response and parses to ``[]`` without raising.
    """
    resp.read()
    raise_for_response(resp)
    raw = resp.json()
    if not isinstance(raw, dict):
        raise IOLAPIError(0, f"shape mismatch: expected dict envelope, got {type(raw).__name__}")
    titulos = raw.get("titulos", [])
    if not isinstance(titulos, list):
        raise IOLAPIError(
            0, f"shape mismatch: 'titulos' expected list, got {type(titulos).__name__}"
        )
    return [Titulo.from_api(fila) for fila in titulos]
