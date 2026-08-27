---
phase: 27-verificaci-n-en-vivo-segura-fixes
plan: 02
subsystem: api
tags: [market-data-client, httpx, safemodel, calendar, parser, tdd, pytest]

# Dependency graph
requires:
  - phase: 22-market-data-client-lecturas
    provides: "The SafeModel base, the reference-read parser ladder and the PROVISIONAL CalendarDay"
  - phase: 26-market-data-client-mutaciones
    provides: "HolidayIn / parse_calendar_write_response, and the D-16 hand-off that assigned this fix to Phase 27"
provides:
  - "parse_calendar_response unwraps the develop envelope {config, coverage, days[], market} via days"
  - "CalendarDay retyped to the five fields that actually exist on the wire"
  - "Double collection guard: missing days, non-list days, null, scalar and 204 bodies all collapse to []"
  - "Mirrored sync/async dispatch regression coverage for the enveloped calendar body"
affects: [27-03-driver-shape-diff, 27-04-holiday-cycle, 27-05-live-evidence, 27-06-in-cycle-fixes, 28-release]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Envelope-unwrap parser ladder (parse_latest_response shape) applied to a reference-data collection parser"
    - "Wire-reconciled SafeModel docstring recording the committed schema baseline as the source of truth"

key-files:
  created: []
  modified:
    - packages/market-data-client/src/market_data_client/models.py
    - packages/market-data-client/src/market_data_client/_core.py
    - packages/market-data-client/tests/test_reference_models.py
    - packages/market-data-client/tests/test_reference_core.py
    - packages/market-data-client/tests/test_reference_client.py
    - packages/market-data-client/tests/test_reference_async_client.py

key-decisions:
  - "CalendarDay is the HolidayIn shape echoed back: day/closed/description required, open_time/close_time as str | None"
  - "get_calendar keeps its published return type list[CalendarDay] — the fix is behavioural only (D-13 minor/non-breaking)"
  - "The unwrap key is days, not items — the only structural difference from the market-data sibling parsers"
  - "Bare-list tolerance is kept as a behaviour, not deleted, so an older/simpler body shape still parses"

patterns-established:
  - "Reference collection parsers use the same three-branch shape ladder plus a non-list second guard as parse_latest_response"
  - "Mocked test bodies reproduce only the SHAPE of the committed PII-free schema baseline, never live values"

requirements-completed: [LIVE-MUT-01]

# Metrics
duration: 62min
completed: 2026-08-01
status: complete
---

# Phase 27 Plan 02: Calendar envelope parse fix Summary

**`GET /calendar` now yields real holiday rows: `parse_calendar_response` unwraps the develop `{config, coverage, days[], market}` envelope via `days`, and `CalendarDay` was retyped from the fictional `date`/`marketId`/`isBusinessDay` triple to the five fields the wire actually sends.**

## Performance

- **Duration:** ~62 min (dominated by two >13 min full-monorepo suite runs)
- **Tasks:** 2 (both TDD, 4 commits total)
- **Files modified:** 6
- **Package suite:** 329 → 342 tests (+13), all green

## Accomplishments

- Killed a silent false-PASS: the old parser iterated the response **dict**, so `get_calendar()`
  returned four all-default `CalendarDay` rows built from the strings `"config"`, `"coverage"`,
  `"days"`, `"market"`. It now returns one populated row per actual calendar day.
- Reconciled `CalendarDay` against the committed baseline
  `.planning/verification/schemas/market-data-client/get-calendar.json`: the three declared fields
  existed nowhere on the wire and were replaced by the real `HolidayIn`-echo shape.
- Hardened the parser against degenerate bodies (T-27-11): a dict without `days`, a non-list
  `days`, `null`, a scalar and a 204 all collapse to `[]`; `401`/`429`/`422` still raise before
  any decoding (body-consume-then-raise order untouched).
- Mirrored coverage across both shells per CLAUDE.md — `test_reference_client.py` and
  `test_reference_async_client.py` are file-for-file symmetric.
- Unblocks **ROADMAP criterion 2**: `GET /calendar` is the only read that can confirm an
  `add_holidays` landed, so the 27-04 holiday create→verify→revert cycle is now verifiable.

## Task Commits

Each task was committed atomically, RED then GREEN (both tasks are `tdd="true"`):

