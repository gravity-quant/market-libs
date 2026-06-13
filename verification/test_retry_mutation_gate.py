"""Cross-cutting mutation gate guard — POST/non-idempotent calls NEVER retry on 503.

Phase 8 D-01, D-07, D-26, RELY-03 / Pitfall 4. Wave 1 tests-first guard test;
fails RED in HEAD (no `_transport.py` retry loop exists yet). Plans 2-5 turn it
GREEN when each package ships its `RetryTransport` with the `idempotent` gate.

The invariant asserted here is the CRITICAL "duplicate matriz order" prevention:
matriz Primary API uses HTTP **GET** for ``new_order`` (Primary API quirk), so a
method-based retry gate (the default in most retry libraries) would silently retry
mutations on 503. The mutation gate MUST be ``request.extensions["idempotent"]``
set by the shell ``_request()`` from ``RequestSpec.idempotent`` — never method-based.

Two parametrize tables in this file:

1. ``_MUTATING_CALLS`` — for each auth paquete, call the lowest-level mutating
   surface that exists today and assert ``len(httpx_mock.get_requests()) == 1``
   even with 503 mocked twice. Matches Phase 7 D-13 forward-decl
   ``RequestSpec.idempotent: bool = False`` (default — POST/new_order).
2. ``_IDEMPOTENT_GET_CALLS`` — for each auth paquete, call a GET surface and
   assert that AFTER Phase 8 Plans 2-5 land, 503 mocked twice produces ``max_attempts``
   wire requests (currently 1 — will turn GREEN as Plans 2-5 add retry).
"""

from __future__ import annotations

import importlib
from typing import Any

import httpx
import pytest
from pytest_httpx import HTTPXMock


def _configure_pkg(pkg: Any, pkg_name: str) -> None:
    """Configure each paquete with sentinel creds + cached token to skip auth flow."""
    if pkg_name == "ambito_financiero_client":
        pkg.configure(base_url="https://api.test")
    elif pkg_name == "iol_client":
        pkg.configure(
            base_url="https://api.test",
            username="u",
            password="p",
            token="test-token",
            token_expires_at=9_999_999_999.0,
        )
    elif pkg_name == "higyrus_client":
        pkg.configure(
            base_url="https://api.test",
            username="u",
            password="p",
            client_id="tenant",
            token="test-token",
            token_expires_at=9_999_999_999.0,
        )
    elif pkg_name == "matriz_client":
        pkg.configure(
            base_url="https://api.test",
            username="test-user",
            password="test-pass",
            token="test-token",
            token_expires_at=9_999_999_999.0,
        )
    else:  # pragma: no cover
        raise AssertionError(f"unhandled package: {pkg_name}")


# Mutating surfaces per paquete (lowest-level mutating call available).
# ámbito has NO mutating endpoints (all-GET scraping) — excluded here; it appears
# in _IDEMPOTENT_GET_CALLS below.
# iol login is marked idempotent=True per D-03 (replay-safe) — NOT a mutation gate
# test; use the _IDEMPOTENT_GET_CALLS half. The truly mutating iol surfaces don't
# exist as top-level fns today (trade execution is Phase 9+).
# matriz: new_order is the canonical Primary API quirk — HTTP GET that MUST NOT retry.
_MUTATING_CALLS: list[tuple[str, str, dict[str, Any]]] = [
    (
        "matriz_client",
        "new_order",
        {
            "symbol": "GGAL",
            "side": "BUY",
            "qty": 1,
            "account": "test",
            "price": 100.0,
        },
    ),
]


