---
phase: 26
slug: calendar-write
status: approved
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-31
---

# Phase 26 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: 26-RESEARCH.md "## Validation Architecture".

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio (`asyncio_mode = "auto"`) + pytest-httpx 0.36.2 |
| **Config file** | root `pyproject.toml` (`[tool.pytest.ini_options]`, `--import-mode=importlib`, `--strict-markers`, `--strict-config`) |
| **Quick run command** | `uv run --package market-data-client pytest packages/market-data-client/tests -q` |
| **Full suite command** | `uv run pytest -q` (all packages + `tests` + `verification/`) |
| **Estimated runtime** | ~0.3 s package quick run — measured baseline **191 passed in 0.25 s** |

---

## Sampling Rate

- **After every task commit:** Run `uv run --package market-data-client pytest packages/market-data-client/tests -q` (~0.3 s)
- **After every plan wave:** Run `uv run pytest -q` (full suite incl. `verification/`)
- **Before `/gsd-verify-work`:** Four green gates must pass. Note the mypy gate must be
  **explicit for this package** — `[tool.mypy] files` excludes it, so `uv run mypy .` does NOT
  cover it (RESEARCH X6):
  `uv run ruff check . && uv run ruff format --check . && uv run mypy packages/market-data-client/src && uv run pytest -q`
- **Max feedback latency:** < 5 seconds

---

## Per-Task Verification Map

> Task IDs are assigned by the planner; this map derives verifiable observations from the
> 5 ROADMAP success criteria + MUT-MD-02. Each row is a source-checkable or behavior-checkable
> assertion (no subjective language).

| Requirement / SC | Behavior (observable) | Test Type | Automated Command | File Exists |
|------------------|------------------------|-----------|-------------------|-------------|
| SC#1 / MUT-MD-02 | the 5 methods dispatch correct method/URL/Bearer with the gate open, **sync** | unit | `pytest packages/market-data-client/tests/test_calendar_write.py -q` | ❌ W0 |
| SC#1 / MUT-MD-02 | same, **async** mirror | unit | `pytest packages/market-data-client/tests/test_calendar_write_async.py -q` | ❌ W0 |
| SC#2 | `MarketHoursIn` emits `confirm: False` by default in the `PUT` body; `confirm=True` travels when set; remaining defaults (`pre_open_minutes=10`, `enabled=True`, `updated_by=""`) are emitted | unit | `pytest .../test_calendar_write.py -k confirm -q` + `pytest .../test_models.py -q` | ❌ W0 |
| SC#3 | `to_dict()` of the 3 models routes through `drop_none`: `HolidayIn` without times **omits** `open_time`/`close_time` and **emits** `closed=True` + `description=""`; `HolidaysIn` nests | unit | `pytest .../test_models.py -q` | partial (extend) |
| SC#3 | `preview_calendar_config` **passes through the gate** (refused with gate OFF, 0 requests) — read-safe exception documented | unit | `pytest .../test_calendar_write.py -k preview -q` | ❌ W0 |
| SC#4 | `build_add_holidays_request` ⇒ `idempotent is False`; the other 4 ⇒ `True`; the 2 DELETE builders ⇒ `json_body is None` | unit (builder) | `pytest .../test_core.py -q` | partial (extend) |
| SC#4 | **dispatch-level:** `add_holidays` against repeated 503 emits **exactly 1** request and 0 sleeps (package first, D-15). Needs `@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)` and a `monkeypatch` of `time.sleep` on the positive control | unit | `pytest .../test_calendar_write.py -k retry -q` | ❌ W0 |
| SC#5 (gate) | all 5 methods refuse-by-default with **0 HTTP and 0 Auth0 round-trips** (force-expired token), sync + async | unit | `pytest .../test_calendar_write.py .../test_calendar_write_async.py -q` | ❌ W0 |
| SC#5 (gate host) | gate ON + host ≠ `expected_host` ⇒ refused, 0 requests | unit | same | ❌ W0 |
| SC#5 (422) | server `422` ⇒ `MarketDataAPIError` via `raise_for_response` (no new handling) | unit | same | ❌ W0 |
| SC#5 (tolerance) | empty `200` body ⇒ `CalendarConfig.from_api(None)` (config trio) and `{}` (holiday pair), never raises | unit | `pytest .../test_core.py -q` | ❌ W0 |
| SC#5 (parity) | all 5 methods exist on `Client` and `AsyncClient`; sync shims in the flat namespace, async under `aio`; 8 new names in `__all__` | unit | `pytest .../test_public_surface_market_data.py -q` | partial (extend) |
| SC#5 (bounds) | `HolidaysIn([])` and `HolidaysIn([501 items])` ⇒ bare `ValueError` before any dispatch | unit | `pytest .../test_models.py -q` | partial (extend) |
| SC#5 (4 gates) | ruff check / ruff format / mypy strict / pytest green | gate | see Sampling Rate above (mypy must target `packages/market-data-client/src`) | n/a |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `packages/market-data-client/tests/test_calendar_write.py` — 5 sync methods: happy dispatch
      (method/URL/Bearer/body), `confirm` default `False` on the wire, DELETE with no body and no
      `Content-Type`, `422`→typed, refusal ×5 with 0 requests, host mismatch, `add_holidays`
      no-retry (+ positive control with `monkeypatch` of `time.sleep`), module-level shims
      — covers SC#1–5
- [ ] `packages/market-data-client/tests/test_calendar_write_async.py` — identical async mirror
      over `aio._get_default()` — covers SC#1 / SC#5 parity
- [ ] Extend `packages/market-data-client/tests/test_core.py` — 5 builder specs
      (method/path/json_body/idempotent/authenticated/endpoint_name), state-independence, and
      tolerance of the new passthrough parser (empty/`null`/non-dict body ⇒ `{}`)
- [ ] Extend `packages/market-data-client/tests/test_models.py` — `to_dict()` of the 3 models,
      OpenAPI-verbatim defaults, `drop_none` effect (drop `None` times, preserve `closed=True` /
      `description=""`), `HolidaysIn` 1–500 bound
- [ ] Extend `packages/market-data-client/tests/test_public_surface_market_data.py` —
      `_NEW_PUBLIC_NAMES` +8, `_MUTATION_METHODS` +5
- [ ] **No infrastructure gaps:** framework, config, `conftest.py` (including the gate reset)
      and all templates already exist. Nothing to install or configure.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real shape of the 5 `200` bodies; real per-endpoint idempotency; `"HH:MM"` vs `"HH:MM:SS"`; effect of dropping vs. sending `null` for a holiday's times | LIVE-MUT-01 | Requires live develop + Auth0 creds; the OpenAPI declares all 5 `200`s as bare `object` with no schema | Deferred to Phase 27 (create→verify→revert with dedicated identifiers). Tolerant parsers (D-07) are the hedge |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

*`wave_0_complete` stays `false` until execution actually creates the Wave 0 test files.*

**Approval:** approved 2026-07-31 (gsd-plan-checker: VERIFICATION PASSED, Dimension 8 clean)
