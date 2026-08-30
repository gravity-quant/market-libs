# Roadmap: market-libs — Verificación en vivo de clientes

## Milestones

- ✅ **v1.0 Verification cycle** — Phases 1-5 (shipped 2026-06-10) — see [`milestones/v1.0-ROADMAP.md`](./milestones/v1.0-ROADMAP.md)
- ✅ **v1.1 Tech Debt Cleanup** — Phases 6-11 (shipped 2026-06-14) — see [`milestones/v1.1-ROADMAP.md`](./milestones/v1.1-ROADMAP.md)
- ✅ **v1.2 Architecture + Auth/Ergonomics Carry-forwards** — Phases 12-17 (shipped 2026-06-25) — see [`milestones/v1.2-ROADMAP.md`](./milestones/v1.2-ROADMAP.md)
- ✅ **v1.3 Codegen Single-Source (libcst)** — Phases 18-19 (closed 2026-07-03 on signed SPIKE-006 NO-GO; Phase 19 REFAC-06 dropped) — see [`milestones/v1.3-ROADMAP.md`](./milestones/v1.3-ROADMAP.md)
- ✅ **v1.4 market-data-client** — Phases 20-24 (shipped 2026-07-31) — nuevo paquete cliente (solo lectura) contra la API primary-extractor con Auth0 client-credentials, verificado en vivo y publicado v0.1.0 — see [`milestones/v1.4-ROADMAP.md`](./milestones/v1.4-ROADMAP.md)
- ✅ **v1.5 market-data-client · mutaciones** — Phases 25-28 (shipped 2026-08-17) — superficie de **escritura** (symbols + calendar) detrás de mutating-gate default-refuse, verificada en vivo (create→verify→revert) y publicada `market-data-client-v0.4.0` — see [`milestones/v1.5-ROADMAP.md`](./milestones/v1.5-ROADMAP.md)
- ✅ **v1.6 Tipado homogéneo de la superficie pública** — Phases 29-34 (shipped 2026-08-27) — contrato de tipos idéntico y verificable por máquina en los 6 paquetes: decodificación por-campo observable, `iol-client` y los endpoints de ops tipados, gates de CI que sostienen la homogeneidad, verificación en vivo en modo estricto, y publicación de `iol-client-v0.3.0` + `market-data-client-v0.5.0` — see [`milestones/v1.6-ROADMAP.md`](./milestones/v1.6-ROADMAP.md)
- 🚧 **v1.7 API tipada con Null Objects** — Phases 35-40 (in progress) — patrón Null Object en los 6 paquetes: ningún eslabón de cadena (`snapshot.market_data.last.price`) puede ser `None`, cero `dict[str, Any]` en campos de modelos públicos (exención única: `UnknownFrame.raw`)

## Phases

<details>
<summary>✅ v1.6 Tipado homogéneo de la superficie pública (Phases 29-34) — SHIPPED 2026-08-27</summary>

- [x] Phase 29: Decoder observable (10/10 plans) — completed 2026-08-19
- [x] Phase 30: `iol-client` tipado (13/13 plans) — completed 2026-08-23
- [x] Phase 31: Endpoints de ops + estructura uniforme (5/5 plans) — completed 2026-08-25
- [x] Phase 32: Gates de homogeneidad + D-16 (6/6 plans) — completed 2026-08-25
- [x] Phase 33: Verificación en vivo en modo estricto + fixes (7/7 plans) — completed 2026-08-27
- [x] Phase 34: Releases por paquete (3/3 plans) — completed 2026-08-27

Full detail: [`milestones/v1.6-ROADMAP.md`](./milestones/v1.6-ROADMAP.md)

</details>

### 🚧 v1.7 API tipada con Null Objects (Phases 35-40) — IN PROGRESS

**Milestone Goal:** Que toda cadena de acceso como `snapshot.market_data.last.price` sea **siempre válida bajo mypy strict y nunca lance** en las 6 libs: ningún eslabón intermedio de tipo modelo/lista puede ser `None` (patrón Null Object — el campo devuelve una instancia vacía falsy), y `dict[str, Any]` desaparece de los campos de modelos públicos, de modo que un typo sea error de mypy + `AttributeError` y nunca un `KeyError` ni un `None` propagado.

> **Notas de sizing y restricciones (leer antes de planificar).**
> **La Phase 35 es load-bearing y es la única fase transversal**: toca las bases `SafeModel` de los 6 paquetes y el walker `_decode.py` de las 5 copias verbatim, sin cambiar ni una firma pública. Todo lo que hacen 36-38 depende de que su política esté firmada primero. La restricción **no-shared-code** (DT-03) sigue vigente: cada cambio de base se **copia verbatim** por paquete y `tools/check_decode_intactness.py` lo verifica por hash — no hay atajo por un paquete común.
> **Los 4 gates de CI de v1.6 son el contrato de no-regresión de este milestone**: `check_decode_intactness.py`, `check_uniform_structure.py`, `check_surface_types.py` y `surface_parity.py` deben quedar verdes en cada fase, y `check_surface_types.py` es además el instrumento que mide el criterio central de D-NO-02 (cero `dict[str, Any]` en la superficie pública).
> **Todo cambio de lógica se espeja en `client.py` y `aio.py`** del mismo paquete (D-NO-06 / deuda dual conocida), y `surface_parity.py` lo asevera por introspección.
> **La cobertura en vivo de la Phase 39 arranca con dos bloqueos heredados de la Phase 33**: `higyrus-client` (host que no resuelve por DNS) y `matriz-client` (assert de política remarkets-only D-MATZ-33, que **no se rodea**). Ninguno se resuelve desde adentro de una fase; el registro correcto es `SKIPPED` con causa medida y destino nombrado (`LIVE-HIGY-33` / `LIVE-MATZ-33`), nunca un cero que se lea como limpio.
> **Las Phases 36, 37 y 38 paralelizan** entre sí (las tres dependen sólo de la 35 y tocan paquetes disjuntos).

