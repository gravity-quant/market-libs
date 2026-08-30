# Phase 37: `matriz-client` — dicts residuales tipados + alias - Research

**Researched:** 2026-08-29
**Domain:** Typed-surface ratchet extension + Null Object modelling in a Python 3.12 client monorepo (internal codebase archaeology — no external dependencies)
**Confidence:** HIGH (every claim below was executed or read against the working tree at commit `851d3d4`)

## Summary

CONTEXT.md was written from static analysis. This research **executed** every claim it makes. The
headline: **the decisions hold**, with three corrections and two hazards that would have bitten a
planner turning them into file-level tasks.

Confirmed by execution: the gate is vacuously green today (`0 violations` with all five
`dict[str, Any]` sites in place); the five sites are at exactly lines 344/481/495/496/548; the
D-03 envelope suspicion is **real** (vendor doc shows `detailedPosition` / `accountData`
wrappers the parsers ignore); `portfolio` is the scalar `60240`; `tickPriceRanges` is a
single-key `{"0": {lowerLimit, upperLimit, tick}}` mapping in all three observed samples; the
walker has no `dict` branch; matriz's `MarketDataSnapshot` has **no alias properties yet**; the
Phase 36 template is verbatim-copyable; and the baseline is green (488 tests, mypy clean, all
four gates pass).

Corrected: **D-03's "espeja sync/async" is wrong** — both risk parsers live once in `_core.py`
and `client.py`/`aio.py` merely delegate, so the envelope fix is a **one-site** edit, not two
(F-4). **D-06's "walk_field ... would hand back `None`"** is wrong — the bare pass-through
returns the value verbatim (F-6); harmless to the decision, but the planner must not write a
task premised on a `None` that never appears. And the **roster floor is `>=`, not `==`** — it
cannot break, so raising it is hygiene rather than a required task (F-13).

The two hazards CONTEXT did not anticipate: a field predicate that strips `Optional` would hit
`RequestSpec.params: dict[str, Any] | None` in **all six packages** — defused only because
`RequestSpec` is unexported (F-9), which the planner must state explicitly rather than
rediscover; and **D-07's two-level `dict[str, dict[str, Model]]` needs a recursive axis**, since
`_apply_mapping_policy` is single-level and the precondition test that guards it only inspects
one level of `__args__` (F-8, F-11).

**Primary recommendation:** Sequence as 4 waves — (1) gate extension + RED fixture in
`tools/` + `packages/matriz-client/tests/`, (2) `_core.py` envelope unwrap + regression, (3)
`models.py` new classes + recursive axis + the four retypes, (4) alias properties on
`MarketDataSnapshot`. Waves 2 and 4 are independent of 1 and 3 and can run in parallel; wave 3
must land after wave 1 or CI is red between commits.

## Project Constraints (from CLAUDE.md)

| Directive | Bearing on this phase |
|-----------|----------------------|
| Python 3.12+, uv, httpx, pytest+pytest-httpx, ruff, mypy strict | All new code must pass `uv run mypy packages/matriz-client/src` (clean today) and ruff at `line-length = 100`, double quotes |
| `from __future__ import annotations` mandatory in every module | New model classes inherit this from the existing `models.py` header — do not add a second one |
| Dual sync/async: logic fixes mirrored in `client.py` and `aio.py` | **Does not apply to the D-03 fix** — see F-4; both surfaces delegate to `_core.py`. Applies to nothing else in this phase |
| No shared code between packages | The axis stays in `matriz_client/models.py`; do not re-add a copy to market-data (models.py:122-133 documents why) |
| Never commit `.env` / expose credentials | No live runs in this phase anyway (D-MATZ-33) |
| Model dataclasses `frozen=True`, built via `from_api`, wire names verbatim camelCase | New classes: `@dataclass(frozen=True)`, camelCase fields (`lowerLimit`, `tick`, `upperLimit`) |
| GSD workflow enforcement — no direct edits outside a GSD command | Execution happens under `/gsd-execute-phase` |

Note: matriz uses `@dataclass(frozen=True)` **without** `slots=True`, unlike market-data's
`@dataclass(frozen=True, slots=True)`. Match the local file, not the Phase 36 source.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01 — Gate extension (`tools/check_surface_types.py`)**
- **D-01a:** El gate compartido `tools/check_surface_types.py` (step del job `lint`, cross-package, usado por los 6 paquetes) gana una dimensión nueva de escaneo: anotaciones de campo de dataclass (`ast.AnnAssign` dentro de una `ClassDef` exportada), no solo tipos de retorno de función como hoy. Confirmado por ejecución real: `uv run python tools/check_surface_types.py` reporta "0 violations" HOY con los 5 sitios `dict[str, Any]` en su lugar — el gate estructuralmente nunca los mira (`_candidates_for` solo produce `FunctionDef`/`AsyncFunctionDef`, `tools/check_surface_types.py:495-514`). Vive en el gate compartido, no en un test matriz-local (mismo argumento D-05/D-12 que el propio script documenta: cross-package by nature, y `verification/` nunca ejecuta en CI).
- **D-01b:** El predicado de campo es **angosto**: banea `dict[str, Any]` y `Any` desnudo únicamente — NO cada mención de `Any` en la anotación (a diferencia del predicado de retorno existente, `_annotation_mentions_any`). Medido: un predicado amplio reenrojecería `market-data-client` (`CalendarConfig.warnings: list[Any]` y `CalendarConfigPreview.warnings: list[Any]`, ambos exportados — `packages/market-data-client/src/market_data_client/models.py:943,1034`), un paquete fuera de alcance de esta fase (disjunto con 36/38). Fuera de alcance: tocar o exentar `warnings` de market-data — eso es decisión de otra fase si se decide abordar.
- **D-01c:** `UnknownFrame.raw` es la única exención declarada del predicado de campo, atada por nombre de clase+campo (no por naming pattern genérico como el resto de las exenciones DT-06), con motivo explícito en el código del gate: el escape hatch documentado de frames desconocidos (ya justificado en el docstring existente de `UnknownFrame`, Phase 29/35).
- **D-01d:** Se agrega un fixture RED al estilo `packages/iol-client/tests/test_surface_types_red.py` que prueba que el gate detecta un campo `dict[str, Any]` reintroducido — necesario porque el gate hoy es vacuamente verde sobre esta clase de violación.

**D-02 — `AccountReport.portfolio`**
- `portfolio` se retipa a `float | None` (hoja escalar D-NO-03), NO a un modelo/mapping. Evidencia: `packages/matriz-client/documentation/Primary-API.md:1894` muestra `"portfolio": 60240` — un número, no un objeto — y ese valor coincide con `"totalMarketValue": 60240` de `detailedPosition` para la misma cuenta (`:1706`), consistente con ser un valor de mercado de cuenta. Sale por completo del trabajo de mapping-fields; deja de pasar por `_mapping_value`/`_apply_mapping_policy`.

**D-03 — Envelope unwrap de los parsers Risk (`_core.py`)**
- El fix de envelope-unwrap de `get_detailed_positions`/`get_account_report` es **in-scope** de esta fase, junto con el tipado. Evidencia de la sospecha: ambos parsers (`_core.py:914-918`, `:941-945`) pasan el body raíz verbatim a `from_api` bajo el comentario "NO envelope key, D-07", pero el vendor doc muestra body envuelto (`{"status":"OK","detailedPosition":{...}}` en `Primary-API.md:1701-1703`, `{"status":"OK","accountData":{...}}` en `:1817-1819`), y el endpoint hermano `get_positions` SÍ desenvuelve (`_core.py:885-889`, `unwrap(data, "positions", path)`). Ningún test actual lo cubriría (codifican la forma plana). Tipar sin corregir el unwrap dejaría `report`/`detailedAccountReports` decodificando siempre desde el nivel equivocado — campos tipados pero inertes. El fix se espeja sync/async (D-NO-06) con regresión mockeada nueva. **Si en la ejecución se determina que el envelope NO está roto** (evidencia contraria encontrada), esta decisión se revierte sin bloquear el resto de la fase — no es una precondición dura de las otras decisiones.

