# Phase 15: Driver Migration × 4 (REFAC-05) - Discussion Log (Assumptions Mode)

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-06-24
**Phase:** 15-driver-migration-4-refac-05
**Mode:** assumptions
**Areas analyzed:** Migration mechanics, INT-01 `_state` reads, AST-guard test, probe-name/finding-title stability, LOC-drop reachability

## Assumptions Presented

### Migration Mechanics — How Each Driver Gets Its Client
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| One sync `Client()` in `main()` + one `AsyncClient()` in `_async_main()`, threaded into every probe as a parameter | Confident | `main_ambito_financiero.py:131,219,301`; `main_iol.py:219,336`; `main_matriz.py:453`; async batched into one `asyncio.run` |
| sync `Client` and async `AsyncClient` are SEPARATE instances (gate "1 sync + 1 async" accommodates split) | Confident | `await aio.aclose()` at `main_ambito_financiero.py:678`, `main_matriz.py:2046`; matriz `aio.py:136,710` |

### INT-01 `_state` Read Migration
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Every `_get_default()._state.<attr>` → `client._state.<attr>`, 1:1 mechanical; counts ámbito ~8+2 docstring, iol 17, higyrus ~19, matriz 6 | Confident | grep enumeration; write-site `main_iol.py:1289` |

### AST-Guard Test Shape and Location
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| `test_main_<pkg>_uses_single_client_instance` in `verification/`, modeled on `test_main_drivers_bare_except.py`; counts constructors, ≤2; `with_options` not counted | Likely | `verification/test_main_drivers_bare_except.py:17-51` (only AST-walker in repo); `client.py:264` |

### Probe-Name / Finding-Title Stability
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Title stability auto-preserved if migration changes only client-access, never `title=`/`fid=` literals; verify via static diff scoped to title/fid | Likely | `verification/findings.py:192,595` content-addressed dedupe; `_DETAIL_HEADER_RE` |

### LOC-Drop Target Reachability
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| -30% library LOC NOT closeable by driver migration alone (shims stay, Phase 16 dropped); criterion #5 is measurement/attestation | Unclear | shims STAY locked decision; ROADMAP line 161-168 Phase 16 DROPPED; current LOC iol 1511, matriz client.py 922 |

## Corrections Made

No assumptions were corrected — all confirmed via "Yes, proceed". Three open gray areas were
resolved by user selection (all recommended options):

### LOC criterion #5
- **Question:** How should Phase 15 treat the -30% LOC target it can't physically reach?
- **User choice:** Attestation / measure-only — record current vs baseline, document residual,
  confirm 907-test baseline; closure deferred to v1.3; shims STAY. → D-08
- **Rejected:** "Physically hit -30% now" (would violate shims-STAY / break external consumers);
  "Drop criterion #5 from Phase 15".

### Stability gate verification
- **Question:** How to verify probe-name/finding-title stability (criterion #2)?
- **User choice:** Static `git diff baseline..HEAD` scoped to title/fid lines, no live re-run. → D-07
- **Rejected:** "Full live re-run + full diff" (false-fails on nondeterministic live data;
  full live re-verification is Phase 17 anyway).

### Ergonomics scope
- **Question:** Adopt Phase 13 `with_options()`/`from_env()` during migration, or minimal?
- **User choice:** Minimal construction only — bare `Client()`/`AsyncClient()`, tight mechanical
  refactor. → D-10
- **Rejected:** "Adopt with_options/from_env too" (larger diff, not the phase objective).

## External Research

None performed — pure internal refactor; analyzer flagged no research gaps. The single open
measurement item (exact v1.0 baseline LOC anchor for the -30% delta) is internal historical
data to be recovered by the planner from a git tag / milestone archive (D-09), not external
research.
