# Phase 29 — Divergence record & aggregation contract

**Status:** authoritative policy artifact — **awaiting operator signature**
**Written:** 2026-08-19
**Source tree:** branch `milestone/v1.5-mutations` @ `8b3b69b`
**Governs:** the `_emit` function, the `DivergenceSink` / `DecodeScope` machinery
and the strict-mode raise sites inside every `_decode.py` copy created by Phase 29
Plans 02-10.
**Companion artifacts:** `29-SEMANTICS-MATRIX.md` (D-07),
`29-DLOCK-RESPONSE-LITERAL.md` (D-09).

This document resolves the two decisions `29-RESEARCH.md` explicitly refused to
assume — Open Question 1 / Assumption A2 (does strict mode raise on extra wire
keys?) and Open Question 4 / Assumption A3 (what is the dedupe key and its scope?).
RESEARCH labelled the aggregation contract **LOW confidence / proposal**, not a
finding. Locks 4 and 5 below are the decisions; everything else is the surrounding
contract they need in order to be implementable.

Each lock is normative. "MUST" means Plan 09's intactness check or an in-package test
is expected to detect a violation.

---

## Lock 1 — Record schema

The divergence record is **exactly six `extra` keys**, every value a `str`, every key
top level, **no nested containers of any kind**:

| Key | Value | Example |
|---|---|---|
| `package` | The package logger name. | `"higyrus_client"` |
| `divergence` | The kind (lock 2). | `"missing"` |
| `field_path` | Dotted path from the decode root to the divergent field. | `".parking[].diasParking"` |
| `declared_type` | The model's declared type name. | `"float"` |
| `observed_type` | The wire value's runtime type name. | `"NoneType"` |
| `model` | The **bare** class name. | `"PosicionValuada"` |

The log message is the constant string `decode divergence`. It carries no
interpolation and no `%`-args — every variable part of the record lives in `extra`.

`model` MUST carry the bare class name, never a dotted path and never a
fully-qualified name. An FQN would carry the module, which invites a `module` key —
and `module` is reserved (see below). The `package` key already answers "which
library", so the FQN is redundant as well as dangerous.

`declared_type` and `observed_type` MUST use the `verification/schema.py::schema_of`
vocabulary — i.e. the value of `type(x).__name__` (`verification/schema.py:40`).
This is D-06: the record's type strings are then byte-identical to what the
`.planning/verification/schemas/` corpus stores, so Phase 33's handler needs zero
translation and the Phase 29 sizing floor is directly contrastable with Phase 33's
live census. Do **not** introduce a `type_of()` helper.

For a divergence of kind `extra` there is no declared type. `declared_type` is then
the single character `-`. It is never the empty string (an empty string in a log
record reads as a bug) and never `None` (the all-str contract).

### Why this key set, and not the natural one

`logging.Logger.makeRecord` refuses to overwrite an existing `LogRecord` attribute
and raises `KeyError` when `extra` contains one. Verified by direct execution on this
repo's interpreter (CPython 3.12.13) during this plan:

```
SAFE:   package  divergence  field_path  declared_type  observed_type  model
RAISES: name  msg  args  levelname  module  message  asctime  exc_info  taskName
```

The two most natural names for "which module diverged" and "which field diverged" are
`module` and `name` — **both raise**. A decoder that raises `KeyError` from inside its
own emission path converts observable mode into fatal mode for every caller, which is
the precise inversion of the policy change this phase exists to make. This is a live
trap, not a theoretical one, and it is absent from all 25 pitfalls catalogued in
`.planning/research/`.

The full reserved set the schema deliberately avoids, enumerated from a real
`LogRecord.__dict__` plus the two names `makeRecord` adds by hand
(`message`, `asctime`):

```
args  asctime  created  exc_info  exc_text  filename  funcName  levelname
levelno  lineno  message  module  msecs  msg  name  pathname  process
processName  relativeCreated  stack_info  taskName  thread  threadName
```

The naming discipline is copied from the repo's only existing structured-`extra`
emitter, `packages/higyrus-client/src/higyrus_client/_transport.py:165-177`, which
already dodges every reserved name by using `method` / `url` rather than
`module` / `name`, and leads with `"package": _LOGGER_NAME`. That emitter is a naming
analog only — it is *not* all-str (`status_code` and `attempt` are ints); the decode
record tightens that to all-str per D-05.

