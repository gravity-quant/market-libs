"""Driver de verificación en vivo del paquete ``iol-client`` (Phase 3).

Ejecuta 15 probes nombrados que ejercitan la superficie pública sync+async del
cliente IOL contra ``api.invertironline.com`` y producen dos artefactos
committeable: el findings markdown clasificado y 4 schema snapshots JSON
(DRIFT-01 mirror, uno por endpoint).

Probes en orden de ejecución (D-IOL-5; ``probe_auth_401`` ÚLTIMO, D-IOL-4):

1.  ``probe_login_sync``                    — ``iol_client.login()`` (IOL-01).
2.  ``probe_login_async``                   — ``await aio.login()`` (IOL-01).
3.  ``probe_get_quote_sync``                — ``iol_client.get_quote("GGAL")`` (IOL-02).
4.  ``probe_get_quote_async``               — ``await aio.get_quote("GGAL")`` (IOL-02).
5.  ``probe_get_historical_quotes_sync``    — GGAL últimos ~5 días hábiles (IOL-02).
6.  ``probe_get_historical_quotes_async``   — espejo async (IOL-02).
7.  ``probe_get_instruments_sync``          — ``pais="argentina"`` (IOL-02).
8.  ``probe_get_instruments_async``         — espejo async (IOL-02).
9.  ``probe_get_instruments_by_type_sync``  — ``instrument_type="acciones"`` + sanity 6 types (IOL-02 + IOL-04 + IOL-17).
10. ``probe_get_instruments_by_type_async`` — espejo async sample (IOL-02).
11. ``probe_parity_sync_async``             — diff estructural sync↔async (IOL-06, D-IOL-20).
12. ``probe_field_type_map``                — ``schema_of`` vs ``_ASSUMED_*`` + envelope check ``"titulos"`` (IOL-03 + IOL-04 detail + Pitfall 2).
13. ``probe_schema_snapshot``               — 4 snapshots con envelope D-21 + D-25 no-overwrite (DRIFT-01).
14. ``probe_refresh_token``                 — verifica IOL-07 in-vivo (D-IOL-11).
15. ``probe_auth_401``                      — opt-in vía ``VERIFY_IOL_BAD_CREDS=1`` (D-IOL-1/2/4).

Uso::

    uv run --package iol-client python main_iol.py

Variables de entorno (cargadas por ``iol_client`` vía ``python-dotenv``):

- ``IOL_USER`` (requerido)
- ``IOL_PASSWORD`` (requerido)
- ``IOL_BASE_URL`` (opcional, default ``https://api.invertironline.com``)
- ``VERIFY_IOL_BAD_CREDS=1`` (opcional; activa ``probe_auth_401``, D-IOL-1)

Reglas de seguridad:

- **Auth-once discipline:** el primer ``login()`` cachea el token; los downstream
  reusan vía ``_ensure_token`` sin re-disparar password grant.
- **Cascade SKIPPED (D-IOL-3):** si ``probe_login_sync`` o ``probe_login_async``
  fallan, los probes downstream emiten ``SKIPPED`` con razón ``auth failed``.
  Implementado vía flag module-level ``_auth_failed``.
- **Single-shot 401 (D-IOL-1):** ``probe_auth_401`` es opt-in, sin retry, sin
  sleep, sin loop. Cada corrida consume **1** intento contra credenciales reales.
- **Try/finally con restore (D-IOL-2):** ``probe_auth_401`` SIEMPRE restaura
  ``IOL_PASSWORD`` original aunque el call levante.
- **Redacción (D-IOL-7/22):** todos los prints pasan por ``safe_print(text,
  secrets=[IOL_USER, IOL_PASSWORD, _refresh_token])``; el regex ``_BEARER``
  cubre tokens reflejados aun sin enumerar.

Artefactos generados (NO commiteados en este plan; se commitean en 03-03 tras
checkpoint humano):

- ``.planning/verification/iol-client-findings.md`` (esqueleto + appends).
- ``.planning/verification/schemas/iol-client/get-quote.json``
- ``.planning/verification/schemas/iol-client/get-historical-quotes.json``
- ``.planning/verification/schemas/iol-client/get-instruments.json``
- ``.planning/verification/schemas/iol-client/get-instruments-by-type.json``
"""

from __future__ import annotations

import asyncio
import contextlib
import datetime as dt
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from verification import require_env, safe_print, schema_of, write_findings
from verification.findings import append_finding

import iol_client
from iol_client import IOLAPIError, IOLAuthError, aio

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

_PKG = "iol-client"
_REPO_ROOT = Path(__file__).resolve().parent
_SCHEMA_DIR = _REPO_ROOT / ".planning" / "verification" / "schemas" / _PKG
_SCHEMA_FILES: dict[str, Path] = {
    "get_quote": _SCHEMA_DIR / "get-quote.json",
    "get_historical_quotes": _SCHEMA_DIR / "get-historical-quotes.json",
    "get_instruments": _SCHEMA_DIR / "get-instruments.json",
    "get_instruments_by_type": _SCHEMA_DIR / "get-instruments-by-type.json",
}

# D-IOL-18: símbolo fijo + D-IOL-17: instrument_type baseline + tupla de los 6.
_SAMPLE_SYMBOL = "GGAL"
_SAMPLE_INSTRUMENT_TYPE: iol_client.InstrumentType = "acciones"
_ALL_INSTRUMENT_TYPES: tuple[iol_client.InstrumentType, ...] = (
    "obligacionesNegociables",
    "titulosPublicos",
    "cedears",
    "acciones",
    "letras",
    "cauciones",
)

# D-IOL-14: caller assumptions hardcoded como state público del driver.
# Listas mínimas — campos cuya presencia/tipo el caller asume; ampliar a
# discreción al observar payloads reales (Discretion).
_ASSUMED_QUOTE_FIELDS: dict[str, str] = {
    "ultimoPrecio": "float",  # IOL-04: numeric, JSON number
    "simbolo": "str",
}
_ASSUMED_HISTORICAL_FIELDS: dict[str, str] = {
    "fechaHora": "str",
    "ultimoPrecio": "float",
}
_ASSUMED_INSTRUMENTS_BY_TYPE_ENVELOPE: dict[str, str] = {
    "titulos": "list",  # IOL-04: envelope key
}

# Bounds plausibles para el sanity check de precio en probe_get_quote_sync
# (Discretion D-IOL-20 inspirado en AMB-02 D-23): si fuera de rango → finding PARAM.
_PRICE_MIN: float = 0.0
_PRICE_MAX: float = 1_000_000.0

