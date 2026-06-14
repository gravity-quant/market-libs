---
phase: 11-harness-hardening-code-review-close-out-live-re-verification
plan: 01
subsystem: verification-harness
tags:
  - harness
  - findings
  - dedupe
  - append-only
  - HARN-07
  - HARN-08
  - HARN-09
  - HARN-10
requires:
  - "Phase 5 baseline `4d48e07` (verification-cycle-2026-Q2) — 4 `<pkg>-findings.md` files"
  - "Existing `verification/findings.py` (494 LOC) with `_parse_findings`/`_serialize_findings`/`append_finding` (D-10 idempotent-by-fid contract)"
provides:
  - "Append-only `<pkg>-findings.md` contract: operator content ABOVE `<!-- BEGIN AUTO-GENERATED -->` and BELOW `<!-- END AUTO-GENERATED -->` survives byte-identical N re-runs"
  - "`append_finding(idempotent_by_title=True)` kwarg — content-addressed dedupe by title; cierra HARN-08 (cross-driver) y HARN-10 (matriz D-MATZ-27 EXPECTED terminal en un solo run)"
  - "4 baseline `<pkg>-findings.md` files migrados con markers BEGIN/END (one-time, non-destructive)"
affects:
  - "4 drivers (`main_matriz.py`, `main_iol.py`, `main_higyrus.py`, `main_ambito_financiero.py`) adoptan `idempotent_by_title=True` en terminales EXPECTED/NO-FIX con título estable cross-run"
tech-stack:
  added:
    - "ninguno (sin nuevas dependencias — stack Python 3.12+ / httpx / pytest preservado)"
  patterns:
    - "HTML-comment marker contract para delimitar auto-zone (analog del marker `<!-- Clases (D-09): ... -->` existente en `new_findings`)"
    - "3-zone parser state machine (operator_prefix / auto-zone / operator_suffix) con back-compat fallback (in_auto_zone=True por defecto si no hay markers)"
    - "Content-addressed dedupe by title como kwarg opt-in (default False preserva legacy fid-based)"
key-files:
  created:
    - "verification/test_findings_append_only.py — 4 tests HARN-07/09 (markers en skeleton, operator prefix/suffix/bullets sobreviven N=3 re-runs)"
    - "verification/test_findings_dedupe_by_title.py — 3 tests x 4 packages = 12 cases HARN-08/10 (dedupe by title, preservation, backwards-compat default-False)"
    - ".planning/phases/11-harness-hardening-code-review-close-out-live-re-verification/11-01-SUMMARY.md"
  modified:
    - "verification/findings.py — _ParsedFile.operator_prefix/operator_suffix; _parse_findings 3-zone state machine; _serialize_findings markers + ART refresh-in-prefix path; append_finding idempotent_by_title=False kwarg; new_findings emits markers; +~110 LOC delta"
    - ".planning/verification/ambito-financiero-client-findings.md — 2 lines (BEGIN+END markers)"
    - ".planning/verification/iol-client-findings.md — 2 lines (BEGIN+END markers)"
    - ".planning/verification/higyrus-client-findings.md — 2 lines (BEGIN+END markers)"
    - ".planning/verification/matriz-client-findings.md — 2 lines (BEGIN+END markers)"
    - "main_matriz.py:2117 — D-MATZ-27 EXPECTED terminal flip (HARN-10)"
    - "main_iol.py:1444 — auth_401 EXPECTED terminal flip (HARN-08)"
    - "main_higyrus.py:2010 — auth_401 EXPECTED terminal flip (HARN-08)"
    - "main_ambito_financiero.py:604 — antibot EXPECTED terminal flip (HARN-08)"
requirements_completed: [HARN-07, HARN-08, HARN-09, HARN-10]
decisions:
  - "D-HARN-01 HÍBRIDO: extender `_parse_findings`/`_serialize_findings` en sitio (NO full rewrite). +~110 LOC delta vs ~400 LOC de un rewrite from scratch; preserva los 3 invariantes existentes (CR-01 preservation guard, CR-02 single-line title, ART block refresh)."
  - "Rule 1 deviation discovered during Task 3 verification: cuando se preserva un `operator_prefix` capturado por el parser, el ART block dentro del prefix se refresca in-place via `_replace_art_block` (vs re-emitirse verbatim que dejaba los placeholders sin actualizar)."
  - "Atomic per-task commits (3 commits total — Task 1 RED→GREEN + tests, Task 2 migration, Task 3 driver flips + Rule 1 fix)."
metrics:
  duration: "~75 min (1 wave executor agent)"
  completed: "2026-06-14"
---

# Phase 11 Plan 01: Harness Hardening — Append-Only Findings + Content-Addressed Dedupe — Summary

## One-liner

`verification/findings.py` ahora preserva contenido operator-owned cross-run via BEGIN/END HTML-comment markers y soporta dedupe por title con el kwarg `idempotent_by_title=True`; los 4 drivers adoptan la flag en sus terminales EXPECTED estables (cierra HARN-07/08/09/10).

