---
phase: 29-decoder-observable
fixed_at: 2026-08-19T00:00:00Z
review_path: .planning/phases/29-decoder-observable/29-REVIEW.md
iteration: 1
findings_in_scope: 11
fixed: 10
skipped: 1
status: partial
---

# Phase 29: Code Review Fix Report

**Fixed at:** 2026-08-19
**Source review:** `.planning/phases/29-decoder-observable/29-REVIEW.md`
**Iteration:** 1
**Scope:** Critical + Warning (`critical_warning`)

**Summary:**
- Findings in scope: 11 (4 Critical, 7 Warning)
- Fixed: 10
- Deferred (design decision, needs operator input): 1 (WR-04)

**Gate results after all fixes:**

```
uv run pytest packages/higyrus-client packages/matriz-client packages/market-data-client \
              packages/iol-client packages/ambito-financiero-client -q --no-cov
→ 1531 passed, 1 deselected in 92.49s          (baseline before the fixes: 1469 passed)

uv run python tools/check_decode_intactness.py → exit 0
  Check A  5 copies of `_decode.py` → one normalized hash ac14868282ad0a5c, matching CANONICAL_DIGEST
  Check B  5 marker-delimited scan regions (54 lines each) → one hash 684191c7cdc5ff9c
  Check C  `strict=False` (in `_decode.py`), `msgspec.field(` absent from 67 package source files
  Check D  5 in-scope packages carry a `_decode.py`; `wallets-client` exempt

uv run ruff check .        → All checks passed
uv run ruff format --check → 215 files already formatted
uv run mypy                → Success: no issues found in 55 source files
uv run mypy packages/<pkg>/tests → unchanged from baseline for all five packages
```

The canonical `_decode.py` body changed four times over these fixes; every change was
applied to **all five copies** and `CANONICAL_DIGEST` in `tools/check_decode_intactness.py`
was bumped with it. The digest pin is itself one of the fixes (WR-07), so the last three
commits both consume and maintain it.

---

## Fixed Issues

### CR-01: Stale request scope silences every decode not initiated by `_request`

**Files modified:** all five `_decode.py`; `higyrus_client/_core.py`,
`market_data_client/_core.py`, `matriz_client/_core.py`, `matriz_client/ws_client.py`;
all five `tests/test_decode.py`; `29-AGGREGATION-CONTRACT.md`
**Commit:** `f3484c7`
**Status:** fixed

**Applied fix (adapted from the suggestion):** the review proposed a
`take_request_scope()` consumed once per `Model.from_api`. That breaks lock 5 — a
top-level `list[Model]` parse is N sibling `from_api` calls, so element 2 onward would
each get a fresh scope and a 5,000-row catalogue read would emit 5,000 records instead
of one. It also breaks pre-existing tests that drive `open_request_scope()` then decode
repeatedly.

The lifetime is closed at the other end instead, where "one HTTP response" actually
ends — **the parse owns the scope and retires it on the way out**:

- `DecodeScope` gains `closed` (and a `_holds` re-entrancy counter).
- `_decode._response_scope()` adopts the scope `_request` bound, creating one if none is
  bound or the bound one is retired, and sets `closed = True` on exit. Re-entrant, so a
  parser delegating to another parser retires it once.
- `_decode._response_parser` is the decorator form, applied to every `_core` parser that
  builds models: higyrus ×1, market-data ×7, matriz ×20, plus `ws_client._parse_frame`.
  Applying it at the **parser** rather than per `from_api` call is what keeps every
  element of a top-level `list[Model]` parse inside one scope.
- `current_sink()` treats a retired scope as no scope, which brings lock 6's own
  "fresh per-call scope" fallback back to life.

The `_request` bind is unchanged, so both invariants that depend on it still hold (the
scope bound during `_request` is the same object after it returns; each request binds a
distinct one) and no pre-existing test needed editing.

Verified by direct execution against the fixed code: two consecutive standalone
`Posicion.from_api(payload)` calls after a simulated response parse now report 21
records each (previously 21 then 0), while the same two calls **inside** one parse still
collapse to 21 then 0.

Lock 6 amended in `29-AGGREGATION-CONTRACT.md` to record the retirement mechanism.

---

### CR-02: Strict mode is bypassed on any re-decode within one scope

**Files modified:** all five `_decode.py`; all five `tests/test_decode.py`
**Commit:** `b9c0048`
**Status:** fixed — **requires human verification** (logic change to the dedupe/strict
disposition, verifiable only by reading the new ordering)

**Applied fix:** exactly the suggestion. `DecodeScope.__call__` now computes `strict`
first, adds the triple to `_seen` **only when not raising**, emits, and raises last. A
caught-and-retried decode of the same divergence inside one scope therefore raises again
instead of taking the "already reported" branch, and a strict run leaves the record on
the paquete logger (`_emit` never raises, lock 9, so it cannot mask the disposition).

New per-package test
`test_strict_mode_raises_on_every_visit_of_one_divergence_in_one_scope` decodes the same
divergent payload twice through one scope under strict mode and asserts two raises and
two records.

---

### CR-03: `MarketDataSnapshot.market_data` silently decodes to `None`

**Files modified:** `market_data_client/models.py`, `matriz_client/models.py`,
`market-data-client/tests/test_decode.py`, `market-data-client/tests/test_models.py`,
`29-SEMANTICS-MATRIX.md`
**Commit:** `9711806`
**Status:** fixed — **requires human verification** (see the behaviour note below)

**Applied fix:** matriz's call-site mapping pass (`_mapping_value` /
`_apply_mapping_policy`) ported **verbatim** into `market_data_client.models`, applied in
both `SafeModel.from_api` and `MarketDataSnapshot.from_api`, with `SILENT_SINK` under a
non-dict payload so lock 8's terminal `non_dict` stays terminal. `_decode.py` untouched.

