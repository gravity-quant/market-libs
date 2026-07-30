---
phase: 23-verificaci-n-en-vivo-contra-develop-fixes
verified: 2026-07-30T21:52:55Z
status: gaps_found
score: 11/12 must-haves verified
behavior_unverified: 0
overrides_applied: 0
gaps:
  - truth: "Every probe catches broad Exception and httpx.ConnectError so an unreachable develop or closed-market empty is classified NO-DATA/SKIP, never an uncaught crash that flips main_verify to FAILED (D-09)"
    status: failed
    reason: "Confirmed by direct code read (matches 23-REVIEW.md CR-01, independently re-verified, not taken on SUMMARY faith): in every read probe, _emit_shape(...) and _write_schema_snapshot(...) — which do file I/O (mkdir/read_text/write_text), json.loads() on a committed baseline, and call append_finding() (which raises ValueError on a multi-line title, findings.py:574) — run AFTER the probe's try/except Exception block, not inside it. Neither main() nor _async_main() has a catch-all around the probe-call region (only a try/finally for client teardown). A corrupt/hand-edited/merge-conflicted schema baseline (JSONDecodeError), a disk/permission error (OSError), or a server-controlled field name that lands in a SHAPE finding title with an embedded newline (ValueError) therefore propagates uncaught out of main() -> non-zero exit -> main_verify.py._run_driver classifies market-data-client as FAILED (main_verify.py:79-80) -- the exact outcome D-09 forbids. This does not manifest under the current require_env-SKIP run (no probes execute, so the vulnerable code path is never reached), but it is a live, deterministic defect that will fire the first time a real live sweep runs with credentials -- it is not hypothetical or a matter of runtime luck, it is structurally unguarded code, verifiable by static read alone."
    artifacts:
      - path: "main_market_data.py"
        issue: "_emit_shape/_write_schema_snapshot calls sit outside each probe's try/except in probe_market_data_sync (345-358), probe_latest_sync (371-381), probe_instruments_sync (398-408), probe_segments_sync (419-433), probe_symbols_sync (447-457), probe_calendar_sync (473-492), and their async mirrors (623-637, 649-660, 678-689, 702-716, 729-740, 757-777); the health probes' _write_schema_snapshot calls (287-300, 313-326) sit after their try/except too."
    missing:
      - "Move the _emit_shape / _write_schema_snapshot calls inside each probe's try/except (or a dedicated nested guard) so a post-request I/O/parsing failure degrades to a finding/SKIP rather than an uncaught exception, matching the sibling main_ambito_financiero.py pattern where SHAPE emission lives inside the probe try block."
      - "Harden _write_schema_snapshot to catch json.JSONDecodeError around the committed-baseline read (main_market_data.py:201)."
      - "Optionally add a top-level except Exception around the probe-orchestration body in main()/_async_main() as defense-in-depth so the driver can never exit non-zero on an unhandled path."
---

# Phase 23: Verificación en vivo contra develop + fixes Verification Report

**Phase Goal:** Ejercitar toda la superficie pública (sync + async) en vivo contra develop, detectar divergencias cliente-vs-servicio y corregirlas en el ciclo.
**Verified:** 2026-07-30T21:52:55Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Context Note on the SKIP Path

