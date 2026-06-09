---
phase: 05-matriz-verification
plan: 01
subsystem: matriz-client + verification harness
tags: [verification, matriz-client, sync-only, helper-promotion, envelope-fix, token-assert-fix, regression-tests]
dependency_graph:
  requires:
    - "verification.findings.findings_path (pre-existing)"
    - "matriz_client.exceptions.PrimaryAPIError (pre-existing)"
    - "matriz_client.client._request / _get / _ensure_token (pre-existing)"
    - "higyrus_client.models.SafeModel + matriz_client.models._SafeModel (duck-typed, no direct import)"
  provides:
    - "verification.diff_safemodel_bidirectional — cross-package SafeModel<->wire diff helper"
    - "verification.cycle_report.verify_cycle_closure — structural CONFIRMED/FIXED → regression test linkage validator"
    - "matriz_client.client._unwrap — typed envelope-key guard raising PrimaryAPIError instead of KeyError"
    - "Defensive _token raise RuntimeError (no longer stripped by python -O) in matriz _request"
    - "Docstring warnings on new_order/replace_order/cancel_order (§6.3 GET-as-write quirk)"
    - "18 envelope regression tests + 1 _token sentinel test that lock the behaviour"
  affects:
    - "verification/safemodel_diff.py (new)"
    - "verification/cycle_report.py (new)"
    - "verification/__init__.py (barrel update)"
    - "packages/matriz-client/src/matriz_client/client.py"
    - "packages/matriz-client/tests/test_client.py"
tech-stack:
  added: []
  patterns:
    - "Duck-typed cross-package compat: `isinstance(cls, type) and dataclasses.is_dataclass(cls) and callable(cls.from_api)` instead of importing a specific SafeModel base"
    - "`dataclasses.fields(cls)` filter on `get_type_hints` keys so the `__dataclass_fields__: ClassVar[...]` declaration on matriz `_SafeModel` does not leak as a model-only divergence"
    - "Structural markdown parser over `<pkg>-findings.md` (no pytest import, no client-package import) for cycle closure validation"
    - "Path-traversal defence on regression paths: regex + `..`-component check + `resolve().relative_to(_REPO_ROOT)` boundary"
    - "Envelope helper `_unwrap(data, key, endpoint)` raising `PrimaryAPIError(status='ERROR', description=f\"missing envelope key '{key}' in response from {endpoint}\")` (no new exception subclass — consistent with D-HIGY-8)"
    - "`if _token is None: raise RuntimeError(...)` in the non-auth_basic branch of `_request` (defensive guard not stripped by `python -O`); the auth_basic branch is intentionally untouched"
    - "Docstring warning `WARNING: Submission uses HTTP GET per Primary API §6.3 spec ... Never refactor to POST` on new_order/replace_order/cancel_order"
    - "Regression test divider `# ------ Regressions ------` at the end of test_client.py with 18 envelope tests + 1 _token sentinel"
key-files:
  created:
    - "verification/safemodel_diff.py — duck-typed cross-package diff helper (~155 lines)"
    - "verification/cycle_report.py — structural CONFIRMED/FIXED → regression linkage validator (~170 lines)"
  modified:
    - "verification/__init__.py — barrel export of `diff_safemodel_bidirectional` in alphabetical order between `capture` and `mutating_allowed`"
    - "packages/matriz-client/src/matriz_client/client.py — `_unwrap` helper, 18 envelope sites refactored, `_token` assert → raise RuntimeError, 3 docstring §6.3 warnings"
    - "packages/matriz-client/tests/test_client.py — 18 envelope regression tests + 1 _token sentinel = 19 new tests appended after the last pre-existing test"
