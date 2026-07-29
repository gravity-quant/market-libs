# Phase 21: Market data (lectura) + modelos - Research

**Researched:** 2026-07-29
**Domain:** In-repo extension of `market-data-client` — REST read surface, tolerant response models, per-call retry views
**Confidence:** HIGH (nearly all findings verified by reading the actual Phase-20 code + template packages; the one gap is the live wire contract, which is a Phase-23 target by design)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**`received_at` semantics**
- **D-01:** `received_at` is **client-stamped** — the wall-clock captured in `_core.py` at the moment the HTTP response is read, NOT a field parsed from the JSON payload. Injected into each `SafeModel` at parse time, i.e. `from_api(payload, received_at=...)`; the parser captures the timestamp ONCE per response and threads it into every constructed model.
- **D-02:** `received_at` is the caller's **local companion** to the server-side `max_staleness_seconds` filter — the client owns the stamp. Confirm/reconcile against real develop payloads in Phase 23. If the server also carries an event-time timestamp, that is additive to consider then — not a blocker now.

**Models (`models.py` — net-new)**
- **D-03:** Create `packages/market-data-client/src/market_data_client/models.py` carrying its **own copy** of higyrus's `SafeModel` base + `_coerce` helper (no-shared-internals — do NOT import from another package). Mirror `higyrus_client/models.py`.
- **D-04:** Snapshot model is `@dataclass(frozen=True, slots=True)` built via `from_api`, with a nested `entries` list model and the `received_at` field (D-01). Wire field names kept **camelCase verbatim**. Add the module to ruff's `N815` per-file-ignores. `from_api` tolerates partial/None/extra keys without raising.
- **D-05:** `LatestRequest` is a typed **request** dataclass (the one schema the OpenAPI does define), serialized to the `POST /marketdata/latest` `json_body`.

**Endpoint builders + param serialization (`_core.py`)**
- **D-06:** Add three pure builders to `_core.py`: `build_market_data_request`, `build_latest_request`, `build_latest_batch_request`, each returning `RequestSpec(authenticated=True, idempotent=True)`. `authenticated=True` triggers Bearer injection in `_request`; GET reads are idempotent → retry-eligible.
- **D-07:** GET filters passed as `params=` with `None`-valued optionals dropped via a new `drop_none` helper (new `_params.py`, mirroring `higyrus_client/_params.py`). Booleans (`active`, `with_data`) rely on httpx's native `True→"true"` param encoding for now — a Phase-23 verification target.

**`with_options` parity + folded Phase-20 debt**
- **D-08:** Add `with_options(max_retries=N)` to BOTH `Client` and `AsyncClient` via iol's Phase-13 **shared-view-clone** pattern: `_max_retries` + `_is_view` in `__slots__`, `max_retries` `__init__` kwarg with `_validate_max_retries`, shallow-clone `with_options` sharing `_state`, view-aware `close()`/`aclose()` no-ops, and thread `request.extensions["max_attempts"] = self._max_retries + 1` into `_request`/`_send_auth_request`. **Note:** current `market_data_client/client.py` builds requests WITHOUT any `max_attempts` extension — if that threading is skipped, `with_options` is a silent no-op (fails success criterion 3).
- **D-09:** **Fold in WR-04**: align async header precedence to sync so the **token/Authorization header WINS** over `spec.headers` in both surfaces.
- **D-10:** **Fold in the 401 test gap**: add permanent regression tests for the authenticated `401 → clear token → re-auth once → retry → succeed` path AND the persistent-401 re-raise path, for BOTH sync and async surfaces.

**Test strategy**
- **D-11:** Mocked tests via **pytest-httpx** cover: query-param serialization for every `GET /marketdata` filter + `GET /marketdata/latest`, `LatestRequest` batch body, `from_api` partial/None tolerance, `received_at` client-stamping, `with_options` retry propagation (sync+async), and the D-10 401 sequences. All four CI gates (ruff / format / mypy strict / pytest) green.

