# Phase 31: Endpoints de ops + estructura uniforme - Pattern Map

**Mapped:** 2026-08-23
**Files analyzed:** 22 (7 new modules, 3 new/extended test files, 1 new tools script, 11 modified sources)
**Analogs found:** 21 / 22

Scope drivers: CONTEXT D-01..D-13, RESEARCH § Signature Site Census, § Parser Split Plan,
§ File Layout Census, § Wave 0 Gaps.

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `packages/higyrus-client/src/higyrus_client/models.py` (MOD: `+Health`, `+to_dict`) | model | transform | `packages/iol-client/src/iol_client/models.py:65-94` | exact |
| `packages/market-data-client/src/market_data_client/models.py` (MOD: `+8` models, `+to_dict`) | model | transform | `market_data_client/models.py:608-635` (`CalendarDay`) + `iol_client/models.py:80-93` | exact |
| `packages/higyrus-client/src/higyrus_client/_core.py` (MOD: `parse_get_health_response`) | service (parser) | request-response | `higyrus_client/_core.py:457-472` (`_parse_list_or_raise`) | exact |
| `packages/market-data-client/src/market_data_client/_core.py` (MOD: 2 parsers → 4) | service (parser) | request-response | `market_data_client/_core.py:1066-1080` (`parse_calendar_config_response`) | exact |
| `packages/higyrus-client/src/higyrus_client/{client,aio}.py` (MOD: 4 sites) | controller (shell) | request-response | same files, sibling endpoints (`get_posiciones`) | exact |
| `packages/market-data-client/src/market_data_client/{client,aio}.py` (MOD: 16 sites) | controller (shell) | request-response | `client.py:661-679` (`preview_calendar_config`) | exact |
| `packages/{higyrus,market-data}-client/src/*/__init__.py` (MOD: re-exports) | config (surface) | — | `higyrus_client/__init__.py:33-45,95-105` | exact |
| `packages/{iol,higyrus,market-data,ambito-financiero,wallets}-client/src/*/types.py` (NEW ×5) | config (placeholder) | — | `matriz_client/types.py:1-14` | role-match |
| `packages/{ambito-financiero,wallets}-client/src/*/models.py` (NEW ×2) | config (placeholder) | — | `matriz_client/types.py:1-14` (header only) | role-match |
| `tools/check_uniform_structure.py` (NEW) | utility (CI gate) | batch | `tools/check_decode_intactness.py:625-692` | exact |
| `.github/workflows/ci.yml` (MOD: `lint` step) | config | — | `ci.yml` `decode-intactness` step | exact |
| `packages/market-data-client/tests/test_mutation_gate_ast.py` (NEW) | test (AST guard) | batch | `verification/test_main_market_data_no_gate_bypass.py:41-109` | role-match |
| `packages/market-data-client/tests/test_calendar_write{,_async}.py` (MOD + byte-identical tests) | test | request-response | `test_calendar_write.py:258-272,345-359` | partial |
| `packages/market-data-client/tests/test_{with_options,with_options_async,transport,core,decode}.py` (MOD: re-mock) | test | request-response | same files | exact |
| `packages/higyrus-client/tests/test_{core,client,async_client}.py` (MOD: re-mock) | test | request-response | same files | exact |
| `verification/snapshots/higyrus-client-surface.txt` (REGEN) | golden | — | `verification/snapshots/iol-client-surface.txt` (Phase 30) | exact |
| `main_higyrus.py`, `main_market_data.py` (MOD: `to_dict()` sites) | entry point | file-I/O | `main_iol.py:336` `_capture_raw_wire` | role-match |

---

## Pattern Assignments

### `higyrus_client/models.py` — `SafeModel.to_dict()` + `Health` (model, transform)

**Analog:** `packages/iol-client/src/iol_client/models.py:65-94` (Phase 30 D-08)

**Copy verbatim into BOTH higyrus and market-data `SafeModel`** (C-2: no cross-package import):