- [x] **Phase 35: Fundación Null Object — `__bool__` + política del walker** *(load-bearing, PRIMERO)* — `SafeModel.__bool__`/`empty()` en las 4 jerarquías de base copiadas verbatim a los 6 paquetes + nueva disposición del walker para eslabones no-opcionales, con los 4 gates de v1.6 verdes y **cero** cambios de superficie pública — NOBJ-01, NOBJ-02 (completed 2026-08-29)
- [x] **Phase 36: `market-data-client` — `market_data` tipado + revocación de la Fase 33** — `MarketDataEntries`/`BookLevel`/`EntryValue` con alias `last`/`bids`/`offers`/`settlement`/`close`/`open_interest`, `entries` de vuelta a `list[str]`, fila no-data expresada por veracidad y baja de la maquinaria `_mapping_value` — NOBJ-MD-01, NOBJ-MD-02 (completed 2026-08-29)
- [x] **Phase 37: `matriz-client` — dicts residuales tipados + alias** — `tickPriceRanges`, `AccountReport.report`/`detailedAccountReports`/`portfolio` modelados contra payloads reales (exención única `UnknownFrame.raw`) + los mismos alias en su `MarketDataSnapshot`, compartidos por REST y frames WS — NOBJ-MTZ-01, NOBJ-MTZ-02 (completed 2026-08-29)
- [x] **Phase 38: `iol-client` + auditoría de higyrus/ámbito/wallets** — `Cotizacion.puntas` → `list[Punta]` y `Titulo.puntas` → `Punta` Null Object, más el censo con disposición por campo de los tres paquetes restantes hasta que el grep de cierre devuelva sólo hojas escalares — NOBJ-IOL-01, NOBJ-AUD-01 (completed 2026-08-29)
- [x] **Phase 39: Verificación en vivo del encadenamiento profundo** — los drivers `main_*.py` ejercen cadenas profundas reales en sync y async contra las APIs en vivo, con divergencias corregidas in-cycle y censo contrastado contra el de la Fase 33 — LIVE-NOBJ-01 (completed 2026-08-30)
- [ ] **Phase 40: Releases breaking coordinados** — bumps sólo de los paquetes cuya superficie cambió, con callout + tabla de migración vieja→nueva por paquete, y las dos operaciones irreversibles detrás de dos gates humanos independientes — PUB-NOBJ-01

## Phase Details (v1.7)

### Phase 35: Fundación Null Object — `__bool__` + política del walker

**Goal**: La ausencia deja de expresarse con `None` y pasa a expresarse con veracidad — toda base `SafeModel` de los 6 paquetes sabe decir "estoy vacío" y el walker `_decode` sabe colapsar un `null` legítimo sobre un eslabón sin ensuciar el canal de divergencias, sin que ninguna firma pública cambie todavía.
**Depends on**: Nothing (primera fase de v1.7; parte del head de v1.6)
**Requirements**: NOBJ-01, NOBJ-02
**Success Criteria** (what must be TRUE):

  1. `bool(X.from_api(None)) is False` para toda clase `SafeModel` de los 6 paquetes y `bool(instancia_con_un_campo_no_default) is True`, incluida la jerarquía `_SafeModel` de matriz (sin `slots`, con `empty()` y semánticas propias registradas en la tabla 6-way de la Phase 29) — `empty()` existe y es invocable en las 4 bases, y el chequeo se hace por enumeración de las clases reales del paquete, nunca sobre un fixture de test.
  2. Un `null`/ausente sobre un campo **no-opcional** de tipo modelo o lista decodifica a instancia vacía / `[]` **sin emitir registro de divergencia**, mientras que un valor **wrong-typed** sobre el mismo campo sigue emitiendo el record de seis claves y sigue levantando bajo `strict_decode` — las dos mitades probadas por falsificación (invertir la disposición enrojece un test), no sólo por el camino feliz.
  3. Los 4 gates de CI de v1.6 quedan verdes tras la actualización verbatim: `check_decode_intactness.py` reduce las copias de `_decode.py` a **un único hash canónico nuevo** (ninguna copia se queda atrás ni diverge), y `check_uniform_structure.py`, `check_surface_types.py` y `surface_parity.py` pasan sin que se afloje ninguna regla, se baje ningún lower bound ni se excluya ningún paquete.
  4. **Ninguna superficie pública cambia en esta fase**: las suites de los 6 paquetes pasan sin editar un solo test, y los snapshots de superficie pública quedan byte-idénticos — la fase entrega política y capacidad, no ruptura.
  5. Las propiedades alias que introducen las fases 36-38 son **invisibles para el walker**: un test prueba que `get_type_hints()` sobre una dataclass con `@property` alias devuelve exactamente los campos declarados, de modo que agregar un alias no puede fabricar un `missing` ni cambiar el conteo de divergencias.

**Plans**: 5/5 plans complete
**Wave 1**

