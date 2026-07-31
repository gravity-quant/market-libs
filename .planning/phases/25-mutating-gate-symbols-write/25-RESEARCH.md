# Phase 25: Mutating-gate + Symbols write - Research

**Researched:** 2026-07-31
**Domain:** Python HTTP client extension — safety-gated write surface (`market-data-client` v0.2.0), dual sync/async, mypy-strict
**Confidence:** HIGH (all findings grounded in the existing package source, verified this session)

## Summary

Phase 25 extends the existing `market-data-client` package (read-only, v0.2.0) with its first **mutation surface** — three `/symbols` write endpoints — behind a load-bearing safety gate. The research confirms that the CONTEXT.md locked decisions (D-01…D-16) are directly executable against the current source with **zero structural changes to the transport or `RequestSpec`**: the `RequestSpec` dataclass already carries `method: str` and `json_body: dict[str, Any] | None`, both `_request` dispatchers already thread `json=spec.json_body` into `http.build_request`, and `build_latest_batch_request` is a working POST-with-JSON-body builder that the three new symbols builders mirror exactly. The transport-level mutation gate (`request.extensions["idempotent"]`) is already in place and honored by `RetryTransport.handle_request`.

The new work is additive and follows patterns already proven in the same package: three pure builders in `_core.py`, three frozen request-model dataclasses with hand-written `to_dict()` (mirroring `LatestRequest`), a new `MarketDataMutationNotAllowedError` exception subclass, two new `_ClientState` fields (`mutating_allowed`, `expected_host`), and a `_ensure_mutation_allowed()` helper on each shell called at the top of every mutation method — before spec-build, before `_ensure_token`, before any transport touch. Because the flag lives on the shared `_ClientState` and `with_options` views share `self._state`, the gate propagates to views for free.

**The single most important research finding that contradicts CONTEXT.md:** the cross-package `verification/test_public_surface.py` and `verification/test_sync_async_isolation.py` tests **do NOT cover `market_data_client`** — their `_PACKAGES` lists contain only ambito/iol/higyrus/matriz, and there is no `market-data-client-surface.txt` snapshot. D-16's claim that "existing `verification/test_public_surface.py` and `test_sync_async_isolation.py` enforce this parity — a missing entry fails the gates" is **false for this package**. The plan must add explicit in-package tests for export/parity of the new surface; it cannot rely on those cross-package guards catching a missing `__all__` entry.

**Primary recommendation:** Implement per CONTEXT.md D-01…D-16 verbatim, mirroring `build_latest_batch_request` (builder), `LatestRequest.to_dict()` (request model), `_validate_max_retries` (batch `ValueError`), and the `verification/mutation_gate.py` exact-hostname discipline (host gate). Add explicit in-package tests for the gate (zero HTTP + zero Auth0 on refusal), body serialization, status parsing, no-retry, and sync/async export parity — because the cross-package parity nets do not include this package.

## User Constraints (from CONTEXT.md)

### Locked Decisions

**A. Env/host gate mechanics**
- **D-01:** Add opt-in `expected_host: str | None` to `_ClientState` alongside `mutating_allowed`. Host gate compares `urllib.parse.urlsplit(self._state.base_url).hostname` by **EXACT match** (never substring, never `.endswith`) against the expected host.
- **D-02:** `expected_host` defaults to the hostname of `DEFAULT_BASE_URL` (`market-data-develop.bbsa.com.ar`). A consumer that reconfigures `base_url` to a legit alternate develop host must also set `expected_host` to match, or the gate refuses.
- **D-03:** The `require_env` / `VERIFY_MUTATING` env opt-in (from `verification/env_gate.py`) stays in the **Phase-27 verification harness**, NOT inside the client. The client's second gate is purely the host check.

**B. Gate check location**
- **D-04:** A private `_ensure_mutation_allowed()` helper on each shell. Every public mutation method calls it FIRST — before building the spec, before any token fetch, before any transport touch.
- **D-05:** On refusal (`mutating_allowed is False` OR host check fails) it raises `MarketDataMutationNotAllowedError` and **guarantees zero HTTP request AND zero Auth0 round-trip**. The check does NOT live in `_core` (must stay IO-free / state-agnostic) nor in `_request` (shared by the read surface).

**C. RequestSpec extension for write**
- **D-06:** `RequestSpec` needs **no structural change** — already carries `method: str` and `json_body: dict[str, Any] | None`; `_request` already threads `json=spec.json_body`. `build_latest_batch_request` is the working POST-with-JSON-body precedent.
- **D-07:** Add three pure builders to `_core.py`: `build_create_symbol_request`, `build_create_symbols_request`, `build_update_symbol_request` — returning `RequestSpec(method="POST"|"PATCH", path=..., json_body=..., authenticated=True, idempotent=True, endpoint_name=...)`. Per DM-03 all three symbols endpoints are `idempotent=True`.
- **D-08:** `PATCH /symbols/{symbol_id}` interpolates the id into the path. Account for `symbol_id` values that may contain `/` (spec example `"DLR/DIC26"`) — treat path-encoding as an explicit assumption to confirm live in Phase 27.