An in-package test MUST construct a real record through `logger.warning(msg, extra=…)`
or `Logger.makeRecord` directly. The existing `_make_record` test helper
(`packages/higyrus-client/tests/test_logging.py:25-40`) uses `setattr` and therefore
**cannot** reproduce the `KeyError` — `makeRecord` raises, `LogRecord.__init__` does not.

---

## Lock 2 — Divergence kinds

Exactly four, and no others may be added within this milestone:

| Kind | Definition |
|---|---|
| `missing` | The model declares the field but the payload has no key for it (or the key is present with a `None` value where the declared type is not `Optional`). |
| `type` | The payload has the key, but the value's runtime type does not match the declared type, so the policy substitutes a default. |
| `extra` | The payload carries a key the model does not declare, so the value is discarded entirely. |
| `non_dict` | A model was asked to decode a payload that is not a `dict` (e.g. `None`, a `list`, a bare scalar). |

---

## Lock 3 — Level map

| Kind | Level |
|---|---|
| `missing` | `WARNING` |
| `type` | `WARNING` |
| `non_dict` | `WARNING` |
| `extra` | `INFO` |

`extra` is demoted deliberately. An extra wire key is the **normal** result of vendor
API growth — the vendor added a field and our model has not caught up. That is
information, not a defect. The repo already draws this distinction:
`verification/safemodel_diff.py` classifies `model-only` as a FALSE PASS risk and
`wire-only` as informational. Emitting extras at `WARNING` would drown the real
signal — the `missing` and `type` records that represent silent substitution, which is
the class of bug DEC-01 exists to surface. The research prototype found 7 extra keys
on matriz `InstrumentDetail` alone.

---

## Lock 4 — Open decision 1, RESOLVED: strict mode never raises on `extra`

**Strict mode raises on `missing`, `type` and `non_dict`, and never on `extra`.**

This is unambiguous and admits no per-package override: there is no policy field, no
keyword argument and no environment variable that makes an `extra` divergence fatal.
In strict mode an `extra` divergence is emitted at `INFO` exactly as in observable
mode, and decoding continues.

**Reasoning, recorded because criterion 2 read literally says otherwise.** ROADMAP
criterion 1 lists "campo extra" among the payload shapes that must decode without
raising in observable mode; criterion 2 says "la misma divergencia levanta" in strict
mode. Read literally, extra keys would raise. That reading makes Phase 33's strict
driver run fail on **every legitimate new vendor field** — a divergence storm by
construction, and one that arrives on the vendor's release schedule rather than ours.
It would force Phase 33 to absorb every upstream field addition as a blocking finding,
materially worsening the mass-divergence-discovery risk already flagged in `STATE.md`.
It is also inconsistent with D-09, which forbids `Literal` membership enforcement for
exactly the same reason: vendor enum growth must not be fatal.

The cost is stated plainly so it is not discovered later: a field that the vendor
**renames** surfaces as an `INFO` `extra` record for the new name plus a `WARNING`
`missing` record for the old one, rather than as one loud failure. The `missing` half
still raises in strict mode, so a rename is never silent — it is simply reported as
two records instead of one.

---

## Lock 5 — Open decision 2, RESOLVED: the dedupe key

**The dedupe key is the triple `(model, field_path, kind)`.**

- `model` is the bare class name, as in the record.
- `field_path` is the dotted path, as in the record.
- `kind` is one of the four values in lock 2.

`package` is not part of the key because a scope never spans two packages.
`declared_type` and `observed_type` are not part of the key: including
`observed_type` would defeat the whole purpose on a heterogeneous list, where row 1
sends `null` and row 2 sends `0` for the same declared-`str` field and would produce
two records for one modelling problem.

**The list index is deliberately excluded.** A `list[X]` element contributes the path
segment `[]` with **no index** — the path for the third element of `parking` is
`.parking[].diasParking`, identical to the first element's. This is the mechanism that
collapses N identically-diverging rows into one record, and it is the entire answer to
the log-spam problem: an unbounded catalogue read (`matriz.get_all_instruments`,
`market_data.get_instruments`) whose 5,000 rows all miss the same field emits **one**
record, not 5,000.

**Distinct kinds at the same path stay distinct records.** A path that is `missing` on
some rows and `type`-divergent on others yields two records, because those are two
different facts about the model and a consumer triaging them needs both.

---

## Lock 6 — Scope

The dedupe set lives in a **decode scope**.