- [x] 35-01-PLAN.md — TRACER: higyrus end-to-end (`SafeModel.empty()` forma A + `__bool__`, suite de enumeración/veracidad/alias, 2 tests nuevos de wrong-type sobre lista) — wave 1
- [x] 35-02-PLAN.md — Artefacto D-17 `35-RETIRED-TRIPLES.md`: los 35 triples que la política retira, con resta por paquete y advertencia de unidad para la Phase 39 — wave 1

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 35-03-PLAN.md — Fan-out A: bases + suites de iol (forma A) y market-data (forma B con mapping pass, caveat `received_at` D-09) — wave 2
- [x] 35-04-PLAN.md — Fan-out B: matriz (`_SafeModel.__bool__` + `UnknownFrame.__bool__`, 17 clases) y las aserciones de roster vacío de ámbito/wallets — wave 2

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 35-05-PLAN.md — ATÓMICO: EDIT 1 + EDIT 2 en las 5 copias de `_decode.py` + comentario byte-idéntico + las 11 inversiones + `CANONICAL_DIGEST` recomputado, en UN commit; más el gate de fase — wave 3

### Phase 36: `market-data-client` — `market_data` tipado + revocación de la Fase 33

**Goal**: El consumidor de `market-data-client` escribe `snapshot.market_data.last.price` y esa expresión compila bajo mypy strict y nunca lanza — con el payload real, con un `market_data` ausente, con `null` y con la fila no-data.
**Depends on**: Phase 35 (necesita `__bool__` + la disposición del walker; paraleliza con 37 y 38)
**Requirements**: NOBJ-MD-01, NOBJ-MD-02
**Success Criteria** (what must be TRUE):

  1. `snapshot.market_data.last.price`, `.market_data.bids[0].price`, `.offers`, `.settlement`, `.close` y `.open_interest` pasan `mypy --strict` y **no lanzan** contra los cuatro payloads de la matriz de casos: el wire real ya capturado (`.planning/verification/schemas/market-data-client/get-market-data.json`), `market_data` ausente, `market_data: null` y `market_data: {}` — verificado en **ambas** superficies (`client.py` y `aio.py`).
  2. `MarketDataEntries` (wire verbatim `BI`/`OF: list[BookLevel]`, `LA`/`SE`/`CL`/`OI: EntryValue` Null Object, `OP`/`HI`/`LO`/`TV`… hojas `float | None`), `BookLevel {price, size}` y `EntryValue {price, size, date}` existen como **copia local** del patrón matriz (sin import cross-package, D-NO-06) con las propiedades alias de sólo lectura de D-NO-05, y `MarketDataSnapshot.market_data: MarketDataEntries` no admite `None` en su anotación.
  3. El widening de la Fase 33 queda **revocado donde rompe la cadena y sólo ahí**: `MarketDataSnapshot.entries` y `LatestRequest.entries` vuelven a `list[str]` con default `[]`, mientras que `staleness_seconds` y `note` se quedan como hojas `| None` (D-NO-03) — la revocación se registra en el docstring del módulo con referencia al checkpoint 33-07 que revoca.
  4. La fila no-data de `/marketdata/latest` conserva **el mismo poder expresivo sin `None`**: `bool(snapshot.market_data) is False` y `note` poblado; `test_snapshot_no_data_row.py` queda migrado a esa semántica en vez de eliminado.
  5. `_mapping_value` / `_apply_mapping_policy` y su test de precondición desaparecen de `market-data-client` **sin mover el hash de `_decode.py`** (la maquinaria vive en `models.py`, no en el walker), y `main_market_data.py` consume por encadenamiento profundo en sus sitios reales.

**Plans**: 3/3 plans complete

**Wave 1**

- [x] 36-01-PLAN.md — Prep: retirar el eje mapping de la suite de tests por censo per-call-site (no por rango), con checkpoint del operator sobre la disposición del contrato CR-03 — wave 1

**Wave 2** *(blocked on Wave 1)*

- [x] 36-02-PLAN.md — TRACER: `BookLevel`/`EntryValue`/`MarketDataEntries` + 6 alias, revocación del widening 33-07 por rol de campo, `LatestRequest` alineado, baja de la maquinaria en `models.py`, y la matriz SC-1 de 4 payloads × 2 superficies — wave 2

**Wave 3** *(blocked on Wave 2)*

- [x] 36-03-PLAN.md — SC-5: encadenamiento profundo en los 4 probes reales de `main_market_data.py` con lock AST, cierre de prosa form B → form A, y gate de fase — wave 3

### Phase 37: `matriz-client` — dicts residuales tipados + alias

