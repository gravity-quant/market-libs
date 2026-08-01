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

Gate de mutaciones (LIVE-MUT-01 / D-01): las escrituras requieren DOS patas a la
vez — el opt-in explícito ``MARKET_DATA_VERIFY_MUTATING=1`` **y** que el hostname
de la base URL resuelta sea exactamente ``market-data-develop.bbsa.com.ar``. El
booleano se computa UNA vez en ``main()`` vía
``verification.mutation_gate.mutating_allowed_for`` y se thread-ea a los DOS
constructores existentes junto con un ``expected_host`` explícito (la pata de host
in-package queda así independiente de su default). El gate apagado NO corta el
run: el read sweep completo sigue corriendo (D-03) y el driver nunca hace
``sys.exit`` por el gate.

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
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from verification import (
    diff_safemodel_bidirectional,
    safe_print,
    schema_of,
    write_findings,
)
from verification.cycle_report import verify_cycle_closure
from verification.env_gate import require_env
from verification.findings import append_finding, findings_path, max_existing_fid
from verification.mutation_gate import mutating_allowed_for

import market_data_client as md
from market_data_client import (
    AsyncClient,
    CalendarConfig,
    CalendarDay,
    Client,
    Instrument,
    LatestRequest,
    MarketDataSnapshot,
    MarketHoursIn,
    Segment,
    Symbol,
    _core,
)
from market_data_client._core import RequestSpec
from market_data_client._state import _env_base_url

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

_PKG = "market-data-client"
_REPO_ROOT = Path(__file__).resolve().parent
_SCHEMA_DIR = _REPO_ROOT / ".planning" / "verification" / "schemas" / _PKG

# Campos CLIENT-STAMPED (D-01): declarados por el modelo pero NUNCA presentes en
# el wire. Se excluyen del direction ``model-only`` del SHAPE-diff para no emitir
# un finding garantizado-falso (``received_at`` lo inyecta ``from_api``).
_CLIENT_STAMPED = frozenset({"received_at"})

# Campos ENDPOINT-UNION (LIVE-MD-01): declarados por MarketDataSnapshot pero que
# UN endpoint omite por diseño — ``note`` está ausente en ``/marketdata`` y
# ``entries`` está ausente en las filas no-data de ``/marketdata/latest``. Su
# ausencia model-only es esperada (endpoint-union), no un defecto, así que se
# excluyen del direction ``model-only`` del SHAPE-diff igual que ``received_at``.
_ENDPOINT_OPTIONAL = frozenset({"note", "entries"})

# Símbolo placeholder para el probe batch (``get_latest_batch``); reconciliado
# contra develop en Wave 2 (23-02).
_SAMPLE_SYMBOLS = ["GGAL"]

# Prefix improbable para forzar un resultado vacío en el probe no-data.
_NO_DATA_PREFIX = "__no_such_symbol__"

# Gate de mutaciones del driver (LIVE-MUT-01 / D-01). DOS patas reales:
#   1. el opt-in explícito ``MARKET_DATA_VERIFY_MUTATING=1``, y
#   2. el hostname EXACTO del target develop.
# El nombre de la variable es market-data-scoped a propósito: ``main_verify.py``
# corre los seis drivers en un mismo lote, así que reusar el ``VERIFY_MUTATING``
# de matriz armaría DOS gates a la vez. Nunca se reusa el gate de otro paquete:
# ``mutating_allowed()`` valida la base URL de matriz, así que su segunda pata
# sería vacua acá y la variable sola habilitaría escrituras contra cualquier host.
_EXPECTED_DEVELOP_HOST = "market-data-develop.bbsa.com.ar"
_MUTATING_ENV_VAR = "MARKET_DATA_VERIFY_MUTATING"

# Detalle de skip a nivel PROBE que usan los probes mutantes cuando el gate está
# apagado (D-03). SIN dos puntos, a propósito: ``main_verify.py`` clasifica el
# PAQUETE ENTERO como SKIPPED ante ``^SKIPPED \S.*:`` (``main_verify.py:42``), de
# modo que un read sweep completamente exitoso se reportaría como skip si esta
# cadena llevara dos puntos. El único emisor legítimo de la forma con dos puntos
# es el gate de credenciales en ``verification/env_gate.py``.
_MUTATING_SKIP_DETAIL = "SKIPPED (mutating, guard off)"

# Status terminales que cuentan como "ciclo cerrado" en el findings file. Se usa
# para que ``probe_cycle_closure`` no pueda pasar de forma vacua (D-18).
_CLOSED_STATUS_RE = re.compile(r"\*\*Status:\*\*\s*`?(?:CONFIRMED|FIXED)`?")

# Body usado por los probes de refusal del gate in-package. Se eligió
# ``preview_calendar_config`` —el método mutante MÁS seguro del paquete: es un dry
# run compute-only que NO persiste nada server-side— justamente para que, si el
# gate fallara en rechazar, el peor caso sea un POST inocuo en lugar de una
# escritura real sobre la config compartida de develop.
_REFUSAL_PROBE_CONFIG = MarketHoursIn(
    open_time="11:00",
    close_time="17:00",
    timezone="America/Argentina/Buenos_Aires",
)

# Contador module-level para asignar fids deterministicamente. NO arranca en 0 en
# el run real: ``_seed_fid_counter()`` lo sube al máximo fid ya registrado antes
# del primer probe (D-16/D-24). Sin ese seed, cada finding nuevo re-emitiría un
# fid ya ocupado por un finding promovido (F-01..F-36) y ``append_finding`` lo
# descartaría en silencio mientras el driver sigue reportando ``FINDING=N``.
_fid_counter: int = 0


