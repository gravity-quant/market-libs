"""Symbols-write dispatch (async) — espejo de ``test_symbols_write.py`` (D-15).

Mismo contrato observable sobre el default ``AsyncClient``: gate abierto
despacha método/URL/body con el Bearer y parsea tolerante; ``422`` →
``MarketDataAPIError``; refusal end-to-end con token forzado-vencido prueba CERO
HTTP y CERO grant a Auth0; host mismatch → refused con 0 requests.
"""

from __future__ import annotations

import json as _json

import pytest
from pytest_httpx import HTTPXMock

from market_data_client import MarketDataAPIError, MarketDataMutationNotAllowedError, aio
from market_data_client.models import NewSymbol, NewSymbols, Symbol, SymbolPatch

_BASE = "https://market-data-develop.test/api"
_TOKEN_URL = "https://auth.test/oauth/token"
_CONFTEST_HOST = "market-data-develop.test"


def _open_gate() -> None:
    """Abre el gate del singleton async default para el host del conftest."""
    aio.configure(mutating_allowed=True, expected_host=_CONFTEST_HOST)


# ----------------------------------------------------------------------
# Happy-path dispatch (gate abierto + host coincidente)
# ----------------------------------------------------------------------


async def test_create_symbol_sends_bearer_and_body(httpx_mock: HTTPXMock) -> None:
    """``create_symbol`` async POSTea ``/symbols`` con el body snake_case y el Bearer."""
    _open_gate()
    httpx_mock.add_response(
        method="POST",
        status_code=201,
        json=[{"symbol": "DLR/DIC26", "marketId": "ROFX"}],
    )

    result = await aio._get_default().create_symbol(NewSymbol("DLR/DIC26"))

    assert isinstance(result, list)
    req = httpx_mock.get_requests()[0]
    assert req.method == "POST"
    assert req.url.path == "/api/symbols"
    assert req.headers["Authorization"] == "Bearer test-token"
    assert _json.loads(req.content) == {"symbol": "DLR/DIC26", "market_id": "ROFX"}


async def test_create_symbols_batch_sends_body(httpx_mock: HTTPXMock) -> None:
    """``create_symbols`` async POSTea ``/symbols/batch`` con la lista serializada."""
    _open_gate()
    httpx_mock.add_response(method="POST", status_code=201, json=[])

    batch = NewSymbols([NewSymbol("DLR/DIC26"), NewSymbol("DLR/ENE27")])
    await aio._get_default().create_symbols(batch)

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


async def test_update_symbol_patches_body(httpx_mock: HTTPXMock) -> None:
    """``update_symbol`` async PATCHea ``/symbols/{id}`` con el body del patch."""
    _open_gate()
    httpx_mock.add_response(method="PATCH", status_code=200, json=[])

    await aio._get_default().update_symbol("DLR/DIC26", SymbolPatch(active=False))

    req = httpx_mock.get_requests()[0]
    assert req.method == "PATCH"
    assert req.url.path == "/api/symbols/DLR/DIC26"
    assert req.headers["Authorization"] == "Bearer test-token"
    assert _json.loads(req.content) == {"active": False}


async def test_create_symbol_422_raises_api_error(httpx_mock: HTTPXMock) -> None:
    """Un ``422`` fluye por el ``raise_for_response`` existente → ``MarketDataAPIError``."""
    _open_gate()
    httpx_mock.add_response(method="POST", status_code=422, json={"detail": "invalid"})

    with pytest.raises(MarketDataAPIError):
        await aio._get_default().create_symbol(NewSymbol("BAD"))


# ----------------------------------------------------------------------
# Refusal end-to-end (gate OFF / host mismatch) → CERO IO (D-04/D-05)
# ----------------------------------------------------------------------


async def test_create_symbol_refused_by_default_emits_no_request(httpx_mock: HTTPXMock) -> None:
    """Gate OFF por default + token FORZADO-vencido → refused, 0 HTTP y 0 grant Auth0."""
    aio.configure(token_expires_at=0.0)

    with pytest.raises(MarketDataMutationNotAllowedError):
        await aio._get_default().create_symbol(NewSymbol("DLR/DIC26"))

    assert httpx_mock.get_requests() == []


