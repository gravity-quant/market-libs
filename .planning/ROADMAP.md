# Roadmap: market-libs — Verificación en vivo de clientes

## Overview

This is a live-API verification cycle, not a product build. The journey climbs a risk/complexity curve: first build the safety harness that every live run depends on (credential gating, mutation gating, redaction, the `@pytest.mark.live` marker, the classified findings format, and the live-payload→regression-fixture pipeline), then verify each of the four clients end-to-end in ascending order of risk — Ámbito (no auth, smallest surface) → IOL (highest silent-shape risk) → Higyrus (SafeModel false-pass trap) → Matriz (largest surface, only destructive endpoints, last for maximum caution). Each client phase is a vertical slice: exercise the full public surface live → classify every discrepancy in a findings file → fix each confirmed bug in `client.py` AND `aio.py` (Matriz is sync-only) → lock each fix with a mocked regression test → commit a structural schema snapshot. The cycle is done when all four clients are verified, every confirmed bug is fixed with a passing mocked regression test, and the findings + snapshots are committed.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Safety Harness & Verification Infrastructure** - Credential/mutation gating, redaction, live marker, classified findings format, payload→fixture pipeline, schema-snapshot tooling (completed 2026-05-28)
- [x] **Phase 2: Ámbito Verification** - Verify the no-auth FX client end-to-end; validate the driver→finding→fix→regression loop at minimum risk; establish schema snapshots (completed 2026-06-05)
- [x] **Phase 3: IOL Verification** - Verify the raw-dict client end-to-end (highest silent-shape risk); implement the refresh_token fix (completed 2026-06-06)
- [x] **Phase 4: Higyrus Verification** - Verify the SafeModel client end-to-end via raw-payload diffing (false-pass trap) (completed 2026-06-08)
- [ ] **Phase 5: Matriz Verification** - Verify the largest, sync-only surface against remarkets; mock-only order mutation; per-package closing report

## Phase Details

### Phase 1: Safety Harness & Verification Infrastructure

**Goal**: Every safety convention and piece of verification plumbing is in place and proven so that no live API can be touched unsafely — credentials never leak, mutations never fire by accident, and every later phase has a ready findings format, a live-payload→fixture pipeline, and an offline-clean test marker.
**Mode:** mvp
**Depends on**: Nothing (first phase)
**Requirements**: HARN-01, HARN-02, HARN-03, HARN-04, HARN-05, HARN-06
**Success Criteria** (what must be TRUE):

  1. Running any `main_*.py` driver with missing env vars prints a loud, specific `SKIPPED <pkg>: missing X, Y` line and exits cleanly without blocking the other drivers (HARN-01)
  2. Matriz order mutations are unreachable by default: they run only when `VERIFY_MUTATING=1` AND the resolved base URL is asserted to contain `remarkets`; otherwise a `SKIPPED (mutating, guard off)` line is printed (HARN-02)
  3. A redaction helper is wired into all driver output so tokens, passwords, and auth values can never be printed in full (only a redacted prefix), and credential globals are never echoed (HARN-03)
  4. `@pytest.mark.live` is registered in the root `conftest.py` with a `--live` flag that excludes live tests by default, keeping CI fully offline and deterministic (HARN-04)
  5. The classified findings format (`.planning/verification/<pkg>-findings.md`, with classes SHAPE/AUTH/ERROR-MAP/PARAM/SYNC-ASYNC-DRIFT/NO-DATA/ANTI-BOT and an ART run-context timestamp) and the live-payload→PII-anonymized regression-fixture pipeline both exist and are documented for the client phases to consume (HARN-05, HARN-06)

**Plans**: 4 plansPlans:
**Wave 1**

