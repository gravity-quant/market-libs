# Stack Research

**Domain:** Backlog closeout on an existing Python client-library monorepo (no new packages, no new domain)
**Researched:** 2026-08-31
**Confidence:** HIGH

---

## Headline: No new stack needed

**The honest answer is that v1.8 requires zero new libraries, zero new dev tools, zero new CI jobs, and zero new scripts.** Every one of the four target groups is executable with what is already on disk at HEAD. This was not assumed — each claim below was verified by direct inspection or by executing the tool.

There is exactly **one tooling change** required, and it is a ~10-line edit to an existing script (`scripts/literal_census_33.py`), not a new dependency. It is described in detail below because the ROADMAP currently states the opposite.

No external research providers were consulted, and none were needed: `gsd-tools query init.phase-op` reports `brave_search: false`, `firecrawl: false`, `exa_search: false`, and every question in scope is answerable against first-party repo state. Nothing new is proposed, so there is no third-party version to verify against upstream docs.

---

## Recommended Stack

### Core Technologies — all already installed, all unchanged

| Technology | Version (declared floor → installed) | Purpose | Why Recommended |
|------------|--------------------------------------|---------|-----------------|
| Python | `>=3.12` → 3.12.13 (`.venv/`) | Runtime for all 4 groups | CI matrix is 3.12+3.13; nothing in v1.8 needs a newer feature |
| uv | 0.11.3 | Workspace + `uv run` invocation | Every command in this milestone is `uv run …`; `uv.lock` is committed and `uv lock --check` is a CI gate |
| httpx | `>=0.27` | Live HTTP for LIVE-01/02 | Already the sole transport; the census script and the 5 drivers both ride it |
| pytest | `>=8.3` → 9.0.3 | Regression tests for SHAPE-01 / HARN-01 / HARN-02 | `asyncio_mode = "auto"`, `--import-mode=importlib` already configured |
| pytest-httpx | `>=0.34` | Mocked regression pins for the SHAPE-01 field fix | The established pattern for every in-cycle shape fix since v1.4 |
| ruff | `>=0.7` → 0.15.12 | Lint + format gate | `uv run ruff check .` covers **the whole repo including `scripts/`** — the census-script edit must pass it |
| mypy | `>=1.13` → 1.20.2 | Strict typecheck | Scope is `packages/*/src` only — see "Integration points" for what that means for `scripts/` and `verification/` |
| import-linter | `>=2.11,<3` | `_core` boundary contracts | Untouched by v1.8; SHAPE-01 edits `models.py`, not `_core.py` |

**Nothing is added to any package's runtime `dependencies`.** SHAPE-01 and HARN-02 are pure `@dataclass(frozen=True, slots=True)` field-declaration edits on existing `SafeModel` subclasses. That is stdlib.

### Existing project scripts and harness — the actual "stack" for this milestone

| Asset | Path | Used by | State verified |
|-------|------|---------|----------------|
| `literal_census_33.py` | `scripts/literal_census_33.py` | LIVE-02 | **Exists (14,987 bytes). `--selftest` PASSES today.** One stale gate — see below |
| `preflight_33.py` | `scripts/preflight_33.py` | LIVE-01 (higyrus DNS re-probe) | Exists (5,010 bytes); this is the tool that produced the `AUTH FAIL ConnectError` diagnosis in Phase 33 |
| `main_higyrus.py` | repo root | LIVE-01 | Already emits the `SKIPPED — vendor inalcanzable` line with measured cause |
| `verification/findings.py` | `verification/findings.py:597` | HARN-01 | **`idempotent_by_title: bool = False` parameter already exists.** HARN-01 is a call-site change, not a new feature |
| `verification/capture.py` | `verification/capture.py` | LIVE-02 | Census dumps raw payloads to gitignored `.planning/verification/captures/` |
| `verification/mutation_gate.py` | `verification/mutation_gate.py:73` | LIVE-02 (by *not* touching it) | `_SANDBOX_HOST = "api.remarkets.primary.com.ar"` — remarkets-only, fails closed under bbsa **by design** |
| 4 CI gates | `tools/check_decode_intactness.py`, `check_uniform_structure.py`, `check_surface_types.py`, `surface_parity.py` | SHAPE-01 / HARN-02 guardrails | All four run in the `lint` job; SHAPE-01 must keep `check_surface_types.py` green |
| `/gsd-validate-phase` | `.claude/gsd-core/workflows/validate-phase.md` | NYQ-01 | Fully wired — see below |

