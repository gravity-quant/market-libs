# Roadmap: market-libs — Verificación en vivo de clientes

## Milestones

- ✅ **v1.0 Verification cycle** — Phases 1-5 (shipped 2026-06-10) — see [`milestones/v1.0-ROADMAP.md`](./milestones/v1.0-ROADMAP.md)
- ✅ **v1.1 Tech Debt Cleanup** — Phases 6-11 (shipped 2026-06-14) — see [`milestones/v1.1-ROADMAP.md`](./milestones/v1.1-ROADMAP.md)
- 🔄 **v1.2 Architecture + Auth/Ergonomics Carry-forwards** — Phases 12-17 (planning 2026-06-14)

## Phases

<details>
<summary>✅ v1.0 Verification cycle (Phases 1-5) — SHIPPED 2026-06-10</summary>

- [x] Phase 1: Safety Harness & Verification Infrastructure (4/4 plans) — completed 2026-05-28
- [x] Phase 2: Ámbito Verification (3/3 plans) — completed 2026-06-05
- [x] Phase 3: IOL Verification (3/3 plans) — completed 2026-06-06
- [x] Phase 4: Higyrus Verification (4/4 plans) — completed 2026-06-08
- [x] Phase 5: Matriz Verification (4/4 plans) — completed 2026-06-10 (DRIFT-02 cycle closure baseline `verification-cycle-2026-Q2`)

Full details: [`milestones/v1.0-ROADMAP.md`](./milestones/v1.0-ROADMAP.md)
Requirements archive: [`milestones/v1.0-REQUIREMENTS.md`](./milestones/v1.0-REQUIREMENTS.md)
Audit: [`milestones/v1.0-MILESTONE-AUDIT.md`](./milestones/v1.0-MILESTONE-AUDIT.md)

</details>

<details>
<summary>✅ v1.1 Tech Debt Cleanup (Phases 6-11) — SHIPPED 2026-06-14</summary>

- [x] Phase 6: Compat Safety Net + Client Class Skeleton (7/7 plans) — completed 2026-06-11 — `Client`/`AsyncClient` per package + PEP 562 compat shim; REFAC-01/02
- [x] Phase 7: `_core.py` Extraction — Sync/Async Logic Dedup (6/6 plans) — completed 2026-06-12 — pure builders/parsers + import-linter contracts; REFAC-03 + CR-03/05
- [x] Phase 8: Retries, Backoff, Structured Logging (6/6 plans) — completed 2026-06-13 — `tenacity` full-jitter + mutation gate + `RedactingFilter`; RELY-01..04 + LOG-01..03
- [x] Phase 9: Deferred Bug Fixes (4/4 plans) — completed 2026-06-13 — BUG-01..04 (2 operator overrides)
- [x] Phase 10: matriz `aio.py` Creation + TokenStore (4/4 plans) — completed 2026-06-14 — 852 LOC async REST + `TokenStore` 3-way concurrency + `_atransport.py`; REFAC-04 + LIVE-02
- [x] Phase 11: Harness Hardening + Code Review Close-out + Live Re-verification (3/3 plans) — completed 2026-06-14 — append-only findings + idempotent dedupe + LIVE-01 final gate × 4 packages (iol F-02 fixed inline); HARN-07..10 + CR-01/02/04/06/07/08 + LIVE-01

Full details: [`milestones/v1.1-ROADMAP.md`](./milestones/v1.1-ROADMAP.md)
Requirements archive: [`milestones/v1.1-REQUIREMENTS.md`](./milestones/v1.1-REQUIREMENTS.md)
Audit: [`milestones/v1.1-MILESTONE-AUDIT.md`](./milestones/v1.1-MILESTONE-AUDIT.md)
Phase artifacts: [`milestones/v1.1-phases/`](./milestones/v1.1-phases/)

</details>

### 🔄 v1.2 Architecture + Auth/Ergonomics Carry-forwards (Phases 12-17) — PLANNING 2026-06-14