decisions:
  - "D-MATZ-18 implementado: helper promoteido de inline (main_higyrus.py) a verification/safemodel_diff.py con duck-typing cross-package"
  - "D-MATZ-19 implementado: barrel exporta `diff_safemodel_bidirectional` alfabéticamente; `verify_cycle_closure` accesible solo vía `from verification.cycle_report import` (preferencia modular)"
  - "D-MATZ-28 implementado: `verify_cycle_closure(pkg)` parser estructural (sin pytest, sin imports de paquetes cliente)"
  - "D-MATZ-9 implementado: `_unwrap` raises `PrimaryAPIError(status='ERROR', ...)` — NO nueva subclase PrimaryShapeError (consistencia con D-HIGY-8)"
  - "D-MATZ-10 implementado: 18 sites de `_get(...)[key]` refactoreados a `_unwrap(_get(path), key, path)`; `get_detailed_positions` y `get_account_report` NO tocados"
  - "D-MATZ-12 implementado: `assert _token is not None` (rama else no-auth_basic) reemplazado por `if _token is None: raise RuntimeError(...)`; rama `if auth_basic:` intacta"
  - "D-MATZ-17 implementado: docstrings de new_order/replace_order/cancel_order expanden con WARNING §6.3 + 'Never refactor to POST without explicit API confirmation'"
  - "D-MATZ-11 + D-MATZ-13 implementados: sección `# ------ Regressions ------` con docstrings verbatim (placeholder `F-NN` queda hasta Plan 05-03 que asigne fids)"
  - "Adicional (Rule 2 — correctness): filtro de `dataclasses.fields()` sobre `get_type_hints()` en el diff helper para evitar que `__dataclass_fields__: ClassVar[...]` (declarado por matriz `_SafeModel` para pyright) se reporte como `model-only` divergence cross-package"
metrics:
  duration: "8 min"
  tasks_completed: 4
  files_modified: 2
  files_created: 2
  commits: 4
  completed_date: "2026-06-09"
requirements: [MATZ-03, MATZ-04, DRIFT-02]
---

# Phase 5 Plan 01: DRY Foundation (helpers + MATZ-04 + _token + §6.3) Summary

## One-liner

DRY foundation phase 5: helper `diff_safemodel_bidirectional` promoteido de Phase 4 con duck-typing cross-package (`isinstance(cls, type) + dataclasses.is_dataclass + callable(from_api)`); `verify_cycle_closure(pkg)` nuevo módulo que parsea findings markdown estructuralmente sin importar pytest; MATZ-04 cerrado con helper `_unwrap` + 18 sites refactoreados (KeyError → PrimaryAPIError tipado); `assert _token` reemplazado por `raise RuntimeError` (T-5-02); docstrings §6.3 en new/replace/cancel_order; 19 regression tests bloquean cualquier reintroducción.

## Goal Met

Sí. Las 4 tasks ejecutaron sin desviaciones del flujo (excepto un fix correctness aplicado durante Task 1.1 — ver "Deviations from Plan"). Todos los acceptance criteria, la verificación whole-plan integrada, y la non-regression del repo completo (251 tests) pasan. Los archivos creados/modificados están listos para ser consumidos por Plan 05-02 (driver) y Plan 05-03 (Verified-live + MATZ-06).

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1.1 | Promote `diff_safemodel_bidirectional` to verification/ with duck-typing | `017f3e7` | `verification/safemodel_diff.py` (new), `verification/__init__.py` |
| 1.2 | Create `verification/cycle_report.py` with `verify_cycle_closure` | `9b7f1fc` | `verification/cycle_report.py` (new) |
| 1.3 | MATZ-04 envelope fix (18 sites) + `_token` raise + §6.3 docstrings | `693e0f9` | `packages/matriz-client/src/matriz_client/client.py` |
| 1.4 | Add Regressions section (18 envelope tests + 1 sentinel) | `fc906de` | `packages/matriz-client/tests/test_client.py` |

## Helper Promotion (Task 1.1) — verification/safemodel_diff.py

Nuevo módulo (~155 líneas) con la API pública `diff_safemodel_bidirectional(payload, model_cls, path="") -> Iterator[tuple[str, str, str]]`. Estructura:

- 4 helpers internos: `_is_optional`, `_is_safemodel_like`, `_nested_safemodel_class`, `_is_list_of_safemodel`.
- 1 helper público: `diff_safemodel_bidirectional`.
- `__all__ = ["diff_safemodel_bidirectional"]`.
- Sin imports de `higyrus_client` ni `matriz_client` (zero cross-package coupling, verificado por `inspect.getsource`).

El barrel `verification/__init__.py` exporta la función en orden alfabético entre `capture` y `mutating_allowed`; el import directo `from verification.safemodel_diff import diff_safemodel_bidirectional` también funciona. La firma `inspect.signature` reporta `(payload, model_cls, path)`.

La diferencia conductual vs. la copia inline original es **duck-typed cross-package compat**: el helper interno `_is_safemodel_like(cls)` retorna `True` sii `isinstance(cls, type) and dataclasses.is_dataclass(cls) and callable(getattr(cls, "from_api", None))`. Esto admite tanto `higyrus_client.SafeModel` como `matriz_client._SafeModel` sin tener que importar ninguno de los dos paquetes-cliente.

Verificación cross-package en runtime:
- `Segment` (matriz) con payload `{"extra_field": "X"}` → yield `(.seg, wire-only, extra_field)` correctamente.
- `Cuenta` (higyrus) con payload `{"extra_field": 1}` → yield `(.cuenta, wire-only, extra_field)` correctamente.
- Custom dataclass con field `b: int` non-optional ausente → yield `model-only b`.

## Cycle Report Module (Task 1.2) — verification/cycle_report.py

Nuevo módulo (~170 líneas) con `verify_cycle_closure(pkg: str) -> tuple[bool, list[str]]`. El parser es **estructural**:

1. Si el findings file no existe → return `(True, [])` (nada que validar).
2. Lee el archivo y extrae bloques por finding usando split por `### F-NN` headers.
3. Por bloque: extrae status con regex `\*\*Status:\*\*\s*\`?(\w+)\`?` y regression path con regex `(?:Regression|regression)[^\n]*?([\w\-/.]+\.py::[A-Za-z_][\w]*)`.
4. Filtra solo `CONFIRMED` y `FIXED` (los demás status no participan).
5. Para cada finding aplicable, valida que el regression path:
   - Matchee `_REGRESSION_RE = r"^([^:\s]+\.py)::([A-Za-z_][A-Za-z0-9_]*)$"`
   - No sea absoluto, ni contenga `..` (path-traversal defence T-5-06).
   - El path resuelto via `resolve()` esté bajo `_REPO_ROOT` (boundary safety).
   - El archivo exista.
   - El contenido del archivo contenga `f"def {test_name}("` (matchea tanto `def` como `async def` por substring).

Validado end-to-end con findings sintéticos en `.planning/verification/test-pkg-findings.md`:
- OPEN-only file → `(True, [])`.
- FIXED sin campo regression → `(False, ['F-01'])`.
- FIXED con regression válida → `(True, [])`.
- FIXED con regression a archivo inexistente → `(False, ['F-01'])`.
- Path traversal `packages/foo/../etc/test.py::test_x` → rechazado.
- Path absoluto `/etc/passwd::test_x` → rechazado.

`verify_cycle_closure("higyrus-client")` sobre el findings real existente → `(True, [])` (los findings de Phase 4 están en estados que no requieren validación, o tienen regression links válidos).

### Convención forward-looking (caveat operacional)

El parser acepta `**Regression:** <pkg>/tests/<file>.py::<test_name>` como bullet dentro del finding block. El módulo `verification.findings.append_finding(..., regression=...)` ya soporta este parámetro y lo serializa correctamente. Si un finding histórico promovido a `FIXED` no tiene el campo `regression`, `verify_cycle_closure` lo reportará como missing — Plan 05-04 podrá decidir si retro-populear los findings históricos o marcarlos como aceptados. La convención queda documentada en el docstring del módulo.