1. **Task 1: Retype CalendarDay to the real develop wire shape**
   - `ee83feb` (test) — 5 failing `CalendarDay` wire-shape tests (RED gate)
   - `831f44f` (feat) — retype the dataclass (GREEN gate)
2. **Task 2: Unwrap the calendar envelope and mirror the coverage sync/async**
   - `63ad4c6` (test) — 8 failing envelope tests across `_core` and both shells (RED gate)
   - `f6fe44f` (fix) — the `days` unwrap ladder in `parse_calendar_response` (GREEN gate)

No REFACTOR commit was needed on either task; ruff `--fix` import ordering was folded into the
respective GREEN commit.

## Files Created/Modified

- `packages/market-data-client/src/market_data_client/models.py` — `CalendarDay` fields replaced;
  docstring rewritten in the `CalendarConfig` "reconciled against the real wire" style, recording
  the baseline, the `HolidayIn`-echo relationship, and the D-13 non-breaking rationale.
- `packages/market-data-client/src/market_data_client/_core.py` — `parse_calendar_response` body
  rewritten to mirror `parse_latest_response` exactly (`days` instead of `items`); docstring drops
  the stale "flat list item (D-06 collection), not a wrapped object" claim. Signature, return type
  and `build_calendar_request` unchanged.
- `packages/market-data-client/tests/test_reference_models.py` — model-level tolerance coverage.
- `packages/market-data-client/tests/test_reference_core.py` — parser-level envelope, tolerance and
  error-status coverage; new `_CALENDAR_ENVELOPE` fixture constant.
- `packages/market-data-client/tests/test_reference_client.py` — sync dispatch on the envelope.
- `packages/market-data-client/tests/test_reference_async_client.py` — async twin.

## Test Function Names (for plan 27-06 `Regression:` bullets)

`packages/market-data-client/tests/test_reference_models.py`
- `test_calendar_day_from_api_partial_fills_typed_zeros` *(name kept, body rewritten to the new fields)*
- `test_calendar_day_from_api_populated_wire_row` *(new)*
- `test_calendar_day_from_api_session_hours_populate_str_fields` *(new)*
- `test_calendar_day_from_api_none_and_non_dict_return_defaults` *(new)*
- `test_calendar_day_from_api_extra_keys_ignored` *(new)*

`packages/market-data-client/tests/test_reference_core.py`
- `test_parse_calendar_response_unwraps_days_envelope` *(new — the D-12 regression guard)*
- `test_parse_calendar_response_bare_list_still_parses` *(renamed successor of `test_parse_calendar_response_returns_list_of_models`)*
- `test_parse_calendar_response_dict_without_days_returns_empty` *(new)*
- `test_parse_calendar_response_non_list_days_returns_empty` *(new)*
- `test_parse_calendar_response_scalar_body_returns_empty` *(new)*
- `test_parse_calendar_response_401_raises_auth` *(new)*
- `test_parse_calendar_response_429_raises_rate_limit` *(new)*
- `test_parse_calendar_response_422_raises_api_error` *(new)*
- `test_parse_calendar_response_null_and_204_return_empty` *(pre-existing, unchanged)*

`packages/market-data-client/tests/test_reference_client.py`
- `test_get_calendar_sends_bearer_and_year` *(name kept, body switched to the envelope)*
- `test_get_calendar_unwraps_days_envelope` *(new)*

`packages/market-data-client/tests/test_reference_async_client.py`
- `test_async_get_calendar_sends_bearer_and_year` *(name kept, body switched to the envelope)*
- `test_async_get_calendar_unwraps_days_envelope` *(new)*

## Final `CalendarDay` Field List

```python
day: str
closed: bool
description: str
open_time: str | None = None
close_time: str | None = None
```

`@dataclass(frozen=True, slots=True)`, `SafeModel` base, entry kept in `models.__all__`, no
`received_at` stamp (D-05). Removed: `date`, `marketId`, `isBusinessDay`.

## Neither Shell Parses the Calendar Body Inline — Confirmed

```
$ grep -c "_core\.parse_calendar_response(" .../client.py  -> 1
$ grep -c "_core\.parse_calendar_response(" .../aio.py     -> 1
```

