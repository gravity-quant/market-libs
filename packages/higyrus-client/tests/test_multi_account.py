"""Regression test for BUG-04 (HIGY multi-account iteration).

Phase 9 Plan 09-02 — D-08 / D-10 mocked regression. Validates that the
per-call ``id_cuenta`` pattern emits one wire request per account, with
the correct ``id_cuenta`` in the URL path.

The autouse ``_configure_sync`` fixture in ``conftest.py`` pre-loads
``token="test-token"`` + ``token_expires_at=9_999_999_999.0`` so no
additional setup is required.
"""

from __future__ import annotations

import datetime as dt

from pytest_httpx import HTTPXMock

import higyrus_client


def test_multi_account_iteration_via_per_call_id_cuenta(httpx_mock: HTTPXMock) -> None:
    """BUG-04 (D-08 per-call only): loop over 2 cuentas → 2 distinct wire requests.

    The caller iterates ``for acct in (a, b): get_movimientos(id_cuenta=acct, ...)``.
    Each call MUST produce its own outgoing HTTP request whose URL path embeds
    the correct ``id_cuenta``. This guards against any future refactor that
    might inadvertently cache the account id at the client level (e.g.,
    reintroducing the ``_state.account_id`` field removed in D-09).

    Wire format note: ``_params.format_date`` emits ``dd/mm/yyyy``, which
    httpx URL-encodes the ``/`` as ``%2F`` (see
    ``test_client.py::test_get_movimientos_serializa_fechas_dd_mm_yyyy``).
    """
    today = dt.date(2026, 6, 13)
    httpx_mock.add_response(
        method="GET",
        url=(
            "https://api.test/api/cuentas/5208/movimientos"
            "?fechaDesde=13%2F06%2F2026&fechaHasta=13%2F06%2F2026"
        ),
        json=[],
    )
    httpx_mock.add_response(
        method="GET",
        url=(
            "https://api.test/api/cuentas/9999/movimientos"
            "?fechaDesde=13%2F06%2F2026&fechaHasta=13%2F06%2F2026"
        ),
        json=[],
    )

    for acct in ("5208", "9999"):
        higyrus_client.get_movimientos(
            id_cuenta=acct,
            fecha_desde=today,
            fecha_hasta=today,
        )

    requests = httpx_mock.get_requests()
    assert len(requests) == 2
    assert "/5208/" in str(requests[0].url)
    assert "/9999/" in str(requests[1].url)
