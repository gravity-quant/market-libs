# Phase 26: Calendar write - Research

**Researched:** 2026-07-31
**Domain:** Extensión de cliente HTTP Python — segunda superficie de mutación (`market-data-client`) detrás del mutating-gate de Phase 25, dual sync/async, mypy-strict
**Confidence:** HIGH (todo verificado esta sesión contra el código shipeado, la OpenAPI en vivo y ejecuciones locales de httpx/pytest)

## Summary

Phase 26 agrega la **segunda superficie de mutación** a `market-data-client` — los cinco
endpoints de calendar write — reusando **sin ningún cambio** el mutating-gate construido y
AST-verificado en Phase 25. La investigación confirma que las 17 decisiones lockeadas de
`26-CONTEXT.md` son ejecutables tal cual contra el código actual: `RequestSpec` ya carga
`method`/`path`/`json_body`/`idempotent`/`endpoint_name`/`authenticated` y no necesita cambio
estructural; ambos shells ya threadean `json=spec.json_body` y `req.extensions["idempotent"]`;
`_ensure_mutation_allowed()` ya existe idéntico en `client.py:257` y `aio.py:215`; y
`RetryTransport.handle_request` ya corta el loop de retry en la PRIMERA línea cuando
`idempotent` es falsy. El trabajo es puramente aditivo: 5 builders + 1 parser en `_core.py`,
3 request-models en `models.py`, 5 métodos × 2 shells + 10 shims, re-exports, y tests mockeados.

**Tres claims de CONTEXT.md fueron verificados empíricamente esta sesión** (no restated):
(1) **D-02 confirmado** — con httpx 0.28.1 pineado en `uv.lock`, `build_request("DELETE", url,
json=None)` emite `content == b""` y **ningún header `Content-Type`**, tanto a nivel `httpx.Client`
como end-to-end a través de `Client._request`. Cuidado: `json={}` SÍ emite `b"{}"` con
`Content-Type: application/json` — los dos builders DELETE deben pasar `json_body=None`, nunca
`{}`. (2) **D-04/D-15 confirmado** — un spec con `idempotent=False` contra tres 503 encadenados
produce **exactamente 1 request saliente y 0 sleeps**; el control positivo `idempotent=True`
produce 3 requests y 2 sleeps. (3) **D-16 confirmado** — `parse_calendar_response` sobre el
envelope real produce **4 objetos `CalendarDay` todos-default** (itera las claves del dict).

**El hallazgo que más contradice el material upstream:** `parse_health_response` **NO es
tolerante** — sobre un body vacío levanta `json.JSONDecodeError`, y sobre `null` o `[]` retorna
`None`/`list` mientras su anotación dice `dict[str, Any]`. D-06/D-07 piden un passthrough
"en el estilo de `parse_health_response`" **tolerante**; eso exige una **función nueva** con el
collection-guard (`if not resp.content: return {}` + `isinstance(raw, dict)`), no una reutilización
literal. Un segundo hallazgo de seguridad concreto: `day` interpolado RAW permite **retargeting de
request** — `day="../config"` colapsa a `DELETE /api/calendar/config` (verificado con httpx).

**Primary recommendation:** Implementar D-01…D-17 verbatim, espejando `build_create_symbol_request`
(builder con body), `build_segments_request` (builder zero-kwarg), `build_update_symbol_request`
(builder con path-param), `NewSymbol.to_dict()` (request-model) y `NewSymbols.__post_init__`
(bound `ValueError`). Escribir **un parser passthrough tolerante nuevo** (no reusar
`parse_health_response`), pasar `json_body=None` explícito en los DELETE, y añadir un guard de
path-safety para `day` (ver Open Question 1).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**A. Builders + routing (`_core.py`)**
- **D-01:** Add **five** pure builders to `_core.py` mirroring the Phase-25 symbols
  builders (`del state`, already-serialized `json_body` passed in):
  `build_set_calendar_config_request` (`PUT /calendar/config`),
  `build_delete_calendar_config_request` (`DELETE /calendar/config`),
  `build_preview_calendar_config_request` (`POST /calendar/config/preview`),
  `build_add_holidays_request` (`POST /calendar/holidays`),
  `build_delete_holiday_request` (`DELETE /calendar/holidays/{day}`).
  All `authenticated=True`, each with a distinct `endpoint_name`.
- **D-02:** `RequestSpec` needs **no structural change** (Phase-25 D-06 holds). The two
  DELETE builders simply leave `json_body=None`; verified against the pinned httpx 0.28.1
  that `build_request("DELETE", url, json=None)` emits no body and no `Content-Type`.
  `build_segments_request` is the zero-kwarg template; `build_update_symbol_request` is
  the path-param template.
- **D-03:** `day` is interpolated **RAW** into `/calendar/holidays/{day}` — no
  `urllib.parse.quote()`. The live OpenAPI declares the path param as
  `{"type":"string","format":"date"}` (ISO `YYYY-MM-DD`), so the D-08 `"DLR/DIC26"`
  encoding risk does not apply here.
- **D-04:** Idempotency per DM-03 — `idempotent=True` for `PUT /calendar/config`,
  `DELETE /calendar/config`, `POST /calendar/config/preview` (compute-only) and
  `DELETE /calendar/holidays/{day}`; **`idempotent=False` for `POST /calendar/holidays`**
  (append is not idempotent). Revalidated live in Phase 27.

**B. Return types + parsers**
- **D-05:** `set_calendar_config`, `delete_calendar_config` and `preview_calendar_config`
  return the existing typed **`CalendarConfig`**, reusing the existing
  `_core.parse_calendar_config_response` unchanged. Rationale: the three operate on the
  same config resource whose real develop wire shape is already captured and already
  matches `CalendarConfig` field-for-field; the model even carries `warnings`, which is
  exactly what the OpenAPI ties `confirm` to.
- **D-06:** `add_holidays` and `delete_holiday` return **`dict[str, Any]`** via a
  passthrough parser in the `parse_health_response` style. They must **NOT** reuse
  `parse_calendar_response` nor return `list[CalendarDay]` — that model/parser pair is
  broken against the real wire (see D-16).
- **D-07:** All new parsers keep the package's body-consume-then-raise order
  (`resp.read()` → `raise_for_response(resp)` → decode) and stay tolerant of an
  empty/`null` body (`CalendarConfig.from_api(None)` for the config trio; `{}` for the
  holiday pair). Response shapes are unverified against the live server by design —
  tolerance is the hedge until Phase 27.

**C. Request models (`models.py`)**
- **D-08:** Model `MarketHoursIn`, `HolidayIn`, `HolidaysIn` as frozen
  `@dataclass(frozen=True, slots=True)` — **NOT** `SafeModel` subclasses (they serialize
  OUTWARD), each with a hand-written `to_dict()`, exactly per Phase-25 D-09.
- **D-09:** `confirm` is a **field of `MarketHoursIn`** (`confirm: bool = False`), always
  emitted on the wire — not a separate keyword-only method parameter. Method signature
  stays model-only: `set_calendar_config(config: MarketHoursIn)`. This satisfies ROADMAP
  criterion 2 (`confirm` exposed with default `False`) and matches the `NewSymbol.market_id`
  defaulted-and-always-emitted precedent (Phase-25 D-10).
- **D-10:** Field defaults follow the live OpenAPI verbatim: `MarketHoursIn` requires
  `open_time`/`close_time`/`timezone` and defaults `pre_open_minutes=10`, `enabled=True`,
  `updated_by=""`, `confirm=False`. `HolidayIn` requires `day` and defaults `closed=True`,
  `open_time=None`, `close_time=None`, `description=""`.
- **D-11:** `to_dict()` routes through `_params.drop_none` (ROADMAP criterion 3). Effect:
  `HolidayIn.open_time`/`close_time` are **dropped when `None`**, while `closed=True` and
  `description=""` are **always emitted** (`drop_none` preserves falsy-but-not-`None`).
  `MarketHoursIn.to_dict()` routes through it too even though it is a no-op there (no
  nullable fields) — consistency. `HolidaysIn.to_dict()` →
  `{"days": [d.to_dict() for d in self.days]}`.

**D. Validation**
- **D-12:** Enforce the `HolidaysIn.days` **1–500** bound client-side in
  `__post_init__`, raising a plain **`ValueError`** — an exact mirror of the `NewSymbols`
  check (Phase-25 D-11). The live OpenAPI declares `days: {minItems: 1, maxItems: 500}`;
  the source plan omitted this bound.
- **D-13:** Scalar field bounds are **NOT** validated client-side — `pre_open_minutes`
  (0–120), `timezone` (1–64), `updated_by` (≤200), `description` (≤500), and the
  `HH:MM` time format all go to the server's `422` via the existing `raise_for_response`.
  This matches the real Phase-25 precedent: `NewSymbol.symbol` has a declared 1–255 bound
  that Phase 25 deliberately did not enforce. A client-side `HH:MM` regex would also risk
  false negatives (the OpenAPI uses `format: time`, which admits `"10:00:00"`).

**E. Gate, parity, and the no-retry proof**
- **D-14:** `_ensure_mutation_allowed()` is the **literal first statement** of all five
  new methods on both shells — before spec build, before any token fetch, before any
  transport touch (Phase-25 D-04/D-05, AST-verified). `preview_calendar_config` is
  compute-only and does not persist, but it is a POST and therefore **still passes
  through the gate** — this read-safe exception is documented, not carved out.
- **D-15:** Phase 26 must add the **first dispatch-level `idempotent=False` no-retry
  test** in this package: `add_holidays` against a repeated 503 must emit **exactly one**
  outgoing request. Phase 25 never exercised this path (all three symbols builders are
  `idempotent=True`), and the package's existing `idempotent` assertions are builder-level
  only (`tests/test_core.py`). If a contrasting `idempotent=True` positive control is
  included, use the `monkeypatch.setattr(time, "sleep", ...)` pattern from
  `tests/test_transport.py` to avoid real jitter sleeps.
- **D-16:** Phase 26 does **NOT** fix the pre-existing `get_calendar` / `CalendarDay` /
  `parse_calendar_response` envelope bug (Phase-22 read surface, now proven — see
  Deferred). It only avoids inheriting it (D-06) and records it as a Phase-27 finding.
  This mirrors how Phase 25 disposed of the analogous WR-01 read-path bug.
- **D-17:** Mirror every method, model, shim and export across `client.py` AND `aio.py`
  identically; module-level sync shims delegate to `_get_default()`, async shims stay
  under `aio`; add the three models to `models.py` `__all__` and re-export everything
  through `__init__.py` `__all__`. Parity is enforced by the in-package
  `tests/test_public_surface_market_data.py` (Phase-25 D-15/D-16).

