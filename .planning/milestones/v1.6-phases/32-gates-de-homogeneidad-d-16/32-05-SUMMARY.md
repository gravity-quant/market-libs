---
phase: 32-gates-de-homogeneidad-d-16
plan: 05
subsystem: tooling
tags: [d-16, enrollment-lists, mypy-scope, import-linter, red-fixture, subprocess, non-vacuity, atomic-commit]

# Dependency graph
requires:
  - phase: 32-gates-de-homogeneidad-d-16
    plan: 02
    provides: "The Wave 1 tracer slice — the CI-green baseline plus the precedent that a gate's non-vacuity proof is an automated test in the 6x2 matrix, never a manual demonstration recorded in a SUMMARY"
  - phase: 31-endpoints-de-ops-estructura-uniforme
    provides: "WR-05 — the market_data_client entry in import-linter `root_packages` and its `_core` contract, which this plan proves rather than adds"
  - phase: 29-decoder-observable
    provides: "tools/check_decode_intactness.py — the typed ExemptPackage(reason, resolved_by) record whose forward reference named this phase as its resolver, and the fixed-argv subprocess precedent Task 2 copies"
provides:
  - "All six package src trees enrolled in `[tool.mypy] files` — the single real code gap of D-16, closed (62 -> 75 source files, zero fixes required)"
  - "packages/market-data-client/tests/test_core_boundary_red.py — the first import-linter RED fixture in this repository; the `_core` boundary contract has now been OBSERVED failing, not merely reported KEPT"
  - "The two deliberate exclusions written down with their structural reasons: wallets from `root_packages` (D-10), market-data + wallets from `_PACKAGES` (D-11)"
  - "The dangling forward reference in check_decode_intactness.py's wallets `resolved_by` no longer dangles — it records a settled outcome in the past tense"
affects: [32-06, phase-33-live-verification, phase-34-republish]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Contract roster read from `[tool.importlinter]` at runtime via tomllib rather than hardcoded, so a sixth contract cannot fall outside the 'all the others stayed KEPT' assertion"
    - "Mutate-and-restore with a PROOF of restoration: `try/finally` write-back, then byte-equality assertion plus a green re-run inside the same test body (OQ-3)"
    - "Repo-root resolution anchored on the `[tool.importlinter]` marker rather than on the mere presence of a pyproject.toml — this file's own package has one two levels up, and that is not the config the linter reads"
    - "A missing executable is an assertion failure, never a skip — a gate that silently skips when its tool is absent reports green for the wrong reason"

key-files:
  created:
    - "packages/market-data-client/tests/test_core_boundary_red.py"
    - ".planning/phases/32-gates-de-homogeneidad-d-16/32-05-SUMMARY.md"
  modified:
    - "pyproject.toml"
    - "verification/test_public_surface.py"
    - "tools/check_decode_intactness.py"

key-decisions:
  - "32-05: the automated RED route was taken over the manual demonstration CONTEXT.md D-02 leaned toward, because the cost premise behind that lean ('decenas de segundos') was measured wrong — lint-imports runs in ~0.06 s. The criterion said only 'RED-probado', so the cheaper route was conforming; it was rejected on merit, not on necessity"
  - "32-05: the other four contract names are READ from pyproject.toml at runtime, not hardcoded. A hardcoded four would have been a seventh package roster in a phase whose whole subject is rosters that drift apart"
  - "32-05: the RED leg's restoration is asserted, not trusted — byte-equality against the text read at the start, plus a fresh green invocation, both inside the test body after `finally`"
  - "32-05: Task 2 lands in its own commit and this does NOT break criterion 4's atomicity, because it touches no enrollment list — atomicity is a property of the four lists moving together, not of the plan having one commit"
  - "32-05: `# noqa` must never appear in prose comments in this repo — ruff parses it as a directive wherever it sees it. Two self-inflicted lint findings came from writing about noqa rather than using it"

