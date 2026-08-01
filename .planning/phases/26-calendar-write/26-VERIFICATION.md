---
phase: 26-calendar-write
verified: 2026-07-31T00:00:00Z
status: passed
score: 5/5 must-haves verified
behavior_unverified: 0
overrides_applied: 0
deferred:
  - truth: "WR-01: parse_calendar_write_response / parse_calendar_config_response raise a raw json.JSONDecodeError on a non-JSON 200 body (e.g. an HTML error page), escaping the MarketData* hierarchy"
    addressed_in: "Phase 27"
    evidence: "Phase 27 SC#4: 'Toda divergencia (shape de respuesta, códigos, idempotencia real) se documenta en findings y se corrige in-cycle' — recorded in 26-REVIEW-FIX.md 'Deliberately left open' table"
  - truth: "WR-02: HolidaysIn's 1-500 client-side bound is bypassable by mutating .days after construction (frozen blocks rebinding, not list mutation)"
    addressed_in: "Phase 27"
    evidence: "Same defect pattern flagged for the Phase-25 NewSymbols precedent; carried explicitly in 26-REVIEW-FIX.md, matches Phase 27 SC#4 divergence-fix scope"
  - truth: "WR-03: the async test file (test_calendar_write_async.py) omits the idempotent=False no-retry dispatch-level test — D-04/D-15 unverified on the async shell (AsyncRetryTransport behaviour confirmed correct by code reading only, not pinned by a test)"
    addressed_in: "Phase 27"
    evidence: "26-REVIEW-FIX.md 'Deliberately left open' table; Phase 27 SC#3 explicitly revalidates per-endpoint idempotency against live behaviour"
  - truth: "WR-05: the D-18 path-safety allow-list guard is not applied to the sibling raw-interpolating mutator build_update_symbol_request (symbol_id) — one path-parameterised mutation endpoint guarded, one not"
    addressed_in: "Phase 27"
    evidence: "26-REVIEW-FIX.md names this explicitly as 'the notable carry... recorded here as a Phase-27 blocker so the asymmetry is not lost past the milestone'"
  - truth: "WR-06: MarketHoursIn.to_dict() silently drops a field (including confirm) when a caller passes None for a non-nullable field, contradicting the docstring's 'always present' claim"
    addressed_in: "Phase 27"
    evidence: "26-REVIEW-FIX.md 'Deliberately left open' table; Phase 27 SC#4 divergence-fix scope"
  - truth: "IN-01/IN-02/IN-03: unused test constants, refusal tests don't pin gate-before-build ordering, sync/async parity net checks names only (not signatures)"
    addressed_in: "Phase 27"
    evidence: "26-REVIEW-FIX.md 'Deliberately left open' table (INFO-severity, non-blocking)"
---

# Phase 26: Calendar write Verification Report

**Phase Goal:** El consumidor puede administrar la configuración de calendario y los feriados
detrás del mismo mutating-gate, con el guardrail `confirm` del servidor expuesto explícitamente.
**Verified:** 2026-07-31
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | SC#1 — Behind the gate, consumer can `set_calendar_config`/`delete_calendar_config`/`preview_calendar_config`/`add_holidays`/`delete_holiday(day)` in sync AND async | ✓ VERIFIED | All 5 methods exist on `Client` (`client.py:594,620,634,654,677`) and `AsyncClient` (`aio.py:605,631,645,666,689`) with matching `PUT`/`DELETE`/`POST`/`POST`/`DELETE` semantics; 329 package tests pass including dispatch tests that assert exact method/URL/Bearer/body over `httpx_mock` |
| 2 | SC#2 — `set_calendar_config` exposes `confirm` with default `False` and honors rest of `MarketHoursIn` defaults | ✓ VERIFIED | Live-executed: `MarketHoursIn("10:00","17:00","America/Argentina/Buenos_Aires").to_dict() == {"open_time":"10:00","close_time":"17:00","timezone":"...","pre_open_minutes":10,"enabled":True,"updated_by":"","confirm":False}` — exact match confirmed by direct interpreter run |
| 3 | SC#3 — Request models serialize via `_params.drop_none`; `preview` passes gate (POST) but does not persist, exception documented | ✓ VERIFIED | Live-executed: `HolidayIn("2026-12-25").to_dict() == {"day":"2026-12-25","closed":True,"description":""}` (hours dropped). `preview_calendar_config` docstring (`client.py:634-648`, `aio.py:645-660`) explicitly documents the read-safe/no-carve-out exception; gate call confirmed as first statement, identical to persisting methods |
| 4 | SC#4 — Per-endpoint idempotency per DM-03; `POST /calendar/holidays` idempotent=False → no retry, rest retry-safe | ✓ VERIFIED | Builder specs confirmed: 4×`idempotent=True`, 1×`idempotent=False` (`build_add_holidays_request`). Behavioral test `test_add_holidays_not_retried_on_repeated_503` run individually — PASSED (1 request, 0 sleeps against repeated 503), contrasted against 3-request idempotent-sibling positive control |
| 5 | SC#5 — Sync/async parity + gate enforcement identical to Phase 25; mocked tests (gate, serialization, defaults, confirm, 422, parity) + 4 green gates | ✓ VERIFIED | `_ensure_mutation_allowed()` confirmed as literal first statement in all 10 method bodies (5×2 shells) by direct source read; 8 new names confirmed in `__init__.__all__` and importable; all 4 gates re-run and green (see below) |

