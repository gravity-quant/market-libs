# Architecture Research — v1.8 Cierre de deuda post-v1.7

**Domain:** Integration study for 4 backlog groups against the existing `market-libs` monorepo (no new packages, no new layers)
**Researched:** 2026-08-31
**HEAD verified at:** `e55398d` (`docs: start milestone v1.8 …`)
**Confidence:** HIGH (every path below opened, read, or executed at HEAD — not read off docs)

> **Scope note.** This is NOT a general architecture survey. The per-package
> `client.py`/`aio.py`/`_core.py`/`models.py` structure and the verification harness
> are established and unchanged. This document answers only: *where do LIVE-01/02,
> NYQ-01, SHAPE-01 and HARN-01..04 attach, what is new vs modified, and in what order.*
>
> **`/.planning/codebase/ARCHITECTURE.md` is stale** (`refreshed: 2026-05-27`, pre-v1.2:
> 5 packages, no `market_data_client`, claims `matriz_client` has no `aio.py`). It was
> read and deliberately not used as a source. Everything below is from the live tree.

---

## Standard Architecture

### System Overview — where the 4 groups attach

```
┌───────────────────────────────────────────────────────────────────────────────┐
│  PUBLISHED PACKAGE SOURCE  (semver-bearing — only SHAPE-01 + HARN-02 touch it) │
│                                                                                │
│   packages/market-data-client/src/market_data_client/                          │
│     ├── models.py      ← SHAPE-01 (Instrument:787, Segment:803)                │
│     │                     HARN-02 (FeedIngestor:~1307-, HealthFeed, Symbol:817)│
│     ├── _core.py       ← parsers only; shared by BOTH shells (no change needed)│
│     ├── client.py / aio.py  ← signatures stay `list[Instrument]` (no change)   │
│     └── README.md §Changelog ← version callout + migration table (v1.7 pattern)│
├───────────────────────────────────────────────────────────────────────────────┤
│  CI GATES  (tools/ + ci.yml — must stay green)                                 │
│   tools/check_decode_intactness.py   tools/check_uniform_structure.py          │
│   tools/check_surface_types.py  ← HARN-03/IN-01 stale comment (:47, :58)       │
│   tools/surface_parity.py                                                      │
│   .github/workflows/ci.yml  ← lint job: 4 gates + EXPLICIT 12-file             │
│                                verification/ allowlist ← HARN-03/IN-06, HARN-04│
├───────────────────────────────────────────────────────────────────────────────┤
│  VERIFICATION HARNESS  (repo-root, non-publishable — HARN-01/04, LIVE-01/02)   │
│   verification/findings.py::append_finding(idempotent_by_title=) ← HARN-01     │
│   verification/{divergences,mutation_gate,env_gate,cycle_report,safemodel_diff}│
│   verification/test_matriz_sweep_snapshot.py            ← HARN-04 (19F/19E)    │
│   verification/test_main_matriz_login_fail_uniformity.py← HARN-04              │
│   verification/test_finding_count_consistency.py        ← HARN-01 hazard pin   │
├───────────────────────────────────────────────────────────────────────────────┤
│  LIVE DRIVERS + SCRIPTS  (repo-root — LIVE-01/02)                              │
│   main_higyrus.py     ← LIVE-01: vendor-unreachable path ALREADY built (Ph.39) │
│   main_matriz.py      ← _VENUE_ALLOWLIST:139 (remarkets + api.bbsa.…)          │
│   main_market_data.py ← SHAPE-01 collateral: Segment probe at :1507            │
│   scripts/preflight_33.py       ← LIVE-01 measurement instrument               │
│   scripts/literal_census_33.py  ← LIVE-02; STILL substring-gated at :192 (!)   │
├───────────────────────────────────────────────────────────────────────────────┤
│  PLANNING ARTIFACTS  (NYQ-01 only — zero source footprint)                     │
│   .planning/milestones/v1.7-phases/{35..39}-*/  ← resolvable in place          │
│   .planning/milestones/v1.7-REQUIREMENTS.md    ← v1.7 REQ IDs live HERE        │
└───────────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities (only the pieces the 4 groups touch)

| Component | Owns | Verified state at HEAD |
|-----------|------|------------------------|
| `verification/findings.py` | Findings file lifecycle; `append_finding` with `fid`-idempotence and opt-in `idempotent_by_title` (`:597`, short-circuit at `:665`) | Present, working. Dedupe returns **before** the new block is written but **after** the caller already burned a `_next_fid()`. |
| `main_*.py::_write_or_check_schema` / `_write_schema_snapshot` | Write-once schema snapshot (DRIFT-01) or emit `SHAPE` drift finding (D-25, never overwrites) | 4 drivers have it, 5 drift call sites, **none** pass `idempotent_by_title=True`. |
| `tools/check_surface_types.py` | AST ratchet: zero `Any`/`dict[str, Any]` in exported surface, incl. field dimension (Phase 37) | Green. Live count `186 __all__ names, 336 definitions, 442 fields, 0 violations`. Docstring at `:47`/`:58` says `330` — stale. |
| `ci.yml` lint job | 4 cross-package gates **plus** an explicit 12-file `verification/` allowlist (Phase 36 WR-01 precedent) | Present at `ci.yml` lint step "driver locks…". |
| `market_data_client/_core.py` | `parse_instruments_response` (`:982`), `parse_segments_response` (`:1029`) — pure, single call site for both shells | Envelope-unwrap already FIXED (F-82/83/102/103). Field shape deliberately NOT fixed (docstring `:1043-1044` says so verbatim). |
| `main_matriz.py::_VENUE_ALLOWLIST` (`:139`) | Exact-hostname allowlist, the Phase-39 D-02 widening | `{"api.remarkets.primary.com.ar": "remarkets", "api.bbsa.matrizoms.com.ar": "bbsa"}` |

---

## Group-by-group integration points

### Group 1 — LIVE-01 / LIVE-02

#### LIVE-01 (higyrus DNS recheck) — **plumbing 100% built; this is a measurement, not a build**

`main_higyrus.py` already carries the entire vendor-unreachable path, landed in Phase 39:

| Element | Location |
|---|---|
| `_vendor_unreachable` / `_vendor_unreachable_reason` globals | `main_higyrus.py:236-237` |
| `_VENDOR_UNREACHABLE_SKIP_LINE` (`SKIPPED higyrus-client: vendor host unreachable (DNS) — LIVE-HIGY-42`) | `:245` |
| `_VENDOR_UNREACHABLE_DETAIL` / `_VENDOR_UNREACHABLE_EVIDENCE` | `:249`, `:254` |
| `except httpx.ConnectError` in sync/async login, ordered **before** `httpx.HTTPError` | `:669`, `:750` |
| Cheaper independent probe | `scripts/preflight_33.py` → one line `higyrus-client: AUTH OK` / `AUTH FAIL <ClassName>` |

**Where it plugs in:** run `uv run python scripts/preflight_33.py` (measures auth for all 4 credentialed
packages, one line each, never leaks credentials or URLs) and, if it resolves, `uv run python main_higyrus.py`
via `main_verify.py`. **No new script.** If DNS still fails, the deliverable is a re-measured
`SKIPPED` with the same named cause — an artifact, not code.

**One real code candidate, already named:** Phase 39 WR-02 — `httpx.ConnectTimeout` is **not** caught
alongside `ConnectError`, so a firewall-drop (rather than NXDOMAIN) would fall through to the
`httpx.HTTPError` arm and be misclassified as a finding rather than `SKIPPED`. Scope-limited by
decision and documented in the code itself. Fixing it is 2 lines × 2 sites (`:669`, `:750`) and is
the only sync/async-mirror obligation in this group.

#### LIVE-02 (matriz RESPONSE `Literal` census) — **the backlog's readiness claim is WRONG**

`ROADMAP.md:64` says *"`scripts/literal_census_33.py` ya tiene el gate remarkets-only listo para correr
contra el sandbox `bbsa` ahora desbloqueado."* Read at HEAD, `scripts/literal_census_33.py:192` is:

```python
if "remarkets" not in base:
    _skip("matriz-client", "base URL fuera de política (D-MATZ-33: …remarkets-only)")
