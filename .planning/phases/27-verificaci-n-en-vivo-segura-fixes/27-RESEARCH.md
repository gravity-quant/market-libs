# Phase 27: Verificación en vivo segura + fixes - Research

**Researched:** 2026-08-01
**Domain:** Verificación en vivo destructiva de una superficie de mutación HTTP (Python, httpx sync+async) contra un backend real — driver-side gating, disciplina de identificadores de prueba + cleanup, experimento empírico de idempotencia, y plumbing del harness de findings/snapshots/cycle-closure
**Confidence:** HIGH para todo lo verificable offline (código shipeado, OpenAPI en vivo, ejecución real de `verify_cycle_closure` y de `append_finding`); MEDIUM/LOW marcado explícitamente para lo que sólo el servidor puede responder

## Summary

Phase 27 no construye superficie: **ejercita** las 8 mutaciones ya shipeadas y **corrige** lo que
diverja. La investigación de esta sesión confirma que las 20 decisiones de `27-CONTEXT.md` son
ejecutables, pero desentierra **tres bloqueantes de plumbing que no estaban en CONTEXT.md** y que
convierten el orden de trabajo en no-negociable: la fase debe arreglar el harness **antes** de
correr nada en vivo, o pierde su deliverable.

**Los tres bloqueantes (los tres verificados empíricamente esta sesión, no inferidos):**

1. **`verify_cycle_closure("market-data-client")` ya devuelve `(False, 34)` HOY.** Ejecutado en
   esta sesión: los findings `F-03`…`F-36` están en status `FIXED` **sin** bullet `Regression:`,
   y `cycle_report.py:148-155` los cuenta como missing. El riesgo real de D-18 es el **inverso**
   del anotado: no es un PASS vacuo, es un FAIL inmediato en cuanto se cablee la llamada. Los
   otros 4 paquetes devuelven `(True, [])`.
2. **El primer `append_finding` con un fid nuevo DESTRUYE la prosa humana de los 36 findings
   existentes.** Reproducido sobre una copia: `**Classification:**` 36→0, `**Resolution:**` 34→0,
   `**Rationale:**` 2→0, el archivo pasa de 22.201 a 11.580 bytes. Causa: `_parse_findings`
   sólo retiene `Expected`/`Actual`/`Diff`/`Regression` (`findings.py:404-410`) y
   `_serialize_findings` re-emite sólo esos cuatro (`findings.py:493-505`); la guarda CR-01 de
   `findings.py:610` protege el finding **que se está escribiendo**, no a sus vecinos.
3. **`idempotent_by_title=True` NO resuelve D-16.** El chequeo por título (`findings.py:599-603`)
   corre **antes** del short-circuit por fid (`findings.py:610`), pero sólo hace no-op cuando el
   título **ya existe**. Un finding con título **nuevo** y fid colisionado sigue cayendo en el
   short-circuit y escribiéndose a un no-op. La alternativa "o `idempotent_by_title=True` en
   todos lados" que ofrece D-16 es **insuficiente por construcción**: sólo el offset del
   allocator de fids cierra el agujero.

**Cuatro hallazgos que corrigen premisas del material upstream:**

- **`main_matriz.py` NO es un precedente destructivo.** `grep mutating_allowed` sobre todo el repo:
  ningún driver lo invoca; `main_matriz.py` no tiene un solo probe de mutación (cero
  `new_order`/`cancel_order`). Su única protección es un assert por **substring**
  (`main_matriz.py:2166`, `if "remarkets" not in base`) — exactamente el anti-patrón que
  `mutation_gate.py:56-59` documenta como inseguro. **Phase 27 es la primera verificación live
  destructiva del repo**: no hay patrón de cleanup que copiar, hay que diseñarlo.
- **`market-data-client-v0.3.0` y `v0.3.1` YA ESTÁN PUBLICADOS**, y `v0.3.0` incluye
  `create_symbol`/`create_symbols`/`update_symbol` (`git show market-data-client-v0.3.0:…/client.py`
  → 4 matches). Es decir: el `-> list[Symbol]` de D-11 y el `symbol_id: str` de D-09/D-10 son
  contrato **ya liberado**. Las realizaciones no-breaking existen (desenvolver el envelope
  manteniendo `list[Symbol]`; ensanchar a `symbol_id: int | str`) y son estrictamente mejores.
  Las calendar writes (Phase 26) **no** están en ninguna tag → ahí sí hay libertad total.
- **La OpenAPI en vivo entrega el observable de idempotencia y confirma D-05/D-09/D-10 con texto
  normativo**: *"There is no DELETE"*, *"`GET /symbols` returns the id"*, *"Idempotent by design:
  re-posting a symbol that exists reactivates it and returns 200 rather than 201"*. Pero el
  status-code **no sirve como observable estable** (en el segundo run el primer POST ya es 200):
  el observable robusto es el **conteo de filas** vía `GET /symbols?prefix=…`.
- **`POST /calendar/holidays` se autodescribe idempotente**: *"Add **or update** calendar entries.
  **Idempotent by date, so re-seeding is safe.**"* Eso apunta a que el `idempotent=False` de
  Phase 26 D-04 es **conservador de más** (dirección segura, pero probablemente incorrecta). D-19
  prohíbe inferirlo del texto: el experimento manda, pero el planner debe presupuestar el flip.

**Primary recommendation:** decomponer en **4 waves con orden forzado** — (0) plumbing de findings
+ cycle closure + baselines, (1) gate driver-side + fix offline de `parse_calendar_response`/
`CalendarDay` (prerequisito de criterio 2), (2) probes de mutación + cleanup + experimento de
idempotencia contra develop, (3) fixes in-cycle con regresión mockeada + re-run + closure PASS.
Ninguna wave posterior es significativa sin la anterior.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**A. Gate de mutación a nivel driver**

- **D-01:** `main_market_data.py` **NO** reutiliza `verification/mutation_gate.py::mutating_allowed()`
  tal cual. Ese helper hard-importa `matriz_client` y valida el `_base_url` **de matriz**
  (`verification/mutation_gate.py:53-59`, `_SANDBOX_HOST` hardcodeado a remarkets en `:39`);
  invocado desde el driver de market-data su segunda pata es **vacua** — `VERIFY_MUTATING=1`
  solo desbloquearía escrituras contra cualquier `base_url`. Phase 27 provee un gate
  market-data-específico que compone **dos** patas: una variable de entorno de opt-in **y**
  `urlsplit(base_url).hostname == "market-data-develop.bbsa.com.ar"` (comparación exacta,
  nunca substring/`endswith`, malformado→`None` falla cerrado — mismo criterio que el gate
  in-package de Phase 25).
- **D-02:** El resultado de D-01 se pasa como `Client(mutating_allowed=...)` /
  `AsyncClient(mutating_allowed=...)` en la **única** construcción existente de cada shell.
  **NO** se construye un segundo cliente mutante: `verification/test_main_market_data_uses_single_client_instance.py:53`
  asserta `1 <= ctor_sites <= 2` y un tercer sitio lo pone RED. `configure()` es
  module-level (`client.py:716`, muta solo el singleton `_get_default()`) y por lo tanto
  **no** es una vía válida para la instancia del driver — `__init__` es la única ruta.
- **D-03:** Con el gate apagado, los probes destructivos emiten un `SKIPPED` **a nivel de
  probe, sin dos puntos** (forma `SKIPPED (mutating, guard off)`), y el driver **continúa**
  con el sweep de lectura. Prohibido un early-exit a nivel driver y prohibida cualquier
  línea que matchee `^SKIPPED \S.*:` — `main_verify.py:42` clasificaría el paquete entero
  como SKIPPED aun con un sweep de lectura exitoso (la regresión que documenta
  `main_verify.py:75`). El único emisor legítimo de esa forma con dos puntos sigue siendo
  el gate de credenciales `require_env` (`main_market_data.py:954-963`).
