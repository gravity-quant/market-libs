---
phase: 27-verificaci-n-en-vivo-segura-fixes
plan: 04
subsystem: verification-harness
tags: [verification, mutation, symbols, idempotency, ast-guard, driver, live]

# Dependency graph
requires:
  - phase: 27-verificaci-n-en-vivo-segura-fixes
    plan: 03
    provides: "the double gate threaded into the two existing constructors, MARKET_DATA_VERIFY_MUTATING, the seeded fid allocator, _MUTATING_SKIP_DETAIL and the two refusal probes"
  - phase: 27-verificaci-n-en-vivo-segura-fixes
    plan: 01
    provides: "max_existing_fid + the unknown-bullet-preserving serializer, without which every finding these probes emit would be silently discarded"
  - phase: 25-market-data-client-mutations
    provides: "_ensure_mutation_allowed, the three symbols write builders and the public create_symbol / create_symbols / update_symbol methods"
provides:
  - "_mutate_raw_sync / _mutate_raw_async — the only permitted mutation dispatch route from the driver; gate first, then _request, returning the materialised httpx.Response"
  - "_emit_cleanup_finding — a cleanup failure is itself a finding, never suppressed (D-08)"
  - "_skipped_when_gated — uniform, colon-free, probe-level SKIPPED for every destructive probe with the gate closed (D-03)"
  - "six stable GSDPROBE/-prefixed symbol identifiers, sync/async disjoint, bounding the permanent residue at exactly six rows"
  - "_discovered_symbol_ids registry — the row id is discovered from live evidence and threaded from the read probe to the revert probe (D-10)"
  - "eight symbols destructive probes (create -> confirm -> revert, both surfaces) judging idempotency by row count, not status code"
  - "two AST guards making gate bypass (T-27-20) and silent cleanup failure (T-27-23) unreintroducible"
affects: [27-05-calendar-cycle, 27-06-armed-run, 27-07-close-cycle]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Gated dispatch twin: the ungated raw helpers keep serving reads unchanged; a parallel _mutate_raw_* pair calls _ensure_mutation_allowed() first, and an AST taint-tracking guard proves no mutation-builder spec ever reaches the ungated pair"
    - "Row-count idempotency: the verdict is read back from the server (one row = dedupe, two or more = the idempotent=True flag is too permissive), never inferred from a status code that is only observable against a virgin symbol"
    - "Runtime id discovery over spec assumption: the row id is located by scanning the raw row's integer-valued keys with a deterministic precedence, and the finding on failure records key NAMES only"
    - "Cleanup-as-finding: contextlib.suppress stays legitimate for local transport teardown and is forbidden for cleanup of state created on shared infrastructure"

key-files:
  created:
    - verification/test_main_market_data_no_gate_bypass.py
    - verification/test_main_market_data_cleanup_emits_finding.py
  modified:
    - main_market_data.py

status: complete
---

# Phase 27 Plan 04: Symbols destructive cycle Summary

The repo's first destructive live probes — eight symbols `create -> confirm -> revert` probes on
both surfaces, behind gate-checked dispatch plumbing designed here rather than copied, with the
idempotency experiment folded into the same sequence. **Nothing in this plan ran against develop
as a mutation: the gate stayed closed for every run and all eight probes reported a probe-level
skip.**

## Tasks completed

| # | Task | Commit |
|---|------|--------|
| 1 | Gate-checked dispatch, identifiers, cleanup-finding helper, two AST guards | `98ba5b8` |
| 2 | Four sync probes: create -> confirm -> revert with id discovery and row-count idempotency | `bd5bc8b` |
| 3 | The four async mirrors | `95c7648` |

## What shipped

### The two traps, closed

**Trap 1 — gate bypass (Pitfall 4 / T-27-20).** `_raw_via_request_sync` / `_raw_via_request_async`
call `client._request(spec)` directly, and `_request` never calls `_ensure_mutation_allowed()` —
confirmed by reading `client.py:339-395` rather than taken on trust. Routing a mutation spec
through them would fire a real write with the gate possibly closed, against whatever host.
`_mutate_raw_sync` / `_mutate_raw_async` are the parallel pair: `_ensure_mutation_allowed()` is
the literal first statement, exactly as in every public mutating method, and only then `_request`.
They return the **materialised `httpx.Response`** rather than decoded JSON, which is what lets one
round trip serve the D-19 status evidence, the D-10 id discovery, the snapshot body and the D-11
parser evidence simultaneously.

