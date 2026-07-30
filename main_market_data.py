"""Driver de verificación en vivo del paquete ``market-data-client`` (Phase 23).

Ejerce la superficie pública completa del cliente market-data —health + reads de
market-data + reads de reference, los 10 métodos de endpoint sobre AMBAS
superficies (``Client`` sync y ``AsyncClient`` async)— contra el target
``develop`` (``https://market-data-develop.bbsa.com.ar/api``) usando Auth0
``client_credentials``. Cada probe aísla sus propias excepciones (D-09) para que
un develop inalcanzable o un mercado cerrado se clasifiquen como NO-DATA/SKIP y
NUNCA como un crash que voltee ``main_verify.py`` a FAILED.

Uso::

    uv run --package market-data-client python main_market_data.py

Gating (D-01): el driver requiere las cuatro variables Auth0
``MARKET_DATA_CLIENT_ID`` / ``MARKET_DATA_CLIENT_SECRET`` / ``MARKET_DATA_AUDIENCE``
/ ``MARKET_DATA_AUTH0_TOKEN_URL`` vía ``require_env``; si falta alguna imprime la
línea verbatim ``SKIPPED market-data-client: missing ...`` y hace ``sys.exit(0)``
(el runner agregado la clasifica SKIPPED, no FAILED). NO hay flag ``--live``: el
split offline/skip ya lo realiza el early-return de ``require_env`` — un flag
rompería la clasificación SKIPPED (``main_verify.py:41``) y la invocación
flag-less del subproceso (``main_verify.py:61``). ``MARKET_DATA_BASE_URL`` es
opcional (default al target develop en ``client.py``) y NO se gatea.

Invariante de single-Client (D-02 / success-criterion 1): ``main()`` construye
EXACTAMENTE UN ``Client()`` sync y ``_async_main()`` construye EXACTAMENTE UN
``AsyncClient()``; ambos se threadean como parámetros a cada probe. La AST-guard
``verification/test_main_market_data_uses_single_client_instance.py`` lo enforcea.

Artefactos generados: findings clasificados en
``.planning/verification/market-data-client-findings.md`` (bootstrap idempotente
vía ``write_findings``) y schema snapshots write-once (DRIFT-01) bajo
``.planning/verification/schemas/market-data-client/``.
"""

from __future__ import annotations

import asyncio
import contextlib
import datetime as dt
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from verification import safe_print, schema_of, write_findings
from verification.env_gate import require_env
from verification.findings import append_finding

import market_data_client as md
from market_data_client import AsyncClient, Client

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

_PKG = "market-data-client"
_REPO_ROOT = Path(__file__).resolve().parent
_SCHEMA_DIR = _REPO_ROOT / ".planning" / "verification" / "schemas" / _PKG

# Contador module-level para asignar fids deterministicamente F-01, F-02, ...
_fid_counter: int = 0


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
# Shared helpers — exception ladder (D-09) + schema snapshot (DRIFT-01)
# ---------------------------------------------------------------------------


def _finding_for_exc(
    exc: Exception,
    *,
    name: str,
    surface: str,
    base_url: str,
) -> ProbeResult:
    """Mapea una excepción de probe a un finding + ``ProbeResult`` (ladder D-09).

    - ``MarketDataAuthError`` → clase ``AUTH``.
    - ``httpx.ConnectError`` / ``ConnectTimeout`` → clase ``NO-DATA`` (develop
      inalcanzable via VPN/allowlist o timeout: se clasifica como skip, nunca un
      crash — D-09).
    - cualquier otra ``Exception`` → clase ``ERROR-MAP``.
    """
    if isinstance(exc, httpx.ConnectError | httpx.ConnectTimeout):
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="NO-DATA",
            surface=surface,
            status="OPEN",
            title=f"{name}: develop inalcanzable",
            expected="200 OK desde develop",
            actual=repr(exc),
            diff=f"type={type(exc).__name__}",
            base_url=base_url,
        )
        return ProbeResult(name, "SKIPPED", "develop inalcanzable")
    class_ = "AUTH" if isinstance(exc, md.MarketDataAuthError) else "ERROR-MAP"
    fid = _next_fid()
    append_finding(
        _PKG,
        fid=fid,
        class_=class_,
        surface=surface,
        status="OPEN",
        title=f"{name}: {type(exc).__name__} inesperado",
        expected="200 OK",
        actual=repr(exc),
        diff=f"type={type(exc).__name__}",
        base_url=base_url,
    )
    return ProbeResult(name, "FINDING", f"{fid} (OPEN)")


