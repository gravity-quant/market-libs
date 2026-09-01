# Feature Research

**Domain:** Internal debt closeout in a mature, convention-heavy Python client monorepo (v1.8 backlog, 4 work groups, 8 REQ-IDs)
**Researched:** 2026-08-31
**Confidence:** HIGH (repo-internal precedent, verified by execution)

> **Method note.** This milestone has no external ecosystem to survey — every item is a
> named backlog entry with a measured cause and a file location, and the quality gate
> asked for grounding in *this project's* precedent rather than generic advice. So the
> research is precedent archaeology plus live verification: models read, gates executed,
> broken tests actually run. Every claim below cites a file, a line, or a command output.
> Two findings materially change the work (marked **⚠ FINDING**).

---

## Executive Categorization (for the roadmap)

| Group | REQ-IDs | Category | Complexity | Blocks on |
|-------|---------|----------|------------|-----------|
| 1. Live re-check + census | LIVE-01, LIVE-02 | **Risk-bearing** (touches vendor network + a security policy gate) | LOW (LIVE-01) / **MEDIUM** (LIVE-02 — has a hidden blocker) | Porting the Phase-39 `_VENUE_ALLOWLIST` into `scripts/literal_census_33.py` |
| 2. Retroactive Nyquist | NYQ-01 | **Table-stakes coverage** — low risk *by tooling construction* | MEDIUM (5 phases × audit) | Nothing. Verified unblocked. |
| 3. Published shape fix | SHAPE-01 | **Risk-bearing** — the only source-breaking change in the milestone | **MEDIUM-HIGH** | A version-disposition decision + the Phase-34/40 release machinery |
| 4. Harness cleanup | HARN-01..04 | **Table-stakes cleanup**, with two spikes inside it | LOW overall; **MEDIUM** for HARN-01 correctness and HARN-04 scoping | HARN-04 depends on the CI allowlist precedent |

---

## Feature Landscape

### Table Stakes (Expected — absence is a defect in the closeout, not a missing feature)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **LIVE-01** higyrus re-probe with a *measured* outcome, never a silent zero | The project has closed this loop twice already (Phase 33 D-13, Phase 39) and both times recorded `SKIPPED — vendor inalcanzable` with the exact `socket.gaierror` cause. A third probe that reports "no findings" instead of "unreachable, measured" would break a two-milestone invariant. | LOW | Reuse `scripts/preflight_33.py` (already prints `AUTH OK` / `AUTH FAIL <exc>` without leaking the URL). Pre-register **both** outcomes as success before running — a SKIP is a result, not a phase failure. Fold in the documented D39-WR-02 gap while here: higyrus does not catch `httpx.ConnectTimeout`, and "DNS now resolves but the host hangs" is the newly-plausible failure mode a re-probe can hit. |
| **NYQ-01** run `/gsd-validate-phase` on 35-39 | 40 reached `nyquist_compliant: true`; 35-39 sit at `status: draft` / `nyquist_compliant: false` (verified in all five `*-VALIDATION.md` frontmatters). `audit-milestone §5.5` explicitly reads `draft` as NOT-VALIDATED. It is a coverage hole the project's own audit already flagged. | MEDIUM | **Verified unblocked:** `gsd-tools query init.phase-op 35` resolves the *archived* dir `.planning/milestones/v1.7-phases/35-…` — no un-archiving needed. All five are **State A** (VALIDATION.md exists → audit existing), not State B reconstruction. |
| **HARN-01** dedupe schema-drift findings by title | `findings.py::append_finding` has shipped `idempotent_by_title` since Phase 11 (HARN-08/10) and the other terminal call sites already pass it. The drift branch is the one that never got it — an inconsistency, not a missing capability. | LOW code / **MEDIUM correctness** | Title is `f"Schema drift en {func_name}"` (`main_higyrus.py:590`) — byte-identical across passes, so dedupe is sound. Two traps below in *Dependency Notes*. |
| **HARN-02** type the 5 remaining `extra` keys | Four of them exist only because Phase 31 typed `Health`/`HealthFeed` (TYP-02) — they are the visible tail of work already done. `extra` is INFO-only by Phase-29 policy, so this is surface coverage, not defect repair. | LOW ×4 / **MEDIUM ×1** | `symbols_never_delivered`(int), `last_error_age_seconds`(int), `last_error_at`(str), `Symbol.note`(str) are trivial. `ingestor.subscription` is a **dict** → under D-NO-02 it needs a new nested `SafeModel` + Null Object, and the Phase-37 *field dimension* of `check_surface_types.py` will enforce that. Apply the Phase-31 **Restraint** verdict: do not declare `\| None` on states never observed. |
| **HARN-03** stale comment + named cosmetics | Zero-risk hygiene. | **LOWEST** | **IN-01 confirmed real:** `tools/check_surface_types.py:47,58` docstring says `330 definitions scanned`; running the gate now prints `336 definitions scanned, 442 fields scanned … 0 violations`. Two docstring lines. **IN-05 is already resolved** — `packages/matriz-client/src/matriz_client/__init__.py:186` has `__version__ = "0.3.0"` (added in `50d1c0e`, Phase 40). **IN-06 still open** (`verification/test_public_surface.py` absent from the CI list). *Re-verify each cosmetic before scheduling it; one of three was stale.* |
| **SHAPE-01** correct `Instrument`/`Segment` against measured wire | `get_segments()` currently returns rows whose three declared fields are **all** empty on every call — declared set and wire set are disjoint. Shipping a client that returns structurally empty rows from a public endpoint is the exact bug class this project exists to eliminate. | MEDIUM-HIGH | Measured against committed baselines. See the dedicated section below. |

