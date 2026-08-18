---
phase: 26-calendar-write
reviewed: 2026-07-31T00:00:00Z
depth: deep
files_reviewed: 10
files_reviewed_list:
  - packages/market-data-client/src/market_data_client/__init__.py
  - packages/market-data-client/src/market_data_client/_core.py
  - packages/market-data-client/src/market_data_client/aio.py
  - packages/market-data-client/src/market_data_client/client.py
  - packages/market-data-client/src/market_data_client/models.py
  - packages/market-data-client/tests/test_calendar_write.py
  - packages/market-data-client/tests/test_calendar_write_async.py
  - packages/market-data-client/tests/test_core.py
  - packages/market-data-client/tests/test_models.py
  - packages/market-data-client/tests/test_public_surface_market_data.py
findings:
  critical: 2
  warning: 6
  info: 3
  total: 11
status: issues_found
---

# Phase 26: Code Review Report

**Reviewed:** 2026-07-31
**Depth:** deep
**Files Reviewed:** 10
**Status:** issues_found

## Summary

Phase 26 wires the second mutation surface (calendar write) behind the Phase-25 gate.
The mutating-gate contract (priority 1) holds: `_ensure_mutation_allowed()` is the literal
first statement of all five methods on **both** shells (`client.py:615,629,649,672,694`;
`aio.py:626,640,661,684,706`), and it is a pure state read with no `await` and no transport
touch, so a refusal genuinely leaks nothing. Idempotency assignment (priority 3) is correct —
`build_add_holidays_request` is the only `idempotent=False` builder and the sync no-retry test
is non-vacuous (1 request, 0 sleeps, contrasted against a 3-request idempotent sibling). DELETE
body semantics (priority 4) are correct: both DELETE builders omit `json_body` and the tests
assert `content == b""` plus absent `content-type`. `drop_none`'s predicate is `is not None`
(`_params.py:28`), so falsy-but-present values survive as required (priority 5). The new
`parse_calendar_write_response` correctly keeps the `read() → raise → decode` order and does not
copy `parse_health_response`'s missing guards for the *empty / null / list / scalar* cases.
Sync/async parity (priority 7) is clean for the ten new methods — the only divergence is
`async def` / `await` / docstring language. 287 package tests pass.

**The phase's headline security control does not hold.** The D-18 path-safety guard
(priority 2, ASVS L1, block_on: high) is a four-token substring check that I broke twice under
httpx 0.28.1 — once entirely client-side, with no server cooperation needed. Two BLOCKERs
below carry reproductions. Six WARNINGs cover parser tolerance that the docstring overclaims,
a client-side batch bound that is bypassable after construction, and an async test-parity gap
that leaves the `idempotent=False` contract unverified on the async shell.

## Critical Issues

### CR-01: D-18 guard misses a single `.` — `delete_holiday(".")` retargets the collection endpoint

**File:** `packages/market-data-client/src/market_data_client/_core.py:692,718`
**Issue:** `_PATH_SEGMENT_ESCAPES = ("/", "?", "#", "..")` blocks `..` but not `.`. httpx 0.28.1
applies RFC 3986 `remove_dot_segments` during `build_request`, so a lone `.` does not stay in the
path — it **deletes the whole segment**. Verified end-to-end through the sync `Client` with the
gate open (pytest-httpx capture):

```
delete_holiday(".")   -> raw_path = b'/api/calendar/holidays'      # collection, NOT /holidays/.
delete_holiday("%2e") -> raw_path = b'/api/calendar/holidays/%2e'  # server decodes to the same
```

This is precisely the D-18 threat model the guard was written for — a `day` value that changes
*which* endpoint runs — and it is worse than the `../config` case the guard does block, because
the collapse happens client-side with no server behaviour required. The outgoing request is
`DELETE` against a holidays collection URL; if that route exists server-side it is a mass delete,
and if it does not the client has silently issued a mutation the caller never asked for. The
docstring at `_core.py:711-716` claims the guard "REJECTS rather than sanitizes", and
`build_delete_holiday_request` is the sole enforcement point for both shells, so the miss is
package-wide.

**Fix:** stop enumerating hostile tokens and enforce the actual invariant — a single, safe path
segment — with an allow-list. This also closes CR-02 and the non-str `day` case (WR-04):

```python
import re

# D-18: a ``day`` is a single path segment. Allow-list rather than deny-list —
# an enumeration of escape tokens missed ``.`` (collapses the segment away under
# RFC 3986 dot-segment removal) and every percent-encoded form.
_DAY_SEGMENT_RE = re.compile(r"\A[0-9A-Za-z][0-9A-Za-z:-]*\Z")


def build_delete_holiday_request(state: _ClientState, day: str) -> RequestSpec:
    if not isinstance(day, str) or not _DAY_SEGMENT_RE.fullmatch(day):
        raise ValueError(f"day must be a single path segment, got {day!r}")
    ...
```

