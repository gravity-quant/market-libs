---
phase: 31-endpoints-de-ops-estructura-uniforme
plan: 05
subsystem: api
tags: [market-data-client, typing, dataclasses, safemodel, mutation, asvs-v4, asvs-v13, byte-identical-request, tolerance, drift-detection]

# Dependency graph
requires:
  - plan: 31-01
    provides: "the non-vacuous mutating-gate AST guard, the direct `idempotent is True` builder assertions, and the raw-bytes v0.4.0 request pin — all three re-run after EVERY task here and all three passed with an EMPTY `git diff`"
  - plan: 31-04
    provides: "`SafeModel.to_dict()` on market-data's base (the escape hatch the driver's `len()` and snapshot sites use), the health-parser split precedent, and the `# Phase 31 — ops endpoints (TYP-02)` roster block"
  - phase: 27-calendario-mutaciones
    provides: "the four committed live captures (`add-holidays-{sync,async}-response.json`, `delete-holiday-{sync,async}-response.json`) and the D-20 row-count measurement that corrected both holiday builders to `idempotent=True`"
provides:
  - "`market_data_client.AddHolidaysResult` — `days: list[CalendarDay]` (the SHIPPED model, reused), `note: str`, `saved: int`"
  - "`market_data_client.DeleteHolidayResult` — `day: str`, `deleted: bool` (boolean, per the capture; the contradicted integer mock corrected on the TEST side)"
  - "`_core.parse_add_holidays_response` + `_core.parse_delete_holiday_response` — the shared calendar-write parser SPLIT in two, both `@_decode._response_parser` decorated, both preserving the T-26-13 tolerance as `Model.from_api(None)` on all four branches"
  - "8 retyped signature sites (2 methods x 2 shells + 4 module shims) with the gate call, builder call and `_request` line byte-unchanged"
  - "G-6 discharged: the stale `idempotent=False` claim removed from the `add_holidays` docstring on BOTH shells (and from a third instance found in `test_calendar_write.py`)"
  - "An explicit FA-09-style drift-blindness carry-forward at both `delete_holiday` probes routing Phase 33 to the divergence census"
  - "CRITERION 1 CLOSED: all 5 ops endpoints x 2 surfaces x (method, shim) = 20 sites name a model class"
affects: [32-enrollment, 33-drivers-strict-mode, 34-release]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Response-only change on a PUBLISHED mutation, proven mechanically rather than asserted: the request pin and the AST guard are re-run after every task AND their own `git diff` is required to be empty"
    - "Walker behaviour MEASURED before declaring, not reasoned about — the int-for-bool branch was executed and its outcome pinned with a comment recording the measurement"
    - "Tolerance disposition decided by ENDPOINT CLASS, not by package uniformity: reads gained a non-dict raise (31-04), published mutations keep the tolerance (this plan)"
    - "`typing.Any` disappearing from a shell's import line is itself evidence that no untyped-mapping return remains in it"

key-files:
  created: []
  modified:
    - packages/market-data-client/src/market_data_client/models.py
    - packages/market-data-client/src/market_data_client/_core.py
    - packages/market-data-client/src/market_data_client/client.py
    - packages/market-data-client/src/market_data_client/aio.py
    - packages/market-data-client/src/market_data_client/__init__.py
    - packages/market-data-client/tests/test_core.py
    - packages/market-data-client/tests/test_calendar_write.py
    - packages/market-data-client/tests/test_calendar_write_async.py
    - packages/market-data-client/tests/test_public_surface_market_data.py
    - main_market_data.py

