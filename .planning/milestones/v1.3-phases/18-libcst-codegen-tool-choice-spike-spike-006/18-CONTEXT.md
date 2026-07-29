# Phase 18: libcst Codegen Tool-Choice Spike (SPIKE-006) - Context

**Gathered:** 2026-07-02 (assumptions mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

**Produce a signed GO/NO-GO decision** on whether `libcst >=1.8.0,<2` (AST-level codemod)
can single-source the sync/async transport shells — evaluated against the `D-RIGOR-02`
**10-item gate** on the ámbito canary in its **v1.2-head shape (NOT migrated)**, plus
inheritance of the matriz construct audit + deny-list intactness.

This is a **RESEARCH FLAG / spike-before-plan** phase (same pattern as v1.2 Phase 12 /
SPIKE-005). It **ALWAYS runs**; its signed decision is the milestone's guaranteed
deliverable. The deliverable is a **binary decision + evidence transcripts + per-package
CSTTransformer drafts** — NOT production codegen integration (that is Phase 19, conditional
on GO).

**In scope:** ámbito canary round-trip via libcst CSTTransformers; matriz audit + deny-list
re-verification; the signed `DECISION.md`.
**Out of scope (spike CONFIRMS, does not build):** production CI hook / pre-commit /
Makefile target / pinned dev-dep (all Phase 19 GO-branch); re-running unasync experiments
(already NO-GO per SPIKE-005); codegen for `_core.py` (single-source since v1.1 Phase 7) or
the 4 matriz deny-list files.
</domain>

<decisions>
## Implementation Decisions

### Sub-Experiment Decomposition
- **D-01:** The spike decomposes into **4 sub-experiments** mirroring SPIKE-005's `001a`–`001d`,
  under `.planning/spikes/SPIKE-006-libcst-codegen-tool-choice/`:
  - `001a-ambito-round-trip` — the 3 GO-determining items (1 byte-identical, 4 `ruff check`
    import-order, 6 mocked-suite-green) via working libcst CSTTransformers on the **un-migrated**
    canary. **Item 9** (CSTTransformer purity, `CSTNode → CSTNode`, no global state/side-effects)
    folds in here as an assertion on the transformer classes.
  - `001b-ambito-marker-future-compat` — item 8 (`@generated` marker × `from __future__ import
    annotations`) re-verified with libcst's `cst.Comment` leading-comment insertion (marker design
    itself carries forward unchanged from SPIKE-005 001b).
  - `001c-matriz-construct-audit` — item 10a: **re-run the existing SPIKE-005 `001c/audit.py`
    unchanged** (pure stdlib-`ast`, tool-agnostic — copy verbatim). Merge gate sentinel
    `**MERGE GATE PASS:** zero unresolved rows.` reused as-is.
  - `001d-matriz-deny-list-config` — item 10b: 4-file sha256 byte-identity pre/post under
    `libcst.MetadataWrapper` **per-file scope** (libcst's equivalent of unasync's `fpath_list` scope).

### Transformer Scope & the GO Bar (item 1) — **operator-decided, STRICT**
- **D-02:** **Item 1 target is STRICT byte-identity to the EXISTING v1.1 hand-written
  `client.py`.** Any divergence in the generated sync output = **item-1 FAIL = NO-GO**.
  (Operator decision 2026-07-02 — honors the CODEGEN-01 requirement literal and matches the
  strict SPIKE-005 NO-GO reading.)
- **D-03:** Consequently the spike must author **more than the 3 headline transformers.**
  In addition to `ImportDirectionNormalizer` (moves `_validate_max_retries` def → client.py,
  rewrites the `aio.py:34` import), the import-order `ImportNormalizer` (normalizes the
  non-alphabetical single-line `from <pkg> import ...`), and `DocstringLocalizer`
  (sincrónico↔asincrónico, Client↔AsyncClient), it must **SUPPRESS aio-only constructs during
  sync emission** so the output matches hand-written `client.py` verbatim:
  - no sync `close()` delegator (`aio.py:266-268 aclose()` has no hand-written sync twin),
  - `configure()` must OMIT the WR-07 `ResourceWarning` block (`aio.py:224-242`),
  - `_REQUEST_TIMEOUT` placement matches `client.py` (before `_validate`), not `aio.py` order.
  **All normalization happens at generation time. `aio.py` source is NOT edited** — this is the
  whole point vs unasync's required ~30 LOC source migration. If the spike cannot hit byte-identity
  via generation-time transformers alone, that is an honest FAIL, not a target to soften.
- **D-04:** **Aggregate verdict:** GO = all 10 `D-RIGOR-02` items genuine PASS **+** matriz audit
  0-unresolved **+** within timebox. **Any item FAIL → NO-GO.** A Recipe-2-style informative
  hunk classification is allowed **alongside** the strict verdict (as SPIKE-005 did), never
  replacing it. On NO-GO the 3 previously-failing items (1/4/6) failing again → REFAC-06 is
  **permanently shelved** and the milestone closes on the signed NO-GO.

