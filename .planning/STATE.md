---
gsd_state_version: 1.0
milestone: v1.6
milestone_name: Tipado homogéneo de la superficie pública
current_phase: 29
current_phase_name: decoder-observable
status: verifying
stopped_at: "Completed 29-10-PLAN.md (Phase 29 complete: 10/10 plans)"
last_updated: "2026-08-19T22:41:03.220Z"
last_activity: 2026-08-19
last_activity_desc: "Plan 29-09 completo: gate de intactness normalize-then-hash (5 copias -> 1 hash) + step decode-intactness en el job lint + exencion de wallets"
progress:
  total_phases: 6
  completed_phases: 1
  total_plans: 10
  completed_plans: 10
  percent: 17
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-18 for milestone v1.6)

**Core value:** Cada divergencia entre un cliente y su API en vivo debe ser detectada, documentada y corregida. (v1.6 lo lleva al sistema de tipos: que sea **imposible cometer un typo al consumir la lib** —acceso por atributo verificado por mypy— y que **ninguna divergencia con la API en vivo sea silenciosa** —hoy `SafeModel.from_api()` convierte un campo desaparecido en `0.0` sin que nadie se entere.)

**Current focus:** Phase 29 — decoder-observable

## Current Position

Phase: 29 (decoder-observable) — EXECUTING
Plan: 10 of 10
Status: Phase complete — ready for verification
Last activity: 2026-08-19 — Plan 29-09 completo: gate de intactness normalize-then-hash (5 copias -> 1 hash) + step decode-intactness en el job lint + exencion de wallets

## Performance Metrics

**Velocity (v1.0 archived):**

- Total plans completed: 83 (v1.0)
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

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

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

### Quick Tasks Completed

| # | Description | Date | Commits | Directory |
|---|-------------|------|---------|-----------|
| 260611-u0v | Fix CI failures on phase-06-compat-safety-net (snapshot trailing whitespace + iol tests mypy strict + v1.0 archive whitespace) | 2026-06-11 | bc16e26, 2be4e90, 9360cf5 | [260611-u0v-fix-ci-failures-on-phase-06-compat-safet](./quick/260611-u0v-fix-ci-failures-on-phase-06-compat-safet/) |
| 260613-nwb | Fix INT-01: replace denied `_base_url` with `_get_default()._state.base_url` in main_iol.py (15 probes) — closes INT-01, unblocks LIVE-01 (Phase 11) | 2026-06-13 | 3de1940 | [260613-nwb-fix-int-01-main-iol-py-crashea-con-attri](./quick/260613-nwb-fix-int-01-main-iol-py-crashea-con-attri/) |
| 260614-de5 | Fix DOC-01..04 before completing milestone v1.1 — backfill 4 SUMMARY frontmatters + flip REQUIREMENTS.md traceability table 18 rows Open→Complete + emit Phase 10/11 VERIFICATION shims + remove ORP-01 dead `account_id` field from matriz `_state.py` | 2026-06-14 | 9d01d7f, cd946a3 | [260614-de5-fix-doc-01-04-before-completing-mileston](./quick/260614-de5-fix-doc-01-04-before-completing-mileston/) |
| 260614-r1x | Fix v1.1 CI mypy + pre-commit tech debt (mypy-precommit-v1.1-techdebt) — Bucket A: 4 unused `# type: ignore` dropped + `_raise_for_response` added to `aio.__all__`; Bucket B+C: bump `ruff-pre-commit` v0.7.4→v0.15.12; Bucket D: add `tenacity>=9.1.0,<10` to pre-commit mypy `additional_dependencies` | 2026-06-14 | e5ad1c1, 73cb578, c7bf9e9, 2b8ec4a | [260614-r1x-fix-v1-1-ci-mypy-pre-commit-tech-debt-cl](./quick/260614-r1x-fix-v1-1-ci-mypy-pre-commit-tech-debt-cl/) |
| 260731-j93 | Make `symbol` a required kwarg in market-data-client `get_latest` (5 sites: client.py method+shim, aio.py method+shim, `_core.build_latest_request`) + probe updates + sync/async/builder regression tests — closes v1.4 Phase-23 live findings F-01/F-13 (`GET /marketdata/latest` returns 422 without `symbol`; OpenAPI `required=True`). Verified live: driver re-run PASS=19 FINDING=0; 137 pkg tests green | 2026-07-31 | d062761, 36aa94b, 68092d7 | [260731-j93-make-symbol-a-required-kwarg-in-market-d](./quick/260731-j93-make-symbol-a-required-kwarg-in-market-d/) |
| 260731-jim | Reconcile `MarketDataSnapshot` + `CalendarConfig` SafeModels against the real develop wire (LIVE-MD-01 schema snapshots): `marketId`→`market_id`, add `active`/`market_data`/`staleness_seconds`/`note`; drop invented `businessDays`+`MarketDataEntry`, add full `/calendar/config` field set; **fix `parse_market_data_response` envelope-unwrap bug** (iterated envelope keys instead of `items[]`). Closes the 36 live SHAPE findings. Verified live: `market_data snapshots=5→12`, SHAPE divergences gone (only 2 benign NO-DATA remain); 139 pkg tests green | 2026-07-31 | 0852d43, 45c1885, 8c8e494 | [260731-jim-reconcile-market-data-client-marketdatas](./quick/260731-jim-reconcile-market-data-client-marketdatas/) |
| 260731-l4s | Bump `market-data-client` to **v0.2.0** (release prep): version in pyproject + `__version__`, CLAUDE.md workspace bullet, README changelog (breaking changes), `uv.lock` refresh. Minor bump because the post-v0.1.0 LIVE-MD-01 fixes (`get_latest.symbol` required, model reconciliation, envelope-unwrap) broke the public API. On `release/v0.2.0` → PR → tag `market-data-client-v0.2.0`. 139 pkg tests green | 2026-07-31 | 73dda1c | [260731-l4s-bump-market-data-client-to-v0-2-0-releas](./quick/260731-l4s-bump-market-data-client-to-v0-2-0-releas/) |
| 260731-t9o | Fix `get_latest_batch` empty snapshots — `parse_latest_response` (`_core.py`) iterated the batch envelope's keys instead of `items[]` (WR-01 from Phase 25 review; live shape `{requested,count,not_found,server_time,items}`). Unwrap `items` mirroring sibling `parse_market_data_response`, preserve single-GET bare-list path, dict-without-`items`→`[]`; fixed 2 mis-mocked client batch tests (sync+async) that hid the bug. Shipped as v0.3.1. 191 pkg tests green | 2026-08-01 | 7d58b3f, f1f051b | [260731-t9o-fix-get-latest-batch-empty-snapshots-par](./quick/260731-t9o-fix-get-latest-batch-empty-snapshots-par/) |

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

Last session: 2026-08-19T22:41:03.216Z
Stopped at: Completed 29-10-PLAN.md (Phase 29 complete: 10/10 plans)
Resume file: None

## Operator Next Steps

- Revisar `.planning/ROADMAP.md` § Phases (v1.6) + § Phase Details (v1.6)
- Correr `/gsd-discuss-phase 29` **antes** de planificar: la decisión msgspec-dos-motores-vs-stdlib-only cambia el perfil de dependencias de los 6 wheels y el set de releases de la Phase 34 (research flag explícito)
- Luego `/gsd-plan-phase 29` (Decoder observable — load-bearing, PRIMERO)
