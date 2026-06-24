"""Tests de regresión sobre el driver `main_ambito_financiero.py` (Phase 2 fixes).

El driver vive en la raíz del repo y no está en `testpaths` (D-05: NO se ejecuta
dentro de pytest), pero su comportamiento crítico se chequea acá vía tests de
regresión que mockean la superficie sync+async del cliente y assertean
invariantes del driver:

- **WR-01:** ``probe_antibot`` lee ``exc.status_code`` directamente (no usa el
  fallback dead-code ``exc.args[0]``).
- **WR-03:** ``probe_happy_sync`` / ``probe_happy_async`` hacen **una sola
  llamada HTTP** por probe — no doblan el tráfico llamando al wrapper
  ``get_dollar_banco_nacion`` después del ``_request`` crudo.
- **IN-03:** ``_async_main`` honra D-04 — si ``aclient.aclose()`` levanta durante
  el teardown, la excepción NO se propaga a ``asyncio.run`` (driver exit 0).

Estos tests viven bajo ``packages/ambito-financiero-client/tests/`` porque
``testpaths=["packages"]`` los colecta automáticamente; el driver se importa
desde la raíz del repo vía ``pythonpath=["."]``.

Phase 15 driver migration: cada ``probe_*`` ahora recibe su ``Client`` /
``AsyncClient`` threadeado como parámetro (D-01). Estos tests construyen una
instancia real y mockean su superficie de instancia (``client._request`` /
``client.get_dollar_banco_nacion`` / ``aclient.aclose``) en vez del default
module-level — preservando las mismas invariantes WR-01/WR-03/IN-03.
"""

from __future__ import annotations

import asyncio
import datetime as dt
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import main_ambito_financiero as driver
import pytest

from ambito_financiero_client import AsyncClient, Client
from ambito_financiero_client.exceptions import (
    AmbitoFinancieroAuthError,
    AmbitoFinancieroNoDataError,
)


def _ok_response(payload: object) -> MagicMock:
    """MagicMock httpx.Response: ``status_code=200`` para que ``_raise_for_response``
    (que lee ``status_code`` + ``is_error``) trate la respuesta como exitosa."""
    resp = MagicMock()
    resp.status_code = 200
    resp.is_error = False
    resp.json.return_value = payload
    return resp


