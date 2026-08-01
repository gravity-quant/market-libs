"""Symbols-write dispatch (sync) — MUT-MD-01 + GATE-MD-01 end-to-end.

Cubre el contrato observable de los tres métodos mutadores gated del ``Client``
sync (``create_symbol`` / ``create_symbols`` / ``update_symbol``):

- Gate abierto (``mutating_allowed=True`` + host coincidente): despacha el
  método/URL/body correctos con el Bearer, y parsea la respuesta 201/200 vía
  ``Symbol.from_api`` tolerante.
- ``422`` levanta ``MarketDataAPIError`` vía el ``raise_for_response`` existente
  (D-12 — sin manejo de status nuevo en los métodos mutadores).
- Refusal end-to-end adversarial (D-04/D-05): con el gate del singleton default
  OFF y el token FORZADO-vencido (``token_expires_at=0.0``), una mutación levanta
  ``MarketDataMutationNotAllowedError`` y ``httpx_mock.get_requests() == []`` —
  CERO HTTP y CERO grant a Auth0 (el gate corta antes de ``_ensure_token``).
- Host mismatch (gate ON pero host ≠ ``expected_host``) → refused, 0 requests.
"""

from __future__ import annotations

import json as _json

import pytest
from pytest_httpx import HTTPXMock

import market_data_client
from market_data_client import MarketDataAPIError, MarketDataMutationNotAllowedError
from market_data_client.models import NewSymbol, NewSymbols, Symbol, SymbolPatch

_BASE = "https://market-data-develop.test/api"
_TOKEN_URL = "https://auth.test/oauth/token"
# El host que el conftest siembra en base_url (NO el default develop bbsa).
_CONFTEST_HOST = "market-data-develop.test"


def _open_gate() -> None:
    """Abre el gate del singleton default para el host del conftest."""
    market_data_client.configure(mutating_allowed=True, expected_host=_CONFTEST_HOST)


# ----------------------------------------------------------------------
# Happy-path dispatch (gate abierto + host coincidente)
# ----------------------------------------------------------------------


def test_create_symbol_sends_bearer_and_body(httpx_mock: HTTPXMock) -> None:
    """``create_symbol`` POSTea ``/symbols`` con el body snake_case y el Bearer."""
    _open_gate()
    httpx_mock.add_response(
        method="POST",
        status_code=201,
        json=[{"symbol": "DLR/DIC26", "marketId": "ROFX"}],
    )

    result = market_data_client.client._get_default().create_symbol(NewSymbol("DLR/DIC26"))

    assert isinstance(result, list)
    req = httpx_mock.get_requests()[0]
    assert req.method == "POST"
    assert req.url.path == "/api/symbols"
    assert req.headers["Authorization"] == "Bearer test-token"
    assert _json.loads(req.content) == {"symbol": "DLR/DIC26", "market_id": "ROFX"}


def test_create_symbols_batch_sends_body(httpx_mock: HTTPXMock) -> None:
    """``create_symbols`` POSTea ``/symbols/batch`` con la lista serializada."""
    _open_gate()
    httpx_mock.add_response(method="POST", status_code=201, json=[])

    batch = NewSymbols([NewSymbol("DLR/DIC26"), NewSymbol("DLR/ENE27", market_id="ROFX")])
    market_data_client.client._get_default().create_symbols(batch)

    req = httpx_mock.get_requests()[0]
    assert req.method == "POST"
    assert req.url.path == "/api/symbols/batch"
    assert req.headers["Authorization"] == "Bearer test-token"
    assert _json.loads(req.content) == {
        "symbols": [
            {"symbol": "DLR/DIC26", "market_id": "ROFX"},
            {"symbol": "DLR/ENE27", "market_id": "ROFX"},
        ]
    }


