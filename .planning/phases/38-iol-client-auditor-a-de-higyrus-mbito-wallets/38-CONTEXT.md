# Phase 38: `iol-client` + auditoría de higyrus/ámbito/wallets - Context

**Gathered:** 2026-08-29 (assumptions mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

Los cuatro paquetes restantes (`iol-client`, `higyrus-client`, `ambito-financiero-client`,
`wallets-client`) quedan sin eslabones `None` en sus cadenas — `titulo.puntas.precioCompra` es
siempre válido — y la limpieza de los tres casi-limpios (higyrus/ámbito/wallets) queda **medida
campo por campo**, no supuesta. Requisitos: NOBJ-IOL-01, NOBJ-AUD-01.

NOBJ-IOL-01 cubre **únicamente** los dos campos `puntas` (`Cotizacion.puntas`, `Titulo.puntas`) —
no una auditoría completa de retornos públicos de iol; esa auditoría más amplia del plan fuente
queda superseded por el alcance más angosto del roadmap/REQUIREMENTS.md. NOBJ-AUD-01 cubre
higyrus/ámbito/wallets únicamente — no iol, no market-data/matriz (ya cerrados en Phases 36/37).

Paquetes disjuntos con 36 (`market-data-client`) y 37 (`matriz-client`), ambos completos. Este
phase toca `packages/iol-client/`, `packages/higyrus-client/`, `packages/ambito-financiero-client/`,
`packages/wallets-client/` y, por la naturaleza cross-package del gate, `tools/check_surface_types.py`
(ver D-10). No toca `packages/market-data-client/` ni `packages/matriz-client/`.

Versionado (bump, changelog callout con número real, tabla de migración publicada) queda
**fuera de alcance** — eso es Phase 40 (PUB-NOBJ-01). Verificación en vivo del encadenamiento
profundo también fuera de alcance — Phase 39 (LIVE-NOBJ-01).
</domain>

<decisions>
## Implementation Decisions

### iol `puntas` — shape + mirroring (NOBJ-IOL-01)

- **D-01:** `Cotizacion.puntas: list[Punta]` y `Titulo.puntas: Punta` quedan declarados
  **REQUIRED, sin default a nivel dataclass** (ni `field(default_factory=list)` ni
  `field(default_factory=Punta.empty)`). El walker (`_decode.py:447-495`, política NOBJ-02 de
  Phase 35) ya colapsa `null`/ausente a `[]`/instancia vacía **sin** emitir divergencia para
  campos no-opcionales de tipo lista/modelo — el "default `[]`" de SC-1 es ese comportamiento
  del walker, no un default de Python. Un default de dataclass es además **mecánicamente
  imposible** sin reordenar campos: `Cotizacion.puntas` es el campo 15/20 seguido de 4 campos
  sin default (`tendencia`, `ultimoPrecio`, `variacion`, `volumenNominal`); `Titulo.puntas` es
  13/20 seguido de 6 — reordenar cambiaría la firma posicional de `__init__` registrada en
  `verification/snapshots/iol-client-surface.txt:11,21`. Precedente exacto: Phase 36 D-04 hizo
  lo mismo con `MarketDataSnapshot.entries`/`market_data` (sin default de dataclass, sólo el
  walker).
- **D-02:** **Nada que mirrorear** en `client.py`/`aio.py`. Ambas superficies llaman a los
  mismos parsers compartidos de `_core.py` (`_core.parse_get_quote_response`, etc. —
  `client.py:528,548,557,572` / `aio.py:547,563,569,580`), que a su vez llaman
  `Cotizacion.from_api`/`Titulo.from_api`. El cambio queda confinado a `models.py:213,301` +
  docstrings. No editar `client.py`/`aio.py`/`_core.py`/`_decode.py` para "satisfacer D-NO-06" —
  eso duplicaría lógica de decode y reintroduciría el drift que `surface_parity.py` existe para
  prevenir.
- **D-03:** Cero clases nuevas → cero edits a `test_null_object.py`, incluido **sin** bump del
  roster floor (`>= 4` en `test_null_object.py:226`, iol ya ships exactamente 4 clases:
  `Punta`, `Cotizacion`, `Instrumento`, `Titulo`). El orden de dispatch de `_perturb` tampoco se
  ve afectado — `apertura: float` es el primer campo de ambas clases y dispara la rama
  `int | float` antes de llegar a la rama de modelo anidado.

### Migración de tests existentes

- **D-04:** 6 aserciones rompen en runtime y requieren migración semántica:
  `test_models.py:209` (fila histórica), `:229` (dict vacío), `:235` (`from_api(None)`), `:248`
  (`test_puntas_nula_queda_nula`), `:412` (Titulo dict vacío), `:441`
  (`test_titulo_puntas_nula_no_emite_registro`). 2 aserciones quedan tautológicamente verdes sin
  cambio requerido (`:264`, `:389` — `is not None` sigue siendo cierto). El test
  `test_puntas_nula_queda_nula` (`:247`) se **renombra** (no solo se re-asertea) — el nombre
  codifica la semántica retirada. `test_decode.py:861-870` no requiere cambio (fixture local
  `puntas: list[_Leaf]` ya es non-Optional).
- **D-05:** Los dos tests "no emite registro" (`:198-210`, `:436-441`) mantienen su aserción
  `_divergences(caplog) == []` pero **sí requieren reescritura de docstring**: hoy el cero viene
  de la rama `Union`/Optional temprana de `_decode.py:438-441`; tras el cambio viene de la rama
  de colapso NOBJ-02 (`:447-495`). Las docstrings actuales citan verbatim la rama vieja
  (`:201` "D-03: la rama Optional del walker devuelve `None` sin emitir registro",
  `:437` similar) — dejarlas sería una afirmación de procedencia falsa sobre una rama que ya no
  ejecuta (misma clase de defecto que Phase 36 CR-02).
- **D-06:** Idioma de reemplazo, siguiendo Phase 36 D-07 literal: `quote.puntas == []` para
  `Cotizacion`; `bool(titulo.puntas) is False` / `titulo.puntas == Punta.empty()` para `Titulo`
  (no `not titulo.puntas` — la equivalencia contra `empty()` pinea la identidad del Null Object,
  no solo el predicado compuesto).

### Censo de higyrus / ámbito / wallets (NOBJ-AUD-01)

- **D-07:** El censo es un **artefacto phase-local** (`38-CENSUS.md` bajo el directorio de esta
  fase), siguiendo la forma de `.planning/phases/35-.../35-RETIRED-TRIPLES.md` (tabla con columna
  de disposición + sección de método/límites + ceros declarados explícitamente por enumeración).
  **No** es una entrada en `.planning/verification/<pkg>-findings.md` — esos ledgers son
  auto-generados por el harness de verificación en vivo entre marcadores
  `<!-- BEGIN AUTO-GENERATED -->`/`<!-- END AUTO-GENERATED -->` con schema fijo de corrida real
  (ID/Class/Surface/Status); un censo estático de anotaciones no tiene contexto de corrida ni
  ciclo de vida OPEN→FIXED y corrompería ese formato.
- **D-08:** El censo enumera la **población candidata completa** (todo campo modelo/lista/mapping
  y todo retorno público, tenga o no violación), no solo violaciones — de lo contrario higyrus/
  ámbito/wallets (medido: 0 violaciones en los tres) producen tablas vacías, que SC-4 prohíbe
  explícitamente ("no reportar un verde vacuo"). Medido por introspección `get_type_hints`:
  higyrus = 15 clases / 142 campos / 0 campos modelo-lista-mapping opcionales / 0
  `dict[str, Any]`; ámbito y wallets = 0 clases (`models.py` deliberadamente vacío en ambos,
  decisión documentada de Phase 29/31).
- **D-09:** La mitad de `dict[str, Any]`-en-retornos de SC-2/SC-3 ya está resuelta vía las
  exenciones existentes del gate (`to_dict()` serialize-out ×9, shims legacy `_request` ×2,
  confirmado por corrida real de `tools/check_surface_types.py`: "442 fields scanned, 24
  exempted, 0 violations"). Las filas del censo para estos casos **citan** la tabla de exención
  existente del gate — no proponen fix, no re-abren el D-08 escape hatch documentado en
  `packages/iol-client/README.md:150-161`.

### README de iol — callout de breaking change (SC-1)

- **D-10:** Formato de sección: `## Unreleased — BREAKING` (precedente de Phase 36 en
  `packages/market-data-client/README.md:7-33`, mismo milestone v1.7) — NO
  `### v0.4.0 — sin publicar todavía` (formato v1.6 de higyrus) porque ese formato asume el
  número de versión que Phase 40 asigna. El callout incluye tabla de migración vieja→nueva con
  las dos filas asimétricas: `Cotizacion.puntas`: `None→[]` (falsy→falsy, sin flip real) y
  `Titulo.puntas`: `None→Punta.empty()` (falsy vía `__bool__`, pero ya no `None` — checks
  `is None` dejan de disparar en silencio). Filas de migración: `titulo.puntas is None` →
  `not titulo.puntas`; `quote.puntas or []` → `quote.puntas`.

### Gate ratchet — extensión de `check_surface_types.py`

- **D-11:** El predicado de campo del gate se extiende para banear también `Model | None` y
  `list[Model] | None` en campos de dataclass exportada (no solo `dict[str, Any]`/`Any` desnudo
  como hoy) — mismo patrón que la extensión de Phase 37 D-01 (dimensión `ast.AnnAssign`), ahora
  ensanchando el predicado en vez de agregar una dimensión nueva. Se agrega un fixture RED
  espejando `packages/iol-client/tests/test_surface_types_red.py` (D-01d de Phase 37) que prueba
  que el gate detecta un campo `Model | None` reintroducido. SC-3 pasa de ser una medición
  puntual a un **ratchet permanente de CI** — el gap existía porque Phase 37 D-01b restringió el
  predicado deliberadamente a `dict[str, Any]`/`Any` para no reenrojecer los 11 leaves
  `Literal | None` de matriz; el predicado extendido debe distinguir "campo tipado como
  dataclass/lista-de-dataclass" de "campo tipado como alias `Literal`" para no reenrojecer esos
  mismos 11 sitios (`matriz_client/models.py:532,552,553,561,607,619,660,661,662,669`).
  **Decisión explícita del operador** (no auto-resuelta): extender el gate, no dejarlo como
  medición de una sola vez.

### Contabilidad para Phase 39 — `35-RETIRED-TRIPLES.md`

- **D-12:** Phase 38 le debe a Phase 39 una actualización explícita del ledger
  `35-RETIRED-TRIPLES.md`: la fila que ya nombra los 2 links de iol (`:137-144`) tiene referencias
  de línea desactualizadas (`iol_client/models.py:154,242` → hoy `:213,301`, tras drift de código
  entre Phase 35 y 38) y debe corregirse; y la nota de `:190` (que dice explícitamente que
  Phases 36/37/38 introducen nuevos links no-`Optional` cuyas triples retiradas "no están en este
  ledger y pertenecen a la contabilidad de sus propias fases") implica que esta fase debe dejar
  registrado, en algún artefacto (el propio `38-CENSUS.md` o una nota en `35-RETIRED-TRIPLES.md`),
  cuántas triples retira el cambio de `puntas` — para que Phase 39 pueda separar "desapareció por
  política Null Object" de "desapareció por fix" sin adivinar.

### Claude's Discretion

- Nombre exacto del archivo del censo (`38-CENSUS.md` vs. variante) y organización interna de sus
  secciones — sigue la forma de `35-RETIRED-TRIPLES.md` pero el detalle de layout es libre.
- Redacción exacta de las docstrings reescritas en D-05 y del párrafo de procedencia en `models.py`
  para los dos campos `puntas` — sigue el patrón ya establecido por Phases 36/37, contenido libre.
- Alcance exacto del predicado extendido de D-11 (si distingue por `issubclass(SafeModel)` vs. por
  el roster de clases `Literal` conocidas) — decisión de implementación, no de producto.

### Folded Todos

Ninguno — `todo.match-phase 38` no encontró coincidencias (`todo_count: 0`).
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/ROADMAP.md` — sección "Phase 38" (goal, 4 success criteria formales, requirements)
- `.planning/REQUIREMENTS.md` — NOBJ-IOL-01 (línea 24), NOBJ-AUD-01 (línea 33)
- `.future_plans/api-tipada-null-objects.md` — plan fuente del milestone v1.7: principios
  D-NO-01..06, Fase D (iol) y Fase E (higyrus/ámbito/wallets), inventario de violaciones — nota:
  el alcance de iol en esta fase es más angosto que lo que la Fase D del plan fuente describe
  (ver `<domain>`)
- `packages/iol-client/src/iol_client/models.py` — los 2 campos a retipar
  (`Cotizacion.puntas:213`, `Titulo.puntas:301`); `Punta` (líneas ~157-169, shape "inobservado");
  `SafeModel.__bool__`/`empty()` (líneas ~114-137)
- `packages/iol-client/src/iol_client/_decode.py` — walker byte-verbatim (líneas 447-495,
  colapso NOBJ-02); NO se toca en esta fase
- `packages/iol-client/src/iol_client/_core.py` — parsers compartidos que ambas superficies
  llaman (`parse_get_quote_response`, etc.) — confirma que no hay mirroring pendiente
- `packages/iol-client/tests/test_null_object.py` — fixture pre-construida en Phase 35 que
  anticipa exactamente esta fase (docstring cita "the invariant Phase 38 depends on"); roster
  floor línea 226, `_perturb` líneas ~113-139
- `packages/iol-client/tests/test_models.py` — las 6 aserciones a migrar (líneas 209, 229, 235,
  248, 412, 441), el rename de `:247`, las 2 docstrings a reescribir (`:201`, `:437`)
- `packages/iol-client/tests/test_decode.py` — sin cambios requeridos (líneas 861-870, fixture ya
  non-Optional)
- `packages/iol-client/README.md` — sección `## Changelog` (línea ~110), prosa de "Flip de
  truthiness" existente a espejar (líneas 140-149) como plantilla de tono
- `packages/market-data-client/README.md` — líneas 7-33, plantilla exacta de
  `## Unreleased — BREAKING` a copiar (formato, D-10)
- `packages/higyrus-client/src/higyrus_client/models.py` y `client.py`/`aio.py` — evidencia de
  0 violaciones (censo D-08); funciones públicas ya devuelven modelos tipados
- `packages/ambito-financiero-client/src/ambito_financiero_client/models.py` — vacío deliberado
  documentado (Phase 31, D-11 del propio módulo)
- `packages/wallets-client/src/wallets_client/models.py` y `client.py` — stub documentado (Phase
  29 exemption), sin funciones públicas de dominio que auditar
- `.planning/phases/35-fundaci-n-null-object-bool-pol-tica-del-walker/35-RETIRED-TRIPLES.md` —
  precedente de formato del censo (D-07); líneas 137-155 (fila de iol, con line refs a corregir)
  y línea 190 (contabilidad que Phase 38 debe completar, D-12)
- `.planning/phases/36-market-data-client-market-data-tipado-revocaci-n-de-la-fase-/36-CONTEXT.md`
  — precedente directo de D-07 (migración de semántica de tests, D-06 de esta fase)
- `.planning/phases/37-matriz-client-dicts-residuales-tipados-alias/37-CONTEXT.md` — precedente
  de D-01/D-01b/D-01d (extensión del gate, D-11 de esta fase) y de docstrings de procedencia
- `tools/check_surface_types.py` — gate a extender (D-11); leer docstring completo antes de
  tocarlo, especialmente el razonamiento de D-01b de Phase 37 (por qué el predicado quedó
  angosto) para no repetir el mismo reenrojecido en los 11 leaves `Literal` de matriz
- `packages/iol-client/tests/test_surface_types_red.py` — patrón de fixture RED a espejar (D-11)
- `packages/matriz-client/src/matriz_client/models.py:532,552,553,561,607,619,660,661,662,669` —
  los 11 sitios `Literal | None` que el predicado extendido NO debe reenrojecer
- `verification/regen_snapshots.py` — regenerar snapshot de superficie pública tras el cambio de
  `puntas` (SC-1 lo exige explícitamente), commitear el diff en el mismo commit
- `verification/snapshots/iol-client-surface.txt` — snapshot a regenerar (líneas 11, 21 citan la
  firma posicional afectada por D-01)
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `SafeModel.__bool__`/`empty()` (Phase 35) ya disponibles en la base de iol — las clases
  existentes los heredan sin trabajo adicional, solo cambia la anotación de tipo.
- El walker `_decode.py` ya implementa el colapso silencioso NOBJ-02 desde Phase 35 — no requiere
  ningún cambio en esta fase.
- `test_null_object.py` de iol ya viene pre-armado desde Phase 35 anticipando esta fase
  exactamente (fixtures `_AliasShaped`/`_AliasFree` para el criterio 5, aunque iol no necesita
  alias propiamente — el wire key `puntas` ya es legible, a diferencia de `LA`/`BI` de
  matriz/market-data).
- Formato de censo ya validado (`35-RETIRED-TRIPLES.md`) y plantilla de README breaking-change ya
  validada (`market-data-client/README.md`, Phase 36) — ambos se copian, no se inventan de cero.
- Gate `check_surface_types.py` ya tiene el mecanismo de extensión de predicado documentado por
  Phase 37 D-01 — D-11 reusa el mismo patrón de extensión, solo cambia qué se prohíbe.

### Established Patterns
- D-NO-06: todo cambio de lógica se espeja `client.py`/`aio.py` — pero esta fase no tiene lógica
  de decode propia que espejar (confirmado D-02), así que la paridad sync/async se sostiene sola.
- "Roster cerrado + reporting de divergencias para extras" — no aplica directamente a `puntas`
  (`Punta` ya tiene roster cerrado desde Phase 30), pero sí es el patrón que higyrus/ámbito/wallets
  ya cumplen naturalmente (0 violaciones medidas).
- Migración de semántica de tests de `is None` a veracidad/lista-vacía — patrón fijado
  literalmente por Phase 36 D-07, reusado aquí sin variación (D-06).
- Gates son ratchets que nunca se debilitan bajo presión — si el predicado extendido reenrojece
  algo fuera de alcance (matriz Literal leaves), la respuesta es angostar el predicado
  correctamente, no exentar por nombre libre.

### Integration Points
- `tools/check_surface_types.py` corre como step del job `lint` en CI, cross-package, sin lista
  hardcodeada de paquetes — la extensión de D-11 aplica automáticamente a los 6 paquetes.
- `main_iol.py` no tiene referencias a `puntas` hoy — el driver no ejercita esta cadena; eso es
  explícitamente trabajo de Phase 39 (LIVE-NOBJ-01), no de esta fase.
</code_context>

<specifics>
## Specific Ideas

Ninguna referencia particular adicional del usuario más allá de las 3 decisiones explícitas
tomadas en checkpoint (D-10 formato README, D-11 extender el gate, y confirmación general de las
demás asunciones vía "Sí, proceder").
</specifics>

<deferred>
## Deferred Ideas

- Auditoría completa de retornos públicos de `iol-client` más allá de `puntas` (Fase D completa
  del plan fuente) — explícitamente fuera del alcance angosto de NOBJ-IOL-01 en esta fase; si
  aparecen más violaciones se descubren en el propio censo de auditoría o en Phase 39.
- Bump de versión, changelog callout con número real, tabla de migración publicada — Phase 40
  (PUB-NOBJ-01).
- Verificación en vivo del encadenamiento profundo de `puntas` (`titulo.puntas.precioCompra`
  contra la API real) — Phase 39 (LIVE-NOBJ-01); `main_iol.py` no se toca en esta fase.
- Exención o retipado de `CalendarConfig.warnings`/`CalendarConfigPreview.warnings` de
  market-data-client (`list[Any]`) — ya deferido explícitamente por Phase 37, sigue fuera de
  alcance (paquete disjunto).

### Reviewed Todos (not folded)

Ninguno — `todo.match-phase 38` no encontró coincidencias.
</deferred>