`verification/test_main_market_data_no_gate_bypass.py` walks the driver AST and asserts, per
function, that no argument to an ungated helper derives from a mutation builder — **including via a
local variable** (two-pass taint tracking over `spec = build_x(...)` and then `other = spec`), not
only by direct nesting. It also asserts positively that both gated helpers exist and that
`_ensure_mutation_allowed` appears at a lower line number than `_request` inside each. The eight
mutation builders it watches include the five calendar-write builders plan 27-05 will use, so that
wave is covered without having to remember to widen the guard.

**Trap 2 — silent cleanup failure (D-08 / T-27-23).**
`verification/test_main_market_data_cleanup_emits_finding.py` asserts that every `finally` owned by
a mutation probe (a) contains a call to `_emit_cleanup_finding` or `append_finding`, (b) contains
no error-swallowing context manager, and (c) wraps the cleanup in its own `try/except` so a failed
revert does not escape the probe and skip its D-09 ladder. The driver's two pre-existing teardowns
(`client.close()`, `await aclient.aclose()`) keep their `contextlib.suppress` idiom — they close a
local socket and leave no orphaned remote state; that distinction is written into the guard's
docstring so it is not "fixed" later.

Both guards assert their own non-vacuity: the bypass guard requires that mutation builders and
ungated helpers are actually invoked in the driver, and the cleanup guard requires that its name
pattern matched at least one `probe_*`, that at least one matched probe has a `finally`, and that
`_emit_cleanup_finding` exists. A rename or a typo turns them RED instead of green-and-blind.

### Identifiers and residue (D-05)

There is **no `DELETE /symbols`** in the live spec — the row stays referenced by `market_data` — so
the only revert is `PATCH active=false` and every identifier leaves one permanently inactive row in
develop's catalogue, forever. The identifiers are therefore **stable, not timestamped**: a
`GSDPROBE/<timestamp>` would leave a new permanent row per run, while the six fixed ones cap the
residue at exactly six rows and keep the cycle re-runnable (a re-POST is a documented reactivation,
not a conflict).

```
_PROBE_PREFIX  = "GSDPROBE/"
_SYM_SYNC      = "GSDPROBE/P27-SYNC"        _SYM_ASYNC      = "GSDPROBE/P27-ASYNC"
_SYM_SYNC_B1   = "GSDPROBE/P27-SYNC-B1"     _SYM_ASYNC_B1   = "GSDPROBE/P27-ASYNC-B1"
_SYM_SYNC_B2   = "GSDPROBE/P27-SYNC-B2"     _SYM_ASYNC_B2   = "GSDPROBE/P27-ASYNC-B2"
```

Written as **full literals rather than f-strings over the prefix**, deliberately: the whole point of
a dedicated prefix is that the residue is greppable, and a derived constant would make
`grep GSDPROBE/` find one line instead of seven. A fourth test in the bypass guard file locks the
invariant — prefix value, all six present as module-level string literals, all prefixed, all
distinct, and sync ∩ async = ∅ (so a failure on one surface cannot contaminate the other's row
count).

### Probe names registered

Sync (in `main()`): `create_symbol_sync`, `symbols_after_create_sync`, `create_symbols_batch_sync`,
`update_symbol_sync`.
Async (in `_async_main`): `create_symbol_async`, `symbols_after_create_async`,
`create_symbols_batch_async`, `update_symbol_async`.

### Snapshot `client_function` identifiers (files land on the armed run, 27-06)

Under `.planning/verification/schemas/market-data-client/`, one file per identifier, distinct per
surface so a sync and an async mutation body can never overwrite each other's baseline:

| `client_function` | File written in 27-06 |
|---|---|
| `create_symbol_sync_response` | `create-symbol-sync-response.json` |
| `get_symbols_probe_prefix_sync` | `get-symbols-probe-prefix-sync.json` |
| `create_symbols_batch_sync_response` | `create-symbols-batch-sync-response.json` |
| `update_symbol_sync_response` | `update-symbol-sync-response.json` |
| `create_symbol_async_response` | `create-symbol-async-response.json` |
| `get_symbols_probe_prefix_async` | `get-symbols-probe-prefix-async.json` |
| `create_symbols_batch_async_response` | `create-symbols-batch-async-response.json` |
| `update_symbol_async_response` | `update-symbol-async-response.json` |

The two `get_symbols_probe_prefix_*` names exist so the **prefix-filtered** read never overwrites or
drifts the unfiltered `get-symbols.json` baseline (D-17). Note the unfiltered baseline is still
`"schema": []` and *will* drift once six inactive rows exist — that is Pitfall 2, expected, and is
27-05/27-07's problem, not this plan's.

### Id discovery strategy (what 27-06 should expect as evidence)

