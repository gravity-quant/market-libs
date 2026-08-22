---
phase: 30-iol-client-tipado
plan: 08
subsystem: testing
tags: [iol-client, security, redaction, verification-harness, tdd]

# Dependency graph
requires:
  - phase: 30-iol-client-tipado (plan 30-07)
    provides: probe_field_type_map / probe_schema_snapshot raw-wire capture (_capture_raw_wire), the CR-01 sync gap closure this plan's BLOCKER was discovered downstream of
provides:
  - "_capture_raw_wire's except branch redacted to exception class + status code only, never the exception message (which carries the upstream response body)"
  - "First direct regression test for _capture_raw_wire, driven end-to-end through httpx.MockTransport + real _core.raise_for_response"
  - "WR-01/WR-02 test-quality gaps closed: both rewritten tests can now fail on their own subject"
affects: [30-iol-client-tipado, "any future main_*.py driver that renders a caught exception into an append_finding argument"]

# Actuals (#2632)
actuals:
  tokens: 3200
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "getattr(exc, \"status_code\", None) defensive read before rendering an exception into a durable report — never repr(exc), never str(exc)"
    - "httpx.MockTransport injected via Client(http_client=...) + pre-seeded token for offline, credential-free driver-function unit tests"

key-files:
  created: []
  modified:
    - main_iol.py
    - verification/test_main_iol_raw_wire_drift.py

key-decisions:
  - "AD-30-08-01: redact at the emitter (_capture_raw_wire), not at the sink (verification/findings.py) — the emitter still holds the exception object and can name exactly the two safe facts (class, status code) without inspecting an opaque string; a sink-side scrubber would guess at wire-value substrings across six drivers"
  - "WR-02: probe_schema_snapshot's aggregate status assertion changed from == \"PASS\" to != \"FINDING\" — pins only the property this test owns (absence never fabricates a finding), leaves the still-open probe-13 anti-vacuity gap (no capture_fids seeding) fixable instead of cemented"

requirements-completed: [TYP-01]

coverage:
  - id: D1
    description: "A marker planted in an upstream 500 error body never crosses into any append_finding kwarg from _capture_raw_wire's failure path (CR-01 BLOCKER closed)"
    requirement: TYP-01
    verification:
      - kind: unit
        ref: "verification/test_main_iol_raw_wire_drift.py::test_capture_failure_finding_never_carries_the_upstream_response_body"
        status: pass
      - kind: unit
        ref: "verification/test_main_iol_raw_wire_drift.py::test_capture_failure_finding_reports_only_the_exception_type_and_status_code"
        status: pass
    human_judgment: false
  - id: D2
    description: "A transport-level failure with no status_code attribute (httpx.ConnectError) is reported defensively as '<ClassName> status_code=None', never as the exception's own message"
    verification:
      - kind: unit
        ref: "verification/test_main_iol_raw_wire_drift.py::test_capture_failure_without_a_status_code_reports_the_type_and_none"
        status: pass
    human_judgment: false
  - id: D3
    description: "A partial capture failure redacts only the failed endpoints; the successfully captured endpoint is stored verbatim, no marker leaks"
    verification:
      - kind: unit
        ref: "verification/test_main_iol_raw_wire_drift.py::test_a_partial_capture_failure_redacts_only_the_failed_endpoints"
        status: pass
    human_judgment: false
  - id: D4
    description: "The absent-not-null capture contract (failed endpoint absent from dict, one fid per failure) survives the redaction unchanged"
    verification:
      - kind: unit
        ref: "verification/test_main_iol_raw_wire_drift.py::test_capture_failure_leaves_the_endpoint_absent_and_still_returns_its_fid"
        status: pass
    human_judgment: false
  - id: D5
    description: "WR-01: probe_field_type_map's PASS detail names exactly the endpoints inspected, verified against an independently authored expected set (not a comprehension over the input)"
    verification:
      - kind: unit
        ref: "verification/test_main_iol_raw_wire_drift.py::test_probe_field_type_map_pass_detail_names_exactly_the_inspected_endpoints"
        status: pass
    human_judgment: false
  - id: D6
    description: "WR-02: probe_schema_snapshot's absence-vs-null-body distinction no longer pins probe 13's still-open anti-vacuity gap as a permanent invariant"
    verification:
      - kind: unit
        ref: "verification/test_main_iol_raw_wire_drift.py::test_absent_capture_is_still_distinguishable_from_a_null_body"
        status: pass
    human_judgment: false

