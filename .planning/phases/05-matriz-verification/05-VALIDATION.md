---
phase: 5
slug: matriz-verification
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-09
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-httpx + pytest-asyncio |
| **Config file** | `pyproject.toml` (root) — `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run --package matriz-client pytest -x -q packages/matriz-client/tests/` |
| **Full suite command** | `uv run pytest -q` |
| **Estimated runtime** | ~10 seconds (matriz package only) / ~30 seconds (full workspace) |

---

## Sampling Rate

- **After every task commit:** Run quick command (`pytest -x -q packages/matriz-client/tests/`)
- **After every plan wave:** Run full suite (`uv run pytest -q` across all 5 packages)
- **Before `/gsd-verify-work`:** Full suite must be green AND `ruff check . && mypy .` clean
- **Max feedback latency:** ~15 seconds (matriz only) / ~35 seconds (full)

---

## Per-Task Verification Map

> Filled by planner from PLAN.md task list during Step 8. Each task with `<automated>` block populates one row.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Pre-existing test infrastructure (validated in Phases 1-4) covers most needs. Phase 5 introduces these new test modules:

- [ ] `packages/matriz-client/tests/test_envelope_unwrap.py` — regression tests for MATZ-04 (envelope-key unwrap `_unwrap` helper)
- [ ] `packages/matriz-client/tests/test_token_assert.py` — regression test for `_token` assert → RuntimeError fix
- [ ] `packages/matriz-client/tests/test_mock_order_mutation.py` — MATZ-06 mock-only contract (11 tests, GET-as-write quirk)
- [ ] `verification/tests/test_safemodel_diff.py` — unit tests for promoted `diff_safemodel_bidirectional` helper
- [ ] `verification/tests/test_cycle_report.py` — unit tests for `verify_cycle_closure` automated check

*If existing pytest-httpx fixtures cover all MATZ regression tests, "Existing infrastructure covers all phase requirements" applies to those.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live remarkets auth + lazy-auth flow | MATZ-01 | Requires real remarkets credentials in `.env` (`PRIMARY_USERNAME`, `PRIMARY_PASSWORD`); not stubbable end-to-end | Run `uv run --package matriz-client python main_matriz.py`; verify login banner, then trigger any `get_*` call to confirm lazy-auth path; assert `_token_ts` set in run log |
| Full read-only surface against remarkets | MATZ-02 | Live API calls — raw payload capture only meaningful against live service | Run `main_matriz.py`; verify every endpoint listed in CONTEXT.md §3 emits a `runs/matriz-*.jsonl` line with raw payload preserved; cross-check schemas snapshot diff |
| Market data shape/type assertions guarded by market hours | MATZ-07 | Market hours window is wall-clock dependent | Run live during market hours OR run with `MATRIZ_MARKET_HOURS_OVERRIDE=true` env; verify `shape_assertions_passed: true` per snapshot |
| `{"status":"ERROR"}` error-path exercises | MATZ-05 | Requires live API to return errors (bogus symbol, invalid account, malformed param) | Run `main_matriz.py` error-path block; verify 3+ distinct `PrimaryAPIError` captures in run log with environment label `remarkets` |

*MATZ-03, MATZ-04, MATZ-06, DRIFT-02 are fully automated via mocked pytest regressions + cycle closure check.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (new test files listed above)
- [ ] No watch-mode flags
- [ ] Feedback latency < 35 seconds for full suite
- [ ] `nyquist_compliant: true` set in frontmatter after planner populates Per-Task Verification Map

**Approval:** pending