patterns-established:
  - "A declared-but-never-falsified contract is an assertion about the tool, not about the code. Proving it costs one test"
  - "Prove the proof: after writing a RED fixture, neuter its mutation and confirm the fixture FAILS. A RED test that passes with a no-op mutation is testing nothing"

requirements-completed: []

# Metrics
duration: 7min
completed: 2026-08-25
status: complete
---

# Phase 32 Plan 05: D-16 atomic reconciliation + import-linter RED proof Summary

**The four enrollment lists now agree in one commit — one substantive edit (`packages/market-data-client/src` into mypy `files`, 62 → 75 source files, zero fixes) plus two deliberate exclusions written down with their structural reasons — and the `market_data_client._core` boundary contract has for the first time in this repository been observed FAILING under a deliberate violation instead of merely reported KEPT.**

## Performance

- **Duration:** ~7 min
- **Started:** 2026-08-25T21:31:59Z
- **Completed:** 2026-08-25T21:38:31Z
- **Tasks:** 2
- **Files created/modified:** 4 (1 created, 3 modified)

## Task Commits

1. **Task 1 — the atomic D-16 reconciliation** — `461b8d1` (fix), exactly three files: `pyproject.toml`, `verification/test_public_surface.py`, `tools/check_decode_intactness.py`
2. **Task 2 — the import-linter RED proof** — `f72b766` (test), one new file, 192 lines

## Accomplishments

- **Criterion 4 of Phase 32 is closed.** The roadmap's framing ("reconciliar 4 listas") was stale and research was right: three of the four lists were already correct. The one real gap is filled, the two deliberate exclusions are documented rather than silently tolerated, and the forward reference that named this phase as its own resolver now records an outcome.
- **The repository's first import-linter RED fixture exists.** Five `forbidden` contracts have been declared since Phase 7 and reported KEPT on every CI run since, with no fixture anywhere demonstrating that any of them would fail if violated. That is an assertion about the linter, not about the code. The market-data one is now falsifiable.
- **The proof was itself proven.** Neutering `_VIOLATION` to `""` makes the RED leg **fail** at the `returncode != 0` assertion — so the test genuinely depends on the mutation happening, rather than passing for an ambient reason.
- **A wrong cost premise was retired with evidence.** `32-CONTEXT.md` D-02 priced the subprocess route at "decenas de segundos" and steered toward a manual demonstration. Measured here end to end: the whole two-test file runs in **0.19 s**, three `lint-imports` invocations included.

## Task 1 — the state of each of the four lists

| # | List | Location | State found | Action taken |
|---|------|----------|-------------|--------------|
| 1 | mypy `files` | `pyproject.toml:97` | 5 packages; `packages/market-data-client/src` **absent** | **Edited.** The only substantive code change in all of D-16 |
| 2 | import-linter `root_packages` | `pyproject.toml:147-153` | 5 entries, **already includes** `market_data_client`; contract at `:182-186` KEPT | **Not edited** (D-01). Editing it would have contradicted the decision |
| 3 | `ci.yml` mypy-tests loop | `.github/workflows/ci.yml:95` | 6 packages, complete | **Not edited** |
| 4 | `verification/test_public_surface._PACKAGES` | `verification/test_public_surface.py:46-51` | 4 entries | **Comment only** (D-11); list unchanged at four |

`mypy` went from `no issues found in 62 source files` to `no issues found in 75 source files` — exactly the count research predicted, with **zero** fixes required.

### The two exclusions, and why each is structural rather than preferential

**wallets out of `root_packages` (D-10).** It is the only pre-Phase-7 package and has no `_core.py` — nor `_state.py`, `_transport.py`, `_decode.py`, `_logging.py`. There is therefore no `source_modules` value against which a `forbidden` contract of the shape the other five use could be written. This is now recorded in `check_decode_intactness.py`'s `ExemptPackage.resolved_by`, in the past tense, naming both Phase 32 and the specific list it stays out of so a reader can verify the claim against `pyproject.toml` directly. The `reason` field was left byte-for-byte untouched; the whole change is **6 insertions, 1 deletion**.