- **D-04:** Se preserva la invariante D-09 de Phase 23: sin credenciales o fuera de develop
  el driver termina **SKIPPED, nunca FAILED**. Todo post-processing (snapshot, SHAPE-diff,
  finding) de un probe de mutación vive **dentro** del `try` de ese probe. Evaluar si
  `verification/test_main_market_data_postprocess_guarded.py` debe extenderse a los probes
  nuevos (Claude's discretion sobre la forma exacta del assert).

**B. Identificadores de prueba y cleanup**

- **D-05:** **Symbols — el revert es `PATCH active=false`, no un delete.** No existe
  `DELETE /symbols*` en ninguna parte: `_core.py` expone solo `build_create_symbol_request:401`,
  `build_create_symbols_request:419`, `build_update_symbol_request:436`, y el spec live no
  declara ningún método DELETE bajo `/symbols`. El ciclo es
  create → `GET /symbols` confirma → `PATCH active=false`, exactamente como prescribe el
  plan fuente (`.planning/future-plans/market_data_mutations.md:92`, locked DM-06 en `:60`).
  Los símbolos de prueba usan un **prefijo sintético reconocible y colisión-libre**; queda
  registrado que cada corrida deja un símbolo inactivo residual en el catálogo de develop
  (no hay forma de borrarlo) — el prefijo es lo que lo hace auditable.
- **D-06:** **Calendar config — preview-only. Decisión del operator (2026-08-01).**
  Se verifica en vivo **únicamente** `POST /calendar/config/preview` (compute-only, no
  persiste, `confirm=False`). `PUT /calendar/config` y `DELETE /calendar/config` **NO** se
  ejercitan contra develop: quedan cubiertos por sus tests mockeados, y se registra un
  finding **EXPECTED** que deja asentado que la cobertura live de `PUT` está operator-gated.
  Rationale: `delete_calendar_config` (`client.py:620`) **resetea a los defaults del
  servidor** — no restaura un valor previo — por lo que un DELETE no puede servir de cleanup
  de un PUT; cualquier PUT real dejaría la config compartida de develop pisada. Esto honra
  ROADMAP criterio 2 y `REQUIREMENTS.md:52`.
- **D-07:** **Holidays — reversibles, ciclo completo.** `POST /calendar/holidays` con una
  fecha ISO **lejana en el futuro** dedicada al test → `GET /calendar` confirma → `DELETE
  /calendar/holidays/{day}`. `delete_holiday` existe (`client.py:677`) y el day param es
  `format: date` en el spec, así que la guarda de charset de D-18 (Phase 26) no interfiere.
  Este es el único ciclo create→verify→revert **completo** de la fase.
- **D-08:** Cleanup por probe vía `try/finally`, y **el fallo de cleanup es en sí mismo un
  finding emitido**, nunca suprimido. Los dos `finally` existentes del driver
  (`main_market_data.py:940-942`, `995-997`) usan `contextlib.suppress(Exception)` — ese
  patrón aplicado a cleanup dejaría estado huérfano en develop **sin registro**, y la
  corrida siguiente malinterpretaría el `422` de día duplicado como divergencia de shape.
  La llamada de cleanup va envuelta en su propio `try/except` que emite el finding.

**C. Fixes in-cycle**

- **D-09:** **`symbol_id` es un entero, no un string.** El spec live declara el path param
  de `PATCH /symbols/{symbol_id}` como `{"type": "integer"}`, pero el cliente lo tipa
  `symbol_id: str` en los tres sitios (`_core.py:437`, `client.py:567`, `aio.py:578`).
  **Consecuencia inmediata: el ítem D-08/WR-05 de percent-encoding heredado de Phase 25
  queda DISUELTO** — un id entero nunca puede contener `/`, así que la premisa
  (`symbol_id == "DLR/DIC26"`) era falsa. **NO** aplicar `urllib.parse.quote()`.
- **D-10:** El problema real que reemplaza a WR-05: el ciclo de D-05 necesita **obtener**
  ese id entero, y el modelo `Symbol` no tiene campo `id`. **Decisión del operator
  (2026-08-01): descubrir en vivo, después corregir in-cycle.** Se prueba el body real del
  `201` de `POST /symbols` y los items de `GET /symbols` para localizar dónde vive el id;
  recién entonces se agrega el campo a `Symbol` y se retipa `symbol_id: int` en
  `_core`/`client`/`aio`, como fix in-cycle con sus tests de regresión mockeados. **No** se
  retipa por autoridad del spec antes de ver una respuesta real.
- **D-11:** **`parse_symbols_response` está mal reutilizado por las tres mutaciones.**
  `_core.py:877-890` hace `[Symbol.from_api(item) for item in raw]`, y las tres mutaciones
  (`client.py:554/565/576`) rutean sus bodies por ahí — pero el spec declara **todas** las
  respuestas de mutación como `object` bare (`additionalProperties: true`), no array.
  Iterar un objeto produce sus **claves**, así que `create_symbol` devuelve un `Symbol`
  todo-default por clave JSON. `GET /symbols` **sí** es un array (`{"type":"array"}`), o
  sea el read path está bien: el defecto es la reutilización en el write path. Fix
  in-cycle una vez confirmado el body real; la elección entre desenvolver un envelope vs.
  darle a las mutaciones su propio parser passthrough `dict[str, Any]` (precedente
  `parse_calendar_write_response`, `_core.py:926`, y la decisión D-06 de Phase 26) se
  resuelve con la evidencia live.
- **D-12:** **`parse_calendar_response` / `CalendarDay` se corrigen en esta fase** (era
  D-16 de Phase 26, explícitamente asignado acá). `_core.py:893-907` itera `GET /calendar`
  como lista, pero el spec lo declara `object` — confirmando el envelope
  `{config, coverage, days[], market}` ya capturado en
  `.planning/verification/schemas/market-data-client/get-calendar.json`. Los campos de
  `CalendarDay` (`date`/`marketId`/`isBusinessDay`) no existen en el wire; los items reales
  son `{day, closed, open_time, close_time, description}` (la forma de `HolidayIn`).
  **No es opcional:** `GET /calendar` es la única lectura que puede confirmar que un
  `add_holidays` aterrizó, así que el criterio 2 no se cumple sin este fix.
- **D-13:** Corregir los campos de `CalendarDay` se trata como **cambio minor no-breaking**,
  compatible con el bump no-breaking que exige Phase 28 (`REQUIREMENTS.md:28`). Rationale:
  `parse_calendar_response` está roto, de modo que **ningún consumidor pudo jamás haber
  leído un `CalendarDay` poblado** — no hay comportamiento real que romper. Si la evidencia
  live contradijera esto, escalar antes de Phase 28 en vez de decidirlo en el release.
- **D-14:** **WR-01 (`parse_latest_response`) ya está cerrado** por el quick task
  `260731-t9o` — `_core.py:796-830` desenvuelve `items` correctamente. Phase 27 lo
  **verifica** en el sweep, no lo re-corrige. No arrastrarlo como deuda abierta.
- **D-15:** Todo fix se espeja `client.py` **y** `aio.py` y lleva **al menos un test de
  regresión mockeado** (criterio 4). Los tests nuevos viven en el paquete
  (`packages/market-data-client/tests/`), consistente con Phase 25 D-15/D-16 — las redes
  cross-package excluyen este paquete.

**D. Plumbing de findings, snapshots y cycle closure**

- **D-16:** El allocator de fids **debe** offsetearse, o **todo** `append_finding` de
  mutación debe pasar `idempotent_by_title=True`. `main_market_data.py:99-107` resetea
  `_fid_counter = 0` en cada corrida y reparte `F-01`, `F-02`, …, pero
  `.planning/verification/market-data-client-findings.md:15-50` ya contiene `F-01`…`F-36`
  y **ninguno está `OPEN`**; `verification/findings.py:610` corta en seco cuando el fid
  existe con status ≠ `OPEN`. Sin esto, **los primeros 36 hallazgos de Phase 27 se escriben
  a un no-op** mientras el resumen igual reporta `FINDING=N`, y el cycle closure pasa
  vacuamente. Ningún call-site actual pasa `idempotent_by_title` (default `False`,
  `findings.py:531`).
- **D-17:** Los payloads de mutación **no** deben disparar drift auto-infligido en las
  baselines write-once (DRIFT-01). `main_market_data.py:201-206` escribe la baseline una
  sola vez y `:227-241` emite un finding `SHAPE` OPEN ante cualquier diferencia sin
  sobreescribir; la baseline commiteada `get-symbols.json` es `schema: []`, así que un
  símbolo de prueba creado aparece en `get_symbols(active=False)`
  (`main_market_data.py:484`) y voltea ese schema garantizadamente. Igual `get-calendar.json`
  al agregar un holiday. Excluir los payloads de mutación de `_write_schema_snapshot` o
  curar explícitamente el drift resultante — no dejar que contamine el conteo de
  divergencias del criterio 4.
- **D-18:** **Cablear `verify_cycle_closure("market-data-client")` en el driver** — hoy
  `main_market_data.py` nunca lo llama (imports en `:48-56`; contrastar `main_matriz.py:76`).
  Cada fix in-cycle debe promover su finding a `CONFIRMED`/`FIXED` **con** un bullet
  `Regression: packages/market-data-client/tests/<file>.py::<test_name>` que
  `verification/cycle_report.py:123-176` pueda resolver (el archivo debe existir y contener
  `def <test_name>(`). Ojo: el closure devuelve `(True, [])` **vacuamente** si el archivo de
  findings no existe — un PASS vacío no satisface el criterio 5. Ojo también: la
  preservación de campos humanos de `append_finding` (`findings.py:610`) vuelve inmutable a
  un finding marcado `FIXED` sin el bullet, obligando a editar el markdown a mano.

**E. Revalidación de idempotencia (DM-03)**

- **D-19:** La idempotencia asumida se revalida **empíricamente contra el servidor real**,
  no se infiere de la semántica HTTP ni del texto del spec. El experimento debe poder
  correrse **sin dejar residuo**: doble-POST del mismo identificador de prueba → leer el
  estado → limpiar, dentro de la misma disciplina de cleanup de D-08. Los flags a validar
  son los ya asignados: `idempotent=True` en los tres builders de symbols (Phase 25) y en
  `PUT`/`DELETE /calendar/config`, `POST /calendar/config/preview`, `DELETE
  /calendar/holidays/{day}`; **`idempotent=False` en `POST /calendar/holidays`** (Phase 26
  D-04).
- **D-20:** Si la realidad contradice DM-03, **gana la realidad**: se cambia el flag
  `idempotent=` del builder afectado, se espeja sync/async, y se agrega un test de
  regresión a nivel dispatch (el precedente es la primera prueba no-idempotente del
  paquete, Phase 26 D-15: 503 repetido → **exactamente una** request saliente; usar el
  patrón `monkeypatch.setattr(time, "sleep", ...)` de `tests/test_transport.py` para evitar
  jitter real). Un flag que resulte demasiado permisivo (`True` cuando el server duplica)
  es un **bug de seguridad de datos**, no una nota — se corrige, no se documenta.

### Claude's Discretion

- Dónde vive exactamente el gate de D-01 (una función parametrizada nueva en
  `verification/mutation_gate.py` con un wrapper back-compat para matriz, vs. un
  `_mutations_enabled(client)` privado en `main_market_data.py`) y el nombre de la variable
  de entorno de opt-in.
- La forma concreta del prefijo/identificador de prueba de symbols y de la fecha ISO
  futura de holidays.
- Si el cleanup es `try/finally` por probe o además un `probe_cleanup_sweep` terminal que
  barra residuos por prefijo (D-08 fija el contrato "el fallo es un finding", no la forma).
- Organización de archivos de test para las regresiones nuevas; si los probes de mutación
  van en archivos/funciones nuevas o extienden los existentes; el pairing exacto sync/async
  (siguiendo el patrón interleaved de una sola `main()` de Phase 23).
- El mecanismo exacto de D-17 (exclusión vs. curación del drift).

### Deferred Ideas (OUT OF SCOPE)

**A Phase 28 (release):**
- Bump `0.3.0` + README changelog + `uv.lock` + PR + tag. Phase 27 **para** antes del bump.
- Si D-13 resultara falso (algún consumidor sí dependía de `CalendarDay`), escalar la
  decisión major-vs-minor **antes** de Phase 28, no durante.

**Follow-up documentado desde Phase 24 (sigue diferido, no es un CI failure):**
- Enrolar `market-data-client` en el loop de mypy cross-package de CI y en
  `importlinter.root_packages`. Los gates se corren per-package explícitamente mientras
  tanto.

**Backlog v1.6+ (per DM-08):**
- SSE streaming `GET /marketdata/stream` (STREAM-MD-01), Auth0 token disk cache
  (SEC-MD-01), validación de firma JWT RS256 (SEC-MD-02).

**Carry-forwards del monorepo (siguen en ROADMAP Backlog, fuera de v1.5):**
- prod-vs-remarkets (D-MATZ-27), `ws_client` live verification, token encryption at-rest,
  CR-01 v1.2 (`configure()` no limpia el disk cache de IOL).

**Disuelto, no diferido:**
- El percent-encoding de `symbol_id` (Phase 25 D-08 / WR-05) — la premisa era falsa, el
  param es un entero (D-09). No re-abrir.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LIVE-MUT-01 | La superficie de mutación completa (sync + async) se ejercita en vivo contra develop con credenciales Auth0 a través de `main_market_data.py`, **detrás del mutating-gate** y con **identificadores de prueba dedicados + cleanup** (create→verify→revert); NUNCA toca config real de mercado sin `confirm`. Toda divergencia (shape de respuesta, idempotencia real, códigos) se documenta y se corrige en el mismo ciclo, espejada sync/async. Revalida la idempotencia asumida por-endpoint (DM-03) | § *Gate driver-side* (forma exacta + resolución del chicken-and-egg de `base_url`); § *Identificadores de prueba y residuos*; § *Lista de probes y ordenamiento*; § *Experimento de idempotencia*; § *Plumbing de findings/snapshots/closure*; § *Fixes in-cycle candidatos* |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

| Directiva | Consecuencia para esta fase |
|-----------|------------------------------|
| Python 3.12+, uv, httpx sync+async, pytest+pytest-httpx, ruff, mypy strict | Los 4 gates deben quedar verdes; todo test nuevo usa `pytest-httpx` (no red real) |
| **Dual sync/async obligatorio**: todo fix de lógica se espeja en `client.py` y `aio.py` | Cada fix de D-10/D-11/D-12 son **dos** ediciones + paridad; `_core.py` es el punto donde el espejado se colapsa a uno |
| Sin código compartido entre paquetes (por diseño) | Prohibido importar `matriz_client` desde el gate de market-data (es exactamente el defecto de `mutation_gate.py:53`) |
| Credenciales en `.env` por paquete; nunca commitear ni loggear | Todo `print` del driver va por `safe_print`; el token Auth0 no debe entrar a ningún finding ni snapshot; `schema_of` es PII-free por construcción (`verification/schema.py:27-40`) |
| Dependencias externas en vivo: resultados varían por horario/rate-limits | El driver nunca puede terminar FAILED por develop caído (invariante D-09 de Phase 23) |
| `from __future__ import annotations` obligatorio en todo módulo | Aplica a cualquier archivo nuevo |
| Ruff: line-length 100, comillas dobles, reglas E/W/F/I/B/UP/SIM/RUF/ASYNC/PIE/PT/RET/TID | Sin imports relativos; sin wildcard imports |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Decidir *si* se permite mutar en esta corrida (env + host) | Driver (`main_market_data.py` / `verification/`) | — | Es política de la **corrida de verificación**, no del cliente; el cliente ya tiene su propio gate y no debe conocer variables de entorno del harness |
| Rechazar una mutación no autorizada en el punto de despacho | Package shell (`client.py` / `aio.py` `_ensure_mutation_allowed`) | — | Gate load-bearing, refuse-by-default, cero HTTP y cero token en el rechazo (`client.py:259-285`) |
| Construir el `RequestSpec` (path, body, `idempotent`) | `_core.py` (PURO, IO-free) | — | Los builders hacen `del state`; ni gate ni política viven ahí |
| Parsear el body de una mutación | `_core.py` parsers | — | Un solo parser compartido por sync+async: el espejado se colapsa acá |
| Elegir identificadores de prueba y limpiarlos | Driver | — | Es disciplina de verificación, no superficie de librería |
| Registrar divergencias | `verification/findings.py` | Driver (call sites) | Append-only, con zona auto-generada delimitada por markers |
| Detectar drift de shape | `verification/schema.py` + baselines commiteadas | Driver | Write-once; el driver nunca sobreescribe una baseline (D-25 de Phase 23) |
| Validar el cierre del ciclo | `verification/cycle_report.py` | Driver (probe terminal) | Chequeo estructural sobre el markdown, sin importar pytest |

## Standard Stack

### Core (ya presente — reusar, no agregar)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | 0.28.1 (pineada en `uv.lock`) | transporte sync+async | ya es el único transporte del paquete |
| pytest / pytest-httpx / pytest-asyncio | 8.3+ / 0.34+ / 0.24+ | tests mockeados de regresión | `asyncio_mode = "auto"` en `pyproject.toml:113` |
| tenacity (vía `_transport.RetryTransport`) | ya presente | retry con jitter; short-circuit por `idempotent` | `_transport.py:158-160` es el punto que D-19/D-20 ejercitan |
| stdlib `urllib.parse.urlsplit` | — | comparación exacta de hostname en ambos gates | ya usado en `client.py:281` y `mutation_gate.py:59` |
| stdlib `datetime` | — | fecha ISO del holiday de prueba | — |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Gate parametrizado en `verification/mutation_gate.py` | `_mutations_enabled()` privado en `main_market_data.py` | El privado no toca módulo compartido (menor blast radius) pero queda sin tests dedicados y contradice "patrón `verification/mutation_gate.py`" del criterio 1 |
| Allocator de fids dinámico (max existente + 1) | Offset hardcodeado `_fid_counter = 36` | El hardcode vuelve a romperse en Phase 28+; el dinámico es ~8 líneas y es permanente |
| Re-baseline de `get-symbols.json` | Excluir `get_symbols` del snapshot | Excluir apaga la detección de drift real de un endpoint de lectura de primera clase; re-baselinear la restaura y además captura por primera vez la shape real de `Symbol` |

**Installation:** ninguna. Esta fase **no agrega dependencias**.

## Package Legitimacy Audit

**No aplica: la fase no instala ningún paquete externo.** Toda la superficie usada
(`httpx`, `pytest`, `pytest-httpx`, `tenacity`, stdlib) ya está en `uv.lock` y fue auditada en
fases anteriores. `uv sync --frozen` no cambia.

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Contrato de la API en vivo (re-fetcheado y verificado 2026-08-01)

`https://market-data-develop.bbsa.com.ar/api/openapi.json` — 30.218 bytes, OpenAPI 3.1.0,
`info.title = "primary-extractor"`, `servers[0].url = "/api"`. Alcanzable desde esta máquina
(`GET /api/health` → `200`). **No vendorizado** en el repo. [VERIFIED: fetch directo esta sesión]

### Inventario completo de paths (19 operaciones)

```
GET    /health                      GET    /instruments
GET    /health/feed                 GET    /instruments/segments
GET    /symbols                     GET    /marketdata
POST   /symbols                     GET    /marketdata/latest
POST   /symbols/batch               POST   /marketdata/latest
PATCH  /symbols/{symbol_id}         GET    /marketdata/stream      ← SSE, backlog v1.6
GET    /calendar                    GET    /calendar/config
POST   /calendar/holidays           PUT    /calendar/config
DELETE /calendar/holidays/{day}     DELETE /calendar/config
                                    POST   /calendar/config/preview
```

**No existe ningún método `DELETE` bajo `/symbols`** → D-05 confirmado por ausencia
**y** por texto normativo. [VERIFIED: openapi.json]

### Texto normativo de la OpenAPI que decide decisiones de esta fase

Las descripciones del spec no son prosa decorativa: son el contrato escrito del servicio. Citas
verbatim (traducción libre entre paréntesis):

| Operación | Cita verbatim | Impacto |
|-----------|---------------|---------|
| `POST /symbols` | *"Idempotent by design: re-posting a symbol that exists reactivates it and returns 200 rather than 201, instead of erroring. The row id is stable, so a symbol that was deactivated and comes back keeps its history."* | Hipótesis fuerte para D-19; da un observable secundario (200 vs 201) y confirma que el ciclo de D-05 es re-ejecutable |
| `POST /symbols` | *"The symbol is **not** validated against the exchange here; an unknown one will be rejected by the feed and surface as `last_error` in the ingestor status."* | **Efecto colateral operativo no anticipado** — ver Pitfall 3 |
| `POST /symbols/batch` | *"Subscribe to several symbols at once. **Idempotent, like the single form.**"* | Mismo experimento aplica al batch |
| `PATCH /symbols/{symbol_id}` | *"Addressed by id rather than by symbol because symbols contain `/` and spaces (\"MERV - XMEV - AL30 - 24hs\")… **`GET /symbols` returns the id.** **There is no DELETE.** `market_data` references this row, so deleting cascades…"* | Confirma D-05, D-09 y **dónde** vive el id de D-10 |
| `POST /calendar/holidays` | *"**Add or update** calendar entries. **Idempotent by date, so re-seeding is safe.**"* | Contradice la hipótesis detrás de `idempotent=False` (Phase 26 D-04) — el experimento de D-19 debe presupuestar el flip |
| `DELETE /calendar/holidays/{day}` | *"Unlike `subscribed_symbols`, deleting here is safe and necessary: nothing references these rows…"* | Confirma D-07: es el único ciclo revert-completo |
| `PUT /calendar/config` | *"**409, not 422, for the confirm gate.** 422 means 'this body is nonsense'; a 55-minute session is a valid window we merely want said twice."* | El cliente NO tiene mapeo específico para 409 → cae a `MarketDataAPIError` (`_core.py:156-157`). Cubrible con test mockeado (D-06 lo saca del live) |
| `DELETE /calendar/config` | *"Revert to the environment's window. **404 if there was nothing stored.**"* | Un retry de un DELETE ya exitoso devuelve 404 → `idempotent=True` es correcto a nivel *estado* pero no a nivel *status observable*. Registrar como nota, no ejercitar (D-06) |
| `POST /calendar/config/preview` | *"What this window would do, without saving it. **Writes nothing.**"* | Base de D-06: es el único write-path seguro de config |
| `GET /calendar` | *"`coverage.warning` is the field to watch."* | El envelope `{config, coverage, days, market}` es contrato, no accidente → refuerza D-12 |

### Shapes declaradas (verbatim del spec)

| Elemento | Declaración |
|----------|-------------|
| `PATCH /symbols/{symbol_id}` path param | `{"type": "integer"}` — **D-09 confirmado** |
| `GET /symbols` 200 | `{"type":"array","items":{"type":"object","additionalProperties":true}}` |
| `GET /calendar` 200 | `{"type":"object","additionalProperties":true}` — **D-12 confirmado** |
| Las 8 respuestas de mutación | `object` bare con `additionalProperties: true`, **ninguna** con schema — **D-11 confirmado** |
| `POST /symbols` | declara **`201`** (+ `422`); el `200` de re-post sólo vive en la descripción |
| `NewSymbol` | `symbol` (str, 1–255, **required**), `market_id` (str, 1–255, default `"ROFX"`) — **wire keys snake_case, coincide con `models.py:216-218`** → cierra la asunción A2 de Phase 25 |
| `NewSymbols` / `HolidaysIn` | `symbols` / `days`: `minItems:1, maxItems:500` — ya enforced client-side |
| `SymbolPatch` | `active` (bool, **required**) — único campo |
| `HolidayIn` | `day` (date, required), `closed` (bool, def `true`), `open_time`/`close_time` (time \| null), `description` (str ≤500, def `""`) |
| `MarketHoursIn` | `open_time`/`close_time`/`timezone` required; `pre_open_minutes` 0–120 def 10; `enabled` def true; `updated_by` ≤200; `confirm` def false |
| `GET /calendar` query `year` | integer, **min 2000, max 2100** — acota la elección de fecha futura de D-07 |
| `GET /symbols` query `prefix` | *"Symbol prefix, e.g. `DLR/`"* — **habilita el residue sweep por prefijo** |
| `422` | `HTTPValidationError` → `{detail: [{loc, msg, type, input?, ctx?}]}` |

## Architecture Patterns

### System Architecture Diagram

```text
                      ENV                                        DEVELOP
        MARKET_DATA_VERIFY_MUTATING=1                market-data-develop.bbsa.com.ar
                       │                                          ▲
                       ▼                                          │
      ┌────────────────────────────────┐                          │
      │ pata 1: opt-in explícito       │                          │
      │ pata 2: hostname EXACTO        │◄── _env_base_url()       │
      │   (urlsplit(...).hostname)     │    (_state.py:63-65,     │
      │   GATE DRIVER-SIDE (D-01)      │     sin construir Client)│
      └───────────────┬────────────────┘                          │
                      │ bool                                      │
                      ▼                                           │
   ┌──────────────────────────────────────────┐                   │
   │ main()                                   │                   │
   │  Client(mutating_allowed=<bool>,         │  UN solo ctor      │
   │         expected_host="market-data-…")   │  (AST guard ≤2)    │
   └──────────────┬───────────────────────────┘                   │
                  │ threaded a cada probe                          │
     ┌────────────┴─────────────┬──────────────────┐              │
     ▼                          ▼                  ▼              │
 READ SWEEP              MUTATION CYCLE       CLEANUP/SWEEP        │
 (ya existe)             (nuevo)              (nuevo)              │
     │                        │                    │               │
     │  probe_*_sync          │ create ──┐         │ get_symbols(  │
     │  probe_*_async         │          ▼         │   prefix=…)   │
     │                        │  GET verify        │ get_calendar( │
     │                        │          │         │   year=2099)  │
     │                        │          ▼         │      │        │
     │                        │  PATCH active=false│      ▼        │
     │                        │  DELETE holiday    │  ¿residuo? →  │
     │                        │  (en finally)      │   finding     │
     └────────────┬───────────┴────────────────────┘               │
                  ▼                                                │
   ┌───────────────────────────────────────┐                       │
   │ POST-PROCESO — dentro del try (D-04)  │                       │
   │  _emit_shape  → findings SHAPE        │                       │
   │  _write_schema_snapshot → baselines   │                       │
   │  append_finding(fid = OFFSET + n)     │                       │
   └───────────────┬───────────────────────┘                       │
                   ▼                                               │
   ┌───────────────────────────────────────┐                       │
   │ verify_cycle_closure("market-data-…") │  probe terminal       │
   │  FIXED/CONFIRMED ⇒ Regression: …::…   │                       │
   └───────────────┬───────────────────────┘                       │
                   ▼                                               │
        PROBE …  /  SUMMARY (safe_print)  ────────────────────────►┘
```

### Pattern 1 — El gate driver-side y el chicken-and-egg de `base_url` (D-01/D-02)

**El problema que hay que resolver primero.** D-02 exige que el booleano llegue como
**kwarg del constructor**, y D-01 exige que el gate valide `urlsplit(base_url).hostname`. Pero
`base_url` vive en el estado del cliente… que todavía no existe. Y no se puede construir un
`Client` "de sondeo" porque `test_main_market_data_uses_single_client_instance.py:53` cuenta
sitios de construcción de `Client`/`AsyncClient` y tope es 2. [VERIFIED: lectura del test]

**Solución sin duplicar lógica ni agregar ctor sites:** resolver el `base_url` con la **misma**
función que usa el cliente. `_state.py:63-65`:

```python
def _env_base_url() -> str:
    """Default-factory for ``base_url``; re-reads env var on each instantiation."""
    return os.getenv("MARKET_DATA_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
```

`_ClientState()` (dataclass puro, cero I/O, `_state.py:84-114`) también sirve: `_ClientState().base_url`.
Ninguna de las dos es un `Call` a `Client`/`AsyncClient`, así que el AST guard no las cuenta.
El driver ya importa símbolos privados del paquete (`_core` en `main_market_data.py:68`), así que
el precedente existe.

**Forma recomendada del gate** (nueva función pura en `verification/mutation_gate.py`, con
`mutating_allowed()` reducida a un wrapper back-compat que delega):

```python
def mutating_allowed_for(*, env_var: str, base_url: str, expected_host: str) -> bool:
    """Doble gate parametrizado: opt-in por env + hostname EXACTO.

    Sin import de ningún paquete cliente — esa es exactamente la falla que hace
    vacua la segunda pata de ``mutating_allowed()`` cuando la invoca un driver
    que no es matriz (D-01).
    """
    if os.getenv(env_var) != "1":
        print("SKIPPED (mutating, guard off)")
        return False
    if urlsplit(base_url).hostname != expected_host:   # None (malformado) falla cerrado
        print("SKIPPED (mutating, guard off)")
        return False
    return True
```

Notas load-bearing:
- La línea impresa **no lleva dos puntos**, así que `_ENV_SKIP = ^SKIPPED \S.*:`
  (`main_verify.py:42`) no la matchea → D-03 satisfecho. [VERIFIED: regex leído]
- Comparar `hostname` (no la URL, no `endswith`): `https://market-data-develop.bbsa.com.ar.attacker.example`
  y `https://x/?h=market-data-develop.bbsa.com.ar` deben fallar. Es el mismo criterio de
  `client.py:279-285`.
- **Nombre de la env var recomendado: `MARKET_DATA_VERIFY_MUTATING`.** Razón: `main_verify.py`
  corre los 6 drivers en un solo lote (`main_verify.py:28-35`); reusar `VERIFY_MUTATING` armaría
  simultáneamente el gate de matriz. Prefijo `MARKET_DATA_*` = convención del paquete
  (`MARKET_DATA_CLIENT_ID`, etc.).
- Pasar **también** `expected_host=` explícito al constructor, para que la segunda pata del gate
  in-package no dependa de su default. Las dos patas de host quedan independientes y explícitas.

**Call site (una sola construcción por shell):**

```python
_EXPECTED_HOST = "market-data-develop.bbsa.com.ar"
_MUTATION_ENV_VAR = "MARKET_DATA_VERIFY_MUTATING"

def main() -> None:
    if not require_env(_PKG, [...4 vars Auth0...]):
        sys.exit(0)
    write_findings(_PKG)
    _seed_fid_counter(_PKG)                      # ← D-16, ver Pattern 4
    resolved = _env_base_url()
    mutating = mutating_allowed_for(
        env_var=_MUTATION_ENV_VAR, base_url=resolved, expected_host=_EXPECTED_HOST
    )
    client = Client(mutating_allowed=mutating, expected_host=_EXPECTED_HOST)   # ctor #1
    ...
    async_results, seg_async = asyncio.run(_async_main(mutating))              # ctor #2 adentro
```

### Pattern 2 — Despachar una mutación capturando el body crudo SIN bypassear el gate

**Trampa concreta:** `_raw_via_request_sync` (`main_market_data.py:244-252`) llama
`client._request(spec)`, y `_request` (`client.py:339`) **no** invoca `_ensure_mutation_allowed()`.
Aplicarlo a un spec de mutación sería un **bypass del gate**, contradiciendo el criterio 1.
[VERIFIED: lectura de `client.py:339-395` — no hay llamada al gate]

**Solución de un solo request que da método público + body crudo + status:** `_request` devuelve
un `httpx.Response` ya materializado (`http.send(req)` no-streaming), así que `resp.json()` y el
parser pueden consumirlo los dos.

```python
def _mutate_raw_sync(client: Client, spec: RequestSpec) -> httpx.Response:
    """Despacha un spec de MUTACIÓN con el gate chequeado primero (no bypass)."""
    client._ensure_mutation_allowed()          # misma primera sentencia que el método público
    return client._request(spec)

# en el probe:
resp = _mutate_raw_sync(client, _core.build_create_symbol_request(client._state, ns.to_dict()))
status = resp.status_code                       # 201 (primer alta) | 200 (re-post) — evidencia D-19
raw = resp.json()                               # evidencia D-10 (¿dónde vive el id?) + snapshot
parsed = _core.parse_symbols_response(resp)     # evidencia D-11 (la lista basura), MISMO response
```

**Y además** ejercitar el método público al menos una vez por endpoint/superficie
(`client.create_symbol(ns)`), que es lo que el criterio 1 pide literalmente. Como el endpoint es
idempotente por diseño, esa segunda llamada **es** el doble-fire del experimento de D-19: una sola
secuencia sirve a los tres propósitos.

### Pattern 3 — El ciclo create→verify→revert de symbols (D-05)

```python
_PROBE_PREFIX = "GSDPROBE/"
_SYM_SYNC  = f"{_PROBE_PREFIX}P27-SYNC"
_SYM_ASYNC = f"{_PROBE_PREFIX}P27-ASYNC"
```

```
1. create_symbol(NewSymbol(symbol=_SYM_SYNC))          método público → gate ejercitado
2. _mutate_raw_sync(build_create_symbol_request(...))  2º fire: status + body crudo + doble-fire D-19
3. get_symbols(prefix=_PROBE_PREFIX)                   confirma alta + LOCALIZA EL ID (D-10)
                                                       + cuenta filas (observable D-19)
                                                       + SHAPE-diff contra Symbol
4. finally: update_symbol(<id>, SymbolPatch(active=False))   ← el revert (D-05)
5. get_symbols(prefix=_PROBE_PREFIX)                   confirma active is False
```

**Identificadores estables, no únicos por corrida.** Un `GSDPROBE/<timestamp>` deja **un residuo
permanente nuevo por cada corrida** (D-05 reconoce que el residuo es inevitable). Un identificador
**fijo** acota el residuo a exactamente una fila para siempre, y encima hace el ciclo
re-ejecutable: la API documenta el re-post como reactivación (200), no como error. El **prefijo**
compartido es lo que hace auditable y barrible el conjunto vía `GET /symbols?prefix=GSDPROBE/`.

Identificadores propuestos (todos dentro de `1..255` chars, sin restricción de charset en el spec):

| Uso | Identificador | Superficie |
|-----|---------------|------------|
| ciclo single | `GSDPROBE/P27-SYNC` | sync |
| ciclo single | `GSDPROBE/P27-ASYNC` | async |
| batch (2 items) | `GSDPROBE/P27-SYNC-B1`, `GSDPROBE/P27-SYNC-B2` | sync |
| batch (2 items) | `GSDPROBE/P27-ASYNC-B1`, `GSDPROBE/P27-ASYNC-B2` | async |
| holiday | `2099-12-29` | sync |
| holiday | `2099-12-30` | async |

Sync y async usan identificadores **disjuntos** para que un fallo de una superficie no
contamine el diagnóstico de la otra, y para que el conteo de filas del experimento de idempotencia
sea inequívoco por superficie. Residuo permanente total: **6 símbolos inactivos**, acotado, no
creciente. Los dos días de 2099 se borran en el cleanup (y el sweep terminal los persigue si no).

**Elección de la fecha:** `2099-12-29`/`2099-12-30` — dentro del rango `year ∈ [2000, 2100]` que
acepta `GET /calendar` (necesario para poder **verificar** el alta con `get_calendar(year=2099)`),
lejano a cualquier feriado real, y con `description` sintética (`"GSD phase27 probe"`, ≤500 chars).
`closed=True` + `open_time`/`close_time` en `None` → la forma del item queda **idéntica** a la del
baseline (ver Pitfall 2). Impacto operativo real de un feriado en 2099: cero.

### Pattern 4 — Allocator de fids que no escribe a un no-op (D-16)

El bug: `_fid_counter = 0` en cada corrida (`main_market_data.py:99-107`) + `F-01…F-36` ya
existentes y ninguno `OPEN` + short-circuit en `findings.py:610` ⇒ los primeros 36 findings de
Phase 27 se escriben a la nada mientras `SUMMARY: … FINDING=N` miente.

**`idempotent_by_title=True` NO lo arregla.** Traza exacta de `append_finding`:

```
findings.py:599-603   if idempotent_by_title and ∃ finding con MISMO título → no-op, return
findings.py:610-612   if fid ∈ existing and existing[fid].status != "OPEN"  → no-op, return   ← acá muere
findings.py:614-639   crear/actualizar + serializar
```

Un finding con **título nuevo** (todos los de Phase 27 lo son) salta el primer chequeo y muere en
el segundo. [VERIFIED: lectura del flujo completo]

**Fix recomendado — seed dinámico, no offset hardcodeado:**

```python
_FID_RE = re.compile(r"^### (F-(\d+))\b", re.MULTILINE)

def _seed_fid_counter(pkg: str) -> None:
    """Arranca el allocator después del fid más alto ya registrado (D-16).

    Se llama DESPUÉS de ``write_findings(pkg)`` (el archivo ya existe) y ANTES
    del primer probe. Un offset hardcodeado volvería a romperse en la próxima
    fase; el máximo dinámico es permanente.
    """
    global _fid_counter
    path = findings_path(pkg)
    if not path.exists():
        _fid_counter = 0
        return
    nums = [int(m.group(2)) for m in _FID_RE.finditer(path.read_text(encoding="utf-8"))]
    _fid_counter = max(nums, default=0)
```

Con el estado actual arranca en 36 → primer fid de Phase 27 = `F-37`. El formato `F-{n:02d}`
sigue funcionando más allá de 99 (`F-100`), y `_INDEX_ROW_RE` / `_DETAIL_HEADER_RE` de
`findings.py` no imponen ancho fijo.

`idempotent_by_title=True` sigue siendo útil, pero **para otra cosa**: los findings **terminales**
que se re-emiten en cada corrida (el `EXPECTED` de D-06, el `EXPECTED` del re-baseline de D-17).
Precedente exacto: `main_matriz.py:2280-2299`.

### Pattern 5 — Preservar la prosa humana del archivo de findings (bloqueante nuevo)

**Reproducido esta sesión** sobre una copia del archivo real, con `_FINDINGS_DIR` apuntado a un
temp dir: un único `append_finding(fid="F-37", status="OPEN", …)` produjo

```
**Classification:**  36 → 0
**Resolution:**      34 → 0
**Rationale:**        2 → 0
bytes:           22.201 → 11.580
```

Causa: `_parse_findings` guarda todos los bullets en `bullets_by_fid` pero al reconstruir sólo
lee `Expected`/`Actual`/`Diff`/`Regression` (`findings.py:404-410`), y `_serialize_findings`
re-emite exactamente esos cuatro (`findings.py:493-505`). La guarda CR-01 de `findings.py:605-612`
protege **el finding que se está escribiendo**, no a los otros 35.

**Consecuencia directa:** `- **Regression:** …` **sí** hace round-trip (es campo de primera clase),
así que las anotaciones de D-18 son estables. Los bullets `Classification`/`Resolution`/`Rationale`
**no**.

Dos caminos, con recomendación:

| Opción | Costo | Recomendación |
|--------|-------|---------------|
| **(A)** Extender `_Finding` con `extra_bullets: dict[str,str]` preservado en orden, parseado en `findings.py:389-393` y re-emitido tras los cuatro conocidos, + test en `verification/test_findings_append_only.py` | ~15 líneas en un módulo compartido por 5 drivers | **Recomendado.** Elimina un vector de pérdida silenciosa de datos que va a morder en cada ciclo futuro, y es aditivo (los archivos sin bullets extra serializan idéntico) |
| **(B)** Aceptar la pérdida y re-agregar la prosa a mano post-run | cero código, alto riesgo de olvido; el diff de git lo hace visible pero ya destruido | Fallback si se quiere blast radius cero |

Sea cual sea, el planner debe **verificar el archivo de findings en git antes y después del primer
run en vivo** (`git diff --stat .planning/verification/market-data-client-findings.md`).

### Pattern 6 — Cablear el cycle closure (D-18)

**Estado actual medido**, no inferido:

```
$ uv run python -c "from verification.cycle_report import verify_cycle_closure; ..."
market-data-client        False  34  ['F-03','F-04','F-05','F-06','F-07','F-08','F-09','F-10', …]
matriz-client             True    0
iol-client                True    0
higyrus-client            True    0
ambito-financiero-client  True    0
```

Los 34 `FIXED` de `F-03`…`F-36` no tienen bullet `Regression:`. El PASS del criterio 5 exige
repararlos. Mapeo derivado de los títulos (`.planning/verification/market-data-client-findings.md:76-450`)
y de los tests que el quick task `260731-jim` dejó (commit `8c8e494`):

| Fids | Tema | Regression sugerida (existe y contiene `def <name>(`) |
|------|------|------------------------------------------------------|
| F-03…F-07, F-19…F-25 | campos de `MarketDataSnapshot` | `packages/market-data-client/tests/test_models.py::test_from_api_marketdata_item_parses_new_fields` (para F-19 `entries` model-only: `::test_from_api_latest_nodata_item`) |
| F-08…F-18, F-26…F-36 | campos de `CalendarConfig` | `packages/market-data-client/tests/test_reference_models.py::test_calendar_config_from_api_populated` |

Formato exacto del bullet que `cycle_report.py` resuelve (`_REGRESSION_RE`, `:47`;
`_REGRESSION_BULLET_RE`, `:54-56`):

```markdown
- **Regression:** packages/market-data-client/tests/test_models.py::test_from_api_marketdata_item_parses_new_fields
```

Reglas del validador: ruta **relativa a la raíz del repo**, sin `..`, sin espacios, termina en
`.py`, nombre de test = identificador Python válido, el archivo debe existir y contener
`def <name>(` (matchea también `async def`). [VERIFIED: `cycle_report.py:90-176`]

**Cómo se escribe el bullet en un finding ya `FIXED`:** a mano. `append_finding` corta antes de
tocar un fid no-OPEN (`findings.py:610`). Editar **las dos** apariciones del status (fila del
`## Index` y la línea `**Status:**` del bloque de detalle), porque `_parse_findings` prefiere el
Index (`findings.py:392-394`) y `_serialize_findings` re-emite desde un único registro.

**Para los findings nuevos de Phase 27** el camino es: el driver los emite `OPEN` → se corrige el
bug → se edita el markdown a `FIXED` + bullet `Regression:` apuntando al test de regresión recién
escrito. La siguiente corrida los deja intactos (short-circuit no-OPEN).

**Ubicación de la llamada** (espejando `main_matriz.py:2243-2272`): probe terminal en `main()`,
después de todos los probes y antes del bucle de `safe_print`, emitiendo un finding `ERROR-MAP`
OPEN si falla:

```python
ok, missing = verify_cycle_closure(_PKG)
results.append(ProbeResult("cycle_closure", "PASS" if ok else "FAIL",
                           "" if ok else f"missing regressions: {', '.join(missing)}"))
```

**Sobre la no-vacuidad:** `verify_cycle_closure` devuelve `(True, [])` vacuamente sólo si el
archivo **no existe** (`cycle_report.py:141-143`). El archivo existe y tiene 36 findings, así que
el chequeo es no-vacuo por construcción hoy. El riesgo real es el opuesto (FAIL inmediato). Para
blindarlo, el probe puede además asertar que el archivo tiene ≥1 finding en `FIXED`/`CONFIRMED`.

### Pattern 7 — Snapshots: qué derivará y qué no (D-17)

`schema_of` (`verification/schema.py:27-40`) reduce a claves+tipos y para una lista **muestrea sólo
el primer elemento**. Eso cambia el análisis de riesgo respecto de lo que anota D-17:

| Baseline | ¿Deriva? | Por qué |
|----------|----------|---------|
| `get-symbols.json` (`schema: []`) | **SÍ, y de forma permanente** | `probe_symbols_sync` lee `active=False` (`main_market_data.py:484`); el símbolo de prueba revertido vive ahí **para siempre**. No es drift "de este run": es el estado nuevo y correcto del endpoint. Excluir no ayuda — la lectura que deriva es un probe de **lectura**, no de mutación |
| `get-calendar.json` | **NO (riesgo bajo)** | el item de prueba (`closed=True`, horas `None`, `description` str) tiene shape byte-idéntica al `days[0]` commiteado (`{close_time:NoneType, closed:bool, day:str, description:str, open_time:NoneType}`), y `schema_of` sólo mira el elemento 0. Además el holiday se borra en el cleanup. `coverage.years` sigue siendo `["int"]` |
| `get-health-feed.json` | **RIESGO REAL no anticipado** | tiene `ingestor.last_error: "NoneType"`, y el spec dice que un símbolo desconocido *"will be rejected by the feed and surface as `last_error`"*. Si el ingestor levanta nuestro símbolo de prueba, `NoneType → str` ⇒ finding SHAPE en corridas siguientes. Ver Pitfall 3 |
| Snapshots **nuevos** de las mutaciones (`create-symbol.json`, `create-symbols.json`, `update-symbol.json`, `preview-calendar-config.json`, `add-holidays.json`, `delete-holiday.json`) | **NO en el primer run** | write-once: sin baseline previa no hay comparación posible (`main_market_data.py:201-206`). Capturarlas es un **deliverable** de la fase (hoy la OpenAPI declara esos bodies como `object` sin schema) |

**Mecanismo recomendado para D-17 (curación, no exclusión):**

1. **Snapshotear** las 6 respuestas de mutación con `client_function` propios → cero drift, y por
   primera vez queda contrato escrito de un body que el spec no declara.
2. **Re-baselinear `get-symbols.json`** como tarea explícita y revisable: borrar el archivo tras el
   primer run en vivo con símbolos creados, dejar que el write-once lo re-escriba en el run
   siguiente, y commitear el diff junto con la justificación. Restaura la detección de drift real y
   captura la shape real de `Symbol` (que hoy nadie vio: la baseline `[]` nunca probó nada).
3. **Emitir un finding `EXPECTED`** con `idempotent_by_title=True` documentando el re-baseline
   deliberado, para que quede en el registro y no se confunda con drift no explicado.
4. **Las lecturas de verificación del ciclo** (`get_symbols(prefix=…)`, `get_calendar(year=2099)`)
   **NO** deben llamar `_write_schema_snapshot` con `client_function="get_symbols"`/`"get_calendar"`:
   escribirían/derivarían las baselines de los probes de lectura con un payload filtrado. O se
   omiten, o usan un `client_function` distinto (p.ej. `get_symbols_probe_prefix`).

### Pattern 8 — Lista de probes propuesta, ordenamiento y dependencias

Ordenamiento derivado de tres restricciones duras: (a) los probes de lectura y sus snapshots deben
correr **antes** de cualquier mutación (evita el efecto `last_error` del Pitfall 3); (b) el id
entero descubierto por el probe N es insumo del probe N+1; (c) sync y async viven en bloques
separados porque cada shell tiene su propio único cliente.

```
main()
 ├─ require_env → SKIPPED <pkg>: missing …   (única línea con dos puntos, D-03)
 ├─ write_findings(_PKG)  +  _seed_fid_counter(_PKG)        ← D-16
 ├─ gate = mutating_allowed_for(...)                        ← D-01
 ├─ Client(mutating_allowed=gate, expected_host=…)          ← D-02 (ctor 1/2)
 │
 ├─ [1..10]  read sweep sync            (EXISTENTE, sin cambios)
 ├─ asyncio.run(_async_main(gate)):
 │    ├─ AsyncClient(mutating_allowed=gate, expected_host=…) ← D-02 (ctor 2/2)
 │    ├─ [11..18] read sweep async      (EXISTENTE, sin cambios)
 │    ├─ [19] probe_mutation_gate_refusal_async   ← cero HTTP, corre con gate ON u OFF
 │    ├─ [20] probe_create_symbol_async           → id async
 │    ├─ [21] probe_symbols_after_create_async    → SHAPE(Symbol) + conteo de filas
 │    ├─ [22] probe_create_symbols_batch_async
 │    ├─ [23] probe_update_symbol_async  (finally: PATCH active=false)  ← revert D-05
 │    ├─ [24] probe_preview_calendar_config_async (×2: eco + ventana sospechosa)
 │    ├─ [25] probe_add_holidays_async  (2099-12-30)  ×2 fires → D-19
 │    ├─ [26] probe_calendar_after_holiday_async  (get_calendar(year=2099)) ← exige D-12 arreglado
 │    ├─ [27] probe_delete_holiday_async          (finally, con su try/except → finding D-08)
 │    └─ [28] probe_residue_sweep_async
 │
 ├─ [29] probe_mutation_gate_refusal_sync
 ├─ [30..38] espejo sync de [20..28]
 ├─ [39] probe_parity_mutations        (¿sync y async concluyeron lo mismo?)
 ├─ [40] probe_expected_put_config_operator_gated   ← finding EXPECTED de D-06, idempotent_by_title
 ├─ [41] probe_cycle_closure                        ← D-18
 └─ safe_print PROBE … / SUMMARY
```

**Probe de refusal (recomendado, discrecional):** hace no-vacua la corrida con el gate APAGADO.
Con el gate abierto, apagarlo temporalmente sobre el estado compartido y restaurarlo:

```python
def probe_mutation_gate_refusal_sync(client: Client) -> ProbeResult:
    """El gate rechaza sin emitir HTTP ni token, aun con credenciales válidas."""
    name = "mutation_gate_refusal_sync"
    base_url = client._state.base_url
    previous = client._state.mutating_allowed
    try:
        client._state.mutating_allowed = False
        try:
            client.create_symbol(NewSymbol(symbol=_SYM_SYNC))
        except md.MarketDataMutationNotAllowedError:
            return ProbeResult(name, "PASS", "refuse-by-default confirmado")
        return ProbeResult(name, "FINDING", ...)     # el gate NO rechazó → finding AUTH
    except Exception as exc:                          # D-09
        return _finding_for_exc(exc, name=name, surface="sync", base_url=base_url)
    finally:
        client._state.mutating_allowed = previous
```

(Mutar `client._state.mutating_allowed` directamente es el patrón que ya usan los tests
in-package, `tests/test_mutation_gate.py:139`. No es un ctor site ni un `configure()`.)

**Con el gate cerrado**, cada probe destructivo devuelve
`ProbeResult(name, "SKIPPED", "(mutating, guard off)")`, que se imprime como
`PROBE create_symbol_sync: SKIPPED (mutating, guard off)` — empieza con `PROBE`, así que el regex
de `main_verify.py:42` ni lo mira. D-03 satisfecho sin esfuerzo.

### Pattern 9 — El experimento de idempotencia (D-19/D-20)

**El observable robusto es el conteo de filas, no el status code.** El 201→200 sólo es observable
en la **primerísima** corrida contra un símbolo virgen; a partir de ahí ambos fires son 200. Un
experimento que dependa del status es no-reproducible.

| Endpoint | ¿Ejercitable en vivo? | Doble-fire | Observable que distingue "dedupe" de "duplicó" |
|----------|----------------------|-----------|-----------------------------------------------|
| `POST /symbols` | **SÍ** | 2× mismo `NewSymbol` | `len([r for r in get_symbols(prefix="GSDPROBE/") if r.symbol == _SYM])` ⇒ **1** = dedupe; **≥2** = duplicó ⇒ `idempotent=False` obligatorio |
| `POST /symbols/batch` | **SÍ** | 2× mismo `NewSymbols` | mismo conteo sobre los 2 símbolos del batch |
| `PATCH /symbols/{id}` | **SÍ** | 2× `SymbolPatch(active=False)` | estado final `active is False` tras ambos fires (un PATCH de bool es idempotente por definición; el riesgo real sería un 404/409 en el segundo → se registra el status) |
| `POST /calendar/config/preview` | **SÍ** | 2× mismo `MarketHoursIn` | bodies idénticos + `get_calendar_config()` **sin cambios** antes y después (prueba el *"Writes nothing"*) |
| `POST /calendar/holidays` | **SÍ** | 2× mismo `HolidayIn(day=2099-12-29)` | `len([d for d in get_calendar(year=2099)["days"] if d["day"] == "2099-12-29"])` ⇒ **1** = upsert por fecha ⇒ **el flag `idempotent=False` de Phase 26 D-04 es conservador de más**; **2** = append real ⇒ el flag está bien |
| `DELETE /calendar/holidays/{day}` | **SÍ** | 2× DELETE del mismo día | 2º status: `200` = idempotente puro; `404` = idempotente en estado pero no en status (registrar; `_core.py:156` lo convertiría en `MarketDataAPIError` en un retry) |
| `PUT /calendar/config` | **NO** (D-06) | — | cubierto por test mockeado + finding `EXPECTED` |
| `DELETE /calendar/config` | **NO** (D-06) | — | idem; el spec ya avisa *"404 if there was nothing stored"* |

**Residuo cero:** los tres símbolos de cada superficie terminan `active=false` (única reversión
posible), y los dos holidays se borran. El experimento no agrega residuo por encima del que D-05
ya acepta.

**Si el flag cambia (D-20):** el test de regresión es a nivel dispatch, no a nivel unidad. Template
literal, ya en el repo (`packages/market-data-client/tests/test_calendar_write.py:611-651`):
`@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)` + 3×503 encolados +
`monkeypatch.setattr(time, "sleep", …)` + `assert len(httpx_mock.get_requests()) == 1` y
`assert sleeps == []`; el control positivo idempotente da 3 requests / 2 sleeps.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Comparar host de forma segura | `"develop" in base_url` / `endswith` | `urlsplit(base_url).hostname != expected` | Es exactamente el defecto que `main_matriz.py:2166` tiene hoy y que `mutation_gate.py:56-59` documenta |
| Reducir un payload a su estructura | recorrer dicts a mano | `verification.schema.schema_of` | PII-free por construcción, ya es el formato de las 9 baselines |
| Diffear modelo vs wire | comparar `dataclasses.fields` a mano | `verification.safemodel_diff.diff_safemodel_bidirectional` | Maneja `Optional`, anidados y `list[SafeModel]` sin acoplar paquetes |
| Escribir/actualizar findings | escribir markdown a mano desde el driver | `verification.findings.append_finding` | Append-only, markers BEGIN/END, preservación de status humano |
| Validar el cierre del ciclo | grepear el markdown en el driver | `verification.cycle_report.verify_cycle_closure` | Ya valida path-traversal, existencia y `def <name>(` |
| Redactar secretos en stdout | `print` crudo | `verification.safe_print(..., secrets=[...])` | El driver ya lo usa (`main_market_data.py:1000`) |
| Reintentar una mutación | loop propio en el probe | `RequestSpec.idempotent` + `RetryTransport` | El corte por `idempotent` falsy está en la primera línea de `_transport.py:158-160`; un loop propio lo saltearía |
| Resolver el `base_url` efectivo | reimplementar `os.getenv(...) or DEFAULT` | `_state._env_base_url()` | Cualquier reimplementación puede divergir en el `.rstrip("/")` |

**Key insight:** toda la infraestructura ya existe y está probada; el trabajo de esta fase es
**cablearla correctamente**, y los tres bloqueantes del Summary son precisamente cableado mal hecho
(o no hecho).

## Common Pitfalls

### Pitfall 1: emitir findings a un no-op y reportar éxito

**Qué sale mal:** `SUMMARY: … FINDING=12` mientras el archivo de findings no registró ninguno, y
el cycle closure pasa sin nada que validar. **Por qué:** `_fid_counter` reinicia en 0 y
`findings.py:610` corta ante fids no-OPEN. **Cómo evitarlo:** seed dinámico (Pattern 4) **antes
del primer probe**. **Señal temprana:** `git diff --stat .planning/verification/market-data-client-findings.md`
después de un run que reportó `FINDING>0` — si el archivo sólo cambió el `Timestamp` del ART block,
todo se escribió a la nada.

### Pitfall 2: creer que el drift de calendar es el problema y el de symbols manejable

**Qué sale mal:** se invierte esfuerzo en excluir `get-calendar` del snapshot (que no va a derivar)
y se deja pasar `get-symbols` (que va a derivar **para siempre**). **Por qué:** `schema_of` muestrea
sólo `days[0]` y nuestro holiday tiene shape idéntica; en cambio el símbolo revertido queda en
`active=False` de forma permanente. **Cómo evitarlo:** re-baselinear `get-symbols.json`
deliberadamente (Pattern 7). **Señal temprana:** el finding SHAPE `schema drift en get_symbols`
aparece en **cada** corrida posterior, no sólo en la del ciclo.

### Pitfall 3: el símbolo de prueba envenena `/health/feed`

**Qué sale mal:** un finding SHAPE `NoneType → str` en `ingestor.last_error` de
`get-health-feed.json` en corridas futuras, sin relación aparente con nada. **Por qué:** el spec
dice que `POST /symbols` **no** valida contra el exchange y que un símbolo desconocido *"will be
rejected by the feed and surface as `last_error` in the ingestor status"*; el ingestor repollea
cada `SYMBOL_REFRESH_SECONDS`. **Cómo evitarlo:** (a) correr todos los probes de salud/lectura
**antes** de cualquier mutación; (b) minimizar la ventana activa (crear → verificar → `active=false`
inmediatamente); (c) agregar un probe terminal que relea `/health/feed` y clasifique un
`last_error` poblado como **EXPECTED auto-infligido**, no como drift. **Nota:**
`SYMBOL_REFRESH_SECONDS` es desconocido → **descubrimiento en tiempo de ejecución**.

### Pitfall 4: usar `_raw_via_request_sync` con un spec de mutación

**Qué sale mal:** se dispara una escritura real **sin pasar por el gate**, con el gate
posiblemente cerrado, contra el host que sea. **Por qué:** `client._request` no llama
`_ensure_mutation_allowed()` (`client.py:339-395`). **Cómo evitarlo:** helper dedicado
`_mutate_raw_sync` que chequea el gate primero (Pattern 2). **Señal temprana:** una escritura que
ocurre con `MARKET_DATA_VERIFY_MUTATING` sin setear.

### Pitfall 5: poner `_write_schema_snapshot` / `_emit_shape` dentro de un `finally`

**Qué sale mal:** el AST guard `test_main_market_data_postprocess_guarded.py` pone RED.
**Por qué:** `_protected_call_ids` (`:43-57`) sólo considera protegidas las llamadas dentro del
**`body`** de un `try`; `except`/`else`/`finally` están deliberadamente excluidos. **Cómo evitarlo:**
en el `finally` va sólo el cleanup (PATCH/DELETE) envuelto en su propio `try/except` que emite el
finding (D-08); todo post-proceso queda en el `try` principal. El guard también tiene un piso
(`_MIN_GUARDED_CALLS = 10`) que los probes nuevos sólo pueden subir.

### Pitfall 6: la línea SKIPPED con dos puntos

**Qué sale mal:** `main_verify.py` clasifica **todo** el paquete como SKIPPED aunque el sweep de
lectura haya sido exitoso. **Por qué:** `_ENV_SKIP = ^SKIPPED \S.*:` (`main_verify.py:42`).
**Cómo evitarlo:** ninguna línea nueva puede empezar con `SKIPPED ` seguida de no-espacio y algún
`:`. La forma `SKIPPED (mutating, guard off)` es segura; las líneas `PROBE x: SKIPPED …` también
(empiezan con `PROBE`). **Señal temprana:** `main_verify.py` reporta SKIPPED para market-data en un
run donde el driver imprimió `SUMMARY: PASS=20 …`.

### Pitfall 7: dar por hecho que un feriado repetido devuelve 422

**Qué sale mal:** la lógica de cleanup/re-run se diseña alrededor de un 422 que no ocurre, y el
experimento de idempotencia interpreta mal el resultado. **Por qué:** el spec dice *"Add **or
update**… Idempotent by date"* — un día repetido es un upsert (200), no un conflicto. D-08 lo
anota al revés. **Cómo evitarlo:** el probe registra el status observado y decide por **conteo de
filas**, no por el código.

### Pitfall 8: retipar `symbol_id: str → int` como si fuera libre

**Qué sale mal:** se estrecha el tipo de un método **ya publicado** en `market-data-client-v0.3.0`
y se rompe el mypy de cualquier consumidor que pase `str`. **Por qué:** las tags `v0.3.0` y
`v0.3.1` existen y `v0.3.0` ya contiene `create_symbol`/`create_symbols`/`update_symbol`.
**Cómo evitarlo:** ensanchar a `symbol_id: int | str` — satisface la intención de D-10 (el id es un
entero, el cliente debe poder pasarlo como tal) sin romper a nadie, y sigue siendo mypy-strict.
Aplicar en los tres sitios (`_core.py:437`, `client.py:567`, `aio.py:578`).

### Pitfall 9: cambiar el tipo de retorno de las mutaciones de symbols sin mirar la tag

**Qué sale mal:** `create_symbol` pasa de `list[Symbol]` a `dict[str, Any]` y Phase 28 descubre que
el bump "minor no-breaking" de `REQUIREMENTS.md:28` ya no aplica. **Por qué:** ese `list[Symbol]`
está publicado desde v0.3.0. **Cómo evitarlo:** preferir la variante **no-breaking**: desenvolver
el envelope real y seguir devolviendo `list[Symbol]` (precedente exacto: `parse_latest_response`,
`_core.py:796-830`, que desenvuelve `items` y conserva la firma). Sólo si el body real no contiene
absolutamente nada con forma de symbol se justifica el passthrough — y en ese caso hay que
**escalar la decisión de versión antes de Phase 28**, tal como D-13 prescribe para su caso análogo.
Las calendar writes de Phase 26 **no** están publicadas: ahí no hay restricción.

### Pitfall 10: `except Exception` en el driver

**No es un problema aquí.** `verification/test_main_drivers_bare_except.py:25` limita su scope a
`main_matriz.py` y `main_higyrus.py`. `main_market_data.py` usa `except Exception as exc` como
escalera D-09 deliberada (`:328`, `:394`, `:567`, …) y los probes nuevos deben seguir ese patrón.
No "arreglarlo".

## Code Examples

### Verificar el conteo de filas tras el doble-fire (observable de D-19)

```python
def probe_idempotency_symbols_sync(client: Client, symbol: str) -> ProbeResult:
    """Doble-POST del mismo símbolo → GET confirma UNA sola fila (D-19)."""
    name = "idempotency_create_symbol_sync"
    base_url = client._state.base_url
    try:
        ns = NewSymbol(symbol=symbol)
        first = _mutate_raw_sync(client, _core.build_create_symbol_request(client._state, ns.to_dict()))
        second = _mutate_raw_sync(client, _core.build_create_symbol_request(client._state, ns.to_dict()))
        rows = client.get_symbols(prefix=_PROBE_PREFIX)
        hits = [r for r in rows if r.symbol == symbol]
        if len(hits) != 1:
            fid = _next_fid()
            append_finding(
                _PKG, fid=fid, class_="ERROR-MAP", surface="sync", status="OPEN",
                title=f"POST /symbols duplicó estado con doble-fire de {symbol}",
                expected="exactamente 1 fila tras 2 POST idénticos (idempotent=True asumido, DM-03)",
                actual=f"{len(hits)} filas; statuses={first.status_code},{second.status_code}",
                diff="idempotent=True en build_create_symbol_request es DEMASIADO PERMISIVO (D-20)",
                base_url=base_url,
            )
            return ProbeResult(name, "FINDING", f"{fid} (OPEN)")
        return ProbeResult(name, "PASS",
                           f"1 fila; statuses={first.status_code},{second.status_code}")
    except Exception as exc:  # D-09
        return _finding_for_exc(exc, name=name, surface="sync", base_url=base_url)
```

### Cleanup que emite finding en vez de suprimir (D-08)

```python
    finally:
        # D-08: el fallo de cleanup es un finding, NUNCA contextlib.suppress.
        # Ojo: nada de _emit_shape / _write_schema_snapshot acá (Pitfall 5).
        try:
            client.delete_holiday(_HOLIDAY_SYNC)
        except Exception as exc:
            fid = _next_fid()
            append_finding(
                _PKG, fid=fid, class_="ERROR-MAP", surface="sync", status="OPEN",
                title=f"cleanup falló: delete_holiday({_HOLIDAY_SYNC})",
                expected="200 y el día ausente de get_calendar(year=2099)",
                actual=repr(exc),
                diff="residuo huérfano en develop; el sweep terminal debe reintentarlo",
                base_url=base_url,
            )
```

### Sweep terminal de residuos por prefijo

```python
def probe_residue_sweep_sync(client: Client) -> ProbeResult:
    """Ningún símbolo GSDPROBE/ queda activo y ningún holiday de 2099 queda vivo."""
    name = "residue_sweep_sync"
    base_url = client._state.base_url
    try:
        actives = [s.symbol for s in client.get_symbols(prefix=_PROBE_PREFIX) if s.active]
        raw_cal = _raw_via_request_sync(client, _core.build_calendar_request(client._state, year=2099))
        days = raw_cal.get("days", []) if isinstance(raw_cal, dict) else []
        leftovers = [d.get("day") for d in days if isinstance(d, dict)]
        if actives or leftovers:
            fid = _next_fid()
            append_finding(
                _PKG, fid=fid, class_="ERROR-MAP", surface="sync", status="OPEN",
                title="residuo de probes de mutación en develop",
                expected="0 símbolos GSDPROBE/ activos y 0 holidays en 2099",
                actual=f"activos={actives} holidays_2099={leftovers}",
                diff="cleanup incompleto — barrer manualmente antes del próximo run",
                base_url=base_url,
            )
            return ProbeResult(name, "FINDING", f"{fid} (OPEN)")
        return ProbeResult(name, "PASS", "sin residuo")
    except Exception as exc:  # D-09
        return _finding_for_exc(exc, name=name, surface="sync", base_url=base_url)
```

### El fix offline de `parse_calendar_response` (D-12) — desenvolver `days`

```python
def parse_calendar_response(resp: httpx.Response) -> list[CalendarDay]:
    """Pure: parse ``GET /calendar`` → ``list[CalendarDay]``.

    El wire de develop devuelve un envelope ``{config, coverage, days[], market}``
    (OpenAPI: ``object``; baseline en ``get-calendar.json``), NO un array. Se
    desenvuelve ``days`` con el mismo collection-guard que
    ``parse_market_data_response``/``parse_latest_response``; una lista bare se
    acepta por compatibilidad, y cualquier otro body colapsa a ``[]``.
    """
    resp.read()
    raise_for_response(resp)
    if not resp.content:
        return []
    raw = resp.json()
    if raw is None:
        return []
    if isinstance(raw, dict):
        rows = raw.get("days", [])
    elif isinstance(raw, list):
        rows = raw
    else:
        rows = []
    if not isinstance(rows, list):
        rows = []
    return [CalendarDay.from_api(item) for item in rows]
```

Con `CalendarDay` retipado a la forma real del wire (verbatim de
`.planning/verification/schemas/market-data-client/get-calendar.json`):

```python
@dataclass(frozen=True, slots=True)
class CalendarDay(SafeModel):
    day: str
    closed: bool
    description: str
    open_time: str | None = None
    close_time: str | None = None
```

**Este fix es 100% verificable offline** (la baseline real ya está commiteada) y es
**prerequisito del criterio 2**: sin él no hay forma de confirmar que un `add_holidays` aterrizó.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `verification/mutation_gate.py::mutating_allowed()` como gate universal | gate **parametrizado**, sin import de paquetes cliente | Phase 27 (D-01) | El original nunca fue usado por ningún driver; su segunda pata es específica de matriz |
| Safety por substring (`"remarkets" not in base`, `main_matriz.py:2166`) | hostname exacto vía `urlsplit(...).hostname` | Phase 25 (in-package) → Phase 27 (driver) | El substring es el anti-patrón que el propio `mutation_gate.py:56-59` documenta |
| Verificación live sólo de lectura (v1.0–v1.4) | verificación live **destructiva** con cleanup | Phase 27 | Primera vez en el repo; no hay patrón previo que copiar |
| `_fid_counter = 0` por corrida | allocator sembrado con el máximo existente | Phase 27 (D-16) | Sin esto los findings se pierden silenciosamente |

**Deprecado / obsoleto:**
- El ítem de percent-encoding de `symbol_id` (Phase 25 D-08 / WR-05): premisa falsa, disuelto por D-09.
- `PUB-MUT-01` "publicar v0.3.0": **ya está publicado** (tags `market-data-client-v0.3.0` y `v0.3.1`).
  Phase 28 tendrá que apuntar a otro número; no es problema de Phase 27 pero sí condiciona qué
  cambios puede hacer (Pitfalls 8 y 9).

## Discrepancias entre el material upstream y el código real

| Fuente | Afirma | Realidad verificada |
|--------|--------|---------------------|
| `27-CONTEXT.md` canonical_refs | *"`main_matriz.py` — el único precedente de verificación live destructiva del repo… Estudiar cómo hace selección de identificadores, cleanup y confirmación de operator"* | `main_matriz.py` **no tiene mutaciones** y **no llama** `mutating_allowed()`. No hay nada que estudiar: no existe precedente de cleanup en el repo |
| `27-CONTEXT.md` D-16 | ofrece `idempotent_by_title=True` en todos lados como alternativa al offset | **Insuficiente**: no cubre títulos nuevos con fid colisionado (`findings.py:599-612`) |
| `27-CONTEXT.md` D-18 | el riesgo es un PASS vacuo | El riesgo real es un **FAIL inmediato**: hoy `(False, 34)` |
| `27-CONTEXT.md` D-08 | *"la corrida siguiente malinterpretaría el `422` de día duplicado"* | El spec documenta upsert idempotente por fecha; un día repetido devuelve 200, no 422 |
| `27-CONTEXT.md` D-17 | *"Igual `get-calendar.json` al agregar un holiday"* | `get-calendar.json` **no** derivará (`schema_of` muestrea `days[0]` y la shape del item de prueba es idéntica); el riesgo no anticipado está en `get-health-feed.json` |
| `REQUIREMENTS.md:28` / `ROADMAP` Phase 28 | bump "minor no-breaking a v0.3.0" | v0.3.0 y v0.3.1 **ya están tagueadas**; el symbols-write ya es contrato público |
| `models.py:203-210` (`NewSymbol`) | *"el real key se confirma live en Phase 27"* (A2) | **Confirmado ahora** contra la OpenAPI: `symbol` + `market_id` snake_case. El cliente ya está bien |

## Runtime State Inventory

Esta fase **crea estado en un servicio de terceros**. Inventario de lo que queda vivo fuera del repo:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data (develop DB) | Hasta 6 filas en `subscribed_symbols` con prefijo `GSDPROBE/`, todas terminando en `active=false`. **Irreversibles** (no existe `DELETE /symbols`, y el spec explica por qué: `market_data` referencia la fila) | Ninguna acción posible; el prefijo las hace auditables. Documentar en el findings file |
| Stored data (develop DB) | 2 filas en `market_calendar` (`2099-12-29`, `2099-12-30`) | Borradas por el cleanup (`DELETE /calendar/holidays/{day}`) + sweep terminal como red |
| Live service config | `market_hours` config de develop: **NO se toca** (D-06, preview-only) | Ninguna. Registrar finding `EXPECTED` |
| Live service state | El ingestor de develop puede intentar suscribir el símbolo de prueba y dejar `last_error` poblado en `/health/feed` | Probe terminal de re-lectura + clasificación EXPECTED (Pitfall 3) |
| Secrets/env vars | `MARKET_DATA_*` (4 Auth0) ya en `packages/market-data-client/.env`; **nueva** `MARKET_DATA_VERIFY_MUTATING` — sólo de proceso, no va a `.env` ni a git | Documentar en `.env.example` como comentario, sin valor |
| Build artifacts | Ninguno — no hay bump de versión en esta fase (es Phase 28) | Ninguna |
| Repo artifacts | `.planning/verification/market-data-client-findings.md` (crece), `schemas/market-data-client/*.json` (6 nuevas + 1 re-baselineada) | Commit revisado; `get-symbols.json` re-baselineada con justificación |

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| uv | correr driver y gates | ✓ | 0.11.3 | — |
| Python 3.12 (venv del workspace) | todo | ✓ | CPython 3.12.11 | — |
| Red a `market-data-develop.bbsa.com.ar` | probes en vivo | ✓ | `GET /api/health` → `200` | Sin red: el driver degrada a NO-DATA/SKIPPED (D-09), nunca FAILED |
| `MARKET_DATA_CLIENT_ID` | auth | ✓ | len=32 | `require_env` → SKIPPED, exit 0 |
| `MARKET_DATA_CLIENT_SECRET` | auth | ✓ | len=64 | idem |
| `MARKET_DATA_AUDIENCE` | auth | ✓ | len=18 | idem |
| `MARKET_DATA_AUTH0_TOKEN_URL` | auth | ✓ | len=53 | idem |
| `MARKET_DATA_BASE_URL` | opcional | ✗ (no seteada) | — | default `https://market-data-develop.bbsa.com.ar/api` (`_state.py:49`) — que es justo el host que el gate exige |
| `MARKET_DATA_VERIFY_MUTATING` | armar el gate driver-side | ✗ (a definir en esta fase) | — | Sin ella: probes destructivos `SKIPPED (mutating, guard off)`, sweep de lectura sigue |
| OpenAPI en vivo | verificar el contrato | ✓ | 30.218 bytes, OpenAPI 3.1.0 | Sin ella: usar lo transcrito en este documento |

**Missing dependencies with no fallback:** ninguna.
**Missing dependencies with fallback:** `MARKET_DATA_VERIFY_MUTATING` — la define esta fase; su
ausencia es el estado seguro por defecto.

## Los 4 gates (comandos exactos, verificados en Phase 26)

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy packages/market-data-client/src      # el root mypy EXCLUYE este paquete
uv run --package market-data-client pytest packages/market-data-client/tests -q
uv run pytest packages tests verification -q     # suite completa del monorepo + harness
```

Correr el driver en vivo (no es un gate; es operator-run):

```bash
# sweep de lectura solamente (gate cerrado)
uv run --package market-data-client python main_market_data.py

# ciclo destructivo completo
MARKET_DATA_VERIFY_MUTATING=1 uv run --package market-data-client python main_market_data.py
```

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.3+ (+ pytest-httpx 0.34+, pytest-asyncio 0.24+ con `asyncio_mode = "auto"`) |
| Config file | `pyproject.toml:102-120` (`testpaths = ["packages", "tests", "verification"]`, `--import-mode=importlib`, `--strict-markers`) |
| Quick run command | `uv run --package market-data-client pytest packages/market-data-client/tests -q` |
| Full suite command | `uv run pytest packages tests verification -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LIVE-MUT-01 (gate driver, doble pata) | `mutating_allowed_for` exige env==`"1"` **y** hostname exacto; host malformado (`hostname is None`) falla cerrado; substring no alcanza | unit | `uv run pytest verification/test_mutation_gate_parametrized.py -q` | ❌ Wave 0/1 |
| LIVE-MUT-01 (gate driver, back-compat) | `mutating_allowed()` de matriz sigue con el mismo comportamiento tras delegar | unit | `uv run pytest packages/ambito-financiero-client/tests/test_harness_mutation_gate.py -q` | ✅ existe |
| LIVE-MUT-01 (un solo cliente) | ≤2 ctor sites tras agregar todos los probes de mutación | unit/AST | `uv run pytest verification/test_main_market_data_uses_single_client_instance.py -q` | ✅ existe |
| LIVE-MUT-01 (aislamiento D-09) | todo `_emit_shape`/`_write_schema_snapshot` de los probes nuevos vive dentro de un `try.body`; el piso sube | unit/AST | `uv run pytest verification/test_main_market_data_postprocess_guarded.py -q` | ✅ existe (subir `_MIN_GUARDED_CALLS`) |
| LIVE-MUT-01 (clasificación SKIPPED) | ninguna línea nueva del driver matchea `^SKIPPED \S.*:` | unit/AST o regex sobre el fuente | `uv run pytest verification/test_main_market_data_skip_line_shape.py -q` | ❌ Wave 1 |
| LIVE-MUT-01 (allocator de fids) | `_seed_fid_counter` arranca en `max(fid)` y el primer fid nuevo no colisiona | unit | `uv run pytest verification/test_findings_fid_seed.py -q` | ❌ Wave 0 |
| LIVE-MUT-01 (prosa preservada) | un `append_finding` con fid nuevo no borra bullets desconocidos de otros findings | unit | `uv run pytest verification/test_findings_append_only.py -q` | ✅ existe (extender) |
| LIVE-MUT-01 (cycle closure) | `verify_cycle_closure("market-data-client")` → `(True, [])` con ≥1 finding FIXED | unit | `uv run pytest verification/test_cycle_closure_market_data.py -q` | ❌ Wave 0 |
| LIVE-MUT-01 → D-12 fix | `parse_calendar_response` desenvuelve `days[]` del envelope real; lista bare sigue funcionando; body raro → `[]` | unit | `uv run pytest packages/market-data-client/tests/test_reference_core.py -q` | ✅ existe (extender) |
| LIVE-MUT-01 → D-12 fix | `CalendarDay.from_api` sobre un item real (`{day,closed,open_time,close_time,description}`) puebla los 5 campos | unit | `uv run pytest packages/market-data-client/tests/test_reference_models.py -q` | ✅ existe (extender) |
| LIVE-MUT-01 → D-10 fix | `Symbol` expone el campo id descubierto; `update_symbol` acepta el id entero (`int | str`) y lo interpola sin encoding | unit | `uv run pytest packages/market-data-client/tests/test_symbols_write.py packages/market-data-client/tests/test_symbols_write_async.py -q` | ✅ existe (extender) |
| LIVE-MUT-01 → D-11 fix | el body real de las 3 mutaciones de symbols se parsea a un valor correcto (no `Symbol` all-default por clave) | unit | `uv run pytest packages/market-data-client/tests/test_symbols_write.py -q` | ✅ existe (extender) |
| LIVE-MUT-01 → D-20 (si el flag cambia) | 3×503 sobre el builder que cambió → exactamente N requests y N-1 sleeps | unit/dispatch | `uv run pytest packages/market-data-client/tests/test_calendar_write.py -k retr -q` | ✅ existe (template en `:611-651`) |
| LIVE-MUT-01 (paridad) | todo símbolo público nuevo/cambiado existe en sync y async con firma equivalente | unit | `uv run pytest packages/market-data-client/tests/test_public_surface_market_data.py -q` | ✅ existe |
| LIVE-MUT-01 (ciclo real create→verify→revert) | 8 mutaciones ejercitadas contra develop, cleanup completo, residuo cero | **manual (operator-run)** | `MARKET_DATA_VERIFY_MUTATING=1 uv run --package market-data-client python main_market_data.py` | n/a — requiere red + credenciales + autorización de operator |
| LIVE-MUT-01 (idempotencia real) | doble-fire por endpoint → conteo de filas esperado | **manual (operator-run)** | idem, leer los probes `idempotency_*` del SUMMARY | n/a |

### Sampling Rate

- **Per task commit:** `uv run --package market-data-client pytest packages/market-data-client/tests -q`
- **Per wave merge:** `uv run pytest packages tests verification -q` + `uv run ruff check . && uv run ruff format --check . && uv run mypy packages/market-data-client/src`
- **Phase gate:** suite completa verde **+** una corrida en vivo con `MARKET_DATA_VERIFY_MUTATING=1`
  que termine con `cycle_closure: PASS` y `residue_sweep_*: PASS`, antes de `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `verification/test_findings_fid_seed.py` — cubre el allocator (D-16)
- [ ] extender `verification/test_findings_append_only.py` — cubre la preservación de bullets desconocidos (bloqueante 2)
- [ ] `verification/test_cycle_closure_market_data.py` — cubre D-18 (y falla RED hoy, que es lo correcto)
- [ ] `verification/test_mutation_gate_parametrized.py` — cubre las dos patas del gate nuevo (D-01)
- [ ] `verification/test_main_market_data_skip_line_shape.py` — cubre D-03
- [ ] Instalación de framework: **no hace falta**, pytest ya está configurado

### Manual-Only Verifications

| Qué | Por qué no se automatiza | Cómo se evidencia |
|-----|--------------------------|--------------------|
| El ciclo destructivo contra develop | requiere credenciales reales, red al host de la empresa y autorización de operator; el resultado depende del estado de un servicio de terceros | salida `PROBE …` / `SUMMARY` del driver + diff del findings file + diff de los snapshots, todo commiteado |
| El experimento de idempotencia | sólo el servidor real puede responder si deduplica | probes `idempotency_*` en PASS/FINDING + los conteos registrados en el finding |
| La shape real de los 6 bodies de mutación | la OpenAPI los declara `object` sin schema | los 6 snapshots nuevos bajo `.planning/verification/schemas/market-data-client/` |

## Security Domain

`security_enforcement: true`, `security_asvs_level: 1`.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | sí | Auth0 `client_credentials` ya implementado (`_core.build_token_request`); las credenciales viven en `.env` y nunca se imprimen (`safe_print` + `secrets=[]`) |
| V3 Session Management | no | no hay sesión de usuario; el token es machine-to-machine con TTL y buffer de 60 s |
| V4 Access Control | **sí — el corazón de la fase** | doble gate en dos capas independientes: driver (env + hostname exacto) y paquete (`mutating_allowed` refuse-by-default + `expected_host` exacto, `client.py:259-285`), ambos fail-closed |
| V5 Input Validation | sí | `_DAY_SEGMENT_RE` (allow-list RFC 3986 unreserved, `_core.py:700-703`) para el path param `day`; bounds 1–500 client-side en `NewSymbols`/`HolidaysIn`; el resto de los bounds los valida el servidor con 422 |
| V6 Cryptography | no | TLS lo aporta httpx; no se implementa cripto propia. La validación de firma JWT es backlog v1.6 (SEC-MD-02) |

### Known Threat Patterns for este stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Mutación disparada contra el host equivocado (prod) | Tampering | Hostname exacto en **ambas** capas; nunca substring/`endswith`; `hostname is None` (URL malformada) falla cerrado |
| Bypass del gate por una ruta secundaria (`_request` crudo) | Elevation of Privilege | Helper `_mutate_raw_*` que chequea el gate primero (Pattern 2); prohibido pasar un spec de mutación por `_raw_via_request_*` |
| Path traversal por el path param `day` | Tampering | Allow-list de charset + rechazo de segmentos todo-puntos ya shipeado (`_core.py:700-703`); un `day` hostil retargetearía la request a `DELETE /calendar/config` |
| Retry de una operación no idempotente duplicando estado | Tampering / Repudiation | Flag `idempotent` por spec con short-circuit en la primera línea del transport (`_transport.py:158-160`); **el propósito del experimento de D-19 es validarlo empíricamente** |
| Leak de credenciales por stdout / findings / snapshots | Information Disclosure | `safe_print` con lista de secretos; `schema_of` guarda tipos, nunca valores; los findings no incluyen headers |
| Contaminación permanente del catálogo de develop | Denial of Service (leve) | Prefijo dedicado + identificadores estables (residuo acotado a 6 filas, no creciente) + sweep terminal que emite finding |

**Riesgo aceptado y documentado:** el `409` del confirm-gate de `PUT /calendar/config` no tiene
excepción dedicada (cae a `MarketDataAPIError`). Como D-06 saca ese endpoint del alcance live, el
riesgo queda cubierto por test mockeado; sólo escalar si un consumidor necesita distinguirlo.

## Wave / plan decomposition hint (granularity: `coarse`)

El orden no es preferencia, es dependencia dura: **el plumbing roto invalida el run en vivo, y el
run en vivo es el único insumo de los fixes de D-10/D-11.**

| Wave | Contenido | Bloquea a | Verificable sin red |
|------|-----------|-----------|---------------------|
| **0 — Plumbing del harness** | seed dinámico de fids (D-16); preservación de bullets en `findings.py`; bullets `Regression:` para F-03…F-36; cablear `verify_cycle_closure` + su probe; tests de los tres | todo | **sí, 100%** |
| **1 — Gate driver-side + fix offline** | `mutating_allowed_for` + wrapper back-compat; resolución de `base_url` sin ctor extra; ctor kwargs; probes `SKIPPED` sin dos puntos; probe de refusal; **fix D-12 (`parse_calendar_response` + `CalendarDay`) con sus tests** | wave 2 (criterio 2 necesita D-12) | **sí, 100%** — la baseline `get-calendar.json` ya está commiteada |
| **2 — Ciclo destructivo en vivo** | probes de mutación sync+async, identificadores, cleanup en `finally`, sweep de residuos, experimento de idempotencia, 6 snapshots nuevos, re-baseline de `get-symbols.json`, findings `EXPECTED` de D-06 y del re-baseline | wave 3 | **no** — operator-run |
| **3 — Fixes in-cycle + cierre** | D-10 (`Symbol.id` + `symbol_id: int \| str`), D-11 (parser de las mutaciones), flip de `idempotent=` si aplica (D-20); espejado sync/async; ≥1 test mockeado por fix; promoción de findings a FIXED con bullet `Regression:`; **re-run en vivo**; `cycle_closure: PASS`; 4 gates | Phase 28 | parcialmente (los tests sí; el re-run no) |

Con granularidad `coarse` esto mapea naturalmente a **4 planes** (uno por wave). Waves 0 y 1 son
paralelizables entre sí salvo que ambas toquen `main_market_data.py` — si se paralelizan, wave 0
debe limitarse a `verification/` y a la edición del markdown de findings.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | El id entero de `PATCH /symbols/{symbol_id}` viene en los items de `GET /symbols` bajo una clave tipo `id` | Pattern 3, D-10 | El spec lo afirma en prosa (*"`GET /symbols` returns the id"*) pero no declara la shape del item. Si viniera sólo en el body del `POST`, el ciclo de D-05 debe guardar el id de la respuesta de creación en vez de releerlo |
| A2 | El param `prefix` de `GET /symbols` hace match de prefijo real server-side | Pattern 3, sweep | Si fuera match exacto o case-sensitive distinto, el sweep de residuos y el conteo del experimento necesitan filtrar client-side sobre `get_symbols()` completo |
| A3 | `GET /calendar?year=2099` devuelve los días de ese año en `days[]` | Pattern 8, D-07 | Si `days[]` ignorara `year`, hay que buscar el día en la lista completa. No cambia el diseño, sólo el filtro |
| A4 | `POST /symbols` con un símbolo sintético no rompe nada aguas abajo más allá de `last_error` | Pitfall 3 | Si el ingestor entrara en reconnect-loop, hay impacto operativo en develop → abortar el ciclo y avisar al operator |
| A5 | Los 34 findings `FIXED` legacy pueden apuntar a los dos tests de reconciliación identificados | Pattern 6 | Si el revisor exige un test por finding, hay que escribir 34 tests o re-clasificar; el validador sólo exige que archivo+test existan |
| A6 | El body real de las mutaciones de symbols contiene algo con forma de symbol (envelope desenvolvible) | Pitfall 9, D-11 | Si no, el fix no-breaking no existe y hay que escalar la decisión de versión antes de Phase 28 |
| A7 | `SYMBOL_REFRESH_SECONDS` del ingestor es lo bastante largo como para que la ventana activa del probe no dispare una suscripción | Pitfall 3 | Si es corto, `last_error` se puebla igual → tratarlo como EXPECTED desde el arranque |

## Open Questions

1. **¿Dónde vive el id del symbol?**
   - Sabemos: el spec afirma que `GET /symbols` lo devuelve y que *"the row id is stable"*.
   - No sabemos: el nombre de la clave (`id`? `symbol_id`?) ni si el `201` de `POST` también lo trae.
   - Recomendación: **descubrimiento en tiempo de ejecución** (D-10 lo ordena así). El probe debe
     loguear las claves del item (no los valores) y del body del POST, y recién ahí se agrega el
     campo a `Symbol`.

2. **¿`Symbol.marketId` es correcto?**
   - Sabemos: la baseline `get-symbols.json` es `[]` (nunca se vio un item real) y **todo** el resto
     de esta API usa snake_case (`market_id`, `staleness_seconds`, `open_time`, `pre_open_minutes`).
     `MarketDataSnapshot` fue reconciliado a `market_id` en el quick task `260731-jim`.
   - No sabemos: la shape del item de `/symbols`.
   - Recomendación: esperar el SHAPE-diff del primer run con símbolos; hipótesis fuerte de que
     `marketId` es model-only y `market_id` wire-only. El fix es del mismo tenor que D-10.

3. **¿`POST /calendar/holidays` es realmente idempotente por fecha?**
   - Sabemos: el spec lo afirma explícitamente.
   - No sabemos: si la implementación coincide con su documentación.
   - Recomendación: D-19 manda — medir. Si dedupe, evaluar el flip a `idempotent=True` **con** su
     test de dispatch; nótese que dejarlo en `False` es la dirección segura (a lo sumo se pierde un
     retry), mientras que un `True` erróneo duplicaría feriados bajo 5xx.

4. **¿Cómo tratar los 34 `FIXED` legacy?**
   - Sabemos: hoy hacen fallar el closure; los tests de reconciliación existen.
   - No sabemos: si el operator prefiere un bullet por finding o aceptar dos tests compartidos.
   - Recomendación: bullets compartidos por familia (`MarketDataSnapshot` / `CalendarConfig`) —
     el validador es estructural y no exige unicidad. Es una decisión de 10 minutos que conviene
     confirmar en `/gsd-discuss-phase` si el planner quiere blindarla.

5. **¿Wave 0 debería tocar `verification/findings.py`?**
   - Sabemos: sin el fix se pierde prosa de triage en cada corrida, de los 5 paquetes.
   - No sabemos: el apetito del operator por tocar un módulo compartido en una fase de verificación.
   - Recomendación: hacerlo (opción A del Pattern 5) — es aditivo, testeable y elimina un vector de
     pérdida silenciosa. Si se rechaza, dejar constancia explícita de que la prosa se re-agrega a mano.

## Sources

### Primary (HIGH confidence)
- `https://market-data-develop.bbsa.com.ar/api/openapi.json` — fetch directo 2026-08-01; 19 paths,
  descripciones normativas, componentes `NewSymbol`/`NewSymbols`/`SymbolPatch`/`MarketHoursIn`/
  `HolidayIn`/`HolidaysIn`/`HTTPValidationError`
- Código shipeado leído verbatim: `main_market_data.py` (1013 líneas), `main_matriz.py`,
  `main_verify.py`, `verification/{mutation_gate,findings,cycle_report,schema,safemodel_diff,env_gate}.py`,
  `verification/test_main_market_data_{uses_single_client_instance,postprocess_guarded}.py`,
  `verification/test_main_drivers_bare_except.py`,
  `packages/market-data-client/src/market_data_client/{_core,client,aio,models,_state,_transport}.py`,
  `packages/market-data-client/tests/test_calendar_write.py`
- Ejecuciones reales de esta sesión: `verify_cycle_closure` × 5 paquetes; `append_finding` sobre una
  copia del findings file; `curl` al `/api/health`; `git tag` / `git show` de las tags publicadas
- Baselines commiteadas: `.planning/verification/schemas/market-data-client/*.json` (9 archivos)
- `.planning/verification/market-data-client-findings.md` (F-01…F-36)

### Secondary (MEDIUM confidence)
- `.planning/future-plans/market_data_mutations.md` (DM-03, DM-06), `.planning/REQUIREMENTS.md`,
  `.planning/ROADMAP.md`, `.planning/STATE.md`
- `.planning/phases/26-calendar-write/26-{CONTEXT,RESEARCH,VERIFICATION}.md`,
  `.planning/phases/25-mutating-gate-symbols-write/25-CONTEXT.md`
- `packages/market-data-client/README.md` (changelog v0.2.0 / v0.3.0 / v0.3.1)

### Tertiary (LOW confidence)
- Ninguna. No se usó búsqueda web: todo el dominio es interno al repo o al contrato en vivo.

## Metadata

**Confidence breakdown:**
- Contrato de la API en vivo: **HIGH** — OpenAPI re-fetcheada y citada verbatim esta sesión
- Estado del plumbing (findings / closure / snapshots): **HIGH** — los tres bloqueantes se
  reprodujeron ejecutando el código, no leyéndolo
- Restricciones del harness (AST guards, regex de clasificación, gates): **HIGH** — leídos línea a línea
- Forma concreta del gate driver-side y de los probes: **HIGH** para las restricciones, **MEDIUM**
  para la forma exacta (queda en discreción del planner dentro de esas restricciones)
- Shape real de los 6 bodies de mutación y ubicación del id: **LOW** — sólo el servidor responde;
  marcado como descubrimiento en tiempo de ejecución en A1/A6 y Open Questions 1–2
- Idempotencia real por endpoint: **LOW por diseño** — D-19 prohíbe inferirla; el spec da hipótesis
  fuertes pero el experimento es la evidencia

**Research date:** 2026-08-01
**Valid until:** 2026-08-31 para el código del repo; **7 días** para el contrato en vivo de develop
(es un servicio interno en desarrollo activo — re-fetchear la OpenAPI antes del run destructivo)