**D. Request-model serialization**
- **D-09:** Model `NewSymbol`, `NewSymbols`, `SymbolPatch` as frozen `@dataclass(frozen=True, slots=True)` in `models.py` — **NOT** `SafeModel` subclasses. Each has a hand-written `to_dict()` mirroring `LatestRequest.to_dict()`.
- **D-10:** `NewSymbol` sends `symbol` always and `market_id` always (defaulted, non-nullable, default `"ROFX"` — sent explicitly, not dropped). `NewSymbols.to_dict()` → `{"symbols": [s.to_dict() for s in self.symbols]}`. `SymbolPatch.to_dict()` → `{"active": self.active}`. `_params.drop_none` applies only to genuinely-optional `None` fields (none in current symbols models).

**E. Batch validation (1–500)**
- **D-11:** Enforce the `NewSymbols` 1–500 length constraint **client-side**, raising a plain **`ValueError`** (NOT a typed `MarketData*` error) before any spec build or HTTP dispatch. Placement: `NewSymbols.__post_init__`. Mirrors `_validate_max_retries`.
- **D-12:** Server-side `422` remains a separate concern surfaced as the existing typed API error via `raise_for_response` (`_core.py` status mapping) — unchanged.

**F. Typing + view propagation**
- **D-13:** Add `mutating_allowed: bool = False` (refuse-by-default) and `expected_host: str | None = None` to `_ClientState` as plainly-typed fields. Add matching keyword-only params to `Client.__init__` / `AsyncClient.__init__` and to `configure()` (both surfaces), following the existing `if x is not None:` carry-forward pattern.
- **D-14:** Because these fields live on the SHARED `_ClientState` and `with_options` clones share `self._state`, the mutation flag + host gate **propagate to views automatically** with zero extra code. Do NOT store `mutating_allowed` on the instance `__slots__` (would break view inheritance).

**G. Sync/async parity + public surface**
- **D-15:** Mirror EVERY symbols method, the `_ensure_mutation_allowed` helper, the new constructor + `configure()` params, and module-level shims across `client.py` AND `aio.py` identically. Module-level sync shims delegate to `_get_default()` exactly like `get_symbols`; async shims stay under `aio`.
- **D-16:** Add `MarketDataMutationNotAllowedError` to `exceptions.py` `__all__` (see note below — `exceptions.py` currently has no `__all__`), the three request models to `models.py` `__all__`, and re-export all through `__init__.py` `__all__`.

### Claude's Discretion
- Exact builder/method naming beyond the DM-locked public names (`create_symbol`, `create_symbols`, `update_symbol`); internal helper names; test file organization; whether the host-gate comparison is a small module-level pure function reused by both shells (a reasonable dedup consistent with the sync/async duplication constraint).

### Deferred Ideas (OUT OF SCOPE — confirm live in Phase 27, do NOT research/resolve here)
- Exact `201` / `200` / `422` response shapes for the three symbols endpoints (single `Symbol` vs `list[Symbol]` vs `{items:[...]}` envelope; whether `422` body carries structured detail). Parsers stay tolerant (`from_api`).
- Real server-side idempotency of `POST /symbols` and `POST /symbols/batch` — DM-03 locks `idempotent=True`; flips to `False` in Phase 27 if a retried POST duplicates state.
- PATCH path encoding for `symbol_id` values containing `/` (e.g. `"DLR/DIC26"`) — URL-safe surrogate vs raw symbol needing percent-encoding (D-08).
- Out of milestone scope (backlog v2): SSE streaming, Auth0 token disk cache (SEC-MD-01), JWT signature validation (SEC-MD-02) — per DM-08.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| GATE-MD-01 | Mutating-gate: opt-in `mutating_allowed` (`__init__` + `configure()`), second host/env gate, no-retry of non-idempotent ops, new `MarketDataMutationNotAllowedError ⊂ MarketDataError`, dual sync/async | Gate slot + carry-forward pattern verified in `_ClientState` / `Client.__init__` / `configure()`; transport `idempotent` gate already live in `_transport.py`/`_atransport.py`; `verification/mutation_gate.py` exact-hostname discipline available to mirror; exception hierarchy in `exceptions.py` ready to extend |
| MUT-MD-01 | Symbols write: `POST /symbols` (`NewSymbol`), `POST /symbols/batch` (`NewSymbols`, 1–500), `PATCH /symbols/{symbol_id}` (`SymbolPatch`); typed request-models → JSON, tolerant `SafeModel` responses, `422`→typed error, sync+async, behind gate | `build_latest_batch_request` = POST-with-JSON-body builder template; `LatestRequest.to_dict()` = request-model template; `parse_symbols_response` = tolerant `Symbol.from_api` parser template; `_validate_max_retries` = batch `ValueError` template; wire-body test `test_get_latest_batch_sends_bearer_and_body` = serialization-test template |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Refuse-by-default mutation gate (flag + host check) | Stateful shell (`client.py` / `aio.py`) | `_ClientState` (flag storage) | D-05: policy check needs live state (`mutating_allowed`, `base_url`); `_core` is IO-free/state-agnostic and `_request` is shared with reads |
| Non-idempotent no-retry enforcement | Transport (`_transport.py` / `_atransport.py`) | Builder (`_core.py` sets `idempotent`) | Gate is `request.extensions["idempotent"]`, already honored by `RetryTransport.handle_request` — never method-based |
| Request spec construction | Pure builders (`_core.py`) | — | Builders are pure `state → RequestSpec`; symbols builders `del state` (payload comes from typed models) |
| Request-body serialization (model → JSON) | Request models (`models.py`, `to_dict()`) | `_params.drop_none` | Frozen dataclasses serialize OUT; distinct from `SafeModel` (deserialize IN) |
| Batch 1–500 validation | Request model (`NewSymbols.__post_init__`) | — | Client-side `ValueError` before any dispatch; independent of entry point |
| Response parsing (tolerant) | Pure parsers (`_core.py`) | `SafeModel.from_api` (`models.py`) | Existing `parse_symbols_response` pattern; shape deferred to Phase 27, tolerance bounds blast radius |
| Error mapping (401/403/429/4xx→typed) | Pure helper (`_core.raise_for_response`) | — | Unchanged; `422`→`MarketDataAPIError` already covered by `if resp.is_error` |
| Public export parity | `__init__.py` / `models.py` / `exceptions.py` `__all__` | In-package tests (NEW) | Cross-package parity nets do NOT cover this package (see finding) |

