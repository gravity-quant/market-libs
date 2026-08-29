---
phase: 37
plan: 01
subsystem: matriz-client response parsing
tags: [envelope-unwrap, risk-endpoints, d-03, strict-unwrap, tdd, null-object]
status: complete

requires:
  - "matriz_client._core.unwrap (Phase 7) — typed PrimaryAPIError on a missing envelope key"
  - "matriz_client._core.parse_envelope_response (Phase 7 CR-03) — body-consume-then-raise ordering"
  - "matriz_client._decode._response_parser (Phase 29) — decode-scope ownership"
provides:
  - "Risk parsers that reach their payload through the vendor envelope keys detailedPosition / accountData"
  - "A tested, operator-ratified disposition for a flat (unenveloped) Risk body: raise"
  - "A single envelope parser in _core.py (the unwrap-less duplicate is gone)"
  - "The D-03 disposition record that Plans 37-02 / 37-03 read to shape their test payloads"
affects:
  - "37-03 — DetailedPosition.report and AccountReport.detailedAccountReports now decode from the correct nesting level, so typing them is no longer inert"
  - "37-02 — unblocked indirectly (same precondition, RESEARCH Pitfall 1)"
  - "Phase 39 (LIVE-NOBJ-01) — inherits the one unverified assumption this plan creates"

tech-stack:
  added: []
  patterns:
    - "Envelope unwrap via the existing unwrap() helper, never a hand-rolled membership check (D-MATZ-9)"
    - "TDD RED/GREEN/REFACTOR as three separate commits"
    - "Falsified prose corrected in the same commit as the code that falsifies it"

key-files:
  created: []
  modified:
    - packages/matriz-client/src/matriz_client/_core.py
    - packages/matriz-client/tests/test_core.py
    - packages/matriz-client/tests/test_async_queries.py

decisions:
  - "D-03 disposition ratified as strict-unwrap by the operator at the 37-01 checkpoint"
  - "The plan-unanticipated flat fixtures in test_async_queries.py were migrated, not deleted"
  - "_parse_risk_response deleted; its history preserved in parse_envelope_response's docstring"

metrics:
  duration: ~10 min
  completed: 2026-08-29
  tasks: 3
  commits: 3
  files_changed: 3
  tests: 488 → 493
---

# Phase 37 Plan 01: Envelope-unwrap fix for the matriz Risk parsers — Summary

Both matriz Risk response parsers now unwrap the vendor's `detailedPosition` / `accountData`
envelope before decoding, so the four fields Plans 37-02/37-03 are about to type decode from the
right nesting level instead of never populating at all.

## D-03 disposition

**Ratified option id: `strict-unwrap`**

Operator's verbatim answer, received at the Task 1 checkpoint:

> **strict-unwrap**
>
> matches the sibling `parse_get_positions_response` behavior, makes a wrong-shape response loud
> (raises `PrimaryAPIError`) instead of silently returning an empty-looking account, fully
> reversible via git revert.

**What this means for downstream plans:** the **enveloped** body is canonical. Plan 37-03's
`report` and `detailedAccountReports` test payloads must be shaped
`{"status": "OK", "detailedPosition": {"report": {...}}}` and
`{"status": "OK", "accountData": {"detailedAccountReports": {...}}}` — a flat payload will now
raise `PrimaryAPIError` rather than decoding to an all-defaults model, so a flat fixture will
redden rather than silently pass with empty fields.

**Evidence quoted at the checkpoint, as the task required.** The absence below is the evidence gap
the decision priced — it was measured, not asserted:

```
$ ls .planning/verification/schemas/matriz-client/
get-all-instruments.json          get-instruments-details.json
get-instrument-detail.json        get-market-data.json
get-instruments-by-cfi-esxxxx.json  get-segments.json
get-instruments-by-segment.json   get-trades.json

$ grep -rn 'detailedPosition\|accountData' .planning/verification/schemas/
(no matches — exit 1)
```

