---
phase: 27
slug: verificaci-n-en-vivo-segura-fixes
status: approved
nyquist_compliant: true
wave_0_complete: false
created: 2026-08-01
updated: 2026-08-01
plans: 7
waves: 6
tasks: 20
---

> **Revision note (2026-08-01):** this file was first written between research and
> planning, when the expected shape was 4 plans across waves 0–3. The planner produced
> **7 plans across waves 1–6** (20 tasks). The map below has been refreshed against the
> real `27-01-PLAN.md` … `27-07-PLAN.md`. Task IDs are positional (`27-<plan>-<task>`),
> since plan tasks carry no explicit `id` attribute. Wave numbering starts at **1**, not
> 0 — what this file originally called "Wave 0 harness plumbing" is **Wave 1 / plan 27-01**.

# Phase 27 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (+ pytest-asyncio `asyncio_mode=auto`, pytest-httpx) |
| **Config file** | Root `pyproject.toml` (`[tool.pytest.ini_options]`, `--import-mode=importlib`, `--strict-markers`) |
| **Quick run command** | `uv run --package market-data-client pytest packages/market-data-client/tests -q` |
| **Full suite command** | `uv run pytest -q` (workspace-wide, includes `verification/`) |
| **Estimated runtime** | ~25s package / ~90s workspace |

**Gate commands (all four must be green before the phase closes):**

| Gate | Command |
|------|---------|
| lint | `uv run ruff check .` |
| format | `uv run ruff format --check .` |
| types | `uv run mypy packages/market-data-client/src` |
| tests | `uv run pytest -q` |

> `market-data-client` is still absent from the root mypy `files` list and from
> `importlinter.root_packages` (deferred follow-up from Phase 24, restated in 27-CONTEXT
> `<deferred>`), so the typecheck gate is run **explicitly per-package** as above.

---

## Sampling Rate

- **After every task commit:** Run the quick command (package suite).
- **After every plan wave:** Run the full suite plus all four gates.
- **Before `/gsd-verify-work`:** Full suite green **and** `verify_cycle_closure("market-data-client")` returns `(True, [])`.
- **Max feedback latency:** 30 seconds (quick command).

**Live-run sampling is different in kind.** The destructive live probes are not part of
any pytest run — they execute through `main_market_data.py` against develop and are gated
by credentials + the driver mutation gate (D-01/D-02). Their feedback signal is the
driver's own `SUMMARY:` line plus the findings file, not a test exit code. Every live
divergence must land back in the mocked suite as a regression test before it counts as
fixed (criterion 4).

---

## Per-Task Verification Map

