---
gsd_state_version: 1.0
milestone: v1.8
milestone_name: Cierre de deuda post-v1.7
current_phase: 45
current_phase_name: limpieza-del-harness-dedupe-de-drift-comentarios-stale-desti
status: executing
stopped_at: Completed 45-04-PLAN.md
last_updated: "2026-09-01T15:29:04.188Z"
last_activity: 2026-09-01
last_activity_desc: Phase 45 execution started
progress:
  total_phases: 5
  completed_phases: 4
  total_plans: 24
  completed_plans: 21
  percent: 80
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-30 after v1.7 milestone complete)

**Core value:** Cada divergencia entre un cliente y su API en vivo debe ser detectada, documentada y corregida. (v1.7 lo lleva al sistema de tipos: ningún eslabón intermedio de una cadena de acceso —`snapshot.market_data.last.price`— puede ser `None`; el patrón Null Object hace que la ausencia se exprese por veracidad, `dict[str, Any]` desaparece de los campos de modelos públicos, y un typo es error de mypy + `AttributeError`, nunca un `KeyError` ni un `None` propagado.)

**Current focus:** Phase 45 — limpieza-del-harness-dedupe-de-drift-comentarios-stale-desti

## Current Position

Phase: 45 (limpieza-del-harness-dedupe-de-drift-comentarios-stale-desti) — EXECUTING
Plan: 3 of 5
Status: Ready to execute
Last activity: 2026-09-01 — Phase 45 execution started
Resume: Phase 44 is done. Next is Phase 45 (harness cleanup — drift dedupe, stale comments, `verification/` destination for matriz — HARN-01/03/04) — not yet planned or started; `/gsd-plan-phase 45` or `/gsd-discuss-phase 45` is the next step.

## Performance Metrics

**Velocity (v1.0 archived):**

- Total plans completed: 162 (v1.0)
- Total tasks completed: 27 (v1.0)
- v1.0 duration: 2026-05-28 → 2026-06-10 (~13 days, 5 phases)

**By Phase (v1.0):**

| Phase | Plans | Status   | Notes |
|-------|-------|----------|-------|
| 01    | 4     | Complete | Safety harness baseline |
| 02    | 3     | Complete | Ámbito (smallest blast radius) |
| 03    | 3     | Complete | IOL (OAuth refresh_token) |
| 04    | 4     | Complete | Higyrus (largest surface; 24+ regressions) |
| 05    | 4     | Complete | Matriz (sync only; 19 regressions; DRIFT-02 closure) |

**By Phase (v1.1 shipped 2026-06-14):**

| Phase | Plans | Status   | Notes |
|-------|-------|----------|-------|
| 06    | 7     | Complete | Compat safety net + Client/AsyncClient classes + PEP 562 shim (REFAC-01/02) |
| 07    | 6     | Complete | `_core.py` extraction + import-linter contracts (REFAC-03 + CR-03/05; LOC drop partial, v1.2 carry-forward) |
| 08    | 6     | Complete | `tenacity` retries + full-jitter backoff + mutation gate + `RedactingFilter` (RELY-01..04 + LOG-01..03) |
| 09    | 4     | Complete | 4 deferred bug fixes (BUG-01..04, 2 operator overrides) |
| 10    | 4     | Complete | matriz `aio.py` 852 LOC + TokenStore 3-way + `_atransport.py` (REFAC-04 + LIVE-02) |
| 11    | 3     | Complete | findings.py append-only + 6 CR fixes + LIVE-01 final gate × 4 packages (HARN-07..10 + CR-01/02/04/06/07/08 + LIVE-01) |

- v1.1 duration: 2026-06-11 → 2026-06-14 (~3.5 days, 6 phases, 30 plans, 52 tasks)
- v1.1 git stats: 179 commits, 307 files changed, +76,286 / −3,538 LOC
- Test suite: 277 (v1.0 close) → 907/908 (v1.1 close) on Python 3.12 local
- Quick tasks: 3 (260611-u0v, 260613-nwb, 260614-de5)

**By Phase (v1.2 shipped 2026-06-25):**

| Phase | Plans | Status   | Notes |
|-------|-------|----------|-------|
| 12    | 4/3   | Complete | Codegen tool-choice spike (unasync vs libcst) — **NO-GO** (3/8 D-RIGOR-01 FAIL, source-shape asymmetry); REFAC-06 → v1.3; REFAC-06 (spike) |
| 13    | 5     | Complete | `with_options(max_retries=N)` × 4 packages; CRITICAL matriz mutation-gate merge gate (new_order under 503 = exactly 1 request); ERG-01 |
| 14    | 3     | Complete | IOL `_token_cache.py` + platformdirs + fcntl.flock + 0600 + caplog no-leak + failed-refresh cleanup; SEC-01 |
| 15    | 5/4   | Complete | Driver migration × 4; ONE Client per main() AST guard; probe-name stability vs LIVE-01 71bf201; REFAC-05 |
| 16    | -     | Dropped  | Codegen Single-Source — DROPPED per Phase 12 NO-GO; REFAC-06 → v1.3 |
| 17    | 3     | Complete | Final LIVE-01-equivalent gate × 4 packages; cycle closure × 4 PASS; 0-BLOCKER audit; LIVE-03 |

- v1.2 duration: 2026-06-14 → 2026-06-25 (5 phases, 18 plans, 40 tasks); shipped via PR #2
- Test suite: 907 (v1.1 close) → ≥989 (v1.2 close) on Python 3.12 + 3.13

**By Phase (v1.4 shipped 2026-07-31):**

| Phase | Plans | Status   | Notes |
|-------|-------|----------|-------|
| 20    | 6     | Complete | Scaffold + Auth0 client-credentials + transport foundations; AUTH-MD-01 + CORE-MD-01 |
| 21    | 4     | Complete | Market data read surface + models (`received_at` client-stamped); MD-01 |
| 22    | 2     | Complete | Reference-data read surface + 5 models; REF-MD-01 |
| 23    | 2     | Complete | Live-verification apparatus (`main_market_data.py`) + D-09 hardening; LIVE-MD-01 |
| 24    | 2     | Complete | Release prep + publish `market-data-client-v0.1.0`; PUB-MD-01 |

- v1.4 duration: 2026-07-29 → 2026-07-31 (5 phases, 16 plans, 36 tasks); package released v0.1.0 → v0.2.0

**By Phase (v1.5 planned):**

| Phase | Plans | Status      | Requirements | Notes |
|-------|-------|-------------|--------------|-------|
| 25    | ?     | Not started | GATE-MD-01 + MUT-MD-01 | Mutating-gate load-bearing (opt-in `mutating_allowed` + env gate + no-retry de no-idempotentes, `MarketDataMutationNotAllowedError`) construido PRIMERO; symbols write (`POST /symbols`, `POST /symbols/batch`, `PATCH /symbols/{id}`) es la primera superficie que lo ejercita. Dual sync/async vía `_core.py`. |
| 26    | ?     | Not started | MUT-MD-02 | Calendar write (`PUT`/`DELETE /calendar/config`, `POST /calendar/config/preview`, `POST /calendar/holidays`, `DELETE /calendar/holidays/{day}`); `confirm` guardrail default False; depende del gate de Phase 25. |
| 27    | ?     | Not started | LIVE-MUT-01 | Verificación en vivo destructiva-pero-segura contra develop (create→verify→revert, identificadores dedicados), revalida idempotencia DM-03, fixes in-cycle sync/async. Depende de 25 + 26. |
| 28    | ?     | Not started | PUB-MUT-01 | Release prep + publish `market-data-client-v0.3.0` (minor bump no-breaking). Depende de 27. |
| Phase 25 P01 | 10 | 3 tasks | 7 files |
| Phase 25 P02 | 4min | 2 tasks | 4 files |
| Phase 25 P03 | 7min | 2 tasks | 7 files |
| Phase 28 P01 | 12min | 3 tasks | 6 files |
| Phase 28 P02 | 69min | 3 tasks | 0 files |

**By Phase (v1.6 planned):**

| Phase | Plans | Status      | Requirements | Notes |
|-------|-------|-------------|--------------|-------|
| 29    | ?     | Not started | DEC-01 | **Load-bearing, PRIMERO** — decoder único de política observable copiado verbatim 6× (DT-03), walker por-campo como motor primario (evolución de `_coerce`, NO reemplazado), modo estricto por `ContextVar` desde `_ClientState`, `from_api` preservado (DT-05). Artefactos de fase obligatorios: decisión msgspec-dos-motores-vs-stdlib-only, D-lock de `Literal` en RESPONSE, tabla 3-way de semánticas de matriz, fix del `RedactingFilter` × 6, test de intactness 6-way, **corrida exploratoria de sizing con el walker** sobre `verification/snapshots/`. ~3× el scope naive (14/25 pitfalls aterrizan acá). |
| 30    | ?     | Not started | TYP-01 | `iol-client` tipado — `models.py` nuevo desde los schemas live ya capturados (`puntas` polimórfico resuelto), 16 firmas migradas + parsers de `_core.py`, `main_iol.py` a acceso por atributo (2 sitios reales, no 6). `mercado`/`plazo` quedan **`str`**; promoción a `Literal` diferida a F33 (DT-07). Paraleliza con Phase 31. |
| 31    | ?     | Not started | TYP-02, TYP-03 | 5 endpoints de ops tipados (higyrus `get_health`; market-data `get_health`/`get_health_feed`/`add_holidays`/`delete_holiday`) — **response-only**, con prueba de **request byte-idéntico** para las 2 mutaciones ya publicadas en v0.4.0 (no perturbar el mutating-gate) + `models.py`/`types.py` en los 6 paquetes. Paraleliza con Phase 30. |
| 32    | ?     | Not started | GATE-TYP-01 | Gate AST de superficie como **job de CI nuevo** (`verification/` nunca corrió en CI) + paridad sync/async no-vacua (lower bounds + fixture RED) + cierre de **D-16** reconciliando las **4** listas de enrollment en un commit atómico. Depende de 30 + 31; la mitad D-16 puede adelantarse a 29. |
| 33    | ?     | Not started | LIVE-TYP-01 | Drivers en modo estricto contra APIs reales; `Literal` cerrados con evidencia (iol input + los de RESPONSE pre-existentes de matriz); divergencias corregidas in-cycle espejadas sync/async; cycle closure PASS. **Scope provisional** hasta la corrida de sizing de F29. |
| 34    | ?     | Not started | PUB-TYP-01 | Releases sólo de los paquetes cuya superficie cambió; iol 0.2.0 → **0.3.0** source-breaking con callout (DT-08); `uv.lock` global refrescado **una sola vez**; ops irreversibles detrás de doble checkpoint humano independiente (precedente D-18). |
| Phase 29 P01 | 24 | 3 tasks | 3 files |
| Phase 29 P02 | 11min | 3 tasks | 6 files |
| Phase 29 P03 | 9min | 2 tasks | 7 files |
| Phase 29 P04 | 12min | 2 tasks | 1 files |
| Phase 29 P05 | 11min | 3 tasks | 11 files |
| Phase 29 P06 | 16min | 3 tasks | 11 files |
| Phase 29 P07 | 22min | 2 tasks | 20 files |
| Phase 29 P08 | 9min | 2 tasks | 2 files |
| Phase 29 P09 | 24min | 2 tasks | 3 files |
| Phase 29 P10 | 15min | 2 tasks | 2 files |
| Phase 30 P01 | 36min | 3 tasks | 12 files |
| Phase 30 P02 | 8min | 3 tasks | 10 files |
| Phase 30 P03 | 6min | 3 tasks | 13 files |
| Phase 30 P04 | 31min | 3 tasks | 7 files |
| Phase 30 P09 | 35min | 3 tasks | 2 files |
| Phase 30 P10 | 6min | 2 tasks | 3 files |
| Phase 30 P11 | 8min | 2 tasks | 1 files |
| Phase 30 P12 | 6min | 3 tasks | 2 files |
| Phase 30 P13 | 6min | 2 tasks | 1 files |
| Phase 31 P01 | 14min | 2 tasks | 2 files |
| Phase 31 P02 | 95min | 2 tasks | 12 files |
| Phase 31 P03 | 52min | 3 tasks | 10 files |
| Phase 31 P04 | 47min | 3 tasks | 15 files |
| Phase 31 P05 | 27min | 3 tasks | 10 files |
| Phase 32 P01 | 9min | 3 tasks | 4 files |
| Phase 32 P02 | 7min | 3 tasks | 3 files |
| Phase 32 P03 | 4min | 1 tasks | 0 files |
| Phase 32 P04 | 7min | 2 tasks | 3 files |
| Phase 32 P05 | 7min | 2 tasks | 4 files |
| Phase 32 P06 | 21min | 3 tasks | 5 files |
| Phase 33 P01 | 28min | 3 tasks | 7 files |
| Phase 33 P02 | 15min | 2 tasks | 2 files |
| Phase 33 P03 | 14min | 2 tasks | 2 files |
| Phase 33 P04 | 15 min | 2 tasks | 1 files |
| Phase 33 P05 | 16min | 3 tasks | 6 files |
| Phase 33 P06 | 12min | 2 tasks | 5 files |
| Phase 33 P07 | 42min | 3 tasks | 19 files |
| Phase 34 P01 | 10 min | 3 tasks | 11 files |
| Phase 34 P02 | 14 min | 3 tasks | 1 files |
| Phase 34 P03 | 5 min | 3 tasks | 1 files |

**By Phase (v1.7 planned):**

| Phase | Plans | Status      | Requirements | Notes |
|-------|-------|-------------|--------------|-------|
| 35    | ?     | Not started | NOBJ-01, NOBJ-02 | **Load-bearing, PRIMERO** y única fase transversal — `__bool__`/`empty()` en las 4 jerarquías de base (`SafeModel` de higyrus/iol/market-data + `_SafeModel` de matriz) copiadas verbatim a los 6 paquetes, más la nueva disposición del walker `_decode` (null legítimo sobre eslabón no-opcional → vacío **sin** divergencia; wrong-type sigue divergiendo y sigue fatal en strict). **Cero cambios de superficie pública**: las suites de los 6 paquetes pasan sin editar un test. Los 4 gates de v1.6 verdes, con `check_decode_intactness.py` reduciendo las 5 copias a un único hash canónico nuevo. Incluye el test de que las `@property` alias son invisibles a `get_type_hints()` (retira el riesgo antes de 36-38). |
| 36    | ?     | Not started | NOBJ-MD-01, NOBJ-MD-02 | El disparador del milestone. `MarketDataEntries` + `BookLevel` + `EntryValue` (copia local del patrón matriz, no-shared-code) con alias D-NO-05; `market_data: dict[str, Any] \| None` → modelo Null Object; `entries` de vuelta a `list[str]` default `[]` (revoca el widening de la Fase 33, SC-2); fila no-data expresada por veracidad + `note`; baja de `_mapping_value`/`_apply_mapping_policy` sin mover el hash de `_decode.py`. Bump breaking. Paraleliza con 37 y 38. |
| 37    | ?     | Not started | NOBJ-MTZ-01, NOBJ-MTZ-02 | `tickPriceRanges`, `AccountReport.report`/`detailedAccountReports`/`portfolio` tipados con **procedencia declarada por campo** (baseline / captura / modelo mínimo) — matriz sigue bloqueado para vivo por D-MATZ-33 (`LIVE-MATZ-33`), que **no se rodea**; exención única y documentada `UnknownFrame.raw`; alias compartidos por REST y frames WS (daemon thread incluido). Paraleliza con 36 y 38. |
| 38    | ?     | Not started | NOBJ-IOL-01, NOBJ-AUD-01 | `Cotizacion.puntas` → `list[Punta]` default `[]` y `Titulo.puntas` → `Punta` Null Object (espejado sync/async, snapshot de superficie regenerado, ruptura en el README de iol); más el **censo con disposición por campo** de higyrus/ámbito/wallets — cero filas sin disposición — cerrado con el grep del plan fuente reportado con comando y salida. Paraleliza con 36 y 37. |
| 39    | ?     | Not started | LIVE-NOBJ-01 | Cadenas profundas reales en sync + async por los drivers `main_*.py`. **Arranca con dos bloqueos heredados**: `LIVE-HIGY-33` (DNS) y `LIVE-MATZ-33` (política) → se registran `SKIPPED` con causa medida y destino nombrado, nunca cero. Divergencias corregidas in-cycle con espejo + regresión mockeada; censo contrastado contra el de la Fase 33 declarando cuántas divergencias bajaron **por la política Null Object** y cuántas por corrección. Depende de 36 + 37 + 38. |
| 40    | ?     | Not started | PUB-NOBJ-01 | Releases sólo de los paquetes cuya superficie cambió, bump breaking + callout + **tabla de migración vieja→nueva**; `uv.lock` refrescado una sola vez; CI asertado por conteo; merge commit real (nunca squash); tags anotados; verificación post-publicación instalando desde el wheel público. **Doble gate humano independiente** (D-08/D-18), nunca colapsado ni auto-aprobado pese a `auto_advance: true` + `mode: yolo`. Depende de 39. |
| Phase 35 P01 | 7min | 3 tasks | 3 files |
| Phase 35 P02 | 18min | 2 tasks | 1 files |
| Phase 35 P03 | 14min | 2 tasks | 6 files |
| Phase 35 P04 | 15 min | 3 tasks | 6 files |
| Phase 35 P05 | 10min | 2 tasks | 13 files |
| Phase 36 P01 | 15min | 3 tasks | 2 files |
| Phase 36 P02 | 55min | 3 tasks | 7 files |
| Phase 36 P03 | 18min | 3 tasks | 3 files |
| Phase 37 P01 | 10min | 3 tasks | 3 files |
| Phase 37 P02 | ~11 min | 2 tasks | 5 files |
| Phase 37 P03 | ~22 min | 3 tasks | 6 files |
| Phase 37 P04 | 34min | 2 tasks | 2 files |
| Phase 37 P05 | ~8 min | 2 tasks | 2 files |
| Phase 38 P01 | 6min | 3 tasks | 4 files |
| Phase 38 P02 | 7min | 3 tasks | 2 files |
| Phase 38 P03 | 8min | 2 tasks | 2 files |
| Phase 38 P04 | 8min | 2 tasks | 1 files |
| Phase 39 P01 | 42min | 3 tasks | 6 files |
| Phase 39 P02 | 38min | 3 tasks | 4 files |
| Phase 39 P03 | 8min | 3 tasks | 9 files |
| Phase 39 P04 | 3min | 2 tasks | 3 files |
| Phase 39 P05 | 6min | 2 tasks | 3 files |
| Phase 39 P06 | 6min | 3 tasks | 5 files |
| Phase 39 P07 | 1h 25m | 3 tasks | 23 files |
| Phase 39 P08 | 22m | 3 tasks | 2 files |
| Phase 40 P01 | 35m | 4 tasks | 20 files |
| Phase 40 P02 | 7min | 3 tasks | 0 files |
| Phase 40 P03 | 4min | 3 tasks | 0 files |