**Goal:** Cerrar la deuda arquitectónica residual de v1.1 — migrar los 4 drivers `main_*.py` a consumir `Client`/`AsyncClient` directamente (cierra el LOC drop residual iol -5.1% / matriz -20%), eliminar la duplicación estructural sync/async vía unasync/codegen single-source (spike-gated), agregar IOL refresh_token disk persistence, y exponer `client.with_options(max_retries=N)` cross-package.

**Operational gate (pre-Phase-12):** v1.1 head `71bf201` MUST be confirmed CI-green on Python 3.13 BEFORE Phase 12 starts. Closes the 3 deferred human-verification items from v1.1 Phases 7/8/9 (CI matrix Python 3.13 remote confirmation). Anti-Pitfall 17 — prevents v1.1-vs-v1.2 attribution ambiguity if a 3.13 break surfaces during v1.2. If CI red, fix lands as quick-task BEFORE Phase 12.

**Summary checklist (Phases 12-17):**

- [ ] **Phase 12: Codegen Spike** — Tool-choice spike (unasync vs libcst) on ámbito canary + matriz worst-case; outputs go/no-go decision for Phase 16 + per-package `Rule` config + B8 identity preservation proof. RESEARCH FLAG.
- [ ] **Phase 13: Cross-Package Ergonomics** — `client.with_options(max_retries=N)` × 4 packages via `request.extensions["max_attempts"]` per-request override; mutation-gate invariant preserved (anti-Pitfall 14: duplicate-order). ERG-01.
- [ ] **Phase 14: IOL Disk Persistence** — `iol_client/_token_cache.py` + `platformdirs >=4.0,<5` runtime dep + atomic write + `fcntl.flock` + 0600 chmod + failed-refresh cleanup + caplog no-leak guard. SEC-01. *Parallel-eligible with Phase 15.*
- [ ] **Phase 15: Driver Migration × 4** — `main_ambito` → `main_iol` → `main_higyrus` → `main_matriz` consume `Client()`/`AsyncClient()` directly; ONE Client per `main()` run invariant; probe names UNCHANGED; AST regression-guard per driver. REFAC-05. *Parallel-eligible with Phase 14.*
- [ ] **Phase 16: Codegen Single-Source (CONDITIONAL)** — unasync `aio.py` → `client.py` × 4 transport shells; `@generated` marker + CI `lint-codegen` verify-clean + import-linter `_aio` ↔ `_sync` contracts + matriz `_token_store.py` / `_refresh_policy.py` / `ws_client.py` in deny-list. REFAC-06. **CONDITIONAL: dropped if Phase 12 spike returns NO-GO; in that case REFAC-06 defers to v1.3.**
- [ ] **Phase 17: Final Live Re-verification × 4** — LIVE-01-equivalent gate post-migration; operator dispositions ambito/iol/higyrus/matriz; no new findings outside in-cycle classified set vs baseline `verification-cycle-2026-Q2` + v1.1 LIVE-01 head `71bf201`. LIVE-03.

## Phase Details

### Phase 12: Codegen Spike
**Goal**: Decide whether unasync/codegen single-source is feasible for v1.2 transport shells (`client.py`/`aio.py`) and capture the per-package configuration the eventual Phase 16 will consume — OR return NO-GO and defer REFAC-06 to v1.3.
**Depends on**: v1.1 head `71bf201` confirmed CI-green on Python 3.13 (operational gate); v1.1 Phase 7 `_core.py` extraction; v1.1 Phase 10 matriz `aio.py` 852 LOC.
**Requirements**: REFAC-06 (spike-gated decision artifact only; full implementation is Phase 16)
**Success Criteria** (what must be TRUE):
  1. A spike report under `.planning/phases/12-*/` records a single binary decision (GO or NO-GO for v1.2 Phase 16) signed off by the operator, with measurable evidence: ámbito round-trip generated `client.py` is byte-identical to v1.1 hand-written `client.py` modulo `ruff format` normalization.
  2. B8 identity invariant is preserved by the candidate tool on ámbito output: a parametric test `test_codegen_preserves_raise_for_response_identity[ambito_financiero_client]` reads the generated file and asserts `client._raise_for_response is aio._raise_for_response is _core.raise_for_response` (anti-Pitfall 4).
  3. Matriz worst-case audit enumerates every `aio.py` async-only construct (`asyncio.Lock`, `asyncio.to_thread`, `async with`, `_get_async_lock()`) and proves either (a) the tool emits a correct sync rewrite, OR (b) the construct lives in a file already in the codegen deny-list (`_token_store.py`, `_refresh_policy.py`, `ws_client.py`); no construct is unaccounted for (anti-Pitfall 6).
  4. If decision = GO: per-package `Rule(fromdir, todir, additional_replacements={...})` config is captured for all 4 packages, plus a draft of the `@generated by unasync` marker syntax that does not conflict with `from __future__ import annotations`.
  5. If decision = NO-GO: REQUIREMENTS.md and ROADMAP.md updated to defer REFAC-06 to v1.3; Phase 16 dropped from the schedule; Phase 17 unblocked to run immediately after Phase 14 + 15.
