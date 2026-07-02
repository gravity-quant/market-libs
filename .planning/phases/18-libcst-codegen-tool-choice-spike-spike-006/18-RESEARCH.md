# Phase 18: libcst Codegen Tool-Choice Spike (SPIKE-006) - Research

**Researched:** 2026-07-02
**Domain:** AST-level codegen (libcst CST codemods) for single-sourcing dual sync/async transport shells
**Confidence:** HIGH (repo evidence VERIFIED by grep/diff; libcst round-trip guarantee CITED from official docs; the item-1/item-9 outcome is the spike's empirical job and is flagged as an Open Question)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** 4 sub-experiments mirroring SPIKE-005's `001a`–`001d`, under `.planning/spikes/SPIKE-006-libcst-codegen-tool-choice/`:
  - `001a-ambito-round-trip` — the 3 GO-determining items (1 byte-identical, 4 `ruff check` import-order, 6 mocked-suite-green) via working libcst CSTTransformers on the **un-migrated** canary. **Item 9** (CSTTransformer purity, `CSTNode → CSTNode`, no global state/side-effects) folds in here as an assertion on the transformer classes.
  - `001b-ambito-marker-future-compat` — item 8 (`@generated` marker × `from __future__ import annotations`) re-verified with libcst's `cst.Comment` leading-comment insertion (marker design carries forward unchanged from SPIKE-005 001b).
  - `001c-matriz-construct-audit` — item 10a: **re-run the existing SPIKE-005 `001c/audit.py` unchanged** (pure stdlib-`ast`, tool-agnostic — copy verbatim). Merge gate sentinel `**MERGE GATE PASS:** zero unresolved rows.` reused as-is.
  - `001d-matriz-deny-list-config` — item 10b: 4-file sha256 byte-identity pre/post under `libcst.MetadataWrapper` **per-file scope** (libcst's equivalent of unasync's `fpath_list` scope).
- **D-02:** **Item 1 target is STRICT byte-identity to the EXISTING v1.1 hand-written `client.py`.** Any divergence in the generated sync output = **item-1 FAIL = NO-GO**. (Operator decision 2026-07-02.)
- **D-03:** The spike must author **more than the 3 headline transformers.** In addition to `ImportDirectionNormalizer` (moves `_validate_max_retries` def → client.py, rewrites the `aio.py:34` import), the import-order `ImportNormalizer`, and `DocstringLocalizer`, it must **SUPPRESS aio-only constructs during sync emission** so output matches hand-written `client.py` verbatim: no sync `close()` delegator (`aio.py:266-268 aclose()`), `configure()` must OMIT the WR-07 `ResourceWarning` block (`aio.py:224-242`), `_REQUEST_TIMEOUT` placement matches `client.py` (before `_validate`), not `aio.py` order. **All normalization happens at generation time. `aio.py` source is NOT edited.** If the spike cannot hit byte-identity via generation-time transformers alone, that is an honest FAIL, not a target to soften.
- **D-04:** **Aggregate verdict:** GO = all 10 `D-RIGOR-02` items genuine PASS **+** matriz audit 0-unresolved **+** within timebox. **Any item FAIL → NO-GO.** A Recipe-2-style informative hunk classification is allowed **alongside** the strict verdict, never replacing it. On NO-GO with items 1/4/6 failing again → REFAC-06 **permanently shelved**.
- **D-05:** libcst installed **ephemerally** via `uv run --with 'libcst>=1.8.0,<2' python <experiment>.py`. **NOT** added to root `[dependency-groups] dev` during the spike.
- **D-06:** Operator-signed **`DECISION.md`** (frontmatter with per-item verdict map for all 10 items) + **`evidence-checklist.txt`** (10-item PASS/FAIL transcripts) at SPIKE-006 root, mirroring SPIKE-005 verbatim.
- **D-07:** **24h D-SCOPE-03 hard timebox inherited**; over-cap → **AUTO-NO-GO.**
- **D-08:** On **GO** — handoff is the **3+ working CSTTransformer classes** authored in `001a`, canary-proven and asserted pure (item 9), promoted as "drafts" for the 4-package rollout (NOT required to be generalized across iol/higyrus/matriz within the spike). On **NO-GO** — REFAC-06 marked permanently shelved; duplicate shells become an accepted structural feature.
- **D-09:** The 4 matriz deny-list files re-verified **sha256-byte-identical pre/post** (item 10b). The spike CONFIRMS they are OUT of codegen scope; does not renegotiate.

### Claude's Discretion
- Exact file naming/layout inside `001a/transformers/`; whether item-9 purity is a runtime test assertion or a documented property.
- Whether `001b` is standalone or a check appended to `001a` (marker insertion is a single leading `cst.SimpleStatementLine`/module-header edit).

### Deferred Ideas (OUT OF SCOPE)
- **Production codegen integration** (CI `lint-codegen` job, pre-commit hook, `make codegen` target, pinned `libcst` dev-dep) — Phase 19 GO-branch only, DROPPED if NO-GO.
- **4-package generalization** of the transformers (iol/higyrus/matriz) — Phase 19; the spike proves only the ámbito canary + infers the rest.
- Re-running unasync experiments (already NO-GO per SPIKE-005); codegen for `_core.py` or the 4 matriz deny-list files.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CODEGEN-01 | Evaluate `libcst >=1.8.0,<2` as AST-level codegen tool for single-source sync/async against a `D-RIGOR-02` 10-item gate; sign a binary GO/NO-GO. Vehicle: SPIKE-006. Canary = ámbito `aio.py` in **v1.2-head** (NOT migrated). Must close the 3 items unasync couldn't (1 byte-identical, 4 import-order, 6 mocked-suite/circular-import). Output: signed decision + per-package CSTTransformer drafts. If 1/4/6 FAIL again → REFAC-06 permanently shelved. | This research supplies: (a) the libcst round-trip guarantee (§Standard Stack, §Architecture Patterns) confirming the AST premise; (b) the full **verified** byte-level asymmetry catalog the transformers must close (§Canary Asymmetry Catalog); (c) the **content-absent-from-source** tension that most likely determines item-1/item-6 outcome (§Open Questions Q1); (d) the reusable SPIKE-005 harness (§Don't Hand-Roll); (e) the exact 10-item verification commands (§Validation Architecture). |
</phase_requirements>