**Goal**: La implementación de referencia del patrón Null Object queda ella misma sin `dict[str, Any]` en su superficie pública y expone la misma ergonomía de alias que market-data, compartida por la superficie REST y los frames de WebSocket.
**Depends on**: Phase 35 (paraleliza con 36 y 38)
**Requirements**: NOBJ-MTZ-01, NOBJ-MTZ-02
**Success Criteria** (what must be TRUE):

  1. `InstrumentDetail.tickPriceRanges`, `AccountReport.report`, `AccountReport.detailedAccountReports` y `AccountReport.portfolio` devuelven modelos tipados (o `list[modelo]`) derivados de **payloads observados**, con la procedencia de cada uno declarada por campo: baseline committeado, captura nueva, o modelo mínimo con los campos no observados dejados al reporting de divergencias — nunca un `dict[str, Any]` de reemplazo ni un modelo inventado presentado como observado. **Restricción heredada:** `matriz-client` sigue bloqueado para corridas en vivo por el assert de política D-MATZ-33 (`LIVE-MATZ-33`), que no se rodea; si un payload no es observable, esa fila se declara como tal.
  2. `check_surface_types.py` reporta **cero** `dict[str, Any]` en campos de modelos públicos de matriz con **una única exención**, `UnknownFrame.raw`, declarada explícitamente como exención documentada (el escape hatch de frames desconocidos) y no obtenida por omisión o por un hueco de resolución del gate.
  3. `snapshot.last.price`, `.bids`, `.offers`, `.settlement`, `.close` y `.open_interest` funcionan sobre `matriz_client.models.MarketDataSnapshot` tanto cuando la instancia viene de la superficie REST como cuando viene de un frame de `ws_client` — es el mismo objeto y el mismo juego de alias — con `mypy --strict` limpio sobre el paquete.
  4. La suite de matriz queda verde en REST **y** en las rutas del daemon thread de WS (incluida la propagación explícita del modo de decode por conexión y por frame de la Phase 29), sin aflojar el mutation gate ni tocar la deny-list `_token_store.py` / `_refresh_policy.py` / `_refresh.py` más allá de lo que exija el alias.

**Plans**: 5 plans

Plans:
**Wave 1**

- [x] 37-01-PLAN.md — Envelope unwrap de los dos parsers Risk en `_core.py` (D-03, un solo sitio) + regresiones mockeadas; checkpoint de disposición del body plano
- [x] 37-02-PLAN.md — Tracer: axis de mapping con tipo de elemento y recursión (D-06) + `TickPriceRange` con procedencia `baseline` (D-04c/D-05)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 37-03-PLAN.md — `report` a dos niveles, `detailedAccountReports` a uno, `portfolio` a escalar (D-02/D-07) con procedencia `vendor-documented, UNMEASURED` + filas en el ledger

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 37-04-PLAN.md — Dimensión de campos en `tools/check_surface_types.py` (D-01a/b/c) + fixture RED de no-vacuidad (D-01d)
- [x] 37-05-PLAN.md — Seis `@property` alias sobre `MarketDataSnapshot` (NOBJ-MTZ-02), compartidas por REST y frames WS

### Phase 38: `iol-client` + auditoría de higyrus/ámbito/wallets

**Goal**: Los cuatro paquetes restantes quedan sin eslabones `None` en sus cadenas — `titulo.puntas.precioCompra` es siempre válido — y la limpieza de los tres casi-limpios queda **medida campo por campo**, no supuesta.
**Depends on**: Phase 35 (paraleliza con 36 y 37)
**Requirements**: NOBJ-IOL-01, NOBJ-AUD-01
**Success Criteria** (what must be TRUE):

  1. `Cotizacion.puntas` es `list[Punta]` con default `[]` y `Titulo.puntas` es un `Punta` Null Object: `titulo.puntas.precioCompra` y `cotizacion.puntas[0].precioCompra` pasan `mypy --strict` y no lanzan con un payload sin `puntas`, con `puntas: null` y con el `puntas` polimórfico real ya resuelto en la Phase 30 — espejado en `client.py` y `aio.py`, con el snapshot de superficie pública regenerado y la ruptura (incluido el flip de truthiness) registrada en el README de iol.
  2. La auditoría de higyrus, ámbito y wallets está **publicada como censo con disposición**: cada campo modelo/lista `| None` y cada `dict[str, Any]` en campos de modelos o retornos públicos aparece en una fila con su disposición — corregido a Null Object/`[]`, hoja escalar permitida por D-NO-03, o exención documentada — y **cero filas quedan sin disposición**.
  3. El grep de cierre del plan fuente sobre `packages/*/src/*/models.py` devuelve **sólo** hojas escalares y `Literal` en los 6 paquetes, y ningún retorno de función pública expone `dict[str, Any]` / `list[dict[str, Any]]` fuera de los shims `_legacy` e internals (`_request`) — el resultado se reporta con el comando ejecutado y su salida, no como afirmación.
  4. Las suites de los cuatro paquetes quedan verdes con los 4 gates de v1.6 activos, y `surface_parity.py` asevera que cada cambio de lógica viajó a las dos superficies (D-NO-06); para `wallets-client` se registra explícitamente su condición de stub sin endpoints reales en vez de reportar un verde vacuo.

**Plans**: 4/4 plans complete

**Wave 1**

- [x] 38-01-PLAN.md — TRACER: retipado Null Object de los 2 `puntas` de iol (RED: 7 aserciones migradas + rename + 3 docstrings de procedencia; GREEN: `models.py:213,301`; snapshot regenerado) — wave 1

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 38-02-PLAN.md — Ratchet D-11: predicado de campo del gate ensanchado con discriminador `ClassDef` + 3 fixtures RED en iol, sin reenrojecer los 10 leaves `Literal` de matriz — wave 2
- [x] 38-03-PLAN.md — Callout `## Unreleased — BREAKING` en el README de iol (D-10) + corrección de refs y addendum de contabilidad Phase 38 en `35-RETIRED-TRIPLES.md` (D-12) — wave 2

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 38-04-PLAN.md — `38-CENSUS.md`: censo con disposición por campo de higyrus/ámbito/wallets, ceros por enumeración con la condición de stub de wallets, y la evidencia SC-3 como comando ejecutado con su salida — wave 3

### Phase 39: Verificación en vivo del encadenamiento profundo

