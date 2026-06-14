---
name: spike-findings-codegen-market-libs
description: NO-GO close-out for SPIKE-005 codegen tool choice (Phase 12, 2026-06-14). Records what was learned about unasync 0.6.0 in market-libs context (B8 identity preserved, marker design PEP-compliant, matriz audit clean, deny-list intactness via fpath_list scope) plus the failure modes that v1.3 libcst spike must address (3 of 8 D-RIGOR-01 items FAIL — items 1 byte-identical, 4 ruff check, 6 ámbito pytest — all tracing to source-shape asymmetry). Auto-loaded when v1.3 libcst spike or any future codegen revisit is planned.
---

<context>
## Project: market-libs — Codegen Tool Choice (Phase 12, NO-GO)

market-libs is a Python monorepo of 5 client libraries for Argentine financial services
(iol-client, higyrus-client, matriz-client, ambito-financiero-client, wallets-client).
Each client has a dual sync/async surface: `client.py` (sync) and `aio.py` (async). The
two files are 80%+ structurally identical and accumulated as v1.0/v1.1 tech debt — the
single-source codegen pattern (REFAC-06) was scheduled to close the duplication.

**Phase 12 (SPIKE-005)** evaluated `unasync >=0.6.0,<0.7` as the codegen tool — token
replacement that strips `async`/`await` keywords and substitutes async-specific token
patterns (`AsyncClient → Client`, `aclose → close`, etc.). Decision binary: GO (Phase 16
proceeds with per-package Rule configs) vs NO-GO (defer REFAC-06 to v1.3 with libcst
exploration per locked decision D-NOGO-01).

**Outcome: NO-GO signed 2026-06-14 by sebadlf under strict D-RIGOR-01 reading.**
3 of 8 evidence items FAIL (items 1, 4, 6); all 3 trace to a single source-shape root
cause: `aio.py` was authored sync-first in v1.1 Phase 7 (sync was primary, async
mirrored), but unasync codegen direction is async-first (`aio.py` is canonical source,
`client.py` is generated). The 10 diff hunks in the ámbito canary round-trip classify per
Recipe-2 as 7 inherent-asymmetry + 2 cosmetic + 1 semantic-consistent-extension —
**zero class-3 (unfixable) hunks**.

Phase 12 spike sessions: 2026-06-14 (Plans 01 + 02 + 03 wrapped; ~19 min cumulative
wall-clock, well under the D-SCOPE-03 24h cap).
</context>

<requirements>
## Requirements (non-negotiable carry-forward to v1.3 libcst spike)

These constraints emerged from SPIKE-005 evaluation and MUST be honored in the v1.3
libcst spike + any future REFAC-06 implementation:

### Validation gate (D-RIGOR-01, 8 items inherited)

The v1.3 spike inherits the 8-item D-RIGOR-01 gate verbatim. SPIKE-005 confirmed:

- **5 items PASS unconditionally** under unasync (so libcst trivially inherits):
  - Item 2 (B8 identity preserved on generated)
  - Item 3 (`uv run ruff format --check` clean)
  - Item 5 (`uv run mypy --strict` clean)
  - Item 7 (`uv run lint-imports` 4 contracts intact)
  - Item 8 (`@generated` marker × `from __future__ import annotations` compatibility)

- **3 items FAIL under unasync** (the gap libcst must close):
  - Item 1 (byte-identical round-trip ámbito) — 10 hunks, source-shape asymmetry
  - Item 4 (`uv run ruff check` clean) — single-line import-order I001 inherited from
    aio.py source order; ruff format does NOT converge
  - Item 6 (ámbito mocked suite green vs generated) — circular import at collection because
    aio.py imports `_validate_max_retries` from client.py; codegen emits a self-import

### Matriz architectural deny-list (LOCKED — do NOT renegotiate)

These 4 files NEVER undergo codegen, full stop. They contain 3-way concurrency
primitives that token replacement OR AST transform cannot mechanically rewrite:

- `packages/matriz-client/src/matriz_client/_token_store.py` — `threading.Lock` +
  per-loop `asyncio.Lock` + `asyncio.to_thread` (3-way TokenStore for sync REST +
  async REST + ws_client daemon thread).
- `packages/matriz-client/src/matriz_client/_refresh_policy.py` — pure sync retry +
  backoff + fail-cache, runs inside `asyncio.to_thread` from the async path.
- `packages/matriz-client/src/matriz_client/_refresh.py` — sync `httpx.Client`-based
  MatrizRefresh adapter; async path delegates via TokenStore.
- `packages/matriz-client/src/matriz_client/ws_client.py` — `websocket-client` daemon
  thread; no `asyncio` primitives in module body; always sync from Python's perspective.