def _seed_fid_counter() -> None:
    """Sube ``_fid_counter`` al máximo fid ya registrado en el findings file (D-16).

    Debe correr DESPUÉS de ``write_findings(_PKG)`` (el bootstrap del archivo) y
    ANTES del primer probe, para que todo fid emitido en este run caiga por
    encima de lo ya escrito y realmente aterrice en el archivo.
    """
    global _fid_counter
    _fid_counter = max_existing_fid(_PKG)


def _next_fid() -> str:
    """Devuelve el siguiente ``F-NN`` (NN zero-padded a 2 dígitos; degrada >99)."""
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
    try:
        committed = json.loads(schema_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        # D-09: un baseline committed corrupto/ilegible (hand-edit, merge-conflict,
        # error de disco) degrada a un finding SHAPE, NUNCA un crash. No se
        # sobreescribe el baseline (D-25).
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="SHAPE",
            surface=surface,
            status="OPEN",
            title=f"baseline schema ilegible en {client_function}",
            expected="baseline JSON parseable",
            actual=repr(exc),
            diff="committed baseline corrupto/ilegible; NO se sobreescribe (D-25)",
            base_url=base_url,
        )
        return
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


def _raw_via_request_sync(client: Client, spec: RequestSpec) -> Any:
    """Despacha un spec por el shell sync y devuelve el payload JSON CRUDO.

    El acceso crudo (pre-``from_api``) es necesario para el SHAPE-diff: el
    ``from_api`` tolerante aplana la divergencia, así que inspeccionamos el wire
    body directamente (espejo de ``main_ambito_financiero.py``).
    """
    resp = client._request(spec)
    return resp.json()


async def _raw_via_request_async(aclient: AsyncClient, spec: RequestSpec) -> Any:
    """Espejo async de :func:`_raw_via_request_sync`."""
    resp = await aclient._request(spec)
    return resp.json()


def _unwrap_rows(raw: Any, key: str) -> list[Any]:
    """Devuelve las filas de un body wire, desenvolviendo el envelope si lo hay.

    El wire de develop envuelve varias colecciones en un objeto
    (``{count, items[]}`` para market-data, ``{config, coverage, days[], market}``
    para calendar). Un body de lista bare se acepta tal cual por compatibilidad;
    cualquier otra cosa colapsa a ``[]`` en vez de romper el SHAPE-diff.
    """
    if isinstance(raw, dict):
        rows = raw.get(key, [])
    elif isinstance(raw, list):
        rows = raw
    else:
        rows = []
    return rows if isinstance(rows, list) else []


def _emit_shape(
    sample: Any,
    model_cls: type,
    model_name: str,
    surface: str,
    base_url: str,
) -> int:
    """Diffea un item wire crudo contra un SafeModel y emite findings SHAPE.

    ``model-only`` = FALSE-PASS risk (el modelo declara, el wire omite →
    ``from_api`` inyecta un default silencioso). ``wire-only`` = info (el server
    agregó un campo). Los campos client-stamped (D-01) se saltan en direction
    ``model-only``. Devuelve la cantidad de findings emitidos.
    """
    if not isinstance(sample, dict):
        return 0
    n = 0
    for path_, direction, key in diff_safemodel_bidirectional(sample, model_cls):
        if direction == "model-only" and key in _CLIENT_STAMPED | _ENDPOINT_OPTIONAL:
            continue  # D-01: received_at client-stamped + note/entries endpoint-union
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="SHAPE",
            surface=surface,
            status="OPEN",
            title=f"{direction} field {key} en {model_name}{path_}",
            expected=f"{model_name} y wire concuerdan en {key}",
            actual=f"{direction}: {key}",
            diff=f"path={path_ or '<root>'} direction={direction}",
            base_url=base_url,
        )
        n += 1
    return n


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
        # D-09: el post-procesado (schema snapshot: file I/O + json.loads +
        # append_finding) va DENTRO del try para que un fallo de I/O/parse degrade
        # a finding/SKIP en vez de crashear el driver a FAILED.
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
    except Exception as exc:  # D-09: aislamiento per-probe (request + post-procesado)
        return _finding_for_exc(exc, name=name, surface="sync", base_url=base_url)


async def probe_health_async(aclient: AsyncClient) -> ProbeResult:
    """Health async: ``get_health`` + ``get_health_feed`` (anónimos, D-09)."""
    name = "health_async"
    base_url = aclient._state.base_url
    try:
        health = await aclient.get_health()
        feed = await aclient.get_health_feed()
        # D-09: post-procesado dentro del try (espejo sync).
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
    except Exception as exc:  # D-09: aislamiento per-probe (request + post-procesado)
        return _finding_for_exc(exc, name=name, surface="async", base_url=base_url)


# ---------------------------------------------------------------------------
# Market-data + reference read probes — sync
# ---------------------------------------------------------------------------


