---
phase: 3
slug: iol-verification
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-06
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `03-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3+ with pytest-asyncio (`asyncio_mode = "auto"`) + pytest-httpx |
| **Config file** | `pyproject.toml` (root) `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest packages/iol-client -q` |
| **Full suite command** | `uv run pytest -q` |
| **Type-check command** | `uv run mypy verification main_iol.py packages/iol-client/` |
| **Lint command** | `uv run ruff check verification main_iol.py packages/iol-client/` |
| **Format check** | `uv run ruff format --check verification main_iol.py packages/iol-client/` |
| **Estimated runtime** | ~5 seconds quick (~15 with full suite) |

---

## Sampling Rate

- **After every task commit:** `uv run pytest packages/iol-client -q && uv run mypy packages/iol-client main_iol.py verification && uv run ruff check packages/iol-client main_iol.py verification`
- **After every plan wave:** `uv run pytest -q && uv run mypy . && uv run ruff check . && uv run ruff format --check .`
- **Before `/gsd-verify-work`:** Full suite must be green AND `main_iol.py` dry-run sync emits `SUMMARY: PASS=N FAIL=0 SKIPPED=N FINDING=N` (no FAIL ever — D-04 honored)
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

Will be filled by the planner (gsd-planner) with one row per task. The mapping below
is the requirement→test contract derived from research; the planner derives
`Task ID` and per-plan `Wave` assignments and fills the rest.

| Requirement | Behavior to verify | Test Type | Automated Command | File Exists | Status |
|---|---|---|---|---|---|
| IOL-01 | `login()` succeeds + lazy-auth on first call (sync+async) | unit (mocked) | `uv run pytest packages/iol-client/tests/test_client.py::test_login_obtiene_access_token packages/iol-client/tests/test_async_client.py::test_async_login_obtiene_access_token -x` | ✅ (pre-existing) | ⬜ pending |
| IOL-01 | `login()` raises `IOLAuthError` on missing creds | unit (mocked) | `uv run pytest packages/iol-client/tests/test_client.py::test_login_falla_sin_credenciales -x` | ✅ (pre-existing) | ⬜ pending |
| IOL-01 | Live: `iol_client.login()` returns a non-empty access_token | manual / driver | `uv run --package iol-client python main_iol.py` → expect `PROBE login_sync: PASS` + `PROBE login_async: PASS` | ❌ W0 | ⬜ pending |
| IOL-02 | URL+query verbatim per endpoint (sync+async) | unit (mocked) | existing 8 sync + 6 async + 4 new Verified-live tests per surface | ✅ pre-existing + ❌ W0 | ⬜ pending |
| IOL-02 | Live: 4 endpoints return non-empty raw payloads (sync+async) | manual / driver | `main_iol.py` probes 3-10 emit PASS | ❌ W0 | ⬜ pending |
| IOL-03 | `schema_of` builds field→type map from raw payload | unit | `uv run pytest verification/` (existing) | ✅ (Phase 1) | ⬜ pending |
| IOL-03 | Live: `probe_field_type_map` compares observed vs `_ASSUMED_*` and emits findings per discrepancy | manual / driver | `main_iol.py` probe 12; check `.planning/verification/iol-client-findings.md` | ❌ W0 | ⬜ pending |
| IOL-04 | Mock: `get_instruments_by_type` unwraps `data["titulos"]` | unit (mocked) | `uv run pytest packages/iol-client/tests/test_client.py::test_get_instruments_by_type_extrae_titulos -x` | ✅ (pre-existing) | ⬜ pending |
| IOL-04 | Mock: numeric field arrives as int/float not str | unit (mocked) | new Verified-live test asserting `isinstance(quote["ultimoPrecio"], (int, float))` | ❌ W0 | ⬜ pending |
| IOL-04 | Mock: historical path is `YYYY-MM-DD/YYYY-MM-DD/sinAjustar` with day > 12 | unit (mocked) | new Verified-live test with `dt.date(2026, 4, 21)` | ❌ W0 | ⬜ pending |
| IOL-04 | Live: raw payload of `get_instruments_by_type` contains `"titulos"` envelope key (use `_request` direct, not wrapper) | manual / driver | `main_iol.py` probe 12 envelope sub-check (Pitfall 2) | ❌ W0 | ⬜ pending |
| IOL-05 | Mock: 401 → `IOLAuthError` with `status_code=401` | unit (mocked) | `uv run pytest packages/iol-client/tests/test_client.py::test_request_propaga_auth_error -x` | ✅ (pre-existing — extend with `status_code` assertion per IN-05 hardening) | ⬜ pending |
| IOL-05 | Live: opt-in 401 probe with bad creds raises typed exception (single-shot) | manual / driver | `VERIFY_IOL_BAD_CREDS=1 uv run --package iol-client python main_iol.py` → `PROBE auth_401: FINDING F-NN (EXPECTED)` | ❌ W0 | ⬜ pending |
| IOL-06 | Live: structural parity sync↔async for 4 endpoints | manual / driver | `main_iol.py` probe 11 emits PASS or FINDING SYNC-ASYNC-DRIFT | ❌ W0 | ⬜ pending |
| IOL-07 | Mock: refresh path used when `_refresh_token` cached and `_token` expired (sync+async) | unit (mocked) | `uv run pytest -k test_refresh_token_success_path -x` | ❌ W0 | ⬜ pending |
| IOL-07 | Mock: refresh 4xx falls back to password grant (sync+async) | unit (mocked) | `uv run pytest -k test_refresh_fails_falls_back_to_password -x` | ❌ W0 | ⬜ pending |
| IOL-07 | Mock: both refresh and password 4xx raise `IOLAuthError` (sync+async) | unit (mocked) | `uv run pytest -k test_refresh_and_password_both_fail -x` | ❌ W0 | ⬜ pending |
| IOL-07 | Mock: `login()` captures `refresh_token` from response (sync+async) | unit (mocked) | `uv run pytest -k test_login_captures_refresh_token -x` | ❌ W0 | ⬜ pending |
| IOL-07 | Live: `probe_refresh_token` confirms in-vivo that forced expiry triggers refresh path | manual / driver | `main_iol.py` probe 14 emits PASS | ❌ W0 | ⬜ pending |
| DRIFT-01 (mirror) | 4 schema snapshots committed; re-run produces `schema sin drift` | manual / driver | `main_iol.py` probe 13 first run writes; second run PASS | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `main_iol.py` — rewrite from smoke test to 15 probes (D-IOL-5)
- [ ] `packages/iol-client/src/iol_client/client.py` — add `_refresh_token`, `_refresh()`, modify `login()` + `_ensure_token()` + `configure()` (D-IOL-8/9/10)
- [ ] `packages/iol-client/src/iol_client/aio.py` — mirror with double-checked locking inside `_token_lock` for the refresh path
- [ ] `packages/iol-client/tests/test_client.py` — append `# ------ Verified live (Phase 3) ------` and `# ------ Regressions ------` sections + 4 IOL-04 invariants + 4 IOL-07 regressions
- [ ] `packages/iol-client/tests/test_async_client.py` — mirror sections + 4+4 tests
- [ ] `.planning/verification/iol-client-findings.md` — auto-generated by driver first run (committed at end-of-phase like Phase 2)
- [ ] `.planning/verification/schemas/iol-client/{get-quote,get-historical-quotes,get-instruments,get-instruments-by-type}.json` — auto-generated by driver first run (committed at end-of-phase)
- [ ] (No framework install needed — pytest-httpx + pytest-asyncio already in `uv.lock`)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live driver run (default) | IOL-01..06 | Real API call to `api.invertironline.com`; requires `IOL_USER`/`IOL_PASSWORD` env vars; outside automated CI by D-05 (driver-only for live) | `uv run --package iol-client python main_iol.py` — expect 15 PROBE lines + SUMMARY with PASS=N (no FAIL); exit 0 |
| Live 401 probe (opt-in) | IOL-05 | Risk of lockout if accidentally repeated (D-IOL-1, D-IOL-4 single-shot, last in sequence) | `VERIFY_IOL_BAD_CREDS=1 uv run --package iol-client python main_iol.py` — ONE-SHOT only per session |
| Findings file + schema snapshots commit | DRIFT-01 mirror | First live run produces artifacts; humano inspecciona antes de commit (mirror Phase 2 Task 3.2 checkpoint) | `cat .planning/verification/iol-client-findings.md` + `cat .planning/verification/schemas/iol-client/*.json` + approve via human-verify gate task |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter after planner fills per-task table

**Approval:** pending — planner must update `nyquist_compliant: true` after filling per-task Task ID/Wave/Plan columns and verifying no 3-consecutive-tasks gap.