async def test_create_symbols_refused_by_default_emits_no_request(httpx_mock: HTTPXMock) -> None:
    """Batch async: gate OFF por default → refused con 0 requests."""
    aio.configure(token_expires_at=0.0)

    with pytest.raises(MarketDataMutationNotAllowedError):
        await aio._get_default().create_symbols(NewSymbols([NewSymbol("X")]))

    assert httpx_mock.get_requests() == []


async def test_update_symbol_refused_by_default_emits_no_request(httpx_mock: HTTPXMock) -> None:
    """PATCH async: gate OFF por default → refused con 0 requests."""
    aio.configure(token_expires_at=0.0)

    with pytest.raises(MarketDataMutationNotAllowedError):
        await aio._get_default().update_symbol("X", SymbolPatch(active=True))

    assert httpx_mock.get_requests() == []


async def test_create_symbol_refused_on_host_mismatch(httpx_mock: HTTPXMock) -> None:
    """Gate ON pero host de base_url ≠ expected_host → refused, 0 requests."""
    aio.configure(
        mutating_allowed=True,
        expected_host="market-data-PROD.bbsa.com.ar",
        token_expires_at=0.0,
    )

    with pytest.raises(MarketDataMutationNotAllowedError):
        await aio._get_default().create_symbol(NewSymbol("DLR/DIC26"))

    assert httpx_mock.get_requests() == []


async def test_create_symbol_module_shim_dispatches(httpx_mock: HTTPXMock) -> None:
    """El shim async module-level ``aio.create_symbol`` delega al default AsyncClient."""
    _open_gate()
    httpx_mock.add_response(method="POST", status_code=201, json=[])

    await aio.create_symbol(NewSymbol("DLR/DIC26"))

    req = httpx_mock.get_requests()[0]
    assert req.method == "POST"
    assert req.url.path == "/api/symbols"


# ----------------------------------------------------------------------
# symbol_id: int | str — espejo async del ensanche (D-09 / D-15 / D-22)
# ----------------------------------------------------------------------


async def test_update_symbol_accepts_int_row_id(httpx_mock: HTTPXMock) -> None:
    """La forma correcta: el id ENTERO de fila viaja tal cual en el path."""
    _open_gate()
    httpx_mock.add_response(method="PATCH", status_code=200, json=[])

    await aio._get_default().update_symbol(8123, SymbolPatch(active=False))

    req = httpx_mock.get_requests()[0]
    assert req.method == "PATCH"
    assert req.url.path == "/api/symbols/8123"


async def test_update_symbol_still_accepts_str_row_id(httpx_mock: HTTPXMock) -> None:
    """La forma publicada en v0.3.x sigue funcionando: ensanchar, no angostar (D-22)."""
    _open_gate()
    httpx_mock.add_response(method="PATCH", status_code=200, json=[])

    await aio._get_default().update_symbol("8123", SymbolPatch(active=False))

    req = httpx_mock.get_requests()[0]
    assert req.url.path == "/api/symbols/8123"


async def test_update_symbol_int_and_str_forms_hit_the_same_path(httpx_mock: HTTPXMock) -> None:
    """Ambas formas producen el MISMO path — el ensanche no bifurca el dispatch."""
    _open_gate()
    httpx_mock.add_response(method="PATCH", status_code=200, json=[])
    httpx_mock.add_response(method="PATCH", status_code=200, json=[])

    aclient = aio._get_default()
    await aclient.update_symbol(8123, SymbolPatch(active=False))
    await aclient.update_symbol("8123", SymbolPatch(active=False))

    paths = [r.url.path for r in httpx_mock.get_requests()]
    assert paths == ["/api/symbols/8123", "/api/symbols/8123"]


async def test_update_symbol_applies_no_percent_encoding(httpx_mock: HTTPXMock) -> None:
    """D-09: nada se encodea; el path sale byte por byte, sin ``%2F``."""
    _open_gate()
    httpx_mock.add_response(method="PATCH", status_code=200, json=[])

    await aio._get_default().update_symbol("DLR/DIC26", SymbolPatch(active=False))

    req = httpx_mock.get_requests()[0]
    assert req.url.path == "/api/symbols/DLR/DIC26"
    assert "%2F" not in str(req.url)
    assert "%2f" not in str(req.url)


