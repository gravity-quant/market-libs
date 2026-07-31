# Phase 21: Market data (lectura) + modelos - Context

**Gathered:** 2026-07-29 (assumptions mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement the **read** surface of market data in `packages/market-data-client/`, on top of
the Phase 20 foundation (Auth0 client_credentials auth, transport with retries, `_request`
with `authenticated` gating, health endpoints). Scope — three endpoints:

- `GET /marketdata` (filters: `market_id, prefix, active, entries, max_staleness_seconds,
  with_data, order, limit, offset`)
- `GET /marketdata/latest` (`symbol, market_id, entries`)
- `POST /marketdata/latest` (batch via a `LatestRequest` request model)

Responses deserialize into frozen `SafeModel` dataclasses with `received_at` as a
first-class field; `with_options(max_retries=N)` parity across sync (`client.py`) and async
(`aio.py`). Requirement: **MD-01**.

**Out of scope (do NOT add):** mutations (symbols/calendar writes), SSE streaming
(`/marketdata/stream`), reference-data endpoints (instruments/segments/symbols/calendar →
Phase 22), live verification (Phase 23). Read-only, no mutating-gate.
</domain>

<decisions>
## Implementation Decisions

### `received_at` semantics
- **D-01:** `received_at` is **client-stamped** — the wall-clock captured in `_core.py` at the
  moment the HTTP response is read, NOT a field parsed from the JSON payload. It is injected
  into each `SafeModel` at parse time, i.e. `from_api(payload, received_at=...)`; the parser
  captures the timestamp ONCE per response and threads it into every constructed model.
- **D-02:** `received_at` is the caller's **local companion** to the server-side
  `max_staleness_seconds` filter — the client owns the stamp. Confirm/reconcile against real
  develop payloads in Phase 23 (Fase 4 already flags "semántica de `received_at`/staleness"
  as a live divergence to reconcile). If the server turns out to also carry an event-time
  timestamp, that is an additive field to consider then — not a blocker now.

### Models (`models.py` — net-new)
- **D-03:** Create `packages/market-data-client/src/market_data_client/models.py` carrying its
  **own copy** of higyrus's `SafeModel` base + `_coerce` helper (per the no-shared-internals
  constraint — do NOT import from another package). Mirror
  `packages/higyrus-client/src/higyrus_client/models.py`.
- **D-04:** Snapshot model is `@dataclass(frozen=True, slots=True)` built via `from_api`, with
  a nested `entries` list model and the `received_at` field (D-01). Wire field names kept
  **camelCase verbatim** from the JSON. Add the module to ruff's `N815` per-file-ignores.
  `from_api` tolerates partial/None/extra keys without raising (bounded blast radius if the
  exact payload shape needs adjusting in Phase 23).
- **D-05:** `LatestRequest` is a typed **request** dataclass (the one schema the OpenAPI does
  define), serialized to the `POST /marketdata/latest` `json_body`.

### Endpoint builders + param serialization (`_core.py`)
- **D-06:** Add three pure builders to `_core.py`: `build_market_data_request`,
  `build_latest_request`, `build_latest_batch_request`, each returning
  `RequestSpec(authenticated=True, idempotent=True)`. `authenticated=True` (vs health's
  `authenticated=False`) triggers Bearer injection in `_request`; GET reads are idempotent →
  retry-eligible.
