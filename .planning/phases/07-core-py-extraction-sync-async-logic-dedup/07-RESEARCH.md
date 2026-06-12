# Phase 7: `_core.py` Extraction — Sync/Async Logic Dedup - Research

**Researched:** 2026-06-12
**Domain:** Python sync/async client refactor — extracción de helpers puros a `_core.py` por paquete (4 paquetes), cierre de CR-03 (resource leak en matriz `_request`) y CR-05 (18 sweep probes en `main_matriz.py`).
**Confidence:** HIGH

## Summary

Phase 7 es un refactor 100% mecánico apoyado en infraestructura ya construida en Phase 6: cada paquete (ámbito, iol, higyrus, matriz) ya tiene `_state.py` con `_ClientState`, `Client`/`AsyncClient` con `__init__/__enter__/__exit__/aclose`, PEP 562 `__getattr__` shim, y aliases `_raise_for_response`/`_unwrap` module-level stateless (patrón B8). El trabajo de Phase 7 es: (a) **mover** estos helpers stateless a `_core.py`, (b) **extraer** builders puros `build_<endpoint>_request(state, ...) → RequestSpec` y parsers `parse_<endpoint>_response(resp) → typed result` por endpoint, (c) **colapsar** `client.py`/`aio.py` a transport shells que sólo dispatch `httpx.Client.request(...)` vs `await httpx.AsyncClient.request(...)`, (d) **cerrar CR-03** consumiendo body explícito en `_core.parse_envelope_response` antes de cualquier raise, (e) **cerrar CR-05** refactorizando 18 probes a `_envelope_probe(envelope_key=...)` en `main_matriz.py` preservando las 2 risk probes (`get_detailed_positions`, `get_account_report`).

Toda la investigación confirma que el patrón Phase 7 es zero-risk technical: los helpers stateless ya están comprobados (B8 funciona, tests `aio._raise_for_response is client._raise_for_response` están verdes), `import-linter` v2.11 está disponible en PyPI con soporte oficial para `[tool.importlinter]` en pyproject.toml y contratos `forbidden`, y los 393 tests baseline (Phase 6 — no 277 como dice el upstream context) pueden mantenerse verdes vía D-04 alias re-export. El único `[ASSUMED]` significativo es el LOC drop esperado por paquete (≥30% agregado client+aio) — la cifra de drop real sólo se sabrá al ejecutar el refactor; el research **recomienda** que el planner instrucione `wc -l` per archivo + ratio agregado como métrica observable post-commit.

**Primary recommendation:** Usar `import-linter>=2.11` con configuración en `[tool.importlinter]` de `pyproject.toml` raíz (4 contratos `forbidden`, uno por paquete). Construir `_core.py` por paquete siguiendo este orden estricto: (1) mover `_raise_for_response`/`_unwrap` con shim alias (zero churn), (2) extraer `RequestSpec` per-package frozen dataclass con slots=True, (3) extraer auth-flow primitives (`build_login_request` + `parse_login_response`, iol agrega `_refresh_*`), (4) extraer endpoint builders/parsers agrupados por sección del docstring API (matriz §4/§5/§6/§7/§9), (5) colapsar shells. matriz NO recibe `aio.py` refactor (es stub Phase 6 → Phase 10); matriz `_core.py` SÍ se construye y se prepara para que Phase 10 consuma sin copy-paste (Pitfall 8).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01: Per-package `RequestSpec` dataclasses.** Cada paquete define su propio `@dataclass(frozen=True, slots=True) RequestSpec` en su `_core.py` con los fields que necesita (matriz: `auth_basic: tuple[str, str] | None`; iol: refresh-aware; higyrus: `json_body` + URL-encoding flag; ámbito: minimal). **NO** hay shared `RequestSpec` cross-package — consistente con la project constraint "no shared internals between packages". Forward-compat con Phase 8: cuando RELY-03 (`idempotent: bool = False`) aterrice, cada RequestSpec lo agrega independientemente (4× replicación; aceptado).

**D-02: Auth-flow factorizado como builders + parsers puros.** `_core.build_login_request(state) → RequestSpec` + `_core.parse_login_response(status, body, headers) → (token, expires_at, refresh_token?)`. El transport shell ejecuta el HTTP call (`httpx.Client.post(...)` sync o `await httpx.AsyncClient.post(...)` async) y feed al parser. iol agrega `_core.build_refresh_request(state) → RequestSpec` + `_core.parse_refresh_response(...) → (token, expires_at, refresh_token?)` (mismo patrón). `_core.py` 100% sin I/O.

**D-03: Shell `_request` retorna `httpx.Response` cruda.** Endpoint method llama `_core.parse_<endpoint>(resp) → typed result` que hace `resp.read()` + `.json()` + valida shape + raise typed exception si aplica + retorna typed result. Cambia el contrato actual de higyrus (devolvía `dict | list | None`) y matriz (devolvía `dict`) — ahora todos retornan Response. **Plus:** Phase 8 retry transport puede inspeccionar `resp.status_code` / `resp.headers` libremente (e.g., `Retry-After`).

**D-04: Helpers stateless se mueven a `_core.py` con shim re-export.** `_core.raise_for_response` y `_core.unwrap` son las fuentes únicas. `client.py` define aliases module-level: `_raise_for_response = _core.raise_for_response` (los 3 paquetes con auth) y `_unwrap = _core.unwrap` (matriz). Tests y `main_matriz.py` que importan `_unwrap` directamente siguen funcionando. Snapshot público igual.

**D-05: Endpoint groups = secciones del docstring del API.** La métrica "≤30-50 LOC por endpoint group" del success-criterion #3 se mide por secciones existentes en `client.py`/`aio.py` (matriz: `§4 Segments`, `§5 Instruments`, `§6 Orders`, `§7 Market Data`, `§9 Risk`; higyrus: Cuentas, Movimientos, Posiciones; iol: Quotes, Instruments; ámbito: Cotizaciones). Cada group post-refactor ≤30-50 LOC en el shell.

**D-06: CR-03 absorbido por `_core.parse_envelope_response`.** El parser ejecuta `resp.read()` explícito, luego `resp.json()`, luego check `if raw["status"] == "ERROR": raise PrimaryAPIError(...)`. Body 100% consumido antes de cualquier raise. Shell sólo dispara `data = _core.parse_envelope_response(resp, endpoint_path)`. Self-contained: futuro `http2=True` no requiere auditoría del flow.

**D-07: CR-05 `_envelope_probe` driver-only en `main_matriz.py`.** Signature: `_envelope_probe(name: str, path: str, *, envelope_key: str | None = None, model_from_api: Callable[[Any], Any] | None = None) -> ProbeResult`. Las 2 risk probes (`probe_get_detailed_positions`, `probe_get_account_report`) pasan `envelope_key=None` (omite `_unwrap`). `verification/` NO recibe la promotion (otros drivers no la consumen).

**D-08: Refactor 18 probes atomic en el plan matriz.** El plan REFAC-03 matriz incluye en el MISMO commit: `_core.py` extraction + CR-03 fix + `_envelope_probe` helper + 18 probes migradas + snapshot test guard. Snapshot test pre-refactor registra `ProbeResult(name, status, ...)` de cada probe contra payload canned vía `pytest-httpx`. Si algo rompe, revert atómico del commit.

**D-09: `import-linter` declarativo bloquea `_core.py → client.py`/`aio.py` imports.** Library `import-linter` agregada a `[dependency-groups] dev` del root `pyproject.toml`. Config en `[tool.importlinter]` del root o en `.importlinter`. 4 contracts: `<pkg>._core` forbids `<pkg>.client`, `<pkg>.aio` (uno por paquete). CI step `lint-imports` en `.github/workflows/ci.yml`.

**D-10: Cross-leak sentinel test parametrizado en `verification/test_sync_async_isolation.py`.** 1 archivo cross-cutting, parametrize sobre `["iol_client", "higyrus_client", "ambito_financiero_client", "matriz_client"]`. Por paquete: configure sync con token `"SYNC-sentinel-<pkg>"`, configure async con token `"ASYNC-sentinel-<pkg>"`, fire 1 request en cada surface, assert wire header (auth nativo de cada paquete) tiene el sentinel correspondiente.

**D-11: matriz `pytest.skip` con motivo explícito.** El test parametrizado para matriz skip con reason `"matriz aio.py REST stub hasta Phase 10 REFAC-04 + TokenStore"`. Visible en CI output, no silenciado, forward-tracked. Plan Phase 10 explicitará "des-skip matriz" como tarea cuando aio.py REST aterrice.

**D-12: 6 planes en la phase.** Plan 1 — CI gates infrastructure (tests-only, import-linter setup + 4 contracts + `verification/test_sync_async_isolation.py` parametrizado). Plan 2 — REFAC-03 ámbito (canary). Plan 3 — REFAC-03 iol (auth-flow más complejo). Plan 4 — REFAC-03 higyrus (URL-encoding quirks). Plan 5 — REFAC-03 matriz + CR-03 + CR-05 (ATOMIC). Plan 6 — CI green gate consolidation.

**D-13: Orden serial idem Phase 6.** ámbito → iol → higyrus → matriz.

**D-14: LOC metric per-package vs Phase 6 baseline.** Baseline = `wc -l packages/<pkg>/src/<pkg>/{client,aio}.py` en HEAD del commit final de Phase 6. Cada plan SUMMARY.md incluye drops. Success-criterion ≥30% drop **agregado client+aio** por paquete.

**D-15: ámbito recibe full refactor `_core.py` como canary.** Aunque no tiene auth, tiene parsing duplicado.

**D-16: `_core.py` NO aparece en `verification/test_public_surface.py`.** Re-export shims (`_raise_for_response`, `_unwrap`) preservados. Snapshot iguale 1:1 vs Phase 6.

### Claude's Discretion

- Estructura interna exacta de cada `_core.py` — orden, agrupación. Recomendar agrupar por sección del API (D-05).
- Naming de funciones en `_core.py` — Preferencia: `build_<endpoint_name>_request` (consistente, mecánicamente derivable del nombre del método público).
- Ubicación exacta del snapshot test guard para las 18 matriz probes — Preferencia: `verification/test_matriz_sweep_snapshot.py`.
- `pyproject.toml` vs `.importlinter` file para import-linter config — Preferencia: `pyproject.toml` `[tool.importlinter]` por consistencia con ruff/mypy/pytest.
- Forward-decl de Phase 8 `idempotent` field en RequestSpec — Preferencia: declararlo ahora (zero-cost, forward-compat).
- Snapshot test mechanics para 18 matriz probes — pytest-httpx vs MockTransport, inline payloads vs JSON fixtures.
- Test cadence per plan — mismo idiom Phase 6 D-07.

### Deferred Ideas (OUT OF SCOPE)