### Development Tools — configuration facts that matter for v1.8

| Tool | Purpose | Notes |
|------|---------|-------|
| `uv run ruff check .` | Lint gate | Covers `scripts/` and `verification/`, unlike mypy. The census-script gate edit **will** be linted |
| `uv run mypy` | Typecheck gate | `files = [packages/*/src ×6]`. `scripts/` and `verification/` are **out of scope** — this is why HARN-VERIF-01's 43 mypy errors are invisible (`.pre-commit-config.yaml:32` is scoped `^packages/.*/src/` too) |
| `pytest` explicit allowlist in CI | `verification/` guard tests | `.github/workflows/ci.yml:79-92` runs a hand-maintained list of 12 `verification/test_*.py` files, never `pytest verification/`. **Any new guard test must be added to that list by hand or it is inert** — this is exactly the WR-01 defect Phase 36's code review found |
| `pyproject.toml` `testpaths` | Local runs | `["packages", "tests", "verification"]` — a bare local `pytest` picks up the red HARN-VERIF-01 baseline. Use `uv run pytest packages/ -q` |

---

## Installation

```bash
# Nothing to install. The workspace is already synced.
uv sync --all-packages --all-extras --dev --frozen
```

If SHAPE-01 ships a version bump, the only lockfile action is the established one-shot refresh (Phase 34 / Phase 40 precedent, commit `f1e1a3e`):

```bash
uv lock            # regenerates only the bumped package's version entry
uv lock --check    # the CI gate that must then pass
```

---

## The one required tooling change: LIVE-02's census gate is stale

**This contradicts the ROADMAP and needs to be corrected in the phase plan.**

`ROADMAP.md:64` states that *"`scripts/literal_census_33.py` ya tiene el gate remarkets-only listo para correr contra el sandbox `bbsa` ahora desbloqueado."* — and `PROJECT.md:174` repeats the same premise ("ahora desbloqueado por el allowlist de hostname `bbsa` que Phase 39 habilitó").

**Measured reality:** the Phase 39 D-02 allowlist widening landed **only in `main_matriz.py`**. The census script was never touched.

```python
# scripts/literal_census_33.py:191-192  — the OLD Phase-33 substring gate
base = client._state.base_url
if "remarkets" not in base:
```

Against `bbsa.matrizoms.com.ar`, `"remarkets" not in base` is `True`, so the script prints `SKIPPED — base URL fuera de política` and returns `False` **before authenticating and before emitting a single request**. Run as-is today, LIVE-02 produces exactly the same skip it produced in Phase 33 — a green run that measured nothing.

The correct fix is to port the already-reviewed, already-human-approved primitive from `main_matriz.py`, not to invent a second one:

| Source (authoritative) | Target |
|---|---|
| `main_matriz.py:139` `_VENUE_ALLOWLIST: dict[str, str]` (exact-hostname equality: `api.remarkets.primary.com.ar` → `remarkets`, `bbsa.matrizoms.com.ar` → `bbsa`) | replaces `scripts/literal_census_33.py:192` |
| `main_matriz.py:229-247` hostname extraction via `urllib.parse.urlsplit`, `.hostname`, fail-closed `None` | the lookup helper the census calls |

**Why exact-equality and not the substring:** `main_matriz.py:126-127` records that the old substring check would have admitted `https://api.remarkets.primary.com.ar.attacker.example`. Porting the allowlist makes the census script *stricter* than it is today, not looser. Do not weaken it to `"bbsa" in base`.

