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
from dataclasses import dataclass, fields
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
    NewSymbol,
    NewSymbols,
    Segment,
    Symbol,
    SymbolPatch,
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

# ---------------------------------------------------------------------------
# Identificadores de prueba del ciclo destructivo de symbols (D-05)
# ---------------------------------------------------------------------------
#
# La API NO expone ``DELETE /symbols`` (la fila queda referenciada por
# ``market_data``), así que la ÚNICA reversión posible de un alta es
# ``PATCH active=false``. Cada identificador que este driver crea deja, por lo
# tanto, UNA FILA PERMANENTE E INACTIVA en el catálogo de develop, para siempre.
#
# De ahí las dos propiedades de estos identificadores:
#
#   1. **Estables, NO timestampeados.** Un ``GSDPROBE/<timestamp>`` dejaría una
#      fila permanente NUEVA por cada corrida — residuo creciente sin techo. Los
#      identificadores fijos de acá acotan el residuo a EXACTAMENTE SEIS filas
#      para siempre y, además, hacen el ciclo re-ejecutable: el re-POST del mismo
#      símbolo es una reactivación documentada (200), no un conflicto.
#   2. **Prefijo dedicado y compartido `GSDPROBE/`.** Es lo que convierte un
#      residuo permanente en un residuo AUDITABLE: ``GET /symbols?prefix=GSDPROBE/``
#      lo lista server-side y el sweep terminal (27-05) lo barre. Los literales se
#      escriben completos —en vez de derivarse por f-string— para que un
#      ``grep GSDPROBE/`` sobre el repo encuentre los seis.
#
# Sync y async usan identificadores DISJUNTOS: así un fallo en una superficie no
# contamina el conteo de filas de la otra (el observable de idempotencia, D-19).
_PROBE_PREFIX = "GSDPROBE/"
_SYM_SYNC = "GSDPROBE/P27-SYNC"
_SYM_ASYNC = "GSDPROBE/P27-ASYNC"
_SYM_SYNC_B1 = "GSDPROBE/P27-SYNC-B1"
_SYM_SYNC_B2 = "GSDPROBE/P27-SYNC-B2"
_SYM_ASYNC_B1 = "GSDPROBE/P27-ASYNC-B1"
_SYM_ASYNC_B2 = "GSDPROBE/P27-ASYNC-B2"

# ---------------------------------------------------------------------------
# Identificadores del ciclo de calendar (D-06 config preview-only / D-07 holidays)
# ---------------------------------------------------------------------------
#
# CONFIG — **PREVIEW-ONLY** (D-06, ruling del operator). En vivo se ejercita
# ÚNICAMENTE ``POST /calendar/config/preview``, documentado como *"Writes
# nothing"*. ``PUT /calendar/config`` y ``DELETE /calendar/config`` NO tienen
# call site en este driver y la AST-guard
# ``verification/test_main_market_data_no_config_write.py`` lo vuelve
# irreintroducible: ``delete_calendar_config`` RESETEA a los defaults del
# servidor —no restaura el valor previo—, así que un DELETE no puede servir de
# cleanup para un PUT y cualquier PUT real dejaría clobbereada la configuración
# COMPARTIDA de develop. Ambos endpoints siguen cubiertos por los tests mockeados
# del paquete, y la limitación se registra como finding EXPECTED
# (``probe_expected_put_config_operator_gated``).
#
# HOLIDAYS — el ÚNICO ciclo create -> verify -> revert COMPLETO de la fase
# (D-07): ``DELETE /calendar/holidays/{day}`` existe y el spec en vivo dice que
# borrar ahí es seguro porque nada referencia esas filas.
#
# El AÑO 2099 es deliberado y no arbitrario: ``GET /calendar`` sólo acepta
# ``year`` en el rango 2000..2100, así que 2099 es a la vez LEGIBLE de vuelta
# (condición sin la cual el paso de confirmación no existiría) y lo bastante
# lejano como para no colisionar jamás con un feriado real ni tener impacto
# operativo alguno.
#
# Sync y async usan DÍAS DISJUNTOS por la misma razón que los símbolos: el
# observable de idempotencia es el CONTEO de días leídos de vuelta, así que un
# fallo en una superficie no puede contaminar el conteo de la otra.
_HOLIDAY_YEAR = 2099
_HOLIDAY_SYNC = "2099-12-29"
_HOLIDAY_ASYNC = "2099-12-30"
_HOLIDAY_DESCRIPTION = "GSD verification harness probe holiday"

# ``updated_by`` del preview: identifica al HARNESS, nunca a una persona, y NO
# se deriva de ninguna variable de entorno (T-27-30). El body del preview se
# snapshotea, así que nada operator-identifying puede entrar en él.
_PREVIEW_UPDATED_BY = "gsd-verification-harness"

# Ventana deliberadamente ESTRECHA (5 minutos) para observar cómo se REPORTA un
# preview que dispara el confirm-gate del servidor, sin persistir nada: el spec
# documenta el 409 del confirm gate sobre ``PUT``, y el preview es el único lugar
# donde esa señal puede observarse sin escribir.
_PREVIEW_NARROW_OPEN = "11:00"
_PREVIEW_NARROW_CLOSE = "11:05"

# Registro de ids de fila DESCUBIERTOS en vivo (D-10). ``Symbol`` no declara
# ningún campo de id y la spec en vivo tipa ``symbol_id`` como ENTERO mientras el
# cliente lo tipa ``str``, así que el id NO se asume: el probe de lectura lo
# localiza escaneando las claves de la fila cruda y lo deposita acá, y el probe de
# reversión lo consume. La clave del dict es el identificador de símbolo; el valor
# es ``object`` a propósito — no se presume ni el tipo ni el nombre de la clave de
# origen.
_discovered_symbol_ids: dict[str, object] = {}

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