## Standard Stack

No new external dependencies. The phase is a pure additive extension of the existing package using only stdlib + the already-vendored stack.

### Core (already present — reuse, do not add)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `httpx` | >=0.27 | sync + async HTTP transport | Sole transport for all packages; `build_request(..., json=...)` already used for POST bodies [VERIFIED: source `client.py:316-322`] |
| `python-dotenv` | >=1.0 | `.env` credential loading at import | `load_dotenv()` at module level in `client.py`/`aio.py` [VERIFIED: source] |
| `tenacity` | (vendored via `_transport`) | bounded retry + full-jitter backoff | Drives `RetryTransport`; mutation gate short-circuits it via `idempotent` extension [VERIFIED: source `_transport.py:159`] |
| `urllib.parse.urlsplit` | stdlib | exact-hostname host gate | Same primitive `verification/mutation_gate.py` uses for its exact-host check [VERIFIED: source] |

**Installation:** None. `uv sync --all-packages --all-extras --dev --frozen` already provides everything.

**Version verification:** Not applicable — no packages added. No Package Legitimacy Audit required (no external install).

## Architecture Patterns

### System Architecture Diagram

```
  Consumer code
      │  create_symbol(NewSymbol(...))  /  create_symbols(NewSymbols([...]))  /  update_symbol(id, SymbolPatch(...))
      ▼
  ┌─────────────────────────── Stateful shell (client.py / aio.py) ───────────────────────────┐
  │                                                                                            │
  │   [1] _ensure_mutation_allowed()  ◄── FIRST, before anything                               │
  │         ├─ mutating_allowed is False?  ──────────────► raise MarketDataMutationNotAllowedError
  │         └─ urlsplit(base_url).hostname != expected_host? ─► raise MarketDataMutationNotAllowedError
  │              (D-05: NO http build, NO _ensure_token, NO Auth0 round-trip)                  │
  │                                                                                            │
  │   [2] (NewSymbols only) __post_init__ already raised ValueError if len ∉ [1,500]  (D-11)   │
  │                                                                                            │
  │   [3] spec = _core.build_create_symbol_request(state, model.to_dict())   ── pure builder   │
  │              RequestSpec(method="POST"/"PATCH", path, json_body, authenticated=True,       │
  │                         idempotent=True, endpoint_name)                                    │
  │                                                                                            │
  │   [4] resp = self._request(spec)   ── shared read+write dispatch                           │
  │         ├─ authenticated → _ensure_token() → inject Authorization: Bearer                  │
  │         ├─ build_request(method, base_url+path, json=spec.json_body, headers)              │
  │         ├─ req.extensions["idempotent"] = spec.idempotent  (True → retry-eligible)         │
  │         └─ http.send(req) ──────► RetryTransport (idempotent gate; 422 not retryable)      │
  │                                                                                            │
  │   [5] return _core.parse_symbols_response(resp) / parse_symbol_response(resp)  ── tolerant  │
  │         raise_for_response maps 401/403→Auth, 429→RateLimit, 422/4xx→APIError (D-12)        │
  └────────────────────────────────────────────────────────────────────────────────────────────┘
```

File-to-responsibility mapping is in the Architectural Responsibility Map above.

### Recommended Project Structure (files touched — all existing)
```
packages/market-data-client/src/market_data_client/
├── _core.py         # + build_create_symbol_request / build_create_symbols_request
│                    #   build_update_symbol_request; + parse_symbol_response (single) if 201 shape needs it
├── _state.py        # + mutating_allowed: bool = False; + expected_host: str | None = None
├── models.py        # + NewSymbol / NewSymbols / SymbolPatch (frozen, to_dict); + __all__ entries
├── exceptions.py    # + MarketDataMutationNotAllowedError(MarketDataError); + __all__ (currently none)
├── client.py        # + _ensure_mutation_allowed; + create_symbol/create_symbols/update_symbol;
│                    #   + __init__/configure params; + module-level shims
├── aio.py           # identical mirror of client.py additions
└── __init__.py      # + re-export new exception + 3 models + (module shims already auto via *? NO — explicit)
```

### Pattern 1: POST-with-JSON-body pure builder (mirror `build_latest_batch_request`)
**What:** A pure `_core` builder returning a `RequestSpec` with `method`, `path`, `json_body`, `idempotent=True`, `authenticated=True`.
**When to use:** All three symbols builders.
**Example:**
```python
# Source: packages/market-data-client/src/market_data_client/_core.py:361-377 (build_latest_batch_request)
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
The three new builders follow this exactly. `build_update_symbol_request` additionally interpolates the id: `path=f"/symbols/{symbol_id}"` with `method="PATCH"` (D-08 path-encoding assumption noted in Assumptions Log).

### Pattern 2: Frozen request-model with hand-written `to_dict()` (mirror `LatestRequest`)
**What:** `@dataclass(frozen=True, slots=True)`, NOT a `SafeModel`, serializes OUT.
**When to use:** `NewSymbol`, `NewSymbols`, `SymbolPatch`.
**Example:**
```python
# Source: packages/market-data-client/src/market_data_client/models.py:160-181 (LatestRequest)
@dataclass(frozen=True, slots=True)
class LatestRequest:
    symbols: list[str]
    marketId: str | None = None
    entries: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"symbols": self.symbols}
        if self.marketId is not None:
            out["marketId"] = self.marketId
        if self.entries is not None:
            out["entries"] = self.entries
        return out