# Path templates para el envelope D-21 de los schema snapshots.
_ENDPOINT_TEMPLATES: dict[str, str] = {
    "get_quote": "/api/v2/{mercado}/Titulos/{simbolo}/Cotizacion",
    "get_historical_quotes": (
        "/api/v2/{mercado}/Titulos/{simbolo}/Cotizacion/seriehistorica/{desde}/{hasta}/{ajustada}"
    ),
    "get_instruments": "/api/v2/{pais}/Titulos/Cotizacion/Instrumentos",
    "get_instruments_by_type": "/api/v2/Cotizaciones/{instrument_type}/{pais}/Todos",
}

# Contador module-level para asignar fids deterministicamente F-01, F-02, ...
_fid_counter: int = 0

# D-IOL-3: cascade SKIPPED — flag único compartido entre surfaces sync y async.
# Si CUALQUIER login falla, todos los downstream emiten SKIPPED.
_auth_failed: bool = False
_auth_failure_reason: str = ""


def _next_fid() -> str:
    """Devuelve el siguiente ``F-NN`` (NN zero-padded a 2 dígitos)."""
    global _fid_counter
    _fid_counter += 1
    return f"F-{_fid_counter:02d}"


# ---------------------------------------------------------------------------
# ProbeResult
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ProbeResult:
    """Resultado de un probe; agregado al summary final."""

    name: str
    status: str  # "PASS" | "FAIL" | "SKIPPED" | "FINDING"
    detail: str


# ---------------------------------------------------------------------------
# Helpers de fecha
# ---------------------------------------------------------------------------


def _last_business_day(today: dt.date) -> dt.date:
    """Lunes->viernes anterior; cualquier otro día -> el día previo."""
    d = today - dt.timedelta(days=1)
    while d.weekday() >= 5:  # 5 = sábado, 6 = domingo
        d -= dt.timedelta(days=1)
    return d


# ---------------------------------------------------------------------------
# Probes — orden D-IOL-5 (probe_auth_401 último, D-IOL-4)
# ---------------------------------------------------------------------------


def probe_login_sync() -> ProbeResult:
    """Probe 1: ``iol_client.login()`` (IOL-01).

    Setea ``_auth_failed`` global si falla con ``IOLAuthError`` (D-IOL-3 cascade).
    Cualquier otra excepción propaga como crash inesperado (D-04 lo permite).
    """
    global _auth_failed, _auth_failure_reason
    base_url = iol_client.client._base_url
    try:
        iol_client.login()
    except IOLAuthError as exc:
        _auth_failed = True
        _auth_failure_reason = f"sync login: {exc}"
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="AUTH",
            surface="sync",
            status="OPEN",
            title="login() sync falló",
            expected="login succeeds + cached token",
            actual=repr(exc),
            diff=f"status_code={exc.status_code!r}",
            base_url=base_url,
        )
        return ProbeResult("login_sync", "FINDING", f"{fid} (OPEN)")
    refresh = iol_client.client._refresh_token
    return ProbeResult(
        "login_sync",
        "PASS",
        f"_token cached, _refresh_token={'<cached>' if refresh else 'NONE'}",
    )


async def probe_login_async() -> ProbeResult:
    """Probe 2: ``await aio.login()`` (IOL-01).

    Setea el mismo ``_auth_failed`` global (Discretion: flag único compartido,
    no surface-segregated — D-IOL-3 Discretion).
    """
    global _auth_failed, _auth_failure_reason
    base_url = aio._base_url
    try:
        await aio.login()
    except IOLAuthError as exc:
        _auth_failed = True
        _auth_failure_reason = f"async login: {exc}"
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="AUTH",
            surface="async",
            status="OPEN",
            title="login() async falló",
            expected="login succeeds + cached token",
            actual=repr(exc),
            diff=f"status_code={exc.status_code!r}",
            base_url=base_url,
        )
        return ProbeResult("login_async", "FINDING", f"{fid} (OPEN)")
    refresh = aio._refresh_token
    return ProbeResult(
        "login_async",
        "PASS",
        f"_token cached, _refresh_token={'<cached>' if refresh else 'NONE'}",
    )


def probe_get_quote_sync() -> tuple[ProbeResult, dict[str, Any] | None]:
    """Probe 3: ``iol_client.get_quote(GGAL)`` (IOL-02).

    WR-03: single HTTP call por probe. WR-01: ``exc.status_code`` typed directo.
    Sanity check de plausibility del precio (Discretion D-IOL-20).
    """
    if _auth_failed:
        return (
            ProbeResult("get_quote_sync", "SKIPPED", f"auth failed: {_auth_failure_reason}"),
            None,
        )
    base_url = iol_client.client._base_url
    try:
        quote = iol_client.get_quote(_SAMPLE_SYMBOL)
    except IOLAuthError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="AUTH",
            surface="sync",
            status="OPEN",
            title="get_quote_sync recibió AuthError",
            expected="200 OK con token Bearer válido",
            actual=repr(exc),
            diff=f"status_code={exc.status_code!r}",
            base_url=base_url,
        )
        return (ProbeResult("get_quote_sync", "FINDING", f"{fid} (OPEN)"), None)
    except IOLAPIError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title="get_quote_sync recibió APIError inesperado",
            expected="200 OK",
            actual=repr(exc),
            diff=f"status_code={exc.status_code!r}",
            base_url=base_url,
        )
        return (ProbeResult("get_quote_sync", "FINDING", f"{fid} (OPEN)"), None)
    except Exception as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title=f"get_quote_sync unexpected {type(exc).__name__}",
            expected="200 OK + dict",
            actual=repr(exc),
            diff=f"type={type(exc).__name__}",
            base_url=base_url,
        )
        return (ProbeResult("get_quote_sync", "FINDING", f"{fid} (OPEN)"), None)
    # Plausibility check del precio (Discretion).
    ultimo = quote.get("ultimoPrecio")
    if isinstance(ultimo, int | float) and not (_PRICE_MIN < float(ultimo) < _PRICE_MAX):
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="PARAM",
            surface="sync",
            status="OPEN",
            title="ultimoPrecio fuera del rango plausible",
            expected=f"{_PRICE_MIN} < ultimoPrecio < {_PRICE_MAX}",
            actual=f"ultimoPrecio={ultimo!r}",
            diff="posible corrupción de magnitud (escala x100/x1000) o instrumento sin cotización",
            base_url=base_url,
        )
        return (
            ProbeResult("get_quote_sync", "FINDING", f"{fid} (OPEN)"),
            quote,
        )
    return (ProbeResult("get_quote_sync", "PASS", f"ultimoPrecio={ultimo!r}"), quote)


