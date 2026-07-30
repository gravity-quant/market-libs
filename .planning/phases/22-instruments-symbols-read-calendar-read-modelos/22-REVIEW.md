---
phase: 22-instruments-symbols-read-calendar-read-modelos
reviewed: 2026-07-30T00:00:00Z
depth: deep
files_reviewed: 9
files_reviewed_list:
  - packages/market-data-client/src/market_data_client/models.py
  - packages/market-data-client/src/market_data_client/_core.py
  - packages/market-data-client/src/market_data_client/client.py
  - packages/market-data-client/src/market_data_client/aio.py
  - packages/market-data-client/src/market_data_client/__init__.py
  - packages/market-data-client/tests/test_reference_models.py
  - packages/market-data-client/tests/test_reference_core.py
  - packages/market-data-client/tests/test_reference_client.py
  - packages/market-data-client/tests/test_reference_async_client.py
findings:
  critical: 0
  warning: 1
  info: 2
  total: 3
status: issues_found
---

# Phase 22: Code Review Report

**Reviewed:** 2026-07-30
**Depth:** deep (cross-file, call-chain trace of builder → `_request` → parser → model)
**Files Reviewed:** 9
**Status:** issues_found (advisory — no blockers)

## Summary

Phase 22 adds the reference-data read surface (`instruments`, `instruments/segments`,
`symbols`, `calendar`, `calendar/config`) to `market-data-client`: 5 `SafeModel`
dataclasses, 5 pure builders, 5 pure parsers, 5 sync methods, 5 async methods, 10
module-level shims, and re-exports. I traced every new function against its exact
Phase-21 template (`build_market_data_request` / `parse_market_data_response`), diffed
`client.py` against `aio.py` line-by-line to confirm the mandated sync/async parity, and
verified `drop_none` / falsy-preservation / `params or None` collapsing, the
body-consume-then-raise ordering, the 204/null→`[]` collection guards, and the
`CalendarConfig` single-object + empty-body-tolerant contract (D-07). `ruff check`, `ruff
format --check`, `mypy --strict`, and the full package test suite (134 tests) all pass
against HEAD.

This is a faithful, well-disciplined implementation: naming, `__all__` ordering,
docstrings, and the auth/retry integration all match the plan and existing
conventions exactly. I found no correctness blockers. One real robustness gap is
worth fixing before Phase 23 live verification (it is the exact class of issue that
phase is designed to catch), plus two minor quality/consistency notes.

## Warnings

### WR-01: Collection parsers don't type-guard `raw` before iterating — a non-list 200 response silently misbehaves or crashes

**File:** `packages/market-data-client/src/market_data_client/_core.py:570-632`
(`parse_instruments_response`, `parse_segments_response`, `parse_symbols_response`,
`parse_calendar_response`)

**Issue:** Each of the four collection parsers does:

```python
raw = resp.json()
if raw is None:
    return []
return [Instrument.from_api(item) for item in raw]
```

There is no `isinstance(raw, list)` check. If the live API ever returns a 200 with a
JSON object (`{"data": [...]}`), a scalar, or a string instead of a bare array — a
realistic possibility given every one of these shapes is explicitly marked
PROVISIONAL/unverified against the real develop payloads (A1/A2, reconciled in Phase
23) — the behavior is silently wrong rather than a clean typed error:

- `raw` is a `dict` → `for item in raw` iterates the dict's **keys** (strings), and
  `Instrument.from_api("someKey")` tolerates the non-dict payload by returning an
  all-typed-zero instance for **every top-level key**, silently fabricating N bogus
  rows instead of surfacing the shape mismatch.
- `raw` is an `int`/`float`/`bool` → `for item in raw` raises an unhandled
  `TypeError: 'int' object is not iterable`, which propagates as a raw Python
  `TypeError` instead of the package's `MarketDataAPIError` hierarchy that callers
  are set up to catch.
- `raw` is a `str` → iterates individual characters, again fabricating bogus rows.

This pattern is inherited from the pre-existing `parse_market_data_response` template
(Phase 21, unchanged this phase), but Phase 22 copies the same unguarded pattern into
four *new* functions rather than hardening it once. Given this package's stated core
value (CLAUDE.md: "cada divergencia entre el cliente y el servicio en vivo debe ser
detectada, documentada y corregida"), an unguarded shape assumption is precisely the
kind of defect Phase 23's live-verification cycle exists to catch — but right now a
shape mismatch degrades to silent data corruption (dict case) or an opaque crash (int
case) instead of a clear, catchable, typed error.

**Fix:** Add an explicit type guard before iterating, e.g.:

```python
raw = resp.json()
if raw is None:
    return []
if not isinstance(raw, list):
    raise MarketDataAPIError(resp.status_code, f"expected a JSON array, got {type(raw).__name__}")
return [Instrument.from_api(item) for item in raw]
```

Apply the same guard to `parse_segments_response`, `parse_symbols_response`, and
`parse_calendar_response` (and, ideally, back-port to `parse_market_data_response` /
`parse_latest_response` in a follow-up, since they share the same gap).

## Info

### IN-01: 401 coverage gap for 3 of the 4 collection parsers

**File:** `packages/market-data-client/tests/test_reference_core.py`

**Issue:** The plan's own test-strategy (D-09 / Task 3 `<behavior>`) states "any parser
on a 401 response raises `MarketDataAuthError`" for the reference parsers, but only
`test_parse_instruments_response_401_raises_auth` (line 189) and
`test_parse_calendar_config_response_401_raises_auth` (line 216) exist.
`parse_segments_response`, `parse_symbols_response`, and `parse_calendar_response` have
no equivalent 401 test, even though `test_market_data.py`'s template and this file's own
stated behavior list call for it. The code path is shared (`raise_for_response`), so
this is not a functional bug, but it is a documented-but-unmet acceptance criterion and
leaves a coverage gap if that shared path is ever refactored.

**Fix:** Add the three missing parametrized (or explicit) 401 tests, mirroring
`test_parse_instruments_response_401_raises_auth`:

```python
@pytest.mark.parametrize(
    "parser",
    [_core.parse_segments_response, _core.parse_symbols_response, _core.parse_calendar_response],
)
def test_reference_collection_parsers_401_raise_auth(parser: Any) -> None:
    with pytest.raises(MarketDataAuthError):
        parser(_resp(401))
```

### IN-02: Docstring language split (English `client.py` vs Spanish `aio.py`) carried into the new methods

**File:** `packages/market-data-client/src/market_data_client/client.py:448,465,477,487,493`
vs `packages/market-data-client/src/market_data_client/aio.py:462,479,491,501,507`

**Issue:** The five new sync methods (`get_instruments`, `get_segments`, `get_symbols`,
`get_calendar`, `get_calendar_config`) have English one-line docstrings in `client.py`
while their async mirrors in `aio.py` have Spanish docstrings ("Autenticado ``GET
...``" vs "Authenticated ``GET ...``"). This matches the pre-existing split already
present for `get_market_data`/`get_latest` (not introduced by this phase), so it's not
a regression, but it is a maintainability wrinkle worth flagging since every new
addition perpetuates a two-language surface within the same package. Not
actionable within this phase's scope without a broader docstring-language decision, but
worth a follow-up note (e.g. an ADR picking one language for public docstrings package-wide).

---

_Reviewed: 2026-07-30_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