def test_update_symbol_patches_body(httpx_mock: HTTPXMock) -> None:
    """``update_symbol`` PATCHea ``/symbols/{id}`` con el body del patch."""
    _open_gate()
    httpx_mock.add_response(method="PATCH", status_code=200, json=[])

    market_data_client.client._get_default().update_symbol("DLR/DIC26", SymbolPatch(active=False))

    req = httpx_mock.get_requests()[0]
    assert req.method == "PATCH"
    assert req.url.path == "/api/symbols/DLR/DIC26"
    assert req.headers["Authorization"] == "Bearer test-token"
    assert _json.loads(req.content) == {"active": False}


def test_create_symbol_422_raises_api_error(httpx_mock: HTTPXMock) -> None:
    """Un ``422`` fluye por el ``raise_for_response`` existente → ``MarketDataAPIError``."""
    _open_gate()
    httpx_mock.add_response(method="POST", status_code=422, json={"detail": "invalid"})

    with pytest.raises(MarketDataAPIError):
        market_data_client.client._get_default().create_symbol(NewSymbol("BAD"))


# ----------------------------------------------------------------------
# Refusal end-to-end (gate OFF / host mismatch) → CERO IO (D-04/D-05)
# ----------------------------------------------------------------------


def test_create_symbol_refused_by_default_emits_no_request(httpx_mock: HTTPXMock) -> None:
    """Gate OFF por default + token FORZADO-vencido → refused, 0 HTTP y 0 grant Auth0."""
    # Forzar el token vencido: si el gate NO cortara primero, ``_ensure_token``
    # dispararía un POST a Auth0 — la ausencia de ese POST prueba el short-circuit.
    market_data_client.configure(token_expires_at=0.0)

    with pytest.raises(MarketDataMutationNotAllowedError):
        market_data_client.client._get_default().create_symbol(NewSymbol("DLR/DIC26"))

    assert httpx_mock.get_requests() == []


def test_create_symbols_refused_by_default_emits_no_request(httpx_mock: HTTPXMock) -> None:
    """Batch: gate OFF por default → refused con 0 requests."""
    market_data_client.configure(token_expires_at=0.0)

    with pytest.raises(MarketDataMutationNotAllowedError):
        market_data_client.client._get_default().create_symbols(NewSymbols([NewSymbol("X")]))

    assert httpx_mock.get_requests() == []


def test_update_symbol_refused_by_default_emits_no_request(httpx_mock: HTTPXMock) -> None:
    """PATCH: gate OFF por default → refused con 0 requests."""
    market_data_client.configure(token_expires_at=0.0)

    with pytest.raises(MarketDataMutationNotAllowedError):
        market_data_client.client._get_default().update_symbol("X", SymbolPatch(active=True))

    assert httpx_mock.get_requests() == []


def test_create_symbol_refused_on_host_mismatch(httpx_mock: HTTPXMock) -> None:
    """Gate ON pero host de base_url ≠ expected_host → refused, 0 requests."""
    # Gate ON con un expected_host que NO coincide con el host del conftest.
    market_data_client.configure(
        mutating_allowed=True,
        expected_host="market-data-PROD.bbsa.com.ar",
        token_expires_at=0.0,
    )

    with pytest.raises(MarketDataMutationNotAllowedError):
        market_data_client.client._get_default().create_symbol(NewSymbol("DLR/DIC26"))

    assert httpx_mock.get_requests() == []


def test_create_symbol_module_shim_dispatches(httpx_mock: HTTPXMock) -> None:
    """El shim module-level ``create_symbol`` delega al default Client."""
    _open_gate()
    httpx_mock.add_response(method="POST", status_code=201, json=[])

    market_data_client.create_symbol(NewSymbol("DLR/DIC26"))

    req = httpx_mock.get_requests()[0]
    assert req.method == "POST"
    assert req.url.path == "/api/symbols"


