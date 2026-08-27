---
phase: 33-verificaci-n-en-vivo-en-modo-estricto-fixes
verified: 2026-08-27T02:39:31Z
status: passed
score: 5/5 must-haves verified
behavior_unverified: 0
overrides_applied: 2
overrides:
  - must_have: "Los 4 drivers verificables + main_market_data.py corren en modo estricto contra sus APIs reales (ámbito, iol, higyrus, matriz; market-data contra develop)"
    reason: "The mechanism (130/130 probes decorated, AST-gated by verification/test_probe_context_coverage.py) is fully wired and proven for all 5 packages. Only the LIVE RUN could not complete for higyrus-client (DNS unreachable from this network — vendor host does not resolve, credentials present) and matriz-client (the D-MATZ-33 remarkets-only safety assert correctly refused to point demo-scoped credentials at a different sandbox — the operator explicitly instructed not to route around it, since matriz's surface includes order entry). Both gaps were surfaced to and accepted by the human operator mid-execution (33-05-SUMMARY.md, 33-CENSUS.md), with named backlog destinations LIVE-HIGY-33 and LIVE-MATZ-33 added to ROADMAP.md § Backlog in the same commits, never silently absorbed. 33-CENSUS.md itself states the honest verdict verbatim: 'GATE HUMANO ABIERTO... PARCIAL — 3 de 5 paquetes medidos en vivo.'"
    accepted_by: "sebadlf (operator, mid-execution — 33-05/33-CENSUS.md, 2026-08-27)"
    accepted_at: "2026-08-27T00:57:00Z"
  - must_have: "Los Literal RESPONSE pre-existentes de matriz (CFICode/MarketId/OrderType/Currency) se resuelven según el D-lock de la Phase 29 con el censo vivo"
    reason: "Same root cause as the criterion-1 override: scripts/literal_census_33.py carries the identical D-MATZ-33 gate and correctly SKIPPED before any round-trip against the demo host. The structural half of the disposition (all four aliases decode without enforcement, proven by code reading of the shared POLICY constants plus 84 green matriz decode/types tests) IS delivered; only the wire-value census is unmeasured. iol's half of criterion 3 (mercado/plazo, DT-07) is fully closed with 2,191-row live evidence. 33-LITERALS.md documents the matriz gap honestly (SKIPPED, not a fabricated zero) and routes it to LIVE-MATZ-33, the same named destination."
    accepted_by: "sebadlf (operator, mid-execution — 33-06/33-LITERALS.md, 2026-08-27)"
    accepted_at: "2026-08-27T01:20:00Z"
re_verification: null
gaps: []
deferred: []
human_verification: []
---

# Phase 33: Verificación en vivo en modo estricto + fixes — Verification Report

