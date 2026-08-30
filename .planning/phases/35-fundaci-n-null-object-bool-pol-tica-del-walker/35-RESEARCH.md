# Phase 35: Fundación Null Object — `__bool__` + política del walker - Research

**Researched:** 2026-08-28
**Domain:** Python 3.12 dataclass semantics + a hand-rolled type-hint-driven decoder replicated verbatim across 5 packages, under 4 machine gates
**Confidence:** HIGH — every load-bearing claim below was **executed** in this session against the real repo (patch → measure → revert), not inferred.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Mecanismo del walker (NOBJ-02)

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

#### Superficie de las bases SafeModel (NOBJ-01)

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

#### Gates, hash canónico y snapshots (criterios 3-4)

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

#### Tests — relectura del criterio 4 y falsificación (criterio 2)

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

#### Contabilidad para Phase 39

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

### Deferred Ideas (OUT OF SCOPE)

- Corregir la ruta stale `check_decode_intactness.py:139` (cita `.planning/phases/29-…` ya
  archivada) — cosmético, gate verde; candidato a quick-fix fuera de fase.
- Propiedades alias (`last`, `bids`, …) — Phases 36-38 por diseño.
- Eliminación de `_mapping_value`/`_apply_mapping_policy` en market-data — Phase 36.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| NOBJ-01 | Toda instancia vacía de un `SafeModel` es falsy (`bool(X.from_api(None)) is False`) y una instancia con al menos un campo no-default es truthy, en los 6 paquetes (copia verbatim de la base + `empty()` garantizado en todas las jerarquías, incl. `_SafeModel` de matriz) | §Findings F-1 (52/52 clases verificadas en vivo, 0 mismatches), F-2 (`empty()` en 2 formas compila y no emite), F-3 (perturbación genérica necesaria para las 18 clases sin campo escalar), §Code Examples 1-3 |
| NOBJ-02 | El walker `_decode` colapsa `null`/ausente sobre un campo modelo/lista **no-opcional** a instancia vacía/`[]` sin emitir divergencia; wrong-typed sigue emitiendo divergencia y sigue fatal bajo `strict_decode`; los 4 gates de CI de v1.6 siguen verdes tras la actualización verbatim | §Findings F-4 (edit de 2 sitios ejecutado, red set medido = 11), F-5 (los 4 gates corridos bajo el parche: solo Check A rojo), F-6 (digest nuevo), §Code Examples 4-5, §Pitfall 1 (no existe hoy test wrong-type para el sitio de lista — hay que escribirlo) |
</phase_requirements>

---

## Summary

Esta fase no tiene incógnitas técnicas de librería: no se instala nada, no hay API externa que
consultar, y todo el "estado del arte" relevante es el propio repo. Lo que sí tenía incógnitas —
**cuál es exactamente el radio de explosión de tests, si el cambio compila bajo mypy strict, qué
hacen los 4 gates, y si los snapshots se mueven** — fue **medido ejecutándolo**: se aplicó el
cambio completo (walker × 5 + `__bool__` × 4 bases + `empty()` × 3 + `UnknownFrame`), se corrió la
suite entera de `packages/`, los 4 gates, `ruff check`, `ruff format --check`, `mypy` (global +
market-data explícito) y la regeneración de snapshots; después se revirtió con `git checkout` y el
árbol quedó limpio.

**Los resultados corrigen dos afirmaciones del CONTEXT.** Primero: el red set no es de **10**
aserciones sino de **11** — existe un onceavo test, `market-data-client/tests/test_core.py::test_health_from_api_missing_auth_yields_zero_valued_nested_model`
(`:1052-1059`), que pinea exactamente el record que NOBJ-02 deja de emitir, pero sobre un **modelo
real** (`Health.auth`) en vez de un fixture del walker. Es de la misma especie lógica que los otros
10 y su inversión es igual de legítima bajo D-13, pero el plan tiene que nombrarlo o el ejecutor se
va a encontrar con un rojo "prohibido" y va a parar. Segundo: la cifra de perf de D-06 (~2,6 µs)
viene de una clase sintética plana; sobre modelos anidados reales el costo medido es **11,2 µs**
(`higyrus.Posicion`) a **18,8 µs** (`matriz.MarketDataFrame`) por `bool()`, porque `__bool__`
reconstruye el árbol vacío entero en cada llamada. No es un bloqueante, pero sí un dato que el
docstring debería llevar y que prohíbe memoizar `empty()` a la ligera (§Pitfall 4).

Todo lo demás salió confirmado y verde: 1749 tests pasan con los 11 rojos esperados y **ningún
rojo extra**; `ruff` y `mypy --strict` limpios; `check_uniform_structure`, `check_surface_types` y
`surface_parity` verdes sin tocar una regla; `check_decode_intactness` falla **solo** en Check A
(B, C y D siguen verdes) y pide exactamente el bump de digest que D-10 anticipa; y los 4 snapshots
de `verification/snapshots/` se regeneran **byte-idénticos**.

**Primary recommendation:** planificar en 3 olas estrictamente secuenciales — (0) tests nuevos en
rojo + artefacto de censo, (1) las 4 bases `models.py` (paralelizable por paquete, no toca el
hash), (2) el walker × 5 + bump de digest + inversión de las 11 aserciones (un solo commit atómico,
porque cualquier estado intermedio deja `check_decode_intactness` rojo). El digest **no** se
predice: se recomputa corriendo el gate al final de la ola 2.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Truthiness de un modelo (`__bool__`) | Base `SafeModel` / `_SafeModel` en `models.py` | — | Es semántica del **modelo**, no del decoder; el walker nunca llama a `bool()` sobre lo que construye. |
| Construcción de la instancia vacía (`empty()`) | Base en `models.py` | Walker (`walk_model` con `SILENT_SINK`) | La base define la política de paquete (mapping pass o no); el walker aporta el mecanismo de sintetizar kwargs sin emitir. |
| Disposición de `null` sobre eslabón no-opcional | Walker `_decode.walk_field` | — | Es una decisión sobre el **canal de divergencias**, y el canal vive entero en el walker. Ponerla en `models.py` la haría por-paquete, que es lo contrario de lo que pide la copia verbatim. |
| Raise bajo `strict_decode` | `DecodeScope.__call__` (`_decode.py:205-221`) | — | Choke point único ya existente. Se hereda gratis: no llamar al sink ⇒ no raise. **No se edita.** |
| Discriminación missing-vs-wrong-type | `_kind_of` (`_decode.py:363-367`) | — | Ya existe; el sitio de lista lo usa hoy y lo va a seguir usando (o su equivalente literal `"type"`). |
| Eje mapping (`dict[str, Any]`) | `models.py` (`_mapping_value` / `_apply_mapping_policy`) | — | Fuera del walker por diseño (D-03c). Phase 36 lo elimina. |
| Contabilidad de triples retirados | Artefacto de planning en `.planning/phases/35-…/` | — | No es código; es insumo de la Phase 39. |
| Invariante de invisibilidad de `@property` | Suite de tests (`get_type_hints`) | — | Pinea un hecho de CPython/typing, no código propio. |

---

## Standard Stack

### Core

Esta fase **no instala nada**. Todo lo que usa ya está en `uv.lock` y fue ejercitado en esta
sesión.

| Herramienta | Versión medida | Propósito en esta fase | Por qué es la estándar acá |
|---|---|---|---|
| CPython | 3.12.11 (venv activo), matriz CI 3.12 + 3.13 | Runtime | `[VERIFIED: uv run python -V]` — `pyproject.toml` fija `target-version = "py312"`. |
| `uv` | 0.9.0 | Runner de todo (`uv run --frozen …`) | `[VERIFIED: uv --version]` — workspace monorepo. |
| `pytest` | 8.x + `pytest-asyncio` (`asyncio_mode = "auto"`) + `pytest-httpx` | Suites por paquete | `[VERIFIED: uv run pytest]` — 1749 tests en `packages/` corren en 94 s. |
| `ruff` | 0.7+ | lint + format; **también es parte de la normalización del gate** (Rule 8 de `check_decode_intactness`) | `[VERIFIED: uv run ruff check/format --check]` — 0 hallazgos con el cambio aplicado. |
| `mypy` | 1.13+, `strict = true` | Typecheck | `[VERIFIED: uv run mypy → Success: no issues found in 75 source files]` |
| `dataclasses` (stdlib) | — | Igualdad estructural que hace viable `__bool__` | `[CITED: docs.python.org/3/library/dataclasses.html]` — `eq=True` genera `__eq__`; `frozen=True` mantiene `__hash__`. |
| `typing.get_type_hints` (stdlib) | — | Motor del walker; **base del criterio 5** | `[VERIFIED: probe en esta sesión]` — no devuelve `@property`, ni con `slots=True`. |

### Supporting

| Artefacto del repo | Ubicación | Cuándo se usa |
|---|---|---|
| `tools/check_decode_intactness.py` | raíz | Única fuente del digest nuevo. Correr **después** del último byte editado en las 5 copias. |
| `verification/regen_snapshots.py` | raíz | Regenera los 4 snapshots. **No tiene flag `--check`**: el check es `git diff --exit-code verification/snapshots/` después de correrlo. |
| `verification/safemodel_diff.py` | raíz | Helper duck-typed cross-paquete `(is type, is_dataclass, callable from_api)` — **patrón a copiar** para el test de enumeración de D-15. |

### Alternatives Considered

