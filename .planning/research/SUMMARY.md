# Project Research Summary

**Project:** market-libs — v1.6 "Tipado homogéneo de la superficie pública" (Phases 29-34)
**Domain:** Typed, observable-decode public surface for six independently-released Python HTTP client wheels (Argentine fintech APIs)
**Researched:** 2026-08-18
**Confidence:** HIGH — nearly every load-bearing claim in all four dimension files was verified by execution (msgspec 0.21.1, mypy --strict, live repo introspection), not inferred from memory.

## Executive Summary

The four researchers converge on a single structural correction to the milestone plan: msgspec cannot implement the observable decode mode the milestone exists to deliver. Verified independently by Stack, Features, Architecture, and Pitfalls: msgspec is fail-fast (one error per decode, no collect-all API), silently ignores extra/unknown wire keys in every mode including strict, and has no working field-rename for stdlib dataclasses. The plan's premise that "_coerce reemplazado" is wrong — _coerce (or its equivalent hand-written per-field walker) is not replaced, it IS the primary implementation of the observable runtime path. msgspec's real contribution is confined to a fast strict-mode detector: try msgspec.convert first (~0.5us, the overwhelming common case), and only fall into the per-field walker when it raises. This reframes Phase 29's central deliverable from "swap _coerce for msgspec" to "build a two-pass decoder where the walker is load-bearing and msgspec is an optimization."

A second convergent correction: the plan's claim that SafeModel/_coerce is "duplicado verbatim x3" is measurably false. higyrus_client and market_data_client are byte-identical; matriz_client uses a structurally different base (_SafeModel/_convert/empty(), no slots, scalars pass through unvalidated, missing values become None not 0.0/""). Any Phase 29 task that treats the three as interchangeable will silently corrupt matriz's published contract. matriz also carries Literal-typed response fields that are decorative today (pass-through) but would become hard-enforced validation failures under strict decoding — a second, independent divergence-storm risk absent from iol's mercado/plazo discussion in the plan.

The recommended approach: decode at the from_api dict boundary (not bytes-in-parser, which would re-litigate ~30 live-verified envelope-unwrap parsers across 6 packages); carry the strict/observable mode via a ContextVar bound from _ClientState at the top of _request (not env var, not module global — both are unsafe under the project's interleaved sync/async/WS-thread concurrency); emit flat, all-str, key-anchored-safe divergence records (never nested dicts, never wire values) because RedactingFilter does not traverse nested extra= structures and is marker-anchored, not value-anchored. The two biggest risks to mitigate before committing Phases 30-32: (1) Phase 29 is under-scoped by roughly 3x as currently written — 14 of 25 identified pitfalls land there, and several D-locks that 30-34 depend on (matriz's different semantics, the response-Literal policy, the log-spam aggregation contract, the redaction-gap fix, the six-way intactness test) need to become explicit Phase-29 artifacts, not implicit assumptions; (2) any strict-mode "sizing run" used to size Phase 33 will undercount by construction (fail-fast + convert's silent accept of NaN/Infinity from json.loads) unless it uses the per-field walker over the existing verification/snapshots corpus, not a single msgspec strict pass.

## Key Findings

### Recommended Stack

msgspec >=0.19,<0.22 (resolves to 0.21.1) is the one proposed addition — zero transitive deps, py.typed, BSD-3-Clause, decodes directly into stdlib frozen=True, slots=True dataclasses with no inheritance, which is exactly what keeps DT-01 (no third-party type in any public signature) achievable. Stack's own analysis frames it as a hard runtime dependency across all six wheels (wheel coverage is complete for every platform this project's consumers plausibly run); the optional-extra-with-_coerce-fallback pattern the plan floats is rejected on four grounds — the fallback IS the silent-tolerance bug being removed, it doubles code paths (12 not 6), doubles CI (24 jobs), and the AST surface gate cannot express "unless msgspec is absent." Nothing else in the dependency profile changes; msgspec becomes the first compiled artifact in an otherwise 100%-pure-Python closure — worth a README/DT-08 changelog line, not a blocker. GATE-TYP-01 (AST surface gate + sync/async parity introspection) needs no third-party dependency: stdlib ast + typing.get_type_hints + inspect are sufficient and were verified against all 130 public callables across the 6 packages with zero failures.

**Core technologies:**
- `msgspec>=0.19,<0.22`: fast-path strict decode detector inside from_api — never in public signatures; NOT the observable-mode engine (see tension below)
- stdlib `ast`/`typing`/`inspect`: AST surface gate + sync/async parity test — deliberately stays third-party-free so it runs even if msgspec is broken
- `httpx`, `python-dotenv`, `tenacity`, `platformdirs`, `websocket-client`: unchanged