- `_envelope_probe` promoted to `verification/probes.py` cross-package — v1.2+.
- `RequestSpec.idempotent` forward-decl si planner difiere — Phase 8 RELY-03 lo asume.
- Generated-code parity tooling (unasync/codegen) → v1.2+.
- import-linter `independence` / `layered` contracts → v1.2+ (Phase 7 sólo usa `forbidden`).
- Cross-leak sentinel test des-skipear matriz — Phase 10 plan.
- CR-05 cross-package promotion — v1.2+.
- `Client.with_options(max_retries=N)` per-call override — v1.2+ (Phase 8 mentions).
- `_request` con `with http.send(...) as resp:` context-manager — descartada (D-06 cubre el riesgo con menos churn).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REFAC-03 | Módulo `_core.py` por paquete con builders/parsers puros (`RequestSpec`, `raise_for_response`, `unwrap_envelope`, auth-flow helpers); `client.py` y `aio.py` quedan como shells de transporte (~30-50 LOC por endpoint) llamando a `_core`; CI rule que prohíbe `_core.py` importar `client.py`/`aio.py`. | Standard Stack (`import-linter` v2.11 verificado); Architecture Patterns (4 patrones canónicos: pure builder, pure parser, transport shell sync, transport shell async); Per-package endpoint inventory; Code Examples (matriz/iol/higyrus/ámbito-specific sketches). |
| CR-03 | matriz `_request` no consume response body antes de raise cuando `data.status=="ERROR"` — potential connection-pool resource leak con HTTP/2; consumir body explícito. | Pitfall 21 deep dive; código actual en `client.py:278-294` analizado; D-06 `_core.parse_envelope_response` absorbe `resp.read()` + `.json()` + check status==ERROR ANTES de cualquier raise. |
| CR-05 | 18 sweep probes con ~95% boilerplate duplicado en `main_matriz.py` (300-1394) — refactor a helper único; previene drift entre probes. | Pitfall 23 deep dive; 18 probes localizadas (líneas 300-1170 envelope, 1222-1402 risk); 2 risk probes (`probe_get_detailed_positions:1277`, `probe_get_account_report:1342`) preservadas con `envelope_key=None`; snapshot test guard pattern documentado. |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Pure request building (path + params + headers + body) | `_core.py` (per-package library tier) | — | Builders son funciones puras `state → RequestSpec`; no tocan I/O, no acceden al transport. |
| Pure response parsing (read body + JSON + shape check + raise typed) | `_core.py` (per-package library tier) | — | Parsers son funciones puras `httpx.Response → typed result`; consumen body inline (D-06 cierra CR-03). |
| Auth flow primitives (login request + login response parsing) | `_core.py` (per-package library tier) | — | `build_login_request(state) → RequestSpec` + `parse_login_response(status, body, headers) → tuple`. Transport shell ejecuta el HTTP call. |
| HTTP transport dispatch (`httpx.Client.request` / `await httpx.AsyncClient.request`) | `client.py` / `aio.py` (transport shell tier) | — | Único diferencial sync vs async post-refactor: la línea de transporte. ~30-50 LOC por endpoint group. |
| Token caching + freshness check (`_ensure_token`) | `client.py` / `aio.py` (transport shell tier) | `_core.py` (pure freshness check helper) | El check `token and time.time() < expires_at` es puro y vive en `_core.token_is_fresh(state)`; el `_ensure_token` que dispara `login()` es transport (orquesta I/O). |
| Module-level state singleton (`_default_client`, `configure()`, PEP 562 shim) | `client.py` / `aio.py` (compat layer tier) | `_state.py` (data tier) | Sin cambios respecto a Phase 6. `_core.py` NO toca este tier. |
| `_envelope_probe` driver helper | `main_matriz.py` (driver tier) | `matriz_client._core` (parse_envelope_response) | D-07: driver-only. Llama `_get_default()._request(...)` + `_core.unwrap` indirectamente vía el envelope key. |
| Snapshot test guard (18 probes pre/post refactor) | `verification/` (test harness tier) | `pytest-httpx` (mock tier) | D-08: vive en `verification/test_matriz_sweep_snapshot.py` (consistente con `verification/test_public_surface.py`). |
| Import boundary enforcement | `pyproject.toml` `[tool.importlinter]` + CI step `lint-imports` (CI tier) | — | Declarativo; no requiere código en runtime. 4 contracts `forbidden`. |
| Cross-leak sentinel test | `verification/test_sync_async_isolation.py` (test harness tier) | `pytest-httpx` (mock tier) | D-10: parametrizado sobre 4 paquetes; matriz `pytest.skip` (D-11). |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `import-linter` | `>=2.11,<3` | Bloquear `_core.py → client.py/aio.py` imports declarativamente vía pyproject.toml | [VERIFIED: PyPI registry + official docs] Industry standard para Python import boundary enforcement; mantenido activamente por seddonym; v2.11 publicada 2026-03-06; soporte oficial para `[tool.importlinter]` en pyproject.toml y contratos `forbidden` con `as_packages=True` (descendant-transitive). |
| `httpx` | `>=0.27` | HTTP sync + async (sin cambios — ya en Phase 6) | [VERIFIED: existing dep in root pyproject.toml] |
| `pytest-httpx` | `>=0.34` | Mock HTTP responses para cross-leak test + snapshot test 18 probes | [VERIFIED: existing dev dep] Mismo idiom que `verification/test_public_surface.py` y los tests `test_fixture_reaches_production.py` de Phase 6. |
| `pytest` | `>=8.3` | Test runner (sin cambios) | [VERIFIED: existing dev dep] |
| `mypy` (strict) | `>=1.13` | Type checking (sin cambios) | [VERIFIED: existing dev dep] |
| `ruff` | `>=0.7` | Linter + formatter (sin cambios) | [VERIFIED: existing dev dep] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `dataclasses` (stdlib) | — | `@dataclass(frozen=True, slots=True)` para `RequestSpec` | Per-package en cada `_core.py`. `frozen=True` porque RequestSpec es input puro (no muta); `slots=True` para memory efficiency. |
| `typing.NamedTuple` (stdlib, alternative) | — | Alternativa al frozen dataclass | NO recomendado: dataclass+slots tiene mejor diagnostics en mypy strict + es el patrón ya usado por SafeModel (higyrus/matriz). |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `import-linter` | grep CI rule en GitHub Actions (`grep -rn "from <pkg>\\.client\\|from <pkg>\\.aio" packages/*/src/*/\\_core.py`) | Zero deps nuevas, pero false-negatives con qualified imports (`import <pkg>.client as c`) + false-positives en comentarios. Locked OUT por D-09. |
| `import-linter` | Test pytest que parsea AST | Robust vs regex pero código extra; el AST test sería ~50 LOC vs ~15 líneas de TOML config. Locked OUT por D-09. |
| `@dataclass(frozen=True, slots=True)` para RequestSpec | `TypedDict` | TypedDict es `dict[str, Any]` runtime — sin tipo runtime, sin `__slots__`, sin igualdad estructural. mypy strict los acepta a ambos; dataclass gana en runtime safety + introspection. |
| `@dataclass` para RequestSpec | `NamedTuple` | NamedTuple es tuple — no soporta defaults bien en strict mode + no extensible (Phase 8 `idempotent` field). |
| Shared `RequestSpec` en `verification/_shared/` cross-package | Shared module en `verification/` (lib-style) | Viola constraint "no shared internals between packages". Locked OUT por D-01. |

**Installation:**

Agregar al root `pyproject.toml`:

```toml
[dependency-groups]
dev = [
    "ruff>=0.7",
    "mypy>=1.13",
    "pytest>=8.3",
    "pytest-cov>=6.0",
    "pytest-asyncio>=0.24",
    "pytest-httpx>=0.34",
    "pre-commit>=4.0",
    "import-linter>=2.11,<3",  # NUEVO: Phase 7 REFAC-03 enforcement
]
```

Sync con `uv sync --all-packages --all-extras --dev`.

**Version verification (ejecutar antes de planificar):**

```bash
curl -s https://pypi.org/pypi/import-linter/json | python3 -c \
  "import sys, json; d=json.load(sys.stdin); print('version:', d['info']['version']); print('requires_python:', d['info']['requires_python'])"
# Esperado: version: 2.11+ ; requires_python: >=3.10
```

Resultado en research: `version: 2.11`, `requires_python: >=3.10` — **compatible con el repo Python 3.12+ constraint.** [VERIFIED: PyPI JSON 2026-06-12]

## Package Legitimacy Audit

> Required: este phase agrega **1 nuevo package** (`import-linter`).

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| `import-linter` | PyPI | v2.11 publicada 2026-03-06 (~3 meses); proyecto activo desde 2017 (~9 años) | No verificable sin slopcheck — pero PyPI stats reportan miles de descargas semanales para v2.x | `github.com/seddonym/import-linter` (verificable en PyPI JSON `project_urls.Source-code`) [VERIFIED] | unavailable (slopcheck no instalado en research env) | Approved — verificado manualmente vía PyPI JSON + docs oficiales (readthedocs.io) + cross-confirmado en search ecosystem |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

**Manual verification (compensación por slopcheck unavailable):**
- Doc oficial: `https://import-linter.readthedocs.io/en/v2.7/contract_types.html` confirma `forbidden` contract type (source_modules, forbidden_modules, ignore_imports, as_packages, allow_indirect_imports). [CITED]
- Doc oficial: `https://import-linter.readthedocs.io/en/v2.7/usage.html` confirma `[tool.importlinter]` en pyproject.toml + `[[tool.importlinter.contracts]]` + CLI `lint-imports`. [CITED]
- PyPI source URL `github.com/seddonym/import-linter` resuelve a repo público con LICENSE Apache-2.0 + 9 años de historia.
- requires-python `>=3.10` compatible con repo `>=3.12`.
- No `postinstall` (es pure-Python via setuptools).

**Disposition:** Aprobado. Planner debe agregar `[checkpoint:human-verify]` task ANTES del `uv sync` en Plan 1 (consistent con package_legitimacy_protocol fallback cuando slopcheck no está disponible). Mensaje del checkpoint: "Verificar `import-linter` en PyPI: `pip index versions import-linter` (esperado ≥2.11) + repo source `github.com/seddonym/import-linter`".

## Architecture Patterns

### System Architecture Diagram

```
                  ┌─────────────────────────┐
                  │ caller (top-level API)  │
                  │ pkg.get_quote("GGAL")   │
                  └────────────┬────────────┘
                               │
                ┌──────────────┴──────────────┐
                │                             │
        ┌───────▼────────┐          ┌─────────▼────────┐
        │   client.py    │          │     aio.py       │
        │ (sync shell)   │          │  (async shell)   │
        │                │          │                  │
        │ Client class   │          │ AsyncClient cls  │
        │  ├ httpx.Client│          │  ├ httpx.Async   │
        │  ├ _state      │          │  ├ _state        │
        │  └ _request()  │          │  └ _request()    │
        │                │          │                  │
        │ delegators:    │          │                  │
        │  get_quote()   │          │  async get_qte() │
        │  configure()   │          │                  │
        │  PEP 562 shim  │          │  PEP 562 shim    │
        │                │          │                  │
        │ aliases:       │          │ aliases:         │
        │ _raise_for_resp│          │ _raise_for_resp  │
        │ = _core.r_f_r  │          │ = _core.r_f_r    │
        │ _unwrap        │          │                  │
        │ = _core.unwrap │          │                  │
        └────┬───────────┘          └────────┬─────────┘
             │ build_X_request(state, ...)   │
             │ parse_X_response(resp)        │
             ▼                               ▼
        ┌────────────────────────────────────────┐
        │             _core.py (NEW)             │
        │      PURE, TRANSPORT-AGNOSTIC          │
        │                                         │
        │  @dataclass(frozen=True, slots=True)   │
        │  class RequestSpec: ...                │
        │                                         │
        │  def build_get_quote_request(           │
        │      state, simbolo, mercado="bcba",   │
        │  ) -> RequestSpec: ...                  │
        │                                         │
        │  def parse_get_quote_response(          │
        │      resp,                              │
        │  ) -> dict[str, Any]:                   │
        │      resp.read()       # CR-03 fix     │
        │      raise_for_response(resp)          │
        │      return resp.json()                │
        │                                         │
        │  def build_login_request(state) ...    │
        │  def parse_login_response(...) ...     │
        │                                         │
        │  def raise_for_response(resp) ...      │
        │  def unwrap(data, key, ep) ...         │
        │                                         │
        │  ← NO importa client/aio/httpx.Client  │
        │  ← NO holds module state               │
        │  ← Enforced by import-linter           │
        └────────────────────┬───────────────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │     _state.py       │
                  │ (Phase 6, unchanged)│
                  │                     │
                  │ @dataclass(slots=T) │
                  │ class _ClientState  │
                  │   base_url          │
                  │   token             │
                  │   token_expires_at  │
                  │   http_client       │
                  │   ...               │
                  └─────────────────────┘

CI gates (Plan 1):
    pyproject.toml [tool.importlinter] →  lint-imports
        contracts: _core ⊬ client, aio  (4× per package)
    verification/test_sync_async_isolation.py
        SYNC-sentinel-<pkg> != ASYNC-sentinel-<pkg>
            (matriz: pytest.skip until Phase 10)

CR closures (Plan 5 matriz):
    main_matriz.py
        _envelope_probe(name, path, envelope_key=None, model_from_api=None)
            ✓ 16 probes pass envelope_key="segments"|"instruments"|...
            ✓  2 risk probes pass envelope_key=None
    verification/test_matriz_sweep_snapshot.py
        snapshot guard: 18 probes pre-refactor (canned payloads)
                       == 18 probes post-refactor
```

### Recommended Project Structure

