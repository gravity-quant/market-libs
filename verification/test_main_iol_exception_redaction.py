"""CR-01 (BLOCKER, file-wide) — ninguna excepción cruza cruda hacia un finding de ``main_iol.py``.

Un finding es un artefacto **durable y versionado en git**:
``.planning/verification/iol-client-findings.md`` está trackeado, así que lo que
se escribe ahí es permanente y se distribuye en cada push. La excepción que
llega a cada handler del driver lleva el body de error upstream adentro de su
propio mensaje, porque ``_core.raise_for_response`` lo puso ahí para beneficio
del **consumidor** que debe debuggearlo, no para el reporte. Contra una API de
brokerage autenticada ese body lleva plausiblemente identificadores de cuenta y
de instrumento.

Por lo tanto el driver puede reportar exactamente dos hechos de una excepción:
el **nombre de su clase** y su **status code** cuando es un entero. La única
clase exenta es :class:`iol_client.IOLDecodeError`, cuyos cuatro atributos
(``model``, ``field_path``, ``declared_type``, ``observed_type``) están
certificados por el docstring de ``exceptions.py`` como "tipos y rutas, **jamás**
un valor del wire" (T-29-36): redactarlos no compraría nada y le costaría al
operador cualquier forma de triagear el finding.

Este archivo codifica esa falsificación en cuatro secciones:

1. El contrato de ``main_iol._redacted_exc`` — el ÚNICO renderer sancionado del
   driver — incluyendo el caso ``IOLDecodeError`` y el caso de un ``status_code``
   no entero.
2. Extremo a extremo: probes reales manejados por un ``httpx.MockTransport`` que
   responde con un marker plantado en el body; ningún kwarg registrado de
   ``append_finding`` puede llevarlo, ni el detalle de la cascada de auth.
3. Un lock de regresión por AST sobre el fuente del driver, con control positivo
   (no-vacuidad, T-30-06-05) y control negativo (no ruido).
4. El **camino de crash**: varios probes dejan escapar por diseño todo tipo fuera
   de su ``except`` angosto (``probe_login_sync`` sólo atrapa ``IOLAuthError``,
   así que un 500 del endpoint de token escapa como ``IOLAPIError``). Sin hook,
   ese escape llega al ``sys.excepthook`` default de CPython, que renderiza el
   mensaje de la excepción a stderr — y stderr lo captura CI. Es la misma clase
   de vulnerabilidad que las secciones 1-3 cierran en los 32 sitios atrapados,
   dejada abierta en el camino no atrapado. Esta sección fija el contrato de
   ``main_iol._redacted_excepthook`` (delegación al renderer sancionado, frames
   sin cadena de causas), su instalación, y —vía subproceso— que el proceso siga
   muriendo con exit code distinto de cero.

Provenencia: ``30-VERIFICATION.md`` tercer y cuarto ciclo (BLOCKER + WARNING +
INFO), ``30-REVIEW.md`` CR-01 / CR-02 / WR-02 / WR-03 / WR-06, threats
T-30-09-01 a T-30-09-08 y T-30-10-01 a T-30-10-07.

Los tests son **offline**: sin red, sin credenciales, sin ``.env``, sin
``httpx_mock``. Todo ``Client`` se construye con un token ya fresco, así que la
capa de auth nunca emite una request y ningún valor de credencial llega al
transport.

Nota de disciplina: acá y en ``main_iol.py``, las formas de llamada prohibidas se
describen **por concepto** ("renderizar la excepción cruda", "el mensaje de la
excepción") y nunca deletreando el literal — el gate file-wide de la Task 3
grepea ``main_iol.py`` por esos literales, y un comentario que los deletree lo
invalidaría. Las tres formas sí aparecen deletreadas dentro de los fuentes
sintéticos de la sección 3, que son constantes string y por lo tanto invisibles
para el detector AST (esa inmunidad es exactamente la razón de elegir AST sobre
un grep por línea).
"""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import textwrap
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import main_iol
import pytest

from iol_client import Client, IOLAPIError, IOLAuthError, IOLDecodeError, IOLRateLimitError
from verification import findings as findings_module

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DRIVER_PATH = _REPO_ROOT / "main_iol.py"
_BASE_URL = "https://api.test"

# Token que no puede aparecer por accidente en ningún texto de finding, así que
# su presencia es prueba inequívoca de que un body cruzó la frontera hacia el
# reporte. Deliberadamente DISTINTO del de
# ``test_main_iol_raw_wire_drift.py``: si fueran iguales, un copy-paste entre
# archivos podría hacer que la aserción de uno dependiera del fixture del otro.
_WIRE_BODY_MARKER = "ZZ-MARCADOR-DE-CUERPO-DE-ERROR-ZZ"