## Summary

libcst is Meta/Instagram's Concrete Syntax Tree library. Its defining property — **lossless round-trip**: `cst.parse_module(src).code == src` holds byte-for-byte, preserving every comment, whitespace run, trailing-comment, rST `::` docstring block, and `# ---...---` divider **without any `ruff format` post-pass** — is CITED from the official docs and is the v1.3 premise. That premise is mechanically sound: the parse→transform→`.code` pipeline changes only the nodes a transformer actually rewrites and re-emits untouched trivia verbatim. This is a genuine capability gain over unasync's tokenizer (SPIKE-005), which required a `ruff format` post-pass and could not reach substrings inside docstrings or reverse an import direction.

However, the mechanical round-trip guarantee is **not** the gate. The gate (D-02, STRICT) is byte-identity of the *generated sync output* to the *existing hand-written `client.py`*, with `aio.py` as the sole source and **no source migration** (D-03). The central finding of this research is that two regions of the target `client.py` contain **content that does not exist anywhere in the `aio.py` source**: (1) the 22-line `_validate_max_retries` definition (`client.py:41-62`) — `aio.py` only *imports* it (`aio.py:34`); and (2) the `from dotenv import load_dotenv` import + module-level `load_dotenv()` call (`client.py:25,30`) — absent from `aio.py` by design (D-19). libcst can *move* or *rewrite* nodes that exist; it cannot *synthesize* a 22-line function body or a dotenv bootstrap that the source module never contained. This is the same root cause (source-shape asymmetry) that produced the SPIKE-005 NO-GO, relocated into libcst's node model rather than eliminated by it. Compounding this, the hand-written `client.py` and `aio.py` diverge in **substantial hand-authored prose** (module docstring, the `with_options` method docstring is 43 lines in `client.py` vs 19 in `aio.py`, plus multiple per-method docstrings and per-line comments) that is not a mechanical `sincrónico↔asincrónico` swap.

**Primary recommendation:** Structure the spike honestly around the D-02 STRICT bar and instrument the two "content-absent-from-source" obstacles as the decisive item-1/item-6 evidence. The likely-honest outcome under the un-migrated constraint is a **second NO-GO for the same root cause** — which is an explicitly valid, guaranteed milestone deliverable (D-08). Do not soften the gate to manufacture a GO. Use libcst 1.8.x (latest 1.8.6) via ephemeral `uv run --with 'libcst>=1.8.0,<2'`; reuse the SPIKE-005 `001c/audit.py` verbatim and the `001d` sha256 harness adapted to per-module transform; author `001b` marker insertion via `Module.header` (never `str.replace`). Item 9 (transformer purity) is achievable **at the class level** by placing all cross-module state in an impure codegen *driver*, not in the `CSTTransformer` subclasses — see §Open Questions Q2.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Parse `aio.py` → CST | libcst codemod tool (offline) | — | Pure source-to-source; no runtime tier involved |
| Per-asymmetry node rewrite | `CSTTransformer` subclass (pure, per-module) | — | Item-9 purity bar applies here: `leave_*` is a function of its input node |
| Cross-module orchestration (def relocation, import rewrite in a *different* emitted file) | Codegen **driver** script (impure, stateful) | — | Multi-module state cannot live in a single pure transformer — see Q2 |
| `@generated` marker prepend | `Module.header` edit | — | Grammar-neutral leading comment; PEP 263/236 compliant |
| Deny-list scope enforcement | Per-file transform invocation (matriz `aio.py` only) | sha256 witness (item 10b) | The 4 deny-list files are never parsed → cannot be mutated |
| Verdict aggregation | `evidence-checklist.txt` + `DECISION.md` (operator sign-off) | — | Human gate; D-04 strict `any FAIL → NO-GO` |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `libcst` | `>=1.8.0,<2` (latest **1.8.6**, published 2025-11-03) `[CITED: pypi.org/project/libcst]` | Parse Python 3 source into a lossless CST, transform via `CSTTransformer`, re-emit via `Module.code` | Meta/Instagram's codemod engine; Rust-backed native parser; supports Python 3.0→3.14 syntax; the reference tool for formatting-preserving Python codemods (mypy ecosystem, Meta-scale refactors) `[CITED: pypi.org/project/libcst]` |
| Python stdlib `ast` | 3.12 | Reused **unchanged** for item 10a matriz construct audit (`001c/audit.py`) | Tool-agnostic, deterministic AST walk; already proven at SPIKE-005 (0 unresolved rows) `[VERIFIED: repo 001c/audit.py]` |

### Supporting (already in the workspace — verification harness, not new installs)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `ruff` | `>=0.7` (dev) | `ruff check` (item 4, incl. I001 import-order + ASYNC1xx) and `ruff format --check` (item 3) on generated output | Every item-3/4 verification `[VERIFIED: CLAUDE.md + evidence-checklist.txt]` |
| `mypy` | `>=1.13` strict (dev) | `mypy --strict` clean on generated `client.py` (item 5) | Item-5 verification `[VERIFIED: evidence-checklist.txt §item 5]` |
| `import-linter` (`lint-imports`) | dev | 4 `_core`-cannot-depend-on-transport contracts intact (item 7) | Item-7 verification; runs against `packages/`, not spike artifacts `[VERIFIED: evidence-checklist.txt §item 7]` |
| `pytest` + `pytest-httpx` + `pytest-asyncio` | `>=8.3` / `>=0.34` / `>=0.24` | Ámbito mocked suite green vs generated (item 6), via sandbox-copy | Item-6 verification `[VERIFIED: CLAUDE.md tech stack]` |
| `uv` | `0.9.0` | `uv run --with 'libcst>=1.8.0,<2'` ephemeral install (D-05); `uv run ruff/mypy/pytest/lint-imports` | Every command `[VERIFIED: CLAUDE.md + repo uv.lock]` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `libcst` | `unasync 0.6.0` | Already NO-GO (SPIKE-005); token-level, cannot reverse import direction or reach docstring substrings; out of scope to re-run (Out-of-Scope table) |
| `libcst` | stdlib `ast` + `ast.unparse` | `ast.unparse` **destroys** all comments/formatting → cannot round-trip; unusable for byte-identity |
| `libcst` | `bowler` (built on libcst) | Higher-level fluent wrapper; adds a dependency layer with no benefit for hand-authored per-package transformers; libcst directly is more precise |

