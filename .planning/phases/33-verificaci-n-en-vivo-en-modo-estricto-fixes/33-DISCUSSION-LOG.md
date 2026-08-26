# Phase 33: Verificación en vivo en modo estricto + fixes - Discussion Log (Assumptions Mode)

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-08-26
**Phase:** 33-verificaci-n-en-vivo-en-modo-estricto-fixes
**Mode:** assumptions
**Areas analyzed:** Divergence handler architecture, Strict-mode execution model and driver
survivability, Literal closure evidence, Gate vacuity/census scope/credential availability

## Assumptions Presented

### Divergence handler architecture (`verification/divergences.py`)

| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Handler is a `logging.Handler` per package logger, mapping the 6-key `extra` to `append_finding(class_="SHAPE", idempotent_by_title=True, ...)` | Confident | `29-AGGREGATION-CONTRACT.md` Lock 10 (signed spec); `verification/findings.py` FINDING_CLASSES already includes SHAPE |
| `endpoint`/`surface` reach the handler via a driver-set contextvar reusing `_ENDPOINT_TEMPLATES`/`probe_<func>_<surface>`, never by adding keys to the frozen 6-key `_decode.py` record | Likely | `_RECORD_KEYS` frozen + intactness-gated across 5 copies; `_ENDPOINT_TEMPLATES` exists in 3/5 drivers already |
| `main_market_data.py` needs a new `_ENDPOINT_TEMPLATES` map from scratch | Confident | grep shows only `_ENDPOINT_OPTIONAL` (unrelated) in that driver |

### Strict-mode execution model and driver survivability

| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Strict mode alone can't produce the full census — needs two-pass (observable census + strict proof-of-raise) | Likely | `DecodeScope.__call__` raises on first fatal divergence per response; S-2 predicts 9 fabricated fields, strict reports 1 |
| `strict_decode=True` alone kills the driver — `<Pkg>DecodeError` is a sibling of `<Pkg>APIError`, uncaught everywhere today | Confident | Verified exception hierarchy in all 5 packages' `exceptions.py`; `_RESIDUAL_PROBE_EXCEPTIONS` is builtins-only |
| No blanket `except Exception` allowed in `main_matriz.py`/`main_higyrus.py` | Confident | `verification/test_main_drivers_bare_except.py` AST gate parametrized over exactly those two drivers |
| Existing hand-rolled `HigyrusDecodeError` catch (health probe) becomes redundant, should be deleted not replicated | Likely | Would produce duplicate findings for the same divergence, defeating `idempotent_by_title` |

### Literal closure evidence (criterion 3)

| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Walker emits no record for out-of-set Literal with correct runtime type — divergence stream alone can't produce the Literal census | Confident | `policy.literal_enforced=False` in all 5 copies short-circuits before `sink()` call |
| Matriz's 7 RESPONSE fields with pre-existing Literal aliases resolve via "confirm unenforced + record observed values", never widen/enforce | Confident | `29-DLOCK-RESPONSE-LITERAL.md` explicitly forbids closure this milestone |
| iol `mercado`/`plazo` resolve to `str` permanent, documented decision — no evidence of accepted value set exists | Likely | Drivers only ever send fixed defaults `"bcba"`/`"t2"`; `types.py` deliberately empty |

### Gate vacuity, census scope, credential availability (criteria 4-5)

| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| `verify_cycle_closure` PASS is vacuous for OPEN-status findings — only CONFIRMED/FIXED count | Confident | `verification/cycle_report.py` status filter; same trap as Phase 23 market-data |
| `ambito-financiero-client` is a structural no-op under strict mode (zero divergences by construction) | Confident | Zero model classes, zero walker calls in the package |
| Live credentialed runs available for iol/higyrus/matriz/market-data (`.env` present); market-data no longer needs Phase-23 operator-paste workaround; credential validity itself unverifiable from this environment | Likely | `.env` file existence confirmed via `ls`; contents unreadable per environment permissions |
| iol schema-snapshot corruption risk (30-CONTEXT D-07) already closed — `to_dict()` confined to parity probe only | Confident | `main_iol.py` snapshot sites consume raw wire via `_capture_raw_wire`, unchanged since Phase 30 |

## Corrections Made

No corrections — all 14 assumptions confirmed as presented ("Yes, proceed").

## Auto-Resolved

Not applicable — `--auto` was not used.

## External Research

None performed — the analyzer agent found every open question resolvable against in-repo
evidence; the only unverifiable fact (`.env` file contents) is a permissions constraint, not a
research gap.
