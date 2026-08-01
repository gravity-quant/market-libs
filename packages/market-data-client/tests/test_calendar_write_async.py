"""Calendar-write dispatch (async) — espejo de ``test_calendar_write.py``.

Mismo contrato observable de wire sobre el default ``AsyncClient``: gate abierto
despacha método/URL/body con el Bearer; ``confirm`` viaja en ``false`` por
default y en ``true`` con el opt-in explícito; los dos ``DELETE`` salen sin body
ni ``Content-Type``; el trío de config parsea a ``CalendarConfig`` tolerante y un
``422`` levanta ``MarketDataAPIError``; y el par de feriados retorna ``dict``
passthrough tolerante.

Y —agregado por el Plan 04— el espejo async de la matriz adversarial: refusal
end-to-end de los CINCO métodos con el gate OFF por default y el token
FORZADO-vencido (0 HTTP y 0 grant a Auth0, incluido ``preview_calendar_config``),
host mismatch → refused con 0 requests, y el guard de path-safety D-18 verificado
end-to-end con el gate ABIERTO.
"""

from __future__ import annotations

import asyncio
import json as _json
from typing import Any

import pytest
from pytest_httpx import HTTPXMock

from market_data_client import MarketDataAPIError, MarketDataMutationNotAllowedError, aio
from market_data_client.models import CalendarConfig, HolidayIn, HolidaysIn, MarketHoursIn

_BASE = "https://market-data-develop.test/api"
_TOKEN_URL = "https://auth.test/oauth/token"
_CONFTEST_HOST = "market-data-develop.test"

# Forma de wire REAL capturada en
# .planning/verification/schemas/market-data-client/get-calendar-config.json.
_CONFIG_200: dict[str, Any] = {
    "open": "11:00",
    "close": "17:00",
    "enabled": True,
    "editable": True,
    "env_bypass": False,
    "pre_open_minutes": 10,
    "source": "db",
    "timezone": "America/Argentina/Buenos_Aires",
    "updated_by": "ops",
    "warnings": ["mercado abierto fuera de la ventana habitual"],
    "updated_at": None,
}

# El body que ROADMAP SC#2 pinea en el wire para los defaults de MarketHoursIn.
_HOURS_BODY: dict[str, Any] = {
    "open_time": "10:00",
    "close_time": "17:00",
    "timezone": "America/Argentina/Buenos_Aires",
    "pre_open_minutes": 10,
    "enabled": True,
    "updated_by": "",
    "confirm": False,
}


def _hours(**overrides: Any) -> MarketHoursIn:
    """``MarketHoursIn`` con los valores del caso canónico del ROADMAP."""
    return MarketHoursIn("10:00", "17:00", "America/Argentina/Buenos_Aires", **overrides)


def _open_gate() -> None:
    """Abre el gate del singleton async default para el host del conftest."""
    aio.configure(mutating_allowed=True, expected_host=_CONFTEST_HOST)


# ----------------------------------------------------------------------
# set_calendar_config — PUT /calendar/config
# ----------------------------------------------------------------------


async def test_set_calendar_config_sends_bearer_and_body(httpx_mock: HTTPXMock) -> None:
    """``set_calendar_config`` async PUTea ``/calendar/config`` con las 7 claves."""
    _open_gate()
    httpx_mock.add_response(method="PUT", status_code=200, json=_CONFIG_200)

    await aio._get_default().set_calendar_config(_hours())

    req = httpx_mock.get_requests()[0]
    assert req.method == "PUT"
    assert req.url.path == "/api/calendar/config"
    assert req.headers["Authorization"] == "Bearer test-token"
    # ROADMAP SC#2: `confirm` viaja en `false` por default.
    assert _json.loads(req.content) == {
        "open_time": "10:00",
        "close_time": "17:00",
        "timezone": "America/Argentina/Buenos_Aires",
        "pre_open_minutes": 10,
        "enabled": True,
        "updated_by": "",
        "confirm": False,
    }