### Differentiators (Beyond closing the ticket — durable value)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Single-source the D-MATZ-33 venue allowlist** | ⚠ **FINDING** — the gate is currently forked. `main_matriz.py:140-141` has the Phase-39 `_VENUE_ALLOWLIST` (exact-hostname equality, admits `api.bbsa.matrizoms.com.ar`). `scripts/literal_census_33.py:192` still runs the pre-Phase-39 `if "remarkets" not in base:` substring check. Collapsing them fixes a functional blocker *and* removes a spoofing weakness that D-02 explicitly called out. | LOW | Also affects `verification/mutation_gate.py:73` (`_SANDBOX_HOST = "api.remarkets.primary.com.ar"`) — but that one is **deliberately** narrower (keeps order entry fail-closed under bbsa) and must NOT be widened. Two of three copies converge; the third stays strict, documented. |
| **Enroll repaired `verification/` tests into the CI allowlist** | Repair without enrollment guarantees re-rot: `.github/workflows/ci.yml` documents in three places that `verification/` "NUNCA corrió en CI" because the `test` job passes an explicit path that overrides `testpaths`. The rot is *invisible by construction*. | LOW (once repaired) | Precedent shape already exists: an **explicit 12-file allowlist** inside the `lint` job (`ci.yml:80-92`), added file-by-file, with a comment saying exactly why it is not `pytest verification/`. Make "added to that list" the acceptance criterion for HARN-04, not "tests pass locally". |
| **A drift-dedupe regression test that fails first** | HARN-01's failure mode is silent (duplicate blocks, no data loss) — precisely the class this repo pins with fail-first tests. The sibling invariant already has one: `verification/test_finding_count_consistency.py` ships a deliberate `test_unseeded_allocator_silently_loses_findings` control arm. | LOW | Follow that file's own pattern: a seeded arm plus a control arm proving the assertion *detects* its violation. |
| **Cross-package `__version__` metadata test** | Only `market-data-client` has `tests/test_version_metadata.py`. Phase 34 logged this as WR-05 parity debt for `iol-client`; it is really a 5-package gap. Cheap, and it hard-pins the exact class of drift Phase 34 shipped a real bug on (README citing v0.4.0 under a v0.5.0 changelog). | LOW | Natural companion to SHAPE-01's release. Optional — do not let it expand the milestone. |

