# Phase 26: Calendar write - Context

**Gathered:** 2026-07-31 (assumptions mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

Extend `market-data-client` with the **second mutation surface** — calendar write — behind
the SAME mutating-gate built in Phase 25. One requirement:

- **MUT-MD-02** — calendar write: `set_calendar_config` (`PUT /calendar/config`,
  `MarketHoursIn`), `delete_calendar_config` (`DELETE /calendar/config`),
  `preview_calendar_config` (`POST /calendar/config/preview`, `MarketHoursIn`),
  `add_holidays` (`POST /calendar/holidays`, `HolidaysIn`), `delete_holiday(day)`
  (`DELETE /calendar/holidays/{day}`) — typed request models, sync + async, all behind
  the gate, with the server's `confirm` guardrail explicitly exposed and defaulting to
  `False`.

The gate mechanics themselves are DONE (Phase 25, GATE-MD-01) — this phase consumes them
unchanged. Live verification is **Phase 27**, release is **Phase 28** — both OUT of scope.

**IN scope:** 5 `_core` builders + parsers, 3 request models (`MarketHoursIn`/`HolidayIn`/
`HolidaysIn`), 5 methods × 2 shells + module shims + `__init__` re-exports, mocked tests
(gate, serialization, defaults, `confirm`, `422`, no-retry, parity), 4 green gates.
**OUT of scope:** any change to the gate itself, live verification, version bump/release,
and the pre-existing `get_calendar` read-surface bug (see D-16 / Deferred).
</domain>

<decisions>
## Implementation Decisions

### A. Builders + routing (`_core.py`)

- **D-01:** Add **five** pure builders to `_core.py` mirroring the Phase-25 symbols
  builders (`del state`, already-serialized `json_body` passed in):
  `build_set_calendar_config_request` (`PUT /calendar/config`),
  `build_delete_calendar_config_request` (`DELETE /calendar/config`),
  `build_preview_calendar_config_request` (`POST /calendar/config/preview`),
  `build_add_holidays_request` (`POST /calendar/holidays`),
  `build_delete_holiday_request` (`DELETE /calendar/holidays/{day}`).
  All `authenticated=True`, each with a distinct `endpoint_name`.
- **D-02:** `RequestSpec` needs **no structural change** (Phase-25 D-06 holds). The two
  DELETE builders simply leave `json_body=None`; verified against the pinned httpx 0.28.1
  that `build_request("DELETE", url, json=None)` emits no body and no `Content-Type`.
  `build_segments_request` is the zero-kwarg template; `build_update_symbol_request` is
  the path-param template.
- **D-03:** `day` is interpolated **RAW** into `/calendar/holidays/{day}` — no
  `urllib.parse.quote()`. The live OpenAPI declares the path param as
  `{"type":"string","format":"date"}` (ISO `YYYY-MM-DD`), so the D-08 `"DLR/DIC26"`
  encoding risk does not apply here.
- **D-04:** Idempotency per DM-03 — `idempotent=True` for `PUT /calendar/config`,
  `DELETE /calendar/config`, `POST /calendar/config/preview` (compute-only) and
  `DELETE /calendar/holidays/{day}`; **`idempotent=False` for `POST /calendar/holidays`**
  (append is not idempotent). Revalidated live in Phase 27.

### B. Return types + parsers

- **D-05:** `set_calendar_config`, `delete_calendar_config` and `preview_calendar_config`
  return the existing typed **`CalendarConfig`**, reusing the existing
  `_core.parse_calendar_config_response` unchanged. Rationale: the three operate on the
  same config resource whose real develop wire shape is already captured and already
  matches `CalendarConfig` field-for-field; the model even carries `warnings`, which is
  exactly what the OpenAPI ties `confirm` to.
- **D-06:** `add_holidays` and `delete_holiday` return **`dict[str, Any]`** via a
  passthrough parser in the `parse_health_response` style. They must **NOT** reuse
  `parse_calendar_response` nor return `list[CalendarDay]` — that model/parser pair is
  broken against the real wire (see D-16).
- **D-07:** All new parsers keep the package's body-consume-then-raise order
  (`resp.read()` → `raise_for_response(resp)` → decode) and stay tolerant of an
  empty/`null` body (`CalendarConfig.from_api(None)` for the config trio; `{}` for the
  holiday pair). Response shapes are unverified against the live server by design —
  tolerance is the hedge until Phase 27.

### C. Request models (`models.py`)

- **D-08:** Model `MarketHoursIn`, `HolidayIn`, `HolidaysIn` as frozen
  `@dataclass(frozen=True, slots=True)` — **NOT** `SafeModel` subclasses (they serialize
  OUTWARD), each with a hand-written `to_dict()`, exactly per Phase-25 D-09.
- **D-09:** `confirm` is a **field of `MarketHoursIn`** (`confirm: bool = False`), always
  emitted on the wire — not a separate keyword-only method parameter. Method signature
  stays model-only: `set_calendar_config(config: MarketHoursIn)`. This satisfies ROADMAP
  criterion 2 (`confirm` exposed with default `False`) and matches the `NewSymbol.market_id`
  defaulted-and-always-emitted precedent (Phase-25 D-10).
- **D-10:** Field defaults follow the live OpenAPI verbatim: `MarketHoursIn` requires
  `open_time`/`close_time`/`timezone` and defaults `pre_open_minutes=10`, `enabled=True`,
  `updated_by=""`, `confirm=False`. `HolidayIn` requires `day` and defaults `closed=True`,
  `open_time=None`, `close_time=None`, `description=""`.
- **D-11:** `to_dict()` routes through `_params.drop_none` (ROADMAP criterion 3). Effect:
  `HolidayIn.open_time`/`close_time` are **dropped when `None`**, while `closed=True` and
  `description=""` are **always emitted** (`drop_none` preserves falsy-but-not-`None`).
  `MarketHoursIn.to_dict()` routes through it too even though it is a no-op there (no
  nullable fields) — consistency. `HolidaysIn.to_dict()` →
  `{"days": [d.to_dict() for d in self.days]}`.

### D. Validation

- **D-12:** Enforce the `HolidaysIn.days` **1–500** bound client-side in
  `__post_init__`, raising a plain **`ValueError`** — an exact mirror of the `NewSymbols`
  check (Phase-25 D-11). The live OpenAPI declares `days: {minItems: 1, maxItems: 500}`;
  the source plan omitted this bound.
- **D-13:** Scalar field bounds are **NOT** validated client-side — `pre_open_minutes`
  (0–120), `timezone` (1–64), `updated_by` (≤200), `description` (≤500), and the
  `HH:MM` time format all go to the server's `422` via the existing `raise_for_response`.
  This matches the real Phase-25 precedent: `NewSymbol.symbol` has a declared 1–255 bound
  that Phase 25 deliberately did not enforce. A client-side `HH:MM` regex would also risk
  false negatives (the OpenAPI uses `format: time`, which admits `"10:00:00"`).

### E. Gate, parity, and the no-retry proof

- **D-14:** `_ensure_mutation_allowed()` is the **literal first statement** of all five
  new methods on both shells — before spec build, before any token fetch, before any
  transport touch (Phase-25 D-04/D-05, AST-verified). `preview_calendar_config` is
  compute-only and does not persist, but it is a POST and therefore **still passes
  through the gate** — this read-safe exception is documented, not carved out.
- **D-15:** Phase 26 must add the **first dispatch-level `idempotent=False` no-retry
  test** in this package: `add_holidays` against a repeated 503 must emit **exactly one**
  outgoing request. Phase 25 never exercised this path (all three symbols builders are
  `idempotent=True`), and the package's existing `idempotent` assertions are builder-level
  only (`tests/test_core.py`). If a contrasting `idempotent=True` positive control is
  included, use the `monkeypatch.setattr(time, "sleep", ...)` pattern from
  `tests/test_transport.py` to avoid real jitter sleeps.
- **D-16:** Phase 26 does **NOT** fix the pre-existing `get_calendar` / `CalendarDay` /
  `parse_calendar_response` envelope bug (Phase-22 read surface, now proven — see
  Deferred). It only avoids inheriting it (D-06) and records it as a Phase-27 finding.
  This mirrors how Phase 25 disposed of the analogous WR-01 read-path bug.
- **D-17:** Mirror every method, model, shim and export across `client.py` AND `aio.py`
  identically; module-level sync shims delegate to `_get_default()`, async shims stay
  under `aio`; add the three models to `models.py` `__all__` and re-export everything
  through `__init__.py` `__all__`. Parity is enforced by the in-package
  `tests/test_public_surface_market_data.py` (Phase-25 D-15/D-16).

### Claude's Discretion

- Exact builder/parser/helper naming beyond the DM-locked public method names
  (`set_calendar_config`, `delete_calendar_config`, `preview_calendar_config`,
  `add_holidays`, `delete_holiday`); test file organization (whether calendar-write tests
  live in new `test_calendar_write.py` / `test_calendar_write_async.py` files mirroring
  `test_symbols_write*.py`, or extend existing ones); whether the two holiday passthrough
  parsers are one shared function or two.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Source plan + requirements (locked scope)
- `.planning/future-plans/market_data_mutations.md` — milestone source plan: calendar
  endpoint table, request schemas, DM-01…DM-08 locks (esp. DM-03 idempotency, DM-04
  typed request models, DM-05 sync/async mirroring).
  **Note:** its `HolidaysIn = { days: [HolidayIn] (req) }` line is incomplete — the live
  OpenAPI declares `minItems: 1, maxItems: 500` (D-12).
- `.planning/REQUIREMENTS.md` — MUT-MD-02 acceptance text.
- `.planning/ROADMAP.md` — Phase 26 goal + 5 success criteria.
- `.planning/phases/25-mutating-gate-symbols-write/25-CONTEXT.md` — the locked gate +
  request-model + parity decisions this phase mirrors (D-04/D-05, D-09/D-10, D-11,
  D-13/D-14, D-15/D-16).

### Live API contract (fetched 2026-07-31, reachable from this machine)
- `https://market-data-develop.bbsa.com.ar/api/openapi.json` — NOT vendored in the repo;
  re-fetch if needed. Confirmed: `MarketHoursIn`/`HolidayIn`/`HolidaysIn` field sets,
  defaults and bounds; `day` path param `format: date`; `confirm` described as
  *"Required when the change produces warnings. See POST /calendar/config/preview"*;
  all five calendar-write 200 responses declared as bare `object`
  (`additionalProperties: true`) — i.e. no server-declared response shape.
- `.planning/verification/schemas/market-data-client/get-calendar-config.json` — the REAL
  captured config wire shape backing D-05.
- `.planning/verification/schemas/market-data-client/get-calendar.json` — the REAL
  captured `GET /calendar` envelope backing D-06 and D-16.

### Package to extend (market-data-client v0.2.0)
- `packages/market-data-client/src/market_data_client/_core.py` — Phase-25 symbols write
  builders (`build_create_symbol_request` / `build_create_symbols_request` /
  `build_update_symbol_request`) = the direct template; `build_segments_request` =
  zero-kwarg template; `parse_calendar_config_response` (reuse per D-05);
  `parse_health_response` (dict passthrough precedent per D-06);
  `parse_calendar_response` (**broken** — do not reuse, D-16); `RequestSpec`;
  `raise_for_response` (422 mapping).
- `packages/market-data-client/src/market_data_client/client.py` — sync shell:
  `_ensure_mutation_allowed`, the three Phase-25 mutation methods, `_request` /
  `request.extensions["idempotent"]` threading, module-level shims.
- `packages/market-data-client/src/market_data_client/aio.py` — async mirror.
- `packages/market-data-client/src/market_data_client/models.py` — `SafeModel`, `_coerce`,
  Phase-25 request models + `to_dict()`, `CalendarConfig` (reconciled, reuse),
  `CalendarDay` (**wrong shape** — do not reuse, D-16).
- `packages/market-data-client/src/market_data_client/_params.py` — `drop_none`
  (preserves falsy-but-not-`None`).
- `packages/market-data-client/src/market_data_client/_transport.py` /
  `_atransport.py` — the falsy-`idempotent` short-circuit before the tenacity loop (D-15).
- `packages/market-data-client/src/market_data_client/exceptions.py`,
  `__init__.py` — error hierarchy + `__all__` re-exports.

### Test templates to mirror
- `packages/market-data-client/tests/test_symbols_write.py` /
  `test_symbols_write_async.py` — mutation-method test shape incl. `422` → typed error.
- `packages/market-data-client/tests/test_mutation_gate.py` — adversarial gate tests
  (zero HTTP + zero Auth0 round-trip on refusal).
- `packages/market-data-client/tests/test_public_surface_market_data.py` — export/parity net.
- `packages/market-data-client/tests/test_transport.py` — the `monkeypatch` sleep pattern.
- `packages/iol-client/tests/test_transport.py` — the only existing dispatch-level
  non-idempotent no-retry test in the monorepo (other package; pattern reference for D-15).

### Conventions
- `.planning/codebase/CONVENTIONS.md`, `.planning/codebase/STRUCTURE.md`
- `./CLAUDE.md` — dual sync/async mirroring rule, mypy-strict, credential redaction.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- The **entire gate** is already built and AST-verified (Phase 25): `_ensure_mutation_allowed`,
  `mutating_allowed` + `expected_host` on the shared `_ClientState`, the
  `MarketDataMutationNotAllowedError` type, `configure()` params, and free inheritance into
  `with_options` views. Phase 26 consumes it with zero gate changes.
- `parse_calendar_config_response` + `CalendarConfig` — already reconciled against the real
  develop wire; reusable verbatim for the config trio (D-05).
- `parse_health_response` — the `dict[str, Any]` passthrough precedent (D-06).
- The three Phase-25 symbols builders + request models + their tests — near-line-for-line
  templates for the five calendar builders and three calendar models.
- `_params.drop_none` — already imported in the package; first real *request-model* use is
  `HolidayIn`'s nullable time pair (D-11).
- `NewSymbols.__post_init__` 1–500 `ValueError` — exact template for `HolidaysIn` (D-12).

### Established Patterns
- `_core.py` is PURE / IO-free; builders `del state`. Gate/policy checks live only in the
  stateful shell.
- Uniform shell method shape: `_ensure_mutation_allowed()` → `spec = _core.build_x(...)` →
  `resp = self._request(spec)` → `parse`.
- Request models serialize OUT (frozen dataclass + `to_dict()`); response models deserialize
  IN (tolerant `SafeModel.from_api`).
- Every logic change mirrored sync + async; parity enforced by the in-package public-surface
  test (the cross-package nets exclude this package).

### Integration Points
- New public methods ×5 on both shells + module shims; five `_core` builders + parsers;
  three request models in `models.py`; all re-exported via `__init__.py` `__all__`.
- No new exception type, no `_ClientState` change, no transport change.
</code_context>

<specifics>
## Specific Ideas

- **`confirm` is a second opinion, not a force flag.** The OpenAPI's own words: it is
  required only when the proposed window is legal but suspicious; anything genuinely
  impossible is a `422` that no amount of confirming gets past. The intended workflow is
  `preview_calendar_config(...)` → inspect `warnings` → re-issue with `confirm=True`.
  Default `False` is load-bearing (ROADMAP criterion 2).
- **`preview` goes through the gate anyway.** It is compute-only and does not persist, so
  it is morally a read — but it is a POST, and carving it out would create a second,
  weaker path into the mutation surface. Document the exception; do not implement it.
- **The holiday endpoints must not be typed against `CalendarDay`.** Doing so would ship
  methods that return silently-empty objects against the real server while the mocked
  tests stay green (the mocks would encode the same wrong shape), surfacing only in
  Phase 27 — where fixing it would be a public return-type change immediately before the
  v0.3.0 publish.
</specifics>

<deferred>
## Deferred Ideas

**Pre-existing read-surface bug — record as a Phase-27 finding, do NOT fix here (D-16):**
- `GET /calendar` really returns a dict envelope `{config, coverage, days[], market}`, but
  `_core.parse_calendar_response` iterates `raw` as a list — so it iterates the envelope's
  **keys** and yields four all-default `CalendarDay` objects. Compounding it, `CalendarDay`'s
  fields (`date`/`marketId`/`isBusinessDay`) do not exist on the wire, whose `days[]` items
  are `{day, closed, open_time, close_time, description}` — i.e. the `HolidayIn` shape.
  Proven by `.planning/verification/schemas/market-data-client/get-calendar.json`. The
  Phase-23 live probe never flagged it because `main_market_data.py` only emits a shape
  finding when the payload is a `list`. This is Phase-22 code outside MUT-MD-02's boundary,
  and it is the natural verification path for `add_holidays` — so Phase 27 should fix it
  alongside the already-carried WR-01 `parse_latest_response` envelope gap, before Phase 28
  publishes v0.3.0.

**Confirm live against develop in Phase 27 (LIVE-MUT-01):**
- The concrete 200 body of each of the five calendar-write endpoints. The live OpenAPI
  declares them all as bare `object` with no schema, so D-05's `CalendarConfig` typing and
  D-06's `dict[str, Any]` are evidence-based bets, not contracts. Tolerant parsers (D-07)
  are the hedge.
- Real server-side idempotency of `PUT /calendar/config` and `DELETE /calendar/holidays/{day}`
  (DM-03 assigns `idempotent=True` on HTTP-semantics grounds only), and whether
  `POST /calendar/holidays` is genuinely non-idempotent as assumed (D-04).
- Whether the server accepts `"HH:MM"` only or also `"HH:MM:SS"` for `open_time`/`close_time`
  (`format: time`), and the real effect of dropping vs. sending `null` for a holiday's
  time overrides (D-11).

**Out of scope of this milestone (backlog v2):** SSE streaming (STREAM-MD-01), Auth0 token
disk cache (SEC-MD-01), JWT signature validation (SEC-MD-02) — per DM-08.

### Reviewed Todos (not folded)
None — no pending todos matched Phase 26 scope.
</deferred>

---

*Phase: 26-calendar-write*
*Context gathered: 2026-07-31 via assumptions mode*
