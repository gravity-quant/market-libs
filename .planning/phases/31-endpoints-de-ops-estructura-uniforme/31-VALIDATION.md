---
phase: 31
slug: endpoints-de-ops-estructura-uniforme
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-23
---

# Phase 31 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3+ with pytest-asyncio (`asyncio_mode = "auto"`), pytest-httpx 0.36.2 |
| **Config file** | root `pyproject.toml` `[tool.pytest.ini_options]` (`testpaths = ["packages", "tests", "verification"]`, `--import-mode=importlib`, `--strict-markers`) |
| **Quick run command** | `uv run pytest packages/market-data-client -q` (≈25s) |
| **Full suite command** | `uv run pytest packages/market-data-client packages/higyrus-client -q` (baseline: 699 passed / 36s) |
| **Estimated runtime** | ~36 seconds (full suite); ~25s (quick) |

CI-equivalent: `uv run pytest packages/<pkg>` per matrix leg — note this excludes `verification/`. Phase gate must additionally run `uv run pytest -q` (full repo, including `verification/`) locally, since G-1 (stale higyrus public-surface snapshot) lives there and CI never runs it.

---

## Sampling Rate

- **After every task commit:** `uv run pytest packages/<touched-package> -q` + `uv run ruff check .`
- **After every plan wave:** `uv run pytest packages/market-data-client packages/higyrus-client -q` (baseline **699**, expect ≥699 after) + `uv run python tools/check_decode_intactness.py` + `uv run python tools/check_uniform_structure.py`
- **Before `/gsd-verify-work`:** Full local suite **including `verification/`** (`uv run pytest -q`) must be green, plus `uv run mypy` and `uv run mypy packages/market-data-client/src` (D-13 local-only acceptance step, not CI-enforced).
- **Max feedback latency:** ~40 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 31-01-XX | TBD | 0 | TYP-02 | V4 | Mutating-gate first-literal-statement AST guard, in-package, non-vacuous | unit (AST) | `uv run pytest packages/market-data-client/tests/test_mutation_gate.py -q` | ❌ W0 | ⬜ pending |
| 31-01-XX | TBD | 0 | TYP-02 | — | Byte-identical request pin for `add_holidays`/`delete_holiday`, sync + async | unit | `uv run pytest packages/market-data-client/tests/test_calendar_write.py -k byte_identical -q` | ❌ W0 | ⬜ pending |
| 31-01-XX | TBD | 0 | TYP-02 | V4 | Neither holiday builder changes `idempotent=` (stays `True`, D-20) | unit | `uv run pytest packages/market-data-client/tests/test_core.py -k idempotent -q` | ⚠️ W0 (extend) | ⬜ pending |
| 31-01-XX | TBD | 0 | TYP-02 | V7 | Market-data health parsers gain a non-dict guard (type-name-only error) | unit | `uv run pytest packages/market-data-client/tests/test_core.py -k health -q` | ❌ W0 | ⬜ pending |
| 31-01-XX | TBD | 1 | TYP-02 | — | `higyrus.get_health` returns `Health` (sync+async, method+shim) | unit | `uv run pytest packages/higyrus-client/tests/test_core.py packages/higyrus-client/tests/test_client.py packages/higyrus-client/tests/test_async_client.py -q` | ✅ re-mock | ⬜ pending |
| 31-01-XX | TBD | 1 | TYP-02 | — | higyrus 204 → zero-valued `Health`; non-dict → `HigyrusAPIError(status_code=0, ...)` | unit | `uv run pytest packages/higyrus-client/tests/test_core.py -k health -q` | ✅ re-assert | ⬜ pending |
| 31-01-XX | TBD | 1 | TYP-02 | — | `get_health`/`get_health_feed` return `Health`/`HealthFeed`, 3-level nesting populated | unit | `uv run pytest packages/market-data-client/tests/test_core.py -k health -q` | ✅ re-mock | ⬜ pending |
| 31-01-XX | TBD | 1 | TYP-02 | — | `add_holidays` returns `AddHolidaysResult` with `days: list[CalendarDay]` (reused model) | unit | `uv run pytest packages/market-data-client/tests/test_calendar_write.py packages/market-data-client/tests/test_calendar_write_async.py -q` | ✅ re-mock | ⬜ pending |
| 31-01-XX | TBD | 1 | TYP-02 | — | `delete_holiday` returns `DeleteHolidayResult` (`deleted: bool`) | unit | same as above | ✅ re-mock | ⬜ pending |
| 31-01-XX | TBD | 1 | TYP-02 | — | Zero `dict[str, Any]` across the 20 touched signature sites | typecheck | `uv run mypy packages/higyrus-client/src` (CI) + `uv run mypy packages/market-data-client/src` (local, D-13) | ⚠️ md not CI-enrolled | ⬜ pending |
| 31-01-XX | TBD | 1 | TYP-02 | V8 | higyrus public surface reflects new signature (golden, local only) | golden | `uv run pytest verification/test_public_surface.py -q` | ✅ needs snapshot regen (G-1) | ⬜ pending |
| 31-01-XX | TBD | 1 | TYP-03 | — | All 6 packages have `models.py` + `types.py` present | script | `uv run python tools/check_uniform_structure.py` | ❌ W0 | ⬜ pending |
| 31-01-XX | TBD | 1 | TYP-03 | — | New near-empty modules pass strict typecheck + lint | typecheck/lint | `uv run mypy` + `uv run ruff check .` + `uv run ruff format --check .` | ✅ existing CI | ⬜ pending |
| 31-01-XX | TBD | 1 | TYP-03 | — | `check_decode_intactness.py` stays green (wallets still exempt) | script | `uv run python tools/check_decode_intactness.py` | ✅ exists | ⬜ pending |

*Task IDs finalized once the planner assigns plan/task numbers — the planner and plan-checker reconcile this table's Wave 0 items against the actual plan.*

---

## Wave 0 Requirements

- [ ] Byte-identical request tests (sync + async) for `add_holidays`/`delete_holiday` — covers TYP-02 criterion 2. New file/test; use the captured frozen tuple `(method, str(url), sorted(headers.items()), content_bytes)`, compared as raw bytes (never `json.loads`).
- [ ] Mutating-gate AST guard, in-package (NOT under `verification/` — that directory never runs in CI) — covers TYP-02 criterion 3 (D-07).
- [ ] `tools/check_uniform_structure.py` + new `ci.yml` `lint` job step — covers TYP-03 criterion 4 (D-12).
- [ ] Direct builder-flag assertion (`idempotent is True` for both holiday builders) — criterion 3's second clause; extends existing `test_transport.py` coverage.
- [ ] Non-dict guard tests for the two market-data health parsers (`parse_health_response` currently has none; D-04 requires an equivalent guard to higyrus's).

---

## Manual-Only Verifications

*None — all phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (5 gaps above)
- [ ] No watch-mode flags
- [ ] Feedback latency < 40s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