Also corrected matriz's `_mapping_value` docstring, which asserted "higyrus and
market-data declare no mapping fields" — false, and the reason market-data never got the
pass. New Section 3(d) in `29-SEMANTICS-MATRIX.md` records the axis as a shared,
not per-package, concern.

**Behaviour change a human must confirm.** This is the only change in this whole fix set
that a caller can observe: `MarketDataSnapshot.market_data` now falls back to `{}`
instead of holding `None`. One pre-existing assertion changed
(`market-data-client/tests/test_models.py:154`, `is None` → `== {}`), which is a
deliberate exception to the zero-edit merge gate — it pinned the defect.

The operational consequence is recorded in the matrix rather than left to be
discovered: a `/marketdata/latest` **no-data row legitimately sends
`"market_data": null`** alongside `"note": "no data"`, so that row now emits a `missing`
WARNING and is **fatal in strict mode**. That is the correct reading of lock 2 for a
non-`Optional` declaration and matches what matriz already ships, but if the operator
would rather treat the field as genuinely nullable, the remedy is to declare it
`dict[str, Any] | None` — a public-surface typing decision that belongs to the v1.6
typed-surface milestone, not to a review fix.

New tests: absent → `missing` + `{}`; wrong-typed → `type` + `{}`; strict raises on
absent; the pass is silent under a non-dict payload; plus the two precondition tests
described under WR-03.

---

### CR-04: Wire-controlled key names travel verbatim into `field_path`

**Files modified:** all five `_decode.py`; all five `tests/test_decode.py`;
`29-AGGREGATION-CONTRACT.md`
**Commit:** `b9cdb48`
**Status:** fixed

**Applied fix:** `_safe_key()` in all five copies, applied to the `extra` branch's path
segment. Deviates from the suggested regex in one place: `.` is **excluded** from the
safe alphabet (the review kept it), because a wire key containing `.` would forge a path
separator and could collide with a real decode site under lock 10.

```python
_KEY_SAFE_RE = re.compile(r"[^0-9A-Za-z_\-]")
_MAX_KEY_LEN = 64
```

`str(key)` is applied first, and the extra-key iteration now sorts with `key=str`, so a
hand-built dict carrying a non-`str` key can neither interpolate an arbitrary object's
`__repr__` into the record nor raise `TypeError` inside the decode path (lock 9).

