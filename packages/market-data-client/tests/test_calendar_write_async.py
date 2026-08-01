"""Calendar-write dispatch (async) — espejo de ``test_calendar_write.py``.

Mismo contrato observable de wire sobre el default ``AsyncClient``: gate abierto
despacha método/URL/body con el Bearer; ``confirm`` viaja en ``false`` por
default y en ``true`` con el opt-in explícito; los dos ``DELETE`` salen sin body
ni ``Content-Type``; el trío de config parsea a ``CalendarConfig`` tolerante y un
``422`` levanta ``MarketDataAPIError``.

La matriz adversarial de refusals (cero requests) vive en el Plan 04.
"""

from __future__ import annotations

import json as _json
from typing import Any

import pytest
from pytest_httpx import HTTPXMock

from market_data_client import MarketDataAPIError, aio
from market_data_client.models import CalendarConfig, MarketHoursIn

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
