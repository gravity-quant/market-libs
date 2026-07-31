---
phase: 23-verificaci-n-en-vivo-contra-develop-fixes
verified: 2026-07-30T22:15:00Z
status: passed
score: 12/12 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 11/12
  gaps_closed:
    - "Every probe catches broad Exception and httpx.ConnectError so an unreachable develop or closed-market empty is classified NO-DATA/SKIP, never an uncaught crash that flips main_verify to FAILED (D-09)"
  gaps_remaining: []
  regressions: []
---

# Phase 23: Verificación en vivo contra develop + fixes Verification Report

**Phase Goal:** Ejercitar toda la superficie pública (sync + async) en vivo contra develop, detectar divergencias cliente-vs-servicio y corregirlas en el ciclo.
**Verified:** 2026-07-30T22:15:00Z
**Status:** passed
**Re-verification:** Yes — after gap closure (commit `2c8e040`)

## Context Note on the SKIP Path (unchanged from prior verification)

There is still no `.env` for `market-data-client` in this repository (only `.env.example`).
Running the driver live therefore legitimately takes the plan-anticipated `require_env`-SKIP /
D-09 NO-DATA path — confirmed again in this re-verification run (see Behavioral Spot-Checks
below). **A real live sweep against develop still awaits Auth0 credentials.** Success criteria 3
and 4 (documenting/fixing real divergences) remain unexercised by construction on this path; that
was already the plan-sanctioned outcome in the prior verification and is not itself a gap. What
*was* a gap — the D-09 never-FAILED contract being structurally unsafe the first time a live run
with real credentials actually executes probes — is what this re-verification confirms is now
closed.

## Gap-Closure Verification (CR-01 / D-09)

Independently re-verified against the actual code in `main_market_data.py` at commit `2c8e040`
(not taken on SUMMARY or commit-message faith):

1. **Every read probe now performs post-processing inside its `try` block.** Read the full
   994-line file directly. In `probe_health_sync`/`probe_health_async`,
   `probe_market_data_sync`/`_async`, `probe_latest_sync`/`_async`,
   `probe_instruments_sync`/`_async`, `probe_segments_sync`/`_async`,
   `probe_symbols_sync`/`_async`, and `probe_calendar_sync`/`_async`, the `_emit_shape(...)` and
   `_write_schema_snapshot(...)` calls now sit inside the `try` body, and the success
   `return ProbeResult(...)` is the last statement of that same `try`, falling through to a
   single `except Exception as exc: return _finding_for_exc(...)`. Confirmed line-by-line for
   every one of the 12 probe functions (6 pairs) named in the original CR-01 finding — no
   post-processing call remains after an `except` block anywhere in the file.
2. **`_write_schema_snapshot` now hardens the committed-baseline read.** Lines 201-220:
   `json.loads(schema_file.read_text(...))` is wrapped in `try: ... except (OSError,
   json.JSONDecodeError) as exc:`, which emits a `SHAPE` finding (`"baseline schema ilegible en
   {client_function}"`) and returns cleanly instead of raising — matches the CR-01 fix
   recommendation exactly, and additionally respects D-25 (never overwrites the baseline on this
   path).
3. **Defense-in-depth top-level guards added.** `main()` (lines 953-975) and `_async_main()`
   (lines 903-920) now each wrap their probe-orchestration body in `except Exception as exc:`
   that appends a `SKIPPED`/`driver_guard` or `async_guard` `ProbeResult` rather than letting the
   exception propagate — confirmed present and syntactically enclosing the entire probe-call
   sequence, not just a subset.
