# Requirements: market-libs — v1.5 market-data-client · mutaciones

**Defined:** 2026-07-31
**Core Value:** Que las mutaciones del cliente reflejen fielmente el contrato de la API develop y sean **imposibles de disparar por accidente** (opt-in explícito + gate de entorno + no-retry de no idempotentes), con la misma calidad (dual sync/async, request-models tipados, logging redactado, tests, verificación en vivo) que el resto del monorepo.

## v1 Requirements

Requisitos del milestone v1.5. Cada uno mapea a una fase del roadmap. Plan fuente: `.planning/future-plans/market_data_mutations.md`.

### Safety

- [x] **GATE-MD-01**: El paquete provee un **mutating-gate de seguridad** — toda operación de mutación requiere opt-in explícito del consumidor (`Client(mutating_allowed=True)` / `configure(mutating_allowed=True)`); por default rehúsa con un error tipado nuevo (`MarketDataMutationNotAllowedError ⊂ MarketDataError`). Segundo gate de entorno (verifica host/base_url esperado antes de mutar). Las operaciones no idempotentes NO se reintentan (`request.extensions["idempotent"]=False`). Espeja el patrón de `matriz-client` / `verification/mutation_gate.py`, dual sync (`client.py`) y async (`aio.py`)

### Symbols (write)

- [x] **MUT-MD-01**: El consumidor puede escribir symbols — `POST /symbols` (crear uno, `NewSymbol`), `POST /symbols/batch` (crear 1–500, `NewSymbols`) y `PATCH /symbols/{symbol_id}` (actualizar `active`, `SymbolPatch`) — con request-models tipados serializados a JSON, respuestas `SafeModel` tolerantes, sync y async, detrás del mutating-gate

### Calendar (write)

- [x] **MUT-MD-02**: El consumidor puede administrar el calendario — `PUT /calendar/config` (setear horario, `MarketHoursIn`, respeta `confirm`), `DELETE /calendar/config` (reset), `POST /calendar/config/preview` (preview sin persistir, `MarketHoursIn`), `POST /calendar/holidays` (agregar feriados, `HolidaysIn`) y `DELETE /calendar/holidays/{day}` (borrar un feriado) — con request-models tipados, sync y async, detrás del mutating-gate

### Verification

- [ ] **LIVE-MUT-01**: La superficie de mutación completa (sync + async) se ejercita en vivo contra develop con credenciales Auth0 a través de `main_market_data.py`, **detrás del mutating-gate** y con **identificadores de prueba dedicados + cleanup** (create→verify→revert); NUNCA toca config real de mercado sin `confirm`. Toda divergencia (shape de respuesta, idempotencia real, códigos) se documenta y se corrige en el mismo ciclo, espejada sync/async. Revalida la idempotencia asumida por-endpoint (DM-03)

### Release

- [ ] **PUB-MUT-01**: `market-data-client` se publica como `v0.3.0` (minor bump — features nuevas, no rompe la superficie de lectura v0.2.0) por el pipeline de tags — bump `pyproject`+`__version__`, README changelog, `uv.lock` refresh, CI verde, PR → merge → tag `market-data-client-v0.3.0` → GitHub Release con wheel + sdist

## v2 Requirements

Diferidos a v1.6+. Trackeados pero fuera del roadmap actual.

### Streaming

- **STREAM-MD-01**: Consumir el stream de market data (`GET /marketdata/stream`, SSE con param `interval`) vía un transporte dedicado (patrón `ws_client` de matriz)

### Security

- **SEC-MD-01**: Cache del token Auth0 en disco (`_token_cache.py` + platformdirs, atomic + flock + 0600)
- **SEC-MD-02**: Validación de firma del JWT (RS256) contra el JWKS de Auth0

## Out of Scope

Excluido explícitamente para prevenir scope creep.

| Feature | Reason |
|---------|--------|
| Streaming SSE `/marketdata/stream` | Transporte distinto (streaming); se planifica aparte — v1.6+ |
| Cache de token en disco | El grant client_credentials es barato de re-obtener; cache en memoria por TTL alcanza |
| Validación de firma JWT | El token se usa como bearer opaco (Auth0 lo emite, el servidor lo valida) |
| Mutar config real de mercado en develop sin `confirm` | La verificación en vivo usa identificadores de prueba + cleanup; tocar config real requiere autorización operator explícita |
| prod-vs-remarkets / `ws_client` live / token encryption at-rest | Carry-forwards del monorepo, siguen en el ROADMAP Backlog |

## Traceability

Qué fases cubren qué requisitos. Confirmado en la creación del roadmap (2026-07-31).

| Requirement | Phase | Status |
|-------------|-------|--------|
| GATE-MD-01 | Phase 25 | Complete |
| MUT-MD-01 | Phase 25 | Complete |
| MUT-MD-02 | Phase 26 | Complete |
| LIVE-MUT-01 | Phase 27 | Pending |
| PUB-MUT-01 | Phase 28 | Pending |

**Coverage:**

- v1 requirements: 5 total
- Mapped to phases: 5 (confirmed — 100% coverage, sin orphans)
- Unmapped: 0

---
*Requirements defined: 2026-07-31*
*Last updated: 2026-07-31 after v1.5 roadmap creation (Phases 25-28)*