**Installation (ephemeral only — D-05, do NOT add to `[dependency-groups] dev` during the spike):**
```bash
uv run --with 'libcst>=1.8.0,<2' python .planning/spikes/SPIKE-006-libcst-codegen-tool-choice/001a-ambito-round-trip/experiment.py
```

**Version verification (performed this session):** `pip index versions libcst` → `1.8.6` latest; available `1.8.0, 1.8.1, 1.8.2, 1.8.4, 1.8.5, 1.8.6` within the `>=1.8.0,<2` band. Rust-backed native parser, Python 3.9+ (project is 3.12/3.13 — compatible). `[VERIFIED: pip index + pypi.org]`

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| `libcst` | PyPI | mature (1.0.0 in 2023; 1.8.6 published 2025-11-03) | seam returned `null` (metadata gap) | `github.com/Instagram/LibCST` (Meta/Instagram; not surfaced by the seam) | **SUS** (seam) → assessed **legitimate** | **Keep — ephemeral install only (D-05). Planner adds one `checkpoint:human-verify` before the first ephemeral `uv run --with libcst`.** |

**Seam verdict detail:** `gsd-tools query package-legitimacy check --ecosystem pypi libcst` → `SUS`, reasons `["unknown-downloads", "no-repository"]`. Both reasons are **metadata-gap false positives**: the seam could not fetch PyPI download stats or the repository URL, not evidence of risk. libcst is the well-known Meta/Instagram Concrete Syntax Tree library (github.com/Instagram/LibCST), the canonical formatting-preserving codemod engine. No `postinstall`/lifecycle script (PyPI wheels, Rust-backed). Version band `>=1.8.0,<2` resolves to real, published releases (verified via `pip index versions`).

**Packages removed due to [SLOP] verdict:** none.
**Packages flagged as suspicious [SUS]:** `libcst` — legitimacy confirmed by name+repo provenance; because it is discovered from the requirement text and not from Context7/official-docs-in-session, it is tagged `[ASSUMED]` for provenance rigor and the planner should keep the single human-verify checkpoint before the first install. Its ephemeral-only install (D-05) already contains blast radius.

## Architecture Patterns

### System Architecture Diagram

```text
                 SPIKE-006 codegen driver (impure, stateful — owns cross-module state)
                 uv run --with 'libcst>=1.8.0,<2' python experiment.py
                          │
   ┌──────────────────────┼───────────────────────────────────────────────┐
   │ INPUT                │ TRANSFORM (pure CSTTransformer classes)        │ OUTPUT
   │                      ▼                                                 │
   │  aio.py (source) ─► cst.parse_module() ─► CST(module)                 │
   │  (sandbox copy,           │                    │                       │
   │   read-only)              │                    ▼                       │
   │                           │   ┌── ImportDirectionNormalizer ──┐        │
   │                           │   │   ImportNormalizer (I001)      │        │
   │                           │   │   DocstringLocalizer           │ (each  │
   │                           │   │   AsyncToSync (async/await,    │  pure, │
   │                           │   │     AsyncClient→Client, …)     │  per-  │
   │                           │   │   Suppressors (aclose(),       │  module│
   │                           │   │     WR-07 block, import warnings)       │
   │                           │   └───────────────┬────────────────┘        │
   │                           │                   ▼                         │
   │                           │        module.header += @generated marker   │
   │                           │                   │                         │
   │  ── CONTENT ABSENT FROM SOURCE (Q1) ──────────┤                         │
   │     _validate_max_retries def (22 LOC)  ◄── driver must SYNTHESIZE or   │
   │     load_dotenv import + call           ◄── DONATE from client.py       │
   │                                                ▼                         │
   │                                       updated_module.code ─► client_generated.py
   └──────────────────────────────────────────────┬────────────────────────┘
                                                   ▼
   VERIFY (10-item D-RIGOR-02 harness):  diff (item1) · ruff check (item4) ·
      pytest sandbox (item6) · B8 is-identity · ruff format --check · mypy --strict ·
      lint-imports · marker×future (item8) · purity assertion (item9) · matriz audit+sha256 (item10)

   DENY-LIST (never parsed): matriz _token_store.py · _refresh_policy.py · _refresh.py · ws_client.py
      └─ sha256 witnessed byte-identical pre/post (item 10b)
```

### Recommended Project Structure (parallel to SPIKE-005, per D-01)
```text
.planning/spikes/SPIKE-006-libcst-codegen-tool-choice/
├── README.md                              # frontmatter spike: 006, verdict: TBD
├── DECISION.md                            # operator-signed GO|NO-GO + 10-item verdict map (D-06)
├── evidence-checklist.txt                 # 10-item PASS/FAIL transcripts (D-06)
├── NO-GO.md  OR  GO-handoff.md            # close-out branch (D-08)
├── 001a-ambito-round-trip/
│   ├── README.md
│   ├── experiment.py                      # driver: parse → transform → emit → diff → B8 → purity
│   ├── transformers/                      # pure CSTTransformer subclasses (item-9 unit)
│   │   ├── async_to_sync.py               # async/await strip + renames (AsyncClient→Client, _atransport→_transport, …)
│   │   ├── import_normalizer.py           # single-line import-order → alphabetical (item 4 / H3)
│   │   ├── docstring_localizer.py         # SimpleString value rewrite (item 1 docstrings)
│   │   ├── import_direction_normalizer.py # rewrite/strip the `from …client import _validate_max_retries` (Q1)
│   │   └── suppressors.py                 # RemovalSentinel: aclose() delegator, WR-07 block, `import warnings`
│   ├── output/client_generated.py
│   ├── diff_vs_v1.1_client.txt            # REGENERATE against CURRENT client.py (drift — see Pitfall 1)
│   └── FINDING.md
├── 001b-ambito-marker-future-compat/      # item 8 (may fold into 001a per Discretion)
├── 001c-matriz-construct-audit/           # item 10a: COPY 001c/audit.py VERBATIM, re-run
└── 001d-matriz-deny-list-config/          # item 10b: sha256 pre/post, per-module transform scope
```