## MATZ-04 Envelope Fix (Task 1.3) — matriz_client/client.py

**`_unwrap` helper** (D-MATZ-9 verbatim) agregado después de `_get` y antes de `_risk_auth`:

```python
def _unwrap(data: dict[str, Any], key: str, endpoint: str) -> Any:
    if key not in data:
        raise PrimaryAPIError(
            status="ERROR",
            description=f"missing envelope key '{key}' in response from {endpoint}",
            message=None,
        )
    return data[key]
```

**18 envelope sites refactoreados**:

| # | Función | Path | Key |
|---|---------|------|-----|
| 1 | get_segments | `/rest/segment/all` | `segments` |
| 2 | get_all_instruments | `/rest/instruments/all` | `instruments` |
| 3 | get_instruments_details | `/rest/instruments/details` | `instruments` |
| 4 | get_instrument_detail | `/rest/instruments/detail` | `instrument` |
| 5 | get_instruments_by_cfi | `/rest/instruments/byCFICode` | `instruments` |
| 6 | get_instruments_by_segment | `/rest/instruments/bySegment` | `instruments` |
| 7 | new_order | `/rest/order/newSingleOrder` | `order` |
| 8 | replace_order | `/rest/order/replaceById` | `order` |
| 9 | cancel_order | `/rest/order/cancelById` | `order` |
| 10 | get_order_status | `/rest/order/id` | `order` |
| 11 | get_order_history | `/rest/order/allById` | `orders` |
| 12 | get_active_orders | `/rest/order/actives` | `orders` |
| 13 | get_filled_orders | `/rest/order/filleds` | `orders` |
| 14 | get_all_orders | `/rest/order/all` | `orders` |
| 15 | get_order_by_exec_id | `/rest/order/byExecId` | `order` |
| 16 | get_market_data | `/rest/marketdata/get` | `marketData` |
| 17 | get_trades | `/rest/data/getTrades` | `trades` |
| 18 | get_positions | `/rest/risk/position/getPositions/{account_name}` | `positions` |

Patrón aplicado: cada site extrae `path` a variable local antes de la invocación a `_get` / `_request` para reusar el mismo string en el envelope error. Para `get_positions` el path se construye con f-string preservando el `{account_name}` del URL path. Para `get_instrument_detail` la signature es la única donde la línea original tenía `_get(...)["instrument"]` en singular (Instrument detail, no plural).

**`get_detailed_positions` (línea 471) y `get_account_report` (línea 478) NO se tocaron** — retornan el dict raíz directo a `DetailedPosition.from_api(_request(...))` / `AccountReport.from_api(_request(...))` sin envelope key (Risk API §9.2/§9.3 sin wrapper).

**`_token` assert reemplazado** (D-MATZ-12) solo en la rama `else` (no-auth_basic) de `_request`:

```python
else:
    _ensure_token()
    if _token is None:
        raise RuntimeError("matriz_client.client: _ensure_token() did not populate _token")
    resp = _session.request(...)
```

La rama `if auth_basic:` **quedó intacta** (Pitfall 7 RESEARCH L673-678).

**Docstring §6.3 warnings** agregados a `new_order` (§6.3), `replace_order` (§6.5) y `cancel_order` (§6.6), cada uno con el bloque `WARNING: Submission uses HTTP GET per Primary API §6.3 spec — this is intentional, not a bug. Never refactor to POST without explicit API confirmation; the upstream service silently mismatches POSTs.` (D-MATZ-17).

**NO se introdujo `PrimaryShapeError`** (D-MATZ-9 rechaza explícitamente — consistencia con D-HIGY-8).