`_request` binds a fresh decode scope at its top, using the same `.set()`-without-reset
discipline as the strict-mode carrier (D-03). Every model decoded from one HTTP
response therefore shares one scope — including **every element of a top-level
`list[Model]` parse**, which is what makes lock 5's collapse actually fire. The bind
sits alongside the mode bind, in `Client._request` and `AsyncClient._request` (C-3),
on the method only; the module-level shims delegate through it.

Binding at `_request` rather than at the decode entry is safe with respect to the
re-auth carve-out (`market_data_client/client.py:392-402` re-sends the same request
once after a 401): only the final response ever reaches a parser, so decode runs once
regardless of how many times the request was sent. A scope spanning both attempts
costs nothing because the first attempt never decodes.

**When no scope is bound** — a direct `Model.from_api()` call with no preceding
request, which is a supported public entry point (DT-05) — the outermost `walk_model`
creates a **per-call scope** for the duration of that call and discards it on return.
The nested `walk_model` calls beneath it MUST detect the existing scope and reuse it,
so a nested model does not restart deduplication.

**A process-lifetime scope is explicitly rejected.** It would make the second
identical response decode silently clean: the first `get_instruments()` of the process
would report, and every subsequent one would emit nothing, so a consumer who attaches
a handler after startup — or who only inspects logs from the second request onward —
sees a clean decode of a divergent payload. That is a false pass, which is precisely
what this milestone exists to eliminate. For the same reason the dedupe set MUST NOT
be a module-level global.

---

## Lock 7 — Emission timing and ordering

**Emit eagerly at the first occurrence** of a dedupe key within the scope; suppress
every later occurrence of the same key. There is no flush, no buffer and no
end-of-scope pass.

**No `occurrences` counter is carried.** RESEARCH's draft record proposed a seventh
`occurrences` key. It is dropped, for three reasons stated here so the omission is not
mistaken for an oversight:

1. A true multiplicity cannot be known at first emission, so carrying it requires
   deferring emission to a **flush phase** at scope close.
2. A flush phase requires **two emission modes** — request-scoped (flushed by
   `_request`) and self-owned (flushed by the outermost `walk_model`) — doubling the
   surface where a scope-lifetime bug can hide.
3. Buffered records are **lost if the process dies mid-decode**, which is exactly the
   run you most want the records from.

The phase criterion asks for **exactly one record per divergent field**, not for a
count. Aggregate counting is Phase 33's job, via the findings pipeline, over records
that are already on disk.

**Emission order is deterministic.** Within one `walk_model`:

1. `extra` keys first, in **sorted key order** (`sorted(set(payload) - declared)`);
2. then declared fields in `dataclasses.fields()` **declaration order**;
3. recursing **depth-first** into nested models and list elements as each declared
   field is reached.

The result is stable across runs for the same payload, which makes a test able to
assert on the record sequence rather than only on a set, and makes two log files from
two runs diffable.

---

## Lock 8 — `non_dict` is terminal for reporting

When a payload is not a `dict`, emit **exactly one** `non_dict` record for that model
and **suppress the per-field `missing` records** the substitution would otherwise
imply. The walker still returns the per-package default shape unchanged
(`{}`-substitution for higyrus/market-data, `cls.empty()` for matriz — see
`29-SEMANTICS-MATRIX.md` Section 2); only the reporting is suppressed.

Without this rule a legitimate 204 response or a `null` body emits one `WARNING` per
declared field — 21 records for a single `higyrus.PosicionValuada`, none of which
carries information beyond "the payload was not a dict."

**An empty dict `{}` is a dict.** It does **not** produce a `non_dict` record, and it
**does** report per-field `missing` — because an empty object where a populated one
was expected is a real, per-field modelling signal, not a shape error.

---

## Lock 9 — Emitter safety

The emit call MUST be wrapped so that a failure inside `logging`, inside a consumer's
handler, or inside a consumer's filter can **never** propagate into the decode return
path. The decode returns its value regardless of what the logging stack does.

Observable mode raising from its own emitter is the inversion of the entire policy
change: a library that previously substituted silently would begin crashing on the
divergences it was added to merely report, and the crash would originate in third-party
handler code the library does not control. Lock 1's reserved-name discipline removes
the known `KeyError`; lock 9 covers the unknown remainder.

This wrapping applies to the **observable** emission only. Strict mode's raise is the
intended control flow and is not suppressed.

---

## Lock 10 — Findings compatibility (D-06)

