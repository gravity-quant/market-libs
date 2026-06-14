---
phase: 6
slug: compat-safety-net-client-class-skeleton
status: verified
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-10
revised: 2026-06-11
verified: 2026-06-11
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: synthesized from `06-RESEARCH.md ## Validation Architecture` (Dimension 8).
> Revised 2026-06-10 in response to checker B1/B2/B3/B5/W1: per-package guard test placement, baseline counts task, nyquist sign-off.
> Audited 2026-06-11 by Nyquist auditor: all 19 tasks flipped from pending to green; 3 secondary gaps filled with new automated tests in `verification/test_phase06_nyquist_gaps.py`.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3 + pytest-asyncio (auto) + pytest-httpx |
| **Config file** | `pyproject.toml` (root, `[tool.pytest.ini_options]`) — Plan 01 Task 1 adds `verification` to `testpaths` |
| **Quick run command** | `uv run pytest <pkg>/tests -q` per package (≤ 5 s per package on cache hit) |
| **Full suite command** | `uv run pytest -q` (392 tests: 277 baseline + 112 Phase 6 new + 3 nyquist gap tests) |
| **Estimated runtime** | ~30 s full suite; ~3–5 s per-package quick run |

Per-package commands (substitute `{pkg}` with `iol-client`, `higyrus-client`, `matriz-client`, `ambito-financiero-client`):

| Command | What it covers |
|---------|----------------|
| `uv run --package {pkg} pytest packages/{pkg}/tests -q` | Package-local mocked tests + per-package guard at `packages/{pkg}/tests/test_fixture_reaches_production.py` |
| `uv run pytest verification -q` | Cross-package shared harness: public surface snapshot, harness-mutation gate, nyquist gap tests |
| `uv run ruff check .` | Lint (TID, RUF, B) — class skeleton must comply |
| `uv run ruff format --check .` | Formatting parity |
| `uv run mypy --strict packages/{pkg}/src` | Strict types on the new `_ClientState` / `Client` / `AsyncClient` |
| `uv run --python 3.13 pytest -q` | B4 — Python 3.13 parity (Plan 07 Task 1 verify block) |
| `uv run --python 3.13 mypy --strict packages/{pkg}/src` | B4 — Python 3.13 type-check parity |

---

## Sampling Rate

- **After every task commit:** Run the relevant per-package quick command (`uv run --package {pkg} pytest packages/{pkg}/tests -q`) plus `uv run pytest verification -q` if any cross-package file was touched.
- **After every plan wave:** Run the full suite (`uv run pytest -q`) and `uv run ruff check . && uv run mypy --strict .`.
- **Before `/gsd-verify-work`:** Full suite + ruff + mypy strict must be green on Python 3.12 AND Python 3.13 (Plan 07 runs both explicitly per B4).
- **Max feedback latency:** 30 s (full suite). Per-package quick path < 5 s.

---

## Per-Task Verification Map