**D-04 — Provenance de payloads no observados en vivo**
- **D-04a:** `packages/matriz-client/documentation/Primary-API.md` (vendor doc committeado en el propio paquete) cuenta como evidencia admisible para tipar, pero bajo una **tercera clase de procedencia nueva**: `vendor-documented, unmeasured` — distinta de `baseline` (captura viva committeada, ej. `.planning/verification/schemas/matriz-client/get-instrument-detail.json`) y de `capture` (nueva corrida en vivo, no disponible en esta fase por D-MATZ-33). Nunca se presenta como si fuera una captura real.
- **D-04b:** Formato de la declaración de procedencia: el patrón de dos artefactos ya establecido en Phase 36 — (1) un párrafo de docstring por clase citando la fuente exacta (path + rango de líneas de `Primary-API.md`, o el nombre del archivo baseline + fecha de captura), espejo de `MarketDataEntries`' docstring de Phase 36 (`market_data_client/models.py:314-316`: "Live-capture provenance: ..."); (2) una entrada en el ledger existente `.planning/verification/matriz-client-findings.md` (ya usa columnas `Class`/`Status`, ya soporta `NO-FIX`/`EXPECTED` terminal) para cualquier fila que quede como declarada-no-observada. NO se crea un nuevo formato de registro de procedencia.
- **D-04c:** `tickPriceRanges` es la única de las cuatro fields con baseline de captura viva real (`get-instrument-detail.json`, 2026-06-10) — las otras tres (`report`, `detailedAccountReports`, `portfolio` si terminara siendo modelo) dependen de `vendor-documented, unmeasured` (D-04a) o quedan explícitamente declaradas no observadas si D-07 decide un modelo mínimo sin siquiera esa evidencia.

**D-05 — `tickPriceRanges`**
- Se retipa a `dict[str, TickPriceRange]` (mapping string-keyed), NO a `list[TickPriceRange]`. Las tres muestras observadas (baseline committeado + 2 muestras del vendor doc en `Primary-API.md:330,378,454`) coinciden en 3 campos (`lowerLimit`, `tick`, `upperLimit`) pero todas tienen una sola key (`"0"`) — nada observado establece que las keys sean contiguas/ordenadas, así que aplanar a lista asertaría una propiedad de secuencia no demostrada. Requiere D-06 (upgrade del axis de mapping) para decodificar correctamente.

**D-06 — Fate de `_mapping_value` / `_apply_mapping_policy`**
- El axis (`models.py:99-197`) se **actualiza**, no se elimina. A diferencia de la eliminación de Phase 36 (válida porque `market_data` pasó a ser un modelo anidado que el walker ya sabe decodificar vía su rama `_is_model`), un hint `dict[str, Model]` sigue sin match en ninguna rama de `walk_field` (`_decode.py`: no tiene rama `dict` — cae al pass-through bare de `:555`), así que el axis sigue siendo necesario para que los valores internos se decodifiquen como modelos y no como dicts crudos. El axis gana el tipo de elemento y enruta cada valor a través de `_decode.walk_field` (mismo sink, mismo strict mode, mismo dedupe) en vez de solo coercionar el contenedor externo a `{}`. **No se toca `_decode.py`** — el walker compartido byte-verbatim entre paquetes queda intacto (D-NO-06, `check_decode_intactness.py`); el axis sigue viviendo en `matriz_client/models.py` como mecanismo call-site matriz-only.
- Tras D-02 (portfolio pasa a escalar) y la disposición de `report`/`detailedAccountReports` (D-07), el axis puede terminar aplicándose solo a `tickPriceRanges` — eso es aceptable y no requiere generalizarlo más allá de lo que estos campos necesitan.

**D-07 — Profundidad de modelado de `DetailedPosition.report` / `AccountReport.detailedAccountReports`**
- Disposición **mínima**: solo se modelan los campos escalares con evidencia directa (ej. los tres `instrument*Size` del registro interno de `report`), NO el árbol completo de 2 niveles + `detailedPositions` anidado que el vendor doc sugiere (`Primary-API.md:1707-1789`). Las claves no declaradas del payload real llegan como divergencias `extra` no-fatales (`_decode.py`, mecanismo ya existente), consistente con SC-1 ("nunca un modelo inventado presentado como observado") y con el propio precedente de `MarketDataEntries` (roster cerrado + reporting de divergencias para lo no declarado, `market_data_client/models.py:318-352`). El nivel exterior de mapping (`contractType` → `symbol` → registro) sigue tipado como `dict[str, dict[str, <modelo mínimo>]]` vía el axis D-06 — es la única forma honesta de representar dos niveles de keys abiertas sin inventar un enum de `contractType` ni una lista de símbolos.

### Claude's Discretion
- Naming exacto de las clases nuevas (`TickPriceRange`, modelo mínimo de `report`/`detailedAccountReports`) — sigue la convención `PascalCase` matching wire/domain existente.
- Ubicación exacta del párrafo de docstring de procedencia dentro de cada clase (formato libre mientras cite el path + evidencia, siguiendo el ejemplo de `MarketDataEntries`).
- Si D-03 (envelope fix) resulta no aplicar tras investigación en ejecución, decidir sin bloqueo cómo documentarlo (nota en el mismo docstring de procedencia).

### Deferred Ideas (OUT OF SCOPE)
- Exención o retipado de `CalendarConfig.warnings`/`CalendarConfigPreview.warnings` (`market-data-client`, `list[Any]`) descubierto como efecto colateral de extender el predicado del gate — explícitamente fuera de alcance de esta fase (D-01b), candidato para una fase futura de `market-data-client` o para el propio backlog de auditoría (Phase 38 cubre iol + higyrus/ámbito/wallets, no market-data).
- Modelado completo del árbol de 2 niveles de `DetailedPosition.report` (`detailedPositions` anidado con ~20 campos + `detailedDailyDiff` de 8) — deferido por D-07 hasta que exista una captura en vivo real (post `LIVE-MATZ-33`) que confirme la forma completa.
- Verificación en vivo real de las 3 fields Risk (`report`, `detailedAccountReports`, `portfolio` si termina requiriendo evidencia adicional) — bloqueada por D-MATZ-33 en esta fase; destino ya nombrado en el milestone (`LIVE-NOBJ-01`, Phase 39).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| NOBJ-MTZ-01 | `InstrumentDetail.tickPriceRanges`, `AccountReport.report`, `AccountReport.detailedAccountReports`, `AccountReport.portfolio` tipados como modelos contra payloads reales (exención única y documentada: `UnknownFrame.raw`) | F-1 (exact sites), F-2 (gate blind spot), F-3 (portfolio scalar), F-5 (tickPriceRanges shape + `lowerLimit` int→float widening), F-7 (report/detailedAccountReports vendor shape), F-8 (recursive axis needed), F-9 (predicate blast radius), F-10 (`UnknownFrame` not a `_SafeModel`, exemption must be class+field keyed) |
| NOBJ-MTZ-02 | `matriz_client.models.MarketDataSnapshot` gana las mismas propiedades alias (`last`/`bids`/`offers`/`settlement`/`close`/`open_interest`), compartidas por la superficie REST y los frames WS | F-12 (one class serves both surfaces — no WS-side work), F-14 (Phase 36 alias template verbatim), F-15 (Phase 35 tests already prove property invisibility), F-16 (WS decode-mode propagation untouched by aliases) |

**REQUIREMENTS.md wording note:** the requirement says `AccountReport.report`, but the field is
`DetailedPosition.report` (`models.py:481`) — `AccountReport` has no `report` field. The ROADMAP
success criterion has the same slip. This is a naming error in the requirement, not a missing
field; the phase should type `DetailedPosition.report` and note the correction in the plan so
`/gsd-verify-work` does not chase a field that never existed. [VERIFIED: models.py:474-500]
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Field-annotation ban enforcement | Repo-level CI gate (`tools/check_surface_types.py`) | — | Cross-package by construction; the script's own docstring D-05/D-12 argues `verification/` never runs in CI |
| Gate non-vacuity proof | Package test dir (`packages/*/tests/`) | — | Only `packages/<pkg>` paths are collected by the 6×2 CI matrix |
| Wire-shape typing (models) | `matriz_client/models.py` | — | Package-local; no shared model layer exists by design |
| Mapping-value decode routing | `matriz_client/models.py` (call-site axis) | — | `_decode.py` is byte-verbatim locked across 5 packages; a `dict` branch there is forbidden |
| Envelope unwrapping | `matriz_client/_core.py` (parsers) | — | Single shared parser layer; `client.py`/`aio.py` delegate (F-4) |
| Human-facing alias ergonomics | `matriz_client/models.py` (`@property`) | — | Properties are invisible to `get_type_hints`/`dataclasses.fields`, so REST and WS inherit them for free (F-12) |

## Standard Stack

**No new packages.** This phase adds zero dependencies. Everything is stdlib (`ast`,
`dataclasses`, `typing`) plus the already-installed dev stack.

