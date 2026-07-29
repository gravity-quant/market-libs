---
phase: 18-libcst-codegen-tool-choice-spike-spike-006
plan: 01
subsystem: testing
tags: [codegen, libcst, spike, ambito, matriz, B8-identity, deny-list, sha256, ast]

# Dependency graph
requires:
  - phase: 12-codegen-spike
    provides: "SPIKE-005 unasync NO-GO harness (001b marker design, 001c audit.py, 001d sha256 skeleton) inherited ~60%"
provides:
  - "SPIKE-006 spike tree scaffold (README + DECISION.md + evidence-checklist.txt skeletons) paralleling SPIKE-005"
  - "Item 10a (001c): matriz construct audit PASS — 0 unresolved rows vs current 959-LOC aio.py (verbatim audit.py)"
  - "Item 8 (001b): @generated marker via libcst Module.header — STRICT PASS (all 4 verification commands exit 0)"
  - "Item 10b (001d): matriz 4-file deny-list sha256-byte-identical pre/post; aio.py transformed via per-module libcst scope"
  - "Empirical confirmation of libcst lossless round-trip + Module.header semantics (RESEARCH A2)"
affects: [18-02 (001a CSTTransformer suite), 18-03 (DECISION aggregation + close-out)]

# Tech tracking
tech-stack:
  added: ["libcst >=1.8.0,<2 (EPHEMERAL only via uv run --with — NOT added to dev deps, D-05)"]
  patterns:
    - "Marker insertion via cst.Module.header (EmptyLine/Comment), never str.replace (Anti-Pitfall 6)"
    - "Deny-list honored by per-module transform SCOPE (only aio.py parsed) — libcst equivalent of unasync fpath_list"
    - "Verification subprocesses spawned with sanitized env (VIRTUAL_ENV/UV_* removed) to resolve workspace .venv"

key-files:
  created:
    - ".planning/spikes/SPIKE-006-libcst-codegen-tool-choice/README.md"
    - ".planning/spikes/SPIKE-006-libcst-codegen-tool-choice/DECISION.md"
    - ".planning/spikes/SPIKE-006-libcst-codegen-tool-choice/evidence-checklist.txt"
    - ".planning/spikes/SPIKE-006-libcst-codegen-tool-choice/001c-matriz-construct-audit/audit.py"
    - ".planning/spikes/SPIKE-006-libcst-codegen-tool-choice/001b-ambito-marker-future-compat/experiment.py"
    - ".planning/spikes/SPIKE-006-libcst-codegen-tool-choice/001d-matriz-deny-list-config/experiment.py"
  modified: []

key-decisions:
  - "audit.py copied byte-identical from SPIKE-005 (SKILL mandate); SOURCE auto-points at current matriz aio.py via REPO_ROOT parents[4]"
  - "001b bar raised to STRICT (all 4 commands exit 0) since target is the CURRENT clean client.py, not SPIKE-005's noisy 001a output"
  - "001d uses a minimal AsyncToSync transform (not a 'trivial round-trip'): round-trip is lossless=no-op and would fail the 'aio.py transformed' gate"
  - "libcst kept ephemeral (D-05); uv.lock verified unchanged after runs"

patterns-established:
  - "Pattern: ephemeral libcst via uv run --with; verification subprocess env sanitized to hit workspace .venv"
  - "Pattern: spike scripts under .planning/spikes/** (ruff extend-exclude; mypy files:^packages/.*/src/) — no CI lint coupling"

requirements-completed: [CODEGEN-01]

# Metrics
duration: 22min
completed: 2026-07-02
status: complete
---

# Phase 18 Plan 01: SPIKE-006 Scaffold + Inherited libcst Evidence (items 8, 10a, 10b) Summary

**Stood up the SPIKE-006 libcst spike tree and landed the ~60% inherited D-RIGOR-02 harness — item 10a matriz construct audit (0 unresolved / 959 LOC, verbatim audit.py), item 8 @generated marker via libcst Module.header (STRICT PASS, all 4 commands exit 0), and item 10b matriz 4-file deny-list sha256 byte-identity under per-module libcst scope — with the libcst supply-chain gate operator-approved and libcst kept ephemeral.**

## Performance

- **Duration:** ~22 min
- **Completed:** 2026-07-02
- **Tasks:** 3 (Task 1 checkpoint operator-approved; Tasks 2 + 3 executed)
- **Files created:** 15 (spike tree)

