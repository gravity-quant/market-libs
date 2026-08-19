# Phase 29 — The 6-way `from_api` semantics matrix (D-07)

**Status:** authoritative policy artifact
**Written:** 2026-08-19
**Source tree:** branch `milestone/v1.5-mutations` @ `c5cedd7`
**Governs:** every `_decode.py` copy created by Phase 29 Plans 02-10, and the
`DecodePolicy` constant inside each copy.

D-07 requires this table to exist **before any decoder code is written**. Plan 02's
walker is a transcription of Section 2; Plan 02's exemption branches are a
transcription of Section 3. Every cell below was read off the working tree during
this plan's execution — the line ranges are the *verified* ones, not the ones quoted
in `29-RESEARCH.md` (RESEARCH cites `matriz models.py:106-116` for `from_api`; the
verified `def` line is `107`, and RESEARCH's `_convert:76-93` is verified as `74-92`).

---

## Section 1 — the 6-way table

Six `from_api` implementations exist across the three packages that have a
`models.py` today. There is no seventh: `iol-client` and `ambito-financiero-client`
have no `models.py` (Phase 30 / never), and `wallets-client` is the D-02 exemption.

| # | Implementation | Location (`file:line-range`) | missing scalar | missing `list[X]` | missing nested model | non-dict payload | `Optional[T]` | scalar handling | slots? | `empty()`? |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `SafeModel.from_api(payload)` | `packages/higyrus-client/src/higyrus_client/models.py:38-45` (`@classmethod` at `:37`; + `_coerce:48-89`) | typed zero — `""` / `0` / `0.0` / `False` | `[]` (`_coerce:63-67`) | `X.from_api(None)` (`_coerce:69-70`) | `{}` substituted at `:40`, then every field takes its typed-zero default | stays `None` (`_coerce:55-57`) | coerced by declared type; `bool`-is-`int` guard at `:79-80` prevents `cantidad=True` | **yes** (`@dataclass(frozen=True, slots=True)`) | no |
| 2 | `SafeModel.from_api(payload)` | `packages/market-data-client/src/market_data_client/models.py:74-81` (`@classmethod` at `:73`; + `_coerce:84-125`) | identical to #1 | identical to #1 | identical to #1 | identical to #1 (`:76`) | identical to #1 | identical to #1; the guard comment reads `size=True` instead of `cantidad=True` (`:113`) | **yes** | no |
| 3 | `MarketDataSnapshot.from_api(payload, *, received_at=0.0)` | `packages/market-data-client/src/market_data_client/models.py:151-168` (`@classmethod` at `:150`) | as #2 | as #2 | as #2 | as #2 (`:160`) | as #2 | as #2 **except `received_at`, which bypasses `_coerce` entirely** and is injected from the keyword (`:164-165`) | yes (class at `:128-129`) | no |
| 4 | `Symbol.from_api(payload)` | `packages/market-data-client/src/market_data_client/models.py:486-502` (`@classmethod` at `:485`) | as #2 | as #2 | as #2 | as #2 (delegates) | as #2 | as #2, **after** mirroring wire `market_id` → `marketId` when `marketId` is absent (`:495-496`); delegates via explicit two-arg `super(Symbol, cls)` (`:502`) | yes (class at `:438-439`) | no |
| 5 | `_SafeModel.from_api(data)` | `packages/matriz-client/src/matriz_client/models.py:107-111` (`@classmethod` at `:106`; + `_convert:74-92`, `_strip_optional:61-67`) | **`None`** — falls through to the bare `return value` at `_convert:92` | `[]` (`_convert:79-84`) | `X.empty()` (`_convert:89-90`) | **`cls.empty()` — early return at `:108-109`**, never `{}` | unwrapped by `_strip_optional` before dispatch (`_convert:76`) | **pass-through, unvalidated** — no `str`/`int`/`float`/`bool` branch exists; `_convert` ends in `return value` | **no** (`@dataclass(frozen=True)`, no `slots`) | **yes** (`:113-116`) |
| 6 | `UnknownFrame.from_api(data)` | `packages/matriz-client/src/matriz_client/models.py:384-387` (`@classmethod` at `:383`; class `:370-391`) | n/a — only 2 declared fields (`type`, `raw`) | n/a | n/a | `cls()` — both fields take their dataclass defaults (`:385-386`) | `type: str \| None = None` is a plain default, never coerced | **the entire payload is retained** as `raw = dict(data)` (`:387`) — no per-field walk at all | no | **yes**, hand-written (`:389-391`) |

### Companion table — the two `empty()` implementations

`empty()` is a matriz-only concept. It is the non-dict fallback for rows 5 and 6 and
therefore part of the decode contract, not a convenience constructor.

| Implementation | Location | Behavior |
|---|---|---|
| `_SafeModel.empty()` | `packages/matriz-client/src/matriz_client/models.py:114-116` (`@classmethod` at `:113`) | Resolves hints, then calls `_convert(hint, None)` for every field. Because `_convert`'s scalar path is a bare pass-through, every scalar field lands on `None`; `list[X]` lands on `[]`; nested models recurse into their own `empty()`. |
| `UnknownFrame.empty()` | `packages/matriz-client/src/matriz_client/models.py:390-391` (`@classmethod` at `:389`) | Hand-written `return cls()` — relies on the dataclass field defaults (`type=None`, `raw={}` via `default_factory=dict`). Does **not** inherit `_SafeModel`; it satisfies the same duck-typed contract by hand. |

### Byte-level status of rows 1 and 2

The `SafeModel` + `_coerce` blocks of higyrus and market-data are both **2107
characters** and differ in exactly two lines — a docstring noun (`"Higyrus"` vs
`"market-data"`) and one comment noun (`"cantidad=True"` at higyrus `:78` vs
`"size=True"` at market-data `:113`). They are near-verbatim but **not**
byte-identical. This is why the Plan 09 intactness check must be
*normalize-then-hash*, never a raw byte comparison.

---

## Section 2 — derived policy axes (`DecodePolicy`)

The table above is translated into exactly seven fields on the frozen `DecodePolicy`
dataclass that every `_decode.py` copy carries. The class body is **identical in all
five copies**; only the `POLICY` constant's value differs. That constant, the module
docstring's package name, and the logger-name literal are the only three per-package
deltas the intactness check normalizes away.

### Field list

| Field | Type | Meaning |
|---|---|---|
| `missing_str` | `str \| None` | Value substituted when a `str`-declared field is absent or wrong-typed. |
| `missing_int` | `int \| None` | Value substituted when an `int`-declared field is absent or wrong-typed. |
| `missing_float` | `float \| None` | Value substituted when a `float`-declared field is absent or wrong-typed. |
| `missing_bool` | `bool \| None` | Value substituted when a `bool`-declared field is absent or wrong-typed. |
| `non_dict_model` | `str` | Which fallback a non-dict payload takes: `"from_api_none"` (walk every field with `None`, i.e. `{}` substitution) or `"empty_classmethod"` (early-return `cls.empty()`). |
| `scalar_passthrough` | `bool` | `True` = scalars are returned unchanged regardless of declared type (matriz); `False` = scalars are coerced to the declared type. |
| `literal_enforced` | `bool` | Whether `Literal` membership is enforced. **Not a tunable — see below.** |

RESEARCH's Pattern 2 sketch collapsed `int` and `float` into one `missing_num` field.
That collapse is rejected here: higyrus/market-data `_coerce` returns `0` for `int`
and `0.0` for `float` on two separate branches (`:81` and `:87`), and the `bool`
guard differs between them (`:79-80` returns `0`, `:83-84` returns `0.0`). A single
`missing_num` would force the walker to re-derive which zero to hand back, which is
exactly the kind of implicit rule D-07 exists to eliminate. Four separate scalar
fields make the substitution table readable straight off the constant.

### Concrete constants per package

| Package | `missing_str` | `missing_int` | `missing_float` | `missing_bool` | `non_dict_model` | `scalar_passthrough` | `literal_enforced` |
|---|---|---|---|---|---|---|---|
| `higyrus-client` | `""` | `0` | `0.0` | `False` | `"from_api_none"` | `False` | `False` |
| `market-data-client` | `""` | `0` | `0.0` | `False` | `"from_api_none"` | `False` | `False` |
| `matriz-client` | `None` | `None` | `None` | `None` | `"empty_classmethod"` | `True` | `False` |
| `iol-client` | `""` | `0` | `0.0` | `False` | `"from_api_none"` | `False` | `False` |
| `ambito-financiero-client` | `""` | `0` | `0.0` | `False` | `"from_api_none"` | `False` | `False` |

As literal source lines:

```python
# higyrus-client / market-data-client / iol-client / ambito-financiero-client
POLICY = DecodePolicy("", 0, 0.0, False, "from_api_none", False, False)

# matriz-client
POLICY = DecodePolicy(None, None, None, None, "empty_classmethod", True, False)
```

**iol and ambito carry the higyrus/market-data constant even though neither has a
`models.py` today.** The constant is inert in both packages — nothing calls the
walker until a model exists — but it must be present so the file stays verbatim
across all five copies and the intactness check has one canonical shape to normalize
to. **iol's value is re-ratified when Phase 30 adds `iol_client/models.py`**: the
Phase 30 planner must confirm that the models it writes actually want typed-zero
substitution rather than matriz-style `None`, and record that confirmation. Ambito's
value is expected to stay inert indefinitely — its single public function returns a
`float`, not a model.

### `literal_enforced` is not a tunable

`literal_enforced` is `False` in all five copies, in every branch, permanently within
this milestone. It is a field on `DecodePolicy` rather than a hard-coded `False`
purely so that the walker's `Literal` branch reads against a named policy value
instead of a bare constant — but **no package may set it to `True`**, and no future
plan in Phase 29 may introduce a copy where it differs. The value is fixed by D-09
and by `29-DLOCK-RESPONSE-LITERAL.md`; changing it is a public-surface behavior break
on already-published wheels (matriz `_convert` passes `Literal`-typed fields through
unvalidated today, at `models.py:92`), and it would produce a divergence storm on
legitimate vendor enum growth. Plan 09's ban-list grep should treat
`literal_enforced=True` as a violation.

---

## Section 3 — exemptions the policy constant cannot express

Three behaviors are per-model, not per-package. A `DecodePolicy` constant cannot
carry them, so the walker needs an explicit branch or the call site keeps its
existing code verbatim. Each is cited to its source line.

### (a) `MarketDataSnapshot.received_at` — injection bypass

**Source:** `packages/market-data-client/src/market_data_client/models.py:164-165`

```python
            if field.name == "received_at":
                kwargs[field.name] = received_at  # INJECT — skip _coerce (D-01)
```

`received_at` is a **client-side stamp**, not a wire field. It arrives through the
keyword-only parameter on `MarketDataSnapshot.from_api(payload, *, received_at=0.0)`
(`:151`) and must **never** be routed through the walker. Routing it would collapse
the stamp to `0.0` whenever the payload omits the key, and — worse — would let a wire
`received_at` value win over the client stamp, which is the D-01 fidelity contract
this branch exists to protect (docstring at `:152-159` states it explicitly).

**Walker obligation:** the `received_at` field of `MarketDataSnapshot` is skipped
entirely — no walk, no divergence record, not even an `extra` record if the wire
carries the key. The `if field.name == "received_at":` branch stays verbatim.

**Near-miss to guard against:** `Symbol` also declares `received_at`
(`models.py:483`, `received_at: str | None = None`), but there it is a genuine wire
field carrying the server's ingest timestamp — same name, opposite provenance. The
exemption is scoped to `MarketDataSnapshot` only. A field-name-keyed exemption list
that is not also class-keyed would silently break `Symbol`.

### (b) `Symbol.from_api` — wire key mirror + two-arg `super()`

**Source:** `packages/market-data-client/src/market_data_client/models.py:495-502`

```python
        if isinstance(payload, dict) and "marketId" not in payload and "market_id" in payload:
            payload = {**payload, "marketId": payload["market_id"]}
        # Explicit two-arg ``super()``: ``@dataclass(slots=True)`` REBUILDS the
        # class, so the implicit ``__class__`` cell captured by a zero-arg
        # ``super()`` still points at the pre-slots class and raises
        # ``TypeError: obj must be an instance or subtype of type``. The module
        # global ``Symbol`` is rebound to the slots class, so naming it works.
        return super(Symbol, cls).from_api(payload)
```

Two separate exemptions live in these eight lines.

**The pre-processing hook (`:495-496`):** the wire never sends `marketId`; the mirror
fills the deprecated alias from `market_id` so it does not stay `""` forever and
silently contradict `market_id`. It runs **before** the walker sees the payload,
which has a direct consequence for extra-key reporting: after the mirror, `marketId`
is a declared field with a present key, so no `extra` record fires for it — correct,
because the key was synthesized by the client, not received from the vendor. An
explicit `marketId` already in the payload still wins; the mirror only fills an
absent key.

**The two-arg `super()` (`:497-502`):** `@dataclass(slots=True)` **rebuilds** the
class object, so the implicit `__class__` cell captured by a zero-arg `super()` still
points at the pre-slots class and raises `TypeError: obj must be an instance or
subtype of type`. This is a bug the repo already hit and documented in place. Any
plan in Phase 29 that touches a `from_api` override **keeps the explicit two-arg
`super(Cls, cls)` form**. A diff that changes `super(Symbol, cls)` to `super()` is a
regression, not a cleanup. This affects market-data and higyrus only — matriz models
are `@dataclass(frozen=True)` with no `slots` (verified: `models.py:369` decorates
`UnknownFrame`, and no matriz model carries `slots=True`), so they are structurally
immune. That asymmetry is itself row 5's `slots?` cell.

### (c) `UnknownFrame` — deliberate catch-all, exempt from extra-key reporting

**Source:** `packages/matriz-client/src/matriz_client/models.py:383-387`

```python
    @classmethod
    def from_api(cls, data: Any) -> Self:
        if not isinstance(data, dict):
            return cls()
        return cls(type=data.get("type"), raw=dict(data))
```

`UnknownFrame` is a plain `@dataclass(frozen=True)` that does **not** inherit
`_SafeModel` (class declaration at `:370-371`). It implements the `from_api` / `empty`
duck-typed contract by hand and stores the entire payload in `raw`. It is the
catch-all for WebSocket frames whose `type` is not modeled, and its docstring
(`:372-378`) states the intent: preserve the raw payload so callers can inspect
forward-compatible fields without losing information.

**Walker obligation:** `UnknownFrame.from_api` is left untouched and is **exempt from
extra-key reporting entirely**. Under a naive extra-key rule every key of every
unknown frame is "extra" — but those keys are a deliberate catch-all, not a modelling
gap, and reporting them would emit one `extra` record per key on every unmodeled
frame the WebSocket delivers. There is also no per-field walk to hook: the method
declares two fields and copies the payload wholesale.

---

## Never harmonize

**No row of the table in Section 1 is a bug to be fixed in Phase 29.**

Every difference between rows — matriz's `None` where higyrus substitutes `""`,
matriz's `cls.empty()` where higyrus substitutes `{}`, matriz's unvalidated scalar
pass-through, matriz's absence of `slots`, `MarketDataSnapshot`'s extended signature,
`Symbol`'s key mirror, `UnknownFrame`'s raw retention — is a **declared policy axis**
with a `file:line` citation above, not an inconsistency awaiting cleanup.

This matters because the five `_decode.py` copies are byte-verbatim by design (C-2,
D-02, DT-03). A verbatim copy plus an implicit semantic makes harmonization the path
of least resistance: the first executor to notice that matriz returns `None` where
higyrus returns `""` will be tempted to "fix" it, and the change will look like a
one-line diff rather than what it is — a silent behavior break on published wheels
whose consumers already depend on the current substitution. The `DecodePolicy`
constant is the mechanism that makes divergence *declared* rather than accidental:
there is no unparameterized code path in the walker, so a harmonization requires
editing a named constant in a named package, which is visible in review.

The zero-edit merge gate is the mechanical counterpart: **872 tests across the three
`SafeModel` packages must stay green without a single test file being edited**
(DT-05). Any harmonization of a cell above breaks that gate by construction.

**Any future change to a cell in this table is a separate decision with its own
artifact and its own operator signature.** It is not in scope for Phase 29, it is not
a refactor, and it may not be folded into an unrelated plan.

---

## Traceability

| Section | Consumed by |
|---|---|
| Section 1 (6-way table) | Plan 02 (`_decode.py` walker branch order), Plan 09 (intactness normalization rules) |
| Section 2 (`DecodePolicy` fields + constants) | Plan 02 (class body), Plans 03-07 (per-package `POLICY` constant), Plan 09 (ban-list grep on `literal_enforced=True`) |
| Section 3 (exemptions) | Plan 02 (`walk_model` exemption branches), Plan 05 (matriz `UnknownFrame`), Plan 06 (market-data `MarketDataSnapshot` / `Symbol`) |
| "Never harmonize" | Phase 29 verification, Phase 33 findings triage |
