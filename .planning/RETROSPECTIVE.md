# Project Retrospective — market-libs

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.1 — Tech Debt Cleanup

**Shipped:** 2026-06-14
**Phases:** 6 | **Plans:** 30 | **Tasks:** 52 | **Sessions:** ~3 days of dense work

### What Was Built

- **`Client`/`AsyncClient` classes per package** with `_ClientState` per-instance, backed by a PEP 562 `__getattr__` shim that preserves the top-level `pkg.get_X(...)` API 100%. Four packages: ámbito, iol, higyrus, matriz. Singleton state moved to a lazy default-client; the test suite stayed green at every commit.
- **`_core.py` extraction per package** — pure builders/parsers (`RequestSpec`, `raise_for_response`, `unwrap_envelope`, auth-flow helpers); `client.py`/`aio.py` collapse to transport shells calling `_core`. Import-linter v2.11 enforces 4 forbidden contracts (`_core` cannot import `client`/`aio`).
- **Retries + structured logging** — `tenacity 9.1.4` (zero deps, py.typed, Apache-2.0); full-jitter backoff; `Retry-After` cap at 60s; mutation gate via `request.extensions["idempotent"]`; per-package `RedactingFilter` over `logging.getLogger("<pkg>")` with `NullHandler`. matriz Risk API carve-out for no-401-reauth (D-23).
- **4 v1.0 deferred bugs closed** — BUG-01 (matriz CFI guard, hybrid Literal+regex pre-HTTP), BUG-02 (higyrus NO-FIX bucket (a) after live triage N=3), BUG-03 (IOL `refresh_token` lifecycle with 8 regression tests), BUG-04 (Higyrus multi-account per-call iteration).
- **matriz async REST + TokenStore 3-way concurrency** — `aio.py` grew from 103-LOC stub to 852 LOC full REST mirror; `_token_store.py` uses `threading.Lock` callable from sync REST, ws_client daemon thread, and asyncio context (via `asyncio.to_thread` offload + per-loop `asyncio.Lock`); `_refresh_policy.py` prevents auth-server DOS.
- **Harness + driver close-out** — `verification/findings.py` 640 LOC append-only with BEGIN/END zone parser, content-addressed `idempotent_by_title` dedupe, operator-field preservation cross-runs; 18 sweep probes refactored to a single helper; 27 sites of bare `except Exception` narrowed with AST regression-guard; LIVE-01 final gate × 4 packages PASS.

### What Worked

- **PEP 562 `__getattr__` shim** as the compat strategy — let the refactor land 4× without breaking a single existing consumer. Phase 6 fixture-reaches-production guard + golden public-surface snapshot caught monkeypatch silent breakage before it could ship.
- **`_core` ↔ `_transport` decoupling via `request.extensions`** — the transport reads `request.extensions.get("idempotent", False)` instead of importing `_core` types. Mutation gate is enforced without re-coupling.
- **Spike-before-plan for Phase 10** — the TokenStore 3-way concurrency primitive was the single architectural unknown. Auto-loaded `Skill("spike-findings-market-libs")` carried the validated recipe (threading.Lock + asyncio.to_thread + per-loop asyncio.Lock) directly into the plan. Zero design surprises during implementation.
- **Worktree isolation for parallel waves** — most plans ran in worktree-agent branches; concurrent edits never collided because each branch had its own checkout.
- **Per-phase atomic commits with hooks running normally** — pre-commit hooks (ruff + mypy) fired on every commit; CI stayed green throughout. No silent regressions.
- **Operator override mechanism** — BUG-02 NO-FIX (after live N=3 triage) and BUG-01 D-02 (guard in builder, not raise_for_response) were both operator-authorized deviations captured in VERIFICATION.md `overrides:` block. Clean audit trail, no ambiguity at milestone close.
- **INT-01 idiom (`_get_default()._state.base_url`)** caught a recurring driver-migration drift twice — once in quick-task 260613-nwb (15 sites in `main_iol.py`) and again as iol F-02 PROBE_STALE during the LIVE-01 final gate (one site at `main_iol.py:1289` shadowing PEP 562 `__getattr__`). The idiom is now a documented pattern, not a surprise.