# ---------------------------------------------------------------------------
# Fixtures — dos cinturones independientes contra escribir en artefactos reales
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolate_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Aísla el findings dir, el token cache en disco y el state del driver.

    ``_FINDINGS_DIR`` repuntado a ``tmp_path`` es el segundo cinturón: aun si
    una escritura ocurriera pese al spy de ``recorded``, no podría alcanzar
    ``.planning/verification/`` (T-30-09-05).

    ``IOL_TOKEN_CACHE_PATH`` repuntado a ``tmp_path`` impide que un ``Client``
    de test lea o escriba el cache de refresh token real del operador: el
    default de ``Client.__init__`` resuelve una ruta de ``platformdirs`` cuando
    la env var está ausente, y ``login()``/``_refresh()`` escriben ahí ante un
    grant exitoso (T-30-09-06).
    """
    monkeypatch.setattr(findings_module, "_FINDINGS_DIR", tmp_path)
    monkeypatch.setenv("IOL_TOKEN_CACHE_PATH", str(tmp_path / "token-cache.json"))
    monkeypatch.setattr(main_iol, "_auth_failed", False)
    monkeypatch.setattr(main_iol, "_auth_failure_reason", "")
    monkeypatch.setattr(main_iol, "_fid_counter", 0)


@pytest.fixture
def recorded(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Intercepta ``append_finding`` y devuelve la lista de llamadas registradas."""
    calls: list[dict[str, Any]] = []

    def _spy(pkg: str, **kwargs: Any) -> Path:
        calls.append({"pkg": pkg, **kwargs})
        return Path("unused")

    monkeypatch.setattr(main_iol, "append_finding", _spy)
    return calls


# ---------------------------------------------------------------------------
# Helpers de fixture — cliente offline, bodies con marker, censo de kwargs
# ---------------------------------------------------------------------------


def _mock_client(
    handler: Callable[[httpx.Request], httpx.Response],
    *,
    refresh_token: str | None = None,
) -> Client:
    """Construye un ``Client`` sobre un ``httpx.MockTransport``, token pre-sembrado.

    ``token=`` + ``token_expires_at=`` en el futuro hacen que
    ``_core.token_is_fresh`` devuelva ``True``, así que ``_ensure_token`` no
    dispara ninguna request de auth: el test queda offline y determinístico y
    ningún valor de credencial llega jamás al transport. ``username`` y
    ``password`` son literales dummy.

    El ``Client`` es un context manager: al cerrarse cierra también el
    ``httpx.Client`` inyectado, porque ambos comparten el mismo objeto vía
    ``self._state.http_client``.
    """
    inner = httpx.Client(transport=httpx.MockTransport(handler), base_url=_BASE_URL)
    return Client(
        base_url=_BASE_URL,
        username="u",
        password="p",
        token="tok-de-prueba",
        token_expires_at=time.time() + 3600,
        refresh_token=refresh_token,
        http_client=inner,
    )


def _error_body_with_marker() -> str:
    """Body de error con forma real de IOL, marker plantado en TODOS sus strings.

    30-REVIEW.md IN-02: plantarlo en un solo campo dejaría pasar una fuga
    parcial que reprodujera únicamente otro campo. Con el marker en cada string,
    cualquier reproducción de cualquier fragmento del body tripea el chequeo.
    """
    return json.dumps(
        {
            "cuenta": f"{_WIRE_BODY_MARKER}-cuenta-999999",
            "simbolo": f"{_WIRE_BODY_MARKER}-GGAL",
            "detalle": f"{_WIRE_BODY_MARKER}-detalle",
            "mensaje": f"{_WIRE_BODY_MARKER}-mensaje",
        }
    )


def _handler_500_with_marker(request: httpx.Request) -> httpx.Response:
    del request
    return httpx.Response(500, text=_error_body_with_marker())


def _handler_401_with_marker(request: httpx.Request) -> httpx.Response:
    del request
    return httpx.Response(401, text=_error_body_with_marker())


