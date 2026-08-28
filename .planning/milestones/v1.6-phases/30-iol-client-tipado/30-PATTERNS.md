# Phase 30: `iol-client` tipado - Pattern Map

**Mapped:** 2026-08-19
**Files analyzed:** 12 (1 new source, 4 modified source, 1 modified driver, 5 modified/new test files, 1 README, 1 golden snapshot)
**Analogs found:** 11 / 12

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `packages/iol-client/src/iol_client/models.py` (NEW) | model | transform | `packages/higyrus-client/src/higyrus_client/models.py` | exact (same walker, same SafeModel contract) |
| `packages/iol-client/src/iol_client/_core.py` (parsers `:327-360`) | service (pure parser) | transform / request-response | `packages/higyrus-client/src/higyrus_client/_core.py:457-498` | exact |
| `packages/iol-client/src/iol_client/client.py` (8 sigs) | controller (transport shell) | request-response | `packages/higyrus-client/src/higyrus_client/client.py` (typed 3-liner methods + shims) | exact |
| `packages/iol-client/src/iol_client/aio.py` (8 sigs) | controller (async transport shell) | request-response | `packages/higyrus-client/src/higyrus_client/aio.py` | exact |
| `packages/iol-client/src/iol_client/__init__.py` | config / exports | — | `packages/higyrus-client/src/higyrus_client/__init__.py:56-72` | exact |
| `main_iol.py` (attr sites + `to_dict()` sites + probe annotations) | driver / harness | batch verification | `main_higyrus.py:435-470` (`_write_or_check_schema` + `schema_of(raw_payload)`) | role-match (higyrus feeds models to `schema_of` today) |
| `packages/iol-client/tests/test_models.py` (NEW) | test | transform | `packages/market-data-client/tests/test_models.py:1-55` | exact |
| `packages/iol-client/tests/test_typed_surface_red.py` (NEW) | test (static RED fixture) | — | **none** — no typecheck-RED fixture exists in the monorepo | no analog (use RESEARCH Pitfall 1 form) |
| `packages/iol-client/tests/test_core.py` (parser asserts + non-list raise) | test | transform | `packages/iol-client/tests/test_decode.py:96-140` (module-local model fixtures = the shape F30 generates) | exact |
| `packages/iol-client/tests/test_client.py`, `test_async_client.py`, `test_refresh_token_lifecycle*.py`, `test_fixture_reaches_production.py` (18 re-mock lines + 23 assert lines) | test | request-response | `packages/iol-client/tests/test_client.py:55-100` (its own current form) | exact (self-analog, mechanical rewrite) |
| `packages/iol-client/README.md` (Changelog + §Uso fix) | doc | — | `packages/market-data-client/README.md:123-193` | exact |
| `verification/snapshots/iol-client-surface.txt` | golden | — | `verification/snapshots/higyrus-client-surface.txt` (shows models rendered with full `__init__` signature) | exact |

## Pattern Assignments

### `iol_client/models.py` (model, transform) — NEW

**Analog:** `packages/higyrus-client/src/higyrus_client/models.py`

**Module docstring + imports** (higyrus `models.py:1-38`) — copy structure, **drop the `N815` sentence** (lines 18-20: it claims a per-file-ignore that does not exist for higyrus and would propagate a false claim; see RESEARCH C-5). Add the D-08/Pitfall-2 `DecodePolicy` ratification paragraph here:

```python
"""Safe-access frozen dataclasses for IOL API responses.
...
- ``str`` -> ``""`` ; ``int``/``float`` -> ``0``/``0.0`` ; ``bool`` -> ``False``
- ``list[X]`` -> ``[]`` ; nested ``SafeModel`` -> empty instance
- ``X | None`` -> ``None`` when missing (explicit opt-in to nullable)
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import Any, Self

from iol_client import _decode
```

Note: higyrus imports only `dataclass`; iol additionally needs `import dataclasses` for `asdict` (D-08).

**SafeModel base** — copy verbatim from `higyrus_client/models.py:41-54`, then add `to_dict` (iol-only):

