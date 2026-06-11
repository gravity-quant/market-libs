---
phase: 6
slug: compat-safety-net-client-class-skeleton
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-10
revised: 2026-06-10
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: synthesized from `06-RESEARCH.md ## Validation Architecture` (Dimension 8).
> Revised 2026-06-10 in response to checker B1/B2/B3/B5/W1: per-package guard test placement, baseline counts task, nyquist sign-off.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3 + pytest-asyncio (auto) + pytest-httpx |
| **Config file** | `pyproject.toml` (root, `[tool.pytest.ini_options]`) — Plan 01 Task 1 adds `verification` to `testpaths` |
| **Quick run command** | `uv run pytest <pkg>/tests -q` per package (≤ 5 s per package on cache hit) |
| **Full suite command** | `uv run pytest -q` (277 tests across 4 packages × sync+async + Phase 6 new tests) |
| **Estimated runtime** | ~30 s full suite; ~3–5 s per-package quick run |

Per-package commands (substitute `{pkg}` with `iol-client`, `higyrus-client`, `matriz-client`, `ambito-financiero-client`):

| Command | What it covers |
|---------|----------------|
| `uv run --package {pkg} pytest packages/{pkg}/tests -q` | Package-local mocked tests + per-package guard at `packages/{pkg}/tests/test_fixture_reaches_production.py` |
| `uv run pytest verification -q` | Cross-package shared harness: public surface snapshot, harness-mutation gate |
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

