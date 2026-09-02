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

## Milestone: v1.3 — Codegen Single-Source (libcst)

**Closed:** 2026-07-03 (on a signed NO-GO)
**Phases:** 1 (Phase 18; Phase 19 REFAC-06 dropped) | **Plans:** 3 | **Tasks:** 7

### What Was Built

Nothing shipped to production — and that was a valid, guaranteed milestone outcome. v1.3 was a single spike-before-plan phase (SPIKE-006) that evaluated `libcst >=1.8.0,<2` as an AST-level codemod for single-sourcing the sync/async transport shells, against a 10-item `D-RIGOR-02` evidence gate. It produced: (1) a spike tree inheriting ~60% of the SPIKE-005 harness — matriz construct audit (item 10a, 0 unresolved), `@generated` marker via `libcst.Module.header` (item 8, STRICT PASS), 4-file deny-list sha256 byte-identity (item 10b); (2) five pure `CSTTransformer` subclasses + an impure driver transforming the un-migrated ámbito `aio.py` into a candidate `client.py`; (3) an honest gate transcript — 7 PASS / 3 FAIL; and (4) an operator-signed NO-GO decision + close-out. REFAC-06 is permanently shelved; the duplicate shells are accepted as a structural feature.

### What Worked

- **Two-tool convergence as strong evidence.** unasync (SPIKE-005) and libcst (SPIKE-006) are architecturally different codemod tools, yet both hit the same strict-D-04 NO-GO for the same root cause (content-absence: `_validate_max_retries` def + `load_dotenv` bootstrap live only in `client.py`). Reaching the same answer twice, from two directions, turns "this tool can't do it" into "the source-shape asymmetry is intrinsic" — a far more durable decision.
- **Honest transcript discipline.** The executor never synthesized the content-absent constructs from a `client.py` donor or by editing `aio.py` (D-02). It let items 1/6 FAIL truthfully rather than manufacturing a GO. The NO-GO is trustworthy precisely because the harness refused to cheat.
- **Inheritance from the prior spike.** ~60% of the harness (marker design, audit.py, deny-list sha256 skeleton) carried over verbatim from SPIKE-005 via the auto-loaded findings skill — the second spike was cheap because the first one's learnings were captured as a reusable artifact.
- **Zero production footprint by construction.** libcst stayed ephemeral (`uv run --with libcst`, never added to dev deps per D-05); the whole milestone lived under `.planning/spikes/`. A NO-GO milestone left the codebase byte-identical.

### What Was Inefficient

- **The outcome was ~70% predictable going in.** The v1.2 Phase 12 NO-GO analysis already identified the content-absence root cause and flagged items 1/4/6 as the gap libcst would have to close. libcst closed item 4 (the mechanical `ruff check` asymmetry) but items 1/6 were always going to hinge on synthesizing absent content — which no pure transform can do. The spike was still worth running (it converted a strong hypothesis into signed evidence, and item 4 was a genuine unknown), but the dominant result was foreseeable.
- **Single-phase milestone overhead.** Wrapping one spike phase in a full milestone (requirements → roadmap → discuss → plan → execute → close) is heavy ceremony for a binary decision. The structure paid off in traceability but the process-to-payload ratio was the highest of any milestone.

### Patterns Established

- **CONDITIONAL-phase drop on NO-GO, milestone-scale.** v1.2 dropped a single phase (16) on a spike NO-GO; v1.3 closed an *entire milestone* on one — Phase 19 dropped, milestone closes on the signed decision. The "spike is the guaranteed deliverable; implementation is CONDITIONAL" model scales up cleanly to a whole milestone.
- **`--force` milestone close for by-design dropped phases.** `milestone.complete` treats a dropped conditional phase as "unstarted" and blocks; `--force` is the correct override when the drop is intentional and recorded. Worth remembering for any future spike-gated milestone.
- **Two independent tools before shelving permanently.** Before accepting an architectural limitation as permanent, prove it with two genuinely different tools. One NO-GO is "maybe the tool"; two is "the source."

### Key Lessons

1. **A NO-GO milestone is a real deliverable.** v1.3 shipped no code and that's a success, not a failure — the operator now has a signed, evidence-backed decision that the sync/async duplication is intrinsic and REFAC-06 should never be re-opened without a new tool class or relaxing D-02. That decision has lasting value: it stops future cycles from re-litigating the same question.
2. **Capture spike learnings as reusable skills.** The `spike-findings-codegen-market-libs` skill made SPIKE-006 ~60% cheaper than SPIKE-005. The discipline of writing findings to an auto-loaded artifact compounds across milestones.
3. **Predictable spikes still earn their cost when they convert hypothesis → signed evidence.** The result was ~70% foreseeable, but the 30% (does libcst close item 4?) was a genuine unknown, and turning "we think unasync's failure generalizes" into "two tools prove it does" is what lets you shelve permanently with confidence.

