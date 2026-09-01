# Roadmap: market-libs — Verificación en vivo de clientes

## Milestones

- ✅ **v1.0 Verification cycle** — Phases 1-5 (shipped 2026-06-10) — see [`milestones/v1.0-ROADMAP.md`](./milestones/v1.0-ROADMAP.md)
- ✅ **v1.1 Tech Debt Cleanup** — Phases 6-11 (shipped 2026-06-14) — see [`milestones/v1.1-ROADMAP.md`](./milestones/v1.1-ROADMAP.md)
- ✅ **v1.2 Architecture + Auth/Ergonomics Carry-forwards** — Phases 12-17 (shipped 2026-06-25) — see [`milestones/v1.2-ROADMAP.md`](./milestones/v1.2-ROADMAP.md)
- ✅ **v1.3 Codegen Single-Source (libcst)** — Phases 18-19 (closed 2026-07-03 on signed SPIKE-006 NO-GO; Phase 19 REFAC-06 dropped) — see [`milestones/v1.3-ROADMAP.md`](./milestones/v1.3-ROADMAP.md)
- ✅ **v1.4 market-data-client** — Phases 20-24 (shipped 2026-07-31) — nuevo paquete cliente (solo lectura) contra la API primary-extractor con Auth0 client-credentials, verificado en vivo y publicado v0.1.0 — see [`milestones/v1.4-ROADMAP.md`](./milestones/v1.4-ROADMAP.md)
- ✅ **v1.5 market-data-client · mutaciones** — Phases 25-28 (shipped 2026-08-17) — superficie de **escritura** (symbols + calendar) detrás de mutating-gate default-refuse, verificada en vivo (create→verify→revert) y publicada `market-data-client-v0.4.0` — see [`milestones/v1.5-ROADMAP.md`](./milestones/v1.5-ROADMAP.md)
- ✅ **v1.6 Tipado homogéneo de la superficie pública** — Phases 29-34 (shipped 2026-08-27) — contrato de tipos idéntico y verificable por máquina en los 6 paquetes: decodificación por-campo observable, `iol-client` y los endpoints de ops tipados, gates de CI que sostienen la homogeneidad, verificación en vivo en modo estricto, y publicación de `iol-client-v0.3.0` + `market-data-client-v0.5.0` — see [`milestones/v1.6-ROADMAP.md`](./milestones/v1.6-ROADMAP.md)
- ✅ **v1.7 API tipada con Null Objects** — Phases 35-40 (shipped 2026-08-30) — patrón Null Object en los 6 paquetes: ningún eslabón de cadena puede ser `None`, `dict[str, Any]` desaparece de los campos de modelos públicos, y 4 paquetes publicados con bump breaking + tabla de migración — see [`milestones/v1.7-ROADMAP.md`](./milestones/v1.7-ROADMAP.md)
- 🚧 **v1.8 Cierre de deuda post-v1.7** — Phases 41-45 (in progress) — sin superficie nueva: se cierra el backlog que quedó documentado *con causa medida* al cierre de v1.7 (cobertura Nyquist retroactiva, los dos bloqueos en vivo, la corrección de forma de `Instrument`/`Segment` + su release, y la limpieza del harness)

## Phases

<details>
<summary>✅ v1.7 API tipada con Null Objects (Phases 35-40) — SHIPPED 2026-08-30</summary>

- [x] Phase 35: Fundación Null Object — `__bool__` + política del walker (5/5 plans) — completed 2026-08-29
- [x] Phase 36: `market-data-client` — `market_data` tipado (3/3 plans) — completed 2026-08-29
- [x] Phase 37: `matriz-client` — dicts residuales + alias (5/5 plans) — completed 2026-08-29
- [x] Phase 38: `iol-client` + auditoría higyrus/ámbito/wallets (4/4 plans) — completed 2026-08-29
- [x] Phase 39: Verificación en vivo del encadenamiento profundo (8/8 plans) — completed 2026-08-30
- [x] Phase 40: Releases breaking coordinados (3/3 plans) — completed 2026-08-30

Full detail: [`milestones/v1.7-ROADMAP.md`](./milestones/v1.7-ROADMAP.md)

</details>

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

### 🚧 v1.8 Cierre de deuda post-v1.7 (Phases 41-45) — IN PROGRESS

**Milestone Goal:** Que el backlog documentado al cierre de v1.7 deje de rodar de milestone en milestone: cada ítem que quedó abierto **con causa medida** recibe en v1.8 un resultado igualmente medido — una disposición escrita, un veredicto en vivo, una corrección publicada o una deuda formalmente aceptada. Sin superficie nueva y sin descubrimiento de alcance nuevo: v1.8 no agrega capacidades, cierra las cuentas que v1.7 dejó nombradas.

> **Notas de sizing y restricciones (leer antes de planificar).**
> **La Phase 41 audita historia congelada y por eso va primera y sola.** `/gsd-validate-phase` sobre las Phases 35-39 tiene que correr contra el árbol de v1.7 tal como se shippeó; cualquier cambio de fuente de v1.8 antes de ese punto hace que los hallazgos queden atribuidos al árbol equivocado. No es una preferencia de orden: es la condición de validez del artefacto.
> **El gate de venue de `scripts/literal_census_33.py` está STALE y el backlog lo sobreestima.** La entrada `LIVE-MATZ-33` de abajo afirma que el script "ya tiene el gate listo para correr contra `bbsa`"; verificado falso en HEAD — el script sigue en substring-match pre-Phase-39 (`if "remarkets" not in base:`) y **saltearía en silencio** contra el sandbox ya desbloqueado. Portar el `_VENUE_ALLOWLIST` por igualdad exacta de hostname de `main_matriz.py` es la **primera** tarea de la Phase 42, es un cambio relevante para seguridad, y va detrás de un checkpoint humano bloqueante antes de cualquier tráfico de red. Un `endswith`/`in` "rápido" reintroduce exactamente la debilidad de spoofing que el D-02 de la Phase 39 removió.
> **HARN-01 no es un kwarg.** `idempotent_by_title=True` sobre la rama de schema drift —cuyo título es endpoint-scoped y libre de contenido— haría que toda divergencia *posterior y distinta* sobre ese mismo endpoint se tragara para siempre; y `_next_fid()` se llama **antes** del chequeo de dedupe, así que un no-op quema un fid y rompe el invariante que `verification/test_finding_count_consistency.py` pinnea. Requiere título content-addressed (o dedupe intra-run) + reordenar la asignación de fid + un **test de falsificación**. Nunca relajar la aserción de conteo.
> **Decisión de orden explícita (research la dejó abierta): HARN-01 aterriza DESPUÉS de las corridas en vivo de la Phase 42.** HARN-01 cambia *qué se registra*; el comportamiento de hoy es ruidoso (22 bloques para 8 snapshots) pero **no es lossy**. Correr en vivo sobre el harness conocido-lossless y recién después cambiar el dedupe mantiene el peor caso en "ledger inflado" en vez de "divergencia perdida", que es la clase de fallo que este proyecto existe para eliminar. Por eso la limpieza del harness es la Phase 45 y no la 42.
> **SHAPE-01 se corrige contra la lectura fresca de la Phase 42, no contra el baseline congelado del 2026-07-31.** Ese es el motivo de que vivo vaya antes que shape, y no al revés.
> **El release nunca comparte fase con el trabajo que lo habilita.** Precedente lockeado (v1.5 Phase 28, v1.6 Phase 34, v1.7 Phase 40): la Phase 44 existe separada de la 43 precisamente porque la co-locación es donde el bug de autoría del gate ya se coló **dos veces** — los checkpoints se escribieron `gate="blocking"` en vez de `gate="blocking-human"` y sólo la prosa del plan evitó la auto-aprobación bajo `auto_advance: true` + `mode: yolo`.
> **Granularity `coarse` con 5 fases, deliberado.** No hay compresión válida disponible: 41 no puede fusionarse con nada porque audita un árbol que las otras modifican; 42 no puede fusionarse con 43 porque 43 consume su evidencia; 43 y 44 no pueden fusionarse por el precedente de release; 45 no puede adelantarse por la decisión de orden de arriba. Las 5 fases salen de restricciones estructurales, no de granularidad.