Add regression cases for `"."`, `"%2e"`, `".."`, `"%2e%2e%2fconfig"`, `"%2Fconfig"`,
`"config%3Fx=1"`, `"a\\b"`, `" 2026-12-25 "` to the existing
`test_build_delete_holiday_request_rejects_path_escapes` parametrize list, and mirror the `"."`
case into the end-to-end zero-request tests in both `test_calendar_write.py` and
`test_calendar_write_async.py`.

### CR-02: D-18 guard is bypassed by percent-encoded and backslash escapes

**File:** `packages/market-data-client/src/market_data_client/_core.py:692,718`
**Issue:** The guard is a raw substring containment check on the *decoded* caller string. Because
`day` is interpolated raw (by design, D-03) and httpx preserves already-percent-encoded sequences
without double-encoding, every escape token survives in encoded form and reaches the wire.
Verified through the client with the gate open:

```
"%2e%2e%2fconfig" -> raw_path = b'/api/calendar/holidays/%2e%2e%2fconfig'   # decodes to ../config
"%2Fconfig"       -> raw_path = b'/api/calendar/holidays/%2Fconfig'          # decodes to //config
"config%3Fx=1"    -> raw_path = b'/api/calendar/holidays/config%3Fx=1'       # decodes to ?x=1
"2026-12-25%23frag" -> raw_path = b'/api/calendar/holidays/2026-12-25%23frag'  # decodes to #frag
"a\\b"            -> raw_path = b'/api/calendar/holidays/a\\b'               # WHATWG-normalizing
                                                                             # proxies read \ as /
```

Whether these land depends on the server's decode-vs-route ordering — this is the classic
decode-then-normalize traversal, and ASGI servers such as uvicorn `unquote()` the raw path before
the router sees it. The guard's own docstring names itself as the mitigation for this class ("the
server's `422` is NOT a mitigation for this: the request never reaches the endpoint that would
validate it"), so an escape that survives the guard is a control failure, not a residual risk. The
Phase-26 test suite parametrizes only the four literal decoded tokens
(`test_core.py`, `test_build_delete_holiday_request_rejects_path_escapes`), which is why the gap is
invisible to the current gates.

**Fix:** same allow-list as CR-01. A character allow-list rejects `%`, `\`, whitespace and every
encoded escape by construction, and it cannot silently miss a token the way an enumeration does.
Do **not** fix by adding `"%"` and `"\\"` to `_PATH_SEGMENT_ESCAPES` — that is another
enumeration and it still admits unicode/control-character variants.

## Warnings

### WR-01: `parse_calendar_write_response` overclaims tolerance — a malformed 200 body still raises a raw `json.JSONDecodeError`

**File:** `packages/market-data-client/src/market_data_client/_core.py:896-927` (and, for the config
trio, `_core.py:880-893` reached from `client.py:618,632,652` / `aio.py:629,643,664`)
**Issue:** The docstring (`_core.py:906-909`) states the parser degrades "an absent body, a `null`,
a list or a scalar" to `{}` "instead of raising a raw `json.JSONDecodeError`". It does not cover a
body that is present but not JSON — `resp.json()` is called unguarded at line 924. Verified:

```
b'<html>oops</html>' -> RAISES json.decoder.JSONDecodeError
b'   '               -> RAISES json.decoder.JSONDecodeError
```

A 200 carrying an HTML error page (reverse proxy, WAF interstitial, captive gateway) therefore
escapes the `MarketData*` hierarchy that every other failure mode in this package funnels through,
and callers doing `except MarketDataError` will not catch it. The same hole exists in
`parse_calendar_config_response`, which Phase 26 newly routes three write methods through — so
this is a pre-existing defect that Phase 26 took a new dependency on.
**Fix:** wrap the decode, matching the tolerance the docstring already promises:

```python
    if not resp.content:
        return {}
    try:
        raw = resp.json()
    except ValueError:
        return {}
    if not isinstance(raw, dict):
        return {}
    return raw
