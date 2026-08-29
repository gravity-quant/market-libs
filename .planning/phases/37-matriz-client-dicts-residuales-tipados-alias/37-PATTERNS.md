# Phase 37: `matriz-client` — dicts residuales tipados + alias - Pattern Map

**Mapped:** 2026-08-29
**Files analyzed:** 7 (2 source, 1 tool, 4 test — 1 test file is NEW)
**Analogs found:** 7 / 7

Every file this phase touches has a concrete in-repo analog. There is **no** "no analog found"
section: this phase is composition of existing mechanisms, not invention (37-RESEARCH "Don't
Hand-Roll" key insight). The Phase 36 `market-data-client` work is the named template for the
Null Object / alias / provenance-docstring dimension; matriz's own `parse_get_positions_response`
is the template for the envelope dimension; `iol-client`'s RED fixture is the template for the
gate non-vacuity dimension.

## File Classification

| New/Modified File | New? | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|------|-----------|----------------|---------------|
| `tools/check_surface_types.py` | mod | config / CI gate (AST static analysis) | batch / transform | itself — `_candidates_for` + `_adjudicate` (`:495-539`) | exact (self-analog: the field dimension mirrors the existing return dimension) |
| `packages/matriz-client/src/matriz_client/models.py` — new classes + 4 retypes | mod | model | transform (wire→typed) | `packages/market-data-client/src/market_data_client/models.py:272-410` (`BookLevel`, `EntryValue`, `MarketDataEntries`) | exact |
| `packages/matriz-client/src/matriz_client/models.py` — 6 alias properties | mod | model | transform (read-only view) | `market_data_client/models.py:381-409` | exact |
| `packages/matriz-client/src/matriz_client/models.py` — recursive mapping axis | mod | utility (call-site decode axis) | transform | `matriz_client/models.py:99-197` (itself — the single-level version being upgraded) | role-match (recursion is genuinely new — F-8) |
| `packages/matriz-client/src/matriz_client/_core.py` — 2 risk parsers | mod | service / response parser | request-response | `matriz_client/_core.py:884-889` `parse_get_positions_response` | exact (sibling endpoint, same layer, same file) |
| `packages/matriz-client/tests/test_surface_types_red.py` | **NEW** | test (gate non-vacuity) | batch | `packages/iol-client/tests/test_surface_types_red.py` | exact |
| `packages/matriz-client/tests/test_core.py` — envelope regressions | mod | test | request-response | `test_core.py:98-136`, `:172-182` (same file, envelope + unwrap cases) | exact |
| `packages/matriz-client/tests/test_null_object.py` — real-alias assertions + roster floor | mod | test | transform | `packages/market-data-client/tests/test_market_data_chain.py:479-504` | exact |
| `packages/matriz-client/tests/test_decode.py` / `test_models.py` — assertion flips | mod | test | transform | themselves (hit list in 37-RESEARCH Pitfall 4) | exact |
| `.planning/verification/matriz-client-findings.md` — provenance rows | mod | doc / ledger | batch | itself (`Index` table + `Detalle por hallazgo`) | exact |

**Files explicitly NOT touched** (writing a task for any of these produces a no-op — F-4, F-12):
`ws_client.py`, `client.py`, `aio.py`, `_decode.py`, `_logging.py`, and every non-matriz package.

## Pattern Assignments

### `tools/check_surface_types.py` (config / CI gate, batch)

**Analog:** itself — the existing return-annotation dimension. D-01a adds a parallel
`_field_candidates_for` + `_adjudicate_field` pair alongside `_candidates_for` + `_adjudicate`.

**Candidate-collection pattern to mirror** (`tools/check_surface_types.py:495-514`):
```python
def _candidates_for(
    binding: _Binding,
) -> list[tuple[str, str, ast.FunctionDef | ast.AsyncFunctionDef]]:
    """The definitions one resolved export contributes to the scan. ..."""
    node = binding.node
    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
        return [(node.name, node.name, node)]
    if isinstance(node, ast.ClassDef):
        return [
            (f"{node.name}.{member.name}", member.name, member)
            for member in _module_level_statements(node.body)
            if isinstance(member, ast.FunctionDef | ast.AsyncFunctionDef)
        ]
    return []
```
The field version keeps the same `(qualified, simple, node)` triple shape and the same
`_module_level_statements(node.body)` traversal (so conditionally-defined fields are included),
but filters `ast.AnnAssign` with an `ast.Name` target instead of function defs. Only `ClassDef`
bindings contribute; a `FunctionDef` binding contributes nothing.

**Adjudication pattern to mirror** (`:517-539`):
```python
def _adjudicate(
    qualified: str, member: str, node: ast.FunctionDef | ast.AsyncFunctionDef, package: str
) -> tuple[str | None, str | None]:
    """Classify one candidate definition as ``(exemption_reason, violation)``. ..."""
    annotation = node.returns
    if annotation is not None and not _annotation_mentions_any(annotation):
        return None, None
    reason = _is_exempt(member)
    if reason is not None:
        return reason, None
    if annotation is None:
        detail = "has no return annotation"
    else:
        detail = f"returns `{ast.unparse(annotation)}`"
    return None, f"    `{package}.{qualified}` {detail} on the exported surface"
```
Copy the two-slot `(exemption_reason, violation)` return contract and the
`f"    \`{package}.{qualified}\` ..."` message shape verbatim (four-space indent included — the
summary line formatting depends on it). **Differences the plan must state:**
- The predicate is `_field_annotation_is_untyped_mapping`, NOT `_annotation_mentions_any` (D-01b).
  Narrow: `dict[str, Any]` and bare `Any` only, `Optional` stripped first (A2/F-9). `list[Any]`
  must NOT match, or market-data's `CalendarConfig.warnings` reddens (out of scope).
- An `AnnAssign` with no annotation is impossible, so the "no return annotation" arm has no
  field analogue — drop it rather than inventing an equivalent.

**Exemption pattern — and why it must NOT extend `_is_exempt`** (`:390-403`):
```python
def _is_exempt(name: str) -> str | None:
    """Return the DT-06 exemption reason for a member name, or ``None``.

    Attribution is by the **simple** member name, never the qualified
    ``Class.member`` form, ...
    """
    if name.startswith("__") and name.endswith("__"):
        return "dunder"
    if name.startswith("_"):
        return "private-helper"
    if name == "to_dict":
        return "serialize-out"
    return None
```
D-01c's `UnknownFrame.raw` exemption is **class+field qualified**. Adding `raw` here would exempt
every member named `raw` in all six packages. Use a separate module-level constant keyed on the
qualified name (e.g. `_FIELD_EXEMPTIONS: dict[str, str] = {"UnknownFrame.raw": "ws-catch-all"}`)
consulted by `_adjudicate_field` before `_is_exempt`, with the reason string flowing into the same
`exempted_by_reason` counter so the RED fixture can assert it by name.

**Ratchet discipline** (`:116-119`, quoted in CONTEXT "Established Patterns"): "A red gate is
never resolved by weakening the gate." If the field predicate reddens anything outside matriz,
narrow the predicate — do not add exemptions.

---

### `packages/matriz-client/src/matriz_client/models.py` — new leaf classes (model, transform)

**Analog:** `packages/market-data-client/src/market_data_client/models.py:272-308`

**Class shape + provenance docstring pattern** (`market_data_client/models.py:272-289`):
```python
@dataclass(frozen=True, slots=True)
class BookLevel(SafeModel):
    """One price level inside an order-book entry (``BI`` / ``OF``).

    Live-capture provenance: field set taken verbatim from
    ``.planning/verification/schemas/market-data-client/get-market-data.json``,
    captured 2026-07-31 against ``market-data-develop``. Not from the OpenAPI and
    not from a mock.

    ``price`` is declared ``float`` although the capture shows ``int`` on the
    wire: ``_decode.walk_field``'s ``float`` arm widens ``int`` to ``float``
    BEFORE consulting ``scalar_passthrough``, so the widening is silent and
    fabricates no divergence (36-RESEARCH F-3). ``size`` stays ``int`` and is
    not widened.
    """

    price: float | None = None
    size: int | None = None
```

**Two mandatory deviations from this analog:**
1. **Decorator:** matriz uses `@dataclass(frozen=True)` **without** `slots=True`
   (see every class at `matriz_client/models.py:281-528`). Match the local file, not the
   Phase 36 source.
2. **Base class name:** matriz's base is `_SafeModel` (private, `models.py:205`), market-data's is
   `SafeModel`. Use `_SafeModel`.

The `int`→`float` widening paragraph above is directly reusable for `TickPriceRange.lowerLimit`
(F-5 / A4) — reuse the *reasoning*, re-cite matriz's own baseline file.

**Three provenance classes, three docstring forms.** D-04a introduces a third class beyond the
analog's two. The plan must use exactly one of:
- `baseline` (live capture committed) — for `TickPriceRange`, citing
  `.planning/verification/schemas/matriz-client/get-instrument-detail.json`, captured 2026-06-10
  against `api.remarkets.primary.com.ar`. Copy the analog's wording verbatim with those
  substitutions.
- `vendor-documented, unmeasured` — for the `report` / `detailedAccountReports` inner models.
  Suggested form (37-RESEARCH F-14): "Vendor-documented provenance, UNMEASURED: field set taken
  from `packages/matriz-client/documentation/Primary-API.md:<range>`. No live capture exists —
  `matriz-client` is blocked from live runs by D-MATZ-33 (`LIVE-MATZ-33`). This roster has never
  been observed on the wire; undeclared keys arrive as non-fatal `extra` divergences."
- `capture` — unavailable this phase.

**Closed-roster + extra-divergence disclosure pattern** (`market_data_client/models.py:318-352`):
the `MarketDataEntries` docstring records the *cost* of closing a roster (an undeclared key is
DISCARDED) and names the artifact where detection lands. D-07 reuses this: the new
`report`/`detailedAccountReports` inner models must carry an equivalent paragraph pointing at
`.planning/verification/matriz-client-findings.md`. Copy the **form**, never the content.

**Field-shape constraint from `_perturb`** (Pitfall 5): keep every new field to
`float | None` / `int | None` / `str | None` / a nested `_SafeModel`. Nothing else is handled by
`test_null_object.py::_perturb`.

**Container-depth asymmetry (F-7 — do not flatten):**
| Field | Container | Levels of open keys |
|-------|-----------|---------------------|
| `InstrumentDetail.tickPriceRanges` | `dict[str, TickPriceRange]` | 1 |
| `DetailedPosition.report` | `dict[str, dict[str, <minimal>]]` | 2 (`contractType` → `symbol`) |
| `AccountReport.detailedAccountReports` | `dict[str, <minimal>]` | 1 |
| `AccountReport.portfolio` | `float \| None` | 0 — leaves the mapping axis entirely (D-02) |

---

### `packages/matriz-client/src/matriz_client/models.py` — alias properties (model, transform)

**Analog:** `packages/market-data-client/src/market_data_client/models.py:381-409` — verbatim
copyable (F-14).

**Pattern** (copy all six, changing only the return type to matriz's class names):
```python
    @property
    def bids(self) -> list[BookLevel]:
        """Human-facing alias over the wire-named field ``BI`` (D-03)."""
        return self.BI

    @property
    def last(self) -> EntryValue:
        """Human-facing alias over the wire-named field ``LA`` (D-03)."""
        return self.LA
```
One-line docstring, single `return`, no transformation, no cache. Re-cite matriz's own decision
id (`D-16` / NOBJ-MTZ-02) rather than market-data's `D-03`.

**Target class:** `MarketDataSnapshot` (`matriz_client/models.py:418-441`) — the ONE class that
serves both the REST return type and `MarketDataFrame.marketData` (F-12). Alias→field map:

| Alias | Field | matriz return type |
|-------|-------|--------------------|
| `bids` | `BI` | `list[MarketDataLevel]` |
| `offers` | `OF` | `list[MarketDataLevel]` |
| `last` | `LA` | `MarketDataEntryValue` |
| `settlement` | `SE` | `MarketDataEntryValue` |
| `close` | `CL` | `MarketDataEntryValue` |
| `open_interest` | `OI` | `MarketDataEntryValue` |

`OP` is a bare `float` and is deliberately **not** aliased (matches the analog's exclusion of
`OP`/`HI`/`LO`/`TV`). matriz's extra scalars `IV`/`EV`/`NV`/`ACP` get no aliases either.

---

### `packages/matriz-client/src/matriz_client/models.py` — mapping axis (utility, transform)

**Analog:** itself, `matriz_client/models.py:99-197`. This is the one genuinely new control flow
in the phase (F-8) — there is no external analog for the recursion.

**Current state (the thing D-06 updates)** — bodies at `:139-142` and `:161-169`:
```python
def _mapping_value(value: Any, *, path: str, model: str, sink: _decode.DecodeScope) -> Any:
    if isinstance(value, dict):
        return value                 # ← values NOT decoded; raw dicts reach the caller
    sink(model, path, "missing" if value is None else "type", "dict", type(value).__name__)
    return {}


def _apply_mapping_policy(cls, kwargs, *, sink) -> None:
    target = cast(Any, cls)
    hints = _decode.hints_for(target)
    model = cls.__name__
    for f in fields(target):
        hint = hints[f.name]
        if _is_mapping(hint):
            kwargs[f.name] = _mapping_value(
                kwargs[f.name], path=f".{f.name}", model=model, sink=sink
            )
```

**Patterns to preserve while rewriting:**
- `_is_mapping` (`:94-96`) already strips `Optional` — reuse it, do not re-derive.
- `cast(Any, cls)` before `_decode.hints_for` — the file's documented mypy-strict discipline
  (`:159-161`), no `type: ignore`.
- The sink signature `sink(model, path, kind, expected, actual)` and the
  `"missing" if value is None else "type"` discrimination — the reporting contract stays identical.
- Path composition: `f".{f.name}"` at the top level; extend with the key for nested values
  (e.g. `f"{path}.{key}"`) so divergence paths stay readable.
- **Route values through `_decode.walk_field`, never `Model.from_api`** — the "Don't Hand-Roll"
  row: `from_api` resolves its own sink via `current_sink()` and leaves the surrounding scope,
  breaking dedupe lock 5 (`_decode.py:459-506` documents the trap).
- Carry the existing docstring's Phase 29 CR-03 / Phase 36 WR-03 history forward (`:115-133`) —
  including the "do not re-create a copy in market-data" instruction. Rewrite, do not drop.

**Pinned call site** (F-17, `models.py:172-197`): `_convert(tp, value)` must keep its reversed
`(tp, value)` argument order and must still answer `{}` for `_convert(dict[str, Any], None)`.
Derive the element hint from `get_args(tp)` inside `_convert`, defaulting to `Any` when absent.
Pinned by `test_decode.py:921-925` and `:927-933`.

**Do NOT add a `dict` branch to `_decode.py`** — `check_decode_intactness.py` Check A hashes all
five copies. `models.py` itself is unconstrained by that gate (F-18).

---

### `packages/matriz-client/src/matriz_client/_core.py` — risk parsers (service, request-response)

**Analog:** `matriz_client/_core.py:884-889` — the sibling endpoint in the same file that already
does it right.

**Reference implementation** (`_core.py:884-889`):
```python
@_decode._response_parser
def parse_get_positions_response(resp: httpx.Response, account_name: str) -> list[Position]:
    """Parse envelope ``{positions: [...]}`` → ``list[Position]``."""
    path = f"/rest/risk/position/getPositions/{account_name}"
    data = parse_envelope_response(resp, path)
    return [Position.from_api(p) for p in unwrap(data, "positions", path)]
```

**Sites to change** (`:911-918` and `:940-945`), currently:
```python
@_decode._response_parser
def parse_get_detailed_positions_response(
    resp: httpx.Response, account_name: str
) -> DetailedPosition:
    """Parse risk payload raíz (NO envelope key, D-07) → ``DetailedPosition``."""
    path = f"/rest/risk/detailedPosition/{account_name}"
    raw = _parse_risk_response(resp, path)
    return DetailedPosition.from_api(raw)
```
Target shape: `parse_envelope_response(resp, path)` + `unwrap(data, "detailedPosition", path)`
(and `"accountData"` for the account-report twin), preserving the `@_decode._response_parser`
decorator and the `path` local.

**Error-handling helper to reuse, not hand-roll** (`_core.py:224-238`):
```python
def unwrap(data: dict[str, Any], key: str, endpoint: str) -> Any:
    """Return ``data[key]`` or raise ``PrimaryAPIError`` if missing. ..."""
    if key not in data:
        raise PrimaryAPIError(
            status="ERROR",
            description=f"missing envelope key '{key}' in response from {endpoint}",
            message=None,
        )
    return data[key]
```

**Docstring/comment corrections that are part of the change** (not optional): the
`"NO envelope key, D-07"` claim appears at `_core.py:279` (`_parse_risk_response` docstring),
`:898` and `:927` (the two `build_*` docstrings), and `:915` / `:942` (the two parser docstrings).
All five are falsified by the vendor doc — correct the prose, not just the code.

**Single site, not mirrored** (F-4): `client.py:679,685` and `aio.py:713,718` both delegate to
these `_core` functions. A mirrored sync/async task is a no-op.

**Optional simplification flagged by research (Open Question 3):** once the `unwrap` lands,
`_parse_risk_response` (`:278-301`) becomes byte-identical to `parse_envelope_response`
(`:241-275`) and has only these two callers. Folding it away is a clean win but is explicitly a
nice-to-have, not a requirement.

**Behaviour change to declare, not discover** (Pitfall 2): `unwrap` raises on a missing key, so a
flat body now raises `PrimaryAPIError` instead of silently decoding to all-defaults. Existing
flat-shaped fixtures must be updated, and the raise must get its own test.

---

### `packages/matriz-client/tests/test_surface_types_red.py` (test, batch) — NEW

**Analog:** `packages/iol-client/tests/test_surface_types_red.py` — mirror the file, copy the
helper (research Open Question 1: a shared test util would be the repo's first cross-package test
dependency; do not create one).

**Import + seam pattern** (`:51-63`):
```python
from __future__ import annotations

from pathlib import Path

import pytest
from tools.check_surface_types import CheckFailure, check_surface_types, scan_surface_types

# Derived independently of the gate's own ``REPO_ROOT``: this module asserts
# *about* the gate, so it must not borrow the constant it is checking.
_REPO_ROOT = Path(__file__).resolve().parents[3]

_UNTYPED_MAPPING_RETURN = "dict[str, Any]"
```

**Synthetic-package helper** (`:65-83`, copy verbatim):
```python
def _write_fake_package(
    root: Path,
    *,
    init_source: str,
    client_source: str,
    extra_modules: dict[str, str] | None = None,
) -> None:
    """Materialise ``<root>/packages/fake-client/src/fake_client/`` on disk. ..."""
    pkg = root / "packages" / "fake-client" / "src" / "fake_client"
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "__init__.py").write_text(init_source, encoding="utf-8")
    (pkg / "client.py").write_text(client_source, encoding="utf-8")
    for name, source in (extra_modules or {}).items():
        (pkg / f"{name}.py").write_text(source, encoding="utf-8")
```

**Lower-bound (non-vacuity) case pattern** (`:127-150`) — adapt from a method return to a
dataclass **field**:
```python
def test_regression_inside_an_exported_class_is_caught(tmp_path: Path) -> None:
    """D-03 in executable form: methods of exported classes are in scope. ..."""
    _write_fake_package(
        tmp_path,
        init_source="from fake_client.client import Client\n\n__all__ = ['Client']\n",
        client_source=(
            "from typing import Any\n"
            "\n"
            "\n"
            "class Client:\n"
            f"    def get_thing(self) -> {_UNTYPED_MAPPING_RETURN}:\n"
            "        return {}\n"
        ),
    )

    with pytest.raises(CheckFailure, match=r"Client\.get_thing"):
        check_surface_types(root=tmp_path)
```
matriz variant: an exported `@dataclass` whose body is `payload: dict[str, Any]`, asserted with
`match=r"Thing\.payload"`.

**Exemption-reachability case pattern** (`:153-192`) — the shape D-01c needs, proving the
exemption absorbs a genuine *hit* rather than being dead code:
```python
    result = scan_surface_types(tmp_path)

    assert result.violations == ()
    assert result.definitions == 4
    assert result.exempted == 3
    assert dict(result.exempted_by_reason) == {
        "dunder": 1,
        "private-helper": 1,
        "serialize-out": 1,
    }
```
matriz variant: a synthetic exported `class UnknownFrame` with `raw: dict[str, Any]` must NOT
redden, and the new reason must appear by name in `exempted_by_reason`.

**Upper-bound case pattern** (`:86-102`) — floors, never equalities, so a new export cannot
falsely redden:
```python
    result = scan_surface_types(_REPO_ROOT)
    assert result.violations == ()
    assert result.packages >= 6
    assert result.definitions >= 300
    assert result.exempted >= 20
```

**Anti-patterns the analog's module docstring already rules out** (`:1-49`, worth re-stating in
the matriz file): no mypy/CLI subprocess; no fake package committed under `packages/` (it would
enter `check_decode_intactness` Check D and owe `check_uniform_structure` a `models.py`+`types.py`).

---

### `packages/matriz-client/tests/test_core.py` — envelope regressions (test, request-response)

**Analog:** the same file's existing envelope and unwrap cases.

**Parser happy-path pattern** (`test_core.py:98-103`):
```python
def test_parse_envelope_response_returns_dict_on_success() -> None:
    """Happy path: status OK + body dict → retorna el dict."""
    resp = _make_response(json_body={"status": "OK", "segments": [{"x": 1}]})
    data = _core.parse_envelope_response(resp, "/rest/segment/all")
    assert data["status"] == "OK"
    assert data["segments"] == [{"x": 1}]
```

**Missing-key raise pattern** (`:172-176`) — the exact shape the new flat-body regression needs:
```python
def test_unwrap_raises_on_missing_key() -> None:
    """Envelope key ausente → ``PrimaryAPIError`` tipado (D-MATZ-9)."""
    with pytest.raises(PrimaryAPIError) as exc_info:
        _core.unwrap({"some_other_key": []}, "segments", "/rest/segment/all")
    assert "missing envelope key 'segments'" in (exc_info.value.description or "")
```

Two new cases per parser: (a) the **enveloped** body from `Primary-API.md:1701-1703` /
`:1817-1819` populates the declared fields; (b) a **flat** body raises `PrimaryAPIError` with
`"missing envelope key 'detailedPosition'"` / `'accountData'`. Use the file's local
`_make_response(json_body=...)` helper, not raw `httpx.Response` construction.

The existing `test_parse_get_detailed_positions_response_returns_model` (`:327-328`) encodes the
flat shape in both its body and its docstring — it is a fixture to **update**, and its docstring
claim "(NO envelope unwrap)" must be corrected with it.

---

### `packages/matriz-client/tests/test_null_object.py` — alias assertions (test, transform)

**Analog:** `packages/market-data-client/tests/test_market_data_chain.py:479-504`

**Disjointness + roster-exactness pattern** (`:479-492`):
```python
def test_the_six_aliases_and_the_ten_wire_fields_are_disjoint() -> None:
    """No alias may collide with a declared slot of a ``frozen=True, slots=True`` class. ..."""
    field_names = {f.name for f in dataclasses.fields(MarketDataEntries)}
    alias_names = {"bids", "offers", "last", "settlement", "close", "open_interest"}

    assert field_names == {"BI", "CL", "HI", "LA", "LO", "OF", "OI", "OP", "SE", "TV"}
    assert field_names & alias_names == set()
    assert MarketDataEntries.empty() is not None
```
matriz variant: the wire roster is the fourteen of `MarketDataSnapshot`
(`BI OF LA SE OI CL OP HI LO TV IV EV NV ACP`). The slots rationale does not apply (matriz has no
`slots=True`), so restate the reason as name-shadowing rather than slot collision.

**Identity pattern** (`:495-504`) — `is`, not `==`, proving a plain read-only view:
```python
def test_each_alias_returns_the_identical_object_the_wire_field_returns() -> None:
    """The aliases are plain read-only views — no copy, no cache, no transformation."""
    entries = MarketDataEntries.from_api(_WIRE_REAL["market_data"])

    assert entries.bids is entries.BI
    ...
```
matriz variant additionally exercises a **WS-parsed** instance (`MarketDataFrame.from_api(...)
.marketData`) alongside the REST-parsed one — that is SC-3's direct evidence (F-12).

**Do NOT rewrite the invisibility proof.** `test_property_aliases_are_invisible_to_get_type_hints`
(`test_null_object.py:292-311`) and
`test_adding_a_property_alias_does_not_change_the_divergence_count` (`:314-331`), with their
`_AliasShaped`/`_AliasFree` fixtures (`:195-213`), already prove the invariant generically —
their docstring literally says "The exact shape phases 36-38 introduce". This phase only applies it.

**Roster floor** (`:221-229`) — hygiene, not a blocker (F-13):
```python
    assert len(_safemodel_classes()) >= 17
```
It is `>=`, so it cannot break. Bump it to the new count and update the docstring's rationale;
do not sequence anything behind it. The parametrized roster tests (`:232-253`) auto-extend to the
new classes — each must satisfy falsy-when-empty, truthy-when-perturbed, silent-`empty()`.

---

### `.planning/verification/matriz-client-findings.md` (doc / ledger, batch)

**Analog:** itself. The file already carries an `## Index` table with `| ID | Class | Surface |
Status |` and a `## Detalle por hallazgo` section per row, inside a `<!-- BEGIN AUTO-GENERATED -->`
region. Existing vocabulary: classes `SHAPE, AUTH, ERROR-MAP, PARAM, SYNC-ASYNC-DRIFT, NO-DATA,
ANTI-BOT`; states `OPEN -> CONFIRMED -> FIXED` plus terminal `EXPECTED` / `NO-FIX`. Rows for
declared-but-unobserved payloads use `Class: SHAPE`, `Status: NO-FIX` or `EXPECTED` — the same
disposition F-01..F-10 already use. **Do not invent a new provenance record format** (D-04b); the
programmatic writer is at `main_matriz.py:398`.

## Shared Patterns

### Provenance docstring (applies to every new model class)
**Source:** `packages/market-data-client/src/market_data_client/models.py:276-279`
```python
    Live-capture provenance: field set taken verbatim from
    ``.planning/verification/schemas/market-data-client/get-market-data.json``,
    captured 2026-07-31 against ``market-data-develop``. Not from the OpenAPI and
    not from a mock.
```
Every new class gets exactly one of the three labels (`baseline` / `vendor-documented, unmeasured`
/ `capture`), citing path + line range or filename + capture date. Never present vendor doc as a
capture (SC-1).

### matriz dataclass house style (applies to every new model class)
**Source:** `packages/matriz-client/src/matriz_client/models.py:400-414`
```python
@dataclass(frozen=True)
class MarketDataLevel(_SafeModel):
    """Price level inside an order-book entry (``BI`` / ``OF``)."""

    price: float | None = None
    size: int | None = None
```
`frozen=True` with **no** `slots=True`; base `_SafeModel`; wire-verbatim camelCase field names;
`| None = None` leaves and `field(default_factory=X.empty)` for nested models; a `§`-referenced
one-line summary. `from_api`/`empty`/`__bool__` are inherited — never hand-write them (the sole
exception, `UnknownFrame`, is documented at `:527-545` and stays untouched).

### Divergence reporting via the shared sink (applies to models.py axis work)
**Source:** `packages/matriz-client/src/matriz_client/models.py:141`
```python
    sink(model, path, "missing" if value is None else "type", "dict", type(value).__name__)
```
Same five-argument signature, same `missing`/`type` discrimination, same `SILENT_SINK` swap under
a non-dict payload (`models.py:246-248`, lock 8). Any new axis code emits through the sink it was
handed — never through `current_sink()` (dedupe lock 5).

### Gate ratchet discipline (applies to `tools/` work)
**Source:** `tools/check_surface_types.py:116-119`
A red gate is never resolved by weakening the gate. If the field predicate reddens something out
of scope, narrow the predicate (D-01b) — do not widen the exemption set and do not edit the
foreign package.

## No Analog Found

None. Every file has a concrete in-repo analog. The single piece of genuinely new logic — the
**recursion** inside `_mapping_value` for `dict[str, dict[str, Model]]` (F-8) — has no analog
anywhere in the repo and should carry its own task and its own tests; its surrounding contract
(signature style, sink usage, `_is_mapping` reuse, `_convert` shim compatibility) is fully
constrained by the existing single-level version it replaces.

## Metadata

**Analog search scope:** `packages/matriz-client/src/`, `packages/matriz-client/tests/`,
`packages/market-data-client/src/`, `packages/market-data-client/tests/`,
`packages/iol-client/tests/`, `tools/`, `.planning/verification/`
**Files read for excerpts:** 9
**Pattern extraction date:** 2026-08-29
