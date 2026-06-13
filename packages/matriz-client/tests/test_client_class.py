"""Skeleton tests for matriz-client ``Client`` class (Phase 6 Plan 06).

Covers:
- Lifecycle: ``__init__``, context manager, ``close()`` idempotency.
- Repr redaction (password/token never appear in plain text).
- Pickle/deepcopy raise (D-04).
- ``configure()`` carry-forward via the new default singleton.
- Explicit-instance isolation (instance state != default state).
- D-22 matriz peculiarity: ``Client.login()`` reads ``X-Auth-Token`` from
  *response headers* (not from JSON body).
- ``_request`` sends ``X-Auth-Token`` header (not ``Authorization``).
- PEP 562 shim forwards ``_base_url`` (Open Q #4) + ``_session``/``_client``
  (Pitfall #5).
- PEP 562 shim raises ``AttributeError`` for ``_user``/``_password``.
- W5 closure: no callable module-level ``_ensure_token`` in ``__dict__``.
- ``verification/mutation_gate.py`` reads via the shim.
"""

from __future__ import annotations

import copy
import pickle

import pytest
from pytest_httpx import HTTPXMock

import matriz_client
from matriz_client import client as _client_mod
from matriz_client.client import Client

# ------------------------------------------------------------------
# Lifecycle
# ------------------------------------------------------------------


def test_client_init_default_state_from_env() -> None:
    c = Client()
    assert c._state.base_url
    # username/password are env-driven; just check the attribute exists.
    assert isinstance(c._state.username, str)
    assert isinstance(c._state.password, str)
    assert c._state.token is None
    assert c._state.token_expires_at == 0.0
    assert c._state.http_client is None


def test_client_init_kwargs_override_env() -> None:
    c = Client(
        base_url="https://example.test",
        username="u",
        password="p",
        token="t",
        token_expires_at=123.0,
    )
    assert c._state.base_url == "https://example.test"
    assert c._state.username == "u"
    assert c._state.password == "p"
    assert c._state.token == "t"
    assert c._state.token_expires_at == 123.0


def test_client_context_manager_closes_http_client() -> None:
    with Client(base_url="https://example.test") as c:
        # Trigger lazy http client creation.
        c._ensure_http_client()
        assert c._state.http_client is not None
    # After __exit__ the http client is closed and reset to None.
    assert c._state.http_client is None


def test_client_close_is_idempotent() -> None:
    c = Client()
    c.close()
    c.close()  # second call must not raise


def test_client_repr_redacts_password_and_token() -> None:
    c = Client(
        base_url="https://x",
        username="u",
        password="SECRETPW",
        token="SECRETTOKEN",
    )
    text = repr(c)
    assert "SECRETPW" not in text
    assert "SECRETTOKEN" not in text
    assert "password='***'" in text or 'password="***"' in text
    assert "token='***'" in text or 'token="***"' in text


def test_client_pickle_raises() -> None:
    c = Client()
    with pytest.raises((TypeError, NotImplementedError)):
        pickle.dumps(c)


def test_client_deepcopy_raises() -> None:
    c = Client()
    with pytest.raises((TypeError, NotImplementedError)):
        copy.deepcopy(c)


# ------------------------------------------------------------------
# Login + token semantics (D-22: read header, not body)
# ------------------------------------------------------------------


def test_login_stores_token_from_x_auth_token_header(httpx_mock: HTTPXMock) -> None:
    c = Client(base_url="https://api.test", username="u", password="p")
    httpx_mock.add_response(
        url="https://api.test/auth/getToken",
        method="POST",
        headers={"X-Auth-Token": "MATR-TOK"},
    )
    token = c.login()
    assert token == "MATR-TOK"
    assert c._state.token == "MATR-TOK"
    assert c._state.token_expires_at > 0


def test_login_missing_header_raises_auth_error(httpx_mock: HTTPXMock) -> None:
    from matriz_client.exceptions import AuthenticationError

    c = Client(base_url="https://api.test", username="u", password="p")
    httpx_mock.add_response(
        url="https://api.test/auth/getToken",
        method="POST",
        headers={},
    )
    with pytest.raises(AuthenticationError):
        c.login()


def test_login_missing_credentials_raises_auth_error() -> None:
    from matriz_client.exceptions import AuthenticationError

    c = Client(base_url="https://api.test", username="", password="")
    with pytest.raises(AuthenticationError):
        c.login()


# ------------------------------------------------------------------
# _request sends X-Auth-Token (not Authorization Bearer)
# ------------------------------------------------------------------


