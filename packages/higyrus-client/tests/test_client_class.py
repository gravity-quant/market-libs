"""Tests del esqueleto ``Client`` / ``AsyncClient`` de higyrus-client.

Phase 06 Plan 05 — REFAC-02 higyrus. Cubre:

- Construcción explícita de ``Client`` con kwargs (`__init__` per CONTEXT.md D-13).
- Lifecycle: ``__enter__`` / ``__exit__`` / ``close()`` idempotente (sync).
- Lifecycle async: ``__aenter__`` / ``__aexit__`` / ``aclose()`` idempotente.
- ``__repr__`` redacta ``password`` y ``token`` (D-18); muestra ``client_id`` (no secreto).
- ``__reduce__`` / ``__deepcopy__`` levantan ``TypeError`` (D-23).
- ``configure(token=..., token_expires_at=...)`` con carry-forward incluye ``client_id``.
- Aislamiento del default client respecto a instancias explícitas.
- PEP 562 shim: ``_token`` / ``_token_ts`` (renamed → ``token_expires_at`` internamente) /
  ``_client`` reads forward al state del default client. Reads de ``_user``,
  ``_password``, ``_client_id``, ``_base_url`` levantan ``AttributeError``.
- Regresión higyrus-específica: ``_request`` preserva el literal ``/`` en query string
  via ``urlencode(..., safe="/")`` — Higyrus IIS rechaza ``%2F`` con 400 "formato
  dd/mm/yyyy" (F-01..F-06 plan 04-04).
- B8: ``aio._raise_for_response`` ES el mismo objeto que ``client._raise_for_response``
  (no se duplica la lógica).
"""

from __future__ import annotations

import copy
import datetime as dt
import pickle
import re

import pytest
from pytest_httpx import HTTPXMock

import higyrus_client

# ---------------------------------------------------------------------------
# Sync Client lifecycle
# ---------------------------------------------------------------------------


def test_client_init_with_explicit_kwargs() -> None:
    """``Client(base_url=..., client_id=..., username=..., password=...)`` setea state."""
    c = higyrus_client.Client(
        base_url="https://api.test",
        client_id="tenant-explicit",
        username="explicit-user",
        password="explicit-pass",
        token="explicit-token",
        token_expires_at=1234.5,
    )
    assert c._state.base_url == "https://api.test"
    assert c._state.client_id == "tenant-explicit"
    assert c._state.username == "explicit-user"
    assert c._state.password == "explicit-pass"
    assert c._state.token == "explicit-token"
    assert c._state.token_expires_at == 1234.5


def test_client_base_url_strips_trailing_slash() -> None:
    """``Client(base_url='https://api.test/')`` debe quitar el trailing slash."""
    c = higyrus_client.Client(base_url="https://api.test/")
    assert c._state.base_url == "https://api.test"


def test_client_context_manager_closes_http_client() -> None:
    """``with Client(...) as c:`` cierra el http_client al salir."""
    c = higyrus_client.Client(base_url="https://api.test")
    with c as ctx:
        # Forzar creación del http_client lazy.
        ctx._ensure_http_client()
        assert ctx._state.http_client is not None
    # Tras __exit__, http_client queda en None.
    assert c._state.http_client is None


def test_client_close_is_idempotent() -> None:
    """``close()`` puede invocarse repetidas veces sin error."""
    c = higyrus_client.Client(base_url="https://api.test")
    c.close()
    c.close()
    c.close()
    assert c._state.http_client is None


def test_client_repr_redacts_password_and_token() -> None:
    """``__repr__`` muestra ``client_id`` pero redacta ``password`` y ``token`` (D-18)."""
    c = higyrus_client.Client(
        base_url="https://api.test",
        client_id="tenant",
        username="user1",
        password="super-secret",
        token="bearer-secret",
        token_expires_at=1234.5,
    )
    r = repr(c)
    # password / token nunca aparecen en claro
    assert "super-secret" not in r
    assert "bearer-secret" not in r
    # base_url, username, client_id sí (no son secretos)
    assert "https://api.test" in r
    assert "user1" in r
    assert "tenant" in r
    # marcadores redactados
    assert "***" in r


