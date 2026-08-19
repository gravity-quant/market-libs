---
phase: 29-decoder-observable
plan: 04
subsystem: api
tags: [decoder, msgspec, benchmark, spike, d-lock, pure-python, supply-chain, decision]

# Dependency graph
requires:
  - phase: 29-decoder-observable
    plan: 02
    provides: "The shipped `_decode.py` walker with `hints_for` (`lru_cache`), `walk_model` and `open_request_scope()` — arm B of the benchmark is this module imported, never reimplemented"
  - phase: 29-decoder-observable
    plan: 01
    provides: "29-DLOCK-RESPONSE-LITERAL.md (D-09), the signed lock that msgspec's Literal enforcement would violate — the decisive capability finding"
provides:
  - "`29-DLOCK-MSGSPEC.md` — SIGNED: `no-go-stdlib-only`, sebadlf, 2026-08-19. D-lock (a) is closed, not deferred."
  - "A three-arm measured benchmark (uncached `from_api` / hints-cached walker / `msgspec.convert`) over five dataclass shapes including two frozen-NO-slots matriz forms"
  - "Five capability probes proving msgspec structurally cannot implement observable mode, and cannot implement strict mode without violating D-09"
  - "An absolute decode budget of 100 ms for the 5,000-row reference catalogue response, with the sensitivity table naming ~20.7 ms as the budget that would flip the verdict"
  - "The confirmed invariant that the six wheels remain a pure-Python closure — no compiled extension, no `uv.lock` churn"
affects: [29-05, 29-06, 29-07, 29-08, 29-09, 29-10, 30-typing, 33-driver-runs, 34-release]

actuals:
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Three-arm benchmark shape: the status-quo reference is NEVER the comparator. The comparator is the already-shipped optimisation, so a third-party library is measured against what the project can already do for free."
    - "GO/NO-GO stated as an absolute budget for a named reference workload, never as a speed ratio, when no throughput requirement exists against which a ratio would be decidable."
    - "Capability probes recorded alongside timing, because a faster engine that cannot express the required semantics is not a candidate at any speed."
    - "Ephemeral `uv --with X --no-project --python 3.12` evaluation with a mechanical byte-unchanged assertion on `uv.lock` and every `pyproject.toml` as the acceptance criterion."

key-files:
  created: []
  modified:
    - .planning/phases/29-decoder-observable/29-DLOCK-MSGSPEC.md

key-decisions:
  - "D-lock (a) SIGNED NO-GO — `no-go-stdlib-only`, sebadlf, 2026-08-19. Stdlib only, one engine: the cached walker. msgspec does not enter the project."
  - "The decision criterion is an absolute 100 ms budget for the 5,000-row reference catalogue response measured on arm B, not a speed ratio. Arm B measured 19.37 ms (matriz.Instrument) and 20.69 ms (market_data.Symbol) — 4.8x headroom, so the GO condition (arm B misses the budget) was never met."
  - "msgspec's 13-24x advantage over the shipped cached walker is real and was rejected anyway: it cannot serve observable mode at all, and a strict-mode-only fast path would violate the signed D-09 RESPONSE-Literal lock on the first new CFI code MATBA ROFEX publishes."
  - "The 123x figure that a naive benchmark would have reported (arm C against arm A) is an artifact of uncached `get_type_hints`, which is ~86% of arm A. The `lru_cache` shipped in Plan 29-02 already captures 7.1x of it with no dependency. Reporting that ratio would have manufactured a GO."
  - "Probe 4 (Literal enforcement) was the finding the spike did not anticipate and is the strongest single argument on the record — it turns the msgspec question from a cost/benefit tradeoff into a conflict with an already-signed lock of the same phase."
  - "The six packages remain a pure-Python closure. The §6 GO consequence list does not apply; Phase 34's release set stays as planned and the README's pure-Python claim stands."

patterns-established:
  - "A signed NO-GO is a complete outcome that closes a lock — the third consecutive one in this project (SPIKE-005, SPIKE-006, now D-lock (a))."
  - "Third-party evaluation runs in an ephemeral no-project environment with the interpreter explicitly pinned to the repo's minor version, so the comparison is never silently made against a newer CPython than the project targets."

requirements-completed: [DEC-01]