## Accomplishments

- **Task 1 (checkpoint, operator-approved):** libcst supply-chain legitimacy gate (D-05) cleared by the operator (PyPI provenance + github.com/Instagram/LibCST verified; SUS verdict assessed as metadata-gap false positive). Recorded as cleared; libcst used **ephemerally only** (never added to `[dependency-groups] dev`). `uv.lock` verified unchanged after all runs.
- **Task 2 — scaffold + item 10a (001c):** Created the SPIKE-006 tree paralleling SPIKE-005 (`README.md` spike:006/verdict:TBD, `DECISION.md` skeleton with the 10-item verdict map + `decision: TBD`, `evidence-checklist.txt` skeleton with per-item commands). Copied `001c/audit.py` **byte-identical** from SPIKE-005 (pure stdlib `ast`, no libcst); it exits 0 with **0 unresolved rows** against the current 959-LOC matriz `aio.py`. **Item 10a PASS.**
- **Task 3 — items 8 + 10b:** `001b` inserts the 3-line `@generated` marker via libcst `Module.header` (never `str.replace`) into the current clean ámbito `client.py`; all 4 verification commands (`ruff check`, `ruff format --check`, `mypy --strict`, `ast.parse`) exit 0 on the marked file and are marker-neutral vs baseline — **item 8 STRICT PASS**. `001d` sha256-witnesses the matriz 4-file deny-list byte-identical pre/post a per-module libcst transform while sandbox `aio.py` is transformed — **item 10b PASS**.
- Empirically confirmed RESEARCH open question A2: libcst lossless round-trip (`cst.parse_module(src).code == src`) and `Module.header` trivia semantics both behave as cited.

## Task Commits

1. **Task 2: Scaffold spike tree + decision skeletons + item 10a matriz construct audit (001c)** — `b358245` (feat)
2. **Task 3: Inherited libcst experiments — item 8 marker (001b) + item 10b deny-list sha256 (001d)** — `2d2f873` (feat)

_Task 1 was a `checkpoint:human-verify` supply-chain gate, pre-approved by the operator — no code commit._

## Files Created/Modified

- `.../SPIKE-006-.../README.md` — spike entry (spike:006, verdict:TBD), sub-experiment table, ephemeral run instructions
- `.../SPIKE-006-.../DECISION.md` — signed-decision skeleton, 10-item `evidence_checklist` verdict map (all TBD)
- `.../SPIKE-006-.../evidence-checklist.txt` — 10-item transcript skeleton; items 8/10a/10b filled with Plan 01 PASS results
- `.../001c-matriz-construct-audit/audit.py` — verbatim SPIKE-005 copy (stdlib ast, read-only)
- `.../001c-matriz-construct-audit/{audit-run.log, matriz-aio-constructs.md, FINDING.md}` — item 10a evidence (110 rows, 0 unresolved)
- `.../001b-ambito-marker-future-compat/experiment.py` — libcst Module.header marker insertion + 4-command verification
- `.../001b-ambito-marker-future-compat/{client_with_marker.py, client_baseline_no_marker.py, verification_transcripts.txt, FINDING.md}` — item 8 evidence
- `.../001d-matriz-deny-list-config/experiment.py` — per-module libcst transform + 4-file sha256 harness
- `.../001d-matriz-deny-list-config/{sha256_before.txt, sha256_after.txt, FINDING.md}` — item 10b evidence

## Decisions Made

