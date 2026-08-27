---
phase: 30-iol-client-tipado
plan: 01
subsystem: api
tags: [python, dataclasses, mypy, typing, iol-client, decode, tdd]

# Dependency graph
requires:
  - phase: 29-decoder-observable
    provides: "`_decode.py` — the frozen walker (walk_model, POLICY, _response_parser, DecodeScope) that SafeModel.from_api delegates to"
  - phase: 07-core-extraction
    provides: "`_core.py` pure builders/parsers + the import-linter contract that keeps _core off the transport modules"
provides:
  - "`iol_client.models` — SafeModel (from_api + to_dict), Punta, Cotizacion"
  - "`Cotizacion` decoding both captured schemas (get-quote, get-historical-quotes) with zero divergences"
  - "`get_quote` returning `Cotizacion` across all 4 signatures (method/shim × sync/async)"
  - "`parse_get_quote_response` owning a per-response DecodeScope via `@_decode._response_parser`"
  - "The TYP-01 RED fixture — non-vacuous in both directions under warn_unused_ignores"
  - "The written DecodePolicy re-ratification Phase 29 deferred to this phase"
affects: [30-02, 30-03, 30-04, 33-live-strict-run, 34-release]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Copied SafeModel per package (no cross-package imports) — CLAUDE.md zero-shared-code constraint"
    - "to_dict() on the base class via dataclasses.asdict, not per model"
    - "@_decode._response_parser on every _core parser that builds models"
key-files:
  created:
    - packages/iol-client/src/iol_client/models.py
    - packages/iol-client/tests/test_models.py
    - packages/iol-client/tests/test_typed_surface_red.py
  modified:
    - packages/iol-client/src/iol_client/__init__.py
    - packages/iol-client/src/iol_client/_core.py
    - packages/iol-client/src/iol_client/client.py
    - packages/iol-client/src/iol_client/aio.py
    - packages/iol-client/tests/test_core.py
    - packages/iol-client/tests/test_client.py
    - packages/iol-client/tests/test_async_client.py
    - packages/iol-client/tests/test_decode.py
    - verification/snapshots/iol-client-surface.txt

key-decisions:
  - "DecodePolicy re-ratified for iol: typed-zero substitution stays, recorded in the models.py module docstring (discharges the Phase 29 obligation in 29-SEMANTICS-MATRIX.md:126-131)"
  - "to_dict() uses cast(Any, self) rather than a type: ignore — SafeModel itself is not a dataclass, and _decode.py's existing cast discipline is the in-repo precedent"
  - "The three assertions on keys absent from the live corpus were removed/rewritten, not migrated: simbolo and precio are not Cotizacion fields"
  - "Prose mentions of subscript syntax and of the attr-defined error code were rephrased so the plan's grep gates measure code, not docstrings"

patterns-established:
  - "Pattern 1: model tests derive their payloads from the committed schema snapshots and round-trip through schema_of, so a model/corpus divergence fails a unit test"
  - "Pattern 2: a RED typecheck fixture is made auto-invalidating by warn_unused_ignores and dual-legged by slots=True + pytest.raises"

requirements-completed: [TYP-01]

# Metrics
duration: 36min
completed: 2026-08-20
status: complete
---

# Phase 30 Plan 01: iol-client tipado (tracer get_quote) Summary

**`get_quote` now returns a frozen slotted `Cotizacion` end-to-end — model, per-response-scoped parser, 4 signatures, public export — with a RED fixture that fails the typecheck on an attribute typo and cannot rot into a no-op.**

## Performance

- **Duration:** 36 min
- **Started:** 2026-08-20T02:08:35Z
- **Completed:** 2026-08-20T02:44:14Z
- **Tasks:** 3
- **Files modified:** 12 (3 created, 9 modified)

## Accomplishments

- `iol_client.models` created with `SafeModel` (`from_api` + `to_dict`), `Punta` and the 20-field `Cotizacion`; all three exported from the package root and listed in `__all__`.
- `Cotizacion.from_api()` decodes **both** captured schemas with zero divergence records, and `schema_of(quote.to_dict())` reproduces both committed baselines exactly.
- All 4 `get_quote` signatures (method + shim, sync + async) return `Cotizacion`, landed in a single commit.
- The `DecodePolicy` re-ratification Phase 29 deferred here is now written down and testable.
- Package suite grew 205 → 220 with mypy strict, ruff, format and import-linter all green.

## Task Commits