| En vez de | Se podría usar | Tradeoff |
|---|---|---|
| `self != type(self).empty()` | `dataclasses.astuple(self) == astuple(empty)` | `astuple` recursa y falla sobre campos `dict`/`list` mutables de matriz; `__eq__` de dataclass ya hace lo correcto y es lo que D-06 lockea. |
| `self != type(self).empty()` | `any(getattr(self, f.name) for f in fields(self))` | Semántica distinta: `active=False` y `price=0.0` son campos *poblados* pero falsy — daría falsos negativos. **Rechazado.** |
| `empty()` memoizado con `lru_cache` | — | Ver §Pitfall 4: las clases de matriz llevan `dict`/`list` mutables; un singleton cacheado sería estado compartido mutable. **Prohibido en esta fase.** |
| Silenciar el sitio de lista con `_kind_of(value) != "missing"` | Gatear con `value is not None` | Equivalentes (`_kind_of` retorna `"missing"` sii `value is None`). El literal `"type"` en la llamada resultante es más legible y ya es lo que el record diría. Ambas pasan ruff/mypy — es discreción del planner, pero **la forma elegida cambia el digest**, así que hay que fijarla en el plan. |

**Installation:** ninguna. `uv sync --all-packages --all-extras --dev --frozen` ya cubre todo.

---

## Package Legitimacy Audit

**No aplica.** Esta fase no agrega ninguna dependencia externa en ningún ecosistema.
`[VERIFIED: el diff completo del probe tocó solo 9 archivos bajo packages/, ningún pyproject.toml, ningún uv.lock]`

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

---

## Project Constraints (from CLAUDE.md)

| Directiva | Aplicación en esta fase |
|---|---|
| **mypy strict** (`disallow_untyped_defs`, `warn_return_any`) | `__bool__` necesita `-> bool` explícito; `empty()` necesita `-> Self`. `[VERIFIED: mypy limpio con ambas anotaciones]` |
| **ruff**: line-length 100, comillas dobles, 4 espacios, reglas E/W/F/I/B/UP/SIM/RUF/ASYNC/PIE/PT/RET/TID | `[VERIFIED: ruff check + format --check limpios con el cambio aplicado]` |
| **`from __future__ import annotations` obligatorio en todo módulo** | Ya presente en los 4 `models.py` y las 5 copias de `_decode.py`. No agregar módulos sin él. |
| **Sin imports relativos, sin wildcard** (TID) | El test de enumeración debe importar `higyrus_client.models` absoluto. |
| **Sin código compartido entre paquetes** | El test de enumeración se **copia** por paquete; **prohibido** un helper compartido importado cross-package. Es la misma restricción que `verification/safemodel_diff.py` documenta explícitamente. |
| **Dual sync/async espejado** | Esta fase toca solo `models.py` y `_decode.py`, compartidos por ambas superficies. **No hay espejo `client.py`/`aio.py` que mantener** — pero `surface_parity` corre igual y quedó verde. |
| **Docstring de módulo obligatorio** con propósito + ejemplos | Si el planner crea archivos de test nuevos, cada uno necesita su docstring de módulo. |
| **Nunca commitear `.env` ni exponer credenciales** | Sin impacto: esta fase no toca transporte ni auth. |
| **GSD workflow: no editar fuera de un comando GSD** | El probe de esta investigación se revirtió íntegramente (`git status` limpio). Toda edición real va por `/gsd-execute-phase`. |

---

## Architecture Patterns

### System Architecture Diagram

```text
                       payload (dict | list | None | scalar)
                                    │
                                    ▼
              ┌──────────── walk_model(cls, payload) ────────────┐
              │  payload no-dict? ──► sink(non_dict)  [D-03a: INTACTO]
              │  payload dict?    ──► extras sorted ► sink(extra)
              └──────────────────────┬──────────────────────────┘
                                     │  por campo declarado
                                     ▼
                          walk_field(value, hint)
                                     │
        ┌────────────────────────────┼────────────────────────────┐
        ▼                            ▼                            ▼
  Union / Optional            origin is list               _is_model(hint)
  (:434-440)                  (:442-445)                   (:454-487)
  value None ─► return None   ┌──────────────┐             ┌──────────────┐
  NO es divergencia           │ no es list?  │             │ value None?  │
  ── RETORNO TEMPRANO ──      │  None ─►[]   │◄─ EDIT 1    │  ─► empty()  │◄─ EDIT 2
  (por eso todo lo de         │      SILENCIO│             │      SILENCIO│
   abajo es no-opcional       │  otro ─►[]   │             ├──────────────┤
   por construcción)          │      sink(type)            │ no-dict real │
                              └──────┬───────┘             │  ─► walk_model
                                     │ es list             │    ─► sink(non_dict)
                                     ▼                     └──────┬───────┘
                        walk_field(item, inner) ──────────────────┘
                        path = f"{path}[]"   (D-04: un None de elemento
                                              cae en EDIT 2 y se silencia)
        ▼
  escalares str/bool/int/float/Literal  (:489-534)  ── TODOS INTACTOS ──
                                     │
                                     ▼
                       sink = DecodeScope.__call__ (:205-221)
                       ┌──────────────────────────────────┐
                       │ triple ya visto? ─► return       │
                       │ strict && kind ∉ INFO ─► RAISE   │◄── el ÚNICO raise
                       │ _emit(record de 6 claves)        │
                       └──────────────────────────────────┘
                                     │
                                     ▼
                        logger `<pkg>` (WARNING / INFO)
```

Los dos rombos marcados `EDIT 1` / `EDIT 2` son **los únicos puntos que esta fase toca en el
walker**. Todo lo demás del diagrama es invariante.

### Recommended Project Structure

No se crean directorios. Los archivos que se tocan o crean:

```
packages/<pkg>/src/<pkg>/_decode.py      # EDIT ×5 (verbatim, hasheado)
packages/<pkg>/src/<pkg>/models.py       # EDIT ×4 (higyrus, iol, market-data, matriz)
packages/<pkg>/tests/test_decode.py      # EDIT ×5 (2 aserciones invertidas) + tests nuevos
packages/market-data-client/tests/test_core.py  # EDIT ×1 (la 11ª aserción — §Finding F-4b)
packages/<pkg>/tests/test_null_object.py # NUEVO ×6 (o extender existentes — discreción)
tools/check_decode_intactness.py         # EDIT ×1 (CANONICAL_DIGEST:222)
.planning/phases/35-…/35-RETIRED-TRIPLES.md  # NUEVO (artefacto D-17)
```

### Pattern 1: Verbatim × 5 con hash pinneado

**What:** las 5 copias de `_decode.py` se normalizan con 8 reglas y deben colapsar a **un** hash,
que además debe igualar `CANONICAL_DIGEST`.
**When to use:** todo edit a `_decode.py`.
**Mecánica medida** `[VERIFIED: lectura de tools/check_decode_intactness.py:402-516 + ejecución]`:

- **Rule 1** descarta el **docstring de módulo** — es la única parte no hasheada.
- **Rules 2-6** reemplazan por placeholders: `POLICY = …`, el import y el nombre de la excepción
  de decode, `_LOGGER_NAME`, los 2 nombres literales de `ContextVar`, y **toda ocurrencia del
  nombre de import del paquete** (`higyrus_client` → `__PKG__`).
- **Rule 7** rstrip por línea + newline final normalizado.
- **Rule 8** `ruff format` sobre el texto normalizado ⇒ **el layout no afecta el hash**, pero
  `ruff format --check` sobre el archivo real sí es un gate aparte.
- **Consecuencia crítica no dicha en CONTEXT:** los **docstrings de función y de clase SÍ se
  hashean** (solo el de módulo se descarta). Documentar la nueva disposición dentro del docstring
  de `walk_field` es por lo tanto **más seguro** que hacerlo en el docstring de módulo: el gate lo
  vuelve byte-idéntico por construcción, mientras que el de módulo queda a revisión humana × 5.

**Procedimiento (derivado de la ejecución de esta sesión):**

```bash
# 1. aplicar el MISMO texto a las 5 copias (script, no edición manual × 5)
# 2. formato y tipos
uv run ruff format packages/ && uv run ruff check packages/ && uv run mypy
uv run mypy packages/market-data-client/src        # market-data NO está en el `files` global
# 3. leer el digest nuevo del mensaje de error del gate
uv run python tools/check_decode_intactness.py     # imprime `computed: <sha256>`
# 4. pegar ese valor en tools/check_decode_intactness.py:222 y re-correr hasta verde
```

**Nota de línea/offset:** las 5 copias **no** comparten numeración. Ámbito está desplazado +7
respecto de las otras cuatro (docstring de módulo más largo). Sitios reales medidos:

| Paquete | `if origin is list:` | sink del sitio de lista | `if _is_model(hint):` | sink del sitio de modelo |
|---|---|---|---|---|
| ambito-financiero | 449 | **451** | 461 | **490** |
| higyrus | 442 | **444** | 454 | **483** |
| iol | 444 | **446** | 456 | **485** |
| market-data | 442 | **444** | 454 | **483** |
| matriz | 442 | **444** | 454 | **483** |

`[VERIFIED: grep -n sobre las 5 copias, 2026-08-28]`. El sink de `:531`/`:538` es la rama
`Literal` — **no se toca**.

### Pattern 2: Base no-dataclass + subclases frozen dataclass

