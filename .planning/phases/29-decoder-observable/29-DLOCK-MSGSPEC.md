---
lock: D-lock (a) — msgspec two engines vs stdlib only
phase: 29-decoder-observable
plan: 04
decision: TBD
recommended_verdict: NO-GO
criterion: absolute decode budget for the largest live catalogue response
budget_ms: 100
measured_worst_case_ms: 20.7
signoff_by: TBD
signoff_date: TBD
requirements: [DEC-01]
supersedes: "tipado_homogeneo.md:100 (msgspec a runtime deps de los 6 paquetes)"
---

# D-lock (a) — msgspec as a strict-mode fast path, or stdlib only

**Status:** DRAFT — `decision: TBD`, awaiting the operator signature in Task 29-04-02.
**Recommended verdict (advisory):** **NO-GO** — stdlib only, one engine.

## 1. The question

Not *which decoder*. The stdlib per-field walker (`_decode.walk_model`) is the
primary engine in **both** branches of this lock, because msgspec structurally
cannot implement observable mode (§4). The question is narrower:

> Does a msgspec **strict-mode fast path**, added *alongside* the walker, earn
> the cost of putting a compiled C extension into six wheels that are pure
> Python today?

A GO means two decode engines to keep semantically identical, forever. A NO-GO
means one.

## 2. Three-arm benchmark

Run in an ephemeral environment. **No `pyproject.toml` and no `uv.lock` was
mutated**; msgspec was never installed into the workspace.

```
uv run --with msgspec --with httpx --with python-dotenv --with websocket-client \
       --with tenacity --no-project --python 3.12 python spike_msgspec_timing.py
```

(`httpx`, `python-dotenv`, `websocket-client` and `tenacity` are the transitive
imports the three packages' `__init__.py` pull in; they carry no meaning for the
measurement. The explicit `--python 3.12` pins the interpreter to the repo's
minor version so the comparison is not silently made against a newer CPython.)

| Field | Value |
|---|---|
| Interpreter | **CPython 3.12.13** (`main`, Mar 25 2026, Clang 22.1.1) |
| msgspec | **0.21.1** |
| Platform | macOS-26.5.2-arm64, Apple silicon |
| Method | `timeit.repeat`, 7 repetitions, adaptive `number`, **median** reported |

### The three arms

| Arm | What it is | Role |
|---|---|---|
| **Arm A** | `from_api` with **uncached** `get_type_hints` — the pre-Phase-29 status quo | Reference **only**. Never the comparator. |
| **Arm B** | The **shipped hints-cached walker**, imported from `higyrus_client._decode` | **The honest comparator.** |
| **Arm C** | `msgspec.convert(payload, type=cls)` | The pro-msgspec evidence. |

Arm B is imported, never reimplemented. The exact import in the spike script:

```python
from higyrus_client._decode import (
    POLICY, DecodePolicy, hints_for, open_request_scope, walk_model,
)
```

Arm A had to be sourced two different ways, because Wave 4 has not run yet:

- **higyrus** — `models.py` already delegates to the cached walker (Plan 29-02),
  so there is no uncached `from_api` left to time. Arm A is reconstructed as
  `hints_for.cache_clear()` before each decode, which forces exactly one
  uncached `get_type_hints` per decode — the status quo. Control: `cache_clear()`
  alone costs **0.035 µs**, i.e. 0.05 % of arm A, so it does not distort the
  reference.
- **market-data and matriz** — `models.py` is **untouched**; their `from_api`
  still calls `get_type_hints(cls)` uncached on every decode. Arm A there is the
  genuine production code as it stands today.

### Results — µs per single-row decode

| Shape | dataclass form | fields | **Arm A** (µs) | **Arm B** (µs) | **Arm C** (µs) | C vs B |
|---|---|---|---|---|---|---|
| `higyrus.PosicionValuada` | `frozen=True, slots=True` | 21 | 67.11 | **9.430** | 0.546 | 17.3× |
| `higyrus.Movimiento` | `frozen=True, slots=True` | 22 | 73.60 | **10.604** | 0.568 | 18.7× |
| `market_data.Symbol` | `frozen=True, slots=True` | 8 | 29.00 | **4.138** | 0.321 | 12.9× |
| `matriz.Instrument` | **`frozen=True`, NO slots** | 2 (1 nested) | 42.71 | **3.946** | 0.297 | 13.3× |
| `matriz.InstrumentDetail` | **`frozen=True`, NO slots** | 20 (2 nested, 2 list) | 156.49 | **20.297** | 0.865 | 23.5× |

Two of the five shapes are `frozen=True` with **no** `slots` — matriz's actual
form. The only prior msgspec evidence in this project covered `frozen+slots`
only, which would not have covered 18 of matriz's dataclasses. The no-slots
shapes behave no differently in any arm.

Payloads were synthesised from the model field lists. No `.env` was read, no
captured live payload was used, and no credential is touched by the spike.