duration: 50min
completed: 2026-08-22
status: complete
---

# Phase 30 Plan 08: CR-01 marker-leak redaction + WR-01/WR-02 test-quality gaps Summary

**`_capture_raw_wire`'s failure path now reports only the exception's class name and `status_code` (e.g. `IOLAPIError status_code=500`), never `repr(exc)` — closing the BLOCKER where the full upstream error response body (account/instrument identifiers included) was landing verbatim in the git-tracked `iol-client-findings.md` on every capture failure.**

## Performance

- **Duration:** ~50 min (includes a ~14 min full `verification/` regression sweep dominated by pre-existing real-backoff retry tests unrelated to this plan)
- **Tasks:** 3
- **Files modified:** 2 (`main_iol.py`, `verification/test_main_iol_raw_wire_drift.py`)
- **Commits:** 3 task commits (RED → GREEN → WR-01/WR-02 + sweep)

## Accomplishments

- Closed the CR-01 BLOCKER (30-VERIFICATION.md 2026-08-21 / 30-REVIEW.md): `_capture_raw_wire`'s `except` branch no longer renders `repr(exc)` — which carried `resp.text` (the full upstream error body) via `IOLAPIError.__init__` — into any `append_finding` argument. It now binds `status_code = getattr(exc, "status_code", None)` and reports `f"{type(exc).__name__} status_code={status_code!r}"`.
- Gave `_capture_raw_wire` its first direct regression test (5 new cases in a new section 9), driven end-to-end through a real `httpx.MockTransport` + the package's actual `_core.raise_for_response` — not a hand-built exception — so the test proves the leak (and its fix) flow from the real wire path.
- Closed both WARNING-level test-quality gaps from the same verification cycle: WR-01 (a tautological assertion that could never fail on its stated pathology) and WR-02 (a test that cemented a separate, still-open probe-13 defect as a permanent invariant).
- Ran the full sweep specified by the plan (package suite, mypy, ruff, full `verification/` suite) and confirmed the only failures are pre-existing, documented matriz debt with zero overlap with this diff.

## Task Commits

Each task was committed atomically:

1. **Task 1: RED — marker-leak regression cases for `_capture_raw_wire`** - `d37ab79` (test)
2. **Task 2: GREEN — report only the exception class and status code, never the message** - `5a85822` (fix)
3. **Task 3: Close the two WARNING test-quality gaps, then sweep for regressions and scope containment** - `fe44747` (test)

_No plan-metadata commit: `commit_docs: false` was not set, but per this executor's worktree-mode contract, STATE.md/ROADMAP.md updates and the final metadata commit are the orchestrator's responsibility after merge — this SUMMARY.md is committed by the orchestrator's post-merge step, not by this agent._

## Files Created/Modified

- `main_iol.py` — `_capture_raw_wire`'s `except` branch redacted (status_code binding + `actual` f-string); docstring's data-discipline paragraph extended to state the failure-path rule explicitly (T-30-06-01 + T-30-08-01, referencing T-29-36). No other function touched.
- `verification/test_main_iol_raw_wire_drift.py` — new section 9 (5 marker-leak regression tests + `_mock_client` helper + `_WIRE_BODY_MARKER` constant); WR-01 test renamed and rewritten to compare against an independently authored expected set; WR-02 test's `probe_schema_snapshot` half rewritten to an inequality status check + exact-set skipped-list parsing. File grew from 549 to 792 lines (≥620 required).