- **Verbatim audit.py:** copied byte-identical from SPIKE-005 per the `spike-findings-codegen-market-libs` SKILL and the plan must-have. `SOURCE` resolves to the current matriz `aio.py` automatically (same sub-dir depth → `parents[4]` = repo root). No `== 109`/`== 110` row assertion (Pitfall 2); the gate is "0 unresolved."
- **001b STRICT bar:** because the marker target is the current CLEAN `client.py` (not SPIKE-005's noisy 001a output), item 8 is asserted at the strict "all 4 exit 0" level — a strictly stronger result than SPIKE-005's neutral-delta reading.
- **001d transform choice:** used a minimal `AsyncToSync` pass rather than a "trivial round-trip." libcst's round-trip is lossless (`code == src`), so a round-trip would leave `aio.py` byte-identical and fail the "aio.py transformed" half of item 10b. The real transform proves SCOPE, not a no-op.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Item 10a verify greps stdout, but verbatim audit.py writes the sentinel to its output file**
- **Found during:** Task 2 (item 10a audit)
- **Issue:** The plan's `<automated>` verify greps `/tmp/spike006-001c.log` (stdout) for `MERGE GATE PASS`, but the **verbatim** `audit.py` (mandated by the SKILL + must-have "Verbatim copy") writes that sentinel to its OUTPUT file `matriz-aio-constructs.md`, not to stdout (stdout carries `Unresolved (...): 0`). A literal re-run of the plan's grep-stdout command fails against the required verbatim script.
- **Fix:** Kept `audit.py` byte-identical (hard requirement wins over the buggy verify target). The substantive gate — **0 unresolved rows** — passes; the sentinel is present in `matriz-aio-constructs.md`. `audit-run.log` was produced to carry both the stdout transcript AND the appended merge-gate lines from the output file, so any grep of `audit-run.log` for the sentinel also passes. Corrected verification command (grep the audit's output file) documented in `001c/FINDING.md` and `evidence-checklist.txt` §item 10a.
- **Files modified:** `001c/audit-run.log`, `001c/FINDING.md`, `evidence-checklist.txt`
- **Verification:** `uv run python 001c/audit.py` exits 0; `grep '**MERGE GATE PASS:**' 001c/matriz-aio-constructs.md` succeeds; `git diff --exit-code packages/` clean.
- **Committed in:** `b358245` (Task 2 commit)

**2. [Rule 3 - Blocking] Marker/verification subprocesses under ephemeral libcst env could not resolve the workspace package**
- **Found during:** Task 3 (001b item 8)
- **Issue:** `001b/experiment.py` runs under `uv run --with 'libcst>=1.8.0,<2'` (ephemeral env). Nested `uv run mypy` subprocesses inherited the ephemeral `VIRTUAL_ENV`, producing a spurious `import-not-found` for `ambito_financiero_client` (the SPIKE-005 001b spike-location artifact) — which would have blocked the strict "exit 0" bar.
- **Fix:** Spawn the 4 verification subprocesses with a sanitized env (`VIRTUAL_ENV` + `UV_*` removed) so `uv run` resolves the workspace `.venv`. This is a harness detail, not a marker property; documented in `001b/FINDING.md`.
- **Files modified:** `001b/experiment.py`
- **Verification:** all 4 commands exit 0 on the marked file; marker-neutral vs baseline.
- **Committed in:** `2d2f873` (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (1 plan-verify bug, 1 blocking env resolution)
**Impact on plan:** Both necessary to land the inherited evidence honestly under the verbatim/ephemeral constraints. No scope creep; no production source touched; deny-list confirmed intact (D-09).

## Issues Encountered

- Confirmed matriz `aio.py` grew 852→959 LOC since SPIKE-005 (Pitfall 2): the audit now enumerates 110 rows (was 109). The +1 is a `manual-sync-proof` row from ordinary async-surface growth and does not affect the 0-unresolved gate. No hardcoded row-count assertion was introduced.

## Threat Flags

None. The spike introduces no new security surface. The matriz concurrency/secret-handling primitives are deny-listed and were verified sha256-byte-identical (item 10b, T-18-01); `packages/` production source is unmutated (T-18-02); no `.env` read (T-18-03); libcst install is ephemeral with `uv.lock` verified unchanged (T-18-SC).

## Next Phase Readiness

- **Plan 02** (`001a` CSTTransformer suite: `AsyncToSync`, `ImportNormalizer`, `DocstringLocalizer`, `ImportDirectionNormalizer`, `Suppressors`) has a stable scaffold, a cleared libcst install gate, and confirmed libcst node-API behavior (lossless round-trip, `Module.header`, minimal `AsyncToSync`) to build on.
- **Plan 03** (aggregation) inherits `DECISION.md` + `evidence-checklist.txt` skeletons with items 8, 10a, 10b already PASS-filled; it fills the GO-determining items 1/4/6 and 2/3/5/7/9 and computes the signed verdict.
- Deny-list (D-09) CONFIRMED out of codegen scope — not renegotiated.

## Self-Check: PASSED

- All 15 spike files verified present on disk.
- Both task commits (`b358245`, `2d2f873`) verified in `git log`.
- `packages/` (incl. matriz deny-list files) verified byte-unchanged in the repo; `uv.lock` unchanged; no `.env` touched.

---
*Phase: 18-libcst-codegen-tool-choice-spike-spike-006*
*Completed: 2026-07-02*