```

Add `test_parse_calendar_write_response_tolerates_non_json_body` next to the existing tolerance
tests in `test_core.py`. If the config trio should instead surface a typed error, raise
`MarketDataAPIError(resp.status_code, resp.text[:200])` — but pick one and make both parsers agree.

### WR-02: `HolidaysIn` 1-500 bound is bypassable by mutating `days` after construction

**File:** `packages/market-data-client/src/market_data_client/models.py:380-389`
**Issue:** `HolidaysIn` is `frozen=True, slots=True`, but `days: list[HolidayIn]` is a mutable
container and `__post_init__` runs exactly once. `frozen` blocks rebinding the attribute, not
mutating the list it points at. Verified:

```python
h = HolidaysIn([HolidayIn("2026-12-25")])   # passes the 1-500 guard
h.days.extend(...)                          # 601 elements
len(h.to_dict()["days"])                    # -> 601 — guard silently bypassed
```

Same defect in the Phase-25 `NewSymbols` (`models.py:233-242`), which Phase 26 copied the pattern
from. The bound is documented as the client-side cut "before any spec build or HTTP dispatch"
(D-12), so a bypassed bound means a 501-element body reaches the wire and only the server's `422`
stops it — with the caller having been told the bound was enforced locally. The existing boundary
tests (`test_holidays_in_boundary_1_and_500_construct`) only exercise construction, so they cannot
see this.
**Fix:** re-validate at serialization time — the one place the value is actually load-bearing:

```python
    def to_dict(self) -> dict[str, Any]:
        """Serialize to ``{"days": [each element's to_dict()]}`` — pure wrapper (D-11)."""
        if not 1 <= len(self.days) <= 500:
            raise ValueError(f"HolidaysIn requires 1-500 days, got {len(self.days)}")
        return {"days": [d.to_dict() for d in self.days]}