**What:** `SafeModel` / `_SafeModel` son clases **planas** (no dataclasses); cada modelo concreto
es `@dataclass(frozen=True, slots=True)` (higyrus/iol/market-data) o `@dataclass(frozen=True)`
sin slots (matriz).
**Por qué importa acá:**
- `@dataclass` **no** sobrescribe `__bool__`, así que el heredado de la base gana por MRO.
  `[VERIFIED: probe sobre 52 clases]`
- `slots=True` **recrea la clase**; los métodos heredados de la base siguen resolviendo por MRO
  sin problema. `[VERIFIED]`
- La base no es dataclass ⇒ `cls(**kwargs)` dentro de `empty()` necesita el mismo trato de
  mypy que ya usa `from_api` (que compila hoy). No hace falta `cast` nuevo. `[VERIFIED: mypy strict limpio]`

### Pattern 3: Falsificación en las dos direcciones (criterio 2)

El criterio pide que *invertir la disposición enrojezca un test* en **ambas** mitades. El estado
del arte del repo, medido:

| Mitad | Sitio | Test que la falsifica | Estado |
|---|---|---|---|
| Colapso **sin** registro (modelo) | `:483` | `test_absent_nested_model_key_is_missing_on_the_outer_model` ×5, **invertido** | existe, se edita |
| Colapso **sin** registro (lista) | `:444` | `test_missing_list_field_returns_empty_list_and_reports` ×5, **invertido** | existe, se edita |
| Colapso **sin** registro (modelo real) | `:483` | `test_health_from_api_missing_auth_yields_zero_valued_nested_model` (market-data), **invertido** | existe, se edita — **no estaba en el inventario del CONTEXT** |
| Wrong-type **sigue** divergiendo (modelo) | `:487` | `test_non_dict_nested_payload_keeps_the_nested_attribution` (higyrus `:1149`, análogos en los 5) | **ya existe y ya queda verde sin editar** |
| Wrong-type **sigue** divergiendo (lista) | `:444` | **NO EXISTE** | **hay que escribirlo ×5** |
| Wrong-type **sigue** fatal bajo strict (lista) | `:205-221` | **NO EXISTE** | **hay que escribirlo ×5** |

`[VERIFIED: grep exhaustivo de `hojas` en higyrus/tests/test_decode.py — ningún payload con `hojas` wrong-typed; y las suites quedaron verdes salvo los 11 rojos, confirmando que ningún test existente cubre ese caso]`

### Anti-Patterns to Avoid

- **Implementar `empty()` como `cls.from_api(None)`:** emite un record `non_dict` (viola T-29-33)
  en las 3 bases nuevas y **recursa infinito** en matriz por el early-return `empty_classmethod`
  (`models.py:223-228`). Prohibido por D-07.
- **Inventar un no-op compartido para que `empty()` sea byte-idéntico en las 4 bases:** dead code
  que la Phase 36 borra al eliminar `_apply_mapping_policy`. D-07 lo rechaza explícitamente.
- **"Armonizar" las 5 copias más allá del edit:** `29-SEMANTICS-MATRIX.md §Never harmonize` —
  cada diferencia entre filas es un eje de política declarado con cita `file:line`, no una
  inconsistencia. Un edit que "de paso" unifica algo es un break silencioso sobre wheels
  publicados.
- **Editar los tests para que pasen:** solo las **11** aserciones nombradas pueden invertirse.
  Cualquier otro rojo es señal de que el cambio salió del scope, no de que el test esté mal.
- **Bumpear `CANONICAL_DIGEST` a un valor predicho o copiado de este documento:** el digest es
  función del texto exacto, incluidos comentarios y docstrings de función. Se recomputa.
- **`if not value:` en vez de `if value is not None:` en el gate del sitio de lista:** `0`, `""`
  y `{}` son falsy y son wrong-type legítimos que deben seguir divergiendo.

---

## Don't Hand-Roll

| Problema | No construir | Usar en cambio | Por qué |
|---|---|---|---|
| Comparar instancia contra vacío | Un walk campo-a-campo propio | `__eq__` generado por `@dataclass` (`self != type(self).empty()`) | Ya recursa correctamente en modelos anidados, listas y dicts; `astuple` en cambio falla/duplica trabajo. D-06 lo lockea. |
| Sintetizar la instancia vacía | Un constructor de defaults nuevo | `walk_model(cls, {}, policy=POLICY, sink=SILENT_SINK)` | Es el mecanismo que el propio walker ya usa en `:484`; garantiza que `empty()` y el default de eslabón anidado sean **el mismo objeto por construcción**. |
| Silenciar la emisión durante `empty()` | Un flag/ContextVar nuevo | `SILENT_SINK` (`_decode.py:241`) | Ya existe, ya está exento de dedupe y de raise; agregar un eje sería un edit al cuerpo canónico. |
| Discriminar missing vs wrong-type | Un `isinstance` ad-hoc | `_kind_of` (`:363-367`) | Ya existe y ya es la fuente de verdad del `kind` en el record. |
| Enumerar las clases reales de un paquete | Una lista hardcodeada | `inspect.getmembers(mod, inspect.isclass)` filtrado por `issubclass(base)` + `is_dataclass` + `obj.__module__ == mod.__name__` | El filtro por `__module__` es indispensable: sin él, una clase re-exportada de otro módulo entra al censo. Patrón ya usado por `verification/safemodel_diff.py`. |
| Verificar byte-identidad de snapshots | Un test nuevo | `uv run python verification/regen_snapshots.py && git diff --exit-code verification/snapshots/` | Ya existe el regenerador; `verification/` no corre en CI, así que el check tiene que ser explícito en el plan (D-12). |
| Detectar drift de las 5 copias | Un diff manual | `tools/check_decode_intactness.py` | Normaliza con 8 reglas y además pinea el contenido revisado. Un diff manual pasa verde ante un edit uniforme incorrecto. |

**Key insight:** todo el andamiaje que esta fase necesita **ya fue construido por la Phase 29**.
El riesgo dominante no es de implementación sino de **scope creep dentro de un archivo hasheado**:
cualquier byte de más en `_decode.py` se propaga a 5 archivos y a un digest, y cualquier byte de
menos deja el gate rojo.

---

## Runtime State Inventory

Esta fase **no es** un rename/refactor/migración de datos, pero sí toca un artefacto con estado
persistido fuera del código (el digest) y varios artefactos generados. Inventario explícito:

| Categoría | Ítems encontrados | Acción requerida |
|---|---|---|
| Stored data | **Ninguno** — verificado: los paquetes no persisten modelos decodificados; el único cache on-disk del monorepo es el token de IOL (`_token_cache`), que no toca `models.py` ni `_decode.py`. | ninguna |
| Live service config | **Ninguno** — verificado: esta fase no toca transporte, base URLs ni credenciales. | ninguna |
| OS-registered state | **Ninguno** — verificado: no hay tareas programadas ni daemons registrados por el repo (el daemon thread de `ws_client` es in-process). | ninguna |
| Secrets/env vars | **Ninguno** — verificado: `grep` del diff del probe no tocó `.env`, `.env.example` ni ninguna lectura de env. | ninguna |
| Build artifacts / estado derivado | (a) `CANONICAL_DIGEST` en `tools/check_decode_intactness.py:222` — **valor derivado del código, se invalida con el edit**; (b) `verification/snapshots/*.txt` (4 archivos) — derivados de `__all__` + firmas; (c) `__pycache__` en `tools/` y `packages/*/tests/` | (a) **bump obligatorio**, valor recomputado; (b) **verificado byte-idéntico** tras regenerar `[VERIFIED: git diff --stat verification/ vacío]` — regenerar igual como evidencia; (c) sin acción (gitignored) |

---

## Common Pitfalls

### Pitfall 1: El inventario de tests a invertir está incompleto en CONTEXT (10 vs 11)

**Qué sale mal:** el ejecutor aplica el edit, corre la suite, ve 11 rojos, encuentra uno que D-13
no autoriza a editar (`test_health_from_api_missing_auth_yields_zero_valued_nested_model`) y para
—o peor, lo "arregla" cambiando el comportamiento en vez de la aserción.
**Por qué pasa:** el inventario del CONTEXT se armó buscando los **fixtures del walker** (`test_decode.py`),
y este onceavo vive en `test_core.py` sobre un **modelo real** (`Health.auth: HealthAuth`, un campo
modelo no-opcional del roster de los 35).
**Cómo evitarlo:** nombrarlo en el plan junto a los otros 10, con la misma justificación de D-13.
Su aserción actual es:
```python
assert [(r.field_path, r.divergence) for r in records] == [(".auth", "missing")]
```
y su forma invertida es `== []`, con el `assert health.auth == HealthAuth(configured=False, enabled=False, issuer="")`
intacto (el **valor** no cambia — es exactamente el punto de NOBJ-02).
**Señal temprana:** el conteo. Si la suite de `packages/` da algo distinto de **11 failed / 1749
passed**, el cambio salió del scope.
`[VERIFIED: uv run pytest packages -q → 11 failed, 1749 passed, 1 deselected in 93.70s]`

### Pitfall 2: Las 5 copias del test WR-02 **no** son verbatim entre sí

**Qué sale mal:** el ejecutor escribe un script de sed para invertir las 10 aserciones y falla en
matriz/market-data.
**Por qué pasa:** los `_decode.py` son verbatim, los **tests no lo son**. La versión de matriz usa
otros fixtures y otra forma de aserción:
```python
# matriz-client/tests/test_decode.py:~1251
assert instance.leaf == _Leaf.empty()
assert ("_Nested", ".leaf", "missing") in triples      # ← `in`, no `==`
```
mientras higyrus usa `assert triples == [("_CarriesNested", ".hoja", "missing")]`.
**Cómo evitarlo:** editar las 11 aserciones **una por una**, leyendo cada una. Ubicaciones medidas:

| Paquete | `test_missing_list_field_…` | `test_absent_nested_model_key_…` |
|---|---|---|
| higyrus | `tests/test_decode.py:215` | `tests/test_decode.py:1131` |
| iol | `:308` | `:1202` |
| market-data | `:240` | `:1466` |
| matriz | `:335` | `:1234` |
| ambito-financiero | `:354` | `:1272` |
| market-data (11ª) | — | `tests/test_core.py:1052` |

`[VERIFIED: grep -n en los 6 archivos]`

### Pitfall 3: 18 de las 52 clases no tienen ningún campo escalar que perturbar

**Qué sale mal:** el test de enumeración de D-15 hace `dataclasses.replace(empty, primer_campo_str="X")`
y explota (o queda vacuo) en las 17 clases de matriz y en `higyrus.Administrador`, porque su
`empty()` tiene **todos** los campos en `None` (matriz declara casi todo `Optional` con default) o
en instancias anidadas (`Administrador` = 3 modelos anidados, cero escalares).
**Cómo evitarlo:** el helper de perturbación tiene que cubrir `None` primero:
```python
def _perturb(empty):
    for f in dataclasses.fields(empty):
        cur = getattr(empty, f.name)
        if cur is None:                       # ← indispensable para matriz + Administrador
            return dataclasses.replace(empty, **{f.name: "SENTINEL"})
        if isinstance(cur, str):   return dataclasses.replace(empty, **{f.name: "SENTINEL"})
        if isinstance(cur, bool):  return dataclasses.replace(empty, **{f.name: not cur})
        if isinstance(cur, int | float): return dataclasses.replace(empty, **{f.name: cur + 1})
        if isinstance(cur, list):  return dataclasses.replace(empty, **{f.name: ["SENTINEL"]})
        if isinstance(cur, dict):  return dataclasses.replace(empty, **{f.name: {"k": "v"}})
    raise AssertionError(f"no perturbable field on {type(empty).__name__}")
```
Con la rama `None` primero, **17/17 clases de matriz** dan `bool(perturbada) is True`.
`[VERIFIED: probe ejecutado — "matriz classes 17, perturb failures: []"]`
**Señal temprana:** un `AssertionError("no perturbable field …")` señala una clase que el test
estaría cubriendo vacuamente.

### Pitfall 4: `__bool__` reconstruye el árbol vacío en cada llamada — y memoizarlo es peor

**Qué sale mal (a):** se asume el ~2,6 µs de D-06 y se usa `bool(modelo)` dentro de un loop sobre
100 snapshots de `/marketdata`.
**Medición real** `[VERIFIED: probe con 2000 iteraciones]`:

| Clase | µs por `bool()` |
|---|---|
| `higyrus.Posicion` (2 niveles) | **11,19** |
| `matriz.MarketDataFrame` (3 niveles) | **18,82** |
| dataclass sintética plana (la que midió D-06) | 2,6 |

No es bloqueante para esta fase (nadie llama `bool()` sobre modelos hoy — grep limpio), pero sí
para las fases 36-38, donde `if snapshot.market_data.last:` pasa a ser el idioma. El docstring de
`__bool__` debería decir que el costo es proporcional al subárbol.

**Qué sale mal (b):** se "arregla" con `@lru_cache` / un singleton `_EMPTY` por clase. Varias
clases de matriz (`Order`, `AccountReport`, `InstrumentDetail`, `UnknownFrame`) llevan campos
`dict`/`list` con `default_factory`; cachear una instancia vacía la convierte en **estado mutable
compartido a nivel de proceso** — un caller que haga `empty().raw["k"] = 1` contamina a todos.
**Prohibido en esta fase.** Si hace falta, es trabajo de la Phase 36 con su propio análisis.

### Pitfall 5: `verification/` tarda >10 min y no corre en CI

**Qué sale mal:** el plan pone `uv run pytest` (sin path) como paso de verificación y el ejecutor
se cuelga.
**Por qué pasa:** `testpaths = ["packages", "tests", "verification"]`, y `verification/` incluye
tests de retry/backoff con sleeps reales. Corrida medida: **timeout a los 10 min sin terminar**.
Además `verification/` está **rojo de base** por deuda conocida (`HARN-VERIF-01`: 19 failed + 19
errors por firmas stale de `main_matriz.py`), así que un verde ahí no es alcanzable ni esperado.
**Cómo evitarlo:** los pasos de verificación del plan usan paths explícitos, igual que CI:
```bash
uv run pytest packages -q                 # 94 s, la suite que importa
uv run pytest tests -q                    # 2 tests, 0.01 s
uv run python verification/regen_snapshots.py && git diff --exit-code verification/snapshots/
```
`[VERIFIED: .github/workflows/ci.yml:128-135 pasa `packages/${{ matrix.package }}` explícito, lo que anula `testpaths`; `verification/` y `tests/` nunca corren en CI]`

### Pitfall 6: `mypy` global no cubre market-data

**Qué sale mal:** se corre `uv run mypy`, sale verde, y el error de tipos de `market_data_client/models.py`
aparece recién en pre-commit (o en ningún lado).
**Por qué pasa:** market-data está fuera del `files` de mypy del root (`pyproject.toml:97`, deuda
D-16 diferida desde la Phase 24). La cobertura real la da el hook de pre-commit scopeado
`files: ^packages/.*/src/`.
**Cómo evitarlo:** el plan corre **las dos**:
```bash
uv run mypy                                    # 75 archivos
uv run mypy packages/market-data-client/src    # 13 archivos
```
`[VERIFIED: ambas verdes con el cambio completo aplicado]`

### Pitfall 7: El commit del walker no puede quedar a medias

**Qué sale mal:** se commitea el edit de las 5 copias y el bump del digest en commits separados, o
se commitea 1 copia editada.
**Por qué pasa:** `check_decode_intactness` corre en el job `lint` de CI sobre **cada push**.
Cualquier estado intermedio (copias en desacuerdo, o copias de acuerdo con digest viejo) deja el
gate rojo.
**Cómo evitarlo:** las 5 copias + el bump del digest + la inversión de las 11 aserciones son **un
solo commit atómico**. El bump del digest sin el edit tampoco sirve (rojo por el lado inverso).

### Pitfall 8: `MarketDataSnapshot` de market-data hace ruido en el criterio 1

**Qué sale mal:** el test de enumeración asevera `bool(X.from_api(None)) is False` y pasa —
pero por accidente, y el lector concluye algo falso sobre la clase.
**Por qué pasa:** `MarketDataSnapshot.from_api(cls, payload, *, received_at: float = 0.0)` inyecta
`received_at` **post-walk**. Con el default `0.0` la igualdad con `empty()` se sostiene (por eso el
probe dio 0 mismatches), pero **el cliente real siempre pasa `time.time()`**, así que en producción
un snapshot es **siempre truthy** aunque venga vacío.
**Cómo evitarlo:** D-09 ya lo cubre — documentarlo en el docstring y hacer que el test de
truthiness a nivel *dominio* apunte al **campo** (`snapshot.market_data`), no al snapshot. El test
de enumeración puede seguir cubriendo la clase, pero con un comentario que diga por qué su verde
es estructural y no semántico.

---

## Code Examples

### 1. `__bool__` — cuerpo byte-verbatim para las 4 bases (D-06)

```python
    def __bool__(self) -> bool:
        """Null Object truthiness: an all-defaults instance is falsy (NOBJ-01)."""
        return self != type(self).empty()
```
`[VERIFIED: aplicado a las 4 bases + UnknownFrame; mypy strict y ruff limpios; 52/52 clases con bool(empty()) is False]`

Notas de tipos: `type(self)` es `type[Self]`, `empty()` retorna `Self`, y `!=` sobre `object`
está tipado `bool` en typeshed ⇒ **no dispara `warn_return_any`**. `self.empty()` sería
equivalente y más corto, pero `type(self).empty()` es la forma que D-06 lockea y la que deja claro
que la comparación es contra el vacío de la **clase concreta**, no de la base.

### 2. `empty()` — forma A (higyrus, iol) (D-07)

```python
    @classmethod
    def empty(cls) -> Self:
        """Build an all-defaults instance. Emits nothing (T-29-33)."""
        kwargs = _decode.walk_model(cls, {}, policy=_decode.POLICY, sink=_decode.SILENT_SINK)
        return cls(**kwargs)
```

### 3. `empty()` — forma B (market-data; matriz ya la tiene en `models.py:238-250`) (D-07)

```python
    @classmethod
    def empty(cls) -> Self:
        """Build an all-defaults instance. Emits nothing (T-29-33).

        Delta vs. higyrus/iol: this paquete's ``from_api`` carries a mapping pass
        (``_apply_mapping_policy``), so ``empty()`` must carry it too or the two
        constructors would disagree on any ``dict[str, Any]`` field.
        """
        kwargs = _decode.walk_model(cls, {}, policy=_decode.POLICY, sink=_decode.SILENT_SINK)
        _apply_mapping_policy(cls, kwargs, sink=_decode.SILENT_SINK)
        return cls(**kwargs)
```
`[VERIFIED: ambas formas ejecutadas; 0 records emitidos por empty() sobre las 52 clases; 0 mismatches contra from_api(None)]`

### 4. EDIT 1 — sitio de lista (`:444` en 4 copias, `:451` en ámbito)

```python
    if origin is list:
        if not isinstance(value, list):
            if value is not None:
                sink(model, path, "type", _name_of(hint), type(value).__name__)
            return []
```
Antes:
```python
    if origin is list:
        if not isinstance(value, list):
            sink(model, path, _kind_of(value), _name_of(hint), type(value).__name__)
            return []
```
`[VERIFIED: ruff check + ruff format --check limpios sobre esta forma; ninguna regla SIM se dispara]`

### 5. EDIT 2 — sitio de modelo (`:483` en 4 copias, `:490` en ámbito)

```python
        if value is None:
            return hint(**walk_model(hint, {}, path=path, policy=policy, sink=SILENT_SINK))
```
Antes:
```python
        if value is None:
            sink(model, path, "missing", _name_of(hint), "NoneType")
            return hint(**walk_model(hint, {}, path=path, policy=policy, sink=SILENT_SINK))
```
El bloque de comentario WR-02 que precede a estas líneas (`:458-481`) **debe reescribirse**: hoy
explica por qué se emite el `missing`, que es exactamente lo que deja de ser cierto. Al estar
hasheado, la reescritura tiene que ser byte-idéntica en las 5 copias — lo que es una ventaja, no
un costo.

### 6. Test de enumeración (criterio 1 / D-15) — esqueleto por paquete

```python
def _safemodel_classes() -> list[type]:
    """Every shipped SafeModel subclass of THIS paquete, by introspection."""
    return sorted(
        (
            obj
            for _, obj in inspect.getmembers(models, inspect.isclass)
            if issubclass(obj, models.SafeModel)
            and obj is not models.SafeModel
            and dataclasses.is_dataclass(obj)
            and obj.__module__ == models.__name__     # ← sin esto entran re-exports
        ),
        key=lambda c: c.__name__,
    )


@pytest.mark.parametrize("cls", _safemodel_classes(), ids=lambda c: c.__name__)
def test_every_shipped_model_is_falsy_when_empty(cls: type) -> None:
    assert bool(cls.from_api(None)) is False
    assert cls.from_api(None) == cls.empty()


@pytest.mark.parametrize("cls", _safemodel_classes(), ids=lambda c: c.__name__)
def test_every_shipped_model_is_truthy_when_populated(cls: type) -> None:
    assert bool(_perturb(cls.empty())) is True


def test_the_enumeration_is_not_vacuous() -> None:
    """A guard: an empty roster would make the two tests above pass vacuously."""
    assert len(_safemodel_classes()) >= 15      # higyrus: 15 / iol: 4 / md: 16 / matriz: 17
```

Conteos medidos para el guard anti-vacuo (`[VERIFIED: probe de enumeración]`): higyrus **15**,
iol **4**, market-data **16**, matriz **17** (más `UnknownFrame` fuera de la jerarquía) = **52**.
Para ámbito y wallets el roster es **0 por decisión** (D-05): ahí el test debe aseverar
explícitamente `models.py` sin base y sin subclases, con el motivo citado, en vez de un
`parametrize` vacío que pytest saltaría en silencio.

### 7. Test del criterio 5 — invisibilidad de `@property` para el walker (D-16)

```python
@dataclass(frozen=True, slots=True)
class _AliasShaped(SafeModel):
    """The exact shape phases 36-38 introduce: wire fields + a read-only alias."""

    LA: _Leaf
    BI: list[_Leaf]

    @property
    def last(self) -> _Leaf:
        return self.LA


def test_property_aliases_are_invisible_to_get_type_hints() -> None:
    hints = get_type_hints(_AliasShaped)
    assert set(hints) == {f.name for f in dataclasses.fields(_AliasShaped)}
    assert "last" not in hints


def test_adding_an_alias_cannot_change_the_divergence_count(caplog) -> None:
    _, records = _walk(_AliasShaped, {}, caplog)
    assert records == []          # bajo la nueva disposición: 2 eslabones no-opcionales, 0 records
```
`[VERIFIED: probado en esta sesión — get_type_hints(Outer) devolvió ['LA', 'rows'] y "last" not in hints, con slots=True]`

### 8. Los 3 comandos de verificación que el plan necesita

```bash
# gates (los 4, como los corre CI en el job `lint`)
uv run python tools/check_decode_intactness.py    # el único que se mueve
uv run python tools/check_uniform_structure.py
uv run python tools/check_surface_types.py
uv run python tools/surface_parity.py

# suites (paths explícitos, igual que CI)
uv run pytest packages -q                          # esperado: 1760 passed tras invertir las 11

# snapshots byte-idénticos (D-12) — verification/ NO corre en CI
uv run python verification/regen_snapshots.py && git diff --exit-code verification/snapshots/
```

---

## State of the Art

| Enfoque viejo | Enfoque actual | Cuándo cambió | Qué implica |
|---|---|---|---|
| `_coerce(value, hint)` por paquete dentro de `models.py` | Walker único `_decode.walk_field` / `walk_model`, verbatim × 5, con canal de divergencias de 6 claves | Phase 29 (v1.6, 2026-08) | El edit de NOBJ-02 es de **2 líneas × 5 archivos**, no de N implementaciones. |
| Ausencia expresada como `None` en el tipo | Ausencia expresada como veracidad (`__bool__`) + record de divergencia | **Esta fase** (D-NO-04) | La señal de ausencia se muda del sistema de tipos al canal de observabilidad + `bool()`. |
| El plan fuente decía "las copias del walker viven en matriz y market-data; evaluar adopción en el resto" | Las **5** copias ya existen desde la Phase 29 | Phase 29 | `.future_plans/api-tipada-null-objects.md` línea correspondiente está **stale**; el CONTEXT ya lo marca. |
| `check_decode_intactness` verificando solo acuerdo mutuo | Acuerdo mutuo **+** `CANONICAL_DIGEST` pinneado | Phase 29 code review WR-07 | Un edit uniforme incorrecto ya no pasa verde: hay que bumpear a mano y justificar en el commit. |

**Deprecado / no reutilizar:**
- `Model.from_api(None)` como forma de obtener el vacío dentro de `empty()` — ver D-07 y
  §Anti-Patterns.
- La cifra "~2,6 µs/call" de D-06 como estimación de costo de `bool()` sobre modelos reales — ver
  §Pitfall 4.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|---|---|---|
| A1 | El artefacto de D-17 debería ser un archivo propio `35-RETIRED-TRIPLES.md` en el directorio de la fase, con la 4-tupla `(slug, model, field_path, kind)` que usa `33-CENSUS.md` | §D-17 abajo | Bajo. Si la Phase 39 prefiere otra unidad, el contenido se re-proyecta; el conjunto de campos es el mismo. La forma es discreción del planner por CONTEXT. |
| A2 | La forma exacta del gate del sitio de lista (`if value is not None:` + literal `"type"`) es la que el plan va a fijar | §Code Examples 4 | Medio-bajo. Cualquier forma equivalente funciona, pero **cambia el digest**. Si el plan elige otra, el digest de §Findings F-6 no aplica y hay que recomputar (que es lo que el plan debe hacer igual). |
| A3 | Los 11 rojos son el conjunto completo también en Python 3.13 | §Pitfall 1 | Bajo. Todo lo medido corrió en CPython 3.12.11; nada del cambio depende de una diferencia 3.12/3.13. CI corre ambas — se descubriría en el primer push. |
| A4 | Ningún consumidor externo del monorepo depende hoy de que un `null` sobre eslabón no-opcional emita un record | §Summary | Medio. Es un cambio de comportamiento observable en el logger. Mitigación: es exactamente lo que NOBJ-02 pide, y la Phase 39 lo contrasta contra el censo (D-17). |
| A5 | `Health.auth` (el 11º test) es el único caso "modelo real" — no hay un 12º escondido en un test que hoy pase por otra razón | §Pitfall 1 | Bajo. Se corrió la suite **completa** de `packages/` con el cambio aplicado; 11 es el conjunto medido, no estimado. Riesgo residual solo si un test está marcado skip/xfail. |

---

## Open Questions

1. **¿La reescritura del bloque de comentario WR-02 (`_decode.py:458-481`) se conserva o se
   reemplaza?**
   - Lo que sabemos: el bloque explica por qué se emite el `missing` — la mitad que deja de ser
     verdad. Está hasheado, así que la reescritura es byte-idéntica × 5 por construcción.
   - Lo que no está claro: cuánto del razonamiento WR-02 sigue siendo load-bearing. La parte de
     "el VALOR retornado es la misma instancia all-defaults" **sigue siendo cierta y sigue siendo
     importante**; la parte de la atribución al modelo externo deja de aplicar.
   - Recomendación: conservar el bloque, reescribir el párrafo WR-02 final para declarar la
     **nueva** disposición y dejar la cita a `35`/NOBJ-02 al lado de la de WR-02, para que un
     lector futuro vea la historia completa. Es discreción del planner (CONTEXT lo lista).