**By Phase (v1.8 planned):**

| Phase | Plans | Status      | Requirements | Notes |
|-------|-------|-------------|--------------|-------|
| 41    | ?     | Not started | NYQ-01 | **Primera y sola** — audita el árbol **congelado** de v1.7 (Phases 35-39) con `/gsd-validate-phase`; disposición de 3 vías por hallazgo (`VERIFIED-NOW` / `VERIFIED-HISTORICALLY` / `NOT-VERIFIABLE-RETROACTIVELY`), nunca un flip mecánico de `nyquist_compliant`. Cualquier cambio de fuente de v1.8 antes de cerrarla atribuye los hallazgos al árbol equivocado. Locks generados quedan inertes-por-escrito y su enrolamiento en CI se rutea a la Phase 45. |
| 42    | ?     | Not started | LIVE-01, LIVE-02 | **P1 = portar el `_VENUE_ALLOWLIST`** por igualdad exacta de hostname de `main_matriz.py` a `scripts/literal_census_33.py` (hoy sigue en substring-match pre-Phase-39 — el backlog lo decía "listo", verificado falso en HEAD — y saltearía en silencio contra `bbsa`). Checkpoint humano bloqueante antes de tráfico; `verification/mutation_gate.py` byte-idéntico. higyrus: veredicto **medido** (resuelto o `SKIPPED` con causa re-confirmada), nunca cero. Produce además la lectura fresca del wire que consume la Phase 43. |
| 43    | ?     | Not started | SHAPE-01, HARN-02 | Un solo cambio de `market_data_client/models.py`: tabla de disposición **campo por campo** (`alias aditivo` / `remover` / `agregar` / `mantener`) contra la lectura fresca de la Phase 42 — `Instrument.marketId` como **alias aditivo** (precedente D-22), nunca rename — más las 5 claves `extra` tipadas sin flip `extra`→`missing`. Fixtures **re-derivadas** con aserción fixture-⊆-baseline. **No** bumpea ni publica. |
| 44    | ?     | Not started | PUB-01 | Release `market-data-client` **0.7.0**: 4 sitios de versión, `uv.lock` una sola vez, `release.yml` sin editar, changelog + **tabla de migración** vieja→nueva, tag anotado sobre merge commit real, verificación post-publicación instalando desde el wheel público. Los dos gates escritos literalmente `gate="blocking-human"` — la forma `gate="blocking"` ya se auto-aprobó dos veces. Fase propia por precedente lockeado (v1.5 P28 / v1.6 P34 / v1.7 P40). |
| 45    | ?     | Not started | HARN-01, HARN-03, HARN-04 | Aterriza **después** de las corridas en vivo (decisión de orden explícita). HARN-01 no es un kwarg: título content-addressed o dedupe intra-run + reordenar `_next_fid()` respecto del chequeo + **test de falsificación**; nunca relajar `test_finding_count_consistency.py`. HARN-04 se cierra con decisión escrita y fechada (reparar **con** enrolamiento en CI, o aceptar la deuda). Edit consolidado único de la allowlist de `ci.yml`. |
| Phase 41 P01 | 8min | 3 tasks | 2 files |
| Phase 41 P02 | 22min | 2 tasks | 1 files |
| Phase 41 P03 | 13 min | 2 tasks | 1 files |
| Phase 41 P04 | 24min | 2 tasks | 1 files |
| Phase 41 P05 | 19min | 2 tasks | 1 files |
| Phase 41 P06 | 21min | 2 tasks | 1 files |
| Phase 41 P07 | 23min | 3 tasks | 3 files |
| Phase 42 P01 | 11min | 3 tasks | 3 files |
| Phase 42 P02 | 4min | 2 tasks | 1 files |
| Phase 42 P03 | 6min | 2 tasks | 2 files |
| Phase 42 P04 | 7min | 3 tasks | 4 files |
| Phase 42 P05 | 3min | 2 tasks | 8 files |
| Phase 42 P06 | 9min | 2 tasks | 5 files |
| Phase 43 P01 | 15min | 3 tasks | 7 files |
| Phase 43 P02 | 6min | 3 tasks | 4 files |
| Phase 43 P03 | 11min | 3 tasks | 4 files |
| Phase 44 P01 | 6 min | 3 tasks | 4 files |
| Phase 45 P01 | 2min | 3 tasks | 3 files |
| Phase 45 P04 | 15 min | 2 tasks | 4 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [v1.8 Roadmap]: Phase numbering CONTINUES from v1.7 (última fase = 40) — v1.8 arranca en **Phase 41** (no resetea). Sequential `phase_naming` per config.json.
- [v1.8 Roadmap]: **5 fases (41-45)** pese a granularity `coarse`, y sin compresión disponible: la 41 no se puede fusionar con ninguna porque audita el árbol que las otras modifican; la 42 no se puede fusionar con la 43 porque la 43 consume su evidencia; la 43 y la 44 no se pueden fusionar por el precedente lockeado de release; y la 45 no se puede adelantar por la decisión de orden harness-vs-vivo. Las 5 fases salen de restricciones estructurales, no de granularidad. 9 requisitos → 5 fases: 41=1, 42=2, 43=2, 44=1, 45=3.
- [v1.8 Roadmap]: **La Phase 41 va primera y sola porque audita historia congelada.** `/gsd-validate-phase` sobre las Phases 35-39 tiene que correr contra el árbol de v1.7 tal como se shippeó; cualquier cambio de fuente de v1.8 antes de ese punto hace que los hallazgos queden atribuidos al árbol equivocado. No es preferencia de orden: es la condición de validez del artefacto. Y ningún `nyquist_compliant` se flippea mecánicamente — sólo donde la disposición es `VERIFIED-NOW` re-ejecutada.
- [v1.8 Roadmap]: **El gate de venue de `scripts/literal_census_33.py` está STALE y el backlog lo sobreestima.** La entrada `LIVE-MATZ-33` afirmaba que el script "ya tiene el gate listo para correr contra `bbsa`"; verificado **falso en HEAD** por research — sigue en substring-match pre-Phase-39 (`if "remarkets" not in base:`) y saltearía **en silencio** contra el sandbox ya desbloqueado. Portar el `_VENUE_ALLOWLIST` por igualdad exacta de hostname de `main_matriz.py` es la **primera** tarea de la Phase 42, es relevante para seguridad, y va detrás de un checkpoint humano bloqueante antes de cualquier tráfico. Un `endswith`/`in` "rápido" reintroduce la debilidad de spoofing que el D-02 de la Phase 39 removió. La corrección del texto del backlog viaja en el mismo commit.
- [v1.8 Roadmap]: **Decisión de orden explícita (research la dejó abierta): HARN-01 aterriza DESPUÉS de las corridas en vivo de la Phase 42.** HARN-01 cambia *qué se registra*; el comportamiento de hoy es ruidoso (22 bloques de drift para 8 snapshots) pero **no es lossy**. Correr en vivo sobre el harness conocido-lossless y recién después cambiar el dedupe mantiene el peor caso en "ledger inflado" en vez de "divergencia perdida", que es la clase de fallo que el proyecto existe para eliminar. Por eso la limpieza del harness es la Phase 45 y no la 42.
- [v1.8 Roadmap]: **HARN-01 no es un kwarg.** `idempotent_by_title=True` sobre la rama de schema drift —cuyo título es endpoint-scoped y libre de contenido— haría que toda divergencia *posterior y distinta* sobre ese mismo endpoint se tragara para siempre; y `_next_fid()` se llama **antes** del chequeo de dedupe, así que un no-op quema un fid y rompe el invariante que `verification/test_finding_count_consistency.py` pinnea. Requiere título content-addressed (o dedupe intra-run) + reordenar la asignación de fid + un **test de falsificación**. Nunca relajar la aserción de conteo.
- [v1.8 Roadmap]: **SHAPE-01 se corrige contra la lectura fresca de la Phase 42, no contra el baseline congelado del 2026-07-31** — ese es el motivo de que vivo vaya antes que shape. La disposición es **campo por campo** (`alias aditivo` / `remover` / `agregar` / `mantener`), con `Instrument.marketId` como alias aditivo por el precedente D-22 de `Symbol.marketId`, nunca un rename; y las fixtures se **re-derivan** de los baselines medidos con aserción fixture-⊆-baseline, nunca se renombran para que sigan pasando.
- [v1.8 Roadmap]: **El release nunca comparte fase con el trabajo que lo habilita** (precedente lockeado v1.5 P28 / v1.6 P34 / v1.7 P40). La Phase 44 existe separada de la 43 precisamente porque la co-locación es donde el bug de autoría del gate ya se coló **dos veces** — los checkpoints se escribieron `gate="blocking"` en vez de `gate="blocking-human"` y sólo la prosa del plan evitó la auto-aprobación bajo `auto_advance: true` + `mode: yolo`. En la Phase 44 la autoría del gate se verifica **en el propio archivo de plan**, no sólo en el comportamiento observado.
- [v1.8 Roadmap]: **HARN-04 no admite "reparar sin enrolar".** Reparar los dos archivos rotos de `verification/` sin meterlos en el allowlist explícito de `ci.yml` garantiza el re-rot — son rot invisible por construcción desde la Phase 15 precisamente porque `verification/` nunca corrió en CI. Las dos formas admisibles son: reparar **con** presupuesto declarado por adelantado **y** enrolamiento, o aceptar formalmente la deuda con su razón escrita. El gemelo de mypy sobre `verification/` (43-44 errores, 8-9 archivos) queda fuera de alcance por escrito.

- [v1.7 Roadmap]: Phase numbering CONTINUES from v1.6 (última fase = 34) — v1.7 arranca en **Phase 35** (no resetea). Sequential `phase_naming` per config.json.
- [v1.7 Roadmap]: **6 fases (35-40)** pese a granularity `coarse`, con una compresión deliberada respecto del plan fuente: las Fases D (iol) y E (auditoría del resto) de `.future_plans/api-tipada-null-objects.md` se **funden en la Phase 38** — iol son dos campos y la auditoría es un barrido sobre tres paquetes casi limpios; ninguna de las dos sostiene una fase propia. La Fase F del plan fuente se **parte en 39 (vivo) + 40 (release)** siguiendo el precedente de v1.4/v1.5/v1.6: el release tiene doble gate humano y no puede compartir fase con la verificación que lo habilita. 10 requisitos → 6 fases, 2:1 salvo 39 y 40.
- [v1.7 Roadmap]: **Phase 35 es load-bearing y la única fase transversal** — es la que toca las 4 jerarquías de base y las 5 copias verbatim de `_decode.py`, y es la única que puede romper los 4 gates de CI de v1.6 de un golpe. Entrega política y capacidad con **cero** cambios de superficie pública (suites de los 6 paquetes verdes sin editar un test); si algo de la superficie se mueve ahí, el scope se corrió.
- [v1.7 Roadmap]: **Phases 36, 37 y 38 paralelizan** (las tres dependen sólo de la 35 y tocan paquetes disjuntos: market-data / matriz / iol+higyrus+ámbito+wallets). Phase 39 depende de las tres; Phase 40 depende de la 39.
- [v1.7 Roadmap]: La restricción **no-shared-code (DT-03)** sigue vigente y es lo que hace cara a la Phase 35: cada cambio a la base `SafeModel` y al walker se **copia verbatim** por paquete, y `tools/check_decode_intactness.py` lo verifica por hash. No hay atajo por `market-libs-core` — está listado en Out of Scope.
- [v1.7 Roadmap]: La cobertura en vivo de la **Phase 39 arranca con dos bloqueos heredados de la Phase 33** que ninguna fase resuelve desde adentro: `LIVE-HIGY-33` (el host de higyrus no resuelve por DNS desde esta red) y `LIVE-MATZ-33` (el assert de política remarkets-only D-MATZ-33 de `main_matriz.py`, que **no se rodea** — la superficie de matriz incluye entrada de órdenes). El registro correcto es `SKIPPED` con causa medida y destino nombrado, nunca un cero que se lea como limpio (precedente D-13 / 33-05).
- [v1.7 Roadmap]: La Phase 39 debe declarar **cuántas divergencias desaparecieron por la nueva política Null Object** (colapso sin registro) frente a cuántas por corrección real, contrastando contra el censo de la Fase 33 y el piso ratificado de `29-SIZING.md`. Sin esa separación, la baja de números de la política se lee como un falso limpio — exactamente lo que v1.6 existió para eliminar.
- [v1.7 Roadmap]: **La Fase 33 (SC-2, checkpoint 33-07 "fix-shape-now") queda formalmente revocada sólo donde rompe cadenas**: `MarketDataSnapshot.entries` y `.market_data` vuelven a ser no-opcionales en la Phase 36, mientras que `.staleness_seconds` y `.note` **se quedan** `| None` por ser hojas escalares (D-NO-03). La revocación es parcial y por rol del campo (eslabón vs hoja), no un rollback del checkpoint.

