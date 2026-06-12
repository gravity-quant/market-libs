---
phase: 02-mbito-verification
plan: 01
subsystem: verification-harness
tags: [verification, findings, harness, dry-foundation, tdd]
dependency-graph:
  requires:
    - verification/findings.py (existing: FINDING_CLASSES, STATUS_LIFECYCLE, findings_path, new_findings, write_findings)
    - verification/__init__.py (existing barrel)
    - .planning/verification/FINDINGS-TEMPLATE.md (documented schema for per-finding block)
  provides:
    - verification.findings.append_finding (idempotent helper, D-10)
    - verification.append_finding (barrel re-export)
    - private internals: _Finding (frozen+slots dataclass), _ParsedFile, _parse_findings, _serialize_findings
  affects:
    - Phase 2 driver (main_ambito_financiero.py — Wave 2): will call append_finding from probes
    - Phases 3-5 drivers: same helper reused (DRY foundation per Phase 2 RESEARCH)
tech-stack:
  added: []
  patterns:
    - "@dataclass(frozen=True, slots=True) for internal model (_Finding) — consistent with verification.anonymize.Denylist (Phase 1 precedent)"
    - "Re-render full file from model on every write (no regex spot-edits) — Pitfall 2 mitigation from 02-RESEARCH.md"
    - "Idempotent file-I/O: write_findings + path.exists() guard, mkdir(parents=True, exist_ok=True) precedent"
    - "Line-scan markdown parser with regex for index rows / detail headers / bullets — tolerant (skips unmatched lines)"
key-files:
  created:
    - packages/ambito-financiero-client/tests/test_findings_helper.py
  modified:
    - verification/findings.py
    - verification/__init__.py
decisions:
  - "Insertion order policy: append-at-end (new fids), preserve-original-position (re-render). _parse_findings reconstructs insertion_order from the union of Index rows + Detail headers in document order; _serialize_findings emits them in the same order."
  - "Index status is canonical when it disagrees with the Detail block (Index wins). Rationale: humans typically edit the index row first to promote a status; the detail meta line is updated by append_finding on the next call. _parse_findings tolerates the disagreement and propagates the Index status."
  - "Private helpers _parse_findings + _serialize_findings + _Finding kept module-private (no __all__ re-export). Public API is just append_finding."
  - "ART block refreshes always — even when the human-status guard preserves an existing finding. Run trace is always recorded."
metrics:
  duration: ~14 min
  completed: "2026-06-02T23:34:14Z"
  commits: 3
  tasks_total: 2
  tasks_completed: 2
---

# Phase 2 Plan 01: append_finding (D-10) DRY Foundation Summary

One-liner: Added idempotent-by-fid `append_finding` to `verification/findings.py` (re-exported via barrel), with markdown-aware parse/re-serialize internals that preserve human-promoted statuses (CONFIRMED/FIXED/EXPECTED/NO-FIX) and refresh the ART block on every call.

## What Was Built

1. **`verification.findings.append_finding(...)`** — new public function with the exact signature proposed in 02-PATTERNS.md / 02-RESEARCH.md Pattern 1:

   ```python
   def append_finding(
       pkg: str,
       *,
       fid: str,
       class_: str,
       surface: str,
       status: str,
       title: str,
       expected: str,
       actual: str,
       diff: str,
       regression: str | None = None,
       base_url: str | None = None,
       market_hours: str | None = None,
   ) -> Path: ...
   ```

   Invariants verified by unit tests:
   - Creates the skeleton file via `write_findings(pkg)` if missing.
   - Idempotent by `fid` (no duplicate Index rows; second call with same `fid` OPEN updates fields).
   - Preserves human-promoted status: if `existing[fid].status != "OPEN"`, the finding is left untouched and only the ART block is refreshed.
   - Refreshes `Timestamp` (UTC ISO-8601) on every call; refreshes `Resolved base URL / env` and `Market hours note` only when the argument is passed.
   - Raises `ValueError` if `class_ not in FINDING_CLASSES` or `status not in STATUS_LIFECYCLE`.
   - Returns the `Path` to the written file.