### Expected Features

**Must have (table stakes):**
- Attribute-access typed model for every data return, zero Any/dict[str, Any] (TYP-01/02)
- Tolerant-by-default decode — API evolution must never crash the caller (already current behavior; DT-02 preserves it)
- `to_dict()` raw-payload escape hatch on every model — must ship in the SAME release as the dict-to-model break, not after
- `py.typed` + clean mypy --strict surface, including closing the D-16 gap for market-data-client
- Package logger + NullHandler (already shipped) as the emission channel for divergence records
- Migration guide / README changelog callout for the return-type break
- `Literal` aliases for enum-like INPUT params — checker-only, so an incomplete set is a suppressible type-check inconvenience, not a runtime break

**Should have (differentiators — genuinely ahead of the peer SDK set):**
- Observable divergence emission (one structured record per divergent field) — no mainstream Python client (stripe, openai, kubernetes) does this
- One decoder, two policies (observable at runtime / strict for drivers) via an explicit `_ClientState` flag — precedent: `mutating_allowed`
- Divergence record carrying endpoint + model FQN + surface(sync|async) — maps 1:1 onto the existing verification/findings.py API
- `DecodeReport`/collector accumulating N records per response — forced by msgspec's first-error-only behavior
- Machine-enforced homogeneity gates (AST + non-vacuous parity), since DT-03 (no shared code) means nothing else enforces the six packages staying structurally identical

**Defer (v1.7+, do NOT build now):**
- `__getitem__`/Mapping shim on models for dict-style backward compat — anti-feature: stripe's StripeObject did this for a decade and reversed it in v15 after field-name collisions with .items/.keys; it also defeats the milestone's entire purpose
- `Literal[...] | str` for inputs (openai pattern) — verified empirically to give ZERO mypy coverage, the union collapses to str
- `Literal` on response model fields — asymmetric with inputs: an incomplete response Literal converts vendor enum growth into a divergence storm or hard failure on legitimate data
- Recording the offending value in divergence records — unbounded credential/PII leak
- A shared `market-libs-core` package for the decoder — DT-03 locked
- Metrics/OTel emission from inside the decoder — infra-tier concern; logging.Handler already is the extension point
- Unmodelled-key preservation (CatchAll) — defer until F33 shows real demand

### Architecture Approach

Both existing state architectures (iol module-globals, market-data _ClientState) turn out to be identical under the hood — iol's module globals are a read-only PEP 562 shim forwarding to the same _ClientState dataclass pattern — so one insertion pattern serves all six packages. The decode boundary is architecturally forced to be inside from_api (dict), not bytes-in-parser: Client._request is a generic dispatcher that returns httpx.Response with zero type knowledge, and re-expressing the ~30 existing envelope-unwrap parsers as msgspec wrapper types would re-litigate live-verified Phase 4/5/27 work. The strict/observable mode flag must live on _ClientState (never Client.__slots__, which with_options() views don't copy) and be threaded via a ContextVar bound at the top of _request — this is the only carrier that survives interleaved async tasks and the matriz WS daemon thread without clobbering. Perhaps the most consequential finding: verification/ — including the existing public-surface golden-file gate — has never once run in CI. ci.yml passes an explicit packages/${{ matrix.package }} path to pytest that overrides testpaths. GATE-TYP-01 therefore needs a genuinely new CI job (or in-package parity tests riding the existing 6x2 matrix), not just a new test file dropped into verification/.

**Major components:**
1. `_decode.py` (NEW, x6, copied verbatim per DT-03) — msgspec fast-path detector + ContextVar mode carrier + per-field walker (the observable engine) + divergence emitter through the package logger
2. `models.py` — modified in-place (from_api body only, signature preserved per DT-05); matriz needs its OWN reconciliation pass, not a copy of the higyrus/market-data base
3. `tools/check_surface_types.py` (NEW) — stdlib-ast-only cross-package surface gate, runs in the existing lint job with zero package imports
4. `packages/<pkg>/tests/test_sync_async_parity.py` (NEW, per package) — rides the existing 6x2 CI matrix
5. `verification/divergences.py` (NEW) — a logging.Handler the drivers attach to collect observable-mode divergence records into findings

### Critical Pitfalls

