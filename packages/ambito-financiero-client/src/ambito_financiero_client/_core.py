"""Pure builders and parsers for the ambito-financiero-client REST client.

Phase 7 REFAC-03 + D-01 (per-package ``RequestSpec``) + D-04 (``raise_for_response``
movido aquí con alias re-export en ``client.py`` / ``aio.py``). Plan 7-02 (canary):
ámbito es el paquete más simple (sin auth, sin token refresh, sin envelope), por lo
que sirve para validar mecánicamente el patrón antes de iol/higyrus/matriz.

**Privacidad:** este módulo es PRIVADO — sólo ``client.py`` y ``aio.py`` dentro de
``ambito_financiero_client`` deben importarlo. La invariante "``_core.py`` NO importa
``client.py`` ni ``aio.py``" es enforzada por el contract ``import-linter``
configurado en ``pyproject.toml`` ``[tool.importlinter]`` (Plan 7-01).

**Contrato:** las funciones son puras — state in → ``RequestSpec`` out (builders) o
``httpx.Response`` in → typed result out (parsers). No I/O. No httpx.Client /
httpx.AsyncClient. Los parsers consumen el body explícitamente vía ``resp.read()``
ANTES de ``raise_for_response(resp)`` (D-06: body-consume-then-raise — preventivo
contra el resource leak HTTP/2 documentado en CR-03 para matriz).

Example::

    from ambito_financiero_client import _core
    import datetime as dt

    spec = _core.build_get_dollar_banco_nacion_request(state, dt.date(2026, 4, 7))
    resp = client._request(spec)
    precio = _core.parse_get_dollar_banco_nacion_response(resp)
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any

import httpx

from ambito_financiero_client._parsing import parse_ar_decimal
from ambito_financiero_client._state import _ClientState
from ambito_financiero_client.exceptions import (
    AmbitoFinancieroAPIError,
    AmbitoFinancieroAuthError,
    AmbitoFinancieroNoDataError,
    AmbitoFinancieroRateLimitError,
)

__all__ = [
    "RequestSpec",
    "build_get_dollar_banco_nacion_request",
    "parse_get_dollar_banco_nacion_response",
    "raise_for_response",
]


# ---------------------------------------------------------------------------
# RequestSpec (D-01 — per-package shape; ámbito minimal, no auth, no body)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RequestSpec:
    """Pure description of an HTTP request — no transport coupling.

    Per-package shape D-01: ámbito minimal — sin ``auth_basic`` (no auth),
    sin ``data``/``json_body`` (no body), sin ``url_pre_encoded`` (no
    URL-encoding quirks). Sólo ``method`` + ``path`` requeridos; ``params``
    y ``headers`` opcionales.
    """

    method: str
    path: str
    params: dict[str, Any] | None = None
    headers: dict[str, str] | None = None


# ---------------------------------------------------------------------------
# Stateless helpers (D-04 — moved from client.py; alias preserved there)
# ---------------------------------------------------------------------------


def raise_for_response(resp: httpx.Response) -> None:
    """Map an ``httpx.Response`` status to a typed Ámbito exception.

    Behaviour copied verbatim from Phase 6 ``client._raise_for_response``
    (D-04): 401/403 → :class:`AmbitoFinancieroAuthError`,
    429 → :class:`AmbitoFinancieroRateLimitError`,
    any other error status → :class:`AmbitoFinancieroAPIError`.
    """
    if resp.status_code in (401, 403):
        raise AmbitoFinancieroAuthError(resp.status_code, resp.text)
    if resp.status_code == 429:
        raise AmbitoFinancieroRateLimitError(resp.status_code, resp.text)
    if resp.is_error:
        raise AmbitoFinancieroAPIError(resp.status_code, resp.text)


# ---------------------------------------------------------------------------
# Endpoint builders
# ---------------------------------------------------------------------------


def build_get_dollar_banco_nacion_request(state: _ClientState, date: dt.date) -> RequestSpec:
    """Build the spec for ``GET /dolarnacion/historico-general/<date>/<date>``.

    The endpoint expects the same date on both segments of the path
    (``from``/``to``) to retrieve a single day's cotización.
    """
    # state is unused for this endpoint (no auth, no per-instance headers in
    # the URL), but the signature matches the canon builder shape
    # ``build_X_request(state, ...)`` so the transport shell calls it the
    # same way as all the auth-bearing packages.
    _ = state  # kept for signature uniformity per Phase 7 D-01.
    formatted = date.strftime("%Y-%m-%d")
    return RequestSpec(
        method="GET",
        path=f"/dolarnacion/historico-general/{formatted}/{formatted}",
    )


# ---------------------------------------------------------------------------
# Endpoint parsers
# ---------------------------------------------------------------------------


def parse_get_dollar_banco_nacion_response(resp: httpx.Response) -> float:
    """Decode the Banco Nación historic response into a single ``venta`` float.

    D-06 (body-consume-then-raise): ``resp.read()`` runs FIRST so the body is
    buffered before we hand off to ``raise_for_response``. This is the
    canonical Phase 7 pattern; ámbito uses ``httpx.Client`` (not HTTP/2) so
    the resource leak is theoretical here, but we apply it uniformly for
    cross-package consistency with matriz (CR-03).

    Raises :class:`AmbitoFinancieroNoDataError` when the payload contains
    only the header row (no cotización for the requested date — fin de
    semana, feriado o fecha futura).
    """
    resp.read()
    raise_for_response(resp)
    rows: list[list[str]] = resp.json()
    if len(rows) < 2:
        # Note: the path is not available to the parser; surface the parsed
        # date via the body's header row when present so the message stays
        # useful. Caller knows the date and can re-raise with more context
        # if needed.
        raise AmbitoFinancieroNoDataError("Sin cotización del dólar Banco Nación")
    _, _, venta = rows[1]
    return parse_ar_decimal(venta)
