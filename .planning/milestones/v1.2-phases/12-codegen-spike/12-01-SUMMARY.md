---
phase: 12-codegen-spike
plan: 01
status: complete
wave: 1
tasks_completed: [12-01-01, 12-01-02, 12-01-03]
files_created:
  - .planning/spikes/SPIKE-005-codegen-tool-choice/README.md
  - .planning/spikes/SPIKE-005-codegen-tool-choice/001a-ambito-round-trip/README.md
  - .planning/spikes/SPIKE-005-codegen-tool-choice/001a-ambito-round-trip/experiment.py
  - .planning/spikes/SPIKE-005-codegen-tool-choice/001a-ambito-round-trip/output/client_generated.py
  - .planning/spikes/SPIKE-005-codegen-tool-choice/001a-ambito-round-trip/diff_vs_v1.1_client.txt
  - .planning/spikes/SPIKE-005-codegen-tool-choice/001a-ambito-round-trip/run_log.txt
  - .planning/spikes/SPIKE-005-codegen-tool-choice/001a-ambito-round-trip/FINDING.md
  - .planning/spikes/SPIKE-005-codegen-tool-choice/001b-ambito-marker-future-compat/README.md
  - .planning/spikes/SPIKE-005-codegen-tool-choice/001b-ambito-marker-future-compat/experiment.py
  - .planning/spikes/SPIKE-005-codegen-tool-choice/001b-ambito-marker-future-compat/FINDING.md
  - .planning/spikes/SPIKE-005-codegen-tool-choice/001c-matriz-construct-audit/README.md
  - .planning/spikes/SPIKE-005-codegen-tool-choice/001c-matriz-construct-audit/audit.py
  - .planning/spikes/SPIKE-005-codegen-tool-choice/001c-matriz-construct-audit/FINDING.md
  - .planning/spikes/SPIKE-005-codegen-tool-choice/001d-matriz-deny-list-config/README.md
  - .planning/spikes/SPIKE-005-codegen-tool-choice/001d-matriz-deny-list-config/experiment.py
  - .planning/spikes/SPIKE-005-codegen-tool-choice/001d-matriz-deny-list-config/FINDING.md
files_modified:
  - .planning/spikes/MANIFEST.md
ambito_round_trip_verdict: FAIL
ambito_round_trip_classification: "10 hunks — 7 INHERENT-ASYMMETRY (Recipe 2 class 4) + 2 COSMETIC (class 1) + 1 SEMANTIC-CONSISTENT-EXTENSION; ZERO Recipe-2 class-3 (NO-GO triggers)"
b8_identity_check: PASS
format_stable_check: PASS
diff_hunk_count: 10
slopcheck_unasync: OK
operational_pregate: approved_with_caveat
commits:
  - c461e42  # docs(12-01): bootstrap SPIKE-005 directory + 4 sub-experiment skeletons + MANIFEST row
  - a8996a1  # test(12-01): 001a ámbito round-trip — B8 PASS, format-stable PASS, diff 10 hunks
duration_seconds: 610
duration_minutes: ~10
completed: 2026-06-14
requirements: [REFAC-06]
tags: [spike, codegen, unasync, ambito, round-trip, B8-identity, phase-12]
---

# Phase 12 Plan 01: Codegen Spike Wave 0 + Wave 1 Summary

**One-liner:** Bootstrapped SPIKE-005 directory + 4 sub-experiment skeletons + ran the ámbito round-trip canary — unasync 0.6.0 + ruff format + B8 identity assertion all execute end-to-end; verdict is FAIL on strict byte-identical contract (10 inherent-asymmetry hunks remain) but B8 identity preserved (`is` test passes) and format-stability holds; path to GO in Phase 16 is well-bounded (~30 LOC source migration on aio.py).

## Summary

Wave 0 (Task 12-01-02) created the SPIKE-005 codegen-tool-choice spike directory with 4 sub-experiment skeletons (001a/b/c/d) following CONVENTIONS.md, registered the spike in MANIFEST.md, and confirmed that 12-VALIDATION.md was already populated by the planner with `nyquist_compliant: true` + `wave_0_complete: true` + the Per-Task Verification Map covering all 9 tasks across 3 plans.

