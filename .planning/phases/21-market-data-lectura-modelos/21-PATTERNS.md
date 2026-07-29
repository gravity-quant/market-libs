# Phase 21: Market data (lectura) + modelos - Pattern Map

**Mapped:** 2026-07-29
**Files analyzed:** 8 (2 create, 5 modify, 1 test-set create)
**Analogs found:** 8 / 8 (all in-repo templates — zero net-new design)

> **Key insight (from RESEARCH.md, confirmed by reading source):** Phase 21 is ~90% mechanical
> copy-and-adapt from FOUR in-repo templates that already solved every non-trivial sub-problem:
> - `higyrus_client/models.py` + `_params.py` → `SafeModel`/`_coerce`/`drop_none`
> - `market_data_client/_core.py` `build_health_request` → the builder template
> - `iol_client/client.py` + `aio.py` → the `with_options` shared-view-clone
> - Phase-20 `market_data_client/{client,aio}.py` → the `_request` dispatch shells
>
> The risk is **fidelity of copying**, not novel design. The three highest-risk fidelity points
> are: (1) `received_at` injection (must NOT route through `_coerce`), (2) `with_options`
> threading `extensions["max_attempts"]` (silent no-op if skipped), and (3) the async header
> reorder (D-09).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `market_data_client/models.py` ★ | model | transform (JSON→dataclass) | `higyrus_client/models.py` | exact (copy verbatim) |
| `market_data_client/_params.py` ★ | utility | transform (param serialize) | `higyrus_client/_params.py` | exact (copy `drop_none`) |
| `market_data_client/_core.py` | utility (pure builders/parsers) | request-response + transform | `_core.build_health_request` (same file) | exact (in-file template) |
| `market_data_client/client.py` (sync) | client/controller | CRUD-read + request-response | `iol_client/client.py` (`with_options`) | role-match + exact (Phase-20 self) |
| `market_data_client/aio.py` (async) | client/controller | CRUD-read + request-response | `iol_client/aio.py` (`with_options`) | role-match + exact (Phase-20 self) |
| `market_data_client/__init__.py` | config (barrel) | — | same file (Phase-20) | exact (self) |
| `pyproject.toml` (ruff N815) | config | — | **root** `pyproject.toml:72-73` | ⚠ see note |
| `tests/test_*.py` ★ | test | request-response | `tests/test_client.py` + `conftest.py` | exact (self) |

★ = net-new file.

## Pattern Assignments

### `market_data_client/models.py` ★ (model, transform) — D-01/D-03/D-04/D-05

**Analog:** `packages/higyrus-client/src/higyrus_client/models.py` — copy `SafeModel` + `_coerce` **verbatim** (no import; no-shared-internals constraint D-03).

**`SafeModel` base + imports** (`higyrus_client/models.py:23-45`):
```python
from __future__ import annotations
from dataclasses import dataclass, fields
from types import NoneType, UnionType
from typing import Any, Self, Union, cast, get_args, get_origin, get_type_hints


class SafeModel:
    @classmethod
    def from_api(cls, payload: Any) -> Self:
        data: dict[str, Any] = payload if isinstance(payload, dict) else {}
        hints = get_type_hints(cls)
        kwargs: dict[str, Any] = {}
        for field in fields(cast(Any, cls)):
            kwargs[field.name] = _coerce(data.get(field.name), hints[field.name])
        return cls(**kwargs)
```

**`_coerce` helper** (`higyrus_client/models.py:48-89`) — copy verbatim. Handles: `Optional[T]`
None-preserving; `list[X]` → `[]` + recurse; nested `SafeModel` → `X.from_api(value)`; primitives
→ typed zero **with the bool-is-subclass-of-int guard** (lines 74-87). Do NOT reinvent — it already
covers every edge (bool-vs-int, int→float widening, None → `[]`).

