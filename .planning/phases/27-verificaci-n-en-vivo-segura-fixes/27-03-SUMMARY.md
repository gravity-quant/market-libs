---
phase: 27-verificaci-n-en-vivo-segura-fixes
plan: 03
subsystem: verification-harness
tags: [verification, mutation-gate, security, ast-guard, driver, tdd, pytest]

# Dependency graph
requires:
  - phase: 27-verificaci-n-en-vivo-segura-fixes
    plan: 01
    provides: "max_existing_fid(pkg) for the seeded allocator, and the backfill that takes verify_cycle_closure('market-data-client') to (True, [])"
  - phase: 27-verificaci-n-en-vivo-segura-fixes
    plan: 02
    provides: "the reconciled CalendarDay the newly-working calendar SHAPE-diff lines up against"
  - phase: 25-market-data-client-mutations
    provides: "the in-package refuse-by-default gate (_ensure_mutation_allowed) and the mutating_allowed/expected_host constructor kwargs"
provides:
  - "mutating_allowed_for(env_var, base_url, expected_host) — package-agnostic double gate; both legs real, exact-hostname only, fail-closed"
  - "main_market_data.py computes the gate once and threads it through the two existing constructors with an explicit expected_host"
  - "seeded fid allocator (starts above the highest recorded finding) so emitted findings are no longer silently swallowed"
  - "cycle_closure terminal probe reporting PASS, hardened against a vacuous pass"
  - "HTTP-free refuse-by-default probes on both surfaces"
  - "source-level guard that no driver output line can classify the package as SKIPPED"
affects: [27-04-symbols-cycle, 27-05-calendar-cycle, 27-06-armed-run, 27-07-close-cycle]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Gate parametrization over gate duplication: one pure decision function receives (env var name, resolved base URL, expected host); no client package is imported, so no driver can inherit another package's vacuous host leg"
    - "Gate-before-client: the base URL is resolved with _env_base_url() (a plain function) so the gate is evaluable before any client exists — the AST single-instance guard stays at exactly 2 ctor sites"
    - "Refusal probes as non-vacuity: two HTTP-free probes run identically armed or disarmed, so a gate-off run still proves something"
    - "Output-shape guards: a test imports the classifier regex from main_verify and renders every driver print site with a hostile placeholder"

key-files:
  created:
    - verification/test_mutation_gate_parametrized.py
    - verification/test_main_market_data_skip_line_shape.py
  modified:
    - verification/mutation_gate.py
    - main_market_data.py

status: complete
---

# Phase 27 Plan 03: Driver mutation gate + harness wiring Summary

Package-agnostic double gate (exact env opt-in AND exact develop hostname) threaded through the
market-data driver's two existing constructors, plus the seeded fid allocator, the cycle-closure
terminal probe, HTTP-free refuse-by-default probes and a source-level guard on output shape — the
gate ships **closed**; no destructive probe was added.

## Tasks completed

| # | Task | Commits |
|---|------|---------|
| 1 | Package-agnostic parametrized mutation gate (D-01) | `53ac203` (RED) → `63af080` (GREEN) |
| 2 | Driver gate, seeded allocator, cycle-closure probe, D-06 EXPECTED finding, calendar unwrap | `d77d443` |
| 3 | Gate-refusal probes + skip-line shape guard (D-03/D-04) | `99cd77f` |

Task 1 was TDD and committed a genuine failing RED (`ImportError: cannot import name
'mutating_allowed_for'`) before GREEN.

## What shipped

### D-01 — the gate that actually has two legs

`verification/mutation_gate.py` gains
`mutating_allowed_for(*, env_var, base_url, expected_host) -> bool`. Leg one: the env var must
equal the literal `"1"`. Leg two: `urlsplit(base_url).hostname` must **equal** `expected_host` —
never `in`, never `endswith`. It imports no client package, which is the whole point: the old
`mutating_allowed()` validates *matriz's* `_base_url`, so calling it from the market-data driver
would have left the env flag as the only real leg.

