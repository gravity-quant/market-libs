---
phase: 29-decoder-observable
reviewed: 2026-08-19T00:00:00Z
depth: standard
files_reviewed: 57
files_reviewed_list:
  - .github/workflows/ci.yml
  - packages/ambito-financiero-client/src/ambito_financiero_client/__init__.py
  - packages/ambito-financiero-client/src/ambito_financiero_client/_decode.py
  - packages/ambito-financiero-client/src/ambito_financiero_client/_logging.py
  - packages/ambito-financiero-client/src/ambito_financiero_client/_state.py
  - packages/ambito-financiero-client/src/ambito_financiero_client/aio.py
  - packages/ambito-financiero-client/src/ambito_financiero_client/client.py
  - packages/ambito-financiero-client/src/ambito_financiero_client/exceptions.py
  - packages/ambito-financiero-client/tests/test_decode.py
  - packages/ambito-financiero-client/tests/test_logging.py
  - packages/higyrus-client/src/higyrus_client/__init__.py
  - packages/higyrus-client/src/higyrus_client/_decode.py
  - packages/higyrus-client/src/higyrus_client/_logging.py
  - packages/higyrus-client/src/higyrus_client/_state.py
  - packages/higyrus-client/src/higyrus_client/aio.py
  - packages/higyrus-client/src/higyrus_client/client.py
  - packages/higyrus-client/src/higyrus_client/exceptions.py
  - packages/higyrus-client/src/higyrus_client/models.py
  - packages/higyrus-client/tests/test_decode.py
  - packages/higyrus-client/tests/test_logging.py
  - packages/iol-client/src/iol_client/__init__.py
  - packages/iol-client/src/iol_client/_decode.py
  - packages/iol-client/src/iol_client/_logging.py
  - packages/iol-client/src/iol_client/_state.py
  - packages/iol-client/src/iol_client/aio.py
  - packages/iol-client/src/iol_client/client.py
  - packages/iol-client/src/iol_client/exceptions.py
  - packages/iol-client/tests/test_decode.py
  - packages/iol-client/tests/test_logging.py
  - packages/market-data-client/src/market_data_client/__init__.py
  - packages/market-data-client/src/market_data_client/_decode.py
  - packages/market-data-client/src/market_data_client/_logging.py
  - packages/market-data-client/src/market_data_client/_state.py
  - packages/market-data-client/src/market_data_client/aio.py
  - packages/market-data-client/src/market_data_client/client.py
  - packages/market-data-client/src/market_data_client/exceptions.py
  - packages/market-data-client/src/market_data_client/models.py
  - packages/market-data-client/tests/test_decode_concurrency.py
  - packages/market-data-client/tests/test_decode.py
  - packages/market-data-client/tests/test_logging.py
  - packages/matriz-client/src/matriz_client/__init__.py
  - packages/matriz-client/src/matriz_client/_decode.py
  - packages/matriz-client/src/matriz_client/_logging.py
  - packages/matriz-client/src/matriz_client/_state.py
  - packages/matriz-client/src/matriz_client/aio.py
  - packages/matriz-client/src/matriz_client/client.py
  - packages/matriz-client/src/matriz_client/exceptions.py
  - packages/matriz-client/src/matriz_client/models.py
  - packages/matriz-client/src/matriz_client/ws_client.py
  - packages/matriz-client/tests/test_decode.py
  - packages/matriz-client/tests/test_logging.py
  - packages/matriz-client/tests/test_ws_decode_mode.py
  - tools/check_decode_intactness.py
  - verification/snapshots/ambito-financiero-client-surface.txt
  - verification/snapshots/higyrus-client-surface.txt
  - verification/snapshots/iol-client-surface.txt
  - verification/snapshots/matriz-client-surface.txt
findings:
  critical: 4
  warning: 7
  info: 4
  total: 15
status: issues_found
---

# Phase 29: Code Review Report

**Reviewed:** 2026-08-19
**Depth:** standard
**Files Reviewed:** 57
**Status:** issues_found

## Summary

The phase ships a per-field decode walker in five verbatim copies, a strict/observable
mode carrier, a bounded nested-scan redaction fix, and a normalize-then-hash CI gate.
The mechanical parts hold up: `tools/check_decode_intactness.py` runs clean (5 copies →
one hash `a5889d57`, 5 scan regions → one hash `684191c7`), the copies differ only in the
documented per-package deltas, and 178 decode tests pass in 0.15s.

The behavioural core does not hold up. Four findings are reproducible defects that
defeat the phase's own stated guarantees, and every one of them is invisible to the
green test suite:

1. The decode scope is bound with `.set()` and never unbound, so on the sync surface
   **every decode that does not originate in `_request` inherits the previous request's
   dedupe set and reports nothing** — the exact false pass lock 6 says it rejects.
2. The dedupe triple is recorded **before** the strict-mode raise, so a caught-and-retried
   decode inside one scope silently substitutes the default, emits no record and does not
   raise — a strict-mode bypass.
3. `market_data_client.MarketDataSnapshot.market_data` is declared `dict[str, Any]` and
   decodes to `None` with **no divergence record and no strict raise**. The walker's
   missing dict branch is sanctioned, but the call-site lever that compensates for it was
   only built for matriz; market-data has a dict field and never got one.
4. On an `extra` divergence the **wire's own key name** travels verbatim into
   `field_path`. Lock 11 states there is no key in the schema in which a wire value can
   travel; that is false. A key containing a newline injects a forged line into every text
   handler, and the marker-anchored redactor provably does not cover bare identifiers.

Findings 1-3 were each confirmed by direct execution against the shipped code, not
inferred. Reproductions are inlined.

All four are BLOCKERs against the phase's own contract (`29-AGGREGATION-CONTRACT.md`),
not against a reviewer's preference.

## Critical Issues

### CR-01: Stale request scope silences every decode not initiated by `_request`

**File:** `packages/higyrus-client/src/higyrus_client/_decode.py:214-236`, and the four
sibling copies; bind sites `packages/higyrus-client/src/higyrus_client/client.py:375-376`,
`packages/higyrus-client/src/higyrus_client/aio.py:364-365`,
`packages/market-data-client/src/market_data_client/client.py:377-378`,
`packages/matriz-client/src/matriz_client/client.py:411-412`,
`packages/iol-client/src/iol_client/client.py:459-460`,
`packages/ambito-financiero-client/src/ambito_financiero_client/client.py:237-238`

**Issue:** `open_request_scope()` does `DECODE_SCOPE.set(scope)` with no token and no
reset — correctly so for the mode carrier, since the parser runs after `_request`
returns. But the consequence for the *scope* carrier is not the same as for the mode
carrier. On the sync surface the context is the caller's own, never a per-task copy, so
after one HTTP call the scope stays bound for the rest of the thread's life. Every
subsequent `Model.from_api()` — a supported public entry point (DT-05), and the entry
point lock 6 explicitly writes a per-call fallback for — reuses the previous request's
`_seen` set and emits nothing.

`current_sink()`'s "no scope bound → fresh per-call scope" fallback (`:226-236`) is
therefore dead after the first request in the process.

Reproduced against the shipped code:

```python
# no scope bound: both calls report
Posicion.from_api(payload)   # 20 records
Posicion.from_api(payload)   # 20 records

# after open_request_scope() (i.e. after ANY client call):
_decode.open_request_scope()
Posicion.from_api(payload)   # 20 records
Posicion.from_api(payload)   #  0 records   <-- silently clean decode of a divergent payload
```

Lock 6 rejects a process-lifetime scope in these words: "it would make the second
identical response decode silently clean … That is a false pass, which is precisely what
this milestone exists to eliminate." The `.set()`-without-reset bind reintroduces exactly
that for the standalone-`from_api` path.

**Fix:** make the outermost decode entry own its scope instead of inheriting an
unbounded one. `walk_model` already knows whether it is outermost (`sink is None`), so
bind/reset there rather than relying on the request-lifetime bind, and have `_request`
hand its scope down explicitly:

```python
def open_request_scope() -> DecodeScope:
    scope = DecodeScope()
    DECODE_SCOPE.set(scope)
    return scope


def take_request_scope() -> DecodeScope:
    """Consume the request-bound scope exactly once, then unbind it."""
    scope = DECODE_SCOPE.get()
    DECODE_SCOPE.set(None)          # a second decode gets a FRESH scope, not this one
    return scope if scope is not None else DecodeScope()
```

and in each `SafeModel.from_api`, replace `sink=_decode.current_sink()` with
`sink=_decode.take_request_scope()`. A top-level `list[Model]` parse must still share one
scope — pass the taken scope down from the `_core` parser rather than taking it per
element. Add a regression test asserting that two consecutive `Model.from_api(payload)`
calls after a simulated `_request` bind produce two identical record sets.

