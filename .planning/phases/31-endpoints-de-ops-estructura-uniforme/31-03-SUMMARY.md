---
phase: 31-endpoints-de-ops-estructura-uniforme
plan: 03
subsystem: api
tags: [higyrus-client, typing, mypy-strict, dataclasses, safemodel, decode-walker, public-surface-snapshot]

# Dependency graph
requires:
  - phase: 29-decode-walker
    provides: "`_decode.walk_model` / `walk_field`, the `DecodeScope` sink, `STRICT_DECODE`, and the `@_decode._response_parser` scope decorator that this plan applies to `parse_get_health_response`"
  - phase: 30-iol-client-tipado
    provides: "`SafeModel.to_dict()` (D-08) — the verbatim source copied into higyrus's base — plus the CR-01 rule that a `schema_of` fed from a model projection echoes the declaration rather than the wire, and the 30-03 precedent that a dict→model re-mock is fixed on the TEST side"
  - phase: 07-refactor-core
    provides: "`_core.parse_get_health_response` with the CR-02 204 carve-out and the raise-on-non-dict shape guard whose exact strings this plan preserves byte-unchanged"
provides:
  - "`higyrus_client.Health` — a frozen, slotted, one-field `SafeModel` derived verbatim from the committed live capture"
  - "`SafeModel.to_dict()` on higyrus's own base, byte-identical to iol's, copied not imported"
  - "A typed `get_health` on all four signature sites (sync method, sync shim, async method, async shim) plus the parser"
  - "MEASURED strict-decode behaviour of the 204 / empty-body carve-out, pinned by test"
  - "A regenerated `verification/snapshots/higyrus-client-surface.txt`"
  - "The end-to-end tracer recipe (declare → decode → dispatch → re-export → regen golden → strict-typecheck) validated at minimum blast radius before plans 31-04/31-05 scale it"
affects: [31-04, 31-05, 33-drivers-strict-mode, 34-release]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-package verbatim copy of `SafeModel.to_dict()` — never a cross-package import (C-2)"
    - "Model-building parsers carry `@_decode._response_parser`; shape carve-outs live in the parser, never in a `from_api` override"
    - "Public-surface golden regenerated in the SAME commit as the source change, verified locally because CI never runs `verification/`"

key-files:
  created: []
  modified:
    - packages/higyrus-client/src/higyrus_client/models.py
    - packages/higyrus-client/src/higyrus_client/_core.py
    - packages/higyrus-client/src/higyrus_client/client.py
    - packages/higyrus-client/src/higyrus_client/aio.py
    - packages/higyrus-client/src/higyrus_client/__init__.py
    - packages/higyrus-client/tests/test_core.py
    - packages/higyrus-client/tests/test_client.py
    - packages/higyrus-client/tests/test_async_client.py
    - verification/snapshots/higyrus-client-surface.txt
    - main_higyrus.py

key-decisions:
  - "MEASURED: `Health.from_api(None)` — the 204 / empty-body carve-out — emits exactly ONE `non_dict` divergence record and, under `strict_decode=True`, raises `HigyrusDecodeError` instead of returning the zero-valued instance. A legitimate 204 therefore DOES raise in strict mode, on the very branch Phase 7 CR-02 added so it would not."
  - "CONTEXT D-03 CORRECTED: `main_higyrus.py`'s health probes needed NO `to_dict()` call site — they read raw wire via `_raw_request_sync`/`_raw_request_async`, never the typed wrapper. Plan 31-04 MUST re-check each market-data driver site individually rather than generalizing this."
  - "`Health.status` is declared `str`, never `str | None` — `walk_field`'s union branch returns `None` without a divergence record, so an over-declared Optional would erase the signal (T-31-12)."
  - "Test re-mocks were folded into Task 2's RED gate rather than deferred to Task 3, so no commit boundary leaves the suite red outside a deliberate TDD gate."
  - "Two pre-existing mypy errors in higyrus's byte-frozen `test_decode.py` are DEFERRED, not fixed — applying plan 31-02's ratified D-2 precedent (logged as deferred-items D-3)."

