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
12. ``probe_field_type_map``                — ``schema_of`` vs ``_ASSUMED_*`` + envelope check ``"titulos"``, sobre la captura de wire CRUDO de los 4 endpoints (IOL-03 + IOL-04 detail + Pitfall 2 + CR-01).
13. ``probe_schema_snapshot``               — 4 snapshots tomados del wire CRUDO, con envelope D-21 + D-25 no-overwrite (DRIFT-01 + CR-01).
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
- **Camino de crash (CR-02, única excepción a la regla anterior):**
  ``_redacted_excepthook`` escribe a **stderr** y por eso NO pasa por
  ``safe_print`` — ``safe_print`` escribe sólo a stdout y no toma parámetro de
  archivo, y volcar la salida del crash a stdout corrompería la línea
  ``SUMMARY`` que el operador y CI parsean. El texto que el hook emite es
  libre de credenciales **por construcción**: es exactamente la salida de
  ``_redacted_exc`` (un nombre de clase más un status code entero) seguida de
  frames de traceback, que son archivo/línea/función y fuente estática del
  repo, jamás valores del wire ni variables locales.
- **El camino de crash falla CERRADO (T-30-12-01/04):** si la maquinaria de
  redacción falla a mitad de camino, el hook degrada el **texto** a un
  placeholder estático, nunca la frontera. CPython, ante un excepthook que
  levanta, cae al renderer default —que imprime ``[<status>] <body>``—, así que
  un hook sin guard sería peor que no tener hook. La llamada al renderer va
  adentro de un ``try``, y cada uno de los dos sinks de stderr va adentro de su
  propio ``contextlib.suppress``.

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
import sys
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Any

from verification import (
    divergence_capture,
    endpoint_scope,
    probe_context,
    require_env,
    safe_print,
    schema_of,
    write_findings,
    write_run_evidence,
)
from verification.findings import append_finding, max_existing_fid