**Goal**: El encadenamiento profundo deja de ser una propiedad demostrada contra fixtures y pasa a ser una propiedad demostrada contra las APIs reales, en sync y en async, con toda divergencia corregida dentro del mismo ciclo.
**Depends on**: Phases 36, 37, 38
**Requirements**: LIVE-NOBJ-01
**Success Criteria** (what must be TRUE):

  1. Cada driver `main_*.py` ejercita al menos una **cadena profunda real** (`snapshot.market_data.last.price`, `titulo.puntas.precioCompra`, `snapshot.last.price`, …) en **ambas** superficies contra la API en vivo, y la corrida reporta por paquete `PASS` o `SKIPPED` **con causa medida y destino nombrado** — los bloqueos heredados `LIVE-HIGY-33` (DNS) y `LIVE-MATZ-33` (política D-MATZ-33, que no se rodea) se registran así si siguen vigentes, nunca como cero.
  2. Ninguna cadena lanza `AttributeError` ni `TypeError` con datos reales en ninguno de los paquetes que efectivamente corrieron, incluidos los casos límite que sólo produce la API en vivo: mercado cerrado, fila no-data, campo ausente y respuesta 204/vacía.
  3. Toda divergencia CONFIRMED se corrige **in-cycle** con espejo sync/async y un test de regresión mockeado que la pinea, y `verify_cycle_closure` devuelve PASS **no-vacuo** para cada paquete medido (con la evidencia positiva de que el driver corrió, no la mera ausencia de findings).
  4. El censo de esta corrida se contrasta explícitamente contra el de la Fase 33 y contra el piso ratificado de `29-SIZING.md`, **declarando cuántas divergencias desaparecieron por la nueva política Null Object** (colapso sin registro) frente a cuántas desaparecieron por corrección — para que la baja de números no pueda leerse como un falso limpio.

**Plans**: 8/8 plans complete

> **Secuenciación (recomendación de `39-RESEARCH.md`, seguida al pie).** Correr en vivo **antes**
> de que aterricen las correcciones de harness escribe basura en ledgers versionados y puede
> quemar baselines write-once. Por eso los planes 01-03 (clasificación, allowlist D-MATZ-33,
> evidencia de corrida y cierre de ciclo no-vacuo) preceden a las cadenas por driver (04-06), que
> preceden a la corrida en vivo (07) y al censo (08). Los planes 04, 05 y 06 quedan en olas
> separadas porque los tres tocan la allowlist explícita de `.github/workflows/ci.yml`: un lock
> bajo `verification/` que no se agrega ahí **en el mismo commit** ship inerte (defecto ya
> committeado en la Phase 36, WR-01).
>
> **Corrección a la premisa de D-05:** `matriz_client` **sí** tiene `aio.py` con un `AsyncClient`
> completo en HEAD, y `main_matriz.py` ya corre ~19 probes async sin importar `ws_client` ni una
> vez. "Ambas superficies" para matriz es `client.py` + `aio.py`, igual que iol y higyrus; ningún
> plan propone camino WebSocket.

**Wave 1** *(paralelo: no comparten archivos)*

- [x] 39-01-PLAN.md — Gate D-MATZ-33 por hostname exacto (D-02, checkpoint humano bloqueante) + clasificación SKIPPED de matriz y higyrus (D-01), con 3 locks nuevos cableados a CI — wave 1
- [x] 39-02-PLAN.md — Suites mockeadas de casos límite del encadenamiento profundo en iol/higyrus/matriz, ambas superficies (SC-2 / D-12) — wave 1

**Wave 2** *(bloqueado por 39-01)*

- [x] 39-03-PLAN.md — `verification/run_evidence.py` + los 4 drivers cableados + cierre de ciclo no-vacuo por conteo de probes (D-09) y semilla del censo (D-10) — wave 2

**Wave 3-5** *(secuenciales: los tres tocan la allowlist de `ci.yml`)*

- [x] 39-04-PLAN.md — iol: cadena `.puntas` en los 4 probes tipados + lock AST (D-03) — wave 3
- [x] 39-05-PLAN.md — higyrus: cadena tipada `Posicion.parking` sin HTTP adicional + lock AST (D-04) — wave 4
- [x] 39-06-PLAN.md — matriz: los 6 alias en sync y async + segregación por venue de los baselines write-once + lock AST (D-05, Open Question 1) — wave 5

**Wave 6** *(bloqueado por 39-01…39-06)*

- [x] 39-07-PLAN.md — Corrida en vivo de los 4 drivers, casos límite forzados, fixes in-cycle con espejo sync/async y regresión mockeada, checkpoint de disposición (D-08, D-12) — wave 6

**Wave 7** *(bloqueado por 39-07)*

- [x] 39-08-PLAN.md — `39-CENSUS.md`: contraste contra Fase 33 y contra el piso ratificado, split colapso-de-política vs corrección real, ausencia medida de ámbito, addendum al ledger de triples retiradas (D-06, D-10, D-11) — wave 7

### Phase 40: Releases breaking coordinados