This map is the contract each task's `<verify>` block must satisfy. **File Exists** answers
"does a test file covering this already exist?" — ❌ W1 means plan 27-01 (wave 1) must create
it first.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 27-01-01 | 01 | 1 | LIVE-MUT-01 | T-27-01 | `append_finding` with a new fid preserves unknown bullets (`Classification:`/`Rationale:`/`Resolution:`) on all 36 pre-existing findings (D-23) | unit (tdd) | `uv run pytest verification -q -k findings` | ✅ | ⬜ pending |
| 27-01-02 | 01 | 1 | LIVE-MUT-01 | — | `max_existing_fid(pkg)` lets the allocator seed above the highest recorded fid, so no Phase-27 finding dies on the non-OPEN short-circuit (D-16/D-24) | unit (tdd) | `uv run pytest verification -q -k findings` | ✅ | ⬜ pending |
| 27-01-03 | 01 | 1 | LIVE-MUT-01 | — | 34 legacy `Regression:` bullets backfilled; `verify_cycle_closure("market-data-client")` returns `(True, [])` (D-21/D-18) | cli | `uv run python -c "from verification.cycle_report import verify_cycle_closure as v; ok,m=v('market-data-client'); assert ok, m"` | ✅ | ⬜ pending |
| 27-02-01 | 02 | 1 | LIVE-MUT-01 | — | `CalendarDay` carries the real develop wire fields (`day`/`closed`/`open_time`/`close_time`/`description`), not the invented `date`/`marketId`/`isBusinessDay` (D-12/D-13) | unit (tdd) | `uv run --package market-data-client pytest packages/market-data-client/tests -q -k calendar` | ✅ | ⬜ pending |
| 27-02-02 | 02 | 1 | LIVE-MUT-01 | — | `parse_calendar_response` unwraps the `{config, coverage, days[], market}` envelope instead of iterating it as a list; coverage mirrored sync/async (D-12/D-15) | unit (tdd) | `uv run --package market-data-client pytest packages/market-data-client/tests -q -k calendar` | ✅ | ⬜ pending |
| 27-03-01 | 03 | 2 | LIVE-MUT-01 | T-27-02 | Package-agnostic parametrized gate refuses unless the env opt-in is set **and** `urlsplit(base_url).hostname` equals the develop host exactly — substring, superstring, port, userinfo and malformed URLs all fail closed (D-01) | unit | `uv run pytest verification -q -k mutation_gate` | ✅ | ⬜ pending |
| 27-03-02 | 03 | 2 | LIVE-MUT-01 | T-27-03 | Gate, seeded allocator, cycle-closure probe and the D-06 EXPECTED finding wired into the driver without adding a ctor site (`1 <= ctor_sites <= 2` holds) (D-02/D-04/D-06/D-12/D-16/D-18) | unit | `uv run pytest verification/test_main_market_data_uses_single_client_instance.py -q` | ✅ | ⬜ pending |
| 27-03-03 | 03 | 2 | LIVE-MUT-01 | — | Gate-refusal probes present; source-level guard proves the skip line is **colon-less** so no line matches `^SKIPPED \S.*:` except the `require_env` credentials line (D-03/D-04) | unit | `uv run pytest verification -q -k skip_line` | ❌ W1 | ⬜ pending |
| 27-04-01 | 04 | 3 | LIVE-MUT-01 | T-27-04 | Gate-checked mutation dispatch + dedicated test identifiers + `_emit_cleanup_finding` helper; two AST guards prove cleanup failure emits a finding rather than being suppressed (D-08) | unit | `uv run pytest verification -q -k main_market_data` | ❌ W1 | ⬜ pending |
| 27-04-02 | 04 | 3 | LIVE-MUT-01 | T-27-05 | Symbols create → `GET /symbols` verify → `PATCH active=false` revert on the sync surface, with id discovery and row-count idempotency (D-05/D-10/D-11/D-19/D-27) | manual (live) + unit | driver `SUMMARY:` line + findings file; gate-off smoke run emits zero new findings | n/a | ⬜ pending |
| 27-04-03 | 04 | 3 | LIVE-MUT-01 | — | The four symbols probes mirrored on the async surface (D-05/D-15/D-19) | manual (live) + unit | driver `SUMMARY:` line; parity assertion | n/a | ⬜ pending |
| 27-05-01 | 05 | 4 | LIVE-MUT-01 | T-27-06 | Calendar config exercised **preview-only**; an AST guard proves no `PUT`/`DELETE /calendar/config` call site exists in the driver (D-06/D-19) | unit | `uv run pytest verification -q -k main_market_data` | ❌ W1 | ⬜ pending |
| 27-05-02 | 05 | 4 | LIVE-MUT-01 | T-27-07 | Holidays `POST` far-future ISO date → `GET /calendar` verify → `DELETE /calendar/holidays/{day}`, both surfaces (D-07/D-08/D-12/D-19/D-27) | manual (live) + unit | driver `SUMMARY:` line + findings file | n/a | ⬜ pending |
| 27-05-03 | 05 | 4 | LIVE-MUT-01 | — | Terminal residue sweep leaves no unrecognized test-prefixed state; self-inflicted health-feed recheck; snapshot drift policy applied (D-08/D-17/D-26) | manual (live) + cli | residue sweep output; `git diff --stat .planning/verification/schemas/market-data-client/` | n/a | ⬜ pending |
| 27-06-01 | 06 | 5 | LIVE-MUT-01 | — | Pre-flight re-fetches the live OpenAPI, re-verifies its load-bearing claims, and records a clean prose-preservation baseline before anything is armed | manual (live) | pre-flight output captured in SUMMARY | n/a | ⬜ pending |
| 27-06-02 | 06 | 5 | LIVE-MUT-01 | T-27-08 | **Blocking operator authorization** obtained before the destructive run; no write is emitted without it | manual (human) | explicit operator approval recorded | n/a | ⬜ pending |
| 27-06-03 | 06 | 5 | LIVE-MUT-01 | T-27-09 | Armed destructive run against develop; evidence captured; residue verified absent (test symbol `active=false`, test holiday deleted) | manual (live) | driver `SUMMARY:` line + findings file + residue check | n/a | ⬜ pending |
| 27-07-01 | 07 | 6 | LIVE-MUT-01 | — | `symbol_id` widened to `int \| str` (**not** narrowed to `int`) across all four call sites; discovered `Symbol` row-id field added alongside, mirrored sync/async — released v0.3.x contract unbroken (D-09/D-10/D-22) | unit | signature-inspection assertion + `uv run --package market-data-client pytest packages/market-data-client/tests -q -k symbols` | ✅ | ⬜ pending |
| 27-07-02 | 07 | 6 | LIVE-MUT-01 | — | Symbols mutation parsing corrected while **keeping** `list[Symbol]` (envelope unwrap, mirroring `parse_latest_response`); any contradicted `idempotent=` flag flipped with a dispatch-level no-retry test proving exactly one request under repeated 503 (D-11/D-20/D-22) | unit (tdd) | `uv run --package market-data-client pytest packages/market-data-client/tests -q -k "symbols or transport"` | ✅ | ⬜ pending |
| 27-07-03 | 07 | 6 | LIVE-MUT-01 | — | Every divergence promoted to `FIXED` with a resolvable `Regression:` bullet, mirrored sync **and** async; `get-symbols.json` re-baselined; live re-run clean; **cycle closure PASS** (D-17/D-18/D-21/D-26) | cli + unit | `uv run pytest -q` and `verify_cycle_closure("market-data-client") == (True, [])` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Sampling continuity check:** no run of 3 consecutive tasks lacks an automated verify.
The longest manual-only run is `27-06-01 … 27-06-03` (the armed live run), which is
inherently manual by nature — it is bracketed by fully automated waves on both sides
(27-05 before, 27-07 after) and gated by a blocking human checkpoint at `27-06-02`.