**Plans:** 3 plans
- [ ] 12-01-PLAN.md — Wave 0 + Wave 1: bootstrap SPIKE-005 directory + sub-experiment skeletons + MANIFEST registration + 12-VALIDATION.md fill + Ámbito round-trip experiment (001a) end-to-end (unasync round-trip + ruff format + diff + B8 identity assert)
- [ ] 12-02-PLAN.md — Wave 2 + Wave 3 + Wave 4: @generated marker × from __future__ compatibility (001b) + matriz construct audit ast.walk + operator triage zero-TBD merge gate (001c) + matriz deny-list intactness sha256 before/after (001d)
- [ ] 12-03-PLAN.md — Wave 5 + Wave 6: D-RIGOR-01 8-item evidence checklist execution + 1-day timebox check + operator GO|NO-GO signoff + GO branch wrap-up Skill + auto-load OR NO-GO branch REQUIREMENTS/ROADMAP/pending-todo updates + skill NO-GO flavor + 12-SUMMARY.md

### Phase 13: Cross-Package Ergonomics (`with_options(max_retries=N)`)
**Goal**: Operators can override `max_retries` per-call without re-instantiating Client, while the v1.1 mutation gate continues to prevent duplicate mutating requests under any override value.
**Depends on**: v1.1 Phase 8 `RetryTransport`/`AsyncRetryTransport` + `request.extensions["idempotent"]` mutation gate.
**Requirements**: ERG-01
**Success Criteria** (what must be TRUE):
  1. `client.with_options(max_retries=N).get_X(...)` returns a Client view that SHARES `_state.http_client` and `_state.token` with the parent (no resource leak, no re-auth) — verified by `test_with_options_shares_http_client_and_token` parametrized × 4 packages (anti-Pitfall 13).
  2. **CRITICAL merge gate**: `client.with_options(max_retries=10).new_order(...)` on matriz Primary executes EXACTLY 1 outgoing request when the upstream returns 503, regardless of the `max_retries=10` override — verified by `test_with_options_does_not_bypass_mutation_gate_matriz` (httpx_mock asserts `len(requests) == 1`). Anti-Pitfall 14 — duplicate-order money-on-the-line.
  3. `RetryTransport.handle_request` reads `max_attempts` from `request.extensions.get("max_attempts", self.max_attempts)`, falling back to the constructor default — mirrors v1.1 `idempotent` extension pattern.
  4. Per-package serial roll-out completes (ámbito → higyrus → matriz → iol; iol last because it interacts with Phase 14 disk cache): each package's mocked test suite stays green; the cross-cutting mutation-gate regression test lands ONCE in `verification/` and applies to all 4.
  5. v1.1's 907-test baseline is preserved (`pytest` reports ≥ 907 passing); the new tests are net-additive.
**Plans**: TBD