```
Symbols models per D-10:
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
            raise ValueError(f"NewSymbols requires 1–500 symbols, got {len(self.symbols)}")
    def to_dict(self) -> dict[str, Any]:
        return {"symbols": [s.to_dict() for s in self.symbols]}

@dataclass(frozen=True, slots=True)
class SymbolPatch:
    active: bool
    def to_dict(self) -> dict[str, Any]:
        return {"active": self.active}
```
Note: field name is `market_id` (snake_case) per the source-plan schema `NewSymbol = { symbol, market_id }` — unlike `LatestRequest` which uses wire-camelCase `marketId`. This is intentional per the source plan (`.planning/future-plans/market_data_mutations.md` line 39); the plan should preserve the schema's snake_case wire keys for symbols and flag it as a Phase-27 confirmation point.

### Pattern 3: Gate helper on the shell, called first (D-04/D-05)
**What:** Private `_ensure_mutation_allowed()` on each shell; raises before any IO.
**When to use:** Top of every mutation method.
**Example:**
```python
# NEW — pattern derived from verification/mutation_gate.py exact-host discipline
from urllib.parse import urlsplit

def _ensure_mutation_allowed(self) -> None:
    if not self._state.mutating_allowed:
        raise MarketDataMutationNotAllowedError(
            "Mutations refused: set mutating_allowed=True (constructor or configure())."
        )
    expected = self._state.expected_host
    actual = urlsplit(self._state.base_url).hostname
    if expected is not None and actual != expected:      # EXACT match, never substring (D-01)
        raise MarketDataMutationNotAllowedError(
            f"Mutations refused: base_url host {actual!r} != expected_host {expected!r}."
        )
```
Discretion (D-16 note): the exception signature can be a plain `str` message (simplest — `MarketDataMutationNotAllowedError` subclasses `MarketDataError` directly, NOT `MarketDataAPIError`, so it takes no `status_code`). See Anti-Patterns for the hierarchy choice.

### Pattern 4: `_ClientState` field + carry-forward propagation (D-13/D-14)
**What:** Plainly-typed new fields on the `@dataclass(slots=True)` state; constructor + `configure()` use `if x is not None:` carry-forward.
**Example:**
```python
# Source: _state.py:77-99 — add two fields:
    mutating_allowed: bool = False           # refuse-by-default
    expected_host: str | None = None
```
```python
# In Client.__init__ / AsyncClient.__init__ (mirror the existing `if base_url is not None:` chain):
    if mutating_allowed:                     # bool: only set True explicitly (see note)
        self._state.mutating_allowed = True
    if expected_host is not None:
        self._state.expected_host = expected_host
```
**Subtlety — bool carry-forward:** the existing carry-forward guard is `if x is not None`. For `mutating_allowed: bool` you must decide the constructor signature. Two mypy-clean options (Discretion): (a) `mutating_allowed: bool = False` param, assigned unconditionally (`self._state.mutating_allowed = mutating_allowed`) — simplest, but a bare `Client()` still gets `False` from the state default so it is safe; or (b) `mutating_allowed: bool | None = None` with `if mutating_allowed is not None:` to preserve carry-forward semantics in `configure()`. **Recommendation: use `bool | None = None` + `if is not None` in `configure()`** so `configure(base_url=...)` alone does not silently reset `mutating_allowed` to `False` — matching the carry-forward contract of every other `configure()` field. In `__init__`, a fresh `_ClientState()` already defaults to `False`, so either form is safe there.

**`expected_host` default (D-02):** default to `urlsplit(DEFAULT_BASE_URL).hostname` (`"market-data-develop.bbsa.com.ar"`). Cleanest: compute a module constant `_DEFAULT_EXPECTED_HOST = urlsplit(DEFAULT_BASE_URL).hostname` in `_state.py` and use it as the `expected_host` field default via `field(default=...)` (a plain str constant, not a factory). Confirm mypy-strict: `urlsplit(...).hostname` is `str | None`, so cast/assert or store the literal string constant directly to keep the field type `str | None` clean.

