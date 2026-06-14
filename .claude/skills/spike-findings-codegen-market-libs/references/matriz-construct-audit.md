# Matriz `aio.py` Construct Audit — Reference (D-SCOPE-02)

Synthesized from `sources/001c-matriz-construct-audit-FINDING.md` for self-contained
Skill reference. Captures the audit methodology, the 109-row classification result, and
the structural deny-list self-enforcement observation that makes matriz a stronger
codegen scope guarantee than fpath_list alone.

## Audit Methodology

- **Tool:** stdlib `ast.walk` over `packages/matriz-client/src/matriz_client/aio.py`
  (852 LOC, READ-ONLY).
- **Script:** `001c-matriz-construct-audit/audit.py` (~225 LOC stdlib `ast` only).
- **Capture:** `audit.py 2>&1 | tee audit-run.log` proves the audit ran end-to-end (not
  hand-crafted).
- **Output:** `matriz-aio-constructs.md` (classification table).
- **Merge gate:** `grep -cE '\| (REVIEW|TBD|DENY-LIST-VIOLATION) \|' matriz-aio-constructs.md`
  returns 0 (D-SCOPE-02 satisfied).

## Result (109 rows)

| Category | Count | Examples |
|----------|-------|----------|
| `manual-sync-proof` | 106 | `async def <name>` → `def <name>` (unasync default), `async with` → `with` (unasync default), `await <expr>` → `<expr>` (await keyword stripped), `__aenter__` → `__enter__` |
| `comment-only` | 3 | Docstring mentions of `asyncio.Lock` at line 235; `asyncio.to_thread` at lines 42 and 267 |
| `REVIEW` | 0 | (none) |
| `TBD` | 0 | (none) |
| `DENY-LIST-VIOLATION` | 0 | (none) |

**Total:** 109 rows / 0 unresolved → D-SCOPE-02 merge gate PASS.

## Triage Notes (zero operator intervention)

The audit's classifier resolved every row deterministically from the AST shape. No
operator triage was required.

- `async def`, `async with`, `async for`, `await` AST node types → classified
  `manual-sync-proof` automatically (unasync default strips them).
- `ast.Attribute` nodes with `node.value.id == "asyncio"` → zero hits in the entire file.
  The grep universe (~128 matches) overestimated because grep can't distinguish code from
  docstrings.
- Docstring `asyncio.*` mentions → detected by checking source line membership in
  `ast.Constant(value: str)` spans. Three lines: 42, 235, 267. Classified
  `comment-only`.
- Bare `import asyncio` or `from asyncio import ...` → zero hits. The async primitives
  (`Lock`, `to_thread`) are entirely encapsulated inside `matriz_client._token_store`;
  aio.py only imports `build_token_store`.

## Structural Deny-List Self-Enforcement

This is the **key insight** for codegen scope:

> matriz `aio.py` has ZERO bare `asyncio.<attr>` references in code body. All are inside
> docstrings. The async primitives are entirely encapsulated inside `_token_store.py`
> (deny-listed).

**Implication:** the codegen Rule cannot accidentally rewrite `asyncio.Lock` or
`asyncio.to_thread` in matriz aio.py — there is no token to match. This is a stronger
guarantee than the unasync `fpath_list` file-scope deny-list (001d):

- `fpath_list` scope says: "the tool does not get a handle to the deny-listed files".
- Structural self-enforcement says: "the tokens that would mutate the deny-listed
  primitives are not even referenced in aio.py".

Both guarantees compose: a buggy Rule cannot mutate the deny-list, AND aio.py is shaped
such that the Rule has no opportunity to attempt the mutation in the first place.

v1.3 libcst inherits this audit directly:
- Re-run `audit.py` against the current matriz aio.py. If 109 rows / 0 unresolved still
  holds, no v1.3-specific work needed on the matriz scope.
- The structural self-enforcement observation extends to libcst — the AST nodes the
  audit identifies as code-body constructs are the only ones libcst CSTTransformer
  needs to handle; deny-listed primitives are out of scope by source-shape, not by
  tool config.

## Matriz Rule Config Draft (informative)

From `sources/001c-matriz-construct-audit-FINDING.md` and DECISION.md per-package
draft:

```python
unasync.Rule(
    fromdir=str(MATRIZ_DIR) + "/",
    todir=str(MATRIZ_DIR) + "/",
    additional_replacements={
        # Inherited from ámbito Rule:
        "AsyncClient": "Client",
        "AsyncRetryTransport": "RetryTransport",
        "_atransport": "_transport",
        "aclose": "close",
        # Matriz-specific additions:
        "_aensure_token": "_ensure_token",
        "MatrizAsyncClient": "MatrizClient",
    },
)
unasync.unasync_files(
    fpath_list=[str(MATRIZ_DIR / "aio.py")],   # DENY-LIST enforced by file scope
    rules=[<above Rule>],
)
```

Deny-list scope (locked per ARCHITECTURE.md, CONFIRMED by 001d sha256):

| File | Role | Why deny-listed |
|------|------|-----------------|
| `_token_store.py` | 3-way TokenStore | `threading.Lock` + per-loop `asyncio.Lock` + `asyncio.to_thread` cross-loop primitive — cannot be mechanically rewritten by token replacement OR AST transform. |
| `_refresh_policy.py` | retry + backoff + fail-cache | Pure sync (runs inside `asyncio.to_thread`). No async/await tokens to strip. |
| `_refresh.py` | MatrizRefresh adapter | Sync `httpx.Client`-based refresh adapter. Async path delegates. |
| `ws_client.py` | WebSocket daemon thread | Uses `websocket-client` library; daemon-thread event loop; no `asyncio` primitives in module body. |

## Anti-Pitfall 5 Compliance

The programmatic grep-gate ensures soft-relax is impossible:

```bash
grep -cE '\| (REVIEW|TBD|DENY-LIST-VIOLATION) \|' matriz-aio-constructs.md
# Output: 0
```

If any future re-run of `audit.py` against a modified aio.py introduces a `REVIEW`
row, the gate fails and the spike re-opens for triage.

## Linkage

- Full FINDING: `sources/001c-matriz-construct-audit-FINDING.md`
- audit script + log: SPIKE-005 `001c-matriz-construct-audit/audit.py` + `audit-run.log`
- classification table: SPIKE-005 `001c-matriz-construct-audit/matriz-aio-constructs.md`
- Deny-list intactness check: `sources/001d-matriz-deny-list-config-FINDING.md`