# ---------------------------------------------------------------------------
# Despacho de MUTACIONES con el gate chequeado primero (LIVE-MUT-01 / T-27-20)
# ---------------------------------------------------------------------------
#
# CONTRASTE LOAD-BEARING con los dos helpers de arriba: ``_raw_via_request_sync``
# y ``_raw_via_request_async`` llaman ``_request`` DIRECTAMENTE, y ``_request``
# NO invoca ``_ensure_mutation_allowed()``. Son correctos para LECTURAS y sólo
# para lecturas: pasarles un spec de MUTACIÓN dispararía una escritura real sin
# pasar por el gate —con el gate posiblemente cerrado, contra el host que sea—.
# Esa es exactamente la elevación de privilegio que
# ``verification/test_main_market_data_no_gate_bypass.py`` vuelve imposible de
# reintroducir.


def _mutate_raw_sync(client: Client, spec: RequestSpec) -> httpx.Response:
    """Despacha un spec de MUTACIÓN sync con el gate chequeado ANTES (no bypass).

    ``_ensure_mutation_allowed()`` es la primera sentencia, exactamente como en
    cada método mutador público del paquete: un refusal emite CERO HTTP y CERO
    grant a Auth0.

    Devuelve el ``httpx.Response`` MATERIALIZADO en vez del JSON decodificado, a
    propósito: un único round trip rinde entonces el status code (evidencia
    D-19), el body crudo para el snapshot y el descubrimiento del id (D-10), y un
    response que el parser de ``_core`` también puede consumir (evidencia D-11).
    """
    client._ensure_mutation_allowed()
    return client._request(spec)


async def _mutate_raw_async(aclient: AsyncClient, spec: RequestSpec) -> httpx.Response:
    """Espejo async de :func:`_mutate_raw_sync` (gate primero, luego dispatch)."""
    aclient._ensure_mutation_allowed()
    return await aclient._request(spec)


def _emit_cleanup_finding(
    name: str,
    *,
    surface: str,
    base_url: str,
    exc: Exception,
    detail: str,
) -> None:
    """Emite un finding porque el CLEANUP de estado creado en develop falló (D-08).

    Un cleanup fallido es en sí mismo un hallazgo: deja estado huérfano en una
    infraestructura compartida y nadie se entera. Por eso NUNCA se traga con
    ``contextlib.suppress``. (Los dos teardowns de transporte del driver —
    ``client.close()`` / ``aclient.aclose()`` — sí conservan el idiom de suppress:
    ahí no hay estado remoto que quede huérfano, sólo un socket local.)
    """
    fid = _next_fid()
    append_finding(
        _PKG,
        fid=fid,
        class_="ERROR-MAP",
        surface=surface,
        status="OPEN",
        title=f"cleanup falló en {name}",
        expected="el estado creado por el probe revertido antes de terminar",
        actual=repr(exc),
        diff=f"{detail}; residuo huérfano en develop — el sweep terminal debe perseguirlo",
        base_url=base_url,
    )


def _skipped_when_gated(name: str) -> ProbeResult:
    """``ProbeResult`` uniforme de los probes destructivos con el gate cerrado (D-03).

    El detalle NO lleva dos puntos y la línea renderizada empieza con ``PROBE ``,
    así que el clasificador de ``main_verify.py`` ni la mira: el read sweep sigue
    clasificándose por sus propios méritos.
    """
    return ProbeResult(name, "SKIPPED", "(mutating, guard off)")


def _gate_open(state: Any) -> bool:
    """``True`` si el doble gate resuelto en ``main()`` llegó abierto a este cliente."""
    return bool(state.mutating_allowed)


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
# Ciclo destructivo de symbols (D-05) — create -> confirm -> revert
# ---------------------------------------------------------------------------
#
# NO existe ``DELETE /symbols`` en la spec en vivo (la fila queda referenciada
# por ``market_data``), así que la única reversión posible es
# ``PATCH active=false`` y el residuo es permanente por diseño — acotado a los
# seis identificadores fijos de arriba y barrible por su prefijo.
#
# Los ocho probes de esta sección se saltean a nivel PROBE cuando el gate está
# cerrado (D-03): el read sweep sigue corriendo y el driver nunca sale != 0.


def _discover_row_id(row: dict[str, Any]) -> tuple[str, object] | None:
    """Localiza el id de fila escaneando las CLAVES de un item crudo de ``/symbols`` (D-10).

    ``Symbol`` no declara ningún campo de id y la spec en vivo tipa ``symbol_id``
    como ENTERO mientras el cliente lo tipa ``str``, así que el nombre de la clave
    NO se hardcodea: se elige el primer valor ENTERO (excluyendo ``bool``, que en
    Python es subclase de ``int``) con esta precedencia determinística:

      1. la clave exacta ``id``;
      2. cualquier clave que termine en ``id`` (case-insensitive), en orden de wire;
      3. cualquier otra clave de valor entero, en orden de wire.

    Devuelve ``(nombre_de_clave, valor)``, o ``None`` si la fila no trae enteros.
    """
    candidates = [(k, v) for k, v in row.items() if isinstance(v, int) and not isinstance(v, bool)]
    if not candidates:
        return None
    for key, value in candidates:
        if key.lower() == "id":
            return key, value
    for key, value in candidates:
        if key.lower().endswith("id"):
            return key, value
    return candidates[0]


def _describe_symbols_misparse(raw: Any, parsed: list[Symbol]) -> str | None:
    """Describe la evidencia D-11 sin arreglarla: parser de lectura sobre body de escritura.

    ``_core.parse_symbols_response`` itera el body directamente. Contra una
    respuesta de MUTACIÓN que sea un objeto JSON bare, eso produce UN ``Symbol``
    all-default por CLAVE del objeto en vez de filas reales. Devuelve una
    descripción cuando el resultado tiene esa firma; ``None`` cuando el body es
    una lista (el caso para el que el parser fue escrito).
    """
    if isinstance(raw, list):
        return None
    if isinstance(raw, dict):
        blanks = sum(1 for p in parsed if p.symbol == "")
        return (
            f"body objeto JSON de {len(raw)} clave(s); parse_symbols_response devolvió "
            f"{len(parsed)} Symbol, {blanks} all-default"
        )
    return f"body de tipo {type(raw).__name__}; parse_symbols_response devolvió {len(parsed)} filas"


def _prefixed_rows(raw: Any) -> list[Any]:
    """Filas crudas de un ``GET /symbols?prefix=`` (bare list o envelope ``items``)."""
    return _unwrap_rows(raw, "items")