---

### CR-02: Strict mode is bypassed on any re-decode within one scope

**File:** `packages/higyrus-client/src/higyrus_client/_decode.py:169-181` (and all five
copies)

**Issue:** `DecodeScope.__call__` adds the triple to `self._seen` **before** evaluating
the strict-mode raise:

```python
triple = (model, path, kind)
if triple in self._seen:
    return                       # <-- second visit: no raise, no record
self._seen.add(triple)           # <-- recorded even though nothing was reported
if kind not in _INFO_KINDS and STRICT_DECODE.get():
    raise HigyrusDecodeError(path, declared, observed, model)
_emit(model, path, kind, declared, observed)
```

When strict mode raises, `_emit` never runs — so the divergence is marked "already
reported" while nothing was reported. Any second decode of the same divergence inside the
same scope then takes the `return` branch: no raise, no record, and the policy default is
substituted silently. This is a strict-mode escape, and the ws frame handler
(`ws_client.py:159-166`) is a caught-and-continue path of exactly this shape.

Reproduced with a single-divergence payload:

```
attempt1 raised: decode divergence in Parking.diasParking: declared int, observed str
attempt2 NO RAISE -> STRICT BYPASS. diasParking = 0   records emitted: []
```

The same hole exists in observable mode: a divergence suppressed by an exception that
aborted the emit is never re-reported inside the scope.

**Fix:** only record the triple once the divergence has actually been disposed of, and
emit before raising so a strict run still leaves the record on disk:

```python
def __call__(self, model, path, kind, declared, observed) -> None:
    triple = (model, path, kind)
    if triple in self._seen:
        return
    strict = kind not in _INFO_KINDS and STRICT_DECODE.get()
    if not strict:
        self._seen.add(triple)
    _emit(model, path, kind, declared, observed)   # record survives the raise
    if strict:
        raise HigyrusDecodeError(path, declared, observed, model)
```

Note this is a five-copy edit; re-run `tools/check_decode_intactness.py` afterwards.

---

### CR-03: `MarketDataSnapshot.market_data` silently decodes to `None` — no record, no strict raise

**File:** `packages/market-data-client/src/market_data_client/models.py:133`;
walker fall-through at `packages/market-data-client/src/market_data_client/_decode.py:392`

**Issue:** `market_data: dict[str, Any]` is a declared, non-optional field. The walker has
no `dict` branch, so `walk_field` falls through every arm to the bare `return value` and
hands back whatever the payload had — `None` when the key is absent. Nothing is reported
in observable mode and nothing raises in strict mode.

matriz solved this at the call site (`matriz_client/models.py:99-151`,
`_mapping_value` / `_apply_mapping_policy`), which is the sanctioned lever. market-data
declares a mapping field too and never got one, so the package's own flagship model
carries a field whose divergence is completely invisible — the precise class of silent
substitution DEC-01 exists to surface — *and* violates its own type declaration by
holding `None` where `dict[str, Any]` is annotated.

Reproduced:

```
market_data = None (declared dict[str, Any])
records: []
strict mode: NO RAISE; market_data = None
```

Per lock 2 an absent declared key is a `missing` divergence; per lock 3 that is WARNING;
per lock 4 it is fatal in strict mode. All three are unmet here.

**Fix:** port matriz's call-site pass to market-data (keeping `_decode.py` byte-verbatim),
in `market_data_client/models.py`:

```python
def _mapping_value(value: Any, *, path: str, model: str, sink: _decode.DecodeScope) -> Any:
    if isinstance(value, dict):
        return value
    sink(model, path, "missing" if value is None else "type", "dict", type(value).__name__)
    return {}
```

applied to every `dict`-declared top-level field after `walk_model` in
`SafeModel.from_api` and in `MarketDataSnapshot.from_api`, and mirror matriz's
`test_no_mapping_carrying_model_is_ever_a_nested_field_type` precondition test. Add a
test asserting `MarketDataSnapshot.from_api({...no market_data...})` emits one `missing`
record and raises in strict mode.

---

### CR-04: Wire-controlled key names travel verbatim into `field_path` on `extra` records

**File:** `packages/higyrus-client/src/higyrus_client/_decode.py:425-426` (and all five
copies); contract claim at `29-AGGREGATION-CONTRACT.md` lock 11

**Issue:**

```python
for key in sorted(set(data) - names):
    scope(model, f"{path}.{key}", "extra", "-", type(data[key]).__name__)
```

