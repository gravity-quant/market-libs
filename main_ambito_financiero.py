"""Driver de verificación en vivo del paquete `ambito-financiero-client` (Phase 2).

Ejecuta 7 probes nombrados que ejercen la superficie pública sync+async del
cliente contra ``mercados.ambito.com`` y producen dos artefactos
committeable: el findings markdown clasificado y el schema snapshot JSON
(DRIFT-01). Los probes corren en el orden D-13 (antibot último) y cada uno
captura sus propias excepciones para satisfacer D-04 (driver continúa todos
los probes y exit 0 salvo crash inesperado).

Uso::

    uv run --package ambito-financiero-client python main_ambito_financiero.py

No requiere credenciales: la API pública de Ámbito no usa auth. El probe
``antibot`` es **opt-in** y solo corre si se exporta ``VERIFY_ANTIBOT=1``
(D-12); sin esa variable el driver imprime ``SKIPPED`` para ese probe y
sigue. ``antibot`` es one-shot, sin retry ni sleep (D-14).

Probes en orden de ejecución (D-01 + D-13):

1. ``probe_happy_sync``           — happy path sync ``get_dollar_banco_nacion``.
2. ``probe_happy_async``          — happy path async (mismo endpoint via ``aio``).
3. ``probe_parity_sync_async``    — sync ↔ async devuelven el mismo precio.
4. ``probe_parse_decimal_adversarial`` — doble check del wire ``"1.415,00"`` (D-23).
5. ``probe_no_data``              — fecha futura levanta ``AmbitoFinancieroNoDataError``.
6. ``probe_schema_snapshot``      — DRIFT-01: escribe/compara schema JSON con D-25.
7. ``probe_antibot``              — opt-in: ``BAD_UA`` debe recibir 403.

Artefactos generados (NO commiteados en este plan; se commitean en 02-03
luego del checkpoint humano):

- ``.planning/verification/ambito-financiero-client-findings.md``
  (esqueleto creado por ``write_findings`` + appends idempotentes).
- ``.planning/verification/schemas/ambito-financiero-client/get-dollar-banco-nacion.json``
  (envelope D-21; NO se sobreescribe si difiere — D-25).
"""

from __future__ import annotations

import asyncio
import contextlib
import datetime as dt
import json
import os
from dataclasses import dataclass
from pathlib import Path

import httpx
from verification import safe_print, schema_of, write_findings
from verification.findings import append_finding

import ambito_financiero_client as ambito
from ambito_financiero_client import AsyncClient, Client
from ambito_financiero_client._core import RequestSpec
from ambito_financiero_client._parsing import parse_ar_decimal
from ambito_financiero_client.client import _raise_for_response

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

_PKG = "ambito-financiero-client"
_REPO_ROOT = Path(__file__).resolve().parent
_SCHEMA_DIR = _REPO_ROOT / ".planning" / "verification" / "schemas" / _PKG
_SCHEMA_FILE = _SCHEMA_DIR / "get-dollar-banco-nacion.json"
_ENDPOINT_TEMPLATE = "/dolarnacion/historico-general/{from}/{to}"
_EXPECTED_HEADER = ["Fecha", "Compra", "Venta"]

# Bounds D-23 plausible-range check para la venta parseada (USD/ARS).
# Hoy (2026) USD/ARS ~ 1400; 100..100000 deja amplio margen sin falsos positivos.
_VENTA_MIN: float = 100.0
_VENTA_MAX: float = 100_000.0

# Contador module-level para asignar fids deterministicamente F-01, F-02, ...
# (Discretion en la fase: counter sequence simple, no derivado del probe name).
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
# Helpers de fecha
# ---------------------------------------------------------------------------


def _last_business_day(today: dt.date) -> dt.date:
    """Lunes->viernes anterior; cualquier otro día -> el día previo."""
    d = today - dt.timedelta(days=1)
    while d.weekday() >= 5:  # 5 = sábado, 6 = domingo
        d -= dt.timedelta(days=1)
    return d