### Pattern 1: Lossless round-trip (the v1.3 premise)
**What:** libcst parses to a CST that retains all trivia; `.code` re-emits it byte-for-byte.
**When to use:** Foundational assumption of every transformer; verify it first as a smoke test.
**Example:**
```python
# Source: libcst tutorial — "Generating the source code from a cst tree is as easy as
# accessing the `code` attribute on `Module`." [CITED: libcst.readthedocs.io/en/latest/tutorial.html]
import libcst as cst
src = open("aio.py").read()
module = cst.parse_module(src)
assert module.code == src   # lossless round-trip — comments, whitespace, `::` blocks, `# ---` dividers preserved
```
**Confidence:** HIGH — this is libcst's headline invariant, CITED from docs and consistent with its Rust CST design. No `ruff format` post-pass is required for untouched regions.

### Pattern 2: Per-module pure transformer + impure driver (item-9 boundary)
**What:** Each `CSTTransformer` subclass is a pure function over ONE module's CST. Cross-module state (relocating a def from one emitted file to another, rewriting an import in a *different* module) lives in the codegen **driver**, not the transformer.
**When to use:** To satisfy item 9 ("CSTTransformer subclasses are pure `CSTNode → CSTNode`, no global state/side-effects") while still handling the import-direction asymmetry.
**Example:**
```python
# Source: libcst CSTTransformer API. [CITED: libcst.readthedocs.io/en/latest/tutorial.html]
import libcst as cst

class AsyncToSync(cst.CSTTransformer):
    """Pure: depends only on nodes it visits; holds no global/module state."""
    def leave_FunctionDef(self, orig: cst.FunctionDef, updated: cst.FunctionDef) -> cst.BaseStatement:
        if updated.asynchronous is not None:
            return updated.with_changes(asynchronous=None)   # strip `async`
        return updated

    def leave_Await(self, orig: cst.Await, updated: cst.Await) -> cst.BaseExpression:
        return updated.expression                            # unwrap `await x` → `x`

# Driver (impure — this is where cross-module orchestration is allowed; NOT a CSTTransformer):
module = cst.parse_module(aio_src)
module = module.visit(AsyncToSync())
# ... then the driver, not a transformer, decides how to handle _validate_max_retries (Q1)
generated = module.code
```

### Pattern 3: Docstring / SimpleString value rewrite (item 1 docstrings)
**What:** A module or method docstring is the first statement: `SimpleStatementLine → Expr → SimpleString` (or `ConcatenatedString` for implicit concatenation). Rewrite `.value` (the raw literal *including* quotes).
**Example:**
```python
# Source: libcst node model — docstring is a SimpleString expression. [CITED: libcst nodes reference]
class DocstringLocalizer(cst.CSTTransformer):
    def leave_SimpleString(self, orig: cst.SimpleString, updated: cst.SimpleString) -> cst.BaseExpression:
        v = updated.value
        if "asincrónico" in v:
            v = v.replace("asincrónico", "sincrónico")
        return updated.with_changes(value=v)
```
**Caveat (decisive — see Q1):** label swaps (`sincrónico↔asincrónico`, `AsyncClient↔Client`) are mechanical, but the hand-written `client.py` docstrings **diverge structurally** from `aio.py` (different examples, different phase notes, `with_options` docstring 43 vs 19 lines). Byte-identity for those regions requires the transformer to emit the *entire* target literal — i.e., hardcode the sync docstring per module — which is not "single-sourcing," it is embedding the target in the tool.

### Pattern 4: `@generated` marker via `Module.header` (item 8)
**What:** Prepend a leading comment block to `Module.header` (a sequence of `EmptyLine`), NOT via `str.replace` (Anti-Pitfall 6). Marker is grammar-neutral before `from __future__ import annotations` (PEP 263/236).
**Example:**
```python
# Source: libcst Module.header holds leading EmptyLine/Comment trivia. [CITED: libcst nodes reference]
marker = [
    cst.EmptyLine(comment=cst.Comment("# @generated by libcst from aio.py — DO NOT EDIT BY HAND.")),
    cst.EmptyLine(comment=cst.Comment("# To modify, edit aio.py and run `make codegen`.")),
    cst.EmptyLine(),
]
module = module.with_changes(header=[*marker, *module.header])
```
**Confidence:** MEDIUM (CITED docs structure; exact `header` semantics to be confirmed empirically in `001b` — but SPIKE-005 already proved the *marker text* is neutral on all 4 verification commands).

### Pattern 5: Suppression via `RemovalSentinel` / `FlattenSentinel` (D-03)
**What:** Return `cst.RemovalSentinel.REMOVE` from `leave_*` to delete a node (the module-level `aclose()` FunctionDef, `import warnings`); use `cst.FlattenSentinel([...])` to replace one node with zero-or-many within a sequence. Remove the WR-07 `If` block inside `configure()` by rewriting that FunctionDef's body.
**Example:**
```python
class Suppressors(cst.CSTTransformer):
    def leave_FunctionDef(self, orig, updated) -> cst.RemovalSentinel | cst.BaseStatement:
        if updated.name.value == "aclose":            # aio.py:266 module-level delegator
            return cst.RemovalSentinel.REMOVE          # hand-written client.py has no sync twin
        return updated
    def leave_Import(self, orig, updated) -> cst.RemovalSentinel | cst.BaseSmallStatement:
        if any(a.name.value == "warnings" for a in updated.names):
            return cst.RemovalSentinel.REMOVE          # only async configure() needs warnings
        return updated