- [v1.6 / Phase 29 P04 — **D-lock (a) FIRMADO, NO-GO**]: **msgspec queda afuera; stdlib-only, un solo motor (el walker con caché de hints).** Firmado `no-go-stdlib-only` por **sebadlf** el **2026-08-19** en `29-DLOCK-MSGSPEC.md`. Criterio: **presupuesto absoluto de 100 ms** para el decode de una respuesta de catálogo de referencia de 5.000 filas medida sobre el arm B (el walker ya shippeado) — **no** un ratio, porque no existe requisito de throughput contra el cual un ratio sea decidible. Medido: **19,37 ms** (`matriz.Instrument` end-to-end) y **20,69 ms** (`market_data.Symbol`) → 4,8× de holgura, la condición de GO (que el arm B se pase del presupuesto) nunca se cumplió. La ventaja real de msgspec sobre el arm B es de **13-24×** (no 123×: ese número sale de comparar contra el arm A sin caché y fabricaría un GO por una mejora que el `lru_cache` de la Plan 29-02 ya entrega gratis). Rechazado igual porque: no puede implementar el modo observable, **violaría el lock D-09 de RESPONSE-`Literal`** firmado en esta misma fase (msgspec valida pertenencia a `Literal` y levanta excepción), descarta claves extra en silencio, reporta un error por decode e ignora el rename de campos en dataclasses del stdlib (`market_data.Symbol`). **Consecuencia:** los 6 wheels siguen siendo un closure 100% puro-Python, `uv.lock` no se toca, el set de releases de la Phase 34 queda como estaba, y las Phases 30-34 avanzan con un único motor de decode. Revisitar exige un requisito de throughput declarado: sólo un presupuesto por debajo de ~20,7 ms a 5.000 filas daría vuelta el veredicto.
- [v1.6 Roadmap]: Phase numbering CONTINUES from v1.5 (última fase = 28) — v1.6 arranca en **Phase 29** (no resetea). Sequential `phase_naming` per config.json.
- [v1.6 Roadmap]: **6 fases (29-34)** pese a granularity `coarse` — la estructura del plan fuente (`.planning/future-plans/tipado_homogeneo.md`) queda intacta porque los cuatro researchers convergieron independientemente en los mismos límites de fase y el mismo orden load-bearing-first. La corrección del research es de **scope y contenido dentro de la Phase 29**, no de cantidad ni orden de fases. 7 requisitos → 6 fases, 1:1 salvo Phase 31 (TYP-02 + TYP-03).
- [v1.6 Roadmap]: **Phase 29 es load-bearing y ~3× el scope naive de "copiar un decoder"** — 14 de 25 pitfalls aterrizan ahí. Varios D-locks de los que dependen 30-34 deben ser **artefactos explícitos de la fase**: (a) msgspec dos-motores vs stdlib-only un-motor; (b) los campos de RESPONSE **nunca** se cierran como `Literal` en este milestone (alcanza retroactivamente a `CFICode`/`MarketId`/`OrderType`/`Currency` de matriz); (c) tabla 3-way de semánticas (matriz **no** es copia verbatim de higyrus/market-data: missing → `None`, sin `slots`, `empty()`); (d) contrato de agregación anti-log-spam; (e) fix del `RedactingFilter` en las 6 copias.
- [v1.6 Roadmap]: El **scope de la Phase 33 es provisional** hasta la corrida exploratoria de sizing del final de la Phase 29 — que debe usar el **walker por-campo** sobre `verification/snapshots/`, nunca un pase strict de msgspec (fail-fast + `json.loads` acepta NaN/Infinity → sub-cuenta por construcción). El número reportado es un **piso** (`≥ N`), no una estimación.
- [v1.6 Roadmap]: Phases 30 y 31 **paralelizan** (ambas dependen sólo de la Phase 29). Phase 32 depende de 30 + 31 (aunque la mitad D-16 es independiente y puede adelantarse a 29); Phase 33 depende de 30/31/32; Phase 34 depende de 33.
- [v1.6 Roadmap]: Phase 34 refresca el `uv.lock` global **exactamente una vez** para todos los bumps (corrección del research) y mantiene las ops irreversibles (merge, push de tag) detrás de **dos checkpoints humanos independientes, nunca colapsados** (precedente D-18 de v1.5).
- [v1.5 Roadmap]: Phase numbering CONTINUES from v1.4 (last phase = 24) — v1.5 starts at **Phase 25** (does NOT reset). Sequential `phase_naming` per config.json. Granularity `coarse` → 4 phases, 1:1 con requisitos salvo Phase 25 (GATE-MD-01 + MUT-MD-01 combinados: el gate es load-bearing y symbols es la primera superficie que lo ejercita end-to-end).
- [v1.5 Roadmap]: 4 fases lineales (25 gate+symbols → 26 calendar → 27 live verification → 28 publish). Phase 25 construye el mutating-gate PRIMERO (mitigación primaria del riesgo central = mutación accidental); Phases 26 y 27 dependen del gate. NO paralelizan: 25 es prerequisito estricto de 26, y 27 necesita ambas superficies (25 + 26).
- [v1.5 Roadmap]: Verificación en vivo (Phase 27) es **destructiva** a diferencia de v1.4 (solo lectura) → obligatorio cleanup + identificadores de prueba dedicados (DM-06); nunca toca config real sin `confirm`. La idempotencia por-endpoint (DM-03) se revalida en vivo antes de confiar el retry-behavior. Plan fuente: `.planning/future-plans/market_data_mutations.md`.
- [v1.4 Roadmap]: Phase numbering CONTINUES from v1.3 — v1.3 allocated Phases 18-19 (19 dropped), so v1.4 starts at **Phase 20** (avoids collision with the dropped Phase 19 reference). Sequential `phase_naming`.
- [v1.4 Scope]: Paquete `market-data-client` (import `market_data_client`) — nombre con sufijo `-client` OBLIGATORIO por el regex de `release.yml`. Solo lectura; mutaciones + streaming SSE + disk token cache + JWT signature validation diferidos a v1.5+ (REQUIREMENTS § v2). Auth = Auth0 client_credentials. Plan fuente: `.future_plans/market_data.md`.
- [v1.4 Roadmap]: 5 fases lineales (20 scaffold+auth → 21 market data → 22 reference data → 23 live verification → 24 publish); Phases 21 y 22 pueden paralelizar (ambas dependen solo de 20). 6 requisitos, 1:1 con fases salvo Phase 20 (AUTH-MD-01 + CORE-MD-01).

<details>
<summary>v1.3 decisions (milestone closed 2026-07-03, archived for reference)</summary>

- [v1.3 Roadmap]: Phase numbering CONTINUES from v1.2 (last phase = 17) — v1.3 starts at Phase 18 (does NOT reset). Sequential `phase_naming` per config.json.
- [v1.3 Roadmap]: Spike-gated conditional structure mirrors v1.2 (Phase 12 spike + conditional Phase 16). Phase 18 (SPIKE-006) is spike-before-plan and the guaranteed deliverable; Phase 19 (REFAC-06) is CONDITIONAL — DROPPED entirely if Phase 18 returns NO-GO, in which case REFAC-06 is shelved permanently per D-NOGO-01 and the milestone closes on the signed NO-GO.
- [v1.3 Roadmap]: The 3 GO-determining gate items are D-RIGOR-02 item 1 (byte-identical round-trip, no source migration), item 4 (ruff check clean incl. single-line import-order), item 6 (mocked suite green vs generated, no circular self-import) — all trace to the single unasync root cause (source-shape asymmetry). libcst must close all 3 for GO.
- [v1.3 Roadmap]: No standalone milestone-close / live re-verification phase. Per the in-cycle verification convention, byte-identical generated output means wire behavior is unchanged by construction; the D-RIGOR-02 item-1 + item-6 gates fold verification into Phase 19. Milestone kept tight (REFAC-06-only) — other v1.3 candidates (prod-vs-remarkets, ws_client live, token encryption) stay in backlog.
- [v1.3 Roadmap]: Matriz deny-list (`_token_store.py`/`_refresh_policy.py`/`_refresh.py`/`ws_client.py`) is OUT of codegen scope in BOTH phases — the spike CONFIRMS (sha256-byte-identical under MetadataWrapper), it does NOT renegotiate. Codegen applies ONLY to `client.py`/`aio.py` transport shells.
- [Phase 18]: SPIKE-006 001a: libcst closes mechanical asymmetries (items 4/5/7/9 PASS) but items 1/6 FAIL on content-absence (_validate_max_retries def + dotenv bootstrap absent from aio.py) — same SPIKE-005 root cause; aggregate NO-GO
- [Phase 18]: Item-9 purity scoped to transformer CLASSES; impure driver owns cross-module/scope orchestration (flagged for operator ratification in Plan 03 DECISION.md)
- [Phase 18 / 18-03]: SPIKE-006 **signed NO-GO** (sebadlf, 2026-07-03) — 7 PASS / 3 FAIL (items 1/3/6) → strict D-04 NO-GO. libcst is a partial gain over unasync (closes item 4 `ruff check` / ASYNC1xx) but cannot cross the content-absence boundary without a forbidden source migration (D-02). Two independent tools now reach the same NO-GO for the same root cause.
- [Phase 18 / 18-03]: **REFAC-06 PERMANENTLY shelved; Phase 19 DROPPED**; duplicate `client.py`/`aio.py` transport shells accepted as a structural feature. v1.3 milestone closes on the signed NO-GO (run `/gsd-complete-milestone`).

</details>