### Anti-Features (Attractive here, and wrong)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **A deprecation window / major bump for SHAPE-01** | "Source-breaking on a published package" reflexively suggests semver ceremony. | The project has **never** run a deprecation window. Every source-breaking change shipped as a **minor bump on 0.x** with a changelog callout: `CalendarDay` field replacement (v1.5 D-03), iol 0.2.0→0.3.0 + market-data 0.4.0→0.5.0 (Phase 34), the four packages of Phase 40. These are 0.x GitHub Releases with known consumers, not PyPI with an anonymous userbase. Inventing a window here creates a precedent nothing else follows. | Minor bump (`0.6.0 → 0.7.0`) + changelog callout + migration table + the double human gate (D-08/D-18). The *one* deprecation-shaped tool the project owns is the `Symbol.marketId` additive alias (D-22) — use that per-field, not as a milestone-wide policy. |
| **Letting Nyquist gaps trigger implementation fixes** | A retroactive audit naturally surfaces "this shipped decision looks wrong." | That re-opens closed phases and turns coverage work into a second milestone. | The guardrail already exists in the tooling: `gsd-nyquist-auditor` is spawned with `Never modify impl files. Max 3 debug iterations. Escalate impl bugs.` Honor it literally. The in-project template is the v1.7 milestone-close `40-VERIFICATION.md`: it re-verified 22/22 against live git/GitHub/wheel state, produced a **new artifact**, and changed **nothing shipped**. Route every escalation to the backlog with a named destination — the project's standing habit. |
| **Expanding NYQ-01 to phases 32-33** | They are also `status: draft` (verified) — "while we're in here." | v1.8 scope names 35-39. 32/33 belong to a shipped-and-archived milestone with its own audit verdict; absorbing them doubles the group and re-opens v1.6. | Note them in the backlog as `NYQUIST-32-33`. The project already does this — Phase 34 twice refused to widen a release PR's diff for exactly this reason (D-16). |
| **`pytest verification/` in CI to "just cover it"** | Would close HARN-04 and IN-06 in one line. | The directory carries pre-existing red unrelated to any single package (measured: 19 failed / 19 errors / 3 passed) plus **43 mypy errors across 8 files** — it is outside mypy `files` and outside the pre-commit `^packages/.*/src/` scope. A blanket run turns CI red on day one and gets reverted. | Keep the explicit allowlist (`ci.yml:80-92`). Add files as they are proven green. Treat the mypy half as a **separate** decision with a much larger blast radius. |
| **Leaving `verification/` red but documented as "accepted debt"** | It is the cheapest way to close HARN-04. | A permanently-red file trains everyone to ignore red — and the 19/19 red has already survived four milestones (Phase 15 → Phase 40) precisely because it was "documented." Documentation has demonstrably not worked as a control here. | Repair (evidence below says it is mechanical), or **delete the files outright**. If the answer is deprecate, deprecate *by removal*, not by annotation. |
| **Renaming `Instrument.marketId` → `market_id` outright** | It is a straightforward typo fix against the wire. | It is the identical situation to `Symbol.marketId`, where the project already decided (D-22) NOT to rename because the model is published read surface. Renaming here contradicts a signed decision on a sibling model in the same package. | Additive alias + `from_api` mirror, verbatim from `Symbol.from_api` (`models.py:880-897`), with the same "scheduled for removal at the next MAJOR" docstring. |
| **Running the matriz census "to see what happens"** | The sandbox is unblocked and creds authenticate. | With `literal_census_33.py:192` unchanged it prints `SKIPPED` and costs a cycle; and matriz's surface includes **order entry**, which is why P-05 forbids routing around the gate. | Port the allowlist first (a reviewed code change), then run. Never bypass the gate; `verification/mutation_gate.py` stays remarkets-only so order entry remains fail-closed under bbsa without a code change. |

---

## SHAPE-01 in Detail — the only genuinely risk-bearing change

**Measured evidence** (committed baselines, read this session):

`.planning/verification/schemas/market-data-client/get-instruments.json` → `items[]` wire keys:
`symbol, market_id, segment, currency, days_to_maturity, maturity, outright, subscribed, expired, active` (with `active` observed as `NoneType`).

`.planning/verification/schemas/market-data-client/get-segments.json` → `segments[]` wire keys:
`segment, live_instruments`.

Declared today (`packages/market-data-client/src/market_data_client/models.py:787-813`):
`Instrument(symbol, marketId, segment, instrumentType, expired)`; `Segment(marketSegmentId, marketId, description)`.

**Recommendation: dispose per field-role, not per model.** One policy for the whole change would either
over-ceremonialize the additive part or under-protect the alias part.

| Field | Wire status | Disposition | Precedent |
|-------|-------------|-------------|-----------|
| `Instrument.marketId` | wire sends `market_id` | **Additive alias + `from_api` mirror**, alias retained, removal at next MAJOR | `Symbol.marketId` / D-22, Phase 27 — identical camelCase-vs-snake_case case in the same package |
| `Instrument.instrumentType` | no wire counterpart | **Remove** — genuinely breaking, no alias target exists | `CalendarDay` field replacement, v1.5 D-03 |
| `Instrument.currency / days_to_maturity / maturity / outright / subscribed` | wire-only today | **Add** — purely additive, not breaking | Standard additive model growth |
| `Instrument.active` | wire-only, observed `null` | **Add as leaf `bool \| None`** — a scalar leaf terminates the chain, so `\| None` is correct here | D-NO-03 (v1.7) |
| `Segment.marketSegmentId / marketId / description` | all three disjoint from wire | **Replace** with `segment`, `live_instruments` | `CalendarDay`, v1.5 D-03 |