key-decisions:
  - "G-4 RESOLVED TOWARD TOLERANCE: both new parsers keep the T-26-13 tolerance as `Model.from_api(None)` on all four branches (absent / null / list / scalar). A raise would be a behaviour change on a mutation published in v0.4.0, which criterion 2's response-only framing does not authorize. 31-04's health parsers took the opposite disposition on the non-dict branch — deliberately, because those serve READS."
  - "MEASURED: an `int` arriving for the `bool`-declared `deleted` is NOT widened. `walk_field`'s `hint is bool` branch fails `isinstance(value, bool)`, emits a `type` divergence (`declared=bool` / `observed=int`), and substitutes `False` because market-data's `POLICY.scalar_passthrough is False`. Contrast Phase 29's matriz finding where an `int` for a `float`-declared field DOES widen."
  - "The driver's `_emit_holiday_idempotency_verdict` prose (which still names `idempotent=False`) is deliberately SCOPED OUT: it is the RECORD of the Phase-27 measurement that produced the correction, not a claim about the current client contract, and editing it would change the driver's emitted finding strings."
  - "Both `delete_holiday` probes ACCEPT snapshot drift-blindness (T-31-29) with a mandatory carry-forward note; a raw re-fire is impossible because a second DELETE is legitimately a 404 AND is the D-19 measurement."
  - "`AddHolidaysResult.days` REUSES the shipped `CalendarDay`; no parallel element model exists, pinned by a hint-equality test."

patterns-established:
  - "Before typing a published mutation, prove the request side did not move — and prove the proof was not adjusted, by requiring the pin's own diff to be empty"
  - "When a committed mock and a live capture disagree, the capture wins and the mock is corrected; the declaration is never widened to accommodate a wrong mock"
  - "A stale docstring that contradicts a shipped flag is treated as an active trap and is corrected wherever it appears, including in test-file section comments"

requirements-completed: [TYP-02]

# Metrics
duration: 27min
completed: 2026-08-25
status: complete
---

# Phase 31 Plan 05: market-data calendar-write mutations (`AddHolidaysResult` + `DeleteHolidayResult`) Summary

**The last two endpoints of the phase — the two already published as mutations in v0.4.0 — are typed
without a single request byte moving and without the mutating gate being perturbed, and both of those
claims are mechanical rather than asserted.**

## Performance

- **Duration:** 27 min
- **Started:** 2026-08-25T10:46:42Z
- **Completed:** 2026-08-25T11:14Z
- **Tasks:** 3 (all TDD, 5 commits)
- **Files modified:** 10

## Task Commits

| Task | Gate | Commit |
|---|---|---|
| 1 — the two models | RED | `e44d762` |
| 1 — the two models | GREEN | `79fd762` |
| 2 — parser split, 8 sites, G-6, exports | RED | `80212bb` |
| 2 — parser split, 8 sites, G-6, exports | GREEN | `7a9af04` |
| 3 — driver result reads + carry-forward | fix | `70ecb3e` |

No REFACTOR commit was needed: both GREEN implementations landed at production shape.

---

## 1. CRITERION 2 AND CRITERION 3 — the evidence, stated first

**Plan 31-01's request pin and AST guard passed after every task in this plan, and their own
`git diff` against the plan-start commit (`69e6145`) is EMPTY.** A green gate that had been adjusted
would prove nothing; this one was not touched.

```
$ uv run pytest packages/market-data-client/tests/test_v040_request_pin.py \
                packages/market-data-client/tests/test_mutation_gate_ast.py -q
9 passed

$ git diff 69e6145 -- packages/market-data-client/tests/test_v040_request_pin.py \
                      packages/market-data-client/tests/test_mutation_gate_ast.py
(empty)
```

Run after Task 1's GREEN, after Task 2's GREEN, and again at the end of Task 3. Green every time,
diff empty every time.

**Second, independent proof that the gate and the builders were untouched** — no CHANGED line in
either shell's diff names them:

```
$ git diff .../client.py .../aio.py | grep '^[+-]' \
    | grep -E '_ensure_mutation_allowed|build_add_holidays_request|build_delete_holiday_request'
(empty)
```

Only two things changed per method: the return annotation and the parser name on the final line.
`self._ensure_mutation_allowed()`, the builder call and `self._request(spec)` are byte-unchanged in
all four methods. Neither builder was edited, so both keep `idempotent=True` (D-20).

**A third, incidental proof that no untyped mapping return survives in either shell:**
`from typing import Any, Self` became `from typing import Self` in BOTH `client.py` and `aio.py`.
The holiday pair held the last `dict[str, Any]` annotations in each file; once they were retyped,
`Any` had no remaining use and ruff's F401 said so.

---