- [x] **Phase 41: Validación Nyquist retroactiva de v1.7** *(primera y sola — audita árbol congelado)* — `/gsd-validate-phase` sobre las Phases 35-39 con disposición de 3 vías por hallazgo, sin flip mecánico de `nyquist_compliant` — NYQ-01 (completed 2026-08-31)
- [x] **Phase 42: Re-chequeos en vivo — DNS de higyrus + port del gate de venue + censo `Literal` de matriz** — higyrus produce un veredicto medido y matriz produce el censo de valores `Literal` de RESPONSE, con el gate del script portado a igualdad exacta de hostname antes de tocar la red — LIVE-01, LIVE-02 (completed 2026-08-31)
- [x] **Phase 43: `market-data-client` — forma de `Instrument`/`Segment` + 5 claves `extra` tipadas** *(fix, sin publicar)* — disposición campo por campo contra la lectura fresca de la Phase 42, fixtures re-derivadas y los 4 gates de CI verdes — SHAPE-01, HARN-02 (completed 2026-09-01)
- [x] **Phase 44: Release `market-data-client` 0.7.0** — bump en los 4 sitios, changelog + tabla de migración, doble gate humano independiente **escrito** `gate="blocking-human"` — PUB-01 — completado 2026-09-01
- [x] **Phase 45: Limpieza del harness — dedupe de drift, comentarios stale, destino de `verification/` de matriz** — dedupe con test de falsificación e invariante de fids intacto, `IN-06` cerrado, `IN-05` retirado, y `HARN-04` decidido por escrito — HARN-01, HARN-03, HARN-04 (completed 2026-09-01)

## Phase Details (v1.8)

### Phase 41: Validación Nyquist retroactiva de v1.7

**Goal**: Las cinco fases de v1.7 que nunca corrieron su validación dejan de tener cobertura desconocida — cada criterio queda con una disposición explícita y con la evidencia que la sostiene nombrada, producida contra el árbol de v1.7 congelado y antes de que v1.8 toque una sola línea de fuente.
**Depends on**: Nothing (primera fase de v1.8; parte del head de v1.7)
**Requirements**: NYQ-01
**Success Criteria** (what must be TRUE):

  1. Existe un artefacto de validación por cada una de las Phases **35, 36, 37, 38 y 39** — cinco, ninguno faltante — y cada uno declara el SHA del árbol de v1.7 contra el que se produjo; ningún archivo fuente de v1.8 cambió antes de que el último de los cinco quedara escrito.
  2. Cada criterio auditado lleva **exactamente una** de las tres disposiciones (`VERIFIED-NOW` / `VERIFIED-HISTORICALLY` / `NOT-VERIFIABLE-RETROACTIVELY`) con su evidencia nombrada, y el conteo por disposición cierra contra el total de criterios enumerados — cero filas sin disponer.
  3. Ningún `nyquist_compliant` pasa a `true` por flip mecánico: sólo cambia donde la disposición es `VERIFIED-NOW` re-ejecutada en esta sesión, y toda fase que conserve ítems `NOT-VERIFIABLE-RETROACTIVELY` lo dice en su propio front-matter en vez de reportarse limpia.
  4. Todo test o lock que el auditor deje en disco está o bien enrolado en el allowlist explícito de CI, o bien declarado **inerte por escrito** con su enrolamiento ruteado al edit consolidado de `ci.yml` de la Phase 45 — un lock que no corre no se cuenta como cobertura.
  5. El alcance queda acotado a las cinco fases nombradas: la entrada `NYQUIST-32-33` sigue en el backlog con su texto intacto, no absorbida en silencio (está en `REQUIREMENTS.md § Out of Scope`).

**Plans**: 7/7 plans complete

Plans:
**Wave 1**

- [x] 41-01-PLAN.md — Preflight: invariante de árbol congelado, doble SHA, y el contrato de auditoría compartido (denominador 62, reglas R-01..R-09, front-matter objetivo, mapa de enforcement de CI, 3 prohibiciones de workflow) *(wave 1)*

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 41-02-PLAN.md — Phase 35: reconstrucción del mapa (12 filas desde los planes) + 13 disposiciones *(wave 2)*
- [x] 41-03-PLAN.md — Phase 36: 11 disposiciones + resolución de la fila que shipeó sin comando declarado *(wave 2)*
- [x] 41-04-PLAN.md — Phase 37: 14 disposiciones bajo clave ordinal + re-apunte del selector vacío *(wave 2)*
- [x] 41-05-PLAN.md — Phase 38: 9 disposiciones (7 re-ejecutadas + 2 históricas con confirmación humana fechada) *(wave 2)*
- [x] 41-06-PLAN.md — Phase 39: 15 disposiciones incl. las 4 no re-verificables declaradas en front-matter (criterio 3b) *(wave 2)*

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 41-07-PLAN.md — Cierre: aritmética contra 62, criterios 3/4/5, declaración inerte ruteada a la Phase 45, rollup y auto-auditoría *(wave 3)*

### Phase 42: Re-chequeos en vivo — DNS de higyrus + port del gate de venue + censo `Literal` de matriz

**Goal**: Los dos bloqueos en vivo que v1.7 dejó abiertos dejan de ser incógnitas — higyrus produce un veredicto medido en vez de un silencio, y matriz produce el censo de valores `Literal` de RESPONSE que el plan 33-06 dejó abierto — con el gate de venue del script de censo endurecido a igualdad exacta de hostname **antes** de la primera llamada de red.
**Depends on**: Phase 41 (la auditoría de historia congelada tiene que cerrar antes del primer cambio de fuente de v1.8)
**Requirements**: LIVE-01, LIVE-02
**Success Criteria** (what must be TRUE):

  1. `scripts/literal_census_33.py` decide el venue por **igualdad exacta de hostname** contra el mismo `_VENUE_ALLOWLIST` que `main_matriz.py` — nunca por substring / `endswith` / `in` — con un test que falsifica el superstring de spoofing (un host tipo `…bbsa.matrizoms.com.ar.attacker.example` es rechazado) y que pinnea que ambos sitios comparten una única fuente; el widening queda autorizado en un checkpoint humano **bloqueante** antes de que salga tráfico.
  2. `higyrus-client` produce un resultado **medido**: o resuelve y corre, o queda `SKIPPED` con la causa re-confirmada en esta sesión (excepción y diagnóstico citados, no heredados del reporte de la Phase 39) y con el destino `LIVE-HIGY-33` renombrado — nunca un cero ni un silencio que se lea como limpio (precedente D-13).
  3. El censo reporta los valores observados de los cinco campos `Literal` de RESPONSE (`marketId`, `cficode`, `currency`, `orderTypes`, `ordType`) con **venue y timestamp en el encabezado**, o declara explícitamente qué campo no se pudo medir y por qué; y el D-lock (b) de v1.6 — los campos de RESPONSE **no** se cierran como `Literal` — queda reafirmado, no revocado por el mero hecho de que ahora exista un censo.
  4. `verification/mutation_gate.py` queda **byte-idéntico** y el order entry sigue fail-closed bajo `bbsa`: el widening es del gate de lectura del censo, jamás del gate de mutación.
  5. La corrida deja en disco una **lectura fresca del wire** de `/instruments` y `/segments` de `market-data-client`, fechada en esta sesión, que es la base de evidencia que consume la Phase 43 — el baseline committeado del 2026-07-31 queda explícitamente marcado como no-autoritativo para SHAPE-01.

**Plans**: 6/6 plans complete

Plans:

**Wave 1**

- [x] 42-01-PLAN.md — Port del gate de venue por import (D-01), header venue/timestamp del censo, flag `--matriz-only`, lock de falsificación enrolado en CI, y checkpoint humano bloqueante que habilita el tráfico *(wave 1)*

**Wave 2** *(bloqueada por el checkpoint del plan 42-01)*

- [x] 42-02-PLAN.md — Censo `Literal` de matriz en vivo contra `bbsa` + `42-CENSUS.md` con venue, timestamp y D-lock (b) reafirmado *(wave 2)*
- [x] 42-03-PLAN.md — Medición de la alcanzabilidad de higyrus + corrida del driver completo con sobre de evidencia fechado *(wave 2)*
- [x] 42-04-PLAN.md — `capture()` con envelope timestampeado en `main_market_data.py`, corrida en vivo y `42-WIRE-READ.md` committeado *(wave 2)*