## Decisions Made

- **AD-30-08-01** (locked in plan frontmatter, executed as specified): redact at the emitter (`_capture_raw_wire`), not at the sink (`verification/findings.py`). The emitter still holds the exception object and can name exactly two safe facts without inspecting an opaque string; a sink-side scrubber would have to guess at wire-value substrings across all six drivers' finding text — a lossy heuristic this plan explicitly rejected.
- **WR-02 status assertion**: `snapshot.status != "FINDING"` instead of `== "PASS"`. The property this test genuinely owns is that a genuinely-absent capture never fabricates a finding; whether the *aggregate* status on total capture failure reads `PASS` or `SKIPPED` is a separate, still-open defect (probe 13 has no `capture_fids` anti-vacuity seeding, unlike probe 12) that this plan explicitly does not fix. The inequality survives both proposed future fixes without blocking either.

## Deviations from Plan

None — plan executed exactly as written. Both auto-fix opportunities that arose during execution were pre-authorized by the plan itself (not discretionary Rule 1/2/3 deviations):

- The venv was missing 5 of 6 workspace packages (`matriz_client`, `ambito_financiero_client`, etc. — `ModuleNotFoundError` on `uv run pytest verification -q`) before the Task 3 sweep could run. Resolved with `uv sync --all-packages --all-extras --dev --frozen`, the exact command CLAUDE.md documents as the standard workspace-install step. Not a code change; no commit.
- Two throwaway background pytest processes launched during investigation of a slow test collided on the IOL token-cache file lock, producing transient false failures in a log I discarded before drawing any conclusion from it (documented under "Issues Encountered" below, not treated as a real regression).

## Issues Encountered

