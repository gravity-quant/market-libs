"""Calendar-write dispatch (sync) — MUT-MD-02 + GATE-MD-01 end-to-end.

Cubre el contrato observable de wire de los cinco métodos mutadores gated del
``Client`` sync (``set_calendar_config`` / ``delete_calendar_config`` /
``preview_calendar_config`` / ``add_holidays`` / ``delete_holiday``):

- Gate abierto (``mutating_allowed=True`` + host coincidente): despacha el
  método/URL/body correctos con el Bearer.
- El body del ``PUT /calendar/config`` lleva ``confirm: false`` por default y
  ``confirm: true`` sólo cuando el consumidor lo setea (D-09, ROADMAP SC#2).
- Los dos ``DELETE`` salen con ``content == b""`` y SIN header ``Content-Type``
  (D-02 / T-26-08).
- El trío de config parsea a ``CalendarConfig`` vía el
  ``parse_calendar_config_response`` existente (D-05), tolerante ante un ``200``
  con body vacío (D-07).
- El par de feriados retorna ``dict`` passthrough (D-06) y degrada a ``{}`` ante
  un ``200`` con body vacío (D-07).
- ``422`` levanta ``MarketDataAPIError`` vía el ``raise_for_response`` existente
  (sin manejo de status nuevo en los métodos).

La matriz adversarial de refusals (cero requests) y el test dispatch-level de
no-retry (D-15) viven en el Plan 04.
"""

from __future__ import annotations

import json as _json
from typing import Any

import pytest
from pytest_httpx import HTTPXMock

import market_data_client
from market_data_client import MarketDataAPIError
from market_data_client.models import CalendarConfig, HolidayIn, HolidaysIn, MarketHoursIn

_BASE = "https://market-data-develop.test/api"
_TOKEN_URL = "https://auth.test/oauth/token"
# El host que el conftest siembra en base_url (NO el default develop bbsa).
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
    """Abre el gate del singleton default para el host del conftest."""
    market_data_client.configure(mutating_allowed=True, expected_host=_CONFTEST_HOST)


# ----------------------------------------------------------------------
# set_calendar_config — PUT /calendar/config
# ----------------------------------------------------------------------


def test_set_calendar_config_sends_bearer_and_body(httpx_mock: HTTPXMock) -> None:
    """``set_calendar_config`` PUTea ``/calendar/config`` con las 7 claves y el Bearer."""
    _open_gate()
    httpx_mock.add_response(method="PUT", status_code=200, json=_CONFIG_200)

    market_data_client.client._get_default().set_calendar_config(_hours())

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


def test_set_calendar_config_confirm_opt_in_travels_true(httpx_mock: HTTPXMock) -> None:
    """``confirm=True`` explícito viaja como ``true`` en el body (D-09)."""
    _open_gate()
    httpx_mock.add_response(method="PUT", status_code=200, json=_CONFIG_200)

    market_data_client.client._get_default().set_calendar_config(_hours(confirm=True))

    body = _json.loads(httpx_mock.get_requests()[0].content)
    assert body["confirm"] is True
    assert body == {**_HOURS_BODY, "confirm": True}


def test_set_calendar_config_parses_real_wire_shape(httpx_mock: HTTPXMock) -> None:
    """El ``200`` con la forma real de develop parsea a un ``CalendarConfig`` poblado."""
    _open_gate()
    httpx_mock.add_response(method="PUT", status_code=200, json=_CONFIG_200)

    cfg = market_data_client.client._get_default().set_calendar_config(_hours())

    assert isinstance(cfg, CalendarConfig)
    assert cfg.open == "11:00"
    assert cfg.close == "17:00"
    assert cfg.enabled is True
    assert cfg.timezone == "America/Argentina/Buenos_Aires"
    assert cfg.warnings == ["mercado abierto fuera de la ventana habitual"]


def test_set_calendar_config_empty_body_returns_typed_defaults(httpx_mock: HTTPXMock) -> None:
    """Un ``200`` con body vacío degrada a un ``CalendarConfig`` de defaults (D-07)."""
    _open_gate()
    httpx_mock.add_response(method="PUT", status_code=200, content=b"")

    cfg = market_data_client.client._get_default().set_calendar_config(_hours())

    assert isinstance(cfg, CalendarConfig)
    assert cfg.open == ""
    assert cfg.enabled is False
    assert cfg.warnings == []