1. **Task 1: models.py — SafeModel + Punta + Cotizacion** — `284f51a` (test, RED) → `23505d3` (feat, GREEN). Refactor folded into GREEN: `ruff format`/`check --fix` produced no residual changes worth a separate commit.
2. **Task 2: get_quote end-to-end** — `7e55be4` (test, RED) → `c35071e` (feat, GREEN).
3. **Task 3: RED typecheck fixture** — `86b7830` (test).

## Files Created/Modified

- `packages/iol-client/src/iol_client/models.py` — **new.** `SafeModel` base (delegates to the frozen walker; `to_dict` via `dataclasses.asdict`), `Punta`, `Cotizacion`. Module docstring carries the `DecodePolicy` ratification.
- `packages/iol-client/src/iol_client/__init__.py` — re-exports `Cotizacion`, `Punta`, `SafeModel`; `__version__` untouched at `0.2.0`.
- `packages/iol-client/src/iol_client/_core.py` — `parse_get_quote_response` rewritten in place, returns `Cotizacion`, decorated `@_decode._response_parser`.
- `packages/iol-client/src/iol_client/client.py` / `aio.py` — 4 return annotations; shells stay 3-line delegations; `plazo: str` untouched.
- `packages/iol-client/tests/test_models.py` — **new**, 14 tests.
- `packages/iol-client/tests/test_typed_surface_red.py` — **new**, 1 test.
- `packages/iol-client/tests/test_core.py` / `test_client.py` / `test_async_client.py` — assertions migrated to attribute access.
- `packages/iol-client/tests/test_decode.py` — see deviations 1–3.
- `verification/snapshots/iol-client-surface.txt` — regenerated: +3 class lines, 1 changed function line (exactly the diff Pitfall 3 predicted).

## Plan-mandated records

### (a) DecodePolicy re-ratification — where it lives

Written as a titled section of the `iol_client/models.py` **module docstring**
("DecodePolicy re-ratification (Phase 30…)"). It confirms that iol keeps
`POLICY = DecodePolicy("", 0, 0.0, False, "from_api_none", False, False)` —
typed-zero substitution — rather than matriz-style `missing → None`, with the
three reasons from RESEARCH Pitfall 2: (a) every observed-nullable field is
already declared `T | None`, which the walker returns as `None` without a
record; (b) matriz's policy travels with `scalar_passthrough=True`, which would
put a wire `int` into a `float`-annotated field and break the mypy guarantee
TYP-01 exists to give; (c) `literal_enforced=False` is fixed by D-09 and is not
a tunable. `_decode.py` was **not** touched — it is a ratification of a constant
already in place. The docstring of
`test_decode.py::test_policy_constant_matches_the_semantics_matrix` was updated
to point at where the ratification now lives.

### (b) Assertions removed for naming keys the live corpus does not have

Three, all documented in place with the reason:

| Site | Removed | Reason |
|---|---|---|
| `test_client.py::test_get_quote_url_exacta_con_query_string` | `assert quote["simbolo"] == "GGAL"` | `simbolo` is not among the 20 keys `get-quote.json` records, so it is not a `Cotizacion` field. Post-migration the mock key decodes as an `extra` divergence. The key was **left in the mock** to keep exercising that tolerance. |
| `test_async_client.py::test_async_get_quote_url_exacta_con_query_string` | `assert quote["simbolo"] == "GGAL"` | Same, async twin. |
| `test_core.py::test_parse_get_quote_response_returns_json_dict` | `assert data == {"simbolo": "GGAL", "precio": 1234.5}` | **Neither** key is a `Cotizacion` field nor a corpus key. Fully rewritten as `test_parse_get_quote_response_returns_a_cotizacion` with a real corpus key (`ultimoPrecio`) plus an `isinstance` assertion — the type claim is strictly stronger than the dict-equality claim it replaced. |

No assertion with a typed equivalent was dropped: every subscript read became an
attribute read, and every dict-equality assertion became an `isinstance` + an
attribute assertion.

### (c) Inverse non-vacuity probe of the RED fixture

Both directions run by hand before closing Task 3:

- **Forward** (typo `ultimoPrecioo` + `# type: ignore[attr-defined]`):
  `uv run mypy packages/iol-client/tests` → `Success: no issues found in 13 source files`.
  `pytest …/test_typed_surface_red.py` → `1 passed`.