Both `Client.get_calendar` (`client.py:582`) and `AsyncClient.get_calendar` (`aio.py:593`) return
`_core.parse_calendar_response(resp)` directly. There is exactly **one** production edit point, so
the sync/async mirroring collapses to the shared parser. `year` is still threaded as a query param
through `_core.build_calendar_request`, which was not modified.

## Decisions Made

- **D-13 upheld, no contradicting evidence found.** The "no consumer could ever have read a
  populated `CalendarDay`" rationale survives inspection: the only in-repo consumer,
  `main_market_data.py:518` / `:815`, passes the **class** to `_emit_shape` for a bidirectional
  SHAPE diff — it never reads a field off an instance. There is no other reader anywhere in the
  monorepo. Retyping stays **minor / non-breaking**.
- Kept bare-list tolerance as an explicit tested behaviour rather than deleting the old test, so a
  simpler body shape (or a future un-enveloped endpoint variant) does not regress to `[]`.
- Added `429` and `422` raise tests alongside the `401` one; the plan's `<behavior>` block listed
  all four statuses but only `401` had prior coverage on a calendar parser.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Restored the workspace venv after `uv run --package` narrowed it**
- **Found during:** Task 1 (baseline test run)
- **Issue:** The plan's stated gate command `uv run --package market-data-client pytest ...` cannot
  work in this workspace — the root `[dependency-groups] dev` (which owns `pytest`) is not visible
  to a package-scoped env, so it fails with `Failed to spawn: pytest`. Worse, running it *rewrote*
  `.venv` down to `market-data-client` only, which then broke collection for the other five
  packages (`ModuleNotFoundError: No module named 'iol_client'`, etc.).
- **Fix:** Ran `uv sync --all-packages --all-extras --dev --frozen` to restore the workspace env,
  and used the equivalent, working form `uv run pytest packages/market-data-client/tests -q` for
  every subsequent gate. No lockfile change; no package installed.
- **Files modified:** none (environment only)
- **Verification:** Full monorepo collection restored; 1314 + 555 tests collected and run.

**2. [Rule 3 - Blocking] Fixed ruff `I001` import ordering in the two shell test files**
- **Found during:** Task 2 (gate run)
- **Issue:** The `from typing import Any` import added for the `_CALENDAR_ENVELOPE` annotation was
  placed after `from pytest_httpx import HTTPXMock`, tripping ruff `I001`.
- **Fix:** `uv run ruff check . --fix`.
- **Files modified:** `tests/test_reference_client.py`, `tests/test_reference_async_client.py`
- **Verification:** `uv run ruff check .` → All checks passed; `ruff format --check .` clean.
- **Committed in:** `f6fe44f` (Task 2 GREEN commit)

### Plan-text imprecision (no code impact)

Task 2's acceptance criterion states that `grep -c 'parse_calendar_response'` should output `1` for
each shell. It actually outputs `2` — because `add_holidays` in **both** shells carries a
pre-existing Phase 26 docstring sentence that *names* `parse_calendar_response` to explain why the
calendar-read parser is deliberately NOT reused for writes (`client.py:667`, `aio.py:679`). The
criterion's intent — one call site per shell, no inline parsing — holds exactly:
`grep -c "_core\.parse_calendar_response("` returns `1` for each. Nothing was changed to satisfy
the literal count; removing correct prose to appease a grep would be worse than the imprecision.

---

**Total deviations:** 2 auto-fixed (both Rule 3 - blocking), 0 architectural.
**Impact on plan:** Both were tooling/lint issues, not design changes. No scope creep; the two
production edits are exactly the two the plan specified.

## Issues Encountered

**Pre-existing, out-of-scope monorepo failures (NOT caused by this plan).** The plan's verification
step 2 (`uv run pytest -q`, full monorepo) ends `19 failed, 1314 passed, 19 errors`. Every failure
is the same matriz driver signature drift, entirely outside this plan's blast radius:

- `verification/test_matriz_sweep_snapshot.py:260` calls `probe_fn()` while
  `main_matriz.probe_get_segments` (and its 16 sibling sweep probes) now require a `client`
  argument → `TypeError: probe_get_segments() missing 1 required positional argument: 'client'`.
- `verification/test_main_matriz_login_fail_uniformity.py:78` fails the same way.