### Claude's Discretion

- Exact builder/parser/helper naming beyond the DM-locked public method names
  (`set_calendar_config`, `delete_calendar_config`, `preview_calendar_config`,
  `add_holidays`, `delete_holiday`); test file organization (whether calendar-write tests
  live in new `test_calendar_write.py` / `test_calendar_write_async.py` files mirroring
  `test_symbols_write*.py`, or extend existing ones); whether the two holiday passthrough
  parsers are one shared function or two.

### Deferred Ideas (OUT OF SCOPE)

**Pre-existing read-surface bug — record as a Phase-27 finding, do NOT fix here (D-16):**
- `GET /calendar` really returns a dict envelope `{config, coverage, days[], market}`, but
  `_core.parse_calendar_response` iterates `raw` as a list — so it iterates the envelope's
  **keys** and yields four all-default `CalendarDay` objects. Compounding it, `CalendarDay`'s
  fields (`date`/`marketId`/`isBusinessDay`) do not exist on the wire, whose `days[]` items
  are `{day, closed, open_time, close_time, description}` — i.e. the `HolidayIn` shape.
  Proven by `.planning/verification/schemas/market-data-client/get-calendar.json`. The
  Phase-23 live probe never flagged it because `main_market_data.py` only emits a shape
  finding when the payload is a `list`. This is Phase-22 code outside MUT-MD-02's boundary,
  and it is the natural verification path for `add_holidays` — so Phase 27 should fix it
  alongside the already-carried WR-01 `parse_latest_response` envelope gap, before Phase 28
  publishes v0.3.0.

**Confirm live against develop in Phase 27 (LIVE-MUT-01):**
- The concrete 200 body of each of the five calendar-write endpoints. The live OpenAPI
  declares them all as bare `object` with no schema, so D-05's `CalendarConfig` typing and
  D-06's `dict[str, Any]` are evidence-based bets, not contracts. Tolerant parsers (D-07)
  are the hedge.
- Real server-side idempotency of `PUT /calendar/config` and `DELETE /calendar/holidays/{day}`
  (DM-03 assigns `idempotent=True` on HTTP-semantics grounds only), and whether
  `POST /calendar/holidays` is genuinely non-idempotent as assumed (D-04).
- Whether the server accepts `"HH:MM"` only or also `"HH:MM:SS"` for `open_time`/`close_time`
  (`format: time`), and the real effect of dropping vs. sending `null` for a holiday's
  time overrides (D-11).

**Out of scope of this milestone (backlog v2):** SSE streaming (STREAM-MD-01), Auth0 token
disk cache (SEC-MD-01), JWT signature validation (SEC-MD-02) — per DM-08.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MUT-MD-02 | Calendar write: `PUT /calendar/config` (`MarketHoursIn`, respeta `confirm`), `DELETE /calendar/config`, `POST /calendar/config/preview` (`MarketHoursIn`), `POST /calendar/holidays` (`HolidaysIn`), `DELETE /calendar/holidays/{day}` — request-models tipados, sync y async, detrás del mutating-gate | Los 5 endpoints + los 3 schemas fueron **verificados contra la OpenAPI en vivo esta sesión** (§ Contrato de la API en vivo). Templates exactos ya en el paquete: `build_create_symbol_request` (builder con body), `build_segments_request` (zero-kwarg), `build_update_symbol_request` (path-param), `NewSymbol`/`NewSymbols` (request-models + `to_dict()` + `__post_init__`), `parse_calendar_config_response` (parser single-object tolerante, reusable verbatim por D-05), `_params.drop_none`, `_ensure_mutation_allowed()` (gate, sin cambios), `req.extensions["idempotent"]` (no-retry, verificado empíricamente), `test_symbols_write*.py` / `test_mutation_gate.py` / `test_public_surface_market_data.py` (templates de test) |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

| Directiva | Impacto en Phase 26 |
|-----------|---------------------|
| Python 3.12+, uv, httpx (sync+async), pytest+pytest-httpx, ruff, mypy strict | Sin dependencias nuevas; todo el código nuevo debe pasar los 4 gates |
| Estado singleton a nivel módulo; **sin código compartido entre paquetes** | Los 5 builders/parsers/modelos viven dentro de `market_data_client`; **prohibido** importar de `higyrus_client` u otro paquete (ej. no importar `drop_none` de higyrus — usar la copia local `market_data_client._params`) |
| **Dual sync/async**: todo fix de lógica se espeja en `client.py` y `aio.py` del mismo paquete | D-17. La duplicación es deliberada (codegen shelved permanentemente en Phase 18 — SPIKE-006 NO-GO firmado) |
| Credenciales en `.env`; nunca commitear ni exponer en logs/reportes/tests | Los métodos nuevos no deben loguear payloads; el `__repr__` redactor y el `RedactingFilter` existentes no se tocan |
| `from __future__ import annotations` obligatorio en todo módulo | Ya presente en todos los archivos a tocar |
| GSD workflow enforcement: nada de edits directos fuera de un comando GSD | Aplica a la ejecución, no al plan |
| Modelos `@dataclass(frozen=True, slots=True)`; response-models vía `SafeModel.from_api`, **nunca** construcción directa | D-08: los tres nuevos son request-models → frozen dataclass + `to_dict()`, **NO** `SafeModel` |
| `__all__` explícito + `__version__`; re-exports desde `client`/`exceptions`/`models` | D-17 |
| Nombres de campo de modelos siguen el wire verbatim | Los tres nuevos son snake_case en el wire (OpenAPI verificada) → sin excepción `N815` |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Refuse-by-default mutation gate (flag + host exacto) | Stateful shell (`client.py` / `aio.py`) — **YA EXISTE, sin cambios** | `_ClientState` (storage) | Phase 25 D-05: la política necesita estado vivo; `_core` es IO-free. Phase 26 sólo **consume** |
| No-retry de operaciones no idempotentes | Transport (`_transport.py` / `_atransport.py`) — **YA EXISTE** | Builder (`_core.py` setea `idempotent`) | El gate es `request.extensions["idempotent"]`, leído en la 1ª línea de `handle_request`. `POST /calendar/holidays` es el primer consumidor `False` del paquete |
| Construcción del spec de request | Pure builders (`_core.py`) — 5 nuevos | — | Builders puros `state → RequestSpec`; hacen `del state` (el payload llega como `json_body`) |
| Serialización del body (modelo → JSON) | Request models (`models.py`, `to_dict()`) — 3 nuevos | `_params.drop_none` | Frozen dataclasses serializan HACIA AFUERA; distinto de `SafeModel` (deserializa HACIA ADENTRO) |
| Bound 1–500 de `HolidaysIn.days` | Request model (`HolidaysIn.__post_init__`) | — | `ValueError` client-side antes de cualquier dispatch, independiente del entry point |
| Parsing tolerante de respuesta (config trio) | `_core.parse_calendar_config_response` — **REUSO verbatim** | `CalendarConfig.from_api` | D-05; ya reconciliado contra el wire real de develop |
| Parsing tolerante de respuesta (holiday pair) | Pure parser **NUEVO** en `_core.py` | — | D-06/D-07. `parse_health_response` **no** es tolerante (ver Pitfall 2) |
| Mapeo de errores (401/403/429/422/4xx → tipado) | `_core.raise_for_response` — **sin cambios** | — | `422` ya cae en `if resp.is_error → MarketDataAPIError` |
| Paridad de superficie pública | `__init__.py` / `models.py` / `_core.py` `__all__` | `tests/test_public_surface_market_data.py` (extender) | Los nets cross-package **excluyen** este paquete (verificado en Phase 25 y revalidado abajo) |

## Standard Stack

Sin dependencias externas nuevas. La fase es una extensión aditiva pura del paquete existente
usando sólo stdlib + el stack ya vendorizado.

### Core (ya presente — reusar, no agregar)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `httpx` | **0.28.1** (pineado en `uv.lock`; declarado `>=0.27`) | transporte sync + async | Único transporte del monorepo; `build_request(..., json=...)` ya usado para bodies POST/PATCH [VERIFIED: `uv.lock` + `httpx.__version__` ejecutado esta sesión] |
| `tenacity` | (vía `_transport`/`_atransport`) | retry acotado + full-jitter backoff | Maneja `RetryTransport`; el gate `idempotent` lo corto-circuita [VERIFIED: `_transport.py:159`] |
| `python-dotenv` | >=1.0 | carga de `.env` al import | `load_dotenv()` a nivel módulo en `client.py`/`aio.py` [VERIFIED: source] |
| `pytest-httpx` | **0.36.2** (declarado `>=0.34`) | mocking HTTP en tests | Soporta `@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)`, necesario para el test no-retry de D-15 [VERIFIED: ejecutado esta sesión] |
| `pytest-asyncio` | >=0.24 (`asyncio_mode="auto"`) | tests async sin decorador | Los tests async del paquete son `async def` planos [VERIFIED: `pyproject.toml` + `test_symbols_write_async.py`] |

**Installation:** ninguna. `uv sync --all-packages --all-extras --dev --frozen` ya provee todo.

**Version verification:** N/A — no se agregan paquetes.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `json_body=None` en los DELETE | `json_body={}` | **RECHAZADO — verificado que rompe**: httpx 0.28.1 con `json={}` emite `b"{}"` + `Content-Type: application/json`, contradiciendo D-02. `None` es obligatorio |
| Reusar `parse_health_response` para el par holiday | Parser nuevo con collection-guard | **Parser nuevo obligatorio**: `parse_health_response` levanta `JSONDecodeError` en body vacío (ver Pitfall 2) |
| `confirm` como kwarg del método | `confirm` como campo del modelo (D-09) | Locked D-09. Además el campo es lo que declara la OpenAPI (`MarketHoursIn.confirm`), no un query param — **verificado en vivo** |

## Package Legitimacy Audit

**No aplica.** Phase 26 no instala ningún paquete externo. Todo el código nuevo usa
stdlib + dependencias ya presentes en `uv.lock` (verificado: `uv lock --check` es un gate de CI
existente y `uv.lock` no requiere cambios).

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Contrato de la API en vivo (verificado esta sesión)

`GET https://market-data-develop.bbsa.com.ar/api/openapi.json` fue **re-fetcheado y parseado
esta sesión** (2026-07-31). Todas las claims de D-03/D-09/D-10/D-12 quedan confirmadas.
[VERIFIED: fetch directo de la OpenAPI en vivo]