**Wave 3** *(bloqueada por 42-03)*

- [x] 42-05-PLAN.md — Rename condicional D-06 en los 11 sitios vivos + regeneración del sobre por corrida real *(wave 3)*

**Wave 4** *(bloqueada por 42-02, 42-04 y 42-05)*

- [x] 42-06-PLAN.md — Cierre: corrección del backlog (Q5), disposición de los 5 criterios en `42-CLOSURE.md` y gate cross-fase *(wave 4)*

### Phase 43: `market-data-client` — forma de `Instrument`/`Segment` + 5 claves `extra` tipadas

**Goal**: `market-data-client` deja de declarar campos que el wire no manda y de ignorar campos que sí manda — `get_segments()` deja de devolver filas enteramente vacías, `Instrument` refleja el payload real, y las cinco claves `extra` medidas quedan tipadas — todo en un único cambio de `models.py`, verificado y listo para publicar pero **sin** publicar.
**Depends on**: Phase 42 (la corrección se evidencia contra la lectura fresca del wire, no contra el baseline congelado)
**Requirements**: SHAPE-01, HARN-02
**Success Criteria** (what must be TRUE):

  1. Existe una tabla de disposición **campo por campo** para `Instrument` y `Segment`: cada campo declarado hoy y cada clave del wire fresco recibe exactamente una disposición (`alias aditivo` / `remover` / `agregar` / `mantener`) con la evidencia citada — cero filas sin disponer — y `Instrument.marketId` queda dispuesto como **alias aditivo** siguiendo el precedente D-22 de `Symbol.marketId`, nunca como rename.
  2. `get_segments()` devuelve filas **pobladas** contra el payload real medido — hoy sus tres campos declarados son disjuntos del wire y toda fila sale vacía; el antes/después se demuestra con la medición, no se afirma.
  3. Las cinco claves `extra` restantes (`HealthFeed.symbols_never_delivered`, `FeedIngestor.last_error_age_seconds` / `.last_error_at` / `.subscription`, `Symbol.note`) quedan declaradas y decodifican tipadas, y el censo de divergencias deja de reportarlas como `extra` **sin** que ninguna aparezca como `missing` en su lugar — el flip `extra`→`missing` es una regresión disfrazada de fix.
  4. Las fixtures de test afectadas se **re-derivan** de los baselines medidos, con una aserción de que el conjunto de claves de cada fixture es subconjunto del baseline — ninguna se renombra para que siga pasando.
  5. Los 4 gates de CI de v1.6 quedan verdes, el cambio se espeja donde corresponda en `client.py` / `aio.py` (o se demuestra **por medición** que los parsers genéricos no necesitan cambio), y la fase **no** bumpea versión ni publica: el release es la Phase 44.

**Plans**: 3/3 plans complete

**Wave 1**

- [x] 43-01-PLAN.md — `Instrument` + `Segment` reconciliados contra la lectura fresca del wire (D-01…D-06) y los 6 archivos de test re-derivados *(wave 1)*

**Wave 2** *(bloqueada por 43-01 — mismo `models.py`)*

- [x] 43-02-PLAN.md — HARN-02: las 5 claves `extra` tipadas (`FeedSubscription` nueva, D-08…D-11) + el helper de subconjunto de claves de D-13 *(wave 2)*

**Wave 3** *(bloqueada por 43-01 y 43-02)*

- [x] 43-03-PLAN.md — Cierre: docstring de `_core.py` (D-14), `43-DISPOSITION.md` (criterios 1/2/5), backlog del dereference del driver y los 4 gates de CI verdes sin bump *(wave 3)*

### Phase 44: Release `market-data-client` 0.7.0

**Goal**: La corrección de forma llega a los consumidores como una release publicada con su tabla de migración, y las dos operaciones irreversibles pasan por dos gates humanos independientes que esta vez están **escritos** como tales en el plan, no sólo respetados por accidente de prosa.
**Depends on**: Phase 43
**Requirements**: PUB-01
**Success Criteria** (what must be TRUE):

  1. `market-data-client` **0.7.0** está publicado: tag anotado sobre un merge commit real de dos padres, corrida de `release.yml` verde, GitHub Release con wheel + sdist — y se verifica **instalando desde el wheel público** en un entorno descartable fuera del repo, no leyendo el reporte de la corrida.
  2. La versión `0.7.0` es consistente en los **4 sitios** de versión, `uv.lock` se refresca **exactamente una vez**, y `release.yml` queda sin editar (séptima reutilización sin cambios).
  3. `README.md` lleva el callout de ruptura + la **tabla de migración vieja→nueva campo por campo** de `Instrument`/`Segment`: un consumidor puede leer de ahí qué acceso cambió sin abrir el diff.
  4. Los dos checkpoints (merge y push de tag) están autorizados literalmente como `gate="blocking-human"` en el archivo de plan, son independientes entre sí, y ninguno se auto-aprueba pese a `auto_advance: true` + `mode: yolo` — la autoría del gate se verifica **en el propio archivo de plan**, no sólo en el comportamiento observado.
  5. Ningún otro paquete se publica en esta fase, y los conteos de tags de los otros cinco paquetes quedan idénticos al baseline pre-fase — sólo cambió la superficie de `market-data-client`.

**Plans**: 0/3 plans executed

Plans:
**Wave 1**

- [x] 44-01-PLAN.md — Prep reversible: bump de los 4 sitios a `0.7.0` (D-01), fold de `FeedSubscription` (D-05), changelog `### v0.7.0` con las dos tablas de migración (D-03/D-04), `uv lock` único + `uv sync` (D-02), mirror local de CI, scan de credenciales y push de la branch `milestone/v1.8-*` (D-07) *(wave 1)*

**Wave 2** *(bloqueada por 44-01 — el PR necesita la branch pusheada)*

- [x] 44-02-PLAN.md — PR de release + conteo positivo 15/15 (D-11) + auditoría de autoría del gate en el propio archivo (criterio 4), **primer gate humano bloqueante** (D-08a) y merge real de dos padres *(wave 2, `autonomous: false`)* — completado 2026-09-01: PR #16 mergeado, merge commit `bca1add0`, dos padres, operador respondió "approved"

**Wave 3** *(bloqueada por 44-02 — el tag va sobre el merge commit re-resuelto)*

- [x] 44-03-PLAN.md — **Segundo gate humano bloqueante** (D-08b), tag anotado sobre el SHA re-resuelto y pusheado por nombre (D-09), Release con wheel + sdist, invariancia de conteos de tags (D-10) y verificación post-publicación desde el wheel público fuera del repo (D-12) *(wave 3, `autonomous: false`)* — completado 2026-09-01: tag `market-data-client-v0.7.0` publicado, Release con wheel+sdist, wheel público instalado y verificado en venv 3.12 fuera del repo, auditoría de autoría de gates cerrada en 0/2

### Phase 45: Limpieza del harness — dedupe de drift, comentarios stale, destino de `verification/` de matriz

**Goal**: El harness de verificación deja de mentir en dos direcciones — deja de inflar el ledger con bloques duplicados y deja de arrastrar en silencio archivos que nunca corren — y la deuda de `verification/` de matriz, rota desde la Phase 15, recibe una decisión escrita en vez de rodar un milestone más.
**Depends on**: Phase 41 (para consolidar el enrolamiento en CI de cualquier lock que genere) y Phase 42 (decisión de orden: el dedupe aterriza **después** de las corridas en vivo, ver notas del milestone)
**Requirements**: HARN-01, HARN-03, HARN-04
**Success Criteria** (what must be TRUE):

  1. Un mismo schema drift repetido deja de escribir un bloque `### F-` nuevo por pase, **y** un test de **falsificación** prueba que una divergencia *distinta* sobre el mismo endpoint sigue escribiéndose — el dedupe no puede convertirse en pérdida permanente de censo.
  2. El invariante de conteo de fids (`verification/test_finding_count_consistency.py`) sigue verde **sin aflojarse**: la asignación de fid se reordena respecto del chequeo de dedupe para que un no-op no queme un fid, en vez de relajar la aserción.
  3. `HARN-04` queda resuelto con una decisión **escrita y fechada**: reparar los dos archivos rotos con un presupuesto declarado por adelantado **y** enrolamiento en el allowlist de CI, o aceptar formalmente la deuda con su razón — "reparar sin enrolar" no es una opción admisible, porque garantiza el re-rot (el gemelo de mypy sobre `verification/` queda explícitamente fuera de alcance).
  4. El comentario stale de la Phase 37 dice el número **medido** (337 definitions scanned, medido el 2026-09-01 sobre el commit `fe323d6`, no 330), `IN-06` queda cerrado con el archivo dentro del allowlist explícito de `ci.yml`, e `IN-05` queda **retirado** del backlog por estar ya resuelto en la Phase 40 — verificado contra el código, no asumido del reporte. *(Nota: este criterio decía originalmente `336`, cifra medida antes de las Phases 43/44; el movimiento de superficie de esas fases la dejó stale y el plan 45-01 re-midió `337` corriendo el propio gate, tal como D-05 ENMENDADA lo exige.)*
  5. Los edits de `ci.yml` de todo el milestone llegan en **un** cambio consolidado del allowlist, y CI queda verde en las 12 patas de la matriz (6 paquetes × py3.12/py3.13) más los jobs `lint`, `pre-commit` y `typecheck`.

