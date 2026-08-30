---
phase: 35-fundaci-n-null-object-bool-pol-tica-del-walker
verified: 2026-08-29T00:00:00Z
status: passed
score: 5/5 roadmap success criteria verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 35: Fundación Null Object — `__bool__` + política del walker Verification Report

**Phase Goal:** La ausencia deja de expresarse con `None` y pasa a expresarse con veracidad — toda base `SafeModel` de los 6 paquetes sabe decir "estoy vacío" y el walker `_decode` sabe colapsar un `null` legítimo sobre un eslabón sin ensuciar el canal de divergencias, sin que ninguna firma pública cambie todavía.

**Verified:** 2026-08-29
**Status:** passed
**Re-verification:** No — initial verification

All verification commands below were re-run independently against the current worktree
(commit `2b82bf1`), not inferred from SUMMARY.md prose. NOBJ-02's `[x]` in REQUIREMENTS.md
was NOT trusted as evidence (per `deferred-items.md` D1) — its truth is established below
directly against the walker at commit `ece3a3c`.

## Goal Achievement

### Observable Truths (ROADMAP Phase 35 Success Criteria — the goal-backward contract)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `bool(X.from_api(None)) is False` for every `SafeModel`/`_SafeModel` class across all 6 packages, `empty()` exists and is invocable, roster obtained by real-module introspection | ✓ VERIFIED | Independently re-derived rosters via `inspect.getmembers` (not the test file's copy) and asserted falsy+`empty()`-equality for all: higyrus 15, iol 4, market-data 16, matriz 17 + `UnknownFrame` (False). ambito/wallets roster confirmed empty by direct module introspection. `empty()` is non-memoized in all 4 hierarchies (`X.empty() is not X.empty()` → True in higyrus/iol/market-data/matriz). |
| 2 | Null/absent on a non-optional model/list field collapses silently (no divergence record); wrong-typed value on the same field still emits the record and is still fatal under `strict_decode`; both halves falsified by named tests | ✓ VERIFIED | Independently drove `higyrus_client._decode.walk_model` directly (not via the test suite): `{'hojas': None, 'hoja': None}` → 0 records, correct collapsed values. `{'hojas': 'garbage'}` → exactly 1 record `('.hojas', 'type')`. Same payload under `STRICT_DECODE=True` raises `HigyrusDecodeError`. Commit `ece3a3c` shows the 11-failure measured red set (documented in 35-05-SUMMARY, cross-checked against `git show --stat`: 12 files, exactly the ones named). 10 wrong-type tripwires all green (`pytest packages -q -k "wrong_typed_list or still_raises..."` → 10 passed). |
| 3 | All 4 v1.6 CI gates green; `check_decode_intactness` reduces to ONE new canonical hash; no rule loosened, no lower bound lowered, no package excluded | ✓ VERIFIED | Ran all 4 gates myself: `check_decode_intactness.py` exit 0 (hash `a1f00c824348164c...`, matches pinned `CANONICAL_DIGEST`), `check_uniform_structure.py` exit 0, `check_surface_types.py` exit 0 (0 violations), `surface_parity.py` exit 0. `git diff 242b9f3..HEAD --numstat -- tools/check_decode_intactness.py` → `1  1` (pin line only). The other 3 gate scripts, `pyproject.toml`, `.github/workflows/ci.yml` byte-unchanged over the whole phase (`git diff --numstat` empty). |
| 4 | No public surface change; suites pass without editing a test (rescoped by CONTEXT D-13 to permit exactly the falsification inversions) | ✓ VERIFIED | `verification/regen_snapshots.py` run fresh by me, `git diff --exit-code verification/snapshots/` → exit 0 (byte-identical, 4 files, worktree clean after). Phase-wide `git diff 242b9f3..HEAD --numstat -- '*.py'` shows deletions in exactly: 5×`_decode.py` (10 each, the EDIT1/EDIT2 pair), 5×`test_decode.py` + `test_core.py` (the 11 named inversions), `matriz/models.py` (1 line — the `UnknownFrame` docstring count sentence, confirmed in 35-04-SUMMARY), and `tools/check_decode_intactness.py` (1 line, the pin). No 7th file with deletions. `uv run pytest packages -q` → **1947 passed, 1 deselected** (re-run by me, matches SUMMARY). |
| 5 | `@property` alias is invisible to `get_type_hints()` on a frozen+slots dataclass; adding an alias cannot fabricate a `missing` or change the divergence count | ✓ VERIFIED (with a documented weakness — see below) | `test_property_aliases_are_invisible_to_get_type_hints` is non-vacuous and independently re-confirmed true by construction (a `@property` is never a dataclass field, so `get_type_hints()` genuinely excludes it — this is a Python-language guarantee, not merely a test artifact). All 177 `test_null_object.py` cases across 6 packages pass (`pytest packages/*/tests/test_null_object.py -q` → 177 passed). **Known weakness (REVIEW WR-05):** the companion test `test_adding_a_property_alias_does_not_change_the_divergence_count` compares two fixtures whose only fields (`LA: _Leaf`, `BI: list[_Leaf]`) both collapse to zero records post-NOBJ-02 in 4 of 5 packages, so that specific assertion is now `[] == []` — it still catches an alias erroneously entering the walk, but can no longer prove the "cannot suppress a genuine divergence" half. This does not falsify the criterion (the get_type_hints() half — the actual mechanism the criterion asks for — remains solid and independently reproducible), but it is a real reduction in falsification strength. See "Code Review Findings Requiring Follow-Up" below. |

