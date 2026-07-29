---
phase: 20
slug: scaffold-auth0-client-credentials-fundaciones-de-transporte
status: planned
nyquist_compliant: true
wave_0_complete: true
created: 2026-07-29
---

# Phase 20 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=8.3 + pytest-asyncio (`asyncio_mode = "auto"`) + pytest-httpx |
| **Config file** | root `pyproject.toml` (`[tool.pytest.ini_options]`, `--import-mode=importlib`, `--strict-markers`) |
| **Quick run command** | `uv run --package market-data-client pytest packages/market-data-client/tests -q` |
| **Full suite command** | `uv run --package market-data-client pytest packages/market-data-client/tests` |
| **Estimated runtime** | ~5–15 seconds (all HTTP mocked via pytest-httpx; no live calls) |

---

## Sampling Rate

- **After every task commit:** Run the quick run command scoped to the touched test module(s)
- **After every plan wave:** Run the full suite command for the package
- **Before `/gsd-verify-work`:** All 4 CI gates green for the package — `ruff check`, `ruff format --check`, `mypy` (strict), `pytest`
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

> Seeded during planning; each planned task lifts its acceptance criterion here. Requirements: AUTH-MD-01 (Auth0 client_credentials token lifecycle), CORE-MD-01 (transport/retry/logging-redaction/exceptions/config/health foundations).

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 20-02 core builders/parsers | 02 | 2 | AUTH-MD-01 | T-20-03 / T-20-02 | Pure grant builder (client_credentials form, authenticated=False) + parser (2-tuple, TTL buffer 60s / 3600s fallback) + token_is_fresh + raise_for_response mapping | unit (tdd) | `uv run --package market-data-client pytest packages/market-data-client/tests/test_core.py -x` | ✅ created by Plan 02 | ⬜ pending |
| 20-03 redaction | 03 | 2 | CORE-MD-01 | T-20-02 / T-20-06 | Zero credential leakage: `client_secret` (form + JSON), Bearer, access_token redacted; attach() idempotent + package-logger-scoped | unit (tdd) | `uv run --package market-data-client pytest packages/market-data-client/tests/test_logging.py -x` | ✅ created by Plan 03 | ⬜ pending |
| 20-06 token lifecycle | 06 | 4 | AUTH-MD-01 | T-20-03 | Token fetched via client_credentials grant, cached, re-fetched only when stale — sync + async (double-checked lock) | unit | `uv run --package market-data-client pytest -k token` | ✅ created by Plan 06 | ⬜ pending |
| 20-06 health + exceptions | 06 | 4 | CORE-MD-01 | T-20-02 / T-20-08 | Health reaches service via retry transport on an anonymous path (no Authorization, no `_ensure_token()`, no re-auth on health 401); exception mapping at dispatch | unit | `uv run --package market-data-client pytest -k "health or client"` | ✅ created by Plan 06 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `packages/market-data-client/tests/conftest.py` — shared pytest-httpx fixtures (Plan 06 Task 1: autouse `configure()` sync+async + state-reset + `NEVER_EXPIRES`)
- [x] `packages/market-data-client/tests/` — test modules covering AUTH-MD-01 and CORE-MD-01 (Plan 02 `test_core.py`, Plan 03 `test_logging.py`, Plan 06 `test_token_lifecycle{,_async}.py` + `test_client.py`/`test_async_client.py`)
- [x] pytest + pytest-asyncio + pytest-httpx already available at workspace root — no framework install needed

> NOTE: `_core.py`/`_logging.py` tests (Plans 02/03) run standalone via namespace imports (no conftest/`__init__` needed). The shell behavioral tests (token lifecycle, health, 401) run in Plan 06 once `__init__.py` (attach-first) + `conftest.py` wire the full package — this is why they are Wave 4, not earlier.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Exact health endpoint URL and absolute `MARKET_DATA_AUTH0_TOKEN_URL` shape against the live service | AUTH-MD-01 / CORE-MD-01 | Live third-party dependency; deferred to Phase 23 live verification (fully mockable now) | Confirm against OpenAPI / live before Phase 23 smoke; Phase 20 uses mocked wire shapes only |

*All Phase 20 automated behaviors are mockable via pytest-httpx — no live calls in this phase.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (test scaffolding authored within the plans that produce it)
- [x] No watch-mode flags
- [x] Feedback latency < 15s (all HTTP mocked)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** planned — pending execution
