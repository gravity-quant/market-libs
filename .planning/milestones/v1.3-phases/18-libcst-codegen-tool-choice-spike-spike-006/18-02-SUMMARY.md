---
phase: 18-libcst-codegen-tool-choice-spike-spike-006
plan: 02
subsystem: testing
tags: [codegen, libcst, spike, ambito, CSTTransformer, byte-identity, content-absence, B8-identity, NO-GO]

# Dependency graph
requires:
  - phase: 18-libcst-codegen-tool-choice-spike-spike-006
    plan: 01
    provides: "SPIKE-006 scaffold + cleared libcst install gate + confirmed libcst node-API (lossless round-trip, Module.header)"
provides:
  - "001a CSTTransformer suite (5 pure CSTNode→CSTNode subclasses) + impure driver — canary-proven on ámbito aio.py"
  - "Item 1 (GO-det) FAIL transcript: 13 hunks / 383 lines vs REGENERATED current client.py (content-absence root cause)"
  - "Item 4 (GO-det) PASS: ruff check clean (I001 + ASYNC1xx) — the item unasync/SPIKE-005 FAILED"
  - "Item 6 (GO-det) FAIL: circular self-import _validate_max_retries (exact SPIKE-005 root cause reproduced)"
  - "Items 2/5/7/9 PASS + item 3 FAIL; Q1 content-absence + Q2 purity-scope + Q3 docstring-divergence instrumented"