## 2. THE MEASURED INT-FOR-BOOL OUTCOME

The plan required this to be run, observed and pinned rather than reasoned about. It was.

**Observation (2026-08-25, market-data `POLICY`):**

```
$ uv run python -c "... CalendarDay.from_api({'closed': 1, ...}) ..."
closed = False
CalendarDay .closed type bool int
```

**Verdict: an `int` arriving for a `bool`-declared field is NOT widened.** `_decode.walk_field`'s
`hint is bool` branch takes an `isinstance(value, bool)` check, which an `int` fails; it emits a
`type` divergence with `declared="bool"` / `observed="int"` and substitutes `policy.missing_bool`
(`False`), because market-data's `POLICY.scalar_passthrough` is `False`.

So `{"deleted": 1}` — the shape the pre-Phase-31 mock asserted — yields `deleted is False` plus
exactly one `(".deleted", "type")` record. The integer is neither silently absorbed nor
truthy-coerced: it is **recorded and zeroed**.

This mattered to measure. Phase 29 found the *opposite* behaviour one branch away — an `int`
arriving for a `float`-declared matriz field DOES widen. The two branches differ, so the outcome
here could not be inferred from that precedent.

Pinned by `test_delete_holiday_result_integer_deleted_is_not_widened_and_is_reported`, whose
docstring carries the measurement verbatim.

---

## 3. G-4 RESOLVED — and the deliberate divergence from 31-04

### The decision

**Both new parsers PRESERVE the T-26-13 tolerance.** An absent body, a `null`, a JSON list and a
JSON scalar all collapse to `Model.from_api(None)` — the zero-valued instance — and **none of them
raises**. What used to be `{}` is now a typed zero-valued model; the contract is otherwise identical.

### Why, and why it differs from the health parsers

31-04 gave the two health parsers a non-dict **raise**. This plan deliberately did not follow that
on the non-dict branch. The distinguishing fact is endpoint class, not package uniformity:

- The health parsers serve **reads**. A non-mapping body there is a genuine contract violation with
  no released consumer depending on the tolerance.
- These two serve **mutations already published in v0.4.0**. The replaced function's own docstring
  argued at length that its tolerance was deliberate (T-26-13) and was the reason it existed as a
  separate function rather than a reuse of the health parser. Converting a tolerance branch into a
  raise is a **behaviour change**, and criterion 2's response-only framing does not authorize one.

`parse_calendar_config_response`, one function above in the same file, is the direct in-package
precedent for the empty-body → `from_api(None)` shape.

The reasoning is recorded in both new parsers' docstrings and in a section comment above the tests,
so a future reader meeting the two dispositions side by side sees why they differ.

Covered by `test_calendar_write_parsers_preserve_the_t2613_tolerance` — 8 parametrized cases
(2 parsers x 4 branches), each asserting the zero-valued model and none expecting a raise.

### The out-of-scope decision, recorded rather than left silent

`main_market_data.py`'s `_emit_holiday_idempotency_verdict` (line ~2294) still names
`idempotent=False` throughout its finding strings — the title, the `expected` field and both `diff`
branches. **This is deliberately scoped OUT of Phase 31.**

That prose is the **RECORD of the Phase-27 live measurement that produced the correction**, not a
claim about the current client contract. Its `expected` field literally reads *"medición en vivo del
flag idempotent=False"* — describing what was being measured at the time. Editing it would change
the driver's emitted findings and rewrite the audit trail of a completed measurement.

It is also the one place in the repo where the old flag name legitimately survives, and it is
recorded here so it does not read as an oversight — and so it cannot seed a builder edit.

---

## 4. THE DELETE-PROBE DRIFT-BLINDNESS CARRY-FORWARD (for Phase 33)

> **The schema snapshot of `DELETE /calendar/holidays/{day}` is BLIND TO DRIFT. A clean snapshot
> diff for this endpoint is NOT evidence that the wire did not change.**

`probe_delete_holiday_sync` / `_async` feed `_write_schema_snapshot` with the **public result**, and
since this plan that result is a `DeleteHolidayResult`. The walker has already coerced every
non-optional field to its declared type and dropped every undeclared key, so `schema_of` over that
projection is a function of the **declaration**, not the wire: a type change, an added key and a
removed key are all three invisible.