```
packages/<pkg>/src/<pkg>/
├── __init__.py        # PUBLIC — sin cambios Phase 7 (D-16)
├── _state.py          # Phase 6 — Phase 7 lo CONSUME, no modifica
├── _core.py           # NUEVO Phase 7 — builders + parsers + auth + helpers (PURE)
├── client.py          # Sync transport shell — colapsado, ~30-50 LOC/group
├── aio.py             # Async transport shell — colapsado (matriz: stub Phase 6→10)
├── exceptions.py      # sin cambios
├── models.py          # sin cambios (higyrus, matriz)
├── types.py           # sin cambios (matriz)
├── _params.py         # sin cambios (higyrus) — drop_none, format_date, format_bool
└── _parsing.py        # sin cambios (ámbito) — parse_ar_decimal

packages/matriz-client/src/matriz_client/
└── ws_client.py       # sin cambios Phase 7 (Phase 10 TokenStore lo tocará)

verification/
├── test_public_surface.py       # Phase 6 — Phase 7 verifica SIN diff (D-16)
├── snapshots/<pkg>-surface.txt  # Phase 6 — Phase 7 NO regenera
├── test_sync_async_isolation.py # NUEVO Plan 1 — cross-leak sentinel (D-10)
└── test_matriz_sweep_snapshot.py # NUEVO Plan 5 — 18 probes guard (D-08)
```

### Pattern 1: `RequestSpec` per-package frozen dataclass

**What:** Dataclass inmutable que captura todo lo necesario para emitir una HTTP request, sin tocar `httpx.Client` ni `httpx.AsyncClient`.

**When to use:** Como retorno de cada `build_<endpoint>_request(state, ...)` en `_core.py`. El shell sync hace `self._http.request(spec.method, spec.path, ...)`; el shell async hace `await self._http.request(...)` — la línea es idéntica salvo el `await`.

**Example (matriz — el más rico):**

```python
# packages/matriz-client/src/matriz_client/_core.py
# Source: CONTEXT.md D-01 + research Pattern 1 + frozen dataclass idiom (Phase 6 _state.py)

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class RequestSpec:
    """Pure description of an HTTP request — no transport coupling.

    Per-package shape (D-01 / no shared internals): matriz tiene
    ``auth_basic`` opcional para la Risk API (HTTP Basic Auth fallback).
    Otros paquetes no lo necesitan.

    Phase 8 forward-decl (D-13 planner-discretion): si declaramos
    ``idempotent: bool = False`` ahora, Phase 8 RELY-03 sólo cambia
    defaults per GET endpoint.
    """

    method: str
    path: str
    params: dict[str, Any] | None = None
    headers: dict[str, str] | None = None
    json_body: dict[str, Any] | None = None
    auth_basic: tuple[str, str] | None = None
    # idempotent: bool = False  # Phase 8 RELY-03 forward-decl (planner discretion)
```

**Per-package divergence:**

| Package | RequestSpec extra fields | Reason |
|---------|--------------------------|--------|
| ámbito | (minimal: `method`, `path`, `params`, `headers`) | Sin auth, sin body, parser HTML. |
| iol | (base + `data`: form-encoded body para login/refresh) | OAuth `POST /token` usa `application/x-www-form-urlencoded`, NO JSON. |
| higyrus | (base + `json_body` + `url_pre_encoded: str \| None`) | URL-encoding quirk: `urlencode(..., doseq=True, quote_via=quote, safe="/")` preserva `/`. La opción A es que el builder retorne URL ya encodeada (`spec.path` = `"<path>?<query>"`); opción B es un campo `params_doseq: bool = False`. **Preferencia:** opción A — encapsula la quirk en `_core.build_<endpoint>_request`. |
| matriz | (base + `auth_basic: tuple[str, str] \| None`) | Risk API (`§9`) usa HTTP Basic Auth; el resto del API usa `X-Auth-Token` header. |

### Pattern 2: Pure parser with body-consume-then-raise (CR-03 fix)

**What:** Función `parse_<endpoint>_response(resp: httpx.Response) -> T` que (1) consume body explícito vía `resp.read()`, (2) decodifica JSON, (3) valida shape, (4) raise typed si aplica, (5) retorna typed result.

**When to use:** Para CADA endpoint de los 4 paquetes. matriz adicionalmente para envelope-wrapped responses (`_core.parse_envelope_response`).

**Example (matriz — cierra CR-03):**

```python
# packages/matriz-client/src/matriz_client/_core.py
# Source: CONTEXT.md D-06 + research Pitfall 21 close-out

from __future__ import annotations

from typing import Any

import httpx

from matriz_client.exceptions import PrimaryAPIError


def raise_for_response(resp: httpx.Response) -> None:
    """Stateless HTTP status → exception mapper (moved from client.py).

    D-04 alias preserved: ``client._raise_for_response = _core.raise_for_response``
    so legacy imports (e.g. ``higyrus_client.aio`` already imports this name from
    ``client``) keep working.
    """
    resp.raise_for_status()


def unwrap(data: dict[str, Any], key: str, endpoint: str) -> Any:
    """Envelope-key extractor (moved from client.py). D-04 alias preserved."""
    if key not in data:
        raise PrimaryAPIError(
            status="ERROR",
            description=f"missing envelope key '{key}' in response from {endpoint}",
            message=None,
        )
    return data[key]


def parse_envelope_response(resp: httpx.Response, endpoint: str) -> dict[str, Any]:
    """Body-consume-then-raise parser — cierra CR-03 (Pitfall 21).

    Orden CRÍTICO (D-06):
      1. ``resp.read()``  ← consume body EXPLICITLY (HTTP/2-safe)
      2. ``resp.json()``  ← decode (raises ValueError si malformed JSON)
      3. shape check + status==ERROR check
      4. raise PrimaryAPIError if applicable

    Si el body NO se consume antes de raise, futuro ``httpx.Client(http2=True)``
    introduce stream leak en el connection pool (cada raise sin read deja
    el stream abierto hasta GC).
    """
    resp.read()           # ← CR-03 FIX: explicit body consume
    raise_for_response(resp)
    raw = resp.json()
    if not isinstance(raw, dict):
        raise PrimaryAPIError(
            status="ERROR",
            description=f"expected JSON object body at {endpoint}, got {type(raw).__name__}",
            message=None,
        )
    if raw.get("status") == "ERROR":
        raise PrimaryAPIError(
            status="ERROR",
            description=raw.get("description"),
            message=raw.get("message"),
        )
    return raw  # type: ignore[return-value]
```

### Pattern 3: Transport shell (sync) — endpoint method post-refactor

**What:** Método de endpoint en `client.py` que sólo hace: (a) build spec via `_core`, (b) ejecutar HTTP, (c) parse via `_core`. ≤30-50 LOC por endpoint group (D-05).

**When to use:** Cada endpoint actual de `Client` post-refactor. La línea de transporte (`http.request(...)`) es el ÚNICO diferencial entre sync y async.

**Example (matriz — `get_segments` post-refactor):**

```python
# packages/matriz-client/src/matriz_client/client.py
# Source: CONTEXT.md D-03 + research Pattern 3

from matriz_client import _core
from matriz_client.models import Segment

class Client:
    # ... __init__, _ensure_token, _ensure_http_client unchanged ...

    def _request(self, spec: _core.RequestSpec) -> httpx.Response:
        """Transport shell — única responsabilidad: dispatch HTTP."""
        http = self._ensure_http_client()
        if spec.auth_basic is not None:
            return http.request(
                spec.method,
                f"{self._state.base_url}{spec.path}",
                params=spec.params,
                auth=httpx.BasicAuth(*spec.auth_basic),
            )
        self._ensure_token()
        assert self._state.token is not None
        headers = {"X-Auth-Token": self._state.token, **(spec.headers or {})}
        return http.request(
            spec.method,
            f"{self._state.base_url}{spec.path}",
            params=spec.params,
            headers=headers,
        )

    # -- Segments (§4) ----------------------------------------------

    def get_segments(self) -> list[Segment]:
        spec = _core.build_get_segments_request(self._state)
        resp = self._request(spec)
        data = _core.parse_envelope_response(resp, spec.path)
        return [Segment.from_api(s) for s in _core.unwrap(data, "segments", spec.path)]
```

### Pattern 4: Transport shell (async) — endpoint method post-refactor

**What:** Mirror exact de Pattern 3 con `await`. Body de la función IDÉNTICO a sync excepto las 2-3 líneas con `await`.

**Example (iol — `get_quote` post-refactor):**

```python
# packages/iol-client/src/iol_client/aio.py
# Source: CONTEXT.md D-02/D-03 + research Pattern 4

from iol_client import _core

class AsyncClient:
    # ... __init__, _ensure_token (async), _ensure_http_client (async) unchanged ...

    async def _request(self, spec: _core.RequestSpec) -> httpx.Response:
        await self._ensure_token()
        lock = self._ensure_token_lock()
        async with lock:
            token = self._state.token
        assert token is not None
        client = await self._ensure_http_client()
        headers = {"Authorization": f"Bearer {token}", **(spec.headers or {})}
        return await client.request(
            spec.method,
            f"{self._state.base_url}{spec.path}",
            params=spec.params,
            json=spec.json_body,
            headers=headers,
        )

    async def get_quote(
        self,
        simbolo: str,
        *,
        mercado: str = "bcba",
        plazo: str = "t2",
    ) -> dict[str, Any]:
        spec = _core.build_get_quote_request(self._state, simbolo, mercado=mercado, plazo=plazo)
        resp = await self._request(spec)
        return _core.parse_get_quote_response(resp)
```

### Pattern 5: Auth-flow factoring (builder + parser)

**What:** `build_login_request(state) → RequestSpec` + `parse_login_response(status, body, headers) → (token, expires_at, refresh_token?)`. Sync/async transport shells ejecutan el HTTP call y feed al parser.

**Example (iol — login + refresh):**

```python
# packages/iol-client/src/iol_client/_core.py

from __future__ import annotations

import time
from typing import Any

from iol_client._state import _TOKEN_TTL_BUFFER_SECONDS, _ClientState
from iol_client.exceptions import IOLAuthError


def build_login_request(state: _ClientState) -> RequestSpec:
    """Pure: emite RequestSpec para OAuth password grant."""
    if not state.username or not state.password:
        raise IOLAuthError(0, "IOL_USER y IOL_PASSWORD son requeridos")
    return RequestSpec(
        method="POST",
        path="/token",
        data={
            "username": state.username,
            "password": state.password,
            "grant_type": "password",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )


def parse_login_response(resp: httpx.Response) -> tuple[str, float, str | None]:
    """Pure: extrae (token, expires_at_epoch, refresh_token_opt) del response.

    Returns:
        Tuple of (access_token, token_expires_at_epoch, new_refresh_token_or_None).
        Caller (transport shell) writes to ``state.token`` / ``state.token_expires_at`` /
        ``state.refresh_token`` (the latter ONLY if non-None — CR-01 condicional).
    """
    resp.read()
    raise_for_response(resp)
    data: dict[str, Any] = resp.json()
    access_token = data.get("access_token")
    expires_in = data.get("expires_in", 900)
    if not isinstance(access_token, str) or not access_token:
        raise IOLAuthError(resp.status_code, "No access_token in response")
    new_refresh = data.get("refresh_token")
    refresh_out = new_refresh if isinstance(new_refresh, str) and new_refresh else None
    expires_at = time.time() + float(expires_in) - _TOKEN_TTL_BUFFER_SECONDS
    return access_token, expires_at, refresh_out


def build_refresh_request(state: _ClientState) -> RequestSpec:
    refresh_token = state.refresh_token
    if not refresh_token:
        raise IOLAuthError(0, "No refresh_token cached")
    return RequestSpec(
        method="POST",
        path="/token",
        data={"refresh_token": refresh_token, "grant_type": "refresh_token"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )


def parse_refresh_response(resp: httpx.Response) -> tuple[str, float, str | None]:
    """Same shape as parse_login_response — mismo formato del server."""
    # Reuses parse_login_response logic; alias OK
    return parse_login_response(resp)
```

```python
# packages/iol-client/src/iol_client/client.py — transport shell consume

class Client:
    def login(self) -> str:
        spec = _core.build_login_request(self._state)
        http = self._ensure_http_client()
        resp = http.post(f"{self._state.base_url}{spec.path}", data=spec.data, headers=spec.headers)
        token, expires_at, refresh = _core.parse_login_response(resp)
        self._state.token = token
        self._state.token_expires_at = expires_at
        if refresh is not None:
            self._state.refresh_token = refresh
        return token
```

