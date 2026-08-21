---
phase: 30-iol-client-tipado
plan: 07
subsystem: testing
tags: [verification-harness, drift-probes, iol-client, pytest, gap-closure]

# Dependency graph
requires:
  - phase: 30-iol-client-tipado
    provides: "30-04's raw-wire capture (`_capture_raw_wire`) and the two drift probes it feeds; 30-06's nine-case regression lock on `verification/test_main_iol_raw_wire_drift.py`"
  - phase: 29-decoder-observable
    provides: "the per-field walker whose model projection made the raw-wire probes necessary in the first place"
provides:
  - "`probe_field_type_map` and `probe_schema_snapshot` gated on dict membership against `raw_wire` instead of on value identity against the null sentinel"
  - "a captured JSON `null` body now reaches the existing top-level-shape checks and produces SHAPE findings (3 from probe 12, 4 from probe 13) instead of two false PASSes"
  - "`probe_field_type_map`'s PASS detail is truthful by construction: the gating predicate and the reporting predicate are now the same expression"
  - "eight new regression cases pinning the null-body input class in both directions (null → finding, absent → skip)"
affects: [33-live-typ, phase-33-strict-driver-run, verification-harness-maintenance]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Membership-gated probe inputs: a drift probe asks the capture dict whether it holds the key, never whether the value equals the failure sentinel"
    - "The predicate that gates a check and the predicate that builds the PASS detail must be the same expression, so the attestation cannot outrun the inspection"
    - "Test fixtures that seed every committed baseline, so a comparison helper can never silently take its write-new-baseline branch under test"

key-files:
  created: []
  modified:
    - "main_iol.py"
    - "verification/test_main_iol_raw_wire_drift.py"

key-decisions:
  - "AD-30-07-01: the absent-vs-null distinction is made explicit at the three consumers (membership tests), not at the producer via a dedicated sentinel object — Python dicts already distinguish absent from present-with-None and membership is the language's own answer, needing no new vocabulary"
  - "probe_field_type_map emits 3 SHAPE findings on an all-null raw_wire, not the 4 the gap brief predicted: it field-maps exactly three endpoints and contains no reference to get_instruments, whose drift coverage comes from probe 13's baseline comparison instead"
  - "The null-body case is written as its own explicit tests rather than as a fourth `_DRIFT_LABELS` entry — a null body is the replacement of the body, not a mutation of a dict, and folding it into `_mutated()` would drag it into the section-7 projection canary whose subject is the three projection-blind mutations"

patterns-established:
  - "Region gate by introspection: `inspect.getsource` over the two probe bodies, regex-counting the removed predicate class, so a future reintroduction is mechanically detectable"
  - "Both-directions regression cases: every discrimination fix ships the negative case (absence must still route to skip) alongside the positive one, so the fix cannot be satisfied by converting every skip into a finding"

requirements-completed: [TYP-01]

# Metrics
duration: 21min
completed: 2026-08-21
status: complete
---

# Phase 30 Plan 07: Null-body drift-probe discrimination Summary

**Both iol drift probes now gate on `raw_wire` key membership instead of on the null sentinel, so a 200-OK JSON `null` body produces 7 SHAPE findings (3 + 4) where it previously produced two false PASSes and zero findings.**

## Performance

- **Duration:** 21 min
- **Started:** 2026-08-21T14:14:55Z
- **Completed:** 2026-08-21T14:36:11Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments

- Closed the post-closure half of CR-01 / 30-VERIFICATION.md truth 6: a captured `null` body is now treated as a payload that arrived, not as a capture that failed.
- Four predicate changes in two probe functions; every finding title, body, `expected`/`actual`/`diff` string and control-flow branch left byte-identical. The change alters *which inputs reach* the existing checks, never what those checks do or report.
- `probe_field_type_map`'s PASS detail became truthful by construction — the gate and the `checked` list comprehension are now the same `in raw_wire` predicate, where previously the comprehension already used membership while the gates used identity.
- Eight new regression cases (one fixture + five test functions, one of them parametrized ×4) pin the input class that defeated 30-06's nine-case lock, in both directions.
- The `_write_or_check_schema` write branch (T-30-07-03) was contained rather than fixed, exactly as the plan's threat register specified.