### Endpoints

| Method | Path | Request body | Path/query params | Respuestas declaradas |
|--------|------|--------------|-------------------|------------------------|
| PUT | `/calendar/config` | `MarketHoursIn` (required) | — | `200` bare `object` (`additionalProperties: true`), `422` `HTTPValidationError` |
| DELETE | `/calendar/config` | — | — | `200` bare `object`. **Sin `422` declarado** |
| POST | `/calendar/config/preview` | `MarketHoursIn` (required) | — | `200` bare `object`, `422` |
| POST | `/calendar/holidays` | `HolidaysIn` (required) | — | `200` bare `object`, `422` |
| DELETE | `/calendar/holidays/{day}` | — | `day` path, `{"type":"string","format":"date"}`, required | `200` bare `object`, `422` |

**Ninguno de los cinco declara un schema de respuesta** — los cinco `200` son `object` con
`additionalProperties: true`. Esto es exactamente lo que justifica D-05/D-06 como "apuestas
basadas en evidencia" y D-07 (parsers tolerantes) como hedge hasta Phase 27.

### Schemas (verbatim de la OpenAPI en vivo)

`MarketHoursIn` — `required: ["open_time", "close_time", "timezone"]`
| Campo | Tipo wire | Default | Bound declarado |
|-------|-----------|---------|-----------------|
| `open_time` | `string` / `format: time` (ej. `"10:00"`) | — (required) | — |
| `close_time` | `string` / `format: time` (ej. `"17:00"`) | — (required) | — |
| `timezone` | `string` (ej. `"America/Argentina/Buenos_Aires"`) | — (required) | `minLength 1`, `maxLength 64` |
| `pre_open_minutes` | `integer` | `10` | `0 ≤ x ≤ 120` |
| `enabled` | `boolean` | `true` | — |
| `updated_by` | `string` | `""` | `maxLength 200` |
| `confirm` | `boolean` | `false` | — |

Descripción literal de `confirm` en la OpenAPI: *"Required when the change produces warnings.
See POST /calendar/config/preview."* Y la descripción del schema: *"`confirm` is the second
opinion, not a force flag: it is required only when the window is legal but suspicious
(see `check_hours`). Anything genuinely impossible is a 422 that no amount of confirming gets
past."* — corrobora literalmente el bloque `<specifics>` de CONTEXT.md.

`HolidayIn` — `required: ["day"]`
| Campo | Tipo wire | Default | Nota |
|-------|-----------|---------|------|
| `day` | `string` / `format: date` | — (required) | ISO `YYYY-MM-DD` |
| `closed` | `boolean` | `true` | *"false = open with custom hours"* |
| `open_time` | `string \| null` / `format: time` | (opcional, sin `default` declarado) | *"null = configured default"* |
| `close_time` | `string \| null` / `format: time` | (opcional, sin `default` declarado) | *"null = configured default"* |
| `description` | `string` | `""` | `maxLength 500` |

`HolidaysIn` — `required: ["days"]`; `days: {type: array, items: $ref HolidayIn, minItems: 1, maxItems: 500}`
→ **D-12 confirmado**: el bound 1–500 existe en el contrato en vivo y el plan fuente lo omitió.

**Matiz sobre D-11:** la OpenAPI describe `null` para `open_time`/`close_time` como *"configured
default"*. Dropear la clave (lo que hace `drop_none`) hace que Pydantic use el default del campo,
que también es `None` → mismo efecto semántico. Es un razonamiento sólido pero **no probado
contra el servidor** — queda como assumption A3 y ya está en Deferred para Phase 27.

## Architecture Patterns

### System Architecture Diagram

```
  Consumer code
      │  set_calendar_config(MarketHoursIn(...))   preview_calendar_config(MarketHoursIn(...))
      │  delete_calendar_config()                  add_holidays(HolidaysIn([...]))
      │                                            delete_holiday("2026-12-25")
      ▼
  ┌──────────────── Stateful shell (client.py / aio.py) ── 5 métodos nuevos × 2 shells ───────────┐
  │                                                                                                │
  │  [0] (HolidaysIn) __post_init__ ya levantó ValueError si len(days) ∉ [1,500]   (D-12)          │
  │                                                                                                │
  │  [1] self._ensure_mutation_allowed()   ◄── LITERAL PRIMERA SENTENCIA (D-14)                    │
  │        ├─ not state.mutating_allowed          ──────────► MarketDataMutationNotAllowedError    │
  │        └─ urlsplit(base_url).hostname != expected_host ─► MarketDataMutationNotAllowedError    │
  │             (CERO http.build_request, CERO _ensure_token, CERO round-trip Auth0)               │
  │             ⚠ preview_calendar_config TAMBIÉN pasa por acá (es POST) — D-14, sin carve-out     │
  │                                                                                                │
  │  [2] spec = _core.build_<x>_request(self._state, <model>.to_dict() | day | ∅)  ── builder puro │
  │          RequestSpec(method=PUT|DELETE|POST, path, json_body=dict|None,                        │
  │                      authenticated=True, idempotent=<per D-04>, endpoint_name)                 │
  │                                                                                                │
  │  [3] resp = self._request(spec)        ── dispatch compartido read+write (SIN cambios)         │
  │        ├─ authenticated → _ensure_token() → header Authorization: Bearer                       │
  │        ├─ http.build_request(method, base_url+path, params=None, json=spec.json_body, headers) │
  │        │     └─ json=None ⇒ content=b"" y SIN Content-Type   [VERIFICADO httpx 0.28.1]         │
  │        ├─ req.extensions["idempotent"] = spec.idempotent                                       │
  │        ├─ req.extensions["max_attempts"] = self._max_retries + 1                               │
  │        └─ http.send(req) ──► RetryTransport.handle_request                                     │
  │                                 └─ if not extensions["idempotent"]: return super()  ◄── 1 req  │
  │                                    [VERIFICADO: 3×503 con idempotent=False ⇒ 1 request, 0 sleep]│
  │                                                                                                │
  │  [4a] config trio  → _core.parse_calendar_config_response(resp) → CalendarConfig   (D-05 reuso)│
  │  [4b] holiday pair → _core.parse_<nuevo>_response(resp)         → dict[str, Any]   (D-06 nuevo)│
  │          ambos: resp.read() → raise_for_response() → decode tolerante                          │
  │          raise_for_response: 401/403→Auth, 429→RateLimit, 422/4xx→APIError  (sin cambios)      │
  └────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure (archivos tocados — todos existentes)

```
packages/market-data-client/
├── src/market_data_client/
│   ├── _core.py       # + 5 builders + 1 parser tolerante nuevo; + 6 entradas en __all__
│   ├── models.py      # + MarketHoursIn/HolidayIn/HolidaysIn; + import de _params; + 3 en __all__
│   ├── client.py      # + 5 métodos gated + 5 shims module-level; + imports de los 3 modelos
│   ├── aio.py         # espejo idéntico (5 métodos async + 5 shims async)
│   └── __init__.py    # + 3 modelos + 5 shims sync en imports y __all__ (8 entradas)
└── tests/
    ├── test_calendar_write.py         # NUEVO (sync)   — espeja test_symbols_write.py
    ├── test_calendar_write_async.py   # NUEVO (async)  — espeja test_symbols_write_async.py
    ├── test_core.py                   # EXTENDER — 5 specs de builder + state-independence
    ├── test_models.py                 # EXTENDER — to_dict()/defaults/drop_none/bound 1-500
    └── test_public_surface_market_data.py  # EXTENDER — _NEW_PUBLIC_NAMES + _MUTATION_METHODS
```

**Archivos que NO se tocan:** `_state.py`, `exceptions.py`, `_transport.py`, `_atransport.py`,
`_params.py`, `_logging.py`, `conftest.py` (el reset del gate ya está ahí de Phase 25),
`pyproject.toml`, `uv.lock`, `.github/workflows/ci.yml`.

### Pattern 1: Builder puro con body ya serializado (template: `build_create_symbol_request`)

**What:** builder puro `_core` que hace `del state` y recibe el dict ya serializado.
**When to use:** `build_set_calendar_config_request`, `build_preview_calendar_config_request`,
`build_add_holidays_request`.
**Example (código shipeado, verbatim):**
```python
# Source: packages/market-data-client/src/market_data_client/_core.py:394-409
def build_create_symbol_request(state: _ClientState, json_body: dict[str, Any]) -> RequestSpec:
    """Pure: build spec for ``POST /symbols`` (single symbol create, MUT-MD-01)."""
    del state  # state-independent (payload comes via json_body)
    return RequestSpec(
        method="POST",
        path="/symbols",
        json_body=json_body,
        idempotent=True,
        endpoint_name="create_symbol",
        authenticated=True,
    )
```
Firmas concretas propuestas para los tres análogos (naming = Claude's Discretion, paths y
`idempotent` LOCKED por D-01/D-04):
```python
def build_set_calendar_config_request(state: _ClientState, json_body: dict[str, Any]) -> RequestSpec
#   method="PUT",  path="/calendar/config",          idempotent=True,  endpoint_name="set_calendar_config"
def build_preview_calendar_config_request(state: _ClientState, json_body: dict[str, Any]) -> RequestSpec
#   method="POST", path="/calendar/config/preview",  idempotent=True,  endpoint_name="preview_calendar_config"
def build_add_holidays_request(state: _ClientState, json_body: dict[str, Any]) -> RequestSpec
#   method="POST", path="/calendar/holidays",        idempotent=False, endpoint_name="add_holidays"  ◄── ÚNICO False
```

### Pattern 2: Builder zero-kwarg sin body (template: `build_segments_request`)

**What:** builder sin kwargs de filtro; `params` y `json_body` quedan en su default `None`.
**When to use:** `build_delete_calendar_config_request`.
**Example (código shipeado, verbatim):**
```python
# Source: packages/market-data-client/src/market_data_client/_core.py:502-515
def build_segments_request(state: _ClientState) -> RequestSpec:
    """Pure: build spec for ``GET /instruments/segments`` (D-01, no params)."""
    del state  # state-independent
    return RequestSpec(
        method="GET",
        path="/instruments/segments",
        idempotent=True,
        endpoint_name="segments",
        authenticated=True,
    )