> Audited 2026-06-11 — all tasks flipped from ⬜ pending to ✅ green based on actual test execution.
> Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | Test File | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-----------|-------------|--------|
| 6-01-01 | 01 (snapshot harness) | 0 | REFAC-01 | — / SAFETY-NET-01 | Public surface drift is detected before refactor | snapshot/unit | `uv run pytest verification/test_public_surface.py -q` | `verification/test_public_surface.py` | ✅ | ✅ green |
| 6-01-02 | 01 | 0 | REFAC-01 | — | Snapshot fixture committed and deterministic; header is exactly 8 lines, line 8 == `#` (W3) | unit | `uv run pytest verification/test_public_surface.py -q` | `verification/snapshots/<pkg>-surface.txt` × 4 | ✅ | ✅ green |
| 6-01-03 | 01 | 0 | REFAC-01 | — | regen_snapshots.py is idempotent on a clean tree | unit | `uv run pytest verification/test_phase06_nyquist_gaps.py::test_snapshot_regen_is_idempotent -q` | `verification/test_phase06_nyquist_gaps.py` | ✅ (filled by audit) | ✅ green |
| 6-01-04 | 01 (baseline counts — B5) | 0 | REFAC-01 | — | Phase 6 entry-baseline test_count + coverage% captured before any refactor | unit | `uv run pytest verification/test_phase06_nyquist_gaps.py::test_phase_06_baseline_has_required_keys -q` | `verification/test_phase06_nyquist_gaps.py` | ✅ (filled by audit) | ✅ green |
| 6-02-01 | 02 (per-package guards — sync) | 0 | REFAC-01 | — / SAFETY-NET-02 | Sentinel token in production code path lands on the wire `Authorization` / `X-Auth-Token` / URL | behavior | `uv run pytest packages/*/tests/test_fixture_reaches_production.py -q -k sync` | `packages/<pkg>/tests/test_fixture_reaches_production.py` × 4 | ✅ | ✅ green |
| 6-02-02 | 02 (per-package guards — async) | 0 | REFAC-01 | — / SAFETY-NET-02 | Async sentinel reaches wire; matriz async is skip (Phase 10) | behavior | `uv run pytest packages/*/tests/test_fixture_reaches_production.py -q` | `packages/<pkg>/tests/test_fixture_reaches_production.py` × 4 (extended) | ✅ | ✅ green (7 passed + 1 skip) |
| 6-03-01 | 03 (ambito skeleton) | 1 | REFAC-02 | — | `Client`/`AsyncClient` exposed; `_ClientState` per instance; AsyncClient.__slots__ excludes _client_lock (B7) | unit + behavior | `uv run --package ambito-financiero-client pytest packages/ambito-financiero-client/tests -q` | `packages/ambito-financiero-client/tests/test_client_class.py` | ✅ | ✅ green (18 tests) |
| 6-03-02 | 03 | 1 | REFAC-02 | — | aio.py imports `_raise_for_response` from client.py (B8) | unit | `uv run pytest packages/ambito-financiero-client/tests/test_client_class.py::test_aio_imports_raise_for_response_from_client -q` | `packages/ambito-financiero-client/tests/test_client_class.py` | ✅ | ✅ green |
| 6-03-03 | 03 | 1 | REFAC-02 | — | Per-package guard still passes against refactored ambito | behavior | `uv run pytest packages/ambito-financiero-client/tests/test_fixture_reaches_production.py -q` | `packages/ambito-financiero-client/tests/test_fixture_reaches_production.py` | ✅ | ✅ green |
| 6-04-01 | 04 (iol skeleton) | 1 | REFAC-02 | — | Same as 6-03-01 for iol + OAuth refresh_token forward in shim allowlist | unit + behavior | `uv run --package iol-client pytest packages/iol-client/tests -q` + `uv run pytest verification -q` | `packages/iol-client/tests/test_client_class.py` | ✅ | ✅ green (26 tests) |
| 6-04-02 | 04 | 1 | REFAC-02 | — | W2 pre/post-edit grep gate returns zero hits — no legacy monkeypatch write sites | unit (source-grep) | `uv run pytest verification/test_phase06_nyquist_gaps.py::test_w2_iol_test_client_has_no_legacy_monkeypatch_write_sites -q` | `verification/test_phase06_nyquist_gaps.py` | ✅ (filled by audit) | ✅ green |
| 6-04-03 | 04 | 1 | REFAC-02 | — | aio.py imports `_raise_for_response` from client.py (B8) | unit | `uv run pytest packages/iol-client/tests/test_client_class.py::test_aio_imports_raise_for_response_from_client -q` | `packages/iol-client/tests/test_client_class.py` | ✅ | ✅ green |
| 6-04-04 | 04 | 1 | REFAC-02 | — | iol per-package guard MIGRATED to `configure(token=...)` and passes | behavior | `uv run pytest packages/iol-client/tests/test_fixture_reaches_production.py -q` | `packages/iol-client/tests/test_fixture_reaches_production.py` | ✅ | ✅ green |
| 6-05-01 | 05 (higyrus skeleton) | 1 | REFAC-02 | — | Same as 6-03-01 for higyrus + _token_ts → token_expires_at rename mapping | unit + behavior | `uv run --package higyrus-client pytest packages/higyrus-client/tests -q` | `packages/higyrus-client/tests/test_client_class.py` | ✅ | ✅ green (27 tests) |
| 6-05-02 | 05 | 1 | REFAC-02 | — | aio.py imports `_raise_for_response` from client.py (B8) | unit | `uv run pytest packages/higyrus-client/tests/test_client_class.py::test_aio_imports_raise_for_response_from_client -q` | `packages/higyrus-client/tests/test_client_class.py` | ✅ | ✅ green |
| 6-05-03 | 05 | 1 | REFAC-02 | — | higyrus per-package guard MIGRATED and passes | behavior | `uv run pytest packages/higyrus-client/tests/test_fixture_reaches_production.py -q` | `packages/higyrus-client/tests/test_fixture_reaches_production.py` | ✅ | ✅ green |
| 6-06-01 | 06 (matriz skeleton + stub AsyncClient) | 1 | REFAC-02 | — | `matriz_client.AsyncClient` stub present with `__aenter__`/`__aexit__`/`aclose()`; sync `Client` mirrors REST surface; X-Auth-Token header (D-22) | unit | `uv run --package matriz-client pytest packages/matriz-client/tests -q` | `packages/matriz-client/tests/test_client_class.py` | ✅ | ✅ green (28 tests) |
| 6-06-02 | 06 | 1 | REFAC-02 | — | No module-level `_ensure_token` callable in `matriz_client.client.__dict__` (W5) | unit | `uv run pytest packages/matriz-client/tests/test_client_class.py::test_no_module_level_ensure_token_callable -q` | `packages/matriz-client/tests/test_client_class.py` | ✅ | ✅ green |
| 6-06-03 | 06 | 1 | REFAC-02 | — | matriz per-package guard MIGRATED (sync) + matriz async stays skip | behavior | `uv run pytest packages/matriz-client/tests/test_fixture_reaches_production.py -q` | `packages/matriz-client/tests/test_fixture_reaches_production.py` | ✅ | ✅ green (1 passed + 1 skip) |
| 6-06-04 | 06 | 1 | REFAC-02 | — | verification/mutation_gate.py NOT in Plan 06 files_modified (B6) | invariant | `uv run pytest packages/matriz-client/tests/test_client_class.py::test_mutation_gate_reads_via_shim packages/matriz-client/tests/test_client_class.py::test_mutation_gate_blocks_non_sandbox_through_shim -q` | `packages/matriz-client/tests/test_client_class.py` | ✅ | ✅ green |
| 6-07-01 | 07 (CI green gate) | 2 | REFAC-01, REFAC-02 | — | All 277 baseline + Phase 6 new tests + ruff + mypy strict green on 3.12 AND 3.13 (B4) | regression | `uv run pytest -q && uv run --python 3.13 pytest -q && uv run ruff check . && uv run mypy --strict packages && uv run --python 3.13 mypy --strict packages` | n/a | ✅ (CI workflow file) | ✅ green (389+3=392 passed locally; 389 confirmed on 3.13 in Plan 07) |
| 6-07-02 | 07 | 2 | REFAC-01, REFAC-02 | — | Driver smoke via `python -m py_compile` (W4) | unit (syntax) | `uv run python -m py_compile main_iol.py main_higyrus.py main_matriz.py main_ambito_financiero.py` | `main_*.py` | ✅ | ✅ green |
| 6-07-03 | 07 | 2 | REFAC-01, REFAC-02 | — | mutation_gate audit confirms sandbox vs prod gating still works (B6 — Plan 07 owns audit) | behavior | `uv run pytest packages/matriz-client/tests/test_client_class.py::test_mutation_gate_reads_via_shim packages/matriz-client/tests/test_client_class.py::test_mutation_gate_blocks_non_sandbox_through_shim -q` | `packages/matriz-client/tests/test_client_class.py` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Wave 0 (executed first, before any refactor) must land the safety net:

- [x] `verification/test_public_surface.py` — snapshot harness + first run captures the baseline for all 4 packages (sync + async).
- [x] `verification/snapshots/<pkg>-surface.txt` × 4 — committed deterministic baselines with the 8-line `#` header (line 8 == `#`).
- [x] `verification/regen_snapshots.py` — operator script for intentional regeneration.
- [x] `verification/baselines/phase-06-baseline.txt` — Phase 6 entry-baseline (test_count + coverage% + git_sha + test ID list) per REFAC-01 (B5 fix).
- [x] `packages/ambito-financiero-client/tests/test_fixture_reaches_production.py` — per-package guard (B1 fix).
- [x] `packages/iol-client/tests/test_fixture_reaches_production.py` — per-package guard (B1 fix).
- [x] `packages/higyrus-client/tests/test_fixture_reaches_production.py` — per-package guard (B1 fix).
- [x] `packages/matriz-client/tests/test_fixture_reaches_production.py` — per-package guard, async stays skip (B1 fix).
- [x] NO shared `verification/test_fixture_reaches_production.py` — per-package layout eliminates the B3 write conflict.
- [x] `pyproject.toml` updated: `testpaths = ["packages", "tests", "verification"]`.
- [x] No new framework install required — pytest/pytest-httpx/pytest-asyncio already in `dev` group.