### Dependency Handling
- **D-05:** libcst is installed **ephemerally** via `uv run --with 'libcst>=1.8.0,<2' python
  <experiment>.py` (SPIKE-005 used the identical `--with unasync` pattern). It is **NOT** added
  to root `[dependency-groups] dev` during the spike — the pinned dev-dep is a Phase 19 GO-branch
  deliverable (`REQUIREMENTS.md` REFAC-06). This keeps a NO-GO outcome free of a dangling committed
  dep and avoids `uv.lock --frozen` churn mid-spike.

### Decision Artifact & Timebox — **operator-decided**
- **D-06:** An operator-signed **`DECISION.md`** (frontmatter with a per-item verdict map for all
  10 items) + **`evidence-checklist.txt`** (10-item PASS/FAIL transcripts) live at the SPIKE-006
  root, mirroring SPIKE-005's shape verbatim.
- **D-07:** **24h D-SCOPE-03 hard timebox inherited** from SPIKE-005; over-cap → **AUTO-NO-GO.**
  (Operator decision 2026-07-02. SPIKE-005 finished in ~19 min; libcst is slower and its
  transformers are more code, but the operator elects the strict inherited cap.)

### Phase 19 Handoff Artifact
- **D-08:** On **GO** — the handoff is the **3+ working CSTTransformer classes** authored in `001a`,
  canary-proven and asserted pure (item 9), promoted as **"drafts"** for the 4-package rollout.
  They are **NOT** required to be generalized/verified across iol/higyrus/matriz within the spike
  (draft quality = canary-proven + other-package-inferred, per SPIKE-005's per-package Rule-config
  precedent). On **NO-GO** — REFAC-06 marked permanently shelved; the duplicate `client.py`/`aio.py`
  shells become an accepted structural feature.

### Matriz Deny-List (CONFIRM, do not renegotiate)
- **D-09:** The 4 matriz deny-list files (`_token_store.py`, `_refresh_policy.py`, `_refresh.py`,
  `ws_client.py`) are re-verified **sha256-byte-identical pre/post** (item 10b). The spike CONFIRMS
  they are OUT of codegen scope; it does **not** renegotiate the deny-list.

### Folded Todos
- **Folded:** `.planning/todos/pending/spike-codegen-libcst-v1.3.md` (`resolves_phase: 18`,
  match score 0.9) — this todo **is** the phase; its scope/acceptance-criteria/references are the
  source material for the decisions above. On completion it moves out of `pending/`.

### Claude's Discretion
- Exact file naming/layout inside `001a/transformers/`; whether item-9 purity is expressed as a
  runtime test assertion or a documented property (analyzer folded it into `001a`).
- Whether `001b` is a standalone experiment or a check appended to `001a` (marker insertion is a
  single leading `cst.SimpleStatementLine`); planner's call within the SPIKE-005-parallel structure.

### Needs Research (for gsd-phase-researcher — resolving these empirically IS the spike)
- **libcst round-trip trivia fidelity:** whether `libcst` parse→transform→`.code` is byte-lossless
  on ámbito's `aio.py` (trailing comments, multi-line rST `::` docstrings, `# ---...---` dividers)
  **without** a `ruff format` post-pass — the v1.3 premise, must be empirically confirmed.