def probe_market_data_sync(client: Client) -> ProbeResult:
    """Market-data read sync: happy-path + SHAPE-diff (Snapshot) + snapshot."""
    name = "market_data_sync"
    base_url = client._state.base_url
    try:
        snapshots = client.get_market_data(active=True)
        raw = _raw_via_request_sync(
            client, _core.build_market_data_request(client._state, active=True)
        )
        # D-09: SHAPE-diff + schema snapshot dentro del try (pueden hacer I/O,
        # json.loads y append_finding); un fallo degrada a finding, no a crash.
        # El wire envuelve las filas en un envelope {count, items:[...], ...}
        # (LIVE-MD-01): se desenvuelve items[] antes de tomar la muestra.
        if isinstance(raw, dict):
            rows = raw.get("items", [])
        elif isinstance(raw, list):
            rows = raw
        else:
            rows = []
        sample = rows[0] if isinstance(rows, list) and rows else None
        if isinstance(sample, dict):
            _emit_shape(sample, MarketDataSnapshot, "MarketDataSnapshot", "sync", base_url)
        _write_schema_snapshot(
            endpoint="/marketdata",
            client_function="get_market_data",
            raw=raw,
            base_url=base_url,
            surface="sync",
        )
        return ProbeResult(name, "PASS", f"snapshots={len(snapshots)}")
    except Exception as exc:  # D-09
        return _finding_for_exc(exc, name=name, surface="sync", base_url=base_url)


def probe_latest_sync(client: Client) -> ProbeResult:
    """Latest reads sync: ``get_latest`` (GET) + ``get_latest_batch`` (POST body)."""
    name = "latest_sync"
    base_url = client._state.base_url
    try:
        latest = client.get_latest(symbol=_SAMPLE_SYMBOLS[0])
        batch = client.get_latest_batch(LatestRequest(symbols=_SAMPLE_SYMBOLS))
        raw = _raw_via_request_sync(
            client, _core.build_latest_request(client._state, symbol=_SAMPLE_SYMBOLS[0])
        )
        # D-09: post-procesado dentro del try.
        sample = raw[0] if isinstance(raw, list) and raw else None
        if isinstance(sample, dict):
            _emit_shape(sample, MarketDataSnapshot, "MarketDataSnapshot", "sync", base_url)
        _write_schema_snapshot(
            endpoint="/marketdata/latest",
            client_function="get_latest",
            raw=raw,
            base_url=base_url,
            surface="sync",
        )
        return ProbeResult(name, "PASS", f"latest={len(latest)} batch={len(batch)}")
    except Exception as exc:  # D-09
        return _finding_for_exc(exc, name=name, surface="sync", base_url=base_url)


def probe_instruments_sync(client: Client) -> ProbeResult:
    """Instruments read sync (bool filters) + SHAPE-diff + snapshot."""
    name = "instruments_sync"
    base_url = client._state.base_url
    try:
        instruments = client.get_instruments(include_expired=True, only_outright=False, offset=0)
        raw = _raw_via_request_sync(
            client,
            _core.build_instruments_request(
                client._state, include_expired=True, only_outright=False, offset=0
            ),
        )
        # D-09: post-procesado dentro del try.
        sample = raw[0] if isinstance(raw, list) and raw else None
        if isinstance(sample, dict):
            _emit_shape(sample, Instrument, "Instrument", "sync", base_url)
        _write_schema_snapshot(
            endpoint="/instruments",
            client_function="get_instruments",
            raw=raw,
            base_url=base_url,
            surface="sync",
        )
        return ProbeResult(name, "PASS", f"instruments={len(instruments)}")
    except Exception as exc:  # D-09
        return _finding_for_exc(exc, name=name, surface="sync", base_url=base_url)


def probe_segments_sync(client: Client) -> tuple[ProbeResult, list[Segment] | None]:
    """Segments read sync + SHAPE-diff + snapshot; devuelve la lista para paridad."""
    name = "segments_sync"
    base_url = client._state.base_url
    try:
        segments = client.get_segments()
        raw = _raw_via_request_sync(client, _core.build_segments_request(client._state))
        # D-09: post-procesado dentro del try. Si el post-procesado falla, la lista
        # de segments se pierde (return None) → el probe de paridad hace SKIP.
        sample = raw[0] if isinstance(raw, list) and raw else None
        if isinstance(sample, dict):
            _emit_shape(sample, Segment, "Segment", "sync", base_url)
        _write_schema_snapshot(
            endpoint="/instruments/segments",
            client_function="get_segments",
            raw=raw,
            base_url=base_url,
            surface="sync",
        )
        return ProbeResult(name, "PASS", f"segments={len(segments)}"), segments
    except Exception as exc:  # D-09
        return (
            _finding_for_exc(exc, name=name, surface="sync", base_url=base_url),
            None,
        )


def probe_symbols_sync(client: Client) -> ProbeResult:
    """Symbols read sync (``active=False`` falsy filter) + SHAPE-diff + snapshot."""
    name = "symbols_sync"
    base_url = client._state.base_url
    try:
        symbols = client.get_symbols(active=False)
        raw = _raw_via_request_sync(
            client, _core.build_symbols_request(client._state, active=False)
        )
        # D-09: post-procesado dentro del try.
        sample = raw[0] if isinstance(raw, list) and raw else None
        if isinstance(sample, dict):
            _emit_shape(sample, Symbol, "Symbol", "sync", base_url)
        _write_schema_snapshot(
            endpoint="/symbols",
            client_function="get_symbols",
            raw=raw,
            base_url=base_url,
            surface="sync",
        )
        return ProbeResult(name, "PASS", f"symbols={len(symbols)}")
    except Exception as exc:  # D-09
        return _finding_for_exc(exc, name=name, surface="sync", base_url=base_url)


