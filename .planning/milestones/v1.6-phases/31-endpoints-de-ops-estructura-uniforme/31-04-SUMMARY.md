---
phase: 31-endpoints-de-ops-estructura-uniforme
plan: 04
subsystem: api
tags: [market-data-client, typing, dataclasses, safemodel, decode-walker, nullability, drift-detection]

# Dependency graph
requires:
  - phase: 29-decoder-observable
    provides: "`_decode.walk_model` / `walk_field`, the `DecodeScope` sink, `STRICT_DECODE`, and the `@_decode._response_parser` scope decorator now applied to BOTH health parsers"
  - phase: 30-iol-client-tipado
    provides: "`SafeModel.to_dict()` (D-08) — the verbatim source copied into market-data's base — plus the ratified CR-01 rule that a `schema_of` fed from a model projection echoes the DECLARATION rather than the wire, which is what Task 3(e) exists to prevent"
  - plan: 31-01
    provides: "the mutating-gate AST guard and the v0.4.0 byte-identical request pin, re-run green after this plan's edits to both shells"
  - plan: 31-03
    provides: "the validated tracer recipe (declare -> decode -> dispatch -> re-export -> strict-typecheck) and the CONTEXT D-03 correction that forced a per-site driver re-check here"
provides:
  - "`market_data_client.Health` / `HealthAuth` / `HealthFeed` / `FeedIngestor` / `FeedMarket` / `FeedPipeline` — six frozen `SafeModel` subclasses across three nesting levels, derived verbatim from the two committed live captures"
  - "`SafeModel.to_dict()` on market-data's own base, verified BYTE-IDENTICAL to iol's by source comparison"
  - "`_core.parse_health_feed_response` — a NEW parser split off the previously shared one; both halves decorated and both newly guarded against a non-dict body"
  - "A typed `get_health` / `get_health_feed` on all 8 signature sites (2 methods + 2 module shims, sync and async)"
  - "Raw-wire schema snapshots restored at both driver health probes, closing the G-3 / T-31-18 drift-blindness hazard before it could land"
  - "The recorded Task 1 nullability verdict (option-b) plus a per-field, per-model audit trail in the model docstrings — Phase 33's adjudication input"
affects: [31-05, 32-enrollment, 33-drivers-strict-mode, 34-release]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Three-nesting-level `SafeModel` trees in market-data — the first ones; the walker's nested branch is now exercised in this package"
    - "Nullability declared ONLY from observed evidence (checkpoint option-b), with a per-`| None` justification sentence in every model docstring"
    - "Typed wrapper call + raw-wire refire at every driver probe that writes a schema snapshot (`probe_market_data_sync`'s in-file pattern, now the health probes too)"
    - "Structural test narrowing over relaxation: an over-broad precondition is restated as the invariant it actually protects, never deleted"

key-files:
  created: []
  modified:
    - packages/market-data-client/src/market_data_client/models.py
    - packages/market-data-client/src/market_data_client/_core.py
    - packages/market-data-client/src/market_data_client/client.py
    - packages/market-data-client/src/market_data_client/aio.py
    - packages/market-data-client/src/market_data_client/__init__.py
    - packages/market-data-client/tests/test_core.py
    - packages/market-data-client/tests/test_decode.py
    - packages/market-data-client/tests/test_client.py
    - packages/market-data-client/tests/test_async_client.py
    - packages/market-data-client/tests/test_with_options.py
    - packages/market-data-client/tests/test_with_options_async.py
    - packages/market-data-client/tests/test_transport.py
    - packages/market-data-client/tests/test_public_surface_market_data.py
    - main_market_data.py
    - .planning/phases/31-endpoints-de-ops-estructura-uniforme/deferred-items.md

key-decisions:
  - "CHECKPOINT VERDICT option-b (Restraint): exactly TWO fields across the six models are declared nullable — `FeedIngestor.last_error` and `FeedPipeline.last_write_error`, both CONTEXT-locked by D-01 and both observed as `null` in the one live capture. Every other field is declared per the capture."
  - "CORRECTED MODEL COUNT: this phase produces NINE models across both packages (higyrus `Health` from 31-03, plus eight in market-data — six here and two in 31-05). CONTEXT D-01's '~7' and D-13's '4' are both wrong."
  - "`last_write_at` belongs to `FeedPipeline`, NOT `FeedMarket` — the checkpoint discussion's field list had it on the wrong model; the live schema is authoritative and was followed."
  - "market-data's `probe_health_feed_recheck_sync` needed NO `to_dict()` escape hatch — `feed.ingestor.last_error` reads the same value the chained `.get()` did, and the site writes no schema snapshot. The `len(created)` site RESEARCH flagged belongs to `add_holidays` (plan 31-05), not to any health probe."
  - "The blanket `test_no_shipped_safemodel_appears_as_a_nested_field_type` was NARROWED to the call-site-exempt models it actually guards, not relaxed — the two later companion tests pin the same two axes independently."
  - "Four `mypy --strict` errors remain in `packages/market-data-client/tests/`; all four are pre-existing and the plan is net-negative-one (5 -> 4). Deferred as D-4."