def _last_business_day_with_day_gt_12(today: dt.date) -> dt.date:
    """Día hábil anterior con ``date.day > 12`` (D-24, AMB-03).

    Descarta la ambigüedad MM/DD vs DD/MM en el wire: cualquier ``DD`` > 12 es
    inequívocamente día, no mes. Retrocede desde ``_last_business_day(today)``
    día a día hasta encontrar uno con ``day > 12``, saltando fines de semana.
    """
    d = _last_business_day(today)
    while d.day <= 12:
        d -= dt.timedelta(days=1)
        while d.weekday() >= 5:
            d -= dt.timedelta(days=1)
    return d


# ---------------------------------------------------------------------------
# Probes — orden D-13 (antibot último)
# ---------------------------------------------------------------------------


def probe_happy_sync(
    today: dt.date, client: Client
) -> tuple[ProbeResult, list[list[str]] | None]:
    """Probe 1: happy path sync de ``get_dollar_banco_nacion``.

    Llama ``client._request`` (estado resuelto en vivo; sólo lectura)
    para inspeccionar el payload crudo (``rows``) y además invoca el wrapper
    público ``ambito.get_dollar_banco_nacion`` para cross-check. Retorna el
    ``rows`` capturado para que los probes 3, 4 y 6 lo reutilicen sin
    re-pegar al servidor.
    """
    fecha = _last_business_day(today)
    base_url = client._state.base_url
    formatted = fecha.strftime("%Y-%m-%d")
    path = f"/dolarnacion/historico-general/{formatted}/{formatted}"
    try:
        # WR-03: una sola llamada HTTP por probe — capturamos ``rows`` crudo y
        # parseamos la venta directamente, en lugar de llamar al wrapper
        # ``get_dollar_banco_nacion`` que repetiría el GET al mismo endpoint.
        # Reduce el riesgo de IP-ban (T-2-06) y elimina el stale-snapshot
        # mismatch entre la shape captura y el precio cross-checked.
        resp = client._request(RequestSpec(method="GET", path=path))
        _raise_for_response(resp)
        rows = resp.json()
        if not isinstance(rows, list) or len(rows) < 2 or rows[0] != _EXPECTED_HEADER:
            fid = _next_fid()
            append_finding(
                _PKG,
                fid=fid,
                class_="SHAPE",
                surface="sync",
                status="OPEN",
                title="shape inesperada en get_dollar_banco_nacion",
                expected=f"list[list[str]] con header {_EXPECTED_HEADER!r} y >= 2 filas",
                actual=f"type={type(rows).__name__}, repr={rows!r}",
                diff="header/longitud no coincide con la expectativa del cliente",
                base_url=base_url,
            )
            return (
                ProbeResult("happy_sync", "FINDING", f"{fid} (OPEN)"),
                None,
            )
        precio = parse_ar_decimal(rows[1][2])
    except ambito.AmbitoFinancieroAuthError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ANTI-BOT",
            surface="sync",
            status="OPEN",
            title="happy_sync recibió AuthError (posible anti-bot en happy path)",
            expected="200 OK con UA por defecto",
            actual=repr(exc),
            diff=f"status_code={getattr(exc, 'status_code', None)!r}",
            base_url=base_url,
        )
        return (ProbeResult("happy_sync", "FINDING", f"{fid} (OPEN)"), None)
    except ambito.AmbitoFinancieroAPIError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title="happy_sync recibió APIError inesperado",
            expected="200 OK",
            actual=repr(exc),
            diff=f"status_code={getattr(exc, 'status_code', None)!r}",
            base_url=base_url,
        )
        return (ProbeResult("happy_sync", "FINDING", f"{fid} (OPEN)"), None)
    except Exception as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title="happy_sync falló con excepción inesperada",
            expected="200 OK + parse OK",
            actual=repr(exc),
            diff=f"type={type(exc).__name__}",
            base_url=base_url,
        )
        return (ProbeResult("happy_sync", "FINDING", f"{fid} (OPEN)"), None)
    return (ProbeResult("happy_sync", "PASS", f"precio={precio}"), rows)