**Two guardrails to preserve while doing this:**
1. `verification/mutation_gate.py:73` `_SANDBOX_HOST` stays remarkets-only. Phase 39 deliberately left it untouched so order entry stays fail-closed under bbsa with zero code change. Touching it is scope creep with a real safety cost.
2. The skip path must keep printing the *cause* without printing the resolved URL (`literal_census_33.py:193-198` already does this). The non-leak criterion is load-bearing.

**Everything else in the census script is intact — verified, not assumed:**

- `uv run python scripts/literal_census_33.py --selftest` → `SELFTEST: PASS` (8 synthetic paths, both packages). The walker is not a dead channel.
- All 5 matriz `_core` builders it calls still exist post-Phase-37 strict-unwrap and post-Phase-39 `_normalize_instrument_element`: `build_get_segments_request`, `build_get_all_instruments_request`, `build_get_instruments_details_request`, `build_get_active_orders_request`, `build_get_all_orders_request`.
- Both iol builders still exist: `build_get_instruments_by_type_request`, `build_get_quote_request`.
- `Client._request(self, spec: RequestSpec) -> httpx.Response` signature unchanged in both `matriz_client/client.py:378` and `iol_client/client.py:436`.

This last point matters: the census script does **not** have the signature rot that broke the matriz `verification/` harness (HARN-04). Those two files call probes with pre-REFAC-05 signatures; this script calls `_core` builders, which never changed shape.

---

## Per-group verdicts

### LIVE-01 (higyrus DNS re-check) — no new stack

`scripts/preflight_33.py` + `main_higyrus.py` are the tools. The measured cause is `socket.gaierror` on DNS resolution — network reachability, not credential rejection. Nothing in the stack can fix an unresolvable hostname.

**Do not add:** a DNS-mocking library, a retry/backoff wrapper, or a VPN client. The correct v1.8 outcome is either (a) it resolves now and the census runs, or (b) it still doesn't and the phase records the re-measured cause. Both are stack-neutral.

One documented gap worth folding in cheaply: Phase 39 WR-02 noted higyrus does not catch `httpx.ConnectTimeout` in the vendor-unreachable branch (a documented scope limit, asserted in-code). That is a two-line `except` widening in an existing driver — still no new stack.

### LIVE-02 (matriz Literal RESPONSE census) — one existing-script edit

Covered above. After the gate port, the run needs only `PRIMARY_BASE_URL` / `PRIMARY_USER` / `PRIMARY_PASSWORD` (+ optional `PRIMARY_ACCOUNT` to reach the `ordType` census on the two orders endpoints). `.env` for matriz already exists per CLAUDE.md.

Note that Phase 39 already committed bbsa schema baselines (`.planning/verification/schemas/matriz-client/get-segments.bbsa.json`, `get-instruments-details.bbsa.json`, `get-instruments-by-cfi-esxxxx.bbsa.json`, `get-instruments-by-segment.bbsa.json`). These record **type names**, not values — `verification.schema.schema_of` reduces each value to its type. They do not substitute for the census, which is the whole point of `literal_census_33.py` reading the raw wire.

Collateral documentation fix already scoped in the backlog: `29-DLOCK-RESPONSE-LITERAL.md:140-142` claims the divergence stream is the census mechanism. It is not — the `Literal` branch of `_decode.walk_field` returns early with `literal_enforced=False` and never calls the sink. The lock is signed, so the correction belongs to the signer.

### NYQ-01 (`/gsd-validate-phase` on Phases 35-39) — zero project-side setup, verified by execution

Every prerequisite was checked by running the tooling, not by reading docs:

| Prerequisite | Check | Result |
|---|---|---|
| Nyquist hook active | `gsd-tools loop render-hooks verify:post --raw` | `capId: "nyquist"`, `kind: "step"`, `ref.skill: "validate-phase"`, `when: workflow.nyquist_validation`, `onError: halt` — **active** |
| Auditor agent installed | `ls .claude/agents/` | `gsd-nyquist-auditor.md` present |
| Auditor model resolves | `gsd-tools query resolve-model gsd-nyquist-auditor --raw` | `sonnet` |
| Archived phase dirs resolve | `gsd-tools find-phase 35` / `39` | `found: true` → `.planning/milestones/v1.7-phases/35-…` and `…/39-…`, with all 5 and 8 PLAN+SUMMARY files enumerated |
| `init.phase-op` resolves archived dirs | `gsd-tools query init.phase-op 35` | `phase_found: true`, `phase_dir` correct, `agents_installed: true`, `missing_agents: []` |
| Input state | `35-VALIDATION.md` exists with `status: draft`, `nyquist_compliant: false` | **State A** (audit existing), not State B/C |

This was the highest-risk unknown going in — the v1.7 phase directories were archived out of `.planning/phases/` into `.planning/milestones/v1.7-phases/` by `/gsd-complete-milestone`, and `.planning/phases/` no longer exists. **The resolver handles it.** No un-archiving, no symlinks, no `--dir` flag, no config change.

**Do not add:** a shim to restore `.planning/phases/`, or a custom script to walk the archived dirs. Both would be solving a problem that does not exist.

The one thing to expect: the workflow's Test Infrastructure detection will read each phase's existing `VALIDATION.md`, whose Quick/Full run commands already carry the correct project-specific caveat (`uv run pytest packages/ -q` — **NEVER bare `pytest`**, because `verification/` is red at baseline and slow). That caveat is already written into the drafts; it does not need to be re-derived.

### SHAPE-01 (`Instrument`/`Segment` field correction) — no new stack; a well-worn process precedent

The change itself is stdlib dataclass field edits at `packages/market-data-client/src/market_data_client/models.py:787` (`Instrument`) and `:803` (`Segment`), mirrored by regression tests using the already-installed `pytest-httpx`.

The measured delta against the committed baselines (`/.planning/verification/schemas/market-data-client/get-instruments.json`, `get-segments.json`, both captured 2026-07-31 against `market-data-develop.bbsa.com.ar`):

| Model | Declared today | Real wire (baseline `schema.items[0]` / `schema.segments[0]`) |
|---|---|---|
| `Instrument` | `symbol`, `marketId`, `segment`, `instrumentType`, `expired` | `symbol`, `segment`, `expired` ✓ · plus `market_id: str`, `currency: str`, `days_to_maturity: int`, `maturity: str`, `outright: bool`, `subscribed: bool`, `active: NoneType` · `marketId`/`instrumentType` **not sent** |
| `Segment` | `marketSegmentId`, `marketId`, `description` | `segment: str`, `live_instruments: int` — **disjoint sets**; every `get_segments()` row is all-empty today |

Note `"active": "NoneType"` in the live capture. Under the v1.7 D-NO-03 rule this is a **scalar leaf**, so `bool | None` is correct and does not violate the Null Object policy. This is the same class of call as Phase 36's deferred `market_id`/`active` leaves, which Phase 40 resolved as nullable in the v0.6.0 D-12 batch — that is the precedent to follow, not to re-litigate.

**Existing pattern for a source-breaking model fix + version bump — confirmed, three times over (v1.5 Phase 28, v1.6 Phase 34, v1.7 Phase 40):**