**Goal**: Los paquetes cuya superficie pública cambió quedan publicados con la ruptura declarada y una tabla de migración que el consumidor puede seguir, y ninguna operación irreversible ocurre sin que un humano la apruebe.
**Depends on**: Phase 39
**Requirements**: PUB-NOBJ-01
**Success Criteria** (what must be TRUE):

  1. **Sólo** los paquetes cuya superficie pública cambió se bumpean y publican, cada uno con bump **breaking** y un callout source-breaking **primero** en el changelog, acompañado de una **tabla de migración vieja→nueva** ejecutable por el consumidor (`market_data["LA"]["price"]` → `market_data.last.price`; `if snapshot.market_data is None` → `if not snapshot.market_data`; `puntas or []` → `puntas`); los paquetes sin cambios NO se re-publican.
  2. `uv.lock` global se refresca **exactamente una vez** para todos los bumps, y el PR llega a CI verde asertado **por conteo explícito** de checks (6 paquetes × py3.12/py3.13 más los 4 gates), nunca por ausencia de la palabra `fail`; el merge usa **merge commit real**, nunca squash (D-11).
  3. Un tag anotado por paquete queda sobre el SHA del merge commit re-resuelto en vivo, `release.yml` **sin editar** publica wheel + sdist por paquete, y la publicación se verifica **post-publicación instalando desde el wheel público** y ejerciendo una cadena profunda en el paquete instalado.
  4. Merge y push de tags quedan detrás de **dos checkpoints humanos independientes**, nunca colapsados en uno solo y nunca auto-aprobados pese a `auto_advance: true` + `mode: yolo` activos en config (precedente D-08 / D-18).

**Plans**: TBD

## Progress

| Phase                                                        | Milestone | Plans | Status      | Completed  |
|--------------------------------------------------------------|-----------|-------|-------------|------------|
| 35. Fundación Null Object — `__bool__` + política del walker | v1.7      | 5/5 | Complete    | 2026-08-29 |
| 36. `market-data-client` — `market_data` tipado              | v1.7      | 3/3 | Complete    | 2026-08-29 |
| 37. `matriz-client` — dicts residuales + alias               | v1.7      | 5/5 | Complete    | 2026-08-29 |
| 38. `iol-client` + auditoría higyrus/ámbito/wallets          | v1.7      | 4/4 | Complete    | 2026-08-29 |
| 39. Verificación en vivo del encadenamiento profundo         | v1.7      | 8/8 | Complete   | 2026-08-30 |
| 40. Releases breaking coordinados                            | v1.7      | 0/?   | Not started | -          |

*(Fases 1-34: ver las tablas de progreso en `milestones/v1.0-…v1.6-ROADMAP.md`.)*

## Backlog

*(Candidate items for next milestone; see `.planning/todos/pending/` + v1.0/v1.1/v1.2/v1.3 milestone audits deferred sections)*

### Deferred to v1.7+ (from v1.6)

- **HARN-VERIF-01 — reparar las firmas de probe stale de `main_matriz.py` en `verification/`** — paquete: `matriz-client`. Archivos: `verification/test_matriz_sweep_snapshot.py` (17 FAILED + 17 ERROR) y `verification/test_main_matriz_login_fail_uniformity.py` (2 FAILED + 2 ERROR). Causa raíz única: ambos llaman a los probes de `main_matriz.py` sin argumentos (`TypeError: probe_get_segments() missing 1 required positional argument: 'client'`), firma pre-migración REFAC-05 de la Phase 15; cada caso cuenta doble porque el teardown de `pytest_httpx` asevera que la respuesta mockeada fue pedida. Explica el **100%** del rojo de `verification/` (19 failed / 19 errors, medido en `33-BASELINE.md` sobre `0a9fdae`). Incluye el gap gemelo de **43 errores de `uv run mypy verification` en 8 archivos**: `verification/` está fuera del `files` de mypy y del scope `^packages/.*/src/` del hook de pre-commit. Es rot **invisible por construcción** — `verification/` nunca corrió en CI (el job `test` pasa una ruta explícita que anula `testpaths`) — no un CI failure. Excluido por escrito del scope de LIVE-TYP-01 (P-13) y deliberadamente NO absorbido en la Phase 34 (releases), que ya rechazó una vez expandir el diff del PR de release por el mismo motivo (ver D-16). Precaución al repararlo: estos dos archivos son el **canario** del refactor de `probe_context` de los planes 33-02/33-03, porque invocan los probes directamente y no vía `main()`.

- **LIVE-MATZ-33 — censo en vivo de `matriz-client` + disposición de S-3/S-4/S-5** — paquete: `matriz-client`. El pase observable de la Phase 33 (plan 33-05, 2026-08-27) **no pudo correr**: `main_matriz.py` aborta en el assert de hostname **D-MATZ-33** (`:2550`) porque `PRIMARY_BASE_URL` apunta a `api.demo.matrizoms.com.ar`, que no es el sandbox remarkets al que la política de seguridad de la Phase 5 restringe la verificación. Las credenciales **sí** autentican (`preflight_33.py` → `AUTH OK`); el bloqueo es de política, no de auth, y **no se debe rodear** (la superficie de matriz incluye entrada de órdenes; prohibición P-05 de 33-05). Queda sin contrastar el piso `≥24` de `29-SIZING.md` (equivalente en triples distintos: 14) y quedan **COULD-NOT-DECIDE** las tres estructurales del paquete: **S-3** (`Instrument.instrumentId` ausente en byCFICode/bySegment, con `marketId`/`symbol` llegando aplanados y descartados como `extra` — *"the highest-consequence finding in the set"* según `29-SIZING.md`), **S-4** (`InstrumentDetail` no declara 7 claves del wire) y **S-5** (`MarketDataSnapshot.LA/.SE/.OI/.CL` no-`Optional` llegando `null`). **Requisito de ventana horaria:** el pase observable tiene que correr **dentro de una sesión de trading de ARG** o S-5 sigue siendo indecidible — un `null` de mercado cerrado no se distingue de un error de modelado (P-12). Colateral: las **nueve** entradas de `_SCHEMA_FILES` declaradas y ausentes en disco (orders / positions / account-report) sólo toman su rama write-once en una corrida exitosa. Detalle completo en `33-CENSUS.md`. **Ampliación (plan 33-06, 2026-08-27):** el mismo gate bloqueó el **censo de valores de los siete campos RESPONSE con alias `Literal`** — `marketId` (`Segment`, `InstrumentId`), `cficode` (`Instrument`, `InstrumentDetail`), `currency` y `orderTypes` (`InstrumentDetail`) y `ordType` (`Order`). Los cuatro alias (`MarketId`, `CFICode`, `Currency`, `OrderType`) quedan confirmados como **decodificando sin enforcement** (`POLICY` de matriz pasa `literal_enforced=False` y `scalar_passthrough=True`, `_decode.py:136`), pero **qué valores manda el vendor sigue sin medirse**: es la mitad abierta del criterio 3. `scripts/literal_census_33.py` ya lleva el gate remarkets-only y corre el censo completo apenas haya un `PRIMARY_BASE_URL` de remarkets con credenciales emitidas para ese host. Colateral del mismo desbloqueo: corregir el párrafo `29-DLOCK-RESPONSE-LITERAL.md:140-142`, que afirma que el stream de divergencias es el mecanismo de censo — la rama `Literal` de `walk_field` (`_decode.py:521-534`) retorna temprano con `literal_enforced=False` y nunca llama al sink, así que no lo es. El lock está firmado, así que la corrección es del firmante. Detalle en `33-LITERALS.md`.

