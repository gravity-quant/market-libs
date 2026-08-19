# Phase 29: Decoder observable - Research

**Researched:** 2026-08-18
**Domain:** Observable per-field decode for six independently-released Python HTTP client wheels — structured divergence emission, strict-mode carrier, verbatim-copy topology
**Confidence:** HIGH (nearly every load-bearing claim below was measured by executing against this repo at `32cc4a3`, not recalled)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Motor del decoder (D-lock a)
- **D-01:** El **walker por-campo stdlib es el motor primario** en cualquier escenario (evolución de `_coerce`, NO reemplazado — corrección del research). La decisión msgspec-dos-motores vs stdlib-only **se resuelve dentro de la fase con un spike de timing descartable** (elección del operator): micro-benchmark walker vs `msgspec.convert()` sobre payloads sintéticos representativos; el D-lock se firma con esos números como evidencia del lado pro-msgspec. Hechos verificados que condicionan el spike: msgspec no puede implementar el modo observable (fail-fast, un error por decode, ignora claves extra, sin field-rename para dataclasses stdlib); msgspec tiene cero presencia en `uv.lock`/`pyproject.toml` hoy; la verificación empírica previa de msgspec (`frozen+slots`) NO cubre la forma real de matriz (18 dataclasses frozen, 0 slots). Si el spike da GO, msgspec sería solo fast-path del modo estricto, los 6 wheels se re-publican en F34 y el README declara la pérdida del closure puro-Python.

#### Topología de copia
- **D-02:** El helper de decode aterriza **verbatim en 5 paquetes, no 6** — `wallets-client` queda con **exención documentada** (no tiene `_logging.py`, `_state.py`/`_ClientState`, `_core.py`, `models.py` ni `tests/test_logging.py`; bootstrapearlo es scope de Phase 31 TYP-03). Los criterios "×6" del roadmap (fix del filter, sentinels caplog, intactness) se leen "×5 + exención wallets documentada". El test de intactness es por hash + ban-list grep (`strict=False`, `msgspec.field()`) sobre las 5 copias.

#### Portador del modo estricto
- **D-03:** Flag `strict_decode` en `_ClientState` (precedente exacto `mutating_allowed`/`expected_host` de market-data `_state.py:100-107`, regla D-14: nunca en `__slots__` de instancia, así los views de `with_options` heredan). El `ContextVar` se bindea con **`.set()` SIN reset** al tope de `_request` — un reset al final de `_request` desbindearía el modo antes de que el decoder lo lea, porque `_request` retorna el `httpx.Response` y el decode ocurre después en el parser. Nunca env var, nunca global de módulo. Debe documentarse el default del modo para `Model.from_api()` invocado directo sin `_request` previo (default: observable).
- **D-04:** El daemon thread de `ws_client` de matriz **no hereda** el ContextVar (thread nuevo = Context vacío; el path de frames nunca pasa por `_request`) → necesita **propagación explícita del modo** como mecanismo propio. El test de concurrencia del criterio 2 prueba dos cosas: no-clobbering entre tareas async interleaved Y propagación explícita (no herencia) hacia el thread.

#### Registro de divergencia + RedactingFilter
- **D-05:** El fix del `RedactingFilter` es **dos-partes**: (a) el scan de extras saltea valores no-str (`isinstance(value, str)`) → los dicts anidados nunca se recorren; (b) los markers de redacción son literales anclados (`"Bearer "`, `"password="`, …) → un credential pelado sin marker sobrevive. **Ningún cambio al filter hace seguro loggear valores del wire** (`_redact` mismo es regex marker-anchored) → la garantía la carga el **contrato del registro: flat, all-str, top-level, type-not-value, jamás el valor del wire**; el fix del filter es defensa en profundidad. Sentinel caplog por paquete (5, precedente SEC-01 `verification/test_logging_no_token_leak.py` — que asserta sobre `getMessage()`, `str(record.args)` y `record.__dict__`).
- **D-06:** El vocabulario del registro de divergencia se deriva de `verification/schema.py::schema_of` (claves + tipos, nunca valores) y la emisión queda compatible con el pipeline `findings.py` existente — no se inventa un formato paralelo (el handler de F33 `verification/divergences.py` debe consumirlo sin traducción, y el piso de sizing debe ser directamente contrastable con el censo vivo de F33). `verification/safemodel_diff.py::diff_safemodel_bidirectional` (duck-typed cross-package) es reusable para el pase de sizing.

#### Reconciliación de semánticas
- **D-07:** La "tabla 3-way" del roadmap es en realidad **6-way sobre implementaciones de `from_api`** (+2 `empty()`): (1) `SafeModel` higyrus y (2) market-data (2107 chars c/u, NO byte-idénticos — difieren en docstring + 1 comentario); (3) `MarketDataSnapshot.from_api(payload, *, received_at=0.0)` firma extendida que bypassea `_coerce`; (4) `Symbol.from_api` pre-procesa `market_id`→`marketId`; (5) `_SafeModel.from_api(data)` de matriz (missing→`None`, sin slots, `empty()`, escalares pass-through, non-dict→`cls.empty()`); (6) `UnknownFrame.from_api` que retiene el payload crudo en `raw`. La tabla se escribe como artefacto **antes de escribir código de decoder**; política parametrizada por paquete, nunca "harmonizada" en silencio. Merge gate: **872 tests** de los 3 paquetes con SafeModel verdes **sin editar un solo test** (DT-05: `from_api(payload)` conserva firma y contrato). Trap conocido: `@dataclass(slots=True)` rebuilds de clase rompen `super()` zero-arg en `from_api` reescritos (warning in-place en market-data `models.py:495-499`).

#### Corrida de sizing
- **D-08:** El corpus del criterio 5 está mal identificado en el roadmap: `verification/snapshots/` son 4 `.txt` de superficie pública **sin payloads**, y `.planning/verification/captures/` está vacío. La corrida se **re-basa en `.planning/verification/schemas/`** (43 JSON type-only: ambito 1 / higyrus 5 / iol 4 / matriz 8 / market-data 25). El piso resultante es de **keyset/tipo** (`≥ N` por paquete, nunca `N`) — honesto como piso, con blind spot documentado: ciego a divergencias de valor (NaN/Infinity, enums out-of-set), que son justo el objeto del D-lock 4b. Freshness conocida: capturas iol de 2026-06-06 (~2.5 meses) — válido como piso igual.

#### D-lock b: Literal en RESPONSE
- **D-09:** Los campos de **RESPONSE nunca se cierran como `Literal`** en este milestone: se decodifican como `str` y el valor fuera de set se reporta como divergencia. Alcanza retroactivamente a los 9 aliases de matriz `types.py` (`Side`/`OrderType`/`TimeInForce`/`MarketId`/`SegmentId`/`CFICode`/`MarketDataEntry`/`OrderStatus`/`Currency`). Es **behaviorally-free** para matriz: hoy `_convert` los pasa sin validar (`return value` final), así que el cambio es solo de reporting, nunca de los valores devueltos. El walker NO debe enforcear membership de `Literal` (evitaría la tormenta de divergencias por crecimiento legítimo de enums del vendor).

### Claude's Discretion
- Forma exacta del helper (`_decode.py` como módulo nuevo vs extensión de `models.py`), naming del ContextVar, y estructura interna del spike de timing — dentro de los locks de arriba.
- El mecanismo concreto de propagación explícita del modo al daemon thread de ws_client (parámetro, snapshot del flag en connect, etc.).

### Deferred Ideas (OUT OF SCOPE)
- Bootstrap de `wallets-client` (`models.py`/`types.py`/`_logging.py`/`_state.py`) — Phase 31 (TYP-03); acá solo exención documentada
- Cierre de `Literal` con censo vivo (input de iol + RESPONSE de matriz según D-09) — Phase 33 (DT-07)
- Handler `verification/divergences.py` que rutea divergencias al pipeline de findings — Phase 33 (acá solo se garantiza compatibilidad de formato, D-06)
- Re-captura live para refrescar schemas (~2.5 meses de staleness en iol) — si hace falta, es trabajo de F33 con creds; el piso de sizing es válido igual
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| **DEC-01** | Todo consumidor de las 6 libs recibe divergencias de forma **observable** (registro estructurado por el logger del paquete) en lugar de sustituciones silenciosas; los drivers `main_*.py` corren en modo estricto (divergencia → finding). Walker por-campo como motor primario (evolución de `_coerce`); emisión flat/all-str/type-not-value compatible con `RedactingFilter` (+ fix del filter); modo estricto por `ContextVar` bindeado desde `_ClientState`; `from_api` preservado (DT-05); copiado verbatim con test de intactness por hash (DT-03); reconciliación explícita de matriz; D-lock msgspec; corrida de sizing. | §"Walker design" gives the exact `_coerce`→walker signature delta and the 3 capabilities today's implementations structurally cannot express. §"Divergence record" gives a reserved-key-safe, flat, all-str schema **verified against `logging.Logger.makeRecord`**. §"ContextVar mechanics" gives measured thread/task semantics and the exact `copy_context()` mechanism for the ws daemon thread. §"6-way semantics matrix" is a pre-filled draft of the mandatory D-07 artifact. §"Sizing run" reports a *working prototype* with per-package raw numbers and the one design constraint (envelope unwrap) that would otherwise make the floor garbage. §"Timing spike" reports measured `msgspec.convert` vs `from_api` vs hints-cached walker and the trap that would produce a false GO. |
</phase_requirements>

---

## Project Constraints (from CLAUDE.md)

The planner MUST verify each plan against these; they carry the same authority as CONTEXT.md locks.