---

## Wave 1 Requirements (the "Wave 0" role)

Plan **27-01** is the harness plumbing, and it is load-bearing: without it a live run
silently discards its own findings (D-16/D-24) and destroys 36 findings' worth of human
triage prose (D-23). Nothing destructive may run before it lands. Plan 27-02 shares wave 1
but is independent (zero `files_modified` overlap) — the two are the only true parallel pair
in this phase.

- [x] `verification/findings.py` — preserve unknown bullets (`Classification:`,
      `Rationale:`, `Resolution:`) across a rewrite triggered by a new fid — **27-01-01** (D-23)
- [x] `verification/findings.py` — `max_existing_fid(pkg)` so allocators seed above the
      highest recorded fid — **27-01-02** (D-16/D-24)
- [x] `.planning/verification/market-data-client-findings.md` — backfill 34 `Regression:`
      bullets on F-03…F-36 — **27-01-03** (D-21)
- [x] `verification/test_findings_*.py` — regression coverage for both harness fixes — **27-01-01/02**
- [x] `main_market_data.py` — import and call `verify_cycle_closure("market-data-client")` — **27-03-02** (D-18)
- [x] New driver-gate + skip-line + cleanup-finding guards — **27-03-01/03**, **27-04-01**,
      **27-05-01** (D-01/D-03/D-08/D-06); no existing file covered these

*Existing infrastructure covers the rest: pytest + pytest-httpx + pytest-asyncio are
installed and configured; `verification/` already provides redaction, snapshots,
SafeModel diffing and the findings lifecycle.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Destructive live cycle against develop (symbols create→verify→revert; holidays create→verify→delete) | LIVE-MUT-01 | Requires real Auth0 credentials, network reachability to `market-data-develop.bbsa.com.ar`, and mutates shared develop state — cannot run in CI | Export the Auth0 creds and the driver mutation opt-in, then `uv run --package market-data-client python main_market_data.py`. Confirm the `SUMMARY:` line, inspect the findings file, and verify no residue remains (test-prefixed symbol is `active=false`, test holiday deleted). |
| Real per-endpoint idempotency (DM-03 revalidation) | LIVE-MUT-01 | Only the live server can answer whether a repeated POST dedupes or duplicates; the spec's claim is a hypothesis, not evidence (D-19/D-27) | Double-fire each safely-repeatable mutation, then read row counts via `GET /symbols?prefix=` and `GET /calendar?year=2099`. Compare against the builder's declared `idempotent=` flag; any contradiction is a finding **and** a code fix. |
| Response shapes of the 8 mutation endpoints | LIVE-MUT-01 | The OpenAPI declares every mutation response as bare `object` with no schema — the concrete body is unknowable offline | Capture each 200/201 body during the live run; reconcile `parse_symbols_response` and the symbol-id location (D-10/D-11) against what actually arrives. |
| Operator authorization for what is safe to touch on develop | LIVE-MUT-01 (DM-06) | A judgement about shared infrastructure, not a codebase fact | **Already given (2026-08-01):** calendar config is preview-only; `PUT`/`DELETE /calendar/config` are not exercised live (D-06). |

---

## Validation Sign-Off

Checked against the final 7-plan / 6-wave / 20-task structure.

- [x] All 20 tasks have an automated verify or a declared wave-1 dependency
- [x] Sampling continuity: no 3 consecutive tasks without automated verify (the manual
      `27-06-*` run is inherently live and is bracketed by automated waves on both sides)
- [x] Wave 1 covers every MISSING test-file reference
- [x] No watch-mode flags
- [x] Feedback latency < 30s (package suite)
- [x] Live-only behaviors enumerated in Manual-Only Verifications with concrete instructions
- [ ] Every live divergence has a mocked regression test mirrored sync + async *(execution-time — 27-07-03)*
- [ ] `verify_cycle_closure("market-data-client")` returns `(True, [])` *(execution-time — 27-01-03 establishes it, 27-07-03 re-confirms after new findings)*
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-08-01 (plan-checker VERIFICATION PASSED; stale-map warning resolved by this revision)
