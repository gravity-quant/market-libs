# Phase 27: Verificación en vivo segura + fixes - Discussion Log (Assumptions Mode)

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-08-01
**Phase:** 27-verificaci-n-en-vivo-segura-fixes
**Mode:** assumptions
**Areas analyzed:** Driver mutation opt-in + develop host gate; Test identifiers + cleanup guarantees; Scope of in-cycle fixes; Findings/snapshot/cycle-closure plumbing
**Calibration tier:** standard (no USER-PROFILE.md, no `preferences.vendor_philosophy`)

## Assumptions Presented

### A. Driver mutation opt-in + develop host gate

| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Do NOT reuse `verification/mutation_gate.py::mutating_allowed()` verbatim; add a market-data-specific env-var + exact-hostname gate | Likely | `verification/mutation_gate.py:39` (`_SANDBOX_HOST` hardcoded to remarkets), `:53-59` (hard-imports `matriz_client`, validates matriz's `_base_url` → second leg vacuous for market-data) |
| Pass the gate result into the **existing single** `Client(mutating_allowed=...)` ctor; never a second client | Likely | `client.py:126-157` (`__init__` is the only per-instance route), `client.py:716` (`configure()` is module-level), `verification/test_main_market_data_uses_single_client_instance.py:53` (`1 <= ctor_sites <= 2`) |
| Gate-off → probe-level colon-less `SKIPPED (mutating, guard off)`, driver continues | Confident | `main_verify.py:42` (classifies on `^SKIPPED \S.*:`), `:75` (documents the carve-out), `verification/mutation_gate.py:45` |
| Preserve Phase-23 D-09: no creds / wrong host → SKIPPED, never FAILED; post-processing inside each probe's `try` | Confident | `main_market_data.py:328`, `:394`, `:567`, `:954-963`, `:987-994`; `verification/test_main_market_data_postprocess_guarded.py` |

### B. Test identifiers + cleanup guarantees

| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Symbols revert is `PATCH active=false` — no delete exists | Confident | `_core.py:401`/`:419`/`:436` are the only symbols builders; live OpenAPI declares no DELETE under `/symbols`; `.planning/future-plans/market_data_mutations.md:92` prescribes this cycle (DM-06 at `:60`) |
| Calendar config exercised preview-only; `PUT`/`DELETE /calendar/config` not run live | Likely → **operator-confirmed** | `client.py:620` (`delete_calendar_config` resets to server defaults, does not restore); `REQUIREMENTS.md:52`; ROADMAP criterion 2 |
| Holidays get the full create→verify→revert cycle on a far-future ISO date | Confident | `client.py:677` (`delete_holiday` exists); spec `day` param is `format: date`; Phase-26 D-18 charset guard does not interfere |
| Cleanup via per-probe `try/finally`; a cleanup failure is itself an emitted finding | Likely | `main_market_data.py:940-942`, `:995-997` use bare `contextlib.suppress(Exception)` — would orphan develop state with no record |

### C. Scope of in-cycle fixes

| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| `symbol_id` is an **integer**, not a string — the carried WR-05 percent-encoding item is **dissolved** | Confident (resolved by live re-fetch) | Live OpenAPI: `PATCH /symbols/{symbol_id}` param `{"type":"integer"}`; client types it `str` at `_core.py:437`, `client.py:567`, `aio.py:578` |
| The real problem is obtaining that integer id — `Symbol` has no `id` field | Confident | `models.py:436-448` (`Symbol` PROVISIONAL: `symbol`/`marketId`/`active`); `get-symbols.json` baseline captured `schema: []` |
| `parse_symbols_response` is wrongly reused by all three mutations (spec: mutation responses are `object`, not array) | Confident (resolved by live re-fetch) | `_core.py:877-890`; routed from `client.py:554`/`:565`/`:576`; live OpenAPI declares all 8 mutation responses `object` + `additionalProperties:true`; `GET /symbols` genuinely `{"type":"array"}` |
| `parse_calendar_response` / `CalendarDay` fixed in this phase (Phase-26 D-16 handoff) | Confident | `_core.py:893-907` iterates as list; live OpenAPI declares `GET /calendar` as `object`; `.planning/verification/schemas/market-data-client/get-calendar.json` envelope `{config, coverage, days[], market}`; real items are `{day, closed, open_time, close_time, description}` |
| Correcting `CalendarDay` counts as non-breaking minor | Unclear | `REQUIREMENTS.md:28` requires a non-breaking bump in Phase 28; rationale = the broken parser means no consumer ever read a populated `CalendarDay` |
| WR-01 `parse_latest_response` already closed — verify only | Confident | `_core.py:796-830` unwraps `items`; quick task `260731-t9o` |

### D. Findings / snapshot / cycle-closure plumbing

| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| fid allocator must be offset, or every mutation `append_finding` must pass `idempotent_by_title=True` | Confident | `main_market_data.py:99-107` resets `_fid_counter=0`; `market-data-client-findings.md:15-50` holds `F-01`…`F-36`, none `OPEN`; `verification/findings.py:610` short-circuits non-OPEN fids; `:531` default `False` |
| Mutation payloads trip the write-once DRIFT-01 baselines → must be excluded or curated | Confident | `main_market_data.py:201-206` (write-once), `:227-241` (SHAPE OPEN finding, never overwrites), `:484` (`get_symbols(active=False)`); baseline `get-symbols.json` is `schema: []` |
| `verify_cycle_closure` must be wired in; each fix's finding needs a resolvable `Regression:` bullet | Confident | `main_market_data.py:48-56` never imports it (contrast `main_matriz.py:76`); `verification/cycle_report.py:123-176` (path must resolve and contain `def <test>(`); closure returns `(True,[])` vacuously if the file is absent |

### E. Idempotency revalidation (DM-03)

| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Revalidate empirically (double-POST → read → clean), never infer from HTTP semantics or spec text | Confident | DM-03; STATE.md Blockers/Concerns (v1.5 / Phase 27 risk) |
| If reality contradicts DM-03, the flag changes and gets a dispatch-level regression test | Confident | Phase-26 D-15 (first non-idempotent dispatch test); `tests/test_transport.py` `monkeypatch` sleep pattern; `_transport.py`/`_atransport.py` falsy-`idempotent` short-circuit |

## Corrections Made

No corrections — the user selected "Yes, proceed"; all assumptions confirmed as presented.

Two open items were resolved by direct operator decision rather than correction:

### B. Develop safety (DM-06 operator authorization)
- **Question:** What is safe to touch on develop's calendar config, given `DELETE /calendar/config` resets to server defaults and cannot serve as cleanup for a `PUT`?
- **Operator decision:** **Preview-only, no persisting PUT.** Live-verify `POST /calendar/config/preview` only; `PUT`/`DELETE /calendar/config` stay covered by mocked tests, with an EXPECTED finding recording that live `PUT` coverage is operator-gated.
- **Recorded as:** D-06.

### C. Symbol id acquisition
- **Question:** `symbol_id` is an integer per the live spec but `Symbol` has no `id` field, so the create→verify→revert cycle cannot learn the id it must PATCH.
- **Operator decision:** **Discover live, then fix in-cycle.** Probe the real `POST /symbols` 201 body and `GET /symbols` items to locate the id, then add the field to `Symbol` and retype `symbol_id: int` across `_core`/`client`/`aio` as an in-cycle fix with mocked regression tests — rather than retyping up front on spec authority alone.
- **Recorded as:** D-10.

## External Research

The analyzer flagged 5 research topics. Four are inherently live-server or operator
questions — i.e. the phase's own deliverable — and were left for execution. One was
resolvable offline and was resolved by re-fetching the live spec.

**Source:** `https://market-data-develop.bbsa.com.ar/api/openapi.json`, re-fetched
2026-08-01 (30,218 bytes; reachable from this machine, not vendored in the repo).

- **`symbol_id` semantics for `PATCH /symbols/{symbol_id}`** — **RESOLVED.** The path param
  is declared `{"type": "integer"}`. This **dissolves** the carried Phase-25 D-08 / WR-05
  percent-encoding concern (an integer id can never contain `/`; the premise
  `symbol_id == "DLR/DIC26"` was false) and replaces it with the id-acquisition problem
  above. Confidence impact: took the WR-05 blocker question from Unclear to Confident-and-moot,
  and surfaced D-10 as its replacement.
- **Response shapes for the 8 mutation endpoints** — **PARTIALLY RESOLVED.** All eight are
  declared `object` with `additionalProperties: true` and **no** schema, so the concrete
  bodies remain a live question (as 26-CONTEXT predicted). But the declaration alone is
  decisive for one thing: none is an array, which confirms `parse_symbols_response`'s
  list-iteration reuse in the write path is a genuine bug (D-11) without needing live
  evidence. Also confirmed offline: `GET /symbols` → `array`, `GET /calendar` → `object`
  (independently corroborating the D-12 envelope bug at spec level, not just from the
  captured snapshot), and no `DELETE` method exists under `/symbols` (D-05).
- **Empirical POST idempotency (DM-03 revalidation)** — NOT resolvable offline; it needs a
  double-POST experiment against develop. Carried into D-19/D-20.
- **Whether develop's calendar config is shared/production-adjacent state** — an operator
  decision by construction (`market_data_mutations.md:103`). Resolved by the operator
  question above → D-06.
- **`"HH:MM"` vs `"HH:MM:SS"` acceptance, and drop-vs-`null` semantics for `HolidayIn`'s
  time overrides** — NOT resolvable offline; `MarketHoursIn` uses `format: time` with
  example `"10:00"`, and `HolidayIn.open_time`/`close_time` are `anyOf[time, null]`
  described as "null = configured default", but actual server acceptance is a live question.
  Remains in the Phase-26 Deferred list, to be answered by this phase's sweep.