## Per-task atomic commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | `967b868` | feat(11-01): findings.py append-only with BEGIN/END zone parser + idempotent_by_title (HARN-07/08/09/10) |
| 2 | `e8307a6` | docs(11-01): migrate 4 baseline findings.md files — inject BEGIN/END markers (HARN-07 migration) |
| 3 | `8b157ae` | feat(11-01): content-addressed dedupe across 4 drivers + ART refresh in operator prefix path (HARN-08 + HARN-10) |

## Test count delta

**Before (pre-Plan 11-01):** Phase 10 baseline — N tests in `verification/` (192 pre-plan).

**After (post-Plan 11-01):** 192 + 16 new = 208 tests.

New tests:

| File | Tests | Cases (parametric) | HARN closed |
|------|-------|--------------------|-------------|
| `verification/test_findings_append_only.py` | 4 functions | 4 cases | HARN-07, HARN-09 |
| `verification/test_findings_dedupe_by_title.py` | 3 functions × 4 pkgs | 12 cases | HARN-08, HARN-10 |
| **Total** | **7 functions** | **16 cases** | 4 requirements |

Acceptance criterion "≥ 12 new test cases" → **16 cases delivered (33% over plan)**.

## File migration evidence

Phase 11 migration delta (this plan only — not vs Phase 5 baseline `4d48e07`):

```
$ git diff --stat HEAD~3 HEAD~1 -- .planning/verification/
 .planning/verification/ambito-financiero-client-findings.md | 2 ++
 .planning/verification/higyrus-client-findings.md           | 2 ++
 .planning/verification/iol-client-findings.md               | 2 ++
 .planning/verification/matriz-client-findings.md            | 2 ++
 4 files changed, 8 insertions(+)
```

Each file gained **exactly 2 lines** (BEGIN marker + END marker) — **zero deletions**. Operator content (header, ART block, `<!-- Clases -->`/`<!-- Estados -->` comments, Phase 5 `Classification rationale (Phase 5):` bullets inside finding sections, Phase 9 Plan 09-02/09-03 evidence HTML comment + Resolution bullets in higyrus/matriz, `## Cycle Closure` section) preservada byte-identical.

Round-trip parse evidence (against migrated files):

| Package | `findings_count` | `operator_prefix` lines | `operator_suffix` lines |
|---------|------------------|------------------------|------------------------|
| ambito-financiero-client | 1 | 10 | 24 |
| iol-client | 1 | 10 | 24 |
| higyrus-client | 2 | 11 | 26 |
| matriz-client | 10 | 10 | 30 |

End-to-end smoke (against migrated `matriz-client-findings.md`): running `append_finding(fid='F-99', status='OPEN', ...)` against the migrated file preserves `## Cycle Closure` block **byte-identical** (1245 bytes pre = 1245 bytes post).

## Driver flip evidence

```
$ grep -n "idempotent_by_title=True" main_matriz.py main_iol.py main_higyrus.py main_ambito_financiero.py
main_matriz.py:2117:        idempotent_by_title=True,           # D-MATZ-27 EXPECTED (HARN-10)
main_iol.py:1444:                    idempotent_by_title=True,  # auth_401 EXPECTED (HARN-08)
main_higyrus.py:2010:                    idempotent_by_title=True,  # auth_401 EXPECTED (HARN-08)
main_ambito_financiero.py:604:                    idempotent_by_title=True,  # antibot EXPECTED (HARN-08)
```

**4/4 drivers flipped** at the identified EXPECTED terminals (matriz `D-MATZ-27 prod-vs-remarkets divergence acknowledged` per HARN-10 fix sketch; iol `credenciales inválidas reciben 401`; higyrus `credenciales inválidas reciben 401`; ambito `UA inválido recibe 403`).

Dry-run validation (HARN-10 single-run dedupe assertion):

```
$ uv run python -c "
import tempfile, pathlib
import verification.findings
tmp = pathlib.Path(tempfile.mkdtemp())
verification.findings._FINDINGS_DIR = tmp
from verification.findings import append_finding
for i in range(3):
    append_finding('matriz-client', fid=f'F-{i:02d}', class_='SHAPE',
        surface='sync', status='EXPECTED',
        title='prod-vs-remarkets divergence acknowledged',
        expected='e', actual='a', diff='d', idempotent_by_title=True)
text = (tmp / 'matriz-client-findings.md').read_text()
assert text.count('prod-vs-remarkets divergence acknowledged') == 1
print('OK -- 3 calls produce 1 occurrence')
"
OK -- 3 calls produce 1 occurrence
```

## Phase 6-10 invariants stay GREEN

