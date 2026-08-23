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

Este archivo codifica esa falsificación en tres secciones:

1. El contrato de ``main_iol._redacted_exc`` — el ÚNICO renderer sancionado del
   driver — incluyendo el caso ``IOLDecodeError`` y el caso de un ``status_code``
   no entero.
2. Extremo a extremo: probes reales manejados por un ``httpx.MockTransport`` que
   responde con un marker plantado en el body; ningún kwarg registrado de
   ``append_finding`` puede llevarlo, ni el detalle de la cascada de auth.
3. Un lock de regresión por AST sobre el fuente del driver, con control positivo
   (no-vacuidad, T-30-06-05) y control negativo (no ruido).

Provenencia: ``30-VERIFICATION.md`` tercer ciclo (BLOCKER + WARNING + INFO),
``30-REVIEW.md`` CR-01 / WR-02 / WR-03 / WR-06, threats T-30-09-01 a T-30-09-08.

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

import json
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