Eight committed schemas covering instruments, market data, segments and trades. **No live capture
of either Risk endpoint exists anywhere in the repo**, and none could be produced: `main_matriz.py`
asserts the remarkets hostname (D-MATZ-33 / `LIVE-MATZ-33`) and that assert was never bypassed.
The payload provenance for everything in this plan is therefore **`vendor-documented, unmeasured`**
(D-04a) — never presented as a capture. Real verification is deferred to Phase 39
(`LIVE-NOBJ-01`), which is where this assumption gets discharged.

## What Was Built

### Task 1 — checkpoint:decision (no code)

Presented the three options verbatim with the evidence gap measured. Halted rather than
auto-resolving: `workflow.auto_advance` and `_auto_chain_active` are both `true`, and the generic
GSD auto-mode rule would have auto-selected the front-loaded first option — but the orchestrator
explicitly overrode that for this checkpoint, and the plan's own `must_haves` demand the flat-body
disposition be "operator-ratified — never a silent behaviour drift discovered later". Working tree
carried no source-file modification at the moment the checkpoint was presented.

### Task 2 — the fix, TDD (commits `00ffb2f` RED → `2c07df1` GREEN)

**RED (`00ffb2f`)** — six cases written against the unfixed parsers, four correctly failing:

| Case | Asserts |
|------|---------|
| `..._detailed_positions_response_unwraps_envelope` | enveloped body populates `account`, `totalMarketValue`, `totalDailyDiffPlain`, `lastCalculation` |
| `..._account_report_response_unwraps_envelope` | enveloped body populates `accountName`, `margin`, `currentCash` |
| `..._detailed_positions_response_raises_on_flat_body` | flat body → `PrimaryAPIError`, `"missing envelope key 'detailedPosition'"` |
| `..._account_report_response_raises_on_flat_body` | flat body → `PrimaryAPIError`, `"missing envelope key 'accountData'"` |
| `test_risk_parsers_raise_on_status_error_before_the_envelope_lookup` | preserved: vendor `status == "ERROR"` wins over the key lookup (both parsers) |
| `test_risk_parsers_raise_on_non_dict_body_naming_the_endpoint` | preserved: non-dict body raises naming the endpoint path (both parsers) |

The last two passed immediately, which is correct — they pin contracts that must survive the
change, not new behaviour. The RED commit measured `4 failed, 489 passed`.

The happy-path assertions are written as the **inversion of the bug**, not merely as value checks:
before this plan the identical enveloped body decoded `account is None`, because the root body
reached `from_api` and `detailedPosition` was absorbed as an `extra` key.

**GREEN (`2c07df1`)** — both parsers repointed to `parse_envelope_response(resp, path)` +
`unwrap(data, "<key>", path)`, preserving the `@_decode._response_parser` decorator, the
signatures, and the `path` local. No hand-rolled `if key not in data` — `unwrap` already raises
the typed `PrimaryAPIError` that keeps the client's exception contract (D-MATZ-9).

All **five** falsified prose sites corrected in the same commit, each citing the vendor doc range
that falsifies it, and the two parser docstrings naming the ratified option id so a future reader
can tell a decision from a drift:

| Site | Was | Now |
|------|-----|-----|
| `build_get_detailed_positions_request` | "Risk §9.2 sin envelope key — payload raíz ES el resultado" | cites `Primary-API.md:1701-1703`, names D-03 / `strict-unwrap` |
| `build_get_account_report_request` | "Risk §9.3 sin envelope key — payload raíz ES el resultado" | cites `Primary-API.md:1817-1819` |
| `parse_get_detailed_positions_response` | "Parse risk payload raíz (NO envelope key, D-07)" | "Parse envelope `{detailedPosition: {...}}`" + the bug's mechanism + the ratified disposition |
| `parse_get_account_report_response` | "Parse risk payload raíz (NO envelope key, D-07)" | "Parse envelope `{accountData: {...}}`" |
| `_parse_risk_response` | "payload raíz ES el resultado (NO envelope key, D-07)" | corrected here, function then deleted in Task 3 |

### Task 3 — the fold (commit `bb02b8f`)

`_parse_risk_response` was byte-identical to `parse_envelope_response` except for the missing
`unwrap` call; once Task 2 landed it had zero callers. Confirmed before deleting:

```
$ grep -rn '_parse_risk_response' packages/ tools/ verification/ main_matriz.py
packages/matriz-client/src/matriz_client/_core.py:290:def _parse_risk_response(...)
```

Only its own definition. Deleted. `_core.py` now has exactly one envelope parser.

Its history was carried forward into `parse_envelope_response`'s docstring rather than dropped:
that matriz once shipped a second, unwrap-less copy; that the copy rested on a claim the vendor doc
*committed inside the package itself* falsifies; and that Phase 37 D-03 removed it. The
counter-evidence line ranges travel with the record.

## Key Implementation Details

**One site each, not mirrored (RESEARCH F-4).** `client.py:679,685` and `aio.py:713,718` delegate
to `_core`, and both are **byte-unchanged** — verified by an empty
`git diff -- client.py aio.py`. The CLAUDE.md dual-sync/async rule is satisfied by construction
here; a mirrored task would have been a no-op that fabricated the appearance of coverage. The
migrated async fixtures (below) are the empirical proof: the async path went green without an
`aio.py` edit.

**`models.py` untouched**, per the plan's prohibition — the four field retypes belong to Plans
37-02 and 37-03, and landing an annotation change here would have put two plans on the same file
in the same wave.

**`_decode.py` untouched** — `check_decode_intactness.py` green, all five copies still reduce to
the canonical hash `a1f00c824348164c`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] Two flat-shaped async fixtures the plan did not enumerate**

- **Found during:** Task 2, GREEN phase
- **Issue:** `test_async_queries.py::test_async_get_detailed_positions` (AQ16) and
  `::test_async_get_account_report` (AQ17) encode the flat body and reddened on the contract
  change. The plan and 37-RESEARCH both located the flat fixtures only in `test_core.py:327`; these
  two were missed by the pre-plan survey, which greps for the parser *function* names — these tests
  call the public `aio.*` surface instead, so they never matched.
- **Fix:** migrated both to the enveloped shape and corrected their docstrings, per the plan's
  standing instruction "Migrate, do not delete". Neither was deleted and no assertion was weakened.
- **Files modified:** `packages/matriz-client/tests/test_async_queries.py`
- **Commit:** `2c07df1`
- **Note:** this widens Task 2's `git diff --name-only` acceptance criterion from two files to
  three. The criterion's intent — that `client.py` and `aio.py` stay untouched (F-4) — holds
  exactly; the third file is a test fixture, not a mirrored source edit.

**2. [Rule 1 — Bug] Wrong attribute name in a test I wrote**

- **Found during:** Task 2, RED phase
- **Issue:** asserted `exc_info.value.message`; `PrimaryAPIError` stores the ctor's `message` kwarg
  as `api_message` (`exceptions.py:23-26`) because `message` would collide with `BaseException`.
- **Fix:** corrected to `api_message` with an explanatory comment, before the RED commit.
- **Commit:** `00ffb2f`

### Accepted Tension

Task 3's acceptance criterion asks that `grep -rn '_parse_risk_response'` return no matches, while
the same task's action requires "recording that matriz once had a second, unwrap-less copy of this
parser". Both cannot literally hold. The history paragraph in `parse_envelope_response` names the
deleted function, so one prose match survives. Naming it is what makes the record useful — an
anonymous "there used to be a duplicate" would not stop a future reader from re-adding it. **No
code** references the symbol.

## Known Stubs

None. No placeholder, no hardcoded empty, no TODO introduced.

## Threat Flags

None. This plan introduced no new network endpoint, auth path, file access pattern, or schema at a
trust boundary. Threat register dispositions were honoured:

- **T-37-01 (mitigate)** — both parsers reach the payload through `unwrap()`, which raises rather
  than producing an all-defaults model that reads as "the account holds nothing". Locked by the two
  `..._raises_on_flat_body` tests.
- **T-37-02 (mitigate)** — `parse_envelope_response` keeps the `resp.read()` →
  `raise_for_response` → shape-check ordering; `test_parse_envelope_consumes_body_before_raise` is
  green.
