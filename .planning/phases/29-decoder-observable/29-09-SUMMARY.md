---
phase: 29-decoder-observable
plan: 09
subsystem: infra
tags: [ci, gate, intactness, hashing, normalization, ruff, ban-list, exemption, dec-01]

# Dependency graph
requires:
  - phase: 29-decoder-observable
    plan: 05
    provides: "The five-line `_decode.py` delta (the exception SYMBOL appears at the import AND the raise site) and the two `higyrus`-naming comments kept verbatim in every copy"
  - phase: 29-decoder-observable
    plan: 06
    provides: "matriz's marker-region contract — the D-22 `auth_basic` pre-scan block sits ABOVE the marker region, so the marker-delimited region diffs empty against higyrus; also the one genuinely different `POLICY` constant"
  - phase: 29-decoder-observable
    plan: 07
    provides: "The formatter-reflow finding — substituting the package name into the two ContextVar declarations changes LINE COUNT in opposite directions (iol 3->1, ambito 1->3), so a byte-compare normalizer false-positives on two of five copies"
  - phase: 29-decoder-observable
    plan: 03
    provides: "The contiguous `# --- decode-intactness: generic-scan begin/end ---` marker region in `_logging.py` that Check B hashes"
provides:
  - "`tools/check_decode_intactness.py` — four-check gate: normalize-then-hash over five `_decode.py` copies, marker-delimited hash over five `_logging.py` scan regions, a call-shaped ban list, and the explicit package roster"
  - "The eight written normalization rules — the only sanctioned place to record a legitimate difference between copies"
  - "Rule 8 (re-format the normalized text) proven load-bearing: without it the five copies produce THREE distinct hashes, exactly the split Plan 07 predicted"
  - "`.github/workflows/ci.yml` `decode-intactness` step in the `lint` job — a job that actually executes, unlike `verification/`"
  - "`29-WALLETS-EXEMPTION.md` — the evidence-backed five-plus-one reading, cross-referenced with the checker's roster constants"
  - "Four RED fixtures proven: injected decode drift, removed marker, ban-list construct, exempt package acquiring a `_decode.py`"
affects: [29-10, 31-estructura-uniforme, 32-gates-homogeneidad]

actuals:
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Normalize-then-REFORMAT-then-hash: when the text being compared is subject to an auto-formatter and the substituted token changes length, canonicalizing layout after substitution is the only comparison that is a pure function of the normalized text"
    - "AST-driven line-range surgery computed against the ORIGINAL line numbering and applied in a single pass, so earlier edits cannot shift later spans"
    - "Marker-delimited comparison region instead of a hardcoded per-variant expected hash — the one legitimate package-specific block is outside the comparison by construction, and cannot rot on the next edit"
    - "Call-shaped and keyword-shaped ban-list patterns, never bare-name, so a docstring discussing the banned concept in prose cannot fail the build"
    - "A gate's roster constant as the machine-visible record of scope, with the prose exemption document and the constant naming each other so neither can be updated in isolation"
    - "Closed-world roster check: fail on a package that is on NEITHER the in-scope list nor the exemption list, so new scope cannot enter silently"

key-files:
  created:
    - tools/check_decode_intactness.py
    - .planning/phases/29-decoder-observable/29-WALLETS-EXEMPTION.md
  modified:
    - .github/workflows/ci.yml