- [x] 01-01-PLAN.md — Live-test marker (--live, deselect-by-default) + redaction helpers (HARN-03, HARN-04) [wave 1]
- [x] 01-02-PLAN.md — Env gate (require_env) + Matriz mutation gate (mutating_allowed) (HARN-01, HARN-02) [wave 1]
- [x] 01-04-PLAN.md — Schema snapshot + capture→anonymize→fixture pipeline + findings template (HARN-05, HARN-06) [wave 1]

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 01-03-PLAN.md — Wire gating/redaction into all 5 drivers + aggregate runner main_verify.py (HARN-01, HARN-02, HARN-03) [wave 2]

### Phase 2: Ámbito Verification

**Goal**: The Ámbito FX client is fully verified end-to-end against the live public API on both sync and async surfaces, proving the entire driver→finding→fix→regression loop on the lowest-risk target, with the first structural schema snapshot committed and any confirmed bug fixed with a mocked regression test.
**Mode:** mvp
**Depends on**: Phase 1
**Requirements**: AMB-01, AMB-02, AMB-03, AMB-04, AMB-05, AMB-06, DRIFT-01
**Success Criteria** (what must be TRUE):

  1. A real `get_dollar_banco_nacion` call succeeds with the current User-Agent on both sync and async surfaces, with structurally-equal results, and the raw payload is retained as the expected `list[list[str]]` shape (AMB-01, AMB-03, AMB-05)
  2. `parse_ar_decimal` is verified against the real `"1.415,00"` format using adversarial values ≥ 1000, surfacing a finding if the server ever emits a dot-decimal `1415.00` (×100 corruption), and the emitted URL date format is confirmed accepted with a day > 12 sample (AMB-02, AMB-03)
  3. `NoDataError` is confirmed to fire for a date with no quotation, and the anti-bot probe confirms the correct UA passes while a deliberately-wrong UA reproduces the 403 without looping (AMB-04, AMB-06)
  4. Every discrepancy is classified in `.planning/verification/ambito-findings.md` and a committed structural schema snapshot (keys + types, not values) exists for the verified endpoint (DRIFT-01)
  5. Each confirmed bug is fixed in both `client.py` and `aio.py` with a paired mocked regression test (`Regression: ... (issue #NNN)`) and the full mocked suite + mypy strict + ruff pass green

**Plans**: 3 plans

**Wave 1**

- [x] 02-01-PLAN.md — Extend verification/findings.py with append_finding helper (D-10) + barrel re-export + helper tests (DRIFT-01 DRY foundation for Phases 3-5) [wave 1]

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 02-02-PLAN.md — Rewrite main_ambito_financiero.py with 7 named probes + summary (AMB-01..06 driver) [wave 2]

**Wave 3** *(blocked on Waves 1-2 completion; contains human checkpoint)*

- [x] 02-03-PLAN.md — Append Verified-live (Phase 2) invariants + Regressions section to test_client.py/test_async_client.py + live driver run + commit DRIFT-01 baseline schema + Phase 2 findings file (AMB-01..05, DRIFT-01) [wave 3]

### Phase 3: IOL Verification

**Goal**: The IOL client — the highest silent-shape risk in the codebase (raw `dict`, zero validation) — is fully verified end-to-end on both surfaces with retained payloads and an observed field→type map, the auth and 401 paths are confirmed without lockout risk, and the known `refresh_token` bug is fixed in both surfaces with regression tests.
**Mode:** mvp
**Depends on**: Phase 2
**Requirements**: IOL-01, IOL-02, IOL-03, IOL-04, IOL-05, IOL-06, IOL-07
**Success Criteria** (what must be TRUE):

  1. The auth flow (`login()` + lazy-auth on first call) is verified live on both surfaces with auth-once discipline (no `configure()` mid-loop, fail-fast on auth error), and the full read surface — `get_quote`, `get_historical_quotes`, `get_instruments`, `get_instruments_by_type` — is exercised sync and async with raw payloads retained (IOL-01, IOL-02)
  2. A field→observed-type map is built from the live payloads and compared against caller assumptions, confirming the `["titulos"]` envelope key is present, the historical date-path format is accepted, and numeric fields arrive as JSON numbers (not strings) (IOL-03, IOL-04)
  3. The 401 error path is confirmed live with bad credentials mapping to the typed exception, and structural sync↔async parity is confirmed for every endpoint (IOL-05, IOL-06)
  4. `grant_type=refresh_token` with password-grant fallback is implemented in both `client.py` and `aio.py`, with tests covering both successful refresh and fallback (IOL-07)
  5. Every discrepancy is classified in `.planning/verification/iol-findings.md`, a schema snapshot is committed, and each confirmed bug is fixed in both surfaces with paired mocked regression tests; the mocked suite + mypy strict + ruff pass green