def _handler_connect_error(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError(_WIRE_BODY_MARKER, request=request)


def _offending_kwargs(recorded: list[dict[str, Any]]) -> list[tuple[int, str]]:
    """(índice de llamada, nombre de kwarg) para todo par cuyo valor lleve el marker.

    Coerciona cada valor con ``str()`` antes de buscar, para que un kwarg no
    string no pueda esconderlo. El invariante es sobre el **registro completo**,
    no sobre un campo puntual: una regresión en ``title``, ``diff`` o
    ``expected`` se detecta igual que una en ``actual``.
    """
    return [
        (i, key)
        for i, call in enumerate(recorded)
        for key, value in call.items()
        if _WIRE_BODY_MARKER in str(value)
    ]


class _ExceptionWithNonIntegerStatus(Exception):
    """Excepción arbitraria que expone un ``status_code`` que no es un entero.

    30-REVIEW.md WR-06: 11 de los 32 handlers del driver son ``except
    Exception``, así que el renderer recibe tipos de ``iol_client``, de ``httpx``
    y de la stdlib, presentes y futuros. Nada obliga a que un objeto que expone
    ``status_code`` exponga un ``int``, y formatear un valor arbitrario sería una
    fuga a través de la mismísima expresión escrita para evitar fugas.
    """

    def __init__(self, status_code: str) -> None:
        super().__init__("estado no entero")
        self.status_code = status_code


def _marker_bearing_exceptions() -> list[BaseException]:
    """Las excepciones cuyo mensaje SÍ carga el marker.

    ``IOLDecodeError`` no está en esta lista a propósito: sus cuatro atributos
    son reportados en pleno por contrato (T-29-36), así que plantarle el marker
    fabricaría un fallo por diseño en vez de detectar uno. Su caso propio lo
    cubre :func:`test_redacted_exc_preserves_the_decode_error_type_only_fields`.
    """
    body = _error_body_with_marker()
    return [
        IOLAPIError(500, body),
        IOLAuthError(401, body),
        IOLRateLimitError(429, body),
        httpx.ConnectError(_WIRE_BODY_MARKER),
        _ExceptionWithNonIntegerStatus(f"{_WIRE_BODY_MARKER}-status"),
    ]


# ---------------------------------------------------------------------------
# 1. Contrato del renderer sancionado — ``main_iol._redacted_exc``
# ---------------------------------------------------------------------------


def test_redacted_exc_reports_only_the_class_and_status_code() -> None:
    """Igualdad exacta, nunca substring.

    Una aserción por substring pasaría para un valor que además llevara el
    body; la exactitud ES el punto. Estas dos formas son además las que la
    suite 30-08 (``test_main_iol_raw_wire_drift.py``) ya fija por igualdad para
    ``_capture_raw_wire``, así que el renderer debe reproducirlas carácter por
    carácter.
    """
    body = _error_body_with_marker()
    assert main_iol._redacted_exc(IOLAPIError(500, body)) == "IOLAPIError status_code=500"
    assert main_iol._redacted_exc(IOLAuthError(401, body)) == "IOLAuthError status_code=401"
    assert (
        main_iol._redacted_exc(IOLRateLimitError(429, body)) == "IOLRateLimitError status_code=429"
    )


def test_redacted_exc_reports_none_when_the_exception_has_no_status_code() -> None:
    """Caso transporte: sin response, sin atributo de status."""
    exc = httpx.ConnectError(_WIRE_BODY_MARKER)
    assert main_iol._redacted_exc(exc) == "ConnectError status_code=None"


def test_redacted_exc_ignores_a_non_integer_status_code() -> None:
    """WR-06 cerrado por construcción: cualquier valor que no sea ``int`` se descarta."""
    exc = _ExceptionWithNonIntegerStatus(f"{_WIRE_BODY_MARKER}-status")
    rendered = main_iol._redacted_exc(exc)
    assert rendered == "_ExceptionWithNonIntegerStatus status_code=None"
    assert _WIRE_BODY_MARKER not in rendered


def test_redacted_exc_preserves_the_decode_error_type_only_fields() -> None:
    """WR-03: los cuatro atributos certificados wire-free sobreviven la redacción.

    Sobre-redactar es su propio modo de falla (T-30-09-03): un finding OPEN
    durable que dijera sólo "IOLDecodeError, sin status code" no le daría al
    operador ninguna forma de reproducir, triagear ni cerrar, e invitaría a una
    re-corrida con logging subido — recreando la exposición por otra vía.
    """
    exc = IOLDecodeError(
        field_path=".ultimoPrecio",
        declared_type="float",
        observed_type="str",
        model="Cotizacion",
    )
    rendered = main_iol._redacted_exc(exc)
    assert "Cotizacion" in rendered
    assert ".ultimoPrecio" in rendered
    assert "float" in rendered
    assert "observed=str" in rendered
    assert rendered != "IOLDecodeError status_code=None"


@pytest.mark.parametrize("exc", _marker_bearing_exceptions(), ids=lambda e: type(e).__name__)
def test_redacted_exc_never_carries_the_exception_message(exc: BaseException) -> None:
    """El invariante enunciado UNA vez sobre toda la clase, no re-derivado por caso."""
    rendered = main_iol._redacted_exc(exc)
    assert _WIRE_BODY_MARKER not in rendered, f"marker filtrado en: {rendered!r}"


# ---------------------------------------------------------------------------
# 2. Extremo a extremo — un probe real jamás registra un kwarg con el marker
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("handler", "expected_class", "expected_actual"),
    [
        (_handler_500_with_marker, "ERROR-MAP", "IOLAPIError status_code=500"),
        (_handler_401_with_marker, "AUTH", "IOLAuthError status_code=401"),
        (_handler_connect_error, "ERROR-MAP", "ConnectError status_code=None"),
    ],
    ids=["500", "401", "transport"],
)
def test_probe_get_quote_sync_finding_never_carries_the_upstream_body(
    recorded: list[dict[str, Any]],
    handler: Callable[[httpx.Request], httpx.Response],
    expected_class: str,
    expected_actual: str,
) -> None:
    """Los tres shapes de handler del driver, manejados por el probe real.

    ``probe_get_quote_sync`` carga las tres formas que el driver usa
    (``IOLAuthError``, ``IOLAPIError``, ``Exception``), así que un solo probe
    cubre las tres ramas contra ``_core.raise_for_response`` real en vez de
    contra excepciones construidas a mano.
    """
    with _mock_client(handler) as client:
        result, quote = main_iol.probe_get_quote_sync(client)

    assert quote is None
    assert result.status == "FINDING"
    assert len(recorded) == 1, repr(recorded)
    assert recorded[0]["class_"] == expected_class, repr(recorded)
    assert recorded[0]["actual"] == expected_actual, repr(recorded)

    offenders = _offending_kwargs(recorded)
    assert offenders == [], f"marker filtrado en (índice de llamada, kwarg): {offenders}"


def test_probe_login_sync_redacts_both_the_finding_and_the_cascade_reason(
    recorded: list[dict[str, Any]],
) -> None:
    """Un solo caso cubre un sitio BLOCKER y un sitio WARNING a la vez.

    El finding es el sink durable (CR-01); ``_auth_failure_reason`` es el sink
    transitorio que alimenta los 13 ``ProbeResult.detail`` SKIPPED downstream y
    de ahí a stdout y a los logs de CI (WR-02). Son dos sinks separados y se
    asertan por separado. El prefijo ``sync login: `` se conserva verbatim para
    que el detalle de cascada que lee el operador mantenga su forma.
    """
    with _mock_client(_handler_401_with_marker) as client:
        result = main_iol.probe_login_sync(client)

    assert main_iol._auth_failed is True
    assert result.status == "FINDING"

    assert len(recorded) == 1, repr(recorded)
    assert recorded[0]["class_"] == "AUTH", repr(recorded)
    assert recorded[0]["actual"] == "IOLAuthError status_code=401", repr(recorded)
    offenders = _offending_kwargs(recorded)
    assert offenders == [], f"marker filtrado en (índice de llamada, kwarg): {offenders}"

    reason = main_iol._auth_failure_reason
    assert _WIRE_BODY_MARKER not in reason, f"marker filtrado en la razón de cascada: {reason!r}"
    assert reason.startswith("sync login: "), f"la razón perdió su prefijo: {reason!r}"


