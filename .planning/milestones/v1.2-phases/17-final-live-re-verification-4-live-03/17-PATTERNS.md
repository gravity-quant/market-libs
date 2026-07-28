# Phase 17: Final Live Re-verification × 4 (LIVE-03) - Pattern Map

**Mapped:** 2026-06-24
**Files analyzed:** 8 (1 new validation doc, 4 findings files modified, 1 requirements row-flip, 1 conditional regression test, 1 conditional cycle-closure marker update — last two only if a genuinely-new live finding surfaces)
**Analogs found:** 8 / 8 (all artifacts in this gate phase have established in-repo precedent)

> **Phase nature:** This is an operator-driven live re-verification GATE phase (`autonomous: false`), not a feature build. No client source code (`client.py`/`aio.py`/`_core.py`) is touched unless D-07 triggers an in-cycle fix. The dominant artifact is a markdown disposition doc; the dominant "code" patterns are markdown-document structures and (conditionally) a pytest regression test.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `.planning/phases/17-final-live-re-verification-4-live-03/17-VALIDATION.md` | operator-gated validation doc (new) | transform (run evidence → disposition) | `.planning/milestones/v1.1-phases/11-harness-hardening-code-review-close-out-live-re-verification/11-VALIDATION.md` | exact |
| `.planning/verification/iol-client-findings.md` | findings disposition (modify) | event-driven (append-only finding events) | itself + `matriz-client-findings.md` cycle-closure marker | exact (self-precedent) |
| `.planning/verification/higyrus-client-findings.md` | findings disposition (modify) | event-driven | `higyrus-client-findings.md` cycle-closure marker | exact (self-precedent) |
| `.planning/verification/matriz-client-findings.md` | findings disposition (modify) | event-driven | `matriz-client-findings.md` (richest closure marker w/ regression-link table) | exact (self-precedent) |
| `.planning/verification/ambito-financiero-client-findings.md` | findings disposition (modify) | event-driven | `ambito-financiero-client-findings.md` cycle-closure marker | exact (self-precedent) |
| `.planning/REQUIREMENTS.md` (traceability rows 143-156) | traceability table (modify) | transform (status flip) | same table rows (Open → Complete) | exact (self-precedent) |
| `packages/<pkg>/tests/test_*.py` (CONDITIONAL — only if NEW CONFIRMED/FIXED finding) | regression test (new) | request-response / transform assertion | `packages/matriz-client/tests/test_core.py::test_get_instruments_by_cfi_validates_cfi_code` (links to F-09) | exact |
| `.planning/verification/<pkg>-findings.md` § Cycle Closure (CONDITIONAL — only if NEW finding) | cycle-closure marker (modify) | transform | `matriz-client-findings.md` lines 119-143 (regression-link table) | exact |

## Pattern Assignments

### `17-VALIDATION.md` (operator-gated validation doc, transform)

**Analog:** `.planning/milestones/v1.1-phases/11-harness-hardening-code-review-close-out-live-re-verification/11-VALIDATION.md`

This is the load-bearing artifact. Mirror its structure exactly per CONTEXT D-01 and the `<specifics>` directive. Phase 11 was LIVE-01; Phase 17 is the LIVE-03 equivalent post-v1.2-migration.

**Operator frontmatter pattern** (11-VALIDATION.md lines 1-37) — adapt field values, keep shape:
```yaml
---
phase: 17-final-live-re-verification-4-live-03
slug: final-live-re-verification-4-live-03
status: approved            # set by operator at signoff; pre-fill leaves a PENDING marker
nyquist_compliant: true
phase_status: ready_for_close
requirements_closed:
  - REFAC-05
  - SEC-01
  - ERG-01
  - LIVE-03
operator_dispositions:      # one key per package — REQUIRED for Success Criterion #1
  ambito: no_new_findings
  iol: F-01 re-confirmed OPEN (baseline carry-forward, D-05)
  higyrus: no_new_findings
  matriz: no_new_findings
baseline_commit: <verification-cycle-2026-Q2 anchor>
head_commit: 71bf201        # v1.1 LIVE-01 head / title-stability anchor (D-06)
operator_signoff_date: <YYYY-MM-DD>
operator_signoff_by: sebadlf (Sebastián de la Fuente)
operator_signoff_run_logs:
  - /tmp/phase17-live-ambito.log
  - /tmp/phase17-live-iol.log
  - /tmp/phase17-live-higyrus.log
  - /tmp/phase17-live-matriz.log
---
```

