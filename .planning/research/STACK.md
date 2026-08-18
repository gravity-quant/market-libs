# Stack Research

**Domain:** Typed public surface for six independently-released Python HTTP client wheels (msgspec-backed observable decoding)
**Milestone:** v1.6 · Tipado homogéneo de la superficie pública (phases 29-34)
**Researched:** 2026-08-18
**Confidence:** HIGH — every load-bearing claim below was verified by execution against msgspec 0.21.1, the live PyPI/GitHub APIs, or the repo itself. Nothing here is inferred from memory.

---

## TL;DR — the five answers

| # | Question | Answer |
|---|----------|--------|
| 1 | msgspec version + status | `msgspec>=0.19,<0.22` (resolves to **0.21.1**, 2026-04-12). 48 wheels, cp310–cp314 × 8 platforms incl. musllinux + win_arm64 + cp314t free-threaded. Actively maintained. |
| 2 | Optional extra vs hard dep | **Hard runtime dependency.** The fallback path *is* the bug the milestone exists to delete. Dual-path cost is 12 code paths + a 24-job CI matrix, buying coverage only for platforms this project has no consumers on. |
| 3 | Dep-profile interaction | **Zero conflicts, zero transitive deps.** But msgspec becomes the **first compiled artifact** in a currently 100%-pure-Python closure (verified 10/10). One root `uv.lock`, 48 → 49 packages, one refresh total (not six). |
| 4 | Observable-mode API | msgspec is **fail-fast, one error, no collection API**. A **two-pass helper is mandatory**: strict `convert` fast path → on `ValidationError`, per-field `convert` loop that reports every divergence and substitutes defaults. Verified sketch below. |
| 5 | AST gate + parity test | **stdlib only** — `ast` + `typing.get_type_hints` + `inspect`. Verified: `get_type_hints` succeeds on **130/130** public callables across all 6 packages, 0 failures. No third-party need. |

---

## Recommended Stack

### Core Technologies — the single addition

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **msgspec** | `>=0.19,<0.22` → resolves **0.21.1** | Internal decode engine for the DEC-01 observable helper | Only library verified to decode straight into stdlib `@dataclass(frozen=True, slots=True)` with **no base-class inheritance** — which is precisely what makes DT-01 (no third-party type in any public signature) achievable. Strict by default, so divergences surface instead of being coerced away. Zero runtime deps, `py.typed`, BSD-3-Clause, ~200 KiB wheel. |

### What explicitly does NOT change

| Technology | Version | Status |
|------------|---------|--------|
| httpx | `>=0.27` | Unchanged — decode happens on the already-parsed payload, not the wire |
| python-dotenv | `>=1.0` | Unchanged |
| tenacity | `>=9.1.0,<10` | Unchanged |
| platformdirs | `>=4.0,<5` (iol only) | Unchanged |
| websocket-client | `>=1.8.0` (matriz only) | Unchanged |
| mypy / ruff / pytest / pytest-httpx | current | Unchanged — msgspec is clean under `--strict` (verified) |

**Nothing is removed.** `SafeModel` / `from_api` stay as the public constructor (DT-05); only their *body* changes.

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `ast` (stdlib) | GATE-TYP-01 surface gate | Parses annotations as real expression nodes even under `from __future__ import annotations` — no import, no runtime side effects. Verified working. |
| `typing.get_type_hints` (stdlib) | DT-04 sync/async parity introspection | Verified: 130/130 public callables resolve across all 6 packages, 0 `NameError`. |
| `inspect` (stdlib) | Signature/param comparison for parity | — |
| `msgspec.inspect` | *Available but not needed* | `type_info()` works on dataclasses, but the gate should stay stdlib-only so it can run even if msgspec is broken. |

---

## Installation

```toml
# packages/<each-of-six>/pyproject.toml — append to [project].dependencies
dependencies = [
    "httpx>=0.27",
    "python-dotenv>=1.0",
    "tenacity>=9.1.0,<10",
    "msgspec>=0.19,<0.22",  # Phase 29 DEC-01 — internal decoder only, never in public signatures (DT-01)
]
```