The unasync 0.6.0 `fpath_list` scope (001d/FINDING.md) is structurally sufficient: by
NOT passing these 4 files to `unasync_files()`, the tool cannot mutate them. v1.3 libcst
must adopt the equivalent per-CSTTransformer invocation scope.

### B8 identity invariant (Pitfall 4 mitigation)

```python
assert (
    client_module._raise_for_response
    is aio._raise_for_response
    is _core.raise_for_response
)
```

unasync 0.6.0's tokenizer preserves the alias line `_raise_for_response = _core.raise_for_response`
verbatim because (a) it's 5 plain Python tokens, (b) none match the `additional_replacements`
keys, (c) no `async`/`await` keyword adjacent. The failure mode this catches is codegen
emitting a thunk wrapper `def _raise_for_response(resp): return _core.raise_for_response(resp)`.
v1.3 libcst's CSTTransformer must equally preserve this assignment node verbatim.

### `@generated` marker × `from __future__ import annotations` compatibility

Marker syntax (PEP 263 / PEP 236 compliant; confirmed `ast.parse` clean):

```python
# @generated by unasync from aio.py — DO NOT EDIT BY HAND.
# To modify, edit aio.py and run `make codegen` (Phase 16 setup).

"""<module docstring>"""

from __future__ import annotations
```

Three-line marker block (2 comment lines + 1 blank). Prepended via `str.__add__`
(Anti-Pitfall 6 — NEVER `str.replace`). All 4 verification commands (ruff check,
ruff format --check, mypy --strict, ast.parse) are MARKER-NEUTRAL (exit codes IDENTICAL
between unmarked baseline and marked file; only diff is line numbers shifted +3). v1.3
libcst spike inherits this marker design unchanged; for libcst the marker can be a
leading `cst.SimpleStatementLine` with `cst.Comment(...)` children.

### Matriz `aio.py` construct audit (D-SCOPE-02 merge gate)

Matriz `aio.py` 852 LOC enumerated 109 async-only constructs:

- 106 rows `manual-sync-proof` (every async construct has documented unasync default
  replacement: `async def → def`, `async with → with`, etc.).
- 3 rows `comment-only` (docstring mentions of `asyncio.*` at lines 42, 235, 267 —
  preserved verbatim by tokenizer).
- 0 rows REVIEW / TBD / DENY-LIST-VIOLATION.

**Critical structural observation:** matriz `aio.py` has ZERO bare `asyncio.<attr>`
references in code body — all are inside docstrings. The async primitives are entirely
encapsulated inside `_token_store.py` (deny-listed). This is a stronger guarantee than
fpath_list scope alone. v1.3 inherits the audit script + result; the merge gate sentinel
`**MERGE GATE PASS:** zero unresolved rows.` is reused as-is.

### What v1.3 libcst spike must address (the unasync gap)

The 3 FAIL items above all trace to ONE source-of-truth shape problem:

1. **Import direction asymmetry** (items 1 H4/H5, 6): `aio.py` imports
   `_validate_max_retries` from `client.py`. Token replacement can't reverse this. libcst
   CAN — AST analysis identifies the import + the corresponding definition; transformer
   moves the definition to the canonical async-first location and rewrites import.
2. **Single-line import order asymmetry** (item 4 H3): `aio.py` has
   `from <pkg> import _transport, _core` (non-alphabetical). ruff format does NOT
   converge on single-line import order. libcst CAN normalize via an `ImportNormalizer`
   transformer.
3. **Docstring/comment asymmetry** (items 1 H1/H8/H9/H10): hand-written sync docstrings
   diverge from async (sincrónico ↔ asincrónico labels, `(async)` doc tags, WR-07
   ResourceWarning block only in async configure()). Token replacement can't reach
   substrings inside docstrings. libcst CAN — docstring is a `cst.Constant(value: str)`
   node; transformer rewrites its value.

**If libcst v1.3 spike ALSO fails on the same 3 items, the team must reconsider whether
codegen single-source is the right architectural pattern at all.** That negative result
would shelve REFAC-06 permanently and accept the duplicate client.py/aio.py shells as
a structural feature.
</requirements>

<findings_index>
## Feature Areas