2. **¿Los tests nuevos van en archivo propio o extienden `test_decode.py`/`test_models.py`?**
   - Lo que sabemos: el repo nombra por sujeto (`test_<subject>.py`) y `test_decode.py` ya tiene
     ~1150-1500 líneas por paquete.
   - Recomendación: **archivo nuevo `tests/test_null_object.py` por paquete** para los tests de
     veracidad/enumeración (criterio 1) y del criterio 5, porque son sobre `models.py`, no sobre
     el walker; y **dentro de `test_decode.py`** los 2 tests nuevos de wrong-type del sitio de
     lista, porque pertenecen a la sección "Divergence class 2 — wrong type" que ya existe ahí.
     Ámbito y wallets también reciben su `test_null_object.py`, con el assert de roster vacío
     documentado (D-05).

3. **¿Cuántos de los 35 campos del blast radius corresponden a triples del censo ya medido?**
   - Lo que sabemos: el roster de 35 está enumerado exactamente (§D-17 abajo). Los pisos
     ratificados están en `29-SIZING.md` y el censo medido en `33-CENSUS.md`
     (`.planning/milestones/v1.6-phases/33-…/`).
   - Lo que no está claro: la intersección exacta para matriz y market-data (higyrus **sí** está
     resuelta: exactamente 2 de sus 22 — `Movimiento.idMovimientos` y `Posicion.parking` — porque
     los 11 de `PosicionValuada` y `disponibleAjustado` son escalares).
   - Recomendación: es una tarea del plan (lectura + intersección), no de investigación. El plan
     debe producir la tabla completa, no estimarla.

---

## Environment Availability

| Dependencia | Requerida por | Disponible | Versión | Fallback |
|---|---|---|---|---|
| CPython 3.12 | Todo | ✓ | 3.12.11 (`.venv/`) | — |
| CPython 3.13 | Matriz de CI | ✗ localmente | — | CI lo cubre; nada del cambio es version-specific |
| `uv` | Runner | ✓ | 0.9.0 | — |
| `ruff` | lint + format + **normalización del gate** | ✓ | 0.7+ | ninguno — el gate lo invoca por subprocess (`check_decode_intactness.py:370-399`) |
| `mypy` | Typecheck strict | ✓ | 1.13+ | — |
| `pytest` + `pytest-asyncio` + `pytest-httpx` | Suites | ✓ | 8.x / 0.24+ / 0.34+ | — |
| `git` | Verificación de byte-identidad de snapshots (D-12) | ✓ | — | — |
| Red / APIs financieras en vivo | **NO requerida** | n/a | — | Esta fase es 100% offline: no hay driver `main_*.py` en scope. |

**Missing dependencies with no fallback:** ninguna.
**Missing dependencies with fallback:** CPython 3.13 local — cubierto por la matriz de CI.

---

## Validation Architecture

### Test Framework

| Property | Value |
|---|---|
| Framework | pytest 8.x (+ pytest-asyncio `asyncio_mode = "auto"`, pytest-httpx) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]:102-120` |
| Quick run command | `uv run pytest packages/<pkg> -q` (por paquete; higyrus+iol = 52 s) |
| Full suite command | `uv run pytest packages -q` (**94 s**, 1760 tests) — **nunca** `uv run pytest` sin path (§Pitfall 5) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|---|---|---|---|---|
| NOBJ-01 | `bool(X.from_api(None)) is False` para las 52 clases reales + `UnknownFrame` | unit (parametrizado por enumeración) | `uv run pytest packages -q -k test_every_shipped_model_is_falsy_when_empty` | ❌ Wave 0 |
| NOBJ-01 | `bool(instancia_perturbada) is True` | unit | `uv run pytest packages -q -k test_every_shipped_model_is_truthy_when_populated` | ❌ Wave 0 |
| NOBJ-01 | La enumeración no es vacua (roster ≥ N por paquete; 0 documentado en ámbito/wallets) | unit (guard) | `uv run pytest packages -q -k test_the_enumeration_is_not_vacuous` | ❌ Wave 0 |
| NOBJ-01 | `empty()` existe e invocable en las 4 bases y **no emite** nada | unit | `uv run pytest packages -q -k test_empty_emits_nothing` | ❌ Wave 0 |
| NOBJ-02 | `null`/ausente sobre lista no-opcional → `[]` **sin** record | unit (**inversión** ×5) | `uv run pytest packages -q -k test_missing_list_field_returns_empty_list_and_reports` | ✅ existe — se invierte |
| NOBJ-02 | `null`/ausente sobre modelo no-opcional → instancia vacía **sin** record | unit (**inversión** ×5 + 1) | `uv run pytest packages -q -k "test_absent_nested_model_key or test_health_from_api_missing_auth"` | ✅ existe — se invierte |
| NOBJ-02 | wrong-typed sobre **lista** sigue emitiendo record de 6 claves | unit (falsificación) | `uv run pytest packages -q -k test_wrong_typed_list_field_still_reports_type` | ❌ Wave 0 — **no existe hoy** |
| NOBJ-02 | wrong-typed sobre **lista** sigue fatal bajo `strict_decode` | unit (falsificación) | `uv run pytest packages -q -k test_strict_mode_still_raises_on_a_wrong_typed_list` | ❌ Wave 0 — **no existe hoy** |
| NOBJ-02 | wrong-typed sobre **modelo** sigue emitiendo `non_dict` | unit (falsificación) | `uv run pytest packages -q -k test_non_dict_nested_payload_keeps_the_nested_attribution` | ✅ existe — **queda verde sin editar** |
| NOBJ-02 | `non_dict` top-level sigue emitiéndose (D-03a) | unit (regresión) | `-k "test_none_payload_behaves_as_non_dict or test_non_dict_returns_empty"` | ✅ existe — verde sin editar |
| NOBJ-02 | Eje mapping intacto (D-03c) | unit (regresión) | `-k test_strict_mode_raises_on_a_missing_mapping_field` | ✅ existe — verde sin editar |
| NOBJ-02 | Los 4 gates verdes | gate | los 4 comandos de §Code Examples 8 | ✅ existen |
| criterio 4 | Snapshots byte-idénticos | gate | `uv run python verification/regen_snapshots.py && git diff --exit-code verification/snapshots/` | ✅ existe |
| criterio 5 | `get_type_hints()` no ve `@property` | unit | `-k test_property_aliases_are_invisible_to_get_type_hints` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest packages/<pkg> -q` del paquete tocado (≤ 30 s por paquete) +
  `uv run ruff check packages/ && uv run ruff format --check packages/`.
- **Per wave merge:** `uv run pytest packages -q` (94 s) + `uv run mypy` + `uv run mypy packages/market-data-client/src`.
- **Phase gate:** los 4 gates verdes + `pytest packages` verde + `git diff --exit-code verification/snapshots/`
  limpio, antes de `/gsd-verify-work`.

### Wave 0 Gaps

- [ ] `packages/{higyrus,iol,market-data,matriz,ambito-financiero,wallets}-client/tests/test_null_object.py` — cubre NOBJ-01 + criterio 5 (6 archivos nuevos)
- [ ] Helper `_perturb()` **copiado** por paquete (sin import cross-package) — ver §Pitfall 3
- [ ] 2 tests nuevos de wrong-type del sitio de lista, dentro de `tests/test_decode.py` ×5 — cubren la mitad de falsificación de NOBJ-02 que **hoy no tiene cobertura**
- [ ] Artefacto D-17 (`35-RETIRED-TRIPLES.md`) — no es test, pero es entregable de la fase
- [ ] Framework install: **ninguno** — pytest + plugins ya en `uv.lock`

---

## Security Domain

`security_enforcement: true`, `security_asvs_level: 1`.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---|---|---|
| V2 Authentication | no | Esta fase no toca auth, tokens ni credenciales. Diff medido: 0 archivos de auth. |
| V3 Session Management | no | Sin sesiones; el `ContextVar` de scope se mantiene sin cambios. |
| V4 Access Control | no | Librerías cliente; sin control de acceso propio. |
| V5 Input Validation | **sí** | El walker **es** la capa de validación de entrada del payload de terceros. Controles conservados: `_safe_key` (lock 11) neutraliza claves wire antes del record; `_MAX_KEY_LEN = 64`; `scalar_passthrough` por `DecodePolicy`; `strict_decode` como modo fatal. **Ninguno se toca.** |
| V6 Cryptography | no | Sin cripto. |
| V7 Error Handling & Logging | **sí** | El record de divergencia es un canal de log. Cambio: deja de emitirse un `WARNING` para una clase específica de entrada (null sobre eslabón no-opcional). Ver análisis abajo. |

### Known Threat Patterns for este stack

| Pattern | STRIDE | Standard Mitigation | Estado en esta fase |
|---|---|---|---|
| Log injection vía clave de payload hostil (`\n`, `.`) | Tampering | `_safe_key` + `_KEY_SAFE_RE` + truncado a 64 (`_decode.py:337-360`) | **Intacto** — la rama `extra` no se toca. |
| Log flooding: payload que fabrica N records por respuesta | DoS | Dedupe por triple en `DecodeScope._seen` + `SILENT_SINK` bajo `non_dict` (lock 8) | **Intacto**, y la nueva disposición **reduce** volumen (menos records por payload con nulls legítimos). |
| Excepción del handler de logging propagando al caller | DoS | `_emit` nunca levanta (lock 9) | **Intacto**. |
| **Reducción de observabilidad: un payload malformado pasa sin señal** | Repudiation / Tampering | `strict_decode` sigue fatal para wrong-type; el valor de retorno no cambia; `non_dict` top-level sigue emitiéndose | **Aceptado y acotado por diseño.** El silencio se aplica **solo** a `value is None` sobre un campo no-opcional de tipo modelo/lista — la clase de entrada que D-NO-01 declara legítima. Un `"abc"` donde va una lista, un `{}` donde va una lista, un `0` — todos siguen emitiendo y siguen siendo fatales bajo strict. Esto está **probado por falsificación** en ambas direcciones (criterio 2), y las 2 mitades wrong-type del sitio de lista son tests **nuevos** que esta fase debe escribir (§Pitfall 1 del mapa de tests). |
| Contaminación de estado compartido vía instancia vacía cacheada | Tampering | — | **Riesgo introducido si se memoiza `empty()`.** Prohibido en esta fase (§Pitfall 4b): las clases de matriz llevan `dict`/`list` mutables con `default_factory`. |