- [Phase 21-02]: drop_none copiado verbatim en un _params.py nuevo (sin import cross-package); format_date/format_bool omitidos (bool wire-encoding diferido a Phase 23, D-07).
- [Phase 21-02]: parse_latest_response retorna list[MarketDataSnapshot] (provisional) — el batch POST retorna varios simbolos; la forma single-snapshot del GET se reconcilia en Phase 23 via from_api tolerance.
- [Phase ?]: [Phase 21-03]: with_options threads req.extensions['max_attempts']=_max_retries+1 in BOTH _request and _send_auth_request (D-08 load-bearing); mirrors iol, _validate_max_retries copied verbatim (no cross-package import).
- [Phase ?]: [Phase 21-03]: sync read methods + module shims added in client.py only (__init__ re-export deferred to respect files_modified scope); retry count asserted by outgoing-request count, 401 re-auth by token-POST count.
- [Phase 21]: Async with_options mirrors sync as a shared-view clone; per-call max_attempts threaded via req.extensions in both _request and _send_auth_request (load-bearing).
- [Phase 21]: D-09: authenticated async header build spreads spec.headers first and Authorization token last so the fresh token always wins over a decoy spec header.
- [Phase ?]: Phase 22-01: reference SafeModels carry no received_at (D-05); calendar/config is the single non-collection parser with empty-body from_api(None) fallback (D-07)
- [Phase 22]: 22-02: 5 sync + 5 async reference methods dispatch through Plan 01 _core builders/parsers; get_calendar_config returns a single CalendarConfig (D-07), the other four return list[Model]
- [Phase ?]: [Phase 24-01]: Committed the pre-staged uv.lock market-data-client workspace-member registration (D-03/D-11), validated via uv sync --frozen + uv lock --check (both exit 0), not regenerated.
- [Phase ?]: [Phase 24-01]: Left global mypy files, importlinter root_packages, and CI typecheck per-package loop untouched (scope_decisions deferrals) — coverage gaps not CI failures; new package pytest+coverage runs via the matrix edit so CI stays green.
- [Phase ?]: [Phase 24-02]: Merged PR #5 with a true merge commit (gh pr merge --merge) so tag market-data-client-v0.1.0 sits on the distinct merge commit 1ea655d (D-10); release.yml unedited (D-02) matched the tag and published the GitHub Release with wheel + sdist (PUB-MD-01).
- [Phase ?]: GATE-MD-01: mutation gate is IO-free exact-hostname refuse-by-default on both shells; expected_host field None disables only the host leg
- [Phase ?]: 25-02: NewSymbol emits snake_case market_id wire key (not camelCase marketId) per source-plan schema; confirmed live Phase 27 (A2)
- [Phase ?]: 25-02: NewSymbols 1-500 batch guard raises plain ValueError in __post_init__, not a MarketData* error (D-11)
- [Phase ?]: 25-02: all three symbols write builders idempotent=True (DM-03); PATCH symbol_id interpolated raw, percent-encoding deferred to Phase 27 (D-08)
- [Phase ?]: [Phase 28-01]: Release publicada como 0.4.0 (minor), no 0.3.2 ni 1.0.0 — el diff sin publicar agrega 13 nombres públicos nuevos, un patch bump violaría semver para todo pin ~=0.3.1 (D-01)
- [Phase ?]: [Phase 28-01]: CalendarDay se documenta en el changelog v0.4.0 en vez de blindarse con compat shim — D-03 rechazó el shim de aliases deprecados; el callout ES la mitigación lockeada. Riesgo residual D-13 aceptado (nunca auditado independientemente)
- [Phase ?]: [Phase 28-01]: Los strings de título 'Phase 28: Release prep + publish v0.3.0' quedan textuales en ROADMAP; solo se re-apuntó el target de release adentro — la tooling GSD resuelve el directorio de fase desde ese string
- [Phase ?]: [Phase 28-01]: D-16 (market-data-client ausente de mypy files / import-linter root_packages / ci.yml:85) sigue diferido pero archivado en ROADMAP § Backlog 'Deferred to v1.6+' — gap de cobertura, no CI failure
- [Phase ?]: [Phase 28-01]: Branch publicada con fast-forward plano (behind=0, ahead=104); sin force flag y sin rebase/merge de origin/main — preserva los ~99 SHAs que los SUMMARY de Phases 25-27 cross-referencian (D-10, T-28-08)
- [Phase 28-02]: PR #10 mergeado a main con merge commit real 5d0825d (dos padres 7b0e0b2 + 0c1a382) via gh pr merge --merge; nunca --squash ni --rebase (D-11) — un squash orfanaría los ~106 SHAs que los SUMMARY de Phases 25-27 cross-referencian
- [Phase 28-02]: El gate de 15 checks se asertó POR CONTEO (15 filas / 15 pass / 0 no-pass / 2 market-data-client), nunca por ausencia de la palabra fail — pending, skipping y cancelled leen como verde bajo el chequeo negativo, y cancel-in-progress:true (ci.yml:20) hace cancelled alcanzable
- [Phase 28-02]: El merge corrió SOLO tras el 'approved' verbatim del operator (2026-08-01T22:13:53Z) en el checkpoint D-18a; main no tiene branch protection (protected:false, rulesets []), así que esa respuesta fue el único control de acceso sobre la operación irreversible
- [Phase 28-02]: Ningún tag ni GitHub Release se creó en 28-02 — D-18 exige dos gates independientes y el tag queda detrás del SEGUNDO checkpoint en 28-03; los gates no se colapsaron
- [Phase ?]: Phase 29 (signed sebadlf 2026-08-18): strict decode mode raises on missing/type/non_dict but NEVER on extra wire keys — vendor field growth stays informational (INFO) so Phase 33 strict driver runs are not broken by legitimate upstream additions
- [Phase ?]: Phase 29 (signed sebadlf 2026-08-18): RESPONSE fields are never closed as Literal in v1.6 — they decode as str, out-of-set values are reported not enforced; reaches retroactively to matriz's 9 types.py aliases; closing deferred to Phase 33 with a live census
- [Phase ?]: Phase 29: divergence record is six flat str keys (package, divergence, field_path, declared_type, observed_type, model) with NO occurrences counter; dedupe key is (model, field_path, kind) scoped per decode scope, never process-lifetime
- [Phase ?]: Phase 29: per-package from_api differences are DecodePolicy axes, never harmonized — no row of the 6-way semantics matrix is a bug to fix in this phase
- [Phase ?]: 29-03: configure(strict_decode=...) carries forward — an unrelated configure(base_url=...) must not silently reset a security-relevant opt-in
- [Phase ?]: 29-03: the generic record.__dict__ scan is a module-level _scan_record_dict inside one contiguous marker-delimited region, so Plan 09 hashes constants+helper+loop together
- [Phase ?]: 29-03: the decoder caplog sentinel literal carries no redaction marker, so its absence is evidence about the record contract rather than about _redact
- [Phase ?]: 29-05: MarketDataSnapshot's received_at exemption is implemented as a pre-processing hook (stamp written over the payload before the walk) PLUS a post-walk overwrite. The walker offers no field-exclusion hook and adding one would break the byte-identity D-02 requires across five copies.
- [Phase ?]: 29-05: market-data's _decode.py differs from the higyrus original in FIVE lines below 'from __future__', not four — the exception SYMBOL appears at both the import and the raise site. Plan 09's intactness normalizer must normalize the name, not just the import statement.
- [Phase ?]: 29-05: two comments inside the copied walker body still read 'higyrus' and were kept VERBATIM. Plan 09 should decide once, for all five copies, whether to normalize them rather than let each executor choose locally.
- [Phase ?]: 29-05: a plain threading.Thread provably sees the ContextVar DEFAULT, not the spawning thread's value — matriz's websocket daemon thread cannot inherit the REST mode and Plan 08 must bind it explicitly.
- [Phase 29]: 29-06: matriz's mapping axis (a dict-declared field falling back to {}) lives in models.py as a post-walk pass taking the walker's own sink, never as a walker branch — _decode.py stays byte-verbatim across the five copies (D-02)
- [Phase 29]: 29-06: an int arriving for a float-declared matriz field now widens to float (walk_field coerces before consulting scalar_passthrough) — the one observable delta outside the seven declared policy axes, pinned by a test rather than prevented
- [Phase 29]: 29-06: matriz has TWO decode bind sites, not one — Plan 03's 'no aio.py' note predates Phase 10 Plan 10-02's AsyncClient REST surface
- [Phase ?]: 29-07: The ContextVar name substitution changes _decode.py LINE COUNT in BOTH directions — iol_client collapses DECODE_SCOPE 3->1, ambito_financiero_client expands STRICT_DECODE 1->3, both forced by ruff format at the 100-col boundary. Plan 09's intactness normalizer must compare semantically or re-format both sides.
- [Phase ?]: 29-07: iol and ambito receive the walker before (iol, Phase 30) or without ever needing (ambito) a models module — the standalone-import property in a package with no models.py is the evidence that makes the verbatim-copy contract enforceable in the three packages that have one.
- [Phase ?]: 29-07: Decode fixture dataclasses live in the test files, never in src/ — a placeholder model in iol's src would have to be deleted in Phase 30, and one in ambito's would be permanently dead code on a published wheel.
- [Phase ?]: 29-08: research assumption A1 CONFIRMED by measurement on CPython 3.12.13 and 3.13.12 — contextvars.Context.run() raises 'already entered' on nested AND concurrent overlapping entry; writes inside a stored Context also persist across runs, which would break aggregation lock 6. The matriz ws daemon thread therefore gets the mode via an explicit bool snapshot + re-set() at on_open, not via copy_context().
- [Phase ?]: 29-08: matriz ws _handle_message opens a FRESH decode scope per frame (a frame is the WS analogue of one HTTP response). Binding the mode once at on_open is correct; sharing one scope for the whole connection is not — it is a process-lifetime dedupe set, which aggregation lock 6 rejects by name.
- [Phase ?]: [Phase 29-09]: Rule 8 (re-format normalized text with ruff format before hashing) is load-bearing for the decode intactness gate: disabling only that rule yields THREE distinct hashes across the five copies (iol and ambito reflow in opposite directions) — exactly the false positive Plan 07 predicted
- [Phase ?]: [Phase 29-09]: Comments stay inside the hashed decode body; ast.unparse rejected because it discards them. Settles Plans 05/07's open item on the two 'higyrus'-naming comments once for all five copies: keep verbatim, normalize nothing
- [Phase ?]: [Phase 29-09]: The decode-intactness gate runs in the CI lint job, never under verification/ — the test job passes an explicit package path that overrides pyproject's testpaths, so verification/ has never executed in CI
- [Phase ?]: [Phase 29-09]: wallets-client exempt from Phase 29 (no _state.py/_logging.py/_core.py/models.py, no Client class, module-level _request); Phase 31 bootstraps structure, Phase 32 D-16 settles enrollment. Every per-package Phase 29 criterion reads as five packages plus this documented exemption
- [Phase 29 / 29-10]: **Sizing floor RATIFICADO** — sebadlf firmó "ratified" el 2026-08-19 en `29-SIZING.md`. Los pisos por paquete quedan como **presupuesto declarado** de la fase de verificación en vivo (**Phase 33**): `higyrus-client ≥ 22`, `matriz-client ≥ 24`, `market-data-client ≥ 50`, `iol-client` N/A (sus modelos llegan en la Phase 30), `ambito-financiero-client` N/A — nunca 0, porque un 0 se lee como limpio y un falso-limpio es exactamente lo que este milestone existe para eliminar. Total modelado **≥ 96** (56 missing / 0 wrong_type / 32 extra / 8 non_dict). Es un **piso**, no una estimación: el corpus type-only es ciego a divergencias de valor (NaN/Infinity, valores fuera de conjunto en las 9 aliases de `types.py` de matriz, rango/formato, inconsistencia cross-field, colecciones heterogéneas — `schema_of` reduce por el PRIMER elemento), así que el margen de error apunta **sólo hacia arriba**. **La Phase 33 debe contrastar su censo en vivo contra estos números** — son directamente comparables sin traducción porque ambas corridas emiten el mismo record de 6 claves por el mismo walker con el mismo triple de dedupe `(model, field_path, kind)` (D-06, locks 1 y 5 del contrato de agregación). Si el censo los **excede**, eso exige un **re-scope explícito**: cada finding diferido se rutea a una **fase destino nombrada** con paquete y campo registrados; diferir a "más adelante" sin destino, o silenciar angostando el walker, no es una opción disponible. Los 5 hallazgos estructurales (S-1…S-5) quedan documentados para corrección in-cycle en la Phase 33 — el de mayor consecuencia es S-3 (matriz `Instrument.instrumentId` ausente en byCFICode/bySegment: `marketId`/`symbol` llegan aplanados, se reportan como `extra` y se **descartan**, y todo consumidor de `inst.instrumentId.symbol` lee vacío en cada fila, en silencio).
- [Phase ?]: Plan 30-01: DecodePolicy de iol re-ratificada (typed zeros); la confirmacion vive en el docstring de models.py
- [Phase ?]: Plan 30-01: to_dict() vive en SafeModel via dataclasses.asdict + cast(Any, self), no per-modelo
- [Phase 30]: Plan 30-02: _parse_list_or_raise levanta IOLAPIError(0, ...) ante una forma inesperada; jamas degrada a lista vacia (D-06/T-30-06)
- [Phase 30]: Plan 30-02: el envelope titulos se desenvuelve como paso raw-dict y no se modela; su ausencia sigue dando lista vacia a proposito (D-06)
- [Phase 30]: Plan 30-02: FA-05 resuelta a favor del schema — Titulo tiene 20 campos, no los 21 que dicen D-01 y RESEARCH
- [Phase ?]: 30-03: el desajuste de get_instruments se corrigio del lado del test (16 mocks re-mockeados a la lista top-level capturada), nunca aflojando el guard del parser a tolerancia dict-o-lista
- [Phase ?]: 30-03: las 16 firmas de iol-client devuelven modelos; el guard de forma levanta IOLAPIError ante un body no-lista y sigue aceptando la lista vacia
- [Phase 30]: Normalizar modelo→wire en la frontera hacia el harness de verificación (_as_wire), no en cada sitio de llamada — los payloads del probe de paridad llegan opacos y un dict crudo debe atravesar el adaptador intacto (30-04)
- [Phase 30]: Verificar no-vacuidad de los probes por aserción positiva, nunca por ausencia de findings — tres de los cuatro sitios de frontera reportan PASS precisamente cuando están rotos (30-04)
- [Phase 30]: El guard de tipo del precio se elimina, no se relaja — ultimoPrecio está declarado float y el walker lo garantiza; conservarlo implicaría no creerle al tipo que la fase entrega (30-04)
- [Phase 30]: Para los endpoints modelados de iol la señal autoritativa de drift pasa a ser el censo de divergencias, no el diff del snapshot de schema — to_dict() proyecta el drift afuera por construcción; carry-forward FA-09 a Phase 33 (30-04)
- [Phase 30]: 30-09: AD-30-09-01 en codigo — main_iol.py tiene UN solo renderer de excepciones (_redacted_exc) y los 32 sitios de reporte rutean por el; IOLDecodeError exento porque sus 4 atributos son type-only por T-29-36, y un status_code no-int se descarta por isinstance (WR-06)
- [Phase 30]: 30-09: el lock de regresion es un detector AST que toma un STRING de fuente, no un path — asi el audit de Phase 33 lo apunta a los otros cinco main_*.py sin reescribirlo; no-vacuidad probada con control positivo (3 lineas plantadas) y no-ruido con control negativo
- [Phase 30]: 30-10: AD-30-10-01 en código — el camino de crash de main_iol.py se cierra con un sys.excepthook nombrado instalado desde el guard __main__, NO con un try/except en main(): un try/except bindearía la excepción dentro de un ast.ExceptHandler (la forma que _raw_exception_renders recorre) y no cubriría nada levantado en tiempo de import
- [Phase 30]: 30-10: el hook usa traceback.print_tb (frames only); los helpers que toman la excepción o el triple de exc_info agregan la línea del mensaje y recorren __cause__/__context__, reintroduciendo la fuga. Costo aceptado: el mensaje de una causa encadenada (triage, no fuga)
- [Phase 30]: 30-10: el camino de crash es la única salida del driver que NO pasa por safe_print — safe_print escribe sólo a stdout y sin parámetro de archivo, y mezclar el crash en stdout corrompería la línea SUMMARY; registrado como bullet en las Reglas de seguridad del module docstring
- [Phase 30]: 30-10: _seed_fid_counter espeja main_market_data.py verbatim (global + max_existing_fid(_PKG)) y queda bajo lock AST de orden — write_findings < seed < primer probe; un seed definido pero no llamado falla el test
- [Phase ?]: 30-11: AD-30-11-01 split-by-role — el bypass del segundo renderer se cierra en el SITIO DE LLAMADA (delegación del nombre bindeado a cualquier callee fuera de {_redacted_exc,type,isinstance,getattr}, sin analizar al callee) y en la DECLARACIÓN (censo con gate de anotación). Un solo análisis whole-file no sirve: el snippet de fix de 30-REVIEW.md WR-02 devuelve [] contra este driver porque _redacted_exc no tiene repr/str ni .message/.args
- [Phase ?]: 30-11: status_code queda FUERA del set de atributos con fuga por decisión documentada en el comentario de la constante — WR-03 (22 lecturas inline en argumentos diff=) sigue abierto y no escalado; incluirlo fallaría el lock del driver sobre 22 sitios pre-existentes
- [Phase ?]: 30-11: el predicado del censo distingue RENDERIZAR de PASAR — entregar la excepción al renderer sancionado no cuenta, que es la única razón por la que _redacted_excepthook (anotado con tipo de excepción por 30-10) queda correctamente afuera
- [Phase ?]: 30-11: la aserción del censo es una igualdad contra el nombre sancionado, nunca contra una lista vacía — un censo que deja de detectar al primer renderer es tan roto como uno que no detecta al segundo (gate 14 lo demuestra)
- [Phase ?]: 30-12: AD-30-12-01: el camino de crash falla cerrado envolviendo el CUERPO DEL HOOK, no endureciendo _redacted_exc — el hook es el último frame antes del fallback de CPython, así que un guard ahí es provablemente suficiente sin importar qué sub-paso falló
- [Phase ?]: 30-12: _HOOK_RENDER_FAILED es una constante ESTÁTICA: en la rama de fallback la maquinaria que decide qué es seguro mostrar ya falló, así que nada derivado de exc puede asumirse seguro ahí
- [Phase ?]: 30-12: Los dos sinks del crash van en dos contextlib.suppress(BaseException) SEPARADOS, no en uno compartido — falsificado colapsándolos y observando que sólo el test dedicado falla
- [Phase 30]: AD-30-13-01: getattr queda sancionado como callee y se adjudica sobre su argumento de nombre de atributo; sacarlo del allow-list habria marcado la forma conforme del renderer sancionado — Una sola constante (_LEAKY_EXC_ATTRS) gobierna las dos escrituras de una lectura con fuga, asi que no pueden derivar; un nombre de atributo no constante se marca conservadoramente
- [Phase 30]: Las dos constantes de callees sancionados no se fusionan: _SANCTIONED_DELEGATES incluye getattr, _CENSUS_SANCTIONED_DELEGATES no — Contestan preguntas distintas; fusionarlas romperia el censo del propio renderer sancionado, cuyo cuerpo es un getattr mas un type()
- [Phase 31]: 31-01: AD-31-01-01 — el guard AST descubre METODOS DE CLASE, no ast.walk del modulo: los dos shells definen shims a nivel modulo con los MISMOS 8 nombres que delegan en el default Client y correctamente no llaman al gate
- [Phase 31]: 31-01: Hazard 1 resuelto — user-agent queda ADENTRO del set congelado con valor derivado de httpx.__version__; excluirlo cegaria al pin ante un header eliminado y pinear 0.28.1 enrojeceria el criterio 2 ante un bump de uv.lock ajeno a la fase
- [Phase 31]: 31-01: se congela una tupla de headers POR ENDPOINT, nunca una lista compartida — el DELETE no lleva Content-Length ni Content-Type (D-02)
- [Phase 31]: Uniform-structure gate reads its package roster from disk, never from a hardcoded list — A seventh package is gated automatically; an unresolvable src/ root and an empty packages/ scan are both PROBLEMS, never skips, so the gate cannot report green vacuously (T-31-06). RED was observed with all 7 missing paths before the files existed.
- [Phase 31]: wallets-client's new models.py and types.py import nothing beyond the __future__ flag — The package has no _decode.py; a cosmetic SafeModel would ImportError at package import and redden all 12 wallets CI matrix legs. The Phase 29 exemption stays load-bearing and check_decode_intactness.py was left byte-unedited (T-31-07, T-31-09).
- [Phase 31]: Phase 29's 'ambito has no models.py' test was restated, not suppressed — TYP-03 creates that file by design (D-11). The property the test guarded never depended on the file's absence but on ambito declaring no response models, so the assertion now pins zero ClassDefs, __future__-only imports, and an empty __all__ -- strictly more specific than the file-absence proxy it replaces.
- [Phase ?]: 31-03: higyrus get_health returns Health; the 204/empty-body carve-out resolves to Health.from_api(None), which emits one non_dict divergence and RAISES HigyrusDecodeError under strict_decode=True (measured, pinned by test)
- [Phase ?]: 31-03: CONTEXT D-03 corrected — main_higyrus.py health probes need no to_dict() site (they read raw wire); plan 31-04 must re-check each market-data driver site individually
- [Phase ?]: 31-03: SafeModel.to_dict() is copied byte-identically into each package's own base, never imported cross-package (C-2)
- [Phase ?]: 31-05: G-4 resuelto hacia TOLERANCIA — los dos parsers de calendar-write preservan la tolerancia T-26-13 como Model.from_api(None) en las cuatro ramas; un raise seria un cambio de comportamiento sobre mutaciones ya publicadas en v0.4.0 (diverge deliberadamente del raise de 31-04, que sirve LECTURAS)
- [Phase ?]: 31-05: MEDIDO — un int que llega a un campo declarado bool NO se ensancha: walk_field emite divergencia type (declared=bool/observed=int) y sustituye False (POLICY.scalar_passthrough=False). Contrasta con Phase 29 en matriz, donde un int para un campo float SI ensancha
- [Phase ?]: 31-05: los probes de delete_holiday ACEPTAN la ceguera a la deriva del snapshot (T-31-29) con carry-forward en ambos docstrings — un re-fire crudo es imposible (un segundo DELETE es legitimamente 404 Y ES la medicion D-19). Para Phase 33 la señal autoritativa es el CENSO de divergencias
- [Phase ?]: 31-05: CRITERIO 1 CERRADO — 5 endpoints de ops x 2 superficies x (metodo, shim) = 20 sitios devuelven una clase modelo; ningun retorno de mapping sin tipar sobrevive
- [Phase ?]: 32-01: los 6 errores comparison-overlap de matriz se arreglaron ensanchando la LECTURA a un intermedio tipado object, nunca re-asertando contra un typed zero sustituido — scalar_passthrough=True devuelve el valor de wire VERBATIM, asi que asertar un typed zero habria invertido la propiedad bajo test
- [Phase ?]: 32-01: assumption A1 de RESEARCH.md CONFIRMADA por ejecucion — los 33 errores cayeron con cambios en codigo de test unicamente; pyproject.toml quedo byte-identico y ninguna perilla de strictness se afloja (sin per-file-ignores, sin warn_unused_ignores off, sin --no-strict)
- [Phase ?]: 32-01: GATE-TYP-01 NO se marca completo — los seis planes de la Phase 32 cargan ese ID y este plan no entrega nada de su scope declarado; cerrarlo en el plan 1 de 6 seria una completitud falsa. Queda para el plan 32-06
- [Phase 32]: 32-02: una anotacion de retorno AUSENTE es violacion, no solo una que menciona `Any` — es lo que hace aparecer la exencion numero 23 (el `__init__` sin anotar de una clase de excepcion, absorbido como `dunder`); el delta contra los 22 medidos en RESEARCH sale de la regla mas estricta, nunca de un predicado de exencion mas ancho
- [Phase 32]: 32-02: `exempted` cuenta HITS absorbidos (definiciones que habrian sido violaciones), no todo miembro dunder/underscore encontrado — es la unica semantica bajo la cual el numero es comparable con los 22 de RESEARCH y bajo la cual `exempted == 3` en el test 4 dice algo sobre el predicado
- [Phase 32]: 32-02: `scan_surface_types` levanta solo ante problemas ESTRUCTURALES y DEVUELVE las violaciones; solo `check_surface_types` levanta ante violaciones. Ese split es lo que permite al fixture RED asertar la taxonomia de exenciones de un arbol deliberadamente lleno de hits exentos, y a la vez exigir que un arbol vacio/irresoluble levante desde el scan
- [Phase 32]: 32-02: ningun nombre de paquete aparece en el codigo del gate, docstring incluido — una mencion en prosa se lee como roster hardcodeado para cualquiera que grepee uno, y el propio criterio de aceptacion del plan grepea (fallo en el primer draft y se reescribio describiendo la forma, no el dueño)
- [Phase 32]: 32-02: D-05 registrado in situ (docstring del gate + comentario en `ci.yml`) — el "job de CI nuevo" de ROADMAP.md:25 queda superseded por el D-12 lockeado de la Phase 31 ("step en `lint`"); agregar un step ademas no renombra el job, lo que cierra la assumption A2 de RESEARCH sin tocar branch protection
- [Phase 32]: 32-02: el seam de root inyectable (D-04) queda como precedente para `tools/surface_parity.py` del plan 32-04 — es la unica razon por la que este gate tiene test y los dos preexistentes no
- [Phase 32]: 32-03: D-09 resuelto a option-a — market_data_client.aio.configure recibe http_client: httpx.AsyncClient | None = None (lo implementa el plan 32-04); option-b (allowlistear configure del chequeo de hints completo) rechazada porque estrenaria la primera excepcion de normalizacion de la fase para acomodar un defecto, no una diferencia legitima
- [Phase 32]: 32-03: la seleccion de D-09 fue AUTO-RESUELTA al default investigado bajo auto_advance/yolo, NO respondida por el desarrollador — el action del plan lo autoriza explicitamente y exige declararlo para que el registro no sea repudiable (T-32-10)
- [Phase 32]: 32-03: consecuencia semver declarada antes de que ningun codigo dependa de ella — market-data-client (publicado v0.4.0) gana un parametro publico keyword-only aditivo, entrada de changelog minor-worthy en la Phase 34 y nunca un major; la irreversibilidad esta en retirarlo, no en publicarlo
- [Phase 32]: 32-03: el roster de tres paquetes de verification/test_async_configure_resource_warning.py:27 (ambito, iol, higyrus) queda INTACTO por D-12 cualquiera fuera la seleccion — que option-a haga emitir un ResourceWarning a market-data NO habilita enrolarlo ahi dentro de la Phase 32 (T-32-11)
- [Phase ?]: 32-04: assert_class_parity raises for a package with no Client/AsyncClient pair instead of passing vacuously; the absence is asserted explicitly via class_parity_report + CLASS_AXIS_ABSENT
- [Phase ?]: 32-04: ParityReport counts are class-EXCLUSIVE on the module axis so the bounds table and the report share one metric (Pitfall 4 structural fix)
- [Phase ?]: 32-04: D-09 closed in source — market_data_client.aio.configure threads http_client into _ClientState with a ResourceWarning on live-client replacement, and does NOT set rotated
- [Phase ?]: 32-05: automated import-linter RED proof chosen over manual demonstration — the 'decenas de segundos' cost premise measured wrong (~0.06 s), so the cheaper conforming route was rejected on merit rather than necessity
- [Phase ?]: 32-05: the RED fixture reads the other four contract names from [tool.importlinter] at runtime instead of hardcoding them — a hardcoded four would be a seventh package roster inside the very phase whose subject is rosters that drift apart
- [Phase ?]: 32-05: wallets stays OUT of import-linter root_packages for a STRUCTURAL reason (no _core.py, so no source_modules against which a forbidden contract could be written); recorded in check_decode_intactness.py resolved_by in the past tense, closing the forward reference that named Phase 32 as its own resolver
- [Phase ?]: 32-05: verification/test_public_surface._PACKAGES stays at four — verification/ never executes in CI, so a fifth snapshot would be red-invisible after the first surface change; market-data's real net is in-package and does run in the 6x2 matrix
- [Phase ?]: 32-05: Task 2 landing in its own commit does NOT break criterion 4's atomicity — atomicity is a property of the four enrollment lists moving together, and the RED fixture touches none of them
- [Phase 32]: 32-06: la ausencia del par Client/AsyncClient de wallets se asevera por DOS caminos independientes — hasattr sobre client y aio (forma del Check D de check_decode_intactness) y class_parity_report(...).axis == CLASS_AXIS_ABSENT (el reporte marcado que 32-04 construyo para este caller); cualquiera solo seria un unico punto de obsolescencia
- [Phase 32]: 32-06: la no-vacuidad del test de ausencia se probo IN-PROCESS inyectando client.Client = type('Client', (), {}) antes de invocar pytest, nunca mutando un archivo trackeado — a diferencia del fixture RED de import-linter de 32-05, que debe escribir a disco porque lint-imports lee fuente estaticamente
- [Phase 32]: 32-06: el conteo esperado de iol en el plan (248) es un desliz aritmetico de dos; 250 es correcto (242 baseline + 3 paridad + 5 RED del gate de superficie de 32-02) y coincide con la derivacion del total del propio plan (1682+18+5+2=1707). Reconciliado, nunca forzado
- [Phase 32]: 32-06: tools/surface_parity.py quedo byte-identico en el fan-out — ninguna regla de normalizacion agregada, ningun bound bajado, ningun paquete excluido; las 18 aserciones de los 6 paquetes pasaron en su primera corrida
- [Phase 32]: 32-06: criterio 5 se declara PROBADO LOCALMENTE con su unica pata no reproducible nombrada (las 12 legs sobre runners reales de GitHub Actions), nunca como un verde incondicional; las 4 jobs y las 12 legs corrieron verdes localmente a 1707 passing en py3.12 y py3.13
- [Phase 32]: 32-06: D-05 resuelto y registrado — el 'job de CI nuevo' de ROADMAP.md:25 y REQUIREMENTS queda superseded por el D-12 lockeado de la Phase 31 ('step en lint'); la mitad load-bearing del texto (verification/ nunca corrio en CI) se honra plenamente y agregar un step no renombra el job (cierra A2)
- [Phase 32]: 32-06: la deuda carry-forward de probe_login_sync se re-chequeo antes del claim de matriz verde — sigue abierta pero localizada en 2 call sites de un solo archivo (2 failed + 2 errors) e invisible a las 12 legs (0 items de verification/ colectados bajo un path per-package); un pytest verification completo NO termina en 10 min porque esos probes tocan servicios en vivo
- [Phase ?]: [Phase 33 / 33-01]: convención de título de finding LOCKEADA en surface-in-title-write-new — la superficie VA embebida en el título f"{model}{path}: {kind} (declared={declared}, observed={observed}) [{surface}]", así que la identidad de dedupe cross-run es de SEIS componentes y una divergencia sync-only queda visible como finding propio. Consecuencia obligatoria para 33-04/33-05: el conteo de findings es ~2x el de triples distintos y hay que reportar y ETIQUETAR los dos números; el censo se cuenta SIEMPRE de DivergenceHandler.seen (distinto (slug, model, field_path, kind)), la única unidad comparable con el piso >=96 de 29-SIZING.md sin traducción. Resuelta en auto-mode al default recomendado por RESEARCH (Open Question 1), no respondida por el desarrollador.
- [Phase ?]: [Phase 33 / 33-01]: matriz F-03..F-08 (los seis NO-FIX hand-written de las claves extra de InstrumentDetail) NO se absorben por matcheo de título — el handler escribe seis findings OPEN nuevos al lado y se triagean a NO-FIX referenciando los originales. Una tabla de títulos bespoke adentro del handler sería el patrón hand-rolled que D-07 borra en esta misma fase, y cualquier drift entre la tabla y los títulos reales revertiría en silencio a escribir duplicados igual.
- [Phase ?]: [Phase 33 / 33-01]: probe_context NO importa ningún *_client — la clase de decode-error y el fallback con forma de ProbeResult se inyectan por los kwargs decode_error/on_decode_error. on_decode_error recibe (fn.__name__, surface, exc) y su retorno se devuelve sin tocar; NO debe escribir un finding (el SHAPE ya lo escribió el handler desde el record que _decode emitió justo antes de levantar — mintear otro rompe el idempotent_by_title del lock 10).
- [Phase ?]: [Phase 33 / 33-01]: el triple del censo se agrega a DivergenceHandler.seen ANTES de llamar al sink — si se agregara después, una falla de escritura del findings file haría que el censo reporte un número MÁS CHICO, que se lee como 'menos divergencias' (falso limpio) en vez de como un error. Falsificado: mover el add después del sink enrojece test_emit_never_raises.
- [Phase ?]: [Phase 33 / 33-01]: el rot rojo de verification/ (19 failed / 19 errors, 100% de una sola causa raíz: dos archivos llaman probes de main_matriz.py sin el parámetro client de la migración REFAC-05 de la Phase 15) queda committeado en 33-BASELINE.md y ruteado a HARN-VERIF-01 en ROADMAP § Backlog 'Deferred to v1.7+'. NO a una fase de v1.6: la 33 lo excluye por escrito (P-13) y la 34 es releases. Los dos archivos son el CANARIO del refactor de probe_context: 33-02 y 33-03 deben re-correrlos y comparar contra 17/17 y 2/2 exactos.
- [Phase ?]: 33-02: dos helpers de fallback por driver (bare + _pair) — matriz y higyrus tienen CADA UNO dos formas canónicas de retorno de probe; un único fallback 2-tuple habría reventado 39 probes con AttributeError bajo modo estricto
- [Phase ?]: 33-02: los probes de login de higyrus angostan su bracket de HigyrusClientError a HigyrusAPIError — el decode error es hermano, no subclase, y la base lo tragaba reclasificandolo como AUTH y cascadeando SKIPPED a los 17 probes restantes
- [Phase ?]: 33-02: formato de linea SUMMARY unificado en ambos drivers con DIVERGENCES=len(handler.seen) (la unidad del censo) y HANDLER_ERRORS; DIVERGENCES NO es el conteo de findings
- [Phase 33]: 33-03: los helpers _shape_probe_result* de main_iol.py reciben detail: str (texto YA renderizado por _redacted_exc), NO la excepción — El lock AST de AD-30-09-01 (test_the_driver_declares_exactly_one_exception_renderer) marca como segundo renderer toda función con parámetro anotado con tipo de excepción que lo lea o lo delegue a un callee no sancionado, y _raw_exception_renders regla 5 marca toda delegación desde un except a un callee fuera de _SANCTIONED_DELEGATES. La firma que el plan especifica enrojece 3 tests. El driver ya tenía el patrón escrito: _emit_crash_report(detail, tb), documentado desde 30-12 con exactamente esta razón; el fix lo extiende del camino de crash al camino atrapado.
- [Phase 33]: 33-03: ninguna rama de decode mintea un finding — el SHAPE ya lo escribió el DivergenceHandler bajo el título lockeado — El <action> del plan pedía append_finding(class_=SHAPE) dentro de _shape_probe_result. _decode emite el record y DESPUÉS levanta, así que para cuando la rama corre el handler ya escribió el SHAPE. Un segundo write produciría dos findings por divergencia bajo dos títulos distintos, rompiendo el idempotent_by_title que la rama existe para habilitar (contrato de on_decode_error, 33-01-SUMMARY.md; mismo comportamiento que los helpers homónimos de matriz y higyrus).
- [Phase 33]: 33-03: probe_refresh_token recibe la doceava rama de decode aunque no tiene handler amplio — IOLDecodeError es HERMANO de IOLAPIError bajo IOLClientError, no subclase, así que la escalera AuthError->APIError de ese probe lo dejaba propagar. Llama get_instruments, cuyo parser SÍ está decorado: bajo modo estricto el driver moría en el probe 14 de 15 y perdía el probe 15 más la línea SUMMARY entera. Era el único sitio ALCANZABLE del driver sin cubrir, y el plan no lo enumeraba porque enumera por handler amplio.
- [Phase 33]: 33-03: 12 ramas de decode escritas en main_iol.py, 10 alcanzables — los dos números se reportan por separado — probe_auth_401 sólo llama login() y parse_login_response no está decorado con @_decode._response_parser; _capture_raw_wire corre _request + resp.json() sin ningún parser. Ambas ramas están declaradas inalcanzables en comentarios en el propio código. Reportar 12 como cobertura sería la señal que no inspecciona nada que P-02 prohíbe.
- [Phase 33]: La rama de decode de main_market_data.py NO escribe un finding — _decode emite el record de seis claves ANTES de levantar, asi que el DivergenceHandler ya escribio el SHAPE bajo el titulo lockeado; un segundo append_finding duplicaria la divergencia y romperia idempotent_by_title. Ademas el titulo que el plan especifica no es componible: MarketDataDecodeError no guarda la especie de divergencia.
- [Phase 33]: Los 34 sitios de _write_schema_snapshot consumen _ENDPOINT_TEMPLATES — Dejar el literal inlineado al lado del dict con el mismo valor es la duplicacion drift-prone que D-03 manda evitar; cada string renderizado es byte-identico al que reemplaza, asi que ningun baseline write-once se mueve.
- [Phase 33]: El piso >=96 de 29-SIZING.md es una suma de REGISTROS sobre 43 archivos de corpus, no un conteo de triples distintos: el equivalente comparable con DivergenceHandler.seen es 58 (higyrus 22, matriz 14, market-data 22) — 33-RESEARCH Pattern 6 afirmaba que eran la misma unidad. Contrastar 24 triples en vivo contra 50 registros habria fabricado un "por debajo del piso" que es de la unidad y no del censo, disparando una investigacion de perdida donde no hay ninguna. 33-CENSUS.md contrasta contra ambas columnas.
- [Phase 33]: La asercion "fids emitidos == bloques nuevos" es falsa por construccion; la forma decidible es "ningun fid asignado pudo chocar con un finding terminal" (min asignado 67 > max preexistente 66) mas la clasificacion enumerada de los 54 gaps como dedupe intencional — El DivergenceHandler pide un fid por CADA record y pasa idempotent_by_title=True, asi que un record repetido consume un fid y no escribe bloque. La igualdad literal habria reportado una falla P-3 masiva donde solo hay dedupe content-addressed intencional, probado offline (mismo titulo x5 -> 5 fids, 1 bloque).
- [Phase 33]: matriz y higyrus se registran SKIPPED con su causa medida y destino nombrado (LIVE-MATZ-33 / LIVE-HIGY-33), nunca como cero; no se rodeo el assert remarkets-only de matriz ni se reapunto PRIMARY_BASE_URL — matriz autentica (AUTH OK) pero el driver aborta por politica D-MATZ-33, y las credenciales del .env fueron emitidas para el host demo: mandarlas a remarkets seria una fuga disfrazada de fix de config. higyrus falla por DNS gaierror con las tres credenciales presentes: es alcanzabilidad, no auth. Un cero seria una afirmacion de limpieza que ninguna medicion respalda (P-03).
- [Phase ?]: DT-07 CERRADO: iol Titulo.mercado/Titulo.plazo quedan str permanente — censo vivo sobre 2191 filas (RESPONSE mercado={'1'}, plazo={'T0','T1'}) disjunto de los defaults de INPUT 'bcba'/'t2' de la propia libreria (33-06)
- [Phase ?]: El censo de Literal se toma del wire crudo, no del stream de divergencias: literal_enforced=False en las cinco POLICY hace que walk_field:521-534 retorne temprano sin llamar al sink; 29-DLOCK-RESPONSE-LITERAL.md:140-142 queda falsificado por el codigo shipeado (33-06)
- [Phase ?]: Los 7 campos Literal-aliased de matriz quedan SKIPPED — base URL fuera de politica (D-MATZ-33), sin rodear el gate y sin mover ningun alias; ruteado a LIVE-MATZ-33 (33-06)
- [Phase 33 / 33-07]: Las tres disposiciones fix-shape-now del checkpoint 33-07 Task 1 se aplicaron, pero la consecuencia de semver NO se absorbio en la Phase 33 — `__version__` y `pyproject` siguen en 0.4.0 a proposito, porque la opcion que el operator eligio dice literalmente que la Phase 34 cargue la consecuencia. `market-data-client` 0.4.0 -> **0.5.0 SOURCE-BREAKING** queda escrito en ROADMAP § Phase 34 criterio 1: (a) `preview_calendar_config` pasa de `-> CalendarConfig` a `-> CalendarConfigPreview` en las dos superficies y en los dos shims module-level; (b) `MarketDataSnapshot.entries`/`.market_data`/`.staleness_seconds` pasan a `| None`; (c) `Symbol.created_at`/`.updated_at` pasan de `str = ""` a `str | None = None`. La Phase 34 tiene ahora DOS paquetes source-breaking (con iol 0.2.0->0.3.0 de DT-08), no uno, y los dos necesitan callout de changelog.
- [Phase 33 / 33-07]: S-1 se cerro A MEDIAS y la mitad restante se ruteo a `SHAPE-MD-REF-33` en vez de arreglarse. Desenvolver el sobre destapo una divergencia de forma que el `non_dict` TERMINAL venia escondiendo (el lock 8 suprime los records por campo debajo de un `non_dict`): `Instrument` declara `marketId`/`instrumentType` que el wire no manda y omite 7 claves que si manda; `Segment` declara 3 campos disjuntos de las 2 del wire. Corregirlo es un CUARTO cambio de forma de modelo publicado desde v0.2.0 y el checkpoint bloqueante 33-07 Task 1 gatea esa clase (T-33-44): el operator autorizo tres nominalmente y este no estaba entre ellos. Aplicarlo 'de paso' porque el paquete ya estaba abierto habria sido el cambio de contrato sin decision que el checkpoint previene. El resultado igual es mejora neta: la divergencia paso de silenciosa (1 record, 6 filas all-default) a VISIBLE campo por campo y fatal bajo `strict_decode`.
- [Phase 33 / 33-07]: El ensanche de `MarketDataSnapshot.market_data` a Optional era INEFECTIVO sin un guard en `_apply_mapping_policy`: `_is_mapping` desenvuelve Optional (tiene que hacerlo, o un campo `dict|None` se saltearia el pase entero y volveria al agujero que CR-03 cerro), asi que el pase seguia substituyendo `{}` y reportando `missing` una linea despues de que `walk_field` honro el `| None`. El guard vive en el pase especifico de market-data, NO en `_mapping_value`, que sigue byte-identico al port de matriz. La propiedad CR-03 (un `dict[...]` REQUERIDO nunca es un None silencioso) se re-anclo sobre un fixture module-local `_RequiredMapping`, porque tras SC-2 ningun modelo shipeado declara un mapping requerido.
- [Phase 33 / 33-07]: Criterio 4 no-vacuo con piso POR PAQUETE: ambito 0, higyrus 0, iol 1, matriz 1, market-data 88 (baseline medido 50 + 38 promociones). Las dos filas de piso cero NO llevan `>= 0` —esa asercion es el verde vacuo que el gate existe para prevenir—: ambito lleva la propiedad D-12 aseverada por AST (cero `ClassDef`, `__all__` vacio) MAS la linea SUMMARY verbatim de su pase estricto como evidencia POSITIVA de que el driver corrio; higyrus lleva su vacuidad DECLARADA con `LIVE-HIGY-33` aseverado como destino, porque hacer legible la vacuidad es mejor que taparla con un piso que pasaria por la razon equivocada. Probado por 4 falsificaciones, todas revertidas. Conteos inspeccionados pre->post: market-data 50->88; los otros cuatro sin mover.
- [Phase 33 / 33-07]: Los cuatro campos del record de divergencia quedaron BYTE-VERBATIM en las 76 promociones; solo se movio `status` (+ `regression` en los 38 FIXED). La razon de cada disposicion vive en `33-CENSUS.md`, no dentro del finding: P-01 prohibe componer un campo del finding con algo fuera de las seis claves del record mas el endpoint y la superficie. El short-circuit de preservacion de `append_finding` mira el status EXISTENTE, no el nuevo, asi que promover un OPEN re-serializa el archivo entero — se midio la fidelidad del round-trip ANTES de promover (0 lineas de diff) en vez de confiar en la afirmacion del plan.
- [Phase ?]: 34-01: memory files — refrescar market-data-client-releases.md en 34-03; NO crear iol-client-releases.md
- [Phase 34]: 34-02: gate humano D-08(a) resuelto con un 'approved' literal del operador; NO auto-aprobado pese a auto_advance=true y mode=yolo
- [Phase 34]: 34-02: la falla de 'Type check (mypy)' se corrigio con narrowing en el test (e5eeb8a), nunca parcheando ci.yml (D-11)
- [Phase 34]: [Phase 34-03]: El gate humano D-08(b) se resolvió con un "approved" literal del operador (2026-08-27T21:34:30Z), independiente del gate (a) de 34-02 — NO se auto-aprobó pese a auto_advance:true, mode:yolo y el gate="blocking" del task; una sola aprobación cubrió AMBOS tags y el gate no se partió por paquete (D-08)
- [Phase 34]: [Phase 34-03]: Dos tags anotados (iol-client-v0.3.0 + market-data-client-v0.5.0) sobre el MISMO merge commit a89fa45 re-resuelto en vivo con git rev-parse origin/main, pusheados POR NOMBRE uno por uno — nunca --tags, porque existía un tag local-only v1.3 que un push masivo habría publicado; dos runs independientes de release.yml (33118792322 + 33118800550) en verde, cuatro assets verificados por separado
- [Phase 34]: [Phase 34-03]: Se refrescó la memory existente market-data-client-releases.md en sus seis regiones (commit 60fc58b en milestone/v1.5-mutations, llega a main en un PR futuro); NO se creó iol-client-releases.md — ese era el item diferido en CONTEXT y queda intacto y disponible para que una fase futura lo tome deliberadamente
- [Phase 34]: [Phase 34-03]: La aserción (f) del plan (diff dir-wide de .github/workflows contra el tag de release anterior) usa baseline obsoleto y falla sobre ci.yml por commits de Phases 24/29/31/32; el invariante real de D-11 se asertó por sha256 de release.yml (7109ff0b… idéntico en los 4 refs) y por diff desde el commit base de la fase (0 archivos, 0 commits) — tercera aparición del mismo baseline obsoleto en la fase, conviene corregir la forma de la aserción en el patrón
- [Phase ?]: 35-01: _perturb needs a seventh nested-SafeModel branch that RESEARCH Pitfall 3 omits — in higyrus a nested-model default is an empty INSTANCE, not None, so Administrador (3 nested fields, 0 scalars) falls through every declared branch; 35-03/35-04 fan-out must copy that branch.
- [Phase ?]: 35-01: the criterio-5 alias-vs-twin equality is asserted on (field_path, divergence, declared_type, observed_type) and EXCLUDES the model key — the two fixture classes necessarily disagree on their own class name and on nothing else.
- [Phase ?]: 35-01: canonical digest UNCHANGED (ac14868282ad0a5c) — no byte of any _decode.py moved; all 4 v1.6 gates green, surface snapshots byte-identical, 1810 workspace tests passing.
- [Phase ?]: [Phase 35 / 35-02]: 29-SIZING.md's corpus run predates WR-02 (36b79e2 is not a descendant of 2c31790), so its non_dict labels for matriz's five model-link records differ from today's walker in BOTH the model and kind components of the 4-tuple — Phase 39 must match on (slug, field_path) and read kind from 35-RETIRED-TRIPLES.md
- [Phase ?]: [Phase 35 / 35-02]: 'triples retired' is the INTERSECTION of the 35-field roster with a measured census, never the row count — only 7 of 35 rows intersect a ratified floor (higyrus 2, matriz 5); matriz's answer is column-dependent (6 records vs 5 distinct triples)
- [Phase ?]: 35-04: matriz's base declares __dataclass_fields__ as a ClassVar, so get_type_hints reports one name dataclasses.fields omits — the criterio-5 hint assertion pins that single extra as an equality rather than relaxing to a subset check
- [Phase ?]: 35-04: a zero roster is asserted as a positive structural property (AST class count, empty __all__, import discipline, absent walker) in ambito and wallets — never a >= 0 bound, never an empty parametrize pytest would skip
- [Phase ?]: 35-04: matriz needed __bool__ only; its Phase-29 empty() was verified against the plan and left byte-unchanged (one removed source line total, the UnknownFrame docstring method count)
- [Phase ?]: [Phase 35-05]: la disposicion NOBJ-02 se compuerta por identidad contra null (if value is not None:), NUNCA por falsedad — cadena vacia, 0, dict vacio y lista vacia son falsy y son wrong-types legitimos que siguen divergiendo y siguen siendo fatales bajo strict_decode; los 10 tripwires de wrong-type de las olas 1-2 son la falsificacion de esa mitad
- [Phase ?]: [Phase 35-05]: CANONICAL_DIGEST ac14868282ad0a5c -> a1f00c824348164c, leido VERBATIM del mensaje de falla del propio gate (que reporto UN solo hash distinto en las 5 copias), nunca del digest cd937d17 de RESEARCH F-6, que corresponde a una variante sin reescritura del comentario
- [Phase ?]: [Phase 35-05]: los docstrings de modulo de _decode.py NO estan hasheados (la regla 1 de normalizacion los strippea) — la revision manual x5 que exige D-10 encontro un bullet podrido y se enmendo byte-identico x5 sin mover el digest
- [Phase ?]: [Phase 36-01]: CR-03 disposition = retire — la maquinaria de mapping se retira entera, así que conservar _RequiredMapping y sus dos tests habría exigido mantener _mapping_value vivo como código muerto en un módulo shipeado (contradice D-05 y hace SC-5 inalcanzable). Auto-resuelto bajo auto-mode (primera opción = recomendación de RESEARCH), no por veredicto humano; punto de revert = de7614a
- [Phase ?]: [Phase 36-01]: _strip_optional copiado módulo-local en test_core.py y test_decode.py (DT-03 no-shared-code); _is_mapping no se copia a ningún lado. Las 3 locks que sólo pedían prestado el detector (T-31-17, mutation-result no-Optional, WR-03) sobreviven intactas — edición por censo per-call-site, nunca por rango de líneas (Pitfall 1). 663 → 660 tests; models.py intacto (dea0dec)
- [Phase 36]: la revocación del widening de la Fase 33 es POR ROL DE CAMPO y ADITIVA — entries y market_data (eslabones) vuelven a required, staleness_seconds y note (hojas) se quedan | None, y el bloque de docstring de la Fase 33 se CONSERVA junto al nuevo en vez de borrarse
- [Phase 36]: un market_data wrong-typed cambia de KIND (type -> non_dict) y de ATRIBUCIÓN (MarketDataSnapshot -> MarketDataEntries), pero NO de disposición — sigue siendo fatal en strict decode, ahora aseverado con pytest.raises en vez de argumentado en prosa
- [Phase 36]: market-data-client pasa de form B a form A de D-07 (la maquinaria de mapping sale del paquete); el roster SafeModel va de 16 a 19 clases y el hash de _decode.py no se movió (a1f00c824348164c)
- [Phase 36]: los nombres test_no_data_row_keeps_its_nulls / _async son anclas de trazabilidad load-bearing — sostienen los bullets Regression: de F-72/73/75 y F-92/93/95 en el ledger append-only; se migran las ASERCIONES, nunca el nombre
- [Phase 36]: consecuencia semver para la Phase 40 — 3 nombres públicos ADITIVOS (BookLevel, EntryValue, MarketDataEntries) MÁS un cambio SOURCE-BREAKING (market_data: dict|None -> MarketDataEntries; subíndice -> cadena de atributos, con int ensanchado a float). Sin bump en esta fase (D-09)
- [Phase ?]: 36-03: _ENDPOINT_OPTIONAL stays unchanged — measured evidence (Pitfall 7 / F-6) shows removing 'entries' would manufacture a false model-only SHAPE finding on every /marketdata/latest run; CONTEXT's open discretion item is RESOLVED
- [Phase ?]: 36-03: SC-5 driver consumption locked structurally by AST (verification/test_main_market_data_deep_chain.py, 4 tests, non-vacuity floor 24) — a row-counting probe passes green with every chain link broken
- [Phase ?]: [Phase 37-01]: D-03 ratificado strict-unwrap por el operator — un body Risk SIN envelope key levanta PrimaryAPIError en vez de decodificar a all-defaults; la forma ENVUELTA queda canonica para los payloads de test de 37-02/37-03
- [Phase ?]: 37-02: the mapping axis takes the element hint as its 2nd POSITIONAL parameter, mirroring _decode.walk_field(value, hint, *, ...)
- [Phase ?]: 37-02: payload-supplied mapping keys are neutralized with _decode._safe_key before entering field_path (lock 11 extended to the axis)
- [Phase ?]: 37-02: F-11 depth-2 blind spot answered with option (a) - every Phase 37 inner model is kept mapping-free; the __args__ walk is NOT deepened
- [Phase ?]: 37-03: DetailedPosition.report typed at TWO levels and AccountReport.detailedAccountReports at ONE — the vendor samples show different depths (F-7/F-8); forcing a shared shape would fabricate a level of keys
- [Phase ?]: 37-03: both new inner models declare D-04a's third provenance class 'vendor-documented, UNMEASURED' — no live capture exists, LIVE-MATZ-33 blocks producing one, destination Phase 39 LIVE-NOBJ-01 (ledger rows F-11/F-12)
- [Phase ?]: 37-03: _safemodel_classes() is now 20; Plan 37-05 raises test_null_object.py's roster floor from 17 to it
- [Phase ?]: 37-04: el predicado de campo del gate no restringe el tipo de la KEY del mapping — más estricto que la letra del plan, cierra dict[int, Any] como bypass
- [Phase ?]: 37-04: el guard anti-vacuidad pasa de 'cero definiciones' a 'cero definiciones Y cero campos'; sin cláusula dura de cero-campos (reenrojecería los fixtures de iol)
- [Phase ?]: 37-04: la exención de campo se prueba por nombre (exempted_by_reason['ws-catch-all'] == 1), no subiendo el piso total de exenciones
- [Phase ?]: 37-05: los seis alias de MarketDataSnapshot citan NOBJ-MTZ-02/D-16, no el D-03 de market-data — D-03 en matriz es el envelope unwrap de Risk
- [Phase ?]: 37-05: la disjunción de nombres se argumenta como name shadowing silencioso (matriz no usa slots), no como colisión de slots
- [Phase ?]: 37-05: sin tarea WS y sin tocar ws_client.py — MarketDataFrame.marketData ES un MarketDataSnapshot (F-12), ahora aseverado
- [Phase ?]: 38-01: Cotizacion.puntas es list[Punta] y Titulo.puntas es Punta — no-Optional, sin default de dataclass; el colapso lo produce el walker NOBJ-02 congelado, no Python
- [Phase ?]: 38-01: la deriva del round-trip se absorbe en el valor ESPERADO del test con la causa dicha; la captura live 2026-06-06 nunca se reescribe
- [Phase ?]: 38-01: sin edit espejo en client.py/aio.py — ambas superficies delegan en _core.py; la obligación sync/async se descarga con surface_parity, no duplicando decode
- [Phase ?]: 38-02: el discriminador de modelo del gate es estatico (conjunto de nombres ClassDef por import root) - issubclass/get_type_hints exigirian importar un modulo de paquete, lo que dispararia load_dotenv() en el job lint
- [Phase ?]: 38-02: dict[str, Model] | None queda fuera del ratchet como exclusion declarada; agregarlo despues es una adicion declarada, no un bug fix
- [Phase ?]: 38-03: las refs de models.py en 35-RETIRED-TRIPLES.md se escriben :235/:334 (verificadas en HEAD), no :213/:301 — la tabla del plan se midio en cf79e65, antes del drift de docstrings de 38-01
- [Phase ?]: 38-03: la fila de cero explicito de iol en 35-RETIRED-TRIPLES.md se conserva y las 2 filas nuevas van en un addendum delimitado — reemplazarla habria roto la igualdad de 35 filas con el conteo D-17
- [Phase ?]: 38-04: la cita 35-RETIRED-TRIPLES.md:184-197 del plan estaba stale — el parrafo de ausencia enumerada esta en :169-180; el censo escribe el numero medido y registra la discrepancia
- [Phase ?]: 38-04: las uniones PEP-604 se sacaron de toda celda de tabla del censo — un pipe dentro de una celda rompe el conteo de columnas del awk de verificacion; las firmas de _request van en bloque de codigo verbatim
- [Phase ?]: 38-04: el cross-check de los 142 campos de higyrus se hizo scopeando el gate a un solo paquete (semilla D-04 inyectable), no comparando contra el total workspace de 442 fields scanned
- [Phase ?]: 39-01: allowlist D-MATZ-33 por igualdad exacta de hostname, ampliado sólo a api.bbsa.matrizoms.com.ar con aprobación humana explícita (D-02)
- [Phase ?]: 39-01: verification/mutation_gate.py queda byte-idéntico — su _SANDBOX_HOST remarkets-only deja el order entry fail-closed bajo bbsa sin cambio de código
- [Phase ?]: 39-01: las líneas SKIPPED de los drivers son literales de módulo sin interpolación — veredicto de política y destino, nunca el hostname ni la base URL
- [Phase ?]: 39-01: el finding terminal EXPECTED de matriz queda superseded en el ledger y recibe disposición explícita en 39-07 (no se borra)
- [Phase ?]: [Phase 39-02]: Las tres suites de casos límite viven bajo packages/<pkg>/tests/ y no bajo verification/ — es el único árbol que el job test de CI corre de verdad (verification/ sólo corre por allowlist explícita), así que las tres entran a CI en 3.12 y 3.13 sin tocar ci.yml.
- [Phase ?]: [Phase 39-02]: iol y matriz NO tienen tolerancia a 204/cuerpo vacío — resp.json() levanta json.JSONDecodeError, que escapa IOLClientError/PrimaryAPIError; higyrus sí devuelve su zero-value. La asimetría se assertea explícitamente por tipo y se difiere como D39-01/D39-02: cambiarla es un cambio de superficie del paquete, fuera del alcance de un plan que sólo crea tests.
- [Phase ?]: 39-03: la costura de no-vacuidad vive en el loop de main_matriz.py, no en verification/cycle_report.py (que queda byte-identico)
- [Phase ?]: 39-03: el predicado de cierre de ciclo es probes_executed > 0 (evidencia positiva de corrida), NO el conteo de findings promovidos
- [Phase ?]: 39-03: el sobre de evidencia se reescribe en cada corrida, incluidos los dos caminos de skip (T-39-12)
- [Phase ?]: 39-04: la allowlist de driver locks de ci.yml vive en el job lint, no en el test — el job test corre per-package y nunca ve verification/
- [Phase ?]: 39-04: la rama de la cadena .puntas se decide por truthiness (lista vacia / Null Object falsy), nunca por is None — ambos campos estan declarados sin | None desde la Phase 38
- [Phase ?]: 39-05: la cadena tipada de higyrus se construye sobre el payload ya obtenido (Posicion.from_api), no llamando a la funcion tipada — enruta por el mismo walker, sink y ContextVar de modo estricto, asi que cuesta CERO llamadas HTTP adicionales
- [Phase ?]: 39-05: incluirParking sigue en False — flipearlo quemaria el baseline write-once de get_posiciones por deriva de schema; la rama poblada de parking no se ejercita en vivo y su evidencia es la suite mockeada de 39-02
- [Phase ?]: 39-06: probe_get_market_data_async recibe cuerpo propio en vez de extender _ainvoke — el helper genérico lo comparten ~16 probes de paridad y descartaba el resultado; el mapeo de excepciones se replicó byte-paralelo
- [Phase ?]: 39-06: los baselines write-once de schema de matriz se keyean por (func_name, venue) con el token del allowlist D-MATZ-33 — sin esto la primera corrida bbsa emitiría hasta 8 findings SHAPE OPEN que describen una diferencia entre venues, no un defecto del cliente
- [Phase ?]: 39-06: 'ambas superficies' para matriz es client.py + aio.py, NO REST+WS — la premisa de CONTEXT está vencida y un test AST prohíbe reintroducir el import de ws_client en el driver
- [Phase ?]: 39-07: la divergencia CONFIRMED del identificador plano de byCFICode/bySegment se corrige en _core (sitio unico que ambos shells atraviesan por REFAC-03), no en cada shell — el espejo sync/async sale por construccion
- [Phase ?]: 39-07: F-11 queda NO-FIX medido a medias con destino nombrado LIVE-POS-39; F-01 de iol se mantiene OPEN arrastrado con destino LIVE-NOBJ-01 (el operador no firmo la promocion a terminal)
- [Phase ?]: 39-07: una sola corrida autoritativa por paquete — el harness re-emite findings por corrida (idempotent_by_title default False, D39-03), asi que correr dos veces contamina el ledger
- [Phase ?]: [Phase 39-08]: El delta entre las dos costuras del censo (9 vs 7 triples de matriz) NO se resuelve eligiendo una: son los dos triples que el fix in-cycle F-43/F-44 cerro entre la emision pre-fix y la captura post-fix del sobre de evidencia. El delta ES el fix.
- [Phase ?]: [Phase 39-08]: La resta de matriz cierra exacta en las DOS columnas de unidad — 14 - 5 (colapso de politica NOBJ-02) - 2 (correccion real) = 7 triples distintos medidos, y 24 - 6 - 4 = 14 registros. Ninguna de las 14 divergencias del piso queda sin columna (SC-4 / D-11).
- [Phase ?]: [Phase 39-08]: NOBJ-RETIRE-3637 registra la deuda de retiro no saldada de las Fases 36 y 37 (no existe artefacto 36-RETIRED ni 37-RETIRED), a saldar con un addendum al ledger de la Phase 35 en el cierre del milestone v1.7. Etiqueta de bookkeeping, no decision nueva de alcance.
- [Phase 40]: 40-01: D-02 resuelto A-fold-higyrus — higyrus-client entra como cuarto paquete bumpeado (0.2.0 -> 0.3.0)
- [Phase 40]: 40-01: D-12 resuelto B-widen-now — MarketDataSnapshot.market_id -> str | None y .active -> bool | None dentro del mismo bump breaking
- [Phase 40]: 40-03: D-07(b) resuelto con un `approved` literal del operador — SEGUNDO gate bloqueante, independiente del de merge (40-02), no colapsado y no auto-emitido pese a auto_advance + _auto_chain_active + mode:yolo los tres activos
- [Phase 40]: 40-03: PUBLICADO — 4 tags anotados (market-data-client-v0.6.0, iol-client-v0.4.0, matriz-client-v0.3.0, higyrus-client-v0.3.0) sobre el merge SHA re-resuelto en vivo 8e0013f2ac7f0361df1ad4893cf0de8f6c773751, pusheados UNO POR NOMBRE (cero `git push --tags`)
- [Phase 40]: 40-03: 4 corridas independientes de release.yml verdes y observadas por separado (33315928885, 33315932932, 33315937584, 33315942414); concurrency.group per-tag confirmado empíricamente por solapamiento temporal
- [Phase 40]: 40-03: release.yml byte-idéntico (sha256 7109ff0b…) en 10 refs incluyendo los 4 tags nuevos — SEXTA reutilización sin editar. La forma rota de la Phase 34 (git diff --name-only <prior-tag>..HEAD) NO se reutilizó
- [Phase 40]: 40-03: verificación post-publicación en verde — los 4 wheels instalados desde su URL pública de Release en un venv py3.12.13 descartable fuera del repo; `__file__` en site-packages prueba que las cadenas profundas corrieron contra la distribución INSTALADA, no contra el checkout
- [Phase 40]: 40-03: matriz_client.__version__ resuelve a 0.3.0 — sitio NUEVO (no existía antes de 40-01, OQ-4), no una baseline de regresión
- [Phase 40]: 40-03: ámbito y wallets NO publicados (D-01, aditivos por medición); conteos de tags idénticos al baseline pre-fase (ámbito 2, wallets 1)
- [Phase 40]: 40-03: defecto de plan confirmado — la cláusula `wallets-client-v*` == 2 del verify de la Task 2 es STALE (el conteo real es 1). Se OVERRIDEÓ con justificación; NO se creó ni borró ningún tag para hacerla pasar. Forma correcta a futuro: ámbito == 2, wallets == 1
- [Phase 40]: 40-03: los bloques `<verify>` de los planes asumen bash word-splitting y fallan bajo zsh (`for T in $TAGS`, `uv pip install $WHEELS`). Correr los verify blocks bajo `bash -c` en esta máquina
- [Phase ?]: Phase 41 OQ#1: las 4 filas manual-only de la Phase 39 se disponen NOT-VERIFIABLE-RETROACTIVELY (R-07) — gana el ejemplo lockeado de D-04 sobre la inferencia del researcher; en auditoría se sub-declara, no se sobre-declara
- [Phase ?]: Phase 41 OQ#2: ni 36 ni 37 cierran limpias — R-09 exige además cero calificadores de corrección, así que las cinco fases quedan en nyquist_compliant: false por evidencia, no por decreto
- [Phase ?]: Phase 41-01: criterio 3b se marca con la clave de front-matter not_verifiable_retroactively en los cinco archivos (incluso donde vale 0); se descarta nyquist_compliant: partial
- [Phase ?]: Phase 41-01: denominador del criterio 2 fijado en 62 (13/11/14/9/15); rechazados 51 (as-declared) y 25 (criterios de ROADMAP de v1.7)
- [Phase ?]: Phase 41-01: audit_baseline_head (6dd83cf4) se captura una sola vez en 41-AUDIT-CONTRACT.md y se copia literal; criterio 1 es invariante continuo, no gate único
- [Phase ?]: Phase 41-01: el planner mis-sumó las tareas de la fase como 14; el valor real medido es 16 (3+2+2+2+2+2+3) — corrección registrada en 41-AUDIT-CONTRACT.md §2.5 para el gate de 41-07
- [Phase ?]: Phase 41 / plan 41-02: el paso RED de TDD 35-r01 se dispone VERIFIED-HISTORICALLY (R-05) sin re-ejecutarlo — su cadena lleva un '&& !' sobre tres tests que hoy pasan, asi que sale 1 por diseno; leerlo como rojo llevaria a 'arreglar' un test que esta bien.
- [Phase ?]: Phase 41 / plan 41-02: las dos rutas muertas de 35-02 (35-r04, 35-r05) se corrigen en el comando EJECUTADO y se disponen VERIFIED-NOW (ruta corregida) por R-03; 35-02-PLAN.md queda intacto como registro historico y la ruta stale se nombra en Hallazgos de bookkeeping.
- [Phase ?]: Phase 41 / plan 41-02: nyquist_compliant de la Phase 35 se queda en false por evidencia medida, no por decreto — R-09 falla por (b) una fila VERIFIED-HISTORICALLY y por (c) dos calificadores de correccion. Cero flags flipeados; las seis casillas preexistentes del sign-off quedan sin tildar.
- [Phase ?]: Phase 41 / plan 41-02: la fila placeholder del mapa de la Phase 35 se CONSERVA marcada como superada en vez de borrarse — su existencia es en si un hallazgo de la auditoria (la fase shipeo con el mapa sin llenar, D-05); las 12 filas reales se reconstruyen debajo desde los bloques <verify><automated> de los cinco planes.
- [Phase ?]: Phase 41 / plan 41-03: 36-r11 se dispone VERIFIED-NOW (comando redactado retroactivamente) por R-04 — la Phase 36 shipeó una fila sin contrato de verificación; la auditoría redactó el comando tras leer el cuerpo del lock. Es el hallazgo principal de la fase, no el VERIFIED-NOW
- [Phase ?]: Phase 41 / plan 41-03: las celdas File Exists de la Phase 36 y wave_0_complete quedan intactas — su contradicción con la medición es el hallazgo (D-04); corregirlas lo borraría
- [Phase ?]: Phase 41 / plan 41-03: nyquist_compliant de la Phase 36 sigue en false — R-09 falla por (c) y, en consecuencia, por (a); (b) sí se satisface. Cero flags flipeados
- [Phase ?]: 41-04: la clave ordinal 37-r01..37-r14 es la unidad de conteo del criterio 2 en la Phase 37 — sus Task ID se reparten solo cuatro etiquetas entre catorce filas
- [Phase ?]: 41-04: 37-r11 dispuesta VERIFIED-NOW (comando corregido) tras leer el cuerpo de los dos tests sustitutos; nyquist_compliant sigue en false por R-09(c) pese a 14/14 filas verdes
- [Phase ?]: Phase 38 auditada 7/2/0: las dos filas de revisión de documento se disponen VERIFIED-HISTORICALLY contra la confirmación humana fechada 2026-08-29T22:04:57Z, sin re-derivar; nyquist_compliant sigue en false por la condición (b) de R-09
- [Phase ?]: [41-06] Las 4 filas manual-only de la Phase 39 quedan NOT-VERIFIABLE-RETROACTIVELY (R-07), contra la recomendación de 41-RESEARCH.md de partir el bloque 3/1: D-04 las nombra por su nombre como el arquetipo del marcador, y en una auditoría la dirección segura es sub-declarar. La evidencia parcial superviviente no se descarta: cada celda nombra su artefacto fechado (los 4 envelopes de run-evidence con sus sondas ejecutadas, 39-07-SUMMARY.md, dos secciones de 39-CENSUS.md, el sign-off del operador) con la frase explícita de por qué no basta. Resultado: not_verifiable_retroactively: 4 en front-matter — la única de las cinco fases con valor distinto de cero, y la forma en que el criterio 3b se satisface.
- [Phase ?]: [41-06] El node-id ::_ambito_declares_zero_models de la fila 39-r08 NO consume una tercera corrección R-02: R-02 se dispara con selector -k que colecciona 0 tests y exit 5; acá el node-id nombra un helper privado y pytest sale exit 4 (error de uso). Fila dispuesta VERIFIED-NOW plano vía -k ambito (2 passed, 19 deselected), tras confirmar que los dos casos parametrizados atraviesan ese helper y assertan la conducta declarada. Registrado como hallazgo de bookkeeping, preservando el 'cero escalaciones' del contrato.
- [Phase 41]: 41-07: el gate de inmutabilidad de REQUIREMENTS.md del criterio 5 se sustituye por un hash byte-a-byte de la fila de alcance excluido — la cláusula as-written es insatisfacible porque el seam requirements mark-complete edita ese archivo dentro de la fase
- [Phase 41]: 41-07: nyquist_compliant de la propia Phase 41 queda en false por evaluación medida de R-09 (fallan (a) y (c): 3 de 16 filas llevan calificador de corrección), no por simetría con las cinco auditadas
- [Phase 41]: 41-07: los 40 locks de verification/ fuera del allowlist de ci.yml quedan declarados inertes por escrito, con su enrolamiento ruteado a la Phase 45 (HARN-03/HARN-04); la Phase 41 no edita .github/workflows/ci.yml
- [Phase 42]: El gate de venue de scripts/literal_census_33.py se porta por IMPORT de main_matriz (_VENUE_ALLOWLIST + _venue_token), pinneado por identidad de objeto (is), no por igualdad de contenido — Con import, la divergencia de politica entre el driver y el censo es estructuralmente imposible en vez de solo detectada. El substring-match pre-Phase-39 habria hecho saltear el censo EN SILENCIO contra el sandbox bbsa ya desbloqueado.
- [Phase 42]: El walk AST anti-substring se restringe al FunctionDef de census_matriz, NO al modulo entero (Q4, cerrada en planificacion) — Un walk a nivel de modulo produce falsos positivos sobre el despacho de flags de main() — confirmado en ejecucion: la Task 2 agrego un segundo despacho (--matriz-only) de la misma forma sintactica. Descubrirlo con un test rojo invita al reflejo de relajar la asercion.
- [Phase 42]: Aprobacion humana explicita del operador ('Approved') registrada verbatim en 42-01-SUMMARY.md antes de cualquier trafico en vivo; habilita 42-02/42-03/42-04 — checkpoint:human-verify con gate=blocking-human. La aprobacion NO se derivo de auto_advance, mode:yolo ni human_verify_mode:end-of-phase — ese modo no puede gatear trafico que ya ocurrio. verification/mutation_gate.py quedo byte-identico (6bdaec00), order entry fail-closed bajo bbsa sin cambio de codigo.
- [Phase ?]: Phase 42 (42-02): los 8 valores de vendor fuera de los alias Literal declarados de matriz (6 en CFICode, 2 en OrderType) quedan REGISTRADOS, NO APLICADOS — ampliar un alias es un cambio de forma de un paquete publicado y necesita disposicion de semver propia; ruteado a la Phase 43
- [Phase ?]: Phase 42 (42-02): ordType se reporta NO MEDIBLE EN ESTA CORRIDA con causa medida (orders vacio en la cuenta bbsa), no se rellena — emitir una orden para fabricar una fila seria una mutacion
- [Phase ?]: [42-03 / LIVE-01]: **Alcanzabilidad de higyrus MEDIDA hoy (2026-08-31), no heredada.** `socket.gaierror` en DNS y `httpx.ConnectError` en `login()`, ambos con errno `[Errno 8] nodename nor servname provided, or not known` citado verbatim tras pasar un guard de contención case-insensitive (hostname/base URL/netloc). La clase medida es IGUAL a la heredada de la Phase 39 — dicho como hecho verificado, no re-estampado. El driver completo salió 0 con `SKIPPED higyrus-client: vendor host unreachable (DNS) — LIVE-HIGY-33` y el sobre quedó con `captured_at 2026-08-31T21:20:38Z`, `probes_executed 0` y `skipped` con causa medida. **LIVE-01 medido NO cierra `LIVE-HIGY-33`: los 22 triples (Movimiento 9, PosicionValuada 11, Posicion 2) siguen sin contrastar.**
- [Phase ?]: [42-03 / WR-02]: **`httpx.ConnectTimeout` re-declarado FUERA DE ALCANCE, decidido por escrito ANTES de la corrida y no revisitado.** No es subclase de `ConnectError` (MRO httpx 0.28.1), así que un host que resuelve pero cuelga cae en `_RESIDUAL_PROBE_EXCEPTIONS` y da `FINDING`/`FAILED` en vez de `SKIPPED`. La rama `_vendor_unreachable` NO se amplió. Destino: backlog de deuda in-code de Phase 39 (D39-01..04, WR-02). Cero líneas de `main_higyrus.py` tocadas.
- [Phase ?]: [42-03 → 42-05]: **Veredicto explícito: el rename D-06 DISPARA (SÍ).** El bloqueo sigue vivo y medido hoy, el sobre recién committeado lleva el identificador stale `LIVE-HIGY-33`, y ni la rama "DNS resolvió → D-06 moot" ni la rama de resultado inesperado aplican. 42-05 va por su rama principal, respetando su propio hallazgo: **11 ocurrencias en 6 archivos vivos, y UNA no debe renombrarse** (asevera sobre artefacto histórico congelado de v1.6; renombrarla viola la premisa de la Phase 41).
- [Phase ?]: [42-03 / D42-DEF-01]: Exposición **pre-existente** del base URL del vendor en `higyrus-client-findings.md:5` (header `Resolved base URL / env:`) detectada por el chequeo de no-fuga y **NO corregida**: byte-idéntica a HEAD (último commit `fbb69c3`/Phase 17, header de `e8307a6`/Phase 11), ledger append-only versionado (HARN-07), y la política T-39-04 es posterior a ese header. Ruteada a la **Phase 45** con tres opciones escritas en `deferred-items.md`. Todos los artefactos DE LA SESIÓN dieron CLEAN.
- [Phase ?]: [42-03 / LIVE-01 traceability]: **LIVE-01 queda `Pending` a propósito al cierre de 42-03.** El criterio 2 del ROADMAP tiene dos mitades: (a) resultado medido —entregado por este plan— y (b) "con el destino `LIVE-HIGY-33` renombrado", que es el plan **42-05**. Marcarlo completo con la mitad (b) sin hacer sería el falso limpio que este proyecto existe para eliminar. Lo cierra el plan **42-06**, que ya lleva LIVE-01 en su frontmatter.
- [Phase 42]: 42-04: n_rows quedó null en /instruments y /segments y NO se 'arregló' — el wire devuelve un sobre paginado (dict), no un array, así que len(raw) if isinstance(raw, list) else None evaluó como el plan lo especificó — Cambiar el cómputo habría exigido una segunda corrida en vivo contra un servicio de terceros para regenerar un dato que ya está reportado (50 filas / 4 filas, derivado de items y segments) en 42-WIRE-READ.md
- [Phase 42]: 42-04: el delta vacío contra el baseline del 2026-07-31 se reporta como RESULTADO de la re-medición y NO revierte la marca de no-autoritatividad — Lo autoritativo para SHAPE-01 es la medición de hoy, que resulta coincidir; escrito explícitamente en 42-WIRE-READ.md § 4 para que la Phase 43 no concluya 'el baseline coincide, entonces uso el baseline'
- [Phase 42]: 42-04: D42-DEF-02 (SHAPE-diff del driver INERTE para Instrument/Segment) se difiere a la Phase 43 en vez de arreglarse — Es preexistente (no lo causó ninguna task del plan), no hubo pérdida de evidencia (el censo de divergencias del decode produjo los 28 findings F-205..F-242), y el fix exigía otra corrida en vivo sin producir un hecho nuevo
- [Phase ?]: 42-05: el rename D-06 disparo porque el veredicto medido por 42-03 fue SKIPPED — LIVE-HIGY-33 pasa a LIVE-HIGY-42 en los 14 sitios vivos (11 codigo + 3 prosa, 7 archivos, 1 commit atomico)
- [Phase ?]: 42-05: la historia congelada NO se renombra — test_cycle_closure_phase33.py:250-252 conserva exactamente 2 ocurrencias del identificador viejo (asevera contra 33-CENSUS.md); el criterio es 'afirma estado vivo vs. historico', no 'prosa vs. codigo'
- [Phase ?]: 42-05: el sobre de evidencia se regenero corriendo el driver por segunda vez (captured_at 2026-08-31T21:38:57), nunca editando el JSON; las dos mediciones de la sesion COINCIDIERON (SKIPPED, exit 0)
- [Phase 42-06]: Phase 42 cerrada: los 5 criterios del ROADMAP disponen 2 SATISFECHO + 3 SATISFECHO POR LA VIA DECLARADA + 0 NO SATISFECHO, cero filas sin disponer (42-CLOSURE.md)
- [Phase 42-06]: Q5 corregida: el backlog ya no afirma que scripts/literal_census_33.py tenia el gate listo — estaba en substring-match pre-Phase-39; correccion aplicada a las dos entradas forward-looking, texto historico de la Phase 33 preservado verbatim
- [Phase 42-06]: LIVE-01 cerrado por la via 'causa re-confirmada'; LIVE-HIGY-42 (ex LIVE-HIGY-33) sigue ABIERTO con sus 22 triples sin contrastar — el rename cambio el identificador, no el estado
- [Phase 43]: [43-01] Instrument.active se declara bool | None = None (D-03): el wire mando null en 50/50 filas medidas; declararlo bool plano habria convertido una extra medida en una missing permanente sobre cada lectura de catalogo. — El miembro bool de la union nunca se observo y queda como asuncion declarada, autocorrectiva via el censo de divergencias.
- [Phase 43]: [43-01] Instrument.marketId se conserva como alias aditivo deprecado con espejo en from_api (D-04, precedente D-22); Segment en cambio se reemplaza por completo (D-06) en vez de alias-mapearse. — D-22 cubre UNA clave con variante de spelling camelCase/snake_case; marketSegmentId vs segment son nombres distintos, asi que el alias no aplica.
- [Phase 43]: FeedIngestor.last_error_age_seconds y .last_error_at nullables (D-09): ausentes del baseline sano y presentes junto a un last_error poblado, condicionales a que exista un error; declararlas planas emitiria un missing en cada llamada sana
- [Phase 43]: HealthFeed.symbols_never_delivered PLANO (D-11) pese a emitir un missing contra la fixture congelada del 2026-07-31: la clave esta poblada en las tres capturas posteriores y un Optional sobre-declarado absorberia un futuro null sin dejar record
- [Phase 43]: ingestor.subscription tipado como FeedSubscription (15 campos), nunca como dict[str, Any]: walk_field no tiene rama para mappings, asi que un mapping seria un punto ciego permanente del censo de divergencias
- [Phase ?]: Phase 43 cerrada: 43-DISPOSITION.md consolida la disposicion de los 17 campos de Instrument/Segment con cero filas sin disponer, el antes/despues MEDIDO de get_segments(), y los 4 jobs de CI verdes sin bump de version (0.6.0 intacto en los tres sitios)
- [Phase ?]: D-14 medido por identidad de objeto funcion: client.py y aio.py no necesitan cambio porque ambas superficies llaman al mismo _core.parse_X; el comando del plan asumia un re-export inexistente y se sustituyo declarando la sustitucion
- [Phase ?]: El job pre-commit estaba rojo en main desde antes de la Phase 43 (end-of-file-fixer sobre 41-06-PLAN.md y 42-05-PLAN.md); corregido con +1 byte por archivo, cero caracteres de contenido alterados
- [Phase ?]: [45-01]: El docstring del gate de superficie queda REPRODUCIBLE, no congelado — el bloque historico se pinnea a su commit (00ffb2f~1) con sus digitos byte-identicos y el bloque vigente lleva fecha + commit (Measured 2026-09-01, fe323d6) con las tres cifras re-medidas hoy (187/337/467). El defecto IN-01 nunca fue el digito historico: era la ausencia de fecha en el bloque vigente.
- [Phase ?]: [45-01]: DRV-MD-SEG-43 CERRADO (probe_parity compara s.segment; mypy main_market_data.py de 2 errores a 0) pero su entrada de backlog se CONSERVA — su medicion de por que ningun gate estatico lo detecta es la evidencia que cita la declaracion de Q5. El gap de gate NO se cierra en esta fase: apuntar mypy a los 5 drivers de la raiz es scope creep no medido, ruteado al plan 45-05 + backlog v1.9.
- [Phase ?]: [45-01]: IN-05 retirado del backlog justificado por el CODIGO y no por el reporte — el retiro se ejecuto despues de correr el import y pegar su salida (matriz_client.__version__ -> 0.3.0) en el propio ROADMAP. El criterio 4 de la Phase 45 dejo de decir 336 (medido pre-Phases-43/44) y dice 337 con su fecha de medicion.
- [Phase ?]: [Phase 45-04]: HARN-04 cerrado: los 2 archivos de verification/ de matriz quedan aceptados como deuda documentada (no reparar, no borrar) en 45-HARN-04-DECISION.md, fechado 2026-09-01; censo re-declarado 53/13/40 (corrige el 52/12/40 de 41-ROLLUP.md)
- [Phase ?]: [Phase 45-04]: Q4 cerrado por implementacion: la taxonomia FINDING-no-FAIL de probe_login_sync tiene guardian por AST en verification/test_main_matriz_skip_line_shape.py, archivo ya enrolado en CI (19 -> 20 tests, no-vacuidad demostrada por mutacion)
- [Phase ?]: [Phase 45-04]: Q5 declarado, no cerrado: ningun gate de CI mira los 5 drivers main_*.py de la raiz (mypy files = packages/*/src, pre-commit files: ^packages/.*/src/); destino backlog v1.9, entrada que el plan 45-05 debe agregar al ROADMAP