`Symbol` declares no id field and the live spec types `symbol_id` as an **integer** while the client
types it `str`, so nothing is assumed. `_discover_row_id(row)` scans the **raw** row's items for
values that are `int` and **not** `bool` (Python's `bool` is an `int` subclass — an `active: true`
would otherwise be mistaken for an id), then picks with this deterministic precedence:

1. the exact key `id`;
2. the first key ending in `id`, case-insensitive, in wire order;
3. otherwise the first integer-valued key, in wire order.

It returns `(key_name, value)`. The read probe records the **key name** in the probe detail and
stores the value in `_discovered_symbol_ids[<identifier>]`; the revert probe consumes it. If no
integer key exists at all, the probe emits an `ERROR-MAP` OPEN finding whose `actual` is
`sorted(row.keys())` — **key names only, never values** (T-27-24). If the registry is empty when the
revert probe runs, it emits a finding rather than guessing an id: a `PATCH` on an invented id would
touch somebody else's row in develop.

So 27-06 should expect, per surface, either a `PASS` detail of the form
`1 fila; id descubierto en clave 'id' (prefijo devolvió N filas)` — which pins down the real key
name — or the key-name-only finding.

### Idempotency observable

The verdict is the **row count read back from the server**, never a status code: the 201 -> 200
transition is only observable against a virgin symbol, so a status-based experiment is not
reproducible. One row = the server deduped; two or more = the double fire duplicated state and
`idempotent=True` on the builder is too permissive, which is a data-safety bug — an `ERROR-MAP` OPEN
finding is emitted naming `build_create_symbol_request` / `build_create_symbols_request` (the flag
itself is corrected in 27-07, D-20). The batch probe reports per-identifier counts and distinguishes
`duplicados` from `ausentes`.

### D-11 evidence captured, not fixed

`_core.parse_symbols_response` iterates the response body directly. Against a mutation response that
is a bare JSON object it yields one all-default `Symbol` per JSON **key**. `_describe_symbols_misparse`
runs the parser on the *same* `httpx.Response` the raw body came from and records that signature
alongside the snapshot. Per the plan this is evidence for 27-07, deliberately not repaired here.

### Probe ordering

Every read probe and its snapshot runs before any mutation. The develop ingestor repolls the symbol
catalogue and an unknown active symbol surfaces as `last_error` in `/health/feed` (Pitfall 3), so a
read that ran after a mutation could permanently drift a health baseline. The async read sweep lives
inside `_async_main`, which `main()` invokes mid-body — so the sync destructive block is registered
**after** `asyncio.run(_async_main(...))` (see Deviation 3).

## Verification

- `verification/test_main_market_data_no_gate_bypass.py` + `..._cleanup_emits_finding.py` +
  `..._postprocess_guarded.py` + `..._uses_single_client_instance.py` + `..._skip_line_shape.py`
  → **14 passed**. All post-processing still inside `try` bodies, still **exactly 2** ctor sites.
- `verification/test_cycle_closure_market_data.py`, `test_mutation_gate_parametrized.py`,
  `test_findings_fid_seed.py`, `test_findings_append_only.py` alongside the five above →
  **54 passed**.
- `packages/market-data-client/tests` → **344 passed**.
- `ruff check .` → all checks passed. `ruff format --check .` → 199 files already formatted.
  `mypy main_market_data.py packages/market-data-client/src` → no issues, 12 source files.
- Plan AST acceptance one-liners, all exit 0: the four new helpers exist and both `_mutate_raw_*`
  contain `_ensure_mutation_allowed`; `_discovered_symbol_ids` is a module-level `AnnAssign`;
  full sync/async parity across all four probe families; exactly 2 `Client`/`AsyncClient` ctor
  sites. `grep -c 'GSDPROBE/' main_market_data.py` → **11** (floor was 6).

### Gate-off run

