---
phase: 27
slug: verificaci-n-en-vivo-segura-fixes
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-01
---

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

Task IDs are assigned by the planner; this map is the contract each task's `<verify>`
block must satisfy. Rows marked **W0** depend on Wave 0 harness work landing first.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | 01 | 0 | LIVE-MUT-01 | T-27-01 | `append_finding` with a new fid preserves `Classification:`/`Resolution:` prose on all pre-existing findings (D-23 data-loss fix) | unit | `uv run pytest verification -q -k findings` | ❌ W0 | ⬜ pending |
| TBD | 01 | 0 | LIVE-MUT-01 | — | Seeded fid allocator emits the first new fid above the highest existing fid, so no Phase-27 finding is swallowed by the non-OPEN short-circuit (D-16/D-24) | unit | `uv run pytest verification -q -k findings` | ❌ W0 | ⬜ pending |
| TBD | 01 | 0 | LIVE-MUT-01 | — | `verify_cycle_closure("market-data-client")` returns `(True, [])` after the 34 legacy `Regression:` bullets are backfilled (D-21) | cli | `uv run python -c "from verification.cycle_report import verify_cycle_closure as v; ok,m=v('market-data-client'); assert ok, m"` | ✅ | ⬜ pending |
| TBD | 02 | 1 | LIVE-MUT-01 | T-27-02 | Driver mutation gate refuses when the env opt-in is unset **or** `urlsplit(base_url).hostname` is not exactly the develop host; superstring/substring hosts are refused (D-01) | unit | `uv run pytest verification -q -k mutation_gate` | ❌ W0 | ⬜ pending |
| TBD | 02 | 1 | LIVE-MUT-01 | T-27-03 | Driver constructs at most 2 `Client`/`AsyncClient` ctor sites total — the mutating client is the existing single instance, not a second one (D-02) | unit | `uv run pytest verification/test_main_market_data_uses_single_client_instance.py -q` | ✅ | ⬜ pending |
| TBD | 02 | 1 | LIVE-MUT-01 | — | Gate-off emits a **colon-less** probe-level SKIP; no line matches `^SKIPPED \S.*:` except the `require_env` credentials line (D-03) | unit | `uv run pytest verification -q -k main_market_data` | ❌ W0 | ⬜ pending |
| TBD | 02 | 1 | LIVE-MUT-01 | — | No creds / wrong host ⇒ driver exits SKIPPED, never FAILED; all mutation post-processing sits inside each probe's `try` (D-04) | unit | `uv run pytest verification/test_main_market_data_postprocess_guarded.py -q` | ✅ | ⬜ pending |
| TBD | 02 | 1 | LIVE-MUT-01 | — | `parse_calendar_response` unwraps the `{config, coverage, days[], market}` envelope; `CalendarDay` carries the real wire fields (D-12/D-13) | unit | `uv run --package market-data-client pytest packages/market-data-client/tests -q -k calendar` | ✅ | ⬜ pending |
| TBD | 03 | 2 | LIVE-MUT-01 | T-27-04 | Symbols cycle: create with the dedicated prefix → `GET /symbols` confirms → `PATCH active=false` reverts (D-05) | manual (live) | driver `SUMMARY:` line + findings file | n/a | ⬜ pending |
| TBD | 03 | 2 | LIVE-MUT-01 | T-27-05 | Holidays cycle: `POST` far-future ISO date → `GET /calendar` confirms → `DELETE /calendar/holidays/{day}` (D-07) | manual (live) | driver `SUMMARY:` line + findings file | n/a | ⬜ pending |
| TBD | 03 | 2 | LIVE-MUT-01 | T-27-06 | Calendar config is exercised **preview-only**; no `PUT`/`DELETE /calendar/config` request is ever emitted against develop (D-06) | manual (live) + unit | outgoing-request assertion in the mocked suite | ❌ W0 | ⬜ pending |
| TBD | 03 | 2 | LIVE-MUT-01 | — | Cleanup failure emits a finding rather than being suppressed (D-08) | unit | `uv run pytest verification -q -k main_market_data` | ❌ W0 | ⬜ pending |
| TBD | 03 | 2 | LIVE-MUT-01 | — | Idempotency measured by **row count** via `GET /symbols?prefix=` and `GET /calendar?year=2099`, not status code (D-19/D-27) | manual (live) | findings file | n/a | ⬜ pending |
| TBD | 04 | 3 | LIVE-MUT-01 | — | Every live divergence has a mocked regression test, mirrored sync **and** async (D-15, criterion 4) | unit | `uv run pytest -q` | ❌ W0 | ⬜ pending |
| TBD | 04 | 3 | LIVE-MUT-01 | — | `symbol_id` accepts `int \| str` and symbols mutations still return `list[Symbol]` — released v0.3.x contract unbroken (D-22) | unit | `uv run --package market-data-client pytest packages/market-data-client/tests -q -k symbols` | ✅ | ⬜ pending |
| TBD | 04 | 3 | LIVE-MUT-01 | — | If live measurement contradicts DM-03, the builder's `idempotent=` flag changes and a **dispatch-level** no-retry test proves exactly one outgoing request under repeated 503 (D-20/D-27) | unit | `uv run --package market-data-client pytest packages/market-data-client/tests -q -k transport` | ✅ | ⬜ pending |
| TBD | 04 | 3 | LIVE-MUT-01 | — | `get-symbols.json` re-baselined (permanent drift from the reverted test symbol), `get-calendar.json` untouched (D-26) | cli | `git diff --stat .planning/verification/schemas/market-data-client/` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Wave 0 is **harness plumbing**, and it is load-bearing: without it a live run silently
discards its own findings (D-16/D-24) and destroys 36 findings' worth of human triage
prose (D-23). Nothing destructive may run before it lands.

- [ ] `verification/findings.py` — preserve human-triage fields (`Classification:`,
      `Rationale:`, `Resolution:`) across a rewrite triggered by a new fid (D-23)
- [ ] `verification/findings.py` / `main_market_data.py` — seeded fid allocator so new
      findings start above the highest existing fid (D-16/D-24)
- [ ] `.planning/verification/market-data-client-findings.md` — backfill 34 `Regression:`
      bullets on F-03…F-36 (D-21)
- [ ] `verification/test_findings_*.py` — regression coverage for both harness fixes above
- [ ] `main_market_data.py` — import and call `verify_cycle_closure("market-data-client")` (D-18)
- [ ] New driver-gate tests (D-01/D-03/D-08) — no existing file covers these

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

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] Live-only behaviors are enumerated in Manual-Only Verifications with concrete instructions
- [ ] Every live divergence has a mocked regression test mirrored sync + async
- [ ] `verify_cycle_closure("market-data-client")` returns `(True, [])`
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