1. **Decision gate first.** A source-breaking change to a published surface requires a genuine blocking human checkpoint. This is the exact reason plan 33-07 Task 1 refused to make this change: the operator authorized SC-1/SC-2/SC-3 and this was not among them, and T-33-44 prohibits contract changes without a decision. Key Decision rows for v1.6 Phase 34 D-08 and v1.7 Phase 40 both record that these gates were **never auto-approved despite `auto_advance: true` + `mode: yolo`**. Follow-up already recorded in Key Decisions: use `gate="blocking-human"`, not `gate="blocking"`, so the orchestrator does not have to detect the intent from prose each time.
2. **Version sites — there are four, and there is no `CHANGELOG.md`.** `packages/market-data-client/pyproject.toml:3` (`version = "0.6.0"`), `src/market_data_client/__init__.py:163` (`__version__ = "0.6.0"`), and **two install lines in `README.md`** (the `git+…@market-data-client-v0.6.0#subdirectory=…` line and the GitHub-Release wheel URL). The v1.6 Phase 34 code review caught a real live bug on `main` from missing exactly one of these README sites.
3. **Changelog lives in `README.md`**, under `## Changelog` → `### vX.Y.Z`, with a prose BREAKING callout followed by an `| Antes (0.5.0 publicado) | Ahora (0.6.0) |` before/after migration table. `packages/market-data-client/README.md:125` is the v0.6.0 exemplar to copy.
4. **Bump shape:** 0.x minor bump carries breaking changes (v0.5.0 → v0.6.0 was source-breaking). SHAPE-01 alone implies `market-data-client` 0.6.0 → **0.7.0**.
5. **Publication is a separate, double-gated act** if v1.8 chooses to release: PR → explicit count gate (`TOTAL=15 && PASSED=15`, never absence-of-"fail" — v1.6 D-09 caught both a real mypy failure and a transient zero-checks race) → human approval #1 → merge → human approval #2 → annotated per-package tag on the merge commit → `release.yml` (unedited, D-02/D-06).

**Legitimate scoping choice for the phase to make explicitly:** fix-and-hold (land the shape fix, defer publication to a later release cycle) versus fix-and-publish. The backlog entry names both. Either is defensible; leaving it undecided is not, because a source-breaking edit sitting unreleased on `main` is how the v1.6 README-vs-changelog mismatch happened.

### HARN-01..04 — no new stack; three are one-line-class edits and one is a decision

**HARN-01 (schema-drift dedupe).** The `idempotent_by_title` primitive already exists at `verification/findings.py:597`, is documented in-place as Phase 11 HARN-08/10, is already used correctly at ~5 other sites, and is already covered by `verification/test_findings_dedupe_by_title.py`. The fix is passing the kwarg. AST-measured call sites currently missing it:

| Driver | Line | Title |
|---|---|---|
| `main_market_data.py` | 511 | `f"schema drift en {client_function}"` |
| `main_iol.py` | 1754 | `f"Schema drift en {func_name}"` |
| `main_higyrus.py` | 590 | `f"Schema drift en {func_name}"` |
| `main_matriz.py` | 584 | `f"Schema drift en {func_name}"` |
| `main_ambito_financiero.py` | 608 | `"Schema drift en get_dollar_banco_nacion"` |
| `main_iol.py` (siblings, same family) | 1617, 1685 | `f"type drift on \`{key}\` in …"` |

Six schema-drift sites, plus two iol `type drift` siblings the phase should consciously include or exclude rather than miss. Note the drift branch shares the fid allocator, so `verification/test_finding_count_consistency.py` already asserts consistency over it — that is the existing net, no new test infrastructure needed.

**HARN-02 (5 remaining `extra` keys).** `HealthFeed.symbols_never_delivered: int`, `FeedIngestor.last_error_age_seconds: int`, `.last_error_at: str`, `.subscription: dict`, `Symbol.note: str`. Pure field declarations on existing `SafeModel` subclasses (`models.py:1264` `FeedIngestor`, `:1307` `HealthFeed`, `:817` `Symbol`). `extra` is informative by Phase 29 policy (emitted at INFO, never raises), so this is surface-coverage work, not defect repair — it does **not** carry the semver weight SHAPE-01 does, though it is additive-and-therefore-safe either way.

The `.subscription: dict` one deserves a note: declaring it as `dict[str, Any]` would be **rejected by `tools/check_surface_types.py`** if `FeedIngestor` is reachable from `__all__`. Under the v1.7 D-NO-06 rule it needs its own typed `SafeModel` (local copy, no cross-package import), the same move Phase 36 made for `MarketDataEntries`. Plan for that, don't discover it at gate time.

