# Phase 43: `market-data-client` — forma de `Instrument`/`Segment` + 5 claves `extra` tipadas - Pattern Map

**Mapped:** 2026-08-31
**Files analyzed:** 5 fuente + 8 de test (13 sitios de edición; 0 archivos nuevos)
**Analogs found:** 13 / 13 (todos los cambios tienen precedente in-package)

> Esta fase **no crea ningún archivo nuevo**. Todo el trabajo son ediciones a archivos
> existentes, y para cada edición existe un precedente verbatim dentro del mismo paquete.
> Por eso la tabla de clasificación mapea *sitios de edición*, no archivos nuevos.
> RESEARCH.md §"Mapa completo de sitios afectados" tiene el inventario de anclas de línea;
> este documento aporta **el código exacto a copiar**.

---

## File Classification

### Fuente

| Sitio a modificar | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `models.py:786-800` — `Instrument` (D-01…D-05) | model | transform (wire→dataclass) | `models.py:816-901` (`Symbol`) | exact — mismo archivo, mismo problema (alias camelCase + campos wire-only) |
| `models.py:802-813` — `Segment` (D-06) | model | transform | `models.py:904-931` (`CalendarDay`, remoción no-breaking A1/A2) | exact |
| `models.py:869-876` — `Symbol.note` (D-10) | model | transform | `models.py:874-876` (`created_at`/`updated_at: str \| None = None`, mismo modelo) | exact |
| `models.py:1263-1303` — `FeedSubscription` nuevo + 3 campos de `FeedIngestor` (D-08/D-09) | model (nested) | transform | `models.py:1229-1260` (`FeedPipeline`) y `:1195-1226` (`FeedMarket`) | exact |
| `models.py:1306-1343` — `HealthFeed.symbols_never_delivered` (D-11) | model | transform | `models.py:1338-1340` (`active_symbols`/`symbols_with_data: int`, mismo modelo) | exact |
| `models.py:95-123` — `__all__` (S4) | config/export | — | entrada `"FeedPipeline"` (`:105`) | exact |
| `__init__.py:72-99` + `:104-…` — import + `__all__` (S5) | config/export | — | entradas `FeedMarket`/`FeedPipeline` (`:81-82`, `:115-116`) | exact |
| `_core.py:1042-1051` — docstring de `parse_segments_response` (S6/D-14) | service (parser) | transform | docstring de `parse_calendar_response` post-reconciliación | role-match |
| `main_market_data.py:1541-1542` — `.marketSegmentId` → `.segment` (S7) | script/driver | batch | `main_market_data.py:1538-1544` (el propio bloque `try/except`) | exact (2 líneas, sin lógica) |

### Tests

| Sitio a modificar | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `test_reference_models.py:41-54` — valores viejos (T1/T2) | test (unit) | transform | `test_calendar_config_from_api_populated` (`:130-158`) | exact |
| **NUEVO** `test_instrument_field_set_matches_reconciled_wire` (Wave 0) | test (unit) | transform | `test_calendar_config_field_set_matches_reconciled_wire` (`:161-180`) **y** `test_symbol_field_set_matches_reconciled_wire` (`:211-228`) | exact |
| **NUEVO** `test_segment_field_set_matches_reconciled_wire` (Wave 0) | test (unit) | transform | ídem | exact |
| **NUEVO** los 2 tests de alias de `Instrument` (D-04) | test (unit) | transform | `test_symbol_market_id_alias_mirrors_wire_snake_case` (`:262-269`) + `test_symbol_explicit_camel_case_payload_key_still_wins` (`:272-277`) | exact |
| `test_reference_models.py:219-228` — field-set de `Symbol` gana `"note"` (T3) | test (unit) | transform | el propio test | exact |
| `test_reference_core.py:167-190` (T4/T5) | test (unit) | request-response | `test_reference_core.py:211-213` (contrato "valores sintéticos, key-sets reales") | exact |
| `test_reference_client.py` / `test_reference_async_client.py` (T6/T7) | test (unit, gemelos) | request-response | uno es el analog del otro | exact |
| `test_decode.py:664-689`, `:1339-1360` (T8/T9/T10) | test (unit) | event-driven (log sink) | `_from_api(factory, caplog, payload)` helper local | exact |
| `test_core.py:1125-1150`, `:1183-1199` (T11/T13/T14) | test (unit) | event-driven | `_CAPTURED_HEALTH_FEED` + `_from_api` (`:1043-1051`) | exact |
| **NUEVO** `_MEASURED_HEALTH_FEED_43` + `_keys_recursive` + test de subconjunto (D-13) | test (fixture + unit) | transform | `_CAPTURED_HEALTH_FEED` (`test_core.py:962-1004`) + su docstring de provenance (`:939-944`) | role-match (el helper de subconjunto es genuinamente nuevo) |
| `test_public_surface_market_data.py:102-121` (T12) | test (unit) | — | el propio test (sólo requiere `FeedSubscription` en `models.__all__`) | exact — **no se edita**, se satisface desde S4 |
| `test_reference_envelope_unwrap.py:65-68` — aserciones de valor (criterio 2) | test (unit) | request-response | `test_bare_list_bodies_still_parse` (`:120-139`) | exact |

---

## Pattern Assignments

### `models.py` — `Instrument` (model, transform) · D-01…D-05

**Analog:** `models.py:816-901` (`Symbol`) — el precedente D-22 completo.

**Excerpt 1 — declaración de campos con el alias deprecado y el bloque de defaults al final**
(`models.py:869-876`, verbatim):

```python
    symbol: str
    marketId: str
    active: bool
    id: int = 0
    market_id: str = ""
    created_at: str | None = None
    updated_at: str | None = None
    received_at: str | None = None
```

Nota load-bearing para `Instrument`: aquí `market_id` tiene default porque cae en el bloque
posterior a `id: int = 0`. En `Instrument` **no hay ningún campo con default hoy**, así que
`market_id: str` va **sin** default y `active: bool | None = None` (D-03) es el único con
default y debe ir **último** (Pitfall 5 — un orden mal puesto revienta la colección de pytest
entera en tiempo de import, no un test).

**Excerpt 2 — el override `from_api` del alias aditivo, los 4 elementos load-bearing**
(`models.py:878-901`, verbatim — copiar entero, incluidos los tres comentarios justificativos):

```python
    @classmethod
    def from_api(cls, payload: Any) -> Self:
        """Build a ``Symbol``, mirroring the wire ``market_id`` into ``marketId``.

        The only :class:`SafeModel` subclass that pre-processes its payload. The
        wire never sends ``marketId``; without this the deprecated alias would stay
        ``""`` forever and silently contradict :attr:`market_id`. An explicit
        ``marketId`` in the payload (a hand-built dict, an older fixture) still
        wins — the mirror only FILLS an absent key, it never overwrites.

        Phase 29 (``29-SEMANTICS-MATRIX.md`` Section 3(b)): the mirror runs
        BEFORE the walker sees the payload, which is what keeps extra-key
        reporting correct. After the mirror ``marketId`` is a declared field
        with a present key, so no ``extra`` record fires for it — right, because
        the client synthesized that key, the vendor did not send it.
        """
        if isinstance(payload, dict) and "marketId" not in payload and "market_id" in payload:
            payload = {**payload, "marketId": payload["market_id"]}
        # Explicit two-arg ``super()``: ``@dataclass(slots=True)`` REBUILDS the
        # class, so the implicit ``__class__`` cell captured by a zero-arg
        # ``super()`` still points at the pre-slots class and raises
        # ``TypeError: obj must be an instance or subtype of type``. The module
        # global ``Symbol`` is rebound to the slots class, so naming it works.
        return super(Symbol, cls).from_api(payload)
```

**Cómo adaptar:** sustituir `Symbol` → `Instrument` en la firma del `super()` de dos argumentos
y en el docstring; el cuerpo del `if` es idéntico carácter por carácter. **No** cambiar a
`super()` de cero argumentos (Pitfall 4).

**Excerpt 3 — patrón de docstring de provenance + argumento de no-breaking para la remoción de
`instrumentType`** (`models.py:917-921`, `CalendarDay`, verbatim):