**`received_at` injection (the trickiest fidelity point — D-01).** The base `from_api` would route
`received_at` through `_coerce(data.get("received_at"), float)` → `0.0` (Pitfall 2). Override
`from_api` on the top-level snapshot model to inject the stamp WITHOUT coercing it from the payload
(design from RESEARCH.md §Pattern 2):
```python
@dataclass(frozen=True, slots=True)
class MarketDataSnapshot(SafeModel):
    # ... camelCase wire fields verbatim (provisional, Phase-23 reconciles) ...
    entries: list[MarketDataEntry]   # nested tolerant SafeModel — NO received_at
    received_at: float               # client-stamped, first-class (D-01)

    @classmethod
    def from_api(cls, payload: Any, *, received_at: float = 0.0) -> Self:
        data = payload if isinstance(payload, dict) else {}
        hints = get_type_hints(cls)
        kwargs: dict[str, Any] = {}
        for field in fields(cls):
            if field.name == "received_at":
                kwargs[field.name] = received_at        # INJECT — skip _coerce
            else:
                kwargs[field.name] = _coerce(data.get(field.name), hints[field.name])
        return cls(**kwargs)
```
Nested `entries` models use the plain base `from_api` (no `received_at`) — the base `_coerce`
recursion for `list[MarketDataEntry]` needs no change.

**Model shape convention** (from `higyrus_client/models.py:92-134` `PosicionValuada`): `@dataclass(frozen=True, slots=True)`,
camelCase wire field names verbatim, one dataclass per wire object, nested list models declared above
their parent. Wire field names are PROVISIONAL (A1/A2 — OpenAPI not vendored; Phase-23 reconciles;
`from_api` tolerance bounds the blast radius).

**`LatestRequest` (D-05)** — a typed **request** dataclass (not a `SafeModel`; it serializes OUT).
Model it frozen with an explicit `to_dict()` (or `dataclasses.asdict`) so Phase-23 can adjust field
names in one place; the `_core` batch builder calls it for `json_body`.

**Module docstring + N815 note:** mirror the `higyrus_client/models.py:1-21` docstring (purpose,
safe-default table, camelCase-verbatim rationale, N815-exempt reference).

---

### `market_data_client/_params.py` ★ (utility, transform) — D-07

**Analog:** `packages/higyrus-client/src/higyrus_client/_params.py` — copy `drop_none` **verbatim**.

**`drop_none`** (`higyrus_client/_params.py:53-59`):
```python
def drop_none(params: dict[str, Any]) -> dict[str, Any]:
    """Return ``params`` without keys whose value is ``None``.

    Preserves falsy-but-not-None values (``False``, ``0``, ``""``) because
    those are legitimate API inputs.
    """
    return {k: v for k, v in params.items() if v is not None}
```
The falsy-but-not-None preservation is load-bearing: `active=False`, `offset=0`, `prefix=""` are
legitimate filters that must survive. **Do NOT copy `format_date`/`format_bool`** (higyrus-specific
`dd/mm/yyyy` + capitalized-bool conventions) — D-07 defers to httpx-native `True→"true"` encoding
for market-data; explicit encoding is a Phase-23 target. `__all__ = ["drop_none"]`.

---

### `market_data_client/_core.py` (utility, builders + parsers) — D-06/D-01

**Analog:** the existing `build_health_request` (`_core.py:221-230`) in the SAME file — the builder
template. Market-data builders flip two flags: `authenticated=False → True` and add `params`/`json_body`.

**`RequestSpec` already carries every field needed** (`_core.py:78-102`) — NO dataclass surgery:
```python
@dataclass(frozen=True, slots=True)
class RequestSpec:
    method: str
    path: str
    params: dict[str, Any] | None = None
    headers: dict[str, str] | None = None
    json_body: dict[str, Any] | None = None
    data: dict[str, Any] | None = None
    idempotent: bool = False
    endpoint_name: str = ""
    authenticated: bool = True
```