def _count_symbol_rows(raw_rows: list[Any], symbol: str) -> int:
    """Cuenta filas crudas cuyo ``symbol`` es exactamente ``symbol`` (observable D-19)."""
    return sum(1 for r in raw_rows if isinstance(r, dict) and r.get("symbol") == symbol)


def probe_create_symbol_sync(client: Client) -> ProbeResult:
    """Alta sync del símbolo de prueba: método público + re-fire crudo (D-05/D-11/D-19).

    Fire 1 va por el método PÚBLICO ``create_symbol`` — es lo que el criterio 1
    del ROADMAP pide literalmente y lo que ejercita el gate in-package. Fire 2 va
    por el helper con gate, que devuelve el ``httpx.Response`` y por lo tanto el
    status code y el body crudo. Como el endpoint está documentado idempotente,
    esos dos fires SON el doble-fire del experimento D-19; el veredicto de
    idempotencia, sin embargo, no se emite acá sino en el probe de lectura, por
    CONTEO DE FILAS (el 201 -> 200 sólo es observable contra un símbolo virgen,
    así que un experimento basado en el status no sería reproducible).
    """
    name = "create_symbol_sync"
    base_url = client._state.base_url
    if not _gate_open(client._state):
        return _skipped_when_gated(name)
    try:
        new_symbol = NewSymbol(symbol=_SYM_SYNC)
        created = client.create_symbol(new_symbol)
        refire = _mutate_raw_sync(
            client,
            _core.build_create_symbol_request(client._state, new_symbol.to_dict()),
        )
        raw = refire.json()
        parsed = _core.parse_symbols_response(refire)
        # D-09: todo el post-procesado dentro del try.
        _write_schema_snapshot(
            endpoint="POST /symbols",
            client_function="create_symbol_sync_response",
            raw=raw,
            base_url=base_url,
            surface="sync",
        )
        misparse = _describe_symbols_misparse(raw, parsed)
        if misparse is not None:
            fid = _next_fid()
            append_finding(
                _PKG,
                fid=fid,
                class_="ERROR-MAP",
                surface="sync",
                status="OPEN",
                title="create_symbol parsea la respuesta de escritura con el parser de lectura",
                expected="list[Symbol] con filas reales desde el body de POST /symbols",
                actual=misparse,
                diff=(
                    "parse_symbols_response itera el body: contra un objeto bare devuelve "
                    "un Symbol all-default por clave (D-11; se captura, no se arregla acá)"
                ),
                base_url=base_url,
            )
            return ProbeResult(name, "FINDING", f"{fid} (OPEN) refire_status={refire.status_code}")
        return ProbeResult(
            name,
            "PASS",
            f"public_rows={len(created)} refire_status={refire.status_code}",
        )
    except Exception as exc:  # D-09
        return _finding_for_exc(exc, name=name, surface="sync", base_url=base_url)


def probe_symbols_after_create_sync(client: Client) -> ProbeResult:
    """Confirma el alta sync, DESCUBRE el id y juzga idempotencia por filas (D-10/D-19).

    La lectura va por el helper SIN gate a propósito: es un GET. El veredicto de
    idempotencia se toma sobre el conteo de filas leído del servidor —una sola
    fila = el server dedupeó; dos o más = el doble-fire duplicó estado y el
    ``idempotent=True`` del builder es demasiado permisivo (D-20)—, nunca sobre un
    status code.
    """
    name = "symbols_after_create_sync"
    base_url = client._state.base_url
    if not _gate_open(client._state):
        return _skipped_when_gated(name)
    try:
        rows = client.get_symbols(prefix=_PROBE_PREFIX)
        raw = _raw_via_request_sync(
            client, _core.build_symbols_request(client._state, prefix=_PROBE_PREFIX)
        )
        # D-09: todo el post-procesado dentro del try. El snapshot lleva un
        # ``client_function`` PROPIO para que el payload filtrado por prefijo no
        # pise ni derive el baseline del read sin filtrar (D-17).
        raw_rows = _prefixed_rows(raw)
        _write_schema_snapshot(
            endpoint="GET /symbols?prefix=GSDPROBE/",
            client_function="get_symbols_probe_prefix_sync",
            raw=raw,
            base_url=base_url,
            surface="sync",
        )
        hits = [r for r in raw_rows if isinstance(r, dict) and r.get("symbol") == _SYM_SYNC]
        if hits:
            # Primera vez que se observa una fila de symbols POBLADA: es también la
            # evidencia de si ``Symbol.marketId`` debería ser ``market_id``.
            _emit_shape(hits[0], Symbol, "Symbol", "sync", base_url)
        if not hits:
            fid = _next_fid()
            append_finding(
                _PKG,
                fid=fid,
                class_="ERROR-MAP",
                surface="sync",
                status="OPEN",
                title=f"{_SYM_SYNC} ausente de GET /symbols tras el alta",
                expected="la fila creada visible al filtrar por el prefijo del probe",
                actual=f"0 filas con ese symbol sobre {len(raw_rows)} leídas por prefijo",
                diff="el alta no persistió o el param prefix no filtra como se asume",
                base_url=base_url,
            )
            return ProbeResult(name, "FINDING", f"{fid} (OPEN)")
        if len(hits) > 1:
            fid = _next_fid()
            append_finding(
                _PKG,
                fid=fid,
                class_="ERROR-MAP",
                surface="sync",
                status="OPEN",
                title=f"POST /symbols duplicó estado con el doble-fire de {_SYM_SYNC}",
                expected="exactamente 1 fila tras 2 POST idénticos (idempotent=True, DM-03)",
                actual=f"{len(hits)} filas con ese symbol",
                diff=(
                    "idempotent=True en build_create_symbol_request es DEMASIADO PERMISIVO: "
                    "un retry del RetryTransport duplicaría estado (D-20)"
                ),
                base_url=base_url,
            )
            return ProbeResult(name, "FINDING", f"{fid} (OPEN) filas={len(hits)}")
        found = _discover_row_id(hits[0])
        if found is None:
            fid = _next_fid()
            append_finding(
                _PKG,
                fid=fid,
                class_="ERROR-MAP",
                surface="sync",
                status="OPEN",
                title="ninguna clave de valor entero en la fila de GET /symbols (id no hallado)",
                expected="un id de fila entero, el que PATCH /symbols/{symbol_id} espera",
                actual=f"claves observadas: {sorted(hits[0])}",
                diff="sólo se registran NOMBRES de clave, nunca valores (T-27-24)",
                base_url=base_url,
            )
            return ProbeResult(name, "FINDING", f"{fid} (OPEN)")
        key, value = found
        _discovered_symbol_ids[_SYM_SYNC] = value
        return ProbeResult(
            name,
            "PASS",
            f"1 fila; id descubierto en clave {key!r} (prefijo devolvió {len(rows)} filas)",
        )
    except Exception as exc:  # D-09
        return _finding_for_exc(exc, name=name, surface="sync", base_url=base_url)


