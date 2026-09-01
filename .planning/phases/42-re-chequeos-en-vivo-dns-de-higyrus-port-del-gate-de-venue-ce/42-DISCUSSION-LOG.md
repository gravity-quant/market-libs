# Phase 42: Re-chequeos en vivo — Discussion Log (Assumptions Mode)

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-08-31
**Phase:** 42-re-chequeos-en-vivo-dns-de-higyrus-port-del-gate-de-venue-ce
**Mode:** assumptions
**Areas analyzed:** Venue gate port, iol scope creep, higyrus DNS re-check, market-data-client fresh wire read

## Assumptions Presented

### Venue gate port
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Import `main_matriz._VENUE_ALLOWLIST`/`._venue_token` directly, not duplicate-and-pin | Confident | `main_matriz.py` has zero top-level side effects outside `__main__` guard; 8 files already import it at test scope; `pythonpath = ["."]` |
| Blocking-human checkpoint = fidelity-of-port confirmation, not fresh bbsa authorization | Likely | `39-01-PLAN.md:87-141` checkpoint precedent; bbsa already authorized system-wide (D-02) |
| Falsification test mirrors `test_main_matriz_skip_line_shape.py:24-40` | Confident | existing test already exercises the exact spoofing cases needed |

### iol scope creep
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Phase 42 live run calls `census_matriz()` only, not unmodified `main()` | Likely | live IOL creds present; DT-07 already closed (`STATE.md:405`); LIVE-02 names only matriz fields |

### higyrus DNS re-check
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Run full `main_higyrus.py` driver, not `preflight_33.py` | Likely | only the driver persists a fresh `captured_at` via `write_run_evidence()`; preflight prints but doesn't persist |
| Rename `LIVE-HIGY-33` → `LIVE-HIGY-42` if still SKIPPED | Likely | criterion 2 literally requires "destino renombrado"; naming convention embeds phase-of-origin |

### market-data-client fresh wire read
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Use `verification.capture.capture(...)` at existing raw-JSON points, not `_write_schema_snapshot` | Likely | `_write_schema_snapshot` is write-once/no-overwrite (D-25); baselines confirmed dated 2026-07-31 via git log |
| Timestamp mechanism (envelope vs. SUMMARY citation) left open | Unclear (explicitly flagged, not resolved) | `capture()` doesn't self-timestamp — genuinely underdetermined by the codebase |

## Corrections Made

No corrections — all assumptions confirmed as presented ("Yes, proceed").

## External Research

None performed — deep codebase analysis (gsd-assumptions-analyzer, 55 tool uses) determined every open question resolves against files already in the repository; no library/ecosystem research gap existed.
