---
phase: 30-iol-client-tipado
plan: 02
subsystem: api
tags: [python, dataclasses, mypy, typing, iol-client, decode, tdd]

# Dependency graph
requires:
  - phase: 30-iol-client-tipado
    provides: "Plan 30-01 — `iol_client.models` with SafeModel (from_api + to_dict), Punta, Cotizacion; the `@_decode._response_parser` idiom on _core parsers"
  - phase: 29-decoder-observable
    provides: "`_decode.py` — the frozen walker (walk_model, walk_field, POLICY, _response_parser, DecodeScope)"
provides:
  - "`iol_client.models.Titulo` — 20 fields verbatim from the committed get-instruments-by-type schema"
  - "`iol_client._core._parse_list_or_raise` — the shared list-shaped parser body, owner of the per-response DecodeScope, raising on an unexpected shape"
  - "`get_historical_quotes` returning `list[Cotizacion]` across all 4 signatures"
  - "`get_instruments_by_type` returning `list[Titulo]` across all 4 signatures"
  - "12 of the 16 iol signatures migrated to models (6 per shell)"
affects: [30-03, 30-04, 32-gate-ast, 33-live-strict-run, 34-release]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "`_parse_list_or_raise(resp, model_cls)` decorated with `@_decode._response_parser`; delegating parsers stay undecorated one-liners with an annotated local that narrows the generic list for mypy strict"
    - "Envelope unwrap stays a raw-dict step before any model is built — transport shape is never modelled (D-06)"
    - "A failing shape guard raises; it never degrades to an empty list"
key-files:
  created: []
  modified:
    - packages/iol-client/src/iol_client/models.py
    - packages/iol-client/src/iol_client/__init__.py
    - packages/iol-client/src/iol_client/_core.py
    - packages/iol-client/src/iol_client/client.py
    - packages/iol-client/src/iol_client/aio.py
    - packages/iol-client/tests/test_models.py
    - packages/iol-client/tests/test_core.py
    - packages/iol-client/tests/test_client.py
    - packages/iol-client/tests/test_async_client.py
    - verification/snapshots/iol-client-surface.txt

key-decisions:
  - "`_parse_list_or_raise` raises `IOLAPIError(0, ...)` with status_code 0 — the transport succeeded, the payload shape did not; an HTTP status would misattribute the failure"
  - "The `titulos` envelope keeps its own parser body rather than delegating to the list helper: its top-level wire shape is a dict, not a list, so the helper's guard would reject every valid response"
  - "Task 2's mypy-over-tests gate was reached only at Task 3's commit, because Task 3 owns the files the type change breaks — sequencing recorded rather than papered over by merging the tasks"
  - "No assertion was removed in this plan: every key the migrated tests read (`simbolo`, `ultimoPrecio`, `fechaHora`) is a real field of its model"

patterns-established:
  - "Pattern 3: the per-response DecodeScope is proven by a dedupe test — N rows missing the same key emit 1 record, not N — run under a pristine-decode-context fixture so the claim cannot pass by test-execution order"

requirements-completed: [TYP-01]

# Metrics
duration: 8min
completed: 2026-08-20
status: complete
---

# Phase 30 Plan 02: list-shaped endpoints tipados (`Titulo` + `_parse_list_or_raise`) Summary

**Both list-shaped IOL endpoints now return lists of models across sync and async, and the shared helper that got them there turns an unexpected response shape into a loud `IOLAPIError` instead of the silent empty list this milestone exists to eliminate.**

## Performance

- **Duration:** 8 min
- **Started:** 2026-08-20T02:47:29Z
- **Completed:** 2026-08-20T02:55:02Z
- **Tasks:** 3
- **Files modified:** 10 (0 created, 10 modified)

## Accomplishments

