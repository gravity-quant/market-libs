---
spike: 005
sub: 001a
name: ambito-round-trip
type: comparison
validates: "Given v1.1 hand-written ambito client.py, when unasync.unasync_files() runs on aio.py with prescribed additional_replacements AND ruff format normalizes, then diff is empty AND B8 identity preserved (mod._raise_for_response is aio._raise_for_response is _core.raise_for_response)"
verdict: FAIL
related: [001b, 001c, 001d]
tags: [codegen, unasync, ambito, byte-identical, B8-identity]
created: 2026-06-14
---

# Spike 005 / Sub-experiment 001a: Ámbito Round-Trip (Canary)

## What This Validates

**Given** the v1.1 hand-written `packages/ambito-financiero-client/src/ambito_financiero_client/client.py` (sync transport shell, ~260 LOC).

**When** `unasync.unasync_files()` runs on a `shutil.copy` of `packages/.../aio.py` (read-only source) with the prescribed `additional_replacements` table, AND `uv run ruff format` post-processes the output, AND the result is renamed to `output/client_generated.py`.

**Then**:

1. `diff -u <v1.1 client.py> <client_generated.py>` returns empty (SC#1: byte-identical round-trip).
2. `mod._raise_for_response is aio._raise_for_response is _core.raise_for_response` (SC#2: B8 identity preserved).
3. `uv run ruff format --check <generated>` exits 0 (format-stable / idempotent — Pitfall 3 mitigation).

## How to Run

```bash
cd /Users/sebadlf/development/becerra/market-libs
uv run --with unasync python .planning/spikes/SPIKE-005-codegen-tool-choice/001a-ambito-round-trip/experiment.py
```

Captures stdout/stderr to `run_log.txt`, diff transcript to `diff_vs_v1.1_client.txt`, B8 identity result inline in `run_log.txt`. Exits 0 on PASS (empty diff AND B8 assertion holds); exits 1 on FAIL.

## What to Expect

| Outcome | Verdict | Next |
|---------|---------|------|
| Diff empty AND B8 PASS | PASS | FINDING.md verdict PASS + Rule config draft captured for Phase 16 |
| Diff non-empty (cosmetic, fixable, or inherent-asymmetry) | PASS or DEVIATION | Classify per Recipe 2 triage protocol; inherent-asymmetry (e.g., `_validate_max_retries` import direction) does NOT trigger NO-GO |
| Diff non-empty AND unfixable-structural | FAIL | NO-GO root cause documented |
| B8 identity FAILED | FAIL | Spike heading NO-GO; thunk wrapper detected (Pitfalls.md §Pitfall 4) |

## Investigation Trail

### Iteration 1 — initial run (2026-06-14)

- Wrote `experiment.py` with 7 steps (copy → unasync → rename → ruff format → ruff format --check → diff → B8 identity) and the 6-key `additional_replacements` table prescribed by 12-RESEARCH.md §"Recipe 1".
- First run via `uv run --with unasync python experiment.py`:
  - Steps 1-4 PASS (copy, unasync emits `client_generated.py`, ruff format leaves it unchanged — meaning unasync already produces ruff-clean output).
  - Step 4b PASS (`ruff format --check` exits 0 — format-stable / idempotent).
  - Step 5 returns diff exit 1 with 10 hunks. Diff transcript written to `diff_vs_v1.1_client.txt`.
  - Step 6 (B8 identity) failed with `ModuleNotFoundError: No module named 'ambito_financiero_client'` because the `uv run --with unasync` ephemeral venv does NOT install workspace packages.

### Iteration 2 — sys.path fix for B8 identity (2026-06-14)

- Added `sys.path.insert(0, str(REPO_ROOT / "packages/ambito-financiero-client/src"))` BEFORE the import block in Step 6.
- Re-ran: Step 6 now imports `ambito_financiero_client._core` + `ambito_financiero_client.aio` successfully.
- **B8 identity: PASS** — all three identifiers resolve to the same object id (`0x106d2afc0` in this run). Asserted via `is` chain.

### Iteration 3 — pycache cleanup (2026-06-14)

- Added Step 6b to remove `output/__pycache__` left by `importlib.util.spec_from_file_location` + `exec_module`.
- Spike artifacts are now deterministic across runs (no bytecode caches accumulate).

### Diff Triage (2026-06-14)

- Per Recipe 2 triage protocol (12-RESEARCH.md), each of the 10 hunks was classified:
  - **7 hunks** → inherent asymmetry (class 4). Phase 16 source-migration steps documented in FINDING.md.
  - **2 hunks** → cosmetic (class 1) — ruff format does not converge on single-line import order or constant placement. Phase 16 fix = tighter ruff/isort config OR source-pin.
  - **1 hunk** → semantic-consistent extension (codegen extends sync surface with `close()` delegator + `__all__` entry).
  - **0 hunks** → "semantic NOT fixable via additional_replacements" (the only NO-GO trigger per Recipe 2 line 507).

### Boundary case noted (Anti-Pitfall 7 follow-up)

- Docstring contents were preserved verbatim by unasync's tokenizer — the tokenizer does NOT descend into string literals (A1 assumption confirmed).
- The hand-written docstring-text asymmetry (sincrónico vs asincrónico, examples block) IS observable in the diff and IS classified as inherent-asymmetry. Phase 16 strategy = source-of-truth = `aio.py` (async docstrings authored canonical; sync docstrings get token-rewritten where keys overlap). Open question 2 in FINDING.md captures the maintenance-burden tradeoff.

### Verdict

- **Strict byte-identical contract:** FAIL (10 hunks, script exit code 1).
- **B8 identity:** PASS.
- **Format-stable:** PASS.
- **Recipe-2 NO-GO triggers:** 0.
- **Path to GO in Phase 16:** well-bounded — 6 source-migration steps on `aio.py` (~30 LOC of edits) plus per-package Rule. Plan 03 Task 12-03-01 will weigh item 1 FAIL against this when computing the 8-item aggregate. The spike's job ends here with full data captured.