### Pattern 6: D-04 alias re-export (B8 preservation)

**What:** Después de mover `_raise_for_response` y `_unwrap` a `_core.py`, `client.py` define aliases module-level que apuntan AL MISMO objeto. Tests `aio._raise_for_response is client._raise_for_response` siguen verdes porque `is` compara identidad del objeto, y AMBOS aliases referencian `_core.raise_for_response`.

**Why this matters:** Hay tests vivientes (`packages/{higyrus,ambito}/tests/test_client_class.py:359-369` y `packages/ambito.../tests/test_client_class.py:170-178`) que hacen `assert a_impl is c_impl`. Si Phase 7 rompe esto, son red flag de re-coupling. La D-04 alias garantiza identidad.

**Example:**

```python
# packages/iol-client/src/iol_client/client.py — Phase 7 post-refactor (snippet)

from iol_client import _core

# D-04 aliases — preserve B8 imports from aio.py and from tests.
# Both aio._raise_for_response and client._raise_for_response are the
# SAME OBJECT (_core.raise_for_response), so `is` checks pass.
_raise_for_response = _core.raise_for_response
```

```python
# packages/iol-client/src/iol_client/aio.py — Phase 7 post-refactor (snippet)

from iol_client import _core
# Phase 6: aio.py importaba `_raise_for_response` de client.py.
# Phase 7 D-04: ahora lo importa de _core.py.
# Test `aio._raise_for_response is client._raise_for_response` sigue verde
# porque ambos aliases apuntan al mismo objeto.
_raise_for_response = _core.raise_for_response
```

### Pattern 7: `_envelope_probe` driver helper (CR-05 close)

**What:** Helper en `main_matriz.py` que dedupea las 18 sweep probes. `envelope_key=None` preserva las 2 risk probes.

**Example:**

```python
# main_matriz.py — Plan 5 (Phase 7)
# Source: CONTEXT.md D-07 + research Pitfall 23 close-out

from collections.abc import Callable
from typing import Any

import matriz_client as primary
from matriz_client.exceptions import PrimaryAPIError


def _envelope_probe(
    name: str,
    path: str,
    *,
    envelope_key: str | None = None,
    model_from_api: Callable[[Any], Any] | None = None,
    request_params: dict[str, Any] | None = None,
    auth_basic_fn: Callable[[], tuple[str, str]] | None = None,
) -> tuple[ProbeResult, Any | None]:
    """Sweep probe helper: GET path, optionally unwrap envelope_key,
    optionally map model_from_api over the result, emit ProbeResult.

    Args:
        name: ProbeResult label (used in cycle_report).
        path: REST path (e.g. ``/rest/segment/all``).
        envelope_key: Envelope key to unwrap; ``None`` for risk probes
            (D-07) where payload root is the result dict.
        model_from_api: Optional model.from_api callable to map the
            unwrapped list / wrap the unwrapped dict.
        request_params: kwargs forwarded to ``_matriz_request("GET", path, params=...)``.
        auth_basic_fn: Returns (user, pass) for Risk API; ``None`` uses X-Auth-Token.

    Returns:
        (ProbeResult, raw_payload_or_None) — same shape as the 18 probes today.
    """
    if _auth_failed:
        return (ProbeResult(name, "SKIPPED", f"auth failed: {_auth_failure_reason}"), None)
    base_url = primary.client._base_url
    auth = auth_basic_fn() if auth_basic_fn is not None else None
    try:
        raw = _matriz_request("GET", path, params=request_params, auth_basic=auth)
    except PrimaryAPIError as exc:
        fid = _next_fid()
        append_finding(_PKG, fid=fid, class_="ERROR-MAP", surface="sync",
                       status="OPEN", title=f"{name} levantó PrimaryAPIError",
                       expected=f"200 OK con envelope {{{envelope_key}: ...}}"
                                if envelope_key else "200 OK con dict raíz",
                       actual=f"PrimaryAPIError: {exc}",
                       diff="error upstream o status=='ERROR'", base_url=base_url)
        return (ProbeResult(name, "FINDING", f"{fid} (OPEN)"), None)
    if envelope_key is None:
        # Risk probe: payload root IS the result.
        if not isinstance(raw, dict):
            fid = _next_fid()
            append_finding(_PKG, fid=fid, class_="SHAPE", surface="sync", status="OPEN",
                           title=f"{name} payload shape incorrecto",
                           expected="payload raíz es dict (sin envelope key)",
                           actual=f"raw={type(raw).__name__}",
                           diff="payload raíz no es dict", base_url=base_url)
            return (ProbeResult(name, "FINDING", f"{fid} (OPEN)"), None)
        return (ProbeResult(name, "PASS", "received"), raw)
    # Envelope probe: unwrap key, validate list.
    payload = raw.get(envelope_key)
    if not isinstance(payload, list):
        fid = _next_fid()
        append_finding(_PKG, fid=fid, class_="SHAPE", surface="sync", status="OPEN",
                       title=f"{name} envelope shape incorrecto",
                       expected=f"raw['{envelope_key}'] es list",
                       actual=f"raw['{envelope_key}']={type(payload).__name__}",
                       diff=f"envelope key '{envelope_key}' ausente o no-list",
                       base_url=base_url)
        return (ProbeResult(name, "FINDING", f"{fid} (OPEN)"), None)
    return (ProbeResult(name, "PASS", f"{len(payload)} items"), payload)
```

**Migration map (18 probes → `_envelope_probe` calls):**

| Probe | envelope_key | Notes |
|-------|--------------|-------|
| `probe_get_segments` | `"segments"` | sets `_resolved_segment` from `payload[0]["marketSegmentId"]` post-call |
| `probe_get_all_instruments` | `"instruments"` | sets `_resolved_symbol` post-call |
| `probe_get_instruments_details` | `"instruments"` | |
| `probe_get_instrument_detail` | `"instrument"` | requires `_resolved_symbol`; SKIP if None |
| `probe_get_instruments_by_cfi_ESXXXX` | `"instruments"` | |
| `probe_get_instruments_by_cfi_sanity` | (special — loop over 8 CFI codes; **does NOT fit the helper exactly**) | Keep custom OR factor out an inner `_envelope_probe_inner` |
| `probe_get_instruments_by_segment` | `"instruments"` | requires `_resolved_segment`; SKIP if None |
| `probe_get_market_data` | `"marketData"` | has market-hours guard logic (NOT fit exactly; partial reuse) |
| `probe_get_trades` | `"trades"` | |
| `probe_get_active_orders` | `"orders"` | requires `_PRIMARY_ACCOUNT` |
| `probe_get_filled_orders` | `"orders"` | requires `_PRIMARY_ACCOUNT` |
| `probe_get_all_orders` | `"orders"` | requires `_PRIMARY_ACCOUNT` |
| `probe_get_order_status` | `"order"` | requires order context |
| `probe_get_order_history` | `"orders"` | |
| `probe_get_order_by_exec_id` | `"order"` | |
| `probe_get_positions` | `"positions"` | Risk API, `auth_basic_fn=_risk_auth` |
| **`probe_get_detailed_positions`** | **`None`** ← RISK PROBE | preserved per D-07 |
| **`probe_get_account_report`** | **`None`** ← RISK PROBE | preserved per D-07 |

**Honesty flag:** 3 probes (`probe_get_instruments_by_cfi_sanity`, `probe_get_market_data`, side-effect probes que setean `_resolved_*`) tienen lógica adicional que NO encaja exactamente en el helper plano. Planner debe decidir: (a) mantenerlas custom + 15 migradas, (b) extender el helper con kwargs `post_unwrap_hook: Callable[[Any], None] | None`, o (c) factor del side-effect setter al call site. **Recomendación:** opción (a) — mantener custom las 3 con lógica especial + migrar 15 limpias; el plan documenta cuáles son custom. Esto sigue cumpliendo CR-05 ("~95% boilerplate eliminado").

### Anti-Patterns to Avoid

- **`from <pkg>.client import _raise_for_response` en `<pkg>._core`** — Re-coupling sync/async. Pitfall 3 / D-09 import-linter lo bloquea automáticamente.
- **`_core.py` importa `httpx.Client` o `httpx.AsyncClient`** — `_core.py` solo importa `httpx` (para `httpx.Response` type hint) y `httpx.BasicAuth` (matriz auth). NO crea instancias de Client/AsyncClient.
- **`_core.py` mantiene state module-level** — Cualquier `_token`, `_base_url`, `_client` en `_core.py` rompe el contrato pure-helper. Si necesita state, lo recibe como arg `state: _ClientState`.
- **Parser que NO consume body antes de raise** — CR-03 / D-06. Cualquier `_core.parse_*` que haga `if resp.is_error: raise ...` sin `resp.read()` previo introduce el bug.
- **`_envelope_probe` con `envelope_key=""` para risk probes** — `""` es truthy en `data.get("")`. Las risk probes USAN `None` (D-07). Test deriva del snapshot guard.
- **Cambiar el contrato de `client._request` sin actualizar `main_iol.py:1287,1289,1322,1421-1422`** — el driver lee `iol_client.client._token` y SETEA `iol_client.client._token_expires_at`. El PEP 562 shim de Phase 6 ya forward lecturas; **escrituras NO van por shim** (read-only D-01 Phase 6). Si Phase 7 cambia el flujo, planner debe verificar que `main_iol.py` siga funcionando vía `_get_default()._state.X = Y` o `configure(...)`.
- **Snapshot test rendido a "weakening"** — Pitfall 18. El snapshot guard de las 18 probes (Plan 5) DEBE registrar el shape pre-refactor y compararlo post-refactor; cualquier cambio de fields del `ProbeResult` rompe el snapshot — el commit message debe documentar la razón.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Bloquear imports cross-module a nivel CI | regex grep en GH Actions o AST custom test | `import-linter>=2.11` + `[tool.importlinter]` en pyproject.toml | Standard tool con 9 años de uso productivo; soporta wildcards, `as_packages` (descendant-transitive), `ignore_imports` granular, `allow_indirect_imports`. Grep fragile contra qualified imports; AST custom = ~50 LOC vs ~15 líneas TOML. [VERIFIED: import-linter docs] |
| Comparar response wire headers en sync vs async | introspección de `httpx.Client.event_hooks` | `pytest-httpx` `httpx_mock.get_requests()` + assert `req.headers[K] == V` | `pytest-httpx` ya es dev dep; el patrón aparece en `packages/iol-client/tests/test_client.py:14-22` y `test_fixture_reaches_production.py` de Phase 6. |
| Snapshot test de 18 probes con payloads canned | JSON fixtures externos + custom loader | `pytest-httpx` `httpx_mock.add_response(url=..., json=...)` inline en el test | Phase 6 `06-02-PLAN.md` ya estableció el patrón. Inline payloads (small) son más legibles que JSON fixtures externos en el test file. |
| Construir y serializar `RequestSpec` para retry transport (Phase 8 forward-decl) | `dict[str, Any]` + manual conversion | `@dataclass(frozen=True, slots=True)` | Dataclass es type-safe, immutable, soporta `replace()` para variaciones (Phase 8 puede `replace(spec, idempotent=True)`), y se introspecciona con `dataclasses.asdict(spec)` para logging estructurado (Phase 8). |
| Parser que retorna `dict | list | None` (higyrus actual) | `dict[str, Any] | list[Any] | None` runtime check | typed dataclasses + `Optional[T]` por endpoint, mediante `parse_<endpoint>_response(resp) → list[Movimiento]` que ENCAPSULA el shape check. Higyrus actual hace shape check en el endpoint method; Phase 7 lo mueve al parser. |

**Key insight:** Toda la complejidad de Phase 7 está en la organización mecánica (4 paquetes × N endpoints), NO en innovación técnica. Cada decisión de diseño tiene un patrón pre-existente en el repo o en el ecosistema; el research recomienda APEGARSE estrictamente a los patrones de Phase 6 y al stack del project.

## Runtime State Inventory