The six keys MUST be consumable by
`verification/findings.py::append_finding` (`:583`) in Phase 33 **without
translation**. The target finding class is **`SHAPE`**, the first entry of
`FINDING_CLASSES` (`verification/findings.py:77`) and the correct class for a decode
divergence.

Mapping, to be implemented by Phase 33's `verification/divergences.py` handler:

| Record key | `append_finding` parameter | Note |
|---|---|---|
| `package` | `pkg` | Logger name → package slug (`higyrus_client` → `higyrus-client`); the slug must satisfy `_PKG_SLUG_RE`. |
| `divergence` | contributes to `title` and to `fid` | The kind is the finding's discriminator alongside the path. |
| `field_path` | contributes to `surface` and `title` | The path is what makes the finding actionable and is the stable half of the dedupe identity. |
| `declared_type` | `expected` | "the model declares `float`". |
| `observed_type` | `actual` | "the wire sent `NoneType`". |
| `model` | contributes to `surface` | Together with `field_path`, names the exact decode site. |
| — | `diff` | Composed by the handler from `declared_type` / `observed_type`; no new record key needed. |
| — | `class_` | Constant `"SHAPE"`. |
| — | `status` | Constant `"OPEN"` on first write; `append_finding` preserves human-promoted statuses. |

Phase 33 should call `append_finding` with `idempotent_by_title=True` so that the same
divergence discovered by two different drivers does not produce two findings — the
cross-driver counterpart to lock 5's within-scope dedupe.

---

## Lock 11 — Redaction posture (D-05)

**The record contract is the primary control. The `RedactingFilter` fix is defense in
depth.**

State plainly: **no change to the filter makes a wire value safe to log.** The
redaction passes are marker-anchored regexes — `Bearer\s+…`, `("password"\s*:\s*")[^"]+`,
`cuit=…` and their siblings (`higyrus_client/_logging.py:68-75`), driven by the literal
marker tuple at `:58-65`. A bare credential, a bare account identifier or a bare CUIT
in a record field matches **none** of them and ships intact to every downstream
handler. The repo already has a test asserting an identifier-shaped `extra` value is
deliberately *not* redacted (`higyrus-client/tests/test_logging.py:166-178`).

Therefore the guarantee is carried by the schema in lock 1: **flat, all-str,
top level, type-not-value, never the wire value.** `declared_type` and `observed_type`
carry type *names*; `field_path` and `model` carry *identifiers from our own source
code*, never payload content. There is no key in which a wire value can travel.

The filter fix remains worth doing — it closes the nested-container gap for *other*
callers' `extra` dicts — but it is not what protects this record. Per-package caplog
sentinels (×5, following the SEC-01 pattern in
`verification/test_logging_no_token_leak.py:41-90`, relocated in-package per Pitfall 10)
assert a credential literal is absent from `record.getMessage()`, `str(record.args)`
**and** `record.__dict__`.

---

## Lock 12 — Filter recursion bound

The `RedactingFilter` fix traverses nested containers (`dict` / `list` / `tuple`)
rebuilding them with redacted string leaves. That traversal MUST carry:

- an explicit **recursion depth bound of 4** — beyond depth 4 the container is left
  untouched;
- a **container size skip at more than 64 entries** — a `dict` or sequence with more
  than 64 entries is left untouched rather than walked.

A log filter runs on every record on the emitting thread. An unbounded traversal turns
it into a latency amplifier, and a hostile or merely enormous payload placed in some
other caller's `extra` dict turns it into a CPU sink. The bounds cost nothing for the
divergence record itself, which is flat by lock 1 and therefore never recurses at all.

Both bounds MUST be named constants with a comment citing this lock, so a future reader
does not "clean up" the magic numbers.

---

## Deviation from the research draft, under signature

The record carries **six** keys and **no** occurrence counter. `29-RESEARCH.md`
proposed a seven-key record including `occurrences`. The reasoning for dropping it is
lock 7. This deviation is called out here explicitly because it is under the same
signature as locks 4 and 5.

---

## Signature

Both lock 4 and lock 5 are one-way doors. Phase 33 runs the drivers in strict mode
against lock 4 and budgets its findings against it; Phases 30-34 write model surface
and tooling against the record schema in lock 1. Reversing either after Phase 30 means
re-editing already-shipped public surface and re-publishing wheels in Phase 34.

Signed:
Date:
Decision recorded:
