# Phase 22: Instruments + symbols(read) + calendar(read) + modelos - Pattern Map

**Mapped:** 2026-07-30
**Files analyzed:** 6 (5 modified + 1 test surface)
**Analogs found:** 6 / 6 (all exact, same-package Phase-21 precedents)

This phase is a purely additive read-surface extension of `packages/market-data-client/`.
Every new symbol has a direct Phase-21 analog living in the SAME package — the planner
copies existing structures verbatim and swaps endpoint paths, filter kwargs, and model
shapes. No cross-package imports (no-shared-internals constraint). Dual sync/async parity
is mandatory. All new modules already carry `from __future__ import annotations`.

## File Classification

| Modified File | Role | Data Flow | Closest Analog (same file) | Match Quality |
|---------------|------|-----------|----------------------------|---------------|
| `src/market_data_client/_core.py` | utility (pure builders/parsers) | request-response / transform | `build_market_data_request` + `parse_market_data_response` (same file) | exact |
| `src/market_data_client/models.py` | model | transform (deserialize) | `MarketDataEntry` (no-`received_at` SafeModel, same file) | exact |
| `src/market_data_client/client.py` | client (sync methods + shims) | request-response / CRUD (read) | `Client.get_market_data` + top-level `get_market_data` shim | exact |
| `src/market_data_client/aio.py` | client (async methods + shims) | request-response / CRUD (read) | `AsyncClient.get_market_data` + async shim | exact |
| `src/market_data_client/__init__.py` | config (re-exports) | n/a | existing `get_market_data` / `MarketDataSnapshot` re-export block | exact |
| `tests/test_*.py` | test | request-response | `test_market_data.py` + `test_models.py` + `test_client.py` param-encoding tests | exact |

## Pattern Assignments

### `src/market_data_client/_core.py` (5 builders + 5 parsers)

**Analog:** `build_market_data_request` / `build_latest_request` (builders),
`parse_market_data_response` (collection parser), `parse_health_response` (single-object
shape reference).

**Builder template — authenticated GET with filters** (from `build_market_data_request`, `_core.py:265-308`):

```python
def build_market_data_request(
    state: _ClientState,
    *,
    market_id: str | None = None,
    # ... more filter kwargs, all `X | None = None`
) -> RequestSpec:
    del state  # state-independent (filtros vienen por kwargs)
    params = _params.drop_none(
        {
            "market_id": market_id,
            # ... one entry per filter kwarg
        }
    )
    return RequestSpec(
        method="GET",
        path="/marketdata",
        params=params or None,   # empty dict → None (D-02)
        idempotent=True,
        endpoint_name="market_data",
        authenticated=True,
    )
```

**Builder template — no-params GET** (from `build_health_request`, `_core.py:228-237`; the
segments / calendar-config builders take NO filter kwargs — use this shape, but set
`authenticated=True` since D-01 makes these authenticated, unlike anonymous health):

```python
def build_health_request(state: _ClientState) -> RequestSpec:
    del state  # state-independent
    return RequestSpec(
        method="GET",
        path="/health",
        idempotent=True,
        endpoint_name="health",
        authenticated=False,   # <-- for segments/calendar_config use authenticated=True (D-01)
    )
```

Per D-01, the 5 builders and their endpoints/`endpoint_name`s:
| Builder | path | filter kwargs (D-02) | endpoint_name |
|---------|------|----------------------|---------------|
| `build_instruments_request` | `/instruments` | `q, segment, market_id, include_expired, only_outright, subscribed, limit, offset, refresh` | `instruments` |
| `build_segments_request` | `/instruments/segments` | none | `segments` |
| `build_symbols_request` | `/symbols` | `active, market_id, prefix` | `symbols` |
| `build_calendar_request` | `/calendar` | `year` | `calendar` |
| `build_calendar_config_request` | `/calendar/config` | none | `calendar_config` |

All five: `method="GET"`, `authenticated=True`, `idempotent=True` (D-01). Booleans ride
httpx-native encoding — do NOT copy higyrus `format_bool` (D-03).

**Collection parser template** (from `parse_market_data_response`, `_core.py:365-383`) — but
STRIP the `received_at` stamp (D-05/D-06). Reference parsers do NOT capture wall-clock:

```python
def parse_market_data_response(resp: httpx.Response) -> list[MarketDataSnapshot]:
    resp.read()
    received_at = time.time()          # <-- OMIT this line for reference parsers (D-05)
    raise_for_response(resp)
    if not resp.content:
        return []
    raw = resp.json()
    if raw is None:
        return []
    return [MarketDataSnapshot.from_api(item, received_at=received_at) for item in raw]
    #        ^ reference: `Model.from_api(item)` — no received_at kwarg (D-05)
```

Reference collection parser (instruments/segments/symbols/calendar) — the exact shape to write:

```python
def parse_instruments_response(resp: httpx.Response) -> list[Instrument]:
    resp.read()
    raise_for_response(resp)
    if not resp.content:
        return []
    raw = resp.json()
    if raw is None:
        return []
    return [Instrument.from_api(item) for item in raw]
```

**Single-object parser template** (D-07 — `parse_calendar_config_response`). The body-consume
order comes from `parse_health_response` (`_core.py:252-257`), but returns a typed model via
`from_api(raw)` with tolerant empty-body fallback (NOT a raw dict):

```python
def parse_calendar_config_response(resp: httpx.Response) -> CalendarConfig:
    resp.read()
    raise_for_response(resp)
    if not resp.content:
        return CalendarConfig.from_api(None)   # tolerant empty default (D-07)
    raw = resp.json()
    return CalendarConfig.from_api(raw)        # from_api(None) is safe too
```

**`__all__` update:** the module `__all__` (`_core.py:63-77`) is a sorted list — insert the 5
`build_*` and 5 `parse_*` names in alphabetical position. Add the 5 model imports to the
`from market_data_client.models import (...)` block (`_core.py:61`).

---

### `src/market_data_client/models.py` (5 SafeModel dataclasses)

**Analog:** `MarketDataEntry` (`models.py:108-120`) — the KEY precedent (D-05): a plain
`SafeModel` subclass with NO `received_at`, no custom `from_api` override. Do NOT copy
`MarketDataSnapshot`'s custom `from_api` (that override exists ONLY to inject `received_at`).

**Exact template to replicate for each of the 5 new models:**

```python
@dataclass(frozen=True, slots=True)
class MarketDataEntry(SafeModel):
    """A single market-data entry row nested inside a :class:`MarketDataSnapshot`.

    PROVISIONAL shape (A1/A2 — OpenAPI not vendored; Phase 23 reconciles field
    names against real payloads). A plain :class:`SafeModel` subclass: it carries
    NO ``received_at`` (only the top-level snapshot is client-stamped).
    """

    entryType: str
    price: float
    size: float
```

New models per D-04 (all `@dataclass(frozen=True, slots=True)`, inherit `SafeModel`,
camelCase wire fields verbatim, PROVISIONAL shapes tolerant via inherited `from_api`):
`Instrument`, `Segment`, `Symbol`, `CalendarDay`, `CalendarConfig`. Exact field shapes are
Claude's Discretion (designed from endpoint semantics; `from_api` tolerance absorbs Phase-23
corrections). `CalendarConfig` is the singular non-collection model (D-07).

**`_coerce` field-type support** (`models.py:64-105`): only `str`, `bool`, `int`, `float`,
`list[X]`, nested `SafeModel`, and `X | None` are coerced. Design new model fields from this
palette. `X | None` fields default to `None` (nullable opt-in); everything else falls to a
typed zero.

**`__all__` update:** `models.py:43` is a sorted list — insert the 5 new class names
alphabetically (result order: `CalendarConfig`, `CalendarDay`, `Instrument`, `LatestRequest`,
`MarketDataEntry`, `MarketDataSnapshot`, `SafeModel`, `Segment`, `Symbol`).

**N815:** `models.py` is already exempt from the camelCase-field lint — no `pyproject.toml`
change (D-04).

---

### `src/market_data_client/client.py` (5 sync methods + 5 module-level shims)

**Analog:** `Client.get_market_data` method (`client.py:360-393`) + top-level `get_market_data`
shim (`client.py:508-531`). Method dispatch is a strict 3-line body: build spec → `_request` →
parse (D-08).

**Method template** (from `Client.get_market_data`, `client.py:360-393`):

```python
def get_market_data(
    self,
    *,
    market_id: str | None = None,
    # ... filter kwargs mirroring the builder signature
) -> list[MarketDataSnapshot]:
    """Authenticated ``GET {base_url}/marketdata`` → list of snapshots (D-06)."""
    spec = _core.build_market_data_request(
        self._state,
        market_id=market_id,
        # ... pass through every filter kwarg
    )
    resp = self._request(spec)
    return _core.parse_market_data_response(resp)
```

For `get_calendar_config`, return type is the single `CalendarConfig` (not `list[...]`) and
the parser is `parse_calendar_config_response`.

**Module-level shim template** (from `get_market_data` shim, `client.py:508-531`):

```python
def get_market_data(
    *,
    market_id: str | None = None,
    # ... same filter kwargs
) -> list[MarketDataSnapshot]:
    """Top-level shim: delega al default Client."""
    return _get_default().get_market_data(
        market_id=market_id,
        # ... pass through
    )
```

**Import update:** add the 5 model classes to the
`from market_data_client.models import (...)` block (`client.py:54`). No new deps.

Method names (Claude's Discretion, working names): `get_instruments`, `get_segments`,
`get_symbols`, `get_calendar`, `get_calendar_config` — consistent with the concise existing
surface (`get_market_data`, `get_latest`).

`with_options(max_retries=N)` (`client.py:199-227`) already threads through `_request` — the
new methods inherit the per-call retry cap for free (D-08). No changes needed there.

---

### `src/market_data_client/aio.py` (5 async methods + 5 module-level shims)

**Analog:** `AsyncClient.get_market_data` (`aio.py:373-407`) + async shim `get_market_data`
(`aio.py:520-543`). IDENTICAL body to the sync method except `await self._request(spec)`
(D-08 dual-parity — logic duplicated by design, no shared internals).

**Async method template** (from `AsyncClient.get_market_data`, `aio.py:373-407`):

```python
async def get_market_data(
    self,
    *,
    market_id: str | None = None,
    # ... same filter kwargs as sync
) -> list[MarketDataSnapshot]:
    """Autenticado ``GET {base_url}/marketdata`` → lista de snapshots (D-06)."""
    spec = _core.build_market_data_request(
        self._state,
        market_id=market_id,
        # ...
    )
    resp = await self._request(spec)      # <-- only difference from sync: await
    return _core.parse_market_data_response(resp)
```

**Async shim template** (from `aio.py:520-543`):

```python
async def get_market_data(
    *,
    market_id: str | None = None,
    # ...
) -> list[MarketDataSnapshot]:
    """Top-level shim: delega al default Client."""
    return await _get_default().get_market_data(market_id=market_id, ...)
```

Parity check: every method/shim added to `client.py` MUST have an identical async twin here
(same name, same signature, `async`/`await` added, same builder + parser). The builders and
parsers are shared from `_core.py` — only the dispatch surface is duplicated.

---

### `src/market_data_client/__init__.py` (re-exports)

**Analog:** the existing `get_market_data` / `MarketDataSnapshot` re-export wiring.

Three edits, each mirroring an existing entry:
1. `from market_data_client.client import (...)` block (`__init__.py:40-49`) — add the 5 new
   sync shim names (async shims live on `aio`, imported as needed; the sync top-level surface
   is what `__init__` re-exports, matching `get_market_data`).
2. `from market_data_client.models import (...)` block (`__init__.py:56-60`) — add the 5 new
   model classes.
3. `__all__` (`__init__.py:65-81`, sorted) — insert the 5 method names + 5 model class names
   alphabetically.

Note: the async `AsyncClient` methods are reached via `from market_data_client import aio` —
`aio`'s own module-level shims are NOT added to the package `__all__` (matches the existing
`get_market_data` treatment, where only the sync shim is in `__all__`).

---

### `tests/` (mocked pytest-httpx coverage — D-09)

Three analog test layers exist; organizing new tests (extend vs. dedicated `test_reference.py`)
is Claude's Discretion (D-09). Copy from:

**1. Pure `_core` builder/parser tests** — analog `test_market_data.py` (`tests/test_market_data.py:1-191`).
Synthetic `_ClientState` + `httpx.Response` via the local `_resp()` helper
(`test_market_data.py:39-47`). Cover per D-09:
- builder param serialization — falsy preserved (`active=False`, `offset=0`, `""`), None
  dropped, empty→`params=None`. Template: `test_build_market_data_request_shape_and_params`
  (`test_market_data.py:69-91`).
- collection parser 204/None→`[]` guard. Template:
  `test_parse_market_data_response_null_body_returns_empty` (`test_market_data.py:153-158`) —
  tests both `content=b"null"` and a bare `204`.
- 401→`MarketDataAuthError`. Template: `test_market_data.py:161-164`.
- single-object `calendar/config` parse + empty-body tolerance (D-07) — new assertion shape:
  empty body → `CalendarConfig.from_api(None)`, never a raise.

**2. Model tolerance tests** — analog `test_models.py` (`tests/test_models.py:1-99`).
Cover `from_api` partial/None/extra-key tolerance for each new model. Templates:
`test_from_api_empty_dict_typed_zero_defaults` (`test_models.py:25-29`),
`test_from_api_none_does_not_raise` (`test_models.py:32-35`),
`test_from_api_extra_keys_ignored` (`test_models.py:38-43`). Assert new models carry NO
`received_at` (D-05) — mirror `assert not hasattr(...)` at `test_models.py:80`.