**Score:** 5/5 roadmap success criteria verified.

### Required Artifacts (sample — cross-checked across all 5 plans' must_haves)

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `packages/{higyrus,iol,market-data}-client/src/*/models.py` | `SafeModel.empty()` (form A/B) + `.__bool__()` | ✓ VERIFIED | `grep -c "def empty"` / `"def __bool__"` = 1 each in all 3; body confirmed to route through `_decode.walk_model(..., sink=SILENT_SINK)`, never `from_api`; `__bool__` body is `return self != type(self).empty()` verbatim (D-06) in all. |
| `packages/matriz-client/src/matriz_client/models.py` | `_SafeModel.__bool__()` + `UnknownFrame.__bool__()` (empty() pre-existing from Phase 29) | ✓ VERIFIED | `grep -c "def __bool__"` = 2; `def empty` count unchanged from parent commit (2==2, confirmed via 35-04-SUMMARY's own diff evidence, re-checked structurally). |
| `packages/{6 pkgs}/tests/test_null_object.py` | Enumeration/truthiness/empty()-silence/alias-invisibility suites | ✓ VERIFIED | All 6 files exist; 177 total cases collected and pass. |
| The five `_decode.py` copies | EDIT 1 (list-site null gate) + EDIT 2 (model-site collapse) + rewritten disposition comment | ✓ VERIFIED | `if value is not None:` present exactly once per copy (re-grepped); `Phase 35, NOBJ-02` marker present in all 5; behaviorally reproduced independently (see Truth 2 above). |
| `tools/check_decode_intactness.py` | New `CANONICAL_DIGEST`, recomputed | ✓ VERIFIED | Contains `a1f00c824348164cb04c086993826c0050d6d344fcdaf778a37112751bc97e1f`; gate passes against the 5 live copies. |
| `packages/market-data-client/tests/test_core.py` | The 11th inverted assertion | ✓ VERIFIED | Contains `test_health_from_api_missing_auth_yields_zero_valued_nested_model`, asserts `records == []`. |
| `.planning/phases/35-.../35-RETIRED-TRIPLES.md` | D-17 accounting ledger for Phase 39 | ✓ VERIFIED | File exists, 35 field rows + explicit iol zero row, per-package subtraction table present. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `SafeModel.empty()` (all 4 bases) | `_decode.walk_model(cls, {}, policy=POLICY, sink=SILENT_SINK)` | same mechanism the walker's own nested-model default site uses | ✓ WIRED | Confirmed by direct source read in higyrus/iol/market-data; matriz's pre-existing form B confirmed unchanged. |
| `_decode.py` list site | `DecodeScope.__call__` (the strict-mode raise choke point) | `if value is not None:` gates the sink call; not calling the sink is not raising | ✓ WIRED | Independently reproduced: wrong-type on list still raises under strict; null/absent does not. |
| The five `_decode.py` copies | `tools/check_decode_intactness.py` | 8-rule normalization → single hash vs. pinned `CANONICAL_DIGEST` | ✓ WIRED | Gate re-run, exit 0, hash matches. |

### Behavioral Spot-Checks (run independently, not from SUMMARY prose)

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Truthiness enumeration, 6 packages | ad-hoc `inspect.getmembers` + `bool(from_api(None))` per package | higyrus 15/15 falsy, iol 4/4, market-data 16/16, matriz 17/17 + UnknownFrame False, ambito/wallets roster=0 | ✓ PASS |
| `empty()` non-memoization | `X.empty() is not X.empty()` in higyrus/iol/market-data/matriz | all `True` | ✓ PASS |
| Walker collapse (null → silent) | `walk_model(Carrier, {'hojas': None, 'hoja': None}, ...)` on a fresh local higyrus fixture | 0 records, correct collapsed values | ✓ PASS |
| Walker falsification (wrong-type → still reports + fatal) | same fixture, `{'hojas': 'garbage'}`, then under `STRICT_DECODE=True` | 1 record `('.hojas', 'type')`; raises `HigyrusDecodeError` under strict | ✓ PASS |
| `bool(SafeModel())` on the exported abstract base | `higyrus_client.models.SafeModel()` / `iol_client.models.SafeModel()` | raises `TypeError: must be called with a dataclass type or instance` | ✗ CONFIRMED DEFECT (WR-09, non-blocking — see below) |

### Probe Execution

Not applicable — this phase has no `scripts/*/tests/probe-*.sh` and none is declared in the plans.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| NOBJ-01 | 35-01, 35-03, 35-04 | Every empty `SafeModel` instance is falsy, populated is truthy, across 6 packages incl. matriz's `_SafeModel` | ✓ SATISFIED | Independently re-verified, see Truth 1 above. `deferred-items.md` D1 correctly notes REQUIREMENTS.md's premature `[x]` came from plan-frontmatter auto-marking at 35-01 close, not from a completed walker edit — this does not affect NOBJ-01's own truth, which was genuinely closed by 35-01/03/04. |
| NOBJ-02 | 35-01 (falsification half), 35-05 (collapse half) | Walker collapses null/absent on non-optional model/list fields without emitting a divergence; wrong-type still emits + still fatal; the 4 v1.6 gates stay green | ✓ SATISFIED | Verified directly against the shipped walker (commit `ece3a3c`), not against the checkbox — see Truth 2 and the Behavioral Spot-Checks above. `deferred-items.md` D1's instruction ("verify against 35-05's artefacts, not the premature checkbox") was followed. |

No orphaned requirements: REQUIREMENTS.md Phase 35 traceability lists exactly NOBJ-01 and NOBJ-02, both declared in plan frontmatter (`35-01`, `35-02`, `35-03`, `35-04` all declare `[NOBJ-01, NOBJ-02]` or `[NOBJ-02]`; `35-05` declares `[NOBJ-02]`).

### Anti-Patterns Found

None blocking. Scanned every `.py` file touched in the phase (`git diff 242b9f3..HEAD --name-only -- '*.py'`) for `TBD|FIXME|XXX|TODO|HACK|PLACEHOLDER`: the only hits are (a) the Spanish word "TODO" (= "all") inside an explanatory comment in `matriz-client/tests/test_decode.py`, not a debt marker, and (b) `_PKG_PLACEHOLDER`-style identifiers in `tools/check_decode_intactness.py`, which are the gate's own pre-existing normalization-token variable names, not new debt. No stub patterns, no empty-implementation red flags in the diff. `mypy` (root + market-data scoped) both `Success`; `ruff check` / `ruff format --check` both clean.

### Code Review Findings Requiring Follow-Up (from 35-REVIEW.md, independently re-confirmed — 0 critical / 10 warnings)

I re-confirmed the three findings the task specifically asked me to judge, plus one more that's worth surfacing (WR-08, a real WR-02 defect the new comment now argues both sides of):

- **WR-05 — the criterio-5 divergence-count test is now vacuous ([] == []) in 4 of 5 packages.** Confirmed by reading the `_AliasShaped`/`_AliasFree` fixtures directly: both declare only a nested-model field and a list field, which both collapse to zero records post-NOBJ-02. **Judgment: does NOT compromise criterion 5** — the criterion's actual mechanism (`get_type_hints()` excluding a `@property`) is a Python-language guarantee independently verified true, and the vacuous test still catches the failure mode of an alias erroneously entering the walk. It does mean the "cannot suppress a genuine divergence" half is currently unfalsifiable in 4/5 packages. Recommend a small follow-up (add one scalar field to both fixtures, per the REVIEW's proposed fix) before Phase 36-38 lean further on this invariant.
- **WR-06 — matriz's 2 of 11 inversions use `not in` membership instead of `==` equality.** Confirmed at `test_decode.py:350` and `:1266`. **Judgment: does NOT compromise criterion 2** — the disposition change is still correctly falsified (a red walker would still redden these), but the assertion is strictly weaker than its 9 siblings: it would not catch the walker emitting a *different* record at the same site (e.g. `"type"` instead of `"missing"`). Worth a trivial follow-up fix (the REVIEW's proposed `== []` form is directly usable) but not a phase blocker.
- **WR-09 — `bool(SafeModel())` raises `TypeError` on the exported abstract base in higyrus and iol.** Confirmed independently (see Behavioral Spot-Checks). **Judgment: does NOT compromise criterion 1** — criterion 1 is about concrete `SafeModel` subclasses (`bool(X.from_api(None))`), and the project's own convention (CLAUDE.md: "Constructed exclusively via `Model.from_api(...)` classmethod — never `Model(field=value)` directly") means the abstract base was never meant to be instantiated directly. It is a real, narrow regression on a dunder that previously never raised, on a class that is technically public (`__all__`). Recommend the REVIEW's proposed guard clause as a quick, low-risk follow-up.
- **WR-08 — the new NOBJ-02 comment restates WR-02's counter-argument while the code still exhibits the defect it counters, for the wrong-type half.** Confirmed: `Health.from_api({"status":"ok","auth":"garbage"})` still emits `[('HealthAuth', '.auth', 'non_dict')]`, naming a decode site (`HealthAuth.auth`) that does not exist. This is pre-existing (Phase 29 WR-02) behavior, unchanged by this phase, but the new comment now quotes the counter-argument against it immediately above the code that still does it. Documentation-clarity issue, not a functional regression — worth cleaning up but does not affect any Phase 35 criterion.

