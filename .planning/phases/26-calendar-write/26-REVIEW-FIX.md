---
phase: 26-calendar-write
fixed_at: 2026-07-31T00:00:00Z
review_path: .planning/phases/26-calendar-write/26-REVIEW.md
iteration: 1
scope: scoped (operator-selected: CR-01, CR-02, WR-04)
findings_in_scope: 3
fixed: 3
skipped: 0
deferred_to_phase_27: 8
status: all_fixed
---

# Phase 26: Code Review Fix Report (scoped)

**Fixed at:** 2026-07-31
**Source review:** `.planning/phases/26-calendar-write/26-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 3 (CR-01, CR-02, WR-04 — the D-18 path-safety guard)
- Fixed: 3
- Skipped: 0
- Deliberately left open (carried to Phase 27): 8

## What changed

One root cause, one fix. All three in-scope findings were symptoms of the same
design error: `_PATH_SEGMENT_ESCAPES = ("/", "?", "#", "..")` was a **deny-list
enumeration** of hostile tokens, checked by substring containment against the
caller's decoded string. An enumeration is only as good as the reviewer's
imagination, and this one missed three whole classes.

`packages/market-data-client/src/market_data_client/_core.py` — the deny-list is
replaced by a **charset allow-list** plus an all-dots rejection:

```python
_DAY_SEGMENT_RE = re.compile(r"\A[A-Za-z0-9._~-]+\Z")

if not isinstance(day, str) or not _DAY_SEGMENT_RE.fullmatch(day) or day.strip(".") == "":
    raise ValueError(f"day must be a single path segment, got {day!r}")
```

The charset is RFC 3986 `unreserved` — exactly the characters that need no
encoding to travel a path segment. `%` is excluded because it is the
percent-encoding introducer (CR-02), `\` because WHATWG-normalizing proxies read
it as `/`, and everything outside the set (whitespace, control and unicode
characters) falls out by construction rather than by enumeration.

Per finding:

- **CR-01** (`.` retargets the collection endpoint) — closed by the
  `day.strip(".") == ""` clause. `.` and `..` are legal `unreserved` characters,
  so the charset alone would admit them; an all-dots segment is never a day, and
  httpx 0.28.1 applies RFC 3986 dot-segment removal at `build_request`, which
  **deletes** the segment and collapses the request onto
  `DELETE /api/calendar/holidays` — the COLLECTION endpoint.
- **CR-02** (percent-encoded escapes) — closed by `%` being outside the charset.
  No sanitization was added: the guard still rejects, and `_core.py` still
  contains no `urllib.parse.quote()` anywhere.
- **WR-04** (non-`str` `day`) — closed by the leading `isinstance(day, str)`
  check, which short-circuits before any operation that could raise `TypeError`.
  A `list` no longer passes the guard and interpolates its `repr`.

The `build_delete_holiday_request` docstring was rewritten so it describes what
the guard actually blocks — the old text named itself as the mitigation for the
traversal class it failed to block, which was itself part of the finding.

### Invariants preserved (verified, not assumed)

| Invariant | Evidence |
|---|---|
| **D-03** — legit ISO date rides the wire byte-for-byte, unencoded | `test_build_delete_holiday_request_passes_legit_day_byte_for_byte` asserts `path == f"/calendar/holidays/{day}"` and `"%" not in path` |
| **D-13** — no client-side scalar/format validation | `"2026-13-45"` still builds a spec and goes to the server's `422`; `%` is excluded as the encoding introducer, not for date shape |
| **D-12** — plain `ValueError`, not the `MarketData*` hierarchy | `test_build_delete_holiday_request_guard_raises_plain_value_error` (unchanged, still green) |
| Guard rejects, never sanitizes | no `quote()` / percent-encoding introduced in `_core.py` |
| Message leaks no credentials or client state | `test_build_delete_holiday_request_guard_message_leaks_no_state` (unchanged, still green) |
| `__version__` untouched at `"0.3.1"` | release bump remains Phase 28 |

## Verification evidence

**Non-vacuity of the new tests.** Every vector was run through the old predicate
and the new one. 8 vectors flipped from *reaching the wire* to *blocked*; the
rest were already blocked and stay blocked:

```
'.'                  new=blocked  old=PASSED-WIRE   <- CR-01
'%2e'                new=blocked  old=PASSED-WIRE   <- CR-02
'%2e%2e%2fconfig'    new=blocked  old=PASSED-WIRE   <- CR-02
'%2Fconfig'          new=blocked  old=PASSED-WIRE   <- CR-02
'config%3Fx=1'       new=blocked  old=PASSED-WIRE   <- CR-02
'2026-12-25%23frag'  new=blocked  old=PASSED-WIRE   <- CR-02
'a\b'                new=blocked  old=PASSED-WIRE   <- CR-02
['2026-12-25']       new=blocked  old=PASSED-WIRE   <- WR-04
'..' '' '../config' '2026-12-25?x=1' 'a/b' None      already blocked, still blocked
20261225 (int)       new=blocked  old=TypeError     <- WR-04
```

**Tests added:**
- `tests/test_core.py` — the `rejects_path_escapes` parametrize list grew from 5
  to 19 vectors (adds `.`, `..`, `...`, five percent-encoded forms, backslash,
  and three whitespace/control forms); new
  `test_build_delete_holiday_request_rejects_non_str_day` (6 non-`str` types);
  new `test_build_delete_holiday_request_passes_legit_day_byte_for_byte`.
- `tests/test_calendar_write.py` and `tests/test_calendar_write_async.py` — the
  end-to-end proof on **both** shells with the gate OPEN: `delete_holiday(".")`
  raises `ValueError` **and** `httpx_mock.get_requests() == []`. Asserting only
  the exception would not have caught CR-01, since the whole point is that the
  collapsed request never reaches the wire. Same zero-request assertion for the
  8 encoded-escape vectors and the 3 non-`str` vectors.

All `pytest.raises(ValueError, ...)` carry `match="single path segment"` (ruff
`PT011`), which also pins the refusal to the path-safety guard rather than to any
incidental `ValueError`.

**All 4 gates green:**

```
uv run ruff check .                        -> All checks passed!
uv run ruff format --check .               -> 193 files already formatted
uv run mypy packages/market-data-client/src -> Success: no issues found in 11 source files
uv run --package market-data-client pytest packages/market-data-client/tests -q
                                           -> 329 passed  (baseline 287, +42 new)