async def test_set_calendar_config_confirm_opt_in_travels_true(httpx_mock: HTTPXMock) -> None:
    """``confirm=True`` explícito viaja como ``true`` en el body async (D-09)."""
    _open_gate()
    httpx_mock.add_response(method="PUT", status_code=200, json=_CONFIG_200)

    await aio._get_default().set_calendar_config(_hours(confirm=True))

    body = _json.loads(httpx_mock.get_requests()[0].content)
    assert body["confirm"] is True
    assert body == {**_HOURS_BODY, "confirm": True}


async def test_set_calendar_config_parses_real_wire_shape(httpx_mock: HTTPXMock) -> None:
    """El ``200`` con la forma real de develop parsea a un ``CalendarConfig`` poblado."""
    _open_gate()
    httpx_mock.add_response(method="PUT", status_code=200, json=_CONFIG_200)

    cfg = await aio._get_default().set_calendar_config(_hours())

    assert isinstance(cfg, CalendarConfig)
    assert cfg.open == "11:00"
    assert cfg.close == "17:00"
    assert cfg.enabled is True
    assert cfg.timezone == "America/Argentina/Buenos_Aires"
    assert cfg.warnings == ["mercado abierto fuera de la ventana habitual"]


async def test_set_calendar_config_empty_body_returns_typed_defaults(
    httpx_mock: HTTPXMock,
) -> None:
    """Un ``200`` con body vacío degrada a un ``CalendarConfig`` de defaults (D-07)."""
    _open_gate()
    httpx_mock.add_response(method="PUT", status_code=200, content=b"")

    cfg = await aio._get_default().set_calendar_config(_hours())

    assert isinstance(cfg, CalendarConfig)
    assert cfg.open == ""
    assert cfg.enabled is False
    assert cfg.warnings == []


async def test_set_calendar_config_422_raises_api_error(httpx_mock: HTTPXMock) -> None:
    """Un ``422`` fluye por el ``raise_for_response`` existente → ``MarketDataAPIError``."""
    _open_gate()
    httpx_mock.add_response(method="PUT", status_code=422, json={"detail": "invalid"})

    with pytest.raises(MarketDataAPIError):
        await aio._get_default().set_calendar_config(_hours())


# ----------------------------------------------------------------------
# delete_calendar_config — DELETE /calendar/config (sin body, D-02)
# ----------------------------------------------------------------------


async def test_delete_calendar_config_sends_empty_body_without_content_type(
    httpx_mock: HTTPXMock,
) -> None:
    """``delete_calendar_config`` async DELETEa sin body ni ``Content-Type`` (D-02)."""
    _open_gate()
    httpx_mock.add_response(method="DELETE", status_code=200, json=_CONFIG_200)

    cfg = await aio._get_default().delete_calendar_config()

    req = httpx_mock.get_requests()[0]
    assert req.method == "DELETE"
    assert req.url.path == "/api/calendar/config"
    assert req.headers["Authorization"] == "Bearer test-token"
    assert req.content == b""
    assert "content-type" not in req.headers
    assert isinstance(cfg, CalendarConfig)
    assert cfg.open == "11:00"


async def test_delete_calendar_config_422_raises_api_error(httpx_mock: HTTPXMock) -> None:
    """Un ``422`` en el reset levanta ``MarketDataAPIError``."""
    _open_gate()
    httpx_mock.add_response(method="DELETE", status_code=422, json={"detail": "nope"})

    with pytest.raises(MarketDataAPIError):
        await aio._get_default().delete_calendar_config()


# ----------------------------------------------------------------------
# preview_calendar_config — POST /calendar/config/preview (gateado igual, D-14)
# ----------------------------------------------------------------------


async def test_preview_calendar_config_posts_same_body(httpx_mock: HTTPXMock) -> None:
    """``preview_calendar_config`` async POSTea el preview con el mismo body."""
    _open_gate()
    httpx_mock.add_response(method="POST", status_code=200, json=_CONFIG_200)

    cfg = await aio._get_default().preview_calendar_config(_hours())

    req = httpx_mock.get_requests()[0]
    assert req.method == "POST"
    assert req.url.path == "/api/calendar/config/preview"
    assert req.headers["Authorization"] == "Bearer test-token"
    assert _json.loads(req.content) == _HOURS_BODY
    assert isinstance(cfg, CalendarConfig)