```python
    def to_dict(self) -> dict[str, Any]:
        """Re-project the model as the plain wire dict (D-08).

        Escape hatch for the dict -> model break of Phase 30, and the adapter
        the verification harness feeds to ``verification.schema.schema_of``.
        Nested models are flattened to dicts; ``None`` keys are **kept** — a
        response model must reproduce the wire shape, holes included.

        ``cast(Any, self)`` follows ``_decode.py``'s existing mypy-strict
        discipline: :class:`SafeModel` itself is not a dataclass — every
        concrete subclass is — so ``asdict``'s ``DataclassInstance`` overload
        cannot be satisfied by the base's ``self``.
        """
        wire: dict[str, Any] = dataclasses.asdict(cast(Any, self))
        return wire
```

**Imports to add** (`iol_client/models.py:56-62` is the reference header):

```python
from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import Any, Self, cast

from higyrus_client import _decode   # already present; market-data likewise
```

higyrus's `SafeModel` (`models.py:41-54`) and market-data's (`models.py:160-179`) are
**left otherwise untouched** — `to_dict` is appended as a second method on the same class.
market-data's `_apply_mapping_policy` step stays exactly as written.

**Model declaration pattern** — copy `CalendarDay`'s shape, `market_data_client/models.py:608-635`:

```python
@dataclass(frozen=True, slots=True)
class CalendarDay(SafeModel):
    """One entry of the ``days[]`` list inside the ``GET /calendar`` envelope (D-12).

    Reconciled against the real develop wire (LIVE-MUT-01): ... ``open_time`` /
    ``close_time`` are ``str | None`` because the wire sends ``null`` for a fully
    closed day and custom ``HH:MM`` session hours otherwise.

    A plain :class:`SafeModel` subclass built via the inherited ``from_api``: it
    carries NO ``received_at`` (D-05 — reference data is unstamped).
    """

    day: str
    closed: bool
    description: str
    open_time: str | None = None
    close_time: str | None = None
```

Copy exactly this three-part docstring shape for all 9 new models: (1) endpoint + D-ref,
(2) the live-capture provenance sentence naming the committed schema JSON, (3) a
per-`str | None` justification line. Then bare annotations, `str | None` fields last with
`= None`.

**Anti-pattern to avoid** (`models.py:222-265`, `MarketDataSnapshot.from_api`): none of the 9
new models may override `from_api` — `test_decode.py:1239` asserts
`overriding == {"MarketDataSnapshot", "Symbol"}` by equality. Shape carve-outs go in the
**parser**, never in a model override.

---

### `market_data_client/_core.py` — 4 split, decorated parsers (service, request-response)

**Analog (structure + decorator + tolerant fallback):** `market_data_client/_core.py:1066-1080`

```python
@_decode._response_parser
def parse_calendar_config_response(resp: httpx.Response) -> CalendarConfig:
    """Pure: parse ``GET /calendar/config`` → a single ``CalendarConfig`` (D-07).

    The ONE non-collection reference parser: returns a single typed object, NOT a
    list. Uses the ``parse_health_response`` body-consume order but returns a
    tolerant model — an empty/None body collapses to ``CalendarConfig.from_api(None)``
    (the D-07 fallback), never a raise. No ``received_at`` stamp (D-05).
    """
    resp.read()
    raise_for_response(resp)
    if not resp.content:
        return CalendarConfig.from_api(None)
    raw = resp.json()
    return CalendarConfig.from_api(raw)
```

This is the direct template for `parse_add_holidays_response` and
`parse_delete_holiday_response` — it is the in-package precedent RESEARCH G-4 recommends for
resolving the two `return {}` branches into `Model.from_api(None)` (preserving the T-26-13
tolerance on a published mutation).

**Analog (raise-on-non-dict guard the two health parsers must GAIN, D-04):**
`higyrus_client/_core.py:444-453`

```python
    raw = resp.json()
    if not isinstance(raw, dict):
        raise HigyrusAPIError(
            status_code=0,
            errors=[
                {
                    "title": "shape mismatch",
                    "detail": f"expected dict, got {type(raw).__name__}",
                }
            ],
        )
```

Note `type(raw).__name__` and never `repr(raw)` — the T-29-36 rule (types and paths, never a
wire value). market-data's equivalent raises `MarketDataAPIError`, whose constructor shape
differs from higyrus's `errors=[...]` list; check `market_data_client/exceptions.py` and follow
the market-data convention for the message argument.

**Collection-guard analog** for `AddHolidaysResult.days`: `_core.py:1029-1063`
(`parse_calendar_response`) shows the `days` unwrap + double collection guard, though the new
parser builds one envelope model rather than a bare list.

**Ordering invariant:** `resp.read()` then `raise_for_response(resp)` then decode — Phase 7 D-06
(HTTP/2 safety), present in every parser in this file. Never reorder.

**Decorator convention:** write `@_decode._response_parser` with the leading underscore intact
(all 11 existing sites do; `_core.py:51` already imports `_decode`). Never `with
_decode._response_scope():` inline.

**`__all__` update:** `_core.py:95-96` — 2 names become 4.

---

### `higyrus_client/_core.py::parse_get_health_response` (service, request-response)

**Analog:** `higyrus_client/_core.py:457-472` — the sibling that already carries the decorator.

```python
@_decode._response_parser
def _parse_list_or_raise(resp: httpx.Response, model_cls: type[Any]) -> list[Any]:
    """Helper común para parsers que retornan ``list[Model]`` con 204→``[]``."""
    body = _consume_and_check(resp)
    if resp.status_code == 204 or not body:
        return []
    raw = resp.json()
    if not isinstance(raw, list):
        raise HigyrusAPIError(status_code=0, errors=[...])
```

The change to `parse_get_health_response` is exactly three edits, keeping everything else
verbatim: add `@_decode._response_parser`, change the return annotation to `Health`, and turn
the two returns into `Health.from_api(None)` / `Health.from_api(raw)`. The `_consume_and_check`
helper (`_core.py:418-423`), the 204 carve-out, and the exact `title`/`detail` strings are
**pinned by tests** (`test_core.py:406-415`, `test_async_client.py:198-206`) — keep the strings
byte-identical and re-mock the tests around them (Pitfall 5).

---

### `market_data_client/{client,aio}.py` — shells (controller, request-response)

**Analog:** `client.py:661-679` (`preview_calendar_config`) — the gated 4-liner that already
returns a typed model.

```python
        self._ensure_mutation_allowed()
        spec = _core.build_preview_calendar_config_request(self._state, config.to_dict())
        resp = self._request(spec)
        return _core.parse_calendar_config_response(resp)
```

Compare with the two methods being changed (`client.py:699-702`, `:721-724`): the diff is
**one line each** — the parser name — plus the return annotation. The gate line, the builder
call, and `self._request(spec)` are untouched by construction (criterion 3).

Ungated read analog, `client.py:425-429`:

```python
    def get_health(self) -> dict[str, Any]:
        """Reach ``GET {base_url}/health`` anonymously via the retry transport."""
        spec = _core.build_health_request(self._state)
        resp = self._request(spec)
        return _core.parse_health_response(resp)
```

`get_health_feed` (`:431-435`) currently calls the **same** parser — that shared call is the
split point (D-05); after the split each method names its own parser.

Shim analog, `client.py:818-825`:

```python
def get_health() -> dict[str, Any]:
    """Top-level shim: delega al default Client."""
    return _get_default().get_health()
```

`aio.py` mirrors both, with `async def` / `await self._request(spec)` — see
`higyrus_client/aio.py:442-445` for the compact form:

```python
    async def get_health(self) -> dict[str, Any]:
        """``GET /api/health``."""
        spec = _core.build_get_health_request(self._state)
        return _core.parse_get_health_response(await self._request(spec))
```

Only the annotation changes; the parser is shared with the sync shell (C-3 parity mechanism).

**Docstring hazard, G-6:** `client.py:684`'s `add_holidays` docstring claims the builder is
`idempotent=False`. Both holiday builders are `idempotent=True` today. Fix this prose while
editing the method; a planner reading it would seed a criterion-3-violating edit.

---

### `higyrus_client/__init__.py` + `market_data_client/__init__.py` (config, surface)

**Analog:** `higyrus_client/__init__.py:33-45` (import block) and `:95-105` (`__all__`).