`key` is a **payload-supplied JSON object key**. Lock 11 is the phase's stated security
guarantee — "`field_path` and `model` carry *identifiers from our own source code*, never
payload content … There is no key in that schema in which a wire value can travel" — and
the `extra` kind falsifies it. Three concrete consequences, all reproduced against the
shipped code with `RedactingFilter` attached:

```
extra '.Bearer ***'                                   # only survived because of a marker
extra '.cuit=***'                                     # only survived because of a marker
extra '.a\nWARNING:root: forged log line'             # LOG INJECTION — newline reaches the record
extra '.XXXXXXXX…' (200 chars)                        # unbounded payload-controlled length
```

- **Log injection.** A key containing `\n` renders as an additional, attacker-shaped line
  in any text/`logging.Formatter` handler and as a forged field in naive log shippers.
- **Unredactable identifiers.** The redaction chain is marker-anchored by design, and the
  repo's own `test_account_id_not_redacted` asserts identifier-shaped values are
  deliberately *not* redacted. A bare CUIT, account number or token-shaped key with no
  `Bearer `/`cuit=` marker ships intact to every downstream handler (Sentry, etc.).
  Lock 11 accepted that risk only on the premise that no payload content reaches the
  record; the premise is wrong.
- **Unbounded size.** Key length is payload-controlled, so a large or hostile object
  inflates every record.

This also propagates: lock 10 maps `field_path` into the Phase 33 finding `surface` and
`fid`, so payload-controlled strings become finding identifiers.

**Fix:** sanitize and bound the wire-derived segment before it enters the record. Keep it
useful (the key name is the point of the `extra` kind) but make it non-injectable:

```python
_KEY_SAFE_RE = re.compile(r"[^0-9A-Za-z_\-.]")
_MAX_KEY_LEN = 64

def _safe_key(key: str) -> str:
    """A wire key is payload content: strip control chars, bound the length (lock 11)."""
    cleaned = _KEY_SAFE_RE.sub("?", key)
    return cleaned if len(cleaned) <= _MAX_KEY_LEN else cleaned[:_MAX_KEY_LEN] + "..."

for key in sorted(set(data) - names):
    scope(model, f"{path}.{_safe_key(str(key))}", "extra", "-", type(data[key]).__name__)
```

`str(key)` also closes a smaller hole: JSON keys are always `str`, but a hand-built dict
passed to `from_api` can carry a non-`str` key, and `f"{path}.{key}"` would then stringify
an arbitrary object's `__repr__` into the record. Amend lock 11 to state the sanitization
rather than the (currently false) absolute, and add a per-package test asserting a
newline-bearing and an over-long wire key are neutralized.

## Warnings

### WR-01: `DecodePolicy.non_dict_model` is inert — the documented mechanism does not exist

**File:** `packages/higyrus-client/src/higyrus_client/_decode.py:115` and `:427-434`;
`packages/matriz-client/src/matriz_client/models.py:196-203`;
`29-SEMANTICS-MATRIX.md` Section 2

**Issue:** `non_dict_model` is declared on `DecodePolicy`, assigned per package
(`"from_api_none"` vs `"empty_classmethod"`), asserted by five tests — and **read by no
code path anywhere in the repo**. `walk_model`'s non-dict branch runs the identical
`data = {}` substitution for all five packages. Setting matriz's value to
`"from_api_none"` would change nothing.

Two documents assert otherwise. `matriz_client/models.py:198` claims "`POLICY`'s
`non_dict_model = "empty_classmethod"` **makes** the walker emit the single terminal
`non_dict` record … and produce the all-defaults kwargs". It does not; the walker does
that unconditionally. And the matrix's central safety argument — "There is no
unparameterized path in the walker, so harmonizing a cell requires editing a named
constant" — is untrue for this axis: the cell is decorative, and the behaviour it names
is hard-coded.

**Fix:** either make the field load-bearing (branch on it in `walk_model`, and have
matriz's `from_api` early-return `cls.empty()` under `"empty_classmethod"` as the matrix
row 5 describes), or delete it from `DecodePolicy` and record in the matrix that the
non-dict fallback converged on one implementation. Correct
`matriz_client/models.py:196-203` either way — a docstring that attributes behaviour to an
unread constant is worse than no docstring.

---

### WR-02: An absent nested-model key is reported as `non_dict`, attributed to the wrong model