coverage:
  - id: D1
    description: "Three-arm benchmark measured over five dataclass shapes, including two frozen-NO-slots matriz forms, with per-shape microsecond numbers and the interpreter/msgspec versions named"
    requirement: DEC-01
    verification:
      - kind: other
        ref: "uv run --with msgspec --no-project --python 3.12 python spike_msgspec_timing.py (throwaway, scratch only; results transcribed into 29-DLOCK-MSGSPEC.md §2)"
        status: pass
      - kind: other
        ref: "test -f 29-DLOCK-MSGSPEC.md && grep -cE 'Arm A|Arm B|Arm C' >= 3"
        status: pass
    human_judgment: false
  - id: D2
    description: "Five capability probes recording msgspec's behaviour on undeclared keys, multiple simultaneous problems, missing fields, out-of-set Literals and stdlib-dataclass field renames"
    requirement: DEC-01
    verification:
      - kind: other
        ref: "Same spike run; findings table at 29-DLOCK-MSGSPEC.md §4"
        status: pass
    human_judgment: false
  - id: D3
    description: "No manifest mutated by the evaluation — uv.lock and every pyproject.toml byte-unchanged, no benchmark script committed"
    verification:
      - kind: other
        ref: "git diff --quiet HEAD -- uv.lock pyproject.toml 'packages/*/pyproject.toml'; grep -rn msgspec pyproject.toml packages/*/pyproject.toml uv.lock (no hits)"
        status: pass
      - kind: unit
        ref: "uv run pytest packages/higyrus-client -q --no-cov (213 passed)"
        status: pass
    human_judgment: false
  - id: D4
    description: "D-lock (a) signed by the operator with the verbatim decision and the budget it was measured against"
    requirement: DEC-01
    verification:
      - kind: manual_procedural
        ref: "checkpoint:decision gate=blocking-human; operator sebadlf answered `no-go-stdlib-only` 2026-08-19; recorded at 29-DLOCK-MSGSPEC.md §9"
        status: pass
    human_judgment: true
    rationale: "A blocking-human decision gate by construction — the verdict determines Phase 34's release set and the README's pure-Python claim, and no automation can supply the operator's acceptance of the 100 ms engineering ceiling, which is itself part of what is signed."

# Metrics
duration: 12min working (9h37m wall clock, spanning the blocking-human checkpoint)
completed: 2026-08-19
status: complete
---

# Phase 29 Plan 04: msgspec D-lock Summary

**D-lock (a) closed with a signed NO-GO: the stdlib hints-cached walker is the sole decode engine, msgspec rejected on a measured 100 ms budget it beat by 4.8x plus five capability probes showing it cannot express observable mode and would violate the signed D-09 Literal lock.**

## Performance

- **Duration:** 12 min working time; 9h 37m wall clock, the difference being the blocking-human checkpoint between task 1 and task 2
- **Started:** 2026-08-18T23:30:00-03:00 (task 1, prior executor session)
- **Task 1 committed:** 2026-08-18T23:37:40-03:00
- **Completed:** 2026-08-19T09:14:21-03:00
- **Tasks:** 2 of 2
- **Files modified:** 1 (`29-DLOCK-MSGSPEC.md`) — zero source files, zero manifests

## Accomplishments

- **The lock is signed and closed.** `29-DLOCK-MSGSPEC.md` carries `decision: no-go-stdlib-only`, `Signed: sebadlf`, `Date: 2026-08-19`. Phases 30-34 no longer wait on it; Phase 34's release set is final and the README's pure-Python claim stands.
- **The evidence is measured on both sides, not asserted.** Three arms over five shapes, with the interpreter (CPython 3.12.13) and library (msgspec 0.21.1) versions named, plus a measured end-to-end 5,000-row catalogue decode rather than a projection from per-row numbers.
- **The false-GO trap was avoided by construction.** Arm C against arm A would have reported **123x** and manufactured a GO for a win the `lru_cache` shipped in Plan 29-02 already delivers. The decision comparison, arm C against arm B, is **13-24x**.
- **The decisive finding was a capability, not a timing.** Probe 4 showed msgspec raises `ValidationError: Invalid enum value` on an out-of-set `Literal`. Lock D-09, signed earlier in this same phase, holds that a RESPONSE `Literal` is never closed. A msgspec strict-mode fast path would therefore break a signed lock on the first new CFI code the vendor publishes.
- **Zero repository footprint from a third-party evaluation.** msgspec was executed only in an ephemeral `--no-project` environment; `uv.lock` and all seven `pyproject.toml` files are byte-unchanged and the benchmark script was never committed.

