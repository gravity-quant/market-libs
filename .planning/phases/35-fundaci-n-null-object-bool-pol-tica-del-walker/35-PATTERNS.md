# Phase 35: Fundación Null Object — `__bool__` + política del walker - Pattern Map

**Mapped:** 2026-08-28
**Files analyzed:** 18 (4 models.py + 5 _decode.py + 1 gate + 6 test files + 1 planning artefact + N new test files)
**Analogs found:** 17 / 18 (only the D-17 census artefact has no code analog)

> **Governing constraint for this phase:** three of the four "roles" below are
> *verbatim-replicated* files. The analog is not merely a style reference — for
> `_decode.py` the analog is the **byte-identical sibling copy**, and any deviation
> reddens `tools/check_decode_intactness.py` Check A/B. Copy exactly.

---

## File Classification

| File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `packages/higyrus-client/src/higyrus_client/models.py` (+`__bool__`, +`empty()`) | model (base class) | transform | `matriz_client/models.py:238-250` (`_SafeModel.empty`) | exact (reference impl) |
| `packages/iol-client/src/iol_client/models.py` (+`__bool__`, +`empty()`) | model (base class) | transform | `higyrus_client/models.py:52-87` (`SafeModel`, sibling twin) | exact |
| `packages/market-data-client/src/market_data_client/models.py` (+`__bool__`, +`empty()`) | model (base class) | transform | `matriz_client/models.py:238-250` (mapping-pass form) | exact |
| `packages/matriz-client/src/matriz_client/models.py` (+`__bool__` on `_SafeModel`, +`__bool__` on `UnknownFrame`) | model (base class + union member) | transform | itself (`empty()` already present, `:238-250`, `:528-530`) | exact |
| `packages/{ambito,higyrus,iol,market-data,matriz}/…/_decode.py` ×5 (EDIT 1 + EDIT 2) | utility (canonical walker) | transform / event-driven (sink) | each other — byte-verbatim under 8 normalization rules | exact (mandated) |
| `tools/check_decode_intactness.py:222` (`CANONICAL_DIGEST`) | config (gate constant) | batch | itself — value is recomputed, never authored | exact |
| `packages/*/tests/test_decode.py` ×5 (invert 2 assertions each) | test | request-response fixtures | `higyrus/tests/test_decode.py:215-222`, `:1131-1146` | exact (per-copy, NOT verbatim) |
| `packages/market-data-client/tests/test_core.py:1052-1059` (11th assertion) | test | CRUD (real model) | `higyrus/tests/test_decode.py:1131` (same species) | role-match |
| NEW: per-package truthiness/enumeration tests ×6 | test | batch (introspection) | `verification/safemodel_diff.py:49-62` (duck-typed roster) | role-match |
| NEW: property-invisibility test | test | transform | `higyrus/tests/test_decode.py` module-local fixtures `:81-112` | exact |
| NEW: `35-RETIRED-TRIPLES.md` (D-17) | doc artefact | — | `29-SIZING.md:302-304` | no analog |

---

## Pattern Assignments

### A. `models.py` ×4 — base gains `__bool__` + `empty()`

**Analog (reference implementation):** `packages/matriz-client/src/matriz_client/models.py:238-250`

```python
    @classmethod
    def empty(cls) -> Self:
        """Build an all-defaults instance. Emits nothing (T-29-33).

        ``empty()`` does not decode wire data: it is the nested-model default,
        the ``default_factory`` of several shipped fields, and the shape a
        non-dict payload converges on. Routing it through an emitting sink
        would produce one spurious ``missing`` record per field on every one of
        those calls and would break the terminal-``non_dict`` rule.
        """
        kwargs = _decode.walk_model(cls, {}, policy=_decode.POLICY, sink=_decode.SILENT_SINK)
        _apply_mapping_policy(cls, kwargs, sink=_decode.SILENT_SINK)
        return cls(**kwargs)
```