```

This is the **pre-Phase-39 substring gate**. Against `api.bbsa.matrizoms.com.ar` it evaluates to
`True` → the script prints `SKIPPED` and emits zero requests. **LIVE-02 is blocked on porting the
Phase-39 exact-hostname allowlist into the census script.** That is the first task of this group, not
an afterthought — and it is also a security-relevant edit (the substring form would have admitted
`api.remarkets.primary.com.ar.attacker.example`, which is exactly why Phase 39 replaced it).

**Where the census writes:**

| Output | Destination | Committed? |
|---|---|---|
| Raw wire payloads | `.planning/verification/captures/` via `verification.capture.capture()` | **No** — gitignored (`.gitignore:51`), the only legal home for raw wire |
| Distinct-value sets (the census proper) | **stdout only**, one line per observed path: `matriz-client <endpoint> <path>: rows=N types=[…] distinct=[…]` | Operator pastes into the milestone census artifact |

**It does NOT touch `verification/findings.py` at all** — no `append_finding`, no fid allocation, no
findings-file mutation. The integration with `findings.py` the question asks about **does not exist and
should not be created**: the census is a vocabulary measurement, not a divergence stream. (D-08 in the
script's own docstring explains why the divergence stream *cannot* be the census mechanism:
`_decode.walk_field`'s `Literal` arm returns early with `literal_enforced=False` and never calls the sink.)

**Two collateral items ride LIVE-02**, both already scoped in the backlog:
- Correct `29-DLOCK-RESPONSE-LITERAL.md:140-142` (signed lock, so the signer corrects it) — it claims the
  divergence stream is the census mechanism; the shipped code says otherwise.
- `mutation_gate.py`'s `_SANDBOX_HOST` stays remarkets-only and is **deliberately untouched** — under bbsa
  it leaves order entry fail-closed with zero code change (Phase 39 T-39-02). Do not "fix" it.

---

### Group 2 — NYQ-01 (`/gsd-validate-phase` over archived phases 35-39)

**Answer to the question asked: no restore is needed. The archived dirs resolve in place.**
Executed at HEAD:

```
$ node .claude/gsd-core/bin/gsd-tools.cjs query init.phase-op 39
  "phase_found": true,
  "phase_dir": ".planning/milestones/v1.7-phases/39-verificaci-n-en-vivo-del-encadenamiento-profundo",
  "has_plans": true, "plan_count": 8, "has_verification": true,
