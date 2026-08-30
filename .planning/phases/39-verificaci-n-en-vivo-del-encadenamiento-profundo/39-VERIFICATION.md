---
phase: 39-verificaci-n-en-vivo-del-encadenamiento-profundo
verified: 2026-08-30T04:15:00Z
status: passed
score: 15/15 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 39: Verificación en vivo del encadenamiento profundo — Verification Report

**Phase Goal:** El encadenamiento profundo deja de ser una propiedad demostrada contra fixtures y pasa a ser una propiedad demostrada contra las APIs reales, en sync y en async, con toda divergencia corregida dentro del mismo ciclo.
**Verified:** 2026-08-30T04:15:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (mapped to ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 (SC-1) | Cada driver `main_*.py` ejercita al menos una cadena profunda real en ambas superficies contra la API en vivo, reportando PASS/SKIPPED con causa medida y destino nombrado | ✓ VERIFIED | `39-07-SUMMARY.md` transcript: iol RAN (`PASS=14 FAIL=0 SKIPPED=1 FINDING=0`), ambito RAN (`PASS=6`), matriz RAN vs bbsa (`PASS=39 FINDING=7→post-fix 5`), higyrus SKIPPED with `LIVE-HIGY-33` (DNS re-probed this session). Four run-evidence envelopes exist on disk (`.planning/verification/run-evidence/*.json`) with plausible `probes_executed` (15/7/50/0) and `n_triples`. |
| 2 (SC-1) | `LIVE-MATZ-33` allowlist gate is exact-hostname, never rounded/bypassed | ✓ VERIFIED | `main_matriz.py:228-247` `_venue_token()` uses `urlsplit(...).hostname` + dict `.get()` exact lookup against `_VENUE_ALLOWLIST = {"api.remarkets.primary.com.ar": ..., "api.bbsa.matrizoms.com.ar": ...}`. Confirmed no substring/`endswith`/`in`. `verification/mutation_gate.py` untouched since Phase 27 (`git diff dcbb3d2` empty). |
| 3 (SC-2) | Ninguna cadena profunda lanza AttributeError/TypeError con datos reales, incluidos casos límite (mercado cerrado, fila sin datos, campo ausente, 204/vacío) | ✓ VERIFIED | Live run: matriz's 6 `MarketDataSnapshot` aliases dereferenced against real `null` entries (closed market) without exception, in both `client.py` and `aio.py` — `39-CENSUS.md` "Casos límite de D-12" table. The 204/empty-body case (not produced live) is covered by the mocked edge suites (`packages/{iol,higyrus,matriz}-client/tests/test_deep_chain_edges.py`, 50 tests, all passing, each with a populated control that fails if green for the wrong reason). |
| 4 (SC-3) | Toda divergencia CONFIRMED se corrige in-cycle con espejo sync/async y regresión mockeada | ✓ VERIFIED | F-43/F-44 (`Instrument.marketId`/`.symbol` flat-identifier data loss) fixed via `_core._normalize_instrument_element`, wired into both `client.py:534,541` and `aio.py:572,579` (single site, both shells traverse it). Regression: `packages/matriz-client/tests/test_instruments_flat_identifier_shape.py`, 13/13 passing. Ledger status `FIXED` confirmed in `matriz-client-findings.md:378-396`. |
| 5 (SC-3) | `verify_cycle_closure` devuelve PASS no-vacuo (evidencia positiva de que el driver corrió, no ausencia de findings) | ✓ VERIFIED | `main_matriz.py:174-225` `_cycle_closure_verdict()`: `probes <= 0` → SKIPPED with named destination; `probes > 0 and ok` → PASS with probe count + timestamp; explicitly documents rejecting the "≥1 CONFIRMED/FIXED finding" predicate that would misclassify a clean-and-ran package the same as a never-ran one. `verification/test_cycle_closure_phase33.py` (21 tests, all passing) pins this behavior including the D-09 non-vacuous predicate tests. |
| 6 | El conteo de errores del handler (`HANDLER_ERRORS`) es cero en cada corrida | ✓ VERIFIED | `39-07-SUMMARY.md` table: iol/ambito/matriz all report `HANDLER_ERRORS=0`; higyrus n/a (SKIPPED, 0 probes). Confirmed in `39-CENSUS.md` "El gate duro se cumplió". |
| 7 | `main_market_data.py` no se toca (D-07 respetado) | ✓ VERIFIED | `git log b659084^..312c6d2 -- main_market_data.py` empty; `.planning/verification/market-data-client-findings.md` byte-identical (`git diff dcbb3d2` empty). |
| 8 (SC-4) | El censo contrasta explícitamente contra la Fase 33 y el piso de `29-SIZING.md`, separando colapso-de-política vs corrección real | ✓ VERIFIED | `39-CENSUS.md` "El split que SC-4 exige (D-11)" — per-package tables splitting each of the 14 matriz floor triples and the 22 higyrus floor triples into exactly one of {policy collapse, real fix, still open/UNMEASURED}; zeros declared by enumeration, not silence. |
| 9 | Suites mockeadas de casos límite cubren iol/higyrus/matriz en ambas superficies, con control poblado anti-vacuidad | ✓ VERIFIED | `packages/{iol,higyrus,matriz}-client/tests/test_deep_chain_edges.py` — 50 tests total, all passing; each has `*_populated_control`/`*_populated_control_async` pairs. `verification/test_main_iol_deep_chain.py::test_the_deep_chain_lock_is_not_vacuous` explicitly guards the AST lock against silent pass. |
| 10 | Los 8 baselines de schema de matriz (remarkets) quedan intactos; bbsa se captura fresco, segregado por venue | ✓ VERIFIED | `.planning/verification/schemas/matriz-client/`: 8 `*.remarkets.json` files byte-identical to their pre-rename content (`diff` confirms `get-all-instruments.json` → `get-all-instruments.remarkets.json` identical), 14 fresh `*.bbsa.json` files including the two Risk endpoints captured for the first time. |
| 11 | Los nuevos dereferences de `.puntas`/`.parking`/alias viven dentro del cuerpo de un `try` del propio probe (no `except`/`else`/`finally`) | ✓ VERIFIED | Confirmed directly (grep + manual read) and independently confirmed by `39-REVIEW.md` targeted verification: "all sites... All are inside the `try:` block, never in `except`/`else`/`finally`." |
| 12 | 7 nuevos archivos `verification/test_*.py` están en el allowlist explícito de `ci.yml`, incluido `test_cycle_closure_phase33.py` (WR-01 del review, retroactivo) | ✓ VERIFIED | `.github/workflows/ci.yml:81-92` lists all 8 files. Commit `0f45508` ("fix(39): wire test_cycle_closure_phase33.py into the CI allowlist") post-dates the review and closes WR-01. |
| 13 | Ledger de triples retiradas (`35-RETIRED-TRIPLES.md`) tiene addendum de la Fase 39 | ✓ VERIFIED | `35-RETIRED-TRIPLES.md:315-` `## Phase 39 addendum` section present, cross-references `39-CENSUS.md`, computes the subtraction matching D-11. |
| 14 | Requirement LIVE-NOBJ-01 está cubierto sin huérfanos | ✓ VERIFIED | REQUIREMENTS.md maps only LIVE-NOBJ-01 to Phase 39; all 8 plans declare `requirements: [LIVE-NOBJ-01]`. No other requirement IDs map to Phase 39. |
| 15 | Cero debt markers (TBD/FIXME/XXX) sin referencia en archivos tocados por la fase | ✓ VERIFIED | Grepped all key source/test files touched this phase — zero hits. Deferred items (D39-01..D39-04) are formally tracked in `deferred-items.md` with named destinations, not left as inline markers. |

**Score:** 15/15 truths verified (0 present-but-behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `verification/test_main_verify_classification.py` | Classification contract lock | ✓ VERIFIED | Exists, imports `from main_verify import _ENV_SKIP`, in CI allowlist, passes. |
| `verification/test_main_matriz_skip_line_shape.py` | SKIPPED line shape + exact-hostname allowlist lock | ✓ VERIFIED | Exists, `import main_matriz`, in CI allowlist, passes. |
| `verification/test_main_higyrus_skip_line_shape.py` | Higyrus SKIPPED line shape lock | ✓ VERIFIED | Exists, in CI allowlist, passes. |
| `.github/workflows/ci.yml` | Allowlist expanded with all new files | ✓ VERIFIED | All 8 verification/test_*.py files present, including retroactive `test_cycle_closure_phase33.py`. |
| `packages/{iol,higyrus,matriz}-client/tests/test_deep_chain_edges.py` | Mocked edge-case matrices, both surfaces | ✓ VERIFIED | 50 tests total, sync+async pairs, `from pytest_httpx import HTTPXMock` present, all passing. |
| `verification/run_evidence.py` | Run-evidence envelope read/write | ✓ VERIFIED | Exports `write_run_evidence`, `read_run_evidence`, `run_evidence_path`, `probes_executed`; `.planning/verification/run-evidence/` has 4 envelopes. |
| `verification/test_run_evidence.py` | Envelope contract tests | ✓ VERIFIED | Present, passes as part of the 103-test verification/ suite run. |
| `verification/test_main_iol_deep_chain.py` | AST lock for `.puntas` chain (4 probes) | ✓ VERIFIED | 301 lines (>120 min), contains `_chain_reaches`, passes including non-vacuity test. |
| `verification/test_main_higyrus_deep_chain.py` | AST lock for `.parking` chain | ✓ VERIFIED | 382 lines, contains `_chain_reaches`, passes. |
| `verification/test_main_matriz_deep_chain.py` | AST lock for 6 MarketDataSnapshot aliases | ✓ VERIFIED | 435 lines, contains `open_interest`, passes. |
| `.planning/verification/schemas/matriz-client/` | Venue-segregated baselines | ✓ VERIFIED | 8 `*.remarkets.json` (byte-identical to pre-rename) + 14 `*.bbsa.json` (fresh, incl. 2 Risk endpoints). |
| `packages/matriz-client/tests/test_instruments_flat_identifier_shape.py` | Regression for the CONFIRMED divergence | ✓ VERIFIED | 234 lines, 13/13 tests passing, covers all 4 affected surfaces + nested control + forward-compat tolerance + 6 degenerate edges. |
| `.planning/phases/39-.../39-CENSUS.md` | Census with Phase 33 / floor contrast, policy-vs-fix split | ✓ VERIFIED | 430 lines (>120 min), present, cross-verified against findings ledgers and run-evidence directly. |
| `.planning/phases/35-.../35-RETIRED-TRIPLES.md` | Phase 39 addendum | ✓ VERIFIED | `## Phase 39 addendum` section present. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `main_matriz.py` / `main_higyrus.py` | `main_verify.py` | SKIPPED stdout line matched by `_ENV_SKIP` pattern | ✓ WIRED | Verified via passing `test_main_verify_classification.py`, `test_main_matriz_skip_line_shape.py`, `test_main_higyrus_skip_line_shape.py`. |
| `verification/test_main_matriz_deep_chain.py` | `packages/matriz-client/src/matriz_client/aio.py` | exercises `AsyncClient.get_market_data` alongside sync | ✓ WIRED | Confirmed via test content and passing suite. |
| `main_matriz.py` (cycle-closure loop) | `verification/run_evidence.py` | reads evidence before accepting PASS | ✓ WIRED | `_cycle_closure_verdict()` consumes `probes_executed`/`evidence` params; `test_cycle_closure_phase33.py` pins the D-09 predicate live. |
| `main_iol.py` | `packages/iol-client/src/iol_client/models.py` | dereferences `Cotizacion.puntas` (list) and `Titulo.puntas` (singular Null Object) | ✓ WIRED | Confirmed by REVIEW targeted verification + direct grep, all inside `try:` bodies. |
| `main_higyrus.py` | `packages/higyrus-client/src/higyrus_client/models.py` | `Posicion.from_api(row)` then `.parking[...].diasParking` | ✓ WIRED | Confirmed present, no extra HTTP call added. |
| `main_matriz.py` | `packages/matriz-client/src/matriz_client/models.py` | `MarketDataSnapshot.from_api` then 6 aliases | ✓ WIRED | Confirmed live-exercised against real `null` payload without exception. |
| CONFIRMED divergence | `packages/matriz-client/tests/` | mocked regression pinning the fix | ✓ WIRED | `test_instruments_flat_identifier_shape.py` under `packages/`, exercised by per-package CI, not `verification/` allowlist. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| CI-exact verification/ allowlist suite passes | `pytest verification/test_main_verify_classification.py ... test_cycle_closure_phase33.py` (the 8-file list from `ci.yml`) | 103 passed | ✓ PASS |
| Matriz flat-identifier regression | `pytest packages/matriz-client/tests/test_instruments_flat_identifier_shape.py` | 13 passed | ✓ PASS |
| Mocked deep-chain edge suites (3 packages) | `pytest packages/{iol,higyrus,matriz}-client/tests/test_deep_chain_edges.py` | 50 passed | ✓ PASS |
| Full in-scope package test suites | `pytest packages/{matriz,iol,higyrus,ambito-financiero}-client/tests/` | 1431 passed, 1 deselected | ✓ PASS |
| Ruff lint on touched drivers/core | `ruff check main_matriz.py main_higyrus.py main_iol.py main_ambito_financiero.py verification/run_evidence.py verification/__init__.py packages/matriz-client/src/matriz_client/_core.py` | All checks passed | ✓ PASS |
| Exact-hostname gate (not substring) | manual read of `_venue_token()` | `urlsplit(...).hostname` + dict `.get()` | ✓ PASS |
| `mutation_gate.py` untouched | `git log` since Phase 27 | last touch commit `63af080` (Phase 27) | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| LIVE-NOBJ-01 | 39-01..39-08 (all) | Los drivers `main_*.py` ejercitan el encadenamiento profundo (sync+async) contra las APIs en vivo; toda divergencia se corrige in-cycle con espejo sync/async y regresión mockeada | ✓ SATISFIED | All truths above; REQUIREMENTS.md marks it `Complete`, no orphaned requirement IDs found for Phase 39. |

### Anti-Patterns Found

None. Zero `TBD`/`FIXME`/`XXX` markers in phase-touched files. All deferred work (D39-01 through D39-04) is formally tracked in `deferred-items.md` with named destinations rather than left as inline debt markers. The one code-review WARNING that pointed to a genuine CI gap (WR-01, `test_cycle_closure_phase33.py` missing from allowlist) was closed post-review in commit `0f45508`. The second review WARNING (WR-02, higyrus `httpx.ConnectTimeout` not caught by the vendor-unreachable branch) is explicitly documented in the code's own docstring (`main_higyrus.py:676-678`) as a known, deliberate scope boundary, not a silent gap — accepted per this verification's task framing.

### Human Verification Required

None. All must-haves are directly verifiable against committed artifacts, findings ledgers, run-evidence envelopes, and passing test suites — no visual, real-time, or subjective judgment calls remain open.

### Gaps Summary

No gaps found. All 15 derived truths (covering the 4 ROADMAP Success Criteria plus phase-level must-haves from the 8 plan frontmatters) verified against actual codebase state, not SUMMARY.md narrative. Independently confirmed:

- The 4 run-evidence JSON envelopes exist with plausible, mutually consistent counts (cross-checked against `39-07-SUMMARY.md`'s transcribed SUMMARY lines and `39-CENSUS.md`'s own re-derivation).
- The 4 findings ledgers' actual status markers match claimed dispositions exactly (matriz: 3 FIXED / 7 EXPECTED / 30 NO-FIX / 0 OPEN, verified by direct grep of `**Status:**` fields; higyrus and ambito byte-identical to pre-phase state; iol's F-01 correctly left OPEN with operator signoff, not silently promoted).
- `ci.yml`'s allowlist includes all 8 new/modified `verification/test_*.py` files, including the WR-01 fix landed after the code review.
- `main_matriz.py`'s D-MATZ-33 gate is exact-hostname (`urlsplit().hostname` + dict lookup), not substring, and `verification/mutation_gate.py` is byte-unchanged since Phase 27.
- The one CONFIRMED divergence (matriz's flat instrument identifier bug, F-43/F-44) is fixed in the single shared `_core.py` site traversed by both `client.py` and `aio.py`, with a 13-test mocked regression suite under `packages/matriz-client/tests/` (CI-exercised path, not the inert `verification/` tree).

---

*Verified: 2026-08-30T04:15:00Z*
*Verifier: Claude (gsd-verifier)*