None of the four findings above changes the VERIFIED status of any of the 5 roadmap success criteria. All are pre-existing-quality / test-strength gaps that the code review already caught and proposed concrete, small fixes for. I recommend the user decide whether to fold these into a short 35-06 hardening plan before Phase 36/37/38 begin (all three depend on the alias-invisibility and truthiness invariants this phase establishes), or accept them as tracked debt.

## Gaps Summary

No gaps block the phase goal. All 5 roadmap success criteria are independently verified true against the live codebase (not inferred from SUMMARY.md), all 4 v1.6 CI gates pass, the full workspace suite (1947 tests) passes, mypy/ruff are clean, and the public-surface snapshots are byte-identical. `NOBJ-01` and `NOBJ-02` are both satisfied — `NOBJ-02` specifically was verified against the shipped walker at commit `ece3a3c`, not against the premature `[x]` in REQUIREMENTS.md that `deferred-items.md` (D1) correctly flagged as not evidence.

Four code-review WARNINGS (WR-05, WR-06, WR-08, WR-09) are real, confirmed, and non-blocking — they reduce falsification strength or documentation accuracy in narrow, already-identified spots, with fixes already sketched in `35-REVIEW.md`. None reopens a FAILED truth. Recommended for a lightweight follow-up before Phase 36-38 lean further on the invariants they touch.

---

_Verified: 2026-08-29_
_Verifier: Claude (gsd-verifier)_