**market-data and wallets out of `_PACKAGES` (D-11).** `verification/` has never executed in CI — the `test` job passes an explicit `packages/${{ matrix.package }}` path that overrides `testpaths`. A snapshot added there would go **red-invisible** after the first surface change: a net reporting nothing whether or not the surface drifted, which is strictly worse than a documented gap. Market-data's real coverage already exists in-package at `packages/market-data-client/tests/test_public_surface_market_data.py` — which *does* run in the 6×2 matrix, and which already carried the reciprocal half of this note from the other side. The new comment names it by path, completing the pair.

## Task 2 — the observed output (quoted, as the plan requires)

The exact marker wordings were read off real runs during execution rather than recalled. Clean tree:

```
market_data_client._core does not depend on transport modules KEPT

Contracts: 5 kept, 0 broken.
```

With `_core.py` carrying `from market_data_client import client`, the same fixed-argv invocation exits **1** and produces:

```
ambito_financiero_client._core does not depend on transport modules KEPT
higyrus_client._core does not depend on transport modules KEPT
iol_client._core does not depend on transport modules KEPT
matriz_client._core does not depend on transport modules KEPT
market_data_client._core does not depend on transport modules BROKEN

Contracts: 4 kept, 1 broken.

----------------
Broken contracts
----------------

market_data_client._core does not depend on transport modules
-------------------------------------------------------------

market_data_client._core is not allowed to import market_data_client.client:

-   market_data_client._core -> market_data_client.client (l.1269)
```

Note the dependency count moves `141 → 142`: the mutation is **surgical**, adding exactly one edge, which is why the other four contracts stay KEPT and the failure is attributable to this contract rather than to a collapsed run.

### What the two tests pin

1. **`test_core_boundary_contract_is_kept_on_the_clean_tree`** — the upper bound. Exit 0, the contract name followed by `KEPT`, every *other* declared contract also `KEPT`, and `Contracts: 5 kept, 0 broken.`. Without it, the RED leg could be green for the wrong reason — a permanently broken contract or an unreadable config would make "it went red under mutation" meaningless.
2. **`test_core_boundary_contract_is_red_when_violated`** — the lower bound, the actual proof. Exit non-zero, the contract name followed by `BROKEN`, the other four still `KEPT`, `Contracts: 4 kept, 1 broken.`. Then, after `finally` restores the file: byte-equality with the text read at the start, and a fresh green invocation.

The other four contract names are **read from `[tool.importlinter]` via `tomllib` at runtime**, not hardcoded. Hardcoding them would have created a seventh package roster inside the very phase whose subject is rosters that drift apart, and would let a future sixth contract fall silently outside the assertion.

### Non-vacuity of the fixture itself

Not assumed. `_VIOLATION` was temporarily set to `""` and the suite re-run:

```
FAILED packages/market-data-client/tests/test_core_boundary_red.py::test_core_boundary_contract_is_red_when_violated
1 failed, 1 passed in 0.14s
```

failing at line 180, `assert result.returncode != 0`, with the linter reporting `Contracts: 5 kept, 0 broken.`. The file was then restored and re-verified at 2 passed. A RED fixture that still passes when its mutation is a no-op is testing nothing; this one does not.

## Threat mitigations applied

