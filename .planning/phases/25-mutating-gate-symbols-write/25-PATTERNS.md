# Phase 25: Mutating-gate + Symbols write - Pattern Map

**Mapped:** 2026-07-31
**Files analyzed:** 7 modified + 4 new test files (11 artifacts)
**Analogs found:** 11 / 11 (every artifact has an in-package precedent)

All analogs live inside `packages/market-data-client/` — the phase is a purely
additive extension of one package, so every excerpt below is same-package,
same-role, same-data-flow (exact match). No cross-package borrowing (forbidden by
the no-shared-internals constraint).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/market_data_client/_core.py` (+3 builders) | pure builder | request-response (POST/PATCH w/ JSON body) | `build_latest_batch_request` (same file, `_core.py:361-377`) | exact |
| `src/market_data_client/models.py` (+3 request models) | model (serialize-OUT) | transform (dataclass → wire dict) | `LatestRequest` + `to_dict()` (same file, `models.py:160-181`) | exact |
| `src/market_data_client/exceptions.py` (+1 exception) | exception | — | `MarketDataError` hierarchy (same file, `exceptions.py:6-24`) | exact |
| `src/market_data_client/_state.py` (+2 fields) | state (dataclass) | — | existing `_ClientState` slotted fields (`_state.py:77-99`) | exact |
| `src/market_data_client/client.py` (gate + 3 methods + params + shims) | stateful shell (sync) | request-response | `get_symbols` method (`client.py:470-485`) + `_request` (`289-346`) + `configure` (`516-571`) + `__init__` (`117-144`) + `with_options` (`207-235`) | exact |
| `src/market_data_client/aio.py` (mirror) | stateful shell (async) | request-response | `get_symbols` (`aio.py:484-499`) + `_request` (`297-359`) + `configure` (`534+`) + `__init__` (`96-134`) | exact |
| `src/market_data_client/__init__.py` (re-exports) | package barrel | — | existing `__all__` block (`__init__.py:39-99`) | exact |
| `tests/test_mutation_gate.py` (NEW) | test | request-response | `test_get_latest_batch_sends_bearer_and_body` (`test_client.py:241-255`) | role-match |
| `tests/test_symbols_write.py` + `_async.py` (NEW) | test | request-response | `test_get_latest_batch_sends_bearer_and_body` (`test_client.py:241-255`) | exact |
| `tests/test_public_surface_market_data.py` (NEW) | test | — | (no in-package precedent — see No Analog Found) | none |
| `tests/test_models.py` + `test_core.py` (EXTEND) | test | transform / builder-spec | `test_latest_request_to_dict_*` (`test_models.py:129-140`), `test_build_latest_batch_request_posts_serialized_body` (`test_market_data.py:121-132`) | exact |

## Pattern Assignments

### `_core.py` — 3 new builders (pure builder, POST/PATCH with JSON body)

**Analog:** `build_latest_batch_request` at `packages/market-data-client/src/market_data_client/_core.py:361-377`

**Core pattern to copy** (the POST-with-json_body pure builder — `del state`, no I/O):
```python
def build_latest_batch_request(state: _ClientState, latest_request: LatestRequest) -> RequestSpec:
    del state  # state-independent (payload viene en latest_request)
    return RequestSpec(
        method="POST",
        path="/marketdata/latest",
        json_body=latest_request.to_dict(),
        idempotent=True,
        endpoint_name="latest_batch",
        authenticated=True,
    )