- **Inverse** (typo replaced by the correct `ultimoPrecio`, ignore comment untouched):
  `uv run mypy packages/iol-client/tests` → `error: Unused "type: ignore" comment [unused-ignore]` at that line, `Found 1 error in 1 file`.

The typo was restored and every gate re-run green. The fixture is therefore
non-vacuous in both directions and cannot silently degrade into a no-op.

### (d) Test counts

| Point | `pytest packages/iol-client -q` |
|---|---|
| Baseline (before this plan) | **205** |
| After Task 1 | 219 (+14 from `test_models.py`; `test_decode.py` net 0 — one test replaced) |
| After Task 2 | 219 (assertions migrated, no new tests) |
| After Task 3 | **220** (+1 RED fixture) |

## Decisions Made

- **`cast(Any, self)` over `# type: ignore` in `to_dict`.** `dataclasses.asdict` requires a `DataclassInstance`; `SafeModel` itself is not a dataclass (its subclasses are). `_decode.py` already uses `cast(Any, cls)` for the same class of problem and calls it "the file's existing mypy-strict discipline", so the cast is the in-repo idiom. It also avoids an ignore that `warn_unused_ignores` would have to keep alive.
- **Mock payloads left as-is.** The 1–2 key mocks now emit ~19 `missing` records per call (Pitfall 9). Confirmed harmless: `strict_decode` defaults to `False`, no iol test enables it for the client surface, and no test asserts on record counts from the package logger. Strict mode was **not** enabled — that is Phase 33's deliverable.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Two pre-existing mypy-strict failures in `test_decode.py`**
- **Found during:** Task 1 (verification)
- **Issue:** `uv run mypy packages/iol-client/tests` failed on two Phase 29 leftovers — `func-returns-value` on `assert _decode.SILENT_SINK(...) is None` (line 736) and an unused `# type: ignore[arg-type]` (line 805). Both predate this plan and both are in the CI mypy loop, so the whole package's tests typecheck gate — which is an acceptance criterion of Tasks 1, 2 **and** 3, and the substrate of Task 3's non-vacuity probe — was red before the first line of this plan was written.
- **Fix:** the `SILENT_SINK` call is now made bare, with a comment recording that mypy proves the `-> None` leg statically while the bare call still pins the "never raises" leg; the unused ignore was deleted.
- **Files modified:** `packages/iol-client/tests/test_decode.py`
- **Verification:** `uv run mypy packages/iol-client/src packages/iol-client/tests` → `Success: no issues found in 25 source files`; the test still passes.
- **Committed in:** `23505d3`

**2. [Rule 1 - Bug] `test_this_package_really_has_no_models_module` asserted the precondition this plan inverts**
- **Found during:** Task 1 (GREEN)
- **Issue:** Phase 29 pinned "iol has no `models.py`" as the structural backing for its standalone-import evidence. Creating `models.py` made that test fail by construction.
- **Fix:** rewritten as `test_decode_stays_decoupled_now_that_models_exists`, asserting the **stronger** post-Phase-30 statement: the module exists, `_decode` still never imports it (the neighbouring test), and the walker recognises `models.Cotizacion` purely by duck-typing (`_is_model(Cotizacion)` true, `_is_model(dict)` false). Three now-stale docstrings/comments in the same file were corrected.
- **Files modified:** `packages/iol-client/tests/test_decode.py`
- **Verification:** 220 tests green; the assertion count went up, not down.
- **Committed in:** `23505d3`