**Plans**: 5/5 plans complete

Plans:
**Wave 1**

- [x] 45-01-PLAN.md — HARN-03 mecánico: docstring del gate re-medido y pinneado (D-05 ENMENDADA), fold-in `DRV-MD-SEG-43` (D-09) y retiro de `IN-05` (D-07) *(wave 1)*
- [x] 45-04-PLAN.md — HARN-04: decisión escrita y fechada (`45-HARN-04-DECISION.md`) + cierre de Q4 dentro de un archivo ya enrolado *(wave 1)*

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 45-02-PLAN.md — HARN-01 por TDD: test de falsificación de D-04 (colapso + NO-colapso + fid no quemado) y guarda `(func, digest)` en `main_market_data.py` *(wave 2, `type: tdd`)*

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 45-03-PLAN.md — HARN-01: los 6 sitios de drift restantes con el no-op de SU contrato de retorno + lock por AST de orden y forma sobre los 7 sitios *(wave 3)*

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 45-05-PLAN.md — Edit consolidado único de `ci.yml` (13 → 18, D-06/D-10/D-11), censo post-fase y cierre del backlog *(wave 4)*

## Progress

| Phase                                                        | Milestone | Plans | Status      | Completed  |
|--------------------------------------------------------------|-----------|-------|-------------|------------|
| 35. Fundación Null Object — `__bool__` + política del walker | v1.7      | 5/5 | Complete    | 2026-08-29 |
| 36. `market-data-client` — `market_data` tipado              | v1.7      | 3/3 | Complete    | 2026-08-29 |
| 37. `matriz-client` — dicts residuales + alias               | v1.7      | 5/5 | Complete    | 2026-08-29 |
| 38. `iol-client` + auditoría higyrus/ámbito/wallets          | v1.7      | 4/4 | Complete    | 2026-08-29 |
| 39. Verificación en vivo del encadenamiento profundo         | v1.7      | 8/8 | Complete    | 2026-08-30 |
| 40. Releases breaking coordinados                            | v1.7      | 3/3 | Complete    | 2026-08-30 |
| 41. Validación Nyquist retroactiva de v1.7                   | v1.8      | 7/7 | Complete    | 2026-08-31 |
| 42. Re-chequeos en vivo — higyrus + venue gate + censo `Literal` | v1.8   | 6/6 | Complete   | 2026-08-31 |
| 43. `market-data-client` — forma `Instrument`/`Segment` + `extra` | v1.8 | 3/3 | Complete    | 2026-09-01 |
| 44. Release `market-data-client` 0.7.0                       | v1.8      | 3/3 | Complete    | 2026-09-01 |
| 45. Limpieza del harness                                     | v1.8      | 5/5 | Complete    | 2026-09-01 |

*(Fases 1-34: ver las tablas de progreso en `milestones/v1.0-…v1.6-ROADMAP.md`.)*

## Backlog

*(Candidate items for next milestone; see `.planning/todos/pending/` + v1.0/v1.1/v1.2/v1.3 milestone audits deferred sections)*

> **Absorbido por v1.8 (2026-08-31).** Las entradas de abajo dejan de ser backlog libre y quedan
> ruteadas a una fase: `NYQUIST-35-39` → **Phase 41** (NYQ-01); `LIVE-HIGY-42` (ex `LIVE-HIGY-33`,
> renombrado el 2026-08-31 por D-06) → **Phase 42**
> (LIVE-01); el censo de `Literal` de RESPONSE de `LIVE-MATZ-33` → **Phase 42** (LIVE-02);
> `SHAPE-MD-REF-33` → **Phase 43** (SHAPE-01); `TYP-MD-EXTRA-33` → **Phase 43** (HARN-02);
> `HARN-DRIFT-33` → **Phase 45** (HARN-01); el cosmético `IN-01`/`IN-06` de la Phase 37 →
> **Phase 45** (HARN-03, con `IN-05` a retirar); `HARN-VERIF-01` → **Phase 45** (HARN-04, como
> decisión reparar-vs-aceptar, no como reparación asumida). El texto original de cada entrada se
> conserva abajo sin editar — es la evidencia con la que se planifican esas fases.
>
> **Corrección al texto de `LIVE-MATZ-33`:** la afirmación de que `scripts/literal_census_33.py`
> "ya lleva el gate remarkets-only y corre apenas haya un `PRIMARY_BASE_URL`" está **verificada
> falsa en HEAD** — el script sigue en substring-match pre-Phase-39 y saltearía en silencio contra
> el sandbox `bbsa` ya desbloqueado. El port del `_VENUE_ALLOWLIST` por igualdad exacta de hostname
> es la primera tarea de la Phase 42.
>
> **Q5 RESUELTA (2026-08-31, plan 42-06).** El port se ejecutó (plan 42-01, commits `7cc103a` RED /
> `99fb17c` GREEN) y el censo corrió contra `bbsa` (plan 42-02, `42-CENSUS.md`). Las dos entradas
> **forward-looking** de abajo —la de `LIVE-MATZ-33` de v1.7 y la de "RESPONSE-Literal value census
> de matriz" en § Deferred to v1.8+— quedaron corregidas y anotadas con el resultado medido, así que
> el próximo milestone ya no hereda la afirmación falsa. El **texto histórico de la Phase 33**
> (última entrada, `LIVE-MATZ-33 (histórico, Phase 33)`) se conserva **verbatim y sin editar**,
> incluida su afirmación hoy falsificada: es la evidencia de procedencia con la que se planificó la
> Phase 42, y esta nota es su corrección. Ninguna fase posterior debe leer ese párrafo histórico
> como estado de HEAD.

### Nuevos en v1.8 (from Phase 43)

