"""Guard test: configured base_url reaches the wire-level request URL (no-auth path).

Ambito has no auth: this guard documents the configured-base_url -> wire-URL path.
Treated as the 'skip-style' no-auth analog of the per-package guard pattern that the
authed packages use for tokens. Same intent as the iol/higyrus/matriz guards: prove
that the fixture-to-wire path is intact so a future refactor cannot silently break
the test plumbing.

Phase 06 Plan 02 pattern: this file calls ``ambito_financiero_client.configure(
base_url="https://configured.test")`` and asserts the URL of the next outgoing
request contains ``configured.test``. Plan 04 (ambito) will keep this file as-is
during the per-package refactor (no token semantics to migrate) but the test must
still re-run green after the Client class skeleton lands.

See: .planning/phases/06-compat-safety-net-client-class-skeleton/06-CONTEXT.md D-12
and 06-RESEARCH.md Pattern 6 (ambito snippet).
"""

from __future__ import annotations

import datetime as dt

from pytest_httpx import HTTPXMock

import ambito_financiero_client


def test_ambito_sync_configured_base_url_reaches_request_url(
    httpx_mock: HTTPXMock,
) -> None:
    """SYNC: ``configure(base_url=...)`` reaches the wire URL of the next request."""
    ambito_financiero_client.configure(base_url="https://configured.test")

    httpx_mock.add_response(
        url="https://configured.test/dolarnacion/historico-general/2026-01-02/2026-01-02",
        json=[["Fecha", "Compra", "Venta"], ["02/01/2026", "1.000,00", "1.100,00"]],
    )

    ambito_financiero_client.get_dollar_banco_nacion(dt.date(2026, 1, 2))

    [req] = httpx_mock.get_requests()
    assert "configured.test" in str(req.url)


async def test_ambito_async_configured_base_url_reaches_request_url(
    httpx_mock: HTTPXMock,
) -> None:
    """ASYNC: ``aio.configure(base_url=...)`` reaches the wire URL of the next request."""
    from ambito_financiero_client import aio

    aio.configure(base_url="https://configured.test")

    httpx_mock.add_response(
        url="https://configured.test/dolarnacion/historico-general/2026-01-02/2026-01-02",
        json=[["Fecha", "Compra", "Venta"], ["02/01/2026", "1.000,00", "1.100,00"]],
    )

    await aio.get_dollar_banco_nacion(dt.date(2026, 1, 2))

    [req] = httpx_mock.get_requests()
    assert "configured.test" in str(req.url)
