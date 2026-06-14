# FINDING: Ámbito Round-Trip

**Verdict:** FAIL — strict byte-identical round-trip not achieved; root cause is inherent source-of-truth asymmetry (Recipe 2 class 4 + extension), NOT unfixable codegen failure. Path to GO in Phase 16 is well-defined (source migration setup steps captured below).

**B8 identity:** PASS (alias preserved verbatim — see Run Transcript).

**Format-stable:** PASS (`uv run ruff format --check` exits 0 on already-formatted output — Pitfall 3 mitigation holds).

**Slopcheck Verification:** see `## Slopcheck Verification` section.

---

## Slopcheck Verification

```
$ slopcheck install unasync
slopcheck checking 1 package(s) on pypi before install...

  Installing: unasync
  Running: pip install unasync


  [OK] unasync (pypi)

==================================================
  scanned 1 packages
  1 OK
```

Note: slopcheck reports `[OK] unasync (pypi)` (T-12-01-SC supply-chain risk mitigated). The CLI raises a benign Python traceback at end-of-run because its embedded `pip install unasync` step fails inside the slopcheck venv (no pip installed there); this does NOT affect the legitimacy verdict — the legitimacy check ran and passed BEFORE the install attempt. `unasync 0.6.0` is then resolved transiently by `uv run --with unasync` from PyPI.

---

## Run Transcript

```
[step 1] copied <repo>/packages/ambito-financiero-client/src/ambito_financiero_client/aio.py -> <repo>/.planning/spikes/SPIKE-005-codegen-tool-choice/001a-ambito-round-trip/output/aio.py
[step 2] running unasync.unasync_files (replacements: 6 keys)
[step 3] renamed -> <repo>/.planning/spikes/SPIKE-005-codegen-tool-choice/001a-ambito-round-trip/output/client_generated.py
[step 4] running uv run ruff format ...
1 file left unchanged
[step 4b] running uv run ruff format --check (idempotency) ...
[step 4b] format-stable: True (exit 0)
1 file already formatted
[step 5] diff -u <v1.1 client.py> <client_generated.py> ...
[step 5] diff exit code: 1 (10 hunks)
[step 5] diff transcript written to: <repo>/.planning/spikes/SPIKE-005-codegen-tool-choice/001a-ambito-round-trip/diff_vs_v1.1_client.txt
[step 6] B8 identity check (loading generated as standalone module) ...
[step 6] B8 IDENTITY: PASS
[step 6]   mod._raise_for_response  id=106d2afc0
[step 6]   aio._raise_for_response  id=106d2afc0
[step 6]   _core.raise_for_response id=106d2afc0
[step 6b] removed <output>/__pycache__
SPIKE 001a VERDICT: FAIL diff=10 hunks b8=PASS format-stable=PASS
```

Script exit code: 1 (strict byte-identical contract not satisfied).

---

## Diff Analysis

The full diff transcript lives at `diff_vs_v1.1_client.txt` (10 hunks, ~250 LOC delta). Each hunk classified per Recipe 2 triage protocol (12-RESEARCH.md §"Recipe 2 — Ámbito Round-Trip Experiment Recipe"):

