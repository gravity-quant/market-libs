"""Cross-cutting 401 re-auth-once guard — auth packages re-auth exactly once on 401.

Phase 8 D-02, D-23, D-26, RELY-04 / Pitfall 1+5. Wave 1 tests-first guard; fails
RED in HEAD (no 401 re-auth path in the shell ``_request()`` yet). Plans 3-5 turn
it GREEN when iol / higyrus / matriz Primary ship the re-auth flow in their shell.

The invariant: on 401 with stale token, the shell catches ``<Pkg>AuthError``, clears
``state.token``, calls ``_ensure_token()`` (which triggers the login wire request),
then retries the original request ONCE with the fresh token. ``AuthError`` MUST
NEVER appear in ``retry_on=`` of the transport — that would cause infinite-loop
retry storm with the same stale Bearer (Pitfall 1).

Three parametrize cases:
- ``iol_client``: ``POST /token`` for login → re-auth via OAuth2 password grant.
- ``higyrus_client``: ``POST /api/login`` → Bearer token refresh.
- ``matriz_client`` Primary: ``POST /auth/getToken`` → ``X-Auth-Token`` header.
- ``matriz_client`` Risk (D-23): auth_basic — NO re-auth attempted, AuthError surfaces
  directly. Covered in ``test_matriz_risk_401_no_reauth``.
- ámbito SKIPPED — no auth surface at all.
"""

from __future__ import annotations

import importlib

import pytest
from pytest_httpx import HTTPXMock

# Auth packages with re-auth-once invariant. ámbito skipped (no auth).
# matriz Risk API has its own carve-out per D-23 — tested in a dedicated case below.
_AUTH_PACKAGES = ["iol_client", "higyrus_client", "matriz_client"]


@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
@pytest.mark.parametrize("pkg_name", _AUTH_PACKAGES)
def test_401_then_login_then_200_triggers_exactly_one_reauth(
    pkg_name: str,
    httpx_mock: HTTPXMock,
) -> None:
    """RELY-04: 401 → login → 200 chain emits exactly 3 wire requests, refreshed token.

    Wire sequence:
      1. Original GET with STALE-TOKEN → 401
      2. Login flow (POST /token | /api/login | /auth/getToken) → 200 with FRESH-TOKEN
      3. Retry original GET with FRESH-TOKEN → 200 with payload

    Last request MUST carry FRESH-TOKEN in Authorization or X-Auth-Token header.
    Guard test; RED in HEAD until Plans 3-5 add re-auth to each shell.
    """
    pkg = importlib.import_module(pkg_name)

    if pkg_name == "iol_client":
        pkg.configure(
            base_url="https://api.test",
            username="u",
            password="p",
            token="STALE-TOKEN",
            token_expires_at=9_999_999_999.0,
        )
        # 1) original GET → 401
        httpx_mock.add_response(
            url="https://api.test/api/v2/argentina/Titulos/Cotizacion/Instrumentos",
            status_code=401,
        )
        # 2) login → 200 with new token
        httpx_mock.add_response(
            url="https://api.test/token",
            json={
                "access_token": "FRESH-TOKEN",
                "expires_in": 900,
                "refresh_token": "R",
                "token_type": "bearer",
            },
        )
        # 3) retry → 200 with payload
        httpx_mock.add_response(
            url="https://api.test/api/v2/argentina/Titulos/Cotizacion/Instrumentos",
            json={"instrumentos": []},
        )
        pkg.get_instruments("argentina")
        header_name = "Authorization"
        expected_prefix = "Bearer "
    elif pkg_name == "higyrus_client":
        pkg.configure(
            base_url="https://api.test",
            username="u",
            password="p",
            client_id="tenant",
            token="STALE-TOKEN",
            token_expires_at=9_999_999_999.0,
        )
        httpx_mock.add_response(
            url="https://api.test/api/cuentas/listadoCuentas?estado=alta",
            status_code=401,
        )
        httpx_mock.add_response(
            url="https://api.test/api/login",
            json={"token": "FRESH-TOKEN"},
        )
        httpx_mock.add_response(
            url="https://api.test/api/cuentas/listadoCuentas?estado=alta",
            json=[],
        )
        pkg.get_listado_cuentas(estado="alta")
        header_name = "Authorization"
        expected_prefix = "Bearer "
    elif pkg_name == "matriz_client":
        pkg.configure(
            base_url="https://api.test",
            username="test-user",
            password="test-pass",
            token="STALE-TOKEN",
            token_expires_at=9_999_999_999.0,
        )
        httpx_mock.add_response(
            url="https://api.test/rest/segment/all",
            status_code=401,
        )
        httpx_mock.add_response(
            url="https://api.test/auth/getToken",
            headers={"X-Auth-Token": "FRESH-TOKEN"},
        )
        httpx_mock.add_response(
            url="https://api.test/rest/segment/all",
            json={"status": "OK", "segments": []},
        )
        pkg.get_segments()
        header_name = "X-Auth-Token"
        expected_prefix = ""
    else:  # pragma: no cover
        raise AssertionError(f"unhandled pkg: {pkg_name}")

    requests = httpx_mock.get_requests()
    assert len(requests) == 3, (
        f"{pkg_name}: expected 3 wire requests (1 stale + 1 login + 1 fresh), "
        f"got {len(requests)}. RED in HEAD until Plans 3-5 add re-auth flow."
    )
    last = requests[-1]
    last_auth = last.headers.get(header_name, "")
    assert "FRESH-TOKEN" in last_auth, (
        f"{pkg_name}: expected FRESH-TOKEN in retry's {header_name} header, "
        f"got: {last_auth!r}"
    )
    assert expected_prefix == "" or last_auth.startswith(expected_prefix), (
        f"{pkg_name}: expected {expected_prefix!r} prefix in {header_name}, got {last_auth!r}"
    )