### Anti-Patterns to Avoid
- **Putting the gate in `_core` or `_request`:** `_core` builders `del state` and must stay IO-free (D-05); `_request` is shared with the read surface — a gate there would wrongly gate reads. Gate lives only in `_ensure_mutation_allowed()` on the shell.
- **Substring / `.endswith` host match:** `…bbsa.com.ar.attacker.example` would wrongly pass. Use exact `urlsplit(...).hostname == expected` (D-01, security-load-bearing).
- **`True` default for `mutating_allowed`:** defeats the entire phase. Refuse-by-default (`False`) is mandatory (D-13).
- **Storing `mutating_allowed` on instance `__slots__`:** breaks view inheritance — a `with_options` view would diverge from its parent (D-14). It must live on shared `_ClientState`.
- **Making `MarketDataMutationNotAllowedError` subclass `MarketDataAPIError`:** it is a client-side policy refusal, not a server error — it takes no `status_code`. Subclass `MarketDataError` directly (D-16 says `⊂ MarketDataError`).
- **Typed `MarketData*` error for the 1–500 batch check:** D-11 reserves that hierarchy for server contract errors; the length check raises a plain `ValueError`.
- **`_ensure_token()` before the gate:** would emit an Auth0 round-trip on a refused mutation, violating D-05's zero-round-trip guarantee. Gate is strictly first.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| No-retry of non-idempotent ops | A method-name retry filter | Existing `request.extensions["idempotent"]` gate in `RetryTransport` | Already implemented + tested; method-based gates silently retry POSTs (the matriz duplicate-order class of bug) |
| POST JSON body dispatch | Custom body encoder | `http.build_request(..., json=spec.json_body)` (already in `_request`) | Both shells already thread it; httpx handles content-type + encoding |
| Error → exception mapping | New status handling in mutation methods | Existing `_core.raise_for_response` | `422` already falls into `if resp.is_error → MarketDataAPIError` (D-12) |
| Tolerant response parsing | Manual `dict.get` chains | `SafeModel.from_api` (existing `Symbol` / `parse_symbols_response`) | Response shape deferred to Phase 27; `from_api` bounds the blast radius |
| Exact-host security check | New URL parser | `urllib.parse.urlsplit(...).hostname` | Same primitive `verification/mutation_gate.py` already trusts |

**Key insight:** Every mechanism this phase needs already exists in the package from the read-surface build-out (Phases 20–24). The phase is composition of proven parts, not new infrastructure. The only genuinely new logic is the ~10-line `_ensure_mutation_allowed()` gate helper (mirrored sync/async).

## Common Pitfalls

### Pitfall 1: Gate emits an Auth0 round-trip on refusal
**What goes wrong:** Placing `_ensure_mutation_allowed()` after `_ensure_token()` (or inside `_request`) means a refused mutation still fetches a token — leaking an attempt and violating D-05.
**Why it happens:** Copy-pasting the read-method shape (`spec = build_x(); resp = self._request(spec)`) which calls `_ensure_token` inside `_request`.
**How to avoid:** Call `_ensure_mutation_allowed()` as the literal first statement of every mutation method, before `_core.build_*`.
**Warning signs:** A gate-refusal test that asserts `len(httpx_mock.get_requests()) == 0` fails, or an Auth0 token endpoint mock is unexpectedly hit.

### Pitfall 2: Relying on cross-package parity tests that don't cover this package
**What goes wrong:** D-16 assumes `verification/test_public_surface.py` + `test_sync_async_isolation.py` will fail a missing `__all__` entry. They will NOT — `market_data_client` is absent from both `_PACKAGES` lists and has no surface snapshot.
**Why it happens:** Those tests were written in Phase 06/07 for the original 4 packages; market-data-client (added later, v0.2.0) was never enrolled.
**How to avoid:** Add explicit in-package tests: (a) assert each new public name is importable from `market_data_client` and in `__all__`; (b) assert sync and async surfaces expose identically-named `create_symbol`/`create_symbols`/`update_symbol`. Optionally (larger, Discretion) enroll `market_data_client` into the cross-package `_PACKAGES` lists + generate a `market-data-client-surface.txt` snapshot — but that is a bigger change touching cross-cutting verification and is not required by the phase.
**Warning signs:** A dropped export silently passes CI because no test references it.

### Pitfall 3: `market_id` wire-key casing mismatch
**What goes wrong:** Reusing `LatestRequest`'s camelCase `marketId` for `NewSymbol` when the source-plan schema specifies snake_case `market_id`.
**Why it happens:** The two request models live in the same file with different wire conventions.
**How to avoid:** `NewSymbol.to_dict()` emits `"market_id"` per the source plan schema (line 39). Flag as a Phase-27 live-confirmation point (Assumptions Log A2).
**Warning signs:** N/A until Phase 27 live verification — mocked tests pass with whatever key the model emits.

### Pitfall 4: PATCH path with `/` in `symbol_id`
**What goes wrong:** `f"/symbols/{symbol_id}"` with `symbol_id="DLR/DIC26"` produces `/symbols/DLR/DIC26`, which httpx sends as two path segments — the server may 404 or misroute.
**Why it happens:** The spec example id contains a literal `/`.
**How to avoid:** Interpolate raw for Phase 25 (mocked tests are agnostic), but explicitly document the encoding assumption (D-08) so Phase 27 confirms whether percent-encoding (`quote(symbol_id, safe="")`) is required. Do NOT resolve here.
**Warning signs:** N/A until Phase 27 (deferred).

### Pitfall 5: `configure(mutating_allowed=...)` resetting the flag via carry-forward
**What goes wrong:** If `mutating_allowed` is a plain `bool = False` param in `configure()`, then `configure(base_url="...")` (flag omitted) resets the flag to `False`, silently disabling mutations a consumer previously enabled.
**Why it happens:** `configure()` carry-forward relies on `None` sentinels; a `bool` default breaks it.
**How to avoid:** Type the `configure()` param `mutating_allowed: bool | None = None`, apply only `if mutating_allowed is not None`. (See Pattern 4 subtlety.)
**Warning signs:** A test that enables the gate, then calls `configure(base_url=...)`, then finds mutations refused.