| # | Region (line range in `client_generated.py`) | Description | Recipe 2 Class | Triggers NO-GO? | Phase 16 Fix |
|---|----------------------------------------------|-------------|----------------|------------------|---------------|
| H1 | 1-21 module docstring | Hand-written async/sync docstrings differ (sincrónico/asincrónico labels, different `::` examples, B7 divergence note only in async) | **Inherent asymmetry** (class 4) — hand-written copy authored independently | NO | Source migration: pick one canonical docstring shape, parameterize via `additional_replacements` for the sync/async label tokens (e.g. `sincrónico ↔ asincrónico`) OR accept a per-package docstring template that lives in `aio.py` and gets token-rewritten cleanly |
| H2 | 27 `import warnings` | `warnings` only used by async `configure()` for the WR-07 ResourceWarning | **Inherent asymmetry** (class 4) | NO | Source migration: move WR-07 ResourceWarning into `aio.py` only (already the case), and accept that the generated sync `client.py` will not have the `warnings` import (a future ruff F401 unused-import would surface, but does not today because the import is absent — codegen elides it) |
| H3 | 31 import-block ordering `_transport, _core` (gen) vs `_core, _transport` (hand) | Single-line import order differs; ruff format does NOT reorder single-line imports | **Cosmetic** (class 1) — `ruff format` does not converge | NO | Phase 16: tighten `ruff format` config to enable `isort` single-line reorder OR pin `aio.py` source to use the same order as `client.py` |
| H4 | 32 `from ambito_financiero_client.client import _validate_max_retries` | Extra import line in generated; aio.py imports the helper FROM client.py | **Inherent asymmetry** (class 4 — direction-of-import) | NO | **Phase 16 setup step**: move the `_validate_max_retries` definition from `client.py` to `aio.py` so codegen emits it in `client.py` and `aio.py` imports it FROM client (reverse the current direction). 12-RESEARCH.md §Recipe 2 line 510 calls this out explicitly: "NOT a barrier to codegen — it's a one-time source migration that Phase 16 performs" |
| H5 | 41 missing `_validate_max_retries` definition + docstring (25 LOC) | Defined in hand-written sync, absent in generated | **Inherent asymmetry** (class 4) — same as H4 root cause | NO | Same as H4 — single migration eliminates H4 + H5 |
| H6 | 44-47 `__all__` includes `"close"` (gen) vs no `"close"` (hand) | `aclose → close` token replacement applied to `__all__` entry | **Semantic-consistent extension** (class between 2 and 4) — codegen extends sync surface | NO | Phase 16: either (a) add a module-level `close()` delegator to hand-written `client.py` to match (semantic equivalent for symmetry), OR (b) remove `aclose` from `aio.py` `__all__` (but then async loses a public symbol). Recommended: (a) — the sync surface is intentionally minimalist today but adding the delegator is non-breaking |
| H7 | 49 `_REQUEST_TIMEOUT = 30.0` placement | Position differs (hand-written places constant before validate fn; generated places after `__all__`) | **Cosmetic** (class 1) — positional reordering | NO | Phase 16: codify the canonical layout in `aio.py` (move `_REQUEST_TIMEOUT` after `__all__` block, same as generated, OR pin both to identical order) |
| H8 | 75 missing comment `# max_retries=0 means no retries (bypass retry loop entirely per D-19).` + 73 mirror-comment label shift `# WR-06: validate max_retries early (mirror sync Client).` | Per-line comment differences between hand-written copies | **Inherent asymmetry** (class 4) — hand-written comments | NO | Phase 16: align comment wording in `aio.py` to be the canonical text after token substitution |
| H9 | 121-134, 144-149, 159-164 docstring + repr asymmetries (`AmbitoFinancieroAsyncClient` ↔ `AmbitoFinancieroClient` — these ARE in additional_replacements, but multi-line comments diverge), `(async)` suffix on `get_dollar_banco_nacion` docstring | Hand-written `(async)` doc tags + multi-line indentation of TypeError messages | **Inherent asymmetry** (class 4) — hand-written wording | NO | Phase 16: align doc tags via token replacement (`(async)` → `` or via shared docstring source) |
| H10 | 178-204 `configure()` body: WR-07 ResourceWarning block (~25 LOC) | Only async `configure()` warns on dropping live client; sync `configure()` does not | **Inherent asymmetry** (class 4) — D-19/D-23 design choice for async only | NO | Phase 16: either (a) extend sync `configure()` to also warn on dropping live `httpx.Client` (semantic equivalent for symmetry), OR (b) accept the asymmetry as a design choice and let codegen elide it. Recommended: (a) for cleaner round-trip |

**Aggregate classification:**