def probe_create_symbols_batch_sync(client: Client) -> ProbeResult:
    """Alta batch sync doble-fire + conteo de filas por identificador (D-05/D-19).

    El ``finally`` revierte los DOS identificadores del batch a ``active=false``
    apenas terminada la medición: dejarlos activos envenenaría el ingestor de
    develop de forma permanente (un símbolo desconocido se rechaza en el feed y
    aflora como ``last_error``). Un fallo de esa reversión emite un finding, nunca
    se suprime (D-08).
    """
    name = "create_symbols_batch_sync"
    base_url = client._state.base_url
    if not _gate_open(client._state):
        return _skipped_when_gated(name)
    batch = (_SYM_SYNC_B1, _SYM_SYNC_B2)
    try:
        new_symbols = NewSymbols(
            symbols=[NewSymbol(symbol=_SYM_SYNC_B1), NewSymbol(symbol=_SYM_SYNC_B2)]
        )
        created = client.create_symbols(new_symbols)
        refire = _mutate_raw_sync(
            client,
            _core.build_create_symbols_request(client._state, new_symbols.to_dict()),
        )
        raw = refire.json()
        # D-09: todo el post-procesado dentro del try.
        _write_schema_snapshot(
            endpoint="POST /symbols/batch",
            client_function="create_symbols_batch_sync_response",
            raw=raw,
            base_url=base_url,
            surface="sync",
        )
        readback = _raw_via_request_sync(
            client, _core.build_symbols_request(client._state, prefix=_PROBE_PREFIX)
        )
        readback_rows = _prefixed_rows(readback)
        counts = {sym: _count_symbol_rows(readback_rows, sym) for sym in batch}
        for sym in batch:
            match = next(
                (r for r in readback_rows if isinstance(r, dict) and r.get("symbol") == sym),
                None,
            )
            found = _discover_row_id(match) if isinstance(match, dict) else None
            if found is not None:
                _discovered_symbol_ids[sym] = found[1]
        if any(n != 1 for n in counts.values()):
            fid = _next_fid()
            duplicated = sorted(s for s, n in counts.items() if n > 1)
            missing = sorted(s for s, n in counts.items() if n == 0)
            append_finding(
                _PKG,
                fid=fid,
                class_="ERROR-MAP",
                surface="sync",
                status="OPEN",
                title="POST /symbols/batch no dejó exactamente 1 fila por identificador",
                expected="1 fila por identificador tras 2 batches idénticos (idempotent=True, DM-03)",
                actual=f"conteos={counts}",
                diff=(
                    f"duplicados={duplicated} ausentes={missing}; si hay duplicados, "
                    "idempotent=True en build_create_symbols_request es DEMASIADO PERMISIVO (D-20)"
                ),
                base_url=base_url,
            )
            return ProbeResult(name, "FINDING", f"{fid} (OPEN) conteos={counts}")
        return ProbeResult(
            name,
            "PASS",
            f"1 fila por identificador; public_rows={len(created)} refire_status={refire.status_code}",
        )
    except Exception as exc:  # D-09
        return _finding_for_exc(exc, name=name, surface="sync", base_url=base_url)
    finally:
        # D-08: el fallo de cleanup es un finding, NUNCA un suppress. Nada de
        # _emit_shape / _write_schema_snapshot acá (rompería el guard de D-09).
        for sym in batch:
            row_id = _discovered_symbol_ids.get(sym)
            try:
                if row_id is not None:
                    client.update_symbol(str(row_id), SymbolPatch(active=False))
            except Exception as exc:
                _emit_cleanup_finding(
                    name,
                    surface="sync",
                    base_url=base_url,
                    exc=exc,
                    detail=f"{sym} pudo quedar ACTIVO en el catálogo de develop",
                )