```python
class SafeModel:
    """Base class for IOL API response models.

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

    def to_dict(self) -> dict[str, Any]:   # D-08 — NOT in the higyrus template
        """Escape hatch for the dict→model break + the harness ``schema_of`` adapter."""
        return dataclasses.asdict(self)
```

**Do NOT copy** `higyrus_client/models.py:57-71` (`_coerce` back-compat shim) — it exists only for higyrus's pre-Phase-29 callers; iol has none.

**Dataclass declaration pattern** — copy from `higyrus_client/models.py:74-116` (`PosicionValuada`): `@dataclass(frozen=True, slots=True)`, `SafeModel` base, docstring carrying *verified-against-wire* notes, then bare camelCase field declarations with no defaults:

```python
@dataclass(frozen=True, slots=True)
class PosicionValuada(SafeModel):
    """Valued position row returned by ``GET /api/cuentas/{idCuenta}/posicionValuada``.

    Verified against sandbox on 2026-04-24:
    - ``cantidad`` arrives as a float (e.g. ``-2788.35``). Modeled as ``float``.
    ...
    """

    cuenta: str
    ...
    cantidad: float
```

Apply to `Punta` (declare first), `Cotizacion`, `Instrumento`, `Titulo` per the RESEARCH field tables. Docstrings must carry: the A1 unobserved-type flags (`Titulo.fechaVencimiento`/`precioEjercicio`/`tipoOpcion`), the D-04 `cantidadOperaciones` int/float asymmetry (Pitfall 4), and the D-02 unobserved-element note on `Cotizacion.puntas`.

**Anti-pattern (do not copy from anywhere):** a `from_api` override. `market_data_client/models.py:600-605` needs `super(Symbol, cls).from_api(...)` because of Pitfall 7 (`slots=True` rebuilds the class); iol's minimal SafeModel has zero overrides and must stay that way.

---

### `iol_client/_core.py` parsers (service, transform) — rewrite in place

**Analog:** `packages/higyrus-client/src/higyrus_client/_core.py:457-498`

**Shared helper carrying the decorator** (higyrus `_core.py:457-474`):

```python
@_decode._response_parser
def _parse_list_or_raise(resp: httpx.Response, model_cls: type[Any]) -> list[Any]:
    """Helper común para parsers que retornan ``list[Model]`` con 204→``[]``."""
    body = _consume_and_check(resp)
    if resp.status_code == 204 or not body:
        return []
    raw = resp.json()
    if not isinstance(raw, list):
        raise HigyrusAPIError(
            status_code=0,
            errors=[{"title": "shape mismatch",
                     "detail": f"expected list, got {type(raw).__name__}"}],
        )
    return [model_cls.from_api(item) for item in raw]
```

**Typed one-liner parsers** (higyrus `_core.py:477-498`) — the exact shape the four iol parsers become:

```python
def parse_get_movimientos_response(resp: httpx.Response) -> list[Movimiento]:
    """Parser ``GET /api/cuentas/{id_cuenta}/movimientos`` → ``list[Movimiento]``."""
    result: list[Movimiento] = _parse_list_or_raise(resp, Movimiento)
    return result
```

The intermediate annotated local is load-bearing: `_parse_list_or_raise` returns `list[Any]`, so the annotation is what narrows for mypy strict.

**Three iol adaptations — the copy is NOT verbatim:**
1. iol has **no** `_consume_and_check`. Its existing pair is `resp.read()` + `raise_for_response(resp)` (`_core.py:329-330`). Copying higyrus's helper would add 204/empty-body tolerance iol does not have — out of scope.
2. `IOLAPIError.__init__(status_code: int, message: str)` is **two positional args** (`exceptions.py:13`), not higyrus's `(status_code, errors=[...])`.
3. The decorator goes on the shared helper only; the four public parsers stay undecorated one-liners (nesting stays safe).

**Current code being replaced** (`iol_client/_core.py:327-360`) — note the envelope unwrap at `:358-359` that D-06 preserves as a raw-dict step:

```python
def parse_get_instruments_by_type_response(resp: httpx.Response) -> list[dict[str, Any]]:
    """Pure: parse instruments-by-type response → list under ``titulos`` key."""
    resp.read()
    raise_for_response(resp)
    data: dict[str, Any] = resp.json()
    titulos: list[dict[str, Any]] = data.get("titulos", [])
    return titulos
```

Target forms for all four are given verbatim in `30-RESEARCH.md` § Pattern 3.

---

### `iol_client/client.py` + `aio.py` (controller, request-response) — 16 return annotations

**Analog:** the files themselves — the 3-liner shell shape is already correct; only the return type changes. Current shapes:

```python
# client.py:514-527 — method
    def get_quote(self, simbolo: str, *, mercado: str = "bcba", plazo: str = "t2",
    ) -> dict[str, Any]:                     # → Cotizacion
        """Cotización actual de un título.

        Endpoint: ``GET /api/v2/{mercado}/Titulos/{simbolo}/Cotizacion``.
        """
        spec = _core.build_get_quote_request(self._state, simbolo, mercado=mercado, plazo=plazo)
        resp = self._request(spec)
        return _core.parse_get_quote_response(resp)

# client.py:673-680 — module shim (identical signature, one-line delegation)
def get_quote(simbolo: str, *, mercado: str = "bcba", plazo: str = "t2") -> dict[str, Any]:
    """Top-level shim: delega al default Client."""
    return _get_default().get_quote(simbolo, mercado=mercado, plazo=plazo)

# client.py:549-556 — the `Any` outlier
    def get_instruments(self, pais: str = "argentina") -> Any:   # → list[Instrumento]
```

**Rules:** no logic moves into the shells; only the annotation and the `models` import change. `client.py:536` `ajustada: Literal[...]` is an INPUT literal and stays. Treat all 16 as one atomic unit (Pitfall 6). `aio.py` mirrors at `:536-546`, `:548-562`, `:564-568`, `:570-579` (methods) and `:693-699`, `:702-713`, `:715-716`, `:719-725` (shims).

---

### `iol_client/__init__.py` (exports)

**Analog:** `packages/higyrus-client/src/higyrus_client/__init__.py:56-72` — models imported in a dedicated block and each listed in the sorted `__all__`:

```python
from higyrus_client.models import (  # noqa: E402
    Administrador,
    ...
    SafeModel,
    Sucursal,
)

__all__ = [
    "Administrador",
    "Agente",
    "AsyncClient",
    ...
]
```

iol's current block is `__init__.py:32-70` (imports are post-`_logging_attach.attach()`, hence the `# noqa: E402` on every import — preserve that). Add `Cotizacion`, `Instrumento`, `Punta`, `Titulo` (and `SafeModel`, following higyrus) to both the import and the sorted `__all__`. Pitfall 3: without this the surface snapshot and the Phase 32 AST gate see nothing.

---

### `main_iol.py` (driver/harness, batch)

**Analog:** `main_higyrus.py:435-470` (`_write_or_check_schema`) — the D-25 no-overwrite discipline iol shares:

```python
    actual_schema = schema_of(raw_payload)
    envelope = {..., "schema": actual_schema}
    file_path = _SCHEMA_FILES[func_name]
    if not file_path.exists():
        file_path.write_text(json.dumps(envelope, indent=2, ensure_ascii=False) + "\n", ...)
        return ("PASS", f"escrito {file_path.name}")
    committed = json.loads(file_path.read_text(encoding="utf-8"))
    if committed.get("schema") == actual_schema:
        return ("PASS", f"{file_path.name} sin drift")
```

This is why RESEARCH C-1 holds: baselines are never overwritten on drift, so the D-07 risk is **vacuous green**, not corruption.

**Attribute sites to change** — current form at `main_iol.py:316-317` and `:395`:

```python
    # Plausibility check del precio (Discretion).
    ultimo = quote.get("ultimoPrecio")
    if isinstance(ultimo, int | float) and not (_PRICE_MIN < float(ultimo) < _PRICE_MAX):
```