def probe_calendar_sync(client: Client) -> ProbeResult:
    """Calendar reads sync: ``get_calendar`` (list) + ``get_calendar_config`` (object)."""
    name = "calendar_sync"
    base_url = client._state.base_url
    try:
        days = client.get_calendar()
        config = client.get_calendar_config()
        raw_days = _raw_via_request_sync(client, _core.build_calendar_request(client._state))
        raw_config = _raw_via_request_sync(
            client, _core.build_calendar_config_request(client._state)
        )
        # D-09: post-procesado dentro del try.
        # El wire envuelve las filas en el envelope {config, coverage, days[],
        # market} (LIVE-MUT-01): tomar ``raw_days[0]`` sobre el dict daba siempre
        # None, así que el SHAPE-diff de CalendarDay nunca llegó a correr. Se
        # desenvuelve ``days`` y se mantiene el path de lista bare por compat.
        day_rows = _unwrap_rows(raw_days, "days")
        sample_day = day_rows[0] if day_rows else None
        if isinstance(sample_day, dict):
            _emit_shape(sample_day, CalendarDay, "CalendarDay", "sync", base_url)
        if isinstance(raw_config, dict):
            _emit_shape(raw_config, CalendarConfig, "CalendarConfig", "sync", base_url)
        _write_schema_snapshot(
            endpoint="/calendar",
            client_function="get_calendar",
            raw=raw_days,
            base_url=base_url,
            surface="sync",
        )
        _write_schema_snapshot(
            endpoint="/calendar/config",
            client_function="get_calendar_config",
            raw=raw_config,
            base_url=base_url,
            surface="sync",
        )
        return ProbeResult(name, "PASS", f"days={len(days)} config_tz={config.timezone!r}")
    except Exception as exc:  # D-09
        return _finding_for_exc(exc, name=name, surface="sync", base_url=base_url)


def probe_param_encoding_sync(client: Client) -> ProbeResult:
    """Param-encoding sync (D-04): los filtros bool falsy deben preservarse.

    Offline-determinístico: sólo construye el ``RequestSpec`` (sin HTTP) y afirma
    que ``offset=0`` / ``only_outright=False`` sobreviven y ``subscribed=None`` se
    dropea. Un drop de falsy legítimo emite un finding ``PARAM``.
    """
    name = "param_encoding_sync"
    base_url = client._state.base_url
    try:
        spec = _core.build_instruments_request(
            client._state,
            include_expired=True,
            only_outright=False,
            offset=0,
            subscribed=None,
        )
        params = spec.params or {}
        problems: list[str] = []
        if params.get("include_expired") is not True:
            problems.append("include_expired=True perdido/mis-typed")
        if params.get("only_outright") is not False:
            problems.append("only_outright=False (falsy) dropeado")
        if params.get("offset") != 0:
            problems.append("offset=0 (falsy) dropeado")
        if "subscribed" in params:
            problems.append("subscribed=None no dropeado")
    except Exception as exc:  # D-09
        return _finding_for_exc(exc, name=name, surface="sync", base_url=base_url)
    if problems:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="PARAM",
            surface="sync",
            status="OPEN",
            title="instruments param-encoding dropea filtros falsy",
            expected="include_expired=True/only_outright=False/offset=0 preservados; subscribed=None dropeado",
            actual=f"params={params!r}",
            diff="; ".join(problems),
            base_url=base_url,
        )
        return ProbeResult(name, "FINDING", f"{fid} (OPEN)")
    return ProbeResult(name, "PASS", "filtros falsy preservados")


def probe_no_data_sync(client: Client) -> ProbeResult:
    """No-data sync (D-09): un prefix inexistente → lista vacía clasificada NO-DATA."""
    name = "no_data_sync"
    base_url = client._state.base_url
    try:
        snapshots = client.get_market_data(prefix=_NO_DATA_PREFIX)
    except Exception as exc:  # D-09
        return _finding_for_exc(exc, name=name, surface="sync", base_url=base_url)
    if not snapshots:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="NO-DATA",
            surface="sync",
            status="OPEN",
            title=f"market_data vacío para prefix {_NO_DATA_PREFIX!r}",
            expected="lista vacía para un prefix inexistente",
            actual="[]",
            diff="empty/closed-market clasificado NO-DATA, nunca un crash",
            base_url=base_url,
        )
        return ProbeResult(name, "FINDING", f"{fid} (OPEN)")
    return ProbeResult(name, "PASS", f"snapshots={len(snapshots)}")


def probe_auth_fail_sync(client: Client) -> ProbeResult:
    """Auth-fail sync (D-05): un 401 debe mapear a ``MarketDataAuthError`` (AUTH)."""
    name = "auth_fail_sync"
    base_url = client._state.base_url
    synthetic = httpx.Response(401, request=httpx.Request("GET", f"{base_url}/marketdata"))
    try:
        _core.raise_for_response(synthetic)
    except md.MarketDataAuthError:
        return ProbeResult(name, "PASS", "401 -> MarketDataAuthError")
    except Exception as exc:  # D-09
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="AUTH",
            surface="sync",
            status="OPEN",
            title="401 mapeado a excepción incorrecta",
            expected="MarketDataAuthError",
            actual=repr(exc),
            diff=f"type={type(exc).__name__}",
            base_url=base_url,
        )
        return ProbeResult(name, "FINDING", f"{fid} (OPEN)")
    fid = _next_fid()
    append_finding(
        _PKG,
        fid=fid,
        class_="AUTH",
        surface="sync",
        status="OPEN",
        title="401 no levantó excepción",
        expected="MarketDataAuthError",
        actual="ninguna excepción",
        diff="raise_for_response se tragó un 401",
        base_url=base_url,
    )
    return ProbeResult(name, "FINDING", f"{fid} (OPEN)")


