---
phase: 43
slug: market-data-client-forma-de-instrument-segment-5-claves-extr
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-31
validated: 2026-09-02
---

# Phase 43 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3+ · pytest-asyncio (`asyncio_mode = "auto"`) · pytest-httpx 0.34+ · pytest-cov |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (`testpaths = ["packages", "tests", "verification"]`, `--import-mode=importlib`, `--strict-markers`) |
| **Quick run command** | `uv run pytest packages/market-data-client -q --no-cov` |
| **Full suite command** | `uv run pytest packages/market-data-client --cov=packages/market-data-client/src --cov-report=term` |
| **Estimated runtime** | ~1 second (baseline measured: 711 passed in 1.05s) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest packages/market-data-client -q --no-cov`
- **After every plan wave:** Run `uv run python tools/check_surface_types.py && uv run mypy && uv run mypy packages/market-data-client/tests`
- **Before `/gsd-verify-work`:** Full suite must be green — reproduce all 4 CI jobs locally: `uv run ruff check . && uv run ruff format --check . && uv run python tools/check_surface_types.py && uv run mypy && uv run mypy packages/market-data-client/tests && uv run pytest packages/market-data-client -q && uv run pre-commit run --all-files`
- **Max feedback latency:** ~1 second

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 43-01-01 | 01 | 0 | SHAPE-01 | V5 | `Instrument` declares exactly the 10 wire fields + `marketId` alias | unit | `uv run pytest packages/market-data-client/tests/test_reference_models.py::test_instrument_field_set_matches_reconciled_wire -x -q --no-cov` | ✅ | ✅ green — **2 passed**, re-run 2026-09-02 |
| 43-01-02 | 01 | 0 | SHAPE-01 | V5 | `Segment` declares exactly `{segment, live_instruments}` | unit | `uv run pytest packages/market-data-client/tests/test_reference_models.py::test_segment_field_set_matches_reconciled_wire -x -q --no-cov` | ✅ | ✅ green — included in the same 2-passed run above |
| 43-01-03 | 01 | 0 | SHAPE-01 | V5 (Tampering mitigation) | `Instrument.marketId` mirrors `market_id`; explicit `marketId` always wins | unit | `uv run pytest packages/market-data-client/tests/test_reference_models.py -k "instrument_market_id_alias_mirrors_wire_snake_case or instrument_explicit_camel_case_payload_key_still_wins" -q --no-cov` | ✅ | ✅ green — **2 passed**, re-run 2026-09-02 |
| 43-01-04 | 01 | 0 | SHAPE-01 | — | `Instrument.instrumentType` no longer exists | unit | *(command corrected — the draft's `-k instrumentType` filter matches no test name; the absence assertion lives inline at `test_reference_models.py:134` as part of the exact-field-set test)* `uv run pytest packages/market-data-client/tests/test_reference_models.py::test_instrument_field_set_matches_reconciled_wire -q --no-cov` (asserts `not hasattr(Instrument.from_api({}), "instrumentType")` at line 134) | ✅ | ✅ green — same run as 43-01-01, assertion confirmed present at the cited line |
| 43-02-01 | 02 | 1 | SHAPE-01 (crit. 2) | — | `get_segments()` over the real envelope returns populated rows | unit | `uv run pytest packages/market-data-client/tests/test_reference_envelope_unwrap.py -q --no-cov` | ✅ | ✅ green — **6 passed**, re-run 2026-09-02 (value assertion `result[0].segment == "SEG1"` / `.live_instruments == 7` present, draft's "value assertion missing" note is stale) |
| 43-02-02 | 02 | 1 | SHAPE-01 (crit. 2) | — | Before/after measured against Phase 42 capture | manual (1×) | capture read + F-214…F-218 census documented in SUMMARY | n/a — documentary evidence, not a test | ✅ **manual-only, executed and evidenced** — `43-01-SUMMARY.md:10` cites `42-WIRE-READ.md` § 2, findings F-205..F-218 |
| 43-03-01 | 03 | 0 | HARN-02 | V5, V7 | The 5 `extra` keys are declared and decode without `extra` | unit | *(command corrected — `_MEASURED_HEALTH_FEED_43` is a fixture, not a test name)* `uv run pytest packages/market-data-client/tests/test_core.py -k measured_health_feed -q --no-cov` | ✅ | ✅ green — **1 passed** (`test_measured_health_feed_payload_produces_zero_divergence_records`), fixture consumed at 4 sites (`test_core.py:1201,1212,1325,1364`) |
| 43-03-02 | 03 | 0 | HARN-02 (crit. 3) | — | No measured `extra` flips to `missing` on a healthy payload | unit | `uv run pytest packages/market-data-client/tests/test_core.py -k healthy_feed_payload_emits_no_missing -q --no-cov` | ✅ | ✅ green — **1 passed**, re-derivation confirmed materialized (not just planned) |
| 43-03-03 | 03 | 0 | HARN-02 (crit. 4) | — | Every fixture key ⊆ measured key-set | unit | `uv run pytest packages/market-data-client/tests/test_core.py::test_every_fixture_key_is_a_measured_wire_key -q --no-cov` | ✅ | ✅ green — **1 passed**, re-run 2026-09-02 |
| 43-04-01 | 04 | 1 | SHAPE-01+HARN-02 | — | Exact optionals set reflects D-03/D-09/D-10 | unit | `uv run pytest packages/market-data-client/tests/test_core.py -q --no-cov` | ✅ | ✅ green — **174 passed**, re-derivation confirmed materialized |
| 43-04-02 | 04 | 1 | SHAPE-01 | Tampering mitigation | Exact overrides set reflects D-04 | unit | `uv run pytest packages/market-data-client/tests/test_decode.py -q --no-cov` | ✅ | ✅ green — **77 passed**, re-derivation confirmed materialized |
| 43-05-01 | 05 | 1 | D-14 | — | Async surface identical to sync (fixtures re-derived, zero source diff) | unit | `uv run pytest packages/market-data-client/tests/test_reference_client.py packages/market-data-client/tests/test_reference_async_client.py -q --no-cov` | ✅ | ✅ green — **12 passed**, fixtures confirmed re-derived (43-VERIFICATION.md truth 4) |
| 43-06-01 | 06 | 2 | D-15 | — | All 4 CI gates green | integration | `uv run ruff check . && uv run ruff format --check . && uv run python tools/check_surface_types.py && uv run mypy && uv run mypy packages/market-data-client/tests && uv run pytest packages/market-data-client -q` | ✅ | ✅ green — `All checks passed!` · `280 files already formatted` · surface types 0 violations (337 definitions) · mypy clean (75 + 36 files) — re-run 2026-09-02 |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*Task IDs above are illustrative — the planner assigns final plan/wave numbers; this map is the requirement→test contract, not a binding task schedule.*

---

## Wave 0 Requirements

- [x] `test_reference_models.py::test_instrument_field_set_matches_reconciled_wire` — SHAPE-01. **Entregado:** present, 2 passed (re-run 2026-09-02).
- [x] `test_reference_models.py::test_segment_field_set_matches_reconciled_wire` — SHAPE-01. **Entregado:** same run, passing.
- [x] `test_reference_models.py::test_instrument_market_id_alias_mirrors_wire_snake_case` — D-04. **Entregado:** present, passing.
- [x] `test_reference_models.py::test_instrument_explicit_camel_case_payload_key_still_wins` — D-04. **Entregado:** present, passing.
- [x] `test_core.py::_MEASURED_HEALTH_FEED_43` (fixture) + `_keys_recursive` + `test_every_fixture_key_is_a_measured_wire_key` — D-13 / criterio 4. **Entregado:** fixture at `test_core.py:1056`, consumed at 4 sites, subset test passing (1 passed).
- [x] `test_core.py::test_feed_subscription_decodes_the_measured_blob` — D-08 (all 15 fields). **Entregado:** present, passing (1 passed).
- [x] `test_core.py::test_healthy_feed_payload_emits_no_missing_for_the_conditional_error_fields` — criterio 3 / D-09. **Entregado:** present, passing (1 passed).
- [x] Framework install: **none** — everything already present. **Confirmado:** no package-manager commands in phase diff.

**Todos los ítems de Wave 0 quedaron cerrados en disco** (re-verificado 2026-09-02, no heredado del draft). Ésa es la base de `wave_0_complete: true`.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `get_segments()` before/after against the live Phase 42 capture | SHAPE-01 (crit. 2) | The capture (`market-data-wire-segments-42.json`) is gitignored and T-42-05 prohibits transcribing raw payload values into tests — evidence must stay documentary | Read the capture's key-set (never its values) against F-214…F-218 in `market-data-client-findings.md`; document the before/after key-set diff in SUMMARY.md, never the raw payload |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies — 11 of 12 rows carry a re-run automated command; the 1 remaining row is correctly declared `manual-only` with named evidence
- [x] Sampling continuity: no 3 consecutive tasks without automated verify — confirmed by the map above
- [x] Wave 0 covers all MISSING references — all 8 Wave 0 items exist on disk and pass, re-verified 2026-09-02
- [x] No watch-mode flags — no command in this map uses `--watch`
- [x] Feedback latency < 5s — full `test_core.py` (174 tests) + `test_decode.py` (77 tests) run in ~0.2s combined
- [x] `nyquist_compliant: true` set in frontmatter — based on every row above being independently re-run in this audit, not inherited from the draft

**Approval:** closed 2026-09-02 by `/gsd-validate-phase 43` (retroactive audit ahead of `/gsd-complete-milestone v1.8`). Two of the draft's originally-speced `Automated Command` strings (43-01-04, 43-03-01) pointed at non-matching `-k` filters — corrected in the map above to the actual test name/location; no missing coverage, only stale command pointers from the pre-execution draft.

---

## Validation Audit 2026-09-02

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 (2 stale command pointers corrected, no new tests needed) |
| Escalated | 0 |

This VALIDATION.md was seeded by plan-phase before Phase 43 executed and was never reconciled
afterward (`status: draft`, #2117). All 12 mapped behaviors were independently re-run against the
live codebase in this audit: 0 MISSING, 0 PARTIAL — every behavior the draft named already has
passing coverage, either under the exact command originally speced or under a corrected pointer to
where the assertion actually lives (see 43-01-04, 43-03-01 above).
