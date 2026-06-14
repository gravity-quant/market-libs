---
spike: 005
sub: 001c
name: matriz-construct-audit
type: enumeration
validates: "Given matriz aio.py 852 LOC, when ast.walk enumerates async-only constructs (AsyncFunctionDef, AsyncWith, AsyncFor, Await, asyncio.*) AND operator triages REVIEW rows, then zero TBD/REVIEW/DENY-LIST-VIOLATION rows remain (D-SCOPE-02 merge gate)"
verdict: PASS
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

**Run (2026-06-14):** Single pass — the `ast.walk` produced 109 rows: 106
`manual-sync-proof` (every `async def` / `await` / `async with` / `async for`
delegates to a unasync default replacement) + 3 `comment-only` (docstring
mentions of `asyncio.Lock` and `asyncio.to_thread` at lines 42, 235, 267 —
preserved verbatim by the unasync tokenizer because they live inside string
literals). **Zero REVIEW / TBD / DENY-LIST-VIOLATION rows.** No operator
triage required: the audit's classifier resolves every row deterministically
from the source AST shape + docstring-line membership.

**Critical observation:** matriz `aio.py` has ZERO bare `asyncio.<attr>`
references in code body. Every `asyncio.Lock` / `asyncio.to_thread` mention
is encapsulated inside `_token_store.py` (via the deny-listed import of
`build_token_store`); aio.py only orchestrates `await
token_store.get_async()`. This means the deny-list is structurally
self-enforcing — codegen cannot produce a broken sync emission for the
deny-listed primitives because aio.py never names them directly.

See `FINDING.md` for the full Audit Summary + Triage Notes + Matriz Rule
Config Draft + Anti-Pitfall 5 Compliance sections.