import iol_client
from iol_client import (
    AsyncClient,
    Client,
    Cotizacion,
    Instrumento,
    IOLAPIError,
    IOLAuthError,
    IOLDecodeError,
    Titulo,
    _core,
)
from iol_client.client import _raise_for_response

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
#
# WR-02: **toda** entrada de estos dicts debe estar sostenida por el baseline
# committeado correspondiente bajo ``.planning/verification/schemas/iol-client/``.
# Una clave asumida que el corpus no registra emite, ahora que el probe vuelve a
# leer wire real, un finding SHAPE OPEN en cada corrida viva que ningún cambio
# upstream puede cerrar — ruido que entrena al operador a ignorar el archivo de
# findings, que es lo opuesto a lo que este harness busca.
# ``verification/test_main_iol_raw_wire_drift.py::
# test_assumed_quote_fields_are_all_present_in_committed_baseline`` lo enforcea
# offline: una entrada sin respaldo falla ahí, no en producción.
_ASSUMED_QUOTE_FIELDS: dict[str, str] = {
    "ultimoPrecio": "float",  # IOL-04: numeric, JSON number
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

# El endpoint del password grant / refresh grant (``_core.build_login_request``).
# Vive aparte de ``_ENDPOINT_TEMPLATES`` porque ese dict indexa los 4 endpoints
# que tienen schema snapshot, y ``/token`` no tiene ninguno.
_LOGIN_ENDPOINT = "/token"

# Endpoint bindeado por los probes que NO hacen ninguna llamada en vivo (11, 12 y
# 13: paridad, field→type map y snapshots operan sobre modelos y wire ya
# capturados). ``"-"`` es el default del ``ContextVar`` de
# ``verification.divergences`` y significa exactamente "ningún endpoint
# bindeado"; inventarles uno atribuiría una divergencia a un endpoint que ese
# probe nunca tocó.
_NO_ENDPOINT = "-"

# Phase 33 (LIVE-TYP-01): flag del segundo pase. El runner de dos pases corre el
# driver una vez en modo observable (censo completo) y otra con
# ``MARKET_LIBS_STRICT_DECODE=1``, que prueba que el raise de modo estricto
# efectivamente dispara. Viaja como kwarg del constructor para NO agregar un
# segundo sitio de construcción: ``test_main_iol_uses_single_client_instance``
# asserta ``1 <= ctor_calls <= 2`` por AST.
_STRICT: bool = os.getenv("MARKET_LIBS_STRICT_DECODE") == "1"

# Contador module-level para asignar fids deterministicamente F-01, F-02, ...
# NO arranca en 0 en el run real: ``_seed_fid_counter()`` lo sube al máximo fid
# ya registrado antes del primer probe (D-16/D-24). Sin ese seed, cada finding
# nuevo re-emitiría un fid ya ocupado — y contra el archivo committeado, que hoy
# lleva F-01 (OPEN) y F-02 (FIXED), eso significa reescribir el triage del
# operador en el primer caso y perder el finding en silencio en el segundo,
# mientras el driver sigue reportando ``FINDING=N``.
_fid_counter: int = 0

# D-IOL-3: cascade SKIPPED — flag único compartido entre surfaces sync y async.
# Si CUALQUIER login falla, todos los downstream emiten SKIPPED.
_auth_failed: bool = False
_auth_failure_reason: str = ""


def _seed_fid_counter() -> None:
    """Sube ``_fid_counter`` al máximo fid ya registrado en el findings file (D-16/D-24).

    Debe correr DESPUÉS de ``write_findings(_PKG)`` (el bootstrap del archivo) y
    ANTES del primer probe, para que todo fid emitido en este run caiga por
    encima de lo ya escrito y realmente aterrice en el archivo.

    La falla que previene tiene dos caras, y ambas son observables hoy contra
    ``.planning/verification/iol-client-findings.md``:

    - un fid re-emitido cuyo status registrado ES ``OPEN`` (hoy ``F-01``) NO
      dispara el short-circuit de :func:`verification.findings.append_finding`:
      el bloque de detalle se **reescribe en el lugar** con contenido ajeno y el
      triage que el operador arrastró desde la Phase 17 se pierde;
    - un fid re-emitido cuyo status registrado NO es ``OPEN`` (hoy ``F-02``,
      ``FIXED``) sí dispara el short-circuit: el write se vuelve un no-op
      **silencioso** mientras ``main()`` igual lo cuenta en ``FINDING=N`` y el
      ``SUMMARY`` reporta éxito. El run pierde su entregable creyendo que
      funcionó.

    Misma forma que ``main_market_data.py::_seed_fid_counter``.
    """
    global _fid_counter
    _fid_counter = max_existing_fid(_PKG)


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
# Frontera hacia el harness de verificación (Phase 30, D-07/D-08)
# ---------------------------------------------------------------------------


def _as_wire(value: Any) -> Any:
    """Proyecta un modelo (o una lista de modelos) de vuelta a su dict de wire.

    **Un solo consumidor:** :func:`probe_parity_sync_async` (probe 11). Los
    probes 12 y 13 tenían call sites acá y los perdieron con CR-01: ahora leen
    el wire CRUDO capturado por :func:`_capture_raw_wire`, porque una proyección
    del modelo es función de la **declaración** del modelo y no del wire, y por
    lo tanto ciega al type-drift, a las claves agregadas y a las quitadas.

    Lo que la proyección sigue habilitando en el probe de paridad:
    ``verification.schema.schema_of`` reduce cualquier cosa que no sea ``dict``
    ni ``list`` al **nombre de su tipo**, así que sin este adaptador el probe
    compararía ``"Cotizacion" == "Cotizacion"``: siempre igual, PASS habiendo
    perdido todo su poder discriminante.

    **Qué prueba —y qué NO prueba— un PASS de paridad (WR-07).** Los dos lados
    son proyecciones de la *misma* clase, así que el conjunto de claves es
    idéntico por construcción y los tipos de las hojas no-opcionales también:
    esas dos clases de drift el probe **no puede** detectarlas. Lo que sí
    discrimina es la presencia de campos ``Optional`` (``None`` vs valor) y la
    cardinalidad de las listas. Un PASS acá no es evidencia de que sync y async
    hayan recibido el mismo wire; es evidencia de que produjeron modelos con la
    misma forma poblada. Un lector futuro no debe tomarlo por más de eso.

    La salida alimenta ``schema_of`` y **nada más**: esa función emite claves y
    nombres de tipo, jamás valores, y por eso es libre de datos personales por
    construcción. Ningún llamador la escribe a un archivo de findings ni
    directamente a un snapshot.
    """
    if isinstance(value, list):
        return [_as_wire(v) for v in value]
    return value.to_dict() if hasattr(value, "to_dict") else value


def _redacted_exc(exc: BaseException) -> str:
    """Única función del driver autorizada a convertir una excepción en texto de reporte.

    **Por qué existe (T-30-09-01, extiende T-30-08-01 a todo el archivo).**
    ``_core.raise_for_response`` construye ``IOLAuthError`` / ``IOLRateLimitError``
    / ``IOLAPIError`` con ``resp.text`` como mensaje: el body de error upstream
    completo queda adentro de la excepción, puesto ahí para beneficio del
    **consumidor** que debe debuggearlo, no para el reporte. Un finding, en
    cambio, es un artefacto durable versionado en git
    (``.planning/verification/iol-client-findings.md``), y contra una API de
    brokerage autenticada ese body lleva plausiblemente identificadores de cuenta
    y de instrumento. Este helper es la frontera donde esa diferencia se hace
    valer, y es **uno solo** (AD-30-09-01): con 32 sitios de reporte, una
    expresión inline sería 32 decisiones independientes que derivan — que es
    exactamente cómo nació este gap.

    **Qué se conserva y por qué.** El status code sobrevive porque es el único
    hecho que discrimina falla de auth, de rate limit, de error de servidor y de
    transporte sin ser un valor del wire: sin él, un finding OPEN durable no es
    triageable.

    **Por qué está type-guardeado.** 11 de los 32 handlers del driver son
    ``except Exception``, así que acá llegan tipos de ``iol_client``, de ``httpx``
    y de la stdlib, presentes y futuros. Nada obliga a que un objeto que expone
    ``status_code`` exponga un ``int``, y formatear un valor arbitrario sería una
    fuga a través de la mismísima expresión escrita para evitar fugas
    (30-REVIEW.md WR-06). Cualquier valor que no sea ``int`` se descarta.

    **Por qué ``IOLDecodeError`` está exento** (30-REVIEW.md WR-03): sus cuatro
    atributos ya están certificados por ``exceptions.py`` como "tipos y rutas,
    **jamás** un valor del wire" (T-29-36). Redactarlos no compraría nada y le
    costaría al operador cualquier forma de reproducir o cerrar el finding —
    sobre-redactar es su propio modo de falla (T-30-09-03).

    Nunca lee ``Exception.args`` ni ``.message``, y nunca vuelca el objeto
    excepción.
    """
    if isinstance(exc, IOLDecodeError):
        return (
            f"IOLDecodeError model={exc.model} path={exc.field_path} "
            f"declared={exc.declared_type} observed={exc.observed_type}"
        )
    raw_status = getattr(exc, "status_code", None)
    status_code = raw_status if isinstance(raw_status, int) else None
    return f"{type(exc).__name__} status_code={status_code!r}"


def _shape_probe_result(probe_name: str, surface: str, detail: str) -> ProbeResult:
    """Traduce un ``IOLDecodeError`` ya renderizado al ``ProbeResult`` canónico (P-4).

    **Por qué la interceptación va acá y no en el decorador.** A diferencia de
    higyrus y de matriz, los probes de este driver terminan en un
    ``except Exception`` propio, que atrapa el ``IOLDecodeError`` ANTES de que
    pueda llegar a ``probe_context``. Un ``decode_error=`` / ``on_decode_error=``
    sobre el decorador sería código muerto en este archivo — por eso no se pasan
    (esta nota está escrita una sola vez, acá, para que un lector futuro no
    "arregle" la omisión aparente en los 15 sitios de decorador).

    **Qué cambia respecto del ``except Exception``.** Ese handler mintea un
    finding ``ERROR-MAP`` cuyo título lleva el nombre del probe, así que dos
    probes que golpean la MISMA divergencia ``(model, field_path, kind)``
    producen dos títulos distintos y el ``idempotent_by_title`` del lock 10 no
    puede colapsarlos: cada corrida viva ensucia el censo con fids nuevos. Esta
    rama devuelve un detail derivado ÚNICAMENTE de la excepción —jamás del
    nombre del probe—, así que es idéntico entre probes para la misma
    divergencia.

    **NO escribe un finding**, y eso es deliberado (33-01-SUMMARY.md, contrato
    de ``on_decode_error``): el ``SHAPE`` ya lo escribió
    :class:`verification.divergences.DivergenceHandler` a partir del record que
    ``_decode`` emitió justo antes de levantar, bajo el título determinístico de
    la convención lockeada ``surface-in-title-write-new``. Mintear otro acá
    duplicaría la divergencia bajo un segundo título y rompería el mismísimo
    ``idempotent_by_title`` que esta rama existe para habilitar.

    **Recibe texto ya renderizado, NO la excepción**, y eso es load-bearing:
    es exactamente el mismo contrato que :func:`_emit_crash_report` documenta
    desde 30-12. Un helper que tomara la excepción se volvería un **segundo**
    renderer bajo el censo de AD-30-09-01
    (``test_the_driver_declares_exactly_one_exception_renderer``), y además cada
    ``except`` que se la pasara sería una delegación no sancionada bajo
    ``test_no_except_handler_in_the_driver_renders_its_exception_raw``. Los 12
    sitios de llamada renderizan con :func:`_redacted_exc` —el único renderer
    sancionado— y le entregan el ``str``. Para un ``IOLDecodeError`` ese renderer
    emite exactamente ``model`` / ``field_path`` / ``declared_type`` /
    ``observed_type``: los cuatro atributos certificados type-and-path-only por
    T-29-36, y nada más.
    """
    return ProbeResult(probe_name.removeprefix("probe_"), "FINDING", f"SHAPE [{surface}] {detail}")


def _shape_probe_result_pair(
    probe_name: str, surface: str, detail: str
) -> tuple[ProbeResult, None]:
    """Variante 2-tuple de :func:`_shape_probe_result` para los probes con payload.

    ``main_iol.py`` tiene DOS formas canónicas de retorno de probe, no una: los 8
    probes que alimentan el batch de paridad (quote, historical, instruments,
    by_type — sync y async) devuelven ``(ProbeResult, payload | None)``, mientras
    que login, parity, field_type_map, schema_snapshot, refresh_token y auth_401
    devuelven un ``ProbeResult`` pelado. Un único fallback con forma de 2-tuple
    haría que ``results.append(probe_auth_401(client))`` metiera una tupla en una
    ``list[ProbeResult]`` y el ``r.name`` del loop de impresión reventara con
    ``AttributeError`` — bajo modo estricto, exactamente el crash que este plan
    existe para eliminar. Mismo par de helpers que ``main_matriz.py`` y
    ``main_higyrus.py`` (33-04 lee los tres).
    """
    return (_shape_probe_result(probe_name, surface, detail), None)


def _capture_raw_wire(client: Client, today: dt.date) -> tuple[dict[str, Any], list[str]]:
    """Captura el body CRUDO de los 4 endpoints, una vez cada uno (CR-01).

    Devuelve ``(raw_by_endpoint, capture_fids)``. Las claves de
    ``raw_by_endpoint`` son las 4 de ``_SCHEMA_FILES``. Un endpoint cuya captura
    levantó queda **ausente** del dict — ausente, no ``None``, para que aguas
    abajo no se pueda confundir "no capturado" con "capturado como null".

    **Por qué existe (CR-01 / 30-VERIFICATION.md truth 6):** los wrappers
    públicos devuelven modelos. Para cuando un modelo existe, el walker de la
    Phase 29 ya coercionó cada campo no-opcional a su tipo declarado y descartó
    cada clave que ningún campo declara, así que ``schema_of`` sobre la
    proyección del modelo es función de la **declaración**, no del wire: un
    ``float→str``, una clave agregada y una clave quitada son las tres
    invisibles. Los probes de drift deben volver a ser función de lo que la API
    efectivamente devolvió.

    Esto generaliza —no inventa— la excepción ya razonada como "la ÚNICA HTTP
    call duplicada permitida (Pitfall 2)": el mismo argumento, descubierto
    aplicable a tres endpoints más. Costo: 3 GET autenticados extra por corrida
    viva, sobre un token ya cacheado por la disciplina auth-once.

    Los ``RequestSpec`` se construyen con los **builders de ``_core``**, no con
    paths hardcodeados: así el body capturado es el body que el wrapper habría
    recibido, y un drift en el builder mismo no puede quedar enmascarado por una
    captura que reproduce un path viejo.

    Discipline de datos (T-30-06-01 + T-30-08-01): el body crudo alimenta
    ``schema_of`` y nada más. Ningún argumento de ``append_finding`` recibe un
    body — tampoco en la rama de falla. La excepción que llega al ``except``
    de abajo lleva el body de error upstream adentro de su propio mensaje,
    porque ``_core.raise_for_response`` lo puso ahí para el consumidor, no
    para el reporte; por eso el handler reporta sólo la clase de la excepción
    y su status code, y se detiene ahí. Esto satisface T-29-36
    (``exceptions.py``: "tipos y rutas, jamás un valor del wire") en la rama
    de falla tal como ya valía en la de éxito.
    """
    if _auth_failed:
        # D-IOL-3: los probes 12 y 13 conservan sus propias ramas SKIPPED por
        # _auth_failed, así que la cascada no cambia.
        return ({}, [])

    base_url = client._state.base_url
    hasta = _last_business_day(today)
    desde = hasta - dt.timedelta(days=7)
    # Parámetros idénticos a los que manda el wrapper público e idénticos a los
    # que el probe 13 documenta en ``sample_params``.
    specs: list[tuple[str, _core.RequestSpec]] = [
        (
            "get_quote",
            _core.build_get_quote_request(
                client._state, _SAMPLE_SYMBOL, mercado="bcba", plazo="t2"
            ),
        ),
        (
            "get_historical_quotes",
            _core.build_get_historical_quotes_request(
                client._state,
                _SAMPLE_SYMBOL,
                desde,
                hasta,
                mercado="bcba",
                ajustada="sinAjustar",
            ),
        ),
        (
            "get_instruments",
            _core.build_get_instruments_request(client._state, "argentina"),
        ),
        (
            "get_instruments_by_type",
            _core.build_get_instruments_by_type_request(
                client._state, _SAMPLE_INSTRUMENT_TYPE, pais="argentina"
            ),
        ),
    ]

    raw_by_endpoint: dict[str, Any] = {}
    capture_fids: list[str] = []
    for func_name, spec in specs:
        try:
            # Phase 33 (P-5): este helper toca CUATRO endpoints en una sola
            # llamada, y es el único sitio del driver que lo hace. Sin este
            # re-binding las cuatro capturas quedarían atribuidas al endpoint
            # que el probe llamador tenga bindeado —o a ``"-"``, que es el caso
            # real: ``main()`` lo invoca fuera de todo ``probe_*``.
            with endpoint_scope(_ENDPOINT_TEMPLATES[func_name]):
                # WR-08 (fuera de scope de este cierre): cada uno de estos
                # ``_request`` bindea un ``DecodeScope`` que ningún parser
                # decorado retira, porque acá no corre ningún parser. Sigue
                # inalcanzable SÓLO porque entre esta captura y el próximo
                # ``_request`` (probe 14) no hay ningún ``from_api`` suelto: los
                # probes 12 y 13 no decodifican. Un reordenamiento futuro del
                # driver debe revisarlo.
                resp = client._request(spec)
                # ``Client._request`` (D-03) devuelve el response crudo sin
                # levantar; replicamos el raise-on-error del shim module-level
                # legacy.
                if resp.is_error:
                    _raise_for_response(resp)
                raw_by_endpoint[func_name] = resp.json()
        except IOLDecodeError:
            # Rama de decode ADELANTE del handler amplio, por uniformidad con
            # los 11 sitios de probe. Hoy es INALCANZABLE y se declara como tal:
            # este helper no corre ningún parser decorado, así que ningún
            # ``walk_model`` puede levantar acá. Existe para que el hazard WR-08
            # que el docstring de arriba ya nombra —un reordenamiento que meta un
            # ``from_api`` bajo este ``DecodeScope``— aterrice como divergencia
            # de forma y no como un ``ERROR-MAP`` con título único por endpoint.
            # El finding ``SHAPE`` lo escribe el ``DivergenceHandler``; acá el
            # endpoint queda AUSENTE del dict, que es exactamente lo que el
            # docstring define como "no capturado".
            continue
        except Exception as exc:
            # Un endpoint que falla no aborta los otros tres: se registra y sigue.
            fid = _next_fid()
            append_finding(
                _PKG,
                fid=fid,
                class_="ERROR-MAP",
                surface="sync",
                status="OPEN",
                title=f"captura de wire crudo falló en {func_name}",
                expected=f"200 OK con el body crudo de {func_name} para schema_of",
                actual=_redacted_exc(exc),
                diff=f"type={type(exc).__name__}",
                base_url=base_url,
            )
            capture_fids.append(fid)
    return (raw_by_endpoint, capture_fids)


# ---------------------------------------------------------------------------
# Probes — orden D-IOL-5 (probe_auth_401 último, D-IOL-4)
# ---------------------------------------------------------------------------


@probe_context(endpoint=_LOGIN_ENDPOINT, surface="sync")
def probe_login_sync(client: Client) -> ProbeResult:
    """Probe 1: ``iol_client.login()`` (IOL-01).

    Setea ``_auth_failed`` global si falla con ``IOLAuthError`` (D-IOL-3 cascade).
    Cualquier otra excepción propaga como crash inesperado (D-04 lo permite).
    """
    global _auth_failed, _auth_failure_reason
    base_url = client._state.base_url
    try:
        client.login()
    except IOLAuthError as exc:
        _auth_failed = True
        _auth_failure_reason = f"sync login: {_redacted_exc(exc)}"
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="AUTH",
            surface="sync",
            status="OPEN",
            title="login() sync falló",
            expected="login succeeds + cached token",
            actual=_redacted_exc(exc),
            diff=f"status_code={exc.status_code!r}",
            base_url=base_url,
        )
        return ProbeResult("login_sync", "FINDING", f"{fid} (OPEN)")
    refresh = client._state.refresh_token
    return ProbeResult(
        "login_sync",
        "PASS",
        f"_token cached, _refresh_token={'<cached>' if refresh else 'NONE'}",
    )