- **7 hunks** classify as Recipe 2 class 4 — **inherent asymmetry**. Per Recipe 2 line 508: "NOT a unasync failure — it's an inherent asymmetry of the source-of-truth model. ... DOCUMENTS this as a known Phase 16 setup step but does NOT regard it as a NO-GO trigger."
- **2 hunks** classify as Recipe 2 class 1 — **cosmetic** (ruff format does not converge on single-line import order or constant placement). Phase 16 fixable via tighter ruff/isort config OR source-pin.
- **1 hunk** (H6) classifies as **semantic-consistent extension**: codegen extends sync surface with a module-level delegator. Fixable in Phase 16 via either source addition (preferred) or async `__all__` reduction.

**Zero hunks** classify as Recipe 2 class 3 — "Semantic NOT fixable via additional_replacements (multi-token, structural)". That class is the only one that triggers NO-GO per Recipe 2 line 507.

**Strict-contract verdict:** FAIL (diff non-empty against the hand-written file).
**Recipe-2-classified verdict:** PASS-WITH-PHASE-16-SETUP (no NO-GO trigger).

The discrepancy is informative for the spike: it tells Phase 16 that unasync CAN produce a byte-identical roundtrip IF the source-of-truth side (`aio.py`) is migrated to match the codegen-friendly shape (1 source migration: `_validate_max_retries` direction; 1 doc shape pin; 1 ruff config tighten). Plan 03's DECISION.md will need to integrate this finding when computing the aggregate GO/NO-GO.

---

## B8 Identity Check

```
[step 6] B8 IDENTITY: PASS
[step 6]   mod._raise_for_response  id=106d2afc0
[step 6]   aio._raise_for_response  id=106d2afc0
[step 6]   _core.raise_for_response id=106d2afc0
```

Assertion evaluated in `experiment.py` Step 6:

```python
assert (
    mod._raise_for_response          # generated client.py module-level alias
    is aio._raise_for_response       # v1.1 hand-written aio.py module-level alias
    is core.raise_for_response       # _core.py canonical function
)
```

All three identifiers resolve to the SAME object id (`0x106d2afc0`). The unasync tokenizer preserved the assignment `_raise_for_response = _core.raise_for_response` verbatim because:

1. The aio.py source line is five Python tokens (`_raise_for_response`, `=`, `_core`, `.`, `raise_for_response`).
2. None of the tokens match `additional_replacements` keys.
3. There is no `async`/`await` keyword adjacent.

This empirically confirms the prediction in 12-RESEARCH.md §"Recipe 3 — B8 Identity Preservation Test Recipe" line 559: "unasync emits the line verbatim and the identity invariant SHOULD hold trivially." It does.

The failure mode this test catches — emitting a thunk wrapper `def _raise_for_response(resp): return _core.raise_for_response(resp)` instead of an alias — would have produced `is` False. The test would have detected the regression.

**B8 identity satisfies D-RIGOR-01 item 2 / SC#2.**

---

## Ámbito Rule Config Draft

The exact `unasync.Rule(...)` block that produced the (B8-PASS, format-stable, Recipe-2-classified-clean) output:

```python
unasync.Rule(
    fromdir=<work_dir> + "/",          # spike-local sandbox; in Phase 16 = aio.py source dir
    todir=<work_dir> + "/",            # same dir (in-place tokenization); rename afterwards
    additional_replacements={
        # Core async→sync class + transport renames.
        "AsyncClient": "Client",
        "AsyncRetryTransport": "RetryTransport",
        "_atransport": "_transport",
        "AmbitoFinancieroAsyncClient": "AmbitoFinancieroClient",
        "_default_async_client": "_default_client",
        "aclose": "close",
    },
)
```

**Auto-applied by unasync 0.6.0 default rewrites (no config needed):**

- `__aenter__` → `__enter__`, `__aexit__` → `__exit__`, `__aiter__` → `__iter__`, `__anext__` → `__next__`
- `asynccontextmanager` → `contextmanager`
- `AsyncIterable` → `Iterable`, `AsyncIterator` → `Iterator`, `AsyncGenerator` → `Generator`, `StopAsyncIteration` → `StopIteration`
- Strips `async`/`await` keywords

**Phase 16 source-migration setup steps required for byte-identical roundtrip:**