### Pending Todos

[From .planning/todos/pending/ — ideas captured during sessions]

- spike-codegen-libcst-v1.3.md — the fully-scoped SPIKE-006 spec + D-RIGOR-02 10-item gate; consumed by Phase 18 planning (v1.3 closed).

### Blockers/Concerns

[Issues that affect future work]

- [v1.6 / Phase 33 risk]: **Descubrimiento masivo de divergencias.** La tolerancia silenciosa actual puede estar ocultando divergencias acumuladas; la primera corrida estricta podría destapar muchas de golpe y desbordar el scope del milestone. Mitigación locked: corrida exploratoria de sizing con el walker al final de la Phase 29, **antes** de comprometer 30-32. El resultado es un piso, no una estimación.
- ~~[v1.6 / Phase 29 decision gate]~~ **RESUELTO 2026-08-19 (Plan 29-04, firmado `no-go-stdlib-only` por sebadlf).** Ya no bloquea nada: la Phase 34 puede cerrar su set de releases y las Phases 30-33 avanzan con un solo motor. Evidencia en `29-DLOCK-MSGSPEC.md` (benchmark de tres arms + 5 probes de capacidad). Texto original del gate, conservado como registro: La **decisión msgspec-dos-motores vs stdlib-only** cambia el perfil de dependencias de los 6 wheels (msgspec sería el primer artefacto compilado de un closure hoy 100% puro-Python) y el set de paquetes a re-publicar en la Phase 34. Debe resolverse en `discuss-phase` de la Phase 29 con evidencia de ambos lados, no pre-decidirse en el roadmap. Hecho load-bearing verificado: **msgspec no puede implementar el modo observable** (fail-fast, un error por decode, ignora claves extra en todos los modos, sin field-rename para dataclasses del stdlib) — el walker es el motor primario en cualquiera de los dos escenarios.
- [v1.6 / Phase 31 risk]: `add_holidays` y `delete_holiday` son **mutaciones ya publicadas en v0.4.0** con contrato de idempotencia verificado en vivo y un invariante de orden del mutating-gate. El trabajo de tipado es **response-only**: hace falta un test de **request byte-idéntico** y el guard AST de `_ensure_mutation_allowed()` como primer statement debe seguir verde.
- [v1.6 / Phase 32 blocker]: **`verification/` nunca corrió en CI** — `ci.yml` pasa un path `packages/${{ matrix.package }}` explícito a pytest que pisa `testpaths`, así que hasta el gate golden-file de superficie pre-existente estuvo inerte. GATE-TYP-01 no es "agregar un archivo de test": requiere superficie de CI nueva (script en el job de lint + tests in-package que viajen en la matrix 6×2).
- [v1.6 / Phase 32 note]: Las **4** listas de enrollment de D-16 ya discrepan entre sí (mypy `files` 5/6; import-linter `root_packages` 4/6; loop de `ci.yml:85` 5/6; `test_public_surface._PACKAGES` 4/6 — market-data excluido **por diseño** desde Phase 25, hay que documentarlo, no "arreglarlo"). El backlog de mypy subyacente es trivial (2 errores `var-annotated`); el trabajo real es decidir explícitamente si `wallets_client` entra.
- [v1.6 / Phase 30 unknown]: Se desconoce si algo **fuera de este repo** consume `iol-client` 0.2.0 — determina si la ruptura dict→modelo necesita alguna consideración transicional. Relevar antes de la Phase 30.
- [v1.6 / operativo]: El `.venv/` del repo apuntaba a un intérprete inexistente y `uv` no podía recrearlo (`.venv/lib` tomado por un proceso). Cerrar el proceso y re-sincronizar antes de arrancar la Phase 29.
- [v1.5 / Phase 27 risk]: La verificación en vivo es **destructiva** (crea/modifica estado en develop) — a diferencia de v1.4 (solo lectura). Requiere identificadores de prueba dedicados + cleanup obligatorio (crear→verificar→revertir, DM-06) y **confirmación del operator sobre qué es seguro tocar en develop** antes de Phase 27. El mutating-gate impide prod. Depende también de creds Auth0 + acceso a develop (mismo standing blocker que v1.4 Phase 23, ya resuelto post-close con creds provistas por el operator).
- [v1.5 / Phase 27 risk]: La **idempotencia real** de los POST de symbols la declara el spec, pero un POST no idempotente reintentado duplicaría estado → se revalida en vivo (DM-03) antes de confiar el retry-behavior. `POST /calendar/holidays` se asume `idempotent=False` (no retry) salvo confirmación live.
- [v1.5 / Phase 26 note]: `PUT /calendar/config` tiene un guardrail `confirm` server-side → el cliente lo expone explícitamente con default `False`; nunca se persiste config real sin `confirm` explícito.
- [v1.6 / Phase 32 STILL OPEN]: `verification/` matriz probes call `probe_login_sync()` with the pre-15-05 signature (19 failed + 19 errors in a **full** local suite run). Sigue abierto y **fuera del scope del plan 32-01**: `verification/` nunca corrió en CI (`ci.yml:125` pasa un path `packages/<pkg>` explícito que pisa `testpaths`), así que no afecta ninguna de las 6 patas per-package. GATE-TYP-01 es lo primero que va a meter superficie de test a nivel repo en CI → re-chequear antes de que el plan 32-06 reclame un verde de matriz completa. Ver `.planning/phases/31-endpoints-de-ops-estructura-uniforme/deferred-items.md`.
- ~~[v1.6 / Phase 31 deferred-items D-2/D-3]~~ **RESUELTO 2026-08-25 (Plan 32-01, commits `5ce4e87` + `f08b7f2`).** Texto original: *ambito's test_decode.py has 2 live mypy --strict errors that the typecheck CI job DOES run; mypy packages/higyrus-client/tests is RED on 2 pre-existing errors in the byte-frozen test_decode.py copy (deferred-items D-3); typecheck CI iterates higyrus first under set -e, so it masks the identical ambito D-2. Needs a five-copy repair plan before v1.6 ships.* Los 33 errores (29 matriz + 2 higyrus + 2 ambito) se arreglaron **en código de test únicamente** — `pyproject.toml` byte-idéntico, cero tests borrados/skippeados. El loop per-package de `ci.yml:92-99` imprime `Success: no issues found` **seis veces**; el job `typecheck` está verde por primera vez desde 2026-08-18. Baseline completo de los 4 jobs en `.planning/phases/32-gates-de-homogeneidad-d-16/32-01-SUMMARY.md` § CI-green baseline (Wave 0 close).
- ~~Criterio 1 de la Phase 33 PARCIAL (registrado por 33-05): 33-07 debe surfacearlo en vez de dar el criterio 1 por cerrado.~~ **SURFACEADO 2026-08-27 por el plan 33-07** en tres lugares: `33-CENSUS.md` § Criterio 1 (declarado GATE HUMANO ABIERTO), `33-07-SUMMARY.md`, y una asercion EJECUTABLE dentro de `verification/test_cycle_closure_phase33.py` que exige que el censo siga diciendo `SKIPPED — vendor inalcanzable` y que `LIVE-HIGY-33` siga nombrado. El gate en si **sigue abierto** — ver la entrada siguiente.
- ~~Criterio 1 de la Phase 33 **PARCIAL** — 3 de 5 paquetes medidos en vivo.~~ **PARCIALMENTE RESUELTO 2026-08-30 (v1.7 Phase 39, D-02).** `matriz-client` corrió en vivo por primera vez desde v1.0 — el gate D-MATZ-33 se amplió de substring-match a allowlist exacto de hostname, admitiendo el sandbox `bbsa.matrizoms.com.ar`; la corrida encontró y corrigió in-cycle una pérdida real de datos (~9160 instrumentos). `higyrus-client` **sigue** `SKIPPED` — el DNS del host todavía no resuelve desde esta red (`LIVE-HIGY-33` sigue abierto, re-sondeado en Phase 39 con la misma causa medida). El censo de valores `Literal` de RESPONSE de matriz (S-4) tampoco se tocó en Phase 39 — ver la entrada `LIVE-MATZ-33` en `ROADMAP.md § Backlog`.
- ~~DEF-37-01: 4 errores mypy PRE-EXISTENTES en packages/matriz-client/tests/{test_core.py:372, test_decode.py:666,839,840} heredados de los retipados 37-01/02/03 — rompen el job CI typecheck; diagnóstico en 37-.../deferred-items.md~~ **RESUELTO** (commit `2e28672`, orquestador, antes de despachar 37-05): 2× `# type: ignore[comparison-overlap]` explícito en las aserciones `scalar_passthrough` + comentario `# type: ignore[attr-defined]` movido a la línea del acceso real. `uv run mypy` global y `uv run mypy packages/matriz-client/tests` limpios; 547 tests matriz verdes.

