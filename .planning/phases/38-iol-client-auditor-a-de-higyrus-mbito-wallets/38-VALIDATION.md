---
phase: 38
slug: iol-client-auditor-a-de-higyrus-mbito-wallets
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-29
---

# Phase 38 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest` >= 8.3 with `pytest-asyncio` (`asyncio_mode = "auto"`), `pytest-httpx` >= 0.34 |
| **Config file** | root `pyproject.toml`, `[tool.pytest.ini_options]` (`--import-mode=importlib`, `--strict-markers`, `pythonpath = ["."]`) |
| **Quick run command** | `uv run --package iol-client pytest packages/iol-client -q` |
| **Full suite command** | `uv run --package iol-client pytest packages/iol-client -q && uv run --package higyrus-client pytest packages/higyrus-client -q && uv run --package ambito-financiero-client pytest packages/ambito-financiero-client -q && uv run --package wallets-client pytest packages/wallets-client -q && uv run python tools/check_decode_intactness.py && uv run python tools/check_uniform_structure.py && uv run python tools/check_surface_types.py && uv run mypy packages/iol-client && uv run ruff check packages/iol-client` |
| **Estimated runtime** | ~15s quick / ~90s full suite |

---

## Sampling Rate

- **After every task commit:** Run `uv run --package iol-client pytest packages/iol-client -q` (or the affected package's leg) + `uv run ruff check <touched paths>`
- **After every plan wave:** Run all four package suites + the three `tools/` gates + `uv run mypy packages/iol-client`
- **Before `/gsd-verify-work`:** Full suite must be green — 289 / 289 / 208+1 / 10 as the floor (any decrease is a regression, an increase is expected from the new RED test)
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 38-01-01 | 01 | 0 | NOBJ-AUD-01 | — | N/A | unit (RED fixture) | `pytest packages/iol-client/tests/test_surface_types_red.py -k optional_model_field -q` | ❌ W0 | ⬜ pending |
| 38-01-02 | 01 | 0 | NOBJ-AUD-01 | — | N/A | unit (RED fixture) | `pytest packages/iol-client/tests/test_surface_types_red.py -k optional_literal_alias -q` | ❌ W0 | ⬜ pending |
| 38-02-01 | 02 | 1 | NOBJ-IOL-01 | — | N/A | unit | `pytest packages/iol-client/tests/test_models.py -k puntas -q` | ✅ | ⬜ pending |
| 38-02-02 | 02 | 1 | NOBJ-IOL-01 | — | N/A | unit | `pytest packages/iol-client/tests/test_models.py -k round_trip -q` | ✅ | ⬜ pending |
| 38-03-01 | 03 | 2 | NOBJ-IOL-01 | — | N/A | static | `uv run mypy packages/iol-client` | ✅ | ⬜ pending |
| 38-03-02 | 03 | 2 | NOBJ-IOL-01 | — | N/A | snapshot | `uv run python verification/regen_snapshots.py && git diff --stat verification/snapshots/iol-client-surface.txt` | ✅ | ⬜ pending |
| 38-04-01 | 04 | 2 | NOBJ-AUD-01 | — | N/A | unit | `pytest packages/matriz-client/tests/test_surface_types_red.py -q` (read-only regression check) | ✅ | ⬜ pending |
| 38-05-01 | 05 | 3 | NOBJ-AUD-01 | — | N/A | doc review | `checkpoint:human-verify` on `38-CENSUS.md` | ❌ manual | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `packages/iol-client/tests/test_surface_types_red.py` — add `test_an_optional_model_field_is_caught` (covers NOBJ-AUD-01 D-11 lower bound)
- [ ] `packages/iol-client/tests/test_surface_types_red.py` — add `test_an_optional_literal_alias_field_is_spared` (covers the D-01b narrowness corollary — must NOT reflag the 10 matriz `Literal | None` leaves)
- [ ] No framework install needed; no `conftest.py` changes needed

`tdd_mode` is enabled: the 7 migrated assertions in `test_models.py` (D-04, plus the round-trip assertion found in research) are themselves the RED step for the source change — write them before flipping the `puntas` annotations and confirm they fail for the stated reason, not by collection error.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `38-CENSUS.md` has zero rows without a disposition | NOBJ-AUD-01 | Census completeness (SC-2) is a documentation contract, not an executable assertion | Read `38-CENSUS.md`, confirm every row (higyrus/ámbito/wallets) has a disposition value; confirm zero-violation packages are enumerated, not omitted |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