Wave 1 (Task 12-01-03) ran the canary: 001a ámbito round-trip experiment ran unasync 0.6.0 against `packages/ambito-financiero-client/src/.../aio.py` (read-only source, copied via `shutil.copy` to a sandbox), applied the prescribed 6-key `additional_replacements` table, post-processed with `uv run ruff format`, confirmed format-stability via `ruff format --check`, captured a 10-hunk diff transcript against the v1.1 hand-written `client.py`, then asserted the B8 identity invariant `mod._raise_for_response is aio._raise_for_response is _core.raise_for_response` via `importlib.util.spec_from_file_location` + `exec_module`. B8 identity PASS (all three resolve to id `0x106d2afc0`); format-stable PASS; strict byte-identical contract FAIL on the 10 hunks.

Per Recipe 2 triage (12-RESEARCH.md), 7 of the 10 hunks classify as **inherent asymmetry** (Recipe 2 class 4: hand-written docstrings, comments, `_validate_max_retries` definition direction, WR-07 ResourceWarning block); 2 as **cosmetic** (class 1: single-line import order, `_REQUEST_TIMEOUT` placement — `ruff format` does NOT converge on these); 1 as **semantic-consistent extension** (codegen extends sync surface with `close()` module-level delegator + `__all__` entry). **Zero hunks classify as "Semantic NOT fixable via additional_replacements" — i.e., zero NO-GO triggers** per Recipe 2 line 507. The strict-FAIL is informative for Phase 16 (well-bounded source-migration setup, ~30 LOC of aio.py edits), not a NO-GO signal.

Task 12-01-01 (operational pre-gate, CI 3.13 confirmation) was PRE-RESOLVED by the operator before this executor was spawned (see "Operator pre-gate response" section below).

Zero mutations under `packages/` (Anti-Pitfall 2 enforced via `git status --porcelain packages/ | wc -l` returning 0 after each commit).

## Ámbito Round-Trip Outcome

| Property | Value |
|----------|-------|
| Script | `.planning/spikes/SPIKE-005-codegen-tool-choice/001a-ambito-round-trip/experiment.py` (172 LOC, 7 steps + 1 cleanup step) |
| Generated artifact | `output/client_generated.py` (248 LOC, ruff-format-clean) |
| Diff transcript | `diff_vs_v1.1_client.txt` (10 hunks, ~250 LOC delta, full unified diff) |
| Run log | `run_log.txt` (full stdout) |
| Script exit code | 1 (strict byte-identical contract FAIL) |
| Recipe-2 classification | 7 INHERENT-ASYMMETRY + 2 COSMETIC + 1 SEMANTIC-CONSISTENT-EXTENSION + 0 NO-GO-TRIGGER |
| D-RIGOR-01 item 1 (byte-identical) | FAIL (will go into Plan 03 Task 12-03-01 evidence checklist; aggregate verdict weighs it against the documented Phase 16 source-migration path) |