becomes `ultimo = quote.ultimoPrecio` + `if not (_PRICE_MIN < ultimo < _PRICE_MAX):` (the `isinstance` guard is provably dead; Open Question 2 recommends removal). Keep the `quote is None` guard.

**`schema_of` boundary sites** — `main_iol.py:1065-1066` current form:

```python
    if quote is not None:
        observed = schema_of(quote)
        if isinstance(observed, dict):
```

becomes `schema_of(quote.to_dict())`. Same at `:1102` (`historical[0].to_dict()`), `:1164` (3 of 4 targets), and `:918-919` via the `_as_wire` adapter in RESEARCH § Code Examples. **`by_type_envelope` is immune** (raw `_request` at `:995`) — do not route it through `to_dict()` or `_as_wire` call sites that assume a model.

---

### `packages/iol-client/tests/test_models.py` (test, transform) — NEW

**Analog:** `packages/market-data-client/tests/test_models.py:1-55` — docstring pinning the decisions, direct model imports, one behavior per test:

```python
"""Tests for the tolerant ``market_data_client.models`` layer (Plan 21-01).

Pins the D-01/D-04/D-05 behaviors:
- ``MarketDataSnapshot.from_api`` tolerates ``{}`` / ``None`` / extra-key payloads ...
"""

from __future__ import annotations

import dataclasses
import pytest

from market_data_client.models import (MarketDataSnapshot, SafeModel, ...)


def test_from_api_empty_dict_typed_zero_defaults() -> None:
    snap = MarketDataSnapshot.from_api({})
    assert snap.symbol == ""
    assert snap.entries == []
    assert snap.note is None


def test_from_api_none_does_not_raise() -> None:
    snap = MarketDataSnapshot.from_api(None)
```

Cover per RESEARCH § Wave 0: 4 shapes vs the 4 committed schemas (zero divergences), `puntas` across `[]`/object/`null`, `to_dict()` round-trip vs the 3 committed JSON baselines, and the `cantidadOperaciones` int/float asymmetry.

**Secondary analog for scope-isolation:** `packages/iol-client/tests/test_decode.py:49-75` — the `_pristine_decode_context` autouse fixture. Any bare `Model.from_api()` assertion about divergence records must run under an unbound scope or a prior test's `DECODE_SCOPE` dedupes the record away (test-order-dependent green).

---

### `packages/iol-client/tests/test_typed_surface_red.py` (test, static) — NEW, **no analog**

No typecheck-RED fixture exists anywhere in the monorepo. Use the exact validated form from `30-RESEARCH.md` Pitfall 1 (`pytest.raises(AttributeError)` wrapping the `# type: ignore[attr-defined]` typo). Non-vacuity in both directions depends on `warn_unused_ignores = true` (`pyproject.toml:86`).

---

### iol test migration (test, request-response) — self-analog

**Current form to rewrite**, `packages/iol-client/tests/test_client.py:55-100`:

```python
def test_get_quote_arma_url_y_params(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://api.test/...", json={"ultimoPrecio": 1234.5, "simbolo": "GGAL"})
    quote = iol_client.get_quote("GGAL")
    assert quote["ultimoPrecio"] == 1234.5          # → quote.ultimoPrecio

def test_get_instruments_devuelve_payload(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="...", json={"instrumentos": ["acciones", "cedears"]})   # → json=[{...}]
    payload = iol_client.get_instruments()
    assert payload == {"instrumentos": ["acciones", "cedears"]}   # → attribute assert on list[Instrumento]
```

Note `test_client.py:114` / `test_async_client.py:76` assert `quote["simbolo"] == "GGAL"` — `simbolo` is **not** a `Cotizacion` field; those asserts get **deleted**, not rewritten. Exact line inventories: RESEARCH § Blast Radius (18 mock lines, 23 assert lines, 4 non-mechanical).

---

### `packages/iol-client/README.md` (doc)

