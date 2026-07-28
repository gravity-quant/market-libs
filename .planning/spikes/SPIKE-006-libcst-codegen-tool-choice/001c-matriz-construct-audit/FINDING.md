# 001c — Matriz aio.py Construct Audit (D-RIGOR-02 item 10a)

**Verdict:** PASS — 0 unresolved rows.

## What This Proves

Re-runs the SPIKE-005 construct audit **verbatim** against the CURRENT matriz
`aio.py` (959 LOC — grew from 852 since SPIKE-005). The D-SCOPE-02 merge gate is:
**zero `TBD` / `REVIEW` / `DENY-LIST-VIOLATION` rows**. This is a structural,
deterministic `ast.walk` property, so it is tool-independent — libcst inherits it
exactly as unasync did. The audit reads `aio.py` read-only; no `packages/` mutation.

## Method

- `audit.py` is **byte-identical** to
  `.planning/spikes/SPIKE-005-codegen-tool-choice/001c-matriz-construct-audit/audit.py`
  (`diff` = empty). It uses pure stdlib `ast` — **no libcst** (so this experiment does
  not consume the ephemeral libcst install / D-05 gate).
- `SOURCE = REPO_ROOT / "packages/matriz-client/src/matriz_client/aio.py"` where
  `REPO_ROOT = Path(__file__).resolve().parents[4]`. The spike sub-dir sits at the same
  depth as SPIKE-005, so `parents[4]` resolves to the repo root and `SOURCE`
  automatically points at the CURRENT matriz `aio.py` — no edit required.
- `DENY_LIST` (audit.py lines 46–53) = the 4 locked files: `_token_store.py`,
  `_refresh_policy.py`, `_refresh.py`, `ws_client.py` (D-09 — confirmed, not renegotiated).

## Run (2026-07-02)

```text
$ uv run python .planning/spikes/SPIKE-006-libcst-codegen-tool-choice/001c-matriz-construct-audit/audit.py
Audit written to .../001c-matriz-construct-audit/matriz-aio-constructs.md
Total rows: 110
Unresolved (REVIEW/TBD/DENY-LIST-VIOLATION): 0
Deny-list imports detected in aio.py (re-exports): ['build_token_store']
exit code: 0
```

`matriz-aio-constructs.md` tail:

```text
## Unresolved rows: 0

**MERGE GATE PASS:** zero unresolved rows.
```

## Row Count Note (Pitfall 2)

SPIKE-005 recorded **109 rows** against an 852-LOC `aio.py`. The current 959-LOC `aio.py`
enumerates **110 rows** — a +1 drift from ordinary async-surface growth. The gate is
**"0 unresolved," NOT a fixed row count**; the +1 row is `manual-sync-proof` and does not
affect the merge gate. Hardcoding a `== 109` (or `== 110`) assertion would be Pitfall 2 and
is deliberately avoided — `audit.py` exits 0 iff `len(unresolved) == 0`.

## Structural Guarantee (inherited)

The critical SPIKE-005 observation holds: matriz `aio.py` has **zero bare `asyncio.<attr>`
references in the code body** — every `asyncio.*` mention lives inside a docstring/string
literal (classified `comment-only`, preserved verbatim). The async concurrency primitives
are entirely encapsulated in the deny-listed `_token_store.py`. This is a stronger guarantee
than per-module transform scope alone (item 10b): even if the deny-list scope were
mis-configured, there are no bare deny-listed primitives in `aio.py`'s body for a
transformer to touch.

## Verification-command reconciliation

The 18-01 plan's `<automated>` verify greps **stdout** for `MERGE GATE PASS`. The
**verbatim** `audit.py` (mandated by the `spike-findings-codegen-market-libs` SKILL and the
plan's must-have "Verbatim copy") writes that sentinel to its **output file**
`matriz-aio-constructs.md`, not to stdout — stdout carries `Unresolved (...): 0`. The correct
verification greps the audit's output file:

```bash
uv run python .../001c/audit.py \
  && grep -q '\*\*MERGE GATE PASS:\*\*' \
       .planning/spikes/SPIKE-006-libcst-codegen-tool-choice/001c-matriz-construct-audit/matriz-aio-constructs.md
```

`audit-run.log` captures the stdout transcript plus the appended merge-gate lines from the
output file, so the sentinel is present there too. See the 18-01 SUMMARY "Deviations" section.

## Linkage

- Audit output: `001c-matriz-construct-audit/matriz-aio-constructs.md`
- Run log: `001c-matriz-construct-audit/audit-run.log`
- Evidence: `evidence-checklist.txt` §item 10a
- Prior art: `.planning/spikes/SPIKE-005-codegen-tool-choice/001c-matriz-construct-audit/FINDING.md`