async def probe_happy_async(
    today: dt.date, aclient: AsyncClient
) -> tuple[ProbeResult, float | None]:
    """Probe 2: happy path async de ``aio.get_dollar_banco_nacion``.

    Espejo de ``probe_happy_sync`` usando la superficie ``aio``. No reusa
    ``rows`` del sync — captura su propio payload via ``await aclient._request``
    para verificar el shape independientemente y devuelve sólo el ``precio``
    parseado (que el probe 3 compara contra el sync).
    """
    fecha = _last_business_day(today)
    base_url = aclient._state.base_url
    formatted = fecha.strftime("%Y-%m-%d")
    path = f"/dolarnacion/historico-general/{formatted}/{formatted}"
    try:
        # WR-03 (mirror del sync): una sola llamada HTTP — parse de la venta
        # directamente desde ``rows`` capturado. Evita doblar el tráfico
        # contra mercados.ambito.com y elimina el stale-snapshot mismatch.
        resp = await aclient._request(RequestSpec(method="GET", path=path))
        _raise_for_response(resp)
        rows = resp.json()
        if not isinstance(rows, list) or len(rows) < 2 or rows[0] != _EXPECTED_HEADER:
            fid = _next_fid()
            append_finding(
                _PKG,
                fid=fid,
                class_="SHAPE",
                surface="async",
                status="OPEN",
                title="shape inesperada en aio.get_dollar_banco_nacion",
                expected=f"list[list[str]] con header {_EXPECTED_HEADER!r} y >= 2 filas",
                actual=f"type={type(rows).__name__}, repr={rows!r}",
                diff="header/longitud no coincide con la expectativa del cliente",
                base_url=base_url,
            )
            return (ProbeResult("happy_async", "FINDING", f"{fid} (OPEN)"), None)
        precio = parse_ar_decimal(rows[1][2])
    except ambito.AmbitoFinancieroAuthError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ANTI-BOT",
            surface="async",
            status="OPEN",
            title="happy_async recibió AuthError (posible anti-bot en happy path)",
            expected="200 OK con UA por defecto",
            actual=repr(exc),
            diff=f"status_code={getattr(exc, 'status_code', None)!r}",
            base_url=base_url,
        )
        return (ProbeResult("happy_async", "FINDING", f"{fid} (OPEN)"), None)
    except ambito.AmbitoFinancieroAPIError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="async",
            status="OPEN",
            title="happy_async recibió APIError inesperado",
            expected="200 OK",
            actual=repr(exc),
            diff=f"status_code={getattr(exc, 'status_code', None)!r}",
            base_url=base_url,
        )
        return (ProbeResult("happy_async", "FINDING", f"{fid} (OPEN)"), None)
    except Exception as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="async",
            status="OPEN",
            title="happy_async falló con excepción inesperada",
            expected="200 OK + parse OK",
            actual=repr(exc),
            diff=f"type={type(exc).__name__}",
            base_url=base_url,
        )
        return (ProbeResult("happy_async", "FINDING", f"{fid} (OPEN)"), None)
    return (ProbeResult("happy_async", "PASS", f"precio={precio}"), precio)


def probe_parity_sync_async(
    today: dt.date,
    rows_sync: list[list[str]] | None,
    precio_async: float | None,
    client: Client,
) -> ProbeResult:
    """Probe 3: sync ↔ async paridad estructural y numérica.

    Compara el ``precio`` parseado desde ``rows_sync[1][2]`` con el ``precio``
    retornado por la superficie async. Si discrepan: finding
    ``SYNC-ASYNC-DRIFT`` OPEN.
    """
    if rows_sync is None or precio_async is None:
        return ProbeResult(
            "parity_sync_async",
            "SKIPPED",
            "(sync o async happy probe falló antes)",
        )
    base_url = client._state.base_url
    try:
        venta_sync = parse_ar_decimal(rows_sync[1][2])
    except Exception as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="SYNC-ASYNC-DRIFT",
            surface="both",
            status="OPEN",
            title="parity: no pude parsear el venta crudo del sync para comparar",
            expected="parse_ar_decimal(rows_sync[1][2]) -> float",
            actual=repr(exc),
            diff="el sync devolvió un payload que ni siquiera se puede re-parsear",
            base_url=base_url,
        )
        return ProbeResult("parity_sync_async", "FINDING", f"{fid} (OPEN)")
    if venta_sync != precio_async:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="SYNC-ASYNC-DRIFT",
            surface="both",
            status="OPEN",
            title="sync y async devolvieron precios distintos",
            expected=f"sync == async (={venta_sync})",
            actual=f"sync={venta_sync}, async={precio_async}",
            diff=f"delta={venta_sync - precio_async}",
            base_url=base_url,
        )
        return ProbeResult("parity_sync_async", "FINDING", f"{fid} (OPEN)")
    return ProbeResult(
        "parity_sync_async",
        "PASS",
        f"sync==async={venta_sync}",
    )