### Phase 14: IOL Disk Persistence (SEC-01)
**Goal**: An IOL operator restarting `main_iol.py` skips the password grant when a valid disk-cached `refresh_token` exists, without leaking the token to logs or losing it across concurrent processes.
**Depends on**: v1.1 BUG-03 in-instance refresh_token lifecycle; v1.1 LOG-02 `RedactingFilter`.
**Requirements**: SEC-01
**Success Criteria** (what must be TRUE):
  1. **CRITICAL merge gate (caplog no-leak)**: `test_disk_persistence_never_logs_token` exercises the full disk lifecycle (write-on-rotate → read-on-init → write-fail OSError → corrupt-file read) with `caplog.set_level(DEBUG, logger="iol_client")`, asserts the sentinel `REFRESH-TOKEN-SENTINEL-DO-NOT-LEAK-9876543210` never appears in any log record's message, args, or `repr(extra)` (anti-Pitfall 7).
  2. **CRITICAL merge gate (multi-process race)**: `test_disk_token_write_under_concurrent_processes` spawns 20 concurrent writer threads via `fcntl.flock`, asserts the resulting file contains exactly one valid token (no interleaved bytes, no truncation, no double-write corruption) — anti-Pitfall 9.
  3. **CRITICAL merge gate (failed-refresh cleanup)**: `test_disk_token_deleted_on_refresh_401` seeds disk with stale `STALE-REFRESH-TOKEN`, mocks IOL returning 401 on refresh, asserts disk file contains the fresh password-grant token after recovery (NOT the stale one) — anti-Pitfall 8.
  4. `Client(token_cache_path=Path(...))` opt-in kwarg + `IOL_TOKEN_CACHE_PATH` env var override + `platformdirs.user_data_dir("iol-client", "market-libs")` default; chmod 0600 on POSIX + parent dir 0700; CI detection (`os.environ["CI"]=="true"`) refuses default-path persistence (anti-Pitfall 10).
  5. 8+ regression tests cover the 4 v1.1 BUG-03 lifecycle paths × disk (refresh→success, refresh→401→password fallback, preserve-on-omit, rotate-on-provide) for both sync and async; `platformdirs >=4.0,<5` added to `packages/iol-client/pyproject.toml` runtime deps ONLY (other 3 packages unaffected).
**Plans**: TBD