key-decisions:
  - "**Rule 8 — re-format the normalized text with `ruff format` before hashing — is the plan's central technical decision, and it is proven load-bearing rather than assumed.** Plan 07 handed over the finding that substituting the package name reflows the ContextVar declarations in opposite directions. A probe that disables ONLY rule 8 produces **three distinct hashes** across the five copies: higyrus / market-data / matriz agree, iol diverges one way, ambito the other. With rule 8 the five collapse to one. That is the false-positive Plan 07 warned about, reproduced and then eliminated."
  - "**Comments are deliberately KEPT inside the hashed body**, which settles Plan 05's and Plan 07's open hand-off item 4 (the two `higyrus`-naming comments) once for all five copies. They were kept verbatim everywhere, so they hash identically and need no normalization rule at all. The tempting alternative — normalizing via `ast.unparse` — would have discarded every comment and let a copy's commentary drift silently. Layout canonicalization was therefore done with `ruff format`, which preserves comments, not with the AST round-trip."
  - "**Check B hashes the marker-delimited region and deliberately has NO second expected hash for matriz.** matriz's D-22 `auth_basic` pre-scan block sits above the `begin` marker, so it is outside the comparison by construction. A hardcoded variant hash would have to be regenerated on every legitimate edit to the region and would rot into a rubber stamp."
  - "**The ban-list patterns are keyword-shaped and call-shaped on purpose, and the source comment says why.** `\\bstrict\\s*=\\s*False\\b` cannot match `strict_decode: bool = False` — there is no word boundary between `strict` and the `_` that follows — and it cannot match the decode docstring's prose about strict mode. A bare-name `strict` or `msgspec.field` pattern would fail the build on a docstring, which is how a gate gets weakened into a suppression."
  - "**Check D is closed-world, not just a presence check.** Beyond asserting that the five in-scope packages have a `_decode.py` and that the exempt one does not, it fails on any directory under `packages/` that appears on neither list. Without that third assertion a seventh package could enter the workspace and silently escape the copy contract — the roster would remain 'correct' while no longer describing the repository."
  - "**The gate went into the `lint` job, not `verification/` and not the `test` job.** `pyproject.toml` sets `testpaths = [\"packages\", \"tests\", \"verification\"]`, but `ci.yml`'s test job runs `pytest packages/${{ matrix.package }}` — an explicit path argument that OVERRIDES `testpaths`. Everything under `verification/` has therefore never executed in CI. The `lint` job runs unconditionally on every push and PR."
  - "**`wallets-client` is exempt because it has nothing to attach a walker to, and the evidence is structural rather than a judgement call.** It has no `_state.py`, no `_logging.py`, no `_core.py`, no `models.py`; it declares no `Client` or `AsyncClient` class at all; its `_request` is a module-level function, not a method; and it has no response models for a walker to serve. Phase 31 gives it the shared layout; Phase 32's D-16 settles its enrollment."

patterns-established:
  - "Prove the normalizer's hardest rule is load-bearing by DISABLING it and showing the check goes red — a normalization rule that cannot be shown to matter is indistinguishable from an over-normalization that hides drift"
  - "Every RED fixture is exercised and reverted in the same session, with the revert re-verified green, so 'the gate fails loudly' is an observation rather than a claim"
  - "A gate that skips a package records WHY in a constant the gate itself prints on success, so a green CI log states its own scope"

requirements-completed: [DEC-01]