### What Was Inefficient

- **Sync/async logic duplication is now structural debt.** Phase 7's `_core.py` extraction collapsed `client.py` + `aio.py` to thin shells, but each package still has *two* shells maintained side-by-side. The SC#3 LOC drop missed target (iol -5.1%, matriz client.py -20%) precisely because back-compat shims + PEP 562 + D-23 lifecycle were unremovable. v1.2 driver-migration + unasync/codegen is the right closure.
- **CI Python 3.13 confirmation deferred 3× phases** — Phase 7/8/9 each closed with the same pending UAT scenario (push + observe GitHub Actions matrix). All three could have been consolidated into a single deferred check at milestone close instead of one per phase.
- **Worktree cleanup-wave reliably blocked** — `gsd-sdk query worktree.cleanup-wave` failed on every plan that touched files also modified ambient in the working tree. The manual `rm + ff-merge` recipe (now memorized) worked, but cost extra ceremony each wave.
- **Quick task `260614-de5` DOC-02 scope expanded after the fact** — the audit said "flip 17 rows" but the real count was 18, and a follow-up commit was needed to flip 4 more body checkboxes that the audit assumed were already up to date. Better cross-checking before declaring a doc-sync scope.
- **VERIFICATION.md vs VALIDATION.md inconsistency at Phases 10/11** — operator chose to close those phases via `*-VALIDATION.md status: approved` + signoff, but the milestone audit's 3-source matrix expected `VERIFICATION.md`. Resolved by emitting 5-line shim files in DOC-04. Future phases should pick one artifact and stick to it.

### Patterns Established

