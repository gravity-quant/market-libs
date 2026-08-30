---
quick_id: 260614-de5
description: fix DOC-01..04 before completing milestone
date: 2026-06-14
status: complete
plans_completed: 1
tasks_completed: 2
commits:
  - 9d01d7f  # Task 1 — docs(quick-260614-de5): sync v1.1 docs after audit — DOC-01/02/04
  - cd946a3  # Task 2 — refactor(matriz-client): remove ORP-01 dead field account_id — DOC-03
files_modified:
  - .planning/REQUIREMENTS.md
  - .planning/phases/10-matriz-aio-py-creation-tokenstore/10-04-SUMMARY.md
  - .planning/phases/10-matriz-aio-py-creation-tokenstore/10-VERIFICATION.md (new)
  - .planning/phases/11-harness-hardening-code-review-close-out-live-re-verification/11-01-SUMMARY.md
  - .planning/phases/11-harness-hardening-code-review-close-out-live-re-verification/11-02-SUMMARY.md
  - .planning/phases/11-harness-hardening-code-review-close-out-live-re-verification/11-03-SUMMARY.md
  - .planning/phases/11-harness-hardening-code-review-close-out-live-re-verification/11-VERIFICATION.md (new)
  - packages/matriz-client/src/matriz_client/_state.py
test_results:
  matriz_pytest: 907 passed, 1 deselected in 162.64s (Python 3.12)
  ruff: All checks passed (full repo)
  mypy_strict: Success — no issues found in 50 source files
verification_gates:
  doc_01_requirements_completed_present: 4/4 SUMMARY files OK
  doc_02_open_count: 0
  doc_02_complete_count: 29
  doc_03_account_id_field_removed: true
  doc_04_verification_shims_present: 2/2 (10-VERIFICATION.md + 11-VERIFICATION.md)
---

# Quick task 260614-de5 — Fix DOC-01..04 before completing milestone v1.1

## Summary

Closed the four documentation-hygiene follow-ups (DOC-01, DOC-02, DOC-03, DOC-04) flagged by `.planning/v1.1-MILESTONE-AUDIT.md` (`status: passed`, 2026-06-14) so the persisted planning artifacts match the operator-signed reality and `/gsd-complete-milestone v1.1` can run without ambiguous cross-references.

Two atomic commits landed:

| Task | Commit | Scope | Type |
|------|--------|-------|------|
| 1 | `9d01d7f` | DOC-01 + DOC-02 + DOC-04 — 7 docs files | `docs(quick-260614-de5)` |
| 2 | `cd946a3` | DOC-03 — 1 source file (`_state.py`) | `refactor(matriz-client)` |

No code refactoring beyond removing the dead field; no runtime behavior changes; ROADMAP.md untouched (quick-task scope).

## What each DOC-* item closed

### DOC-01 — `requirements_completed` backfilled in 4 SUMMARY frontmatters

The authoritative source per phase is the corresponding `*-VALIDATION.md` `requirements_closed`. Each SUMMARY was edited to mirror that list as a YAML inline array inserted right before the existing `decisions:` block:

| File | Inserted line |
|------|---------------|
| `.planning/phases/10-matriz-aio-py-creation-tokenstore/10-04-SUMMARY.md` | `requirements_completed: [REFAC-04, LIVE-02]` |
| `.planning/phases/11-harness-hardening-code-review-close-out-live-re-verification/11-01-SUMMARY.md` | `requirements_completed: [HARN-07, HARN-08, HARN-09, HARN-10]` |
| `.planning/phases/11-harness-hardening-code-review-close-out-live-re-verification/11-02-SUMMARY.md` | `requirements_completed: [CR-01, CR-02, CR-04, CR-06, CR-07, CR-08]` |
| `.planning/phases/11-harness-hardening-code-review-close-out-live-re-verification/11-03-SUMMARY.md` | `requirements_completed: [LIVE-01]` |

Verification: `grep -E "requirements_completed:.*<REQ>"` returns 1 hit per SUMMARY for each expected REQ-ID. All four SUMMARY files pass the "non-empty array" gate.

### DOC-02 — REQUIREMENTS.md traceability table flipped Open → Complete

18 stale rows were flipped: REFAC-01, REFAC-02, REFAC-03, REFAC-04, CR-01, CR-02, CR-03, CR-04, CR-05, CR-06, CR-07, CR-08, HARN-07, HARN-08, HARN-09, HARN-10, LIVE-01, LIVE-02. (CR-03 + CR-05 were closed in Phases 7/9 per Phase 5 v1.0 plus Phase 11 plan-02 commit log; the audit `follow_ups` block correctly listed all 18 IDs even though the human-language summary said "17 rows".)

Verification (grep gates):

```
grep -c "| Open" .planning/REQUIREMENTS.md       → 0   (was 18)
grep -c "| Complete" .planning/REQUIREMENTS.md  → 29  (was 11)
```

The audit's `requirements: 29/29` is now fully mirrored by the table.