**File:** `packages/higyrus-client/src/higyrus_client/_decode.py:342-343` and `:434`

**Issue:** `walk_field`'s model branch recurses unconditionally, so a *missing key* whose
declared type is a nested model reaches `walk_model` as `payload=None` and is emitted as
`non_dict` rather than `missing`. Worse, the `model` field of that record is the **nested**
class while `field_path` is rooted at the outer decode root. Observed on
`Cuenta.from_api({"id": "1"})`:

```
('WARNING', 'missing',  'Cuenta',                 '.tipo',                   'str', 'NoneType')
('WARNING', 'non_dict', 'DisposicionesGenerales', '.disposicionesGenerales', ...,   'NoneType')
('WARNING', 'non_dict', 'Administrador',          '.administrador',          ...,   'NoneType')
```

Lock 2 defines `missing` as "the model declares the field but the payload has no key for
it" — which is what happened. Lock 1 defines `model` as the class being decoded, paired
with `field_path` to "name the exact decode site"; `DisposicionesGenerales` +
`.disposicionesGenerales` names no site that exists. Lock 10 feeds exactly that pair into
Phase 33's `surface` and `fid`, so the misattribution becomes a permanent finding
identity. matriz is affected more heavily — roughly ten nested-model fields, every one of
them defaulted via `field(default_factory=X.empty)`.

**Fix:** classify before recursing:

```python
if _is_model(hint):
    if value is None:
        sink(model, path, "missing", _name_of(hint), "NoneType")
        return hint(**walk_model(hint, {}, path=path, policy=policy, sink=SILENT_SINK))
    return hint(**walk_model(hint, value, path=path, policy=policy, sink=sink))
```

A genuinely non-dict (not `None`) nested payload keeps the `non_dict` kind and the nested
`model` attribution, which is correct for that case.

---

### WR-03: Nested models are constructed with `hint(**walk_model(...))`, bypassing every `from_api` override

**File:** `packages/higyrus-client/src/higyrus_client/_decode.py:342-343` (all five copies)

**Issue:** the walker builds a nested model by calling the constructor directly, never
`hint.from_api(value)`. Every per-model exemption blessed by `29-SEMANTICS-MATRIX.md`
Section 3 lives in a `from_api` override and is therefore skipped for any nested
occurrence:

- matriz's `_apply_mapping_policy` (`matriz_client/models.py:126-151`) — a nested model
  with a `dict` field would land on `None` instead of `{}`, violating its own type
  annotation. Acknowledged in the docstring and pinned by
  `test_no_mapping_carrying_model_is_ever_a_nested_field_type`.
- market-data's `Symbol.from_api` `market_id` → `marketId` mirror
  (`market_data_client/models.py:507-508`) — a nested `Symbol` would carry `""` for the
  deprecated alias again.
- market-data's `MarketDataSnapshot.from_api` `received_at` injection (`:169-173`) — a
  nested snapshot would take a wire `received_at`, defeating the D-01 fidelity contract.

Only the matriz case has a guard; the two market-data cases have none. The failure mode is
silent in all three.

**Fix:** prefer the model's own constructor when it declares one:

```python
if _is_model(hint):
    from_api = getattr(hint, "from_api", None)
    if getattr(from_api, "__func__", None) is not getattr(_BASE_FROM_API, "__func__", None):
        return from_api(value)      # respects the model's declared exemption
    return hint(**walk_model(hint, value, path=path, policy=policy, sink=sink))
```

If that is too invasive for a byte-verbatim file, at minimum add the market-data
counterpart of matriz's precondition test — a test asserting no model carrying a
`from_api` override is ever another model's declared field type — so the two unguarded
exemptions fail loudly the day someone nests them.

---

### WR-04: Fields made optional by a dataclass default are reported as `missing` and are fatal in strict mode

**File:** `packages/higyrus-client/src/higyrus_client/_decode.py:436-446`

**Issue:** `walk_model` supplies a value for **every** declared field, so
`dataclasses.Field.default` / `default_factory` never applies, and an absent key always
produces a `missing` divergence. Model authors used defaults precisely to express "the
wire may omit this": `Symbol.id: int = 0`, `market_id: str = ""`, `created_at: str = ""`,
`updated_at: str = ""` (`market_data_client/models.py:485-488`) and every
`field(default_factory=X.empty)` in matriz. Each of those now emits a WARNING on a
perfectly normal payload and **raises** in strict mode.

