---
phase: 30-iol-client-tipado
plan: 09
subsystem: verification-harness
tags: [security, information-disclosure, redaction, regression-lock, ast, tdd, gap-closure]
status: complete
requires:
  - "30-08 (_capture_raw_wire narrow redaction + its 22-case regression suite)"
  - "packages/iol-client/src/iol_client/exceptions.py (IOLDecodeError, T-29-36 wire-free contract)"
provides:
  - "main_iol._redacted_exc — the driver's single sanctioned exception-to-report-text renderer"
  - "verification/test_main_iol_exception_redaction.py — 18-case contract + end-to-end + AST lock"
  - "_raw_exception_renders(source: str) — reusable AST detector for the other five drivers"
affects:
  - "main_iol.py (32 exception-reporting sites)"
  - ".planning/verification/iol-client-findings.md (sink, never written by this plan)"
tech-stack:
  added: []
  patterns:
    - "emitter-side redaction via one named renderer (AD-30-09-01, extends AD-30-08-01)"
    - "AST-over-driver-source regression lock with positive + negative controls"
    - "httpx.MockTransport with a pre-seeded fresh token for offline probe drives"
key-files:
  created:
    - verification/test_main_iol_exception_redaction.py
  modified:
    - main_iol.py
decisions:
  - "AD-30-09-01 re-ratified in code: one named renderer, not 32 inline expressions"
  - "IOLDecodeError exempt from blanket redaction — its four attributes are certified type-only (WR-03)"
  - "Non-integer status_code discarded by isinstance guard, closing WR-06 by construction"
  - "IOL_TOKEN_CACHE_PATH repointed to tmp_path in the autouse fixture (Rule 2 addition)"
metrics:
  duration: ~35min
  completed: 2026-08-22
  tasks: 3
  files: 2
---

# Phase 30 Plan 09: File-wide exception redaction in `main_iol.py` — Summary

File-wide closure of the CR-01 BLOCKER: all 32 exception-reporting sites in `main_iol.py` now
route through a single named renderer that emits an exception's class name plus an
integer-validated status code, so no upstream response body can reach the git-tracked
`.planning/verification/iol-client-findings.md` or the stdout auth-cascade detail.

## What was built

**`main_iol._redacted_exc(exc: BaseException) -> str`** — the driver's only sanctioned
exception-to-report-text renderer, defined immediately after `_as_wire` and before
`_capture_raw_wire`. Two branches:

- `IOLDecodeError` → `IOLDecodeError model=<model> path=<field_path> declared=<declared_type>
  observed=<observed_type>`. The four attributes are certified type-only by `exceptions.py:40-46`
  (T-29-36), so redacting them would trade an information-disclosure defect for an untriageable
  finding (WR-03 / T-30-09-03).
- Everything else → `f"{type(exc).__name__} status_code={status_code!r}"`, where `status_code` is
  the `status_code` attribute only when `isinstance(value, int)` and `None` in every other case —
  absent attribute *or* present-but-not-an-int (WR-06 / T-30-09-04). The `!r` is load-bearing: the
  30-08 suite pins `IOLAPIError status_code=500` and `ConnectError status_code=None` by exact
  equality.

**`verification/test_main_iol_exception_redaction.py`** (new, 527 lines, 18 cases) — helper
contract, end-to-end probe leak cases through `httpx.MockTransport`, and the AST regression lock
with both controls.

## Measured RED state (Task 1) — this plan's own reproduction of the BLOCKER

Against HEAD `ffb2e53`, before any driver change:

- **14 failed / 0 passed**, `--collect-only` exit 0 (clean collection; the RED is run-time, never a
  collection error).
- **9 failures in section 1**, every one `AttributeError: module 'main_iol' has no attribute
  '_redacted_exc'`.
- **5 failures in section 2**, the leaked kwarg was **`actual`** in every single one — reported as
  `[(0, 'actual')]` by `_offending_kwargs` for the transport, login and refresh cases, and as an
  exact-equality mismatch for the 500/401 quote cases (e.g. observed
  `'IOLAPIError(...-mensaje"}\')'` vs expected `'IOLAPIError status_code=500'`). No other kwarg
  (`title`, `expected`, `diff`, `base_url`) ever carried the marker, confirming the planner's audit
  that the remaining arguments are value-free by construction.

## Final gate values (every gate in `<verification>`)