### DOC-03 — ORP-01 dead field `account_id` removed from matriz `_ClientState`

Pre-edit grep sweep across `packages/matriz-client/` (`rg "state\.account_id|\._state\.account_id|state\['account_id'\]|state\[\"account_id\"\]"`) returned 0 hits, matching the v1.1 integration check finding. Single-line removal at `packages/matriz-client/src/matriz_client/_state.py:59`:

```python
# Removed line:
account_id: str | None = None
```

`_ClientState` is `@dataclass(slots=True)` (not `frozen`, but `slots=True` enforces an explicit `__slots__` so this is a closed surface — removing a field cannot break dynamic attribute callers that did not exist). Phase 9 D-09 had removed `account_id` from higyrus + iol `_state.py` but explicitly left matriz out of scope; Phase 11 CR-08 was narrowed to spike-artifact ruff exclusion + `main_higyrus.py:767` line-length and did not cover this carry-forward. This commit closes ORP-01 (cosmetic WARNING from `v1.1-MILESTONE-AUDIT.md`).

Verification (post-edit):

```
uv run ruff check packages/matriz-client/                           → All checks passed!
uv run ruff format --check packages/matriz-client/src/matriz_client/_state.py → 1 file already formatted
uv run mypy                                                          → Success — no issues found in 50 source files
uv run --package matriz-client pytest -q                            → 907 passed, 1 deselected in 162.64s
```

### DOC-04 — Phase 10 + Phase 11 VERIFICATION.md shims created

Each phase already had its operator-signed `*-VALIDATION.md` (`status: approved`, `operator_signoff_date: 2026-06-14`), but the 3-source-matrix audit tooling (`/gsd-audit-milestone`) expects a `*-VERIFICATION.md` alongside the SUMMARY + traceability columns. The two new files are 13-line shims that point at the canonical `*-VALIDATION.md` artifact and re-state the closed requirements:

- `.planning/phases/10-matriz-aio-py-creation-tokenstore/10-VERIFICATION.md` — `verification_artifact: 10-VALIDATION.md`, closes `REFAC-04, LIVE-02`.
- `.planning/phases/11-harness-hardening-code-review-close-out-live-re-verification/11-VERIFICATION.md` — `verification_artifact: 11-VALIDATION.md`, closes `HARN-07..10, CR-01/02/04/06/07/08, LIVE-01`. Also references the iol F-02 PROBE_STALE inline fix at `main_iol.py:1289` per the INT-01 idiom.

Verification:

```
grep -q "verification_artifact: 10-VALIDATION.md" 10-VERIFICATION.md    → OK
grep -q "verification_artifact: 11-VALIDATION.md" 11-VERIFICATION.md    → OK
```

## Deviations from plan

None. All four DOC-* items were closed exactly as described in `260614-de5-PLAN.md`. No deviations under Rules 1-4.

The plan's `<verification>` section also called the project-wide gates green (`uv run ruff check .` + `uv run mypy`); both still pass post-edit (see test_results above).

A first attempt at `uv run mypy --strict packages/matriz-client/src/matriz_client/_state.py` (per the plan body) surfaced 5 cosmetic stub-not-found errors caused by a fresh venv missing `websocket-client` and `python-dotenv`; running `uv sync --all-packages --all-extras --dev --frozen` installed the missing deps and the canonical `uv run mypy` (which honors the strict config in `pyproject.toml`) returned Success cleanly. This was a tooling priming step, not a plan deviation — the source change itself is mypy-clean.

## Auth gates

None — no live HTTP, no credential prompts, no operator action required.

## Self-Check: PASSED

- [x] Task 1 commit `9d01d7f` exists (verified via `git log`).
- [x] Task 2 commit `cd946a3` exists (verified via `git log`).
- [x] All 4 SUMMARY files contain a non-empty `requirements_completed:` array (verified via `grep -E "requirements_completed:.*\S"`).
- [x] REQUIREMENTS.md traceability table: 0 Open rows, 29 Complete rows.
- [x] `packages/matriz-client/src/matriz_client/_state.py` no longer contains `account_id: str | None` (verified via `! grep "account_id: str | None"`).
- [x] `.planning/phases/10-matriz-aio-py-creation-tokenstore/10-VERIFICATION.md` exists with `verification_artifact: 10-VALIDATION.md`.
- [x] `.planning/phases/11-harness-hardening-code-review-close-out-live-re-verification/11-VERIFICATION.md` exists with `verification_artifact: 11-VALIDATION.md`.
- [x] `uv run pytest -q --package matriz-client` → 907 passed, 1 deselected.
- [x] `uv run ruff check .` → All checks passed.
- [x] `uv run mypy` → Success (50 source files).

## Next step

```
/gsd-complete-milestone v1.1
```

All preconditions for milestone close are satisfied: `v1.1-MILESTONE-AUDIT.md status: passed`, all 4 audit `follow_ups` resolved, SUMMARY ↔ VALIDATION ↔ VERIFICATION ↔ traceability table cross-references resolve to `satisfied` for every closed REQ-ID.