def test_probe_refresh_token_finding_never_carries_the_upstream_body(
    recorded: list[dict[str, Any]],
) -> None:
    """El peor caso de 30-REVIEW.md: dispara tras un call autenticado en vivo.

    ``probe_refresh_token`` fuerza el expiry del token sobre una instancia ya
    autenticada y dispara una llamada real; el body de error que vuelve es el de
    una sesión autenticada contra un broker.
    """
    with _mock_client(_handler_500_with_marker, refresh_token="refresh-de-prueba") as client:
        result = main_iol.probe_refresh_token(client)

    assert result.status == "FINDING"
    assert recorded, "el probe no emitió ningún finding; el caso sería vacuo"
    offenders = _offending_kwargs(recorded)
    assert offenders == [], f"marker filtrado en (índice de llamada, kwarg): {offenders}"


# ---------------------------------------------------------------------------
# 3. Lock de regresión por AST — el patrón no puede volver en silencio
# ---------------------------------------------------------------------------
#
# Los dos fuentes sintéticos de abajo son los controles del detector. Son
# constantes string, así que las formas prohibidas que contienen son invisibles
# para ``ast.parse`` del driver — esa inmunidad es precisamente la razón de
# elegir AST sobre un grep por línea, y es lo que permite que este archivo
# contenga los patrones que prohíbe en otro lado.

_OFFENDING_SOURCE = """
def probe():
    try:
        do()
    except ValueError as exc:
        report(actual=repr(exc))
        reason = f"login: {exc}"
        append_finding("pkg", actual=exc)
        append_finding("pkg", actual=exc.message)
        append_finding("pkg", diff=f"{exc.args}")
        _render(exc)
        print(exc)
        append_finding("pkg", actual="%s" % exc)
        append_finding("pkg", actual="{}".format(exc))
        alias = exc
        report(actual=str(alias))
    except KeyError:
        report(actual=str(sys.exc_info()[1]))
"""

_COMPLIANT_SOURCE = """
def probe():
    try:
        do()
    except ValueError as exc:
        code = getattr(exc, "status_code", None)
        append_finding(
            "pkg",
            actual=_redacted_exc(exc),
            diff=f"type={type(exc).__name__} status_code={exc.status_code!r}",
        )
        note = f"code={code!r}"
        return note
"""

# Las once líneas plantadas en ``_OFFENDING_SOURCE``, **una por forma prohibida**
# y exactamente una entrada marcada por línea. ``offenders`` es un set de pares
# ``(lineno, etiqueta)`` y el control positivo asertan tanto la cantidad como la
# tupla exacta de líneas: una línea que tripe dos reglas produciría dos entradas
# con el mismo número y volvería ambigua la aserción de la tupla. Si una línea
# plantada empieza a doble-marcar, se parte en dos.
#
# El fuente arranca con un newline, así que ``def probe():`` es la línea 2.
#
#   6  -> repr() sobre el nombre bindeado                       (regla 1, ya existía)
#   7  -> interpolación f-string del nombre bindeado            (regla 2, ya existía)
#   8  -> append_finding(kwarg=<bindeado>)                      (regla 3, ya existía)
#   9  -> lectura de atributo con fuga: ``.message``            (regla 4, NUEVA)
#   10 -> lectura de atributo con fuga en f-string: ``.args``   (regla 4, NUEVA)
#   11 -> delegación a una función común                        (regla 5, NUEVA)
#   12 -> delegación a una función que imprime                  (regla 5, NUEVA)
#   13 -> formateo por porcentaje                               (regla 6, NUEVA)
#   14 -> ``.format()`` sobre el nombre bindeado                (regla 1 ampliada)
#   16 -> alias de un nivel (línea 15) luego stringificado      (regla 8, NUEVA)
#   18 -> ``sys.exc_info()`` en un handler que no bindea nombre (regla 7, NUEVA)
_OFFENDING_LINES = (6, 7, 8, 9, 10, 11, 12, 13, 14, 16, 18)