coverage:
  - id: D1
    description: "The five `_decode.py` copies reduce to exactly one canonical hash under written normalization rules"
    requirement: "DEC-01"
    verification:
      - kind: command
        ref: "`uv run python tools/check_decode_intactness.py` -> `Check A  decode-helper intactness: 5 copies of `_decode.py` reduce to one normalized hash a5889d5778f11dde`, exit 0"
        status: pass
      - kind: command
        ref: "Probe disabling ONLY rule 8 (`_ruff_format` replaced by identity): 3 distinct hashes — higyrus/market-data/matriz `a59470a3af52`, iol `06a35c454639`, ambito `2afde1561327`. Rule 8 is load-bearing and reproduces Plan 07's predicted split exactly."
        status: pass
    human_judgment: false
  - id: D2
    description: "Check A is non-vacuous — injected drift in one copy makes it exit non-zero and print a unified diff"
    requirement: "DEC-01"
    verification:
      - kind: command
        ref: "Appended `_DRIFT_SENTINEL = \"this copy is no longer a copy\"` to `iol-client/_decode.py` -> exit 1, `2 distinct normalized hashes across 5 copies`, `Copies disagreeing with `higyrus-client`: iol-client`, per-copy hash roster, and a unified diff whose `+` lines are the injected statement. `git checkout --` on that one file -> exit 0 again."
        status: pass
    human_judgment: false
  - id: D3
    description: "Check B is non-vacuous in both failure modes — a removed marker and real drift inside the region"
    requirement: "DEC-01"
    verification:
      - kind: command
        ref: "Removed the `begin` marker from `matriz-client/_logging.py` -> exit 1 with a message naming the file and reporting `found 0 begin and 1 end`. Reverted -> green."
        status: pass
      - kind: command
        ref: "Changed `_MAX_SCAN_DEPTH = 4` to `5` inside higyrus's region only -> exit 1, `scan regions have drifted`, with the unified diff. Reverted -> green."
        status: pass
    human_judgment: false
  - id: D4
    description: "Check C reports every banned construct with file and line, and its patterns cannot fire on prose"
    requirement: "DEC-01"
    verification:
      - kind: command
        ref: "Injected `_BANNED = dict(strict=False)` into `iol-client/_decode.py` -> exit 1 with `packages/iol-client/src/iol_client/_decode.py:73: `strict=False` -- ...` plus the offending source line. Reverted -> green."
        status: pass
      - kind: command
        ref: "Baseline `grep -rnE '\\bstrict\\s*=\\s*False\\b|\\bmsgspec\\s*\\.\\s*field\\s*\\(' packages/*/src/` -> no matches, despite `strict_decode: bool = False` appearing in five `_state.py` files and the decode docstrings discussing strict mode in prose. The word-boundary and paren anchors are what make that true."
        status: pass
    human_judgment: false
  - id: D5
    description: "Check D fails if the exempt package acquires a decode module"
    requirement: "DEC-01"
    verification:
      - kind: command
        ref: "`touch packages/wallets-client/src/wallets_client/_decode.py` -> exit 1 with `exempt package `wallets-client` has acquired a `_decode.py` -- move it into IN_SCOPE_PACKAGES and update .planning/.../29-WALLETS-EXEMPTION.md`. Removed -> green."
        status: pass
      - kind: command
        ref: "Roster names exactly five in-scope directories and one exemption; the green summary line prints both counts and the exemption document path."
        status: pass
    human_judgment: false
  - id: D6
    description: "The gate runs in a CI job that actually executes, and the tests job is unchanged"
    requirement: "DEC-01"
    verification:
      - kind: command
        ref: "YAML parse of `ci.yml` -> the `lint` job's step names are `[checkout, Instalar uv, Verificar uv.lock, Sync workspace, ruff check, ruff format --check, import-linter, lint-logging, decode-intactness]` — the new step is index 8, immediately after the cross-package grep gate at index 7."
        status: pass
      - kind: command
        ref: "`git diff -U0 .github/workflows/ci.yml` -> a single hunk `@@ -50,0 +51,5 @@`. The tests job begins at line 91; no hunk touches it."
        status: pass
    human_judgment: false
  - id: D7
    description: "The wallets exemption is recorded with evidence and is machine-visible in the checker"
    requirement: "DEC-01"
    verification:
      - kind: command
        ref: "`29-WALLETS-EXEMPTION.md` lists the four modules wallets has and the six families it lacks (table), quotes its three module-level state globals, cites `client.py:57` / `aio.py:73` as module-level `_request` definitions, names Phase 31 and Phase 32, and enumerates the three affected criteria (filter fix, caplog sentinels, intactness roster)."
        status: pass
      - kind: command
        ref: "Cross-reference is bidirectional: the checker's `EXEMPTION_DOC` constant names the file and prints it in Check D's summary and both failure messages; the document names `IN_SCOPE_PACKAGES` and `EXEMPT_PACKAGES`."
        status: pass
    human_judgment: false
  - id: D8
    description: "The checker never imports package source"
    requirement: "DEC-01"
    verification:
      - kind: command
        ref: "The script imports only `ast`, `difflib`, `hashlib`, `re`, `subprocess`, `sys`, `dataclasses`, `pathlib`. Every package file is read via `Path.read_text` and parsed with `ast.parse`; there is no `import`/`importlib` of a package module, so no import-time `load_dotenv()` or client construction runs inside the gate (T-29-52)."
        status: pass
    human_judgment: true
    rationale: "The absence of a dynamic import is visible in a 637-line source with a fixed import block, and the only subprocess call is a fixed argv invoking `ruff format` on stdin. A reader must confirm no future edit introduces an `importlib` call; the check is structural, not mechanically enforced."
  - id: D9
    description: "The repo's own quality gates stay green with the new file"
    requirement: "DEC-01"
    verification:
      - kind: command
        ref: "`uv run ruff check .` -> All checks passed. `uv run ruff format --check .` -> 215 files already formatted. `uv run mypy tools/check_decode_intactness.py` -> Success: no issues found in 1 source file. `uv run lint-imports` -> Contracts: 4 kept, 0 broken."
        status: pass
      - kind: test
        ref: "`uv run pytest packages/higyrus-client packages/matriz-client packages/market-data-client -q --no-cov` -> 1082 passed (criterion asked for >= 872)."
        status: pass
    human_judgment: false

# Metrics
duration: 24min
completed: 2026-08-19
status: complete
---

