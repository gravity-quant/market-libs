"""Cross-cutting `with_options(max_retries=N)` guard — Phase 13 ERG-01 (D-P2).

Phase 13 tests-first idiom (Phase 8 D-21 carry-forward): these 4 tests are
committed RED in Plan 1 HEAD because the `with_options(max_retries=N)` method
does not yet exist on any of the 4 Client/AsyncClient classes. They turn
GREEN incrementally as Plans 2-5 land per-package implementations
(Plan 2 turns the ámbito row green; Plan 5 turns all 4 green).

Coverage map (D-V1..D-V3, D-P2, SC#1..SC#3 ROADMAP):

- ``test_with_options_shares_http_client_and_token`` x 4 packages
  → SC#1 (resource leak; Anti-Pitfall 13). Asserts that the view shares
  ``_state`` and ``_state.http_client`` with the parent — no second TCP
  pool, no re-auth.

- ``test_with_options_does_not_bypass_mutation_gate_matriz`` (matriz only,
  **CRITICAL MERGE GATE** — Anti-Pitfall 14, money-on-the-line)
  → SC#2. matriz Primary API ``new_order`` (HTTP GET that mutates) MUST
  execute EXACTLY 1 outgoing request under 503 even when the caller
  bumps ``with_options(max_retries=10)``. Mutation gate (Phase 8 D-01,
  ``request.extensions["idempotent"] = False``) remains the absolute
  authority on retry permission.

- ``test_with_options_max_attempts_extension_honored`` x 4 packages
  → SC#3. Idempotent GET under 503: default ``max_retries=2`` → 3 wire
  requests; ``with_options(max_retries=10)`` → 11 wire requests. The
  ``request.extensions["max_attempts"]`` thread is end-to-end exercised.

- ``test_with_options_chaining_inner_wins`` x 4 packages
  → D-V2. ``c.with_options(5).with_options(10)._max_retries == 10`` and
  the parent's ``_max_retries`` stays at 2 (original untouched).

Configuration discipline (Phase 6 patterns): each test instantiates
``<pkg>.Client(...)`` directly (not via ``configure()`` + ``_get_default()``)
so per-test isolation is automatic, EXCEPT the matriz mutation-gate test
which mirrors the exact ``<specifics>`` D-P2 body and uses ``configure()`` —
the autouse fixture ``_reset_default_clients`` clears ``_default_client``
for every package between tests to prevent leakage.

This file is SEPARATE from ``verification/test_retry_mutation_gate.py``
(Phase 8 D-26) per D-P2 scope separation: the Phase 13 cross-cutting
tests live in their own file so per-Plan atomicity is preserved.
"""

from __future__ import annotations

import datetime as dt
import importlib
from collections.abc import Callable, Iterator
from typing import Any

import httpx
import pytest
from pytest_httpx import HTTPXMock

import ambito_financiero_client
import higyrus_client
import iol_client
import matriz_client

# ---------------------------------------------------------------------------
# Per-test isolation — clear each package's module-level _default_client so
# state from a prior test (e.g., a configure() call) does not leak.
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_default_clients() -> Iterator[None]:
    """Reset the module-level ``_default_client`` singleton in each package."""
    _PKGS = (ambito_financiero_client, higyrus_client, iol_client, matriz_client)
    for mod in _PKGS:
        if hasattr(mod, "_default_client"):
            mod._default_client = None  # type: ignore[attr-defined]
    yield
    for mod in _PKGS:
        if hasattr(mod, "_default_client"):
            mod._default_client = None  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Per-package Client factory helpers — pre-seed credentials + cached tokens
# so no auth-flow request hits the mock.
# ---------------------------------------------------------------------------


def _make_client(pkg_name: str, *, max_retries: int = 2) -> Any:
    """Construct a sync Client for the given package with sentinel creds."""
    if pkg_name == "ambito_financiero_client":
        return ambito_financiero_client.Client(
            base_url="https://api.test",
            max_retries=max_retries,
        )
    if pkg_name == "iol_client":
        return iol_client.Client(
            base_url="https://api.test",
            username="u",
            password="p",
            token="test-token",
            token_expires_at=9_999_999_999.0,
            max_retries=max_retries,
        )
    if pkg_name == "higyrus_client":
        return higyrus_client.Client(
            base_url="https://api.test",
            client_id="tenant",
            username="u",
            password="p",
            token="test-token",
            token_expires_at=9_999_999_999.0,
            max_retries=max_retries,
        )
    if pkg_name == "matriz_client":
        return matriz_client.Client(
            base_url="https://api.test",
            username="u",
            password="p",
            token="test-token",
            token_expires_at=9_999_999_999.0,
            max_retries=max_retries,
        )
    raise AssertionError(f"unhandled package: {pkg_name}")  # pragma: no cover