```
**Confidence:** MEDIUM (CITED API names; `RemovalSentinel`/`FlattenSentinel` are documented libcst return types for `leave_*`).

### Anti-Patterns to Avoid
- **`str.replace` on generated source** (Anti-Pitfall 6): defeats the CST model, reintroduces the fragility unasync had. All edits go through nodes.
- **Putting cross-module state inside a `CSTTransformer`** (breaks item 9): the def-relocation orchestration belongs in the driver.
- **Reusing SPIKE-005's `diff_vs_v1.1_client.txt` as the item-1 baseline**: it is stale (v1.1, pre-`with_options`). Regenerate against the current `client.py` (Pitfall 1).
- **Assuming matriz audit still yields "109 rows"**: matriz `aio.py` grew 852→959 LOC since SPIKE-005 (Pitfall 2). The gate is "0 unresolved," not "109 rows."

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Lossless source round-trip | A custom tokenizer/formatter | `libcst.parse_module().code` | Byte-fidelity is libcst's core guarantee; hand-rolling reintroduces the unasync failure class |
| matriz async-construct audit (item 10a) | A new libcst-based walker | **Copy `.../SPIKE-005/001c/audit.py` VERBATIM** | Pure stdlib `ast`, tool-agnostic, no unasync reference; already proven (0 unresolved). CONTEXT D-01 mandates verbatim reuse. Just point `SOURCE` at current matriz `aio.py` (re-run yields current row count) |
| Deny-list sha256 harness (item 10b) | New sha256 logic | Adapt `.../SPIKE-005/001d/experiment.py` | Same `shutil.copytree` → sha256_before → transform → sha256_after skeleton; swap `unasync.unasync_files(fpath_list=[aio.py])` for a per-module libcst transform of the sandbox `aio.py` only (the 4 deny-list files are never parsed) |
| `@generated` marker design | New marker syntax | Reuse SPIKE-005 001b 3-line PEP-263/236 block, inserted via `Module.header` | Marker text already proven neutral on ruff check / ruff format --check / mypy --strict / ast.parse |
| B8 identity test (item 2) | New assertion harness | Reuse the `importlib.util` load + `is` triple-assert | `assert mod._raise_for_response is aio._raise_for_response is _core.raise_for_response` — catches thunk-wrapper regression |
| Sandbox for item 6 | Mutating `packages/` | `cp -r` package into `/tmp`, overwrite `client.py` with generated, `uv run pytest` | Anti-Pitfall 2: never mutate production source; spike writes ONLY under `.planning/spikes/SPIKE-006-.../` |

**Key insight:** ~60% of the spike harness (items 8, 10a, 10b, 2, and the sandbox recipe) is **inherited verbatim or near-verbatim** from SPIKE-005. The genuinely new work is the `001a` CSTTransformer suite and its item-1/4/6 evidence — that is where the spike's answer lives.

## Runtime State Inventory

> This is a spike (codegen tooling evaluation). It writes ONLY under `.planning/spikes/SPIKE-006-.../` and reads repo source; it mutates no production code, no datastore, no service, no OS registration. Included for completeness because the phase touches source-shape.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — spike produces markdown/py artifacts under the spike dir only. | None |
| Live service config | None — no service touched. | None |
| OS-registered state | None. | None |
| Secrets/env vars | None read or written. `.env` files untouched. (client.py's `load_dotenv()` is source content, not a spike action.) | None |
| Build artifacts | libcst installed **ephemerally** by `uv run --with` into a transient env; NOT persisted to `uv.lock` or `[dependency-groups] dev` (D-05). No egg-info/wheel changes. | None — verify `uv.lock` unchanged after spike (`git diff --exit-code uv.lock`) |

**The canonical question — "after the spike, what runtime state carries the change?":** Nothing. A NO-GO leaves zero footprint outside the spike dir + planning docs; a GO adds only CSTTransformer draft files under the spike dir (Phase 19 consumes them). Explicitly verified: no `packages/` mutation, no dependency committed.

## Common Pitfalls

### Pitfall 1: Stale SPIKE-005 baseline (canary drift)
**What goes wrong:** Reusing `SPIKE-005/001a/diff_vs_v1.1_client.txt` (10 hunks) as the item-1 target, or assuming the same 10 hunks.
**Why it happens:** SPIKE-005 ran against **v1.1** ámbito. The **v1.2-head** canary (the required target, per CODEGEN-01) added Phase 13 `with_options()`, the `_is_view` slot, and view lifecycle — VERIFIED this session: `__slots__` is now `("_is_view", "_max_retries", "_state")` in both files (SPIKE-005 diff shows `("_max_retries", "_state")`), and the `with_options` docstring is **43 lines in `client.py` vs 19 in `aio.py`** — a ~24-line hand-authored prose divergence absent from SPIKE-005's hunk list.
**How to avoid:** Regenerate the item-1 baseline by diffing the freshly generated output against the **current** `packages/ambito-financiero-client/.../client.py`. Expect MORE divergence than SPIKE-005's 10 hunks, concentrated in `with_options` docstrings.
**Warning signs:** A hunk count of exactly 10, or a diff that omits the `with_options` region.

### Pitfall 2: matriz audit LOC/row drift
**What goes wrong:** Asserting "109 rows / 0 unresolved" as the item-10a pass condition.
**Why it happens:** matriz `aio.py` grew from 852 LOC (SPIKE-005) to **959 LOC** (VERIFIED this session). The construct count will differ.
**How to avoid:** The gate is **"0 unresolved rows"** (`REVIEW`/`TBD`/`DENY-LIST-VIOLATION`), not a fixed row count. Re-run `001c/audit.py` verbatim; assert the `**MERGE GATE PASS:** zero unresolved rows.` sentinel. Also re-confirm the "zero bare `asyncio.*` in module body" structural property on current source.
**Warning signs:** A hardcoded `== 109` check.

### Pitfall 3: Conflating "lossless round-trip" with "byte-identity to the target"
**What goes wrong:** Concluding the premise is proven because `parse_module(src).code == src`.
**Why it happens:** libcst's round-trip guarantee is real but is about *reproducing the input*, not *producing a different hand-written target*. The gate (D-02) is the latter.
**How to avoid:** Keep the two checks distinct: (a) a smoke test that round-trip holds on `aio.py` (expected PASS, validates the tool), and (b) the item-1 diff of *transformed* output vs hand-written `client.py` (the actual gate).
**Warning signs:** An item-1 "PASS" that never diffs against `client.py`.

### Pitfall 4: B8 identity broken by a rebuilt alias node
**What goes wrong:** A transformer that rebuilds the module emits a thunk `def _raise_for_response(resp): return _core.raise_for_response(resp)` instead of preserving the alias assignment.
**Why it happens:** Over-eager FunctionDef synthesis or an AsyncToSync pass that touches the assignment line.
**How to avoid:** Never transform the `_raise_for_response = _core.raise_for_response` `Assign` node; assert `mod._raise_for_response is aio._raise_for_response is _core.raise_for_response` after load (item 2).
**Warning signs:** `is` returns `False`; two distinct object ids.

### Pitfall 5: Item-9 purity claimed while the transformer holds cross-module state
**What goes wrong:** The `ImportDirectionNormalizer` stores the extracted `_validate_max_retries` def as instance/global state and injects it into another module — now it is stateful and fails item 9.
**Why it happens:** Trying to do multi-module orchestration inside a single transformer.
**How to avoid:** Put orchestration in the driver; keep every `CSTTransformer` a pure per-module `leave_*`. See Q2.
**Warning signs:** A transformer with `self.<mutable>` accumulating nodes, or reading a second file.

## Code Examples

### Item-6 sandbox recipe (Anti-Pitfall 2 — never mutate `packages/`)
```bash
# Source: adapted from SPIKE-005 evidence-checklist.txt §item 6.
TS=$(date +%s); SB=/tmp/spike-006-ambito-$TS
cp -r packages/ambito-financiero-client "$SB-pkg"
cp .../output/client_generated.py "$SB-pkg/src/ambito_financiero_client/client.py"
uv run --package ambito-financiero-client pytest -q \
  packages/ambito-financiero-client/tests   # run against the sandboxed generated client.py