**Analog:** `packages/market-data-client/README.md:123-193`. Structure: `## Changelog` heading, then `### vX.Y.Z` sections newest-first, each opening with a bolded one-line verdict plus a semver-rationale parenthetical, then bullets naming the decision IDs:

```markdown
## Changelog

### v0.4.0

**Nueva superficie de escritura: calendar, más los fixes verificados en vivo contra develop**
(features nuevas, minor bump — la superficie de lectura v0.2.0 sigue intacta **excepto
`CalendarDay`**, que reemplaza campos; ver "Reemplazo de campos de `CalendarDay`" abajo).

- **Calendar write (MUT-MD-02):** ocho nombres públicos nuevos en el `__all__` plano — ...
```

Note the precedent at `:154-163`: a breaking change gets its own bolded sub-block explaining *why it ships in that bump* — the exact shape the dict→model break + truthiness flip needs. iol's `### v0.3.0` section lands now; `__version__` stays `"0.2.0"` (D-11).

**Also (D-12):** the `## Uso` section (README lines 13-31) documents `IOLClient(token=...)` / `AsyncIOLClient` / `get_portfolio()` — **none exist**. Replace with the real surface, whose canonical statement is the `iol_client/__init__.py:1-21` module docstring:

```python
"""Cliente HTTP (sync y async) para Invertir Online (IOL).

Sync (top-level shim, back-compat 100%)::

    import iol_client
    iol_client.login()
    quote = iol_client.get_quote("GGAL")

Sync (class-based, Phase 6+)::

    from iol_client import Client
    with Client(username="alice", password="secret") as c:
        quote = c.get_quote("GGAL")

Async::

    from iol_client import aio
    await aio.login()
    quote = await aio.get_quote("GGAL")
    await aio.aclose()
"""
```

## Shared Patterns

### Module header (applies to every new/modified source file)
**Source:** `higyrus_client/models.py:1-38`, `iol_client/_core.py:1-45`
Module docstring stating purpose + decision IDs + usage `::` block, then `from __future__ import annotations` (mandatory repo-wide, and load-bearing here per Pitfall 8), then stdlib → third-party → in-package imports, no relative imports (TID).

### Decode delegation (applies to `models.py` only)
**Source:** `higyrus_client/models.py:48-54`
`from_api` is a 3-line delegation to `_decode.walk_model(cls, payload, policy=_decode.POLICY, sink=_decode.current_sink())`. **No coercion logic may live in `models.py`** — a local coercion path is invisible to the Phase 33 divergence census.

### Decode-scope ownership (applies to `_core.py` parsers only)
**Source:** `higyrus_client/_core.py:457`
`@_decode._response_parser` decorates the shared list helper and each top-level per-response parser — one `DecodeScope` per HTTP response. Never a module-level dedupe `set()` (rejected by name, aggregation lock 6).

### Error raising in parsers
**Source:** `higyrus_client/_core.py:444-453` (shape guard) — adapted to iol's signature `IOLAPIError(0, f"expected list, got {type(raw).__name__}")` (`exceptions.py:13`, two positionals). A failed shape guard **raises**; it never degrades to `[]` (D-06, ASVS V5).

### Sync/async mirroring
**Source:** CLAUDE.md Constraints; `client.py` ↔ `aio.py` across all six packages.
Every signature change lands in both files in the same commit.

### Frozen model declaration
**Source:** `higyrus_client/models.py:74-116`
`@dataclass(frozen=True, slots=True)` + `SafeModel` base + wire-verbatim camelCase fields + a docstring recording what was verified against the live wire and on what date.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `packages/iol-client/tests/test_typed_surface_red.py` | test (static typecheck RED) | — | No `# type: ignore` + `warn_unused_ignores` RED fixture exists in any package. Use the empirically validated form in `30-RESEARCH.md` Pitfall 1 verbatim. |

## Metadata

**Analog search scope:** `packages/higyrus-client/`, `packages/market-data-client/`, `packages/iol-client/`, `main_iol.py`, `main_higyrus.py`, `verification/`
**Files scanned:** 16
**Pattern extraction date:** 2026-08-19