Per-package test additions (Wave 1) introduce `tests/test_client_class.py` in each of the 4 packages AND migrate each package's per-package guard file to `pkg.configure(token=...)`. Each Wave 1 plan owns its own guard file exclusively (B3).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `main_iol.py` / `main_higyrus.py` / `main_matriz.py` / `main_ambito_financiero.py` still run end-to-end against live APIs after the refactor | REFAC-02 (Success Criterion 4 — top-level API intact) | Live API calls hit third-party services — not appropriate for CI | `uv run --package <pkg> python main_<name>.py` with `.env` populated, confirm no exception + sensible output |
| CI matrix Python 3.13 parity | REFAC-02 (Success Criterion 5) | Local Task 1 step 2 + step 5 explicitly run `uv run --python 3.13` (B4); CI also runs the matrix | After push, check the GitHub Actions matrix job for 3.13 across all 4 packages → green |

---

## Validation Audit — 2026-06-11

**Auditor:** Nyquist adversarial auditor
**Phase state at audit time:** Merged to main (commit `fd7ab43`), security audit complete (`10278ec`), CI fixes applied (`bc16e26`, `2be4e90`, `9360cf5`). Full suite 389 passed, 1 skipped, 1 deselected.

### Audit Findings

All 5 Phase 6 Success Criteria had automated verification at the time of audit:

| Success Criterion | Coverage | Tests | Status |
|-------------------|----------|-------|--------|
| SC1: `verification/test_public_surface.py` snapshotting 4 packages | `verification/test_public_surface.py` | 4 parametrized | GREEN |
| SC2: fixture-reaches-production guard per package | `packages/*/tests/test_fixture_reaches_production.py` | 7 passing + 1 skip | GREEN |
| SC3: Client/AsyncClient with close/aclose/context-managers/_ClientState | `packages/*/tests/test_client_class.py` | 101 tests across 4 packages | GREEN |
| SC4: top-level API 100% functional; 277 baseline tests pass | Full suite | 389 passed (277 baseline + 112 new) | GREEN |
| SC5: ruff + mypy strict + pytest green on 3.12 AND 3.13 | Plan 07 CI gate | Verified both versions | GREEN |

### Secondary Gaps Found

Three verification entries in the Per-Task Verification Map had no dedicated pytest test — their verification was bash-only (one-shot commands, not permanent CI tests):

| Task ID | Gap | Impact |
|---------|-----|--------|
| 6-01-03 | Snapshot regen idempotency was verified by `regen + git diff --exit-code` shell command only; no pytest test would re-fail if regen became non-deterministic | Medium — any drift in regen_snapshots.py or public surface would go undetected until the next manual CI gate check |
| 6-01-04 | Baseline file key presence was verified by a `grep -qE` shell command; no pytest test would catch if the file became key-less | Low — baseline is immutable once committed, but a future phase creating a new baseline might omit required keys |
| 6-04-02 | W2 grep gate (zero legacy monkeypatch write sites in iol/test_client.py) had no enforcing test; a future PR could silently re-introduce a legacy write site | Medium — test corruption undetected: the shim read-path still works but a write via `monkeypatch.setattr(_token, X)` would write to the module dict, not to `_state`, creating a silent correctness bug |

### Gaps Resolved

All 3 secondary gaps were filled by creating `verification/test_phase06_nyquist_gaps.py` with one test per gap:

| Test | Gap Covered | Result |
|------|-------------|--------|
| `test_w2_iol_test_client_has_no_legacy_monkeypatch_write_sites` | 6-04-02 | PASS |
| `test_snapshot_regen_is_idempotent` | 6-01-03 | PASS |
| `test_phase_06_baseline_has_required_keys` | 6-01-04 | PASS |

Post-audit full suite: **392 passed**, 1 skipped, 1 deselected.
Ruff + mypy strict: clean on new test file.

### Escalations

None. All phase requirements have automated verification. No implementation bugs found.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies declared
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (snapshot harness, per-package guards, baseline counts file)
- [x] No watch-mode flags (pytest runs are one-shot)
- [x] Feedback latency < 30s on full suite
- [x] `nyquist_compliant: true` set in frontmatter at sign-off (W1 closure — flipped after the B1/B2/B3/B4/B5/B6/B7/B8 revision pass added `<automated>` verify blocks to every task and addressed structural issues)
- [x] B4 closure: Plan 07 Task 1 explicitly runs `uv run --python 3.13` for pytest and mypy
- [x] B6 closure: Plan 07 owns `verification/mutation_gate.py` audit; Plan 06 leaves it untouched
- [x] Audit 2026-06-11: all 22 tasks GREEN; 3 secondary gaps filled with new automated tests; no escalations
- [x] wave_0_complete: true (flipped from false; Wave 0 Plans 01+02 are merged and all Wave 0 items confirmed present)

**Approval:** validation strategy approved (post-audit, all gaps filled)

> `verified: 2026-06-11` — audit passed, nyquist_compliant remains true.