**Why it cannot be fixed with a raw re-fire** (unlike the add probes, which already refire and are
unaffected): a second `DELETE` is legitimately a `404` and would capture an error body as the
baseline — and that second DELETE **is** the D-19 idempotency measurement the probe exists to make.
The two purposes are in direct conflict.

**Resolution — Phase 30's ratified option, applied here (T-31-29, `accept`):** keep the projection
(fed through `to_dict()` so the snapshot at least remains a mapping of the declared shape), and add
an unmissable `.. warning::` carry-forward to BOTH probe docstrings naming `main_iol.py`'s
`_capture_raw_wire` rationale as the precedent.

**The operative consequence, phrased for Phase 33 to pick up:** for this endpoint the
**authoritative drift signal is the DIVERGENCE CENSUS**, not the schema-snapshot diff. The two
stopped being independent signals here — the snapshot became an echo of the declaration.

`schema_of` remains value-blind either way, so no data-protection property is lost.

**The add probes are unaffected and were not changed on this axis:** `probe_add_holidays_{sync,async}`
already refire the raw wire (`_mutate_raw_sync(...).json()`) for their snapshot, so those two
snapshots remain genuine wire evidence. Only their PASS-detail key count moved to `to_dict()` — the
`len(created)` question 31-04 carried forward, resolved here in favour of the escape hatch so the
reported number stays a key count of the wire projection.

**The sweep / cleanup sites** (`_retry_residue_cleanup_{sync,async}`, and the `finally` blocks of
both delete probes) discard the returned value entirely and needed no change. 31-03's warning
against generalizing a sibling's finding was honoured: each site was judged on its own terms.

---

## 5. CRITERION 1 COMPLETION RECORD — all five endpoints, both surfaces, method and shim

| # | Package | Endpoint | Surface | Method returns | Module shim returns | Landed in |
|---|---|---|---|---|---|---|
| 1 | higyrus-client | `GET /health` | sync | `Health` | `Health` | 31-03 |
| 1 | higyrus-client | `GET /health` | async | `Health` | `Health` | 31-03 |
| 2 | market-data-client | `GET /health` | sync | `Health` | `Health` | 31-04 |
| 2 | market-data-client | `GET /health` | async | `Health` | `Health` | 31-04 |
| 3 | market-data-client | `GET /health/feed` | sync | `HealthFeed` | `HealthFeed` | 31-04 |
| 3 | market-data-client | `GET /health/feed` | async | `HealthFeed` | `HealthFeed` | 31-04 |
| 4 | market-data-client | `POST /calendar/holidays` | sync | `AddHolidaysResult` | `AddHolidaysResult` | **31-05** |
| 4 | market-data-client | `POST /calendar/holidays` | async | `AddHolidaysResult` | `AddHolidaysResult` | **31-05** |
| 5 | market-data-client | `DELETE /calendar/holidays/{day}` | sync | `DeleteHolidayResult` | `DeleteHolidayResult` | **31-05** |
| 5 | market-data-client | `DELETE /calendar/holidays/{day}` | async | `DeleteHolidayResult` | `DeleteHolidayResult` | **31-05** |

**20 sites. Zero untyped-mapping returns. Criterion 1 is closed.** Verified by direct inspection of
all four shell files, and corroborated by `typing.Any` having become unused in market-data's two
shells.

---

## 6. What was built

### `models.py` — two models, nothing else

`AddHolidaysResult` (`days: list[CalendarDay]`, `note: str`, `saved: int`) and
`DeleteHolidayResult` (`day: str`, `deleted: bool`), both `@dataclass(frozen=True, slots=True)` on
`SafeModel`, declared after `CalendarDay` so the reference resolves.

- **`CalendarDay` is REUSED, never duplicated.** The capture's `days[]` items match it field for
  field including both `str | None` hour fields, which the capture shows as `null`. Pinned by a hint
  equality test (`hints_for(AddHolidaysResult)["days"] == list[CalendarDay]`), so a future parallel
  element model fails immediately.