```python
from higyrus_client.client import (  # noqa: E402
    Client,
    configure,
    get_health,
    ...
)
```

```python
__all__ = [
    ...
    "PosicionValuada",
    "SafeModel",
    "Sucursal",
    "configure",
    "get_health",
    ...
]
```

`__all__` is alphabetically sorted with classes before lowercase functions (ASCII sort). Add
`Health` to higyrus; add the 8 new names to market-data following `models.py:71-85`'s existing
re-export of the 13 shipped models. Also add them to
`packages/market-data-client/tests/test_public_surface_market_data.py:32` `_NEW_PUBLIC_NAMES`
(G-2) — that list is hand-maintained and silently green when incomplete.

---

### `packages/*/src/*/types.py` ×5 and `models.py` ×2 (config, placeholder — NEW)

**Analog (header + `__all__` form):** `packages/matriz-client/src/matriz_client/types.py:1-14`

```python
"""Shared type vocabulary for the Primary API v1.21 client.

Exports :class:`~typing.Literal` aliases for enum-like parameters
(``Side``, ``OrderType`` …) ... Payload shapes live in
:mod:`matriz_client.models` as safe-access dataclasses; this module
intentionally only carries the small enum-like vocabulary.
"""

from __future__ import annotations

from typing import Literal

__all__ = [
    ...
]
```

The placeholder variant drops the `Literal` import and pins the annotation
(mypy strict needs it for an empty list):

```python
"""Placeholder por uniformidad de estructura (Phase 31, TYP-03).

... Ver `.planning/phases/29-decoder-observable/29-WALLETS-EXEMPTION.md`.
"""

from __future__ import annotations

__all__: list[str] = []
```

**Hard constraints on these 7 files:**
- `from __future__ import annotations` is mandatory in all 7 (CLAUDE.md C-5), even docstring-only.
- wallets' two files must import **nothing** — no `_decode` (the module does not exist there;
  the import reddens all 12 wallets CI matrix legs). Pitfall 8.
- ambito's two files must **not** be re-exported into `__init__.__all__` — that would move
  `verification/snapshots/ambito-financiero-client-surface.txt`.
- `__all__: list[str] = []` (annotated) — bare `[]` fails mypy strict.

---

### `tools/check_uniform_structure.py` (utility, batch — NEW)

**Analog:** `tools/check_decode_intactness.py:625-662` (`check_d_roster`) and `:668-693` (`main`).

Problem-list accumulation + single raise:

```python
def check_d_roster() -> str:
    problems: list[str] = []

    for pkg in IN_SCOPE_PACKAGES:
        if not pkg.decode_path.is_file():
            problems.append(
                f"    in-scope package `{pkg.directory}` has no "
                f"{pkg.decode_path.relative_to(REPO_ROOT)}"
            )
    ...
    on_disk = {p.name for p in sorted((REPO_ROOT / "packages").iterdir()) if p.is_dir()}
    ...
    if problems:
        raise _fail("package roster is out of date:\n" + "\n".join(problems))

    return (
        f"Check D  package roster: {len(IN_SCOPE_PACKAGES)} in-scope packages carry a "
        f"`_decode.py`; {exemptions} exempt (see {EXEMPTION_DOC})"
    )
```

Runner + GitHub annotation form (`:668-693`):