2. **Internal model (`_Finding`)** — `@dataclass(frozen=True, slots=True)` matching the precedent of `verification.anonymize.Denylist`. Holds `fid`, `class_`, `surface`, `status`, `title`, `expected`, `actual`, `diff`, `regression`.

3. **`_parse_findings(text)`** — line-scan parser that reconstructs the list of `_Finding`s and the ART dict from an existing file. Tolerant (skips lines that do not match expected regexes). When Index and Detail disagree, the Index value wins (canonical for human edits).

4. **`_serialize_findings(pkg, findings, art)`** — re-renders the whole file (header + ART + class/status comments + `## Index` table + `## Detalle por hallazgo` section with one `### F-NN -- <title>` block per finding). Trailing newline appended (UNIX convention).

5. **Barrel re-export** — `verification/__init__.py` imports `append_finding` from `verification.findings` and lists it in `__all__` (alphabetical position between `anonymize` and `capture`). The module docstring describes the new helper.

6. **9 unit tests** in `packages/ambito-financiero-client/tests/test_findings_helper.py` covering the 6 critical invariants plus `Path` return type, constants visibility, and barrel re-export:

   - `test_append_finding_creates_skeleton_if_missing`
   - `test_append_finding_is_idempotent_by_fid`
   - `test_append_finding_preserves_human_promoted_status`
   - `test_append_finding_refreshes_art_block`
   - `test_append_finding_rejects_invalid_class`
   - `test_append_finding_rejects_invalid_status`
   - `test_append_finding_returns_existing_path`
   - `test_append_finding_validates_constants_visible`
   - `test_append_finding_is_exported_by_barrel`

   Test isolation: autouse fixture `_isolate_findings_dir` monkeypatches `verification.findings._FINDINGS_DIR` to `tmp_path`, ensuring no real findings files are written during tests.

## Tasks Executed

| # | Task | Type | Commits | Files |
| - | ---- | ---- | ------- | ----- |
| 1.1 | Extend `verification/findings.py` with `append_finding` (RED → GREEN → REFACTOR) | tdd auto | b3024e9 (RED), acea8b1 (GREEN) | `verification/findings.py`, `packages/ambito-financiero-client/tests/test_findings_helper.py` |
| 1.2 | Re-export `append_finding` via `verification/__init__.py` barrel | tdd auto | 14439f6 | `verification/__init__.py` |

REFACTOR step (task 1.1) was not needed — initial GREEN implementation already used `_parse_findings` + `_serialize_findings` helpers extracted from the start.

## Verification Results

| Check | Command | Result |
| ----- | ------- | ------ |
| Helper tests | `uv run pytest packages/ambito-financiero-client/tests/test_findings_helper.py -v` | 9 passed |
| Barrel smoke | `uv run python -c "from verification import append_finding; import verification; assert 'append_finding' in verification.__all__"` | OK |
| Static (types) | `uv run mypy verification` | Success: no issues found in 8 source files |
| Static (lint) | `uv run ruff check verification packages/ambito-financiero-client/tests/test_findings_helper.py` | All checks passed |
| Static (format) | `uv run ruff format --check verification packages/ambito-financiero-client/tests/test_findings_helper.py` | 9 files already formatted |
| Full suite | `uv run pytest -q` | 166 passed (was 157 pre-plan; 9 new = 166) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] ruff PIE810 in initial `_parse_findings` impl**

- Found during: GREEN phase verification (`uv run ruff check`).
- Issue: `line.startswith("## Detalle por hallazgo") or line.startswith("## ")` triggers PIE810 (merge into tuple).
- Fix: Replaced with `line.startswith(("## Detalle por hallazgo", "## "))`.
- Files modified: `verification/findings.py`.
- Commit: acea8b1 (part of GREEN commit).

**2. [Rule 3 - Blocking] ruff RUF043 in test `pytest.raises(match=...)`**

- Found during: GREEN phase verification.
- Issue: `match="BOGUS|FINDING_CLASSES"` (and same for `WIP|STATUS_LIFECYCLE`) flagged because `|` is a regex metacharacter in a non-raw string.
- Fix: Marked both patterns as raw strings (`r"..."`).
- Files modified: `packages/ambito-financiero-client/tests/test_findings_helper.py`.
- Commit: acea8b1 (part of GREEN commit).

