---
phase: 25
slug: mutating-gate-symbols-write
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-31
---

# Phase 25 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: 25-RESEARCH.md "## Validation Architecture".

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=8.3 + pytest-asyncio >=0.24 (`asyncio_mode = "auto"`) + pytest-httpx >=0.34 |
| **Config file** | root `pyproject.toml` (`[tool.pytest.ini_options]`, `--import-mode=importlib`, `--strict-markers`) |
| **Quick run command** | `uv run --package market-data-client pytest packages/market-data-client/tests -q` |
| **Full suite command** | `uv run pytest -q` (all packages + `verification/`) |
| **Estimated runtime** | ~10–20 seconds (package quick run) |

---

## Sampling Rate

- **After every task commit:** Run `uv run --package market-data-client pytest packages/market-data-client/tests -q`
- **After every plan wave:** Run `uv run pytest -q` (full suite incl. `verification/`)
- **Before `/gsd-verify-work`:** Four green gates (`ruff check`, `ruff format --check`, `mypy` strict, `pytest`) must all pass
- **Max feedback latency:** ~20 seconds (package quick run)

---

## Per-Task Verification Map

> Task IDs are assigned by the planner; this map derives verifiable observations from the
> 5 success criteria + GATE-MD-01 / MUT-MD-01. Each row is a source-checkable or
> behavior-checkable assertion (no subjective language).

| Requirement / SC | Wave | Secure / Observable Behavior | Test Type | Automated Command | File Exists |
|------------------|------|------------------------------|-----------|-------------------|-------------|
| SC#1 / GATE-MD-01 | 1 | default `Client()`/`AsyncClient()` refuses mutation with `MarketDataMutationNotAllowedError` and emits **0 HTTP requests** (assert `httpx_mock.get_requests() == []`) | unit | `pytest .../tests/test_mutation_gate.py -q` | ❌ W0 |
| SC#1 (adversarial) | 1 | refused mutation emits **0 Auth0 token round-trips** (auth URL never hit) | unit | same file | ❌ W0 |
| SC#1 (host gate) | 1 | `mutating_allowed=True` + wrong `base_url` host → refused; exact-host match (substring attacker host `…bbsa.com.ar.evil.example` rejected) | unit | same file | ❌ W0 |
| SC#2 / MUT-MD-01 | 2 | `create_symbol` / `create_symbols` / `update_symbol` dispatch with gate ON + correct host, sync **and** async | unit | `pytest .../test_symbols_write.py .../test_symbols_write_async.py -q` | ❌ W0 |
| SC#3 | 2 | request bodies serialize model→JSON (wire assert on request body); `201`/`200` parse to tolerant `SafeModel`; `422` → typed `MarketDataAPIError` | unit | same | ❌ W0 |
| SC#3 (batch bounds) | 1 | `NewSymbols([])` and `NewSymbols([501 items])` raise plain `ValueError` before any dispatch | unit | `pytest .../test_models.py -q` | partial (exists) |
| SC#4 | 1 | the 3 symbols builders set `idempotent=True` (DM-03); gate-refusal path emits 0 requests | unit | `pytest .../test_core.py .../test_mutation_gate.py -q` | partial (test_core.py exists) |
| SC#5 (parity) | 2 | sync + async expose identically-named methods + module shims; new names present in `__all__` | unit | `pytest .../test_public_surface_market_data.py -q` (NEW, in-package) | ❌ W0 |
| SC#5 (gates) | all | ruff / format / mypy-strict / pytest all green | gate | `uv run ruff check . && uv run ruff format --check . && uv run mypy . && uv run pytest -q` | n/a |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `packages/market-data-client/tests/test_mutation_gate.py` — gate ON/OFF, zero-HTTP + zero-Auth0 refusal, exact-host rejection (sync + async) — covers GATE-MD-01 / SC#1
- [ ] `packages/market-data-client/tests/test_symbols_write.py` + `test_symbols_write_async.py` — 3 endpoints, body serialization, 201/200 parse, 422→typed error — covers MUT-MD-01 / SC#2–3
- [ ] `packages/market-data-client/tests/test_public_surface_market_data.py` — **in-package** export + sync/async name-parity assertions (cross-package `verification/test_public_surface.py` + `test_sync_async_isolation.py` **exclude** this package — RESEARCH contradiction with CONTEXT.md D-16) — covers SC#5
- [ ] Extend `packages/market-data-client/tests/test_models.py` — `NewSymbol`/`NewSymbols`/`SymbolPatch` `to_dict()` + `NewSymbols` 1–500 `ValueError` bounds — covers D-10/D-11
- [ ] Extend `packages/market-data-client/tests/test_core.py` — 3 new builder specs (method/path/idempotent/json_body)
- [ ] Extend `conftest.py` teardown to reset `mutating_allowed`/`expected_host` on the default singletons (Pitfall 6 — global-state leakage across tests)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real 201/200/422 response shapes; real POST idempotency; PATCH `/`-encoding | LIVE-MUT-01 | Requires live develop + Auth0 creds (VPN-gated); explicitly deferred to Phase 27 | Deferred — Phase 25 carries A1–A4 as assumptions; tolerant `from_api` absorbs shape surprises |

*All Phase-25 behaviors have automated (mocked) verification; only the live-contract items are manual and out of scope here.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
