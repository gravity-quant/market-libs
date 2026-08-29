---
phase: 38-iol-client-auditor-a-de-higyrus-mbito-wallets
verified: 2026-08-29T21:53:38Z
status: human_needed
score: 14/14 must-haves verified
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Open `.planning/phases/38-iol-client-auditor-a-de-higyrus-mbito-wallets/38-CENSUS.md` and read every table row top to bottom."
    expected: "Every row in both tables has a non-empty disposition cell and a non-empty evidence cell. The three packages are all represented — higyrus with real per-field and per-class rows, ambito and wallets with explicit zero-by-enumeration sub-headings rather than empty tables. The wallets section states the stub condition (no domain function in `__all__`, Phase 29 decoder exemption, 10 tests that exercise plumbing only). The SC-3 section shows both commands and their literal output rather than a claim about them. The 10-vs-11 discrepancy against CONTEXT D-11 is named, not silently absorbed."
    why_human: "SC-2's 'zero rows without disposition' and SC-4's 'no vacuous green' are documentation-completeness contracts. A grep can confirm the phrases are present; only a reader can confirm the dispositions are real rather than filler. Deferred from checkpoint:human-verify to end-of-phase per `workflow.human_verify_mode = end-of-phase` (harvested from 38-04-PLAN.md's `<human-check>` block)."
---

# Phase 38: `iol-client` + auditoría de higyrus/ámbito/wallets — Verification Report

**Phase Goal:** Los cuatro paquetes restantes quedan sin eslabones `None` en sus cadenas —
`titulo.puntas.precioCompra` es siempre válido — y la limpieza de los tres casi-limpios queda
**medida campo por campo**, no supuesta.
**Verified:** 2026-08-29T21:53:38Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

Note on the verifier's own independent read of `38-CENSUS.md` (see below): I opened the file
in full and cross-checked its numeric claims against the source with an independent AST scan
(not transcribed from RESEARCH/CONTEXT). Every number I recomputed matched the census exactly
(142 fields, 15 field-carrying classes, 10 link fields, 0 optional-bearing fields, 0 mapping
fields, per-class field counts for all 15 classes). This satisfies the harvested human-check's
`<expected>` on its technical merits; it is still surfaced below as `human_needed` because the
plan explicitly deferred it as a documentation-completeness judgment call under
`workflow.human_verify_mode = end-of-phase`, and the framework routes such harvested items to
human confirmation regardless of the verifier's own read.

### Observable Truths

