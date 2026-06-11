---
phase: 6
slug: compat-safety-net-client-class-skeleton
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-10
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: synthesized from `06-RESEARCH.md ## Validation Architecture` (Dimension 8).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3 + pytest-asyncio (auto) + pytest-httpx |
| **Config file** | `pyproject.toml` (root, `[tool.pytest.ini_options]`) — no new config introduced this phase |
| **Quick run command** | `uv run pytest <pkg>/tests -q` per package (≤ 5 s per package on cache hit) |
| **Full suite command** | `uv run pytest -q` (277 tests across 4 packages × sync+async) |
| **Estimated runtime** | ~30 s full suite; ~3–5 s per-package quick run |

Per-package commands (substitute `{pkg}` with `iol-client`, `higyrus-client`, `matriz-client`, `ambito-financiero-client`):

| Command | What it covers |
|---------|----------------|
| `uv run --package {pkg} pytest packages/{pkg}/tests -q` | Package-local mocked tests (must stay green) |
| `uv run pytest verification -q` | Cross-package guards: public surface snapshot, fixture-reaches-production, harness-mutation gate |
| `uv run ruff check .` | Lint (TID, RUF, B) — class skeleton must comply |
| `uv run ruff format --check .` | Formatting parity |
| `uv run mypy --strict packages/{pkg}/src` | Strict types on the new `_ClientState` / `Client` / `AsyncClient` |

---

## Sampling Rate

- **After every task commit:** Run the relevant per-package quick command (`uv run --package {pkg} pytest packages/{pkg}/tests -q`) plus `uv run pytest verification -q` if any cross-package file was touched.
- **After every plan wave:** Run the full suite (`uv run pytest -q`) and `uv run ruff check . && uv run mypy --strict .`.
- **Before `/gsd-verify-work`:** Full suite + ruff + mypy strict must be green on Python 3.12 (CI matrix doubles on 3.13).
- **Max feedback latency:** 30 s (full suite). Per-package quick path < 5 s.

---

## Per-Task Verification Map

> Status set to ⬜ pending until plans land. `Test Type` chosen per task; `Test File` lists where the assertion lives. `File Exists` flags whether the test artifact must be created in Wave 0 (❌ W0) or already exists (✅).

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | Test File | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-----------|-------------|--------|
| 6-01-01 | 01 (snapshot harness) | 0 | REFAC-01 | — / SAFETY-NET-01 | Public surface drift is detected before refactor | snapshot/unit | `uv run pytest verification/test_public_surface.py -q` | `verification/test_public_surface.py` | ❌ W0 | ⬜ pending |
| 6-01-02 | 01 | 0 | REFAC-01 | — | Snapshot fixture committed and deterministic | unit | `uv run pytest verification/test_public_surface.py -q` | `verification/_snapshots/public_surface.json` (or `.txt`) | ❌ W0 | ⬜ pending |
| 6-02-01 | 02 (fixture-reaches-production guards) | 0 | REFAC-01 | — / SAFETY-NET-02 | Sentinel token in production code path lands on the wire `Authorization` header | behavior | `uv run pytest verification/test_fixture_reaches_production.py -q` | `verification/test_fixture_reaches_production.py` | ❌ W0 | ⬜ pending |
| 6-03-01 | 03 (iol-client skeleton) | 1 | REFAC-02 | — | `Client`/`AsyncClient` exposed; `_ClientState` per instance; top-level `iol_client.get_X(...)` unchanged | unit + behavior | `uv run --package iol-client pytest packages/iol-client/tests -q` + `uv run pytest verification -q` | `packages/iol-client/tests/test_client_class.py`, existing 100+ mocked tests | ❌ W0 (new) + ✅ (existing) | ⬜ pending |
| 6-03-02 | 03 | 1 | REFAC-02 | — | `iol_client.configure(token=..., token_expires_at=...)` accepted by conftest fixtures | unit | `uv run --package iol-client pytest packages/iol-client/tests/conftest.py -q` (via test usage) | conftest of `iol-client` | ✅ (migrate) | ⬜ pending |
| 6-04-01 | 04 (higyrus-client skeleton) | 1 | REFAC-02 | — | Same as 6-03-01 for higyrus | unit + behavior | `uv run --package higyrus-client pytest packages/higyrus-client/tests -q` | `packages/higyrus-client/tests/test_client_class.py` | ❌ W0 (new) | ⬜ pending |
| 6-05-01 | 05 (ambito skeleton) | 1 | REFAC-02 | — | Same as 6-03-01 for ambito (no auth path; `configure(token=...)` is N/A — verify N/A is documented) | unit | `uv run --package ambito-financiero-client pytest packages/ambito-financiero-client/tests -q` | `packages/ambito-financiero-client/tests/test_client_class.py` | ❌ W0 (new) | ⬜ pending |
| 6-06-01 | 06 (matriz skeleton + AsyncClient stub) | 1 | REFAC-02 | — | `matriz_client.AsyncClient` stub present with `__aenter__`/`__aexit__`/`aclose()`; sync `Client` mirrors REST surface | unit | `uv run --package matriz-client pytest packages/matriz-client/tests -q` | `packages/matriz-client/tests/test_client_class.py` | ❌ W0 (new) | ⬜ pending |
| 6-07-01 | 07 (CI green gate) | 2 | REFAC-01, REFAC-02 | — | All 277 tests + ruff + mypy strict green on 3.12 and 3.13 | regression | CI workflow (push); locally `uv run pytest -q && uv run ruff check . && uv run mypy --strict packages` | n/a | ✅ (CI workflow file) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

> Task IDs above are placeholders — the planner refines them into PLAN.md task lists. The mapping shows the minimum surface that must be verifiable.

---

## Wave 0 Requirements

Wave 0 (executed first, before any refactor) must land the safety net:

- [ ] `verification/test_public_surface.py` — snapshot harness + first run captures the baseline for all 4 packages (sync + async).
- [ ] `verification/_snapshots/public_surface.json` (or `.txt`) — committed deterministic baseline.
- [ ] `verification/test_fixture_reaches_production.py` — fixture-reaches-production guard for the 3 auth'd packages (iol, higyrus, matriz). Ambito skipped (no auth).
- [ ] `verification/conftest.py` — shared helpers (if needed) for the cross-package guards.
- [ ] No new framework install required — pytest/pytest-httpx/pytest-asyncio already in `dev` group.

Per-package test additions (Wave 1) introduce `tests/test_client_class.py` in each of the 4 packages.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `main_iol.py` / `main_higyrus.py` / `main_matriz.py` / `main_ambito_financiero.py` still run end-to-end against live APIs after the refactor | REFAC-02 (Success Criterion 4 — top-level API intact) | Live API calls hit third-party services — not appropriate for CI | `uv run --package <pkg> python main_<name>.py` with `.env` populated, confirm no exception + sensible output |
| CI matrix Python 3.13 parity | REFAC-02 (Success Criterion 5) | Local dev is typically 3.12; 3.13 is verified by CI only | After push, check the GitHub Actions matrix job for 3.13 across all 4 packages → green |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies declared
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (snapshot harness, guard tests)
- [ ] No watch-mode flags (pytest runs are one-shot)
- [ ] Feedback latency < 30s on full suite
- [ ] `nyquist_compliant: true` set in frontmatter at sign-off

**Approval:** pending
