# Testing Patterns

**Analysis Date:** 2026-05-27

## Test Framework

**Runner:**
- pytest 8.3+
- Config: `pyproject.toml` (`[tool.pytest.ini_options]`)

**Key pytest settings:**
- `asyncio_mode = "auto"` — all `async def test_*` functions run as coroutines without `@pytest.mark.asyncio`
- `--import-mode=importlib` — avoids `conftest.py` namespace conflicts between packages in the monorepo
- `--strict-markers`, `--strict-config` enforced
- `-ra` — shows short summary of all non-passing tests

**Assertion Library:**
- pytest built-in assertions (no `unittest.assert*`)

**HTTP mocking:**
- `pytest-httpx` 0.34+ — `HTTPXMock` fixture intercepts all `httpx` requests

**Async support:**
- `pytest-asyncio` 0.24+

**Coverage:**
- `pytest-cov` 6.0+, branch coverage enabled

**Run Commands:**
```bash
uv run pytest                          # Run all tests across all packages
uv run pytest packages/iol-client/     # Run tests for one package
uv run pytest --cov --cov-report=term  # With coverage report
uv run mypy packages/iol-client/tests  # Type-check tests for one package
```

## Test File Organization

**Location:**
- Separate `tests/` directory at the root of each package (not co-located with source)
- Pattern: `packages/<package-name>/tests/`

**Naming:**
- `test_client.py` — sync client smoke tests
- `test_async_client.py` — async (`aio`) client smoke tests
- `test_models.py` — model parsing and safe-access tests (packages with dataclass models)
- `test_exceptions.py` — exception hierarchy tests (matriz-client)
- `test_types.py` — Literal type constant tests (matriz-client)
- `test_ws_client.py` — WebSocket client tests (matriz-client)
- `conftest.py` — shared autouse fixtures per package

**Structure:**
```
packages/
  higyrus-client/
    tests/
      conftest.py
      test_client.py
      test_async_client.py
  iol-client/
    tests/
      conftest.py
      test_client.py
      test_async_client.py
  matriz-client/
    tests/
      conftest.py
      test_client.py
      test_models.py
      test_exceptions.py
      test_types.py
      test_ws_client.py
  ambito-financiero-client/
    tests/
      conftest.py
      test_client.py
      test_async_client.py
  wallets-client/
    tests/
      conftest.py
      test_client.py
      test_async_client.py
```

## Test Structure

**Function-level tests, no test classes:**
```python
def test_<what>_<expected_outcome>(httpx_mock: HTTPXMock) -> None:
    ...

async def test_async_<what>_<expected_outcome>(httpx_mock: HTTPXMock) -> None:
    ...
```

No `class Test*` grouping is used — all tests are top-level functions in `test_*.py` files. Section comments (`# ------ Auth ------`) are used to group related tests within a file.

**Test naming convention:**
- Pattern: `test_<function_under_test>_<scenario_or_expected_result>`
- Spanish: `test_login_obtiene_access_token`, `test_request_propaga_auth_error`
- English (matriz-client): `test_login_requires_credentials`, `test_login_stores_token_from_header`
- Mixed usage exists — choose the language matching the package's existing tests

**Async tests:**
- Declared as `async def test_*` — no decorator needed due to `asyncio_mode = "auto"`
- Identical structure to sync tests; `await` the function under test directly

## Mocking

**Framework:** `pytest-httpx` (`HTTPXMock` fixture) for all HTTP interception. `pytest.MonkeyPatch` for module-level state patching.

**HTTP mocking pattern:**
```python
def test_get_quote_arma_url_y_params(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://api.test/api/v2/bcba/Titulos/GGAL/Cotizacion?model.mercado=bcba&model.simbolo=GGAL&model.plazo=t2",
        json={"ultimoPrecio": 1234.5, "simbolo": "GGAL"},
    )
    quote = iol_client.get_quote("GGAL")
    assert quote["ultimoPrecio"] == 1234.5
```

- Always pass `url=` with the full expected URL including query string to validate routing and params
- Pass `method="POST"` for non-GET requests
- Pass `json=` for JSON responses, `text=` for plain text (error cases), `status_code=` for error status tests
- `match_headers={"Header": "value"}` to assert that specific headers were sent
- Use `httpx_mock.get_requests()` to inspect outgoing request objects (URL, params, headers)

**Module-level state patching:**
```python
# In conftest.py autouse fixtures:
monkeypatch.setattr(iol_client.client, "_token", "test-token", raising=False)
monkeypatch.setattr(iol_client.client, "_token_expires_at", 9_999_999_999.0, raising=False)

# In individual tests:
monkeypatch.setattr(_client, "_user", "")
monkeypatch.setattr(_client, "_token", None)
```

- `raising=False` used when the attribute might not exist at import time (first access)
- Patch at the module level (`iol_client.client._token`), not at a class level

**Capturing stubs (ws_client pattern):**
```python
@pytest.fixture
def capture_send(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    sent: list[dict[str, Any]] = []
    monkeypatch.setattr(_ws, "_send", lambda msg: sent.append(msg))
    return sent
```

**What to mock:**
- All outgoing HTTP calls via `HTTPXMock` — never make real network requests in tests
- Module-level token state to pre-load a valid token and skip login in endpoint tests
- Internal functions (`login`, `_send`) via `monkeypatch.setattr` when testing callers in isolation