**Phase Goal:** La nueva decodificación queda verificada contra las APIs reales — este es el
momento donde aparecen las divergencias que la tolerancia silenciosa venía ocultando, y todas
se documentan y corrigen en el mismo ciclo.
**Verified:** 2026-08-27T02:39:31Z
**Status:** passed (with 2 documented, operator-accepted overrides on partial live coverage)
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP.md § Phase 33 Success Criteria, verbatim)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Los 4 drivers verificables + `main_market_data.py` corren en modo estricto contra sus APIs reales, con divergencias vía `verification/divergences.py` (endpoint + FQN + superficie) | PASSED (override) | Mechanism 100% delivered and proven: `verification/divergences.py` (`DivergenceHandler`, `divergence_capture`, `probe_context`, `endpoint_scope`) exists, is wired to all 5 package loggers, and `verification/test_probe_context_coverage.py` AST-gates all 130/130 probes across the 5 drivers (verified: `uv run pytest verification/test_probe_context_coverage.py -q` → 8 passed). Live execution: 3/5 packages actually ran against real APIs (ámbito 6 probes PASS, iol 14 probes PASS, market-data 39+14 probes PASS with `MARKET_DATA_VERIFY_MUTATING=1` for pass 1). higyrus SKIPPED (DNS `gaierror`, not auth) and matriz SKIPPED (D-MATZ-33 remarkets-only assert, credentials verified valid but host out of policy) — both surfaced honestly in `33-CENSUS.md` as "GATE HUMANO ABIERTO... PARCIAL — 3 de 5", never reported as clean, both routed to named backlog destinations `LIVE-HIGY-33`/`LIVE-MATZ-33` (confirmed present in `ROADMAP.md` § Backlog). |
| 2 | Cada divergencia confirmada se corrige in-cycle, espejada sync/async, con test de regresión mockeado por fix | VERIFIED | 4 fix families in `market-data-client` (S-1 envelope unwrap, SC-1 preview envelope, SC-2 `Optional` widening, SC-3 `Symbol` timestamps), each fixed once in `_core.py`/`models.py` (the shared dispatch point for both `client.py` and `aio.py`, confirmed by `grep` showing identical `preview_calendar_config` signature change mirrored in both files), each with a dedicated mocked regression file under `packages/market-data-client/tests/` (`test_reference_envelope_unwrap.py`, `test_preview_calendar_config_envelope.py`, `test_snapshot_no_data_row.py`, `test_symbol_write_ack_timestamps.py`) — 22 tests, all passing (verified directly). `test_surface_parity.py` (3 tests) confirms no sync/async drift introduced. Full package suite: 609 passed (verified directly, matches SUMMARY claim exactly). |
| 3 | Los `Literal` se cierran con evidencia real: iol `mercado`/`plazo` promovidos o documentados `str` permanente; matriz RESPONSE Literals resueltos según D-lock con censo vivo | PASSED (override) | iol: fully closed with evidence. `packages/iol-client/src/iol_client/types.py` docstring verified to state "**DT-07 is CLOSED**" with the full reasoning (RESPONSE-side `{"1"}` / `{"T0","T1"}` vs INPUT defaults `"bcba"`/`"t2"` are disjoint by case/domain) and a pointer to `33-LITERALS.md`'s 2,191-row census. matriz: SKIPPED for the same D-MATZ-33 reason as criterion 1 — the four aliases' *structural* property (decode without enforcement) is confirmed by code reading of the shared `POLICY` constants and 84 green `test_decode.py`/`test_types.py` tests (verified directly: 84 passed), but the *wire-value* census is unmeasured and honestly marked so in `33-LITERALS.md`'s per-field table (`SKIPPED — base URL fuera de política`, never a fabricated zero). No alias was widened, closed, or enforced (`git diff --stat` on `matriz_client/types.py`/`models.py` confirmed empty). |
| 4 | `verify_cycle_closure` PASS por paquete y schema snapshots reconciliados contra el baseline | VERIFIED | `uv run pytest verification/test_cycle_closure_phase33.py -q` → 11 passed (verified directly): green for all 5 packages, non-vacuously — 3 packages carry numeric floors derived from measured pre/post counts (iol 1, matriz 1, market-data 50→88), 2 packages (ámbito, higyrus) carry positive, argued exemptions instead of a silent `>= 0` (structural zero-model proof for ámbito; explicit "honestly vacuous" declaration for higyrus). Schema snapshots: `git status --porcelain .planning/verification/schemas/` empty (verified directly) — zero delta, all drift detected-and-reported (22 findings) not silently absorbed, matriz's 9 declared-but-absent files explained as a registered consequence of the SKIP, not an omission. |
| 5 | El volumen real se contrasta contra el piso de sizing de la Phase 29; excedentes con re-scope explícito documentado | VERIFIED | `33-CENSUS.md` present with full per-package contrast table (both the ratified-floor unit and the corrected triples-distinct unit), a `## Re-scope` table listing every undisposed finding with package/model/field/destination — zero cells say `TBD`/`later`/`a futuro` (verified directly, no such strings found). All 5 named destinations (`LIVE-MATZ-33`, `LIVE-HIGY-33`, `TYP-MD-EXTRA-33`, `HARN-DRIFT-33`, `SHAPE-MD-REF-33`) resolve to real, detailed entries in `ROADMAP.md` § Backlog (confirmed via `grep`, all 5 present with multi-paragraph rationale). The one genuinely new architectural finding discovered mid-fix (the other half of S-1 — `Instrument`/`Segment` declared-field mismatches) was correctly **not** applied without authorization (operator locked exactly 3 shape-change dispositions; this was not among them) and was routed to the newly-created `SHAPE-MD-REF-33` in the same commit that discovered it — discipline confirmed by direct code inspection (`_core.py::parse_segments_response` docstring documents the deliberate non-fix). |