- **DRV-MD-SEG-43 — `main_market_data.py:1541-1542` dereferencia `Segment.marketSegmentId`, el campo que la Phase 43 removió** — paquete: harness (driver de `market-data-client`). `probe_parity_sync_async` construye `ids_sync`/`ids_async` con `sorted(s.marketSegmentId for s in seg_sync)` sobre un `Segment` que desde el plan 43-01 declara `segment` / `live_instruments` (D-06). **Ningún gate estático de CI lo detecta, y esto está MEDIDO, no supuesto:** el `files` de mypy del root (`pyproject.toml:97`) lista seis rutas `packages/*/src` y el driver vive en la raíz del repo, así que el job `typecheck` nunca lo mira; el hook de pre-commit está scoped a `files: ^packages/.*/src/` (`.pre-commit-config.yaml:32`); y `verification/test_main_market_data_deep_chain.py` parsea el driver con `ast` **sin importarlo**, auditando cadenas de acceso profundo de market data, no la existencia de atributos. Apuntar mypy al archivo a mano **sí** lo levanta — `uv run mypy main_market_data.py` → `main_market_data.py:1542: error: "Segment" has no attribute "marketSegmentId" [attr-defined]` —, que es exactamente la medición de por qué el gap es de alcance de gate y no de tipabilidad. **Consecuencia:** el `try/except Exception` de `:1543` lo degrada a un finding de handler en la próxima corrida en vivo, no a un crash — el mismo modo de falla que el code review CR-01 de la Phase 37 documentó, y el probe de paridad de segments queda ciego en silencio. **Disposición de la Phase 43: NO se corrige ahí** — D-16 lockea el alcance de la fase a `models.py` + tests + el docstring de D-14, y este sitio no es ninguno de los tres. Corrección estimada: 2 líneas, sin lógica, sin obligación de espejo sync/async por ser un dereference. **→ candidato v1.8 Phase 44** (que ya toca el paquete para el release y publica la tabla de migración vieja→nueva donde este campo aparece) **o Phase 45** (limpieza del harness, que es donde vive el archivo). Detalle en `43-DISPOSITION.md` § 5. **CERRADO en la Phase 45 (plan 45-01, D-09):** las dos líneas ahora dereferencian `s.segment` y `uv run mypy main_market_data.py` pasó de 2 errores `attr-defined` a `Success: no issues found in 1 source file`. La entrada se conserva porque su medición de **por qué ningún gate lo detectó** es la evidencia que cita la declaración por escrito de ese gap (Q5 — mypy sobre los drivers `main_*.py` de la raíz —, ruteada al plan 45-05 con destino en el backlog v1.9; apuntar mypy a los 5 drivers dentro de esta fase es scope creep no medido).
- **SURF-MD-FEEDSUB-43 — `FeedSubscription` está en `models.__all__` pero no en el `__all__` del paquete** — paquete: `market-data-client`. Inconsistencia con `FeedMarket` y `FeedPipeline`, que sí están en ambos. **Efecto secundario real, no cosmético:** `tools/check_surface_types.py` resuelve candidatos desde el `__all__` de cada `__init__.py` hacia afuera, así que los **15 campos** de la clase nueva no quedan escaneados por el gate — su `0 violations` es verdadero pero no cubre esta clase. **Disposición de la Phase 43: no se corrige ahí** (D-16). **→ candidato v1.8 Phase 44**, que ya toca `__init__.py` para el bump de versión. Detalle en `43-DISPOSITION.md` § 6.

### Deferred to v1.8+ (from v1.7)

- **NYQUIST-35-39 — correr `/gsd-validate-phase` en las Phases 35-39** — sólo la Phase 40 llegó a `nyquist_compliant: true`; las otras cinco tienen Nyquist configurado activo pero nunca ejecutado (`VALIDATION.md` status `draft`). Gap de cobertura, no de compliance — flagged por el audit de cierre del milestone v1.7 (`v1.7-MILESTONE-AUDIT.md`). **→ v1.8 Phase 41 (NYQ-01).**
- **RESPONSE-Literal value census de matriz (S-4 + los 7 campos alias)** — ver la entrada `LIVE-MATZ-33` arriba: Phase 39 desbloqueó y midió S-3/S-5 pero no tocó el censo de valores `Literal` de RESPONSE que el plan 33-06 dejó abierto (`marketId`/`cficode`/`currency`/`orderTypes`/`ordType`); ~~`scripts/literal_census_33.py` ya tiene el gate remarkets-only listo para correr contra el sandbox `bbsa` ahora desbloqueado.~~ **Verificado falso en HEAD y corregido por la Phase 42 (2026-08-31):** el gate estaba en substring-match pre-Phase-39 (`if "remarkets" not in base:`) y habría salteado **en silencio** contra `bbsa`; el plan 42-01 lo portó a igualdad exacta de hostname por `from main_matriz import _VENUE_ALLOWLIST, _venue_token` (fuente única, pinneada por identidad `is` y por 13 casos de spoofing en `verification/test_literal_census_venue_gate.py`, enrolado en la allowlist de `ci.yml`). **→ v1.8 Phase 42 (LIVE-02) — CORRIDO el 2026-08-31 contra `bbsa`; resultado en `42-CENSUS.md`.**
- **Cosmético Phase 37** — `IN-01` comentario stale del gate ("330 definitions scanned"); `IN-06` `verification/test_public_surface.py` sigue fuera de la lista explícita del job de lint de CI (pre-existente). Ninguno bloqueante. **→ v1.8 Phase 45 (HARN-03).** `IN-05` (`matriz_client/__init__.py` sin `__version__`) queda **RETIRADO de este backlog: resuelto en la Phase 40** — verificado contra el código en el plan 45-01 (D-07), no asumido del reporte: `uv run python -c "import matriz_client; print(matriz_client.__version__)"` → `0.3.0`. `IN-01` quedó cerrado por el mismo plan 45-01 (bloque histórico pinneado a `00ffb2f~1`, bloque vigente re-medido 187 / 337 / 467 el 2026-09-01).
- **Deuda documentada in-code de Phase 39 (D39-01..04, WR-02)** — respuestas 204/vacías escapan las jerarquías `IOLClientError`/`MatrizClientError` (decisión de alcance deliberada, aseverada por tests de regresión); `verification/findings.py::append_finding` no es content-addressed cross-run para hallazgos de probe no-terminales (deuda de harness, operator-approved fuera de alcance, junto a `HARN-VERIF-01`); un mock de matriz codificaba una forma de instrumento anidada que el vendor nunca emite; higyrus no captura `httpx.ConnectTimeout` en la rama vendor-unreachable (límite de alcance documentado en el propio código). Ninguno silencioso — todos documentados con destino nombrado. **Parcialmente → v1.8 Phase 45 (HARN-01 cubre el content-addressing de `append_finding`); D39-01/02/04 siguen en backlog.**

### Deferred to v1.9+ (from v1.8)

- **GATE-DRV-MYPY-45 — ningún gate de CI apunta a los 5 drivers `main_*.py` de la raíz** — paquete: harness (los 5 drivers de la raíz del repo, 13.370 líneas entre los cinco). **El hecho medido:** apuntar mypy **a mano** a un driver de la raíz sí lo analiza y sí levanta errores reales — fue exactamente así como se detectó `DRV-MD-SEG-43` (`uv run mypy main_market_data.py` → `main_market_data.py:1542: error: "Segment" has no attribute "marketSegmentId" [attr-defined]`, `45-RESEARCH.md` Hallazgo 12). Ese defecto vivió sin detectarse desde la Phase 43 y sólo apareció porque alguien apuntó la herramienta a mano. **La causa es de ALCANCE de gate, no de tipabilidad, y está medida en las tres piezas:** (i) el `files` de mypy del root (`pyproject.toml:97`) lista **seis rutas `packages/*/src`** y ningún archivo de la raíz; (ii) el hook de mypy de pre-commit está scoped a `files: ^packages/.*/src/` (`.pre-commit-config.yaml:32`); (iii) el job `typecheck` de CI invoca `uv run mypy` **sin argumentos** (`ci.yml:123-124`), así que hereda ese `files` — `Success: no issues found in 75 source files`, y **ninguno de los 75 es un `main_*.py`**. Colateral que cierra la última salida: el lock de deep-chain de market-data (`verification/test_main_market_data_deep_chain.py:147`) **parsea el driver por AST sin importarlo**, así que tampoco lo ejercita bajo un type checker. **Por qué NO se cerró en la Phase 45:** apuntar mypy a 5 archivos de miles de líneas dentro de una fase de **limpieza** es scope creep de tamaño **no medido** — no hay medición de cuántos errores nuevos levantaría, y una fase cuyo tema es dejar de mentir sobre su propio alcance no puede abrirse un frente cuyo tamaño no midió. La Phase 45 **arregló el sitio** (`DRV-MD-SEG-43`, plan 45-01, `4039551`) y **no cerró el gate**, y lo declaró por escrito en vez de silenciarlo. **Primer paso al retomarlo:** medir el conteo de errores de `uv run mypy main_iol.py main_higyrus.py main_matriz.py main_ambito_financiero.py main_market_data.py` **antes** de decidir la forma del gate (¿extender `files`? ¿un step propio con su propio `--follow-imports`?) — el presupuesto sale de esa medición, no de una estimación. Declarado con medición pegada en `45-HARN-04-DECISION.md § 4` (Q5 de `45-CONTEXT.md`), y ruteado acá por el plan 45-05. **→ v1.9.**

### Deferred to v1.7+ (from v1.6)