- **Neither carries `received_at`** — a mutation acknowledgement is not a snapshot and has no
  staleness dimension.
- **Neither declares a mapping field, a `from_api` override, or any Optional.** All four captures
  show every field populated; an over-declared Optional would permanently hide that field from the
  divergence census (T-31-17, 31-04's option-b logic applied here). Pinned by a parametrized test.
- Both docstrings carry the three-part audit trail: endpoint + decision reference and the
  response-only framing; live-capture provenance naming the schema JSON by path and recording that
  the sync and async captures are byte-identical; and for `AddHolidaysResult`, why `CalendarDay` is
  reused rather than duplicated.

### `_core.py` — one parser became two

```
@_decode._response_parser        # NEW — the replaced shared parser was UNdecorated
resp.read()                      # body-consume-then-raise: Phase 7 D-06 HTTP/2 invariant
raise_for_response(resp)
if not resp.content: return Model.from_api(None)     # tolerance branch 1
raw = resp.json()
if not isinstance(raw, dict): return Model.from_api(None)   # tolerance branches 2-4
return Model.from_api(raw)
```

The decoration is new on both halves: the replaced function returned a raw mapping and built no
model, so it had no divergences to scope. `__all__` swapped `"parse_calendar_write_response"` for
`"parse_add_holidays_response"` and `"parse_delete_holiday_response"` in sort position and remains
ASCII-sorted (RUF022).

### `client.py` / `aio.py` — 8 sites, plus G-6 on both shells

Four methods and four module shims retyped. The stale paragraph — which claimed the builder was
marked non-idempotent and was *"the ONLY such spec in the package"* — was rewritten on both shells
to state the measured `idempotent=True`, to name Phase 27 / LIVE-MUT-01 and the row-count method
that established it, and to record that no builder in the package carries `idempotent=False` any
more. The 1-500 batch-bound sentence and the path-safety sentence were left intact — both still
describe real live guards on the request path.

### `__init__.py` + the hand-maintained roster

Both names added to the models import block and to `__all__` in ASCII sort position (indices 0 and 5
of `__all__`), **and** to `_NEW_PUBLIC_NAMES` under the `# Phase 31 — ops endpoints (TYP-02)`
comment 31-04 introduced — that tuple asserts *"every listed name is importable"* and never *"every
exported name is listed"*, so omitting them would have been silently green (G-2).
`_MUTATION_METHODS` was **not touched**: the only diff in that file is the two added roster lines.

### The re-mocks

Every holiday-endpoint response body in both calendar-write files now uses the live capture shape
(`_ADD_HOLIDAYS_200`, `_DELETE_HOLIDAY_200`, each with a provenance comment naming the JSON by path),
and every assertion on a returned value is attribute access on a model. The delete case is the
sharpest: the mock sent the integer `1` and asserted a mapping equality against it — both changed.

Both files gained an explicit empty-200 → zero-valued-model assertion: the T-26-13 tolerance now
expressed through the type.

**The refusal matrix, host-mismatch and path-safety tests are semantically untouched.** The
zero-request assertion count is **12 (sync) / 11 (async)** — identical to the pre-task count,
verified by `git show 69e6145:...`. Those are the behavioural half of the ASVS V4 gate. The three
config-trio tests were left alone; they route through `parse_calendar_config_response`, which this
phase does not modify.

---

## Decisions Made

All five key decisions are in the frontmatter and expanded in sections 2-4 above. In brief:

- **G-4 → tolerance**, deliberately diverging from 31-04's health-parser disposition on the non-dict
  branch, because these are published mutations.
- **`deleted` is `bool`**, and the int-arrival outcome was measured rather than assumed.
- **The driver's Phase-27 verdict prose stays**, recorded as a scope decision rather than left
  silent.
- **Delete-probe snapshot blindness accepted** with a mandatory carry-forward.
- **`CalendarDay` reused**, pinned by test.

## Deviations from Plan

### 1. [Rule 3 — Sequencing] The calendar-write re-mocks were folded into Task 2's RED gate

- **Found during:** Task 2 planning, on reading the plan's own Task 2 `<verify>` block.
- **Issue:** The plan assigns the `test_calendar_write{,_async}.py` re-mocks to **Task 3**, and its
  Task 2 `<verify>` deliberately omits those two files. Landing Task 2's GREEN with the re-mocks
  still pending would have left the package suite **red at a commit boundary** (6 mapping-equality
  assertions contradicting the new return types).
- **Fix:** applied 31-04's ratified deviation-5 precedent (itself inherited from 31-03's
  deviation 1): the re-mocks landed in Task 2's **RED** commit, so Task 2's GREEN restored the suite
  fully green at a deliberate gate. Task 3 kept its own substance — the driver result reads, the
  carry-forward notes and the phase gate.