**Confirmed pre-existing at the worktree base SHA** `dd56f21`:
`git show dd56f21:main_matriz.py` already declares `def probe_get_segments(client: Client)` while
`git show dd56f21:verification/test_matriz_sweep_snapshot.py:260` already calls `probe_fn()`.
Per the executor scope boundary these were **not** fixed here — they belong to `main_matriz.py` /
`verification/`, files this plan is explicitly forbidden to touch (and 27-02 must stay parallel-safe
with 27-01). Excluding those two files, the market-data + verification run is **555 passed, 0
failed**.

Recommend routing this to a matriz-scoped fix (or a `/gsd-audit-fix`) before Phase 28 release, since
it means the matriz sweep-snapshot guard is currently not guarding anything.

## Deferred Issues

- `verification/test_matriz_sweep_snapshot.py` + `verification/test_main_matriz_login_fail_uniformity.py`
  — 19 failures / 19 errors from `main_matriz` probe signature drift (probes gained a required
  `client` parameter; the verification callers were never updated). Pre-existing at base SHA,
  unrelated to market-data-client, out of this plan's file scope.

## Gate Results

| Gate | Command | Result |
|------|---------|--------|
| Package suite | `uv run pytest packages/market-data-client/tests -q` | **342 passed** (was 329) |
| Monorepo suite | `uv run pytest -q` | 1314 passed; 19 pre-existing matriz failures (see above) |
| Types | `uv run mypy packages/market-data-client/src` | **Success: no issues found in 11 source files** |
| Lint | `uv run ruff check .` | **All checks passed!** |
| Format | `uv run ruff format --check .` | **193 files already formatted** |

All four acceptance-criteria one-liners from Task 1 and both from Task 2 exit 0.

## Threat Model Compliance

- **T-27-10 (false-negative verification)** — mitigated. `test_parse_calendar_response_unwraps_days_envelope`
  builds its body from the committed baseline shape, so criterion 2 now rests on a real read.
- **T-27-11 (DoS on a degenerate body)** — mitigated. Double collection guard proven by four tests
  (missing `days`, non-list `days`, `null`, scalar) plus the pre-existing 204 test; error statuses
  still raise before decoding.
- **T-27-12 (contract break)** — accepted per D-13, and independently re-verified above (no reader
  of the old fields exists anywhere in the monorepo).
- **T-27-13 (information disclosure)** — mitigated. Every new fixture uses invented values
  (`2099-12-29`, `"GSD phase27 probe"`, `"Ano Nuevo"`); only the **shape** comes from the baseline.
  No credentials, tokens or production payload values entered any test file.
- **T-27-SC (package installs)** — no packages installed; `uv.lock` unchanged (`git status` shows
  only the six planned files).

## Known Stubs

None. No placeholder values, no unwired data paths.

## Threat Flags

None. No new network endpoint, auth path, file access pattern or schema change at a trust boundary
was introduced — the single trust boundary touched (HTTP response → typed model) was hardened, not
widened.

## User Setup Required

None — this plan is fully offline and touches no credentials, env vars or external services.

## Next Phase Readiness

- **Ready for 27-03:** the driver-side unwrap in `main_market_data.py` (`_emit_shape(sample_day,
  CalendarDay, ...)` at `:518` / `:815`) is still fed `raw_days[0]` from the raw envelope, so it
  currently diffs the envelope's `config` sub-dict against the model. That is 27-03's task and was
  deliberately **not** touched here, keeping this plan parallel-safe with 27-01.
- **Ready for 27-04:** the holiday create→verify→revert cycle can now read back what it wrote.
- **For 27-05:** if live evidence ever contradicts the D-13 "nobody could have read it" rationale,
  escalate the major-vs-minor question before Phase 28 rather than at release time. Nothing found
  so far contradicts it.

## Self-Check: PASSED

- `packages/market-data-client/src/market_data_client/models.py` — FOUND
- `packages/market-data-client/src/market_data_client/_core.py` — FOUND
- `packages/market-data-client/tests/test_reference_models.py` — FOUND
- `packages/market-data-client/tests/test_reference_core.py` — FOUND
- `packages/market-data-client/tests/test_reference_client.py` — FOUND
- `packages/market-data-client/tests/test_reference_async_client.py` — FOUND
- Commits `ee83feb`, `831f44f`, `63ad4c6`, `f6fe44f` — all FOUND in `git log`

---
*Phase: 27-verificaci-n-en-vivo-segura-fixes*
*Completed: 2026-08-01*