async def probe_get_quote_async() -> tuple[ProbeResult, dict[str, Any] | None]:
    """Probe 4: ``await aio.get_quote(GGAL)`` (IOL-02). Espejo async del probe 3."""
    if _auth_failed:
        return (
            ProbeResult("get_quote_async", "SKIPPED", f"auth failed: {_auth_failure_reason}"),
            None,
        )
    base_url = aio._base_url
    try:
        quote = await aio.get_quote(_SAMPLE_SYMBOL)
    except IOLAuthError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="AUTH",
            surface="async",
            status="OPEN",
            title="get_quote_async recibió AuthError",
            expected="200 OK con token Bearer válido",
            actual=repr(exc),
            diff=f"status_code={exc.status_code!r}",
            base_url=base_url,
        )
        return (ProbeResult("get_quote_async", "FINDING", f"{fid} (OPEN)"), None)
    except IOLAPIError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="async",
            status="OPEN",
            title="get_quote_async recibió APIError inesperado",
            expected="200 OK",
            actual=repr(exc),
            diff=f"status_code={exc.status_code!r}",
            base_url=base_url,
        )
        return (ProbeResult("get_quote_async", "FINDING", f"{fid} (OPEN)"), None)
    except Exception as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="async",
            status="OPEN",
            title=f"get_quote_async unexpected {type(exc).__name__}",
            expected="200 OK + dict",
            actual=repr(exc),
            diff=f"type={type(exc).__name__}",
            base_url=base_url,
        )
        return (ProbeResult("get_quote_async", "FINDING", f"{fid} (OPEN)"), None)
    ultimo = quote.get("ultimoPrecio")
    return (ProbeResult("get_quote_async", "PASS", f"ultimoPrecio={ultimo!r}"), quote)


def probe_get_historical_quotes_sync(
    today: dt.date,
) -> tuple[ProbeResult, list[dict[str, Any]] | None]:
    """Probe 5: serie histórica de GGAL (IOL-02, D-IOL-19)."""
    if _auth_failed:
        return (
            ProbeResult(
                "get_historical_quotes_sync",
                "SKIPPED",
                f"auth failed: {_auth_failure_reason}",
            ),
            None,
        )
    base_url = iol_client.client._base_url
    # D-IOL-19: ~5 días hábiles back desde el último hábil (7 calendario ≈ 5 hábiles).
    hasta = _last_business_day(today)
    desde = hasta - dt.timedelta(days=7)
    try:
        serie = iol_client.get_historical_quotes(_SAMPLE_SYMBOL, desde, hasta)
    except IOLAuthError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="AUTH",
            surface="sync",
            status="OPEN",
            title="get_historical_quotes_sync recibió AuthError",
            expected="200 OK con token Bearer válido",
            actual=repr(exc),
            diff=f"status_code={exc.status_code!r}",
            base_url=base_url,
        )
        return (
            ProbeResult("get_historical_quotes_sync", "FINDING", f"{fid} (OPEN)"),
            None,
        )
    except IOLAPIError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title="get_historical_quotes_sync recibió APIError inesperado",
            expected="200 OK",
            actual=repr(exc),
            diff=f"status_code={exc.status_code!r}",
            base_url=base_url,
        )
        return (
            ProbeResult("get_historical_quotes_sync", "FINDING", f"{fid} (OPEN)"),
            None,
        )
    except Exception as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title=f"get_historical_quotes_sync unexpected {type(exc).__name__}",
            expected="200 OK + list",
            actual=repr(exc),
            diff=f"type={type(exc).__name__}",
            base_url=base_url,
        )
        return (
            ProbeResult("get_historical_quotes_sync", "FINDING", f"{fid} (OPEN)"),
            None,
        )
    return (
        ProbeResult("get_historical_quotes_sync", "PASS", f"len={len(serie)}"),
        serie,
    )


async def probe_get_historical_quotes_async(
    today: dt.date,
) -> tuple[ProbeResult, list[dict[str, Any]] | None]:
    """Probe 6: serie histórica de GGAL — espejo async (IOL-02, D-IOL-19)."""
    if _auth_failed:
        return (
            ProbeResult(
                "get_historical_quotes_async",
                "SKIPPED",
                f"auth failed: {_auth_failure_reason}",
            ),
            None,
        )
    base_url = aio._base_url
    hasta = _last_business_day(today)
    desde = hasta - dt.timedelta(days=7)
    try:
        serie = await aio.get_historical_quotes(_SAMPLE_SYMBOL, desde, hasta)
    except IOLAuthError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="AUTH",
            surface="async",
            status="OPEN",
            title="get_historical_quotes_async recibió AuthError",
            expected="200 OK con token Bearer válido",
            actual=repr(exc),
            diff=f"status_code={exc.status_code!r}",
            base_url=base_url,
        )
        return (
            ProbeResult("get_historical_quotes_async", "FINDING", f"{fid} (OPEN)"),
            None,
        )
    except IOLAPIError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="async",
            status="OPEN",
            title="get_historical_quotes_async recibió APIError inesperado",
            expected="200 OK",
            actual=repr(exc),
            diff=f"status_code={exc.status_code!r}",
            base_url=base_url,
        )
        return (
            ProbeResult("get_historical_quotes_async", "FINDING", f"{fid} (OPEN)"),
            None,
        )
    except Exception as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="async",
            status="OPEN",
            title=f"get_historical_quotes_async unexpected {type(exc).__name__}",
            expected="200 OK + list",
            actual=repr(exc),
            diff=f"type={type(exc).__name__}",
            base_url=base_url,
        )
        return (
            ProbeResult("get_historical_quotes_async", "FINDING", f"{fid} (OPEN)"),
            None,
        )
    return (
        ProbeResult("get_historical_quotes_async", "PASS", f"len={len(serie)}"),
        serie,
    )


def probe_get_instruments_sync() -> tuple[ProbeResult, Any]:
    """Probe 7: ``iol_client.get_instruments("argentina")`` (IOL-02)."""
    if _auth_failed:
        return (
            ProbeResult("get_instruments_sync", "SKIPPED", f"auth failed: {_auth_failure_reason}"),
            None,
        )
    base_url = iol_client.client._base_url
    try:
        data = iol_client.get_instruments("argentina")
    except IOLAuthError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="AUTH",
            surface="sync",
            status="OPEN",
            title="get_instruments_sync recibió AuthError",
            expected="200 OK con token Bearer válido",
            actual=repr(exc),
            diff=f"status_code={exc.status_code!r}",
            base_url=base_url,
        )
        return (ProbeResult("get_instruments_sync", "FINDING", f"{fid} (OPEN)"), None)
    except IOLAPIError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title="get_instruments_sync recibió APIError inesperado",
            expected="200 OK",
            actual=repr(exc),
            diff=f"status_code={exc.status_code!r}",
            base_url=base_url,
        )
        return (ProbeResult("get_instruments_sync", "FINDING", f"{fid} (OPEN)"), None)
    except Exception as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title=f"get_instruments_sync unexpected {type(exc).__name__}",
            expected="200 OK",
            actual=repr(exc),
            diff=f"type={type(exc).__name__}",
            base_url=base_url,
        )
        return (ProbeResult("get_instruments_sync", "FINDING", f"{fid} (OPEN)"), None)
    return (
        ProbeResult("get_instruments_sync", "PASS", f"type={type(data).__name__}"),
        data,
    )


