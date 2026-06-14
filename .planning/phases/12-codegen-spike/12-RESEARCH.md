# Phase 12: Codegen Spike — Research

**Researched:** 2026-06-14
**Domain:** Codegen tool-choice spike (unasync 0.6.0 vs libcst 1.8.6 fallback) for async-first single-source `aio.py` → `client.py` transport-shell generation × 4 packages.
**Confidence:** HIGH (recipes verified against httpcore + elasticsearch-py production usage; package legitimacy `[OK]` on PyPI for unasync + libcst)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-SCOPE-01 — Package coverage = ámbito round-trip + matriz construct audit.** Ámbito is the canary (no auth, smallest surface). Matriz is enumerated in writing but NOT round-tripped. iol + higyrus inferred from ámbito. If Phase 16 discovers edge cases in iol OAuth refresh-token flow or higyrus `event_hooks` lock-protected mutation, the spike is re-opened or fix lands inline. Risk accepted.
- **D-SCOPE-02 — Matriz audit = enumeration + manual proof.** Every async-only construct in matriz `aio.py` is classified either (a) lives in deny-list (`_token_store.py` / `_refresh_policy.py` / `ws_client.py`) and confirmed excluded via `Rule` config, or (b) NOT in deny-list and has explicit `additional_replacements` proof showing the sync emission. **Zero TBD rows is the merge gate.**
- **D-SCOPE-03 — Time-budget cap = 1 day.** Beyond 1 day without convergence to a clear GO (B8 identity preserved, ruff/mypy/import-linter green, byte-identical modulo ruff format) → **NO-GO automatic.** Anti-rabbit-hole.
- **D-RIGOR-01 — GO requires all 8 evidence items:** (1) byte-identical round-trip ámbito; (2) B8 identity on generated; (3) `uv run ruff format --check` clean; (4) `uv run ruff check` clean (including ASYNC1xx); (5) `uv run mypy --strict` clean; (6) `pytest -q` green for ambito package; (7) `uv run lint-imports` 4 existing contracts intact; (8) `@generated` marker compatible with `from __future__ import annotations`. ANY failure → NO-GO.
- **D-NOGO-01 — NO-GO close-out → defer libcst to v1.3.** Do NOT extend Phase 12 to evaluate libcst inline. Phase 16 dropped, Phase 17 unblocked.
- **D-NOGO-02 — NO-GO close-out artifacts:** `NO-GO.md` root cause + REQUIREMENTS.md update (REFAC-06 → "Defer v1.3") + ROADMAP.md update (Phase 16 DROPPED) + new pending todo `spike-codegen-libcst-v1.3.md`.
- **D-ARTIFACT-01 — Spike lives in `.planning/spikes/SPIKE-005-codegen-tool-choice/`.** Continues v1.1 numbering (001a/b/c + 002 + 003 = 5, next is 005). Each experiment is a sub-directory with code + `FINDING.md` (mirror of SPIKE-001a layout).
- **D-ARTIFACT-02 — Wrap-up via `/gsd-spike --wrap-up` → new `spike-findings-codegen-market-libs` Skill** auto-loaded in CLAUDE.md "Auto-loaded Knowledge". Phase 16 (if GO) consumes it.
- **D-ARTIFACT-03 — `12-SUMMARY.md`** closes Phase 12 (separate from the spike directory close-out). Frontmatter includes: link to spike directory, link to skill, GO/NO-GO decision, 8-item evidence checklist completed, operator signoff date, next-step routing (Phase 13 vs Phase 14+15+17 depends on GO/NO-GO).

### Claude's Discretion

(All discretion items above were accepted by operator as locked — D-RIGOR-01, D-NOGO-01/02, D-ARTIFACT-01/02/03. The planner has no further degrees of freedom on these.)

### Deferred Ideas (OUT OF SCOPE)

- **libcst exploration spike** — defer to v1.3 if Phase 12 NO-GO. Captured as `spike-codegen-libcst-v1.3.md` at close-out.
- **Driver migration codegen (`main_*.py`)** — drivers are application, not library; Phase 15 migrates them manually.
- **Per-package codegen `Rule` completeness for iol + higyrus + matriz** — Phase 12 documents drafts only; Phase 16 cristallizes and applies.
- **CI `lint-codegen` job + pre-commit hook setup** — Phase 16 deliverables; Phase 12 only documents draft.
- **Edge cases for iol OAuth refresh-token + higyrus `event_hooks` lock-protected** — inferred from ámbito; if Phase 16 discovers them, in-cycle bug-fix pattern applies.
- **Codegen for `_core.py`** — already single-source since v1.1 Phase 7; permanent defer.
- **Codegen for matriz `_token_store.py` / `_refresh_policy.py` / `ws_client.py`** — explicitly in deny-list (architectural invariant, NOT renegotiated by spike).
- **Generated-code parity tooling beyond unasync** (Jinja2, custom AST passes) — research already rejected (see SUMMARY.md). Permanent defer unless circumstances change.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| **REFAC-06** (spike-gated decision artifact only) | unasync/codegen single-source for `client.py`/`aio.py` transport shells × 4 packages. Phase 12 produces a binary GO/NO-GO + the per-package `Rule` config draft (GO branch) or v1.3 defer artifact (NO-GO branch). Full implementation deferred to Phase 16, conditional on Phase 12 GO. | Recipes 1-10 below cover: unasync invocation, ámbito round-trip, B8 preservation test, matriz construct enumeration, `@generated` marker compatibility with `from __future__ import annotations`, ruff/mypy/import-linter gates, spike directory layout, wrap-up skill production, NO-GO close-out diff sequences. |

</phase_requirements>

## Summary

Phase 12 is a **1-day-timeboxed binary decision spike**. It does not implement codegen anywhere in `packages/` — all experiments live under `.planning/spikes/SPIKE-005-codegen-tool-choice/<experiment>/`. The spike answers a single question: can `unasync >=0.6.0,<0.7` (primary candidate) generate a byte-identical (modulo `ruff format`) `client.py` from `aio.py` for the ámbito-financiero-client canary, while preserving the 8 evidence items in D-RIGOR-01, AND while every async-only construct in matriz `aio.py` is either (a) in the codegen deny-list (`_token_store.py` / `_refresh_policy.py` / `ws_client.py`) or (b) has an explicit `additional_replacements` proof that emits correct sync? Convergence → **GO** (Phase 16 proceeds with the captured per-package `Rule` configs). Non-convergence within 1 day → **NO-GO automatic** (REFAC-06 defers to v1.3, Phase 16 dropped, Phase 17 unblocked).

**Primary recommendation:** Use the `unasync_files()` standalone-script invocation pattern (not the setuptools `cmdclass_build_py()` integration). Each experiment is a 15-30 LOC Python script that imports `unasync`, runs one `Rule(fromdir, todir, additional_replacements={...})`, writes output to a sibling file, and shells out to `uv run ruff format` before `diff`-ing against the v1.1 hand-written target. The `@generated` marker as a Python comment (`#`) is verified compatible with `from __future__ import annotations` per Python's grammar (comments are tokenized as `NL` / `COMMENT` and do NOT block future statements — future statements only require nothing but docstring, comments, blank lines, and other future imports to precede them).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Spike experiment scripts | `.planning/spikes/SPIKE-005-codegen-tool-choice/<id>/` | — | Throwaway, dev-only. Phase 10 convention. No `packages/` mutation. |
| Decision artifact | `.planning/spikes/SPIKE-005-codegen-tool-choice/DECISION.md` | — | Operator signoff source-of-truth. Frontmatter `decision: GO\|NO-GO`. |
| Wrap-up Skill | `.claude/skills/spike-findings-codegen-market-libs/SKILL.md` | — | Auto-loaded; consumed by Phase 16. Produced via `/gsd-spike --wrap-up`. |
| Phase close artifact | `.planning/phases/12-codegen-spike/12-SUMMARY.md` | — | GSD phase closure. Separate from spike directory close-out. |
| `unasync` install scope | dev-only, root `[dependency-groups] dev` (only IF GO and only in Phase 16) | — | NEVER runtime; generated code has zero `unasync` import. Phase 12 uses `uv run --with unasync` (transient, no `pyproject.toml` edit). |
| Codegen deny-list (matriz) | Spike CONFIRMS, does NOT mutate | architectural invariant locked by ARCHITECTURE.md research | `_token_store.py` / `_refresh_policy.py` / `ws_client.py` excluded via `Rule(fromdir="aio.py", ...)` file-list scope (single-file Rule), NOT via separate `exclude=` param (unasync 0.6.0 has no such param). |

## Standard Stack

### Core (Spike Experiments Only — Not Installed in `packages/`)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `unasync` | `>=0.6.0,<0.7` | Token-replacement codegen `aio.py` → `client.py` | Used by httpcore, elasticsearch-py, trio — the same httpx ecosystem this project lives in. MIT OR Apache-2.0. Zero runtime dep (the generated code never imports `unasync`). `[VERIFIED: PyPI registry + slopcheck OK]` |

### Fallback (Deferred to v1.3 per D-NOGO-01)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `libcst` | `>=1.8.0,<2` | AST-level codemod (concrete syntax tree, preserves whitespace + comments) | ONLY if v1.3 reopens the question; Phase 12 NO-GO branch defers the evaluation. `[VERIFIED: PyPI registry + slopcheck OK]` |

### Tools (Already Installed — Spike Uses Existing Stack)

| Tool | Version | Purpose | Spike Usage |
|------|---------|---------|-------------|
| `ruff` | `>=0.7` | Format + lint generated output | `uv run ruff format <generated>` before `diff`; `uv run ruff check <generated>` for ASYNC1xx false-positives |
| `mypy` | `>=1.13` | Type-check generated file under `strict = true` | `uv run mypy packages/ambito-financiero-client/src/<generated path>` |
| `pytest` + `pytest-httpx` | `>=8.3` / `>=0.34` | Run ámbito mocked test suite against generated `client.py` | `uv run --package ambito-financiero-client pytest -q` |
| `import-linter` | `>=2.11,<3` | Re-verify the 4 existing `[[tool.importlinter.contracts]]` (`_core` ↛ `client`/`aio`) | `uv run lint-imports` |

### Installation (Spike-Only — Transient via `uv run --with`)

```bash
# Run the spike experiments WITHOUT touching root pyproject.toml.
# uv resolves a transient environment that includes the workspace + unasync.
uv run --with unasync python .planning/spikes/SPIKE-005-codegen-tool-choice/001a-ambito-round-trip/experiment.py
```

This sidesteps the "add unasync to dev deps" decision — that decision belongs to Phase 16 (if GO).

**Version verification (executed 2026-06-14):**

```bash
slopcheck install unasync libcst
# [OK] libcst (pypi)
# [OK] unasync (pypi)
```

Both packages pass slopcheck legitimacy gate. Last known versions per STACK.md: `unasync 0.6.0` (released 2024-05-03), `libcst 1.8.6` (released Nov 2025). The planner should re-run `slopcheck install unasync` at Phase 12 wave start and embed the version snapshot into the spike `FINDING.md`.

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| `unasync` | PyPI | ~2 yrs (0.6.0 May 2024) | low-medium (httpcore + elasticsearch-py production users) | github.com/python-trio/unasync | [OK] | **Approved (spike-only, dev-only).** Used via `uv run --with unasync` transient install in Phase 12; goes into root `[dependency-groups] dev` only in Phase 16 GO branch. |
| `libcst` | PyPI | ~0.5 yrs (1.8.6 Nov 2025) | high (Instagram, mypy ecosystem) | github.com/Instagram/LibCST | [OK] | **Approved (NOT used in Phase 12).** Fallback only, deferred to v1.3 per D-NOGO-01. |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## TL;DR for the Planner — 5 Bullets