- **T-37-03 (accept)** — the new raise path's `description` interpolates only the static envelope
  key name and the endpoint path assembled in `_core.py`; no wire value, no credential.
  `_logging.py` untouched (Check B hash-locked).
- **T-37-05 (mitigate)** — the D-MATZ-33 hostname assert was never bypassed. No live run was
  attempted.
- **T-37-SC (accept)** — zero packages installed; `uv.lock` untouched.

## Deferred / Follow-ups

- **`DetailedPosition.lastCalculation` is annotated `str | None` but the wire carries an epoch
  `int`** (`Primary-API.md:1791` → `1669996294136`). Out of scope here (`models.py` is prohibited
  in this plan). matriz runs with `scalar_passthrough=True` (`_decode.py:140`), so the value
  arrives verbatim and the mismatch is **reported as a divergence, not swallowed** — the field
  populates, which is what this plan's must-have required. `AccountReport.lastCalculation` is not a
  declared field at all. Worth a disposition in a later matriz plan or the Phase 38 audit.
- **The whole flat-body disposition is unverified against the live API** and cannot be verified
  before `LIVE-MATZ-33` lifts. This is 37-RESEARCH assumption A1 — the only assumption in the phase
  with real behavioural risk. Destination: Phase 39 / `LIVE-NOBJ-01`. D-03 grants the escape hatch:
  if live evidence later shows a flat body is real, `git revert bb02b8f 2c07df1` restores the old
  behaviour with no migration and no data involved.

## Verification Results

| Check | Result |
|-------|--------|
| `pytest packages/matriz-client/tests -q` | **493 passed** (baseline 488; criterion: strictly greater) |
| `pytest packages/matriz-client/tests/test_core.py -k envelope -q` | **8 passed** (criterion: ≥ 2) |
| `mypy packages/matriz-client/src` | Success — no issues in 17 source files |
| `ruff check packages/matriz-client` | All checks passed |
| `ruff format --check packages/matriz-client` | 43 files already formatted |
| `python tools/check_decode_intactness.py` | Checks A–D green; `_decode.py` byte-unchanged |
| `python tools/check_surface_types.py` | 0 violations |
| `grep -c 'detailedPosition' _core.py` | 8 (criterion: ≥ 2) |
| `grep -c 'accountData' _core.py` | 5 (criterion: ≥ 2) |
| `grep -c 'NO envelope key' _core.py` | **0** — the falsified claim does not survive anywhere |
| `git diff -- client.py aio.py` | empty — byte-unchanged (F-4) |

## Success Criteria

- [x] An enveloped `detailedPosition` body populates `DetailedPosition.account` and
      `.totalMarketValue`; an enveloped `accountData` body populates `AccountReport.accountName`
      and `.margin`. All four were `None` before this plan.
- [x] The flat-body outcome is locked by named tests matching the ratified `strict-unwrap` option.
- [x] Zero surviving prose in `_core.py` asserts the Risk payload has no envelope key.
- [x] `client.py` and `aio.py` are byte-unchanged.

## Commits

| Commit | Type | Description |
|--------|------|-------------|
| `00ffb2f` | test | RED — failing envelope regressions for both Risk parsers |
| `2c07df1` | feat | GREEN — unwrap the vendor envelope in both Risk parsers + 5 prose corrections |
| `bb02b8f` | refactor | Fold `_parse_risk_response` into `parse_envelope_response` |

## Self-Check: PASSED

All four claimed files exist on disk. All three claimed commit hashes resolve in `git log`. Both
`must_haves.artifacts` `contains` probes hold (`_core.py` ⊃ `detailedPosition`, `test_core.py` ⊃
`accountData`), and both `must_haves.key_links` patterns match in `_core.py`
(`unwrap(data, "detailedPosition"` and `unwrap(data, "accountData"`).

## TDD Gate Compliance

Full RED → GREEN → REFACTOR sequence present and in order. RED (`00ffb2f`) was verified to fail
for the right reason (`4 failed, 489 passed` — the four new behavioural cases, not a collection
error) before any implementation was written. No test was deleted to make a red go away, and the
matriz suite is green at every commit of this plan.
