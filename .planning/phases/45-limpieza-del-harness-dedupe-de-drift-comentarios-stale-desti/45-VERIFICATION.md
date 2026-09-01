---
phase: 45-limpieza-del-harness-dedupe-de-drift-comentarios-stale-desti
verified: 2026-09-01T00:00:00Z
status: passed
score: 5/5 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 45: Limpieza del harness — dedupe de drift, comentarios stale, destino de `verification/` de matriz Verification Report

**Phase Goal:** El harness de verificación deja de mentir en dos direcciones — deja de inflar el ledger con bloques duplicados y deja de arrastrar en silencio archivos que nunca corren — y la deuda de `verification/` de matriz, rota desde la Phase 15, recibe una decisión escrita en vez de rodar un milestone más.
**Verified:** 2026-09-01
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Dedupe collapse + falsification non-collapse test both present and passing (D-04) | ✓ VERIFIED | `uv run pytest -q verification/test_drift_dedupe_falsification.py` → `6 passed`. Docstring explicitly names the non-collapse scenario (`grep -c 'no debe colapsar'` = 1). Guard `(func, digest)` present in all 5 drivers before `_next_fid()`, confirmed by direct line-number inspection: `main_market_data.py:544<549`, `main_iol.py` (3 sites: 1655/1658, 1733/1736, 1809/1815), `main_higyrus.py:618/625`, `main_matriz.py:616/623` (keyed on `file_path.name` per venue-segregation), `main_ambito_financiero.py:639/645`. Each no-op matches its function's return contract (`return` bare, `("PASS", …)` tuple ×3, `ProbeResult(...)`, `continue` ×2 without appending to `finding_fids`) — verified by reading each site. |
| 2 | `test_finding_count_consistency.py` (P-3) stays green without relaxation, fid reordered relative to dedupe check | ✓ VERIFIED | `uv run pytest -q verification/test_finding_count_consistency.py` → `2 passed`. `git log --oneline -- verification/test_finding_count_consistency.py` shows the file's only commit is from phase 33-05 — untouched by phase 45 (matches SUMMARY claim of `git diff --quiet` = exit 0). Fid-not-burned arm (`test_dedupe_no_op_leaves_the_fid_not_burned`) is part of the green 6-arm suite, and the SUMMARY documents a red demonstration when the order was inverted (`assert 2 == 1`). |
| 3 | HARN-04 resolved with a dated written decision — the two matriz test files accepted as documented debt, not repaired | ✓ VERIFIED | `.planning/phases/45-.../45-HARN-04-DECISION.md` exists, dated 2026-09-01, 340+ lines, with all mandated sections (Decision, per-file D-08 items 1-3, canary transfer named with CI enrollment, scope not repaired, Q5, census/D-10 re-declaration, two scope limits, post-phase census § 7). Re-measured live: `uv run pytest -q verification/test_matriz_sweep_snapshot.py verification/test_main_matriz_login_fail_uniformity.py` → `19 failed, 3 passed, 19 errors` (matches documented accepted debt exactly). Both debt files carry an in-code docstring pointer to the decision doc (`grep -c '45-HARN-04-DECISION'` = 1 in each). Canary transfer confirmed real: `verification/test_probe_context_coverage.py` → `6 passed` AND present in the CI allowlist (not just declared). Q4 (the one genuinely orphaned assertion — `probe_login_sync` returns FINDING not FAIL) closed by implementation inside an already-enrolled file: `test_login_sync_probe_returns_finding_never_fail` present and green in `verification/test_main_matriz_skip_line_shape.py` (20 passed, up from 19 baseline). |
| 4 | Phase 37 stale comment fixed to the MEASURED number (337, not 336), IN-06 closed via CI allowlist enrollment, IN-05 retired | ✓ VERIFIED | `uv run python tools/check_surface_types.py` → `187 \`__all__\` names, 337 definitions scanned, 467 fields scanned` — matches docstring block verbatim (read lines 25-65 of `tools/check_surface_types.py`): historical block pinned to `00ffb2f~1` with original digits intact (183/330/13/23 untouched), current block dated "Measured 2026-09-01 (commit `fe323d6`)" with 187/337/467. IN-06 closed: `verification/test_public_surface.py` is present in `.github/workflows/ci.yml` allowlist and runs green standalone (`4 passed`). IN-05 retired: `grep -n 'IN-05' .planning/ROADMAP.md` shows only lines describing it as resolved in Phase 40 (verified against code: `matriz_client.__version__` → `0.3.0`), none listing it as pending. This is per the explicit context note that the criterion text itself was amended from 336→337 by D-05 ENMENDADA (a legitimate correction, not a discrepancy). |
| 5 | All ci.yml edits for the whole phase land in exactly ONE consolidated commit | ✓ VERIFIED | `git log --oneline 6b9b3b6..HEAD -- .github/workflows/ci.yml` → exactly 1 commit (`d6b34f0`). Allowlist grew from 13 to 18 files (`grep -c 'verification/test_.*\.py' .github/workflows/ci.yml` = 18), the 5 new files are exactly the ones D-10 ENMENDADA/D-11 declared. All 18 files run green together: `181 passed`. |