@probe_context(endpoint=_LOGIN_ENDPOINT, surface="async")
async def probe_login_async(aclient: AsyncClient) -> ProbeResult:
    """Probe 2: ``await aclient.login()`` (IOL-01).

    Setea el mismo ``_auth_failed`` global (Discretion: flag único compartido,
    no surface-segregated — D-IOL-3 Discretion).
    """
    global _auth_failed, _auth_failure_reason
    base_url = aclient._state.base_url
    try:
        await aclient.login()
    except IOLAuthError as exc:
        _auth_failed = True
        _auth_failure_reason = f"async login: {_redacted_exc(exc)}"
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="AUTH",
            surface="async",
            status="OPEN",
            title="login() async falló",
            expected="login succeeds + cached token",
            actual=_redacted_exc(exc),
            diff=f"status_code={exc.status_code!r}",
            base_url=base_url,
        )
        return ProbeResult("login_async", "FINDING", f"{fid} (OPEN)")
    refresh = aclient._state.refresh_token
    return ProbeResult(
        "login_async",
        "PASS",
        f"_token cached, _refresh_token={'<cached>' if refresh else 'NONE'}",
    )


@probe_context(endpoint=_ENDPOINT_TEMPLATES["get_quote"], surface="sync")
def probe_get_quote_sync(client: Client) -> tuple[ProbeResult, Cotizacion | None]:
    """Probe 3: ``client.get_quote(GGAL)`` (IOL-02).

    WR-03: single HTTP call por probe. WR-01: ``exc.status_code`` typed directo.
    Sanity check de plausibility del precio (Discretion D-IOL-20).
    """
    if _auth_failed:
        return (
            ProbeResult("get_quote_sync", "SKIPPED", f"auth failed: {_auth_failure_reason}"),
            None,
        )
    base_url = client._state.base_url
    try:
        quote = client.get_quote(_SAMPLE_SYMBOL)
        # SC-1 / NOBJ-IOL-01: la cadena tipada se GASTA acá, dentro del cuerpo del
        # ``try``. La Phase 38 declaró ``Cotizacion.puntas`` como ``list[Punta]``
        # —no-Optional, con la rama de colapso NOBJ-02 cubriendo el ``null`` del
        # wire y la clave ausente—, así que ``quote.puntas[0].precioCompra`` no
        # necesita guard de nulidad: la pregunta "¿vino libro?" se hace por
        # truthiness de la lista (models.py:203-205). Un ``len()`` solo dejaría el
        # decode de ``Punta`` sin ejercitar y el probe reportaría PASS igual.
        #
        # D-09 (never-FAILED): la ubicación es load-bearing. Fuera del ``try`` un
        # eslabón roto se propagaría sin capturar y tumbaría iol-client a FAILED en
        # vez de degradar a FINDING.
        niveles_libro = len(quote.puntas)
        mejor_compra = quote.puntas[0].precioCompra if quote.puntas else None
        mejor_venta = quote.puntas[0].precioVenta if quote.puntas else None
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
            actual=_redacted_exc(exc),
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
            actual=_redacted_exc(exc),
            diff=f"status_code={exc.status_code!r}",
            base_url=base_url,
        )
        return (ProbeResult("get_quote_sync", "FINDING", f"{fid} (OPEN)"), None)
    # Rama de decode ADELANTE del handler amplio (P-4). Sin ella el
    # ``except Exception`` de abajo mintea un ``ERROR-MAP`` cuyo titulo lleva
    # el nombre del probe, y dos probes sobre la misma divergencia producen
    # dos titulos que ``idempotent_by_title`` no puede colapsar.
    except IOLDecodeError as exc:
        return _shape_probe_result_pair("get_quote_sync", "sync", _redacted_exc(exc))
    except Exception as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="sync",
            status="OPEN",
            title=f"get_quote_sync unexpected {type(exc).__name__}",
            expected="200 OK + Cotizacion",
            actual=_redacted_exc(exc),
            diff=f"type={type(exc).__name__}",
            base_url=base_url,
        )
        return (ProbeResult("get_quote_sync", "FINDING", f"{fid} (OPEN)"), None)
    # Plausibility check del precio (Discretion).
    # TYP-01: acceso por atributo tipado. El guard de tipo que envolvía esta
    # comparación desapareció por ser código muerto demostrable — ``ultimoPrecio``
    # está declarado ``float`` en ``Cotizacion`` y el walker garantiza que un
    # decimal llega al atributo (sustituye el typed-zero y reporta si el wire
    # diverge). Dejarlo puesto implicaría no creerle al tipo que esta fase
    # entrega. El guard de **ausencia** sobre ``quote`` sí se conserva: el probe
    # sigue recibiendo un valor opcional.
    ultimo = quote.ultimoPrecio
    if not (_PRICE_MIN < ultimo < _PRICE_MAX):
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
    return (
        ProbeResult(
            "get_quote_sync",
            "PASS",
            f"ultimoPrecio={ultimo!r} puntas={niveles_libro} "
            f"compra={mejor_compra!r} venta={mejor_venta!r}",
        ),
        quote,
    )