1. **SafeModel/_coerce is NOT duplicated verbatim x3 — matriz has opposite semantics** (missing scalar becomes None not 0.0/""; no slots; empty() classmethod referenced inside class bodies via default_factory). Avoid by: a written 3-way semantics table as a Phase 29 artifact before any decoder code, a policy parameter baked in per package, and a merge gate run per-package with zero test edits.
2. **msgspec is fail-fast — any exploratory sizing run built on strict convert alone will undercount Phase 33's real scope by an order of magnitude**, and additionally under-counts because json.loads silently accepts NaN/Infinity that convert then passes straight into a float field with zero divergence. Avoid by: sizing with the per-field walker over the existing verification/snapshots corpus; report sizing as "greater than or equal to N," never "N."
3. **RedactingFilter does not cover the divergence-record shape.** It is key-anchored and only scans top-level string values in record.__dict__ — a nested extra={"divergence": {...}} dict bypasses it entirely. Avoid by: emit flat, all-str, top-level extra keys only, never the wire value, type-not-value; add a per-package caplog sentinel test for the decoder path (SEC-01 precedent extended to six new tests).
4. **matriz's response-side Literal fields are decorative today but become hard validation failures under strict decoding** — MATBA ROFEX adds instruments/segments/order-states over time, and the first strict run could produce a divergence per row for something that isn't a bug at all. Avoid by: an explicit Phase 29 D-lock deciding whether response Literals decode as str-with-divergence-report or stay Literal and get closed with live evidence in Phase 33.
5. **verification/ never runs in CI** (blocking for GATE-TYP-01) — the AST gate and parity tests must land as a new tools/ script wired into the existing lint job plus in-package tests, or they reproduce the exact silent-gate failure mode the milestone is trying to prevent elsewhere.

## Tensions to resolve explicitly (do not paper over)

**1. msgspec hard dependency vs. stdlib-only single engine.** Stack recommends msgspec as a hard runtime dependency across all six wheels, reasoning from wheel-coverage completeness and the cost asymmetry of a dual-path fallback. Features independently concludes the opposite is defensible: because msgspec structurally cannot serve the observable mode (headline finding), its real contribution is confined to a strict-path speed optimization that a project with no measured throughput requirement (low-QPS REST clients) may not need at all — Features frames "one engine, stdlib-only" as the recommended default unless a measured need appears, since it also dissolves the C-extension/wheel-availability risk entirely. Architecture's traced call chains show msgspec only earns its keep as the fast-path detector layered in front of the walker — both engines end up present either way in Architecture's design, but the walker is the load-bearing one regardless of the msgspec go/no-go. Recommend this be the milestone's first Phase 29 decision gate, argued from evidence on both sides rather than assumed: (a) two engines (msgspec fast-path + stdlib walker) — Architecture's recommended shape, buys ~0.5us on the common case at the cost of msgspec becoming the project's first compiled artifact; (b) stdlib-only single engine — Features' recommendation, zero new dependency, zero C extension, single code path, no observable/strict drift risk, at the cost of losing that fast-path speed (which nothing in the current corpus proves is needed).

**2. When/whether Literal params get evidence-closed.** The plan (DT-07) states Literal parameter sets are derived from live verification evidence, full stop. Pitfalls recommends a two-step sequence: ship str in Phase 30 for mercado/plazo if the set can't be closed with evidence yet, and promote to closed Literal only after Phase 33's live census. Features adds a second, independent axis: response-side Literals are flatly an anti-feature (A4) regardless of how well the set is closed, because an incomplete response Literal converts routine vendor enum growth into either a divergence storm or hard failures on legitimate data — asymmetric with input Literals, where an incomplete set is merely a suppressible type-check inconvenience. Architecture's matriz findings sharpen this further: matriz's EXISTING response-side Literal aliases (CFICode, MarketId, OrderType, Currency) are currently decorative/unvalidated and would newly become enforced under any msgspec-backed decode path — meaning DT-07's evidence-closure obligation retroactively attaches to matriz's pre-existing types.py, not just iol's new mercado/plazo. Recommend Phase 29 lock: input Literals may ship as str-with-carry-forward-note if unclosable; response-side fields never become closed Literals in this milestone regardless of evidence quality — decode them as str internally with an out-of-set-value reported as a divergence.

**3. CI enforcement gap.** verification/ — including the pre-existing public-surface golden-file gate — has never executed in CI because ci.yml passes an explicit per-package path argument that overrides testpaths. GATE-TYP-01 (Phase 32) is not "add a test file" but "stand up new CI surface": a stdlib-ast-only script in the existing lint job plus in-package test_sync_async_parity.py files riding the existing 6x2 pytest matrix, and optionally a new gates: job to retroactively activate the ~25 existing verification/ meta-tests (expect an initial red run against pre-existing known failures).