**Score:** 5/5 truths verified (0 present, behavior-unverified)

### Deferred Items

None — all identified follow-on work items (mypy gate on root drivers, repair of the 2 debt files, disposition of the remaining 36 inert `verification/` files, full-surface `test_public_surface.py` coverage extension) are explicitly declared out-of-scope for v1.8 within the phase's own artifacts (`45-HARN-04-DECISION.md` §§ 3-6, ROADMAP `GATE-DRV-MYPY-45` entry routed to v1.9), not silently dropped gaps.

### Required Artifacts (PLAN must_haves, aggregated across 45-01..45-05)

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tools/check_surface_types.py` | Docstring with historical block pinned to commit, current block dated | ✓ VERIFIED | `00ffb2f~1` pin present, current block dated 2026-09-01/`fe323d6`, all 3 figures match live gate output |
| `main_market_data.py` | `probe_parity` comparing `Segment.segment`; `_seen_drift_keys`/`_drift_digest` guard | ✓ VERIFIED | `s.segment for s in seg_sync`/`seg_async` present (lines 1579-1580); `uv run mypy main_market_data.py` → `Success`; guard at 544 before fid at 549 |
| `.planning/ROADMAP.md` | IN-05 retired, criterion 4 with measured figure, DRV-MD-SEG-43 closed, HARN-VERIF-01 resolved, GATE-DRV-MYPY-45 backlog entry | ✓ VERIFIED | All confirmed by grep + read |
| `verification/test_drift_dedupe_falsification.py` | 6 arms: 3 runtime + AST order/shape locks + higyrus runtime | ✓ VERIFIED | `6 passed`, `6 tests collected`, contains `_seen_drift_keys` and `ast` |
| `main_iol.py`, `main_higyrus.py`, `main_matriz.py`, `main_ambito_financiero.py` | Guard + digest at each of the 6 remaining D-02 sites, no-op matching each function's return contract | ✓ VERIFIED | All 7 sites (1 market-data + 3 iol + 1 higyrus + 1 matriz + 1 ambito) confirmed by direct line inspection; matriz correctly keys on `file_path.name` not `func_name` |
| `.planning/phases/45-.../45-HARN-04-DECISION.md` | Dated decision doc, ≥60 lines, names `test_probe_context_coverage.py` enrollment | ✓ VERIFIED | 340+ lines, dated, all 6 mandated sections + post-phase census § 7 |
| `verification/test_main_matriz_skip_line_shape.py` | Q4 closure lock inside already-CI-enrolled file | ✓ VERIFIED | `test_login_sync_probe_returns_finding_never_fail` present, 20 passed (base 19) |
| `.github/workflows/ci.yml` | Allowlist extended 13→18, single commit | ✓ VERIFIED | 18 files, exactly 1 commit (`d6b34f0`), explicit-list comment intact |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `main_market_data.py::_write_schema_snapshot` | `main_market_data.py::_next_fid` | Guard returns before fid allocation | ✓ WIRED | Line 544 (guard) < line 549 (`_next_fid()`) |
| `main_iol.py` (3 sites) | `_seen_drift_keys` / `finding_fids` | Guard before fid; `continue` without append for type-drift sites | ✓ WIRED | Confirmed at all 3 sites |
| `main_matriz.py::_write_or_check_schema` | Baseline segregated by venue | Key uses `file_path.name`, not `func_name` | ✓ WIRED | Line 615, with rationale comment in-code |
| `verification/test_drift_dedupe_falsification.py` | 5 drivers `main_*.py` | `ast.parse` over driver source, biject guard<fid<finding by line | ✓ WIRED | Arms 4/5 pass, and SUMMARY documents red demonstrations for both order-inversion and no-op uniformization |
| `.github/workflows/ci.yml` (job `lint`) | `verification/test_drift_dedupe_falsification.py`, `test_probe_context_coverage.py` | New lines in explicit allowlist | ✓ WIRED | Both present, both run green as part of the 18-file, 181-passed CI mirror |
| `45-HARN-04-DECISION.md` | `.github/workflows/ci.yml` (45-05 edit) | Decision doc names the canary enrollment | ✓ WIRED | Canary file confirmed actually enrolled, not just declared — verified independently against `ci.yml` content |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| HARN-01 | 45-02, 45-03, 45-05 | Dedupe schema drift findings correctly, with falsification test, without relaxing fid invariant | ✓ SATISFIED | 7/7 sites guarded, falsification test 6/6 green and enrolled in CI |
| HARN-03 | 45-01, 45-05 | Fix stale Phase 37 comment, close IN-06, retire IN-05 | ✓ SATISFIED | All three sub-items confirmed independently |
| HARN-04 | 45-04, 45-05 | Written decision on `verification/` matriz debt | ✓ SATISFIED | Decision doc exists, dated, canary really enrolled, Q4 closed by implementation |

No orphaned requirements — `.planning/REQUIREMENTS.md` maps only HARN-01/03/04 to Phase 45, and the traceability table shows all three as `Complete`, correctly committed in the phase's final commit (`98393eb`), after (not before) the supporting code landed.

### Anti-Patterns Found

None. Debt-marker scan (`TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER`) over all files this phase modified turned up only pre-existing false positives unrelated to this phase's diff (Spanish word "TODO" meaning "all", and `XXXXX`/`ESXXXX` CFI-code test literals in `main_matriz.py` that predate this phase). Diffing `6b9b3b6..HEAD` for these files confirms zero new debt markers introduced.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Dedupe falsification suite (all 6 arms) | `uv run pytest -q verification/test_drift_dedupe_falsification.py` | `6 passed` | ✓ PASS |
| P-3 fid invariant unaffected | `uv run pytest -q verification/test_finding_count_consistency.py` | `2 passed`, file untouched since phase 33-05 | ✓ PASS |
| Debt files reproduce documented red state | `uv run pytest -q verification/test_matriz_sweep_snapshot.py verification/test_main_matriz_login_fail_uniformity.py` | `19 failed, 3 passed, 19 errors` | ✓ PASS (matches documented debt exactly) |
| Canary transferee green | `uv run pytest -q verification/test_probe_context_coverage.py` | `6 passed` | ✓ PASS |
| Q4 lock green, +1 over baseline | `uv run pytest -q verification/test_main_matriz_skip_line_shape.py` | `20 passed` | ✓ PASS |
| Surface-types gate reproducible | `uv run python tools/check_surface_types.py` | `187/337/467, 0 violations` | ✓ PASS |
| market-data mypy clean | `uv run mypy main_market_data.py` | `Success: no issues found in 1 source file` | ✓ PASS |
| Full CI allowlist (18 files) mirror | `uv run pytest -q <18 files>` | `181 passed` | ✓ PASS |
| Consolidated ci.yml commit gate | `git log --oneline 6b9b3b6..HEAD -- .github/workflows/ci.yml \| wc -l` | `1` | ✓ PASS |
| Repo-wide lint/format/import gates | `ruff check .`, `ruff format --check .`, `lint-imports` | All pass | ✓ PASS |

### Human Verification Required

None. All must-haves were independently verifiable via code inspection and command execution. The only item the phase's own SUMMARY flagged as needing human confirmation (`45-05-SUMMARY.md` "Human check pendiente" — full CI matrix green on GitHub Actions across 12 legs) is an operational/deployment confirmation outside this phase's code-level success criteria, not a must-have of this verification; the phase's ROADMAP success criteria are satisfied by the local CI mirror plus the deterministic single-commit gate, both independently reproduced above.

### Gaps Summary

None found. All 5 ROADMAP success criteria, all 5 plans' must_haves (truths, artifacts, key_links), and both requirement traceability entries were independently re-derived from the codebase (not from SUMMARY.md claims) and matched exactly. The phase's own amendments to D-01/D-05/D-08 (documented in `45-CONTEXT.md`'s post-research checkpoint) were honored correctly — e.g., the dedupe key is `(func, digest)` without `surface`, the historical `check_surface_types.py` block cites `00ffb2f~1` rather than being rewritten, and the `probe_context` canary transfer is backed by an actual CI enrollment (not just a docstring claim).

---

*Verified: 2026-09-01*
*Verifier: Claude (gsd-verifier)*