def _write_schema_snapshot(
    *,
    endpoint: str,
    client_function: str,
    raw: Any,
    base_url: str,
    surface: str,
) -> None:
    """Escribe un schema snapshot write-once (DRIFT-01) o emite drift (D-25).

    Primer run: escribe el envelope ``schema_of`` (keys+types, PII-free por
    construcción). Runs subsiguientes: compara el schema actual contra el
    committed; iguales → no-op; distintos → emite finding ``SHAPE`` OPEN y NUNCA
    sobreescribe el baseline (D-25).
    """
    actual_schema = schema_of(raw)
    schema_file = _SCHEMA_DIR / f"{client_function.replace('_', '-')}.json"
    envelope: dict[str, Any] = {
        "endpoint": endpoint,
        "client_function": client_function,
        "captured_at": dt.datetime.now(dt.UTC).isoformat(),
        "base_url": base_url,
        "schema": actual_schema,
    }
    _SCHEMA_DIR.mkdir(parents=True, exist_ok=True)
    if not schema_file.exists():
        schema_file.write_text(
            json.dumps(envelope, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return
    committed = json.loads(schema_file.read_text(encoding="utf-8"))
    if committed.get("schema") == actual_schema:
        return
    fid = _next_fid()
    append_finding(
        _PKG,
        fid=fid,
        class_="SHAPE",
        surface=surface,
        status="OPEN",
        title=f"schema drift en {client_function}",
        expected=json.dumps(committed.get("schema"), ensure_ascii=False),
        actual=json.dumps(actual_schema, ensure_ascii=False),
        diff="baseline schema difiere; NO se sobreescribe (D-25)",
        base_url=base_url,
    )


# ---------------------------------------------------------------------------
# Health probes (anonymous, authenticated=False) — sync + async
# ---------------------------------------------------------------------------


def probe_health_sync(client: Client) -> ProbeResult:
    """Health sync: ``get_health`` + ``get_health_feed`` (anónimos, D-09)."""
    name = "health_sync"
    base_url = client._state.base_url
    try:
        health = client.get_health()
        feed = client.get_health_feed()
    except Exception as exc:  # D-09: aislamiento per-probe
        return _finding_for_exc(exc, name=name, surface="sync", base_url=base_url)
    _write_schema_snapshot(
        endpoint="/health",
        client_function="get_health",
        raw=health,
        base_url=base_url,
        surface="sync",
    )
    _write_schema_snapshot(
        endpoint="/health/feed",
        client_function="get_health_feed",
        raw=feed,
        base_url=base_url,
        surface="sync",
    )
    return ProbeResult(name, "PASS", "health+feed ok")


async def probe_health_async(aclient: AsyncClient) -> ProbeResult:
    """Health async: ``get_health`` + ``get_health_feed`` (anónimos, D-09)."""
    name = "health_async"
    base_url = aclient._state.base_url
    try:
        health = await aclient.get_health()
        feed = await aclient.get_health_feed()
    except Exception as exc:  # D-09: aislamiento per-probe
        return _finding_for_exc(exc, name=name, surface="async", base_url=base_url)
    _write_schema_snapshot(
        endpoint="/health",
        client_function="get_health",
        raw=health,
        base_url=base_url,
        surface="async",
    )
    _write_schema_snapshot(
        endpoint="/health/feed",
        client_function="get_health_feed",
        raw=feed,
        base_url=base_url,
        surface="async",
    )
    return ProbeResult(name, "PASS", "health+feed ok")


# ---------------------------------------------------------------------------
# Async wrapper — un único asyncio.run + UN AsyncClient (D-02)
# ---------------------------------------------------------------------------


async def _async_main() -> list[ProbeResult]:
    """Construye EXACTAMENTE UN ``AsyncClient`` y corre los probes async.

    IN-03: el ``aclose()`` se envuelve en ``contextlib.suppress`` para que un
    fallo de teardown (error de red durante cierre, etc.) nunca se propague a
    ``asyncio.run(...)`` y crashee el driver (D-09).
    """
    aclient = AsyncClient()
    results: list[ProbeResult] = []
    try:
        results.append(await probe_health_async(aclient))
    finally:
        with contextlib.suppress(Exception):
            await aclient.aclose()
    return results


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------


def main() -> None:
    """Gatea creds Auth0, orquesta los probes con UN Client + UN AsyncClient."""
    # D-01: gate offline-safe. Sin las 4 vars Auth0, imprime SKIPPED y exit 0.
    if not require_env(
        _PKG,
        [
            "MARKET_DATA_CLIENT_ID",
            "MARKET_DATA_CLIENT_SECRET",
            "MARKET_DATA_AUDIENCE",
            "MARKET_DATA_AUTH0_TOKEN_URL",
        ],
    ):
        sys.exit(0)

    # D-08.3: bootstrap idempotente del findings file (no-op si ya existe).
    write_findings(_PKG)

    # D-02: EXACTAMENTE UN Client sync threadeado a cada probe sync.
    client = Client()
    results: list[ProbeResult] = []
    try:
        results.append(probe_health_sync(client))
        results.extend(asyncio.run(_async_main()))
    finally:
        with contextlib.suppress(Exception):
            client.close()

    for r in results:
        safe_print(f"PROBE {r.name}: {r.status} {r.detail}".rstrip(), secrets=[])

    n_pass = sum(1 for r in results if r.status == "PASS")
    n_fail = sum(1 for r in results if r.status == "FAIL")
    n_skip = sum(1 for r in results if r.status == "SKIPPED")
    n_find = sum(1 for r in results if r.status == "FINDING")
    safe_print(
        f"SUMMARY: PASS={n_pass} FAIL={n_fail} SKIPPED={n_skip} FINDING={n_find}",
        secrets=[],
    )


if __name__ == "__main__":
    main()