**4. Four D-16 enrollment lists already disagree.** mypy files in root pyproject.toml has 5 of 6 packages (market-data-client missing); import-linter root_packages has only 4 (wallets and market-data-client missing); ci.yml's mypy-tests loop has 5 (market-data-client missing); verification/test_public_surface.py::_PACKAGES has 4 (wallets and market-data-client missing, the latter BY DESIGN since market-data-client already has its own in-package surface test from Phase 25 — this exclusion is deliberate and must stay documented, not "fixed"). The underlying mypy backlog is trivial (2 one-line var-annotated errors, src is already clean) — the real work is deciding, explicitly and in one atomic commit, whether wallets_client joins root_packages and _PACKAGES in this milestone, and RED-proving the new market-data-client _core import-linter contract.

## Implications for Roadmap

The plan's existing 6-phase structure (29-34) is directionally correct and should NOT be reshuffled — all four research files independently converge on the same phase boundaries and the same load-bearing-first ordering. The correction is scope and content within Phase 29, not phase count or order.

### Phase 29: Decoder foundation (DEC-01) — expand scope, do not split
**Rationale:** All four researchers agree this must land first and gates everything downstream. But Pitfalls found 14 of 25 total pitfalls land here, meaning the plan's current Phase 29 scope (single task) is roughly 3x under-scoped.
**Delivers:** Two-pass decoder (msgspec fast-path detector — pending the go/no-go decision — + stdlib per-field walker as the actual observable-mode engine), matriz's separate semantics reconciled (not harmonized), response-Literal D-lock, ContextVar mode carrier bound from _ClientState, six-way intactness test (byte/AST-equivalence across the verbatim copies), ban-list grep gates (strict=False, msgspec.field()), ~5000-row log-spam aggregation contract, RedactingFilter extended to recurse into nested extra= values across all six _logging.py copies, exploratory sizing run using the walker (not a raw msgspec strict pass) to size Phase 33, to_dict() landed early.
**Addresses:** DEC-01, and pulls forward the D-16 mypy/import-linter half.
**Avoids:** Pitfalls 1 (matriz semantics), 2 (matriz response Literals), 3 (undercounted sizing), 4 (log spam), 5 (redaction gap), 6 (TYPE_CHECKING NameError), 7 (silent field-rename/extra-field failures), 8 (NaN), 9 (received_at stamp collision), 10 (strict=False temptation), 17 (six-way drift).

### Phase 30: iol-client typed (TYP-01)
**Rationale:** First real end-to-end exercise of the Phase 29 decoder against a package with no existing models.py.
**Delivers:** New models.py, Quote/TituloCotizacion/Punta models derived from the already-committed live schema snapshots, mercado/plazo as Literal or documented str carry-forward, main_iol.py migrated at its 2 real consumption sites (not 6 as originally estimated — Architecture corrects this).
**Uses:** the two-pass decoder from Phase 29; to_dict() as the migration escape hatch.
**Implements:** TYP-01, feeding DT-08's semver bump obligation for iol 0.2.0 to 0.3.0.

### Phase 31: Ops endpoints + structural uniformity (TYP-02, TYP-03)
**Rationale:** Parallelizable with Phase 30. Requires special care because two of the five target endpoints (add_holidays, delete_holiday) are already-published v0.4.0 mutations with a live-verified idempotency contract and a mutation-gate-ordering invariant that must not be perturbed by response-typing work.
**Delivers:** Response models for get_health/get_health_feed/add_holidays/delete_holiday, models.py+types.py presence (even if empty) in all six packages including wallets.
**Addresses:** TYP-02, TYP-03.
**Avoids:** Pitfall 13 (mutation-gate displacement) — scope strictly to response-side edits only, with a byte-identical-request regression test proving the wire request is unchanged.

### Phase 32: Homogeneity gates + D-16 closure (GATE-TYP-01)
**Rationale:** Must come after Phase 30/31, but the D-16 half is independent and ideally pulled forward into 29.
**Delivers:** AST surface gate (stdlib-only, wired into the lint CI job, non-vacuous with a RED fixture), per-package sync/async parity tests riding the existing matrix, D-16's remaining enrollment (all four lists reconciled in one atomic commit).
**Addresses:** GATE-TYP-01, DT-09.
**Avoids:** Pitfall 14 (vacuous gates), Pitfall 15 (AST false negatives), Pitfall 16 (D-16 list disagreement).

### Phase 33: Live verification + fixes (LIVE-TYP-01)
**Rationale:** This is the phase the Phase 29 exploratory sizing run exists to budget for; strict mode flips on for the drivers here.
**Delivers:** Divergence findings across all 4 verifiable packages, Literal sets closed with live evidence (iol's new ones AND matriz's pre-existing CFICode/MarketId/OrderType/Currency), fixes mirrored sync/async with mocked regression tests.
**Requires:** D2 (strict mode) + D3 (rich divergence record) from Phase 29; budget assumes the Phase 29 sizing number is a floor, not an estimate.