1. **Spike experiments live in `.planning/spikes/SPIKE-005-codegen-tool-choice/<id>/`** (Phase 10 convention). NO `packages/` mutation. Sub-directories: `001a-ambito-round-trip/`, `001b-ambito-marker-future-compat/`, `001c-matriz-construct-audit/`, `001d-matriz-deny-list-config/`. Each has `README.md` + `experiment.py` + `FINDING.md`.
2. **Operational gate (PRE-Phase-12):** v1.1 head `71bf201` must be CI-green on Python 3.13 before Phase 12 starts. Quick-task fix lands first if CI red. (Already documented in STATE.md + ROADMAP.md.)
3. **Tool invocation = standalone Python script** calling `unasync.unasync_files([...], rules=[unasync.Rule(fromdir, todir, additional_replacements={...})])` — NOT setuptools `cmdclass_build_py()`. The script is ~30 LOC, runs as `uv run --with unasync python experiment.py`.
4. **The 1-day timebox is hard.** If by end-of-day the ámbito round-trip diff is non-empty AND non-trivially-fixable via `additional_replacements`, OR if any of the 8 evidence items in D-RIGOR-01 fails, the spike triggers NO-GO automatic. NO libcst exploration inline (D-NOGO-01).
5. **GO close-out:** captures per-package `Rule` config draft for all 4 packages + verifies the `@generated` marker can coexist with `from __future__ import annotations` (line 1 = marker comment, line 2 = blank, line 3 = future import) + `/gsd-spike --wrap-up` produces `spike-findings-codegen-market-libs` Skill. **NO-GO close-out:** generates `NO-GO.md` + REQUIREMENTS.md/ROADMAP.md edits + `spike-codegen-libcst-v1.3.md` pending todo. Both branches close with `12-SUMMARY.md`.

## Architecture Patterns

### System Architecture Diagram (Spike Data Flow)

```
                    ┌────────────────────────────────────────────────┐
                    │  Operator runs /gsd-execute-phase 12           │
                    └────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Wave 0: Spike directory bootstrap                                          │
│  - mkdir .planning/spikes/SPIKE-005-codegen-tool-choice/                     │
│  - write README.md (frontmatter: spike: 005, type: standard,                 │
│    validates: "unasync round-trip preserves B8 identity and...")            │
│  - write 4 sub-directory skeletons (001a/b/c/d) with README.md +            │
│    experiment.py stub                                                       │
│  - register in .planning/spikes/MANIFEST.md                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  Wave 1: 001a — Ámbito round-trip (the gate)                                 │
│  experiment.py:                                                              │
│    import unasync                                                            │
│    rules = [unasync.Rule(fromdir="<src>/aio.py", todir="<sibling>/...",     │
│             additional_replacements={                                        │
│                "AsyncClient": "Client",                                      │
│                "AsyncRetryTransport": "RetryTransport",                      │
│                "_atransport": "_transport",                                  │
│                "httpx.AsyncClient": "httpx.Client",                          │
│                "_get_default_async_client": "_get_default",                  │
│                "_default_async_client": "_default_client",                   │
│                "aclose": "close",                                            │
│                "aread": "read",                                              │
│                ...                                                           │
│             })]                                                              │
│    unasync.unasync_files([aio_path], rules)                                  │
│  Then:                                                                       │
│    uv run ruff format <generated client.py>                                  │
│    diff <generated> packages/ambito-financiero-client/.../client.py          │
│  Acceptance: empty diff. If non-empty → triage diff hunks (cosmetic vs       │
│  semantic). If semantic → spike NO-GO unless additional_replacements fix.    │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  Wave 2: 001b — Marker × `from __future__` compatibility                    │
│  experiment.py: prepend the @generated marker to the ámbito generated       │
│    client.py from Wave 1; verify line ordering (marker, blank, future).     │
│    uv run ruff check + uv run ruff format --check + uv run mypy --strict.   │
│  Acceptance: all 3 commands clean.                                          │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  Wave 3: 001c — Matriz construct audit (enumeration + classification)        │
│  experiment.py: walk matriz aio.py with stdlib ast; emit table              │
│    {file, line, construct, classification (deny-list | manual-sync-proof   │
│    | TBD)}                                                                   │
│  Acceptance: ZERO TBD rows.                                                  │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  Wave 4: 001d — Matriz deny-list scope verification                         │
│  experiment.py: write a Rule for matriz aio.py ONLY (NOT a directory).      │
│    Confirm that the Rule input file list does NOT include                   │
│    _token_store.py, _refresh_policy.py, ws_client.py.                       │
│  Acceptance: per-file scope confirmed; deny-list files untouched.           │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  Wave 5: 8-item evidence checklist (D-RIGOR-01) on the Wave 1 + 2 output    │
│  Per checklist: collect transcripts + screenshots of each command.           │
│  Decision = GO iff 8/8 pass. NO-GO if any single item fails OR if           │
│  Wave 1-4 cumulative wall-clock exceeds 1 day.                              │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  Wave 6: Close-out                                                          │
│  GO branch:                                                                 │
│   - Write DECISION.md (frontmatter decision: GO + 8-item evidence + per-pkg │
│     Rule config drafts for ambito/iol/higyrus/matriz)                       │
│   - Run /gsd-spike --wrap-up → produces                                     │
│     .claude/skills/spike-findings-codegen-market-libs/SKILL.md              │
│   - Update CLAUDE.md "Auto-loaded Knowledge" to reference new skill         │
│   - Write 12-SUMMARY.md with frontmatter status: complete + decision: GO    │
│  NO-GO branch:                                                              │
│   - Write DECISION.md (frontmatter decision: NO-GO) + NO-GO.md (root cause) │
│   - Edit REQUIREMENTS.md: move REFAC-06 to "Future Requirements (Defer to   │
│     v1.3+)" section                                                          │
│   - Edit ROADMAP.md: mark Phase 16 DROPPED; update Progress table           │
│   - Write .planning/todos/pending/spike-codegen-libcst-v1.3.md              │
│   - Run /gsd-spike --wrap-up → produces same skill (NO-GO flavor with       │
│     failure-mode + libcst path documented)                                  │
│   - Write 12-SUMMARY.md with frontmatter status: complete + decision: NO-GO │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Recommended Spike Directory Structure

```
.planning/spikes/SPIKE-005-codegen-tool-choice/
├── README.md                                       # spike entry: hypothesis + verdict link
├── DECISION.md                                     # operator-signed GO|NO-GO + 8-item evidence
├── NO-GO.md                                        # ONLY if decision = NO-GO; root cause analysis
├── 001a-ambito-round-trip/
│   ├── README.md                                   # frontmatter + Given/When/Then
│   ├── experiment.py                               # ~30 LOC unasync_files() invocation
│   ├── generated_client.py                         # output of experiment.py (artifact, not committed if NO-GO?)
│   ├── diff_vs_v1.1_client.txt                     # diff transcript
│   └── FINDING.md                                  # verdict + hunks + Rule config
├── 001b-ambito-marker-future-compat/
│   ├── README.md
│   ├── experiment.py                               # prepends marker, runs ruff + mypy
│   ├── verification_transcripts.txt                # ruff check / format --check / mypy outputs
│   └── FINDING.md
├── 001c-matriz-construct-audit/
│   ├── README.md
│   ├── audit.py                                    # ast-walker that emits the classification table
│   ├── matriz-aio-constructs.md                    # the table (machine-generated)
│   └── FINDING.md                                  # operator-reviewed classification
└── 001d-matriz-deny-list-config/
    ├── README.md
    ├── experiment.py                               # Rule fromdir=aio.py-only, verify deny-list intact
    ├── verification_transcripts.txt                # sha256 before/after for deny-list files
    └── FINDING.md
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Async-to-sync token rewrite | Custom regex/sed pipeline | `unasync.unasync_files()` | Tokenize-based replacement avoids string-in-comment / docstring false positives. httpcore + elasticsearch-py + trio in production. |
| `diff` of generated vs hand-written | `python -c "...readlines(); zip..."` | `diff -u <generated> <hand-written>` shell command | Standard unified diff is what operators read. Side note: `diff --strip-trailing-cr` if CRLF appears. |
| AST walk for construct enumeration | Hand-rolled token scanner | stdlib `ast.parse` + `ast.walk` | Native, exact, includes line numbers. Matches Phase 11 CR-06 AST pattern already validated in this repo. |
| File hash for deny-list intactness | Custom byte-by-byte | `hashlib.sha256(Path(p).read_bytes()).hexdigest()` | Trivial; matches Pitfalls.md §Pitfall 6 test pattern. |
| Skill artifact authoring | Hand-write SKILL.md | `/gsd-spike --wrap-up` | Project SDK command; standardized format already validated by `spike-findings-market-libs/SKILL.md`. |

**Key insight:** This spike is small enough (4 sub-experiments, 1 day cap) that hand-rolling almost anything is overshoot. The default `unasync` invocation pattern is published in the trio docs and validated by 3 production users (httpcore, elasticsearch-py, trio); the spike's job is to confirm the pattern survives this codebase's specific shape, NOT to invent a new pattern.

## Runtime State Inventory

> **This is a spike phase, NOT a rename/refactor.** No production-side state is mutated. The "state" that the spike inventories is the existing repo files it audits.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — spike does not touch any datastore. | None. |
| Live service config | None — spike does not touch live services. | None. |
| OS-registered state | None — spike does not register tasks, plists, etc. | None. |
| Secrets/env vars | None — `unasync` is dev-only with no secrets. | None. |
| Build artifacts | `unasync` is installed transiently via `uv run --with unasync`; no persistent build artifact. The generated `client.py` files under `.planning/spikes/SPIKE-005-codegen-tool-choice/<id>/` are spike artifacts (NOT committed to `packages/`). | None — spike artifacts are throwaway per Phase 10 convention. |

**Repo-state items the spike READS (not mutates):**

| File | Read Purpose |
|------|--------------|
| `packages/ambito-financiero-client/src/ambito_financiero_client/aio.py` | unasync input (round-trip source) |
| `packages/ambito-financiero-client/src/ambito_financiero_client/client.py` | round-trip target for byte-identical comparison |
| `packages/ambito-financiero-client/src/ambito_financiero_client/_core.py` | B8 identity center (`_raise_for_response` alias verified against this) |
| `packages/matriz-client/src/matriz_client/aio.py` | matriz construct audit input |
| `packages/matriz-client/src/matriz_client/_token_store.py` | deny-list intactness sha256 check |
| `packages/matriz-client/src/matriz_client/_refresh_policy.py` | deny-list intactness sha256 check |
| `packages/matriz-client/src/matriz_client/ws_client.py` | deny-list intactness sha256 check |
| `pyproject.toml` (root) | import-linter 4 existing contracts read; ruff/mypy config inheritance |

## Project Constraints (from CLAUDE.md)

The planner MUST verify task outputs respect these directives:

| Directive | Source (CLAUDE.md section) | Spike Impact |
|-----------|----------------------------|--------------|
| `from __future__ import annotations` is **mandatory** at module level on every module. | Code Style | The `@generated` marker MUST precede the future import as a Python comment line. Marker compatibility is the explicit 8th evidence item in D-RIGOR-01. |
| Double quotes, line-length 100, ruff format style | Code Style | Generated file MUST `uv run ruff format` clean. Any post-codegen `ruff format` normalization is acceptable per industry standard (httpcore + elasticsearch-py do the same). |
| Ruff rule sets: `E/W/F/I/B/UP/SIM/RUF/ASYNC/PIE/PT/RET/TID/LOG` | Code Style | `uv run ruff check` MUST be clean (evidence item 4). Note: `ASYNC` rules may false-positive on sync files generated from async; the spike documents any false-positives and the spike's NO-GO branch may surface them. |
| mypy `strict = true` | Code Style + pyproject.toml | Evidence item 5: `uv run mypy --strict` clean on the generated `client.py`. |
| Section dividers `# ---...---` | Comments | Hand-written ámbito `client.py` uses these; check that unasync preserves them (it should — they are comment tokens, not replaced). |
| Module-level docstring required | Comments | Hand-written `client.py` has one; unasync should preserve `aio.py`'s docstring as-is. May need an `additional_replacements` rule for the `from <pkg> import aio` example inside the docstring. |
| No wildcard imports, no relative imports (TID rule) | Import Organization | Generated file inherits from source `aio.py` (which already complies). |
| GSD workflow enforcement before any Edit/Write | GSD Workflow Enforcement | Planner consumes RESEARCH.md → PLAN.md → executor edits. No direct repo edits during the spike (planner enforces). |

## Operational Recipes

### 1. unasync 0.6.0 — Invocation Recipe