- **PEP 562 compat shim** for any future Client/AsyncClient surface change — preserves top-level functions while moving state to instances.
- **`_core.py` builders/parsers + import-linter contracts** — enforced by CI, blocks the natural re-coupling drift.
- **Mutation gate via `request.extensions["idempotent"]`** — transport knows nothing about domain types; the flag lives on the httpx request.
- **Spike-before-plan flag** — for any plan with architectural uncertainty (concurrency, IPC, novel external API), spike first; auto-load findings into CLAUDE.md.
- **Per-phase VALIDATION.md frontmatter** as the operator signoff artifact — `status: approved` + `operator_signoff_date` + `operator_signoff_by` is materially equivalent to a passed VERIFICATION.md (need to harmonize the audit tooling so we don't write both).
- **INT-01 idiom (`_get_default()._state.base_url`)** as the canonical post-Phase-6 driver-side state access pattern. Document in CLAUDE.md for future drivers.
- **`verification/findings.py` append-only with BEGIN/END zones + `idempotent_by_title`** — re-runnable drivers without destroying operator annotations.
- **Operator override block in VERIFICATION.md frontmatter** — clean audit trail for documented deviations (`overrides:` array with `reason` + `accepted_by` + `accepted_at`).

### Key Lessons

1. **Compat shims have a half-life.** PEP 562 + back-compat function delegators let v1.1 land without breaking changes, but they also blocked the LOC-drop target on iol + matriz client.py. Document the residual as a v1.2 driver-migration target rather than fighting it phase-by-phase.
2. **Worktree isolation + working-tree mods don't mix** — `cleanup-wave` will block whenever the main checkout has ambient uncommitted edits to the same files. Either commit the ambient state before spawning the wave, or accept the manual `rm + ff-merge` workaround.
3. **The audit-as-doc-driver pattern works.** `/gsd-audit-milestone` surfaced 4 documentation follow-ups (DOC-01..04) with exact file paths; a single `/gsd-quick` resolved them all in 2 commits. The audit became the spec.
4. **Quick tasks compound.** Three quick tasks (260611-u0v CI fixes, 260613-nwb INT-01 hotfix, 260614-de5 DOC-01..04) closed v1.0 leftovers and milestone-close cosmetics that would otherwise have lived in deferred-items.md or polluted phase scope. Use them for crosscut work, not phase-shaped work.
5. **3-source cross-reference (VERIFICATION + SUMMARY + traceability) is sensitive to YAML keys.** SUMMARY.md `requirements_completed: []` empty arrays count as "missing" even when VALIDATION.md says otherwise. Backfill the frontmatter at phase close, not at milestone close.
6. **The `human_verification_pending` pattern in VERIFICATION.md frontmatter** is cleaner than ad-hoc tracking — each pending item gets a `test`, `expected`, and `why_human` field. CI Python 3.13 across 3 phases all used this format and stayed organized.

### Cost Observations

- Model mix this milestone (estimated from agent dispatch patterns): ~60% opus (planner + executor on substantive plans), ~35% sonnet (verifier, code-reviewer, integration-checker), ~5% haiku (utility tooling).
- Sessions: dense 3-day window 2026-06-11 → 2026-06-14; ~30 plan executions + ~3 quick tasks + 2 milestone audit re-runs.
- Notable: the v1.1 integration audit re-run after Phase 11 used a single sonnet pass over all 6 phases (covering 29 REQ-IDs end-to-end) — efficient consolidation vs running 6 per-phase checks.

---

## Milestone: v1.2 — Architecture + Auth/Ergonomics Carry-forwards

**Shipped:** 2026-06-25
**Phases:** 5 (12-15, 17; Phase 16 dropped) | **Plans:** 18 | **Tasks:** 40 | **Sessions:** ~11 days elapsed (2026-06-14 → 2026-06-25)

### What Was Built

- **Codegen tool-choice spike (Phase 12, REFAC-06 → NO-GO)** — SPIKE-005 ran an unasync round-trip on the ámbito canary + a matriz worst-case construct audit (109 rows, 0 unresolved); an 8-item D-RIGOR-01 evidence checklist returned 3/8 FAIL, all tracing to a single root cause (source-shape asymmetry: v1.1 `aio.py` was authored sync-first, unasync codegen runs async-first), with 0 unfixable hunks. Operator signed NO-GO; REFAC-06 cleanly deferred to v1.3 with a libcst handoff scope + an auto-loaded findings skill.
- **`client.with_options(max_retries=N)` × 4 (Phase 13, ERG-01)** — shallow-clone Client/AsyncClient "view" (`_is_view`) sharing the parent's `httpx.Client` + `_ClientState` + token; the override threads via `request.extensions["max_attempts"]` (mirror of the v1.1 `idempotent` extension). CRITICAL merge gate: matriz `new_order` under 503 executes exactly 1 request regardless of `max_retries=10`.
- **IOL refresh_token disk persistence (Phase 14, SEC-01)** — `_token_cache.py` with atomic write-then-rename, `fcntl.flock`, 0600 perms, `platformdirs` default, CI-refuses-default-path; 3 CRITICAL gates (caplog no-leak, 20-thread race, failed-refresh cleanup) GREEN across sync + async via `asyncio.to_thread`.
- **Driver migration × 4 (Phase 15, REFAC-05)** — every `main_*.py` builds exactly one `Client()`/`AsyncClient()` per run with probes threaded through; per-driver AST single-Client guard (matriz hardened to non-vacuous after WR-01/WR-02 + plan 15-05 migrated the 18 matriz sync sweep probes off the singleton); finding-title stability static-clean vs `71bf201`.
- **Final live re-verification × 4 (Phase 17, LIVE-03)** — operator dispositions captured for all 4 packages, schema snapshot vs baseline `verification-cycle-2026-Q2` clean, `verify_cycle_closure × 4` PASS, traceability flip + 0-BLOCKER integration audit, pytest ≥989 / CI green on 3.12 + 3.13.

### What Worked

- **Spike-before-plan honored a NO-GO.** The single architectural unknown (codegen) was gated by a measurable 8-item checklist read strictly. When 3 items failed, the operator took the NO-GO rather than shipping fragile token-replacement codegen — and the failure analysis became the v1.3 libcst spike's scope. The spike paid for itself by *preventing* work.
- **The `request.extensions` extension pattern composed cleanly.** ERG-01's `max_attempts` override reused the exact transport-decoupling mechanism v1.1 established for the `idempotent` mutation gate — no new coupling, and the two extensions interact correctly (idempotent evaluated FIRST, so `max_retries` can't bypass the duplicate-order guard).
- **AST regression-guards as merge gates.** Phase 15's "ONE Client per `main()`" invariant is mechanically enforced per driver instead of by convention; the matriz guard was caught being *vacuous* in code review and hardened — exactly the kind of silent gap a guard test should surface.
- **Phase 16 drop was frictionless.** Because the NO-GO landed at Phase 12 (early) and the roadmap had Phase 16 modeled as CONDITIONAL, dropping it just unblocked Phase 17 to run immediately after 14+15 — no re-planning churn.
- **Industry-survey-driven scope cut.** `Client.from_env()` was on the roadmap but a 7-SDK survey found zero precedent and the constructor already does implicit env fallback; cutting it avoided a redundant public surface.