- **Verification:** `uv run pytest packages/market-data-client -q` → 552 passed at Task 2 GREEN.
- **Committed in:** `80212bb` (RED) / `7a9af04` (GREEN)

### 2. [Rule 1 — Bug] A THIRD instance of the stale G-6 claim, in a test-file section comment

- **Found during:** Task 2, while reading `test_calendar_write.py`'s retry section.
- **Issue:** the section comment at `test_calendar_write.py:~592` asserted that
  `build_add_holidays_request` *"es el ÚNICO builder `idempotent=False` del paquete"* and that
  `RetryTransport` therefore cut its loop on the first line. That is the **same stale claim G-6
  names**, in a third location the plan did not enumerate — and it directly **contradicted the two
  tests it headed**, both of which already assert the corrected behaviour (3 requests, 2 sleeps).
  A reader trusting the header over the tests is exactly the trap G-6 exists to remove.
- **Fix:** rewritten to state the measured D-20 behaviour, to name the Phase-27 row-count
  measurement that established it, to record explicitly that the comment (not the tests) was what
  had gone stale, and to point at `test_mutation_gate_ast.py` as the flag's authority. No test
  semantics changed.
- **Checked and NOT changed:** `test_transport.py:~112`'s equivalent block, which is already
  accurate — it describes the flag's history in the past tense and explains why the short-circuit is
  now re-pinned on a synthetic non-idempotent spec. `aio.py`'s counterpart docstring, which the plan
  asked to be checked for the same drift, **did** carry it and was corrected identically to
  `client.py`'s.
- **Committed in:** `80212bb`

### 3. [Rule 3 — Blocking] `typing.Any` became unused in both shells and had to be dropped

- **Found during:** Task 2 GREEN lint gate.
- **Issue:** `uv run ruff check` reported F401 in `client.py:46` and `aio.py:35`. The holiday pair
  held the last `dict[str, Any]` annotation in each file; once retyped, `Any` had no remaining use.
- **Fix:** `from typing import Any, Self` → `from typing import Self` in both shells.
- **Why it is worth recording rather than a silent tidy:** it is **incidental evidence for
  criterion 1** — `Any` becoming unused in a shell means no untyped-mapping return survives in it.
- **Committed in:** `7a9af04`

### 4. [Acceptance-criterion literalism, not a code change] The removed-parser grep counts prose