def test_set_calendar_config_422_raises_api_error(httpx_mock: HTTPXMock) -> None:
    """Un ``422`` fluye por el ``raise_for_response`` existente → ``MarketDataAPIError``."""
    _open_gate()
    httpx_mock.add_response(method="PUT", status_code=422, json={"detail": "invalid"})

    with pytest.raises(MarketDataAPIError):
        market_data_client.client._get_default().set_calendar_config(_hours())


# ----------------------------------------------------------------------
# delete_calendar_config — DELETE /calendar/config (sin body, D-02)
# ----------------------------------------------------------------------


def test_delete_calendar_config_sends_empty_body_without_content_type(
    httpx_mock: HTTPXMock,
) -> None:
    """``delete_calendar_config`` DELETEa sin body ni ``Content-Type`` (D-02)."""
    _open_gate()
    httpx_mock.add_response(method="DELETE", status_code=200, json=_CONFIG_200)

    cfg = market_data_client.client._get_default().delete_calendar_config()

    req = httpx_mock.get_requests()[0]
    assert req.method == "DELETE"
    assert req.url.path == "/api/calendar/config"
    assert req.headers["Authorization"] == "Bearer test-token"
    assert req.content == b""
    assert "content-type" not in req.headers
    assert isinstance(cfg, CalendarConfig)
    assert cfg.open == "11:00"


def test_delete_calendar_config_422_raises_api_error(httpx_mock: HTTPXMock) -> None:
    """Un ``422`` en el reset levanta ``MarketDataAPIError``."""
    _open_gate()
    httpx_mock.add_response(method="DELETE", status_code=422, json={"detail": "nope"})

    with pytest.raises(MarketDataAPIError):
        market_data_client.client._get_default().delete_calendar_config()


# ----------------------------------------------------------------------
# preview_calendar_config — POST /calendar/config/preview (gateado igual, D-14)
# ----------------------------------------------------------------------


def test_preview_calendar_config_posts_same_body(httpx_mock: HTTPXMock) -> None:
    """``preview_calendar_config`` POSTea ``/calendar/config/preview`` con el mismo body."""
    _open_gate()
    httpx_mock.add_response(method="POST", status_code=200, json=_CONFIG_200)

    cfg = market_data_client.client._get_default().preview_calendar_config(_hours())

    req = httpx_mock.get_requests()[0]
    assert req.method == "POST"
    assert req.url.path == "/api/calendar/config/preview"
    assert req.headers["Authorization"] == "Bearer test-token"
    assert _json.loads(req.content) == _HOURS_BODY
    assert isinstance(cfg, CalendarConfig)


def test_preview_calendar_config_422_raises_api_error(httpx_mock: HTTPXMock) -> None:
    """Un ``422`` en el dry-run levanta ``MarketDataAPIError``."""
    _open_gate()
    httpx_mock.add_response(method="POST", status_code=422, json={"detail": "invalid"})

    with pytest.raises(MarketDataAPIError):
        market_data_client.client._get_default().preview_calendar_config(_hours())


# ----------------------------------------------------------------------
# Shims module-level del trío de config
# ----------------------------------------------------------------------


def test_config_trio_module_shims_dispatch(httpx_mock: HTTPXMock) -> None:
    """Los tres shims module-level delegan al default Client."""
    _open_gate()
    httpx_mock.add_response(method="PUT", status_code=200, json=_CONFIG_200)
    httpx_mock.add_response(method="DELETE", status_code=200, json=_CONFIG_200)
    httpx_mock.add_response(method="POST", status_code=200, json=_CONFIG_200)

    market_data_client.client.set_calendar_config(_hours())
    market_data_client.client.delete_calendar_config()
    market_data_client.client.preview_calendar_config(_hours())

    paths = [(r.method, r.url.path) for r in httpx_mock.get_requests()]
    assert paths == [
        ("PUT", "/api/calendar/config"),
        ("DELETE", "/api/calendar/config"),
        ("POST", "/api/calendar/config/preview"),
    ]


# ----------------------------------------------------------------------
# add_holidays — POST /calendar/holidays
# ----------------------------------------------------------------------


def test_add_holidays_sends_nested_body_without_null_hours(httpx_mock: HTTPXMock) -> None:
    """``add_holidays`` POSTea ``/calendar/holidays`` sin las horas ``None`` (ROADMAP SC#3)."""
    _open_gate()
    httpx_mock.add_response(method="POST", status_code=200, json={"created": 1})

    market_data_client.client._get_default().add_holidays(HolidaysIn([HolidayIn("2026-12-25")]))

    req = httpx_mock.get_requests()[0]
    assert req.method == "POST"
    assert req.url.path == "/api/calendar/holidays"
    assert req.headers["Authorization"] == "Bearer test-token"
    assert _json.loads(req.content) == {
        "days": [{"day": "2026-12-25", "closed": True, "description": ""}]
    }


