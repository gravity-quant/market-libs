# Phase 23: Verificación en vivo contra develop + fixes - Context

**Gathered:** 2026-07-30 (assumptions mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

Exercise the **entire public surface** (sync `client.py` + async `aio.py`) of
`packages/market-data-client/` **live against develop**
(`https://market-data-develop.bbsa.com.ar/api`) with Auth0 client-credentials,
via a new root driver `main_market_data.py`. Detect client-vs-server divergences
(model fields, `received_at`/staleness semantics, param handling) and **fix them
in-cycle, mirrored sync/async**. Document every divergence in
`.planning/verification/market-data-client-findings.md` and reach **cycle closure**
(DRIFT pattern). Requirement: **LIVE-MD-01**.

**Read-only — NO mutating-gate.** The whole surface exercised here (health +
market-data read + reference read) is idempotent.

**Out of scope (do NOT add):** mutations (symbols/calendar writes — v1.5+ MUT-MD-*),
SSE streaming (`/marketdata/stream` — STREAM-MD-01), disk token cache (SEC-MD-01),
JWT signature validation (SEC-MD-02), and the release/publish work (Phase 24).
</domain>

<decisions>
## Implementation Decisions

### Driver structure & gating
- **D-01:** `main_market_data.py` follows the established **4/4-driver convention** with
  **NO `--live` argparse flag**. It gates on the four required Auth0 vars via
  `require_env("market-data-client", ["MARKET_DATA_CLIENT_ID", "MARKET_DATA_CLIENT_SECRET",
  "MARKET_DATA_AUDIENCE", "MARKET_DATA_AUTH0_TOKEN_URL"])`; on any missing var it prints
  the verbatim `SKIPPED market-data-client: missing ...` line and `sys.exit(0)`. The
  source-plan phrase *"split live/offline con `--live`"* is **reconciled against the
  codebase**: the "offline split" is already realized by the `require_env` early-return
  (creds absent → skip). A real `--live` flag would break `main_verify.py`'s SKIPPED
  classification (`main_verify.py:41` `_ENV_SKIP`) and its flag-less subprocess invocation
  (`main_verify.py:61`). `MARKET_DATA_BASE_URL` is **not** required — it defaults to the
  develop target in `client.py:29-30`.
- **D-02:** Driver idioms mirror the existing drivers (`main_ambito_financiero.py` is the
  smallest template): named `probe_*` functions, a frozen `ProbeResult(name, status, detail)`,
  a `_next_fid()` module counter for `F-NN`, **each probe catches its own exceptions**,
  `contextlib.suppress` on client teardown, and **exit 0 unless an unexpected crash**. The
  driver constructs **exactly ONE `Client()` and ONE `AsyncClient()`** and threads them into
  every probe (success-criterion 1).

### Public-surface coverage (probes)
- **D-03:** Exercise **all 10 endpoint methods on BOTH `Client` and `AsyncClient`** (and their
  module-level shims), mirrored: anonymous `get_health` / `get_health_feed`
  (`authenticated=False`), and authenticated `get_market_data`, `get_latest`,
  `get_latest_batch` (POST `LatestRequest` body), `get_instruments`, `get_segments`,
  `get_symbols`, `get_calendar`, `get_calendar_config`. Confirmed on `client.py:352-497` /
  `aio.py:365-511`, shims in `__init__.py:40-101`.
- **D-04:** Probe set covers, per endpoint: **happy-path**, **sync↔async parity** (same result
  from both surfaces), **param-encoding** (boolean filters `active`/`with_data`/`include_expired`/
  `only_outright`/`subscribed` — the Phase-21 D-07 / Phase-22 D-03 live-verification target for
  httpx-native `true`/`false`), **`received_at`/staleness semantics** (Phase-21 D-01/D-02
  reconcile against real payloads), **no-data** (empty/closed-market → NO-DATA, not a crash),
  and **auth-fail**. Model shapes diffed via `diff_safemodel_bidirectional` for every
  `SafeModel` (`MarketDataSnapshot`, `MarketDataEntry`, `Instrument`, `Segment`, `Symbol`,
  `CalendarDay`, `CalendarConfig` — fields per `models.py:118-275`).

### Divergence handling & in-cycle fixes
- **D-05:** Divergences are documented via `append_finding("market-data-client", ...)` using
  **only the seven valid finding classes** — `SHAPE, AUTH, ERROR-MAP, PARAM, SYNC-ASYNC-DRIFT,
  NO-DATA, ANTI-BOT` (closed tuple, `findings.py:76-84`; unknown class → `ValueError`). **No
  new class is invented**: `received_at`/staleness + event-time gaps map to **SHAPE** (surfaced
  by `diff_safemodel_bidirectional` model-only/wire-only), mis-encoded bool/param filters →
  **PARAM**, token/401 anomalies → **AUTH**.
- **D-06:** Fixes are applied **in-cycle**, in `models.py` + the two `_core` parsers
  (`parse_market_data_response` / `parse_latest_response`, `received_at = time.time()` at
  `_core.py:527,548`), and **mirrored sync↔async** (any unmirrored change opens a
  `SYNC-ASYNC-DRIFT` finding by policy). Models are explicitly **PROVISIONAL** (`models.py:19-23`)
  — expect back-and-forth as real develop payloads land; `from_api` tolerance bounds the blast
  radius. Phase-21 D-01/D-02 and Phase-22 D-05 (`received_at` additive-reconcile) apply:
  server-side event-time or reference-model stamping, if revealed, is additive, not a blocker.
- **D-07:** Each **CONFIRMED/FIXED** finding links a **mocked pytest-httpx regression** via the
  `regression="packages/market-data-client/tests/test_*.py::test_name"` field so
  `verify_cycle_closure("market-data-client")` returns **PASS** (structural link check,
  `cycle_report.py:123-176`). Cycle closure PASS is the phase's exit gate (criterion 4).

### Harness integration artifacts
- **D-08:** Four integration artifacts land:
  1. New AST guard `verification/test_main_market_data_uses_single_client_instance.py`
     (asserts `1 ≤ (Client|AsyncClient) ctor calls ≤ 2`), ported mechanically from the ambito
     guard with `_DRIVER = "main_market_data.py"`.
  2. Append `("market-data-client", "main_market_data.py")` to `main_verify.py._DRIVERS`
     (`main_verify.py:28-34`) so the aggregate runner exercises it.
  3. Bootstrap the findings file via `write_findings("market-data-client")` (idempotent) in
     `main()`.
  4. Schema snapshots under `.planning/verification/schemas/market-data-client/` (DRIFT-01
     pattern). `capture`/`anonymize` usage is minimal (read-only; captures gitignored) — used
     only if a payload is snapshotted for a fixture.

### Live-environment access risk
- **D-09:** The driver **degrades gracefully**. Missing creds → `require_env` SKIPPED + exit 0
  (runner classifies SKIPPED, not FAILED). **Network-unreachable develop (VPN/allowlist) and
  closed-market empties must be caught per-probe and classified as NO-DATA / SKIP-equivalent —
  never an uncaught exception that flips the driver to FAILED** in `main_verify.py`. This
  honors the CLAUDE.md live-dependency constraint (results vary by market hours / availability /
  rate limits).

### Claude's Discretion
- Exact probe naming and ordering, and whether the schema-snapshot / no-data / auth-fail probes
  are one-per-endpoint or consolidated — designed from the plan against the real signatures.
- Whether regression tests extend existing `test_*.py` files or land in dedicated new files —
  organize per existing `packages/market-data-client/tests/` conventions.
- The precise plausible-range / sanity assertions inside each probe (à la ambito's `_VENTA_MIN`/
  `_VENTA_MAX`) — pick sensible bounds per field.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.future_plans/market_data.md` § **"Fase 4"** (lines 89-96) — milestone v1.4 source plan for
  this exact live-verification surface. **Source of truth** (note: `--live` phrase reconciled
  per D-01).
- `.planning/REQUIREMENTS.md` → **LIVE-MD-01** (line 25; develop base URL + Auth0 + reuse
  `verification/` + document-and-fix mirrored sync/async).
- `.planning/ROADMAP.md` § "Phase Details (v1.4)" → **Phase 23** (success criteria).
- `.planning/phases/21-market-data-lectura-modelos/21-CONTEXT.md` — D-01/D-02 (`received_at`
  client-stamp + reconcile-here), D-07 (bool param-encoding live target).
- `.planning/phases/22-instruments-symbols-read-calendar-read-modelos/22-CONTEXT.md` — D-03
  (bool param-encoding), D-05 (reference models unstamped, additive-reconcile).
- `main_ambito_financiero.py` — smallest driver template: `ProbeResult`, `_next_fid`,
  per-probe exception isolation, `write_findings`+`append_finding`, schema snapshot, ONE
  `Client()`+`AsyncClient()` construct-and-thread.
- `main_verify.py` — aggregate runner + `_DRIVERS` list to extend (D-08.2) + `_ENV_SKIP`
  contract (D-01).
- `verification/` modules: `env_gate.require_env` (D-01), `findings.py`
  (`write_findings`/`append_finding`/`findings_path`; class tuple `findings.py:76-84`),
  `cycle_report.verify_cycle_closure` (D-07), `safemodel_diff.diff_safemodel_bidirectional`
  (D-04 SHAPE), `schema.schema_of`, `capture`/`anonymize`+`Denylist`, `redaction.safe_print`/
  `redact`.
- `verification/test_main_ambito_financiero_uses_single_client_instance.py` — AST-guard
  template for D-08.1.
- `packages/market-data-client/src/market_data_client/` — the surface under test: `client.py`
  (10 methods @352-497, Auth0 vars @25-30, base_url default @29-30), `aio.py` (@365-511),
  `models.py` (`SafeModel`s @118-275, PROVISIONAL note @19-23), `_core.py`
  (parsers, `received_at` stamp @527,548), `__init__.py` (shims @40-101), `exceptions.py`.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`verification/` harness is complete and battle-tested across 4 packages** — `require_env`,
  `write_findings`/`append_finding` (idempotent, 7 closed classes, OPEN→CONFIRMED→FIXED +
  EXPECTED/NO-FIX), `capture`+`anonymize`+`Denylist` (2-phase PII pipeline → gitignored
  captures/), `schema_of`/schema snapshots (DRIFT-01), `diff_safemodel_bidirectional`
  (duck-typed, cross-package-safe), `verify_cycle_closure` (structural `Regression:` link
  check), `safe_print`/`redact`. All directly importable; **no new harness code needed** beyond
  the per-driver AST guard.
- **Phase 20/21/22 foundation is done and green** — `market_data_client` has Auth0 auth (single
  grant), sync+async shells, retry transport, redaction logging, `configure()`, health, the full
  market-data + reference read surface, `models.py` (7 `SafeModel`s), `_params.drop_none`, and
  `with_options`. This phase adds NO new endpoints — it verifies and reconciles the existing 10.
- Four existing drivers are copy-ready templates; `main_ambito_financiero.py` is the smallest.

### Established Patterns
- Driver = named `probe_*` + `ProbeResult` + `_next_fid` counter; per-probe exception isolation;
  exit 0 unless crash; ONE `Client()`+`AsyncClient()` per `main()` (Phase-15 REFAC-05 AST guard).
- Findings appended idempotently by `fid`; human-promoted statuses (CONFIRMED/FIXED/EXPECTED/
  NO-FIX) never overwritten by re-runs.
- Any client-logic fix mirrored sync↔async (no shared internals by design); model `from_api`
  tolerates partial/None → shape corrections are low-risk, bounded.
- Raw payloads only ever written to gitignored `.planning/verification/captures/`; committed
  fixtures pass through `anonymize` + mandatory human review.

### Integration Points
- New root file `main_market_data.py`; new `verification/test_main_market_data_uses_single_client_instance.py`;
  edit `main_verify.py._DRIVERS`; new `.planning/verification/market-data-client-findings.md`
  (bootstrap) + `.planning/verification/schemas/market-data-client/`.
- Fixes touch `market_data_client/models.py` + `_core.py` parsers (mirrored across
  `client.py`/`aio.py` call sites); regression tests under `packages/market-data-client/tests/`.
</code_context>

<specifics>
## Specific Ideas

- **No `--live` flag** (D-01): the source-plan wording is honored via the existing
  `require_env` offline/skip split, not a new argparse surface — chosen to preserve the
  `main_verify.py` runner contract and 4/4-driver consistency.
- **Auth0 env vars are `MARKET_DATA_CLIENT_ID` / `MARKET_DATA_CLIENT_SECRET` /
  `MARKET_DATA_AUDIENCE` / `MARKET_DATA_AUTH0_TOKEN_URL`** (+ optional `MARKET_DATA_BASE_URL`),
  verbatim from `client.py:25-30` — NOT the `..._AUTH0_CLIENT_ID` spellings the source plan
  implies.
- **Network-unreachable develop and closed-market empties are findings/skips, never crashes**
  (D-09) — a probe that lets `httpx.ConnectError` escape would spuriously flip the aggregate
  runner to FAILED.
</specifics>

<deferred>
## Deferred Ideas

- **Server-provided / dual `received_at`** — if live develop payloads carry an event-time
  timestamp, add it as an additive field then (Phase-21 D-02). Not a blocker; handled as a
  SHAPE finding + additive fix in-cycle if it surfaces.
- **`received_at` on reference models** — only if live payloads reveal consumers need it on
  instruments/symbols/calendar (Phase-22 D-05). Additive then.
- **Explicit boolean/param wire-encoding** (`1/0`, repeated keys, comma-join) — only if live
  verification shows the server rejects httpx-native `true/false` or wants multi-valued params
  (Phase-21 D-07 / Phase-22 D-03). Fix in-cycle as a PARAM finding if confirmed.
- **Mutations / SSE streaming / disk token cache / JWT signature validation** — v1.5+
  (MUT-MD-*, STREAM-MD-01, SEC-MD-01/02); explicitly out of scope.

### Reviewed Todos (not folded)
- None matched Phase 23. (Phase-21's `market-data-client-review-debt.md` IN-01..IN-04 remain
  tracked debt, not blocking LIVE-MD-01.)
</deferred>