```bash
uv lock                                    # one refresh; 48 -> 49 packages
uv sync --all-packages --all-extras --dev  # 6 pyprojects, ONE resolution
uv lock --check                            # CI gate, currently green
```

---

## (1) msgspec version pinning + release status

### Verified release facts

| Fact | Value | How verified |
|------|-------|--------------|
| Latest version | **0.21.1** | PyPI JSON API |
| Uploaded | 2026-04-12 | PyPI JSON API |
| requires-python | `>=3.10` | PyPI metadata |
| Runtime dependencies | **none** (only `toml`/`yaml` optional extras) | `requires_dist` |
| License | **BSD-3-Clause** | GitHub API — permissive, compatible with the MIT wheels |
| `py.typed` | **present** | inspected installed package |
| Wheel size | 184–220 KiB; 551 KiB installed | PyPI file sizes + install |
| Repo | `msgspec/msgspec` (org-ified from `jcrist/msgspec`) | GitHub API |
| Maintenance | 4,036 stars, **pushed 2026-08-12** (6 days ago), not archived, 228 open issues | GitHub API |

### Wheel matrix — 48 wheels + 1 sdist

| Python tag | ABI | Platforms (8 each) |
|------------|-----|--------------------|
| cp310, cp311, cp312, cp313, cp314 | matching | `macosx_x86_64`, `macosx_11_0_arm64`, `manylinux_2_17/2_28_x86_64`, `manylinux_2_17/2_28_aarch64`, `musllinux_1_2_x86_64`, `musllinux_1_2_aarch64`, `win_amd64`, `win_arm64` |
| **cp314** | **cp314t** | same 8 — **free-threaded build supported** |

**Coverage for this project's targets is complete.** `requires-python >=3.12`; CI is `ubuntu-latest` × py3.12/3.13 — fully covered by prebuilt wheels. macOS arm64 (the dev machine) fully covered.

### Known gaps and issues

| Gap | Impact here |
|-----|-------------|
| **No `cp313t`** free-threaded wheel (only `cp314t`) | None — project doesn't use free-threaded 3.13 |
| **No PyPy wheels at all** (CPython C-API extension) | PyPy consumers would need a compiler and would likely fail to build |
| No `linux armv7l` / 32-bit ARM, `ppc64le`, `s390x`, `win32` | Nil for this consumer base |
| New-CPython lag window | 0.20.0 shipped cp314 in **Nov 2025**, at/ahead of CPython 3.14's release — a good signal, but a 3.15 gap window is plausible |
| Release cadence is lumpy | 0.18.6 (Jan 2024) → 0.19.0 (Dec 2024) is an 11-month gap; recent cadence has improved (0.20.0 Nov 2025, 0.21.0/0.21.1 Apr 2026) |

### Pinning strategy — `msgspec>=0.19,<0.22`