There is no `.env` for `market-data-client` in this repository (only `.env.example`), and this
was independently confirmed (`find packages/market-data-client -maxdepth 1 -iname "*.env*"` →
only `.env.example`). Running the driver live therefore legitimately takes the plan-anticipated
`require_env`-SKIP / D-09 NO-DATA path: zero CONFIRMED divergences, no fabricated
`models.py`/`_core.py` diff (confirmed empty via `git diff 9e26ecc..HEAD --stat` over
`packages/market-data-client/src`, `.../tests`, the findings file, and `schemas/`), and
`verify_cycle_closure("market-data-client")` passes vacuously (`(True, [])`, re-run and
confirmed). This vacuous PASS is the plan-sanctioned outcome for success criteria 3 and 4, not a
gap. **A real live sweep against develop still awaits Auth0 credentials** — until then, criteria
3 and 4 (documenting/fixing real divergences) are unexercised by construction, and the D-09
never-FAILED contract (see gap below) has never actually been triggered by a live probe run
either — it remains a latent, unexercised defect rather than an observed failure.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `main_market_data.py` constructs exactly ONE `Client()` + ONE `AsyncClient()`, threaded into every probe; exercises health + market-data + reference reads (SC1/D-02) | ✓ VERIFIED | `main()` constructs `client = Client()` (main_market_data.py:905), threads it into every sync probe; `_async_main()` constructs `aclient = AsyncClient()` (863), threads it into every async probe. AST guard confirms ctor count in [1,2] (`uv run pytest verification/test_main_market_data_uses_single_client_instance.py -q` → 1 passed). |
| 2 | Reuses `verification/` infra (require_env split, credential redaction); read-only, no mutating-gate (SC2) | ✓ VERIFIED | Imports `require_env`, `safe_print`, `schema_of`, `write_findings`, `append_finding`, `diff_safemodel_bidirectional` from `verification`. No mutation calls (only `get_*` reads). `safe_print(..., secrets=[])` used for all stdout. |
| 3 | Driver gates on the four Auth0 vars via `require_env`; missing var → verbatim `SKIPPED market-data-client: missing ...` + `sys.exit(0)` (D-01) | ✓ VERIFIED | Ran `uv run --package market-data-client python main_market_data.py` → printed exactly `SKIPPED market-data-client: missing MARKET_DATA_CLIENT_ID, MARKET_DATA_CLIENT_SECRET, MARKET_DATA_AUDIENCE, MARKET_DATA_AUTH0_TOKEN_URL`, exit code 0. |
| 4 | Every probe catches broad `Exception`/`httpx.ConnectError` so develop-unreachable/closed-market is classified NO-DATA/SKIP, **never** an uncaught crash flipping `main_verify` to FAILED (D-09) | ✗ FAILED | Confirmed by direct source read: `_emit_shape`/`_write_schema_snapshot` (file I/O + `append_finding`, which raises `ValueError` on a multi-line title) run AFTER the per-probe `try/except` in every read probe; neither `main()` nor `_async_main()` has a catch-all. See gap detail below (matches 23-REVIEW.md CR-01, independently re-verified). |
| 5 | All 10 endpoint methods exercised on BOTH sync `Client` and async `AsyncClient` surfaces (D-03) | ✓ VERIFIED | `grep` count of `client.<method>(` / `aclient.<method>(` for all 10 methods (`get_health`, `get_health_feed`, `get_market_data`, `get_latest`, `get_latest_batch`, `get_instruments`, `get_segments`, `get_symbols`, `get_calendar`, `get_calendar_config`) each ≥1 on both surfaces. |
| 6 | `main_verify.py._DRIVERS` contains the `market-data-client` tuple (D-08.2) | ✓ VERIFIED | `main_verify.py:34` — `("market-data-client", "main_market_data.py")` present in `_DRIVERS`. |
| 7 | AST guard asserts `1 <= (Client\|AsyncClient) ctor calls <= 2` in `main_market_data.py` (D-08.1) | ✓ VERIFIED (weak — see WR-01) | `verification/test_main_market_data_uses_single_client_instance.py:53` asserts exactly this bound; test passes. Note: the bound is looser than the docstring's claimed invariant (see Anti-Patterns WR-01). |
| 8 | Every client-vs-server divergence is documented in findings and fixed in-cycle, mirrored sync/async (SC3/D-06) | ✓ VERIFIED (vacuous) | No divergences were surfaced (SKIP path — no probes ran). Findings file remains the bootstrap skeleton (`.planning/verification/market-data-client-findings.md`, empty Index table). `git diff 9e26ecc..HEAD` over `models.py`/`_core.py`/`tests/` is empty — no fabricated fix. Plan-sanctioned no-op per 23-01/23-02 PLAN text. |
| 9 | Each CONFIRMED/FIXED finding links a mocked pytest-httpx regression via `Regression:` (D-07) | ✓ VERIFIED (vacuous) | No CONFIRMED/FIXED findings exist to check; requirement holds trivially. |
| 10 | `verify_cycle_closure("market-data-client")` returns PASS (SC4) | ✓ VERIFIED | Ran `verify_cycle_closure("market-data-client")` directly → `(True, [])`. |
| 11 | Any unmirrored shell (`_request`) change opens a `SYNC-ASYNC-DRIFT` finding (D-06 policy) | ✓ VERIFIED (vacuous) | No shell-level change was made (confirmed empty diff on `client.py`/`aio.py`) — nothing to mirror, nothing to flag. |
| 12 | New model fields additive; `received_at` never repurposed (D-05/D-06) | ✓ VERIFIED (vacuous) | No model changes made (confirmed empty diff on `models.py`). |