async def probe_get_instruments_async() -> tuple[ProbeResult, Any]:
    """Probe 8: ``await aio.get_instruments("argentina")`` (IOL-02). Espejo async."""
    if _auth_failed:
        return (
            ProbeResult("get_instruments_async", "SKIPPED", f"auth failed: {_auth_failure_reason}"),
            None,
        )
    base_url = aio._base_url
    try:
        data = await aio.get_instruments("argentina")
    except IOLAuthError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="AUTH",
            surface="async",
            status="OPEN",
            title="get_instruments_async recibió AuthError",
            expected="200 OK con token Bearer válido",
            actual=repr(exc),
            diff=f"status_code={exc.status_code!r}",
            base_url=base_url,
        )
        return (ProbeResult("get_instruments_async", "FINDING", f"{fid} (OPEN)"), None)
    except IOLAPIError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="async",
            status="OPEN",
            title="get_instruments_async recibió APIError inesperado",
            expected="200 OK",
            actual=repr(exc),
            diff=f"status_code={exc.status_code!r}",
            base_url=base_url,
        )
        return (ProbeResult("get_instruments_async", "FINDING", f"{fid} (OPEN)"), None)
    except Exception as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="async",
            status="OPEN",
            title=f"get_instruments_async unexpected {type(exc).__name__}",
            expected="200 OK",
            actual=repr(exc),
            diff=f"type={type(exc).__name__}",
            base_url=base_url,
        )
        return (ProbeResult("get_instruments_async", "FINDING", f"{fid} (OPEN)"), None)
    return (
        ProbeResult("get_instruments_async", "PASS", f"type={type(data).__name__}"),
        data,
    )


def probe_get_instruments_by_type_sync() -> tuple[ProbeResult, list[dict[str, Any]] | None]:
    """Probe 9: ``iol_client.get_instruments_by_type("acciones")`` + sanity 6 (IOL-02/17).

    Discretion: el sanity check de los 6 ``InstrumentType`` (type-only assertion)
    se incluye en este probe — los 6 HTTP calls extra son verificación del MISMO
    endpoint cubierto por D-IOL-17, no duplicación del concepto-probe. WR-03
    aplica al concepto (un endpoint por probe), no al número de HTTP requests.

    Pitfall 2: este probe NO captura el envelope crudo — usa el wrapper. El
    envelope check va en ``probe_field_type_map`` (probe 12) con ``_request``
    directo para evitar el silent unwrap.
    """
    if _auth_failed:
        return (
            ProbeResult(
                "get_instruments_by_type_sync",
                "SKIPPED",
                f"auth failed: {_auth_failure_reason}",
            ),
            None,
        )
    base_url = iol_client.client._base_url
    try:
        wrapper_result = iol_client.get_instruments_by_type(_SAMPLE_INSTRUMENT_TYPE)
    except IOLAuthError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="AUTH",
            surface="sync",
            status="OPEN",
            title="get_instruments_by_type_sync recibió AuthError",
            expected="200 OK con token Bearer válido",
            actual=repr(exc),
            diff=f"status_code={exc.status_code!r}",
            base_url=base_url,
        )
        return (
            ProbeResult("get_instruments_by_type_sync", "FINDING", f"{fid} (OPEN)"),
            None,
        )
    except IOLAPIError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title="get_instruments_by_type_sync recibió APIError inesperado",
            expected="200 OK",
            actual=repr(exc),
            diff=f"status_code={exc.status_code!r}",
            base_url=base_url,
        )
        return (
            ProbeResult("get_instruments_by_type_sync", "FINDING", f"{fid} (OPEN)"),
            None,
        )
    except Exception as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title=f"get_instruments_by_type_sync unexpected {type(exc).__name__}",
            expected="200 OK + list",
            actual=repr(exc),
            diff=f"type={type(exc).__name__}",
            base_url=base_url,
        )
        return (
            ProbeResult("get_instruments_by_type_sync", "FINDING", f"{fid} (OPEN)"),
            None,
        )

    # D-IOL-17: sanity check type-only de los 6 InstrumentType.
    bad_types: list[str] = []
    for itype in _ALL_INSTRUMENT_TYPES:
        try:
            titulos = iol_client.get_instruments_by_type(itype)
        except Exception as exc:
            # Sanity gate cubre cualquier excepción del cliente o transporte:
            # cualquiera de los 6 types que falle se registra para el finding.
            bad_types.append(f"{itype}: {type(exc).__name__}")
            continue
        if not (isinstance(titulos, list) and titulos and isinstance(titulos[0], dict)):
            bad_types.append(f"{itype}: shape={type(titulos).__name__}")
    if bad_types:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="SHAPE",
            surface="sync",
            status="OPEN",
            title="sanity check de InstrumentType: algún type devolvió shape inesperada",
            expected="cada InstrumentType retorna list[dict] no vacía",
            actual=f"bad_types={bad_types!r}",
            diff="shape !=list[dict] o lista vacía en algún type",
            base_url=base_url,
        )
        return (
            ProbeResult("get_instruments_by_type_sync", "FINDING", f"{fid} (OPEN)"),
            wrapper_result,
        )

    return (
        ProbeResult(
            "get_instruments_by_type_sync",
            "PASS",
            f"sample={_SAMPLE_INSTRUMENT_TYPE} len={len(wrapper_result)}; 6 types OK",
        ),
        wrapper_result,
    )


