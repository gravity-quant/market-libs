# Phase 36: `market-data-client` — `market_data` tipado + revocación de la Fase 33 — Pattern Map

**Mapped:** 2026-08-29
**Files analyzed:** 8 (1 source modificado + 1 `__init__` + 5 test files modificados + 1 test file nuevo + 1 driver)
**Analogs found:** 8 / 8 (7 exactos, 1 role-match)

> Esta fase **no crea archivos de source nuevos**. Todo el trabajo es (a) declarativo dentro de
> `models.py`, (b) de retirada de la maquinaria de mapping, (c) de migración de aserciones.
> El único archivo nuevo es un test (`test_market_data_chain.py`).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `packages/market-data-client/src/market_data_client/models.py` (+3 clases: `BookLevel`, `EntryValue`, `MarketDataEntries`) | model | transform (wire→typed) | `packages/matriz-client/src/matriz_client/models.py:387-428` (`MarketDataLevel`/`MarketDataEntryValue`/`MarketDataSnapshot`) | exact (patrón), adaptación obligatoria por base |
| ↳ nested-model field no-opcional (`MarketDataSnapshot.market_data: MarketDataEntries`) | model | transform | `models.py:1057-1073` (`Health.auth: HealthAuth`) — analog **local** | exact |
| ↳ `@property` alias sobre frozen+slots | model | transform | `packages/market-data-client/tests/test_null_object.py:191-201` (`_AliasShaped.last`) | exact (forma ya pineada) |
| ↳ `MarketDataSnapshot.from_api` tras retirar el pase | model | transform | `models.py:211-223` (`SafeModel.from_api`, form A tras el colapso) | exact |
| ↳ `LatestRequest` (D-06) | model (serialize-OUT) | request-response | `models.py:463-505` (`NewSymbol`/`NewSymbols`, mismo idioma `to_dict` con drop condicional) | role-match |
| `packages/market-data-client/src/market_data_client/__init__.py` (+3 re-exports) | config / barrel | — | el propio bloque `from .models import (...)` + `__all__` (`__init__.py:75-135`) | exact |
| `packages/market-data-client/tests/test_market_data_chain.py` (**NUEVO**) | test (integration) | request-response | `packages/market-data-client/tests/test_snapshot_no_data_row.py` | exact |
| `packages/market-data-client/tests/test_snapshot_no_data_row.py` (migración D-07) | test (integration) | request-response | sí mismo (edición in-place) | exact |
| `packages/market-data-client/tests/{test_core,test_decode}.py` (helper `_strip_optional` local ×3) | test (unit) | transform | `packages/market-data-client/tests/test_null_object.py:33-38` (helper módulo-local deliberado) | exact |
| `packages/market-data-client/tests/{test_models,test_decode,test_null_object}.py` (migración de aserciones) | test (unit) | transform | Pattern 3 de RESEARCH (`is None` → veracidad) | exact |
| `main_market_data.py` (encadenamiento profundo, SC-5) | driver / entry point | request-response | `main_market_data.py::probe_market_data_sync` (~825) y su espejo async (~1136) | exact |

---

## Pattern Assignments

### `models.py` — las 3 clases nuevas (model, transform)

**Analog primario:** `packages/matriz-client/src/matriz_client/models.py:387-428` — VERIFICADO, es
la implementación shippeada del patrón Null Object contenedor+hijos.

**Excerpt a copiar (patrón, NO import — C-2 / D-NO-06)** — `matriz_client/models.py:387-428`:

```python
@dataclass(frozen=True)
class MarketDataLevel(_SafeModel):
    """Price level inside an order-book entry (``BI`` / ``OF``)."""

    price: float | None = None
    size: int | None = None


@dataclass(frozen=True)
class MarketDataEntryValue(_SafeModel):
    """Scalar market-data entry (``LA``, ``SE``, ``OI`` …) per §8.1."""

    price: float | None = None
    size: int | None = None
    date: int | None = None


@dataclass(frozen=True)
class MarketDataSnapshot(_SafeModel):
    BI: list[MarketDataLevel] = field(default_factory=list)
    OF: list[MarketDataLevel] = field(default_factory=list)
    LA: MarketDataEntryValue = field(default_factory=MarketDataEntryValue.empty)
    SE: MarketDataEntryValue = field(default_factory=MarketDataEntryValue.empty)
    OI: MarketDataEntryValue = field(default_factory=MarketDataEntryValue.empty)
    CL: MarketDataEntryValue = field(default_factory=MarketDataEntryValue.empty)
    OP: float | None = None
    HI: float | None = None
    LO: float | None = None
    TV: float | None = None
    IV: float | None = None   # ← NO copiar (D-02)
    EV: float | None = None   # ← NO copiar
    NV: float | None = None   # ← NO copiar
    ACP: float | None = None  # ← NO copiar
```