### Pitfall 6: Module-level singleton cross-test contamination
**What goes wrong:** The new `mutating_allowed`/`expected_host` state persists on the default `Client` singleton across tests (like `_configure_sync`/`_configure_async` in conftest already manage token state).
**Why it happens:** `_default_client` is a process-wide singleton (documented conftest Pitfall 6).
**How to avoid:** Gate tests that flip `mutating_allowed=True` must reset it (or construct fresh `Client(mutating_allowed=True, expected_host=...)` instances rather than mutating the default). The autouse conftest fixtures reset base_url/creds but do NOT yet reset the new fields — the plan should extend the conftest teardown or use per-test instances.
**Warning signs:** Test order-dependent gate failures.

## Code Examples

### Wire-level body serialization test (mirror existing batch test)
```python
# Source: packages/market-data-client/tests/test_client.py:241-255
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
Symbols equivalent: mock a 201, call `create_symbol(NewSymbol("DLR/DIC26"))`, assert `req.method == "POST"`, `req.url.path == "/api/symbols"`, and `_json.loads(req.content) == {"symbol": "DLR/DIC26", "market_id": "ROFX"}`.

### Gate-refusal test (zero HTTP + zero Auth0)
```python
# NEW — asserts D-05 zero-side-effect guarantee
def test_create_symbol_refused_by_default_emits_no_request(httpx_mock: HTTPXMock) -> None:
    client = market_data_client.Client()               # mutating_allowed defaults False
    with pytest.raises(market_data_client.MarketDataMutationNotAllowedError):
        client.create_symbol(NewSymbol("DLR/DIC26"))
    assert len(httpx_mock.get_requests()) == 0         # no HTTP, no Auth0 token fetch
```

### Builder unit test (mirror `test_build_latest_batch_request_posts_serialized_body`)
```python
# Source pattern: packages/market-data-client/tests/test_market_data.py:121-132
def test_build_create_symbol_request() -> None:
    state = _ClientState()
    spec = _core.build_create_symbol_request(state, NewSymbol("DLR/DIC26").to_dict())
    assert spec.method == "POST"
    assert spec.path == "/symbols"
    assert spec.authenticated is True
    assert spec.idempotent is True                     # DM-03
    assert spec.json_body == {"symbol": "DLR/DIC26", "market_id": "ROFX"}
