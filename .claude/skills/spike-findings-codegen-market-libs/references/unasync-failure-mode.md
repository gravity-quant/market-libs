# unasync 0.6.0 — Failure Mode Reference (SPIKE-005 NO-GO)

Synthesized from `sources/001a-ambito-round-trip-FINDING.md` for self-contained Skill
reference. Captures what unasync 0.6.0 CAN do, what it CAN'T, and the concrete failure
transcripts that triggered SPIKE-005 NO-GO.

## What unasync 0.6.0 does well (PASS evidence)

unasync 0.6.0 is a tokenize-and-replace codegen tool:

1. **Tokenize** the source Python file using stdlib `tokenize`.
2. **Replace** specific token sequences via the `additional_replacements` dict (single-token
   substitutions only — multi-token sequences like `@pytest.mark.trio` are not supported).
3. **Strip** `async` / `await` keywords (default behavior, no config).
4. **Default substitutions** (no config needed):
   - `__aenter__` → `__enter__`, `__aexit__` → `__exit__`, `__aiter__` → `__iter__`, `__anext__` → `__next__`
   - `asynccontextmanager` → `contextmanager`
   - `AsyncIterable` → `Iterable`, `AsyncIterator` → `Iterator`, `AsyncGenerator` → `Generator`, `StopAsyncIteration` → `StopIteration`
5. **Preserves** verbatim:
   - Docstrings (string literals) — the tokenizer treats them as opaque tokens. Token replacements
     do NOT descend into string-literal contents (matches SPIKE-005 001a A1 assumption +
     001c docstring `asyncio.*` preservation evidence).
   - Comments — same tokenize policy.
   - Identifiers not in `additional_replacements` keys — emitted as-is.
   - The 5-token alias line `_raise_for_response = _core.raise_for_response` (B8 identity,
     SPIKE-005 item 2 PASS).

### Confirmed passes (SPIKE-005 evidence)

- **Item 2 (B8 identity):** PASS. `mod._raise_for_response is aio._raise_for_response is _core.raise_for_response`
  — all three resolve to same Python object id. Pitfall 4 (thunk-wrapper failure mode)
  does not surface.
- **Item 3 (`ruff format --check`):** PASS. `unasync` emits ruff-clean output to begin
  with; `ruff format` is idempotent on the result.
- **Item 5 (`mypy --strict`):** PASS in canonical workspace-venv invocation.
- **Item 7 (`lint-imports` 4 contracts):** PASS — spike does NOT touch packages/, so
  production contracts unchanged.
- **Item 8 (marker × `from __future__`):** PASS — marker-neutral on all 4 commands.

## What unasync 0.6.0 CANNOT do (NO-GO failure modes)

Token replacement matches single tokens only. It CANNOT:

1. **Reverse import direction.** If `aio.py` imports `_validate_max_retries` from
   `client.py`, the codegen-generated `client.py` token-replaces the line verbatim into
   `from <pkg>.client import _validate_max_retries` — which becomes a self-import. The
   only fix is source migration: move the definition from client.py to aio.py.
2. **Normalize single-line import order.** Tokenize-and-replace preserves token sequence;
   it cannot reorder `from <pkg> import _transport, _core` to alphabetical
   `_core, _transport`. ruff format does NOT converge on this either (single-line imports
   are intentionally left as-is by the formatter).
3. **Localize docstring text.** Docstrings are opaque string tokens; substring replacement
   inside them is not possible. `additional_replacements` for substrings inside docstrings
   (e.g., "asincrónico" → "sincrónico") is INERT — confirmed in SPIKE-005 001a Step 6b.
4. **Add or remove module-level statements.** Token replacement is in-place per token;
   it cannot insert new statements (e.g., a sync-only `close()` delegator) or elide
   async-only statements (e.g., the WR-07 ResourceWarning block in `configure()`).

### Concrete failure transcripts (SPIKE-005 NO-GO)

**Item 1 (byte-identical round-trip):**

```
$ diff -u packages/ambito-financiero-client/src/ambito_financiero_client/client.py \
          .planning/spikes/SPIKE-005-codegen-tool-choice/001a-ambito-round-trip/output/client_generated.py
exit code: 1
hunk count: 10
```