affects: [18-03 (DECISION aggregation — signs the milestone GO/NO-GO from these per-item verdicts)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pure CSTTransformer subclass + impure driver split (item-9 purity: vars(t) unchanged across visit)"
    - "Immutable frozenset config at __init__ keeps a transformer pure while the driver owns cross-module scope"
    - "Content-absence honesty: self-import RETAINED (never synthesized from client.py donor / aio.py edit)"

key-files:
  created:
    - ".planning/spikes/SPIKE-006-libcst-codegen-tool-choice/001a-ambito-round-trip/README.md"
    - ".planning/spikes/SPIKE-006-libcst-codegen-tool-choice/001a-ambito-round-trip/experiment.py"
    - ".planning/spikes/SPIKE-006-libcst-codegen-tool-choice/001a-ambito-round-trip/transformers/async_to_sync.py"
    - ".planning/spikes/SPIKE-006-libcst-codegen-tool-choice/001a-ambito-round-trip/transformers/import_normalizer.py"
    - ".planning/spikes/SPIKE-006-libcst-codegen-tool-choice/001a-ambito-round-trip/transformers/docstring_localizer.py"
    - ".planning/spikes/SPIKE-006-libcst-codegen-tool-choice/001a-ambito-round-trip/transformers/import_direction_normalizer.py"
    - ".planning/spikes/SPIKE-006-libcst-codegen-tool-choice/001a-ambito-round-trip/transformers/suppressors.py"
    - ".planning/spikes/SPIKE-006-libcst-codegen-tool-choice/001a-ambito-round-trip/transformers/test_transformers.py"
    - ".planning/spikes/SPIKE-006-libcst-codegen-tool-choice/001a-ambito-round-trip/output/client_generated.py"
    - ".planning/spikes/SPIKE-006-libcst-codegen-tool-choice/001a-ambito-round-trip/diff_vs_current_client.txt"
    - ".planning/spikes/SPIKE-006-libcst-codegen-tool-choice/001a-ambito-round-trip/run_log.txt"
    - ".planning/spikes/SPIKE-006-libcst-codegen-tool-choice/001a-ambito-round-trip/FINDING.md"
  modified: []

key-decisions:
  - "Item-9 purity scoped to the transformer CLASSES (A3); cross-module/scope orchestration lives in the impure driver — flagged for operator ratification (Q2)"
  - "ImportDirectionNormalizer takes an immutable frozenset config; the driver computes locally-defined names — _validate_max_retries absent → self-import RETAINED (honest Q1 residual)"
  - "DocstringLocalizer does mechanical label swaps only; structural prose divergence (with_options 43-vs-19) left as honest item-1 residual, NOT hardcoded from the oracle"
  - "Module-level close-delegator drop done in the driver (scope-aware), not a transformer, to preserve item-9 class purity"

patterns-established:
  - "Pattern: TDD for a codegen suite — RED behavior+purity test under ephemeral libcst, GREEN transformers, honest gate transcript"
  - "Pattern: content-absent-from-source is a hard boundary for pure single-file codegen (libcst relocates/rewrites, never synthesizes)"

requirements-completed: [CODEGEN-01]

# Metrics
duration: 33min
completed: 2026-07-02
status: complete
---

# Phase 18 Plan 02: 001a ámbito Round-Trip — CSTTransformer Suite + GO-Determining Gate Transcript Summary

**Authored the genuinely-new core of SPIKE-006 — five pure libcst `CSTTransformer` subclasses + an impure driver that transform the un-migrated ámbito `aio.py` into a candidate sync `client.py` — and captured the honest D-RIGOR-02 gate transcript: item 4 (GO-det, `ruff check`) now PASSES (the item unasync failed), but items 1 and 6 (GO-det) FAIL for the exact SPIKE-005 source-shape root cause — `_validate_max_retries` def + `load_dotenv` bootstrap are content-absent from `aio.py` and cannot be synthesized by any pure transform — a signed same-root-cause NO-GO that is a valid, guaranteed deliverable (D-04/D-08), reached without editing `aio.py` or reading `client.py` as a donor.**

## Performance

- **Duration:** ~33 min
- **Completed:** 2026-07-02
- **Tasks:** 2 (Task 1 TDD: RED + GREEN; Task 2: gate transcript)
- **Files created:** 12 (001a sub-experiment)

## Accomplishments

- **Task 1 (TDD) — transformer suite + driver.** RED: a 14-assertion behavior + item-9 purity suite (`test_transformers.py`) failing on absent transformers. GREEN: five PURE `CSTNode→CSTNode` subclasses — `AsyncToSync` (async/await strip + fixed rename map), `ImportNormalizer` (I001 alias sort), `DocstringLocalizer` (mechanical label swaps), `Suppressors` (RemovalSentinel: `import warnings`, WR-07 `ResourceWarning` block, `prior_http_client` assign, `"aclose"` `__all__` entry), `ImportDirectionNormalizer` (immutable-frozenset config; strips a self-import only when the name is locally defined) — all 14 tests pass. The impure driver `experiment.py` parses `aio.py` (SOLE source), runs the passes, drops the module-level `close` delegator (scope-aware), prepends the `@generated` marker via `Module.header`, emits `output/client_generated.py`, and asserts the lossless round-trip smoke, B8 verbatim preservation, and item-9 purity (`vars(t)` unchanged across visit).
- **Task 2 — the D-RIGOR-02 gate transcript** (`run_log.txt` + `diff_vs_current_client.txt` + `FINDING.md`): items 1/2/3/4/5/6/7/9 each captured with command + exit-code + verdict.
- **Item 1 baseline REGENERATED** vs the current v1.2-head `client.py` (SPIKE-005 `diff_vs_v1.1_client.txt` is stale — Pitfall 1): 13 hunks / 383 lines (more than SPIKE-005's 10/295, as RESEARCH predicted).
- **Q1 content-absence instrumented honestly:** the driver's runtime scan confirms `_validate_max_retries` is not a module-level def in `aio.py` and the `from dotenv import load_dotenv` bootstrap is absent; the generated file retains the `aio.py:34` self-import, and the item-6 `/tmp` sandbox reproduces the EXACT SPIKE-005 `ImportError: cannot import name '_validate_max_retries' from partially initialized module … circular import`.

## D-RIGOR-02 Item Verdicts (001a-owned)

| Item | GO-det | Verdict | Evidence |
|------|:------:|:-------:|----------|
| 1 byte-identical vs current client.py | ✅ | **FAIL** | 13 hunks / 383 lines; residual = content-absent def + dotenv bootstrap + prose docstrings |
| 2 B8 is-triple identity | | **PASS** | same object id across mod/aio/_core |
| 3 ruff format --check | | **FAIL** | length-changing swap left aio.py multi-line wrapping (premise breaks on length change) |
| 4 ruff check (I001 + ASYNC1xx) | ✅ | **PASS** | `All checks passed!` — the item unasync FAILED |
| 5 mypy --strict | | **PASS** | `Success: no issues found` |
| 6 ámbito mocked suite (no circular import) | ✅ | **FAIL** | circular self-import `_validate_max_retries` (SPIKE-005 root cause) |
| 7 lint-imports 4 contracts | | **PASS** | `4 kept, 0 broken` |
| 9 CSTTransformer purity | | **PASS** | `vars(t)` unchanged across visit; 14/14 tests |

**Aggregate (D-04, strict): NO-GO** — 2 of 3 GO-determining items FAIL (1, 6). Final signed verdict + REFAC-06 shelving is Plan 18-03's job.

## Task Commits

1. **Task 1 RED — failing transformer behavior + item-9 purity suite** — `c0fcac6` (test)
2. **Task 1 GREEN — pure CSTTransformer suite + impure driver; emit generated client.py** — `a616258` (feat)
3. **Task 2 — 001a D-RIGOR-02 gate transcript (items 1/2/3/4/5/6/7/9)** — `acc44a7` (feat)

## TDD Gate Compliance

RED (`test(...)` `c0fcac6`) → GREEN (`feat(...)` `a616258`) gate sequence present and ordered. RED failed on absent
transformers (collection ImportError); no test passed unexpectedly before implementation. No REFACTOR commit needed
(implementation landed clean; 14/14 green with no post-cleanup).

## Decisions Made

- **Item-9 purity at the CLASS level (A3/Q2).** Each transformer is pure; the driver is explicitly impure and owns
  cross-module/scope orchestration (locally-defined-name scan, module-level delegator drop, marker insertion). Flagged
  in FINDING.md for operator ratification in Plan 03 — moot for the verdict since items 1/6 already force NO-GO.
- **Self-import RETAINED, not synthesized (Q1 honesty).** `ImportDirectionNormalizer` strips a self-import only when the
  name is in the driver-computed locally-defined frozenset; `_validate_max_retries` is absent, so the import is kept
  verbatim — reproducing the honest failure rather than smuggling a `client.py` donor or an `aio.py` edit.
- **DocstringLocalizer = mechanical swaps only.** Structural prose divergence (with_options 43-vs-19, module docstring)
  is left as honest item-1 residual; hardcoding the target literal (oracle-embedding) was rejected.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `transformers/__init__.py` broke pytest collection**
- **Found during:** Task 1 GREEN
- **Issue:** an `__init__.py` re-exporting the submodules with bare imports made `transformers/` a package; pytest
  (importlib mode) then triggered the package `__init__` before the test's `sys.path` insertion, raising
  `ModuleNotFoundError: No module named 'async_to_sync'`.
- **Fix:** removed `__init__.py` — the driver and test both use `sys.path` insertion + bare imports, so `transformers/`
  is intentionally NOT a package. All 14 tests then pass. (`__init__.py` was not in the plan's `<files>`.)
- **Files modified:** deleted the transient `transformers/__init__.py`.
- **Committed in:** `a616258`.

**2. [Rule 1 - Bug] `load_dotenv` presence check hit the docstring mention**
- **Found during:** Task 1 GREEN (driver instrumentation)
- **Issue:** an initial `"load_dotenv" in AIO_SRC` substring check returned `True` because `aio.py`'s docstring says
  "D-19: NO llama `load_dotenv()`" — prose, not an executable bootstrap — producing a misleading Q1 annotation.
- **Fix:** tightened to detect the actual `from dotenv import load_dotenv` import statement (correctly absent → `False`).
- **Files modified:** `experiment.py`.
- **Committed in:** `a616258`.

---

**Total deviations:** 2 auto-fixed (both Rule 1 bugs in the spike harness). No production source touched; no scope creep.

## Issues Encountered

- **Item 3 honest finding:** the "no `ruff format` post-pass needed" premise HOLDS for untouched trivia but BREAKS
  where a substring swap changes line length — the `AmbitoFinancieroAsyncClient`→`AmbitoFinancieroClient` swap shortened
  the `__reduce__`/`__deepcopy__` TypeError strings while libcst preserved `aio.py`'s original multi-line wrapping. This
  drives both item 3 and part of the item-1 residual.
- **Item 4 improved vs SPIKE-005:** `ruff check` (I001 + ASYNC1xx) is clean under libcst — a genuine capability gain
  over token-level unasync — but does not change the content-absence-driven aggregate NO-GO.

## Known Stubs

None. All artifacts are real transcripts against live commands; no placeholder values or mocked-empty data. The
generated `client_generated.py` is a genuine transform output (its self-import residual is the honest finding, not a stub).

## Threat Flags

None. The spike introduces no new security surface. `aio.py` (`git diff --exit-code .../aio.py`), all of `packages/`
after the item-6 `/tmp` sandbox (`git diff --exit-code packages/`), and `uv.lock` (libcst ephemeral only — D-05) are all
verified byte-unchanged; `client.py` used only as a `diff` oracle, never parsed as a donor (D-02); no `.env` read.

## Next Phase Readiness

- **Plan 18-03** (aggregation) now has all 001a per-item verdicts (1 FAIL, 2 PASS, 3 FAIL, 4 PASS, 5 PASS, 6 FAIL, 7 PASS,
  9 PASS) plus Plan 01's items 8/10a/10b PASS — enough to compute the signed D-04 verdict. On the current evidence the
  milestone lands on a **NO-GO** with items 1/4/6's decisive pair (1, 6) failing for the same source-shape root cause →
  REFAC-06 permanently shelved. Q2 (purity scope) and Q3 (docstring divergence) are flagged for operator ratification in
  `DECISION.md`.

## Self-Check: PASSED

- All 12 001a spike files + `18-02-SUMMARY.md` verified present on disk.
- All 3 task commits (`c0fcac6`, `a616258`, `acc44a7`) verified in `git log`.
- `packages/` (incl. ámbito `aio.py`/`client.py`/`_core.py`) + `uv.lock` verified byte-unchanged; no `.env` touched.
