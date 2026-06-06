# Phase 4: Higyrus Verification — Research

**Researched:** 2026-06-06
**Domain:** Live-API verification of a SafeModel-based Python HTTP client (sync+async) with PII payloads, bidirectional schema diffing, and in-cycle dual `assert isinstance` fix
**Confidence:** HIGH (almost every claim is grounded in committed source files; the few unknowns are flagged in Open Questions)

## Summary

Phase 4 is the third end-to-end live verification cycle. Unlike Phase 2 (`ambito`, one stateless function, no auth) and Phase 3 (`iol`, OAuth dict-only client), Phase 4 targets `higyrus-client` — the only client where every endpoint result is parsed through a tolerant `SafeModel.from_api` that silently substitutes typed zeros for missing keys. A mocked test against `SafeModel` always passes; only a **bidirectional diff between the raw payload and `get_type_hints(Model)`** detects the FALSE PASS. The phase also exercises real PII (account holders, CBU, addresses, related persons) for the first time, so the redaction discipline established in Phase 3 must hold even tighter.

The lifecycle (driver → finding → in-cycle fix → mocked regression) is identical to Phases 2-3, and Phase 4 inherits the locked patterns verbatim: `append_finding` helper (DRY, hardened after `02-REVIEW.md`), `safe_print` two-layer redaction, single `asyncio.run` with `contextlib.suppress(Exception)` aclose, schema snapshot envelope D-21 with D-25 no-overwrite-on-drift, Verified-live + Regressions test sections per surface, `_auth_failed` cascade flag for SKIPPED downstream, and the opt-in 401 probe via `VERIFY_HIGYRUS_BAD_CREDS=1` mirrored from `VERIFY_IOL_BAD_CREDS=1`. Three things are net-new in Phase 4: (1) the **bidirectional `_diff_safemodel_bidirectional` recursive helper** over `get_type_hints` (D-HIGY-3/4/5); (2) **in-vivo verification of the known `drop_none` deviation** by inspecting `httpx.Request.url.params` sync vs async (D-HIGY-10 #13); (3) **the 10-site `assert isinstance(raw, list/dict)` → `HigyrusAPIError(0, [{"title":"shape mismatch", ...}])` fix-of-phase** with 10 mocked regression tests by surface (D-HIGY-7/8/9).

**Primary recommendation:** Replicate the Phase 2/3 three-plan horizontal slice (Plan 1 = fix HIGY-04 + 10 mocked regressions; Plan 2 = driver rewrite with 18 probes; Plan 3 = Verified-live sections + live run + commit 5 snapshots + findings file). Vertical-slice variant rejected — see *MVP Slice Composition* analysis below.

## User Constraints (from CONTEXT.md)

### Locked Decisions

The 18 numbered decisions D-HIGY-1..D-HIGY-18 in `04-CONTEXT.md` are LOCKED and must be honored verbatim. Summary table:

| ID | Locked decision |
|----|-----------------|
| D-HIGY-1 | Only schema snapshots committeable; NO raw payloads, NO anonymized fixtures committeable (consistency with Phase 2/3 pattern). `verification.capture()` available for gitignored `captures/`. |
| D-HIGY-2 | Driver stdout = counts + shape descriptor only; NEVER values. `safe_print` with `secrets=[HIGYRUS_USER, HIGYRUS_PASSWORD, _token]`. |
| D-HIGY-3 | Diff bidireccional is **recursive** in nested `SafeModel`s: `Cuenta → {DisposicionesGenerales, Domicilio[], PersonaRelacionada[], MedioComunicacion[], CuentaBancaria[], Administrador→{Agente,Operador,Sucursal}}`, `Posicion → Parking[]`. For `list[X]` with `X: SafeModel`, sample the first element. No type-drift check. |
| D-HIGY-4 | Helper `_diff_safemodel_bidirectional(payload, model_cls, path)` lives **inline in `main_higyrus.py`** module-level (private). YAGNI promotion to `verification/safemodel_diff.py` — defer to Phase 5 if Matriz confirms compatibility. |
| D-HIGY-5 | Two finding directions per discrepancy: `model \ wire` (FALSE PASS risk) and `wire \ model` (info). Path qualifier full: `.cuenta.administrador.operador.idExterno`, `.movimiento.idMovimientos[0]`. Initial run emitting ~30 findings is OK; OPEN→CONFIRMED→FIXED filters noise. |
| D-HIGY-6 | Probe `field_type_map` covers the 4 endpoints with models. `get_health` returns `dict[str, Any]` raw → assert dict + at least one key, no diff. |
| D-HIGY-7 | Fix HIGY-04 is **fix-of-phase**: 5 sites in `client.py` (lines 208, 244, 286, 313, 337) + 5 sites in `aio.py` (lines 233, 264, 302, 325, 345) → `if not isinstance(raw, T): raise HigyrusAPIError(status_code=0, errors=[{"title":"shape mismatch", "detail": f"expected {T}, got {type(raw).__name__}"}])`. |
| D-HIGY-8 | `status_code=0` is the sentinel for client-side detected shape mismatch (HTTP was 200). NO new subclass `HigyrusShapeError`. Document sentinel in `HigyrusAPIError` docstring. |
| D-HIGY-9 | 10 regression tests (5 sync + 5 async) with docstring `"""Regression: assert isinstance(raw, <T>) reemplazado por HigyrusAPIError tipado (finding F-NN)."""`; each asserts `e.status_code == 0` and `e.errors[0]["title"] == "shape mismatch"`. Mocked-only. |
| D-HIGY-10 | 18 probes in `main_higyrus.py` in fixed order; `probe_auth_401` LAST opt-in. |
| D-HIGY-11 | `_resolved_cuenta` set by probe 5 = `cuentas[0].id` or `HIGYRUS_SAMPLE_CUENTA` env override. Downstream probes SKIPPED if `_resolved_cuenta is None`. |
| D-HIGY-12 | Date ranges derived from `today` (no hardcoded anchors): `get_movimientos` = today-30d to today; `get_posicion_valuada` = today/today; `get_posiciones` = today. HIGY-07 `raw == []` is PASS, not FAIL. |
| D-HIGY-13 | Single `asyncio.run(_async_main(...))`; `await aio.aclose()` in `contextlib.suppress(Exception)` (IN-03 of Phase 2 mirror). |
| D-HIGY-14 | Required env vars: `HIGYRUS_USER`, `HIGYRUS_PASSWORD`, `HIGYRUS_BASE_URL`. Optional: `HIGYRUS_CLIENT_ID`, `HIGYRUS_SAMPLE_CUENTA`, `HIGYRUS_SAMPLE_TIPO_CUENTA` (default `"propia"`), `HIGYRUS_SAMPLE_NIVEL` (default `"detalle"`), `VERIFY_HIGYRUS_BAD_CREDS` (opt-in 401). |
| D-HIGY-15 | `safe_print(text, secrets=[HIGYRUS_USER, HIGYRUS_PASSWORD, _token])`. `_token` added dynamically after first `login()`. No `refresh_token` in Higyrus (single Bearer 24h). |
| D-HIGY-16 | 5 schema snapshots in `.planning/verification/schemas/higyrus-client/<func>.json` with envelope D-21 + D-25 no-overwrite-on-drift. |
| D-HIGY-17 | `# ------ Verified live (Phase 4) ------` + `# ------ Regressions ------` sections in `test_client.py` and `test_async_client.py`. Verified-live invariants: URL/query verbatim per endpoint (HIGY-02), `from_api` tolerance (HIGY-03), 10 fix-HIGY-04 regressions, error envelope parsing (HIGY-05), empty path (HIGY-07), and parity emitted-params verbatim sync vs async (HIGY-06). |
| D-HIGY-18 | Same redaction discipline as Phase 3: `safe_print(text, secrets=[...])` with dynamic `_token` extension after login. Driver never prints payload content (D-HIGY-2). |

### Claude's Discretion

The CONTEXT.md `## Claude's Discretion` section lists 9 discretion areas. Verbatim:

- Exact verbatim text of the final summary line (format `SUMMARY: PASS=N FAIL=N SKIPPED=N FINDING=N` per Phase 2 D-02).
- Internal structure of `_diff_safemodel_bidirectional` (iterative vs recursive, `yield from` vs accumulated list, path qualifier format `.a.b[0].c` vs `a.b[0].c`).
- Cascade SKIPPED tactic post `login()` failure (D-IOL-3 mirror): module-level flag, decorator wrapper, or per-probe early-return.
- How `probe_parity_sync_async` inspects emitted params: monkey-patch on `httpx.Client.request` / `httpx.AsyncClient.request`, or capture `request.url.query` from response — `pytest-httpx` is NOT available (live).
- Whether `probe_get_listado_cuentas_sync` filters by `estado="alta"` or not.
- Finding sub-classification of direction A (`wire \ model`, info) vs direction B (`model \ wire`, FALSE PASS) — convention suggested: prefix `(info)` vs `(FALSE PASS riesgo)` in the `detail` field.
- Exact timing of `Optional[T]` detection in `_diff_safemodel_bidirectional` (current Higyrus models do not use `Optional` except potentially future additions): if `Optional`, do NOT emit direction-B finding (explicit nullable, not FALSE PASS).
- Plausibility bounds for `Movimiento.cantidad` (e.g., `|cantidad| < 1e9`) — discretionarily NO bounds checks in Phase 4 (movement values are highly variable).
- The `phase_requirements` table at the bottom of this RESEARCH.md is the authoritative mapping from HIGY-NN to research findings; the planner uses it to organize plans.

### Deferred Ideas (OUT OF SCOPE)

From CONTEXT.md `<deferred>`:

- Iterate ALL accounts in the listing (multi-account sweep) — Phase 4 uses fixed sample.
- Committable anonymized fixtures via `verification.anonymize` — D-HIGY-1 defers; consistency with Phase 2/3.
- Promote `_diff_safemodel_bidirectional` to `verification/safemodel_diff.py` — defer until Phase 5 confirms compatibility.
- Type drift check (wire `'1234'` vs model `float`) — `_coerce` absorbs silently; SafeModel’s `_coerce` already documents this.
- Plausibility bounds on `Movimiento.cantidad` / `Posicion` — defer.
- `probe_get_listado_cuentas` with other filters — Phase 4 uses only `estado="alta"`.
- Test of `auth-once` discipline mocked — not load-bearing.
- New subclass `HigyrusShapeError(HigyrusAPIError)` — D-HIGY-8 rejects.
- Refactor to class `Client` / sync-async dedup — PROJECT.md out of scope.
- DRIFT-02 (consolidated per-package report) — anchored to Phase 5.

## Phase Requirements

The phase requirement IDs were provided in the additional context. The table below maps each HIGY-NN to the research findings the planner consumes to build implementation tasks.

| ID | Description (from REQUIREMENTS.md) | Research Support |
|----|------------------------------------|------------------|
| HIGY-01 | Verificar login + lazy-auth, sync y async | *Cascade SKIPPED pattern* + *Lifecycle* sections; reuse `_auth_failed` flag from `main_iol.py` (D-IOL-3 mirror). Driver invokes `higyrus_client.login()` and `await aio.login()` as probes 1 and 2. |
| HIGY-02 | Happy-path sweep `get_health` / `get_listado_cuentas` / `get_movimientos` / `get_posicion_valuada` / `get_posiciones`, retaining raw payload, sync+async | *Sample selection* sub-section. Probes 3-12 sweep all 5 endpoints on both surfaces. `_resolved_cuenta` propagated through tuple-return per Phase 3 pattern. |
| HIGY-03 | Bidirectional diff of raw payload keys vs declared model fields (defeating the SafeModel.from_api FALSE PASS trap) | **Pattern 1 (Bidirectional diff)** — the most novel mechanism this phase introduces. Probe 14 `probe_field_type_map`. |
| HIGY-04 | Verify in-vivo `assert isinstance(raw, list/dict)`; if broken, fix to typed `HigyrusAPIError` | *Don't Hand-Roll* (no new subclass), *Pattern 4 (assert → typed exception)*. Fix at 10 sites (5 sync + 5 async). 10 mocked regressions. |
| HIGY-05 | Verify parsing of `errors` envelope on a bad request | Probes 16-17 (always-on, `id_cuenta="INVALID-CUENTA-XXXXX"`). `_raise_for_response` already parses `errors`/`timestamp` (existing code). |
| HIGY-06 | Sync↔async parity including the known async `drop_none` deviation | **Pattern 2 (Live param capture)** — second most novel mechanism. Probe 13 captures `httpx.URL.params` from sync vs async with the same `None` params. |
| HIGY-07 | Empty/204 response paths | Probes 5/7/11 with empty samples return `[]` per `if raw is None: return []` guard already in client.py:242,284,311,335. Driver counts as PASS (D-HIGY-12). |

## Architectural Responsibility Map

The phase touches three architectural tiers in parallel; mapping prevents misassignment of tasks.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|--------------|----------------|-----------|
| Login + token caching (HIGY-01) | `higyrus_client.client` / `higyrus_client.aio` module-level state | Driver (read-only via `client._token`) | Auth lives in module globals; driver never mutates `_token` (only reads for `safe_print` secrets list). |
| Endpoint wrappers + `_request` (HIGY-02/04/05/07) | `higyrus_client.client` / `higyrus_client.aio` | n/a | Pure client responsibility; fix HIGY-04 modifies 10 wrapper sites. |
| Wire shape parsing (HIGY-03) | `higyrus_client.models.SafeModel.from_api` | Driver (introspection via `get_type_hints`) | `from_api` IS the FALSE PASS source; the driver runs the bidirectional diff *outside* of `from_api`. |
| Param serialization (HIGY-06 `drop_none` deviation) | `higyrus_client._params.drop_none` | Driver (inspects emitted `request.url.params`) | Already exists; driver verifies the deviation in vivo by capturing the request URL, not by re-implementing. |
| Findings file / schema snapshots / redaction | `verification.findings` / `verification.schema` / `verification.redaction` (Phase 1+2 harness) | Driver (call site only) | Driver calls `append_finding`, `write_findings`, `schema_of`, `safe_print` as library functions. No harness mutation in Phase 4. |
| Mocked tests (Verified-live + Regressions) | `packages/higyrus-client/tests/{test_client,test_async_client}.py` | `packages/higyrus-client/tests/conftest.py` (autouse fixtures reused as-is) | Tests append sections to existing files; conftest stays untouched. |

## Standard Stack

The stack is **fixed** — no new packages. Phase 4 reuses everything Phase 3 already vendored. Versions are pinned in `uv.lock` (root) and already satisfy `mypy --strict` + `ruff check` for Phases 2-3.

### Core (already installed; do NOT add)

| Library | Version (lockfile) | Purpose | Why standard |
|---------|--------------------|---------|--------------|
| httpx | >=0.27 | sync `httpx.Client` + async `httpx.AsyncClient` for HTTP transport in `higyrus_client.client` / `aio` | Project-wide HTTP transport; used by all 5 packages. `httpx.Request.url.params` is the API used by Pattern 2 (live param capture). |
| pytest | >=8.3 | Test runner | Project standard. |
| pytest-httpx | >=0.34 | Mock HTTP responses for the 10 regression tests + Verified-live tests | Already used in `test_client.py` / `test_async_client.py`. URL-with-query matching pattern locked in TESTING.md. |
| pytest-asyncio | >=0.24 | `asyncio_mode = "auto"` enables `async def test_*` without decorator | Project standard. |
| python-dotenv | >=1.0 | Loads `.env` per package via `load_dotenv()` at module import | Already used by `higyrus_client.client` / `aio.py`. |

### Supporting (harness, no install required)

| Library | Version | Purpose | When to use |
|---------|---------|---------|-------------|
| `verification.findings.append_finding` | committed (Phase 2 + post-review hardening) | Idempotent finding emission, preserves human-promoted status (CONFIRMED/FIXED/EXPECTED/NO-FIX), validates pkg slug, single-line title invariant | Every probe that detects a discrepancy. |
| `verification.findings.write_findings` | committed | Idempotent skeleton creation | Driver `main()` start. |
| `verification.schema.schema_of` | committed | PII-free type-only structure (keys + type names; values never appear) | Schema snapshots (probe 15) and field-type maps (probe 14). |
| `verification.redaction.safe_print` | committed | Two-layer redaction: explicit `secrets=[...]` replace + `_BEARER` regex catch-all | Every line of stdout output. |
| `verification.env_gate.require_env` | committed | Skip-and-continue with verbatim `SKIPPED <pkg>: missing X, Y` | Driver `main()` first call. |
| `verification.capture.capture` | committed | Gitignored payload staging (operator inspection) | Optional; D-HIGY-1 says no fixtures committed. |

### Alternatives Considered (and rejected)

| Instead of | Could use | Tradeoff |
|------------|-----------|----------|
| Driver-level bidirectional diff inline (D-HIGY-4) | Promote to `verification/safemodel_diff.py` | Rejected by D-HIGY-4 (YAGNI; Phase 5 / Matriz may have different model shape — defer promotion). |
| Reuse `HigyrusAPIError(status_code=0)` for shape mismatch | New subclass `HigyrusShapeError(HigyrusAPIError)` | Rejected by D-HIGY-8 (callers distinguish via `e.status_code == 0`; promoting to subclass deferred until Phase 5 confirms recurrence). |
| Fixed sample account via `cuentas[0].id` + env override | Iterate all accounts in listing | Rejected by deferred list (multi-account aggregation requires extra design; sample fixed is enough for shape verification). |
| Mocked-only regression for fix HIGY-04 | Also exercise in vivo | Rejected by D-HIGY-9 (the wire probably respects shape today — fix is prophylactic, no need to consume live attempts for a path that won't trigger). |

**Installation:**

```bash
# No new packages.
uv sync --all-packages --all-extras --dev --frozen   # already up to date for Phases 2-3
```

**Version verification:** [VERIFIED: codebase grep] All five packages above are present in `uv.lock` (758 lines, committed per CLAUDE.md). `pytest-httpx >=0.34` and `pytest-asyncio >=0.24` confirmed in root `pyproject.toml` dev-dependencies. No version drift expected during Phase 4 — `--frozen` enforces.

## Package Legitimacy Audit

Phase 4 installs **zero** new packages. The Package Legitimacy Gate protocol is therefore vacuously satisfied. All libraries listed in Standard Stack are pre-existing pinned deps satisfied by `uv.lock` (no install action in Phase 4 plans).

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| *(none — phase adds no packages)* | — | — | — | — | — | — |

**Packages removed due to `[SLOP]`:** none (no candidates).
**Packages flagged as `[SUS]`:** none (no candidates).

If a future plan in Phase 4 were to add a package (e.g., `respx` as an alternative to `pytest-httpx`), the planner MUST run the gate before merging. Default posture: do not add packages in Phase 4.

## Architecture Patterns

### System Architecture Diagram

```text
                          ┌─────────────────────────────────────────────┐
                          │  Driver: main_higyrus.py (rewrite target)   │
                          │                                              │
                          │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌─────┐ │
                          │  │ p1-2 │ │ p3-4 │ │ p5-12│ │ p13  │ │p14-15│  18 named
                          │  │login │ │health│ │5 EPs │ │parity│ │ diff │  probes
                          │  │      │ │      │ │async │ │drop_n│ │schema│  D-HIGY-10
                          │  └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └──┬──┘ │
                          │     │        │        │        │        │    │
                          │   ┌─▼────────▼────────▼────────▼────────▼──┐ │
                          │   │  append_finding / write_findings        │ │
                          │   │  schema_of / safe_print / require_env   │ │
                          │   │  (verification/* harness, Phase 1+2)    │ │
                          │   └────────┬────────────┬───────────────────┘ │
                          └────────────┼────────────┼───────────────────-─┘
                                       │            │
                                       │            │   ┌──────────────────┐
                                       │            └──▶│ stdout (verbatim │
                                       │                │  per D-02 Phase 2│
                                       │                │  + redacted by   │
                                       │                │  safe_print)     │
                                       │                └──────────────────┘
                                       │
                          ┌────────────▼────────────────────────────────┐
                          │  higyrus_client {.client, .aio} (target SUT)│
                          │                                              │
                          │  login() → POST /api/login (Bearer 24h)     │
                          │  _request() → drop_none(params) + Bearer    │
                          │     [HIGY-04 targets — 5+5 assert sites]    │
                          │  get_health, get_listado_cuentas,           │
                          │  get_movimientos, get_posicion_valuada,     │
                          │  get_posiciones                              │
                          │     → models.{Cuenta, Movimiento, Posicion, │
                          │        PosicionValuada}.from_api(raw)       │
                          │     (SafeModel — FALSE PASS surface!)       │
                          └─────────────┬────────────────────────────────┘
                                        │
                                        │  HTTPS
                                        ▼
                          ┌─────────────────────────────────────────────┐
                          │  Higyrus live API                            │
                          │  https://cliente.aunesa.com/Irmo (default)  │
                          │  Bearer 24h TTL, returns JSON with PII       │
                          │  (cuentas: titular, CBU, domicilios,         │
                          │   personasRelacionadas, mediosComunicacion) │
                          └─────────────────────────────────────────────┘

                          Side outputs (committable after human checkpoint):
                          - .planning/verification/higyrus-client-findings.md
                          - .planning/verification/schemas/higyrus-client/
                              ├── get-health.json
                              ├── get-listado-cuentas.json
                              ├── get-movimientos.json
                              ├── get-posicion-valuada.json
                              └── get-posiciones.json

                          Test outputs (committed in Plan 3):
                          - packages/higyrus-client/tests/test_client.py
                              ├── # ------ Verified live (Phase 4) ------
                              └── # ------ Regressions ------
                          - packages/higyrus-client/tests/test_async_client.py (mirror)
```

### Recommended Project Structure

```
market-libs/
├── main_higyrus.py                                    # ← REWRITE TARGET (D-HIGY-10)
├── verification/                                      # ← harness (Phase 1+2, UNCHANGED in Phase 4)
│   ├── findings.py (append_finding, write_findings)
│   ├── schema.py (schema_of)
│   ├── redaction.py (safe_print)
│   ├── env_gate.py (require_env)
│   └── capture.py (optional, gitignored)
├── packages/higyrus-client/
│   ├── src/higyrus_client/
│   │   ├── client.py          # ← 5 assert isinstance sites: lines 208, 244, 286, 313, 337
│   │   ├── aio.py             # ← 5 assert isinstance sites: lines 233, 264, 302, 325, 345
│   │   ├── exceptions.py      # ← edit docstring: status_code=0 sentinel
│   │   ├── models.py          # ← UNTOUCHED (SafeModel pattern is the SUT)
│   │   └── _params.py         # ← UNTOUCHED (drop_none is the verification target)
│   ├── tests/
│   │   ├── conftest.py        # ← UNTOUCHED (autouse fixtures already correct)
│   │   ├── test_client.py     # ← APPEND Verified-live + Regressions sections
│   │   └── test_async_client.py  # ← APPEND mirror
│   └── .env.example           # ← APPEND optional vars (D-HIGY-14)
└── .planning/verification/    # ← outputs (5 snapshots + 1 findings file)
    ├── higyrus-client-findings.md          [generated, committed after checkpoint]
    └── schemas/higyrus-client/
        ├── get-health.json                  [generated, committed after checkpoint]
        ├── get-listado-cuentas.json         [generated, committed after checkpoint]
        ├── get-movimientos.json             [generated, committed after checkpoint]
        ├── get-posicion-valuada.json        [generated, committed after checkpoint]
        └── get-posiciones.json              [generated, committed after checkpoint]
```

### Pattern 1: Bidirectional SafeModel diff (`_diff_safemodel_bidirectional`) — **THE novel mechanism of Phase 4**

**What:** Recursively compare the set of keys in the raw `payload` (from `resp.json()`) against `set(get_type_hints(model_cls))`. Emit two findings per discrepancy:
- **direction `model \ wire`** ("model declares, wire doesn't emit"): the SafeModel will silently substitute a typed zero (`""`, `0`, `0.0`, `False`, `[]`) and `from_api` won't raise. THIS is the FALSE PASS trap.
- **direction `wire \ model`** ("wire emits, model ignores"): the SafeModel discards the key. INFO only — possibly a feature added to the backend, not a client bug.

**When to use:** Probe 14 (`probe_field_type_map`). Iterate the 4 endpoints with models — `Cuenta`, `Movimiento`, `Posicion`, `PosicionValuada` (D-HIGY-6).

**Where:** Helper lives inline in `main_higyrus.py` as `_diff_safemodel_bidirectional` (private, module-level). D-HIGY-4 forbids promotion to `verification/safemodel_diff.py` until Phase 5 confirms compatibility.

**Reference implementation (verified against `higyrus_client.models`):**

```python
# Source: this RESEARCH.md (composed from .planning/codebase verified-as-of-2026-06-06).
# Mirrors the iteration pattern in main_iol.py:1046-1115 (probe_field_type_map),
# adapted to recursive SafeModel descent per D-HIGY-3.
from __future__ import annotations

from collections.abc import Iterator
from types import NoneType, UnionType
from typing import Any, Union, get_args, get_origin, get_type_hints

from higyrus_client.models import SafeModel


def _diff_safemodel_bidirectional(
    payload: Any,
    model_cls: type,
    path: str = "",
) -> Iterator[tuple[str, str, str]]:
    """Yield (path, direction, key) tuples.

    direction in {'model-only', 'wire-only'}.

    - 'model-only' means the key is declared by the model but ABSENT in the wire
      payload — FALSE PASS risk because SafeModel.from_api(payload) substitutes a
      typed zero default and does not raise. Phase 4 D-HIGY-5 maps this to
      finding `SHAPE` class with detail prefix `(FALSE PASS riesgo)`.
    - 'wire-only' means the key is present in the wire payload but ABSENT from
      the model — INFO only. Phase 4 D-HIGY-5 maps this to finding `SHAPE` class
      with detail prefix `(info)`.

    Recurses into nested SafeModels and list[SafeModel] (samples list[0] only,
    consistent with verification.schema.schema_of).
    """
    if not isinstance(payload, dict):
        return  # Cannot diff non-dict; SafeModel.from_api would already substitute {}.

    hints = get_type_hints(model_cls)
    model_keys = set(hints.keys())
    wire_keys = set(payload.keys())

    # Direction A: model declares, wire doesn't emit  -> FALSE PASS risk.
    for key in sorted(model_keys - wire_keys):
        hint = hints[key]
        # Discretion-D-HIGY-7: Optional[T] / T | None means explicitly nullable;
        # absence is the intended representation of None. Do NOT emit direction A.
        if _is_optional(hint):
            continue
        yield (path, "model-only", key)

    # Direction B: wire emits, model doesn't declare -> info only.
    for key in sorted(wire_keys - model_keys):
        yield (path, "wire-only", key)

    # Recurse into nested SafeModels and list[SafeModel].
    for key in model_keys & wire_keys:
        hint = hints[key]
        nested_payload = payload[key]
        nested_cls = _nested_safemodel_class(hint)
        if nested_cls is None:
            continue
        if _is_list_of_safemodel(hint):
            # D-HIGY-3: sample first element only (consistent with schema_of).
            if isinstance(nested_payload, list) and nested_payload:
                yield from _diff_safemodel_bidirectional(
                    nested_payload[0],
                    nested_cls,
                    f"{path}.{key}[0]",
                )
            # Empty list is HIGY-07 path — no recursion, no finding.
        else:
            yield from _diff_safemodel_bidirectional(
                nested_payload, nested_cls, f"{path}.{key}"
            )


def _is_optional(hint: Any) -> bool:
    """True if hint is Optional[T] / T | None."""
    origin = get_origin(hint)
    if origin is Union or origin is UnionType:
        return any(a is NoneType for a in get_args(hint))
    return False


def _nested_safemodel_class(hint: Any) -> type | None:
    """If hint is SafeModel subclass or list[SafeModel subclass], return the class; else None."""
    if isinstance(hint, type) and issubclass(hint, SafeModel):
        return hint
    if get_origin(hint) is list:
        args = get_args(hint)
        if args and isinstance(args[0], type) and issubclass(args[0], SafeModel):
            return args[0]
    return None


def _is_list_of_safemodel(hint: Any) -> bool:
    return get_origin(hint) is list and _nested_safemodel_class(hint) is not None
```

**Path qualifier format (D-HIGY-5):** Full dotted from root, e.g. `.cuenta.administrador.operador.idExterno`. The leading dot is the locked convention (D-HIGY-5 lists examples with leading dots: `.cuenta.administrador.operador.idExterno`, `.movimiento.idMovimientos[0]`). Empty path at root: `""`. Discretion left on whether to render as `.path` or `path` — recommend leading dot to match the locked examples.

**Where the diff hooks into the probe:**

```python
# Excerpted pattern, inline in main_higyrus.py probe_field_type_map:
def probe_field_type_map(
    cuenta_raw: dict[str, Any] | None,
    movimientos_raw: list[dict[str, Any]] | None,
    posiciones_raw: list[dict[str, Any]] | None,
    posicion_valuada_raw: list[dict[str, Any]] | None,
) -> ProbeResult:
    if _auth_failed:
        return ProbeResult("field_type_map", "SKIPPED", f"auth failed: {_auth_failure_reason}")
    base_url = higyrus_client.client._base_url
    fids: list[str] = []
    targets = [
        ("cuenta", cuenta_raw, Cuenta),
        ("movimiento", movimientos_raw[0] if movimientos_raw else None, Movimiento),
        ("posicion", posiciones_raw[0] if posiciones_raw else None, Posicion),
        ("posicion_valuada", posicion_valuada_raw[0] if posicion_valuada_raw else None, PosicionValuada),
    ]
    for root_name, payload, model_cls in targets:
        if payload is None:
            continue
        for path, direction, key in _diff_safemodel_bidirectional(
            payload, model_cls, path=f".{root_name}"
        ):
            fid = _next_fid()
            if direction == "model-only":
                title = f"{path}.{key}: model declara, wire no emite (FALSE PASS riesgo)"
                actual = "<wire ausente; SafeModel sustituye default tipado>"
                diff_detail = f"key `{key}` ausente en wire bajo `{path}` (model: {model_cls.__name__})"
            else:  # wire-only
                title = f"{path}.{key}: wire emite, model ignora (info)"
                actual = f"key `{key}` presente en wire bajo `{path}`"
                diff_detail = f"backend posiblemente agregó campo nuevo; candidato a extender model"
            append_finding(
                _PKG,
                fid=fid,
                class_="SHAPE",
                surface="both",
                status="OPEN",
                title=title,
                expected=(
                    "model y wire coinciden en el set de claves"
                    if direction == "model-only"
                    else "model declara el superset del wire"
                ),
                actual=actual,
                diff=diff_detail,
                base_url=base_url,
            )
            fids.append(fid)
    if fids:
        return ProbeResult("field_type_map", "FINDING", f"{', '.join(fids)} (OPEN)")
    return ProbeResult("field_type_map", "PASS", "4 endpoints, no field drift")
```

### Pattern 2: Live `httpx.Request.url.params` capture — sync vs async parity (HIGY-06)

**What:** Verify the known async `drop_none` deviation by inspecting the literal `httpx.QueryParams` emitted to the wire on a call where multiple optional params are `None`. The two surfaces should emit byte-identical query strings.

**When to use:** Probe 13 (`probe_parity_sync_async`).

**The trap:** `pytest-httpx.HTTPXMock` is NOT usable in live runs. The driver must capture the request URL via monkey-patch on `httpx.Client.request` / `httpx.AsyncClient.request`. This is more invasive than the `iol_client` parity probe (which compared `schema_of` of two payloads) because Higyrus parity verification is about the *request side*, not the response side.

**Reference implementation (verified against `httpx >= 0.27` API surface):**

```python
# Source: this RESEARCH.md.
# Mirrors the discretion noted in D-HIGY (Discretion bullet "Cómo el probe 13
# inspecciona los params emitidos: monkey-patch del httpx.Client.request o
# captura del request.url.query desde el response").
from __future__ import annotations

import datetime as dt
import httpx
import higyrus_client
from higyrus_client import aio


def _capture_sync_query_string(
    cuenta: str, fecha_desde: dt.date, fecha_hasta: dt.date
) -> str | None:
    """Capture the literal query string emitted by the sync client.

    Strategy: monkey-patch the *bound* request method on the module-level
    httpx.Client instance. Less invasive than patching the class because the
    patch is scoped to this single call and restored in finally.
    """
    captured: dict[str, str] = {}
    original_request = higyrus_client.client._client.request

    def _spy_request(method: str, url: str, **kwargs):  # type: ignore[no-untyped-def]
        resp = original_request(method, url, **kwargs)
        captured["query"] = str(resp.request.url.query, "utf-8") if isinstance(
            resp.request.url.query, bytes
        ) else resp.request.url.query
        return resp

    try:
        higyrus_client.client._client.request = _spy_request  # type: ignore[assignment]
        # Call with all four optional params = None (the deviation surface).
        higyrus_client.get_movimientos(cuenta, fecha_desde, fecha_hasta)
    finally:
        higyrus_client.client._client.request = original_request  # type: ignore[assignment]
    return captured.get("query")


async def _capture_async_query_string(
    cuenta: str, fecha_desde: dt.date, fecha_hasta: dt.date
) -> str | None:
    """Async mirror — captures aio surface via the AsyncClient.request method.

    Note: the async client is lazily instantiated; ensure it exists first.
    """
    await aio._ensure_http_client()
    assert aio._client is not None
    captured: dict[str, str] = {}
    original_request = aio._client.request

    async def _spy_request(method: str, url: str, **kwargs):  # type: ignore[no-untyped-def]
        resp = await original_request(method, url, **kwargs)
        # httpx.Request.url is an httpx.URL; .query is bytes in httpx>=0.27.
        q = resp.request.url.query
        captured["query"] = q.decode("utf-8") if isinstance(q, bytes) else q
        return resp

    try:
        aio._client.request = _spy_request  # type: ignore[assignment]
        await aio.get_movimientos(cuenta, fecha_desde, fecha_hasta)
    finally:
        aio._client.request = original_request  # type: ignore[assignment]
    return captured.get("query")
```

**Probe body:**

```python
def probe_parity_sync_async(
    cuenta: str, fecha_desde: dt.date, fecha_hasta: dt.date
) -> ProbeResult:
    if _auth_failed:
        return ProbeResult("parity_sync_async", "SKIPPED", f"auth failed: {_auth_failure_reason}")
    base_url = higyrus_client.client._base_url
    sync_q = _capture_sync_query_string(cuenta, fecha_desde, fecha_hasta)
    # Async capture runs inside _async_main (single asyncio.run, D-HIGY-13);
    # the captured async_q is passed in from there. Pattern shown collapsed for brevity.
    # If they match -> PASS. Otherwise -> SYNC-ASYNC-DRIFT OPEN.
    if sync_q != _async_q_from_async_main:  # injected via tuple-return from _async_main
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="SYNC-ASYNC-DRIFT",
            surface="both",
            status="OPEN",
            title="sync y async emiten query strings distintos en get_movimientos",
            expected=f"sync.query == async.query (drop_none paridad)",
            actual=f"sync={sync_q!r}; async={_async_q_from_async_main!r}",
            diff="diferencia en cómo drop_none se aplica en aio._request",
            base_url=base_url,
        )
        return ProbeResult("parity_sync_async", "FINDING", f"{fid} (OPEN)")
    return ProbeResult("parity_sync_async", "PASS", f"query={sync_q!r}")
```

**Trade-off:** Monkey-patching the *bound method* on `_client` is preferred over patching `httpx.Client.request` at the class level — the latter would affect any other code that uses `httpx` in the same process. The bound-method patch is scoped to the single live call and restored in `finally`. The risk that `_client.request` is read-only (`mappingproxy` etc.) is not a concern in `httpx` — instance attribute assignment is supported.

**Alternative:** Inspect `request.url.params` via `httpx.Request` object inside an httpx event hook. `httpx.Client(event_hooks={"request": [fn]})` would be cleaner, but the existing `_client` is module-level and lazily instantiated; mutating event_hooks on the live instance is at least as invasive. The monkey-patch wins on simplicity.

### Pattern 3: Cascade SKIPPED via `_auth_failed` flag (D-IOL-3 mirror)

**What:** A single module-level `_auth_failed: bool = False` flag set by `probe_login_sync` or `probe_login_async` on `HigyrusAuthError`. Every downstream probe checks `if _auth_failed: return ProbeResult(name, "SKIPPED", f"auth failed: {_auth_failure_reason}")`.

**Why this tactic (vs decorator wrapper vs per-probe early-return):** Phase 3 used exactly this pattern (`main_iol.py:140-142, 260-263, ...`) and the Phase 3 review (`03-REVIEW.md`, `03-SECURITY.md` T-3-15) confirmed it works with zero friction:
- T-3-15 (Repudiation: cascade SKIPPED masks root cause) was CLOSED by emitting `AUTH OPEN` finding on the FIRST failing `probe_login_*` call BEFORE setting the flag.
- The post-mortem review of Phase 2 (the closest analogue without cascade) showed no equivalent friction; Phase 3’s explicit `_auth_failed` flag was a NET addition, not a regression from Phase 2.

The decorator wrapper variant adds indirection (every probe wrapped in `@skip_if_auth_failed`) and the per-probe early-return repeats the same check verbatim — both are equivalent in semantics but the module-level flag is the most readable. **Recommend: module-level flag, exact copy of Phase 3 pattern.**

**Reference implementation (lifted verbatim from `main_iol.py:140-235`):**

```python
# Module-level state (after constants):
_auth_failed: bool = False
_auth_failure_reason: str = ""


def probe_login_sync() -> ProbeResult:
    global _auth_failed, _auth_failure_reason
    base_url = higyrus_client.client._base_url
    try:
        higyrus_client.login()
    except HigyrusAuthError as exc:
        _auth_failed = True
        _auth_failure_reason = f"sync login: {exc}"
        fid = _next_fid()
        append_finding(
            _PKG,
            fid=fid,
            class_="AUTH",
            surface="sync",
            status="OPEN",
            title="login() sync falló",
            expected="login succeeds + cached token",
            actual=repr(exc),
            diff=f"status_code={exc.status_code!r}",
            base_url=base_url,
        )
        return ProbeResult("login_sync", "FINDING", f"{fid} (OPEN)")
    return ProbeResult("login_sync", "PASS", "_token cached")
```

### Pattern 4: `assert isinstance` → `HigyrusAPIError(0, [...])` (HIGY-04 fix)

**What:** Replace each of the 10 `assert isinstance(raw, T)` statements with a typed exception raise. The shape matches `_raise_for_response` (existing) but uses `status_code=0` sentinel because the HTTP request succeeded with 200 OK — only the body shape failed.

**When to use:** Apply at the 10 sites listed in D-HIGY-7.

**Reference implementation (verbatim per D-HIGY-7):**

```python
# Before (client.py:208, mirror at aio.py:233; same for the 9 other sites):
def get_health() -> dict[str, Any]:
    raw = _request("GET", "/api/health")
    assert isinstance(raw, dict)
    return raw

# After:
def get_health() -> dict[str, Any]:
    raw = _request("GET", "/api/health")
    if not isinstance(raw, dict):
        raise HigyrusAPIError(
            status_code=0,
            errors=[{
                "title": "shape mismatch",
                "detail": f"expected dict, got {type(raw).__name__}",
            }],
        )
    return raw
```

**Site mapping (verified by reading the files line-by-line):**

| Site | File | Line | Endpoint | Expected type |
|------|------|------|----------|---------------|
| 1 | `client.py` | 208 | `get_health` | `dict` |
| 2 | `client.py` | 244 | `get_movimientos` | `list` |
| 3 | `client.py` | 286 | `get_posicion_valuada` | `list` |
| 4 | `client.py` | 313 | `get_listado_cuentas` | `list` |
| 5 | `client.py` | 337 | `get_posiciones` | `list` |
| 6 | `aio.py` | 233 | `get_health` | `dict` |
| 7 | `aio.py` | 264 | `get_movimientos` | `list` |
| 8 | `aio.py` | 302 | `get_posicion_valuada` | `list` |
| 9 | `aio.py` | 325 | `get_listado_cuentas` | `list` |
| 10 | `aio.py` | 345 | `get_posiciones` | `list` |

**Exception docstring update (D-HIGY-8):** Edit `packages/higyrus-client/src/higyrus_client/exceptions.py:23-25` to document the sentinel:

```python
# Before:
#     status_code: HTTP status devuelto.
# After:
#     status_code: HTTP status devuelto, o 0 si el error fue detectado client-side
#         (e.g., shape mismatch tras un 2xx exitoso).
```

### Pattern 5: Opt-in 401 probe with single-shot + try/finally (D-HIGY-10 #18 = D-IOL-1/2/4 mirror)

**What:** Verify `HigyrusAuthError` fires on bad credentials. Opt-in gated by `VERIFY_HIGYRUS_BAD_CREDS=1`, single-shot (no retry/sleep/loop), runs LAST in the probe sequence.

**When to use:** Probe 18.

**Important deviation from Phase 3 (IOL):** Higyrus has NO refresh_token. The CR-03 fix that motivated Phase 3’s direct `_password` mutation (preserving `_refresh_token` through `configure()`) does NOT apply here. We CAN use `configure(password=...)` safely because there is no other state to preserve. Recommendation: prefer `configure()` for symmetry with the documented client API.

**Reference implementation:**

```python
def probe_auth_401() -> ProbeResult:
    if os.getenv("VERIFY_HIGYRUS_BAD_CREDS") != "1":
        return ProbeResult("auth_401", "SKIPPED", "(opt-in via VERIFY_HIGYRUS_BAD_CREDS=1)")
    if _auth_failed:
        return ProbeResult("auth_401", "SKIPPED", f"auth failed: {_auth_failure_reason}")

    base_url = higyrus_client.client._base_url
    original_password = os.getenv("HIGYRUS_PASSWORD", "")
    bad_password = original_password + "_INVALID"
    try:
        higyrus_client.configure(password=bad_password)  # resets _token, _token_ts
        try:
            higyrus_client.login()  # D-HIGY: ÚNICA llamada, sin retry/sleep/loop.
        except HigyrusAuthError as exc:
            status_code = exc.status_code  # WR-01: typed directly.
            if status_code == 401:
                fid = _next_fid()
                append_finding(
                    _PKG,
                    fid=fid,
                    class_="AUTH",
                    surface="sync",
                    status="EXPECTED",
                    title="credenciales inválidas reciben 401",
                    expected="401 con password=HIGYRUS_PASSWORD+_INVALID",
                    actual="401",
                    diff="ninguno; comportamiento esperado",
                    base_url=base_url,
                )
                return ProbeResult("auth_401", "FINDING", f"{fid} (EXPECTED)")
            fid = _next_fid()
            append_finding(_PKG, fid=fid, class_="AUTH", surface="sync", status="OPEN",
                title="credenciales inválidas recibieron status inesperado",
                expected="401",
                actual=f"status_code={status_code!r}",
                diff=f"AuthError con status_code={status_code!r}",
                base_url=base_url,
            )
            return ProbeResult("auth_401", "FINDING", f"{fid} (OPEN)")
        except Exception as exc:
            fid = _next_fid()
            append_finding(_PKG, fid=fid, class_="AUTH", surface="sync", status="OPEN",
                title="credenciales inválidas produjeron error inesperado",
                expected="401 (HigyrusAuthError)",
                actual=repr(exc),
                diff=f"type={type(exc).__name__}",
                base_url=base_url,
            )
            return ProbeResult("auth_401", "FINDING", f"{fid} (OPEN)")
        # Sin excepción → defensa relajada (200 OK con bad creds).
        fid = _next_fid()
        append_finding(_PKG, fid=fid, class_="AUTH", surface="sync", status="OPEN",
            title="credenciales inválidas NO recibieron 401",
            expected="401 con password=HIGYRUS_PASSWORD+_INVALID",
            actual="200 OK (defensa relajada)",
            diff="el server aceptó un password inválido",
            base_url=base_url,
        )
        return ProbeResult("auth_401", "FINDING", f"{fid} (OPEN)")
    finally:
        # SIEMPRE restaurar — crash-proof.
        higyrus_client.configure(password=original_password)
```

### Anti-Patterns to Avoid

- **Looping `probe_auth_401` for retry semantics:** Anti-feature (lockout risk). The probe is single-shot by D-HIGY-10 #18. **NO retry, NO sleep, NO loop.**
- **Iterating ALL accounts in the listing:** Fixed sample (`cuentas[0].id` or `HIGYRUS_SAMPLE_CUENTA`) is enough for HIGY-02/03; multi-account aggregation is deferred.
- **New subclass `HigyrusShapeError`:** D-HIGY-8 rejects. Reuse `HigyrusAPIError(status_code=0)`.
- **Committing raw payloads or fixtures with real account data:** D-HIGY-1 forbids. Schemas-only.
- **Driver printing payload content (titular, CBU, denominación):** D-HIGY-2 forbids. Only counts + shape descriptors.
- **Mutating module state outside `configure()` for the password swap:** Unlike Phase 3 (where CR-03 forced direct `_password` mutation to preserve `_refresh_token`), Higyrus has no refresh_token. Prefer `configure(password=...)`.
- **Adding a second `asyncio.run`:** D-HIGY-13 mandates ONE event loop. The `_async_main` orchestrates all async probes including the parity capture for the async surface.
- **Promoting `_diff_safemodel_bidirectional` to `verification/`:** D-HIGY-4 forbids until Phase 5 confirms reuse.

## Don't Hand-Roll

| Problem | Don't build | Use instead | Why |
|---------|-------------|-------------|-----|
| Findings file generation + idempotent updates | Custom markdown writer | `verification.findings.append_finding` + `write_findings` | Hardened post-Phase-2 review (CR-01 prose preservation, CR-02 single-line title invariant, WR-04 pkg slug validation). Reusing is mandatory; reinventing reintroduces those CR/WR bugs. |
| Bearer/secret redaction in stdout | Hand-rolled `re.sub` | `verification.redaction.safe_print(text, secrets=[...])` | Two-layer defense: explicit list + `_BEARER` regex catch-all (`_BEARER = r"(Bearer\s+)[A-Za-z0-9._~+/=-]+"`). Threshold `len(secret) >= 4` avoids the `replace("", marker)` Pitfall 3. |
| Type-only structural schema | Hand-rolled walker | `verification.schema.schema_of(payload)` | PII-free by construction (types only, never values). Already used by Phase 2 and Phase 3 DRIFT-01 baselines. |
| Env var skip-and-continue | Print + `sys.exit(0)` open-coded | `verification.env_gate.require_env(pkg, vars)` | Locks the verbatim line `SKIPPED <pkg>: missing X, Y` consumed by `main_verify.py` aggregator from Phase 1. |
| Date helpers | New per-package | Copy `_last_business_day` from Phase 3 `main_iol.py:171` if needed; Phase 4 mostly uses `today` and `today - 30d` directly (D-HIGY-12). | Consistency; avoids subtle differences. Phase 4 does NOT need `_last_business_day_with_day_gt_12` (no day>12 verification — that was AMB-03 specific). |
| Shape mismatch exception type | New `HigyrusShapeError` subclass | Reuse `HigyrusAPIError(status_code=0)` per D-HIGY-8 | Sentinel keeps the exception hierarchy stable; callers distinguish via `e.status_code == 0`. |
| Findings ART block header | Hand-edit findings.md | Let `append_finding(... base_url=...)` refresh the ART block on every call | Phase 2 D-03/D-10 invariant; hand-editing risks losing human-promoted statuses. |
| Schema drift handling | Custom diff | `_write_or_check_schema(...)` helper (copy from `main_iol.py:1132-1178`) | D-25 no-overwrite-on-drift already proven in Phase 2 and Phase 3 baselines. |
| Param capture for HIGY-06 | Re-implement `drop_none` inside the driver | Monkey-patch `_client.request` and read `resp.request.url.query` | The wire is the source of truth; re-implementing `drop_none` in the driver verifies the driver, not the client. |

**Key insight:** Phase 4 is the **third application** of the same harness. Every "Don't Hand-Roll" item above has already been built, code-reviewed, security-audited, and locked. The Phase 4 driver is a *consumer* of that harness, not an author. The only net-new code is (a) `_diff_safemodel_bidirectional` (locked inline by D-HIGY-4), (b) the param-capture monkey-patch helpers, and (c) the 10-site fix HIGY-04 + 10 mocked regressions. Everything else is rearrangement.

## Runtime State Inventory

Not applicable — Phase 4 is **not** a rename/refactor/migration phase. It adds a fix (`assert isinstance` → `HigyrusAPIError`) and a verification driver. No stored data, no live service config, no OS-registered state, no env-var renames, no build artifacts to update.

If a future plan within Phase 4 ever renames symbols (e.g., renaming `HigyrusAPIError`), perform a Runtime State Inventory at THAT plan's research step. None expected.

## Common Pitfalls

### Pitfall 1: SafeModel.from_api silently absorbs missing keys (THE FALSE PASS trap)

**What goes wrong:** Wire payload drops a key, `SafeModel.from_api` substitutes the typed zero, the mocked test passes, the live caller silently gets the wrong data.

**Why it happens:** `SafeModel._coerce` (`models.py:48-89`) is designed to be tolerant. The drop is by design for partial payloads; it becomes the FALSE PASS trap only when the wire DROPS a key the client documents as present.

**How to avoid:** Bidirectional diff (Pattern 1). Always emit direction A (`model \ wire`) finding for non-Optional keys.

**Warning signs:** A test mocks a payload with fewer keys than the model declares, and the test still passes with the model fields populated as typed zeros. The Higyrus existing mocked test `test_get_listado_cuentas_devuelve_modelos` (line 88-105) exhibits exactly this property: the mocked payload omits `disposicionesGenerales`, `cuentasBancarias`, `administrador`, etc., and the test verifies `cuentas[0].alias == ""` (the typed-zero default) without raising. This is the trap Phase 4 exists to defeat.

### Pitfall 2: Driver prints reveal PII (real account holder names, CBU, addresses)

**What goes wrong:** A `print(cuentas)` accidentally lands in the driver and titles, CBU, denominations, addresses leak to stdout.

**Why it happens:** The current `main_higyrus.py:43-44` literally does `safe_print(f"   primera: {cuentas[0]}", secrets)` — printing a model instance with PII directly. This must NOT survive the rewrite.

**How to avoid:** D-HIGY-2 LOCKED: `PROBE <name>: <status> <detail>` where `<detail>` is `(N items, shape <descriptor>)`, NEVER the items. The model `__repr__` of a `@dataclass(frozen=True, slots=True)` instance reveals all field values verbatim — `safe_print(f"primera: {cuentas[0]}")` would emit a single line with every titular/CBU verbatim because the secrets list does not contain those values.

**Warning signs:** Any line in the rewritten driver that formats a model instance, a payload dict, or anything other than counts and types into the output string.

### Pitfall 3: `_diff_safemodel_bidirectional` recurses into a non-existent nested key

**What goes wrong:** Direction A finding emits, the recursion still tries to descend into `payload[key]` and KeyErrors.

**Why it happens:** The naive implementation iterates `model_keys` and recurses regardless. The correct implementation recurses only on `model_keys & wire_keys` (intersection).

**How to avoid:** The reference implementation in Pattern 1 already restricts recursion to `model_keys & wire_keys`. Keep this guard.

**Warning signs:** `KeyError` during a probe; the `except Exception` in the probe must wrap the recursion to honor D-04 (driver continues).

### Pitfall 4: Empty list (`list[X]` with no elements) is hit by the recursion sampler

**What goes wrong:** D-HIGY-3 says "for `list[X]` with `X: SafeModel`, sample the first element". If the list is empty (legitimate HIGY-07 path), `payload[key][0]` raises IndexError.

**Why it happens:** Naive `payload[0]`.

**How to avoid:** Guard `if isinstance(nested_payload, list) and nested_payload:` before sampling. Empty list is the HIGY-07 empty path — NOT a finding (HIGY-07 explicitly says empty list is OK).

**Warning signs:** A finding emitted because a model declares `domicilios: list[Domicilio]` and the wire returns `domicilios: []` — that's NOT a finding, it's the empty path.

### Pitfall 5: Optional[T] / T | None misclassified as FALSE PASS

**What goes wrong:** A model field declared `Optional[str] = None` is missing from the wire. Naive diff emits direction A finding. But Optional explicitly opts into nullable — the absence is the intended representation of `None`.

**Why it happens:** `_coerce` (`models.py:55-61`) special-cases `Union`/`UnionType` and returns `None` for missing Optional, NOT a typed zero. So missing Optional is semantically distinct from missing required.

**How to avoid:** The reference implementation (Pattern 1) has `_is_optional(hint)` check before emitting direction A. Note: current Higyrus models do NOT declare any `Optional` field, but future additions might. The check is forward-compatible.

**Warning signs:** Find rerun emits more direction A findings than the previous run after a model field was promoted from `str` to `str | None`.

### Pitfall 6: Param capture monkey-patch leaks beyond the call (resource leak / wrong-process patch)

**What goes wrong:** The patch on `_client.request` is not restored in `finally`; subsequent probes/calls run with the spy attached.

**Why it happens:** Forgetting the `finally` block, or restoring only when no exception happens.

**How to avoid:** Use `try/finally` (the reference implementation in Pattern 2 does this). The `original_request` variable holds the bound method; reassign in `finally`.

**Warning signs:** A probe after probe 13 (parity) reports a query string in its output, or stdout shows captured queries from probes the patch was not meant to capture.

### Pitfall 7: Async `_async_main` running param capture re-opens the AsyncClient post-aclose

**What goes wrong:** The async param-capture happens AFTER the `finally: await aio.aclose()` in `_async_main`. The next call to `aio.get_movimientos(...)` lazily re-creates `_client`, which never gets closed.

**Why it happens:** Ordering. The capture must happen INSIDE `_async_main`, BEFORE the `aclose`.

**How to avoid:** The capture for async parity must be part of the `_async_main` probe sequence, executed BEFORE the `finally: await aio.aclose()` block. Then the captured query string is returned in the tuple consumed by `main()`. Same pattern Phase 3 used (`main_iol.py:1520-1539`).

**Warning signs:** `_client` not None after `_async_main` returns; or a `RuntimeError: Event loop is closed` if a re-opened client tries to close in a teardown.

### Pitfall 8: Cascade SKIPPED on async login NOT propagated back to sync probes that already ran

**What goes wrong:** `probe_login_sync` PASSES; `probe_login_async` FAILS and sets `_auth_failed`. All async-only probes get SKIPPED, but sync probes already ran (they happened first in main() ordering).

**Why it happens:** Single shared flag, not surface-segregated.

**How to avoid:** Accept this asymmetry. It is the Phase 3 D-IOL-3 Discretion choice: single flag is the stricter cascade (a downstream sync probe scheduled AFTER async login would also be SKIPPED). The actual ordering in main_iol.py is: probe 1 (sync login) → probe 2 (async login, batched inside asyncio.run) → probes 3+ in interleaved order. If sync passes and async fails, the sync probes that ran BEFORE async login are unaffected; the sync probes AFTER async login (probes 5, 7, 9, 11+) get SKIPPED. This is the documented behavior and the Phase 3 review accepted it. Phase 4 should mirror exactly.

**Warning signs:** Confusion about why sync probes after probe 2 appear SKIPPED. Document the asymmetry in the docstring of `probe_login_async`.

### Pitfall 9: `_resolved_cuenta` race — probe 5 fails, downstream probes get SKIPPED

**What goes wrong:** `probe_get_listado_cuentas_sync` returns `[]` (no accounts in `estado="alta"`), so `_resolved_cuenta` stays `None`. Probes 7, 9, 11 (movimientos, posicion_valuada, posiciones) all SKIPPED. The driver runs but produces little signal.

**Why it happens:** The sample account is required for the parametric endpoints.

**How to avoid:** The override env var `HIGYRUS_SAMPLE_CUENTA` (D-HIGY-14) lets the operator provide a known account. If neither the live listing nor the env var provides one, SKIPPED is the only correct behavior — emit a NO-DATA finding for visibility.

**Warning signs:** A run where 7/12 endpoint probes are SKIPPED. Inspect findings file for the NO-DATA fid.

### Pitfall 10: `probe_errors_envelope` consumes a 4xx attempt counter on the live server

**What goes wrong:** `probe_errors_envelope_sync` deliberately calls `get_movimientos("INVALID-CUENTA-XXXXX", ...)` expecting a 4xx. If the server tracks bad requests per IP, repeated driver runs accumulate.

**Why it happens:** Always-on probe.

**How to avoid:** D-HIGY-10 #16-17 mark these probes "always-on" but explicitly expecting `errors` envelope — NOT a 401/403/429. A 400/404 should not trigger rate-limit defenses. If the server does start rate-limiting bad account IDs, demote the probes to opt-in via a new env var. Out of scope for now.

**Warning signs:** A finding `RATE-LIMIT` or `429` from probes 16/17.

## Code Examples

### Example A: Driver skeleton (top-level, copy of Phase 3 pattern adapted to Higyrus)

```python
# Source: this RESEARCH.md, derived from main_iol.py:62-180 + adapted per D-HIGY-10/13/14/15.
"""Driver de verificación en vivo del paquete ``higyrus-client`` (Phase 4)."""

from __future__ import annotations

import asyncio
import contextlib
import datetime as dt
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from verification import require_env, safe_print, schema_of, write_findings
from verification.findings import append_finding

import higyrus_client
from higyrus_client import (
    HigyrusAPIError,
    HigyrusAuthError,
    aio,
)
from higyrus_client.models import Cuenta, Movimiento, Posicion, PosicionValuada

# Module-level constants
_PKG = "higyrus-client"
_REPO_ROOT = Path(__file__).resolve().parent
_SCHEMA_DIR = _REPO_ROOT / ".planning" / "verification" / "schemas" / _PKG
_SCHEMA_FILES: dict[str, Path] = {
    "get_health": _SCHEMA_DIR / "get-health.json",
    "get_listado_cuentas": _SCHEMA_DIR / "get-listado-cuentas.json",
    "get_movimientos": _SCHEMA_DIR / "get-movimientos.json",
    "get_posicion_valuada": _SCHEMA_DIR / "get-posicion-valuada.json",
    "get_posiciones": _SCHEMA_DIR / "get-posiciones.json",
}
_ENDPOINT_TEMPLATES: dict[str, str] = {
    "get_health": "/api/health",
    "get_listado_cuentas": "/api/cuentas/listadoCuentas",
    "get_movimientos": "/api/cuentas/{id_cuenta}/movimientos",
    "get_posicion_valuada": "/api/cuentas/{id_cuenta}/posicionValuada",
    "get_posiciones": "/api/cuentas/{id_cuenta}/posiciones",
}

_SAMPLE_CUENTA: str | None = os.getenv("HIGYRUS_SAMPLE_CUENTA")
_SAMPLE_TIPO_CUENTA: str = os.getenv("HIGYRUS_SAMPLE_TIPO_CUENTA", "propia")
_SAMPLE_NIVEL: str = os.getenv("HIGYRUS_SAMPLE_NIVEL", "detalle")

_fid_counter: int = 0
_auth_failed: bool = False
_auth_failure_reason: str = ""
_resolved_cuenta: str | None = None


def _next_fid() -> str:
    global _fid_counter
    _fid_counter += 1
    return f"F-{_fid_counter:02d}"


@dataclass(frozen=True, slots=True)
class ProbeResult:
    name: str
    status: str  # "PASS" | "FAIL" | "SKIPPED" | "FINDING"
    detail: str


# ... probes 1-18 ...


async def _async_main(today: dt.date) -> tuple[Any, ...]:
    """All async probes + async param capture for HIGY-06 parity."""
    try:
        # Probe 2: login_async
        r_login_async = await probe_login_async()
        # Probes 4, 6, 8, 10, 12: async endpoint sweep
        r_health_async, _ = await probe_get_health_async()
        r_listado_async, listado_raw_async = await probe_get_listado_cuentas_async()
        r_movs_async, movs_raw_async = await probe_get_movimientos_async(today)
        r_pv_async, pv_raw_async = await probe_get_posicion_valuada_async(today)
        r_pos_async, pos_raw_async = await probe_get_posiciones_async(today)
        # Probe 13 async half: capture async query string for HIGY-06.
        async_query = await _capture_async_query_string(...)
        # Probe 17: errors envelope async
        r_errors_async = await probe_errors_envelope_async(today)
    finally:
        with contextlib.suppress(Exception):
            await aio.aclose()
    return (
        r_login_async,
        r_health_async, r_listado_async, r_movs_async, r_pv_async, r_pos_async,
        listado_raw_async, movs_raw_async, pv_raw_async, pos_raw_async,
        async_query,
        r_errors_async,
    )


def main() -> None:
    if not require_env(_PKG, ["HIGYRUS_USER", "HIGYRUS_PASSWORD", "HIGYRUS_BASE_URL"]):
        return

    today = dt.date.today()
    write_findings(_PKG)
    results: list[ProbeResult] = []

    # Probe 1: login sync.
    results.append(probe_login_sync())

    # Probes 2/4/6/8/10/12/17 in a single asyncio.run (D-HIGY-13).
    (
        r_login_async,
        r_health_async, r_listado_async, r_movs_async, r_pv_async, r_pos_async,
        listado_raw_async, movs_raw_async, pv_raw_async, pos_raw_async,
        async_query,
        r_errors_async,
    ) = asyncio.run(_async_main(today))

    # Probes 3/5/7/9/11 (sync); interleaved with async per D-HIGY-10 order.
    r_health_sync, _ = probe_get_health_sync()
    results.append(r_login_async)
    results.append(r_health_sync)
    results.append(r_health_async)

    r_listado_sync, listado_raw_sync = probe_get_listado_cuentas_sync()  # sets _resolved_cuenta
    results.append(r_listado_sync)
    results.append(r_listado_async)

    r_movs_sync, movs_raw_sync = probe_get_movimientos_sync(today)
    results.append(r_movs_sync)
    results.append(r_movs_async)

    r_pv_sync, pv_raw_sync = probe_get_posicion_valuada_sync(today)
    results.append(r_pv_sync)
    results.append(r_pv_async)

    r_pos_sync, pos_raw_sync = probe_get_posiciones_sync(today)
    results.append(r_pos_sync)
    results.append(r_pos_async)

    # Probe 13: parity sync↔async (drop_none deviation verification).
    sync_query = _capture_sync_query_string(...)
    results.append(probe_parity_sync_async(sync_query, async_query))

    # Probe 14: field_type_map (bidirectional diff).
    results.append(probe_field_type_map(
        listado_raw_sync[0] if listado_raw_sync else None,
        movs_raw_sync,
        pos_raw_sync,
        pv_raw_sync,
    ))

    # Probe 15: 5 schema snapshots.
    results.append(probe_schema_snapshot(
        today,
        {"keys": "TODO"},  # get_health raw payload
        listado_raw_sync,
        movs_raw_sync,
        pv_raw_sync,
        pos_raw_sync,
    ))

    # Probes 16, 17: errors envelope (always-on).
    results.append(probe_errors_envelope_sync(today))
    results.append(r_errors_async)

    # Probe 18: auth_401 LAST, opt-in.
    results.append(probe_auth_401())

    # Output with safe_print (D-HIGY-15).
    captured_token = higyrus_client.client._token
    secrets = [
        v for v in (
            os.getenv("HIGYRUS_USER"),
            os.getenv("HIGYRUS_PASSWORD"),
            captured_token,
        )
        if v and len(v) >= 4
    ]
    for r in results:
        safe_print(f"PROBE {r.name}: {r.status} {r.detail}".rstrip(), secrets=secrets)

    n_pass = sum(1 for r in results if r.status == "PASS")
    n_fail = sum(1 for r in results if r.status == "FAIL")
    n_skip = sum(1 for r in results if r.status == "SKIPPED")
    n_find = sum(1 for r in results if r.status == "FINDING")
    safe_print(
        f"SUMMARY: PASS={n_pass} FAIL={n_fail} SKIPPED={n_skip} FINDING={n_find}",
        secrets=secrets,
    )


if __name__ == "__main__":
    main()
```

### Example B: One of the 10 mocked regression tests for HIGY-04 (sync)

```python
# Source: this RESEARCH.md, derived from D-HIGY-9 specification and Phase 3 mocked-regression pattern.
# Append to packages/higyrus-client/tests/test_client.py under section
# `# ------ Regressions ------`.

import pytest
from pytest_httpx import HTTPXMock

import higyrus_client
from higyrus_client import HigyrusAPIError


def test_get_health_raises_on_list_payload(httpx_mock: HTTPXMock) -> None:
    """Regression: assert isinstance(raw, dict) reemplazado por HigyrusAPIError tipado (finding F-NN)."""
    httpx_mock.add_response(
        url="https://api.test/api/health",
        json=["unexpected", "list"],
    )
    with pytest.raises(HigyrusAPIError) as exc_info:
        higyrus_client.get_health()
    assert exc_info.value.status_code == 0
    assert exc_info.value.errors[0]["title"] == "shape mismatch"
    assert "expected dict" in exc_info.value.errors[0]["detail"]
    assert "got list" in exc_info.value.errors[0]["detail"]
```

### Example C: HIGY-06 mocked regression test (drop_none parity, sync)

```python
# Source: this RESEARCH.md.
# Locks the invariant that drop_none yields the same query string sync vs async
# when several optional params are None.

import datetime as dt
import pytest
from pytest_httpx import HTTPXMock

import higyrus_client


def test_get_movimientos_drop_none_emits_only_two_params(httpx_mock: HTTPXMock) -> None:
    """Regression: drop_none(params) emits only fechaDesde + fechaHasta when 4 optional params are None (finding F-NN)."""
    httpx_mock.add_response(
        url="https://api.test/api/cuentas/123/movimientos?fechaDesde=01%2F01%2F2026&fechaHasta=31%2F01%2F2026",
        json=[],
    )
    movs = higyrus_client.get_movimientos(
        id_cuenta="123",
        fecha_desde=dt.date(2026, 1, 1),
        fecha_hasta=dt.date(2026, 1, 31),
    )
    assert movs == []
    request = httpx_mock.get_requests()[0]
    assert set(dict(request.url.params).keys()) == {"fechaDesde", "fechaHasta"}
```

### Example D: HIGY-03 SafeModel tolerance test (lock for `from_api` invariant)

```python
# Source: this RESEARCH.md. D-HIGY-17 #2: lock the invariant that from_api substitutes typed defaults.
# Append to test_client.py under `# ------ Verified live (Phase 4) ------`.

from higyrus_client.models import Cuenta


def test_cuenta_from_api_partial_payload_returns_typed_defaults() -> None:
    """Verified live (Phase 4): Cuenta.from_api tolerates partial payloads with typed defaults."""
    payload = {"id": "CTA-001", "tipo": "comitente"}  # all other fields missing
    cuenta = Cuenta.from_api(payload)
    assert cuenta.id == "CTA-001"
    assert cuenta.tipo == "comitente"
    assert cuenta.titular == ""           # str default
    assert cuenta.alias == ""             # str default
    assert cuenta.domicilios == []        # list default
    assert cuenta.cuentasBancarias == []  # list default
    # Nested model substitutes empty instance via X.from_api(None):
    assert cuenta.administrador.operador.nombre == ""
    assert cuenta.administrador.operador.idExterno == ""
```

## State of the Art

| Old approach | Current approach | When changed | Impact |
|--------------|------------------|--------------|--------|
| Mocked tests only (Phase 0 baseline) | Driver + mocked, finding-classified, schema-snapshot lifecycle | Phase 1 (2026-05-28) | All Phases 2-5 use the same loop. |
| Findings file written by hand | `verification.findings.append_finding` idempotent helper | Phase 2 Plan 02-01 (2026-06-02) | Re-runnable; preserves human-promoted status. |
| Driver crashes on first error | D-04 lifecycle: every probe continues, exit 0 always | Phase 2 D-04 (2026-05-29) | Findings file is the output; runs cover the full surface. |
| `assert isinstance` for runtime invariants | Typed exceptions with sentinel `status_code` | Phase 4 (this phase) for higyrus; Phase 3 already did it for IOL via different mechanism | Production-safe under `python -O` which strips `assert`. |
| Anonymized committed fixtures | Schemas-only committed; gitignored captures for operator inspection | Phase 2 D-HIGY-1 carry-forward | PII-free by construction; no anonymization burden on contributors. |

**Deprecated/outdated:**

- **Existing `main_higyrus.py` smoke test** (lines 22-44): D-HIGY-10 fully rewrites. The current 48-line file is the smallest harness usage in the monorepo; it does NOT honor D-HIGY-2 (it prints model `__repr__` directly, exposing PII), does NOT register findings, does NOT capture schemas. Full rewrite is the right scope.
- **`assert isinstance` defensive pattern** (10 sites in client.py + aio.py): Replaced by HIGY-04 fix. Both `python -O` stripping and the "AssertionError is not the contract" argument apply. The fix is documented and the only invariant-breaking change in Phase 4.

## Assumptions Log

| # | Claim | Section | Risk if wrong |
|---|-------|---------|---------------|
| A1 | The default Higyrus base URL `https://cliente.aunesa.com/Irmo` (from `.env.example`) is reachable from the developer's machine during the live run. | Architecture diagram | [ASSUMED] If the URL is wrong or unreachable, login fails and cascade SKIPPED kicks in. Mitigation: cascade SKIPPED is the documented expected behavior. Operator can override with `HIGYRUS_BASE_URL` env var. |
| A2 | The 10 `assert isinstance(raw, list/dict)` line numbers in client.py (208, 244, 286, 313, 337) and aio.py (233, 264, 302, 325, 345) are stable through the lifetime of Phase 4. | Standard Stack — fix HIGY-04 site mapping | [VERIFIED: codebase grep] Confirmed by reading the files at the listed lines. If the user edits these files before the planner generates plans, line numbers must be re-verified. |
| A3 | `httpx.Request.url.query` returns `bytes` in httpx>=0.27 (verified API), so decode is required for string comparison. | Pattern 2 (Live param capture) | [CITED: httpx docs] `httpx.URL.query` is `bytes` in current httpx; decoded via `.decode("utf-8")`. If a future httpx breaks this, the test fails loudly (string comparison fails). Mitigation: defensive decode in the helper. |
| A4 | Higyrus Bearer token is 24h TTL and the existing 23h refresh (`_TOKEN_TTL_SECONDS = 23 * 60 * 60`) is correct. | Pattern 3 + general lifecycle | [CITED: INTEGRATIONS.md] Documented in `.planning/codebase/INTEGRATIONS.md` and confirmed by `client.py:56`. If the server reduces TTL, the lazy-auth refresh might trigger mid-run; Phase 4 driver does NOT verify TTL — out of scope (would be ERR-02 deferred). |
| A5 | The existing `_raise_for_response` in client.py:142-161 and aio.py:168-187 correctly parses `errors` and `timestamp` envelope from Higyrus 4xx payloads. | HIGY-05 always-on probe | [VERIFIED: codebase grep] Confirmed by reading the implementation. The existing test `test_login_credenciales_rechazadas` (`test_client.py:38-52`) already locks this invariant for a 401 case. Probe 16/17 is the live verification of the same path on a 4xx-by-invalid-id. |
| A6 | `HigyrusAuthError`, `HigyrusAuthorizationError`, `HigyrusRateLimitError` all derive from `HigyrusAPIError` (which takes `status_code, errors, timestamp`). | Patterns 4 and 5 | [VERIFIED: codebase grep] Confirmed in `exceptions.py:19-61`. |
| A7 | The driver running on the developer's machine has a Python version that supports `Self` (PEP 673) — i.e., Python 3.12+. | All code examples | [VERIFIED: CLAUDE.md + pyproject] Tech stack pins Python 3.12+. Confirmed. |
| A8 | The `_resolved_cuenta` sample from `cuentas[0].id` has data in `get_movimientos` for the last 30 days, `get_posicion_valuada` for today, and `get_posiciones` for today. | D-HIGY-12 date ranges | [ASSUMED] Depends on the operator's tenant. If an account has no data in 30d, `[]` is returned and HIGY-07 PASS path is exercised (D-HIGY-12 says empty is PASS). Risk: the bidirectional diff (probe 14) cannot inspect shapes that are not in the payload. Operator can override sample account via `HIGYRUS_SAMPLE_CUENTA`. |
| A9 | The `tipo_cuenta="propia"` and `nivel="detalle"` defaults for `get_posicion_valuada` are accepted by the operator's tenant. | D-HIGY-14 | [ASSUMED] Default values inferred from documentation pp. 49-52. If the operator's tenant uses different vocabulary (e.g., `tipo_cuenta="cuentaTitulares"`), the probe emits PARAM OPEN finding (D-HIGY-10 #9 explicitly calls this out). Operator can override via env vars. |
| A10 | The driver run is single-threaded; module-level `_fid_counter`, `_auth_failed`, `_resolved_cuenta` globals are safe. | Cascade SKIPPED pattern; ProbeResult propagation | [VERIFIED: arch precedent] Phase 2 and Phase 3 drivers use the same pattern. ARCHITECTURE.md confirms drivers are single-threaded by design. |

## Open Questions

1. **Should the param capture helper for HIGY-06 be inside the parity probe, or a separate utility?**
   - What we know: The reference implementation (Pattern 2) places `_capture_sync_query_string` / `_capture_async_query_string` as module-level helpers. The probe body calls them.
   - What's unclear: Whether the Planner should split them into a dedicated `_drop_none_inspector.py` module under `verification/` (rejected by D-HIGY-4 unless they prove reusable in Phase 5 / Matriz).
   - Recommendation: Keep inline in `main_higyrus.py` for Phase 4. Promote to `verification/` only if Phase 5 confirms reuse.

2. **What sample params to use for `probe_get_listado_cuentas`?**
   - What we know: D-HIGY-10 #5 says `estado="alta"` (the most useful filter). Discretion notes operator can leave unfiltered. The schema snapshot envelope D-21 records `sample_params: {"estado": "alta"}` for the file.
   - What's unclear: If the operator's tenant has zero accounts in `estado="alta"`, the unfiltered listing might still return some.
   - Recommendation: Use `estado="alta"` per D-HIGY-10 #5. If empty, emit a NO-DATA finding + retry unfiltered as a probe-internal fallback (with a finding for the fallback so it's auditable).

3. **Should the bidirectional diff path qualifier use leading dot (`.cuenta.administrador`) or not (`cuenta.administrador`)?**
   - What we know: D-HIGY-5 examples show LEADING dot (`.cuenta.administrador.operador.idExterno`, `.movimiento.idMovimientos[0]`). Discretion notes the format is open.
   - What's unclear: Whether the leading dot at the very root looks awkward.
   - Recommendation: Match the locked examples — leading dot. Stable convention.

4. **Should `_diff_safemodel_bidirectional` emit findings inline (via `append_finding` calls inside the recursion) or return an iterator of tuples consumed by the probe?**
   - What we know: Phase 2 emits inline (the probe body of `probe_field_type_map`). Phase 3 also emits inline. The reference implementation in this RESEARCH.md returns an iterator (more testable).
   - What's unclear: Whether the planner prefers testability (iterator) vs precedent (inline).
   - Recommendation: Iterator-based (the reference implementation). Easier to unit-test the diff itself without writing to the findings file. The probe consumes the iterator and calls `append_finding`.

5. **Does the `_resolved_cuenta` fallback (env var override) need a NO-DATA finding when neither the listing nor the env var provides one?**
   - What we know: D-HIGY-11 says "downstream SKIPPED if `_resolved_cuenta is None`". The finding class `NO-DATA` exists for exactly this case.
   - What's unclear: Whether the SKIPPED status alone is sufficient documentation, or whether a NO-DATA finding should also be emitted.
   - Recommendation: Emit a single NO-DATA finding from `probe_get_listado_cuentas_sync` when the listing is empty and the env var is unset. Easier for the human triage cycle to see why downstream probes were SKIPPED.

## Environment Availability

The phase requires the Higyrus live API to be reachable and the operator to have valid credentials. Local tooling is already in place (verified by Phase 3 completion).

| Dependency | Required by | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12+ | All driver and test code | ✓ | 3.12.11 (active venv) per CLAUDE.md | — |
| uv 0.9.0+ | Workspace install | ✓ | 0.9.0 per CLAUDE.md | — |
| httpx >=0.27 | HTTP transport sync+async | ✓ | pinned in uv.lock | — |
| pytest 8.3+ / pytest-httpx 0.34+ / pytest-asyncio 0.24+ | Regression tests | ✓ | pinned in uv.lock | — |
| `verification/*` harness | Findings, schema, redaction, env gate | ✓ | Phases 1+2 already committed | — |
| Higyrus credentials (`HIGYRUS_USER`, `HIGYRUS_PASSWORD`, `HIGYRUS_BASE_URL`) | Live run | ⚠ (operator-supplied; via `packages/higyrus-client/.env` per CLAUDE.md) | — | If missing → `require_env` prints `SKIPPED higyrus-client: missing ...` and exit 0 (HARN-01 pattern; same as Phase 3). Plans 1 (fix) and 3 (mocked tests) do NOT require credentials; only Plan 2 driver-execution + Plan 3 live-run task. |
| Network reachability to `cliente.aunesa.com` | Live driver run | ⚠ (network-dependent) | — | If unreachable → live run fails at login; cascade SKIPPED triggers; driver exits 0; operator retries. |
| `HIGYRUS_SAMPLE_CUENTA` (optional) | Override the auto-resolved account | optional | — | If unset → driver uses `cuentas[0].id`; if listing empty → SKIPPED downstream. |
| `VERIFY_HIGYRUS_BAD_CREDS=1` (optional) | Activates probe_auth_401 | optional | — | If unset → probe 18 SKIPPED (D-HIGY-10 #18). |

**Missing dependencies with no fallback:** none — every missing dependency has a documented skip-and-continue path inherited from Phase 1 HARN-01.

**Missing dependencies with fallback:** the credentials and the live network access. Both fall back to `SKIPPED` lines that don't block Plan 1 (fix code-only) or Plan 3 (mocked tests).

## Validation Architecture

Nyquist Dimension 8 (invariantes verificables tras el run) requires every phase requirement to be testable, sampled at the right cadence, and tied to either a unit test or a documented live-driver invariant. Phase 4 is enabled (`workflow.nyquist_validation: true` in `.planning/config.json`).

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.3+ + pytest-httpx 0.34+ + pytest-asyncio 0.24+ + pytest-cov 6.0+ |
| Config file | root `pyproject.toml` `[tool.pytest.ini_options]` (`asyncio_mode = "auto"`, `--strict-markers`, `--import-mode=importlib`) |
| Quick run command | `uv run pytest -q packages/higyrus-client/tests` |
| Full suite command | `uv run pytest -q` (all 5 packages) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test type | Automated command | File exists? |
|--------|----------|-----------|-------------------|--------------|
| HIGY-01 | login() + lazy-auth in sync surface | unit | `uv run pytest -q packages/higyrus-client/tests/test_client.py::test_login_obtiene_y_cachea_token` | ✅ (existing test_client.py:18) |
| HIGY-01 | login() + lazy-auth in async surface | unit | `uv run pytest -q packages/higyrus-client/tests/test_async_client.py::test_async_login_obtiene_token` | ✅ (existing test_async_client.py:17) |
| HIGY-01 | login() captures token from real Higyrus | live driver invariant | manual: `uv run --package higyrus-client python main_higyrus.py` (Probe 1+2 PASS) | ❌ Plan 2 (driver rewrite) |
| HIGY-02 | URL emitted for each endpoint locks the path + query string | unit | `uv run pytest -q packages/higyrus-client/tests/test_client.py -k get_movimientos or get_posiciones` | partial — existing tests cover get_movimientos URL + get_posiciones URL. Wave 0 gap: get_health, get_listado_cuentas, get_posicion_valuada URL locks. |
| HIGY-02 | sync+async happy-path against live | live driver invariant | manual: PROBE happy_*_sync/async PASS | ❌ Plan 2 |
| HIGY-03 | bidirectional diff finds zero `model \ wire` keys on the live payload (or only the documented OPEN findings) | live driver invariant | manual: PROBE field_type_map PASS or FINDING (OPEN) | ❌ Plan 2 |
| HIGY-03 | SafeModel.from_api tolerates partial payload — typed defaults | unit | `uv run pytest -q packages/higyrus-client/tests/test_client.py::test_cuenta_from_api_partial_payload_returns_typed_defaults` | ❌ Wave 0 — append to test_client.py per D-HIGY-17 |
| HIGY-04 | get_health raises HigyrusAPIError(0) on list payload | unit (regression) | `uv run pytest -q packages/higyrus-client/tests/test_client.py::test_get_health_raises_on_list_payload` | ❌ Plan 1 (Regressions section) |
| HIGY-04 | get_movimientos/get_listado_cuentas/get_posiciones/get_posicion_valuada raise on dict payload | unit (regression) | `uv run pytest -q packages/higyrus-client/tests/test_client.py::test_get_*_raises_on_*` | ❌ Plan 1 — 4 sync tests + 4 async = 8 more (10 total) |
| HIGY-05 | errors envelope parsed: status_code + errors + timestamp captured | unit | `uv run pytest -q packages/higyrus-client/tests/test_client.py::test_login_credenciales_rechazadas` | ✅ existing test_client.py:38 |
| HIGY-05 | errors envelope verified on live 4xx (invalid id_cuenta) | live driver invariant | manual: PROBE errors_envelope_*_sync/async PASS | ❌ Plan 2 |
| HIGY-06 | sync+async drop_none emit identical query strings | unit (mocked) | `uv run pytest -q packages/higyrus-client/tests/test_client.py::test_get_movimientos_drop_none_emits_only_two_params` (+ async mirror) | ❌ Plan 3 (Verified-live section) |
| HIGY-06 | sync+async live param capture identical | live driver invariant | manual: PROBE parity_sync_async PASS | ❌ Plan 2 |
| HIGY-07 | 204 returns empty list, not None | unit | `uv run pytest -q packages/higyrus-client/tests/test_client.py::test_get_listado_cuentas_204_devuelve_lista_vacia` | ✅ existing test_client.py:108 |
| HIGY-07 | empty list returned from live endpoint (HIGY-07 PASS path) | live driver invariant | manual: PROBE happy_* PASS with `(0 items — empty path verified)` | ❌ Plan 2 |

### Sampling Rate

- **Per task commit:** `uv run pytest -q packages/higyrus-client/tests` (~20-30 tests including new ones; sub-30s)
- **Per wave merge:** `uv run pytest -q && uv run mypy && uv run ruff check && uv run ruff format --check` (full suite; ~few minutes)
- **Phase gate:** Full suite green + live driver run successful (operator-observed) before `/gsd-verify-work`.

### Wave 0 Gaps

These test files / sections do not exist yet and must be created in the appropriate plan:

- [ ] `packages/higyrus-client/tests/test_client.py` — append `# ------ Verified live (Phase 4) ------` section with HIGY-02/HIGY-03/HIGY-06/HIGY-07 invariants (Plan 3)
- [ ] `packages/higyrus-client/tests/test_client.py` — append `# ------ Regressions ------` section with 5 HIGY-04 sync regressions (Plan 1 — fix first; Plan 3 appends)
- [ ] `packages/higyrus-client/tests/test_async_client.py` — mirror of above (5 async regressions + async Verified-live tests)
- [ ] `main_higyrus.py` — full rewrite per D-HIGY-10 (Plan 2)
- [ ] `.planning/verification/schemas/higyrus-client/{get-health,get-listado-cuentas,get-movimientos,get-posicion-valuada,get-posiciones}.json` — generated by Plan 2 live run, committed in Plan 3
- [ ] `.planning/verification/higyrus-client-findings.md` — generated by Plan 2 live run, committed in Plan 3
- [ ] `packages/higyrus-client/.env.example` — append optional env vars per D-HIGY-14 (Plan 2)

*Note:* No framework install needed; pytest + pytest-httpx already cover. The existing autouse fixtures in `packages/higyrus-client/tests/conftest.py` work as-is for the new Verified-live + Regressions tests.

## Security Domain

`security_enforcement: true` and `security_asvs_level: 1` are explicitly set in `.planning/config.json`. Phase 4 inherits the 27 mitigations Phase 3 closed (`03-SECURITY.md`) and adds Higyrus-specific threats.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Single Bearer token cached at module level; `configure(password=...)` resets cache. Probe `auth_401` opt-in single-shot pattern (Pattern 5) prevents lockout — exactly the same control posture as Phase 3 T-3-09. |
| V3 Session Management | yes (limited) | No HTTP session/cookies; only the 24h Bearer. The 23h refresh window (`_TOKEN_TTL_SECONDS = 23*3600`) avoids the boundary edge. No state to manage beyond `_token`/`_token_ts`. |
| V4 Access Control | no | Phase 4 does not implement any access control; the API enforces it server-side. The driver and tests use the operator's credentials; no privilege boundaries inside the codebase. |
| V5 Input Validation | yes | Bidirectional diff (Pattern 1) IS a structural input validation: the wire shape is validated against the model contract. Fix HIGY-04 adds runtime type validation for the top-level shape (`HigyrusAPIError(0, ...)` on shape mismatch). |
| V6 Cryptography | no | TLS is provided by `httpx` defaults (HTTPS). Phase 4 does not implement any cryptographic primitives. |
| V7 Error Handling and Logging | yes | `safe_print` two-layer redaction prevents secrets in stdout. Findings file never carries raw payload values (D-HIGY-2 forbids in driver; T-3-19/T-3-20 inherited from Phase 3). |
| V8 Data Protection | yes | **THIS IS THE NEW DIMENSION FOR PHASE 4** — first ciclo with real PII. See "PII threat surface" below. |
| V14 Configuration | yes | `.env` files NEVER committed; existing `.gitignore` posture verified Phase 1. Per-package `.env.example` shows required variables only. |

### Known Threat Patterns for the Phase 4 Stack

| Pattern | STRIDE | Standard Mitigation | Phase 4 Status |
|---------|--------|---------------------|----------------|
| Real PII in stdout (titular, CBU, addresses, personasRelacionadas) | Information Disclosure | D-HIGY-2 LOCKED: driver stdout = counts + shape descriptors only; never values. `safe_print` two-layer redaction. | **NEW Phase 4 threat T-4-PII.** Inherits Phase 3 T-3-13/T-3-14 controls and adds the "no raw model __repr__ in print" invariant. |
| Real PII in findings file `actual=`/`diff=` fields | Information Disclosure | D-HIGY-2 + Pattern 1 implementation passes only `keys=[sorted_key_list]` and type names (never values) to `append_finding`. | **NEW Phase 4 threat T-4-FINDINGS-PII.** Inherits Phase 3 T-3-19 control. The bidirectional diff helper MUST NOT pass `payload[key]` (the value) — only the key NAME and type information. |
| Real PII in committed schema files | Information Disclosure | `schema_of` PII-free by construction (only type names). | Inherits Phase 3 T-3-20 control. Already CLOSED by construction. |
| Real PII in gitignored `captures/` exposed accidentally | Information Disclosure | `.planning/verification/captures/` in `.gitignore` (verified by Phase 1 D-11). Operator inspection allowed; commit forbidden by construction. | Already mitigated. Operator discipline: do NOT `git add -f captures/`. |
| Bearer token reflected by payload (Higyrus echoes the JWT-like Bearer in some error responses) | Information Disclosure | `_BEARER` regex catch-all in `safe_print` (`verification/redaction.py:31`) covers reflected `Bearer <token>` even if the token is not in the `secrets` list. | Inherits Phase 3 T-3-13 control. |
| Real password in stack trace from `HigyrusAuthError(401, payload)` | Information Disclosure | `_raise_for_response` constructs the exception from `resp.json()` `errors`/`timestamp` — not from credentials. `safe_print` `secrets=[HIGYRUS_PASSWORD, ...]` masks any reflected value. | Inherits Phase 3 T-3-16 control. |
| Account lockout from repeated bad-creds probe | DoS (against self) | Opt-in via `VERIFY_HIGYRUS_BAD_CREDS=1` + single-shot (no retry/sleep/loop) + LAST in sequence (Pattern 5). | **NEW Phase 4 threat T-4-LOCKOUT.** Inherits Phase 3 T-3-09 control verbatim. |
| Cascade SKIPPED masks root cause | Repudiation | Probe 1/2 emit AUTH OPEN finding on `HigyrusAuthError` BEFORE setting `_auth_failed`. Human sees the cause in findings.md. | Inherits Phase 3 T-3-15 control. |
| Driver-side fix HIGY-04 introduces a behavior change (AssertionError → HigyrusAPIError) | Tampering (with caller assumptions) | Documented in D-HIGY-7 docstring justification: `AssertionError` was never part of the contract; the documented hierarchy IS `HigyrusClientError → HigyrusAPIError → ...`. Callers correctly catch the base. | **NEW Phase 4 threat T-4-CONTRACT-CHANGE.** Mitigation: documented in the exception docstring per D-HIGY-8. |
| `_diff_safemodel_bidirectional` recurses into untrusted data and crashes the driver | DoS (against self) | Wrap probe body in `try/except Exception` per D-04. Test the helper with adversarial inputs (cycles via recursion limit, very deep nesting). | **NEW Phase 4 threat T-4-DIFF-DOS.** Mitigation: standard probe except-Exception envelope. |
| Param capture monkey-patch leaks to other modules | Tampering | Try/finally restore on the same `_client.request` bound method (Pattern 2). | **NEW Phase 4 threat T-4-PATCH-LEAK.** Mitigation: try/finally invariant. |
| Drift detection silently overwrites baseline | Tampering | `_write_or_check_schema` D-25 no-overwrite invariant. | Inherits Phase 3 T-3-12 control. |

### Phase 4 New Threats (proposed threat register entries for plans)

The Planner must include `<threat_model>` blocks in each plan. Proposed threat IDs (matching the Phase 3 convention `T-N-NN`):

- **T-4-01** (Information Disclosure): driver prints real PII via model `__repr__`. Mitigation: D-HIGY-2 + `safe_print(..., secrets=[HIGYRUS_USER, HIGYRUS_PASSWORD, _token])`. Test: grep driver for `safe_print` count >= 2; grep for `f"...{cuenta}"` or similar (manual code review at checkpoint).
- **T-4-02** (Information Disclosure): findings file `actual=` / `diff=` contains raw PII. Mitigation: bidirectional diff passes only key NAMES (sorted list) and type names — never values. Test: post-run grep of findings.md for known PII patterns (CBU regex `^\d{22}$`, etc.) confirms zero hits.
- **T-4-03** (DoS / Lockout): `probe_auth_401` runs in loop / on every commit. Mitigation: opt-in env var + LAST-in-sequence + single-shot. Test: grep driver for `time.sleep`, `for _ in range`, `while`; assert zero in `probe_auth_401`.
- **T-4-04** (Tampering): HIGY-04 fix introduces wrong exception type. Mitigation: 10 mocked regression tests assert `status_code == 0` and `errors[0]["title"] == "shape mismatch"`. Test: tests verbatim.
- **T-4-05** (Tampering / Pitfall 6): param capture monkey-patch not restored on exception. Mitigation: try/finally bound-method restore. Test: post-call assertion `_client.request is original_request`.
- **T-4-06** (DoS / Pitfall 5): bidirectional diff infinite recursion on cyclic model. Mitigation: SafeModel models are acyclic dataclasses (`@dataclass(frozen=True, slots=True)`); recursion bounded by `get_type_hints` depth. No mitigation needed beyond standard except-Exception envelope. Test: probe envelope swallows recursion errors.
- **T-4-07** (Repudiation): cascade SKIPPED masks root cause. Mitigation: emit AUTH OPEN BEFORE setting `_auth_failed`. Test: findings file contains the AUTH OPEN row.
- **T-4-08** (Information Disclosure / Pitfall 4): empty list samples for nested SafeModel cause direction A flood. Mitigation: empty list IS HIGY-07 PASS; recursion guard `if isinstance(nested_payload, list) and nested_payload`. Test: unit test on diff helper with empty `domicilios: []` payload — emits zero findings.
- **T-4-SC** (Tampering): supply-chain package installs. Mitigation: ACCEPTED — no new packages in Phase 4 (see Package Legitimacy Audit).

These threat IDs are PROPOSED for the planner. The exact numbering may be adjusted by `gsd-secure-phase`; what matters is that each threat appears with a `mitigate` or `accept` disposition.

## MVP Slice Composition (Vertical vs Horizontal)

The Planner has a choice: organize the work as vertical slices (per-endpoint: probe + fix + regression for each of 5 endpoints) or horizontal layers (all probes, then all fixes, then all tests). Phases 2 and 3 used horizontal layers (3 plans each). Phase 4 should follow the same pattern.

**Recommended: Horizontal 3-plan layout.**

| Plan | Subsystem | Wave | Description | Verification |
|------|-----------|------|-------------|--------------|
| 04-01 | higyrus-fix | Wave 1 | Fix HIGY-04 dual sync+async at 10 sites + 10 mocked regression tests + update HigyrusAPIError docstring | `uv run pytest -q packages/higyrus-client/tests` (existing 8 tests + 10 new regressions = 18+ passing) |
| 04-02 | higyrus-driver | Wave 2 | Rewrite `main_higyrus.py` with 18 probes per D-HIGY-10; introduce `_diff_safemodel_bidirectional` helper; ALL helpers (`_capture_sync_query_string`, etc.); update `.env.example` | `uv run mypy main_higyrus.py` + `uv run ruff check main_higyrus.py` (driver-static-only; live run is Plan 3) |
| 04-03 | higyrus-verification | Wave 3 (contains human checkpoint) | Append Verified-live + (re-arrange) Regressions sections to test_client.py / test_async_client.py; live driver run; human checkpoint inspecting findings + 5 schemas; commit baseline | Full suite green + manual driver run produces 5 schema files + 1 findings file; commit them after human approval |

**Why horizontal over vertical:**

- **Cohesion of the fix:** HIGY-04 is ONE conceptual fix replicated across 10 sites + 10 tests. A vertical slice (per-endpoint) would scatter the fix change across 5 plans; horizontal puts it all in Plan 1 where it can be code-reviewed as one diff.
- **Cohesion of the driver:** The 18 probes interact (cascade SKIPPED flag, `_resolved_cuenta` propagation, `_async_main` ordering). Splitting them across 5 vertical plans creates tangled merge dependencies. Horizontal keeps the driver in one Plan 2.
- **Phase 2/3 precedent worked:** Phase 2 was 3 plans (helper + driver + commit), Phase 3 was 3 plans (fix + driver + commit). Both reviewed cleanly. Phase 4 has the same structure: helper-equivalent is fix (Plan 1), driver (Plan 2), commit + tests (Plan 3).
- **Human checkpoint placement:** The checkpoint naturally lives in Plan 3 between live-run + commit (Phase 2/3 pattern). Vertical slicing would force 5 checkpoints, increasing operator friction.

**Wave dependencies (planner consumes this):**

- Wave 1 = Plan 04-01 alone (no dependencies on driver).
- Wave 2 = Plan 04-02 (depends on Wave 1 because the driver imports `HigyrusAPIError` and the new shape-mismatch behavior. If the fix is applied, the driver assertions of `e.status_code == 0` are stable. Without Plan 1, Plan 2 would race against unfixed asserts. Therefore Plan 1 BEFORE Plan 2.)
- Wave 3 = Plan 04-03 (depends on Waves 1+2; contains the human checkpoint after the live run).

If the user prefers a single-plan MVP (one big plan), the structure still works but loses the cohesion of the per-plan code review. **Strong recommendation: 3 plans, horizontal.**

## Sources

### Primary (HIGH confidence)

- `.planning/phases/04-higyrus-verification/04-CONTEXT.md` — D-HIGY-1..D-HIGY-18 locked decisions [VERIFIED: file read in this session]
- `.planning/REQUIREMENTS.md` §"Verificación higyrus-client (HIGY)" — HIGY-01..07 [VERIFIED: file read]
- `.planning/ROADMAP.md` §"Phase 4: Higyrus Verification" — 5 success criteria, mode (mvp) [VERIFIED: file read]
- `.planning/phases/02-mbito-verification/02-CONTEXT.md` — D-01..D-26 base lifecycle [VERIFIED: file read]
- `.planning/phases/02-mbito-verification/02-01-SUMMARY.md` — `append_finding` design [VERIFIED]
- `.planning/phases/02-mbito-verification/02-02-SUMMARY.md` — Phase 2 driver structure [VERIFIED]
- `.planning/phases/02-mbito-verification/02-03-SUMMARY.md` — Verified-live + Regressions sections [VERIFIED]
- `.planning/phases/02-mbito-verification/02-REVIEW.md` — CR-01/CR-02/WR-04 post-mortem fixes already merged into helper [VERIFIED]
- `.planning/phases/03-iol-verification/03-CONTEXT.md` — D-IOL-1..D-IOL-22 patterns Phase 4 mirrors [VERIFIED]
- `.planning/phases/03-iol-verification/03-SECURITY.md` — 27 mitigations baseline [VERIFIED]
- `.planning/phases/03-iol-verification/03-02-SUMMARY.md` — IOL driver structure (mirror target) [VERIFIED]
- `main_iol.py` — implemented reference driver (1666 lines, all patterns Phase 4 mirrors) [VERIFIED]
- `packages/higyrus-client/src/higyrus_client/{client,aio,models,exceptions,_params}.py` — target of verification [VERIFIED: each file read in this session]
- `packages/higyrus-client/tests/{conftest,test_client,test_async_client}.py` — existing mocked tests [VERIFIED]
- `verification/{findings,schema,redaction,env_gate,capture}.py` — harness source [VERIFIED]
- `.planning/verification/FINDINGS-TEMPLATE.md` — finding file format [VERIFIED]
- `.planning/codebase/{INTEGRATIONS,TESTING,CONVENTIONS,CONCERNS,ARCHITECTURE}.md` — codebase maps [VERIFIED]
- `.planning/config.json` — `workflow.nyquist_validation: true`, `workflow.security_enforcement: true`, `workflow.security_asvs_level: 1` [VERIFIED]
- `CLAUDE.md` — project constraints (Python 3.12+, uv, httpx, ruff line-length=100, mypy strict) [VERIFIED]

### Secondary (MEDIUM confidence)

- `httpx >= 0.27` documentation — `httpx.Request.url`, `httpx.URL.query` is `bytes`. [CITED: httpx official docs — used here in Pattern 2 reference implementation. Not independently re-verified in this session; if the planner has access to Context7, recommend re-confirming the API surface.]

### Tertiary (LOW confidence)

None. Every claim above is grounded in committed source files in the repository.

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — every library already pinned in `uv.lock`, version constraints unchanged from Phases 2-3.
- Architecture: HIGH — patterns are direct mirrors of Phase 3 with the 4 net-new mechanisms isolated and exemplified inline.
- Pitfalls: HIGH — 10 pitfalls catalogued from Phase 2 and Phase 3 reviews, plus the FALSE PASS trap unique to Phase 4.
- Bidirectional diff implementation: MEDIUM-HIGH — reference implementation is correct against `higyrus_client.models` source as read in this session, but the path qualifier format and the Optional handling are recommendations (D-HIGY-5 discretion allows variation).
- Param capture for HIGY-06: MEDIUM — the monkey-patch approach works; whether the planner prefers it over an event-hook variant is a discretion point.
- Security: HIGH — inherits Phase 3’s 27 closed mitigations + 9 new Phase 4-specific threats catalogued.
- MVP slice composition: HIGH — Phase 2/3 precedent is the strongest signal.

**Research date:** 2026-06-06
**Valid until:** 2026-07-06 (30 days; stable phase patterns, no fast-moving dependencies)