**3. [Rule 3 - Blocking] ruff PIE810 + I001 in test file**

- Found during: GREEN phase verification.
- Issue: similar tuple-merge suggestion for `stripped.startswith("- Timestamp:") or stripped.startswith("- **Timestamp:**")`; also import ordering (I001) collapsed `pytest` and `verification` into the same group via `--fix`.
- Fix: applied tuple merge manually; let ruff `--fix` consolidate imports.
- Files modified: `packages/ambito-financiero-client/tests/test_findings_helper.py`.
- Commit: acea8b1 (part of GREEN commit).

**4. [Rule 3 - Blocking] ruff format reflow of `verification/findings.py`**

- Found during: GREEN phase verification.
- Issue: `uv run ruff format --check` flagged the new file for reformatting (whitespace before slice colon: `line[len("- Timestamp:") :]`).
- Fix: Ran `uv run ruff format verification packages/ambito-financiero-client/tests/test_findings_helper.py`.
- Files modified: `verification/findings.py`.
- Commit: acea8b1 (part of GREEN commit).

All four were caught by the planned per-task `<verify>` block, fixed inline within the GREEN step, and verified to leave the tests still passing. No architectural changes.

## TDD Gate Compliance

- RED gate: `test(02-01): add failing tests for append_finding (D-10)` → b3024e9.
- GREEN gate: `feat(02-01): implement append_finding with idempotency + human-status preservation (D-10)` → acea8b1.
- REFACTOR gate: not needed (initial implementation already factored into private helpers).

Sequence validated: RED commit precedes GREEN commit; RED failed on `ImportError: cannot import name 'append_finding'` as expected before implementation landed.

## Key Decisions

- **Insertion order:** append-at-end for new fids; preserve original position when re-rendering existing ones. Rationale: deterministic re-renders + intuitive "newest at bottom" reading order matches the existing `## Index` table convention.
- **Index wins over Detail on disagreement:** humans typically edit the index row first when promoting a status. `_parse_findings` propagates the Index status to the model; the Detail meta line is rewritten on the next `append_finding` call. This makes the human-status guard tolerant to partial edits.
- **Internal helpers stay private:** `_Finding`, `_ParsedFile`, `_parse_findings`, `_serialize_findings` are not exposed in `__all__`. The public API is just `append_finding`. Phases 3-5 only need `from verification import append_finding`.
- **ART refresh on every call, even when the finding is preserved.** Every run leaves a trace in the header, even runs that reaffirm an already-CONFIRMED finding.
- **Validation is explicit `ValueError`, not assert.** mypy strict does not enforce string-literal containment for the runtime `class_`/`status` arguments; the explicit `ValueError` is the contract.

## Threat Flags

None. The plan's `<threat_model>` (T-2-01 through T-2-05, T-2-SC) was the design baseline:

- T-2-01 (tamper human status in re-runs) — mitigated by Test 3 (`test_append_finding_preserves_human_promoted_status`).
- T-2-02 (regex spot-edits) — mitigated by `_parse_findings` + `_serialize_findings` (full re-render from model).
- T-2-03 (ART not updated) — mitigated by Test 4 (`test_append_finding_refreshes_art_block`); unconditional refresh.
- T-2-04 (PII in expected/actual/diff) — accepted at design; Phase 2 has no credentials (Ámbito public API). Phases 3-5 must redact before calling.
- T-2-05 (class_/status invalid) — mitigated by Tests 5 & 6 (`test_append_finding_rejects_invalid_class`/`_status`).
- T-2-SC (slopsquat) — N/A; no external packages added (stdlib only: `dataclasses`, `datetime`, `re`).

## Known Stubs

None. `append_finding` is fully wired into both its module and the barrel; the only consumers (Phase 2 driver, Phases 3-5 drivers) are out of scope for this plan and will be implemented in Wave 2+.

## Self-Check: PASSED

Verified files exist:

- `verification/findings.py` — FOUND (extended)
- `verification/__init__.py` — FOUND (extended)
- `packages/ambito-financiero-client/tests/test_findings_helper.py` — FOUND (new)

Verified commits exist:

- b3024e9 (RED) — FOUND
- acea8b1 (GREEN) — FOUND
- 14439f6 (barrel) — FOUND