**HARN-03 (stale comment).** `tools/check_surface_types.py:47` and `:58` both say `330 definitions scanned`; the measured value is 336. Two docstring lines. Companion cosmetics named in the backlog: `matriz_client/__init__.py` still lacks `__version__` (pre-existing), and `verification/test_public_surface.py` is still absent from the CI lint job's explicit list (pre-existing — see the `ci.yml:79-92` allowlist note above; adding it is a one-line CI edit, but it must be a *deliberate* one because the list is hand-maintained on purpose).

**HARN-04 (matriz `verification/` harness fate).** This is a decision, not a stack question. Measured state: `verification/test_matriz_sweep_snapshot.py` (337 lines, 17 FAILED + 17 ERROR) and `verification/test_main_matriz_login_fail_uniformity.py` (84 lines, 2 FAILED + 2 ERROR) call `main_matriz.py` probes with pre-REFAC-05 (Phase 15) no-argument signatures. That is 100% of the `verification/` red. Repairing them needs no new tool — only the same argument-threading the drivers already use. The standing caution from the backlog stands: these two files are the **canary** for the `probe_context` refactor of plans 33-02/33-03 precisely because they invoke probes directly rather than through `main()`, so repairing them removes a detector as well as a red line.

If the decision is "repair," the corollary is enrolling them in the `ci.yml` explicit allowlist — otherwise they stay invisible-by-construction and rot again. If the decision is "accept as debt," it must be written down formally, because this item has now rolled silently across v1.6, v1.7 and into v1.8.

---

## What NOT to Use — scope-creep flags

