# Pitfalls Research

**Domain:** Retrofitting strict/typed, observable decoding onto tolerant, already-published financial-API client libraries (6 standalone wheels, no shared code)
**Researched:** 2026-08-18
**Confidence:** HIGH for msgspec behavior (verified empirically against `msgspec 0.21.1` on CPython 3.12.13 + upstream docs) and for repo-state claims (read directly from source at `milestone/v1.5-mutations` head). MEDIUM for divergence-volume predictions (depends on live payloads not yet observed).

---

## How this file was verified

Every msgspec claim below was produced by running the case, not by reading about it. Environment:

```
uv run --no-project --python 3.12 --with 'msgspec==0.21.1' python <probe>
# msgspec 0.21.1 (uploaded 2026-04-12), py 3.12.13
# 48 wheels published: cp310/cp311/cp312/cp313/cp314 × macOS(x86_64,arm64) / manylinux / musllinux / win-amd64 + sdist
```

Every repo claim cites a file and, where it matters, a line. Two claims in the source plan (`.planning/future-plans/tipado_homogeneo.md`) were **measured false** and are called out as Pitfalls 1 and 7.

---

## Critical Pitfalls

### Pitfall 1: "`SafeModel`/`_coerce` duplicado verbatim ×3" is false — matriz has the OPPOSITE semantics

**What goes wrong:**
Phase 29 replaces "the three copies" of `_coerce` with one msgspec-backed decoder and treats them as interchangeable. They are not. Two of the three zero-default; the third passes values through untouched.

| Package | Base class | Coercer | Missing `str` | Missing `float` | Missing nested | Missing `dict` | dataclass flags |
|---|---|---|---|---|---|---|---|
| `higyrus_client` | `SafeModel` (public, in `__all__`) | `_coerce` | `""` | `0.0` | `X.from_api(None)` | n/a | `frozen=True, slots=True` |
| `market_data_client` | `SafeModel` (public, in `__all__`) | `_coerce` | `""` | `0.0` | `X.from_api(None)` | n/a | `frozen=True, slots=True` |
| `matriz_client` | `_SafeModel` (**private**, not exported) | `_convert` | **`None`** | **`None`** | `X.empty()` | `{}` | `frozen=True` — **no `slots`**, uses `field(default_factory=...)` |

`matriz_client/models.py::_convert` ends with a bare `return value` — scalars are never coerced. Its own docstring says so: *"missing scalars become `None`, missing dicts become `{}`"*. It also exposes an `empty()` classmethod that `higyrus`/`market-data` do not have, and that classmethod is **called inside the class bodies** (`instrumentId: InstrumentId = field(default_factory=InstrumentId.empty)`) — removing it breaks import, not just decode.

So there are **two** contracts to preserve under DT-05, not one. A single decoder that zero-defaults will silently turn every absent matriz scalar from `None` into `0.0` — on a package whose untyped-surface count is already **0** and which therefore gains nothing from this milestone.

**Why it happens:**
The plan's evidence table says "`SafeModel` + `_coerce` **duplicados verbatim** (~90 LOC × 3)". That statement was inherited, not re-measured. The drift is real and predates this milestone — which is itself the strongest possible argument for Pitfall 17.

**How to avoid:**
- Phase 29 task 1 is a three-way `diff` of the three model bases, producing a written semantics table (the one above) checked into the phase artifacts *before* any decoder is written.
- The decoder takes the default-policy as a parameter (`zero_defaults: bool` or a policy object), copied 6× with the per-package value baked in. Do not "harmonize" matriz onto zero-defaults in this milestone — that is a silent behavior change on a published package outside the milestone's stated scope.
- The DT-05 merge gate must be run **per package, on all three suites, with zero test edits**. matriz's suite pins the `None`/`empty()`/`{}` contract; higyrus's and market-data's pin `""`/`0.0`/`[]`. If any of the three needs a test edit to go green, the contract broke.

**Warning signs:**
A Phase-29 plan that says "replace `_coerce` in the 3 packages" in one task. A matriz test asserting `is None` being changed to `== 0.0`. A reviewer comment saying "this test was wrong anyway".

**Phase to address:** 29 (measurement + policy parameter + three-suite merge gate).

---

### Pitfall 2: matriz's `Literal`-typed **response** fields become runtime-enforced and flood Phase 33

**What goes wrong:**
`matriz_client/models.py` annotates response fields with `Literal` aliases from `types.py`: `Instrument.cficode: CFICode | None`, `Order.ordType: OrderType | None`, `Order.side: Side | None`, `Order.status: OrderStatus | None`, `Order.timeInForce: TimeInForce | None`, `InstrumentDetail.currency: Currency | None`, `InstrumentDetail.orderTypes: list[OrderType]`, `Segment.marketSegmentId: SegmentId | None`, `marketId: MarketId | None`.

Today these are **decorative** — `_convert` returns the raw value untouched, so an exchange sending a new CFI code, a new order status, or an undocumented segment id flows through as a plain `str` and nothing notices. Under msgspec they become hard validation:

```
msgspec.convert({"marketId": "XXXX"}, type=Seg)
→ ValidationError: Invalid enum value 'XXXX' - at `$.marketId`   [verified, 0.21.1]
```

MATBA ROFEX adds instruments, segments and order states over time. The first strict run against remarkets can produce a divergence per row on `get_instruments` / `get_orders` for a reason that is **not a bug** — the `Literal` set was written from a PDF spec in v1.0, never from a live census.

**Why it happens:**
DT-07 ("the `Literal` set comes from live verification, never assumptions; an incomplete `Literal` breaks legitimate calls") is written as a **parameter** rule. Nobody re-reads it as a **response-field** rule, because the response `Literal`s already exist and predate the decision.

**How to avoid:**
- Phase 29 makes an explicit D-lock on response-side `Literal`s. Recommended: decode them as `str` internally and *report* an out-of-set value as a divergence (observable), rather than letting msgspec raise. That keeps DT-02's "silencioso → observable, NO tolerante → fatal" honest for a case that today is tolerant.
- If they stay `Literal`, they must be re-derived from live evidence in Phase 33 exactly like `mercado`/`plazo`, and matriz joins the DT-08 release list it otherwise would not.
- Do the same audit for `market_data_client` and any Literal introduced in Phases 30-31.

**Warning signs:**
Phase-33 findings dominated by `Invalid enum value` on matriz. Any Phase-29 plan whose Literal discussion mentions only `mercado`/`plazo`.

**Phase to address:** 29 (D-lock + decode policy), 33 (live census if kept).

---

### Pitfall 3: msgspec is fail-fast — one error per decode — so the Phase-29 sizing run undercounts

**What goes wrong:**
The plan's central risk mitigation is *"correr el modo estricto de forma exploratoria al final de Phase 29 para dimensionar el volumen real"*. msgspec reports **the first error and stops**:

```
msgspec.convert({"a":"x","b":"y","c":"z"}, type=Multi)
→ ValidationError: Expected `int`, got `str` - at `$.a`        [b and c never inspected]

msgspec.json.decode(b'[{ok},{bad}]', type=list[Quote])
→ ValidationError: Object missing required field `ultimoPrecio` - at `$[1]`   [rows 2..N never inspected]
```

A payload with 5 divergent fields reports 1. A 5000-row list with 400 bad rows reports 1. The sizing number that authorizes committing Phases 30-32 will be an order of magnitude low, and Phase 33 becomes serialized whack-a-mole: fix one, re-run, discover the next.

**Why it happens:**
The natural implementation is `try: msgspec.convert(...) except ValidationError as e: log(e); return from_api(payload)`. It is correct, it is observable, and it structurally cannot enumerate.

**How to avoid:**
- The decoder needs an **enumerating** mode distinct from the runtime observable mode: on failure, walk the declared fields and probe each one independently (`msgspec.convert({k: v}, type=SingleFieldShim)` or a per-field `convert(value, type=hint)`), collecting all divergences. Per-row for collections. Cost is bounded — measured below — and it only runs when the fast path already failed.
- The sizing report says **"≥ N"**, never "N", and states the enumeration mode used.
- Phase 33's budget assumes the sizing number is a floor.

**Warning signs:**
A sizing report with a suspiciously round small number. A Phase-33 loop where each fix reveals exactly one new divergence in the same endpoint.

**Phase to address:** 29 (enumerating mode + honest sizing), 33 (budget).

---

### Pitfall 4: log-spam flood — one divergence record per row on a 5000-row response

**What goes wrong:**
`iol.get_instruments("argentina")` returns the country-wide instrument list (today typed `-> Any`; `main_iol.py` logs only `type={type(data).__name__}` because it never counts it). `market_data.get_symbols` / `get_calendar` return catalogs. Live-measured higyrus row counts from v1.1 Phase 9: `get_posicion_valuada` = 390, `get_movimientos` = 139, and those were a single account. One structural divergence (a renamed field, a `null` where a `float` was declared) is present on **every row**, so a naive per-row emitter produces one record per row per call.

Measured cost (5000 rows, `frozen=True, slots=True` dataclass, msgspec 0.21.1 / py3.12.13):

```
msgspec.json.decode(bytes, type=list[Row])  = 1.35 ms
msgspec.convert(list, type=list[Row])       = 0.79 ms
per-row msgspec.convert in a Python loop    = 2.06 ms
```

Decoding is free. The cost is **`logging.LogRecord` construction + `RedactingFilter`**, which runs 4 `re.sub` passes plus a full `record.__dict__` scan **per record** — and filters attached to the package logger run for every record that survives the level check, before any handler. With a consumer's Sentry/Datadog handler attached to `logging.getLogger("iol_client")`, a 5000-record burst per call is an incident, not a log line.

**Why it happens:**
"Emit a structured divergence" reads as a per-occurrence operation. Nobody sizes it against the widest endpoint.

**How to avoid:**
- Aggregate before emitting. Key = `(endpoint_name, json_path_normalized, expected_type, got_type)`; `json_path_normalized` collapses list indices (`$[1731].price` → `$[*].price`). Emit **one** record per distinct key per response, carrying `count` and `first_index`.
- Hard cap distinct keys per response (e.g. 20) with a final `"... N more distinct divergences suppressed"` record.
- Guard construction: `if logger.isEnabledFor(logging.WARNING):` **before** building the payload. Never `logger.debug(json.dumps(payload))` — that serializes unconditionally.
- Merge gate for Phase 29: a mocked test decodes a 5000-row list where every row diverges the same way and asserts `len(caplog.records) == 1` and `record.count == 5000`. Assert the cap with 25 distinct divergence shapes.