```

### No-retry-on-503 test for a mutation (mirror `test_mutating_call_never_retries_against_503`)
```python
# Source pattern: verification/test_retry_mutation_gate.py:118-145 (but symbols are idempotent=True)
# NOTE: symbols builders set idempotent=True per DM-03, so a 503 on create_symbol WILL retry
# up to max_attempts. The "no-retry" guarantee in this phase applies to the transport gate
# mechanism, exercised in Phase 26 by POST /calendar/holidays (idempotent=False). For Phase 25,
# the relevant assertion is that the gate FLAG (mutating_allowed) blocks, not the idempotent flag.
```
Important nuance: per DM-03/D-07, all three symbols endpoints are `idempotent=True`, so they ARE retry-eligible. Success Criterion #4 (`request.extensions["idempotent"]=False`) explicitly notes "for symbols all are idempotent=True; the False applies to calendar in Phase 26." The plan's no-retry test should therefore target the **gate-refusal** path (0 requests), not a 503-no-retry path.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Read-only client (v0.2.0) | Adds first write surface behind opt-in gate | Phase 25 (this) | Minor bump to v0.3.0 (Phase 28); no break to read surface |
| Method-based retry gates (industry default) | `request.extensions["idempotent"]` per-request gate | Established in Phase 8/20 | Prevents duplicate-mutation on non-idempotent POSTs |

**Deprecated/outdated:** None relevant to this phase.

## Runtime State Inventory

Not applicable — this is a **greenfield additive** phase (new methods/models/fields), not a rename/refactor/migration. No stored data, live service config, OS-registered state, secrets, or build artifacts carry an old name that must change. Verified by grep: `mutating_allowed`/`expected_host`/`MutationNotAllowed` do not exist anywhere in the package source yet (greenfield for this phase).

## Validation Architecture

`.planning/config.json` was not located under standard paths during research; treating `nyquist_validation` as **enabled** (absent = enabled). The plan should confirm.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >=8.3 + pytest-asyncio >=0.24 (`asyncio_mode = "auto"`) + pytest-httpx >=0.34 |
| Config file | root `pyproject.toml` (`[tool.pytest.ini_options]`, `--import-mode=importlib`, `--strict-markers`) |
| Quick run command | `uv run --package market-data-client pytest packages/market-data-client/tests -q` |
| Full suite command | `uv run pytest -q` (all packages + `verification/`) |

### Phase Requirements → Test Map
| Req / Success Criterion | Behavior | Test Type | Automated Command | File Exists? |
|-------------------------|----------|-----------|-------------------|--------------|
| SC#1 / GATE-MD-01 | default `Client()`/`AsyncClient()` refuses mutation with `MarketDataMutationNotAllowedError`, **0 HTTP requests** | unit (pytest-httpx) | `pytest packages/market-data-client/tests/test_mutation_gate.py -q` | ❌ Wave 0 |
| SC#1 (adversarial) | refused mutation emits **0 Auth0 token round-trips** (no token endpoint mock hit) | unit | same file, assert `get_requests() == []` incl. auth URL | ❌ Wave 0 |
| SC#1 (host gate) | `mutating_allowed=True` but wrong `base_url` host → refused (exact-host, substring attacker host rejected) | unit | same file | ❌ Wave 0 |
| SC#2 / MUT-MD-01 | `create_symbol` / `create_symbols` / `update_symbol` dispatch with gate ON + correct host (sync + async) | unit | `pytest .../test_symbols_write.py .../test_symbols_write_async.py -q` | ❌ Wave 0 |
| SC#3 | request bodies serialize model→JSON; 201/200 parse to tolerant `SafeModel`; 422→typed `MarketDataAPIError` | unit | same | ❌ Wave 0 |
| SC#3 (batch bounds) | `NewSymbols([])` and `NewSymbols([501 items])` raise plain `ValueError` before dispatch | unit | `pytest .../test_models.py -q` | partial (test_models.py exists) |
| SC#4 | symbols builders set `idempotent=True` (DM-03); gate-refusal path emits 0 requests | unit | `pytest .../test_core.py .../test_mutation_gate.py -q` | test_core.py exists |
| SC#5 (parity) | sync + async expose identically-named methods + shims; new names in `__all__` | unit | `pytest .../test_public_surface_market_data.py -q` (NEW, in-package) | ❌ Wave 0 |
| SC#5 (gates) | ruff / format / mypy-strict / pytest all green | gate | `uv run ruff check . && uv run ruff format --check . && uv run mypy . && uv run pytest -q` | n/a |

### Sampling Rate
- **Per task commit:** `uv run --package market-data-client pytest packages/market-data-client/tests -q`
- **Per wave merge:** `uv run pytest -q` (full suite incl. `verification/`)
- **Phase gate:** four green gates (`ruff check`, `ruff format --check`, `mypy` strict, `pytest`) before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `packages/market-data-client/tests/test_mutation_gate.py` — gate ON/OFF, zero-HTTP-zero-Auth0 refusal, exact-host rejection (sync + async) — covers GATE-MD-01 / SC#1
- [ ] `packages/market-data-client/tests/test_symbols_write.py` + `test_symbols_write_async.py` — 3 endpoints, body serialization, 201/200 parse, 422→typed error — covers MUT-MD-01 / SC#2-3
- [ ] `packages/market-data-client/tests/test_public_surface_market_data.py` — in-package export + sync/async name-parity assertions (because cross-package nets exclude this package) — covers SC#5
- [ ] Extend `packages/market-data-client/tests/test_models.py` — `NewSymbol`/`NewSymbols`/`SymbolPatch` `to_dict()` + `NewSymbols` 1–500 `ValueError` bounds — covers D-10/D-11
- [ ] Extend `packages/market-data-client/tests/test_core.py` — 3 new builder specs (method/path/idempotent/json_body)
- [ ] Extend `conftest.py` teardown to reset `mutating_allowed`/`expected_host` on the default singletons (Pitfall 6)

## Security Domain

`security_enforcement` config was not locatable during research; treating as **enabled** (absent = enabled). This phase's core deliverable IS a security control (the mutation gate), so the section applies directly.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V1 Architecture / Secure Defaults | yes | Refuse-by-default (`mutating_allowed=False`) — mutations impossible without explicit opt-in (D-13) |
| V4 Access Control | yes | Double gate: opt-in flag AND exact-host environment check before any state-mutating call (D-01/D-05) |
| V5 Input Validation | yes | `NewSymbols` 1–500 client-side `ValueError` (D-11); typed request models constrain payload shape |
| V6 Cryptography | no | No new crypto; bearer token handling unchanged from v0.2.0 |
| V7 Error Handling / Logging | yes | Credential redaction already enforced (`__repr__` redacts secret/token; `RedactingFilter` on package logger) — mutation methods must not log payloads with credentials |
| V9 Communications | yes | Exact-hostname gate prevents mutating against an unexpected/hostile host (`…bbsa.com.ar.attacker.example` rejected) |

### Known Threat Patterns for this stack
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Accidental mutation fired without opt-in | Tampering | Refuse-by-default flag on shared `_ClientState` (D-13) |
| Mutation dispatched to a hostile/wrong host | Tampering / Spoofing | Exact `urlsplit(base_url).hostname == expected_host`, never substring (D-01) |
| Substring host bypass (`bbsa.com.ar.attacker.example`) | Spoofing | Exact-match only — adversarial test required (Specifics in CONTEXT.md) |
| Refusal leaks an attempt via Auth0 round-trip | Information Disclosure | Gate strictly before `_ensure_token` — zero token fetch on refusal (D-05) |
| Duplicate mutation via retried non-idempotent POST | Tampering | `request.extensions["idempotent"]` transport gate (symbols=True per spec; revalidated Phase 27) |
| Credential leak in mutation logs/reprs | Information Disclosure | Existing `RedactingFilter` + redacting `__repr__` (unchanged, must not be regressed) |

## Environment Availability

Skipped — no new external dependencies, tools, services, or runtimes. The phase is a code-only additive change against the already-installed workspace (`uv sync --all-packages`). Mocked tests (pytest-httpx) require no live network; live verification is explicitly Phase 27.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | 201/200/422 response shapes for the 3 symbols endpoints (single `Symbol` vs `list[Symbol]` vs `{items:[...]}`) — parsers stay tolerant | Deferred / MUT-MD-01 | LOW — `from_api` tolerance degrades gracefully; Phase 27 reconciles (explicitly deferred per CONTEXT.md) |
| A2 | `NewSymbol` wire key is snake_case `market_id` (per source-plan schema), not camelCase `marketId` | Pattern 2 / Pitfall 3 | LOW-MED — a wrong key means server ignores/rejects the field; mocked tests pass either way; Phase 27 confirms |
| A3 | `POST /symbols` and `POST /symbols/batch` are truly server-side idempotent (DM-03) → `idempotent=True` | D-07 / SC#4 | MED — if a retried POST duplicates state, flips to `idempotent=False` in Phase 27 (explicitly deferred) |
| A4 | `symbol_id` with `/` (`"DLR/DIC26"`) can be interpolated raw into the PATCH path | D-08 / Pitfall 4 | MED — may need `quote(..., safe="")`; mocked tests agnostic; Phase 27 confirms (explicitly deferred) |
| A5 | `.planning/config.json` `nyquist_validation` and `security_enforcement` are enabled (absent=enabled) | Validation / Security | LOW — if disabled, those sections are informational only |
| A6 | `MarketDataMutationNotAllowedError` should subclass `MarketDataError` directly (no `status_code`), not `MarketDataAPIError` | D-16 / Anti-Patterns | LOW — CONTEXT.md D-16 says `⊂ MarketDataError`; a client-side refusal has no HTTP status |

## Open Questions (RESOLVED)

1. **Should `market_data_client` be enrolled into the cross-package `verification/test_public_surface.py` + `test_sync_async_isolation.py` nets?** — **RESOLVED:** Plan 25-03 adds an in-package `test_public_surface_market_data.py` (sufficient for SC#5); cross-package enrollment noted as an optional non-blocking follow-up.
   - What we know: it is currently absent from both `_PACKAGES` lists and has no surface snapshot; D-16 incorrectly assumes those tests cover it.
   - What's unclear: whether enrolling it (bigger cross-cutting change + snapshot generation) is in-scope or whether in-package tests suffice for Phase 25.
   - Recommendation: add **in-package** export/parity tests for Phase 25 (minimal, sufficient for SC#5). Optionally file enrolling market-data into the cross-package nets as a follow-up (not blocking).

2. **`configure(mutating_allowed=...)` sentinel typing.** — **RESOLVED:** Plan 25-01 uses `bool | None = None` with `if mutating_allowed is not None` carry-forward, so `configure(base_url=...)` cannot silently reset a prior opt-in.
   - What we know: `configure()` uses `None`-sentinel carry-forward for every field.
   - Recommendation applied: `bool | None = None` with `if mutating_allowed is not None`.

## Sources

### Primary (HIGH confidence — verified against source this session)
- `packages/market-data-client/src/market_data_client/_core.py` — `RequestSpec` (has `method`, `json_body`), `build_latest_batch_request`, `raise_for_response`, `build_symbols_request`, `parse_symbols_response` [VERIFIED]
- `packages/market-data-client/src/market_data_client/client.py` — `_request` / `_send_auth_request` dispatch, `request.extensions["idempotent"]`/`max_attempts`, `configure()`, `__init__`, `with_options`, `_validate_max_retries`, module shims [VERIFIED]
- `packages/market-data-client/src/market_data_client/aio.py` — async mirror (double-checked locking, identical dispatch) [VERIFIED]
- `packages/market-data-client/src/market_data_client/models.py` — `SafeModel`, `_coerce`, `LatestRequest.to_dict()`, `Symbol` [VERIFIED]
- `packages/market-data-client/src/market_data_client/_state.py` — `_ClientState` (`slots=True`), `DEFAULT_BASE_URL` [VERIFIED]
- `packages/market-data-client/src/market_data_client/exceptions.py` — `MarketDataError` hierarchy (no `__all__` present) [VERIFIED]
- `packages/market-data-client/src/market_data_client/_transport.py` — `RetryTransport` idempotent gate [VERIFIED]
- `packages/market-data-client/src/market_data_client/__init__.py` — `__all__`, `__version__ = "0.2.0"` [VERIFIED]
- `verification/mutation_gate.py` — exact-hostname discipline (`urlsplit(base).hostname != _SANDBOX_HOST`) [VERIFIED]
- `verification/test_public_surface.py` + `verification/test_sync_async_isolation.py` — `_PACKAGES` lists exclude `market_data_client`; no market-data snapshot in `verification/snapshots/` [VERIFIED]
- `packages/market-data-client/tests/conftest.py`, `test_client.py:241-255`, `test_market_data.py:121-132`, `test_core.py` — test patterns [VERIFIED]
- `verification/test_retry_mutation_gate.py` — mutation-gate no-retry test pattern [VERIFIED]

### Secondary (MEDIUM confidence)
- `.planning/future-plans/market_data_mutations.md` — request schemas, DM-01…DM-08 locks (source plan, not yet executed)
- `.planning/phases/25-mutating-gate-symbols-write/25-CONTEXT.md` — locked D-01…D-16

### Tertiary (LOW confidence)
- None. No external/web sources needed — the phase is grounded entirely in existing source.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new deps; every mechanism verified present in source
- Architecture: HIGH — all patterns have working in-package precedents (`build_latest_batch_request`, `LatestRequest`, `_validate_max_retries`, `with_options` shared-state)
- Pitfalls: HIGH — grounded in source (gate placement, cross-package test exclusion, bool carry-forward, singleton contamination); Phase-27-deferred items honestly flagged as assumptions
- Security: HIGH — mirrors the verified `verification/mutation_gate.py` exact-host discipline

**Research date:** 2026-07-31
**Valid until:** 2026-08-30 (stable — internal package source, no fast-moving external deps)