`mutating_allowed()` is now a thin wrapper that keeps its matriz-specific parts (the lazy
`import matriz_client`, the live `_base_url` read, `_SANDBOX_HOST`) and delegates the decision.
The env leg is still evaluated **before** the client import, so a driver without `matriz_client`
installed refuses cleanly instead of raising. Its signature, printed output and return values are
unchanged — the 5 pre-existing ambito back-compat tests pass verbatim, unmodified.

The refusal line is hoisted into the module constant **`_SKIP_LINE`** (`"SKIPPED (mutating, guard
off)"`), shared by both functions so they cannot drift.

### D-02/D-16 — the driver

- **Env var name: `MARKET_DATA_VERIFY_MUTATING`** (module constant `_MUTATING_ENV_VAR`), scoped to
  market-data deliberately: `main_verify.py` runs all six drivers in one batch, so reusing matriz's
  `VERIFY_MUTATING` would arm two gates at once.
- **Expected host: `market-data-develop.bbsa.com.ar`** (module constant `_EXPECTED_DEVELOP_HOST`).
- The gate is computed **once** in `main()` from `_env_base_url()` — a plain function, not a client
  construction — and threaded into the two **existing** ctor sites as
  `mutating_allowed=<gate>, expected_host=_EXPECTED_DEVELOP_HOST`. `_async_main` gained the boolean
  parameter (was zero-arg). No third constructor; `configure()` was not used.
- `_seed_fid_counter()` assigns `max_existing_fid(_PKG)` to the module counter, called in `main()`
  right after `write_findings(_PKG)` and before any client construction. **The allocator seeded from
  36, so the first fid this run allocated was `F-37`** — previously the driver reset to 0 and every
  finding collided with the promoted F-01…F-36 corpus and was silently discarded.
- `probe_cycle_closure` calls `verify_cycle_closure(_PKG)` as the last registered probe. Hardened
  against the vacuous pass: `verify_cycle_closure` also returns `(True, [])` when the file is absent
  or holds nothing promoted, so the probe additionally requires ≥1 `CONFIRMED`/`FIXED` block and
  reports `FAIL` otherwise.
- `probe_expected_put_config_operator_gated` emits the D-06 EXPECTED finding with
  `idempotent_by_title=True` (so it does not duplicate under a new fid every run), recording that
  `PUT`/`DELETE /calendar/config` stay operator-gated out of the live run: the DELETE resets to
  server defaults rather than restoring a prior value, so it cannot serve as cleanup for a PUT, and
  a real PUT would clobber shared develop config. Both endpoints stay covered by mocked tests.
- **Calendar SHAPE-diff fixed.** The wire body is the `{config, coverage, days[], market}` envelope,
  so `raw_days[0] if isinstance(raw_days, list)` always yielded `None` and the `CalendarDay`
  SHAPE-diff had **never run**. A shared `_unwrap_rows(raw, key)` helper now unwraps `days`
  (bare-list path kept for compatibility) in both surfaces. First real run of that diff produced
  **zero** CalendarDay findings — i.e. 27-02's reconciliation holds against the live wire.

### D-03/D-04 — refusal probes and output shape

- `probe_mutation_gate_refusal_sync` / `probe_mutation_gate_refusal_async` force
  `_state.mutating_allowed = False` (the in-package test precedent — neither a constructor nor
  `configure()`), attempt one mutation through a **public** method, expect
  `MarketDataMutationNotAllowedError`, and restore the previous flag in a `finally`. If no exception
  is raised they emit an `AUTH` OPEN finding and return `FINDING`. The `except Exception as exc:
  # D-09` ladder stays outermost.
  - **Probe vehicle: `preview_calendar_config`.** It is on the gated mutation surface but is a
    compute-only dry run that persists nothing server-side, so if the gate ever failed to refuse the
    worst case is an inert POST rather than a real write against shared develop config.
  - Both probes are HTTP-free and run identically armed or disarmed — they are what makes a
    gate-off run non-vacuous. Registered before the destructive probes 27-04 will add.