This is the same failure shape lock 4 rejected for `extra` keys — making a routine,
expected condition fatal — and it directly inflates the Phase 33 finding budget with
noise that has no modelling signal.

**Fix:** treat "declared with a default" as an opt-in to absence, the way `T | None`
already is. In `walk_model`, skip the divergence when the key is absent *and* the field
declares a default:

```python
_MISSING = object()
...
raw = data.get(f.name, _MISSING)
absent_but_defaulted = raw is _MISSING and (
    f.default is not MISSING or f.default_factory is not MISSING
)
kwargs[f.name] = walk_field(
    None if raw is _MISSING else raw,
    hints[f.name],
    path=f"{path}.{f.name}",
    model=model,
    policy=policy,
    sink=SILENT_SINK if absent_but_defaulted else field_sink,
)
```

If instead the current behaviour is intended, say so explicitly in the semantics matrix as
an eighth axis, because it changes what "optional" means for every model in the repo and
Phase 33 will budget against it.

---

### WR-05: matriz's `auth_basic` pre-scan silently falls through on malformed input, leaking the password

**File:** `packages/matriz-client/src/matriz_client/_logging.py:132-145` and `:233-237`

**Issue:** `_redact_auth_basic_tuple` returns `None` for "any malformed input (non-tuple,
wrong arity, non-string members)". The caller then does nothing:

```python
split = _redact_auth_basic_tuple(record.__dict__["auth_basic"])
if split is not None:
    del record.__dict__["auth_basic"]
    record.__dict__.update(split)
# else: the credential-bearing value stays in the record
```