| Phase | Invariant | Test | Status |
|-------|-----------|------|--------|
| 6 | Fixture-reaches-production guard (4 packages) | `packages/*/tests/test_*_fixture_guard.py` | GREEN |
| 7 | Import-linter contracts (`_core.py` no importa `client.py`/`aio.py`) | `verification/test_import_contracts.py` | GREEN |
| 8 | RetryTransport mutation gate (cross-pkg) | `verification/test_retry_mutation_gate.py` | GREEN |
| 8 | Logging no-token-leak (cross-pkg) | `verification/test_logging_no_token_leak.py` | GREEN |
| 8 | Logging root unchanged (cross-pkg) | `verification/test_logging_root_unchanged.py` | GREEN |
| 9 | BUG-01..04 regression (matriz CFI / multi-account / etc) | `packages/matriz-client/tests/test_core.py::test_get_instruments_by_cfi_validates_cfi_code` + `packages/higyrus-client/tests/test_multi_account.py` | GREEN |
| 10 | Matriz async cross-leak sentinel | `verification/test_sync_async_isolation.py` | GREEN |

**Final aggregate:** `uv run pytest -q` → **892 passed, 1 deselected in 157.25s** (Python 3.12). ruff strict + mypy strict clean on all touched files.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] ART block frozen when re-serializing with operator_prefix**
- **Found during:** Task 3 verification — `uv run pytest -q` surfaced 1 failure in `packages/ambito-financiero-client/tests/test_findings_helper.py::test_append_finding_refreshes_art_block`.
- **Issue:** After Task 1 added BEGIN/END markers to the `new_findings` skeleton, the freshly-created file is parsed with `_parse_findings` and the resulting `_ParsedFile.operator_prefix` captures the header + ART block + `<!-- Clases -->`/`<!-- Estados -->` comments. When `_serialize_findings` was called with this prefix on the next `append_finding` invocation (a non-preservation path, status="OPEN"), my initial implementation re-emitted the prefix **verbatim** — meaning the ART block in the prefix kept the original `<ISO-8601>` / `<url>` / `<abierto|cerrado>` placeholders instead of the freshly-resolved values from `art={Timestamp: ..., Resolved base URL / env: ..., Market hours note: ...}`. Pre-Phase-11, `_serialize_findings` always emitted a fresh ART block, so the test passed; post-Phase-11 (initial fix), the prefix was frozen.
- **Fix:** In `_serialize_findings`, when `prefix` is provided, run `_replace_art_block(prefix_text, art)` to refresh the 3 ART lines in-place inside the prefix before re-emitting. The rest of the prefix (header + clases/estados comments + any operator narrative) is preserved verbatim.
- **Files modified:** `verification/findings.py` (lines 460-471 — _serialize_findings prefix path).
- **Commit:** `8b157ae` (folded into Task 3 atomic commit since same file as Task 1 — discovered during Task 3 verification).

### Auth gates

None — Plan 11-01 is entirely offline (no live HTTP). Live re-verification is Plan 11-03 (LIVE-01 final gate).

## Known Stubs

None. Plan 11-01 is a harness extension; it does not introduce new endpoint coverage or stubbed wire shapes.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries introduced. The marker contract (HARN-07) is a docs-format change within an existing operator-curated artifact (`.planning/verification/<pkg>-findings.md`), already covered by T-11-01 / T-11-02 / T-11-06 in the plan's `<threat_model>` (all mitigated per the regression tests).

## Self-Check: PASSED

- **Files created (exist):**
  - `verification/test_findings_append_only.py` — FOUND
  - `verification/test_findings_dedupe_by_title.py` — FOUND
  - `.planning/phases/11-.../11-01-SUMMARY.md` — FOUND
- **Commits exist in branch:**
  - `967b868` (Task 1) — FOUND
  - `e8307a6` (Task 2) — FOUND
  - `8b157ae` (Task 3) — FOUND
- **Test counts:**
  - `verification/test_findings_append_only.py::test_*` — 4 functions
  - `verification/test_findings_dedupe_by_title.py::test_*` — 3 functions × 4 packages = 12 cases
- **Acceptance criteria met:**
  - `grep -c "BEGIN AUTO-GENERATED" verification/findings.py` = 5 (≥ 3 expected) — PASS
  - `grep -c "END AUTO-GENERATED" verification/findings.py` = 5 (≥ 3 expected) — PASS
  - `grep -cE "operator_prefix|operator_suffix" verification/findings.py` = 15 (≥ 6 expected) — PASS
  - `grep -c "idempotent_by_title" verification/findings.py` = 4 (≥ 2 expected — kwarg signature + dedupe branch + doc) — PASS
  - `grep -c "idempotent_by_title" verification/test_findings_dedupe_by_title.py` = 12 (≥ 3 expected) — PASS
  - 4 baseline files each have exactly 1 BEGIN/END marker pair — PASS
  - 4 drivers each have ≥ 1 `idempotent_by_title=True` — PASS
  - `uv run pytest -q` → 892 passed, 1 deselected — PASS
  - `uv run ruff check` on touched files → PASS
  - `uv run mypy --strict verification/findings.py` → PASS