```

`RequestSpec` (same file `_core.py:103-127`) already carries `method`, `path`,
`json_body`, `idempotent`, `endpoint_name`, `authenticated` — **no structural change
needed** (D-06). The three new builders each take the already-serialized dict
(`model.to_dict()`) as `json_body`, set `idempotent=True` (DM-03), `authenticated=True`:

- `build_create_symbol_request` → `method="POST"`, `path="/symbols"`, `endpoint_name="create_symbol"`
- `build_create_symbols_request` → `method="POST"`, `path="/symbols/batch"`, `endpoint_name="create_symbols"`
- `build_update_symbol_request` → `method="PATCH"`, `path=f"/symbols/{symbol_id}"`, `endpoint_name="update_symbol"` (D-08: interpolate `symbol_id` raw for Phase 25; percent-encoding deferred to Phase 27)

**`__all__` update:** add the three builder names to the sorted `__all__` list at `_core.py:71-95`.

**Do NOT** put the gate check here — `_core` builders `del state` and stay IO-free / state-agnostic (D-05). Also note the existing `build_symbols_request` (`_core.py:448-476`) is the GET read analog — mirror its `endpoint_name`/`path` style, not its `params` shape.

---

### `models.py` — 3 new frozen request models with `to_dict()` (serialize-OUT)

**Analog:** `LatestRequest` at `packages/market-data-client/src/market_data_client/models.py:160-181`

**Core pattern to copy** (frozen dataclass, NOT a `SafeModel`, hand-written `to_dict()`):
```python
@dataclass(frozen=True, slots=True)
class LatestRequest:
    symbols: list[str]
    marketId: str | None = None
    entries: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a wire dict, dropping ``None``-valued optional fields."""
        out: dict[str, Any] = {"symbols": self.symbols}
        if self.marketId is not None:
            out["marketId"] = self.marketId
        if self.entries is not None:
            out["entries"] = self.entries
        return out
```

New models per D-09/D-10 (note: snake_case `market_id` wire key per source-plan schema —
**intentionally different** from `LatestRequest`'s camelCase `marketId`; Pitfall 3 / A2):
```python
@dataclass(frozen=True, slots=True)
class NewSymbol:
    symbol: str
    market_id: str = "ROFX"          # D-10: defaulted, non-nullable, ALWAYS sent
    def to_dict(self) -> dict[str, Any]:
        return {"symbol": self.symbol, "market_id": self.market_id}

@dataclass(frozen=True, slots=True)
class NewSymbols:
    symbols: list[NewSymbol]
    def __post_init__(self) -> None:                       # D-11: client-side ValueError
        if not 1 <= len(self.symbols) <= 500:
            raise ValueError(f"NewSymbols requires 1-500 symbols, got {len(self.symbols)}")
    def to_dict(self) -> dict[str, Any]:
        return {"symbols": [s.to_dict() for s in self.symbols]}

@dataclass(frozen=True, slots=True)
class SymbolPatch:
    active: bool
    def to_dict(self) -> dict[str, Any]:
        return {"active": self.active}
```

**`__post_init__` on a frozen dataclass:** allowed as long as it does not mutate fields
(the `ValueError`-only body here does not) — no `object.__setattr__` needed. The
`_validate_max_retries` precedent (`client.py:79-95`) is the ValueError-shape analog,
but placement is inside the model (D-11), not a free function.

**`__all__` update:** add `NewSymbol`, `NewSymbols`, `SymbolPatch` to the sorted `__all__`
at `models.py:43-52`. **Do NOT** subclass `SafeModel` (that is the deserialize-IN pattern,
e.g. `Symbol` at `models.py:227-238`); request models serialize OUT.

---

### `exceptions.py` — `MarketDataMutationNotAllowedError`

**Analog:** the base `MarketDataError` and its subclasses at `exceptions.py:6-24`

**Pattern:** subclass `MarketDataError` **directly** (D-16 / A6 — it is a client-side
policy refusal, NOT a server error; it takes NO `status_code`, unlike `MarketDataAPIError`
at `exceptions.py:10-16` which requires `(status_code, message)`):
```python
class MarketDataMutationNotAllowedError(MarketDataError):
    """Mutation refused: mutating_allowed is False or base_url host != expected_host."""
```
`MarketDataError` is a bare `Exception` subclass, so a plain `str` message constructor is
inherited — no `__init__` override needed.

**`__all__` note:** `exceptions.py` currently has **no `__all__`** (RESEARCH finding, D-16
overstated). Adding one is optional; re-export flows through `__init__.py` regardless.

---

### `_state.py` — 2 new `_ClientState` fields

**Analog:** existing slotted fields at `_state.py:77-99` and the `DEFAULT_BASE_URL` constant at `_state.py:48`

**Pattern to copy** (plainly-typed fields on the `@dataclass(slots=True)` state):
```python
@dataclass(slots=True)
class _ClientState:
    base_url: str = field(default_factory=_env_base_url)
    ...
    mutating_allowed: bool = False            # D-13: refuse-by-default
    expected_host: str | None = None          # D-01/D-02: defaults to DEFAULT_BASE_URL host
```

**`expected_host` default (D-02):** default to the hostname of `DEFAULT_BASE_URL`
(`"market-data-develop.bbsa.com.ar"`). Cleanest mypy-strict approach: define a module
constant near `DEFAULT_BASE_URL` (`_state.py:48`), e.g.
`_DEFAULT_EXPECTED_HOST = urlsplit(DEFAULT_BASE_URL).hostname` — but `urlsplit(...).hostname`
is typed `str | None`, so either `assert`/narrow it or store the literal string
`"market-data-develop.bbsa.com.ar"` directly to keep the field type clean. Use
`field(default=_DEFAULT_EXPECTED_HOST)` (a plain constant, NOT a factory).

**Do NOT** add these to any instance `__slots__` — they MUST live on the shared
`_ClientState` so `with_options` views inherit them (D-14). Add both to the `__all__`?
No — `_ClientState` itself is already exported; the fields are attributes.

---

### `client.py` — gate helper + 3 methods + constructor/configure params + shims (sync shell)

**(a) New `_ensure_mutation_allowed()` helper** — no direct in-package analog for the body;
mirror the exact-host discipline from `verification/mutation_gate.py:56-63`:
```python
# verification/mutation_gate.py:59-63 — exact-hostname discipline to mirror
if urlsplit(base).hostname != _SANDBOX_HOST:
    print("SKIPPED (mutating, guard off)")  # host no-sandbox -> nunca mutar
    return False
return True
```
New helper (raises instead of returning bool; state-driven, on the shell per D-04/D-05):
```python
from urllib.parse import urlsplit  # add to imports

def _ensure_mutation_allowed(self) -> None:
    if not self._state.mutating_allowed:
        raise MarketDataMutationNotAllowedError(
            "Mutations refused: set mutating_allowed=True (constructor or configure())."
        )
    expected = self._state.expected_host
    actual = urlsplit(self._state.base_url).hostname
    if expected is not None and actual != expected:   # EXACT match, never substring (D-01)
        raise MarketDataMutationNotAllowedError(
            f"Mutations refused: base_url host {actual!r} != expected_host {expected!r}."
        )
```

**(b) New mutation methods** — mirror the uniform `get_symbols` method shape at
`client.py:470-485`, but insert the gate as the FIRST statement (before `_core.build_*`,
before `self._request`, before any token fetch — Pitfall 1 / D-04):
```python
# ANALOG — client.py:470-485 (get_symbols): spec -> self._request -> parse
def get_symbols(self, *, active=None, market_id=None, prefix=None) -> list[Symbol]:
    spec = _core.build_symbols_request(self._state, active=active, market_id=market_id, prefix=prefix)
    resp = self._request(spec)
    return _core.parse_symbols_response(resp)
```
New method shape:
```python
def create_symbol(self, new_symbol: NewSymbol) -> ...:
    self._ensure_mutation_allowed()                      # FIRST — zero IO on refusal (D-05)
    spec = _core.build_create_symbol_request(self._state, new_symbol.to_dict())
    resp = self._request(spec)
    return _core.parse_symbols_response(resp)            # tolerant parse; shape deferred to Phase 27
```
`update_symbol(symbol_id, patch)` additionally passes `symbol_id` to the builder. Response
parser is a Phase-27-deferred shape (A1) — reuse `parse_symbols_response` (`_core.py:614-627`)
or add a single-object `parse_symbol_response`; either stays tolerant via `Symbol.from_api`.

**(c) Constructor params** — mirror the `if x is not None:` carry-forward chain at
`client.py:130-139`. For the bool, use `mutating_allowed: bool | None = None` +
`if mutating_allowed is not None: self._state.mutating_allowed = mutating_allowed`
(Pitfall 5 — a fresh `_ClientState()` already defaults `False`, so this is safe):
```python
# ANALOG — client.py:130-139
if base_url is not None:
    self._state.base_url = base_url.rstrip("/")
if client_id is not None:
    self._state.client_id = client_id
```

**(d) `configure()` carry-forward** — mirror `client.py:516-571`. Add
`mutating_allowed: bool | None = None` and `expected_host: str | None = None`; apply
each only under `if ... is not None:` (Pitfall 5 — a bare `configure(base_url=...)` must
NOT reset the flag). These are pure config, NOT credentials, so they must NOT set the
`rotated` flag that invalidates the token (`client.py:542-557`):
```python
# ANALOG — client.py:543-545 (carry-forward guard, but WITHOUT rotated=True)
if base_url is not None:
    state.base_url = base_url.rstrip("/")
    rotated = True
```

**(e) `with_options` — zero new code needed** (D-14). It already shares `self._state`
(`client.py:231-235`: `view._state = self._state`), so the gate fields propagate to views
automatically:
```python
view = type(self).__new__(type(self))
view._state = self._state  # SHARE — anti-Pitfall 13   (gate inherits for free)
```

**(f) Module-level shims** — mirror `get_symbols` shim at `client.py:656-663`:
```python
def get_symbols(*, active=None, market_id=None, prefix=None) -> list[Symbol]:
    return _get_default().get_symbols(active=active, market_id=market_id, prefix=prefix)
```
Add `create_symbol`, `create_symbols`, `update_symbol` shims delegating to `_get_default()`.

---

### `aio.py` — identical async mirror

**Analog:** the sync `client.py` additions above, mapped to the async precedents:

| Sync site (`client.py`) | Async analog (`aio.py`) |
|-------------------------|-------------------------|
| method shape `get_symbols` (`470-485`) | `get_symbols` async (`aio.py:484-499`) — `resp = await self._request(spec)` |
| `_request` (`289-346`) | `_request` async (`aio.py:297-359`) — already threads `json=spec.json_body` at `aio.py:328` |
| `__init__` carry-forward (`117-144`) | `__init__` (`aio.py:96-134`) |
| `configure` (`516-571`) | `configure` (`aio.py:534+`) |
| shims (`656-663`) | async shims under `aio` (`aio.py:668+`) |

The async `_request` (`aio.py:297-359`) already passes `json=spec.json_body` (line 328),
so no transport change. `_ensure_mutation_allowed` is a pure state read (no `await`) — copy
the sync helper verbatim into `AsyncClient`; the async mutation methods call it as the first
(non-awaited) statement before `await self._request(spec)`. Mirror EVERY method, helper,
param, and shim identically (D-15).

---

### `__init__.py` — re-exports

**Analog:** the existing barrel `__all__` at `__init__.py:39-99`

Add to the `from market_data_client.client import (...)` block: `create_symbol`,
`create_symbols`, `update_symbol`. Add to `from ...exceptions import (...)`:
`MarketDataMutationNotAllowedError`. Add to `from ...models import (...)`: `NewSymbol`,
`NewSymbols`, `SymbolPatch`. Add all seven public names to the sorted `__all__`
(`__init__.py:74-99`). Async methods stay under `aio` (not flat-namespace re-exported).

---

### Test files

**Wire-body serialization test (the highest-value template)** — mirror
`test_get_latest_batch_sends_bearer_and_body` at `tests/test_client.py:241-255`:
```python
def test_get_latest_batch_sends_bearer_and_body(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(method="POST", json=[{"symbol": "GGAL", "marketId": "ROFX", "entries": []}])
    latest_request = LatestRequest(symbols=["GGAL", "YPFD"], marketId="ROFX")
    result = market_data_client.client._get_default().get_latest_batch(latest_request)
    req = httpx_mock.get_requests()[0]
    assert req.method == "POST"
    assert req.url.path == "/api/marketdata/latest"
    assert req.headers["Authorization"] == "Bearer test-token"
    assert _json.loads(req.content) == {"symbols": ["GGAL", "YPFD"], "marketId": "ROFX"}
```
Symbols equivalent (`test_symbols_write.py`): mock a 201, call
`create_symbol(NewSymbol("DLR/DIC26"))`, assert `req.method == "POST"`,
`req.url.path == "/api/symbols"`, `_json.loads(req.content) == {"symbol": "DLR/DIC26", "market_id": "ROFX"}`.
**IMPORTANT (see Shared Patterns / conftest):** the gate must be opened first — construct
`Client(mutating_allowed=True, expected_host="market-data-develop.test")` OR call the module
`configure(mutating_allowed=True, expected_host="market-data-develop.test")`, because the
conftest sets `base_url` host to `market-data-develop.test` (NOT the default
`market-data-develop.bbsa.com.ar`).

**Builder unit test** — mirror `test_build_latest_batch_request_posts_serialized_body` at
`tests/test_market_data.py:121-132` (extend `test_core.py`):
```python
def test_build_create_symbol_request() -> None:
    state = _ClientState()
    spec = _core.build_create_symbol_request(state, NewSymbol("DLR/DIC26").to_dict())
    assert spec.method == "POST"
    assert spec.path == "/symbols"
    assert spec.authenticated is True
    assert spec.idempotent is True                      # DM-03
    assert spec.json_body == {"symbol": "DLR/DIC26", "market_id": "ROFX"}
```

**Model to_dict + ValueError bounds** — mirror `test_latest_request_to_dict_*` at
`tests/test_models.py:129-140` (extend `test_models.py`):
```python
def test_latest_request_to_dict_drops_none_optionals() -> None:
    req = LatestRequest(symbols=["GGAL", "YPFD"])
    assert req.to_dict() == {"symbols": ["GGAL", "YPFD"]}
```
Add `NewSymbols([])` and `NewSymbols([...501 items])` → `pytest.raises(ValueError)`.

**Gate-refusal test (NEW, `test_mutation_gate.py`)** — no exact analog; asserts D-05
zero-side-effect. Uses the `httpx_mock` fixture from `test_client.py` and the `pytest.raises`
idiom (`test_client.py:237`):
```python
def test_create_symbol_refused_by_default_emits_no_request(httpx_mock: HTTPXMock) -> None:
    client = market_data_client.Client()               # mutating_allowed defaults False
    with pytest.raises(market_data_client.MarketDataMutationNotAllowedError):
        client.create_symbol(NewSymbol("DLR/DIC26"))
    assert len(httpx_mock.get_requests()) == 0         # no HTTP AND no Auth0 token fetch (D-05)
```
Also test the host-gate: `mutating_allowed=True` but `base_url` host ≠ `expected_host`
(incl. the substring-attacker host `...bbsa.com.ar.attacker.example`) → refused, 0 requests.

## Shared Patterns

### Gate placement (applies to all 3 mutation methods, both shells)
**Source:** `verification/mutation_gate.py:59-63` (exact-host discipline) + `client.py` method shape
`_ensure_mutation_allowed()` is the literal FIRST statement of every mutation method —
before `_core.build_*`, before `self._request`, before `_ensure_token`. This guarantees
zero HTTP + zero Auth0 round-trip on refusal (D-05). Never in `_core` (IO-free) nor
`_request` (shared with reads).

### Carry-forward config (applies to `__init__` + `configure`, both shells)
**Source:** `client.py:130-139` (`__init__`) and `client.py:543-566` (`configure`)
`if x is not None:` guards. For the new `bool` field use `bool | None = None` +
`if ... is not None` (Pitfall 5). The gate fields are pure config, so — unlike credentials
at `client.py:542-557` — they MUST NOT set `rotated = True` (they do not invalidate the token).

### Shared-state view propagation (applies to `with_options`, both shells)
**Source:** `client.py:231-234` — `view._state = self._state`
Zero new code: gate fields on shared `_ClientState` inherit into views automatically (D-14).

### Conftest gate reset (Pitfall 6 — MUST extend `tests/conftest.py`)
**Source:** `tests/conftest.py:29-72` (autouse `_configure_sync` / `_configure_async`)
The autouse fixtures seed `base_url="https://market-data-develop.test/api"` (host
`market-data-develop.test`) and dummy creds, and reset on teardown — but do NOT yet reset
the new `mutating_allowed` / `expected_host` singleton fields. Two consequences the plan
must handle:
1. **Cross-test contamination:** a test that flips `mutating_allowed=True` on the default
   singleton must reset it (extend the teardown `configure(...)` calls) OR use per-test
   `Client(mutating_allowed=True, ...)` instances.
2. **Host mismatch:** the conftest host (`market-data-develop.test`) ≠ the default
   `expected_host` (`market-data-develop.bbsa.com.ar`). Any "happy-path" write test that
   dispatches must set `expected_host="market-data-develop.test"` (or `None` to disable the
   host leg) when opening the gate, or the host check refuses.

### Error mapping (unchanged — reused as-is)
**Source:** `_core.raise_for_response` at `_core.py:135-147`
`422` already falls into `if resp.is_error → MarketDataAPIError` (D-12). No new status
handling in mutation methods.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `tests/test_public_surface_market_data.py` | test (export/parity) | — | No in-package export-parity test exists; the cross-package `verification/test_public_surface.py` + `test_sync_async_isolation.py` **exclude** `market_data_client` (RESEARCH finding — `_PACKAGES` lists omit it, no surface snapshot). Build fresh: assert each new public name is importable from `market_data_client` and in `__all__`; assert sync `Client` and async `AsyncClient` expose identically-named `create_symbol`/`create_symbols`/`update_symbol`. Use `hasattr` / `__all__` membership assertions. |
| `_ensure_mutation_allowed()` body | helper | — | No in-package helper does an exact-host gate; the closest discipline is `verification/mutation_gate.py:56-63` (a bool-returning print-and-skip guard in a different package). Adapt to raise `MarketDataMutationNotAllowedError` and read live `_state` (do NOT copy its `print`/`os.getenv` — the env opt-in stays in the Phase-27 harness per D-03). |

## Metadata

**Analog search scope:** `packages/market-data-client/src/market_data_client/` (all 12 modules),
`packages/market-data-client/tests/` (test precedents), `verification/mutation_gate.py` (host-gate discipline).
**Files scanned:** 8 source modules read in full/targeted + 5 test files + 1 verification module.
**Pattern extraction date:** 2026-07-31