# ----------------------------------------------------------------------
# symbol_id: int | str — WIDENED, never narrowed (D-09 / D-22)
# ----------------------------------------------------------------------
#
# The live spec types ``PATCH /symbols/{symbol_id}``'s path parameter as an
# INTEGER and the wire confirms it (``Symbol.id``). The annotation therefore
# widens to ``int | str`` rather than narrowing to ``int``: ``str`` is what
# v0.3.0/v0.3.1 published, and narrowing would break every consumer at
# type-check time. Both forms must reach the SAME path, and neither may be
# percent-encoded — the D-08 encoding item is DISSOLVED (an integer cannot
# contain a slash), so a quoting layer here could only corrupt a valid id.


def test_update_symbol_accepts_int_row_id(httpx_mock: HTTPXMock) -> None:
    """La forma correcta: el id ENTERO de fila viaja tal cual en el path."""
    _open_gate()
    httpx_mock.add_response(method="PATCH", status_code=200, json=[])

    market_data_client.client._get_default().update_symbol(8123, SymbolPatch(active=False))

    req = httpx_mock.get_requests()[0]
    assert req.method == "PATCH"
    assert req.url.path == "/api/symbols/8123"


def test_update_symbol_still_accepts_str_row_id(httpx_mock: HTTPXMock) -> None:
    """La forma publicada en v0.3.x sigue funcionando: ensanchar, no angostar (D-22)."""
    _open_gate()
    httpx_mock.add_response(method="PATCH", status_code=200, json=[])

    market_data_client.client._get_default().update_symbol("8123", SymbolPatch(active=False))

    req = httpx_mock.get_requests()[0]
    assert req.url.path == "/api/symbols/8123"


def test_update_symbol_int_and_str_forms_hit_the_same_path(httpx_mock: HTTPXMock) -> None:
    """Ambas formas producen el MISMO path — el ensanche no bifurca el dispatch."""
    _open_gate()
    httpx_mock.add_response(method="PATCH", status_code=200, json=[])
    httpx_mock.add_response(method="PATCH", status_code=200, json=[])

    client = market_data_client.client._get_default()
    client.update_symbol(8123, SymbolPatch(active=False))
    client.update_symbol("8123", SymbolPatch(active=False))

    paths = [r.url.path for r in httpx_mock.get_requests()]
    assert paths == ["/api/symbols/8123", "/api/symbols/8123"]


def test_update_symbol_applies_no_percent_encoding(httpx_mock: HTTPXMock) -> None:
    """D-09: nada se encodea. Un id con ``/`` sale byte por byte, sin ``%2F``.

    No es que un id así sea legítimo — el path param es un entero. Es que si
    alguna vez se agregara una capa de quoting, este test la detectaría: el
    contrato es interpolación CRUDA, y ese contrato es lo que disuelve el ítem
    D-08 en vez de diferirlo otra vez.
    """
    _open_gate()
    httpx_mock.add_response(method="PATCH", status_code=200, json=[])

    market_data_client.client._get_default().update_symbol("DLR/DIC26", SymbolPatch(active=False))

    req = httpx_mock.get_requests()[0]
    assert req.url.path == "/api/symbols/DLR/DIC26"
    assert "%2F" not in str(req.url)
    assert "%2f" not in str(req.url)


def test_update_symbol_module_shim_accepts_int_row_id(httpx_mock: HTTPXMock) -> None:
    """El shim module-level ensancha igual que el método (las 4 rutas, D-15)."""
    _open_gate()
    httpx_mock.add_response(method="PATCH", status_code=200, json=[])

    market_data_client.update_symbol(8123, SymbolPatch(active=False))

    req = httpx_mock.get_requests()[0]
    assert req.url.path == "/api/symbols/8123"


# ----------------------------------------------------------------------
# Los tres mutadores devuelven filas REALES sin cambiar list[Symbol] (D-11/D-22)
# ----------------------------------------------------------------------
#
# Bodies copiados de los baselines LIVE-MUT-01. Antes del fix estos tres
# métodos devolvían un Symbol all-default POR CLAVE del objeto de respuesta —
# medido en vivo como "6 Symbol, 6 all-default" en ambas superficies
# (F-41/F-51). El tipo de retorno `list[Symbol]` NO cambia: es contrato
# publicado en v0.3.0, así que se desenvuelve el envelope en vez de pasarlo
# crudo (D-22).