## Task Commits

1. **Task 1: RED — null-body regression cases for both drift probes** — `2e10561` (test)
2. **Task 2: GREEN — gate both probes on dict membership instead of the null sentinel** — `b12c4d4` (fix)
3. **Task 3: Regression sweep and scope containment** — no commit; a verification-only task that changed no file. Its evidence is recorded below.

## Files Created/Modified

- `main_iol.py` — four predicates in `probe_field_type_map` and `probe_schema_snapshot` changed from null-sentinel identity to `raw_wire` key membership, plus two explanatory comments restated around the distinction now enforced. 21 insertions / 9 deletions, all inside the two probe bodies.
- `verification/test_main_iol_raw_wire_drift.py` — 337 → 549 lines. New section 8 with the `tmp_schema_all` fixture, the `_null_wire()` helper, `_SCHEMA_BASELINE_NAMES` / `_FIELD_MAPPED_ENDPOINTS` constants, and five test functions. Module docstring extended with a conceptual paragraph naming what section 8 pins.

## Verbatim Evidence

### Pre-fix RED output (proof the reproduction reproduced)

`uv run pytest verification/test_main_iol_raw_wire_drift.py -v` against the unmodified driver: **3 failed, 14 passed** (17 collected). The three failures are exactly the null-body cases; the nine pre-existing cases and the two new invariant cases pass.

```
verification/test_main_iol_raw_wire_drift.py::test_probe_field_type_map_treats_captured_null_body_as_shape_defect FAILED [ 25%]
verification/test_main_iol_raw_wire_drift.py::test_probe_schema_snapshot_treats_captured_null_body_as_shape_defect FAILED [ 50%]
verification/test_main_iol_raw_wire_drift.py::test_a_single_null_bodied_endpoint_is_enough_for_both_probes FAILED [ 75%]
verification/test_main_iol_raw_wire_drift.py::test_absent_capture_is_still_distinguishable_from_a_null_body PASSED [100%]
```

```
>       assert result.status == "FINDING", repr(result)
E       AssertionError: ProbeResult(name='field_type_map', status='PASS', detail='3 endpoints checked (get_quote, get_historical_quotes, get_instruments_by_type), no drift')
E       assert 'PASS' == 'FINDING'

>       assert result.status == "FINDING", repr(result)
E       AssertionError: ProbeResult(name='schema_snapshot', status='PASS', detail="written=[] matched=[] skipped=['get_quote', 'get_historical_quotes', 'get_instruments', 'get_instruments_by_type']")
E       assert 'PASS' == 'FINDING'

>       assert field_map.status == "FINDING", repr(field_map)
E       AssertionError: ProbeResult(name='field_type_map', status='PASS', detail='1 endpoints checked (get_quote), no drift')
E       assert 'PASS' == 'FINDING'
```

This matches the planner's `verification_evidence.before` exactly, including the false PASS detail naming three endpoints none of which were inspected.

### Post-fix reproduction transcript

Run against the patched driver with `append_finding` spied and `_SCHEMA_DIR`/`_SCHEMA_FILES` pointed at a temp copy of the four committed baselines:

```
=== input: raw_wire con los 4 endpoints capturados con cuerpo JSON null ===
    {'get_quote': None, 'get_historical_quotes': None, 'get_instruments': None, 'get_instruments_by_type': None}

probe 12 (field_type_map)  -> status=FINDING  detail='F-01, F-02, F-03 (OPEN)'
    SHAPE findings: 3
      - get_instruments_by_type devolvió tipo top-level no-dict  | actual=type=NoneType
      - get_quote devolvió tipo top-level no-dict  | actual=type=NoneType
      - get_historical_quotes devolvió tipo top-level no-list  | actual=type=NoneType

probe 13 (schema_snapshot) -> status=FINDING  detail='F-04/get-quote.json, F-05/get-historical-quotes.json, F-06/get-instruments.json, F-07/get-instruments-by-type.json (OPEN) — NO sobreescribe'
    SHAPE findings: 4
      - Schema drift en get_quote
      - Schema drift en get_historical_quotes
      - Schema drift en get_instruments
      - Schema drift en get_instruments_by_type
```