This is cleanup, not feature work. Each row below is something a well-meaning plan could plausibly reach for, and each is wrong here.

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `msgspec` / `pydantic` / `attrs` for the SHAPE-01 or HARN-02 model edits | Signed D-lock (v1.6 Phase 29 DT-01): msgspec is **NO-GO, stdlib-only**; the spike measured the stdlib walker at 19.4ms against a 100ms budget. Pydantic was rejected for lenient coercion + weight across 6 wheels | The existing `@dataclass(frozen=True, slots=True)` + `SafeModel` + `_decode` walker |
| A shared `market-libs-core` package to hold the field fixes | No shared code between packages is an architectural constraint (CLAUDE.md, DT-03, D-NO-06). Phase 36 explicitly copied the Null Object pattern locally rather than import cross-package | Local, per-package edits |
| Re-opening codegen / `unasync` / `libcst` to sync `client.py`↔`aio.py` | REFAC-06 is **permanently shelved** on two signed NO-GOs (SPIKE-005, SPIKE-006). Do not re-open without a new tool class or a decision to relax D-02 | Mirror the sync/async edit by hand, as every prior phase did |
| Enrolling `verification/` wholesale into mypy `files`, or running `pytest verification/` in CI | `ci.yml:75-78` documents the explicit-list choice on purpose: the directory carries pre-existing red (HARN-VERIF-01). A wholesale enrollment turns a scoped cleanup into a 43-mypy-error, 38-test-failure yak shave | If HARN-04 lands "repair," add exactly the repaired files to the hand-maintained allowlist |
| `jsonschema`, `dataclasses-json`, `datamodel-code-generator`, or vendoring the OpenAPI spec to derive `Instrument`/`Segment` | D-10 forbids retyping on the spec's authority alone. The live OpenAPI types these rows as bare `object` with `additionalProperties: true` — it would tell you nothing anyway | The committed live baselines `get-instruments.json` / `get-segments.json`, which are **measured** wire shape |
| A `--live` flag, a new pytest marker, or a new test runner for LIVE-01/02 | D-01 already settled this: the split is `require_env`-driven offline/skip, not a flag. A `@pytest.mark.live` marker already exists from HARN-01..06 | `uv run python scripts/literal_census_33.py`, gated by env presence |
| A new CI job/workflow for the census or the live drivers | These are credentialed, network-dependent, market-hours-sensitive, and touch a venue with an order-entry surface. They must never run unattended in CI | Operator-runs-and-pastes, the Phase 23 / Phase 33 / Phase 39 precedent |
| Weakening or widening `verification/mutation_gate.py` `_SANDBOX_HOST` to admit bbsa | Phase 39 deliberately left it remarkets-only so matriz order entry stays fail-closed under bbsa with zero code change. LIVE-02 is read-only and does not need it | Leave it untouched; port the allowlist only into the census script's read gate |
| A second, ad-hoc hostname check written fresh in `literal_census_33.py` | Two divergent implementations of a security gate is how the Phase 33 substring gate survived past its own widening | Port `_VENUE_ALLOWLIST` + the `urlsplit` helper verbatim from `main_matriz.py:139/229-247` |
| `vcrpy` / `pytest-recording` to make the live census reproducible | `verification/capture.py` + the write-once schema-snapshot mechanism (DRIFT-01) already fill this role, with gitignored raw-payload staging | The existing capture + baseline machinery |
| A generic "dedupe all findings" refactor of `verification/findings.py` | The primitive exists and is content-addressed; the file is append-only by contract with operator-field preservation. Refactoring it risks the Classification/Rationale/Regression/Resolution preservation guarantee | Pass `idempotent_by_title=True` at the 6 measured call sites |
| Un-archiving `.planning/phases/` for NYQ-01 | Verified unnecessary — `find-phase` and `init.phase-op` both resolve `.planning/milestones/v1.7-phases/*` correctly | Run `/gsd-validate-phase 35` … `39` as-is |
| Bumping `ambito-financiero-client` or `wallets-client` | Their surfaces do not change in v1.8. v1.7 correctly left both unbumped | Bump only `market-data-client`, and only if SHAPE-01 lands |

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Port `_VENUE_ALLOWLIST` into `literal_census_33.py` | Extract the allowlist into a shared `verification/venue_allowlist.py` consumed by both driver and script | Reasonable *if* a third consumer appears. Today it is two call sites, and `main_matriz.py`'s copy is the one that carries the Phase 39 human-approved review. Extracting means re-reviewing a security gate for zero present benefit — defer |
| Fix-and-hold SHAPE-01 (land the shape fix, defer the release) | Fix-and-publish (bump to 0.7.0 and run the full double-gated release inside v1.8) | Publish if the operator wants a consumable artifact this cycle and is prepared for the two blocking human gates. Hold if v1.8 is meant to stay a cleanup milestone — but then say so explicitly in the phase record |
| Repair the two broken matriz `verification/` files (HARN-04) | Formally document as accepted debt and delete/xfail them | Accept-as-debt is legitimate if the phase judges the canary value already spent; it is **not** legitimate to leave undecided a fourth milestone running |
| Type `FeedIngestor.subscription` as a new local `SafeModel` | Add it to the `check_surface_types.py` DT-06 exemption list | Exempt only if the live wire shape is genuinely unbounded/opaque; the v1.7 precedent is that `UnknownFrame.raw` is the *single* exemption anyone earned, and it took a phase to justify |
| Operator-runs-and-pastes for LIVE-01/02 | Automate behind an env-gated CI job | Never for matriz (order-entry surface); potentially for higyrus if it ever becomes reachable from CI's network — which is exactly what LIVE-01 is measuring |

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| Python 3.12.13 (venv) / 3.13 (CI) | everything in scope | `from __future__ import annotations` is mandatory and uniform; nothing in v1.8 needs a 3.13-only feature |
| pytest 9.0.3 installed vs `>=8.3` declared | pytest-asyncio `>=0.24`, pytest-httpx `>=0.34` | Installed is well ahead of the floor and green today. **Do not tighten or bump the floor** as part of v1.8 — a dependency-range edit inside a cleanup milestone is an unforced CI risk |
| mypy 1.20.2 installed vs `>=1.13` declared | strict mode over `packages/*/src` | SHAPE-01's field edits must stay strict-clean; `scripts/` is out of scope, so the census gate edit is lint-only |
| ruff 0.15.12 installed vs `>=0.7` declared | `line-length = 100`, `target-version = "py312"` | Applies to `scripts/literal_census_33.py` — the ported allowlist must be formatted and import-sorted |
| `market-data-client` 0.6.0 (published) | prospective 0.7.0 | Four version sites + README changelog + migration table, per the Phase 40 pattern. `uv lock` refresh is a single follow-up commit (`f1e1a3e` precedent) |
| The 4 CI gates | SHAPE-01 + HARN-02 edits | `check_surface_types.py` has a **field dimension** since Phase 37 — it inspects `ast.AnnAssign` on exported classes, so a `dict[str, Any]` field added by HARN-02 fails the gate, not just a return type |

