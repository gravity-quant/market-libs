# Phase 29: Decoder observable - Context

**Gathered:** 2026-08-18 (assumptions mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

Ninguna sustitución de campo vuelve a ser silenciosa — todo consumidor de las 6 libs recibe cada divergencia entre el modelo y el wire como un registro estructurado del logger del paquete, y los drivers pueden pedir modo estricto sin cambiar el comportamiento tolerante del runtime.

Load-bearing y PRIMERO en v1.6 (~3× el scope naive de "copiar un decoder": 14 de 25 pitfalls del research aterrizan acá). Artefactos de fase obligatorios: D-lock msgspec, D-lock `Literal` en RESPONSE, tabla de semánticas de `from_api`, fix del `RedactingFilter`, test de intactness por hash, corrida exploratoria de sizing. Requirement: DEC-01. El cambio de política es *silencioso → observable*, NO *tolerante → fatal* (DT-02).
</domain>

<decisions>
## Implementation Decisions

### Motor del decoder (D-lock a)
- **D-01:** El **walker por-campo stdlib es el motor primario** en cualquier escenario (evolución de `_coerce`, NO reemplazado — corrección del research). La decisión msgspec-dos-motores vs stdlib-only **se resuelve dentro de la fase con un spike de timing descartable** (elección del operator): micro-benchmark walker vs `msgspec.convert()` sobre payloads sintéticos representativos; el D-lock se firma con esos números como evidencia del lado pro-msgspec. Hechos verificados que condicionan el spike: msgspec no puede implementar el modo observable (fail-fast, un error por decode, ignora claves extra, sin field-rename para dataclasses stdlib); msgspec tiene cero presencia en `uv.lock`/`pyproject.toml` hoy; la verificación empírica previa de msgspec (`frozen+slots`) NO cubre la forma real de matriz (18 dataclasses frozen, 0 slots). Si el spike da GO, msgspec sería solo fast-path del modo estricto, los 6 wheels se re-publican en F34 y el README declara la pérdida del closure puro-Python.

### Topología de copia
- **D-02:** El helper de decode aterriza **verbatim en 5 paquetes, no 6** — `wallets-client` queda con **exención documentada** (no tiene `_logging.py`, `_state.py`/`_ClientState`, `_core.py`, `models.py` ni `tests/test_logging.py`; bootstrapearlo es scope de Phase 31 TYP-03). Los criterios "×6" del roadmap (fix del filter, sentinels caplog, intactness) se leen "×5 + exención wallets documentada". El test de intactness es por hash + ban-list grep (`strict=False`, `msgspec.field()`) sobre las 5 copias.

### Portador del modo estricto
- **D-03:** Flag `strict_decode` en `_ClientState` (precedente exacto `mutating_allowed`/`expected_host` de market-data `_state.py:100-107`, regla D-14: nunca en `__slots__` de instancia, así los views de `with_options` heredan). El `ContextVar` se bindea con **`.set()` SIN reset** al tope de `_request` — un reset al final de `_request` desbindearía el modo antes de que el decoder lo lea, porque `_request` retorna el `httpx.Response` y el decode ocurre después en el parser. Nunca env var, nunca global de módulo. Debe documentarse el default del modo para `Model.from_api()` invocado directo sin `_request` previo (default: observable).
- **D-04:** El daemon thread de `ws_client` de matriz **no hereda** el ContextVar (thread nuevo = Context vacío; el path de frames nunca pasa por `_request`) → necesita **propagación explícita del modo** como mecanismo propio. El test de concurrencia del criterio 2 prueba dos cosas: no-clobbering entre tareas async interleaved Y propagación explícita (no herencia) hacia el thread.

### Registro de divergencia + RedactingFilter
- **D-05:** El fix del `RedactingFilter` es **dos-partes**: (a) el scan de extras saltea valores no-str (`isinstance(value, str)`) → los dicts anidados nunca se recorren; (b) los markers de redacción son literales anclados (`"Bearer "`, `"password="`, …) → un credential pelado sin marker sobrevive. **Ningún cambio al filter hace seguro loggear valores del wire** (`_redact` mismo es regex marker-anchored) → la garantía la carga el **contrato del registro: flat, all-str, top-level, type-not-value, jamás el valor del wire**; el fix del filter es defensa en profundidad. Sentinel caplog por paquete (5, precedente SEC-01 `verification/test_logging_no_token_leak.py` — que asserta sobre `getMessage()`, `str(record.args)` y `record.__dict__`).
- **D-06:** El vocabulario del registro de divergencia se deriva de `verification/schema.py::schema_of` (claves + tipos, nunca valores) y la emisión queda compatible con el pipeline `findings.py` existente — no se inventa un formato paralelo (el handler de F33 `verification/divergences.py` debe consumirlo sin traducción, y el piso de sizing debe ser directamente contrastable con el censo vivo de F33). `verification/safemodel_diff.py::diff_safemodel_bidirectional` (duck-typed cross-package) es reusable para el pase de sizing.

### Reconciliación de semánticas
- **D-07:** La "tabla 3-way" del roadmap es en realidad **6-way sobre implementaciones de `from_api`** (+2 `empty()`): (1) `SafeModel` higyrus y (2) market-data (2107 chars c/u, NO byte-idénticos — difieren en docstring + 1 comentario); (3) `MarketDataSnapshot.from_api(payload, *, received_at=0.0)` firma extendida que bypassea `_coerce`; (4) `Symbol.from_api` pre-procesa `market_id`→`marketId`; (5) `_SafeModel.from_api(data)` de matriz (missing→`None`, sin slots, `empty()`, escalares pass-through, non-dict→`cls.empty()`); (6) `UnknownFrame.from_api` que retiene el payload crudo en `raw`. La tabla se escribe como artefacto **antes de escribir código de decoder**; política parametrizada por paquete, nunca "harmonizada" en silencio. Merge gate: **872 tests** de los 3 paquetes con SafeModel verdes **sin editar un solo test** (DT-05: `from_api(payload)` conserva firma y contrato). Trap conocido: `@dataclass(slots=True)` rebuilds de clase rompen `super()` zero-arg en `from_api` reescritos (warning in-place en market-data `models.py:495-499`).

### Corrida de sizing
- **D-08:** El corpus del criterio 5 está mal identificado en el roadmap: `verification/snapshots/` son 4 `.txt` de superficie pública **sin payloads**, y `.planning/verification/captures/` está vacío. La corrida se **re-basa en `.planning/verification/schemas/`** (43 JSON type-only: ambito 1 / higyrus 5 / iol 4 / matriz 8 / market-data 25). El piso resultante es de **keyset/tipo** (`≥ N` por paquete, nunca `N`) — honesto como piso, con blind spot documentado: ciego a divergencias de valor (NaN/Infinity, enums out-of-set), que son justo el objeto del D-lock 4b. Freshness conocida: capturas iol de 2026-06-06 (~2.5 meses) — válido como piso igual.

### D-lock b: Literal en RESPONSE
- **D-09:** Los campos de **RESPONSE nunca se cierran como `Literal`** en este milestone: se decodifican como `str` y el valor fuera de set se reporta como divergencia. Alcanza retroactivamente a los 9 aliases de matriz `types.py` (`Side`/`OrderType`/`TimeInForce`/`MarketId`/`SegmentId`/`CFICode`/`MarketDataEntry`/`OrderStatus`/`Currency`). Es **behaviorally-free** para matriz: hoy `_convert` los pasa sin validar (`return value` final), así que el cambio es solo de reporting, nunca de los valores devueltos. El walker NO debe enforcear membership de `Literal` (evitaría la tormenta de divergencias por crecimiento legítimo de enums del vendor).

### Claude's Discretion
- Forma exacta del helper (`_decode.py` como módulo nuevo vs extensión de `models.py`), naming del ContextVar, y estructura interna del spike de timing — dentro de los locks de arriba.
- El mecanismo concreto de propagación explícita del modo al daemon thread de ws_client (parámetro, snapshot del flag en connect, etc.).

### Folded Todos
None — no pending todos matched this phase.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/ROADMAP.md` — § Phase Details (v1.6) → Phase 29 (los 5 success criteria) + nota de sizing del milestone
- `.planning/future-plans/tipado_homogeneo.md` — plan fuente con DT-01..DT-09 lockeados (DT-02 silencioso→observable, DT-03 copia verbatim, DT-05 `from_api` preservado, DT-07 Literal diferido)
- `.planning/research/SUMMARY.md` — correcciones empíricas del research (walker primario, límites de msgspec, riesgo de tormenta de divergencias)
- `.planning/verification/schemas/` — corpus real de la corrida de sizing (43 JSON type-only por paquete)
- `.planning/codebase/` — mapas de codebase (ARCHITECTURE, CONVENTIONS, STRUCTURE, CONCERNS)
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `verification/schema.py::schema_of` — reduce payload a claves+tipos, nunca valores; vocabulario base del registro de divergencia (D-06)
- `verification/safemodel_diff.py::diff_safemodel_bidirectional` — duck-typed cross-package (`_is_safemodel_like`), computa `model-only` (false-pass risk) y `wire-only`; motor candidato del pase de sizing
- `verification/findings.py::append_finding` — pipeline append-only de findings, destino de la emisión en F33
- `verification/test_logging_no_token_leak.py` — precedente SEC-01 del sentinel caplog (asserta `getMessage()` + `str(record.args)` + `record.__dict__`)
- market-data `_state.py:100-107` — precedente exacto D-14 para el flag `strict_decode` (`mutating_allowed`/`expected_host` en `_ClientState` compartido, herencia por views de `with_options`)

### Established Patterns
- 5 copias byte-idénticas del cuerpo de `RedactingFilter.filter` (higyrus `_logging.py:86-100`, ambito `:59-73`, iol `:81-95`, market-data `:71-85`, matriz `:135-157` — matriz agrega bloque D-22 `auth_basic` antes del scan genérico: precedente existente de divergencia per-package en el filter)
- `_request` retorna `httpx.Response`; el decode ocurre después en el parser (`market-data/client.py:450-451` → `_core.py:846+`); `_request` puede enviar el mismo request dos veces (re-auth carve-out)
- Sin código compartido entre paquetes: todo helper se copia verbatim con test de intactness (DT-03)
- `requires-python = ">=3.12"` uniforme; msgspec cero presencia en `uv.lock`

### Integration Points
- Las 5 copias de `_logging.py` (fix del filter) + las 5 `_state.py` (flag) + tope de `_request` en `client.py`/`aio.py` ×5 (bind del ContextVar)
- Los 3 `models.py` con SafeModel (higyrus, matriz, market-data) — 6 `from_api` con contrato propio; 872 tests como merge gate zero-edit
- matriz `ws_client.py:90-93` (decode en daemon thread, línea 184) + `_acquire_token_for_ws:123-140` — único path de decode fuera de `_request`
- `verification/` NUNCA corrió en CI (`ci.yml:114-115` pisa `testpaths`) — los tests de intactness/sentinel que deban gatear deben viajar in-package o esperar el job nuevo de F32

### Environment
- Blocker operativo del `.venv/` (STATE.md) **resuelto** — `uv run` funciona, CPython 3.12.13
</code_context>

<specifics>
## Specific Ideas

- Operator eligió **spike de timing en fase** para el D-lock msgspec (en vez de declarar "sin requisito de perf" o pre-firmar NO-GO): micro-benchmark descartable walker vs `msgspec.convert()` sobre payloads sintéticos representativos; el D-lock se firma con esos números.
</specifics>

<deferred>
## Deferred Ideas

- Bootstrap de `wallets-client` (`models.py`/`types.py`/`_logging.py`/`_state.py`) — Phase 31 (TYP-03); acá solo exención documentada
- Cierre de `Literal` con censo vivo (input de iol + RESPONSE de matriz según D-09) — Phase 33 (DT-07)
- Handler `verification/divergences.py` que rutea divergencias al pipeline de findings — Phase 33 (acá solo se garantiza compatibilidad de formato, D-06)
- Re-captura live para refrescar schemas (~2.5 meses de staleness en iol) — si hace falta, es trabajo de F33 con creds; el piso de sizing es válido igual

### Reviewed Todos (not folded)
None — no pending todos matched this phase.
</deferred>