rm -rf "$SB-pkg"
```
**Expected failure mode to watch (item 6 / SPIKE-005 root cause):** if the generated `client.py` still contains `from ambito_financiero_client.client import _validate_max_retries` (a self-import), collection dies with `ImportError: cannot import name '_validate_max_retries' from partially initialized module` — the exact SPIKE-005 item-6 FAIL. The `ImportDirectionNormalizer` + def synthesis (Q1) must eliminate it.

### Item-10b deny-list scope under libcst (adapt 001d)
```python
# Only aio.py is ever parsed; the 4 deny-list files are never handed to libcst.
import hashlib, shutil, libcst as cst
DENY = ["_token_store.py", "_refresh_policy.py", "_refresh.py", "ws_client.py"]
pre  = {f: hashlib.sha256((SB/f).read_bytes()).hexdigest() for f in DENY+["aio.py"]}
mod  = cst.parse_module((SB/"aio.py").read_text())          # aio.py ONLY
(SB/"aio.py").write_text(mod.visit(AsyncToSync()).code)     # transform only aio.py
post = {f: hashlib.sha256((SB/f).read_bytes()).hexdigest() for f in DENY+["aio.py"]}
assert all(pre[f] == post[f] for f in DENY)                 # 4/4 byte-identical (item 10b)
assert pre["aio.py"] != post["aio.py"]                      # aio.py was transformed
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| unasync 0.6.0 token replacement (SPIKE-005) | libcst CST codemod (SPIKE-006) | v1.2→v1.3 | AST-level can reach docstring substrings + reorder imports; but cannot synthesize source-absent content (Q1) |
| `ruff format` post-pass required (unasync) | No post-pass needed for untouched trivia (libcst lossless) | v1.3 premise | Item 3 (`ruff format --check`) trivially PASS on untouched regions |
| `fpath_list` scope (unasync deny-list) | Per-module `parse_module` invocation (libcst) | v1.3 | Same guarantee shape — deny-list files never parsed = never mutated |

**Deprecated/outdated:**
- `ast.unparse` for this task: destroys comments/formatting — never a round-trip option.
- SPIKE-005 `diff_vs_v1.1_client.txt` as a baseline: superseded by v1.2-head source (regenerate).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `libcst` is the Meta/Instagram LibCST at `github.com/Instagram/LibCST`; the `SUS` seam verdict is a metadata-gap false positive, not a supply-chain signal. | Package Legitimacy Audit | Low — ephemeral install (D-05) contains blast radius; planner keeps one human-verify checkpoint |
| A2 | Exact libcst API surface for suppression/insertion (`RemovalSentinel.REMOVE`, `FlattenSentinel`, `Module.header` of `EmptyLine`/`Comment`, `SimpleString.value` rewrite) behaves as described. Round-trip guarantee itself is CITED/HIGH; these node-level specifics are CITED-structure/MEDIUM and must be confirmed empirically in `001a`/`001b`. | Architecture Patterns 3–5 | Medium — wrong node names cost transformer-authoring time, not the verdict; the spike surfaces them immediately |
| A3 | Item 9 purity is satisfiable by keeping `CSTTransformer` subclasses pure and pushing cross-module orchestration into the driver (the requirement text scopes purity to "the subclasses"). | Open Questions Q2 | Medium — if the operator reads item 9 as "the whole codegen pipeline must be pure," item 9 becomes unsatisfiable given the def-relocation need |
| A4 | The un-migrated ámbito `client.py` regions `_validate_max_retries` (def) and `load_dotenv` (import+call) have NO representation in `aio.py` and therefore cannot be produced by any pure transform of `aio.py` alone. | Open Questions Q1 | High if wrong — this is the crux of the item-1/6 outcome; VERIFIED by grep (aio.py only imports `_validate_max_retries`; has no `load_dotenv`), so risk is low but the *consequence* (likely NO-GO) is what the spike must confirm |

## Open Questions