def test_request_sends_x_auth_token_header(httpx_mock: HTTPXMock) -> None:
    c = Client(
        base_url="https://api.test",
        username="u",
        password="p",
        token="LIVE-TOK",
        token_expires_at=9_999_999_999.0,
    )
    httpx_mock.add_response(
        url="https://api.test/rest/anything?symbol=DLR",
        method="GET",
        match_headers={"X-Auth-Token": "LIVE-TOK"},
        json={"status": "OK"},
    )
    # Phase 7 D-03: _request takes a RequestSpec and returns httpx.Response;
    # back-compat wrapper preserves the original dict-decoded contract.
    c._matriz_legacy_request("GET", "/rest/anything", params={"symbol": "DLR"})


# ------------------------------------------------------------------
# configure() carry-forward
# ------------------------------------------------------------------


def test_configure_updates_default_and_resets_token() -> None:
    matriz_client.configure(
        base_url="https://api.test",
        username="test-user",
        password="test-pass",
        token="pre-existing",
        token_expires_at=9_999_999_999.0,
    )
    default = matriz_client._get_default()
    assert default._state.base_url == "https://api.test"
    assert default._state.username == "test-user"
    assert default._state.token == "pre-existing"

    # Reconfigure base_url: token cache resets to None.
    matriz_client.configure(base_url="https://api2.test")
    default = matriz_client._get_default()
    assert default._state.base_url == "https://api2.test"
    assert default._state.token is None
    assert default._state.token_expires_at == 0.0


def test_explicit_instance_isolated_from_default() -> None:
    matriz_client.configure(
        base_url="https://api.test",
        username="default-u",
        password="default-p",
        token="default-tok",
        token_expires_at=9_999_999_999.0,
    )
    c = Client(base_url="https://other.test", username="x", password="y")
    assert c._state.base_url == "https://other.test"
    default = matriz_client._get_default()
    assert default._state.base_url == "https://api.test"


# ------------------------------------------------------------------
# PEP 562 shim (Open Q #4 — _base_url forwarded for matriz)
# ------------------------------------------------------------------


def test_pep_562_shim_forwards_base_url() -> None:
    matriz_client.configure(base_url="https://shimtest.example")
    assert _client_mod._base_url == "https://shimtest.example"


def test_pep_562_shim_forwards_token_and_token_ts() -> None:
    matriz_client.configure(
        base_url="https://api.test",
        username="u",
        password="p",
        token="abc",
        token_expires_at=12345.0,
    )
    assert _client_mod._token == "abc"
    assert _client_mod._token_ts == 12345.0


def test_pep_562_shim_forwards_session_and_client() -> None:
    matriz_client.configure(base_url="https://api.test", username="u", password="p")
    default = matriz_client._get_default()
    # Trigger lazy http client creation.
    default._ensure_http_client()
    # Both _session (legacy matriz name) and _client (consistency) forward.
    assert _client_mod._session is default._state.http_client
    assert _client_mod._client is default._state.http_client


def test_pep_562_shim_raises_for_user() -> None:
    with pytest.raises(AttributeError):
        _ = _client_mod._user


def test_pep_562_shim_raises_for_password() -> None:
    with pytest.raises(AttributeError):
        _ = _client_mod._password


def test_no_module_level_ensure_token_callable() -> None:
    """W5 closure: no callable ``_ensure_token`` in module ``__dict__``."""
    assert "_ensure_token" not in _client_mod.__dict__


# ------------------------------------------------------------------
# mutation_gate.py reads through the shim (Open Q #4 enforcement)
# ------------------------------------------------------------------


def test_mutation_gate_reads_via_shim(monkeypatch: pytest.MonkeyPatch) -> None:
    from verification.mutation_gate import mutating_allowed

    matriz_client.configure(base_url="https://api.remarkets.primary.com.ar")
    monkeypatch.setenv("VERIFY_MUTATING", "1")
    assert mutating_allowed() is True


def test_mutation_gate_blocks_non_sandbox_through_shim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from verification.mutation_gate import mutating_allowed

    matriz_client.configure(base_url="https://api.primary.com.ar")
    monkeypatch.setenv("VERIFY_MUTATING", "1")
    assert mutating_allowed() is False


# ------------------------------------------------------------------
# ws_client uses default state base_url + ensure_token
# ------------------------------------------------------------------


def test_ws_client_url_derives_from_default_state_base_url() -> None:
    from matriz_client import ws_client as _ws

    matriz_client.configure(base_url="https://api.test")
    assert _ws._ws_url() == "wss://api.test"

    matriz_client.configure(base_url="http://localhost:8080")
    assert _ws._ws_url() == "ws://localhost:8080"