**Warning signs:**
A `for row in rows: try/except: logger.warning(...)` shape. Any Phase-29 test whose fixture has fewer than ~100 rows.

**Phase to address:** 29.

---

### Pitfall 5: `RedactingFilter` does not cover the divergence-record shape — verified gap, not a hypothesis

**What goes wrong:**
Two independent holes, both read directly from `packages/*/src/*/_logging.py` (six near-identical copies):

**(a) Redaction is key-anchored.** `_redact()` only rewrites text that carries an anchoring token. Per package:

| Package | Anchors it can redact |
|---|---|
| `market_data_client` | `Bearer <tok>`, `client_secret=<v>`, `"client_secret":"<v>"`, `"access_token":"<v>"` |
| `iol_client` | `Bearer`, `X-Auth-Token`, `password=`, `"password"`, `refresh_token=`, `"refresh_token"`, `"access_token"` |
| `higyrus_client` | `Bearer`, `X-Auth-Token`, `password=`, `"password"`, `"token"`, **`cuit=`** |
| `matriz_client` | `Bearer`, `X-Auth-Token`, `X-Password`, `Authorization: Basic`, `password=`, `"password"` |

A divergence record quotes a **value**, not a key/value pair: `Expected 'float', got 'str' at $.token — value 'eyJhbGciOiJI...'` has no anchor, so **nothing redacts it**. The milestone question framed this exactly right: divergence records quote VALUES, and value-only text is outside every one of the six pattern sets.

**(b) The `extra=` scan only inspects `str`.** All six copies do:

```python
for key, value in list(record.__dict__.items()):
    if isinstance(value, str) and any(m in value for m in _REDACTION_MARKERS):
        record.__dict__[key] = _redact(value)
```

The idiomatic structured shape — `logger.warning("divergence", extra={"divergence": {...}})` — puts a **dict** in `record.__dict__`. It is never scanned, never redacted, and lands verbatim in whatever handler the consumer attached. Same for lists and tuples.

**(c) higyrus specifically.** `cuit=` is in higyrus's marker set: a CUIT is Argentine tax-ID PII on a brokerage back-office. A divergence on any field whose value happens to be a CUIT, emitted as a bare value, leaks PII with no marker to catch it.

**Why it happens:**
`RedactingFilter` was designed in v1.1 Phase 8 for *request/response debug strings* — text that always carries the header or JSON key next to the secret. Divergence records are a new record shape that violates that assumption. And the SEC-01 caplog no-leak sentinel (`verification/test_logging_no_token_leak.py`) tests the old shape, so it stays green while the new shape leaks.

**How to avoid:**
- **Contract, enforced by test: the divergence record never contains a wire value.** Emit `(endpoint_name, json_path, expected_type, got_type, count)` only. Type names, not values. If a value is ever genuinely needed for triage, emit `sha256(value)[:8]` and `len(value)`.
- Extend the `record.__dict__` pass in **all six** `_logging.py` copies to recurse into `dict` / `list` / `tuple` values. Do it in one commit (Pitfall 17).
- Add a per-package `caplog` no-leak sentinel for the **decoder** path, mirroring SEC-01: inject a payload whose divergent field's value is a sentinel token, assert the token appears in zero records. Six tests, one per package.
- Ban `logger.*(..., exc_info=True)` on the decoder path: the `ValidationError` message embeds the offending value for some type errors, and tracebacks are not filtered by content.

**Warning signs:**
`extra={"payload": ...}`, `extra={"value": ...}`, `repr(payload)` or `str(e)` anywhere in the emitter. A Phase-29 test that asserts the record *contains* the bad value (that test is a leak, inverted).

**Phase to address:** 29 (contract + filter recursion + 6 sentinels); re-verified in 33 when real credentialed payloads flow.

---

### Pitfall 6: `TYPE_CHECKING`-only annotations become a `NameError` at decode time

**What goes wrong:**
Every module in this repo carries `from __future__ import annotations` — CLAUDE.md calls it *"mandatory and applied uniformly"*. So all annotations are strings, and msgspec resolves them via `get_type_hints()` **when the type is first used for decoding**. A name imported only under `if TYPE_CHECKING:` resolves to nothing:

```python
if TYPE_CHECKING:
    from decimal import Decimal as _Hidden

@dataclass(frozen=True)
class TC:
    v: _Hidden | None = None

msgspec.convert({"v": None}, type=TC)
→ NameError: name '_Hidden' is not defined       [verified, 0.21.1 / py3.12.13]
```

Not at import. Not under mypy. Not in any test that does not decode that specific model. It surfaces in production, or in Phase 33 against a live API, as a `NameError` — which is neither observable-mode nor strict-mode, it is a crash.

**Why it happens:**
`if TYPE_CHECKING:` is the standard idiom for breaking import cycles, and Phase 32's AST surface gate creates pressure to add type imports to modules that did not have them.

**How to avoid:**
- `models.py` and `types.py` import every annotation name at **runtime**. No `TYPE_CHECKING` block in any module that defines a decodable model.
- One cheap, non-vacuous test per package that catches the entire class: enumerate every model class in the package and call `typing.get_type_hints(cls)` on each, asserting it does not raise. That single test also catches typo'd forward refs and stale imports.
- Phase 32's gate must operate on **AST**, not `get_type_hints()`, precisely so it cannot be satisfied by hiding an import (see Pitfall 15).

**Warning signs:**
`if TYPE_CHECKING:` appearing in a `models.py` diff. A gate implementation that imports the module to introspect it.

**Phase to address:** 29 (models + the get_type_hints sweep test), 31 (new models), 32 (gate design must not incentivize it).

---

### Pitfall 7: there is **no** working field rename for stdlib dataclasses in msgspec 0.21.1 — and both attempts fail SILENTLY

**What goes wrong:**
Verified, both cases, no exception raised:

```python
@dataclass(frozen=True)
class R2:
    ultimo_precio: float = msgspec.field(name="ultimoPrecio")
msgspec.convert({"ultimoPrecio": 1.5}, type=R2)
→ R2(ultimo_precio=<msgspec._core.Field object at 0x...>)     # sentinel object in a float field
msgspec.convert({"ultimo_precio": 1.5}, type=R2)
→ R2(ultimo_precio=1.5)                                        # the "rename" did nothing

@dataclass(frozen=True)
class R1:
    ultimo_precio: float = dataclasses.field(default=0.0, metadata={"msgspec": {"name": "ultimoPrecio"}})
msgspec.convert({"ultimoPrecio": 1.5}, type=R1)
→ R1(ultimo_precio=0.0)                                        # wire value silently dropped
```