**Score:** 5/5 truths verified (0 present-but-behavior-unverified)

### Deferred Items

8 review findings from `26-REVIEW.md` were deliberately left open per operator scoping decision
(`26-REVIEW-FIX.md`, iteration 1: scope = CR-01/CR-02/WR-04 only). Verified these are genuinely
still present in the code (not silently fixed, not silently regressed) and correctly recorded as
carries to Phase 27 (whose SC#3/SC#4 explicitly cover live idempotency revalidation and
divergence-fix-in-cycle). See YAML frontmatter `deferred:` list for the 6 grouped items
(WR-01, WR-02, WR-03, WR-05, WR-06, IN-01/02/03).

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `packages/market-data-client/src/market_data_client/models.py` | `MarketHoursIn`, `HolidayIn`, `HolidaysIn` frozen dataclasses, NOT `SafeModel` subclasses | ✓ VERIFIED | Present at lines 274/327/368, all `@dataclass(frozen=True, slots=True)`, no base class; `to_dict()` routes through `_params.drop_none` (load-bearing for `HolidayIn`, no-op for `MarketHoursIn`) |
| `packages/market-data-client/src/market_data_client/_core.py` | 5 builders + `parse_calendar_write_response`, D-18 guard | ✓ VERIFIED | All 5 builders present with correct method/path/idempotent/endpoint_name; D-18 guard is a charset allow-list (`_DAY_SEGMENT_RE`) + all-dots rejection, confirmed to reject `.`/`..`/`%2e`/`%2Fconfig`/`a/b`/`2026-12-25?x=1`/newline-suffixed/non-str inputs, and pass `2026-12-25` byte-for-byte and `2026-13-45` through to server 422 |
| `packages/market-data-client/src/market_data_client/client.py` | 5 gated sync methods + 5 shims | ✓ VERIFIED | Lines 594-697 (methods) + 900-924 (shims); `_ensure_mutation_allowed()` is literal first statement in all 5 |
| `packages/market-data-client/src/market_data_client/aio.py` | 5 gated async methods + 5 shims, mirroring client.py | ✓ VERIFIED | Lines 605-709 (methods) + 910-934 (shims); identical gate-first ordering, `await self._request(spec)`, gate call NOT awaited |
| `packages/market-data-client/src/market_data_client/__init__.py` | 8 new names re-exported, `__version__` unchanged | ✓ VERIFIED | All 8 names (`HolidayIn`, `HolidaysIn`, `MarketHoursIn`, `add_holidays`, `delete_calendar_config`, `delete_holiday`, `preview_calendar_config`, `set_calendar_config`) present in import blocks and `__all__`; `__version__ == "0.3.1"` (bump correctly deferred to Phase 28) |
| `packages/market-data-client/tests/test_calendar_write.py` + `_async.py` | Dispatch, adversarial-gate, D-18 end-to-end, D-15 no-retry (sync only) tests | ✓ VERIFIED (sync), gap noted (async no-retry, deferred WR-03) | 329 total package tests pass; named no-retry test independently re-run and passed |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `models.py` | `_params.py` | `to_dict()` routes through `_params.drop_none` | ✓ WIRED | Confirmed by direct execution: `HolidayIn` hours dropped when `None`, `closed`/`description` falsy-but-present survive |
| `client.py`/`aio.py` | `_core.py` builders | Each method calls its builder, dispatches via `self._request`/`await self._request`, parses response | ✓ WIRED | Confirmed by source read for all 5 methods × 2 shells |
| `client.py`/`aio.py` methods | `_ensure_mutation_allowed()` | Gate as literal first statement | ✓ WIRED | Confirmed for all 10 method bodies; no `_core.build_*`/`self._request`/`_ensure_token` call precedes it |
| `build_add_holidays_request` | `_transport.py` `RetryTransport` | `spec.idempotent=False` short-circuits retry loop | ✓ WIRED | Behavioral test (single named test, re-run) confirms exactly 1 request against repeated 503, 0 sleeps, vs. 3-request idempotent-sibling control |
| `__init__.py` | `client.py`/`models.py` | Re-export of 8 new names | ✓ WIRED | Confirmed importable + present in `__all__`, `list(__all__) == sorted(__all__)` |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| D-18 guard rejects all hostile `day` vectors from verification_context | Direct Python execution of the guard regex against `.`, `..`, `%2e`, `%2Fconfig`, `a/b`, `2026-12-25?x=1`, `\n`-suffixed, non-str `123`/`['x']` | All 8 raised `ValueError`; legit `2026-12-25` and format-invalid-but-server-validated `2026-13-45` both passed | ✓ PASS |
| D-18 no `urllib.parse.quote` anywhere in `_core.py` | `grep -n urllib _core.py` | No matches | ✓ PASS |
| D-15 add_holidays no-retry (behavior-dependent truth) | `pytest -k test_add_holidays_not_retried_on_repeated_503` (single named test) | 1 passed | ✓ PASS |
| MarketHoursIn.to_dict() SC#2 exact-dict assertion | Direct Python execution | Matches expected 7-key dict with `confirm: False` | ✓ PASS |
| HolidayIn.to_dict() SC#3 drop_none effect | Direct Python execution | Matches `{"day":...,"closed":True,"description":""}`, hours absent | ✓ PASS |
| Full package test suite | `uv run --package market-data-client pytest packages/market-data-client/tests -q` | 329 passed | ✓ PASS |
| Full monorepo package suite (excludes live-API `verification/`) | `uv run pytest packages -q` | 1083 passed, 1 deselected | ✓ PASS |
| Root `tests/` suite | `uv run pytest tests -q` | 2 passed | ✓ PASS |
| Lint | `uv run ruff check .` | All checks passed! | ✓ PASS |
| Format | `uv run ruff format --check .` | 193 files already formatted | ✓ PASS |
| Typecheck (explicit target, per X6 — root mypy excludes this package) | `uv run mypy packages/market-data-client/src` | Success: no issues found in 11 source files | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| MUT-MD-02 | 26-01, 26-02, 26-03, 26-04 (all four) | Consumer can administer calendar — PUT/DELETE/POST-preview config + POST/DELETE holidays, typed request models, sync+async, behind mutating-gate | ✓ SATISFIED | All 5 endpoints implemented, gated, tested, exported; REQUIREMENTS.md line 63 marks `MUT-MD-02 | Phase 26 | Complete` — confirmed consistent with actual codebase state (not just the doc claim) |