### Quick Tasks Completed

Archived to `.planning/milestones/v1.7-quick/` at the v1.7 milestone close (2026-08-30) — see that
directory's `README.md` for the index. These 8 tasks predated v1.7 itself (2026-06-11 → 2026-08-01)
and had never been archived at any earlier milestone close.

| # | Description | Date | Commits | Directory |
|---|-------------|------|---------|-----------|

## Deferred Items

Items acknowledged and carried forward from v1.0 milestone close on 2026-06-10:

| Category | Item | Status | Resolution in v1.1 |
|----------|------|--------|---------------------|
| todo | matriz-driver-findings-file-handling | low priority — driver dedupe + append-only bugs | Resolved in Phase 11 (HARN-07/08/10) |
| uat_gap | 03-HUMAN-UAT.md | partial — legacy HUMAN-UAT from Phase 3 close | N/A — archived under v1.0 |
| uat_gap | 05-HUMAN-UAT.md | partial — 2 ítems satisfied via operator re-run 2026-06-10T15Z | N/A — archived under v1.0 |
| verification_gap | 03-VERIFICATION.md | human_needed — operator-driven validation | N/A — archived under v1.0 |
| verification_gap | 05-VERIFICATION.md | human_needed — operator-driven validation satisfied via re-run | N/A — archived under v1.0 |
| deferred_bug | F-09 matriz ERROR-MAP | DEFERRED in v1.0 Phase 5 | Resolved in Phase 9 (BUG-01) |
| deferred_bug | F-02 higyrus get_listado_cuentas=0 | DEFERRED in v1.0 Phase 4 | Resolved in Phase 9 (BUG-02) |
| deferred_cap | IOL refresh_token persistence | DEFERRED in v1.0 Phase 3 | Resolved in Phase 9 (BUG-03, in-instance only; disk persistence Phase 14 SEC-01) |
| deferred_cap | HIGY multi-account iteration | DEFERRED in v1.0 Phase 4 | Resolved in Phase 9 (BUG-04) |