`rename=` and `field(name=)` are `msgspec.Struct`-only; dataclass renaming is an open upstream request ([jcrist/msgspec#553](https://github.com/jcrist/msgspec/issues/553)). Neither failure mode raises. The first puts a `msgspec._core.Field` object where a `float` belongs — it will travel through the library, past mypy (the annotation says `float`), and blow up in consumer arithmetic.

**Corollary that matters more: `forbid_unknown_fields` is also `Struct`-only.** Extra/unknown keys are ignored on dataclasses in **every** mode, `strict=True` included ([verified](https://msgspec.dev/supported-types): *"extra fields ignored"*). The Phase-29 test list in the plan includes *"campo extra"* — **msgspec will never raise on it.** If that test asserts a divergence is emitted, it fails; if it asserts nothing is emitted, it is vacuous and gives false confidence that a renamed server field would be caught.

A renamed/new server field is one of the most likely real divergences (it is literally what killed `parse_latest_response` in Phase 25 WR-01 and what Phase 23's schema snapshots exist to catch). msgspec cannot see it.

**Why it happens:**
msgspec's docs lead with `Struct`; the dataclass support page mentions only `InitVar` as unsupported. The Struct feature set reads as the msgspec feature set.

**How to avoid:**
- Field names stay **camelCase verbatim**, matching the wire, in all six packages. The existing N815 per-file ignore is now **load-bearing, not cosmetic** — document it as such in `models.py` docstrings so a future tidy-up does not snake_case them.
- Grep gate: `msgspec.field(` must not appear in any `models.py`. (`dataclasses.field(` is fine and already used by matriz.)
- Implement **unknown-key detection by hand** in the decoder: `set(payload) - {f.name for f in fields(cls)}` → emit as a divergence with the key names (key names are safe to log; values are not — Pitfall 5). This is the piece that actually delivers "ninguna divergencia con la API en vivo sea silenciosa" for the schema-evolution case, and msgspec gives you none of it.
- The "campo extra" test must assert **the hand-rolled detector** fires, not msgspec.

**Warning signs:**
Any `models.py` diff that introduces snake_case field names. A `<msgspec._core.Field object>` in a test failure or a `main_*.py` probe output. A Phase-29 "extra field" test that passes on the first try without a hand-rolled detector.

**Phase to address:** 29.

---

### Pitfall 8: `msgspec.convert(resp.json())` and `msgspec.json.decode(resp.content)` are not interchangeable — and the difference is a `nan` price

**What goes wrong:**
Every parser in this repo goes through `resp.json()`, i.e. httpx → stdlib `json.loads`. Verified differences that matter for a market-data client:

| Case | `json.loads` → `msgspec.convert` | `msgspec.json.decode(bytes)` |
|---|---|---|
| `{"px": NaN}` | `json.loads` **accepts** it (`{'px': nan}`); `convert` then **accepts `float('nan')` into a `float` field with zero divergence** | `DecodeError: JSON is malformed: invalid character` |
| `{"px": Infinity}` | `json.loads` accepts (`inf`) | `DecodeError` |
| `{"px": 1.10}` → `Decimal` | `Decimal('1.1')` — routed through a Python float, scale lost | `Decimal('1.10')` — literal digits preserved |
| `{"ts": <python datetime>}` | accepted (`convert` takes real objects) | N/A |
| `{"ts": "2026-08-18T10:00:00"}` | accepted (naive) | accepted (naive) |
| `{"ts": "2026-08-18 10:00:00"}` | accepted | accepted |
| `{"ts": "18/08/2026"}` | `ValidationError: Invalid RFC3339 encoded datetime` | same |

The `NaN` row is the dangerous one. Python's `json.loads` accepts `NaN`/`Infinity`/`-Infinity` by default — they are not valid JSON, but stdlib emits and accepts them, and so do several JVM and .NET serializers upstream of financial feeds. A `float`-typed price field silently carrying `nan` is precisely the class of silent corruption this milestone exists to eliminate, and the strict decoder will report **nothing**.

The `Decimal` row is numerically harmless (`Decimal('1.1') == Decimal('1.10')`) but changes `as_tuple().exponent`, hence `str()`, `quantize()`, and any round-trip formatting.

**Why it happens:**
"msgspec decodes JSON" collapses two APIs with different front-ends. `convert` is the drop-in (it takes `resp.json()` output), so it will be chosen for free — along with `json.loads`'s permissiveness.

**How to avoid:**
- Pick one, D-lock it, copy it 6×. Recommendation: **`convert(resp.json())`** — it preserves the CR-03 / D-06 body-consume-then-raise ordering and the 204/empty-body guards already live in every parser, which `json.decode(resp.content)` would force you to re-verify across ~20 parsers.
- Then add the guard `convert` does not give you: for every `float`/`Decimal` field, `math.isfinite()` check → divergence if not. Cheap, and it closes the only hole the choice opens.
- If you instead choose `json.decode(resp.content)`: re-test every parser's 204 / empty-body / `null`-body path, and re-check `parse_calendar_write_response` and the mutation parsers whose bodies were live-shaped in Phase 27/28.
- Never pass `strict=False` (Pitfall 10).

**Warning signs:**
A price/quantity field that is `nan` in a driver probe output. A `Decimal` assertion that compares `str(px)` rather than the value.

**Phase to address:** 29 (D-lock + isfinite guard), 33 (live confirmation that NaN actually appears — or does not).

---

### Pitfall 9: `MarketDataSnapshot.received_at` client-stamping silently breaks under whole-object decoding

**What goes wrong:**
`market_data_client/models.py` documents D-01 explicitly: `received_at` is **client-stamped**, injected as a keyword directly in `from_api`, *"and never routed through `_coerce` (which would collapse it to `0.0`)"*. msgspec decodes the whole object in one call, so it has no seam to inject through. Verified consequences:

```python
msgspec.convert({"symbol": "X"}, type=Snap)        → Snap(symbol='X', received_at=0.0)   # stamp lost
msgspec.convert({"symbol":"X","received_at":1.0}, type=Snap) → received_at=1.0            # WIRE WINS
```

If the field is left required instead of defaulted: `ValidationError: Object missing required field 'received_at'` on every single response — a total outage of the read surface, discovered on the first live call.

The second row is the subtle one: the server sending a `received_at` key would **silently override the client stamp**, converting a client-side staleness measurement into a server-side one with no signal. And `market_data_client.Symbol` **also declares `received_at`**, but there it is a genuine wire field (the server's ingest timestamp) — same name, opposite provenance, documented in the module docstring. Any generic "strip `received_at` before decode / re-inject after" helper corrupts `Symbol`.

**Why it happens:**
The stamp is one line in `from_api` and reads as an implementation detail. The name collision with `Symbol.received_at` is documented in prose only.

**How to avoid:**
- Keep `from_api` as the seam: msgspec decodes a model **without** `received_at`, and `from_api` constructs the final frozen instance with the stamp (`dataclasses.replace` does not work on `slots=True` frozen classes as cheaply as re-constructing — measure, do not assume).
- Per-model opt-in, never a name-based rule. A `_CLIENT_STAMPED: ClassVar[frozenset[str]]` on the class, empty by default, `{"received_at"}` on `MarketDataSnapshot` only.
- Two regression tests: (1) a payload containing `received_at` must NOT override the stamp on `MarketDataSnapshot`; (2) a payload containing `received_at` MUST be read verbatim on `Symbol`.

**Warning signs:**
`received_at == 0.0` in any market-data driver output. A helper named `_strip_stamped_fields` that takes only a field name.

**Phase to address:** 29.

---

### Pitfall 10: `strict=False` is Pydantic-lenient coercion under another name, and it will look like a fix in Phase 33

**What goes wrong:**
Verified:

```python
msgspec.convert({"ultimoPrecio": "1.0"}, type=Quote, strict=False)          → ultimoPrecio=1.0
msgspec.convert({"cantidadOperaciones": "5"}, type=Quote, strict=False)     → cantidadOperaciones=5
```

This is *exactly* the behavior cited in the plan as the reason to reject Pydantic v2 (*"coerciona lenient por default (`"123.5"` → `123.5` silenciosamente — exactamente la divergencia a cazar)"*). It is one keyword argument away in msgspec. In Phase 33, facing a noisy string-typed price from a real feed at 2am, `strict=False` is the fastest way to make the noise stop — and it re-creates the silence the whole milestone was built to remove.

**Why it happens:**
The flag is called `strict`. Turning off "strict" reads like turning off pedantry, not like turning off the product requirement.

**How to avoid:**
- Grep gate in Phase 32: `strict=False` and `strict = False` must not appear in any `packages/*/src/`. Add it alongside the surface AST gate — one line, permanently.
- A string-shaped number on the wire is a **FINDING** to document and reconcile (the type annotation is wrong, or the server is wrong), never a flag flip.
- Note the asymmetry that makes this tempting: `int` → `float` widening is accepted in strict mode already (`{"ultimoPrecio": 3}` → `3.0`, verified), so strict mode is not brittle about the common case. Only genuine type mismatches raise.

**Warning signs:**
`strict=False` in any diff. A Phase-33 finding closed with "adjusted decoder leniency" rather than a model or server correction.

**Phase to address:** 29 (ban in the decoder), 32 (grep gate), 33 (the temptation point).

---

### Pitfall 11: iol `0.2.0 → 0.3.0` dict→model — the truthiness flip is the one that breaks silently

**What goes wrong:**
Migrating `get_quote -> dict[str, Any]` to `-> Quote` (frozen, slots) changes consumer behavior in five loud ways and **one silent** way:

| Consumer pattern | Old (`dict`) | New (`Quote`, frozen+slots) | Signal |
|---|---|---|---|
| `q["ultimoPrecio"]` | works | `TypeError: 'Quote' object is not subscriptable` | **LOUD** |
| `q.get("ultimoPrecio")` | works | `AttributeError: 'Quote' object has no attribute 'get'` (slots ⇒ no `__dict__`, so not even a stray attribute) | **LOUD** |
| `f(**q)` | works | `TypeError: argument after ** must be a mapping` | **LOUD** |
| `json.dumps(q)` | works | `TypeError: Object of type Quote is not JSON serializable` | **LOUD** |
| `for k in q` / `q.keys()` / `len(q)` | works | TypeError / AttributeError | **LOUD** |
| **`if not q:` / `if q:`** | `{}` is **falsy** | a dataclass instance is **always truthy** | **SILENT — behavior flips, no error** |

Any consumer using `if not quote:` or `if data:` as an emptiness/absence check inverts. That is the one to call out in the DT-08 README callout, because it is the only one a consumer cannot discover by running their tests unless they happen to hit the empty case.

Second-order: **`get_instruments` is annotated `-> Any` today.** mypy will flag *zero* call sites when it becomes `-> list[Instrument]`, because `Any` is compatible with everything. The other three functions (`dict[str, Any]`, `list[dict[str, Any]]`) do give a compile-time signal. So one of the four functions ships with no static migration aid at all.

**Why it happens:**
The loud failures dominate the review conversation, so the truthiness flip never comes up. And `Any → Model` feels like the *safest* migration when it is actually the least-instrumented one.

**How to avoid:**
- `main_iol.py` is the canary and must migrate in the **same commit**. Confirmed `.get()` sites: `main_iol.py:316` and `main_iol.py:395` (both `quote.get("ultimoPrecio")`). Note `:1182` / `:1192` are `committed.get("schema")` on the snapshot dict — **not** client output; do not migrate those.
- Do **not** add `__bool__`, `__getitem__`, or a `get()` shim to the models. They would hide exactly the break DT-08 says to advertise.
- Ship `to_dict()` on the new iol models as the documented one-line migration for JSON-serializing consumers. Precedent exists in-repo: market-data's request models (`HolidaysIn`, `NewSymbol`, `SymbolPatch`) already carry `to_dict()`.
- Survey consumers before Phase 30 — PROJECT.md already flags *"conviene relevar quién consume iol antes de Phase 30"*. Treat that as a Phase-30 entry gate, not a nicety.
- README changelog callout enumerates all six rows of the table above, with the truthiness row first.

**Warning signs:**
A Phase-30 plan whose migration section lists only `[]`/`.get()`. A `__bool__` or `keys()` method appearing on an iol model.

**Phase to address:** 30 (implementation + canary + `to_dict`), 34 (callout).

---

### Pitfall 12: `main_iol.py` hard-codes a source line reference inside a finding record

**What goes wrong:**
`main_iol.py:1027` contains:

```python
diff="client.py:254 hace data.get('titulos', []) y devuelve [] silenciosamente",
```

Phase 30 rewrites and renumbers `iol_client/client.py`. That string goes stale. Worse, it interacts with the HARN-07/08/09 findings machinery: `verification/findings.py` is append-only with **content-addressed `idempotent_by_title` dedupe** and cross-run preservation of operator fields (Classification / Rationale / Regression / Resolution). Change the text that feeds a finding's identity and you orphan the operator's disposition on the old record while creating a duplicate — and Phase 15 D-07 established a **static title-stability gate** (`git diff <baseline>..HEAD` over the `*-findings.md` files must show zero title/fid/probe-name changes) precisely because this is expensive to undo.

**Why it happens:**
It reads as a comment. It is data in an append-only ledger.

**How to avoid:**
- Before Phase 30 edits: `grep -rnE '(client|aio|_core)\.py:[0-9]+' main_*.py verification/` and inventory every hard-coded source coordinate.
- If a finding's identity text must change, follow the Phase-15 D-07 protocol explicitly (re-baseline + operator sign-off), do not just edit it.
- Prefer symbol references (`_core.parse_get_instruments_response`) over line numbers in any new finding text written in Phases 30-33.

**Warning signs:**
A `*-findings.md` diff in Phase 30 that was not intended. Duplicate findings with near-identical titles after a driver run.

**Phase to address:** 30.

---

### Pitfall 13: typing the **already-published** `add_holidays` / `delete_holiday` responses can perturb three live-verified contracts

**What goes wrong:**
`market-data-client v0.4.0` is publicly released. `add_holidays` / `delete_holiday` are live-verified mutations. TYP-02 wants their `-> dict[str, Any]` returns typed. Three distinct ways that goes wrong:

**(a) Touching the REQUEST while typing the RESPONSE.**
The request side is already typed: `add_holidays(self, holidays: HolidaysIn)` → `holidays.to_dict()` → `build_add_holidays_request(state, json_body)`. TYP-02 is a **response** job only. But `build_add_holidays_request`'s docstring records that `idempotent=True` was **corrected from `False` on measurement** during LIVE-MUT-01 (F-49/F-59: two identical POSTs left exactly 1 row for `2099-12-29` and 1 for `2099-12-30`, on both surfaces) — and D-20 states that the spec's prose alone was *never* sufficient authorization. Any change to `HolidaysIn.to_dict()` serialization changes what the server UPSERTs, and there is no cheap way to re-earn that measurement.

**(b) Displacing the mutation gate from the first statement.**
`_ensure_mutation_allowed()` is the **literal first statement** of every mutation method on both shells — `client.py:551, 562, 577, 619, 633, 653, 676, 698` and the `aio.py` mirrors at `562, 573, 588, 630, 644, 665, 688, 710`. This is AST-verified (`verification/test_main_market_data_no_gate_bypass.py`, in-package `tests/test_mutation_gate.py`), and Phase 25 proved adversarially with a force-expired token that a refused mutation emits **zero HTTP requests and zero Auth0 round-trips**. Inserting a validation line, a decoder warm-up, or a `models` lookup *above* that call breaks the invariant, and the failure mode is a request escaping before the gate.

**(c) Deleting the last proof that the non-idempotent short-circuit works.**
`_core.py` documents: *"no builder in this package carries `idempotent=False` any more. The short-circuit itself is therefore pinned directly at the transport, in `tests/test_transport.py`, with a synthetic non-idempotent spec — otherwise this correction would have silently deleted the only proof that the flag does anything at all."* Anyone tidying transport tests while touching calendar-write can delete it without noticing.

**Why it happens:**
"Add a response model" reads as a two-line change (annotation + parser), so it is planned as a small task and reviewed as one — in a file where the surrounding invariants are load-bearing and invisible.

**How to avoid:**
- Scope Phase 31's market-data work to exactly three edits per endpoint: a new response model in `models.py`, `parse_calendar_write_response` returning it, and the return annotation on four call sites (method + shim × sync/async). **No other line in `client.py` / `aio.py` / `_core.py` builders.**
- **Byte-identical request proof:** a `pytest-httpx` test that captures `request.method`, `request.url`, `request.headers` and `request.content` for `add_holidays` and `delete_holiday`, with the expected bytes hard-coded from the pre-change run. If the wire changes, it fails.
- Re-run the gate-ordering AST test and `verification/test_mutation_gate_parametrized.py` as an explicit Phase-31 merge gate, not as incidental CI.
- Re-run `tests/test_transport.py` and assert the synthetic non-idempotent spec test still exists by name.
- Keep `parse_calendar_write_response` tolerant: the live 200/201 body shape for these endpoints was reconciled in Phase 27/28 and a strict model that gets it wrong turns a working published mutation into an exception.

**Warning signs:**
A Phase-31 diff touching `HolidaysIn`, `_core.build_*_request`, or any line above an `_ensure_mutation_allowed()` call. A green CI run where `test_mutation_gate.py` was not collected.

**Phase to address:** 31.

---

### Pitfall 14: vacuous CI gates — three vectors that are *already true today*, not hypothetical

**What goes wrong:**
The project has a signed precedent. From `verification/test_main_matriz_uses_single_client_instance.py`, describing WR-02:

> *"the `<=2`-ctor count alone was a **vacuous** guard for the singleton-leak it claims to prevent: a regression could thread a single `Client()` AND still route every sweep probe through the module singleton path ... that the ctor-count never sees."*

The fix had two parts, and both are the recipe: a **lower bound** (*"the lower bound makes the gate non-vacuous — a driver that constructs ZERO classes, i.e. the un-migrated state, FAILS RED rather than passing trivially"*) and a **second, complementary assertion on the actual mechanism**.

Three concrete vacuity vectors for GATE-TYP-01, measured now:

**(a) A parity test keyed on `__all__` silently skips half the repo.** Measured: `aio.py` defines `__all__` in `higyrus`, `ambito_financiero`, `matriz` — and **not** in `iol_client`, `market_data_client`, or `wallets_client`. A test that reads `aio.__all__` either raises `AttributeError` on three packages (and gets wrapped in a `getattr(..., [])`), or compares two empty sets and passes.

**(b) The AST surface gate is vacuous on two of six packages by construction.** `wallets_client.__all__` is exactly `["WalletsAPIError", "WalletsAuthError", "WalletsClientError", "WalletsRateLimitError", "configure"]` — **zero data functions**. TYP-03 adds empty `models.py`/`types.py`, which does not change that. `ambito_financiero_client` has one data function already returning `float`. So the gate can be green while enforcing nothing on 2/6 packages, and nobody will notice because green is green.

**(c) The D-16 lists disagree today, so partial enrollment looks complete.** See Pitfall 16.

**Why it happens:**
A guard is written to pass against the intended end state. Nobody runs it against the *current* state to confirm it fails.

**How to avoid — the repo's own recipe, applied to every Phase-32 gate:**
1. **Lower bound per package.** Hard-code the expected count (`iol_client` exports ≥ 4 data functions, `market_data_client` ≥ 14, ...). A package dropping to zero fails RED.
2. **RED proof.** Each gate ships with a deliberately-broken fixture — a throwaway module annotated `-> dict[str, Any]`, an `aio` shim with a mismatched signature — that the gate must reject. Commit the fixture; it is the gate's own test.
3. **Second assertion on the mechanism.** For parity: not just "same names" but "same `get_type_hints()` return type per name", and not just "same signature" but "the sync name is a function and the async name is a coroutine function".
4. **Run every gate against `HEAD~1` before the migration lands and record that it FAILED.** Put the failing output in the phase artifacts.

**Warning signs:**
A gate that passes on the first commit that introduces it. A `getattr(mod, "__all__", [])` fallback. Any gate whose test file has no fixture directory.

**Phase to address:** 32.

---

### Pitfall 15: AST surface-gate false negatives (worse than false positives) given `from __future__ import annotations` everywhere

**What goes wrong:**
Every module has `from __future__ import annotations`, so annotations are strings at runtime and `ast` nodes at parse time. A gate looking for `Any` / `dict[str, Any]` in return position must handle all of these, and the ones it misses are **false negatives** that let the exact current shape through:

| Shape | AST node | Miss risk |
|---|---|---|
| `-> Any` | `ast.Name(id='Any')` | low |
| `-> dict[str, Any]` | `ast.Subscript` | low |
| `-> list[dict[str, Any]]` | `Subscript` nested one level | **HIGH — this is iol's literal current shape for `get_historical_quotes` and `get_instruments_by_type`** |
| `-> Quote \| None` | `ast.BinOp` (PEP 604), **not** `Subscript` | HIGH — a `Subscript`-only walker skips it entirely |
| `-> dict[str, Any] \| None` | `BinOp` containing a `Subscript` | HIGH |
| `-> Optional[Any]` | `Subscript(Name('Optional'))` | medium |
| `-> "Quote"` | `ast.Constant(str)` | medium |
| `import typing as t` → `-> t.Any` | `ast.Attribute` | medium |
| `from typing import Any as _A` → `-> _A` | `Name('_A')` | medium — needs import-alias resolution |

The gate must **recurse into the full annotation subtree** and flag `Any` anywhere in a return position, plus `dict[str, Any]` at any depth. Simple `isinstance(node.returns, ast.Name)` checks are the failure mode.

Two more, specific to this repo:

- **Walk the defining module, not `__init__.py`.** `__all__` lives in `__init__.py` but the annotated `def`s live in `client.py` / `aio.py` (and the module-level shims live in `client.py`/`aio.py` too). A gate that only parses `__init__.py` sees re-export names with no annotations attached.
- **DT-06 exemptions rot.** Dunders (`__reduce__`, `__deepcopy__`, `__getattr__`), `_`-prefixed helpers including `_matriz_legacy_request`, and the `_request` transport methods returning `httpx.Response`. Encode them as an explicit allow-list with a **reason string per entry**, and make the gate **fail if an exemption matches nothing** — a dead exemption is a permanent, invisible hole. (`_matriz_legacy_request` is a deprecated back-compat wrapper for `main_matriz.py` probes; when the probes stop using it, the exemption must go, not linger.)

**Why it happens:**
PEP 604 unions and nested generics are recent enough that most example AST walkers on the internet predate them, and the code that gets copied checks `ast.Name` and `ast.Subscript` only.

**How to avoid:**
- The gate's RED fixture (Pitfall 14) contains **one function per row of the table above**. That is the acceptance test.
- Prefer AST over `get_type_hints()` — the latter crashes on `TYPE_CHECKING`-only names (Pitfall 6) and cannot run against a module that fails to import.
- Add the `strict=False` grep (Pitfall 10) and the `msgspec.field(` grep (Pitfall 7) to the same gate script — three checks, one CI step.

**Phase to address:** 32.

---

### Pitfall 16: D-16 enrollment — the mypy backlog is trivial (2 errors, measured); the trap is four lists that disagree

**What goes wrong:**
The feared "backlog of pre-existing mypy errors" is small. Measured just now:

```
uv run mypy packages/market-data-client/src packages/market-data-client/tests
packages/market-data-client/tests/test_reference_core.py:412: error: Need type annotation for "body"  [var-annotated]
packages/market-data-client/tests/test_core.py:417: error: Need type annotation for "body"  [var-annotated]
Found 2 errors in 2 files (checked 34 source files)
```

`src` is **clean**. Both errors are `var-annotated` on a `body = {...}` literal — one-line fixes.

The real trap is that there are **four independent enrollment lists** and they currently disagree, so updating three of four looks green and enforces nothing:

| List | Location | Currently contains | Missing |
|---|---|---|---|
| mypy `files` | `pyproject.toml` (`files = [...]`) | 5 (higyrus, wallets, matriz, iol, ambito) | **market-data** |
| import-linter `root_packages` | `pyproject.toml` `[tool.importlinter]` | **4** (ambito, iol, higyrus, matriz) | **wallets, market-data** |
| mypy-tests loop | `.github/workflows/ci.yml` (`for pkg in ...`) | 5 (higyrus, wallets, matriz, iol, ambito) | **market-data** |
| cross-package surface net | `verification/test_public_surface.py::_PACKAGES` | **4** (ambito, iol, higyrus, matriz) | wallets, market-data — the latter **by design** (market-data uses in-package `tests/test_public_surface_market_data.py`; RESEARCH corrected CONTEXT in Phase 25) |

Note also that `wallets_client` is missing from two of the four — an unowned gap that predates this milestone and will look like a D-16 regression if not stated up front.

The `_core` contract itself should pass on first write: `market_data_client/_core.py` imports `re`, `time`, `dataclasses`, `typing`, `httpx`, `market_data_client._params`, `._state`, `.exceptions` — no `client`, no `aio`. Which makes it **vacuous on arrival**.

**How to avoid:**
- Treat D-16 as a single atomic commit touching all four lists (minus the deliberate market-data exclusion from the cross-package surface net, which must be **documented in the test file** so a future reader does not "fix" it).
- Fix the two `var-annotated` errors first, in their own commit, so the enrollment commit is a pure config change.
- **RED-prove the new import-linter contract:** temporarily add `from market_data_client import client` to `_core.py`, confirm `lint-imports` fails, revert. Record the failing output in the phase artifacts. Without that, the contract is a green line that has never once been exercised.
- Decide explicitly whether `wallets_client` joins `root_packages` and `_PACKAGES` in this milestone or is deferred with a written reason. Do not leave it ambiguous.

**Phase to address:** 32.

---

### Pitfall 17: the 6× copies drift **during** the milestone — and there is proof it already happened

**What goes wrong:**
DT-03 copies the decoder verbatim into six packages in Phase 29. Phases 30, 31 and 33 will each find a bug in it while working on one package, fix the copy in front of them, and ship. Three copies of one fix, three copies of an old bug.

This is not speculative. **It already happened**: `SafeModel`/`_coerce` was documented as "duplicado verbatim ×3" and is measurably not (Pitfall 1). The drift survived two milestones undetected because nothing checked.

The same hazard applies to `_logging.py`, which Pitfall 5 requires changing in all six.

**How to avoid:**
- Ship, in Phase 29, an intactness test in `verification/`: normalize each copy (strip the module docstring, apply an explicit substitution map for the intentional per-package deltas — logger name, exception class, package name) and assert all six normalized bodies hash identical. The technique has precedent in-repo: SPIKE-006 item 10b used sha256 byte-identity for deny-list intactness across four files.
- Make the substitution map an explicit, reviewed list. Anything not in the map that differs is a failure. That is what turns "verbatim" from an aspiration into a gate.
- Extend the same test to `_logging.py`'s `RedactingFilter` class body (the marker tuples and regex sets legitimately differ per package — those go in the substitution map; the `filter()` method body does not).
- Any decoder fix is one commit touching six files. A five-of-six commit fails RED.

**Warning signs:**
A commit message like "fix decoder edge case in iol". A `git log --stat` for a decoder fix touching fewer than six `_decode.py` files.

**Phase to address:** 29 (build the test), enforced through 30-33.

---

### Pitfall 18: the decoder's logging turns "pure" `_core` parsers into side-effecting code

**What goes wrong:**
REFAC-03 made `_core.py` pure builders/parsers, with import-linter forbidding `_core → client|aio` in four packages. Divergence emission happens where decoding happens — inside the parsers. That is not forbidden by the existing contract, but it does mean `_core` unit tests become order-dependent on logging configuration, and `caplog` assertions in one test can be polluted by decode calls in another (`asyncio_mode = "auto"` and `--import-mode=importlib` make ordering non-obvious).

`market_data_client/models.py` already imports `market_data_client._params`, so the models layer is not import-free either.

**How to avoid:**
- Put the decoder in its own module, `_decode.py`, per package. Dependencies: stdlib + `msgspec` + `logging.getLogger("<pkg>")` only. No `_state`, no `exceptions`, no `client`, no `aio`.
- While the import-linter contracts are open for D-16 edits (Phase 32), extend each `forbidden` contract's `source_modules` to include `<pkg>._decode`. Six lines, and it is the one moment where the cost is zero.
- Every decoder test uses `caplog.at_level(..., logger="<pkg>")` scoped to the package logger, never the root.

**Phase to address:** 29 (module placement), 32 (contract extension).

---

### Pitfall 19: duplicate divergence emission, sync vs async

**What goes wrong:**
CLAUDE.md mandates that every logic fix be mirrored in `client.py` and `aio.py`. If emission is added to both shells *and* the `_core` parsers already emit, one response produces two records. In the async surface the duplicates interleave with other tasks' records, so the Phase-29 merge gate "observable mode emits exactly one record" becomes flaky rather than failing cleanly — the worst kind of failure, because it gets marked "known flaky" and disabled.

**How to avoid:**
- Emission happens in **exactly one layer**: the `_decode` helper, called from `_core` parsers. Never in `client.py` or `aio.py`. This is also the only arrangement that keeps the copy count at one per package (Pitfall 17).
- Attach `endpoint_name` (already threaded through `RequestSpec.endpoint_name` in every package) to the record as a correlation field, so duplicates are detectable rather than merely suspected.
- Run the "exactly one record" test on **both** surfaces (the repo's existing `test_*_async.py` mirroring convention), with the async case awaiting a single call and asserting on a logger-scoped `caplog`.

**Phase to address:** 29.

---

### Pitfall 20: emission cost in hot async paths

**What goes wrong:**
`logging` is synchronous. The library only attaches `NullHandler`, so by default the cost after the level check is near-zero — but three things break that assumption:

1. **Filters run before handlers.** `RedactingFilter` is attached to the package logger, so every constructed record pays 4 `re.sub` passes plus a full `record.__dict__` scan, `NullHandler` or not.
2. **Consumers attach real handlers** to package loggers (Sentry, Datadog, structlog bridges). A 5000-record burst is an incident (Pitfall 4).
3. **The strict-mode drivers attach real handlers by design.** Phase 33 runs with output on.

An emitter that builds its payload before checking the level pays the construction cost unconditionally, even with `NullHandler`.

**How to avoid:**
- `if not logger.isEnabledFor(logging.WARNING): return` as the **first line** of the emitter, before any dict/string construction.
- Never `logger.debug(json.dumps(payload))`. Pass the structured data via `extra=` (namespaced — Pitfall 21) and let the handler format it.
- Aggregate before emitting (Pitfall 4). One record per distinct divergence shape per response, with a count.
- Measured baseline for the sizing conversation: decoding is not the cost. 5000 rows = 0.79 ms via `convert`, 1.35 ms via `json.decode`, 2.06 ms per-row. Anything slower than that is logging.

**Phase to address:** 29.

---

### Pitfall 21: "observable, not fatal" becomes fatal via a reserved `LogRecord` attribute collision

**What goes wrong:**
`logging.Logger.makeRecord` raises at the **call site** if an `extra=` key collides with an existing `LogRecord` attribute:

```
KeyError: "Attempt to overwrite 'name' in LogRecord"
```

Reserved names include `name`, `msg`, `args`, `levelname`, `levelno`, `pathname`, `filename`, `module`, `exc_info`, `lineno`, `funcName`, `created`, `msecs`, `thread`, `process`, `message`, `asctime`. Several of those — `name`, `module`, `filename`, `msg` — are entirely plausible keys for a decoder divergence record describing a *field name* or a *module*. A single collision converts an observation into a runtime exception, violating DT-02 in the most embarrassing possible way: the mechanism built to avoid crashing crashes.

**How to avoid:**
- Namespace every key: `divergence_endpoint`, `divergence_path`, `divergence_expected`, `divergence_got`, `divergence_count`. Or nest everything under one non-reserved key.
- A test that emits a divergence whose field is literally named `name` and one named `module`, asserting no exception. Cheap; catches the whole class.
- Related: Pitfall 5(b) — if you nest under one key, that key's value is a dict and `RedactingFilter` will not scan it. Both fixes are needed together.

**Phase to address:** 29.

---

### Pitfall 22: the Phase-29 sizing run returns "0 divergences" because it SKIPped

**What goes wrong:**
The sizing run is the decision gate for committing Phases 30-32. It depends on live APIs, and this project has a documented precedent of exactly this returning nothing:

- **Phase 23**: no develop Auth0 creds in-repo → the market-data driver took the sanctioned `require_env`-SKIP / D-09 NO-DATA path → *"`verify_cycle_closure("market-data-client")` returns `(True, [])` **vacuously**"*. An entire phase's live verification produced zero evidence, correctly, and the requirement stayed Pending for a full milestone.
- matriz is **remarkets-only** (D-MATZ-27, still in backlog) — prod shapes are unobserved by construction.
- IOL and higyrus depend on operator credentials and market hours (a PROJECT.md constraint: *"resultados pueden variar por horario de mercado"*).

Compounded by Pitfall 3 (one error per decode) and Pitfall 7 (renamed/new server fields invisible to msgspec), a run that *does* execute still undercounts.

**How to avoid:**
- The sizing report is a **per-package RUN / SKIP table**. A SKIP is not evidence and must not contribute a zero to the total. This is the same discipline the Phase-23 runner already applies (classify SKIPPED, never FAILED).
- **Size offline against the committed schema snapshots.** `verification/snapshots/` holds 18 write-once schemas across 4 packages plus 9 market-data baselines from the credentialed 2026-07-31 sweep. Decoding every snapshot with the strict + enumerating decoder needs zero credentials, zero VPN, no market hours, and enumerates every field. That is the honest floor, and it is available on day one of Phase 29.
- State the number as `≥ N (offline snapshots) + <live coverage table>`.

**Phase to address:** 29 (method), 33 (execution).

---

### Pitfall 23: narrowing `mercado` / `plazo` to `Literal` is itself a source break, and the evidence to close the set does not exist until Phase 33

**What goes wrong:**
`iol.get_quote(simbolo, *, mercado: str = "bcba", plazo: str = "t2")` (`client.py:497-508`, plus the module shim at `:647` and the async mirrors). Narrowing to `Literal[...]` has two costs:

1. **DT-07's stated cost**: an incomplete `Literal` rejects legitimate values. The set must come from live evidence.
2. **An unstated cost**: narrowing a *parameter* is source-breaking for **mypy-strict consumers even when every value they pass is valid**. `mercado=some_str_variable` now fails with `arg-type`. That belongs in the DT-08 callout next to dict→model, and it is easy to forget because it does not break at runtime.

The evidence problem: `main_iol.py` only ever exercises `bcba` / `t2` plus a six-type instrument sanity sweep. That is evidence of *what works*, not of *the complete set*. IOL's API accepts other markets (`nyse`, `nasdaq`, `rofex`, ...) and other settlement terms; a `Literal["bcba"]` derived from driver coverage would break every non-BCBA consumer.

The pressure peaks in Phase 30, where the models work makes it feel natural to "finish the typing" — before Phase 33's live evidence exists.

**How to avoid:**
- Order the work: **Phase 30 ships `str`** with an explicit `# TYP-01 carry-forward: Literal pending live census (DT-07)` marker at each of the four sites. **Phase 33 promotes to `Literal`** only against a written per-value evidence table (value → probe name → live response). Never the reverse.
- If Phase 33 cannot close the set, it stays `str` and is documented as a carry-forward. DT-07 already authorizes this outcome; the plan just has to not treat it as failure.
- If it *is* closed: add the `Literal` narrowing as its own row in the iol README changelog callout, separate from the dict→model row.

**Warning signs:**
A Phase-30 diff containing `Literal[` on `mercado` or `plazo`. A `Literal` set whose members exactly match the values `main_iol.py` happens to probe.

**Phase to address:** 30 (hold at `str`), 33 (promote with evidence), 34 (callout if promoted).

---

### Pitfall 24: `msgspec` as a hard runtime dep silently expands the Phase-34 release set from 2 packages to 6

**What goes wrong:**
DT-08: only packages whose surface changed get republished. But DEC-01 adds `msgspec` to the runtime dependencies of all six `pyproject.toml` files and copies a decoder into all six. That is a **wheel-content and dependency-metadata change in every package**, including `ambito-financiero-client` (one function, already `-> float`) and `wallets-client` (zero data functions, and it would gain a C-extension runtime dependency to support an empty `models.py`).

Dependency profile today is minimal and pure-Python: `httpx`, `python-dotenv`, `tenacity`, plus `platformdirs` in iol and `websocket-client` in matriz. `msgspec` is a C extension. Wheel availability is good — 48 wheels for 0.21.1, tags `cp310`–`cp314`, macOS x86_64/arm64, manylinux, musllinux, win-amd64 — so the CI matrix (ubuntu, py3.12 + py3.13) is covered. The residual risk is a consumer on a platform or Python version without a wheel needing a compiler, with **no pure-Python fallback** (sdist only).

`uv.lock` refresh touches the whole workspace, and the Phase-24/28 release flow validates `uv lock --check` + version alignment.

**How to avoid:**
- **Decide in Phase 29, not Phase 34.** PROJECT.md already flags it: *"Evaluar en F29 si `msgspec` (extensión C) debe ser extra opcional con fallback."* The answer determines the release set.
  - **Hard dep** → accept that all six packages get a version bump and say so in the Phase-29 artifacts, so Phase 34 is not a surprise. Simplest; one code path; one test matrix.
  - **Optional extra with `_coerce` fallback** → ambito and wallets need no release, but the fallback path needs its own full test matrix (every decoder test × 2 paths), roughly **doubling Phase 29's test surface**, and the two paths will drift (Pitfall 17 again, now within a package).
- Whichever is chosen, do **not** add `msgspec` to `wallets-client` if its `models.py` is empty — an unused C-extension dep on a stub is pure cost.
- Phase 34 gate: for each package, diff the built wheel's `METADATA` and `RECORD` against the published version; "surface unchanged" must mean *wheel content unchanged*, not just `__all__` unchanged.

**Phase to address:** 29 (decision, D-lock), 34 (execution).

---

### Pitfall 25: DT-05 "preserve `from_api`" is read as a signature guarantee when the contract is the *semantics*

**What goes wrong:**
DT-05 says `from_api(payload)` is preserved as the public constructor — *"cambia su implementación interna, no su firma"*. A reviewer checks the signature, sees `(cls, payload: Any) -> Self`, and approves. Meanwhile the tolerance semantics — the thing consumers and 900+ tests actually depend on — changed.

The merge gate ("the three suites stay green without test changes") is the right gate, and it *will* catch Pitfall 1 — **but only if it is run per-package on all three, with literally zero test edits.** The existing suites do pin the contracts: higyrus/market-data tests assert `""` / `0.0` / `[]` / nested-empty; matriz tests assert `None` / `empty()` / `{}`. They disagree, on purpose, and that is the signal.

Additional trap: `matriz`'s `empty()` is public API used **inside the class definitions** (`field(default_factory=InstrumentId.empty)`, `field(default_factory=Segment.empty)`). msgspec never calls it — but removing it breaks import, at class-definition time, for the whole package.

**How to avoid:**
- The Phase-29 merge gate is stated as: *"`uv run pytest packages/higyrus-client packages/matriz-client packages/market-data-client` passes with `git diff --stat` showing zero lines changed under any `tests/` directory."* Mechanical, checkable, not a judgment call.
- `empty()` stays on matriz models, unchanged, tested.
- `from_api` keeps accepting `None`, non-dict, and partial payloads. Verified msgspec behavior for the non-dict cases: `convert(None, type=Quote)` → `ValidationError: Expected 'object', got 'null'`; `convert([1], type=Quote)` → `Expected 'object', got 'array'`. Those must be caught by `from_api` and routed to the tolerant path + a divergence, never propagated.

**Phase to address:** 29.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|---|---|---|---|
| `try: convert() except: return from_api()` with no field-level enumeration | Decoder done in 20 lines; observable mode works | One divergence reported per response instead of per field; Phase-29 sizing undercounts by ~an order of magnitude; Phase-33 becomes serialized whack-a-mole | Acceptable as the **runtime** observable path. Never as the strict/enumerating path. |
| `strict=False` to silence a noisy field | A red Phase-33 run goes green in one character | Re-creates the exact lenient coercion cited as the reason to reject Pydantic v2; the milestone's core value is void | **Never.** Grep-gate it. |
| Harmonizing matriz onto zero-defaults "while we're in there" | One decoder policy instead of two | Silent semantic change to a published package with zero untyped surface, i.e. all cost and no benefit; breaks its test suite, which then gets "fixed" | **Never in v1.6.** A separate, announced decision if ever. |
| Snake_casing model fields | Pythonic public API | No working rename exists for stdlib dataclasses in 0.21.1; `msgspec.field(name=)` yields a `Field` sentinel object silently, metadata is ignored silently | **Never** until upstream #553 lands and is verified. |
| Skipping the 6× intactness hash test | Saves half a day in Phase 29 | The `SafeModel` drift (Pitfall 1) is the proof of what happens; the next reader inherits three decoders and a false claim of verbatim copies | Never — it is ~40 lines and it is the only thing enforcing DT-03. |
| `msgspec` as optional extra with `_coerce` fallback | ambito + wallets need no release; no C-extension in a stub | Doubles Phase-29's test surface; two code paths that will drift; every future decoder fix is 12 edits, not 6 | Only if a concrete consumer platform without a wheel is identified. Otherwise take the hard dep and the six releases. |
| Reusing the existing SEC-01 `caplog` no-leak test as the decoder's leak proof | One less test × 6 | It exercises the *old* record shape (anchored key/value text); the new shape (bare values, dict `extra=`) leaks past it while it stays green | Never — it is a false green. |
| Typing the holiday **request** while typing the response | "Finish the endpoint properly" | Perturbs a wire body whose UPSERT-by-date idempotency was earned by row-count measurement (D-20/F-49/F-59), not by spec prose | Never in Phase 31. |
| Landing D-16 by updating three of the four enrollment lists | CI is green | The unenrolled list enforces nothing and nobody re-checks; matches the existing four-way disagreement that created D-16 | Never — atomic commit, all four, with a written note for the deliberate exclusion. |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|---|---|---|
| **`RedactingFilter` (6 copies)** | Assuming it redacts anything sensitive in a record | It is **key-anchored** and **str-only**. Emit no wire values; recurse the `record.__dict__` scan into dict/list/tuple in all six copies; add a decoder-specific `caplog` sentinel per package. |
| **`_ensure_mutation_allowed()` (market-data)** | Inserting a line above it while adding response models | It is the **literal first statement** of 16 mutation methods and AST-verified. Phase 31 touches only the return annotation + parser + model. Re-run `test_mutation_gate.py` + the no-gate-bypass AST test as an explicit merge gate. |
| **`build_add_holidays_request` idempotency** | Treating `idempotent=True` as a spec-derived default | It was corrected from `False` **on live row-count measurement** (F-49/F-59). D-20 says prose was never sufficient. Do not touch the builder or `HolidaysIn.to_dict()`; prove the request bytes are unchanged with `pytest-httpx`. |
| **`verification/findings.py`** | Editing text that feeds a finding title/identity | Append-only + content-addressed `idempotent_by_title` dedupe + operator-field preservation. A title change orphans the operator's disposition and creates a duplicate. Follow the Phase-15 D-07 title-stability protocol. `main_iol.py:1027` hard-codes `client.py:254` and must be handled deliberately in Phase 30. |
| **`verification/snapshots/`** | Regenerating snapshots to make the strict decoder pass | Snapshots are the write-once baseline and the **only credential-free divergence-sizing corpus** available in Phase 29. Read them, decode them, never regenerate them to fit. |
| **`main_*.py` drivers** | Adding a second `Client()` for a strict-mode run | Each driver is AST-gated to ≤2 constructors (1 sync + 1 async) — matriz's TokenStore corrupts otherwise. Strict mode is a decoder **flag threaded into the existing instance**, not a second client. |
| **`_core.py` purity contracts** | Putting the decoder in `_core.py` or `models.py` | Own module `_decode.py`; add it to each `forbidden` contract's `source_modules` during the D-16 edit. |
| **`market_data_client` in the cross-package surface net** | "Fixing" its absence from `verification/test_public_surface.py::_PACKAGES` | Deliberate — it uses in-package `tests/test_public_surface_market_data.py` (RESEARCH corrected CONTEXT in Phase 25). Document the exclusion **in the test file** so the next reader does not undo it. |
| **`wallets_client`** | Copying the decoder + `msgspec` dep into it for symmetry | Zero data functions, no `_logging.py`, no `_core.py`, no `_state.py`, absent from import-linter and the surface net. TYP-03's empty `models.py`/`types.py` is structure only — do not add a C-extension runtime dep to a stub. |
| **`asyncio_mode = "auto"` + `caplog`** | Asserting "exactly one record" on the root logger | Scope `caplog.at_level(..., logger="<pkg>")`; emit from exactly one layer (Pitfall 19); include `endpoint_name` for correlation. |
| **httpx `resp.json()`** | Assuming it rejects non-standard JSON | It is stdlib `json.loads`: **`NaN` / `Infinity` / `-Infinity` are accepted**. `convert` then passes `nan` into a `float` field with zero divergence. Add an `isfinite` guard. |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|---|---|---|---|
| Per-row divergence emission | A driver run that used to take 2 s takes minutes; a consumer's log pipeline rate-limits; Sentry quota alert | Aggregate by `(endpoint, normalized_path, expected, got)` → one record + `count`; cap distinct keys per response | The first structural divergence on a collection endpoint. `get_posicion_valuada` measured at **390 rows**; `get_movimientos` at **139**; `iol.get_instruments` is a country-wide catalog. |
| Building the record payload before the level check | Steady overhead even with `NullHandler`, i.e. in every consumer that never enabled logging | `if not logger.isEnabledFor(WARNING): return` as the emitter's first line; pass structured data via `extra=`, never `json.dumps` | Any hot loop; the async surface under concurrency |
| `RedactingFilter` on every record | Filters run before handlers, so `NullHandler` does not save you: 4 `re.sub` + full `record.__dict__` scan per record | Aggregate first (fewer records); keep records small; recursion added in Pitfall 5 must not become O(payload) | ~10³ records/second |
| Per-field / per-row enumeration on the **hot** path | Latency regression on every response, not just divergent ones | Enumeration runs **only** after the fast `convert()` already failed. Measured: 5000 rows batch = **0.79 ms**, per-row = **2.06 ms** — cheap, but not free, and pointless when the batch succeeds | If enumeration is made the default path |
| `get_type_hints()` called per decode | Reflection cost on every response | Cache resolved hints per class (`functools.cache`) — msgspec already caches internally per type, so this only matters for the hand-rolled unknown-key detector and the enumerating fallback | Immediately, on any collection endpoint |
| Decoding treated as the bottleneck | Time spent optimizing the wrong thing | It is not. `json.decode` 1.35 ms / `convert` 0.79 ms for 5000 rows. Logging is the cost. | n/a — this trap is wasted effort, not a runtime failure |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---|---|---|
| Divergence record quotes the offending **value** | `RedactingFilter` is key-anchored — a bare value carries no anchor and is emitted verbatim. Tokens, `client_secret`, `refresh_token`, passwords and **CUITs** (higyrus PII) all live in payload values. | Contract: records carry `(endpoint, json_path, expected_type, got_type, count)` only. Type names, never values. Enforced by a per-package `caplog` sentinel test. |
| Structured emission via `extra={"divergence": {...}}` | The `record.__dict__` scan is `isinstance(value, str)`-guarded in **all six** copies — a dict/list value is never scanned and bypasses redaction entirely | Recurse the scan into dict/list/tuple in all six `_logging.py`; or keep every `extra=` value a scalar |
| `exc_info=True` on the decoder path | `ValidationError` messages embed offending values for several type errors; tracebacks are not content-filtered | Ban `exc_info` on the decoder path; log `str(e)`'s **path component** only, never the whole message when it can contain a value |
| Reusing the SEC-01 no-leak test as the decoder's proof | It exercises the anchored-text shape; the new shapes leak past it while it stays green | New, decoder-specific sentinel tests, one per package |
| Schema snapshots / findings regenerated from a **credentialed** strict run | Phase 29's offline sizing and Phase 33's runs produce divergence text that could be committed to `*-findings.md` or `verification/snapshots/` with real values in it | The redaction contract applies to findings text too. `verification/redaction.py::safe_print` already exists — route sizing output through it. Review every findings diff for values before commit. |
| Unknown-key detector logs the **values** of unknown keys | An unknown key is exactly where a new credential-ish field would appear | Log unknown **key names** only. Key names are schema, not secrets. |
| `msgspec` sdist build on an unwheeled consumer platform | Compiles C at install time from a source dist; supply-chain surface grows for six wheels | Pin an exact version; verify the CI matrix (py3.12/3.13 on ubuntu) resolves to a wheel, not the sdist; document the sdist fallback in the READMEs |

---

## Consumer-DX Pitfalls

("UX" for a client library = what the consumer feels.)

| Pitfall | Consumer Impact | Better Approach |
|---|---|---|
| Silent truthiness flip on iol dict→model | `if not quote:` inverts with no error; the bug ships to their production | Lead the README callout with this row; do **not** add `__bool__` to hide it |
| No `to_dict()` on the new iol models | Every consumer who serialized the dict has to hand-write a converter | Ship `to_dict()`; precedent exists (market-data request models) |
| `Literal` narrowing on `mercado`/`plazo` with an incomplete set | Legitimate calls stop type-checking; consumers pin the old version | Live-evidence census (DT-07) or leave `str`. Never guess. |
| Divergence warnings with no way to turn them off | A consumer whose feed legitimately omits an optional field gets a warning per call forever | Standard `logging` levels are the off switch — but document the logger name and the record's structured fields in each README so filtering is possible |
| Six packages, six different decoder behaviors | The "identical contract across six libs" promise is the milestone's headline; drift makes it a lie | The 6× intactness hash test (Pitfall 17) is what makes the promise checkable |
| `msgspec` leaking into a public signature | Consumers inherit a C-extension type in their own type annotations | DT-01. Enforce with a grep in the Phase-32 gate: `msgspec` must not appear in any annotation of an `__all__`-exported symbol |
| A breaking minor with no migration section | Consumers discover the break at runtime | DT-08 README callout per package, with a before/after code block per changed function |

---

## "Looks Done But Isn't" Checklist

- [ ] **Decoder copied 6×:** often missing the intactness hash test — verify a deliberately-edited single copy makes CI fail RED.
- [ ] **`_coerce` replaced in "3 packages":** often missing that matriz's semantics are the opposite — verify all three suites pass with `git diff --stat` showing **zero** lines changed under any `tests/`.
- [ ] **"Extra field" divergence test:** often vacuous — msgspec **cannot** detect extra fields on dataclasses. Verify the hand-rolled `set(payload) - fieldnames` detector fires and that removing it makes the test fail.
- [ ] **Observable mode "emits exactly one record":** often tested with a 3-row fixture — verify with 5000 identical-divergence rows that it is still exactly one, with `count == 5000`.
- [ ] **Redaction:** often verified with the old SEC-01 test — verify a decoder-emitted record carrying a sentinel token, including via a **dict** in `extra=`, leaks nothing.
- [ ] **Model annotations:** often missing runtime imports — verify `get_type_hints()` succeeds on **every** model class in every package (one test, whole class of bugs).
- [ ] **`received_at`:** verify (a) the client stamp survives decoding, (b) a wire `received_at` does **not** override it on `MarketDataSnapshot`, (c) it **is** read verbatim on `Symbol`.
- [ ] **iol migration:** often stops at `client.py` — verify all **16** signatures (4 functions × method/shim × sync/async) plus `_core` parsers, plus `main_iol.py:316` and `:395`.
- [ ] **iol breaking-change callout:** often lists only `[]`/`.get()` — verify the truthiness flip and the `json.dumps` break are both documented.
- [ ] **Holiday mutations typed:** often missing the wire proof — verify request `method`/`url`/`headers`/`content` are byte-identical before and after, and that `_ensure_mutation_allowed()` is still the literal first statement (re-run the AST gate).
- [ ] **`test_transport.py` synthetic non-idempotent spec:** verify it still exists by name after any calendar-write work — it is the only remaining proof the idempotent flag does anything.
- [ ] **Surface AST gate:** often only handles `ast.Name`/`ast.Subscript` — verify against a RED fixture containing `list[dict[str, Any]]`, `X | None` (BinOp), `dict[str, Any] | None`, `t.Any`, `Any as _A`, and `-> "Quote"`.
- [ ] **Surface AST gate coverage:** verify a per-package **minimum export count** so `wallets` (0 data functions) and `ambito` (1) cannot make the gate vacuously green.
- [ ] **Parity test:** verify it does not key on `aio.__all__` — `iol`, `market_data_client` and `wallets_client` do not define one. Verify the expected-count lower bound per package.
- [ ] **Every Phase-32 gate:** verify it FAILS against `HEAD~1` (pre-migration) and record that output in the phase artifacts.
- [ ] **D-16:** verify all four lists updated (mypy `files`, import-linter `root_packages`, `ci.yml` mypy-tests loop, and a written note on the deliberate `test_public_surface.py` exclusion) — and RED-prove the new `_core` contract by temporarily adding a forbidden import.
- [ ] **Phase-29 sizing run:** verify it reports a per-package RUN/SKIP table and states `≥ N`, and that the offline snapshot corpus was decoded.
- [ ] **Release scope:** verify by diffing built wheel `METADATA`/`RECORD` against the published version, not by eyeballing `__all__`.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---|---|---|
| matriz semantics silently changed (P1) | **HIGH** if released, LOW if caught by the merge gate | Caught pre-release: revert to the policy-parameterized decoder, re-run all three suites with zero test edits. Released: matriz consumers now get `0.0` where they got `None` — patch release restoring pass-through + README erratum. This is the strongest argument for the merge gate being non-negotiable. |
| Divergence flood in Phase 33 (P2, P3) | MEDIUM | Triage by `(endpoint, path)` frequency. Split: schema-fix (model wrong) vs server-divergence (finding) vs Literal-census (widen to `str`). Widening a response `Literal` to `str` is a safe, non-breaking, one-line stopgap that preserves observability — do that before touching the decoder. |
| Credential leak in a log record (P5) | **HIGH** | Rotate the credential immediately (per-package `.env`). Audit any committed findings/snapshots for the value. Then fix the emitter contract — the fix is cheap; the rotation is the cost. Prevention is the only affordable option here. |
| iol 0.3.0 breaks an unknown consumer (P11) | MEDIUM | The consumer survey **before** Phase 30 is the cheap version. After the fact: a `0.3.1` adding `to_dict()` plus an expanded README migration section. Do **not** add `__bool__`/`__getitem__` back — that trades a loud break for a permanent silent one. |
| Holiday mutation wire contract perturbed (P13) | **HIGH** | Live-verified UPSERT-by-date behavior is re-earned only by another armed live run with cleanup (LIVE-MUT-01 protocol) against develop, under the double human gate. The byte-identity test costs an hour and makes this unreachable. |
| Vacuous gate discovered later (P14) | LOW to fix, HIGH in lost confidence | Add the lower bound + RED fixture, re-run against the pre-migration commit, record the failure. Then re-audit anything the gate "verified" while vacuous. |
| Decoder copies drifted (P17) | MEDIUM and it grows | Three-way-diff the copies, pick the newest correct one, re-copy, land the intactness test in the same commit. Cost scales with how long it went unnoticed — the `SafeModel` case took two milestones. |
| `msgspec` unavailable on a consumer platform (P24) | MEDIUM | Retrofitting the optional-extra + fallback after release means shipping a second code path into already-published wheels. Decide in Phase 29. |
| `NameError` from a `TYPE_CHECKING` annotation in production (P6) | LOW to fix, HIGH impact | One-line import fix + patch release. The `get_type_hints()` sweep test makes it a CI failure instead. |

---

## Pitfall-to-Phase Mapping

| # | Pitfall | Prevention Phase | Verification |
|---|---|---|---|
| 1 | matriz `_convert` has opposite semantics | **29** | Written 3-way semantics table in phase artifacts; all 3 suites green with `git diff --stat` = 0 lines under `tests/` |
| 2 | matriz response `Literal`s become enforced | **29** (D-lock), 33 (census) | D-lock recorded; strict run over matriz snapshots produces no `Invalid enum value` — or a live-evidence census table |
| 3 | msgspec fail-fast undercounts | **29** | Enumerating mode test: a 3-bad-field payload yields 3 divergences, not 1. Sizing report states `≥ N`. |
| 4 | Log-spam flood | **29** | 5000-row all-divergent fixture → exactly 1 record with `count == 5000`; 25-distinct-shape fixture hits the cap |
| 5 | RedactingFilter gap | **29**, re-verified 33 | Per-package `caplog` sentinel: token in a divergent value, and in a dict `extra=`, appears in zero records |
| 6 | `TYPE_CHECKING` → decode-time `NameError` | **29**, 31, 32 | `get_type_hints()` sweep over every model class in all 6 packages |
| 7 | No dataclass rename; no `forbid_unknown_fields` | **29** | Grep gate `msgspec.field(` absent from `models.py`; hand-rolled unknown-key detector proven by removing it and seeing the test fail |
| 8 | `convert(resp.json())` vs `json.decode(bytes)` | **29** (D-lock), 33 | D-lock recorded; `isfinite` guard test with a `NaN` payload through the real `resp.json()` path |
| 9 | `received_at` stamping | **29** | 3 tests: stamp survives; wire value does not override on `MarketDataSnapshot`; wire value **is** read on `Symbol` |
| 10 | `strict=False` | **29**, 32 (gate), 33 | Grep gate over `packages/*/src/` in CI |
| 11 | iol dict→model breakage | **30**, 34 | `main_iol.py:316`/`:395` migrated same commit; `to_dict()` shipped; README callout leads with the truthiness flip |
| 12 | Hard-coded source coordinates in findings | **30** | `grep -rnE '(client\|aio\|_core)\.py:[0-9]+' main_*.py` inventory; `*-findings.md` diff clean or D-07 protocol followed |
| 13 | Published holiday mutations perturbed | **31** | Byte-identical request test (`pytest-httpx` capture); gate-ordering AST test + `test_mutation_gate_parametrized.py` re-run; `test_transport.py` synthetic spec still present |
| 14 | Vacuous gates | **32** | Every gate FAILS against `HEAD~1`, output recorded; RED fixture committed; per-package minimum counts |
| 15 | AST gate false negatives | **32** | RED fixture with one function per annotation shape in the Pitfall-15 table |
| 16 | D-16 partial enrollment | **32** | All four lists in one commit; new `_core` contract RED-proven with a temporary forbidden import; deliberate exclusion documented in-file |
| 17 | 6× copies drift | **29**, enforced 30-33 | Normalized-source hash equality across 6 copies + explicit substitution map; a single edited copy fails RED |
| 18 | `_core` purity erosion | **29**, 32 | `_decode.py` imports stdlib + msgspec + logging only; added to each `forbidden` contract's `source_modules` |
| 19 | Duplicate sync/async emission | **29** | "Exactly one record" asserted on both surfaces, logger-scoped `caplog`, `endpoint_name` correlation field present |
| 20 | Emission cost in async hot paths | **29** | `isEnabledFor` guard is the emitter's first line (assert by source inspection or by a mock logger that fails if called when disabled) |
| 21 | `LogRecord` attribute collision | **29** | Test emitting divergences on fields named `name` and `module` raises nothing |
| 22 | Sizing run SKIPs to zero | **29**, 33 | Sizing report has a per-package RUN/SKIP table; offline snapshot corpus decoded and counted |
| 23 | `Literal` params narrowed without evidence | **30** (hold `str`), 33 (promote), 34 (callout) | Phase-30 diff contains no `Literal[` on `mercado`/`plazo`; Phase-33 promotion carries a value→probe→response evidence table |
| 24 | `msgspec` hard dep expands the release set | **29** (decision), 34 | D-lock in Phase-29 artifacts; Phase-34 scope justified by wheel `METADATA`/`RECORD` diffs |
| 25 | `from_api` signature vs semantics | **29** | The zero-test-edit merge gate, stated mechanically; matriz `empty()` preserved and tested |

**Phase load summary:** 29 carries 14 of 25 — which is correct and matches the plan's own framing of DEC-01 as *load-bearing, PRIMERO*. Phase 29 is the milestone's risk concentration; if it is planned as "copy a decoder 6×" it will be under-scoped by roughly a factor of three. Phases 30, 31, 32 carry 3, 1 and 4 respectively; 33 and 34 mostly **verify** decisions locked in 29.

---

## Sources

**Primary — empirical (HIGH confidence).** All msgspec behavioral claims were executed, not cited:
- `msgspec 0.21.1` on CPython 3.12.13 and 3.14.3, via `uv run --no-project --python 3.12 --with 'msgspec==0.21.1'`. Probe scripts covered: dataclass decoding (slots / non-slots / inheritance / `default_factory`), unknown-field policy, missing-required, `null`/`bool`/`str`/`int` type mismatches, `Literal` enforcement, `Any` and `dict[str, Any]` fields, `Decimal` and `datetime` parsing, NaN/Infinity, `__post_init__`, `msgspec.field(name=)` and `dataclasses.field(metadata=)` renaming, `Annotated`+`Meta` constraints, `TYPE_CHECKING`-only annotations, error-path formatting, multi-error reporting, and 5000-row throughput.
- `https://pypi.org/pypi/msgspec/0.21.1/json` — 48 wheels, tags `cp310`–`cp314`, `requires_python >=3.10`, uploaded 2026-04-12, sdist present, no pure-Python fallback.

**Primary — repo state (HIGH confidence), read at `milestone/v1.5-mutations` head:**
- `packages/higyrus-client/src/higyrus_client/models.py`, `packages/market-data-client/src/market_data_client/models.py`, `packages/matriz-client/src/matriz_client/models.py` — the three-way `SafeModel`/`_coerce` vs `_SafeModel`/`_convert` divergence.
- `packages/*/src/*/_logging.py` (×6) — `RedactingFilter` marker sets and the str-only `record.__dict__` scan.
- `packages/market-data-client/src/market_data_client/{client,aio,_core}.py` — `_ensure_mutation_allowed()` call sites, `build_add_holidays_request` D-20 idempotency note, `build_delete_holiday_request` `_DAY_SEGMENT_RE`, parser inventory.
- `packages/iol-client/src/iol_client/client.py:62-69, 497-546, 647-680` — `InstrumentType`, the four untyped data functions, `mercado`/`plazo` as `str`.
- `packages/wallets-client/src/wallets_client/__init__.py` — 5-symbol `__all__`, no data functions; directory listing confirms no `_logging.py`/`_core.py`/`_state.py`.
- `pyproject.toml` — mypy `files` (5), `[tool.importlinter] root_packages` (4) + 4 forbidden contracts.
- `.github/workflows/ci.yml:70-90` — the 5-package mypy-tests loop.
- `verification/test_public_surface.py:46-51` — `_PACKAGES` (4).
- `verification/test_main_matriz_uses_single_client_instance.py` — the WR-01/WR-02 vacuous-guard precedent, quoted.
- `main_iol.py:316, 395, 1027, 1182, 1192` — `.get()` sites and the hard-coded `client.py:254` finding text.
- `uv run mypy packages/market-data-client/{src,tests}` executed 2026-08-18 → exactly 2 `var-annotated` errors, `src` clean.

**Primary — project artifacts:**
- `.planning/PROJECT.md` (v1.5 close state, D-locks, Key Decisions table, Phase 23 `require_env`-SKIP / D-09 NO-DATA precedent, Phase 15 D-07 title-stability gate, SPIKE-006 sha256 intactness technique).
- `.planning/future-plans/tipado_homogeneo.md` (DT-01..DT-09, phase 29-34 outline, empirical evidence section — two claims of which are corrected here as Pitfalls 1 and 7).

**Secondary (MEDIUM confidence):**
- [msgspec — Supported Types](https://msgspec.dev/supported-types) — dataclass/attrs limitations (`InitVar` unsupported, extra fields ignored), RFC3339/ISO8601 datetime handling.
- [jcrist/msgspec#553 — Renaming fields for dataclasses](https://github.com/jcrist/msgspec/issues/553) — dataclass rename is an open request, not a shipped feature.
- [jcrist/msgspec#355 — Support renaming struct fields through `msgspec.field`](https://github.com/jcrist/msgspec/issues/355) — establishes `field(name=)` as a `Struct` feature.
- [jcrist/msgspec#545 — `forbid_unknown_fields` default](https://github.com/jcrist/msgspec/issues/545) — confirms `forbid_unknown_fields` is `Struct`-scoped.

---
*Pitfalls research for: retrofitting typed + observable decoding onto 6 published financial-API client wheels (market-libs v1.6, Phases 29-34)*
*Researched: 2026-08-18*