| Area | Reference | Key Finding |
|------|-----------|-------------|
| unasync round-trip on ámbito canary | references/unasync-failure-mode.md (synth. from 001a/FINDING.md) | 10 diff hunks — 7 inherent-asymmetry + 2 cosmetic + 1 semantic-consistent-extension; 0 NO-GO triggers (class-3). Path to PASS is ~30 LOC source migration on aio.py. unasync's tokenize-and-replace approach is too low-level for source-shape asymmetries. |
| @generated marker × `from __future__ import annotations` | references/codegen-pitfalls.md §marker | PEP 263 + PEP 236 compliant; marker-neutral on all 4 verification commands. Inherited unchanged by v1.3 libcst spike. |
| matriz `aio.py` construct audit (852 LOC, 109 constructs) | references/matriz-construct-audit.md (synth. from 001c/FINDING.md) | 109 rows enumerated, 0 unresolved. Critically: matriz aio.py has ZERO bare `asyncio.<attr>` in code body — async primitives entirely encapsulated in `_token_store.py` (deny-listed). Structural deny-list self-enforcement is stronger than fpath_list scope alone. |
| matriz deny-list intactness via fpath_list scope | references/codegen-pitfalls.md §deny-list | unasync 0.6.0 has NO `exclude=` parameter; deny-list is achieved by NOT listing the deny-listed files in `fpath_list`. 4-file sha256 byte-identical pre/post; transformed file (aio.py) sha256-different pre/post. v1.3 libcst adopts equivalent per-CSTTransformer invocation scope. |
| libcst v1.3 exploration scope | references/libcst-v1.3-exploration-path.md | AST-level CSTTransformer pattern: preserves whitespace + comments natively, can detect-and-rewrite multi-token patterns (import direction reversal, docstring localization, single-line import-order normalization). Pending todo: `.planning/todos/pending/spike-codegen-libcst-v1.3.md`. |

## Source Files

Spike sub-experiment FINDINGs preserved in `sources/` for complete reference:

- `sources/001a-ambito-round-trip-FINDING.md` — canary FAIL (strict byte-identical),
  B8 PASS, format-stable PASS; 10 hunks classified per Recipe 2.
- `sources/001b-ambito-marker-future-compat-FINDING.md` — marker PASS (marker-neutral
  on 4 commands).
- `sources/001c-matriz-construct-audit-FINDING.md` — 109 rows, 0 unresolved; D-SCOPE-02
  merge gate PASS.
- `sources/001d-matriz-deny-list-config-FINDING.md` — 4/4 deny-listed files sha256
  byte-identical pre/post; fpath_list scope sufficient.