# Las once filas de la tabla de formas no detectadas de ``30-REVIEW.md`` WR-01
# (10 MISSED + 1 FLAGGED contra el detector tal como se shippeó en 30-09),
# reproducidas verbatim como fuentes sintéticos completos. Es la matriz de
# falsificación de la Task 1 de 30-11: cada fila debe producir al menos un
# offender. Vive separada de ``_OFFENDING_SOURCE`` porque aquélla pinnea líneas
# exactas (una forma por línea) mientras que esto es cobertura fila por fila,
# incluidas las variantes que comparten regla con otra fila.
_WR01_ROWS: tuple[tuple[str, str], ...] = (
    (
        "actual=exc.message",
        """
def probe():
    try:
        do()
    except ValueError as exc:
        append_finding("p", actual=exc.message)
""",
    ),
    (
        "actual=f-string de exc.message",
        """
def probe():
    try:
        do()
    except ValueError as exc:
        append_finding("p", actual=f"{exc.message}")
""",
    ),
    (
        "reason=f-string de exc.args",
        """
def probe():
    try:
        do()
    except ValueError as exc:
        reason = f"login: {exc.args}"
        return reason
""",
    ),
    (
        "formateo por porcentaje",
        """
def probe():
    try:
        do()
    except ValueError as exc:
        append_finding("p", actual="%s" % exc)
""",
    ),
    (
        "str.format sobre exc",
        """
def probe():
    try:
        do()
    except ValueError as exc:
        append_finding("p", actual="{}".format(exc))
""",
    ),
    (
        "print(exc)",
        """
def probe():
    try:
        do()
    except ValueError as exc:
        print(exc)
""",
    ),
    (
        "safe_print(exc, ...)",
        """
def probe():
    try:
        do()
    except ValueError as exc:
        safe_print(exc, secrets=[])
""",
    ),
    (
        "segundo renderer bajo otro nombre",
        """
def _render(e):
    return str(e)


def probe():
    try:
        do()
    except ValueError as exc:
        append_finding("p", actual=_render(exc))
""",
    ),
    (
        "alias de un nivel",
        """
def probe():
    try:
        do()
    except ValueError as exc:
        e2 = exc
        append_finding("p", actual=str(e2))
""",
    ),
    (
        "sys.exc_info() en handler sin nombre",
        """
def probe():
    try:
        do()
    except Exception:
        append_finding("p", actual=str(sys.exc_info()[1]))
""",
    ),
    (
        "interpolación con conversión !r (la única que ya marcaba)",
        """
def probe():
    try:
        do()
    except ValueError as exc:
        return ProbeResult("n", "FINDING", f"{exc!r}")
""",
    ),
)


# Los atributos de la excepción que exponen el body de error upstream verbatim.
# ``IOLAPIError.__init__`` (``packages/iol-client/src/iol_client/exceptions.py``)
# guarda ``resp.text`` en ``self.message`` **y** lo mete adentro del mensaje que
# le pasa a ``super().__init__``, de donde sale ``.args``: los dos son el body
# crudo, que es precisamente lo que este lock existe para mantener afuera.
# ``.response`` / ``.request`` son las formas equivalentes de ``httpx``.
#
# ``status_code`` NO está acá y su ausencia es una decisión, no un olvido:
# ``30-REVIEW.md`` WR-03 (22 lecturas inline de ``exc.status_code`` en argumentos
# ``diff=``) es un carry-forward abierto y **no escalado**, así que agregarlo
# haría fallar el lock del driver sobre 22 sitios pre-existentes. Cerrar WR-03 es
# lo que debe habilitar esa entrada, nunca al revés.
_LEAKY_EXC_ATTRS = ("message", "args", "response", "request")

# Las únicas cuatro llamadas que pueden recibir el nombre bindeado sin que eso
# cuente como fuga. ``_redacted_exc`` es el renderer sancionado de la fase
# (AD-30-09-01); las otras tres son las formas de introspección que el driver ya
# usa y que no pueden reproducir un valor del wire: ``type(<n>)`` devuelve una
# clase, ``isinstance`` un bool, y ``getattr(<n>, "status_code", None)`` un
# atributo que el propio renderer guardea con ``isinstance(..., int)``.
_SANCTIONED_DELEGATES = ("_redacted_exc", "type", "isinstance", "getattr")

# Las llamadas que convierten un objeto en texto. ``format`` cubre
# ``"...".format(<n>)`` porque :func:`_called_name` resuelve el ``func`` de un
# ``ast.Attribute`` por su ``.attr``.
_STRINGIFYING_CALLS = ("repr", "str", "format")


def _called_name(func: ast.expr) -> str | None:
    """Nombre simple al que resuelve el ``func`` de una llamada, o ``None``."""
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _bound_names(handler: ast.ExceptHandler) -> set[str]:
    """El nombre bindeado por el handler más sus alias directos de **un** nivel.

    Un alias es un ``ast.Assign`` cuyo valor es exactamente el nombre bindeado
    (``otro = exc``). Se resuelve en una sola pasada previa, así que un alias
    declarado después de su uso cuenta igual.

    **Un nivel, y sólo uno.** Una cadena (``a = exc; b = a; str(b)``) queda
    fuera: el segundo eslabón no se agrega al conjunto. Eso es una frontera
    declarada, no una omisión — ver el docstring de
    :func:`_raw_exception_renders`.
    """
    if handler.name is None:
        return set()
    bound = {handler.name}
    for node in ast.walk(handler):
        if not isinstance(node, ast.Assign):
            continue
        if not (isinstance(node.value, ast.Name) and node.value.id == handler.name):
            continue
        bound.update(target.id for target in node.targets if isinstance(target, ast.Name))
    return bound