def probe_parse_decimal_adversarial(
    rows_sync: list[list[str]] | None, client: Client
) -> ProbeResult:
    """Probe 4: doble check del wire AR-decimal (D-23, AMB-02).

    Doble validación sobre ``rows_sync[1][2]``:

    - **Estructural:** el wire debe usar coma como separador decimal
      (``"1.415,00"``). Si llega ``"1415.00"`` (dot-decimal), ``parse_ar_decimal``
      lo multiplica por 100 silenciosamente -> finding ``PARAM`` OPEN.
    - **Rango plausible:** la venta parseada debe estar en
      ``[_VENTA_MIN, _VENTA_MAX]``. Fuera de rango -> finding ``SHAPE`` OPEN.
    """
    if rows_sync is None:
        return ProbeResult(
            "parse_decimal",
            "SKIPPED",
            "(happy_sync falló antes)",
        )
    base_url = client._state.base_url
    try:
        venta_raw = rows_sync[1][2]
    except (IndexError, TypeError) as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="SHAPE",
            surface="sync",
            status="OPEN",
            title="parse_decimal: shape inesperada al extraer venta_raw",
            expected="rows_sync[1][2] es str",
            actual=repr(exc),
            diff="rows_sync no tiene la forma list[list[str]] esperada",
            base_url=base_url,
        )
        return ProbeResult("parse_decimal", "FINDING", f"{fid} (OPEN)")

    if "," not in venta_raw:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="PARAM",
            surface="both",
            status="OPEN",
            title="wire emite dot-decimal en lugar de AR-decimal",
            expected="separador decimal ',' (e.g. '1.415,00')",
            actual=f"venta_raw={venta_raw!r}",
            diff="parse_ar_decimal multiplicaría silenciosamente por 100",
            base_url=base_url,
        )
        return ProbeResult("parse_decimal", "FINDING", f"{fid} (OPEN)")

    try:
        venta_parseada = parse_ar_decimal(venta_raw)
    except Exception as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="PARAM",
            surface="both",
            status="OPEN",
            title="parse_ar_decimal falló sobre venta_raw observado",
            expected=f"parse_ar_decimal({venta_raw!r}) -> float",
            actual=repr(exc),
            diff="el formato del server cambió fuera del contrato AR-decimal",
            base_url=base_url,
        )
        return ProbeResult("parse_decimal", "FINDING", f"{fid} (OPEN)")

    if not (_VENTA_MIN <= venta_parseada <= _VENTA_MAX):
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="SHAPE",
            surface="both",
            status="OPEN",
            title="venta parseada fuera de rango plausible",
            expected=f"{_VENTA_MIN} <= venta <= {_VENTA_MAX}",
            actual=f"{venta_parseada}",
            diff=f"venta_raw={venta_raw!r}",
            base_url=base_url,
        )
        return ProbeResult("parse_decimal", "FINDING", f"{fid} (OPEN)")
    return ProbeResult("parse_decimal", "PASS", f"venta={venta_parseada}")