- **D-07:** GET filters passed as `params=` with `None`-valued optionals dropped via a new
  `drop_none` helper (new `_params.py`, mirroring `higyrus_client/_params.py`). Booleans
  (`active`, `with_data`) rely on httpx's native `True→"true"` param encoding for now — this
  is a Phase-23 verification target (see Claude's Discretion below).

### `with_options` parity + folded Phase-20 debt
- **D-08:** `with_options(max_retries=N)` does not exist in `market-data-client` yet — add it
  to BOTH `Client` and `AsyncClient` via iol's Phase-13 **shared-view-clone** pattern:
  `_max_retries` + `_is_view` in `__slots__`, `max_retries` `__init__` kwarg with
  `_validate_max_retries`, shallow-clone `with_options` sharing `_state`, view-aware
  `close()`/`aclose()` no-ops, and thread `request.extensions["max_attempts"] =
  self._max_retries + 1` into `_request`/`_send_auth_request`. Analog:
  `packages/iol-client/src/iol_client/client.py`. **Note:** current
  `market_data_client/client.py` builds requests WITHOUT any `max_attempts` extension — if
  that threading is skipped, `with_options` is a silent no-op (fails success criterion 3).
- **D-09:** **Fold in WR-04** (deferred Phase-20 debt): align async header precedence to sync
  so the **token/Authorization header WINS** over `spec.headers` in both surfaces. (Sync sets
  `Authorization` after spreading `spec.headers`; async currently lets `spec.headers` win —
  wrong once authenticated endpoints exist, since a stray spec header would shadow the fresh
  token.)
- **D-10:** **Fold in the 401 test gap** (deferred Phase-20 debt): add permanent regression
  tests for the authenticated `401 → clear token → re-auth once → retry → succeed` path AND
  the persistent-401 re-raise path, for BOTH sync and async surfaces.

### Test strategy
- **D-11:** Mocked tests via **pytest-httpx** cover: query-param serialization for every
  `GET /marketdata` filter + `GET /marketdata/latest`, `LatestRequest` batch body,
  `from_api` partial/None tolerance, `received_at` client-stamping, `with_options` retry
  propagation (sync+async), and the D-10 401 sequences. All four CI gates (ruff / format /
  mypy strict / pytest) green.

### Claude's Discretion
- Exact endpoint method names (`get_market_data` / `get_latest` / `get_latest_batch` are the
  roadmap's suggestion — "o nombres equivalentes"); pick names consistent with the existing
  package surface.
- Exact model class/field naming and the nested-entries shape — designed from the plan, with
  `from_api` tolerance absorbing shape corrections in Phase 23.
- Boolean/`entries` param wire-encoding (httpx-native `true`/`false` vs `1/0` vs repeated
  keys): default to httpx-native now; treat as an explicit Phase-23 live-verification target
  since mocked tests can't catch a server silently ignoring a mis-encoded filter.

### Folded Todos
- **`market-data-client-review-debt.md`** — folded WR-04 (→ D-09) and the authenticated-401
  re-auth test gap (→ D-10), both tagged `resolves_phase: 21` in the todo. Remaining items
  (IN-01..IN-04) stay deferred — see Deferred Ideas.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.future_plans/market_data.md` — milestone v1.4 source plan; D-locks (D-01..D-07) and the
  **"Fase 2"** section describing this exact surface. **Source of truth.**
- `.planning/REQUIREMENTS.md` → **MD-01** (acceptance criteria for this phase).
- `.planning/ROADMAP.md` § "Phase Details (v1.4)" → **Phase 21** (success criteria, lines
  ~120-133).
- `packages/market-data-client/src/market_data_client/` — the Phase-20 foundation this phase
  extends: `_core.py` (`RequestSpec` + builder templates), `client.py` / `aio.py`
  (`_request`, `_ensure_token`, health), `_state.py`, `exceptions.py`, `__init__.py`.
- `packages/higyrus-client/src/higyrus_client/models.py` — `SafeModel` + `_coerce` template
  to mirror (copy, do NOT import). `packages/higyrus-client/src/higyrus_client/_params.py` —
  `drop_none` template.
- `packages/iol-client/src/iol_client/client.py` — `with_options` shared-view-clone pattern
  (Phase 13) to mirror for both surfaces.
- `.planning/todos/pending/market-data-client-review-debt.md` — WR-04 (D-09) + authenticated
  401 re-auth test gap (D-10).
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Phase-20 foundation is done and green** — `market_data_client` already has working Auth0
  auth, sync+async shells, retry transport, redaction logging, exceptions, `configure()`, and
  health. This phase is purely additive on that base.
- `_core.py` `RequestSpec` already carries every field the new builders need (`params`,
  `json_body`, `data`, `idempotent`, `endpoint_name`, `headers`, and the net-new
  `authenticated: bool`). `build_health_request` is the builder template (it sets
  `authenticated=False`; market-data sets `authenticated=True`).
- `_request` in both `client.py`/`aio.py` already branches on `spec.authenticated` (Bearer
  injection + `_ensure_token` only when authenticated; health carve-out fires first).
- higyrus `models.py` (`SafeModel`/`_coerce`) and `_params.py` (`drop_none`) are copy-ready
  templates. iol `client.py` is the `with_options` clone template.

### Established Patterns
- `@dataclass(frozen=True, slots=True)` + `from_api(payload)` tolerant deserialization;
  explicit `__all__`; camelCase wire fields with N815 ruff exemption.
- Dual sync/async: any logic added to `client.py` must be mirrored in `aio.py` (known
  duplication debt — no shared internals by design).
- Optional API params default to `None`, dropped via `drop_none()` before the request.
- `with_options(...)` returns a shallow shared-view clone (shares `_state`), never a deep copy
  (iol Phase-13 pattern).

### Integration Points
- New builders live in `_core.py`; new public methods on `Client`/`AsyncClient` in
  `client.py`/`aio.py`; new `models.py` + `_params.py`; `__init__.py` re-exports (models +
  `LatestRequest` + new methods surfaced per package convention).
- `pyproject.toml` ruff config: add `models.py` to N815 per-file-ignores.
- WR-04 alignment touches the header-merge logic in both `_request` implementations.
</code_context>

<specifics>
## Specific Ideas

- `received_at` is **client-stamped at receipt time**, captured once per response and threaded
  into every model (D-01/D-02) — this is the user's explicit call, chosen over server-provided
  or dual-timestamp variants.
- WR-04 alignment must make the **token win** (not `spec.headers`) — aligning sync→async the
  other way would let a stray spec header shadow the fresh token.
</specifics>

<deferred>
## Deferred Ideas

- **Server-provided / dual `received_at`** — if Phase-23 live payloads reveal a server
  event-time timestamp, consider adding it as an additive field then. Not now.
- **Explicit boolean/`entries` param encoding** (`1/0`, repeated keys, comma-join) — only if
  Phase-23 live verification shows the server rejects httpx-native `true`/`false` or wants
  multi-valued `entries`.

### Reviewed Todos (not folded)
- **`market-data-client-review-debt.md` IN-01..IN-04** (INFO-level, from the same todo):
  `configure(http_client=...)` sync/async asymmetry (IN-01), `RedactingFilter` handler-scope
  documentation (IN-02), `assert`-based narrowing stripped under `python -O` (IN-03),
  unguarded `resp.json()` dict assumptions (IN-04). Not blocking MD-01; left as tracked debt.
</deferred>