> N/A para Phase 7 — no es una rename/refactor de strings persistidos. El refactor mueve código entre archivos del MISMO paquete; no toca DBs, servicios externos, OS state, secrets, ni build artifacts.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — Phase 7 no escribe a stores externos. | None |
| Live service config | None — Phase 7 no cambia config de servicios upstream. | None |
| OS-registered state | None — Phase 7 no toca registries OS. | None |
| Secrets/env vars | None — env vars (`IOL_USER`, `PRIMARY_USER`, `HIGYRUS_USER`, etc.) leídos por `_state.py` factories — sin cambios. | None |
| Build artifacts | None — Phase 7 no renombra paquetes ni cambia `pyproject.toml` de paquetes individuales. SÍ agrega `import-linter` a root `[dependency-groups] dev`, que requiere `uv sync` post-merge. | Re-run `uv sync --all-packages --all-extras --dev --frozen` después de mergear Plan 1. |

**Nothing found in category:** Explicit — verified por inspección de los 4 archivos `client.py`/`aio.py`, `_state.py`, drivers `main_*.py`, y `verification/` modules. Phase 7 es pure code refactor dentro del repo.

## Common Pitfalls

### Pitfall 1: `_core.py` accidentalmente re-coupla sync/async via hidden import

**What goes wrong:** Durante extracción mecánica, un dev agrega `from .client import _ensure_token` o `from .aio import _client_lock` a `_core.py` "just for this one helper". `_core.py` deja de ser pure y enmascara bugs cross-surface (refresh async pasa por sync state).
**Why it happens:** Extraction es mecánica; reviewers no notan una línea de import en un módulo "puro".
**How to avoid:** import-linter contract `forbidden` con `source_modules = ["<pkg>._core"]` y `forbidden_modules = ["<pkg>.client", "<pkg>.aio"]` corre en CI antes del merge. Plan 1 lo instala. PLUS: cross-leak sentinel test (Plan 1 D-10) lo detecta a runtime si el contract se bypassea con `importlib.import_module(...)`.
**Warning signs:** El test `verification/test_sync_async_isolation.py::test_sync_async_token_isolation[<pkg>]` falla — el async wire request lleva el SYNC sentinel, o vice versa.

### Pitfall 2: D-04 alias falla porque algún plan reasigna `_raise_for_response`

**What goes wrong:** Plan 3 (iol) re-define `_raise_for_response` localmente en `client.py` "para evitar un alias confuso". Tests B8 (`a_impl is c_impl`) rompen porque `aio.py` aún apunta al `_core.raise_for_response` original mientras `client._raise_for_response` ahora es una función nueva.
**Why it happens:** El alias `X = _core.Y` parece redundant — IDE puede sugerir "remove redundant assignment".
**How to avoid:** Comentario explícito sobre el alias en cada `client.py`: `# D-04: alias preserves B8 ("aio.X is client.X" tests stay green)`. El plan-checker debe verificar.
**Warning signs:** Tests `test_aio_imports_raise_for_response_from_client` (3 instances: ambito, higyrus, iol — matriz no tiene ese test porque no tiene aio.py REST) fallan con `assert a_impl is c_impl`.

### Pitfall 3: Parser consume body via `resp.json()` pero NO via `resp.read()` — falsa solución de CR-03

**What goes wrong:** Dev "fixe" CR-03 cambiando `resp.json()` por `raw = resp.json(); raise_for_response(resp)`. Esto consume body (json() llama read() internally), pero el orden es `json() → raise` — y `resp.json()` puede ELLA MISMA raise `ValueError` si malformed. Si `raise_for_response(resp)` falla DESPUÉS de un `json()` exitoso, todo OK; si raise dentro de `json()`, el body posiblemente no se consumió completo en streaming responses.
**Why it happens:** `httpx.Response.json()` y `resp.read()` parecen equivalentes para closure.
**How to avoid:** **D-06 explícito**: el patrón canónico es `resp.read()` PRIMERO (consume completo el body al buffer), luego `raise_for_response(resp)`, luego `resp.json()`. NO se invierte el orden. Test guard verifica:

```python
def test_parse_envelope_consumes_body_before_raise(httpx_mock: HTTPXMock) -> None:
    # response with status=ERROR in body
    httpx_mock.add_response(json={"status": "ERROR", "description": "boom"})
    resp = httpx.Client().get("https://test/x")
    with pytest.raises(PrimaryAPIError):
        _core.parse_envelope_response(resp, "/x")
    # body must be fully consumed (resp.is_closed or resp.read() returns empty)
    assert resp.content is not None  # body buffered
```
**Warning signs:** Si se habilitan HTTP/2 (`httpx.Client(http2=True)`) en el futuro y los connection pool stats muestran streams stuck en `HALF_CLOSED_LOCAL`, el patrón se rompió.

### Pitfall 4: 277 tests baseline mencionado en CONTEXT.md es STALE — el real es 393

**What goes wrong:** El plan documenta "277 tests baseline verde" porque copia el número del milestone v1.1 spec. Phase 6 agregó tests (snapshot, fixture-reaches-production, B8 enforcement, gaps) — el baseline real al cierre de Phase 6 es **393 tests** (verificado via `uv run pytest --collect-only -q`). Si el plan-checker compara contra 277, no detecta regresiones.
**Why it happens:** Documentos heredados del milestone planning.
**How to avoid:** Plan-checker debe leer el conteo en HEAD via `uv run pytest --collect-only -q | tail -1` y usar ESE número como baseline. Plan 1 SUMMARY.md documenta el baseline observado.
**Warning signs:** Plan declara "277 → 277 verde" pero CI corre 393 — discrepancia ininformativa.

### Pitfall 5: `_envelope_probe` no preserva el side-effect setter de `_resolved_segment` / `_resolved_symbol`

**What goes wrong:** El refactor migra `probe_get_segments` a `_envelope_probe(envelope_key="segments")` pero no preserva el setter `global _resolved_segment; _resolved_segment = segments[0]["marketSegmentId"]`. Las probes 8 (`probe_get_instruments_by_segment`) y 5 (`probe_get_instrument_detail`) ya no pueden ejecutarse porque `_resolved_segment is None` siempre.
**Why it happens:** El helper plano hide el detalle de "esta probe specifica setea state global".
**How to avoid:** El planner identifica las **3 probes con side-effect** (`probe_get_segments`, `probe_get_all_instruments`, `probe_get_market_data`-guard) y decide: (a) NO migrarlas al helper (mantener custom), (b) o agregar `post_unwrap_hook: Callable[[Any], None] | None` al helper. Preferencia: opción (a) — claridad sobre dedup mechanical.
**Warning signs:** Snapshot test (Plan 5 D-08) muestra que las probes 5, 8, dependientes pasan a `SKIPPED ("no _resolved_segment")` post-refactor.

### Pitfall 6: import-linter falla con "module not found" porque no encuentra `<pkg>._core`

**What goes wrong:** Plan 1 mete contracts en pyproject.toml ANTES de que ninguno de los `_core.py` exista (los contracts pasan vacíos según CONTEXT.md "Plan 1 NO bloquea Plan 2"). Pero import-linter lee `root_packages` y al no encontrar `<pkg>._core` puede fallar con "Could not find package" o pasar vacío silenciosamente (ambos casos en CI verde — el verde silencioso es el peligro).
**Why it happens:** Order of operations: contracts declared first, modules created later.
**How to avoid:** Plan 1 declara los 4 contracts con `source_modules = ["<pkg>._core"]`. Si `<pkg>._core` no existe, import-linter v2.11 retorna "Could not find package: <pkg>._core" como WARN (CI verde) o ERROR (CI rojo) — el behavior cambia por versión. Plan-checker debe verificar empíricamente al introducir el primer contract. **Mitigación:** crear `<pkg>/_core.py` placeholder (sólo `from __future__ import annotations` + docstring) en Plan 1 para que los contracts NO sean vacíos; cada plan subsiguiente lo extiende.
**Warning signs:** `uv run lint-imports` retorna 0 sin reportar contract status — verificar el output text para "Could not find package" en stderr.

### Pitfall 7: matriz `_request` actual mezcla "transport" y "parsing" — D-03 cambia su contrato

**What goes wrong:** matriz `client._request(method, path, params=..., auth_basic=...) → dict[str, Any]` actualmente HACE el `resp.json()` y el `_raise_for_response` y el `data.status==ERROR` check todo inline. Migrar a D-03 (retorna `httpx.Response`) ROMPE: (a) main_matriz.py `_matriz_request("GET", path, params=...)` que retorna dict, (b) los 18 probes que hacen `raw.get("segments")` directly.
**Why it happens:** Phase 7 cambia el contrato del shell sin tocar el driver — pero el driver llama AL contrato del shell, NO al `_core`.
**How to avoid:** Plan 5 incluye un wrapper de back-compat: `client._matriz_legacy_request(method, path, **kw) → dict[str, Any]` que internally hace `resp = self._request(spec); return _core.parse_envelope_response(resp, path)`. main_matriz.py llama este wrapper. Alternativa: migrar main_matriz.py al patrón `spec = _core.build_X_request(...); resp = client._request(spec); data = _core.parse_envelope_response(resp, spec.path)`. **Recomendación:** wrapper de back-compat — menor churn en el driver, consistente con D-04 alias philosophy.
**Warning signs:** Plan 5 corre los 393 tests y main_matriz.py probes hacen `raw.get("segments")` sobre un `httpx.Response` → AttributeError.

## Code Examples

Patrones verificados de fuentes oficiales y del codebase existente:

### Example 1: `import-linter` config en pyproject.toml

```toml
# Source: https://import-linter.readthedocs.io/en/v2.7/usage.html [CITED]
# pyproject.toml raíz

[tool.importlinter]
root_packages = [
    "ambito_financiero_client",
    "iol_client",
    "higyrus_client",
    "matriz_client",
]

[[tool.importlinter.contracts]]
name = "ambito_financiero_client._core does not depend on transport modules"
type = "forbidden"
source_modules = ["ambito_financiero_client._core"]
forbidden_modules = [
    "ambito_financiero_client.client",
    "ambito_financiero_client.aio",
]

[[tool.importlinter.contracts]]
name = "iol_client._core does not depend on transport modules"
type = "forbidden"
source_modules = ["iol_client._core"]
forbidden_modules = ["iol_client.client", "iol_client.aio"]

[[tool.importlinter.contracts]]
name = "higyrus_client._core does not depend on transport modules"
type = "forbidden"
source_modules = ["higyrus_client._core"]
forbidden_modules = ["higyrus_client.client", "higyrus_client.aio"]

[[tool.importlinter.contracts]]
name = "matriz_client._core does not depend on transport modules"
type = "forbidden"
source_modules = ["matriz_client._core"]
forbidden_modules = ["matriz_client.client", "matriz_client.aio"]
```

**CLI invocation:**
```bash
uv run lint-imports
# Exit 0 = all contracts pass.  Exit non-0 = at least one contract violated.
```

**CI step (`.github/workflows/ci.yml` — append to existing `lint` job):**

```yaml
- name: Enforce import boundaries (Phase 7 REFAC-03)
  run: uv run lint-imports
```

### Example 2: Cross-leak sentinel test (parametrized, with matriz skip)

