# Phase 35: Fundación Null Object — `__bool__` + política del walker - Context

**Gathered:** 2026-08-28 (assumptions mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

La ausencia deja de expresarse con `None` y pasa a expresarse con veracidad — toda base
`SafeModel` de los 6 paquetes sabe decir "estoy vacío" y el walker `_decode` sabe colapsar un
`null` legítimo sobre un eslabón sin ensuciar el canal de divergencias, **sin que ninguna firma
pública cambie todavía**. Requirements: NOBJ-01, NOBJ-02. Las propiedades alias y los cambios de
forma de modelos son de las fases 36-38 — esta fase entrega política y capacidad, no ruptura.
</domain>

<decisions>
## Implementation Decisions

### Mecanismo del walker (NOBJ-02)

- **D-01:** La disposición "colapso legítimo de null/ausente" se decide **por la anotación sola**
  — sin registro por-modelo, sin marcador `Annotated`, sin eje nuevo en `DecodePolicy`. El branch
  `Optional` ya retorna temprano (`_decode.py:434-440`), así que todo lo que alcanza el sitio de
  lista (`:442-445`) y el de modelo (`:482-484`) es no-opcional por construcción. El edit es
  quirúrgico: borrar la llamada `sink(...)` en esos 2 sitios. En el sitio de lista, el silencio se
  gatea a `value is None` (`_kind_of(value) == "missing"`): un wrong-type (`"abc"` donde va una
  lista) sigue emitiendo el record de seis claves. Ambos sitios ya devuelven `[]` / instancia
  vacía hoy — no cambia el valor de retorno, solo el reporting.
- **D-02:** `strict_decode` no necesita código nuevo: el raise vive en el único choke point
  `DecodeScope.__call__` (`_decode.py:205-221`). No llamar al sink = no raise para el colapso
  legítimo; wrong-type sigue llamando al sink y sigue fatal bajo strict.
- **D-03:** Tres disposiciones adyacentes quedan **sin tocar**: (a) el record `non_dict` top-level
  cuando el payload entero es `None`/204 (`:575-582`) — sigue emitiéndose; (c) el eje mapping de
  `dict[str, Any]` (`_mapping_value` en `models.py` de matriz/market-data) — vive fuera del walker
  y no se toca en esta fase.
- **D-04:** El caso (b) — un `null` como **elemento dentro** de una `list[Model]` (alcanza el
  branch de modelo vía la recursión `:449-452`) — **se silencia junto con el resto**: una sola
  regla uniforme ("null/ausente sobre eslabón no-opcional colapsa sin registro"), sin threading de
  flags que ensancharía el cuerpo canónico verbatim de las 5 copias.

### Superficie de las bases SafeModel (NOBJ-01)

- **D-05:** Se tocan exactamente **4 jerarquías**: `SafeModel` de higyrus (`models.py:52-87`), iol
  (`models.py:65-94`) y market-data (`models.py:204-245`), más `_SafeModel` de matriz
  (`models.py:192-250`). **Ámbito y wallets NO ganan base**: sus `models.py` están deliberadamente
  vacíos con docstring que lo explica (wallets rompería el import del paquete). El criterio 1
  ("los 6 paquetes") se satisface por enumeración vacía en esos dos, y así se documenta.
- **D-06:** `__bool__` se implementa como `return self != type(self).empty()` — un **cuerpo
  byte-verbatim único** copiado a las 4 bases. Verificado por probe sobre las 52 clases reales de
  los 4 paquetes: `X.from_api(None) == X.empty()` da 0 mismatches, 0 errores (~2,6 µs/call).
- **D-07:** `empty()` acepta **2 formas** (no puede ser byte-verbatim en las 4 bases): higyrus/iol
  usan `cls(**walk_model(cls, {}, policy=POLICY, sink=SILENT_SINK))`; market-data/matriz agregan
  el pase `_apply_mapping_policy(...)` que sus `from_api` ya llevan. Cada docstring declara el
  delta. **Prohibido** implementar `empty()` como `cls.from_api(None)`: emite `non_dict` en 3
  bases (viola T-29-33 "`empty()` emits nothing") y recursa infinito en matriz (early-return
  `empty_classmethod` en `models.py:223-228`). No se inventa un no-op compartido para forzar
  byte-identidad (dead code que la Phase 36 borraría).
- **D-08:** `UnknownFrame` de matriz (`models.py:504-530`, no hereda `_SafeModel`, miembro del
  union público `PrimaryWsMessage`) **gana un `__bool__` a mano** que espeja la semántica de la
  base (`self != type(self).empty()` — ya tiene `empty()` propio), para que `if frame:` sea
  consistente con todos sus hermanos del union. Las 7 dataclasses request de market-data
  (`LatestRequest`, `NewSymbol`, …) son entrada, no salida — fuera de alcance.
- **D-09:** Dato a documentar (no a "arreglar"): `MarketDataSnapshot.received_at` se inyecta con
  `time.time()` post-walk (`market_data_client/models.py:344-353`), así que la truthiness a nivel
  snapshot la domina el timestamp. La truthiness es test de vacuidad **a nivel campo**
  (`snapshot.market_data`), no a nivel snapshot — el docstring lo dice.

### Gates, hash canónico y snapshots (criterios 3-4)

- **D-10:** El edit del walker se aplica **idéntico a las 5 copias** de `_decode.py` (ámbito,
  higyrus, iol, market-data, matriz; wallets exento por roster) y el bump de `CANONICAL_DIGEST`
  en `tools/check_decode_intactness.py:222` es mecánico: correr el gate, pegar el digest impreso,
  explicar el porqué en el commit. **Los comentarios dentro de `_decode.py` se hashean** — todo
  comentario nuevo debe ser byte-idéntico en las 5 copias; los docstrings de módulo NO se hashean,
  así que la documentación de la nueva disposición en docstrings debe revisarse a mano en las 5.
- **D-11:** Los otros 3 gates no se tocan: `check_surface_types` exime dunders (`__bool__`) y
  `empty() -> Self` es anotación concreta; `check_uniform_structure` es filesystem-only;
  `surface_parity` no mira `models.py`. Ninguna regla se afloja, ningún lower bound baja.
- **D-12:** Byte-identidad de snapshots de superficie: el formato
  (`verification/test_public_surface.py:104-122`) solo registra `nombre : kind : signature(__init__)`
  — agregar métodos a una base no lo mueve. Como `verification/` no corre en CI, la byte-identidad
  se aserta con `git diff` sobre `verification/snapshots/` (4 archivos) en la verificación del
  plan, no confiando en un leg verde.

### Tests — relectura del criterio 4 y falsificación (criterio 2)

- **D-13:** El criterio 4 "sin editar un solo test" se **rescopea a tests de superficie
  pública/comportamiento**: hay 10 aserciones (2 tests × 5 paquetes:
  `test_missing_list_field_returns_empty_list_and_reports` y el test WR-02
  `test_absent_nested_model_key_is_missing_on_the_outer_model`) que pinean exactamente el record
  que NOBJ-02 deja de emitir — son lógicamente contradictorias con la nueva disposición sobre el
  mismo input. Su **inversión deliberada y documentada es la evidencia de falsificación** que pide
  el criterio 2 (ambas mitades: colapso sin registro + wrong-type sigue divergiendo, cada una con
  test que enrojece si se invierte la disposición). Cualquier otra edición de tests fuera de esas
  y de los tests nuevos queda prohibida.
- **D-14:** Tests que deben seguir verdes sin editar: los `missing` de escalares
  (`.s`/`.i`/`.f`/`.b`), los `missing` de escalares dentro de elementos de lista
  (`.hojas[].dias`), `test_non_dict_returns_empty` / `test_none_payload_behaves_as_non_dict`
  (non_dict top-level, D-03a), `test_strict_mode_raises_on_a_missing_mapping_field` (eje mapping,
  D-03c) y `test_strict_mode_does_not_make_empty_fatal`.
- **D-15:** El chequeo de veracidad del criterio 1 se hace **por enumeración de las clases reales**
  de cada paquete (introspección de `models.py`), nunca sobre fixtures — y cubre las 4 jerarquías
  más `UnknownFrame`.
- **D-16:** El test del criterio 5 (invisibilidad de properties para el walker) pinea un hecho
  **ya verdadero** (probado: `get_type_hints()` no ve `@property`, incluso con `slots=True`) y se
  escribe sobre una dataclass con la forma exacta de los alias de las fases 36-38 (frozen, slots,
  `@property last` junto a campos wire), asertando que `get_type_hints()` devuelve exactamente los
  campos declarados y que el conteo de divergencias no cambia.

### Contabilidad para Phase 39

- **D-17:** La fase deja **registrado qué triples del censo retira la nueva política** (35 campos
  modelo/lista no-opcionales en el blast radius: higyrus 11, iol 0, market-data 8, matriz 16;
  incluye `Movimiento.idMovimientos` y `Posicion.parking` del piso ratificado `≥22` de higyrus en
  `29-SIZING.md:302-304`), para que la Phase 39 pueda **restar en vez de descubrir** y la baja de
  números no se lea como falso limpio (criterio 4 de la Phase 39).

### Claude's Discretion

- Redacción exacta de los docstrings de la nueva disposición (mismo contenido en las 5 copias,
  revisión manual porque no están hasheados).
- Dónde viven los tests nuevos de veracidad/enumeración (archivo nuevo por paquete vs. extender
  `test_decode.py`/`test_models.py` existentes), respetando convenciones de nombre del repo.
- Forma exacta del artefacto de D-17 (sección en VERIFICATION vs. archivo propio).

### Folded Todos

Ninguno — `todo.match-phase 35` devolvió 0 matches.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.future_plans/api-tipada-null-objects.md` — plan fuente, principios D-NO-01..D-NO-06 (D-NO-04
  define `__bool__`; D-NO-06 exige verbatim en las copias del walker). Nota: su línea "matriz,
  market-data; evaluar adopción en el resto" está **stale** — las 5 copias de `_decode.py` ya
  existen desde la Phase 29.
- `.planning/milestones/v1.6-phases/29-decoder-observable/29-SEMANTICS-MATRIX.md` — tabla 6-way de
  semánticas por paquete + regla "Never harmonize" sobre celdas de `DecodePolicy`.
- `.planning/milestones/v1.6-phases/29-decoder-observable/29-SIZING.md` — pisos ratificados del
  censo (composición del `≥22` de higyrus en `:302-304`), insumo de D-17.
- `tools/check_decode_intactness.py` — reglas de normalización (`:402-469`), `CANONICAL_DIGEST`
  (`:222`), roster de exención de wallets (`:188-206`).
- `tools/check_surface_types.py`, `tools/check_uniform_structure.py`, `tools/surface_parity.py` —
  los otros 3 gates (no se tocan, D-11).
- `verification/test_public_surface.py` + `verification/snapshots/` — formato y ubicación de los
  snapshots de superficie (D-12).
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `matriz_client.models._SafeModel.empty()` (`models.py:238-250`) — la implementación de
  referencia de `empty()` con mapping pass; las otras 3 bases derivan de su forma.
- `SILENT_SINK` + `walk_model(cls, {}, ...)` — mecanismo existente para sintetizar instancias
  vacías sin emitir registros (ya usado por el sitio de modelo del walker en `:482-484`).
- `_kind_of` (`_decode.py:363-367`) — discriminador missing-vs-type ya existente que hace gratis
  la mitad wrong-type del criterio 2 en el sitio de lista.

### Established Patterns

- **Verbatim × 5:** todo cambio a `_decode.py` se replica byte-idéntico en las 5 copias; el gate
  de intactness normaliza (8 reglas) y exige 1 hash único == `CANONICAL_DIGEST`. Comentarios
  hasheados; docstrings no.
- **Dual sync/async:** esta fase toca `models.py` y `_decode.py` (compartidos por ambas
  superficies), así que no hay espejo `client.py`/`aio.py` que mantener — pero `surface_parity`
  corre igual en los hooks per-package.
- **Dataclasses frozen** → igualdad estructural gratis, que es lo que hace viable D-06.
- Los `models.py` de ámbito/wallets vacíos-por-decisión llevan docstring explicativo — patrón a
  respetar (no agregar bases muertas).

### Integration Points

- `_decode.py:442-445` (sitio lista) y `:482-484` (sitio modelo) — los 2 únicos puntos de edición
  del walker.
- `DecodeScope.__call__` (`:205-221`) — choke point de strict; no se edita.
- Las 4 bases `SafeModel`/`_SafeModel` — ganan `__bool__` (verbatim) + `empty()` (2 formas).
- `matriz_client.models.UnknownFrame` (`:504-530`) — `__bool__` a mano (D-08).
- `tools/check_decode_intactness.py:222` — único gate que se mueve (bump de digest).
- Deuda conocida sin impacto: `check_decode_intactness.py:139` cita la ruta pre-archivo
  `.planning/phases/29-decoder-observable/29-WALLETS-EXEMPTION.md` (string stale, se imprime pero
  no se chequea existencia — el gate queda verde; no es de esta fase arreglarlo).

### Blast radius medido

- 52 clases `SafeModel` en 4 paquetes (higyrus 15, iol 4, market-data 16, matriz 17).
- 35 campos modelo/lista no-opcionales afectados por la nueva disposición (higyrus 11, iol 0,
  market-data 8, matriz 16).
- 10 aserciones de test a invertir (D-13); ningún call-site de truthiness sobre modelos existe hoy
  en los `client.py`/`aio.py`/`ws_client.py` (grep limpio), así que `__bool__` no tiene efecto
  latente dentro de los paquetes.
</code_context>

<specifics>
## Specific Ideas

- El test del criterio 5 debe tener la forma exacta de los alias de 36-38 (frozen + slots +
  `@property` junto a campos wire), no una clase sintética arbitraria (D-16).
- La inversión de los 10 tests es evidencia, no daño colateral: cada mitad del criterio 2 queda
  con un test que enrojece si se invierte la disposición (falsificación en ambas direcciones).
</specifics>

<deferred>
## Deferred Ideas

- Corregir la ruta stale `check_decode_intactness.py:139` (cita `.planning/phases/29-…` ya
  archivada) — cosmético, gate verde; candidato a quick-fix fuera de fase.
- Propiedades alias (`last`, `bids`, …) — Phases 36-38 por diseño.
- Eliminación de `_mapping_value`/`_apply_mapping_policy` en market-data — Phase 36 (criterio 5 de
  esa fase exige hacerlo sin mover el hash del walker; coherente con D-03c).

### Reviewed Todos (not folded)

Ninguno — no hubo matches de todos para esta fase.
</deferred>