- `Titulo` added to `models.py` with the 20 fields the committed schema records, exported from the package root and listed in `__all__`.
- `_parse_list_or_raise` introduced — owner of the per-response `DecodeScope`, and the site of the shape guard that **raises** rather than degrading (D-06 / T-30-06).
- `parse_get_historical_quotes_response` → `list[Cotizacion]`; `parse_get_instruments_by_type_response` → `list[Titulo]` with the `titulos` unwrap surviving as a raw-dict step.
- All 8 corresponding signatures re-annotated in `client.py` and `aio.py` in a single commit (Pitfall 6). **12 of 16** signatures are now typed — `grep` counts 6 model-returning annotations per shell.
- Package suite grew 220 → **229**, with mypy strict, ruff, ruff format, import-linter and the decode-intactness gate all green.

## Task Commits

1. **Task 1: `Titulo` model** — `35a17a5` (test, RED) → `bc55fbb` (feat, GREEN). Refactor folded into GREEN: `ruff format` / `check --fix` produced no residual changes.
2. **Task 2: `_parse_list_or_raise` + 2 parsers + 8 signatures** — `5b0af59` (test, RED) → `963b85c` (feat, GREEN).
3. **Task 3: assertion migration** — `10503a7` (test).

## Files Created/Modified

- `packages/iol-client/src/iol_client/models.py` — `Titulo` appended after `Cotizacion`; no `from_api` override anywhere (Pitfall 7 respected — `from_api` is still defined exactly once in the module).
- `packages/iol-client/src/iol_client/__init__.py` — `Titulo` added to the `models` import block and to `__all__`, both alphabetically.
- `packages/iol-client/src/iol_client/_core.py` — `_parse_list_or_raise` added; both list-shaped parsers rewritten in place; `Titulo` imported.
- `packages/iol-client/src/iol_client/client.py` / `aio.py` — 8 return annotations; shells stay pure delegations, zero logic moved.
- `packages/iol-client/tests/test_models.py` — +7 tests (14 → 21).
- `packages/iol-client/tests/test_core.py` — +2 tests, 2 rewritten; a `_pristine_decode_context` autouse fixture added.
- `packages/iol-client/tests/test_client.py` / `test_async_client.py` — 8 assertion sites migrated and strengthened.
- `verification/snapshots/iol-client-surface.txt` — regenerated (see deviation 1).

## Plan-mandated records

### (a) Assertions removed for naming keys the live corpus does not have

**None.** Every key the migrated assertions read is a real field of the model
that now carries it:

| Site | Key read | Verdict |
|---|---|---|
| `test_client.py` / `test_async_client.py` — the four `get_historical_quotes` tests | `ultimoPrecio`, `fechaHora` | Both are among `Cotizacion`'s 20 fields (`get-quote.json` / `get-historical-quotes.json`). Migrated. |
| `test_client.py` / `test_async_client.py` — the four `get_instruments_by_type` tests | `simbolo` | Among `Titulo`'s 20 fields. Migrated. |

Note the contrast with Plan 30-01, where `simbolo` **was** removed: it is not a
key of the `get-quote` corpus, and therefore not a `Cotizacion` field. It *is* a
key of the `titulos` corpus, so it is a legitimate `Titulo` field. The same
identifier is a valid attribute on one model and an invalid one on the other —
which is precisely why the plan's rule is "verify the key exists in the model"
rather than "keep any key that looks familiar".

No assertion lost coverage. Three were made **stronger**:

- `isinstance(t, dict)` → `isinstance(t, Titulo)` in both `unwraps_titulos`
  tests — names the class instead of the container.
- Cardinality assertions (`len(serie) == 1`, `len(titulos) == 2`) added where
  the test verifies how many rows came back but only ever read the last one.
- `all(isinstance(row, Cotizacion) ...)` added to the four historical-series
  tests, which previously asserted a value with no type claim at all.

### (b) FA-02 / A1 is marked in the `Titulo` docstring