**Conclusión de seguridad:** el cambio **estrecha** la superficie de observabilidad de forma
deliberada, medida y falsificable, sin tocar ninguno de los 4 controles de entrada del walker
(`_safe_key`, límite de longitud, dedupe, `strict_decode`). No hay hallazgo de nivel `high`.

---

## Findings (measured this session)

> Todo lo de esta sección se obtuvo **ejecutando el cambio completo** contra el repo real
> (`git status` limpio antes y después). No es inferencia.

### F-1 — Las 4 bases + `UnknownFrame` con `__bool__`: 52/52 clases correctas

`[VERIFIED: probe de enumeración, 2026-08-28]`

```
higyrus: 15 clases · iol: 4 · market-data: 16 · matriz: 17   = 52
TOTAL classes probed: 52
FAILS: 0
```
Cubre: `empty()` no levanta, `from_api(None) == empty()`, `bool(empty()) is False`,
`bool(perturbada) is True`. Más `UnknownFrame`: `bool(empty()) is False` y
`bool(from_api({"type": "zz"})) is True`.

### F-2 — `empty()` no emite ningún record en ninguna de las 52 clases

`[VERIFIED: handler adjunto a los 4 loggers de paquete durante el barrido completo]`
```
records emitted by empty()/bool() across all classes: 0
```
Confirma T-29-33 para las 2 formas de `empty()` (con y sin mapping pass).

### F-3 — 18 clases no tienen campo escalar en su `empty()`

Las 17 de matriz (todo `Optional` con default) y `higyrus.Administrador` (3 campos, los 3
modelos anidados). Con el helper `_perturb` que trata `None` primero: **17/17 matriz OK**.
`[VERIFIED: "matriz classes 17, perturb failures: []"]`

### F-4 — Red set completo bajo el cambio: **11 failed / 1749 passed / 1 deselected** en 93,70 s

`[VERIFIED: uv run pytest packages -q, con walker + bases + UnknownFrame aplicados]`

**F-4a — los 10 previstos:**
```
ambito-financiero-client/tests/test_decode.py::test_missing_list_field_returns_empty_list_and_reports
ambito-financiero-client/tests/test_decode.py::test_absent_nested_model_key_is_missing_on_the_outer_model
higyrus-client/tests/test_decode.py::test_missing_list_field_returns_empty_list_and_reports
higyrus-client/tests/test_decode.py::test_absent_nested_model_key_is_missing_on_the_outer_model
iol-client/tests/test_decode.py::test_missing_list_field_returns_empty_list_and_reports
iol-client/tests/test_decode.py::test_absent_nested_model_key_is_missing_on_the_outer_model
market-data-client/tests/test_decode.py::test_missing_list_field_returns_empty_list_and_reports
market-data-client/tests/test_decode.py::test_absent_nested_model_key_is_missing_on_the_outer_model
matriz-client/tests/test_decode.py::test_missing_list_field_returns_empty_list_and_reports
matriz-client/tests/test_decode.py::test_absent_nested_model_key_is_missing_on_the_outer_model
```

**F-4b — el 11º, NO inventariado en CONTEXT:**
```
market-data-client/tests/test_core.py::test_health_from_api_missing_auth_yields_zero_valued_nested_model
```
`test_core.py:1052-1059`. Misma especie lógica; sobre modelo real (`Health.auth: HealthAuth`).

**F-4c — agregar `__bool__` + `empty()` no rompió NADA.** El red set con solo el walker parcheado
(medido por separado) fue idéntico: 11. Los métodos nuevos son aditivos puros.

### F-5 — Los 4 gates bajo el cambio completo

`[VERIFIED: ejecución de los 4]`

| Gate | Resultado | Detalle |
|---|---|---|
| `check_decode_intactness` | **ROJO solo Check A** | Checks B (`684191c7cdc5ff9c`, sin mover), C y D **verdes**. Check A pide el bump del digest, exactamente como D-10 anticipa. |
| `check_uniform_structure` | verde | "all 6 packages … carry `models.py`, `types.py`" |
| `check_surface_types` | verde | 6 paquetes, 180 nombres `__all__`, **324** definiciones escaneadas (319 antes), 23 exentas (dunder 13 — **sin cambio**), **0 violaciones**. `__bool__` cae en `_is_exempt` → `"dunder"` (`check_surface_types.py:390-403`); `empty() -> Self` no menciona `Any` y pasa el chequeo de anotación de retorno. |
| `surface_parity` | verde | sin salida, exit 0 |

### F-6 — Digest computado para **esta** forma exacta del edit

```
expected (CANONICAL_DIGEST): ac14868282ad0a5c6fb85ab7b7920068303a781835b9c76ca50f26283c1c3dc5
computed:                    cd937d179f454b50f4a3cf6abbf2b2ee3fcb193e14e57d1b50b1b790fb8dbd16
```
**No copiar `cd937d…` al plan.** Ese valor corresponde al edit **sin** reescritura del bloque de
comentario WR-02 y con la forma `if value is not None:` + literal `"type"`. Cualquier byte
distinto en comentarios o docstrings de función lo cambia. El valor real se lee del mensaje del
gate al final de la ola 2.

### F-7 — `ruff` y `mypy --strict` limpios con el cambio completo

```
uv run ruff check packages/          → All checks passed!
uv run ruff format --check packages/ → 186 files already formatted
uv run mypy                          → Success: no issues found in 75 source files
uv run mypy packages/market-data-client/src → Success: no issues found in 13 source files
```
`[VERIFIED]` — incluye `-> bool` en `__bool__`, `-> Self` en `empty()`, y la forma anidada
`if not isinstance(...): if value is not None:` (ninguna regla `SIM` se dispara).

### F-8 — Snapshots de superficie: byte-idénticos

```
uv run python verification/regen_snapshots.py
  → Wrote ambito(10 symbols), iol(19), higyrus(31), matriz(65)
git status --porcelain verification/  → (vacío)
git diff --stat verification/         → (vacío)
```
`[VERIFIED]` — D-12 confirmado empíricamente, no solo por lectura del formato. Nótese que hay
**4** snapshots (ámbito, iol, higyrus, matriz); market-data tiene su propio
`tests/test_public_surface_market_data.py`, y wallets no tiene snapshot.

### F-9 — `verification/` no es corrible como parte de la verificación

Timeout a los 10 min sin completar (tests de retry/backoff con sleeps reales). Además está rojo de
base por `HARN-VERIF-01` (19 failed + 19 errors, deuda diferida a v1.7+). CI **nunca** lo corre: el
job `test` pasa `packages/${{ matrix.package }}` explícito, lo que anula `testpaths`. El root
`tests/` sí corre local en 0,01 s (2 tests) y también queda fuera de CI. `[VERIFIED]`

### F-10 — Roster completo de los 35 campos del blast radius (insumo directo de D-17)

`[VERIFIED: introspección de get_type_hints sobre las 52 clases]`

**higyrus — 11**
```
Administrador.agente                : Agente
Administrador.operador              : Operador
Administrador.sucursal              : Sucursal
Cuenta.disposicionesGenerales       : DisposicionesGenerales
Cuenta.domicilios                   : list[Domicilio]
Cuenta.personasRelacionadas         : list[PersonaRelacionada]
Cuenta.mediosComunicacion           : list[MedioComunicacion]
Cuenta.cuentasBancarias             : list[CuentaBancaria]
Cuenta.administrador                : Administrador
Movimiento.idMovimientos            : list[int]        ← del piso ≥22 (29-SIZING.md:302-304)
Posicion.parking                    : list[Parking]    ← del piso ≥22
```
**iol — 0** (confirma D-17: iol no retira ningún triple en esta fase; sus `puntas` son
`| None` hoy y se convierten en eslabones recién en la Phase 38).

**market-data — 8**
```
AddHolidaysResult.days              : list[CalendarDay]
CalendarConfig.warnings             : list[Any]
CalendarConfigPreview.market_after  : PreviewMarket
CalendarConfigPreview.warnings      : list[Any]
FeedIngestor.market                 : FeedMarket
FeedIngestor.pipeline               : FeedPipeline
Health.auth                         : HealthAuth       ← el que hace rojo el 11º test (F-4b)
HealthFeed.ingestor                 : FeedIngestor
```
**matriz — 16**
```
ExecutionReportFrame.orderReport    : OrderReport
Instrument.instrumentId             : InstrumentId     ← S-3 de 29-SIZING (el de mayor consecuencia)
InstrumentDetail.instrumentId       : InstrumentId
InstrumentDetail.segment            : Segment
InstrumentDetail.orderTypes         : list[Literal[...]]
InstrumentDetail.timesInForce       : list[Literal[...]]
MarketDataFrame.instrumentId        : InstrumentId
MarketDataFrame.marketData          : MarketDataSnapshot
MarketDataSnapshot.BI               : list[MarketDataLevel]
MarketDataSnapshot.OF               : list[MarketDataLevel]
MarketDataSnapshot.LA               : MarketDataEntryValue   ← S-5 de 29-SIZING
MarketDataSnapshot.SE               : MarketDataEntryValue   ← S-5
MarketDataSnapshot.OI               : MarketDataEntryValue   ← S-5
MarketDataSnapshot.CL               : MarketDataEntryValue   ← S-5
Order.instrumentId                  : InstrumentId
OrderReport.instrumentId            : InstrumentId
```
Total **35** — coincide exactamente con el conteo de D-17.