1. **The content-absent-from-source obstacle (decisive for item 1 + item 6).**
   - What we know (VERIFIED): the target `client.py` contains a 22-line `_validate_max_retries` definition (`client.py:41-62`) and a dotenv bootstrap (`from dotenv import load_dotenv` `client.py:25` + `load_dotenv()` `client.py:30`). The source `aio.py` contains **neither** — it only *imports* `_validate_max_retries` (`aio.py:34`) and never imports dotenv (D-19). libcst transforms nodes that exist; it cannot invent a function body or a bootstrap the source module lacks.
   - What's unclear (the spike's job): whether the operator's transformer design can hit byte-identity **without** (a) migrating `aio.py` to hold the def (forbidden by D-03) or (b) reading the existing `client.py` as a *donor* input (which would make `client.py` both input and output, defeating single-sourcing). Under the strict un-migrated constraint, both escape hatches are closed — pointing to an honest **item-1 FAIL / item-6 self-import FAIL for the same source-shape root cause SPIKE-005 found.**
   - Recommendation: instrument this explicitly. Have `001a` attempt a pure-transform emission, capture the resulting diff, and record in `FINDING.md` whether the def + dotenv regions are the residual divergence. If they are, that is the signed evidence for a same-root-cause NO-GO (a valid, guaranteed deliverable per D-08). Do NOT smuggle in a client.py-donor step to force a GO.

2. **Item-9 purity vs cross-module def relocation.**
   - What we know: item 9 requires the `CSTTransformer` subclasses to be pure `CSTNode → CSTNode`. Relocating a def from one emitted module while rewriting an import in another is inherently multi-module, stateful orchestration.
   - What's unclear: whether the operator scopes "purity" to the transformer *classes* (satisfiable — driver owns state) or the *whole pipeline* (unsatisfiable given relocation).
   - Recommendation: adopt the class-level reading (A3): pure `CSTTransformer` subclasses + an explicitly impure driver. Express item 9 as a runtime/documented assertion that no `CSTTransformer` subclass reads global state, mutates instance state across nodes, or performs I/O. Flag the interpretation in `DECISION.md` so the operator ratifies it.

3. **Docstring byte-identity beyond mechanical localization.**
   - What we know (VERIFIED): module docstrings, the `with_options` docstring (43 vs 19 lines), `_request`/`configure`/`get_dollar_banco_nacion` docstrings, and several per-line comments diverge as independently hand-authored prose — not `sincrónico↔asincrónico` swaps.
   - What's unclear: whether the operator accepts a per-module hardcoded docstring literal inside `DocstringLocalizer` (which embeds the target in the tool — arguably not single-sourcing) as an item-1 PASS, or treats residual docstring divergence as an item-1 FAIL.
   - Recommendation: surface each divergent docstring region in `FINDING.md`; let the operator decide in `DECISION.md`. Note this compounds Q1.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `uv` | ephemeral libcst install + all `uv run` commands | ✓ | 0.9.0 | — |
| Python | runtime | ✓ | 3.12.11 (3.13 in CI) | — |
| `libcst` | 001a/001b/001d transforms | ✓ (ephemeral via `uv run --with`) | `>=1.8.0,<2` (1.8.6 latest) | none needed — resolved on demand |
| `ruff` | items 3, 4 | ✓ (dev dep) | `>=0.7` | — |
| `mypy` | item 5 | ✓ (dev dep, strict) | `>=1.13` | — |
| `import-linter` / `lint-imports` | item 7 | ✓ (dev dep) | — | — |
| `pytest`/`pytest-httpx`/`pytest-asyncio` | item 6 | ✓ | `>=8.3`/`>=0.34`/`>=0.24` | — |
| stdlib `ast` | item 10a (001c/audit.py) | ✓ | 3.12 | — |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none — libcst is the only new tool and is available on PyPI within the pinned band.

## Validation Architecture

> The `D-RIGOR-02` 10-item gate **is** the acceptance harness. Aggregate rule (D-04): GO iff all 10 items genuine PASS AND matriz audit 0-unresolved AND within 24h timebox; any FAIL → NO-GO.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `pytest >=8.3` + `pytest-httpx >=0.34` + `pytest-asyncio >=0.24` (`asyncio_mode=auto`); `ruff >=0.7`; `mypy >=1.13 --strict`; `import-linter`; stdlib `ast`; `libcst >=1.8.0,<2` |
| Config file | root `pyproject.toml` (pytest/ruff/mypy/coverage); `importlinter` contracts in `pyproject.toml`; libcst has none (ephemeral) |
| Quick run command | item-1 diff + item-2 B8 assert (`uv run --with 'libcst>=1.8.0,<2' python 001a/experiment.py`) |
| Full suite command | all 10 items → `evidence-checklist.txt` (mirrors SPIKE-005 Wave 5) |

### Phase Requirements → Test Map (the 10-item D-RIGOR-02 gate)
| Item | Behavior | Type | Automated Command | Checkable? | File Exists? |
|------|----------|------|-------------------|-----------|-------------|
| 1 (GO-det.) | Byte-identical round-trip vs **current** hand-written `client.py` (no source migration) | byte-diff | `diff -u packages/ambito-financiero-client/src/ambito_financiero_client/client.py 001a/output/client_generated.py` | ✅ byte | ❌ Wave 0 (regenerate baseline) |
| 2 | B8 identity preserved on generated | identity | `importlib` load + `assert mod._raise_for_response is aio._raise_for_response is _core.raise_for_response` | ✅ transcript | ♻ reuse SPIKE-005 |
| 3 | `ruff format --check` clean | format | `uv run ruff format --check 001a/output/client_generated.py` | ✅ exit-code | — |
| 4 (GO-det.) | `ruff check` clean incl. single-line import-order (I001) + ASYNC1xx | lint | `uv run ruff check 001a/output/client_generated.py` | ✅ exit-code | — |
| 5 | `mypy --strict` clean | typecheck | `uv run mypy --strict 001a/output/client_generated.py` | ✅ exit-code | — |
| 6 (GO-det.) | Ámbito mocked suite green vs generated (no circular self-import) | pytest | sandbox-copy recipe → `uv run --package ambito-financiero-client pytest -q` | ✅ exit-code | ♻ reuse recipe |
| 7 | `lint-imports` 4 contracts intact | contract | `uv run lint-imports` | ✅ exit-code | — |
| 8 | `@generated` marker × `from __future__ import annotations` | grammar | `ruff check` + `ruff format --check` + `mypy --strict` + `ast.parse` on marked file | ✅ exit-code | ♻ reuse 001b design |
| 9 (new) | CSTTransformer subclasses pure `CSTNode → CSTNode`, no global state/side-effects | property/assert | runtime assertion in `001a` (no `self`-accumulation, no I/O) OR documented property | ✅ assert | ❌ Wave 0 |
| 10a (new) | matriz construct audit: 0 unresolved rows | ast walk | `uv run python 001c/audit.py` → assert `MERGE GATE PASS` sentinel | ✅ sentinel | ♻ COPY 001c/audit.py verbatim |
| 10b (new) | matriz 4 deny-list files sha256-byte-identical pre/post; `aio.py` transformed | sha256 | 001d harness adapted to per-module libcst transform | ✅ hash | ♻ adapt 001d |

