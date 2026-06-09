---
phase: 5
slug: matriz-verification
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-09
updated: 2026-06-09
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

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 5-01-1.1 | 01 | 1 | MATZ-03 | T-5-01 | Helper duck-typed, cross-package safe (no credential surface) | unit | `uv run mypy verification && uv run pytest verification/ -q` | ✅ existing | ⬜ pending |
| 5-01-1.2 | 01 | 1 | DRIFT-02 | T-5-02 | Structural parser; no eval, file-read only | unit | `uv run mypy verification && uv run ruff check verification/cycle_report.py` | ✅ existing | ⬜ pending |
| 5-01-1.3 | 01 | 1 | MATZ-04 | T-5-03 / T-5-04 | `_unwrap` raises typed PrimaryAPIError (no untyped KeyError leak); GET-as-write docstring warning preserved | integration | `uv run mypy packages/matriz-client && uv run pytest packages/matriz-client/tests/test_client.py -q` | ✅ existing | ⬜ pending |
| 5-01-1.4 | 01 | 1 | MATZ-04 / MATZ-12 | T-5-05 | 19 mocked regression tests (no live calls); `_token` sentinel asserts RuntimeError | unit | `uv run pytest packages/matriz-client/tests/test_client.py -q -k "Regressions"` | ✅ existing | ⬜ pending |
| 5-02-2.1 | 02 | 2 | MATZ-01 / MATZ-02 | T-5-08 | `.env.example` is opt-in template; no actual credentials | static | `grep -c "PRIMARY_USER\|MATRIZ_SAMPLE_" packages/matriz-client/.env.example` | ✅ existing | ⬜ pending |
| 5-02-2.2 | 02 | 2 | MATZ-03 | T-5-09 | Removes duplicated helper; consumes from `verification` barrel | static | `uv run mypy . && grep -c "from verification import diff_safemodel_bidirectional" main_higyrus.py` | ✅ existing | ⬜ pending |
| 5-02-2.3 | 02 | 2 | MATZ-01 / MATZ-02 / MATZ-07 | T-5-16 / T-5-17 | safe_print credential redaction (D-MATZ-32); hostname assert remarkets prefix (D-MATZ-33) | integration | `uv run mypy . && uv run ruff check main_matriz.py && grep -c "remarkets" main_matriz.py` | ✅ existing | ⬜ pending |
| 5-02-2.4 | 02 | 2 | MATZ-03 / MATZ-05 / MATZ-07 | T-5-18 | field_type_map, error probes always-on, schema_snapshot D-21 envelope, cycle_closure × 4 invocation | integration | `uv run mypy . && uv run python -c "import main_matriz; assert hasattr(main_matriz, 'probe_field_type_map')"` | ✅ existing | ⬜ pending |
| 5-03-3.1 | 03 | 3 | MATZ-01 / MATZ-02 / MATZ-05 / MATZ-07 | T-5-19 | URL invariants locked; market-hours guard sentinel; PrimaryAPIError mapping | unit | `uv run pytest packages/matriz-client/tests/test_client.py -q -k "Verified live"` | ✅ existing | ⬜ pending |
| 5-03-3.2 | 03 | 3 | MATZ-06 | T-5-20 / T-5-21 | 11 mock-only tests (no live mutation); GET-as-write sentinels assert `request.method == 'GET'` | unit | `uv run pytest packages/matriz-client/tests/test_client.py -q -k "new_order or replace_order or cancel_order or get_as_write"` | ✅ existing | ⬜ pending |
| 5-03-3.3 | 03 | 3 | MATZ-01 / MATZ-02 / MATZ-07 / DRIFT-02 | T-5-22 | Operator-driven live run; hostname assert + safe_print enforced; findings classified; no live mutation invoked | manual | `uv run --package matriz-client python main_matriz.py` (operator-driven) | ✅ existing | ⬜ pending |
| 5-04-4.1 | 04 | 4 | DRIFT-02 | T-5-23 | Read-only inspection; tmp.json local | unit | `grep -c "def verify_cycle_closure" verification/cycle_report.py` | ✅ existing | ⬜ pending |
| 5-04-4.2 | 04 | 4 | DRIFT-02 | T-5-24 | Idempotent append of D-MATZ-27 EXPECTED finding | static | `grep -c "EXPECTED" .planning/verification/matriz-client-findings.md` | ✅ existing | ⬜ pending |
| 5-04-4.3 | 04 | 4 | DRIFT-02 | T-5-25 | Direct filesystem write (Assumption A3 — NOT `append_finding`); cycle ID `verification-cycle-2026-Q2` | static | `grep -c "^## Cycle Closure" .planning/verification/*-findings.md` (== 4) | ✅ existing | ⬜ pending |
| 5-04-4.4 | 04 | 4 | DRIFT-02 | — | Operator ratifies cross-cycle patterns + FAIL handling | manual | Operator checkpoint (human-verify gate=blocking) | ✅ existing | ⬜ pending |
| 5-04-4.5 | 04 | 4 | DRIFT-02 / MATZ-03 | T-5-26 / T-5-27 | CYCLE-REPORT.md; canonical commit message `docs(05): baseline DRIFT-02 cycle closure (verification-cycle-2026-Q2)` (forensic-locatable) | integration | `test -f .planning/verification/CYCLE-REPORT.md && git log -1 --pretty=%s` (must include "DRIFT-02 cycle closure") | ✅ existing | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Test-type definitions:**
- `unit`: pure pytest, no external services
- `integration`: pytest + pytest-httpx (mocked HTTP)
- `static`: shell assertion / grep / type-check / lint
- `manual`: operator-driven (requires live remarkets account or human ratification — explicitly carved out)