@pytest.fixture(autouse=True)
def _isolate_driver_state(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """Aísla el driver: redirige el directorio de findings y schema a tmp_path."""
    from verification import findings

    monkeypatch.setattr(findings, "_FINDINGS_DIR", tmp_path)
    monkeypatch.setattr(driver, "_SCHEMA_DIR", tmp_path / "schemas")
    monkeypatch.setattr(driver, "_SCHEMA_FILE", tmp_path / "schemas" / "x.json")
    # Resetear el counter module-level para evitar bleed entre tests
    monkeypatch.setattr(driver, "_fid_counter", 0)


# ---------------------------------------------------------------------------
# WR-03: probe_happy_sync NO llama a get_dollar_banco_nacion (una sola HTTP call)
# ---------------------------------------------------------------------------


def test_probe_happy_sync_single_http_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """WR-03 regression: probe_happy_sync hace UNA sola llamada HTTP (no dobla)."""
    client = Client()
    fake_resp = _ok_response(
        [
            ["Fecha", "Compra", "Venta"],
            ["15/04/2026", "1.405,00", "1.415,00"],
        ]
    )
    request_mock = MagicMock(return_value=fake_resp)
    wrapper_mock = MagicMock(return_value=999.99)  # NO debería ser invocado

    # Phase 15: Client usa __slots__ → no se puede setattr por-instancia; parcheamos
    # el método de clase (monkeypatch auto-deshace tras el test).
    monkeypatch.setattr(Client, "_request", request_mock)
    monkeypatch.setattr(Client, "get_dollar_banco_nacion", wrapper_mock)

    result, rows = driver.probe_happy_sync(dt.date(2026, 4, 21), client)

    assert result.status == "PASS"
    assert result.detail == "precio=1415.0"
    assert rows == [
        ["Fecha", "Compra", "Venta"],
        ["15/04/2026", "1.405,00", "1.415,00"],
    ]
    # WR-03: solo el GET crudo via _request — NO el wrapper
    assert request_mock.call_count == 1
    assert wrapper_mock.call_count == 0


def test_probe_happy_async_single_http_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """WR-03 regression (mirror async): probe_happy_async hace UNA sola llamada HTTP."""
    aclient = AsyncClient()
    fake_resp = _ok_response(
        [
            ["Fecha", "Compra", "Venta"],
            ["15/04/2026", "1.405,00", "1.415,00"],
        ]
    )
    request_mock = AsyncMock(return_value=fake_resp)
    wrapper_mock = AsyncMock(return_value=999.99)  # NO debería ser invocado

    # Phase 15: AsyncClient usa __slots__ → parcheamos el método de clase.
    monkeypatch.setattr(AsyncClient, "_request", request_mock)
    monkeypatch.setattr(AsyncClient, "get_dollar_banco_nacion", wrapper_mock)

    result, precio = asyncio.run(driver.probe_happy_async(dt.date(2026, 4, 21), aclient))

    assert result.status == "PASS"
    assert result.detail == "precio=1415.0"
    assert precio == 1415.0
    # WR-03: solo el GET crudo via _request — NO el wrapper
    assert request_mock.call_count == 1
    assert wrapper_mock.call_count == 0


# ---------------------------------------------------------------------------
# WR-01: probe_antibot lee exc.status_code (no usa el fallback dead-code)
# ---------------------------------------------------------------------------


def test_probe_antibot_uses_typed_status_code(monkeypatch: pytest.MonkeyPatch) -> None:
    """WR-01 regression: probe_antibot lee ``exc.status_code`` directamente.

    Crea un AmbitoFinancieroAuthError con un `args[0]` que NO sería 403
    (formato `"[403] forbidden"` que era la trampa del bug). El probe debe
    igualmente clasificarlo como EXPECTED via el atributo typed.
    """
    monkeypatch.setenv("VERIFY_ANTIBOT", "1")
    client = Client()
    good_ua = client._state.user_agent

    # Constructor del AuthError: status_code=403, message="forbidden"
    # -> exc.args[0] == "[403] forbidden" (str, no int)
    # -> exc.status_code == 403 (int)
    # El fallback `exc.args[0] == 403` siempre fallaría comparando str vs int.
    # El path correcto via exc.status_code clasifica el 403 como EXPECTED.
    raise_403 = AmbitoFinancieroAuthError(403, "forbidden")

    def get_dollar_raises(self: Client, *args: object, **kwargs: object) -> float:
        raise raise_403

    # Phase 15: Client usa __slots__ → parcheamos métodos de clase (incluido close()
    # para no abrir/cerrar pools reales durante el one-shot).
    monkeypatch.setattr(Client, "get_dollar_banco_nacion", get_dollar_raises)
    monkeypatch.setattr(Client, "close", lambda self: None)

    result = driver.probe_antibot(dt.date(2026, 4, 21), client)

    # EXPECTED terminal vía exc.status_code path
    assert result.status == "FINDING"
    assert "EXPECTED" in result.detail
    # D-15: el finally restauró el GOOD_UA sobre la instancia threadeada.
    assert client._state.user_agent == good_ua


def test_probe_antibot_403_via_typed_attribute_classifies_expected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """WR-01 regression: 403 clasifica como EXPECTED aun si args[0] fuera mentirosa."""
    monkeypatch.setenv("VERIFY_ANTIBOT", "1")
    client = Client()

    # Crear el error y mutar args para verificar que exc.status_code es load-bearing
    exc = AmbitoFinancieroAuthError(403, "forbidden")
    # Si el código aún usara args[0], comparar "[403] forbidden" == 403 -> False
    # y caería en la rama OPEN. Con el fix, exc.status_code (int=403) gana.

    def get_dollar_raises(self: Client, *args: object, **kwargs: object) -> float:
        raise exc

    monkeypatch.setattr(Client, "get_dollar_banco_nacion", get_dollar_raises)
    monkeypatch.setattr(Client, "close", lambda self: None)

    result = driver.probe_antibot(dt.date(2026, 4, 21), client)
    assert result.status == "FINDING"
    assert "EXPECTED" in result.detail


# ---------------------------------------------------------------------------
# IN-03: _async_main NO se cae si aclose() levanta (D-04 honrado)
# ---------------------------------------------------------------------------


def test_async_main_swallows_aclose_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """IN-03 regression: si ``aclient.aclose()`` levanta, el driver NO debe crashear.

    D-04 manda exit 0 salvo crash inesperado. La limpieza del AsyncClient
    durante teardown puede fallar (httpx error de red, race con la app); el
    error debe quedar contenido dentro de ``_async_main``.

    Phase 15: ``_async_main`` ahora construye su propio ``AsyncClient`` y llama
    ``aclient.aclose()`` (no el delegador module-level). Parcheamos el método
    de clase ``AsyncClient.aclose`` para que levante en el teardown.
    """

    # Mock probe_happy_async (acepta hoy el aclient threadeado) → ProbeResult válido.
    async def fake_happy_async(
        today: dt.date, aclient: AsyncClient
    ) -> tuple[driver.ProbeResult, float | None]:
        return driver.ProbeResult("happy_async", "PASS", "precio=1.0"), 1.0

    async def fake_aclose(self: AsyncClient) -> None:
        raise RuntimeError("simulated teardown failure")

    monkeypatch.setattr(driver, "probe_happy_async", fake_happy_async)
    monkeypatch.setattr(AsyncClient, "aclose", fake_aclose)

    # Si IN-03 estuviera regressed, el RuntimeError propagaría afuera de asyncio.run
    # y este test fallaría con la excepción no capturada.
    result, precio = asyncio.run(driver._async_main(dt.date(2026, 4, 21)))
    assert result.status == "PASS"
    assert precio == 1.0


# ---------------------------------------------------------------------------
# Sanity: probes existentes siguen verdes con los fixes aplicados
# ---------------------------------------------------------------------------


def test_probe_no_data_still_classifies_nodataerror_as_pass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sanity: probe_no_data sigue clasificando NoDataError como PASS post-fixes."""
    client = Client()

    def raise_no_data(self: Client, *args: object, **kwargs: object) -> float:
        raise AmbitoFinancieroNoDataError("no data")

    # Phase 15: Client usa __slots__ → parcheamos el método de clase.
    monkeypatch.setattr(Client, "get_dollar_banco_nacion", raise_no_data)
    result = driver.probe_no_data(dt.date(2026, 4, 21), client)
    assert result.status == "PASS"
    assert "NoDataError" in result.detail