async def test_preview_calendar_config_422_raises_api_error(httpx_mock: HTTPXMock) -> None:
    """Un ``422`` en el dry-run levanta ``MarketDataAPIError``."""
    _open_gate()
    httpx_mock.add_response(method="POST", status_code=422, json={"detail": "invalid"})

    with pytest.raises(MarketDataAPIError):
        await aio._get_default().preview_calendar_config(_hours())


# ----------------------------------------------------------------------
# Shims async module-level del trío de config
# ----------------------------------------------------------------------


async def test_config_trio_module_shims_dispatch(httpx_mock: HTTPXMock) -> None:
    """Los tres shims async module-level delegan al default AsyncClient."""
    _open_gate()
    httpx_mock.add_response(method="PUT", status_code=200, json=_CONFIG_200)
    httpx_mock.add_response(method="DELETE", status_code=200, json=_CONFIG_200)
    httpx_mock.add_response(method="POST", status_code=200, json=_CONFIG_200)

    await aio.set_calendar_config(_hours())
    await aio.delete_calendar_config()
    await aio.preview_calendar_config(_hours())

    paths = [(r.method, r.url.path) for r in httpx_mock.get_requests()]
    assert paths == [
        ("PUT", "/api/calendar/config"),
        ("DELETE", "/api/calendar/config"),
        ("POST", "/api/calendar/config/preview"),
    ]


# ----------------------------------------------------------------------
# add_holidays — POST /calendar/holidays
# ----------------------------------------------------------------------


async def test_add_holidays_sends_nested_body_without_null_hours(httpx_mock: HTTPXMock) -> None:
    """``add_holidays`` async POSTea sin las horas ``None`` (ROADMAP SC#3)."""
    _open_gate()
    httpx_mock.add_response(method="POST", status_code=200, json={"created": 1})

    await aio._get_default().add_holidays(HolidaysIn([HolidayIn("2026-12-25")]))

    req = httpx_mock.get_requests()[0]
    assert req.method == "POST"
    assert req.url.path == "/api/calendar/holidays"
    assert req.headers["Authorization"] == "Bearer test-token"
    assert _json.loads(req.content) == {
        "days": [{"day": "2026-12-25", "closed": True, "description": ""}]
    }


async def test_add_holidays_emits_hours_when_present(httpx_mock: HTTPXMock) -> None:
    """Un ``HolidayIn`` con horas emite ambas claves en su elemento."""
    _open_gate()
    httpx_mock.add_response(method="POST", status_code=200, json={})

    await aio._get_default().add_holidays(
        HolidaysIn(
            [
                HolidayIn(
                    "2026-12-24",
                    closed=False,
                    open_time="10:00",
                    close_time="13:00",
                    description="media rueda",
                )
            ]
        )
    )

    assert _json.loads(httpx_mock.get_requests()[0].content) == {
        "days": [
            {
                "day": "2026-12-24",
                "closed": False,
                "open_time": "10:00",
                "close_time": "13:00",
                "description": "media rueda",
            }
        ]
    }


async def test_add_holidays_returns_body_passthrough(httpx_mock: HTTPXMock) -> None:
    """``add_holidays`` async devuelve el dict del ``200`` tal cual (D-06)."""
    _open_gate()
    httpx_mock.add_response(method="POST", status_code=200, json={"created": 1, "skipped": 0})

    out = await aio._get_default().add_holidays(HolidaysIn([HolidayIn("2026-12-25")]))

    assert isinstance(out, dict)
    assert out == {"created": 1, "skipped": 0}


async def test_add_holidays_empty_body_returns_empty_dict(httpx_mock: HTTPXMock) -> None:
    """Un ``200`` con body vacío degrada a ``{}`` (D-07 visto desde el shell)."""
    _open_gate()
    httpx_mock.add_response(method="POST", status_code=200, content=b"")

    out = await aio._get_default().add_holidays(HolidaysIn([HolidayIn("2026-12-25")]))

    assert out == {}