### Phase 34: Per-package releases (PUB-TYP-01)
**Rationale:** Unchanged from the plan; Stack's one correction is that uv.lock refreshes exactly once globally regardless of how many packages bump.
**Delivers:** Bumps, README changelogs (with the iol truthiness-flip callout explicitly first per Pitfall 11), tags, GitHub Releases, the D-18 double-human-gate for irreversible ops.

### Research Flags

Needs deeper research/discussion during planning:
- **Phase 29:** the msgspec two-engine vs. stdlib-only decision gate (tension #1) should be resolved via discuss-phase before plan-phase, since it changes the dependency profile of all six wheels.
- **Phase 30:** whether anything outside this repo consumes iol-client 0.2.0 — affects whether the dict-to-model break needs any transitional shim consideration at all.
- **Phase 33:** genuinely can't be sized until Phase 29's exploratory walker run completes; treat its scope as provisional until then.

Standard patterns (established precedent in-repo, low research need):
- **Phase 31:** the _ClientState/with_options pattern and mutation-gate structure are already well-established.
- **Phase 32:** the AST-gate-and-parity-test shape has a direct precedent in the project's own WR-01/WR-02 vacuous-gate fix recipe.
- **Phase 34:** identical shape to prior release phases (28-01, 28-02) — no new pattern needed.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Every claim verified by direct execution against msgspec 0.21.1, PyPI/GitHub JSON APIs, or the repo itself |
| Features | MEDIUM-HIGH | msgspec/mypy behavioral claims are first-party empirical runs (HIGH); ecosystem-practice claims (stripe/openai/kubernetes precedent) are web-tier secondary sources (MEDIUM) |
| Architecture | HIGH for integration mechanics (every claim read off the repo at a specific commit/line or measured); MEDIUM for divergence-volume estimates |
| Pitfalls | HIGH for msgspec behavior and repo-state claims; MEDIUM for divergence-volume predictions |

**Overall confidence:** HIGH. The convergence of four independently-run researchers on the same headline finding (msgspec cannot implement observable mode) and the same structural correction (matriz is not verbatim) is itself strong corroborating evidence, not just four separate opinions.

### Gaps to Address

- **Real divergence volume in live payloads is unknown** until Phase 29's exploratory walker run executes — every phase-sizing statement in this summary and in the plan is provisional on that run.
- **The msgspec go/no-go (tension #1) is unresolved** — this summary presents both positions with their evidence; the roadmapper and Phase 29 discuss-phase should treat it as an open decision, not pre-settle it in the roadmap document.
- **Whether iol-client has real external consumers** is unknown — affects Phase 30's scope and whether any transitional dict-compat consideration is needed at all.
- **matriz's exact reconciliation plan needs its own sub-task definition** during Phase 29 planning — the three-way semantics diff exists in this research but the actual decoder-policy-parameter design is not yet written as code.

## Sources

Aggregated from the four dimension files — see each for full citation lists.

### Primary (HIGH confidence)
- Direct execution against msgspec 0.21.1 (multiple independent verification runs across all four researchers, 2026-08-18)
- Direct execution against this repo (.venv/bin/python, CPython 3.12.13) — get_type_hints 130/130 across 6 packages, AST gate prototypes, uv lock --check, uv pip compile resolution
- Repo inspection at commit adb82f5 / branch milestone/v1.5-mutations — pyproject.toml, ci.yml, all six packages' client.py/aio.py/models.py/_state.py/_logging.py, verification/ test suite, .planning/verification/schemas/iol-client/*.json live schema captures (2026-06-06)
- PyPI JSON API (msgspec + 10-package pure-Python-closure verification) and GitHub API
- First-party mypy --strict runs — TypedDict .get() blind spot, Literal | str zero-coverage verification

### Secondary (MEDIUM confidence)
- stripe-python RFC #1454 and v15 migration guide
- openai-python DeepWiki source analysis + issues #2204/#1300
- pydantic/marshmallow/dataclasses-json config docs

### Tertiary (LOW confidence)
- kubernetes-client client_side_validation as a policy-toggle precedent
- "No mainstream Python client emits divergence telemetry" — argued from absence of evidence across 4 surveyed SDKs
- Schema-drift-monitoring-is-infra-tier claim — search returned mostly vendor/SEO content

---
*Research completed: 2026-08-18*
*Ready for roadmap: yes*