def _expected_error_types(pkg: Any, pkg_name: str) -> tuple[type[Exception], ...]:
    """Return the tuple of exception types that may surface from a 503 response.

    Includes the package's top-level error base AND ``httpx.HTTPStatusError``
    because some paquetes (e.g. matriz) currently call ``resp.raise_for_status()``
    directly and have not yet wrapped 5xx into typed exceptions. Phase 8 Plans 2-5
    add the typed wrapping; tests stay tolerant pre/post for the cross-cutting Wave 1.
    """
    if pkg_name == "ambito_financiero_client":
        return (pkg.AmbitoFinancieroClientError, httpx.HTTPStatusError)
    if pkg_name == "iol_client":
        return (pkg.IOLClientError, httpx.HTTPStatusError)
    if pkg_name == "higyrus_client":
        return (pkg.HigyrusClientError, httpx.HTTPStatusError)
    if pkg_name == "matriz_client":
        return (pkg.MatrizClientError, httpx.HTTPStatusError)
    raise AssertionError(f"unhandled pkg: {pkg_name}")  # pragma: no cover


@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
@pytest.mark.parametrize(("pkg_name", "fn_name", "kwargs"), _MUTATING_CALLS)
def test_mutating_call_never_retries_against_503(
    pkg_name: str,
    fn_name: str,
    kwargs: dict[str, Any],
    httpx_mock: HTTPXMock,
) -> None:
    """RELY-03: mutating call MUST emit exactly 1 wire request even against mock 503.

    Failure means the mutation gate is broken — duplicate-order risk on matriz
    Primary API (Pitfall 4 / D-01). Guard test; RED in HEAD waiting for Plans 2-5
    RetryTransport landing.
    """
    pkg = importlib.import_module(pkg_name)
    _configure_pkg(pkg, pkg_name)

    # Two 503 responses queued — second one would be consumed if retry happened.
    httpx_mock.add_response(status_code=503)
    httpx_mock.add_response(status_code=503)

    fn = getattr(pkg, fn_name)
    with pytest.raises(_expected_error_types(pkg, pkg_name)):
        fn(**kwargs)

    requests = httpx_mock.get_requests()
    assert len(requests) == 1, (
        f"{pkg_name}.{fn_name} emitted {len(requests)} wire requests against "
        f"503 — mutation gate broken. Expected exactly 1 (no retry on mutation)."
    )


# Idempotent GET surfaces per paquete — after Phase 8 Plans 2-5 land, these
# MUST retry up to max_attempts (default 2 per D-06). In HEAD (no _transport.py),
# this assertion fails RED with len == 1 — that is expected per D-26.
_IDEMPOTENT_GET_CALLS: list[tuple[str, str, dict[str, Any]]] = [
    ("iol_client", "get_instruments", {"pais": "argentina"}),
    ("higyrus_client", "get_listado_cuentas", {"estado": "alta"}),
    ("matriz_client", "get_segments", {}),
]


@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
@pytest.mark.parametrize(("pkg_name", "fn_name", "kwargs"), _IDEMPOTENT_GET_CALLS)
def test_idempotent_get_retries_on_503(
    pkg_name: str,
    fn_name: str,
    kwargs: dict[str, Any],
    httpx_mock: HTTPXMock,
) -> None:
    """RELY-01: idempotent GET on 503 retries up to max_attempts.

    Expected count after Phase 8 Plans 2-5: 2 requests (default max_attempts=2 per
    D-06 = 1 initial + 1 retry). In HEAD, this asserts len == 2 and FAILS RED —
    that is the by-design Wave 1 RED gate. Plans 2-5 turn GREEN.
    """
    pkg = importlib.import_module(pkg_name)
    _configure_pkg(pkg, pkg_name)

    # Two 503 responses queued; if retry policy is correctly in place,
    # both will be consumed and the final raise is RateLimitError or APIError.
    httpx_mock.add_response(status_code=503)
    httpx_mock.add_response(status_code=503)

    fn = getattr(pkg, fn_name)
    with pytest.raises(_expected_error_types(pkg, pkg_name)):
        fn(**kwargs)

    requests = httpx_mock.get_requests()
    # Phase 8 D-06 default max_attempts=2 → 1 initial + 1 retry = 2 wire requests.
    assert len(requests) == 2, (
        f"{pkg_name}.{fn_name} emitted {len(requests)} wire requests against "
        f"503 — expected 2 (1 initial + 1 retry per max_attempts=2). "
        f"RED in HEAD until Phase 8 Plans 2-5 land RetryTransport."
    )
