# Phase 33: Verificación en vivo en modo estricto + fixes - Pattern Map

**Mapped:** 2026-08-26
**Files analyzed:** 13 (4 new code files + 1 new script + 2 new artifacts + 6 modified drivers/barrel, plus N per-fix package pairs)
**Analogs found:** 12 / 13

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `verification/divergences.py` (NEW) | utility / harness module | event-driven (logging sink) | `verification/capture.py` (module shape) + `verification/findings.py::append_finding` (sink API) | role-match |
| `verification/__init__.py` (MOD) | barrel / config | — | itself (lines 1-51, additive edit) | exact |
| `verification/test_divergences.py` (NEW) | test | event-driven | `verification/test_logging_root_unchanged.py` | exact |
| `verification/test_cycle_closure_phase33.py` (NEW) | test | batch / assertion | `verification/test_cycle_closure_market_data.py` | exact |
| AST gate: every `probe_*` carries the decorator (NEW, optional) | test | transform / static | `verification/test_main_drivers_bare_except.py` | exact |
| `main_higyrus.py` (MOD) | driver / controller | request-response | itself (`_RESIDUAL_PROBE_EXCEPTIONS` :140-147, `_ENDPOINT_TEMPLATES` :157-163) + `main_iol.py:190-220` (fid seed) | exact |
| `main_matriz.py` (MOD) | driver / controller | request-response | `main_higyrus.py` (same zero-`except Exception` shape) | exact |
| `main_ambito_financiero.py` (MOD) | driver / controller | request-response | `main_iol.py:190-220` (fid seed only; D-12 smoke) | role-match |
| `main_iol.py` (MOD) | driver / controller | request-response | itself (`_ENDPOINT_TEMPLATES` :166-173, seed already present) | exact |
| `main_market_data.py` (MOD) | driver / controller | request-response | `main_iol.py:166-173` / `main_higyrus.py:157-163` for the new `_ENDPOINT_TEMPLATES` (D-03) | exact |
| `packages/<pkg>/src/<pkg>/{client,aio,models,_core}.py` (MOD per fix) | service / model | request-response | the sibling surface file in the same package (C-3 mirror) | exact |
| `packages/<pkg>/tests/test_<fix>.py` (NEW per fix) | test | request-response (mocked) | `packages/higyrus-client/tests/test_decode.py:870-921` | exact |
| `scripts/preflight_33.py` (NEW, may be uncommitted) | script / config | request-response | `verification/env_gate.py::require_env` (SKIP semantics) | partial |
| `33-CENSUS.md` / `33-LITERALS.md` (NEW artifacts) | doc | — | — | **no analog** |

Probe counts per driver (decorator application surface): higyrus 19, iol 15, matriz 46, market-data 43, ambito 7 = **130**.

---

## Pattern Assignments

### `verification/divergences.py` (utility, event-driven) — NEW

**Analog A (module shape):** `verification/capture.py`
**Analog B (sink contract):** `verification/findings.py:583-598`

**Module-header pattern to copy verbatim** (`verification/capture.py:1-34`) — Spanish module docstring with purpose + `Uso::` block, `from __future__ import annotations`, explicit `__all__` immediately after imports, repo root resolved from `__file__` never `cwd`:

```python
"""<purpose one-liner> (<REQ-ID>/<D-NN>).

<why this module exists, 2-4 paragraphs>

Uso::

    from verification.capture import capture

    path = capture("ambito", "dollar", payload)   # .../captures/ambito-dollar.json
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

__all__ = ["capture", "captures_dir"]

# Raíz del repo = el directorio que contiene el paquete ``verification/``.
# Se resuelve respecto de la ubicación de este módulo, no del cwd, para que
# la ruta del staging sea estable sin importar desde dónde se invoque.
_REPO_ROOT = Path(__file__).resolve().parent.parent
```

**Sink signature the handler must call** (`verification/findings.py:583-598`) — keyword-only after `pkg`; `class_="SHAPE"`, `status="OPEN"`, `idempotent_by_title=True` per Lock 10:

```python
def append_finding(
    pkg: str,
    *,
    fid: str,
    class_: str,
    surface: str,
    status: str,
    title: str,
    expected: str,
    actual: str,
    diff: str,
    regression: str | None = None,
    base_url: str | None = None,
    market_hours: str | None = None,
    idempotent_by_title: bool = False,
) -> Path:
```

Validation that raises `ValueError` and is therefore swallowed by P-2 (`findings.py:631-634`) — the handler MUST pre-validate or catch:

```python
if class_ not in FINDING_CLASSES:
    raise ValueError(f"class_={class_!r} no está en FINDING_CLASSES={FINDING_CLASSES!r}")
if status not in STATUS_LIFECYCLE:
    raise ValueError(f"status={status!r} no está en STATUS_LIFECYCLE={STATUS_LIFECYCLE!r}")
```

**ContextVar precedent to mirror:** `_decode.STRICT_DECODE` / `_decode.DECODE_SCOPE` (`packages/higyrus-client/src/higyrus_client/_decode.py:248-251`). Same primitive, module-level, `set`/`reset` token discipline.

**Handler + install-CM + decorator sketches:** RESEARCH.md Patterns 1-3 (lines 401-527) are the authoritative shape; the planner should treat them as the starting draft. Three non-optional hardenings: `setLevel(INFO)` on each package logger (P-1), self-guarding `emit` with an `errors` tally (P-2), a **single shared** `next_fid` callable passed in from the driver (P-3).

**Anti-pattern:** never `logging.root`. Guarded three ways — see `verification/test_logging_root_unchanged.py` below.

---

### `verification/__init__.py` (barrel) — MOD

**Analog:** itself, lines 1-51. The edit is purely additive and must touch three places consistently:

```python
# 1. docstring bullet, same voice as the others (lines 7-20):
- :mod:`verification.findings` — ``new_findings`` / ``write_findings`` /
  ``append_finding``: plantilla de hallazgos + append idempotente por fid, ...

# 2. import, alphabetical among the existing block (lines 29-36):
from verification.capture import capture
from verification.env_gate import require_env
from verification.findings import append_finding, new_findings, write_findings

# 3. __all__, sorted (lines 38-51):
__all__ = [
    "Denylist",
    "anonymize",
    "append_finding",
    ...
]
```

---

### `verification/test_divergences.py` (test, event-driven) — NEW

**Analog:** `verification/test_logging_root_unchanged.py` (67 lines, read in full)

**Imports + header pattern** (lines 1-24):

```python
"""<Invariant one-liner> — <what MUST NOT happen>.

Phase 8 D-14, D-26, D-27, LOG-01 / Pitfall 6. ...

Invariant: importing any of the 4 paquetes MUST NOT add handlers to
``logging.root``, ...
"""

from __future__ import annotations

import importlib
import logging
```

**Snapshot/restore assertion pattern** (lines 39-67) — the exact shape `test_install_sets_level_and_restores` should copy: capture before, act, assert identity, and put the *why* in the assertion message:

```python
handlers_before = list(logging.root.handlers)
filters_before = list(logging.root.filters)
level_before = logging.root.level
...
assert list(logging.root.handlers) == handlers_before, (
    f"logging.root.handlers drifted after package import.\n"
    f"  before: {handlers_before!r}\n"
    f"  after:  {list(logging.root.handlers)!r}\n"
    f"Library code MUST attach NullHandler to its own logger only "
    f"(per D-13, D-14, LOG-01)."
)
```

**Note carried from the analog's docstring (lines 34-38):** pytest's `caplog` installs handlers on `logging.root` by design — a test asserting root is untouched must deliberately *not* request `caplog`. The `extra`-kind capture tests, conversely, may use `caplog`.

---

### `verification/test_cycle_closure_phase33.py` (test, batch) — NEW