10 hunks classified per Recipe 2:
- 7 hunks class 4 (inherent-asymmetry — root cause: source-shape).
- 2 hunks class 1 (cosmetic — ruff format does not converge).
- 1 hunk semantic-consistent-extension (close() module delegator).
- **0 hunks class 3 (NO-GO trigger).** The tool is structurally sound; the gap is
  source-shape compatibility.

**Item 4 (ruff check — I001 import order):**

```
I001 [*] Import block is un-sorted or un-formatted
  --> .../client_generated.py:23:1
32 | | from ambito_financiero_client import _transport, _core
   | |
Found 1 error.
exit code: 1
```

ASYNC1xx false-positives anticipated by D-RIGOR-01 item 4 did NOT materialize.

**Item 6 (ámbito pytest sandbox — circular import):**

```
ImportError while loading conftest '/private/tmp/.../tests/conftest.py'.
src/ambito_financiero_client/client.py:34: in <module>
    from ambito_financiero_client.client import _validate_max_retries
E   ImportError: cannot import name '_validate_max_retries' from partially initialized
    module 'ambito_financiero_client.client' (most likely due to a circular import)
exit code: 2 (collection error before any test ran)
```

## Path to GO under unasync (~30 LOC source migration)

If REFAC-06 wanted to stay with unasync (NOT the current plan — defer to v1.3 libcst),
the path to GO is the ~30 LOC source migration on aio.py documented in 001a/FINDING.md
§"Ámbito Rule Config Draft" → "Phase 16 source-migration setup steps":

1. Move `_validate_max_retries` definition from client.py → aio.py (fixes hunks H4 + H5).
2. Pin import order in aio.py to `from <pkg> import _core, _transport` alphabetical
   (fixes H3).
3. Pin `_REQUEST_TIMEOUT` constant placement after `__all__` block (fixes H7).
4. Extend hand-written client.py with module-level `close()` delegator + WR-07
   ResourceWarning block (fixes H6 + H10).
5. Normalize docstring shape: aio.py becomes canonical source-of-truth; sync docstrings
   emitted via token-replacement (fixes H1, H8, H9).
6. Align per-line comment wording between aio.py and the canonical sync form (fixes H8
   residual).

After this migration, expected: 8/8 D-RIGOR-01 PASS on second iteration. **But:** v1.3
libcst is the strategic direction per D-NOGO-01 because libcst handles all of (1)-(6)
via AST transforms WITHOUT requiring source migration. The libcst spike's success
criterion is closing items 1, 4, 6 WITHOUT the migration.

## Per-Package Rule Config Drafts (informative, captured in SPIKE-005 DECISION.md)

These drafts were captured in DECISION.md before NO-GO signoff. They remain documented
for reference (in case unasync is revisited despite v1.3 libcst direction):

```python
# ámbito (canary)
unasync.Rule(
    fromdir=str(AMBITO_DIR) + "/",
    todir=str(AMBITO_DIR) + "/",
    additional_replacements={
        "AsyncClient": "Client",
        "AsyncRetryTransport": "RetryTransport",
        "_atransport": "_transport",
        "AmbitoFinancieroAsyncClient": "AmbitoFinancieroClient",
        "_default_async_client": "_default_client",
        "aclose": "close",
    },
)

# matriz (delta from ámbito)
unasync.Rule(
    fromdir=str(MATRIZ_DIR) + "/",
    todir=str(MATRIZ_DIR) + "/",
    additional_replacements={
        "AsyncClient": "Client",
        "AsyncRetryTransport": "RetryTransport",
        "_atransport": "_transport",
        "aclose": "close",
        "_aensure_token": "_ensure_token",
        "MatrizAsyncClient": "MatrizClient",
    },
)
unasync.unasync_files(
    fpath_list=[str(MATRIZ_DIR / "aio.py")],   # DENY-LIST enforced by file scope
    rules=[<above Rule>],
)
```

iol + higyrus inferred from ámbito per D-SCOPE-01; if ever re-attempted, the per-package
finalization would happen at Phase-16-equivalent.

## Linkage

- Full SPIKE-005 FINDING: `sources/001a-ambito-round-trip-FINDING.md`
- Full D-RIGOR-01 evidence: `sources/evidence-checklist.txt`
- Operator-signed NO-GO: `sources/DECISION.md`
- v1.3 libcst handoff scope: `references/libcst-v1.3-exploration-path.md`
