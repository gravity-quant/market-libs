# Phase 36: `market-data-client` — `market_data` tipado + revocación de la Fase 33 — Research

**Researched:** 2026-08-29
**Domain:** Tipado interno de modelos Python (dataclasses frozen+slots, Null Object, walker de decode), sin dependencias externas nuevas
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Modelos nuevos + alias (D-NO-05)**

- **D-01:** Tres clases nuevas en `models.py`, copia local del patrón matriz (sin import
  cross-package, D-NO-06): `BookLevel {price: float | None, size: int | None}`,
  `EntryValue {price: float | None, size: int | None, date: int | None}`,
  `MarketDataEntries` (contenedor) con `BI`/`OF: list[BookLevel]` (default `field(default_factory=list)`),
  `LA`/`SE`/`CL`/`OI: EntryValue` (Null Object vía `field(default_factory=EntryValue.empty)`).
- **D-02:** El roster de escalares de `MarketDataEntries` incluye SOLO las 10 claves observadas
  en la captura real de Phase 33 (`BI`, `CL`, `HI`, `LA`, `LO`, `OF`, `OI`, `OP`, `SE`, `TV`) — no
  el set más amplio de matriz (`IV`/`EV`/`NV`/`ACP`). Un campo real no modelado llega como "extra"
  no fatal (divergencia reportada, no crash) hasta que Phase 39 lo corrija in-cycle.
- **D-03:** Las propiedades alias (`last → LA`, `bids → BI`, `offers → OF`, `settlement → SE`,
  `close → CL`, `open_interest → OI`) son `@property` de solo lectura simples, SIN caché/memoización
  — la forma exacta ya está fijada por el fixture `_AliasShaped`/`_AliasFree` de
  `packages/market-data-client/tests/test_null_object.py:191-201` (criterio 5 de Phase 35). El
  roster `_safemodel_classes()` de ese mismo archivo espera exactamente 3 clases nuevas
  (`>= 16`, medido en 16 pre-Phase-36).

**Reversión SC-2 (Fase 33) + baja de la maquinaria de mapping**

- **D-04:** `MarketDataSnapshot.entries: list[str]` (sin `| None`) y
  `MarketDataSnapshot.market_data: MarketDataEntries` (sin `| None`, Null Object nunca `None`) —
  ambos vuelven a REQUIRED sin default explícito a nivel dataclass; el walker
  (`_decode.py:436-506`) ya colapsa `null`/ausente a `[]`/instancia vacía SIN emitir divergencia
  para campos no-opcionales de tipo lista/modelo (política NOBJ-02, Phase 35). `staleness_seconds`
  y `note` quedan `| None` (hojas, D-NO-03) — sin cambios.
