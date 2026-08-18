# Feature Research

**Domain:** Typed public surface + observable decoding for financial API client libraries (Python, 6 standalone wheels)
**Milestone:** v1.6 "Tipado homogéneo" (phases 29-34)
**Researched:** 2026-08-18
**Confidence:** MEDIUM-HIGH (all `msgspec` and `mypy` behavioural claims are first-party empirical runs on this machine; ecosystem-practice claims are web-tier)

---

## Headline finding (read this before the tables)

**`msgspec` cannot produce the output the observable mode needs.** Verified locally against
`msgspec 0.21.1` with stdlib `frozen=True, slots=True` dataclasses:

| Divergence class | msgspec behaviour | Usable for observable mode? |
|---|---|---|
| Extra/unknown wire key | **silently ignored, zero signal** | ❌ decoder must diff key sets itself |
| Missing required field | `ValidationError: Object missing required field \`ultimoPrecio\`` (path present only when nested: `` - at `$.rows[1]` ``) | ⚠️ raises — no value returned |
| Wrong type | `` ValidationError: Expected `float`, got `str` - at `$.ultimoPrecio` `` | ⚠️ raises — no value returned |
| `null` in non-optional | `` Expected `float`, got `null` `` | ⚠️ raises |
| Unknown `Literal` value | `` Invalid enum value 'rofex' - at `$.mercado` `` | ⚠️ raises |
| **Two+ divergences in one payload** | **only the FIRST is reported** — no collect-all mode ([issue #425](https://github.com/msgspec/msgspec/issues/425)) | ❌ |

Observable mode is defined (DT-02) as *"emit a structured record **and** return a usable value"* —
and it must emit **one record per divergent field**, not one exception per payload. `msgspec` gives
you neither: it aborts on the first problem and returns nothing.

**Consequence for Phase 29:** the observable path has to be a hand-written per-field walk (an
evolution of today's `_coerce`, which already walks `get_type_hints()` field by field). `msgspec`'s
real contribution is confined to the **strict** path — where fail-fast with an exact `$.path` is
exactly the right semantics — plus speed. That reframes the plan's own open risk ("evaluar en F29 si
`msgspec` debe ser extra opcional con fallback"): **the fallback isn't a fallback, it's the primary
implementation of the default runtime mode.** Recommend Phase 29 explicitly time-boxes a decision
between:

- **(a) Two engines** — stdlib walker for observable, `msgspec` for strict. Two code paths that can
  drift; `msgspec` becomes a hard dep of all six wheels for a driver-only feature.
- **(b) One engine, stdlib only** — the per-field walker raises in strict mode with a
  msgspec-shaped `$.path` message it builds itself. Zero new dependency in six wheels, zero C
  extension, single code path, no observable/strict drift risk. **Recommended** unless a measured
  decode-throughput requirement appears — none exists in this project (these are low-QPS REST
  clients, not a hot serialization loop).

Option (b) also dissolves the plan's stated C-extension/wheel-availability risk entirely and keeps
DT-01 (msgspec never in public signatures) trivially true by not depending on it at all.

---

## Feature Landscape

### Table Stakes (consumers assume these exist)

| Feature | Why Expected | Complexity | Notes / dependencies |
|---------|--------------|------------|----------------------|
| **T1 — Attribute-access typed model for every data return** (zero `Any`/`dict[str, Any]`) | Every modern Python SDK ships this (stripe ≥7.1, openai, google-cloud). Without it mypy cannot catch a field typo, which is the milestone's stated core value. Empirically verified: mypy flags `q.ultimoPrecioo` with *"maybe you meant ultimoPrecio?"* | MEDIUM | TYP-01/TYP-02. 16 iol signatures + 5 ops endpoints. Depends on DEC-01 landing first. |
| **T2 — Tolerant-by-default decode; API evolution never crashes the caller** | Universal across the peer set: stripe never validates responses; openai-python deliberately bypasses pydantic validation via `construct()` and sets `extra="allow"`; kubernetes drops unknown attrs silently. A market-data client that 500s because the vendor added a field is unusable. | LOW | Already the current behaviour. DT-02 keeps it. `msgspec` also ignores extras by default. |
| **T3 — Raw-payload escape hatch on every model (`to_dict()`)** | Universal: stripe `to_dict()`/`as_dict()`, openai `model_dump()`/`to_dict()`, pydantic `model_dump()`. It is simultaneously (a) the answer to "you didn't model the field I need", (b) the migration ramp for dict→model, and (c) what makes T2 honest — tolerance is only acceptable if the untouched payload is still reachable. | LOW | **Load-bearing for DT-08.** Without it the iol 0.2.0→0.3.0 break has no escape valve. Consider also carrying the unmodelled extra keys (dataclasses-json `CatchAll` precedent) — see D4b. |
| **T4 — `py.typed` + annotations clean under `mypy --strict`** | Table stakes since PEP 561; a typed surface consumers can't actually type-check is theatre. | LOW | Already true for 5/6 packages; **D-16 closure** (market-data-client into root mypy `files`, import-linter `root_packages`, `ci.yml:85`) is the gap. GATE-TYP-01. |
| **T5 — Package logger + `NullHandler`, root logger never touched** | Python Logging HOWTO convention; a library that spams the root logger gets uninstalled. | NONE | **Already shipped** (LOG-01, `_logging.attach()`). The divergence emission rides this. |
| **T6 — Migration guide / changelog callout for the return-type break** | Stripe wrote a full wiki migration guide for its v15 object change; every SDK with a breaking release does. DT-08 already mandates the README callout. | LOW | PUB-TYP-01. Precedent in-repo: the D-03 `CalendarDay` callout in market-data v0.4.0. |
| **T7 — `Literal` aliases for enum-like *input* params, checker-only** | The pattern already exists twice in-repo (`iol.InstrumentType`, `matriz/types.py`); `mercado="bcaba"` currently passes mypy and fails at the server. | LOW | DT-07. **Key property:** `Literal` is not enforced at runtime, so an incomplete set is a *type-check-time* inconvenience (suppressible with `# type: ignore`), **not** a runtime break — unless you add a runtime guard. That materially de-risks the plan's "Literal incompleto es peor que str" worry for inputs. |

### Differentiators (where this milestone is genuinely ahead of the peer set)

| Feature | Value Proposition | Complexity | Notes / dependencies |
|---------|-------------------|------------|----------------------|
| **D1 — Observable divergence emission** (one structured record per divergent field, through the package logger) | **No mainstream Python API client does this.** Stripe, openai, kubernetes and google all chose *silent* tolerance; the ecosystem's only policy knob (pydantic `extra`, marshmallow `unknown`, dataclasses-json `Undefined`) is a 3-state `ignore/allow/forbid` that covers **extra fields only** — none has any knob for *missing* or *wrong-type* fields, which are precisely the classes that turn into `0.0` today. This is the milestone's core value and it is a real gap in the ecosystem, not a reinvention. | HIGH | DEC-01. Requires the per-field walker (see headline finding), the record shape (below), and flat-`extra` emission (see A6). |
| **D2 — One decoder, two policies: observable (runtime) / strict (drivers)** | Turns the verification harness from "diff schemas after the fact" into "the decoder itself is the detector". Strict mode fails fast with an exact field path so a driver can file a finding instead of a human eyeballing a snapshot diff. | MEDIUM | DEC-01 + LIVE-TYP-01. **Recommended toggle: an explicit flag threaded on `_ClientState`**, exact precedent = `mutating_allowed` (GATE-MD-01) which already lives there and is inherited by `with_options` views for free. See A8 for why *not* env var / `warnings.simplefilter`. |
| **D3 — Divergence record carries endpoint + model FQN + surface** | A bare `"expected float got str"` log line is unactionable at 3am. With `endpoint` + `model` + `surface(sync\|async)` a record maps 1:1 onto a `verification/findings.py` entry — including the `SYNC-ASYNC-DRIFT` class when the same endpoint diverges on only one surface. | LOW (given D1) | Depends on the builders in `_core.py` already knowing the endpoint; the decoder must be *called with* that context, so parsers pass it down. |
| **D4 — Collectable report object (`DecodeReport`) returned/accumulated per response** | Forced by the headline finding: strict mode needs *all* divergences in a payload, not the first. A report object also gives the drivers a clean aggregation point per probe and makes the mocked tests ("emits exactly one record") trivially assertable. | MEDIUM | DEC-01. Internal type only — must **not** appear in public signatures (DT-01 spirit). Drivers reach it via the strict-mode exception payload or a context-scoped collector. |
| **D4b — Unmodelled wire keys preserved on the model (`extra` / CatchAll)** | dataclasses-json `Undefined.INCLUDE` + `CatchAll` and openai's `extra="allow"` precedent. Makes "wire-only" divergences *recoverable* rather than merely reported, and softens T3. | MEDIUM | Optional. Conflicts with `frozen=True, slots=True` purity — needs one dedicated slot. **Defer to v1.x** unless F33 shows real demand. |
| **D6 — Machine-enforced homogeneity gates** (AST surface check + non-vacuous sync/async parity introspection) | With no shared code by design (DT-03), homogeneity has no structural enforcer — it degrades in three releases. DT-09 correctly makes these first-class. The parity test is also the *affirmative* substitute for the permanently-archived REFAC-06 (DT-04). | MEDIUM | GATE-TYP-01. **Precedent warning:** Phase 15 WR-01/WR-02 shipped a *vacuous* AST guard that passed without checking anything — the parity test must assert it actually compared N>0 names. |
| **D7 — `types.py` present in all 6 packages with evidence-derived `Literal` sets** | Uniform shape means the next endpoint is born with somewhere to live; matriz already proves the pattern. | LOW | TYP-03. Empty-but-present in ámbito/wallets is the right call. |

### Anti-Features (do NOT build these)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **A1 — `__getitem__` / `Mapping` shim on models so old `dict` call sites keep working** | Obvious zero-churn ramp for the iol dict→model break; `q["ultimoPrecio"]` keeps compiling. | **Strongest negative evidence in this research.** `stripe-python`'s `StripeObject` inherited from `dict` for a decade and [RFC #1454](https://github.com/stripe/stripe-python/issues/1454) documents the result: `subscription.items` returned `dict.items` instead of the line items, and every field named `keys`/`values`/`get`/`items` was permanently shadowed. Stripe **removed dict inheritance in v15** as a deliberate breaking change. Worse here: a `__getitem__` shim *defeats the milestone's entire purpose* — `q["ultimoPrecioo"]` is exactly the string-keyed typo mypy cannot catch, so the shim preserves the bug class being eliminated. | `to_dict()` (T3) + a README migration table (old key → new attribute) + DT-08's 0.x-minor callout. This is what stripe, openai and pydantic all do. |
| **A2 — Fatal strict decoding as the runtime default** | "Never let bad data through" feels like the rigorous choice. | Trades silent incorrectness for loud unavailability in a **live market-data** client, where the vendor changes shapes without notice. Zero peer SDKs do this. | DT-02 (already locked): observable-not-fatal. Restated here so it isn't relitigated by a reviewer citing "strict typing". |
| **A3 — `Literal[...] \| str` for input params (the openai `Union[str, ChatModel]` pattern)** | openai-python uses exactly this to tolerate server-side enum growth, and it preserves IDE autocomplete. | **Empirically verified on this machine (mypy --strict, 2026-08-18): it provides ZERO type checking.** `Literal["bcba","nyse","nasdaq"] \| str` accepted the typo `"bcaba"` with no error — the union collapses to `str`. A closed `Literal` flagged the same call (`arg-type`). Adopting this pattern would satisfy DT-07 on paper while delivering none of the milestone's core value. | Closed `Literal` derived from live evidence (DT-07). Enum growth is safe because `Literal` is checker-only: a consumer needing a new value passes it and it *works at runtime*, with a suppressible type error until the next patch release. Where a **runtime** guard is genuinely needed, use the in-repo hybrid precedent: `matriz` BUG-01 CFI = `Literal` for the checker + permissive `\A[A-Z]{6}\Z` regex for runtime forward-compat. |
| **A4 — `Literal` on *response model* fields** | Symmetry with input params; "the API only returns these values". | Verified: `msgspec` **validates** Literal on decode — an unknown server value yields `Invalid enum value 'rofex' - at $.mercado`. On the response side an incomplete `Literal` converts vendor enum growth into a divergence storm (observable mode) or a hard failure (strict mode) on *legitimate* data. Asymmetric with A3: on inputs an incomplete Literal is a compile-time annoyance; on outputs it is a data lie. | `str` on response models. Reserve `Literal` for parameters. If a response enum must be typed, do it only after F33 closes the value set with live evidence, and prefer `str` + a documented constant tuple. |
| **A5 — Recording the offending *value* in the divergence record** | Makes the log line self-diagnosing: "got `'N/A'` where float expected". | Unbounded credential/PII leak surface. `RedactingFilter` is **marker-based** (`Bearer `, `"password"`, `"token"`, `cuit=`, …) — it only redacts strings containing a *known* marker, so an arbitrary field value in an unmodelled payload passes through untouched. Note `msgspec` itself never embeds the value, only its type — a deliberate design the decoder should copy. | Record `got_type` (`"str"`, `"null"`, `"absent"`) only. If a value sample is ever needed, gate it behind an explicit debug flag *and* extend the redaction markers, never by default. |
| **A6 — Passing the divergence record as a nested dict/dataclass under `extra=`** | Natural: `logger.warning(msg, extra={"divergence": asdict(rec)})`. | **Verified against `_logging.py`:** `RedactingFilter.filter` only redacts *top-level string values* in `record.__dict__`. A nested dict or dataclass is never traversed → the record bypasses redaction entirely, silently defeating LOG-02/SEC-01. | Flat, top-level, **all-`str`** extra keys (`divergence_kind`, `divergence_path`, `divergence_model`, …). Each is then individually scanned by the filter. Lock it with a `caplog` sentinel test (SEC-01 precedent). |
| **A7 — Counters / metrics / OpenTelemetry emission from inside the decoder** | "We should monitor divergence rate." | Research shows schema-drift monitoring is an **infrastructure-tier** concern in practice (OpenAPI contract tests in CI with `additionalProperties: false`, proxy/traffic diffing, OTel schema inference) — not an SDK feature. Adding an OTel dep to six minimal wheels for this is disproportionate, and `logging` already *is* the extension point: a consumer attaches a `logging.Handler` and counts. | Ship D1 (log records with flat structured fields). Document "count divergences by attaching a Handler to `logging.getLogger('<pkg>')`" in the README. |
| **A8 — Selecting decode policy via env var, module global, or `warnings.simplefilter`** | Zero API-surface change; `PYTHONWARNINGS`/`-W error` is idiomatic Python, and PEP 565 blesses custom warning categories for library-compat signals. | All three mutate **process-global** state. `warnings.catch_warnings()` is explicitly not thread-safe, and these packages run sync clients, `asyncio` loops and (matriz) a daemon WS thread concurrently. An env var also can't be scoped to one probe inside a driver that shares a process with other probes. | Explicit flag on `_ClientState` (exact precedent: `mutating_allowed`, inherited by `with_options` views for free) + a decoder-level parameter for the pure `_core` parsers. Optionally *also* emit a custom `DivergenceWarning` as a secondary channel, but never as the only control. |
| **A9 — A shared `market-libs-core` package for the decoder** | 6× duplication of a non-trivial walker is the milestone's biggest smell. | DT-03 (locked): the cost is not effort, it is coupling six independently-publishable release cycles. Same trade-off already accepted for `SafeModel`/`_coerce` (3×), `_transport`, `_logging`, `_validate_max_retries`. | Verbatim copy ×6 + a byte-identity or AST-equivalence test across the six copies so drift is *detected* even though it isn't *prevented*. (Cheap addition to GATE-TYP-01, worth proposing.) |
| **A10 — `msgspec` types anywhere in a public signature** | Convenience — `msgspec.Struct` is faster than a stdlib dataclass. | DT-01 (locked). Leaking a third-party type into six wheels' public API makes `msgspec` a permanent forced dep of every consumer. Already verified: `msgspec.convert(dict, type=StdlibDataclass)` works fine on `frozen=True, slots=True` stdlib dataclasses, so there is no reason to. | Stdlib frozen+slots dataclasses in signatures; `msgspec` internal-only — or, per the headline finding, possibly not at all. |
| **A11 — A dedicated `on_divergence=` callback kwarg on the client** | Consumers want programmatic reaction, not log scraping. | A second, parallel extension mechanism to `logging` that must be threaded through every parser, doubles the sync/async surface (DT-04 parity test now has to cover it), and has no consumer demand yet. Exception-safety of user callbacks inside a decode path is its own hazard. | `logging.Handler` is the callback. Revisit only if a real consumer asks after v1.6 ships. |

---

## Proposed divergence-record shape (concrete)

Internal frozen dataclass, one instance **per divergent field**:

```python
@dataclass(frozen=True, slots=True)
class Divergence:
    kind: Literal[
        "missing_field",    # declared by model, absent on wire  -> the 0.0 bug class
        "type_mismatch",    # present but wrong type             -> "1.5" instead of 1.5
        "null_value",       # explicit null in a non-optional field
        "unknown_field",    # on wire, not on model              -> upstream added a field
        "not_a_mapping",    # payload was not an object at all   -> today's silent {} fallback
    ]
    path: str            # "$.rows[1].ultimoPrecio"  — msgspec-compatible, safe to render
    model: str           # "iol_client.models.Quote"
    expected: str        # "float"
    got_type: str        # "str" | "null" | "absent" | "list"   -- NEVER the value (A5)
    substituted: str     # repr of the default actually used, e.g. "0.0"; "" in strict mode
    endpoint: str        # "GET /api/v2/{mercado}/Titulos/{simbolo}/Cotizacion"
    package: str         # "iol_client"
    surface: Literal["sync", "async"]
```

**Why these fields.** `path` + `expected` + `got_type` is exactly the triple `msgspec` chose after
optimising its own error messages, minus the value (A5). `substituted` is the field that makes the
record *honest about the old bug* — it is the answer to "what did my caller actually receive?", and
it is what no ecosystem library records. `endpoint` + `surface` + `model` are what turn a log line
into a finding (D3).

**Emission (observable mode)** — flat, all-`str`, redaction-compatible (A6):

```python
logger.warning(
    "decode divergence: %s at %s (expected %s, got %s)",
    rec.kind, rec.path, rec.expected, rec.got_type,
    extra={
        "divergence_kind": rec.kind,
        "divergence_path": rec.path,
        "divergence_model": rec.model,
        "divergence_expected": rec.expected,
        "divergence_got_type": rec.got_type,
        "divergence_substituted": rec.substituted,
        "divergence_endpoint": rec.endpoint,
        "divergence_package": rec.package,
        "divergence_surface": rec.surface,
    },
)
```

Level: `WARNING` for `missing_field` / `type_mismatch` / `null_value` / `not_a_mapping`;
`DEBUG` for `unknown_field` (upstream additions are routine and would otherwise flood logs).

**Strict mode → finding.** The record maps 1:1 onto the existing harness API
(`verification/findings.py:583`), which already has everything needed:

| `Divergence` field | `append_finding(...)` argument |
|---|---|
| — | `class_="SHAPE"` (already in `FINDING_CLASSES`; use `"SYNC-ASYNC-DRIFT"` when only one surface diverges) |
| `surface` | `surface=` |
| `endpoint` + `path` | `title=` (deterministic ⇒ `idempotent_by_title=True` dedupes across runs) |
| `model` + `expected` | `expected=` |
| `got_type` + `substituted` | `actual=` |
| full record | `diff=` |

No new harness code is required — this is a pure integration, which is a meaningful complexity
reduction for Phase 33.

---

## dict → model migration UX: options compared

Constraints: DT-05 (`from_api` preserved as a public constructor), DT-08 (`iol-client` 0.2.0 →
0.3.0, source-breaking inside a 0.x minor, with a README callout).

| Option | What it is | Evidence | Verdict |
|---|---|---|---|
| **1. Clean break + `to_dict()` + migration table** | `get_quote()` returns `Quote`; `Quote.to_dict()` returns the raw payload; README maps every old key to the new attribute. | Ecosystem default (stripe v15 wiki migration guide, openai `model_dump`, pydantic). | ✅ **Recommended.** Compatible with DT-05 (`from_api` untouched) and DT-08 (exactly the callout it prescribes). Preserves the core value: no string-keyed access survives. |
| **2. Mapping/`__getitem__` shim on the model** | Model also supports `q["ultimoPrecio"]`. | stripe-python lived this for a decade and [reversed it in v15](https://github.com/stripe/stripe-python/issues/1454) over `items`/`keys`/`get` collisions. | ❌ **Anti-feature (A1).** Also self-defeating: string keys are the typo vector being eliminated. |
| **3. Parallel methods** (`get_quote()` dict + `get_quote_typed()` model) | Both surfaces coexist for a release. | Common in large SDKs with big install bases. | ❌ Doubles 16 iol signatures to 32, then doubles again across sync/async — and the DT-04 parity test must cover both. Disproportionate for a 0.x package whose consumers are countable. |
| **4. `DeprecationWarning` on dict access for one minor, then remove** | Ship the shim, warn, delete in 0.4.0. | PEP 565 pattern; the `deprecated` package automates it. | ⚠️ Only viable *with* option 2, and inherits all of A1's collision problems for the duration. Skip. |
| **5. Transitional `.raw` attribute alongside the model** | `q.raw` is the untouched payload dict. | Not a distinct option — this is option 1 with a different spelling. | ➕ **Adopt as a naming choice if preferred over `to_dict()`.** `to_dict()` matches stripe/openai/pydantic convention; `.raw` is shorter. Pick one, apply to all six packages (TYP-03 homogeneity). |

**Recommendation: option 1, with `to_dict()`.** Add one pre-Phase-30 action the plan already
flags: *relevar quién consume iol* — if the answer is "only this repo's `main_iol.py`", the break is
free and options 2-4 are moot.

---

## Feature Dependencies

```
D1 Observable divergence emission  (DEC-01, Phase 29)
    ├──requires──> per-field walker (evolution of _coerce)   [NOT msgspec — headline finding]
    ├──requires──> T5 package logger + RedactingFilter        [ALREADY SHIPPED, LOG-01]
    ├──requires──> A6 flat all-str extra emission             [constraint, not a feature]
    └──requires──> D4 DecodeReport (multi-record accumulation)

D2 Strict mode  ──requires──> D1
    └──requires──> policy flag on _ClientState                [precedent: mutating_allowed]

D3 Rich record (endpoint/model/surface)
    └──requires──> _core.py parsers pass endpoint context into the decoder

T1 Typed returns (TYP-01/02, Phases 30-31)
    └──requires──> D1  (a model with no observable decoder just relocates the silence)
    └──requires──> T3 to_dict()   [migration escape hatch — must land WITH the break, not after]

T7 Literal input params
    └──requires──> LIVE-TYP-01 evidence (DT-07)  -- may stay `str` if unclosable
    ──conflicts──> A3 (Literal | str)  and  A4 (Literal on response fields)

D6 Homogeneity gates (GATE-TYP-01, Phase 32)
    └──requires──> T1 + T3 landed everywhere (else the gate fails on its own repo)
    └──requires──> D-16 closure (market-data-client into mypy files / import-linter / ci.yml:85)

LIVE-TYP-01 (Phase 33)
    └──requires──> D2 + D3  (strict mode is the detector; record shape is the finding)
    └──enables───> T7 value-set closure  and  PUB-TYP-01 scope (which packages actually changed)
```

### Dependency notes

- **D1 must precede T1.** Typing `iol` without the observable decoder converts a silent `0.0` into a
  silent `0.0` *with a type annotation on it*. The plan's ordering (F29 load-bearing first) is right.
- **T3 must ship in the same release as the break.** A migration guide that says "use `to_dict()`"
  is worthless if `to_dict()` arrives in the next version.
- **The plan's F29-exploratory-strict-run mitigation is the highest-leverage item in the milestone.**
  Because `msgspec` reports only the first error per payload, the *count* of divergences discovered
  in that run is a function of the decoder design — a first-error-only implementation will
  under-report and give false confidence about F33's scope. Size F33 with the **per-field walker**,
  not with a `msgspec` strict pass.
- **A4 conflicts with T7's symmetry instinct.** Expect a reviewer to propose Literal-typing response
  enums "for consistency". The asymmetry is deliberate and evidence-backed.

---

## MVP Definition

### Launch with (Phase 29 — DEC-01, load-bearing)

- [ ] **Per-field observable walker** replacing `_coerce` in the 3 packages with models, `from_api`
      signature untouched (DT-05) — merge gate: existing suites green **with zero test changes**
- [ ] **`Divergence` record + flat all-`str` logger emission** through the existing `RedactingFilter`
- [ ] **`DecodeReport`** accumulating N records per response (internal only)
- [ ] **Strict mode** via an explicit `_ClientState` flag, raising with the full record set
- [ ] **`to_dict()`** on the model base (needed by T1/T3 in Phase 30, cheap to land now)
- [ ] **Adversarial mocked tests**: missing field, wrong type, extra key, non-dict payload, `None`,
      204; observable emits *exactly one* record per divergence and does not raise; strict raises
      with the field path; `caplog` sentinel proves no credential leak (SEC-01 precedent)
- [ ] **msgspec go/no-go decision recorded** (option (a) vs (b) from the headline finding)
- [ ] **Exploratory strict run** to size Phase 33 before committing 30-32

### Add after validation (Phases 30-34, as planned)

- [ ] T1 typed returns — iol (F30), ops endpoints (F31)
- [ ] T7 `Literal` inputs closed with F33 live evidence
- [ ] D6 AST surface gate + non-vacuous parity test + D-16 (F32)
- [ ] Cross-package decoder byte/AST-equivalence test (cheap addition to F32; mitigates A9's real cost)
- [ ] T6 migration guide + per-package bumps (F34)

### Future consideration (v1.7+)

- [ ] **D4b** unmodelled-key preservation (CatchAll) — defer until F33 shows real demand
- [ ] **A11** `on_divergence=` callback — only on explicit consumer request
- [ ] **A7** metrics/OTel — infra-tier; a `logging.Handler` covers it today
- [ ] Response-side `Literal` typing — only after two consecutive clean live cycles close the sets

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| D1 observable divergence emission | HIGH | HIGH | **P1** |
| D4 DecodeReport (multi-record) | HIGH | MEDIUM | **P1** (forced by msgspec first-error-only) |
| D2 strict mode via `_ClientState` flag | HIGH | LOW | **P1** |
| T3 `to_dict()` escape hatch | HIGH | LOW | **P1** (blocks DT-08 migration) |
| T1 typed returns (iol, 16 sigs) | HIGH | MEDIUM | **P1** |
| D3 endpoint/model/surface in record | MEDIUM | LOW | **P1** (near-free, unlocks F33) |
| T7 `Literal` input params | MEDIUM | LOW | **P1** (contingent on F33 evidence) |
| D6 AST + parity gates | MEDIUM | MEDIUM | **P1** (DT-09 makes it first-class) |
| T4/D-16 market-data mypy enrolment | MEDIUM | LOW | **P1** (long-deferred, cheap) |
| T2 tolerant default | HIGH | NONE | **P1** (already shipped; do not regress) |
| T6 migration guide | MEDIUM | LOW | **P1** |
| D7 `types.py` in all 6 | LOW | LOW | **P2** |
| Cross-package decoder equivalence test | MEDIUM | LOW | **P2** |
| D4b CatchAll extras | LOW | MEDIUM | **P3** |
| A11 callback hook | LOW | MEDIUM | **P3** (leaning never) |
| A7 metrics/OTel | LOW | HIGH | **P3** (leaning never) |

---

## Competitor Feature Analysis

| Behaviour | stripe-python | openai-python | kubernetes-client | msgspec (raw) | **market-libs v1.6** |
|---|---|---|---|---|---|
| Response validation | none | bypassed (`construct()`) | minimal (`client_side_validation`) | strict, first-error | **observable per-field** |
| Extra wire field | tolerated | preserved (`extra="allow"`) | dropped | ignored silently | **DEBUG record** |
| Missing field | tolerated | as-is / `None` | dropped | raises (no root path) | **WARNING record + typed default** |
| Wrong type | tolerated | returned as-is | as-is | raises w/ `$.path` | **WARNING record + typed default** |
| Divergence telemetry | ❌ | ❌ | ❌ | ❌ (exception only) | ✅ **the differentiator** |
| Item + attribute access | dict-inherited → **removed in v15** | attribute only | attribute only | n/a | **attribute only** (learn from v15) |
| Raw payload escape | `to_dict()`/`as_dict()` | `model_dump()`/`to_dict()` | `to_dict()` | `to_builtins()` | **`to_dict()`** |
| Enum-growth strategy | API-version pinning | `Union[str, Literal]` | open `str` | validates Literal | **closed `Literal` (inputs only), `str` on responses** |
| Strict/lenient toggle | ❌ | ❌ | `Configuration.client_side_validation` | `strict=` kwarg | **`_ClientState` flag** |
| Drift detection venue | server-side versioning | none | none | n/a | **inside the client** |

---

## Confidence & gaps

| Claim | Confidence | Basis |
|---|---|---|
| `msgspec` behaviour table (extras/missing/type/Literal/first-error/paths) | **HIGH** | First-party run, `msgspec 0.21.1`, this machine, 2026-08-18 |
| `Literal[...] \| str` gives zero mypy coverage | **HIGH** | First-party `mypy --strict` run, 2026-08-18 |
| `RedactingFilter` does not traverse nested `extra=` values | **HIGH** | Direct read of `_logging.py:85-99` |
| `append_finding` maps cleanly to the record shape | **HIGH** | Direct read of `verification/findings.py:583` + `FINDING_CLASSES` |
| stripe v15 removed dict inheritance and why | **MEDIUM** | Primary source (RFC #1454) via WebFetch, corroborated by release notes/migration wiki |
| openai-python bypasses validation, `extra="allow"` | **MEDIUM** | Secondary (DeepWiki source analysis) + corroborating issue #2204 |
| pydantic/marshmallow/dataclasses-json 3-state, none covers missing/wrong-type | **MEDIUM** | Multiple corroborating docs pages |
| kubernetes `client_side_validation` as a policy-toggle precedent | **LOW** | Thin, mostly issue-tracker chatter; its real scope is narrower than the name suggests |
| "No mainstream Python client emits divergence telemetry" | **LOW-MEDIUM** | Absence of evidence across 4 surveyed SDKs + schema-drift literature being infra-tier. Argues *for* the differentiator claim but cannot be proven exhaustively |
| Schema-drift monitoring is infra-tier not SDK-tier | **LOW** | Search returned mostly vendor/SEO content, not primary engineering sources |

**Open questions for Phase 29 discussion:**

1. `msgspec` two-engine vs stdlib-only single-engine (headline finding) — a genuine architectural
   fork with a dependency-profile consequence across six wheels.
2. `to_dict()` vs `.raw` naming — must be decided once and applied to all six (TYP-03).
3. Does anything outside this repo consume `iol-client` 0.2.0? Determines whether options 2-4 of the
   migration comparison need any consideration at all.
4. `unknown_field` at DEBUG vs WARNING — DEBUG avoids log floods but means the F33 exploratory run
   must raise the level deliberately or it will under-count wire-only drift.

## Sources

- [stripe/stripe-python RFC #1454 — What if StripeObject didn't inherit from dict?](https://github.com/stripe/stripe-python/issues/1454)
- [stripe/stripe-python — Migration guide for v15](https://github.com/stripe/stripe-python/wiki/Migration-guide-for-v15)
- [stripe/stripe-python — Inline type annotations](https://github.com/stripe/stripe-python/wiki/Inline-type-annotations)
- [openai/openai-python — Pydantic Models and BaseModel (DeepWiki)](https://deepwiki.com/openai/openai-python/5.4-pydantic-models-and-basemodel)
- [openai/openai-python issue #2204 — Response constructed to wrong type in discriminated union](https://github.com/openai/openai-python/issues/2204)
- [openai/openai-python issue #1300 — ChatCompletions create() doesn't type-check enums as role](https://github.com/openai/openai-python/issues/1300)
- [msgspec — Usage (strict vs lax decoding)](https://msgspec.dev/usage)
- [msgspec issue #425 — Support using default value if provided data was invalid, rather than erroring](https://github.com/msgspec/msgspec/issues/425)
- [Pydantic — Model config (`extra`: ignore/allow/forbid)](https://docs.pydantic.dev/latest/api/config/)
- [kubernetes-client/python issue #1800 — client_side_validation](https://github.com/kubernetes-client/python/issues/1800)
- [PEP 565 — Show DeprecationWarning in `__main__`](https://peps.python.org/pep-0565/)
- [Python docs — `warnings` — Warning control](https://docs.python.org/3/library/warnings.html)
- [Total Shift Left — API Schema Validation / drift detection guide](https://totalshiftleft.ai/blog/api-schema-validation-catching-drift)
- First-party empirical runs (2026-08-18): `mypy --strict` on `Literal | str` + dataclass attr typo;
  `msgspec 0.21.1` `convert()` against frozen+slots stdlib dataclasses (7 divergence cases, nested paths)
- In-repo primary sources: `packages/higyrus-client/src/higyrus_client/_logging.py:85`,
  `packages/higyrus-client/src/higyrus_client/models.py:30-89`, `verification/findings.py:44-88,583`,
  `verification/safemodel_diff.py`, `.planning/future-plans/tipado_homogeneo.md`

---
*Feature research for: typed public surface + observable decoding, market-libs v1.6*
*Researched: 2026-08-18*