```

Alternatively store `days` as a `tuple` via `object.__setattr__` in `__post_init__`. Mirror
whichever fix into `NewSymbols`.

### WR-03: async test file omits the `idempotent=False` no-retry proof — D-04 is unverified on the async shell

**File:** `packages/market-data-client/tests/test_calendar_write_async.py` (whole file)
**Issue:** `test_calendar_write.py:544-586` carries the no-retry test plus its contrasting positive
control, and the phase names D-04/D-15 as an explicit contract. The async mirror has neither. The
file's own docstring claims to be the mirror of the sync suite and enumerates every other scenario,
so the omission reads as an oversight rather than a decision. `AsyncRetryTransport.handle_async_request`
(`_atransport.py:58`) does gate on `request.extensions["idempotent"]`, so the behaviour is currently
correct — but nothing pins it, and a future edit to the async transport would break the "append is
never retried" guarantee with all gates green. Under the CLAUDE.md dual sync/async constraint, an
untested async half of a duplicated contract is exactly the asymmetry the constraint exists to catch.
**Fix:** port both tests, replacing the `time.sleep` monkeypatch with `asyncio.sleep`:

```python
@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
async def test_add_holidays_not_retried_on_repeated_503(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    sleeps: list[float] = []

    async def _fake_sleep(s: float) -> None:
        sleeps.append(s)

    monkeypatch.setattr(asyncio, "sleep", _fake_sleep)
    _open_gate()
    for _ in range(3):
        httpx_mock.add_response(method="POST", status_code=503)
    with pytest.raises(MarketDataAPIError):
        await aio._get_default().add_holidays(HolidaysIn([HolidayIn("2026-12-25")]))
    assert len(httpx_mock.get_requests()) == 1
    assert sleeps == []
```

Port the `delete_holiday` 3-request positive control alongside it; without the contrast the
single-request assertion cannot distinguish "no retry" from "mock served once".

### WR-04: non-`str` `day` raises `TypeError`, not the guard's `ValueError`

**File:** `packages/market-data-client/src/market_data_client/_core.py:718`
**Issue:** `any(token in day for token in _PATH_SEGMENT_ESCAPES)` requires `day` to support `in`.
`build_delete_holiday_request(state, 20261225)` raises
`TypeError: argument of type 'int' is not iterable` from inside the guard expression. The public
entry points (`Client.delete_holiday`, `AsyncClient.delete_holiday`, and both module-level shims)
are reachable from untyped callers — notebooks, `main_*.py` scripts, JSON-driven config — where
mypy is not in the loop, and a date read from JSON as an int is the obvious way to arrive here. A
`list`/`tuple` argument is worse: `"/" in ["2026-12-25"]` is `False`, so it passes the guard and
interpolates its `repr` into the path. The error also names the failure as a type problem rather
than the path-safety refusal the caller needs to act on.
**Fix:** the `isinstance(day, str)` check in the CR-01 allow-list fix covers this in one line. If
CR-01 is fixed separately, add `if not isinstance(day, str) or not day or any(...)` here.

### WR-05: D-18 guard is not applied to the sibling raw-interpolating mutator `build_update_symbol_request`

**File:** `packages/market-data-client/src/market_data_client/_core.py:435-453` (guard added at
`_core.py:692-719`)
**Issue:** `build_update_symbol_request` interpolates `symbol_id` raw into
`PATCH /symbols/{symbol_id}` with no validation, in the same module and behind the same mutation
gate. Its docstring defers percent-encoding to Phase 27 (D-08 / Pitfall 4), which was reasonable
*before* the threat was characterised — but Phase 26 both proved the threat is real and built the
enforcement primitive (`_PATH_SEGMENT_ESCAPES`) two hundred lines below, and did not apply it. The
result is that the package's mutation surface has one path-parameterised endpoint guarded and one
unguarded, so `update_symbol("../../calendar/config", patch)` still retargets. The asymmetry is not
recorded anywhere in the Phase 26 artifacts I can see, which makes it likely to be lost.
**Fix:** apply the same validation to `symbol_id` (a `symbol_id` like `"DLR/DIC26"` legitimately
contains `/`, so this needs percent-encoding rather than rejection — `urllib.parse.quote(symbol_id,
safe="")`), or, at minimum, record the gap explicitly as a Phase-27 blocker so it is not silently
carried past the milestone.

### WR-06: `MarketHoursIn.to_dict()` silently drops keys the docstring guarantees are always present

**File:** `packages/market-data-client/src/market_data_client/models.py:306-323`
**Issue:** The docstring says "all 7 keys always present (D-10)" and calls the `drop_none` routing
"a no-op because no field is nullable". Both statements are true only under mypy. At runtime the
dataclass performs no coercion, so a `None` on any of the seven fields is dropped by `drop_none`
rather than emitted. Verified:

```python
MarketHoursIn("10:00", "17:00", "TZ", updated_by=None).to_dict()
# -> {'open_time': ..., 'close_time': ..., 'timezone': 'TZ',
#     'pre_open_minutes': 10, 'enabled': True, 'confirm': False}   # updated_by GONE
```

The `confirm` case is the one that matters: `confirm=None` from an untyped caller silently
disappears from the body, and the server then applies its own default for the exact "second
opinion" flag this phase made a model field to force an on-purpose decision (D-09). The
serialization becomes a silent no-op instead of a visible error.
**Fix:** either build the dict directly (the `LatestRequest` / `NewSymbol` precedent — no
`drop_none` where no field is nullable), or, if the `drop_none` routing is kept for symmetry with
`HolidayIn`, drop the "always present" claim from the docstring and add a `__post_init__` that
rejects `None` on the seven non-nullable fields. The current combination of a guarantee in prose
and a dropper in code is the worst of the three.

## Info

### IN-01: unused module constants in both new test files

**File:** `packages/market-data-client/tests/test_calendar_write.py:47-48`,
`packages/market-data-client/tests/test_calendar_write_async.py:28-29`
**Issue:** `_BASE` and `_TOKEN_URL` are defined in both files and referenced nowhere (only
`_CONFTEST_HOST` is used). Ruff does not flag unused module-level assignments, so they will accrete.
**Fix:** delete all four lines.

### IN-02: the zero-request refusal tests cannot distinguish gate-before-build from gate-after-build

**File:** `packages/market-data-client/tests/test_calendar_write.py:413-466`,
`packages/market-data-client/tests/test_calendar_write_async.py:389-442`
**Issue:** The ten refusal tests are genuinely non-vacuous for the *network* half — `token_expires_at=0.0`
with `token` left seeded makes `token_is_fresh()` false, so a missing gate would surface an Auth0
POST in `get_requests()`. But they assert nothing about ordering relative to `_core.build_*`, which
priority 1 states as a separate requirement. Moving the gate below the builder would keep all ten
green. The code is correct today; the test just does not pin that half.
**Fix:** add one ordering test that passes a spec-build-failing argument to a closed gate and asserts
the gate wins, e.g. `delete_holiday("../config")` with the gate OFF must raise
`MarketDataMutationNotAllowedError`, not `ValueError`.

### IN-03: the sync/async parity net checks names only

**File:** `packages/market-data-client/tests/test_public_surface_market_data.py:83-92`
**Issue:** `test_sync_async_method_name_parity` asserts only `callable(getattr(...))`. Signature
drift between the two shells (a kwarg added to one `set_calendar_config` and not the other, or an
`async def` that lost its `async`) passes. Given the file exists specifically because the
cross-package parity nets exclude this package, the check is thinner than its docstring implies.
**Fix:** compare `inspect.signature(...).parameters` between the two classes and assert
`inspect.iscoroutinefunction` on the `AsyncClient` side.

---

_Reviewed: 2026-07-31_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