@probe_context(endpoint=_ENDPOINT_TEMPLATES["get_quote"], surface="async")
async def probe_get_quote_async(
    aclient: AsyncClient,
) -> tuple[ProbeResult, Cotizacion | None]:
    """Probe 4: ``await aclient.get_quote(GGAL)`` (IOL-02). Espejo async del probe 3."""
    if _auth_failed:
        return (
            ProbeResult("get_quote_async", "SKIPPED", f"auth failed: {_auth_failure_reason}"),
            None,
        )
    base_url = aclient._state.base_url
    try:
        quote = await aclient.get_quote(_SAMPLE_SYMBOL)
        # SC-1 / NOBJ-IOL-01: espejo exacto del sitio sync — misma cadena, misma
        # ubicación dentro del cuerpo del ``try`` (D-09), misma guarda por
        # truthiness sobre la lista.
        niveles_libro = len(quote.puntas)
        mejor_compra = quote.puntas[0].precioCompra if quote.puntas else None
        mejor_venta = quote.puntas[0].precioVenta if quote.puntas else None
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
            actual=_redacted_exc(exc),
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
            actual=_redacted_exc(exc),
            diff=f"status_code={exc.status_code!r}",
            base_url=base_url,
        )
        return (ProbeResult("get_quote_async", "FINDING", f"{fid} (OPEN)"), None)
    # Rama de decode ADELANTE del handler amplio (P-4). Sin ella el
    # ``except Exception`` de abajo mintea un ``ERROR-MAP`` cuyo titulo lleva
    # el nombre del probe, y dos probes sobre la misma divergencia producen
    # dos titulos que ``idempotent_by_title`` no puede colapsar.
    except IOLDecodeError as exc:
        return _shape_probe_result_pair("get_quote_async", "async", _redacted_exc(exc))
    except Exception as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="ERROR-MAP",
            surface="async",
            status="OPEN",
            title=f"get_quote_async unexpected {type(exc).__name__}",
            expected="200 OK + Cotizacion",
            actual=_redacted_exc(exc),
            diff=f"type={type(exc).__name__}",
            base_url=base_url,
        )
        return (ProbeResult("get_quote_async", "FINDING", f"{fid} (OPEN)"), None)
    # TYP-01: acceso por atributo tipado (espejo async del sitio sync).
    ultimo = quote.ultimoPrecio
    return (
        ProbeResult(
            "get_quote_async",
            "PASS",
            f"ultimoPrecio={ultimo!r} puntas={niveles_libro} "
            f"compra={mejor_compra!r} venta={mejor_venta!r}",
        ),
        quote,
    )


@probe_context(endpoint=_ENDPOINT_TEMPLATES["get_historical_quotes"], surface="sync")
def probe_get_historical_quotes_sync(
    client: Client,
    today: dt.date,
) -> tuple[ProbeResult, list[Cotizacion] | None]:
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
    base_url = client._state.base_url
    # D-IOL-19: ~5 días hábiles back desde el último hábil (7 calendario ≈ 5 hábiles).
    hasta = _last_business_day(today)
    desde = hasta - dt.timedelta(days=7)
    try:
        serie = client.get_historical_quotes(_SAMPLE_SYMBOL, desde, hasta)
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
            actual=_redacted_exc(exc),
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
            actual=_redacted_exc(exc),
            diff=f"status_code={exc.status_code!r}",
            base_url=base_url,
        )
        return (
            ProbeResult("get_historical_quotes_sync", "FINDING", f"{fid} (OPEN)"),
            None,
        )
    # Rama de decode ADELANTE del handler amplio (P-4). Sin ella el
    # ``except Exception`` de abajo mintea un ``ERROR-MAP`` cuyo titulo lleva
    # el nombre del probe, y dos probes sobre la misma divergencia producen
    # dos titulos que ``idempotent_by_title`` no puede colapsar.
    except IOLDecodeError as exc:
        return _shape_probe_result_pair("get_historical_quotes_sync", "sync", _redacted_exc(exc))
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
            actual=_redacted_exc(exc),
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


@probe_context(endpoint=_ENDPOINT_TEMPLATES["get_historical_quotes"], surface="async")
async def probe_get_historical_quotes_async(
    aclient: AsyncClient,
    today: dt.date,
) -> tuple[ProbeResult, list[Cotizacion] | None]:
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
    base_url = aclient._state.base_url
    hasta = _last_business_day(today)
    desde = hasta - dt.timedelta(days=7)
    try:
        serie = await aclient.get_historical_quotes(_SAMPLE_SYMBOL, desde, hasta)
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
            actual=_redacted_exc(exc),
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
            actual=_redacted_exc(exc),
            diff=f"status_code={exc.status_code!r}",
            base_url=base_url,
        )
        return (
            ProbeResult("get_historical_quotes_async", "FINDING", f"{fid} (OPEN)"),
            None,
        )
    # Rama de decode ADELANTE del handler amplio (P-4). Sin ella el
    # ``except Exception`` de abajo mintea un ``ERROR-MAP`` cuyo titulo lleva
    # el nombre del probe, y dos probes sobre la misma divergencia producen
    # dos titulos que ``idempotent_by_title`` no puede colapsar.
    except IOLDecodeError as exc:
        return _shape_probe_result_pair("get_historical_quotes_async", "async", _redacted_exc(exc))
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
            actual=_redacted_exc(exc),
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


@probe_context(endpoint=_ENDPOINT_TEMPLATES["get_instruments"], surface="sync")
def probe_get_instruments_sync(client: Client) -> tuple[ProbeResult, list[Instrumento] | None]:
    """Probe 7: ``client.get_instruments("argentina")`` (IOL-02)."""
    if _auth_failed:
        return (
            ProbeResult("get_instruments_sync", "SKIPPED", f"auth failed: {_auth_failure_reason}"),
            None,
        )
    base_url = client._state.base_url
    try:
        data = client.get_instruments("argentina")
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
            actual=_redacted_exc(exc),
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
            actual=_redacted_exc(exc),
            diff=f"status_code={exc.status_code!r}",
            base_url=base_url,
        )
        return (ProbeResult("get_instruments_sync", "FINDING", f"{fid} (OPEN)"), None)
    # Rama de decode ADELANTE del handler amplio (P-4). Sin ella el
    # ``except Exception`` de abajo mintea un ``ERROR-MAP`` cuyo titulo lleva
    # el nombre del probe, y dos probes sobre la misma divergencia producen
    # dos titulos que ``idempotent_by_title`` no puede colapsar.
    except IOLDecodeError as exc:
        return _shape_probe_result_pair("get_instruments_sync", "sync", _redacted_exc(exc))
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
            actual=_redacted_exc(exc),
            diff=f"type={type(exc).__name__}",
            base_url=base_url,
        )
        return (ProbeResult("get_instruments_sync", "FINDING", f"{fid} (OPEN)"), None)
    return (
        ProbeResult("get_instruments_sync", "PASS", f"type={type(data).__name__}"),
        data,
    )


@probe_context(endpoint=_ENDPOINT_TEMPLATES["get_instruments"], surface="async")
async def probe_get_instruments_async(
    aclient: AsyncClient,
) -> tuple[ProbeResult, list[Instrumento] | None]:
    """Probe 8: ``await aclient.get_instruments("argentina")`` (IOL-02). Espejo async."""
    if _auth_failed:
        return (
            ProbeResult("get_instruments_async", "SKIPPED", f"auth failed: {_auth_failure_reason}"),
            None,
        )
    base_url = aclient._state.base_url
    try:
        data = await aclient.get_instruments("argentina")
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
            actual=_redacted_exc(exc),
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
            actual=_redacted_exc(exc),
            diff=f"status_code={exc.status_code!r}",
            base_url=base_url,
        )
        return (ProbeResult("get_instruments_async", "FINDING", f"{fid} (OPEN)"), None)
    # Rama de decode ADELANTE del handler amplio (P-4). Sin ella el
    # ``except Exception`` de abajo mintea un ``ERROR-MAP`` cuyo titulo lleva
    # el nombre del probe, y dos probes sobre la misma divergencia producen
    # dos titulos que ``idempotent_by_title`` no puede colapsar.
    except IOLDecodeError as exc:
        return _shape_probe_result_pair("get_instruments_async", "async", _redacted_exc(exc))
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
            actual=_redacted_exc(exc),
            diff=f"type={type(exc).__name__}",
            base_url=base_url,
        )
        return (ProbeResult("get_instruments_async", "FINDING", f"{fid} (OPEN)"), None)
    return (
        ProbeResult("get_instruments_async", "PASS", f"type={type(data).__name__}"),
        data,
    )