# Phase 29 Plan 09: The verbatim-copy contract becomes enforceable Summary

**Five copies of the decode walker now reduce to one canonical hash under eight written normalization rules, five `_logging.py` scan regions reduce to one hash over a marker-delimited region, and the gate runs in the `lint` job — the only CI job on this repo where a cross-package check actually executes — with all four failure modes proven red and reverted green in the same session.**

## Performance

- **Duration:** 24 min
- **Started:** 2026-08-19T14:02:00Z
- **Completed:** 2026-08-19T14:26:00Z
- **Tasks:** 2
- **Files modified:** 2 created, 1 modified

## Accomplishments

- **Plan 07's headline hand-off was reproduced, then eliminated, then proven to have mattered.** The warning was that substituting the package name reflows the two `ContextVar` declarations in *opposite directions* — `iol_client` is short enough that `DECODE_SCOPE` collapses 3→1, `ambito_financiero_client` long enough that `STRICT_DECODE` expands 1→3 — so a substitute-then-byte-compare normalizer reports a false divergence on two of five copies. The fix is normalization rule 8: re-format the normalized text with `ruff format` at a fixed line length, so the layout of every copy is a function of the normalized text alone. A probe that disables **only** rule 8 produces **three distinct hashes** in exactly the predicted split (higyrus/market-data/matriz together, iol alone, ambito alone). With rule 8, one hash. The rule is load-bearing and now has evidence, not an argument.
- **The naive approach was measured, not just described.** A `sed`-substitute-then-`diff` normalizer over the five copies yields 4 differing lines for market-data, 6 for matriz, but **8 each** for iol and ambito — the extra four are pure reflow noise, with nothing to do with the walker.
- **The two `higyrus`-naming comments are settled once, for all five copies** — Plan 05 and Plan 07 both left this open and asked Plan 09 to decide. The decision: **keep comments inside the hashed body and normalize nothing about them.** They were kept verbatim everywhere, so they already hash identically. This also rules out the tempting `ast.unparse` normalizer, which would have canonicalized layout for free but discarded every comment in the process, letting a copy's commentary drift with the gate still green.
- **matriz's package-specific block is outside the comparison by construction, with no variant hash to rot.** Check B extracts only the text strictly between the two marker comment lines. matriz's D-22 `auth_basic` pre-scan sits above the `begin` marker, so it never enters the hash. All five regions are 54 lines and already byte-identical after package-name substitution.
- **All four failure modes are proven, and every fixture was reverted and re-verified green.** Injected drift in a decode copy → exit 1 with a per-copy hash roster and a unified diff. Removed marker → exit 1 naming the file and reporting `found 0 begin and 1 end`. `_MAX_SCAN_DEPTH = 4` → `5` inside one region → exit 1 with the region diff. `strict=False` injected into a copy → exit 1 with file, line and the offending source line. `touch`ing a `_decode.py` into the exempt package → exit 1 telling the operator to move the roster entry and update the exemption document.
- **The ban list cannot fire on prose, and that is the difference between a gate and a nuisance.** `\bstrict\s*=\s*False\b` does not match `strict_decode: bool = False` (no word boundary before the `_`) and does not match the decode docstring's several sentences about strict mode. `\bmsgspec\s*\.\s*field\s*\(` requires the call paren. The baseline grep over 67 package source files is clean.
- **Check D is closed-world.** It fails not only when an in-scope package loses its copy or the exempt package gains one, but also when a directory appears under `packages/` that is on **neither** list — so a seventh package cannot enter the workspace and silently escape the contract.
- **The gate is in the one job where it will actually run.** `pyproject.toml` declares `testpaths = ["packages", "tests", "verification"]`, but the test job runs `pytest packages/${{ matrix.package }}`, and an explicit path argument overrides `testpaths`. Everything under `verification/` has therefore never executed in CI. The new step sits in `lint`, immediately after the `lint-logging` grep gate, and the tests job's arguments are untouched — the whole `ci.yml` diff is a single five-line hunk at line 51, sixty lines above where the tests job begins.

## Task Commits

1. **Task 1: the normalize-then-hash checker with its ban list and declared exemption** — `dcb1a0c` (feat)
2. **Task 2: wire the gate into the CI lint job + the wallets exemption record** — `b37b95c` (chore)

## Files Created/Modified