### Phase 15: Driver Migration × 4 (REFAC-05)
**Goal**: An operator running any `main_*.py --live` constructs exactly one `Client()`/`AsyncClient()` instance per `main()` run; every probe shares that instance, finding-title stability is preserved against the v1.1 LIVE-01 baseline `71bf201`, and the v1.1 LOC-drop residual closes for iol (-5.1%) and matriz (-20%).
**Depends on**: v1.1 Phase 6 `Client`/`AsyncClient` classes + PEP 562 shim; v1.1 Phase 11 `verification/findings.py` append-only with BEGIN/END zones; Phase 13 `with_options()` (drivers use the new ergonomic).
**Requirements**: REFAC-05
**Success Criteria** (what must be TRUE):
  1. **CRITICAL merge gate (single-Client invariant)**: `test_main_<pkg>_uses_single_client_instance` AST-walker test exists for each of the 4 drivers and asserts at most 2 `Client()` / `AsyncClient()` constructor calls (1 sync + 1 async) per `main()` — anti-Pitfall 1 (OAuth churn IOL + TokenStore corruption matriz).
  2. **CRITICAL merge gate (probe-name stability)**: `git diff baseline..HEAD -- .planning/verification/*-findings.md` reports ZERO BEGIN/END-zone changes for unchanged-classification findings; probe names, finding IDs, finding titles are unchanged vs LIVE-01 baseline `71bf201` (anti-Pitfall 2 + anti-Pitfall 15: finding-title stability).
  3. Per-driver per-package serial completes (ámbito → iol → higyrus → matriz): each driver replaces all `pkg.get_X(...)` top-level calls + INT-01 idiom (`_get_default()._state.<attr>`) reads with `client.get_X(...)` + `client._state.<attr>` direct access; library back-compat shims STAY (PEP 562 + top-level delegators preserved per ARCHITECTURE §6).
  4. Each driver passes its existing per-package LIVE smoke at end of migration (operator-driven; not the milestone-final gate); v1.1 907-test baseline preserved across the milestone (`pytest` reports ≥ 907 passing).
  5. LOC-drop residual closes: iol `client.py` + `aio.py` aggregate LOC delta ≤ -30% vs v1.0 baseline; matriz `client.py` aggregate LOC delta ≤ -30% (operator-accepted thresholds from v1.1 Phase 7 SC#3 carry-forward).
**Plans**: TBD

### Phase 16: Codegen Single-Source (REFAC-06) — CONDITIONAL
**Goal**: ONE source of truth for sync/async transport shells × 4 packages — operators editing endpoint logic touch one file (`aio.py`), pre-commit regenerates `client.py`, CI verifies idempotency. **DROPPED if Phase 12 spike returns NO-GO.**
**Conditional**: This phase is DROPPED from the v1.2 schedule if and only if Phase 12 outputs a NO-GO decision; in that case REFAC-06 defers to v1.3 and Phase 17 (LIVE-03) runs immediately after Phase 14 + 15. If Phase 12 outputs GO, this phase runs after Phase 13 + 14 + 15.
**Depends on**: Phase 12 spike GO decision; Phase 13 (with_options surface stable); Phase 15 (driver migration validates public method surface before codegen masks API gaps); v1.1 Phase 7 `_core.py` extraction (codegen targets transport shells ONLY).
**Requirements**: REFAC-06
**Success Criteria** (what must be TRUE):
  1. **CRITICAL merge gate (generated marker + verify-clean)**: every generated transport shell starts with `# @generated by unasync from aio.py — DO NOT EDIT.`; CI job `lint-codegen` runs `make codegen && git diff --exit-code` as a separate job and fails the build on any drift — anti-Pitfall 5.
  2. **CRITICAL merge gate (B8 identity preservation)**: parametric `test_codegen_preserves_raise_for_response_identity` × 4 packages runs FIRST in CI and asserts `client._raise_for_response is aio._raise_for_response is _core.raise_for_response` after every codegen regeneration — anti-Pitfall 4.
  3. **CRITICAL merge gate (deny-list contract)**: `_token_store.py`, `_refresh_policy.py`, `ws_client.py` are in the codegen deny-list with an import-linter contract `[[tool.importlinter.contracts]]` blocking codegen-generated files from importing these primitives' sync/async halves separately; pre-commit hook rejects regen attempts that touch the deny-listed files (anti-Pitfall 6).
  4. Per-package serial roll-out (ámbito → iol → higyrus → matriz): each package's mocked test suite stays green after codegen replaces hand-written shells; mypy strict + ruff format pass on generated files; `unasync >=0.6.0,<0.7` added to root `[dependency-groups] dev`.
  5. Library-side LOC drop measurable: aggregate `client.py` LOC across 4 packages reduces by ≥ 30% vs Phase 15 baseline (operator-accepted threshold); 907-test baseline preserved.
**Plans**: TBD

### Phase 17: Final Live Re-verification × 4 (LIVE-03)
**Goal**: An operator running `main_*.py --live × 4` post-migration confirms no new findings outside the in-cycle classified set vs baseline `verification-cycle-2026-Q2` + v1.1 LIVE-01 head `71bf201`; the milestone v1.2 ships with audit `passed`.
**Depends on**: All preceding v1.2 phases complete (Phase 13 ERG-01 + Phase 14 SEC-01 + Phase 15 REFAC-05 + Phase 16 REFAC-06 if shipped).
**Requirements**: LIVE-03
**Success Criteria** (what must be TRUE):
  1. Operator dispositions captured for all 4 packages: ambito/iol/higyrus/matriz each return `no_new_findings` OR every new finding is classified CONFIRMED/FIXED/EXPECTED/NO-FIX with a regression test landed in this same phase (v1.0/v1.1 in-cycle pattern carries forward).
  2. Schema snapshot comparison vs baseline `verification-cycle-2026-Q2` reports zero new schema drift; `verify_cycle_closure × 4` PASS; cycle closure markers updated.
  3. v1.1 LIVE-01 finding IDs (4d48e07 → 71bf201) preserve operator dispositions (Classification/Rationale/Regression/Resolution) across the driver migration in Phase 15 + codegen in Phase 16 (if shipped) — verified via `verification/findings.py` append-only + content-addressed dedupe.
  4. Milestone audit `passed`: all v1.2 requirements (REFAC-05, SEC-01, ERG-01, LIVE-03, plus REFAC-06 if GO) reflected as Complete in REQUIREMENTS.md traceability table; integration audit reports 0 BLOCKER.
  5. `pytest` final count is ≥ Phase 16 baseline (or Phase 15 baseline if Phase 16 dropped); CI matrix green on Python 3.12 + 3.13.
**Plans**: TBD

## Progress

| Phase                                                       | Milestone | Plans | Status      | Completed  |
|-------------------------------------------------------------|-----------|-------|-------------|------------|
| 1. Safety Harness & Verification Infrastructure             | v1.0      | 4/4   | Complete    | 2026-05-28 |
| 2. Ámbito Verification                                      | v1.0      | 3/3   | Complete    | 2026-06-05 |
| 3. IOL Verification                                         | v1.0      | 3/3   | Complete    | 2026-06-06 |
| 4. Higyrus Verification                                     | v1.0      | 4/4   | Complete    | 2026-06-08 |
| 5. Matriz Verification                                      | v1.0      | 4/4   | Complete    | 2026-06-10 |
| 6. Compat Safety Net + Client Class Skeleton                | v1.1      | 7/7   | Complete    | 2026-06-11 |
| 7. `_core.py` Extraction — Sync/Async Logic Dedup           | v1.1      | 6/6   | Complete    | 2026-06-12 |
| 8. Retries, Backoff, Structured Logging                     | v1.1      | 6/6   | Complete    | 2026-06-13 |
| 9. Deferred Bug Fixes                                       | v1.1      | 4/4   | Complete    | 2026-06-13 |
| 10. matriz `aio.py` Creation + TokenStore                   | v1.1      | 4/4   | Complete    | 2026-06-14 |
| 11. Harness Hardening + Code Review + Live Re-verification  | v1.1      | 3/3   | Complete    | 2026-06-14 |
| 12. Codegen Spike                                           | v1.2      | 0/3   | Not started | -          |
| 13. Cross-Package Ergonomics (`with_options`)               | v1.2      | 0/?   | Not started | -          |
| 14. IOL Disk Persistence                                    | v1.2      | 0/?   | Not started | -          |
| 15. Driver Migration × 4                                    | v1.2      | 0/?   | Not started | -          |
| 16. Codegen Single-Source (CONDITIONAL on Phase 12)         | v1.2      | 0/?   | Not started | -          |
| 17. Final Live Re-verification × 4                          | v1.2      | 0/?   | Not started | -          |

## Backlog

*(Candidate items for next milestone; see `.planning/todos/pending/` + v1.0/v1.1 milestone audits deferred sections)*

### Deferred to v1.2+ (from v1.1 planning)

- prod-vs-remarkets verification (D-MATZ-27 REQUIRED handoff)
- `matriz_client.ws_client` live verification (WebSocket streaming en daemon thread)
- IOL refresh_token disk persistence (secure token storage)
- Generated-code parity tooling (one source, dual emit via unasync/codegen)
- Automatic `Idempotency-Key` header para retried POSTs
- `findings.toml` machine-readable side-file
- `client.with_options(max_retries=N)` per-call override (anthropic/openai pattern)
- `Client.from_env()` classmethod for explicit env-reading
- `request_id` UUID per `_request()` invocation threaded through retry log records
- `max_elapsed_seconds` retry budget cap as belt-and-suspenders
- Extender alcance de verificación a `wallets-client` (cuando tenga endpoints reales)
- ERR-01 (mocked 403/429/5xx mapping), ERR-02 (mocked token TTL refresh) — v2 requirements del v1.0 backlog

### Deferred from v1.1 close (operator-accepted, see audit)

- LOC drop residual (iol -5.1%, matriz client.py -20% vs target ≥30%) — back-compat shims; closes when drivers migrate to the `Client`/`AsyncClient` class directly (v1.2 driver migration target)
- v1.1 Phase 7/8/9 human verification items (CI matrix Python 3.13 confirmation × 3 phases, live retry smoke, log legibility subjective UX) — operator-acknowledged at v1.1 close in STATE.md `Deferred Items`