- `sources/evidence-checklist.txt` — D-RIGOR-01 8-item re-run with PASS/FAIL per item.
- `sources/DECISION.md` — operator-signed NO-GO + per-package Rule config drafts
  (informative; libcst's analogue is per-package CSTTransformer).
</findings_index>

<integration_blueprint>
## v1.3 libcst Spike Integration Blueprint

The v1.3 spike (captured in `.planning/todos/pending/spike-codegen-libcst-v1.3.md`)
should follow this structure, parallel to SPIKE-005:

```
.planning/spikes/SPIKE-006-libcst-codegen-tool-choice/    # new spike, v1.3
├── README.md                                              # frontmatter spike: 006, verdict: TBD
├── DECISION.md                                            # operator-signed GO|NO-GO
├── NO-GO.md OR GO-checklist                               # close-out branch
├── 002a-ambito-round-trip-libcst/                        # canary, parallel to SPIKE-005 001a
│   ├── README.md
│   ├── experiment.py                                      # libcst CSTTransformer subclass
│   ├── transformers/                                      # per-asymmetry transformer
│   │   ├── import_direction_normalizer.py                # closes SPIKE-005 H4/H5
│   │   ├── single_line_import_order.py                   # closes SPIKE-005 H3
│   │   └── docstring_localizer.py                         # closes SPIKE-005 H1/H8/H9
│   ├── output/client_generated.py
│   ├── diff_vs_v1.1_client.txt
│   └── FINDING.md
└── (002b/c/d parallel sub-experiments)
```

### Per-package CSTTransformer pattern (v1.3 target)

```python
# Per-package transformer subclass — pure CSTNode → CSTNode function.
import libcst as cst

class AmbitoAsyncToSync(cst.CSTTransformer):
    """Transforms ámbito aio.py module into sync client.py module."""

    def leave_FunctionDef(self, orig: cst.FunctionDef, upd: cst.FunctionDef) -> cst.BaseStatement:
        # Strip async; rename specific identifiers; transform docstring.
        ...

    def leave_ImportFrom(self, orig: cst.ImportFrom, upd: cst.ImportFrom) -> cst.BaseSmallStatement:
        # Normalize alphabetical single-line import order (SPIKE-005 H3 closure).
        ...

    def leave_SimpleString(self, orig: cst.SimpleString, upd: cst.SimpleString) -> cst.BaseExpression:
        # Docstring localizer: sincrónico ↔ asincrónico (SPIKE-005 H1/H8/H9 closure).
        ...
```

### B8 identity preservation (mandatory)

Every CSTTransformer subclass MUST emit the assignment line verbatim:

```python
_raise_for_response = _core.raise_for_response
```

Regression test (identical to SPIKE-005 item 2):

```python
spec = importlib.util.spec_from_file_location("generated", str(generated))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
assert (
    mod._raise_for_response
    is aio._raise_for_response
    is _core.raise_for_response
), "B8 identity FAILED: codegen emitted a thunk wrapper instead of alias assignment."
```

### Matriz audit + deny-list (inherited from SPIKE-005)

- Re-run the SPIKE-005 001c audit script against the current matriz `aio.py`. If
  result is still 109 rows / 0 unresolved, no v1.3 work needed on this axis. Note that
  the merge gate is structural (deterministic AST walk), so libcst inherits it.
- Re-run the SPIKE-005 001d sha256 check with libcst's equivalent of `fpath_list`
  scope (per-CSTTransformer invocation against the sandbox aio.py file only). 4/4
  byte-identical pre/post is the gate.

### Decision rigor (D-RIGOR-02 for v1.3 spike)

Inherit SPIKE-005's 8-item gate verbatim + add 2 libcst-specific items:

- Item 9: CSTTransformer pattern correctness (pure CSTNode → CSTNode, no side effects).
- Item 10: matriz audit + deny-list under libcst (parallel to 001c + 001d).

### Production integration (if v1.3 GO)

If libcst v1.3 spike returns GO, the Phase 16-equivalent (v1.3 phase) inherits:

- Marker syntax: identical to SPIKE-005 (PEP 263/PEP 236).
- Pre-commit hook: `head -1 packages/<pkg>/src/<pkg>/client.py | grep -q '^# @generated by libcst'`
  (or unasync, name-agnostic).
- Makefile `codegen` + `codegen-check` targets.
- CI `lint-codegen` job.
- `pyproject.toml` `[dependency-groups] dev`: `libcst >=1.8.0,<2`.
</integration_blueprint>

<metadata>
## Processed Spikes

- 001a-ambito-round-trip (FAIL — strict byte-identical; B8 PASS; format-stable PASS;
  10 hunks classified per Recipe 2; ZERO class-3 NO-GO triggers — informative for v1.3)
- 001b-ambito-marker-future-compat (PASS — marker-neutral on 4 commands;
  inherited by v1.3 unchanged)
- 001c-matriz-construct-audit (PASS — 109 rows, 0 unresolved; D-SCOPE-02 merge gate;
  inherited by v1.3 unchanged)
- 001d-matriz-deny-list-config (PASS — 4/4 byte-identical via fpath_list scope;
  v1.3 adapts to libcst MetadataWrapper)

## Phase 12 Outcome

- **Decision:** NO-GO (signed 2026-06-14 by sebadlf, strict D-RIGOR-01 reading)
- **Items FAIL:** 3 of 8 (items 1, 4, 6 — all source-shape asymmetry)
- **Items PASS:** 5 of 8 (items 2, 3, 5, 7, 8)
- **Matriz audit unresolved:** 0 (D-SCOPE-02 merge gate satisfied automatically)
- **Timebox:** WITHIN-CAP (~19 min cumulative wall-clock, 24h cap)
- **Recipe-2 NO-GO triggers (class 3):** 0
- **Phase 16 status:** DROPPED from v1.2 schedule
- **Phase 17 status:** UNBLOCKED — runs immediately after Phases 14 + 15
- **REFAC-06 disposition:** deferred to v1.3 with libcst spike (D-NOGO-01)
- **v1.2 milestone scope:** 4 of 5 requirements ship (REFAC-05, SEC-01, ERG-01, LIVE-03)

## Related Artifacts

- SPIKE-005 spike directory: `.planning/spikes/SPIKE-005-codegen-tool-choice/`
- NO-GO close-out: `.planning/spikes/SPIKE-005-codegen-tool-choice/NO-GO.md`
- v1.3 libcst pending todo: `.planning/todos/pending/spike-codegen-libcst-v1.3.md`
- Phase 12 SUMMARY: `.planning/phases/12-codegen-spike/12-SUMMARY.md`
- Plan 03 SUMMARY: `.planning/phases/12-codegen-spike/12-03-SUMMARY.md`
- v1.2 REQUIREMENTS REFAC-06 deferred entry: `.planning/REQUIREMENTS.md` §"Future Requirements (Defer to v1.3+)"
- v1.2 ROADMAP Phase 16 DROPPED entry: `.planning/ROADMAP.md` §Phase 16
</metadata>