- **Cross-module purity tension:** whether the `_validate_max_retries` move (rewrite an import in
  one emitted module while relocating a def to another) can be a **pure `CSTNode → CSTNode`**
  transformer (item 9's bar) or fundamentally needs stateful two-module orchestration. May be an
  inherent tension in the gate the researcher/planner must resolve.
- **Docstring rewrite mechanics:** exact `cst.SimpleString` value-rewrite API for `DocstringLocalizer`
  (localize labels, strip `await ` inside docstring example blocks) while preserving triple-quote
  style + internal indentation.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/REQUIREMENTS.md` — CODEGEN-01 + the full `D-RIGOR-02` 10-item gate + in-cycle
  verification convention + Out-of-Scope table.
- `.planning/ROADMAP.md` §"Phase 18" — Goal + 5 Success Criteria (what must be TRUE).
- `.planning/todos/pending/spike-codegen-libcst-v1.3.md` — the folded todo: scope, validation
  target, inherited evidence, acceptance criteria, references.
- `.claude/skills/spike-findings-codegen-market-libs/SKILL.md` — auto-loaded SPIKE-005 NO-GO
  learnings, requirements carry-forward, and the v1.3 libcst integration blueprint (spike dir
  structure, per-package CSTTransformer pattern, B8 preservation, marker design).
- `.planning/spikes/SPIKE-005-codegen-tool-choice/` — the blueprint to parallel:
  - `DECISION.md` — operator-signed NO-GO + per-package Rule drafts + frontmatter shape.
  - `evidence-checklist.txt` — 8-item D-RIGOR-01 transcript format (items 2/3/5/7/8 inherited PASS).
  - `README.md` — sub-experiment table + `--with unasync` ephemeral pattern.
  - `001a-ambito-round-trip/FINDING.md` — the 10-hunk Recipe-2 classification + the ~30 LOC
    source-migration sketch libcst must AVOID.
  - `001b-.../FINDING.md` — `@generated` marker design (PEP 263/236, marker-neutral).
  - `001c-matriz-construct-audit/audit.py` — **reuse verbatim** for item 10a (109 rows, 0 unresolved).
  - `001d-.../FINDING.md` — deny-list intactness via `fpath_list` scope (adapt to `MetadataWrapper`).
- Canary source (read in full): `packages/ambito-financiero-client/src/ambito_financiero_client/`
  `{aio.py, client.py, _core.py}`.
- Matriz deny-list (item 10b sha256 targets): `packages/matriz-client/src/matriz_client/`
  `{_token_store.py, _refresh_policy.py, _refresh.py, ws_client.py}`.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **SPIKE-005 `001c/audit.py`** — pure stdlib-`ast`, tool-agnostic (no unasync reference);
  `DENY_LIST` at lines 46-53. Copy verbatim for item 10a; if result is still 109 rows / 0
  unresolved, no new audit work needed.
- **`@generated` marker design** (SPIKE-005 001b) — 3-line block (2 comment lines + 1 blank),
  PEP 263/236 compliant, marker-neutral on all 4 verification commands. Prepend via a leading
  `cst.SimpleStatementLine`/`cst.Comment` (NEVER `str.replace` — Anti-Pitfall 6).
- **B8 identity test** — `assert mod._raise_for_response is aio._raise_for_response is
  _core.raise_for_response`. Every CSTTransformer MUST emit `_raise_for_response =
  _core.raise_for_response` verbatim (guards against a thunk-wrapper — Pitfall 4). Line exists
  verbatim in ámbito `client.py`/`aio.py`/`_core.py`.

### Established Patterns
- **Concrete asymmetries to close** (evidence from the canary):
  - Import direction: `_validate_max_retries` DEFINED at `client.py:41-62`, IMPORTED at `aio.py:34`.
  - Import order: `aio.py:32` `from <pkg> import _atransport, _core` → non-alphabetical
    `_transport, _core` after async→sync rename.
  - Docstrings: `aio.py:1` "asincrónico" vs `client.py:1` "sincrónico".
  - **aio-only constructs to SUPPRESS** (D-03): `aclose()` at `aio.py:266-268`; WR-07
    `ResourceWarning` block at `aio.py:224-242`; `_REQUEST_TIMEOUT` position `aio.py:49` vs
    `client.py:32`.
- **Deny-list scope discipline** — unasync achieved it by NOT listing files in `fpath_list`;
  libcst's equivalent is per-file `CSTTransformer`/`MetadataWrapper` invocation. Matriz `aio.py`
  additionally has ZERO bare `asyncio.<attr>` in the code body (all async primitives encapsulated
  in the deny-listed `_token_store.py`) — a structural guarantee stronger than scope alone.

### Integration Points
- libcst is currently **absent** from every `pyproject.toml` and `uv.lock` — the spike introduces
  it only ephemerally (D-05).
- The spike writes ONLY under `.planning/spikes/SPIKE-006-.../` — no `packages/` source is mutated
  (canary transforms run against sandbox copies; deny-list files are read-only sha256 targets).
</code_context>

<specifics>
## Specific Ideas

- **Strict byte-identity to the *existing* hand-written `client.py`** (D-02) is the operator's
  explicit bar — the generated sync output must match verbatim, including the ABSENCE of a sync
  `close()`/`ResourceWarning`, forcing generation-time suppression transformers rather than any
  edit to `aio.py`.
- **24h D-SCOPE-03 cap → AUTO-NO-GO** on over-cap (D-07) — the operator elects the strict inherited
  timebox even knowing libcst is slower to author.
</specifics>

<deferred>
## Deferred Ideas

- **Production codegen integration** (CI `lint-codegen` job, pre-commit hook, `make codegen`
  target, pinned `libcst` dev-dep) — Phase 19 GO-branch only, DROPPED if NO-GO.
- **4-package generalization** of the transformers (iol/higyrus/matriz) — Phase 19; the spike
  proves only the ámbito canary + infers the rest.

### Reviewed Todos (not folded)
- None beyond the single folded spike todo — analysis stayed within phase scope.
</deferred>