async def test_add_holidays_422_raises_api_error(httpx_mock: HTTPXMock) -> None:
    """Un ``422`` en el alta de feriados levanta ``MarketDataAPIError``."""
    _open_gate()
    httpx_mock.add_response(method="POST", status_code=422, json={"detail": "invalid"})

    with pytest.raises(MarketDataAPIError):
        await aio._get_default().add_holidays(HolidaysIn([HolidayIn("bad")]))


# ----------------------------------------------------------------------
# delete_holiday — DELETE /calendar/holidays/{day} (sin body, D-02)
# ----------------------------------------------------------------------


async def test_delete_holiday_interpolates_day_and_sends_no_body(httpx_mock: HTTPXMock) -> None:
    """``delete_holiday`` async DELETEa el día interpolado, sin body ni ``Content-Type``."""
    _open_gate()
    httpx_mock.add_response(method="DELETE", status_code=200, json={"deleted": 1})

    out = await aio._get_default().delete_holiday("2026-12-25")

    req = httpx_mock.get_requests()[0]
    assert req.method == "DELETE"
    assert req.url.path == "/api/calendar/holidays/2026-12-25"
    assert req.headers["Authorization"] == "Bearer test-token"
    assert req.content == b""
    assert "content-type" not in req.headers
    assert isinstance(out, dict)
    assert out == {"deleted": 1}


async def test_delete_holiday_empty_body_returns_empty_dict(httpx_mock: HTTPXMock) -> None:
    """Un ``200`` con body vacío degrada a ``{}`` también en el borrado."""
    _open_gate()
    httpx_mock.add_response(method="DELETE", status_code=200, content=b"")

    out = await aio._get_default().delete_holiday("2026-12-25")

    assert out == {}


async def test_delete_holiday_422_raises_api_error(httpx_mock: HTTPXMock) -> None:
    """Un ``422`` (p.ej. fecha mal formada, D-13) levanta ``MarketDataAPIError``."""
    _open_gate()
    httpx_mock.add_response(method="DELETE", status_code=422, json={"detail": "bad date"})

    with pytest.raises(MarketDataAPIError):
        await aio._get_default().delete_holiday("2026-13-45")


# ----------------------------------------------------------------------
# Shims async module-level del par de feriados
# ----------------------------------------------------------------------


async def test_holiday_pair_module_shims_dispatch(httpx_mock: HTTPXMock) -> None:
    """Los dos shims async module-level del par de feriados delegan al default."""
    _open_gate()
    httpx_mock.add_response(method="POST", status_code=200, json={})
    httpx_mock.add_response(method="DELETE", status_code=200, json={})

    await aio.add_holidays(HolidaysIn([HolidayIn("2026-12-25")]))
    await aio.delete_holiday("2026-12-25")

    paths = [(r.method, r.url.path) for r in httpx_mock.get_requests()]
    assert paths == [
        ("POST", "/api/calendar/holidays"),
        ("DELETE", "/api/calendar/holidays/2026-12-25"),
    ]


# ----------------------------------------------------------------------
# Refusal end-to-end x5 async (gate OFF por default) → CERO IO (D-14/T-26-04)
#
# Igual que en el espejo sync: ``token_expires_at=0.0`` fuerza el token vencido,
# de modo que la lista vacía de requests prueba a la vez cero HTTP al servicio y
# cero grant a Auth0 (T-26-06).
# ----------------------------------------------------------------------


async def test_set_calendar_config_refused_by_default_emits_no_request(
    httpx_mock: HTTPXMock,
) -> None:
    """``PUT`` de config async: gate OFF por default → refused, 0 HTTP y 0 grant."""
    aio.configure(token_expires_at=0.0)

    with pytest.raises(MarketDataMutationNotAllowedError):
        await aio._get_default().set_calendar_config(_hours())

    assert httpx_mock.get_requests() == []


async def test_delete_calendar_config_refused_by_default_emits_no_request(
    httpx_mock: HTTPXMock,
) -> None:
    """``DELETE`` de config async (reset): gate OFF → refused con 0 requests."""
    aio.configure(token_expires_at=0.0)

    with pytest.raises(MarketDataMutationNotAllowedError):
        await aio._get_default().delete_calendar_config()

    assert httpx_mock.get_requests() == []


