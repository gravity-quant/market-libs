"""Pin de REQUEST byte-idéntico a v0.4.0 para las dos mutaciones de feriados.

``add_holidays`` (``POST /calendar/holidays``) y ``delete_holiday``
(``DELETE /calendar/holidays/{day}``) ya están PUBLICADAS en
``market-data-client`` v0.4.0. La Phase 31 retipa sólo sus RESPUESTAS: este
módulo congela sus REQUESTS EMITIDAS como bytes crudos —método, URL completa,
set de headers y bytes del body, incluido el ORDEN DE CLAVES— para que
cualquier deriva del lado del request falle a los gritos en vez de viajar
escondida adentro de un cambio "response-only".

Provenencia (criterio 2): ``git diff market-data-client-v0.4.0 --
packages/market-data-client/src/`` muestra que los ÚNICOS cambios posteriores al
tag son el cableado del decoder de la Phase 29 —un import más 7 decoraciones de
parsers en ``_core.py``, y dos líneas de bind al tope de ``_request`` en
``client.py`` / ``aio.py``—. Ningún cuerpo de builder y ninguna línea de
construcción de request cambió. Por lo tanto los bytes que HEAD emite SON los
bytes de v0.4.0, y la captura de abajo es el pin de v0.4.0.

Vive en un módulo DEDICADO a propósito: ``test_calendar_write.py`` y su espejo
async se re-mockean en el plan 31-05, y mantener el pin afuera hace que su diff
quede vacío a través de ese re-mock — lo cual es, en sí mismo, evidencia para el
criterio 2.

Las cuatro pruebas comparan contra LOS MISMOS dos literales en las dos
superficies: esa identidad es la evidencia de paridad sync/async de request
(C-3). Literales que divergieran por superficie la anularían.
"""

from __future__ import annotations

import httpx
from pytest_httpx import HTTPXMock

import market_data_client
from market_data_client import aio
from market_data_client.models import HolidayIn, HolidaysIn

_BASE = "https://market-data-develop.test/api"
# El host que el conftest siembra en base_url (NO el default develop bbsa).
_CONFTEST_HOST = "market-data-develop.test"

# Payload EXACTO que RESEARCH ejecutó para capturar las tuplas. El día y la
# descripción NO se cambian: el literal de ``Content-Length`` se deriva de ellos.
_PROBE_DAY = "2099-12-29"


def _probe_holidays() -> HolidaysIn:
    return HolidaysIn([HolidayIn(_PROBE_DAY, description="probe")])


def _open_gate() -> None:
    """Abre el gate del singleton default sync para el host del conftest."""
    market_data_client.configure(mutating_allowed=True, expected_host=_CONFTEST_HOST)


def _open_gate_async() -> None:
    """Abre el gate del singleton default async para el host del conftest."""
    aio.configure(mutating_allowed=True, expected_host=_CONFTEST_HOST)


# Hazard 1, RESUELTO acá: ``user-agent`` se queda ADENTRO del set congelado pero
# con el valor DERIVADO, no hard-pineado. Excluirlo dejaría al pin ciego ante un
# header que desaparece; pinear el literal de la versión enrojecería el criterio
# 2 ante un bump de ``uv.lock`` por una razón ajena a esta fase. Derivarlo
# mantiene el SET de headers congelado y desacopla sólo la versión.
_UA = f"python-httpx/{httpx.__version__}"

# Tupla capturada contra el camino de código real (RESEARCH § Byte-Identical
# Request Test). El ORDEN DE CLAVES del body es ``day, closed, description``:
# ``description`` al final porque ``HolidayIn.to_dict()`` la lista al final, y
# ``open_time``/``close_time`` ausentes porque ``_params.drop_none`` las sacó.
# Ese ordenamiento es exactamente lo que una comparación parseada perdería.
_ADD_HOLIDAYS_V040 = (
    "POST",
    f"{_BASE}/calendar/holidays",
    (
        ("accept", "*/*"),
        ("accept-encoding", "gzip, deflate"),
        ("authorization", "Bearer test-token"),
        ("connection", "keep-alive"),
        ("content-length", "67"),
        ("content-type", "application/json"),
        ("host", _CONFTEST_HOST),
        ("user-agent", _UA),
    ),
    b'{"days":[{"day":"2099-12-29","closed":true,"description":"probe"}]}',
)