Lock 11 amended in `29-AGGREGATION-CONTRACT.md`: the absolute ("there is no key in which
a wire value can travel") is replaced by the precise guarantee, including the explicit
statement of what sanitization does **not** buy (a bare identifier-shaped key still
ships as itself; consumers who need those suppressed filter on `divergence == "extra"`).

New per-package tests: a newline-bearing key, a 200-character key, and non-`str` keys.

---

### WR-01: `DecodePolicy.non_dict_model` is inert

**Files modified:** all five `_decode.py`; `matriz_client/models.py`;
`matriz-client/tests/test_decode.py`; `tools/check_decode_intactness.py`;
`29-SEMANTICS-MATRIX.md`
**Commit:** `b8c1806`
**Status:** fixed

**Applied fix:** the review's first option (make it load-bearing), placed where matrix
row 5 always said the axis lives — at the package's own `from_api`, not in the walker.
`walk_model` returns kwargs and can only express `"from_api_none"`; matriz's
`_SafeModel.from_api` now branches on `POLICY.non_dict_model == "empty_classmethod"` and
early-returns `cls.empty()`. The walker still emits the single terminal `non_dict`
record first, so reporting is unchanged and `test_non_dict_returns_empty` passes for a
reason instead of by coincidence.

Deleting the field (the review's second option) was not available: five pre-existing
`test_policy_constant_matches_the_semantics_matrix` tests assert it.

The false docstring at `matriz_client/models.py` is corrected in place, the
`DecodePolicy` docstring now states **where each axis is read**, and the matrix carries a
new "Where each axis is READ" subsection retracting the "no unparameterized path in the
walker" claim. `test_non_dict_model_axis_is_actually_read` flips the constant and asserts
the fallback taken changes with it.

---

### WR-02: An absent nested-model key is reported as `non_dict`, wrongly attributed

**Files modified:** all five `_decode.py`; all five `tests/test_decode.py`;
`tools/check_decode_intactness.py`
**Commit:** `2c31790`
**Status:** fixed — **requires human verification** (classification change)

**Applied fix:** exactly the suggestion. `walk_field`'s model branch classifies before
recursing: `value is None` emits `missing` against the **outer** model at the correct
path and builds the nested default through `SILENT_SINK`; a genuinely non-dict (not
`None`) nested payload keeps `non_dict` and the nested attribution.

The returned value is unchanged in every case — the same all-defaults instance the
`non_dict` branch produced, built with the same silent sink. Only the record changes.
All 1531 tests pass, including matriz's `empty()`-silence and lock-8 terminal tests.

New tests per package: absent nested key → `("_CarriesNested", ".hoja", "missing")` and
nothing else; `"garbage"` nested payload → `("_Leaf", ".hoja", "non_dict")`. matriz uses
its existing `_Nested`/`_Leaf` pair, which is the shape the finding says matriz carries
about ten times.

---

### WR-03: Nested models are constructed with `hint(**walk_model(...))`

**Files modified:** `market-data-client/tests/test_decode.py` (commit `9711806`);
all five `_decode.py` + `tools/check_decode_intactness.py` (commit `3d12a9d`)
**Commits:** `9711806`, `3d12a9d`
**Status:** fixed via the review's stated fallback, deliberately not via the walker change

**Applied fix:** the review's primary suggestion — dispatch to `hint.from_api(value)`
when the model declares an override — is **not** safe here, and the reason is worth
recording: an override resolves its own sink through `current_sink()` rather than
accepting the sink threaded through the recursion, so the nested decode would leave the
enclosing scope and lock 5's collapse would stop firing inside it. Trading a silent
exemption skip for a silent dedupe leak is not an improvement.

The review's stated minimum is implemented instead, and hardened:

- `test_models_with_a_from_api_override_are_never_a_nested_field_type` added to
  market-data — the counterpart of matriz's mapping precondition test — covering both
  unguarded exemptions (`MarketDataSnapshot.from_api`'s `received_at` injection and
  `Symbol.from_api`'s `market_id` mirror).
- `test_no_mapping_carrying_model_is_ever_a_nested_field_type` added to market-data as
  well, so the mapping axis added by CR-03 carries the same guard matriz has.
- The constraint and the reason the obvious fix is wrong are now recorded **at the
  `_is_model` branch itself**, in all five copies, naming the tests that fail the day an
  overriding model becomes another model's field type.

---

### WR-05: matriz's `auth_basic` pre-scan falls through on malformed input

**Files modified:** `matriz_client/_logging.py`, `matriz-client/tests/test_logging.py`
**Commit:** `d90f472`
**Status:** fixed

**Applied fix:** exactly the suggestion — fail closed. The `auth_basic` key is now
deleted unconditionally and replaced either by the split fields or, when
`_redact_auth_basic_tuple` returns `None`, by `{"auth_basic": "***"}`. The helper's
docstring now states that `None` means "could not be split", **not** "safe".

The change is outside the marker-delimited scan region (it lives in
`RedactingFilter.filter`, below the `end` marker), so Check B is unaffected.

One pre-existing test asserted the vulnerability
(`test_redact_auth_basic_tuple_malformed_does_not_crash`: "leaves it untouched") and was
updated — a second deliberate exception to the zero-edit gate, on a credential-leak path.
A new parametrized test covers list, wrong arity, `bytes` member, mapping and raw `bytes`
shapes, asserting the secret literal is absent from `record.__dict__`.

---

### WR-06: The WebSocket path silently downgrades strict mode to observable

**Files modified:** `matriz_client/ws_client.py`, `matriz-client/tests/test_ws_decode_mode.py`
**Commit:** `fd5b490`
**Status:** fixed

**Applied fix:** exactly the suggestion. `ws_connect` stamps
`_DECODE_STRICT_ATTR` on the `WebSocketApp` instance before starting the thread, and
`_handle_open` reads it from there — the instance is owned by the daemon thread for the
whole connection, so `ws_disconnect` clearing the module global while a frame is in
flight can no longer take the mode away. When the attribute is absent (a handler invoked
on an app this module did not build), the fallback is still observable but is now
**announced** at WARNING on the paquete logger instead of collapsing silently through
`bool(None)`.

New tests: the stamp survives the module global being cleared mid-connection; an unstamped
app logs the warning and lands in observable mode.

---

### WR-07: The intactness gate proves the copies agree with each other only

**Files modified:** `tools/check_decode_intactness.py`
**Commit:** `7d06016` (subsequently bumped by `2c31790`, `b8c1806`, `3d12a9d`)
**Status:** fixed

**Applied fix:** exactly the suggestion, both halves.

- `CANONICAL_DIGEST` pins the sha256 of the reviewed canonical body. Check A now fails
  when the five copies agree with each other but not with the pin — the uniform-edit hole
  — and the failure message prints the computed digest so a reviewed change can be
  re-pinned deliberately. The pin was exercised for real four times during this fix run.
- Check C's `BAN_LIST` entries carry the filename they apply to. `strict=False` is now
  scoped to `_decode.py`, so `zip(a, b, strict=False)` or `json.loads(..., strict=False)`
  elsewhere in a package no longer reds the build with a misleading message.
  `msgspec.field(` stays repo-wide (the pattern is specific enough to be unambiguous).

Both behaviours were self-tested by driving the module directly: a wrong digest raises
`CheckFailure`, and a filename-scoped pattern matches only in the named file.

---

## Deferred Issues

### WR-04: Fields made optional by a dataclass default are `missing` and fatal in strict mode

**File:** `packages/higyrus-client/src/higyrus_client/_decode.py:436-446` (and all five copies)
**Status:** deferred — design decision requiring operator input, not guessed at

**Why it is not fixed here.** The finding is correct on the facts: `walk_model` supplies a
value for every declared field, so `dataclasses.Field.default` / `default_factory` never
applies, and `Symbol.id: int = 0`, `market_id: str = ""`, `created_at`/`updated_at`, and
every matriz `field(default_factory=X.empty)` emit a WARNING on a perfectly normal payload
and raise in strict mode.

But the fix is a **semantics change to what "optional" means for every model in the repo**,
and it collides with two signed artifacts rather than sitting under them:

1. **Lock 2 is explicit** that the opt-in to absence is `Optional`, not "has a default":
   "the model declares the field but the payload has no key for it (or the key is present
   with a `None` value where the declared type is not `Optional`)". Treating a dataclass
   default as a second, implicit opt-in adds an eighth axis to
   `29-SEMANTICS-MATRIX.md` — which that document states in terms is "a separate decision
   with its own artifact and its own operator signature", explicitly not in scope for
   Phase 29.
2. **Phase 33 budgets against the current reading.** `29-SIZING.md` declares the divergence
   budget; suppressing every defaulted-and-absent field silently changes the floor that
   budget was ratified against. Whichever way this goes, Phase 33's numbers move.

The two defensible outcomes are mutually exclusive and the review itself offers both
("If instead the current behaviour is intended, say so explicitly in the semantics matrix
as an eighth axis"). Picking one without the operator would be guessing at a one-way door
of exactly the kind locks 4 and 5 were signed for.

**What the operator needs to decide:** does "declared with a default" opt a field out of
absence reporting, the way `T | None` does?

- **Yes** → apply the review's `_MISSING` sentinel patch in all five copies, add the eighth
  axis to the matrix, and re-ratify `29-SIZING.md`'s floor downward.
- **No** → record the current behaviour as the eighth axis in the matrix so Phase 33
  budgets against it knowingly, and note that model authors' defaults are construction
  conveniences, not wire contracts.

Related but distinct: CR-03's fix makes a `/marketdata/latest` no-data row
(`"market_data": null`) fatal in strict mode. That is the same *shape* of question for a
single field and is recorded under CR-03 above; if WR-04 resolves toward "yes", that case
should be revisited with it.

---

## Out of Scope (not attempted)

IN-01 (dead `open_request_scope()` in `_handle_open`), IN-02 (`_MAX_SCAN_ENTRIES` bypass),
IN-03 (matriz's missing `_RECORD_KEYS` assertion) and IN-04 (multi-arm `Union`
pass-through) are Info-tier and outside this run's `critical_warning` scope. Note that
IN-01's dead call is now harmless in a new way: with CR-01's fix, the scope
`_handle_open` binds is adopted and retired by the first frame's `_parse_frame`.

---

_Fixed: 2026-08-19_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