**KEY DEVIATION from analog:** D-02 requires that a SKIPPED package (missing creds / market closed / sandbox unavailable) still gets a recorded disposition as a *documented EXPECTED exception*. The Phase 11 table had every package RAN. The Phase 17 acceptance table MUST add a RAN/SKIPPED column and an explicit SKIP disposition so Success Criterion #1 ("dispositions captured for all 4 packages") is met even on SKIP. ámbito always RUNs (no auth); iol/higyrus/matriz SKIP without provisioned `.env`.

**Per-package acceptance-bar table pattern** (11-VALIDATION.md lines 67-74) — extend with RAN/SKIPPED column:
```markdown
| Package | RAN/SKIPPED | Pre-baseline status | Post-run SUMMARY | NEW FIDs vs baseline 71bf201 | Operator disposition |
|---|---|---|---|---|---|
| ámbito-financiero-client | RAN | PASS (F-01 EXPECTED) | PASS=… FAIL=0 SKIPPED=… FINDING=… | (none) | no_new_findings |
| iol-client | RAN or SKIPPED | PASS (F-01 OPEN — pre-existing SHAPE) | … | (none expected) | F-01 re-confirmed OPEN (D-05) / SKIPPED-EXPECTED |
| higyrus-client | RAN or SKIPPED | PASS (F-01 EXPECTED + F-02 NO-FIX Phase 9) | … | (none) | no_new_findings / SKIPPED-EXPECTED |
| matriz-client | RAN or SKIPPED | F-01..F-10 mix (F-02/F-10 D-MATZ-27 EXPECTED) | … | (none) | no_new_findings / SKIPPED-EXPECTED |
```

**Blocking-regressions table pattern** (11-VALIDATION.md lines 87-93) — these are NON-operator-gated; non-zero blocks close. Reuse the same three gates plus the D-06 static title-stability gate:
```markdown
| Gate | Test / Detection | Result |
|---|---|---|
| (a) Wire URL changes sync vs async | `verification/test_sync_async_isolation.py` | GREEN |
| (b) Probe outcome flips PASS→FAIL (pre-baseline FIDs) | diff scan over /tmp/phase17-live-diff-<pkg>.log | ZERO |
| (c) Credential leak in logs | `verification/test_logging_no_token_leak.py` + grep | GREEN |
| (d) Finding-title/fid/class stability vs 71bf201 (D-06) | STATIC `git diff 71bf201..HEAD` scoped to title=/fid=/class_= literals in 4 drivers | ZERO changed literals |
```

**Operator-approval section pattern** (11-VALIDATION.md lines 222-261): pre-fill leaves a `## Operator Approval (Pending)` checkpoint; operator types resume signal; finalizer flips frontmatter `status: approved`. Mirror this two-phase pre-fill → approval handshake.

**Evidence-index table pattern** (11-VALIDATION.md lines 264-279): end the doc with a `| Item | Path |` table pointing at `/tmp/phase17-*.log` artifacts and the per-package findings files.

---

### `.planning/verification/<pkg>-findings.md` (findings disposition, event-driven) — all 4

**Analog:** the findings files themselves (self-precedent) — `iol-client-findings.md`, `matriz-client-findings.md`.