# Hazard 3: el set de headers del DELETE NO es el del POST — le faltan
# ``Content-Length`` y ``Content-Type`` porque el builder omite ``json_body``
# (D-02). Por eso se congela una tupla POR ENDPOINT y nunca una lista de headers
# compartida entre los dos.
_DELETE_HOLIDAY_V040 = (
    "DELETE",
    f"{_BASE}/calendar/holidays/{_PROBE_DAY}",
    (
        ("accept", "*/*"),
        ("accept-encoding", "gzip, deflate"),
        ("authorization", "Bearer test-token"),
        ("connection", "keep-alive"),
        ("host", _CONFTEST_HOST),
        ("user-agent", _UA),
    ),
    b"",
)


def _frozen(req: httpx.Request) -> tuple[str, str, tuple[tuple[str, str], ...], bytes]:
    """Proyección comparable de una request: método, URL, headers ordenados, bytes.

    Hazard 2: el mapping ``request.extensions`` queda deliberadamente AFUERA — ``request_id`` es
    un ``uuid4().hex`` fresco por llamada. Un string de 32 caracteres hex
    apareciendo en el diff de un fallo es la señal de que se coló igual.
    """
    return (req.method, str(req.url), tuple(sorted(req.headers.items())), req.content)


def _captured(httpx_mock: HTTPXMock, path: str) -> httpx.Request:
    """Última request capturada cuyo ``url.path`` es ``path``.

    Filtra por PATH en vez de indexar ``[0]`` a ciegas: un grant de token en la
    lista de capturas no puede correr el índice.
    """
    matches = [r for r in httpx_mock.get_requests() if r.url.path == path]
    assert matches, f"ninguna request capturada para {path}"
    return matches[-1]


# ----------------------------------------------------------------------
# add_holidays — POST /calendar/holidays
# ----------------------------------------------------------------------


def test_add_holidays_request_is_byte_identical_to_v040(httpx_mock: HTTPXMock) -> None:
    """La request sync de ``add_holidays`` iguala la tupla congelada de v0.4.0."""
    _open_gate()
    # El body de la respuesta es irrelevante: este test no afirma NADA sobre ella.
    httpx_mock.add_response(method="POST", status_code=200, json={})

    market_data_client.client._get_default().add_holidays(_probe_holidays())

    assert _frozen(_captured(httpx_mock, "/api/calendar/holidays")) == _ADD_HOLIDAYS_V040


async def test_add_holidays_request_is_byte_identical_to_v040_async(httpx_mock: HTTPXMock) -> None:
    """La request async de ``add_holidays`` iguala EL MISMO literal (paridad C-3)."""
    _open_gate_async()
    httpx_mock.add_response(method="POST", status_code=200, json={})

    await aio._get_default().add_holidays(_probe_holidays())

    assert _frozen(_captured(httpx_mock, "/api/calendar/holidays")) == _ADD_HOLIDAYS_V040


# ----------------------------------------------------------------------
# delete_holiday — DELETE /calendar/holidays/{day}
# ----------------------------------------------------------------------


def test_delete_holiday_request_is_byte_identical_to_v040(httpx_mock: HTTPXMock) -> None:
    """La request sync de ``delete_holiday`` iguala la tupla congelada de v0.4.0."""
    _open_gate()
    httpx_mock.add_response(method="DELETE", status_code=200, json={})

    market_data_client.client._get_default().delete_holiday(_PROBE_DAY)

    captured = _captured(httpx_mock, f"/api/calendar/holidays/{_PROBE_DAY}")
    assert _frozen(captured) == _DELETE_HOLIDAY_V040


async def test_delete_holiday_request_is_byte_identical_to_v040_async(
    httpx_mock: HTTPXMock,
) -> None:
    """La request async de ``delete_holiday`` iguala EL MISMO literal (paridad C-3)."""
    _open_gate_async()
    httpx_mock.add_response(method="DELETE", status_code=200, json={})

    await aio._get_default().delete_holiday(_PROBE_DAY)

    captured = _captured(httpx_mock, f"/api/calendar/holidays/{_PROBE_DAY}")
    assert _frozen(captured) == _DELETE_HOLIDAY_V040