**What NOT to mock:**
- The exception hierarchy — test it directly via `pytest.raises`
- Model parsing (`from_api`) — test with real dict payloads
- Parameter helpers (`format_date`, `format_bool`, `drop_none`) — test directly

## Fixtures and Factories

**Autouse per-package fixtures in `conftest.py`:**

Every package has two `autouse=True` fixtures that run before every test:

```python
@pytest.fixture(autouse=True)
def _configure_sync(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    iol_client.configure(
        base_url="https://api.test",
        username="u",
        password="p",
    )
    monkeypatch.setattr(iol_client.client, "_token", "test-token", raising=False)
    monkeypatch.setattr(iol_client.client, "_token_expires_at", 9_999_999_999.0, raising=False)
    yield
    iol_client.configure(base_url="https://api.test", username="", password="")


@pytest.fixture(autouse=True)
async def _configure_async(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[None]:
    aio.configure(base_url="https://api.test", username="u", password="p")
    monkeypatch.setattr(aio, "_token", "test-token", raising=False)
    monkeypatch.setattr(aio, "_token_expires_at", 9_999_999_999.0, raising=False)
    yield
    await aio.aclose()
    aio.configure(base_url="https://api.test", username="", password="")
```

- `base_url` is always set to `"https://api.test"` so `HTTPXMock` URL assertions are deterministic
- A pre-loaded valid token bypasses login for all endpoint tests unless a test explicitly patches it out
- `yield` + teardown resets state so tests are independent
- Async fixture calls `await aio.aclose()` to release the async HTTP client

**Test data (models tests):**
- Inline dicts as payloads — no factory functions or fixtures for model construction
- Named module-level constants for large reusable payloads:
  ```python
  ORDER_PAYLOAD = {
      "orderId": "218681",
      "clOrdId": "1-1234",
      ...
  }
  def test_order_round_trip() -> None:
      parsed = Order.from_api(ORDER_PAYLOAD)
      ...
  def test_order_accepts_null_order_id() -> None:
      payload = {**ORDER_PAYLOAD, "orderId": None, "status": "PENDING_NEW"}
      ...
  ```

**Location:** All fixtures are in `tests/conftest.py`. No shared cross-package fixture files exist (each package is self-contained).

## Coverage

**Requirements:**
- Branch coverage enabled (`branch = true` in `[tool.coverage.run]`)
- Source: `packages/` directory
- No enforced minimum percentage

**Excluded lines:**
```ini
exclude_lines =
    "pragma: no cover"
    "if TYPE_CHECKING:"
    "raise NotImplementedError"
```

**View Coverage:**
```bash
uv run pytest --cov --cov-report=term-missing
uv run pytest --cov --cov-report=html  # HTML report in htmlcov/
```

## Test Types

**Unit Tests (the primary test type):**
- Scope: individual public functions exercised against mocked HTTP responses
- Each public endpoint function in `client.py` and `aio.py` has at least one test
- Auth flow, error propagation (401/403/429), and happy-path response parsing are each tested separately

**Model Tests (packages with SafeModel):**
- Scope: `from_api` parsing logic — round-trip, partial payload, `None`/non-dict payloads, frozen immutability, `empty()` classmethod
- Regression tests for specific bugs have inline comments: `"""Regression: CL viene como objeto {price, size, date}, no como float (issue #102)."""`

**Integration Tests:**
- Not present. All tests use mocked HTTP; no real API calls.

**E2E Tests:**
- Not present. Root `main_<pkg>.py` scripts serve as manual smoke runners.

## Common Patterns

**Error testing:**
```python
def test_request_propaga_auth_error(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(status_code=401, text="bad")
    with pytest.raises(IOLAuthError):
        iol_client.client._request("GET", "/api/anything")

# With attribute inspection:
def test_login_credenciales_rechazadas(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(status_code=401, json={"errors": [{"title": "auth", "detail": "bad"}]})
    with pytest.raises(HigyrusAuthError) as exc_info:
        higyrus_client.login()
    assert exc_info.value.status_code == 401
    assert exc_info.value.errors == [{"title": "auth", "detail": "bad"}]
```

**URL and param validation:**
```python
# Pass full URL with query string to httpx_mock — mismatch causes test failure
httpx_mock.add_response(
    url="https://api.test/api/cuentas/123/movimientos?fechaDesde=01%2F01%2F2026&fechaHasta=31%2F01%2F2026",
    json=[],
)
# Or inspect request objects:
[request] = httpx_mock.get_requests()
params = dict(request.url.params)
assert params["symbol"] == "DLR/DIC23"
```

**Async testing:**
```python
async def test_async_login_obtiene_access_token(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://api.test/token",
        method="POST",
        json={"access_token": "tok-iol", "expires_in": 900},
    )
    assert await aio.login() == "tok-iol"
```

**204 / empty body:**
```python
def test_get_listado_cuentas_204_devuelve_lista_vacia(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(status_code=204)
    assert higyrus_client.get_listado_cuentas() == []
```

**Token refresh logic:**
```python
def test_ensure_token_skips_when_fresh(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_client, "_token", "fresh")
    monkeypatch.setattr(_client, "_token_ts", time.time())
    called = {"n": 0}

    def fake_login() -> str:
        called["n"] += 1
        return "new"

    monkeypatch.setattr(_client, "login", fake_login)
    _client._ensure_token()
    assert called["n"] == 0
```

---

*Testing analysis: 2026-05-27*
