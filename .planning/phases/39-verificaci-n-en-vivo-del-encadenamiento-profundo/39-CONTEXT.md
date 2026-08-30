# Phase 39: Verificación en vivo del encadenamiento profundo - Context

**Gathered:** 2026-08-29 (assumptions mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

El encadenamiento profundo (`snapshot.market_data.last.price`, `titulo.puntas.precioCompra`,
`snapshot.last.price`, …) deja de ser una propiedad demostrada sólo contra fixtures y pasa a
demostrarse contra las APIs financieras reales, en sync **y** async, con toda divergencia
CONFIRMED corregida dentro del mismo ciclo (espejo sync/async + regresión mockeada). Requisito:
LIVE-NOBJ-01.

Alcance de milestone (`CLAUDE.md` / `PROJECT.md`): **4 de los 5 paquetes** —
`iol-client`, `higyrus-client`, `matriz-client`, `ambito-financiero-client`. `market-data-client`
queda **fuera** de esta fase — su encadenamiento profundo (`.market_data.last.price` etc.) ya se
verificó en vivo en Phase 36 (`main_market_data.py` ya lo ejercita, SC-5 de esa fase).

Depende de Phases 36, 37, 38 (las 3 ya completas — los Null Objects y alias que esta fase va a
ejercitar en vivo ya existen en código).

Fuera de alcance explícito:
- Publicación / bump de versión / changelog / tabla de migración — eso es Phase 40 (PUB-NOBJ-01).
- Reparar el harness roto `verification/` (pytest, HARN-VERIF-01) — deuda pre-existente desde
  Phase 15/32, no relacionada con los drivers `main_*.py` que esta fase sí toca.
- Auditoría de superficie más allá de las cadenas que ya se decidieron en Phases 36-38 — esta fase
  **ejercita en vivo** cadenas ya tipadas, no descubre ni tipa cadenas nuevas.
</domain>

<decisions>
## Implementation Decisions

### Clasificación PASS/SKIPPED de los dos bloqueos heredados

- **D-01:** `main_verify.py` clasifica hoy mal ambos bloqueos heredados, y esta fase debe
  corregir la clasificación como parte de cumplir SC-1 literalmente ("PASS o SKIPPED con causa
  medida y destino nombrado, nunca como cero"):
  - **matriz** hoy sale `FAILED` — el `sys.exit(1)` de D-MATZ-33 (`main_matriz.py` ~línea 2558-2566)
    no matchea el regex `_ENV_SKIP` (`^SKIPPED \S.*:`) de `main_verify.py`. Con D-02 (abajo),
    matriz debería dejar de necesitar esta rama en la práctica (corre PASS), pero la clasificación
    igual debe quedar correcta para el caso general (si el sandbox bbsa dejara de responder, por
    ejemplo).
  - **higyrus** hoy sale `RAN` (falso limpio) — el `ConnectError` de DNS es absorbido por
    `_RESIDUAL_PROBE_EXCEPTIONS` dentro de `probe_login_sync` (`main_higyrus.py:144-151`) como
    `FINDING`, no como `SKIPPED`, y el driver sigue con exit 0. Esta fase debe distinguir
    "vendor inalcanzable" (DNS) de una divergencia real y reportar `SKIPPED — LIVE-HIGY-33` si el
    DNS sigue sin resolver cuando se corra.

### D-MATZ-33 — ampliar el allowlist a bbsa.matrizoms.com.ar (decisión del operador)

- **D-02:** El assert D-MATZ-33 (`main_matriz.py`, hostname check) se **amplía** en esta fase
  para aceptar explícitamente `bbsa.matrizoms.com.ar` además de `remarkets`, vía un allowlist
  explícito de hosts conocidos-seguros — **no** un substring genérico ni un debilitamiento del
  check. Ejemplo de forma (implementación exacta es de discreción del planner/executor):
  ```python
  if not ("remarkets" in base or base == "https://api.bbsa.matrizoms.com.ar"):
      sys.exit(1)  # D-MATZ-33: allowlist explícito, no substring genérico
  ```
  **Decisión explícita del operador** (checkpoint, no auto-resuelta) — el sandbox bbsa fue
  confirmado por el operador el 2026-08-29 como real, seguro, no-remarkets, no-prod, con
  `login()` + `get_segments()` ya verificados funcionando ahí (ver memoria
  `project_matriz_bbsa_sandbox.md`). Esto **desbloquea matriz para correr en vivo esta fase**,
  resolviendo la mitad de `LIVE-MATZ-33` que era resoluble desde dentro del proyecto (la otra
  mitad — la prohibición P-05 de rodear la política para hosts *no* confirmados — sigue vigente
  sin cambios). El cambio debe documentarse en el código (comentario) y en el reporte de esta
  fase como una decisión de seguridad explícita, siguiendo el mismo patrón de gate humano que
  D-08/D-18 en fases anteriores — no un ajuste silencioso.

### Cadenas profundas a agregar por driver (SC-1)

- **D-03 (iol — gap principal):** `main_iol.py` no referencia `.puntas` en ningún lugar hoy.
  Esta fase agrega el ejercicio de `titulo.puntas.precioCompra` y/o `cotizacion.puntas[0].precioCompra`
  **dentro de los probes existentes** que ya obtienen `Cotizacion`/`Titulo` (p. ej.
  `probe_get_quote_sync`/`_async`, `probe_get_instruments_by_type_sync`/`_async`) — no como un
  probe nuevo, siguiendo la convención "una llamada HTTP por concepto de probe" que ya sigue el
  resto del driver. Debe correr en **ambas** superficies (sync + async).
- **D-04 (higyrus — cadena tipada real):** Los probes actuales de higyrus trabajan mayormente
  sobre dicts crudos (`_raw_request_sync`/`_async`). Esta fase suma **al menos una cadena real
  sobre el wrapper tipado** — ej. `posicion.parking[...]` (`Posicion.parking: list[Parking]`,
  `models.py:316`) o una cadena equivalente sobre `Cuenta.domicilios`/`.personasRelacionadas` —
  en simetría con iol/matriz/market-data, todos ejercitando al menos una cadena `.modelo.campo`
  real contra la API en vivo, no sólo la ejecución silenciosa de la función tipada.
- **D-05 (matriz):** Con D-02 desbloqueando el sandbox, matriz debe ejercitar
  `snapshot.last.price` / `.bids` / `.offers` / `.settlement` / `.close` / `.open_interest`
  (los 6 alias de Phase 37) contra el sandbox bbsa real, en sync y async donde aplique — matriz
  no tiene superficie async nativa (`matriz_client` no tiene `aio.py`, sólo REST sync +
  `ws_client` en thread daemon), así que "ambas superficies" para matriz se satisface con REST +
  WS, no con un `aio.py` inexistente.
- **D-06 (ambito — sin cadena, declarado por diseño):** `ambito_financiero_client.models` no
  declara ninguna clase (`__all__: list[str] = []`, decisión deliberada de Phase 29/31). Esta
  fase **no debe inventar un modelo** para ambito sólo para tener algo que encadenar — eso
  repetiría exactamente el anti-patrón que Phase 37 SC-1 prohibió para matriz ("modelo
  inventado presentado como observado"). El cumplimiento de SC-1 para ambito se satisface
  **declarando la ausencia medida** (como hizo `38-CENSUS.md` con higyrus/ámbito/wallets) — el
  driver de ambito sigue ejercitando sus endpoints reales (que ya existen), pero sin pretender
  una cadena de modelo que el paquete no tiene.
- **D-07 (market-data — fuera de alcance):** No se toca `main_market_data.py` en esta fase — ya
  cumple su parte desde Phase 36 (SC-5, `.market_data.last.price` etc. ya ejercitados en
  `main_market_data.py`).

### Fix in-cycle de divergencias CONFIRMED (SC-3)

- **D-08:** Toda divergencia CONFIRMED encontrada durante esta fase se corrige **in-cycle**:
  espejo sync/async del fix + un test de regresión **mockeado** que la pinea (mismo patrón que
  todas las fases previas de v1.7 — 36/37/38). No se difiere ninguna divergencia real a menos
  que sea explícitamente aprobada por el operador con destino nombrado (mismo patrón que
  `LIVE-HIGY-33`/`LIVE-MATZ-33`).

### `verify_cycle_closure` — PASS no-vacuo (SC-3)

- **D-09:** `verify_cycle_closure()` (`verification/cycle_report.py:123`) hoy devuelve
  `(True, [])` tanto si no hay findings reales como si el archivo de findings ni existe —
  exactamente el "PASS vacuo" que SC-3 prohíbe explícitamente. Esta fase necesita una
  verificación adicional (wrapper o extensión de la función — decisión de implementación, no de
  producto) que confirme **evidencia positiva** de que el driver corrió contra la API en vivo
  (p. ej. conteo de probes ejecutados > 0, o un timestamp de corrida reciente) antes de aceptar
  el PASS, para cada paquete medido.

### Contraste del censo contra Fase 33 / 29-SIZING (SC-4)

- **D-10:** El contraste de esta corrida contra `33-CENSUS.md`
  (`.planning/milestones/v1.6-phases/33-verificaci-n-en-vivo-en-modo-estricto-fixes/33-CENSUS.md`)
  y `29-SIZING.md`
  (`.planning/milestones/v1.6-phases/29-decoder-observable/29-SIZING.md`) debe usar la **misma
  unidad** que esos artefactos ya establecieron: triples distintos `(slug, model, field_path,
  kind)` de `DivergenceHandler.seen` (`verification/divergences.py:112-196`) — **no** el conteo
  `FINDING=N` del SUMMARY del driver ni el conteo crudo de entradas del findings-file. `33-CENSUS.md`
  ya documentó un factor ~2× de duplicación por superficie (`surface-in-title-write-new` escribe
  un finding por superficie por triple) que reaparecería si se usa la unidad equivocada, y
  documentó que el piso de `29-SIZING.md` cuenta registros sumados por archivo (una misma triple
  en dos archivos del corpus cuenta dos veces) mientras `handler.seen` cuenta triples distintas
  (cuenta una vez) — hay que reconciliar sobre esa diferencia, no ignorarla.
- **D-11:** El reporte de esta fase debe declarar explícitamente, por separado, cuántas
  divergencias de la Fase 33 desaparecieron por **colapso de política Null Object** (ya no se
  registran porque Phase 35 las volvió silenciosas) frente a cuántas desaparecieron por
  **corrección real** (fix efectivo en Phases 36-38 o en esta misma fase) — esto es SC-4 literal:
  "para que la baja de números no pueda leerse como un falso limpio". La contabilidad debe cruzar
  con `35-RETIRED-TRIPLES.md` (el ledger que Phase 38 D-12 dejó pendiente de actualizar para esta
  fase — ver Canonical References).

### Casos límite a probar (SC-2)

- **D-12:** Para cada paquete que efectivamente corra, la corrida debe incluir intencionalmente
  (no sólo esperar que ocurran) los casos límite que sólo produce la API en vivo: mercado
  cerrado, fila no-data, campo ausente, respuesta 204/vacía — ninguna cadena debe lanzar
  `AttributeError` ni `TypeError` en ninguno de esos casos. Para matriz esto implica correr
  **dentro de una ventana de sesión de trading ARG** si se quiere distinguir "mercado cerrado"
  (null legítimo) de "campo mal modelado" — precedente P-12 de Phase 33.

### Claude's Discretion

- Forma exacta del wrapper/extensión para el PASS no-vacuo de `verify_cycle_closure` (D-09) —
  decisión de implementación.
- Redacción exacta del reporte de contraste Fase 33 vs Fase 39 (D-10/D-11) — sigue el formato de
  censo ya validado (`35-RETIRED-TRIPLES.md`, `33-CENSUS.md`, `38-CENSUS.md`), layout libre.
- Probe exacto elegido en higyrus para la cadena tipada de D-04 (`Posicion.parking` vs
  `Cuenta.domicilios` vs otro) — cualquiera que ejercite una cadena `.modelo.campo` real basta.
- Nombre y ubicación exacta del artefacto de censo de esta fase (`39-CENSUS.md` o similar).

### Folded Todos

Ninguno — `todo.match-phase 39` no encontró coincidencias (`todo_count: 0`).
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/ROADMAP.md` — sección "Phase 39" (goal, 4 success criteria formales, requirement
  LIVE-NOBJ-01) y las notas de sizing/restricciones del milestone v1.7 (líneas 34-39, sobre
  `LIVE-HIGY-33`/`LIVE-MATZ-33` "que no se rodea" — D-02 de esta fase es la resolución parcial
  autorizada explícitamente por el operador para el caso bbsa específico, no una excepción
  general a esa regla)
- `.planning/REQUIREMENTS.md` — LIVE-NOBJ-01 (línea 37)
- `main_iol.py` — probes de quote/instrumentos donde debe sumarse la cadena `.puntas` (D-03);
  cero referencias actuales a `puntas` (confirmado por grep)
- `main_higyrus.py:144-151` — `_RESIDUAL_PROBE_EXCEPTIONS`, la rama que hoy absorbe el DNS
  ConnectError como FINDING en vez de SKIPPED (D-01); probes actuales sobre `_raw_request_sync`/
  `_async` (líneas 335-378) que D-04 debe complementar con una cadena tipada real
- `packages/higyrus-client/src/higyrus_client/models.py:316` (`Posicion.parking`),
  `:463-466` (`Cuenta.domicilios`/`.personasRelacionadas`/`.mediosComunicacion`/
  `.cuentasBancarias`) — candidatos de cadena para D-04
- `main_matriz.py` — el assert D-MATZ-33 a ampliar (~línea 2558-2566, verificar línea exacta en
  HEAD); `probe_get_market_data` construye el payload crudo pero no arma `MarketDataSnapshot`
  para caminar `.last.price` hoy (línea 1359 sólo usa `MarketDataSnapshot` para el diff de
  `field_type_map`) — D-05 requiere cerrar ese gap
- `packages/matriz-client/src/matriz_client/models.py` — `MarketDataSnapshot` y los 6 alias de
  Phase 37 (`last`/`bids`/`offers`/`settlement`/`close`/`open_interest`)
- `main_verify.py:37-42,60-81` — `_ENV_SKIP` regex y la lógica de clasificación PASS/SKIPPED/
  FAILED/RAN que D-01 debe corregir
- `verification/env_gate.py:32-41` — `require_env`, chequea sólo presencia de env vars, no
  resolvibilidad DNS — por qué higyrus no cae hoy en la rama SKIPPED por sí solo
- `verification/cycle_report.py:20-21,123` — `verify_cycle_closure`, el PASS vacuo que D-09 debe
  cerrar
- `verification/divergences.py:112-196` — `DivergenceHandler.seen`, la unidad de triples
  `(slug, model, field_path, kind)` que D-10 exige usar para el contraste
- `.planning/milestones/v1.6-phases/33-verificaci-n-en-vivo-en-modo-estricto-fixes/33-CENSUS.md`
  — método de censo de Fase 33 (líneas 9-38: unidad, factor ~2× de duplicación, floor-vs-triples)
  a reutilizar para D-10/D-11; contiene también S-3/S-4/S-5 de matriz aún COULD-NOT-DECIDE
  (candidatos a resolverse ahora que D-02 desbloquea el sandbox)
- `.planning/milestones/v1.6-phases/29-decoder-observable/29-SIZING.md` — piso ratificado
  (higyrus ≥22, matriz ≥24, market-data ≥50) contra el que D-10 debe contrastar
- `.planning/phases/35-fundaci-n-null-object-bool-pol-tica-del-walker/35-RETIRED-TRIPLES.md` —
  ledger de triples retiradas por la política Null Object; Phase 38 D-12 dejó pendiente su
  actualización para esta fase (D-11 la retoma)
- `.planning/phases/36-.../36-CONTEXT.md`, `37-.../37-CONTEXT.md`, `38-.../38-CONTEXT.md` —
  decisiones previas del milestone v1.7 que esta fase ejercita en vivo (no re-decide)
- Memoria de sesión: `project_matriz_bbsa_sandbox.md` (`.claude/…/memory/`) — evidencia operador
  del sandbox bbsa confirmado seguro, base de D-02
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `verification/divergences.py` (`probe_context`/`divergence_capture` ContextVars,
  `DivergenceHandler`) ya cableado a los 5 drivers desde Phase 29/33 — no requiere nueva
  infraestructura, sólo su uso correcto para el contraste D-10.
- SHAPE-diff infra (`_write_or_check_schema`, snapshots write-once) ya existe y funciona — casos
  límite (D-12) se detectan con la misma maquinaria, no hace falta una nueva.
- Los 6 alias de Phase 37 (`MarketDataSnapshot.last`/etc.) y los Null Objects de Phase 38
  (`Punta`) ya están en código — esta fase sólo necesita *llamarlos* desde los drivers, no
  implementarlos.

### Established Patterns
- "SKIPPED con causa medida y destino nombrado, nunca como cero" — patrón fijado en Phase 33,
  reusado literal por D-01.
- Checkpoint humano explícito para cambios security-policy-adjacent (D-08/D-18) — reusado
  literal por D-02 (ampliación del allowlist D-MATZ-33).
- Censo con disposición por fila, ceros declarados por enumeración — patrón de
  `35-RETIRED-TRIPLES.md`/`33-CENSUS.md`/`38-CENSUS.md`, reusado por D-10/D-11.

### Integration Points
- `main_verify.py` orquesta los 5 `_DRIVERS` (incluye market-data, que esta fase no toca) — D-01
  toca su lógica de clasificación, que es compartida entre todos los paquetes, así que el fix
  debe probarse contra los 4 paquetes en alcance sin romper la clasificación de market-data.
</code_context>

<specifics>
## Specific Ideas

- El operador confirmó explícitamente (checkpoint, 2026-08-29) que `bbsa.matrizoms.com.ar` es un
  sandbox real, seguro y distinto de producción, y autorizó ampliar el allowlist D-MATZ-33 para
  incluirlo por esta vía — no es una asunción de Claude, es una decisión firmada (D-02).
- El resto de las asunciones presentadas (clasificación PASS/SKIPPED, cadenas por driver, PASS
  no-vacuo, unidad de contraste del censo) fueron confirmadas sin cambios ("Sí, proceder").
</specifics>

<deferred>
## Deferred Ideas

- Reparar `verification/` (pytest harness roto, HARN-VERIF-01) — deuda pre-existente, no tocada
  por esta fase (los drivers `main_*.py` son un sistema distinto de `verification/`'s pytest
  suite rota).
- Resolver S-3/S-4/S-5 de matriz (`33-CENSUS.md`) más allá de lo que el censo de esta fase mida
  naturalmente al correr — no es un objetivo explícito de LIVE-NOBJ-01, pero puede resolverse
  como efecto colateral de D-02/D-05 si el censo lo permite.
- Censo de valores RESPONSE Literal de matriz (`33-LITERALS.md`, 7 campos) — mismo bloqueo
  histórico, no en alcance explícito de esta fase salvo que surja naturalmente.
- Publicación/versión/changelog de los paquetes que cambiaron — Phase 40 (PUB-NOBJ-01).

### Reviewed Todos (not folded)

Ninguno — `todo.match-phase 39` no encontró coincidencias.
</deferred>