### Core (already installed, versions verified from `uv.lock` / running env)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pytest` | >=8.3 | Test runner for the RED fixture + regressions | Already the repo runner; CI matrix collects `packages/<pkg>` paths |
| `pytest-httpx` | >=0.34 | Mock the envelope-shaped Risk responses (D-03 regression) | Already used by every parser test in the repo |
| `mypy` | >=1.13 (strict) | SC-3's "`mypy --strict` limpio sobre el paquete" | Baseline clean today: `Success: no issues found in 17 source files` |
| `ruff` | >=0.7 | Lint + format the new code | `line-length = 100`, double quotes, `target-version = "py312"` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Extending `check_surface_types.py` | A matriz-local pytest AST test | Rejected by D-01a; also the gate's own docstring (lines 60-67) argues the roster must be read from `packages/` at runtime so a new package is never "silently exempted by omission" |
| `dict[str, TickPriceRange]` | `list[TickPriceRange]` | Rejected by D-05: all three observed samples have exactly one key `"0"`; nothing observed proves contiguity or ordering |
| Recursive axis in `models.py` | A `dict` branch in `_decode.py` | Forbidden — `check_decode_intactness.py` Check A hashes all five copies of `_decode.py` |

## Package Legitimacy Audit

**Not applicable.** This phase installs no external packages. No registry lookups were performed
because no package name is introduced, recommended, or changed. Every symbol referenced in this
research resolves to a file already committed in this repository.

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Verified Findings

Every finding below was produced by running a command or reading a committed file in this session.

### F-1 — The five `dict[str, Any]` sites are exactly where CONTEXT says
`InstrumentDetail.tickPriceRanges:344`, `DetailedPosition.report:481`,
`AccountReport.detailedAccountReports:495`, `AccountReport.portfolio:496`, `UnknownFrame.raw:548`.
A sixth `Any`-bearing annotation exists — `_SafeModel.__dataclass_fields__: ClassVar[dict[str, Any]]`
at `models.py:209` — but `_SafeModel` is private and unexported, and `__dataclass_fields__` is a
dunder that the gate's existing `_is_exempt` already absorbs. It is **not** a sixth site.
[VERIFIED: grep over `packages/matriz-client/src/matriz_client/models.py`]

### F-2 — The gate is vacuously green today, confirming D-01a
`uv run python tools/check_surface_types.py` →
`surface types: 6 packages, 183 __all__ names, 330 definitions scanned, 13 constant/alias exports, 23 exempted (dunder 13, private-helper 1, serialize-out 9), 0 violations`.
Zero violations with all five sites in place. The cause is structural:
`_candidates_for` (`tools/check_surface_types.py:495-514`) returns only
`FunctionDef`/`AsyncFunctionDef` — for a `ClassDef` it filters `node.body` to member functions
and drops every `AnnAssign`. [VERIFIED: executed + read]

### F-3 — D-02 confirmed: `portfolio` is a scalar
`Primary-API.md:1894` shows `"portfolio":60240` inside the `accountData` object, and
`"totalMarketValue":60240` appears for the same account in the `detailedPosition` response.
`float | None` is correct. **Test impact:** `test_decode.py:470` asserts `report.portfolio == {}`
and `test_models.py:258` asserts `parsed.portfolio == {}` — both must flip to `is None`.
[VERIFIED: read of vendor doc + grep of tests]

### F-4 — D-03's envelope suspicion is REAL, but the sync/async mirroring premise is WRONG
The envelope is real: `Primary-API.md:1701-1703` shows `{"status":"OK","detailedPosition":{...}}`
and `:1817-1819` shows `{"status":"OK","accountData":{...}}`. Both parsers
(`_core.py:911-918`, `:940-945`) call `_parse_risk_response` and hand the **root** dict to
`from_api`. `_parse_risk_response` (`_core.py:278-301`) is byte-identical to
`parse_envelope_response` (`:241-275`) except it omits the `unwrap` call — so today
`DetailedPosition.from_api({"status":"OK","detailedPosition":{...}})` decodes `status` as an
extra key and finds none of the declared fields.

**The correction:** CONTEXT says "El fix se espeja sync/async (D-NO-06)". It does not need to be.
Both parsers live **once** in `_core.py`; `client.py:679,685` and `aio.py:713,718` both call
`_core.parse_get_detailed_positions_response` / `_core.parse_get_account_report_response`.
The fix is a **single-site** edit. Mirroring is satisfied by construction. A planner who writes
two mirrored tasks will produce one no-op task.

The mechanism to reuse already exists: `unwrap(data, key, endpoint)` (`_core.py:224-238`) raises
a typed `PrimaryAPIError` on a missing key, exactly as `parse_get_positions_response`
(`:884-889`) uses it. **Behavioural warning:** switching to `unwrap` makes a flat (unenveloped)
response *raise* instead of silently decoding to empties — a real behaviour change that the
existing tests (which encode the flat shape) will surface. That is the fix working, but it
must be an intentional, documented task outcome, not a surprise.
[VERIFIED: read of `_core.py` + vendor doc + grep of both surfaces]

### F-5 — `tickPriceRanges` shape confirmed, plus an int→float widening detail
Live baseline `.planning/verification/schemas/matriz-client/get-instrument-detail.json`
(captured `2026-06-10T01:01:55Z`, symbol `SOJ.ROS/NOV26 308 P`) records:
`"tickPriceRanges": {"0": {"lowerLimit": "int", "tick": "float", "upperLimit": "NoneType"}}`.
Vendor doc samples at `:330`, `:378`, `:454` all show `{"0":{"lowerLimit":0,"upperLimit":null,"tick":0.1|0.05}}`.
Three samples, one key each, three fields each — D-05's reasoning holds exactly.

**Typing detail the planner must carry into the docstring:** `lowerLimit` is observed as `int`
but should be declared `float | None`. `walk_field`'s `float` arm (`_decode.py:531-538`) widens
`int`→`float` *before* consulting `scalar_passthrough`, so the widening is silent and fabricates
no divergence. This is the identical situation Phase 36 documented on `BookLevel.price`
(`market_data_client/models.py:281-285`) — reuse that paragraph's reasoning. `upperLimit` was
`null` in every sample, so `float | None` is right and an absent one answers `None`.
[VERIFIED: read of baseline JSON + vendor doc + `_decode.py`]

### F-6 — CONTEXT's description of the walker's dict fallback is slightly wrong
D-06 says a dict hint "cae al pass-through bare de `:555`" and "would hand back `None`".
The first half is right; the second is not. `walk_field`'s final statement is `return value`
(`_decode.py:555`) — the raw dict passes through **verbatim**, not as `None`. The axis then
either returns it unchanged (if a dict) or substitutes `{}`. The decision is unaffected — a
`dict[str, Model]` hint still gets raw dicts instead of models, which is exactly why the axis
must gain element-type routing — but a task written to "fix the `None` the walker returns" would
be chasing a value that never occurs. [VERIFIED: read of `_decode.py:417-555`]

### F-7 — `report` / `detailedAccountReports` vendor shape
`report` (`Primary-API.md:1707+`): two levels of open keys —
`{"FUTURE_OPTION_CALL": {"SOJ.ROS/MAY23 380 C": {"detailedPositions": [...], ...}}}`.
`detailedAccountReports` (`:1826+`): one level of open keys —
`{"0": {"currencyBalance": {"detailedCurrencyBalance": {...}}, "settlementDate": 1669950000000}}`.

Note the asymmetry CONTEXT's D-07 blurs: `report` is **two** levels of open keys,
`detailedAccountReports` is **one**. They do not need the same container shape. D-07's
`dict[str, dict[str, <modelo mínimo>]]` describes `report`; `detailedAccountReports` is
`dict[str, <modelo mínimo>]` — one level. The planner should type them separately rather than
forcing a shared depth.

D-07 names "los tres `instrument*Size`" as the directly-evidenced scalars, but the vendor sample
region actually shows the inner `detailedPositions[]` entries carrying `symbolReference`,
`contractType`, `priceConversionFactor`, `contractSize`, `marketPrice`, `currency`,
`exchangeRate`, `contractMultiplier`, `totalInitialSize` — the `instrument*Size` names are not
in the sampled excerpt. **The plan must include a task that re-reads `Primary-API.md:1707-1790`
and `:1826-1890` and derives the minimal roster from what is actually there**, rather than
hard-coding three field names from CONTEXT. [VERIFIED: read of vendor doc]

### F-8 — The single-level axis cannot serve D-07's two-level `report`
`_apply_mapping_policy` (`models.py:145-169`) iterates `fields(cls)`, tests `_is_mapping(hint)`,
and calls `_mapping_value` once per field. `_mapping_value` (`:99-142`) does one `isinstance`
check and returns the dict unchanged. There is no recursion and no element-type parameter.