- **HARN-VERIF-01 — reparar las firmas de probe stale de `main_matriz.py` en `verification/`** — paquete: `matriz-client`. Archivos: `verification/test_matriz_sweep_snapshot.py` (17 FAILED + 17 ERROR) y `verification/test_main_matriz_login_fail_uniformity.py` (2 FAILED + 2 ERROR). Causa raíz única: ambos llaman a los probes de `main_matriz.py` sin argumentos (`TypeError: probe_get_segments() missing 1 required positional argument: 'client'`), firma pre-migración REFAC-05 de la Phase 15; cada caso cuenta doble porque el teardown de `pytest_httpx` asevera que la respuesta mockeada fue pedida. Explica el **100%** del rojo de `verification/` (19 failed / 19 errors, medido en `33-BASELINE.md` sobre `0a9fdae`). Incluye el gap gemelo de **43 errores de `uv run mypy verification` en 8 archivos**: `verification/` está fuera del `files` de mypy y del scope `^packages/.*/src/` del hook de pre-commit. Es rot **invisible por construcción** — `verification/` nunca corrió en CI (el job `test` pasa una ruta explícita que anula `testpaths`) — no un CI failure. Excluido por escrito del scope de LIVE-TYP-01 (P-13) y deliberadamente NO absorbido en la Phase 34 (releases), que ya rechazó una vez expandir el diff del PR de release por el mismo motivo (ver D-16). Precaución al repararlo: estos dos archivos son el **canario** del refactor de `probe_context` de los planes 33-02/33-03, porque invocan los probes directamente y no vía `main()`. **→ v1.8 Phase 45 (HARN-04) como DECISIÓN reparar-vs-aceptar con presupuesto declarado; el gemelo de mypy queda fuera de alcance por escrito.**
  **→ RESUELTO en la v1.8 Phase 45 (2026-09-01) POR DECISIÓN ESCRITA — disposición: `ACEPTAR COMO DEUDA DOCUMENTADA`, NO `reparar`.** El texto de arriba se conserva verbatim y sin editar: su medición de causa raíz es la evidencia que cita el documento de decisión. **Documento:** `.planning/phases/45-limpieza-del-harness-dedupe-de-drift-comentarios-stale-desti/45-HARN-04-DECISION.md`, fechado **2026-09-01** (criterio 3 del ROADMAP, *"decisión escrita y fechada"*, satisfecho de forma literal). Los tres ítems que D-08 exigía están respondidos **por archivo**: (1) `test_matriz_sweep_snapshot.py` no asevera nada que un test enrolado no asevere —declara su propia supersession **in-code**, apuntando a `test_main_matriz_risk_envelope_keys.py`, que sí corre en CI—, mientras que `test_main_matriz_login_fail_uniformity.py` **sí** aseveraba exactamente una cosa huérfana (*`probe_login_sync` devuelve `FINDING`, no `FAIL`* — CR-02 de la Phase 11), y el documento **se niega a redondearla** a la "respuesta esperada"; (2) el rol de **canario de `probe_context`** queda **TRANSFERIDO** a `verification/test_probe_context_coverage.py`, y la transferencia es **real** porque ese archivo quedó **enrolado en el allowlist de CI** por el plan 45-05 (`d6b34f0`) — sin enrolamiento habría sido "renombrar el abandono"; (3) los **3 tests verdes** están nombrados uno por uno con destino, y **no se pierden**: no hay `git rm`, los 2 archivos quedan en disco con un puntero in-code al documento fechado. **Q4 se cerró POR IMPLEMENTACIÓN, no por descarte:** la aserción huérfana vive ahora en `test_login_sync_probe_returns_finding_never_fail` (lock por AST, no por substring) dentro de `verification/test_main_matriz_skip_line_shape.py`, un archivo que **ya** corría en CI — no se enroló nada nuevo ni se reparó nada para conseguirlo (plan 45-04, `8f34c40`). **El gemelo de mypy sobre `verification/` sigue FUERA DE ALCANCE por escrito** (`REQUIREMENTS.md § Out of Scope`), tal como esta misma entrada lo pedía. La rama *"reparar"* queda **diferida, no descartada**: exige presupuesto declarado por adelantado y su propia sub-fase, y la estimación heredada de "38 firmas de argumento" **no fue re-medida** en la Phase 45 y **debe re-medirse antes de planificarla**. Detalle completo, con comandos y salidas pegadas, en `45-HARN-04-DECISION.md` §§ 1-3 y § 7.

- **LIVE-MATZ-33 — censo en vivo de `matriz-client` + disposición de S-3/S-4/S-5 — PARCIALMENTE RESUELTO en v1.7 Phase 39 (2026-08-30).** El gate D-MATZ-33 se amplió de substring-match a un allowlist explícito de hostname que admite `bbsa.matrizoms.com.ar` (checkpoint humano D-02, `39-01-PLAN.md`), desbloqueando la primera corrida en vivo real de matriz desde v1.0. **S-3** y **S-5** quedaron medidos y contabilizados en `39-CENSUS.md` (la resta 14−5−2=7 los incluye); la corrida encontró y corrigió in-cycle el bug real de `byCFICode`/`bySegment` (identificador de instrumento descartado en silencio, ~9160 instrumentos). **Sigue abierto:** el censo de valores `Literal` de RESPONSE (**S-4** y los 7 campos con alias) mencionado más abajo (Ampliación plan 33-06) — Phase 39 no lo tocó. Texto original de la Phase 33 preservado abajo para contexto histórico. **→ v1.8 Phase 42 (LIVE-02).**
  **→ Estado medido en v1.8 Phase 42 (2026-08-31) — la mitad S-4 quedó MEDIDA; corrección de Q5 incluida.** Esta entrada **ya no afirma** que `scripts/literal_census_33.py` "ya lleva el gate remarkets-only y corre el censo completo apenas haya un `PRIMARY_BASE_URL` de remarkets". El hecho verificado en HEAD es el contrario: el script seguía en **substring-match pre-Phase-39** (`if "remarkets" not in base:`) y habría **salteado en silencio** contra `bbsa`. El plan 42-01 portó el gate a **igualdad exacta de hostname por import** de `main_matriz.py` (`_VENUE_ALLOWLIST` + `_venue_token`, fuente única pinneada por identidad `is`, 13 casos de spoofing falsificados, lock enrolado en `ci.yml`), y recién entonces el plan 42-02 corrió el censo. Encabezado verbatim de la corrida autoritativa: `CENSUS-HEADER venue=bbsa captured_at=2026-08-31T21:11:53.196947+00:00 allowlist_size=2`, exit `0`, `CENSUS: matriz=RAN iol=NOT-REQUESTED (--matriz-only)`. Disposición de los cinco campos — **cero filas sin disponer**: `marketId` **MEDIDO** (1 valor), `cficode` **MEDIDO** (15 valores), `currency` **MEDIDO** (2), `orderTypes` **MEDIDO** (6), `ordType` **NO MEDIBLE EN ESTA CORRIDA** (la cuenta `bbsa` devolvió `orders` presente y de longitud 0 en los dos endpoints de órdenes — causa medida sobre el payload capturado, no supuesta; no se emitió ninguna orden para fabricar una fila ni se copió el conjunto declarado como si fuera observado). Hallazgo material: el vendor emite **8 valores fuera de los alias `Literal` declarados** (6 en `CFICode`, 2 en `OrderType`) que el stream de divergencias **no** reporta. **El D-lock (b) de v1.6 sigue EN VIGOR y sale reforzado, no revocado:** con enforcement, una sola corrida de lectura habría fallado sobre 9675 instrumentos. Los 8 valores quedan **registrados, no aplicados** (ampliar `types.py` es cambio de forma de un paquete publicado → disposición de semver propia). **Sigue abierto de este ítem:** `ordType` hasta una corrida con órdenes en la cuenta, y el piso `≥24` de `29-SIZING.md` (14 en triples distintos) — el censo cuenta **valores de vocabulario**, no triples de divergencia, y las unidades no se restan entre sí. Detalle completo en `42-CENSUS.md`; disposición formal en `42-CLOSURE.md`.