## Task Commits

Each task was committed atomically:

1. **Task 1: Three-arm timing spike and the drafted D-lock artifact** — `1e4003e` (docs)
2. **Task 2: Checkpoint — sign the msgspec D-lock** — `dd7bbea` (docs)

**Plan metadata:** see the trailing `docs(29-04): complete the msgspec D-lock plan` commit.

## Files Created/Modified

- `.planning/phases/29-decoder-observable/29-DLOCK-MSGSPEC.md` — created in task 1 (285 lines: question, three-arm table, capability probes, absolute-budget criterion, verdict, GO consequences, supply-chain note, precedent, unsigned signature block), signed in task 2 (+58/-8: frontmatter decision/signoff fields, status line, and the §9 signature with the verbatim answer, the grounds table and the consequences of the signature).

## The operator's verbatim answer

Recorded here as required by the task-2 acceptance criteria, and mirrored into
`29-DLOCK-MSGSPEC.md` §9:

> **no-go-stdlib-only** — signed by operator **sebadlf**, date **2026-08-19**.
> D-lock (a) resolved: NO-GO on msgspec; stdlib-only, one engine (the cached
> walker). Recorded against the measured budget: arm B (cached walker) 19.37 ms /
> 20.69 ms on the 5,000-row catalogue vs the 100 ms budget; msgspec's 13-24x
> advantage rejected because it cannot serve observable mode, would violate the
> signed D-09 RESPONSE-Literal lock (msgspec enforces Literal membership), drops
> extra keys silently, reports one error per decode, and ignores field renames on
> stdlib dataclasses (market-data Symbol).

## The evidence the signature rests on

### Arm B was imported, never reimplemented

The acceptance criteria require this SUMMARY to record the exact import line the
spike used for arm B, so the comparator is provably the shipped module:

```python
from higyrus_client._decode import (
    POLICY, DecodePolicy, hints_for, open_request_scope, walk_model,
)
```

### Per-shape decode, microseconds per single row

| Shape | dataclass form | fields | Arm A | Arm B | Arm C | C vs B |
|---|---|---|---|---|---|---|
| `higyrus.PosicionValuada` | `frozen, slots` | 21 | 67.11 | **9.430** | 0.546 | 17.3x |
| `higyrus.Movimiento` | `frozen, slots` | 22 | 73.60 | **10.604** | 0.568 | 18.7x |
| `market_data.Symbol` | `frozen, slots` | 8 | 29.00 | **4.138** | 0.321 | 12.9x |
| `matriz.Instrument` | **`frozen`, NO slots** | 2 | 42.71 | **3.946** | 0.297 | 13.3x |
| `matriz.InstrumentDetail` | **`frozen`, NO slots** | 20 | 156.49 | **20.297** | 0.865 | 23.5x |

Two frozen-NO-slots shapes were mandatory: the only prior msgspec evidence in
this project covered `frozen+slots` only and therefore did not cover 18 of
matriz's dataclasses. They behaved no differently in any arm.

### The decision measurement

| | 5,000-row catalogue response |
|---|---|
| Budget (criterion, §3) | **100 ms** |
| Arm B — `matriz.Instrument` end-to-end | **19.37 ms** |
| Arm B — `market_data.Symbol` | **20.69 ms** |
| Arm B misses the budget? | **No — 4.8x headroom** |
| Verdict | **NO-GO** |

Only a budget below ~20.7 ms at 5,000 rows (or ~42 ms at 10,000) would have
flipped this, and no throughput requirement exists in this project that would
justify one.

### Capability probes — why speed was not the deciding term

| # | Probe | msgspec 0.21.1 | The shipped walker |
|---|---|---|---|
| 1 | Two undeclared keys | Silently dropped, no error | 2 `extra` records, model untouched |
| 2 | Five simultaneous problems | **One** `ValidationError`; the other four never seen | All **5** divergences with field paths, model still built |
| 3 | Missing required field | Raises | `sesion=''` + a `missing` record |
| 4 | Out-of-set `Literal` | **Raises — violates signed lock D-09** | Returns the value unchanged, 0 records |
| 5 | Field rename on a stdlib dataclass | Ignored — `Renamed(market_id='')` | Works (ordinary Python) |