```

## Deliberately left open — carried to Phase 27

The operator scoped this fix to the three D-18 findings. The remaining 8 findings
from `26-REVIEW.md` were **not** touched and remain open:

| ID | Title | Note |
|---|---|---|
| WR-01 | `parse_calendar_write_response` overclaims tolerance — a non-JSON 200 body raises raw `json.JSONDecodeError` | pre-existing in `parse_calendar_config_response`; Phase 26 took a new dependency on it |
| WR-02 | `HolidaysIn` 1–500 bound bypassable by mutating `days` after construction | same defect in Phase-25 `NewSymbols`; fix must be mirrored |
| WR-03 | async file omits the `idempotent=False` no-retry proof — D-04 unverified on the async shell | behaviour is correct today, just unpinned |
| WR-04 | *(fixed — in scope)* | — |
| WR-05 | D-18 guard not applied to `build_update_symbol_request` | **needs percent-encoding, not rejection**: a legit `symbol_id` like `"DLR/DIC26"` contains `/`. Explicitly recorded here as a Phase-27 blocker so the asymmetry is not lost past the milestone |
| WR-06 | `MarketHoursIn.to_dict()` drops keys the docstring guarantees | the `confirm=None` case is the one that matters |
| IN-01 | unused `_BASE` / `_TOKEN_URL` in both new test files | |
| IN-02 | refusal tests cannot distinguish gate-before-build from gate-after-build | |
| IN-03 | sync/async parity net checks names only | |

**WR-05 is the notable carry.** The package's mutation surface now has one
path-parameterised endpoint guarded (`delete_holiday`) and one unguarded
(`update_symbol`), so `update_symbol("../../calendar/config", patch)` still
retargets. It could not be folded into this fix because the correct remedy is the
opposite one — `urllib.parse.quote(symbol_id, safe="")` rather than rejection —
and that is a wire-shape change outside this scoped fix.

---

_Fixed: 2026-07-31_
_Fixer: Claude (gsd-code-fixer, scoped)_
_Iteration: 1_