---

## Sources

All findings are first-party, verified against the repository at HEAD (`37a83fe`, branch `main`, clean tree) on 2026-08-31. Confidence **HIGH** across the board — every load-bearing claim was produced by executing a tool or reading the exact file and line, not by inference from documentation.

| Claim | How verified |
|---|---|
| Census script exists, selftest passes | `uv run python scripts/literal_census_33.py --selftest` → `SELFTEST: PASS` |
| Census gate is stale substring | Read `scripts/literal_census_33.py:191-201`; compared against `main_matriz.py:116-156, 229-247` |
| Census script's API calls are not rotted | AST enumeration of `_core.py` function defs in both `matriz-client` and `iol-client`; grep of `def _request` signatures |
| NYQuist tooling fully wired | Executed `gsd-tools loop render-hooks verify:post --raw`, `query resolve-model gsd-nyquist-auditor --raw`, `find-phase 35`/`39`, `query init.phase-op 35`; `ls .claude/agents/` |
| VALIDATION.md draft state | Read `.planning/milestones/v1.7-phases/35-…/35-VALIDATION.md` frontmatter (`status: draft`, `nyquist_compliant: false`) |
| `Instrument`/`Segment` real wire shape | Parsed `.planning/verification/schemas/market-data-client/get-instruments.json` and `get-segments.json` (captured 2026-07-31) |
| Declared model shape | Read `packages/market-data-client/src/market_data_client/models.py:787-814` |
| Version-bump precedent | `packages/market-data-client/README.md:123-153` (`## Changelog` / `### v0.6.0` / migration table); `pyproject.toml:3`; `__init__.py:163`; `git log` commits `c05a159`, `a78eec3`, `50d1c0e`, `f1e1a3e`, merge `8e0013f` |
| `idempotent_by_title` exists | Read `verification/findings.py:597,617-665`; `ls verification/test_findings_dedupe_by_title.py` |
| 6 missing dedupe call sites | AST walk of all 5 `main_*.py` drivers, filtering `append_finding` calls whose `title` contains "drift" |
| Stale comment location | grep → `tools/check_surface_types.py:47,58` |
| Broken harness scope | `grep -c ""` on both files; backlog `HARN-VERIF-01` measured counts |
| mutation_gate remains remarkets-only | Read `verification/mutation_gate.py:70-73,130` |
| CI scope and gates | Read `.github/workflows/ci.yml:33-92,103-129,153-156`; `pyproject.toml:97` (mypy `files`), `:106` (`testpaths`), `:141-146` (import-linter) |
| Toolchain versions | `uv run ruff --version`, `mypy --version`, `pytest --version`, `uv --version`, `python -c "import sys;print(sys.version)"` |
| Decisions and precedents | `.planning/PROJECT.md` §Current Milestone (169-179), §Active requirements (285-292), §Constraints (332-338), §Key Decisions (340-378); `.planning/ROADMAP.md` §Backlog (57-106) |

No external/web sources were used — none were required, since nothing new is proposed. Provider availability at the time of research: `brave_search: false`, `firecrawl: false`, `exa_search: false`.

---
*Stack research for: backlog closeout on an existing Python client-library monorepo*
*Researched: 2026-08-31*