- `verification/test_main_market_data_skip_line_shape.py` imports `_ENV_SKIP` from `main_verify`
  (rather than re-declaring it, so the guard tracks the classifier), renders **every** `print` /
  `safe_print` call site in the driver with a hostile `"SKIPPED evil: pwned"` placeholder in each
  f-string hole, and asserts no resulting line matches. It also asserts the probe-level skip detail
  is colon-free, that `PROBE `-prefixed lines are immune by construction (with a positive control so
  the guard is non-vacuous), and that `main()`'s only `sys.exit` is inside the `require_env` guard —
  a gate-off run must continue into the read sweep.
- `_MUTATING_SKIP_DETAIL = "SKIPPED (mutating, guard off)"` is now declared in the driver as the
  exact colon-free string plan 27-04's mutation probes must emit; the guard asserts its shape.

## Artifacts

**New public symbol:** `verification.mutation_gate.mutating_allowed_for`
**New refusal-line constant:** `verification.mutation_gate._SKIP_LINE`
**New driver constants:** `_EXPECTED_DEVELOP_HOST`, `_MUTATING_ENV_VAR`, `_MUTATING_SKIP_DETAIL`,
`_CLOSED_STATUS_RE`, `_REFUSAL_PROBE_CONFIG`
**New driver functions:** `_seed_fid_counter`, `_unwrap_rows`, `probe_cycle_closure`,
`probe_expected_put_config_operator_gated`, `probe_mutation_gate_refusal_sync`,
`probe_mutation_gate_refusal_async`
**Probe names registered** (27-04 extends this list): `mutation_gate_refusal_sync`,
`mutation_gate_refusal_async`, `expected_put_config_operator_gated`, `cycle_closure`
**Changed signature:** `_async_main(mutating: bool)` (was zero-arg)
**No new dependencies.** `uv.lock` untouched.

## Verification

- `verification/test_mutation_gate_parametrized.py` + `packages/ambito-financiero-client/tests/test_harness_mutation_gate.py` → **28 passed** (23 new + the 5 back-compat, unmodified).
- The plan's inline gate acceptance one-liner (7 adversarial hosts, 3 malformed URLs, 4 non-`"1"` env values, the unset case, and the explicit-port positive) → exits 0.
- `verification/test_main_market_data_skip_line_shape.py` → 4 passed.
- The four driver/harness guards (`..._uses_single_client_instance`, `..._postprocess_guarded`, `test_cycle_closure_market_data`, `test_mutation_gate_parametrized`) → 27 passed.
- AST acceptance: exactly **2** `Client`/`AsyncClient` ctor sites, both carrying `mutating_allowed` **and** `expected_host`; `_async_main` takes exactly 1 arg; all six new function names present.
- `packages/market-data-client/tests` → **344 passed**.
- `ruff check .` → all checks passed. `ruff format --check .` → 197 files already formatted. `mypy packages/market-data-client/src main_market_data.py` → no issues (12 source files).
- **Two-leg composition proven end-to-end through the driver's own constants:** with
  `MARKET_DATA_VERIFY_MUTATING=1` and `MARKET_DATA_BASE_URL` pointed at the superstring host
  `https://market-data-develop.bbsa.com.ar.attacker.example/api` the gate printed the refusal line
  and returned `False`; with the same flag and the default develop base URL it returned `True`.

### Gate-off smoke run

Credentials turned out to be present (a `.env` above the worktree), so the driver ran a **real read
sweep** against develop. The gate stayed off — the first output line was the colon-less
`SKIPPED (mutating, guard off)` — and no mutation was attempted. Exit code **0**. Both refusal
probes and the cycle-closure probe reported PASS:

```
PROBE mutation_gate_refusal_sync: PASS mutación rechazada sin opt-in (0 HTTP, 0 Auth0)
PROBE mutation_gate_refusal_async: PASS mutación rechazada sin opt-in (0 HTTP, 0 Auth0)
PROBE expected_put_config_operator_gated: PASS F-41 (EXPECTED, dedupe by title)
PROBE cycle_closure: PASS 34 CONFIRMED/FIXED con regresión
```

**SUMMARY line verbatim:**

```
SUMMARY: PASS=21 FAIL=0 SKIPPED=0 FINDING=2
```

The run also confirmed D-03 empirically: the colon-less gate line did **not** trip `main_verify.py`'s
`^SKIPPED \S.*:` classifier, and the read sweep completed all 23 probes.