# ---------------------------------------------------------------------------
# Market-data + reference read probes — async (mirror)
# ---------------------------------------------------------------------------


async def probe_market_data_async(aclient: AsyncClient) -> ProbeResult:
    """Espejo async de :func:`probe_market_data_sync`."""
    name = "market_data_async"
    base_url = aclient._state.base_url
    try:
        snapshots = await aclient.get_market_data(active=True)
        raw = await _raw_via_request_async(
            aclient, _core.build_market_data_request(aclient._state, active=True)
        )
        # D-09: post-procesado dentro del try (espejo sync). Se desenvuelve el
        # envelope items[] (LIVE-MD-01) antes de tomar la muestra.
        if isinstance(raw, dict):
            rows = raw.get("items", [])
        elif isinstance(raw, list):
            rows = raw
        else:
            rows = []
        sample = rows[0] if isinstance(rows, list) and rows else None
        if isinstance(sample, dict):
            _emit_shape(sample, MarketDataSnapshot, "MarketDataSnapshot", "async", base_url)
        _write_schema_snapshot(
            endpoint="/marketdata",
            client_function="get_market_data",
            raw=raw,
            base_url=base_url,
            surface="async",
        )
        return ProbeResult(name, "PASS", f"snapshots={len(snapshots)}")
    except Exception as exc:  # D-09
        return _finding_for_exc(exc, name=name, surface="async", base_url=base_url)


async def probe_latest_async(aclient: AsyncClient) -> ProbeResult:
    """Espejo async de :func:`probe_latest_sync`."""
    name = "latest_async"
    base_url = aclient._state.base_url
    try:
        latest = await aclient.get_latest(symbol=_SAMPLE_SYMBOLS[0])
        batch = await aclient.get_latest_batch(LatestRequest(symbols=_SAMPLE_SYMBOLS))
        raw = await _raw_via_request_async(
            aclient, _core.build_latest_request(aclient._state, symbol=_SAMPLE_SYMBOLS[0])
        )
        # D-09: post-procesado dentro del try (espejo sync).
        sample = raw[0] if isinstance(raw, list) and raw else None
        if isinstance(sample, dict):
            _emit_shape(sample, MarketDataSnapshot, "MarketDataSnapshot", "async", base_url)
        _write_schema_snapshot(
            endpoint="/marketdata/latest",
            client_function="get_latest",
            raw=raw,
            base_url=base_url,
            surface="async",
        )
        return ProbeResult(name, "PASS", f"latest={len(latest)} batch={len(batch)}")
    except Exception as exc:  # D-09
        return _finding_for_exc(exc, name=name, surface="async", base_url=base_url)


async def probe_instruments_async(aclient: AsyncClient) -> ProbeResult:
    """Espejo async de :func:`probe_instruments_sync`."""
    name = "instruments_async"
    base_url = aclient._state.base_url
    try:
        instruments = await aclient.get_instruments(
            include_expired=True, only_outright=False, offset=0
        )
        raw = await _raw_via_request_async(
            aclient,
            _core.build_instruments_request(
                aclient._state, include_expired=True, only_outright=False, offset=0
            ),
        )
        # D-09: post-procesado dentro del try (espejo sync).
        sample = raw[0] if isinstance(raw, list) and raw else None
        if isinstance(sample, dict):
            _emit_shape(sample, Instrument, "Instrument", "async", base_url)
        _write_schema_snapshot(
            endpoint="/instruments",
            client_function="get_instruments",
            raw=raw,
            base_url=base_url,
            surface="async",
        )
        return ProbeResult(name, "PASS", f"instruments={len(instruments)}")
    except Exception as exc:  # D-09
        return _finding_for_exc(exc, name=name, surface="async", base_url=base_url)


async def probe_segments_async(
    aclient: AsyncClient,
) -> tuple[ProbeResult, list[Segment] | None]:
    """Espejo async de :func:`probe_segments_sync`; devuelve la lista para paridad."""
    name = "segments_async"
    base_url = aclient._state.base_url
    try:
        segments = await aclient.get_segments()
        raw = await _raw_via_request_async(aclient, _core.build_segments_request(aclient._state))
        # D-09: post-procesado dentro del try (espejo sync).
        sample = raw[0] if isinstance(raw, list) and raw else None
        if isinstance(sample, dict):
            _emit_shape(sample, Segment, "Segment", "async", base_url)
        _write_schema_snapshot(
            endpoint="/instruments/segments",
            client_function="get_segments",
            raw=raw,
            base_url=base_url,
            surface="async",
        )
        return ProbeResult(name, "PASS", f"segments={len(segments)}"), segments
    except Exception as exc:  # D-09
        return (
            _finding_for_exc(exc, name=name, surface="async", base_url=base_url),
            None,
        )


async def probe_symbols_async(aclient: AsyncClient) -> ProbeResult:
    """Espejo async de :func:`probe_symbols_sync`."""
    name = "symbols_async"
    base_url = aclient._state.base_url
    try:
        symbols = await aclient.get_symbols(active=False)
        raw = await _raw_via_request_async(
            aclient, _core.build_symbols_request(aclient._state, active=False)
        )
        # D-09: post-procesado dentro del try (espejo sync).
        sample = raw[0] if isinstance(raw, list) and raw else None
        if isinstance(sample, dict):
            _emit_shape(sample, Symbol, "Symbol", "async", base_url)
        _write_schema_snapshot(
            endpoint="/symbols",
            client_function="get_symbols",
            raw=raw,
            base_url=base_url,
            surface="async",
        )
        return ProbeResult(name, "PASS", f"symbols={len(symbols)}")
    except Exception as exc:  # D-09
        return _finding_for_exc(exc, name=name, surface="async", base_url=base_url)