**Intersección con el piso ratificado de higyrus (`29-SIZING.md:302-304`), derivada:** de los 22
triples del piso (`Movimiento` 9 + `PosicionValuada` 11 + `Posicion` 2), **exactamente 2** son
modelo/lista y por lo tanto se retiran: `Movimiento.idMovimientos` y `Posicion.parking`. Los 11 de
`PosicionValuada` y `Posicion.disponibleAjustado` son escalares y **siguen emitiendo**. Coincide
con D-17 al carácter.

---

## D-17 — Forma recomendada del artefacto de contabilidad

`[ASSUMED — es discreción del planner según CONTEXT]`

**Dónde:** archivo propio `.planning/phases/35-fundaci-n-null-object-bool-pol-tica-del-walker/35-RETIRED-TRIPLES.md`,
siguiendo el precedente de `29-SIZING.md`, `33-CENSUS.md` y `33-LITERALS.md` (artefactos de censo
como archivo nombrado, no como sección de VERIFICATION). El nombre queda greppeable desde la
Phase 39.

**Unidad:** la **4-tupla** `(slug, model, field_path, kind)`, que es *literalmente* la unidad de
`33-CENSUS.md` ("La unidad del censo es la 4-tupla distinta `(slug, model, field_path, kind)`
tomada de `DivergenceHandler.seen`"). Elegir la misma unidad permite que la Phase 39 haga una
**resta de conjuntos** en vez de una traducción.

**Advertencia de unidad que el artefacto debe repetir:** `33-CENSUS.md` documenta que los pisos de
`29-SIZING.md` son **sumas de registros** a través de 43 archivos de corpus, no triples distintos
(higyrus ≥22 → 22 distintos; matriz ≥24 → 14; market-data ≥50 → 22). El artefacto de D-17 debe
declarar **contra cuál de las dos columnas** está contando, fila por fila, o reintroduce
exactamente el falso negativo que P-02 prohíbe.

**Esqueleto propuesto:**

```markdown
# 35-RETIRED-TRIPLES.md — triples que la política Null Object retira del censo

**Unidad:** 4-tupla `(slug, model, field_path, kind)` — la misma de `33-CENSUS.md`.
**Disposición aplicada:** NOBJ-02 — `null`/ausente sobre eslabón no-opcional colapsa sin registro.
**Qué NO retira:** wrong-type (sigue `type`/`non_dict`), `extra`, `missing` de escalares,
`non_dict` top-level, eje mapping.

| slug | model | field_path | kind retirado | ¿estaba en el piso 29-SIZING? | ¿medido en 33-CENSUS? |
|---|---|---|---|---|---|
| higyrus-client | Movimiento | .idMovimientos | missing | sí (parte del ≥22 / 22 distintos) | … |
| higyrus-client | Posicion | .parking | missing | sí (parte del ≥22 / 22 distintos) | … |
| …35 filas… |

## Resta esperada por paquete
| Paquete | Piso (registros) | Piso (triples distintos) | Triples retirados por NOBJ-02 | Piso esperado post-35 |
|---|---:|---:|---:|---:|
| higyrus-client | ≥22 | 22 | 2 | 20 |
| iol-client | — | — | 0 | — |
| market-data-client | ≥50 | 22 | … | … |
| matriz-client | ≥24 | 14 | … | … |
```

---

## Recommended Wave Decomposition

`[ASSUMED — es propuesta de investigación; el planner decide]`

**Ola 0 — evidencia primero (paralelizable por paquete, 6 vías):**
tests nuevos de veracidad/enumeración + criterio 5 + los 2 tests de wrong-type del sitio de lista.
Los de veracidad quedan **rojos** hasta la ola 1; los de wrong-type quedan **verdes desde el día 0**
(pinean el comportamiento actual, que la ola 2 debe preservar) — que es exactamente la propiedad
de falsificación que pide el criterio 2. Más el artefacto D-17 (lectura + intersección).

**Ola 1 — las 4 bases (paralelizable por paquete, 4 vías; NO toca el hash):**
`__bool__` × 4 + `empty()` × 3 + `UnknownFrame.__bool__`. Al terminar: `pytest packages` verde
salvo los tests de la ola 0 que dependían del walker; `ruff` + `mypy` × 2 verdes; los 4 gates
**verdes** (ninguno se mueve todavía). Se puede commitear solo. `[VERIFIED: F-4c]`

**Ola 2 — el walker (SECUENCIAL, un solo commit atómico):**
edit × 5 byte-idéntico + reescritura del comentario WR-02 × 5 + inversión de las **11** aserciones
+ bump del digest recomputado. Cualquier partición de este commit deja CI rojo (§Pitfall 7).

**Ola 3 — verificación:** los 4 gates + `pytest packages` + regen de snapshots con
`git diff --exit-code` + `mypy` × 2.

**Por qué las bases van antes del walker:** el edit del walker es el único paso que mueve el
digest; hacerlo último minimiza la ventana en la que `check_decode_intactness` está rojo y
mantiene el commit del hash chico y auditable. Además la ola 1 es donde vive toda la
paralelización real (4 paquetes independientes), mientras que la ola 2 es intrínsecamente
secuencial.

---

## Sources

### Primary (HIGH confidence — ejecutado en esta sesión)

- Probe de enumeración sobre las 52 clases reales de los 4 paquetes (`empty()`, `__bool__`,
  igualdad, perturbación, emisión, perf) — 2026-08-28
- Aplicación completa del cambio + `uv run pytest packages -q` (11 failed / 1749 passed / 93,70 s)
  + reversión verificada con `git status --porcelain`
- `uv run python tools/{check_decode_intactness,check_uniform_structure,check_surface_types,surface_parity}.py`
  bajo el cambio
- `uv run ruff check` / `ruff format --check` / `uv run mypy` / `uv run mypy packages/market-data-client/src`
- `uv run python verification/regen_snapshots.py` + `git diff verification/`
- Lectura directa: `tools/check_decode_intactness.py:120-272,402-519`,
  `tools/check_surface_types.py:83-99,380-415`, `.github/workflows/ci.yml:40-145`,
  `packages/*/src/*/_decode.py:180-594`, los 4 `models.py`,
  `packages/higyrus-client/tests/test_decode.py` (completo),
  `packages/market-data-client/tests/test_core.py:1052-1082`

### Secondary (MEDIUM confidence — documentos de planning del propio repo)

- `.planning/phases/35-…/35-CONTEXT.md` (decisiones D-01..D-17)
- `.future_plans/api-tipada-null-objects.md` (principios D-NO-01..D-NO-06)
- `.planning/milestones/v1.6-phases/29-decoder-observable/29-SEMANTICS-MATRIX.md` ("Never harmonize", §290-327)
- `.planning/milestones/v1.6-phases/29-decoder-observable/29-SIZING.md:290-320` (pisos ratificados)
- `.planning/milestones/v1.6-phases/33-…/33-CENSUS.md` (unidad de censo, corrección de unidad)
- `.planning/ROADMAP.md` (criterios de las fases 35-40; backlog `HARN-VERIF-01`, `D-16`)
- `.planning/REQUIREMENTS.md` (NOBJ-01, NOBJ-02)
- `CLAUDE.md` (stack, convenciones, arquitectura)

### Tertiary (LOW confidence)

- Ninguna. Esta fase no requirió búsqueda web ni documentación externa: no se introduce ninguna
  dependencia y toda la semántica en juego (`dataclasses`, `typing.get_type_hints`) fue verificada
  empíricamente en el runtime del proyecto en vez de citada.

---

## Metadata

**Confidence breakdown:**

- Standard stack: **HIGH** — no se agrega nada; todo lo usado se ejecutó y quedó verde.
- Architecture: **HIGH** — los 2 sitios de edición y el choke point de strict se leyeron línea a
  línea en las 5 copias y se verificaron con offsets reales por paquete.
- Pitfalls: **HIGH** — los 8 salen de una ejecución real; ninguno es especulativo. El más
  importante (F-4b, el 11º test) contradice el inventario del CONTEXT y está medido.
- D-17 / forma del artefacto: **MEDIUM** — la unidad y el archivo son inferencia del precedente
  (`33-CENSUS.md`); el **contenido** (los 35 campos) está verificado.
- Descomposición en olas: **MEDIUM** — propuesta razonada sobre la restricción medida del hash;
  el planner puede reorganizarla.

**Research date:** 2026-08-28
**Valid until:** indefinido mientras el árbol no se mueva. Las líneas citadas (`file:line`), el
red set de 11 y el conteo de 1749 tests son válidos contra `HEAD` = `242b9f3`; cualquier commit
intermedio a `_decode.py`, `models.py` o `tests/test_decode.py` los invalida y hay que re-medir.