| Threat | Mitigation as built |
|--------|--------------------|
| T-32-19 (mutating a tracked file) | `try/finally` restore with `encoding="utf-8"`, then byte-equality assertion **and** a green re-run. `git status --porcelain` on `_core.py` is empty after every run performed during this plan |
| T-32-20 (subprocess) | `shutil.which("lint-imports")` → fixed single-element argv, `shell=False`, nothing interpolated from repository content. AST check confirms no `shell=True` anywhere in the file |
| T-32-21 (passing for the wrong reason) | Both legs assert contract name + state marker + the other contracts' state + the summary count line. `python -m importlinter.cli` is banned **in the docstring with its reason** (no `__main__` guard — exits 0 having executed nothing) |
| T-32-22 (silent skip) | A missing executable is an `assert`, never a skip. Zero skip calls in the file |
| T-32-24 (scope creep) | `root_packages` and the contract blocks show 0 changed lines; `_PACKAGES` still has exactly 4 entries; the six out-of-scope `verification/` rosters show no git status output |
| T-32-SC (installs) | Zero installs. `uv.lock` untouched |

## Verification evidence

| Check | Result |
|-------|--------|
| `uv run mypy` | exit 0 — **`no issues found in 75 source files`** (was 62) |
| mypy `files` has 6 entries incl. market-data | **OK** (tomllib assertion) |
| `root_packages` / contract blocks edited | **0** / **0** changed lines |
| `_PACKAGES` entry count | **4** (AST assertion) |
| `grep -c test_public_surface_market_data.py verification/test_public_surface.py` | **1** |
| wallets `resolved_by` states the settled outcome | **OK** — contains `Phase 32` and `root_packages` |
| exemption `reason` field touched | **0** changed lines |
| `git diff --numstat tools/check_decode_intactness.py` | **6 / 1** — well under the 12-line ceiling |
| `uv run python tools/check_decode_intactness.py` | exit 0, digest **`ac14868282ad0a5c`** unchanged |
| `uv run lint-imports` | exit 0 — **5 kept, 0 broken** |
| `uv run pytest .../test_core_boundary_red.py -q` | **2 passed in 0.19s** |
| `git status --porcelain -- .../\_core.py` after the suite | **empty** |
| contract named per leg | **3** occurrences (≥ 2 required) |
| skip calls in the RED file | **0** |
| `shell=True` in the RED file | **0** (AST assertion) |
| `uv run mypy packages/market-data-client/tests` | exit 0 — 29 source files (was 28) |
| `uv run ruff check . && ruff format --check .` | exit 0 — 235 files formatted |
| `uv run pytest packages/market-data-client -q` | **578 passed** |
| Full package suite | **1692 passed**, 1 deselected (1690 + the 2 new) |
| Sibling gates still green | `check_surface_types.py` 6/178/319/23/**0 violations**; `check_uniform_structure.py` green |
| Out-of-scope `verification/` rosters | untouched — no git status output |
| Task 1 commit contents | exactly the three named files |

## Deferred debt (D-12 — recorded, not silenced, and not tidied in passing)

The criterion-4 scope is the four lists it names. These other package rosters exist and were **deliberately left alone**; documenting them by path is what makes this a deferral rather than an omission:

- `verification/test_async_cancellation.py`
- `verification/test_logging_no_token_leak.py`
- `verification/test_max_retries_validation.py`
- `verification/test_findings_dedupe_by_title.py`
- `verification/test_async_configure_resource_warning.py`
- `verification/test_sync_async_isolation.py`
- `tools/check_decode_intactness.py` — the `IN_SCOPE_PACKAGES` / `EXEMPT_PACKAGES` **membership** tuples (only the wallets `resolved_by` string changed; no membership moved)

Note that the first six live under `verification/`, which never executes in CI — so their drift is currently unobservable by any automated means. That is the more interesting half of this debt and is the reason it deserves a future decision rather than a silent carry-forward.

## Deviations from Plan

**None — plan executed exactly as written.** No deviation rule fired: no bug was auto-fixed, no missing critical functionality was added, no blocker required a workaround, and no architectural change arose. No package was installed.

Three things worth flagging that are **not** deviations:

1. **Two self-inflicted ruff findings during Task 2, both fixed pre-commit.** (a) `RUF100` — a `# noqa: S603` on the `subprocess.run` call, unused because flake8-bandit is not in this repo's `select` list; replaced with a plain explanatory comment. (b) An "Invalid `# noqa` directive" warning caused by *writing about* `# noqa` in a prose comment — ruff parses the token wherever it appears in a comment. Rephrased. Neither changed behaviour. **Lesson worth keeping: never write a bare `# noqa` inside prose in this repo.**
2. **One acceptance criterion caught a phrasing problem, exactly as designed.** `grep -c 'pytest.skip'` returned **1** — from a comment saying the assertion was "deliberately not a `pytest.skip`". The criterion is a blunt grep and cannot distinguish a mention from a call, which is arguably a feature: the sentence was rewritten to "never a skip" rather than the criterion being argued with. Same shape as Plan 32-02's decision 4.
3. **Task 2 landed in its own commit, and criterion 4's atomicity holds.** Atomicity is a property of the four enrollment lists never being observably inconsistent with each other between commits. Task 2 touches no enrollment list — it adds one test file — so `461b8d1` is the atomic reconciliation in full, and `f72b766` cannot break it.

---

**Total deviations:** 0
**Impact on plan:** None. Scope held exactly to the four named files.

## Issues Encountered

- **None blocking.** The two ruff findings above were resolved inside their own task before its commit.
- **Accepted risk, recorded rather than eliminated (the plan's own flagged assumption).** The RED leg mutates a tracked file. A `SIGKILL` between the write and the `finally` would leave the tree dirty, and a future move to parallel test execution (`pytest-xdist`) would let another test observe the mutated file. Neither has been exercised. The failure is loud and undone by a single `git checkout` of one file, which is why OQ-3 chose this over a ~30-line tmp-tree copy. The docstring flags the parallelism caveat in situ so it is not left for someone to rediscover.
- **Carry-forward, unchanged:** the `verification/` matriz probes still call `probe_login_sync()` with the pre-15-05 signature. This plan does not move that needle. Plan 32-06 must still re-check that debt before claiming a full-matrix green.

## Known Stubs

**None.** No hardcoded empty return, no placeholder text, no TODO/FIXME, no component awaiting a data source. Every symbol the plan's artifact list names is implemented and exercised.

## User Setup Required

None. Every command in this plan is offline — no credential, no `.env`, no network call. `lint-imports` reads source statically and never imports a package module, so no `load_dotenv()` runs anywhere in this work.

## Next Phase Readiness

**Ready.** Plan 32-06 inherits:

- **mypy at 75 source files** across all six packages — the src-global count Plan 32-02 predicted would move here. Any new package source is now type-checked by default rather than by enrollment.
- **The suite at 1692 passing**, `check_decode_intactness.py`'s digest still `ac14868282ad0a5c`, and all five gates green.
- **A working import-linter RED pattern** if a second contract ever needs the same proof — the file is parameterised on the contract name and reads the roster from config, so a sibling proof is a copy plus one constant.
- **Criterion 4 closed**, leaving 32-06 owning `requirements mark-complete GATE-TYP-01` and the full-matrix green claim.

`requirements-completed` is deliberately **empty**: all six Phase 32 plans carry `GATE-TYP-01`, and this plan delivers criterion 4 but not criteria 1-3 or 5. Marking it complete here would flip the traceability table for work that plan 32-06 has not finished — the same reasoning Plans 32-01 and 32-02 recorded.

## Self-Check: PASSED

- `packages/market-data-client/tests/test_core_boundary_red.py` — FOUND (192 lines)
- `pyproject.toml` — FOUND (contains `packages/market-data-client/src`)
- `verification/test_public_surface.py` — FOUND (contains `test_public_surface_market_data.py`)
- `tools/check_decode_intactness.py` — FOUND (`resolved_by` contains `Phase 32` and `root_packages`)
- Commit `461b8d1` — present in git history
- Commit `f72b766` — present in git history

---
*Phase: 32-gates-de-homogeneidad-d-16*
*Completed: 2026-08-25*