1. **Move `_validate_max_retries` definition from `client.py` to `aio.py`** so codegen emits the definition in `client.py` and `aio.py` imports it FROM `client.py` (reverses direction). Fixes hunks H4 + H5.
2. **Pin canonical import order** in `aio.py`: `from ambito_financiero_client import _core, _transport` (alphabetical) so generated matches hand-written. Fixes H3.
3. **Pin `_REQUEST_TIMEOUT` constant placement** after `__all__` block (matches generated default). Fixes H7.
4. **Decide H6/H10:** either (a) extend `client.py` with module-level `close()` delegator + WR-07 ResourceWarning block (preferred, symmetric), OR (b) elide the async-only fields. Recommended: (a).
5. **Doc shape normalization**: replace per-hand-written docstring text with codegen-emitted source-of-truth from `aio.py` (the async docstrings become the canonical, sync gets tokenized variant). Fixes H1, H8, H9.
6. **Comment alignment in `aio.py`**: bring the per-line comments up to match the canonical sync wording (e.g., add `# max_retries=0 means no retries...` comment in `aio.py`). Fixes H8.

**Total Phase 16 setup steps:** 6 source migrations on `aio.py` (~30 LOC of edits) → expected: byte-identical roundtrip on second iteration.

---

## Open Questions for Operator

1. **H6 / H10 — extend sync `client.py` with WR-07 + module-level `close()` delegator?** Recommended for symmetry; current hand-written sync intentionally omits them (design choice from Phase 7/8). Operator confirmation needed before Phase 16 commits the source migration.
2. **Docstring asymmetry strategy (H1, H8, H9)** — accept that source-of-truth = `aio.py` (async docstrings authored canonical, sync gets tokenized via additional_replacements) OR build a Jinja2-style shared docstring header? `additional_replacements` for natural-language docstring tokens (sincrónico↔asincrónico) is mechanically possible but the maintenance burden of "1 doc, 2 outputs" via token rewrite needs a Phase 16 decision.
3. **Phase 16 acceptance of `additional_replacements` table size (currently 6 entries)** — Pitfall 8 warns about table growth >10 entries. Ámbito stays comfortably small even after migrating; the other 3 packages (iol, higyrus, matriz) need their own per-package Rule, and total cross-package replacement count will likely exceed 10. Phase 16 needs a per-package table strategy decision (recommended: one Rule per package, not a shared table).
4. **Plan 02 Wave 2 carryover (001b @generated marker test)** — should run against the current `output/client_generated.py` (which has the diff hunks documented above) since the marker compatibility test only cares about `from __future__ import annotations` ordering, not byte-identity. No follow-up question, just a confirmation that the carryover is well-defined.

---

## Conclusion

The canary (001a) returns FAIL on the strict byte-identical contract (10 hunks remain after `ruff format`), but every hunk is classified per Recipe 2 as either **inherent-asymmetry**, **cosmetic** (`ruff format` does not converge on single-line import order / constant placement), or **semantic-consistent extension**. **No hunk classifies as "semantic NOT fixable via additional_replacements" — i.e., zero NO-GO triggers per Recipe 2 line 507.**

**B8 identity passes (`is` assertion confirmed at id 0x106d2afc0).** **Format-stable passes.** The unasync 0.6.0 invocation pattern itself is sound; the gap to GO is a well-bounded Phase 16 source-migration setup (~30 LOC of edits to `aio.py`).

Plan 03 Task 12-03-01 will integrate this finding into the 8-item D-RIGOR-01 evidence checklist:

- D-RIGOR-01 item 1 (byte-identical round-trip): **FAIL** as captured here (10 hunks).
- D-RIGOR-01 item 2 (B8 identity): **PASS**.
- D-RIGOR-01 item 3 (`ruff format --check` format-stable): **PASS**.

The aggregate verdict (GO vs NO-GO) is computed in Task 12-03-01 from the 8-item checklist + matriz audit (SC#3) + timebox status; it is NOT computed inline here. Plan 03 needs to weigh item 1 FAIL against the well-bounded Phase 16 source-migration path. The spike's job is to surface the data, not to pre-judge the operator signoff.