**Builder template** (`build_health_request`, `_core.py:221-230`) → adapt to the three read builders,
each `RequestSpec(authenticated=True, idempotent=True)` (D-06 — `authenticated=True` triggers Bearer
injection; GET reads are idempotent → retry-eligible):
```python
def build_market_data_request(state, *, market_id=None, prefix=None, active=None,
                              entries=None, max_staleness_seconds=None, with_data=None,
                              order=None, limit=None, offset=None) -> RequestSpec:
    del state  # state-independent, like build_health_request
    params = _params.drop_none({
        "market_id": market_id, "prefix": prefix, "active": active, "entries": entries,
        "max_staleness_seconds": max_staleness_seconds, "with_data": with_data,
        "order": order, "limit": limit, "offset": offset,
    })
    return RequestSpec(method="GET", path="/marketdata", params=params or None,
                       idempotent=True, endpoint_name="market_data", authenticated=True)
```
- `build_latest_request` → `GET /marketdata/latest`, params `symbol, market_id, entries`.
- `build_latest_batch_request` → `POST /marketdata/latest`, `json_body=latest_request.to_dict()`,
  `idempotent=True` (a read expressed as POST — replay-safe, like `build_token_request` at `_core.py:141-176`
  which sets `idempotent=True` on a POST).

**Parser + `received_at` stamping (D-01)** — mirror `parse_health_response` (`_core.py:245-250`) body-consume-then-raise
order (`resp.read()` → `raise_for_response` → `resp.json()`), but stamp ONCE per response and thread
into every model + apply the 204/empty-collection guard (`iol`/`higyrus` convention: `if raw is None: return []`):
```python
def parse_market_data_response(resp: httpx.Response) -> list[MarketDataSnapshot]:
    resp.read()
    received_at = time.time()          # D-01: ONE stamp per response, BEFORE raise
    raise_for_response(resp)
    raw = resp.json()
    if raw is None:                    # collection convention
        return []
    return [MarketDataSnapshot.from_api(item, received_at=received_at) for item in raw]
```
`time` is already imported (`_core.py:44`). Add new names to `__all__` (`_core.py:61-70`). Import
`_params` and `models` at module top (both live in-package — no import-boundary violation; `_core`
stays IO-free).

---

### `market_data_client/client.py` (sync client) — D-08/D-06/D-10

**Analog for `with_options`:** `packages/iol-client/src/iol_client/client.py` — the Phase-13
shared-view-clone. Six pieces, all verified below:

**1. `__slots__`** (`iol client.py:128`) — add `_is_view` + `_max_retries` to the current `("_state",)`:
```python
__slots__ = ("_is_view", "_max_retries", "_state")
```

**2. `_validate_max_retries`** (`iol client.py:86-102`) — module-level, copy VERBATIM (duplicated
per-package by design):
```python
def _validate_max_retries(value: int) -> None:
    if isinstance(value, bool):
        raise ValueError(f"max_retries must be a non-negative int, got {value!r} (bool not accepted)")
    if not isinstance(value, int):
        raise ValueError(f"max_retries must be a non-negative int, got {value!r} (type={type(value).__name__})")
    if value < 0:
        raise ValueError(f"max_retries must be a non-negative int, got {value!r}")
```

**3. `__init__` kwarg** (`iol client.py:140,144,174-177`): add `max_retries: int = 2`, call
`_validate_max_retries(max_retries)` FIRST, then `self._max_retries = max_retries` and
`self._is_view = False`.

**4. `with_options`** (`iol client.py:264-329` — the core is lines 324-329):
```python
def with_options(self, *, max_retries: int) -> Self:
    _validate_max_retries(max_retries)
    view = type(self).__new__(type(self))
    view._state = self._state          # SHARE — no re-auth, no 2nd pool
    view._max_retries = max_retries    # OVERRIDE
    view._is_view = True               # FLAG for close() no-op
    return view
```

**5. View-aware `close()`** — prepend to the current `close()` (`market_data client.py:125-131`) the
guard from `iol client.py:202`: `if getattr(self, "_is_view", False): return`. A view must NOT tear
down the parent's shared transport.