def _raw_exception_renders(source: str) -> list[tuple[int, str]]:
    """``(lineno, etiqueta)`` por cada render crudo de la excepción bindeada.

    Toma un **string de fuente**, no un path. Es deliberado por dos razones: hace
    posibles los controles positivo y negativo de abajo, y deja que un plan
    futuro apunte el mismo detector a los otros cinco ``main_*.py`` sin
    reescribirlo (el audit de la Phase 33 que el registro de threats de 30-08 ya
    carga).

    Recorre **cada** ``ast.ExceptHandler`` — incluidos los que no bindean nombre,
    que la versión de 30-09 salteaba — y marca ocho formas:

    1. una llamada a ``repr`` / ``str`` / ``format`` que recibe el nombre
       bindeado como argumento posicional; ``format`` cubre ``"...".format(<n>)``
       porque el ``func`` se resuelve por su ``.attr``;
    2. una interpolación de f-string cuyo valor es el nombre bindeado — cubre las
       tres variantes porque la conversión (``!r`` / ``!s``) vive en un campo
       aparte del nodo y no cambia ``value``;
    3. el nombre bindeado pasado directo como valor de un keyword de
       ``append_finding`` — caso especial de la forma 5, con etiqueta propia
       porque es el sink durable y conviene que el mensaje de falla lo nombre;
    4. una lectura de :data:`_LEAKY_EXC_ATTRS` sobre el nombre bindeado
       (``<n>.message`` es literalmente ``resp.text``);
    5. **delegación no sancionada**: el nombre bindeado pasado —posicional o por
       keyword— a cualquier llamada cuyo callee no esté en
       :data:`_SANCTIONED_DELEGATES`. Esta única regla cierra ``print(<n>)``,
       ``safe_print(<n>, ...)`` y ``_render(<n>)`` donde ``_render`` stringifica,
       **sin analizar al callee**: la excepción sólo puede salir del handler por
       una de estas aristas, así que la decisión se toma donde es decidible;
    6. formateo por porcentaje (``ast.BinOp`` con ``ast.Mod``) cuyo operando
       derecho es el nombre bindeado;
    7. ``sys.exc_info()`` adentro de cualquier handler, **también** de uno que no
       bindea nombre — que es exactamente la ruta por la que se obtiene la
       excepción cuando no hay ``as``;
    8. un alias directo de un nivel (``otro = <n>``) convierte a ``otro`` en un
       nombre bindeado más para todas las reglas anteriores.

    Lo que **no** marca, a propósito:

    * ``<n>.status_code`` — ``30-REVIEW.md`` WR-03 sigue abierto y no escalado;
      marcarlo fallaría el lock sobre 22 sitios pre-existentes. Ver
      :data:`_LEAKY_EXC_ATTRS`.
    * ``type(<n>).__name__``, ``getattr(<n>, ...)``, ``isinstance(<n>, ...)`` —
      las tres formas de introspección de :data:`_SANCTIONED_DELEGATES`, ninguna
      de las cuales puede reproducir un valor del wire.
    * ``_redacted_exc(<n>)`` — el renderer sancionado (AD-30-09-01) es el destino
      *deseado*, no una fuga.
    * cualquier aparición en un docstring o comentario.

    Lo que queda **sin verificar** — que no es lo mismo que permitido, y se dice
    acá explícitamente porque la redacción anterior sugería cobertura que no
    existía (WR-01, párrafo de cierre):

    * el aliasing de más de un nivel (``a = <n>``; ``b = a``; ``str(b)``): el
      segundo eslabón es invisible;
    * el flujo de datos que **sale** del handler (guardar el nombre bindeado en
      un atributo, una lista o un global y leerlo en otro lado);
    * el cuerpo de un callee sancionado — se confía en ``_redacted_exc`` por su
      propio contrato (sección 1) y por
      :func:`_declared_exception_renderers`, no por este detector.
    """
    tree = ast.parse(source)
    offenders: set[tuple[int, str]] = set()
    for handler in ast.walk(tree):
        if not isinstance(handler, ast.ExceptHandler):
            continue
        bound_names = _bound_names(handler)
        for node in ast.walk(handler):
            if isinstance(node, ast.FormattedValue):
                if isinstance(node.value, ast.Name) and node.value.id in bound_names:
                    offenders.add((node.value.lineno, f"interpolación de {node.value.id}"))
                continue
            if isinstance(node, ast.Attribute):
                if (
                    isinstance(node.value, ast.Name)
                    and node.value.id in bound_names
                    and node.attr in _LEAKY_EXC_ATTRS
                ):
                    offenders.add((node.lineno, f"lectura de {node.value.id}.{node.attr}"))
                continue
            if isinstance(node, ast.BinOp):
                if (
                    isinstance(node.op, ast.Mod)
                    and isinstance(node.right, ast.Name)
                    and node.right.id in bound_names
                ):
                    offenders.add((node.lineno, f"formateo % sobre {node.right.id}"))
                continue
            if not isinstance(node, ast.Call):
                continue
            called = _called_name(node.func)
            if called == "exc_info":
                offenders.add((node.lineno, "sys.exc_info() dentro de un handler"))
                continue
            if called in _SANCTIONED_DELEGATES:
                continue
            passed = [arg for arg in node.args if isinstance(arg, ast.Name)]
            passed += [kw.value for kw in node.keywords if isinstance(kw.value, ast.Name)]
            leaked = [name for name in passed if name.id in bound_names]
            if not leaked:
                continue
            if called in _STRINGIFYING_CALLS:
                offenders.add((node.lineno, f"{called}() sobre {leaked[0].id}"))
                continue
            if called == "append_finding":
                keyworded = [
                    kw
                    for kw in node.keywords
                    if isinstance(kw.value, ast.Name) and kw.value.id in bound_names
                ]
                for kw in keyworded:
                    assert isinstance(kw.value, ast.Name)  # acotado por el filtro de arriba
                    offenders.add((kw.value.lineno, f"append_finding({kw.arg}={kw.value.id})"))
                if not keyworded:
                    offenders.add((leaked[0].lineno, f"append_finding({leaked[0].id})"))
                continue
            offenders.add((leaked[0].lineno, f"delegación de {leaked[0].id} a {called}()"))
    return sorted(offenders)