- **Investigated but not a defect:** the `verification/` full-suite sweep took ~14 minutes wall-clock, dominated by `verification/test_with_options.py::test_with_options_max_attempts_extension_honored` — a pre-existing, unmodified test that exercises `tenacity`'s real full-jitter backoff (not mocked sleep) across `max_retries=10` → up to 10 real retries capped at 30s each, for 4 packages. This is expected behavior of code this plan never touches, not a hang.
- **Investigated but not a defect (self-inflicted, resolved):** an early diagnostic run of the same slow test, left running in the background while I started a second full-suite sweep to investigate an apparent F/E pattern, caused genuine transient contention on the IOL client's disk-based token-cache `fcntl.flock`. I killed the orphaned process, confirmed no stray pytest processes remained, and re-ran the sweep cleanly. The final, uncontended sweep result (19 failed, 293 passed, 19 errors) reproduced identically to the contended run, confirming the F/E pattern was real matriz debt, not an artifact of the earlier contention.
- **Pre-existing debt, confirmed unrelated:** the clean `uv run pytest verification -q` sweep reports `19 failed, 293 passed, 19 errors in 828.71s`. All 19 failed + all 19 errored cases are confined to exactly two files: `verification/test_main_matriz_login_fail_uniformity.py` (2 cases) and `verification/test_matriz_sweep_snapshot.py` (17 parametrized cases, `TypeError: probe_get_X() missing 1 required positional argument: 'client'`). Neither file is in this plan's scope boundary, neither touches `iol_client` or `main_iol.py`, and `git log --oneline -- verification/test_matriz_sweep_snapshot.py` shows its last edit was commit `9314e6e` (phase 07, matriz `_core.py` extraction) — long before Phase 15's REFAC-05 driver migration added a `client` parameter to the matriz probe signatures this test never followed. This exact count and cause is already documented in `.planning/PROJECT.md`'s v1.5 Phase 28 close notes: *"pre-existing `verification/test_matriz_sweep_snapshot.py` failures (17-19, phase-07 era, reproduced at pre-phase baseline)"*. Recorded here per the plan's explicit instruction, not fixed (out of scope — this plan's two authorized files are `main_iol.py` and `verification/test_main_iol_raw_wire_drift.py`).

## Verbatim Evidence

### Pre-fix RED output (Task 1, before any production edit)

`uv run pytest verification/test_main_iol_raw_wire_drift.py -v` against the unmodified driver: **22 collected, 18 passed, 4 failed** (tests 1, 2, 3, 5 of section 9; test 4 — absent-not-null contract — passed both ways, as designed).

Test 1's pre-fix failure named the offending kwarg exactly as predicted:
```
assert offenders == [], f"marker filtrado en (índice de llamada, kwarg): {offenders}"
# offenders == [(0, "actual"), (1, "actual"), (2, "actual"), (3, "actual")]
```
Pre-fix `actual[0]` for the API-error case:
```
IOLAPIError('[500] {"cuenta": "ZZ-MARCADOR-DE-CUERPO-DE-WIRE-ZZ-cuenta-999999", "detalle": "boom"}')
```
Pre-fix `actual[0]` for the transport-error case:
```
ConnectError('ZZ-MARCADOR-DE-CUERPO-DE-WIRE-ZZ')
```

### Post-fix redaction transcript (Task 2)

API-error case (4 endpoints, transport answers 500 with the marker embedded):
```
raw_by_endpoint = {}
capture_fids = ['F-01', 'F-02', 'F-03', 'F-04']
actual: IOLAPIError status_code=500 | marker leaked: False   (x4)
```

Transport-error case (`httpx.ConnectError`, no response, no `status_code` attribute):
```
raw_by_endpoint = {}
capture_fids = ['F-05', 'F-06', 'F-07', 'F-08']
actual: ConnectError status_code=None | marker leaked: False   (x4)
```

Partial-failure case (get_quote 200, other three 500): returned dict key set `{"get_quote"}` equal to the clean synthetic body; exactly 3 findings recorded, marker in no kwarg.

### Region gate + positive gate (Task 2 acceptance)

```
$ uv run python -c "import inspect, re, main_iol; print(len(re.findall(r'repr\(', inspect.getsource(main_iol._capture_raw_wire))))"
0
$ uv run python -c "import inspect, main_iol; print(inspect.getsource(main_iol._capture_raw_wire).count('status_code'))"
5
```
(≥3 required — the `getattr` binding, the f-string interpolation, and the docstring's two mentions.)

### TDD REFACTOR gate (Task 2)

Evaluated explicitly after GREEN: the redacted `except` branch is 5 lines with no duplication, no dead code, and no misnamed identifier. No refactor was made — a minimal diff was the goal, and there was no refactor debt to pay.

### WR-01/WR-02 falsifiability perturbations (Task 3)

- **WR-01**: temporarily changed the `solo_get_quote` param's `expected_checked` from `{"get_quote"}` to `{"get_quote", "PERTURBADO"}` → test went RED (`AssertionError: detail='1 endpoints checked (get_quote), no drift' expected_checked={'PERTURBADO', 'get_quote'}`). Reverted; `git diff` after the sweep showed no residue.
- **WR-02**: temporarily changed the skipped-set comparison to `set(skipped_names) == set(tmp_schema_all) | {"PERTURBADO"}` → test went RED (`AssertionError: skipped=[...] tmp_schema_all=[...]` with `'PERTURBADO'` as the extra item). Reverted; `git diff` after the sweep showed no residue.

### Full sweep (Task 3, run in this order)

| Command | Result |
|---|---|
| `uv run pytest verification/test_main_iol_raw_wire_drift.py -v` | 22 passed, 0 failed |
| `uv run pytest verification -q` | 293 passed, 19 failed, 19 errors (all pre-existing matriz debt, see Issues Encountered) |
| `uv run pytest packages/iol-client -q` | 242 passed — matches the 30-05 baseline exactly |
| `uv run mypy packages/iol-client/src packages/iol-client/tests` | `Success: no issues found in 25 source files` |
| `uv run ruff check packages/iol-client main_iol.py verification` | All checks passed |
| `uv run ruff format --check packages/iol-client main_iol.py verification` | 72 files already formatted |
| `git diff --exit-code packages/ .planning/verification/` | exit 0 (both across the whole plan and after each task) |
| `git status --porcelain` (after all 3 commits) | empty — nothing uncommitted |

`grep -c "expected_checked" verification/test_main_iol_raw_wire_drift.py` → `5` (≥5 required).

`probe_schema_snapshot`'s signature after the whole plan:
```
$ uv run python -c "import inspect, main_iol; print(list(inspect.signature(main_iol.probe_schema_snapshot).parameters))"
['client', 'today', 'raw_wire']
```
Unchanged, as required — the probe-13 anti-vacuity fix (`capture_fids` threading) was deliberately not bundled into this plan; it is now unblocked (no longer pinned as an invariant) but still unfixed, offered to the operator as a separate decision.

## Status of `must_haves.prohibitions` (from PLAN.md frontmatter)

| Prohibition | Status | Evidence |
|---|---|---|
| No `append_finding` argument from this driver carries a wire value, the exception message, or a portion of either | **Held** | 5 marker-leak tests pass; region gate = 0 `repr(` occurrences |
| Redaction did not cost diagnosability (status code, ERROR-MAP class, title all retained) | **Held** | `diff=f"type={type(exc).__name__}"`, `class_="ERROR-MAP"`, title unchanged — all asserted in test 2 |
| No change under `packages/` | **Held** | `git diff --exit-code packages/` exits 0 across the whole plan |
| No committed schema baseline or findings artifact touched; tests run against `tmp_path` | **Held** | `git diff --exit-code .planning/verification/` exits 0; `_isolate_state` + `recorded` fixtures repoint/spy as before |
| No credential or `.env` value enters the test | **Held** | `_mock_client` uses dummy `username="u"`/`password="p"` + a pre-seeded token so `_ensure_token` issues no auth request |
| Probe-13 anti-vacuity fix (`capture_fids`) NOT implemented in this plan | **Held** | `probe_schema_snapshot` signature unchanged: `(client, today, raw_wire)` |
| No new test case can pass by construction (every assertion must have a falsifying input) | **Held** | WR-01/WR-02 perturbation evidence above; all 5 new section-9 tests were RED pre-fix by design |

## Carry-forward for the operator

- WR-04 (`verification/` not collected by CI), WR-08 (`DecodeScope` binding inside the capture loop), WR-09 (README version mismatch), WR-10 (stale source reference) all remain open and out of scope for this plan.
- WR-05 (no direct unit test for `_capture_raw_wire`) is incidentally closed by this plan's section 9.
- The probe-13 anti-vacuity gap (`probe_schema_snapshot` takes no `capture_fids`, so a total capture failure could return PASS having verified zero snapshots) remains open. This plan's WR-02 rewrite unblocked it — a future fix is no longer fighting a pinned `== "PASS"` assertion — but did not implement it. Raising this with the operator as a separate decision, per the plan's explicit scope boundary.
- The 19 pre-existing `test_matriz_sweep_snapshot.py` / `test_main_matriz_login_fail_uniformity.py` failures documented above are unchanged debt from Phase 7/15, already tracked in PROJECT.md's v1.5 close notes. No action taken; none is in this plan's authorized file list.

## Next Phase Readiness

- Phase 30's BLOCKER (CR-01) and both WARNING items (WR-01, WR-02) from `30-VERIFICATION.md` / `30-REVIEW.md` are closed.
- No known stubs introduced by this plan.
- No new threat surface introduced beyond what `30-VERIFICATION.md`'s threat model already covered (this plan's own `<threat_model>` in PLAN.md enumerates T-30-08-01 through T-30-08-06, all mitigated or explicitly accepted-with-rationale).

---
*Phase: 30-iol-client-tipado*
*Completed: 2026-08-22*
