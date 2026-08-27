---
phase: 33
slug: verificaci-n-en-vivo-en-modo-estricto-fixes
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-26
---

# Phase 33 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 + pytest-asyncio (`asyncio_mode = "auto"`) + pytest-httpx |
| **Config file** | root `pyproject.toml` `[tool.pytest.ini_options]` (`testpaths = ["packages", "tests", "verification"]`, `pythonpath = ["."]`, `--import-mode=importlib`, `--strict-markers`) |
| **Quick run command** | `uv run pytest packages/<pkg> -q` |
| **Full suite command** | `uv run pytest packages -q` (matches CI: per-package × py3.12/3.13) |
| **Estimated runtime** | ~30s per package quick run; ~828s for a full `verification/` sweep (currently red — see below) |

**CI reality:** the CI `test` job runs `pytest packages/${{ matrix.package }}` — an explicit path that overrides `testpaths`. `verification/` and `tests/` have never executed in CI, so its current red state (19 failed / 362 passed / 19 errors) is pre-existing rot, not a Phase 33 regression signal.

---

## Sampling Rate

- **After every task commit:** `uv run ruff check . && uv run ruff format --check . && uv run pytest packages/<pkg> -q`
- **After every plan wave:** `uv run pytest packages -q` + `uv run python tools/check_decode_intactness.py` + `uv run python tools/check_surface_types.py` + `uv run mypy` + targeted `uv run pytest verification/test_divergences.py verification/test_main_drivers_bare_except.py -q`
- **Before `/gsd-verify-work`:** full CI-equivalent green (lint + pre-commit + mypy + `pytest packages` ×2 Python versions) **plus** `verify_cycle_closure` non-vacuous ×5 **plus** the two new artifacts (`33-CENSUS.md`, `33-LITERALS.md`)
- **Max feedback latency:** ~30s (quick command)

**Do not gate on an unqualified `uv run pytest` or a full `pytest verification` run** — `verification/` is red today and takes ~14 minutes (P-13). Baseline it in Wave 0 and compare against that baseline, not against zero.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 33-01-XX | TBD | 0 | LIVE-TYP-01 (c1) | — | Handler maps a 6-key record to a `SHAPE` finding with the right slug/surface | unit | `uv run pytest verification/test_divergences.py -q` | ❌ Wave 0 | ⬜ pending |
| 33-01-XX | TBD | 0 | LIVE-TYP-01 (c1) | — | `emit` never raises out; failures recorded in `errors` | unit | `verification/test_divergences.py::test_emit_never_raises` | ❌ Wave 0 | ⬜ pending |
| 33-01-XX | TBD | 0 | LIVE-TYP-01 (c1) | — | Install CM raises package loggers to `INFO`, restores on exit, `logging.root` untouched | unit | `verification/test_divergences.py::test_install_sets_level_and_restores` | ❌ Wave 0 | ⬜ pending |
| 33-01-XX | TBD | 0 | LIVE-TYP-01 (c1) | — | `INFO`-kind (`extra`) records reach the handler | unit | `verification/test_divergences.py::test_extra_kind_is_captured` | ❌ Wave 0 | ⬜ pending |
| 33-01-XX | TBD | 0 | LIVE-TYP-01 (c1) | — | Endpoint/surface ContextVars visible inside `emit`, reset after probe | unit | `verification/test_divergences.py::test_probe_context_binding` | ❌ Wave 0 | ⬜ pending |
| 33-XX-XX | TBD | N | LIVE-TYP-01 (c1) | — | Live strict run per package, both surfaces | manual — live API | `MARKET_LIBS_STRICT_DECODE=1 uv run --package <pkg> python main_<x>.py` | n/a (operator/agent-run) | ⬜ pending |
| 33-XX-XX | TBD | N | LIVE-TYP-01 (c2) | — | One mocked regression per confirmed fix, mirrored sync+async | unit | `uv run pytest packages/<pkg>/tests/test_<fix>.py -q` | ❌ per fix | ⬜ pending |
| 33-XX-XX | TBD | N | LIVE-TYP-01 (c2) | — | No sync/async drift introduced by a fix | unit | `uv run pytest packages/<pkg>/tests/test_surface_parity.py -q` | ✅ exists | ⬜ pending |
| 33-XX-XX | TBD | N | LIVE-TYP-01 (c3) | — | `Literal` census produced, DT-07 closure documented | manual — artifact review | `33-LITERALS.md` present with populated observed-values table | ❌ Wave 0 artifact | ⬜ pending |
| 33-XX-XX | TBD | N | LIVE-TYP-01 (c3) | — | matriz's 4 `Literal` aliases still decode without enforcement (D-09 not violated) | unit | `uv run pytest packages/matriz-client/tests/test_decode.py packages/matriz-client/tests/test_types.py -q` | ✅ exists | ⬜ pending |
| 33-XX-XX | TBD | N | LIVE-TYP-01 (c4) | — | `verify_cycle_closure` PASS non-vacuously per package | unit | new `verification/test_cycle_closure_phase33.py` asserting `(True, [])` and inspected-count ≥ N | ❌ Wave 0 | ⬜ pending |
| 33-XX-XX | TBD | N | LIVE-TYP-01 (c4) | — | Schema snapshots reconciled, no unexplained drift | manual — artifact review | diff of `.planning/verification/schemas/` after the run | n/a | ⬜ pending |
| 33-XX-XX | TBD | N | LIVE-TYP-01 (c5) | — | Live census contrasted with the ≥96 floor; excess re-scoped to named phases | manual — artifact review | `33-CENSUS.md` present with per-package table and a named destination for every deferred finding | ❌ Wave 0 artifact | ⬜ pending |
| CI-01 | — | 0 | CI non-regression | — | Bare-except AST gate still green for matriz + higyrus | unit | `uv run pytest verification/test_main_drivers_bare_except.py -q` | ✅ exists | ⬜ pending |
| CI-02 | — | 0 | CI non-regression | — | Single-Client AST gate still green ×5 | unit | `uv run pytest verification/ -q -k uses_single_client_instance` | ✅ exists | ⬜ pending |
| CI-03 | — | 0 | CI non-regression | — | `_decode.py` intactness digest unchanged | script | `uv run python tools/check_decode_intactness.py` | ✅ exists | ⬜ pending |
| CI-04 | — | 0 | CI non-regression | — | Surface types + uniform structure gates | script | `uv run python tools/check_surface_types.py && uv run python tools/check_uniform_structure.py` | ✅ exists | ⬜ pending |