Note the docstring shape to imitate: **one-line summary + a paragraph justifying the
`SILENT_SINK`**, citing the lock/test ID (`T-29-33`). Every method in these four bases
follows that convention.

**Sibling base to place the new methods next to** — `higyrus_client/models.py:52-87`
(iol's `:65-94` is the byte-twin except for the `to_dict` docstring):

```python
class SafeModel:
    """Base class for Higyrus API response models.

    Subclasses must be frozen dataclasses. Construct instances via
    :meth:`from_api` to tolerate partial or missing fields.
    """

    @classmethod
    def from_api(cls, payload: Any) -> Self:
        """Build an instance from an API payload, with safe defaults."""
        kwargs = _decode.walk_model(
            cls, payload, policy=_decode.POLICY, sink=_decode.current_sink()
        )
        return cls(**kwargs)

    def to_dict(self) -> dict[str, Any]:
        ...
        wire: dict[str, Any] = dataclasses.asdict(cast(Any, self))
        return wire
```

**Placement rule derived from the analogs:** `from_api` first, then the new
`empty()` (matriz orders it right after `from_api`), then `__bool__`, then `to_dict`.
matriz has no `to_dict`; there `empty()` is already last and `__bool__` goes after it.

**Import block already in place — nothing to add** (`higyrus/models.py:43-49`;
iol `:56-62` identical modulo package name):

```python
from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import Any, Self, cast

from higyrus_client import _decode
```

`Self` is already imported in all four — `empty() -> Self` needs no new import.
matriz additionally has `ClassVar` for its `__dataclass_fields__` declaration
(`models.py:196`).

**mapping-pass form (market-data)** — the analog for the second `empty()` shape is
`market_data_client/models.py:211-223`, which shows exactly the two-line body plus
the Lock-8 comment that `empty()` must simplify (in `empty()` both sinks are
unconditionally `SILENT_SINK`, so the `isinstance(payload, dict)` ternary disappears):

```python
    @classmethod
    def from_api(cls, payload: Any) -> Self:
        """Build an instance from an API payload, with safe defaults."""
        sink = _decode.current_sink()
        kwargs = _decode.walk_model(cls, payload, policy=_decode.POLICY, sink=sink)
        # Lock 8: under a non-dict payload the walker already swapped its field
        # sink to ``SILENT_SINK``, so the mapping pass must be silent too — ...
        _apply_mapping_policy(
            cls, kwargs, sink=sink if isinstance(payload, dict) else _decode.SILENT_SINK
        )
        return cls(**kwargs)
```

**`UnknownFrame` (D-08)** — analog is the class itself, `matriz_client/models.py:504-530`.
It is `@dataclass(frozen=True)`, does **not** inherit `_SafeModel`, and already carries the
duck-typed pair; the new `__bool__` goes after `empty()`:

```python
    @classmethod
    def from_api(cls, data: Any) -> Self:
        if not isinstance(data, dict):
            return cls()
        return cls(type=data.get("type"), raw=dict(data))

    @classmethod
    def empty(cls) -> Self:
        return cls()
```

Note this class's methods are **undocstringed** (the class docstring carries the
contract) — the hand-written `__bool__` should match that local convention rather than
the base's verbose one, and the class docstring's last line ("Both methods below stay
hand-written and untouched") must be updated to say *three*.

**Empty-by-decision packages (D-05)** — the pattern to *respect, not extend*:
`ambito_financiero_client/models.py` and `wallets_client/models.py` are docstring-only
modules ending in `__all__: list[str] = []`, each explaining **why** there is no base
(ambito: dormant walker, dead weight on a wheel; wallets: no `_decode.py`, a copied
`SafeModel` would `ImportError`). Any Phase-35 documentation of "empty roster by
enumeration" belongs in *that* docstring style, appended to the existing prose.

---

### B. `_decode.py` ×5 — the two surgical edits

**Analog:** the four sibling copies of the same file. Verbatim is mandatory; only the
package-name token differs (Rule 6 of the gate normalizes it).

**Current EDIT 1 site** — `higyrus_client/_decode.py:442-452` (line numbers per package
in RESEARCH §Pattern 1; ámbito is +7):

```python
    if origin is list:
        if not isinstance(value, list):
            sink(model, path, _kind_of(value), _name_of(hint), type(value).__name__)
            return []
        inner = args[0] if args else Any
        # Lock 5: the element path segment carries no index, so identical
        # divergences across elements collapse under the dedupe triple.
        return [
            walk_field(item, inner, path=f"{path}[]", model=model, policy=policy, sink=sink)
            for item in value
        ]
```

**Current EDIT 2 site** — `higyrus_client/_decode.py:454-487`. The 24-line WR-02
comment block (`:455-481`) is the thing to rewrite, and it is **hashed**, so the rewrite
is byte-identical across the five by construction. The tail:

```python
        if value is None:
            sink(model, path, "missing", _name_of(hint), "NoneType")
            return hint(**walk_model(hint, {}, path=path, policy=policy, sink=SILENT_SINK))
        # A genuinely non-dict (not ``None``) nested payload keeps the ``non_dict``
        # kind and the nested-model attribution, which is correct for that case.
        return hint(**walk_model(hint, value, path=path, policy=policy, sink=sink))
```

**Early-return that makes the edit safe** (`:432-440`) — quoted here because the new
comment must reference it as the reason "everything below is non-optional by construction":

```python
    # Optional[T] / T | None: explicit opt-in to nullable — a missing value
    # stays None instead of collapsing to a typed zero, and is NOT a divergence.
    if origin is Union or origin is UnionType:
        if value is None:
            return None
```

**Comment-style pattern to copy:** every non-obvious walker decision carries a
`# Lock N:` or `# Phase 29 code review, WR-0X:` prefix and states *what breaks if
reverted*. The Phase 35 comment should follow that form (e.g. `# Phase 35, NOBJ-02:`).

**Gate constant** — `tools/check_decode_intactness.py:210-222`. The comment above
`CANONICAL_DIGEST` already prescribes the procedure ("Bump it ONLY together with a
reviewed change… run this script: the failure message prints the digest it computed").
Follow it literally; do not author a value.

---

### C. `test_decode.py` ×5 — the 10 inverted assertions

**Analog & harness (higyrus, `tests/test_decode.py`):**

Module-local fixtures (`:81-112`) — the shape new fixtures must copy
(`@dataclass(frozen=True, slots=True)`, one-line docstring, subclasses the package base):

```python
@dataclass(frozen=True, slots=True)
class _Leaf(SafeModel):
    """Nested leaf used to exercise list-element path collapse."""

    nombre: str
    dias: int


@dataclass(frozen=True, slots=True)
class _Nested(SafeModel):
    """A model carrying a ``list[Model]`` field."""

    titulo: str
    hojas: list[_Leaf]
```

Helpers (`:119-141`) — new walker tests must go through `_walk`, never `from_api`
(higyrus/iol/market-data style):

```python
def _divergences(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    """Every divergence record captured so far, in emission order."""
    return [r for r in caplog.records if r.getMessage() == _MESSAGE]


def _walk(cls, payload, caplog, *, sink: DecodeScope | None = None):
    """Walk ``payload`` into ``cls`` with a fresh scope, returning instance + records."""
    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="higyrus_client"):
        kwargs = walk_model(
            cls, payload, policy=POLICY, sink=sink if sink is not None else DecodeScope()
        )
    return cls(**kwargs), _divergences(caplog)


def _tuples(records: list[logging.LogRecord]) -> list[tuple[str, str]]:
    return [(r.field_path, r.divergence) for r in records]  # type: ignore[attr-defined]
```

The autouse `_pristine_decode_context` fixture (`:42-63`) already isolates scope —
new tests in these modules inherit it for free and must not re-implement it.

**Assertion 1 to invert** — `higyrus/tests/test_decode.py:215-222`:

```python
def test_missing_list_field_returns_empty_list_and_reports(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A ``list[X]`` field absent from the payload stays ``[]`` and reports once."""
    obj, records = _walk(_Nested, {"titulo": "t"}, caplog)

    assert obj.hojas == []
    assert _tuples(records) == [(".hojas", "missing")]   # ← becomes == []
```

The **name and docstring both assert the old disposition** and must be rewritten
alongside the assertion, in all five copies.

**Assertion 2 to invert** — `higyrus/tests/test_decode.py:1131-1146`:

```python
    instance, records = _walk(_CarriesNested, {"titulo": "t"}, caplog)

    assert instance == _CarriesNested("t", _Leaf("", 0))          # ← VALUE unchanged
    triples = [(r.model, r.field_path, r.divergence) for r in records]  # type: ignore[attr-defined]
    assert triples == [("_CarriesNested", ".hoja", "missing")]    # ← becomes == []
```

**matriz's copy is NOT the same code** (`matriz/tests/test_decode.py:1234-1252`) —
it drives `from_api` directly, uses `in` rather than `==`, and carries a second
negative assertion. Edit it by reading it, not by pattern substitution:

```python
    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="matriz_client"):
        instance = _Nested.from_api({"tag": "t"})

    assert instance.leaf == _Leaf.empty()
    triples = [(r.model, r.field_path, r.divergence) for r in _divergences(caplog)]  # type: ignore[attr-defined]
    assert ("_Nested", ".leaf", "missing") in triples
    assert not [t for t in triples if t[2] == "non_dict"]
```

**The wrong-type half that must stay green untouched** — the model to imitate when
writing the *new* wrong-type-on-list test (`higyrus:1149-1156`):

```python
def test_non_dict_nested_payload_keeps_the_nested_attribution(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """WR-02: only ``None`` reclassifies — a real non-dict is still ``non_dict``."""
    _, records = _walk(_CarriesNested, {"titulo": "t", "hoja": "garbage"}, caplog)

    triples = [(r.model, r.field_path, r.divergence) for r in records]  # type: ignore[attr-defined]
    assert triples == [("_Leaf", ".hoja", "non_dict")]
```

The new list-site test is the exact structural sibling: payload
`{"titulo": "t", "hojas": "garbage"}`, expecting `[("_Nested", ".hojas", "type")]`.

---

### D. `test_core.py:1052` — the 11th assertion (market-data)

**Analog:** the test immediately above it, `test_health_from_api_populates_the_nested_auth_model`
(`:1041-1048`), plus the `_from_api` helper + `pristine_decode_context` fixture idiom
used here (this module drives **shipped models**, not walker fixtures):

```python
@pytest.mark.usefixtures("pristine_decode_context")
def test_health_from_api_missing_auth_yields_zero_valued_nested_model(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A declared non-optional nested model is NEVER ``None`` — it is the zero instance."""
    health, records = _from_api(Health.from_api, caplog, {"status": "ok"})
    assert health.status == "ok"
    assert health.auth == HealthAuth(configured=False, enabled=False, issuer="")   # ← KEEP
    assert [(r.field_path, r.divergence) for r in records] == [(".auth", "missing")]  # ← → []
```

Only the last line moves. The `HealthAuth(...)` equality is the point of NOBJ-02 and
stays byte-identical.

---

### E. NEW enumeration / truthiness tests ×6

**Analog for the roster filter:** `verification/safemodel_diff.py:49-62`

```python
def _is_safemodel_like(cls: Any) -> bool:
    """Duck-typed check: ``cls`` is a SafeModel-like dataclass.

    True iff ``cls`` is a type, is a dataclass, and exposes a callable
    ``from_api`` classmethod. This admits both
    ``higyrus_client.models.SafeModel`` subclasses and
    ``matriz_client.models._SafeModel`` subclasses without importing either
    package (cross-package coupling is forbidden by repo policy).
    """
    return (
        isinstance(cls, type)
        and dataclasses.is_dataclass(cls)
        and callable(getattr(cls, "from_api", None))
    )
```

Copy the **predicate shape and the rationale paragraph**, but the per-package test
imports its own base concretely (`issubclass(obj, models.SafeModel)`) since it is
in-package, and adds the `obj.__module__ == models.__name__` filter that
`safemodel_diff` does not need. The "no shared helper across packages" constraint that
this file documents applies to the new tests: **copy the helper into each package's
tests**, never import cross-package.

**Analog for module docstring + import discipline of a new test module:**
`higyrus/tests/test_decode.py:1-37` — module docstring stating what the suite pins and
why fixtures are module-local, then `from __future__ import annotations`, stdlib,
`pytest`, then absolute package imports.

**Analog for the parametrize/ids idiom:** grep-confirmed convention in the repo is
`@pytest.mark.parametrize(..., ids=lambda c: c.__name__)`; ruff rule `PT` is on, so
parametrize argnames must be a plain string and fixtures must not be requested
positionally.

---

## Shared Patterns

### Verbatim × 5 discipline
**Source:** `tools/check_decode_intactness.py:210-222` (digest doctrine), normalization
rules `:402-469`.
**Apply to:** every byte of the five `_decode.py`.
Function/class docstrings and inline comments **are hashed**; only the module docstring
is stripped (Rule 1). Consequence: put the new-disposition prose inside `walk_field`'s
docstring or an inline comment and the gate enforces uniformity for you.

### Lock-cited comments
**Source:** `_decode.py:447-448`, `:455-481`, `market_data_client/models.py:216-219`.
**Apply to:** every new comment in `_decode.py` and `models.py`.
Form: `# Lock N:` / `# Phase NN code review, WR-0X:` / `# Phase 35, NOBJ-02:` followed
by *what breaks if this line is reverted* — never a restatement of the code.

### mypy-strict discipline for non-dataclass bases
**Source:** `higyrus/models.py:80-87` (`cast(Any, self)` + its justification docstring),
`market_data_client/models.py:190-192` (`target = cast(Any, cls)`).
**Apply to:** `empty()` in all four bases. `cls(**kwargs)` already compiles in `from_api`
today, so `empty()` needs **no new cast and no `type: ignore`** — the precedent is the
adjacent method.

### Divergence-record attribute access in tests
**Source:** `higyrus/tests/test_decode.py:141`, `:1145`.
**Apply to:** every assertion touching a `LogRecord`.
`# type: ignore[attr-defined]` on the comprehension line is the established idiom
(records carry dynamically-attached attrs). Reuse `_tuples` / inline the 3-tuple form.

### Docstring-only "deliberately empty" modules
**Source:** `ambito_financiero_client/models.py`, `wallets_client/models.py`.
**Apply to:** D-05's documentation of the empty roster.
Prose explains the *cost of the uniform-looking alternative* (dead weight / ImportError),
ends with `__all__: list[str] = []`. Do not add a base to make the roster non-empty.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `35-RETIRED-TRIPLES.md` (D-17 census artefact) | doc | — | No prior phase produced a "triples retired by a policy change" ledger. Nearest reference for *format* only: `29-SIZING.md:302-304` (ratified floors with `file:line` citations) — mirror its per-package table + citation style. |

---

## Metadata

**Analog search scope:** `packages/*/src/*/models.py`, `packages/*/src/*/_decode.py`,
`packages/*/tests/test_decode.py`, `packages/market-data-client/tests/test_core.py`,
`tools/`, `verification/`
**Files scanned:** 12 read (targeted ranges), 6 grepped
**Pattern extraction date:** 2026-08-28