# Idempotent GET endpoint factory per package — returns a callable that
# invokes the GET on the given client. Used in tests 3 (extension honored).
def _idempotent_get_call(pkg_name: str) -> Callable[[Any], object]:
    """Return a callable ``lambda client: client.<idempotent_get>(...)`` per pkg."""
    if pkg_name == "ambito_financiero_client":
        target_date = dt.date(2024, 1, 2)
        return lambda c: c.get_dollar_banco_nacion(target_date)
    if pkg_name == "iol_client":
        return lambda c: c.get_quote("GGAL")
    if pkg_name == "higyrus_client":
        fecha_desde = dt.date(2024, 1, 1)
        fecha_hasta = dt.date(2024, 1, 31)
        return lambda c: c.get_movimientos("1", fecha_desde, fecha_hasta)
    if pkg_name == "matriz_client":
        return lambda c: c.get_segments()
    raise AssertionError(f"unhandled package: {pkg_name}")  # pragma: no cover


def _expected_error_types(pkg_name: str) -> tuple[type[Exception], ...]:
    """Tuple of exception types that may surface from a 503 on a GET."""
    pkg = importlib.import_module(pkg_name)
    if pkg_name == "ambito_financiero_client":
        return (pkg.AmbitoFinancieroClientError, httpx.HTTPStatusError)
    if pkg_name == "iol_client":
        return (pkg.IOLClientError, httpx.HTTPStatusError)
    if pkg_name == "higyrus_client":
        return (pkg.HigyrusClientError, httpx.HTTPStatusError)
    if pkg_name == "matriz_client":
        return (pkg.MatrizClientError,)
    raise AssertionError(f"unhandled package: {pkg_name}")  # pragma: no cover


_ALL_PKGS = [
    "ambito_financiero_client",
    "iol_client",
    "higyrus_client",
    "matriz_client",
]


# ---------------------------------------------------------------------------
# Test 1 — view shares _state.http_client and _state.token with parent
# (D-V1, SC#1 ROADMAP, Anti-Pitfall 13)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("pkg_name", _ALL_PKGS)
def test_with_options_shares_http_client_and_token(pkg_name: str) -> None:
    """View must share ``_state`` and the underlying ``httpx.Client``.

    Anti-Pitfall 13: ``with_options(max_retries=N)`` MUST NOT spawn a new
    TCP connection pool nor trigger re-auth. The view shallow-clones the
    Client (``Client.__new__(Client)``) and shares ``_state`` with the
    parent; only ``_max_retries`` differs.
    """
    parent = _make_client(pkg_name)
    # Force http_client lazy init so the assertion has a non-None reference.
    parent._ensure_http_client()
    assert parent._state.http_client is not None

    view = parent.with_options(max_retries=5)
    assert view._state is parent._state, "view must SHARE _state (not clone it)"
    assert view._state.http_client is parent._state.http_client, (
        "view must SHARE the underlying httpx.Client (no second TCP pool)"
    )
    assert view._max_retries == 5
    assert parent._max_retries == 2, "parent's _max_retries must remain intact"


# ---------------------------------------------------------------------------
# Test 2 — CRITICAL MERGE GATE: matriz new_order under 503 with
# with_options(max_retries=10) emits EXACTLY 1 outgoing request.
# (D-P2, SC#2 ROADMAP, Anti-Pitfall 14, money-on-the-line)
# ---------------------------------------------------------------------------