```

`validate-phase.md` uses that `phase_dir` for everything: `VALIDATION_FILE=$(ls "${PHASE_DIR}"/*-VALIDATION.md)`
(`:41`), `SUMMARY_FILES` (`:42`), and the write target `${PHASE_DIR}/${PADDED_PHASE}-VALIDATION.md` (`:126`).
All five archived phase dirs contain both `*-VALIDATION.md` and `*-SUMMARY.md`, so all five land in
**State A (audit existing)** — not State B (reconstruct), not State C (exit).

Confirmed frontmatter at HEAD:

| Phase | `status` | `nyquist_compliant` |
|---|---|---|
| 35, 36, 37, 38, 39 | `draft` | `false` |
| 40 | `ready` | `true` |

**The one real blocker nobody has written down yet:** `init.phase-op` returns
`"requirements_path": ".planning/REQUIREMENTS.md"` — **that file does not exist at HEAD** (`.planning/`
contains no `REQUIREMENTS.md`; v1.7's was archived to `.planning/milestones/v1.7-REQUIREMENTS.md`). When
v1.8's `/gsd-new-milestone` creates a fresh root `REQUIREMENTS.md`, it will hold `LIVE-01`/`NYQ-01`/
`SHAPE-01`/`HARN-0x` — **not** the `NOBJ-*` IDs that phases 35-39 map their tasks to. The
`gsd-nyquist-auditor` must be pointed explicitly at `.planning/milestones/v1.7-REQUIREMENTS.md`, or its
requirement-to-task map (`validate-phase.md` §2b) resolves against the wrong roster and silently reports
false gaps.

**Source footprint:** normally zero — but §5 spawns `gsd-nyquist-auditor`, which *generates tests*, and §7
commits them (`git add {test_files}`). Any generated test that lands under `verification/` is **inert
unless added to the `ci.yml` explicit allowlist** — this is the exact defect Phase 36's code review found
(WR-01) and the reason that allowlist exists. Generated tests under `packages/<pkg>/tests/` run for free
via the 6×2 matrix.

| NYQ-01 file class | New / Modified |
|---|---|
| `.planning/milestones/v1.7-phases/{35..39}-*/{35..39}-VALIDATION.md` | Modified (State A: status + per-task map + `## Validation Audit {date}` trail) |
| Generated tests under `packages/*/tests/` | New (if gaps found) |
| Generated tests under `verification/` | New (if gaps found) — **plus** a `ci.yml` allowlist edit |

---

### Group 3 — SHAPE-01 (`Instrument` / `Segment` field shape, `market-data-client`)

**Confirmed present at HEAD** — the PROVISIONAL shapes were never fixed:

```python
# packages/market-data-client/src/market_data_client/models.py:787
class Instrument(SafeModel):
    symbol: str; marketId: str; segment: str; instrumentType: str; expired: bool

# :803
class Segment(SafeModel):
    marketSegmentId: str; marketId: str; description: str
```

Against the committed baselines (`.planning/verification/schemas/market-data-client/`, captured
2026-07-31 against `market-data-develop.bbsa.com.ar`):

| Model | Wire keys (measured) | Declared-not-on-wire | On-wire-not-declared |
|---|---|---|---|
| `Instrument` (`get-instruments.json` → `items[]`) | `active`(null) `currency` `days_to_maturity` `expired` `market_id` `maturity` `outright` `segment` `subscribed` `symbol` | `marketId`, `instrumentType` | `market_id` `currency` `days_to_maturity` `maturity` `outright` `subscribed` `active` |
| `Segment` (`get-segments.json` → `segments[]`) | `live_instruments` `segment` | `marketSegmentId` `marketId` `description` (**all three**) | `segment` `live_instruments` |

`Segment`'s sets are **disjoint** — every row from `get_segments()` today decodes to three empty strings.

**Where the fix touches — the answer to "client.py + aio.py?" is NO:**

| File | New/Mod | Why |
|---|---|---|
| `market_data_client/models.py` | **Modified** | The only site of the field declarations. |
| `market_data_client/_core.py` | **Unchanged** | `parse_instruments_response:982` / `parse_segments_response:1029` are `[Model.from_api(item) for item in rows]`. The envelope unwrap is already correct (F-82/83/102/103 = `FIXED`). Its docstring at `:1043-1044` explicitly records the field fix as deliberately deferred — update that prose. |
| `client.py` (`:543`,`:572`,`:940`,`:966`) / `aio.py` (`:545`,`:574`,`:968`,`:994`) | **Unchanged** | Signatures stay `list[Instrument]` / `list[Segment]`. **No sync/async mirroring obligation** — the CLAUDE.md dual-surface rule binds *logic* changes; this is a model-field change reached through one shared `_core.py` parser. |
| `tools/check_surface_types.py` | **Unchanged** | The fix introduces no `Any`/`dict[str, Any]`. Gate is green now (`0 violations`) and stays green. **Caveat:** `active` arrives `null` on the wire, so per D-NO-03 (leaf scalars terminate the chain) it should be `bool \| None`. The gate does not object to `\| None` on scalar leaves. |
| `main_market_data.py:1507-1508` | **Modified — load-bearing** | `sorted(s.marketSegmentId for s in seg_sync)`. Leaving this is a *verbatim repeat of Phase 37 CR-01*: a driver not updated after a shape change fabricates false-positive SHAPE findings on the next live run. `_emit_shape(sample, Instrument, …)` at `:984`/`:1349` is field-agnostic and needs no edit. |
| `verification/schemas/…/get-{instruments,segments}.json` | **Unchanged** | They record the *wire*, not the model. D-25 forbids overwrite. They remain the correct baselines. |

**Test fixtures that must move (6 files, measured):**

| File | Hits |
|---|---|
| `packages/market-data-client/tests/test_reference_client.py` | `:49` `instrumentType`, `:80`/`:87` `marketSegmentId` |
| `packages/market-data-client/tests/test_reference_async_client.py` | `:45`, `:76`, `:83` |
| `packages/market-data-client/tests/test_reference_models.py` | `:46` `inst.instrumentType == ""`, `:52` `seg.marketSegmentId == ""` |
| `packages/market-data-client/tests/test_reference_core.py` | `:186` |
| `packages/market-data-client/tests/test_reference_envelope_unwrap.py` | `:129` |
| `packages/market-data-client/tests/test_decode.py` | `:670-688` — **the trap.** The decode-walker suite uses `models.Segment`/`models.Instrument` as its *real-model* fixtures precisely because they have `marketId`/`marketSegmentId`. This is a decode-behaviour suite that will break for reasons unrelated to reference data. Either re-fixture on a stable model or re-key the payloads. |

`verification/test_matriz_sweep_snapshot.py:90` and `verification/snapshots/matriz-client-surface.txt:41` also
contain `marketSegmentId` — those are **matriz's** `Segment`, unrelated. Do not touch.

**Version disposition.** `market-data-client` is at `0.6.0` (`pyproject.toml:3`, `__init__.py:163`).
Removing `marketId`/`instrumentType`/`marketSegmentId`/`description` is **source-breaking** →
`0.7.0` under the established 0.x-minor-for-breaking convention (precedents: 0.5.0, 0.6.0). The changelog
lives in `packages/market-data-client/README.md` §`## Changelog` (`:123`) — there is **no `CHANGELOG.md`
file** in this package; follow the v0.6.0 pattern (breaking callout + before/after migration table).

**Confirming evidence is offline-only.** SHAPE-01 needs no live run: the wire is pinned in two committed
baselines and the findings file. A post-fix live confirmation would need Auth0 creds + VPN for
`market-data-develop.bbsa.com.ar`, which LIVE-01/02 do **not** cover. Plan for mocked regressions as the
proof (the v1.6/v1.7 in-cycle-fix pattern), and treat a live market-data sweep as optional upside.

---

### Group 4 — HARN-01..04

#### HARN-01 — dedupe schema-drift findings by title

`append_finding(..., idempotent_by_title: bool = False)` exists (`verification/findings.py:597`) and
short-circuits correctly at `:665-669` (scan all findings for an equal `title`, refresh ART block, return).
The 5 drift call sites that omit it:

| Driver | Function | Line | Title template |
|---|---|---|---|
| `main_iol.py` | `_write_or_check_schema` (`:1720`) | `:1760` | `f"Schema drift en {func_name}"` |
| `main_higyrus.py` | `_write_or_check_schema` (`:556`) | `:596` (+ a 2nd `append_finding` at `~:654`) | same |
| `main_matriz.py` | `_write_or_check_schema` (`:541`) | `:590` | same |
| `main_market_data.py` | `_write_schema_snapshot` (`:457`) | `:511` (drift) and `:495` (unreadable-baseline) | `f"schema drift en {client_function}"` / `f"baseline schema ilegible en …"` |
| `main_ambito_financiero.py` | — | — | no schema-snapshot path (0 sites) |

> Naming drift worth fixing while here: the backlog calls it `_write_or_check_schema` universally, but
> `main_market_data.py` names it `_write_schema_snapshot`. The 22-blocks-for-8-snapshots evidence in the
> backlog came from the market-data driver, i.e. from `_write_schema_snapshot`.

**The non-obvious coupling — this is the real design decision in HARN-01.** Every call site does
`fid = _next_fid()` **before** `append_finding`. With `idempotent_by_title=True`, a deduped call burns a
fid that never becomes a `### F-` block, producing fid gaps. `verification/test_finding_count_consistency.py`
pins exactly this property ("la cantidad de fids emitidos tiene que igualar la de bloques `### F-` nuevos")
and its module docstring **names `_write_or_check_schema` as sharing the hazard**. So HARN-01 is not a
one-kwarg change; it is either (a) move the `_next_fid()` call after the dedupe decision — which means the
dedupe check has to move out of `append_finding` or gain a probe API — or (b) update the consistency test's
invariant to tolerate deduped no-ops. **Decide this before implementing**; it is the difference between
5 one-line edits and a small harness refactor.

**Files:** 4 drivers **modified**, `verification/findings.py` possibly **modified** (probe API),
`verification/test_finding_count_consistency.py` **modified**, plus **new** regression test(s). Zero
package source, zero version impact.

#### HARN-02 — type the 5 remaining `extra` keys (`market-data-client`)

Evidence is **offline and complete** in `.planning/verification/market-data-client-findings.md`:

| Finding | Field | Observed type |
|---|---|---|
| F-67 / F-87 | `HealthFeed.symbols_never_delivered` | `int` |
| F-68 | `FeedIngestor.ingestor.last_error_age_seconds` | `int` |
| F-69 | `FeedIngestor.ingestor.last_error_at` | `str` |
| F-70 | `FeedIngestor.ingestor.subscription` | `dict` — full 14-key sub-shape captured verbatim at `:910` |
| F-109 / F-140 | `Symbol.note` | `str` (via `/symbols/{symbol_id}`) |

Note the committed `get-health-feed.json` baseline (2026-07-31) predates these and does **not** contain
them — D-25 write-once means the baseline was never refreshed. The authoritative shape for this work is
the findings file `Actual` blob at `:910`, not the schema snapshot.

`subscription` is the interesting one: `{chunk_size, chunks, confirm_seconds, delivered_count,
forced_reconnects, last_reconnect_reason, quarantined_count, quarantined_symbols: [str], requested, sent,
smd_rejections, smd_resends, smd_unattributed, unconfirmed_count, unconfirmed_symbols: []}`. Under
`check_surface_types.py` it **cannot** be `dict[str, Any]`; it needs a new `FeedSubscription(SafeModel)`
with `__bool__`/`empty()` per the v1.7 Null Object policy, `quarantined_symbols: list[str] = []` (link,
not leaf), and a judgement call on `unconfirmed_symbols` (observed `[]`, member type unmeasured).

**Files:** `market_data_client/models.py` **modified** (+1 new class), package tests **new/modified**.
Additive (new fields with defaults on `from_api`-constructed frozen dataclasses) → **rides SHAPE-01's
0.7.0**, does not justify its own release.

#### HARN-03 — cosmetics (`IN-01`, `IN-05`, `IN-06`)

| Item | State at HEAD | Verdict |
|---|---|---|
| `IN-01` stale gate comment | `tools/check_surface_types.py:47` and `:58` both say `330 definitions scanned`. Live run: **`336 definitions, 442 fields, 186 __all__ names, 0 violations`**. | **Still open.** Two docstring lines. |
| `IN-05` `matriz_client.__version__` | `packages/matriz-client/src/matriz_client/__init__.py:186` → `__version__ = "0.3.0"` | **ALREADY CLOSED** — added by the Phase 40 release. The backlog entry is stale; retire it rather than schedule it. |
| `IN-06` `verification/test_public_surface.py` outside the CI lint list | `grep test_public_surface .github/workflows/ci.yml` → no match | **Still open.** One line appended to the explicit allowlist in the "driver locks" step. |

#### HARN-04 — `verification/` matriz harness (repair vs. accept)

**Re-measured at HEAD, not read from `33-BASELINE.md`:**

```
$ uv run pytest -q verification/test_matriz_sweep_snapshot.py \
                   verification/test_main_matriz_login_fail_uniformity.py
19 failed, 3 passed, 19 errors in 0.13s
```

Identical to the Phase-33 baseline (19F/19E). Root cause reconfirmed, unchanged:

- `verification/test_matriz_sweep_snapshot.py:273-274` — `probe_fn = getattr(main_matriz, probe_name); result, _payload = probe_fn()`
- `verification/test_main_matriz_login_fail_uniformity.py:53`, `:78` — `main_matriz.probe_login_sync()`
- HEAD signatures: `def probe_login_sync(client: Client)` (`main_matriz.py:775`), `def probe_get_segments(client: Client)` (`:847`) — the post-REFAC-05 form.

The visible pytest failure is `AssertionError: The following responses are mocked but not requested`
(pytest-httpx teardown), which is why each case counts twice; the `TypeError` is the underlying cause and
mypy states it plainly: `error: Missing positional argument "client" in call to "probe_login_sync" [call-arg]`.

**mypy gap re-measured:** `uv run mypy verification` → **44 errors in 9 files** (backlog says 43 in 8 —
minor drift, more rot has accumulated). `verification/` is outside mypy's `files` list
(`pyproject.toml:97`, 6 package `src` dirs only) and outside the pre-commit `^packages/.*/src/` scope.

**Correction to the STATE.md premise in the milestone brief.** *"`ci.yml` passes an explicit path that
bypasses `testpaths`, so `verification/` never ran in CI"* is **no longer true as stated.** Post-Phase-36/37/39,
the `lint` job runs an explicit **12-file** allowlist from `verification/`:

```
test_main_market_data_deep_chain · test_safemodel_diff_null_object_links ·
test_main_matriz_risk_envelope_keys · test_safemodel_diff_mapping_recursion ·
test_main_verify_classification · test_main_matriz_skip_line_shape ·
test_main_higyrus_skip_line_shape · test_run_evidence · test_main_iol_deep_chain ·
test_main_higyrus_deep_chain · test_main_matriz_deep_chain · test_cycle_closure_phase33
```

The accurate statement is: **`pytest verification/` as a directory still never runs in CI** — deliberately,
because of exactly the 19F/19E red HARN-04 is about — and the two broken matriz files are **not** on the
allowlist, so they remain invisible-by-construction. The ci.yml comment says so in prose: *"Es una lista
EXPLÍCITA, no `pytest verification/`: ese directorio arrastra fallas pre-existentes … backlog `HARN-VERIF-01`."*

**If repaired:** the fix is 2 **test** files (thread a `Client` through, or drive via `main()`); **no
driver source changes**. Then append both to the ci.yml allowlist — the same edit as `IN-06`, so bundle
HARN-03 and HARN-04. **Standing hazard (from the backlog, still valid):** these two files are the *canary*
for the `probe_context` refactor of plans 33-02/33-03 because they invoke probes directly rather than via
`main()`. Repairing them by simply passing a `Client` must not silently drop that property.

---

## Data Flow — what a v1.8 change actually touches

### SHAPE-01 propagation (one model edit, five downstream surfaces)

```
models.py:{787,803}  ← the ONLY declaration site
   │
   ├─► _core.py parsers (:982,:1029)   … no code change; docstring prose only
   │      └─► client.py + aio.py       … no change (signatures unchanged)
   ├─► packages/*/tests × 6 files      … fixture payloads + assertions
   ├─► main_market_data.py:1507        … Segment probe — MUST update (Ph.37 CR-01 lesson)
   ├─► tools/check_surface_types.py    … re-run; expect 0 violations, counts shift
   └─► README.md §Changelog + pyproject:3 + __init__:163  … 0.6.0 → 0.7.0
```

### HARN-01 propagation (one kwarg, one invariant)

```
main_*.py drift site: fid = _next_fid()   ← the burn
   └─► append_finding(..., idempotent_by_title=True)
          ├─ title match → early return, fid orphaned
          └─► verification/test_finding_count_consistency.py  ← invariant breaks here
```

---

## Interactions between groups (the question's core)

| Pair | Interaction | Consequence for sequencing |
|---|---|---|
| **SHAPE-01 ↔ HARN-02** | Both edit `market_data_client/models.py`; SHAPE-01 is breaking (0.7.0), HARN-02 is additive | **Bundle into ONE release.** Doing them separately either burns 0.7.0 + 0.8.0 or leaves HARN-02 unreleased. Land HARN-02 before cutting the version. |
| **HARN-01 → LIVE-01/LIVE-02** | Any live driver run appends findings; without dedupe a re-run inflates the file (measured: 22 blocks for 8 snapshots in a 2-pass run) | **HARN-01 before the live runs**, so the v1.8 census artifacts are clean the first time. |
| **LIVE-02 blocked-by-itself** | `literal_census_33.py:192` still substring-gated → SKIPs against bbsa | The allowlist port is task 1 of LIVE-02; nothing else in LIVE-02 can run first. |
| **NYQ-01 → HARN-03/IN-06** | Both may append to the `ci.yml` verification allowlist | Run NYQ-01 first, then do one consolidated `ci.yml` edit in HARN-03. |
| **HARN-04 → HARN-03/IN-06** | If matriz's 2 files are repaired they should join the same allowlist | Bundle HARN-04's decision with HARN-03's ci.yml edit. |
| **NYQ-01 ↔ SHAPE-01** | Phase 36/38 Nyquist tests are about Null Object invariants, not `Instrument`/`Segment` — low collision risk. But an auditor-generated test written *after* SHAPE-01 audits a shape the archived phase never claimed. | Prefer NYQ-01 **before** SHAPE-01: phases 35-39 are frozen history, and auditing them against the tree they shipped against is more faithful. |
| **NYQ-01 → nothing** | Does not block or unblock any other group | Fully parallelizable if capacity allows. |
| **LIVE-01 ↔ everything** | Outcome is a measurement; a `SKIPPED` result is a valid deliverable | Never a blocker. Do it early to get the answer, since a resolving DNS would open a whole higyrus census that changes v1.8's shape. |

**Answer to "does SHAPE-01's version bump affect HARN sequencing?" — Yes, for HARN-02 only.**
HARN-01, HARN-03 and HARN-04 touch **zero published package source** (harness, drivers, `tools/` docstrings,
`ci.yml`) and carry **no version impact whatsoever**; they can land before, during or after the release with
no coordination. HARN-02 is the exception: it edits `models.py` and must be inside the 0.7.0 cut.

---

## Suggested build order

```
Wave A (parallel, zero coupling, cheap answers first)
  A1  LIVE-01   run preflight_33.py → measure higyrus DNS. Outcome = artifact.
                (optional, 2 lines × 2 sites: catch ConnectTimeout — Ph.39 WR-02)
  A2  NYQ-01    /gsd-validate-phase 35..39 in place. MUST point the auditor at
                .planning/milestones/v1.7-REQUIREMENTS.md, not the (absent) root file.
  A3  HARN-01   decide the _next_fid()-vs-dedupe question, then wire 5 call sites
                + reconcile test_finding_count_consistency.py.

Wave B (needs A3 landed so the run writes clean findings)
  B1  LIVE-02   (a) port _VENUE_ALLOWLIST into literal_census_33.py:192  ← blocking
                (b) run census against bbsa; paste stdout into the census artifact
                (c) correct 29-DLOCK-RESPONSE-LITERAL.md:140-142 (signer)

Wave C (single market-data-client release — HARN-02 must be inside it)
  C1  SHAPE-01  models.py:787/803 → wire shape; `active` → bool | None (D-NO-03)
  C2  SHAPE-01  update main_market_data.py:1507 + the 6 test files (incl. the
                test_decode.py re-fixturing trap) + _core.py docstring prose
  C3  HARN-02   5 extra keys + new FeedSubscription(SafeModel) Null Object
  C4  release   0.6.0 → 0.7.0: pyproject:3, __init__:163, README §Changelog
                (breaking callout + migration table, v0.6.0 pattern), uv.lock,
                tag market-data-client-v0.7.0 behind the established double human gate

Wave D (CI hygiene last — one consolidated ci.yml edit)
  D1  HARN-04   decide: repair the 2 matriz test files, or write the accepted-debt doc
  D2  HARN-03   IN-01 docstring 330→336; IN-06 + (if D1=repair) the 2 matriz files
                appended to the ci.yml verification allowlist — plus any test files
                NYQ-01 generated under verification/. RETIRE IN-05 (already closed).
```

**Why not SHAPE-01 first?** It is the only group that ends in an irreversible public release. Everything
that could change its content (HARN-02's fields, the shape of the test-fixture churn) should be known
before the tag. Everything cheap and reversible goes first.

---

## Anti-Patterns to avoid in v1.8

### Anti-Pattern 1: shipping SHAPE-01 without updating `main_market_data.py`
**What people do:** change `models.py`, run the package tests green, move on.
**Why it's wrong:** `main_market_data.py:1507` reads `s.marketSegmentId`. This is a byte-for-byte repeat of
Phase 37 CR-01, where `main_matriz.py` was left stale after the strict-unwrap and fabricated false-positive
SHAPE findings on the *next* live run — i.e. the harness manufacturing the exact class of silent divergence
the project exists to eliminate.
**Do this instead:** treat the driver as a first-class consumer of the model surface. Grep the 5 drivers for
every renamed field before closing the plan.

### Anti-Pattern 2: adding `idempotent_by_title=True` and calling HARN-01 done
**What people do:** five one-line kwarg additions.
**Why it's wrong:** the fid is already burned by `_next_fid()` at every call site. You get silent fid gaps and
you break (or vacuously satisfy) `test_finding_count_consistency.py`, whose docstring explicitly names this
call path as sharing the hazard.
**Do this instead:** decide the allocator ordering first, and make the consistency test *detect* the new
behaviour rather than tolerate it.

### Anti-Pattern 3: trusting `ROADMAP.md:64` that the census script is ready
**What people do:** run `literal_census_33.py` against bbsa and report `SKIPPED` as a vendor problem.
**Why it's wrong:** `:192` is the old substring gate. The SKIP is manufactured by the script, not by the venue.
**Do this instead:** port `_VENUE_ALLOWLIST` from `main_matriz.py:139` first, and prove non-vacuity with
`--selftest` plus a measured non-empty `distinct=[…]` line.

### Anti-Pattern 4: restoring the archived phase dirs for NYQ-01
**What people do:** copy `.planning/milestones/v1.7-phases/*` back to `.planning/phases/`.
**Why it's wrong:** `init.phase-op` already resolves archived dirs (`phase_found: true`, measured). Restoring
creates two copies of five `VALIDATION.md` files and guarantees divergence.
**Do this instead:** run `/gsd-validate-phase 35..39` unchanged; it writes back into the archive.

### Anti-Pattern 5: "fixing" `mutation_gate.py`'s remarkets-only `_SANDBOX_HOST` during LIVE-02
**What people do:** notice the census now runs against bbsa and align the mutation gate for consistency.
**Why it's wrong:** the asymmetry is the *point* (Phase 39 T-39-02) — under bbsa, order entry stays
fail-closed with zero code change. Aligning it opens matriz order entry against a non-remarkets venue.
**Do this instead:** leave it. Document the asymmetry if it reads as an inconsistency.

---

## Integration Points

### External services (live-run dependencies)

| Service | Group | Gate | Status at HEAD |
|---|---|---|---|
| Higyrus (`HIGYRUS_BASE_URL`) | LIVE-01 | `env_gate.require_env` + `ConnectError` → SKIPPED path | DNS unresolved since Phase 33; re-probe is the deliverable |
| Primary/matriz `api.bbsa.matrizoms.com.ar` | LIVE-02 | `_VENUE_ALLOWLIST` exact-hostname (driver: yes; **census script: not yet**) | Unblocked for the driver, blocked for the census script |
| `market-data-develop.bbsa.com.ar` | SHAPE-01 (optional confirm) | Auth0 client-credentials + VPN/allowlist | Creds/VPN not available in-repo; SHAPE-01 proof is mocked regressions |

### Internal boundaries touched

| Boundary | Communication | Notes |
|---|---|---|
| `models.py` ↔ `_core.py` parsers | Direct import, `Model.from_api(item)` | SHAPE-01 crosses this without changing the parser |
| `_core.py` ↔ `client.py`/`aio.py` | import-linter `forbidden` contract (both directions blocked) | Unchanged; no new imports needed by any group |
| drivers ↔ `verification/findings.py` | `append_finding(...)` + `_next_fid()` per driver | HARN-01's whole surface |
| `verification/` ↔ CI | **explicit 12-file allowlist** in the `ci.yml` lint job, not `testpaths` | HARN-03/IN-06, HARN-04, NYQ-01-generated tests all land here |
| `tools/*.py` ↔ CI | 4 steps in the `lint` job | All 4 must stay green; only HARN-03 touches one (a docstring) |

---

## Confidence & gaps

| Claim | Confidence | Basis |
|---|---|---|
| Archived phase dirs resolve for `/gsd-validate-phase` | **HIGH** | `init.phase-op 39` executed; `phase_found: true` |
| Root `.planning/REQUIREMENTS.md` absent → NYQ-01 requirement-map hazard | **HIGH** | `ls` returned `No such file or directory` |
| `literal_census_33.py` still substring-gated | **HIGH** | Line `:192` read verbatim |
| SHAPE-01 needs no `client.py`/`aio.py` edit | **HIGH** | Parsers read at `_core.py:982/1029`; shells only re-export |
| HARN-01 fid-allocator coupling | **HIGH** | `findings.py:665` short-circuit + `test_finding_count_consistency.py` docstring |
| HARN-04 red is unchanged (19F/19E) | **HIGH** | pytest executed at HEAD |
| `IN-05` already closed | **HIGH** | `matriz_client/__init__.py:186` |
| `verification/` partially runs in CI now | **HIGH** | `ci.yml` lint job, 12-file list |
| HARN-02 `unconfirmed_symbols` member type | **LOW** | Observed `[]` only; needs a live capture or an explicit `list[str]` assumption |
| Whether a market-data live confirm is reachable in v1.8 | **LOW** | Depends on Auth0 creds + VPN, outside LIVE-01/02 scope |

**Not investigated (out of the question's scope):** the D39-01..04 in-code debt items, `TYP-MD-EXTRA-33`'s
interaction with a future `Health` shape change, and whether Phase 40's release tooling needs any change
for a 5th coordinated release.

## Sources

- Live tree at `e55398d`: `packages/market-data-client/src/market_data_client/{models,_core,client,aio}.py`,
  `main_{higyrus,matriz,market_data}.py`, `scripts/{preflight,literal_census}_33.py`,
  `verification/findings.py`, `verification/test_finding_count_consistency.py`,
  `tools/check_surface_types.py`, `.github/workflows/ci.yml`, `pyproject.toml`
- Executed: `gsd-tools query init.phase-op 39`; `uv run python tools/check_surface_types.py`;
  `uv run pytest -q verification/test_matriz_sweep_snapshot.py verification/test_main_matriz_login_fail_uniformity.py`;
  `uv run mypy verification`
- Committed evidence: `.planning/verification/schemas/market-data-client/get-{instruments,segments,health-feed}.json`,
  `.planning/verification/market-data-client-findings.md` (F-67..F-70, F-82/83, F-102/103, F-109, F-140)
- Planning: `.planning/PROJECT.md`, `.planning/ROADMAP.md § Backlog`, `.planning/STATE.md`,
  `.claude/gsd-core/workflows/validate-phase.md`
- **Rejected as stale:** `.planning/codebase/ARCHITECTURE.md` (`refreshed: 2026-05-27`)

---
*Architecture research for: v1.8 backlog closeout (LIVE-01/02, NYQ-01, SHAPE-01, HARN-01..04)*
*Researched: 2026-08-31 against HEAD `e55398d`*