```python
# verification/test_sync_async_isolation.py — NEW Plan 1
# Source: CONTEXT.md D-10 + Phase 6 D-12 sentinel naming + research Pattern Cross-leak

from __future__ import annotations

import importlib
from typing import Any

import pytest
from pytest_httpx import HTTPXMock

# Parametrize tuples: (pkg_name, header_name, value_prefix, sync_call_factory, async_call_factory)
# Each call_factory returns a callable that fires a single request — the test inspects the wire.
_PACKAGES: list[tuple[str, str, str]] = [
    ("ambito_financiero_client", "<base_url_check>", ""),  # no auth — base_url-in-URL check
    ("iol_client", "Authorization", "Bearer "),
    ("higyrus_client", "Authorization", "Bearer "),
    ("matriz_client", "X-Auth-Token", ""),
]


@pytest.mark.parametrize("pkg_name, header_name, value_prefix", _PACKAGES)
def test_sync_token_isolation_in_wire_request(
    pkg_name: str, header_name: str, value_prefix: str, httpx_mock: HTTPXMock,
) -> None:
    """Phase 7 D-10: SYNC sentinel reaches the wire request unchanged."""
    if pkg_name == "matriz_client":
        # D-11: matriz aio.py is stub until Phase 10 REFAC-04 + TokenStore.
        pass  # sync still tested below
    pkg = importlib.import_module(pkg_name)
    sentinel = f"SYNC-sentinel-{pkg_name}"
    if pkg_name == "ambito_financiero_client":
        pkg.configure(base_url="https://sync-test.example.com")
        httpx_mock.add_response(json=[])
        pkg.get_dollar_banco_nacion(__import__("datetime").date(2026, 1, 2))
        req = httpx_mock.get_requests()[-1]
        assert "sync-test.example.com" in str(req.url)
    else:
        pkg.configure(token=sentinel, token_expires_at=9_999_999_999.0)
        # Fire one auth'd request; httpx_mock will catch.
        # Per-package endpoint setup (planner refines):
        if pkg_name == "iol_client":
            httpx_mock.add_response(url=lambda u: True, json={})
            pkg.get_quote("GGAL")
        elif pkg_name == "higyrus_client":
            httpx_mock.add_response(url=lambda u: True, json={"status": "ok"})
            pkg.get_health()
        elif pkg_name == "matriz_client":
            httpx_mock.add_response(json={"segments": []})
            pkg.get_segments()
        req = httpx_mock.get_requests()[-1]
        assert req.headers.get(header_name) == f"{value_prefix}{sentinel}"


@pytest.mark.parametrize("pkg_name, header_name, value_prefix", _PACKAGES)
async def test_async_token_isolation_in_wire_request(
    pkg_name: str, header_name: str, value_prefix: str, httpx_mock: HTTPXMock,
) -> None:
    """Phase 7 D-10/D-11: ASYNC sentinel reaches the wire request unchanged.

    matriz: skipped until Phase 10 REFAC-04 lands the REST async surface.
    """
    if pkg_name == "matriz_client":
        pytest.skip("matriz aio.py REST stub hasta Phase 10 REFAC-04 + TokenStore")
    pkg = importlib.import_module(pkg_name)
    aio = pkg.aio  # type: ignore[attr-defined]
    sentinel = f"ASYNC-sentinel-{pkg_name}"
    if pkg_name == "ambito_financiero_client":
        aio.configure(base_url="https://async-test.example.com")
        httpx_mock.add_response(json=[])
        import datetime as dt
        await aio.get_dollar_banco_nacion(dt.date(2026, 1, 2))
        req = httpx_mock.get_requests()[-1]
        assert "async-test.example.com" in str(req.url)
    else:
        aio.configure(token=sentinel, token_expires_at=9_999_999_999.0)
        if pkg_name == "iol_client":
            httpx_mock.add_response(url=lambda u: True, json={})
            await aio.get_quote("GGAL")
        elif pkg_name == "higyrus_client":
            httpx_mock.add_response(url=lambda u: True, json={"status": "ok"})
            await aio.get_health()
        req = httpx_mock.get_requests()[-1]
        assert req.headers.get(header_name) == f"{value_prefix}{sentinel}"
```

### Example 3: B8 alias preservation test (existing — must stay green)

```python
# packages/higyrus-client/tests/test_client_class.py:359-369
# Source: existing codebase — Phase 7 D-04 must NOT break this.

def test_aio_imports_raise_for_response_from_client() -> None:
    """B8 enforcement: ``aio._raise_for_response is client._raise_for_response``."""
    from higyrus_client.aio import _raise_for_response as a_impl
    from higyrus_client.client import _raise_for_response as c_impl
    assert a_impl is c_impl  # ← both alias _core.raise_for_response (D-04)
```

### Example 4: matriz `_core.py` skeleton (Plan 5 ATOMIC scope)

```python
# packages/matriz-client/src/matriz_client/_core.py — NEW Plan 5

"""Pure builders and parsers for the matriz REST client.

Phase 7 REFAC-03 + CR-03 (body-consume-then-raise). NO imports from
matriz_client.client or matriz_client.aio (enforced by import-linter contract).

All functions are pure: state in → RequestSpec or typed result out. No I/O.
Auth-flow primitives (build_login_request / parse_login_response) feed the
transport shell which performs the actual HTTP call.
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import httpx

from matriz_client._state import _TOKEN_TTL, _ClientState
from matriz_client.exceptions import AuthenticationError, PrimaryAPIError
from matriz_client.models import (
    AccountReport, DetailedPosition, Instrument, InstrumentDetail,
    MarketDataSnapshot, NewOrderResponse, Order, Position, Segment, Trade,
)
from matriz_client.types import (
    DEFAULT_MARKET_DATA_ENTRIES, CFICode, MarketDataEntry, MarketId,
    OrderType, SegmentId, Side, TimeInForce,
)

# ---------------------------------------------------------------------
# RequestSpec — D-01 per-package
# ---------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RequestSpec:
    method: str
    path: str
    params: dict[str, Any] | None = None
    headers: dict[str, str] | None = None
    auth_basic: tuple[str, str] | None = None
    # idempotent: bool = False  # Phase 8 RELY-03 forward-decl (planner discretion)


# ---------------------------------------------------------------------
# Stateless helpers — D-04 (moved from client.py with alias re-export)
# ---------------------------------------------------------------------


def raise_for_response(resp: httpx.Response) -> None:
    resp.raise_for_status()


def unwrap(data: dict[str, Any], key: str, endpoint: str) -> Any:
    if key not in data:
        raise PrimaryAPIError(
            status="ERROR",
            description=f"missing envelope key '{key}' in response from {endpoint}",
            message=None,
        )
    return data[key]


def parse_envelope_response(resp: httpx.Response, endpoint: str) -> dict[str, Any]:
    """D-06 cierre CR-03 — body consume EXPLICIT antes de cualquier raise."""
    resp.read()  # CR-03 fix: explicit body consume (HTTP/2-safe)
    raise_for_response(resp)
    raw = resp.json()
    if not isinstance(raw, dict):
        raise PrimaryAPIError(
            status="ERROR",
            description=f"expected JSON object body at {endpoint}, got {type(raw).__name__}",
            message=None,
        )
    if raw.get("status") == "ERROR":
        raise PrimaryAPIError(
            status="ERROR",
            description=raw.get("description"),
            message=raw.get("message"),
        )
    return raw  # type: ignore[return-value]


# ---------------------------------------------------------------------
# Auth-flow primitives — D-02
# ---------------------------------------------------------------------


def build_login_request(state: _ClientState) -> RequestSpec:
    if not state.username or not state.password:
        raise AuthenticationError("ERROR", "PRIMARY_USER and PRIMARY_PASSWORD must be set")
    return RequestSpec(
        method="POST",
        path="/auth/getToken",
        headers={"X-Username": state.username, "X-Password": state.password},
    )


def parse_login_response(resp: httpx.Response) -> tuple[str, float]:
    """Returns (token, expires_at_epoch).  Token comes from RESPONSE HEADER (D-22 Phase 6).
    """
    resp.read()
    raise_for_response(resp)
    token = resp.headers.get("X-Auth-Token")
    if not isinstance(token, str) or not token:
        raise AuthenticationError("ERROR", "No X-Auth-Token header in response")
    expires_at = time.time() + _TOKEN_TTL
    return token, expires_at


def token_is_fresh(state: _ClientState) -> bool:
    """Pure freshness check — no I/O. Transport shell uses this."""
    return bool(state.token and time.time() < state.token_expires_at)


# ---------------------------------------------------------------------
# Endpoint builders — § per CONTEXT.md D-05 endpoint groups
# ---------------------------------------------------------------------


# -- Segments (§4) ----------------------------------------------------


def build_get_segments_request(state: _ClientState) -> RequestSpec:  # noqa: ARG001
    return RequestSpec(method="GET", path="/rest/segment/all")


def parse_get_segments_response(resp: httpx.Response) -> list[Segment]:
    data = parse_envelope_response(resp, "/rest/segment/all")
    return [Segment.from_api(s) for s in unwrap(data, "segments", "/rest/segment/all")]


# -- Instruments (§5) -------------------------------------------------


def build_get_all_instruments_request(state: _ClientState) -> RequestSpec:  # noqa: ARG001
    return RequestSpec(method="GET", path="/rest/instruments/all")


def parse_get_all_instruments_response(resp: httpx.Response) -> list[Instrument]:
    path = "/rest/instruments/all"
    data = parse_envelope_response(resp, path)
    return [Instrument.from_api(i) for i in unwrap(data, "instruments", path)]


# ... (similar para los demás endpoints) ...


# -- Risk (§9) — NO envelope (D-07) ----------------------------------


def build_get_detailed_positions_request(state: _ClientState, account_name: str) -> RequestSpec:
    return RequestSpec(
        method="GET",
        path=f"/rest/risk/detailedPosition/{account_name}",
        auth_basic=(state.username, state.password),
    )


def parse_get_detailed_positions_response(resp: httpx.Response, endpoint: str) -> DetailedPosition:
    """Risk API — payload raíz ES el result (sin envelope key)."""
    resp.read()
    raise_for_response(resp)
    raw = resp.json()
    if not isinstance(raw, dict):
        raise PrimaryAPIError(
            status="ERROR",
            description=f"expected dict body at {endpoint}, got {type(raw).__name__}",
            message=None,
        )
    if raw.get("status") == "ERROR":
        raise PrimaryAPIError(
            status="ERROR",
            description=raw.get("description"),
            message=raw.get("message"),
        )
    return DetailedPosition.from_api(raw)
```

### Example 5: matriz `client.py` post-refactor (shell only)