- **LIVE-MATZ-33 (histórico, Phase 33) — censo en vivo de `matriz-client` + disposición de S-3/S-4/S-5** — paquete: `matriz-client`. El pase observable de la Phase 33 (plan 33-05, 2026-08-27) **no pudo correr**: `main_matriz.py` aborta en el assert de hostname **D-MATZ-33** (`:2550`) porque `PRIMARY_BASE_URL` apunta a `api.demo.matrizoms.com.ar`, que no es el sandbox remarkets al que la política de seguridad de la Phase 5 restringe la verificación. Las credenciales **sí** autentican (`preflight_33.py` → `AUTH OK`); el bloqueo es de política, no de auth, y **no se debe rodear** (la superficie de matriz incluye entrada de órdenes; prohibición P-05 de 33-05). Queda sin contrastar el piso `≥24` de `29-SIZING.md` (equivalente en triples distintos: 14) y quedan **COULD-NOT-DECIDE** las tres estructurales del paquete: **S-3** (`Instrument.instrumentId` ausente en byCFICode/bySegment, con `marketId`/`symbol` llegando aplanados y descartados como `extra` — *"the highest-consequence finding in the set"* según `29-SIZING.md`), **S-4** (`InstrumentDetail` no declara 7 claves del wire) y **S-5** (`MarketDataSnapshot.LA/.SE/.OI/.CL` no-`Optional` llegando `null`). **Requisito de ventana horaria:** el pase observable tiene que correr **dentro de una sesión de trading de ARG** o S-5 sigue siendo indecidible — un `null` de mercado cerrado no se distingue de un error de modelado (P-12). Colateral: las **nueve** entradas de `_SCHEMA_FILES` declaradas y ausentes en disco (orders / positions / account-report) sólo toman su rama write-once en una corrida exitosa. Detalle completo en `33-CENSUS.md`. **Ampliación (plan 33-06, 2026-08-27):** el mismo gate bloqueó el **censo de valores de los siete campos RESPONSE con alias `Literal`** — `marketId` (`Segment`, `InstrumentId`), `cficode` (`Instrument`, `InstrumentDetail`), `currency` y `orderTypes` (`InstrumentDetail`) y `ordType` (`Order`). Los cuatro alias (`MarketId`, `CFICode`, `Currency`, `OrderType`) quedan confirmados como **decodificando sin enforcement** (`POLICY` de matriz pasa `literal_enforced=False` y `scalar_passthrough=True`, `_decode.py:136`), pero **qué valores manda el vendor sigue sin medirse**: es la mitad abierta del criterio 3. `scripts/literal_census_33.py` ya lleva el gate remarkets-only y corre el censo completo apenas haya un `PRIMARY_BASE_URL` de remarkets con credenciales emitidas para ese host. Colateral del mismo desbloqueo: corregir el párrafo `29-DLOCK-RESPONSE-LITERAL.md:140-142`, que afirma que el stream de divergencias es el mecanismo de censo — la rama `Literal` de `walk_field` (`_decode.py:521-534`) retorna temprano con `literal_enforced=False` y nunca llama al sink, así que no lo es. El lock está firmado, así que la corrección es del firmante. Detalle en `33-LITERALS.md`.

- **LIVE-HIGY-42 (ex `LIVE-HIGY-33`, renombrado el 2026-08-31 por D-06 de la Phase 42) — censo en vivo de `higyrus-client` (piso `≥22` sin contrastar)** — paquete: `higyrus-client`. El pre-flight de la Phase 33 (plan 33-05, 2026-08-27) imprimió `AUTH FAIL ConnectError`. Diagnóstico acotado: las tres variables (`HIGYRUS_BASE_URL`, `HIGYRUS_USER`, `HIGYRUS_PASSWORD`) están presentes y el esquema es `https`, pero el hostname **no resuelve por DNS** (`socket.gaierror`) desde la red de desarrollo — es alcanzabilidad de red (host plausiblemente interno/VPN), no rechazo de credenciales. Por D-13 el paquete se registró como `SKIPPED — vendor inalcanzable`, **nunca como cero**. Quedan sin contrastar los 22 triples `missing` del piso: `Movimiento` (9), `PosicionValuada` (11), `Posicion` (2). Al desbloquearlo, el camino es el de operador-corre-y-pega de la Phase 23. Detalle completo en `33-CENSUS.md`. **Sigue abierto tras v1.7 Phase 39** — el driver reportó `SKIPPED` con la misma causa medida (DNS aún sin resolver). **→ v1.8 Phase 42 (LIVE-01).**
  **→ Estado medido en v1.8 Phase 42 (2026-08-31): SIGUE ABIERTO, con causa re-medida esta sesión.** No es un re-estampado de la Phase 39: se midió hoy y se contrastó por **clase de excepción**. Resolución DNS → `socket.gaierror`; `login()` vía httpx → `httpx.ConnectError`; ambos con el errno `[Errno 8] nodename nor servname provided, or not known` citado verbatim tras pasar un guard de contención (cero hostname, cero base URL en cualquier artefacto de la sesión). La clase medida hoy es **igual** a la heredada de la Phase 39. El driver completo corrió **dos veces** (planes 42-03 y 42-05), exit `0` las dos, emitiendo una única línea clasificable `SKIPPED higyrus-client: …` y regenerando el sobre `.planning/verification/run-evidence/higyrus-client.json` por corrida real (nunca por edición manual); `captured_at` autoritativo: `2026-08-31T21:38:57.229188+00:00`, `probes_executed: 0` acompañado de `skipped` no nulo — jamás un cero silencioso (D-13). El ledger `higyrus-client-findings.md` quedó byte-idéntico: el corte temprano de `main()` sale antes de todo `append_finding`. **Destino renombrado** de `LIVE-HIGY-33` a `LIVE-HIGY-42` en los 14 sitios vivos (11 de código + 3 de prosa, 7 archivos, commit `f75145c`); las 2 ocurrencias del identificador viejo en `verification/test_cycle_closure_phase33.py:250-252` **se conservan a propósito** porque aseveran contra `33-CENSUS.md`, congelado. **Esto es una re-confirmación medida, NO el cierre del ítem:** los **22 triples sin contrastar** del piso ratificado de `29-SIZING.md` (`Movimiento` 9, `PosicionValuada` 11, `Posicion` 2) siguen exactamente igual de sin contrastar, porque el veredicto volvió a ser `SKIPPED`. Renombrar cambió el identificador, no el estado. Evidencia: `42-03-SUMMARY.md`, `42-05-SUMMARY.md`, `42-CLOSURE.md`.

- **TYP-MD-EXTRA-33 — tipar las 8 claves `extra` en vivo de `market-data-client`** — paquete: `market-data-client`. Ocho triples de especie `extra` medidos en vivo contra `develop` el 2026-08-27 (plan 33-05) que el plan 33-07 **no** corrige: `HealthFeed.symbols_never_delivered` (`int`), `FeedIngestor.ingestor.last_error_age_seconds` (`int`), `.ingestor.last_error_at` (`str`), `.ingestor.subscription` (`dict`), `Symbol.note` (`str`), y las tres del sobre de preview `CalendarConfig.market_after` / `.requires_confirmation` / `.valid`. **Actualización (plan 33-07, 2026-08-27): esas tres YA NO están abiertas** — S-2 se cerró in-cycle dándole al preview su propio modelo (`CalendarConfigPreview` + `PreviewMarket`), que declara las tres, así que este ítem baja de 8 triples a **5**: los cuatro `extra` de `HealthFeed`/`FeedIngestor` más `Symbol.note`. `extra` es **informativo por política** (locks 3 y 4 de la Phase 29: se emite a `INFO` y nunca levanta), así que esto es trabajo de cobertura de superficie, no reparación de defecto. Cuatro de los ocho son **TYP-02**: son visibles porque `Health`/`HealthFeed` se tiparon recién en la Phase 31. **→ v1.8 Phase 43 (HARN-02), en el mismo cambio de `models.py` que SHAPE-01.**
  **→ CERRADA por la Phase 43 (2026-09-01), plan 43-02 (`1bc82b1` RED / `327b3ce` GREEN / `8b4de5e` REFACTOR). Texto de arriba conservado verbatim.** Las **cinco** claves quedaron declaradas con el tipo que su evidencia medida respalda: `FeedIngestor.subscription` como `FeedSubscription`, un **modelo anidado tipado de 15 campos** y no un `dict[str, Any]` (un mapping es un punto ciego permanente del censo: `walk_field` no tiene rama para mappings); `last_error_age_seconds` (`int | None`) y `last_error_at` (`str | None`), condicionales a que exista un error; `HealthFeed.symbols_never_delivered` **plano** (`int`, D-11, deliberadamente no-`Optional`); y `Symbol.note` (`str | None`). **Ninguna `extra` se convirtió en `missing`** sobre un payload sano — probado, no afirmado, por `test_measured_health_feed_payload_produces_zero_divergence_records`, que decodifica el blob medido con **cero** records de cualquier especie. La observación de esta entrada de que `extra` es informativo por política sigue en pie y no se relajó ningún lock para cerrarla. Detalle en `43-DISPOSITION.md` §§ 1 y 3.