def probe_no_data(today: dt.date, client: Client) -> ProbeResult:
    """Probe 5: una fecha futura debe levantar ``AmbitoFinancieroNoDataError``.

    Usa ``today + 60d`` (D-24) — la API pública no tiene datos del futuro,
    pero el wire podría sorprender devolviendo un payload no-vacío. Si
    levanta la excepción esperada -> PASS; si retorna un float -> finding
    ``NO-DATA`` OPEN; si levanta cualquier otra excepción -> finding
    ``ERROR-MAP`` OPEN.
    """
    fecha_futura = today + dt.timedelta(days=60)
    base_url = client._state.base_url
    try:
        returned = client.get_dollar_banco_nacion(fecha_futura)
    except ambito.AmbitoFinancieroNoDataError:
        return ProbeResult("no_data", "PASS", f"NoDataError para {fecha_futura}")
    except Exception as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title="fecha futura levantó excepción distinta de NoDataError",
            expected=f"AmbitoFinancieroNoDataError para {fecha_futura}",
            actual=repr(exc),
            diff=f"type={type(exc).__name__}",
            base_url=base_url,
        )
        return ProbeResult("no_data", "FINDING", f"{fid} (OPEN)")
    fid = _next_fid()
    append_finding(
        _PKG,
        fid=fid,
        class_="NO-DATA",
        surface="sync",
        status="OPEN",
        title="fecha futura devolvió cotización en lugar de NoDataError",
        expected=f"AmbitoFinancieroNoDataError para {fecha_futura}",
        actual=f"precio={returned}",
        diff="el server entregó datos para una fecha que no debería tenerlos",
        base_url=base_url,
    )
    return ProbeResult("no_data", "FINDING", f"{fid} (OPEN)")