def probe_update_symbol_sync(client: Client) -> ProbeResult:
    """Reversión sync: ``PATCH active=false`` doble-fire + confirmación (D-05/D-19).

    Es el cierre del ciclo: la ÚNICA reversión que la API ofrece. El id se toma
    del registro poblado por el probe de lectura; si no está, el probe emite un
    finding en vez de adivinar uno (un PATCH sobre un id inventado tocaría una
    fila ajena de develop).
    """
    name = "update_symbol_sync"
    base_url = client._state.base_url
    if not _gate_open(client._state):
        return _skipped_when_gated(name)
    row_id: object | None = None
    try:
        row_id = _discovered_symbol_ids.get(_SYM_SYNC)
        if row_id is None:
            fid = _next_fid()
            append_finding(
                _PKG,
                fid=fid,
                class_="ERROR-MAP",
                surface="sync",
                status="OPEN",
                title=f"ciclo create->revert incompleto: sin id descubierto para {_SYM_SYNC}",
                expected="un id de fila descubierto en vivo por el probe de lectura (D-10)",
                actual="registro de ids vacío para este identificador",
                diff="no se adivina: un PATCH sobre un id inventado tocaría una fila ajena",
                base_url=base_url,
            )
            return ProbeResult(name, "FINDING", f"{fid} (OPEN)")
        patch = SymbolPatch(active=False)
        reverted = client.update_symbol(str(row_id), patch)
        refire = _mutate_raw_sync(
            client,
            _core.build_update_symbol_request(client._state, str(row_id), patch.to_dict()),
        )
        # D-09: todo el post-procesado dentro del try.
        _write_schema_snapshot(
            endpoint="PATCH /symbols/{symbol_id}",
            client_function="update_symbol_sync_response",
            raw=refire.json(),
            base_url=base_url,
            surface="sync",
        )
        still_active = [s.symbol for s in client.get_symbols(prefix=_PROBE_PREFIX) if s.active]
        if _SYM_SYNC in still_active:
            fid = _next_fid()
            append_finding(
                _PKG,
                fid=fid,
                class_="ERROR-MAP",
                surface="sync",
                status="OPEN",
                title=f"{_SYM_SYNC} sigue activo tras PATCH active=false",
                expected="active=false tras la reversión (única reversión que la API ofrece)",
                actual=f"activos con prefijo del probe: {sorted(still_active)}",
                diff=f"refire_status={refire.status_code}; residuo ACTIVO en develop",
                base_url=base_url,
            )
            return ProbeResult(name, "FINDING", f"{fid} (OPEN)")
        return ProbeResult(
            name,
            "PASS",
            f"revertido; public_rows={len(reverted)} refire_status={refire.status_code}",
        )
    except Exception as exc:  # D-09
        return _finding_for_exc(exc, name=name, surface="sync", base_url=base_url)
    finally:
        # D-08: reintento defensivo de la reversión; su fallo es un finding, NUNCA
        # un suppress. Nada de _emit_shape / _write_schema_snapshot acá.
        try:
            if row_id is not None:
                client.update_symbol(str(row_id), SymbolPatch(active=False))
        except Exception as exc:
            _emit_cleanup_finding(
                name,
                surface="sync",
                base_url=base_url,
                exc=exc,
                detail=f"{_SYM_SYNC} pudo quedar ACTIVO en el catálogo de develop",
            )


async def probe_create_symbol_async(aclient: AsyncClient) -> ProbeResult:
    """Espejo async de :func:`probe_create_symbol_sync` (D-05/D-11/D-15/D-19)."""
    name = "create_symbol_async"
    base_url = aclient._state.base_url
    if not _gate_open(aclient._state):
        return _skipped_when_gated(name)
    try:
        new_symbol = NewSymbol(symbol=_SYM_ASYNC)
        created = await aclient.create_symbol(new_symbol)
        refire = await _mutate_raw_async(
            aclient,
            _core.build_create_symbol_request(aclient._state, new_symbol.to_dict()),
        )
        raw = refire.json()
        parsed = _core.parse_symbols_response(refire)
        # D-09: todo el post-procesado dentro del try (espejo sync). El
        # ``client_function`` es PROPIO de esta superficie, para que una divergencia
        # sync/async del body de escritura quede visible en vez de pisarse.
        _write_schema_snapshot(
            endpoint="POST /symbols",
            client_function="create_symbol_async_response",
            raw=raw,
            base_url=base_url,
            surface="async",
        )
        misparse = _describe_symbols_misparse(raw, parsed)
        if misparse is not None:
            fid = _next_fid()
            append_finding(
                _PKG,
                fid=fid,
                class_="ERROR-MAP",
                surface="async",
                status="OPEN",
                title="create_symbol async parsea la respuesta de escritura con el parser de lectura",
                expected="list[Symbol] con filas reales desde el body de POST /symbols",
                actual=misparse,
                diff=(
                    "parse_symbols_response itera el body: contra un objeto bare devuelve "
                    "un Symbol all-default por clave (D-11; se captura, no se arregla acá)"
                ),
                base_url=base_url,
            )
            return ProbeResult(name, "FINDING", f"{fid} (OPEN) refire_status={refire.status_code}")
        return ProbeResult(
            name,
            "PASS",
            f"public_rows={len(created)} refire_status={refire.status_code}",
        )
    except Exception as exc:  # D-09
        return _finding_for_exc(exc, name=name, surface="async", base_url=base_url)


async def probe_symbols_after_create_async(aclient: AsyncClient) -> ProbeResult:
    """Espejo async de :func:`probe_symbols_after_create_sync` (D-10/D-15/D-19)."""
    name = "symbols_after_create_async"
    base_url = aclient._state.base_url
    if not _gate_open(aclient._state):
        return _skipped_when_gated(name)
    try:
        rows = await aclient.get_symbols(prefix=_PROBE_PREFIX)
        raw = await _raw_via_request_async(
            aclient, _core.build_symbols_request(aclient._state, prefix=_PROBE_PREFIX)
        )
        # D-09: todo el post-procesado dentro del try (espejo sync); snapshot con
        # ``client_function`` propio del prefijo Y de la superficie (D-17).
        raw_rows = _prefixed_rows(raw)
        _write_schema_snapshot(
            endpoint="GET /symbols?prefix=GSDPROBE/",
            client_function="get_symbols_probe_prefix_async",
            raw=raw,
            base_url=base_url,
            surface="async",
        )
        hits = [r for r in raw_rows if isinstance(r, dict) and r.get("symbol") == _SYM_ASYNC]
        if hits:
            _emit_shape(hits[0], Symbol, "Symbol", "async", base_url)
        if not hits:
            fid = _next_fid()
            append_finding(
                _PKG,
                fid=fid,
                class_="ERROR-MAP",
                surface="async",
                status="OPEN",
                title=f"{_SYM_ASYNC} ausente de GET /symbols tras el alta",
                expected="la fila creada visible al filtrar por el prefijo del probe",
                actual=f"0 filas con ese symbol sobre {len(raw_rows)} leídas por prefijo",
                diff="el alta no persistió o el param prefix no filtra como se asume",
                base_url=base_url,
            )
            return ProbeResult(name, "FINDING", f"{fid} (OPEN)")
        if len(hits) > 1:
            fid = _next_fid()
            append_finding(
                _PKG,
                fid=fid,
                class_="ERROR-MAP",
                surface="async",
                status="OPEN",
                title=f"POST /symbols duplicó estado con el doble-fire de {_SYM_ASYNC}",
                expected="exactamente 1 fila tras 2 POST idénticos (idempotent=True, DM-03)",
                actual=f"{len(hits)} filas con ese symbol",
                diff=(
                    "idempotent=True en build_create_symbol_request es DEMASIADO PERMISIVO: "
                    "un retry del RetryTransport duplicaría estado (D-20)"
                ),
                base_url=base_url,
            )
            return ProbeResult(name, "FINDING", f"{fid} (OPEN) filas={len(hits)}")
        found = _discover_row_id(hits[0])
        if found is None:
            fid = _next_fid()
            append_finding(
                _PKG,
                fid=fid,
                class_="ERROR-MAP",
                surface="async",
                status="OPEN",
                title="ninguna clave de valor entero en la fila async de GET /symbols",
                expected="un id de fila entero, el que PATCH /symbols/{symbol_id} espera",
                actual=f"claves observadas: {sorted(hits[0])}",
                diff="sólo se registran NOMBRES de clave, nunca valores (T-27-24)",
                base_url=base_url,
            )
            return ProbeResult(name, "FINDING", f"{fid} (OPEN)")
        key, value = found
        _discovered_symbol_ids[_SYM_ASYNC] = value
        return ProbeResult(
            name,
            "PASS",
            f"1 fila; id descubierto en clave {key!r} (prefijo devolvió {len(rows)} filas)",
        )
    except Exception as exc:  # D-09
        return _finding_for_exc(exc, name=name, surface="async", base_url=base_url)