No orphaned requirements found — `grep "Phase 26" .planning/REQUIREMENTS.md` returns only the single `MUT-MD-02` row, matching the `requirements: [MUT-MD-02]` frontmatter declared identically across all 4 plans.

### Anti-Patterns Found

None. Scanned all 5 source files + 5 test files modified/created by this phase for
`TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER`/"not yet implemented"/"coming soon" — zero matches.
No stub return patterns (`return null`, `return {}`, empty handlers) in the new methods — all 5
dispatch through the real builder → transport → parser chain.

**Security review of the phase's headline control (D-18):** the original guard shipped in Plan 02
was a 4-token deny-list enumeration and was independently broken twice by the code reviewer
(CR-01: a lone `.` collapses the path via RFC 3986 dot-segment removal, retargeting to the
holidays *collection* endpoint; CR-02: percent-encoded escapes survive raw interpolation).
The operator scoped a fix (commits `a0d0ed6`, `c431aea`) that replaced the enumeration with an
RFC-3986-`unreserved` charset allow-list plus an all-dots rejection. I independently re-derived
and executed this guard's logic against every hostile vector named in both `26-REVIEW.md`'s
reproductions and this task's `verification_context` — all are rejected, and the two invariants
the fix had to preserve without regressing (D-03 byte-for-byte passthrough for legit dates, D-13
no client-side format validation) both hold under direct execution.

### Human Verification Required

None. This phase is pure backend library code (dataclasses, pure builders, gated dispatch
methods) with no UI, no real-time behavior, and no external-service dependency that isn't
already covered by mocked tests. Live-API confirmation of the five `200` response shapes,
real per-endpoint idempotency, and `HH:MM` vs `HH:MM:SS` acceptance are explicitly Phase 27
scope (LIVE-MUT-01), not this phase's.

### Gaps Summary

No gaps block the Phase 26 goal. All 5 ROADMAP success criteria are verified against the actual
codebase (not SUMMARY.md claims) via direct source reading, live interpreter execution of the
serialization and path-safety logic, and independent re-execution of the full test suite plus one
named behavior-dependent test. The phase's one prior security-control failure (D-18 deny-list
enumeration missing `.` and percent-encoding, CR-01/CR-02, both independently reproduced by the
code reviewer) was fixed with a charset allow-list and independently re-verified here against
every hostile vector in scope. 8 lower-severity findings (WR-01/02/03/05/06, IN-01/02/03) were
deliberately left open by explicit operator scoping decision and are correctly recorded in
`26-REVIEW-FIX.md` as carries to Phase 27 — confirmed still present (not silently fixed, not
silently regressed) and listed as `deferred` items above rather than gaps, per Phase 27's SC#3/#4
which explicitly cover live idempotency revalidation and in-cycle divergence fixes.

---

_Verified: 2026-07-31_
_Verifier: Claude (gsd-verifier)_