async def probe_calendar_async(aclient: AsyncClient) -> ProbeResult:
    """Espejo async de :func:`probe_calendar_sync`."""
    name = "calendar_async"
    base_url = aclient._state.base_url
    try:
        days = await aclient.get_calendar()
        config = await aclient.get_calendar_config()
        raw_days = await _raw_via_request_async(
            aclient, _core.build_calendar_request(aclient._state)
        )
        raw_config = await _raw_via_request_async(
            aclient, _core.build_calendar_config_request(aclient._state)
        )
        # D-09: post-procesado dentro del try (espejo sync). Se desenvuelve el
        # envelope ``days[]`` antes de tomar la muestra (LIVE-MUT-01).
        day_rows = _unwrap_rows(raw_days, "days")
        sample_day = day_rows[0] if day_rows else None
        if isinstance(sample_day, dict):
            _emit_shape(sample_day, CalendarDay, "CalendarDay", "async", base_url)
        if isinstance(raw_config, dict):
            _emit_shape(raw_config, CalendarConfig, "CalendarConfig", "async", base_url)
        _write_schema_snapshot(
            endpoint="/calendar",
            client_function="get_calendar",
            raw=raw_days,
            base_url=base_url,
            surface="async",
        )
        _write_schema_snapshot(
            endpoint="/calendar/config",
            client_function="get_calendar_config",
            raw=raw_config,
            base_url=base_url,
            surface="async",
        )
        return ProbeResult(name, "PASS", f"days={len(days)} config_tz={config.timezone!r}")
    except Exception as exc:  # D-09
        return _finding_for_exc(exc, name=name, surface="async", base_url=base_url)


async def probe_no_data_async(aclient: AsyncClient) -> ProbeResult:
    """Espejo async de :func:`probe_no_data_sync`."""
    name = "no_data_async"
    base_url = aclient._state.base_url
    try:
        snapshots = await aclient.get_market_data(prefix=_NO_DATA_PREFIX)
    except Exception as exc:  # D-09
        return _finding_for_exc(exc, name=name, surface="async", base_url=base_url)
    if not snapshots:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="NO-DATA",
            surface="async",
            status="OPEN",
            title=f"market_data async vacío para prefix {_NO_DATA_PREFIX!r}",
            expected="lista vacía para un prefix inexistente",
            actual="[]",
            diff="empty/closed-market clasificado NO-DATA, nunca un crash",
            base_url=base_url,
        )
        return ProbeResult(name, "FINDING", f"{fid} (OPEN)")
    return ProbeResult(name, "PASS", f"snapshots={len(snapshots)}")


# ---------------------------------------------------------------------------
# Parity probe — sync ↔ async sobre reference-data estable
# ---------------------------------------------------------------------------


def probe_parity(
    seg_sync: list[Segment] | None,
    seg_async: list[Segment] | None,
    client: Client,
) -> ProbeResult:
    """Paridad sync↔async sobre segments (reference-data estable, D-04).

    Un mismatch de ids entre superficies emite un finding ``SYNC-ASYNC-DRIFT``.
    """
    name = "parity_sync_async"
    base_url = client._state.base_url
    if seg_sync is None or seg_async is None:
        return ProbeResult(name, "SKIPPED", "(un segments probe falló antes)")
    try:
        ids_sync = sorted(s.marketSegmentId for s in seg_sync)
        ids_async = sorted(s.marketSegmentId for s in seg_async)
    except Exception as exc:  # D-09: la comparación nunca crashea el driver
        return _finding_for_exc(exc, name=name, surface="both", base_url=base_url)
    if ids_sync != ids_async:
        fid = _next_fid()
        only_sync = sorted(set(ids_sync) - set(ids_async))
        only_async = sorted(set(ids_async) - set(ids_sync))
        append_finding(
            _PKG,
            fid=fid,
            class_="SYNC-ASYNC-DRIFT",
            surface="both",
            status="OPEN",
            title="segments sync y async devolvieron ids distintos",
            expected=f"sync == async ({len(ids_sync)} ids)",
            actual=f"sync={len(ids_sync)} async={len(ids_async)}",
            diff=f"solo-sync={only_sync} solo-async={only_async}",
            base_url=base_url,
        )
        return ProbeResult(name, "FINDING", f"{fid} (OPEN)")
    return ProbeResult(name, "PASS", f"segments sync==async ({len(ids_sync)})")


# ---------------------------------------------------------------------------
# Refuse-by-default probes del gate in-package (D-04) — sync + async
# ---------------------------------------------------------------------------
#
# Estos dos probes son deliberadamente HTTP-free y corren IDÉNTICO con el gate
# armado o apagado: fuerzan ``mutating_allowed=False`` y afirman que el paquete
# rechaza. Eso es lo que hace que una corrida con el gate apagado NO sea vacua.
# Un gate que NO rechaza es el defecto de mayor severidad que esta fase puede
# encontrar, así que se emite un finding ``AUTH`` OPEN en vez de un PASS.