### Cost Observations

- Model mix (estimated): ~55% opus (planner + executor authoring the CSTTransformer suite), ~40% sonnet (the mechanical audit / diff / transcript-capture work, well-suited to the honest-evidence collection), ~5% haiku (utility). The genuinely-new work (Plan 18-02's transformer suite) was the opus-heavy slice.
- Sessions: ~1 elapsed day (2026-07-02 → 2026-07-03), the tightest milestone — a single spike with three sequential plan waves.
- Notable: the highest process-to-payload ratio of any milestone (full milestone ceremony around one binary decision), offset by ~60% harness inheritance from SPIKE-005 and zero production risk.

---

## Milestone: v1.4 — market-data-client

**Shipped:** 2026-07-31
**Phases:** 5 (20-24) | **Plans:** 16 | **Tasks:** 36 | **Sessions:** ~3 days (2026-07-29 → 2026-07-31)

### What Was Built

The first **greenfield package** since the verification cycle began — `market-data-client v0.1.0`, the 6th monorepo package, publicly released. Rather than verifying an existing client, v1.4 *authored* one by mirroring every architectural decision already proven across the other five: `Client`/`AsyncClient` classes with `_ClientState`, a pure IO-free `_core.py` (builders/parsers), the `RetryTransport`/`AsyncRetryTransport` full-jitter pair, per-package `RedactingFilter`, `configure()`, `with_options(max_retries=N)`, and the PEP-562 public surface. The auth flavor is new — **Auth0 `client_credentials`** single-grant (vs IOL's OAuth refresh_token) — with a TTL-cache token lifecycle in both surfaces (per-loop double-checked `asyncio.Lock`). Scope was deliberately **read-only**: 10 endpoints (health + market-data + reference-data) × sync/async, with tolerant `SafeModel` dataclasses (market-data snapshots carry client-stamped `received_at`; reference/catalog models don't, D-05). Phase 23 stood up the 6th live-verification driver (`main_market_data.py`) reusing the whole `verification/` harness, and Phase 24 published via the existing per-package tag pipeline under a gated human go/no-go.

### What Worked

- **Verbatim mirroring of a proven package as the scaffolding strategy.** Copying `iol-client`'s shape (down to the `_core`/transport/logging split) meant zero architectural risk — every decision was already battle-tested across 5 packages and 3 milestones. The intentional 4×→6× duplication (no shared internals, by design) paid off exactly as the constraint predicted: the new package inherited correctness without a shared-library refactor.
- **TDD data layer, then public surface.** Phases 21/22 both split into a RED→GREEN pure `_core` builders/parsers wave followed by a thin public-surface wave (3-line dispatch methods). The pure layer was fully testable before any client wiring existed, and the public surface became mechanical.
- **Debt folded forward, not deferred indefinitely.** Phase-20 debts D-09 (async header token precedence) and D-10 (permanent 401 re-auth regression tests) were closed in Phase 21 rather than carried to close — the debt list stayed short.
- **In-cycle code review caught a real never-FAILED defect.** Phase 23's advisory review + verifier both surfaced CR-01 (post-request `_emit_shape`/`_write_schema_snapshot` running *outside* the probe try, so a corrupt baseline would crash the driver to FAILED) — fixed in-cycle and locked with a non-vacuous AST regression guard. The review wasn't ceremony; it found a latent crash.
- **Gated human go/no-go for the irreversible publish.** Wave 2 of Phase 24 ran fully mechanical prep autonomously (CI matrix, docs, lockfile validation) but stopped hard before merge-to-main + tag-push — the two ops that trigger a public GitHub Release. Explicit "approved" gated the irreversible step; `release.yml` stayed unedited (D-02).

### What Was Inefficient

- **LIVE-MD-01 could not fully close.** The live-verification requirement shipped its *apparatus* (verifier 12/12) but never ran a real credentialed sweep against develop — Auth0 creds + VPN/allowlist weren't available in-repo. This was a known risk flagged at milestone kickoff (STATE.md blocker), so it didn't derail the plan, but it means one of six requirements is "verified by construction / offline-SKIP" rather than "verified live." The publish (PUB-MD-01) was correctly made independent of it, but the gap is real and carries to v1.5+.
- **Model field shapes were provisional through three phases.** With the API's *responses* untyped in the OpenAPI (only request schemas), the `SafeModel` field names were designed against inference in Phases 21/22 and meant to be reconciled against real payloads in Phase 23 — but Phase 23 hit the SKIP path, so the models remain bounded-by-tolerance rather than confirmed against wire data. `from_api` tolerance de-risks this, but it's unverified surface.
- **Auto-extracted accomplishments needed hand-cleaning.** The `milestone.complete` CLI pulled two code-review bullet artifacts ("[Rule 1 - Bug]…", "[Rule 3 - Blocking]…") into the MILESTONES.md accomplishment list from SUMMARY files. Minor, but the summary-extract heuristic isn't discriminating between deliverables and in-summary review notes.

### Patterns Established

- **Greenfield-by-mirroring.** When the monorepo already encodes a mature package shape, a new package is a *mirror + adapt-the-auth-flavor* exercise, not a from-scratch design. The read-only scope + provisional-models + live-reconcile sequencing is now a reusable template for the next client package.
- **Offline-SKIP as a first-class verification outcome.** Like v1.3's NO-GO, Phase 23's `require_env`-SKIP / D-09 NO-DATA path is a *sanctioned* result: zero fabricated diffs, `verify_cycle_closure` passes vacuously, the runner classifies SKIPPED (never FAILED). A verification driver that can't reach live data must degrade honestly, not fake success.
- **Autonomous prep + gated irreversible ops within one phase.** Phase 24 split a single phase into an autonomous wave (reversible edits) and a human-gated wave (merge + tag). This is the right shape for any release phase.

### Key Lessons

1. **The intentional-duplication constraint is a feature at package-creation time.** What reads as "tech debt" (no shared internals, logic duplicated 6×) is exactly what made adding the 6th package low-risk — there was a complete, proven template to copy and nothing shared to break. The constraint that costs on every logic fix pays back on every new package.
2. **Make the publish independent of the flakiest requirement.** LIVE-MD-01's live sweep was blocked on external access (creds + VPN); PUB-MD-01 was deliberately scoped to not depend on it. Shipping v0.1.0 didn't wait on an environment blocker outside the team's control — the right call, and a pattern for any release gated behind third-party access.
3. **Untyped API responses mean models stay provisional until live-reconciled — plan for the round-trip.** The OpenAPI typed only requests; models were inference-designed and meant to firm up against real payloads. When that live step can't run, `SafeModel` tolerance is the safety net, but the surface is unconfirmed — carry it explicitly rather than claiming it validated.

### Cost Observations

- Model mix (estimated): ~50% opus (planners + executors authoring the new package's `_core`/client/aio/models across 5 phases), ~45% sonnet (the mechanical mirror-and-adapt work, TDD test authoring, driver wiring — well-suited to copying a proven template), ~5% haiku (utility). The genuinely-new slices (Auth0 client_credentials lifecycle, `received_at` client-stamping, the D-09 driver-hardening fix) were the opus-heavy work.
- Sessions: ~3 days (2026-07-29 → 2026-07-31), 5 phases with Phases 21/22 parallelizable (both depend only on 20).
- Notable: the first milestone to *ship a public release* since the package set was defined — highest external-visibility payload, lowest architectural risk (pure mirror), with the one soft spot (LIVE-MD-01) fully attributable to an external-access blocker rather than any planning gap.

---

## Milestone: v1.6 — Tipado homogéneo de la superficie pública

**Shipped:** 2026-08-27
**Phases:** 6 | **Plans:** 44

### What Was Built
Field-level decoder (`_decode.py` walker) retrofitted as the primary decode engine across all 6 packages, replacing silent field substitution with structured observable logging (Phase 29). `iol-client`'s full public surface (16 signatures) migrated to typed attribute access, closing 5 consecutive self-declared leak-guarantee gap cycles along the way (Phase 30). 5 ops endpoints across `higyrus-client`/`market-data-client` now return typed models; all 6 packages gained uniform `models.py`+`types.py` (Phase 31). 4 CI gates now enforce the homogeneity permanently: decode-intactness, uniform-structure, AST surface-types (zero `Any`/`dict[str,Any]` exported), sync/async parity — plus a 4-list enrollment reconciliation (D-16) (Phase 32). Every change live-verified against real APIs in strict-decode mode, surfacing and fixing 3 real shape divergences in `market-data-client` before shipping (Phase 33). `iol-client` v0.3.0 + `market-data-client` v0.5.0 published through the release pipeline under two genuinely independent human approvals (Phase 34).

### What Worked
- Tracer-first phase decomposition (one production-quality end-to-end slice before expansion) caught real gaps early in Phases 29-30 rather than after full breadth was built.
- The count-based CI gate pattern (`TOTAL=N && PASSED=N`, never absence-of-"fail") — reused since v1.4 — caught two more live degenerate cases this milestone: a genuine pre-existing mypy failure and a transient "zero checks reported" race that an absence-of-failure check would have read as green.
- Explicit `gate="blocking-human"`-equivalent override by the orchestrator when a plan's checkpoint attribute didn't match its own stated intent (D-08) — caught before any irreversible action, not after.
- Live install-and-behavior verification of published wheels as a UAT step (fresh venv, install from the actual public Release URL) caught nothing new here but is now a repeatable pattern for future release phases.

### What Was Inefficient
- The `gate="blocking"` vs `gate="blocking-human"` authoring inconsistency appeared on both of Phase 34's checkpoints — a template/pattern fix (not a one-off plan fix) would prevent relying on the orchestrator to catch it every time.
- The `.github/workflows`-wide diff assertion pattern (checking zero change since a prior release tag) produced 3 false positives in one phase because it inherits a single-package-release baseline that doesn't account for legitimate intervening CI work across multiple releases. Needs a narrower per-file assertion form.
- `requirements mark-complete` short-circuits on `already_complete`, leaving the REQUIREMENTS.md traceability table stale for 5 requirements across the milestone — only caught during the final milestone audit, not at any individual phase close.

### Patterns Established
- Per-field decoder walker as the canonical "observable, never silent" decode primitive — now the template for any future package's `from_api`.
- Two-gate (not N-gate) irreversible-ops pattern for multi-artifact releases: one gate per operation *type* (merge, tag-push), not one per artifact — D-08 explicitly generalized this from the single-package v1.4/v1.5 precedent to two packages in one phase.
- Post-execution code review as a standing phase-completion step (not optional) — found a live bug on `main` in Phase 34 that would have shipped invisibly otherwise.

### Key Lessons
- A milestone's own docs can silently defer the same gap through multiple phases without ever closing it (the `verification/` matriz harness, broken since Phase 15, re-discovered and re-deferred at Phases 30/31/32) — a milestone audit is the right place to surface this pattern explicitly, even when it doesn't block shipping.
- When a sibling package gets a release-prep upgrade (README, memory doc, version test) and another published package in the same phase doesn't, that asymmetry is worth flagging even if fixing it is out of the current phase's declared scope (`iol-client` WR-03/04/05).

### Cost Observations
- Sessions: 1 continuous session covering discuss→plan→execute→verify→audit→complete for the milestone's final phase plus milestone close.
- Notable: this was the first milestone where a milestone-close code review found and fixed a live bug on `main` as part of closing, rather than deferring it — the fix shipped via a lightweight docs-only follow-up PR (#13) rather than blocking the milestone close.

---

## Milestone: v1.7 — API tipada con Null Objects

**Shipped:** 2026-08-30
**Phases:** 6 | **Plans:** 28

### What Was Built
`SafeModel.__bool__`/`empty()` — falsy-when-empty Null Object semantics — landed verbatim across all 4 base-class hierarchies in the 6 packages, with the `_decode` walker updated so a legitimate `null`/absent value on a non-optional model/list field collapses silently to an empty instance while a wrong-typed value still diverges and stays fatal under `strict_decode` (Phase 35, zero public-surface change). `market-data-client`'s `market_data` field moved from `dict[str, Any] | None` to a typed `MarketDataEntries`/`BookLevel`/`EntryValue` model with 6 ergonomic alias properties, formally revoking the v1.6/Phase-33 `| None` widening wherever it broke a chain link (Phase 36). `matriz-client` typed its last residual `dict[str, Any]` fields and gained the same 6 aliases shared by REST and WS frames (Phase 37). `iol-client`'s `puntas` became a proper Null Object/list, and higyrus/ámbito/wallets got a field-by-field disposition census (Phase 38). Live deep-chain verification against real APIs (Phase 39) found and fixed a genuine data-loss bug — matriz silently dropping ~9160 instrument identifiers — and widened the D-MATZ-33 security gate from substring-match to an exact-hostname allowlist, unblocking matriz's first live run since v1.0. Four packages shipped breaking releases with migration tables under double human gate (Phase 40).

### What Worked
- Revoking a prior milestone's own locked decision (v1.6/F33's `| None` widening) *by field role* rather than wholesale — chain-link fields got Null Object, leaf fields kept `T | None` — preserved the parts of the prior decision that were still correct instead of reopening the whole design.
- The load-bearing-phase-first structure (Phase 35 touches all 6 packages' base classes; 36/37/38 parallelize on disjoint packages once 35 lands) let three independent-package phases ship the same day without file conflicts.
- Widening a security gate from substring-match to an exact-hostname allowlist (D-MATZ-33, Phase 39 D-02) unblocked real live coverage without weakening the control — the fix was *stricter*, not looser, and it's what let the matriz data-loss bug get found at all.
- A milestone-close audit that distinguishes a **process gap** (missing retroactive VERIFICATION.md) from a **substance gap** (broken functionality) — and resolves it by actually re-verifying live state rather than just writing the missing document — kept the close honest instead of papering over an unknown.

### What Was Inefficient
- Phase 40 shipped without a retroactive `40-VERIFICATION.md`, breaking the pattern every prior release phase (Phase 28, Phase 34) had established — caught only by the milestone-close audit, not at phase-close time. A per-phase checklist item ("does this release phase have its VERIFICATION.md?") would catch this before the audit has to.
- The installed `gsd-tools.cjs` version's `milestone complete` CLI contract (no `--archive-quick`, opt-in-only `--archive-phases` with no `--no-` variant) didn't match what the complete-milestone workflow doc assumed — required falling back to manual `git mv` for both phase and quick-task archival. A version-skew check at the top of the workflow would save a debugging detour next time.
- 8 quick-task directories spanning v1.1 through v1.4 (2026-06-11 → 2026-07-31) had never been archived at any of the 3 intervening milestone closes — quick-task archival being opt-in-default-off means it silently accumulates unless someone explicitly opts in each time.

### Patterns Established
- **Field-role-scoped revocation**: when un-doing a prior milestone's locked decision, split the decision by the dimension that actually matters (chain-link vs. leaf) instead of reverting uniformly — keeps what worked, fixes what didn't.
- **Security-gate widening as unblock mechanism**: converting an overly-broad-but-wrong match (substring) to a narrower-but-correct one (exact allowlist) can simultaneously tighten security *and* unblock previously-inaccessible verification coverage — these aren't in tension when the original gate was imprecise rather than appropriately conservative.
- **Retroactive verification at milestone-close for audit-flagged process gaps**: when `/gsd-audit-milestone` finds a phase missing its VERIFICATION.md, spawn the verifier fresh against live state (git, GitHub API, actual package installs) rather than trusting the SUMMARY.md narrative — this is what separates "the document is missing" from "the thing it would have documented is actually fine."

### Key Lessons
- A backlog item can be *partially* resolved by a later milestone without becoming fully closeable — `LIVE-MATZ-33` went from fully-blocked to partially-measured (S-3/S-5 closed, S-4/RESPONSE-Literal census still open) in Phase 39; the backlog entry needs updating to reflect partial progress, not left stale claiming the original full blockage, and not prematurely marked resolved either.
- Live verification is where structural findings from an earlier phase's *offline* sizing estimate (`29-SIZING.md`'s ratified floor) get contrasted against what actually happened — and the milestone needs to explicitly account for how many divergences vanished *by policy* (Null Object collapse) vs. by *real correction*, or a declining defect count reads as false cleanliness instead of a mix of genuine fixes and a changed measurement baseline.

### Cost Observations
- Sessions: 1 continuous session covering Phase 39 live verification through Phase 40 release through milestone close (including a mid-close detour to backfill the missing Phase 40 verification).
- Notable: this is the first milestone where the close itself commissioned new verification work (the retroactive `40-VERIFICATION.md`) rather than just documenting what phases had already produced — the audit's gaps_found status was treated as an action item, not a formality to acknowledge past.

---

## Milestone: v1.8 — Cierre de deuda post-v1.7

**Shipped:** 2026-09-02
**Phases:** 5 | **Plans:** 24

### What Was Built
Every backlog item v1.7 closed with a *measured cause* got a matching measured disposition, with zero new product surface added to any client. Phase 41 ran `/gsd-validate-phase` retroactively across the 5 v1.7 phases (35-39) that never ran it, disposing 62 map rows into `VERIFIED-NOW` (54) / `VERIFIED-HISTORICALLY` (4) / `NOT-VERIFIABLE-RETROACTIVELY` (4) — with zero mechanical `nyquist_compliant` flips and the v1.7 source tree byte-unchanged throughout. Phase 42 ported matriz's census-script venue gate to exact-hostname equality *before* running the matriz `Literal`-value census against the `bbsa` sandbox (finding 8 vendor-emitted values outside the declared alias sets — the D-lock from v1.6 reaffirmed, not revoked) and re-measured higyrus's DNS blocker (still `SKIPPED`, same exception class as v1.7, backlog ID renamed `LIVE-HIGY-33`→`LIVE-HIGY-42`). Phase 43 reconciled `market-data-client`'s `Instrument`/`Segment` shape against a fresh wire read from Phase 42 (additive `marketId` alias, never a rename) and typed 5 previously-`extra` keys in the same `models.py` change — verified but deliberately unpublished. Phase 44 published `market-data-client-v0.7.0` on a real two-parent merge commit behind two independently-authored `gate="blocking-human"` checkpoints; a code-review-caught changelog gap (the HARN-02 migration table missing from the published README) was closed via a `v0.7.1` errata release rather than rewriting the already-pushed tag. Phase 45 deduplicated schema-drift findings across all 5 verification drivers via a `(func, digest)` guard evaluated *before* fid allocation (with a 6-arm falsification test proving distinct divergences on the same endpoint still get recorded), fixed a stale comment, closed 2 CI-enrollment gaps, and formally accepted 2 broken matriz `verification/` test files as documented debt while genuinely transferring their canary role to a CI-enrolled file.

### What Worked
- **Reversibility-ordered phase sequencing.** The 5 phases ran audit → live-checks → fix → release → harness-cleanup specifically because release is the least reversible operation and harness dedupe needed the live-run evidence to exist first (an explicit, written ordering decision, not incidental). Nothing had to be redone because a later phase's output was needed by an earlier one.
- **Deliberately not fusing the fix phase with the release phase (Phase 43 vs. 44).** Every prior milestone with a release (v1.5 Phase 28, v1.6 Phase 34, v1.7 Phase 40) kept the release in its own phase — this milestone's own roadmap notes call out that the *one* place the blocking-human gate authorship bug (`gate="blocking"` vs `gate="blocking-human"`) had slipped through twice before was exactly when a release phase absorbed other work. Keeping them separate kept the precedent's guardrail intact.
- **A named backlog ID surviving a rename.** `LIVE-HIGY-33`→`LIVE-HIGY-42` (D-06) changed the identifier without losing continuity — Phase 42 re-measured the same DNS failure *by exception class*, not by re-stamping the old finding, so the rename documents progress (re-confirmed today, not inherited) rather than erasing history.
- **Fixing a documentation gap with a new release instead of rewriting a shipped tag.** The v0.7.0 README gap (found by code review after the tag was already public) was never "fixed" by editing the pushed tag — `v0.7.1` shipped as a docs-only errata release. An annotated tag on a public GitHub Release is immutable in practice; treating it that way avoided a worse inconsistency (a tag whose tree doesn't match what `git show <tag>` used to show).

### What Was Inefficient
- The installed `gsd-tools.cjs`'s `milestone complete --archive-quick` flag silently no-op'd (parsed correctly per the CLI source, but the quick-task directory never moved and STATE.md's Quick Tasks table was never touched) — required a manual `git mv` + hand-written `README.md` to actually archive the one v1.8-era quick task. This is the *same* version-skew class of issue the v1.7 retrospective already flagged for `--archive-phases`; it recurred here for a sibling flag on the same command, suggesting the installed binary and the workflow doc have drifted further apart than just those two flags.
- Running `milestone.complete` a second time (to inspect a fuller JSON payload) silently duplicated the entire `MILESTONES.md` entry — the command isn't idempotent against re-invocation, and nothing in its output warned about the duplicate. Caught by diffing before committing; would have shipped a doubled changelog entry otherwise. Treat `milestone.complete` as a **write-once** command: never re-run it to "check" something after the first successful call — inspect the already-produced files/git-status instead.
- `init.manager`'s phase-verification fields (`phase_complete`, `verification_status`) don't exist in this installed schema (it exposes `disk_status`/`roadmap_complete` instead) — the same class of workflow-doc-vs-binary mismatch, third instance this session. A one-time schema probe at the start of a `/gsd-complete-milestone` run (rather than discovering the field names are wrong mid-workflow) would save the detour.
- 4 of 5 phases' `VALIDATION.md` files were never reconciled to `status: validated` — Phase 42 used a non-standard `status: complete` value, Phases 43/44 were left at the pre-execution `status: draft` the planner seeded, and Phase 45 had no `VALIDATION.md` at all. All four turned out to have zero real coverage gaps once audited — the entire cost was documentation reconciliation, not missing tests — but it meant the milestone audit initially read `tech_debt` for a reason that had nothing to do with actual risk.

### Patterns Established
- **Errata release over tag rewrite**: when a code review finds a documentation gap in an already-published, already-tagged release, ship a new patch version with the correction rather than editing the existing tag's tree — the tag stays a trustworthy historical pointer.
- **Rename backlog IDs on re-measurement, not on first mention**: `LIVE-HIGY-33`→`LIVE-HIGY-42` renamed only once the *same underlying finding* was independently re-confirmed in a new phase — the rename is evidence of continuity, not decoration.
- **`(func, digest)` guard before fid allocation, never after**: any content-addressed dedupe scheme that shares an ID allocator with a downstream invariant (`test_finding_count_consistency.py`'s fid count here) must check-then-allocate, never allocate-then-check, or a dedupe hit burns an ID the invariant assumes was consumed by real content.

### Key Lessons
- A `/gsd-validate-phase` audit finding "0 real gaps, only reconciliation" is a different outcome than "gaps found" and should be distinguished in the milestone audit's status vocabulary — this session's audit moved from `tech_debt` to `passed` after the validate-phase pass, which was the correct call, but it took an explicit re-audit to discover that the `tech_debt` label was measuring documentation lag, not actual risk.
- When a GSD-tooling command's actual behavior (flags silently no-op, duplicate entries on re-run, JSON schema fields renamed) diverges from what the invoking workflow doc assumes, the fix belongs in two places: work around it in the moment (which this session did, 3 times), *and* record it here so the next session doesn't re-discover the same three mismatches from scratch.

### Cost Observations
- Sessions: 1 continuous session covering the milestone audit request through the full `/gsd-complete-milestone` archival flow, including an interactive detour to run `/gsd-validate-phase` on 4 phases before closing.
- Notable: this is the second consecutive milestone (after v1.7) where the close itself commissioned new verification/reconciliation work rather than just documenting what phases had already produced — suggesting per-phase Nyquist reconciliation (not just per-milestone) may be worth enforcing earlier in the phase-close checklist to stop this class of gap from reaching the audit at all.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Plans | Key Change |
|-----------|----------|--------|-------|------------|
| v1.0 | ~13 days | 5 | 18 (37 closed-out) | Established the verification cycle (drivers + harness + DRIFT-02 baseline) |
| v1.1 | ~3.5 days | 6 | 30 | Architectural refactor + spike-before-plan + per-phase VALIDATION.md operator signoff |
| v1.2 | ~11 days | 5 (Phase 16 dropped) | 18 | CONDITIONAL phase modeling + spike NO-GO honored + per-request `extensions` override channel |
| v1.3 | ~1 day | 1 (Phase 19 dropped) | 3 | Milestone-scale spike-gate: entire milestone closes on a signed NO-GO; two-tool convergence before permanent shelving |
| v1.4 | ~3 days | 5 | 16 | First greenfield package (mirror-a-proven-shape); autonomous-prep + human-gated-publish; offline-SKIP as a sanctioned verification outcome |
| v1.6 | ~9 days | 6 | 44 | Load-bearing-phase-first decoder retrofit; count-based CI gates (`TOTAL=N && PASSED=N`); two-gate irreversible-ops pattern generalized to multi-artifact releases |
| v1.7 | ~2 days | 6 | 28 | Null Object pattern revokes a prior milestone's locked decision *by field role*; security-gate widened (substring→exact-hostname) to unblock live coverage; retroactive verification commissioned at milestone-close to resolve an audit-flagged process gap |
| v1.8 | ~2 days | 5 | 24 | Pure backlog-closure milestone (zero new product surface); retroactive Nyquist validation as its own first-and-alone phase; errata release (`v0.7.1`) instead of tag rewrite for a post-publish doc gap; `(func, digest)` dedupe guard checked before fid allocation |

### Cumulative Quality

| Milestone | Tests | Test delta | Requirements | Zero-Dep Additions |
|-----------|-------|------------|--------------|---------------------|
| v1.0 | 277 | +227 from baseline ~50 | 35/35 | (none — verification cycle) |
| v1.1 | 907/908 | +630 (vs v1.0 close) / +122 (vs Phase 9 baseline) | 29/29 | tenacity 9.1.4 (Apache-2.0, zero deps, py.typed) |
| v1.2 | ≥989 | +82 (vs v1.1 close) | 4/4 (REFAC-06 → v1.3) | platformdirs >=4.0,<5 (iol-client only) |
| v1.3 | ≥989 (unchanged) | 0 (spike-only, zero production footprint) | 2/2 (CODEGEN-01 resolved NO-GO; REFAC-06 shelved) | (none — libcst ephemeral, never added to deps) |
| v1.4 | ≥1,123 (+134 new package) | +134 (market-data-client suite) | 6/6 (AUTH/CORE/MD/REF/LIVE/PUB-MD; LIVE-MD-01 apparatus-verified, live sweep deferred) | (none new — httpx/python-dotenv/tenacity reused; 6th package) |
| v1.6 | 1,760 | +637 (vs v1.2-era baseline) | 7/7 (DEC/TYP-01/TYP-02/TYP-03/GATE-TYP/LIVE-TYP/PUB-TYP) | (none new — decoder is stdlib-only, msgspec NO-GO) |
| v1.7 | 1,947+ | net growth across 6 packages (regression suites per phase; matriz +13 for the byCFICode/bySegment fix alone) | 10/10 (NOBJ-01/02, NOBJ-MD-01/02, NOBJ-MTZ-01/02, NOBJ-IOL-01, NOBJ-AUD-01, LIVE-NOBJ-01, PUB-NOBJ-01) | (none new — pattern is stdlib `__bool__`/`empty()`, zero new deps) |
| v1.8 | 2,722 | net growth (new falsification/venue-gate/reconciliation locks; zero product-logic tests since zero new surface) | 9/9 (NYQ-01, LIVE-01, LIVE-02, SHAPE-01, HARN-02, PUB-01, HARN-01, HARN-03, HARN-04) | (none new — harness-only additions, zero new runtime deps) |

### Top Lessons (Verified Across Milestones)

1. **In-cycle fixes with regression tests.** Both v1.0 (24+ higyrus regressions in Phase 4, 19 matriz regressions in Phase 5) and v1.1 (8 BUG-03 lifecycle tests, 6 BUG-01 CFI edge-case tests + 16 parametric, 15 CR-06 AST guards) confirmed the same pattern: every discovered bug gets a mocked regression test in the same phase. Zero historical regressions surfaced in the v1.1 re-verification.
2. **Operator-driven classification beats automation for ambiguous findings.** v1.0 introduced the CONFIRMED/FIXED/EXPECTED/NO-FIX taxonomy. v1.1 BUG-02 (server returns HTTP 200 empty body — token scope, not client bug) validated that human triage with N=3 live calls produces correct verdicts that no automated heuristic would have caught.
3. **Per-package serial pattern.** v1.0 processed packages in ámbito → iol → higyrus → matriz order (smallest to largest blast radius). v1.1 Phase 6 and Phase 7 replicated the same order. Each package independent (no shared internals — by design); refactors replicate 4×, and that's fine because the failure modes stay isolated.
4. **DRIFT-02 cycle closure as a signal, not a failure.** v1.0 Phase 5 deferred F-09 deliberately and used `cycle_closure FAIL` as the explicit DRIFT-02 signal that the cycle detects its own gap. v1.1 Phase 9 BUG-01 closed F-09 + flipped that FAIL to PASS, validating the convention. Future cycles inherit the same pattern.
5. **Spike-before-plan works in both directions.** v1.1 Phase 10 spiked the TokenStore concurrency primitive → GO, and the validated recipe dropped straight into the plan with zero design surprises. v1.2 Phase 12 spiked unasync codegen → NO-GO, and the failure analysis became the v1.3 libcst spike scope. The flag earns its cost whether the answer is yes or no — model the dependent work as CONDITIONAL so a NO-GO drops cleanly (Phase 16 cost nothing to absorb).
6. **The per-request `request.extensions[...]` channel is the decoupling pattern.** v1.1 introduced it for the `idempotent` mutation gate; v1.2 reused it for `max_attempts`. The transport stays ignorant of domain types while callers thread per-call knobs through the httpx request object. Default to this for any future per-call override.
7. **Two independent tools before shelving an architectural limitation permanently.** v1.2 Phase 12 (unasync) and v1.3 Phase 18 (libcst) both returned a signed NO-GO on codegen single-source for the same content-absence root cause. One NO-GO says "maybe the tool"; two genuinely-different tools converging says "the source shape is intrinsic." That convergence is what let REFAC-06 be shelved *permanently* (accepted as a structural feature) rather than deferred a third time. A NO-GO milestone that produces a durable signed decision is a real deliverable — v1.3 shipped zero code and was a success.
8. **The intentional-duplication constraint that costs on every fix pays back on every new package.** For 3 milestones the "no shared internals, logic duplicated 4×" design read as tech debt. v1.4 proved its upside: adding the 6th package (`market-data-client`) was a low-risk mirror of a fully-proven template with nothing shared to break. The same constraint that makes a logic fix a 4-6× chore makes package creation a copy-and-adapt-the-auth exercise. Weigh both directions before "fixing" an intentional duplication.
9. **Decouple the release from the flakiest requirement.** v1.4's live-verification (LIVE-MD-01) was blocked on external access (Auth0 creds + VPN); the publish (PUB-MD-01) was scoped to not depend on it, so v0.1.0 shipped on schedule while the live sweep carries forward. When a requirement hinges on third-party access outside the team's control, make the user-visible deliverable independent of it rather than letting an environment blocker gate the ship.
10. **Revoke by field role, not wholesale.** v1.7 formally revoked v1.6/Phase-33's `| None` widening — but only for chain-link fields (model/list), keeping it for leaf fields. Reopening a locked decision doesn't require reverting it uniformly; split by the dimension that actually distinguishes the good part from the bad part, and the prior decision's still-valid half survives.
11. **A widened security gate can unblock verification instead of loosening it.** v1.7 Phase 39 converted matriz's substring-match hostname gate to an exact-hostname allowlist — stricter against spoofing, and simultaneously what let the first live matriz run since v1.0 happen (finding a real ~9160-record data-loss bug in the process). An imprecise gate can be both insecure-feeling *and* over-blocking at once; fixing the precision can improve both properties together.
12. **Treat an audit's `gaps_found` as an action item, not a formality.** v1.7's milestone-close audit flagged a missing retroactive VERIFICATION.md as "process gap, not substance gap" — but rather than just writing the missing document from the existing SUMMARY.md narrative, the close spawned a fresh verifier against live git/GitHub state and an actual package install, which is what actually confirmed the gap was cosmetic. A process gap can hide a real one; only independent re-verification tells the difference.
13. **A pure backlog-closure milestone still needs the same rigor as a feature milestone.** v1.8 added zero product surface, yet its 5 phases each produced named evidence (venue-gate falsification tests, wire-read timestamps, dedupe falsification arms) rather than treating "just closing old items" as lower-stakes work — the same discipline that finds real bugs in feature work is what caught the v0.7.0 changelog gap and the Nyquist reconciliation gap here.
14. **GSD-tooling version skew is now a recurring, not one-off, cost.** Three consecutive close-time surprises this session (`--archive-quick` no-op, `milestone.complete` non-idempotent on re-run, `init.manager`'s renamed phase-status fields) echo the exact `--archive-phases` mismatch v1.7's retrospective already flagged. Treat any `/gsd-complete-milestone` run as needing a live behavior-check against the installed `gsd-tools.cjs`, not a docs read, before trusting its output.