**Analog:** `verification/test_cycle_closure_market_data.py` (54 lines, read in full) — this file already implements the exact non-vacuity assertion D-11/P-7 demands. Copy it per package with the Phase 33 count.

**Imports + module constant** (lines 23-28):

```python
from __future__ import annotations

from verification.cycle_report import _iter_findings, verify_cycle_closure
from verification.findings import findings_path

_PKG = "market-data-client"
```

**Two-test structure — green test + non-vacuity test** (lines 31-53):

```python
def test_market_data_cycle_closure_is_green() -> None:
    ok, missing = verify_cycle_closure(_PKG)
    assert ok, f"cycle closure not green; findings without a resolvable Regression link: {missing}"
    assert missing == []


def test_market_data_cycle_closure_is_not_vacuous() -> None:
    """El pass NO viene de un archivo ausente ni de cero findings aplicables."""
    path = findings_path(_PKG)
    assert path.exists(), (
        f"{path} is missing — verify_cycle_closure returns (True, []) for a "
        "nonexistent file, so its green result would be meaningless"
    )
    statuses = [status for _fid, status, _reg in _iter_findings(path.read_text(encoding="utf-8"))]
    applicable = [s for s in statuses if s in ("CONFIRMED", "FIXED")]
    assert applicable, (
        "no finding is CONFIRMED/FIXED, so the closure check had nothing to "
        f"validate; statuses seen: {sorted(set(statuses))}"
    )
    assert len(applicable) >= 34, f"expected >= 34 applicable findings, got {len(applicable)}"
```

The `>= 34` literal is the analog's Phase-27 backfill count. Phase 33 substitutes the per-package inspected-count baseline measured in Wave 0 **plus** the number of Phase 33 fixes (P-7).

---

### AST gate: decorator coverage over all `probe_*` (test, static) — NEW, optional per RESEARCH Wave-0 list

**Analog:** `verification/test_main_drivers_bare_except.py` (51 lines, read in full)

**Full pattern — parametrized AST walk over drivers with repo-root resolution** (lines 17-51):

```python
from __future__ import annotations

import ast
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DRIVERS = ["main_matriz.py", "main_higyrus.py"]


@pytest.mark.parametrize("driver", _DRIVERS)
def test_no_bare_except_in_driver(driver: str) -> None:
    tree = ast.parse((_REPO_ROOT / driver).read_text(encoding="utf-8"))
    bare_sites: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        if node.type is None:
            bare_sites.append((node.lineno, "<bare except:>"))
            continue
        if isinstance(node.type, ast.Name) and node.type.id == "Exception":
            bare_sites.append((node.lineno, "except Exception"))
    assert not bare_sites, f"{driver} has {len(bare_sites)} bare-except site(s): {bare_sites}"
```

For the coverage gate: same skeleton, `_DRIVERS` extended to all five, walk for `ast.FunctionDef`/`ast.AsyncFunctionDef` whose `name.startswith("probe_")`, and assert the decorator name appears in `node.decorator_list`. **This same file is the CI regression D-06 forbids breaking** — matriz and higyrus must stay at zero `except Exception` after the decorator lands.

---

### `main_higyrus.py` / `main_matriz.py` / `main_ambito_financiero.py` (driver) — MOD