async def test_preview_calendar_config_refused_by_default_emits_no_request(
    httpx_mock: HTTPXMock,
) -> None:
    """El dry-run async tampoco tiene carve-out (D-14): refused con 0 requests."""
    aio.configure(token_expires_at=0.0)

    with pytest.raises(MarketDataMutationNotAllowedError):
        await aio._get_default().preview_calendar_config(_hours())

    assert httpx_mock.get_requests() == []


async def test_add_holidays_refused_by_default_emits_no_request(httpx_mock: HTTPXMock) -> None:
    """Alta de feriados async: gate OFF por default → refused con 0 requests."""
    aio.configure(token_expires_at=0.0)

    with pytest.raises(MarketDataMutationNotAllowedError):
        await aio._get_default().add_holidays(HolidaysIn([HolidayIn("2026-12-25")]))

    assert httpx_mock.get_requests() == []


async def test_delete_holiday_refused_by_default_emits_no_request(httpx_mock: HTTPXMock) -> None:
    """Borrado de feriado async: gate OFF por default → refused con 0 requests."""
    aio.configure(token_expires_at=0.0)

    with pytest.raises(MarketDataMutationNotAllowedError):
        await aio._get_default().delete_holiday("2026-12-25")

    assert httpx_mock.get_requests() == []


async def test_set_calendar_config_refused_on_host_mismatch(httpx_mock: HTTPXMock) -> None:
    """Gate ON async pero host de ``base_url`` ≠ ``expected_host`` → 0 requests."""
    aio.configure(
        mutating_allowed=True,
        expected_host="market-data-PROD.bbsa.com.ar",
        token_expires_at=0.0,
    )

    with pytest.raises(MarketDataMutationNotAllowedError):
        await aio._get_default().set_calendar_config(_hours())

    assert httpx_mock.get_requests() == []


# ----------------------------------------------------------------------
# Path-safety D-18 end-to-end async con el gate ABIERTO (T-26-01)
# ----------------------------------------------------------------------


async def test_delete_holiday_path_safety_dotdot_emits_no_request(httpx_mock: HTTPXMock) -> None:
    """``delete_holiday("../config")`` async: ``ValueError`` y CERO requests.

    Sin el guard, ``day`` interpolado raw haría que httpx normalizara
    ``/api/calendar/holidays/../config`` a ``DELETE /api/calendar/config`` — el
    reset de la configuración de mercado. El ``422`` del servidor no es
    mitigación: el request nunca llega al endpoint que validaría el ``day``.
    """
    _open_gate()

    with pytest.raises(ValueError, match="single path segment"):
        await aio._get_default().delete_holiday("../config")

    assert httpx_mock.get_requests() == []


async def test_delete_holiday_path_safety_empty_and_query_emit_no_request(
    httpx_mock: HTTPXMock,
) -> None:
    """``""`` y un ``day`` con query string async: rechazo con 0 requests."""
    _open_gate()

    with pytest.raises(ValueError, match="single path segment"):
        await aio._get_default().delete_holiday("")

    with pytest.raises(ValueError, match="single path segment"):
        await aio._get_default().delete_holiday("2026-12-25?x=1")

    assert httpx_mock.get_requests() == []


async def test_delete_holiday_path_safety_single_dot_emits_no_request(
    httpx_mock: HTTPXMock,
) -> None:
    """CR-01 async: ``delete_holiday(".")`` → ``ValueError`` y CERO requests.

    httpx 0.28.1 aplica ``remove_dot_segments`` (RFC 3986) en ``build_request``, así
    que un ``"."`` no queda como ``/holidays/.`` — el segmento DESAPARECE y el
    request colapsa a ``DELETE /api/calendar/holidays``, el endpoint COLECCIÓN. El
    colapso es client-side puro: no necesita ninguna cooperación del servidor. Por
    eso la lista vacía de requests es la mitad que importa del assert.
    """
    _open_gate()

    with pytest.raises(ValueError, match="single path segment"):
        await aio._get_default().delete_holiday(".")

    assert httpx_mock.get_requests() == []