**3. Shell end-to-end param-encoding tests (sync + async)** — analogs
`test_client.py:192-232` and its async twin in `test_async_client.py`. Use the `httpx_mock`
fixture; assert Bearer injection + wire-encoded params. Template
`test_get_market_data_sends_bearer_and_encodes_params` (`test_client.py:192-216`):

```python
def test_get_market_data_sends_bearer_and_encodes_params(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url=f"{_BASE}/marketdata", method="GET", json=[...])
    result = market_data_client.client._get_default().get_market_data(
        market_id="ROFX", active=False, with_data=True, limit=10,
    )
    req = httpx_mock.get_requests()[0]
    assert req.url.path == "/api/marketdata"
    assert req.url.params.get("active") == "false"   # httpx-native bool encoding (D-03)
    assert req.url.params.get("with_data") == "true"
    assert req.url.params.get("limit") == "10"
    assert "prefix" not in req.url.params
```

Full sync/async parity required (D-09). All four CI gates green (ruff / format / mypy strict /
pytest).

## Shared Patterns

### `drop_none` filter serialization
**Source:** `packages/market-data-client/src/market_data_client/_params.py:22-28`
**Apply to:** all builders with filter kwargs (`instruments`, `symbols`, `calendar`).
```python
params = _params.drop_none({"market_id": market_id, ...})
return RequestSpec(..., params=params or None, ...)
```
Drops only `None`; preserves `False`/`0`/`""`. Empty dict collapses to `params=None` via
`params or None` (D-02). Do NOT add `format_bool` — booleans ride httpx-native encoding (D-03).

### RequestSpec contract for authenticated reads
**Source:** `packages/market-data-client/src/market_data_client/_core.py:85-109`
**Apply to:** all 5 builders.
`method="GET"`, `authenticated=True` (triggers Bearer injection + `_ensure_token` in
`_request`), `idempotent=True` (retry-eligible GET), distinct `endpoint_name` (flows to
structured logs) (D-01).

### Body-consume-then-raise parser order
**Source:** `parse_market_data_response` (`_core.py:375-383`), `parse_health_response` (`_core.py:252-257`)
**Apply to:** all 5 parsers.
`resp.read()` → `raise_for_response(resp)` → decode. Collection parsers add the
`if not resp.content / raw is None: return []` guard (D-06). Reference parsers OMIT the
`received_at = time.time()` stamp (D-05).

### SafeModel tolerant deserialization
**Source:** `SafeModel` + `_coerce` (`models.py:46-105`), `MarketDataEntry` (`models.py:108-120`)
**Apply to:** all 5 new models.
`@dataclass(frozen=True, slots=True)` + inherit `SafeModel`; build via inherited `from_api`
(no override — that's the `MarketDataEntry` no-`received_at` precedent, D-05). camelCase wire
fields. Fields drawn from `_coerce`-supported types.

### Dispatch triple: method → shim → export
**Source:** `Client.get_market_data` (`client.py:360-393`), shim (`client.py:508-531`),
async twin (`aio.py:373-407`, `aio.py:520-543`), `__init__` re-export (`__init__.py:40-81`).
**Apply to:** all 5 endpoints, both surfaces. Method body is 3 lines (build → request →
parse). Sync and async are identical except `await`. `with_options` retry-cap threading is
already wired through `_request` — inherited free (D-08).

### Test conftest / singleton isolation
**Source:** `tests/conftest.py:29-73`
**Apply to:** all new tests. Autouse fixtures seed a non-expiring token
(`NEVER_EXPIRES = 9_999_999_999.0`) so param-encoding tests skip the auth grant; teardown
closes the transport so `httpx_mock` intercepts a fresh client each test (Pitfall 6).

## No Analog Found

None. Every file has an exact same-package Phase-21 precedent. This phase is mechanically
additive — the planner replicates known structures with new paths, kwargs, and model shapes.

## Metadata

**Analog search scope:** `packages/market-data-client/src/market_data_client/` (all modules)
and `packages/market-data-client/tests/`.
**Files scanned:** `_core.py`, `models.py`, `_params.py`, `client.py`, `aio.py`,
`__init__.py`, `tests/test_market_data.py`, `tests/test_models.py`, `tests/test_client.py`,
`tests/conftest.py`.
**Pattern extraction date:** 2026-07-30