def test_ws_client_module_does_not_reference_legacy_module_globals() -> None:
    """W5 + ws_client migration: ensure ws_client.py uses _get_default(), not legacy globals."""
    import inspect

    from matriz_client import ws_client as _ws

    source = inspect.getsource(_ws)
    # ws_client must no longer touch the legacy module-level _base_url/_token
    # directly. We allow the shim names ONLY through the explicit
    # _get_default() accessor pattern.
    assert "_rest._base_url" not in source
    assert "_rest._ensure_token()" not in source
    assert "_rest._token" not in source


# ------------------------------------------------------------------
# Stub AsyncClient (Task 2 — Open Q #1 resolution)
# ------------------------------------------------------------------


async def test_async_stub_context_manager() -> None:
    from matriz_client.aio import AsyncClient

    async with AsyncClient() as c:
        pass
    # After __aexit__ the http client (if any) is closed.
    assert c._state.http_client is None


async def test_async_stub_aclose_idempotent() -> None:
    from matriz_client.aio import AsyncClient

    c = AsyncClient()
    await c.aclose()
    await c.aclose()  # second call must not raise


def test_async_stub_repr_redacted() -> None:
    from matriz_client.aio import AsyncClient

    c = AsyncClient(
        base_url="https://x",
        username="u",
        password="SECRETPW",
        token="SECRETTOKEN",
    )
    text = repr(c)
    assert "SECRETPW" not in text
    assert "SECRETTOKEN" not in text
    assert "password='***'" in text or 'password="***"' in text
    assert "token='***'" in text or 'token="***"' in text


def test_async_stub_pickle_raises() -> None:
    from matriz_client.aio import AsyncClient

    c = AsyncClient()
    with pytest.raises((TypeError, NotImplementedError)):
        pickle.dumps(c)


def test_async_stub_deepcopy_raises() -> None:
    from matriz_client.aio import AsyncClient

    c = AsyncClient()
    with pytest.raises((TypeError, NotImplementedError)):
        copy.deepcopy(c)


def test_matriz_module_aio_exposes_full_rest_surface() -> None:
    """Phase 10 Plan 10-02: aio.py is the FULL REST surface (stub grown).

    Replaces the Phase 6 ``..._exports_async_client_only`` stub-assertion now that
    Plan 10-02 lands the full async REST surface (REFAC-04 success criterion 1):
    22 endpoints + module-level delegators + ``configure`` + ``login`` + ``aclose``
    + ``_default_async_client`` singleton + PEP 562 shim. B8 lock-in still holds.
    """
    from matriz_client import aio as aio_mod

    assert hasattr(aio_mod, "AsyncClient")
    # The full surface MUST expose top-level shims and the delegators.
    assert hasattr(aio_mod, "configure")
    assert hasattr(aio_mod, "login")
    assert hasattr(aio_mod, "aclose")
    assert hasattr(aio_mod, "get_segments")
    assert hasattr(aio_mod, "new_order")
    assert hasattr(aio_mod, "cancel_order")
    assert hasattr(aio_mod, "replace_order")
    assert hasattr(aio_mod, "get_positions")
    # ``_default_async_client`` lazy singleton lives in the module (private).
    # Reading ``_get_default()`` is the public entry; the global itself is
    # private state, so we only assert the accessor exists.
    assert hasattr(aio_mod, "_get_default")
    # All 22 endpoint delegators + login + aclose must be present.
    expected = [
        "login",
        "get_segments",
        "get_all_instruments",
        "get_instruments_details",
        "get_instrument_detail",
        "get_instruments_by_cfi",
        "get_instruments_by_segment",
        "new_order",
        "replace_order",
        "cancel_order",
        "get_order_status",
        "get_order_history",
        "get_active_orders",
        "get_filled_orders",
        "get_all_orders",
        "get_order_by_exec_id",
        "get_market_data",
        "get_trades",
        "get_positions",
        "get_detailed_positions",
        "get_account_report",
        "aclose",
    ]
    missing = [n for n in expected if not hasattr(aio_mod, n)]
    assert not missing, f"missing module-level delegators: {missing}"


def test_matriz_client_exposes_async_client() -> None:
    """The flat namespace re-exports AsyncClient (CONTEXT.md success criterion 3)."""
    assert hasattr(matriz_client, "AsyncClient")
    assert "AsyncClient" in matriz_client.__all__