```
    The previously declared ``date`` / ``marketId`` / ``isBusinessDay`` fields exist
    NOWHERE on the wire — they were the PROVISIONAL A1/A2 guess. Retyping them is
    treated as a minor, NON-breaking change (D-13): ``parse_calendar_response``
    iterated the envelope's keys instead of ``days[]``, so no released consumer could
    ever have read a populated instance.
```

Es la prosa exacta a re-escribir para D-05 (`instrumentType`) y para D-06 (los tres campos de
`Segment`), cambiando la razón por la que ningún consumidor liberado pudo leer un valor poblado
(en `Segment` es "el key-set del wire y el declarado eran DISJUNTOS", no el bug del parser).

**Qué NO copiar de `Symbol`:** el campo `received_at`. `Instrument` es reference data unstamped
(D-05 de la Phase 23) y `test_reference_models_have_no_received_at` (`:183-190`) lo pinnea sobre
todo `_ALL_MODELS` excepto `Symbol`.

---

### `models.py` — `Segment` (model, transform) · D-06

**Analog:** `models.py:934-958` (`CalendarConfig`) — reemplazo completo de un shape provisional
A1/A2 por el shape medido, con el docstring que documenta la remoción.

Estructura a copiar: docstring con (1) endpoint, (2) provenance de la lectura medida, (3) qué se
removió y por qué es no-breaking, (4) la nota "unstamped (D-05)". Luego los campos planos, sin
override y sin defaults. RESEARCH.md §"Code Examples" ya trae el bloque redactado — usarlo.

---

### `models.py` — `FeedSubscription` (model nested, transform) · D-08

**Analog:** `models.py:1229-1260` (`FeedPipeline`) — el nested model tipado más cercano en forma
(escalares + un campo de tipo compuesto, sin override).

**Excerpt — clase completa** (`models.py:1229-1260`, verbatim):

```python
@dataclass(frozen=True, slots=True)
class FeedPipeline(SafeModel):
    """``ingestor.pipeline`` inside ``GET /health/feed`` (Phase 31 TYP-02, D-01).

    Live-capture provenance: field set taken verbatim from
    ``.planning/verification/schemas/market-data-client/get-health-feed.json``,
    captured 2026-07-31 against ``market-data-develop``.

    ``| None`` justification — :attr:`last_write_error` is declared
    ``str | None`` because the live capture OBSERVED it as ``null`` and because
    CONTEXT D-01 locks it as nullable. Its non-``None`` member is typed ``str``
    on the OpenAPI's word alone: the capture shows a healthy pipeline, so a
    populated error value was never seen (RESEARCH assumption A1). That half is
    still an assumption and Phase 33's live evidence adjudicates it.

    :attr:`last_write_at` is deliberately NOT nullable (checkpoint verdict
    option-b): it came back a populated string, and an over-declared ``Optional``
    here would silently absorb a future ``null`` with no divergence record.
    """

    batch_interval_ms: int
    conserved: bool
    flushes: int
    frames_accepted: int
    frames_coalesced: int
    frames_unknown_symbol: int
    last_write_at: str
    last_write_error: str | None = None
```

**Los 4 invariantes que el analog pinnea y que `FeedSubscription` hereda** (RESEARCH.md §Patrón 2):
declararse **antes** de `FeedIngestor`; **sin** override de `from_api`; **ningún** campo
`dict[...]`; **ningún** `received_at`. Y el quinto, sólo en RESEARCH: `FeedIngestor.subscription`
**no puede** ser `FeedSubscription | None` — la regla D-NO-01 de `tools/check_surface_types.py`
reddenea todo `Model | None` en clase exportada.

**Excerpt — orden de inserción en `FeedIngestor`** (`models.py:1288-1303`, cola verbatim):

```python
    last_frame_at: str
    started_at: str
    market: FeedMarket
    pipeline: FeedPipeline
    last_error: str | None = None
```

`subscription: FeedSubscription` (sin default) va junto a `market`/`pipeline`, **antes** de
`last_error`; los dos nuevos `| None` de D-09 van **después** de `last_error`.

**Excerpt — el bloque de comentarios que pasa a ser falso** (`models.py:1146-1149`, verbatim):

