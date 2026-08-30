---
phase: 39
slug: verificaci-n-en-vivo-del-encadenamiento-profundo
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-29
---

# Phase 39 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3+ with pytest-asyncio (`asyncio_mode = "auto"`), pytest-httpx 0.34+, pytest-cov |
| **Config file** | root `pyproject.toml` `[tool.pytest.ini_options]` (`testpaths = ["packages", "tests", "verification"]`, `--import-mode=importlib`, `--strict-markers`) |
| **Quick run command** | `uv run --frozen python -m pytest -q verification/test_main_<pkg>_deep_chain.py` |
| **Full suite command** | `uv run --frozen python -m pytest -q packages/<pkg>` (per package, mirrors CI) |
| **Estimated runtime** | ~30s per package unit suite; live driver runs are separate (network-bound, minutes) |

---

## Sampling Rate

- **After every task commit:** `uv run --frozen ruff check . && uv run --frozen ruff format --check . && uv run --frozen mypy` + the touched deep-chain lock (AST test)
- **After every plan wave:** `uv run --frozen python -m pytest -q packages/<touched-pkg>` + the full explicit `verification/` allowlist from `ci.yml:80-84`, **including newly appended files**
- **Before `/gsd-verify-work`:** all 6 packages × py3.12/3.13 green, plus the widened `verification/` allowlist green
- **Max feedback latency:** ~30s (unit/AST tests); live-run verification is manual/measured, not part of the fast loop

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 39-01-01 | TBD | 0 | LIVE-NOBJ-01 (SC-1 classification, D-01) | — | New skip line matches `_ENV_SKIP`; `SKIPPED (mutating, guard off)` still does not | unit | `pytest -q verification/test_main_verify_classification.py` | ❌ Wave 0 | ⬜ pending |
| 39-01-02 | TBD | 0 | LIVE-NOBJ-01 (SC-1 classification shape, D-01/Pitfall 2) | — | Emitted skip line shape (colon-present) mirrors market-data precedent | unit | `pytest -q verification/test_main_<pkg>_skip_line_shape.py` | ❌ Wave 0 | ⬜ pending |
| 39-01-03 | TBD | 0 | LIVE-NOBJ-01 (D-02 allowlist) | T-39-01 | D-MATZ-33 exact-equality allowlist admits `bbsa.matrizoms.com.ar`, rejects substring/userinfo spoofing variants | unit | `pytest -q verification/test_main_matriz_deep_chain.py::test_d_matz_33_allowlist` (or dedicated file) | ❌ Wave 0 | ⬜ pending |
| 39-01-04 | TBD | 0 | LIVE-NOBJ-01 (SC-3 non-vacuous closure, D-09) | — | `verify_cycle_closure` PASS requires positive probe-count evidence per package, not absence of findings | unit | `pytest -q verification/test_cycle_closure_phase33.py` | ✅ exists (currently red — stale `_CENSUS` path; repoint + extend) | ⬜ pending |
| 39-02-01 | TBD | 1 | LIVE-NOBJ-01 (SC-1 iol, D-03) | — | `probe_get_quote_{sync,async}` / `probe_get_instruments_by_type_{sync,async}` dereference `.puntas.*` inside `try` body, above a floor | unit (AST) | `pytest -q verification/test_main_iol_deep_chain.py` | ❌ Wave 1 | ⬜ pending |
| 39-02-02 | TBD | 1 | LIVE-NOBJ-01 (SC-1 higyrus, D-04) | — | Chosen posiciones probe builds `Posicion.from_api` and dereferences `.parking[...]`, both surfaces, zero extra HTTP calls | unit (AST) | `pytest -q verification/test_main_higyrus_deep_chain.py` | ❌ Wave 1 | ⬜ pending |
| 39-02-03 | TBD | 1 | LIVE-NOBJ-01 (SC-1 matriz, D-05) | — | `probe_get_market_data{,_async}` dereference all 6 aliases off `MarketDataSnapshot`, inside `try` body, both surfaces (sync + async) | unit (AST) | `pytest -q verification/test_main_matriz_deep_chain.py` | ❌ Wave 1 | ⬜ pending |
| 39-02-04 | TBD | 1 | LIVE-NOBJ-01 (SC-1 ámbito, D-06 declared absence) | — | ámbito still declares zero model classes / empty `__all__` | unit (AST) | `pytest -q verification/test_cycle_closure_phase33.py::_ambito_declares_zero_models` | ✅ exists | ⬜ pending |
| 39-02-05 | TBD | 1 | LIVE-NOBJ-01 (SC-2 edge cases, D-12) | — | No chain raises `AttributeError`/`TypeError` on empty/absent/204/null mocked payloads | unit (mocked) | `pytest -q packages/<pkg>/tests/test_deep_chain_edges.py` | ❌ Wave 1 | ⬜ pending |
| 39-03-01 | TBD | 2 | LIVE-NOBJ-01 (SC-3 in-cycle fix, D-08) | — | Each CONFIRMED divergence found live is fixed with sync+async mirror and pinned by a mocked regression | unit (mocked) | `pytest -q packages/<pkg>/tests/` | ❌ per-fix (unknown until live run) | ⬜ pending |
| 39-03-02 | TBD | 2 | LIVE-NOBJ-01 (SC-4 census, D-10/D-11) | — | `39-CENSUS.md` exists, uses `(slug, model, field_path, kind)` triple unit, separates Null-Object-policy collapse from real fixes, cites source columns | manual (artifact review) | — | ❌ Wave 2 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `verification/test_main_verify_classification.py` — covers SC-1 classification (D-01): env-skip→SKIPPED, new measured-skip→SKIPPED, rc!=0→FAILED, else RAN; market-data + wallets unaffected
- [ ] `verification/test_main_matriz_skip_line_shape.py` / `verification/test_main_higyrus_skip_line_shape.py` — covers the colon-shape contract (Pitfall 2), mirrors `test_main_market_data_skip_line_shape.py`
- [ ] `verification/test_main_iol_deep_chain.py` — AST lock for SC-1 (D-03)
- [ ] `verification/test_main_higyrus_deep_chain.py` — AST lock for SC-1 (D-04)
- [ ] `verification/test_main_matriz_deep_chain.py` — AST lock for SC-1 (D-05), including the D-02 allowlist behavior
- [ ] `packages/<pkg>/tests/test_deep_chain_edges.py` ×3 (iol, higyrus, matriz) — mocked empty/absent/204 edge-case coverage for SC-2
- [ ] **`.github/workflows/ci.yml:80-84`** — append every new `verification/` file to the explicit allowlist in the same commit that adds it, or the lock is inert (documented Phase 36 defect, WR-01)
- [ ] `verification/test_cycle_closure_phase33.py` — repoint stale `_CENSUS` path to `.planning/milestones/v1.6-phases/33-…/33-CENSUS.md`, extend for D-09 non-vacuity
- [ ] Framework install: none required (all dependencies already pinned in `uv.lock`)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|--------------------|
| Live driver run per in-scope package (iol, higyrus, matriz, ambito) reports PASS/SKIPPED with measured cause and named destination | LIVE-NOBJ-01 (SC-1) | Depends on live third-party API availability, DNS, and market-hours state at execution time — not reproducible in a mocked unit test | Run `uv run --package <pkg> python main_<pkg>.py`; inspect stdout classification line and `.planning/verification/<pkg>-findings.md` |
| matriz D-12 market-closed vs. mis-modelled discrimination | LIVE-NOBJ-01 (SC-2) | Requires running inside (or explicitly outside, with the `LA.date` staleness guard) an ARG trading-session window | Run matriz driver during/outside session hours; record window and guard outcome in `39-CENSUS.md` |
| Census contrast against `33-CENSUS.md` and `29-SIZING.md`, with Null-Object-collapse vs. real-fix split | LIVE-NOBJ-01 (SC-4) | Requires cross-referencing multiple historical artifacts and applying judgment documented in `35-RETIRED-TRIPLES.md`; not a pass/fail unit assertion | Author `39-CENSUS.md` per the D-10/D-11 method; cross-check triple-dump (Pattern 4, seam 1) against findings-file parse (seam 2) |
| D-02 operator checkpoint (hostname allowlist widening) | LIVE-NOBJ-01 (security) | Security-policy-adjacent change requires explicit human sign-off per project precedent (D-08/D-18), not just automated test passage | Confirm operator sign-off is recorded in code comment + phase report before merging the allowlist change (already given 2026-08-29, memory `project_matriz_bbsa_sandbox.md` — must still be surfaced as a blocking checkpoint per `mode: yolo` override note in RESEARCH.md Security Domain) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s (fast loop); live-run and census steps are explicitly manual per above
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