async def probe_create_symbols_batch_async(aclient: AsyncClient) -> ProbeResult:
    """Espejo async de :func:`probe_create_symbols_batch_sync` (D-05/D-15/D-19)."""
    name = "create_symbols_batch_async"
    base_url = aclient._state.base_url
    if not _gate_open(aclient._state):
        return _skipped_when_gated(name)
    batch = (_SYM_ASYNC_B1, _SYM_ASYNC_B2)
    try:
        new_symbols = NewSymbols(
            symbols=[NewSymbol(symbol=_SYM_ASYNC_B1), NewSymbol(symbol=_SYM_ASYNC_B2)]
        )
        created = await aclient.create_symbols(new_symbols)
        refire = await _mutate_raw_async(
            aclient,
            _core.build_create_symbols_request(aclient._state, new_symbols.to_dict()),
        )
        raw = refire.json()
        # D-09: todo el post-procesado dentro del try (espejo sync).
        _write_schema_snapshot(
            endpoint="POST /symbols/batch",
            client_function="create_symbols_batch_async_response",
            raw=raw,
            base_url=base_url,
            surface="async",
        )
        readback = await _raw_via_request_async(
            aclient, _core.build_symbols_request(aclient._state, prefix=_PROBE_PREFIX)
        )
        readback_rows = _prefixed_rows(readback)
        counts = {sym: _count_symbol_rows(readback_rows, sym) for sym in batch}
        for sym in batch:
            match = next(
                (r for r in readback_rows if isinstance(r, dict) and r.get("symbol") == sym),
                None,
            )
            found = _discover_row_id(match) if isinstance(match, dict) else None
            if found is not None:
                _discovered_symbol_ids[sym] = found[1]
        if any(n != 1 for n in counts.values()):
            fid = _next_fid()
            duplicated = sorted(s for s, n in counts.items() if n > 1)
            missing = sorted(s for s, n in counts.items() if n == 0)
            append_finding(
                _PKG,
                fid=fid,
                class_="ERROR-MAP",
                surface="async",
                status="OPEN",
                title="POST /symbols/batch async no dejó exactamente 1 fila por identificador",
                expected="1 fila por identificador tras 2 batches idénticos (idempotent=True, DM-03)",
                actual=f"conteos={counts}",
                diff=(
                    f"duplicados={duplicated} ausentes={missing}; si hay duplicados, "
                    "idempotent=True en build_create_symbols_request es DEMASIADO PERMISIVO (D-20)"
                ),
                base_url=base_url,
            )
            return ProbeResult(name, "FINDING", f"{fid} (OPEN) conteos={counts}")
        return ProbeResult(
            name,
            "PASS",
            f"1 fila por identificador; public_rows={len(created)} refire_status={refire.status_code}",
        )
    except Exception as exc:  # D-09
        return _finding_for_exc(exc, name=name, surface="async", base_url=base_url)
    finally:
        # D-08: el fallo de cleanup es un finding, NUNCA un suppress. Nada de
        # _emit_shape / _write_schema_snapshot acá (rompería el guard de D-09).
        for sym in batch:
            row_id = _discovered_symbol_ids.get(sym)
            try:
                if row_id is not None:
                    await aclient.update_symbol(str(row_id), SymbolPatch(active=False))
            except Exception as exc:
                _emit_cleanup_finding(
                    name,
                    surface="async",
                    base_url=base_url,
                    exc=exc,
                    detail=f"{sym} pudo quedar ACTIVO en el catálogo de develop",
                )