- **SHAPE-MD-REF-33 — corregir la forma declarada de `Instrument` y `Segment` (`market-data-client`)** — paquete: `market-data-client`. Es la **mitad de S-1 que el plan 33-07 deliberadamente NO cerró**, y la razón está registrada: 33-07 arregló el desenvolvimiento del sobre (los parsers iteraban las CLAVES del envelope y devolvían un modelo all-default por clave; findings `F-82`/`F-83`/`F-102`/`F-103`, ya `FIXED`), pero corregir los CAMPOS declarados es un cambio de forma de un modelo **publicado** desde v0.2.0, y el checkpoint bloqueante 33-07 Task 1 existe exactamente para esa clase de cambio. El operator autorizó **tres** cambios de forma (SC-1 preview, SC-2 `MarketDataSnapshot`, SC-3 `Symbol`) y éste **no estaba entre ellos**; aplicarlo igual habría sido el cambio de contrato sin decisión que T-33-44 prohíbe. Lo que queda por corregir, contra los baselines committeados `get-instruments.json` y `get-segments.json`: **`Instrument`** declara `marketId` e `instrumentType`, que el wire no manda, y no declara `market_id`, `currency`, `days_to_maturity`, `maturity`, `outright`, `subscribed` ni `active`, que sí manda (3 de 5 campos declarados —`symbol`, `segment`, `expired`— sí coinciden); **`Segment`** declara `marketSegmentId`, `marketId` y `description`, y el wire manda `segment` y `live_instruments` — **conjuntos disjuntos**, así que hoy toda fila de `get_segments()` sale con sus tres campos vacíos. **Estado post-33-07: la divergencia es VISIBLE, no silenciosa** — antes se escondía detrás de un único `non_dict` terminal por modelo y ahora el walker la reporta campo por campo y levanta bajo `strict_decode`, que es estrictamente mejor pero no es el fix. Requiere disposición de semver: es source-breaking y se suma al bump de la Phase 34 si se hace antes del release, o abre su propio ciclo si se hace después. **→ v1.8 Phases 43 (fix) + 44 (release 0.7.0) — "abre su propio ciclo", que es exactamente lo que pasó.**
  **→ CERRADA por la Phase 43 (2026-09-01). El texto de arriba se conserva verbatim y sin editar** — es la evidencia de procedencia con la que se planificó la fase, y esta nota es su resultado medido (mismo precedente que la nota de Q5 del plan 42-06). El fix aterrizó en el plan 43-01 (`52fe007` RED / `2a3de99` GREEN / `1caee63` re-derivación de tests) contra la lectura FRESCA del wire del 2026-08-31, no contra los baselines committeados que esta entrada cita: `42-WIRE-READ.md` § 2 los marca **NO-AUTORITATIVOS** para forma. **Disposición campo por campo, cero filas sin disponer:** `Instrument` pasó de 5 campos declarados a 11 — `symbol`/`segment`/`expired` **mantenidos**, los 6 wire-only **agregados** (`market_id`, `currency`, `days_to_maturity`, `maturity`, `outright`, `subscribed`), `active` **agregado nullable** (`bool | None`, medido `null` en 50/50 filas), `instrumentType` **removido** (el wire nunca mandó la clave) y `marketId` conservado como **alias aditivo deprecado** con espejo en `from_api` — NO renombrado, porque es superficie publicada (D-04, precedente D-22 de `Symbol`; el rename directo está prohibido en `REQUIREMENTS.md` § Out of Scope). `Segment` **reemplazado por completo**: los 3 declarados **removidos**, `segment` (str) y `live_instruments` (int) **agregados**. La afirmación de esta entrada de que "hoy toda fila de `get_segments()` sale con sus tres campos vacíos" quedó **verificada verdadera y luego corregida**: los key-sets eran disjuntos (findings `F-214`…`F-218` sync / `F-238`…`F-242` async), y la decodificación post-fix devuelve las dos claves **pobladas**. La segunda mitad del ítem, `TYP-MD-EXTRA-33`, cerró en el mismo `models.py` (plan 43-02). **Publicación pendiente:** la corrección está en `main`, **no** en un release — el bump a 0.7.0 es la Phase 44 (PUB-01) y la Phase 43 no tocó ninguno de los tres sitios de versión ni `uv.lock`. Evidencia completa en `43-DISPOSITION.md`.

- **HARN-DRIFT-33 — deduplicar los findings de `schema drift` por título** — paquete: harness (`main_market_data.py` y los otros cuatro drivers). `_write_or_check_schema` llama a `append_finding` **sin** `idempotent_by_title=True`, así que un mismo drift escribe un bloque `### F-` nuevo por superficie y por pase, con títulos byte-idénticos: la corrida de dos pases del plan 33-05 produjo **22 bloques** de drift para **8 snapshots distintos** (`get_health_feed` ×4, `get_calendar` ×4, `get_calendar_config` ×4, y ×2 los otros cinco). No hay pérdida de censo —nada se descarta— pero infla el archivo de findings y hace que el triage vea duplicados. La rama comparte además el allocator de fids, así que está cubierta por la aserción de consistencia de `verification/test_finding_count_consistency.py`. **→ v1.8 Phase 45 (HARN-01) — con la advertencia de que `idempotent_by_title=True` a secas es la implementación INCORRECTA: el título es endpoint-scoped y libre de contenido, así que tragaría toda divergencia posterior y distinta sobre el mismo endpoint.**

### Deferred to v1.6+ (from v1.5)

- **D-16 — enrolar `market-data-client` en el typecheck global** — el paquete sigue ausente de tres listas: el `files` de mypy del root (`pyproject.toml:97`, hoy 5 paquetes), el `root_packages` de import-linter (`pyproject.toml:141-146`, hoy 4) y el loop mypy-tests per-package de `ci.yml:85` (hoy 5). Enrolarlo requiere además **escribir un contrato de import-linter** para `market_data_client._core` (los otros 4 paquetes ya tienen el suyo). Es un gap de **COBERTURA de typecheck, no un CI failure**: todos los checks package-scoped están verdes hoy, y la cobertura real de mypy sobre este paquete la da el hook de pre-commit scoped `files: ^packages/.*/src/` (`.pre-commit-config.yaml:32`). Diferido desde Phase 24 y re-confirmado en Phase 28 (**rechazado** enrolarlo en el PR de release: expandiría el diff). Se archiva acá explícitamente para que deje de rodar en silencio release tras release. **RESUELTO por v1.6 Phase 32 — entrada conservada como registro histórico (ver `REQUIREMENTS.md § Out of Scope`).**

### Deferred to v1.5+ (from v1.4 — market-data-client v2 requirements)

- **MUT-MD-01 / MUT-MD-02** — market-data-client mutations: symbols (`POST /symbols`, `POST /symbols/batch`, `PATCH /symbols/{id}`) + calendar (`PUT/DELETE /calendar/config`, `POST /calendar/config/preview`, `POST /calendar/holidays`, `DELETE /calendar/holidays/{day}`) — require the security mutating-gate. **SHIPPED en v1.5 — entrada conservada como registro histórico.**
- **STREAM-MD-01** — market-data-client SSE streaming (`GET /marketdata/stream`, `interval` param) via a dedicated transport (matriz `ws_client` pattern)
- **SEC-MD-01** — market-data-client Auth0 token disk cache (`_token_cache.py` + platformdirs, atomic + flock + 0600)
- **SEC-MD-02** — market-data-client JWT signature validation (RS256 against Auth0 JWKS)
- **LIVE-MD-01 real credentialed sweep** — the apparatus is verified; the actual live run against `market-data-develop.bbsa.com.ar` still awaits Auth0 creds + VPN/allowlist. **RESUELTO post-cierre de v1.4 (2026-07-31).**

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
