# Project Research Summary

**Project:** market-libs — v1.8 "Cierre de deuda post-v1.7"
**Domain:** Backlog closeout on an existing Python client-library monorepo (no new packages, no new domain)
**Researched:** 2026-08-31
**Confidence:** HIGH

## Executive Summary

v1.8 is not feature work — it is a debt closeout across four independent groups (live re-checks, retroactive Nyquist validation, a source-breaking model fix, and harness cleanup), and every one of them is executable with the stack already on disk. No new libraries, dev tools, or CI jobs are needed. The one real "build" item is a ~10-line security-relevant edit: `scripts/literal_census_33.py` still runs the pre-Phase-39 substring venue gate (`if "remarkets" not in base:`), so it will silently SKIP against the now-unblocked `bbsa` sandbox unless the exact-hostname `_VENUE_ALLOWLIST` from `main_matriz.py` is ported in first. The ROADMAP's claim that this script is "ready" is verified false at HEAD — this is the single most important correction research surfaced.

The recommended approach is precedent-driven, not invented: every prior source-breaking change in this repo (v1.5 D-03, Phase 34, Phase 40) followed the same ceremony — minor version bump on the 0.x line, README changelog + migration table, four version sites moved together, and a double independent human gate that must be authored as `gate="blocking-human"` (not `gate="blocking"`, which has silently auto-approved twice already under `mode: yolo`). SHAPE-01 (`Instrument`/`Segment` field correction in `market-data-client`) is the one item in this milestone that touches a published wheel's public surface and must follow that ceremony exactly, disposing each field individually (additive alias vs. remove vs. add) rather than as a single "fix the model" patch.

The dominant risk across the milestone is *silent-vs-visible regression* — the exact failure class the whole project exists to catch. Two items are actively dangerous if implemented naively: HARN-01's dedupe (`idempotent_by_title=True` on the drift branch would permanently swallow every later, genuinely different schema drift on the same endpoint, and also breaks the fid-count invariant P-3 because `_next_fid()` is called before the dedupe check), and any "quick fix" of the census gate using a substring/`endswith` check (reintroduces the exact spoofing weakness Phase 39 D-02 removed). Both require a considered fix, not a one-liner. NYQ-01 (retroactive Nyquist validation of phases 35-39) must run first, against frozen v1.7 state, before any source code in this milestone changes, or its findings become unattributable to the wrong tree.

## Key Findings

### Recommended Stack

Zero new dependencies. The entire milestone rides Python 3.12/3.13, uv, httpx, pytest+pytest-httpx, ruff, and mypy strict — all already installed and configured. `market-data-client`'s field fixes (SHAPE-01, HARN-02) are pure stdlib `@dataclass(frozen=True, slots=True)` edits on existing `SafeModel` subclasses; no msgspec/pydantic/attrs (explicitly NO-GO per a signed v1.6 D-lock). The only tooling change of substance is porting `main_matriz.py:139`'s `_VENUE_ALLOWLIST` (exact-hostname equality) into `scripts/literal_census_33.py:192`, which currently runs a stale substring gate.

**Core technologies (unchanged):**
- Python 3.12+ / uv — runtime and workspace management, no new floor needed
- httpx (sync+async) — sole live-request transport for LIVE-01/02
- pytest + pytest-httpx — mocked regression pins for SHAPE-01/HARN-02
- ruff + mypy strict — lint/typecheck gates; note `scripts/` and `verification/` are outside mypy's `files` scope but inside ruff's, so the census-script edit is lint-only but must pass ruff
- Existing project scripts (`preflight_33.py`, `literal_census_33.py`, `verification/findings.py`, 4 CI gate scripts) — the actual "stack" for this milestone

### Expected Features

Four work groups, each with a distinct risk profile. LIVE and SHAPE are risk-bearing (vendor network / published surface); NYQ and HARN are table-stakes coverage/cleanup.

