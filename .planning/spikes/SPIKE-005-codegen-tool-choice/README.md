---
spike: 005
name: codegen-tool-choice
type: standard
validates: "Given the v1.1 hand-written packages/ambito-financiero-client/.../client.py + matriz aio.py 852 LOC, when unasync 0.6.0 runs against aio.py with prescribed additional_replacements AND ruff format normalizes, then byte-identical diff + B8 identity preserved + matriz construct audit zero TBD + deny-list intact"
verdict: NO-GO
signoff_date: 2026-06-14
signoff_by: sebadlf
related: [001a, 001b, 001c, 001d]
tags: [codegen, unasync, ambito, matriz, B8-identity, phase-12]
created: 2026-06-14
---

# Spike 005: Codegen Tool Choice (unasync vs libcst)

## What This Validates

**Given** the v1.1 hand-written `packages/ambito-financiero-client/src/ambito_financiero_client/client.py` (sync transport shell) and `aio.py` (async transport shell), PLUS the v1.1 hand-written `packages/matriz-client/src/matriz_client/aio.py` (852 LOC, the worst case for the codegen tool).

**When** `unasync 0.6.0` runs against each `aio.py` with a prescribed `additional_replacements` table AND `uv run ruff format` post-processes the output, AND for matriz the deny-list (`_token_store.py`, `_refresh_policy.py`, `ws_client.py`) is excluded from codegen, AND the `@generated` marker is prepended to the output.

**Then**:

1. The generated `client.py` is byte-identical to the v1.1 hand-written `client.py` modulo `ruff format` normalization (SC#1).
2. The B8 identity invariant survives: `client._raise_for_response is aio._raise_for_response is _core.raise_for_response` (SC#2).
3. Every async-only construct in matriz `aio.py` is classified — zero `TBD` / `REVIEW` / `DENY-LIST-VIOLATION` rows remain (SC#3).
4. Deny-listed matriz files are byte-identical pre/post codegen (sha256 equal — D-SCOPE-02 enforcement).
5. The `@generated` marker comment is compatible with `from __future__ import annotations` (Python grammar PEP 236).

## Research

See `.planning/phases/12-codegen-spike/12-RESEARCH.md` for the full Recipe set (1-10). Key inputs:

| Question | Resolution |
|----------|------------|
| Tool | `unasync >=0.6.0,<0.7` (primary candidate; libcst NOT explored inline per D-NOGO-01) |
| Install | Transient via `uv run --with unasync python <experiment>.py` (Phase 16 GO branch decides whether to add to `[dependency-groups] dev`) |
| Canary | Ámbito (simplest — no auth, no token refresh, no envelope) |
| Worst case | Matriz aio.py 852 LOC |
| Timebox | 1 day hard cap (D-SCOPE-03) — overflow triggers AUTO-NO-GO |
| Decision binary | GO (Phase 16 proceeds with captured per-package Rule configs) / NO-GO (REFAC-06 defers to v1.3, Phase 16 DROPPED) |
| Slopcheck status | unasync `[OK] (pypi)` verified 2026-06-14 (see `001a-ambito-round-trip/FINDING.md`) |

## How to Run

```bash
cd /Users/sebadlf/development/becerra/market-libs

# Wave 1 — canary
uv run --with unasync python .planning/spikes/SPIKE-005-codegen-tool-choice/001a-ambito-round-trip/experiment.py

# Wave 2 — marker compatibility (Plan 02)
uv run --with unasync python .planning/spikes/SPIKE-005-codegen-tool-choice/001b-ambito-marker-future-compat/experiment.py

# Wave 3 — matriz audit (Plan 02)
uv run python .planning/spikes/SPIKE-005-codegen-tool-choice/001c-matriz-construct-audit/audit.py

# Wave 4 — matriz deny-list config (Plan 02)
uv run --with unasync python .planning/spikes/SPIKE-005-codegen-tool-choice/001d-matriz-deny-list-config/experiment.py

# Wave 5 — evidence checklist + DECISION.md (Plan 03)
```

## What to Expect

Each sub-experiment emits a `FINDING.md` with a `**Verdict:**` line (PASS / FAIL). The aggregate verdict is computed in Plan 03 Task 12-03-01 by re-running the 8 D-RIGOR-01 evidence items end-to-end into `evidence-checklist.txt`, then operator-signed in `DECISION.md`.

- **GO** iff 8/8 items PASS AND matriz audit unresolved rows == 0 AND timebox status == `WITHIN-CAP`.
- **NO-GO** if ANY of: any item FAILs, matriz unresolved rows > 0, timebox `OVER-CAP`.

## Sub-Experiments

| # | Name | Type | Plan | What it proves |
|---|------|------|------|----------------|
| 001a | ambito-round-trip | comparison | 01 | Byte-identical round-trip + B8 identity preserved (the canary) |
| 001b | ambito-marker-future-compat | standard | 02 | `@generated` marker compatible with `from __future__ import annotations` (ruff/mypy/ast.parse) |
| 001c | matriz-construct-audit | enumeration | 02 | Zero TBD / REVIEW / DENY-LIST-VIOLATION rows in matriz aio.py 852 LOC walk |
| 001d | matriz-deny-list-config | standard | 02 | Per-file `Rule(fromdir=aio.py-only)` simulated; deny-listed files byte-identical (sha256 equal) |

## Forward References

- **Phase 16** (REFAC-06 codegen × 4 transport shells): CONDITIONAL on this spike returning GO. If NO-GO, Phase 16 is DROPPED and REFAC-06 defers to v1.3.
- **Phase 17** (LIVE-03 final gate): runs AFTER Phase 14 + 15 regardless of this spike's outcome.
- **CLAUDE.md auto-loaded Skill** `spike-findings-codegen-market-libs` produced by `/gsd-spike --wrap-up` in Plan 03 Task 12-03-03 (GO) or 12-03-04a (NO-GO).