```python
# packages/matriz-client/src/matriz_client/client.py — Plan 5 post-refactor

"""... existing docstring ..."""

from __future__ import annotations

import time
from typing import Any, Self

import httpx
from dotenv import load_dotenv

from matriz_client import _core
from matriz_client._core import RequestSpec
from matriz_client._state import _REQUEST_TIMEOUT, _TOKEN_TTL, _ClientState
from matriz_client.exceptions import AuthenticationError, PrimaryAPIError
from matriz_client.models import (
    AccountReport, DetailedPosition, Instrument, InstrumentDetail,
    MarketDataSnapshot, NewOrderResponse, Order, Position, Segment, Trade,
)
from matriz_client.types import (
    DEFAULT_MARKET_DATA_ENTRIES, CFICode, MarketDataEntry, MarketId,
    OrderType, SegmentId, Side, TimeInForce,
)

load_dotenv()

# D-04 aliases (B8 preservation) — both `client._raise_for_response is _core.raise_for_response`
# and `aio._raise_for_response is _core.raise_for_response`. Tests verifying
# `aio._raise_for_response is client._raise_for_response` pass.
_raise_for_response = _core.raise_for_response
_unwrap = _core.unwrap

__all__ = [
    "Client", "cancel_order", "configure", "get_account_report", "get_active_orders",
    "get_all_instruments", "get_all_orders", "get_detailed_positions",
    # ... unchanged from Phase 6 ...
]


class Client:
    __slots__ = ("_state",)

    def __init__(self, *, base_url=None, username=None, password=None, token=None, token_expires_at=None) -> None:
        # ... unchanged from Phase 6 ...
        pass

    # -- Lifecycle (unchanged) ---------------------------------------

    def __enter__(self) -> Self: ...
    def __exit__(self, *args: Any) -> None: ...
    def close(self) -> None: ...
    def __repr__(self) -> str: ...
    def __reduce__(self) -> Any: ...
    def __deepcopy__(self, memo: dict[int, Any]) -> Self: ...

    # -- HTTP client lazy accessor (unchanged) -----------------------

    def _ensure_http_client(self) -> httpx.Client: ...

    # -- Auth ---------------------------------------------------------

    def login(self) -> str:
        spec = _core.build_login_request(self._state)
        http = self._ensure_http_client()
        resp = http.request(spec.method, f"{self._state.base_url}{spec.path}", headers=spec.headers)
        token, expires_at = _core.parse_login_response(resp)
        self._state.token = token
        self._state.token_expires_at = expires_at
        return token

    def _ensure_token(self) -> None:
        if _core.token_is_fresh(self._state):
            return
        self.login()

    # -- Request plumbing -- THIN SHELL (D-03) -----------------------

    def _request(self, spec: RequestSpec) -> httpx.Response:
        http = self._ensure_http_client()
        url = f"{self._state.base_url}{spec.path}"
        if spec.auth_basic is not None:
            return http.request(spec.method, url, params=spec.params, auth=httpx.BasicAuth(*spec.auth_basic))
        self._ensure_token()
        assert self._state.token is not None
        headers = {"X-Auth-Token": self._state.token, **(spec.headers or {})}
        return http.request(spec.method, url, params=spec.params, headers=headers)

    # -- Segments (§4) — example of ≤ 30-50 LOC group ---------------

    def get_segments(self) -> list[Segment]:
        spec = _core.build_get_segments_request(self._state)
        return _core.parse_get_segments_response(self._request(spec))

    # -- Risk (§9) — example, NO envelope -------------------------

    def get_detailed_positions(self, account_name: str) -> DetailedPosition:
        spec = _core.build_get_detailed_positions_request(self._state, account_name)
        return _core.parse_get_detailed_positions_response(self._request(spec), spec.path)


# ... rest of module (delegators, PEP 562 shim) unchanged from Phase 6 ...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Sync/async logic duplicated 2× per package | `_core.py` pure helpers + transport shells | Phase 7 (this) | -30 to -55% LOC en `client.py`+`aio.py` agregado por paquete |
| matriz `_request` decodes JSON inline + raises post-json | `_core.parse_envelope_response` consumes body first, then raises | Phase 7 D-06 (CR-03) | HTTP/2 connection pool safe; future `http2=True` enable sin auditoría |
| 18 sweep probes con ~95% boilerplate en main_matriz.py | `_envelope_probe(envelope_key=...)` helper preserves 2 risk probes con `envelope_key=None` | Phase 7 D-07 (CR-05) | Drift prevention; agregar nuevo probe = 1 línea + assertion |
| `_raise_for_response` duplicated entre client.py y aio.py (some packages) | Single source en `_core.py` + alias re-export D-04 | Phase 7 (this) | B8 enforcement tests stay green; legacy imports preserved |
| Grep CI rule fragile (false-positives en comentarios) | `import-linter` v2.11 declarativo en pyproject.toml | Phase 7 D-09 | Robust, descendant-transitive, soporta ignore_imports granular |

**Deprecated/outdated:**
- ❌ `cp client.py aio.py && sed s/Client/AsyncClient/` para crear matriz aio.py — Pitfall 8. Phase 10 USA `_core.py` de matriz para construir aio.py REST surface; copy-paste está OUT.
- ❌ Reading internals via `pkg.client._token` directly — gradualmente removido via PEP 562 shim + tests migrados. Phase 7 NO toca este flujo (D-16 snapshot preservation).

## Assumptions Log

> Claims marcados `[ASSUMED]` necesitan confirmación del usuario antes de execution.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | LOC drop ≥30% client+aio agregado por paquete es achievable. | Standard Stack metric / D-14 | Si ámbito específicamente no llega a 30% (caso más probable — sin auth, sin token refresh, parsing simple), el planner debe documentar el shortfall en SUMMARY.md. Locked decision D-14 acepta esto explícitamente. |
| A2 | `import-linter` 2.11 con `as_packages=True` (default) detecta correctamente intentos de import dentro de submódulos privados (e.g., `_core._helpers`). | Standard Stack | Si import-linter no detecta submódulos, el contract pasa silently — falla en CI verde. Plan 1 debe incluir un test de smoke (committed file with `from .client import X` en `_core.py` → expect `lint-imports` exit non-0). |
| A3 | `verification/test_sync_async_isolation.py` parametrizado funciona con pytest-httpx para ámbito (que no tiene auth — el test usa base_url como sentinel proxy). | Code Examples Example 2 | Si ámbito async path no fira el wire request en el contexto del test (e.g., aio.configure no resetea event_hooks), el assertion `"async-test.example.com" in str(req.url)` falla. Planner valida con un prototype local. |
| A4 | matriz `_envelope_probe` puede absorber 15 de las 18 probes — las 3 con side-effects (`probe_get_segments`, `probe_get_all_instruments`, `probe_get_market_data`) quedan custom. | Architecture Patterns Pattern 7 | Si las 3 custom suman >50% LOC de las 18 originales, CR-05 "~95% boilerplate eliminado" no se cumple literal. Planner ajusta el helper (opción b: agregar `post_unwrap_hook`) o documenta el shortfall. |
| A5 | Test count baseline 393 (verificado en research env) es el mismo que CI ve al cierre de Phase 6. | Pitfall 4 | Si Phase 6 tiene tests adicionales no committed o el CI corre subset diferente, la métrica falla. Plan 1 debe re-medir en CI fresh checkout. |
| A6 | El alias D-04 (`client._raise_for_response = _core.raise_for_response`) preserva `a_impl is c_impl` en TODOS los paquetes (3 de 4 — matriz no tiene aio.py REST). | Common Pitfalls Pitfall 2 | Test B8 explícito en ambito + higyrus + iol tests/test_client_class.py. Si por alguna razón Python optimiza el alias (improbable), tests fallan loudly. Es básicamente garantizado por Python semantics. |
| A7 | El snapshot test guard para 18 probes (D-08) puede ser un único archivo `verification/test_matriz_sweep_snapshot.py` parametrizado, no 18 archivos. | Pattern 7 | Si las probes tienen dependencias entre sí (probe 5 requiere `_resolved_symbol` de probe 3), el snapshot test debe ordenarlos. Locked: `pytest.mark.parametrize` con fixture-style state. |
| A8 | matriz Plan 5 `_request` puede ofrecer wrapper de back-compat para main_matriz.py sin romper los 18 probes pre-snapshot. | Common Pitfalls Pitfall 7 | Si el wrapper no cubre exactly el contrato actual de `_matriz_request`, los probes fallan en el snapshot test pre-refactor. Planner verifica en setup del snapshot test. |
| A9 | `pyproject.toml` raíz acepta nuevos `[dependency-groups]` adds sin requerir `uv sync --refresh-lock`. | Standard Stack | Si `uv.lock` requiere regenerate después de agregar `import-linter`, Plan 1 debe incluir `uv lock` step + commit del lockfile. |

## Open Questions

1. **¿Cuántas LOC mide cada `_core.py` esperado por paquete?**
   - What we know: ámbito client.py=270, aio.py=287 (=557). iol client.py=522, aio.py=476 (=998). higyrus client.py=685, aio.py=669 (=1354). matriz client.py=754, aio.py=103 (=857 sync-only, aio stub). Endpoint counts: ámbito 1, iol 4, higyrus 5, matriz ~19.
   - What's unclear: el tamaño exacto de `_core.py` por paquete dependerá del verbose del builder/parser. Estimaciones bottom-up: ámbito ~80 LOC, iol ~250 LOC, higyrus ~350 LOC, matriz ~450 LOC.
   - Recommendation: planner mide post-Plan-2 (ámbito canary) y refina para Plans 3-5. El SUMMARY.md de cada Plan reporta `_core.py: 0 → N (NEW)` para tracking.

2. **¿Snapshot test para 18 probes debe usar `pytest-httpx` o `httpx.MockTransport`?**
   - What we know: `pytest-httpx` es dev dep, ya usado extensamente en tests. `httpx.MockTransport` es la API low-level de httpx que pytest-httpx wraps.
   - What's unclear: para 18 probes con payloads diferentes, ¿es legible inline en el test o se mueve a `tests/fixtures/`?
   - Recommendation: pytest-httpx inline payloads (consistent con Phase 6 06-02-PLAN.md). Si algún payload supera ~30 líneas, factor a fixture file.

3. **¿`import-linter` debe correr en pre-commit o solo en CI?**
   - What we know: `pre-commit` está configurado (`.pre-commit-config.yaml`). CI tiene un lint job separado.
   - What's unclear: Plan 1 D-09 dice "CI step `lint-imports` en `.github/workflows/ci.yml`" — no menciona pre-commit.
   - Recommendation: solo CI por ahora (rápido, sin slowdown del workflow local). Pre-commit lo agrega un follow-up si lints exceden 5s — improbable para este repo.

4. **¿`_core.py` placeholder en Plan 1 o se difiere hasta Plan 2?**
   - What we know: CONTEXT.md "Plan 1 NO bloquea Plan 2 (no introduce dependencia en `_core.py`); plan 2-5 RECONFIRMA contracts a medida que `_core.py` aparece."
   - What's unclear: si `_core.py` no existe en Plan 1, ¿import-linter reporta WARN ("Could not find package") o pasa silente?
   - Recommendation: Plan 1 crea `<pkg>/_core.py` placeholder con solo docstring + `from __future__ import annotations`. Esto: (a) verifica que import-linter encuentra el módulo, (b) prepara el terreno para Plans 2-5 que sólo extienden el archivo. **Pitfall 6 documenta el riesgo.**

5. **¿`matriz._request` wrapper de back-compat es la solución mejor o migrar `main_matriz.py` al patrón `spec → resp → parse`?**
   - What we know: main_matriz.py llama `_matriz_request(...)` que internally invoca `client._request("GET", path, ...)` y espera `dict[str, Any]`.
   - What's unclear: el wrapper de back-compat (custodia el contrato sync_legacy) vs migración del driver al nuevo contrato.
   - Recommendation: wrapper de back-compat **inicial** en Plan 5 (zero churn en main_matriz.py probes), con TODO comment para migrar en v1.2. La migración del driver es scope follow-up.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | All packages | ✓ | 3.12.11 (active venv at `.venv/`) | — |
| uv | Workspace mgmt | ✓ | 0.9.0+ | — |
| httpx | All packages (transport) | ✓ | >=0.27 (existing dep) | — |
| pytest | Test runner | ✓ | >=8.3 (existing dev dep) | — |
| pytest-httpx | Mock HTTP for cross-leak + snapshot tests | ✓ | >=0.34 (existing dev dep) | — |
| import-linter | NEW Plan 1 — CI gate | ✗ | needs >=2.11 from PyPI | None — if unavailable, fall back to grep CI rule (deprecated by D-09 but viable emergency option) |
| slopcheck | Research env — package legitimacy | ✗ | — | Manual verification via PyPI JSON + readthedocs.io docs (DONE — see Package Legitimacy Audit) |

**Missing dependencies with no fallback:** None — todo lo necesario para refactor + tests está disponible en el env existente. `import-linter` se agrega en Plan 1.

**Missing dependencies with fallback:** `import-linter` (fallback grep, NOT recommended); `slopcheck` (fallback manual verification, COMPLETED).

## Validation Architecture

> Aplicable: `workflow.nyquist_validation: true` en `.planning/config.json`.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.3+ |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command (per package) | `uv run pytest packages/<pkg>/ -x` |
| Full suite command | `uv run pytest -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REFAC-03 | `_core.py` no importa transport modules | CI gate (declarative) | `uv run lint-imports` | ❌ Plan 1 — pyproject.toml `[tool.importlinter]` + 4 contracts |
| REFAC-03 | sync sentinel reaches sync wire request only (cross-leak) | integration | `uv run pytest verification/test_sync_async_isolation.py -k test_sync_token_isolation -x` | ❌ Plan 1 — new file `verification/test_sync_async_isolation.py` |
| REFAC-03 | async sentinel reaches async wire request only (cross-leak) | integration | `uv run pytest verification/test_sync_async_isolation.py -k test_async_token_isolation -x` | ❌ Plan 1 — same file as above |
| REFAC-03 | `aio._raise_for_response is client._raise_for_response` (B8 / D-04 alias preservation) | unit | `uv run pytest packages/<pkg>/tests/test_client_class.py::test_aio_imports_raise_for_response_from_client -x` | ✅ Existe en 3 paquetes (ambito, higyrus, iol) — Phase 7 NO debe romperlo |
| REFAC-03 | Public surface snapshot unchanged (D-16) | snapshot | `uv run pytest verification/test_public_surface.py -x` | ✅ Phase 6 — Plan 6 verifica zero diff |
| REFAC-03 | `_core.build_X_request(state, ...)` retorna `RequestSpec` con shape esperado per endpoint | unit | `uv run pytest packages/<pkg>/tests/test_core.py -x` | ❌ Plan 2/3/4/5 — NEW per package `tests/test_core.py` (planner discretion) |
| REFAC-03 | `_core.parse_X_response(resp)` parser puro retorna typed result | unit | `uv run pytest packages/<pkg>/tests/test_core.py -x` | ❌ same as above |
| CR-03 | matriz `_core.parse_envelope_response` consume body antes de raise (HTTP/2 safe) | unit | `uv run pytest packages/matriz-client/tests/test_core.py::test_parse_envelope_consumes_body_before_raise -x` | ❌ Plan 5 — new test |
| CR-05 | 18 probes pre/post-refactor producen idéntico `ProbeResult` para payload canned | snapshot | `uv run pytest verification/test_matriz_sweep_snapshot.py -x` | ❌ Plan 5 — new file (Plan 5 D-08) |
| Cross | 393 baseline tests siguen verde post-cada-Plan | full suite | `uv run pytest -q` | ✅ Phase 6 baseline — Plans 2-5 verifican zero regression |