```
# NULLABILITY VERDICT (plan 31-04 Task 1 checkpoint, **option-b / Restraint**):
# nothing is declared nullable unless it was CONTEXT-locked (D-01) or actually
# observed as ``null`` in the one live capture. Exactly TWO fields qualify —
# :attr:`FeedIngestor.last_error` and :attr:`FeedPipeline.last_write_error`.
```

"Exactly TWO" pasa a cuatro con D-09 (Open Question 4 de RESEARCH). El resto del bloque
(`:1150-1156`, el argumento de por qué un `Optional` sobre-declarado esconde el campo del censo)
sigue siendo verdadero y **no** se toca — es exactamente la doctrina que D-09/D-11 aplican.

---

### `models.py:95-123` + `__init__.py:72-99` — exports (config)

**Analog:** las entradas `"FeedPipeline"` / `FeedPipeline`, en los cuatro sitios, orden alfabético
estricto. `"FeedSubscription"` va entre `"FeedPipeline"` (`models.py:105`, `__init__.py:82`/`:116`)
y `"Health"`.

`models.__all__` es **obligatorio** (T12 lo asserta: toda subclase de `SafeModel` en `models.py`
debe estar ahí). El `__all__` del paquete es **consistencia** (A5) — y tiene un efecto real: hace
que `check_surface_types.py` escanee los 15 campos de la clase, que es deseable.

---

### `main_market_data.py:1541-1542` (script, batch) · S7 / Pitfall 1

**Analog:** el propio bloque. Cambio de dereference, dos líneas:

```python
        ids_sync = sorted(s.marketSegmentId for s in seg_sync)
        ids_async = sorted(s.marketSegmentId for s in seg_async)
```

→ `s.segment` en ambas. **Ningún gate estático lo detecta** (mypy `files = ["packages/*/src"]`,
pre-commit `files: ^packages/.*/src/`) y el `try/except Exception` de `:1543` lo convierte en un
FINDING silencioso de handler en vez de un crash. No dispara la regla dual sync/async de CLAUDE.md
(es un dereference, no lógica). **Requiere la nota de alcance del planner** — cae fuera de la letra
de D-16 (RESEARCH Open Question 1 / A6).

---

### Tests — field-set exacto (`Instrument`, `Segment`)

**Analog primario:** `test_reference_models.py:161-180`
(`test_calendar_config_field_set_matches_reconciled_wire`) — el único que combina las **dos**
aserciones que esta fase necesita: el set exacto **y** el `not hasattr` de la remoción.

```python
def test_calendar_config_field_set_matches_reconciled_wire() -> None:
    # LIVE-MD-01 / F-08 / F-26: the reconciliation REMOVED the model-only
    # ``businessDays`` field (it never existed on the develop wire) and added the
    # ten real ones. ``test_calendar_config_from_api_populated`` proves the added
    # fields parse, but a stale ``businessDays`` would just default to [] and keep
    # it green — only an exact field-set assertion proves the removal.
    assert {f.name for f in dataclasses.fields(CalendarConfig)} == {
        "open",
        "close",
        "enabled",
        "editable",
        "env_bypass",
        "pre_open_minutes",
        "source",
        "timezone",
        "updated_by",
        "warnings",
        "updated_at",
    }
    assert not hasattr(CalendarConfig.from_api({}), "businessDays")
```

**Analog secundario:** `test_reference_models.py:211-228`
(`test_symbol_field_set_matches_reconciled_wire`) — el que documenta por qué el set exacto prueba
**las dos direcciones a la vez** (las adiciones aterrizaron Y el alias publicado sobrevivió):

```python
def test_symbol_field_set_matches_reconciled_wire() -> None:
    # F-43..F-47 / F-53..F-57 are wire-only field findings: the wire sends five
    # keys ``Symbol`` did not declare. ``test_symbol_from_api_populated_wire_row``
    # proves the added fields PARSE, but it would stay green if only some of them
    # had been added — and, worse, a silent REMOVAL of the published ``marketId``
    # alias would also keep it green (every other assertion reads the new fields).
    # Only an exact field-set assertion proves both directions at once: the five
    # additions landed AND the published alias survived (D-22 forbids the rename).
    assert {f.name for f in dataclasses.fields(Symbol)} == {
        "symbol",
        "marketId",
        "active",
        "id",
        "market_id",
        "created_at",
        "updated_at",
        "received_at",
    }
```

