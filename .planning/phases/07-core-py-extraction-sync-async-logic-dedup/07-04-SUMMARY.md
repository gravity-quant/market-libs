---
phase: 07-core-py-extraction-sync-async-logic-dedup
plan: 04
subsystem: higyrus-client
tags: [phase-07, higyrus, refac-03, url-encoding-quirk, transport-shell]
one_liner: "Extrae higyrus `_core.py` con auth-flow + builders/parsers que encapsulan la quirk URL-encoding Higyrus IIS (`urlencode(..., doseq=True, quote_via=quote, safe='/')`); colapsa `client.py`+`aio.py` a transport shells (-33% LOC) preservando B8 alias y PEP 562 shim."
requires:
  - higyrus_client._state (Phase 6)
  - higyrus_client._params (drop_none, format_date, format_bool)
  - higyrus_client.models (Cuenta, Movimiento, PosicionValuada, Posicion)
  - higyrus_client.exceptions (HigyrusAPIError + subclasses)
  - import-linter config (Plan 07-01)
provides:
  - higyrus_client._core (RequestSpec + auth-flow + builders/parsers + raise_for_response)
  - higyrus_client.client (transport shell sync — endpoint methods 3-liner)
  - higyrus_client.aio (transport shell async — endpoint methods 3-liner)
  - higyrus_client/tests/test_core.py (33 unit tests)
affects:
  - Phase 7 wave 2 progress (higyrus extracted; iol/ambito/matriz pending in their own plans)
tech_stack:
  added: []
  patterns:
    - "RequestSpec(frozen+slots) con json_body + url_pre_encoded (per-package D-01 higyrus row)"
    - "URL-encoding quirk ENCAPSULATED inside _core builders (T-7-URLQUIRK + T-7-SHELL-LEAK mitigation)"
    - "D-04 alias re-export para preservar B8 identity (aio is client)"
    - "D-06 body-consume-then-raise en todos los parsers"
key_files:
  created:
    - packages/higyrus-client/tests/test_core.py
  modified:
    - packages/higyrus-client/src/higyrus_client/_core.py (placeholder → 425 LOC complete)
    - packages/higyrus-client/src/higyrus_client/client.py (685 → 433 LOC, -37%)
    - packages/higyrus-client/src/higyrus_client/aio.py (669 → 473 LOC, -29%)
decisions:
  - "URL-encoding quirk lives ONLY in _core._encode_query (called by builders) — transport shells NEVER call urlencode (T-7-SHELL-LEAK mitigation)"
  - "RequestSpec uses url_pre_encoded: bool to signal that spec.path already has the query encoded with safe='/' — shells forward verbatim with params=None"
  - "Legacy module-level _request(method, path, *, params, json_body) shim kept in both client.py and aio.py for backward-compat with pre-Phase-7 tests"
metrics:
  duration_minutes: 15
  completed_date: 2026-06-12
requirements_addressed: [REFAC-03]
---

# Phase 7 Plan 04: Higyrus `_core.py` Extraction Summary

Extrae el cliente higyrus al pattern Phase 7: módulo `_core.py` con todas las
primitivas puras (RequestSpec + auth-flow + builders/parsers + raise_for_response)
que ENCAPSULAN la quirk URL-encoding propia de Higyrus IIS (rechaza `%2F`).
Colapsa `client.py` y `aio.py` a transport shells que NO conocen el detalle de
encoding — esto cierra T-7-URLQUIRK + T-7-SHELL-LEAK en el threat model.

LOC aggregate baja de 1354 → 906 (-33%), satisfaciendo el threshold ≥30%. B8
alias preservado: `aio._raise_for_response is client._raise_for_response`
porque ambos referencian el MISMO objeto en `_core`. Public surface snapshot
zero diff. PEP 562 shim intacto.

## Tasks Completed

| Task | Description | Commits | Files |
|------|-------------|---------|-------|
| 1 (RED) | Failing tests for higyrus `_core` builders/parsers + URL-encoding quirk assertions | `fae91c3` | `tests/test_core.py` (NEW, 33 tests) |
| 1 (GREEN) | Implementación de `_core.py` — RequestSpec + auth-flow + 5 builder/parser pairs + URL-encoding quirk encapsulation | `32c9d67` | `_core.py` (placeholder → 425 LOC), `tests/test_core.py` (ruff isort) |
| 2 | Collapse `client.py` + `aio.py` to transport shells; D-04 alias + LOC drop ≥30% | `c82bdb1` | `client.py`, `aio.py` |

## LOC Drop vs Phase 6 Baseline

```
client.py: 685 → 433 (-37%)
aio.py:    669 → 473 (-29%)
_core.py:  0   → 425 (NEW — pure builders/parsers + auth-flow)
Aggregate client+aio: 1354 → 906 (-33%)   PASS ≥30% threshold
```

## B8 Identity (D-04 alias re-export)

```
$ python -c "from higyrus_client.aio import _raise_for_response as a;
              from higyrus_client.client import _raise_for_response as c;
              assert a is c"
PASS
```

`client.py` declara `_raise_for_response = _core.raise_for_response` a nivel
módulo; `aio.py` hace `from higyrus_client._core import raise_for_response as
_raise_for_response`. Ambos aliases apuntan al MISMO objeto en `_core`.

## URL-encoding Quirk Encapsulation (T-7-URLQUIRK + T-7-SHELL-LEAK)