- `tools/check_decode_intactness.py` (637 lines, **created**) — the first file in a new top-level `tools/` directory. A plain script with no package imports, runnable as `uv run python tools/check_decode_intactness.py`. Its module docstring is ~110 lines and states the whole contract: why a naive byte comparison fails (three enumerated facts, all properties of the current tree), the eight normalization rules in order, the marker-region construction, why the ban patterns are call-shaped, and where the exemption is written up. Four checks (`check_a_decode_intactness`, `check_b_filter_region_intactness`, `check_c_ban_list`, `check_d_roster`), each printing one summary line on success and raising a `CheckFailure` carrying a fully formed operator-readable message on failure. `main()` runs all four — it does not short-circuit on the first failure, so one run reports every problem — and prefixes each failure with `::error::` plus a final `::error::decode-intactness gate FAILED (N of 4 checks)`.
- `.github/workflows/ci.yml` (+5 lines) — a `decode-intactness` step in the `lint` job, named after this phase and requirement in the style of the neighbouring `lint-logging (Phase 8 LOG-01 — ...)` step, placed immediately after it. Three comment lines record why it is not in the `test` job and not under `verification/`.
- `.planning/phases/29-decoder-observable/29-WALLETS-EXEMPTION.md` (148 lines, **created**) — the module-presence table across all six packages, the quoted module-level state globals, the `client.py:57` / `aio.py:73` module-level `_request` citations, the "nothing to decode" argument, the three affected criteria, the bidirectional cross-reference with the checker's roster constants, and a three-part recipe for what to do when Phase 31 ends the exemption.

## Decisions Made

- **Normalize-then-REFORMAT-then-hash, rather than normalize-then-hash.** Rule 8 invokes `ruff format` on the normalized text with an explicitly pinned `--line-length 100` and `--target-version py312`, rather than letting ruff discover the repo config. The hash only needs all five copies treated *identically*; pinning makes the normalization a pure function of the text, so a future change to the repo's line length reflows the sources without reflowing the comparison. All placeholders are valid Python identifiers and string literals (`__PKG__`, `__DECODE_ERROR__`, `POLICY = "__POLICY__"`, …) precisely so the normalized text still parses and can be re-formatted.
- **Comments stay in the hash; `ast.unparse` was rejected.** `ast.unparse` would have solved the reflow problem in one line, but it discards comments — including the two `higyrus`-naming comments that four of the five copies carry as commentary about a different package. Those comments were kept verbatim by Plans 05, 06 and 07 on the explicit grounds that editing them would be the first crack in the verbatim-copy invariant. Keeping them inside the hash is what makes that decision *enforceable* rather than merely recorded.
- **Line-range surgery is computed against the original line numbering and applied in one pass.** Dropping the docstring, replacing the `POLICY` statement and replacing the decode-error import are all AST-derived spans from the same parse of the untouched source, collected into one `dict[int, str | None]` and applied in a single loop. Doing them sequentially would have invalidated every span after the first edit.
- **The decode-error symbol is normalized as a *name*, not as an import line** — Plan 05's carried-forward finding, confirmed here. The class is found via the `from <pkg>.exceptions import *DecodeError` statement, then every `\bName\b` occurrence is replaced, which covers the `raise` site and any future one.
- **No hardcoded variant hash for matriz.** The plan explicitly forbade modelling matriz's pre-scan block as a second expected hash, and the marker-delimited extraction makes that unnecessary. A variant constant would need regenerating on every legitimate edit to the region, and a constant that gets regenerated on every edit is a rubber stamp.
- **Check D is closed-world rather than a two-sided presence check.** This is an addition beyond the plan's literal wording (see Clarifications) and closes the gap where a new package escapes the roster while both stated assertions still pass.
- **`tools/` is deliberately left out of the mypy `files` roster and the pre-commit mypy hook's `files: ^packages/.*/src/` pattern**, both of which are pre-existing config this plan did not touch. The file is nevertheless clean under the repo's strict settings when checked explicitly, and it *is* covered by `ruff check` and `ruff format` in both the lint job and the pre-commit hook, since neither is path-restricted.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `ruff check tools` rejected an unused `noqa: S603` directive**

- **Found during:** Task 1, at the first `uv run ruff check tools`
- **Issue:** The `subprocess.run` call carried `# noqa: S603` out of habit. This repo's ruff rule set (E, W, F, I, B, UP, SIM, RUF, ASYNC, PIE, PT, RET, TID) does not enable flake8-bandit, so `RUF100` correctly flagged the directive as unused and the task's own `verify` block failed.
- **Fix:** Replaced the `noqa` with a two-line comment stating the actual safety property — fixed argv, no shell, no interpolated user input, the only variable part being stdin, which is repository source the gate already reads.
- **Files modified:** `tools/check_decode_intactness.py`
- **Commit:** `dcb1a0c` (fixed before the task commit)