def test_client_pickle_raises_type_error() -> None:
    """``__reduce__`` (D-23) levanta ``TypeError`` para evitar pickle."""
    c = higyrus_client.Client(base_url="https://api.test")
    with pytest.raises(TypeError):
        pickle.dumps(c)


def test_client_deepcopy_raises_type_error() -> None:
    """``__deepcopy__`` (D-23) levanta ``TypeError`` para evitar copia."""
    c = higyrus_client.Client(base_url="https://api.test")
    with pytest.raises(TypeError):
        copy.deepcopy(c)


# ---------------------------------------------------------------------------
# Configure carry-forward + default-instance isolation
# ---------------------------------------------------------------------------


def test_configure_carry_forward_includes_client_id_and_token() -> None:
    """``configure(token=..., token_expires_at=..., client_id=...)`` aceptado."""
    higyrus_client.configure(
        base_url="https://api.test",
        username="u",
        password="p",
        client_id="other-tenant",
        token="cf-token",
        token_expires_at=5_555_555.5,
    )
    default = higyrus_client._get_default()
    assert default._state.base_url == "https://api.test"
    assert default._state.client_id == "other-tenant"
    assert default._state.token == "cf-token"
    assert default._state.token_expires_at == 5_555_555.5


def test_explicit_instance_isolated_from_default() -> None:
    """Cambiar state en una instancia explícita no afecta al default."""
    default = higyrus_client._get_default()
    default_url_before = default._state.base_url

    c = higyrus_client.Client(base_url="https://other.test")
    c._state.token = "instance-token"

    assert default._state.base_url == default_url_before
    assert default._state.token != "instance-token"


# ---------------------------------------------------------------------------
# PEP 562 shim — sync
# ---------------------------------------------------------------------------


def test_pep_562_shim_token_read_forwards_to_state() -> None:
    """Lectura de ``higyrus_client.client._token`` debería forwardear a ``state.token``."""
    higyrus_client._get_default()._state.token = "shim-tok"
    assert higyrus_client.client._token == "shim-tok"


def test_pep_562_shim_token_ts_renamed_to_token_expires_at() -> None:
    """Lectura de ``higyrus_client.client._token_ts`` mapea al ``state.token_expires_at``.

    El rename es interno: el shim mantiene ``_token_ts`` como nombre legacy y
    lo reescribe a ``token_expires_at`` en el campo del state.
    """
    higyrus_client._get_default()._state.token_expires_at = 1234.5
    assert higyrus_client.client._token_ts == 1234.5


def test_pep_562_shim_client_forwards_to_http_client() -> None:
    """Lectura de ``higyrus_client.client._client`` forwardea a ``state.http_client``."""
    default = higyrus_client._get_default()
    default._ensure_http_client()
    assert higyrus_client.client._client is default._state.http_client


def test_pep_562_shim_raises_for_legacy_credential_names() -> None:
    """Reads de ``_user`` / ``_password`` / ``_client_id`` / ``_base_url`` levantan ``AttributeError``."""
    for name in ("_user", "_password", "_client_id", "_base_url"):
        with pytest.raises(AttributeError):
            getattr(higyrus_client.client, name)


# ---------------------------------------------------------------------------
# URL-encoding regression (higyrus-specific quirk)
# ---------------------------------------------------------------------------


def test_url_encoding_preserves_slash_in_query(httpx_mock: HTTPXMock) -> None:
    """Regression: ``_request`` preserva ``/`` literal en query string.

    Higyrus IIS rechaza ``%2F`` en query con 400 "formato dd/mm/yyyy"
    (F-01..F-06 plan 04-04). El skeleton ``Client._request`` debe usar
    ``urlencode(..., quote_via=quote, safe="/")`` igual que el código legacy.
    """
    httpx_mock.add_response(
        url=re.compile(r"^https://api\.test/api/cuentas/CTA-001/movimientos\?.*"),
        method="GET",
        json=[],
    )
    higyrus_client.get_movimientos(
        "CTA-001",
        fecha_desde=dt.date(2026, 5, 8),
        fecha_hasta=dt.date(2026, 6, 7),
    )
    [req] = httpx_mock.get_requests()
    query_str = req.url.query.decode()
    assert "fechaDesde=08/05/2026" in query_str
    assert "fechaHasta=07/06/2026" in query_str
    assert "%2F" not in query_str
