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

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Plans | Key Change |
|-----------|----------|--------|-------|------------|
| v1.0 | ~13 days | 5 | 18 (37 closed-out) | Established the verification cycle (drivers + harness + DRIFT-02 baseline) |
| v1.1 | ~3.5 days | 6 | 30 | Architectural refactor + spike-before-plan + per-phase VALIDATION.md operator signoff |

### Cumulative Quality

| Milestone | Tests | Test delta | Requirements | Zero-Dep Additions |
|-----------|-------|------------|--------------|---------------------|
| v1.0 | 277 | +227 from baseline ~50 | 35/35 | (none — verification cycle) |
| v1.1 | 907/908 | +630 (vs v1.0 close) / +122 (vs Phase 9 baseline) | 29/29 | tenacity 9.1.4 (Apache-2.0, zero deps, py.typed) |

### Top Lessons (Verified Across Milestones)

1. **In-cycle fixes with regression tests.** Both v1.0 (24+ higyrus regressions in Phase 4, 19 matriz regressions in Phase 5) and v1.1 (8 BUG-03 lifecycle tests, 6 BUG-01 CFI edge-case tests + 16 parametric, 15 CR-06 AST guards) confirmed the same pattern: every discovered bug gets a mocked regression test in the same phase. Zero historical regressions surfaced in the v1.1 re-verification.
2. **Operator-driven classification beats automation for ambiguous findings.** v1.0 introduced the CONFIRMED/FIXED/EXPECTED/NO-FIX taxonomy. v1.1 BUG-02 (server returns HTTP 200 empty body — token scope, not client bug) validated that human triage with N=3 live calls produces correct verdicts that no automated heuristic would have caught.
3. **Per-package serial pattern.** v1.0 processed packages in ámbito → iol → higyrus → matriz order (smallest to largest blast radius). v1.1 Phase 6 and Phase 7 replicated the same order. Each package independent (no shared internals — by design); refactors replicate 4×, and that's fine because the failure modes stay isolated.
4. **DRIFT-02 cycle closure as a signal, not a failure.** v1.0 Phase 5 deferred F-09 deliberately and used `cycle_closure FAIL` as the explicit DRIFT-02 signal that the cycle detects its own gap. v1.1 Phase 9 BUG-01 closed F-09 + flipped that FAIL to PASS, validating the convention. Future cycles inherit the same pattern.
