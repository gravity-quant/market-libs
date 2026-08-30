---
phase: 37
slug: matriz-client-dicts-residuales-tipados-alias
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-29
---

# Phase 37 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3+ with pytest-asyncio (`asyncio_mode = "auto"`), pytest-httpx |
| **Config file** | root `pyproject.toml` `[tool.pytest.ini_options]`, `pythonpath = ["."]` |
| **Quick run command** | `uv run --package matriz-client pytest packages/matriz-client/tests -q` |
| **Full suite command** | `uv run --package matriz-client pytest packages/matriz-client/tests -q && uv run mypy packages/matriz-client/src && uv run python tools/check_surface_types.py && uv run python tools/check_decode_intactness.py` |
| **Estimated runtime** | ~26 seconds (488 tests, baseline measured 25.64s) |

---

## Sampling Rate

- **After every task commit:** Run `uv run --package matriz-client pytest packages/matriz-client/tests -q`
- **After every plan wave:** Run full suite command + all four `tools/` gates
- **Before `/gsd-verify-work`:** Full suite must be green (cross-package gate — all six packages' tests)
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 37-01-xx | TBD | 1 | NOBJ-MTZ-01 | — | Gate detects a reintroduced `dict[str, Any]` field | unit | `pytest packages/matriz-client/tests/test_surface_types_red.py -x` | ❌ Wave 0 | ⬜ pending |
| 37-01-xx | TBD | 1 | NOBJ-MTZ-01 | — | `UnknownFrame.raw` exemption is reachable, not dead code | unit | `pytest packages/matriz-client/tests/test_surface_types_red.py -k exempt -x` | ❌ Wave 0 | ⬜ pending |
| 37-01-xx | TBD | 1 | NOBJ-MTZ-01 | — | Gate stays green on the real tree after extension | unit | `pytest packages/iol-client/tests/test_surface_types_red.py::test_gate_is_green_on_the_real_tree -x` | ✅ (floors only) | ⬜ pending |
| 37-02-xx | TBD | 2 | NOBJ-MTZ-01 | — | Enveloped risk body populates `report`/`detailedAccountReports` | unit | `pytest packages/matriz-client/tests/test_core.py -k envelope -x` | ❌ Wave 0 | ⬜ pending |
| 37-03-xx | TBD | 3 | NOBJ-MTZ-01 | — | `tickPriceRanges` decodes the baseline into `dict[str, TickPriceRange]` | unit | `pytest packages/matriz-client/tests/test_models.py -k tickPriceRange -x` | ❌ Wave 0 | ⬜ pending |
| 37-03-xx | TBD | 3 | NOBJ-MTZ-01 | — | `portfolio` is `None` (not `{}`) on an empty payload | unit | `pytest packages/matriz-client/tests/test_decode.py -k portfolio -x` | ✅ exists, assertion flips | ⬜ pending |
| 37-03-xx | TBD | 3 | NOBJ-MTZ-01 | — | Undeclared inner keys surface as non-fatal `extra` divergences | unit | `pytest packages/matriz-client/tests/test_decode.py -k extra -x` | ✅ mechanism tested; needs new-model case | ⬜ pending |
| 37-03-xx | TBD | 3 | NOBJ-MTZ-01 | — | Mapping axis routes values through `walk_field` with the shared sink | unit | `pytest packages/matriz-client/tests/test_decode.py -k mapping -x` | ✅ exists, must be extended | ⬜ pending |
| 37-03-xx | TBD | 3 | NOBJ-MTZ-01 | — | `_convert` shim still coerces a bare `dict[str, Any]` | unit | `pytest packages/matriz-client/tests/test_decode.py -k convert -x` | ✅ exists, must keep passing | ⬜ pending |
| 37-04-xx | TBD | 4 | NOBJ-MTZ-02 | — | All six aliases return their wire field, identically | unit | `pytest packages/matriz-client/tests/test_null_object.py -k alias -x` | ❌ Wave 0 (fixture case exists) | ⬜ pending |
| 37-04-xx | TBD | 4 | NOBJ-MTZ-02 | — | Aliases work on a REST-parsed and a WS-parsed snapshot | unit | `pytest packages/matriz-client/tests/test_null_object.py -k alias_surfaces -x` | ❌ Wave 0 | ⬜ pending |
| 37-04-xx | TBD | 4 | NOBJ-MTZ-02 | — | Aliases remain invisible to the walker (no divergence delta) | unit | `pytest packages/matriz-client/tests/test_null_object.py::test_adding_a_property_alias_does_not_change_the_divergence_count -x` | ✅ exists — do not rewrite | ⬜ pending |
| 37-xx | TBD | any | SC-4 | — | WS daemon-thread paths stay green incl. per-connection decode mode | unit | `pytest packages/matriz-client/tests/test_ws_client.py packages/matriz-client/tests/test_ws_decode_mode.py -x` | ✅ exists | ⬜ pending |
| 37-xx | TBD | any | SC-3 | — | `mypy --strict` clean over the package | typecheck | `uv run mypy packages/matriz-client/src` | ✅ green today | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `packages/matriz-client/tests/test_surface_types_red.py` — NEW; covers NOBJ-MTZ-01 gate non-vacuity + exemption reachability. Mirror `packages/iol-client/tests/test_surface_types_red.py` structure (`_write_fake_package` helper, `check_surface_types(root=tmp_path)`).
- [ ] Envelope regression cases in `packages/matriz-client/tests/test_core.py` — enveloped body populates; flat body raises `PrimaryAPIError`.
- [ ] Alias assertions on the real `MarketDataSnapshot` in `test_null_object.py`, exercising both a REST-parsed and a WS-frame-parsed instance.
- [ ] `tickPriceRanges` decode case driven from the committed baseline JSON.
- Framework install: **not needed** — pytest/pytest-httpx/mypy/ruff all present and green.

---

## Manual-Only Verifications

*None: all phase behaviors have automated verification. Live-network verification of the three Risk-endpoint fields (`report`, `detailedAccountReports`, `portfolio`) is blocked by policy assert D-MATZ-33 and explicitly deferred to Phase 39 (`LIVE-NOBJ-01`) — not a gap in this phase's own validation contract.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