- **D-05:** `_mapping_value`, `_apply_mapping_policy`, `_is_mapping`, `_strip_optional` se
  eliminan enteros de `models.py`, junto con sus tests de precondición
  (`test_core.py` líneas ~1156-1174 y ~1453-1454; `test_decode.py` líneas ~673-706, ~1328-1373) —
  no tienen otro uso en el paquete fuera de la maquinaria de mapping. El módulo `models.py` ya
  documenta esta baja explícitamente ("Phase 36 retires this paquete's mapping machinery
  outright", línea 259).
- **D-06:** `LatestRequest.entries: list[str] = field(default_factory=list)` (revierte el
  widening); `to_dict()` sigue omitiendo la clave `entries` cuando la lista está vacía
  (`if self.entries:` en vez del actual `is not None`) — se preserva la semántica actual de
  "ausente = todas" en vez de introducir `"entries": []` explícito, porque no hay evidencia en el
  repo de que el servidor distinga ambos casos.

**`test_snapshot_no_data_row.py` — migración de semántica**

- **D-07:** Las aserciones `row.entries is None` / `row.market_data is None` pasan a
  `row.entries == []` / `bool(row.market_data) is False` (equivalente a
  `row.market_data == MarketDataEntries.empty()`); `row.staleness_seconds is None` NO cambia
  (hoja, sin tocar). El docstring del módulo debe referenciar la revocación del checkpoint 33-07
  (SC-2, "fix-shape-now") y el plan fuente `.future_plans/api-tipada-null-objects.md`.
- **D-08:** El docstring de `models.py` (línea 1 en adelante, y el bloque específico de
  `MarketDataSnapshot`) debe documentar explícitamente la revocación del widening de Phase 33
  con referencia al checkpoint que revoca, siguiendo el mismo patrón que ya usó Phase 33 para
  documentar el widening original.

**Versionado — fuera de alcance de esta fase**

- **D-09:** Esta fase NO bumpea versión ni publica — ni `pyproject.toml`, ni `__version__`, ni
  CHANGELOG. El bump breaking + changelog callout + tabla de migración vieja→nueva quedan
  íntegramente para la Phase 40 (`PUB-NOBJ-01`), replicando el patrón v1.6 (Phase 30 tipó
  `iol-client`, Phase 34 publicó). `main_market_data.py` sí se actualiza para consumir por
  encadenamiento profundo en sus sitios reales (parte del alcance de esta fase, SC5).

### Claude's Discretion

- La ubicación exacta de las 3 clases nuevas dentro de `models.py` (sección "Market data" cerca
  de `MarketDataSnapshot`) y el orden de los campos dentro de `MarketDataEntries` quedan a
  discreción de la implementación, siguiendo el orden wire observado en la captura
  (`BI, CL, HI, LA, LO, OF, OI, OP, SE, TV`).
- El tratamiento de `_ENDPOINT_OPTIONAL = frozenset({"note", "entries"})` en
  `main_market_data.py` (usado por la herramienta de captura de schema, no por los modelos) no
  quedó decidido explícitamente — el planner debe verificar si sigue siendo correcto una vez que
  `entries` nunca es genuinamente ausente del payload modelado (aunque puede seguir ausente del
  wire crudo).

### Deferred Ideas (OUT OF SCOPE)

- Bump de versión, changelog callout y tabla de migración vieja→nueva de `market-data-client` —
  explícitamente Phase 40 (`PUB-NOBJ-01`), no esta fase.
- Verificación en vivo del encadenamiento profundo contra develop — explícitamente Phase 39
  (`LIVE-NOBJ-01`), no esta fase.
- Ampliar el roster de `MarketDataEntries` a los campos `IV`/`EV`/`NV`/`ACP` de matriz sin
  evidencia de wire propio — descartado por ahora (D-02); si aparecen en vivo en Phase 39, se
  corrigen in-cycle ahí.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| NOBJ-MD-01 | `snapshot.market_data.last.price` compila bajo mypy strict y nunca lanza con ningún payload real ni `None` — `market_data` pasa de `dict[str, Any] \| None` a modelo tipado (campos wire `BI`/`OF: list[BookLevel]`, `LA`/`SE`/`CL`/`OI: EntryValue` Null Object, `OP`/`HI`/`LO`/`TV/...: float \| None`) con propiedades alias `last`/`bids`/`offers`/`settlement`/`close`/`open_interest` | **F-1** (matriz de 4 payloads ejecutada: 0 divergencias, 0 raises, chain completa), **F-2** (`mypy --strict` limpio sobre el shape propuesto), **F-3** (int→float widening silencioso — el wire manda `int` para `price`), Pattern 1, Pattern 2 |
| NOBJ-MD-02 | `MarketDataSnapshot.entries` vuelve a `list[str]` default `[]` (revierte el widening F33) y `LatestRequest.entries` se alinea; la fila no-data de `/marketdata/latest` expone `market_data` vacío falsy + `note` poblado; se elimina la maquinaria `_mapping_value`/`_apply_mapping_policy` y sus tests de precondición | **F-1** (`entries: None` → `[]` sin divergencia), **F-4** (censo exacto de 13 call-sites de la maquinaria de mapping y su disposición correcta), **F-5** (delta de imports de `models.py`), Pitfall 1, Pitfall 2, Pitfall 3 |
</phase_requirements>

## Summary

Esta fase es **100% interna al repo**: no hay librería nueva, no hay API que consultar, no hay
decisión de stack. Toda la incertidumbre real es sobre **el comportamiento medible del walker
`_decode.py` ya shippeado** frente a la forma de modelo que las decisiones D-01..D-06 fijan, y
sobre el **blast radius exacto** de retirar la maquinaria de mapping. Ambas cosas se midieron
ejecutando código en esta sesión, no se infirieron.

El resultado central es tranquilizador y verificable: **el shape propuesto produce CERO
divergencias contra los cuatro payloads de la matriz de casos**, la cadena profunda
`snapshot.market_data.last.price` devuelve `None` en vez de lanzar en los tres casos vacíos, y
`mypy --strict` acepta el conjunto completo (dataclass frozen+slots + `@property` alias + cadena
de tres niveles) sin un solo `type: ignore`. El `int` que el wire real manda para `price` se
ensancha a `float` **en silencio** (`walk_field` hace `float(value)` antes de consultar
`scalar_passthrough`), así que declarar `price: float | None` no fabrica divergencias — un riesgo
que parecía real y no lo es.

El riesgo verdadero de la fase **no está en los modelos nuevos sino en la baja de la maquinaria de
mapping**. Los rangos de líneas que CONTEXT D-05 manda borrar (`test_core.py` ~1156-1174 /
~1453-1454, `test_decode.py` ~673-706 / ~1328-1373) **contienen tests que NO son de mapping y que
sobreviven a la fase**: el lock T-31-17 de "exactamente dos Optionals" en los modelos de health, el
lock de `received_at` ausente, y el lock WR-03 de `from_api`-override-nunca-anidado. Borrar por
rango retiraría tres invariantes vivos. La disposición correcta es **editar quirúrgicamente 5
tests y borrar sólo 1**, más migrar 6 tests del eje mapping a la semántica de modelo. Ese es el
trabajo real de la fase.

**Primary recommendation:** Copiar el patrón matriz **adaptándolo a la base de market-data**
(`frozen=True, slots=True` + `SafeModel` local, NO `_SafeModel` de matriz que no tiene slots),
declarar los 10 campos en orden wire, y tratar la retirada de la maquinaria de mapping como una
edición campo-por-test guiada por el censo de la sección "Runtime State Inventory" — nunca por
rango de líneas.

## Project Constraints (from CLAUDE.md)

Directivas accionables extraídas de `./CLAUDE.md` que este plan debe respetar:

| # | Directiva | Consecuencia para Phase 36 |
|---|-----------|---------------------------|
| C-1 | Python 3.12+, uv, httpx, pytest+pytest-httpx, ruff, mypy strict — todo cambio pasa el CI existente | Los 4 jobs (`lint`, `pre-commit`, `typecheck`, `tests` 6×2) deben quedar verdes |
| C-2 | **Sin código compartido entre paquetes (por diseño)** | Las 3 clases nuevas son copia LOCAL del patrón matriz; `from matriz_client...` está prohibido (D-NO-06) |
| C-3 | Dual sync/async: todo fix de lógica se espeja en `client.py` y `aio.py` | Esta fase no toca lógica de decode en los shells (el decode vive en `models.py`), pero SC-1 exige verificar la cadena en **ambas** superficies — los tests deben venir de a pares |
| C-4 | Credenciales en `.env` por paquete; nunca commitear ni loggear | Sin impacto directo; los tests usan `pytest_httpx`, nunca red |
| C-5 | `from __future__ import annotations` obligatorio en todo módulo | Las clases nuevas van en `models.py`, que ya lo tiene |
| C-6 | Modelos: `@dataclass(frozen=True, slots=True)`, herencia de `SafeModel`, campos wire-verbatim, construcción sólo vía `from_api`/`empty` | Las 3 clases nuevas siguen esta forma exacta |
| C-7 | `__all__` explícito con todos los nombres públicos + `__version__` | Las 3 clases deben entrar en `models.__all__` (test WR-02 lo asevera por introspección) |
| C-8 | GSD Workflow Enforcement — no editar fuera de un comando GSD | El plan se ejecuta vía `/gsd-execute-phase` |
| C-9 | Ruff: line-length 100, comillas dobles, 4 espacios; reglas E,W,F,I,B,UP,SIM,RUF,ASYNC,PIE,PT,RET,TID,LOG | **F401 (import no usado) es la trampa mecánica de esta fase** — ver F-5 |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Declaración de forma tipada (`MarketDataEntries`/`BookLevel`/`EntryValue`) | `models.py` (capa de modelo) | — | Toda la superficie de respuesta del paquete vive en `models.py`; el walker es ciego a la declaración salvo por `get_type_hints()` |
| Ergonomía de acceso (`@property` alias) | `models.py` | — | Las `@property` son invisibles a `get_type_hints()`/`dataclasses.fields()` (probado en Phase 35 criterio 5) — no pueden vivir en otra capa sin volverse visibles |
| Colapso `null`/ausente → Null Object | `_decode.py` (walker) | — | Ya implementado por Phase 35 (NOBJ-02). **Esta fase no toca `_decode.py`** — es lo que hace que criterio 5 ("sin mover el hash") sea cierto por construcción |
| Decodificación del campo `market_data` | `models.py` vía walker | ~~`_apply_mapping_policy`~~ | Hoy es un pase call-site compensatorio porque el walker no tiene rama `dict`. Al pasar a modelo, la rama `_is_model` del walker se hace cargo y el pase desaparece |
| Serialización de request (`LatestRequest.to_dict`) | `models.py` | — | Dataclass serialize-OUT, NO `SafeModel`; su `entries` es independiente del de `MarketDataSnapshot` |
| Consumo por encadenamiento profundo | `main_market_data.py` (driver de verificación) | `client.py` / `aio.py` (superficies) | SC-5 exige que el driver ejerza la cadena en sus sitios reales; los shells sólo devuelven `list[MarketDataSnapshot]` y no cambian |
| Reporte SHAPE model↔wire | `verification/safemodel_diff.py` + `main_market_data.py::_emit_shape` | — | Recursión automática en modelos anidados — cambia de comportamiento al tipar `market_data` (ver F-6) |

## Standard Stack

Esta fase **no instala ni actualiza ninguna dependencia**. El stack es el ya presente en el
workspace y se documenta sólo para que el planner no lo re-derive.

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| CPython | 3.12.11 (venv) / 3.13 en CI | Runtime | `[VERIFIED: uv run python]` — `pyproject.toml` fija `python_version = "3.12"`, matriz CI 3.12+3.13 |
| stdlib `dataclasses` | stdlib | `@dataclass(frozen=True, slots=True)` + `field(default_factory=...)` | `[VERIFIED: codebase]` — el patrón de modelo en los 6 paquetes; D-lock 29-04 rechazó msgspec, motor único stdlib |
| stdlib `typing` | stdlib | `get_type_hints` (cacheado en `_decode.hints_for`), `Self`, `Any`, `cast` | `[VERIFIED: codebase]` `_decode.py:401-409` |
| pytest | >=8.3 | Runner | `[VERIFIED: pyproject.toml]` |
| pytest-httpx | >=0.34 | Mock HTTP para los tests de superficie sync/async | `[VERIFIED: codebase]` — `test_snapshot_no_data_row.py` ya lo usa |
| pytest-asyncio | >=0.24, `asyncio_mode = "auto"` | Tests async sin decorador | `[VERIFIED: pyproject.toml]` |
| ruff | >=0.7 | Lint + format | `[VERIFIED: pyproject.toml]` |
| mypy | >=1.13, `strict = true` | Type check — es literalmente el criterio 1 de la fase | `[VERIFIED: pyproject.toml:83-97]` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `uv` | 0.9.0 | Runner del workspace | `uv run --package market-data-client pytest ...` |

### Alternatives Considered

Ninguna. El D-lock firmado `no-go-stdlib-only` (Phase 29 P04, sebadlf 2026-08-19) cierra la
pregunta de motor de decode para todo el milestone. Traer `pydantic`/`msgspec`/`attrs` para
"resolver" Null Objects violaría ese lock, cambiaría el perfil de dependencias de los 6 wheels
(hoy closure 100% puro-Python) y no está en el scope de ninguna decisión de CONTEXT.

**Installation:** ninguna. `uv sync --all-packages --all-extras --dev --frozen` (ya sincronizado).

## Package Legitimacy Audit

**No aplica — esta fase no instala ningún paquete externo.**

Todo el cambio ocurre dentro de `packages/market-data-client/` y `main_market_data.py`, usando
únicamente la stdlib y las dependencias ya presentes en `uv.lock`. `uv.lock` **no se toca**
(refrescarlo es explícitamente trabajo de Phase 40, y el precedente v1.6 lo hace una sola vez).

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```text
   HTTP response (httpx.Response)
              │
              ▼
  ┌──────────────────────────────────────┐
  │ _core.parse_market_data_response     │  desenvuelve envelope {count, items[]}
  │ _core.parse_latest_response          │  toma UN received_at por respuesta
  └───────────────┬──────────────────────┘
                  │  por cada fila:  MarketDataSnapshot.from_api(item, received_at=…)
                  ▼
  ┌──────────────────────────────────────────────────────────────┐
  │ MarketDataSnapshot.from_api  (models.py — from_api OVERRIDE) │
  │  1. stamped = {**payload, "received_at": rx}   ← pre-hook    │
  │  2. walk_model(cls, stamped, POLICY, sink)                   │
  │  3. ~~_apply_mapping_policy(...)~~   ← RETIRADO en F36       │
  │  4. kwargs["received_at"] = rx       ← inyección D-01        │
  └───────────────┬──────────────────────────────────────────────┘
                  │
                  ▼
  ┌──────────────────────────────────────────────────────────────┐
  │ _decode.walk_model  →  por campo  _decode.walk_field          │
  │                                                               │
  │   ¿Union con None?  ──sí──► value is None → return None       │
  │        │ no                        (hoja: staleness, note)    │
  │        ▼                                                      │
  │   ¿origin is list? ──sí──► value None → []  SIN divergencia   │
  │        │                    value no-lista → sink("type")     │
  │        ▼                    (entries, BI, OF)                 │
  │   ¿_is_model?      ──sí──► value None → Model.empty-shape     │
  │        │                    SIN divergencia  (NOBJ-02, F35)   │
  │        │                    value no-dict → sink("non_dict")  │
  │        ▼                    (market_data, LA/SE/CL/OI)        │
  │   str / bool / int / float / Literal → typed zero + sink      │
  │        (float: int → float(value) SILENCIOSO)                 │
  └───────────────┬──────────────────────────────────────────────┘
                  │
        divergencias ──► DecodeScope._emit ──► logger market_data_client
                  │                            └─ STRICT_DECODE → raise
                  ▼                               (nunca sobre "extra")
      MarketDataSnapshot(
        market_data = MarketDataEntries(...)  ← NUNCA None
      )
                  │
                  ▼
   consumidor:  snapshot.market_data.last.price
                snapshot.market_data.bids[0].price
                            │
                            └─ @property (invisible a get_type_hints)
```

### Recommended Project Structure

Ningún archivo nuevo. La superficie tocada es:

```text
packages/market-data-client/
├── src/market_data_client/
│   ├── models.py          # +3 clases, −4 funciones, +__all__ ×3, docstring reescrito
│   └── __init__.py        # +3 re-exports (recomendado, ver Pitfall 6)
└── tests/
    ├── test_models.py     # migrar 2 tests de dict → modelo
    ├── test_decode.py     # migrar 5, borrar 1, editar 2
    ├── test_core.py       # editar 3 (NO borrar — ver Pitfall 1)
    ├── test_null_object.py# migrar/retitular 1, docstrings ×2
    └── test_snapshot_no_data_row.py  # migrar semántica (D-07)
main_market_data.py        # encadenamiento profundo en sitios reales (SC-5)
```

**No se toca:** `_decode.py` (criterio 5 depende de ello), `_core.py`, `client.py`, `aio.py`,
`tools/check_decode_intactness.py`, `pyproject.toml`, `uv.lock`, `README.md`, `__version__`.

### Pattern 1: Null Object contenedor con hijos Null Object

**What:** Un contenedor cuyos eslabones no-opcionales son o bien listas (`default_factory=list`) o
bien instancias vacías (`default_factory=Child.empty`), y cuyas hojas son `T | None`.
**When to use:** Cuando la cadena de acceso debe terminar en un valor o en `None`, nunca en un
`AttributeError`. Es exactamente la forma de `matriz_client.models.MarketDataSnapshot`.

```python
# Source: packages/matriz-client/src/matriz_client/models.py:387-428 (patrón de referencia)
#         adaptado a la base de market-data (frozen + slots, SafeModel local).
@dataclass(frozen=True, slots=True)
class BookLevel(SafeModel):
    """Nivel de precio dentro de una entrada de book (``BI`` / ``OF``)."""

    price: float | None = None
    size: int | None = None


@dataclass(frozen=True, slots=True)
class EntryValue(SafeModel):
    """Entrada escalar de market data (``LA``, ``SE``, ``CL``, ``OI``)."""

    price: float | None = None
    size: int | None = None
    date: int | None = None


@dataclass(frozen=True, slots=True)
class MarketDataEntries(SafeModel):
    BI: list[BookLevel] = field(default_factory=list)
    CL: EntryValue = field(default_factory=EntryValue.empty)
    HI: float | None = None
    LA: EntryValue = field(default_factory=EntryValue.empty)
    LO: float | None = None
    OF: list[BookLevel] = field(default_factory=list)
    OI: EntryValue = field(default_factory=EntryValue.empty)
    OP: float | None = None
    SE: EntryValue = field(default_factory=EntryValue.empty)
    TV: float | None = None

    @property
    def bids(self) -> list[BookLevel]:
        """Alias de sólo lectura sobre el campo wire ``BI`` (D-NO-05)."""
        return self.BI
    # … offers → OF, last → LA, settlement → SE, close → CL, open_interest → OI
```

**Diferencias obligatorias contra el original de matriz** (no son opcionales):

| Eje | matriz (`_SafeModel`) | market-data (`SafeModel`) |
|-----|----------------------|---------------------------|
| Decorador | `@dataclass(frozen=True)` — **sin slots** | `@dataclass(frozen=True, slots=True)` (C-6) |
| Base | `_SafeModel` (declara `__dataclass_fields__` como ClassVar) | `SafeModel` local |
| Roster | 14 campos (incluye `IV`/`EV`/`NV`/`ACP`) | **10 campos** (D-02) |
| Alias | ninguno | 6 `@property` (D-NO-05) |
| Import | prohibido cruzarlo (C-2 / D-NO-06) | copia local |

### Pattern 2: `@property` alias sobre dataclass frozen+slots

**What:** Propiedad de sólo lectura declarada junto a los campos wire.
**When to use:** Siempre que el nombre wire sea críptico (`LA`, `BI`) y el consumidor merezca un
nombre legible.
**Por qué es seguro:** El walker usa exclusivamente `get_type_hints()` y `dataclasses.fields()`.
Una `@property` no aparece en ninguno de los dos. Phase 35 criterio 5 lo dejó pineado con el par
`_AliasShaped`/`_AliasFree` (`test_null_object.py:191-209`), que asevera **igualdad de records**
entre la clase con alias y su gemela sin alias.

`[VERIFIED: ejecutado en esta sesión]` — `@property` sobre `frozen=True, slots=True` funciona sin
conflicto siempre que el nombre del alias no colisione con un nombre de campo (los 6 alias
propuestos no colisionan). `mypy --strict` acepta la cadena de 3 niveles sin `type: ignore`.

### Pattern 3: Migración de aserción `is None` → aserción de veracidad

**What:** El test que preguntaba "¿es `None`?" ahora pregunta "¿carga algo?".

```python
# ANTES (Phase 33)                    # DESPUÉS (Phase 36)
assert row.market_data is None        assert bool(row.market_data) is False
assert row.entries is None            assert row.entries == []
assert row.staleness_seconds is None  assert row.staleness_seconds is None   # hoja, SIN CAMBIO
```

`bool(row.market_data) is False` y `row.market_data == MarketDataEntries.empty()` son
equivalentes por construcción: `SafeModel.__bool__` está implementado como
`self != type(self).empty()` (`models.py:295`).

### Anti-Patterns to Avoid

- **Borrar tests por rango de líneas.** Los rangos de CONTEXT D-05 mezclan tests de mapping con
  tests de invariantes que sobreviven. Ver Pitfall 1 y el censo de la sección Runtime State.
- **Tocar `_decode.py`.** El criterio 5 dice literalmente "sin mover el hash de `_decode.py`". La
  maquinaria a retirar está en `models.py`. Cualquier byte movido en `_decode.py` obliga a
  recomputar `CANONICAL_DIGEST` en las 5 copias y a la revisión manual ×5 de D-10.
- **Declarar `market_data: MarketDataEntries | None`.** Rompe SC-2 y reintroduce el `None` que la
  fase existe para eliminar; además el walker ya nunca produce `None` para un eslabón no-opcional.
- **Poner `default_factory=EntryValue.empty` en un campo declarado sin default sobre un campo con
  default previo.** El orden de campos de dataclass exige que todo campo con default vaya después
  de los sin default. En `MarketDataEntries` **todos** los campos llevan default, así que no hay
  problema — pero en `MarketDataSnapshot` los campos `entries`/`market_data` **deben seguir sin
  default explícito** (D-04) para no mover `note: str | None = None` de posición.
- **Memoizar `empty()` o las `@property`.** D-03 lo prohíbe explícitamente, y el docstring de
  `SafeModel.empty()` (`models.py:261-264`) documenta por qué: `list`/`dict` mutables compartidos
  proceso-wide.
- **Añadir un no-op `_apply_mapping_policy` "para que se parezca a matriz".** El docstring de
  `empty()` lo prohíbe por escrito: los ejes por-paquete "never harmonize".

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Colapsar `null`/ausente a instancia vacía sin ruido | Un `if payload.get("market_data") is None: ...` en `from_api` | La rama `_is_model` de `_decode.walk_field:502-503` (NOBJ-02, Phase 35) | Ya está shippeado, ya está testeado, y hacerlo a mano reintroduciría el pase call-site que esta fase retira |
| Ensanchar `int` de wire a `float` declarado | Un coercion manual `float(v)` en el modelo | `walk_field` rama `float` (`_decode.py:535-536`) | Lo hace ya y **sin emitir divergencia** — F-3 |
| Comparar un modelo contra "vacío" | Un `all(getattr(x, f.name) is None ...)` | `bool(model)` / `SafeModel.__bool__` (Phase 35) | Recursa correctamente sobre hijos anidados; hacerlo a mano se rompe en el primer campo lista |
| Construir una instancia vacía | `Model(price=None, size=None, date=None)` | `Model.empty()` | Convención del repo (C-6); además `empty()` es la referencia contra la que `__bool__` compara |
| Diffear modelo↔wire para SHAPE findings | Un walk propio en el driver | `verification.safemodel_diff.diff_safemodel_bidirectional` | Ya recursa en modelos anidados y en `list[Model]` (F-6) |
| Detectar Optional en un test | Reimplementar `_strip_optional` desde cero | Copiar el helper de 6 líneas como **módulo-local** en el test (patrón documentado en `test_null_object.py:33-38`) | Repo sin paquete compartido por diseño; los tests ya llevan copias locales a propósito |

**Key insight:** El 80% del comportamiento que esta fase necesita ya está construido y verificado
por Phase 35. El trabajo es **declarativo** (declarar la forma correcta) más **de retirada**
(quitar el andamio que existía sólo porque la forma era incorrecta). Cualquier lógica nueva de
decode es señal de que el scope se corrió.

## Runtime State Inventory

> Fase de refactor/renombre de superficie tipada. Categorías respondidas explícitamente.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| **Stored data** | **Ninguno — verificado.** El paquete no tiene datastore. Los únicos artefactos persistidos con la forma vieja son los **baselines de schema** `.planning/verification/schemas/market-data-client/get-market-data.json` y `get-latest.json` — pero se escriben desde el **wire crudo**, nunca desde `to_dict()` (`main_market_data.py` § `_raw_via_request_sync`/`_async`, y el caveat CR-01 en `models.py:66-78`). Tipar el modelo **no los mueve**. | Ninguna — no regenerar baselines |
| **Live service config** | Ninguno — verificado. `market-data-client` no registra nada en n8n/Datadog/Cloudflare. Su único punto de contacto externo es `market-data-develop.bbsa.com.ar`, y esta fase **no corre en vivo** (eso es Phase 39) | Ninguna |
| **OS-registered state** | Ninguno — verificado. Sin tasks, sin pm2, sin launchd | Ninguna |
| **Secrets/env vars** | Ninguno — verificado. Las credenciales Auth0 del paquete viven en `.env` y ningún nombre de clave cambia | Ninguna |
| **Build artifacts / installed packages** | Ninguno relevante. El workspace se instala editable vía `uv sync`; no hay egg-info stale ni wheel publicado que reconstruir en esta fase (`market-data-client` sigue en **0.5.0**, D-09) | Ninguna — Phase 40 hace el bump y el wheel |
| **Referencias en tests/prosa a la forma vieja** (*categoría propia de esta fase*) | **13 call-sites de la maquinaria de mapping + 12 aserciones de forma dict + 3 docstrings** — censo completo abajo | Edición quirúrgica, NUNCA borrado por rango |

### Censo de la maquinaria de mapping (fuente: grep exhaustivo `_mapping_value\|_apply_mapping_policy\|_is_mapping\|_strip_optional`)

`[VERIFIED: grep sobre el repo, excluyendo matriz-client que tiene su propia copia legítima]`

| Archivo:línea | Símbolo | Contexto real | Disposición correcta |
|---------------|---------|---------------|----------------------|
| `models.py:118-129` | `_strip_optional`, `_is_mapping` | definiciones | **BORRAR** |
| `models.py:132-201` | `_mapping_value`, `_apply_mapping_policy` | definiciones | **BORRAR** |
| `models.py:220-222` | `_apply_mapping_policy` | llamada en `SafeModel.from_api` | **BORRAR** (colapsa a form A: `return cls(**walk_model(...))`) |
| `models.py:267` | `_apply_mapping_policy` | llamada en `SafeModel.empty` | **BORRAR** (colapsa a form A) |
| `models.py:422-424` | `_apply_mapping_policy` | llamada en `MarketDataSnapshot.from_api` | **BORRAR** (la inyección `received_at` de la línea 425 SE QUEDA) |
| `models.py:56-64, 245-259` | prosa | docstrings que describen el pase | **REESCRIBIR** (D-08) |
| `test_core.py:1159` | `_is_mapping` | dentro de `test_health_models_declare_no_mapping_field_and_no_received_at` — el test **también** asevera `"received_at" not in hints` | **EDITAR**: quitar la línea del `_is_mapping`, conservar el test y la aserción de `received_at`. Renombrar a `..._declare_no_received_at` |
| `test_core.py:1174` | `_strip_optional` | dentro de `test_health_models_declare_exactly_the_two_locked_optionals` — **lock T-31-17, no es un test de mapping** | **EDITAR**: helper `_strip_optional` módulo-local en el test. **NO borrar el test** |
| `test_core.py:1453-1454` | `_is_mapping`, `_strip_optional` | dentro de `test_mutation_result_models_declare_no_mapping_field_no_received_at_no_optional` — asevera 3 cosas, sólo 1 es mapping | **EDITAR**: quitar la línea `_is_mapping`, conservar `received_at` y el lock de no-Optional con helper local |
| `test_decode.py:706` | `_is_mapping` | disyunción dentro de `test_no_call_site_exempt_safemodel_appears_as_a_nested_field_type` | **EDITAR**: quitar el disyunto de mapping. El set `exempt` queda `{MarketDataSnapshot, Symbol}` (los `from_api` override) → **sigue no-vacuo** `[VERIFIED]` |
| `test_decode.py:1328` | `_is_mapping` | dentro de `test_no_mapping_carrying_model_is_ever_a_nested_field_type` — sujeto íntegramente retirado | **BORRAR el test entero** (es el único borrado limpio) |
| `test_decode.py:1335` | `_strip_optional` | dentro del mismo test de arriba | **BORRAR** (arrastrado) |
| `test_decode.py:1373` | `_strip_optional` | dentro de `test_models_with_a_from_api_override_are_never_a_nested_field_type` — **lock WR-03, sobrevive a la fase** | **EDITAR**: helper local. **NO borrar** |

> ⚠️ **El rango `~1328-1373` de CONTEXT D-05 cubre DOS tests**, uno a borrar y uno a conservar.
> Borrar el rango retiraría el lock WR-03 que sigue vivo (`MarketDataSnapshot.from_api` sigue
> inyectando `received_at`, `Symbol.from_api` sigue espejando `market_id`).

### Censo de aserciones de forma `dict` a migrar

| Archivo:línea | Aserción actual | Migración |
|---------------|-----------------|-----------|
| `test_models.py:120-122` | `snap.market_data is not None` / `["BI"][0]["price"] == 1` / `["OI"] is None` | `snap.market_data.bids[0].price == 1.0` / `bool(snap.market_data.open_interest) is False` |
| `test_models.py:174` | `snap.market_data is None` | `bool(snap.market_data) is False` |
| `test_models.py` (~línea 176) | `snap.entries is None` | `snap.entries == []` |
| `test_decode.py:1231-1237` | `snap.market_data is None` + `.market_data not in paths` | `bool(...) is False`; la aserción de "ningún record" **sigue valiendo tal cual** `[VERIFIED]` |
| `test_decode.py:1252-1260` | `market_data: ["not","a","mapping"]` → `== {}` + kind `type` | → `bool(...) is False` + kind **`non_dict`**, modelo `MarketDataEntries` `[VERIFIED — el kind CAMBIA]` |
| `test_decode.py:1286-1292` | strict + `market_data: None` → no raise | **sigue sin lanzar** `[VERIFIED]`; sólo cambia la aserción de valor |
| `test_decode.py:1300-1308` | `from_api(None)` → records `== [("", "non_dict")]` | **el set de records es idéntico** `[VERIFIED]`; sólo cambia `snap.market_data is None` |
| `test_decode.py:1185-1214` | fixture `_RequiredMapping` + 2 tests CR-03 | El eje mapping desaparece del paquete. **Decisión para el planner** (Open Question 1) |
| `test_snapshot_no_data_row.py:71-72, 88-89, 113, 128` | `is None` ×6 | D-07 |
| `test_snapshot_no_data_row.py:139` | `rows[0].market_data == {"BI": [{"price": 10, "size": 1}]}` | **No listado en D-07** — migrar a `.bids[0].price == 10.0` |
| `test_null_object.py:271-281` | `test_empty_and_from_api_agree_on_every_mapping_declared_field` | Sujeto (campo mapping) desaparece; la aserción sigue pasando pero deja de significar lo que dice. Retitular o retirar |

## Common Pitfalls

### Pitfall 1: Borrar por rango de líneas retira invariantes vivos

**What goes wrong:** Aplicar literalmente "borrar `test_core.py` ~1156-1174 y ~1453-1454;
`test_decode.py` ~673-706, ~1328-1373" elimina 3 locks que nada tienen que ver con mapping:
`test_health_models_declare_exactly_the_two_locked_optionals` (T-31-17, "un séptimo Optional no
puede agregarse sin fallar acá"), la aserción `"received_at" not in hints` de dos tests, y
`test_models_with_a_from_api_override_are_never_a_nested_field_type` (WR-03).
**Why it happens:** CONTEXT D-05 afirma "no tienen otro uso en el paquete fuera de la maquinaria de
mapping". Es cierto para `_is_mapping`; es **falso para `_strip_optional`**, que los tests usan
como detector genérico de Optional.
**How to avoid:** Usar el censo de arriba, línea por línea. Para los 3 sitios que sólo necesitan
`_strip_optional`, copiar el helper de 6 líneas como función módulo-local del archivo de test — el
patrón que `test_null_object.py:33-38` documenta explícitamente como deliberado.
**Warning signs:** Si el conteo de tests de market-data baja más de ~2 respecto de 663, se borró de
más.

### Pitfall 2: El kind de la divergencia cambia de `type` a `non_dict`

**What goes wrong:** `test_wrong_typed_mapping_field_reports_type_and_substitutes_the_empty_dict`
espera `(".market_data", "type")` con modelo `MarketDataSnapshot`. Tras tipar, el mismo payload
produce `("MarketDataEntries", ".market_data", "non_dict", "MarketDataEntries", "list")`.
**Why it happens:** `_mapping_value` clasificaba con `_kind_of` (`type` para no-`None`); la rama
`_is_model` del walker delega en `walk_model`, que emite `non_dict` con atribución al modelo
anidado.
**How to avoid:** Migrar la aserción a `non_dict` y al modelo `MarketDataEntries`. Sigue siendo
**fatal bajo `strict_decode`** (`non_dict` no está en `_INFO_KINDS`), así que la propiedad "un
wrong-type sigue divergiendo y sigue siendo fatal" se conserva — que es lo que importa.
**Warning signs:** `[VERIFIED: ejecutado]` — medido en esta sesión, no inferido.

### Pitfall 3: Ruff F401 al retirar la maquinaria

**What goes wrong:** El job `lint` falla con imports no usados.
**Why it happens:** `import types`, `Union`, `get_args`, `get_origin` existen **sólo** para
`_strip_optional`/`_is_mapping`; `fields` (de `dataclasses`) existe **sólo** para
`_apply_mapping_policy`. `[VERIFIED: grep de usos en models.py]`
**How to avoid:** Delta de imports exacto (F-5). Y no olvidar **agregar** `field`, que hoy no está
importado y que `default_factory` necesita.
**Warning signs:** `uv run ruff check .` local antes de commitear.

### Pitfall 4: `from_api` colapsa a form A y las notas de form B mienten

**What goes wrong:** Tras retirar el pase, `SafeModel.from_api` y `SafeModel.empty` quedan
idénticos a los de los paquetes form A, pero sus docstrings siguen explicando "form B es la
diferencia". Peor: `test_null_object.py` tiene un test entero
(`test_empty_and_from_api_agree_on_every_mapping_declared_field`) cuyo sujeto ya no existe, y su
docstring de módulo (líneas 21-24) declara la pertenencia a form B.
**Why it happens:** La documentación de este repo es densa y auto-referencial por diseño; la prosa
es tan load-bearing como el código.
**How to avoid:** Tratar el cambio de form B → form A como un **entregable declarado** de la fase:
reescribir el docstring de `empty()` (`models.py:245-259`), el de `from_api`, el bloque CR-03 del
docstring de módulo (`models.py:56-64`), y el bloque de form B de `test_null_object.py:21-24`.
`29-SEMANTICS-MATRIX.md` no es un test ejecutable pero es la fuente citada por 3 docstrings.
**Warning signs:** Un `grep -n 'form B\|mapping pass\|CR-03' packages/market-data-client/` que
todavía devuelva prosa activa tras el cambio.

### Pitfall 5: La inyección de `received_at` se pierde con el pase

**What goes wrong:** `MarketDataSnapshot.from_api` tiene tres pasos: pre-hook de `received_at`,
walk, pase de mapping, inyección de `received_at`. Al borrar el pase es fácil llevarse por delante
la línea 425 (`kwargs["received_at"] = received_at`).
**Why it happens:** Están adyacentes y el comentario CR-03 de las líneas 417-421 envuelve a ambas.
**How to avoid:** El lock D-01 está pineado por tests (el decoy `received_at: "ignored"` en
`test_models.py:106` debe seguir perdiendo contra `received_at=42.0`).
**Warning signs:** `test_from_api_marketdata_item_parses_new_fields` en rojo por `received_at`.

### Pitfall 6: `models.__all__` es aseverado por introspección

**What goes wrong:** Se agregan las 3 clases pero no a `models.__all__` → falla
`test_models_dunder_all_covers_every_safemodel_subclass` (WR-02,
`test_public_surface_market_data.py:94-114`), que **deriva el set esperado del propio módulo**.
**Why it happens:** Es un test diseñado exactamente contra este modo de fallo.
**How to avoid:** Agregar `"BookLevel"`, `"EntryValue"`, `"MarketDataEntries"` a `models.__all__`.
**Además, recomendado:** re-exportarlas desde `market_data_client/__init__.py` + su `__all__`. No
lo exige ningún test (la tupla `_NEW_PUBLIC_NAMES` es curada), pero sin re-export el consumidor no
puede **nombrar** el tipo que `snapshot.market_data` devuelve, lo que contradice el espíritu de
NOBJ-MD-01 y le crea trabajo a Phase 40. C-7 lo respalda.
**Warning signs:** `uv run pytest packages/market-data-client/tests/test_public_surface_market_data.py`

### Pitfall 7: `_ENDPOINT_OPTIONAL` debe conservar `entries`

**What goes wrong:** Razonar "ahora `entries` es no-opcional y siempre llega, saquémoslo del
frozenset" → el driver empieza a emitir un finding SHAPE `model-only entries` falso en cada corrida
contra `/marketdata/latest`.
**Why it happens:** `diff_safemodel_bidirectional` decide `model-only` por **presencia de la clave
en el wire**, y suprime la dirección A sólo para hints Optional. Al revertir `entries` a
`list[str]` deja de estar suprimido por `_is_optional`, y la fila no-data de `/marketdata/latest`
**no trae la clave `entries` en absoluto** (ver `get-latest.json`).
**How to avoid:** `[VERIFIED: ejecutado]` — con el shape propuesto, `diff_safemodel_bidirectional`
sobre la fila no-data devuelve exactamente `[('', 'model-only', 'entries')]`, y sobre el item real
de `/marketdata` devuelve `[]`. **`_ENDPOINT_OPTIONAL` se queda como está**. Esta es la respuesta
medida al ítem abierto de "Claude's Discretion".
`market_data` **no** necesita agregarse: la fila no-data sí trae esa clave (con `null`).
**Warning signs:** Findings SHAPE nuevos en la corrida de Phase 39 que nadie pidió.

### Pitfall 8: Confundir los dos `entries`

**What goes wrong:** Tocar `_core.build_latest_request(..., entries: str | None = None)` creyendo
que es el `entries` de D-06.
**Why it happens:** Mismo nombre, capas distintas. El de `build_latest_request` es un **query
param string** de `GET /marketdata/latest`, que pasa por `drop_none`. El de D-06 es
`LatestRequest.entries: list[str]`, el body de `POST /marketdata/latest`.
**How to avoid:** D-06 toca **sólo** `models.LatestRequest`. `_core.py` no se toca.
**Warning signs:** Cualquier diff en `_core.py`.

### Pitfall 9: `to_dict()` sobre el snapshot cambia de forma

**What goes wrong:** `SafeModel.to_dict()` usa `dataclasses.asdict`, que **aplana recursivamente
los modelos anidados**. Hoy `snapshot.to_dict()["market_data"]` es el dict del wire verbatim;
después será el dict de los 10 campos declarados, con las claves no observadas presentes como
`None` y las extra del wire **desaparecidas**.
**Why it happens:** Es exactamente el caveat CR-01 que `models.py:66-78` ya documenta ("to_dict
proyecta el drift afuera por construcción").
**How to avoid:** Verificar que ningún sitio de `main_market_data.py` alimente `to_dict()` a
`schema_of` para market-data. `[VERIFIED: grep]` — los sitios de snapshot usan
`_raw_via_request_sync`/`_async` (wire crudo). `to_dict()` está reservado a `len()`/`isinstance`.
**Warning signs:** Un diff en un archivo bajo `.planning/verification/schemas/market-data-client/`.

## Code Examples

### Migración de `MarketDataSnapshot` (SC-2 revocado, D-04)

```python
# packages/market-data-client/src/market_data_client/models.py
@dataclass(frozen=True, slots=True)
class MarketDataSnapshot(SafeModel):
    symbol: str
    market_id: str
    active: bool
    entries: list[str]                 # Phase 36: revoca el widening 33-07 SC-2
    market_data: MarketDataEntries     # Phase 36: modelo Null Object, NUNCA None
    staleness_seconds: float | None    # hoja — D-NO-03, se queda
    received_at: float
    note: str | None = None            # hoja — D-NO-03, se queda
```

Los campos conservan **posición y ausencia de default**, así que `note` no se mueve y ningún
default enmascara una clave ausente (la propiedad que Phase 33 declaró y que sigue valiendo).

### `from_api` tras la retirada del pase

```python
    @classmethod
    def from_api(cls, payload: Any, *, received_at: float = 0.0) -> Self:
        stamped: Any = {**payload, "received_at": received_at} if isinstance(payload, dict) else payload  # fmt: skip
        sink = _decode.current_sink()
        kwargs = _decode.walk_model(cls, stamped, policy=_decode.POLICY, sink=sink)
        kwargs["received_at"] = received_at  # INJECT — skip the walker (D-01)
        return cls(**kwargs)
```

### `LatestRequest` (D-06)

```python
@dataclass(frozen=True, slots=True)
class LatestRequest:
    symbols: list[str]
    marketId: str | None = None
    entries: list[str] = field(default_factory=list)   # revierte el widening

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"symbols": self.symbols}
        if self.marketId is not None:
            out["marketId"] = self.marketId
        if self.entries:                # ← era ``is not None``
            out["entries"] = self.entries
        return out
```

`[VERIFIED: grep]` — ningún call-site del repo pasa `entries=None` a `LatestRequest`, así que el
cambio no rompe mypy en ningún llamador. `test_models.py:183` y `:188` siguen pasando sin edición.

### Delta de imports de `models.py` (F-5)

```python
# ANTES
import dataclasses
import types
from dataclasses import dataclass, fields
from typing import Any, Self, Union, cast, get_args, get_origin

# DESPUÉS
import dataclasses
from dataclasses import dataclass, field
from typing import Any, Self, cast
```

`[VERIFIED: grep de usos]` — `types`/`Union`/`get_args`/`get_origin`/`fields` quedan sin uso;
`dataclasses` (por `asdict` en `to_dict`) y `cast` sobreviven; `field` es nuevo.

### Encadenamiento profundo en el driver (SC-5)

```python
# main_market_data.py, dentro del try de probe_market_data_sync (D-09: todo dentro del try)
        snapshots = client.get_market_data(active=True)
        # SC-5: el driver EJERCE la cadena profunda — si algún eslabón fuera None
        # esto lanzaría, y el probe lo reportaría como finding en vez de pasar.
        deep = [
            (s.symbol, s.market_data.last.price, len(s.market_data.bids), s.market_data.settlement.price)
            for s in snapshots
        ]
        ...
        return ProbeResult(name, "PASS", f"snapshots={len(snapshots)} chained={len(deep)}")
```

Restricciones del driver que el planner debe respetar en estos sitios:
- **Todo post-procesado va DENTRO del `try`** (D-09) — un fallo degrada a finding, nunca a crash.
- **No renombrar probes** — la estabilidad de nombres es un lock desde LIVE-01/REFAC-05.
- **Nunca renderizar una excepción fuera de `_redacted_exc`** — el lock AST AD-30-09-01 marca todo
  segundo renderer; los helpers reciben `detail: str` ya renderizado, nunca la excepción (33-03).
- Los cuatro sitios reales: `probe_market_data_sync` (~825), `probe_latest_sync` (~860),
  `probe_market_data_async` (~1136), y el par async de latest.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `dict[str, Any]` passthrough para sub-estructuras del wire | Modelo tipado con Null Object + alias `@property` | v1.7 (este milestone) | Es el objeto entero de la fase |
| `_mapping_value`/`_apply_mapping_policy` como pase call-site compensatorio | La rama `_is_model` del walker se hace cargo | Phase 36 | El eje mapping desaparece de `market-data-client`; `matriz-client` conserva el suyo legítimamente (Phase 37 decide su destino) |
| `null` sobre eslabón no-opcional → divergencia + typed zero | `null` sobre eslabón no-opcional → instancia vacía, **sin** divergencia (NOBJ-02) | Phase 35 (`CANONICAL_DIGEST` a1f00c82…) | Es la precondición que hace posible SC-2-revocado sin reintroducir ruido |
| `market_data`/`entries`/`staleness_seconds` como `\| None` (widening 33-07) | Revocación **parcial por rol de campo**: eslabones vuelven a required, hojas se quedan `\| None` | Phase 36 | La revocación es por rol (eslabón vs hoja), no un rollback del checkpoint |
| `SafeModel` form B (con pase de mapping) | `SafeModel` form A (walk puro) | Phase 36 | Cambia la fila de market-data en la matriz de semánticas de 29 |

**Deprecated/outdated:**
- `models._mapping_value` / `_apply_mapping_policy` / `_is_mapping` / `_strip_optional` — retirados
  por esta fase; el docstring de `empty()` ya lo anunciaba en presente-futuro (`models.py:259`).
- `test_decode.py::_RequiredMapping` — fixture cuyo único propósito era mantener vivo el contrato
  CR-03 tras SC-2. Sin eje mapping en el paquete, su contrato desaparece (Open Question 1).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | El wire real de `market_data` para `price`/`size`/`date` es siempre numérico (nunca string) — la captura de Phase 33 muestra `int` en todos ellos | Standard Stack / F-3 | Un `price: "10.5"` string produciría una divergencia `type` con typed zero `0.0`. Riesgo bajo y **visible** (divergencia reportada), no silencioso. Phase 39 lo mediría en vivo |
| A2 | Las 10 claves de la captura son el roster completo del vendor | D-02 (decisión del usuario, no asunción mía) | Una clave 11ª llega como `extra` (INFO, **nunca** fatal por decisión firmada de Phase 29). Corrección in-cycle en Phase 39 |
| A3 | `_ENDPOINT_OPTIONAL` sigue siendo la herramienta correcta para suprimir `model-only entries` | Pitfall 7 | Medido `[VERIFIED]` contra los dos baselines committeados; un tercer endpoint con otra forma lo invalidaría |
| A4 | Ningún consumidor **fuera de este repo** depende de `snapshot.market_data` como `dict` | Pitfall 9 / Phase 40 | Es la misma incógnita registrada en STATE para iol 0.2.0 (v1.6 Phase 30 unknown). El paquete ya es 0.5.0 y Phase 40 carga el callout breaking |

## Open Questions

1. **¿Qué pasa con `_RequiredMapping` y los dos tests CR-03 de `test_decode.py:1185-1230`?**
   - **Lo que sabemos:** El fixture es module-local y fue creado por 33-07 **precisamente porque**
     el widening SC-2 dejó al paquete sin ningún modelo shipeado que declarara un mapping
     requerido. Su docstring dice: "la alternativa, borrar las filas, habría retirado un contrato
     vivo porque su ejemplo cambió". Tras Phase 36 el contrato **ya no es vivo**: la maquinaria que
     lo implementaba se retira entera.
   - **Lo que no está claro:** CONTEXT D-05 dice "y sus tests de precondición" sin nombrar estos
     dos. Conservarlos exigiría conservar `_mapping_value` para que haya algo que testear —
     contradicción directa con D-05.
   - **Recomendación:** **Borrar** `_RequiredMapping` y sus dos tests
     (`test_absent_required_mapping_field_...` y `test_strict_mode_raises_on_an_absent_required_...`)
     junto con la maquinaria, y registrar la baja en el SUMMARY nombrando CR-03 como contrato
     retirado con el eje. Conservar `test_mapping_pass_is_silent_under_a_non_dict_payload`
     **retitulado** (p. ej. `test_non_dict_payload_emits_exactly_one_terminal_record`): su
     propiedad real es el **lock 8**, que sobrevive intacto y cuyo set de records `[VERIFIED]` no
     cambia.

2. **¿Se agregan las 3 clases a `market_data_client.__all__` además de `models.__all__`?**
   - **Lo que sabemos:** Sólo `models.__all__` es aseverado automáticamente (WR-02). La tupla
     `_NEW_PUBLIC_NAMES` es curada, así que el paquete `__all__` no falla si se omiten.
   - **Recomendación:** **Sí, re-exportar.** Sin `MarketDataEntries` importable, el consumidor no
     puede anotar una variable con el tipo que la lib devuelve. Agregar los 3 nombres a
     `_NEW_PUBLIC_NAMES` con el comentario `# Phase 36 — market_data tipado (NOBJ-MD-01)`,
     replicando el patrón de las 4 tandas anteriores del mismo archivo. Consecuencia semver
     (aditiva) declarada acá para que Phase 40 la absorba.

3. **¿La `MarketDataEntries` anidada rompe el lock WR-03 de "from_api-override nunca anidado"?**
   - **Lo que sabemos:** `[VERIFIED: razonado sobre el código]` No. El test computa
     `overriding = {MarketDataSnapshot, Symbol}` y `nested_types`, y asevera intersección vacía.
     Phase 36 agrega `{MarketDataEntries, EntryValue, BookLevel}` a `nested_types`; ninguna declara
     `from_api`, así que la intersección sigue vacía.
   - **Recomendación:** Ninguna acción. Es un no-evento — pero conviene que el plan lo diga
     explícitamente, porque el test **cambia de valor computado** sin cambiar de veredicto y un
     ejecutor podría alarmarse.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| CPython | Todo | ✓ | 3.12.11 (venv) | — |
| uv | Runner del workspace | ✓ | 0.9.0+ (`uv run` funcionó) | — |
| pytest + plugins | Suite del paquete | ✓ | 663 tests en 0.99 s | — |
| mypy strict | Criterio 1 de la fase | ✓ | corrió limpio sobre el shape propuesto | — |
| ruff | Job `lint` | ✓ | `check_surface_types.py` corrió: 0 violations | — |
| Red / API `market-data-develop` | **NO requerida** | n/a | — | Esta fase es 100% offline (`pytest_httpx`); la corrida en vivo es Phase 39 |

**Missing dependencies with no fallback:** ninguna.
**Missing dependencies with fallback:** ninguna.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.3+ con pytest-asyncio (`asyncio_mode = "auto"`), pytest-httpx, pytest-cov |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (raíz del monorepo) |
| Quick run command | `uv run pytest packages/market-data-client -q` |
| Full suite command | `uv run pytest -q` (workspace completo, ~1810 tests) |
| **Baseline medido** | **663 passed en 0.99 s** para `market-data-client` `[VERIFIED: ejecutado 2026-08-29]` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| NOBJ-MD-01 | La cadena profunda no lanza con los 4 payloads × 2 superficies (SC-1) | unit + integration (httpx mock) | `uv run pytest packages/market-data-client/tests/test_market_data_chain.py -x` | ❌ Wave 0 — archivo nuevo |
| NOBJ-MD-01 | La cadena compila bajo mypy strict (SC-1) | static | `uv run mypy packages/market-data-client/src packages/market-data-client/tests` | ✅ (job `typecheck`) |
| NOBJ-MD-01 | Las 3 clases existen con la forma y los 6 alias (SC-2) | unit | `uv run pytest packages/market-data-client/tests/test_models.py -k entries -x` | ✅ `test_models.py` (extender) |
| NOBJ-MD-01 | Los alias son invisibles al walker | unit | `uv run pytest packages/market-data-client/tests/test_null_object.py -x` | ✅ (ya lo cubre, sin editar) |
| NOBJ-MD-01 | Las 3 clases entran al roster Null Object (`>= 16` → 19) | unit (parametrizado) | `uv run pytest packages/market-data-client/tests/test_null_object.py -x` | ✅ (automático por introspección) |
| NOBJ-MD-02 | `entries`/`market_data` no admiten `None` en su anotación (SC-2/SC-3) | unit (introspección de hints) | `uv run pytest packages/market-data-client/tests/test_models.py -k field_set -x` | ✅ (extender con aserción de hints) |
| NOBJ-MD-02 | `LatestRequest.entries` default `[]` y `to_dict` omite la clave vacía | unit | `uv run pytest packages/market-data-client/tests/test_models.py -k latest_request -x` | ✅ |
| NOBJ-MD-02 | Fila no-data: `bool(market_data) is False` + `note` poblado, sync y async, strict y no-strict (SC-4) | integration | `uv run pytest packages/market-data-client/tests/test_snapshot_no_data_row.py -x` | ✅ (migrar, NO borrar) |
| NOBJ-MD-02 | Un wrong-type sigue divergiendo y sigue siendo fatal en strict | integration | `uv run pytest packages/market-data-client/tests/test_snapshot_no_data_row.py -k wrong_typed -x` | ✅ |
| NOBJ-MD-02 | La maquinaria de mapping no existe en el paquete (SC-5) | unit (introspección negativa **no vacua**) | `uv run pytest packages/market-data-client/tests/test_models.py -k mapping_machinery -x` | ❌ Wave 0 |
| SC-5 | El hash de `_decode.py` no se movió | gate de CI | `uv run python tools/check_decode_intactness.py` | ✅ |
| SC-5 | El driver consume por encadenamiento profundo | AST / grep | `uv run pytest packages/market-data-client/tests/ -k driver` o assertion en el plan | ❌ Wave 0 (decisión del planner) |

### Sampling Rate

- **Per task commit:** `uv run pytest packages/market-data-client -q` (0.99 s — barato, correrlo
  siempre) + `uv run ruff check packages/market-data-client main_market_data.py`
- **Per wave merge:** `uv run mypy` (src global) + `uv run mypy packages/market-data-client/tests`
  + `uv run python tools/check_decode_intactness.py`
- **Phase gate:** los 4 jobs completos antes de `/gsd-verify-work`:
  1. `uv run ruff check . && uv run ruff format --check . && uv run lint-imports && uv run python tools/check_decode_intactness.py && uv run python tools/check_uniform_structure.py && uv run python tools/check_surface_types.py`
  2. `uv run pre-commit run --all-files`
  3. `uv run mypy` + el loop de tests por paquete
  4. `uv run pytest -q` (workspace completo)

### Wave 0 Gaps

- [ ] `packages/market-data-client/tests/test_market_data_chain.py` — la **matriz de 4 payloads ×
      2 superficies** de SC-1. Ningún archivo existente cubre esto. Debe aseverar, por cada caso:
      (a) la cadena completa no lanza, (b) el set de divergencias, (c) `bool(market_data)`.
      Los 4 casos: wire real (de `get-market-data.json`), `market_data` ausente, `market_data: null`,
      `market_data: {}`. **Falsificación medida disponible** — ver F-1 para los valores esperados.
- [ ] Aserción de "la maquinaria no existe" **no vacua**: `not hasattr(models, "_mapping_value")`
      sólo, es un verde vacuo (pasaría si `models` fuera un módulo vacío). Emparejarla con una
      aserción positiva — p. ej. que `MarketDataSnapshot.from_api` sigue inyectando `received_at`
      y que el roster de `SafeModel` sigue en 19 — siguiendo el precedente 33-07 criterio 4
      (un piso cero se declara con propiedad estructural, nunca con `>= 0`).
- [ ] Lock del driver para SC-5: decidir si el "encadenamiento profundo en sitios reales" se
      asevera por AST (precedente AD-30-09-01) o se declara satisfecho por inspección. **Recomendado:
      AST**, porque el lock existente del driver ya toma un STRING de fuente y es reutilizable
      (precedente 30-09).
- [ ] Helper `_strip_optional` módulo-local en `test_core.py` y `test_decode.py` (3 sitios) —
      prerequisito de las ediciones del censo, no test propio.
- Framework install: **ninguno** — todo presente.

## Security Domain

Esta fase no introduce superficie de seguridad nueva. El registro es explícito, no un salto:

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | La fase no toca el flujo Auth0 client-credentials ni `_state.py` |
| V3 Session Management | no | Sin sesiones; el token cache no se toca |
| V4 Access Control | no | Sin cambios en el mutating-gate (`_ensure_mutation_allowed`); esta fase es read-surface |
| V5 Input Validation | **sí** | El walker `_decode.py` **es** la capa de validación de input, y esta fase la **fortalece**: `market_data` pasa de un `dict[str, Any]` sin validar a 10 campos con tipo declarado y verificado. Se refuerza sin escribir validación nueva |
| V6 Cryptography | no | Ninguna |
| V7 Error Handling & Logging | **sí** | El record de divergencia es de 6 claves planas y **nunca contiene valores** (T-29-22 — los payloads llevan símbolos e identificadores de cuenta). Al tipar `market_data`, los nuevos paths (`.market_data.LA.price`) son **nombres declarados**, no contenido de payload. La única ruta wire→record sigue siendo la clave `extra`, ya neutralizada por `_safe_key` (lock 11) |

### Known Threat Patterns for este stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Fuga de identificadores de cuenta/símbolo por logs de divergencia | Information Disclosure | Ya mitigado: el record no lleva valores (lock 11 + T-29-22). Esta fase **no debe** agregar el valor a ningún record nuevo |
| Clave de payload hostil forjando líneas de log o paths falsos | Tampering | Ya mitigado: `_safe_key` normaliza a `[0-9A-Za-z_-]` y trunca a 64. Sin cambios |
| DoS por payload profundo/enorme | Denial of Service | Sin cambio de perfil: la profundidad de recursión pasa de 1 a 3 niveles sobre un contenedor de 10 campos acotado. `_MAX_SCAN_ENTRIES` del logging sigue vigente |
| Ampliación silenciosa de superficie confiada | Elevation of Privilege | N/A — no hay superficie de mutación tocada; el guard AST de `_ensure_mutation_allowed()` como primer statement debe seguir verde (job `lint`) |

## Sources

### Primary (HIGH confidence — medido/ejecutado en esta sesión)

- `packages/market-data-client/src/market_data_client/_decode.py:417-613` — leído verbatim; ramas
  Union / list / `_is_model` / float / Literal y `walk_model`
- `packages/market-data-client/src/market_data_client/models.py:1-460` — leído verbatim
- `packages/matriz-client/src/matriz_client/models.py:387-428` — patrón de referencia
- `packages/market-data-client/tests/{test_null_object,test_decode,test_core,test_models,test_snapshot_no_data_row,test_public_surface_market_data,test_surface_parity}.py` — leídos en las regiones relevantes
- `verification/safemodel_diff.py:94-160` — recursión del diff SHAPE
- `.planning/verification/schemas/market-data-client/{get-market-data,get-latest}.json` — wire real
- **Ejecución F-1/F-2/F-3/F-6:** script de prueba con el shape propuesto contra los 4 payloads +
  `mypy --strict` + `diff_safemodel_bidirectional` + `_perturb`
- **Ejecución baseline:** `uv run pytest packages/market-data-client -q` → 663 passed
- **Ejecución gate:** `uv run python tools/check_surface_types.py` → 0 violations
- `.planning/{ROADMAP,REQUIREMENTS,STATE}.md`, `36-CONTEXT.md`, `./CLAUDE.md`, `pyproject.toml`,
  `.github/workflows/ci.yml`, `tools/check_decode_intactness.py`

### Secondary (MEDIUM confidence)

- `.planning/STATE.md` § Accumulated Context — decisiones de Phases 29-35 citadas por número; son
  registro del proyecto, no medición de esta sesión

### Tertiary (LOW confidence)

- Ninguna. **No se consultó ninguna fuente externa**: la fase es enteramente interna al repo y no
  hay librería, versión ni API de terceros que verificar. No se ejecutó `research-plan` porque no
  había ninguna pregunta cuya respuesta viviera fuera de este código.

## Key Measured Findings (F-1 … F-6)

**F-1 — La matriz de 4 payloads produce CERO divergencias y CERO raises.** `[VERIFIED: ejecutado]`

| Caso | `entries` | `bool(market_data)` | `last.price` | `bids[0].price` | `offers` | `settlement.price` | `close.price` | `open_interest.price` | divergencias |
|------|-----------|---------------------|--------------|-----------------|----------|--------------------|---------------|------------------------|--------------|
| wire real | `['BI']` | `True` | `10.0` | `10.0` | `[BookLevel(price=11.0, size=2)]` | `10.0` | `9.0` | `None` | **0** |
| `market_data` ausente | `['BI']` | `False` | `None` | n/a (`bids == []`) | `[]` | `None` | `None` | `None` | **0** |
| `market_data: null` | `[]` | `False` | `None` | n/a | `[]` | `None` | `None` | `None` | **0** |
| `market_data: {}` | `['BI']` | `False` | `None` | n/a | `[]` | `None` | `None` | `None` | **0** |

**F-2 — `mypy --strict` acepta el conjunto completo sin `type: ignore`.** `[VERIFIED: ejecutado]`
Los únicos 2 errores reportados fueron del andamiaje de captura de logs del propio script de
prueba (`list[tuple]` sin args, `def emit` sin anotar), ninguno de los modelos, propiedades o
cadenas de acceso.

**F-3 — El `int` del wire se ensancha a `float` en SILENCIO.** `[VERIFIED: _decode.py:535-536 +
ejecución]` `walk_field` hace `if isinstance(value, int | float): return float(value)` **antes** de
consultar `scalar_passthrough`, así que `price: 10` (int, como manda el wire real) llega como
`10.0` sin emitir nada. Declarar `price: float | None` no fabrica divergencias. Contrastar con
`bool`, donde un `int` **sí** diverge (medido en 31-05) — la asimetría es real y está del lado
favorable acá.

**F-4 — Censo de la maquinaria de mapping: 13 call-sites, 5 fuera de `models.py`.**
`[VERIFIED: grep exhaustivo]` De los 5 externos, **1 se borra, 4 se editan**. Tabla completa en
"Runtime State Inventory". Los rangos de línea de CONTEXT D-05 sobre-cubren.

**F-5 — Delta de imports de `models.py`.** `[VERIFIED: grep de usos]` Salen `types`, `Union`,
`get_args`, `get_origin`, `fields`; entra `field`; quedan `dataclasses`, `dataclass`, `Any`,
`Self`, `cast`.

**F-6 — El SHAPE-diff del driver queda limpio contra el wire real; la fila no-data emite
`model-only entries`, que `_ENDPOINT_OPTIONAL` ya suprime.** `[VERIFIED: ejecutado]`
`diff_safemodel_bidirectional(item_real, Snapshot)` → `[]`; sobre la fila no-data →
`[('', 'model-only', 'entries')]`. `market_data` **no** aparece porque la clave está presente
(con `null`). Además: `_perturb` (el helper de `test_null_object.py`) perturba correctamente las 3
clases nuevas **sin necesitar rama nueva** — `MarketDataEntries` engancha en la rama `list` (`BI`
es el primer campo), `BookLevel`/`EntryValue` en la rama `cur is None`.

**F-7 — Roster actual = 16 clases exactas.** `[VERIFIED: ejecutado]` `AddHolidaysResult,
CalendarConfig, CalendarConfigPreview, CalendarDay, DeleteHolidayResult, FeedIngestor, FeedMarket,
FeedPipeline, Health, HealthAuth, HealthFeed, Instrument, MarketDataSnapshot, PreviewMarket,
Segment, Symbol`. Tras la fase: **19**. El bound `>= 16` de `test_null_object.py:226` aguanta sin
edición.

## Metadata

**Confidence breakdown:**

- Standard stack: **HIGH** — no hay stack que elegir; todo verificado contra `pyproject.toml` y ejecución
- Architecture: **HIGH** — el patrón está shippeado en matriz y la adaptación se ejecutó y midió
- Pitfalls: **HIGH** para 1,2,3,5,6,7,8 (medidos o grepeados); **MEDIUM** para 4 y 9 (razonados
  sobre docstrings y grep, no ejecutados)
- Validation architecture: **HIGH** — baseline de 663 tests y comandos de gate ejecutados
- Security: **HIGH** — sin superficie nueva; los locks citados están en código

**Research date:** 2026-08-29
**Valid until:** indefinido mientras `_decode.py` conserve `CANONICAL_DIGEST` a1f00c82… — toda la
investigación se apoya en el comportamiento de ese walker. Si Phase 37/38 lo movieran (no deberían;
Phase 35 fue la única fase transversal), re-medir F-1 y F-3.