**Plans**: 3 plans

**Wave 1**

- [x] 03-01-PLAN.md — IOL-07 fix dual sync+async: `_refresh_token` + `_refresh()`/`_refresh_unlocked()` + `_ensure_token` fallback + 4+4 mocked regression tests por surface (IOL-07) [wave 1]

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 03-02-PLAN.md — Rewrite main_iol.py with 15 named probes (IOL-01..04 + IOL-06 driver + IOL-07 in-vivo) [wave 2]

**Wave 3** *(blocked on Waves 1-2 completion; contains human checkpoint)*

- [x] 03-03-PLAN.md — Append Verified-live (Phase 3) invariants to test_client.py/test_async_client.py + live driver run + commit DRIFT-01 mirror baseline (4 schemas + Phase 3 findings file) (IOL-01..06 lock + DRIFT-01 mirror) [wave 3]

### Phase 4: Higyrus Verification

**Goal**: The Higyrus client is fully verified end-to-end on both surfaces using mandatory raw-payload diffing against declared model fields (defeating the `SafeModel.from_api` false-pass trap), with the known async `drop_none` deviation confirmed or denied, error and empty-data paths verified, account data anonymized in fixtures, and each confirmed bug fixed in both surfaces with regression tests.
**Mode:** mvp
**Depends on**: Phase 3
**Requirements**: HIGY-01, HIGY-02, HIGY-03, HIGY-04, HIGY-05, HIGY-06, HIGY-07
**Success Criteria** (what must be TRUE):

  1. The auth flow (login + lazy-auth) is verified live on both surfaces, and `get_health`, `get_listado_cuentas`, `get_movimientos`, `get_posicion_valuada`, `get_posiciones` are exercised sync and async with raw payloads retained (HIGY-01, HIGY-02)
  2. Each endpoint's raw `resp.json()` is diffed bidirectionally against the model's declared fields (`get_type_hints`) — flagging both wire keys the model ignores and model fields the wire drops — so a non-raising `from_api` never counts as a pass (HIGY-03)
  3. The `assert isinstance(raw, list/dict)` behavior is verified live and flagged as a candidate fix to a typed `HigyrusAPIError`, the `"errors"`-key error path is confirmed on a bad request, and empty/204 responses yield an empty list (not crash, not `None`) (HIGY-04, HIGY-05, HIGY-07)
  4. Sync↔async parity is verified, including the known `drop_none` deviation in the async `_request`, which is confirmed or denied (HIGY-06)
  5. Every discrepancy is classified in `.planning/verification/higyrus-findings.md` with account data anonymized before any fixture is committed, a schema snapshot is committed, and each confirmed bug is fixed in both surfaces with paired mocked regression tests; the mocked suite + mypy strict + ruff pass green

**Plans**: 3 plans

**Wave 1**

- [x] 04-01-PLAN.md — HIGY-04 fix dual sync+async: 10 sites de `assert isinstance` reemplazados por `HigyrusAPIError(status_code=0, ...)` tipado + docstring sentinel + 10 mocked regression tests (5 sync + 5 async) (HIGY-04) [wave 1]

**Wave 2** *(blocked on Wave 1 completion; contains human checkpoint for live driver run)*