The generic scan that follows will not save it — `_redact_nested` only rewrites string
leaves that contain a redaction marker, and a bare password contains none. So
`auth_basic=["user", "pw"]` (a list rather than a tuple), a 3-tuple, or a `bytes`
password ships the secret to every downstream handler. The inline comment at `:230-232`
asserts the opposite outcome ("otherwise the tuple would survive as a non-string field and
leak the password") for the case it does not actually cover.

**Fix:** fail closed — an `auth_basic` key that cannot be split is redacted wholesale
rather than passed through:

```python
if "auth_basic" in record.__dict__:
    split = _redact_auth_basic_tuple(record.__dict__["auth_basic"])
    del record.__dict__["auth_basic"]
    record.__dict__.update(split if split is not None else {"auth_basic": "***"})
```

Add a test for each malformed shape (list, wrong arity, non-str member) asserting the
secret literal is absent from `record.__dict__`.

---

### WR-06: The WebSocket path silently downgrades strict mode to observable

**File:** `packages/matriz-client/src/matriz_client/ws_client.py:79`, `:117`, `:314`

**Issue:** `_handle_open` binds `_decode.STRICT_DECODE.set(bool(_ws_strict_decode))`.
`_ws_strict_decode` is `None` before the first connect and is reset to `None` by
`ws_disconnect` (`:314`), and `bool(None)` is `False`. A consumer who configured
`strict_decode=True` therefore gets observable mode — silently, with no warning record —
whenever `_handle_open` is reached without a preceding `_bind_decode_mode_for_ws`. The
docstring names this outcome but treats it as benign; for a mode whose entire purpose is
"a divergence must be fatal", a silent downgrade to "a divergence is a log line" is the
failure the mode exists to prevent.

The same globals (`_on_message`, `_on_error`, `_on_close`, `_ws_strict_decode`) are plain
module state mutated from the connecting thread and read from the daemon thread with no
synchronisation; `ws_disconnect` clearing `_ws_strict_decode` while a frame is in flight is
a real interleaving on this code path.

**Fix:** make the unbound case observable rather than silent, and remove the `None`
ambiguity by snapshotting the flag onto the `WebSocketApp` instance (which the daemon
thread already owns) instead of a module global:

```python
def _handle_open(ws: websocket.WebSocketApp) -> None:
    mode = getattr(ws, "_decode_strict", None)
    if mode is None:
        _LOGGER.warning("ws decode mode was not handed over; defaulting to observable")
        mode = False
    _decode.STRICT_DECODE.set(mode)
    _connected.set()
```

with `ws_connect` setting `_ws._decode_strict = default._state.strict_decode` before
starting the thread.

---

### WR-07: The intactness gate proves the copies agree with each other, never that they agree with the reviewed body

**File:** `tools/check_decode_intactness.py:430-465` (Check A), `:219-230` and `:538-562`
(Check C)

**Issue:** Check A hashes five normalized copies and asserts `len(distinct) == 1`. It
pins *mutual* agreement, not agreement with any reviewed body. An edit applied uniformly
to all five copies — which is exactly the shape a `sed`, a formatter rule or a
well-meaning "harmonization" produces — collapses to one hash and passes green. The five
copies are the only artifact the gate protects, and the thing most worth protecting is the
canonical *content*.

Check C's `strict=False` ban is a repo-wide, per-line regex over every `.py` under
`packages/*/src/`. `\bstrict\s*=\s*False\b` matches `zip(a, b, strict=False)`,
`json.loads(..., strict=False)` and any other stdlib call with that keyword — none of
which has anything to do with the decode mode. The neighbouring `_logging.py` already uses
`zip(..., strict=True)`; the `False` variant is one refactor away from a red build with a
misleading message.

**Fix:** add a pinned canonical digest alongside the mutual check, updated deliberately
when the body legitimately changes:

```python
# The reviewed canonical body. Bump ONLY together with a reviewed change to
# `_decode.py`, and state the reason in the commit message.
CANONICAL_DIGEST = "a5889d5778f11dde..."   # full sha256
...
if distinct[0] != CANONICAL_DIGEST:
    raise _fail("the canonical decode body changed; re-review it and bump CANONICAL_DIGEST")
```

and scope Check C to `_decode.py` (or exclude a `# noqa: decode-ban` marker), since a copy
"quietly stopping behaving like a copy" can only happen inside the copied file.

## Info

### IN-01: `open_request_scope()` in the WebSocket open handler is dead

**File:** `packages/matriz-client/src/matriz_client/ws_client.py:118`

**Issue:** `_handle_open` opens a decode scope, but `_handle_message` opens a fresh one for
every frame (`:158`) before any decoding happens, and no other decode runs on the daemon
thread. The `:118` call can never be the scope any record is emitted under.

**Fix:** drop the call from `_handle_open`; keep only the `STRICT_DECODE.set(...)` bind,
which is the one thing that genuinely has to happen once on that thread.

---

### IN-02: `_MAX_SCAN_ENTRIES = 64` is a data-shaped redaction bypass

**File:** `packages/higyrus-client/src/higyrus_client/_logging.py:106`, `:123`, `:130`
(and all five copies)

**Issue:** a `dict` or sequence with more than 64 entries is returned untouched, so a
credential sitting in the 65th entry of some caller's `extra` container is never redacted.
This is signed lock 12 and the latency reasoning is sound, but the bound converts a
security control into one that a payload's own size can switch off, with no trace.

**Fix:** redact the first `_MAX_SCAN_ENTRIES` entries and replace the remainder with a
marker (e.g. `"<scan truncated: 412 more entries>"`) rather than passing the whole
container through. Same worst-case cost, no silent bypass. Requires a lock-12 amendment.

---

### IN-03: matriz's decode suite omits the `_RECORD_KEYS` identity assertion the other four carry

**File:** `packages/matriz-client/tests/test_decode.py:68`, `:679-697`

**Issue:** the four sibling suites assert
`set(_decode._RECORD_KEYS) == set(_CONTRACT_KEYS)`
(`higyrus:354`, `market-data:367`, `iol:442`, `ambito:469`). matriz asserts the *emitted*
key set and the reserved-name disjointness but never ties the module's own `_RECORD_KEYS`
tuple to the contract, so a drifted tuple in the matriz copy would only be caught
indirectly.

**Fix:** add the one-line assertion to `packages/matriz-client/tests/test_decode.py` for
parity with the other four copies.

---

### IN-04: A multi-arm `Union` field passes through unvalidated and unreported

**File:** `packages/higyrus-client/src/higyrus_client/_decode.py:322-328`

**Issue:** the Union branch only recurses when exactly one non-`None` arm remains;
`int | str`, `str | list[X]` and similar fall to a bare `return value` with no type check
and no divergence record. No shipped model declares such a field today, so this is latent
rather than active — but it is a silent hole in a walker whose contract is "every
substituted default is reported", and Phase 30's iol models are the likely first
occurrence.

**Fix:** validate membership against the arms and report a `type` divergence when the
runtime type matches none of them:

```python
if not any(isinstance(value, a) for a in non_none if isinstance(a, type)):
    sink(model, path, _kind_of(value), _name_of(hint), type(value).__name__)
return value
```

---

_Reviewed: 2026-08-19_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