async def probe_get_instruments_by_type_async() -> tuple[ProbeResult, list[dict[str, Any]] | None]:
    """Probe 10: espejo async (solo sample principal — sanity 6 vive en sync, probe 9)."""
    if _auth_failed:
        return (
            ProbeResult(
                "get_instruments_by_type_async",
                "SKIPPED",
                f"auth failed: {_auth_failure_reason}",
            ),
            None,
        )
    base_url = aio._base_url
    try:
        wrapper_result = await aio.get_instruments_by_type(_SAMPLE_INSTRUMENT_TYPE)
    except IOLAuthError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="AUTH",
            surface="async",
            status="OPEN",
            title="get_instruments_by_type_async recibió AuthError",
            expected="200 OK con token Bearer válido",
            actual=repr(exc),
            diff=f"status_code={exc.status_code!r}",
            base_url=base_url,
        )
        return (
            ProbeResult("get_instruments_by_type_async", "FINDING", f"{fid} (OPEN)"),
            None,
        )
    except IOLAPIError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="async",
            status="OPEN",
            title="get_instruments_by_type_async recibió APIError inesperado",
            expected="200 OK",
            actual=repr(exc),
            diff=f"status_code={exc.status_code!r}",
            base_url=base_url,
        )
        return (
            ProbeResult("get_instruments_by_type_async", "FINDING", f"{fid} (OPEN)"),
            None,
        )
    except Exception as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="async",
            status="OPEN",
            title=f"get_instruments_by_type_async unexpected {type(exc).__name__}",
            expected="200 OK + list",
            actual=repr(exc),
            diff=f"type={type(exc).__name__}",
            base_url=base_url,
        )
        return (
            ProbeResult("get_instruments_by_type_async", "FINDING", f"{fid} (OPEN)"),
            None,
        )
    return (
        ProbeResult(
            "get_instruments_by_type_async",
            "PASS",
            f"sample={_SAMPLE_INSTRUMENT_TYPE} len={len(wrapper_result)}",
        ),
        wrapper_result,
    )


# ---------------------------------------------------------------------------
# Probes 11-15: parity, field_type_map, schema_snapshot, refresh_token, auth_401
# ---------------------------------------------------------------------------


def probe_parity_sync_async(
    quote_sync: dict[str, Any] | None,
    quote_async: dict[str, Any] | None,
    historical_sync: list[dict[str, Any]] | None,
    historical_async: list[dict[str, Any]] | None,
    instruments_sync: Any,
    instruments_async: Any,
    by_type_sync: list[dict[str, Any]] | None,
    by_type_async: list[dict[str, Any]] | None,
) -> ProbeResult:
    """Probe 11: paridad estructural sync↔async (IOL-06, D-IOL-20).

    Compara ``schema_of(sync) == schema_of(async)`` por endpoint; NO compara
    valores (precios pueden cambiar entre dos calls).
    """
    if _auth_failed:
        return ProbeResult("parity_sync_async", "SKIPPED", f"auth failed: {_auth_failure_reason}")
    base_url = iol_client.client._base_url
    pairs: list[tuple[str, Any, Any]] = [
        ("get_quote", quote_sync, quote_async),
        ("get_historical_quotes", historical_sync, historical_async),
        ("get_instruments", instruments_sync, instruments_async),
        ("get_instruments_by_type", by_type_sync, by_type_async),
    ]
    drift_fids: list[str] = []
    skipped: list[str] = []
    for endpoint, sync_data, async_data in pairs:
        if sync_data is None or async_data is None:
            skipped.append(endpoint)
            continue
        schema_sync = schema_of(sync_data)
        schema_async = schema_of(async_data)
        if schema_sync == schema_async:
            continue
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="SYNC-ASYNC-DRIFT",
            surface="both",
            status="OPEN",
            title=f"sync y async devolvieron schema distinto en {endpoint}",
            expected=json.dumps(schema_sync, ensure_ascii=False),
            actual=json.dumps(schema_async, ensure_ascii=False),
            diff=f"schema_of(sync) != schema_of(async) en endpoint={endpoint}",
            base_url=base_url,
        )
        drift_fids.append(fid)
    if drift_fids:
        return ProbeResult(
            "parity_sync_async",
            "FINDING",
            f"{', '.join(drift_fids)} (OPEN); skipped={skipped!r}",
        )
    if len(skipped) == len(pairs):
        return ProbeResult("parity_sync_async", "SKIPPED", "(todos los pares None)")
    return ProbeResult(
        "parity_sync_async",
        "PASS",
        f"4 endpoints, drift=0, skipped={len(skipped)}",
    )


def probe_field_type_map(
    quote: dict[str, Any] | None,
    historical: list[dict[str, Any]] | None,
    instruments_by_type_envelope: dict[str, Any] | None,
) -> tuple[ProbeResult, dict[str, Any] | None]:
    """Probe 12: field→type map vs ``_ASSUMED_*`` (IOL-03 + IOL-04, D-IOL-13/15).

    **Pitfall 2:** el envelope check de ``get_instruments_by_type`` requiere
    capturar el payload CRUDO con ``_request`` directo — el wrapper público
    silenciosamente devuelve ``[]`` si falta la clave ``"titulos"``, ocultando
    el drift. Por eso este probe hace una HTTP call adicional al endpoint
    by_type vía ``iol_client.client._request``; el resultado es el ÚNICO caso
    permitido de duplicación (documentado en Pitfall 2).

    Devuelve el envelope capturado además del ProbeResult, para que el probe 13
    (schema_snapshot) lo reuse sin volver a llamar.
    """
    if _auth_failed:
        return (
            ProbeResult("field_type_map", "SKIPPED", f"auth failed: {_auth_failure_reason}"),
            instruments_by_type_envelope,
        )
    base_url = iol_client.client._base_url
    finding_fids: list[str] = []
    envelope: dict[str, Any] | None = instruments_by_type_envelope

    # --- Envelope check IOL-04 (Pitfall 2): _request directo, NO el wrapper. ---
    if envelope is None:
        try:
            # ÚNICA HTTP call duplicada permitida (Pitfall 2): capturamos el
            # payload crudo del wrapper de by_type para verificar la clave
            # "titulos" sin que el wrapper la silencie.
            resp = iol_client.client._request(
                "GET",
                f"/api/v2/Cotizaciones/{_SAMPLE_INSTRUMENT_TYPE}/argentina/Todos",
            )
            envelope = resp.json()
        except Exception as exc:
            # Cualquier excepción del transporte o del cliente al pegarle al
            # endpoint by_type cuenta como ERROR-MAP — el envelope check no
            # puede continuar si _request falló.
            fid = _next_fid()
            append_finding(
                _PKG,
                fid=fid,
                class_="ERROR-MAP",
                surface="sync",
                status="OPEN",
                title="field_type_map: _request directo a by_type levantó excepción",
                expected="200 OK con dict {'titulos': [...]}",
                actual=repr(exc),
                diff=f"type={type(exc).__name__}",
                base_url=base_url,
            )
            finding_fids.append(fid)

    if isinstance(envelope, dict):
        if "titulos" not in envelope:
            fid = _next_fid()
            append_finding(
                _PKG,
                fid=fid,
                class_="SHAPE",
                surface="both",
                status="OPEN",
                title="missing envelope key 'titulos' in get_instruments_by_type",
                expected="dict con clave 'titulos' (list[dict])",
                actual=f"keys={sorted(envelope.keys())}",
                diff="client.py:254 hace data.get('titulos', []) y devuelve [] silenciosamente",
                base_url=base_url,
            )
            finding_fids.append(fid)
        else:
            titulos = envelope["titulos"]
            if not isinstance(titulos, list):
                fid = _next_fid()
                append_finding(
                    _PKG,
                    fid=fid,
                    class_="SHAPE",
                    surface="both",
                    status="OPEN",
                    title="envelope['titulos'] no es list en get_instruments_by_type",
                    expected="list[dict]",
                    actual=f"type={type(titulos).__name__}",
                    diff="envelope.titulos cambió de tipo respecto al contrato",
                    base_url=base_url,
                )
                finding_fids.append(fid)
    elif envelope is not None:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="SHAPE",
            surface="both",
            status="OPEN",
            title="get_instruments_by_type devolvió tipo top-level no-dict",
            expected="dict con clave 'titulos'",
            actual=f"type={type(envelope).__name__}",
            diff="el envelope cambió fuera del contrato dict",
            base_url=base_url,
        )
        finding_fids.append(fid)

    # --- get_quote field→type map (D-IOL-14/15) ---
    if quote is not None:
        observed = schema_of(quote)
        if isinstance(observed, dict):
            for key, expected_type in _ASSUMED_QUOTE_FIELDS.items():
                if key not in observed:
                    fid = _next_fid()
                    append_finding(
                        _PKG,
                        fid=fid,
                        class_="SHAPE",
                        surface="both",
                        status="OPEN",
                        title=f"missing assumed key `{key}` in get_quote",
                        expected=f"clave `{key}` (tipo {expected_type}) presente en payload",
                        actual=f"keys={sorted(observed.keys())}",
                        diff=f"clave `{key}` ausente",
                        base_url=base_url,
                    )
                    finding_fids.append(fid)
                elif observed[key] != expected_type:
                    fid = _next_fid()
                    append_finding(
                        _PKG,
                        fid=fid,
                        class_="SHAPE",
                        surface="both",
                        status="OPEN",
                        title=f"type drift on `{key}` in get_quote",
                        expected=f"`{key}`: {expected_type}",
                        actual=f"`{key}`: {observed[key]}",
                        diff=f"tipo observado != asumido para `{key}`",
                        base_url=base_url,
                    )
                    finding_fids.append(fid)

    # --- get_historical_quotes field→type map (sobre el primer row) ---
    if historical is not None and len(historical) >= 1:
        observed_row = schema_of(historical[0])
        if isinstance(observed_row, dict):
            for key, expected_type in _ASSUMED_HISTORICAL_FIELDS.items():
                if key not in observed_row:
                    fid = _next_fid()
                    append_finding(
                        _PKG,
                        fid=fid,
                        class_="SHAPE",
                        surface="both",
                        status="OPEN",
                        title=f"missing assumed key `{key}` in get_historical_quotes[0]",
                        expected=f"clave `{key}` (tipo {expected_type}) presente",
                        actual=f"keys={sorted(observed_row.keys())}",
                        diff=f"clave `{key}` ausente en el primer row",
                        base_url=base_url,
                    )
                    finding_fids.append(fid)
                elif observed_row[key] != expected_type:
                    fid = _next_fid()
                    append_finding(
                        _PKG,
                        fid=fid,
                        class_="SHAPE",
                        surface="both",
                        status="OPEN",
                        title=f"type drift on `{key}` in get_historical_quotes[0]",
                        expected=f"`{key}`: {expected_type}",
                        actual=f"`{key}`: {observed_row[key]}",
                        diff=f"tipo observado != asumido para `{key}`",
                        base_url=base_url,
                    )
                    finding_fids.append(fid)

    if finding_fids:
        return (
            ProbeResult(
                "field_type_map",
                "FINDING",
                f"{', '.join(finding_fids)} (OPEN)",
            ),
            envelope if isinstance(envelope, dict) else None,
        )
    return (
        ProbeResult("field_type_map", "PASS", "3 endpoints checked, no drift"),
        envelope if isinstance(envelope, dict) else None,
    )


def _write_or_check_schema(
    func_name: str,
    endpoint_template: str,
    sample_params: dict[str, Any],
    raw_payload: Any,
    base_url: str,
) -> tuple[str, str]:
    """Helper de probe 13: D-25 no-overwrite-on-drift.

    Returns ``(status, detail)`` donde ``status`` es ``"PASS"`` o ``"FINDING"``.
    En PASS, ``detail`` describe la acción ("escrito"/"sin drift"). En FINDING,
    ``detail`` es el fid emitido.
    """
    actual_schema = schema_of(raw_payload)
    envelope = {
        "endpoint": endpoint_template,
        "client_function": func_name,
        "captured_at": dt.datetime.now(dt.UTC).isoformat(),
        "base_url": base_url,
        "sample_params": sample_params,
        "schema": actual_schema,
    }
    _SCHEMA_DIR.mkdir(parents=True, exist_ok=True)
    file_path = _SCHEMA_FILES[func_name]
    if not file_path.exists():
        file_path.write_text(
            json.dumps(envelope, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return ("PASS", f"escrito {file_path.name}")
    committed = json.loads(file_path.read_text(encoding="utf-8"))
    if committed.get("schema") == actual_schema:
        return ("PASS", f"{file_path.name} sin drift")
    fid = _next_fid()
    append_finding(
        _PKG,
        fid=fid,
        class_="SHAPE",
        surface="both",
        status="OPEN",
        title=f"Schema drift en {func_name}",
        expected=json.dumps(committed.get("schema"), ensure_ascii=False),
        actual=json.dumps(actual_schema, ensure_ascii=False),
        diff="comparar expected vs actual; NO se sobreescribe baseline (D-25)",
        base_url=base_url,
    )
    return ("FINDING", f"{fid}|{file_path.name}")


def probe_schema_snapshot(
    today: dt.date,
    quote: dict[str, Any] | None,
    historical: list[dict[str, Any]] | None,
    instruments: Any,
    by_type_envelope: dict[str, Any] | None,
) -> ProbeResult:
    """Probe 13: 4 schema snapshots con envelope D-21 + D-25 (DRIFT-01 mirror).

    Para ``get_instruments_by_type`` snapshea el envelope CRUDO (con ``titulos``),
    no el unwrapped list, para detectar drift de la envelope key.
    """
    if _auth_failed:
        return ProbeResult("schema_snapshot", "SKIPPED", f"auth failed: {_auth_failure_reason}")
    base_url = iol_client.client._base_url
    hasta = _last_business_day(today)
    desde = hasta - dt.timedelta(days=7)
    targets: list[tuple[str, Any, dict[str, Any]]] = [
        (
            "get_quote",
            quote,
            {"simbolo": _SAMPLE_SYMBOL, "mercado": "bcba", "plazo": "t2"},
        ),
        (
            "get_historical_quotes",
            historical,
            {
                "simbolo": _SAMPLE_SYMBOL,
                "mercado": "bcba",
                "desde": desde.isoformat(),
                "hasta": hasta.isoformat(),
                "ajustada": "sinAjustar",
            },
        ),
        (
            "get_instruments",
            instruments,
            {"pais": "argentina"},
        ),
        (
            "get_instruments_by_type",
            by_type_envelope,
            {"instrument_type": _SAMPLE_INSTRUMENT_TYPE, "pais": "argentina"},
        ),
    ]
    finding_fids: list[str] = []
    written: list[str] = []
    matched: list[str] = []
    skipped: list[str] = []
    for func_name, payload, sample_params in targets:
        if payload is None:
            skipped.append(func_name)
            continue
        status, detail = _write_or_check_schema(
            func_name,
            _ENDPOINT_TEMPLATES[func_name],
            sample_params,
            payload,
            base_url,
        )
        if status == "FINDING":
            fid, fname = detail.split("|", 1)
            finding_fids.append(f"{fid}/{fname}")
        elif detail.startswith("escrito"):
            written.append(func_name)
        else:
            matched.append(func_name)
    if finding_fids:
        return ProbeResult(
            "schema_snapshot",
            "FINDING",
            f"{', '.join(finding_fids)} (OPEN) — NO sobreescribe",
        )
    return ProbeResult(
        "schema_snapshot",
        "PASS",
        f"written={written!r} matched={matched!r} skipped={skipped!r}",
    )


def probe_refresh_token() -> ProbeResult:
    """Probe 14: verifica el fix IOL-07 in-vivo (D-IOL-11).

    Lee ``_refresh_token``, ``_token``, ``_token_expires_at`` antes/después de
    forzar expiry y disparar un call autenticado. El branch ``refresh inválido
    → password fallback`` NO se ejercita en vivo (mocked-only, D-IOL-11).
    """
    if _auth_failed:
        return ProbeResult("refresh_token", "SKIPPED", f"auth failed: {_auth_failure_reason}")
    base_url = iol_client.client._base_url
    refresh_before = iol_client.client._refresh_token
    if refresh_before is None:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="AUTH",
            surface="sync",
            status="OPEN",
            title="login() no capturó refresh_token del payload",
            expected="_refresh_token != None tras login() exitoso",
            actual="_refresh_token=None",
            diff="el server no devolvió refresh_token o el cliente lo descartó",
            base_url=base_url,
        )
        return ProbeResult("refresh_token", "FINDING", f"{fid} (OPEN)")
    token_before = iol_client.client._token
    # Simulación in-vivo de expiry para forzar el branch refresh.
    iol_client.client._token_expires_at = 0.0
    try:
        iol_client.get_instruments("argentina")
    except IOLAuthError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="AUTH",
            surface="sync",
            status="OPEN",
            title="refresh path no funciona en vivo: levantó AuthError",
            expected="renovación silenciosa vía refresh_token o fallback a password",
            actual=repr(exc),
            diff=f"status_code={exc.status_code!r}",
            base_url=base_url,
        )
        return ProbeResult("refresh_token", "FINDING", f"{fid} (OPEN)")
    except IOLAPIError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title="refresh path causó APIError inesperado",
            expected="200 OK tras refresh transparente",
            actual=repr(exc),
            diff=f"status_code={exc.status_code!r}",
            base_url=base_url,
        )
        return ProbeResult("refresh_token", "FINDING", f"{fid} (OPEN)")
    token_after = iol_client.client._token
    refresh_after = iol_client.client._refresh_token
    expires_at_after = iol_client.client._token_expires_at

    if refresh_after is None:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="AUTH",
            surface="sync",
            status="OPEN",
            title="refresh path borró _refresh_token (Pitfall 3 violation)",
            expected="_refresh_token preservado o rotado tras refresh path",
            actual="_refresh_token=None",
            diff="el cliente descartó refresh_token cuando el server no lo rotó",
            base_url=base_url,
        )
        return ProbeResult("refresh_token", "FINDING", f"{fid} (OPEN)")
    if expires_at_after <= time.time():
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="AUTH",
            surface="sync",
            status="OPEN",
            title="_token_expires_at no se renovó tras refresh path",
            expected=f"_token_expires_at > {time.time()}",
            actual=f"_token_expires_at={expires_at_after}",
            diff="el refresh path no actualizó el expiry",
            base_url=base_url,
        )
        return ProbeResult("refresh_token", "FINDING", f"{fid} (OPEN)")
    if token_before == token_after:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="AUTH",
            surface="sync",
            status="OPEN",
            title="_token no cambió después de forzar expiry",
            expected="_token rotado tras refresh path",
            actual="_token sin cambio (posible race o refresh no funcionó)",
            diff="token_before == token_after; investigar refresh branch",
            base_url=base_url,
        )
        return ProbeResult("refresh_token", "FINDING", f"{fid} (OPEN)")

    rotated = refresh_after != refresh_before
    return ProbeResult(
        "refresh_token",
        "PASS",
        f"refresh path verified — token rotated, _refresh_token={'rotated' if rotated else 'preserved'}",
    )


def probe_auth_401() -> ProbeResult:
    """Probe 15: 401 con credenciales inválidas (IOL-05, D-IOL-1/2/4).

    Opt-in vía ``VERIFY_IOL_BAD_CREDS=1``. Single-shot, sin retry, sin sleep.
    try/finally SIEMPRE restaura ``IOL_PASSWORD`` original.
    """
    if os.getenv("VERIFY_IOL_BAD_CREDS") != "1":
        return ProbeResult("auth_401", "SKIPPED", "(opt-in via VERIFY_IOL_BAD_CREDS=1)")
    if _auth_failed:
        return ProbeResult("auth_401", "SKIPPED", f"auth failed: {_auth_failure_reason}")

    base_url = iol_client.client._base_url
    # D-IOL-2: lee del env, no del state cacheado del cliente (podría haberse
    # sobreescrito por otro probe).
    original_password = os.getenv("IOL_PASSWORD", "")
    bad_password = original_password + "_INVALID"
    try:
        iol_client.configure(password=bad_password)
        try:
            iol_client.login()  # D-IOL-1: ÚNICA llamada, sin retry/sleep/loop.
        except IOLAuthError as exc:
            # WR-01: status_code typed directo, NUNCA via fallback a args.
            status_code = exc.status_code
            if status_code == 401:
                fid = _next_fid()
                append_finding(
                    _PKG,
                    fid=fid,
                    class_="AUTH",
                    surface="sync",
                    status="EXPECTED",
                    title="credenciales inválidas reciben 401",
                    expected="401 con password=IOL_PASSWORD+_INVALID",
                    actual="401",
                    diff="ninguno; comportamiento esperado",
                    base_url=base_url,
                )
                return ProbeResult("auth_401", "FINDING", f"{fid} (EXPECTED)")
            fid = _next_fid()
            append_finding(
                _PKG,
                fid=fid,
                class_="AUTH",
                surface="sync",
                status="OPEN",
                title="credenciales inválidas recibieron status inesperado",
                expected="401",
                actual=f"status_code={status_code!r}",
                diff=f"AuthError con status_code={status_code!r}",
                base_url=base_url,
            )
            return ProbeResult("auth_401", "FINDING", f"{fid} (OPEN)")
        except Exception as exc:
            fid = _next_fid()
            append_finding(
                _PKG,
                fid=fid,
                class_="AUTH",
                surface="sync",
                status="OPEN",
                title="credenciales inválidas produjeron error inesperado",
                expected="401 (IOLAuthError)",
                actual=repr(exc),
                diff=f"type={type(exc).__name__}",
                base_url=base_url,
            )
            return ProbeResult("auth_401", "FINDING", f"{fid} (OPEN)")
        # Sin excepción → defensa relajada (200 OK con bad creds).
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="AUTH",
            surface="sync",
            status="OPEN",
            title="credenciales inválidas NO recibieron 401",
            expected="401 con password=IOL_PASSWORD+_INVALID",
            actual="200 OK (defensa relajada)",
            diff="el server aceptó un password inválido",
            base_url=base_url,
        )
        return ProbeResult("auth_401", "FINDING", f"{fid} (OPEN)")
    finally:
        # D-IOL-2: SIEMPRE restaurar el password original, aun ante excepción.
        iol_client.configure(password=original_password)