def probe_schema_snapshot(
    today: dt.date,
    rows_sync: list[list[str]] | None,
    client: Client,
) -> ProbeResult:
    """Probe 6: DRIFT-01 — escribe/compara snapshot estructural del endpoint.

    En el primer run escribe ``.planning/verification/schemas/<pkg>/get-dollar-banco-nacion.json``
    con el envelope D-21. En runs subsiguientes compara el schema actual con
    el committed:

    - Iguales -> PASS sin tocar el archivo.
    - Distintos (D-25) -> **NO sobreescribe**; emite finding ``SHAPE`` OPEN.

    La promoción del schema actual a baseline requiere edición manual del
    JSON committed + re-run del driver.
    """
    if rows_sync is None:
        return ProbeResult("schema_snapshot", "SKIPPED", "(happy_sync falló antes)")
    base_url = client._state.base_url
    fecha = _last_business_day(today)
    actual_schema = schema_of(rows_sync)
    envelope: dict[str, object] = {
        "endpoint": _ENDPOINT_TEMPLATE,
        "client_function": "get_dollar_banco_nacion",
        "captured_at": dt.datetime.now(dt.UTC).isoformat(),
        "base_url": base_url,
        "sample_date": fecha.isoformat(),
        "schema": actual_schema,
    }
    _SCHEMA_DIR.mkdir(parents=True, exist_ok=True)
    if not _SCHEMA_FILE.exists():
        _SCHEMA_FILE.write_text(
            json.dumps(envelope, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return ProbeResult("schema_snapshot", "PASS", f"escrito {_SCHEMA_FILE.name}")
    committed = json.loads(_SCHEMA_FILE.read_text(encoding="utf-8"))
    if committed.get("schema") == actual_schema:
        return ProbeResult("schema_snapshot", "PASS", "schema sin drift")
    fid = _next_fid()
    append_finding(
        _PKG,
        fid=fid,
        class_="SHAPE",
        surface="both",
        status="OPEN",
        title="Schema drift en get_dollar_banco_nacion",
        expected=json.dumps(committed.get("schema"), ensure_ascii=False),
        actual=json.dumps(actual_schema, ensure_ascii=False),
        diff="comparar expected vs actual; NO se sobreescribe baseline (D-25)",
        base_url=base_url,
    )
    return ProbeResult(
        "schema_snapshot",
        "FINDING",
        f"{fid} (OPEN) — NO sobreescribe",
    )


def probe_antibot(today: dt.date, client: Client) -> ProbeResult:
    """Probe 7: anti-bot con BAD_UA (opt-in, sync, one-shot).

    Reglas (D-12/D-13/D-14/D-15/D-16/D-17/D-18):

    - Opt-in via ``VERIFY_ANTIBOT=1``; sin la var -> SKIPPED silencioso.
    - Sólo sync (D-17). El estado mutado vive en ``ambito.client``.
    - One-shot: una sola llamada, sin retry ni sleep (D-14).
    - ``BAD_UA = f"python-httpx/{httpx.__version__}"`` (D-16).
    - ``GOOD_UA`` se lee dinámicamente del estado del default Client
      (``ambito.client._get_default()._state.user_agent``) para evitar
      duplicación que se desincronice (Pitfall 8). Post-refactor 06-03: el
      constant moved to ``_state._DEFAULT_USER_AGENT`` y se materializa via
      ``_ClientState`` defaults.
    - ``try/finally`` con ``ambito.configure(user_agent=good_ua)`` en
      ``finally`` para restaurar el cliente aun ante excepción (D-15).
    - Tres ramas D-18: 403 esperado -> EXPECTED terminal; 200 OK ->
      OPEN (defensa relajada); cualquier otra cosa -> OPEN.

    Phase 15 driver migration: el estado mutado vive ahora en la instancia
    ``client`` threadeada (no en el default module-level). Mutar la UA sobre
    una instancia requiere descartar su ``httpx.Client`` cacheado para que el
    próximo request reconstruya el pool con el header nuevo (la UA se hornea
    en los headers al construir el ``httpx.Client``). El ``finally`` restaura
    la UA buena y vuelve a descartar el pool para que el resto del run use el
    cliente sano.
    """
    if os.getenv("VERIFY_ANTIBOT") != "1":
        return ProbeResult("antibot", "SKIPPED", "(opt-in via VERIFY_ANTIBOT=1)")

    fecha = _last_business_day(today)
    bad_ua = f"python-httpx/{httpx.__version__}"
    good_ua = client._state.user_agent
    base_url = client._state.base_url
    try:
        client._state.user_agent = bad_ua
        client.close()  # drop cached pool so the bad UA is baked on rebuild
        try:
            returned = client.get_dollar_banco_nacion(fecha)
        except ambito.AmbitoFinancieroAuthError as exc:
            # WR-01: AmbitoFinancieroAPIError.__init__ siempre setea
            # ``self.status_code = status_code`` (ver exceptions.py:15), así
            # que el atributo nunca es None. El fallback a ``exc.args[0]``
            # era código muerto y además incorrecto (args[0] es la string
            # formateada "[403] ..."), por eso lo eliminamos.
            status_code = exc.status_code
            if status_code == 403:
                # HARN-08 (Phase 11): idempotent_by_title=True para evitar que
                # el terminal EXPECTED se duplique cross-run con cada
                # _next_fid() distinto — content-addressed dedupe by title.
                fid = _next_fid()
                append_finding(
                    _PKG,
                    fid=fid,
                    class_="ANTI-BOT",
                    surface="sync",
                    status="EXPECTED",
                    title="UA inválido recibe 403",
                    expected="403 con UA=python-httpx/...",
                    actual="403 con UA=python-httpx/...",
                    diff="ninguno; comportamiento esperado de la defensa anti-bot",
                    base_url=base_url,
                    idempotent_by_title=True,
                )
                return ProbeResult("antibot", "FINDING", f"{fid} (EXPECTED)")
            fid = _next_fid()
            append_finding(
                _PKG,
                fid=fid,
                class_="ANTI-BOT",
                surface="sync",
                status="OPEN",
                title="UA inválido produjo AuthError con status_code != 403",
                expected="403",
                actual=f"status_code={status_code!r} ({type(exc).__name__})",
                diff=repr(exc),
                base_url=base_url,
            )
            return ProbeResult("antibot", "FINDING", f"{fid} (OPEN)")
        except Exception as exc:
            fid = _next_fid()
            append_finding(
                _PKG,
                fid=fid,
                class_="ANTI-BOT",
                surface="sync",
                status="OPEN",
                title=f"UA inválido produjo {type(exc).__name__}",
                expected="403",
                actual=repr(exc),
                diff=f"type={type(exc).__name__}",
                base_url=base_url,
            )
            return ProbeResult("antibot", "FINDING", f"{fid} (OPEN)")
        # Sin excepción -> defensa relajada (D-18 OPEN)
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ANTI-BOT",
            surface="sync",
            status="OPEN",
            title="UA inválido NO recibió 403 (defensa relajada)",
            expected="403 con UA=python-httpx/...",
            actual=f"200 OK; precio={returned}",
            diff="el server aceptó un UA tipo python-httpx",
            base_url=base_url,
        )
        return ProbeResult("antibot", "FINDING", f"{fid} (OPEN)")
    finally:
        # D-15: SIEMPRE restaurar el UA del cliente, aun ante excepción.
        client._state.user_agent = good_ua
        client.close()  # drop the bad-UA pool so the rebuilt one carries good_ua


# ---------------------------------------------------------------------------
# Async wrapper — un único asyncio.run (D-11)
# ---------------------------------------------------------------------------


async def _async_main(today: dt.date) -> tuple[ProbeResult, float | None]:
    """Compone los probes async y cierra el cliente al final (D-11).

    IN-03: el ``aclose()`` interno se envuelve en su propio try/except para
    honrar D-04 — si la limpieza del AsyncClient levanta (httpx error de red
    durante teardown, etc.), la excepción NO debe propagarse a
    ``asyncio.run(...)`` y crashear el driver. El driver siempre completa
    todos los probes y sale con exit 0 salvo crash inesperado.
    """
    aclient = AsyncClient()
    try:
        result, precio_async = await probe_happy_async(today, aclient)
    finally:
        # Pitfall 5: cerrar el AsyncClient siempre, aun ante excepción.
        # IN-03: aislar fallos durante teardown para no violar D-04 (exit 0
        # salvo crash inesperado). Errores del teardown del AsyncClient no
        # deben tirarnos abajo el run.
        with contextlib.suppress(Exception):
            await aclient.aclose()
    return result, precio_async


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------


def main() -> None:
    """Orquesta los 7 probes en el orden D-13 y emite el summary final."""
    today = dt.date.today()

    # D-03: el helper es idempotente — no-op si el archivo ya existe.
    write_findings(_PKG)

    # Phase 15 (D-01/D-02): una sola instancia sync ``Client()`` threadeada a
    # todas las probes sync; el ``AsyncClient`` vive en ``_async_main`` (D-02).
    client = Client()
    results: list[ProbeResult] = []
    try:
        # 1. happy_sync — captura rows para reutilizar en probes 3, 4, 6
        result_happy_sync, rows_sync = probe_happy_sync(today, client)
        results.append(result_happy_sync)

        # 2. happy_async — un único asyncio.run (D-11)
        result_happy_async, precio_async = asyncio.run(_async_main(today))
        results.append(result_happy_async)

        # 3. parity sync ↔ async
        results.append(probe_parity_sync_async(today, rows_sync, precio_async, client))

        # 4. parse_ar_decimal adversarial (D-23 doble check)
        results.append(probe_parse_decimal_adversarial(rows_sync, client))

        # 5. fecha futura -> NoDataError
        results.append(probe_no_data(today, client))

        # 6. schema snapshot (DRIFT-01 + D-25)
        results.append(probe_schema_snapshot(today, rows_sync, client))

        # 7. anti-bot (D-13: ÚLTIMO)
        results.append(probe_antibot(today, client))
    finally:
        # Pitfall 5 (mirror sync): cerrar el ``httpx.Client`` siempre. Aislamos
        # el teardown para no violar D-04 (exit 0 salvo crash inesperado).
        with contextlib.suppress(Exception):
            client.close()

    # Output verbatim D-02 + D-26 safe_print con secrets=[] para uniformidad.
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