Credentials are present (`packages/market-data-client/.env` carries the four Auth0 vars and
`load_dotenv()` resolves it from the package module's own directory), so this was a genuine live
**read** sweep against develop — exactly as in 27-03. `MARKET_DATA_VERIFY_MUTATING` is set nowhere
in the environment or in any `.env`, so the gate was closed and **zero mutations were dispatched**.
The first output line was the colon-less `SKIPPED (mutating, guard off)`; exit code **0**.

All eight destructive probes reported the probe-level skip verbatim:

```
PROBE create_symbol_async: SKIPPED (mutating, guard off)
PROBE symbols_after_create_async: SKIPPED (mutating, guard off)
PROBE create_symbols_batch_async: SKIPPED (mutating, guard off)
PROBE update_symbol_async: SKIPPED (mutating, guard off)
PROBE create_symbol_sync: SKIPPED (mutating, guard off)
PROBE symbols_after_create_sync: SKIPPED (mutating, guard off)
PROBE create_symbols_batch_sync: SKIPPED (mutating, guard off)
PROBE update_symbol_sync: SKIPPED (mutating, guard off)
PROBE cycle_closure: PASS 34 CONFIRMED/FIXED con regresión
```

**`SUMMARY:` line verbatim:**

```
SUMMARY: PASS=21 FAIL=0 SKIPPED=8 FINDING=2
```

`SKIPPED` is exactly 8 higher than the 27-03 baseline (`SKIPPED=0`), i.e. one per destructive probe
and no collateral skip. The read sweep completed unchanged.

**Findings-file hygiene.** Both smoke runs (after task 2 and after task 3) rewrote
`.planning/verification/market-data-client-findings.md` with the usual re-serialisation reflow plus
the ART timestamp. Before reverting, the 27-01 prose-preservation invariant was checked and held
both times — `Classification:` **36**, `Resolution:` **34**, `Regression:` **34**. Each run was then
reverted with `git checkout -- <that one file>`; the file is byte-identical to its base state
(sha256 `5fadf738…22ef6`, verified after each revert). `git status` showed no untracked files, so no
schema snapshot was created or overwritten. This plan is code-only; the findings corpus belongs to
the armed run in **27-06**.

## Deviations from Plan

**1. [Plan-ordering / TDD] Task 1's two AST guards were committed RED on their three non-vacuity assertions.**
- **Issue:** Task 1's action spec requires the cleanup guard to "assert the guard itself is
  non-vacuous by requiring it to have matched at least one probe", but the probes it must match do
  not exist until Task 2. The same applies to the bypass guard's requirement that a mutation builder
  actually be invoked. Task 1's acceptance criterion ("`pytest <both files>` exits 0") is therefore
  inconsistent with its own action spec.
- **Resolution:** honoured the action spec — the guards are genuinely non-vacuous — and accepted a
  deliberate RED at Task 1: `3 failed, 5 passed`, the three failures being exactly the non-vacuity
  assertions. Task 2 turned all eight green (`14 passed` with the pre-existing guards). This is the
  RED -> GREEN shape 27-01 and 27-03 already use; the commit message records it explicitly. A guard
  weakened to pass at Task 1 would have been the fabricated-green outcome the phase context warns
  about.

**2. [Rule 2 — missing critical functionality] The batch probes gained a cleanup `finally`.**
- **Issue:** the plan specifies a revert only for `probe_update_symbol_*`, i.e. only for
  `_SYM_SYNC` / `_SYM_ASYNC`. The four batch identifiers would have been left **permanently
  ACTIVE** in develop's catalogue. That contradicts the plan's own threat register (T-27-04
  mitigation: "all ending `active=false`") and walks straight into Pitfall 3 — an unknown active
  symbol is rejected by the feed and surfaces as `last_error` in the ingestor status on every
  subsequent run, forever.
- **Fix:** `probe_create_symbols_batch_sync` / `_async` deactivate both batch identifiers in a
  `finally`, using the ids discovered from the same read-back, routing any failure through
  `_emit_cleanup_finding`. Under the AST guard these are the second and third checked `finally`
  blocks, so the mechanism is locked, not just present.
- **Files:** `main_market_data.py`. **Commits:** `bd5bc8b`, `95c7648`.

**3. [Ordering] The sync destructive block is registered after `asyncio.run(_async_main(...))`, not immediately after the sync refusal probe.**
- **Issue:** the plan says "after the read sweep and after the refusal probe … Order is load-bearing:
  every read probe and its snapshot must run before any mutation." The **async** read sweep lives
  inside `_async_main`, which `main()` invokes in the middle of its body. Registering the sync
  mutations right after the sync refusal probe would have put four writes *before* the entire async
  read sweep — violating the stated invariant while satisfying the literal position.
- **Resolution:** followed the stated reason. Final order is sync reads -> sync refusal -> async
  reads -> async refusal -> async mutations -> sync mutations -> parity -> terminals. Every read and
  every read snapshot precedes every mutation, and the destructive block still sits before the
  terminal cycle-closure probe as required. The relative order *within* each surface is exactly the
  plan's.

**4. [Rule 3 — helpers extracted] Five small helpers instead of pasted logic.**
`_gate_open` (one reading of the gate boolean for all eight probes), `_discover_row_id`,
`_describe_symbols_misparse`, `_prefixed_rows` (thin, self-documenting wrapper over the existing
`_unwrap_rows`) and `_count_symbol_rows`. Each would otherwise have been duplicated four to eight
times across the two surfaces. None is a post-processing helper in the sense the D-09 AST guard
tracks, so its floor is unaffected — the guard's guarded-call count rose from 22 to 28.

**5. [Interpretation] "Both status codes" is recorded as `public_rows=N refire_status=NNN`.**
The plan asks each create/patch probe to "record both status codes". Fire 1 goes through the
**public** method (which is what ROADMAP criterion 1 asks for) and the public method returns parsed
rows, not a status — the status is structurally unavailable without either a third write or
bypassing the public surface. The detail therefore records the public fire's row count and the
gate-checked re-fire's status code. The idempotency verdict does not depend on either, by design.

**6. [Correctness] `_skipped_when_gated` returns the detail `"(mutating, guard off)"`, not `_MUTATING_SKIP_DETAIL`.**
27-03 declared `_MUTATING_SKIP_DETAIL = "SKIPPED (mutating, guard off)"` as "the exact string 27-04's
probes must emit". But the driver's print loop renders `f"PROBE {name}: {status} {detail}"`, so
using that constant as the *detail* would print `SKIPPED SKIPPED (mutating, guard off)`. The constant
is the whole rendered tail; the detail is its remainder after the status. The observed line is
`PROBE create_symbol_sync: SKIPPED (mutating, guard off)`, matching the plan's acceptance criterion
verbatim. `_MUTATING_SKIP_DETAIL` is untouched and its shape guard still passes.

No architectural changes; no Rule 4 checkpoints; no packages installed; `uv.lock` untouched.

## Threat model

All five `mitigate` dispositions are implemented: T-27-20 (gated dispatch + AST guard),
T-27-04 (stable prefixed identifiers, six rows, server-side `prefix` sweepable),
T-27-22 (row-count verdict + finding naming the builder), T-27-23 (`_emit_cleanup_finding` +
AST guard), T-27-24 (key names only in the discovery finding; snapshots go through `schema_of`;
all output through `safe_print`), T-27-25 (every probe keeps its `except Exception` D-09 ladder;
the gate-off run exited 0). T-27-21 (no `DELETE /symbols`) stays **accepted** and is documented
above. T-27-SC: no packages installed.

No new security surface beyond the plan's threat model — no new endpoints, no new auth paths, no
new file access patterns. No **Threat Flags**.

## Known Stubs

None. No hardcoded empty values, placeholders or unwired data paths were introduced. The eight
probes are fully wired and inert only because the gate is closed, which is the intended state until
27-06 arms it.

## Deferred / not mine

The 19 failures + 19 errors in `verification/` from Phase-15 matriz signature drift
(`test_main_matriz_login_fail_uniformity.py`, `test_matriz_sweep_snapshot.py`) and the
worktree-only failure of `test_phase06_nyquist_gaps.py::test_snapshot_regen_is_idempotent` are
unchanged and pre-existing at the base SHA — independently established by 27-01, 27-02 and 27-03 and
recorded in `deferred-items.md`. Nothing in this plan touches matriz or the snapshot regen script.
Per the executor budget, the full `verification/` sweep (~13 min, dominated by a real-sleeping retry
test) was not re-run; the nine directly relevant files were run instead and are green.

`get-symbols.json`'s baseline will drift on the first armed run, once six inactive rows exist. That
is Pitfall 2, expected, and belongs to 27-05/27-07.

## Requirement

`LIVE-MUT-01` — advanced, not satisfied. This plan delivers ROADMAP criteria 1, 2 and 3 for the
**symbols** surface: exercised behind the gate, with dedicated identifiers and a completed
create -> confirm -> revert cycle, and with the assumed idempotency (DM-03) instrumented to be
decided by measured live behaviour rather than spec prose. The calendar surface is 27-05, the armed
run is 27-06, and the requirement is marked complete only after 27-07.

## Self-Check: PASSED

- `main_market_data.py` — FOUND (contains `_mutate_raw_sync`, `_mutate_raw_async`,
  `_emit_cleanup_finding`, `_skipped_when_gated`, `_discovered_symbol_ids`, `GSDPROBE/` ×11, and
  all eight `probe_*` names)
- `verification/test_main_market_data_no_gate_bypass.py` — FOUND
- `verification/test_main_market_data_cleanup_emits_finding.py` — FOUND
- Commits `98ba5b8`, `bd5bc8b`, `95c7648` — all present in `git log`
- `.planning/verification/market-data-client-findings.md` — byte-identical to base
  (sha256 `5fadf738d059437b9030f92e6f2d87ac8f52bf40da4b3c12741fe5d8e8e22ef6`)
- `STATE.md` / `ROADMAP.md` — not modified (orchestrator-owned)