### What Was Inefficient

- **REFAC-06 round-trip cost a full phase to reach NO-GO.** The spike was the right call, but the source-shape asymmetry root cause (sync-first `aio.py` authored in v1.1 Phase 7) was a *predictable* consequence of how v1.1 extracted `_core.py`. A note in the v1.1 retrospective could have flagged the codegen-direction risk before v1.2 planning committed Phase 16.
- **Phase 15 needed a 5th plan (15-05) to close the matriz carve-out.** The 18 matriz sync sweep probes still hit the module singleton after the first pass, making the AST guard vacuously pass. Caught in review, but the initial plan under-scoped matriz's two-login problem.
- **Stale quick-task status files persisted into a second milestone close.** The same 3 v1.1-era quick-tasks the SDK reports as "missing" surfaced again at v1.2 close (now 4), still false-positives. The SDK heuristic should be fixed or the directories normalized rather than re-acknowledging them every milestone.
- **Phase 15 HUMAN-UAT left 4 operator scenarios partial** and was only superseded (not closed) by the Phase 17 LIVE-03 gate. The per-phase UAT and the milestone-final gate overlapped; the phase-level UAT could have deferred those scenarios explicitly to LIVE-03 instead of sitting partial.

### Patterns Established

- **CONDITIONAL phase modeling.** Roadmap phases gated on a spike outcome (Phase 16 on Phase 12) drop cleanly with zero re-planning when the spike says no. Model spike-dependent work as CONDITIONAL from the start.
- **`request.extensions["<knob>"]` as the per-request override channel** — generalized from `idempotent` (v1.1) to `max_attempts` (v1.2). The transport reads `request.extensions.get(...)` with a constructor fallback; domain code stays out of the transport.
- **Shared-view clone (`_is_view`)** for ergonomic per-call config — clone shares `httpx.Client` + state + token; no resource leak, no re-auth. Verified by `test_with_options_shares_http_client_and_token`.
- **Non-vacuous AST guard discipline** — an AST invariant test must be checked that it actually fails when the invariant is violated (matriz guard was vacuous until hardened). Add a "guard fails RED on a counterexample" assertion.
- **Plaintext + 0600 + flock over keyring/Fernet** for developer/CI-tool secret-at-rest when the trust boundary already equals plaintext `.env`. Documented threat-model rationale; encryption deferred to explicit operator authorization.

### Key Lessons

1. **A spike that returns NO-GO is a success, not a wasted phase** — provided the failure analysis feeds the next attempt. Phase 12's root-cause writeup *is* the v1.3 libcst spike spec.
2. **Codegen direction must match source authoring direction.** unasync transforms async→sync; `aio.py` authored sync-first (because v1.1 extracted `_core.py` from the sync shell) creates an asymmetry token-replacement can't bridge. libcst (AST-level, whitespace-preserving) is the v1.3 bet.
3. **Invariant tests can pass vacuously.** "ONE Client per run" enforced by an AST walker is only as good as the assertion that it counts the right nodes — matriz's singleton-path references slipped through until a second guard (`test_main_matriz_has_no_singleton_path_references`) was added.
4. **Audit false-positives accrue across milestones.** The SDK's "missing" quick-task heuristic has now been acknowledged at two consecutive milestone closes for the same directories. Recurring acknowledgements are a smell — fix the source.
5. **Model conditional work as conditional.** Because Phase 16 was CONDITIONAL on Phase 12 from roadmap creation, the NO-GO cost nothing to absorb. Optionality in the plan is cheap insurance against spike outcomes.

