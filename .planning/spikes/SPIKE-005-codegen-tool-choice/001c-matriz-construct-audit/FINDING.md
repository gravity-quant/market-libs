# FINDING: Matriz aio.py Construct Audit

**Verdict:** PASS

**D-SCOPE-02 merge gate satisfied:** zero `REVIEW` / `TBD` / `DENY-LIST-VIOLATION`
rows in `matriz-aio-constructs.md`. The 852 LOC matriz `aio.py` enumerates 109
async-only constructs across 2 categories:

- 106 rows `manual-sync-proof` — every `async def` / `await` / `async with` /
  `async for` has a documented unasync default replacement (`async def → def`,
  `async with → with`, etc.).
- 3 rows `comment-only` — `asyncio.Lock` / `asyncio.to_thread` mentions inside
  string-literal docstrings at lines 42, 235, 267. The unasync tokenizer
  preserves string contents verbatim (A1 assumption from 12-RESEARCH.md §Pitfall
  7 confirmed empirically in 001a).
- 0 rows `REVIEW`, 0 `TBD`, 0 `DENY-LIST-VIOLATION`.

## Audit Summary

| Property | Value |
|----------|-------|
| Source | `packages/matriz-client/src/matriz_client/aio.py` (852 LOC) |
| Tool | `audit.py` — stdlib `ast.walk`, read-only |
| Run command | `uv run python audit.py 2>&1 \| tee audit-run.log` |
| Total rows emitted | 109 |
| `manual-sync-proof` | 106 |
| `comment-only` | 3 |
| `REVIEW` (operator triage needed) | 0 |
| `TBD` | 0 |
| `DENY-LIST-VIOLATION` | 0 |
| Deny-list import names detected | `build_token_store` (from `matriz_client._token_store`) |
| audit-run.log | `audit-run.log` (4 lines, including "Audit written to ...") |
| matriz-aio-constructs.md tail | `**MERGE GATE PASS:** zero unresolved rows.` |

**Anti-Pitfall 5 + Anti-Pitfall #4 (plan-checker iteration-1) compliance evidence:**

1. The audit script executed via `tee audit-run.log` — the log file exists and
   contains the canonical `Audit written to /…/matriz-aio-constructs.md` line
   from `audit.py` Step 7. This proves the table is machine-generated, not
   hand-crafted.
2. The classification table has zero unresolved rows — verified by:
   ```bash
   grep -cE '\| (REVIEW|TBD|DENY-LIST-VIOLATION) \|' matriz-aio-constructs.md
   # 0
   ```
3. The merge-gate sentinel `**MERGE GATE PASS:** zero unresolved rows.` is
   present at file end.

## Triage Notes

The audit's classifier resolved every row deterministically from the source AST
shape; **no operator triage was required**. The triage logic embedded in the
audit:

- **`async def <name>` / `async with` / `async for` / `await <expr>`:**
  classified `manual-sync-proof` with reference to the corresponding unasync
  default replacement in `KNOWN_SYNC_EMISSIONS`.
- **`asyncio.<attr>` Attribute access in code:** the AST walker did NOT find any.
  The script enumerates `ast.Attribute` nodes with `node.value.id == "asyncio"`;
  zero hits in the entire file. The grep universe (~128 matches) overestimated
  because grep cannot distinguish code from docstrings.
- **`asyncio.*` mentions inside docstrings:** detected by checking whether the
  source line falls inside an `ast.Constant(value: str)` span. Three such lines
  found: 42 (`asyncio.to_thread`), 235 (`asyncio.Lock`), 267 (`asyncio.to_thread`).
  Classified `comment-only` — the unasync tokenizer preserves string contents
  verbatim (A1 assumption from 12-RESEARCH.md; confirmed in 001a docstring
  inspection where `aio.aclose` mentions inside the source docstring survived
  the tokenizer).
- **Bare `import asyncio` or `from asyncio import ...`:** the script enumerates
  `ast.Import` and `ast.ImportFrom`; zero hits in matriz aio.py. The async
  primitives (`Lock`, `to_thread`) are entirely encapsulated inside
  `matriz_client._token_store`; aio.py only imports `build_token_store` from
  that module, which is itself in the deny-list.

**Structural deny-list self-enforcement:** because matriz `aio.py` never names
`asyncio.Lock` or `asyncio.to_thread` in code body (they live in
`_token_store.py`), the codegen Rule cannot accidentally rewrite them — there
is no token to match. This is a stronger guarantee than the unasync `fpath_list`
file-scope deny-list (001d).

## Matriz Rule Config Draft

Inferred from 001a ámbito Rule + matriz construct audit deltas:

```python
unasync.Rule(
    fromdir=str(WORK / "matriz_client") + "/",
    todir=str(WORK / "matriz_client") + "/",
    additional_replacements={
        # Inherited from ámbito Rule (001a/FINDING.md):
        "AsyncClient": "Client",
        "AsyncRetryTransport": "RetryTransport",
        "_atransport": "_transport",
        "aclose": "close",
        # Matriz-specific additions (delta from ámbito):
        "_aensure_token": "_ensure_token",
        "MatrizAsyncClient": "MatrizClient",  # if/when matriz adopts the typed name
        # Per-loop primitives NOT listed — they live in _token_store.py (deny-listed):
        #   asyncio.Lock, asyncio.to_thread, _get_async_lock, _async_locks
        # PEP 562 shim symbols passed through verbatim (no async/await keyword):
        #   _default_async_client → _default_client (if symbol exists; otherwise no-op)
    },
)
```

**Tokens NOT in additional_replacements (intentional)** — these are either
defaults (unasync handles them) or never appear in matriz aio.py code body:

| Token | Why not in Rule |
|-------|-----------------|
| `asyncio.Lock` | Inside `_token_store.py` (deny-list); never named in aio.py code |
| `asyncio.to_thread` | Inside `_token_store.py` (deny-list); never named in aio.py code |
| `_get_async_lock` | Inside `_token_store.py` (deny-list) |
| `_async_locks` | Inside `_token_store.py` (deny-list) |
| `__aenter__` / `__aexit__` / `__aiter__` | unasync default replacement |
| `await` keyword | unasync default strip |
| `async def` / `async with` / `async for` | unasync default strip |
| `AsyncIterable` / `AsyncIterator` / etc. | unasync default replacement |

**Per-package Rule config drafts** (for DECISION.md GO-branch block):

| Package | Rule config |
|---------|-------------|
| ámbito | 6-key minimal set (001a/FINDING.md) — `AsyncClient → Client`, `AsyncRetryTransport → RetryTransport`, `_atransport → _transport`, `aclose → close`, `AmbitoFinancieroAsyncClient → AmbitoFinancieroClient`, `_default_async_client → _default_client` |
| iol | Inferred from ámbito + iol-specific token names (`IolAsyncClient → IolClient` if defined; OAuth refresh-token + `event_hooks` lock NOT in deny-list per ARCHITECTURE.md, so the Rule covers them via additional_replacements). Phase 16 finalizes. |
| higyrus | Inferred from ámbito + higyrus-specific token names. Phase 16 finalizes. |
| matriz | Above draft (ámbito superset + `_aensure_token → _ensure_token`); deny-list of 4 files enforced via single-file `fpath_list = [aio.py]` (001d). |

## Anti-Pitfall 5 Compliance

The programmatic grep-gate from Recipe 4 / Anti-Pitfall 5 is satisfied:

```bash
grep -cE '\| (REVIEW|TBD|DENY-LIST-VIOLATION) \|' matriz-aio-constructs.md
# Output: 0
```

This is the hard merge gate — soft-relax is impossible. If any future re-run of
`audit.py` against a modified aio.py introduces a `REVIEW` row, the gate fails
and the spike re-opens for triage.

## Anti-Pitfall #4 (plan-checker iteration-1) Compliance

The plan-checker iteration-1 warning #4 — "audit table could be hand-crafted
without actually running audit.py" — is mitigated by the `audit-run.log` file:

```text
Audit written to /…/matriz-aio-constructs.md
Total rows: 109
Unresolved (REVIEW/TBD/DENY-LIST-VIOLATION): 0
Deny-list imports detected in aio.py (re-exports): ['build_token_store']
```

These 4 lines are the canonical stdout of `audit.py` Step 7+ (the `print(...)`
calls). Their presence in a separate file (`audit-run.log`) proves the script
ran end-to-end, not that the table was hand-edited to look like machine output.

## Open Questions for Operator

None. The audit's classifier resolved every row deterministically. The merge
gate PASSES without operator intervention. The matriz Rule config draft above
is ready for Phase 16 consumption.

## Slopcheck

No new install — audit uses stdlib `ast` only. The `uv run` command resolves
the workspace venv; no `--with` needed. unasync legitimacy verified at Plan 01
start; recorded in `001a/FINDING.md`.

## Linkage

- `audit.py` — stdlib `ast.walk`-based audit script.
- `audit-run.log` — captured stdout of the audit run.
- `matriz-aio-constructs.md` — the classification table (109 rows, MERGE GATE PASS).
- `001a/FINDING.md` — ámbito Rule config (this matriz Rule is a superset).
- `001d/FINDING.md` (next task) — sha256 verification that the deny-list of 4
  files remains byte-identical when only aio.py is in the codegen `fpath_list`.
