---
spike: 005
sub: 001a
name: ambito-round-trip
type: comparison
validates: "Given v1.1 hand-written ambito client.py, when unasync.unasync_files() runs on aio.py with prescribed additional_replacements AND ruff format normalizes, then diff is empty AND B8 identity preserved (mod._raise_for_response is aio._raise_for_response is _core.raise_for_response)"
verdict: TBD
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

<!-- Filled after experiment runs -->