patterns-established:
  - "Tracer-slice validation: exercise every mechanic once on the smallest possible model before scaling to deep trees"
  - "Guard-preservation discipline: a dict→model retype corrects the TEST, never the parser's shape guard or its title/detail strings"
  - "Strict-mode behaviour deltas on defensive branches are MEASURED and pinned by test at introduction, not discovered downstream"

requirements-completed: [TYP-02]

# Metrics
duration: 52min
completed: 2026-08-24
status: complete
---

# Phase 31 Plan 03: The Tracer Slice (higyrus `get_health` → `Health`) Summary

**`higyrus_client.Health` — a one-field frozen `SafeModel` wired end to end: declared from the live capture, decoded through the Phase 29 walker, dispatched on both sync and async shells via one shared parser, re-exported, golden-regenerated, and strict-typechecked by CI.**

## Performance

- **Duration:** 52 min
- **Started:** 2026-08-24T01:31:53Z
- **Completed:** 2026-08-24T02:23:28Z
- **Tasks:** 3 (5 commits — TDD RED/GREEN gates)
- **Files modified:** 10

## Accomplishments

- **`Health` model** declared verbatim from `.planning/verification/schemas/higyrus-client/get-health.json`: `@dataclass(frozen=True, slots=True)`, a single `status: str` field, no `received_at`, no `from_api` override.
- **`SafeModel.to_dict()`** added to higyrus's own base, **verified byte-identical** to `iol_client.models`'s method (docstring included) by programmatic comparison — copied, never imported (C-2, T-31-16).
- **All 4 signature sites plus the parser** return `Health`; one shared `_core` parser serves both shells, so sync/async parity is structural rather than duplicated (C-3 / DT-04).
- **The 204 strict-mode behaviour delta was measured, not assumed** — and it matched the plan's backstop prediction exactly.
- **Surface golden regenerated** with the two predicted rows and nothing else; no other package's golden moved.
- **`main_higyrus.py` docstring corrected** with a docstring-only diff, and CONTEXT D-03's assumption corrected for plan 31-04's benefit.

## Task Commits

1. **Task 1: Health model + `SafeModel.to_dict()`** — `5c8e2c7` (test, RED) → `0dd1f7d` (feat, GREEN)
2. **Task 2: Retype parser + 4 signature sites, sync and async** — `2cfd2c0` (test, RED) → `cf4be6e` (feat, GREEN)
3. **Task 3: Golden regen + driver docstring** — `3aa2257` (chore)

No REFACTOR commit was needed: both GREEN implementations landed at production shape.

## Files Created/Modified

- `packages/higyrus-client/src/higyrus_client/models.py` — `Health` model, `SafeModel.to_dict()`, widened imports (`dataclasses`, `cast`), module docstring records D-03 provenance + the Phase 30 CR-01 caveat
- `packages/higyrus-client/src/higyrus_client/_core.py` — `parse_get_health_response` decorated with `@_decode._response_parser`, retyped to `Health`, both return expressions changed; guard untouched
- `packages/higyrus-client/src/higyrus_client/client.py` — `Client.get_health` + module shim retyped
- `packages/higyrus-client/src/higyrus_client/aio.py` — `AsyncClient.get_health` + async module shim retyped
- `packages/higyrus-client/src/higyrus_client/__init__.py` — `Health` imported and added to `__all__` in ASCII sort position (after `"Domicilio"`, before `"HigyrusAPIError"`)
- `packages/higyrus-client/tests/test_core.py` — 7 `Health` behaviour tests, the health-parser re-mocks, a guard-string pinning test, and the strict-decode delta tests (+226 lines)
- `packages/higyrus-client/tests/test_client.py` — shim assertion moved to attribute access; flat-namespace export test added
- `packages/higyrus-client/tests/test_async_client.py` — async shim assertion moved to attribute access
- `verification/snapshots/higyrus-client-surface.txt` — regenerated (2 rows)
- `main_higyrus.py` — `probe_get_health_sync` docstring correction only

---

## 1. MEASURED behaviour of the 204 / empty-body carve-out (plan backstop truth)

This is the item the plan required to be measured at execution and recorded **verbatim** rather than discovered in Phase 33. **The measurement confirms the plan's prediction exactly.**