**Phase 16 source-migration setup steps** (from FINDING.md ## Ámbito Rule Config Draft) to reach byte-identical roundtrip on a future iteration:

1. Move `_validate_max_retries` definition from `client.py` to `aio.py` (reverses import direction). Fixes hunks H4 + H5.
2. Pin import order in `aio.py` to `from ambito_financiero_client import _core, _transport` (alphabetical). Fixes H3.
3. Pin `_REQUEST_TIMEOUT` constant placement after `__all__` block. Fixes H7.
4. Extend hand-written `client.py` with module-level `close()` delegator + WR-07 ResourceWarning block (semantic symmetry; preferred over reducing async public surface). Fixes H6 + H10.
5. Normalize docstring shape: `aio.py` becomes canonical source-of-truth; sync docstrings emitted via token-replacement. Fixes H1, H8, H9.
6. Align per-line comment wording between `aio.py` and the canonical sync form. Fixes H8 (residual).

Estimated edit volume: ~30 LOC of `aio.py` edits across 6 commits.

## B8 Identity Outcome

**PASS** — strict `is` chain confirmed:

```
mod._raise_for_response  id=0x106d2afc0
aio._raise_for_response  id=0x106d2afc0
_core.raise_for_response id=0x106d2afc0
```

The unasync 0.6.0 tokenizer preserved the alias assignment `_raise_for_response = _core.raise_for_response` verbatim because:

1. The aio.py source line is 5 Python tokens (`_raise_for_response`, `=`, `_core`, `.`, `raise_for_response`).
2. None match the `additional_replacements` keys.
3. No `async`/`await` keyword adjacent.

This empirically confirms 12-RESEARCH.md §"Recipe 3" line 559 prediction. The failure mode the test is designed to catch (codegen emitting a thunk wrapper `def _raise_for_response(resp): return _core.raise_for_response(resp)` — Pitfalls.md §Pitfall 4 CRITICAL) would have caused `is` to return False; it did not. SC#2 / D-RIGOR-01 item 2 satisfied.

## Format-Stability Outcome

**PASS** — `uv run ruff format --check <generated>` exits 0 on the just-formatted file. Confirms idempotent formatting (Recipe 6 / D-RIGOR-01 item 3 / Pitfall 3 mitigation). unasync 0.6.0 emits ruff-clean output to begin with: the first `ruff format` pass shows "1 file left unchanged"; the `--check` pass also exits 0.

## Slopcheck Outcome

**OK** — `slopcheck install unasync` reports:

```
[OK] unasync (pypi)
==================================================
  scanned 1 packages
  1 OK
```

The CLI raises a benign Python traceback at end-of-run because its embedded `pip install unasync` step fails inside the slopcheck venv (no pip installed there); the legitimacy check ran and passed BEFORE the install attempt. Transcript captured in `001a-ambito-round-trip/FINDING.md` and `001b/001d/FINDING.md` (which reference 001a). `unasync 0.6.0` is then resolved transiently by `uv run --with unasync` from PyPI when the experiment runs. T-12-01-SC supply-chain risk mitigated.

## Operator pre-gate response

**Status:** approved with caveat (pre-resolved by operator before executor was spawned).

**Caveat:** Test matrix on `a9c24aa` (origin/main HEAD, post-v1.1-archive) is GREEN on both Python 3.12 AND 3.13 across all 5 packages (10/10 test matrix jobs pass), satisfying anti-Pitfall 17 at the test-matrix level — any 3.13-specific break that surfaces during v1.2 is unambiguously v1.2-attributable for the test suite.

**Known v1.1 tech debt isolated under `tests/` and `verification/`** (NOT shipped library code under `src/`, NOT 3.13-specific):

- **mypy:** RED with 6 errors, all in `packages/matriz-client/tests/`:
  - `test_core.py:375-377`: 3× unused `type: ignore[list-item]` comments (mypy version drift on test fixtures).
  - `test_async_auth.py:223-224`: 2× `Module "matriz_client.aio" does not explicitly export attribute "_raise_for_response"` (PEP 562 shim from v1.1 Phase 10 doesn't expose `_raise_for_response` via `__all__` or explicit re-export — this is the B8 identity test).
  - `test_async_auth.py:245`: 1× unused `type: ignore[attr-defined]` for `_does_not_exist`.
- **pre-commit hooks:** RED — ruff format auto-fixes applied to `verification/test_retry_401_reauth.py` (assertion-message line-wrapping) that were not committed in v1.1.

**Operator decision:** Tracked as follow-up quick-task `mypy-precommit-v1.1-techdebt` to be created AFTER Phase 12 completes (not before; does not block spike work). To be referenced in 12-SUMMARY.md (Plan 03 Task 12-03-03 / 12-03-04a) when written.

Task 12-01-01 was skipped per the executor's pre-resolution instructions; this caveat is captured here so Plan 03 can include it in `12-SUMMARY.md`.

## Anti-Pitfall Compliance

- **Anti-Pitfall 2 (spike creeping into packages/):** verified — `git status --porcelain packages/ | wc -l` returns 0 after every commit. Spike experiment uses `shutil.copy(SRC / "aio.py", WORK / "aio.py")` (read-only access to packages/) + `importlib.util.spec_from_file_location` (loads generated as standalone module, no packages/ write) + `subprocess.run(["uv", "run", "ruff", ...])` (read-only invocation of toolchain). All spike artifacts live under `.planning/spikes/SPIKE-005-codegen-tool-choice/`.
- **Anti-Pitfall 4 (B8 skip under time pressure):** B8 identity assertion is embedded INLINE in `experiment.py` Step 6 (not deferred to a separate file). The script's final verdict line `b8=PASS|FAIL` is part of the strict exit-code contract: B8 FAIL would have caused exit 1 just like diff-non-empty. B8 actually passed here.
- **Anti-Pitfall 17 (CI 3.13 attribution):** addressed via operator pre-gate response — test matrix GREEN on 3.12+3.13 on `a9c24aa` (origin/main HEAD). Any v1.2-period 3.13-specific break is unambiguously a v1.2 regression. Caveat about pre-existing tests/ and verification/ tech debt (mypy + pre-commit) explicitly documented above.

## Deviations from Plan

### Auto-resolved (Rule 2 — missing critical functionality)

**1. [Rule 2 - Critical fix] B8 identity test required `sys.path` fix to resolve workspace package under `uv run --with unasync`**

- Found during: Task 12-01-03 first run of `experiment.py`.
- Issue: The `uv run --with unasync` ephemeral venv does NOT include workspace packages (`ambito_financiero_client` not importable from inside the script). Without this fix, the B8 identity check would have errored with `ModuleNotFoundError`, defeating the spike's central proof (SC#2).
- Fix: Added `sys.path.insert(0, str(REPO_ROOT / "packages/ambito-financiero-client/src"))` before the B8 import block in Step 6. This is documentation-equivalent to running `uv run --package ambito-financiero-client --with unasync python ...`, but keeps the spike invocation command in the README simple (`uv run --with unasync python ...`).
- Files modified: `.planning/spikes/SPIKE-005-codegen-tool-choice/001a-ambito-round-trip/experiment.py` (iteration 2 of the script).
- Commit: `a8996a1`.

**2. [Rule 2 - Critical fix] Added Step 6b (`__pycache__` cleanup) to make spike artifacts deterministic**

- Found during: Task 12-01-03 second run — noticed `output/__pycache__/` left behind by `importlib.util.spec_from_file_location` + `exec_module`.
- Issue: Spike artifacts must be deterministic across runs; uncommitted bytecode caches would either leak into commits or get inconsistently ignored.
- Fix: Added Step 6b to remove `output/__pycache__` at the end of the experiment.
- Files modified: same file, iteration 3.
- Commit: `a8996a1` (squashed in the same commit as the experiment introduction).

### Documented decisions (no rule changes)

**3. Slopcheck verb update (plan said `slopcheck install unasync`; tooling was installed system-wide)**

- The slopcheck CLI emits a benign Python traceback at end-of-run (its embedded `pip install` step fails inside the slopcheck venv because pip isn't installed there). The legitimacy verdict `[OK] unasync (pypi)` is emitted BEFORE the traceback. The plan's STOP-on-NOT-OK condition is honored (we got OK); the trailing traceback is documented inline in `001a/FINDING.md` so a future reader understands it is not a failure.
- No Rule applied; this is informational documentation only.

**4. Plan §12-VALIDATION.md was already populated by planner**

- The plan instructed the executor to "fill in" 12-VALIDATION.md (overwrite if a template), but on read the file was already fully populated (`nyquist_compliant: true`, `wave_0_complete: true`, Per-Task Verification Map covering 11 tasks across 3 plans, with REFAC-06 traceability and ROADMAP SC mapping). No overwrite needed; verified that the existing content satisfies all acceptance criteria for Task 12-01-02 (frontmatter flags, REFAC-06 count > 0).

### Out-of-scope discoveries (logged for Plan 03)

The `12-RESEARCH.md` §Recipe 2 docstring fix-up entries (`from ambito_financiero_client import aio` → `from ambito_financiero_client import client`, `aio.get_dollar_banco_nacion` → `client.get_dollar_banco_nacion`, `aio.aclose` → `client.close`) were originally proposed as 3 additional `additional_replacements` keys. Empirical observation: unasync 0.6.0's tokenizer does NOT descend into string literals (A1 assumption confirmed in Recipe 1 §Pitfall 7 follow-up). Therefore the docstring fix-up keys are INERT — they do nothing. The 6-key table used in the experiment is the minimal sufficient set. Documented for Plan 02 / Plan 03 reference; no action needed in this plan.

## Next Steps

→ **Plan 02 (Waves 2-4)** continues the spike:

- Wave 2 (Task 12-02-01): 001b `@generated` marker × `from __future__ import annotations` compatibility (4 sub-commands: `ruff check`, `ruff format --check`, `mypy --strict`, `ast.parse`).
- Wave 3 (Task 12-02-02): 001c matriz construct audit (`ast.walk` over 852 LOC, zero-TBD merge gate).
- Wave 4 (Task 12-02-03): 001d matriz deny-list config simulation (sha256 pre/post on `_token_store.py`, `_refresh_policy.py`, `ws_client.py`).

→ **Plan 03 (Wave 5 + 6)** closes the spike:

- Task 12-03-01: re-run the 8-item D-RIGOR-01 evidence checklist end-to-end + compute aggregate GO/NO-GO recommendation.
  - **Pre-knowledge from this plan:** item 1 (byte-identical) FAILs; the aggregate decision must weigh that against the well-bounded Phase 16 source-migration path documented in this Summary + `001a/FINDING.md`.
- Task 12-03-02: operator signoff on DECISION.md (binary GO/NO-GO).
- Task 12-03-03 (GO branch) OR 12-03-04a/b (NO-GO branch): close-out + Skill production.
  - Either branch will include the pre-gate caveat (mypy + pre-commit tech debt) in `12-SUMMARY.md` and create the `mypy-precommit-v1.1-techdebt` follow-up quick-task placeholder.

→ **If 001a had been a NO-GO trigger (semantic unfixable):** Plan 02 still runs to complete failure-mode documentation for the v1.3 libcst pending todo. Not the case here — 001a returned FAIL only on the strict byte-identical contract with all 10 hunks classifying as inherent-asymmetry / cosmetic / consistent-extension.

## Self-Check

Verified before returning to orchestrator.

- [x] `.planning/spikes/SPIKE-005-codegen-tool-choice/README.md` exists, frontmatter `spike: 005`.
- [x] 4 sub-experiment directories exist with README + script + FINDING.
- [x] `.planning/spikes/SPIKE-005-codegen-tool-choice/001a-ambito-round-trip/output/client_generated.py` exists (248 LOC, ruff-clean).
- [x] `.planning/spikes/SPIKE-005-codegen-tool-choice/001a-ambito-round-trip/diff_vs_v1.1_client.txt` exists (10 hunks).
- [x] `.planning/spikes/SPIKE-005-codegen-tool-choice/001a-ambito-round-trip/run_log.txt` contains `B8 IDENTITY: PASS` and `SPIKE 001a VERDICT: FAIL diff=10 hunks b8=PASS format-stable=PASS`.
- [x] `001a/FINDING.md` Verdict line: `**Verdict:** FAIL — ...`.
- [x] `001a/README.md` frontmatter `verdict: FAIL` (no longer TBD) + Investigation Trail section populated.
- [x] `.planning/spikes/MANIFEST.md` has the SPIKE-005 row (`| 005 | codegen-tool-choice | standard | ... | TBD | codegen, unasync, phase-12 |`) and sub-experiments table.
- [x] `12-VALIDATION.md` frontmatter has `nyquist_compliant: true`, `wave_0_complete: true`, REFAC-06 count = 14.
- [x] `git status --porcelain packages/` returns 0 lines (Anti-Pitfall 2 verified).
- [x] No modifications to STATE.md or ROADMAP.md (worktree mode — orchestrator owns those writes).
- [x] Commits c461e42 + a8996a1 both visible in `git log --oneline`.

## Self-Check: PASSED