| # | Directive | Consequence for this phase |
|---|-----------|----------------------------|
| C-1 | Python 3.12+, uv, httpx, pytest+pytest-httpx, ruff, mypy **strict**. Every extension/fix must pass existing CI. | The walker must be `mypy --strict` clean. `get_type_hints`-driven code needs `cast`/`Any` discipline — the existing `_coerce` already uses `cast(Any, cls)` for this exact reason. |
| C-2 | **Sin código compartido entre paquetes** (por diseño). Fixes se aplican dentro de cada paquete, sin dependencias cruzadas. | Hard-locks DT-03/D-02: the decode helper is copied, never imported. The intactness test is the only enforcement. |
| C-3 | **Dual sync/async**: todo fix de lógica debe espejarse en `client.py` y `aio.py` del mismo paquete. | The ContextVar bind lands **twice per package** (sync `Client._request` + async `AsyncClient._request`) — 9 sites across 5 packages (matriz `aio.py` has 1 `_request`, market-data has 1 each, the other three have a method + a module shim). |
| C-4 | **Seguridad**: credenciales en `.env` por paquete; **nunca** exponer credenciales en logs, reportes o tests. | This is the load-bearing constraint on the divergence record. It is why the record is type-not-value: the `RedactingFilter` is marker-anchored and structurally cannot make wire values safe (D-05). |
| C-5 | Estado singleton a nivel de módulo. | The strict flag lives on `_ClientState` (shared, inherited by `with_options` views), never on a module global and never in `Client.__slots__`. |
| C-6 | Estilo: `from __future__ import annotations` obligatorio y uniforme; módulos con docstring de módulo; `__all__` explícito; ruff line-length 100, double quotes. | **`from __future__ import annotations` is why `get_type_hints()` is expensive** (see the timing finding) — every annotation is a string re-evaluated per call. |
| C-7 | GSD workflow enforcement — no direct repo edits outside a GSD workflow. | Research is read-only; the sizing prototype lives in scratch, never in the repo. |

---

## Summary

Phase 29 is not "copy a decoder into six packages." It is three structurally independent pieces of work that happen to share a file, plus two signed decisions and two measurement artifacts. The three pieces: **(1)** an evolution of `_coerce`/`_convert` from a *value-returning* recursive function into a *path-carrying, sink-emitting* per-field walker that can additionally see payload keys the model does not declare (today it structurally cannot — both implementations iterate `dataclasses.fields(cls)` and call `data.get(name)`, so the payload key set is never enumerated); **(2)** a divergence record contract that is flat, all-str, top-level and type-not-value, because the `RedactingFilter` in all five copies is provably incapable of protecting anything else; **(3)** a `ContextVar` mode carrier bound at the top of `_request`, which is correct precisely because `_request` returns an `httpx.Response` and the decode happens later in `_core.parse_*` — a `reset()` in a `finally` would unbind the mode before the decoder reads it.

Three measurements taken during this research change the shape of the plan. **First**, `SafeModel.from_api` currently costs **66-70 µs per row** on higyrus' 21/22-field models, and **58.9 µs of that (≈89%) is a single uncached `typing.get_type_hints(cls)` call** re-evaluating stringified annotations on every single decode. An `lru_cache` on the hints lookup drops it to 0.035 µs — a ~10× speedup on the whole decode with zero new dependency, available inside this phase's scope. This directly reframes the msgspec D-lock: benchmarking `msgspec.convert` (measured 0.22 µs/op) against *today's uncached* `from_api` yields a ~300× ratio and a near-automatic GO; benchmarking it against a *hints-cached* walker — the honest comparator, since the walker is the primary engine either way (D-01) — collapses the ratio to roughly 30×, on a low-QPS REST client with no stated throughput requirement. **A spike that omits the hints cache from the baseline will produce a false GO.** **Second**, `logging` raises `KeyError: "Attempt to overwrite 'module' in LogRecord"` for `extra={"module": ...}` and `{"name": ...}` — two of the most natural key names for a divergence record identifying a model's module and field name. A tolerant decoder that raises `KeyError` from inside its own emission path converts observable mode into fatal mode for every caller. This pitfall is absent from the 25 in `.planning/research/`. **Third**, the sizing run over `.planning/verification/schemas/` is mechanically feasible — a working prototype ran during this research — but the schema corpus stores **raw envelope payloads** (`{count, items[], limit, offset, total}` for market-data reads) while the models describe the **unwrapped item**. Walking the raw envelope against the model produces a flood of false MISSING/EXTRA that would inflate market-data's floor by roughly 5×. The sizing run must route through each package's own `_core.parse_*` function (all of them are pure `(httpx.Response) -> models`, so a synthesized `httpx.Response` works), which also makes the number directly comparable with Phase 33's live census as D-06 requires.

The reconciliation table (D-07) was verified precisely: higyrus and market-data `SafeModel`+`_coerce` blocks are both **2107 characters** and differ in exactly two lines (a docstring noun and one comment noun) — near-verbatim but *not* byte-identical, so a naive hash-based intactness test over them fails on day one and needs a normalization rule. matriz's `_SafeModel`/`_convert` is structurally different as documented, and its `Literal`-typed response fields are confirmed pass-through (`_convert` ends in a bare `return value`), making D-09 behaviorally free. Four of the five `RedactingFilter.filter` bodies are byte-identical (763 chars, `sha256:d7bdefcbfc42…`); matriz's is 1219 chars because of the D-22 `auth_basic` block inserted before the generic scan — an existing, sanctioned per-package divergence that the intactness test must model as an allowed variant rather than a failure.

**Primary recommendation:** Build the walker as `_decode.py` (new module, copied ×5) exporting a single `walk_field(value, hint, *, path, policy, sink) -> Any` plus a module-level `lru_cache`d hints accessor, keep `models.py::_coerce` as a thin back-compat shim delegating to it, parameterize the three known semantic axes (`missing_scalar`, `non_dict`, `scalar_passthrough`) as a frozen `DecodePolicy` constant per package, emit divergences as `logger.warning("decode divergence", extra={...})` with a fixed 7-key all-str schema that avoids every `LogRecord` reserved name, and carry strict mode in a module-level `ContextVar("<pkg>_strict_decode", default=False)` set (never reset) at the top of both `_request` implementations, propagated to matriz's ws daemon thread via a `contextvars.copy_context()` snapshot captured in `ws_connect()`.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Per-field type walking + safe-default substitution | Library / decode helper (`_decode.py`) | `models.py` (`from_api` entry) | Pure function of `(value, hint)`; no I/O, no state. Must be importable by tests without an HTTP client. |
| Divergence emission | Library / package logger (`logging.getLogger("<pkg>")`) | — | Established channel: `attach()` already installs `NullHandler` + `RedactingFilter` on exactly this logger in all 5 packages. Consumers opt in via handler. |
| Divergence → finding routing | **Driver / harness** (`verification/divergences.py`, Phase 33) | — | Out of scope here (deferred). Phase 29 only guarantees the record *shape* is consumable without translation (D-06). |
| Strict/observable mode ownership | Config tier (`_ClientState.strict_decode`) | — | Same tier as `mutating_allowed`/`expected_host`; inherited by `with_options` views (D-14). |
| Strict/observable mode *transport* to the decoder | Execution-context tier (`ContextVar`) | Explicit argument (ws daemon thread) | The decoder is called from `_core.parse_*`, which has no reference to the `Client` instance. ContextVar is the only carrier that survives interleaved async tasks (measured). |
| Redaction / credential containment | Library / `_logging.RedactingFilter` (defense in depth) | **Record contract** (primary) | D-05: the filter is marker-anchored and cannot protect wire values; the type-not-value contract is the real control. |
| Verbatim-copy enforcement | CI (`lint` job grep gate) + in-package tests | — | `verification/` never runs in CI (`ci.yml:110-112` passes an explicit path that overrides `testpaths`). The `lint` job already contains a grep-based gate precedent (`lint-logging`, `ci.yml:44-51`). |
| Sizing measurement | Throwaway script + phase artifact | — | Not shipped code; the number is a document, not a test. |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `typing` (stdlib) | 3.12 | `get_type_hints`, `get_origin`, `get_args`, `Literal` introspection | Already the engine of both `_coerce` and `_convert`. `[VERIFIED: repo]` |
| `dataclasses` (stdlib) | 3.12 | `fields()`, `is_dataclass()` | Already used; `fields()` measured at 0.53 µs/call — cheap enough to leave uncached. `[VERIFIED: direct execution]` |
| `functools.lru_cache` (stdlib) | 3.12 | Per-class hints cache | The single highest-leverage change in the phase: 58.9 µs → 0.035 µs per decode. `[VERIFIED: direct execution]` |
| `contextvars` (stdlib) | 3.12 | Strict-mode carrier + `copy_context()` for the ws thread | Zero current usage in the repo (greenfield). Semantics measured, see §ContextVar. `[VERIFIED: direct execution]` |
| `logging` (stdlib) | 3.12 | Divergence emission channel | `attach()` + `RedactingFilter` + `NullHandler` already installed per package. `[VERIFIED: repo]` |

**No new runtime dependency is required for the deliverable.** The stdlib closure is sufficient and is the D-01 primary engine in both branches of the msgspec D-lock.

### Supporting (conditional — only if the D-lock spike returns GO)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `msgspec` | 0.21.1 (latest, published 2026-04-12) | Strict-mode fast-path detector only; never in a public signature (DT-01) | Only if the timing spike shows the hints-cached walker is too slow *against a stated requirement*. No such requirement exists today. `[VERIFIED: direct execution + PyPI]` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| stdlib walker (primary) | `msgspec.convert` as sole engine | **Structurally impossible.** Measured: unknown wire keys are silently accepted with no error and no report; `ValidationError` is one-error-per-decode. Extra-key detection and multi-divergence collection — the two things DEC-01 exists to deliver — are both unavailable. `[VERIFIED: direct execution]` |
| `lru_cache(get_type_hints)` | Precompute hints in `__init_subclass__` | Equivalent perf; `lru_cache` is 1 line and does not touch class construction (which `@dataclass(slots=True)` already rebuilds — see Pitfall 6). |
| `ContextVar` | `threading.local` | Fails on interleaved asyncio tasks sharing one thread — all sibling tasks would see the last writer's value. |
| `ContextVar` | explicit `strict: bool` parameter threaded through every `parse_*` | Would change ~30 pure parser signatures across 5 packages and break the DT-05 `from_api(payload)` contract. Rejected. |
| `logger.warning(extra=…)` | a custom `DecodeReport` return value | Would change `from_api`'s return type → violates DT-05 zero-test-edit merge gate. |

**Installation:** none required for the primary path.

```bash
# Only the throwaway timing spike touches msgspec — ephemeral, never added to any pyproject.toml
# (SPIKE-005/006 precedent: isolated env, no project mutation)
uv run --with msgspec --no-project --python 3.12 python <spike_script>.py
```

**Version verification (executed 2026-08-18):**

```
msgspec 0.21.1   # PyPI latest, published 2026-04-12T21:43:45Z
CPython 3.12.13  # repo .venv, uv run
```

---

## Package Legitimacy Audit