`parse_get_health_response` now resolves its 204 / empty-body branch to `Health.from_api(None)` (D-04's locked zero-valued-instance shape). Under the Phase 29 walker, a `None` payload takes `walk_model`'s non-dict branch (`_decode.py:575-582`), so:

**Normal mode (`strict_decode=False`, the default):**

- Returns `Health(status="")` — the zero-valued instance, **not** an empty mapping and **not** a raise. The Phase 7 CR-02 contract that a 204 must not raise is **preserved**.
- Emits **exactly ONE** divergence record on the `higyrus_client` logger: `field_path=""`, `divergence="non_dict"`, `model="Health"`, `declared_type="Health"`, `observed_type="NoneType"`, at `WARNING` level.
- The per-field `missing` record for `status` is **suppressed** — lock 8 routes declared fields through `SILENT_SINK` under a non-dict payload, so a 204 emits one record, not one per field.
- Pinned by `test_parse_get_health_response_handles_204` and `test_parse_get_health_response_handles_empty_body_200`.

**Strict mode (`strict_decode=True`):**

- **A legitimate 204 RAISES `HigyrusDecodeError`.** `non_dict` is not in `_INFO_KINDS` (only `extra` is), so `DecodeScope.__call__` emits the record and then raises (`_decode.py:205, 220-221`).
- The raised exception carries `field_path=""`, `declared_type="Health"`, `observed_type="NoneType"`, `model="Health"`.
- The record is still emitted **before** the raise, so a strict run leaves the divergence on the paquete logger.
- Pinned by the parametrized `test_parse_get_health_response_empty_body_raises_under_strict_decode[204]` and `[empty-body-200]`.

**Why this matters:** this is a genuine behaviour delta on the defensive branch Phase 7 CR-02 introduced **specifically so that a 204 would not raise**. Under `strict_decode=True` that carve-out no longer holds. **Phase 33 runs the drivers in strict mode** — if the higyrus health endpoint ever answers 204 (or with an empty body) during a strict driver run, the probe will see `HigyrusDecodeError`, not a healthy zero-valued instance. That is now a known, tested contract rather than a field discovery. The healthy path is unaffected: `test_parse_get_health_response_full_payload_is_strict_clean` confirms a populated `{"status": "ok"}` emits nothing and passes through strict mode untouched.

## 2. CONTEXT D-03 CORRECTION — read this before executing plan 31-04

**CONTEXT D-03 assumed `main_higyrus.py` would need a `to_dict()` call site because the health probes read `isinstance(raw, dict)` and `len(raw)`. That assumption is WRONG for higyrus, and the driver needed no functional change at all.**

Probes 3 and 4 (`probe_get_health_sync` / `probe_get_health_async`) capture the wire through `_raw_request_sync` / `_raw_request_async` — the higyrus analogue of `main_iol.py`'s `_capture_raw_wire`, already present since before this phase. They **never call the typed wrapper**. Their `raw` was therefore never a model, the `isinstance(raw, dict)` and `len(raw)` reads already operate on a raw dict, and they stay drift-visible with zero edits. The only thing that was false was the docstring's parenthetical claim that the wrapper "returns the same dict but with no observable difference" — corrected to state the real reason the probe reads raw wire (keeping probe 15's `schema_of` a function of the WIRE, not of the model declaration — Phase 30 CR-01 / T-31-15). `git diff main_higyrus.py` touches only lines inside a triple-quoted block.

> **WARNING for plan 31-04:** do **NOT** generalize this correction to market-data. Each market-data driver site must be re-checked **individually**. The plan explicitly notes that market-data's `len(created)` site genuinely **DOES** need the `to_dict()` escape hatch. "higyrus needed none" is evidence about higyrus's capture path only, not a rule.

## 3. The two-row diff of the regenerated surface golden

Produced by `uv run python verification/regen_snapshots.py` and committed in `3aa2257`, the same commit as no source change — the source landed in `cf4be6e` immediately prior, and the golden's own guard test (`test_snapshot_regen_is_idempotent`) confirms the pair is now consistent. The file was **never hand-edited**.

```diff
+Health : class : (status: 'str') -> None
```
```diff
-get_health : function : () -> 'dict[str, Any]'
+get_health : function : () -> 'Health'
```

Exactly two changed regions, exactly as the plan predicted. `git diff --stat verification/snapshots/` showed **only** `higyrus-client-surface.txt` changed (`2 insertions, 1 deletion`) — the regen script rewrote all four goldens and the other three were byte-identical, confirming no unintended surface drift elsewhere.

Both local-only gates pass (CI never executes `verification/`):
- `uv run pytest verification/test_public_surface.py -q` → 4 passed
- `uv run pytest verification/test_phase06_nyquist_gaps.py::test_snapshot_regen_is_idempotent -q` → passed

**Note on the idempotency guard:** it failed while the regenerated golden was still uncommitted (it asserts `git diff --exit-code verification/snapshots/`), then passed immediately after `3aa2257`. That is the T-31-14 / Pitfall-1 guard doing precisely its job — proving a stale-or-uncommitted golden cannot slip through a local run.

## 4. Confirmation that the parser guard and its pinning tests are byte-unchanged

Verified **programmatically** against `c9b606f` (the phase-start commit), not by eye:

| Artifact | Result |
|---|---|
| `parse_get_health_response`'s `isinstance(raw, dict)` guard + `HigyrusAPIError(status_code=0, ...)` construction + both `title`/`detail` strings | **byte-unchanged** — the only line that moved inside the function body is the 204 branch's `return {}` → `return Health.from_api(None)`, which D-04 requires |
| `test_parse_get_health_response_raises_on_non_dict` (test_core.py) | **byte-unchanged** |
| `test_get_health_raises_on_list_payload` (test_client.py) | **byte-unchanged** |
| `test_async_get_health_raises_on_list_payload` (test_async_client.py) | **byte-unchanged** |

The `detail` string still carries `type(raw).__name__` — the type **NAME** only, never `repr(raw)` and never a wire value (T-31-11 / T-29-36 / ASVS V7). A **new** test, `test_parse_get_health_response_non_dict_guard_strings_are_exact`, now pins `status_code == 0` and `errors == [{"title": "shape mismatch", "detail": "expected dict, got list"}]` exactly, so any future attempt to loosen the guard fails loudly rather than silently retiring a class of divergence detection (T-31-13).

**The guard was never loosened, conditioned, or deleted to make a re-mock pass.** Phase 30-03's ratified precedent was followed throughout: every mismatch was corrected on the TEST side.

---

## Decisions Made

- **`Health.status` declared `str`, not `str | None`** — the live capture shows a populated string, and `walk_field`'s union-with-`None` branch returns `None` **without** emitting a divergence, so an over-declared Optional would silently erase exactly the signal this milestone exists to surface (T-31-12).
- **`Health` does not override `from_api`** — the walker's nested-model branch builds with `hint(**walk_model(...))` and never calls `from_api`, so an override would be silently skipped. Pinned by `test_health_does_not_override_from_api`. Shape carve-outs stay in the parser.
- **`to_dict()` copied, not imported** — verified byte-identical to iol's by extracting both method bodies and comparing. C-2 forbids cross-package imports; `grep -E '^(import|from) '` on higyrus's `models.py` lists only `__future__`, `dataclasses`, `typing`, `higyrus_client`.
- **Deferred the two pre-existing higyrus `test_decode.py` mypy errors** rather than fixing them (see Issues Encountered).

## Deviations from Plan

### 1. [Rule 3 - Sequencing] Test re-mocks folded from Task 3 into Task 2's RED gate

- **Found during:** Task 2 planning of the commit boundary
- **Issue:** The plan assigns the parser/shell retype to Task 2 and the re-mock of all three test files to Task 3. Executed literally, the commit at the end of Task 2 would leave `packages/higyrus-client` red (9 failing tests) at a non-TDD commit boundary — indistinguishable, in `git log`, from a genuine breakage.
- **Fix:** All test re-mocks landed in Task 2's RED commit (`2cfd2c0`), which is a deliberate TDD gate, so Task 2's GREEN commit (`cf4be6e`) restores the suite to fully green. Task 3 then carries only the golden regen and the driver docstring. The plan explicitly sanctions this class of shuffle in Task 1 ("if the executor prefers, land the model behavior tests in Task 3's edit instead ... Either way the six behaviors above must each have an assertion by the end of the plan").
- **Verification:** Every Task-3 acceptance criterion about test content was re-checked at the end of the plan and passes; no assertion was dropped.
- **Committed in:** `2cfd2c0`

### 2. [Rule 2 - Missing Critical] Added an exact-strings pinning test for the shape guard

- **Found during:** Task 2 (RED gate authoring)
- **Issue:** The plan requires the guard's `title`/`detail` strings survive byte-unchanged and names T-31-13 as a mitigated threat, but the existing `test_parse_get_health_response_raises_on_non_dict` only asserts `pytest.raises(HigyrusAPIError)` — it would still pass if the strings were rewritten or the `status_code=0` construction changed. The mitigation had no runtime enforcement.
- **Fix:** Added `test_parse_get_health_response_non_dict_guard_strings_are_exact`, asserting `status_code == 0` and the full `errors` list verbatim. The original test was left byte-unchanged as required.
- **Verification:** Test passes; the original guard test is still byte-identical to `c9b606f`.
- **Committed in:** `2cfd2c0`

### 3. [Rule 2 - Missing Critical] Added a `_pristine_decode_context` fixture to `test_core.py`

- **Found during:** Task 1 (RED gate authoring)
- **Issue:** `test_core.py` had no equivalent of `test_decode.py`'s autouse pristine-context fixture. Because of the Phase 29 D-03 `.set()`-without-reset discipline, once any test in the session drives a real `_request`, a later bare `Model.from_api()` joins that stale scope and has its divergence deduped away — so the new divergence assertions would flip green-to-empty purely on **test order**, producing a silently vacuous test.
- **Fix:** Added a (non-autouse, opt-in via `@pytest.mark.usefixtures`) fixture mirroring `test_decode.py`'s, resetting `STRICT_DECODE` and `DECODE_SCOPE` around each divergence-asserting test. Non-autouse deliberately: it must not perturb the file's existing 30+ tests.
- **Verification:** Full `packages/higyrus-client` suite green both with and without `-p no:randomly`.
- **Committed in:** `5c8e2c7`

---

**Total deviations:** 3 (1 sequencing, 2 missing-critical test coverage)
**Impact on plan:** No scope creep. Deviation 1 improves commit hygiene without changing content; deviations 2 and 3 add runtime enforcement to mitigations the plan named but did not pin. All plan prohibitions were respected.

## Issues Encountered

### Pre-existing mypy failure blocks one acceptance criterion (deferred, not fixed)

`uv run mypy packages/higyrus-client/tests` exits **1** with two errors in `packages/higyrus-client/tests/test_decode.py` (lines 624 and 693) — a file this plan never touched. This is the ONE plan acceptance criterion that does not pass.

**Proven pre-existing** by adding a throwaway `git worktree` at `c9b606f` (phase-start commit), running `uv sync --all-packages --all-extras --dev --frozen` inside it, and reproducing the **identical two errors at the identical line numbers**. The worktree was then removed with `git worktree remove --force`.

They are the same two constructs as deferred-item **D-2** in ambito-financiero (`SILENT_SINK` result used in an `assert ... is None`, and an unneeded `# type: ignore[arg-type]` on a `dataclasses.fields` comprehension). `_decode.py` and its suite are **byte-frozen verbatim copies across all five paquetes**, so the defect almost certainly exists in all five. Fixing it correctly is a five-copy edit, which is exactly the coupling plan 31-02 declined for D-2. Applying that ratified precedent: **deferred**, logged as **deferred-items D-3**.

**What the criterion was actually guarding is green:** `uv run mypy` — the CI `src` gate, and the reason higyrus was chosen as this phase's strict-typechecked tracer — passes on **62 source files**, and `pytest packages/higyrus-client/tests/test_decode.py` passes **57/57**.

### Pre-existing matriz `verification/` failures (already logged as D-1)

The full local suite surfaces 20 failures / 19 errors in `verification/test_main_matriz_login_fail_uniformity.py` and `verification/test_matriz_sweep_snapshot.py` — the stale pre-Phase-15 `probe_login_sync()` signature already logged as deferred-item **D-1** by plan 31-02. Untouched, per the phase's scope boundary.

## Verification Results

| Gate | Result |
|---|---|
| `uv run pytest packages/higyrus-client -q` | **236 passed** (was 224 before the plan — 12 net new tests, none removed) |
| `uv run pytest packages/higyrus-client/tests/test_decode.py -q` | **57 passed** — confirms G-8's prediction that the new decoration perturbs no existing scope test |
| `uv run pytest verification/test_public_surface.py -q` | **4 passed** (local-only; CI never runs `verification/`) |
| `uv run pytest verification/test_phase06_nyquist_gaps.py -q` | **passed**, including `test_snapshot_regen_is_idempotent` |
| `uv run pytest -q` (full local suite, excluding only the D-1 matriz files) | **1955 passed, 0 failed** |
| `uv run mypy` (CI `src` gate) | **Success: no issues found in 62 source files** |
| `uv run mypy packages/higyrus-client/src` | **Success: no issues found in 13 source files** |
| `uv run mypy packages/higyrus-client/tests` | **FAILS — 2 pre-existing errors, see Issues Encountered / deferred-items D-3** |
| `uv run ruff check .` | **All checks passed** |
| `uv run ruff format --check .` | **231 files already formatted** |
| `uv run python -c "import higyrus_client; assert 'Health' in higyrus_client.__all__"` | **exit 0** |
| `python -c "... Health.from_api({'status':'ok'}) ..."` | prints `ok {'status': 'ok'}` |

## Threat Flags

None. This plan introduced no new network endpoint, auth path, file-access pattern, or schema change at a trust boundary. The one error-message surface it touched (`HigyrusAPIError`'s `detail`) is byte-unchanged and still emits a type name only.

## Known Stubs

None. Every declared field is wired to the live-capture wire key, and no placeholder, mock, or hardcoded empty value was introduced.

## User Setup Required

None — no external service configuration required. No package was installed; `uv.lock` is unchanged (T-31-SC).

## Next Phase Readiness

**The tracer recipe is validated end to end and ready to scale.** All seven mechanics plans 31-04 and 31-05 will repeat were exercised here at the smallest possible blast radius, and **all seven behaved as predicted** — no mechanic was found broken:

1. `SafeModel.to_dict()` copied verbatim per package ✅
2. A parser gaining `@_decode._response_parser` while keeping its guard ✅
3. Four signature sites moved (sync method / sync shim / async method / async shim) ✅
4. A re-export into `__all__` at the correct ASCII sort position ✅
5. A golden regen committed alongside the source change ✅
6. Re-mock discipline that fixes the TEST rather than the guard ✅
7. `mypy --strict` clean under CI's `src` gate ✅

**Carry into 31-04 / 31-05:**

- **Re-check every driver site individually.** Section 2 above is a correction to CONTEXT D-03, not a general rule. market-data's `len(created)` site genuinely needs the escape hatch.
- **market-data is NOT mypy-enrolled** (D-13), so unlike higyrus its models get no CI strict-typecheck. Local `mypy` runs are the only gate there.
- **market-data's public surface is not covered by `verification/snapshots/`**, so plans 31-04/31-05 have no golden-regen step for it — but they must still confirm no *other* package's golden drifts.
- **Every non-collection endpoint whose parser has a 204 / empty-body carve-out inherits the strict-mode raise measured in Section 1.** Measure and pin it per endpoint; do not assume.

**Blockers/concerns for the phase verifier:**

- `uv run mypy packages/higyrus-client/tests` is red on **pre-existing** grounds (deferred-items D-3). Because the `typecheck` CI job iterates `higyrus-client` **first** under `set -e`, this masks D-2 and is a live red step on `milestone/v1.5-mutations` today, independent of Phase 31. It needs its own five-copy repair plan before v1.6 ships.
- The TYP-02 concurrency probe row remains **open**, exactly as the plan flagged. The higyrus decode-scope tests (`test_decode.py` lines 866-960) are still green and pin fresh-scope-per-response, but that is coverage, not resolution. Not dismissed.

---
*Phase: 31-endpoints-de-ops-estructura-uniforme*
*Completed: 2026-08-24*

## Self-Check: PASSED

All claimed files exist on disk and all five task commits are present in git history.