### Sampling Rate
- **Per experiment run:** item-1 diff + item-2 B8 (fast smoke).
- **Per sub-experiment merge:** the item(s) that sub-experiment owns (001a→1/2/3/4/5/6/9; 001b→8; 001c→10a; 001d→10b).
- **Phase gate:** full `evidence-checklist.txt` green-or-honest + operator-signed `DECISION.md` with the 10-item verdict map, before milestone close.

### Wave 0 Gaps
- [ ] `001a/experiment.py` — driver: parse → transform → emit → item-1 diff (vs **current** client.py) → item-2 B8 → item-9 purity assertion.
- [ ] `001a/transformers/*.py` — `async_to_sync`, `import_normalizer`, `docstring_localizer`, `import_direction_normalizer`, `suppressors`.
- [ ] Regenerate item-1 baseline against v1.2-head `client.py` (SPIKE-005 diff is stale — Pitfall 1).
- [ ] `001c/audit.py` — copy verbatim from SPIKE-005, re-point `SOURCE` at current matriz `aio.py` (959 LOC), re-run.
- [ ] `001d/experiment.py` — adapt to per-module libcst transform (drop `unasync`).
- [ ] `001b` marker insertion via `Module.header` (or fold into 001a per Discretion).
- [ ] libcst node-API confirmation (A2): confirm `RemovalSentinel`/`FlattenSentinel`/`Module.header`/`SimpleString.value` behavior empirically on first `001a` run.

## Security Domain

> `security_enforcement: true`, ASVS level 1, block_on: high. This is offline codegen tooling that reads trusted repo source and writes only under the spike dir — no network, no auth, no untrusted input, no runtime surface. The security-relevant concern here is **integrity of the concurrency/secret-handling primitives**, enforced by the deny-list gate.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Spike touches no auth flow |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | no (trusted input) | Input is the project's own source (git-tracked); libcst parses trusted Python |
| V6 Cryptography | no (by exclusion) | The token-store/refresh primitives (potential future crypto surface) are **deny-listed** — the spike proves they are NOT modified (item 10b sha256) |
| V14 Configuration / Supply-chain | yes | libcst legitimacy verified (§Package Legitimacy Audit); ephemeral install (D-05) not committed; `git diff --exit-code uv.lock` after spike |

### Known Threat Patterns for this phase
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Codegen silently mutates a deny-listed concurrency primitive (`_token_store.py` 3-way lock, `_refresh_policy.py` fail-cache) | Tampering | item 10b: 4-file sha256 byte-identity pre/post; files never parsed (per-module scope) |
| Supply-chain: malicious/typosquatted `libcst` | Tampering/Elevation | Legitimacy check run (verdict SUS = metadata gap, assessed legitimate — Meta/Instagram repo); ephemeral install; human-verify checkpoint before first install |
| Spike accidentally mutates production `packages/` source | Tampering | Anti-Pitfall 2 sandbox recipe (`cp -r` to `/tmp`, `.planning/spikes/` write-only); `git diff --exit-code packages/` after spike |
| Secret leakage | Info Disclosure | N/A — spike reads no `.env`; matriz secret-handling code is deny-listed and unmodified |

## Sources

### Primary (HIGH confidence)
- Repo source (grep/diff/wc, VERIFIED this session): `packages/ambito-financiero-client/src/ambito_financiero_client/{aio.py,client.py}` — line refs, `__slots__` drift, `with_options` docstring divergence, `_validate_max_retries`/`load_dotenv` content-absence; matriz deny-list files present, `aio.py` 959 LOC.
- `.planning/spikes/SPIKE-005-codegen-tool-choice/{DECISION.md, evidence-checklist.txt, README.md, 001a/FINDING.md, 001a/diff_vs_v1.1_client.txt, 001c/audit.py, 001d/experiment.py}` — the blueprint to parallel + reusable harness.
- `Skill("spike-findings-codegen-market-libs")` — SPIKE-005 NO-GO root cause, requirements carry-forward, integration blueprint.
- `pip index versions libcst` — version band `1.8.0–1.8.6` VERIFIED.

### Secondary (MEDIUM confidence)
- `libcst.readthedocs.io/en/latest/tutorial.html` [CITED] — `Module.code` generation, CSTTransformer subclassing, `.with_changes()`.
- `pypi.org/project/libcst` [CITED] — latest 1.8.6 (2025-11-03), Python 3.9+, Rust-backed, "keeps all formatting details (comments, whitespaces, parentheses, etc)."

### Tertiary (LOW confidence)
- Node-level API specifics (`RemovalSentinel`, `FlattenSentinel`, `Module.header` shape, `SimpleString.value`) — training-derived, structure consistent with CITED docs; confirm empirically in `001a` (A2).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — libcst version/identity VERIFIED against PyPI; round-trip guarantee CITED.
- Architecture / transformer API: MEDIUM — patterns CITED-structure; exact node names to confirm on first run (A2).
- Canary asymmetry catalog + drift: HIGH — VERIFIED by direct grep/diff/wc against current source.
- Item-1/6 outcome (Q1): the *analysis* is HIGH-confidence (content-absence is VERIFIED); the *verdict* is deliberately left to the spike's empirical run (that is the phase's purpose).
- Pitfalls / Don't-Hand-Roll: HIGH — grounded in SPIKE-005 artifacts + verified drift.

**Research date:** 2026-07-02
**Valid until:** 2026-08-01 (30 days — libcst is stable; the repo canary is the moving part, so regenerate baselines if ámbito source changes before planning).
