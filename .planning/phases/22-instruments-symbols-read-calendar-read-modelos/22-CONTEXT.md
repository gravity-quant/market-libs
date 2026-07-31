# Phase 22: Instruments + symbols(read) + calendar(read) + modelos - Context

**Gathered:** 2026-07-30 (assumptions mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

Cover the **reference-data read** surface of `packages/market-data-client/`, on top of
the Phase 20 foundation (Auth0 client_credentials auth, retry transport, `_request` with
`authenticated` gating) and alongside Phase 21 (market-data read + `models.py` +
`with_options`). Scope — five read endpoints:

- `GET /instruments` (filters: `q, segment, market_id, include_expired, only_outright,
  subscribed, limit, offset, refresh`)
- `GET /instruments/segments` (no params)
- `GET /symbols` (filters: `active, market_id, prefix`)
- `GET /calendar` (filter: `year`)
- `GET /calendar/config` (no params)

Each endpoint returns typed models (collections with 204/None → `[]` guards; the singular
config as one typed object). Dual sync/async parity mandatory. Requirement: **REF-MD-01**.

**Out of scope (do NOT add):** mutations — `POST/PATCH /symbols*`, `PUT/POST/DELETE
/calendar*` (deferred to v1.5+, need a mutating-gate); SSE streaming; market-data read
(Phase 21); live verification + model reconciliation (Phase 23). Read-only, no
mutating-gate.
</domain>

<decisions>
## Implementation Decisions

### Endpoint builders + param serialization (`_core.py`)
- **D-01:** Add five pure builders to `_core.py`, mirroring the Phase-21 read builders exactly:
  `build_instruments_request`, `build_segments_request` (`GET /instruments/segments`),
  `build_symbols_request`, `build_calendar_request`, `build_calendar_config_request`. Each
  returns `RequestSpec(method="GET", ..., authenticated=True, idempotent=True)` with a distinct
  `endpoint_name`. `authenticated=True` triggers Bearer injection in `_request`; GET reads are
  idempotent → retry-eligible. Analog: `_core.build_market_data_request`.
- **D-02:** Filter kwargs per endpoint: instruments = `q, segment, market_id, include_expired,
  only_outright, subscribed, limit, offset, refresh`; symbols = `active, market_id, prefix`;
  calendar = `year`; segments + calendar/config take no params. Optionals dropped via the
  existing `_params.drop_none`, preserving legitimate falsy values (`active=False`, `offset=0`,
  `""`); an empty dict collapses to `params=None` (`params or None`).
- **D-03:** Booleans (`include_expired, only_outright, subscribed, active`) ride httpx's native
  `True → "true"` param encoding for now — explicit wire-encoding is the SAME Phase-23
  verification target as Phase 21's D-07 (mocked tests can't catch a server silently ignoring a
  mis-encoded filter). Do NOT copy higyrus `format_bool`.

### Response models (`models.py` — extended in place)
- **D-04:** Add net-new PROVISIONAL `SafeModel` dataclasses to the **existing**
  `packages/market-data-client/src/market_data_client/models.py` (do NOT create a new module):
  `Instrument`, `Segment`, `Symbol`, `CalendarDay`, `CalendarConfig`. All
  `@dataclass(frozen=True, slots=True)`, built via `from_api`, wire field names kept
  **camelCase verbatim**. `models.py` is already in ruff's `N815` per-file-ignores — no config
  change needed. `from_api` tolerates partial/None/extra keys without raising (bounded blast
  radius; Phase 23 reconciles exact shapes against real develop payloads).
- **D-05:** Reference-data models do **NOT** carry a client-stamped `received_at`. Unlike
  `MarketDataSnapshot` (D-01 of Phase 21), these are slow-moving catalog data with no
  `max_staleness_seconds` filter to companion — so they are **plain** `SafeModel` subclasses,
  like the nested `MarketDataEntry` (which already omits `received_at`). If Phase-23 live
  payloads reveal a real need for receipt-time stamping on any reference model, it is an
  additive one-line injection (same pattern as `MarketDataSnapshot.from_api`), not a blocker now.

### Return shapes (parsers in `_core.py`)
- **D-06:** `instruments`, `segments`, `symbols`, `calendar` return **collections** →
  `list[Model]`. Each parser follows the Phase-21 body-consume-then-raise order
  (`resp.read()` → `raise_for_response` → decode) with the `if not resp.content or raw is None:
  return []` 204/None collection guard. No `received_at` stamp is captured (D-05).
- **D-07:** `GET /calendar/config` returns a **single** typed `CalendarConfig` object via
  `CalendarConfig.from_api(raw)` — NOT a list. An empty/None body collapses to an empty instance
  via `CalendarConfig.from_api(None)` (tolerant default), never a raise. Chosen over a raw-dict
  pass-through (à la `parse_health_response`) to honor criterion 2 ("modelos tipados"); its
  singular nature is confirmed by the deferred `PUT/POST/DELETE /calendar/config` mutation
  variants operating on one resource.

### Public surface (methods, shims, exports)
- **D-08:** Add five methods to BOTH `Client` (`client.py`) and `AsyncClient` (`aio.py`), plus
  five module-level top-level shims, plus `__init__.py` re-exports (methods + the new model
  classes). Dual sync/async parity is mandatory (known duplication debt — no shared internals by
  design). Method dispatch mirrors `get_market_data`: build spec → `self._request(spec)` /
  `await self._request(spec)` → parse. `with_options(max_retries=N)` (Phase 21 D-08) already
  threads through `_request`, so these methods inherit the per-call retry cap for free.

### Test strategy
- **D-09:** Mocked tests via **pytest-httpx** cover: query-param serialization for every
  instruments/symbols/calendar filter, `from_api` partial/None tolerance for each new model,
  the 204/None→`[]` collection guards (D-06), the single-object `calendar/config` parse +
  empty-body tolerance (D-07), and full sync/async parity. All four CI gates (ruff / format /
  mypy strict / pytest) green.