**Must have (table stakes):**
- LIVE-01 — higyrus DNS re-probe with a *measured* outcome (never a silent zero); reuse `scripts/preflight_33.py` and `main_higyrus.py`, both already built
- LIVE-02 — matriz RESPONSE `Literal` census against `bbsa`, blocked until the venue allowlist is ported (P1, first task of the group)
- NYQ-01 — `/gsd-validate-phase` over archived phases 35-39; verified unblocked (archived dirs resolve via `init.phase-op`), but the auditor must be pointed at `.planning/milestones/v1.7-REQUIREMENTS.md`, not the absent root file
- SHAPE-01 — correct `Instrument`/`Segment` field declarations against measured wire baselines; `Segment`'s three declared fields are disjoint from the wire, so every row decodes empty today
- HARN-01 — dedupe schema-drift findings by title (primitive exists since Phase 11); NOT a one-line kwarg add — the fid-allocator ordering must change too
- HARN-04 — decide repair-vs-accept-debt for the two broken matriz `verification/` test files (19 failed/19 errors, single root cause: pre-REFAC-05 probe signatures)

**Should have (differentiator, low cost):**
- Single-source the venue allowlist test (pins census-gate == driver-allowlist, and asserts `mutation_gate._SANDBOX_HOST` excludes bbsa)
- Enroll any repaired `verification/` files into the CI explicit allowlist (`ci.yml:80-92`) — repair without enrollment guarantees re-rot
- HARN-02 — type the 5 remaining `extra` keys on `Health`/`HealthFeed`/`Symbol`; bundle into SHAPE-01's release since both touch `models.py`
- HARN-03 — two stale docstring lines (330→336) + `IN-06` (missing CI allowlist entry); note `IN-05` is already closed, retire it