3 + 4 = 7 findings, matching `verification_evidence.after` and the `count_correction` block.

### Both-directions result for the empty `raw_wire`

```
=== ambas direcciones: raw_wire vacío (captura genuinamente ausente) ===
probe 12 -> status=PASS  detail='0 endpoints checked (ninguno), no drift'
probe 13 -> status=PASS  detail="written=[] matched=[] skipped=['get_quote', 'get_historical_quotes', 'get_instruments', 'get_instruments_by_type']"
findings emitidos: 0
```

Absence did not become a finding. The fix discriminates in both directions.

### Region and membership gates

```
$ uv run python -c "import inspect, re, main_iol; s = inspect.getsource(main_iol.probe_field_type_map) + inspect.getsource(main_iol.probe_schema_snapshot); ..."
null_sentinel_comparisons: 0
membership_gates: 5
```

Zero null-sentinel comparisons remain inside either probe body (comments included); membership gates ≥ 4 as required (5, counting the `checked` comprehension that already used membership).

**Factual clarification on the file-wide count** — not a scope change. The plan states "file-wide there are 7 such comparisons … the 3 elsewhere are legitimate". Measured: the pre-fix file has **7 matching lines / 8 regex occurrences**, and the post-fix file has **3 matching lines / 4 occurrences**. The discrepancy is that `main_iol.py:1099` carries two comparisons on one line (`if sync_data is None or async_data is None:`). Both readings agree on the substance: exactly the 4 in-probe comparisons were removed, and exactly the 3 legitimate lines elsewhere (1099, 1526, 1584 — parity probe and refresh-token probe) remain untouched.

### D-25 and the no-values-in-findings invariant (T-30-07-02)

```
=== D-25: baselines copiados byte-idénticos ===
    get_quote: unchanged=True
    get_historical_quotes: unchanged=True
    get_instruments: unchanged=True
    get_instruments_by_type: unchanged=True

=== campos de cada finding emitido (T-30-07-02: nunca un valor crudo) ===
    expected="dict con clave 'titulos'" actual='type=NoneType'
    expected='dict con los campos de la cotización' actual='type=NoneType'
    expected='list de rows de cotización' actual='type=NoneType'
    expected='{"apertura": "float", "cantidadOperaciones": "int", ...' actual='"NoneType"'
    expected='[{"apertura": "float", "cantidadOperaciones": "int", ...' actual='"NoneType"'
    expected='[{"instrumento": "str", "pais": "str"}]' actual='"NoneType"'
    expected='{"titulos": [{"apertura": "float", ...' actual='"NoneType"'
```

Every emitted field carries a **type name**, never a raw body value. T-30-07-02 holds by construction for the new input class, verified rather than assumed.

### Task 3 regression sweep

| Gate | Result |
|------|--------|
| `uv run pytest verification/test_main_iol_raw_wire_drift.py -v` | `17 passed` — zero failures |
| `uv run pytest packages/iol-client -q` | `242 passed` — unchanged from the 30-05 baseline |
| `uv run mypy packages/iol-client/src packages/iol-client/tests` | `Success: no issues found in 25 source files` |
| `uv run ruff check packages/iol-client main_iol.py verification` | `All checks passed!` |
| `uv run ruff format --check packages/iol-client main_iol.py verification` | `72 files already formatted` |
| `uv run pytest verification -q` | `19 failed, 288 passed, 19 errors in 828.54s` — all 19+19 pre-existing and matriz-only (see below) |
| `git diff --exit-code packages/ .planning/verification/schemas/` | exits 0 |
| `git diff --stat <base>..HEAD` | exactly 2 files: `main_iol.py`, `verification/test_main_iol_raw_wire_drift.py` |
| iol harness files (`test_iol_disk_persistence` + `test_main_iol_uses_single_client_instance` + drift lock) | `29 passed` |

**Pre-existing failures in the full harness suite, proven to predate this diff.** The 19 failures + 19 errors are confined to `verification/test_matriz_sweep_snapshot.py` (17F/17E) and `verification/test_main_matriz_login_fail_uniformity.py` (2F/2E) — matriz-only files that this diff does not touch. Evidence of predating obtained **without `git stash`** (prohibited in a worktree — the stash stack is shared across the main checkout and every linked worktree): the base commit tree was exported read-only with `git archive f33582a | tar -x` into a scratch directory and both files were run there against the same interpreter, reproducing `17 failed, 3 passed, 17 errors` and `2 failed, 2 errors` respectively — identical to the post-diff counts. These are the phase-07-era failures already recorded in PROJECT.md as reproduced at the pre-phase baseline. Not fixed: this plan's scope is two files.

## Prohibitions Status (`must_haves.prohibitions`)

| # | Prohibition | Status | Evidence |
|---|-------------|--------|----------|
| 1 | Ningún probe reporta PASS precisamente cuando está roto — un body capturado como null debe producir FINDING, no un skip silencioso | **HELD** | Post-fix transcript: 3 + 4 SHAPE findings on the all-null wire; both probes return FINDING. Pinned permanently by tests 1-3. |
| 2 | Ningún detalle de PASS nombra un endpoint que no está en `raw_wire`: el predicado del detalle y el que gatea los chequeos son el mismo | **HELD** | The gates are now `"get_quote" in raw_wire` / `"get_historical_quotes" in raw_wire` / `"get_instruments_by_type" in raw_wire`, identical to the `checked` comprehension's `if name in raw_wire`. Pinned by `test_probe_field_type_map_pass_detail_never_names_an_uncaptured_endpoint` (×4 shapes, including a capture of the non-field-mapped `get_instruments`). |
| 3 | Ninguna corrida sobreescribe un baseline committeado (D-25) | **HELD** | `git diff --exit-code .planning/verification/schemas/` exits 0. Both null-body snapshot tests assert byte-identity of the tmp copies before/after. The reproduction script confirms `unchanged=True` for all four. |
| 4 | Ningún archivo fuera de `main_iol.py` y `verification/test_main_iol_raw_wire_drift.py` se modifica | **HELD** | `git diff --stat <base>..HEAD` lists exactly those two paths; `git status --porcelain` is empty. `packages/`, `.planning/verification/schemas/`, `models.py`, `client.py`, `aio.py` and the README are all byte-unchanged. |
| 5 | `_write_or_check_schema` y `_capture_raw_wire` no se modifican | **HELD** | Neither function appears in `git diff main_iol.py`. The full diff is confined to lines inside `probe_field_type_map` and `probe_schema_snapshot`. |

## Decisions Made

- **AD-30-07-01 executed as planned** — membership tests at the consumers, not a producer-side sentinel object. The producer was already correct; the defect was three consumers discarding a distinction Python dicts already make.
- **The count correction was confirmed by measurement, not accepted on faith.** `probe_field_type_map` emits 3 SHAPE findings on an all-null wire, not 4. `get_instruments` appears nowhere in probe 12 because it has no `_ASSUMED_*` field map; its drift coverage is probe 13's baseline comparison. The gap's intent — no PASS on a null-bodied capture, and one finding per endpoint each probe actually examines — is fully met at 3 + 4 = 7.
- **Test 2 asserts finding titles by set equality, never by substring containment.** `"Schema drift en get_instruments"` is a prefix of `"Schema drift en get_instruments_by_type"`, so a membership-style check would report green with only three findings — the same class of self-defeating assertion this phase has already been bitten by.
- **The three value bindings (`quote_raw`, `historical_raw`, `envelope`) were left in place** rather than rebound inside each branch, keeping the diff to four predicates plus comments as the plan's minimality instruction required.