```
Análogo: `method="DELETE"`, `path="/calendar/config"`, `idempotent=True`,
`endpoint_name="delete_calendar_config"`. **`json_body` se OMITE** (default `None`) — nunca `{}`.

### Pattern 3: Builder con path-param (template: `build_update_symbol_request`)

**What:** interpola un identificador en el path; el resto igual.
**When to use:** `build_delete_holiday_request`.
**Example (código shipeado, verbatim):**
```python
# Source: packages/market-data-client/src/market_data_client/_core.py:429-447
def build_update_symbol_request(
    state: _ClientState, symbol_id: str, json_body: dict[str, Any]
) -> RequestSpec:
    del state  # state-independent (payload comes via json_body)
    return RequestSpec(
        method="PATCH",
        path=f"/symbols/{symbol_id}",
        json_body=json_body,
        idempotent=True,
        endpoint_name="update_symbol",
        authenticated=True,
    )
```
Análogo: `build_delete_holiday_request(state: _ClientState, day: str) -> RequestSpec` con
`method="DELETE"`, `path=f"/calendar/holidays/{day}"`, **sin `json_body`**, `idempotent=True`,
`endpoint_name="delete_holiday"`. Ver Open Question 1 sobre path-safety de `day`.

### Pattern 4: Request-model frozen con `to_dict()` (template: `NewSymbol` / `NewSymbols`)

**What:** `@dataclass(frozen=True, slots=True)`, **NO** `SafeModel`; serializa hacia afuera.
**Example (código shipeado, verbatim):**
```python
# Source: packages/market-data-client/src/market_data_client/models.py:197-237
@dataclass(frozen=True, slots=True)
class NewSymbol:
    symbol: str
    market_id: str = "ROFX"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a wire dict — both keys always present (D-10)."""
        return {"symbol": self.symbol, "market_id": self.market_id}


@dataclass(frozen=True, slots=True)
class NewSymbols:
    symbols: list[NewSymbol]

    def __post_init__(self) -> None:
        """Enforce the 1-500 batch-size bound (D-11) — plain ValueError."""
        if not 1 <= len(self.symbols) <= 500:
            raise ValueError(f"NewSymbols requires 1-500 symbols, got {len(self.symbols)}")

    def to_dict(self) -> dict[str, Any]:
        """Serialize to ``{"symbols": [each element's to_dict()]}``."""
        return {"symbols": [s.to_dict() for s in self.symbols]}
```
**Delta clave D-11 vs. Phase 25:** `NewSymbol.to_dict()` construye el dict a mano y **NO** pasa
por `drop_none` — `models.py` hoy **no importa `_params`**. Phase 26 introduce ese import por
primera vez. Los tres modelos nuevos:
```python
from market_data_client import _params   # NUEVO import en models.py (sin ciclo: _params no importa nada local)

@dataclass(frozen=True, slots=True)
class MarketHoursIn:
    open_time: str
    close_time: str
    timezone: str
    pre_open_minutes: int = 10
    enabled: bool = True
    updated_by: str = ""
    confirm: bool = False          # D-09 — guardrail del servidor, default False

    def to_dict(self) -> dict[str, Any]:
        # drop_none es no-op acá (no hay campos nullable) — se rutea por consistencia (D-11)
        return _params.drop_none({
            "open_time": self.open_time, "close_time": self.close_time,
            "timezone": self.timezone, "pre_open_minutes": self.pre_open_minutes,
            "enabled": self.enabled, "updated_by": self.updated_by, "confirm": self.confirm,
        })

@dataclass(frozen=True, slots=True)
class HolidayIn:
    day: str
    closed: bool = True
    open_time: str | None = None    # drop_none los ELIMINA cuando son None
    close_time: str | None = None
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _params.drop_none({
            "day": self.day, "closed": self.closed, "open_time": self.open_time,
            "close_time": self.close_time, "description": self.description,
        })

@dataclass(frozen=True, slots=True)
class HolidaysIn:
    days: list[HolidayIn]

    def __post_init__(self) -> None:
        if not 1 <= len(self.days) <= 500:
            raise ValueError(f"HolidaysIn requires 1-500 days, got {len(self.days)}")

    def to_dict(self) -> dict[str, Any]:
        return {"days": [d.to_dict() for d in self.days]}
```
Efecto de `drop_none` (verificado en `_params.py:22-28`: preserva falsy-pero-no-`None`):
`HolidayIn("2026-12-25").to_dict() == {"day": "2026-12-25", "closed": True, "description": ""}`
— `closed=True` y `description=""` **se emiten**, `open_time`/`close_time` **desaparecen**.

### Pattern 5: Parser single-object tolerante (reuso verbatim — D-05)

```python
# Source: packages/market-data-client/src/market_data_client/_core.py:733-746
def parse_calendar_config_response(resp: httpx.Response) -> CalendarConfig:
    resp.read()
    raise_for_response(resp)
    if not resp.content:
        return CalendarConfig.from_api(None)
    raw = resp.json()
    return CalendarConfig.from_api(raw)
```
**Verificado esta sesión:** body `b""` → `CalendarConfig` con zeros tipados; body `b"null"` →
idéntico. Los tres métodos del config trio lo llaman sin cambios.

### Pattern 6: Parser passthrough tolerante — **NUEVO, no reuso** (D-06/D-07)

`parse_health_response` **no sirve tal cual**. Comportamiento medido esta sesión:

| body | `parse_health_response` |
|------|-------------------------|
| `b""` | **RAISES `json.JSONDecodeError`** |
| `b"null"` | retorna `None` (miente vs. `-> dict[str, Any]`) |
| `b"[]"` | retorna `[]` (miente vs. `-> dict[str, Any]`) |
| `b'{"ok":true}'` | `{'ok': True}` ✓ |

El parser nuevo debe combinar el orden body-consume-then-raise con el collection-guard que ya
usan `parse_market_data_response` / `parse_calendar_config_response`:
```python
def parse_calendar_write_response(resp: httpx.Response) -> dict[str, Any]:
    """Pure: parse a calendar-write 200 → dict passthrough tolerante (D-06/D-07)."""
    resp.read()
    raise_for_response(resp)
    if not resp.content:
        return {}
    raw = resp.json()
    if not isinstance(raw, dict):
        return {}
    return raw
```
Uno solo alcanza para `add_holidays` y `delete_holiday` (la discreción de CONTEXT.md sobre
"uno o dos" se resuelve mejor con **uno**: mismo contrato, misma tolerancia, menos superficie).

### Pattern 7: Método gated en el shell (template shipeado — gate PRIMERO)

```python
# Source: packages/market-data-client/src/market_data_client/client.py:539-552
def create_symbol(self, new_symbol: NewSymbol) -> list[Symbol]:
    self._ensure_mutation_allowed()          # ◄── LITERAL primera sentencia (D-14)
    spec = _core.build_create_symbol_request(self._state, new_symbol.to_dict())
    resp = self._request(spec)
    return _core.parse_symbols_response(resp)
```
```python
# Source: packages/market-data-client/src/market_data_client/aio.py:552-563
async def create_symbol(self, new_symbol: NewSymbol) -> list[Symbol]:
    self._ensure_mutation_allowed()          # ◄── NO-awaited, primera sentencia
    spec = _core.build_create_symbol_request(self._state, new_symbol.to_dict())
    resp = await self._request(spec)
    return _core.parse_symbols_response(resp)
```
Las cinco firmas públicas (nombres LOCKED por DM/ROADMAP):
| Método | Firma sync | Retorno |
|--------|-----------|---------|
| `set_calendar_config` | `(self, config: MarketHoursIn)` | `CalendarConfig` |
| `delete_calendar_config` | `(self)` | `CalendarConfig` |
| `preview_calendar_config` | `(self, config: MarketHoursIn)` | `CalendarConfig` |
| `add_holidays` | `(self, holidays: HolidaysIn)` | `dict[str, Any]` |
| `delete_holiday` | `(self, day: str)` | `dict[str, Any]` |

### Pattern 8: Shims module-level (templates shipeados)

```python
# Source: client.py:764-776 (sync)              # Source: aio.py:773-785 (async)
def create_symbol(new_symbol: NewSymbol) -> list[Symbol]:
    """Top-level shim: delega al default Client (gated)."""
    return _get_default().create_symbol(new_symbol)

async def create_symbol(new_symbol: NewSymbol) -> list[Symbol]:
    """Shim async top-level: delega al default AsyncClient (gated)."""
    return await _get_default().create_symbol(new_symbol)
```

### El estado exacto de `RequestSpec` (D-02 — sin cambio estructural)

```python
# Source: packages/market-data-client/src/market_data_client/_core.py:106-130
@dataclass(frozen=True, slots=True)
class RequestSpec:
    method: str
    path: str
    params: dict[str, Any] | None = None
    headers: dict[str, str] | None = None
    json_body: dict[str, Any] | None = None
    data: dict[str, Any] | None = None
    idempotent: bool = False          # ◄── default False; los builders lo setean explícito
    endpoint_name: str = ""
    authenticated: bool = True
```
Nota: `idempotent` **ya defaultea a `False`**, así que `build_add_holidays_request` podría
omitirlo. **No lo omitas** — seteá `idempotent=False` explícito: es una decisión load-bearing
(D-04) y el default implícito la haría invisible en el diff y en el code review.

### Inventario de builders/parsers actuales de `_core.py` (para especificar sin ambigüedad)

| Símbolo | Firma actual | Rol para Phase 26 |
|---------|--------------|-------------------|
| `RequestSpec` | ver arriba | sin cambios (D-02) |
| `raise_for_response` | `(resp: httpx.Response) -> None` | reuso; 422 → `MarketDataAPIError` |
| `build_create_symbol_request` | `(state, json_body: dict[str, Any]) -> RequestSpec` | **template body** |
| `build_create_symbols_request` | `(state, json_body: dict[str, Any]) -> RequestSpec` | template body |
| `build_update_symbol_request` | `(state, symbol_id: str, json_body: dict[str, Any]) -> RequestSpec` | **template path-param** |
| `build_segments_request` | `(state) -> RequestSpec` | **template zero-kwarg** |
| `build_calendar_config_request` | `(state) -> RequestSpec` (GET) | vecino; no tocar |
| `parse_calendar_config_response` | `(resp) -> CalendarConfig` | **reuso verbatim (D-05)** |
| `parse_health_response` | `(resp) -> dict[str, Any]` | ⚠ NO tolerante — no reusar (D-06) |
| `parse_calendar_response` | `(resp) -> list[CalendarDay]` | ⛔ **ROTO** — no reusar (D-16) |
| `_core.__all__` | lista ordenada de 28 nombres | +5 builders +1 parser, **mantener orden alfabético** (ruff `RUF022`) |

### Anti-Patterns to Avoid

- **`json_body={}` en los DELETE:** emite `b"{}"` + `Content-Type: application/json`. Verificado.
  Usar `json_body=None` (o simplemente omitir el kwarg).
- **Reusar `parse_health_response` para el par holiday:** levanta en body vacío y su anotación
  miente para `null`/`[]`. Escribir el parser tolerante nuevo.
- **Reusar `parse_calendar_response` o tipar contra `CalendarDay`:** el par está roto contra el
  wire real (D-16) y los mocks encodearían la misma forma equivocada, dejando los tests verdes
  y el bug latente hasta Phase 27 — donde arreglarlo sería un cambio de tipo de retorno público
  justo antes del publish.
- **Carve-out del gate para `preview`:** crearía un segundo camino, más débil, a la superficie de
  mutación. D-14: pasa por el gate igual; la excepción read-safe se **documenta** en el docstring.
- **`_ensure_token()` / `_core.build_*` antes del gate:** rompe la garantía cero-round-trip.
  El gate es la primera sentencia, literal.
- **Tocar el gate, `_ClientState`, las excepciones o el transporte:** Phase 26 los **consume**.
  Cero cambios ahí (CONTEXT.md `<code_context>` "Integration Points").
- **Error tipado `MarketData*` para el bound 1–500:** D-12 reserva esa jerarquía para errores de
  contrato del servidor; el bound levanta `ValueError` pelado.
- **Validar `HH:MM` client-side:** D-13. La OpenAPI usa `format: time`, que admite `"10:00:00"`;
  un regex daría falsos negativos.
- **Importar `drop_none` de `higyrus_client`:** prohibido por CLAUDE.md (no-shared-internals).
  Usar `market_data_client._params.drop_none`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| No-retry de ops no idempotentes | Un filtro de retry por nombre de método | `request.extensions["idempotent"]` ya honrado por `RetryTransport.handle_request` | Ya implementado + medido: 3×503 con `False` ⇒ 1 request, 0 sleeps |
| Body JSON de PUT/POST | Encoder de body propio | `http.build_request(..., json=spec.json_body)` (ya en ambos `_request`) | httpx maneja `Content-Type` y encoding; ambos shells ya lo threadean |
| DELETE sin body | `headers={"Content-Length": "0"}` u otro workaround | `json_body=None` | httpx 0.28.1 ya emite `b""` sin `Content-Type` (verificado) |
| Mapeo `422`/4xx → excepción | Manejo de status en los métodos nuevos | `_core.raise_for_response` | `422` ya cae en `if resp.is_error → MarketDataAPIError` (D-13) |
| Dropeo de opcionales `None` | Comprensiones `if x is not None` a mano en cada `to_dict` | `_params.drop_none` | Ya existe, preserva falsy legítimos (`False`/`0`/`""`), y es literalmente el criterio 3 del ROADMAP |
| Gate de mutación | Nuevo chequeo / nueva excepción | `self._ensure_mutation_allowed()` existente | Construido y AST-verificado en Phase 25; Phase 26 no lo toca |
| Reset del estado del gate entre tests | Fixture nueva | `tests/conftest.py` autouse (`_configure_sync`/`_configure_async`) ya resetea `mutating_allowed=False` + `expected_host` | Extendido en Phase 25 (Pitfall 6); ya cubre los tests nuevos |

**Key insight:** el 100% de la infraestructura que Phase 26 necesita ya existe y está probada en
el mismo paquete. La única lógica genuinamente nueva son ~15 líneas: el parser passthrough
tolerante y los tres `to_dict()`. Todo lo demás es composición de piezas ya verdes.

## Common Pitfalls

### Pitfall 1: `json_body={}` en un builder DELETE
**What goes wrong:** el request sale con `content=b"{}"` y `Content-Type: application/json`,
contradiciendo D-02; el servidor puede rechazar un DELETE con body o interpretarlo mal.
**Why it happens:** los otros cuatro builders reciben un dict, y por simetría uno tiende a
pasar `{}` "vacío".
**How to avoid:** omitir el kwarg `json_body` (default `None`) en los dos builders DELETE.
**Warning signs:** un test que asserta `req.content == b""` falla, o
`"content-type" not in req.headers` falla. [VERIFIED: probado con httpx 0.28.1]

### Pitfall 2: reusar `parse_health_response` para el par holiday
**What goes wrong:** un `200` con body vacío (plausible para un `DELETE`) levanta
`json.JSONDecodeError` — un error crudo de stdlib, fuera de la jerarquía `MarketDataError` — y
un body `null` retorna `None` con anotación `dict[str, Any]`, que mypy no atrapa porque
`resp.json()` es `Any`.
**Why it happens:** D-06 dice "en el estilo de `parse_health_response`", y "estilo" se confunde
con "reuso".
**How to avoid:** función nueva con `if not resp.content: return {}` + guard `isinstance(raw, dict)`.
**Warning signs:** test con `httpx_mock.add_response(status_code=200)` (sin `json=`) que crashea
en vez de retornar `{}`. [VERIFIED: medido esta sesión]

### Pitfall 3: heredar el bug de `get_calendar` tipando contra `CalendarDay`
**What goes wrong:** `add_holidays`/`delete_holiday` retornarían objetos `CalendarDay`
silenciosamente vacíos contra el servidor real, con los tests mockeados verdes porque los mocks
encodean la misma forma equivocada. Aparece recién en Phase 27, donde arreglarlo es un cambio
de tipo de retorno público justo antes del publish.
**Why it happens:** `CalendarDay` "suena" como el modelo natural para un endpoint de feriados.
**How to avoid:** D-06 — `dict[str, Any]`. Nunca importar `CalendarDay` ni
`parse_calendar_response` en el código nuevo.
**Warning signs:** cualquier aparición de `CalendarDay` en el diff de Phase 26.
[VERIFIED: `parse_calendar_response(envelope)` → 4 `CalendarDay` all-default, ejecutado]

### Pitfall 4: el test no-retry falla por `assert_all_responses_were_requested`
**What goes wrong:** el test de D-15 registra ≥2 respuestas 503 y espera 1 sólo request;
pytest-httpx por default exige que **todas** las respuestas registradas se consuman → el test
falla en teardown con un error que no tiene nada que ver con el retry.
**Why it happens:** default de pytest-httpx `assert_all_responses_were_requested=True`.
**How to avoid:** decorar con `@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)`
— exactamente lo que hace `packages/iol-client/tests/test_transport.py:41`.
**Warning signs:** el assert `len(get_requests()) == 1` pasa pero el test igual falla.
[VERIFIED: reproducido y resuelto esta sesión]

### Pitfall 5: el control positivo `idempotent=True` duerme de verdad
**What goes wrong:** un test que ejercita 3×503 con `idempotent=True` duerme ~4.4 s reales
(backoff full-jitter) — medido: `sleeps == [1.72, 2.68]`. La suite del paquete corre hoy en
0.25 s; un solo test así la multiplicaría por ~20 y rompería el presupuesto de latencia (<20 s).
**Why it happens:** tenacity duerme entre intentos vía `time.sleep`.
**How to avoid:** `monkeypatch.setattr(time, "sleep", lambda s: sleeps.append(s))` — el patrón de
`tests/test_transport.py:98`. Bonus: `sleeps` se vuelve un assert extra
(`assert sleeps == []` en el caso no-idempotente).
**Warning signs:** la suite del paquete pasa de <1 s a varios segundos.

### Pitfall 6: `models.py` importando `_params` — orden de imports y ciclos
**What goes wrong:** `models.py` hoy no importa nada del paquete. Agregar
`from market_data_client import _params` es el primer import intra-paquete de ese módulo.
**Why it happens:** D-11 exige rutear `to_dict()` por `drop_none`.
**How to avoid:** verificado que **no hay ciclo** — `_params.py` sólo importa `typing`;
la cadena queda `_core → models → _params` y `_core → _params`. Ruff `I` (isort) ordena el
import después de `from dataclasses ...`/`from typing ...`. `market_data_client` **no está** en
`[tool.importlinter] root_packages`, así que ningún contrato de boundary aplica a este paquete.
**Warning signs:** `ruff check` reporta `I001`; `python -c "import market_data_client"` falla.

### Pitfall 7: contaminación cross-test del singleton (ya mitigada, no regresionar)
**What goes wrong:** un test que abre el gate (`configure(mutating_allowed=True, ...)`)
contamina al siguiente si el teardown no lo resetea.
**Why it happens:** `_default_client` / `_default_async_client` son singletons de proceso.
**How to avoid:** el `conftest.py` autouse **ya** resetea `mutating_allowed=False` +
`expected_host="market-data-develop.bbsa.com.ar"` en ambas superficies (líneas 47-55 y 72-80).
Los tests nuevos deben usar el helper `_open_gate()` (patrón de `test_symbols_write.py:35-37`)
y **no** agregar fixtures nuevas de reset.
**Warning signs:** fallas dependientes del orden de los tests.

### Pitfall 8: `__all__` desordenado
**What goes wrong:** `ruff check` con `RUF` reporta `RUF022` (`__all__` no ordenado).
**Why it happens:** se agregan nombres al final de la lista.
**How to avoid:** insertar en orden alfabético en las cuatro listas
(`_core.__all__`, `models.__all__`, `__init__.__all__`) — notar que en `__init__.__all__` las
clases (PascalCase) van antes que las funciones (snake_case) por orden ASCII, tal como está hoy.
**Warning signs:** gate `ruff check` rojo.

## Code Examples

### Test de body en el wire (template shipeado)
```python
# Source: packages/market-data-client/tests/test_symbols_write.py:45-61
def test_create_symbol_sends_bearer_and_body(httpx_mock: HTTPXMock) -> None:
    _open_gate()
    httpx_mock.add_response(method="POST", status_code=201,
                            json=[{"symbol": "DLR/DIC26", "marketId": "ROFX"}])
    result = market_data_client.client._get_default().create_symbol(NewSymbol("DLR/DIC26"))
    assert isinstance(result, list)
    req = httpx_mock.get_requests()[0]
    assert req.method == "POST"
    assert req.url.path == "/api/symbols"
    assert req.headers["Authorization"] == "Bearer test-token"
    assert _json.loads(req.content) == {"symbol": "DLR/DIC26", "market_id": "ROFX"}
```
Equivalente calendar: mockear `PUT` 200 con el shape de `get-calendar-config.json`, llamar
`set_calendar_config(MarketHoursIn("10:00", "17:00", "America/Argentina/Buenos_Aires"))`, y
assertar `req.url.path == "/api/calendar/config"` +
`_json.loads(req.content) == {"open_time": "10:00", "close_time": "17:00", "timezone": "America/Argentina/Buenos_Aires", "pre_open_minutes": 10, "enabled": True, "updated_by": "", "confirm": False}`
— este assert **es** el criterio 2 del ROADMAP (`confirm` expuesto, default `False`).

### Test del wire DELETE sin body (probado esta sesión, no hipotético)
```python
def test_delete_holiday_sends_no_body(httpx_mock: HTTPXMock) -> None:
    _open_gate()
    httpx_mock.add_response(method="DELETE", status_code=200, json={"deleted": True})
    out = market_data_client.client._get_default().delete_holiday("2026-12-25")
    req = httpx_mock.get_requests()[0]
    assert req.method == "DELETE"
    assert req.url.path == "/api/calendar/holidays/2026-12-25"
    assert req.content == b""                       # D-02 — sin body
    assert "content-type" not in req.headers        # D-02 — sin Content-Type
    assert out == {"deleted": True}
```
[VERIFIED: este assert exacto pasó contra `Client._request` con httpx 0.28.1 esta sesión]

### Test no-retry a nivel dispatch (D-15 — el primero del paquete; probado esta sesión)
```python
@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
def test_add_holidays_never_retries_on_503(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """idempotent=False ⇒ EXACTAMENTE 1 request saliente y 0 sleeps (DM-03 / D-04)."""
    sleeps: list[float] = []
    monkeypatch.setattr(time, "sleep", lambda s: sleeps.append(s))
    _open_gate()
    for _ in range(3):
        httpx_mock.add_response(method="POST", status_code=503)

    with pytest.raises(MarketDataAPIError):
        market_data_client.client._get_default().add_holidays(
            HolidaysIn([HolidayIn("2026-12-25")])
        )

    assert len(httpx_mock.get_requests()) == 1
    assert sleeps == []
```
Control positivo contrastante (opcional, mismo archivo):
```python
@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
def test_delete_holiday_retries_on_503(
    httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Contraste: idempotent=True ⇒ 3 requests (max_retries default 2 → max_attempts 3)."""
    monkeypatch.setattr(time, "sleep", lambda s: None)
    _open_gate()
    for _ in range(3):
        httpx_mock.add_response(method="DELETE", status_code=503)
    with pytest.raises(MarketDataAPIError):
        market_data_client.client._get_default().delete_holiday("2026-12-25")
    assert len(httpx_mock.get_requests()) == 3
```
[VERIFIED: ambos comportamientos medidos esta sesión — 1 request/0 sleeps vs. 3 requests/2 sleeps]

### Test de builder (template shipeado)
```python
# Source: packages/market-data-client/tests/test_core.py:323-332
def test_build_create_symbol_request_posts_serialized_body() -> None:
    state = _ClientState()
    body = {"symbol": "DLR/DIC26", "market_id": "ROFX"}
    spec = _core.build_create_symbol_request(state, body)
    assert spec.method == "POST"
    assert spec.path == "/symbols"
    assert spec.json_body == body
    assert spec.idempotent is True
    assert spec.authenticated is True
    assert spec.endpoint_name == "create_symbol"
```
El equivalente para `build_add_holidays_request` debe assertar **`spec.idempotent is False`** —
la única aserción de builder `False` del paquete. Los dos DELETE deben assertar
**`spec.json_body is None`**.

### Test de gate end-to-end (template shipeado)
```python
# Source: packages/market-data-client/tests/test_symbols_write.py:112-121
def test_create_symbol_refused_by_default_emits_no_request(httpx_mock: HTTPXMock) -> None:
    """Gate OFF por default + token FORZADO-vencido → refused, 0 HTTP y 0 grant Auth0."""
    market_data_client.configure(token_expires_at=0.0)   # si el gate no cortara, habría POST a Auth0
    with pytest.raises(MarketDataMutationNotAllowedError):
        market_data_client.client._get_default().create_symbol(NewSymbol("DLR/DIC26"))
    assert httpx_mock.get_requests() == []
```
Este es el patrón adversarial que hay que replicar para los **cinco** métodos × 2 superficies,
incluido `preview_calendar_config` (la prueba de que D-14 no tiene carve-out).

### Extensión del net de superficie pública
```python
# Source: packages/market-data-client/tests/test_public_surface_market_data.py:23-33
_NEW_PUBLIC_NAMES = ("MarketDataMutationNotAllowedError", "NewSymbol", "NewSymbols",
                     "SymbolPatch", "create_symbol", "create_symbols", "update_symbol")
_MUTATION_METHODS = ("create_symbol", "create_symbols", "update_symbol")
```
Phase 26 agrega a `_NEW_PUBLIC_NAMES`: `"HolidayIn"`, `"HolidaysIn"`, `"MarketHoursIn"`,
`"add_holidays"`, `"delete_calendar_config"`, `"delete_holiday"`, `"preview_calendar_config"`,
`"set_calendar_config"`; y a `_MUTATION_METHODS` los cinco nombres de método. Las cuatro pruebas
existentes (importabilidad, `__all__`, paridad de métodos de clase, ubicación de shims) cubren
automáticamente las entradas nuevas.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Cliente de sólo lectura (v0.2.0) | Primera superficie de escritura detrás de gate opt-in | Phase 25 (shipeada) | Phase 26 es la segunda superficie; sin cambios de gate |
| Gates de retry por nombre de método | Gate per-request `request.extensions["idempotent"]` | Phase 8/20 | Phase 26 es el **primer consumidor `idempotent=False`** del paquete |
| `parse_latest_response` iteraba las claves del envelope (WR-01) | Unwrap de `items[]` | quick `260731-t9o`, shipeado como **v0.3.1** | El gap WR-01 que D-16 menciona como "already-carried" **ya está cerrado**; sólo queda el de `get_calendar` |
| Codegen sync→async (unasync/libcst) | **Descartado permanentemente** (SPIKE-005 + SPIKE-006 NO-GO firmado) | Phase 18 | La duplicación `client.py`/`aio.py` es una característica estructural aceptada — D-17 se implementa a mano |

**Deprecated/outdated:** ninguno relevante a esta fase.

## Discrepancias entre CONTEXT.md y el código shipeado

> Esta sección es planning-critical: el planner debe usar los valores de la columna "Realidad".

| # | Claim en CONTEXT.md | Realidad verificada | Impacto en el plan |
|---|---------------------|---------------------|--------------------|
| X1 | "Package to extend (**market-data-client v0.2.0**)" | `__version__ = "0.3.1"` en `__init__.py:118` (bump del quick `260731-t9o`) | Ninguno para Phase 26 (no hay bump acá). **Flag para Phase 28**: PUB-MUT-01 apunta a `v0.3.0`, que ya fue superado — el target real será `v0.4.0` (o `v0.3.2`) |
| X2 | D-16: "Phase 27 debería arreglarlo junto al **gap WR-01 `parse_latest_response`** ya arrastrado" | WR-01 **ya está arreglado** y shipeado en v0.3.1 (`_core.py:619-653` unwrappea `items`) | El scope de Phase 27 se reduce: sólo queda el bug de `get_calendar`/`CalendarDay`. No cambia nada en Phase 26 |
| X3 | D-06/D-07: passthrough "**en el estilo de `parse_health_response`**" | `parse_health_response` **no es tolerante** (raise en body vacío; anotación mentirosa en `null`/`[]`) | **Escribir un parser nuevo**, no reusar. Ver Pattern 6 |
| X4 | `<code_context>`: "`_params.drop_none` — ya importado en el paquete; primer uso real en *request-model*" | Correcto, pero `models.py` **no importa `_params` hoy** — es un import nuevo en ese archivo | 1 línea de import nueva + verificación de que no hay ciclo (verificado: no lo hay) |
| X5 | ROADMAP: "Phase 26 **paraleliza con 25** tras el gate" (línea del plan fuente) | CONTEXT.md `<domain>` y STATE.md dicen 25 es prerequisito estricto | Sin impacto: Phase 25 ya está completa |
| X6 | (implícito) "los 4 gates incluyen `mypy` sobre este paquete vía `uv run mypy`" | `[tool.mypy] files` **excluye** `packages/market-data-client/src` (sólo lista los 5 paquetes viejos). El job `typecheck` de CI corre `uv run mypy` → no chequea este paquete. La cobertura real viene del hook `mypy` de pre-commit (`files: ^packages/.*/src/`), que corre en el job `pre-commit` | El comando local del gate mypy debe ser explícito: `uv run mypy packages/market-data-client/src`. Ver § Los 4 gates |
| X7 | (implícito) el loop `mypy` por-paquete de CI cubre los tests | El loop de `.github/workflows/ci.yml:84` itera sólo `higyrus/wallets/matriz/iol/ambito` — **no** `market-data-client` | Los errores mypy pre-existentes en los tests de este paquete (ver `25-deferred-items.md`) siguen sin bloquear CI. **No los arregles** (fuera de scope), pero tampoco agregues nuevos |
| X8 | (implícito) `import-linter` protege el boundary `_core` de este paquete | `[tool.importlinter] root_packages` lista sólo los 4 paquetes viejos | El boundary `_core` IO-free de market-data-client es **convención, no gate**. Los builders nuevos deben mantenerlo por disciplina |
| X9 | (no mencionado) | `AsyncClient.__init__` acepta `token`/`token_expires_at`/`http_client`; `Client.__init__` **no** | Asimetría pre-existente, fuera de scope. **No "arreglar"** — no toques los constructores |

## Runtime State Inventory

**No aplica.** Phase 26 es una fase **aditiva greenfield** (métodos/modelos/builders nuevos), no
un rename/refactor/migración. Verificado por grep: `MarketHoursIn`, `HolidayIn`, `HolidaysIn`,
`set_calendar_config`, `delete_calendar_config`, `preview_calendar_config`, `add_holidays` y
`delete_holiday` **no existen** en ningún archivo del repo. No hay datos almacenados,
configuración de servicio vivo, estado registrado en el SO, secretos ni artefactos de build que
carguen un nombre viejo a cambiar.

## Los 4 gates (comandos exactos)

| Gate | Comando local | Job de CI | Estado baseline (medido hoy) |
|------|---------------|-----------|------------------------------|
| ruff check | `uv run ruff check .` | `lint` | ✅ `All checks passed!` |
| ruff format | `uv run ruff format --check .` | `lint` | ✅ `191 files already formatted` |
| mypy strict (src global) | `uv run mypy` | `typecheck` | ✅ `no issues found in 51 source files` — ⚠ **excluye este paquete** (X6) |
| mypy strict (este paquete) | **`uv run mypy packages/market-data-client/src`** | vía hook `pre-commit` | ✅ `no issues found in 11 source files` |
| pytest (paquete) | `uv run --package market-data-client pytest packages/market-data-client/tests -q` | `test` (matrix py3.12/3.13) | ✅ **191 passed in 0.25s** |
| pytest (full) | `uv run pytest -q` | — | (paquetes + `tests` + `verification`) |

Gates adicionales del job `lint` que también deben quedar verdes: `uv lock --check`
(no cambia — sin deps nuevas), `uv run lint-imports` (no cubre este paquete, X8), y el grep
`lint-logging` (los métodos nuevos no deben llamar `logging.basicConfig` ni `logging.root.*`).
El job `pre-commit` corre además trailing-whitespace, end-of-file-fixer, check-yaml/toml.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio (`asyncio_mode = "auto"`) + pytest-httpx 0.36.2 |
| Config file | root `pyproject.toml` (`[tool.pytest.ini_options]`, `--import-mode=importlib`, `--strict-markers`, `--strict-config`) |
| Quick run command | `uv run --package market-data-client pytest packages/market-data-client/tests -q` |
| Full suite command | `uv run pytest -q` (todos los paquetes + `tests` + `verification`) |
| Baseline actual | **191 passed in 0.25 s** (medido hoy) — presupuesto de latencia holgadísimo |

### Phase Requirements → Test Map

| Req ID / SC | Behavior | Test Type | Automated Command | File Exists? |
|-------------|----------|-----------|-------------------|--------------|
| SC#1 / MUT-MD-02 | los 5 métodos despachan método/URL/Bearer correctos con el gate abierto, **sync** | unit | `pytest packages/market-data-client/tests/test_calendar_write.py -q` | ❌ Wave 0 |
| SC#1 / MUT-MD-02 | idem, **async** (espejo) | unit | `pytest packages/market-data-client/tests/test_calendar_write_async.py -q` | ❌ Wave 0 |
| SC#2 | `MarketHoursIn` emite `confirm: False` por default en el body de `PUT`; `confirm=True` viaja cuando se setea; el resto de defaults (`pre_open_minutes=10`, `enabled=True`, `updated_by=""`) se emiten | unit | `pytest .../test_calendar_write.py -k confirm -q` + `pytest .../test_models.py -q` | ❌ Wave 0 |
| SC#3 | `to_dict()` de los 3 modelos rutea por `drop_none`: `HolidayIn` sin times **omite** `open_time`/`close_time` y **emite** `closed=True` + `description=""`; `HolidaysIn` anida | unit | `pytest .../test_models.py -q` | parcial (existe, extender) |
| SC#3 | `preview_calendar_config` **pasa por el gate** (refused con gate OFF, 0 requests) — excepción read-safe documentada | unit | `pytest .../test_calendar_write.py -k preview -q` | ❌ Wave 0 |
| SC#4 | `build_add_holidays_request` ⇒ `idempotent is False`; los otros 4 ⇒ `True`; los 2 DELETE ⇒ `json_body is None` | unit (builder) | `pytest .../test_core.py -q` | parcial (existe, extender) |
| SC#4 | **dispatch-level**: `add_holidays` contra 503 repetido emite **exactamente 1** request y 0 sleeps (primero del paquete, D-15) | unit | `pytest .../test_calendar_write.py -k retry -q` | ❌ Wave 0 |
| SC#5 (gate) | los 5 métodos refuse-by-default con **0 HTTP y 0 round-trip Auth0** (token forzado-vencido), sync + async | unit | `pytest .../test_calendar_write.py .../test_calendar_write_async.py -q` | ❌ Wave 0 |
| SC#5 (gate host) | gate ON + host ≠ `expected_host` ⇒ refused, 0 requests | unit | idem | ❌ Wave 0 |
| SC#5 (422) | `422` del servidor ⇒ `MarketDataAPIError` vía `raise_for_response` (sin manejo nuevo) | unit | idem | ❌ Wave 0 |
| SC#5 (tolerancia) | body `200` vacío ⇒ `CalendarConfig.from_api(None)` (config trio) y `{}` (holiday pair), nunca raise | unit | `pytest .../test_core.py -q` | ❌ Wave 0 |
| SC#5 (paridad) | los 5 métodos existen en `Client` y `AsyncClient`; shims sync en el namespace plano, async bajo `aio`; 8 nombres nuevos en `__all__` | unit | `pytest .../test_public_surface_market_data.py -q` | parcial (existe, extender) |
| SC#5 (bound) | `HolidaysIn([])` y `HolidaysIn([501 items])` ⇒ `ValueError` pelado antes de cualquier dispatch | unit | `pytest .../test_models.py -q` | parcial (existe, extender) |
| SC#5 (4 gates) | ruff check / ruff format / mypy strict / pytest verdes | gate | ver § Los 4 gates | n/a |

### Sampling Rate

- **Per task commit:** `uv run --package market-data-client pytest packages/market-data-client/tests -q` (~0.3 s)
- **Per wave merge:** `uv run pytest -q` (suite completa incl. `verification/`)
- **Phase gate:** los 4 gates verdes — incluyendo el mypy **explícito** del paquete
  (`uv run mypy packages/market-data-client/src`, X6) — antes de `/gsd-verify-work`
- **Max feedback latency:** < 5 s

### Wave 0 Gaps

- [ ] `packages/market-data-client/tests/test_calendar_write.py` — 5 métodos sync: dispatch feliz
      (método/URL/Bearer/body), `confirm` default `False` en el wire, DELETE sin body ni
      `Content-Type`, `422`→typed, refusal ×5 con 0 requests, host mismatch, no-retry de
      `add_holidays` (+ control positivo con `monkeypatch` de `time.sleep`), shims module-level
      — cubre SC#1–5
- [ ] `packages/market-data-client/tests/test_calendar_write_async.py` — espejo async idéntico
      sobre `aio._get_default()` — cubre SC#1/SC#5 paridad
- [ ] Extender `packages/market-data-client/tests/test_core.py` — 5 specs de builder
      (method/path/json_body/idempotent/authenticated/endpoint_name), state-independence, y
      tolerancia del parser passthrough nuevo (body vacío/`null`/no-dict ⇒ `{}`)
- [ ] Extender `packages/market-data-client/tests/test_models.py` — `to_dict()` de los 3 modelos,
      defaults verbatim de la OpenAPI, efecto de `drop_none` (drop de times `None`, preservación
      de `closed=True`/`description=""`), bound 1–500 de `HolidaysIn`
- [ ] Extender `packages/market-data-client/tests/test_public_surface_market_data.py` —
      `_NEW_PUBLIC_NAMES` +8, `_MUTATION_METHODS` +5
- [ ] **Sin gaps de infraestructura**: framework, config, `conftest.py` (incl. el reset del gate)
      y todos los templates ya existen. No hay que instalar ni configurar nada.

### Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Shape real de los 5 bodies `200`; idempotencia real por endpoint; `"HH:MM"` vs `"HH:MM:SS"`; efecto de dropear vs. mandar `null` en los times de un feriado | LIVE-MUT-01 | Requiere develop en vivo + creds Auth0; la OpenAPI declara los 5 `200` como `object` sin schema | Diferido a Phase 27 (create→verify→revert con identificadores dedicados). Los parsers tolerantes (D-07) son el hedge |

## Security Domain

`security_enforcement: true`, `security_asvs_level: 1`, `security_block_on: "high"`
(`.planning/config.json`). Phase 26 opera **detrás de** un control de seguridad
(el mutating-gate) y agrega superficie de mutación, así que la sección aplica de lleno.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V1 Arquitectura / defaults seguros | sí | Refuse-by-default heredado (`mutating_allowed=False`) + `confirm=False` por default en `MarketHoursIn` (D-09) — **dos** capas de "no hagas nada peligroso sin pedirlo" |
| V4 Control de acceso | sí | Doble gate (flag opt-in + host exacto) antes de cualquier llamada mutante, incluido `preview` (D-14, sin carve-out) |
| V5 Validación de entrada | sí | `HolidaysIn` 1–500 client-side (D-12); resto delegado al `422` del servidor (D-13). ⚠ **Gap identificado**: `day` interpolado raw permite retargeting de path — ver Open Question 1 |
| V6 Criptografía | no | Sin cripto nueva; el manejo del Bearer no cambia |
| V7 Manejo de errores / logging | sí | `RedactingFilter` + `__repr__` redactor existentes; los métodos nuevos **no deben loguear payloads**. `updated_by` es un campo libre — no incluirlo en mensajes de error |
| V9 Comunicaciones | sí | El gate de hostname exacto impide mutar contra un host inesperado |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Mutación de calendario disparada sin opt-in | Tampering | `mutating_allowed=False` refuse-by-default (heredado, sin cambios) |
| Config de mercado sobrescrita saltándose el warning del servidor | Tampering | `confirm: bool = False` como campo del modelo (D-09) — el consumidor tiene que escribir `confirm=True` a propósito |
| Mutación despachada a un host hostil / equivocado | Tampering / Spoofing | Match exacto `urlsplit(base_url).hostname == expected_host` (heredado) |
| Refusal filtra el intento vía round-trip a Auth0 | Information Disclosure | Gate estrictamente antes de `_ensure_token` (D-14) — probado con token forzado-vencido |
| **Feriado duplicado por reintento de un POST no idempotente** | Tampering | `idempotent=False` en `build_add_holidays_request` ⇒ el `RetryTransport` no reintenta. **Este es el motivo por el que D-15 exige el primer test no-retry a nivel dispatch** |
| **Retargeting de request vía `day` interpolado raw** | Tampering | ⚠ **SIN mitigación bajo D-03/D-13 tal como están**. `day="../config"` ⇒ `DELETE /api/calendar/config`; `day="X?a=1"` ⇒ inyecta query string. Verificado con httpx. Ver Open Question 1 |
| Credencial filtrada en logs de mutación | Information Disclosure | `RedactingFilter` + `__repr__` redactor (no regresionar) |

## Environment Availability

**Skipped** — sin dependencias externas nuevas. La fase es un cambio de código puro contra el
workspace ya instalado (`uv sync --all-packages --all-extras --dev --frozen`). Los tests
mockeados (pytest-httpx) no requieren red; la verificación en vivo es explícitamente Phase 27.
El fetch a la OpenAPI en vivo hecho durante esta investigación fue **sólo para research** — el
plan no debe depender de conectividad.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | El body `200` real de los 5 endpoints encaja en `CalendarConfig` (trío config) y en un dict passthrough (par holiday). La OpenAPI los declara `object` sin schema | D-05 / D-06 | MED — degradación grácil por los parsers tolerantes (D-07); Phase 27 reconcilia. Explícitamente diferido |
| A2 | `POST /calendar/holidays` es realmente no idempotente y los otros 4 son retry-safe (DM-03, por semántica HTTP) | D-04 | MED — un `PUT` que no sea idempotente del lado servidor podría duplicar efectos al reintentar; se revalida en vivo (Phase 27) |
| A3 | Dropear `open_time`/`close_time` cuando son `None` es equivalente a mandarlos `null` (la OpenAPI dice *"null = configured default"* y el default del campo también es `None`) | D-11 | LOW-MED — si el servidor distingue "clave ausente" de `null`, un feriado con horario custom parcial se comportaría distinto; Phase 27 confirma |
| A4 | El servidor acepta `"HH:MM"` (los ejemplos de la OpenAPI usan `"10:00"`) además de lo que `format: time` admita | D-13 | LOW — un formato equivocado sale como `422` tipado, que es exactamente el contrato de D-13 |
| A5 | Un `day` fuera de forma ISO produce `422` y no un efecto colateral peligroso | D-03 / Open Q1 | **MED-HIGH** — refutado parcialmente: `day="../config"` **no** llega como `day` malformado, retarget-ea a otro endpoint. Ver Open Question 1 |
| A6 | Los nombres de builder/parser propuestos (`build_set_calendar_config_request`, `parse_calendar_write_response`, …) son aceptables — CONTEXT.md los deja a discreción | Patterns 1-3, 6 | LOW — sólo naming; los nombres de método público están LOCKED |

## Open Questions

1. **`day` interpolado raw permite retargeting del request (path-segment escape).**
   - **Lo que sabemos (verificado con httpx 0.28.1):**
     `f"/calendar/holidays/{day}"` con `day="../config"` produce el path normalizado
     `/api/calendar/config` — es decir, un `delete_holiday("../config")` ejecuta de hecho un
     `DELETE /api/calendar/config` (**reset de la configuración de mercado**, otro endpoint de la
     misma fase). Con `day="2026-12-25?x=1"` httpx separa `x=1` como query string. Con
     `day="a/b"` se emiten dos segmentos de path.
   - **Lo que no está claro:** D-03 lockea la interpolación RAW (correcta para ISO dates: no hay
     nada que percent-encodear) y D-13 lockea "sin validación escalar client-side" (correcta para
     bounds de formato, que son territorio del `422`). Ninguna de las dos contempla esta clase de
     problema, que **no es de formato sino de seguridad de path**: el `422` del servidor nunca
     llega a ejercerse porque el request nunca apunta al endpoint que iba a validarlo.
   - **Recomendación:** añadir en `build_delete_holiday_request` (o en el método del shell) un
     guard **mínimo** de path-safety que levante `ValueError` si `day` contiene `/`, `?`, `#`,
     `..` o está vacío. Es estrictamente más angosto que `quote()` (D-03 sigue valiendo byte a
     byte para cualquier ISO date legítimo) y no es una validación de formato (D-13 sigue valiendo:
     `"2026-13-45"` sigue yendo al `422`). Costo: 3 líneas + 1 test.
     **Alternativa si se prefiere no desviarse de lo lockeado:** documentarlo como finding de
     seguridad para Phase 27 y dejar el comportamiento como está. El planner debería escalar esta
     decisión al operator — `security_block_on: "high"` está activo y esto es una mutación
     no intencionada disparable por input del consumidor.

2. **Naming del parser passthrough: uno o dos.**
   - **Lo que sabemos:** CONTEXT.md lo deja a discreción. Los dos endpoints tienen contrato
     idéntico (`200` bare object, tolerancia a body vacío).
   - **Recomendación:** **una sola** función (`parse_calendar_write_response`) usada por ambos
     métodos. Menos superficie, un solo set de tests de tolerancia. Ya resuelto en Pattern 6.

3. **Organización de los archivos de test.**
   - **Recomendación (resuelta):** archivos nuevos `test_calendar_write.py` /
     `test_calendar_write_async.py` espejando `test_symbols_write*.py`, y **extensión** de
     `test_core.py` / `test_models.py` / `test_public_surface_market_data.py`. Esto mantiene el
     paralelismo 1:1 con Phase 25 y hace que el diff sea legible por wave.

## Sources

### Primary (HIGH confidence — verificado contra el código y ejecutado esta sesión)
- `packages/market-data-client/src/market_data_client/_core.py` — `RequestSpec` (106-130),
  `raise_for_response` (138-150), `build_create_symbol_request` (394-409),
  `build_create_symbols_request` (412-426), `build_update_symbol_request` (429-447),
  `build_segments_request` (502-515), `build_calendar_config_request` (567-580),
  `parse_health_response` (273-278), `parse_calendar_response` (716-730),
  `parse_calendar_config_response` (733-746), `__all__` (71-98) [VERIFIED]
- `packages/market-data-client/src/market_data_client/models.py` — `SafeModel`/`_coerce` (58-117),
  `LatestRequest` (163-184), `NewSymbol`/`NewSymbols`/`SymbolPatch` (197-252),
  `CalendarDay` (312-323), `CalendarConfig` (326-350), `__all__` (43-55) [VERIFIED]
- `packages/market-data-client/src/market_data_client/client.py` — `_ensure_mutation_allowed`
  (257-283), `_request` (337-394), métodos symbols (539-574), `configure` (605-669),
  shims (764-786) [VERIFIED]
- `packages/market-data-client/src/market_data_client/aio.py` — `_ensure_mutation_allowed`
  (215-240), `_request` (344-406), métodos symbols (552-585), `configure` (620-678),
  shims (773-795) [VERIFIED]
- `packages/market-data-client/src/market_data_client/_transport.py` — gate `idempotent`
  (157-163), `_retry_after_or_jitter_wait` (113-135) [VERIFIED]
- `packages/market-data-client/src/market_data_client/_params.py` — `drop_none` (22-28) [VERIFIED]
- `packages/market-data-client/src/market_data_client/_state.py` — `_ClientState` (84-114),
  `_DEFAULT_EXPECTED_HOST` (53-55) [VERIFIED]
- `packages/market-data-client/src/market_data_client/exceptions.py` + `__init__.py`
  (`__version__ = "0.3.1"`) [VERIFIED]
- Tests: `conftest.py`, `test_symbols_write.py`, `test_symbols_write_async.py`,
  `test_mutation_gate.py`, `test_public_surface_market_data.py`, `test_core.py:318-378`,
  `test_transport.py:88-107`, `packages/iol-client/tests/test_transport.py:41-53` [VERIFIED]
- **Ejecuciones locales de verificación (esta sesión):** httpx 0.28.1
  `build_request("DELETE", …, json=None)` ⇒ `b""` sin `Content-Type`; `json={}` ⇒ `b"{}"` con
  `Content-Type`; normalización de `"../config"` / `"?x=1"` en el path; `idempotent=False` ⇒
  1 request / 0 sleeps vs. `idempotent=True` ⇒ 3 requests / 2 sleeps; tolerancia de
  `parse_calendar_config_response` a `b""`/`b"null"`; intolerancia de `parse_health_response` a
  `b""`; `parse_calendar_response(envelope)` ⇒ 4 `CalendarDay` all-default; baseline de los
  4 gates (ruff/format/mypy/191 tests) [VERIFIED]
- **`GET https://market-data-develop.bbsa.com.ar/api/openapi.json` re-fetcheada esta sesión** —
  los 5 endpoints, `MarketHoursIn`/`HolidayIn`/`HolidaysIn` con defaults y bounds, `day` como
  `format: date`, los 5 `200` como bare `object` [VERIFIED]
- `.planning/verification/schemas/market-data-client/get-calendar.json` (envelope real que prueba
  D-16) y `get-calendar-config.json` (wire real que respalda D-05) [VERIFIED]
- `pyproject.toml` (`[tool.mypy] files`, `[tool.ruff]`, `[tool.pytest.ini_options]`,
  `[tool.importlinter]`), `.pre-commit-config.yaml`, `.github/workflows/ci.yml`, `uv.lock` [VERIFIED]

### Secondary (MEDIUM confidence)
- `.planning/phases/26-calendar-write/26-CONTEXT.md` — D-01…D-17 lockeadas
- `.planning/phases/25-mutating-gate-symbols-write/25-{RESEARCH,CONTEXT,PATTERNS,VALIDATION}.md`
  y `deferred-items.md`
- `.planning/future-plans/market_data_mutations.md` — tabla de endpoints de calendar, DM-03
- `.planning/REQUIREMENTS.md` (MUT-MD-02), `.planning/ROADMAP.md` (Phase 26 SC#1–5),
  `.planning/STATE.md` (decisiones acumuladas, quick `260731-t9o`), `./CLAUDE.md`

### Tertiary (LOW confidence)
- Ninguna. No se usó ninguna fuente web ni conocimiento de entrenamiento no verificado: todo se
  ancló en el código del repo, la OpenAPI en vivo o ejecuciones locales.

## Metadata

**Confidence breakdown:**
- Contrato de la API: **HIGH** — OpenAPI en vivo re-fetcheada y parseada esta sesión; los 3
  schemas y los 5 endpoints confirmados campo por campo
- Stack / infraestructura: **HIGH** — sin deps nuevas; cada mecanismo verificado presente y
  ejercitado
- Patterns: **HIGH** — los 8 patrones tienen precedente in-package shipeado y citado por línea
- Pitfalls: **HIGH** — 5 de 8 fueron reproducidos empíricamente esta sesión (no inferidos)
- Discrepancias: **HIGH** — cada fila fue verificada contra el archivo concreto
- Validación: **HIGH** — baseline de los 4 gates medido hoy (191 tests, 0.25 s)
- Seguridad: **MED-HIGH** — el gate heredado es HIGH; el gap de path-safety de `day` es un
  hallazgo nuevo verificado que requiere decisión del operator (Open Question 1)
- Shapes de respuesta: **LOW por diseño** — la OpenAPI no las declara; diferidas a Phase 27 con
  parsers tolerantes como hedge

**Research date:** 2026-07-31
**Valid until:** 2026-08-30 (estable — código interno del paquete; la única fuente móvil es la
OpenAPI de develop, que conviene re-fetchear si Phase 26 se planifica después de esa fecha)