Probes 1 and 2 are DEC-01's two deliverables. msgspec has neither, which is why
the walker is the primary engine in the GO branch too — the question was only ever
whether to add a *second* engine.

## Decisions Made

All six key decisions are listed in the frontmatter. The three that shape
downstream phases:

1. **NO-GO signed** — one decode engine, the cached stdlib walker, in both strict
   and observable mode. Nothing downstream needs a second semantic model.
2. **The budget, not the ratio, is what was signed.** The 100 ms ceiling is an
   engineering judgment, explicitly flagged in the artifact as part of what the
   operator accepts, with a sensitivity table making the consequence of moving it
   visible. Revisiting requires a stated throughput requirement.
3. **The pure-Python closure is preserved.** No compiled extension, no lockfile
   refresh, no CI frozen-sync dependency, no README retraction, no growth in the
   Phase 34 release set.

## Deviations from Plan

None — plan executed exactly as written. Both tasks ran to their stated `done`
criteria, every acceptance criterion was met, and no deviation rule was invoked in
either task.

## Issues Encountered

**Arm A had to be sourced two different ways, and the artifact says so.** Because
Wave 4 has not run, higyrus's `models.py` already delegates to the cached walker,
so no uncached `from_api` survives there to time. Arm A for higyrus is
reconstructed via `hints_for.cache_clear()` before each decode, forcing exactly one
uncached `get_type_hints` per decode. A control measurement bounds the distortion:
`cache_clear()` alone costs 0.035 µs, or 0.05% of arm A. For market-data and
matriz, whose `models.py` are untouched, arm A is the genuine production code as it
stands today. This is disclosed in `29-DLOCK-MSGSPEC.md` §2 rather than smoothed
over, because arm A is the reference the reader calibrates against.

**The checkpoint spanned a session boundary.** Task 2 is `gate="blocking-human"`,
so the task-1 executor halted and returned rather than proceeding; this
continuation executor verified `1e4003e` and the on-disk artifact with its empty
`Signed:`/`Date:` lines before resuming. No work was redone.

## Supply-chain posture

msgspec is flagged `[SUS]` by `gsd-tools query package-legitimacy` for exactly one
reason — the PyPI JSON API exposes no download counts for it — which is a registry
metadata artifact, not a risk signal. The source repository is present and current
and release 0.21.1 is recent. It was executed only in an ephemeral `--no-project`
environment and never installed into the workspace. Under the signed NO-GO it does
not enter the project at all, so the T-29-SC and T-29-19 threats are closed rather
than mitigated.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- **D-lock (a) is resolved**, which was recorded in STATE.md as a gate Phases 30-34
  depend on. Nothing downstream is blocked on it.
- **Plans 29-05 through 29-10** proceed against a single decode engine. There is no
  msgspec branch to plan for and no second path to keep semantically identical.
- **Phase 30 (typing)** may keep `Literal` types as designed — the pressure to widen
  them to `str` for a decoder's benefit is gone with the NO-GO.
- **Phase 34 (release)** keeps its planned release set and wheel matrix; the six
  packages stay platform-independent pure-Python distributions.
- **Wave 4 note, not a blocker:** market-data's and matriz's `models.py` still carry
  uncached `get_type_hints` on every decode — that is arm A, measured here at
  212.87 ms for a 5,000-row catalogue against the cached walker's 19.37 ms. The
  11x is the value Wave 4 delivers when it lands the walker in those packages.
- **No blockers or concerns.**

## Self-Check: PASSED

- `29-DLOCK-MSGSPEC.md` present, carries `Signed: sebadlf` and `Date: 2026-08-19`.
- `29-04-SUMMARY.md` present with the operator's verbatim answer.
- Commits `1e4003e` (task 1) and `dd7bbea` (task 2) both present in git history.
- `git diff --quiet HEAD -- uv.lock pyproject.toml 'packages/*/pyproject.toml'` exits 0.
- `grep -rn msgspec` over `uv.lock` and all `pyproject.toml` files returns no hits.
- `uv run pytest packages/higyrus-client -q --no-cov` — 213 passed.

---
*Phase: 29-decoder-observable*
*Completed: 2026-08-19*