These files are **append-only with an auto-generated zone**. Do NOT hand-edit inside the BEGIN/END markers — `append_finding` (in `verification/findings.py:517`) owns that region and uses content-addressed title dedupe + human-status preservation. Per CONTEXT D-05, do NOT re-open terminal findings (`append_finding`'s human-status preservation refuses the revert anyway).

**Auto-zone marker pattern** (iol-client-findings.md lines 11-35):
```markdown
<!-- BEGIN AUTO-GENERATED -->
## Index
| ID | Class | Surface | Status |
|----|-------|---------|--------|
| F-01 | SHAPE | both | OPEN |
| F-02 | AUTH | sync | FIXED |
## Detalle por hallazgo
### F-01 -- missing assumed key `simbolo` in get_quote
**Class:** `SHAPE` . **Surface:** `both` . **Status:** `OPEN`
- **Expected:** …
- **Actual:** …
- **Diff:** …
<!-- END AUTO-GENERATED -->
```

**Operator-field block pattern** (iol-client-findings.md lines 37-51) — appended BELOW `<!-- END AUTO-GENERATED -->`, preserved across N re-runs (HARN-09 contract). This is the structure to use when dispositioning iol F-01 re-confirmation (D-05) or any new finding (D-07):
```markdown
**Classification:** <PROBE_STALE | NEW-BUG-XX | NO-FIX | EXPECTED | baseline-carry-forward>
**Rationale:** <why this disposition>
**Resolution:** <fix applied + location, if FIXED>
**Regression:** <test path::test_name, if CONFIRMED/FIXED>
**Operator signoff:** sebadlf, <date>, via /gsd-execute-phase 17 disposition
```

For **iol F-01 (D-05)** specifically: re-confirm OPEN as a documented baseline carry-forward — append an operator note (NOT a status flip, NOT a new auto-zone entry) recording that the v1.2 migrations did not resolve it and it remains an intentional documented OPEN.

---

### `.planning/REQUIREMENTS.md` traceability rows (traceability table, transform)

**Analog:** the same table, rows 143-147 (self-precedent for the format).

Flip `Open` → `Complete` for the four v1.2 requirements per D-03 / Success Criterion #4. Preserve column alignment and the parenthetical-annotation idiom already in the table (e.g. row 147's `Open (unblocked by Phase 16 DROP)`).

**Current state** (REQUIREMENTS.md lines 142-147):
```markdown
| REQ-ID   | Phase                       | Status                                  |
|----------|-----------------------------|-----------------------------------------|
| REFAC-05 | Phase 15                    | Open                                    |
| SEC-01   | Phase 14                    | Open                                    |
| ERG-01   | Phase 13                    | Open                                    |
| LIVE-03  | Phase 17                    | Open (unblocked by Phase 16 DROP)       |
```

**Target:** flip each `Open` to `Complete` (REFAC-06 row stays `Deferred`). Suggested annotation: `Complete (Phase 17 LIVE-03 gate, 17-VALIDATION.md)`. Mirror the existing right-pad-to-column-width spacing.

---

### `packages/<pkg>/tests/test_*.py` (regression test, request-response) — CONDITIONAL (D-07)

**Analog:** `packages/matriz-client/tests/test_core.py::test_get_instruments_by_cfi_validates_cfi_code` (lines 343-397) — the canonical in-cycle regression test that links to finding F-09.

Only created if a genuinely-NEW live finding is dispositioned CONFIRMED or FIXED (D-07). Otherwise `verify_cycle_closure` returns `(False, [fid])` and Success Criterion #2 fails. Follow the established in-cycle pattern: finding-id-linked, parametric, mocked (no live deps in the test itself).

**Finding-linked test header pattern** (test_core.py lines 343-344, 380-382):
```python
# Phase 9 BUG-01: CFI hybrid Literal + ISO 10962 regex guard (F-09)
# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("cfi", "expect_raise"),
    [ ... buckets with inline comments per bucket ... ],
)
def test_get_instruments_by_cfi_validates_cfi_code(cfi: str, expect_raise: bool) -> None:
    """BUG-01 (F-09): <one-line contract>. ..."""
```

**Conventions to carry (from CLAUDE.md + this analog):**
- `from __future__ import annotations` at top (mandatory, uniform).
- Module docstring stating which finding/phase the test closes and what it imports (test_core.py lines 1-11 explicitly note it imports only `_core`/`_state`/`exceptions`, NOT `client`/`aio`).
- Parametric buckets with inline comments naming each bucket (literal-known / forward-compat / malformed).
- If the fix is logic, mirror it in BOTH `client.py` and `aio.py` of the package (CLAUDE.md dual sync/async rule) — but matriz has no `aio.py`.
- Link the test path back into the findings file `Regression:` operator field AND the Cycle-Closure regression table.

---

### `.planning/verification/<pkg>-findings.md` § Cycle Closure marker (transform) — CONDITIONAL

**Analog:** `matriz-client-findings.md` lines 119-143 (richest example — has a populated regression-link table).

Only updated if a new finding lands. The cycle-closure marker is the structure `verify_cycle_closure` reads. The regression-link table is what gates CONFIRMED/FIXED.

**Cycle-closure marker pattern** (matriz-client-findings.md lines 119-143):
```markdown
## Cycle Closure
**Cycle ID:** `verification-cycle-2026-Q2`
**Closure date:** <ISO timestamp>
**Packages verified in this cycle:** 4 (ambito-financiero-client, iol-client, higyrus-client, matriz-client)
### Findings by status (this package)
| OPEN | CONFIRMED | FIXED | EXPECTED | NO-FIX | Total |
|------|-----------|-------|----------|--------|-------|
| 0 | 0 | 1 | 2 | 7 | 10 |
### Regression tests linked to FIXED/CONFIRMED findings
| Finding | Regression test |
|---------|-----------------|
| F-09    | `packages/matriz-client/tests/test_core.py::test_get_instruments_by_cfi_validates_cfi_code` (Phase 9 …) |
### Cycle validation
`verify_cycle_closure("matriz-client")` returned: **PASS**
Missing regressions: *(none)*
```

The simplest analog (no FIXED findings → empty regression table) is the ámbito/higyrus/iol marker: `iol-client-findings.md` lines 53-72 with the `*(historical findings predate the regression-link convention …)*` note instead of a table.

## Shared Patterns

### Operator-gated frontmatter handshake
**Source:** `11-VALIDATION.md` lines 1-37 (frontmatter) + lines 39-53 (pre-fill banner) + lines 222-261 (granted approval)
**Apply to:** `17-VALIDATION.md`
The two-phase contract: (1) pre-fill produces the doc with run evidence + a PENDING operator-approval section; (2) operator records dispositions + types a resume signal; (3) finalizer flips `status: approved`, `nyquist_compliant: true`, `phase_status: ready_for_close` and writes `operator_dispositions.<pkg>`. `autonomous: false` is the governing flag (CONTEXT D-01).

### SKIP-as-documented-EXPECTED disposition
**Source:** `verification/env_gate.py` lines 33-39 (`SKIPPED <pkg>: missing <vars>`, returns False, never FAILED) + CONTEXT D-02
**Apply to:** `17-VALIDATION.md` per-package table AND each SKIPPED package's findings file
Drivers `sys.exit(0)` on missing creds (SKIP, not failure). ámbito needs no auth → always RAN. A SKIP must still produce an explicit recorded disposition ("documented EXPECTED exception, out-of-scope carry-forward") so all 4 packages have a disposition (Success Criterion #1).

### Append-only findings with human-status preservation
**Source:** `verification/findings.py:517` (`append_finding`), iol-client-findings.md lines 11-51 (auto-zone + operator-field block)
**Apply to:** all 4 `<pkg>-findings.md`
Never hand-edit inside `<!-- BEGIN/END AUTO-GENERATED -->`. Operator fields (`Classification:`/`Rationale:`/`Resolution:`/`Regression:`/`Operator signoff:`) go BELOW the END marker and survive re-runs (HARN-09). Do not re-open terminal findings (D-05).

### In-cycle disposition + regression-link contract
**Source:** `verification/cycle_report.py:123` (`verify_cycle_closure(pkg) -> (ok, missing_fids)`) + matriz-client-findings.md lines 99-108 (F-09 FIXED w/ Resolution + Regression) + lines 131-135 (regression table)
**Apply to:** any NEW finding (D-07)
`verify_cycle_closure` gates ONLY CONFIRMED/FIXED for regression links; OPEN/EXPECTED/NO-FIX are non-gating. A CONFIRMED/FIXED finding without a linked regression test returns `(False, [fid])` → Success Criterion #2 fails.

### Static title-stability diff vs frozen baseline 71bf201
**Source:** CONTEXT D-06; precedent Phase 15 D-06/D-07
**Apply to:** the blocking-regressions table in `17-VALIDATION.md`
Verify title/probe-name stability via STATIC `git diff 71bf201..HEAD` scoped to `title=`/`fid=`/`class_=` literals in the 4 drivers — NOT a live-data diff (live `actual=`/`diff=` bytes are non-deterministic). Gate currently passes clean (+584/-344 driver lines, zero changed literals).

## No Analog Found

*(none)* — every artifact in this gate phase has an exact in-repo precedent. The phase is deliberately a re-run of the LIVE-01 pattern (Phase 11) applied post-v1.2-migration, so no RESEARCH.md fallback patterns are required.

## Metadata

**Analog search scope:** `.planning/milestones/v1.1-phases/11-*` (LIVE-01 precedent), `.planning/verification/*-findings.md` (4 findings files + cycle-closure markers), `.planning/REQUIREMENTS.md` (traceability), `packages/*/tests/` (regression-test analogs), `verification/` (findings.py, cycle_report.py, env_gate.py contracts)
**Files scanned:** 11
**Pattern extraction date:** 2026-06-24