# ---------------------------------------------------------------------------
# Async wrapper — un único asyncio.run (D-IOL-6, IN-03)
# ---------------------------------------------------------------------------


async def _async_main(
    today: dt.date,
) -> tuple[
    ProbeResult,
    ProbeResult,
    dict[str, Any] | None,
    ProbeResult,
    list[dict[str, Any]] | None,
    ProbeResult,
    Any,
    ProbeResult,
    list[dict[str, Any]] | None,
]:
    """Compone los probes async (2/4/6/8/10) y cierra el AsyncClient.

    D-IOL-6 + IN-03: un único event loop; ``aclose`` envuelto en
    ``contextlib.suppress(Exception)`` para honrar D-04.
    """
    try:
        result_login_async = await probe_login_async()
        result_quote_async, quote_async = await probe_get_quote_async()
        result_historical_async, historical_async = await probe_get_historical_quotes_async(today)
        result_instruments_async, instruments_async = await probe_get_instruments_async()
        result_by_type_async, by_type_async = await probe_get_instruments_by_type_async()
    finally:
        with contextlib.suppress(Exception):
            await aio.aclose()
    return (
        result_login_async,
        result_quote_async,
        quote_async,
        result_historical_async,
        historical_async,
        result_instruments_async,
        instruments_async,
        result_by_type_async,
        by_type_async,
    )


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------


def main() -> None:
    """Orquesta los 15 probes en el orden D-IOL-5 y emite el summary final."""
    if not require_env(_PKG, ["IOL_USER", "IOL_PASSWORD"]):
        # HARN-01: exit limpio sin interrumpir (require_env ya imprimió SKIPPED).
        return

    today = dt.date.today()

    # D-03 mirror: idempotente — no-op si el archivo ya existe.
    write_findings(_PKG)

    results: list[ProbeResult] = []

    # Probe 1: login sync (puede setear _auth_failed).
    result_login_sync = probe_login_sync()
    results.append(result_login_sync)

    # Probes 2 + 4 + 6 + 8 + 10: batch async en un único asyncio.run (D-IOL-6).
    (
        result_login_async,
        result_quote_async,
        quote_async,
        result_historical_async,
        historical_async,
        result_instruments_async,
        instruments_async,
        result_by_type_async,
        by_type_async,
    ) = asyncio.run(_async_main(today))

    # Probes 3 / 5 / 7 / 9 (sync); intercalamos con los async ya capturados
    # respetando el orden D-IOL-5 (sync N seguido del async N+1).
    result_quote_sync, quote_sync = probe_get_quote_sync()
    results.append(result_login_async)
    results.append(result_quote_sync)
    results.append(result_quote_async)

    result_historical_sync, historical_sync = probe_get_historical_quotes_sync(today)
    results.append(result_historical_sync)
    results.append(result_historical_async)

    result_instruments_sync, instruments_sync = probe_get_instruments_sync()
    results.append(result_instruments_sync)
    results.append(result_instruments_async)

    result_by_type_sync, by_type_sync = probe_get_instruments_by_type_sync()
    results.append(result_by_type_sync)
    results.append(result_by_type_async)

    # Probe 11: paridad estructural sync↔async.
    results.append(
        probe_parity_sync_async(
            quote_sync,
            quote_async,
            historical_sync,
            historical_async,
            instruments_sync,
            instruments_async,
            by_type_sync,
            by_type_async,
        )
    )

    # Probe 12: field→type map + envelope check (captura by_type_envelope).
    result_field_type_map, by_type_envelope = probe_field_type_map(
        quote_sync, historical_sync, None
    )
    results.append(result_field_type_map)

    # Probe 13: schema snapshots (reusa by_type_envelope si fue capturado).
    results.append(
        probe_schema_snapshot(
            today,
            quote_sync,
            historical_sync,
            instruments_sync,
            by_type_envelope,
        )
    )

    # Probe 14: refresh_token in-vivo.
    results.append(probe_refresh_token())

    # Probe 15: auth_401 ÚLTIMO (D-IOL-4) — opt-in, single-shot.
    results.append(probe_auth_401())

    # safe_print con secrets dinámicos (D-IOL-7/22): el _refresh_token capturado
    # por login() se evalúa AHORA, después de los probes, para que esté presente
    # como secret en la salida stdout.
    secrets = [
        v
        for v in (
            os.getenv("IOL_USER"),
            os.getenv("IOL_PASSWORD"),
            iol_client.client._refresh_token,
        )
        if v and len(v) >= 4
    ]
    for r in results:
        safe_print(f"PROBE {r.name}: {r.status} {r.detail}".rstrip(), secrets=secrets)

    # Summary final verbatim D-02.
    n_pass = sum(1 for r in results if r.status == "PASS")
    n_fail = sum(1 for r in results if r.status == "FAIL")
    n_skip = sum(1 for r in results if r.status == "SKIPPED")
    n_find = sum(1 for r in results if r.status == "FINDING")
    safe_print(
        f"SUMMARY: PASS={n_pass} FAIL={n_fail} SKIPPED={n_skip} FINDING={n_find}",
        secrets=secrets,
    )


if __name__ == "__main__":
    main()