### Clarifications to acceptance criteria

**1. Check D asserts three things, not the two the plan enumerates.** The plan says "Fail if a package source tree that is in the in-scope list has no decode module, and fail if the exempt package has acquired one." Both are implemented. A third assertion was added: fail if a directory under `packages/` is on **neither** list. Without it, the roster could remain internally consistent while no longer describing the repository — a seventh package would silently escape the copy contract, which is the same class of failure as T-29-51. Treated as Rule 2 (missing critical functionality for correctness of the gate itself) and documented rather than left implicit.

**2. The normalization is stated in the docstring as eight rules, in a different order from the plan's seven.** The plan's rules 1–7 are all present and none was dropped. Two changes: (a) the order was regrouped so that the three AST-derived line-range edits (docstring, `POLICY`, decode-error import) are described together, because they are applied together in one pass against the original line numbering; (b) an eighth rule — re-format the normalized text — was added, because the plan's own `must_haves` and Plan 07's hand-off both require the comparison to survive the formatter reflow, and rules 1–7 alone do not achieve that. The probe result above shows rules 1–7 alone leave three distinct hashes.

**3. The plan's Check B says "apply normalization steps 2 and 7".** In the plan's numbering those are the package-name substitution and the trailing-whitespace/newline normalization; both are applied, and nothing else. The docstring numbering shifted (they are rules 6 and 7 there), so `normalize_scan_region`'s own docstring names them explicitly to avoid ambiguity between the two numberings.

**4. `uv run mypy tools/check_decode_intactness.py` is clean, but `tools/` is outside the configured mypy roster.** `pyproject.toml`'s `[tool.mypy] files` lists five package `src` trees (notably not `market-data-client/src` either), and the pre-commit mypy hook is restricted to `^packages/.*/src/`. The plan's acceptance criterion allows either outcome provided the SUMMARY records it. It is recorded here: the file passes `mypy --strict` when invoked explicitly, and is covered unconditionally by `ruff check` and `ruff format` in both CI and pre-commit. Enrolling `tools/` in the mypy roster would mean editing `pyproject.toml`, which is not in this plan's `files_modified` and which Phase 32's D-16 reconciliation owns.

**5. The commit type for Task 2 is `chore`, not `feat`.** The task's substance is CI wiring plus a planning document — tooling and config — which the commit-type table maps to `chore`. Task 1, which adds the gate itself, is `feat`.

---

**Total deviations:** 1 auto-fixed (Rule 3, blocking lint failure). Five acceptance-criterion clarifications, all documented above.
**Impact on plan:** None on scope. Exactly the three files in `files_modified` were touched; nothing under `packages/` changed in either commit, verified with `git diff --stat HEAD~2..HEAD`.

## Issues Encountered

- **The `ruff format` subprocess needed a valid-Python normalized text.** The first placeholder sketch used bare tokens for the replaced statements, which would not have parsed. Every placeholder was made a valid identifier or string literal (`POLICY = "__POLICY__"`, `from __PKG__.exceptions import __DECODE_ERROR__`) so the normalized body still parses and can be re-formatted. Caught before the first run.
- **The rule-8 probe initially crashed** with `AttributeError: 'NoneType' object has no attribute '__dict__'` inside `dataclasses._process_class` — an artefact of loading the checker via `importlib.util` without registering it in `sys.modules`, which `@dataclass(slots=True)` requires. Registering the module fixed it. Not a defect in the checker; the checker imports and runs normally.
- No other issues. `ruff format --check` passed on the first run for the new file; `mypy --strict` passed on the first run.

## Verification