**Analog for the fid seed:** `main_iol.py:190-220` — copy **verbatim** (docstring included, adjusted to the target driver's own committed fids):

```python
def _seed_fid_counter() -> None:
    """Sube ``_fid_counter`` al máximo fid ya registrado en el findings file (D-16/D-24).

    Debe correr DESPUÉS de ``write_findings(_PKG)`` (el bootstrap del archivo) y
    ANTES del primer probe, para que todo fid emitido en este run caiga por
    encima de lo ya escrito y realmente aterrice en el archivo.
    ...
    Misma forma que ``main_market_data.py::_seed_fid_counter``.
    """
    global _fid_counter
    _fid_counter = max_existing_fid(_PKG)


def _next_fid() -> str:
    """Devuelve el siguiente ``F-NN`` (NN zero-padded a 2 dígitos)."""
    global _fid_counter
    _fid_counter += 1
    return f"F-{_fid_counter:02d}"
```

`main_higyrus.py:237-241` already has the `_next_fid` half verbatim — only `_seed_fid_counter` plus the `max_existing_fid` import and the `main()` call site are missing. Call order (`main_market_data.py:3319-3324`): `require_env(...)` → `write_findings(_PKG)` → `_seed_fid_counter()` → first probe. `main_iol.py:1941` is the equivalent call site.

**Analog for the exception tuple:** `main_higyrus.py:133-147` — extend, never replace; keep the comment block explaining the residual-catch contract:

```python
# Phase 11 CR-06: tuple de excepciones residuales para los catch-all post-mapeo
# en los probe boundaries. ... EXCLUYE
# ``KeyboardInterrupt`` y ``SystemExit`` (no son ``Exception`` subclasses).
_RESIDUAL_PROBE_EXCEPTIONS = (
    httpx.HTTPError,
    OSError,
    AttributeError,
    TypeError,
    ValueError,
    KeyError,
)
```

`main_matriz.py:117` is the same construct. **Do not add `<Pkg>DecodeError` into this tuple** — that would map it to `ERROR-MAP` via the residual handler. It must be intercepted by the decorator *before* the residual `except` so it becomes a deterministic-title `SHAPE`.

**Analog for `_ENDPOINT_TEMPLATES`** (`main_higyrus.py:156-163`, `main_iol.py:165-173`) — dict keyed by **client function name**, values are path templates with `{param}` placeholders. This is the shape `main_market_data.py` must gain per D-03 (its `_ENDPOINT_OPTIONAL` at `:110` is an unrelated `frozenset`):

```python
# D-HIGY-16 envelope D-21: path templates por endpoint.
_ENDPOINT_TEMPLATES: dict[str, str] = {
    "get_health": "/api/health",
    "get_listado_cuentas": "/api/cuentas/listadoCuentas",
    "get_movimientos": "/api/cuentas/{id_cuenta}/movimientos",
}
```

Existing consumption sites to mirror: `main_higyrus.py:1976`, `main_iol.py:1589` (`_ENDPOINT_TEMPLATES[func_name]`).

**Analog for the D-07 deletion:** `main_higyrus.py:681-695` (sync) and `:780+` (async) — this is the exact block to remove, plus the docstring paragraph at `:635-637` that describes it:

```python
    except HigyrusDecodeError as exc:
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="SHAPE",
            surface="sync",
            status="OPEN",
            title="get_health_sync: divergencia de decode en Health (strict_decode)",
            expected="payload compatible con el modelo Health declarado",
            actual=f"model={exc.model} field_path={exc.field_path}",
            diff=f"declared={exc.declared_type} observed={exc.observed_type}",
            base_url=base_url,
        )
        return (ProbeResult("get_health_sync", "FINDING", f"{fid} (OPEN)"), None)
```

Note the **exception-handler ordering** the analog establishes and the decorator must preserve: `<Pkg>AuthError` → `<Pkg>APIError` → (decode) → `_RESIDUAL_PROBE_EXCEPTIONS`. Also note `exc.model` / `exc.field_path` / `exc.declared_type` / `exc.observed_type` are the four certified type-and-path-only attributes (T-29-36) — the decorator's fallback `ProbeResult` may use them; nothing else from the exception.

**`ProbeResult` contract the decorator must keep producing** (`main_higyrus.py:295-301`):

```python
class ProbeResult:
    """Resultado de un probe; agregado al summary final."""

    name: str
    status: str  # "PASS" | "FAIL" | "SKIPPED" | "FINDING"
    detail: str
```

Probes return `tuple[ProbeResult, <payload> | None]` — the decorator's decode-error branch must return that 2-tuple shape, not a bare `ProbeResult`.

**Two-pass flag** (RESEARCH Pattern 4) — module constant read once, threaded through the **single** ctor site so `test_main_*_uses_single_client_instance.py` stays green:

```python
_STRICT = os.getenv("MARKET_LIBS_STRICT_DECODE") == "1"
...
client = Client(strict_decode=_STRICT)     # still ONE ctor site
```

Existing env-var precedents in the drivers for naming consistency: `HIGYRUS_SAMPLE_CUENTA` (`main_higyrus.py:166`), `MARKET_DATA_VERIFY_MUTATING`, `VERIFY_HIGYRUS_BAD_CREDS`.

---

### `packages/<pkg>/tests/test_<fix>.py` (test, mocked request-response) — NEW per confirmed fix

**Analog:** `packages/higyrus-client/tests/test_decode.py:870-921`

**Sync test pattern** (lines 870-884) — `httpx_mock` fixture, context-restoring helper, explicit `Client(...)` with a pre-seeded token so no auth round-trip is mocked:

```python
def test_strict_mode_bound_by_request(httpx_mock: HTTPXMock) -> None:
    """The bind happens at the top of ``Client._request``, from ``_state``."""
    httpx_mock.add_response(json={"status": "ok"})
    with _restored_decode_context():
        _decode.STRICT_DECODE.set(False)
        _decode.DECODE_SCOPE.set(None)
        with Client(
            base_url="https://api.test",
            token="t",
            token_expires_at=9_999_999_999.0,
            strict_decode=True,
        ) as c:
            c._request(_spec())
        assert _decode.STRICT_DECODE.get() is True
```

**Async mirror pattern** (lines 907-921) — C-3 requires the twin; note the docstring convention naming it as parity, and that `asyncio_mode = "auto"` means no `@pytest.mark.asyncio`:

```python
async def test_async_request_binds_mode(httpx_mock: HTTPXMock) -> None:
    """Dual sync/async parity: ``AsyncClient._request`` mirrors the bind verbatim."""
    httpx_mock.add_response(json={"status": "ok"})
    with _restored_decode_context():
        _decode.STRICT_DECODE.set(False)
        _decode.DECODE_SCOPE.set(None)
        async with AsyncClient(
            base_url="https://api.test",
            token="t",
            token_expires_at=9_999_999_999.0,
            strict_decode=True,
        ) as c:
            await c._request(_spec())
            assert _decode.STRICT_DECODE.get() is True
```

**Placement is load-bearing (P-8):** only `packages/<pkg>/tests/` runs in CI. The `Regression:` bullet must read `packages/<pkg>/tests/<file>.py::<test_name>`.

Also present in every package for the C-3 drift check: `packages/<pkg>/tests/test_surface_parity.py` (already exists ×5 — run it after every fix, do not rewrite it).

---

### `scripts/preflight_33.py` (script) — NEW (may be uncommitted)

**Analog:** `verification/env_gate.py:32-41` — the SKIP-not-raise contract the pre-flight extends from presence to authentication:

```python
def require_env(pkg: str, names: list[str]) -> bool:
    """True si todas las vars existen; si faltan, imprime SKIPPED y devuelve False.

    Nunca interrumpe el proceso: el caller controla la salida (Pitfall 6).
    """
    missing = [n for n in names if not os.getenv(n)]
    if missing:
        print(f"SKIPPED {pkg}: missing {', '.join(missing)}")
        return False
    return True
```

Two constraints from RESEARCH: it **must be a real `.py` file**, never `python -c` (P-10 — `find_dotenv()` falls back to `os.getcwd()` when `__main__` has no `__file__`), and it must print only `type(exc).__name__`, never the exception body (C-4 / `main_iol.py::_redacted_exc`). Body sketch at RESEARCH lines 1139-1156.

---

## Shared Patterns

### Module header (every new `.py` in this phase)

**Source:** `verification/capture.py:1-33`, `verification/env_gate.py:1-29`, `verification/test_cycle_closure_market_data.py:1-28`
**Apply to:** `verification/divergences.py`, all three new test files, `scripts/preflight_33.py`

1. Spanish module docstring: purpose + requirement/decision ID in the first line, rationale paragraphs, `Uso::` code block where the module has a public entry point.
2. `from __future__ import annotations` — mandatory, immediately after the docstring (C-7).
3. Explicit `__all__` right after the imports, sorted, in library modules (test modules omit it).
4. Repo root via `Path(__file__).resolve().parent.parent`, never `cwd`.
5. Ruff: line-length 100, double quotes, 4 spaces. `uv run mypy verification` by hand — `verification/` is outside `[tool.mypy] files` (P-9).

### Fid allocation

**Source:** `main_iol.py:182-220` (canonical), `main_market_data.py:264-282` (twin)
**Apply to:** `main_higyrus.py`, `main_matriz.py`, `main_ambito_financiero.py`, and the handler (which receives the driver's `_next_fid` as an injected callable — **one allocator per package process**, never two).

### Finding emission

**Source:** `verification/findings.py:583-598` + the call sites at `main_higyrus.py:653-664` (AUTH), `:668-679` (ERROR-MAP), `:683-694` (SHAPE)
**Apply to:** the handler and every retained probe branch. Keyword-only, `_PKG` positional first, `base_url=` passed where available, `market_hours=` populated for the matriz session run (P-12).

### Exception-handler ladder in a probe

**Source:** `main_higyrus.py:648-710`
**Apply to:** every probe the decorator wraps. Order: `<Pkg>AuthError` → `<Pkg>APIError` → decode error (now via decorator) → `_RESIDUAL_PROBE_EXCEPTIONS`. Never `except Exception` in higyrus/matriz.

### Logger discipline

**Source:** `verification/test_logging_root_unchanged.py:39-67`
**Apply to:** `verification/divergences.py` install/uninstall context manager. Attach to `logging.getLogger("<pkg>")` only; `setLevel(logging.INFO)` (not `DEBUG` — `DEBUG` admits `_transport.py`'s redaction-sensitive request records); restore prior level and remove the handler on exit.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `.planning/phases/33-.../33-CENSUS.md` | doc artifact | — | New artifact kind. Closest precedent for tone/table shape is `.planning/phases/29-decoder-observable/29-SIZING.md` (per-package floor table); RESEARCH Pattern 6 (lines 610-638) supplies the exact column set. |
| `.planning/phases/33-.../33-LITERALS.md` | doc artifact | — | New artifact kind. RESEARCH Pattern 5 (lines 570-608) supplies the evidence-source table; no in-repo document has this shape. |

---

## Notes for the Planner

- **`verification/` is red today** — `19 failed, 362 passed, 19 errors in 828s`, 17+17 of which are one stale file (`verification/test_matriz_sweep_snapshot.py`, calls `probe_get_segments()` with no `client` arg). Baseline it in Wave 0; never gate a task on an unqualified `uv run pytest` or a full `pytest verification` run (P-13).
- **`verification/test_matriz_sweep_snapshot.py` is the canary for this phase's own refactor** — it calls probes directly and will be re-broken by the decorator. Audit every harness test that calls a `probe_*` function before and after applying the decorator.
- **Never edit any `_decode.py` copy** — `tools/check_decode_intactness.py::CANONICAL_DIGEST` pins all five, and the `lint` CI job fails on any drift.
- **Strict-mode survival is not uniform** (P-4): higyrus + matriz die today (0 `except Exception`); iol (12), market-data (55) and ambito (6) survive but misclassify. Two distinct task shapes, not five identical edits.

## Metadata

**Analog search scope:** `verification/` (58 files), `main_*.py` (6 drivers), `packages/*/tests/`, `packages/*/src/*/`
**Files scanned:** ~70 listed, 9 read in full or in targeted ranges
**Pattern extraction date:** 2026-08-26