Only one external package is even a candidate, and it is gated behind an in-phase D-lock.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| `msgspec` | PyPI | latest release 2026-04-12; project is multi-year | unknown (PyPI JSON API exposes no download counts) | github.com/jcrist/msgspec | **[SUS]** | **Approved with note** — the sole `SUS` reason is `unknown-downloads`, a PyPI-metadata artifact, not a risk signal. Repo present, not deprecated, no postinstall concept in the wheel, verified by direct import + execution in an ephemeral env. The phase already gates any adoption behind the D-lock spike + operator signature, which is a stronger control than a `checkpoint:human-verify`. |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** `msgspec` — verdict is metadata-driven only. If the D-lock returns GO, the planner should still add an explicit checkpoint before it enters any `pyproject.toml`, because that act converts six pure-Python wheels into wheels with a C extension (a DT-08 changelog obligation, not a security one).

---

## Architecture Patterns

### System Architecture Diagram

```
                   consumer code
                        │
                        │  pkg.get_posicion_valuada(...)
                        ▼
              ┌──────────────────────┐
              │  Client / AsyncClient│   _ClientState.strict_decode  (D-03, D-14)
              │      ._request()     │───────────────┐
              └──────────┬───────────┘               │
                         │                    _STRICT.set(state.strict_decode)
                         │                    ← NO reset (D-03)
                         │  httpx.Response           │
                         ▼                           │
              ┌──────────────────────┐               │
              │  _core.parse_*()     │               │  ContextVar
              │  (pure; unwraps      │               │  (per-package,
              │   envelope → items)  │               │   module-level)
              └──────────┬───────────┘               │
                         │  dict / list[dict]        │
                         ▼                           │
              ┌──────────────────────┐               │
              │ Model.from_api(payl) │  ◄── DT-05: signature unchanged
              └──────────┬───────────┘               │
                         │                           │
                         ▼                           ▼
              ┌───────────────────────────────────────────┐
              │  _decode.walk_field(value, hint,          │
              │        path=…, policy=…, sink=…)          │
              │                                           │
              │   per field:                              │
              │     missing?  ──┐                         │
              │     wrong type?─┼──► divergence           │
              │     extra key? ─┘        │                │
              │     (Literal: NEVER enforced — D-09)      │
              └───────────┬──────────────┼────────────────┘
                          │              │
        observable mode ──┘              └── strict mode
                          │                        │
                          ▼                        ▼
       logging.getLogger("<pkg>")          raise <Pkg>DecodeError(path)
                 │                                 │
        RedactingFilter (defense in depth)         │
                 │                                 ▼
                 ▼                          driver main_*.py
        consumer handler / NullHandler       → finding (Phase 33)


   ── matriz WS side path (D-04) ───────────────────────────────
   ws_connect()  ──► ctx = contextvars.copy_context()   [captures mode]
        │              (daemon thread does NOT inherit — measured)
        ▼
   daemon thread ──► _handle_message ──► ctx.run(_parse_frame, data)
                                              │
                                              ▼
                                   MarketDataFrame/ExecutionReportFrame/
                                   UnknownFrame.from_api  ──► walker
```

### Recommended Project Structure

```
packages/<pkg>/src/<pkg>/
├── _decode.py       # NEW ×5 (verbatim). Walker + DecodePolicy + ContextVar +
│                    #   divergence emitter + lru_cached hints accessor.
│                    #   Only per-package deltas: the module docstring's package
│                    #   name, the logger name, and the POLICY constant value.
├── models.py        # MODIFIED ×3. `_coerce`/`_convert` become thin shims that
│                    #   delegate to _decode.walk_field. from_api signatures
│                    #   UNCHANGED (DT-05).
├── _state.py        # MODIFIED ×5. + strict_decode: bool = False
├── _logging.py      # MODIFIED ×5. RedactingFilter two-part fix (D-05).
├── client.py        # MODIFIED ×5. ContextVar bind at top of Client._request.
├── aio.py           # MODIFIED ×5. Mirrored bind in AsyncClient._request (C-3).
└── ws_client.py     # MODIFIED ×1 (matriz). copy_context() snapshot + ctx.run.

packages/<pkg>/tests/
├── test_decode.py             # NEW ×5. 5 divergence classes × 2 modes.
├── test_decode_intactness.py  # NEW ×1 (or in tools/). Hash + ban-list over 5 copies.
└── test_logging.py            # MODIFIED. caplog sentinel for the decoder path.

.planning/phases/29-decoder-observable/
├── 29-SEMANTICS-MATRIX.md     # ARTIFACT (D-07) — written BEFORE decoder code.
├── 29-DLOCK-MSGSPEC.md        # ARTIFACT (D-lock a) — signed with spike numbers.
├── 29-DLOCK-RESPONSE-LITERAL.md # ARTIFACT (D-lock b / D-09).
├── 29-AGGREGATION-CONTRACT.md # ARTIFACT — anti-log-spam policy.
└── 29-SIZING.md               # ARTIFACT — per-package floor (≥ N).
```

### Pattern 1: Walker as an evolution of `_coerce` — the exact signature delta

**What:** `_coerce(value, hint) -> Any` becomes `walk_field(value, hint, *, path, policy, sink) -> Any`. The return value and the substitution behavior are *unchanged*; the walker additionally **emits** to a sink and **carries a path**.

**Why this is the shape:** three capabilities are structurally absent today, and exactly one of them requires a change to the call *site* rather than the function.

| Capability | Why today's `_coerce`/`_convert` cannot express it |
|---|---|
| Report *which* field diverged | `_coerce(value, hint)` receives no field name and no parent path. Purely additive fix: add `path`. |
| Report a **type mismatch** | Detected but discarded: `return value if isinstance(value, str) else ""` throws the fact away. Purely additive fix: emit before returning the default. |
| Report an **extra wire key** | **Not fixable inside `_coerce`.** Both `SafeModel.from_api` and `_SafeModel.from_api` iterate `dataclasses.fields(cls)` and call `data.get(name)`; the payload's own key set is never enumerated. The fix lives in `from_api` (or a `walk_model` wrapper), not in the per-field function. `[VERIFIED: repo — higyrus models.py:38-45, matriz models.py:106-111]` |

**Example (the delta, not a rewrite):**

```python
# Source: packages/higyrus-client/src/higyrus_client/models.py:48-88 (current)
def _coerce(value: Any, hint: Any) -> Any:
    ...
    if hint is str:
        return value if isinstance(value, str) else ""     # ← fact discarded here

# _decode.py (proposed) — same control flow, + path + sink + policy
def walk_field(value: Any, hint: Any, *, path: str, policy: DecodePolicy,
               sink: Sink) -> Any:
    ...
    if hint is str:
        if isinstance(value, str):
            return value
        sink(path, "type" if value is not None else "missing", "str",
             type(value).__name__)
        return policy.missing_scalar_str          # "" for higyrus/market-data,
                                                  # None for matriz
```

```python
# _decode.py — the model-level wrapper that makes extra-key detection possible.
def walk_model(cls: type, payload: Any, *, path: str, policy: DecodePolicy,
               sink: Sink) -> dict[str, Any]:
    if not isinstance(payload, dict):
        sink(path or "$", "non_dict", "dict", type(payload).__name__)
        data: dict[str, Any] = {}
    else:
        data = payload
    hints = _hints(cls)                    # lru_cached — the 10x win
    names = {f.name for f in fields(cast(Any, cls))}
    # NEW: the payload key set is finally enumerated.
    for key in sorted(set(data) - names):
        sink(f"{path}.{key}", "extra", "-", type(data[key]).__name__)
    return {n: walk_field(data.get(n), hints[n], path=f"{path}.{n}",
                          policy=policy, sink=sink) for n in names}
```

### Pattern 2: Per-package policy parameterization (never "harmonized")

**What:** a frozen module-level constant, one per package, is the *only* line of `_decode.py` allowed to differ between copies besides the docstring package name and the logger name. The intactness test normalizes exactly these lines away.

```python
# _decode.py — identical class in all 5 copies; only the constant differs.
@dataclass(frozen=True, slots=True)
class DecodePolicy:
    missing_str: str | None            # "" (higyrus/market-data) | None (matriz)
    missing_num: float | int | None    # 0/0.0                    | None
    missing_bool: bool | None          # False                    | None
    non_dict_model: str                # "empty_from_api"         | "empty_classmethod"
    scalar_passthrough: bool           # False (coerce scalars)   | True (matriz)
    literal_enforced: bool             # ALWAYS False (D-09)

# higyrus / market-data
POLICY = DecodePolicy("", 0, False, "empty_from_api", False, False)
# matriz
POLICY = DecodePolicy(None, None, None, "empty_classmethod", True, False)
```

**When to use:** every call. There is no unparameterized path — that is what stops a silent harmonization.

### Pattern 3: ContextVar bind at the top of `_request`, no reset

```python
# client.py — top of Client._request, all 5 packages (mirrored in aio.py per C-3)
def _request(self, spec: _core.RequestSpec) -> httpx.Response:
    _decode.STRICT_DECODE.set(self._state.strict_decode)   # NO reset (D-03)
    ...
    return resp        # decode happens AFTER this returns, in _core.parse_*
```

**Why no `try/finally: reset()`:** measured and read off the repo — `_request` returns the `httpx.Response`; `_core.parse_market_data_response(resp)` (and its ~30 siblings) call `Model.from_api` *after* `_request` has already returned. A `reset()` in a `finally` would restore the previous value before the decoder ever reads the var. `[VERIFIED: repo — market-data client.py:449-451 → _core.py:846-876]`

**Why leaking the set is safe:** measured — an `asyncio.gather` child's `.set()` does not propagate to the parent context and does not clobber siblings. The residual value in a *sync* caller's context is simply the last-used client's mode, which is the intended semantic for the module-singleton API.

### Pattern 4: ws daemon-thread propagation via `copy_context()`

```python
# ws_client.py (matriz only) — D-04. The daemon thread does NOT inherit (measured).
def ws_connect(...) -> None:
    ...
    global _ws_ctx
    _rest._get_default()                      # ensures state exists
    _decode.STRICT_DECODE.set(_rest._get_default()._state.strict_decode)
    _ws_ctx = contextvars.copy_context()      # snapshot AT CONNECT TIME
    _ws_thread = threading.Thread(target=_ws.run_forever, daemon=True)

def _handle_message(ws: websocket.WebSocketApp, raw: str) -> None:
    if _on_message is not None:
        data: dict[str, Any] = json.loads(raw)
        # ctx.run re-establishes the captured mode inside the daemon thread.
        _on_message(_ws_ctx.run(_parse_frame, data))
```