async def test_update_symbol_module_shim_accepts_int_row_id(httpx_mock: HTTPXMock) -> None:
    """El shim async module-level ensancha igual que el método (D-15)."""
    _open_gate()
    httpx_mock.add_response(method="PATCH", status_code=200, json=[])

    await aio.update_symbol(8123, SymbolPatch(active=False))

    req = httpx_mock.get_requests()[0]
    assert req.url.path == "/api/symbols/8123"


# ----------------------------------------------------------------------
# Los tres mutadores async devuelven filas REALES sin cambiar list[Symbol]
# ----------------------------------------------------------------------
#
# Espejo async de la sección homónima de ``test_symbols_write.py``. El bug D-11
# se midió en vivo en AMBAS superficies (F-41 async / F-51 sync), así que la
# corrección se prueba en las dos.

_CREATE_SYMBOL_BODY = {
    "active": True,
    "created": True,
    "id": 8123,
    "market_id": "ROFX",
    "note": "created",
    "symbol": "GSDPROBE/P27-ASYNC",
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
    "symbol": "GSDPROBE/P27-ASYNC",
}


async def test_create_symbol_returns_real_rows_not_key_blanks(httpx_mock: HTTPXMock) -> None:
    """El body plano de ``POST /symbols`` se desenvuelve a UNA fila poblada."""
    _open_gate()
    httpx_mock.add_response(method="POST", status_code=201, json=_CREATE_SYMBOL_BODY)

    result = await aio._get_default().create_symbol(NewSymbol("GSDPROBE/P27-ASYNC"))

    assert len(result) == 1
    assert result[0].symbol == "GSDPROBE/P27-ASYNC"
    assert result[0].id == 8123
    assert len(result) != len(_CREATE_SYMBOL_BODY)
    assert [row for row in result if row.symbol == ""] == []


async def test_create_symbols_returns_real_rows_from_items_envelope(httpx_mock: HTTPXMock) -> None:
    """El envelope de ``POST /symbols/batch`` se desenvuelve por ``items``."""
    _open_gate()
    httpx_mock.add_response(method="POST", status_code=201, json=_CREATE_SYMBOLS_BATCH_BODY)

    result = await aio._get_default().create_symbols(NewSymbols([NewSymbol("A"), NewSymbol("B")]))

    assert [row.symbol for row in result] == ["A", "B"]
    assert [row.id for row in result] == [8124, 8125]


async def test_update_symbol_returns_real_rows(httpx_mock: HTTPXMock) -> None:
    """El body plano de ``PATCH /symbols/{id}`` se desenvuelve a UNA fila poblada."""
    _open_gate()
    httpx_mock.add_response(method="PATCH", status_code=200, json=_UPDATE_SYMBOL_BODY)

    result = await aio._get_default().update_symbol(8123, SymbolPatch(active=False))

    assert len(result) == 1
    assert result[0].id == 8123
    assert result[0].active is False


async def test_symbols_mutations_still_return_lists_of_symbol(httpx_mock: HTTPXMock) -> None:
    """El tipo de retorno publicado se preserva en la superficie async también."""
    _open_gate()
    httpx_mock.add_response(method="POST", status_code=201, json=_CREATE_SYMBOL_BODY)
    httpx_mock.add_response(method="POST", status_code=201, json=_CREATE_SYMBOLS_BATCH_BODY)
    httpx_mock.add_response(method="PATCH", status_code=200, json=_UPDATE_SYMBOL_BODY)

    aclient = aio._get_default()
    results = [
        await aclient.create_symbol(NewSymbol("GSDPROBE/P27-ASYNC")),
        await aclient.create_symbols(NewSymbols([NewSymbol("A")])),
        await aclient.update_symbol(8123, SymbolPatch(active=False)),
    ]

    for result in results:
        assert isinstance(result, list)
        assert all(isinstance(row, Symbol) for row in result)