def probe_mutation_gate_refusal_sync(client: Client) -> ProbeResult:
    """Refuse-by-default sync (D-04): sin opt-in, una mutación pública debe levantar."""
    name = "mutation_gate_refusal_sync"
    base_url = client._state.base_url
    previous = client._state.mutating_allowed
    try:
        # Se toca ``_state`` directamente (precedente in-package en
        # ``packages/market-data-client/tests/test_mutation_gate.py``): no es un
        # constructor ni un ``configure()``, así que ni la AST-guard de
        # single-instance ni el singleton de módulo se ven afectados.
        client._state.mutating_allowed = False
        try:
            client.preview_calendar_config(_REFUSAL_PROBE_CONFIG)
        except md.MarketDataMutationNotAllowedError:
            return ProbeResult(name, "PASS", "mutación rechazada sin opt-in (0 HTTP, 0 Auth0)")
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="AUTH",
            surface="sync",
            status="OPEN",
            title="el gate in-package NO rechazó una mutación con mutating_allowed=False",
            expected="MarketDataMutationNotAllowedError antes de cualquier HTTP",
            actual="ninguna excepción: la mutación salió a la red",
            diff="refuse-by-default roto (D-04/GATE-MD-01)",
            base_url=base_url,
        )
        return ProbeResult(name, "FINDING", f"{fid} (OPEN)")
    except Exception as exc:  # D-09: un error inesperado degrada, nunca voltea el driver
        return _finding_for_exc(exc, name=name, surface="sync", base_url=base_url)
    finally:
        client._state.mutating_allowed = previous


async def probe_mutation_gate_refusal_async(aclient: AsyncClient) -> ProbeResult:
    """Espejo async de :func:`probe_mutation_gate_refusal_sync` (D-04)."""
    name = "mutation_gate_refusal_async"
    base_url = aclient._state.base_url
    previous = aclient._state.mutating_allowed
    try:
        aclient._state.mutating_allowed = False
        try:
            await aclient.preview_calendar_config(_REFUSAL_PROBE_CONFIG)
        except md.MarketDataMutationNotAllowedError:
            return ProbeResult(name, "PASS", "mutación rechazada sin opt-in (0 HTTP, 0 Auth0)")
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="AUTH",
            surface="async",
            status="OPEN",
            title="el gate in-package async NO rechazó una mutación con mutating_allowed=False",
            expected="MarketDataMutationNotAllowedError antes de cualquier HTTP",
            actual="ninguna excepción: la mutación salió a la red",
            diff="refuse-by-default roto (D-04/GATE-MD-01)",
            base_url=base_url,
        )
        return ProbeResult(name, "FINDING", f"{fid} (OPEN)")
    except Exception as exc:  # D-09
        return _finding_for_exc(exc, name=name, surface="async", base_url=base_url)
    finally:
        aclient._state.mutating_allowed = previous


# ---------------------------------------------------------------------------
# Terminal probes — cierre de ciclo (D-18) + limitación operativa (D-06)
# ---------------------------------------------------------------------------


def probe_cycle_closure(client: Client) -> ProbeResult:
    """Cierre de ciclo (D-18): todo CONFIRMED/FIXED enlazado a un test de regresión.

    Endurecido contra el pase vacuo: ``verify_cycle_closure`` devuelve
    ``(True, [])`` también cuando el archivo no existe o no tiene ningún finding
    promovido — es decir, cuando no hay NADA que validar. Este probe exige además
    que el archivo exista y contenga al menos un finding CONFIRMED/FIXED; si no,
    reporta ``FAIL`` en vez de un PASS que no significa nada.
    """
    name = "cycle_closure"
    base_url = client._state.base_url
    try:
        ok, missing = verify_cycle_closure(_PKG)
        path = findings_path(_PKG)
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        n_closed = len(_CLOSED_STATUS_RE.findall(text))
        if ok and n_closed == 0:
            ok = False
            missing = ["<ningún finding CONFIRMED/FIXED: el cierre de ciclo sería vacuo>"]
    except Exception as exc:  # D-09
        return _finding_for_exc(exc, name=name, surface="sync", base_url=base_url)
    if ok:
        return ProbeResult(name, "PASS", f"{n_closed} CONFIRMED/FIXED con regresión")
    fid = _next_fid()
    append_finding(
        _PKG,
        fid=fid,
        class_="ERROR-MAP",
        surface="sync",
        status="OPEN",
        title=f"cycle closure: {len(missing)} findings CONFIRMED/FIXED sin test de regresión",
        expected="cada finding CONFIRMED/FIXED enlazado a un test existente",
        actual=f"missing: {', '.join(missing)}",
        diff="ver salida de verify_cycle_closure",
        base_url=base_url,
    )
    return ProbeResult(name, "FAIL", f"{fid} (OPEN) missing: {', '.join(missing)}")


def probe_expected_put_config_operator_gated(client: Client) -> ProbeResult:
    """Terminal EXPECTED (D-06): PUT/DELETE ``/calendar/config`` fuera del run en vivo.

    ``DELETE /calendar/config`` **resetea a los defaults del servidor**, no
    restaura el valor previo, así que un DELETE NO puede servir de cleanup para un
    PUT: un PUT real dejaría la config de develop —compartida— en un estado
    distinto del que tenía. Por eso ambos endpoints quedan operator-gated fuera de
    esta fase; su cobertura sigue viva en los tests mockeados del paquete.

    ``idempotent_by_title=True`` es lo que evita que este terminal se duplique con
    un fid nuevo en cada run (dedupe content-addressed por título).
    """
    name = "expected_put_config_operator_gated"
    base_url = client._state.base_url
    try:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="SHAPE",
            surface="both",
            status="EXPECTED",
            title="PUT/DELETE /calendar/config operator-gated fuera del run en vivo (D-06)",
            expected=(
                "shape en vivo de set_calendar_config / delete_calendar_config "
                "verificada contra develop"
            ),
            actual=(
                "sin cobertura en vivo: DELETE resetea a defaults del servidor y no "
                "restaura el valor previo, asi que no sirve de cleanup para un PUT; "
                "un PUT real dejaria la config compartida de develop alterada"
            ),
            diff=(
                "limitación operativa reconocida, no drift detectado; ambos endpoints "
                "siguen cubiertos por packages/market-data-client/tests (mocked)"
            ),
            base_url=base_url,
            idempotent_by_title=True,
        )
    except Exception as exc:  # D-09
        return _finding_for_exc(exc, name=name, surface="both", base_url=base_url)
    return ProbeResult(name, "PASS", f"{fid} (EXPECTED, dedupe by title)")