**Adaptación para `Instrument`:** el set exacto son los 11 nombres (10 del wire + el alias
`marketId`), y el `not hasattr` es sobre `"instrumentType"`. Para `Segment`: set de 2
(`{"segment", "live_instruments"}`) y tres `not hasattr` (`marketSegmentId`, `marketId`,
`description`).

**Nota para el planner:** este mismo test (`:219-228`) es T3 — debe ganar `"note"` en el set. Es la
misma edición de una línea, no un test nuevo.

---

### Tests — el par de alias-mirror de `Instrument` (D-04)

**Analog:** `test_reference_models.py:262-277`, los dos gemelos, verbatim:

```python
def test_symbol_market_id_alias_mirrors_wire_snake_case() -> None:
    # F-42 / F-52: ``marketId`` was model-only while ``market_id`` was wire-only in
    # the SAME diff. The alias is kept (published surface, D-22) but is no longer
    # dead: ``from_api`` mirrors the wire value into it. Before this fix a real
    # payload left it permanently "".
    sym = Symbol.from_api(_WIRE_SYMBOL_ROW)
    assert sym.marketId == "ROFX"
    assert sym.marketId == sym.market_id


def test_symbol_explicit_camel_case_payload_key_still_wins() -> None:
    # The mirror only FILLS an absent key. An older fixture or hand-built dict
    # that sends ``marketId`` explicitly keeps its own value.
    sym = Symbol.from_api({"symbol": "GGAL", "marketId": "LEGACY", "market_id": "ROFX"})
    assert sym.marketId == "LEGACY"
    assert sym.market_id == "ROFX"
```

Los dos son necesarios: el primero prueba que el mirror dispara, el segundo prueba el invariante de
seguridad (Tampering, RESEARCH §Security) de que **sólo rellena una clave ausente**.

---

### Tests — fixture de key-set real con valores sintéticos

**Analog:** `test_reference_models.py:198-208` — el contrato de provenance, verbatim:

```python
# The exact row shape of ``get-symbols-probe-prefix-sync.json``. Values are
# synthetic; only the KEY SET and the value TYPES come from the live baseline.
_WIRE_SYMBOL_ROW = {
    "active": False,
    "created_at": "2026-08-01T15:54:36.123456",
    "id": 8123,
    "market_id": "ROFX",
    "received_at": None,
    "symbol": "GSDPROBE/P27-SYNC",
    "updated_at": "2026-08-01T15:54:38.654321",
}
```

Este es el patrón **obligatorio** para las fixtures nuevas de `Instrument`, `Segment` y
`_MEASURED_HEALTH_FEED_43`: el capture del 42 está gitignored y un test que lo lea falla en CI con
`FileNotFoundError` (Pitfall 6). Claves y tipos reales, valores inventados. El mismo contrato está
redactado en `test_core.py:939-944` y `test_reference_core.py:211-213`.

---

## Shared Patterns

### Docstring de provenance de captura
**Source:** `models.py:1199-1201` (`FeedMarket`) / `:1163-1166` (`HealthAuth`)
**Apply to:** toda clase nueva o modificada de esta fase

```
    Live-capture provenance: field set taken verbatim from
    ``.planning/verification/schemas/market-data-client/get-health-feed.json``,
    captured 2026-07-31 against ``market-data-develop``. Not from the OpenAPI and
    not from a mock.
```

Para esta fase la fuente cambia a `42-WIRE-READ.md` §2 + los captures del 42 (segments 4 filas,
instruments 50 filas) y a los blobs F-71/F-202 del ledger. La forma del párrafo se mantiene.

### Justificación explícita de cada `| None` (doctrina option-b)
**Source:** `models.py:1237-1246` (`FeedPipeline`) y `:1146-1156` (bloque de veredicto)
**Apply to:** D-03, D-09, D-10 — cada `| None` nuevo lleva su párrafo `` `| None` justification ``
diciendo **qué observación medida** lo respalda. Y cada campo plano bajo restraint lleva el párrafo
inverso ("deliberately NOT nullable"), que es lo que D-11 necesita.