**Score:** 5/5 truths verified (3 fully VERIFIED, 2 PASSED via documented operator-accepted override), 0 present-but-behavior-unverified.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `verification/divergences.py` | `DivergenceHandler` + ContextVars + install CM + probe decorator | ✓ VERIFIED | Exists, exports `DivergenceHandler`, `divergence_capture`, `endpoint_scope`, `probe_context` (confirmed via `grep`); `emit()` wraps its entire body in `try/except Exception` appending to `self.errors`, never propagating (P-2 hardening, confirmed by direct code read). |
| `verification/test_divergences.py` | 5+ unit tests per 33-VALIDATION.md Wave 0 | ✓ VERIFIED | Exists; part of the 16-test run (`test_divergences.py` + coverage + consistency + bare-except gates) that passed directly. |
| `verification/test_probe_context_coverage.py` | AST gate, 130 probes across 5 drivers | ✓ VERIFIED | `_TOTAL_EXPECTED_PROBES = 130` (confirmed by `grep`); `test_total_probe_coverage_is_one_hundred_and_thirty` passes. |
| `verification/test_finding_count_consistency.py` | P-3 regression class, fail-first control | ✓ VERIFIED | Passes; SUMMARY documents a falsification experiment (unseeded allocator arm fails as expected). |
| `verification/test_cycle_closure_phase33.py` | Non-vacuous criterion-4 gate, per-package floor | ✓ VERIFIED | 11 tests pass directly; exemption list pinned to exactly `{ambito-financiero-client, higyrus-client}` via `test_the_two_exemptions_are_the_only_ones`. |
| `scripts/preflight_33.py` | Per-package live-auth proof, SKIP-not-raise | ✓ VERIFIED | Prints only `type(exc).__name__`, never credential values or exception bodies (confirmed by direct code read). |
| `scripts/literal_census_33.py` | Read-only raw-wire value collection | ✓ VERIFIED | Committed (`5c36b5f`); `--selftest` output transcribed in `33-LITERALS.md` with a deliberate out-of-set (`ZZZZZZ`) and case-sensitivity (`bCBA`/`bcba`) probe. |
| `.planning/phases/.../33-CENSUS.md` | Live census vs. ≥96 floor, re-scope table | ✓ VERIFIED | Present, 482 lines, exhaustively cross-checked against ROADMAP backlog entries. |
| `.planning/phases/.../33-LITERALS.md` | Literal census, DT-07 closure evidence | ✓ VERIFIED | Present, 324 lines, DT-07 closure reasoning present and consistent with `types.py`. |
| `packages/iol-client/src/iol_client/types.py` | DT-07 recorded CLOSED | ✓ VERIFIED | Docstring updated in place (read directly), points to `33-LITERALS.md`. |
| `packages/market-data-client/src/*` (4 fixes) | Mirrored sync/async model-shape fixes | ✓ VERIFIED | `CalendarConfigPreview`/`PreviewMarket` classes exist; `preview_calendar_config` return type changed identically in `client.py:696` and `aio.py:696`; `Symbol.created_at`/`.updated_at` and `MarketDataSnapshot.entries`/`.market_data`/`.staleness_seconds` all `| None` (confirmed by `grep` against `models.py`). |
| `verification/test_main_drivers_bare_except.py` | AST gate, no broad-Exception on matriz/higyrus | ✓ VERIFIED | Passes; confirmed `main_matriz.py`/`main_higyrus.py` diffs add no bare/broad-Exception guards (per-probe catches only). |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `packages/*/src/*/_decode.py` (5 copies) | `verification/divergences.py` | `logging.getLogger('<pkg>')` → `DivergenceHandler.emit` (6-key `extra` record) | ✓ WIRED | `uv run python tools/check_decode_intactness.py` → exit 0, all 5 copies reduce to `CANONICAL_DIGEST` (untouched, as required — P-13 forbids editing this tier). |
| `main_matriz.py` / `main_higyrus.py` / `main_iol.py` / `main_ambito_financiero.py` / `main_market_data.py` | `verification/divergences.py` | `probe_context(...)` decorator on every `probe_*` | ✓ WIRED | AST-gated by `verification/test_probe_context_coverage.py` (130/130), not by inspection. |
| `.planning/verification/<pkg>-findings.md` | `packages/<pkg>/tests/` | `Regression:` bullets resolving to real test functions | ✓ WIRED | `verify_cycle_closure` PASS for all 5 packages (11 tests in `test_cycle_closure_phase33.py`); `grep -rc 'Regression:.*verification/'` → 0 in all 5 findings files (no regression link points at the never-CI-run `verification/` tree). |
| `packages/market-data-client/src/market_data_client/client.py` | `packages/market-data-client/src/market_data_client/aio.py` | Every fix mirrored on both surfaces via shared `_core.py` dispatch | ✓ WIRED | `test_surface_parity.py` green post-fix (3 passed, verified directly); `preview_calendar_config` signature identically changed on both files (confirmed by `grep`). |