## Deviations from Plan

**1. [Rule 2 — missing critical functionality] `urlsplit` `ValueError` is caught in `mutating_allowed_for`**
- **Found during:** Task 1.
- **Issue:** the plan specified fail-closed only for `hostname is None`. `urlsplit` *raises*
  `ValueError` on some malformed inputs (unmatched IPv6 bracket, e.g. `https://[oops/api`), which
  would have propagated out of the gate and crashed the driver instead of refusing.
- **Fix:** the parse is wrapped in `try/except ValueError` → print the refusal line, return `False`.
  A parametrized case (`unmatched-ipv6-bracket`) locks it.
- **Files modified:** `verification/mutation_gate.py`, `verification/test_mutation_gate_parametrized.py`.
- **Commit:** `63af080`.

**2. [Scope decision] The smoke run's `.planning/verification/market-data-client-findings.md` churn was reverted, not committed**
- **Found during:** Task 2 smoke run.
- **Issue:** credentials were unexpectedly available, so the "gate-off smoke run" was a genuine live
  read sweep. It rewrote the findings file (+118/−109, mostly re-serialization reflow plus the ART
  timestamp) and appended F-37…F-41.
- **Decision:** reverted with `git checkout -- <that one file>`. This plan is code-only; the armed
  live run and its findings corpus belong to **27-06**. Committing run-specific, live-data-dependent
  churn from a wave-2 plan would have created merge noise across the parallel wave for no gain —
  every one of those findings regenerates in 27-06, and the D-06 EXPECTED terminal is
  `idempotent_by_title=True` so it re-emits at whatever fid is free.
- **Checked before reverting:** the prose-preservation invariant from 27-01 held — `Classification:`
  36, `Resolution:` 34, `Regression:` 34, identical before and after. No schema snapshot files were
  created or overwritten (`git status` showed no untracked files).

**3. [Rule 3 — helper extracted] `_unwrap_rows(raw, key)`**
- The plan described the calendar unwrap inline. The identical `{envelope: rows[]}` shape already
  appeared twice for `items` in the market-data probes, so the unwrap was factored into one helper
  used by both keys on both surfaces rather than pasted a third and fourth time. Behaviour is
  unchanged for the `items` call sites; the post-process AST guard only tracks
  `_emit_shape`/`_write_schema_snapshot`, so its count is unaffected.

No architectural changes; no Rule 4 checkpoints; no packages installed.

## Deferred / not mine

The 19 failures + 19 errors in `verification/` from Phase-15 matriz signature drift
(`test_main_matriz_login_fail_uniformity.py`, `test_matriz_sweep_snapshot.py`) are unchanged and
**pre-existing at the base SHA** — independently established by both 27-01 and 27-02 and recorded in
`deferred-items.md`. Nothing in this plan touches matriz's driver or its tests.

The full `verification/` directory run was not completed inside budget (it is dominated by tests
that sleep for real and by driver subprocess sweeps). Every test file this plan created or could
affect was run directly and is green — see Verification above.

## Requirement

`LIVE-MUT-01` — advanced, not satisfied. This plan delivers ROADMAP criterion 1's **gating half**:
mutation is authorized only by an exact env opt-in plus an exact develop hostname, evaluated once
and threaded through the two existing constructors. The destructive probes that exercise the gate
land in 27-04/27-05 and the armed run in 27-06; the requirement is marked complete only after 27-07.

## Self-Check: PASSED

- `verification/mutation_gate.py` — FOUND (contains `def mutating_allowed_for`, `_SKIP_LINE`; `grep -c 'import matriz_client'` → 1)
- `verification/test_mutation_gate_parametrized.py` — FOUND
- `verification/test_main_market_data_skip_line_shape.py` — FOUND
- `main_market_data.py` — FOUND (contains `MARKET_DATA_VERIFY_MUTATING`, `mutating_allowed_for`, `max_existing_fid`, `verify_cycle_closure`, `_env_base_url`)
- Commits `53ac203`, `63af080`, `d77d443`, `99cd77f` — all present in `git log`