**The framing that de-risks `Segment`:** the three declared fields are empty on **every** row today
(disjoint sets ⇒ the walker fills defaults). No consumer can be reading a real value from them, so the
break is **nominal, not behavioral**. Say that explicitly in the migration table — it is the difference
between "we broke your code" and "we replaced three fields that were always blank."

**Version disposition is the load-bearing decision, and it is a dependency, not a detail.** Phase 33
proved what happens without it: 33-07 fixed the *envelope* half of S-1, deferred the semver consequence to
Phase 34, and the *field* half (this item) has been open ever since. If v1.8 lands the shape fix with no
release, SHAPE-01 is again half-done and invisible to consumers. Decide up front: either the milestone
carries a `market-data-client 0.6.0 → 0.7.0` release (changelog callout + migration table + double human
gate, per Phase 34/40), or SHAPE-01 explicitly ships as unreleased `## Unreleased — BREAKING` in the README
(the Phase-38 precedent for `iol-client`) with the release named as a v1.9 item.

**Bundle HARN-02 with it.** Both touch `market-data-client/models.py`; both are source-visible; one release
is cheaper than two and matches the Phase-34 rule of releasing only packages whose surface changed.

---

## Feature Dependencies

```
LIVE-02 (matriz Literal census)
    └──requires──> port _VENUE_ALLOWLIST into scripts/literal_census_33.py   ⚠ NOT DONE
                       └──must NOT touch──> verification/mutation_gate.py::_SANDBOX_HOST
                                             (stays remarkets-only = order entry fail-closed)

SHAPE-01 (Instrument/Segment)
    └──requires──> version-disposition decision (release now vs "## Unreleased — BREAKING")
                       └──requires──> Phase 34/40 release machinery + double human gate
    └──bundles-with──> HARN-02 (same models.py, same package, one release)

HARN-01 (drift dedupe)
    └──requires──> findings.py::append_finding(idempotent_by_title=)   [EXISTS since Phase 11]
    └──constrained-by──> verification/test_finding_count_consistency.py P-3 invariant

HARN-04 (verification/ fate)
    └──requires──> CI allowlist precedent (ci.yml:80-92)
    └──separable-from──> the 43-error mypy half (bigger blast radius, decide apart)

HARN-02 (extra keys)
    └──constrained-by──> check_surface_types.py field dimension (Phase 37)
                          [ingestor.subscription is a dict → needs a nested model]

NYQ-01 ──independent of all code work──> but audits a MOVING TARGET if run last
```

### Dependency Notes

- **LIVE-02 requires the allowlist port.** ⚠ **FINDING.** The backlog states the census script "ya tiene el
  gate remarkets-only listo para correr contra el sandbox `bbsa` ahora desbloqueado." That is not accurate.
  Phase 39's D-02 widened `main_matriz.py` only. `scripts/literal_census_33.py:192` is still
  `if "remarkets" not in base:` — it will print `SKIPPED — base URL fuera de política` against `bbsa` and
  never authenticate. It also still carries the substring weakness D-02 removed from the driver
  (`…remarkets.primary.com.ar.attacker.example` would pass). **This is the first task of the group, and it is
  a code change with a security character, not a script run.**
- **HARN-01 has two traps beyond the one-line flag.** (i) `_next_fid()` is called *before* `append_finding`
  (`main_higyrus.py:589-590`), so a deduped call still consumes a fid — and
  `verification/test_finding_count_consistency.py` pins "fids emitted == new `### F-` blocks" as invariant
  **P-3**, with that file's own docstring stating `_write_or_check_schema` "comparte exactamente este hazard."
  (ii) The function returns `("FINDING", f"{fid}|{file_path.name}")`; under dedupe that fid names a block
  that does not exist, so the driver's FINDING line would cite a phantom. The fix must resolve and return the
  **existing** fid. Treat HARN-01 as MEDIUM correctness work with a fail-first test, not a one-liner.