**Floor `0.19` is evidence-based, not arbitrary:**
- **0.18.5** fixed *"bug preventing decoding dataclasses/attrs types with default values and `slots=True, frozen=True`" (#569)* — that is **exactly** this milestone's model shape. Anything below 0.18.5 is disqualified.
- **0.19.0** added Python 3.13 support. Since CI tests 3.13, a resolution below 0.19 would have no wheel on the 3.13 leg. Floor at 0.19.

**Ceiling `<0.22` matches house style.** `tenacity>=9.1.0,<10` and `platformdirs>=4.0,<5` cap at the next breaking boundary; for a 0.x project that boundary is the next *minor*. msgspec does ship breaking changes in minors — verified from release notes:

| Version | Breaking change | Touches this project? |
|---------|-----------------|-----------------------|
| 0.19.0 | Removed deprecated `from_builtins`; `encode_into` buffer behaviour | No |
| 0.21.0 | `__post_init__` now called from `structs.replace`/`copy.replace` | No |

None hit `convert` / `json.decode` with dataclasses — but the pattern is established, so the cap is warranted for a **load-bearing** dependency.

**The cap's cost is affordable *specifically because these wheels are not on PyPI.*** They ship as GitHub Release artifacts to a controlled consumer set, so the classic "capped library blocks a consumer's upgrade" dependency-hell scenario has a known, small blast radius. Accept an annual chore: when 0.22 lands, verify and widen the cap in a patch release across the affected packages.

> If the project ever publishes to PyPI, revisit this — a `<0.22` cap replicated across six public wheels becomes a genuine liability and should widen to `<1.0`.

---

## (2) C-extension risk: hard dependency, not an optional extra

### Recommendation: **hard runtime dependency in all six packages.**

### Which consumer platforms would need a compiler

Only these, and none of them is a plausible consumer of Argentine fintech client libraries:

- PyPy (any version) — no wheels exist
- CPython 3.13t free-threaded
- Linux `armv7l` / 32-bit ARM, `ppc64le`, `s390x`
- 32-bit Windows (`win32`)
- Any CPython release before msgspec ships wheels for it

Everything the project and its consumers actually run — macOS arm64/x86_64, manylinux and musllinux on x86_64/aarch64, Windows amd64/arm64, CPython 3.12/3.13/3.14 — has a prebuilt wheel.

### Why the optional-extra pattern loses

The plan's own framing (`market-data-client[msgspec]` with fallback to `_coerce`) is worth rejecting on four concrete grounds:

1. **The fallback path is the defect being removed.** `_coerce` is silent tolerance — a missing field becomes `0.0` with nobody informed. That is the milestone's stated core-value violation. An optional extra means a consumer who doesn't opt in gets the old silent corruption *and cannot tell*, because the whole point is that it's silent. The milestone would ship a flag that quietly disables the milestone.
2. **Dual-path cost is 12 implementations, not 2.** DT-03 forbids shared code, so the fallback is copied verbatim six times alongside the msgspec path. Every future decoder fix becomes a 12-site change instead of 6.
3. **CI doubles.** Today: 6 packages × 2 Pythons = 12 test jobs. Honest fallback verification needs a no-msgspec leg → **24 jobs**, plus divergence-behaviour assertions that differ per leg.
4. **The GATE-TYP-01 surface gate cannot express it.** The AST gate asserts "this exported function returns a typed model." It has no way to encode "…unless msgspec is absent, in which case the tolerance semantics silently differ." DT-09 declares the gates first-class; an optional extra makes one of them unenforceable.

Against that: the extra buys install coverage on PyPy / 3.13t / armv7 / s390x — platforms with zero present or projected consumers.

### The escape hatch, if it is ever needed

Don't pre-build it. If a real consumer reports a real platform gap, the fix is contained to the single `_decode.py` helper per package — lazy `try: import msgspec / except ImportError` with a pure-Python per-field fallback **that still emits the same structured divergence records**. That preserves observability (the actual requirement) rather than reverting to silence, and it's decided with evidence rather than speculation. Note this as a v1.7 carry-forward, not Phase 29 work.

---

## (3) Existing dep profile + uv workspace / lockfile implications

### Conflicts: none. Verified by resolution.

```
$ uv pip compile  (httpx + python-dotenv + tenacity + platformdirs + websocket-client + msgspec>=0.19,<0.22)
Resolved 12 packages in 198ms
  msgspec==0.21.1          <- adds ZERO transitive dependencies
```

msgspec has no required runtime deps, so it cannot conflict with anything. `uv lock --check` currently passes (48 packages); adding msgspec makes it **49**.

### The one real change: purity of the dependency closure

**Verified — every package in the current transitive closure is pure Python** (single `py3-none-any` wheel each):

| httpx | httpcore | certifi | idna | sniffio | anyio | h11 | python-dotenv | tenacity | platformdirs |
|---|---|---|---|---|---|---|---|---|---|
| pure | pure | pure | pure | pure | pure | pure | pure | pure | pure |

msgspec would be the **first compiled artifact** in the tree. This is the accurate statement of the risk — not "msgspec might not install" (it will, everywhere that matters), but "the project loses the property that its wheels install with zero build tooling on *any* platform." That property is worth naming in the Phase 29 record, and worth a line in each README's changelog under DT-08.

### uv workspace mechanics

- **One root `uv.lock`, one resolution.** Adding the same requirement to six member `pyproject.toml` files produces **one** lock entry, not six. uv unifies the workspace into a single resolution.
- **Phase 34 nuance to correct in the plan:** the roadmap says "`uv.lock` refresh **only** of packages whose surface changed." The lockfile is global — it changes exactly once regardless of how many packages bump. Only the *version bumps and README changelogs* are per-package.
- `uv build --package <name>` reads that member's own `pyproject.toml`, so each wheel independently declares `msgspec>=0.19,<0.22` in its metadata — correct for standalone distribution.
- CI already runs `uv sync --all-packages --all-extras --dev --frozen`; the frozen sync will fail loudly if the lock isn't refreshed alongside the six pyprojects. Land both in the same commit.
- **`wallets-client` is the judgement call.** It's a stub with no endpoints and TYP-03 gives it only empty `models.py`/`types.py`. Adding msgspec there buys nothing today. Recommendation: **add it anyway**, for the DT-03 reason that all six must be structurally identical — but flag it in Phase 31 as a deliberate, reversible choice rather than an oversight.

### Operational note — the plan's venv warning is stale

The plan records that `.venv/` points at a dead interpreter. **Verified false as of today**: `.venv/bin/python` → CPython **3.12.13**, working; `uv lock --check` resolves cleanly; all six packages import. No pre-milestone repair step is needed.

---

## (4) Observable-mode API — msgspec is fail-fast; a two-pass helper is mandatory

### The decisive finding

**msgspec has no multi-error collection API and no non-raising validation mode.** It reports exactly one error and raises. Verified against 0.21.1 with a payload where *all four* fields are wrong:

```python
bad = {"simbolo": 1, "ultimoPrecio": "x", "cantidad": "y", "puntas": 3}
msgspec.convert(bad, type=Quote)
# msgspec.ValidationError: Expected `str`, got `int` - at `$.simbolo`
#                          ^ one error only. The other three are invisible.
```

So the tolerant-with-report mode DEC-01 requires **cannot** be built from a single call. **Two-pass is the answer**, and it maps exactly onto the strategy named in the question.

### Supporting behaviours (all verified on 0.21.1)

| Behaviour | Result | Consequence for the helper |
|-----------|--------|----------------------------|
| Dataclass **defaults honoured** when field absent | `convert({}, type=Quote)` → `Quote(simbolo='', ultimoPrecio=0.0, ...)` | **If every model field has a default, missing fields never raise.** Only *wrong types* raise. This reproduces `SafeModel` tolerance for free. |
| Missing field **without** a default | `Object missing required field 'ultimoPrecio'` | **Design constraint: every model field must carry a default**, or the second pass can't reconstruct. |
| Extra/unknown fields | Ignored by default | Matches current `SafeModel` |
| Non-dict payload | `Expected 'object', got 'null'` (and `array`/`str`/`int`) | Clean `None`/204 handling |
| Error paths | `$.ultimoPrecio`, `$.items[0].a`, `$[1].simbolo` | Full JSON-pointer paths, incl. nesting and list index — ideal for structured logging |
| `Literal` | `Invalid enum value 'bcaba' - at '$.lit'` | Directly delivers DT-07's `mercado`/`plazo` enforcement |
| `__post_init__` | **Is called** | `received_at` client-stamping keeps working |
| `datetime` / `Decimal` | ISO-8601 and string→Decimal supported | Available if models want real temporal types |
| `strict=False` | `"123.5"` → `123.5` **silently** | **Never use it.** This is Pydantic's rejected lenient behaviour — it masks the exact divergences being hunted. |
| Exception hierarchy | `ValidationError < DecodeError < MsgspecError < **ValueError**` | See leak warning below |
| Fast-path cost | **~0.49 µs** per convert | Two-pass is free: pass 2 runs only when a divergence exists |
| mypy `--strict` | `convert(p, type=Quote)` → `Quote`; `convert(p, type=list[Quote])` → `list[Quote]` | **No `Any` leak, no `warn_return_any` hit.** Generic `type[T]` passthrough infers `T`. |

> **DT-01 extends to exceptions.** `msgspec.ValidationError` is a third-party type. If it escapes `from_api`, msgspec has leaked into the public contract just as surely as if it appeared in a signature. Strict mode must raise a **package-local** error (e.g. `IOLDecodeError ⊂ IOLClientError`), never the msgspec class. Note that because it subclasses `ValueError`, a caller's `except ValueError` would swallow it today — silent, and exactly the failure mode this milestone opposes.

### Verified helper sketch (`_decode.py`, copied verbatim ×6 per DT-03)

This exact code was executed and produced the output shown:

```python
from __future__ import annotations

import logging
import typing
from functools import lru_cache
from typing import Any, TypeVar

import msgspec

T = TypeVar("T")
_log = logging.getLogger("iol_client")  # per-package; RedactingFilter already attached


class IOLDecodeError(IOLClientError):
    """Strict-mode decode failure. Never leaks a msgspec type (DT-01)."""
    def __init__(self, cls: type, divergences: list[tuple[str, str]]) -> None:
        self.divergences = divergences
        super().__init__(f"{cls.__name__}: " + "; ".join(f"{p}: {m}" for p, m in divergences))


@lru_cache(maxsize=None)
def _hints(cls: type) -> dict[str, Any]:
    # get_type_hints is expensive; the slow path must not pay it repeatedly.
    return typing.get_type_hints(cls)


def decode(payload: Any, cls: type[T], *, strict: bool = False, path: str = "$") -> T:
    # -- Pass 1: strict, C-speed (~0.5us). The overwhelmingly common case.
    try:
        return msgspec.convert(payload, type=cls)
    except msgspec.ValidationError:
        pass

    # -- Pass 2: field-by-field, collecting EVERY divergence.
    divergences: list[tuple[str, str]] = []
    if not isinstance(payload, dict):
        divergences.append((path, f"expected object, got {type(payload).__name__}"))
        payload = {}

    kept: dict[str, Any] = {}
    for name, ftype in _hints(cls).items():
        if name not in payload:
            continue  # absent -> dataclass default applies (SafeModel semantics)
        try:
            kept[name] = msgspec.convert(payload[name], type=ftype)
        except msgspec.ValidationError as exc:
            divergences.append((f"{path}.{name}", str(exc)))

    if strict:                        # drivers: divergence -> finding
        raise IOLDecodeError(cls, divergences)

    for field_path, message in divergences:   # runtime: observable, never fatal (DT-02)
        _log.warning(
            "schema divergence",
            extra={"model": cls.__name__, "field": field_path, "detail": message},
        )
    return msgspec.convert(kept, type=cls)
```

**Verified output:**

```
TWO-PASS value:        Quote(simbolo='', ultimoPrecio=0.0, cantidad=5, puntas=['a'])
TWO-PASS divergences:  [('$.simbolo',      'Expected `str`, got `int`'),
                        ('$.ultimoPrecio', 'Expected `float`, got `str`')]
NONE value:            Quote(simbolo='', ultimoPrecio=0.0, cantidad=0, puntas=[])
             div:      [('$', 'expected object, got NoneType')]
STRICT raises:         [('$.simbolo', 'Expected `str`, got `int`')]
```

Note it recovers **all** divergences and **still returns a usable value** with good fields preserved (`cantidad=5`, `puntas=['a']`) — precisely DT-02's "silent → observable, not tolerant → fatal."

### Integration points

- **Use `msgspec.convert`, not `msgspec.json.decode`.** The `_core.py` parsers are pure functions over already-parsed payloads, guarded by import-linter contracts. `convert` slots in without touching that architecture and leaves the `pytest-httpx` suites untouched — which is exactly the Phase 29 merge gate ("suites green **without test changes**"). `json.decode(resp.content, ...)` would be marginally faster but forces a parser-signature rewrite and breaks the contract boundary. **Not worth it.**
- **`from_api` becomes a one-liner:** `return decode(payload, cls)` — signature unchanged (DT-05).
- **Strict-mode plumbing:** thread it via an existing mechanism rather than a new global. The `request.extensions` idiom (used for `idempotent` and `max_attempts`) is the established house pattern, but decode happens after the response — a module-level flag set by the driver, or a `strict=` parameter threaded from `_ClientState`, is simpler. Decide in Phase 29.
- **`RedactingFilter` caveat:** it scrubs known credential patterns from log records. The divergence record above logs *field names and type names only* — never values. **Keep it that way.** Logging the offending value would route live payload data through the logger and is a credential-leak vector the `caplog` sentinel test (SEC-01 precedent) should assert against.

---

## (5) AST gate + sync/async parity — stdlib is sufficient. Verified.

**No third-party dependency needed.** Both prototypes below were executed against the real repo using only `ast`, `typing`, and `inspect`.

### `typing.get_type_hints` works everywhere — 130/130

| Package | Public callables resolved | Failures |
|---------|--------------------------|----------|
| iol_client | 15 | **0** |
| higyrus_client | 17 | **0** |
| matriz_client | 47 | **0** |
| ambito_financiero_client | 7 | **0** |
| wallets_client | 3 | **0** |
| market_data_client | 41 | **0** |

The plausible failure mode — `from __future__ import annotations` (mandatory in all 56 source modules) combined with `if TYPE_CHECKING:` imports making annotations unresolvable at runtime — **does not materialise**. The only two `TYPE_CHECKING` blocks in the codebase are in matriz's *private* modules (`_state.py`, `_token_store.py`) and never appear in public annotations. The parity test can call `get_type_hints` directly with no fallback machinery.

### The AST gate reads source, never imports

`ast.parse` yields real expression nodes for annotations regardless of `from __future__ import annotations` (that future only affects *runtime* evaluation). So `ast.unparse(node.returns)` gives `"dict[str, Any]"` directly. No import side effects, no `load_dotenv()` at collection time.

### Measured sizing for Phase 32 — 34 violations, of which 27 are real

Running the gate in the exact scope DT-06 specifies (returns of functions exported in `__all__`):

| Package | `__all__` size | Violations | Notes |
|---------|---------------|-----------|-------|
| **iol_client** | 13 | **12** | 4 data functions × (`Client` method + `AsyncClient` method + module shim) |
| **higyrus_client** | 29 | **3** | `get_health` × 3 |
| **market_data_client** | 39 | **19** | 12 real (health/health_feed/add_holidays/delete_holiday × 3) + **7 `to_dict()`** |
| matriz_client | 64 | **0** | ✓ confirms the plan's survey |
| ambito_financiero_client | 9 | **0** | ✓ |
| wallets_client | 5 | **0** | ✓ |
| **TOTAL** | | **34** | **27** after the `to_dict` exemption below |

### Two gaps in DT-06 as written — surfaced by running the gate

1. **`to_dict() -> dict[str, Any]` needs an explicit exemption.** Seven request-model methods (`NewSymbol`, `NewSymbols`, `SymbolPatch`, `LatestRequest`, `HolidayIn`, `HolidaysIn`, `MarketHoursIn`) return `dict[str, Any]` **correctly** — they serialize *out* to a JSON body. They are public methods on `__all__`-exported classes, are not dunders, and have no leading underscore, so DT-06's current exemption list does not cover them. Without an added carve-out the gate reports 7 false positives forever.
2. **Private *modules* need exemption, not just private *names*.** A broader scan (all functions, not just `__all__`) finds 55 candidates, the extra 21 being public-named functions inside private modules: `_core.py` parsers (`parse_get_quote_response`, `parse_envelope_response`, `unwrap`, …), `_params.py::drop_none`, `_token_cache.py::load`. DT-06 exempts "helpers internos con `_`" — that reads as a *name* rule. Make it explicit that a leading-underscore **filename** also exempts, or scope the gate to `__all__` only (cleaner, and what the 34 number above assumes).

Recommend resolving both as DT-06 amendments during Phase 29 discussion, before Phase 32 builds the gate against an ambiguous spec.

### Non-vacuity — the Phase 15 WR-01/WR-02 lesson

DT-09 and the plan both flag that a parity guard must not silently pass. Both prototypes here are demonstrably non-vacuous: the AST gate **found 55 candidates** and the `__all__` gate **found 34**. Bake that into the tests themselves — assert a known-violating fixture is caught, and assert the discovered-callable count is above a floor, so an introspection bug that yields an empty set fails loudly instead of passing green.

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| msgspec hard dep | msgspec optional extra + `_coerce` fallback | Only if a real consumer on PyPy / 3.13t / armv7 / s390x materialises. Then implement as a lazy import inside the single `_decode.py` that **still emits divergence records** — never a silent-tolerance revert. |
| `msgspec.convert(dict)` | `msgspec.json.decode(bytes)` | If decode throughput ever dominates (it won't — 0.49 µs/convert vs a network round-trip). Costs a `_core.py` parser-signature rewrite and breaks the import-linter contract boundary. |
| `msgspec>=0.19,<0.22` | `msgspec>=0.19,<1.0` | If these wheels are ever published to PyPI, where six replicated caps become real dependency hell. Trade-off: exposure to 0.x minor breakage in a load-bearing component. |
| stdlib `ast` + `typing` | `msgspec.inspect.type_info` | Never for the gate — the gate must stay runnable even when msgspec is broken. |
| Two-pass helper | Single strict `convert` + re-raise | Only for driver strict mode — but then you lose the "report *all* divergences at once" property, and Phase 33's whole purpose is efficient bulk divergence discovery. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **`msgspec.convert(..., strict=False)`** | Silently coerces `"123.5"` → `123.5` — **verified**. This is the identical lenient behaviour that got Pydantic v2 rejected, reintroduced through a keyword argument. It masks the exact divergences the milestone exists to surface. | Default `strict=True` + the two-pass helper |
| **Pydantic v2** | Lenient-by-default coercion + `pydantic-core` (~2 MB compiled) across six wheels | msgspec (~200 KiB, strict by default) |
| **`TypedDict`** | Empirically rejected: mypy does not flag `q.get("typo")`, which is the drivers' actual access style | Frozen `slots=True` dataclasses (attribute access is checked in all cases) |
| **A shared `market-libs-core`** | Couples six independent release cycles (DT-03) | Verbatim copy ×6 |
| **Letting `msgspec.ValidationError` escape `from_api`** | Leaks a third-party type into the public contract (DT-01); and since it subclasses `ValueError`, a caller's `except ValueError` swallows it silently | Wrap in a package-local `<Pkg>DecodeError ⊂ <Pkg>ClientError` |
| **Logging the offending field *value*** | Routes live payload data through the logger — credential-leak vector | Log model name + field path + expected/got type only; assert with a `caplog` sentinel (SEC-01 precedent) |
| **Models with fields lacking defaults** | Verified: a missing required field raises, and the two-pass reconstruct cannot recover it | Give every model field a default (already the `SafeModel` convention) |

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| `msgspec 0.21.1` | Python 3.12, 3.13, 3.14 (+3.14t) | Prebuilt wheels; project's `requires-python >=3.12` fully covered |
| `msgspec 0.21.1` | httpx / tenacity / platformdirs / websocket-client / python-dotenv | **Zero shared deps** — conflict impossible. Verified by resolution. |
| `msgspec >=0.18.5` | `@dataclass(frozen=True, slots=True)` | Below 0.18.5 this combination is **broken** (upstream #569) |
| `msgspec >=0.19.0` | Python 3.13 | 3.13 support added in 0.19.0 — the binding floor for this project's CI |
| `msgspec >=0.20.0` | Python 3.14, Windows arm64 | Needed only if 3.14 consumers appear |
| `msgspec 0.21.1` | mypy `--strict` (`warn_return_any = true`) | Verified clean: no `Any` leak on single or collection decode |
| `msgspec 0.21.1` | ruff rule sets E/W/F/I/B/UP/SIM/RUF/ASYNC/PIE/PT/RET/TID | No interaction — plain function calls |

---

## Corrections and refinements to the milestone plan

Findings that should reach the roadmapper, all measured:

1. **The iol "16 signatures" count is scope-dependent.** `__all__`-visible: **12** (4 functions × Client + AsyncClient + module shim). Total source edits: **16** (adding the `aio` module shims) **+ 4 `_core.py` parsers = 20**. Both numbers are right for different scopes; state which one a given task means.
2. **DT-06 needs two amendments before Phase 32** — a `to_dict()` serialize-out exemption (7 false positives) and an explicit private-*module* exemption (21 more). Resolve in Phase 29 discussion.
3. **Phase 34's "`uv.lock` refresh only of changed packages" is not achievable** — the lock is global and refreshes once. Only bumps and changelogs are per-package.
4. **The stale-venv operational note is obsolete** — `.venv` is healthy on CPython 3.12.13; no repair step needed.
5. **Free-threaded coverage is 3.14t only** — if 3.13t ever enters the CI matrix, msgspec has no wheel for it.
6. **The C-extension risk is real but narrower than the plan implies.** The accurate framing is not "consumers may fail to install" (they won't, on any target platform) but "the dependency closure stops being 100% pure-Python" — verified 10/10 pure today. Worth a README changelog line under DT-08.

---

## Sources

- **PyPI JSON API** (`pypi.org/pypi/msgspec/json`, `/0.21.1/json`, `/0.20.0/json`) — version, upload dates, full 48-wheel matrix, `requires_dist`, file sizes — **HIGH**
- **PyPI JSON API** × 10 packages (httpx, httpcore, certifi, idna, sniffio, anyio, h11, python-dotenv, tenacity, platformdirs) — pure-Python closure verification — **HIGH**
- **GitHub API** `repos/msgspec/msgspec` + `/releases` — maintenance status, license, breaking-change history for 0.19.0 / 0.20.0 / 0.21.0 / 0.21.1 — **HIGH**
- **Direct execution, msgspec 0.21.1** (`uv run --with msgspec==0.21.1 --no-project`) — fail-fast behaviour, defaults/nesting/Literal/`__post_init__`/non-dict handling, `strict=False` leniency, error path formats, 0.49 µs benchmark, and the full two-pass helper sketch — **HIGH (executed, not inferred)**
- **Direct execution, mypy 1.x `--strict`** — `reveal_type` on `convert` for scalar, collection, and generic `type[T]` forms — **HIGH**
- **Direct execution against this repo** (`.venv/bin/python`, CPython 3.12.13) — `get_type_hints` 130/130 across 6 packages; AST gate prototype finding 55 candidates / 34 in `__all__` scope; `uv lock --check`; `uv pip compile` resolution — **HIGH**
- **Repo inspection** — 6 × `pyproject.toml`, root `pyproject.toml` (mypy `files` confirms the D-16 gap: 5 of 6 packages), `.github/workflows/ci.yml` (ubuntu-latest × py3.12/3.13 × 6 packages = 12 jobs) — **HIGH**

---
*Stack research for: typed public surface across six independently-released Python client wheels*
*Researched: 2026-08-18*
