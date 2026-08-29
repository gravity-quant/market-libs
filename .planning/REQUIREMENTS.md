# Requirements: market-libs — v1.7 API tipada con Null Objects

**Defined:** 2026-08-28
**Core Value:** Que toda cadena de acceso (`snapshot.market_data.last.price`) sea siempre válida bajo mypy strict y nunca lance: ningún eslabón intermedio de tipo modelo/lista puede ser `None`, y `dict[str, Any]` desaparece de los campos de modelos públicos — un typo es error de mypy + `AttributeError`, nunca un `KeyError` ni un `None` propagado.

**Plan fuente:** `.future_plans/api-tipada-null-objects.md` (principios D-NO-01..06 + inventario por paquete). Revoca la decisión "fix-shape-now" (v1.6 F33, SC-2).

## v1.7 Requirements

Requirements for this milestone. Each maps to roadmap phases.

### Fundaciones Null Object

- [x] **NOBJ-01**: Toda instancia vacía de un `SafeModel` es falsy (`bool(X.from_api(None)) is False`) y una instancia con al menos un campo no-default es truthy, en los 6 paquetes (copia verbatim de la base + `empty()` garantizado en todas las jerarquías, incl. `_SafeModel` de matriz)
- [x] **NOBJ-02**: El walker `_decode` colapsa `null`/ausente sobre un campo modelo/lista **no-opcional** a instancia vacía/`[]` sin emitir divergencia; un valor wrong-typed sigue emitiendo divergencia y sigue fatal bajo `strict_decode`; los 4 gates de CI de v1.6 (`check_decode_intactness.py`, `check_uniform_structure.py`, `check_surface_types.py`, `surface_parity.py`) siguen verdes tras la actualización verbatim

### market-data-client

- [x] **NOBJ-MD-01**: `snapshot.market_data.last.price` compila bajo mypy strict y nunca lanza con ningún payload real ni `None` — `market_data` pasa de `dict[str, Any] | None` a modelo tipado (campos wire `BI`/`OF: list[BookLevel]`, `LA`/`SE`/`CL`/`OI: EntryValue` Null Object, `OP`/`HI`/`LO`/`TV/...: float | None`) con propiedades alias `last`/`bids`/`offers`/`settlement`/`close`/`open_interest`
- [x] **NOBJ-MD-02**: `MarketDataSnapshot.entries` vuelve a `list[str]` default `[]` (revierte el widening F33) y `LatestRequest.entries` se alinea; la fila no-data de `/marketdata/latest` expone `market_data` vacío falsy + `note` poblado; se elimina la maquinaria `_mapping_value`/`_apply_mapping_policy` y sus tests de precondición

### iol-client

- [x] **NOBJ-IOL-01**: `Cotizacion.puntas` es `list[Punta]` (nunca `None`) y `Titulo.puntas` es `Punta` Null Object — `titulo.puntas.precioCompra` siempre válido, espejado sync/async

### matriz-client

- [x] **NOBJ-MTZ-01**: `InstrumentDetail.tickPriceRanges`, `AccountReport.report`, `AccountReport.detailedAccountReports`, `AccountReport.portfolio` tipados como modelos contra payloads reales (exención única y documentada: `UnknownFrame.raw`)
- [x] **NOBJ-MTZ-02**: `matriz_client.models.MarketDataSnapshot` gana las mismas propiedades alias (`last`/`bids`/`offers`/`settlement`/`close`/`open_interest`), compartidas por la superficie REST y los frames WS

### Auditoría resto

- [ ] **NOBJ-AUD-01**: higyrus/ámbito/wallets auditados: cero campos modelo/lista `| None` y cero `dict[str, Any]` en campos de modelos públicos, verificable por gate/grep (hojas escalares `T | None` permitidas por D-NO-03)

### Verificación en vivo + release

- [ ] **LIVE-NOBJ-01**: los drivers `main_*.py` ejercitan el encadenamiento profundo (sync + async) contra las APIs en vivo en los paquetes verificables; toda divergencia detectada se corrige in-cycle con espejo sync/async y regresión mockeada
- [ ] **PUB-NOBJ-01**: los paquetes cuya superficie pública cambió se publican por el pipeline de tags con bump breaking + changelog callout + tabla de migración, bajo doble gate humano (precedente D-08/D-18, nunca colapsado ni auto-aprobado)

## Deferred / v-next

- **SSE streaming** `GET /marketdata/stream` (market-data) — backlog previo
- **Disk token cache + validación JWT** (market-data) — backlog previo
- **Endpoints reales de wallets-client** — sigue stub
- **LIVE-HIGY-33 / LIVE-MATZ-33** — corridas estrictas pendientes de v1.6 (DNS / safety assert), destino ya nombrado

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Hojas escalares sin `None` (`price: float`, etc.) | D-NO-03: una hoja `T \| None` termina la cadena sin romperla y preserva ausente-vs-cero; forzar `0.0` re-introduce el typed zero silencioso |
| `Optional` chaining vía librerías externas (glom, pydash, etc.) | La solución es estructural (Null Object), no una dependencia nueva |
| Paquete compartido `market-libs-core` | Restricción de diseño vigente (DT-03): sin código compartido entre paquetes; todo cambio de base se copia verbatim |
| Renombrar campos wire a snake_case | Convención wire-verbatim vigente; la ergonomía se resuelve con propiedades alias, no con renames |
| Codegen sync/async (REFAC-06) | Permanentemente archivado (2 spikes NO-GO) |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| NOBJ-01 | Phase 35 | Complete |
| NOBJ-02 | Phase 35 | Complete |
| NOBJ-MD-01 | Phase 36 | Complete |
| NOBJ-MD-02 | Phase 36 | Complete |
| NOBJ-IOL-01 | Phase 38 | Complete |
| NOBJ-MTZ-01 | Phase 37 | Complete |
| NOBJ-MTZ-02 | Phase 37 | Complete |
| NOBJ-AUD-01 | Phase 38 | Pending |
| LIVE-NOBJ-01 | Phase 39 | Pending |
| PUB-NOBJ-01 | Phase 40 | Pending |

**Coverage:**

- v1.7 requirements: 10 total
- Mapped to phases: 10 ✓
- Unmapped: 0

**Phases (35-40):**

| Phase | Name | Requirements |
|-------|------|--------------|
| 35 | Fundación Null Object — `__bool__` + política del walker (load-bearing) | NOBJ-01, NOBJ-02 |
| 36 | `market-data-client` — `market_data` tipado + revocación de la Fase 33 | NOBJ-MD-01, NOBJ-MD-02 |
| 37 | `matriz-client` — dicts residuales tipados + alias | NOBJ-MTZ-01, NOBJ-MTZ-02 |
| 38 | `iol-client` + auditoría de higyrus/ámbito/wallets | NOBJ-IOL-01, NOBJ-AUD-01 |
| 39 | Verificación en vivo del encadenamiento profundo | LIVE-NOBJ-01 |
| 40 | Releases breaking coordinados | PUB-NOBJ-01 |

Phases 36, 37 y 38 paralelizan (dependen sólo de la 35, paquetes disjuntos); 39 depende de 36+37+38; 40 depende de 39.

---
*Requirements defined: 2026-08-28*
*Last updated: 2026-08-29 after v1.7 roadmap creation (phases 35-40, 10/10 requirements mapped)*
