# Phase 35 — deferred items

Out-of-scope discoveries logged during execution. Not fixed by the plan that found them.

## D1 — `NOBJ-02` is already marked Complete in REQUIREMENTS.md, but its implementation leg has not run

- **Found during:** 35-02 (state update step), 2026-08-29
- **Observed:** `REQUIREMENTS.md:15` carries `- [x] **NOBJ-02**` and `REQUIREMENTS.md:66`
  reads `| NOBJ-02 | Phase 35 | Complete |`.
- **Why that is premature:** `NOBJ-02` is the walker disposition itself — "el walker
  `_decode` colapsa `null`/ausente sobre un campo modelo/lista no-opcional a instancia
  vacía/`[]` sin emitir divergencia". `_decode.py` has not been edited in any package
  (`tools/check_decode_intactness.py` still passes against the pre-Phase-35
  `CANONICAL_DIGEST`). The requirement is owned by five plans (35-01 through 35-05) and only
  **35-05** performs the edit that satisfies its text.
- **How it got there:** the requirement is listed in the frontmatter of every plan in the
  phase, so the first plan to finish (35-01) marked it complete through the standard
  `requirements mark-complete` state step.
- **Not fixed here, deliberately.** Flipping a requirement checkbox back mid-phase would
  fight 35-01's recorded state and confuse the orchestrator's progress accounting. 35-05
  re-marks it on completion in any case.
- **Action for the phase verifier:** do not treat the `[x]` as evidence. Verify `NOBJ-02`
  against the artefacts 35-05 produces — the five byte-identical `_decode.py` edits, the
  recomputed `CANONICAL_DIGEST`, and the 11 inverted assertions — exactly as ROADMAP Phase 35
  criterio 2 requires. A checkbox that runs ahead of its implementation is the same class of
  false-clean this milestone exists to eliminate.