Confirmed. The docstring's third bullet states, at the site it constrains, that
`fechaVencimiento`, `precioEjercicio` and `tipoOpcion` arrived **without value**
across the entire 2026-06-06 capture, that their non-null type is therefore
**inferred from the field name and never observed**, that this is FA-02 /
RESEARCH Assumptions Log A1 pending Phase 33, and — the operative part for a
future reader — that a type divergence on any of the three is **this assumption
correcting itself, not a model defect**. Phase 33 will read that sentence before
it files a finding.

### (c) The 21 → 20 field inventory correction

D-01 and RESEARCH both say `Titulo` has "21 keys". The committed schema
`.planning/verification/schemas/iol-client/get-instruments-by-type.json` has
**20**. CONTEXT declares the schema the source of truth, so the model has 20
fields and FA-05 is resolved in the schema's favour.

This is recorded in two places that a reader cannot miss: the
`test_titulo_declara_exactamente_veinte_campos` docstring states the conflict
and its resolution, and the count is pinned by that test plus a plan acceptance
gate. **20 is not an omission.**

### (d) Test counts

| Point | `pytest packages/iol-client -q` |
|---|---|
| Baseline (Plan 30-01 close) | **220** |
| After Task 1 | 227 (+7 in `test_models.py`, 14 → 21) |
| After Task 2 | 229 (+2 net in `test_core.py`: 3 added, 1 rewritten in place) |
| After Task 3 | **229** (assertions migrated and strengthened; no new tests) |

## Decisions Made

- **`IOLAPIError(0, ...)` for the shape guard.** `status_code=0` marks a payload
  failure rather than an HTTP one — the transport succeeded. Reusing a real HTTP
  status would send a reader looking for a server error that never happened. The
  message names the received type (`"shape mismatch: expected list, got dict"`),
  which is type-and-path information only, never a wire value.
- **Three deliberate departures from the higyrus helper**, all recorded in the
  helper's own docstring: iol has no `_consume_and_check` (copying higyrus'
  would smuggle in 204/empty-body tolerance iol does not have today — a behavior
  change outside this plan); `IOLAPIError` takes two positionals, not an error
  list; and the decorator goes on the helper only, leaving the delegating
  parsers as undecorated one-liners.
- **`parse_get_instruments_by_type_response` does not delegate.** Its top-level
  wire shape is a dict envelope, so `_parse_list_or_raise`'s guard would reject
  every valid response. It keeps its own body and its own decorator, and the
  `titulos` unwrap runs before any model exists.
- **The `_pristine_decode_context` fixture was added to `test_core.py`.** The
  dedupe test counts divergence records; without an unbound scope at test entry,
  a scope left bound by an earlier test would collapse those records and the
  assertion would pass by execution order rather than by parser behavior.
  Verified independently under `-p no:randomly`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `verification/snapshots/iol-client-surface.txt` needed regenerating**
- **Found during:** Task 2 (verification)
- **Issue:** `verification/test_public_surface.py` asserts the committed snapshot does not drift from the live surface. The surface legitimately changed (+`Titulo`, and the two re-annotated signatures), so the baseline was stale — exactly the carry-forward Plan 30-01 flagged for each of 30-02/03/04.
- **Fix:** regenerated with the sanctioned tool (`uv run python verification/regen_snapshots.py`) and committed alongside the source change. Only the iol file changed: +1 class line, 2 changed function lines.
- **Files modified:** `verification/snapshots/iol-client-surface.txt`
- **Verification:** `pytest verification/test_public_surface.py` → 4 passed.
- **Committed in:** `963b85c`

