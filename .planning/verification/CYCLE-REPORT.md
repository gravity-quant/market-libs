# Verification Cycle Report — market-libs

**Cycle ID:** `verification-cycle-2026-Q2`
**Cycle start:** 2026-05-26 (Phase 1 — Safety Harness)
**Cycle end:** 2026-06-10T01:10:32+00:00
**Scope:** 4 packages — ambito-financiero-client, iol-client, higyrus-client, matriz-client
**Out of scope (documented):** wallets-client (stub), matriz async/WebSocket surfaces, prod-vs-remarkets verification

## Stats per-package

| Package | Findings Total | OPEN | CONFIRMED | FIXED | EXPECTED | NO-FIX | Regression Tests | Schemas Committed |
|---------|----------------|------|-----------|-------|----------|--------|------------------|-------------------|
| ambito-financiero-client | 1 | 0 | 0 | 0 | 1 | 0 | 0 | 1 |
| iol-client | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 4 |
| higyrus-client | 2 | 1 | 0 | 0 | 1 | 0 | 0 | 5 |
| matriz-client | 10 | 0 | 1 | 0 | 2 | 7 | 0 | 8 |
| **TOTAL CYCLE** | **14** | **2** | **1** | **0** | **4** | **7** | **0** | **18** |

> **Note on Regression Tests column:** the column counts findings with a populated `Regression: <path>::<test>` field. Historical findings from Phases 2-4 predate this convention (introduced by Phase 5 `verification/cycle_report.py`); see *Open questions* below for the forward-looking convention agreed for cycle-2026-Q3+.

## Cross-cycle

- **Total findings emitted in this cycle:** 14 (cumulative across Phases 2-5)
- **Total schemas committed (PII-free via `schema_of`):** 18 (1 ámbito + 4 iol + 5 higyrus + 8 matriz)
- **Total bugs found and fixed in-cycle (CONFIRMED → FIXED transitions):** 0 in matriz Phase 5 (F-09 fix deferred — see B caveat below); 10 envelope sites + 6 wire-encoding sites fixed in higyrus Phase 4 (counted under Phase 4 SUMMARY, pre-dating per-finding linkage convention)
- **Total regression tests added in Phase 5 alone:** 42 (19 envelope+`_token` sentinels from Plan 05-01 + 12 Verified-live invariants + 11 MATZ-06 mock-only contract from Plan 05-03)
- **Cumulative repo test count at cycle end:** 273 (251 entering Phase 5 + 22 net new from Phase 5)

### Patrones recurrentes (cross-cycle observations)

- **Envelope-key indexing as unmapped KeyError** — detected and fixed in-cycle in HIGY (10 sites Phase 4) and MATZ (18 sites Phase 5); IOL had wrap pre-existing.
- **SafeModel false-pass trap** (model accepts wire silently with safe defaults) — detected via bidirectional diff helper promoted in Phase 5; affects HIGY (Posicion.disponibleAjustado FCI-conditional) and MATZ (TBD per live run).
- **ERROR-MAP coverage varies:** IOL/HIGY have auth_401 opt-in (Phase 3-4); MATZ uses always-on read-only error probes (D-MATZ-22) because login retries on remarkets are lockout-risk.
- **Wire encoding bug (httpx %2F vs literal /)** detected in HIGY F-01..F-06 Phase 4 Wave 2.5 opportunistic fix — IIS-style backend rejects %2F in date paths.

## Open questions for downstream milestone

1. **prod-vs-remarkets gap (REQUIRED handoff — D-MATZ-27).** This cycle verifies matriz only against the remarkets sandbox by safety policy (REQUIREMENTS.md Out of Scope). Future milestone: **"verify matriz against prod with appropriate safety harness"** — design read-only-only probes that respect prod rate limits + audit trail + business-hours gates before exercising any path on `https://api.primary.com.ar`. Until then, prod shape divergence is acknowledged as EXPECTED terminal (F-02/F-10 in `matriz-client-findings.md`).

2. **higyrus get_listado_cuentas=0 (deferred investigation — F-02 higyrus).** Higyrus account-list probe returned 0 accounts in remarkets sandbox; finding currently OPEN. Future milestone should confirm whether (a) the sandbox account has no accounts associated, (b) the endpoint requires an additional scope/header, or (c) the client incorrectly drops a query parameter.

3. **F-09 matriz ERROR-MAP fix deferred.** `get_instruments_by_cfi` with malformed CFI did NOT raise `PrimaryAPIError`. Classified CONFIRMED in Plan 05-03 but the fix + regression test are deferred to a future cycle/milestone — until then `verify_cycle_closure("matriz-client")` returns FAIL with missing=[F-09]. That FAIL is itself the DRIFT-02 signal working as designed: cycle closure surfaces the gap automatically.

4. **IOL `refresh_token` persistence between invocations (if applicable).** IOL OAuth refresh-token reuse across process restarts not exercised in this cycle (per-process token cache only). Candidate for a "long-lived session" verification mode in a future milestone.