| # | Truth (ROADMAP SC / plan must-have) | Status | Evidence |
|---|---|---|---|
| 1 | SC-1: `Cotizacion.puntas` is `list[Punta]`, `Titulo.puntas` is a `Punta` Null Object; `titulo.puntas.precioCompra` / `cotizacion.puntas[0].precioCompra` pass `mypy --strict` and never raise on absent/`null`/populated `puntas`; mirrored sync/async; snapshot regenerated; breakage recorded in README | VERIFIED | `models.py:235` (`puntas: list[Punta]`, no default), `:334` (`puntas: Punta`, no default); `mypy packages/iol-client` → `Success: no issues found in 30 source files`; empirically ran `Titulo.from_api({})`/`{"puntas": None}` → `puntas.precioCompra == 0.0`, no raise; `Cotizacion.from_api({})`/`{"puntas": None}`/`{"puntas": []}` → `puntas == []`; `grep -rn puntas client.py aio.py` → 0 hits (delegates to shared `models.py`, no duplication needed); `surface_parity.py` 18 passed; snapshot lines 11/21 show `puntas: 'list[Punta]'` / `puntas: 'Punta'` |
| 2 | Wrong-typed `puntas` still emits a divergence record and still raises under `strict_decode` — only null/absent is silent | VERIFIED | Empirically built a full valid payload with `puntas: 7`: `Cotizacion.from_api(...)` under `STRICT_DECODE.set(True)` raised `IOLDecodeError: decode divergence in Cotizacion.puntas: declared list, observed int`; `Titulo` equivalent raised `... Punta.puntas: declared Punta, observed int` |
| 3 | iol-client still declares exactly 4 `SafeModel` subclasses; `test_null_object.py` carries zero logic changes | VERIFIED | `git diff cf79e65..HEAD -- packages/iol-client/tests/test_null_object.py` → 5 insertions/4 deletions, all inside one docstring paragraph; the `>= 4` roster-floor assertion and `_perturb` logic untouched |
| 4 | SC-2: higyrus/ámbito/wallets audit published as a census with a disposition on every row; zero rows without a disposition | VERIFIED | `.planning/phases/38-.../38-CENSUS.md`, 426 lines; `grep -cE '\|\s*\|'` (empty-cell check) → 0; independently re-derived higyrus's population with a standalone `ast` scan: 142 total fields / 15 field-carrying classes / 10 link fields / 0 optional-bearing / 0 mapping fields — matches every number in the census exactly, including all 15 per-class field counts |
| 5 | SC-2 continued: the census enumerates the full candidate population, not only violations (0-violation packages don't get 3 empty tables) | VERIFIED | Census tables A/B enumerate all 142 higyrus fields (11 link/collection rows + 16 per-class scalar-aggregate rows) and 21 public-return rows across both surfaces, not just the `0 violations` count |
| 6 | SC-2 continued: `ambito-financiero-client` and `wallets-client` reported as absent by enumeration, not as clean; wallets carries its stub condition | VERIFIED | Census "Enumerated zeros" section: `grep -c '^class '` → 0 for both `models.py` files (confirmed independently); wallets qualification states no domain function in `__all__` (`__init__.py:22-28`, verified: 4 exceptions + `configure`, 0 domain fns), Phase 29 decoder exemption path cited, 10 tests exercise plumbing only |
| 7 | SC-3: closing grep over `packages/*/src/*/models.py` returns only scalar leaves / `Literal` aliases across the 6 packages, reported as an executed command + its verbatim output | VERIFIED | Independently ran `grep -nE ": *[A-Z][A-Za-z]* *\\| *None" packages/matriz-client/src/matriz_client/models.py` → exactly 10 lines (532,552,553,561,607,619,660,661,662,669); confirmed all 8 base names (`MarketId`,`SegmentId`,`CFICode`,`Currency`,`OrderType`,`Side`,`TimeInForce`,`OrderStatus`) are `Literal` aliases in `types.py`, not `ClassDef`s; 0 hits in iol/higyrus/ambito/wallets |
| 8 | SC-3 continued: no public function return exposes `dict[str, Any]` / `list[dict[str, Any]]` outside `_legacy`/`_request` internals | VERIFIED | Census "public-return half" table + "out of the gate's candidate set" table: the only untyped-mapping returns are the six module-level `_request` shims, all absent from every `__all__` (confirmed via AST export scan cited in census); `tools/check_surface_types.py` → `0 violations` |
| 9 | SC-4: the four packages' suites are green with the 4 v1.6 gates active | VERIFIED | `pytest packages/iol-client -q` → `293 passed`; `packages/higyrus-client -q` → `289 passed`; `packages/ambito-financiero-client -q` → `208 passed, 1 deselected`; `packages/wallets-client -q` → `10 passed`; `tools/check_surface_types.py` exit 0 (`442 fields scanned`, `0 violations`); `tools/check_decode_intactness.py` exit 0; `tools/check_uniform_structure.py` exit 0; `pytest packages/*/tests/test_surface_parity.py -q` → `18 passed` |
| 10 | Ratchet (D-11/38-02): an exported field annotated `Model \| None` or `list[Model] \| None` reddens `tools/check_surface_types.py`; `Literal`-alias and `list[Any] \| None` fields stay green; the gate is stdlib-`ast` only; 0 violations with non-vacuous scan | VERIFIED | `pytest packages/iol-client/tests/test_surface_types_red.py -q` → 16 passed (incl. `test_an_optional_model_field_is_caught`, `test_a_quoted_list_model_element_is_caught`, `test_an_optional_literal_alias_field_is_spared`, `test_an_optional_list_of_any_field_is_spared`); `grep -n "^import\|^from" tools/check_surface_types.py` → only `__future__`, `ast`, `sys`, `collections.abc`, `dataclasses`, `pathlib`; gate reports `442 fields scanned`, `0 violations` |
| 11 | Code-review finding WR-01 (quoted-forward-reference gap in D-11's `list[...]` arm) is fixed, not just documented | VERIFIED | `tools/check_surface_types.py:870-880` re-parses a quoted `ast.Constant` list element via `ast.parse(elem.value, mode="eval").body` before testing membership, matching the sibling mapping predicate's convention; regression test `test_a_quoted_list_model_element_is_caught` present and passing (commit `b2b06ff`) |
| 12 | README breaking-change callout (D-10/38-03): consumer can read exactly what stops working, incl. the truthiness-asymmetry consequence; headed `## Unreleased — BREAKING` with no version number assumed | VERIFIED | `packages/iol-client/README.md:5` `## Unreleased — BREAKING`, anchors on `iol-client-v0.3.0` (tag confirmed to exist via `git tag -l`); names the asymmetry explicitly (`Cotizacion.puntas`: falsy→falsy, no branch changes; `Titulo.puntas`: falsy→falsy but no longer `None`, an `is None` check stops firing silently); `pyproject.toml`/`uv.lock` untouched (`version = "0.3.0"`, matches the tag, confirming no premature bump) |
| 13 | `35-RETIRED-TRIPLES.md` ledger correction + Phase-38 addendum (D-12/38-03): no stale source-line references survive; Phase 39 can read 2 field rows added / 0 triples retired | VERIFIED | `## Phase 38 addendum` section present, cites `iol_client/models.py:235`/`:334` (confirmed against current source), states 2 rows added / 0 triples retired with the branch-level reasoning (`Union` early-return pre-38 vs. NOBJ-02 collapse arms post-38, same zero-emission observable); cross-references `38-CENSUS.md` |
| 14 | `38-CENSUS.md` documentation-completeness (harvested `<human-check>`, deferred to end-of-phase) | ⚠️ ROUTED TO HUMAN — verifier's own read found no defect | See Human Verification section below. Verifier independently re-derived every higyrus number in the census via AST and found exact agreement; no empty disposition/evidence cells found by grep. |

**Score:** 14/14 truths verified on their technical merits (item 14 additionally routed to human confirmation per deferred human-check protocol)

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `packages/iol-client/src/iol_client/models.py` | `Cotizacion.puntas: list[Punta]`, `Titulo.puntas: Punta`, both non-Optional, no dataclass default | ✓ VERIFIED | Lines 235, 334 confirmed; `mypy --strict` clean |
| `packages/iol-client/tests/test_models.py` | 7 migrated assertions + renamed test | ✓ VERIFIED | `293 passed` (incl. 1 new WR-01 fix test relative to plan's baseline of 292) |
| `packages/iol-client/tests/test_null_object.py` | Zero logic changes, docstring correction only | ✓ VERIFIED | Diff is 5 ins / 4 del inside one docstring paragraph |
| `verification/snapshots/iol-client-surface.txt` | Regenerated, 2-line diff limited to `puntas` token | ✓ VERIFIED | Lines 11/21 show the two new annotations; rest of file unchanged |
| `tools/check_surface_types.py` | Widened D-11 predicate, stdlib-ast only | ✓ VERIFIED | 3 new functions, WR-01 fix present, 0 violations, 442 fields scanned |
| `packages/iol-client/tests/test_surface_types_red.py` | RED/spared fixtures for D-11 | ✓ VERIFIED | 16 passed incl. WR-01 regression test |
| `packages/iol-client/README.md` | `## Unreleased — BREAKING` callout | ✓ VERIFIED | Present at line 5, 2-row migration table, asymmetry prose |
| `.planning/phases/35-.../35-RETIRED-TRIPLES.md` | Corrected refs + Phase 38 addendum | ✓ VERIFIED | Addendum present, refs verified against current source |
| `.planning/phases/38-.../38-CENSUS.md` | Field-by-field census, ≥80 lines, zero rows without disposition | ✓ VERIFIED | 426 lines, 0 empty cells, numbers independently re-derived and matched |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `models.py` `puntas` annotations | `_decode.py` NOBJ-02 collapse arms | frozen walker collapse behavior, no dataclass default | ✓ WIRED | Runtime test: absent/`null`/`[]` all collapse to `[]`/`Punta.empty()` with zero divergence records; wrong-typed raises under `strict_decode` |
| `verification/snapshots/iol-client-surface.txt` | `models.py` | `regen_snapshots.py` transcription | ✓ WIRED | Snapshot content matches current `models.py` signatures exactly |
| `tools/check_surface_types.py::scan_surface_types` | `_adjudicate_field` / `_field_annotation_is_optional_model` | threaded `class_names` parameter | ✓ WIRED | Gate run confirms `0 violations` with the widened predicate active; 10-line matriz `Literal` grep confirms no over-reddening |
| `packages/iol-client/tests/test_surface_types_red.py` | `tools/check_surface_types.py` | in-process import against synthetic tree | ✓ WIRED | 16 passed, including the two new D-11 fixtures and the WR-01 regression |
| `38-CENSUS.md` | `35-RETIRED-TRIPLES.md` ## Phase 38 addendum | cross-reference for retired-triples accounting | ✓ WIRED | Both files reference each other; addendum content matches what the census cites |
| `packages/iol-client/README.md` | `iol-client-v0.3.0` git tag | anchor for the "Unreleased" comparison | ✓ WIRED | Tag confirmed to exist (`git tag -l`); `pyproject.toml` version unchanged, matching the anchor |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| `titulo.puntas.precioCompra` never raises, on absent/`null`/populated payloads | Ran `Titulo.from_api({})`, `{"puntas": None}` in-process | `0.0`, `0.0`, no exception | ✓ PASS |
| `quote.puntas` collapses to `[]` on absent/`null`/`[]` | Ran `Cotizacion.from_api(...)` variants in-process | `[]` in all three cases | ✓ PASS |
| Wrong-typed `puntas` raises under `strict_decode` and names the field in the error | Built a full valid payload with `puntas: 7`, set `STRICT_DECODE`, called `from_api` | `IOLDecodeError` naming `Cotizacion.puntas` / `Punta.puntas` with `declared X, observed int` | ✓ PASS |
| D-11 gate reddens an optional model link, including the quoted-list WR-01 case | `pytest packages/iol-client/tests/test_surface_types_red.py -q` | `16 passed` | ✓ PASS |
| The census's higyrus population count is not asserted, it is reproducible | Independent stdlib-`ast` scan of `higyrus_client/models.py` | `142` total fields / `15` classes / `10` links / `0` optional / `0` mapping — exact match to census | ✓ PASS |
| SC-3 optional-leaf grep returns exactly 10 matriz lines | `grep -nE ": *[A-Z][A-Za-z]* *\| *None" packages/matriz-client/src/matriz_client/models.py` | 10 lines, matching census verbatim | ✓ PASS |
| Full workspace test suite: failures are pre-existing/out-of-scope, not phase 38 regressions | `pytest -q` (partial run to 99%, then `pytest verification/test_matriz_sweep_snapshot.py` + the other 2 named files directly) | `21 failed / 19 errors` total (matched exactly: dot-pattern F/E count = 21F/19E); root causes independently confirmed as (a) `probe_get_account_report() missing 1 required positional argument: 'client'` — a `main_matriz.py` signature bug, and (b) `FileNotFoundError` for `.planning/phases/33-.../33-CENSUS.md`, which no longer exists because Phase-33 artifacts were archived to `.planning/milestones/v1.6-phases/` during the v1.6→v1.7 milestone transition | ✓ PASS (confirms pre-existing/out-of-scope claim) |
| `main_matriz.py` / `packages/matriz-client/` untouched by Phase 38 | `git log -1 -- main_matriz.py` / `git log -1 -- packages/matriz-client/` | Both last touched by Phase 37 commits (`1c9a5bc`, `ca8b759`), not any Phase 38 commit | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|---|---|---|---|---|
| NOBJ-IOL-01 | 38-01, 38-03 | `Cotizacion.puntas`/`Titulo.puntas` Null Object retype, mirrored sync/async, README breakage disclosure | ✓ SATISFIED | See truths 1-3, 12-13 above |
| NOBJ-AUD-01 | 38-02, 38-04 | higyrus/ámbito/wallets audited field-by-field, ratchet gate widened | ✓ SATISFIED | See truths 4-11, 14 above |

No orphaned requirements: `REQUIREMENTS.md` traceability table maps exactly these two IDs to Phase 38, and both appear in a plan's `requirements:` frontmatter.

### Anti-Patterns Found

None. Scanned all 9 files touched by this phase's commits (`8930b5f..cf01930`) for `TBD|FIXME|XXX|TODO|HACK|PLACEHOLDER` and prose stub markers (`placeholder|coming soon|not yet implemented|not available`) — zero matches. `git diff --name-only` confirms the diff is scoped to exactly the files each plan declared (`packages/iol-client/{README.md,src/iol_client/models.py,tests/test_models.py,tests/test_null_object.py,tests/test_surface_types_red.py}`, `tools/check_surface_types.py`, `verification/snapshots/iol-client-surface.txt` — the `35-RETIRED-TRIPLES.md` and `38-CENSUS.md` planning artifacts are outside this glob but were separately reviewed above). Code review (`38-REVIEW.md`) found one Warning (WR-01), which was fixed in commit `b2b06ff` with a regression test, confirmed present and passing above.

### Human Verification Required

### 1. `38-CENSUS.md` completeness read

**Test:** Open `.planning/phases/38-iol-client-auditor-a-de-higyrus-mbito-wallets/38-CENSUS.md` and read every table row top to bottom.
**Expected:** Every row in both tables has a non-empty disposition cell and a non-empty evidence cell. The three packages are all represented — higyrus with real per-field and per-class rows, ambito and wallets with explicit zero-by-enumeration sub-headings rather than empty tables. The wallets section states the stub condition (no domain function in `__all__`, Phase 29 decoder exemption, 10 tests that exercise plumbing only). The SC-3 section shows both commands and their literal output rather than a claim about them. The 10-vs-11 discrepancy against CONTEXT D-11 is named, not silently absorbed.
**Why human:** SC-2's "zero rows without disposition" and SC-4's "no vacuous green" are documentation-completeness contracts. A grep can confirm the phrases are present; only a reader can confirm the dispositions are real rather than filler. This item was deliberately deferred by the planner from `checkpoint:human-verify` to end-of-phase (`workflow.human_verify_mode = end-of-phase`) and is harvested here per that protocol.

**Verifier's note:** I performed this exact read myself as part of goal-backward verification (see "Goal Achievement" preamble above) and independently re-derived the higyrus numbers via a standalone AST scan — every figure matched exactly, and no empty cells were found. I am not aware of any defect in this artifact. It is still listed here because the phase's own plan explicitly routed this class of judgment to a human checkpoint rather than to automated verification, and per the verification protocol harvested human-check items are always surfaced for human confirmation regardless of the verifier's own read.

### Gaps Summary

No gaps found. All 14 must-haves (roadmap Success Criteria 1-4 plus the four plans' own must-haves, including the code-review fix WR-01) are verified against the actual codebase — not merely against SUMMARY.md claims. Every numeric claim in `38-CENSUS.md` that was spot-checked was independently reproduced from source, not transcribed. The one item routed to `human_needed` is a documentation-completeness judgment call the phase's own plan deliberately deferred to end-of-phase human review; it is not a defect.

---

_Verified: 2026-08-29T21:53:38Z_
_Verifier: Claude (gsd-verifier)_
