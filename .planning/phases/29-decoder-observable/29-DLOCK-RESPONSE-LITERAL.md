# Phase 29 — D-lock: `Literal` is never closed on RESPONSE fields (D-09)

**Status:** policy artifact — **awaiting operator signature**
**Written:** 2026-08-19
**Source tree:** branch `milestone/v1.5-mutations` @ `8b3b69b`
**Governs:** the walker's `Literal` branch in every `_decode.py` copy, the
`literal_enforced` field of `DecodePolicy`, and every model field written by Phases
30-34.
**Companion artifacts:** `29-SEMANTICS-MATRIX.md` (Section 2),
`29-AGGREGATION-CONTRACT.md` (locks 2-4).

---

## The decision

**Response fields are never closed as `Literal` in this milestone.**

A field whose value comes back from a vendor API:

1. is declared and decoded as `str` (or its actual runtime type), never as a closed
   `Literal[...]` set that the decoder enforces;
2. when the wire sends a value **outside** the documented set, that value is
   **reported as a divergence and returned unchanged** — it is never rejected,
   never coerced, never replaced by a default;
3. is therefore, from the caller's point of view, behaviorally identical to today.

Silence on out-of-set values. Loudness on wrong runtime type.

---

## What the walker does

The walker gets an **explicit `get_origin(hint) is Literal` branch**, placed **before**
the bare `return value` fall-through where these fields land today. That branch:

**(a) never enforces membership.** A `MarketId`-declared field whose wire value is
`"XYZ"` returns `"XYZ"`. No exception in strict mode, no substitution in observable
mode, and — per lock 4 of the aggregation contract — nothing fatal. Whether an
out-of-set value is even reported as an `INFO`-level observation is the walker's
choice within this policy; what is fixed is that it is **never** a `WARNING`, never
raises, and never changes the returned value.

**(b) does validate the underlying runtime type of the literal's members.** All nine
aliases below are `str`-valued. So a wire `int` where a `str`-valued `Literal` is
declared still reports a **`type`** divergence — a `WARNING`, and fatal under strict
mode — exactly as if the field had been declared `str`.

This asymmetry is the whole point. Vendor enum growth (a new order status, a new
segment, a new CFI code) is a normal, expected event and must not break a caller or
storm a strict driver run. A vendor sending a number where every documented value is a
string is a real shape divergence and must be as loud as any other.

Without the explicit branch, a naive "unknown hint → divergence" policy would emit a
divergence for **every** `Literal`-typed field on **every** decoded row — nine aliases
spread across `InstrumentId`, `Instrument`, `Order`, `Trade` and the market-data frame
models. That is a permanent false-positive floor on every matriz response.

`literal_enforced` exists as a named field on `DecodePolicy` only so the branch reads
against a policy value instead of a bare constant. Per `29-SEMANTICS-MATRIX.md`
Section 2 it is **`False` in all five copies, permanently, and is not a tunable**.
Plan 09's ban-list grep should treat `literal_enforced=True` as a violation.

---

## The nine matriz aliases this reaches retroactively

All nine live in `packages/matriz-client/src/matriz_client/types.py`. All nine are
`str`-valued. All are already published in matriz-client v0.1.1.

| # | Alias | Line | Members |
|---|---|---|---|
| 1 | `Side` | `types.py:35` | `"BUY"`, `"SELL"` |
| 2 | `OrderType` | `types.py:38` | `"LIMIT"`, `"MARKET"`, `"STOP_LIMIT"`, `"STOP_LIMIT_MERVAL"` |
| 3 | `TimeInForce` | `types.py:41` | `"DAY"`, `"IOC"`, `"FOK"`, `"GTD"` |
| 4 | `MarketId` | `types.py:44` | `"ROFX"` — the only documented value (§12.1) |
| 5 | `SegmentId` | `types.py:47` | `"DDF"`, `"DDA"`, `"DUAL"`, `"MERV"`, `"U-DDF"`, `"U-DDA"`, `"U-DUAL"` |
| 6 | `CFICode` | `types.py:50-60` | 9 ISO 10962 codes (`"ESXXXX"` … `"DBXXFR"`) |
| 7 | `MarketDataEntry` | `types.py:63-78` | 14 entry codes (`"BI"`, `"OF"`, `"LA"`, … `"ACP"`) |
| 8 | `OrderStatus` | `types.py:81-92` | 10 life-cycle states (`"NEW"` … `"PARTIALLY_FILLED"`) |
| 9 | `Currency` | `types.py:95` | `"ARS"`, `"USD"` |

`MarketId` is the sharpest case: a single-member `Literal` documented as "the only
documented value." Closing it would make matriz-client raise the moment MATBA ROFEX
introduces a second market — an event entirely outside our control and announced on
their schedule, not ours.

---

## Evidence that this is behaviorally free for matriz

The change is **reporting-only**. It cannot alter a single value matriz-client returns
today, because these fields are **already unvalidated**.

`_convert` — matriz's coercion function — has no `Literal` branch, no scalar branch,
and ends in a bare pass-through:

```python
# packages/matriz-client/src/matriz_client/models.py:74-92
def _convert(tp: Any, value: Any) -> Any:
    """Coerce ``value`` to the shape declared by ``tp``, applying safe defaults."""
    inner = _strip_optional(tp)
    origin = get_origin(inner)

    if origin is list:
        ...
    if origin is dict:
        return value if isinstance(value, dict) else {}
    if _is_model(inner):
        return inner.from_api(value) if isinstance(value, dict) else inner.empty()

    return value          # ← line 92: every Literal-typed field lands here, untouched
```

A `MarketId`-declared field arriving as `"XYZ"` is returned as `"XYZ"` today. It will
be returned as `"XYZ"` after Phase 29. The only difference is that a record now
describes it. This is also row 5 of `29-SEMANTICS-MATRIX.md`, whose `scalar handling`
cell reads "pass-through, unvalidated" and whose `scalar_passthrough` policy constant
is `True`.

The inverse decision would **not** be behaviorally free. Enforcing membership would be
a silent behavior break on published surface: code that works against matriz-client
v0.1.1 today would begin raising after an upgrade, triggered by data rather than by
anything the caller did.

---

## Consequence for Phase 33

**Closing any of these nine aliases with a live census is deferred to Phase 33
(DT-07)** and is explicitly out of scope here.

Doing it early — on documentation alone, without a live census — would be a silent
behavior break on published surface, and would be taken on the weakest possible
evidence: vendor documentation, which is exactly the artifact this whole project
exists because it cannot be trusted. Phase 33 has live credentials and the divergence
pipeline; if a census over real responses shows an alias's set is genuinely closed, it
can be closed **then**, as its own decision with its own artifact and its own
signature, with the census as evidence.

Until then, the observable divergence stream is the census-gathering mechanism: every
out-of-set value that shows up in a Phase 33 driver run is evidence about the real
shape of the vendor's enums, accumulated at zero risk to callers.

Note this D-lock is scoped to **RESPONSE** fields. `Literal` on **input** parameters —
where the closed set constrains what *we* send and mypy catches the error before any
request leaves the process — is a different question and is not decided here.

---

## Signature

This is a one-way door. Phase 30 (`iol-client` typed) and Phase 31 (ops endpoints)
write model surface against this decision. Reversing it after Phase 30 means
re-editing already-shipped public surface and re-publishing wheels in Phase 34.

Signed:
Date:
Decision recorded:
