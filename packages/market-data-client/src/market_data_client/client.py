"""Cliente HTTP sincrónico para la API de market data (primary-extractor).

API basada en clase (Phase 20+)::

    from market_data_client import Client

    with Client() as client:
        health = client.get_health()

API a nivel módulo (delegación al default Client)::

    import market_data_client

    health = market_data_client.get_health()

Este paquete usa Auth0 con el grant ``client_credentials`` (machine-to-machine):
un ``POST`` al ``auth0_token_url`` ABSOLUTO con
``grant_type=client_credentials&client_id=...&client_secret=...&audience=...``
devuelve ``{"access_token", "expires_in"}``. El cliente cachea el
``access_token`` y lo refresca re-corriendo el mismo grant antes del
vencimiento — re-autenticar ES el refresh, sin token de rotación (D-05).

Variables de entorno (cargadas con ``python-dotenv``):

- ``MARKET_DATA_CLIENT_ID`` (requerido)
- ``MARKET_DATA_CLIENT_SECRET`` (requerido)
- ``MARKET_DATA_AUDIENCE`` (requerido)
- ``MARKET_DATA_AUTH0_TOKEN_URL`` (requerido — URL absoluta del token endpoint)
- ``MARKET_DATA_BASE_URL`` (opcional, default
  ``https://market-data-develop.bbsa.com.ar/api``).

El helper ``_raise_for_response`` es un alias module-level
(``= _core.raise_for_response`` — D-04) que preserva la identidad B8
(``aio._raise_for_response is client._raise_for_response is
_core.raise_for_response``) sin duplicar la lógica de mapeo de errores. La
auth-flow + dispatch de endpoints puros viven en ``market_data_client._core``.

Pitfall 1 (T-20-02): el grant de token despacha a la URL ABSOLUTA
``state.auth0_token_url``, NO a ``base_url + path`` — el token endpoint vive en
un host distinto (Auth0) que la API de market data.
"""

from __future__ import annotations

import uuid
from typing import Self

import httpx
from dotenv import load_dotenv

from market_data_client import _core, _transport
from market_data_client._state import _REQUEST_TIMEOUT, _ClientState

load_dotenv()


# ----------------------------------------------------------------------
# Stateless helpers (D-04 alias — sourced from _core.py to preserve B8)
# ----------------------------------------------------------------------

# D-04: preserva la identidad B8. Los tests `aio._raise_for_response is
# client._raise_for_response` quedan verdes porque AMBOS aliases referencian
# el MISMO objeto (_core.raise_for_response).
_raise_for_response = _core.raise_for_response

# Total de requests salientes cuando los retries se agotan (1 inicial + 2
# retries). ``with_options(max_retries=N)`` se difiere a Phase 21 — de ahí que
# no exista un kwarg ``max_retries`` ni una extensión ``max_attempts``.
_DEFAULT_MAX_ATTEMPTS = 3


# ----------------------------------------------------------------------
# Client class
# ----------------------------------------------------------------------


class Client:
    """Sync client for the market-data REST API.

    Per-instance state lives in ``self._state`` (a :class:`_ClientState`
    dataclass). The class owns an ``httpx.Client`` lazily and the Auth0
    ``client_credentials`` token cache.

    Lifecycle: instances are context managers (``with Client() as c: ...``)
    and must be ``close()``d to release the underlying HTTP transport.
    ``close()`` is idempotent.
    """

    __slots__ = ("_state",)

    def __init__(
        self,
        *,
        base_url: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        audience: str | None = None,
        auth0_token_url: str | None = None,
    ) -> None:
        self._state = _ClientState()
        if base_url is not None:
            self._state.base_url = base_url.rstrip("/")
        if client_id is not None:
            self._state.client_id = client_id
        if client_secret is not None:
            self._state.client_secret = client_secret
        if audience is not None:
            self._state.audience = audience
        if auth0_token_url is not None:
            self._state.auth0_token_url = auth0_token_url

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
        # Redact secret + token — never surface credentials in logs/reprs.
        secret_repr = "'***'" if self._state.client_secret else "''"
        token_repr = "'***'" if self._state.token else "None"
        return (
            f"MarketDataClient(base_url={self._state.base_url!r}, "
            f"client_id={self._state.client_id!r}, "
            f"client_secret={secret_repr}, "
            f"token={token_repr})"
        )

    # ------------------------------------------------------------------
    # HTTP transport + Auth0 client-credentials
    # ------------------------------------------------------------------

    def _ensure_http_client(self) -> httpx.Client:
        """Lazily create the per-instance ``httpx.Client``.

        Wraps ``RetryTransport`` so all requests (auth and endpoint) benefit
        from bounded retries + full-jitter backoff. The transport's mutation
        gate (D-01) honors ``request.extensions["idempotent"]`` so
        non-idempotent specs pass through with no retry loop.
        """
        http_client = self._state.http_client
        if http_client is not None:
            assert isinstance(http_client, httpx.Client)
            return http_client
        new_client = httpx.Client(
            timeout=_REQUEST_TIMEOUT,
            transport=_transport.RetryTransport(max_attempts=_DEFAULT_MAX_ATTEMPTS),
        )
        self._state.http_client = new_client
        return new_client

    def _send_auth_request(self, spec: _core.RequestSpec) -> httpx.Response:
        """Dispatch the Auth0 grant to the ABSOLUTE ``auth0_token_url``.

        Pitfall 1 (T-20-02, CRITICAL): the token grant POSTs to
        ``self._state.auth0_token_url`` (an absolute Auth0 URL on a different
        host than ``base_url``), NOT ``f"{base_url}{spec.path}"``. The grant
        request carries NO ``Authorization`` header — auth-flow establishes the
        token. ``idempotent=True`` (from the spec) makes a transient 5xx on the
        grant retry-eable through the ``RetryTransport``.
        """
        http = self._ensure_http_client()
        request_id = uuid.uuid4().hex
        req = http.build_request(
            spec.method,
            self._state.auth0_token_url,
            data=spec.data,
            headers=spec.headers,
        )
        req.extensions["idempotent"] = spec.idempotent
        req.extensions["request_id"] = request_id
        req.extensions["endpoint_name"] = spec.endpoint_name
        return http.send(req)

    def _authenticate(self) -> str:
        """Run the Auth0 ``client_credentials`` grant and cache the token.

        Builds the grant via ``_core.build_token_request``, dispatches it to the
        absolute ``auth0_token_url`` via ``_send_auth_request``, parses the
        2-tuple ``(token, expires_at)``, writes it to state, and returns the
        token. Re-running this grant IS the refresh (D-05 — no rotation token).
        """
        spec = _core.build_token_request(self._state)
        resp = self._send_auth_request(spec)
        token, expires_at = _core.parse_token_response(resp)
        self._state.token = token
        self._state.token_expires_at = expires_at
        return token

    def _ensure_token(self) -> None:
        """No-op when the cached token is fresh; else re-run the grant.

        Gates on ``_core.token_is_fresh`` (which bakes in the 60 s TTL buffer);
        a stale/absent token triggers a full ``_authenticate()`` re-grant
        (T-20-03).
        """
        if _core.token_is_fresh(self._state):
            return
        self._authenticate()