### Asunción declarada sobre un miembro de unión no observado
**Source:** `models.py:1271-1275` (`FeedIngestor.last_error`)

```
    ``| None`` justification — :attr:`last_error` is declared ``str | None``
    because the live capture OBSERVED it as ``null`` and because CONTEXT D-01
    locks it as nullable. As with :attr:`FeedPipeline.last_write_error`, the
    ``str`` half of the union is unobserved (RESEARCH assumption A1) and awaits
    Phase 33.
```

**Apply to:** `Instrument.active: bool | None` (A2 — 50/50 filas `null`, el miembro `bool` nunca se
observó) y `FeedSubscription.unconfirmed_symbols: list[str]` (A1 — el wire mandó `[]`). Ambas son
autocorrectivas vía el censo de divergencias; el patrón es documentarlo, no evitarlo.

### Construcción exclusiva vía `from_api` en tests
**Source:** todo `test_reference_models.py` — ni un solo `Model(field=value)`
**Apply to:** todos los tests nuevos. `SafeModel.from_api`/`.empty()`/`__bool__` dan tolerancia y
Null Object gratis; un `__post_init__` o una property serían invisibles a `dataclasses.fields()`,
al walker, a `to_dict()` y a los tests de field-set (RESEARCH §Don't Hand-Roll).

### Helpers de test que ya existen — no re-implementar
**Source:** `test_core.py:63` (`_strip_optional`), `:1043-1051` (`_from_api(factory, caplog,
payload)`), `:1019-1041` (fixture `pristine_decode_context`); `test_decode.py:49`
**Apply to:** todo test de esta fase que inspeccione anotaciones o capture records de divergencia.
Sin el scope fresco de `_from_api`, el dedupe por triple `(model, path, kind)` de un test previo
apaga las aserciones en silencio.

---

## No Analog Found

| Sitio | Role | Data Flow | Reason |
|---|---|---|---|
| `_keys_recursive` + `test_every_fixture_key_is_a_measured_wire_key` (D-13, criterio 4) | test (helper) | transform | **No existe hoy** ninguna aserción de subconjunto clave-a-clave en el paquete. Lo más cercano es `test_captured_payloads_match_the_committed_live_schemas` (`test_core.py:1055-1062`), que compara por **igualdad** contra un baseline write-once — semántica opuesta y explícitamente **no** el modelo a seguir (D-13 prohíbe tocar o refrescar ese baseline). RESEARCH.md §"Code Examples · El helper de subconjunto de D-13" trae la implementación propuesta; es el único código genuinamente nuevo de la fase fuera de los modelos. |

---

## Notas de riesgo para el planner

1. **Pitfall 4 y 5 son fallas en tiempo de import**, no de test: un `super()` de cero argumentos o
   un campo con default fuera de orden revientan la colección entera de pytest. Ambos están
   cubiertos por copiar el analog verbatim.
2. **T13/T14 (`test_core.py:1125-1150`) no están en D-12** y sólo los dispara el único campo
   *plano* nuevo (`HealthFeed.symbols_never_delivered`, D-11). RESEARCH §Pitfall 2/3 trae la
   re-derivación exacta. El arreglo "obvio" (extender `_CAPTURED_HEALTH_FEED`) rompe el test de
   igualdad contra el baseline write-once — está prohibido por D-13.
3. **`test_public_surface_market_data.py` (T12) no se edita** — se satisface agregando
   `"FeedSubscription"` a `models.__all__` (S4).
4. **No tocar `packages/matriz-client/**`** ni sus snapshots: contienen `marketSegmentId` pero son
   un `Segment` distinto en otro paquete (RESEARCH §"Tests que NO rompen").

---

## Metadata

**Analog search scope:** `packages/market-data-client/src/market_data_client/`
(`models.py`, `__init__.py`, `_core.py`), `packages/market-data-client/tests/`,
`main_market_data.py`
**Files scanned:** 6 leídos con excerpts; 13 sitios de edición mapeados
**Pattern extraction date:** 2026-08-31