patterns-established:
  - "Evidence-only nullability: an Optional must trace to an OBSERVED null or a locked decision, and must be justified by name in the model docstring — because the walker's union-with-None branch reports nothing"
  - "In-test payloads proven against the committed live capture by reducing them with the drivers' own keys+types projection, so a model test is evidence about the WIRE"
  - "Per-site driver verdicts recorded in-code, never generalized from a sibling package's finding"

requirements-completed: [TYP-02]

# Metrics
duration: 47min
completed: 2026-08-25
status: complete
---

# Phase 31 Plan 04: market-data health endpoints (`Health` + `HealthFeed`) Summary

**Six frozen `SafeModel` classes across three nesting levels, one shared parser split into two decorated and newly-guarded ones, eight signature sites retyped on both shells — and the driver's health schema snapshots kept pointed at the raw wire so the typing change imports no observability regression.**

## Performance

- **Duration:** 47 min
- **Started:** 2026-08-25T10:11:17Z
- **Completed:** 2026-08-25T10:58Z
- **Tasks:** 3 (1 pre-resolved checkpoint + 2 TDD tasks, 5 commits)
- **Files modified:** 15

## Task Commits

1. **Task 1: nullability checkpoint** — pre-resolved by the operator before spawn; no commit (produces a recorded decision and no code)
2. **Task 2: six models + `to_dict()`** — `a590e74` (test, RED) → `bbcb4a8` (feat, GREEN)
3. **Task 3: parser split, 8 sites, exports, driver** — `66085bf` (test, RED) → `a323d2a` (feat, GREEN) → `174311a` (fix, mypy discipline on the plan's own new test)

No REFACTOR commit was needed: both GREEN implementations landed at production shape.

---

## 1. THE CHECKPOINT VERDICT — verbatim, and the exact field list

This is the item the plan requires to be recorded prominently, because **Phase 33 adjudicates against it**.

### Verdict: **option-b (Restraint)**

### Explicit per-model nullable-field list

**Declared `str | None` — exactly TWO fields, both already CONTEXT-locked by D-01:**

| Model | Field | Why nullable |
|---|---|---|
| `FeedIngestor` | `last_error` | OBSERVED as `null` in the live capture, and locked nullable by CONTEXT D-01 |
| `FeedPipeline` | `last_write_error` | OBSERVED as `null` in the live capture, and locked nullable by CONTEXT D-01 |

**Declared `str` (non-optional), per the single live capture — the nine under-determined fields:**

| Model | Field |
|---|---|
| `FeedIngestor` | `last_frame_at` |
| `FeedIngestor` | `started_at` |
| `FeedPipeline` | `last_write_at` |
| `FeedMarket` | `next_transition` |
| `FeedMarket` | `session_open` |
| `FeedMarket` | `session_close` |
| `FeedMarket` | `last_business_day` |
| `HealthFeed` | `newest_received_at` |
| `HealthFeed` | `oldest_received_at` |

> **Model-ownership correction, made against the authoritative source as the plan directed.** The checkpoint discussion's field list placed `last_write_at` on `FeedMarket`. The committed live capture
> (`.planning/verification/schemas/market-data-client/get-health-feed.json`) and RESEARCH § "Exact Model Shapes" both put it under `ingestor.pipeline`, so it is declared on **`FeedPipeline`**. Every other field's model assignment in the checkpoint list was re-verified against the capture and matched. The discussion also described these as "seven" while listing nine; nine is the correct count and all nine are declared `str`.

`FeedMarket.reason` — the fifth member of option-a's "market-session group" — is likewise declared `str`; the capture shows it populated alongside `enabled: true`. `FeedIngestor.reason` is an independent field on an independent model and was never in that group.

### Rationale, recorded in each affected model docstring and here

Nothing is declared nullable unless it was **CONTEXT-locked or actually observed as `null`** in the one live capture. The tradeoff is asymmetric and runs against tolerance:

- A wrong **non-null** guess surfaces **loudly** in Phase 33's strict driver run. Self-correcting, in-cycle, and directly comparable against the ratified `market-data-client >= 50` divergence floor. This is the designed outcome, not a break.
- An **over-declared `Optional`** would instead **silently and permanently** hide that field from the divergence census — `_decode.walk_field`'s union-with-`None` branch returns `None` **without emitting a divergence record** — which is exactly why zero fields are declared nullable beyond the two already locked by CONTEXT D-01.

Each model docstring carries the three-part audit trail the plan required: endpoint + decision reference, live-capture provenance (schema JSON path + 2026-07-31 capture date), and a per-`| None` justification naming the field. `HealthFeed`'s docstring additionally records the **single-state caveat**: the capture is one connected, healthy, market-open observation, so the nullability of the nine fields above is a **declared assumption awaiting Phase 33's live evidence** (RESEARCH A1/A2/A3).

**Runtime enforcement of the verdict.** `test_health_models_declare_exactly_the_two_locked_optionals` asserts the Optional set by **equality** against `{FeedIngestor.last_error, FeedPipeline.last_write_error}`. A seventh Optional cannot be added to these six models without failing that test. The verdict is now a pinned contract, not a docstring claim.

**Acceptance criteria of Task 1, confirmed:** a verdict of exactly `option-b` is recorded; the explicit per-model field list is written down above; and `git status --porcelain packages/market-data-client/src/` was **empty** (verified, `0` lines) before any Task 2 edit.

---

## 2. THE CORRECTED MODEL COUNT — nine, not "~7" and not "4"

| Package | Models | Landed in |
|---|---|---|
| `higyrus-client` | `Health` | plan 31-03 |
| `market-data-client` | `Health`, `HealthAuth`, `HealthFeed`, `FeedIngestor`, `FeedMarket`, `FeedPipeline` | **this plan (6)** |
| `market-data-client` | `AddHolidaysResult`, `DeleteHolidayResult` | plan 31-05 (2) |
| | **TOTAL: 9** | |

CONTEXT **D-01** says "~7 models" and **D-13** says "4". Both are wrong; RESEARCH § D-01..D-13 Verification Ledger correction (a) already flagged this and the live captures confirm it. **This plan is where the count actually lives** — six of the nine.

---

## 3. PLAN 31-01's SAFETY NET — re-run and GREEN after the shell edits

This plan edits `client.py` and `aio.py`, which also host the 8 gated mutation methods (T-31-21). Both of plan 31-01's guards were re-run **after** the shell edits landed:

| Gate | Result |
|---|---|
| `uv run pytest packages/market-data-client/tests/test_mutation_gate_ast.py -q` | **green** |
| `uv run pytest packages/market-data-client/tests/test_v040_request_pin.py -q` | **green** |
| `uv run pytest packages/market-data-client/tests/test_mutation_gate.py -q` | **green** (23 passed across the three files) |

`_MUTATION_METHODS` in `test_public_surface_market_data.py` was **not touched** — plan 31-05 owns the mutation side. Neither health builder was modified: both keep `authenticated=False` by design (T-20-02 / T-31-22), so an anonymous spec still cannot acquire a stale Bearer.

---

## 4. `main_market_data.py` — every health-consuming site checked individually, with its verdict

31-03 explicitly warned against generalizing its higyrus finding. Each site was re-checked on its own terms:

| Site | Reads a health result how | G-3 projection hazard? | Verdict / action |
|---|---|---|---|
| `probe_health_sync` (~line 613) | `client.get_health()` / `get_health_feed()` → straight into `_write_schema_snapshot` | **YES** — this is a `schema_of` site | **FIXED.** Keeps the typed calls (they prove the public surface works) and **adds** `_raw_via_request_sync(client, _core.build_health_request(...))` + the feed equivalent, feeding the RAW result to `_write_schema_snapshot`. Mirrors `probe_market_data_sync`; both refires stay inside the `try` per D-09. |
| `probe_health_async` (~line 645) | async mirror of the above | **YES** | **FIXED** identically with `_raw_via_request_async`. |
| `probe_health_feed_recheck_sync` (~line 2983) | `feed.get("ingestor")` then `ingestor.get("last_error")` | **NO** — writes no schema snapshot | **Retyped to attribute access, NOT `to_dict()`.** `feed.ingestor.last_error` reads the same value the chained `.get()` did; the defensive `isinstance(ingestor, dict)` is now dead by construction (an absent `ingestor` is the zero-valued instance, never `None`). The verdict and its reasoning are recorded in-code at the site. |

**Where the `len(created)` site the plan mentioned actually lives:** `main_market_data.py:~2389`, inside the **`add_holidays`** probe — a calendar-write site owned by **plan 31-05**, not a health site. It was left untouched here. So the phase-level picture is: higyrus needed no driver change at all (31-03), market-data's two health snapshot sites needed the raw refire, its health-recheck site needed a one-line attribute retype, and the `len()` escape-hatch question is 31-05's.

**Why the refire matters (T-31-18, the prohibition this plan was warned about):** the walker has already coerced every non-optional field to its declared type and dropped every undeclared key, so `schema_of` over a model projection is a function of the **declaration**, not the wire — a `float→str`, an added key and a removed key are all three invisible. The warning sign the plan named (a live driver run reporting **zero** SHAPE findings on an endpoint that previously reported some) is now structurally impossible for these two endpoints. `schema_of` itself still emits keys and type names only, never values, so the snapshots stay PII-free by construction.

---

## 5. What was built

### `models.py`

- **`SafeModel.to_dict()`** appended to the EXISTING base after `from_api`, **verified byte-identical** to `iol_client.models.SafeModel.to_dict` (docstring included) by `inspect.getsource` comparison. Copied, never imported — C-2 forbids cross-package imports and there is no shared internal package by design. Imports widened with `dataclasses` (`cast` was already present).
- **`from_api`, `_apply_mapping_policy` and the Lock-8 silent-sink branch are byte-unchanged.** `git diff -U0` over the file shows no `-` line inside either function.
- **Six models** in dependency order: `HealthAuth` → `Health` → `FeedMarket` → `FeedPipeline` → `FeedIngestor` → `HealthFeed`. All `@dataclass(frozen=True, slots=True)`, bare annotations, `| None` fields last with `= None`, **no `received_at`** (health is not a snapshot and has no staleness dimension), **no `dict[...]` field**, **no `from_api` override**.
- Module docstring records the **CR-01 caveat** on `to_dict()`: the iol wording calls it "the adapter the verification harness feeds to `schema_of`", which is now known to be wrong for a snapshot site. It is the `len()` / `isinstance` escape hatch only.

### `_core.py`

One shared parser became two. Both follow `parse_calendar_config_response`'s in-package shape exactly:

```
@_decode._response_parser        # leading underscore intact, never aliased
resp.read()                      # body-consume-then-raise: Phase 7 D-06 HTTP/2 invariant
raise_for_response(resp)
if not resp.content: return Model.from_api(None)     # 204 / empty-body zero-valued carve-out
raw = resp.json()
if not isinstance(raw, dict):                        # NEW guard (D-04) — the shared parser had NONE
    raise MarketDataAPIError(0, f"expected dict, got {type(raw).__name__}")
return Model.from_api(raw)
```

`Health` and `HealthFeed` imported in sort order; `"parse_health_feed_response"` added to `__all__` in its sort position (still ASCII-sorted, RUF022-clean).

### `client.py` / `aio.py` — 8 sites

`Client.get_health → Health`, `Client.get_health_feed → HealthFeed` (now naming `parse_health_feed_response` — that one changed line **is** the split), plus the two `AsyncClient` mirrors and the four module shims. Builders untouched. Docstring usage examples in all three modules moved from mapping subscript to attribute access (C-10).

### `__init__.py` + the hand-maintained roster

All six names added to the models import block and to `__all__` in ASCII sort position, **and** to `_NEW_PUBLIC_NAMES` in `tests/test_public_surface_market_data.py` under a `# Phase 31 — ops endpoints (TYP-02)` comment. That tuple asserts "every listed name is importable and in `__all__`", never "every exported name is listed", so omitting the six would have been **silently green** (G-2).

---

## 6. G-8's prediction — confirmed, on one axis; a second axis was NOT predicted

The plan's backstop claim was that adding `@_decode._response_parser` to the health parsers **perturbs no existing decode test**, to be falsified cheaply by running `tests/test_decode.py`.

**On the decoration axis the prediction held exactly.** The four `get_health`-using tests either assert the strict-mode flag, drive `_request` directly, or compare scope object identity — none depends on the retired-versus-open scope distinction. No test failed for a decoration-related reason.

**A second axis the plan did not anticipate did perturb two of them: the SHAPE change.** `test_strict_mode_bound_by_sync_request` and `test_strict_mode_bound_by_async_request` mock `/health` with a bare `{"status": "ok"}` and drive the client with `strict_decode=True`. Once `get_health` returns a `Health` with a non-optional nested `auth`, that mock is a **missing-field divergence**, and strict mode raises `MarketDataDecodeError` — for a reason entirely unrelated to those tests' subject (that the mode is bound from shared state). **Corrected on the TEST side** with the full live shape, per the 30-03 ratified precedent. The parser's guard was never loosened.

---

## Decisions Made

- **option-b, and pinned by equality test** — see § 1. The verdict is enforced at runtime, not just documented.
- **`last_write_at` lives on `FeedPipeline`** — the live schema overrode the checkpoint discussion's model assignment, exactly as the spawn instructions directed.
- **`Health.auth` is a non-optional nested model** — so an absent `auth` yields the zero-valued `HealthAuth` **plus** a `missing` divergence record, rather than a `None` that nothing would have reported.
- **`probe_health_feed_recheck_sync` uses attribute access, not `to_dict()`** — the escape hatch is for `len()` / `isinstance` sites; this one is neither, and it writes no snapshot.
- **The blanket nested-field-type ban was narrowed, not relaxed** — see Deviation 1.
- **Four pre-existing `tests/` mypy errors deferred** as D-4; the plan is net-negative-one on that count.

## Deviations from Plan

### 1. [Rule 3 - Blocking] `test_decode.py`'s blanket nested-field-type ban had to be narrowed

- **Found during:** Task 2 GREEN (first run of `pytest tests/test_decode.py`)
- **Issue:** The plan named the two committed structural assertions at `test_decode.py:~1203` and `:~1239` — both of which **passed** — but a **third**, older and strictly broader one exists at `:641`: `test_no_shipped_safemodel_appears_as_a_nested_field_type`, asserting that **no** shipped `SafeModel` is **ever** another model's field type. This plan requires four of the six new models to be nested field types, so it failed on `('Health', 'auth', HealthAuth)`.
- **Why narrowing is correct, not a relaxation:** that test's own docstring states the invariant it protects — *"a `from_api` OVERRIDE on a nested model type would be BYPASSED"* — and its own escape clause: *"If a future plan nests one, this test fails and the walker needs an explicit hook."* A hook is needed only for a model carrying a **call-site exemption** (a `from_api` override, or the post-walk mapping pass over a `dict[...]`-declaring model). None of the six new models carries either, so nothing is bypassed. Until this phase no market-data model had a nested-model field at all, which is why the blanket and precise forms were indistinguishable when it was written.
- **Fix:** restated as `test_no_call_site_exempt_safemodel_appears_as_a_nested_field_type`, looping the `other` set over exempt models only, with a vacuity guard (`assert exempt`) so it cannot silently become a no-op, and a Phase-31 note recording the narrowing. Both companion tests at `:1203` and `:1239` still pin the same two axes independently — a regression on either now fails in **three** places.
- **Verification:** `pytest tests/test_decode.py -q` green; the two companion assertions still pass unchanged.
- **Committed in:** `bbcb4a8`

### 2. [Rule 3 - Blocking] Two test files outside the plan's `files_modified` had to be re-mocked

- **Found during:** Task 3 (RED gate authoring)
- **Issue:** The plan enumerates three "incidental" G-7 health assertions (`test_with_options.py`, `test_with_options_async.py`, `test_transport.py`). It does not list `test_client.py` and `test_async_client.py`, which contain the package's **direct** health tests — four `== {"status": "ok"}` mapping assertions that fail on the type change. Neither file mentions `add_holidays` or `delete_holiday`, so they are invisible to the grep plan 31-05 will run, exactly like the three the plan did enumerate.
- **Fix:** all four moved to attribute access on `.status`, in the same RED commit as the enumerated three. Each test's subject (anonymity, zero token POSTs, 401 handling) is unchanged.
- **Verification:** `pytest packages/market-data-client -q` → 527 passed.
- **Committed in:** `66085bf`

### 3. [Rule 3 - Blocking] Two `test_decode.py` strict-mode tests re-mocked to the live shape

- **Found during:** Task 3 GREEN
- **Issue / fix / rationale:** see § 6 above.
- **Committed in:** `a323d2a`

### 4. [Rule 2 - Missing Critical] Runtime enforcement added for the checkpoint verdict

- **Found during:** Task 2 (RED gate authoring)
- **Issue:** T-31-17's mitigation as written is documentary — "every `| None` must be justified in its docstring". A docstring cannot fail a build. The threat is precisely that a future edit adds a seventh Optional and the census silently under-counts.
- **Fix:** `test_health_models_declare_exactly_the_two_locked_optionals` asserts the Optional set by **equality**. Companion per-model parametrized tests pin the no-override, no-mapping-field and no-`received_at` bans directly on the six (rather than relying only on the file-wide structural tests).
- **Committed in:** `a590e74`

### 5. [Rule 3 - Sequencing] All Task-3 test re-mocks folded into Task 3's RED gate

- Applying 31-03's ratified deviation-1 precedent: landing the re-mocks with the source would have left a non-TDD commit boundary red. They are in the RED commit, so the GREEN commit restores the suite fully green at a deliberate gate.

**Total deviations:** 5 (3 blocking-fix, 1 missing-critical, 1 sequencing). No scope creep; every plan prohibition was respected — no Optional was added to silence a divergence, no model projection reaches a `schema_of` site, no `from_api` override was used as a carve-out, and neither new guard was weakened.

## Issues Encountered

### Four pre-existing `mypy --strict` errors in `packages/market-data-client/tests/` (deferred, D-4)

`uv run mypy packages/market-data-client/tests` exits 1 with four errors. **All four are pre-existing and this plan is net-negative-one on the count** — at `4e7f414` (the plan-start commit) the same command reported **five**, the fifth being `test_core.py:311: Non-overlapping equality check`, which was `assert data == {"status": "ok"}` against the old `dict[str, Any]` return that this plan retyped away. Proven by checking the two test files out at `4e7f414`, re-running mypy, and restoring.

One error **was** introduced by this plan's own new test and **was fixed in-cycle** (`174311a`): `hints_for(model_cls)` with `model_cls: type[SafeModel]` needs the `cast(Any, ...)` discipline the walker and `models._apply_mapping_policy` already use. No `type: ignore` was introduced.

The plan does not require `mypy` on `tests` — only `packages/market-data-client/src` (mandatory local, D-13) and the CI `src` gate, both of which are clean. Logged as **deferred-items D-4** and routed to the same owner as D-2 / D-3.

### Pre-existing matriz `verification/` failures (already logged as D-1)

The full local suite surfaces **19 failed + 19 errors**, all confined to `verification/test_main_matriz_login_fail_uniformity.py` and `verification/test_matriz_sweep_snapshot.py` — the stale pre-Phase-15 `probe_login_sync()` signature logged as D-1 by plan 31-02. Confirmed by running those two files in isolation and reproducing exactly 19+19. Untouched, per the phase's scope boundary.

## Verification Results

| Gate | Result |
|---|---|
| `uv run pytest packages/market-data-client -q` | **527 passed** (was 480 — 47 net new tests, none removed) |
| `uv run pytest packages/market-data-client/tests/test_decode.py -q` | **green** (G-8, on the decoration axis) |
| `uv run pytest .../test_mutation_gate_ast.py .../test_v040_request_pin.py .../test_mutation_gate.py -q` | **23 passed** — 31-01's net still green after the shell edits |
| `uv run mypy packages/market-data-client/src` | **Success: no issues found in 13 source files** (MANDATORY local — CI does not run it, D-13) |
| `uv run mypy` (CI `src` gate, the enrolled five) | **Success: no issues found in 62 source files** |
| `uv run mypy packages/market-data-client/tests` | **4 pre-existing errors** (was 5 at plan start) — deferred-items D-4 |
| `uv run pytest -q` (full local suite incl. `verification/`) | **2000 passed**, 19 failed + 19 errors — ALL in the two D-1 matriz files |
| `uv run pytest verification/test_public_surface.py verification/test_phase06_nyquist_gaps.py -q` | **7 passed** |
| `uv run python verification/regen_snapshots.py` then `git status --porcelain verification/snapshots/` | **empty** — no golden drifted in any package (market-data is not covered by the goldens; the other four are byte-unchanged) |
| `uv run ruff check .` | **All checks passed** |
| `uv run ruff format --check .` | **231 files already formatted** |
| `uv run python tools/check_decode_intactness.py` | **A/B/C/D all pass** — `_decode.py` still hashes to `CANONICAL_DIGEST` across all five copies |
| `uv run python tools/check_uniform_structure.py` | **pass** |
| `python -c "[m.__all__.index(n) for n in (six names)]"` | **exit 0** |
| `to_dict()` byte-identity vs `iol_client` | **BYTE-IDENTICAL** (`inspect.getsource` comparison) |

All 15 of Task 3's grep-shaped acceptance criteria were run and match (both parsers decorated; distinct return annotations ×1 each; the guard string ×2; `__all__` entry ×1; the split reached both shells ×1 each; 8 sites retyped ×2 per shell per form; 6 roster entries; both driver probes carrying the raw refire).

## Threat Flags

None. This plan introduced no new network endpoint, no new auth path, no new file-access pattern, and no schema change at a trust boundary. It **removed** a trust-boundary weakness: the shared health parser previously annotated `resp.json()` as a `dict` and returned it unchecked, so a non-mapping body produced a value contradicting its own annotation. Both halves now raise, naming the observed type only — never the value, never a repr (T-31-19 / T-29-36 / ASVS V7), pinned by a test that additionally asserts the offending body text does **not** appear in the message.

## Known Stubs

None. Every declared field is wired to a live-capture wire key; no placeholder, mock, or hardcoded empty value was introduced. The two `| None` declarations are evidence-backed, not stubs.

## User Setup Required

None. No package was installed; `uv.lock` is unchanged (T-31-SC).

## Next Phase Readiness

**Carry into plan 31-05:**

- **The `len(created)` escape-hatch question is yours.** It lives at `main_market_data.py:~2389` in the `add_holidays` probe, not in any health probe. Decide `to_dict()` versus attribute access there on its own terms, and check whether that site also writes a schema snapshot (the `add_holidays` path already uses `_mutate_raw_sync(...).json()` for its snapshot, i.e. raw wire, so it is likely already correct).
- **`_MUTATION_METHODS` is untouched** and `_NEW_PUBLIC_NAMES` now ends with the Phase 31 block — append `AddHolidaysResult` / `DeleteHolidayResult` there.
- **G-4's open decision is still open:** `parse_calendar_write_response`'s deliberate T-26-13 tolerance (empty / `null` / list / scalar all → `{}`) must resolve to something when it becomes typed. This plan's two health parsers set the in-package precedent: empty → `Model.from_api(None)`, non-dict → **raise**. Note that is a **different** disposition on the non-dict branch, and the calendar-write parser serves a **published mutation** — so the precedent informs but does not decide it.
- **`_core.__all__` is still ASCII-sorted** after gaining one name; keep it that way (RUF022).

**Carry into Phase 33:**

- **§ 1 is the adjudication input.** Nine fields are declared non-nullable on single-state evidence. If the strict run raises on any of them, that is the mechanism working, and the correction is a one-line declaration change plus a docstring update.
- **Every non-collection parser with a 204 / empty-body carve-out inherits 31-03's measured strict-mode raise.** Both new health parsers have that carve-out. It was not re-measured here (31-03 measured it on `Health.from_api(None)` in higyrus and the walker is byte-identical), but the behaviour is the same: a legitimate 204 emits one `non_dict` record and, under `strict_decode=True`, raises.
- **Both health endpoints' schema snapshots are wire-derived again**, so their SHAPE findings remain meaningful. Their divergence census and their snapshot diff are now independent signals rather than one signal echoing a declaration.

**Blockers/concerns for the phase verifier:**

- `uv run mypy packages/<pkg>/tests` is red on **pre-existing** grounds in at least three packages (D-2 ambito, D-3 higyrus, D-4 market-data). The `typecheck` CI job iterates `higyrus-client` first under `set -e`, so D-3 masks the rest; the whole family needs one repair plan before v1.6 ships.
- The **TYP-02 concurrency probe row remains OPEN**, exactly as the plan flagged. `tests/test_decode_concurrency.py` and the scope tests are green, and the two new decorations behaved as G-8 predicted, but that is coverage, not resolution. Not dismissed.

---
*Phase: 31-endpoints-de-ops-estructura-uniforme*
*Completed: 2026-08-25*

## Self-Check: PASSED

All 16 claimed files exist on disk and all five task commits (`a590e74`, `bbcb4a8`, `66085bf`, `a323d2a`, `174311a`) are present in git history.
