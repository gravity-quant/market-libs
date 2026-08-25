---
phase: 32
slug: gates-de-homogeneidad-d-16
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-25
---

# Phase 32 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 + pytest-asyncio (`asyncio_mode = "auto"`) |
| **Config file** | `pyproject.toml:102-120` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `uv run pytest packages/<pkg> -q` |
| **Full suite command** | `uv run pytest packages -q` (1682 tests) |
| **Estimated runtime** | full suite: low tens of seconds; `check_surface_types.py` / `lint-imports`: sub-second each |

---

## Sampling Rate

- **After every task commit:** `uv run pytest packages/<pkg> -q` for the touched package, plus `uv run python tools/check_surface_types.py` whenever the surface gate itself is touched
- **After every plan wave:** `uv run ruff check . && uv run mypy && uv run pytest packages -q`
- **Before `/gsd-verify-work`:** Full CI matrix must be green — including the per-package mypy loop, which is RED today (33 errors) and is itself part of Wave 0
- **Max feedback latency:** ~10 seconds (fast local suite; no watch mode, no external services)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 32-00-01 | 00 | 0 | Criterion 5 | — | Fix 33 pre-existing mypy errors (matriz 29, higyrus 2, ambito 2) in Phase-29 test files so CI can go green | typecheck | `uv run mypy` | ❌ W0 | ⬜ pending |
| 32-01-01 | 01 | 1 | GATE-TYP-01(a) | V5/V7 | `tools/check_surface_types.py` walks `__all__` incl. class methods, AST-only, fails on `Any`/`dict[str, Any]` with DT-06 exemptions | unit | `uv run python tools/check_surface_types.py` | ❌ W1 | ⬜ pending |
| 32-01-02 | 01 | 1 | GATE-TYP-01(a) | — | New gate wired as a step in the existing `lint` CI job (not a new job) | CI | new step in `.github/workflows/ci.yml` `lint` job | ❌ W1 | ⬜ pending |
| 32-01-03 | 01 | 1 | GATE-TYP-01(b) | Repudiation | RED fixture with an injected `dict[str, Any]` return makes the gate fail; test proves it | unit | `uv run pytest packages/<pkg>/tests/test_surface_types_red.py -x` | ❌ W1 | ⬜ pending |
| 32-02-01 | 02 | 2 | GATE-TYP-01(b) | — | Sync/async parity by introspection (`dir()`+`__module__` filter, `get_type_hints()` w/ normalization rules), per package, lower-bound non-vacuous | unit | `uv run pytest packages/<pkg>/tests/test_surface_parity.py -x` (×6) | ❌ W2 | ⬜ pending |
| 32-02-02 | 02 | 2 | GATE-TYP-01(b) | — | wallets' missing `Client` on async side is asserted explicitly, not silently skipped | unit | `packages/wallets-client/tests/test_surface_parity.py` | ❌ W2 | ⬜ pending |
| 32-02-03 | 02 | 2 | D-09 | V14 | `market_data_client.aio.configure` gains `http_client: httpx.AsyncClient \| None` param (closes real drift found by parity test) | unit + behavior | parity test above + `packages/market-data-client/tests/test_configure*.py` | ❌ W2 | ⬜ pending |
| 32-03-01 | 03 | 3 | GATE-TYP-01(c) | — | mypy `files` includes `packages/market-data-client/src` (zero-fix, already passes) | typecheck | `uv run mypy` → 75 files, 0 errors | ❌ W3 (one-line) | ⬜ pending |
| 32-03-02 | 03 | 3 | GATE-TYP-01(c) | Tampering | `market_data_client._core` import-linter contract is RED-proven (contract mutated in test, restored via `try/finally`) | integration | `uv run pytest packages/market-data-client/tests/test_core_boundary_red.py -x` | ❌ W3 | ⬜ pending |
| 32-03-03 | 03 | 3 | GATE-TYP-01(c) | — | `wallets_client` exclusion from import-linter `root_packages` and `verification/test_public_surface._PACKAGES` scope documented inline, not silently left | manual/review | comment at `verification/test_public_surface.py:46` + import-linter config comment | ❌ W3 | ⬜ pending |
| 32-04-01 | 04 | 4 | Criterion 5 | — | Full CI matrix (6 pkgs × py3.12 + py3.13) green with all new gates active | CI | `gh run list --workflow=ci.yml` / all jobs pass | ❌ W4 (final) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `packages/matriz-client/tests/test_decode.py` + `test_ws_decode_mode.py` — fix 29 mypy errors
- [ ] `packages/higyrus-client/tests/test_decode.py` — fix 2 mypy errors
- [ ] `packages/ambito-financiero-client/tests/test_decode.py` — fix 2 mypy errors
- [ ] No framework install needed — pytest/mypy/ruff/import-linter all present and locked in `uv.lock`

*This Wave 0 is unbudgeted pre-existing breakage (Phase 29 test files, never CI-validated since 2026-08-18 due to `paths-ignore: ["**.md"]` on subsequent docs-only commits) — required because success criterion 5 explicitly demands full CI green, and the new gates in Waves 1-3 cannot be verified as passing in CI while the typecheck job is already red for unrelated reasons.*

---

## Manual-Only Verifications

*None — all phase behaviors have automated verification. D-02's import-linter RED-proof was initially proposed as a manual demonstration (per Phase 30 D-10 precedent) but research measured `lint-imports` at ~0.07s cold, making the automated subprocess/mutation test cheap; use the automated route instead (see Sources in RESEARCH.md).*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (33 mypy errors across 3 packages)
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
