# Phase 27: Verificación en vivo segura + fixes - Context

**Gathered:** 2026-08-01 (assumptions mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

Ejercitar **en vivo contra develop** toda la superficie de mutación de `market-data-client`
construida en Phases 25 y 26 (symbols write + calendar write, sync **y** async), de forma
**destructiva pero segura**, y corregir in-cycle toda divergencia entre el cliente y el
servidor real. Un requisito:

- **LIVE-MUT-01** — la superficie de mutación completa se ejercita vía `main_market_data.py`
  detrás del mutating-gate, con **identificadores de prueba dedicados + cleanup**
  (create→verify→revert), **nunca** tocando config real de mercado sin `confirm`; se
  **revalida la idempotencia por-endpoint (DM-03)** contra el comportamiento en vivo antes
  de confiar el retry-behavior; toda divergencia se documenta en findings y se corrige en
  el mismo ciclo, espejada sync/async, con un test de regresión mockeado por fix; cycle
  closure PASS.

Las superficies de mutación en sí están DONE (Phases 25 + 26) — esta fase las **ejercita**
y las **corrige**. El release v0.3.0 es **Phase 28**, OUT of scope.

**IN scope:** extender `main_market_data.py` con probes de mutación sync+async detrás de un
gate develop-específico; la disciplina de identificadores de prueba y cleanup; el
experimento de revalidación de idempotencia; los fixes in-cycle de las divergencias
encontradas (incluidos los dos bugs de parser ya probados y el tipo de `symbol_id`); la
adaptación del plumbing de findings/snapshots/cycle-closure que hoy impide registrar nada;
un test de regresión mockeado por cada fix; 4 gates verdes.

**OUT of scope:** cambios al mutating-gate en sí (Phase 25, consumido sin tocar); version
bump / README changelog / PR / tag (Phase 28); nuevos endpoints o superficies; SSE
streaming, disk token cache, JWT signature validation (backlog v1.6+); enrolar
`market-data-client` en el loop de mypy cross-package y en `importlinter.root_packages`
(follow-up documentado desde Phase 24 — sigue diferido, no es un CI failure).
</domain>

<decisions>
## Implementation Decisions

### A. Gate de mutación a nivel driver

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

### B. Identificadores de prueba y cleanup

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

### C. Fixes in-cycle

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

### D. Plumbing de findings, snapshots y cycle closure

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

### E. Revalidación de idempotencia (DM-03)

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
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope locked
- `.planning/ROADMAP.md` — Phase 27 goal + los 5 success criteria.
- `.planning/REQUIREMENTS.md` — texto de aceptación de LIVE-MUT-01; `:28` (bump no-breaking
  de Phase 28, restringe D-13); `:52` (Out of Scope: mutar config real sin `confirm`).
- `.planning/future-plans/market_data_mutations.md` — plan fuente; **DM-03** (idempotencia
  por-endpoint), **DM-06** (`:60` + `:92` — el ciclo create→verify→revert y la autorización
  operator sobre develop), `:103`.
- `.planning/phases/25-mutating-gate-symbols-write/25-CONTEXT.md` — gate + request models +
  paridad; D-08 (percent-encoding, **disuelto por D-09 de esta fase**).
- `.planning/phases/26-calendar-write/26-CONTEXT.md` — D-04 (idempotencia calendar), D-06
  (holidays → `dict`), D-15 (primer test no-idempotente a nivel dispatch), **D-16** (el bug
  de `parse_calendar_response`, asignado a esta fase), D-18 (guarda de charset de `day`).

### Contrato live (re-fetcheado 2026-08-01, alcanzable desde esta máquina)
- `https://market-data-develop.bbsa.com.ar/api/openapi.json` — **NO vendorizado en el repo**;
  re-fetchear si hace falta. Confirmado en esta fase:
  - `PATCH /symbols/{symbol_id}` declara el path param como **`{"type": "integer"}`** (D-09).
  - **Las 8 respuestas de mutación** son `object` bare con `additionalProperties: true`,
    ninguna con schema declarado — ni array (D-11), ni forma conocida.
  - `GET /symbols` → **array** de objetos untyped; `GET /calendar` → **object** (D-12).
  - No existe ningún método `DELETE` bajo `/symbols` (D-05).
  - `NewSymbol.market_id` default `"ROFX"`; `SymbolPatch.active` requerido;
    `HolidaysIn.days` / `NewSymbols.symbols` ambos `minItems:1, maxItems:500`;
    `MarketHoursIn.confirm` descrito como *"Required when the change produces warnings.
    See POST /calendar/config/preview"*.
- `.planning/verification/schemas/market-data-client/get-calendar.json` — el envelope real
  capturado que respalda D-12.
- `.planning/verification/schemas/market-data-client/get-symbols.json` — baseline
  `schema: []` que hace inevitable el drift de D-17.
- `.planning/verification/market-data-client-findings.md` — `F-01`…`F-36`, ninguno `OPEN`
  (D-16).

### Driver + harness a extender
- `main_market_data.py` — el archivo que esta fase extiende: `_fid_counter` (`:99-107`,
  D-16), `_write_schema_snapshot` (`:201-206`) + emisión SHAPE (`:227-241`, D-17), probes
  con aislamiento D-09 (`:328`, `:394`, `:567`), `get_symbols(active=False)` (`:484`),
  teardowns con `contextlib.suppress` (`:940-942`, `:995-997`, D-08), gate `require_env`
  (`:954-963`, D-03), `driver_guard` (`:987-994`), imports (`:48-56` — falta
  `verify_cycle_closure`, D-18).
- `main_verify.py:42` + `:75` — la regla de clasificación SKIPPED que fija D-03.
- `main_matriz.py` — **el único precedente de verificación live destructiva del repo**;
  `:76` importa `verify_cycle_closure`. Estudiar cómo hace selección de identificadores,
  cleanup y confirmación de operator.
- `verification/mutation_gate.py` — `:39` `_SANDBOX_HOST` remarkets, `:45` la línea SKIPPED
  colon-less, `:53-59` el hard-import de matriz que hace vacua su segunda pata (D-01).
- `verification/findings.py` — contrato append-only BEGIN/END, `:531`
  (`idempotent_by_title` default `False`), `:610` (short-circuit de fid no-OPEN +
  preservación de campos humanos) — D-16 y D-18.
- `verification/cycle_report.py:123-176` — el formato exacto del bullet `Regression:` que
  resuelve el closure (D-18).
- `verification/schema.py`, `verification/safemodel_diff.py` — snapshot + SHAPE-diff.
- `verification/test_main_market_data_uses_single_client_instance.py:53` — el guard
  `1 <= ctor_sites <= 2` que fija D-02.
- `verification/test_main_market_data_postprocess_guarded.py` — el guard AST de D-09/D-04.

### Paquete a corregir (market-data-client v0.2.0)
- `packages/market-data-client/src/market_data_client/_core.py` — builders de symbols
  (`:401`/`:419`/`:436`), `build_update_symbol_request` firma `symbol_id: str` (`:437`,
  D-09), interpolación de path (`:449`), `parse_latest_response` (`:796-830`, **ya
  corregido**, D-14), `parse_market_data_response` (`:785-792`, el patrón de unwrap),
  `parse_symbols_response` (`:877-890`, D-11), `parse_calendar_response` (`:893-907`,
  D-12), `parse_calendar_write_response` (`:926`, precedente passthrough), guarda de
  charset de `day` (`:700-703`).
- `packages/market-data-client/src/market_data_client/client.py` — `_ensure_mutation_allowed`
  + gate exacto de hostname (`:259-285`), `__init__` (`:126-157`, D-02), mutaciones de
  symbols (`:541`/`:556`/`:567` + parseo en `:554`/`:565`/`:576`),
  `delete_calendar_config` (`:620`, **resetea a defaults**, D-06), `delete_holiday`
  (`:677`), `configure()` module-level (`:716`, D-02), shims (`:885`).
- `packages/market-data-client/src/market_data_client/aio.py` — el espejo async
  (`update_symbol` en `:578`/`:585`/`:895`).
- `packages/market-data-client/src/market_data_client/models.py` — `Symbol` PROVISIONAL sin
  campo `id` (`:436-448`, D-10), `CalendarDay` con campos inexistentes (D-12), request
  models de Phases 25/26.
- `packages/market-data-client/src/market_data_client/_state.py` — `mutating_allowed=False`
  + `expected_host` default (`:49-55`, `:104-105`).
- `packages/market-data-client/src/market_data_client/_transport.py` / `_atransport.py` —
  el short-circuit de `idempotent` falsy antes del loop de tenacity (D-20).

### Templates de test
- `packages/market-data-client/tests/test_symbols_write.py` / `_async.py`,
  `test_calendar_write.py` / `_async.py` — forma de los tests de mutación.
- `packages/market-data-client/tests/test_mutation_gate.py` — tests adversariales del gate.
- `packages/market-data-client/tests/test_public_surface_market_data.py` — red de
  export/paridad in-package.
- `packages/market-data-client/tests/test_transport.py` — patrón `monkeypatch` de `sleep`
  (D-20).

### Conventions
- `.planning/codebase/CONVENTIONS.md`, `.planning/codebase/STRUCTURE.md`,
  `.planning/codebase/TESTING.md`
- `./CLAUDE.md` — regla de espejado dual sync/async, mypy-strict, redacción de credenciales.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **El gate in-package está completo y AST-verificado** (Phase 25): `_ensure_mutation_allowed`,
  `mutating_allowed` + `expected_host` en `_ClientState`, `MarketDataMutationNotAllowedError`,
  herencia gratis a las vistas `with_options`. Phase 27 lo consume sin tocarlo — el trabajo
  nuevo es el gate **del lado del driver** (D-01).
- **Las 8 mutaciones ya existen** en ambos shells con sus request models tipados, sus tests
  mockeados y su cobertura de paridad. Phase 27 no construye superficie, la ejercita.
- **La infra `verification/`** ya provee todo lo necesario: `safe_print` con redacción,
  snapshots write-once, `diff_safemodel_bidirectional`, ciclo de vida de findings
  append-only, `verify_cycle_closure`. El trabajo es **cablearla** (D-16/D-17/D-18), no
  escribirla.
- **`main_matriz.py` es el único precedente destructivo** del repo — la referencia viva de
  cómo se gatea, se identifica y se limpia una mutación en vivo.
- `parse_market_data_response` (`_core.py:785-792`) y `parse_latest_response`
  (`:796-830`) son los dos parsers ya endurecidos: el patrón de unwrap a copiar en D-11.

### Established Patterns
- `_core.py` es PURO / IO-free; los builders hacen `del state`. Gate y política viven solo
  en el shell stateful.
- Forma uniforme del método mutante: `_ensure_mutation_allowed()` → `spec = _core.build_x(...)`
  → `resp = self._request(spec)` → `parse`.
- Un solo `Client()` + un solo `AsyncClient()` por corrida del driver, threadeados a cada
  probe (invariante REFAC-05, con guard AST por driver).
- Todo cambio de lógica espejado sync + async; paridad enforced por el test in-package.
- Body-consume-then-raise en todos los parsers (`resp.read()` → `raise_for_response` →
  decode).

### Integration Points
- `main_market_data.py` gana probes de mutación sync+async + el gate de D-01 + la llamada a
  `verify_cycle_closure`; sigue registrado en `main_verify.py._DRIVERS`.
- Los fixes tocan `_core.py` (parsers + firma de `build_update_symbol_request`),
  `models.py` (`Symbol`, `CalendarDay`) y ambos shells — con sus tests de regresión en
  `packages/market-data-client/tests/`.
- Cero cambios al gate, a `_state.py`, al transport, o a la superficie pública de lectura
  fuera de lo que exijan D-10/D-11/D-12.
</code_context>

<specifics>
## Specific Ideas

- **La segunda pata del gate de matriz es vacua para market-data.** No es un detalle de
  estilo: reutilizar `mutating_allowed()` tal cual produce un gate que *parece* de dos patas
  y en la práctica valida el `base_url` de otro paquete. Es exactamente la clase de falso
  sentido de seguridad que el mutating-gate existe para prevenir.
- **`DELETE /calendar/config` no es cleanup, es un segundo clobber.** Resetea a los defaults
  del servidor; no recuerda el valor previo. Por eso preview-only (D-06) no es timidez sino
  la única opción con cleanup real.
- **Los símbolos de prueba son irreversibles por diseño de la API.** Sin `DELETE /symbols`,
  `active=false` es lo más cerca de un revert que existe. El prefijo reconocible es lo que
  convierte un residuo permanente en un residuo auditable.
- **Un finding que se escribe a un no-op es peor que un finding que no se emite** — el
  resumen dice `FINDING=N` y el archivo no registra nada, así que el cycle closure pasa
  vacuamente y la fase reporta éxito habiendo perdido su deliverable. D-16 se resuelve
  **antes** de correr nada en vivo.
- **La idempotencia demasiado permisiva es un bug de datos.** Si un builder marcado
  `idempotent=True` resulta duplicar estado server-side, el retry lo va a ejercitar bajo
  5xx exactamente cuando el operador menos lo observa. Se corrige el flag, no se anota.

</specifics>

<deferred>
## Deferred Ideas

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

### Reviewed Todos (not folded)
None — no pending todos matched Phase 27 scope (`todo.match-phase 27` → 0 matches).
</deferred>

---

*Phase: 27-verificaci-n-en-vivo-segura-fixes*
*Context gathered: 2026-08-01 via assumptions mode*
