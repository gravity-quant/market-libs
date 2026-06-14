---
spike: 005
sub: 001c
name: matriz-construct-audit
type: enumeration
validates: "Given matriz aio.py 852 LOC, when ast.walk enumerates async-only constructs (AsyncFunctionDef, AsyncWith, AsyncFor, Await, asyncio.*) AND operator triages REVIEW rows, then zero TBD/REVIEW/DENY-LIST-VIOLATION rows remain (D-SCOPE-02 merge gate)"
verdict: TBD
related: [001a, 001d]
tags: [codegen, matriz, ast, audit, deny-list]
created: 2026-06-14
---

# Spike 005 / Sub-experiment 001c: Matriz Construct Audit

## What This Validates

**Given** the v1.1 hand-written `packages/matriz-client/src/matriz_client/aio.py` (852 LOC — the worst case for codegen surface area).

**When** an `ast.walk` over the file enumerates every async-only construct (`AsyncFunctionDef`, `AsyncWith`, `AsyncFor`, `Await`, and `asyncio.*` attribute accesses) AND the operator triages every `REVIEW` row into either `deny-list-confirmed` (file pointer) or `manual-sync-proof` (the exact `additional_replacements` entry that produces correct sync).

**Then** zero `TBD` / `REVIEW` / `DENY-LIST-VIOLATION` rows remain in `matriz-aio-constructs.md` (the D-SCOPE-02 merge gate). The output file ends with `MERGE GATE PASS`.

## How to Run

```bash
cd /Users/sebadlf/development/becerra/market-libs
uv run python .planning/spikes/SPIKE-005-codegen-tool-choice/001c-matriz-construct-audit/audit.py
```

No `--with unasync` needed — this audit uses stdlib `ast` only.

## What to Expect

`matriz-aio-constructs.md` is written by the script. Initial rows may carry `REVIEW` status until operator triages; final committed version has zero unresolved rows. `audit-run.log` captures script stdout.

## Investigation Trail

<!-- Filled in Plan 02 -->