See `.planning/milestones/v1.0-MILESTONE-AUDIT.md` for the full v1.0 audit context.

### Acknowledged at v1.2 close on 2026-06-25

Items surfaced by `gsd-sdk query audit-open` (6 total) and acknowledged by operator at v1.2 milestone close ("Acknowledge & proceed"). All are intentional deferrals or stale history — none are real blockers:

| Category | Item | Status | Carry-forward |
|----------|------|--------|---------------|
| quick_task | 260611-u0v / 260613-nwb / 260614-de5 / 260614-r1x | SDK reports "missing" — v1.1-era tasks, work landed in git history | False-positive (SDK parser heuristic) — no action |
| todo | spike-codegen-libcst-v1.3.md | pending (high) → **now active** | Became the v1.3 codegen spike (Phase 18 SPIKE-006) per Phase 12 NO-GO (D-NOGO-01) |
| uat_gap | 15-HUMAN-UAT.md | partial — 4 operator-driven live scenarios | Superseded by Phase 17 LIVE-03 final gate (dispositions × 4 in 17-VALIDATION.md) |

See `.planning/milestones/v1.2-ROADMAP.md` and the MILESTONES.md v1.2 entry for full close context.

### Acknowledged at v1.4 close on 2026-07-31

Items acknowledged and deferred by operator at v1.4 milestone close ("Proceed with close"). None are real blockers:

| Category | Item | Status | Carry-forward |
|----------|------|--------|---------------|
| uat_gap | 20-UAT.md | passed — 0 pending scenarios | False-positive (open-artifact audit parser heuristic flags file presence) — no action |
| verification_gap | LIVE-MD-01 real credentialed sweep | **RESOLVED post-close 2026-07-31** — operator supplied Auth0 creds; real sweep ran vs develop (PASS=17, snapshots=12), found+fixed 3 real divergences in-cycle (quick tasks 260731-j93 + 260731-jim), final re-run 0 real divergences | No longer deferred — LIVE-MD-01 satisfied with real live evidence; fixes on `release/v0.2.0-bump` (post-`v1.4`-tag) |
| deferred_cap | MUT-MD-01/02, STREAM-MD-01, SEC-MD-01/02 | v2 requirements (market-data-client) | MUT-MD-01/02 **now active in v1.5** (Phases 25-26); STREAM-MD-01 + SEC-MD-01/02 remain v1.6+ (see ROADMAP Backlog) |

See `.planning/milestones/v1.4-ROADMAP.md` and the MILESTONES.md v1.4 entry for full close context.

## Session Continuity

Last session: 2026-09-01T15:29:04.181Z
Stopped at: Completed 45-04-PLAN.md
Resume file: None

## Operator Next Steps

- Revisar `.planning/ROADMAP.md` § Phase Details (v1.8) — 5 fases, 9/9 requisitos mapeados
- Planificar la primera fase con `/gsd-plan-phase 41` (validación Nyquist retroactiva; **antes** de cualquier cambio de fuente de v1.8)
- Research marcó 3 fases como candidatas a `discuss-phase` antes de planificar: **42** (política del widening de venue), **43** (tabla de disposición por campo) y **45** (interacción fid-allocator / dedupe)
- Pregunta abierta que el roadmap resolvió y conviene ratificar: v1.8 **sí** publica la 0.7.0 (Phase 44), no es fix-and-hold