### Claude's Discretion
- Exact method names (`get_instruments`, `get_segments`, `get_symbols`, `get_calendar`,
  `get_calendar_config` are the working names) — pick spellings consistent with the existing
  concise surface (`get_market_data`, `get_latest`).
- Exact model class/field naming and per-model shape — designed from the plan + endpoint
  semantics, with `from_api` tolerance absorbing Phase-23 corrections. `CalendarDay` vs a
  richer `Calendar` wrapper is left to the planner if the `/calendar` payload is clearly a
  wrapped object rather than a flat list.
- Whether new tests extend `test_market_data.py` / `test_models.py` or land in dedicated
  `test_reference.py` / new model test cases — organize per existing test conventions.
- Boolean/param wire-encoding (httpx-native `true/false` vs `1/0` vs repeated keys): default to
  httpx-native now; explicit Phase-23 live-verification target (D-03).
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.future_plans/market_data.md` — milestone v1.4 source plan; D-locks (D-01..D-07) and the
  **"Fase 3"** section describing this exact reference-read surface. **Source of truth.**
- `.planning/REQUIREMENTS.md` → **REF-MD-01** (acceptance criteria for this phase).
- `.planning/ROADMAP.md` § "Phase Details (v1.4)" → **Phase 22** (success criteria, lines
  ~134-145).
- `.planning/phases/21-market-data-lectura-modelos/21-CONTEXT.md` — the parallel read phase this
  one mirrors; its D-01..D-11 define the builder/parser/model/dual-surface/`with_options`
  patterns to replicate for reference data.
- `packages/market-data-client/src/market_data_client/_core.py` — `RequestSpec` +
  `build_market_data_request` / `build_latest_request` builder templates and the
  `parse_market_data_response` collection-guard parser template.
- `packages/market-data-client/src/market_data_client/models.py` — the `SafeModel` / `_coerce`
  base + `MarketDataSnapshot` / `MarketDataEntry` templates to extend (add reference models
  here; `MarketDataEntry` is the no-`received_at` precedent for D-05).
- `packages/market-data-client/src/market_data_client/_params.py` — the `drop_none` helper the
  new builders reuse.
- `packages/market-data-client/src/market_data_client/client.py` + `aio.py` +
  `__init__.py` — the `get_market_data` method/shim/export surface to mirror for the five new
  endpoints (dual sync/async).
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Phase-20 foundation + Phase-21 read surface are done and green** — `market_data_client` has
  working Auth0 auth, sync+async shells, retry transport, redaction logging, `configure()`,
  health, `models.py` (`SafeModel`/`_coerce`), `_params.drop_none`, and `with_options`. This
  phase is purely additive: five more builders, five more parsers, five more models, five more
  method/shim/export triples.
- `_core.py` `RequestSpec` already carries every field the new builders need (`params`,
  `idempotent`, `endpoint_name`, `authenticated`). `build_market_data_request` (authenticated
  GET with `drop_none` filters, `params or None`) is the exact template.
- `parse_market_data_response` is the collection-parser template (body-consume-then-raise +
  `if not resp.content / raw is None: return []`); the reference parsers strip only the
  `received_at` stamp (D-05).
- `_request` in both `client.py`/`aio.py` already branches on `spec.authenticated` (Bearer +
  `_ensure_token`) and threads `request.extensions["max_attempts"]` from `with_options`.
- `models.py` `MarketDataEntry` is the plain-`SafeModel`-without-`received_at` precedent for the
  new reference models (D-05).

### Established Patterns
- `@dataclass(frozen=True, slots=True)` + `from_api(payload)` tolerant deserialization; explicit
  `__all__`; camelCase wire fields (N815-exempt in `models.py`).
- Collections guard 204/None → `[]`; optional API params default to `None`, dropped via
  `drop_none()`.
- Dual sync/async: any logic added to `client.py` must be mirrored in `aio.py`.
- Public method → module-level shim → `__init__.py` re-export, for every new endpoint.

### Integration Points
- New builders + parsers live in `_core.py`; new models appended to `models.py`; new public
  methods on `Client`/`AsyncClient` in `client.py`/`aio.py`; new top-level shims + `__init__.py`
  re-exports (methods + models added to `__all__`).
- No `pyproject.toml` change needed — `models.py` is already N815-exempt.
- No new dependencies; no transport/auth changes.
</code_context>

<specifics>
## Specific Ideas

- Reference-data models are deliberately **unstamped** (no `received_at`, D-05) — the client
  stamp is reserved for staleness-sensitive market data (Phase 21 D-01/D-02); reference
  endpoints have no `max_staleness_seconds` companion to justify it.
- `GET /calendar/config` is modeled as a **single typed object** (D-07), the one non-collection
  endpoint in this phase — everything else returns `list[Model]` with a 204/None → `[]` guard.
</specifics>

<deferred>
## Deferred Ideas

- **`received_at` on reference models** — only if Phase-23 live payloads reveal consumers need
  receipt-time stamping on instruments/symbols/calendar. Additive then, not now (D-05).
- **Explicit boolean/param wire-encoding** (`1/0`, repeated keys, comma-join) — only if Phase-23
  live verification shows the server rejects httpx-native `true/false` or wants multi-valued
  params. Same deferral as Phase 21 D-07 (D-03).
- **Reference-data mutations** — `POST/PATCH /symbols*`, `PUT/POST/DELETE /calendar*` are
  explicitly deferred to v1.5+ (need a mutating-gate); out of scope for this milestone.

### Reviewed Todos (not folded)
- None — no pending todos matched Phase 22.
</deferred>
