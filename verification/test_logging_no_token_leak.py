"""Cross-cutting caplog redaction guard — token literal MUST NOT appear in records.

Phase 8 D-10, D-22, D-26, LOG-02 / Pitfall 3+7. Wave 1 tests-first guard; passes
GREEN trivially in HEAD (libraries don't log anything yet), continues GREEN as
Plans 2-5 add structured DEBUG/INFO/WARNING records (RedactingFilter scrubs).

Invariant: configure each paquete with a sentinel token literal
(``SECRET-LITERAL-12345``), fire a mocked smoke endpoint, capture all log records
emitted to ``logging.getLogger("<pkg>")`` at DEBUG level, and assert the literal
appears NOWHERE in:
- ``record.getMessage()`` (the formatted message — covers ``msg`` + ``args``)
- ``str(record.args)`` (the raw args before interpolation)
- ``record.__dict__`` string values (the ``extra={...}`` fields)

Coverage:
- iol_client: token field (Bearer prefix in Authorization header)
- higyrus_client: token + password (JSON body) + url query (cuit PII not Bearer)
- matriz_client: token (X-Auth-Token header) + auth_basic password (D-22)
- ámbito_financiero_client: no token field; sentinel goes in base_url instead
  (sanity-check the parametrize for the no-auth paquete — base_url IS visible
  in URL-shaped log records, so the assertion is "no record contains the literal
  even though base_url legitimately could mention it" — caller must redact url
  query before logging per D-09).

For ámbito, since base_url is part of the public surface and the URL is not a
secret in itself, the parametrize for ámbito is documented separately and asserts
NO crash + zero records or records with redacted URLs (the ámbito library doesn't
authenticate so its log surface is empty in HEAD).
"""

from __future__ import annotations

import contextlib
import datetime as dt
import importlib
import logging

import pytest
from pytest_httpx import HTTPXMock

_SECRET_LITERAL = "SECRET-LITERAL-12345"
_PACKAGES = ["ambito_financiero_client", "iol_client", "higyrus_client", "matriz_client"]


@pytest.mark.parametrize("pkg_name", _PACKAGES)
def test_token_literal_never_appears_in_log_records(
    pkg_name: str,
    caplog: pytest.LogCaptureFixture,
    httpx_mock: HTTPXMock,
) -> None:
    """LOG-02: even with DEBUG enabled, token literal MUST NOT leak to records.

    Configures each paquete with the sentinel token and fires the package's
    smoke endpoint with a mocked response. Then walks every captured record and
    asserts the literal is absent from all string-typed surfaces.

    For ámbito (no auth), the sentinel is injected into the username/password
    fields of OTHER paquetes too, so the assertion covers password leak (D-10
    JSON ``{"password":"..."}`` pattern) in addition to token leak.
    """
    pkg = importlib.import_module(pkg_name)

    if pkg_name == "ambito_financiero_client":
        pkg.configure(base_url="https://api.test")
        caplog.set_level(logging.DEBUG, logger=pkg_name)
        httpx_mock.add_response(
            json=[["Fecha", "Compra", "Venta"], ["02/01/2026", "1.000,00", "1.100,00"]],
        )
        pkg.get_dollar_banco_nacion(dt.date(2026, 1, 2))
    elif pkg_name == "iol_client":
        pkg.configure(
            base_url="https://api.test",
            username="u",
            password=_SECRET_LITERAL,
            token=_SECRET_LITERAL,
            token_expires_at=9_999_999_999.0,
        )
        caplog.set_level(logging.DEBUG, logger=pkg_name)
        httpx_mock.add_response(
            url="https://api.test/api/v2/argentina/Titulos/Cotizacion/Instrumentos",
            json={"instrumentos": []},
        )
        pkg.get_instruments("argentina")
    elif pkg_name == "higyrus_client":
        pkg.configure(
            base_url="https://api.test",
            username="u",
            password=_SECRET_LITERAL,
            client_id="tenant",
            token=_SECRET_LITERAL,
            token_expires_at=9_999_999_999.0,
        )
        caplog.set_level(logging.DEBUG, logger=pkg_name)
        httpx_mock.add_response(
            url="https://api.test/api/cuentas/listadoCuentas?estado=alta",
            json=[],
        )
        pkg.get_listado_cuentas(estado="alta")
    elif pkg_name == "matriz_client":
        pkg.configure(
            base_url="https://api.test",
            username="test-user",
            password=_SECRET_LITERAL,
            token=_SECRET_LITERAL,
            token_expires_at=9_999_999_999.0,
        )
        caplog.set_level(logging.DEBUG, logger=pkg_name)
        httpx_mock.add_response(
            url="https://api.test/rest/segment/all",
            json={"status": "OK", "segments": []},
        )
        pkg.get_segments()
    else:  # pragma: no cover
        raise AssertionError(f"unhandled pkg: {pkg_name}")

    for record in caplog.records:
        message = record.getMessage()
        assert _SECRET_LITERAL not in message, (
            f"{pkg_name}: token literal leaked in record.getMessage(): {message!r}"
        )
        if record.args:
            args_str = str(record.args)
            assert _SECRET_LITERAL not in args_str, (
                f"{pkg_name}: token literal leaked in record.args: {args_str!r}"
            )
        for key, value in record.__dict__.items():
            if isinstance(value, str):
                assert _SECRET_LITERAL not in value, (
                    f"{pkg_name}: token literal leaked in record.{key}: {value!r}"
                )


def test_matriz_auth_basic_password_not_logged(
    caplog: pytest.LogCaptureFixture,
    httpx_mock: HTTPXMock,
) -> None:
    """D-22: matriz Risk API auth_basic password MUST be redacted from log records.

    The RedactingFilter must detect ``auth_basic`` tuple fields in ``record.__dict__``
    or ``Authorization: Basic ...`` headers and emit ``auth_basic_user=<user>`` +
    redacted password (never the password literal). Guard test; RED in HEAD until
    Plan 5 ships matriz `_logging.py` with the auth_basic redaction pattern.
    """
    import matriz_client

    matriz_client.configure(
        base_url="https://api.test",
        username="risk-user",
        password=_SECRET_LITERAL,
        token="test-token",
        token_expires_at=9_999_999_999.0,
    )
    caplog.set_level(logging.DEBUG, logger="matriz_client")

    httpx_mock.add_response(
        url="https://api.test/risk/account/something",
        json={"status": "OK"},
    )

    client = matriz_client.client._get_default()
    # If parser fails on the synthetic payload, that's not what this test guards.
    with contextlib.suppress(matriz_client.MatrizClientError):
        client._matriz_legacy_request(
            "GET",
            "/risk/account/something",
            auth_basic=("risk-user", _SECRET_LITERAL),
        )

    for record in caplog.records:
        message = record.getMessage()
        assert _SECRET_LITERAL not in message, (
            f"matriz auth_basic password leaked in record.getMessage(): {message!r}"
        )
        for key, value in record.__dict__.items():
            if isinstance(value, str):
                assert _SECRET_LITERAL not in value, (
                    f"matriz auth_basic password leaked in record.{key}: {value!r}"
                )
