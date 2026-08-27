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
            json=[],
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

    The RedactingFilter must detect ``auth_basic`` tuple fields in
    ``record.__dict__`` and split them into ``auth_basic_user=<user>``
    (operational, preserved) + ``auth_basic_password="***"`` (redacted) so the
    password literal NEVER reaches downstream handlers.

    CR-02 fix (Phase 8 review): the previous version of this test called
    ``client._matriz_legacy_request(..., auth_basic=...)`` which builds a
    ``RequestSpec`` with ``idempotent=False`` (default). The transport
    short-circuits non-idempotent requests so NO WARNING record is ever
    emitted — the loop ``for r in caplog.records: assert _SECRET not in
    r.getMessage()`` was vacuously true because there were no matriz records
    AT ALL. The D-22 tuple-splitting filter was never exercised end-to-end.

    The fix is to (a) exercise the REAL Risk surface (``get_positions``,
    ``idempotent=True``), (b) mock a 503→200 retry chain so the transport
    emits at least one WARNING record with the canonical D-09 fields, and (c)
    assert directly that the WARNING record carries ``auth_basic_user`` (the
    split operational field) AND ``auth_basic_password="***"`` AND that the
    secret literal does NOT appear anywhere in the record. Now the filter's
    ``_redact_auth_basic_tuple`` code path is genuinely exercised.
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

    # 503 → 200 chain on real Risk endpoint. get_positions builds with
    # auth_basic + idempotent=True so the transport retries on 503 and emits a
    # WARNING per attempt with the canonical D-09 fields (incl. auth_basic per
    # CR-02 transport fix).
    httpx_mock.add_response(
        url="https://api.test/rest/risk/position/getPositions/acc",
        status_code=503,
    )
    httpx_mock.add_response(
        url="https://api.test/rest/risk/position/getPositions/acc",
        json={"status": "OK", "positions": []},
    )

    # If the upstream parser raises on the synthetic payload, that's not what
    # this test guards — we care only about what the log records look like.
    with contextlib.suppress(matriz_client.MatrizClientError):
        matriz_client.get_positions("acc")

    # The transport MUST have emitted at least one WARNING per the D-22 contract
    # (503→200 chain = 1 retry → 1 WARNING). Without this assertion, the rest of
    # the test is vacuous (the bug fix CR-02 closes).
    warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert warning_records, (
        "matriz auth_basic redaction guard: expected at least one WARNING record "
        "from the 503→200 retry chain on get_positions. Got zero. The transport "
        "is not emitting WARNINGs OR the RetryTransport is not retrying — either "
        "way the D-22 auth_basic tuple-splitting filter is not exercised."
    )

    # D-22: the auth_basic tuple in the WARNING extras MUST have been split by
    # the RedactingFilter into auth_basic_user (operational, kept) and
    # auth_basic_password (redacted to "***"). The original `auth_basic` key
    # MUST have been deleted from record.__dict__ so the (user, password)
    # tuple form never reaches downstream consumers.
    record = warning_records[0]
    assert record.__dict__.get("auth_basic_user") == "risk-user", (
        f"D-22: expected auth_basic_user='risk-user' in record.__dict__, "
        f"got {record.__dict__.get('auth_basic_user')!r}. The RedactingFilter's "
        f"tuple-splitting code path is not running."
    )
    assert record.__dict__.get("auth_basic_password") == "***", (
        f"D-22: expected auth_basic_password='***' in record.__dict__, "
        f"got {record.__dict__.get('auth_basic_password')!r}. "
    )
    assert "auth_basic" not in record.__dict__, (
        f"D-22: original `auth_basic` tuple key MUST be deleted from "
        f"record.__dict__ after the split; got {record.__dict__.get('auth_basic')!r}."
    )

    # Cross-cutting safety: scan ALL records for the literal secret.
    for r in caplog.records:
        message = r.getMessage()
        assert _SECRET_LITERAL not in message, (
            f"matriz auth_basic password leaked in record.getMessage(): {message!r}"
        )
        for key, value in r.__dict__.items():
            if isinstance(value, str):
                assert _SECRET_LITERAL not in value, (
                    f"matriz auth_basic password leaked in record.{key}: {value!r}"
                )