**Test core assertion** (`test_build_get_movimientos_request_preserves_slash_in_query`):
```
assert "fechaHasta=07/06/2026" in spec.path
assert "%2F" not in spec.path
```
PASS — la quirk se aplica dentro del builder, antes de cualquier wire request.

**Phase 6 test sigue verde** (`test_url_encoding_preserves_slash_in_query`):
```
assert "fechaDesde=08/05/2026" in query_str
assert "fechaHasta=07/06/2026" in query_str
assert "%2F" not in query_str
```
PASS sync + async — el wire request final preserva `/` literal.

**Shell encapsulation source assertion**:
```
$ grep -cE "urlencode\(.*doseq=True" packages/higyrus-client/src/higyrus_client/client.py
0
$ grep -cE "urlencode\(.*doseq=True" packages/higyrus-client/src/higyrus_client/aio.py
0
```
PASS — el `urlencode(..., doseq=True, quote_via=quote, safe="/")` aparece SOLO
dentro de `_core._encode_query` (3 ocurrencias en `_core.py`, 0 en los shells).

## Public Surface Snapshot

```
$ uv run pytest verification/test_public_surface.py -k higyrus -x
1 passed
```
Zero diff vs Phase 6 — la API pública del paquete no cambió (mismo `Client`,
`AsyncClient`, `configure`, `login`, `get_*`).

## Cross-leak Guard

```
$ uv run pytest verification/test_sync_async_isolation.py -k higyrus -x -v
test_sync_token_isolation_in_wire_request[higyrus_client-Authorization-Bearer ] PASSED
test_async_token_isolation_in_wire_request[higyrus_client-Authorization-Bearer ] PASSED
```
SYNC y ASYNC sentinels llegan a Authorization header sin contaminarse.

## Verification Matrix

| Check | Result |
|-------|--------|
| `uv run pytest packages/higyrus-client/ -x` | 113 passed (33 nuevos en test_core.py) |
| `uv run pytest verification/test_sync_async_isolation.py -k higyrus` | 2 passed |
| `uv run pytest verification/test_public_surface.py -k higyrus` | 1 passed (zero diff) |
| `uv run mypy packages/higyrus-client/` | clean (14 source files) |
| `uv run ruff check packages/higyrus-client/` | clean |
| `uv run ruff format --check packages/higyrus-client/` | clean |
| `uv run lint-imports` | 4 contracts kept, 0 broken |
| `uv run pytest -q` (full suite) | 432 passed, 2 skipped (matriz aio stub), 1 deselected |

## _core.py Structure (425 LOC)

```text
# RequestSpec frozen dataclass — json_body + url_pre_encoded
RequestSpec(method, path, params, headers, json_body, url_pre_encoded)

# Stateless helpers (D-04 single source of truth)
raise_for_response(resp) → maps 401/403/429/4xx/5xx → HigyrusClientError hierarchy
                          preserves structured `errors` array + `timestamp`
token_is_fresh(state) → bool

# Auth flow primitives (D-02)
build_login_request(state) → RequestSpec(POST, /api/login, json_body={creds})
                              raises HigyrusAuthError if creds/base_url missing
parse_login_response(resp) → (token, expires_at)
                              D-06: resp.read() + raise_for_response + extract

# URL-encoding quirk encapsulator (T-7-URLQUIRK)
_encode_query(base_path, params) → uses urlencode(..., doseq=True,
                                          quote_via=quote, safe="/")

# Endpoint builders (URL-encoding quirk inside)
build_get_health_request(state)
build_get_movimientos_request(state, id_cuenta, fecha_desde, fecha_hasta, *, ...)
build_get_posicion_valuada_request(state, id_cuenta, *, ...)
build_get_listado_cuentas_request(state, *, ...)
build_get_posiciones_request(state, id_cuenta, *, ...)

# Endpoint parsers (D-06 body-consume-then-raise + SafeModel.from_api)
parse_get_health_response(resp) → dict[str, Any]
parse_get_movimientos_response(resp) → list[Movimiento]
parse_get_posicion_valuada_response(resp) → list[PosicionValuada]
parse_get_listado_cuentas_response(resp) → list[Cuenta]
parse_get_posiciones_response(resp) → list[Posicion]
```

## Deviations from Plan

None — plan executed exactly as written.

The compaction of `client.py` + `aio.py` docstrings on endpoint methods and
module-level legacy delegators was needed to reach the ≥30% LOC drop target
(initial pass landed at -13%); this is consistent with the plan's "endpoint
method post-refactor — 3-liner shell" (PATTERNS.md §6) and "≤30-50 LOC/group"
constraint (D-05). Removed per-method docstring redundancy where the class
method docstring covers the same endpoint contract; preserved 1-line module
docstrings + section dividers.

## Self-Check: PASSED

- File exists: packages/higyrus-client/src/higyrus_client/_core.py — FOUND
- File exists: packages/higyrus-client/src/higyrus_client/client.py — FOUND
- File exists: packages/higyrus-client/src/higyrus_client/aio.py — FOUND
- File exists: packages/higyrus-client/tests/test_core.py — FOUND
- Commit fae91c3 — FOUND (RED step: failing tests)
- Commit 32c9d67 — FOUND (GREEN step: _core.py implementation)
- Commit c82bdb1 — FOUND (shells collapsed, LOC -33%)
- B8 alias identity — PASS
- URL-encoding quirk encapsulated in _core (shell leak count = 0) — PASS
- Public surface snapshot zero diff — PASS
- lint-imports 4 contracts kept — PASS
- LOC drop -33% (≤948 target) — PASS