**6. Thread the extension (THE LOAD-BEARING STEP, Pitfall 1)** — `iol client.py:465` and `:356`. The
current market-data shell sets `idempotent`/`request_id`/`endpoint_name` but NOT `max_attempts`
(`market_data client.py:250-252` and `:185-187`). Add to BOTH `_request` AND `_send_auth_request`:
```python
req.extensions["max_attempts"] = self._max_retries + 1
```
Transport already consumes it (`market_data_client/_transport.py:169`:
`effective_max_attempts = request.extensions.get("max_attempts", self._max_attempts)`) — **zero
transport changes**. Without this line `with_options` is a silent no-op → fails success criterion 3.
Also update `_ensure_http_client` (`market_data client.py:160-163`) to use `max_attempts=self._max_retries + 1`
instead of the module const `_DEFAULT_MAX_ATTEMPTS` (mirror `iol client.py:257-259`).

**D-09 header precedence (sync — ALREADY CORRECT, quote as the reference):** `market_data client.py:234-238`
sets `Authorization` AFTER spreading `spec.headers` → token wins. This is the CORRECT pattern the
async surface must be aligned to:
```python
headers = dict(spec.headers or {})
if spec.authenticated:
    self._ensure_token()
    assert self._state.token is not None
    headers["Authorization"] = f"Bearer {self._state.token}"   # set AFTER spread → WINS
```