@pytest.mark.parametrize(
    "hostile_day",
    [
        "..",
        "%2e",
        "%2e%2e%2fconfig",
        "%2Fconfig",
        "config%3Fx=1",
        "2026-12-25%23frag",
        "a\\b",
        "a/b",
    ],
)
async def test_delete_holiday_path_safety_encoded_escapes_emit_no_request(
    httpx_mock: HTTPXMock, hostile_day: str
) -> None:
    """CR-02 async: los escapes percent-encoded se rechazan con 0 requests."""
    _open_gate()

    with pytest.raises(ValueError, match="single path segment"):
        await aio._get_default().delete_holiday(hostile_day)

    assert httpx_mock.get_requests() == []


async def test_delete_holiday_path_safety_non_str_day_emits_no_request(
    httpx_mock: HTTPXMock,
) -> None:
    """WR-04 async: ``day`` no-``str`` → ``ValueError`` (no ``TypeError``), 0 requests."""
    _open_gate()

    for bad_day in (None, 20261225, ["2026-12-25"]):
        with pytest.raises(ValueError, match="single path segment"):
            await aio._get_default().delete_holiday(bad_day)  # type: ignore[arg-type]

    assert httpx_mock.get_requests() == []


# ----------------------------------------------------------------------
# Retry dispatch-level (async) — el flag ``idempotent`` observado (D-20)
# ----------------------------------------------------------------------
#
# Espejo async del par que hasta ahora vivía SÓLO en la superficie sync. Se
# agrega acá porque el flip de ``build_add_holidays_request``
# (``idempotent`` False → True, F-49/F-59) cambia el comportamiento de AMBOS
# transports, y la regla dual sync/async exige probar los dos: sin este espejo
# la corrección quedaría medida en una sola mitad del paquete.
#
# ``AsyncRetrying`` espera el wait vía ``asyncio.sleep``, así que ése es el
# target del monkeypatch — el equivalente async del patrón ``time.sleep``
# in-package de ``tests/test_transport.py``. Sin el patch cada test pagaría los
# ~4,4 s reales de jitter.


async def test_add_holidays_retries_three_times_on_repeated_503(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``idempotent=True`` CORREGIDO (async): 3x503 → 3 requests y 2 sleeps."""
    sleeps: list[float] = []

    async def _fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr(asyncio, "sleep", _fake_sleep)
    _open_gate()
    for _ in range(3):
        httpx_mock.add_response(method="POST", status_code=503)

    with pytest.raises(MarketDataAPIError):
        await aio._get_default().add_holidays(HolidaysIn([HolidayIn("2026-12-25")]))

    assert len(httpx_mock.get_requests()) == 3
    assert len(sleeps) == 2


async def test_delete_holiday_retries_three_times_on_repeated_503(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Control positivo async ``idempotent=True``: 3x503 → 3 requests y 2 sleeps."""
    sleeps: list[float] = []

    async def _fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr(asyncio, "sleep", _fake_sleep)
    _open_gate()
    for _ in range(3):
        httpx_mock.add_response(method="DELETE", status_code=503)

    with pytest.raises(MarketDataAPIError):
        await aio._get_default().delete_holiday("2026-12-25")

    assert len(httpx_mock.get_requests()) == 3
    assert len(sleeps) == 2


async def test_delete_holiday_retry_after_lost_response_surfaces_404(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F-50 async: idempotente en ESTADO, no en STATUS — el retry ve el ``404``.

    Mismo razonamiento que en la superficie sync: el flag se MANTIENE en ``True``
    porque sin retry el caller habría levantado igual sobre el ``503``; lo que
    cambia es la IDENTIDAD del error, no el resultado. El test fija esa
    consecuencia en vez de dejarla como sorpresa.
    """
    sleeps: list[float] = []

    async def _fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr(asyncio, "sleep", _fake_sleep)
    _open_gate()
    httpx_mock.add_response(method="DELETE", status_code=503)
    httpx_mock.add_response(method="DELETE", status_code=404, json={"detail": "not found"})

    with pytest.raises(MarketDataAPIError):
        await aio._get_default().delete_holiday("2026-12-25")

    # 2 requests: el 404 NO es retryable, así que el loop corta ahí.
    assert len(httpx_mock.get_requests()) == 2
    assert len(sleeps) == 1