- **Found during:** Task 2 acceptance verification.
- **Issue:** the criterion reads *"`grep -rn 'parse_calendar_write_response' --include='*.py' .`
  returns no results"*. It returns **5**: three historical prose references that the plan's own
  `<action>` block **required** (*"carrying forward the T-26-13 tolerance argument from the function
  being replaced"* — two in the new parsers' docstrings, one in a test section comment) and two
  **negative assertions** in `test_core_all_exports_calendar_write_surface_in_order` that exist
  precisely to prove the name is gone.
- **Resolution:** the criterion's intent — *"no remaining CALLER"* — holds strictly. Verified two
  ways: filtering prose and negative assertions out of the grep returns **zero**, and
  `hasattr(_core, 'parse_calendar_write_response')` is **`False`** at runtime. Same class as 31-01's
  deviation 3, where two acceptance greps were tripped by prose the plan itself mandated.

**Total deviations:** 4 (1 sequencing, 1 bug-fix, 1 blocking-fix, 1 criterion-literalism). No scope
creep. Every plan prohibition was respected: the gate was not relaxed, reordered or skipped; no
request byte moved; neither `idempotent=` flag was touched; no tolerance branch became a raise; and
`deleted` was not widened to accommodate the contradicted mock.

## Issues Encountered

### Pre-existing matriz `verification/` failures (D-1) — reproduced exactly, untouched

The full local suite reports **19 failed + 19 errors**, all confined to
`verification/test_main_matriz_login_fail_uniformity.py` and
`verification/test_matriz_sweep_snapshot.py` — the stale pre-Phase-15 `probe_login_sync()` signature
logged as **D-1** by plan 31-02. Confirmed by running those two files in isolation and reproducing
exactly 19 + 19. Out of scope per the phase's scope boundary.

### Four pre-existing `mypy --strict` errors in `packages/market-data-client/tests/` (D-4)

`uv run mypy packages/market-data-client/tests` exits 1 with exactly the **same four** errors 31-04
recorded — `test_reference_core.py:412`, `test_core.py:436` (a Phase-26 `body = {"market_hours": []}`
needing an annotation), and two in `test_decode.py`. **This plan introduced none of them and fixed
none of them**, so the count is unchanged at 4. The plan does not require `mypy` on `tests`; both
required gates (`packages/market-data-client/src` and the CI `src` gate) are clean. Remains
deferred as **D-4**.

## Verification Results

| Gate | Result |
|---|---|
| `uv run pytest packages/market-data-client -q` | **552 passed** (was 527 — 25 net new tests, none removed) |
| `uv run pytest packages/market-data-client packages/higyrus-client -q` | **788 passed** (baseline floor was 699) |
| `uv run pytest -q` (full local suite incl. `verification/`) | **2025 passed**; 19 failed + 19 errors, ALL in the two D-1 matriz files |
| `.../test_v040_request_pin.py` + `.../test_mutation_gate_ast.py` | **9 passed**, re-run after every task |
| `git diff 69e6145 -- <those two files>` | **EMPTY** — the gates passed WITHOUT being adjusted |
| gate/builder lines in the `client.py`/`aio.py` diff | **none changed** |
| `uv run mypy packages/market-data-client/src` | **Success: no issues found in 13 source files** (MANDATORY local, D-13) |
| `uv run mypy` (CI `src` gate) | **Success: no issues found in 62 source files** |
| `uv run mypy packages/market-data-client/tests` | **4 pre-existing errors** — unchanged from 31-04, D-4 |
| `uv run python tools/check_decode_intactness.py` | **A/B/C/D all pass** — `_decode.py` still hashes to `CANONICAL_DIGEST` across all five copies |
| `uv run python tools/check_uniform_structure.py` | **pass** |
| `uv run ruff check .` | **All checks passed** |
| `uv run ruff format --check .` | **231 files already formatted** |
| `verification/test_public_surface.py` + nyquist + the two market-data driver guards | **15 passed** |
| `python -c "[m.__all__.index(n) for n in (both names)]"` | **exit 0** (indices 0, 5) |

All of Task 1's, Task 2's and Task 3's grep-shaped acceptance criteria were run and match, with the
one documented exception in deviation 4:

- 2 model classes; `days: list[CalendarDay]` x1; `deleted: bool` x1
- both new parsers decorated; `__all__` swapped one name for two and stays sorted
- 8 sites retyped (2 + 2 per shell, per form); 2 roster entries; both exports importable
- 0 mapping-literal holiday assertions in either calendar-write file
- live shapes present in both files (`"saved"` x1, `"deleted": True` x1 each)
- refusal-matrix zero-request assertions: **12 / 11**, identical to the before-count
- both add probes use `to_dict()`; both delete probes carry the census carry-forward

## Threat Flags

None. This plan introduced no new network endpoint, no new auth path, no new file-access pattern and
no schema change at a trust boundary. Every threat in the register was addressed as planned:

| Threat | Disposition | Outcome |
|---|---|---|
| T-31-24 gate ordering | mitigate | AST guard green after every task, diff empty; no changed diff line names the gate |
| T-31-25 request drift | mitigate | Raw-bytes pin green after every task, diff empty |
| T-31-26 retry amplification | mitigate | Both builders untouched, still `idempotent=True`; the stale docstring that would have seeded the wrong edit is corrected on both shells (and in a third location) |
| T-31-27 path retargeting | transfer | Builder guard untouched; the path-safety tests stay semantically intact |
| T-31-28 tolerance→raise | mitigate | G-4 resolved toward tolerance; all four branches asserted per parser |
| T-31-29 snapshot blindness | accept | Carry-forward note added to both probe docstrings, routing Phase 33 to the census |
| T-31-30 info disclosure | accept | Re-mocks use the conftest-seeded token and committed capture shapes; no payload value in any finding string |
| T-31-SC package installs | mitigate | Zero installs; `uv.lock` unchanged |

## Known Stubs

None. Every declared field is wired to a live-capture wire key; no placeholder, mock or hardcoded
empty value was introduced. Both models declare zero Optionals, so there is no under-determined
declaration to carry forward from this plan.

## User Setup Required

None. No package was installed; `uv.lock` is unchanged.

## Carried-forward open items (not resolved here)

- **TYP-02 / concurrency / UNRESOLVED.** The probe row asks a broader question than this plan's
  evidence answers, and it is **not dismissed**. What is guaranteed today is a property of the
  SERVER and of the builders, neither of which this plan changed: `POST /calendar/holidays` upserts
  by date (measured live in Phase 27 — two identical POSTs, exactly one row), and a repeated DELETE
  is idempotent in state though possibly not in status (a second DELETE may return 404, recorded by
  the driver's D-19 verdict). An interrupted call therefore leaves server state governed by those
  semantics regardless of the response TYPE. That is context, not resolution. **The row stays open.**
- **The driver's `_emit_holiday_idempotency_verdict` prose** still names `idempotent=False`. Scoped
  out deliberately (see § 3); if a future phase wants it modernized, note that editing it changes the
  driver's emitted finding strings and rewrites a completed measurement's audit trail.
- **D-1 through D-4** in `deferred-items.md` remain untouched and out of scope.

## Next Phase Readiness

**For the phase verifier:**

- Criterion 1 is closed — the 20-site table in § 5 is the completion record.
- Criteria 2 and 3 are closed with mechanical evidence — § 1.
- The full local suite is green apart from the two D-1 matriz files, which reproduce identically in
  isolation and predate this phase.
- `uv run mypy packages/<pkg>/tests` remains red on **pre-existing** grounds in three packages
  (D-2 ambito, D-3 higyrus, D-4 market-data). The `typecheck` CI job iterates `higyrus-client` first
  under `set -e`, so D-3 masks the rest; the family needs one repair plan before v1.6 ships.

**Carry into Phase 33 (drivers strict mode):**

- **The delete-holiday snapshot is drift-blind — use the divergence census.** § 4 is written to be
  picked up verbatim; both probe docstrings carry the same warning in-code.
- **Both add-holiday snapshots remain wire-derived**, so their SHAPE findings stay meaningful and
  their census and snapshot diff remain independent signals.
- **Both new parsers carry an empty-body → `from_api(None)` carve-out**, so they inherit 31-03's
  measured strict-mode behaviour: a legitimate 204 emits one `non_dict` record and, under
  `strict_decode=True`, raises. Not re-measured here; the walker is byte-identical across packages.
- **Zero new under-determined nullability declarations** from this plan — unlike 31-04's nine, there
  is nothing here for Phase 33 to adjudicate on that axis.

**Carry into Phase 34 (release):**

- Both endpoints carry the **one-way** reversibility rating: `add_holidays` and `delete_holiday`
  shipped in v0.4.0 returning a mapping, and an external consumer's subscript access breaks at source
  level. This matches the identical rating recorded by 31-04 and is input to the bump decision. The
  door was chosen by the ROADMAP phase goal and CONTEXT D-01, so no checkpoint re-asked it.

---
*Phase: 31-endpoints-de-ops-estructura-uniforme*
*Completed: 2026-08-25*

## Self-Check: PASSED

All 10 claimed source/test files plus this SUMMARY exist on disk, and all five task commits
(`e44d762`, `79fd762`, `80212bb`, `7a9af04`, `70ecb3e`) are present in git history.