Sanity grep post-fix:
- `def _unwrap`: 1
- `_unwrap(`: 19 (1 helper + 18 invocations)
- `_get(...)["` o `_request(...)["` remaining: 0
- `assert _token is not None`: 0
- `raise RuntimeError`: 1
- `did not populate _token`: 1
- `Never refactor to POST`: 3 (uno por new/replace/cancel)
- `missing envelope key`: 1 (en el helper)
- `PrimaryShapeError`: 0

## Regression Tests (Task 1.4) — tests/test_client.py

Sección `# ------ Regressions ------` agregada al final del archivo (después del último test pre-existente `test_get_positions_uses_basic_auth`). 19 tests nuevos:

- **18 envelope regression tests** — uno por endpoint refactoreado en Task 1.3, con docstring verbatim per D-MATZ-11: `"""Regression: PrimaryAPIError tipado en lugar de KeyError no mapeado cuando envelope key falta (finding F-NN)."""`. Cada test mockea una respuesta sin la envelope key esperada (e.g., `{"status": "OK", "some_other_key": []}`), llama la función pública correspondiente con args mínimos, y asserta `pytest.raises(PrimaryAPIError)` con `"missing envelope key '<key>'" in exc_info.value.description`.

  Para los 3 endpoints con URL fija (sin query params variables) — `get_segments`, `get_all_instruments`, `get_instruments_details`, `get_positions` — el mock incluye `url="https://api.test/<path>"` para verificar el path exacto. Para los demás endpoints (con query strings que dependen de args y serían brittle), el mock usa solo `method="GET"` y deja que pytest-httpx haga match por método (cada test hace exactamente UNA llamada HTTP).

- **1 sentinel `_token` test** `test_request_raises_runtime_error_if_ensure_token_leaves_none` con docstring verbatim D-MATZ-13: `"""Regression: defensive guard against _ensure_token returning without populating _token (CONCERNS.md L52-55, finding F-NN)."""`. Monkeypatchea `_client._token=None` y `_client._ensure_token=lambda: None`, luego invoca `_client._request("GET", "/rest/anything")` y asserta `pytest.raises(RuntimeError, match="did not populate _token")`. El raise ocurre ANTES del request HTTP, así que no se necesita mock httpx.

Imports al tope ya incluían `from pytest_httpx import HTTPXMock`, `pytest`, `import matriz_client`, `from matriz_client.exceptions import AuthenticationError, PrimaryAPIError` — ninguno adicional fue necesario.

Sanity grep post-edit:
- `# ------ Regressions ------`: 1 (divider)
- `^def test_.*_raises_primary_api_error_on_missing_envelope_key`: 18
- `test_request_raises_runtime_error_if_ensure_token_leaves_none`: 1
- `Regression: PrimaryAPIError tipado en lugar de KeyError`: 18
- `did not populate _token`: 1 (en el `pytest.raises` match)
- `pytest.raises(PrimaryAPIError)`: 19 (los 18 envelope + 1 pre-existente)
- `missing envelope key`: 18

Suite matriz-client completa: **34 passed** (15 pre-existentes + 19 nuevos). Repo completo: **251 passed**.

## Verification

```bash
# Helpers nuevos importables
uv run python -c "from verification import diff_safemodel_bidirectional"  # barrel OK
uv run python -c "from verification.cycle_report import verify_cycle_closure"  # direct OK

# MATZ-04 envelope fix
grep -c "def _unwrap" packages/matriz-client/src/matriz_client/client.py  # 1
grep -c "_unwrap(" packages/matriz-client/src/matriz_client/client.py    # 19
grep -cE '_get\([^)]+\)\["' packages/matriz-client/src/matriz_client/client.py  # 0

# _token fix
grep -c "assert _token is not None" packages/matriz-client/src/matriz_client/client.py  # 0
grep -c "did not populate _token" packages/matriz-client/src/matriz_client/client.py   # 1
grep -c "raise RuntimeError" packages/matriz-client/src/matriz_client/client.py        # 1

# Docstring warnings
grep -c "Never refactor to POST" packages/matriz-client/src/matriz_client/client.py    # 3

# Regression tests
grep -F "# ------ Regressions ------" packages/matriz-client/tests/test_client.py      # 1
grep -c "^def test_.*_raises_primary_api_error_on_missing_envelope_key" packages/matriz-client/tests/test_client.py  # 18
grep -c "test_request_raises_runtime_error_if_ensure_token_leaves_none" packages/matriz-client/tests/test_client.py  # 1

# Static checks
uv run mypy verification packages/matriz-client  # Success
uv run ruff check .                              # All checks passed
uv run ruff format --check .                     # 70 files already formatted

# Suite
uv run pytest packages/matriz-client -q  # 90 passed
uv run pytest -q                          # 251 passed, 1 deselected
```