| # | Gate | Value | Baseline |
|---|------|-------|----------|
| 1 | `pytest verification/test_main_iol_exception_redaction.py` | **18 passed**, 0 skipped | new |
| 2 | `pytest verification/test_main_iol_raw_wire_drift.py` | **22 passed** | unchanged |
| 2 | `git diff --exit-code verification/test_main_iol_raw_wire_drift.py` | **exit 0** (byte-identical) | — |
| 3 | `grep -nE 'repr\(exc\)\|str\(exc\)\|\{exc[}!]' main_iol.py` | **0 lines** | was 31 |
| 4 | `grep -c "actual=repr(exc)" main_iol.py` | **0** | was 29 |
| 5 | `grep -c "_redacted_exc(exc)" main_iol.py` | **32** | 29 findings + 2 cascade + 1 capture |
| 5b | `grep -c "^def _redacted_exc(exc: BaseException) -> str:"` | **1** | — |
| 6 | `pytest packages/iol-client -q` | **242 passed** | unchanged |
| 7 | `mypy packages/iol-client/src packages/iol-client/tests` | **Success: no issues found in 25 source files** | unchanged |
| 8 | `ruff check` + `ruff format --check` on `main_iol.py verification` | **clean, 48 files formatted** | — |
| 9 | `git diff --exit-code packages/ .planning/verification/` | **exit 0** | — |
| 10 | `git status --porcelain` | `main_iol.py` modified + new test file added, nothing else | — |
| 11 | Detector non-vacuity | demonstrated, reverted (see below) | — |

The two `_auth_failure_reason` sites are at lines **414** and **449** after the helper's insertion
(were 371 and 406), both reading `f"sync login: {_redacted_exc(exc)}"` /
`f"async login: {_redacted_exc(exc)}"` — the prefixes are verbatim so the 13 downstream SKIPPED
`ProbeResult.detail` strings keep their shape.

## Detector non-vacuity, demonstrated and reverted

`_raw_exception_renders` was temporarily forced to `return []` immediately after `ast.parse`. Result:

```
FAILED test_the_detector_flags_a_synthetic_offending_source
AssertionError: el detector encontró 0: []
```

The negative control stayed green throughout. Reverted immediately from a scratchpad copy; the
committed file contains zero trace of the probe (`grep -c "TEMP non-vacuity probe"` → 0) and the
suite is back at 18 passed.

## Audit of the three `exc`-binding handlers that were already value-free

32 handlers bind `exc`; 29 rendered it raw. **29-of-32 is a complete sweep, not a partial one** —
the other three were audited by reading each and confirmed value-free:

| Line (post-edit) | Handler | Why it is already safe |
|---|---|---|
| 372 | `except Exception as exc:` in `_capture_raw_wire` | The one site 30-08 already closed. It now **delegates** to `_redacted_exc`, and its two output strings are pinned character-for-character by the untouched 30-08 suite. |
| 992 | `except Exception as exc:` in the 6-type sanity loop of `probe_get_instruments_by_type_sync` | Appends `f"{itype}: {type(exc).__name__}"` to a local `bad_types` list. `itype` is one of the six hardcoded `_ALL_INSTRUMENT_TYPES` literals; `type(exc).__name__` is a class name. Nothing from the wire. Not "fixed". |
| 1739 | `except IOLAuthError as exc:` in `probe_auth_401` | Two `append_finding` calls: one with the literal `actual="401"` (the EXPECTED branch), one with `actual=f"status_code={status_code!r}"` where `status_code = exc.status_code` is a typed `int`. Not "fixed". |

## `probe_refresh_token` case status

**GREEN, not skipped.** The plan allowed a justified `pytest.skip` if the refresh path could not be
driven offline without touching `packages/`. It could: a `Client` seeded with `token`, a future
`token_expires_at` and `refresh_token="refresh-de-prueba"` over an `httpx.MockTransport` answering
500 with the marker body reaches the probe's `except IOLAPIError` handler via
`_ensure_token → _refresh → parse_refresh_response → raise_for_response`. Zero skips in the suite.

## Deviations from Plan

### Auto-fixed issues

**1. [Rule 2 — missing critical functionality] `IOL_TOKEN_CACHE_PATH` repointed to `tmp_path`**

- **Found during:** Task 1, while tracing the `probe_refresh_token` and `probe_login_sync` paths.
- **Issue:** `Client.__init__` resolves `token_cache_path` from a `platformdirs` default when
  `IOL_TOKEN_CACHE_PATH` is absent, and both `login()` and `_refresh()` call `_token_cache.save(...)`
  on a successful grant while `_ensure_token` calls `_token_cache.load(...)` and, on a stale
  refresh, `_token_cache.delete(...)`. A test run could therefore have read, overwritten or
  **deleted the operator's real IOL refresh-token cache on disk** — a violation of both T-30-09-06
  and CLAUDE.md's credential-safety constraint, and one not covered by either belt the plan named.
- **Fix:** the autouse `_isolate_state` fixture adds
  `monkeypatch.setenv("IOL_TOKEN_CACHE_PATH", str(tmp_path / "token-cache.json"))`, so every
  `Client` built inside a test resolves its cache into `tmp_path`.
- **Files modified:** `verification/test_main_iol_exception_redaction.py`
- **Commit:** `de56b21`

**2. [Rule 2 — hardening the contract] `IOLRateLimitError` added to the marker-bearing set**

- **Found during:** Task 1. `_core.raise_for_response` raises three classes (`IOLAuthError`,
  `IOLRateLimitError`, `IOLAPIError`), all carrying `resp.text`; the plan's contract cases named
  only two. `IOLRateLimitError(429, body)` was added to both the exact-equality case and the
  parametrized marker case, at no cost.
- **Commit:** `de56b21`

**3. [Rule 1 — bug] TYP-01 was NOT flipped to Complete in `REQUIREMENTS.md`**

- **Found during:** state updates. The standard flow marks the plan's frontmatter `requirements:`
  complete, and `requirements mark-complete TYP-01` did flip the checkbox.
- **Issue:** commit `c7b7340` is literally `docs(phase-30): revert premature Complete requirement
  after gaps found` — the operator had just reverted that same checkbox because the verifier
  reported gaps. This plan closes **one** gap (CR-01 / WR-02 / WR-03); WR-01, WR-04, WR-05, WR-07
  and IN-01..03 remain open, and the phase still owes another verification cycle. Re-flipping it
  would re-create the exact premature state the repo deliberately reverted hours earlier.
- **Fix:** `git checkout -- .planning/REQUIREMENTS.md`. TYP-01 stays `[ ]` until the phase verifier
  returns clean. `REQUIREMENTS.md` is byte-identical to HEAD.

Everything else executed exactly as written. `IOLDecodeError` is deliberately excluded from the
`_marker_bearing_exceptions()` parametrization — all four of its attributes are reported in full by
contract, so planting a marker in one would manufacture a failure by design rather than detect one.
The exclusion is documented in the helper's own docstring, and the class is covered by its own
dedicated case.

## Threat mitigations applied

T-30-09-01 (file-wide finding leak), T-30-09-02 (cascade reason → stdout), T-30-09-03
(over-redaction as a repudiation defect), T-30-09-04 (duck-typed `status_code`), T-30-09-05 (test
fixtures reaching committed artifacts), T-30-09-06 (credentials reaching the transport — see
deviation 1), T-30-09-08 (lock vacuity/noise) are all mitigated and pinned by executable assertions.
T-30-09-07 (`_core.raise_for_response` placing `resp.text` in the exception) remains a documented
`accept`, re-ratified from 30-08: the exception is the consumer's diagnostic surface, and the only
known durable sink for it in this repo is the driver finding path, which this plan closes.

## Threat Flags

None. No new network endpoint, auth path, file-access pattern or schema change at a trust boundary
was introduced — the diff is one private function in a non-published driver script plus one offline
test file.

## Known Stubs

None.

## Carry-forward (restated so it does not get lost)

Deliberately left open, none of them a disclosure of an upstream body, none named by
`30-VERIFICATION.md`'s `gaps:` block:

- **WR-01 — probe-13 anti-vacuity.** `probe_schema_snapshot` takes no `capture_fids`, so a total
  capture failure returns PASS having verified zero snapshots. Separate decision; must be raised
  with the operator rather than folded in.
- **WR-04** — the PASS-detail parser does not assert the numeral.
- **WR-05** — `probe_get_quote_sync` writes a raw `ultimoPrecio` (a public closing price) into a
  durable finding. A scope call for the operator, not a planner.
- **WR-07** — `DecodeScope` binding inside the capture loop.
- **IN-01 / IN-02 / IN-03** — IN-02 was partially absorbed here (the marker is planted in every
  string field of the mock error body).
- **Phase 33 audit: the same pattern in the other five `main_*.py` drivers.** Already on 30-08's
  threat register. `_raw_exception_renders` was deliberately written as a function over a **source
  string** rather than a path, so a future plan can point it at the other drivers **unmodified** —
  only the parametrization over driver filenames needs writing.

## Commits

| Task | Commit | Description |
|---|---|---|
| 1 | `de56b21` | `test(30-09)`: RED — contract + end-to-end leak reproduction (14 failing cases) |
| 2 | `5daeba3` | `feat(30-09)`: `_redacted_exc` + the 32-site sweep |
| 3 | `225488b` | `test(30-09)`: AST regression lock with positive and negative controls |

## Self-Check: PASSED

- `main_iol.py` — FOUND (modified, committed in `5daeba3`)
- `verification/test_main_iol_exception_redaction.py` — FOUND (created in `de56b21`, extended in `225488b`)
- `.planning/phases/30-iol-client-tipado/30-09-SUMMARY.md` — FOUND
- Commit `de56b21` — FOUND
- Commit `5daeba3` — FOUND
- Commit `225488b` — FOUND

## TDD Gate Compliance

Plan tasks 1 and 2 carried `tdd="true"` and the gate sequence is intact in git history: `test(30-09)`
RED (`de56b21`, 14 failing cases, measured and recorded) → `feat(30-09)` GREEN (`5daeba3`, all 14
passing, sibling suite still 22) → no REFACTOR commit was needed (the sweep was mechanical and
`ruff format` reported the file already formatted). Task 3's lock is additive test surface and
carried no `tdd` attribute; its non-vacuity was demonstrated empirically instead.