> Status set to ⬜ pending until plans land. `Test Type` chosen per task; `Test File` lists where the assertion lives. `File Exists` flags whether the test artifact must be created in Wave 0 (❌ W0) or already exists (✅).
> Revised: per-package guard files at `packages/<pkg>/tests/test_fixture_reaches_production.py` (B1/B2/B3 fix); baseline counts task added (B5 fix).

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | Test File | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-----------|-------------|--------|
| 6-01-01 | 01 (snapshot harness) | 0 | REFAC-01 | — / SAFETY-NET-01 | Public surface drift is detected before refactor | snapshot/unit | `uv run pytest verification/test_public_surface.py -q` | `verification/test_public_surface.py` | ❌ W0 | ⬜ pending |
| 6-01-02 | 01 | 0 | REFAC-01 | — | Snapshot fixture committed and deterministic; header is exactly 8 lines, line 8 == `#` (W3) | unit | `uv run pytest verification/test_public_surface.py -q` | `verification/snapshots/<pkg>-surface.txt` × 4 | ❌ W0 | ⬜ pending |
| 6-01-03 | 01 | 0 | REFAC-01 | — | regen_snapshots.py is idempotent on a clean tree | unit | `uv run python verification/regen_snapshots.py && git diff --exit-code verification/snapshots/` | `verification/regen_snapshots.py` | ❌ W0 | ⬜ pending |
| 6-01-04 | 01 (baseline counts — B5) | 0 | REFAC-01 | — | Phase 6 entry-baseline test_count + coverage% captured before any refactor | unit | `test -f verification/baselines/phase-06-baseline.txt && grep -v '^#' verification/baselines/phase-06-baseline.txt \| grep -qE '^(test_count\|coverage_total):'` | `verification/baselines/phase-06-baseline.txt` | ❌ W0 | ⬜ pending |
| 6-02-01 | 02 (per-package guards — sync) | 0 | REFAC-01 | — / SAFETY-NET-02 | Sentinel token in production code path lands on the wire `Authorization` / `X-Auth-Token` / URL | behavior | `uv run pytest packages/*/tests/test_fixture_reaches_production.py -q -k sync` | `packages/<pkg>/tests/test_fixture_reaches_production.py` × 4 | ❌ W0 | ⬜ pending |
| 6-02-02 | 02 (per-package guards — async) | 0 | REFAC-01 | — / SAFETY-NET-02 | Async sentinel reaches wire; matriz async is skip (Phase 10) | behavior | `uv run pytest packages/*/tests/test_fixture_reaches_production.py -q` | `packages/<pkg>/tests/test_fixture_reaches_production.py` × 4 (extended) | ❌ W0 | ⬜ pending |
| 6-03-01 | 03 (ambito skeleton) | 1 | REFAC-02 | — | `Client`/`AsyncClient` exposed; `_ClientState` per instance; AsyncClient.__slots__ excludes _client_lock (B7) | unit + behavior | `uv run --package ambito-financiero-client pytest packages/ambito-financiero-client/tests -q` | `packages/ambito-financiero-client/tests/test_client_class.py` | ❌ W0 (new) | ⬜ pending |
| 6-03-02 | 03 | 1 | REFAC-02 | — | aio.py imports `_raise_for_response` from client.py (B8) | unit | included in `test_client_class.py` `test_aio_imports_raise_for_response_from_client` | `packages/ambito-financiero-client/tests/test_client_class.py` | ❌ W0 (new) | ⬜ pending |
| 6-03-03 | 03 | 1 | REFAC-02 | — | Per-package guard still passes against refactored ambito | behavior | `uv run pytest packages/ambito-financiero-client/tests/test_fixture_reaches_production.py -q` | `packages/ambito-financiero-client/tests/test_fixture_reaches_production.py` | ✅ (Plan 02) | ⬜ pending |
| 6-04-01 | 04 (iol skeleton) | 1 | REFAC-02 | — | Same as 6-03-01 for iol + OAuth refresh_token forward in shim allowlist | unit + behavior | `uv run --package iol-client pytest packages/iol-client/tests -q` + `uv run pytest verification -q` | `packages/iol-client/tests/test_client_class.py` | ❌ W0 (new) | ⬜ pending |
| 6-04-02 | 04 | 1 | REFAC-02 | — | W2 pre/post-edit grep gate returns zero hits | unit (grep) | `! grep -nE "monkeypatch\\.setattr.*_token\|iol_client\\.client\\._(token\|password\|refresh_token)\\s*=" packages/iol-client/tests/test_client.py` | `packages/iol-client/tests/test_client.py` | ✅ (migrate) | ⬜ pending |
| 6-04-03 | 04 | 1 | REFAC-02 | — | aio.py imports `_raise_for_response` from client.py (B8) | unit | `test_aio_imports_raise_for_response_from_client` | `packages/iol-client/tests/test_client_class.py` | ❌ W0 (new) | ⬜ pending |
| 6-04-04 | 04 | 1 | REFAC-02 | — | iol per-package guard MIGRATED to `configure(token=...)` and passes | behavior | `uv run pytest packages/iol-client/tests/test_fixture_reaches_production.py -q` | `packages/iol-client/tests/test_fixture_reaches_production.py` | ✅ (migrate; this plan exclusively owns) | ⬜ pending |
| 6-05-01 | 05 (higyrus skeleton) | 1 | REFAC-02 | — | Same as 6-03-01 for higyrus + _token_ts → token_expires_at rename mapping | unit + behavior | `uv run --package higyrus-client pytest packages/higyrus-client/tests -q` | `packages/higyrus-client/tests/test_client_class.py` | ❌ W0 (new) | ⬜ pending |
| 6-05-02 | 05 | 1 | REFAC-02 | — | aio.py imports `_raise_for_response` from client.py (B8) | unit | `test_aio_imports_raise_for_response_from_client` | `packages/higyrus-client/tests/test_client_class.py` | ❌ W0 (new) | ⬜ pending |
| 6-05-03 | 05 | 1 | REFAC-02 | — | higyrus per-package guard MIGRATED and passes | behavior | `uv run pytest packages/higyrus-client/tests/test_fixture_reaches_production.py -q` | `packages/higyrus-client/tests/test_fixture_reaches_production.py` | ✅ (migrate; this plan exclusively owns) | ⬜ pending |
| 6-06-01 | 06 (matriz skeleton + stub AsyncClient) | 1 | REFAC-02 | — | `matriz_client.AsyncClient` stub present with `__aenter__`/`__aexit__`/`aclose()`; sync `Client` mirrors REST surface; X-Auth-Token header (D-22) | unit | `uv run --package matriz-client pytest packages/matriz-client/tests -q` | `packages/matriz-client/tests/test_client_class.py` | ❌ W0 (new) | ⬜ pending |
| 6-06-02 | 06 | 1 | REFAC-02 | — | No module-level `_ensure_token` callable in `matriz_client.client.__dict__` (W5) | unit | `test_no_module_level_ensure_token_callable` | `packages/matriz-client/tests/test_client_class.py` | ❌ W0 (new) | ⬜ pending |
| 6-06-03 | 06 | 1 | REFAC-02 | — | matriz per-package guard MIGRATED (sync) + matriz async stays skip | behavior | `uv run pytest packages/matriz-client/tests/test_fixture_reaches_production.py -q` | `packages/matriz-client/tests/test_fixture_reaches_production.py` | ✅ (migrate; this plan exclusively owns) | ⬜ pending |
| 6-06-04 | 06 | 1 | REFAC-02 | — | verification/mutation_gate.py NOT in Plan 06 files_modified (B6) | invariant | manual review | n/a | ✅ | ⬜ pending |
| 6-07-01 | 07 (CI green gate) | 2 | REFAC-01, REFAC-02 | — | All 277 baseline + Phase 6 new tests + ruff + mypy strict green on 3.12 AND 3.13 (B4) | regression | `uv run pytest -q && uv run --python 3.13 pytest -q && uv run ruff check . && uv run mypy --strict packages && uv run --python 3.13 mypy --strict packages` | n/a | ✅ (CI workflow file) | ⬜ pending |
| 6-07-02 | 07 | 2 | REFAC-01, REFAC-02 | — | Driver smoke via `python -m py_compile` (W4) | unit (syntax) | `uv run python -m py_compile main_iol.py main_higyrus.py main_matriz.py main_ambito_financiero.py` | `main_*.py` | ✅ (unchanged) | ⬜ pending |
| 6-07-03 | 07 | 2 | REFAC-01, REFAC-02 | — | mutation_gate audit confirms sandbox vs prod gating still works (B6 — Plan 07 owns audit) | behavior | manual + smoke in Task 1 step 8 | `verification/mutation_gate.py` | ✅ (audit) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