def test_add_holidays_emits_hours_when_present(httpx_mock: HTTPXMock) -> None:
    """Un ``HolidayIn`` con horas emite ambas claves en su elemento."""
    _open_gate()
    httpx_mock.add_response(method="POST", status_code=200, json={})

    market_data_client.client._get_default().add_holidays(
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


def test_add_holidays_returns_body_passthrough(httpx_mock: HTTPXMock) -> None:
    """``add_holidays`` devuelve el dict del ``200`` tal cual (D-06)."""
    _open_gate()
    httpx_mock.add_response(method="POST", status_code=200, json={"created": 1, "skipped": 0})

    out = market_data_client.client._get_default().add_holidays(
        HolidaysIn([HolidayIn("2026-12-25")])
    )

    assert isinstance(out, dict)
    assert out == {"created": 1, "skipped": 0}


def test_add_holidays_empty_body_returns_empty_dict(httpx_mock: HTTPXMock) -> None:
    """Un ``200`` con body vacío degrada a ``{}`` (D-07 visto desde el shell)."""
    _open_gate()
    httpx_mock.add_response(method="POST", status_code=200, content=b"")

    out = market_data_client.client._get_default().add_holidays(
        HolidaysIn([HolidayIn("2026-12-25")])
    )

    assert out == {}


def test_add_holidays_422_raises_api_error(httpx_mock: HTTPXMock) -> None:
    """Un ``422`` en el alta de feriados levanta ``MarketDataAPIError``."""
    _open_gate()
    httpx_mock.add_response(method="POST", status_code=422, json={"detail": "invalid"})

    with pytest.raises(MarketDataAPIError):
        market_data_client.client._get_default().add_holidays(HolidaysIn([HolidayIn("bad")]))


# ----------------------------------------------------------------------
# delete_holiday — DELETE /calendar/holidays/{day} (sin body, D-02)
# ----------------------------------------------------------------------


def test_delete_holiday_interpolates_day_and_sends_no_body(httpx_mock: HTTPXMock) -> None:
    """``delete_holiday`` DELETEa el día interpolado, sin body ni ``Content-Type``."""
    _open_gate()
    httpx_mock.add_response(method="DELETE", status_code=200, json={"deleted": 1})

    out = market_data_client.client._get_default().delete_holiday("2026-12-25")

    req = httpx_mock.get_requests()[0]
    assert req.method == "DELETE"
    assert req.url.path == "/api/calendar/holidays/2026-12-25"
    assert req.headers["Authorization"] == "Bearer test-token"
    assert req.content == b""
    assert "content-type" not in req.headers
    assert isinstance(out, dict)
    assert out == {"deleted": 1}


def test_delete_holiday_empty_body_returns_empty_dict(httpx_mock: HTTPXMock) -> None:
    """Un ``200`` con body vacío degrada a ``{}`` también en el borrado."""
    _open_gate()
    httpx_mock.add_response(method="DELETE", status_code=200, content=b"")

    out = market_data_client.client._get_default().delete_holiday("2026-12-25")

    assert out == {}


def test_delete_holiday_422_raises_api_error(httpx_mock: HTTPXMock) -> None:
    """Un ``422`` (p.ej. fecha mal formada, D-13) levanta ``MarketDataAPIError``."""
    _open_gate()
    httpx_mock.add_response(method="DELETE", status_code=422, json={"detail": "bad date"})

    with pytest.raises(MarketDataAPIError):
        market_data_client.client._get_default().delete_holiday("2026-13-45")


# ----------------------------------------------------------------------
# Shims module-level del par de feriados
# ----------------------------------------------------------------------


def test_holiday_pair_module_shims_dispatch(httpx_mock: HTTPXMock) -> None:
    """Los dos shims module-level del par de feriados delegan al default Client."""
    _open_gate()
    httpx_mock.add_response(method="POST", status_code=200, json={})
    httpx_mock.add_response(method="DELETE", status_code=200, json={})

    market_data_client.client.add_holidays(HolidaysIn([HolidayIn("2026-12-25")]))
    market_data_client.client.delete_holiday("2026-12-25")

    paths = [(r.method, r.url.path) for r in httpx_mock.get_requests()]
    assert paths == [
        ("POST", "/api/calendar/holidays"),
        ("DELETE", "/api/calendar/holidays/2026-12-25"),
    ]