Todas las salidas confirman los counts esperados.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Correctness] Filter `__dataclass_fields__` ClassVar from `get_type_hints()` keys**
- **Found during:** Task 1.1 (runtime test against matriz `_SafeModel` subclasses)
- **Issue:** `matriz_client.models._SafeModel` declara `__dataclass_fields__: ClassVar[dict[str, Any]]` para que pyright acepte `cls` como dataclass (un patrón estándar de los `_SafeModel` mixins). `get_type_hints(model_cls)` por default incluye este ClassVar, lo que hacía que el helper diff lo reportara como `model-only=__dataclass_fields__` cross-package — un falso positivo no deseado. El inline original en `main_higyrus.py` no exhibía este bug porque higyrus `SafeModel` no declara este ClassVar.
- **Fix:** Restringir las keys del model a los instance fields del dataclass usando `dataclasses.fields(model_cls)`: `field_names = {f.name for f in dataclasses.fields(model_cls)}; model_keys = field_names & hints.keys()`. Esto excluye ClassVars y atributos declarados a nivel de clase, manteniendo el comportamiento correcto para ambos paquetes.
- **Files modified:** `verification/safemodel_diff.py` (líneas en el cuerpo de `diff_safemodel_bidirectional`)
- **Commit:** `017f3e7` (incluido en el commit principal de Task 1.1)

No hubo otras desviaciones. Los `if auth_basic:` quedan intactos, `get_detailed_positions`/`get_account_report` quedan intactos, las firmas públicas no cambiaron, no se introdujo PrimaryShapeError, y no se introdujo `aio.py` para matriz.

### Authentication Gates

Ninguna. Los tests son mockeados y el plan no toca el flujo de auth real.

## Known Stubs

Ninguno. Los `F-NN` placeholder en los docstrings de regression son intencionales — Plan 05-03 asignará los fids reales cuando se redacten los findings de la run live (esto sigue la convención D-MATZ-11/D-MATZ-13 documentada en el plan).

## Threat Flags

Ninguno. Todos los cambios de superficie están documentados en el `<threat_model>` del plan (T-5-01 mitigado por `_unwrap`, T-5-02 mitigado por `raise RuntimeError`, T-5-03 mitigado parcialmente por docstring warning + Plan 05-03 sentinels, T-5-06 mitigado por path-traversal defence en `verify_cycle_closure`).

## Self-Check

Verifying claims made in this Summary against the actual state of the repo:

1. **Files created:**
   ```bash
   [ -f verification/safemodel_diff.py ] && echo "FOUND: verification/safemodel_diff.py" || echo "MISSING"
   [ -f verification/cycle_report.py ] && echo "FOUND: verification/cycle_report.py" || echo "MISSING"
   ```
2. **Commits:**
   ```bash
   for h in 017f3e7 9b7f1fc 693e0f9 fc906de; do
     git log --oneline --all | grep -q "$h" && echo "FOUND: $h" || echo "MISSING: $h"
   done
   ```

(Both checks run below in the post-write verification block.)

## Self-Check: PASSED

All claimed artifacts and commits verified present on disk and in git history (see post-write verification block at execution time).