### Data-Flow Trace (Level 4)

Not applicable in the UI-rendering sense — this is a verification-harness phase with no rendering surface. The equivalent check (does the census number actually derive from a live, inspected signal rather than a dropped/suppressed/unseeded channel) was performed and is documented exhaustively in `33-CENSUS.md § Under-floor investigation`: the three known silent-loss channels (P-1 logger level, P-2 swallowed handler exception, P-3 unseeded fid allocator) were each positively ruled out with evidence (not merely assumed absent), and iol's `DIVERGENCES=0` was proven to be a real inspection result via a synthetic-payload liveness probe rather than accepted as a possible dead channel.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| ruff lint clean | `uv run ruff check .` | All checks passed! | ✓ PASS |
| ruff format clean | `uv run ruff format --check .` | 254 files already formatted | ✓ PASS |
| mypy strict clean | `uv run mypy` | Success: no issues found in 75 source files | ✓ PASS |
| Full package test suite | `uv run pytest packages -q` | 1760 passed, 1 deselected in 91.39s | ✓ PASS |
| `_decode.py` intactness (6-way) | `uv run python tools/check_decode_intactness.py` | exit 0, hash `ac14868282ad0a5c` matches `CANONICAL_DIGEST` | ✓ PASS |
| Surface types gate | `uv run python tools/check_surface_types.py` | 0 violations | ✓ PASS |
| Uniform structure gate | `uv run python tools/check_uniform_structure.py` | all 6 packages carry `models.py`/`types.py` | ✓ PASS |
| Cycle closure, non-vacuous, per-package | `uv run pytest verification/test_cycle_closure_phase33.py -q` | 11 passed | ✓ PASS |
| Wave-0 hardening + coverage gates | `uv run pytest verification/test_divergences.py verification/test_probe_context_coverage.py verification/test_finding_count_consistency.py verification/test_main_drivers_bare_except.py -q` | 16 passed | ✓ PASS |
| market-data-client full suite | `uv run pytest packages/market-data-client -q` | 609 passed | ✓ PASS (matches SUMMARY claim exactly) |
| matriz-client decode/types (Literal alias regression) | `uv run pytest packages/matriz-client/tests/test_decode.py packages/matriz-client/tests/test_types.py -q` | 84 passed | ✓ PASS (matches SUMMARY claim exactly, no alias widened) |
| Full `verification/` suite vs. committed red baseline (P-13, run once) | `uv run pytest verification -q --tb=no -rfE` | 19 failed, 387 passed, 19 errors in 830.55s | ✓ PASS — identical failing/erroring node-ids to `33-BASELINE.md` (`test_matriz_sweep_snapshot.py`, `test_main_matriz_login_fail_uniformity.py`), same 19/19 counts, +19 new green tests from this phase. Confirmed pre-existing rot, not a Phase-33 regression. |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| LIVE-TYP-01 | 33-01..33-07 | La nueva decodificación queda verificada contra las APIs reales en modo estricto; Literals DT-07 cerrados con evidencia; divergencias corregidas in-cycle; cycle closure PASS | ✓ SATISFIED (with documented, operator-accepted 3/5-live-coverage caveat) | `REQUIREMENTS.md` shows the checkbox as `Pending` — this is **deliberate and correct**, not an oversight: `33-CENSUS.md` explicitly states "el criterio no se puede reportar cerrado sin mentir" while `LIVE-HIGY-33`/`LIVE-MATZ-33` remain open. The checkbox should stay unchecked until those two backlog items close a full 5/5 live measurement. This does not block Phase 33 completion — the phase honestly delivered everything it could within this environment's constraints and routed the rest with full traceability. |