- **LIVE-HIGY-33 — censo en vivo de `higyrus-client` (piso `≥22` sin contrastar)** — paquete: `higyrus-client`. El pre-flight de la Phase 33 (plan 33-05, 2026-08-27) imprimió `AUTH FAIL ConnectError`. Diagnóstico acotado: las tres variables (`HIGYRUS_BASE_URL`, `HIGYRUS_USER`, `HIGYRUS_PASSWORD`) están presentes y el esquema es `https`, pero el hostname **no resuelve por DNS** (`socket.gaierror`) desde la red de desarrollo — es alcanzabilidad de red (host plausiblemente interno/VPN), no rechazo de credenciales. Por D-13 el paquete se registró como `SKIPPED — vendor inalcanzable`, **nunca como cero**. Quedan sin contrastar los 22 triples `missing` del piso: `Movimiento` (9), `PosicionValuada` (11), `Posicion` (2). Al desbloquearlo, el camino es el de operador-corre-y-pega de la Phase 23. Detalle completo en `33-CENSUS.md`.

- **TYP-MD-EXTRA-33 — tipar las 8 claves `extra` en vivo de `market-data-client`** — paquete: `market-data-client`. Ocho triples de especie `extra` medidos en vivo contra `develop` el 2026-08-27 (plan 33-05) que el plan 33-07 **no** corrige: `HealthFeed.symbols_never_delivered` (`int`), `FeedIngestor.ingestor.last_error_age_seconds` (`int`), `.ingestor.last_error_at` (`str`), `.ingestor.subscription` (`dict`), `Symbol.note` (`str`), y las tres del sobre de preview `CalendarConfig.market_after` / `.requires_confirmation` / `.valid`. **Actualización (plan 33-07, 2026-08-27): esas tres YA NO están abiertas** — S-2 se cerró in-cycle dándole al preview su propio modelo (`CalendarConfigPreview` + `PreviewMarket`), que declara las tres, así que este ítem baja de 8 triples a **5**: los cuatro `extra` de `HealthFeed`/`FeedIngestor` más `Symbol.note`. `extra` es **informativo por política** (locks 3 y 4 de la Phase 29: se emite a `INFO` y nunca levanta), así que esto es trabajo de cobertura de superficie, no reparación de defecto. Cuatro de los ocho son **TYP-02**: son visibles porque `Health`/`HealthFeed` se tiparon recién en la Phase 31.

- **SHAPE-MD-REF-33 — corregir la forma declarada de `Instrument` y `Segment` (`market-data-client`)** — paquete: `market-data-client`. Es la **mitad de S-1 que el plan 33-07 deliberadamente NO cerró**, y la razón está registrada: 33-07 arregló el desenvolvimiento del sobre (los parsers iteraban las CLAVES del envelope y devolvían un modelo all-default por clave; findings `F-82`/`F-83`/`F-102`/`F-103`, ya `FIXED`), pero corregir los CAMPOS declarados es un cambio de forma de un modelo **publicado** desde v0.2.0, y el checkpoint bloqueante 33-07 Task 1 existe exactamente para esa clase de cambio. El operator autorizó **tres** cambios de forma (SC-1 preview, SC-2 `MarketDataSnapshot`, SC-3 `Symbol`) y éste **no estaba entre ellos**; aplicarlo igual habría sido el cambio de contrato sin decisión que T-33-44 prohíbe. Lo que queda por corregir, contra los baselines committeados `get-instruments.json` y `get-segments.json`: **`Instrument`** declara `marketId` e `instrumentType`, que el wire no manda, y no declara `market_id`, `currency`, `days_to_maturity`, `maturity`, `outright`, `subscribed` ni `active`, que sí manda (3 de 5 campos declarados —`symbol`, `segment`, `expired`— sí coinciden); **`Segment`** declara `marketSegmentId`, `marketId` y `description`, y el wire manda `segment` y `live_instruments` — **conjuntos disjuntos**, así que hoy toda fila de `get_segments()` sale con sus tres campos vacíos. **Estado post-33-07: la divergencia es VISIBLE, no silenciosa** — antes se escondía detrás de un único `non_dict` terminal por modelo y ahora el walker la reporta campo por campo y levanta bajo `strict_decode`, que es estrictamente mejor pero no es el fix. Requiere disposición de semver: es source-breaking y se suma al bump de la Phase 34 si se hace antes del release, o abre su propio ciclo si se hace después.

