---
phase: 07-core-py-extraction-sync-async-logic-dedup
fixed_at: 2026-06-12T18:30:00Z
review_path: .planning/phases/07-core-py-extraction-sync-async-logic-dedup/07-REVIEW.md
iteration: 1
findings_in_scope: 6
fixed: 6
skipped: 0
status: all_fixed
---

# Phase 07: Code Review Fix Report

**Fixed at:** 2026-06-12T18:30:00Z
**Source review:** .planning/phases/07-core-py-extraction-sync-async-logic-dedup/07-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope (critical_warning): 6 (CR-01, CR-02, WR-01, WR-02, WR-03, WR-04)
- Fixed: 6
- Skipped: 0
- Info findings (IN-01, IN-02): fuera de scope; IN-02 (test faltante) quedó cubierto colateralmente por el regression test de CR-01.

## Fixed Issues

### CR-01: `higyrus_client._core.raise_for_response` siempre levanta — no es no-op para 2xx

**Files modified:** `packages/higyrus-client/src/higyrus_client/_core.py`, `packages/higyrus-client/tests/test_core.py`
**Commit:** `af0a2ea`
**Applied fix:** Añadido guard `if not resp.is_error: return` al inicio de `raise_for_response` para hacerla no-op en 2xx/3xx, consistente con `ambito`/`iol`/`matriz`. Docstring actualizado para reflejar que el body-consume es responsabilidad del caller (D-06) — esto cierra también WR-01 en el mismo commit. Tests de regresión añadidos:
- `test_raise_for_response_does_not_raise_on_2xx` — verifica que 200 OK con body `{}` no levanta excepción.
- `test_raise_for_response_no_op_for_3xx` — verifica que 302 redirect tampoco levanta.

Estos tests cierran también IN-02 (ausencia de test `raise_for_response_does_not_raise_on_2xx`). B8 alias identity preservada: `aio._raise_for_response is client._raise_for_response is _core.raise_for_response` sigue True (verificado manualmente y por la suite).

### WR-01: `higyrus_client._core.raise_for_response` hace doble-decode del body en error path

**Files modified:** `packages/higyrus-client/src/higyrus_client/_core.py`
**Commit:** `af0a2ea` (combinado con CR-01)
**Applied fix:** Docstring de `raise_for_response` reescrito para dejar claro que el body ya fue consumido por `_consume_and_check` antes (D-06 caller responsibility) y que `resp.json()` acá es idempotente sobre el buffer en memoria. Combinar este fix con CR-01 en el mismo commit es natural porque ambos modifican la misma función.

### CR-02: `higyrus_client._core.parse_get_health_response` levanta en body vacío incluso en 204 esperado

**Files modified:** `packages/higyrus-client/src/higyrus_client/_core.py`, `packages/higyrus-client/tests/test_core.py`
**Commit:** `1a561df`
**Applied fix:** Reemplazado el `raise HigyrusAPIError(...)` para 204/empty body por `return {}`. Consistente con los list parsers que ya tratan 204 como `[]`. Si el servidor cambia 200→204 en `/api/health`, el cliente sigue funcionando sin romper. Tests de regresión añadidos:
- `test_parse_get_health_response_handles_204` — 204 No Content → `{}`.
- `test_parse_get_health_response_handles_empty_body_200` — 200 OK con body vacío → `{}`.

### WR-02: `test_sync_async_isolation.py` — URL para higyrus `get_listado_cuentas` asume encoding estándar pero el spec usa `url_pre_encoded=True`

**Files modified:** `packages/higyrus-client/tests/test_core.py`
**Commit:** `ad65ee3`
**Applied fix:** Añadido test `test_build_get_listado_cuentas_estado_with_slash_preserves_literal` que verifica que `estado="alta/test"` produce `estado=alta/test` en `spec.path` (sin `%2F`). Esto cierra el gap del isolation test que sólo ejercitaba el happy path. El contrato del quirk Higyrus IIS rechaza `%2F` ahora tiene cobertura dedicada también para `estado` (ya existía para movimientos/posicion_valuada/posiciones).

### WR-03: `higyrus_client.aio._request` shim toma el token bajo lock pero no verifica que sea non-None antes del assert

**Files modified:** `packages/higyrus-client/src/higyrus_client/aio.py`, `packages/higyrus-client/src/higyrus_client/client.py`
**Commit:** `e8eac02`
**Applied fix:** Reemplazado `assert token is not None` por `raise HigyrusAuthError(0, [{"title": "auth", "detail": "_ensure_token() returned without populating token"}])` tipado. Mirror exacto en `client.py` (sync) y `aio.py` (async) — la deuda dual sync/async es conocida del proyecto. Import `HigyrusAuthError` añadido a ambos módulos. Comentario explicativo del fix añadido en cada docstring.

### WR-04: `main_matriz.py` — `_envelope_probe` no protege contra `_auth_failed` para risk probes con `auth_basic_fn` cuando la auth falló

**Files modified:** `main_matriz.py`
**Commit:** `dde5823`
**Applied fix:** Cambiado el guard de `if _auth_failed:` a `if _auth_failed and auth_basic_fn is None:`. Las risk probes con `auth_basic_fn` (que usan HTTP Basic independiente del token) ya no se skipean por cascade cuando falla la auth del token X-Auth-Token — pueden ejecutarse y exponer errores potenciales en el Risk API. Comentario inline añadido explicando el rationale.

## Verificación post-fix

- `uv run pytest packages/higyrus-client/ verification/test_sync_async_isolation.py`: **125 passed, 1 skipped** (el skip es matriz aio.py REST stub pendiente para Phase 10, no relacionado con este fix).
- `uv run lint-imports`: **Contracts: 4 kept, 0 broken**.
- `uv run mypy packages/higyrus-client/`: **Success: no issues found in 14 source files**.
- `uv run mypy main_matriz.py`: **Success: no issues found in 1 source file**.
- `uv run ruff check packages/higyrus-client/ main_matriz.py`: **All checks passed!**.
- **B8 alias identity**: verificado en runtime — `aio._raise_for_response is client._raise_for_response is _core.raise_for_response` → True.

## Out of Scope (info findings)

- **IN-01** (`matriz_client._core.raise_for_response` delega en `resp.raise_for_status()` sin enrichment): info-only, fuera del scope `critical_warning`. El reviewer notó que la elección es consciente y no es un bug activo, sólo reduce la uniformidad de la jerarquía de excepciones.
- **IN-02** (test `raise_for_response_does_not_raise_on_2xx` faltante en higyrus): cubierto colateralmente por el regression test agregado para CR-01 en el commit `af0a2ea`.

---

_Fixed: 2026-06-12T18:30:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