```python
def main() -> int:
    checks = (check_a_..., check_d_roster)
    failures = 0
    for check in checks:
        try:
            print(check())
        except CheckFailure as exc:
            failures += 1
            print(f"::error::Phase 29 DEC-01 decode intactness -- {exc}", file=sys.stderr)
    if failures:
        print(f"::error::decode-intactness gate FAILED ...", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Copy: `problems: list[str]` accumulation, four-space-indented problem lines, `::error::` prefix
on stderr, a success **sentence** printed on the happy path, `raise SystemExit(main())`.
Enumerate `packages/*/` from disk (the `on_disk` set-comprehension above) so a seventh package
is caught automatically. Stdlib-only: `pathlib`, `sys` (D-12; `uv lock --check` is the first
`lint` step and must not see a lock change).

---

### `.github/workflows/ci.yml` — new `lint` step (config)

**Analog:** the `decode-intactness` step, verbatim including the two-line rationale comment:

```yaml
      - name: decode-intactness (Phase 29 DEC-01 — las 5 copias de `_decode.py` colapsan a un hash)
        # Cross-package por naturaleza: NO va al job `test`, que corre per-package.
        # Tampoco puede vivir bajo `verification/`: el job `test` pasa un path
        # explícito que pisa `testpaths`, así que ese directorio nunca corrió en CI.
        run: uv run python tools/check_decode_intactness.py
```

Append the new step immediately after it, same job, same shape (name with phase/req ref in
parentheses, the same rationale comment, `run: uv run python tools/check_uniform_structure.py`).

---

### `packages/market-data-client/tests/test_mutation_gate_ast.py` (test, AST — NEW)

**Analog:** `verification/test_main_market_data_no_gate_bypass.py:41-109` — adapt, do not reuse
(that file parses the *driver*; this one parses `client.py`/`aio.py`). **Place it in-package**,
not under `verification/` — `verification/` never runs in CI (G-5).

Frozenset roster + AST helpers to copy:

```python
_MUTATION_BUILDERS = frozenset(
    {
        "build_create_symbol_request",
        ...
    }
)

_GATE_CALL = "_ensure_mutation_allowed"


def _driver_tree() -> ast.Module:
    return ast.parse((_REPO_ROOT / _DRIVER).read_text(encoding="utf-8"))


def _called_name(node: ast.Call) -> str | None:
    """Nombre invocado de un ``Call``: ``f(...)`` -> ``f``; ``m.f(...)`` -> ``f``."""
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _functions(tree: ast.Module) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    return [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)]
```

`_called_name` and `_functions` transfer verbatim. `_driver_tree` becomes a parametrized
`_shell_tree(name)` over `client.py` / `aio.py`. The first-statement predicate is spelled out in
RESEARCH § Recommended Guard Placement (skip the docstring `ast.Expr`/`ast.Constant`, then check
`body[0]` is an `ast.Expr` wrapping an `ast.Call` whose `_called_name` is `_GATE_CALL`).

**Non-vacuity is mandatory** (Phase 15 WR-01/WR-02): assert the *discovered* method-name set
**equals** the 8-name `_MUTATION_METHODS` frozenset, per shell. A guard that finds zero methods
and reports green is a failure this repo has already been bitten by twice.

Add alongside it the direct builder-flag assertion (`spec.idempotent is True` for both holiday
builders) — criterion 3's second clause, currently only covered indirectly by `test_transport.py`.

---

### Byte-identical request tests (test, request-response — NEW, no analog)

**Closest existing:** `test_calendar_write.py:265-271` and `:352-357` — piecewise, and exactly
what must NOT be copied for this test.

```python
    req = httpx_mock.get_requests()[0]
    assert req.method == "POST"
    assert req.url.path == "/api/calendar/holidays"
    assert req.headers["Authorization"] == "Bearer test-token"
    assert _json.loads(req.content) == {
        "days": [{"day": "2026-12-25", "closed": True, "description": ""}]
    }
```

`json.loads` is order-blind; `HolidayIn.to_dict()`'s key order is part of the v0.4.0 wire
contract. Use RESEARCH § Byte-Identical Request Test's `_frozen()` helper and the two captured
literals instead — a single equality over raw bytes.

**Reuse from the same file** (`test_calendar_write.py:85-88`), the gate opener the new tests need:

```python
def _open_gate() -> None:
    """Abre el gate del singleton default para el host del conftest."""
    market_data_client.configure(mutating_allowed=True, expected_host=_CONFTEST_HOST)
```

Also reuse `_BASE`, `_CONFTEST_HOST` (`:47-50`) and the conftest-seeded `test-token`. Never
include `req.extensions` in the frozen tuple (`request_id` is a fresh `uuid4`, Pitfall 2).

---

### `main_market_data.py` / `main_higyrus.py` (entry point, file-I/O)

Two distinct site classes — do **not** apply one treatment to both (G-3):

| Site class | Sites | Pattern |
|---|---|---|
| `len()` / `isinstance(dict)` | `main_higyrus.py:670,685`; `main_market_data.py:2389` | call `.to_dict()` (D-03) |
| `schema_of(...)` snapshot | `main_market_data.py:627-641`; `main_higyrus.py` probe 15 | **never** `to_dict()` |

**Analog for the snapshot sites:** `main_iol.py:336` `_capture_raw_wire` (Phase 30 CR-01). Its
docstring is the rationale to cite:

> *"los wrappers públicos devuelven modelos. Para cuando un modelo existe, el walker de la Phase 29
> ya coercionó cada campo no-opcional a su tipo declarado y descartó cada clave que ningún campo
> declara, así que `schema_of` sobre la proyección del modelo es función de la **declaración**, no
> del wire."*

`main_market_data.py:2372-2384` already does the right thing via `_mutate_raw_sync(...).json()`
— that is the in-file raw-refire machinery to mirror for the two health probes.

---

## Shared Patterns

### Model declaration
**Source:** `market_data_client/models.py:608-635` (`CalendarDay`)
**Apply to:** all 9 new models
`@dataclass(frozen=True, slots=True)` + `SafeModel` base + bare annotations + `str | None = None`
last. Never construct with `Model(field=value)` — only `Model.from_api(payload)` (C-7). No
`dict[...]` field on any new model (4 of the 8 are nested field types;
`test_decode.py:1203` forbids a mapping-carrying model from being one). No `received_at`.
No `from_api` override (`test_decode.py:1239`, Pitfall 4).

### Parser shape guard + error text
**Source:** `higyrus_client/_core.py:444-453`
**Apply to:** all 4 new/changed parsers that gain a guard
```python
    if not isinstance(raw, dict):
        raise <Pkg>APIError(..., detail=f"expected dict, got {type(raw).__name__}")
```
Type name only, never `repr(raw)` (T-29-36, ASVS V7).

### Decode-scope decoration
**Source:** `market_data_client/_core.py:1029,1066`; `higyrus_client/_core.py:457`;
`iol_client/_core.py:329,344,412`
**Apply to:** every new model-building parser
```python
@_decode._response_parser
def parse_x_response(resp: httpx.Response) -> X:
```
Leading underscore intact, never aliased, never the inline `with _response_scope():` form.

### Body-consume-then-raise order
**Source:** every parser in `market_data_client/_core.py`; `higyrus_client/_core.py:418-423`
(`_consume_and_check`)
**Apply to:** all 4 parsers
`resp.read()` → `raise_for_response(resp)` → decode. Phase 7 D-06 (HTTP/2 safety). Never reorder.

### Sync/async parity
**Source:** `higyrus_client/client.py:450-453` vs `aio.py:442-445`
**Apply to:** all 20 signature sites
The parser is shared through `_core`; only `async def` / `await self._request(spec)` differ.
Never duplicate parse logic into `aio.py` (C-3, DT-04).

### New-module header
**Source:** `matriz_client/types.py:1-12`
**Apply to:** all 7 new modules
Module docstring → blank line → `from __future__ import annotations` → imports → `__all__`.

### CI gate script
**Source:** `tools/check_decode_intactness.py:625-693`
**Apply to:** `tools/check_uniform_structure.py`
`problems: list[str]` accumulation, indented problem lines, `::error::` on stderr, success
sentence on stdout, `raise SystemExit(main())`, stdlib-only.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| byte-identical request tests (in `test_calendar_write{,_async}.py`) | test | request-response | RESEARCH D-08 verified no repo test compares the full header set, the query string, or raw body bytes. The `_frozen()` helper and the two captured literals in RESEARCH § Byte-Identical Request Test are the spec; the only reuse from the codebase is `_open_gate()` and the conftest fixtures. |

---

## Metadata

**Analog search scope:** `packages/*/src/*/`, `packages/*/tests/`, `tools/`, `verification/`,
`.github/workflows/`, `main_*.py`
**Files scanned:** 18 read (targeted ranges), plus directory listings and greps
**Pattern extraction date:** 2026-08-23