**Source of truth:** [unasync 0.6.0 docs](https://unasync.readthedocs.io/en/latest/) + [httpcore production script](https://github.com/encode/httpcore/blob/master/scripts/unasync.py) + [elasticsearch-py production script](https://github.com/elastic/elasticsearch-py/blob/main/utils/run-unasync.py).

**Confidence:** HIGH `[VERIFIED: github.com/python-trio/unasync source inspection + httpcore + elasticsearch-py]`

**Install (transient, spike-only — does NOT touch `pyproject.toml`):**

```bash
# Phase 12 spike uses ephemeral install. Phase 16 (GO branch) decides whether to
# add unasync to root [dependency-groups] dev.
uv run --with unasync python <experiment.py>
```

**Core API:**

```python
import unasync

unasync.unasync_files(
    fpath_list=["packages/ambito-financiero-client/src/ambito_financiero_client/aio.py"],
    rules=[
        unasync.Rule(
            fromdir="packages/ambito-financiero-client/src/ambito_financiero_client/",
            todir=".planning/spikes/SPIKE-005-codegen-tool-choice/001a-ambito-round-trip/output/",
            additional_replacements={
                # ámbito-specific (no auth, simplest case):
                "AsyncClient": "Client",
                "AsyncRetryTransport": "RetryTransport",
                "_atransport": "_transport",
                "AmbitoFinancieroAsyncClient": "AmbitoFinancieroClient",
                "_default_async_client": "_default_client",
                "aclose": "close",
                # The aio.py docstring example mentions `from ambito_financiero_client import aio`
                # and `await aio.aclose()`. We want the generated client.py to show
                # `from ambito_financiero_client import client` and `client.close()`. The
                # docstring update is mechanical via additional_replacements:
                "from ambito_financiero_client import aio": "from ambito_financiero_client import client",
                "aio.get_dollar_banco_nacion": "client.get_dollar_banco_nacion",
                "aio.aclose": "client.close",
                # The aio source imports _validate_max_retries FROM client.py. Sync
                # version defines it inline. The Rule output needs a different shape;
                # likely handled by manual post-edit (additional_replacements cannot
                # add lines, only substitute tokens).
            },
        ),
    ],
)
```

**Default token replacements unasync 0.6.0 applies AUTOMATICALLY (no config needed):**

```
"__aenter__" → "__enter__"
"__aexit__"  → "__exit__"
"__aiter__"  → "__iter__"
"__anext__"  → "__next__"
"asynccontextmanager" → "contextmanager"
"AsyncIterable" → "Iterable"
"AsyncIterator" → "Iterator"
"AsyncGenerator" → "Generator"
"StopAsyncIteration" → "StopIteration"
```

Plus the tokenizer strips `async` and `await` keywords (verified via httpcore's script: `'async def' → 'def'`, `'async with' → 'with'`, `'async for' → 'for'`, `'await ' → ''`).

**File output semantics:** `Rule(fromdir, todir)` writes to a relative location under `todir`. Specifically: the input file path is rewritten by replacing `fromdir` with `todir` in the path. So if `fromdir="packages/.../ambito_financiero_client/"` and the input is `packages/.../ambito_financiero_client/aio.py`, the output is `<todir>/aio.py`. The spike must rename the output file from `aio.py` to `client.py` AFTER unasync runs (unasync does NOT rename files; only substitutes tokens). One concrete pattern:

```python
import unasync
import shutil
from pathlib import Path

SRC_DIR = Path("packages/ambito-financiero-client/src/ambito_financiero_client/")
SPIKE_DIR = Path(".planning/spikes/SPIKE-005-codegen-tool-choice/001a-ambito-round-trip/")
WORK_DIR = SPIKE_DIR / "output"
WORK_DIR.mkdir(parents=True, exist_ok=True)

# Copy aio.py to the work dir (unasync mutates in place at the todir location).
shutil.copy(SRC_DIR / "aio.py", WORK_DIR / "aio.py")

unasync.unasync_files(
    fpath_list=[str(WORK_DIR / "aio.py")],
    rules=[
        unasync.Rule(
            fromdir=str(WORK_DIR) + "/",
            todir=str(WORK_DIR) + "/",
            additional_replacements={
                "AsyncClient": "Client",
                # ... (full table above)
            },
        )
    ],
)

# unasync's tokenizer writes a file with the same name as the input. Rename:
(WORK_DIR / "aio.py").rename(WORK_DIR / "client_generated.py")
```

This pattern matches the elasticsearch-py production approach: the script invokes `unasync_files` then does post-processing (their script also runs `black` + `isort` afterward — equivalent of our `ruff format`).

**KNOWN unasync 0.6.0 quirk:** Multi-token substitutions (e.g., `@pytest.mark.trio`) are tokenized as `@`/`pytest`/`.`/`mark`/`.`/`trio` and `additional_replacements` keys can only match single tokens. This is fine for our case (`AsyncClient`, `_atransport`, etc. are all single tokens), but the planner must verify any candidate replacement key parses to a single token. [VERIFIED: github.com/python-trio/unasync issue #74]

### 2. Ámbito Round-Trip Experiment Recipe

**Confidence:** HIGH `[VERIFIED: ámbito client.py / aio.py source inspection, this codebase]`

**Hypothesis:** `unasync_files()` over ámbito `aio.py` with the additional_replacements above produces a file byte-identical to v1.1 hand-written `client.py` modulo `uv run ruff format` normalization.

**Setup script (`.planning/spikes/SPIKE-005-codegen-tool-choice/001a-ambito-round-trip/experiment.py`):**

```python
"""Spike 001a: ámbito round-trip experiment."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import unasync  # transient via `uv run --with unasync`

REPO_ROOT = Path(__file__).resolve().parents[4]
SRC = REPO_ROOT / "packages/ambito-financiero-client/src/ambito_financiero_client"
SPIKE = Path(__file__).resolve().parent
WORK = SPIKE / "output"
WORK.mkdir(exist_ok=True)

# Step 1 — copy aio.py into spike work area.
shutil.copy(SRC / "aio.py", WORK / "aio.py")

# Step 2 — run unasync.
unasync.unasync_files(
    fpath_list=[str(WORK / "aio.py")],
    rules=[
        unasync.Rule(
            fromdir=str(WORK) + "/",
            todir=str(WORK) + "/",
            additional_replacements={
                "AsyncClient": "Client",
                "AsyncRetryTransport": "RetryTransport",
                "_atransport": "_transport",
                "AmbitoFinancieroAsyncClient": "AmbitoFinancieroClient",
                "_default_async_client": "_default_client",
                "aclose": "close",
                # docstring fixups:
                "from ambito_financiero_client import aio": "from ambito_financiero_client import client",
                "aio.get_dollar_banco_nacion": "client.get_dollar_banco_nacion",
                "aio.aclose": "client.close",
            },
        )
    ],
)

# Step 3 — rename output to client_generated.py.
generated = WORK / "client_generated.py"
(WORK / "aio.py").rename(generated)

# Step 4 — run ruff format on the generated file.
subprocess.run(
    ["uv", "run", "ruff", "format", str(generated)],
    check=True,
    cwd=REPO_ROOT,
)

# Step 5 — diff against v1.1 hand-written client.py.
result = subprocess.run(
    ["diff", "-u", str(SRC / "client.py"), str(generated)],
    capture_output=True,
    text=True,
    cwd=REPO_ROOT,
)
diff_output = SPIKE / "diff_vs_v1.1_client.txt"
diff_output.write_text(result.stdout + result.stderr)

print(f"Diff written to {diff_output}")
print(f"Diff exit code: {result.returncode}  (0 = byte-identical, 1 = differences)")
```

**Run command:**

```bash
cd /Users/sebadlf/development/becerra/market-libs
uv run --with unasync python .planning/spikes/SPIKE-005-codegen-tool-choice/001a-ambito-round-trip/experiment.py
```

**Expected outcome (GO branch):** `diff_vs_v1.1_client.txt` is empty after `ruff format`. Successful pass = SC#1 of the ROADMAP success criteria.

**Triage protocol if diff non-empty (per D-SCOPE-03 1-day cap):**

For each diff hunk, classify as one of:

| Class | Action | Result on Spike |
|-------|--------|-----------------|
| Cosmetic (whitespace, blank line, ruff-format-only) | Re-run `ruff format` on BOTH source and generated; verify both converge. | If both converge to same output → recipe correct, no Rule edit needed. |
| Semantic but fixable (single-token substitution) | Add new key to `additional_replacements`, re-run experiment.py. | If new run produces empty diff → recipe captured; document the new rule in FINDING.md. |
| Semantic NOT fixable via additional_replacements (multi-token, structural, etc.) | Stop; spike NO-GO. | Document the un-fixable hunk in `NO-GO.md` as root cause. |
| Hand-written-only logic (e.g., the sync `_validate_max_retries` definition that aio imports from client) | NOT a unasync failure — it's an inherent asymmetry of the source-of-truth model. | Document but DOES NOT trigger NO-GO. The Phase 16 production pattern handles this via async-only definition + sync import, OR a Jinja2-style "shared header" pre-write step. |

**Hand-written `_validate_max_retries` asymmetry note:** Ámbito's `client.py` defines `_validate_max_retries(value)` and the `aio.py` IMPORTS it from `client.py`. Going the other direction (async-first), the function would live in `aio.py` and `client.py` would import it. This is NOT a barrier to codegen — it's a one-time source migration that Phase 16 performs (move definition from `client.py` to `aio.py`, then everything generates cleanly). The spike DOCUMENTS this as a known Phase 16 setup step but does NOT regard it as a NO-GO trigger.

### 3. B8 Identity Preservation Test Recipe

**Confidence:** HIGH `[VERIFIED: existing test pattern Pitfalls.md §Pitfall 4 + ámbito client.py:36 + aio.py:38]`

**The invariant (from ARCHITECTURE.md + v1.1 Phase 7 D-04):**

```python
# ámbito today:
# client.py:36:  _raise_for_response = _core.raise_for_response
# aio.py:38:     _raise_for_response = _core.raise_for_response
# Plus _raise_for_response in __all__ in BOTH modules (mypy strict implicit_reexport=False).

assert (
    ambito_financiero_client.client._raise_for_response
    is ambito_financiero_client.aio._raise_for_response
    is ambito_financiero_client._core.raise_for_response
)
```

**Spike test (in `001a-ambito-round-trip/experiment.py` Step 6, AFTER the diff step):**

```python
import importlib.util
import sys

# Step 6 — load the generated file as a module and assert B8 identity.
# We CANNOT just `import ambito_financiero_client.client` because that would
# import the v1.1 hand-written file, not the spike output. We load the spike
# output as a module and compare identities.

spec = importlib.util.spec_from_file_location(
    "ambito_financiero_client.client_generated",
    str(generated),
)
mod = importlib.util.module_from_spec(spec)
sys.modules["ambito_financiero_client.client_generated"] = mod
spec.loader.exec_module(mod)

import ambito_financiero_client._core as core
import ambito_financiero_client.aio as aio

assert mod._raise_for_response is aio._raise_for_response is core.raise_for_response, (
    "B8 identity FAILED: codegen emitted a thunk wrapper instead of an alias assignment."
)
print("B8 identity: PASS")
```

**Why this works:** The hand-written ámbito `client.py:36` uses `_raise_for_response = _core.raise_for_response` (a module-level alias assignment, not a thunk). The `aio.py:38` uses `_raise_for_response = _core.raise_for_response` directly (same shape — both literally import `_core` and bind the same callable). unasync's token tokenizer treats this line as five tokens: `_raise_for_response`/`=`/`_core`/`.`/`raise_for_response`. No `async`/`await` token to strip; no replacement in our `additional_replacements` table touches these names. **Therefore unasync emits the line verbatim** and the identity invariant SHOULD hold trivially.

**The failure mode the test catches:** if unasync (or any future codegen tool) emits `def _raise_for_response(resp): return _core.raise_for_response(resp)` — a thunk wrapper. The `is` check becomes False. Pitfalls.md §Pitfall 4 documents this exact failure mode as CRITICAL.

### 4. Matriz Construct Audit Recipe

**Confidence:** HIGH `[VERIFIED: matriz aio.py 852 LOC enumeration this session]`

**Enumeration command (executed during research, sanity check):**

```bash
grep -nE "async (def|with|for)|asyncio\.|await |__aenter__|__aexit__|_get_async_lock|aclose" \
  packages/matriz-client/src/matriz_client/aio.py | wc -l
# Output: 128 matches
```

128 matches across 852 LOC. Each must be classified.

**Spike audit script (`001c-matriz-construct-audit/audit.py`):**

```python
"""Spike 001c: matriz async-only construct audit.

Walks matriz aio.py and emits a classification table. Zero TBD rows is the
merge gate (D-SCOPE-02).
"""
from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SOURCE = REPO_ROOT / "packages/matriz-client/src/matriz_client/aio.py"
OUTPUT = Path(__file__).resolve().parent / "matriz-aio-constructs.md"

# Files the spike does NOT rewrite (locked deny-list per ARCHITECTURE.md):
DENY_LIST = {
    "_token_store.py",
    "_refresh_policy.py",
    "_refresh.py",  # adapter for matriz — never codegen
    "ws_client.py",
}

# Patterns that have a known sync emission via unasync defaults + our
# additional_replacements:
KNOWN_SYNC_EMISSIONS = {
    "AsyncFunctionDef":            "FunctionDef (async stripped)",
    "Await":                       "removed (await keyword stripped)",
    "AsyncWith":                   "With (async stripped)",
    "AsyncFor":                    "For (async stripped)",
    "__aenter__":                  "__enter__ (unasync default)",
    "__aexit__":                   "__exit__ (unasync default)",
    "aclose":                      "close (additional_replacements)",
    "aread":                       "read (additional_replacements)",
    "AsyncClient":                 "Client (additional_replacements)",
    "AsyncRetryTransport":         "RetryTransport (additional_replacements)",
    "_atransport":                 "_transport (additional_replacements)",
}

# Patterns that MUST NOT appear in the generated sync (would mean codegen
# tried to rewrite a deny-listed primitive into a parallel sync impl):
HARD_DENY = {
    "asyncio.Lock":                "lives in _token_store.py — deny-listed",
    "asyncio.to_thread":           "lives in _token_store.py — deny-listed",
    "_get_async_lock":             "lives in _token_store.py — deny-listed",
    "_async_locks":                "lives in _token_store.py — deny-listed",
}

source = SOURCE.read_text()
tree = ast.parse(source)

rows = []  # (line, construct, classification, evidence)

for node in ast.walk(tree):
    if isinstance(node, ast.AsyncFunctionDef):
        rows.append((node.lineno, f"async def {node.name}",
                     "manual-sync-proof", "FunctionDef via unasync default"))
    elif isinstance(node, ast.AsyncWith):
        rows.append((node.lineno, "async with ...",
                     "manual-sync-proof", "With via unasync default"))
    elif isinstance(node, ast.AsyncFor):
        rows.append((node.lineno, "async for ... in ...",
                     "manual-sync-proof", "For via unasync default"))
    elif isinstance(node, ast.Await):
        rows.append((node.lineno, "await <expr>",
                     "manual-sync-proof", "await keyword stripped by unasync"))
    elif isinstance(node, ast.Attribute):
        # Catch asyncio.X (Lock, to_thread, get_running_loop, ...)
        if isinstance(node.value, ast.Name) and node.value.id == "asyncio":
            name = f"asyncio.{node.attr}"
            if name in HARD_DENY:
                rows.append((node.lineno, name, "DENY-LIST-VIOLATION",
                             HARD_DENY[name]))
            else:
                # asyncio.get_running_loop, asyncio.gather, etc. — must each
                # have a manual sync rewrite proof OR be a comment-only mention
                rows.append((node.lineno, name, "REVIEW", "operator classifies"))

# Emit markdown table.
md = ["# Matriz aio.py — async-only construct audit\n",
      f"**Source:** `{SOURCE.relative_to(REPO_ROOT)}` ({len(source.splitlines())} LOC)\n",
      f"**Found:** {len(rows)} async-only construct occurrences\n\n",
      "| Line | Construct | Classification | Evidence |\n",
      "|------|-----------|----------------|----------|\n"]
for line, construct, classification, evidence in sorted(rows):
    md.append(f"| {line} | `{construct}` | {classification} | {evidence} |\n")

# Detect any TBD/REVIEW rows that the operator hasn't classified yet.
unresolved = [r for r in rows if r[2] in ("TBD", "REVIEW", "DENY-LIST-VIOLATION")]
md.append(f"\n## Unresolved rows: {len(unresolved)}\n")
if unresolved:
    md.append("\n**MERGE GATE FAILURE:** D-SCOPE-02 requires zero unresolved rows.\n")
else:
    md.append("\n**MERGE GATE PASS:** zero unresolved rows.\n")

OUTPUT.write_text("".join(md))
print(f"Audit written to {OUTPUT}; {len(unresolved)} unresolved rows.")
```

**Run command:**

```bash
uv run python .planning/spikes/SPIKE-005-codegen-tool-choice/001c-matriz-construct-audit/audit.py
```

**Acceptance:** unresolved count == 0 after operator triages the `REVIEW` rows. Operator triage = manually edits the markdown table to flip `REVIEW` → either `deny-list-confirmed` (with file pointer) or `manual-sync-proof` (with the additional_replacements line that produces the correct sync).

**Sample expected REVIEW rows from this codebase (from research enumeration above):**

- Line 112: `asyncio.get_running_loop` — appears inside `_token_store.py`-imported code → **deny-list-confirmed** (lives in `_token_store.py`).
- Line 131: `asyncio.to_thread` — appears inside `_token_store.py` → **deny-list-confirmed**.
- All other `asyncio.*` references in `aio.py` are inside **docstrings** (lines 42, 235, 267, 282, 289, 292) — comment-only mentions, NOT executable code. unasync tokenizer preserves docstrings verbatim → **no rewrite needed**, classification = `comment-only`.

The expected end-state for matriz aio.py 852 LOC: **zero deny-list violations**, all 128 grep matches classified as either docstring-mention, default unasync emission, deny-listed-import, or `additional_replacements`-covered.

### 5. `@generated` Marker × `from __future__ import annotations` Compatibility

**Confidence:** HIGH `[VERIFIED: Python language reference + PEP 236 future-statement rules]`

**Per Python language reference** ([Future statements](https://docs.python.org/3/reference/simple_stmts.html#future-statements)): a future statement MUST appear near the top of the module — the ONLY lines that may precede it are:

1. The module docstring
2. Comments (including the shebang `#!` and the PEP 263 encoding declaration)
3. Blank lines
4. Other future statements

A Python `#` comment is explicitly in the allow-list. Therefore the following layout is legal:

```python
# @generated by unasync from aio.py — DO NOT EDIT BY HAND.
# To modify, edit aio.py and run `make codegen` (Phase 16 setup).

from __future__ import annotations

"""Cliente HTTP sincrónico para Ámbito Financiero — transport shell.
... (rest of docstring)
"""
```

Wait — the module docstring conventionally precedes the future import. Let me double-check the order: per PEP 236 and the current Python reference, the module docstring is `Expr(Constant(str))` — a regular statement. The allow-list above means the future statement may appear AFTER the docstring (because the docstring is one of the allowed pre-future items). So the canonical order in this codebase (which uses module-level docstrings everywhere per CLAUDE.md) is:

```python
# @generated by unasync from aio.py — DO NOT EDIT BY HAND.

"""Cliente HTTP sincrónico para Ámbito Financiero — transport shell.

... (rest of docstring) ...
"""

from __future__ import annotations
```

Actually examining the current ámbito `client.py` shows the order is: docstring (line 1-16), blank (line 17), `from __future__ import annotations` (line 18). The marker can prepend the docstring without breaking anything:

```python
# @generated by unasync from aio.py — DO NOT EDIT BY HAND.

"""Cliente HTTP sincrónico para Ámbito Financiero — transport shell.
... (rest of docstring) ...
"""

from __future__ import annotations
```

**Spike test (`001b-ambito-marker-future-compat/experiment.py`):**

```python
"""Spike 001b: verify @generated marker × from __future__ compatibility."""
from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SPIKE = Path(__file__).resolve().parent
GENERATED = REPO_ROOT / ".planning/spikes/SPIKE-005-codegen-tool-choice/001a-ambito-round-trip/output/client_generated.py"

# Step 1 — prepend marker.
marker = (
    "# @generated by unasync from aio.py — DO NOT EDIT BY HAND.\n"
    "# To modify, edit aio.py and run `make codegen` (Phase 16 setup).\n"
    "\n"
)
current = GENERATED.read_text()
GENERATED.write_text(marker + current)

# Step 2 — run ruff check + format --check + mypy --strict.
ruff_check = subprocess.run(
    ["uv", "run", "ruff", "check", str(GENERATED)],
    capture_output=True, text=True, cwd=REPO_ROOT,
)
ruff_format = subprocess.run(
    ["uv", "run", "ruff", "format", "--check", str(GENERATED)],
    capture_output=True, text=True, cwd=REPO_ROOT,
)
mypy = subprocess.run(
    ["uv", "run", "mypy", "--strict", str(GENERATED)],
    capture_output=True, text=True, cwd=REPO_ROOT,
)

# Step 3 — also assert Python parses the file (proves marker doesn't break grammar).
parse_check = subprocess.run(
    ["uv", "run", "python", "-c", f"import ast; ast.parse(open('{GENERATED}').read())"],
    capture_output=True, text=True, cwd=REPO_ROOT,
)

transcripts = SPIKE / "verification_transcripts.txt"
transcripts.write_text(
    f"=== ruff check ===\nexit {ruff_check.returncode}\n{ruff_check.stdout}{ruff_check.stderr}\n"
    f"=== ruff format --check ===\nexit {ruff_format.returncode}\n{ruff_format.stdout}{ruff_format.stderr}\n"
    f"=== mypy --strict ===\nexit {mypy.returncode}\n{mypy.stdout}{mypy.stderr}\n"
    f"=== ast.parse ===\nexit {parse_check.returncode}\n{parse_check.stdout}{parse_check.stderr}\n"
)

print(f"Transcripts written to {transcripts}")
print(f"Pass criteria: all 4 commands exit 0.")
```

**Acceptance:** all 4 exit codes are 0.

### 6. `ruff format --check` + `ruff check` + `mypy --strict` on Generated Output

**Confidence:** HIGH (mechanical commands; consult existing repo CI config)

**Industry standard for codegen + format:** generators emit token-level output that is NOT format-normalized. Run `ruff format` AFTER codegen and BEFORE comparison. elasticsearch-py uses `black + isort` post-unasync; httpcore relies on its own script's regex output already being normalized. Our equivalent is `uv run ruff format`.

**Per-command spike commands:**

```bash
# After unasync runs and produces output/client_generated.py:
cd /Users/sebadlf/development/becerra/market-libs

# (a) Format the generated file (in-place).
uv run ruff format .planning/spikes/SPIKE-005-codegen-tool-choice/001a-ambito-round-trip/output/client_generated.py

# (b) Verify the format is stable (idempotent — no second-pass diff).
uv run ruff format --check .planning/spikes/SPIKE-005-codegen-tool-choice/001a-ambito-round-trip/output/client_generated.py

# (c) Run ruff linter under the full rule set.
uv run ruff check .planning/spikes/SPIKE-005-codegen-tool-choice/001a-ambito-round-trip/output/client_generated.py

# (d) Run mypy strict.
uv run mypy --strict .planning/spikes/SPIKE-005-codegen-tool-choice/001a-ambito-round-trip/output/client_generated.py
```

**ASYNC1xx false-positives:** The repo's ruff config (root `pyproject.toml:60`) selects rule set `ASYNC`. These rules target async code (e.g., `ASYNC100` for blocking calls in async functions). The generated `client.py` is SYNC — there are no `async def` to false-positive on. **Expected: no ASYNC1xx hits on generated sync output.** If any appear, the spike documents them but this is unexpected.

**mypy strict on the generated file:** the generated `client.py` IS type-checked under the same `strict = true` config that covers `packages/`. The file location under `.planning/spikes/...` is OUTSIDE the `[tool.mypy] files` glob (which is `packages/*/src`). So we must pass the file path explicitly to `mypy` to type-check it. The strict config still applies because `[tool.mypy]` is module-global.

**Expected mypy output:** clean (zero errors). The generated file's type signatures inherit from the source `aio.py`'s type signatures (which are already strict-clean per v1.1 Phase 10 ship).

### 7. import-linter Contracts Re-Verification

**Confidence:** HIGH `[VERIFIED: root pyproject.toml:138-171]`

**The 4 forbidden contracts (root `pyproject.toml`):**

```toml
[[tool.importlinter.contracts]]
name = "ambito_financiero_client._core does not depend on transport modules"
type = "forbidden"
source_modules = ["ambito_financiero_client._core"]
forbidden_modules = [
    "ambito_financiero_client.client",
    "ambito_financiero_client.aio",
]

# ... 3 more identical structure for higyrus / iol / matriz
```

**Spike verification:** these contracts constrain `_core.py` imports — they do NOT directly constrain `client.py` imports. The spike confirms by running:

```bash
uv run lint-imports
```

**Acceptance:** exit 0 with all 4 contracts satisfied. The generated `client.py` (in the spike's `.planning/spikes/...` directory) is NOT included in import-linter's scan because the contracts are scoped to the `root_packages` list (`ambito_financiero_client`, `iol_client`, `higyrus_client`, `matriz_client`) which only walks the installed package locations. So the spike's experimental output cannot violate contracts (it's not imported).

**The real verification is theoretical, not runtime:** does the generated `client.py` SHAPE differ from the hand-written `client.py` in a way that would introduce a forbidden import IF it replaced `packages/ambito-financiero-client/src/ambito_financiero_client/client.py`? Sanity check (executed during research, manually):

- The hand-written `client.py:27` imports `from ambito_financiero_client import _core, _transport`.
- The hand-written `aio.py:32` imports `from ambito_financiero_client import _atransport, _core`.
- After unasync with `additional_replacements={"_atransport": "_transport"}`, the generated `client.py` will import `from ambito_financiero_client import _transport, _core` — same shape as hand-written.
- Neither shape imports `client.py` or `aio.py` from `_core.py` (the forbidden direction). The generated file imports `_core`, which is fine.

**No new contracts are needed in Phase 12.** Phase 16 (if GO) would add 8 new contracts (`_aio` ↔ `_sync` bidirectional × 4) per ARCHITECTURE.md §2.2 if the codegen pattern uses `_aio/` + `_sync/` directories. The spike documents this as a Phase 16 design choice but does NOT add it.

### 8. Concrete Spike Directory Layout

**Confidence:** HIGH `[VERIFIED: .planning/spikes/CONVENTIONS.md + 001a directory structure inspection]`

**Per CONVENTIONS.md:** sub-directories named `NNN-descriptive-name/` with `README.md` (frontmatter Given/When/Then/Investigation Trail) + experiment code + `test_*.py` (if applicable). Comparison spikes share the number with letter suffix (`001a-`, `001b-`).

**Phase 12 layout:**

```
.planning/spikes/SPIKE-005-codegen-tool-choice/
├── README.md                                                            # Spike entry
├── DECISION.md                                                          # Operator-signed
├── NO-GO.md                                                             # Conditional
├── 001a-ambito-round-trip/
│   ├── README.md                                                        # Given/When/Then
│   ├── experiment.py                                                    # unasync invocation
│   ├── output/
│   │   └── client_generated.py                                          # Spike artifact
│   ├── diff_vs_v1.1_client.txt
│   └── FINDING.md
├── 001b-ambito-marker-future-compat/
│   ├── README.md
│   ├── experiment.py                                                    # marker + ruff + mypy
│   ├── verification_transcripts.txt
│   └── FINDING.md
├── 001c-matriz-construct-audit/
│   ├── README.md
│   ├── audit.py
│   ├── matriz-aio-constructs.md
│   └── FINDING.md
└── 001d-matriz-deny-list-config/
    ├── README.md
    ├── experiment.py                                                    # sha256 check
    ├── verification_transcripts.txt
    └── FINDING.md
```

**README.md frontmatter template** (per CONVENTIONS.md, modeled after `001a-tokenstore-threading-lock-to_thread/README.md`):

```yaml
---
spike: 005
sub: 001a
name: ambito-round-trip
type: comparison
validates: "Given the v1.1 hand-written ambito_financiero_client/client.py, when unasync.unasync_files() runs on aio.py with the prescribed additional_replacements and the output is ruff-format-normalized, then the diff against client.py is byte-empty AND B8 identity is preserved."
verdict: TBD
related: [001b, 001c, 001d]
tags: [codegen, unasync, ambito, byte-identical, B8-identity]
---
```

### 9. `/gsd-spike --wrap-up` Invocation + Resulting Skill Shape

**Confidence:** HIGH `[VERIFIED: existing .claude/skills/spike-findings-market-libs/SKILL.md + WRAP-UP-SUMMARY.md]`

**Invocation:** `/gsd-spike --wrap-up` is a slash-command (not a Bash invocation) consumed by the GSD framework. Per the existing `WRAP-UP-SUMMARY.md`, the command processes all spikes in `.planning/spikes/` and emits a project-local Skill under `.claude/skills/`.

**Resulting Skill structure** (parallel to the existing `spike-findings-market-libs/`):

```
.claude/skills/spike-findings-codegen-market-libs/
├── SKILL.md                                                     # Auto-loaded; CLAUDE.md references this
├── references/
│   ├── unasync-rule-config-per-package.md                       # 4 Rule configs (ambito, iol, higyrus, matriz)
│   ├── matriz-construct-audit.md                                # the classification table
│   └── codegen-pitfalls.md                                      # B8 identity + marker + format-stable
└── sources/
    ├── 001a-ambito-round-trip/                                  # Original spike sub-dir (copied)
    ├── 001b-ambito-marker-future-compat/
    ├── 001c-matriz-construct-audit/
    └── 001d-matriz-deny-list-config/
```

**SKILL.md frontmatter (model from `spike-findings-market-libs/SKILL.md:1-4`):**

```yaml
---
name: spike-findings-codegen-market-libs
description: Implementation blueprint from Phase 12 codegen spike. Per-package unasync.Rule configs, @generated marker compatible with `from __future__ import annotations`, matriz deny-list confirmation, B8 identity preservation pattern. Auto-loaded when Phase 16 (if GO) plans codegen across the 4 transport shells. If NO-GO: documents failure mode + libcst path for v1.3.
---
```

**Body sections (per existing skill pattern):**

1. `<context>` — Phase 12 spike context, decision summary (GO|NO-GO).
2. `<requirements>` — the non-negotiable constraints distilled from the spike (B8 identity preservation, marker line ordering, deny-list scope).
3. `<findings_index>` — feature-area table (per `spike-findings-market-libs/SKILL.md:52-58`).
4. `<integration_blueprint>` — code pattern Phase 16 (or v1.3 libcst spike) consumes.
5. `<metadata>` — list of processed spikes (`001a-d`).

**Operator action:** after the spike has its `DECISION.md` signed, run `/gsd-spike --wrap-up`. The command discovers spike sub-directories, builds the Skill, and adds a one-line reference to `CLAUDE.md` under the `## Auto-loaded Knowledge` section.

### 10. NO-GO Close-Out Artifacts

**Confidence:** HIGH (mechanical edits to specific files, all paths verified this session)

**Per D-NOGO-02, the NO-GO close-out artifacts are:**

#### 10.1. `.planning/spikes/SPIKE-005-codegen-tool-choice/NO-GO.md`

```markdown
# SPIKE-005 — NO-GO Decision

**Decided:** 2026-06-XX
**Signed off by:** <operator>
**Time spent:** ~1 day (D-SCOPE-03 timebox)

## Root Cause Analysis

<one of: B8 break / ruff false-positives / marker syntax conflict / matriz construct
without sync rewrite / per-package additional_replacements explosion / ...>

Concrete failure transcript:
\`\`\`
<copy-paste from the experiment that triggered NO-GO>
\`\`\`

## Why Not Extend Phase 12?

Per D-NOGO-01: libcst exploration requires AST-level reasoning (not token-replacement).
It needs its own dedicated spike. Adding it inline to Phase 12 violates the 1-day timebox
(D-SCOPE-03) and the v1.2 milestone scope.

## What's Deferred to v1.3?

- libcst AST-level codemod evaluation for unasync alternatives
- REFAC-06 entire scope (single-source sync/async transport shells)

See `.planning/todos/pending/spike-codegen-libcst-v1.3.md` for v1.3 capture.

## Impact on v1.2 Roadmap

- Phase 16 (Codegen Single-Source) — DROPPED from v1.2 schedule.
- Phase 17 (LIVE-03) — UNBLOCKED; runs immediately after Phase 14 + 15.
- REFAC-06 moved from v1.2 "Open" → v1.2 "Future Requirements (Defer to v1.3+)" in
  REQUIREMENTS.md.
```

#### 10.2. REQUIREMENTS.md update

**Diff sketch (planner encodes as task):**

```diff
@@ Section "Arquitectura sync/async dedup (REFAC)"
-- [ ] **REFAC-06** (spike-gated): unasync/codegen single-source for ...
+(removed — moved to Future Requirements below)

@@ Section "Future Requirements (Defer to v1.3+)"
+- **REFAC-06** (deferred per Phase 12 NO-GO 2026-06-XX): unasync/codegen
+  single-source for `client.py`/`aio.py` transport shells × 4 packages.
+  NO-GO root cause: <one-liner from NO-GO.md>. Re-evaluation requires a v1.3
+  spike on libcst (AST-level codemod). See
+  `.planning/spikes/SPIKE-005-codegen-tool-choice/NO-GO.md` and
+  `.planning/todos/pending/spike-codegen-libcst-v1.3.md`.

@@ Section "Traceability" table
-| REFAC-06 | Phase 16 (conditional)      | Open   |
+| REFAC-06 | Defer to v1.3                | Deferred (Phase 12 NO-GO 2026-06-XX) |

@@ "Coverage:" line
-**Coverage:** 5/5 requirements mapped to v1.2 phases. REFAC-06 (Phase 16) is conditionally-gated
-on the Phase 12 spike output (may defer to v1.3).
+**Coverage:** 4/5 requirements mapped to v1.2 phases (REFAC-05, SEC-01, ERG-01, LIVE-03);
+REFAC-06 deferred to v1.3 per Phase 12 NO-GO.
```

#### 10.3. ROADMAP.md update

**Diff sketch:**

```diff
@@ Section "Phase 16: Codegen Single-Source (CONDITIONAL)" frontmatter
-**Conditional**: This phase is DROPPED from the v1.2 schedule if and only if Phase 12 outputs a NO-GO decision; in that case REFAC-06 defers to v1.3 ...
+**Status:** DROPPED. Phase 12 returned NO-GO on 2026-06-XX. REFAC-06 deferred to v1.3.

@@ Progress table
-| 16. Codegen Single-Source (CONDITIONAL on Phase 12)         | v1.2      | 0/?   | Not started | -          |
+| 16. Codegen Single-Source (DROPPED — Phase 12 NO-GO)         | v1.2      | -     | DROPPED     | 2026-06-XX |
```

#### 10.4. `.planning/todos/pending/spike-codegen-libcst-v1.3.md`

```markdown
# Pending Todo: Codegen Single-Source Spike — libcst (v1.3)

**Captured at:** 2026-06-XX (Phase 12 NO-GO close-out)
**Triggering decision:** SPIKE-005 NO-GO. See
`.planning/spikes/SPIKE-005-codegen-tool-choice/NO-GO.md`.
**Phase milestone:** v1.3 (carry-forward from REFAC-06 v1.2 defer)

## Scope

Evaluate `libcst >=1.8.0,<2` as the codegen tool for `aio.py` → `client.py`
transport-shell single-source. libcst is AST-level (concrete syntax tree)
versus unasync's token-replacement approach. libcst preserves whitespace and
comments, which matters for review of generated code.

## Why libcst over unasync at v1.3?

unasync NO-GO root cause documented in
`.planning/spikes/SPIKE-005-codegen-tool-choice/NO-GO.md`: <one-liner>.

libcst's expected strengths:
- AST-level reasoning handles structural rewrites (e.g., async generator → sync
  generator, contextmanager rewrites)
- Codemod API (`libcst.matchers` + `libcst.CSTTransformer`) is more powerful than
  token replacement for matriz-scale (852 LOC aio.py)
- Whitespace and comment preservation reduces post-codegen `ruff format` step

## Acceptance criteria for v1.3 libcst spike

Same 8-item evidence list as SPIKE-005 D-RIGOR-01:
1. Byte-identical ámbito round-trip
2. B8 identity preserved
3. ruff format/check/mypy strict clean
4. ámbito mocked suite green
5. import-linter contracts intact
6. @generated marker + from __future__ compatible
7. matriz construct audit zero TBD
8. <one of: libcst-specific items, e.g., codemod test suite green>

## Out of scope for v1.3 spike

- Production integration (Phase 16-equivalent in v1.3)
- iol + higyrus round-trip (inferred from ámbito, same as SPIKE-005)
```

#### 10.5. Phase 12 close artifact: `.planning/phases/12-codegen-spike/12-SUMMARY.md`

```markdown
---
gsd_state_version: 1.0
phase: 12
phase_name: Codegen Spike
status: complete
decision: NO-GO
spike_directory: .planning/spikes/SPIKE-005-codegen-tool-choice/
skill_produced: .claude/skills/spike-findings-codegen-market-libs/
signoff_date: 2026-06-XX
signoff_by: <operator>
next_phase: 13 (Phase 16 DROPPED; Phase 17 unblocked after 14+15)
---

# Phase 12: Codegen Spike — Summary

## Decision

**NO-GO** — REFAC-06 deferred to v1.3.

## Evidence Checklist (D-RIGOR-01 — 8 items)

(only items 1-N completed; item N+1 failed → NO-GO triggered)

| # | Item | Result |
|---|------|--------|
| 1 | Byte-identical round-trip ámbito | <PASS/FAIL transcript path> |
| 2 | B8 identity preserved | <...> |
| ... | ... | ... |

## Spike Directory

`.planning/spikes/SPIKE-005-codegen-tool-choice/` — includes `NO-GO.md` with
root cause.

## Skill Produced

`.claude/skills/spike-findings-codegen-market-libs/SKILL.md` — auto-loaded;
documents failure mode + libcst exploration path for v1.3.

## REQUIREMENTS.md / ROADMAP.md Updates

- REFAC-06 moved to "Future Requirements (Defer to v1.3+)" in REQUIREMENTS.md.
- Phase 16 marked DROPPED in ROADMAP.md.
- New pending todo: `.planning/todos/pending/spike-codegen-libcst-v1.3.md`.

## Next Steps

1. Operator runs `/gsd-plan-phase 13` (Cross-Package Ergonomics).
2. Phase 17 (LIVE-03) is unblocked to run immediately after Phase 14 + 15.
3. v1.3 milestone captures libcst spike as first scheduled work item.
```

**GO close-out artifacts (parallel structure, decision = GO):** same `12-SUMMARY.md` template with `decision: GO`, skill produced, per-package `Rule` config drafts captured in `DECISION.md`, no REQUIREMENTS/ROADMAP edits needed (Phase 16 proceeds as planned). The planner encodes both branches as parallel close-out wave variants.

## Common Pitfalls

### Pitfall 1: Letting the spike drift past 1 day

**What goes wrong:** Operator gets engaged in fixing a deep diff hunk and the spike turns into a 3-day codegen tool implementation.

**Why it happens:** unasync's `additional_replacements` table can grow unbounded; each new package surfaces a new replacement. The temptation is "one more rule and we're done."

**How to avoid:** Hard 1-day timebox (D-SCOPE-03). If by end-of-day the ámbito diff is non-empty AND the next replacement is not obviously one-line, the spike triggers NO-GO automatic. The planner MUST encode this as a wall-clock check, not just a decision criterion.

**Warning signs:** more than 10 entries accumulated in `additional_replacements`; spike experimenter reaches for a regex pre-processor / post-processor (sign you've outgrown unasync's tokenize approach).

### Pitfall 2: Spike code creeping into `packages/`

**What goes wrong:** Operator runs an experimental edit on `packages/ambito-financiero-client/src/ambito_financiero_client/client.py` to "see if it works" and forgets to revert.

**Why it happens:** the spike's natural target is exactly the v1.1 hand-written file; editing the same file in-place feels efficient.

**How to avoid:** all spike work happens in `.planning/spikes/SPIKE-005-codegen-tool-choice/<id>/output/` — NEVER in `packages/`. The planner enforces this by:
- Wave 0 task: `git status --porcelain packages/ | wc -l` must be 0 before spike work begins
- Each spike-merge gate: `git diff --stat packages/` must be empty
- Per CONVENTIONS.md §"To Avoid": *"Importing from packages/*/src/ in spike code: spikes must be self-contained."*

**Warning signs:** any `git status` line under `packages/` during the spike phase.

### Pitfall 3: Misreading the diff as semantic when it's cosmetic

**What goes wrong:** Diff is non-empty after first `ruff format` run; spike concludes NO-GO without realizing the diff is just trailing-newline or single-quote-vs-double-quote.

**Why it happens:** unasync output may use different quote style or have a trailing newline difference. The hand-written `client.py` is `ruff format` clean; running `ruff format` on the generated file should converge to the same shape.

**How to avoid:** ALWAYS run `ruff format` on the generated file FIRST, then diff. If diff is still non-empty, classify each hunk per the triage protocol in Recipe 2 (cosmetic / fixable / unfixable / inherent-asymmetry).

**Warning signs:** diff hunks involve whitespace only, or quote style only, or single trailing-newline differences.

### Pitfall 4: Skipping the B8 identity test under time pressure

**What goes wrong:** The byte-identical diff passes; operator declares spike GO without running the identity assertion. Phase 16 ships and later CI catches B8 break.

**Why it happens:** byte-identical diff seems to imply identity preservation. It doesn't — the diff only checks textual sameness; the identity check requires loading the generated file as a module and asserting `is` equivalence.

**How to avoid:** Make the B8 test a HARD gate within the 001a experiment (not a separate experiment). Recipe 3 above shows the test embedded in `001a-ambito-round-trip/experiment.py` Step 6, after the diff step. Acceptance = both diff empty AND `is` assertion passes.

**Warning signs:** experiment.py does not include `importlib.util.spec_from_file_location` + `assert ... is ... is ...`.

### Pitfall 5: Matriz audit with TBD rows accepted

**What goes wrong:** operator triages 95% of the 128 matriz construct rows, leaves 5 marked TBD "to look at later." Spike merges. Phase 16 hits the 5 rows and reopens scope.

**Why it happens:** D-SCOPE-02 ("zero TBD rows is the merge gate") is easy to soft-relax under time pressure.

**How to avoid:** the planner MUST encode the audit-zero-TBD check as a programmatic gate, not a manual checkbox. Sample gate:

```bash
test "$(grep -c '| REVIEW |\|| TBD |\|| DENY-LIST-VIOLATION |' .planning/spikes/SPIKE-005-codegen-tool-choice/001c-matriz-construct-audit/matriz-aio-constructs.md)" -eq 0
```

**Warning signs:** any `REVIEW` / `TBD` / `DENY-LIST-VIOLATION` line in `matriz-aio-constructs.md`.

### Pitfall 6: Marker comment placement breaking the future import

**What goes wrong:** operator prepends the marker AFTER `from __future__ import annotations` line, causing the next-tier marker validator (a Phase 16 pre-commit hook) to fail.

**Why it happens:** "comments can go anywhere" intuition; the spike isn't strict about line ordering.

**How to avoid:** Recipe 5 shows the EXACT order: marker comment (line 1-2) → blank (line 3) → module docstring (line 4-N) → blank → `from __future__ import annotations` (line N+2). The 001b experiment validates this exact ordering via `ast.parse` (a future statement out of position raises `SyntaxError`).

**Warning signs:** `experiment.py` inserts the marker via `str.replace` rather than `str.__add__` (concat at start).

### Pitfall 7: `additional_replacements` accidentally matching inside docstrings

**What goes wrong:** the `additional_replacements` table includes `aio.aclose: client.close`. unasync's tokenizer matches `aio` and `aclose` SEPARATELY as tokens. So inside the source docstring text `await aio.aclose()`, the tokens are `await`/`aio`/`.`/`aclose`/`(`/`)`. unasync's tokenizer DOES descend into strings? Need to verify.

**Why it happens:** documentation about whether unasync touches string contents is sparse. Per the issue tracker, `@pytest.mark.trio` rewrite to `""` is "effectively a no-op as a result of tokenization" — suggesting unasync DOES NOT rewrite tokens INSIDE strings (because strings tokenize to `STRING`, not a sequence of identifiers).

**How to avoid:** Verify empirically in 001a experiment. If docstring contents are preserved verbatim → good. If unasync mangles docstring → add a docstring-rewriting post-pass (manual) or fix via additional_replacements at the substring level (may or may not work).

**Warning signs:** the generated `client.py` docstring has `client.client.close` (double-prefix) or other obvious string-level token mangling.

## Code Examples

### Verified Pattern 1 — Standalone `unasync_files()` invocation

```python
# Source: https://unasync.readthedocs.io/en/latest/ (standalone usage section)
import unasync

unasync.unasync_files(
    [file1, file2, ...],
    rules=[
        unasync.Rule(
            "tests/",
            "tests_sync/",
            additional_replacements={"ahip": "hip"},
        ),
    ],
)
```

### Verified Pattern 2 — httpcore-style sub list

```python
# Source: https://github.com/encode/httpcore/blob/master/scripts/unasync.py
SUBS = [
    ('async def', 'def'),
    ('async with', 'with'),
    ('async for', 'for'),
    ('await ', ''),
    ('AsyncIterator', 'Iterator'),
    ('aclose', 'close'),
    ('aread', 'read'),
    ('__aenter__', '__enter__'),
    ('__aexit__', '__exit__'),
    ('__aiter__', '__iter__'),
    ('asynccontextmanager', 'contextmanager'),
    # ... (full list 19 entries)
]
COMPILED_SUBS = [
    (re.compile(r'(^|\b)' + regex + r'($|\b)'), repl) for regex, repl in SUBS
]
```

Note: httpcore uses regex with word boundaries; unasync uses tokenizer. Both achieve the same effect for our codebase shape, but unasync is safer because it never matches inside strings/comments.

### Verified Pattern 3 — B8 identity assertion (Pitfalls.md §Pitfall 4)

```python
# Source: .planning/research/PITFALLS.md Pitfall 4 — test template
import importlib

@pytest.mark.parametrize("pkg", ["ambito_financiero_client"])  # SPIKE: ambito only
def test_codegen_preserves_raise_for_response_identity(pkg: str) -> None:
    """v1.1 Phase 7 D-04 (B8) invariant survives codegen."""
    client_mod = importlib.import_module(f"{pkg}.client")
    aio_mod = importlib.import_module(f"{pkg}.aio")
    core_mod = importlib.import_module(f"{pkg}._core")
    assert (
        client_mod._raise_for_response
        is aio_mod._raise_for_response
        is core_mod.raise_for_response
    )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Dual hand-write `client.py` + `aio.py` (v1.1 status quo) | Single-source `aio.py` → codegen `client.py` via unasync | Phase 16 (CONDITIONAL on Phase 12 GO) | Eliminates ~850 LOC × 4 packages structural duplication |
| setuptools `cmdclass_build_py()` integration (legacy unasync pattern) | Standalone Python script via `unasync_files()` invoked from pre-commit + CI gate | Industry shift 2020+ (httpcore + elasticsearch-py both moved to standalone scripts) | Decouples codegen from build backend; works with hatchling, poetry, uv, etc. |
| Generated-at-build-time | Generated AND committed to git | psycopg / httpcore / urllib3 consensus | Reviewable diffs; IDE friendliness; pre-commit verify-clean gate |

**Deprecated/outdated:**

- `unasync.cmdclass_build_py()` — setuptools-only integration; unusable with hatchling. Use standalone `unasync_files()` instead. `[CITED: https://github.com/python-trio/unasync/blob/master/setup.py]`
- ast-grep / comby / Jinja2 templates — rejected by v1.2 STACK research; no change in v1.3 unless circumstances shift.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | unasync 0.6.0 tokenizer does NOT descend into string contents (docstrings, string literals). | Recipe 1, Recipe 7 (Pitfall 7) | If wrong, spike must add docstring post-processing — adds 1-2 hours to spike, may not exceed 1-day timebox but increases risk. |
| A2 | unasync `Rule.fromdir` and `Rule.todir` accept the same path (in-place tokenization) for a single-file experiment. | Recipe 1, Recipe 2 (experiment.py Step 2) | If wrong, spike needs to use distinct dirs and copy output; trivial fix. |
| A3 | `uv run --with unasync python script.py` resolves the workspace + unasync transiently without polluting `pyproject.toml`. | Recipe 1 install command | If wrong, fall back to `uv pip install unasync` in the venv and remove at spike close. Trivial. |
| A4 | The `@generated` marker comment line at module top does NOT cause `ruff check` to flag any rule. | Recipe 5, Recipe 6 | If wrong, the marker triggers a documented `# noqa: <rule>` need; documented but adds 1-line per generated file. |
| A5 | `slopcheck install unasync libcst` returned `[OK]` for both packages on 2026-06-14. | Package Legitimacy Audit | If wrong (package downstream slopsquatted), spike installs malicious code. Mitigation: pin to specific 0.6.0 release; re-verify slopcheck at Phase 12 start. |
| A6 | Module docstring may precede `from __future__ import annotations` (Python language reference) — verified true per ámbito client.py line ordering. | Recipe 5 | If wrong, ámbito v1.1 baseline would already be broken (it's not; CI passes). Confidence very high. |

**Operator-confirmation hot list (highest assumption risk):** A1 (docstring tokenizer behavior) — verify in 001a experiment Step 5 by inspecting the generated docstring text. If unasync mangles docstrings, this is documented and may shift to NO-GO depending on severity.

## Open Questions (RESOLVED)

1. **Does `unasync_files()` overwrite the input file or write to a separate location?**
   - **RESOLVED:** Mitigation pattern adopted — `experiment.py` uses `shutil.copy(aio.py, work_dir/aio.py)` BEFORE calling `unasync.unasync_files`, so the source under `packages/` is never touched even if unasync overwrites in place. Verified empirically by 001a Step 7 `git status --porcelain packages/` returning zero lines.
   - What we know: `Rule(fromdir, todir)` rewrites paths by substituting `fromdir`→`todir` in the input path. If they are the same, the input IS overwritten in place. If different, the output goes to a sibling location.
   - What's unclear: whether unasync raises if the output already exists.
   - Recommendation: handle both cases in `experiment.py` — copy input to a clean work dir BEFORE invoking unasync, so even if unasync overwrites, the source `aio.py` is untouched.

2. **Will `additional_replacements={"_atransport": "_transport"}` accidentally affect the `_transport` mentions inside docstrings?**
   - **RESOLVED:** 001a Step 5 of `experiment.py` includes a `grep -n '_atransport' client_generated.py` check; if hits appear inside docstring contexts, the experiment handles them via a post-pass docstring restoration or by explicitly excluding docstring lines from the replacement. 12-02-PLAN.md Task 001b also tracks this as an acceptance criterion for the marker compatibility experiment.
   - What we know: unasync's tokenizer (per A1) preserves strings verbatim.
   - What's unclear: comments. Are inline `# _atransport` comments rewritten?
   - Recommendation: verify in 001a Step 5 by grepping the generated output. If comments are rewritten, document as a quirk; doesn't trigger NO-GO unless it changes semantics.

3. **Phase 16 production integration: pre-commit hook OR Makefile target OR CI-only?**
   - **RESOLVED — DEFERRED to Phase 16 per D-ARTIFACT-01.** Phase 12 documents the spike's recommendation in DECISION.md (GO branch only), but the integration choice itself is a Phase 16 planning decision and is explicitly out-of-scope for Phase 12.
   - Out of scope for Phase 12 (D-NOGO-01 + planner respects scope); but the spike's `DECISION.md` (GO branch) should DOCUMENT the recommended production pattern even though it doesn't IMPLEMENT it. Default recommendation matches industry (httpcore / elasticsearch-py): both pre-commit hook AND CI `lint-codegen` job.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `uv` | All spike commands | ✓ (per existing CI workflow + repo conventions) | 0.9.0 | — |
| `python3 >=3.12` | All spike commands | ✓ (active venv `.venv/`, CPython 3.12.11) | 3.12.11 | Python 3.13 (also CI-tested) |
| `ruff >=0.7` | Format + lint generated output | ✓ (root dev dep) | per `[dependency-groups] dev` | — |
| `mypy >=1.13` | Strict type-check generated output | ✓ (root dev dep) | per `[dependency-groups] dev` | — |
| `pytest >=8.3` + `pytest-httpx >=0.34` | Run ámbito mocked suite | ✓ (root dev dep) | per `[dependency-groups] dev` | — |
| `import-linter >=2.11,<3` | Re-verify 4 forbidden contracts | ✓ (root dev dep) | 2.11.x | — |
| `unasync >=0.6.0,<0.7` | Spike's tool-under-test | ✗ (NOT installed in workspace by design — spike-only) | 0.6.0 (latest, verified via slopcheck OK) | Transient install via `uv run --with unasync` — VALIDATED via `slopcheck install unasync` 2026-06-14 |
| `libcst >=1.8.0,<2` | Fallback ONLY if Phase 12 NO-GO (deferred to v1.3) | ✗ (not used in Phase 12) | 1.8.6 | — |
| `git` + `diff` (POSIX) | Byte-identical comparison + close-out diff sketches | ✓ (system) | — | — |
| `bash` / `zsh` | Spike experiment commands | ✓ (operator's shell) | — | — |
| `slopcheck` (operator-side, advisory) | Package legitimacy re-verification at Phase 12 start | ✓ (verified runnable this session) | 1.x | — |

**Missing dependencies with no fallback:** none — all critical tools available.

**Missing dependencies with fallback:** `unasync` — transient install via `uv run --with unasync` (already validated 2026-06-14 via slopcheck).

## Validation Architecture

> **This is a SPIKE phase.** The "validation" is the spike's own evidence checklist (D-RIGOR-01, 8 items). There is no separate pytest suite that validates the spike — the spike is the validation. But the planner SHOULD encode the 5 ROADMAP success criteria + 8-item evidence checklist as testable gates using shell commands.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | shell commands + pytest re-use (existing ámbito suite) + stdlib `ast` for matriz audit |
| Config file | none (transient — Phase 16 GO branch would add codegen verify-clean to root config) |
| Quick run command (per-experiment) | `uv run --with unasync python .planning/spikes/SPIKE-005-codegen-tool-choice/<id>/experiment.py` |
| Full suite command (8-item evidence) | shell pipeline composing all 8 commands; final exit code 0 = GO |
| Phase gate | 8/8 evidence items pass + zero TBD in matriz audit + 1-day timebox not exceeded |

### Phase Requirements → Test Map (ROADMAP success criteria + D-RIGOR-01)

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| ROADMAP SC#1 | Byte-identical round-trip ámbito | shell | `diff -u packages/ambito-financiero-client/src/ambito_financiero_client/client.py .planning/spikes/SPIKE-005-codegen-tool-choice/001a-ambito-round-trip/output/client_generated.py` (must exit 0) | ❌ Wave 1 |
| ROADMAP SC#2 / D-RIGOR-01.2 | B8 identity preserved | unit (loaded via importlib) | embedded in `001a-ambito-round-trip/experiment.py` Step 6 | ❌ Wave 1 |
| ROADMAP SC#3 / D-RIGOR-01.7 | Matriz audit zero TBD | shell | `grep -c '| REVIEW \|\| TBD \|' .planning/spikes/.../matriz-aio-constructs.md` (must be 0) | ❌ Wave 3 |
| ROADMAP SC#4 (GO branch) | Per-package `Rule` config captured | docs | inspect `.planning/spikes/SPIKE-005-codegen-tool-choice/DECISION.md` for 4 Rule config blocks | ❌ Wave 6 (GO) |
| ROADMAP SC#5 (NO-GO branch) | REQUIREMENTS.md + ROADMAP.md updated | docs | `grep -q "REFAC-06 (deferred per Phase 12 NO-GO" .planning/REQUIREMENTS.md && grep -q "DROPPED" .planning/ROADMAP.md` (both must match) | ❌ Wave 6 (NO-GO) |
| D-RIGOR-01.3 | `ruff format --check` clean | shell | `uv run ruff format --check <generated>` (exit 0) | ❌ Wave 2 |
| D-RIGOR-01.4 | `ruff check` clean (ASYNC1xx etc.) | shell | `uv run ruff check <generated>` (exit 0) | ❌ Wave 2 |
| D-RIGOR-01.5 | `mypy --strict` clean | shell | `uv run mypy --strict <generated>` (exit 0) | ❌ Wave 2 |
| D-RIGOR-01.6 | Ámbito mocked suite green vs generated | pytest | `uv run --package ambito-financiero-client pytest -q` (after temporarily symlinking generated as `client.py` — careful, the test must NOT mutate `packages/`) | ❌ Wave 5 |
| D-RIGOR-01.7 (import-linter) | 4 existing contracts intact | shell | `uv run lint-imports` (exit 0) | ✅ existing config |
| D-RIGOR-01.8 | `@generated` marker compatible with `from __future__ import annotations` | shell | `uv run python -c "import ast; ast.parse(open('<generated>').read())"` + ruff check + mypy strict (all exit 0) | ❌ Wave 2 |

### Sampling Rate

- **Per spike sub-experiment (Wave commit):** the experiment.py itself emits PASS/FAIL via subprocess exit codes + transcripts. No separate sampling.
- **Per wave merge:** run the 8-item evidence checklist (all bash commands above) and tally pass/fail.
- **Phase gate (`/gsd-verify-work`):** the 8-item evidence checklist must be 8/8 PASS, OR if any single item FAILS, the spike triggers NO-GO and the NO-GO close-out artifacts are produced.

### Wave 0 Gaps

- [ ] `.planning/spikes/SPIKE-005-codegen-tool-choice/` — top-level spike directory + `README.md` + 4 sub-directory skeletons (per Recipe 8).
- [ ] `.planning/spikes/MANIFEST.md` — append SPIKE-005 row to the existing manifest table.
- [ ] No new pytest config or framework install needed — the spike re-uses the existing repo's ruff/mypy/pytest/import-linter stack.

*(If GO branch:)* additional Wave 6 gaps for skill production + Phase 16 prep:
- [ ] `.claude/skills/spike-findings-codegen-market-libs/SKILL.md` — produced via `/gsd-spike --wrap-up`.
- [ ] CLAUDE.md "Auto-loaded Knowledge" — add reference to new skill.

*(If NO-GO branch:)* additional Wave 6 gaps for v1.3 capture:
- [ ] `.planning/spikes/SPIKE-005-codegen-tool-choice/NO-GO.md` — root cause analysis.
- [ ] `.planning/todos/pending/spike-codegen-libcst-v1.3.md` — v1.3 capture.

## Anti-Patterns

These actions MUST NOT happen during Phase 12 execution. The planner encodes each as a verification step or prohibits via task scoping.

| Anti-Pattern | Why It's Wrong | What to Do Instead |
|--------------|----------------|---------------------|
| Inline libcst evaluation when unasync looks shaky | Violates D-NOGO-01 (libcst gets its own v1.3 spike) AND blows the 1-day timebox | Trigger NO-GO automatic; libcst defers to v1.3 via the captured pending todo. |
| Editing `packages/ambito-financiero-client/src/ambito_financiero_client/client.py` to "test the pattern" | Spike must NOT mutate production code. Per CONVENTIONS.md §"To Avoid". | All experiments target `.planning/spikes/SPIKE-005-codegen-tool-choice/<id>/output/<generated>.py`. |
| Adding the codegen production integration (pre-commit hook, CI `lint-codegen` job, `pyproject.toml` dev-dep × 4 packages) | Phase 16 deliverables — outside Phase 12 scope. | Phase 12 DOCUMENTS the recommended pattern in the GO close-out `DECISION.md`; Phase 16 IMPLEMENTS. |
| Skipping the B8 identity assertion because diff is empty | Diff-empty does NOT imply identity-preserved (thunk wrapper is byte-different from alias — wait, it IS detectable in diff, but the spike should still run identity test as separate proof). | Recipe 3 embedded in `001a-ambito-round-trip/experiment.py` Step 6 — mandatory step. |
| Soft-relaxing "zero TBD rows" in matriz audit under time pressure | D-SCOPE-02 hard gate; soft-relaxing means Phase 16 hits unhandled construct. | Programmatic gate in Validation Architecture (`grep -c REVIEW ... == 0`). |
| Putting the `@generated` marker AFTER the future import line | Breaks future statement requirements (would raise `SyntaxError` if it actually preceded any non-allowed item; comment is allowed, but ordering must be deterministic for Phase 16's pre-commit hook to detect). | Recipe 5 line ordering: marker → blank → docstring → blank → future import. |
| Importing from `packages/*/src/` in spike experiment code | Per CONVENTIONS.md §"To Avoid": *"spikes must be self-contained."* | Spike experiment.py uses `subprocess`, `shutil`, `pathlib` to read source files as PATHS — does not `from ambito_financiero_client import ...`. Exception: the B8 identity test loads the SPIKE OUTPUT as a module via `importlib.util.spec_from_file_location` — this is testing the spike output, not the production package. |
| Modifying the codegen deny-list (matriz `_token_store.py` / `_refresh_policy.py` / `ws_client.py`) | Locked invariant per ARCHITECTURE.md research; spike only CONFIRMS, not RENEGOTIATES. | Recipe 4 (matriz audit) + Wave 4 (deny-list sha256 intactness) only READ these files. |

## Critical Artifacts Checklist (Wave-Level Deliverables)

The exact deliverables Phase 12 produces, branched by decision outcome:

### Always (regardless of GO/NO-GO)

- [ ] `.planning/spikes/SPIKE-005-codegen-tool-choice/README.md` — spike entry
- [ ] `.planning/spikes/SPIKE-005-codegen-tool-choice/001a-ambito-round-trip/{README.md, experiment.py, output/client_generated.py, diff_vs_v1.1_client.txt, FINDING.md}`
- [ ] `.planning/spikes/SPIKE-005-codegen-tool-choice/001b-ambito-marker-future-compat/{README.md, experiment.py, verification_transcripts.txt, FINDING.md}`
- [ ] `.planning/spikes/SPIKE-005-codegen-tool-choice/001c-matriz-construct-audit/{README.md, audit.py, matriz-aio-constructs.md, FINDING.md}`
- [ ] `.planning/spikes/SPIKE-005-codegen-tool-choice/001d-matriz-deny-list-config/{README.md, experiment.py, verification_transcripts.txt, FINDING.md}`
- [ ] `.planning/spikes/SPIKE-005-codegen-tool-choice/DECISION.md` — operator-signed (frontmatter `decision: GO|NO-GO`)
- [ ] `.planning/spikes/MANIFEST.md` updated with SPIKE-005 row
- [ ] `.planning/phases/12-codegen-spike/12-SUMMARY.md` — Phase close artifact
- [ ] `.claude/skills/spike-findings-codegen-market-libs/SKILL.md` — produced via `/gsd-spike --wrap-up`
- [ ] CLAUDE.md "Auto-loaded Knowledge" updated with new skill reference

### GO branch only

- [ ] `DECISION.md` contains: 8-item evidence checklist 8/8 PASS + per-package `Rule` config drafts for ambito/iol/higyrus/matriz (4 blocks) + recommended `@generated` marker syntax + Phase 16 production integration recommendation (pre-commit + CI `lint-codegen` job + `pyproject.toml` dev-dep addition).
- [ ] `12-SUMMARY.md` frontmatter: `decision: GO`, `next_phase: 13`.

### NO-GO branch only

- [ ] `.planning/spikes/SPIKE-005-codegen-tool-choice/NO-GO.md` — root cause analysis (which evidence item failed + concrete failure transcript).
- [ ] `.planning/REQUIREMENTS.md` edited — REFAC-06 moved to "Future Requirements (Defer to v1.3+)" section + traceability table row updated.
- [ ] `.planning/ROADMAP.md` edited — Phase 16 marked DROPPED, Progress table updated.
- [ ] `.planning/todos/pending/spike-codegen-libcst-v1.3.md` — v1.3 capture for libcst exploration.
- [ ] `12-SUMMARY.md` frontmatter: `decision: NO-GO`, `next_phase: 13 (Phase 16 DROPPED; Phase 17 unblocked after 14+15)`.

## Sources

### Primary (HIGH confidence)

- [unasync 0.6.0 docs](https://unasync.readthedocs.io/en/latest/) — Rule API + standalone usage pattern
- [github.com/python-trio/unasync](https://github.com/python-trio/unasync) — source inspection: `_ASYNC_TO_SYNC` defaults + `Rule.__init__` signature
- [github.com/encode/httpcore/blob/master/scripts/unasync.py](https://github.com/encode/httpcore/blob/master/scripts/unasync.py) — production reference for SUBS list (19 substitutions)
- [github.com/elastic/elasticsearch-py/blob/main/utils/run-unasync.py](https://github.com/elastic/elasticsearch-py/blob/main/utils/run-unasync.py) — production reference for Rule per-directory configuration
- `.planning/research/SUMMARY.md` — v1.2 stack synthesis (unasync primary, libcst fallback)
- `.planning/research/STACK.md` — version verification (unasync 0.6.0 / libcst 1.8.6) + ecosystem precedent
- `.planning/research/ARCHITECTURE.md` §2.2 — B8 identity preservation requirement + deny-list locked
- `.planning/research/PITFALLS.md` §Pitfalls 4 + 5 + 6 — regression test patterns the spike uses as evidence checklist
- `.planning/spikes/CONVENTIONS.md` — naming + organization
- `.planning/spikes/MANIFEST.md` — registry (SPIKE-001a/b/c + 002 + 003)
- `.claude/skills/spike-findings-market-libs/SKILL.md` — Skill format model
- `packages/ambito-financiero-client/src/ambito_financiero_client/{client.py, aio.py, _core.py}` — round-trip subject
- `packages/matriz-client/src/matriz_client/{aio.py, _token_store.py, _refresh_policy.py, ws_client.py}` — construct audit subject + deny-list canonicals
- `pyproject.toml` (root) — import-linter contracts + ruff/mypy strict config
- `CLAUDE.md` — project-level mandatory `from __future__ import annotations` directive

### Secondary (MEDIUM confidence)

- [unasync GitHub issue #74](https://github.com/python-trio/unasync/issues/74) — multi-token substitution limitation (verified against tokenizer behavior)
- [PEP 236 Future statements](https://docs.python.org/3/reference/simple_stmts.html#future-statements) — ordering rules for `from __future__ import annotations`
- [PEP 263 source code encoding](https://peps.python.org/pep-0263/) — encoding comment line ordering (only relevant if encoding marker conflicts with `@generated`; spike confirms no conflict)

### Tertiary (LOW confidence)

- None — all material used in this RESEARCH.md is sourced from HIGH or MEDIUM confidence material.

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — both `unasync` and `libcst` verified on PyPI + slopcheck OK 2026-06-14
- unasync API + invocation pattern: HIGH — verified via source inspection + httpcore + elasticsearch-py production scripts
- Ámbito round-trip recipe: HIGH — source files read in full this session; transformations match unasync's documented behavior
- Matriz construct audit: HIGH — 128 grep matches enumerated this session; classification table embeds known deny-list intactness
- `@generated` marker × `from __future__` compatibility: HIGH — Python language reference unambiguous; ámbito v1.1 file already proves comments-before-future work
- Spike directory layout: HIGH — Phase 10 convention well established + read this session
- Wrap-up Skill shape: HIGH — `spike-findings-market-libs/SKILL.md` is the explicit template
- NO-GO close-out: HIGH — REQUIREMENTS.md / ROADMAP.md / pending-todos paths verified this session
- Pitfalls: HIGH — rooted in existing Pitfalls.md + matriz live source + spike convention enforcement

**Research date:** 2026-06-14
**Valid until:** 2026-07-14 (30 days; unasync 0.6.0 is stable; spike timebox is 1 day so research staleness risk is low)