@probe_context(endpoint=_ENDPOINT_TEMPLATES["get_instruments_by_type"], surface="sync")
def probe_get_instruments_by_type_sync(
    client: Client,
) -> tuple[ProbeResult, list[Titulo] | None]:
    """Probe 9: ``client.get_instruments_by_type("acciones")`` + sanity 6 (IOL-02/17).

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
    base_url = client._state.base_url
    try:
        wrapper_result = client.get_instruments_by_type(_SAMPLE_INSTRUMENT_TYPE)
        # SC-1 / NOBJ-IOL-01: acá ``puntas`` es un ``Punta`` **singular**, no una
        # lista (models.py D-02: la misma clave con dos formas en el mismo corpus).
        # Declarado sin ``| None``, así que ``titulo.puntas.precioCompra`` nunca
        # levanta y una guarda ``is None`` sería código muerto que contradice el
        # tipo que la Phase 38 entregó; la pregunta "¿vino libro?" se hace por
        # truthiness del Null Object, que es falsy exactamente cuando iguala a
        # ``Punta.empty()``.
        #
        # La comprensión es sobre la colección obtenida, no un ``len()``: con
        # ``len(wrapper_result)`` solo, el decode de cada ``Punta`` de cada fila
        # viajaría sin ejercitar y el probe reportaría PASS igual (WR-06). Dentro
        # del cuerpo del ``try`` por D-09.
        compras_libro = [titulo.puntas.precioCompra for titulo in wrapper_result]
        mejor_compra = compras_libro[0] if compras_libro else None
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
            actual=_redacted_exc(exc),
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
            actual=_redacted_exc(exc),
            diff=f"status_code={exc.status_code!r}",
            base_url=base_url,
        )
        return (
            ProbeResult("get_instruments_by_type_sync", "FINDING", f"{fid} (OPEN)"),
            None,
        )
    # Rama de decode ADELANTE del handler amplio (P-4). Sin ella el
    # ``except Exception`` de abajo mintea un ``ERROR-MAP`` cuyo titulo lleva
    # el nombre del probe, y dos probes sobre la misma divergencia producen
    # dos titulos que ``idempotent_by_title`` no puede colapsar.
    except IOLDecodeError as exc:
        return _shape_probe_result_pair("get_instruments_by_type_sync", "sync", _redacted_exc(exc))
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
            actual=_redacted_exc(exc),
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
            titulos = client.get_instruments_by_type(itype)
        # Rama de decode ADELANTE del handler amplio (P-4). En este loop el
        # handler amplio registra ``<type>: <NombreDeClase>``, que para una
        # divergencia de forma seria siempre el mismo string opaco
        # ``IOLDecodeError``. Se registra en cambio la divergencia
        # renderizada por el unico renderer sancionado.
        except IOLDecodeError as exc:
            bad_types.append(f"{itype}: {_redacted_exc(exc)}")
            continue
        except Exception as exc:
            # Sanity gate cubre cualquier excepción del cliente o transporte:
            # cualquiera de los 6 types que falle se registra para el finding.
            bad_types.append(f"{itype}: {type(exc).__name__}")
            continue
        # Phase 30: el wrapper devuelve ``list[Titulo]``, no ``list[dict]``. Sin
        # migrar este chequeo, los 6 types caerían en ``bad_types`` y cada
        # corrida viva emitiría un finding SHAPE espurio.
        #
        # WR-06: el chequeo discrimina **forma, no cardinalidad** — la misma
        # regla que ``_core.py::parse_get_instruments_response`` ya enuncia en
        # su docstring ("the guard discriminates shape, not cardinality"). Una
        # lista vacía es legítima: ``cauciones`` o ``letras`` fuera de horario
        # de mercado devuelven ``[]`` sin que nada esté roto. Lo que sí es
        # defecto de forma: un no-list, o una lista no vacía cuyo elemento 0 no
        # es un ``Titulo``.
        if not isinstance(titulos, list):
            bad_types.append(f"{itype}: shape={type(titulos).__name__}")
        elif titulos and not isinstance(titulos[0], Titulo):
            bad_types.append(f"{itype}: shape=list[{type(titulos[0]).__name__}]")
    if bad_types:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="SHAPE",
            surface="sync",
            status="OPEN",
            title="sanity check de InstrumentType: algún type devolvió shape inesperada",
            expected="cada InstrumentType retorna list[Titulo] (una lista vacía es válida)",
            actual=f"bad_types={bad_types!r}",
            diff="shape != list[Titulo] en algún type",
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
            f"sample={_SAMPLE_INSTRUMENT_TYPE} len={len(wrapper_result)}; 6 types OK; "
            f"compra={mejor_compra!r}",
        ),
        wrapper_result,
    )


@probe_context(endpoint=_ENDPOINT_TEMPLATES["get_instruments_by_type"], surface="async")
async def probe_get_instruments_by_type_async(
    aclient: AsyncClient,
) -> tuple[ProbeResult, list[Titulo] | None]:
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
    base_url = aclient._state.base_url
    try:
        wrapper_result = await aclient.get_instruments_by_type(_SAMPLE_INSTRUMENT_TYPE)
        # SC-1 / NOBJ-IOL-01: espejo exacto del sitio sync — ``Punta`` singular,
        # rama por truthiness del Null Object, comprensión sobre la colección
        # obtenida y no un ``len()``, todo dentro del cuerpo del ``try`` (D-09).
        compras_libro = [titulo.puntas.precioCompra for titulo in wrapper_result]
        mejor_compra = compras_libro[0] if compras_libro else None
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
            actual=_redacted_exc(exc),
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
            actual=_redacted_exc(exc),
            diff=f"status_code={exc.status_code!r}",
            base_url=base_url,
        )
        return (
            ProbeResult("get_instruments_by_type_async", "FINDING", f"{fid} (OPEN)"),
            None,
        )
    # Rama de decode ADELANTE del handler amplio (P-4). Sin ella el
    # ``except Exception`` de abajo mintea un ``ERROR-MAP`` cuyo titulo lleva
    # el nombre del probe, y dos probes sobre la misma divergencia producen
    # dos titulos que ``idempotent_by_title`` no puede colapsar.
    except IOLDecodeError as exc:
        return _shape_probe_result_pair(
            "get_instruments_by_type_async", "async", _redacted_exc(exc)
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
            actual=_redacted_exc(exc),
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
            f"sample={_SAMPLE_INSTRUMENT_TYPE} len={len(wrapper_result)}; compra={mejor_compra!r}",
        ),
        wrapper_result,
    )


# ---------------------------------------------------------------------------
# Probes 11-15: parity, field_type_map, schema_snapshot, refresh_token, auth_401
# ---------------------------------------------------------------------------


@probe_context(endpoint=_NO_ENDPOINT, surface="sync")
def probe_parity_sync_async(
    client: Client,
    quote_sync: Cotizacion | None,
    quote_async: Cotizacion | None,
    historical_sync: list[Cotizacion] | None,
    historical_async: list[Cotizacion] | None,
    instruments_sync: list[Instrumento] | None,
    instruments_async: list[Instrumento] | None,
    by_type_sync: list[Titulo] | None,
    by_type_async: list[Titulo] | None,
) -> ProbeResult:
    """Probe 11: paridad estructural sync↔async (IOL-06, D-IOL-20).

    Compara ``schema_of(sync) == schema_of(async)`` por endpoint; NO compara
    valores (precios pueden cambiar entre dos calls).
    """
    if _auth_failed:
        return ProbeResult("parity_sync_async", "SKIPPED", f"auth failed: {_auth_failure_reason}")
    base_url = client._state.base_url
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
        # D-07/D-08: los payloads llegan como modelos o listas de modelos, así
        # que la normalización va acá, en la frontera. Sin ella este probe
        # compararía dos veces el mismo nombre de clase y reportaría PASS
        # habiendo perdido todo su poder discriminante. Alcance real del PASS
        # (WR-07): ver el docstring de ``_as_wire`` — claves y tipos de hojas
        # no-opcionales son idénticos por construcción; lo discriminante es la
        # presencia de ``Optional`` y la cardinalidad de las listas.
        schema_sync = schema_of(_as_wire(sync_data))
        schema_async = schema_of(_as_wire(async_data))
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


@probe_context(endpoint=_NO_ENDPOINT, surface="sync")
def probe_field_type_map(
    client: Client,
    raw_wire: dict[str, Any],
    capture_fids: list[str],
) -> ProbeResult:
    """Probe 12: field→type map vs ``_ASSUMED_*`` (IOL-03 + IOL-04, D-IOL-13/15).

    **Pitfall 2, generalizado por CR-01:** este probe lee el wire **crudo**
    capturado por :func:`_capture_raw_wire`, nunca el retorno del wrapper. El
    argumento original cubría un solo endpoint —el wrapper de by_type devuelve
    ``[]`` en silencio si falta la clave ``"titulos"``, ocultando el drift— y
    CR-01 lo encontró aplicable a tres más: desde la Phase 30 los wrappers
    devuelven modelos, y ``schema_of`` sobre un modelo es función de su
    **declaración**, no del wire. Un ``float→str``, una clave agregada y una
    clave quitada son las tres invisibles aguas abajo del wrapper
    (30-VERIFICATION.md truth 6). Las 4 HTTP calls duplicadas de la captura son
    la versión ampliada de la excepción ya documentada en Pitfall 2.

    ``capture_fids`` siembra ``finding_fids``: si la captura de un endpoint
    falló, este probe **no puede** reportar PASS. Un probe cuyo insumo nunca
    llegó no atestigua nada.
    """
    if _auth_failed:
        return ProbeResult("field_type_map", "SKIPPED", f"auth failed: {_auth_failure_reason}")
    base_url = client._state.base_url
    # Anti-vacuidad (T-30-06-05): una captura fallida garantiza FINDING.
    finding_fids: list[str] = list(capture_fids)
    quote_raw = raw_wire.get("get_quote")
    historical_raw = raw_wire.get("get_historical_quotes")
    # CR-01 (mitad post-cierre): lo que decide cada chequeo de acá abajo es la
    # **pertenencia de la clave**, nunca el valor. Una clave ausente significa que
    # la captura levantó y que ``_capture_raw_wire`` ya emitió su ERROR-MAP, cuyo
    # fid ya está en ``finding_fids``: no se re-reporta acá. Una clave presente
    # significa que el endpoint contestó, y entonces su cuerpo —cualquiera sea, un
    # nulo JSON incluido— es un insumo que llegó: si su forma cae fuera del
    # contrato, es un defecto que se reporta, jamás un skip silencioso. Es también
    # el mismo predicado que arma la lista ``checked`` del detalle del PASS, de
    # modo que ese detalle es veraz por construcción y no por coincidencia.
    envelope: Any = raw_wire.get("get_instruments_by_type")

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
    elif "get_instruments_by_type" in raw_wire:
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
    if "get_quote" in raw_wire:
        if not isinstance(quote_raw, dict):
            # Un tipo top-level inesperado ES un defecto de forma, no un skip.
            fid = _next_fid()
            append_finding(
                _PKG,
                fid=fid,
                class_="SHAPE",
                surface="both",
                status="OPEN",
                title="get_quote devolvió tipo top-level no-dict",
                expected="dict con los campos de la cotización",
                actual=f"type={type(quote_raw).__name__}",
                diff="el body crudo de get_quote cambió fuera del contrato dict",
                base_url=base_url,
            )
            finding_fids.append(fid)
        else:
            # CR-01: ``schema_of`` sobre el WIRE CRUDO. Sobre la proyección del
            # modelo la rama ``elif`` de type-drift de abajo es inalcanzable —
            # el walker ya coercionó el campo a su tipo declarado.
            observed = schema_of(quote_raw)
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
    if "get_historical_quotes" in raw_wire:
        if not isinstance(historical_raw, list):
            fid = _next_fid()
            append_finding(
                _PKG,
                fid=fid,
                class_="SHAPE",
                surface="both",
                status="OPEN",
                title="get_historical_quotes devolvió tipo top-level no-list",
                expected="list de rows de cotización",
                actual=f"type={type(historical_raw).__name__}",
                diff="el body crudo de get_historical_quotes cambió fuera del contrato list",
                base_url=base_url,
            )
            finding_fids.append(fid)
        elif historical_raw and not isinstance(historical_raw[0], dict):
            fid = _next_fid()
            append_finding(
                _PKG,
                fid=fid,
                class_="SHAPE",
                surface="both",
                status="OPEN",
                title="get_historical_quotes[0] no es dict",
                expected="cada row es un dict de cotización",
                actual=f"type={type(historical_raw[0]).__name__}",
                diff="el elemento 0 de la serie cambió fuera del contrato dict",
                base_url=base_url,
            )
            finding_fids.append(fid)
        elif historical_raw:
            # CR-01: ídem sobre la fila 0 del WIRE CRUDO. Una serie vacía es
            # cardinalidad, no forma: no se reporta.
            observed_row = schema_of(historical_raw[0])
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
        return ProbeResult(
            "field_type_map",
            "FINDING",
            f"{', '.join(finding_fids)} (OPEN)",
        )
    # El detalle reporta lo que efectivamente se miró, no un conteo fijo: un PASS
    # que nombra tres endpoints habiendo llegado uno es exactamente el modo de
    # falla que este plan existe para eliminar (T-30-06-05).
    checked = [
        name
        for name in ("get_quote", "get_historical_quotes", "get_instruments_by_type")
        if name in raw_wire
    ]
    return ProbeResult(
        "field_type_map",
        "PASS",
        f"{len(checked)} endpoints checked ({', '.join(checked) or 'ninguno'}), no drift",
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


@probe_context(endpoint=_NO_ENDPOINT, surface="sync")
def probe_schema_snapshot(
    client: Client,
    today: dt.date,
    raw_wire: dict[str, Any],
) -> ProbeResult:
    """Probe 13: 4 schema snapshots con envelope D-21 + D-25 (DRIFT-01 mirror).

    Los 4 payloads vienen del WIRE CRUDO capturado por
    :func:`_capture_raw_wire`. Para ``get_instruments_by_type`` eso incluye el
    envelope completo (con ``titulos``), no el unwrapped list, para detectar
    drift de la envelope key.
    """
    if _auth_failed:
        return ProbeResult("schema_snapshot", "SKIPPED", f"auth failed: {_auth_failure_reason}")
    base_url = client._state.base_url
    hasta = _last_business_day(today)
    desde = hasta - dt.timedelta(days=7)
    targets: list[tuple[str, dict[str, Any]]] = [
        (
            "get_quote",
            {"simbolo": _SAMPLE_SYMBOL, "mercado": "bcba", "plazo": "t2"},
        ),
        (
            "get_historical_quotes",
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
            {"pais": "argentina"},
        ),
        (
            "get_instruments_by_type",
            {"instrument_type": _SAMPLE_INSTRUMENT_TYPE, "pais": "argentina"},
        ),
    ]
    finding_fids: list[str] = []
    written: list[str] = []
    matched: list[str] = []
    skipped: list[str] = []
    for func_name, sample_params in targets:
        if func_name not in raw_wire:
            # CR-01 (mitad post-cierre): decide la pertenencia de la clave, nunca
            # el valor. Ausente del dict = la captura levantó; ``_capture_raw_wire``
            # ya emitió su ERROR-MAP y el probe 12 lo convierte en FINDING.
            skipped.append(func_name)
            continue
        # Clave presente = el endpoint contestó y su cuerpo llegó. Se compara
        # contra el baseline tal cual, incluso si es un nulo JSON: la forma de un
        # nulo difiere de la de todo baseline committeado, y reportar esa
        # diferencia es exactamente para lo que este probe existe.
        payload = raw_wire[func_name]
        status, detail = _write_or_check_schema(
            func_name,
            _ENDPOINT_TEMPLATES[func_name],
            sample_params,
            # CR-01: el payload crudo va TAL CUAL. El snapshot compara
            # ``schema_of(wire crudo)`` contra baselines que son ellos mismos
            # documentos ``schema_of(wire crudo)`` — la única comparación
            # like-for-like. La proyección del modelo que había acá antes hacía
            # del snapshot una función de la declaración del modelo, ciega a
            # type-drift, a claves agregadas y a claves quitadas
            # (30-VERIFICATION.md truth 6).
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


@probe_context(endpoint=_ENDPOINT_TEMPLATES["get_instruments"], surface="sync")
def probe_refresh_token(client: Client) -> ProbeResult:
    """Probe 14: verifica el fix IOL-07 in-vivo (D-IOL-11).

    Lee ``_refresh_token``, ``_token``, ``_token_expires_at`` antes/después de
    forzar expiry y disparar un call autenticado. El branch ``refresh inválido
    → password fallback`` NO se ejercita en vivo (mocked-only, D-IOL-11).
    """
    if _auth_failed:
        return ProbeResult("refresh_token", "SKIPPED", f"auth failed: {_auth_failure_reason}")
    base_url = client._state.base_url
    refresh_before = client._state.refresh_token
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
    token_before = client._state.token
    # Simulación in-vivo de expiry para forzar el branch refresh.
    # D-03 (Phase 15): write directly to the threaded ``client`` instance's
    # ``_state`` so the forced-expiry write is observed by the SAME object the
    # subsequent authenticated read uses. Writing to any other instance (e.g. a
    # throwaway default) would silently no-op the forced-refresh check.
    client._state.token_expires_at = 0.0
    try:
        client.get_instruments("argentina")
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
            actual=_redacted_exc(exc),
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
            actual=_redacted_exc(exc),
            diff=f"status_code={exc.status_code!r}",
            base_url=base_url,
        )
        return ProbeResult("refresh_token", "FINDING", f"{fid} (OPEN)")
    # Rama de decode al final de la escalera. Este probe NO tiene handler amplio,
    # y ``IOLDecodeError`` es HERMANO de ``IOLAPIError`` (los dos cuelgan de
    # ``IOLClientError``), así que ninguno de los dos brackets de arriba lo
    # atrapa: bajo modo estricto una divergencia en ``get_instruments`` mataba el
    # driver acá, en el probe 14 de 15, con los tres probes restantes sin correr.
    # Es el único sitio ALCANZABLE del driver que no estaba cubierto por un
    # handler amplio.
    except IOLDecodeError as exc:
        return _shape_probe_result("refresh_token", "sync", _redacted_exc(exc))
    token_after = client._state.token
    refresh_after = client._state.refresh_token
    expires_at_after = client._state.token_expires_at

    if refresh_after is None:
        # CR-02 + CR-01: tras CR-01, login() preserva el cached cuando el server
        # omite refresh_token. Por tanto este caso sólo puede ocurrir si
        # _refresh() viola Pitfall 3 (devuelve éxito pero descarta el cached).
        # El fallback a password ya NO puede causar este state (login() preserva).
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
            diff=(
                "_refresh() descartó refresh_token cuando el server no lo rotó "
                "(violación real de Pitfall 3 tras CR-01 fix de login())"
            ),
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

    # CR-02: la heurística "token cambió + refresh_token no None" no distingue
    # entre refresh path exitoso vs password fallback. Tras CR-01, ambos casos
    # son semánticamente válidos (login() ya preserva el cached), pero el detail
    # documenta la ambigüedad para auditoría humana.
    rotated = refresh_after != refresh_before
    refresh_note = "rotated" if rotated else "preserved (refresh path o password fallback)"
    return ProbeResult(
        "refresh_token",
        "PASS",
        f"refresh path verified — token rotated, _refresh_token={refresh_note}",
    )


@probe_context(endpoint=_LOGIN_ENDPOINT, surface="sync")
def probe_auth_401(client: Client) -> ProbeResult:
    """Probe 15: 401 con credenciales inválidas (IOL-05, D-IOL-1/2/4).

    Opt-in vía ``VERIFY_IOL_BAD_CREDS=1``. Single-shot, sin retry, sin sleep.
    try/finally SIEMPRE restaura ``IOL_PASSWORD`` original.

    CR-03: NO usar ``client.configure(...)``/``configure()`` porque resetearía
    ``token``, ``refresh_token`` y ``token_expires_at`` — esto leakearía el
    ``refresh_token`` capturado por el primer ``login()`` fuera de la lista
    ``secrets`` del summary. En vez, mutar ``client._state.password`` y
    ``client._state.token``/``token_expires_at`` directamente (preservando
    ``client._state.refresh_token`` para redaction) y restaurar también de
    forma directa.
    """
    if os.getenv("VERIFY_IOL_BAD_CREDS") != "1":
        return ProbeResult("auth_401", "SKIPPED", "(opt-in via VERIFY_IOL_BAD_CREDS=1)")
    if _auth_failed:
        return ProbeResult("auth_401", "SKIPPED", f"auth failed: {_auth_failure_reason}")

    base_url = client._state.base_url
    # D-IOL-2: lee del env, no del state cacheado del cliente (podría haberse
    # sobreescrito por otro probe).
    original_password = os.getenv("IOL_PASSWORD", "")
    bad_password = original_password + "_INVALID"
    try:
        # CR-03: mutación directa en vez de configure() — preserva
        # refresh_token (necesario para redaction en SUMMARY) y token cached.
        # Forzamos token=None + token_expires_at=0.0 para que login()
        # explícito vuelva a hacer el password grant con la bad password.
        client._state.password = bad_password
        client._state.token = None
        client._state.token_expires_at = 0.0
        try:
            client.login()  # D-IOL-1: ÚNICA llamada, sin retry/sleep/loop.
        except IOLAuthError as exc:
            # WR-01: status_code typed directo, NUNCA via fallback a args.
            status_code = exc.status_code
            if status_code == 401:
                # HARN-08 (Phase 11): idempotent_by_title=True para evitar que
                # el terminal EXPECTED se duplique cross-run con cada
                # _next_fid() distinto — content-addressed dedupe by title.
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
                    idempotent_by_title=True,
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
        # Rama de decode ADELANTE del handler amplio (P-4). Sin ella el
        # ``except Exception`` de abajo mintea un ``ERROR-MAP`` cuyo titulo lleva
        # el nombre del probe, y dos probes sobre la misma divergencia producen
        # dos titulos que ``idempotent_by_title`` no puede colapsar.
        except IOLDecodeError as exc:
            return _shape_probe_result("auth_401", "sync", _redacted_exc(exc))
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
                actual=_redacted_exc(exc),
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
        # D-IOL-2 + CR-03: SIEMPRE restaurar el password original mediante
        # mutación directa. NO usar configure(): wipearía _refresh_token y
        # rompería la lista secrets del SUMMARY. _token y _token_expires_at
        # quedan en 0/None tras el bad-creds login fallido, lo cual es correcto
        # — el probe va último (D-IOL-4), no hay probes downstream que
        # necesiten el token cacheado.
        client._state.password = original_password


# ---------------------------------------------------------------------------
# Async wrapper — un único asyncio.run (D-IOL-6, IN-03)
# ---------------------------------------------------------------------------


async def _async_main(
    today: dt.date,
) -> tuple[
    ProbeResult,
    ProbeResult,
    Cotizacion | None,
    ProbeResult,
    list[Cotizacion] | None,
    ProbeResult,
    list[Instrumento] | None,
    ProbeResult,
    list[Titulo] | None,
]:
    """Compone los probes async (2/4/6/8/10) y cierra el AsyncClient.

    D-IOL-6 + IN-03: un único event loop; ``aclose`` envuelto en
    ``contextlib.suppress(Exception)`` para honrar D-04.

    D-02 (Phase 15): construye UN único ``AsyncClient()`` y lo threadea como
    parámetro a los 5 probes async; cierra esa misma instancia en el ``finally``.
    """
    aclient = AsyncClient(strict_decode=_STRICT)
    try:
        result_login_async = await probe_login_async(aclient)
        result_quote_async, quote_async = await probe_get_quote_async(aclient)
        result_historical_async, historical_async = await probe_get_historical_quotes_async(
            aclient, today
        )
        result_instruments_async, instruments_async = await probe_get_instruments_async(aclient)
        result_by_type_async, by_type_async = await probe_get_instruments_by_type_async(aclient)
    finally:
        with contextlib.suppress(Exception):
            await aclient.aclose()
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

    # D-01 (Phase 15): construye UN único sync ``Client()`` y lo threadea como
    # parámetro a todos los probes sync. El async ``AsyncClient()`` se construye
    # dentro de ``_async_main`` (D-02, instancias separadas).
    client = Client(strict_decode=_STRICT)

    # D-03 mirror: idempotente — no-op si el archivo ya existe.
    write_findings(_PKG)

    # D-16/D-24: seedear el allocator DESPUÉS del bootstrap y ANTES del primer
    # probe, para que cada fid emitido en este run caiga por encima de lo ya
    # registrado y no pise ni sea tragado por un finding ya triageado.
    _seed_fid_counter()

    results: list[ProbeResult] = []

    # Phase 33 (LIVE-TYP-01 / D-01): el handler de divergencias se instala
    # alrededor del sweep entero — sube ``iol_client`` de NOTSET a INFO (sin eso
    # los records de especie ``extra`` se descartan antes de llegar a ningún
    # handler) y traduce cada record de seis claves a un finding ``SHAPE``.
    # ``next_fid`` recibe el slug y lo descarta: el driver ya tiene UN allocator
    # por proceso y compartirlo es lo que impide que el handler y el driver se
    # pisen los fids.
    with divergence_capture(("iol_client",), next_fid=lambda _slug: _next_fid()) as handler:
        # Probe 1: login sync (puede setear _auth_failed).
        result_login_sync = probe_login_sync(client)
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
        result_quote_sync, quote_sync = probe_get_quote_sync(client)
        results.append(result_login_async)
        results.append(result_quote_sync)
        results.append(result_quote_async)

        result_historical_sync, historical_sync = probe_get_historical_quotes_sync(client, today)
        results.append(result_historical_sync)
        results.append(result_historical_async)

        result_instruments_sync, instruments_sync = probe_get_instruments_sync(client)
        results.append(result_instruments_sync)
        results.append(result_instruments_async)

        result_by_type_sync, by_type_sync = probe_get_instruments_by_type_sync(client)
        results.append(result_by_type_sync)
        results.append(result_by_type_async)

        # Probe 11: paridad estructural sync↔async.
        results.append(
            probe_parity_sync_async(
                client,
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

        # CR-01: captura del wire CRUDO de los 4 endpoints, una vez cada uno. Los
        # probes 12 y 13 son funciones puras de este dict — no vuelven a pegarle a
        # la API — y así el drift vuelve a ser función de lo que la API devolvió y
        # no de lo que los modelos declaran.
        raw_wire, capture_fids = _capture_raw_wire(client, today)

        # Probe 12: field→type map + envelope check sobre el wire crudo.
        results.append(probe_field_type_map(client, raw_wire, capture_fids))

        # Probe 13: schema snapshots sobre el mismo wire crudo (D-25 no-overwrite).
        results.append(probe_schema_snapshot(client, today, raw_wire))

        # Probe 14: refresh_token in-vivo.
        results.append(probe_refresh_token(client))

        # CR-03: snapshot del _refresh_token cacheado ANTES de probe_auth_401, como
        # defense-in-depth — el fix de CR-03 ya preserva el cached usando mutación
        # directa en vez de configure(), pero capturar acá garantiza que aunque un
        # futuro cambio rompa esa invariante, el secret sigue redactado.
        captured_refresh_token = client._state.refresh_token

        # Probe 15: auth_401 ÚLTIMO (D-IOL-4) — opt-in, single-shot.
        results.append(probe_auth_401(client))

    # safe_print con secrets dinámicos (D-IOL-7/22): el _refresh_token capturado
    # por login() se redacta vía snapshot capturado antes de probe_auth_401
    # (CR-03) en vez de live-read, así sobrevive cualquier mutación del probe.
    secrets = [
        v
        for v in (
            os.getenv("IOL_USER"),
            os.getenv("IOL_PASSWORD"),
            captured_refresh_token,
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
    # Phase 33 (P-3 / T-33-11): ``DIVERGENCES`` es ``len(handler.seen)`` — el
    # conteo de triples distintos ``(slug, model, field_path, kind)``, LA unidad
    # del censo y la única directamente comparable contra el piso de
    # ``29-SIZING.md``. NO es el conteo de findings: con la superficie embebida
    # en el título hay ~2 findings por triple, así que ni ``FINDING=N`` ni el
    # conteo de bloques del archivo sirven para ese contraste. ``HANDLER_ERRORS``
    # es el tally de fallas del sink: un pipeline de logging que puede fallar en
    # silencio no sirve como registro de auditoría, así que el número se imprime
    # siempre — un valor distinto de cero invalida el censo de esta corrida.
    # Formato idéntico al de ``main_matriz.py`` y ``main_higyrus.py`` para que
    # 33-04 parsee una sola forma de línea.
    safe_print(
        f"SUMMARY: PASS={n_pass} FAIL={n_fail} SKIPPED={n_skip} FINDING={n_find} "
        f"DIVERGENCES={len(handler.seen)} HANDLER_ERRORS={len(handler.errors)}",
        secrets=secrets,
    )

    # Phase 39 (D-09 + D-10): la línea SUMMARY de arriba imprime el CONTEO de
    # triples y se va con el proceso. El sobre persiste los MIEMBROS —lo único
    # con lo que se puede computar la diferencia de conjuntos contra el censo—
    # y el conteo de probes, que es la evidencia positiva de que este driver
    # corrió. ``handler`` sigue ligado después del bloque ``with``, así que la
    # llamada va acá, junto al SUMMARY.
    write_run_evidence(
        _PKG,
        driver="main_iol.py",
        triples=sorted(handler.seen),
        counts={"PASS": n_pass, "FAIL": n_fail, "SKIPPED": n_skip, "FINDING": n_find},
    )


# ---------------------------------------------------------------------------
# Camino de crash — hook de excepciones no atrapadas (CR-02 / T-30-10-01)
# ---------------------------------------------------------------------------


# Texto de fallback cuando el propio renderer sancionado falla. Es una constante
# ESTÁTICA a propósito, y la staticidad es el punto: en el camino de fallback la
# maquinaria que normalmente decide qué es seguro mostrar ya falló, así que
# cualquier valor derivado de ``exc`` acá —su clase, su status, su repr— sería
# una fuga a través de la mismísima rama que existe para prevenir una.
_HOOK_RENDER_FAILED = "el render de la excepción falló; detalle suprimido a propósito"


def _emit_crash_report(detail: str, tb: TracebackType | None) -> None:
    """Escribe el reporte de crash a stderr sin que ninguna falla del sink escape.

    **Por qué existe (T-30-12-02/03).** El hook es el último frame antes del
    fallback de CPython: si algo se escapa de él, CPython imprime un banner y
    después renderiza la excepción original con el excepthook **default**, que
    para ``IOLAPIError`` / ``IOLAuthError`` / ``IOLRateLimitError`` emite
    ``[<status>] <body>``. Un stderr roto o cerrado —``... 2>&1 | head``, un
    runner de CI con el pipe cerrado— convierte cualquiera de estas dos
    escrituras en ``BrokenPipeError`` / ``ValueError``, y con stderr cerrado la
    escritura del propio fallback también falla, así que CPython cae a su ruta
    ``lost sys.stderr`` y vuelca el **repr** del objeto excepción directo al fd 2.
    Ahí no queda nada que redactar: la única defensa es que nada se escape.

    **Los dos guards son separados a propósito.** Un único ``with`` alrededor de
    las dos escrituras —o un return temprano tras la primera falla— haría que
    perder la línea de ABORT se llevara puestos también los frames, que son
    contenido estático del repo y el único material de triage que le queda al
    operador en ese escenario. Lo fija
    ``test_the_hook_still_prints_frames_when_the_abort_line_fails``, con un stream
    que falla sólo ante el prefijo del ABORT, más su espejo
    ``test_the_hook_survives_a_failing_frame_printer``.

    **Por qué ``contextlib.suppress`` y no ``try``/``except``/``pass``:** el rule
    set ``SIM`` del ruff de la raíz rechaza la segunda forma (SIM105), incluso con
    un comentario en el cuerpo del ``except``, y ``ruff check`` es un gate de CI.

    **Por qué recibe texto ya renderizado y no la excepción.** Un helper que
    tomara la excepción se volvería un **segundo** renderer bajo el censo de
    AD-30-09-01, y haría que :func:`_redacted_excepthook` pasara a leerse como un
    renderer que delega. Con ``str`` y ``TracebackType | None`` ambas funciones
    quedan clasificadas como corresponde: el único renderer sigue siendo
    :func:`_redacted_exc` y el hook sigue siendo un consumidor.

    **Suprimir acá no se traga el crash (D-04).** El hook imprime y retorna;
    CPython termina el proceso con código distinto de cero igual. Lo único que se
    pierde ante un sink roto es el texto, que ya era ilegible por definición.
    """
    with contextlib.suppress(BaseException):
        print(f"ABORT: {detail}", file=sys.stderr)
    with contextlib.suppress(BaseException):
        traceback.print_tb(tb)


def _redacted_excepthook(
    exc_type: type[BaseException], exc: BaseException, tb: TracebackType | None
) -> None:
    """Renderiza una excepción NO atrapada sin filtrar el body de error upstream.

    **Qué filtraba el default.** Varios probes dejan escapar por diseño todo tipo
    que caiga fuera de su ``except`` angosto — ``probe_login_sync`` sólo atrapa
    ``IOLAuthError``, así que un 500 del endpoint de token escapa como
    ``IOLAPIError``; ``probe_refresh_token`` no atrapa errores de transporte. Ese
    escape llegaba al ``sys.excepthook`` default de CPython, que imprime el
    **mensaje** de la excepción a stderr. Para ``IOLAPIError`` /
    ``IOLAuthError`` / ``IOLRateLimitError`` ese mensaje es ``[<status>]
    <body>``: el body de error upstream completo de una sesión de brokerage
    autenticada. stderr lo captura CI, un sink que el threat model de esta fase
    declara en scope (WR-02). Es la misma clase de vulnerabilidad que 30-08 y
    30-09 cerraron en 32 sitios atrapados, dejada abierta en el camino no
    atrapado.

    **El crash se conserva (D-04).** Este hook imprime y retorna; CPython sigue
    terminando el proceso con código distinto de cero. Un tipo inesperado debe
    abortar el run, no degradarse a finding — lo único que cambia es el texto.

    **Delega, no reimplementa (AD-30-09-01).** El único renderer sancionado del
    driver es :func:`_redacted_exc`; un segundo renderer acá sería exactamente la
    deriva que esa decisión existe para prevenir, y heredaría gratis el guard de
    ``status_code`` no entero y la exención de ``IOLDecodeError``.

    **La cadena de excepciones NO se renderiza, a propósito.** Se usa el helper
    de la stdlib que toma el objeto traceback y por lo tanto imprime **sólo
    frames** (archivo, línea, función y la línea de fuente, todo contenido
    estático del repo). Los helpers que toman la excepción o el triple de
    ``exc_info`` agregan la línea del mensaje y recorren ``__cause__`` /
    ``__context__``, reintroduciendo la fuga que esta función existe para
    eliminar. El costo es el mensaje de una causa encadenada: un costo de
    triage, no una fuga.

    **Falla CERRADO (T-30-12-01).** El contrato de CPython para un excepthook que
    levanta (``PyErr_PrintEx``) es: imprimir un banner de error más el traceback
    del propio hook, y después renderizar la excepción ORIGINAL con el excepthook
    **default** — o sea ``str(exc)``, que para ``IOLAPIError`` / ``IOLAuthError``
    / ``IOLRateLimitError`` es ``[<status>] <body>``. Un hook sin guard es por eso
    estrictamente **peor** que no tener hook para esta amenaza: emite justo lo que
    fue escrito para suprimir, y encima el operador cree que está cubierto. Tres
    triggers alcanzables lo disparan (30-VERIFICATION.md, quinto ciclo): (a) un
    ``RecursionError`` que llega con el stack casi agotado, donde el formateo o la
    extracción de frames puede levantar; (b) un stderr roto o cerrado, que
    convierte la escritura en ``BrokenPipeError``/``ValueError``; (c) un
    ``IOLDecodeError`` que nunca asignó sus cuatro atributos type-only, que hace
    levantar ``AttributeError`` adentro del renderer.

    **Por qué ``BaseException`` y no ``Exception``.** Un ``MemoryError`` o un
    ``KeyboardInterrupt`` que llegue a mitad del render tiene que quedar contenido
    igual: el contrato no es "casi nada se escapa", es que **nada** se escapa.

    **Por qué el texto de fallback es estático.** Ver :data:`_HOOK_RENDER_FAILED`:
    en esa rama la maquinaria que filtra ya falló, así que nada derivado de la
    excepción puede considerarse seguro ahí.
    """
    del exc_type  # El nombre de la clase ya viaja dentro de ``_redacted_exc``.
    try:
        detail = _redacted_exc(exc)
    except BaseException:
        detail = _HOOK_RENDER_FAILED
    _emit_crash_report(detail, tb)


def _install_redacted_excepthook() -> None:
    """Arma :func:`_redacted_excepthook` como el hook de excepciones del proceso.

    Existe como función nombrada —en vez de una asignación suelta en el guard—
    para que el test de subproceso instale el hook *exactamente* como lo hace
    producción en vez de duplicar el wiring.
    """
    sys.excepthook = _redacted_excepthook


if __name__ == "__main__":
    _install_redacted_excepthook()
    main()