4. **New regression guard is real and non-vacuous.**
   `verification/test_main_market_data_postprocess_guarded.py` (94 lines) is an AST walk that:
   finds every `probe_*` function, computes the set of `Call` nodes lexically inside a `try`
   body, and asserts every `_emit_shape`/`_write_schema_snapshot` call site is in that set — with
   a `_MIN_GUARDED_CALLS = 10` floor so a gutted driver (helpers removed) fails red instead of
   passing trivially. Read the full file directly; the logic correctly excludes `except`/`else`/
   `finally` bodies from "protected" (a helper call in an `except` block would NOT be caught by
   the ladder it's inside — correctly excluded).

**Independent command verification (not re-stated from SUMMARY, executed fresh in this session):**

| Check | Command | Result |
|---|---|---|
| New regression guard passes | `uv run python -m pytest verification/test_main_market_data_postprocess_guarded.py -q` | 1 passed |
| Single-Client AST guard still passes | `uv run python -m pytest verification/test_main_market_data_uses_single_client_instance.py -q` | 1 passed |
| Driver clean-SKIP unaffected by fix | `uv run --package market-data-client python main_market_data.py` | `SKIPPED market-data-client: missing MARKET_DATA_CLIENT_ID, MARKET_DATA_CLIENT_SECRET, MARKET_DATA_AUDIENCE, MARKET_DATA_AUTH0_TOKEN_URL`, exit 0 |
| Aggregate runner classification | `uv run python main_verify.py` | `SKIPPED market-data-client` (RAN: 3, SKIPPED: 2, FAILED: 1 — the 1 FAILED is `matriz-client`, pre-existing, unrelated to this phase) |
| Cycle closure gate | `from verification.cycle_report import verify_cycle_closure; verify_cycle_closure("market-data-client")` | `(True, [])` |
| Ruff check | `uv run ruff check main_market_data.py verification/test_main_market_data_postprocess_guarded.py` | All checks passed |
| Ruff format | `uv run ruff format --check ...` | 2 files already formatted |
| Mypy strict | `uv run mypy main_market_data.py` | Success: no issues found |
| Debt markers | `grep -n -E "TBD\|FIXME\|XXX" main_market_data.py verification/test_main_market_data_postprocess_guarded.py` | none found |
| Package test suite (full, run once) | `uv run pytest -q packages/market-data-client/tests` | 134 passed |

**Conclusion: the D-09 gap is genuinely closed.** All 12 read probes (6 sync + 6 async) guard
their post-processing inside `try`, `_write_schema_snapshot` no longer raises on a corrupt
baseline, both `main()`/`_async_main()` have defense-in-depth catch-alls, and a non-vacuous AST
regression guard locks the invariant against future regressions.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `main_market_data.py` constructs exactly ONE `Client()` + ONE `AsyncClient()`, threaded into every probe; exercises health + market-data + reference reads (SC1/D-02) | ✓ VERIFIED | Re-confirmed: `client = Client()` (main_market_data.py:950), `aclient = AsyncClient()` (900), threaded as params. AST guard re-run: 1 passed. |
| 2 | Reuses `verification/` infra (require_env split, credential redaction); read-only, no mutating-gate (SC2) | ✓ VERIFIED | Imports unchanged: `require_env`, `safe_print`, `schema_of`, `write_findings`, `append_finding`, `diff_safemodel_bidirectional` all still imported and used; no mutating calls. |
| 3 | Driver gates on the four Auth0 vars via `require_env`; missing var → verbatim `SKIPPED market-data-client: missing ...` + `sys.exit(0)` (D-01) | ✓ VERIFIED | Re-ran driver directly: exact verbatim SKIP line, exit 0. |
| 4 | Every probe catches broad `Exception`/`httpx.ConnectError` so develop-unreachable/closed-market is classified NO-DATA/SKIP, **never** an uncaught crash flipping `main_verify` to FAILED (D-09) | ✓ VERIFIED | **Gap closed.** Direct source read confirms `_emit_shape`/`_write_schema_snapshot` now run inside every probe's `try`; `_write_schema_snapshot` catches `OSError`/`JSONDecodeError` on the baseline read; `main()`/`_async_main()` have top-level defense-in-depth catch-alls; new AST regression guard (`test_main_market_data_postprocess_guarded.py`) passes and is non-vacuous (floor of 10 guarded calls, actual driver has many more). |
| 5 | All 10 endpoint methods exercised on BOTH sync `Client` and async `AsyncClient` surfaces (D-03) | ✓ VERIFIED | Re-confirmed via grep: all 10 methods (`get_health`, `get_health_feed`, `get_market_data`, `get_latest`, `get_latest_batch`, `get_instruments`, `get_segments`, `get_symbols`, `get_calendar`, `get_calendar_config`) called ≥1 on both `client.` and `aclient.` |
| 6 | `main_verify.py._DRIVERS` contains the `market-data-client` tuple (D-08.2) | ✓ VERIFIED | `main_verify.py:34` — `("market-data-client", "main_market_data.py")` present, unchanged. |
| 7 | AST guard asserts `1 <= (Client\|AsyncClient) ctor calls <= 2` in `main_market_data.py` (D-08.1) | ✓ VERIFIED | Unchanged, re-run green. (WR-01 weak-bound observation carried forward as a non-blocking follow-up — see Anti-Patterns.) |
| 8 | Every client-vs-server divergence is documented in findings and fixed in-cycle, mirrored sync/async (SC3/D-06) | ✓ VERIFIED (vacuous) | Still no divergences surfaced (SKIP path). `git diff 9e26ecc..HEAD --stat` over `models.py`/`_core.py`/`tests/` still empty. Plan-sanctioned no-op. |
| 9 | Each CONFIRMED/FIXED finding links a mocked pytest-httpx regression via `Regression:` (D-07) | ✓ VERIFIED (vacuous) | No CONFIRMED/FIXED findings exist; requirement holds trivially, unchanged. |
| 10 | `verify_cycle_closure("market-data-client")` returns PASS (SC4) | ✓ VERIFIED | Re-ran directly (via `verification.cycle_report.verify_cycle_closure`) → `(True, [])`. |
| 11 | Any unmirrored shell (`_request`) change opens a `SYNC-ASYNC-DRIFT` finding (D-06 policy) | ✓ VERIFIED (vacuous) | No shell-level change made; confirmed empty diff on `client.py`/`aio.py`, unchanged. |
| 12 | New model fields additive; `received_at` never repurposed (D-05/D-06) | ✓ VERIFIED (vacuous) | No model changes made; confirmed empty diff on `models.py`, unchanged. |

**Score:** 12/12 truths verified (0 present-but-behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `main_market_data.py` | Live-verification driver: probe_* functions, ProbeResult, env-gate, SHAPE diff, schema snapshot, redacted output | ✓ VERIFIED | 994 lines. All functions present and wired; CR-01 defect fixed — post-processing now inside every probe's `try`. |
| `verification/test_main_market_data_uses_single_client_instance.py` | AST single-Client guard | ✓ VERIFIED | Present, passes green (unchanged by this fix). |
| `verification/test_main_market_data_postprocess_guarded.py` | AST D-09 post-processing guard (new, gap-closure artifact) | ✓ VERIFIED | 94 lines. Correctly walks `probe_*` functions, computes try-protected `Call` node set, asserts zero unguarded helper calls and a non-vacuous floor (`_MIN_GUARDED_CALLS = 10`). Passes green. |
| `main_verify.py` | Aggregate runner extended with market-data-client driver | ✓ VERIFIED | `_DRIVERS` includes the tuple, unchanged by this fix. Ran `uv run python main_verify.py` → classifies `market-data-client` as `SKIPPED` (never FAILED). |
| `.planning/verification/market-data-client-findings.md` | Bootstrapped findings file | ✓ VERIFIED | Exists with the standard bootstrap skeleton, unchanged. |
| `.planning/verification/schemas/market-data-client/` | Schema-snapshot dir (DRIFT-01) | ✓ VERIFIED | Directory exists with `.gitkeep`; unchanged — no live run has occurred yet. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `main_market_data.py` | `verification/env_gate.py` | `require_env("market-data-client", [...])` | ✓ WIRED | Unchanged, called at top of `main()`. |
| `main_market_data.py` | `verification/safemodel_diff.py` | `diff_safemodel_bidirectional(raw_item, Model)` | ✓ WIRED | Called from inside each probe's `try` now (previously called from outside — same call sites, now correctly enclosed). |
| `main_market_data.py` (probes) | `main_market_data.py` (`_write_schema_snapshot`) | direct call, now inside probe `try` | ✓ WIRED | Every one of the 12 read-probe call sites verified inside `try`; success `return` also inside `try`, single `except Exception` fallthrough per probe. |
| `main_verify.py` | `main_market_data.py` | `_DRIVERS` tuple | ✓ WIRED | Confirmed present; `_run_driver` invokes as subprocess, unchanged. |
| `.planning/verification/market-data-client-findings.md` | `packages/market-data-client/tests/` | `Regression:` field | N/A (vacuous) | No findings to link — no-op is correct for the SKIP path, unchanged. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Driver clean-SKIP on missing creds | `uv run --package market-data-client python main_market_data.py` | `SKIPPED market-data-client: missing MARKET_DATA_CLIENT_ID, ...`, exit 0 | ✓ PASS |
| D-09 post-process guard (new) | `uv run python -m pytest verification/test_main_market_data_postprocess_guarded.py -q` | 1 passed | ✓ PASS |
| AST single-Client guard | `uv run python -m pytest verification/test_main_market_data_uses_single_client_instance.py -q` | 1 passed | ✓ PASS |
| Cycle closure gate | `verify_cycle_closure("market-data-client")` | `(True, [])` | ✓ PASS |
| Aggregate runner classification | `uv run python main_verify.py` | `SKIPPED market-data-client` (RAN: 3, SKIPPED: 2, FAILED: 1 — `matriz-client` FAILED is pre-existing, unrelated to this phase) | ✓ PASS (for market-data-client) |
| Ruff / ruff format / mypy on changed files | as above | All clean | ✓ PASS |
| Full package test suite (run once) | `uv run pytest -q packages/market-data-client/tests` | 134 passed | ✓ PASS |
| Findings/schema-dir credential leak scan | `grep` for Bearer/client_secret/JWT | No hits; only `.gitkeep` under schemas dir | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| LIVE-MD-01 | 23-01-PLAN.md, 23-02-PLAN.md | Superficie pública completa ejercitada en vivo contra develop con Auth0; reutiliza `verification/`; divergencias documentadas y corregidas mirrored sync/async | ⚠️ PARTIALLY SATISFIED (apparatus complete and now safe) | The driver apparatus is complete, correct, and — as of this fix — structurally safe to run against real credentials (the D-09 never-FAILED contract now genuinely holds, not just on the SKIP path). What remains outstanding is unchanged from before: no live sweep against develop has actually executed (Auth0 credentials still absent from this repo), so criteria 3/4 (documenting/fixing real divergences) remain unexercised by construction — this was already the plan-sanctioned deferred state, not a new gap. REQUIREMENTS.md still lists LIVE-MD-01 as "Pending" (line 72), which is accurate pending that live run; this is a scheduling/credentials matter, not a code defect. |

No orphaned requirements: only LIVE-MD-01 is mapped to Phase 23 in REQUIREMENTS.md, and both plans declare it.

### Anti-Patterns Found (carried forward — WARNING-tier only, none blocking)

The CR-01 BLOCKER from the prior review/verification cycle is resolved and removed from this
table. The following five WARNING-tier code-review items remain from `23-REVIEW.md` and are
**not phase-goal blockers** — they do not affect whether the phase's success criteria or D-09
contract hold. Recorded here as follow-ups for a future pass:

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `verification/test_main_market_data_uses_single_client_instance.py` | 32, 53 | AST guard sums `Client`+`AsyncClient` into one count (`1<=total<=2`) instead of asserting exactly-1-each (WR-01) | ⚠️ WARNING (follow-up) | A driver constructing two `Client()` and zero `AsyncClient()` would pass the guard green. Not currently exploited. |
| `main_market_data.py` | 574-597, 818-841 | `probe_no_data_sync`/`_async` emit an OPEN finding on the *expected* empty-result happy path and silently PASS the anomalous non-empty case (WR-02) | ⚠️ WARNING (follow-up) | Inverted diagnostic logic: normal runs accumulate a permanent noise finding; a real filter bug would be silently missed. |
| `main_market_data.py` | 93-101 | `_next_fid()` is a per-process sequential counter; `append_finding` dedupes by fid and can silently discard a new divergence on fid collision (WR-03) | ⚠️ WARNING (follow-up) | Latent data-loss risk on future live runs; matches an existing codebase-wide convention. |
| `main_verify.py` | 61-66 | `subprocess.run(...)` has no `timeout=` (WR-04) | ⚠️ WARNING (follow-up) | A wedged/hanging driver would block the entire aggregate runner indefinitely. |
| `main_market_data.py` | 170-216 | `schema_of` samples only the first list element; market-variable payloads can legitimately differ row-to-row (WR-05) | ⚠️ WARNING (follow-up) | False-positive-prone SHAPE drift findings once live runs begin. |

No `TBD`/`FIXME`/`XXX` debt markers found in any file touched by the gap-closure commit
(`main_market_data.py`, `verification/test_main_market_data_postprocess_guarded.py`).

### Human Verification Required

None. All items above (both the gap-closure confirmation and the carried-forward WARNING items)
are resolvable by static analysis and command execution; no visual, real-time, or subjective-
quality checks are needed. A real live-credentialed sweep against develop remains a standing
prerequisite-blocked item (Auth0 creds), not a human-verification item — it is a scheduling
dependency, not something that needs subjective judgment once credentials are available.

### Gaps Summary

No gaps remain. The single BLOCKER from the prior verification cycle (CR-01 / D-09
never-FAILED contract) is confirmed closed by independent source read and independent command
execution in this session — not accepted on SUMMARY or commit-message narrative alone. All 12
must-have truths are now VERIFIED (9 fully exercised, 3 vacuously true because no live sweep has
occurred yet, matching the plan-sanctioned SKIP-path design).

**Standing caveat (not a gap, carried forward for visibility):** a real live sweep against
`develop` with actual Auth0 credentials has still not occurred in this repository — the current
run legitimately takes the plan-sanctioned `require_env`-SKIP path. Success criteria 3 and 4
(documenting and fixing real client-vs-server divergences) remain unexercised by construction
until credentials are supplied. This does not block phase completion under the plan's own design
(the SKIP path is the explicitly anticipated offline-safe outcome), but it does mean
`REQUIREMENTS.md`'s "Pending" marker for LIVE-MD-01 (line 72) is accurate until that live run
happens — that is a follow-on scheduling item, not a code defect.

---

_Verified: 2026-07-30T22:15:00Z_
_Verifier: Claude (gsd-verifier)_