For `dict[str, TickPriceRange]` the axis needs one new level (route each value through
`walk_field`). For `dict[str, dict[str, ReportEntry]]` it needs **recursion**: the element type
is itself a mapping. The natural implementation is to make `_mapping_value` take the element
hint and self-recurse when `_is_mapping(element_hint)` — but that is a genuinely new control
flow, not a parameter addition, and deserves its own task with its own tests.
[VERIFIED: read of `models.py:94-197`]

### F-9 — The field-predicate blast radius, measured across all six packages
An AST scan of every `ClassDef` body in all six `src/` trees found these `Any`-bearing field
annotations:

| Site | Annotation | Exported? | Would a narrow `dict[str,Any]`-stripping-Optional predicate hit it? |
|------|-----------|-----------|--------------------------------------|
| `RequestSpec.params` (×6: ambito, higyrus, iol, market-data, matriz, wallets-adjacent) | `dict[str, Any] \| None` | **No** — `RequestSpec` is in no package's `__all__` | No (unreachable by the gate) |
| `RequestSpec.json_body` / `.data` (higyrus, iol, market-data) | `dict[str, Any] \| None` | No | No |
| `CalendarConfig.warnings`, `CalendarConfigPreview.warnings` (market-data) | `list[Any]` | **Yes** | No (narrow predicate spares `list[Any]`) — this is D-01b's whole point |
| `_SafeModel.__dataclass_fields__` (matriz) | `ClassVar[dict[str, Any]]` | No (and dunder-exempt anyway) | No |
| matriz's five sites | `dict[str, Any]` | Yes | Yes — the intended targets |

**This is the finding that de-risks D-01b.** The `RequestSpec` family is the one shape that would
have reddened all six packages, and it is safe *only* because `RequestSpec` is unexported. The
gate resolves candidates from `__all__` (`_resolve_export`, `:443+`), so it never reaches
`_core.py`'s internals. The plan should state this explicitly so a future reader does not
"helpfully" export `RequestSpec` and detonate the gate.

**Open predicate question for the planner:** should the predicate strip `Optional` before
matching? Nothing exported has `dict[str, Any] | None` today, so it is safe either way.
Recommendation: **yes, strip it** — a nullable untyped mapping on an exported model field is
exactly the regression the ratchet exists to catch, and leaving the hole open invites a trivial
bypass. [VERIFIED: AST scan executed over `packages/*/src/**/*.py` + grep of every `__init__.py`]

### F-10 — `UnknownFrame` is not a `_SafeModel`, which shapes the exemption
`class UnknownFrame:` (`models.py:528`) has **no base class**. It is a duck-typed member of
`PrimaryWsMessage` with hand-written `from_api`/`empty`/`__bool__`. Consequences:
- It is invisible to `_safemodel_classes()` and to the parametrized roster tests — deliberately,
  per the long comment at `test_null_object.py:256-269`.
- The gate reaches it anyway, because the gate resolves `__all__` (it **is** exported —
  `__init__.py:81,146`) and scans `ClassDef` bodies, not `_SafeModel` subclasses.
- `_is_exempt("raw")` returns `None` (not dunder, not underscore-prefixed, not `to_dict`), so
  D-01c's class+field-keyed exemption is genuinely required — no existing exemption absorbs it.
[VERIFIED: read of `models.py:527-561`, `check_surface_types.py:390-403`, `__init__.py`]