- **HARN-04's repair cost is measured, and it is small.** Running the two files this session:
  `19 failed, 3 passed, 19 errors in 0.13s` — matching `33-BASELINE.md` exactly, no network, single root
  cause (probes now take `client` per the Phase-15 REFAC-05 migration; each case double-counts because
  `pytest_httpx` teardown asserts the mock was requested). Three tests already pass, so the file is not
  wholly rotten. And what it guards is not incidental: `test_matriz_sweep_snapshot.py` pins the 18-probe
  envelope shape, and Phase 39 found a **real** envelope-discard data-loss bug in matriz (~9160 instruments).
  The file guards precisely the bug class that actually shipped. The roadmap's "canary for `probe_context`"
  warning is an argument *for* repair — these two files test something nothing else tests, because they
  invoke probes directly rather than through `main()`.
- **NYQ-01 should run first or in isolation.** It audits phases 35-39 as shipped. If HARN/SHAPE land first,
  the auditor sees v1.8 code under v1.7 plans and will manufacture gaps that are really drift. Running it
  against the archived state is both cheaper and more honest.

---

## MVP Definition

### Launch With (the v1.8 core)

- [ ] **Port `_VENUE_ALLOWLIST` into `scripts/literal_census_33.py`** — gates LIVE-02 entirely; also closes a
      live spoofing weakness. Smallest change with the largest unblock.