**Defer (explicitly out of scope for v1.8):**
- `NYQUIST-32-33` (same gap, prior milestone — don't widen scope)
- mypy enrollment for `verification/` (43-44 errors, 8-9 files — separate, much larger decision)
- A deprecation window for SHAPE-01 (project has never used one; minor-bump-on-0.x is the only precedent)
- Renaming `Instrument.marketId` outright (must be an additive alias, per the `Symbol.marketId` D-22 precedent)

### Architecture Approach

No new layers or packages. Every group attaches to existing structure: SHAPE-01/HARN-02 touch only `market_data_client/models.py` (the sole field-declaration site) — `_core.py` parsers, `client.py`, and `aio.py` need **no changes** since parsers already do `Model.from_api(item)` generically and signatures stay `list[Instrument]`. HARN-01 touches `verification/findings.py` + 4-5 driver call sites. LIVE-01/02 touch `main_higyrus.py` (already has the vendor-unreachable path built) and `scripts/literal_census_33.py` (needs the allowlist port). NYQ-01 has zero source footprint except any auditor-generated tests, which are inert unless added to the `ci.yml` explicit allowlist.

**Major components:**
1. `market_data_client/models.py` — the single declaration site for `Instrument`/`Segment`; SHAPE-01 and HARN-02 land here together, in one 0.6.0→0.7.0 release
2. `scripts/literal_census_33.py` + `main_matriz.py::_VENUE_ALLOWLIST` — the venue-policy gate that must be single-sourced (exact-hostname equality), never widened via substring/`endswith`
3. `verification/findings.py::append_finding` — the dedupe primitive HARN-01 must wire correctly, respecting the fid-count invariant `test_finding_count_consistency.py` pins
4. `.github/workflows/ci.yml` lint job's explicit 12-file `verification/` allowlist — the only mechanism by which any harness test actually runs in CI (52 test files exist; 12 are enforced)
5. `.planning/milestones/v1.7-phases/{35..39}-*/` — frozen archived phase dirs that NYQ-01 audits in place, no restoration needed

### Critical Pitfalls

1. **LIVE-02's census gate is stale and the ROADMAP overstates readiness** — port `_VENUE_ALLOWLIST` (exact hostname equality) from `main_matriz.py`, never a substring/`endswith` predicate; treat this as a blocking human checkpoint per P-05, and correct the ROADMAP sentence in the same commit
2. **HARN-01's naive fix causes permanent silent data loss** — `idempotent_by_title=True` on the drift branch (whose title is endpoint-scoped and content-free) would swallow every *later, different* drift on that endpoint forever; content-address the title or dedupe within-run only, and add a falsification test proving a different drift still writes
3. **HARN-01 breaks the fid-count invariant P-3** — `_next_fid()` is called before `append_finding` at every drift site; a dedupe no-op burns a fid with no matching block; reorder the allocation, never relax the test
4. **SHAPE-01 skipping release ceremony** — this is a source-breaking change to a published wheel; every prior instance (4x) used minor-bump + README changelog + migration table + double human gate; author the release gate literally as `gate="blocking-human"` (it has silently auto-approved twice already as `gate="blocking"`)
5. **Retroactive Nyquist validation flipping flags without re-verification** — `VALIDATION.md` is a pre-execution sampling contract; running it after the fact must produce a coverage audit with 3 explicit dispositions (`VERIFIED-NOW`/`VERIFIED-HISTORICALLY`/`NOT-VERIFIABLE-RETROACTIVELY`), never a mechanical status flip to `nyquist_compliant: true`

## Implications for Roadmap

Based on research, suggested phase structure (do NOT bundle all four groups into one "cleanup" phase — they differ on reversibility and evidence class):

### Phase 1: Retroactive Nyquist Validation (NYQ-01)
**Rationale:** Must audit phases 35-39 against *frozen* v1.7 state, before any v1.8 source change occurs, or findings become unattributable to the wrong tree. Zero source footprint (except possible generated tests).
**Delivers:** Per-phase validation audit for phases 35-39 with 3-way disposition per finding, CI-enforcement column, front-matter updated only where genuinely re-verified.
**Addresses:** NYQ-01
**Avoids:** Pitfall 4 (grading against shipped artifact), Pitfall 5 (local-green certifying inert locks)

### Phase 2: Live re-checks — higyrus DNS + matriz venue-gate port + Literal census
**Rationale:** Externally gated, non-deterministic (DNS, market hours), and the venue-widening is a security-relevant blocking human checkpoint that must land before any network call. Also produces the fresh live read of `/instruments` and `/segments` that SHAPE-01 needs as its evidence base — sequence live before shape.
**Delivers:** Higyrus re-probe artifact (SKIPPED-with-cause or resolved), ported exact-hostname venue allowlist in `literal_census_33.py`, matriz Literal-value census against bbsa (with venue+timestamp header, D-lock (b) reaffirmed), fresh market-data wire read.
**Addresses:** LIVE-01, LIVE-02
**Avoids:** Pitfall 1 (false resolution), Pitfall 2 (unsafe quick-fix widening), Pitfall 3 (census read as license to promote `Literal`), Pitfall 8 (correcting against a stale frozen baseline)

### Phase 3: SHAPE-01 + HARN-02 (fix, stop short of publish)
**Rationale:** Both touch `market_data_client/models.py`; bundling avoids burning two separate version bumps. Needs an explicit per-field disposition (alias/remove/add), sync+async mirrored regression tests derived from fresh baselines, and all 4 CI gates green — but the release itself is a separate phase per locked precedent.
**Delivers:** Corrected `Instrument`/`Segment` models, 5 typed `extra` keys (incl. a new `FeedSubscription` nested model for `.subscription`), 6 re-derived test fixtures with a fixture-⊆-baseline assertion, updated `main_market_data.py:1507` consumer.
**Uses:** stdlib dataclasses, `SafeModel`, existing baselines in `.planning/verification/schemas/market-data-client/`
**Implements:** the models.py component; avoids Pitfall 6 (skipping ceremony), Pitfall 7 (fabricated fixtures preserved), Pitfall 11 (`extra`→`missing` disposition flip)

### Phase 4: Release market-data-client 0.7.0
**Rationale:** Locked project precedent — a release with double human gate never shares a phase with the verification/fix work that enables it, precisely because co-location is where the `gate="blocking"` authoring bug (already occurred twice) collapses the gate.
**Delivers:** Version bump across 4 sites, README changelog + migration table, `uv.lock` refresh, annotated tag, GitHub Release via the existing double-gated pipeline.
**Uses:** existing `release.yml`, Phase 34/40 precedent
**Avoids:** Pitfall 14 (release gate collapse, third occurrence)

### Phase 5: Harness cleanup (HARN-01, HARN-03, HARN-04 decision)
**Rationale:** Deterministic and fully offline; can interleave with Phase 1 or Phase 3, but HARN-01's ordering relative to Phase 2's live runs is a decision to make explicitly (harness-changes-what-gets-recorded lands before live; harness-changes-what-gets-decoded lands after).
**Delivers:** Correctly-ordered fid+dedupe fix for schema drift (with falsification test), 2 stale docstring lines fixed, HARN-04 resolved as either a written repair decision (its own sub-phase) or documented accepted-debt, consolidated `ci.yml` allowlist edit.
**Addresses:** HARN-01, HARN-03, HARN-04
**Avoids:** Pitfall 9 (silent census loss), Pitfall 10 (P-3 relaxed), Pitfall 12 (HARN-04 scope creep / canary loss), Pitfall 13 (wrong harness/live ordering)

### Phase Ordering Rationale

- NYQ-01 first because it audits frozen history — any source change before it contaminates the audit.
- Live runs (Phase 2) before SHAPE-01 (Phase 3) because SHAPE-01's correction must be evidenced by a fresh wire read, not the stale 2026-07-31 committed baseline.
- SHAPE-01/HARN-02 fix and the 0.7.0 release are split into separate phases because every prior source-breaking release in this project has been its own phase with its own double human gate — collapsing them is the exact context where the gate-authoring bug has twice slipped through.
- Harness cleanup (Phase 5) is fully offline and low-coupling; it can interleave with Phase 1 or 3, but HARN-01 vs. the live runs in Phase 2 needs an explicit ordering decision stated in the plan, not left to accident.

### Research Flags

Phases likely needing deeper research/discuss-phase before planning:
- **Phase 2 (Live re-checks):** venue-widening is a security-relevant blocking human checkpoint, not a routine script run — warrants discuss-phase for policy, not design
- **Phase 3 (SHAPE-01):** the per-field disposition table and the two dangerous naive-fix traps (fabricated fixtures, `extra`→`missing`) mean this needs a discuss-phase with the operator before planning
- **Phase 5 (HARN-01):** the fid-allocator/dedupe interaction is non-obvious and actively harmful if implemented as a one-liner — discuss-phase recommended

Phases with standard, well-documented patterns (safe to skip research-phase):
- **Phase 1 (NYQ-01):** mechanics are fully wired and verified by execution; follow the `40-VERIFICATION.md` precedent
- **Phase 4 (Release):** four prior identical instances (v1.5, v1.6 x2, v1.7) establish the exact recipe

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Every claim verified by executing the tool or reading the exact file/line; no external providers needed since nothing new is proposed |
| Features | HIGH | Repo-internal precedent archaeology, verified by live execution (gates run, models read, broken tests actually run) |
| Architecture | HIGH | Every integration point opened/read/executed at HEAD `e55398d`; the stale `.planning/codebase/ARCHITECTURE.md` was deliberately rejected as a source |
| Pitfalls | HIGH for repo-measured claims; LOW for 2 web-sourced generalities (semver 0.x norms, retroactive-audit evidence weakness) used only to confirm alignment, not to override project convention |

**Overall confidence:** HIGH

### Gaps to Address

- **Whether LIVE-01's DNS still fails:** genuinely unknown until probed — this is the requirement itself, not a research gap
- **Does v1.8 ship the 0.7.0 release, or fix-and-hold?** SHAPE-01's disposition hinges on this and nothing in the backlog decides it — a checkpoint-shaped question for the roadmap/requirements stage
- **HARN-04 repair budget:** recommend the roadmap declare a budget up front so "repair vs. accept-debt" resolves on evidence rather than fatigue
- **Exact hostname match for `bbsa`:** allowlist key is `api.bbsa.matrizoms.com.ar`; confirm the configured `PRIMARY_BASE_URL` host matches exactly before the census run (`.env` access is policy-denied to research, correctly)
- **HARN-02 `unconfirmed_symbols` member type:** observed empty list only; needs a live capture or an explicit `list[str]` assumption at implementation time

## Sources

### Primary (HIGH confidence)
- Live repository tree at HEAD (`37a83fe` / `e55398d`) — all four research files cite specific files, lines, and executed commands (`uv run pytest`, `uv run mypy verification`, `gsd-tools query init.phase-op`, `tools/check_surface_types.py`, etc.)
- `.planning/PROJECT.md`, `.planning/ROADMAP.md`, `.planning/STATE.md` — Key Decisions, backlog REQ-IDs, constraints
- `.planning/verification/schemas/market-data-client/*.json` — committed live wire baselines (captured 2026-07-31)
- `.planning/milestones/v1.7-phases/{35..39}-*/` — archived phase VALIDATION/SUMMARY artifacts

### Secondary (MEDIUM confidence)
- None — this milestone required no external ecosystem survey

### Tertiary (LOW confidence)
- SemVer 0.x breaking-change conventions (semver#411, pandas policies) — used only to confirm the project's existing 0.4.0/0.5.0/0.6.0 precedent matches wider norms
- Retroactive audit evidence weakness (Adherent, Scrut) — used only to justify the 3-way disposition scheme for NYQ-01, not to introduce new tooling

---
*Research completed: 2026-08-31*
*Ready for roadmap: yes*