async def probe_update_symbol_async(aclient: AsyncClient) -> ProbeResult:
    """Espejo async de :func:`probe_update_symbol_sync` — la reversión (D-05/D-15/D-19)."""
    name = "update_symbol_async"
    base_url = aclient._state.base_url
    if not _gate_open(aclient._state):
        return _skipped_when_gated(name)
    row_id: object | None = None
    try:
        row_id = _discovered_symbol_ids.get(_SYM_ASYNC)
        if row_id is None:
            fid = _next_fid()
            append_finding(
                _PKG,
                fid=fid,
                class_="ERROR-MAP",
                surface="async",
                status="OPEN",
                title=f"ciclo create->revert incompleto: sin id descubierto para {_SYM_ASYNC}",
                expected="un id de fila descubierto en vivo por el probe de lectura (D-10)",
                actual="registro de ids vacío para este identificador",
                diff="no se adivina: un PATCH sobre un id inventado tocaría una fila ajena",
                base_url=base_url,
            )
            return ProbeResult(name, "FINDING", f"{fid} (OPEN)")
        patch = SymbolPatch(active=False)
        reverted = await aclient.update_symbol(str(row_id), patch)
        refire = await _mutate_raw_async(
            aclient,
            _core.build_update_symbol_request(aclient._state, str(row_id), patch.to_dict()),
        )
        # D-09: todo el post-procesado dentro del try (espejo sync).
        _write_schema_snapshot(
            endpoint="PATCH /symbols/{symbol_id}",
            client_function="update_symbol_async_response",
            raw=refire.json(),
            base_url=base_url,
            surface="async",
        )
        current = await aclient.get_symbols(prefix=_PROBE_PREFIX)
        still_active = [s.symbol for s in current if s.active]
        if _SYM_ASYNC in still_active:
            fid = _next_fid()
            append_finding(
                _PKG,
                fid=fid,
                class_="ERROR-MAP",
                surface="async",
                status="OPEN",
                title=f"{_SYM_ASYNC} sigue activo tras PATCH active=false",
                expected="active=false tras la reversión (única reversión que la API ofrece)",
                actual=f"activos con prefijo del probe: {sorted(still_active)}",
                diff=f"refire_status={refire.status_code}; residuo ACTIVO en develop",
                base_url=base_url,
            )
            return ProbeResult(name, "FINDING", f"{fid} (OPEN)")
        return ProbeResult(
            name,
            "PASS",
            f"revertido; public_rows={len(reverted)} refire_status={refire.status_code}",
        )
    except Exception as exc:  # D-09
        return _finding_for_exc(exc, name=name, surface="async", base_url=base_url)
    finally:
        # D-08: reintento defensivo de la reversión; su fallo es un finding, NUNCA
        # un suppress. Nada de _emit_shape / _write_schema_snapshot acá.
        try:
            if row_id is not None:
                await aclient.update_symbol(str(row_id), SymbolPatch(active=False))
        except Exception as exc:
            _emit_cleanup_finding(
                name,
                surface="async",
                base_url=base_url,
                exc=exc,
                detail=f"{_SYM_ASYNC} pudo quedar ACTIVO en el catálogo de develop",
            )


# ---------------------------------------------------------------------------
# Ciclo de calendar (D-06/D-07) — config PREVIEW-ONLY + holidays revert-completo
# ---------------------------------------------------------------------------


def _echo_market_hours(config: CalendarConfig) -> MarketHoursIn:
    """``MarketHoursIn`` que ECOA la ventana ya configurada, con ``confirm=False``.

    Ecoar la config vigente es lo que hace que el preview sea un no-op semántico
    además de un no-op declarado: aunque el servidor persistiera (que es
    justamente lo que el probe verifica que NO pasa), el valor escrito sería el
    que ya estaba. ``updated_by`` es el identificador del HARNESS, nunca uno
    derivado del entorno (T-27-30).
    """
    return MarketHoursIn(
        open_time=config.open,
        close_time=config.close,
        timezone=config.timezone,
        pre_open_minutes=config.pre_open_minutes,
        enabled=config.enabled,
        updated_by=_PREVIEW_UPDATED_BY,
        confirm=False,
    )


def _config_field_diff(before: CalendarConfig, after: CalendarConfig) -> list[str]:
    """NOMBRES de campo que difieren entre dos configs — nunca sus valores (T-27-30)."""
    return sorted(
        f.name for f in fields(before) if getattr(before, f.name) != getattr(after, f.name)
    )


def _emit_preview_idempotency_verdict(*, surface: str, identical: bool, base_url: str) -> str:
    """Registra el veredicto D-19 del doble-fire del preview (EXPECTED, dedupe por título).

    Se emite en AMBAS direcciones porque es evidencia de revalidación de DM-03
    que el criterio 3 exige, no un defecto: el flag ``idempotent=True`` de
    ``build_preview_calendar_config_request`` sólo se toca en el plan 27-07 y
    sólo si esta medición lo pide (D-20). ``status="EXPECTED"`` mantiene la
    medición fuera del conteo de divergencias abiertas.
    """
    fid = _next_fid()
    verdict = "idénticos" if identical else "DISTINTOS"
    append_finding(
        _PKG,
        fid=fid,
        class_="ERROR-MAP",
        surface=surface,
        status="EXPECTED",
        title=f"D-19 {surface}: doble-fire de POST /calendar/config/preview devolvió bodies {verdict}",
        expected=(
            "medición en vivo del flag idempotent=True de "
            "build_preview_calendar_config_request (DM-03/D-19)"
        ),
        actual=f"los dos previews de la MISMA ventana devolvieron bodies {verdict}",
        diff="evidencia medida para el plan 27-07; el flag NO se cambia acá (D-20)",
        base_url=base_url,
        idempotent_by_title=True,
    )
    return fid


def probe_preview_calendar_config_sync(client: Client) -> ProbeResult:
    """Config sync PREVIEW-ONLY (D-06): verifica el *"Writes nothing"* en vez de creerlo.

    Lee la config ANTES, dispara el preview (público + doble-fire con gate + una
    ventana estrecha que debería producir warnings) y RE-LEE la config. La
    igualdad antes/después es la prueba en vivo de que el endpoint no persiste —
    y es lo que permite AFIRMAR el criterio 2 del ROADMAP en lugar de asumirlo.
    Cualquier diferencia es un finding ``ERROR-MAP`` OPEN.
    """
    name = "preview_calendar_config_sync"
    base_url = client._state.base_url
    if not _gate_open(client._state):
        return _skipped_when_gated(name)
    try:
        before = client.get_calendar_config()
        echo = _echo_market_hours(before)
        previewed = client.preview_calendar_config(echo)
        first = _mutate_raw_sync(
            client, _core.build_preview_calendar_config_request(client._state, echo.to_dict())
        )
        second = _mutate_raw_sync(
            client, _core.build_preview_calendar_config_request(client._state, echo.to_dict())
        )
        body_first = first.json()
        body_second = second.json()
        narrow = MarketHoursIn(
            open_time=_PREVIEW_NARROW_OPEN,
            close_time=_PREVIEW_NARROW_CLOSE,
            timezone=before.timezone,
            updated_by=_PREVIEW_UPDATED_BY,
        )
        narrow_body = _mutate_raw_sync(
            client, _core.build_preview_calendar_config_request(client._state, narrow.to_dict())
        ).json()
        after = client.get_calendar_config()
        # D-09: todo el post-procesado dentro del try. El snapshot lleva un
        # ``client_function`` propio de esta superficie (D-17) y captura SÓLO el
        # body del eco: el de la ventana estrecha trae ``warnings`` poblados, y
        # su tipo de lista derivaría el baseline en cuanto el servidor tocara ese
        # texto.
        _write_schema_snapshot(
            endpoint="POST /calendar/config/preview",
            client_function="preview_calendar_config_sync_response",
            raw=body_first,
            base_url=base_url,
            surface="sync",
        )
        n_narrow_warnings = (
            len(narrow_body.get("warnings", [])) if isinstance(narrow_body, dict) else 0
        )
        _emit_preview_idempotency_verdict(
            surface="sync", identical=body_first == body_second, base_url=base_url
        )
        changed = _config_field_diff(before, after)
        if changed:
            fid = _next_fid()
            append_finding(
                _PKG,
                fid=fid,
                class_="ERROR-MAP",
                surface="sync",
                status="OPEN",
                title="POST /calendar/config/preview modificó la config pese a declarar 'Writes nothing'",
                expected="get_calendar_config() idéntica antes y después del preview",
                actual=f"campos que cambiaron: {changed}",
                diff=(
                    "sólo se registran NOMBRES de campo, nunca valores (T-27-30); "
                    "si el preview persiste, la config compartida de develop quedó alterada"
                ),
                base_url=base_url,
            )
            return ProbeResult(name, "FINDING", f"{fid} (OPEN)")
        return ProbeResult(
            name,
            "PASS",
            (
                f"config sin cambios; doble-fire idéntico={body_first == body_second} "
                f"eco_warnings={len(previewed.warnings)} ventana_estrecha_warnings={n_narrow_warnings}"
            ),
        )
    except Exception as exc:  # D-09
        return _finding_for_exc(exc, name=name, surface="sync", base_url=base_url)