@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
@pytest.mark.parametrize("pkg_name", _AUTH_PACKAGES)
def test_401_then_login_then_401_raises_auth_error(
    pkg_name: str,
    httpx_mock: HTTPXMock,
) -> None:
    """RELY-04: 401 → login → 401 chain raises AuthError and emits exactly 3 wire
    requests (no third retry — re-auth happens exactly ONCE per D-02).

    Failure here means the shell is looping (Pitfall 1 — AuthError in retry_on=)
    or re-auth happens multiple times. Guard test; RED in HEAD.
    """
    pkg = importlib.import_module(pkg_name)
    auth_error_cls: type[Exception]

    if pkg_name == "iol_client":
        pkg.configure(
            base_url="https://api.test",
            username="u",
            password="p",
            token="STALE-TOKEN",
            token_expires_at=9_999_999_999.0,
        )
        auth_error_cls = pkg.IOLAuthError
        httpx_mock.add_response(
            url="https://api.test/api/v2/argentina/Titulos/Cotizacion/Instrumentos",
            status_code=401,
        )
        httpx_mock.add_response(
            url="https://api.test/token",
            json={
                "access_token": "FRESH-TOKEN",
                "expires_in": 900,
                "refresh_token": "R",
                "token_type": "bearer",
            },
        )
        httpx_mock.add_response(
            url="https://api.test/api/v2/argentina/Titulos/Cotizacion/Instrumentos",
            status_code=401,
        )
        with pytest.raises(auth_error_cls):
            pkg.get_instruments("argentina")
    elif pkg_name == "higyrus_client":
        pkg.configure(
            base_url="https://api.test",
            username="u",
            password="p",
            client_id="tenant",
            token="STALE-TOKEN",
            token_expires_at=9_999_999_999.0,
        )
        auth_error_cls = pkg.HigyrusAuthError
        httpx_mock.add_response(
            url="https://api.test/api/cuentas/listadoCuentas?estado=alta",
            status_code=401,
        )
        httpx_mock.add_response(
            url="https://api.test/api/login",
            json={"token": "FRESH-TOKEN"},
        )
        httpx_mock.add_response(
            url="https://api.test/api/cuentas/listadoCuentas?estado=alta",
            status_code=401,
        )
        with pytest.raises(auth_error_cls):
            pkg.get_listado_cuentas(estado="alta")
    elif pkg_name == "matriz_client":
        pkg.configure(
            base_url="https://api.test",
            username="test-user",
            password="test-pass",
            token="STALE-TOKEN",
            token_expires_at=9_999_999_999.0,
        )
        # matriz exception hierarchy: PrimaryAPIError / AuthenticationError
        auth_error_cls = pkg.AuthenticationError
        httpx_mock.add_response(
            url="https://api.test/rest/segment/all",
            status_code=401,
        )
        httpx_mock.add_response(
            url="https://api.test/auth/getToken",
            headers={"X-Auth-Token": "FRESH-TOKEN"},
        )
        httpx_mock.add_response(
            url="https://api.test/rest/segment/all",
            status_code=401,
        )
        with pytest.raises(auth_error_cls):
            pkg.get_segments()
    else:  # pragma: no cover
        raise AssertionError(f"unhandled pkg: {pkg_name}")

    requests = httpx_mock.get_requests()
    assert len(requests) == 3, (
        f"{pkg_name}: expected exactly 3 wire requests (1 + login + 1 retry), "
        f"got {len(requests)}. Re-auth must happen exactly once per D-02."
    )


def test_matriz_risk_api_401_does_not_reauth(httpx_mock: HTTPXMock) -> None:
    """D-23: matriz Risk API uses auth_basic — 401 means bad creds, NO re-auth attempt.

    The shell ``_request()`` MUST detect ``spec.auth_basic is not None`` (Risk path)
    and re-raise AuthError on 401 immediately, without calling ``_ensure_token()``.

    This guard fires the lowest-level matriz Risk surface available today and asserts
    exactly 1 wire request + AuthenticationError raised. RED in HEAD until Plan 5
    adds the auth_basic-branch carve-out.
    """
    import matriz_client

    matriz_client.configure(
        base_url="https://api.test",
        username="risk-user",
        password="risk-pass",
        token="test-token",
        token_expires_at=9_999_999_999.0,
    )

    # Risk API endpoints use the legacy `_matriz_legacy_request` path with auth_basic.
    # We exercise it directly via the Risk-style request — most public Risk surfaces
    # are in `risk_*` builder modules. For the cross-cutting guard, we assert the
    # shell branch via a synthesized GET that uses auth_basic.
    client = matriz_client.client._get_default()
    httpx_mock.add_response(
        url="https://api.test/risk/account/something",
        status_code=401,
    )

    with pytest.raises(matriz_client.AuthenticationError):
        # `_matriz_legacy_request` is the documented Risk path (D-23).
        client._matriz_legacy_request(
            "GET",
            "/risk/account/something",
            auth_basic=("risk-user", "risk-pass"),
        )

    requests = httpx_mock.get_requests()
    assert len(requests) == 1, (
        f"matriz Risk: expected exactly 1 wire request on 401 (no re-auth attempted "
        f"per D-23 — auth_basic has no token to refresh), got {len(requests)}."
    )