- `uv run python tools/check_decode_intactness.py` — **exit 0**, four summary lines:
  - `Check A  decode-helper intactness: 5 copies of `_decode.py` reduce to one normalized hash a5889d5778f11dde`
  - `Check B  filter scan-region intactness: 5 marker-delimited regions (54 lines each) reduce to one hash 684191c7cdc5ff9c`
  - `Check C  ban list: `strict=False`, `msgspec.field(` absent from 67 package source files`
  - `Check D  package roster: 5 in-scope packages carry a `_decode.py`; `wallets-client` exempt (see .planning/phases/29-decoder-observable/29-WALLETS-EXEMPTION.md)`
- **RED fixture 1 (Check A):** stray line appended to `iol-client/_decode.py` → exit 1, `2 distinct normalized hashes across 5 copies`, disagreeing copy named, per-copy hash roster printed, unified diff showing the injected statement. `git checkout --` on that file → exit 0.
- **RED fixture 2 (Check B, missing marker):** `begin` marker removed from `matriz-client/_logging.py` → exit 1, message names the file and reports `found 0 begin and 1 end`. Reverted → exit 0.
- **RED fixture 3 (Check B, real drift):** `_MAX_SCAN_DEPTH = 4` → `5` in higyrus's region only → exit 1, `scan regions have drifted`, unified diff. Reverted → exit 0.
- **RED fixture 4 (Check C):** `_BANNED = dict(strict=False)` injected into `iol-client/_decode.py` → exit 1 with `packages/iol-client/src/iol_client/_decode.py:73` and the offending line. Reverted → exit 0.
- **RED fixture 5 (Check D):** `touch packages/wallets-client/src/wallets_client/_decode.py` → exit 1 with the move-the-roster-entry instruction. Removed → exit 0.
- **Rule-8 probe:** with `_ruff_format` replaced by identity, 3 distinct hashes — higyrus `a59470a3af52`, market-data `a59470a3af52`, matriz `a59470a3af52`, iol `06a35c454639`, ambito `2afde1561327`.
- **Naive-normalizer measurement:** `sed`-substitute-then-`diff` against higyrus yields 4 differing lines (market-data), 6 (matriz), **8** (iol), **8** (ambito).
- `uv run ruff check tools` / `uv run ruff format --check tools` — clean.
- `uv run ruff check .` — All checks passed. `uv run ruff format --check .` — **215 files already formatted**.
- `uv run mypy tools/check_decode_intactness.py` — Success: no issues found in 1 source file.
- `uv run lint-imports` — **Contracts: 4 kept, 0 broken.**
- `uv run pytest packages/higyrus-client packages/matriz-client packages/market-data-client -q --no-cov` — **1082 passed** in 66s (criterion asked for ≥ 872).
- YAML parse of `ci.yml` — the `lint` job's step name list ends `..., import-linter (...), lint-logging (Phase 8 LOG-01 — ...), decode-intactness (Phase 29 DEC-01 — ...)`; the new step is index 8, immediately after the grep gate at index 7.
- `git diff -U0 .github/workflows/ci.yml` — one hunk, `@@ -50,0 +51,5 @@`. The tests job starts at line 91; **no hunk inside it**.
- `git diff --stat HEAD~2..HEAD` — exactly three paths: `ci.yml` (+5), `29-WALLETS-EXEMPTION.md` (+148), `tools/check_decode_intactness.py` (+637). `git diff --stat HEAD~2..HEAD -- packages/` — **empty**.
- `git diff --diff-filter=D --name-only HEAD~2..HEAD` — empty; no files deleted.
- `wc -l tools/check_decode_intactness.py` — 637 (min_lines 90).

## Prohibitions status

Both plan prohibitions were carried as `flagged-unverified` and are now satisfied:

- *"The intactness gate must NEVER live under the cross-package verification directory — that directory has never executed in CI because the tests job overrides the configured test paths, so a gate placed there would be inert from the day it was written."* — **Satisfied, and the mechanism was confirmed rather than assumed.** `pyproject.toml` sets `testpaths = ["packages", "tests", "verification"]`, but `ci.yml`'s test job runs `pytest packages/${{ matrix.package }}` with an explicit path argument, and pytest ignores `testpaths` whenever paths are given on the command line. The gate lives at `tools/check_decode_intactness.py` — a new top-level directory, not under `verification/` — and is invoked from the `lint` job, which runs unconditionally on every push and pull request to `main` and has no path argument to override anything. The step's presence is asserted by *parsing* the workflow, not by reading it.
- *"The gate must NEVER be weakened into a vacuous check when it goes red — a red gate means a copy drifted, and the normalization rules are the only sanctioned place to record a legitimate difference."* — **Satisfied in construction and stated in three places in the artifact itself.** The module docstring says it outright ("A red gate means a copy drifted; the fix is to revert the drift or to add a rule here with a stated reason — never to weaken the check into a vacuous one"), Check A's failure message repeats it on every red run ("A legitimate per-package difference belongs in this script's normalization rules, with a stated reason — never in a weakened check"), and Check B's marker-region construction removes the specific temptation the plan named: there is no hardcoded variant hash for matriz that a future executor could regenerate instead of investigating. Check D's failure messages likewise instruct the operator to move the roster entry and update the exemption document, not to delete the assertion. Non-vacuity is demonstrated by five RED fixtures, all reverted.

## TDD Gate Compliance

Neither task carries `tdd="true"` and the plan declares no `<behavior>` block, so the MVP+TDD runtime gate does not fire: under the `task.is-behavior-adding` predicate both tasks are non-behaviour-adding (no `tdd="true"` frontmatter, no `<behavior>` block). No `test(...)` → `feat(...)` gate sequence is required or claimed. The plan's own non-vacuity requirement is discharged by the five RED fixtures above, each injected, observed red, reverted, and re-observed green in the same session — which is the RED half of the TDD contract applied to a gate rather than to a feature.

## Known Stubs

None. All four checks are live and run on every invocation; `main()` deliberately runs all four rather than short-circuiting, so one CI run reports every problem. The `ExemptPackage.reason` and `.resolved_by` fields are read only by human operators reading the source, not by control flow — they are documentation held in a constant on purpose, which is what "machine-visible exemption" means here, and Check D's behaviour (fail if the exempt package acquires a `_decode.py`) is fully live.

## Threat Flags

None. This plan adds no network endpoint, no auth path and no schema at a trust boundary. It adds one file-access surface — the checker reads every `.py` file under `packages/*/src/` and the two module families it hashes — which is the plan's own T-29-52, dispositioned `accept`: the script reads files as text via `Path.read_text` and never imports a package module, so no package import-time side effect runs inside the gate. The one subprocess call is a fixed argv (`sys.executable -m ruff format ...`) with no shell and no interpolated input; the only variable part is stdin, which is repository source the gate has already read.

## User Setup Required

None — no external service configuration required. The gate runs with the workspace already synced by the `lint` job's existing `uv sync` step, and `ruff` is a workspace dev dependency the same job already invokes twice.

## Next Phase Readiness

- **Wave 5's gate half is complete.** DEC-01's "copied verbatim with an intactness check" clause now has the check, and it is proven to fail red in all four of its failure modes.
- **Carried forward for Plan 29-10:** the gate is green on the current tree at hash `a5889d5778f11dde` (Check A) and `684191c7cdc5ff9c` (Check B). Any plan that touches a `_decode.py` or a `_logging.py` scan region must touch **all five copies** or the lint job goes red. There is no per-package escape hatch, by design.
- **Carried forward for Phase 30 (iol typed surface):** writing `iol_client/models.py` does not touch `_decode.py`, so the gate is inert for that work — but the matrix's re-ratification of iol's `POLICY` **is** normalized away by rule 2 and therefore is **not** protected by this gate. `test_policy_constant_matches_the_semantics_matrix` in each package is what pins `POLICY`; that per-package test is the guard, not Check A.
- **Carried forward for Phase 31 (estructura uniforme):** the moment `wallets-client` gains a `_decode.py`, Check D goes red by design. The fix is the three-part edit written at the end of `29-WALLETS-EXEMPTION.md` — move the roster entry, add the `_logging.py` marker region so Check B hashes six, supersede the document. Do not delete the assertion.
- **Carried forward for Phase 32 (gates de homogeneidad):** `tools/` now exists and has one plain, package-import-free script in it — the structural precedent Phase 32's `tools/check_surface_types.py` can follow, including the `::error::` annotation convention, the one-summary-line-per-check output, the `CheckFailure` pattern that reports every problem in one run, and the placement in the `lint` job for the same `testpaths`-override reason. Phase 32's D-16 reconciliation should also decide whether `tools/` joins the mypy `files` roster (see Clarification 4).
- **No blockers.**

## Self-Check: PASSED

Created files verified present on disk: `tools/check_decode_intactness.py` (637 lines), `.planning/phases/29-decoder-observable/29-WALLETS-EXEMPTION.md` (148 lines). Modified file verified present: `.github/workflows/ci.yml`. Both task commits verified present in git history: `dcb1a0c` (feat) and `b37b95c` (chore). The gate itself re-verified exit 0 after the second commit.

---
*Phase: 29-decoder-observable*
*Completed: 2026-08-19*