**2. [Rule 3 - Blocking] Task 2's mypy gate is unreachable before Task 3 lands**
- **Found during:** Task 2 (verification)
- **Issue:** Task 2's acceptance criteria include `uv run mypy packages/iol-client/src packages/iol-client/tests` exiting 0, but the eight assertion sites that break under the new return types live in `test_client.py` and `test_async_client.py` — files Task 3 owns by its own `<files>` block. The gate is unreachable at Task 2's commit by construction of the plan, not by any implementation choice.
- **Fix:** the two tasks were kept separate rather than merged, and the boundary was made honest: `963b85c` is green on `mypy packages/iol-client/src`, on `test_core.py`, on `test_models.py`, on ruff, on import-linter and on the decode-intactness gate, and is red only on the eight sites Task 3 exists to migrate — the same intentional-red relationship a TDD RED commit has with its GREEN. `10503a7` restores the full gate. Merging them would have hidden which change caused which breakage and would have left Task 3 with no deliverable.
- **Files modified:** none beyond the two tasks' own files.
- **Verification:** at `10503a7` — 229 passed, `mypy … src … tests` → `Success: no issues found in 25 source files`.
- **Committed in:** `963b85c` + `10503a7`

---

**Total deviations:** 2 auto-fixed, both blocking, both sequencing consequences rather than defects. No Rule 1 bugs surfaced — the Phase 29 walker and the 30-01 idioms replicated without surprises, as 30-01's "Next Phase Readiness" predicted. No Rule 4 situations arose and no `checkpoint:decision` was needed (the plan predicted none: no one-way decision is taken here).
**Impact on plan:** none on scope. Nothing outside `packages/iol-client` and the one verification snapshot was touched.

## Prohibitions — status at close

| Prohibition | Status |
|---|---|
| No RESPONSE field gains a closed type; `mercado`/`plazo` stay free text, promotion deferred to F33 | **held** — both declared `str`; no `Literal` anywhere in `models.py`. The one `Literal` in the touched surface is `ajustada`, an **INPUT** parameter predating DT-07, which D-09's lock does not reach because it is not a response field. |
| A failing shape guard **raises**; it never degrades to an empty list | **held** — `_parse_list_or_raise` raises `IOLAPIError`, pinned by `test_parse_get_historical_quotes_response_raises_on_non_list_body`. The one surviving empty-list path is the envelope missing its `titulos` key, which is not a shape failure and which D-06 preserves deliberately. |
| `puntas` is not declared as a collection of opaque dicts | **held** — declared `Punta \| None`, the singular model form, and asserted as such by `test_titulo_puntas_es_singular_no_una_lista`. |
| Divergence dedupe is never a process-lifetime module set | **held** — the per-response `DecodeScope` is the only mechanism; verified behaviorally (3 rows → 1 record) and structurally by the AST gate that rejects a module-level set literal in `_core.py`. |
| `_decode.py` and `uv.lock` untouched | **held** — `git diff --exit-code` clean on both at every task; `tools/check_decode_intactness.py` exits 0. |

## Issues Encountered

None. The one operational note carried from 30-01 still applies: `verification/test_with_options.py` takes ~12.5 minutes by nature and is not part of the per-package CI test job — it was not re-run here because nothing in this plan touches the retry/backoff surface.

## User Setup Required

None — no external service configuration required. Zero packages installed; `uv.lock` byte-identical.

## Next Phase Readiness

- **30-03 inherits `_parse_list_or_raise` ready to use.** The plan anticipated this: the helper is generic over `model_cls`, so a new list-shaped endpoint is one annotated one-liner plus its model.
- **The snapshot regeneration is now confirmed as a per-plan ritual**, not a one-off: it fired in 30-01 and again here, and will fire in 30-03/30-04 for the same reason.
- **Open by design (F33):** `Titulo`'s three never-observed field types (FA-02/A1) and the `Punta` element shape (FA-03) both remain unconfirmed, each documented at the site it constrains. The `cantidadOperaciones` int/float asymmetry is now pinned in **both** directions by tests — `Cotizacion` reports, `Titulo` widens silently — so a Phase 33 divergence there is legible as the asymmetry firing rather than as a defect.
- **No blockers.**

---
*Phase: 30-iol-client-tipado*
*Completed: 2026-08-20*

## Self-Check: PASSED

All modified source files exist on disk; all 5 task commits resolve in `git log`.