### Control measurements

| Operation | µs |
|---|---|
| `typing.get_type_hints(PosicionValuada)` uncached | 57.38 |
| `hints_for(PosicionValuada)` warm (`lru_cache`) | 0.0321 |
| `hints_for.cache_clear()` | 0.035 |

This is the Pitfall-2 decomposition, re-measured: ≈ 86 % of arm A is one
uncached `get_type_hints` call. The `lru_cache` shipped in Plan 29-02 is a
**7.1×** whole-decode speedup with zero new dependency. **Comparing arm C
against arm A would report 123× and manufacture a GO for a win the hints cache
already delivers.** The comparison that decides this lock is arm C against
arm B, and that is 13–24×, not 123×.

### End-to-end catalogue decode (measured, not projected)

`matriz.get_all_instruments`, 5,000 rows, one `open_request_scope()` bound for
the whole response, list built to completion:

| Arm | 5,000-row response |
|---|---|
| **Arm A** — native uncached `from_api` | 212.87 ms |
| **Arm B** — shipped cached walker | **19.37 ms** |
| **Arm C** — `msgspec.convert(..., type=list[Instrument])` | 0.85 ms |

Row-count sensitivity for arm B:

| rows | `matriz.Instrument` | `market_data.Symbol` |
|---|---|---|
| 1,000 | 3.95 ms | 4.14 ms |
| 5,000 | 19.73 ms | 20.69 ms |
| 10,000 | 39.46 ms | 41.38 ms |

Context: the same 5,000-row response is a 488 KiB body, and `json.loads` on it
costs **1.05 ms**. Decode is ≈ 18× the cost of parsing the bytes, and both are
small next to a single HTTPS round trip to the vendor.

## 3. GO/NO-GO criterion — an absolute budget, not a ratio

A ratio threshold is **not decidable**: no throughput requirement exists in this
project against which "13×" or "24×" is either sufficient or insufficient. The
criterion is therefore stated as an absolute ceiling.

> **Criterion.** Decode of the largest live catalogue response in this repo —
> `matriz.get_all_instruments` (`GET /rest/instruments/all`) and
> `market_data.get_instruments` / `get_symbols`, taken at a **5,000-row
> reference workload** (the magnitude named in 29-RESEARCH.md Pitfall 7) — must
> complete in **under 100 ms** measured on **Arm B**.
> **GO only if Arm B misses that budget.**

100 ms is the ceiling below which decode is not a term any consumer of these
libraries would notice against the network call that produced the payload. The
number is an engineering ceiling, not a measured requirement — **it is part of
what the operator signs.** The sensitivity below makes the consequence of moving
it explicit.

### Sensitivity — what budget would flip the verdict

| Budget for the 5,000-row reference workload | Arm B verdict |
|---|---|
| 100 ms (proposed) | **passes**, 4.8× headroom |
| 50 ms | passes, 2.4× headroom |
| 25 ms | passes, 1.2× headroom |
| **< 20.7 ms** | **fails → GO** |

Arm B only misses a budget set below ~21 ms for a 5,000-row response, or below
~42 ms at 10,000 rows. A budget that tight would have to be justified by a
stated throughput requirement, and none exists.

## 4. Capability findings — why the walker is primary in either branch

These are behavioural facts, measured in the same run. They are **not** timing
evidence; they are the reason msgspec can only ever be an *additional* engine.

| # | Probe | msgspec 0.21.1 | The shipped walker |
|---|---|---|---|
| 1 | Payload carries **two undeclared keys** | **No error.** Returns a valid `PosicionValuada`; both keys silently dropped, `hasattr(out, 'nuevoCampoDelVendor') == False`. | Emits **2** `extra` records at INFO and leaves the model untouched. |
| 2 | Payload with **five simultaneous problems** (int-where-str, str-where-float, null-where-float, list-where-float, one missing field) | Raises `ValidationError: Expected \`str\`, got \`int\` - at \`$.cuenta\`` — **exactly one error. The other four are never seen.** | Reports **all 5** divergences with their field paths, raises nothing, and still constructs the model. |
| 3 | One **missing required field** | Raises `ValidationError: Object missing required field \`sesion\`` | Returns `sesion=''` and reports `('PosicionValuada', '.sesion', 'missing')`. |
| 4 | **Out-of-set `Literal`** — `cficode='ZZXXXX'` against the declared `CFICode` | Raises `ValidationError: Invalid enum value 'ZZXXXX' - at \`$.cficode\`` | Returns `'ZZXXXX'` **unchanged**, 0 records — D-09, `literal_enforced=False`. |
| 5 | **Field rename** on a stdlib dataclass (`market_id` → `marketId`) | `msgspec.field(name=...)` is a `msgspec.Struct` feature. `dataclasses.field(metadata={"name": ...})` is ignored: `convert({'marketId': 'ROFX'})` yields `Renamed(market_id='')`. | `Symbol.from_api`'s mirror is ordinary Python and works. |

