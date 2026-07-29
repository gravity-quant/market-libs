---
phase: 20
slug: scaffold-auth0-client-credentials-fundaciones-de-transporte
status: draft
nyquist_compliant: false
wave_0_complete: false
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
| 20-XX-XX | XX | 1 | AUTH-MD-01 | T-20-01 / — | Token fetched via client_credentials grant, cached, and re-fetched only when stale (TTL buffer / 3600s fallback) — sync + async | unit | `uv run --package market-data-client pytest -k token` | ❌ W0 | ⬜ pending |
| 20-XX-XX | XX | 1 | CORE-MD-01 | T-20-02 / — | Zero credential leakage: `client_secret` (form + JSON) and Bearer/access_token redacted in logs (caplog) | unit | `uv run --package market-data-client pytest -k redact` | ❌ W0 | ⬜ pending |
| 20-XX-XX | XX | 1 | CORE-MD-01 | — | Health endpoints reach service via retry transport on an anonymous path (no Authorization, no `_ensure_token()`); exception mapping 401/403→Auth, 429→RateLimit, other→APIError | unit | `uv run --package market-data-client pytest -k "health or exception"` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `packages/market-data-client/tests/conftest.py` — shared pytest-httpx fixtures (Auth0 token endpoint stub for initial fetch + TTL-expiry refetch; `configure()` + state-reset fixture)
- [ ] `packages/market-data-client/tests/` — test modules covering AUTH-MD-01 and CORE-MD-01 (token lifecycle sync+async, redaction, health/exception mapping)
- [ ] pytest + pytest-asyncio + pytest-httpx already available at workspace root — no framework install needed

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Exact health endpoint URL and absolute `MARKET_DATA_AUTH0_TOKEN_URL` shape against the live service | AUTH-MD-01 / CORE-MD-01 | Live third-party dependency; deferred to Phase 23 live verification (fully mockable now) | Confirm against OpenAPI / live before Phase 23 smoke; Phase 20 uses mocked wire shapes only |

*All Phase 20 automated behaviors are mockable via pytest-httpx — no live calls in this phase.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