### Sampling Rate

- **Per task commit:** `uv run pytest packages/<pkg>/ -x` (paquete específico, ~5 segundos)
- **Per Plan merge:** `uv run pytest verification/ -x` + `uv run pytest packages/<pkg>/ -x` + `uv run lint-imports` + `uv run ruff check .` + `uv run mypy` (~30 segundos)
- **Phase gate:** Full suite green + ruff + mypy + lint-imports + snapshot zero-diff antes de `/gsd-verify-work` (~60 segundos)

### Wave 0 Gaps

- [ ] `verification/test_sync_async_isolation.py` — covers REFAC-03 cross-leak (D-10)
- [ ] `verification/test_matriz_sweep_snapshot.py` — covers CR-05 18 probes snapshot guard (D-08)
- [ ] `packages/<pkg>/tests/test_core.py` (× 4 paquetes) — covers per-package builders/parsers unit tests
- [ ] `pyproject.toml` `[tool.importlinter]` config — 4 contracts forbidden (Plan 1, REFAC-03 CI gate)
- [ ] `.github/workflows/ci.yml` step `uv run lint-imports` — Plan 1
- [ ] `import-linter>=2.11,<3` in `[dependency-groups] dev` — Plan 1
- [ ] `<pkg>/_core.py` placeholder per package — Plan 1 (Open Q #4 / Pitfall 6 mitigation)

## Security Domain

> `security_enforcement: true` en config.json — security domain incluido aunque Phase 7 sea pure refactor.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Auth-flow primitives (`build_login_request` + `parse_login_response`) preserve existing semantics per-package (D-02). Sin cambios al flow OAuth (iol), Bearer (higyrus), X-Auth-Token (matriz). Zero new auth code = zero new attack surface. |
| V3 Session Management | yes | `_state.token` + `_state.token_expires_at` + token TTL (`_TOKEN_TTL_*`) — sin cambios respecto a Phase 6. La extracción a `_core.token_is_fresh(state)` es pure read; no muta tiempos. |
| V4 Access Control | no | Phase 7 no introduce ni cambia controles de acceso. |
| V5 Input Validation | yes | Parsers (`_core.parse_X_response`) validan shape (`isinstance(raw, dict)`) y raise typed exceptions con descripción. NO se pasan datos no validados al caller. CR-03 fix garantiza body consumido antes de raise — defensa en profundidad para HTTP/2 stream leaks. |
| V6 Cryptography | yes | HTTP Basic Auth (matriz Risk API) sigue usando `httpx.BasicAuth(user, pass)`. NO se hand-rolla cripto. `auth_basic: tuple[str, str]` en `RequestSpec` es solo carrier de credenciales — la encoding la hace `httpx`. |
| V7 Error Handling | yes | `_core.raise_for_response` mapea HTTP status → exception. `_core.parse_envelope_response` consume body antes de raise (D-06 CR-03). Errores nunca exponen credentials (PEP 562 shim D-Q `_user`/`_password` deny-list de Phase 6 sigue activa). |
| V8 Data Protection | yes | Tokens NO se loggean (Phase 6 `__repr__` redaction se preserva). Phase 7 NO introduce logging de credentials. Phase 8 (siguiente) introduce structured logging con RedactingFilter. |
| V14 Configuration | yes | `import-linter` config en `pyproject.toml` raíz checked-in al repo — no se introducen secrets ni config sensible. |

### Known Threat Patterns for {Python sync/async HTTP client refactor}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| HTTP/2 connection pool stream leak via early raise | DoS | `resp.read()` antes de cualquier raise en parsers (CR-03 fix D-06) |
| Sync/async token cross-contamination (one surface writes token of another) | Tampering | `_core.py` is pure (no module state) + import-linter contract `forbidden` + cross-leak sentinel test (D-10) |
| Token leaked in `__repr__` durante debugging | Information Disclosure | `__repr__` redaction se preserva de Phase 6 (`password='***'`, `token='***'`). Phase 7 NO toca `__repr__`. |
| Test fixture monkeypatch ya no alcanza producción → tests pasan vacíos | Tampering (test integrity) | Phase 6 D-12 `SYNC-sentinel-<pkg>` / `ASYNC-sentinel-<pkg>` fixture-reaches-production guard sigue corriendo. Phase 7 lo EXTIENDE con cross-leak isolation. |
| `_core.py` accidentally re-imports transport state | Tampering | import-linter `forbidden` contract + cross-leak sentinel test (Pitfall 1 / D-09 / D-10) |
| `_envelope_probe` mistakenly migrates risk probes (envelope_key="" instead of None) | Information Disclosure / functional bug | Snapshot test guard (D-08) detecta cualquier diff de ProbeResult pre vs post refactor |

## Project Constraints (from CLAUDE.md)

> Directivas mandatorias del CLAUDE.md del proyecto que el planner DEBE honrar:

- **Tech stack inviolable:** Python 3.12+, httpx, pytest+pytest-httpx, ruff, mypy strict — toda extensión y fix respeta el stack. Phase 7 sólo agrega `import-linter` a dev deps; no toca runtime deps.
- **No shared internals between packages:** REQUEST-SPEC ES PER-PACKAGE (D-01 lock). NO crear `verification/_shared/RequestSpec.py` ni similar.
- **Dual sync/async mirroring:** TODO fix en `client.py` se ESPEJA en `aio.py` (deuda conocida que Phase 7 elimina). matriz aio.py es STUB hasta Phase 10 — Plan 5 NO toca matriz aio.py REST (sólo crea `_core.py`).
- **`from __future__ import annotations` mandatorio** en todo módulo nuevo (`_core.py` × 4, `test_sync_async_isolation.py`, `test_matriz_sweep_snapshot.py`).
- **No relative imports** (ruff TID rule) — `from matriz_client._core import RequestSpec`, NO `from ._core import RequestSpec`.
- **No wildcard imports** — `_core.py` explicit re-exports si necesarios.
- **Module-level docstring obligatorio** en cada nuevo archivo `_core.py` describing: purpose, API usage examples (`::` code blocks), env vars (N/A para `_core.py`), auth flow specifics (matriz/iol/higyrus).
- **Section dividers con `# ---...---`** separando logical blocks dentro de módulos grandes (auth, internals, endpoint groups). Aplica a `_core.py` per D-05 endpoint groups.
- **mypy strict:** `disallow_untyped_defs = true`, `warn_return_any = true`. Cada builder/parser tipa input y output explícitamente.
- **Ruff line-length=100 + double-quotes:** sin override en `_core.py`.
- **Credentials en `.env` por paquete, nunca commit ni log:** Phase 7 NO toca el flow de credentials — `_state.py` sigue siendo el único reader. `_core.build_login_request(state)` LEE de state, nunca expone.
- **Tests existentes (393, no 277) deben quedar verde después de cada Plan:** zero regression — incluyendo B8 alias tests (Pattern 6 / Pitfall 2).
- **GSD workflow enforcement:** todo cambio va via `/gsd-execute-phase`; planner respeta el flujo.

## Sources

### Primary (HIGH confidence)

- [VERIFIED: PyPI registry] `https://pypi.org/pypi/import-linter/json` — version 2.11, requires-python>=3.10, project URL `github.com/seddonym/import-linter`, License Apache-2.0 (consultado 2026-06-12)
- [CITED: official docs] `https://import-linter.readthedocs.io/en/v2.7/contract_types.html` — Forbidden contract type syntax (source_modules, forbidden_modules, ignore_imports, as_packages)
- [CITED: official docs] `https://import-linter.readthedocs.io/en/v2.7/usage.html` — `[tool.importlinter]` + `[[tool.importlinter.contracts]]` configuration in pyproject.toml; `lint-imports` CLI invocation
- [VERIFIED: codebase] `packages/matriz-client/src/matriz_client/client.py:91-114, 249-294` — CR-03 lines + `_raise_for_response` + `_unwrap` + `_request` actual shape
- [VERIFIED: codebase] `packages/iol-client/src/iol_client/client.py:71-82, 189-288, 503-522` — `_raise_for_response`, `Client.login`/`_refresh`/`_ensure_token`/`_request`, PEP 562 shim
- [VERIFIED: codebase] `packages/higyrus-client/src/higyrus_client/client.py:78-103, 207-303, 666-684` — `_raise_for_response` (parses errors[]), URL-encoding quirk (line 287), PEP 562 shim
- [VERIFIED: codebase] `packages/ambito-financiero-client/src/ambito_financiero_client/client.py:64-70, 164-185` — `_raise_for_response`, `_request`, no-auth endpoint pattern
- [VERIFIED: codebase] `packages/matriz-client/src/matriz_client/aio.py:1-104` — matriz async STUB (Phase 6 lifecycle only)
- [VERIFIED: codebase] `main_matriz.py:240-1402` — 18 sweep probes + 2 risk probes
- [VERIFIED: codebase] `packages/higyrus-client/tests/test_client_class.py:355-369` — B8 alias enforcement test `a_impl is c_impl`
- [VERIFIED: codebase] `pyproject.toml:23-32, 90-108` — existing dev deps + pytest config; verification/ already in testpaths
- [VERIFIED: codebase] `wc -l packages/{ambito,iol,higyrus,matriz}-client/src/*/{client,aio}.py` — Phase 6 LOC baseline (ámbito 557, iol 998, higyrus 1354, matriz 857)
- [VERIFIED: codebase] `uv run pytest --collect-only -q | tail -1` — 393/394 tests collected at Phase 6 close-out

### Secondary (MEDIUM confidence)

- [CITED] `.planning/research/SUMMARY.md` — "Phase 2: `_core.py` Extraction" architecture summary
- [CITED] `.planning/research/PITFALLS.md` — Pitfall 3 (re-coupling), Pitfall 8 (matriz aio.py copy-paste), Pitfall 18 (test weakening), Pitfall 21 (CR-03 HTTP/2 leak), Pitfall 23 (CR-05 risk probes preservation)
- [CITED] `.planning/phases/06-compat-safety-net-client-class-skeleton/06-PATTERNS.md` — Phase 6 file classification + PEP 562 shim canonical shape + B8 helper sharing pattern
- [CITED] `.planning/REQUIREMENTS.md` — REFAC-03, CR-03, CR-05 verbatim text
- [CITED] `.planning/ROADMAP.md` — Phase 7 goal + 5 success criteria
- [CITED] `.planning/STATE.md` — Phase 6 status (shipped 2026-06-11, PR #1)
- [CITED] `CLAUDE.md` — Tech stack constraints, naming patterns, module structure, code style, dual sync/async invariant

### Tertiary (LOW confidence — flagged for validation)

- [ASSUMED] LOC drop ≥30% achievable per package — no benchmark previo en este repo; A1 en Assumptions Log
- [ASSUMED] 3 de 18 matriz probes (con side-effects) no encajan exactamente en `_envelope_probe` helper — A4 en Assumptions Log
- [ASSUMED] `import-linter` con módulos placeholder vacíos reporta contracts como passing — A2 / Pitfall 6 / Open Q #4 — planner debe verificar empíricamente al introducir el primer contract

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — `import-linter` 2.11 verified via PyPI + docs oficiales + cross-confirmed search; resto de deps sin cambios desde Phase 6
- Architecture: HIGH — patrones validados (`@dataclass(frozen=True, slots=True)` ya usado en SafeModel + `_state.py`; B8 helper sharing ya funcional; transport shell pattern es mecánico)
- Pitfalls: HIGH — 7 pitfalls específicos a Phase 7 documentados con warning signs concretos; 5 de ellos rooted en código real del repo (`main_matriz.py`, `_raise_for_response` aliases, matriz `_request`)
- Security domain: HIGH — ASVS mapping completo; Phase 7 reduce attack surface (CR-03) sin agregar nuevos vectores
- LOC metric / sizing: MEDIUM — A1/A4 assumptions sólo verificables ejecutando el refactor

**Research date:** 2026-06-12
**Valid until:** 2026-07-12 (30 días — Phase 7 stack es estable; no se esperan cambios disruptive en import-linter 2.x ni httpx 0.27.x)