## Deviations from Plan

None — plan executed exactly as written. No deviation rule was invoked; no auto-fix was applied; no file outside the two authorized paths was touched.

Two items are worth recording as *observations*, neither of which changed scope:

1. The plan's file-wide null-comparison count of 7 (and "3 elsewhere") is a **line** count, while the acceptance-criterion one-liner counts **regex occurrences** (8 → 4). Line 1099 carries two comparisons. Reconciled above; the in-probe removal is exactly the 4 the plan specified.
2. The plan's Task 1 acceptance criterion expected "at least 14 test cases". The file collects **17** (9 pre-existing + 8 new, since test 5 is parametrized over four shapes). Above the floor, as intended.

## Issues Encountered

- The worktree had no `.venv` and `uv run` created an empty one, so `import iol_client` failed on the first run. Resolved with `uv sync --all-packages --all-extras --dev --frozen` — environment setup, not a code issue, and `.venv/` is gitignored so it left no trace in the diff.
- `uv run pytest verification -q` takes ~14 minutes and exceeded the foreground timeout; it was moved to the background and its result read on completion. Not a defect — the matriz sweep tests dominate the runtime.

## Carry-forwards

### T-30-07-03 left unfixed **by design** — carry to Phase 33

`_write_or_check_schema` (`main_iol.py:1392`) writes the observed schema as a **new baseline** whenever the baseline file does not exist, and returns PASS. Combined with this fix, a null body on an endpoint whose baseline is missing would commit `"schema": "NoneType"` as permanent ground truth, blinding every future comparison for that endpoint.

Left unfixed because repairing it means editing `_write_or_check_schema`, which this gap's `<scope_boundary>` explicitly forbids. It is **unreachable today**: all four baselines are committed and `git diff --exit-code .planning/verification/schemas/iol-client/` exits 0. Contained in two ways, both verified: the `tmp_schema_all` fixture seeds all four baselines so no test can exercise the write branch, and Task 3 asserts no committed baseline moved.

**Recommendation for Phase 33**, which runs the harness live and where a first-capture-of-a-new-endpoint genuinely hits this branch: gate the write branch on the payload being a well-formed body, or require an explicit opt-in flag before a new baseline is minted.

### Warnings that remain OPEN and out of scope

Confirmed still open, deliberately untouched, none of them this plan's target:

- **WR-01** — `probe_schema_snapshot` never receives `capture_fids`.
- **WR-02** — `actual=repr(exc)` in `_capture_raw_wire` embeds an upstream error body.
- **WR-04** — `verification/` is not collected by CI (the `test` job passes an explicit per-package path that overrides `testpaths`).
- **WR-05** — `_capture_raw_wire` has no direct unit test.
- **WR-09** — README version mismatch.
- **WR-10** — stale source reference at `main_iol.py:1187`.

CR-02 / truth 7 remains fully closed by 30-05; `parse_get_instruments_by_type_response` was not re-touched.

## User Setup Required

None — no external service configuration required. Every test in this plan is offline: no network, no credentials, no `httpx_mock`.

## Next Phase Readiness

- The drift lock now covers the null-body input class permanently, in both directions. A PASS from either iol drift probe once again means a comparison was actually performed.
- Phase 33's strict live driver run inherits probes that cannot report PASS on an input they did not inspect — which matters directly for the sizing-floor contrast ratified in 29-10, since a false-clean is exactly what that census must not produce.
- One carry-forward with a named destination: T-30-07-03 → Phase 33.
- No blockers introduced. `packages/` and `.planning/verification/schemas/` are byte-unchanged; the iol package suite (242) and mypy (25 source files) are exactly at their pre-plan baselines.

---
*Phase: 30-iol-client-tipado*
*Completed: 2026-08-21*