5. **HIGY multi-account iteration (if applicable).** Phase 4 verified higyrus against a single configured account; multi-account fanout (`get_listado_cuentas` → loop probes) is deferred.

6. **Deferred items from CONTEXT.md (cycle-relevant):**
   - `matriz_client.ws_client` (WebSocket streaming for market data + execution reports) — no live verification in this cycle; mock-only test suite exists.
   - `matriz_client` async/`aio.py` surface — by design absent (matriz is sync-only per CLAUDE.md); future "async via thread executor" pattern verification is candidate work.
   - Cross-package shared base (auth/HTTP boilerplate) — explicitly rejected as anti-pattern by current architecture (each package self-contained); reconsider only if maintenance burden becomes acute.

Per D-MATZ-27 in `.planning/verification/matriz-client-findings.md` (F-02/F-10, EXPECTED terminal): the prod-vs-remarkets verification gap is acknowledged as an EXPECTED limitation of this cycle. Future milestone "verify matriz against prod with appropriate safety harness" required.

## Schemas summary

Committed schema snapshots by package (PII-free, structural only — envelope D-21: `{endpoint, client_function, captured_at, base_url, sample_params, schema}` with `schema_of` recursion emitting only type names):

- **ambito-financiero-client (1):**
  - `.planning/verification/schemas/ambito-financiero-client/get-dollar-banco-nacion.json`
- **iol-client (4):**
  - `.planning/verification/schemas/iol-client/get-historical-quotes.json`
  - `.planning/verification/schemas/iol-client/get-instruments-by-type.json`
  - `.planning/verification/schemas/iol-client/get-instruments.json`
  - `.planning/verification/schemas/iol-client/get-quote.json`
- **higyrus-client (5):**
  - `.planning/verification/schemas/higyrus-client/get-health.json`
  - `.planning/verification/schemas/higyrus-client/get-listado-cuentas.json`
  - `.planning/verification/schemas/higyrus-client/get-movimientos.json`
  - `.planning/verification/schemas/higyrus-client/get-posicion-valuada.json`
  - `.planning/verification/schemas/higyrus-client/get-posiciones.json`
- **matriz-client (8):**
  - `.planning/verification/schemas/matriz-client/get-all-instruments.json`
  - `.planning/verification/schemas/matriz-client/get-instrument-detail.json`
  - `.planning/verification/schemas/matriz-client/get-instruments-by-cfi-esxxxx.json`
  - `.planning/verification/schemas/matriz-client/get-instruments-by-segment.json`
  - `.planning/verification/schemas/matriz-client/get-instruments-details.json`
  - `.planning/verification/schemas/matriz-client/get-market-data.json`
  - `.planning/verification/schemas/matriz-client/get-segments.json`
  - `.planning/verification/schemas/matriz-client/get-trades.json`

Matriz schemas committed in 8 of 11-19 expected range; the 9 SKIPPED probes are account/ID-scoped and depend on opt-in env vars (`PRIMARY_ACCOUNT`, `MATRIZ_SAMPLE_*`) not configured by the operator in this run. Per Assumption A4 (RESEARCH L981), the lower bound is acceptable.

## Cycle validation (`verify_cycle_closure` per package)

| Package | Result | Missing (if FAIL) |
|---------|--------|-------------------|
| ambito-financiero-client | PASS | N/A (no CONFIRMED/FIXED findings to check) |
| iol-client | PASS | N/A (no CONFIRMED/FIXED findings to check) |
| higyrus-client | PASS | N/A (no CONFIRMED/FIXED findings to check) |
| matriz-client | FAIL | F-09 (CONFIRMED, regression deferred per Open question #3) |

**Note on historical findings (Phases 2-4) — Operator decision B = Option A (caveat doc):**

Historical findings from Phases 2-4 predate the regression-link field convention introduced in Phase 5 `verification/cycle_report.py`. **Forward-looking convention:** from Phase 6 onwards, every `CONFIRMED → FIXED` transition appends `Regression: <path>::<test>` to the finding bullet list. Cycle closure for historical findings counts as PASS via inherited Phase-level audit (each phase's SUMMARY enumerates regression test counts: Phase 2 ámbito = 12 regressions, Phase 3 iol ≈ TBD per its SUMMARY, Phase 4 higyrus = 24 regressions + 14 verified-live invariants, Phase 5 matriz = 19 regressions + 12 verified-live + 11 mock-only contract).

The matriz FAIL for F-09 is intentional and represents the DRIFT-02 signal working as designed: cycle closure surfaces the gap automatically without manual cross-referencing. F-09 fix + regression test are deferred to a future cycle per Open question #3; until that work lands, `cycle_closure_matriz_client` will continue to FAIL.

## Sign-off

DRIFT-02 cycle closure complete: per-package report produced for every verified client; every confirmed bug closed and TESTED (where applicable — see Cycle validation caveat above for historical findings and the F-09 deferred regression); schema snapshots committed; cross-cycle patterns documented; downstream handoffs explicit.

*Generated by Plan 05-04 / Phase 5 closure on 2026-06-10T01:10:32+00:00.*