### Cost Observations

- Model mix (estimated): ~60% opus (planner + executor on Phases 13-15), ~35% sonnet (verifier, code-reviewer, integration-checker, the Phase 12 evidence collection), ~5% haiku (utility tooling). Phase 12's spike sub-experiments leaned sonnet for the mechanical audit + diff work.
- Sessions: spread over ~11 elapsed days (2026-06-14 → 2026-06-25), denser than v1.1's 3-day window — Phase 14/15 ran across multiple days with operator-driven live gates between waves.
- Notable: dropping Phase 16 removed an entire codegen implementation phase (the most expensive modeled work in v1.2) on the strength of a single well-scoped spike — the highest-leverage cost decision of the milestone.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Plans | Key Change |
|-----------|----------|--------|-------|------------|
| v1.0 | ~13 days | 5 | 18 (37 closed-out) | Established the verification cycle (drivers + harness + DRIFT-02 baseline) |
| v1.1 | ~3.5 days | 6 | 30 | Architectural refactor + spike-before-plan + per-phase VALIDATION.md operator signoff |
| v1.2 | ~11 days | 5 (Phase 16 dropped) | 18 | CONDITIONAL phase modeling + spike NO-GO honored + per-request `extensions` override channel |

### Cumulative Quality

| Milestone | Tests | Test delta | Requirements | Zero-Dep Additions |
|-----------|-------|------------|--------------|---------------------|
| v1.0 | 277 | +227 from baseline ~50 | 35/35 | (none — verification cycle) |
| v1.1 | 907/908 | +630 (vs v1.0 close) / +122 (vs Phase 9 baseline) | 29/29 | tenacity 9.1.4 (Apache-2.0, zero deps, py.typed) |
| v1.2 | ≥989 | +82 (vs v1.1 close) | 4/4 (REFAC-06 → v1.3) | platformdirs >=4.0,<5 (iol-client only) |

### Top Lessons (Verified Across Milestones)

1. **In-cycle fixes with regression tests.** Both v1.0 (24+ higyrus regressions in Phase 4, 19 matriz regressions in Phase 5) and v1.1 (8 BUG-03 lifecycle tests, 6 BUG-01 CFI edge-case tests + 16 parametric, 15 CR-06 AST guards) confirmed the same pattern: every discovered bug gets a mocked regression test in the same phase. Zero historical regressions surfaced in the v1.1 re-verification.
2. **Operator-driven classification beats automation for ambiguous findings.** v1.0 introduced the CONFIRMED/FIXED/EXPECTED/NO-FIX taxonomy. v1.1 BUG-02 (server returns HTTP 200 empty body — token scope, not client bug) validated that human triage with N=3 live calls produces correct verdicts that no automated heuristic would have caught.
3. **Per-package serial pattern.** v1.0 processed packages in ámbito → iol → higyrus → matriz order (smallest to largest blast radius). v1.1 Phase 6 and Phase 7 replicated the same order. Each package independent (no shared internals — by design); refactors replicate 4×, and that's fine because the failure modes stay isolated.
4. **DRIFT-02 cycle closure as a signal, not a failure.** v1.0 Phase 5 deferred F-09 deliberately and used `cycle_closure FAIL` as the explicit DRIFT-02 signal that the cycle detects its own gap. v1.1 Phase 9 BUG-01 closed F-09 + flipped that FAIL to PASS, validating the convention. Future cycles inherit the same pattern.
5. **Spike-before-plan works in both directions.** v1.1 Phase 10 spiked the TokenStore concurrency primitive → GO, and the validated recipe dropped straight into the plan with zero design surprises. v1.2 Phase 12 spiked unasync codegen → NO-GO, and the failure analysis became the v1.3 libcst spike scope. The flag earns its cost whether the answer is yes or no — model the dependent work as CONDITIONAL so a NO-GO drops cleanly (Phase 16 cost nothing to absorb).
6. **The per-request `request.extensions[...]` channel is the decoupling pattern.** v1.1 introduced it for the `idempotent` mutation gate; v1.2 reused it for `max_attempts`. The transport stays ignorant of domain types while callers thread per-call knobs through the httpx request object. Default to this for any future per-call override.