### Claude's Discretion
- Exact endpoint method names (`get_market_data` / `get_latest` / `get_latest_batch` are the roadmap's suggestion — "o nombres equivalentes"); pick names consistent with the existing package surface.
- Exact model class/field naming and the nested-entries shape — designed from the plan, with `from_api` tolerance absorbing shape corrections in Phase 23.
- Boolean/`entries` param wire-encoding (httpx-native `true`/`false` vs `1/0` vs repeated keys): default to httpx-native now; treat as an explicit Phase-23 live-verification target.

### Deferred Ideas (OUT OF SCOPE)
- Mutations (symbols/calendar writes), SSE streaming (`/marketdata/stream`), reference-data endpoints (instruments/segments/symbols/calendar → Phase 22), live verification (Phase 23). Read-only, no mutating-gate.
- **Server-provided / dual `received_at`** — only if Phase-23 live payloads reveal a server event-time timestamp.
- **Explicit boolean/`entries` param encoding** (`1/0`, repeated keys, comma-join) — only if Phase-23 live verification shows the server rejects httpx-native encoding.
- **`market-data-client-review-debt.md` IN-01..IN-04** (INFO-level) — tracked debt, not blocking MD-01.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MD-01 | Read market data — `GET /marketdata` (filters: market_id, prefix, active, entries, max_staleness_seconds, with_data, order, limit, offset), `GET /marketdata/latest` (symbol, market_id, entries), `POST /marketdata/latest` (batch via `LatestRequest`) — returned as `SafeModel` dataclasses with `received_at` first-class, with `with_options(max_retries=N)` parity sync + async | This research pins the exact `RequestSpec` shape and builder template (Architecture Patterns §1), the `SafeModel`/`_coerce`/`from_api` mechanics + `received_at` injection strategy (§2), the iol `with_options` shared-view-clone mechanics with the transport already honoring `extensions["max_attempts"]` (§3), the D-09 header-precedence fix quoted verbatim (§4), and the pytest-httpx patterns already used in the package for param + 401 testing (§5). |
</phase_requirements>

## Summary

Phase 21 is a **purely additive, in-repo extension** of the Phase-20 `market-data-client` foundation. There are **no new external dependencies** — every tool needed (`httpx`, `pytest-httpx`, `tenacity`, `python-dotenv`, `ruff`, `mypy`) is already installed and green. The whole phase is assembled from four copy-and-adapt templates that already exist in the repo: the Phase-20 `_core.py`/`client.py`/`aio.py` (integration surface), `higyrus_client/models.py` + `_params.py` (SafeModel + drop_none), and `iol_client/client.py`/`aio.py` (the `with_options` shared-view-clone). Because these are internal templates rather than third-party libraries, confidence is HIGH on everything except the exact live wire contract.

Three findings materially de-risk the plan. **First**, the Phase-20 `RetryTransport` already reads `request.extensions.get("max_attempts", self._max_attempts)` (`_transport.py:169`) — so the D-08 `with_options` work needs **zero transport changes**; it only needs the `Client`/`AsyncClient` shells to *set* that extension in `_request` and `_send_auth_request`, which they currently do not. **Second**, `RequestSpec` already carries every field the three new builders need (`params`, `json_body`, `idempotent`, `endpoint_name`, `authenticated`) — no dataclass surgery required. **Third**, the D-09 divergence is real and precisely located: sync sets `Authorization` *after* spreading `spec.headers` (token wins) while async does `{"Authorization": ..., **(spec.headers or {})}` (spec.headers wins) — the async fix is a one-line reorder.

The single genuine unknown is the **live wire contract** (exact response JSON shape and the `LatestRequest` body schema). The OpenAPI spec at `https://market-data-develop.bbsa.com.ar/api/openapi.json` is **not vendored in the repo** — no `openapi.json`/`swagger` file exists locally. The query-param *names* are authoritative (they come from CONTEXT.md/ROADMAP, which were transcribed from that spec), but the response body shape and `LatestRequest` fields are not pinned. This is by design: D-04's `from_api` tolerance gives a bounded blast radius, and Phase 23 reconciles against real payloads.

**Primary recommendation:** Copy the four in-repo templates verbatim, wire the three `RequestSpec(authenticated=True, idempotent=True)` builders, model the snapshot as a tolerant `SafeModel` with a `from_api(payload, *, received_at=...)` override that injects the client stamp without coercing it from the payload, mirror the iol `with_options` mechanics on both shells (setting `extensions["max_attempts"]` — the transport already consumes it), and fix the async header ordering to `{**(spec.headers or {}), "Authorization": f"Bearer {token}"}`. Treat all response-field names as provisional pending Phase 23.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Build request specs (params/body) for the 3 endpoints | `_core.py` (pure builders) | — | Established Phase-20 boundary: `_core` is IO-free; builders take state → `RequestSpec` |
| Serialize/drop optional query params | `_params.py` (net-new, pure) | `_core.py` builders | Mirrors higyrus `drop_none`; keeps builders declarative |
| HTTP dispatch + auth + Bearer injection | `client.py`/`aio.py` `_request` | `_transport.py` (retries) | Phase-20 owns the transport shell; `spec.authenticated` gates Bearer |
| Deserialize responses tolerantly | `models.py` (net-new `SafeModel`) | `_core.py` parsers | SafeModel owns the tolerant `from_api`; parser stamps `received_at` once and injects |
| Client-stamp `received_at` | `_core.py` parser (captures `time.time()` once) | `models.py.from_api` (receives it) | D-01: stamp captured at response-read time in `_core`, threaded into `from_api` |
| Per-call retry override (`with_options`) | `client.py`/`aio.py` (view clone) | `_transport.py` (already honors `extensions["max_attempts"]`) | iol Phase-13 pattern; transport plumbing already present |

## Standard Stack

### Core (all already installed — verified in `pyproject.toml` / `uv.lock`)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | >=0.27 | sync+async HTTP; native param encoding (`True→"true"`) | Sole transport across all 5 packages `[VERIFIED: pyproject.toml]` |
| tenacity | >=9.1,<10 | retry/backoff inside `RetryTransport` | Phase-20 CORE-MD-01 dep, already wired `[VERIFIED: packages/market-data-client/pyproject.toml]` |
| python-dotenv | >=1.0 | `load_dotenv()` at module import | Package convention `[VERIFIED: client.py:55]` |

### Supporting (test/tooling — already installed)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest-httpx | >=0.34 | mock HTTP for param-serialization + 401 tests | D-11 mocked tests `[VERIFIED: pyproject.toml:31]` |
| pytest-asyncio | >=0.24 | `asyncio_mode=auto` async tests | Async surface tests `[VERIFIED: pyproject.toml]` |
| ruff | >=0.7 | lint + format gate | CI gate 1+2 `[VERIFIED: pyproject.toml]` |
| mypy | >=1.13 (strict) | type gate | CI gate 3 `[VERIFIED: pyproject.toml]` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Copying `SafeModel` into `models.py` | Importing higyrus's `SafeModel` | **Forbidden** by the no-shared-internals constraint (D-03 / CLAUDE.md); each package is self-contained |
| httpx-native bool encoding | Explicit `1/0` / repeated-key encoding | Deferred to Phase 23 (D-07); mocked tests can't catch a server silently ignoring a mis-encoded filter |

**Installation:** None. No new packages. `uv sync --all-packages --all-extras --dev --frozen` already provides everything.

## Package Legitimacy Audit

> **Not applicable — this phase installs ZERO new external packages.** All dependencies (`httpx`, `tenacity`, `python-dotenv`, `pytest-httpx`, `pytest-asyncio`) are pre-existing, verified in the committed `uv.lock`, and unchanged by this phase.

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```text
  caller
    │  get_market_data(...) / get_latest(...) / get_latest_batch(...)
    │  (optionally via client.with_options(max_retries=N))
    ▼
┌─────────────────────────────────────────────────────────────┐
│ Client (client.py)  /  AsyncClient (aio.py)                  │
│  1. build spec ── _core.build_market_data_request(state, …)  │──▶ RequestSpec(authenticated=True,
│                    _core.build_latest_request(state, …)      │      idempotent=True, params=…/json_body=…)
│                    _core.build_latest_batch_request(state,…) │        │
│                          (params via _params.drop_none)      │        │
│  2. _request(spec):                                          │◀───────┘
│       ├─ spec.authenticated → _ensure_token() + Bearer       │
│       │     (D-09: token header WINS over spec.headers)      │
│       ├─ set req.extensions["max_attempts"]=_max_retries+1   │──▶ RetryTransport (already reads
│       ├─ req.extensions["idempotent"]=spec.idempotent        │      extensions["max_attempts"];
│       └─ http.send(req)                                      │      idempotent gate; full-jitter)
│            └─ on 401: clear token → re-auth once → retry     │        │
│  3. parse: _core.parse_*_response(resp)                      │◀───────┘
│       ├─ received_at = time.time()  (stamped ONCE, D-01)     │
│       └─ Model.from_api(payload, received_at=received_at)    │──▶ SafeModel (models.py)
└─────────────────────────────────────────────────────────────┘        tolerant _coerce; nested entries;
                                                                        received_at first-class
```

### Recommended Project Structure (net-new files marked ★)
```text
packages/market-data-client/src/market_data_client/
├── _core.py        # + build_market_data_request / build_latest_request / build_latest_batch_request
│                   #   + parse_market_data_response / parse_latest_response (+ received_at stamping)
├── _params.py  ★   # drop_none (mirror higyrus_client/_params.py)
├── models.py   ★   # SafeModel + _coerce (copy of higyrus) + snapshot/entries models + LatestRequest
├── client.py       # + _max_retries/_is_view slots, with_options, get_market_data/get_latest/get_latest_batch
│                   #   + thread extensions["max_attempts"]; D-09 already-correct (token wins)
├── aio.py          # async mirror of all the above + D-09 FIX (reorder header dict)
├── _state.py       # unchanged
├── exceptions.py   # unchanged
└── __init__.py     # + re-export models + LatestRequest + new methods
```

### Pattern 1: The `RequestSpec` builder (D-06) — exact current shape

`RequestSpec` (`_core.py:78-102`) is `@dataclass(frozen=True, slots=True)` with fields:
`method, path, params=None, headers=None, json_body=None, data=None, idempotent=False, endpoint_name="", authenticated=True`.

`build_health_request` is the template — market-data builders flip two flags:

```python
# Source: packages/market-data-client/src/market_data_client/_core.py (build_health_request template)
def build_market_data_request(state: _ClientState, *, market_id=None, prefix=None,
                              active=None, entries=None, max_staleness_seconds=None,
                              with_data=None, order=None, limit=None, offset=None) -> RequestSpec:
    del state  # state-independent (like health)
    params = _params.drop_none({
        "market_id": market_id, "prefix": prefix, "active": active,
        "entries": entries, "max_staleness_seconds": max_staleness_seconds,
        "with_data": with_data, "order": order, "limit": limit, "offset": offset,
    })
    return RequestSpec(
        method="GET", path="/marketdata", params=params or None,
        idempotent=True, endpoint_name="market_data", authenticated=True,   # vs health's False
    )
```

`build_latest_request` → `GET /marketdata/latest` (params: `symbol, market_id, entries`).
`build_latest_batch_request` → `POST /marketdata/latest` with `json_body=latest_request.to_dict()` (or dataclasses.asdict), `idempotent=True` (a read expressed as POST — retry-safe).

### Pattern 2: `SafeModel` + `_coerce` + `received_at` injection (D-01/D-03/D-04)

Copy `higyrus_client/models.py` `SafeModel`/`_coerce` **verbatim** (`models.py:30-89`). The base `from_api(cls, payload)` iterates `fields(cls)` and does `_coerce(data.get(field.name), hint)`. The `_coerce` logic already handles: `Optional[T]`→None-preserving, `list[X]`→`[]` + recurse, nested `SafeModel`→`X.from_api(value)`, and `str/bool/int/float`→typed zero (with the bool-is-subclass-of-int guard).

**`received_at` injection strategy (the trickiest D-01 detail):** `received_at` is NOT in the payload, so the base loop would coerce it to a zero-value. Override `from_api` on the snapshot model (or extend the base copy) to accept the stamp as a keyword and set it directly, skipping coercion:

```python
# Injection design — received_at is client-owned, not payload-derived (D-01/D-02)
@dataclass(frozen=True, slots=True)
class MarketDataSnapshot(SafeModel):
    # ... camelCase wire fields verbatim ...
    entries: list[MarketDataEntry]       # nested tolerant model
    received_at: float                    # client-stamped, first-class

    @classmethod
    def from_api(cls, payload: Any, *, received_at: float = 0.0) -> Self:
        data = payload if isinstance(payload, dict) else {}
        hints = get_type_hints(cls)
        kwargs = {}
        for field in fields(cls):
            if field.name == "received_at":
                kwargs[field.name] = received_at      # inject, do NOT coerce from payload
            else:
                kwargs[field.name] = _coerce(data.get(field.name), hints[field.name])
        return cls(**kwargs)
```

The parser in `_core.py` captures the stamp ONCE per response (right after `resp.read()`) and threads it into every top-level model built from that response:

```python
def parse_market_data_response(resp: httpx.Response) -> list[MarketDataSnapshot]:
    resp.read()
    received_at = time.time()          # D-01: ONE stamp per response
    raise_for_response(resp)
    raw = resp.json()
    if raw is None:                    # 204/empty guard (collection convention)
        return []
    return [MarketDataSnapshot.from_api(item, received_at=received_at) for item in raw]
```

Nested `entries` do NOT carry `received_at` (only the top-level snapshot does), so the base `_coerce` recursion for `list[MarketDataEntry]` needs no change.

### Pattern 3: `with_options` shared-view-clone (D-08) — exact iol mechanics

Verified from `iol_client/client.py` and `aio.py`. Six pieces, mirror all of them:

1. **`__slots__`** (`client.py:128`): `("_is_view", "_max_retries", "_state")` — add `_is_view` + `_max_retries` to the current `("_state",)`.
2. **`_validate_max_retries(value)`** (`client.py:86-102`): module-level; rejects `bool`, non-`int`, and `< 0` with `ValueError`. Copy verbatim (the "no shared internals" constraint means it is duplicated per-package by design).
3. **`__init__` kwarg** (`client.py:140,144,174`): add `max_retries: int = 2` (iol's default), call `_validate_max_retries(max_retries)` first, set `self._max_retries = max_retries` and `self._is_view = False`.
4. **`with_options`** (`client.py:264-329`): 
   ```python
   def with_options(self, *, max_retries: int) -> Self:
       _validate_max_retries(max_retries)
       view = type(self).__new__(type(self))
       view._state = self._state          # SHARE — no re-auth, no 2nd pool
       view._max_retries = max_retries    # OVERRIDE
       view._is_view = True               # FLAG for close()/__exit__ no-op
       return view
   ```
5. **View-aware `close()`/`aclose()`** (`client.py:202`): first line `if getattr(self, "_is_view", False): return` — a view must NOT tear down the parent's shared transport.
6. **Thread the extension** into BOTH `_request` and `_send_auth_request`: `req.extensions["max_attempts"] = self._max_retries + 1` (iol `client.py:356,465`). **This is the load-bearing step** — the current market-data shells set `idempotent`/`request_id`/`endpoint_name` but NOT `max_attempts`, so without this `with_options` is a silent no-op.

**Async note (`aio.py`):** identical, plus the shared locks already live on `_state` (`_state.py:96-99` has `token_lock` + `client_lock`), so a view inherits the SAME `asyncio.Lock` instances as the parent — this is exactly the Phase-13 WR-01 fix iol already made (`aio.py:302-310`). No lock-hoisting work needed; `_state` already holds both locks.

**Transport already consumes it** — no `_transport.py`/`_atransport.py` changes:
```python
# Source: packages/market-data-client/src/market_data_client/_transport.py:169
effective_max_attempts = request.extensions.get("max_attempts", self._max_attempts)
```

### Pattern 4: D-09 header-precedence fix (WR-04) — quoted verbatim

**Sync `client.py:234-238` (ALREADY CORRECT — token wins):**
```python
headers = dict(spec.headers or {})
if spec.authenticated:
    self._ensure_token()
    assert self._state.token is not None
    headers["Authorization"] = f"Bearer {self._state.token}"   # set AFTER spread → wins
```

**Async `aio.py:236` (WRONG — spec.headers wins):**
```python
headers = {"Authorization": f"Bearer {token}", **(spec.headers or {})}   # spread AFTER → shadows token
```

**Fix (align async so the token wins):**
```python
headers = {**(spec.headers or {}), "Authorization": f"Bearer {token}"}
```
The 401 re-auth carve-out in async already does `req.headers["Authorization"] = ...` directly (`aio.py:271`), so only the initial dict-build line changes.

### Anti-Patterns to Avoid
- **Importing `SafeModel`/`drop_none` from higyrus:** violates no-shared-internals (D-03). Copy them.
- **Adding `with_options` threading to only one shell:** the dual sync/async constraint (CLAUDE.md) requires both `client.py` and `aio.py`; a one-sided fix fails success criterion 3 on the async surface.
- **Coercing `received_at` from the payload:** it is client-owned (D-01). If it falls through the normal `_coerce` loop it becomes `0.0`.
- **Adding `max_attempts` to the transport constructor instead of the request extension:** the per-call override is a *request extension*, not a transport-level default.
- **Setting `Authorization` inside `spec.headers`:** don't — the header precedence contract (D-09) is that the fresh token always wins; a spec should never carry its own `Authorization`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Tolerant JSON→dataclass with partial/None/extra keys | A custom parser with per-field `.get()` + try/except | Copy higyrus `SafeModel.from_api` + `_coerce` | Already handles `Optional`, `list[X]` recursion, nested models, bool-vs-int subtlety, and never raises `[VERIFIED: higyrus models.py:37-89]` |
| Dropping `None` query params | Inline dict comprehension per builder | Copy higyrus `drop_none` | Preserves falsy-but-not-None (`False`, `0`, `""`) which are legitimate filter values `[VERIFIED: higyrus _params.py:53-59]` |
| Per-call retry override | New transport / config plumbing | iol `with_options` view + `extensions["max_attempts"]` | Transport already reads the extension; only the shell must set it `[VERIFIED: _transport.py:169]` |
| Bool→`"true"`/`"false"` query encoding | Manual string conversion | httpx native param encoding | D-07 default; explicit encoding deferred to Phase 23 |
| max_retries validation | Ad-hoc `if` in `__init__` | Copy iol `_validate_max_retries` | Rejects `bool`/`float`/negative early with a clean `ValueError` `[VERIFIED: iol client.py:86-102]` |

**Key insight:** Phase 21 is ~90% mechanical template application. The Phase-20 foundation and the two donor packages (higyrus, iol) already solved every non-trivial sub-problem; the risk is in *fidelity of copying* (esp. the `received_at` injection and the async header reorder), not in novel design.

## Common Pitfalls

### Pitfall 1: `with_options` silent no-op
**What goes wrong:** `with_options(max_retries=N)` returns a view but retries never change.
**Why it happens:** The current market-data shells (`client.py:243-252`, `aio.py:243-252`) build requests WITHOUT `req.extensions["max_attempts"]`. The transport falls back to its constructor default (`_DEFAULT_MAX_ATTEMPTS=3`), ignoring the view.
**How to avoid:** Set `req.extensions["max_attempts"] = self._max_retries + 1` in BOTH `_request` and `_send_auth_request`, on both shells.
**Warning signs:** A `with_options(max_retries=5)` test that mocks 6 failing responses still only sees 3 requests.

### Pitfall 2: `received_at` collapses to `0.0`
**What goes wrong:** Every snapshot has `received_at == 0.0`.
**Why it happens:** The field went through the normal `_coerce` loop (`data.get("received_at")` → None → `float` default `0.0`) instead of being injected.
**How to avoid:** Override `from_api` to set `received_at` from the kwarg and skip its `_coerce` (Pattern 2). Stamp ONCE per response in the parser.
**Warning signs:** `snapshot.received_at == 0.0` in a test where the response mock succeeded.

### Pitfall 3: Async header precedence left divergent (D-09)
**What goes wrong:** A future `spec.headers` with an `Authorization` key silently shadows the fresh token on async only.
**Why it happens:** `{"Authorization": ..., **(spec.headers or {})}` lets the spread win.
**How to avoid:** Reorder to `{**(spec.headers or {}), "Authorization": f"Bearer {token}"}`. Add a regression test asserting the sent `Authorization` equals the token even when a spec header is present.
**Warning signs:** Sync and async tests for header precedence disagree.

### Pitfall 4: Singleton cross-test contamination (already handled — don't break it)
**What goes wrong:** A test sees a stale `httpx.Client` that pytest-httpx can't intercept.
**Why it happens:** module-level default `Client`/`AsyncClient` persists across tests.
**How to avoid:** The `conftest.py` autouse fixtures already seed dummy creds + a `NEVER_EXPIRES` token and close the transport at teardown (`conftest.py:29-73`). New tests must rely on this, not construct their own un-torn-down default. Force `token_expires_at=0.0` explicitly when testing the grant/401 re-auth path.
**Warning signs:** Tests pass in isolation but fail in suite order.

### Pitfall 5: 401 re-auth assertions by ordering instead of count
**What goes wrong:** Flaky 401-sequence tests.
**Why it happens:** Concurrency/retry can reorder requests.
**How to avoid:** Assert by COUNT of token POSTs (`_token_posts` helper pattern, `test_client.py:36-37`) — e.g. "exactly one token POST after the 401", not "request[2] is the grant".

## Code Examples

### Existing pytest-httpx param/401 pattern to mirror (D-10/D-11)
```python
# Source: packages/market-data-client/tests/test_client.py:36-52
def _token_posts(httpx_mock: HTTPXMock) -> list[object]:
    return [r for r in httpx_mock.get_requests()
            if str(r.url) == _TOKEN_URL and r.method == "POST"]

def test_get_health_anonymous(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url=f"{_BASE}/health", method="GET", json={"status": "ok"})
    assert market_data_client.get_health() == {"status": "ok"}
    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    assert "Authorization" not in requests[0].headers   # anonymous carve-out
    assert _token_posts(httpx_mock) == []
```
For param-serialization tests, inspect `requests[0].url.params` (httpx `QueryParams`) to assert `drop_none` dropped optionals and booleans encoded as `"true"`/`"false"`. For the authenticated-401 D-10 test, seed `token_expires_at` fresh (conftest default) or `0.0`, queue a 401 then a 200 with `httpx_mock.add_response(...)` twice, and assert exactly one token POST + a successful final result; for persistent-401, queue two 401s and assert `pytest.raises(MarketDataAuthError)` with exactly one re-auth POST.

### 204/empty collection guard (mirror the established convention)
```python
# Collections return [] on a null/empty body (higyrus/iol convention)
raw = resp.json()
if raw is None:
    return []
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Module-level function API (iol/higyrus original) | Class-based `Client`/`AsyncClient` + default-singleton shims | Phase 20 (market-data-client) | New methods go on the class; module shims delegate to `_get_default()` |
| Per-call retry not overridable | `with_options(max_retries=N)` shared-view clone | iol Phase 13 → market-data Phase 21 | Transport already reads `extensions["max_attempts"]` |

**Deprecated/outdated:** none relevant. The `market-data-client` is Alpha (v0.1.0) and this is its second feature phase.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The exact response JSON shape (field names/nesting for the snapshot + `entries`) is not pinned; modeled provisionally with camelCase-verbatim fields | Patterns §2, MD-01 | LOW — D-04 `from_api` tolerance absorbs shape corrections; Phase 23 reconciles against live payloads |
| A2 | The `LatestRequest` body schema (field names/types) is not vendored in the repo (no local `openapi.json`) | Patterns §1 (D-05) | MEDIUM — the batch POST body may be rejected by the server if field names are wrong; verified live in Phase 23. Mocked tests only assert the client serializes what it was given |
| A3 | httpx-native `True→"true"` bool encoding is what the server expects for `active`/`with_data` | Standard Stack, D-07 | LOW/MEDIUM — explicitly a Phase-23 verification target; server could silently ignore a mis-encoded filter |
| A4 | Query-param names (`market_id, prefix, active, entries, max_staleness_seconds, with_data, order, limit, offset`; `symbol, market_id, entries`) are authoritative | Patterns §1 | LOW — transcribed from the OpenAPI into CONTEXT.md/ROADMAP/REQUIREMENTS, three concordant sources |
| A5 | Adding `models.py` to a ruff `N815` per-file-ignore (D-04) is harmless but **not strictly required** — see Open Question 1 | Open Questions | LOW — cosmetic config only |

## Open Questions

1. **Is the D-04 `N815` per-file-ignore actually needed?**
   - What we know: The ruff `select` list (`pyproject.toml:53-67`) does **NOT** include `N` (pep8-naming). So camelCase wire fields do not trigger `N815` today — higyrus's `models.py` carries camelCase fields with **no** N815 ignore and passes lint. The existing `"**/tests/**" = ["S101"]` ignore also references an *unselected* rule (`S`/bandit is not in select), so the repo already tolerates defensive ignores for unselected codes.
   - What's unclear: Whether the plan should add the ignore anyway (as D-04 instructs) for forward-safety if `N` is ever enabled, or skip it as dead config.
   - Recommendation: Add the per-file-ignore entry `"packages/market-data-client/src/market_data_client/models.py" = ["N815"]` per D-04 (it is harmless and matches the existing S101 defensive precedent), but the planner/verifier should know it is a **no-op under the current select set** — its absence will NOT fail the lint gate.

2. **How is `market-data-client` wired into the mypy + pytest CI gates?**
   - What we know: The root `pyproject.toml` mypy `files` list (`pyproject.toml:96`) covers the OTHER five packages' `src` but **omits `packages/market-data-client/src`**. The CI test matrix (`ci.yml`) uses a **hardcoded** `matrix.package` list, and the v1.4 plan (`.future_plans/market_data.md` Fase 5 / Phase 24) explicitly defers "agregar `market-data-client` a `matrix.package` en `ci.yml`" to the release phase.
   - What's unclear: Whether the D-11 "mypy strict green" gate is currently enforced in CI for this package, or only runnable locally.
   - Recommendation: The plan must run the four gates **explicitly against the package** locally/in-plan (e.g. `uv run mypy packages/market-data-client/src`, `uv run pytest packages/market-data-client`) rather than assuming the global `mypy`/CI invocation covers it. Do NOT add market-data-client to the global mypy `files` or CI matrix here — that is Phase-24 (PUB-MD-01) scope. Flag this to the verifier so "green gates" is measured with the right command.

3. **`LatestRequest` batch body — dict vs dataclass serialization.**
   - What we know: D-05 makes it a typed request dataclass serialized to `json_body`.
   - What's unclear: exact field names (A2). 
   - Recommendation: Model it as a small frozen dataclass with an explicit `to_dict()` (or `dataclasses.asdict`) so Phase 23 can adjust field names in one place; keep `json_body` construction in the `_core.py` builder.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | all | ✓ | 3.12.11 (CI also 3.13) | — |
| uv | workspace | ✓ | 0.9.0 | — |
| httpx | transport | ✓ | >=0.27 (installed) | — |
| tenacity | retries | ✓ | >=9.1,<10 (installed) | — |
| pytest-httpx | tests | ✓ | >=0.34 (installed) | — |
| Live develop API + Auth0 creds | — | N/A | — | **Not needed this phase** — all tests mocked (D-11); live verification is Phase 23 |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none — the phase is fully exercisable with mocked HTTP.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >=8.3 + pytest-asyncio (`asyncio_mode=auto`) + pytest-httpx >=0.34 |
| Config file | root `pyproject.toml` (`[tool.pytest.ini_options]`, `--import-mode=importlib`, `--strict-markers`) |
| Quick run command | `uv run pytest packages/market-data-client -x` |
| Full suite command | `uv run pytest packages/market-data-client --cov=packages/market-data-client/src` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MD-01 | `GET /marketdata` serializes every filter; `drop_none` drops optionals; bools→`"true"`/`"false"` | unit (pytest-httpx, inspect `req.url.params`) | `uv run pytest packages/market-data-client/tests/test_market_data.py -x` | ❌ Wave 0 |
| MD-01 | `GET /marketdata/latest` serializes `symbol,market_id,entries` | unit | same file | ❌ Wave 0 |
| MD-01 | `POST /marketdata/latest` sends `LatestRequest` json body | unit | same file | ❌ Wave 0 |
| MD-01 | `from_api` tolerates partial/None/extra keys without raising | unit | `test_models.py` | ❌ Wave 0 |
| MD-01 | `received_at` client-stamped, first-class, ONE stamp/response | unit | `test_models.py` | ❌ Wave 0 |
| MD-01 | `with_options(max_retries=N)` propagates (sync+async) — assert request count under repeated failures | unit | `test_with_options.py` + async variant | ❌ Wave 0 |
| MD-01/D-10 | authenticated `401→re-auth once→retry→succeed` + persistent-401 re-raise (sync+async) | unit | extend `test_client.py` / `test_async_client.py` | ⚠️ files exist, cases missing |
| MD-01/D-09 | async `Authorization` header wins over `spec.headers` | unit | extend `test_async_client.py` | ⚠️ file exists, case missing |

### Sampling Rate
- **Per task commit:** `uv run pytest packages/market-data-client -x`
- **Per wave merge:** `uv run pytest packages/market-data-client --cov=packages/market-data-client/src` + `uv run ruff check packages/market-data-client && uv run ruff format --check packages/market-data-client` + `uv run mypy packages/market-data-client/src`
- **Phase gate:** all four gates green before `/gsd-verify-work` (run mypy/pytest **explicitly against the package path** — see Open Question 2)

### Wave 0 Gaps
- [ ] `tests/test_market_data.py` — param serialization for all three endpoints (MD-01, D-07, D-11)
- [ ] `tests/test_models.py` — `SafeModel` tolerance + `received_at` stamping (MD-01, D-01/D-04)
- [ ] `tests/test_with_options.py` (+ async) — retry propagation by request count (MD-01, D-08)
- [ ] Extend `tests/test_client.py` + `tests/test_async_client.py` — D-10 401 sequences (both surfaces) + D-09 header precedence
- Framework install: none — `pytest-httpx` already present; `conftest.py` autouse fixtures already handle singleton isolation.

## Security Domain

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes (indirect) | Auth0 client_credentials Bearer already implemented in Phase 20; this phase only *consumes* `_ensure_token`. D-09 fix hardens header precedence so a stray spec header can never shadow the fresh token |
| V3 Session Management | no | Stateless bearer; TTL cache owned by Phase 20 |
| V4 Access Control | no | Read-only surface; no mutating-gate (out of scope) |
| V5 Input Validation | yes | `_validate_max_retries` rejects bad `max_retries`; query params are client-owned typed kwargs funneled through `drop_none`; httpx encodes params (no injection surface) |
| V6 Cryptography | no | No crypto in this phase (JWT signature validation is explicitly deferred, SEC-MD-02) |
| V7 Error Handling & Logging | yes | `RedactingFilter` (Phase 20) must keep Bearer/secret out of logs; new endpoints add no new log sites that surface credentials — verify no param/response logging leaks a token |

### Known Threat Patterns for market-data-client
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Stale/shadowed Bearer on async (spec header wins over token) | Spoofing/Elevation | D-09 fix: token header ALWAYS wins (`{**spec.headers, "Authorization": ...}`) |
| Credential leak in logs (Bearer/secret in a new endpoint log record) | Information Disclosure | Existing `RedactingFilter`; add no raw-header/token log statements; `__repr__` already redacts |
| Retry amplification (DoS via unbounded retries) | Denial of Service | `max_retries` validated `>= 0`; `max_attempts = N+1` bounded; `idempotent`-gated so only GETs/replay-safe POSTs retry |
| Auth server hammering on repeated 401 | Denial of Service | Exactly-once re-auth carve-out (Phase 20, verified); async double-checked under token lock |

## Sources

### Primary (HIGH confidence — read directly this session)
- `packages/market-data-client/src/market_data_client/_core.py` — `RequestSpec` shape, builder/parser templates, `raise_for_response`, `token_is_fresh`
- `packages/market-data-client/src/market_data_client/client.py` + `aio.py` — `_request`/`_send_auth_request`/`_ensure_token`/health; D-09 divergence (sync `client.py:234-238` vs async `aio.py:236`)
- `packages/market-data-client/src/market_data_client/_transport.py:169` — transport already reads `extensions["max_attempts"]`
- `packages/market-data-client/src/market_data_client/_state.py` — `_ClientState` (locks already on `_state`)
- `packages/higyrus-client/src/higyrus_client/models.py:30-89` — `SafeModel`/`_coerce`/`from_api`
- `packages/higyrus-client/src/higyrus_client/_params.py:53-59` — `drop_none`
- `packages/iol-client/src/iol_client/client.py:86-102,128,264-329,356` + `aio.py:302-336` — `with_options` shared-view-clone mechanics
- `packages/market-data-client/tests/{conftest.py,test_client.py}` — pytest-httpx + singleton-isolation patterns
- `pyproject.toml` — ruff select (no `N`), mypy `files` (omits market-data-client), gates
- `.future_plans/market_data.md`, `.planning/{REQUIREMENTS,ROADMAP}.md` — D-locks, MD-01, param names

### Secondary (MEDIUM confidence)
- `.planning/todos/pending/market-data-client-review-debt.md` — WR-04 (D-09) + 401 test gap (D-10) provenance

### Tertiary (LOW confidence)
- Live OpenAPI at `https://market-data-develop.bbsa.com.ar/api/openapi.json` — referenced by the milestone plan but **not vendored** in the repo; response shapes + `LatestRequest` fields unverified this session (A1/A2, Phase-23 reconciliation)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new deps; all verified in committed `uv.lock`/`pyproject.toml`
- Architecture / integration shapes: HIGH — `RequestSpec`, transport extension handling, `with_options` mechanics, and the D-09 divergence all read directly from source
- `received_at` injection design: HIGH — derived from the verified higyrus `from_api`/`_coerce` internals
- Wire contract (response shape + `LatestRequest` body): LOW — OpenAPI not in repo; provisional, Phase-23 target (bounded by D-04 tolerance)
- Pitfalls / test patterns: HIGH — mirrored from committed tests + verified transport behavior

**Research date:** 2026-07-29
**Valid until:** 2026-08-28 (stable — in-repo templates; only the live wire contract is volatile and is a Phase-23 concern)