Probes 1 and 2 are DEC-01's two deliverables — extra-key detection and
multi-divergence collection — and msgspec has neither. **Probe 4 is the finding
this spike did not expect and is the strongest single argument on the record:**
msgspec enforces `Literal` membership and raises on an out-of-set value. Lock
D-09 (`29-DLOCK-RESPONSE-LITERAL.md`) is signed the other way — a RESPONSE
`Literal` is *never* closed, because vendor enum growth must not fail a Phase 33
strict driver run. A msgspec "strict-mode fast path" would therefore **violate a
signed lock of this same phase** on the first new CFI code MATBA ROFEX
publishes, unless every `Literal` in every model were first widened to `str`
for msgspec's benefit — which would delete the typing work Phase 30 exists to
do. Probe 5 removes market-data's `Symbol` from any msgspec path outright.

## 5. Verdict against the criterion

| | |
|---|---|
| Budget | 100 ms for the 5,000-row reference catalogue response |
| **Arm B measured** | **19.37 ms** (matriz.Instrument end-to-end), **20.69 ms** (market_data.Symbol) |
| Arm B misses the budget? | **No** — 4.8× headroom |
| **Criterion verdict** | **NO-GO** |

Arm C is genuinely 13–24× faster than arm B. That speed buys nothing here: it
converts a 19 ms term into a 1 ms term inside a call whose payload arrived over
the public internet, in libraries with no stated throughput requirement, and it
cannot be applied to the mode that actually needs a decoder (observable) or to
strict mode without breaking D-09 and market-data's `Symbol`.

**Recommended verdict: NO-GO — stdlib only, one engine.**

## 6. If the decision is GO — the itemised downstream consequences

The operator is accepting all six of these, not only the fast path:

1. **A compiled C extension enters six wheels that are pure Python today.**
   `iol-client`, `higyrus-client`, `ambito-financiero-client`, `wallets-client`,
   `matriz-client`, `market-data-client` all stop being platform-independent
   pure-Python distributions.
2. **`uv.lock` is refreshed once**, and the refresh must be committed.
3. **Every CI job's `uv sync --frozen` depends on that refresh** — all lint,
   pre-commit, typecheck and the 6×2 test matrix fail until the lockfile lands,
   so the refresh and the manifest edit must be one atomic change.
4. **The README must declare the loss of the pure-Python closure** — a DT-08
   changelog obligation for every one of the six packages.
5. **The Phase 34 release set changes** — six packages re-publish instead of the
   currently planned set, each with a new wheel matrix.
6. **Two decode paths must be kept semantically identical forever.** The
   walker's substitution table (`DecodePolicy`, five copies, hash-checked by
   Plan 29-09's intactness test) and msgspec's validation semantics diverge on
   at least four of the five probes in §4. Strict mode would have to be proven
   to raise on exactly the same inputs as the walker, in perpetuity, or the two
   engines would disagree about what a divergence is.

Additionally, GO does **not** authorise the change: adoption is a separate,
separately-gated edit in Phase 34. No manifest may be touched in this plan under
any outcome.

## 7. Supply-chain note

From the Package Legitimacy Audit in `29-RESEARCH.md`:

- `msgspec` is flagged **[SUS]** by `gsd-tools query package-legitimacy` for a
  **single** reason: the PyPI JSON API exposes **no download counts** for it.
  That is a registry-metadata artifact, not a risk signal.
- Latest release **0.21.1**, published 2026-04-12. The project is multi-year and
  the source repository (`github.com/jcrist/msgspec`) is present, current and not
  deprecated. The wheel has no postinstall concept.
- It was executed here **only** in an ephemeral `--no-project` environment,
  never installed into the workspace, and `uv.lock` plus every `pyproject.toml`
  are byte-unchanged (asserted mechanically in this plan's verification).
- Adoption is gated behind **this signature plus a separate Phase 34 change** —
  a stronger control than the `checkpoint:human-verify` the audit would
  otherwise require.

## 8. Precedent

Both prior spikes in this project ended in a signed NO-GO
(`SPIKE-005-codegen-tool-choice`, `SPIKE-006-libcst-codegen-tool-choice`). A
signed NO-GO is a complete outcome and closes the lock; it is not a deferral.
Deferring, by contrast, leaves Phase 34 unable to finalise its release set and
propagates the ambiguity into Phases 30–34.

## 9. Signature

Options, as presented at the checkpoint:

| id | Outcome |
|---|---|
| `no-go-stdlib-only` | **NO-GO** — stdlib only, one engine *(recommended)* |
| `go-msgspec-fast-path` | GO — msgspec as a strict-mode fast path alongside the walker |
| `defer` | Defer the decision to a later milestone |

**Verdict:**

**Budget measured against:**

Signed:
Date:

---
*Evidence: throwaway three-arm benchmark, ephemeral env, 2026-08-19. Script not
committed — no repository footprint.*