def test_the_detector_flags_a_synthetic_offending_source() -> None:
    """Control POSITIVO — la razón por la que este lock no es vacuo (T-30-06-05).

    Un detector que devolviera siempre una lista vacía pasaría el lock de abajo y
    no probaría nada. Este caso lo hace imposible: el fuente sintético planta una
    ocurrencia de cada una de las once formas prohibidas, y las once deben
    aparecer, en sus líneas exactas. La aserción de la tupla es lo que hace que
    un angostamiento futuro de *cualquier* regla falle acá de inmediato en vez de
    degradar en silencio la cobertura del lock (T-30-11-04).
    """
    offenders = _raw_exception_renders(_OFFENDING_SOURCE)
    assert len(offenders) == len(_OFFENDING_LINES), (
        f"el detector encontró {len(offenders)}, se esperaban {len(_OFFENDING_LINES)}: {offenders}"
    )
    assert tuple(lineno for lineno, _ in offenders) == _OFFENDING_LINES, f"{offenders}"


@pytest.mark.parametrize(("shape", "source"), _WR01_ROWS, ids=[row[0] for row in _WR01_ROWS])
def test_the_detector_flags_every_shape_of_the_review_table(shape: str, source: str) -> None:
    """Cobertura fila por fila de la tabla de WR-01 (``30-REVIEW.md``).

    El review corrió once formas realistas de fuga por el detector tal como se
    shippeó en 30-09 y **diez pasaron sin marca**. Ese conteo es la métrica que
    esta suite existe para dar vuelta: las once filas, incluidas las que
    comparten regla con otra, deben producir al menos un offender.
    """
    offenders = _raw_exception_renders(source)
    assert offenders, f"forma no detectada — {shape}"


def test_the_detector_accepts_a_synthetic_compliant_source() -> None:
    """Control NEGATIVO — un lock que sobre-marca es un lock que el próximo autor borra."""
    offenders = _raw_exception_renders(_COMPLIANT_SOURCE)
    assert offenders == [], f"el detector marcó código conforme: {offenders}"


def test_no_except_handler_in_the_driver_renders_its_exception_raw() -> None:
    """El lock: ningún handler de ``main_iol.py`` vuelca su excepción bindeada."""
    source = _DRIVER_PATH.read_text(encoding="utf-8")
    offenders = _raw_exception_renders(source)
    assert not offenders, (
        f"main_iol.py tiene {len(offenders)} sitio(s) que tripan el conjunto de reglas de "
        f"_raw_exception_renders (stringificación, interpolación, kwarg de append_finding, "
        f"lectura de un atributo con fuga, delegación no sancionada, formateo por porcentaje, "
        f"sys.exc_info() o un alias de un nivel): {offenders}. No es un conteo total de sitios "
        f"que reporten crudo — el detector cubre ese conjunto y declara su frontera en su "
        f"docstring. El body de error upstream vive adentro del mensaje de la excepción y un "
        f"finding es un artefacto durable versionado en git: la ruta sancionada es "
        f"main_iol._redacted_exc(exc), el único renderer que la fase autoriza (AD-30-09-01)."
    )


def test_the_driver_declares_exactly_one_exception_renderer() -> None:
    """AD-30-09-01 en forma ejecutable: una decisión, no 32.

    Un autor futuro que agregue un segundo renderer debe confrontar este test en
    vez de rodear al primero.
    """
    tree = ast.parse(_DRIVER_PATH.read_text(encoding="utf-8"))
    renderers = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_redacted_exc"
    ]
    assert len(renderers) == 1, f"se esperaba exactamente un _redacted_exc, hay {len(renderers)}"


# ---------------------------------------------------------------------------
# 4. Camino de crash — una excepción no atrapada tampoco filtra el body
# ---------------------------------------------------------------------------
#
# CR-02 / 30-VERIFICATION.md cuarto ciclo, truth 8. Las secciones 1-3 cubren los
# 32 sitios donde el driver ATRAPA y reporta. Varios probes, en cambio, dejan
# escapar por diseño todo lo que cae fuera de su ``except`` angosto — es el
# intent D-04 (un tipo inesperado debe abortar el run, no degradarse a finding).
# Ese escape llegaba al ``sys.excepthook`` default, que renderiza el mensaje de
# la excepción; para ``IOLAPIError`` ese mensaje es ``[<status>] <body>``, o sea
# el body de error upstream completo de una sesión de brokerage autenticada,
# escrito a stderr y capturado por los logs de CI.
#
# El hook redactado no cambia el intent: imprime y retorna, y CPython sigue
# saliendo con código distinto de cero. Lo único que cambia es el texto.


def _caught(exc: BaseException) -> BaseException:
    """Levanta y atrapa ``exc`` para que cargue un ``__traceback__`` real.

    El hook recibe el triple ``(tipo, excepción, traceback)`` que CPython le
    pasaría; construir la excepción sin levantarla dejaría ``tb=None`` y volvería
    vacua la mitad del contrato que exige frames.
    """
    try:
        raise exc
    except BaseException as caught:
        return caught


def _hook_stderr(exc: BaseException, capsys: pytest.CaptureFixture[str]) -> str:
    """Corre el hook sobre ``exc`` y devuelve lo que escribió a stderr."""
    main_iol._redacted_excepthook(type(exc), exc, exc.__traceback__)
    return capsys.readouterr().err


