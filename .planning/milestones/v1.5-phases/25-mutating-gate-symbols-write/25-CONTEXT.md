# Phase 25: Mutating-gate + Symbols write - Context

**Gathered:** 2026-07-31 (assumptions mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

Extend the existing `market-data-client` package (v0.2.0, read-only) with its **first
mutation surface** — symbols write — behind a **load-bearing safety gate** that makes an
accidental mutation impossible to trigger. Two requirements:

- **GATE-MD-01** — the mutating-gate itself: opt-in `mutating_allowed` (constructor +
  `configure()`), a second host/environment gate, no-retry of non-idempotent operations,
  and a new typed `MarketDataMutationNotAllowedError ⊂ MarketDataError`. Dual sync/async.
- **MUT-MD-01** — symbols write: `create_symbol` (`POST /symbols`, `NewSymbol`),
  `create_symbols` (`POST /symbols/batch`, `NewSymbols`, batch 1–500), `update_symbol`
  (`PATCH /symbols/{symbol_id}`, `SymbolPatch`) — typed request-models serialized to JSON,
  tolerant `SafeModel` responses, `422` → typed error, sync + async, all behind the gate.

The gate is built FIRST and symbols is the first surface that exercises it. Calendar write
(MUT-MD-02) is **Phase 26**, live verification is **Phase 27**, release is **Phase 28** —
all OUT of scope here.

**IN scope:** the gate mechanics + 3 symbols endpoints + request models + mocked tests
(pytest-httpx), 4 green gates (ruff/format/mypy-strict/pytest).
**OUT of scope:** calendar endpoints, live verification against develop, version bump/release.
</domain>

<decisions>
## Implementation Decisions

### A. Env/host gate mechanics
- **D-01:** Add an opt-in `expected_host: str | None` field to `_ClientState`, alongside
  `mutating_allowed`. The host gate compares `urllib.parse.urlsplit(self._state.base_url).hostname`
  by **EXACT match** (never substring, never `.endswith`) against the expected host.
- **D-02:** `expected_host` defaults to the hostname of `DEFAULT_BASE_URL`
  (`market-data-develop.bbsa.com.ar`). A consumer that reconfigures `base_url` to a legitimate
  alternate develop host must also set `expected_host` to match, or the gate refuses.
- **D-03:** The `require_env` / `VERIFY_MUTATING` env opt-in (from `verification/env_gate.py`)
  stays in the **Phase-27 verification harness**, NOT inside the client. The client's second
  gate is purely the host check above.

### B. Gate check location
- **D-04:** A private `_ensure_mutation_allowed()` helper on each shell (`Client` /
  `AsyncClient`). Every public mutation method calls it FIRST — before building the spec,
  before any token fetch, before any transport touch.
- **D-05:** On refusal (`mutating_allowed is False` OR host check fails) it raises
  `MarketDataMutationNotAllowedError` and **guarantees zero HTTP request AND zero Auth0
  round-trip** are emitted. The check does NOT live in `_core` (must stay IO-free /
  state-agnostic) nor in `_request` (shared by the read surface).

### C. RequestSpec extension for write
- **D-06:** `RequestSpec` needs **no structural change** — it already carries `method: str`
  and `json_body: dict[str, Any] | None`, and `_request` already threads `json=spec.json_body`
  into `http.build_request`. `build_latest_batch_request` is the working POST-with-JSON-body
  precedent to mirror.
- **D-07:** Add three pure builders to `_core.py`: `build_create_symbol_request`,
  `build_create_symbols_request`, `build_update_symbol_request` — returning
  `RequestSpec(method="POST"|"PATCH", path=..., json_body=..., authenticated=True,
  idempotent=True, endpoint_name=...)`. Per DM-03 all three symbols endpoints are
  `idempotent=True` (spec declares them idempotent; revalidated live in Phase 27).
- **D-08:** `PATCH /symbols/{symbol_id}` interpolates the id into the path. The plan must
  account for `symbol_id` values that may contain `/` (spec example `"DLR/DIC26"`) — treat
  path-encoding as an explicit assumption to confirm live in Phase 27 (see Deferred).

### D. Request-model serialization
- **D-09:** Model `NewSymbol`, `NewSymbols`, `SymbolPatch` as frozen
  `@dataclass(frozen=True, slots=True)` in `models.py` — **NOT** `SafeModel` subclasses (they
  serialize OUTWARD). Each has a hand-written `to_dict()` mirroring the existing
  `LatestRequest.to_dict()` pattern in the same package.
- **D-10:** `NewSymbol` sends `symbol` always and `market_id` always (a defaulted,
  non-nullable field, default `"ROFX"` — sent explicitly, not dropped).
  `NewSymbols.to_dict()` → `{"symbols": [s.to_dict() for s in self.symbols]}`.
  `SymbolPatch.to_dict()` → `{"active": self.active}`. `_params.drop_none` applies only to
  genuinely-optional `None` fields (none in the current symbols models).

### E. Batch validation (1–500)
- **D-11:** Enforce the `NewSymbols` 1–500 length constraint **client-side**, raising a plain
  **`ValueError`** (NOT a typed `MarketData*` error — that hierarchy is reserved for server
  contract errors) before any spec build or HTTP dispatch. Placement: `NewSymbols.__post_init__`
  so it holds regardless of entry point (sync / async / direct construction). Mirrors the
  existing `_validate_max_retries` `ValueError` precedent.
- **D-12:** Server-side `422` responses remain a separate concern surfaced as the existing
  typed API error via `raise_for_response` (`_core.py` status mapping) — unchanged.

### F. Typing + view propagation
- **D-13:** Add `mutating_allowed: bool = False` (refuse-by-default) and
  `expected_host: str | None = None` to `_ClientState` as plainly-typed fields. Add matching
  keyword-only params to `Client.__init__` / `AsyncClient.__init__` and to `configure()`
  (both surfaces), following the existing `if x is not None:` carry-forward pattern.
  **Consistency note (D-02 ↔ D-13):** the `str | None = None` FIELD default is the sentinel
  meaning "unset" — it does NOT mean "no host gate". At gate-check time a `None` `expected_host`
  resolves to the hostname of `DEFAULT_BASE_URL` (D-02), i.e. the effective default host is
  always enforced. `None` = use-default-host, never bypass-host-check.
- **D-14:** Because these fields live on the SHARED `_ClientState` and `with_options` clones
  share `self._state`, the mutation flag + host gate **propagate to views automatically** with
  zero extra code — a view of a mutating-allowed client is also mutating-allowed. Do NOT store
  `mutating_allowed` on the instance `__slots__` (that would break view inheritance and create
  a parent/view gate divergence).

### G. Sync/async parity + public surface
- **D-15:** Mirror EVERY symbols method, the `_ensure_mutation_allowed` helper, the new
  constructor + `configure()` params, and module-level shims across `client.py` AND `aio.py`
  identically. Module-level sync shims (`create_symbol`, etc.) delegate to `_get_default()`
  exactly like `get_symbols`; async shims stay under `aio`.
- **D-16:** Add `MarketDataMutationNotAllowedError` to `exceptions.py` `__all__`, the three
  request models to `models.py` `__all__`, and re-export all of them through `__init__.py`
  `__all__`. Existing `verification/test_public_surface.py` and `test_sync_async_isolation.py`
  enforce this parity — a missing entry fails the gates.

### Claude's Discretion
- Exact builder/method naming beyond the DM-locked public names (`create_symbol`,
  `create_symbols`, `update_symbol`); internal helper names; test file organization; whether
  the host-gate comparison is a small module-level pure function reused by both shells (a
  reasonable dedup that stays consistent with the sync/async duplication constraint).
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Source plan + requirements (locked scope)
- `.planning/future-plans/market_data_mutations.md` — milestone source plan: full mutation API
  surface, request schemas (`NewSymbol`/`NewSymbols`/`SymbolPatch`), and DM-01…DM-08 locks.
- `.planning/REQUIREMENTS.md` — GATE-MD-01, MUT-MD-01 acceptance text.
- `.planning/ROADMAP.md` — Phase 25 goal + 5 success criteria.

### Package to extend (market-data-client v0.2.0)
- `packages/market-data-client/src/market_data_client/_core.py` — pure builders/parsers,
  `RequestSpec` (has `method`, `json_body`), `raise_for_response`, status mapping;
  `build_latest_batch_request` = POST-with-JSON-body precedent.
- `packages/market-data-client/src/market_data_client/client.py` — sync shell: `_request` /
  `_send_auth_request` dispatch, `request.extensions["idempotent"]` / `max_attempts`,
  `configure()`, `__init__`, `with_options` clone, `_validate_max_retries`, module shims.
- `packages/market-data-client/src/market_data_client/aio.py` — async mirror.
- `packages/market-data-client/src/market_data_client/models.py` — `SafeModel` base, `_coerce`,
  `LatestRequest.to_dict()` request-model precedent, existing `Symbol` read model.
- `packages/market-data-client/src/market_data_client/exceptions.py` — `MarketDataError`
  hierarchy (API / Auth / RateLimit).
- `packages/market-data-client/src/market_data_client/_state.py` — `_ClientState`
  (`slots=True`), `DEFAULT_BASE_URL`, env resolution.
- `packages/market-data-client/src/market_data_client/_params.py` — `drop_none`.
- `packages/market-data-client/src/market_data_client/_transport.py` /
  `_atransport.py` — how `request.extensions["idempotent"]` gates retries.

### Mutating-gate reference pattern (matriz)
- `packages/matriz-client/src/matriz_client/client.py` — mutation-gate comments (~lines
  250–330): non-idempotent requests execute exactly 1 outgoing request regardless of retries.
- `verification/mutation_gate.py` — exact-hostname host-check discipline being mirrored (D-01).
- `verification/env_gate.py` — the `require_env` env opt-in that stays in the Phase-27 harness (D-03).

### Conventions
- `.planning/codebase/CONVENTIONS.md`, `.planning/codebase/STRUCTURE.md` — naming, dual
  sync/async, SafeModel, exception, and export conventions.
- `./CLAUDE.md` — dual sync/async mirroring rule, mypy-strict, credential-redaction constraints.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `RequestSpec` already supports write: `method` + `json_body` fields exist; `_request`
  already passes `json=spec.json_body`. No transport/spec structural change needed (D-06).
- `build_latest_batch_request` — a POST builder with a JSON body and `idempotent=True`, the
  direct template for the three symbols builders (D-07).
- `LatestRequest` — the frozen-dataclass request-model + hand-written `to_dict()` template for
  `NewSymbol`/`NewSymbols`/`SymbolPatch` (D-09).
- `_validate_max_retries` — the client-side-`ValueError`-before-dispatch precedent for the
  1–500 batch check (D-11).
- `with_options` shared-`_state` clone — makes the gate flag inherit into views for free (D-14).
- `verification/mutation_gate.py` — exact-hostname gate discipline to mirror (D-01).

### Established Patterns
- `_core.py` is PURE / IO-free and its builders `del state`; policy checks against live
  `mutating_allowed`/host must live in the stateful shell, never in `_core` (D-05).
- Uniform shell method shape: `spec = _core.build_x(...)` → `resp = self._request(spec)` →
  `parse` — insert `_ensure_mutation_allowed()` at method entry (D-04).
- Request models serialize OUT (frozen dataclass + `to_dict()`); response models deserialize
  IN (tolerant `SafeModel.from_api`). Two distinct patterns in the same `models.py`.
- Every logic change mirrored sync (`client.py`) + async (`aio.py`); parity enforced by
  `verification/test_public_surface.py` + `test_sync_async_isolation.py`.

### Integration Points
- New public methods: `create_symbol`, `create_symbols`, `update_symbol` (both shells + module
  shims). New helper `_ensure_mutation_allowed` (both shells). New constructor/`configure`
  params `mutating_allowed` + `expected_host` (both shells + `_ClientState`).
- New exceptions entry `MarketDataMutationNotAllowedError ⊂ MarketDataError`.
- New request models `NewSymbol` / `NewSymbols` / `SymbolPatch` in `models.py`.
- All re-exported via `__init__.py` `__all__`.
</code_context>

<specifics>
## Specific Ideas

- Host-gate comparison MUST be exact-hostname (`urlsplit(...).hostname == expected`), the
  security-load-bearing detail (D-01) — a substring/`endswith` match is a known vulnerability
  (`…bbsa.com.ar.attacker.example` would wrongly pass).
- Refuse-by-default: `mutating_allowed` defaults to `False` (D-13). A `True` default would
  make mutations fire without opt-in and defeat the whole phase.
- Zero side effects on refusal: no HTTP request, no Auth0 token fetch (D-05) — the gate must
  be adversarially tested for this (a refused mutation must not even reveal an attempt via a
  token round-trip).
</specifics>

<deferred>
## Deferred Ideas

**Confirm live against develop in Phase 27 (LIVE-MUT-01) — explicitly deferred per the source
plan, NOT resolvable from the codebase and not blocking Phase 25 planning:**
- Exact `201` / `200` / `422` response shapes for the three symbols endpoints (single `Symbol`
  vs `list[Symbol]` vs an `{items:[...]}` envelope; whether the `422` body carries structured
  detail worth typing beyond the existing API error). Parsers stay tolerant (`from_api`) so a
  shape surprise degrades gracefully rather than crashing.
- Real server-side idempotency of `POST /symbols` and `POST /symbols/batch` — DM-03 locks
  `idempotent=True` per the spec's declaration; if a retried POST duplicates state live, the
  classification flips to `idempotent=False` for those builders in Phase 27.
- PATCH path encoding for `symbol_id` values containing `/` (e.g. `"DLR/DIC26"`) — whether the
  id is a URL-safe surrogate or a raw symbol needing percent-encoding (D-08).

**Out of scope of this milestone (backlog v2):** SSE streaming, Auth0 token disk cache
(SEC-MD-01), JWT signature validation (SEC-MD-02) — per DM-08.

### Reviewed Todos (not folded)
None — no pending todos matched Phase 25 scope.
</deferred>

---

*Phase: 25-mutating-gate-symbols-write*
*Context gathered: 2026-07-31 via assumptions mode*