Measured semantics backing this (CPython 3.12):

```
plain threading.Thread  -> V.get() == False   (default; NOT inherited)
copy_context()+ctx.run  -> V.get() == True    (propagated)
asyncio.gather(t1=True, t2=False) -> [('t1', True), ('t2', False)]; parent unchanged
```
`[VERIFIED: direct execution]`

**Caveat the planner must handle:** a `Context` can only be entered once at a time — `ctx.run()` raises `RuntimeError: cannot enter context ... already entered` on re-entry. With a single daemon thread serially dispatching frames this is safe, but the test must assert it, and an alternative (re-`set()` the var once inside `_handle_open`, since the daemon thread's context is stable for its lifetime) is simpler and re-entrancy-free. **Recommend the `_handle_open` re-set**; keep `copy_context()` as the documented fallback. `[ASSUMED — re-entrancy behavior not executed this session]`

### Anti-Patterns to Avoid

- **Recording the offending wire value.** Directly violates C-4 and D-05. The `RedactingFilter._redact` is a chain of marker-anchored regexes (`Bearer\s+…`, `("password"\s*:\s*")[^"]+`); a bare token in a `divergence_value` field matches none of them and ships to every downstream handler.
- **Nested `extra={"divergence": {...}}`.** The filter's scan is `if isinstance(value, str)` over `record.__dict__` — a dict value is skipped entirely, so nothing inside is ever redacted. `[VERIFIED: repo — higyrus _logging.py:95-98]`
- **Enforcing `Literal` membership in the walker.** D-09. `matriz._convert` today ends in a bare `return value`, so `MarketId | None` with a wire value of `"XYZ"` is returned untouched. Enforcing it would be a silent behavior break on published surface *and* a divergence storm on legitimate vendor enum growth.
- **`from_api` returning a report object.** Breaks DT-05 and the 872-test zero-edit gate.
- **A hash-based intactness test comparing raw file bytes.** Fails immediately: the two `SafeModel` blocks already differ (2 lines) and matriz's filter body legitimately differs (D-22). Normalize first, then hash.
- **`try/finally: STRICT_DECODE.reset(tok)` around `_request`.** See Pattern 3.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Type-name reduction of a payload for the record | A new `type_of()` helper | `verification/schema.py::schema_of` vocabulary (`"str"`, `"int"`, `"NoneType"`, …) — i.e. `type(v).__name__` | D-06 locks the vocabulary. `schema_of` already produces exactly `type(payload).__name__` for scalars, so the record's type strings are *identical* to what the schema corpus stores → the F33 handler needs zero translation and the sizing floor is directly contrastable. `[VERIFIED: repo — verification/schema.py:40]` |
| Model↔wire keyset diffing for the sizing run | A parallel diff implementation | `verification/safemodel_diff.py::diff_safemodel_bidirectional` | Already duck-typed cross-package via `_is_safemodel_like` (no cross-package import), already handles `Optional` opt-out, `list[Model]` first-element sampling, and the `__dataclass_fields__` ClassVar false positive. `[VERIFIED: repo]` |
| Envelope unwrapping in the sizing run | Re-deriving which key holds the rows | The package's own `_core.parse_*(resp)` with a synthesized `httpx.Response` | All parsers are pure `(httpx.Response) -> models` and already encode the live-verified unwrap (`raw.get("items", [])`). Re-deriving it is how the Phase 25 `get_latest_batch` bug happened. `[VERIFIED: repo — market-data _core.py:846-876]` |
| Divergence → findings routing | A bespoke report writer | `verification/findings.py::append_finding` (Phase 33) | Append-only, idempotent by `fid`, human-status-preserving, `idempotent_by_title` dedupe. `FINDING_CLASSES` already contains `SHAPE` — the right class for a decode divergence. Phase 29 only has to keep the record shape consumable. `[VERIFIED: repo]` |
| Per-class type-hint resolution | Manual annotation string parsing | `functools.lru_cache` over `typing.get_type_hints` | 58.9 µs → 0.035 µs, measured. Hand-parsing stringified annotations is how you reintroduce the `TYPE_CHECKING` NameError class of bug. |
| Cross-package copy enforcement | A bespoke CI runner | The existing `lint` job's grep-gate pattern (`ci.yml:44-51`) + in-package pytest | `verification/` never executes in CI. The `lint-logging` gate is a working, in-CI precedent for exactly a ban-list grep. `[VERIFIED: repo]` |
| Redaction | Extending `_redact` to cover wire values | The type-not-value record contract | D-05 — the operator already locked that no filter change makes wire values safe. |

**Key insight:** this repo has already built, live-verified, and CI-hardened every *auxiliary* mechanism this phase needs (schema vocabulary, bidirectional diff, findings pipeline, redaction filter, grep-gate CI pattern, `_ClientState` flag precedent). The genuinely new code is small: one walker, one policy dataclass, one ContextVar, one record schema. Every line spent reimplementing an auxiliary is a line spent re-litigating a live-verified decision.

---

## Runtime State Inventory

This phase is a cross-package refactor touching 5 verbatim copies. Runtime state was audited explicitly.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| **Stored data** | **None.** No database, no cache file, and no persisted payload stores a decoder-related string. The only on-disk client state is `iol-client`'s `_token_cache.py` (token JSON under `platformdirs`), which contains no model/decoder identifiers. `[VERIFIED: repo grep]` | none |
| **Live service config** | **None.** No external service holds a decoder-side configuration. The five packages are outbound HTTP clients only. | none |
| **OS-registered state** | **None.** No scheduler entries, no daemons, no service registrations. The only OS-level thread is matriz's in-process `ws_client` daemon thread, which is created fresh per `ws_connect()` — **but it is the D-04 propagation target and must be handled in code.** `[VERIFIED: repo — ws_client.py:187-189]` | code change (D-04), not migration |
| **Secrets / env vars** | **No new env var.** D-03 explicitly forbids an env-var carrier. Existing per-package `.env` files are untouched. One adjacent risk: `market-data-client` reads `_env_*` factories at `_ClientState` construction (`_state.py:64-83`); adding `strict_decode: bool = False` as a plain default (no factory) keeps it out of the env surface — that is the correct shape. | none (verify no `_env_strict_decode` factory is added) |
| **Build artifacts / installed packages** | Editable workspace installs via `uv sync --all-packages`. Adding a **new module** (`_decode.py`) inside an existing package needs no reinstall (hatchling packages the whole `src/<pkg>` tree; no explicit module list in any `pyproject.toml`). **If** the msgspec D-lock returns GO, `uv.lock` changes and every CI job's `--frozen` sync would fail until it is refreshed. | none for the stdlib path; `uv lock` + `uv lock --check` if msgspec GO |
| **Test-suite state (in-repo)** | 872 tests across the 3 SafeModel packages, measured green in 64s at `32cc4a3`. This is the zero-edit merge gate baseline. Full workspace CI is 6 packages × py3.12/3.13. | capture the baseline number in the plan; re-run per wave |

**Canonical question — after every file in the repo is updated, what runtime systems still hold the old behavior?** Only one: matriz's `ws_client` daemon thread, whose *execution context* does not inherit the new ContextVar. That is exactly D-04 and it is a code change, not a data migration.

---

## Common Pitfalls

### Pitfall 1: `extra=` keys that collide with `LogRecord` attributes raise `KeyError`

**What goes wrong:** the divergence emitter raises `KeyError` from inside the tolerant decode path, converting observable mode into fatal mode for every caller — the exact inversion of DT-02.

**Why it happens:** `Logger.makeRecord` refuses to overwrite existing `LogRecord` attributes. Measured on CPython 3.12:

```
extra key 'message'    RAISES KeyError: "Attempt to overwrite 'message' in LogRecord"
extra key 'module'     RAISES KeyError: "Attempt to overwrite 'module' in LogRecord"
extra key 'name'       RAISES KeyError: "Attempt to overwrite 'name' in LogRecord"
extra key 'msg'        RAISES KeyError   extra key 'args'      RAISES KeyError
extra key 'asctime'    RAISES KeyError   extra key 'levelname' RAISES KeyError
extra key 'exc_info'   RAISES KeyError
extra key 'field'      OK   extra key 'path' OK   extra key 'model' OK
```
`[VERIFIED: direct execution]`

`module` and `name` are the two most natural names for "which module/model diverged" — this is a live trap, not a theoretical one. It is **absent from all 25 pitfalls** in `.planning/research/`.

**How to avoid:** fix the record schema to a reviewed 7-key set that avoids every reserved name (see §Divergence record below), and add a test that constructs a real `LogRecord` with the schema. The existing transport `extra` dicts already dodge this by accident (`package`, `method`, `url`, `status_code`, `attempt`, `request_id`, `endpoint_name`, `retry_reason`) — reuse that naming discipline.

**Warning signs:** any proposed key named `module`, `name`, `msg`, `message`, `args`, `levelname`, `pathname`, `filename`, `lineno`, `funcName`, `created`, `process`, `thread`, `exc_info`, `stack_info`, `asctime`, `taskName`.

### Pitfall 2: benchmarking msgspec against the *uncached* walker produces a false GO

**What goes wrong:** the D-lock spike measures `msgspec.convert` (0.22 µs) against today's `from_api` (66-70 µs), reports ~300×, and the operator signs a GO that adds a C extension to six pure-Python wheels for a speedup that a 1-line `lru_cache` mostly delivers for free.

**Why it happens:** `from __future__ import annotations` (mandatory per C-6) stringifies every annotation, so `typing.get_type_hints(cls)` re-evaluates them on **every** `from_api` call. Measured decomposition on `higyrus.PosicionValuada` (21 fields):

| Operation | µs/op |
|---|---|
| `PosicionValuada.from_api(payload)` (today) | **65.98** |
| `Movimiento.from_api(payload)` (22 fields, today) | 70.21 |
| `market_data.Symbol.from_api(payload)` (8 fields, today) | 28.61 |
| `typing.get_type_hints(cls)` alone | **58.93** ( ≈89% of the total ) |
| `lru_cache`d `get_type_hints(cls)` | **0.035** |
| `dataclasses.fields(cls)` | 0.53 |
| `msgspec.convert(dict, type=Q)` (3-field dataclass) | 0.22 |

`[VERIFIED: direct execution — CPython 3.12.13 repo venv; msgspec run in ephemeral env]`

**How to avoid:** the spike's baseline **must** be the hints-cached walker, not `from_api` as it exists today. Land the `lru_cache` first (it is in-scope as "evolution of `_coerce`"), then benchmark. State this as an explicit precondition in the spike task.

**Warning signs:** a spike script that imports `higyrus_client.models` and times `from_api` directly.

### Pitfall 3: the sizing run walks raw envelopes and inflates the floor

**What goes wrong:** market-data's floor is reported ~5× too high, Phase 33's budget is set against a fictional number, and the "floor, never an estimate" discipline is defeated by a measurement artifact.

**Why it happens:** `.planning/verification/schemas/` stores the **raw wire payload's** schema; the models describe the **unwrapped item**. Observed in the prototype run:

```
market-data-client/get-market-data.json -> MarketDataSnapshot: 12 "divergences"
    MISSING .symbol .market_id .active .entries .market_data .received_at .staleness_seconds
    EXTRA   .count .items .limit .offset .total
```

Every one of those 12 is an artifact: the real payload is `{count, items:[…], limit, offset, total}` and `parse_market_data_response` unwraps `items`. Same artifact on `get-instruments.json`, `get-segments.json`, `get-calendar*.json` (×3), `create-symbols-batch-*.json` (×2), `preview-calendar-config-*.json` (×2).

**How to avoid:** synthesize a witness payload from the type-only schema (`"str"`→`""`, `"float"`→`0.0`, `"NoneType"`→`None`, `[…]`→one synthesized element), wrap it in `httpx.Response(200, json=witness)`, and call the package's **real** `_core.parse_*` with the walker in observable mode + a counting handler. This unwraps correctly by construction and makes the number directly comparable to F33's live census (D-06).

**Warning signs:** a sizing script that maps a schema file straight to a model class without going through a parser.

### Pitfall 4: `client_function` in the schema corpus is not always a real function name

**What goes wrong:** automatic schema→model mapping silently skips half the corpus and the floor undercounts.

**Why it happens:** the drivers wrote probe names, not API names. Measured across all 43 files — auto-mapping via `get_type_hints(getattr(pkg, fn))["return"]` resolves a model class for only **19 of 43**:

| Package | Files | Auto-maps to a model | Notes |
|---|---|---|---|
| higyrus | 5 | 4 | `get_health` → `dict[str, Any]` (no model until TYP-02) |
| matriz | 8 | 7 | `get_instruments_by_cfi_ESXXXX` is a probe name; real fn is `get_instruments_by_cfi` |
| market-data | 25 | 8 | 14 probe/mutation-response names (`create_symbol_sync_response`, `get_symbols_probe_prefix_async`, `add_holidays_*_response`, …); 3 → `dict[str, Any]` |
| iol | 4 | **0** | no `models.py` until Phase 30 |
| ambito | 1 | 0 | `get_dollar_banco_nacion -> float` |

`[VERIFIED: direct execution]`

**How to avoid:** ship an explicit `schema_file → (parser, model)` mapping table as part of the sizing artifact and assert it covers every file or explicitly marks it `N/A` with a reason. Notable real mappings recovered during research: `create_symbol_*_response`/`update_symbol_*_response` → `create_symbol`/`update_symbol` return `list[Symbol]`; `add_holidays`/`delete_holiday` → `dict[str, Any]` (genuinely unmodelled, that is TYP-02's job); `preview_calendar_config` → `CalendarConfig`.

**Warning signs:** a sizing report whose per-file count is silently absent for a file.

### Pitfall 5: hash-based intactness fails on day one

**What goes wrong:** the intactness test is written, goes red immediately against pre-existing sanctioned divergences, and gets weakened into vacuity.

**Why it happens:** measured today —

| Artifact | Copies | Status |
|---|---|---|
| `RedactingFilter.filter` body | higyrus / ambito / iol / market-data | **byte-identical**, 763 chars, `sha256:d7bdefcbfc42…` |
| `RedactingFilter.filter` body | matriz | 1219 chars, `sha256:156a6ac52458…` — D-22 `auth_basic` block inserted **before** the generic scan |
| `SafeModel` + `_coerce` block | higyrus | 2107 chars, `sha256:bf5cc1576de4…` |
| `SafeModel` + `_coerce` block | market-data | 2107 chars, `sha256:5c06a662318c…` — differs in **2 lines**: docstring `"Higyrus"`→`"market-data"`, comment `"cantidad=True"`→`"size=True"` |

`[VERIFIED: direct execution]`

**How to avoid:** define the intactness contract as *normalize-then-hash*, with the normalization rules written down as part of the test docstring: (a) strip the module docstring; (b) replace the package name token and logger-name literal; (c) declare matriz's D-22 block an **allowed named variant** with its own expected hash, not a failure. Then the test asserts "5 copies reduce to exactly 1 canonical hash + 1 declared variant." Pair it with the ban-list grep (`strict=False`, `msgspec.field(`) which is exact-match and needs no normalization.

**Warning signs:** a test that reads two files and asserts `a == b`.

### Pitfall 6: `@dataclass(slots=True)` breaks zero-arg `super()` in a rewritten `from_api`

**What goes wrong:** rewriting `Symbol.from_api` (or any override) with an idiomatic `super().from_api(payload)` raises `TypeError: obj must be an instance or subtype of type` at runtime — only for the slots-decorated classes, only when the override is exercised.

**Why it happens:** `@dataclass(slots=True)` **rebuilds** the class object; the implicit `__class__` cell captured by zero-arg `super()` still points at the pre-slots class. The repo already hit this and documented it in place:

```python
# packages/market-data-client/src/market_data_client/models.py:497-502
# Explicit two-arg ``super()``: ``@dataclass(slots=True)`` REBUILDS the
# class, so the implicit ``__class__`` cell captured by a zero-arg
# ``super()`` still points at the pre-slots class and raises
# ``TypeError: obj must be an instance or subtype of type``.
return super(Symbol, cls).from_api(payload)
```
`[VERIFIED: repo]`

**How to avoid:** any `from_api` override touched by this phase keeps the explicit two-arg `super(Cls, cls)` form. Note this affects **market-data and higyrus only** — matriz's models are `@dataclass(frozen=True)` with **no** `slots`, so they are immune (and that asymmetry is itself a row in the D-07 matrix).

**Warning signs:** a diff that changes `super(Symbol, cls)` to `super()`.

### Pitfall 7: log spam from `list[Model]` responses

**What goes wrong:** one `get_instruments()` returning 5,000 rows, each missing the same field, emits 5,000 identical records. The mandatory aggregation contract (D-05 / STATE.md) exists for this.

**Why it happens:** the walker is per-field per-instance; nothing dedupes across list elements. Real magnitudes from the corpus: `matriz.get_all_instruments` and `market_data.get_instruments` are unbounded catalogue reads.

**How to avoid:** the aggregation contract is a **phase artifact** and must specify at minimum: (a) the dedupe key — recommend `(model_fqn, field_path, kind)`, which is stable across list index and therefore collapses N rows to 1; (b) the scope — recommend *per decode call* (i.e. per `parse_*` invocation), which requires a collector object created in `walk_model`'s top-level entry, not a module global; (c) a `count` field on the record carrying the multiplicity so information is aggregated, not discarded; (d) the strict-mode counterpart — strict raises on the **first** divergence with its exact path, so aggregation is observable-mode-only. Explicitly reject a process-lifetime dedupe: it would make the second identical response silently clean.

**Warning signs:** an aggregation design keyed on the list index, or a module-level `seen` set.

### Pitfall 8: `parse_*` may run twice for the same request (re-auth carve-out)

**What goes wrong:** a 401-triggered re-auth sends the same request twice; if the divergence collector's scope is wrong, divergences double-count or leak across attempts.

**Why it happens:** `Client._request` retries the SAME request once after a 401 (`market-data client.py:392-402`). Only the final response reaches `parse_*`, so decode itself runs once — **but** a collector scoped to `_request` rather than to the decode call would span both attempts. `[VERIFIED: repo]`

**How to avoid:** scope the collector to the decode entry (`from_api`/`walk_model` top call), never to `_request`. This is also why the ContextVar carries only the **mode** (a bool), not the collector.

### Pitfall 9: `MarketDataSnapshot.from_api(payload, *, received_at=0.0)` is not the base signature

**What goes wrong:** a mechanical rewrite of all `from_api` bodies drops the keyword or routes `received_at` through the walker, collapsing the client stamp to `0.0` and breaking the D-01 fidelity contract (a wire/decoy `received_at` would then win).

**Why it happens:** it is the one model whose `from_api` extends the signature, and it deliberately **bypasses** `_coerce` for exactly one field. `[VERIFIED: repo — market-data models.py:151-168]`

**How to avoid:** treat it as row 3 of the D-07 matrix with an explicit "field-level bypass list" in the policy, and keep the `if field.name == "received_at": kwargs[...] = received_at` branch verbatim. Note the near-miss: `Symbol` **also** declares `received_at`, but there it is a plain wire field (server ingest timestamp) read through the walker — same name, opposite provenance, documented in the models docstring.

### Pitfall 10: `verification/` never runs in CI

**What goes wrong:** the intactness test and the caplog sentinels are written into `verification/`, go green locally, and are inert in CI forever.

**Why it happens:** `ci.yml` passes an explicit path that overrides `testpaths`:

```yaml
# .github/workflows/ci.yml:108-112
run: |
  uv run --python ${{ matrix.python-version }} pytest \
    packages/${{ matrix.package }} \
    --cov=packages/${{ matrix.package }}/src
```
while `pyproject.toml:101` declares `testpaths = ["packages", "tests", "verification"]`. `[VERIFIED: repo]`

**How to avoid:** any Phase 29 test that must gate travels **in-package** (`packages/<pkg>/tests/`), riding the existing 6×2 matrix. The cross-package intactness check has no natural package home — put it in the **`lint` job** as a script, following the existing `lint-logging` grep-gate precedent (`ci.yml:44-51`), which is already an in-CI, cross-package, source-scanning gate.

### Pitfall 11: extra-key detection turns every forward-compatible API into a divergence source

**What goes wrong:** enabling `extra` divergences produces a large, mostly-benign baseline that drowns the real signal — the prototype found 7 `EXTRA` keys on matriz `InstrumentDetail` alone, and `wire-only` is classified "info only" by the existing `safemodel_diff` docstring.

**Why it happens:** `wire-only` keys are the *normal* result of vendor API growth. `diff_safemodel_bidirectional` already draws this distinction: `model-only` is a FALSE PASS risk, `wire-only` is informational.

**How to avoid:** give the record a `kind` field with distinct values (`missing` / `type` / `extra` / `non_dict`), emit `extra` at a **lower level** (`INFO`) than `missing`/`type` (`WARNING`), and — critically — make **strict mode raise only on `missing`/`type`/`non_dict`, never on `extra`**. Otherwise Phase 33's strict driver run fails on every legitimate new vendor field. This is a decision the planner must surface, not assume.

### Pitfall 12: matriz's `Literal` fields are the walker's silent trap

**What goes wrong:** the walker's generic scalar branch is reached with `hint = Literal["ROFX"]`; a naive `hint is str` check fails, falls through to a default `return value` — fine — but a naive "unknown hint → divergence" policy would emit a divergence for **every** Literal-typed field on **every** row.

**Why it happens:** matriz has 9 `Literal` aliases used across `InstrumentId.marketId`, `Instrument`, `Order`, `Trade`, etc. Today `_convert` falls to `return value` and passes them through unvalidated. `[VERIFIED: repo — matriz models.py:76-93, types.py]`

**How to avoid:** the walker must have an explicit `get_origin(hint) is Literal` branch that (a) never enforces membership (D-09), and (b) validates against the *underlying* runtime type of the Literal's values (all 9 aliases are str-valued) so a wire `int` where a `Literal[str]` is declared still reports a `type` divergence. Silence on out-of-set values, loudness on wrong runtime type.

### Pitfall 13: `UnknownFrame` is not a `_SafeModel`

**What goes wrong:** a walker rewrite applied uniformly across matriz's models breaks the WS catch-all, which deliberately retains the entire raw payload.

**Why it happens:** `UnknownFrame` is a plain `@dataclass(frozen=True)` that does **not** inherit `_SafeModel`; it implements the `from_api`/`empty` duck-typed contract by hand and stores `raw: dict[str, Any] = dict(data)`. Under a naive extra-key rule, *every* key of an unknown frame is "extra." `[VERIFIED: repo — matriz models.py:370-391]`

**How to avoid:** row 6 of the D-07 matrix; exempt it explicitly (`raw` is a deliberate catch-all, not a modelling gap) and keep its `from_api` untouched.

---

## Code Examples

### Divergence record — the reserved-key-safe schema

```python
# _decode.py — flat, all-str, top-level, type-not-value (D-05/D-06).
# Every key verified NON-reserved against logging.Logger.makeRecord.
_LOGGER = logging.getLogger("higyrus_client")   # ← the only per-package delta

def _emit(path: str, kind: str, declared: str, observed: str,
          model: str, count: int) -> None:
    _LOGGER.warning(
        "decode divergence",
        extra={
            "package":       "higyrus_client",   # mirrors _transport.py convention
            "divergence":    kind,               # "missing"|"type"|"extra"|"non_dict"
            "field_path":    path,               # ".parking[0].diasParking"
            "declared_type": declared,           # "float"          — NEVER a value
            "observed_type": observed,           # "NoneType"       — NEVER a value
            "model":         model,              # "PosicionValuada" (bare name, not FQN)
            "occurrences":   str(count),         # str per the all-str contract
        },
    )
```

Reserved-name check (all 7 keys plus `package` are safe; the near-misses that are **not**):

```
'module' RAISES   'name' RAISES   'message' RAISES   'msg' RAISES
'args' RAISES     'asctime' RAISES  'levelname' RAISES  'exc_info' RAISES
'field' OK        'path' OK         'model' OK
```
`[VERIFIED: direct execution]`

Note `model` carries the **bare class name**, not the FQN — an FQN would tempt a `module` key. Note also that `RedactingFilter` will scan every one of these values because they are top-level `str`s in `record.__dict__` — which is precisely the defense-in-depth D-05 asks for, and is impossible for a nested dict.

### RedactingFilter — the two-part fix (D-05)

```python
# _logging.py, current body — the two gaps, in place.
# Source: packages/higyrus-client/src/higyrus_client/_logging.py:95-99
for key, value in list(record.__dict__.items()):
    if isinstance(value, str) and any(m in value for m in _REDACTION_MARKERS):
    #  ^^^ (a) non-str values are skipped entirely → nested dicts never traversed
    #                        ^^^ (b) marker-anchored → a bare credential survives
        record.__dict__[key] = _redact(value)
```

Fix shape: (a) recurse into `dict`/`list`/`tuple` values, rebuilding them with redacted string leaves (bounded depth, to avoid a pathological payload becoming a CPU sink); (b) leave the marker anchoring **as-is** and document that it is deliberately not a value-scanner — D-05 already locks that the record contract, not the filter, is the guarantee. Ship the fix to 4 copies verbatim and to matriz's copy *after* the D-22 `auth_basic` block, preserving the existing ordering invariant (the tuple must be split before the generic scan or the password leaks as a non-string field).

### `_ClientState` flag — the exact precedent to mirror

```python
# Source: packages/market-data-client/src/market_data_client/_state.py:100-107
    # Gate de mutaciones (D-13/D-01/D-02). Viven SÓLO en el ``_ClientState``
    # compartido — nunca en un ``__slots__`` de instancia — así un view de
    # ``with_options`` hereda el estado del gate del parent (D-14).
    mutating_allowed: bool = False
    expected_host: str | None = _DEFAULT_EXPECTED_HOST
```

`strict_decode: bool = False` goes in this exact block, as a plain default (no `field(default_factory=_env_…)` — D-03 forbids an env-var carrier).

### Sizing run — the working shape

```python
# Throwaway. schema JSON (type-only) → witness payload → REAL parser → count.
_SYNTH = {"str": "", "int": 0, "float": 0.0, "bool": False, "NoneType": None}

def witness(schema):                       # inverse of verification.schema.schema_of
    if isinstance(schema, dict):  return {k: witness(v) for k, v in schema.items()}
    if isinstance(schema, list):  return [witness(schema[0])] if schema else []
    return _SYNTH.get(schema)

def size_one(schema_file, parser):         # parser is the package's own _core.parse_*
    raw = json.loads(Path(schema_file).read_text())["schema"]
    resp = httpx.Response(200, json=witness(raw),
                          request=httpx.Request("GET", "https://x/"))
    with collecting_divergences() as sink: # observable mode, counting handler
        parser(resp)                       # ← envelope unwrap comes free
    return len(sink)
```

Prototype results from this research (**raw, envelope-unwrap NOT yet applied** — market-data is therefore inflated and higyrus/matriz are already envelope-free and closer to real):

| Package | Schemas | Auto-mapped | Raw divergence count | Confidence in the number |
|---|---|---|---|---|
| higyrus | 5 | 4 | **≥ 22** (across 3 files; 1 empty-list, 1 unmodelled `get_health`) | Reasonable — no envelopes in higyrus payloads |
| matriz | 8 | 7 (+1 manual) | **≥ 25** (across 6 files; 2 empty-list) | Reasonable — no envelopes |
| market-data | 25 | 8 (+11 manual) | 128 raw → **materially lower after unwrap** | Low — 9 of 19 mapped files are envelopes |
| iol | 4 | 0 | **N/A** — no `models.py` until Phase 30 | — |
| ambito | 1 | 0 | **N/A** — `get_dollar_banco_nacion -> float` | — |

`[VERIFIED: direct execution — prototype, 2026-08-18]`

The dominant *real* divergence class in higyrus is `TYPE declared=str wire='NoneType'` (11 fields on `PosicionValuada`, 9 on `Movimiento`) — i.e. the live API sends `null` where the model declares a non-Optional scalar, and today `_coerce` silently substitutes `""`/`0.0`. **That is exactly the class of silent substitution DEC-01 exists to surface**, and it is already ≥20 occurrences in a 5-file corpus. Two structural findings worth surfacing early: `higyrus.Posicion.disponibleAjustado` is `MISSING` on the live wire, and matriz `Instrument.instrumentId` is `MISSING` while `marketId`/`symbol` arrive flattened at top level — a real model/wire shape mismatch, not a decoder artifact.

**Planner note:** report iol and ambito as **N/A with a written reason**, not as `≥ 0`. A `0` reads as "clean" and is exactly the false-pass the milestone exists to eliminate.

### Timing spike — the shape that cannot produce a false GO

```bash
# Ephemeral, never mutates any pyproject.toml (SPIKE-005/006 precedent).
# NOTE the explicit --python 3.12: without it the ephemeral env may resolve a
# newer CPython than the repo's, invalidating the comparison.
uv run --with msgspec --no-project --python 3.12 python spike_timing.py
```

Mandatory comparator set (three arms, not two):

| Arm | Why it must be in the spike |
|---|---|
| A. `from_api` as it exists today (uncached hints) | The status-quo reference — *not* the comparator |
| **B. hints-cached stdlib walker** | **The honest comparator.** Omitting this arm is how the spike produces a false GO (Pitfall 2). |
| C. `msgspec.convert` | The pro-msgspec evidence |

Payload shapes must include matriz's actual form (`@dataclass(frozen=True)`, **no** `slots`) — the prior msgspec verification only covered `frozen=True, slots=True`, so a GO signed on slots-only evidence would not cover 18 of matriz's dataclasses. A GO/NO-GO threshold framed as a ratio is not decidable in the absence of a throughput requirement; recommend framing it as an **absolute budget** instead: "decode of the largest live catalogue response (`get_all_instruments`, `get_instruments`) must complete in under X ms," measured against arm B, with GO only if arm B misses it.

---

## The 6-way `from_api` semantics matrix (draft of the mandatory D-07 artifact)

Written here so the planner can task "review and sign" rather than "discover." Every cell was read off the source.

| # | Implementation | Location | missing scalar | missing `list[X]` | missing nested model | non-dict payload | `Optional[T]` | scalars | slots? | `empty()`? |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `SafeModel.from_api` | higyrus `models.py:37-45` + `_coerce:48-88` | `""`/`0`/`0.0`/`False` | `[]` | `X.from_api(None)` | `{}` (then all defaults) | `None` | coerced by type, `bool`≠`int` guard | **yes** | no |
| 2 | `SafeModel.from_api` | market-data `models.py:66-125` | identical to #1 | identical | identical | identical | identical | identical | **yes** | no |
| 3 | `MarketDataSnapshot.from_api(payload, *, received_at=0.0)` | market-data `models.py:151-168` | as #2 | as #2 | as #2 | as #2 | as #2 | as #2, **except `received_at` bypasses `_coerce` entirely** (D-01) | yes | no |
| 4 | `Symbol.from_api(payload)` | market-data `models.py:486-502` | as #2 | as #2 | as #2 | as #2 | as #2 | as #2, **after** mirroring wire `market_id` → `marketId` when absent; explicit two-arg `super(Symbol, cls)` | yes | no |
| 5 | `_SafeModel.from_api(data)` | matriz `models.py:106-116` + `_convert:76-93` | **`None`** | `[]` | `X.empty()` | **`cls.empty()`** (early return) | unwrapped via `_strip_optional` | **pass-through, unvalidated** (bare `return value`) | **no** | **yes** |
| 6 | `UnknownFrame.from_api(data)` | matriz `models.py:383-391` | n/a — 2 fields | n/a | n/a | `cls()` | n/a | `raw = dict(data)` — **entire payload retained** | no | **yes** (hand-written) |

Byte-level status of #1 vs #2: both blocks are **2107 chars**; they differ in exactly two lines (docstring noun, one comment noun). `sha256` `bf5cc1576de4…` vs `5c06a662318c…`. `[VERIFIED: direct execution]`

Derived policy axes (feeds Pattern 2): `missing_scalar` ∈ {typed-zero, None}; `non_dict_model` ∈ {`from_api(None)`, `empty()`}; `scalar_passthrough` ∈ {False, True}; plus two per-model exemption lists (`received_at` bypass; `UnknownFrame` catch-all) and one pre-processing hook (`Symbol` key mirror).

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Tolerant **and silent** field substitution (`_coerce` returns a typed zero, discards the fact) | Tolerant **and observable** — same return value, plus a structured record | this phase (DT-02) | The return contract is untouched → the 872-test gate holds. |
| Decode policy implicit in the code path | Explicit, per-package `DecodePolicy` constant | this phase (D-07) | Divergence between packages becomes declared, not accidental. |
| `Literal` on response fields as decoration | Decoded as `str`, out-of-set reported as divergence, never enforced | this phase (D-09) | Behaviorally free for matriz (verified: `_convert` passes them through). |
| `get_type_hints` called per decode | `lru_cache`d per class | this phase (recommended) | ~10× decode speedup, zero dependency; also the precondition for an honest msgspec comparison. |
| `verification/` as the home for cross-cutting gates | in-package tests + `lint`-job scripts | Phase 32, pulled partially forward | `verification/` gates have been inert since they were written (`ci.yml` path override). |

**Deprecated/outdated in the upstream planning docs — the planner should not act on these:**
- `tipado_homogeneo.md:89` "`_coerce` **reemplazado**" → **superseded** by D-01: `_coerce` is *evolved*, and it is the primary engine in both D-lock branches.
- `tipado_homogeneo.md:100` "`msgspec` a runtime deps de los 6 paquetes" → **superseded** by D-01: conditional on the in-phase spike.
- ROADMAP criterion 5 "`verification/snapshots/`" → **superseded** by D-08: that directory holds 4 public-surface `.txt` files with no payloads; the corpus is `.planning/verification/schemas/`.
- ROADMAP "×6 / tabla 3-way" → **superseded** by D-02 (×5 + wallets exemption) and D-07 (6-way over `from_api` implementations).
- `.planning/codebase/CONCERNS.md` is dated **2026-05-27** (pre-v1.1) and describes module-global state, missing retries, and missing `close()` — **all since fixed**. Do not plan against it. `[VERIFIED: repo]`

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `contextvars.Context.run()` raises on re-entry, making a single stored `copy_context()` fragile if the ws daemon thread ever dispatches frames concurrently | Pattern 4 | If wrong, `copy_context()` is simply fine and the recommended `_handle_open` re-set is a harmless simplification. If right and ignored, matriz's WS path raises `RuntimeError` under load. **Not executed this session — verify in the plan's first WS task.** |
| A2 | Strict mode should raise on `missing`/`type`/`non_dict` but **not** on `extra` | Pitfall 11 | If `extra` raises, Phase 33's strict driver run fails on every legitimate new vendor field — a divergence storm by construction. This is a **policy decision the operator has not made**; surface it, do not assume it. |
| A3 | The aggregation dedupe key is `(model_fqn, field_path, kind)` scoped per decode call | Pitfall 7 | A different key (e.g. including list index) defeats the anti-spam purpose; a wider scope (process lifetime) makes repeat responses silently clean. The contract is a mandatory artifact — this is a **proposal**, not a finding. |
| A4 | `market-data`'s real (envelope-unwrapped) floor is materially below the raw 128 | Sizing | If the unwrapped number is still large, Phase 33's budget is larger than the milestone assumed — which is exactly the risk the sizing run exists to surface. Must be measured, not estimated. |
| A5 | The manual `schema_file → model` mappings used in the prototype for market-data's 14 probe-named files are correct | Pitfall 4 | Wrong mappings inflate or deflate the floor. The real mapping must be derived from the driver source (`main_market_data.py`), not guessed. |
| A6 | Adding `_decode.py` needs no reinstall because hatchling packages the whole `src/<pkg>` tree | Runtime State Inventory | If a `pyproject.toml` pins an explicit module list, the new module is silently absent from the wheel. **Verify per package before the first task.** |
| A7 | An absolute-budget GO/NO-GO framing is preferable to a ratio for the msgspec spike | Timing spike | Operator's call; a ratio threshold is defensible if a target is stated. Either way the three-arm comparator (Pitfall 2) is non-negotiable. |

---

## Open Questions

1. **Does strict mode raise on `extra` keys?** (= A2)
   - *What we know:* D-09 forbids `Literal` enforcement precisely to avoid a storm from vendor enum growth; `safemodel_diff` already classifies `wire-only` as "info only."
   - *What's unclear:* nothing in CONTEXT.md or the roadmap decides this for strict mode. Criterion 1 lists "campo extra" among the payloads that must decode without raising **in observable mode**; criterion 2 says "la misma divergencia levanta" in strict mode — read literally, extra keys would raise.
   - *Recommendation:* surface as an explicit decision in the plan (a one-line D-lock in the aggregation-contract artifact). Recommend `extra` → observable-only, WARNING→INFO level, never raises. If the operator wants criterion 2 read literally, the Phase 33 budget must absorb every vendor field addition.

2. **Which `_request` is the bind site in packages with both a method and a module shim?**
   - *What we know:* higyrus/ambito/iol/matriz have `Client._request` (method) **and** a module-level `_request` shim; market-data has only the method. The shims delegate to the default client.
   - *What's unclear:* whether binding on the method alone covers every path.
   - *Recommendation:* bind on the **method** only (the shims route through it), and add a test that calls the module-level shim and asserts the mode is bound — cheap, and proves the delegation assumption.

3. **Where does the intactness test live so that it actually gates?**
   - *What we know:* `verification/` is inert in CI; the `lint` job has a working cross-package grep-gate precedent.
   - *What's unclear:* whether the operator wants a new `tools/` directory (research SUMMARY proposes `tools/check_surface_types.py` for Phase 32) or a script inline in `ci.yml`.
   - *Recommendation:* create `tools/check_decode_intactness.py` now and wire it into the existing `lint` job — this also lays the ground for Phase 32's surface gate in the same directory.

4. **Does the `RedactingFilter` recursion need a depth/size bound?**
   - *What we know:* the fix makes the filter traverse nested containers; the divergence record itself is flat, so the recursion only matters for *other* callers' `extra=` dicts.
   - *Recommendation:* bound it (depth ≤ 4, and skip containers over N entries) and document why; an unbounded traversal in a log filter is a latency amplifier on a hot path.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `uv` | all workspace ops | ✓ | (repo-managed; `uv run` works) | — |
| CPython 3.12 | runtime + CI matrix | ✓ | 3.12.13 (repo `.venv`) | — |
| CPython 3.13 | CI matrix | ✓ (CI) | — | — |
| `pytest` + `pytest-httpx` + `pytest-asyncio` | all new tests | ✓ | per `uv.lock` | — |
| `msgspec` | timing spike **only** | ✓ via ephemeral env | 0.21.1 | spike is optional; NO-GO is a valid signed outcome |
| `.planning/verification/schemas/` corpus | sizing run | ✓ | 43 JSON files (ambito 1 / higyrus 5 / iol 4 / matriz 8 / market-data 25) | — |
| Live API credentials | **not needed** in this phase | n/a | — | sizing uses the committed schema corpus (D-08) |

**Blocker status:** the `.venv/` blocker recorded in STATE.md is **resolved** — `uv run pytest` executed the full 872-test 3-package suite in 64s during this research. `[VERIFIED: direct execution]`

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.3+ with pytest-asyncio (`asyncio_mode = "auto"`), pytest-httpx, pytest-cov |
| Config file | root `pyproject.toml` `[tool.pytest.ini_options]` (`testpaths = ["packages", "tests", "verification"]`, `--import-mode=importlib`, `--strict-markers`) |
| Quick run command | `uv run pytest packages/<pkg> -q --no-cov` |
| Full suite command | `uv run pytest packages/higyrus-client packages/matriz-client packages/market-data-client -q --no-cov` (872 tests, **64s measured**) |
| CI-equivalent | `uv run pytest packages/<pkg> --cov=packages/<pkg>/src` per matrix cell (6 pkgs × py3.12/3.13) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DEC-01 / crit.1a | Missing field decodes without raising; exactly 1 record | unit | `uv run pytest packages/higyrus-client/tests/test_decode.py -k missing -x` | ❌ Wave 0 |
| DEC-01 / crit.1b | Wrong type → 1 record, value unchanged from today | unit | `... -k wrong_type -x` | ❌ Wave 0 |
| DEC-01 / crit.1c | Extra wire key → 1 record (**new capability**) | unit | `... -k extra_key -x` | ❌ Wave 0 |
| DEC-01 / crit.1d | Non-dict payload → 1 record, per-package default shape | unit | `... -k non_dict -x` | ❌ Wave 0 |
| DEC-01 / crit.1e | `None` / 204 → `[]` or empty model, per-package | unit | `... -k none_or_204 -x` | ❌ Wave 0 |
| DEC-01 / crit.1f | Record is flat / all-str / top-level / type-not-value | unit | `... -k record_shape -x` (asserts every `extra` value `isinstance(str)`, no nested containers) | ❌ Wave 0 |
| DEC-01 / crit.1g | Record keys never collide with `LogRecord` reserved names | unit | `... -k reserved_keys -x` (constructs a real record) | ❌ Wave 0 — **Pitfall 1** |
| DEC-01 / crit.1h | caplog sentinel: credential literal absent from `getMessage()`, `str(record.args)`, `record.__dict__` | unit ×5 | `uv run pytest packages/<pkg>/tests/test_logging.py -k decode_sentinel -x` | ❌ Wave 0 (extends SEC-01 pattern) |
| DEC-01 / crit.2a | Strict mode raises with the exact field path | unit | `... -k strict_raises_with_path -x` | ❌ Wave 0 |
| DEC-01 / crit.2b | Mode bound from `_ClientState`, inherited by `with_options` views | unit | `... -k strict_mode_view_inherits -x` | ❌ Wave 0 |
| DEC-01 / crit.2c | Interleaved async tasks do not clobber each other's mode | unit | `uv run pytest packages/market-data-client/tests/test_decode_concurrency.py -x` | ❌ Wave 0 |
| DEC-01 / crit.2d | matriz ws daemon thread receives the mode **explicitly** (proves non-inheritance) | unit | `uv run pytest packages/matriz-client/tests/test_ws_decode_mode.py -x` | ❌ Wave 0 |
| DEC-01 / crit.3a | **Zero-edit merge gate:** 872 tests green, no test file modified | integration | `uv run pytest packages/higyrus-client packages/matriz-client packages/market-data-client -q --no-cov` + `git diff --name-only <base> -- '*/tests/*'` empty | ✅ suites exist; the git-diff assertion is Wave 0 |
| DEC-01 / crit.3b | matriz semantics preserved (missing→`None`, `empty()`, pass-through) | unit | `uv run pytest packages/matriz-client/tests/test_models.py -x` | ✅ exists |
| DEC-01 / crit.4a | msgspec D-lock artifact exists and is signed | manual | operator signature on `29-DLOCK-MSGSPEC.md` | ❌ artifact |
| DEC-01 / crit.4b | RESPONSE-`Literal` D-lock; walker never enforces membership | unit + artifact | `... -k literal_not_enforced -x` (matriz `MarketId` with wire `"XYZ"` returns `"XYZ"`, emits divergence) | ❌ Wave 0 |
| DEC-01 / crit.5a | 5-way intactness by normalized hash + declared matriz variant | script (lint job) | `uv run python tools/check_decode_intactness.py` | ❌ Wave 0 |
| DEC-01 / crit.5b | Ban-list grep (`strict=False`, `msgspec.field(`) | script (lint job) | same script / `ci.yml` grep step | ❌ Wave 0 |
| DEC-01 / crit.5c | Sizing floor per package published as `≥ N` | artifact | `uv run python <scratch>/sizing.py` → `29-SIZING.md` | ❌ artifact |

### Sampling Rate

- **Per task commit:** `uv run pytest packages/<pkg> -q --no-cov` (single package, seconds)
- **Per wave merge:** the 872-test 3-package suite (`~64s`) **plus** `git diff --name-only -- '*/tests/*'` must be empty for the SafeModel packages (the zero-edit gate is only meaningful if asserted mechanically)
- **Phase gate:** full workspace `uv run pytest` + `uv run ruff check .` + `uv run ruff format --check .` + `uv run mypy` + `uv run lint-imports` + the new intactness script, all green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `packages/<pkg>/tests/test_decode.py` ×5 — crit. 1a-1g, 2a-2b, 4b
- [ ] `packages/market-data-client/tests/test_decode_concurrency.py` — crit. 2c
- [ ] `packages/matriz-client/tests/test_ws_decode_mode.py` — crit. 2d
- [ ] `tools/check_decode_intactness.py` + `ci.yml` `lint`-job wiring — crit. 5a/5b (**must not live in `verification/`** — Pitfall 10)
- [ ] Zero-edit assertion (git-diff check) wired into the merge gate — crit. 3a
- [ ] Extension of the 5 `test_logging.py` files with a decoder-path caplog sentinel — crit. 1h
- [ ] Framework install: **none** — pytest/httpx/asyncio stack already present

---

## Security Domain

`security_enforcement: true`, `security_asvs_level: 1`.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | This phase adds no auth surface. The ws token path (`_acquire_token_for_ws`) is read-only context for D-04. |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | **yes** | The walker **is** the input-validation layer for untrusted upstream JSON. Control: type-checked per-field coercion with an explicit policy; **never** `eval`/dynamic import from payload; `get_type_hints` resolves only *model-declared* annotations, never payload-supplied names. |
| V6 Cryptography | no | No crypto introduced. |
| **V7 Error Handling & Logging** | **yes — primary** | This is the phase's security center of gravity. Controls: (a) type-not-value record contract; (b) `RedactingFilter` two-part fix; (c) per-package caplog sentinel asserting a credential literal is absent from `getMessage()`, `str(record.args)` **and** `record.__dict__`; (d) `NullHandler` default so a library never emits unless the consumer opts in; (e) strict-mode exception messages carry the **path only**, never the value. |
| V8 Data Protection | **yes** | Argentine PII is in scope: `higyrus` already redacts `cuit=` (tax ID) as a query-param marker. A divergence record must never carry a `cuit` value — the type-not-value contract covers it structurally. |
| V12 Files & Resources | marginal | `RedactingFilter` recursion needs a depth/size bound (Open Question 4) so a hostile payload cannot turn a log filter into a CPU sink. |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Credential leaked through a new log surface (the decoder is a **new** emission path in 5 packages) | Information Disclosure | Type-not-value contract (primary) + `RedactingFilter` (defense in depth) + caplog sentinel ×5 (SEC-01 precedent) |
| PII (`cuit`, account identifiers) in a divergence record | Information Disclosure | Same. Note `higyrus.PosicionValuada.cuenta` and `matriz.AccountId.id` are account identifiers — the record must name the **field**, never the value. |
| Nested `extra=` bypassing redaction entirely | Information Disclosure | Flat, top-level-only record (D-05a). Verified: the current filter skips non-`str` values outright. |
| Hostile/malformed upstream payload causing unbounded work | Denial of Service | Bounded recursion in both the walker (model-driven depth, so bounded by the model tree) and the filter fix (explicit bound). Aggregation caps record volume (Pitfall 7). |
| Observable mode silently becoming fatal via a `KeyError` in the emitter | Denial of Service / availability | Reserved-key test (Pitfall 1); wrap the emit call so an emitter failure can never propagate into the decode return path. |
| Strict-mode exception message carrying wire data | Information Disclosure | Exception carries `field_path` + `declared_type` + `observed_type` only — same vocabulary as the record. |
| Supply chain: a C extension entering six pure-Python wheels | Tampering | Gated behind the D-lock + operator signature; `uv.lock` refresh + `uv lock --check` in CI; the `SUS` verdict is metadata-only (see audit). |

---

## Sources

### Primary (HIGH confidence)

- **Direct execution against this repo** (`uv run`, CPython 3.12.13, branch `milestone/v1.5-mutations` @ `32cc4a3`), 2026-08-18:
  - 872-test 3-package suite: green, 64.18s
  - `from_api` / `get_type_hints` / `fields()` micro-timings
  - `contextvars` thread + `asyncio.gather` semantics
  - `logging` reserved-`extra`-key `KeyError` enumeration
  - `SafeModel`/`_coerce` and `RedactingFilter.filter` byte-hash comparison across all copies
  - schema-corpus → model auto-mapping census (43 files)
  - a working sizing-walker prototype over the corpus
- **Direct execution in an ephemeral env** (`uv run --with msgspec --no-project`): msgspec 0.21.1 `convert()` behavior (extra-key silence, fail-fast `ValidationError` with path, missing-field error) + 0.22 µs/op timing
- **Repo source read at specific lines** — `models.py` ×3, `_logging.py` ×5, `_state.py` ×5, `client.py`/`aio.py` `_request` sites, `ws_client.py`, `_core.py` parsers, `verification/{schema,safemodel_diff,findings,test_logging_no_token_leak,test_public_surface}.py`, `.github/workflows/ci.yml`, root `pyproject.toml`
- `gsd-tools query package-legitimacy check --ecosystem pypi msgspec`

### Secondary (MEDIUM confidence)

- `.planning/research/SUMMARY.md` — the four-researcher convergence (msgspec cannot implement observable mode; matriz is not verbatim; 14/25 pitfalls land here). Independently corroborated by execution above.
- `.planning/future-plans/tipado_homogeneo.md` — DT-01..DT-09. Note three of its Phase-29 bullets are superseded (see State of the Art).
- `.planning/STATE.md`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`

### Tertiary (LOW confidence)

- `.planning/codebase/CONCERNS.md` — dated 2026-05-27, describes conditions since fixed. **Do not plan against it.**
- `contextvars.Context` re-entrancy behavior under concurrent `ctx.run()` — reasoned, not executed (A1).

---

## Metadata

**Confidence breakdown:**

| Area | Level | Reason |
|------|-------|--------|
| Standard stack | **HIGH** | stdlib-only primary path; msgspec behavior + version re-verified by execution this session |
| Walker design / `_coerce` delta | **HIGH** | Read off both implementations line by line; the extra-key limitation is structural and demonstrable |
| 6-way semantics matrix | **HIGH** | Every cell read from source; byte-level status of the near-duplicate blocks measured |
| Divergence record schema | **HIGH** | Reserved-key collisions enumerated by execution; redaction gaps read off the filter body |
| ContextVar mechanics | **HIGH** for thread/task semantics (measured); **MEDIUM** for the ws propagation mechanism (two viable shapes, re-entrancy unverified — A1) |
| Timing spike design | **HIGH** — the false-GO trap is measured, not hypothesized |
| Sizing run design | **HIGH** for feasibility and the envelope constraint (prototype ran); **LOW** for the market-data floor magnitude (A4) and the manual mappings (A5) |
| Pitfalls | **HIGH** — 11 of 13 verified against the repo or by execution; 2 flagged as assumptions |
| Aggregation contract | **LOW/proposal** — A3; this is a decision the phase must make, not a finding |

**Research date:** 2026-08-18
**Valid until:** 2026-09-17 (30 days — stdlib-based, stable stack). Invalidated earlier by: any change to `models.py` in the 3 SafeModel packages, any `ci.yml` `testpaths` change, or a msgspec major release.
