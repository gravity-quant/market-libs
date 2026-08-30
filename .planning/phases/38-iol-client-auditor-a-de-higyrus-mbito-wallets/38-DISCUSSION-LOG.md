# Phase 38: `iol-client` + auditoría de higyrus/ámbito/wallets - Discussion Log (Assumptions Mode)

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-08-29
**Phase:** 38-iol-client-auditor-a-de-higyrus-mbito-wallets
**Mode:** assumptions
**Areas analyzed:** iol `puntas` shape + mirroring, test migration strategy, higyrus/ámbito/wallets
census format, README breaking-change documentation, gate coverage / CI ratchet

## Assumptions Presented

### (a) iol `puntas` Null Object shape + mirroring
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| `puntas` fields stay dataclass-REQUIRED, no dataclass default | Confident | `models.py:213,301` field ordering; dataclass `TypeError` reproduced; Phase 36 D-04 twin |
| Nothing to mirror in `client.py`/`aio.py` | Confident | `client.py:528,548,557,572` / `aio.py:547,563,569,580` share `_core.py` parsers |
| Zero new model classes → no `test_null_object.py` roster bump | Confident | roster floor `>= 4` at `:226`, iol ships exactly 4; `_perturb` dispatch unaffected |

### (b) Test migration strategy
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| 6 breaking assertions, 1 rename, 2 tautological | Confident | `test_models.py:209,229,235,248,412,441` (breaking), `:247` (rename), `:264,389` (tautological) |
| "No emite registro" tests need docstring rewrite, not just assertion change | Likely | `_decode.py:438-441` (old branch) vs `:447-495` (new branch); docstrings at `:201,437` cite old branch |
| Replacement idiom `== []` / `bool(...) is False` / `== Punta.empty()` | Likely | Phase 36 D-07 exact precedent (`36-CONTEXT.md:62-64`) |

### (c) Census format for higyrus/ámbito/wallets
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Phase-local artifact following `35-RETIRED-TRIPLES.md` shape, not the auto-generated findings ledgers | Likely | ledgers have fixed live-run schema between AUTO-GENERATED markers |
| Census enumerates full candidate population, not violations-only | Likely | measured: higyrus 15 classes/142 fields/0 violations; ámbito/wallets 0 classes |
| `dict[str, Any]` half already resolved via gate's existing exemptions | Confident | `check_surface_types.py` live run: "442 fields scanned, 24 exempted, 0 violations" |

### (d) SC-1 README requirement vs. Phase 40 deferral
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| No real conflict — breaking callout at introducing phase, version/tag wait for Phase 40 | Confident | `higyrus-client/README.md:131-137`, `market-data-client/README.md:7-33` (Phase 36) |
| Truthiness flip needs its own subsection with migration rows | Likely | asymmetric flip: `Cotizacion.puntas` no flip, `Titulo.puntas` `None→Punta.empty()` flip |

### (e) Gate coverage
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| No gate needs special-casing, but none enforces the new invariant either | Unclear | `check_surface_types.py` predicate (D-01b, Phase 37) bans only `dict[str, Any]`/`Any`, not `Model \| None` — vacuously green today |
| Phase 38 owes Phase 39 a retired-triples accounting update | Confident | `35-RETIRED-TRIPLES.md:190` names Phase 38 by name; line refs at `:137-144` drifted (`:154,242` → `:213,301`) |

## Corrections Made

No corrections to the evidence-backed (Confident/Likely) assumptions — user confirmed "Sí,
proceder" for the bulk of the analysis. Two genuinely open (Unclear / dual-precedent) items were
resolved via explicit operator decision rather than auto-selected:

### Gate ratchet (area e)
- **Options presented:** (1) Extend `check_surface_types.py`'s field predicate to ban Optional
  model/list fields too (+ RED fixture, mirrors Phase 37 D-01d) → SC-3 becomes a permanent CI
  ratchet. (2) Keep the grep as one-time evidence only; add an iol-local test pinning `puntas`
  non-Optional — cross-package invariant stays unguarded.
- **User choice:** Option 1 — Extend the gate. Recorded as D-11 in CONTEXT.md.

### README section format (area d)
- **Options presented:** (1) `## Unreleased — BREAKING` (Phase 36/v1.7 format, market-data-client
  precedent) — doesn't guess Phase 40's version number. (2) `### vX.Y.Z — sin publicar todavía`
  (higyrus/v1.6 format) — versioned but guesses the number Phase 40 will assign.
- **User choice:** Option 1 — `## Unreleased — BREAKING`. Recorded as D-10 in CONTEXT.md.

## External Research

None performed — the analyzer agent resolved every claim against committed code or live command
output (`check_surface_types.py`, `check_uniform_structure.py`, `check_decode_intactness.py`, the
source-plan closure grep, two `get_type_hints` introspection sweeps). No library-version or
ecosystem question arose.