_CREATE_SYMBOL_BODY = {
    "active": True,
    "created": True,
    "id": 8123,
    "market_id": "ROFX",
    "note": "created",
    "symbol": "GSDPROBE/P27-SYNC",
}

_CREATE_SYMBOLS_BATCH_BODY = {
    "created": 2,
    "items": [
        {"active": True, "created": True, "id": 8124, "market_id": "ROFX", "symbol": "A"},
        {"active": True, "created": False, "id": 8125, "market_id": "ROFX", "symbol": "B"},
    ],
    "note": "batch",
    "reactivated": 0,
    "requested": 2,
}

_UPDATE_SYMBOL_BODY = {
    "active": False,
    "id": 8123,
    "market_id": "ROFX",
    "note": "updated",
    "symbol": "GSDPROBE/P27-SYNC",
}


def test_create_symbol_returns_real_rows_not_key_blanks(httpx_mock: HTTPXMock) -> None:
    """El body plano de ``POST /symbols`` se desenvuelve a UNA fila poblada."""
    _open_gate()
    httpx_mock.add_response(method="POST", status_code=201, json=_CREATE_SYMBOL_BODY)

    result = market_data_client.client._get_default().create_symbol(NewSymbol("GSDPROBE/P27-SYNC"))

    assert len(result) == 1
    assert result[0].symbol == "GSDPROBE/P27-SYNC"
    assert result[0].id == 8123
    # La firma exacta del bug: 6 claves → 6 Symbol en blanco.
    assert len(result) != len(_CREATE_SYMBOL_BODY)
    assert [row for row in result if row.symbol == ""] == []


def test_create_symbols_returns_real_rows_from_items_envelope(httpx_mock: HTTPXMock) -> None:
    """El envelope de ``POST /symbols/batch`` se desenvuelve por ``items``."""
    _open_gate()
    httpx_mock.add_response(method="POST", status_code=201, json=_CREATE_SYMBOLS_BATCH_BODY)

    result = market_data_client.client._get_default().create_symbols(
        NewSymbols([NewSymbol("A"), NewSymbol("B")])
    )

    assert [row.symbol for row in result] == ["A", "B"]
    assert [row.id for row in result] == [8124, 8125]


def test_update_symbol_returns_real_rows(httpx_mock: HTTPXMock) -> None:
    """El body plano de ``PATCH /symbols/{id}`` se desenvuelve a UNA fila poblada."""
    _open_gate()
    httpx_mock.add_response(method="PATCH", status_code=200, json=_UPDATE_SYMBOL_BODY)

    result = market_data_client.client._get_default().update_symbol(8123, SymbolPatch(active=False))

    assert len(result) == 1
    assert result[0].id == 8123
    assert result[0].active is False


def test_symbols_mutations_still_return_lists_of_symbol(httpx_mock: HTTPXMock) -> None:
    """El tipo de retorno publicado se preserva: ``list[Symbol]``, no un dict.

    Un passthrough del envelope habría arreglado el parseo rompiendo el contrato
    de v0.3.0 y forzando un major. Esta aserción es la que impide ese atajo.
    """
    _open_gate()
    httpx_mock.add_response(method="POST", status_code=201, json=_CREATE_SYMBOL_BODY)
    httpx_mock.add_response(method="POST", status_code=201, json=_CREATE_SYMBOLS_BATCH_BODY)
    httpx_mock.add_response(method="PATCH", status_code=200, json=_UPDATE_SYMBOL_BODY)

    client = market_data_client.client._get_default()
    results = [
        client.create_symbol(NewSymbol("GSDPROBE/P27-SYNC")),
        client.create_symbols(NewSymbols([NewSymbol("A")])),
        client.update_symbol(8123, SymbolPatch(active=False)),
    ]

    for result in results:
        assert isinstance(result, list)
        assert all(isinstance(row, Symbol) for row in result)