*Task IDs are placeholders (`TBD` / `XX`) — the planner assigns concrete plan/task IDs; this map's requirement→test coverage must carry forward unchanged.*

---

## Wave 0 Requirements

- [ ] `verification/test_divergences.py` — handler mapping, non-raising `emit`, level install/restore, `extra`-kind capture, ContextVar binding (covers criterion 1's mechanism)
- [ ] `verification/test_cycle_closure_phase33.py` — non-vacuity assertion for criterion 4
- [ ] AST-gate extension (optional but recommended): assert every `probe_*` in the five drivers carries the context decorator — extending the anti-vacuity pattern `test_main_*_uses_single_client_instance.py` already establishes
- [ ] Post-run consistency assertion: `FINDING=N` in the SUMMARY == new `### F-` blocks in the findings file (catches the P-3 silent-suppression regression class)
- [ ] Red-baseline capture for `verification/` (`pytest verification -q --tb=no -rfE` → committed artifact) so Phase 33 regressions are distinguishable from the 19 failures / 19 errors already present (P-13)
- [ ] Framework install: none needed — pytest/pytest-httpx/pytest-asyncio all present

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live strict-mode run per package, both surfaces | LIVE-TYP-01 (c1) | Depends on live third-party API availability/creds — not mockable without defeating the phase's purpose | `MARKET_LIBS_STRICT_DECODE=1 uv run --package <pkg> python main_<x>.py` for ámbito, iol, higyrus, matriz, and `main_market_data.py` against `develop` with operator Auth0 creds |
| `Literal` census artifact review | LIVE-TYP-01 (c3) | Requires human/agent judgment reconciling observed values against the Phase 29 D-lock | Confirm `33-LITERALS.md` has a populated observed-values table and an explicit disposition (promote/document) per Literal |
| Schema snapshot reconciliation | LIVE-TYP-01 (c4) | Diff review against baseline requires interpreting whether drift is expected vs a regression | Diff `.planning/verification/schemas/` after the run; confirm no unexplained drift |
| Census-vs-floor artifact review | LIVE-TYP-01 (c5) | Re-scope decisions are judgment calls, not mechanically checkable | Confirm `33-CENSUS.md` has the per-package table and a named destination phase for every deferred finding |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