> Task IDs above are placeholders — the planner refines them into PLAN.md task lists. The mapping shows the minimum surface that must be verifiable.

---

## Wave 0 Requirements

Wave 0 (executed first, before any refactor) must land the safety net:

- [ ] `verification/test_public_surface.py` — snapshot harness + first run captures the baseline for all 4 packages (sync + async).
- [ ] `verification/snapshots/<pkg>-surface.txt` × 4 — committed deterministic baselines with the 8-line `#` header (line 8 == `#`).
- [ ] `verification/regen_snapshots.py` — operator script for intentional regeneration.
- [ ] `verification/baselines/phase-06-baseline.txt` — Phase 6 entry-baseline (test_count + coverage% + git_sha + test ID list) per REFAC-01 (B5 fix).
- [ ] `packages/ambito-financiero-client/tests/test_fixture_reaches_production.py` — per-package guard (B1 fix).
- [ ] `packages/iol-client/tests/test_fixture_reaches_production.py` — per-package guard (B1 fix).
- [ ] `packages/higyrus-client/tests/test_fixture_reaches_production.py` — per-package guard (B1 fix).
- [ ] `packages/matriz-client/tests/test_fixture_reaches_production.py` — per-package guard, async stays skip (B1 fix).
- [ ] NO shared `verification/test_fixture_reaches_production.py` — per-package layout eliminates the B3 write conflict.
- [ ] `pyproject.toml` updated: `testpaths = ["packages", "tests", "verification"]`.
- [ ] No new framework install required — pytest/pytest-httpx/pytest-asyncio already in `dev` group.

Per-package test additions (Wave 1) introduce `tests/test_client_class.py` in each of the 4 packages AND migrate each package's per-package guard file to `pkg.configure(token=...)`. Each Wave 1 plan owns its own guard file exclusively (B3).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `main_iol.py` / `main_higyrus.py` / `main_matriz.py` / `main_ambito_financiero.py` still run end-to-end against live APIs after the refactor | REFAC-02 (Success Criterion 4 — top-level API intact) | Live API calls hit third-party services — not appropriate for CI | `uv run --package <pkg> python main_<name>.py` with `.env` populated, confirm no exception + sensible output |
| CI matrix Python 3.13 parity | REFAC-02 (Success Criterion 5) | Local Task 1 step 2 + step 5 explicitly run `uv run --python 3.13` (B4); CI also runs the matrix | After push, check the GitHub Actions matrix job for 3.13 across all 4 packages → green |

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

**Approval:** validation strategy approved (post-revision)

> `wave_0_complete: false` remains — this flag flips during execution when Wave 0 tasks land.