---

## Wave 0 Requirements

> Reconciled with actual plan decisions: regression and Verified-live tests live in the existing `packages/matriz-client/tests/test_client.py` (sections, not new files); helpers in `verification/` are verified inline via the `<verify>` blocks of each task, not via separate test files. Existing infrastructure covers all phase requirements.

- [x] `pyproject.toml` (root) — pytest + pytest-httpx + pytest-asyncio already configured (Phases 1-4 reuse)
- [x] `packages/matriz-client/tests/test_client.py` — already exists; Plans 05-01/03 append sections (`# ------ Regressions ------`, `# ------ Verified live (Phase 5) ------`)
- [x] `packages/matriz-client/tests/conftest.py` — shared fixtures already configured (reused from Phases 1-4)
- [x] `verification/__init__.py` — barrel module already exists; Plan 05-01 Task 1.1 extends with `diff_safemodel_bidirectional`
- [x] `.planning/verification/` — findings + schemas directory already exists (populated by Phases 2-4)

**Decision:** No new standalone test files are created in Phase 5. All Plan tasks append to existing files. No `Wave 0` task is required because the framework, fixtures, and target file are already present. The original template's separate-file references (`test_safemodel_diff.py`, `test_cycle_report.py`, `test_envelope_unwrap.py`, `test_token_assert.py`, `test_mock_order_mutation.py`) were obsolete — superseded by the planner's decision (validated by RESEARCH.md and Plans 05-01/03) to keep regression + invariant tests in `test_client.py`.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live remarkets auth + lazy-auth flow | MATZ-01 | Requires real remarkets credentials in `.env` (`PRIMARY_USER`, `PRIMARY_PASSWORD`); not stubbable end-to-end | Operator runs `uv run --package matriz-client python main_matriz.py`; verifies login banner, lazy-auth path triggered, `_token_ts` set in run log |
| Full read-only surface against remarkets | MATZ-02 | Live API — raw payload capture only meaningful against live service | Operator runs `main_matriz.py`; verifies every read endpoint listed in CONTEXT.md §3 emits a probe line and raw payload preserved; cross-checks schemas snapshot diff |
| Market data shape/type assertions guarded by market hours | MATZ-07 | Market hours window is wall-clock dependent | Operator runs live during market hours OR with `MATRIZ_MARKET_HOURS_OVERRIDE=true`; verifies `shape_assertions_passed: true` per snapshot |
| `{"status":"ERROR"}` error-path exercises | MATZ-05 | Requires live API to return errors (bogus symbol, invalid account, malformed param) | Operator runs `main_matriz.py` error-path block; verifies 3+ distinct `PrimaryAPIError` captures with environment label `remarkets` |
| Operator finding classification (OPEN → CONFIRMED / NO-FIX / EXPECTED) | DRIFT-02 | Requires human judgment | Operator reviews `.planning/verification/matriz-client-findings.md` post-run and re-classifies each OPEN |
| Cycle closure ratification (CYCLE-REPORT.md content + FAIL handling) | DRIFT-02 | Cross-cycle narrative requires human review | Plan 04 Task 4.4 — checkpoint:human-verify gate=blocking |

*MATZ-03, MATZ-04, MATZ-06 are fully automated via mocked pytest regressions + structural inspection.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (none required — existing infra covers)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify (verified across 16 tasks)
- [x] Wave 0 covers all MISSING references (none — existing files cover everything)
- [x] No watch-mode flags
- [x] Feedback latency < 35 seconds for full suite
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-06-09