### F-11 — The mapping precondition test will survive, but has a depth blind spot
`test_no_mapping_carrying_model_is_ever_a_nested_field_type` (`test_decode.py:474-520`) builds
`carriers` (classes with a mapping-typed hint) and `nested_types` (dataclass models appearing as
a field type or in a hint's `__args__`), then asserts the intersection is empty.

After this phase, `TickPriceRange` enters `nested_types` (it is in `dict[str, TickPriceRange]`'s
`__args__`) but is not a carrier, so the assert still passes. **The blind spot:** the test walks
only **one** level of `__args__`. A model nested at depth 2 — exactly D-07's
`dict[str, dict[str, ReportEntry]]` — is never discovered. So if `ReportEntry` ever gained a
mapping field, the guard would stay green while the axis silently skipped it. Recommend the plan
either (a) keeps every new inner model mapping-free (simplest, and D-07 already implies it), or
(b) deepens the test's `__args__` walk. Option (a) plus an explicit note is sufficient; do not
let this become an unstated assumption. [VERIFIED: read of `test_decode.py:474-520`]

### F-12 — SC-3 is satisfied by editing ONE class; there is no WS-side work
`MarketDataSnapshot` (`models.py:418-441`) is simultaneously:
- the REST return type — `_core.py:810-814` `parse_get_market_data_response` returns
  `MarketDataSnapshot.from_api(unwrap(data, "marketData", path))`, surfaced at `client.py:637`,
  `client.py:875`, `aio.py:672`, `aio.py:931`;
- the WS frame payload — `MarketDataFrame.marketData: MarketDataSnapshot` (`models.py:515`),
  built by `_parse_frame` → `MarketDataFrame.from_api` (`ws_client.py:149-161`).

SC-3's "es el mismo objeto y el mismo juego de alias" is therefore **already true structurally**;
adding six properties to that one class satisfies both surfaces with no `ws_client.py` edit at
all. A planner who writes a separate "add aliases to the WS path" task is writing a no-op.

The alias→field map (matriz's wire names differ from market-data's only in that matriz has
extra scalars):

| Alias | Field | Type |
|-------|-------|------|
| `bids` | `BI` | `list[MarketDataLevel]` |
| `offers` | `OF` | `list[MarketDataLevel]` |
| `last` | `LA` | `MarketDataEntryValue` |
| `settlement` | `SE` | `MarketDataEntryValue` |
| `close` | `CL` | `MarketDataEntryValue` |
| `open_interest` | `OI` | `MarketDataEntryValue` |

All six targets exist and all six types line up with the Phase 36 template one-for-one. Note
`CL` is a `MarketDataEntryValue` (per the existing `# CL viene como objeto ... Ver issue #102`
comment at `models.py:431-432`), so `.close.price` works; `OP` is a bare `float` and is
deliberately **not** in the alias set. [VERIFIED: read of `models.py`, `_core.py`, `ws_client.py`]

### F-13 — Roster floor is `>=`, so it cannot break
`test_null_object.py:229` is `assert len(_safemodel_classes()) >= 17`, and the docstring
explicitly says "`>= 17` rather than `== 17`: ... phases 36-38 may legitimately add classes".
Measured today: exactly 17. CONTEXT says "subir tras agregar clases nuevas" — that is hygiene
matching Phase 36's precedent (market-data uses `>= 16`), **not** a task that unblocks anything.
Do not let a planner mark it as a blocking dependency.

The parametrized roster tests **do** auto-extend to new classes, which is a real (and good)
consequence: every new model must satisfy falsy-when-empty, truthy-when-perturbed, and
silent-`empty()`. `_perturb` (`:110-144`) handles them — its `cur is None` branch fires first and
covers an all-`None` leaf like `TickPriceRange`. [VERIFIED: executed roster count = 17; read of tests]

### F-14 — The Phase 36 alias + provenance template is verbatim-copyable
`market_data_client/models.py:381-409` is six `@property` methods, each a one-line docstring
(`"""Human-facing alias over the wire-named field ``BI`` (D-03)."""`) and a single `return`.
The provenance paragraph pattern is `MarketDataEntries` (`:314-316`):
"Live-capture provenance: the ten declared keys are exactly the ten observed in
`<path>`, captured `<date>` against `<env>`."

For matriz, D-04a requires a **third** provenance class. Suggested wording, mirroring the form:
- `TickPriceRange` → "Live-capture provenance: field set taken verbatim from
  `.planning/verification/schemas/matriz-client/get-instrument-detail.json`, captured 2026-06-10
  against `api.remarkets.primary.com.ar`."
- `report`/`detailedAccountReports` models → "Vendor-documented provenance, UNMEASURED: field set
  taken from `packages/matriz-client/documentation/Primary-API.md:<range>`. No live capture
  exists — `matriz-client` is blocked from live runs by D-MATZ-33 (`LIVE-MATZ-33`). This roster
  has never been observed on the wire; undeclared keys arrive as non-fatal `extra` divergences."

The second form is the honest one SC-1 demands. Copy the *form*, never the content.
[VERIFIED: read of `market_data_client/models.py:272-409`]

### F-15 — Phase 35 already proved properties are invisible to the walker
`test_property_aliases_are_invisible_to_get_type_hints` (`test_null_object.py:292-311`) and
`test_adding_a_property_alias_does_not_change_the_divergence_count` (`:314-331`) use module-local
fixtures `_AliasShaped`/`_AliasFree` (`:195-213`) whose docstring literally reads "The exact
shape phases 36-38 introduce". The invariant is pre-proven; this phase only has to *apply* it.

A new test asserting the six real aliases (e.g. `snapshot.last is snapshot.LA` for a
REST-parsed and a WS-parsed instance) is still worth adding as SC-3's direct evidence, but the
walker-invisibility proof should **not** be rewritten. [VERIFIED: read of `test_null_object.py`]

### F-16 — WS decode-mode propagation is untouched by anything in this phase
`ws_client.py` snapshots `_ClientState.strict_decode` at connect time into `_ws_strict_decode`
(`:79`, `:238-276`) and runs each frame parse in a bound context (`:262`). Properties add no
decode path, so SC-4's "propagación explícita del modo de decode por conexión y por frame" is
preserved by construction. The relevant guard tests already exist
(`test_ws_decode_mode.py::test_plain_thread_does_not_inherit_the_decode_mode`, cited at
`ws_client.py:252`). The one thing that *could* touch this is the D-03 envelope fix — but that
is REST-only. [VERIFIED: read of `ws_client.py`]

### F-17 — `_convert` is a pinned call site of the axis
`_convert` (`models.py:172-197`) calls `_mapping_value(value, path="", model="", sink=sink)`.
Two committed tests pin it:
- `test_decode.py:921-925` `test_convert_argument_order_is_unchanged` — asserts the parameter
  order is `(tp, value)`, reversed vs. other packages.
- `test_decode.py:927-933` `test_convert_shim_still_coerces` — asserts
  `models._convert(dict[str, Any], None) == {}`.

So the new axis signature must still accept a **bare `dict[str, Any]`** hint (element type `Any`)
and return `{}` for `None`. If the element-type parameter is made mandatory, `_convert` must
derive it from `get_args(tp)` and tolerate the empty/`Any` case. This test will fail loudly
otherwise — which is correct, but should be an anticipated task, not a surprise.
[VERIFIED: read of tests + `models.py`]

### F-18 — `models.py` is NOT constrained by the intactness gate
`check_decode_intactness.py` Check A hashes only `_decode.py` (`:155` — `return self.src_root / "_decode.py"`).
Check B hashes only the marker-delimited region in `_logging.py`. Check C's ban list is two
narrow regexes (`strict=False` scoped to `_decode.py`; `msgspec.field(` repo-wide). Check D
verifies each in-scope package *carries* a `_decode.py`.

**Nothing in that gate constrains `models.py`.** The axis rewrite is free. Confirm by re-running
the gate after the change; it should be unaffected. [VERIFIED: read of `tools/check_decode_intactness.py`]

## Architecture Patterns

### System Architecture Diagram

```text
                      ┌──────────────────────────── CI job: lint ────────────────────────────┐
                      │  tools/check_surface_types.py                                        │
                      │    __all__ → _resolve_export → _Binding(ClassDef|FunctionDef)        │
                      │        ├── _candidates_for  → member FunctionDefs → _adjudicate      │  ← exists
                      │        └── _field_candidates_for → member AnnAssigns → _adjudicate_field │ ← D-01a ADDS
                      │              narrow predicate: dict[str,Any] | bare Any (D-01b)      │
                      │              exemption: UnknownFrame.raw only (D-01c)                │
                      └──────────────────────┬───────────────────────────────────────────────┘
                                             │ proven non-vacuous by
                                             ▼
                      packages/matriz-client/tests/test_surface_types_red.py  (D-01d)
                          tmp_path synthetic pkg → check_surface_types(root=tmp_path) → raises


   HTTP response                                                        WebSocket frame
        │                                                                      │
        ▼                                                                      ▼
  _core.py parsers                                                    ws_client._parse_frame
   ├─ parse_get_market_data_response ──┐                               ├─ type "Md" ──┐
   │    unwrap(data,"marketData")      │                               │              │
   ├─ parse_get_detailed_positions ────┤                               ├─ type "or"   │
   │    _parse_risk_response           │                               └─ else → UnknownFrame.from_api
   │    ✗ MISSING unwrap("detailedPosition")   ← D-03 FIX (one site)          (walker-exempt, raw kept)
   └─ parse_get_account_report ────────┤
        _parse_risk_response           │
        ✗ MISSING unwrap("accountData")│
                                       ▼
                          Model.from_api(payload)   [models.py:212-249]
                                       │
                       ┌───────────────┴────────────────┐
                       ▼                                ▼
             _decode.walk_model                _apply_mapping_policy   ← D-06 UPDATES
             (byte-verbatim, LOCKED)            (matriz-only call-site axis)
                       │                                │
                       ▼                                ▼
             walk_field branches:              for each dict-hinted field:
               Union → list → model →            _mapping_value(value, element_hint)
               str/bool/int/float →                ├─ non-dict → sink + {}
               Literal → BARE PASS-THROUGH          └─ dict → route each value through
               (no dict branch — :555)                  _decode.walk_field(element_hint)
                                                        └─ recurse if element is itself a mapping (D-07)
                                       │
                                       ▼
                        MarketDataSnapshot  ← ONE class, BOTH surfaces
                          fields: BI OF LA SE OI CL OP HI LO TV IV EV NV ACP
                          + 6 @property aliases (D-16 / NOBJ-MTZ-02)   ← invisible to walker
```

### Recommended Change Surface

```
tools/
└── check_surface_types.py          # D-01a/b/c: field dimension + narrow predicate + exemption

packages/matriz-client/
├── src/matriz_client/
│   ├── models.py                   # new classes, 4 retypes, recursive axis, 6 aliases
│   └── _core.py                    # D-03: unwrap in the two risk parsers (ONE site each)
└── tests/
    ├── test_surface_types_red.py   # NEW (D-01d) — mirrors iol-client's file
    ├── test_decode.py              # mapping-axis tests + portfolio assertion flip
    ├── test_models.py              # portfolio/report/detailedAccountReports assertions
    ├── test_core.py                # NEW envelope regressions (enveloped + flat-raises)
    └── test_null_object.py         # roster floor bump + real-alias assertions
```

`ws_client.py`, `client.py`, `aio.py`, `_decode.py`, and every other package: **untouched**.

### Pattern 1: Alias property over a wire-named field (Phase 36, verbatim template)
**What:** A read-only `@property` giving a human name to a camelCase/abbreviated wire field.
**When to use:** NOBJ-MTZ-02, all six aliases.
**Why it is safe:** `get_type_hints` and `dataclasses.fields` both omit properties, so the walker
never sees them and the divergence count is unchanged (proven, F-15).

```python
# Source: packages/market-data-client/src/market_data_client/models.py:381-394 (Phase 36)
    @property
    def bids(self) -> list[BookLevel]:
        """Human-facing alias over the wire-named field ``BI`` (D-03)."""
        return self.BI

    @property
    def last(self) -> EntryValue:
        """Human-facing alias over the wire-named field ``LA`` (D-03)."""
        return self.LA
```

### Pattern 2: Envelope unwrap in a parser
**What:** Pull the payload out of `{"status":"OK","<key>":{...}}` before `from_api`.
**When to use:** D-03, both risk parsers.

```python
# Source: packages/matriz-client/src/matriz_client/_core.py:884-889 (the sibling that DOES unwrap)
@_decode._response_parser
def parse_get_positions_response(resp: httpx.Response, account_name: str) -> list[Position]:
    """Parse envelope ``{positions: [...]}`` → ``list[Position]``."""
    path = f"/rest/risk/position/getPositions/{account_name}"
    data = parse_envelope_response(resp, path)
    return [Position.from_api(p) for p in unwrap(data, "positions", path)]
```

### Pattern 3: RED-fixture synthetic package (D-01d)
**What:** Materialise a fake package under `tmp_path` and inject it as the gate's `root`.
**Why it works:** `REPO_ROOT` is a **default argument value**, not an inlined constant — the one
seam that makes the gate testable (documented at `test_surface_types_red.py:19-27`).

```python
# Source: packages/iol-client/tests/test_surface_types_red.py:65-124
def _write_fake_package(root, *, init_source, client_source, extra_modules=None) -> None:
    pkg = root / "packages" / "fake-client" / "src" / "fake_client"
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "__init__.py").write_text(init_source, encoding="utf-8")
    (pkg / "client.py").write_text(client_source, encoding="utf-8")
    ...

def test_gate_fails_on_an_injected_regression(tmp_path: Path) -> None:
    _write_fake_package(tmp_path, init_source=..., client_source=...)
    with pytest.raises(CheckFailure, match="get_thing"):
        check_surface_types(root=tmp_path)
```

The matriz variant must inject a **field**, not a return type — e.g. an exported
`@dataclass` with `payload: dict[str, Any]` — and must also assert the **complement**: that a
class named `UnknownFrame` with a field named `raw` does **not** redden, proving the exemption
is reachable rather than dead code.

### Anti-Patterns to Avoid
- **Adding a `dict` branch to `_decode.py`.** Check A hashes all five copies. The axis belongs in
  `models.py` (F-18 confirms `models.py` is unconstrained).
- **Re-creating the axis in `market_data_client/models.py`.** `models.py:122-133` explicitly
  records that Phase 36 deleted it and instructs maintainers not to restore the symmetry.
- **Writing mirrored sync/async tasks for D-03.** One site (F-4).
- **Writing a WS-side alias task.** No-op (F-12).
- **Widening the field predicate to any mention of `Any`.** Reddens market-data's `warnings`
  (F-9); D-01b forbids it and the gate's own docstring (`:116-119`) forbids resolving that by
  weakening the exemption predicate.
- **Forcing `report` and `detailedAccountReports` to the same container depth.** They differ:
  two levels vs. one (F-7).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Decoding a mapping's values into models | A bespoke per-field loop calling `Model.from_api` | Route through `_decode.walk_field(element_hint, ...)` from the axis | `from_api` resolves its own sink via `current_sink()`, leaving the surrounding scope — dedupe (lock 5) stops firing. `_decode.py:459-506` documents this exact trap |
| Missing-envelope-key errors | A `KeyError` or a manual `if key not in data` | `unwrap(data, key, endpoint)` (`_core.py:224-238`) | Already raises a typed `PrimaryAPIError`, keeping the client's exception contract (D-MATZ-9) |
| Proving the gate isn't vacuous | Spawning a mypy/CLI subprocess, or committing a fake package under `packages/` | In-process `check_surface_types(root=tmp_path)` | A committed fake package enters `check_decode_intactness` Check D's roster and owes `check_uniform_structure` a `models.py`+`types.py` — two unrelated gates go red (documented at `test_surface_types_red.py:12-17`) |
| Declaring unobserved payload shapes | Inventing a full model from the vendor doc and shipping it as observed | Minimal roster + `extra` divergence reporting (D-07) | SC-1 forbids "un modelo inventado presentado como observado"; the `extra` mechanism already exists in `_decode.py` |
| Null-safe attribute chains | Manual `if x is None` guards | `_SafeModel.empty()` / `__bool__` (Phase 35) | New classes inherit both for free |

**Key insight:** every mechanism this phase needs already exists somewhere in the repo. The
work is composition and honest provenance labelling, not invention. The single genuinely new
piece of logic is the axis recursion (F-8).

## Common Pitfalls

### Pitfall 1: Typing the fields without fixing the envelope
**What goes wrong:** `report` and `detailedAccountReports` become typed but decode from the
wrong nesting level forever — "campos tipados pero inertes", as CONTEXT puts it.
**Why it happens:** the parsers' docstrings *assert* "NO envelope key, D-07" and the tests encode
the flat shape, so both artifacts confirm the bug rather than reveal it.
**How to avoid:** land D-03 before or with the retype; add a regression that feeds the
**enveloped** body from `Primary-API.md:1701-1703` and asserts the fields populate.
**Warning signs:** a decode test that passes with a flat fixture and was never given an
enveloped one.

### Pitfall 2: The envelope fix converts silence into a raise
**What goes wrong:** `unwrap` raises `PrimaryAPIError` on a missing key. Existing tests feeding
flat bodies will now raise instead of returning empties. That looks like a regression.
**Why it happens:** the old behaviour silently produced an all-defaults model for *any* body.
**How to avoid:** treat the flat-body tests as fixtures to **update**, and add an explicit test
asserting the raise. Decide and document whether a flat body is genuinely impossible or whether
the parser should tolerate both shapes — the vendor doc shows only the enveloped form.
**Warning signs:** a task that says "fix the unwrap" without any test-update sub-task.

### Pitfall 3: The gate goes red between commits
**What goes wrong:** landing the field-scanning gate before the retypes makes `lint` fail on
matriz's five sites; landing the retypes first leaves the gate vacuous with nothing proving it.
**Why it happens:** the gate and the code it polices are in the same phase.
**How to avoid:** either land both in one commit, or land the gate with the exemption plus the
retypes together in a single wave. Do **not** sequence gate-then-code across two commits.
**Warning signs:** two consecutive tasks where the first touches `tools/` and the second touches
`models.py`, with a commit boundary between them.

### Pitfall 4: Regenerating a `{}` assertion as `{}` when it should be `None`
**What goes wrong:** `portfolio` becomes `float | None`, so `== {}` is now wrong in two committed
tests (`test_decode.py:470`, `test_models.py:258`).
**How to avoid:** grep for the four field names across `packages/matriz-client/tests/` before
editing — the full hit list is `test_decode.py:467,468,470,471,554`, `test_models.py:65,250,258,259`,
`test_logging.py:403,421`.
**Warning signs:** a green suite after the retype — it would mean the parametrized roster tests
absorbed the change and the specific assertions were never exercised.

### Pitfall 5: Assuming `_perturb` handles the new classes
**What goes wrong:** `_perturb` (`test_null_object.py:110-144`) raises `AssertionError` if it
falls off the end. It dispatches `cur is None` first, so an all-optional leaf like
`TickPriceRange` is fine — but a class whose every field defaults to a non-`None`, non-scalar,
non-list, non-dict, non-`_SafeModel` value would blow up.
**How to avoid:** keep new model fields to `float | None` / `str | None` / `int | None` /
nested `_SafeModel`. Every shape D-05 and D-07 need is already covered.

### Pitfall 6: The `_convert` shim breaks on a mandatory element-type parameter
**What goes wrong:** `test_convert_shim_still_coerces` asserts `_convert(dict[str, Any], None) == {}`
and `test_convert_argument_order_is_unchanged` pins `(tp, value)`.
**How to avoid:** derive the element hint inside `_convert` from `get_args(tp)`, defaulting to
`Any` when absent, and keep the parameter order (F-17).

## Code Examples

### The four target sites, current state
```python
# Source: packages/matriz-client/src/matriz_client/models.py:344, 481, 495-496, 548
    tickPriceRanges: dict[str, Any] = field(default_factory=dict)        # :344  InstrumentDetail
    report: dict[str, Any] = field(default_factory=dict)                 # :481  DetailedPosition
    detailedAccountReports: dict[str, Any] = field(default_factory=dict) # :495  AccountReport
    portfolio: dict[str, Any] = field(default_factory=dict)              # :496  AccountReport
    raw: dict[str, Any] = field(default_factory=dict)                    # :548  UnknownFrame (EXEMPT)
```

### The axis as it stands (the thing D-06 updates)
```python
# Source: packages/matriz-client/src/matriz_client/models.py:139-169 (bodies only)
def _mapping_value(value, *, path, model, sink):
    if isinstance(value, dict):
        return value                       # ← values NOT decoded; raw dicts reach the caller
    sink(model, path, "missing" if value is None else "type", "dict", type(value).__name__)
    return {}

def _apply_mapping_policy(cls, kwargs, *, sink) -> None:
    target = cast(Any, cls)
    hints = _decode.hints_for(target)
    for f in fields(target):
        if _is_mapping(hints[f.name]):
            kwargs[f.name] = _mapping_value(kwargs[f.name], path=f".{f.name}", model=cls.__name__, sink=sink)
```

### The observed `tickPriceRanges` payload (D-05's whole evidence base)
```json
// Source: .planning/verification/schemas/matriz-client/get-instrument-detail.json
//         captured 2026-06-10T01:01:55Z, symbol "SOJ.ROS/NOV26 308 P"
"tickPriceRanges": { "0": { "lowerLimit": "int", "tick": "float", "upperLimit": "NoneType" } }

// Source: packages/matriz-client/documentation/Primary-API.md:330 (and :378, :454 — identical shape)
"tickPriceRanges":{ "0":{ "lowerLimit":0, "upperLimit":null, "tick":0.1 } }
```

### The envelope the risk parsers ignore (D-03's evidence)
```json
// Source: packages/matriz-client/documentation/Primary-API.md:1701-1706
{ "status":"OK",
  "detailedPosition":{ "account":"REM7374", "totalDailyDiffPlain":-184777,
                       "totalMarketValue":60240, "report":{ "FUTURE_OPTION_CALL":{ ... } } } }

// Source: packages/matriz-client/documentation/Primary-API.md:1817-1826, 1894
{ "status":"OK",
  "accountData":{ "accountName":"REM7374", "detailedAccountReports":{ "0":{ ... } },
                  "portfolio":60240, "currentCash":103065823 } }
```

### The existing exemption predicate the class+field exemption must join
```python
# Source: tools/check_surface_types.py:390-403
def _is_exempt(name: str) -> str | None:
    if name.startswith("__") and name.endswith("__"):
        return "dunder"
    if name.startswith("_"):
        return "private-helper"
    if name == "to_dict":
        return "serialize-out"
    return None
```
Note `_is_exempt` takes the **simple** member name by design ("never the qualified
`Class.member` form"). D-01c's exemption is qualified, so it needs a **separate**
class+field-keyed lookup, not a new clause here — adding `raw` to this function would exempt
every member named `raw` in all six packages.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `dict[str, Any]` passthrough on model fields | Closed typed roster + non-fatal `extra` divergences | Phase 36 (market-data) | The template this phase applies to matriz; the data-loss tradeoff is documented at `market_data_client/models.py:324-352` |
| Mapping axis duplicated in matriz + market-data | Deleted from market-data; matriz-only again | Phase 36 (D-05) | Do not restore the copy — `models.py:122-133` says so explicitly |
| Gate scans return annotations only | Gate also scans exported class field annotations | **This phase (D-01a)** | Closes the blind spot already named at `.planning/research/ARCHITECTURE.md:397` |
| Wire-named fields only (`LA`, `BI`, `SE`) | Wire fields + human alias properties | Phase 36 (market-data), this phase (matriz) | `snapshot.last.price` alongside `snapshot.LA.price` |

**Deprecated/outdated:**
- The `"NO envelope key, D-07"` claim in `_core.py:898`, `:915`, `:927`, `:942` — contradicted by
  the vendor doc (F-4). These comments must be corrected, not just the code.
- The `_mapping_value` docstring's Phase 29 CR-03 paragraph is already marked as ended
  (`models.py:122`); the rewrite should carry that history forward rather than drop it.

## Runtime State Inventory

This is a typing/refactor phase, so the inventory is required. Every category was checked.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | **None.** matriz-client has no datastore. The only persisted artifact is `.planning/verification/schemas/matriz-client/get-instrument-detail.json` (a read-only committed capture) — read as evidence, never rewritten by this phase. Verified by inspecting the schemas directory and confirming no DB/cache client exists in the package. | None (evidence only) |
| Live service config | **None.** No external service holds matriz-client configuration. The only live dependency is the remarkets sandbox, and D-MATZ-33 blocks all live runs this phase. Verified at `main_matriz.py:2547-2551` (hostname assert). | None — blocked by design |
| OS-registered state | **None.** No scheduler entries, no pm2/launchd/systemd units. `ws_client.py` spawns a daemon thread at runtime only (`ws_client.py:238-276`); nothing is registered with the OS. | None |
| Secrets / env vars | `PRIMARY_USER`, `PRIMARY_PASSWORD`, `PRIMARY_BASE_URL` are read by `main_matriz.py:2540` and the client state. **No secret name changes** in this phase — nothing renamed touches an env-var key. | None |
| Build artifacts | **None affected.** No package rename, no `pyproject.toml` name change, no egg-info staleness. `uv.lock` is unchanged (zero new dependencies). | None |

**The canonical question — after every file is updated, what runtime state still holds the old
shape?** Answer: only the committed test fixtures that encode the flat (unenveloped) risk body.
Those are files, caught by the grep list in Pitfall 4, and are the reason D-03 needs an explicit
fixture-update sub-task.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| uv | Every command | ✓ | 0.9.0 | — |
| Python (venv) | All | ✓ | CPython 3.12.11 | — |
| pytest suite (matriz) | Regressions | ✓ | 488 passed, 25.6s | — |
| mypy strict | SC-3 | ✓ | clean: "no issues found in 17 source files" | — |
| `tools/check_surface_types.py` | D-01 | ✓ | 0 violations | — |
| `tools/check_decode_intactness.py` | D-NO-06 guard | ✓ | passes | — |
| `tools/check_uniform_structure.py` | Structural guard | ✓ | "all 6 packages ... carry `models.py`, `types.py`" | — |
| `tools/surface_parity.py` | Parity guard | ✓ | passes (no output) | — |
| remarkets live API | Live verification of the 3 Risk fields | ✗ | — | **No fallback.** Blocked by D-MATZ-33; deferred to `LIVE-NOBJ-01` (Phase 39). The `vendor-documented, unmeasured` provenance class (D-04a) is the declared substitute |

**Missing dependencies with no fallback:** none that block this phase. The live API is
intentionally unavailable and the phase is designed around that constraint.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3+ with pytest-asyncio (`asyncio_mode = "auto"`), pytest-httpx |
| Config file | root `pyproject.toml` `[tool.pytest.ini_options]`, `pythonpath = ["."]` |
| Quick run command | `uv run --package matriz-client pytest packages/matriz-client/tests -q` |
| Full suite command | `uv run --package matriz-client pytest packages/matriz-client/tests -q && uv run mypy packages/matriz-client/src && uv run python tools/check_surface_types.py && uv run python tools/check_decode_intactness.py` |
| Baseline (measured this session) | 488 passed, 25.64s; mypy clean; all four gates green |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| NOBJ-MTZ-01 | Gate detects a reintroduced `dict[str, Any]` **field** | unit | `pytest packages/matriz-client/tests/test_surface_types_red.py -x` | ❌ Wave 0 |
| NOBJ-MTZ-01 | `UnknownFrame.raw` exemption is reachable, not dead code | unit | `pytest packages/matriz-client/tests/test_surface_types_red.py -k exempt -x` | ❌ Wave 0 |
| NOBJ-MTZ-01 | Gate stays green on the real tree after extension | unit | `pytest packages/iol-client/tests/test_surface_types_red.py::test_gate_is_green_on_the_real_tree -x` | ✅ (floors only — will not falsely redden) |
| NOBJ-MTZ-01 | `tickPriceRanges` decodes the baseline into `dict[str, TickPriceRange]` | unit | `pytest packages/matriz-client/tests/test_models.py -k tickPriceRange -x` | ❌ Wave 0 |
| NOBJ-MTZ-01 | `portfolio` is `None` (not `{}`) on an empty payload | unit | `pytest packages/matriz-client/tests/test_decode.py -k portfolio -x` | ✅ exists, assertion must flip |
| NOBJ-MTZ-01 | Enveloped risk body populates `report`/`detailedAccountReports` | unit | `pytest packages/matriz-client/tests/test_core.py -k envelope -x` | ❌ Wave 0 |
| NOBJ-MTZ-01 | Undeclared inner keys surface as non-fatal `extra` divergences | unit | `pytest packages/matriz-client/tests/test_decode.py -k extra -x` | ✅ mechanism tested; needs a case for the new models |
| NOBJ-MTZ-01 | Mapping axis routes values through `walk_field` with the shared sink | unit | `pytest packages/matriz-client/tests/test_decode.py -k mapping -x` | ✅ exists (`:427-520`), must be extended |
| NOBJ-MTZ-01 | `_convert` shim still coerces a bare `dict[str, Any]` | unit | `pytest packages/matriz-client/tests/test_decode.py -k convert -x` | ✅ exists, must keep passing |
| NOBJ-MTZ-02 | All six aliases return their wire field, identically | unit | `pytest packages/matriz-client/tests/test_null_object.py -k alias -x` | ❌ Wave 0 (real-class case; fixture case exists) |
| NOBJ-MTZ-02 | Aliases work on a REST-parsed **and** a WS-parsed snapshot | unit | `pytest packages/matriz-client/tests/test_null_object.py -k alias_surfaces -x` | ❌ Wave 0 |
| NOBJ-MTZ-02 | Aliases remain invisible to the walker (no divergence delta) | unit | `pytest packages/matriz-client/tests/test_null_object.py::test_adding_a_property_alias_does_not_change_the_divergence_count -x` | ✅ exists — do not rewrite |
| SC-4 | WS daemon-thread paths stay green incl. per-connection decode mode | unit | `pytest packages/matriz-client/tests/test_ws_client.py packages/matriz-client/tests/test_ws_decode_mode.py -x` | ✅ exists |
| SC-3 | `mypy --strict` clean over the package | typecheck | `uv run mypy packages/matriz-client/src` | ✅ green today |

### Sampling Rate
- **Per task commit:** `uv run --package matriz-client pytest packages/matriz-client/tests -q`
- **Per wave merge:** add `uv run mypy packages/matriz-client/src` + all four `tools/` gates
- **Phase gate:** full suite + all six packages' tests green (the gate is cross-package) before
  `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `packages/matriz-client/tests/test_surface_types_red.py` — NEW; covers NOBJ-MTZ-01 gate
      non-vacuity + exemption reachability. Mirror `packages/iol-client/tests/test_surface_types_red.py`
      structure (`_write_fake_package` helper, `check_surface_types(root=tmp_path)`).
- [ ] Envelope regression cases in `packages/matriz-client/tests/test_core.py` — enveloped body
      populates; flat body raises `PrimaryAPIError`.
- [ ] Alias assertions on the real `MarketDataSnapshot` in `test_null_object.py`, exercising both
      a REST-parsed and a WS-frame-parsed instance.
- [ ] `tickPriceRanges` decode case driven from the committed baseline JSON.
- Framework install: **not needed** — pytest/pytest-httpx/mypy/ruff all present and green.

## Security Domain

`security_enforcement` is not disabled in config, so this section is included. matriz-client is
an outbound HTTP/WS client library with no server surface.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (unchanged) | Existing `X-Auth-Token` / HTTP Basic flows are untouched by this phase |
| V3 Session Management | no | No sessions; token TTL logic untouched |
| V4 Access Control | no | Client library; no authorization decisions made here |
| V5 Input Validation | **yes** | This phase *strengthens* it: four untyped mappings become validated typed models via `_decode.walk_field`, with divergence reporting |
| V6 Cryptography | no | No crypto touched; TLS is httpx's |
| V7 Error Handling & Logging | **yes** | `unwrap` raises typed `PrimaryAPIError` rather than leaking `KeyError`; the `RedactingFilter` region in `_logging.py` is untouched and must stay so (Check B hashes it) |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Untrusted vendor payload crashes the client on attribute access | Denial of Service | Null Object pattern + safe defaults (`_SafeModel.empty()`), already the package invariant |
| Vendor adds a key; a closed roster silently discards it | Information disclosure (loss) | Non-fatal `extra` divergence reporting → `matriz-client-findings.md`; the tradeoff is documented at `market_data_client/models.py:324-352` |
| Credentials leaking into divergence logs | Information disclosure | `RedactingFilter` in `_logging.py`, hash-locked by `check_decode_intactness` Check B — **do not touch** |
| Accidentally pointing a live run at production | Tampering | D-MATZ-33 hostname assert (`main_matriz.py:2547-2551`) — never bypassed |
| A weakened gate silently admitting untyped surface | Repudiation | Ratchet discipline: `check_surface_types.py:116-119` — "A red gate is never resolved by weakening the gate"; D-01d's RED fixture is the non-vacuity proof |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The vendor doc's enveloped risk shape reflects the live API's actual response, so `unwrap` is correct | F-4 / D-03 | If the live API returns a flat body, the fix converts working calls into raised `PrimaryAPIError`. **Unverifiable this phase** (D-MATZ-33). Mitigate: keep the change behind an explicit, reversible task, document it in the provenance docstring per Claude's Discretion, and make the flat-body behaviour a deliberate tested decision |
| A2 | `dict[str, Any] \| None` on an exported field should be treated as a violation (predicate strips `Optional`) | F-9 | Zero exported sites have this shape today, so the choice is unobservable now; if wrong it only makes the ratchet stricter than needed |
| A3 | The minimal roster derived from `Primary-API.md` matches the live inner record's field names | F-7 / D-07 | Undeclared keys become `extra` divergences (non-fatal, by design) and declared-but-absent keys become `missing`. This is precisely the outcome D-04a's `vendor-documented, unmeasured` label exists to advertise. No silent failure |
| A4 | `TickPriceRange.lowerLimit` as `float \| None` is correct despite the `int` observation | F-5 | The `float` arm widens `int` silently, so no divergence is fabricated — same as Phase 36's `BookLevel.price`. Low risk, but the docstring must say so or a future reader will "fix" it to `int` |

All four assumptions are consequences of the live-run block (D-MATZ-33), not of missing research.
A1 is the only one with real behavioural risk and it already has a documented escape hatch in
D-03 ("esta decisión se revierte sin bloquear el resto de la fase").

## Open Questions

1. **Should the D-01d RED fixture live in `packages/matriz-client/tests/` or extend the existing
   `packages/iol-client/tests/test_surface_types_red.py`?**
   - What we know: the iol file is the canonical, thoroughly documented home for this gate's
     non-vacuity proof, and its `test_gate_is_green_on_the_real_tree` already asserts about the
     whole tree. CONTEXT D-01d says "al estilo de" that file, which reads as *mirror*, not *extend*.
   - What's unclear: duplicating `_write_fake_package` across two packages is mild duplication
     the repo generally tolerates (no shared test lib by design).
   - Recommendation: **new file in `packages/matriz-client/tests/`**. It keeps the field-dimension
     proof adjacent to the package that motivated it, matches D-01d's wording, and the CI matrix
     collects both paths equally. Copy the helper — a shared test util would be the first
     cross-package test dependency in the repo.

2. **Does `parse_get_positions_response` (the sibling that *does* unwrap) also need review?**
   - What we know: it uses `parse_envelope_response` + `unwrap(data, "positions", path)`, which
     matches the vendor doc. It looks correct.
   - What's unclear: nothing — it is out of scope and appears right.
   - Recommendation: leave it. Cite it as the reference implementation for the D-03 fix.

3. **Should `_parse_risk_response` be deleted in favour of `parse_envelope_response`?**
   - What we know: the two are byte-identical except for the missing `unwrap` (F-4). Once D-03
     lands, `_parse_risk_response` becomes an exact duplicate of `parse_envelope_response`.
   - What's unclear: whether any other caller depends on the separate name. Grep shows only the
     two risk parsers call it.
   - Recommendation: fold it into `parse_envelope_response` and delete `_parse_risk_response`.
     This is a genuine simplification the phase enables, but it is optional — flag it for the
     planner as a clearly-scoped nice-to-have, not a requirement.

## Sources

### Primary (HIGH confidence — executed or read in this session)
- `uv run python tools/check_surface_types.py` — 0 violations, 330 definitions, 23 exempted
- `uv run --package matriz-client pytest packages/matriz-client/tests -q` — 488 passed
- `uv run mypy packages/matriz-client/src` — clean, 17 source files
- `uv run python tools/check_uniform_structure.py`, `tools/surface_parity.py` — green
- AST scan over `packages/*/src/**/*.py` for `Any`-bearing `AnnAssign` in `ClassDef` bodies (F-9)
- Roster introspection: `len(_safemodel_classes()) == 17` (F-13)
- `packages/matriz-client/src/matriz_client/models.py` — full read of `:75-320`, `:320-565`
- `packages/matriz-client/src/matriz_client/_core.py:224-302`, `:860-945`
- `packages/matriz-client/src/matriz_client/_decode.py:417-566`
- `packages/matriz-client/src/matriz_client/ws_client.py` — structure grep
- `packages/market-data-client/src/market_data_client/models.py:270-410`
- `tools/check_surface_types.py:386-562`, `tools/check_decode_intactness.py:84-290`
- `packages/iol-client/tests/test_surface_types_red.py:1-160`
- `packages/matriz-client/tests/test_null_object.py:80-331`, `test_decode.py:474-520`, `:921-933`
- `packages/matriz-client/documentation/Primary-API.md:325-460`, `:1695-1720`, `:1810-1900`
- `.planning/verification/schemas/matriz-client/get-instrument-detail.json`
- `.planning/verification/matriz-client-findings.md:1-30`
- `.planning/REQUIREMENTS.md:24-32`
- `main_matriz.py:2515-2552`

### Secondary (MEDIUM confidence)
- `.planning/phases/37-.../37-CONTEXT.md` — decisions reproduced verbatim; every factual claim in
  it was re-derived from primary sources above rather than taken on trust

### Tertiary (LOW confidence)
- None. No web search was performed: this phase introduces no external dependency and every
  question was answerable from the working tree.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; every existing tool version confirmed by execution
- Architecture: HIGH — every file, line number, and call path read directly; three CONTEXT
  claims corrected against source (F-4, F-6, F-13)
- Pitfalls: HIGH — each derived from a specific committed test or gate that will actually fire
- Live payload shapes for the 3 Risk fields: **MEDIUM** — vendor-documented, unmeasured by
  construction (D-MATZ-33). This is a declared limitation of the phase, not a research gap

**Research date:** 2026-08-29
**Valid until:** 2026-09-28 (30 days — internal codebase, no fast-moving external dependency;
invalidated earlier only by edits to `models.py`, `_core.py`, or `tools/check_surface_types.py`)