No orphaned requirements found — `LIVE-TYP-01` is the only requirement mapped to Phase 33 in `REQUIREMENTS.md`, and it is claimed by all 7 plans.

### Anti-Patterns Found

None. Scanned every file touched by this phase's commits (`verification/divergences.py`, `verification/test_*.py` new files, `scripts/preflight_33.py`, `scripts/literal_census_33.py`, all 5 `main_*.py` drivers, `packages/market-data-client/src/market_data_client/{models,_core,client,aio}.py`, `packages/iol-client/src/iol_client/types.py`) for `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` and stub-shaped patterns (`return null`, hardcoded empty collections not overwritten by a fetch). Zero hits.

### Human Verification Required

None. The two coverage gaps (higyrus DNS unreachability, matriz remarkets-only policy block) are not open questions requiring a human decision right now — they were already surfaced to and resolved by the operator during execution (accepted, with named backlog destinations), and are captured as documented overrides above rather than as pending human-verification items.

### Gaps Summary

No blocking gaps. Two success criteria (1 and 3) are only **partially** true in the strictest reading of the ROADMAP wording ("los 4 drivers... corren... contra sus APIs reales" / "los RESPONSE de matriz se resuelven... con el censo vivo") because 2 of 5 packages (`higyrus-client`, `matriz-client`) could not be reached from this execution environment — one by DNS unreachability, one by a safety policy this phase correctly refused to circumvent. Both gaps were:

1. Discovered and measured with hard evidence during execution (not glossed over).
2. Surfaced to the human operator mid-execution and explicitly accepted.
3. Given named, traceable backlog destinations (`LIVE-HIGY-33`, `LIVE-MATZ-33`) with the exact remaining work spelled out (a DNS-reachable network / a remarkets-sandbox credential set, plus — for matriz — a trading-hours execution window for S-5).
4. Never reported as a false-clean "0 divergences" — every SKIP is labeled and distinguished from a true zero, with positive evidence backing every actual zero that *was* reported (ámbito, iol).

Everything else the phase could deliver within this environment was delivered to a high bar: the mechanism is 100% wired and AST-proven across all 130 probes in all 5 drivers; 4 real defects were found, fixed, mirrored sync/async, and regression-tested; a genuinely new defect discovered mid-fix was correctly *not* silently folded into an authorized fix and was routed with full traceability instead; cycle closure is proven non-vacuous per package; and the full workspace test/lint/type/gate suite is green with the one pre-existing exception (`verification/`'s 19/19 rot) proven unchanged node-id-for-node-id against a committed baseline.

These two overrides are recorded above per `verification-overrides.md` and should be revisited when `LIVE-HIGY-33`/`LIVE-MATZ-33` close — at that point criteria 1 and 3 can move from "PASSED (override)" to plain "VERIFIED".

---

_Verified: 2026-08-27T02:39:31Z_
_Verifier: Claude (gsd-verifier)_