async def probe_preview_calendar_config_async(aclient: AsyncClient) -> ProbeResult:
    """Espejo async de :func:`probe_preview_calendar_config_sync` (D-06/D-19)."""
    name = "preview_calendar_config_async"
    base_url = aclient._state.base_url
    if not _gate_open(aclient._state):
        return _skipped_when_gated(name)
    try:
        before = await aclient.get_calendar_config()
        echo = _echo_market_hours(before)
        previewed = await aclient.preview_calendar_config(echo)
        first = await _mutate_raw_async(
            aclient, _core.build_preview_calendar_config_request(aclient._state, echo.to_dict())
        )
        second = await _mutate_raw_async(
            aclient, _core.build_preview_calendar_config_request(aclient._state, echo.to_dict())
        )
        body_first = first.json()
        body_second = second.json()
        narrow = MarketHoursIn(
            open_time=_PREVIEW_NARROW_OPEN,
            close_time=_PREVIEW_NARROW_CLOSE,
            timezone=before.timezone,
            updated_by=_PREVIEW_UPDATED_BY,
        )
        narrow_resp = await _mutate_raw_async(
            aclient, _core.build_preview_calendar_config_request(aclient._state, narrow.to_dict())
        )
        narrow_body = narrow_resp.json()
        after = await aclient.get_calendar_config()
        # D-09: post-procesado dentro del try (espejo sync); ``client_function``
        # propio de ESTA superficie para que una divergencia sync/async del body
        # quede visible en vez de pisarse (D-17).
        _write_schema_snapshot(
            endpoint="POST /calendar/config/preview",
            client_function="preview_calendar_config_async_response",
            raw=body_first,
            base_url=base_url,
            surface="async",
        )
        n_narrow_warnings = (
            len(narrow_body.get("warnings", [])) if isinstance(narrow_body, dict) else 0
        )
        _emit_preview_idempotency_verdict(
            surface="async", identical=body_first == body_second, base_url=base_url
        )
        changed = _config_field_diff(before, after)
        if changed:
            fid = _next_fid()
            append_finding(
                _PKG,
                fid=fid,
                class_="ERROR-MAP",
                surface="async",
                status="OPEN",
                title="POST /calendar/config/preview async modificó la config pese a 'Writes nothing'",
                expected="get_calendar_config() idéntica antes y después del preview",
                actual=f"campos que cambiaron: {changed}",
                diff=(
                    "sólo se registran NOMBRES de campo, nunca valores (T-27-30); "
                    "si el preview persiste, la config compartida de develop quedó alterada"
                ),
                base_url=base_url,
            )
            return ProbeResult(name, "FINDING", f"{fid} (OPEN)")
        return ProbeResult(
            name,
            "PASS",
            (
                f"config sin cambios; doble-fire idéntico={body_first == body_second} "
                f"eco_warnings={len(previewed.warnings)} ventana_estrecha_warnings={n_narrow_warnings}"
            ),
        )
    except Exception as exc:  # D-09
        return _finding_for_exc(exc, name=name, surface="async", base_url=base_url)


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
        # Ciclo destructivo de symbols (D-05/D-15), en el mismo orden relativo que
        # sus contrapartes sync y DESPUÉS de todo el read sweep async. Los
        # identificadores son los async: las dos superficies nunca se cruzan, y
        # cada una consume del registro el id que ella misma descubrió (D-10).
        results.append(await probe_create_symbol_async(aclient))
        results.append(await probe_symbols_after_create_async(aclient))
        results.append(await probe_create_symbols_batch_async(aclient))
        results.append(await probe_update_symbol_async(aclient))
        # Ciclo de calendar (27-05): config PREVIEW-ONLY (D-06) primero — no
        # persiste nada, así que no puede perturbar la lectura de los holidays.
        results.append(await probe_preview_calendar_config_async(aclient))
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
        # Ciclo destructivo de symbols (D-05), DESPUÉS de TODO el read sweep —
        # sync arriba y async dentro de ``_async_main``. El orden es load-bearing:
        # el ingestor de develop repollea el catálogo, así que un símbolo de prueba
        # activo puede aflorar como ``last_error`` en ``/health/feed`` y derivar un
        # baseline de salud si alguna lectura corriera después de una mutación.
        results.append(probe_create_symbol_sync(client))
        results.append(probe_symbols_after_create_sync(client))
        results.append(probe_create_symbols_batch_sync(client))
        results.append(probe_update_symbol_sync(client))
        # Ciclo de calendar (27-05): config PREVIEW-ONLY (D-06) primero.
        results.append(probe_preview_calendar_config_sync(client))
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