**Delta obligatorio contra el analog** (no negociable, ver RESEARCH tabla Pattern 1):

| Eje | matriz (analog) | market-data (destino) |
|-----|-----------------|------------------------|
| Decorador | `@dataclass(frozen=True)` | `@dataclass(frozen=True, slots=True)` (C-6 — **todas** las 22 clases de `models.py` lo llevan) |
| Base | `_SafeModel` | `SafeModel` local (`models.py:204`) |
| Roster | 14 campos | **10** (`BI CL HI LA LO OF OI OP SE TV`, orden wire — D-02) |
| Nombres | `MarketDataLevel`/`MarketDataEntryValue`/`MarketDataSnapshot` | `BookLevel`/`EntryValue`/`MarketDataEntries` |
| Alias | ninguno | 6 `@property` (D-NO-05) |

> ⚠️ `field` **no está importado hoy** en `market-data/models.py` (`models.py:85` importa
> `dataclass, fields`). Es la trampa mecánica de Pitfall 3.

**Analog de campo nested no-opcional (local, mismo módulo)** — `models.py:1057-1073`:

```python
@dataclass(frozen=True, slots=True)
class Health(SafeModel):
    """...
    No ``| None`` field. :attr:`auth` is declared as the non-optional nested
    :class:`HealthAuth`, so an absent ``auth`` key yields the ZERO-VALUED
    ``HealthAuth`` plus a ``missing`` divergence record — never ``None``...
    """

    status: str
    auth: HealthAuth
```

Esta es la prueba local de que `market_data: MarketDataEntries` (sin `| None`, sin default) es la
forma nativa del paquete. **Nota semántica:** el docstring de `Health` dice "plus a ``missing``
divergence record" — eso es **pre-Phase-35**. Tras NOBJ-02 el colapso es silencioso
(RESEARCH F-1: 0 divergencias). No copiar esa frase del docstring al bloque nuevo.

**Docstring provenance pattern** — copiar el idioma de `HealthAuth` (`models.py:1041-1050`):
`"Live-capture provenance: field set taken verbatim from .planning/verification/schemas/..."`.
Para `MarketDataEntries` la fuente es `get-market-data.json` (captura Phase 33).

---

### `models.py` — `@property` alias (model, transform)

**Analog:** `packages/market-data-client/tests/test_null_object.py:191-201` — la forma **exacta**
ya está fijada por el fixture de criterio 5 de Phase 35.

```python
@dataclass(frozen=True, slots=True)
class _AliasShaped(SafeModel):
    """The exact shape Phase 36 introduces: wire fields + a read-only alias."""

    LA: _Leaf
    BI: list[_Leaf]

    @property
    def last(self) -> _Leaf:
        """Human-facing alias over the wire-named field (D-16)."""
        return self.LA
```

Copiar literalmente esa forma ×6: `last→LA`, `bids→BI`, `offers→OF`, `settlement→SE`,
`close→CL`, `open_interest→OI`. Sin caché, sin `functools.cached_property` (imposible sobre
`slots=True` y prohibido por D-03).

Tipos de retorno: `bids`/`offers` → `list[BookLevel]`; los otros 4 → `EntryValue`.

---

### `models.py` — `from_api` / `empty` tras el colapso form B → form A

**Analog:** `SafeModel.from_api` / `SafeModel.empty` del propio módulo, **una vez removida** la
llamada al pase. Estado actual (`models.py:211-223` y `:266-268`):

```python
    @classmethod
    def from_api(cls, payload: Any) -> Self:
        sink = _decode.current_sink()
        kwargs = _decode.walk_model(cls, payload, policy=_decode.POLICY, sink=sink)
        _apply_mapping_policy(          # ← BORRAR (junto al comentario lock-8 de :216-219)
            cls, kwargs, sink=sink if isinstance(payload, dict) else _decode.SILENT_SINK
        )
        return cls(**kwargs)
```

Destino (form A): `return cls(**walk_model(...))`, tres líneas.

**`MarketDataSnapshot.from_api`** — `models.py:414-426`. Borrar SOLO `:417-424`
(comentario CR-03 + llamada). **CONSERVAR `:425`**:

```python
        kwargs["received_at"] = received_at  # INJECT — skip the walker (D-01)
```

Es Pitfall 5: la línea es adyacente al bloque a borrar y el comentario CR-03 la envuelve visualmente.

**Delta de imports exacto** — `models.py:83-86`:

```python
# ANTES (verbatim en el archivo hoy)
import dataclasses
import types
from dataclasses import dataclass, fields
from typing import Any, Self, Union, cast, get_args, get_origin

# DESPUÉS
import dataclasses
from dataclasses import dataclass, field
from typing import Any, Self, cast
```

---

### `models.py` — `MarketDataSnapshot` (revocación D-04)

Estado actual (`models.py:374-381`):

```python
    symbol: str
    market_id: str
    active: bool
    entries: list[str] | None
    market_data: dict[str, Any] | None
    staleness_seconds: float | None
    received_at: float
    note: str | None = None
```

Destino: `entries: list[str]`, `market_data: MarketDataEntries` — **sin default explícito**, misma
posición. `staleness_seconds` y `note` intactos (hojas, D-NO-03).

**Docstring pattern a espejar (D-08):** el bloque `**BREAKING since 0.5.0 (Phase 33, SC-2).**`
de `models.py:350-371` es el modelo exacto de cómo este repo documenta un cambio de anotación
citando el checkpoint que lo decidió. Phase 36 escribe el bloque simétrico ("revoca el widening
33-07 SC-2 por rol de campo: eslabones vuelven a required, hojas se quedan `| None`"), no lo borra.

**Prosa adicional a reescribir (Pitfall 4):** `models.py:56-64` (bloque CR-03 del docstring de
módulo), `models.py:245-259` (el bloque "form B ... y Phase 36 retires this paquete's mapping
machinery outright" — está escrito en futuro y esta fase lo cumple),
`test_null_object.py:21-24` (declaración de pertenencia a form B) y
`test_null_object.py:256-262` (docstring de `test_empty_emits_nothing` que explica el pase).

---

### `models.py` — `LatestRequest` (D-06)

Estado actual (`models.py:439-450`):

```python
    symbols: list[str]
    marketId: str | None = None
    entries: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"symbols": self.symbols}
        if self.marketId is not None:
            out["marketId"] = self.marketId
        if self.entries is not None:      # ← pasa a ``if self.entries:``
            out["entries"] = self.entries
        return out
```

Destino: `entries: list[str] = field(default_factory=list)` + `if self.entries:`. Analog de idioma
serialize-OUT: `NewSymbol`/`NewSymbols` (`models.py:463-505`), mismo `to_dict` con drop condicional.

**No tocar `_core.build_latest_request(..., entries: str | None)`** — Pitfall 8, es otro `entries`
(query param de GET). Cualquier diff en `_core.py` es señal de error.

---

### `__init__.py` (barrel) — +3 re-exports

**Analog:** el propio archivo. El bloque `from .models import (...)` (`__init__.py:~70-96`) y el
`__all__` (`:101-135`) están **ambos en orden alfabético estricto**. Insertar:

- import block: `BookLevel` (antes de `CalendarConfig`), `EntryValue` (tras `DeleteHolidayResult`),
  `MarketDataEntries` (antes de `MarketDataSnapshot`).
- `models.__all__` (`models.py:~90-115`): los mismos 3, alfabéticos. **Obligatorio** — WR-02 lo
  asevera por introspección (Pitfall 6).
- `market_data_client.__all__` (`:101+`): los mismos 3 (recomendado, Open Question 2).

---

### `tests/test_market_data_chain.py` (**archivo nuevo** — test, integration)

**Analog:** `packages/market-data-client/tests/test_snapshot_no_data_row.py` — es el precedente
exacto: fixtures de payload a nivel módulo + `httpx_mock` + par sync/async + variante strict.

**Header + imports** (`test_snapshot_no_data_row.py:29-37`):

```python
from __future__ import annotations

from typing import Any

import pytest
from pytest_httpx import HTTPXMock

import market_data_client
from market_data_client import MarketDataDecodeError, aio
```

**Fixture de payload a nivel módulo** (`:41-60`) — el idioma con comentario de procedencia:

```python
# ``GET /marketdata/latest`` for a symbol the feed never delivered — the exact
# shape of the committed get-latest.json baseline. Identifiers synthesised.
_NO_DATA_ROW: dict[str, Any] = {
    "symbol": "AAA1",
    ...
}
```

**Par sync/async (C-3)** — copiar la estructura exacta de `:63-93`; el async es un espejo con
docstring `"""Async twin of :func:`...` (C-3)."""`:

```python
def test_no_data_row_keeps_its_nulls(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(method="GET", json=[_NO_DATA_ROW])
    rows = market_data_client.client._get_default().get_latest(symbol="AAA1")
    assert len(rows) == 1
    ...


async def test_no_data_row_keeps_its_nulls_async(httpx_mock: HTTPXMock) -> None:
    """Async twin of :func:`test_no_data_row_keeps_its_nulls` (C-3)."""
    httpx_mock.add_response(method="GET", json=[_NO_DATA_ROW])
    rows = await aio._get_default().get_latest(symbol="AAA1")
```

**Variante strict** (`:96-128`) — el idioma del context manager:

```python
    with market_data_client.Client(
        base_url="https://market-data-develop.test/api",
        token="test-token",
        token_expires_at=9_999_999_999.0,
        strict_decode=True,
    ) as client:
        rows = client.get_latest(symbol="AAA1")
```

Y su espejo `async with aio.AsyncClient(...)`. La matriz SC-1 = 4 payloads × 2 superficies; los
valores esperados por celda están en RESEARCH F-1 (tabla), no re-derivarlos.

---

### `tests/test_snapshot_no_data_row.py` (migración D-07)

**Analog:** Pattern 3 de RESEARCH. Sitios exactos verificados:

| Línea | Actual | Destino |
|-------|--------|---------|
| `:71` `:88` `:113` `:128` | `row.entries is None` / `rows[0].entries is None` | `== []` |
| `:72` `:89` | `row.market_data is None` | `bool(row.market_data) is False` |
| `:73` `:90` | `row.staleness_seconds is None` | **SIN CAMBIO** (hoja) |
| `:139` | `rows[0].market_data == {"BI": [{"price": 10, "size": 1}]}` | `rows[0].market_data.bids[0].price == 10.0` (nota: `10` int → `10.0` float, F-3) — **no listado en D-07**, migrar igual |

**Docstring del módulo** (`:1-27`): reescribir citando la revocación del checkpoint 33-07 SC-2 y
`.future_plans/api-tipada-null-objects.md`, conservando el idioma de trazabilidad de findings
(`F-72`/`F-92` …) que ya usa.

---

### `tests/{test_core,test_decode}.py` — helper `_strip_optional` módulo-local

**Analog:** `packages/market-data-client/tests/test_null_object.py:33-38` — el repo documenta
explícitamente el helper local como deliberado (no hay paquete compartido, por diseño).

Copiar el cuerpo de 6 líneas desde `models.py:118-124` a los 3 archivos de test que lo necesitan
(`test_core.py:1174`, `test_core.py:1453-1454`, `test_decode.py:1373`):

```python
def _strip_optional(tp: Any) -> Any:
    """Return ``T`` from ``T | None`` / ``Optional[T]``; pass through otherwise."""
    if get_origin(tp) in (Union, types.UnionType):
        args = [a for a in get_args(tp) if a is not type(None)]
        if len(args) == 1:
            return args[0]
    return tp
```

> ⚠️ **Nunca borrar por rango de líneas** (Pitfall 1). El censo autoritativo por call-site está en
> RESEARCH § "Runtime State Inventory" — 13 sitios, **1 borrado limpio**
> (`test_decode.py::test_no_mapping_carrying_model_is_ever_a_nested_field_type`), el resto
> ediciones quirúrgicas. Los rangos de CONTEXT D-05 sobre-cubren y arrastrarían T-31-17 y WR-03.

---

### `main_market_data.py` (driver, request-response) — SC-5

**Analog:** el propio `probe_market_data_sync` (`main_market_data.py:823-855`) y su espejo async
(`:1136+`). Forma verificada:

```python
@probe_context(endpoint=_ENDPOINT_TEMPLATES["get_market_data"], surface="sync")
def probe_market_data_sync(client: Client) -> ProbeResult:
    """Market-data read sync: happy-path + SHAPE-diff (Snapshot) + snapshot."""
    name = "market_data_sync"
    base_url = client._state.base_url
    try:
        snapshots = client.get_market_data(active=True)
        # ... TODO post-procesado va DENTRO del try (D-09)
        return ProbeResult(name, "PASS", f"snapshots={len(snapshots)}")
    except Exception as exc:  # D-09
        return _finding_for_exc(exc, name=name, surface="sync", base_url=base_url)
```

Insertar el encadenamiento profundo inmediatamente tras `snapshots = ...`, **dentro del `try`**, y
extender el string de `ProbeResult` (`f"snapshots={len(snapshots)} chained={len(deep)}"`).

Locks del driver que la edición debe respetar:
- Todo post-procesado dentro del `try` (D-09) — el idioma `# D-09:` ya aparece en los 4 sitios.
- **No renombrar probes** (`name = "market_data_sync"`) — lock LIVE-01/REFAC-05.
- Nunca renderizar una excepción fuera de `_redacted_exc` (lock AST AD-30-09-01).
- 4 sitios: `probe_market_data_sync` (~825), `probe_latest_sync` (~857),
  `probe_market_data_async` (~1136), y el par async de latest.

**`_ENDPOINT_OPTIONAL` (`main_market_data.py:115`) — NO TOCAR.** Verificado (Pitfall 7 / F-6):
`diff_safemodel_bidirectional` sobre la fila no-data devuelve `[('', 'model-only', 'entries')]`;
sacar `entries` del frozenset fabricaría un finding SHAPE falso por corrida. Esto **resuelve** el
ítem abierto de "Claude's Discretion" de CONTEXT.

---

## Shared Patterns

### Declaración de modelo (aplica a las 3 clases nuevas)
**Fuente:** las 22 clases de `packages/market-data-client/src/market_data_client/models.py`
**Forma invariante:** `@dataclass(frozen=True, slots=True)` + herencia de `SafeModel` +
campos wire-verbatim + docstring con `"""Una línea. (Phase N, D-XX)."""` + bloque de procedencia.
Sin `received_at` (las 3 son sub-estructuras, no snapshots de primera clase).

### Construcción tolerante
**Fuente:** `models.py:211-223` (`SafeModel.from_api`) / `:266-268` (`empty`)
**Aplica a:** las 3 clases nuevas — **no declaran `from_api` propio**. Heredan el de `SafeModel`.
Esto es lo que mantiene vacía la intersección del lock WR-03 (Open Question 3: no-evento).

### Par sync/async en tests (C-3)
**Fuente:** `test_snapshot_no_data_row.py:63-93`, `:96-128`
**Aplica a:** todo test nuevo de superficie. El async lleva docstring
`"""Async twin of :func:`...` (C-3)."""` y usa `aio._get_default()` / `aio.AsyncClient`.

### Helper de test módulo-local en vez de import compartido
**Fuente:** `test_null_object.py:33-38`
**Aplica a:** `test_core.py` (×2 sitios) y `test_decode.py` (×1) tras retirar `_strip_optional`.

### Orden alfabético estricto en superficies públicas
**Fuente:** `models.__all__` (`models.py:90-115`), `__init__.py` import block + `__all__` (`:75-135`)
**Aplica a:** los 3 nombres nuevos en los 3 rosters.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| — | — | — | Ninguno. Los 8 archivos tienen analog directo. |

Casos con analog **parcial** (el planner debe adaptar, no copiar):

| Elemento | Analog más cercano | Qué falta |
|----------|--------------------|-----------|
| Aserción negativa **no vacua** de "la maquinaria no existe" (Wave 0 gap) | precedente 33-07 criterio 4 (propiedad estructural, nunca `>= 0`) | No hay un test existente de esta forma en el paquete; emparejar `not hasattr(models, "_mapping_value")` con una aserción positiva (roster == 19, `received_at` sigue inyectándose) |
| Lock AST del driver para SC-5 | `main_market_data.py` ya lleva un lock que toma un STRING de fuente (precedente 30-09 / AD-30-09-01) | Reutilizable, pero la decisión AST-vs-inspección es del planner |
| `field(default_factory=...)` en `market-data/models.py` | **ninguno local** — grep confirma 0 ocurrencias hoy | El único ejemplo del workspace es matriz (`models.py:413-420`), sin `slots=True`. Verificado en RESEARCH que `default_factory` + `frozen+slots` funciona |

---

## Metadata

**Analog search scope:** `packages/market-data-client/{src,tests}/`, `packages/matriz-client/src/`,
`main_market_data.py`
**Files scanned:** 7 (leídos en regiones targeted; `models.py` de market-data en 3 rangos
no solapados)
**Pattern extraction date:** 2026-08-29
**Precondición:** todo apoyado en `_decode.py` con `CANONICAL_DIGEST a1f00c82…` — esta fase **no
toca `_decode.py`** (criterio 5).