- [ ] **LIVE-02** — run the census against `bbsa`, record the distinct `marketId`/`cficode`/`currency`/
      `orderTypes`/`ordType` value sets. Closes the open half of criterion 3 that has been carried since 33-06.
      Also fix `29-DLOCK-RESPONSE-LITERAL.md:140-142` (the signed lock claims the divergence stream is the
      census mechanism; `_decode.py:521-534` returns early with `literal_enforced=False` and never calls the
      sink — correction is the signatory's).
- [ ] **LIVE-01** — bounded higyrus re-probe, both outcomes pre-registered, cause re-measured either way.
- [ ] **NYQ-01** — five audits, append-only, escalations routed to backlog.
- [ ] **SHAPE-01** — per-field disposition table above, with the version decision made explicitly.
- [ ] **HARN-01** — dedupe + phantom-fid fix + fail-first regression test.
- [ ] **HARN-04** — decide, then execute the decision *including* CI enrollment (or removal).

### Add After Validation (same milestone if cheap)

- [ ] **HARN-02** — bundle into SHAPE-01's release. `ingestor.subscription` gets a real nested model.
- [ ] **HARN-03** — two docstring lines (330 → 336) + IN-06. Confirm IN-05 is already closed and strike it.
- [ ] **Cross-package `__version__` metadata test** — trigger: if SHAPE-01 ships a release.

### Future Consideration (backlog, not v1.8)

- [ ] **`NYQUIST-32-33`** — same gap, prior milestone. Defer; do not widen scope.
- [ ] **mypy enrollment for `verification/`** (43 errors / 8 files) — much larger blast radius than the two
      broken test files; deserves its own decision.
- [ ] **`HARN-VERIF-01` residue** — anything the HARN-04 repair does not reach.
- [ ] **`append_finding` content-addressing cross-run for non-terminal probe findings** (D39-02) — explicitly
      operator-approved out of scope in v1.7; adjacent to HARN-01 but a different mechanism.

---

## Feature Prioritization Matrix

| Feature | Value | Cost | Priority |
|---------|-------|------|----------|
| Port venue allowlist to census script | HIGH (unblocks LIVE-02 + closes spoofing gap) | LOW | **P1** |
| LIVE-02 matriz Literal census | HIGH (last open half of a v1.6 criterion) | MEDIUM | **P1** |
| SHAPE-01 field-role disposition + version decision | HIGH (public endpoint returns empty rows today) | MEDIUM-HIGH | **P1** |
| HARN-01 dedupe + phantom-fid fix | MEDIUM (triage quality; silent failure mode) | MEDIUM | **P1** |
| NYQ-01 retroactive validation ×5 | MEDIUM (closes an audit-flagged hole) | MEDIUM | **P1** |
| HARN-04 decide + execute + enroll in CI | MEDIUM-HIGH (four milestones of carry) | MEDIUM | **P1** |
| LIVE-01 higyrus re-probe | MEDIUM (keeps the census floor honest) | LOW | **P2** |
| HARN-02 five `extra` keys | MEDIUM (surface coverage, not defect) | LOW-MEDIUM | **P2** |
| HARN-03 stale comment + IN-06 | LOW | LOWEST | **P2** |
| Cross-package `__version__` test | LOW-MEDIUM | LOW | **P3** |

---

## Precedent Analysis (in place of competitor analysis)

| Question | What this project already did | What v1.8 should do |
|----------|-------------------------------|---------------------|
| Source-breaking fix on a published package | Minor bump on 0.x + changelog callout + migration table + double human gate, four times (`CalendarDay` v1.5 D-03; iol 0.3.0 + market-data 0.5.0 Phase 34; four packages Phase 40). Never a deprecation window. | Same. `0.6.0 → 0.7.0`. No window. |
| A declared field that is a mis-spelling of a real wire field | Kept the wrong name as a **deprecated alias**, mirrored the real value in `from_api`, scheduled removal at next MAJOR (`Symbol.marketId`, D-22) | Identical treatment for `Instrument.marketId` |
| A declared field with no wire counterpart | Replaced outright inside a minor bump, with a README callout as the locked mitigation (`CalendarDay`, v1.5 D-03) | Same for `instrumentType` and all of `Segment` |
| Retroactive verification of shipped work | `40-VERIFICATION.md` produced at milestone-close: re-verified 22/22 against **live** git/GitHub/wheel state, not against SUMMARY claims; produced a new artifact; changed nothing shipped | Same posture for NYQ-01 — new artifacts, zero impl edits, escalations to backlog |
| A live vendor that cannot be reached | Recorded `SKIPPED — vendor inalcanzable` with the measured exception, **never as zero**, with a named backlog destination (Phase 33 D-13, Phase 39) | Same for LIVE-01 |
| Getting a `verification/` test to actually run in CI | Explicit per-file allowlist inside the `lint` job, added by hand, with a comment explaining why it is not `pytest verification/` (`ci.yml:80-92`) | Make allowlist enrollment the acceptance criterion for HARN-04 |
| Refusing to widen scope mid-stream | Phase 34 twice refused to expand a release PR's diff (D-16); Phase 36 deferred an over-declared-leaves item to an operator decision rather than deciding alone | Refuse `NYQUIST-32-33` and the mypy-enrollment half |

---

## Confidence Assessment

| Area | Confidence | Basis |
|------|------------|-------|
| Group categorization (table-stakes vs risk-bearing) | **HIGH** | Derived from measured blast radius: only SHAPE-01 changes published surface; only LIVE-01/02 touch vendor networks. |
| SHAPE-01 wire-vs-declared field sets | **HIGH** | Read directly from committed baselines and `models.py:787-813` this session. |
| Version-disposition precedent | **HIGH** | Four independent prior instances in PROJECT.md Key Decisions, plus the `Symbol.marketId` docstring stating the D-22 rationale verbatim. |
| LIVE-02 blocker (forked venue gate) | **HIGH** | `scripts/literal_census_33.py:192` vs `main_matriz.py:140-141`, read side by side. Contradicts the ROADMAP backlog text. |
| HARN-04 repair cost | **HIGH** | Tests executed: `19 failed, 3 passed, 19 errors in 0.13s`, matching `33-BASELINE.md`. |
| NYQ-01 mechanics and archived-dir resolution | **HIGH** | `validate-phase.md` workflow read; `init.phase-op 35` executed and returned the archived path. |
| HARN-03 item validity | **HIGH** | Gate executed (`336`, not `330`); IN-05 disproved via `__init__.py:186` + `git log -S`. |
| HARN-01 fid interaction | **MEDIUM-HIGH** | Inferred from reading `_write_or_check_schema` + `test_finding_count_consistency.py`'s own docstring, which names the shared hazard. Not executed against a dedupe patch. |
| Whether LIVE-01's DNS still fails | **UNKNOWN** | Not probed — probing a vendor host is the requirement itself, not research. |

## Gaps / Open Questions for Planning

- **Does v1.8 ship a release?** SHAPE-01's disposition hinges on it and nothing in the backlog decides it.
  This is a checkpoint-shaped question, not a research one.
- **Is the census's market-hours constraint still binding?** P-12 (Phase 33) required an ARG trading session
  for S-5. S-5 was measured in Phase 39, but the `Literal` value census may still want an open session to see
  a populated `orderTypes` — verify before scheduling the run window.
- **Exact hostname match for `bbsa`.** The allowlist key is `api.bbsa.matrizoms.com.ar`; the memory note
  refers to `bbsa.matrizoms.com.ar`. Exact-equality gating makes the subdomain load-bearing — confirm the
  configured `PRIMARY_BASE_URL` host matches the allowlist key exactly before the run (not read here:
  `.env` access is denied by policy, correctly).
- **HARN-04 repair budget.** Recommend declaring one up front (the framework's real decision variable), so
  "repair vs deprecate" resolves on evidence rather than fatigue.

---
*Feature research for: v1.8 backlog closeout, market-libs*
*Researched: 2026-08-31*