**3. [Rule 1 - Bug] One un-migrated subscript missed by the plan's grep**
- **Found during:** Task 2 (GREEN)
- **Issue:** `test_async_client.py::test_concurrent_401_triggers_exactly_one_reauth` reads `r["ultimoPrecio"]` inside a comprehension over `asyncio.gather` results. The plan's locator (`grep 'quote\['`) does not match a loop variable, so it failed with `TypeError: 'Cotizacion' object is not subscriptable`.
- **Fix:** migrated to attribute access plus an `isinstance` assertion over all three results.
- **Files modified:** `packages/iol-client/tests/test_async_client.py`
- **Verification:** the WR-01 concurrency invariant still passes.
- **Committed in:** `c35071e`

**4. [Rule 3 - Blocking] `verification/snapshots/iol-client-surface.txt` needed regenerating**
- **Found during:** Task 2 (verification)
- **Issue:** `verification/test_phase06_nyquist_gaps.py` shells out to `regen_snapshots.py` and asserts the committed snapshot does not drift. The public surface legitimately changed (+`Cotizacion`, +`Punta`, +`SafeModel`, `get_quote -> 'Cotizacion'`), so the committed baseline was stale — exactly the diff Pitfall 3 predicted.
- **Fix:** regenerated with the sanctioned tool (`uv run python verification/regen_snapshots.py`) and committed alongside the source change, per the golden-file contract written in `test_public_surface.py`. Only the iol file changed.
- **Files modified:** `verification/snapshots/iol-client-surface.txt`
- **Verification:** `pytest verification/test_public_surface.py` → 4 passed; `pytest verification/test_with_options.py` → 17 passed (12m29s, slow by nature).
- **Committed in:** `c35071e`

**5. [Rule 1 - Bug] Two grep acceptance gates were matching prose, not code**
- **Found during:** Tasks 2 and 3 (verification)
- **Issue:** `grep -c 'quote\["'` returned 1 per test file and `grep -c 'attr-defined'` returned 2, in both cases because docstrings I had just written quoted the very syntax the gate looks for. The gates would have kept returning false positives for any future reader.
- **Fix:** rephrased the docstrings ("the assertion on the `simbolo` key", "an undefined attribute") so the gates measure code. No documented fact was lost — the removals are recorded here in full.
- **Files modified:** `test_client.py`, `test_async_client.py`, `test_typed_surface_red.py`
- **Verification:** all three greps now return the values the plan specifies (0, 0, 1).
- **Committed in:** `c35071e`, `86b7830`

---

**Total deviations:** 5 auto-fixed (2 blocking, 3 bugs). No Rule 4 situations arose — no architectural decision was reached, and no `checkpoint:decision` was needed (as the plan predicted).
**Impact on plan:** all five were necessary to reach the plan's own acceptance criteria. Deviations 1, 2 and 4 are consequences of this plan inverting preconditions Phase 29 had frozen; 3 and 5 are locator gaps in the plan's own grep-based instructions. No scope creep: nothing outside `packages/iol-client` and the one verification snapshot was touched.

## Prohibitions — status at close

| Prohibition | Status |
|---|---|
| No RESPONSE field gains a closed type; `plazo`/`moneda` stay free text, promotion deferred to F33 | **held** — both declared `str`/`str \| None`; no `Literal` anywhere in `models.py`; `plazo: str = "t2"` unchanged on all 4 signatures |
| Neither `models.py` nor the parsers emit a wire value on any output channel | **held** — AST allowlist check passes (`__future__`, `dataclasses`, `typing`, `iol_client` only); no logging call in `models.py`; all records remain type-and-path |
| The suite is not made green by weakening assertions that have a typed equivalent | **held** — see record (b): every removal is a key the live corpus does not carry, each recorded above; the one rewrite is strictly stronger than what it replaced |
| `SafeModel` is copied, never imported from another package | **held** — `models.py` imports only `iol_client._decode` |

## Issues Encountered

- **`verification/test_with_options.py` takes ~12.5 minutes.** Pre-existing (retry/backoff paths with real sleeps), not caused by this plan, and not part of the CI test job, which runs per-package only. Noted so a future executor does not treat a long-running harness run as a hang.

## User Setup Required

None — no external service configuration required. Zero packages installed; `uv.lock` byte-identical.

## Next Phase Readiness

- **30-02 (`Titulo`) and 30-03 (`Instrumento`) are mechanical replication.** The tracer closed green with no surprises from the Phase 29 walker: `SafeModel`, `to_dict`, the `@_response_parser` decorator on parsers and the export/snapshot ritual are all proven and can be copied verbatim.
- **Two locator gaps to carry forward:** (i) grep for subscripts on loop/comprehension variables, not just `quote[`, when migrating the remaining endpoints — `test_async_client.py` had one; (ii) `verification/snapshots/iol-client-surface.txt` must be regenerated in each of 30-02/30-03/30-04 that changes the surface.
- **Open by design (F33):** the `Punta` element shape is still inobservado (the corpus only ever recorded `[]` and `null`), and the `cantidadOperaciones` int/float asymmetry will surface as a legitimate divergence in the strict live run, not as a defect. Both are documented in the `Cotizacion` docstring at the site they constrain.
- **No blockers.**

---
*Phase: 30-iol-client-tipado*
*Completed: 2026-08-20*

## Self-Check: PASSED

All 3 created files exist on disk; all 5 task commits resolve in `git log`.