**Score:** 11/12 truths verified (0 present-but-behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `main_market_data.py` | Live-verification driver: probe_* functions, ProbeResult, env-gate, SHAPE diff, schema snapshot, redacted output | ⚠️ VERIFIED w/ defect | 942 lines, all functions present and wired; contains the CR-01 exception-isolation gap (see truth #4). |
| `verification/test_main_market_data_uses_single_client_instance.py` | AST single-Client guard | ✓ VERIFIED | `def test_main_market_data_uses_single_client_instance(` present; test passes green. |
| `main_verify.py` | Aggregate runner extended with market-data-client driver | ✓ VERIFIED | `_DRIVERS` includes the tuple; ran `uv run python main_verify.py` → classifies `market-data-client` as `SKIPPED` (never FAILED, D-09 holds in the current no-creds condition). |
| `.planning/verification/market-data-client-findings.md` | Bootstrapped findings file | ✓ VERIFIED | Exists with the standard bootstrap skeleton (Run Context + empty Index table). |
| `.planning/verification/schemas/market-data-client/` | Schema-snapshot dir (DRIFT-01) | ✓ VERIFIED | Directory exists with `.gitkeep`; no live JSON envelopes yet (expected — no live run occurred). |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `main_market_data.py` | `verification/env_gate.py` | `require_env("market-data-client", [...])` | ✓ WIRED | Called at top of `main()` (main_market_data.py:890), verbatim four-var list matches D-01. |
| `main_market_data.py` | `verification/safemodel_diff.py` | `diff_safemodel_bidirectional(raw_item, Model)` | ✓ WIRED | Called in `_emit_shape` for all 7 SafeModels across the probe set (MarketDataSnapshot, MarketDataEntry, Instrument, Segment, Symbol, CalendarDay, CalendarConfig). |
| `main_verify.py` | `main_market_data.py` | `_DRIVERS` tuple | ✓ WIRED | Confirmed present; `_run_driver` invokes `uv run --package market-data-client python main_market_data.py` as subprocess. |
| `.planning/verification/market-data-client-findings.md` | `packages/market-data-client/tests/` | `Regression:` field | N/A (vacuous) | No findings to link — no-op is correct for the SKIP path. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Driver clean-SKIP on missing creds | `uv run --package market-data-client python main_market_data.py` | `SKIPPED market-data-client: missing MARKET_DATA_CLIENT_ID, ...`, exit 0 | ✓ PASS |
| AST single-Client guard | `uv run python -m pytest verification/test_main_market_data_uses_single_client_instance.py -q` | 1 passed | ✓ PASS |
| Cycle closure gate | `verify_cycle_closure("market-data-client")` | `(True, [])` | ✓ PASS |
| Aggregate runner classification | `uv run python main_verify.py` | `SKIPPED market-data-client` (RAN: 3, SKIPPED: 2, FAILED: 1 — the 1 FAILED is `matriz-client`, unrelated pre-existing issue outside this phase's scope) | ✓ PASS (for market-data-client) |
| Ruff / mypy on phase-changed files | `uv run ruff check ...`, `uv run mypy main_market_data.py` | All checks passed / Success, no issues | ✓ PASS |
| Findings/schema-dir credential leak scan | `grep` for Bearer/client_secret/JWT | No hits; only `.gitkeep` under schemas dir | ✓ PASS |

Step 7b full-suite note: package test suite not re-run here (23-02-SUMMARY.md already reports
134 passed with an empty diff scope, corroborated by the empty `git diff` check above — re-running
would add no new evidence since zero files changed).

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| LIVE-MD-01 | 23-01-PLAN.md, 23-02-PLAN.md | Superficie pública completa ejercitada en vivo contra develop con Auth0; reutiliza `verification/`; divergencias documentadas y corregidas mirrored sync/async | ⚠️ PARTIALLY SATISFIED | Apparatus (driver + harness integration + cycle-closure gate) is built and functions correctly on the SKIP path, but (a) no live sweep against develop has actually occurred (creds absent — acknowledged as pending in both SUMMARYs), and (b) the D-09 "never crash" guarantee central to LIVE-MD-01's safety framing has a confirmed structural gap (CR-01) that would surface the first time a live run actually executes probes. REQUIREMENTS.md still lists LIVE-MD-01 as "Pending" (line 72), consistent with this being not-yet-fully-closed. |

No orphaned requirements: only LIVE-MD-01 is mapped to Phase 23 in REQUIREMENTS.md, and both plans declare it.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `main_market_data.py` | multiple (see gap) | Post-request processing (`_emit_shape`/`_write_schema_snapshot`) outside probe `try/except` | 🛑 BLOCKER (CR-01) | Breaks the D-09 never-FAILED contract; see gap above. |
| `verification/test_main_market_data_uses_single_client_instance.py` | 32, 53 | AST guard sums `Client`+`AsyncClient` into one count (`1<=total<=2`) instead of asserting exactly-1-each | ⚠️ WARNING (WR-01) | A driver constructing two `Client()` and zero `AsyncClient()` would pass the guard green despite violating the single-instance-per-surface invariant the docstring claims. Not currently exploited (the driver does construct exactly one of each), but the guard gives false assurance for its own stated failure mode. |
| `main_market_data.py` | 543-566, 781-804 | `probe_no_data_sync`/`_async` emit an OPEN finding on the *expected* empty-result happy path and silently PASS the anomalous non-empty case | ⚠️ WARNING (WR-02) | Inverted diagnostic logic: normal runs accumulate permanent noise findings; a real anti-bot/filter bug (server returning data for a bogus prefix) would be silently missed. |
| `main_market_data.py` | 94-101 (usage throughout) | `_next_fid()` is a per-process sequential counter; `append_finding` dedupes by fid and preserves human-promoted findings, silently discarding new ones on fid collision | ⚠️ WARNING (WR-03) | Latent data-loss risk: an unrelated new divergence could be dropped if its run-local counter value collides with a prior human-triaged finding's fid. Matches an existing codebase-wide convention (not new to this phase) but still a real risk. |
| `main_verify.py` | 61-66 | `subprocess.run(...)` has no `timeout=` | ⚠️ WARNING (WR-04) | A wedged/hanging driver blocks the entire aggregate runner indefinitely, defeating the "runner never stops" guarantee. |
| `main_market_data.py` | 170-216 | `schema_of` samples only the first list element; market-variable payloads can legitimately differ row-to-row | ⚠️ WARNING (WR-05) | False-positive-prone SHAPE drift findings from sampling variance rather than real schema change, once live runs begin. |

No `TBD`/`FIXME`/`XXX` debt markers found in the phase's modified/created files (`main_market_data.py`, `verification/test_main_market_data_uses_single_client_instance.py`, `main_verify.py`).

### Human Verification Required

None. All items above are resolvable by static analysis and command execution; no visual, real-time, or subjective-quality checks are needed for this phase's artifacts.

### Gaps Summary

The Plan-01/02 apparatus is real, well-structured, and does everything it claims on the
**offline SKIP path**: the single-Client invariant holds, all 10 endpoints are wired on both
surfaces, the harness integration (findings bootstrap, schema-snapshot dir, `_DRIVERS` append,
AST guard) is complete and green, and `verify_cycle_closure` legitimately passes vacuously
because no live sweep has occurred (no develop credentials in this repo — correctly acknowledged
in both SUMMARYs as deferred work).

The one BLOCKER is CR-01, surfaced independently by the code-review agent and independently
re-confirmed here by direct source inspection (not taken on SUMMARY or REVIEW.md faith): the
D-09 "a probe can never propagate an uncaught exception" invariant — an explicit must-have truth
in the 23-01-PLAN.md frontmatter and the phase's core safety contract — is violated by
construction. SHAPE-diff and schema-snapshot post-processing run *after* each probe's
`try/except`, so a corrupt committed schema baseline, a disk error, or a server-supplied field
name landing in a title with an embedded newline would propagate an uncaught exception through
`main()`, exit non-zero, and cause `main_verify.py` to classify `market-data-client` as `FAILED`
— precisely the outcome the phase's design explicitly forbids. This has not yet been *observed*
in a live run (because no live run with real credentials has occurred), so it does not
retroactively invalidate the SKIP-path evidence already gathered — but it means the apparatus is
not yet safe to run against real credentials without the fix, and the phase's central safety
guarantee is not actually true of the code as it stands today.

**This looks like a real defect, not an intentional deviation** — no override is suggested. The
fix is scoped (move the post-processing calls inside each probe's `try/except`, per the
`main_ambito_financiero.py` sibling pattern) and does not require live credentials to implement
or to verify offline (a mocked/synthetic corrupt-baseline or forced-exception test would exercise
it deterministically).

---

_Verified: 2026-07-30T21:52:55Z_
_Verifier: Claude (gsd-verifier)_