- [x] 04-02-PLAN.md — Rewrite main_higyrus.py with 18 named probes (HIGY-01..03+05..07 driver) + bidirectional SafeModel diff helper + httpx.URL.query parity capture + opt-in 401 single-shot + .env.example updates D-HIGY-14 + operator-observed live run generating 5 schemas + findings file (HIGY-01, HIGY-02, HIGY-03, HIGY-05, HIGY-06, HIGY-07) [wave 2]

**Wave 2.5** *(opportunistic, inserted after Plan 04-02 live run revealed httpx `%2F` encoding bug — Higyrus IIS rejects `%2F` in query with 400 "formato dd/mm/yyyy"; F-01..F-06 CONFIRMED)*

- [x] 04-04-PLAN.md — Opportunistic fix dual sync+async: refactor `_request` in client.py + aio.py to pre-attach query string with `urlencode(quote_via=quote, safe="/")` preserving literal `/` in wire + 2 regression tests asserting `httpx.Request.url.query` contains literal `08/05/2026` (NOT `%2F`) under new `# ------ Wire encoding ------` section (HIGY-04, HIGY-06; resolves findings F-01..F-06 from live run) [wave 2.5]

**Wave 3** *(blocked on Waves 1-2.5 completion)*

- [x] 04-03-PLAN.md — Append Verified-live (Phase 4) invariants to test_client.py/test_async_client.py + commit DRIFT-01 mirror baseline (5 schemas + Phase 4 findings file) (HIGY-02, HIGY-03, HIGY-05, HIGY-06, HIGY-07) [wave 3]

### Phase 5: Matriz Verification

**Goal**: The Matriz client — the largest surface, sync-only, and the only destructive surface — is fully verified read-only against the remarkets sandbox with raw-payload diffing and deliberate error-path coverage, order mutation is verified by mock only behind hard gates, every finding is environment-labeled, and the per-package closing reports lock the full cycle.
**Mode:** mvp
**Depends on**: Phase 4
**Requirements**: MATZ-01, MATZ-02, MATZ-03, MATZ-04, MATZ-05, MATZ-06, MATZ-07, DRIFT-02
**Success Criteria** (what must be TRUE):

  1. The auth flow (login + lazy-auth) is verified live against remarkets (sync REST), and the full read-only surface (segments, all instrument variants, market data, trades, order *reads*, risk positions/report) is exercised with raw payloads retained; market-data assertions are on shape/type/presence only, guarded by a market-hours check, never on values (MATZ-01, MATZ-02, MATZ-07)
  2. Each model's raw payload is diffed against its `from_api` fields (silent field-drop, both directions), and every envelope key (`["order"]`, `["orders"]`, `["marketData"]`, `["trades"]`, `["positions"]`) is confirmed present, with any unmapped `KeyError` flagged as a candidate fix (MATZ-03, MATZ-04)
  3. The `{"status":"ERROR"}` → `PrimaryAPIError` path is deliberately exercised across multiple distinct error conditions (bogus symbol, invalid account, malformed param) (MATZ-05)
  4. `new_order`/`replace_order`/`cancel_order` are verified by mock only — request construction and response parsing, preserving the GET-as-write quirk — and never run live; every finding is labeled `remarkets` with the prod-vs-sandbox gap recorded as an explicit open question (MATZ-06)
  5. Every discrepancy is classified in `.planning/verification/matriz-findings.md`, a schema snapshot is committed, each confirmed bug is fixed (sync-only) with a mocked regression test, and a per-package findings report is produced for every verified client with every confirmed bug closed and TESTED (DRIFT-02)

**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Safety Harness & Verification Infrastructure | 4/4 | Complete    | 2026-05-28 |
| 2. Ámbito Verification | 3/3 | Complete   | 2026-06-05 |
| 3. IOL Verification | 3/3 | Complete   | 2026-06-06 |
| 4. Higyrus Verification | 4/4 | Complete    | 2026-06-08 |
| 5. Matriz Verification | 1/4 | In Progress|  |