def test_the_excepthook_renders_only_the_sanctioned_facts(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """T-30-10-01 — el hook emite exactamente los dos hechos que ``_redacted_exc`` autoriza."""
    exc = _caught(IOLAPIError(500, _error_body_with_marker()))

    err = _hook_stderr(exc, capsys)

    assert "IOLAPIError status_code=500" in err, err
    assert _WIRE_BODY_MARKER not in err, f"marker filtrado a stderr: {err!r}"


def test_the_excepthook_still_renders_the_traceback_frames(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """No-vacuidad del caso anterior: un hook que no imprimiera nada lo pasaría vacuo.

    Los frames son contenido estático del repo (archivo, línea, función y la
    línea de fuente), nunca datos del wire ni variables locales — T-30-10-03.
    """
    exc = _caught(IOLAPIError(500, _error_body_with_marker()))

    err = _hook_stderr(exc, capsys)

    assert 'File "' in err, f"el hook no renderizó ningún frame: {err!r}"
    assert "line " in err, f"el hook no renderizó ningún frame: {err!r}"


def test_the_excepthook_does_not_render_a_chained_cause(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Falsifica toda la familia de implementaciones que renderizan la cadena.

    El helper de la stdlib que toma la excepción (o el triple de ``exc_info``)
    agrega la línea del mensaje y recorre ``__cause__``/``__context__``; el que
    toma el objeto traceback imprime frames y nada más. Un ``raise X from Y``
    donde ``Y`` carga el marker distingue ambos.
    """
    try:
        raise IOLAPIError(500, "sin marker acá") from ValueError(_error_body_with_marker())
    except IOLAPIError as exc:
        err = _hook_stderr(exc, capsys)

    assert "IOLAPIError status_code=500" in err, err
    assert _WIRE_BODY_MARKER not in err, f"la cadena de causas filtró el marker: {err!r}"


def test_the_excepthook_inherits_the_non_integer_status_guard(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """WR-06 se hereda por delegación: el hook no reimplementa la redacción (T-30-10-02)."""
    exc = _caught(_ExceptionWithNonIntegerStatus(f"{_WIRE_BODY_MARKER}-status"))

    err = _hook_stderr(exc, capsys)

    assert "_ExceptionWithNonIntegerStatus status_code=None" in err, err
    assert _WIRE_BODY_MARKER not in err, f"marker filtrado a stderr: {err!r}"


def test_the_installed_hook_survives_the_real_crash_machinery(tmp_path: Path) -> None:
    """Extremo a extremo por CPython real: sin marker en ningún sink, y exit code != 0.

    Los casos de arriba llaman al hook directamente. Éste lo instala como
    producción lo instala y deja que el intérprete lo invoque, así que también
    prueba que el crash sobrevive (D-04 / T-30-10-06): un hook que se tragara la
    excepción daría exit code 0 y convertiría un abort en un falso éxito.

    El body se construye desde una variable para que la propia línea que levanta
    no pueda cargar el marker.
    """
    child = textwrap.dedent(
        f"""
        import main_iol
        from iol_client import IOLAPIError

        main_iol._install_redacted_excepthook()
        body = {_WIRE_BODY_MARKER!r} + "-cuenta-999999"
        raise IOLAPIError(500, body)
        """
    )
    env = {
        **os.environ,
        "IOL_TOKEN_CACHE_PATH": str(tmp_path / "token-cache.json"),
    }
    proc = subprocess.run(
        [sys.executable, "-c", child],
        cwd=_REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )

    assert proc.returncode != 0, (
        "el crash fue tragado: el intent D-04 exige que el proceso muera con código != 0"
    )
    assert "ABORT: IOLAPIError status_code=500" in proc.stderr, (
        f"el hook no corrió.\n--- stderr ---\n{proc.stderr}"
    )
    assert _WIRE_BODY_MARKER not in proc.stderr, f"marker en stderr: {proc.stderr!r}"
    assert _WIRE_BODY_MARKER not in proc.stdout, f"marker en stdout: {proc.stdout!r}"


def test_the_installer_assigns_the_redacted_hook(monkeypatch: pytest.MonkeyPatch) -> None:
    """El instalador existe como función nombrada y realmente asigna ``sys.excepthook``.

    Se verifica por comportamiento, no leyendo el fuente: ``monkeypatch`` restaura
    el hook original al terminar, así que ningún otro test hereda la instalación.
    """
    monkeypatch.setattr(sys, "excepthook", sys.__excepthook__)

    main_iol._install_redacted_excepthook()

    assert sys.excepthook is main_iol._redacted_excepthook


def _main_guard_body() -> list[ast.stmt]:
    """Cuerpo del bloque ``if __name__ == "__main__":`` module-level del driver."""
    tree = ast.parse(_DRIVER_PATH.read_text(encoding="utf-8"))
    guards = [
        node
        for node in tree.body
        if isinstance(node, ast.If)
        and isinstance(node.test, ast.Compare)
        and isinstance(node.test.left, ast.Name)
        and node.test.left.id == "__name__"
    ]
    assert len(guards) == 1, f"se esperaba exactamente un guard __main__, hay {len(guards)}"
    return guards[0].body


def test_the_main_guard_installs_the_hook_before_running_main() -> None:
    """El lock: el hook queda armado ANTES de que corra cualquier código del driver.

    Un hook definido pero nunca instalado —o instalado después de ``main()``, que
    es decir nunca— falla acá. Es el análogo exacto del lock de wiring del seed
    de fids en ``verification/test_main_iol_fid_seed.py``.
    """
    body = _main_guard_body()
    called = [
        node.value.func.id
        for node in body
        if isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name)
    ]
    assert called == ["_install_redacted_excepthook", "main"], (
        f"el guard __main__ debe instalar el hook y después llamar a main(); es: {called}"
    )