**Public read methods** — mirror the health-method shape (`market_data client.py:277-287`):
`build spec → self._request(spec) → _core.parse_*_response(resp)`. Names: `get_market_data` /
`get_latest` / `get_latest_batch` (Claude's Discretion — "o nombres equivalentes"). Add matching
module-level shims delegating to `_get_default()` (mirror `market_data client.py:364-371`).

---

### `market_data_client/aio.py` (async client) — D-08/D-09/D-06/D-10

**Analog for `with_options`:** `packages/iol-client/src/iol_client/aio.py:302-310` — identical to sync.
The shared `asyncio.Lock`s already live on `_state` (`market_data_client/_state.py:96,99`
`token_lock`/`client_lock`), so a view inherits the SAME lock instances as the parent — this is
exactly the Phase-13 WR-01 fix iol already made. **No lock-hoisting work needed.**

Mirror all six `with_options` pieces on `AsyncClient` (slots, `__init__` kwarg + validate, `with_options`,
view-aware `aclose()` no-op via `if getattr(self, "_is_view", False): return` at the top of
`aclose()` `market_data aio.py:112-118`, and `extensions["max_attempts"]` in BOTH `_request`
`market_data aio.py:250-252` and `_send_auth_request` `market_data aio.py:180-182`). Reuse the same
`_validate_max_retries` (define it module-level in `aio.py` too — no cross-module import).

**D-09 FIX (WRONG today — Pitfall 3):** `market_data aio.py:236` currently lets `spec.headers` win:
```python
headers = {"Authorization": f"Bearer {token}", **(spec.headers or {})}   # spread AFTER → shadows token
```
Reorder so the token wins (align to sync):
```python
headers = {**(spec.headers or {}), "Authorization": f"Bearer {token}"}
```
The 401 re-auth carve-out already does `req.headers["Authorization"] = ...` directly
(`market_data aio.py:271`), so ONLY this initial dict-build line changes. (Note: `iol aio.py`'s
`_send_auth_request` uses `{"Authorization": ..., **(spec.headers or {})}` for the auth grant where
there is no spec `Authorization` — not a contradiction; the D-09 contract is specifically about the
authenticated ENDPOINT dispatch where a stray spec header must never shadow the fresh token.)

Add async public read methods mirroring `market_data aio.py:282-292` health shape, and async module
shims (`market_data aio.py:367-374`).

---

### `market_data_client/__init__.py` (barrel) — re-exports

**Analog:** the same file (`__init__.py:39-67`, Phase-20). Add to the `from market_data_client.client import (...)`
block the new sync methods; import the new models + `LatestRequest` from `market_data_client.models`;
add all public model classes + `LatestRequest` + new method names to `__all__` (keep alpha-sorted per
existing convention). The `aio` surface is importable as `from market_data_client import aio` but its
methods are NOT flattened (package convention — matches how `AsyncClient` is the only aio re-export).
Note the `# noqa: E402` on imports (they follow the mandatory `_logging_attach.attach()` call).

---

### `pyproject.toml` — ruff N815 per-file-ignore (D-04)

⚠ **Location correction (verified):** The market-data-client `pyproject.toml` has **NO** `[tool.ruff]`
section — ALL ruff config lives in the **ROOT** `/Users/admin/development/market-libs/pyproject.toml`.
The per-file-ignores block is at **root `pyproject.toml:72-73`**:
```toml
[tool.ruff.lint.per-file-ignores]
"**/tests/**" = ["S101"]  # asserts permitidos en tests
```
Add an entry here (NOT in the package pyproject):
```toml
"packages/market-data-client/src/market_data_client/models.py" = ["N815"]
```

⚠ **This is a no-op under the current config** (RESEARCH.md Open Question 1, confirmed): the ruff
`select` list (root `pyproject.toml:53-67`) does NOT include `N` (pep8-naming). `higyrus_client/models.py`
carries camelCase fields with NO N815 ignore and passes lint today. The existing `S101` ignore also
references an unselected code (`S`/bandit not in select) — so this defensive precedent already exists.
Add it per D-04 for forward-safety, but the planner/verifier must know its ABSENCE will NOT fail the
lint gate. If the plan prefers to honor CONTEXT.md's literal "MODIFY package pyproject.toml", note that
adding a `[tool.ruff]` override there is non-standard for this repo (all other packages defer to root) —
prefer the root file.

---

### `tests/` ★ (test, request-response) — D-10/D-11

**Analogs:** `market_data_client/tests/test_client.py` + `conftest.py` (in-package pytest-httpx +
singleton-isolation patterns). Mirror, don't reinvent — the autouse fixtures already handle isolation.

**Singleton isolation (already handled — rely on it, don't break it — Pitfall 4):** `conftest.py:29-73`
seeds dummy creds + `NEVER_EXPIRES` token (sync AND async autouse fixtures) and closes the transport
at teardown. New tests MUST rely on this. To exercise the grant / 401 re-auth path, force
`token_expires_at=0.0` explicitly via `configure(...)`.

**`_token_posts` count helper (assert by COUNT not ordering — Pitfall 5)** (`test_client.py:36-37`):
```python
def _token_posts(httpx_mock: HTTPXMock) -> list[object]:
    return [r for r in httpx_mock.get_requests() if str(r.url) == _TOKEN_URL and r.method == "POST"]
```

**Anonymous-vs-authenticated assertion shape** (`test_client.py:40-52`): `httpx_mock.add_response(...)`,
call the method, then inspect `httpx_mock.get_requests()` — assert `len`, `req.url.path`,
`"Authorization" in/not in req.headers`, and `_token_posts(...)`.

**Param-serialization tests (D-11):** inspect `requests[0].url.params` (httpx `QueryParams`) to assert
`drop_none` dropped optionals and booleans encoded as `"true"`/`"false"` (httpx-native). Cover every
`GET /marketdata` filter, `GET /marketdata/latest`, and the `LatestRequest` batch `json` body
(inspect `json.loads(requests[0].content)` or `requests[0].read()`).

**`from_api` tolerance + `received_at` (D-01/D-04)** in `test_models.py`: assert partial/None/extra-key
payloads never raise and produce typed zeros; assert `received_at` is the injected stamp (NOT `0.0`)
on a successful mock, stamped ONCE per response (all snapshots in one list share the value).

**`with_options` retry propagation (D-08)** in `test_with_options.py` (+ async variant): queue N+1
failing responses, assert the outgoing request COUNT matches `max_retries+1` — the canonical Pitfall-1
regression (a `max_retries=5` test that queues 6 failures must see 6 requests, not 3).

**D-10 401 sequences (extend `test_client.py` + `test_async_client.py`, both surfaces):** for
`401→re-auth→retry→succeed`, seed `token_expires_at` fresh (or `0.0`), queue a 401 then a 200, assert
exactly ONE token POST after the 401 + successful final result; for persistent-401, queue two 401s and
assert `pytest.raises(MarketDataAuthError)` with exactly one re-auth POST.

**D-09 async header precedence (extend `test_async_client.py`):** send an authenticated request with a
`spec.headers` carrying a decoy `Authorization`, assert the SENT `Authorization` equals the fresh token
(regression that sync and async agree).

## Shared Patterns

### Body-consume-then-raise (D-06)
**Source:** `_core.py:195-196,247-248` — `resp.read()` BEFORE `raise_for_response(resp)`.
**Apply to:** every new parser in `_core.py`; the parser captures `received_at = time.time()` between
`resp.read()` and `raise_for_response` (so the stamp reflects receipt, not post-validation).

### Error mapping
**Source:** `_core.raise_for_response` (`_core.py:110-122`) — 401/403 → `MarketDataAuthError`,
429 → `MarketDataRateLimitError`, other error → `MarketDataAPIError`.
**Apply to:** all new parsers (already reused — call `raise_for_response`, do not re-map). The sync/async
shells alias it as `_raise_for_response = _core.raise_for_response` (B8 identity invariant — do not
duplicate).

### `extensions["max_attempts"]` threading (D-08)
**Source:** `iol client.py:356,465` + `aio.py:336`; transport consumer `market_data_client/_transport.py:169`.
**Apply to:** BOTH `_request` and `_send_auth_request` in BOTH `client.py` and `aio.py`. Uniform
`req.extensions["max_attempts"] = self._max_retries + 1`. Load-bearing — the single point that makes
`with_options` real.

### View-aware teardown no-op (D-08)
**Source:** `iol client.py:202` (`close`), `iol aio.py` (`aclose`).
**Apply to:** `close()` (sync) and `aclose()` (async) — first line `if getattr(self, "_is_view", False): return`.

### Header precedence: token ALWAYS wins (D-09)
**Source:** sync `market_data client.py:234-238` (correct reference).
**Apply to:** async `aio.py:236` (fix), and the authenticated `_request` dispatch generally. A spec must
never carry its own `Authorization`; the fresh token always wins.

### Dual sync/async mirroring (CLAUDE.md constraint)
**Source:** whole-package convention — `client.py` ⇄ `aio.py`.
**Apply to:** every logic change (new methods, `with_options`, `max_attempts` threading) must land on
BOTH surfaces. A one-sided change fails the dual-surface success criterion.

## No Analog Found

None. Every file has a strong in-repo analog. The single genuine unknown is the **live wire contract**
(exact response JSON field names/nesting + `LatestRequest` body schema) — NOT a pattern gap but a data
gap: the OpenAPI at `https://market-data-develop.bbsa.com.ar/api/openapi.json` is not vendored (no local
`openapi.json`). This is by design (A1/A2): D-04 `from_api` tolerance bounds the blast radius and Phase-23
reconciles field names against real payloads. Model field names PROVISIONALLY (camelCase-verbatim).

## Metadata

**Analog search scope:** `packages/market-data-client/{src,tests}`, `packages/higyrus-client/src`,
`packages/iol-client/src`, root + package `pyproject.toml`.
**Files scanned:** `higyrus models.py`, `higyrus _params.py`, `market-data _core.py`, `market-data
client.py`, `market-data aio.py`, `market-data _state.py`, `market-data _transport.py`, `market-data
__init__.py`, `iol client.py` (§86-329,430-478), `iol aio.py` (§295-337), `market-data tests/{conftest.py,test_client.py}`,
root `pyproject.toml`, package `pyproject.toml`.
**Pattern extraction date:** 2026-07-29