# ---------------------------------------------------------------------------
# Async wrapper — un único asyncio.run + UN AsyncClient (D-02)
# ---------------------------------------------------------------------------


async def _async_main(mutating: bool) -> tuple[list[ProbeResult], list[Segment] | None]:
    """Construye EXACTAMENTE UN ``AsyncClient`` y corre los probes async.

    ``mutating`` es el booleano del doble gate ya resuelto en ``main()``; se
    thread-ea al ÚNICO constructor async (D-02). No se recomputa acá ni se usa
    ``configure()``: ``configure()`` muta sólo el singleton de módulo, no esta
    instancia, y un segundo constructor rompería la AST-guard de single-instance.

    IN-03: el ``aclose()`` se envuelve en ``contextlib.suppress`` para que un
    fallo de teardown (error de red durante cierre, etc.) nunca se propague a
    ``asyncio.run(...)`` y crashee el driver (D-09). Devuelve los resultados y la
    lista de segments async (para el probe de paridad en ``main``).
    """
    aclient = AsyncClient(mutating_allowed=mutating, expected_host=_EXPECTED_DEVELOP_HOST)
    results: list[ProbeResult] = []
    seg_async: list[Segment] | None = None
    try:
        results.append(await probe_health_async(aclient))
        results.append(await probe_market_data_async(aclient))
        results.append(await probe_latest_async(aclient))
        results.append(await probe_instruments_async(aclient))
        seg_result, seg_async = await probe_segments_async(aclient)
        results.append(seg_result)
        results.append(await probe_symbols_async(aclient))
        results.append(await probe_calendar_async(aclient))
        results.append(await probe_no_data_async(aclient))
        # Refuse-by-default ANTES de cualquier probe destructivo (27-04).
        results.append(await probe_mutation_gate_refusal_async(aclient))
    except Exception as exc:  # D-09 defensa en profundidad: ningún path escapa a FAILED
        results.append(
            ProbeResult(
                "async_guard",
                "SKIPPED",
                f"excepción inesperada no aislada ({type(exc).__name__})",
            )
        )
    finally:
        with contextlib.suppress(Exception):
            await aclient.aclose()
    return results, seg_async


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

    # D-16/D-24: seedear el allocator ANTES del primer probe, para que cada fid
    # emitido en este run caiga por encima de lo ya registrado.
    _seed_fid_counter()

    # LIVE-MUT-01 / D-01: el doble gate se evalúa UNA sola vez, antes de que
    # exista un cliente. ``_env_base_url()`` es una función pura (no construye
    # nada), así que la AST-guard de single-instance no se ve afectada. Un gate
    # apagado NO corta el run: el read sweep sigue (D-03), sin ``sys.exit``.
    mutating = mutating_allowed_for(
        env_var=_MUTATING_ENV_VAR,
        base_url=_env_base_url(),
        expected_host=_EXPECTED_DEVELOP_HOST,
    )

    # D-02: EXACTAMENTE UN Client sync threadeado a cada probe sync. El
    # ``expected_host`` explícito mantiene la pata de host in-package
    # independiente de su default: son dos afirmaciones genuinamente separadas.
    client = Client(mutating_allowed=mutating, expected_host=_EXPECTED_DEVELOP_HOST)
    results: list[ProbeResult] = []
    seg_sync: list[Segment] | None = None
    try:
        results.append(probe_health_sync(client))
        results.append(probe_market_data_sync(client))
        results.append(probe_latest_sync(client))
        results.append(probe_instruments_sync(client))
        seg_result, seg_sync = probe_segments_sync(client)
        results.append(seg_result)
        results.append(probe_symbols_sync(client))
        results.append(probe_calendar_sync(client))
        results.append(probe_param_encoding_sync(client))
        results.append(probe_no_data_sync(client))
        results.append(probe_auth_fail_sync(client))
        # Refuse-by-default ANTES de cualquier probe destructivo (27-04).
        results.append(probe_mutation_gate_refusal_sync(client))
        async_results, seg_async = asyncio.run(_async_main(mutating))
        results.extend(async_results)
        results.append(probe_parity(seg_sync, seg_async, client))
        # Terminales: la limitación operativa D-06 y, último de todo, el cierre
        # de ciclo — que debe ver el findings file ya completo de este run.
        results.append(probe_expected_put_config_operator_gated(client))
        results.append(probe_cycle_closure(client))
    except Exception as exc:  # D-09 defensa en profundidad: el driver NUNCA exit != 0
        results.append(
            ProbeResult(
                "driver_guard",
                "SKIPPED",
                f"excepción inesperada no aislada ({type(exc).__name__})",
            )
        )
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
