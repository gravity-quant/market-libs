---
phase: 43
slug: market-data-client-forma-de-instrument-segment-5-claves-extr
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-31
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
| 43-01-01 | 01 | 0 | SHAPE-01 | V5 | `Instrument` declares exactly the 10 wire fields + `marketId` alias | unit | `uv run pytest packages/market-data-client/tests/test_reference_models.py::test_instrument_field_set_matches_reconciled_wire -x -q --no-cov` | ❌ W0 | ⬜ pending |
| 43-01-02 | 01 | 0 | SHAPE-01 | V5 | `Segment` declares exactly `{segment, live_instruments}` | unit | `uv run pytest packages/market-data-client/tests/test_reference_models.py::test_segment_field_set_matches_reconciled_wire -x -q --no-cov` | ❌ W0 | ⬜ pending |
| 43-01-03 | 01 | 0 | SHAPE-01 | V5 (Tampering mitigation) | `Instrument.marketId` mirrors `market_id`; explicit `marketId` always wins | unit | `uv run pytest packages/market-data-client/tests/test_reference_models.py::test_instrument_market_id_alias_mirrors_wire_snake_case test_reference_models.py::test_instrument_explicit_camel_case_payload_key_still_wins -x -q --no-cov` | ❌ W0 | ⬜ pending |
| 43-01-04 | 01 | 0 | SHAPE-01 | — | `Instrument.instrumentType` no longer exists | unit | `uv run pytest packages/market-data-client/tests/test_reference_models.py -k instrumentType -x -q --no-cov` | ❌ W0 | ⬜ pending |
| 43-02-01 | 02 | 1 | SHAPE-01 (crit. 2) | — | `get_segments()` over the real envelope returns populated rows | unit | `uv run pytest packages/market-data-client/tests/test_reference_envelope_unwrap.py -x -q --no-cov` | ⚠️ partial (fixture correct, value assertion missing) | ⬜ pending |
| 43-02-02 | 02 | 1 | SHAPE-01 (crit. 2) | — | Before/after measured against Phase 42 capture | manual (1×) | capture read + F-214…F-218 census documented in SUMMARY | n/a — documentary evidence, not a test | ⬜ pending |
| 43-03-01 | 03 | 0 | HARN-02 | V5, V7 | The 5 `extra` keys are declared and decode without `extra` | unit | `uv run pytest packages/market-data-client/tests/test_core.py -k _MEASURED_HEALTH_FEED_43 -x -q --no-cov` | ❌ W0 | ⬜ pending |
| 43-03-02 | 03 | 0 | HARN-02 (crit. 3) | — | No measured `extra` flips to `missing` on a healthy payload | unit | `uv run pytest packages/market-data-client/tests/test_core.py -x -q --no-cov` (re-derived T14, `test_core.py:1125-1137`) | ⚠️ re-derive | ⬜ pending |
| 43-03-03 | 03 | 0 | HARN-02 (crit. 4) | — | Every fixture key ⊆ measured key-set | unit | `uv run pytest packages/market-data-client/tests/test_core.py::test_every_fixture_key_is_a_measured_wire_key -x -q --no-cov` | ❌ W0 (D-13 helper) | ⬜ pending |
| 43-04-01 | 04 | 1 | SHAPE-01+HARN-02 | — | Exact optionals set reflects D-03/D-09/D-10 | unit | `uv run pytest packages/market-data-client/tests/test_core.py -x -q --no-cov` (re-derive T11, `:1183-1199`) | ⚠️ re-derive | ⬜ pending |
| 43-04-02 | 04 | 1 | SHAPE-01 | Tampering mitigation | Exact overrides set reflects D-04 | unit | `uv run pytest packages/market-data-client/tests/test_decode.py -x -q --no-cov` (re-derive T10, `:1339-1360`) | ⚠️ re-derive | ⬜ pending |
| 43-05-01 | 05 | 1 | D-14 | — | Async surface identical to sync (fixtures re-derived, zero source diff) | unit | `uv run pytest packages/market-data-client/tests/test_reference_client.py packages/market-data-client/tests/test_reference_async_client.py -x -q --no-cov` | ✓ exists; re-derive fixtures (T7) | ⬜ pending |
| 43-06-01 | 06 | 2 | D-15 | — | All 4 CI gates green | integration | `uv run ruff check . && uv run ruff format --check . && uv run python tools/check_surface_types.py && uv run mypy && uv run mypy packages/market-data-client/tests && uv run pytest packages/market-data-client -q` | ✓ all pre-existing | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*Task IDs above are illustrative — the planner assigns final plan/wave numbers; this map is the requirement→test contract, not a binding task schedule.*

---

## Wave 0 Requirements

- [ ] `test_reference_models.py::test_instrument_field_set_matches_reconciled_wire` — SHAPE-01 (copy pattern from `Symbol` field-set test at `:219` / `CalendarConfig` at `:167`)
- [ ] `test_reference_models.py::test_segment_field_set_matches_reconciled_wire` — SHAPE-01 (same pattern)
- [ ] `test_reference_models.py::test_instrument_market_id_alias_mirrors_wire_snake_case` — D-04 (copy `Symbol` alias test at `:262`)
- [ ] `test_reference_models.py::test_instrument_explicit_camel_case_payload_key_still_wins` — D-04 (copy `Symbol` twin at `:272`)
- [ ] `test_core.py::_MEASURED_HEALTH_FEED_43` (fixture) + `_keys_recursive` + `test_every_fixture_key_is_a_measured_wire_key` — D-13 / criterio 4
- [ ] `test_core.py::test_feed_subscription_decodes_the_measured_blob` — D-08 (all 15 fields)
- [ ] `test_core.py::test_healthy_feed_payload_emits_no_missing_for_the_conditional_error_fields` — criterio 3 / D-09
- [ ] Framework install: **none** — everything already present

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `get_segments()` before/after against the live Phase 42 capture | SHAPE-01 (crit. 2) | The capture (`market-data-wire-segments-42.json`) is gitignored and T-42-05 prohibits transcribing raw payload values into tests — evidence must stay documentary | Read the capture's key-set (never its values) against F-214…F-218 in `market-data-client-findings.md`; document the before/after key-set diff in SUMMARY.md, never the raw payload |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
