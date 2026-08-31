# Phase 43: `market-data-client` — forma de `Instrument`/`Segment` + 5 claves `extra` tipadas - Context

**Gathered:** 2026-08-31 (assumptions mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

`market-data-client` deja de declarar campos que el wire no manda y de ignorar campos que sí
manda — `get_segments()` deja de devolver filas enteramente vacías, `Instrument` refleja el
payload real, y las cinco claves `extra` medidas quedan tipadas — todo en un único cambio de
`models.py`, verificado y listo para publicar pero **sin** publicar. Requirements: SHAPE-01,
HARN-02. El release (bump + changelog + gates humanos) es la Phase 44, fuera de este alcance.
</domain>

<decisions>
## Implementation Decisions

### `Instrument` — disposición campo por campo

- **D-01:** `Instrument` mantiene `symbol: str`, `segment: str`, `expired: bool` (los tres están
  en el wire, sin cambio).
- **D-02:** `Instrument` agrega `market_id: str`, `currency: str`, `days_to_maturity: int`,
  `maturity: str`, `outright: bool`, `subscribed: bool` — medidos en `42-WIRE-READ.md` §2, cero
  divergencia con el baseline del 2026-07-31 (delta vacío).
- **D-03:** `Instrument` agrega `active: bool | None = None` — **no** `bool` sin `| None`. La
  única fila medida trae `active: null` (F-205, `market-data-client-findings.md:1591`); declararlo
  no-nullable convertiría esa `extra` en una `missing` permanente sobre cada lectura de catálogo,
  que es exactamente la regresión que el criterio 3 de la fase prohíbe por nombre (aunque ese
  criterio habla de las 5 claves de HARN-02, el mismo principio de evidencia aplica acá).
- **D-04:** `Instrument.marketId: str` queda como **alias aditivo** (D-22, precedente verbatim de
  `Symbol.marketId` en `models.py:817-901`): se agrega `market_id` como campo wire-correcto, se
  sobre-escribe `Instrument.from_api` para espejar `market_id` → `marketId` **sólo** cuando
  `marketId` está ausente del payload (nunca pisa un valor explícito), llamando a
  `super(Instrument, cls).from_api(payload)` en dos argumentos explícitos (el `@dataclass(slots=True)`
  reconstruye la clase, así que el `super()` de cero argumentos rompe). `marketId` queda documentado
  como DEPRECATED, remoción programada para el próximo MAJOR. **Nunca** se renombra directamente —
  prohibido en `REQUIREMENTS.md § Out of Scope`.
- **D-05:** `Instrument.instrumentType: str` se **remueve**. El wire nunca lo manda (F-212/F-213,
  `market-data-client-findings.md`) y toda instancia liberada lo lee `""` — mismo patrón que la
  remoción no-breaking de `CalendarConfig.businessDays`/`CalendarDay.date`/`.marketId`/
  `.isBusinessDay` (`models.py:916-921`).

### `Segment` — disposición campo por campo

- **D-06:** `Segment` se reemplaza por completo: `marketSegmentId`, `marketId`, `description`
  quedan **removidos** (no alias-mapeados — son nombres distintos del wire, no una variante de
  spelling de la misma clave, así que el mecanismo D-22 no aplica aquí). Se **agregan**
  `segment: str` y `live_instruments: int`.
  - **Rechazado explícitamente:** alias-mapear `marketSegmentId → segment` bajo D-22. La
    precondición de D-22 es una MISMA clave con spelling camelCase/snake_case distinto
    (`marketId`/`market_id`); `marketSegmentId` vs `segment` es un nombre diferente, no una
    variante de spelling.
  - Los tres campos declarados hoy son disjuntos del wire y `_core.py:1042-1051` ya documenta en
    prosa que toda fila de `Segment` decodifica vacía — ningún consumidor liberado puede haber
    leído nunca un valor poblado, mismo argumento D-13 de no-breaking.
- **D-07:** El antes/después de `get_segments()` (criterio 2) se demuestra **offline**, contra
  `.planning/verification/captures/market-data-wire-segments-42.json` (presente en disco,
  gitignored) + las entradas del censo F-214…F-218 — sin segunda corrida en vivo, sin segundo
  checkpoint humano bloqueante. `42-WIRE-READ.md` §4.1 advierte que `_emit_shape` está **inerte**
  para `Instrument`/`Segment` (el sample se computa como `raw[0] if isinstance(raw, list)` y el
  wire es un envelope `dict`), así que un "cero findings de `_emit_shape`" post-fix sería un falso
  verde — la evidencia real está en el censo de divergencias, no en el SHAPE-diff del driver.

### HARN-02 — las 5 claves `extra` restantes

- **D-08:** `FeedIngestor.subscription` se tipa como una **nueva dataclass anidada
  `FeedSubscription(SafeModel)`**, no-opcional, siguiendo el precedente `FeedMarket`/`FeedPipeline`
  (`models.py:1195-1261`). `dict[str, Any]` **no es una opción disponible**: dos gates duros lo
  bloquean — (1) `tools/check_surface_types.py` (paso `surface-types` del job `lint`) reddenea
  cualquier campo de clase exportada anotado como mapping sin tipar (`_FIELD_EXEMPTIONS` tiene una
  única entrada, `UnknownFrame.raw`, y `FeedIngestor` está exportado); (2) `_decode.py` no tiene
  rama `dict` — `walk_field` cae a `return value` sin caminar ni reportar. Los 15 campos se declaran
  verbatim del blob medido (F-71, `market-data-client-findings.md:950`): `chunk_size: int`,
  `chunks: int`, `confirm_seconds: int`, `delivered_count: int`, `forced_reconnects: int`,
  `last_reconnect_reason: str`, `quarantined_count: int`, `quarantined_symbols: list[str]`,
  `requested: int`, `sent: int`, `smd_rejections: int`, `smd_resends: int`, `smd_unattributed: int`,
  `unconfirmed_count: int`, `unconfirmed_symbols: list[str]` (elemento no observado poblado —
  asunción ya registrada en `research/SUMMARY.md:141` con confianza LOW; autocorrectiva vía censo
  de divergencias si resulta mal tipada).
- **D-09:** `FeedIngestor.last_error_age_seconds: int | None = None` y
  `FeedIngestor.last_error_at: str | None = None` — **nullable**, no planos. Ambas claves están
  ausentes del baseline sano del 2026-07-31 (`last_error: NoneType`, sin las dos compañeras) y
  presentes en toda captura posterior junto con un `last_error` poblado — son condicionales a que
  exista un error, no siempre presentes. Declararlas no-nullable emitiría `missing` en cada llamada
  sana a `/health/feed`, que es precisamente lo que el criterio 3 prohíbe.
- **D-10:** `Symbol.note: str | None = None` — nullable. Presente en los acks de escritura
  (`create-symbol-sync-response.json`, `update-symbol-sync-response.json`: `"note": "str"`) y
  ausente en las filas de `GET /symbols` (`get-symbols-probe-prefix-sync.json`) — un solo modelo
  sirve los 4 endpoints (`_core.py:1086-1094`), mismo argumento de condicionalidad que D-09.
- **D-11:** `HealthFeed.symbols_never_delivered: int` — **plano, no nullable**. Ausente sólo del
  baseline stale del 2026-07-31 y presente en las tres capturas posteriores; aplica la doctrina de
  restraint option-b ya usada en el resto de `HealthFeed` (`models.py:1146-1156`).

### Fixtures y tests — alcance de re-derivación

- **D-12:** 9 sitios de test necesitan tocarse (ninguno se renombra para que siga pasando —
  prohibido por criterio 4): `tests/test_reference_models.py` (líneas 41-55 valores viejos, línea
  183 `_ALL_MODELS`, línea 219-228 set exacto de campos de `Symbol` — debe ganar `"note"`);
  `tests/test_reference_core.py` (líneas 167-176, 185-190, bodies hand-built con claves viejas de
  `Segment`); `tests/test_reference_client.py` + su gemelo async
  `tests/test_reference_async_client.py` (línea ~78-81, mismo body stale
  `{"marketSegmentId": "DDF", "marketId": "ROFX", "description": "Dolar"}`);
  `tests/test_decode.py` (línea 664-673 `(".marketId", "missing")` sobre `Instrument`, línea
  676-689 claves viejas de `Segment`, **y** línea 1339-1360 que asserta
  `overriding == {"MarketDataSnapshot", "Symbol"}` exacto — el nuevo override de
  `Instrument.from_api` (D-04) rompe este set y debe pasar a 3 elementos, mientras que
  `overriding & nested_types == set()` sigue en pie porque nada declara un campo tipado
  `Instrument`); `tests/test_core.py` (línea 1185-1199 asserta
  `optionals == {"FeedIngestor.last_error", "FeedPipeline.last_write_error"}` exacto — cada nuevo
  `| None` de D-03/D-09/D-10 rompe este set); `tests/test_public_surface_market_data.py`
  (línea 103-121, cada subclase de `SafeModel` en `models.py` debe estar en `models.__all__` —
  `FeedSubscription` debe agregarse ahí). `tests/test_reference_envelope_unwrap.py` ya usa la forma
  real del wire (agregado en Phase 33) y **no** necesita re-derivarse, sólo aserciones más ricas.
- **D-13:** La aserción "conjunto de claves de la fixture ⊆ baseline medido" (criterio 4) es un
  **helper nuevo, explícitamente escrito**, que compara contra una fuente medida committeada (el
  blob "Actual" de F-202/F-71 en el ledger, o una fixture nueva `_MEASURED_HEALTH_FEED_43` con las
  5 claves) — **no** contra ni refresca ningún baseline `.planning/verification/schemas/market-data-client/*.json`.
  Esos baselines son write-once (D-25): `42-WIRE-READ.md` §3 los marca explícitamente
  NO-AUTORITATIVOS para esta fase, y `_write_schema_snapshot` nunca pisa un baseline que difiere.
  `tests/test_core.py::test_captured_payloads_match_the_committed_live_schemas` (línea 1055-1062)
  sigue aseverando **igualdad** contra `get-health-feed.json` sin tocarse — la fixture del
  2026-07-31 es un subconjunto estricto de la forma medida en 2026-08-31, así que ambas aserciones
  conviven sin conflicto.

### CI y alcance dual sync/async

- **D-14:** `client.py` y `aio.py` requieren **cero cambios de fuente**. Ambas superficies llaman
  al mismo objeto función: los parsers `parse_instruments_response`, `parse_segments_response`,
  `parse_symbols_response`, `parse_health_response` y `parse_health_feed_response` en `_core.py`
  son genéricos (`Model.from_api(item)`, ninguna referencia a nombre de campo) y las dos
  superficies delegan al mismo `_core.py` bajo la arquitectura REFAC-03 — es estructural, no una
  conveniencia. El único cambio no-código: el docstring de `_core.py:1042-1051` que hoy documenta
  que el fix de `Segment` está deliberadamente diferido pasa a ser falso y debe reescribirse.
- **D-15:** "Los 4 gates de CI de v1.6" = los 4 jobs de `.github/workflows/ci.yml`
  (`lint`, `pre-commit`, `typecheck`, `test`); el de mayor riesgo real para esta fase es `lint`
  (paso `surface-types`, por D-08), no `test`. El allowlist de `verification/` en el job `lint`
  asertan **cotas inferiores** sobre un ledger append-only, así que un fix de forma no puede
  reddenearlas.
- **D-16:** La fase toca **sólo** `models.py` + tests (y el docstring de D-14). Sin bump de
  versión en ningún sitio (`pyproject.toml`, `__init__.py.__version__`, `uv.lock`) — el release es
  la Phase 44. `tests/test_version_metadata.py:39-54` queda verde trivialmente al no tocar ninguno
  de los tres sitios.

### Claude's Discretion

Ninguno — las 4 áreas de assumptions fueron confirmadas sin corrección por el usuario.

### Folded Todos

Ninguno — `todo.match-phase 43` devolvió 0 coincidencias.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/phases/42-re-chequeos-en-vivo-dns-de-higyrus-port-del-gate-de-venue-ce/42-WIRE-READ.md`
  — lectura fresca autoritativa del wire de `/instruments` + `/segments` (precondición cross-fase
  de `REQUIREMENTS.md`); reemplaza como fuente de verdad a los baselines committeados del
  2026-07-31 para SHAPE-01.
- `.planning/verification/market-data-client-findings.md` — evidencia FID citada: F-67…F-70
  (HARN-02, `/health/feed`), F-87…F-90 (async twin), F-109/F-140 (`Symbol.note`), F-205…F-242
  (Instrument/Segment field-by-field, sync+async).
- `packages/market-data-client/src/market_data_client/models.py:817-901` — precedente D-22
  completo (`Symbol.marketId`/`market_id`), el patrón exacto a replicar para `Instrument.marketId`.
- `packages/market-data-client/src/market_data_client/models.py:1195-1343` — precedente de modelos
  anidados tipados (`FeedMarket`, `FeedPipeline`, `FeedIngestor`, `HealthFeed`), patrón a replicar
  para `FeedSubscription`.
- `packages/market-data-client/src/market_data_client/_core.py:981-1074` — los dos parsers
  (`parse_instruments_response`, `parse_segments_response`), ya correctos post-Phase-33, docstring
  de `Segment` a reescribir (D-14).
- `.planning/research/ARCHITECTURE.md` (§ surface-types gate, § CI jobs) y
  `.planning/research/SUMMARY.md:141` (asunción `unconfirmed_symbols` element type) — producidos
  por el análisis de assumptions de esta fase, citan `tools/check_surface_types.py` y `_decode.py`
  con líneas exactas.
- `.planning/ROADMAP.md` § Phase 43 (líneas 133-146) y § Notas de sizing (líneas 49-56) —
  boundary y restricciones de orden del milestone v1.8.
- `.planning/REQUIREMENTS.md` líneas 19-22, 45-49, 62-63, 82-83 — texto verbatim de SHAPE-01 /
  HARN-02 y su Out-of-Scope.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- El patrón D-22 completo (alias aditivo + `from_api` override + `super()` de dos argumentos
  explícitos) ya existe en `Symbol` y se copia verbatim para `Instrument.marketId`.
- El patrón de modelo anidado tipado (`FeedMarket`/`FeedPipeline` dentro de `FeedIngestor`) ya
  existe y se copia para `FeedSubscription` dentro de `FeedIngestor`.
- `SafeModel.from_api`/`.empty()`/`__bool__` heredados cubren tolerancia y Null Object gratis para
  cualquier dataclass nueva — no hace falta trabajo extra por clase.

### Established Patterns

- `@dataclass(frozen=True, slots=True)` + `SafeModel` + construcción exclusiva vía
  `Model.from_api(payload)`.
- Nombres de campo del wire verbatim (snake_case donde el wire manda snake_case, ej.
  `days_to_maturity`, `market_id`).
- `| None = None` sólo donde hay evidencia medida de nulabilidad condicional — no por defecto ni
  por "quizás puede ser null".
- Baselines de schema son write-once (D-25) — nunca se pisan on drift, se marca el finding y se
  deja el baseline intacto.

### Integration Points

- `_core.py` es el único punto de parsing compartido entre `client.py`/`aio.py` — cambiar
  `models.py` es suficiente sin tocar ninguna de las dos superficies (D-14).
- El censo de divergencias (`verification/divergences.py`) es el mecanismo de evidencia
  post-fix para `Instrument`/`Segment`, no el `_emit_shape` del driver (inerte para estos dos
  modelos, D-07).
</code_context>

<specifics>
## Specific Ideas

Ninguna referencia particular adicional a la ya capturada en `<decisions>` — el usuario confirmó
las 4 áreas de assumptions sin agregar preferencias nuevas.
</specifics>

<deferred>
## Deferred Ideas

Ninguna — sin scope creep detectado durante la discusión. El release (`market-data-client-v0.7.0`)
permanece en la Phase 44 por diseño del milestone.

### Reviewed Todos (not folded)

Ninguno — `todo.match-phase 43` devolvió 0 coincidencias.
</deferred>