- **HARN-DRIFT-33 — deduplicar los findings de `schema drift` por título** — paquete: harness (`main_market_data.py` y los otros cuatro drivers). `_write_or_check_schema` llama a `append_finding` **sin** `idempotent_by_title=True`, así que un mismo drift escribe un bloque `### F-` nuevo por superficie y por pase, con títulos byte-idénticos: la corrida de dos pases del plan 33-05 produjo **22 bloques** de drift para **8 snapshots distintos** (`get_health_feed` ×4, `get_calendar` ×4, `get_calendar_config` ×4, y ×2 los otros cinco). No hay pérdida de censo —nada se descarta— pero infla el archivo de findings y hace que el triage vea duplicados. La rama comparte además el allocator de fids, así que está cubierta por la aserción de consistencia de `verification/test_finding_count_consistency.py`.

### Deferred to v1.6+ (from v1.5)

- **D-16 — enrolar `market-data-client` en el typecheck global** — el paquete sigue ausente de tres listas: el `files` de mypy del root (`pyproject.toml:97`, hoy 5 paquetes), el `root_packages` de import-linter (`pyproject.toml:141-146`, hoy 4) y el loop mypy-tests per-package de `ci.yml:85` (hoy 5). Enrolarlo requiere además **escribir un contrato de import-linter** para `market_data_client._core` (los otros 4 paquetes ya tienen el suyo). Es un gap de **COBERTURA de typecheck, no un CI failure**: todos los checks package-scoped están verdes hoy, y la cobertura real de mypy sobre este paquete la da el hook de pre-commit scoped `files: ^packages/.*/src/` (`.pre-commit-config.yaml:32`). Diferido desde Phase 24 y re-confirmado en Phase 28 (**rechazado** enrolarlo en el PR de release: expandiría el diff). Se archiva acá explícitamente para que deje de rodar en silencio release tras release.

### Deferred to v1.5+ (from v1.4 — market-data-client v2 requirements)

- **MUT-MD-01 / MUT-MD-02** — market-data-client mutations: symbols (`POST /symbols`, `POST /symbols/batch`, `PATCH /symbols/{id}`) + calendar (`PUT/DELETE /calendar/config`, `POST /calendar/config/preview`, `POST /calendar/holidays`, `DELETE /calendar/holidays/{day}`) — require the security mutating-gate
- **STREAM-MD-01** — market-data-client SSE streaming (`GET /marketdata/stream`, `interval` param) via a dedicated transport (matriz `ws_client` pattern)
- **SEC-MD-01** — market-data-client Auth0 token disk cache (`_token_cache.py` + platformdirs, atomic + flock + 0600)
- **SEC-MD-02** — market-data-client JWT signature validation (RS256 against Auth0 JWKS)
- **LIVE-MD-01 real credentialed sweep** — the apparatus is verified; the actual live run against `market-data-develop.bbsa.com.ar` still awaits Auth0 creds + VPN/allowlist

### Deferred to v1.4+ (from v1.3 planning)

- prod-vs-remarkets verification (D-MATZ-27 REQUIRED handoff — still deferred through v1.0/v1.1/v1.2/v1.3/v1.4)
- `matriz_client.ws_client` live verification (WebSocket streaming en daemon thread)
- `cryptography.fernet` token encryption at-rest (operator authorization required; threat-boundary expansion)
- Code-review CR-01 v1.2 Phase 14 (`configure()` no limpia el on-disk token cache de IOL)
- Extender alcance de verificación a `wallets-client` (cuando tenga endpoints reales)

### Resolved in v1.3 — REFAC-06 permanently shelved

- **REFAC-06** — codegen single-source for `client.py`/`aio.py` transport shells × 4 packages. **Permanently shelved 2026-07-03**: two dedicated spikes (unasync SPIKE-005 in v1.2 Phase 12, libcst SPIKE-006 in v1.3 Phase 18) both returned a signed NO-GO for the same content-absence / source-shape-asymmetry root cause under the un-migrated D-02 bar. The duplicate `client.py`/`aio.py` shells are now an **accepted structural feature** of the codebase (the known dual-surface duplication documented in CLAUDE.md). Do not re-open without a new tool class that can synthesize content-absent constructs, or a decision to relax the no-source-migration constraint (D-02). See `.planning/spikes/SPIKE-006-libcst-codegen-tool-choice/DECISION.md` + `Skill("spike-findings-codegen-market-libs")`.

### Deferred to v1.2+ (from v1.1 planning — REFAC-05/SEC-01/ERG-01 shipped in v1.2)

- Automatic `Idempotency-Key` header para retried POSTs
- `findings.toml` machine-readable side-file
- `Client.from_env()` classmethod for explicit env-reading (SKIPPED v1.2 — industry survey found ZERO SDKs with this pattern; implicit env fallback already exists)
- `request_id` UUID per `_request()` invocation threaded through retry log records
- `max_elapsed_seconds` retry budget cap as belt-and-suspenders
- ERR-01 (mocked 403/429/5xx mapping), ERR-02 (mocked token TTL refresh) — v2 requirements del v1.0 backlog