@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
def test_with_options_does_not_bypass_mutation_gate_matriz(httpx_mock: HTTPXMock) -> None:
    """Anti-Pitfall 14 — duplicate orders money-on-the-line.

    ``with_options(max_retries=10).new_order(...)`` MUST execute EXACTLY 1
    outgoing request under 503 — the mutation gate (Phase 8 D-01,
    ``request.extensions["idempotent"] = False`` for ``new_order``) remains
    the absolute authority on retry permission. ``with_options`` only
    tightens or loosens the cap for **idempotent** calls; non-idempotent
    calls always fall through to the pass-through branch.

    CRITICAL kwarg name (verified at ``packages/matriz-client/src/matriz_client/client.py:417``):
    matriz ``new_order`` declares the param as ``qty`` (3 letters). The
    longer-form spelling would raise ``TypeError`` BEFORE the mutation gate
    is exercised, silently neutralizing the SC#2 ROADMAP merge gate.
    """
    matriz_client.configure(
        base_url="https://api.test",
        username="u",
        password="p",
        token="test-token",
        token_expires_at=9_999_999_999.0,
    )
    httpx_mock.add_response(status_code=503, is_reusable=True)
    client = matriz_client._get_default()
    with pytest.raises(matriz_client.exceptions.MatrizClientError):
        client.with_options(max_retries=10).new_order(symbol="GGAL", side="BUY", qty=1, price=100.0, account="test-acct")  # type: ignore[attr-defined]  # fmt: skip
    assert len(httpx_mock.get_requests()) == 1, (
        "matriz new_order under 503 with with_options(max_retries=10) must emit "
        "EXACTLY 1 wire request — mutation gate breach if > 1 (Anti-Pitfall 14)."
    )


# ---------------------------------------------------------------------------
# Test 3 — view's max_attempts extension is honored by RetryTransport.
# Idempotent GET on 503: default 3 wire requests; view max_retries=10 → 11.
# (D-P2, SC#3 ROADMAP)
# ---------------------------------------------------------------------------


@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
@pytest.mark.parametrize("pkg_name", _ALL_PKGS)
def test_with_options_max_attempts_extension_honored(pkg_name: str, httpx_mock: HTTPXMock) -> None:
    """The view's ``_max_retries`` overrides the transport's cap per-call.

    Parent client with ``max_retries=2`` produces ``max_attempts=3`` wire
    requests on persistent 503 (1 initial + 2 retries; Phase 8 D-19
    ``N → N+1`` mapping). After ``parent.with_options(max_retries=10)``,
    the view bumps the cap to ``max_attempts=11`` (1 initial + 10 retries).

    This validates the end-to-end thread:
    ``view._max_retries → req.extensions["max_attempts"] →
    transport.handle_request → stop_after_attempt(effective_max_attempts)``.
    """
    httpx_mock.add_response(status_code=503, is_reusable=True)
    parent = _make_client(pkg_name, max_retries=2)
    call = _idempotent_get_call(pkg_name)
    expected_exc = _expected_error_types(pkg_name)

    # Parent default: max_retries=2 → 3 wire requests.
    before_parent = len(httpx_mock.get_requests())
    with pytest.raises(expected_exc):
        call(parent)
    after_parent = len(httpx_mock.get_requests())
    assert after_parent - before_parent == 3, (
        f"{pkg_name} parent emitted "
        f"{after_parent - before_parent} requests, expected 3 (max_retries=2 → max_attempts=3)"
    )

    # View: max_retries=10 → 11 wire requests.
    view = parent.with_options(max_retries=10)
    before_view = len(httpx_mock.get_requests())
    with pytest.raises(expected_exc):
        call(view)
    after_view = len(httpx_mock.get_requests())
    assert after_view - before_view == 11, (
        f"{pkg_name} view emitted "
        f"{after_view - before_view} requests, expected 11 (max_retries=10 → max_attempts=11)"
    )


# ---------------------------------------------------------------------------
# Test 4 — chaining: inner with_options wins; parent stays intact.
# (D-V2)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("pkg_name", _ALL_PKGS)
def test_with_options_chaining_inner_wins(pkg_name: str) -> None:
    """``c.with_options(5).with_options(10)._max_retries == 10``.

    Each ``with_options`` call returns a fresh view shallow-cloned from
    the receiver; the inner call's argument overrides. The original
    parent's ``_max_retries`` stays at 2.
    """
    parent = _make_client(pkg_name, max_retries=2)
    view = parent.with_options(max_retries=5).with_options(max_retries=10)
    assert view._max_retries == 10, "inner with_options must win"
    assert parent._max_retries == 2, "parent's _max_retries must remain intact"
    assert view._state is parent._state, "view must STILL share _state after chaining"
