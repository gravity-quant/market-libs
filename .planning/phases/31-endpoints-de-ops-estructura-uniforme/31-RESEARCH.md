# Phase 31: Endpoints de ops + estructura uniforme - Research

**Researched:** 2026-08-23
**Domain:** Typed response modelling of 5 ops endpoints across 2 packages (higyrus, market-data) + uniform `models.py`/`types.py` file layout across 6 packages, under a shipped mutating-gate and a published v0.4.0 wire contract
**Confidence:** HIGH (this phase is ~100% codebase-internal; every load-bearing claim below was verified by reading the file or executing the code in this session)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Diseño de modelos**

- **D-01:** Las 5 formas de respuesta se derivan de los schemas capturados en vivo en
  `.planning/verification/schemas/`, no de mocks ni de OpenAPI: `higyrus.get_health` → `Health`
  (`{status: str}`, 1 modelo); market-data gana ~7 modelos nuevos — `Health`/`HealthAuth` (`get_health`),
  `HealthFeed`/`FeedIngestor`/`FeedMarket`/`FeedPipeline` (`get_health_feed`, 3 niveles de nesting,
  `last_error`/`last_write_error` declarados `str | None`), `AddHolidaysResult`
  (`{days: list[CalendarDay], note: str, saved: int}`) y `DeleteHolidayResult`
  (`{day: str, deleted: bool}`). `add_holidays.days[]` **reutiliza `CalendarDay` existente**
  (`market_data_client/models.py:608-635`) — el schema vivo coincide campo por campo, incluidos
  los dos campos de hora `str | None` — nunca declarar un modelo de elemento paralelo.
- **D-02:** Cada paquete extiende su **propio `SafeModel` existente** verbatim — la base plana de
  higyrus (`higyrus_client/models.py:41-54`) y la base de market-data con el paso
  `_apply_mapping_policy` (`market_data_client/models.py:160-179`, reach top-level-only, pinneado
  por `test_no_mapping_carrying_model_is_ever_a_nested_field_type`). Ningún modelo nuevo declara un
  campo `dict[...]`; ninguno lleva `received_at` (health/holidays no son snapshots ni tienen
  staleness).
- **D-03:** `SafeModel.to_dict()` se agrega a las bases de higyrus y market-data, copiado verbatim
  de `iol_client/models.py:80-93` (precedente Phase 30, D-08 de `30-CONTEXT.md`). Necesario porque
  `main_market_data.py:628-643,2381-2389` y `main_higyrus.py:670,685` llaman `len()`/
  `isinstance(dict)` sobre el resultado — una dataclass frozen+slots rompe eso sin el escape hatch.
- **D-04:** `higyrus.get_health` conserva su comportamiento **raise-on-non-dict** existente
  (`HigyrusAPIError(status_code=0, ...)`, pinneado por `tests/test_core.py:412-415` y
  `tests/test_async_client.py:198-206`) y el carve-out 204→instancia zero-valued (no `{}`,
  precedente Phase 7 CR-02). `market-data.get_health`/`get_health_feed` **ganan** un guard
  equivalente (`parse_health_response` hoy no tiene ninguno).

**Wiring en `_core` + mutating-gate**

- **D-05:** Los dos parsers compartidos se **dividen en cuatro** — `parse_health_response`
  (hoy sirve `get_health` Y `get_health_feed`, `_core.py:280-285`) y
  `parse_calendar_write_response` (hoy sirve `add_holidays` Y `delete_holiday`,
  `_core.py:1083-1114`) ya no pueden compartirse: las formas vivas de cada par son no
  relacionadas. Cada parser nuevo lleva `@_decode._response_parser` (todos los demás parsers
  model-building del monorepo lo tienen; los dos que se reemplazan hoy NO, porque hoy no
  construyen modelos).
- **D-06:** Esta fase **no es zero-edit** — múltiples mocks existentes (`test_calendar_write.py`,
  `test_calendar_write_async.py`, ~132 líneas de referencias a `add_holidays`/`delete_holiday` en
  tests de market-data, 18 hits de `"status": "ok"` en tests de higyrus) fijan formas que el wire
  vivo contradice (ej. `{created, skipped}` mockeado vs. `{days, note, saved}` real) y se
  re-mockean mecánicamente a la forma del schema vivo, siguiendo el precedente Phase 30-03. Blast
  radius comparable a esa fase, no un cambio quirúrgico.
- **D-07:** **No existe hoy** el guard AST que ROADMAP.md asume verde para `_ensure_mutation_allowed()`
  como primer statement — grep del repo no encuentra ningún check AST de orden de statements sobre
  `client.py`/`aio.py` de market-data (el único test con "gate" en el nombre,
  `verification/test_main_market_data_no_gate_bypass.py`, parsea el *driver*, no el cliente). La
  invariante hoy solo está cubierta conductualmente (`test_calendar_write.py:403-467`,
  `test_calendar_write_async.py:382-420`, `test_mutation_gate.py`: refused → zero HTTP requests).
  Esta fase **construye** el guard AST desde cero (o, alternativa documentada pero no preferida,
  restatea el criterio 3 explícitamente contra los tests conductuales existentes) — Claude decide
  cuál al planificar, con preferencia por construir el guard AST (paridad con el precedente
  `test_main_matriz_has_no_singleton_path_references` de Phase 15/30).
- **D-08:** El test de request byte-idéntico (criterio 2) es una pieza **nueva** — no hay patrón
  reusable en el repo hoy (los tests existentes comparan método/path/un header/body via
  `json.loads` pieza por pieza, nunca el set completo de headers ni el query string). Se construye
  como una captura-y-compara: tupla congelada `(method, str(url), sorted(headers.items()),
  content_bytes)` capturada del código pre-cambio y pinneada como literal — comparación de **bytes
  crudos**, nunca `json.loads(...)`, para no perder drift de key-ordering en `HolidaysIn.to_dict()`
  (`models.py:487-489`).

**Estructura uniforme (models.py + types.py)**

- **D-09:** El criterio 4 son **7 archivos nuevos, no 4**: `types.py` en **5** paquetes (higyrus,
  iol, market-data, ambito, wallets — solo matriz tiene uno hoy, 130 líneas en
  `matriz_client/types.py`), más `models.py` en ambito y wallets. higyrus/iol/market-data ya
  tienen `models.py` pero no `types.py` — y no tienen contenido `Literal` real para poner ahí
  todavía (el D-lock de Phase 29 prohíbe `Literal` en campos RESPONSE; la promoción de
  `mercado`/`plazo` de iol queda diferida a Phase 33). Los 5 `types.py` nuevos son **placeholders
  con docstring**, no contenido funcional.
- **D-10:** `wallets-client` recibe `models.py` + `types.py` **docstring-only, con `__all__:
  list[str] = []`** — sin `SafeModel`, sin clases, sin importar `_decode`. Verificado contra
  `tools/check_decode_intactness.py`: Check D (líneas ~625-662) nunca inspecciona `models.py`/
  `types.py`, solo la presencia/ausencia de `_decode.py`. Dar a wallets un `SafeModel` real
  rompería su import (no tiene módulo `_decode` del que importar) y enrojecería su leg completo de
  CI matrix. La exención de Phase 29 (`29-WALLETS-EXEMPTION.md`) **sigue válida sin editar**
  `tools/check_decode_intactness.py` — el prosa de ese doc queda desactualizada (dice "no
  `models.py`") pero nada se pone rojo; Claude decide si vale la pena una nota de actualización
  liviana al doc o dejarlo como está para que Phase 32/una fase futura lo supere formalmente.
- **D-11:** `ambito-financiero-client` recibe el mismo tratamiento docstring-only que wallets —
  `models.py`/`types.py` vacíos pero presentes, sin `SafeModel` (ámbito ya tiene su propio patrón
  de parsing sin modelos, `_parsing.py::parse_ar_decimal`, que esta fase no toca).
- **D-12:** El check de existencia para el criterio 4 se implementa como **script nuevo
  stdlib-only bajo `tools/`**, cableado como step adicional del job `lint` **existente** en
  `ci.yml` — mismo patrón que el step `decode-intactness` ya presente (cross-package por
  naturaleza, no puede vivir en el job `test` per-package, y `verification/` nunca corre en CI
  como documenta el propio comentario inline de `ci.yml`). Nunca un test pytest bajo
  `verification/`.

**Cobertura de tipos fuera de esta fase**

- **D-13:** Los 4 modelos nuevos de market-data **no** quedan cubiertos por mypy en CI esta fase —
  `market-data-client/src` está ausente de `files` en `pyproject.toml:97` y del loop mypy de
  `ci.yml:85` (enrolamiento = D-16, Phase 32). Es un gap esperado, no algo a cerrar acá. Correr
  `uv run mypy packages/market-data-client/src` localmente como paso de aceptación aunque CI no lo
  corra. higyrus SÍ está enrolado, así que su modelo `Health` nuevo sí queda strict-typechecked
  por CI.

### Claude's Discretion

- Nombres exactos de las clases nuevas de market-data (`Health`/`HealthAuth`/`HealthFeed`/
  `FeedIngestor`/`FeedMarket`/`FeedPipeline`/`AddHolidaysResult`/`DeleteHolidayResult` son los
  sugeridos por la evidencia) — dentro de D-01.
- Construir el guard AST vs. restatear el criterio 3 contra tests conductuales (D-07) — preferencia
  documentada por el guard AST, decisión final en planning.
- Si actualizar la prosa de `29-WALLETS-EXEMPTION.md` o dejarla para una fase futura (D-10).
- Forma exacta del script de existence-check (nombre de archivo, mensajes de error) dentro de D-12.

### Deferred Ideas (OUT OF SCOPE)

- Contenido real de `Literal` en los `types.py` nuevos de higyrus/iol/market-data/ambito/wallets —
  Phase 33 (censo vivo, DT-07 / D-lock RESPONSE-Literal de Phase 29)
- Enrolamiento de `market-data-client` en mypy `files`/import-linter/`ci.yml:85` loop — Phase 32
  (D-16)
- Gate AST de superficie (cero `Any`/`dict[str, Any]` en `__all__`) — Phase 32 (GATE-TYP-01)
- Actualización formal de `29-WALLETS-EXEMPTION.md` reconociendo que wallets ahora tiene
  `models.py`/`types.py` vacíos — decisión abierta (D-10), posiblemente Phase 32 o una nota liviana
  en esta fase
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| **TYP-02** | Los 5 endpoints de ops devuelven modelos tipados (`higyrus.get_health`; `market-data.get_health`/`get_health_feed`/`add_holidays`/`delete_holiday`) — cambio response-only, con prueba de request byte-idéntico para las 2 mutaciones ya publicadas en v0.4.0 (no perturbar el mutating-gate). | § Exact Model Shapes (live-schema-derived, all 5 dumped verbatim); § Signature Site Census (20 sites enumerated with file:line); § Parser Split Plan; § Byte-Identical Request Test — **ground truth captured and pinned in this session**, plus proof that HEAD's request-emission code is unchanged since tag `market-data-client-v0.4.0`; § Mutating-Gate Invariant (16 call sites verified). |
| **TYP-03** | Los 6 paquetes presentan estructura uniforme `models.py` + `types.py` (mínimos pero presentes en ambito y wallets). | § File Layout Census (exact `ls` of all 6 packages → 7 files missing); § Existence-Check Wiring (`ci.yml` lint job, `decode-intactness` step as the mirror pattern); § `check_decode_intactness.py` Check D non-interference proof. |
</phase_requirements>

---

## Summary

This phase is **almost entirely codebase-internal**. There is no new library to choose, no external
API to learn, and no dependency to add — the whole job is (a) declaring 9 new frozen dataclasses
whose exact field sets are already committed to `.planning/verification/schemas/`, (b) splitting
two shared `_core.py` parsers into four decorated ones, (c) re-mocking ~180 test lines that pin
shapes the live wire contradicts, (d) creating 7 near-empty module files, and (e) wiring one new
stdlib-only existence check into the `lint` CI job. Accordingly, the value of this research is
**verification of `31-CONTEXT.md`'s D-01..D-13 against the working tree**, not discovery of new
technology.

**Verdict on the CONTEXT: 13 of 13 decisions are directionally CONFIRMED. Zero are contradicted.**
Every file path, line number, and code claim was checked. Three decisions carry numeric or scope
corrections (D-01 model count, D-03 driver-site treatment, D-07 guard placement) and eight
material gaps were found that the CONTEXT does not cover at all — most consequentially **G-1**
(`verification/snapshots/higyrus-client-surface.txt` is a golden file that pins
`get_health : function : () -> 'dict[str, Any]'` and must be regenerated) and **G-3** (Phase 30's
own CR-01 finding says feeding `to_dict()` into `schema_of` projects wire drift away — so D-03's
`to_dict()` prescription is right for the `len()`/`isinstance` sites and **wrong** for the
schema-snapshot sites).

The single highest-risk technical item is the byte-identical request test (criterion 2). This
research **executed the real request-building code path** and captured the exact frozen tuple for
both mutations, then proved by `git diff` against tag `market-data-client-v0.4.0` that nothing on
the request-emission path has changed since that release — so the captured value **is** the v0.4.0
value. Two non-obvious hazards for that pin are documented: `user-agent` embeds
`httpx.__version__` (couples the literal to `uv.lock`), and `request.extensions["request_id"]` is a
fresh `uuid4` per call (must never enter the frozen tuple).

**Primary recommendation:** Model from the committed live schemas verbatim; split both parsers and
decorate all four; pin the byte-identical request as raw bytes using the tuple captured in
§ Byte-Identical Request Test; put the new mutating-gate AST guard **in-package** under
`packages/market-data-client/tests/` (it runs in the 6×2 CI matrix; `verification/` does not run in
CI at all); and treat `verification/snapshots/higyrus-client-surface.txt` regeneration as a
mandatory task, not an afterthought.

---

## Architectural Responsibility Map

Tiers here are library-internal layers, not deployment tiers (this is a client-library monorepo).

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|--------------|----------------|-----------|
| Response shape declaration (9 new dataclasses) | `models.py` (per package) | — | `SafeModel` subclasses are the decode target; `_decode.walk_model` reads their `get_type_hints()`. Nothing else may own a field list. |
| Wire decode + divergence reporting | `_decode.py` (verbatim 5×) | — | **Untouchable this phase.** Byte-hash-pinned by `tools/check_decode_intactness.py`; any edit reddens the `lint` job. |
| Response parsing + shape guards | `_core.py` parsers | — | Pure functions taking `httpx.Response`. Both shells call the same parser — this is the sync/async parity mechanism (DT-04: codegen permanently shelved, parity comes from a shared `_core`). |
| Request building (`RequestSpec`) | `_core.py` builders | — | **Must not change at all.** Criterion 2 is a response-only assertion; builders own `idempotent=`, path, and body. |
| Mutation authorization | `client.py` / `aio.py` methods | `tests/test_mutation_gate.py` | `_ensure_mutation_allowed()` is the literal first statement of 8 methods per shell. Gate lives in the shell, never in `_core` (an IO-free state read must precede any dispatch). |
| Public surface (`__all__`) | `__init__.py` | `verification/snapshots/*.txt`, `tests/test_public_surface_market_data.py` | Two independent golden nets. higyrus is covered by the cross-package one; market-data by the in-package one. |
| Cross-package structural invariants | `tools/*.py` + `ci.yml` `lint` job | — | `verification/` **never executes in CI** (the `test` job passes an explicit per-package path that overrides `testpaths`). Cross-package gates must be `tools/` scripts in `lint`. |
| Per-package regression nets | `packages/*/tests/` | — | Runs in the 6×2 matrix. This is where a market-data-only AST guard belongs. |
| Live drift detection | `main_*.py` drivers + `verification/schema.py` | `.planning/verification/schemas/*.json` | Drivers feed **raw wire** (not model projections) into `schema_of` — see G-3. |

---

## D-01..D-13 Verification Ledger

Every row was checked against the working tree at `HEAD` on branch `milestone/v1.5-mutations`.

| # | Verdict | Evidence |
|---|---------|----------|
| **D-01** | **CONFIRMED, with 3 corrections** | All 7 live schema files exist and were dumped verbatim (§ Exact Model Shapes). `CalendarDay` reuse is **exact**: shipped fields `day/closed/description/open_time: str\|None/close_time: str\|None` match the live `add_holidays.days[]` schema field-for-field. **Correction (a):** the model count is **8** new market-data classes (`Health`, `HealthAuth`, `HealthFeed`, `FeedIngestor`, `FeedMarket`, `FeedPipeline`, `AddHolidaysResult`, `DeleteHolidayResult`), not "~7" — and D-13 says "4", also wrong. Total across both packages: **9** (higyrus `Health` + 8). **Correction (b):** `CalendarDay` is at `models.py:609-635`, not 608. **Correction (c):** `last_error`/`last_write_error` were captured as `NoneType` **only** — the non-null type is unobserved, so `str \| None` is an assumption (A1), and **7 further health-feed fields** carry the same single-healthy-state nullability risk (§ Open Question 1). [VERIFIED: file read + JSON dump] |
| **D-02** | **CONFIRMED + hard constraint discovered** | higyrus `SafeModel` at `models.py:41` (flat `walk_model` + `current_sink()`); market-data `SafeModel` at `models.py:160` (adds `_apply_mapping_policy` with an explicit Lock-8 silent-sink branch for non-dict payloads). **New constraint the CONTEXT does not state:** `packages/market-data-client/tests/test_decode.py:1239` asserts `overriding == {"MarketDataSnapshot", "Symbol"}` by **equality** — so **no new model may declare a `from_api` override**, or that test fails. Companion at `:1203` forbids any mapping-carrying (`dict[...]`-declaring) model from being a nested field type, which is exactly why D-02's "ningún modelo nuevo declara un campo `dict[...]`" is load-bearing (4 of the 8 new models ARE nested field types). [VERIFIED: file read] |
| **D-03** | **CONFIRMED for the stated sites; INCOMPLETE** | `iol_client/models.py:80` `to_dict()` exists verbatim as described (`dataclasses.asdict(cast(Any, self))`). Driver sites confirmed: `main_higyrus.py:670` (`isinstance(raw, dict) or len(raw) < 1`), `:685` (`f"keys={len(raw)}"`), `main_market_data.py:2389` (`public_keys={len(created)}`). **Gap:** the schema-snapshot sites (`main_market_data.py:627-641`, `main_higyrus.py` probe 15 → `schema_of(raw_payload)`) must **not** receive `to_dict()` — see G-3. [VERIFIED: file read] |
| **D-04** | **CONFIRMED + a third guard contract found** | `higyrus_client/_core.py:426` `parse_get_health_response`: 204/empty → `{}` (Phase 7 CR-02 carve-out, documented in the docstring), non-dict → `HigyrusAPIError(status_code=0, errors=[{title: "shape mismatch", detail: "expected dict, got list"}])`. Pinned by `tests/test_core.py:406-415` and `tests/test_async_client.py:198-206` (which asserts the exact `title` and `detail` strings). `market_data_client/_core.py:280` `parse_health_response` has **zero** guards — `data: dict[str, Any] = resp.json()` with an unchecked annotation. **Gap:** `parse_calendar_write_response` (`_core.py:1083`) has a **third**, distinct, deliberately-documented tolerance contract (T-26-13: empty body / `null` / list / scalar all → `{}`) that CONTEXT D-04 does not address — see G-4. [VERIFIED: file read] |
| **D-05** | **CONFIRMED exactly** | `parse_health_response` at `_core.py:280-285`, called from `client.py:429,435` and `aio.py:438,444`. `parse_calendar_write_response` at `_core.py:1083-1114`, called from `client.py:702,724` and `aio.py:711,733`. Neither is decorated. **7** market-data parsers ARE decorated (`_core.py:846,878,928,945,962,1029,1066`), 1 in higyrus (`_core.py:457`), 3 in iol (`_core.py:329,344,412`) — confirming "every model-building parser carries it". `git diff market-data-client-v0.4.0` shows those 7 decorations are exactly what Phase 29 added. [VERIFIED: file read + git diff] |
| **D-06** | **CONFIRMED and quantified** | market-data: **155** matching lines across **10** test files (`test_calendar_write.py` 49, `test_calendar_write_async.py` 47, `test_core.py` 28, `test_async_client.py` 7, `test_client.py` 7, `test_public_surface_market_data.py` 6, `test_decode.py` 4, `test_transport.py` 3, `test_with_options.py` 2, `test_with_options_async.py` 2). higyrus: **26** across 5 files (`test_core.py` 10, `test_client.py` 7, `test_async_client.py` 7, `test_decode.py` 1, `test_transport.py` 1); 18 hits of `"status": "ok"` across 4 files. Contradicted mocks confirmed: `test_calendar_write.py:260` mocks `{"created": 1}` vs. live `{days, note, saved}`; `:349` mocks `{"deleted": 1}` (int) and asserts `out == {"deleted": 1}` vs. live `{day: str, deleted: bool}`. [VERIFIED: grep + file read] |
| **D-07** | **CONFIRMED (guard absent) + placement correction** | 16 files use `ast.parse` under `verification/`; **every one targets a `main_*.py` driver**. `tools/check_decode_intactness.py` targets `_decode.py`. **No AST check anywhere targets `packages/*/src/*/client.py` or `aio.py`.** Behavioral coverage confirmed: `test_calendar_write.py:414-467` (5× refusal → `get_requests() == []`), `test_calendar_write_async.py:382-420`, `tests/test_mutation_gate.py` (helper-level, 7 scenarios × 2 surfaces). **Correction:** CONTEXT/ROADMAP imply placing it like the driver guards, i.e. under `verification/` — but `verification/` **never runs in CI**. See G-5 and § Recommended Guard Placement. [VERIFIED: grep across `verification/`, `tools/`, all `packages/*/tests/`] |
| **D-08** | **CONFIRMED + ground truth captured + 2 hazards** | Existing tests compare piecewise exactly as described (`test_calendar_write.py:258-272` asserts method / `url.path` / one header / `json.loads(content)`; `:345-357` adds `content == b""` and `"content-type" not in headers`). No full-header or query-string comparison exists anywhere. This session **executed the real builder + `build_request` path** and captured the exact tuple for both mutations (§ Byte-Identical Request Test), then proved via `git diff market-data-client-v0.4.0` that `build_add_holidays_request`, `build_delete_holiday_request`, `HolidayIn.to_dict`, `HolidaysIn.to_dict` and the `_request` construction block are **unchanged since the tag** — so the captured tuple IS the v0.4.0 value. **Hazard 1:** `user-agent` = `python-httpx/0.28.1`, embedding `httpx.__version__`. **Hazard 2:** `request.extensions["request_id"]` is a fresh `uuid4().hex` per call. [VERIFIED: code execution + git diff] |
| **D-09** | **CONFIRMED exactly** | `ls` of all six `src/` dirs: `types.py` exists **only** in matriz; `models.py` exists in iol, higyrus, matriz, market-data — absent in ambito and wallets. **7 new files** exactly as stated (5 `types.py` + 2 `models.py`). [VERIFIED: directory listing] |
| **D-10** | **CONFIRMED + doc already stale** | `tools/check_decode_intactness.py::check_d_roster()` (lines 625-662) inspects only `pkg.decode_path.is_file()` for in-scope packages, the same for exempt packages (inverted), and a set-difference of `packages/` dir names against the roster. It never opens `models.py` or `types.py`. Adding them to wallets/ambito **cannot** redden it. wallets has no `_decode.py` (confirmed by listing) so a real `SafeModel` would indeed fail at import. **Note:** `29-WALLETS-EXEMPTION.md`'s module table is **already stale** independent of this phase — it says iol has no `models.py`, but Phase 30 added one. [VERIFIED: file read] |
| **D-11** | **CONFIRMED** | ambito has `_parsing.py` with `parse_ar_decimal`, no `models.py`, no `types.py`. Its public surface (`verification/snapshots/ambito-financiero-client-surface.txt`) is exceptions + `Client`/`AsyncClient` + 1 function — no models. A docstring-only `models.py`/`types.py` not re-exported from `__init__.py` changes nothing in that snapshot. [VERIFIED: file read] |
| **D-12** | **CONFIRMED exactly** | `.github/workflows/ci.yml` `lint` job carries the `decode-intactness` step running `uv run python tools/check_decode_intactness.py`, with an inline comment stating verbatim that it cannot live under `verification/` because "el job `test` pasa un path explícito que pisa `testpaths`, así que ese directorio nunca corrió en CI". Exact pattern to mirror. [VERIFIED: file read] |
| **D-13** | **CONFIRMED (mypy), count wrong** | `pyproject.toml:97` `files = [higyrus, wallets, matriz, iol, ambito]` — market-data absent. `ci.yml:85` loop iterates the same 5. `[tool.importlinter] root_packages` (`pyproject.toml:141-146`) lists only 4 (ambito, iol, higyrus, matriz). `verification/test_public_surface._PACKAGES` lists 4. So the four enrollment lists are 5/6, 4/6, 5/6, 4/6 — exactly the D-16 discrepancy. **Correction:** "los 4 modelos nuevos" → **8**. [VERIFIED: file read] |

---

## Gaps Not Covered by 31-CONTEXT.md

These are the actionable deltas. Each is stated as a planning obligation.

### G-1 — `verification/snapshots/higyrus-client-surface.txt` is a golden file that pins the old signature (HIGH)

```
verification/snapshots/higyrus-client-surface.txt:33
get_health : function : () -> 'dict[str, Any]'
```

The file has an 8-line header stating *"DO NOT EDIT BY HAND. To accept an intentional change, run
the regen script above and commit the diff alongside the source change that justifies it."*
Two rows change: line 33's return annotation, plus a new `Health : class : (status: 'str') -> None`
row (higyrus `__init__.py:56-72` re-exports every model into `__all__`, and the snapshot enumerates
`__all__`).

**Phase 30 did exactly this for iol** — `verification/snapshots/iol-client-surface.txt` now carries
`Cotizacion : class : (...)` and `get_quote : function : (...) -> 'Cotizacion'`. The regen command
is `uv run python verification/regen_snapshots.py`.

**Planning obligation:** one task, in the same commit as the higyrus source change. Note that
because `verification/` never runs in CI, a stale snapshot is **green in CI and red locally** —
the worst failure mode. Do not rely on CI to catch this.
[VERIFIED: file read + git history]

### G-2 — market-data's in-package public-surface net has a hand-maintained name tuple (MEDIUM)

`packages/market-data-client/tests/test_public_surface_market_data.py:32` defines
`_NEW_PUBLIC_NAMES` (16 entries) and `:53` defines `_MUTATION_METHODS` (8 entries). Its docstring
states this file exists precisely because the cross-package `verification/test_public_surface.py`
**excludes** `market_data_client`. If the 8 new market-data models are re-exported from
`__init__.py` (they should be — `models.py:71-85` already re-exports all 13 existing models), this
tuple should gain them. Unlike G-1 this test **does** run in CI (6×2 matrix), but it asserts
"every listed name is importable and in `__all__`", not "every exported name is listed" — so
omitting them is silently green. Adding them is the intent-preserving move.
[VERIFIED: file read]

### G-3 — D-03's `to_dict()` prescription is wrong for the schema-snapshot sites (HIGH)

Phase 30 discovered and recorded this as CR-01. From `main_iol.py:336` `_capture_raw_wire`'s
docstring, verbatim:

> *"los wrappers públicos devuelven modelos. Para cuando un modelo existe, el walker de la Phase 29
> ya coercionó cada campo no-opcional a su tipo declarado y descartó cada clave que ningún campo
> declara, así que `schema_of` sobre la proyección del modelo es función de la **declaración**, no
> del wire: un `float→str`, una clave agregada y una clave quitada son las tres invisibles."*

And from STATE.md, the ratified Phase 30 decision:

> *"Para los endpoints modelados de iol la señal autoritativa de drift pasa a ser el censo de
> divergencias, no el diff del snapshot de schema — `to_dict()` proyecta el drift afuera por
> construcción; carry-forward FA-09 a Phase 33 (30-04)"*

The affected sites in this phase:

| Site | Today | After typing |
|------|-------|--------------|
| `main_market_data.py:627-641` | `_write_schema_snapshot(raw=health, ...)` and `raw=feed` — raw dicts | Would become model projections → drift-blind |
| `main_higyrus.py` probe 15 → `schema_of(raw_payload)` fed by probe 3/4's returned `raw` | raw dict | Same |
| `main_market_data.py:2372-2384` (`add_holidays`) | Already uses `_mutate_raw_sync(...).json()` — **raw wire** | Already correct, no change |

**Planning obligation:** three options, pick one explicitly — (a) mirror `_capture_raw_wire` for
the two health endpoints, (b) accept the blindness and record the FA-09-style carry-forward to
Phase 33 in the driver docstring (what Phase 30 ultimately did for iol), or (c) keep `to_dict()`
only at the `len()`/`isinstance` sites and leave the snapshot path untouched by capturing the raw
body separately. **D-03 remains correct for `main_higyrus.py:670,685` and
`main_market_data.py:2389`** — those are `len()`/`isinstance` sites, not `schema_of` sites.
[VERIFIED: file read + STATE.md]

### G-4 — `parse_calendar_write_response`'s tolerance contract is a third guard the CONTEXT does not address (MEDIUM)

D-04 covers two guard contracts (higyrus raise-on-non-dict, market-data health gains one). It says
nothing about the calendar-write parser's **deliberately documented** T-26-13 tolerance:

```python
resp.read(); raise_for_response(resp)
if not resp.content: return {}
raw = resp.json()
if not isinstance(raw, dict): return {}
return raw
```

The docstring argues at length that this tolerance is *"deliberada"* and that this is *"why it is
a NEW function rather than a reuse of `parse_health_response`"*. When these become
`AddHolidaysResult` / `DeleteHolidayResult`, the two `return {}` branches must resolve to something
— most plausibly `Model.from_api(None)` (the zero-valued-instance carve-out, matching Phase 7
CR-02 and `parse_calendar_config_response`'s existing D-07 fallback at `_core.py:1077`). Choosing
`raise` instead would be a **behavior change on a published mutation**, which criterion 2's
response-only framing does not authorize without an explicit decision.

**Planning obligation:** decide and document, per parser. Recommendation: preserve tolerance as
`Model.from_api(None)` (there is direct in-package precedent one function above).
[VERIFIED: file read]

### G-5 — the new AST guard must not go under `verification/` (HIGH)

`ci.yml` `test` job runs `pytest packages/${{ matrix.package }} ...`, an explicit path that
overrides `[tool.pytest.ini_options] testpaths = ["packages", "tests", "verification"]`. The
`decode-intactness` step's inline comment states this outright, and STATE.md records it as a
**Phase 32 blocker**: *"`verification/` nunca corrió en CI"*.

**Recommendation (§ Recommended Guard Placement):** put the mutating-gate AST guard **in-package**
at `packages/market-data-client/tests/test_mutation_gate.py` (or a sibling
`test_mutation_gate_ast.py`). It is a single-package invariant, so the cross-package `tools/`
mechanism is unnecessary, and in-package gets it into the 6×2 matrix immediately. Reserve `tools/`
+ `lint` for the genuinely cross-package existence check of D-12.
[VERIFIED: file read + STATE.md]

### G-6 — `client.py:684` carries a docstring that contradicts the shipped `idempotent=` flag (MEDIUM)

`Client.add_holidays`'s docstring says:

> *"The builder marks this spec `idempotent=False` — the ONLY such spec in the package (DM-03 /
> D-04) — so `RetryTransport` does NOT retry it"*

But `_core.build_add_holidays_request` sets **`idempotent=True`**, corrected on live measurement in
Phase 27 (D-20: two identical POSTs left exactly 1 row; the endpoint upserts by date). Its own
docstring says *"Note that no builder in this package carries `idempotent=False` any more."*

Success criterion 3 says *"ningún builder cambia su flag `idempotent=`"*. Ground truth: **both
holiday builders are `idempotent=True` today**, and criterion 3 means they must stay `True`. A
planner reading the stale `client.py` docstring would conclude the opposite. The `aio.py:690`
counterpart should be checked for the same drift.

**Planning obligation:** either fix the stale docstring in-phase (cheap, low risk, response-only)
or explicitly note it as out of scope. Do not let it silently seed a wrong "restore
`idempotent=False`" edit.
[VERIFIED: file read]

### G-7 — incidental `get_health` assertions outside the calendar-write test files (MEDIUM)

Three test files use `get_health` as a convenient throwaway endpoint and assert its **return value
as a dict**:

| File:line | Assertion |
|-----------|-----------|
| `packages/market-data-client/tests/test_with_options.py:82,94` | `assert client.get_health() == {"status": "ok"}` / `{"status": "ok2"}` |
| `packages/market-data-client/tests/test_with_options_async.py:100,112` | same, async |
| `packages/market-data-client/tests/test_transport.py:107` | `assert market_data_client.get_health() == {"status": "ok"}` |

These are retry/with-options tests that will fail on the type change for reasons unrelated to their
subject. Easy fix (`.status == "ok"`), but they are outside the two calendar-write files D-06 names,
so they will not be found by a `add_holidays|delete_holiday` grep.
[VERIFIED: grep + file read]

### G-8 — decode-scope semantics change for `get_health` when the parser gains `@_response_parser` (LOW, verified benign)

`_decode._response_scope()` retires the scope on exit (`scope.closed = True`) but never unsets
`DECODE_SCOPE`. Today `get_health` leaves an **open** scope bound after returning; after decoration
it will leave a **closed** one. `_decode.current_sink()` treats a closed scope as "none bound" and
returns a fresh `DecodeScope()`.

Four decode tests use `get_health` (`test_decode.py:932,943,975,977`). Analysis:

- `test_strict_mode_bound_by_sync_request` / `..._async_request` — assert `STRICT_DECODE.get() is True`. Unaffected.
- `test_no_reset_after_request` (`:948-966`) — calls `client._request(spec)` **directly**, never the parser. Unaffected.
- `test_request_binds_a_fresh_scope_per_response` (`:969-984`) — asserts `first is not second` after two `get_health()` calls. `_request` binds a fresh scope each time regardless; the object identities still differ. Unaffected.

No test asserts `.closed` state after a `get_health()` call (the `.closed` assertions at
`test_decode.py:1300,1314,1315,1323` drive `_response_scope` directly). **Net: benign**, but the
behavior *does* change and the planner should not be surprised by it. Note also a grep trap:
`test_reference_client.py:138`'s `result[0].closed is True` is `CalendarDay.closed`, an unrelated
field with a colliding name.
[VERIFIED: file read + source analysis of `_decode._response_scope`]

---

## Exact Model Shapes (live-schema-derived)

All five schemas exist under `.planning/verification/schemas/` and were dumped verbatim this
session. Sync and async captures for the two mutations are **identical**, which is itself evidence
of surface parity.

### `higyrus.get_health` → `Health` (1 model)

`.planning/verification/schemas/higyrus-client/get-health.json` (endpoint `/api/health`, captured
2026-06-08):

```json
{ "status": "str" }
```

```python
@dataclass(frozen=True, slots=True)
class Health(SafeModel):
    status: str
```

### `market-data.get_health` → `Health` + `HealthAuth` (2 models)

`market-data-client/get-health.json` (endpoint `/health`, captured 2026-07-31):

```json
{ "auth": { "configured": "bool", "enabled": "bool", "issuer": "str" }, "status": "str" }
```

```python
@dataclass(frozen=True, slots=True)
class HealthAuth(SafeModel):
    configured: bool
    enabled: bool
    issuer: str

@dataclass(frozen=True, slots=True)
class Health(SafeModel):
    status: str
    auth: HealthAuth
```

### `market-data.get_health_feed` → `HealthFeed` + `FeedIngestor` + `FeedMarket` + `FeedPipeline` (4 models, 3 nesting levels)

`market-data-client/get-health-feed.json` (endpoint `/health/feed`), full observed schema:

```
HealthFeed          active_symbols:int  newest_received_at:str  oldest_received_at:str
                    staleness_seconds:float  status:str  symbols_with_data:int
                    ingestor:FeedIngestor

FeedIngestor        connected:bool  frames_total:int  heartbeat_age_seconds:float
                    last_error:NoneType  last_frame_age_seconds:float  last_frame_at:str
                    present:bool  reason:str  reconnects:int  rows_written:int
                    started_at:str  state:str  symbols_subscribed:int  uptime_seconds:int
                    market:FeedMarket  pipeline:FeedPipeline

FeedMarket          enabled:bool  is_open:bool  last_business_day:str  local_time:str
                    next_transition:str  reason:str  session_close:str  session_open:str
                    state:str

FeedPipeline        batch_interval_ms:int  conserved:bool  flushes:int  frames_accepted:int
                    frames_coalesced:int  frames_unknown_symbol:int  last_flush_ms:float
                    last_write_at:str  last_write_error:NoneType  pending:int
                    pending_peak:int  rows_skipped_stale:int
```

Two fields observed only as `null` → `str | None` per D-01 (A1). See Open Question 1 for the seven
further fields whose nullability is under-determined by a single healthy-state capture.

### `market-data.add_holidays` → `AddHolidaysResult` (1 model, reusing `CalendarDay`)

`market-data-client/add-holidays-{sync,async}-response.json` (identical):

```json
{ "days": [ { "close_time":"NoneType","closed":"bool","day":"str",
              "description":"str","open_time":"NoneType" } ],
  "note": "str", "saved": "int" }
```

Shipped `CalendarDay` (`models.py:609-635`):

```python
day: str
closed: bool
description: str
open_time: str | None = None
close_time: str | None = None
```

**Field-for-field match confirmed.** D-01's "never declare a parallel element model" holds.

```python
@dataclass(frozen=True, slots=True)
class AddHolidaysResult(SafeModel):
    days: list[CalendarDay]
    note: str
    saved: int
```

`CalendarDay` becomes a nested field type here — it has no `from_api` override and declares no
`dict[...]` field, so both `test_decode.py:1203/:1239` preconditions hold.

### `market-data.delete_holiday` → `DeleteHolidayResult` (1 model)

`market-data-client/delete-holiday-{sync,async}-response.json` (identical):

```json
{ "day": "str", "deleted": "bool" }
```

```python
@dataclass(frozen=True, slots=True)
class DeleteHolidayResult(SafeModel):
    day: str
    deleted: bool
```

Note: `test_calendar_write.py:349` currently mocks `{"deleted": 1}` (int) — contradicted by the
live `bool`. This is exactly the D-06 class of re-mock.

**Total: 9 new dataclasses** (higyrus 1, market-data 8).

---

## Signature Site Census (20 sites, all `dict[str, Any]` today)

Criterion 1 requires zero `dict[str, Any]` in the method AND shim signatures, sync AND async.

### higyrus-client (4 sites + 1 parser)

| File:line | Symbol |
|-----------|--------|
| `client.py:450` | `Client.get_health(self) -> dict[str, Any]` |
| `client.py:602` | module shim `get_health() -> dict[str, Any]` |
| `aio.py:442` | `AsyncClient.get_health(self) -> dict[str, Any]` |
| `aio.py:608` | module shim `async get_health() -> dict[str, Any]` |
| `_core.py:426` | `parse_get_health_response(resp) -> dict[str, Any]` |

Plus `__init__.py:38,99` (re-export, `__all__`) and the `Health` class addition.

### market-data-client (16 sites + 2 parsers → 4)

| File:line | Symbol |
|-----------|--------|
| `client.py:425` / `:431` | `Client.get_health` / `get_health_feed` |
| `client.py:818` / `:823` | module shims |
| `client.py:681` / `:704` | `Client.add_holidays` / `delete_holiday` |
| `client.py:950` / `:955` | module shims |
| `aio.py:434` / `:440` | `AsyncClient.get_health` / `get_health_feed` |
| `aio.py:824` / `:829` | module shims |
| `aio.py:690` / `:713` | `AsyncClient.add_holidays` / `delete_holiday` |
| `aio.py:956` / `:961` | module shims |
| `_core.py:280` | `parse_health_response` → split into 2 |
| `_core.py:1083` | `parse_calendar_write_response` → split into 2 |

Plus `__init__.py:51-52,71-85,120-121` (imports, `__all__`) and the 8 class additions.
Plus docstring examples showing `health = client.get_health()` at `__init__.py:11,18,25`,
`client.py:8,14`, `aio.py:19` (cosmetic drift).

---

## Parser Split Plan

```
BEFORE (market-data _core.py)
  parse_health_response          (280)  ─┬─> get_health        (client 429 / aio 438)
                                         └─> get_health_feed   (client 435 / aio 444)
  parse_calendar_write_response  (1083) ─┬─> add_holidays      (client 702 / aio 711)
                                         └─> delete_holiday    (client 724 / aio 733)

AFTER
  @_decode._response_parser
  parse_health_response          -> Health              -> get_health
  @_decode._response_parser
  parse_health_feed_response     -> HealthFeed          -> get_health_feed
  @_decode._response_parser
  parse_add_holidays_response    -> AddHolidaysResult   -> add_holidays
  @_decode._response_parser
  parse_delete_holiday_response  -> DeleteHolidayResult -> delete_holiday
```

`_core.py:95-96` `__all__` entries must be updated (2 names → 4).

The decorator (`_decode.py:310`) is a `functools.wraps` wrapper around `_response_scope()`:

```python
def _response_parser[**P, R](fn: Callable[P, R]) -> Callable[P, R]:
    @functools.wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        with _response_scope():
            return fn(*args, **kwargs)
    return wrapper
```

Applied by prefixing the `def` line — no signature change, no import change (`_core.py:51` already
does `from market_data_client import _decode, _params`). Nesting is safe (`_holds` refcount).

**Note the private-name convention:** every existing call site writes `@_decode._response_parser`
with the leading underscore intact. Follow it verbatim; do not alias.

---

## Byte-Identical Request Test (criterion 2) — ground truth

### Provenance proof

`git diff market-data-client-v0.4.0 -- packages/market-data-client/src/market_data_client/` shows
the only changes since the published tag are Phase 29 decoder wiring:

- `_core.py`: `+from market_data_client import _decode` and **7** `@_decode._response_parser` lines. **No builder body changed.**
- `client.py` / `aio.py`: `strict_decode` kwarg + the two `_decode` bind lines at the top of `_request`. **No request-construction line changed.**
- `models.py`: filtered grep for `HolidayIn|HolidaysIn|drop_none|to_dict|open_time|close_time` returns **zero** changed lines.

**Therefore HEAD's emitted request bytes are identical to v0.4.0's, and the capture below is the
v0.4.0 pin.** [VERIFIED: git diff against tag `market-data-client-v0.4.0`]

### Captured tuple (executed this session against the real code path)

With `base_url = "https://market-data-develop.test/api"`, `token = "test-token"`,
`HolidaysIn([HolidayIn("2099-12-29", description="probe")])`, httpx 0.28.1:

**`add_holidays`**

```
method   : POST
url      : https://market-data-develop.test/api/calendar/holidays
headers  : [('accept', '*/*'),
            ('accept-encoding', 'gzip, deflate'),
            ('authorization', 'Bearer test-token'),
            ('connection', 'keep-alive'),
            ('content-length', '67'),
            ('content-type', 'application/json'),
            ('host', 'market-data-develop.test'),
            ('user-agent', 'python-httpx/0.28.1')]
content  : b'{"days":[{"day":"2099-12-29","closed":true,"description":"probe"}]}'
spec     : idempotent=True  endpoint_name='add_holidays'  authenticated=True
```

**`delete_holiday("2099-12-29")`**

```
method   : DELETE
url      : https://market-data-develop.test/api/calendar/holidays/2099-12-29
headers  : [('accept', '*/*'),
            ('accept-encoding', 'gzip, deflate'),
            ('authorization', 'Bearer test-token'),
            ('connection', 'keep-alive'),
            ('host', 'market-data-develop.test'),
            ('user-agent', 'python-httpx/0.28.1')]
content  : b''
spec     : idempotent=True  endpoint_name='delete_holiday'  authenticated=True
```

Note what this proves that a `json.loads` comparison would not: the body key order is
`day, closed, description` — `open_time`/`close_time` dropped by `_params.drop_none`, and
`description` **last** because `HolidayIn.to_dict()` lists it last. Reordering that dict literal
would be invisible to `json.loads`.

### Hazards for the pin

| Hazard | Why it matters | Mitigation |
|--------|----------------|------------|
| `user-agent: python-httpx/0.28.1` | Embeds `httpx.__version__`. pyprojects declare `httpx>=0.27`; `uv.lock` pins 0.28.1 and CI uses `--frozen`, so it is deterministic **today** — but a lock bump reddens the test for a reason unrelated to this phase. | Either derive it (`f"python-httpx/{httpx.__version__}"`) or exclude `user-agent` from the frozen set with an inline comment stating why. Do **not** silently drop it. |
| `request.extensions["request_id"]` | `uuid.uuid4().hex`, fresh per call (`client.py`, in `_request`). | Never include `req.extensions` in the frozen tuple. Assert `extensions["idempotent"]`, `["endpoint_name"]` and `["max_attempts"]` **separately** if desired — they are deterministic; `request_id` is not. |
| `content-length` | Present for POST, absent for DELETE. A shared helper that asserts a fixed header set across both would be wrong. | Freeze per-endpoint tuples, not a shared header list. |
| `Authorization: Bearer <token>` | Depends on the seeded token. The market-data `conftest.py` seeds `test-token` (as `test_calendar_write.py:262` already relies on). | Keep using the conftest-seeded token; assert the literal. |
| Gate must be open | Both methods call `_ensure_mutation_allowed()` first. `test_calendar_write.py` uses a local `_open_gate()` helper. | Reuse it. |

### Recommended shape

```python
_ADD_HOLIDAYS_V040 = (
    "POST",
    "https://market-data-develop.test/api/calendar/holidays",
    (("accept", "*/*"), ("accept-encoding", "gzip, deflate"),
     ("authorization", "Bearer test-token"), ("connection", "keep-alive"),
     ("content-length", "67"), ("content-type", "application/json"),
     ("host", "market-data-develop.test"),
     ("user-agent", f"python-httpx/{httpx.__version__}")),
    b'{"days":[{"day":"2099-12-29","closed":true,"description":"probe"}]}',
)

def _frozen(req: httpx.Request) -> tuple[str, str, tuple[tuple[str, str], ...], bytes]:
    return (req.method, str(req.url), tuple(sorted(req.headers.items())), req.content)
```

Then assert `_frozen(httpx_mock.get_requests()[0]) == _ADD_HOLIDAYS_V040` — a single equality over
raw bytes, **never** `json.loads`. Mirror in `test_calendar_write_async.py`.

httpx internals backing the determinism: `httpx._models.Headers.__init__` builds an ordered
`list[(raw_key, lower_key, value)]`; `Client._merge_headers` copies client defaults then `.update()`s
the per-request ones; `Request.__init__` → `_prepare` appends `host` and the body-derived
`content-length`/`content-type`. [VERIFIED: source read of installed httpx 0.28.1 + execution]

---

## Mutating-Gate Invariant (criterion 3)

`_ensure_mutation_allowed()` is defined at `client.py:265` and `aio.py:222`, and is the literal
first statement of exactly 8 methods per shell:

| Shell | Call-site lines |
|-------|-----------------|
| `client.py` | 574, 585, 600, 642, 656, 676, 699, 721 |
| `aio.py` | 582, 593, 608, 650, 664, 685, 708, 730 |

The 8 methods are `create_symbol`, `create_symbols`, `update_symbol`, `set_calendar_config`,
`delete_calendar_config`, `preview_calendar_config`, `add_holidays`, `delete_holiday`. All 16 sites
confirmed. [VERIFIED: grep]

Only `add_holidays` (`client.py:676` / `aio.py:685`) and `delete_holiday` (`client.py:699` /
`aio.py:708`) are touched by this phase, and only in their **last two statements** (spec build stays,
parser call changes). The gate line is untouched by construction.

**Builder flags today: both `idempotent=True`.** Criterion 3 means they must remain `True`.
(See G-6 — `client.py:684`'s docstring says otherwise and is stale.)

### Recommended Guard Placement

Build the AST guard **in-package**, at `packages/market-data-client/tests/`, not under
`verification/` (G-5). Minimal shape, adapting the pattern from
`verification/test_main_market_data_no_gate_bypass.py:72-90`:

```python
_GATE_CALL = "_ensure_mutation_allowed"
_MUTATION_METHODS = frozenset({
    "create_symbol", "create_symbols", "update_symbol",
    "set_calendar_config", "delete_calendar_config", "preview_calendar_config",
    "add_holidays", "delete_holiday",
})

def _first_stmt_is_gate(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    body = fn.body
    # skip the docstring
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        body = body[1:]
    return (
        bool(body)
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Call)
        and _called_name(body[0].value) == _GATE_CALL
    )
```

**Non-vacuity is mandatory** (Phase 15 WR-01/WR-02 precedent, restated in Phase 30's decision log):
assert the discovered method-name set **equals** `_MUTATION_METHODS` for each shell. A guard that
finds zero methods and reports green is the exact failure this repo has already been bitten by
twice.

---

## File Layout Census (criterion 4)

Actual `ls packages/*/src/*/` at HEAD:

| Module | iol | higyrus | market-data | matriz | ámbito | wallets |
|--------|-----|---------|-------------|--------|--------|---------|
| `__init__.py` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `client.py` / `aio.py` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `exceptions.py` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `_state.py` | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| `_logging.py` | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| `_core.py` | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| `_transport.py` / `_atransport.py` | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| `_decode.py` | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ (exempt) |
| **`models.py`** | ✓ | ✓ | ✓ | ✓ | **✗** | **✗** |
| **`types.py`** | **✗** | **✗** | **✗** | ✓ | **✗** | **✗** |

**7 new files exactly as D-09 states:** `types.py` × 5 (iol, higyrus, market-data, ámbito, wallets)
+ `models.py` × 2 (ámbito, wallets).

### Constraints on the near-empty modules

| Constraint | Which packages | Why |
|------------|----------------|-----|
| Must pass `mypy --strict` | ambito, wallets, higyrus, iol, matriz (in `pyproject.toml:97` `files`) | `__all__: list[str] = []` is explicitly annotated for this reason. market-data is exempt (D-13). |
| Must pass `ruff check` + `ruff format --check` | all 6 | `from __future__ import annotations` is applied uniformly across the monorepo (CLAUDE.md: "mandatory and applied uniformly"). A module with only a docstring + `__all__` still needs the header line to match convention. |
| Must NOT import `_decode` | wallets | It has no `_decode.py`; the import would `ImportError` and redden all 12 CI matrix legs for wallets. [VERIFIED: `check_decode_intactness.py` roster + directory listing] |
| Must NOT be re-exported into `__init__.__all__` | ambito | Would change `verification/snapshots/ambito-financiero-client-surface.txt`. Keep it out. |
| Must not break import-linter | ambito, iol, higyrus, matriz (`root_packages`) | Contracts are `forbidden: <pkg>._core → transport modules`. An import-free module is inert. |

### Existence-check wiring (D-12)

Mirror the `decode-intactness` step verbatim, in the same `lint` job:

```yaml
      - name: uniform-structure (Phase 31 TYP-03 — models.py + types.py en los 6 paquetes)
        # Cross-package por naturaleza: NO va al job `test`, que corre per-package.
        # Tampoco puede vivir bajo `verification/` — nunca corrió en CI.
        run: uv run python tools/check_uniform_structure.py
```

Suggested script contract (stdlib-only, no third-party imports): enumerate `packages/*/` dirs,
resolve `src/<import_name>/`, assert both `models.py` and `types.py` `is_file()`, exit 1 with a
per-package problem list. Model the error prose on `check_d_roster()`'s style
(`tools/check_decode_intactness.py:625-662`), which prints an indented problem list under a
one-line header and returns a success sentence on the happy path.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Tolerant field decode with divergence reporting | A per-model `__post_init__` or a custom coercion helper | `SafeModel.from_api` → `_decode.walk_model` | `_decode.py` is **byte-hash-pinned across 5 copies** by `tools/check_decode_intactness.py` in the `lint` job. Any new decode logic outside a model's declaration reddens CI. |
| Model → wire dict projection | A per-model `as_dict`/`asdict` call at each site | `SafeModel.to_dict()` copied verbatim from `iol_client/models.py:80-93` | Established Phase 30 precedent, already reviewed. It uses `dataclasses.asdict(cast(Any, self))` with a documented mypy-strict rationale (`SafeModel` itself is not a dataclass). |
| Decode-scope lifecycle in a parser | `with _decode._response_scope():` inline | `@_decode._response_parser` | The decorator is the sanctioned form at all 11 existing sites. Inline use bypasses the `functools.wraps` identity that keeps `__name__` stable for the `__all__` export. |
| Nullable-hour / nullable-timestamp handling | An `Optional` shim or a sentinel default | Declare `T \| None` | `_decode.walk_field`'s first branch returns `None` for a union-with-None **without emitting a divergence**. Correct modelling, not tolerance. |
| Holiday-day element model | A new `AddedHoliday`/`SavedDay` class | Reuse `CalendarDay` (`models.py:609`) | Live schema matches field-for-field. A parallel class would drift and would also add a second nested-field-type to police under `test_decode.py:1203/:1239`. |
| Sync/async parity for the new parsers | Duplicating parse logic in `aio.py` | One `_core.py` parser called by both shells | DT-04: codegen permanently shelved (two signed NO-GOs). Parity comes from a shared `_core`, asserted by introspection in Phase 32. |
| Cross-package structural gate | A pytest file under `verification/` | `tools/*.py` script + `lint` job step | `verification/` never executes in CI. Documented in `ci.yml`'s own inline comment and in STATE.md as a Phase 32 blocker. |
| Request-shape assertion | `json.loads(req.content) == {...}` | Raw-bytes tuple equality | `json.loads` is order-blind; `HolidayIn.to_dict()`'s key order is part of the v0.4.0 wire contract. |

**Key insight:** every "obvious" custom solution in this codebase is already forbidden by a
committed gate. Read the gate before writing the helper.

---

## Common Pitfalls

### Pitfall 1: Regenerating the higyrus surface snapshot is silently optional in CI

**What goes wrong:** `verification/snapshots/higyrus-client-surface.txt` goes stale; CI stays green
because `verification/` never runs; the next developer's local `uv run pytest` fails on an
unrelated branch.
**Why it happens:** the golden-file convention assumes the test that guards it runs. It does not.
**How to avoid:** make regen an explicit task with `uv run python verification/regen_snapshots.py`,
and verify locally with `uv run pytest verification/test_public_surface.py -q`.
**Warning sign:** `git status` shows a source change to `higyrus_client/models.py` or
`_core.py:426` with no companion diff in `verification/snapshots/`.

### Pitfall 2: Freezing `req.extensions` into the byte-identical tuple

**What goes wrong:** the test fails on every run with a different `request_id`.
**Why it happens:** `_request` sets four extensions; three are deterministic, `request_id` is a
fresh `uuid4().hex`.
**How to avoid:** the frozen tuple is `(method, url, sorted headers, content)` and nothing else.
**Warning sign:** a 32-hex-char string in a test failure diff.

### Pitfall 3: Treating criterion 3's "guard AST existente verde" as a fact

**What goes wrong:** the plan includes a "confirm the existing guard is green" task that has no
subject; criterion 3 then closes on nothing.
**Why it happens:** ROADMAP.md says *existente*. CONTEXT D-07 already caught this. **No such guard
exists** — verified against all 16 `ast.parse` users in the repo.
**How to avoid:** build it (§ Recommended Guard Placement), and make it non-vacuous by asserting
set equality against the 8 method names.

### Pitfall 4: Declaring a `from_api` override on a new market-data model

**What goes wrong:** `test_decode.py:1239` fails — it asserts `overriding == {"MarketDataSnapshot",
"Symbol"}` by equality.
**Why it happens:** overrides feel like the natural place for a shape carve-out (e.g. the 204
fallback). They are not: `_decode.walk_field`'s nested-model branch builds with
`hint(**walk_model(...))` and never calls `from_api`, so an override on a nested model is silently
skipped.
**How to avoid:** put shape carve-outs in the **parser**, never in a model override.

### Pitfall 5: Loosening `parse_get_health_response`'s raise-on-non-dict to make a test pass

**What goes wrong:** a real class of divergence stops being detected.
**Why it happens:** `Health.from_api(["unexpected","list"])` would tolerate a list where the wire
contract says object; the tempting fix is to drop the `isinstance` check.
**How to avoid:** Phase 30-03's ratified precedent is explicit — *"el desajuste de `get_instruments`
se corrigió del lado del test, nunca aflojando el guard del parser"*. Keep the guard; re-mock the
test. Two tests pin the exact `title`/`detail` strings (`test_async_client.py:198-206`).

### Pitfall 6: Feeding `to_dict()` into `schema_of`

See G-3. **Warning sign:** a live driver run reports zero SHAPE findings on an endpoint that
previously reported some.

### Pitfall 7: Missing the incidental `get_health` assertions

See G-7. **Warning sign:** `test_with_options.py` / `test_transport.py` failing in a phase whose
diff never mentions retries.

### Pitfall 8: Giving wallets a real `SafeModel`

**What goes wrong:** `ImportError: cannot import name '_decode'` at package import → all 12 wallets
CI matrix legs red.
**Why it happens:** wallets has none of `_state.py`/`_logging.py`/`_core.py`/`_decode.py` and is on
the original module-level singleton pattern (`29-WALLETS-EXEMPTION.md`).
**How to avoid:** docstring + `__all__: list[str] = []` + `from __future__ import annotations`.
Nothing else.

---

## Code Examples

### Splitting + decorating a health parser (market-data `_core.py`)

```python
# Source: pattern from market_data_client/_core.py:846 (parse_market_data_response)
#         guard shape from higyrus_client/_core.py:426 (parse_get_health_response)
@_decode._response_parser
def parse_health_response(resp: httpx.Response) -> Health:
    """Pure: parse ``GET /health`` → :class:`Health`."""
    resp.read()
    raise_for_response(resp)
    if not resp.content:
        return Health.from_api(None)      # 204 carve-out, Phase 7 CR-02 precedent
    raw = resp.json()
    if not isinstance(raw, dict):
        raise MarketDataAPIError(0, f"expected dict, got {type(raw).__name__}")
    return Health.from_api(raw)
```

Note `resp.read()` **before** `raise_for_response` — the body-consume-then-raise order is a Phase 7
D-06 invariant (HTTP/2 safety) present in every parser in this file.

### `to_dict()` to copy verbatim into higyrus + market-data `SafeModel`

```python
# Source: iol_client/models.py:80-93 (Phase 30 D-08)
def to_dict(self) -> dict[str, Any]:
    """Re-project the model as the plain wire dict (D-08)."""
    wire: dict[str, Any] = dataclasses.asdict(cast(Any, self))
    return wire
```

Requires `import dataclasses` and `from typing import cast` in the target `models.py`.

### Docstring-only module (wallets / ámbito)

```python
"""Placeholder por uniformidad de estructura (Phase 31, TYP-03).

`wallets-client` es todavía un stub sin endpoints verificables, así que no
declara modelos de respuesta. Este módulo existe para que los 6 paquetes
presenten el mismo layout y el próximo endpoint tenga dónde nacer.
Ver `.planning/phases/29-decoder-observable/29-WALLETS-EXEMPTION.md`.
"""

from __future__ import annotations

__all__: list[str] = []
```

For the `types.py` variants add a line stating why there is no `Literal` content yet, citing
`29-DLOCK-RESPONSE-LITERAL.md` and the Phase 33 deferral.

---

## Runtime State Inventory

This is a response-typing refactor on a **published wheel**, so the categories below are read as
"what carries the old contract outside this repo's source tree".

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | **None** — no datastore keys, collection names, or IDs are affected. The 5 endpoints are read/ops surfaces; `add_holidays`/`delete_holiday` write server-side calendar rows whose **request** shape is explicitly unchanged (criterion 2). | none |
| Live service config | **None in this phase.** The market-data develop service and its Auth0 tenant are unchanged; no client-side change alters what the server stores. Live re-verification against develop is Phase 33 (LIVE-TYP-01). | none |
| OS-registered state | **None** — verified: no task schedulers, pm2/launchd/systemd registrations exist for this repo. | none |
| Secrets / env vars | **None** — no env var name changes. Per-package `.env` files (`packages/higyrus-client/.env`, `packages/matriz-client/.env`) and market-data Auth0 creds are unaffected. | none |
| Build artifacts / published wheels | **`market-data-client` v0.4.0 is published** on GitHub Releases (tags `market-data-client-v0.1.0` … `-v0.4.0`) and **`higyrus-client` v0.1.1+**. Any external consumer reading `get_health()["status"]` or `add_holidays(...)["saved"]` breaks source-level. STATE.md already carries the analogous open question for iol: *"Se desconoce si algo fuera de este repo consume `iol-client` 0.2.0"*. | Version bump + README changelog is **Phase 34** (PUB-TYP-01), not here. But the planner should record the source-breaking nature of this change so Phase 34's bump decision (minor vs. major, per the v0.4.0 semver precedent recorded in STATE.md 28-01) has the input. |
| Golden files inside the repo | `verification/snapshots/higyrus-client-surface.txt` (stale after the change — G-1); `.planning/verification/schemas/*.json` (unchanged — they record the **wire**, which does not move). | Regenerate the surface snapshot; leave the schema JSONs alone. |

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Python (CPython) | everything | ✓ | 3.12.11 (venv active) | 3.13 also in CI matrix |
| uv | workspace sync, all runners | ✓ | 0.9.0 (per CLAUDE.md); `uv run` works | — |
| httpx | request construction, byte-identical pin | ✓ | **0.28.1** (locked in `uv.lock`) | none — the pin's `user-agent` literal depends on it |
| pytest / pytest-asyncio / pytest-httpx | all tests | ✓ | pytest-httpx 0.36.2 per `uv.lock` | — |
| ruff | `lint` job | ✓ | ≥0.7 (pre-commit pinned v0.15.12) | — |
| mypy | `typecheck` job | ✓ | ≥1.13, `strict = true` | — |
| Live market-data develop API + Auth0 creds | **NOT needed this phase** | n/a | — | All 5 shapes are already captured under `.planning/verification/schemas/`. Live re-verification is Phase 33. |
| Network / package registry | **NOT needed** | n/a | — | Zero new dependencies. |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none.

**Baseline measured this session:** `uv run pytest packages/market-data-client packages/higyrus-client -q`
→ **699 passed in 36.02s**. Use this as the pre-change reference count.
[VERIFIED: command execution]

---

## Package Legitimacy Audit

**Not applicable — this phase installs zero external packages.**

All new code is stdlib-only (`dataclasses`, `typing`, `ast`, `pathlib`, `sys`) plus modules already
present in the workspace (`httpx`, `pytest`). D-12 explicitly requires the new existence-check
script be "stdlib-only". `uv.lock` must **not** change; `uv lock --check` runs as the first step of
the `lint` job and will fail if it does.

| Package | Registry | Verdict | Disposition |
|---------|----------|---------|-------------|
| *(none)* | — | — | No package installs in this phase |

**Packages removed due to [SLOP] verdict:** none.
**Packages flagged as suspicious [SUS]:** none.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.3+ with pytest-asyncio (`asyncio_mode = "auto"`), pytest-httpx 0.36.2 |
| Config file | root `pyproject.toml` `[tool.pytest.ini_options]` (`testpaths = ["packages", "tests", "verification"]`, `--import-mode=importlib`, `--strict-markers`) |
| Quick run command | `uv run pytest packages/market-data-client -q` (≈25s) |
| Full suite command | `uv run pytest packages/market-data-client packages/higyrus-client -q` (**699 passed / 36s** measured) |
| CI-equivalent | `uv run pytest packages/<pkg>` per matrix leg — **note this excludes `verification/`** |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| TYP-02 | `higyrus.get_health` returns `Health` (sync + async, method + shim) | unit | `uv run pytest packages/higyrus-client/tests/test_core.py packages/higyrus-client/tests/test_client.py packages/higyrus-client/tests/test_async_client.py -q` | ✅ (re-mock existing) |
| TYP-02 | higyrus 204 → zero-valued `Health`, non-dict → `HigyrusAPIError(status_code=0, "shape mismatch")` | unit | `uv run pytest packages/higyrus-client/tests/test_core.py -k health -q` | ✅ `test_core.py:406-425` (re-assert) |
| TYP-02 | `market-data.get_health` / `get_health_feed` return `Health` / `HealthFeed`, 3-level nesting populated | unit | `uv run pytest packages/market-data-client/tests/test_core.py -k health -q` | ✅ (re-mock) |
| TYP-02 | market-data health parsers gain a non-dict guard | unit | `uv run pytest packages/market-data-client/tests/test_core.py -k health -q` | ❌ **Wave 0** — no guard exists today |
| TYP-02 | `add_holidays` returns `AddHolidaysResult` with `days: list[CalendarDay]` populated from the live shape | unit | `uv run pytest packages/market-data-client/tests/test_calendar_write.py packages/market-data-client/tests/test_calendar_write_async.py -q` | ✅ (re-mock: `{"created":1}` → `{days,note,saved}`) |
| TYP-02 | `delete_holiday` returns `DeleteHolidayResult` (`deleted: bool`, not int) | unit | same as above | ✅ (re-mock: `{"deleted":1}` → `{"day":"…","deleted":true}`) |
| TYP-02 | **Byte-identical request** for both mutations, sync + async | unit | `uv run pytest packages/market-data-client/tests/test_calendar_write.py -k byte_identical -q` | ❌ **Wave 0** — new file/tests, § Byte-Identical Request Test |
| TYP-02 | Mutating-gate: `_ensure_mutation_allowed()` first literal statement × 8 methods × 2 shells | unit (AST) | `uv run pytest packages/market-data-client/tests/test_mutation_gate.py -q` | ❌ **Wave 0** — guard does not exist (D-07) |
| TYP-02 | Neither holiday builder changes `idempotent=` | unit | `uv run pytest packages/market-data-client/tests/test_core.py -k idempotent -q` | ⚠️ partial — `test_transport.py` pins the transport short-circuit; add a direct builder-flag assertion |
| TYP-02 | Zero `dict[str, Any]` across the 20 signature sites | unit / typecheck | `uv run mypy packages/higyrus-client/src` (CI-covered) + `uv run mypy packages/market-data-client/src` (local only, D-13) | ⚠️ market-data not CI-enrolled |
| TYP-02 | higyrus public surface reflects the new signature | golden | `uv run pytest verification/test_public_surface.py -q` (**local only**) | ✅ exists, snapshot needs regen (G-1) |
| TYP-03 | All 6 packages have `models.py` + `types.py` | script | `uv run python tools/check_uniform_structure.py` | ❌ **Wave 0** — new script + `ci.yml` step |
| TYP-03 | New near-empty modules pass strict typecheck + lint | typecheck/lint | `uv run mypy` + `uv run ruff check .` + `uv run ruff format --check .` | ✅ existing CI jobs |
| TYP-03 | `check_decode_intactness.py` stays green (wallets still exempt) | script | `uv run python tools/check_decode_intactness.py` | ✅ exists |

### Sampling Rate

- **Per task commit:** `uv run pytest packages/<touched-package> -q` + `uv run ruff check .`
- **Per wave merge:** `uv run pytest packages/market-data-client packages/higyrus-client -q` (baseline **699**, expect ≥699 after) + `uv run python tools/check_decode_intactness.py` + `uv run python tools/check_uniform_structure.py`
- **Phase gate:** full local suite **including `verification/`** — `uv run pytest -q` — because CI does not run `verification/` and G-1 lives there. Then `uv run mypy` and `uv run mypy packages/market-data-client/src` (the latter is the D-13 local-only acceptance step).

### Wave 0 Gaps

- [ ] Byte-identical request tests (sync + async) — covers TYP-02 criterion 2. New; use the captured tuple.
- [ ] Mutating-gate AST guard, in-package, non-vacuous — covers TYP-02 criterion 3. New (D-07).
- [ ] `tools/check_uniform_structure.py` + `ci.yml` `lint` step — covers TYP-03 criterion 4. New (D-12).
- [ ] Direct builder-flag assertion (`idempotent is True` for both holiday builders) — criterion 3's second clause.
- [ ] Non-dict guard tests for the two market-data health parsers (D-04's "ganan un guard equivalente").
- [ ] Framework install: **none needed** — pytest, pytest-asyncio, pytest-httpx all present.

---

## Security Domain

`workflow.security_enforcement = true`, `security_asvs_level = 1`. This is a client library with no
server surface; most ASVS categories are structurally inapplicable.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | no (unchanged) | Auth0 client-credentials in `_state`/`_core`; this phase touches no auth path. `get_health`/`get_health_feed` are `authenticated=False` by design (T-20-02: anonymous specs must not carry a stale Bearer) and stay that way. |
| V3 Session Management | no | No sessions. Token TTL logic untouched. |
| V4 Access Control | **yes** | `_ensure_mutation_allowed()` refuse-by-default + exact-hostname match. **Criterion 3 IS this control's regression gate.** Never relax it to make a response test pass. |
| V5 Input Validation | **yes** | Two existing input guards on the touched surface must remain intact: `HolidaysIn.__post_init__`'s 1-500 batch bound and `build_delete_holiday_request`'s `_DAY_SEGMENT_RE` path-safety allow-list (blocks `../config` segment retargeting and the RFC-3986 lone-`.` collapse to the collection endpoint). Both live in the **request** path — untouched by a response-only change, and the byte-identical test is the proof. |
| V6 Cryptography | no | None hand-rolled; TLS via httpx. |
| V7 Error Handling & Logging | **yes** | `T-29-36`: exception attributes carry "tipos y rutas, jamás un valor del wire". New parsers raising on shape mismatch must follow `higyrus_client/_core.py:433`'s form — `f"expected dict, got {type(raw).__name__}"`, the **type name**, never `repr(raw)`. `RedactingFilter` is attached per package. |
| V8 Data Protection | **yes** | `verification/schema.py::schema_of` emits keys and type names only, never values — which is what makes snapshot writing PII-free by construction. Any G-3 change to the driver snapshot path must preserve that: feed `schema_of`, never `append_finding`. |
| V13 API | partial | The response-only guarantee is itself the API-stability control for the two published mutations. |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Accidental mutation of a production calendar | Tampering | `_ensure_mutation_allowed()` first-statement invariant + exact `expected_host` match. Criterion 3's AST guard. |
| Path-segment retargeting via `day` | Tampering / EoP | `_DAY_SEGMENT_RE` allow-list + all-dots rejection in `build_delete_holiday_request` (D-18/T-26-01). Unchanged this phase; byte-identical test pins it. |
| Silent wire drift masked by tolerant decode | Repudiation | Phase 29 divergence records; **G-3** is the live instance of this threat inside this phase. |
| Credential leak through error reporting / findings | Info Disclosure | `RedactingFilter` + T-29-36 type-only exception attributes + `schema_of` value-blindness. |
| Retry amplification on a non-idempotent write | DoS / Tampering | `request.extensions["idempotent"]` gating in `RetryTransport`. Both holiday builders are `idempotent=True`, ratified on live row-count measurement (D-20). Criterion 3 forbids changing either flag. |
| Log injection via a hostile wire key | Tampering | `_decode._safe_key` (`_KEY_SAFE_RE` + `_MAX_KEY_LEN = 64`, lock 11). Inherited free by the new models. |

**No new attack surface is introduced by this phase.** The response type changes from `dict` to a
frozen dataclass, which strictly reduces what a caller can do with an unexpected payload.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `_coerce(value, hint)` per-field shim | `_decode.walk_model` / `walk_field` walker with a divergence sink | Phase 29 (DEC-01) | `_coerce` survives only as a back-compat shim in each `models.py`. New models never call it. |
| Silent typed-zero substitution | Structured divergence record on the package logger + optional strict raise | Phase 29 | The whole point of v1.6. Getting a nullability declaration wrong now surfaces as a Phase 33 finding rather than a silent `""`. |
| `dict[str, Any]` returns for un-modelled endpoints | Typed frozen dataclasses | Phases 30-31 | This phase closes the last 5. |
| `add_holidays` builder `idempotent=False` | `idempotent=True` | Phase 27 (D-20, live row-count measurement) | Criterion 3's "no builder changes its flag" means **stay True**. `client.py:684`'s docstring still says `False` — stale (G-6). |
| msgspec as a second decode engine | **stdlib-only, one engine** | Phase 29 Plan 04, signed NO-GO 2026-08-19 | The 6 wheels stay a 100%-pure-Python closure. No new dependency is admissible in this phase. |
| Codegen for sync/async parity (REFAC-06) | Shared `_core.py` + introspection-asserted parity | Phases 12/18, two signed NO-GOs | Never generate `aio.py`; mirror by hand through a shared parser. |
| `Literal` on RESPONSE fields | `str`, out-of-set values reported not enforced | Phase 29 D-lock, signed 2026-08-18 | Why the 5 new `types.py` are docstring placeholders (D-09). |

**Deprecated / outdated in the docs, not the code:**

- `29-WALLETS-EXEMPTION.md`'s module table — says iol has no `models.py` (Phase 30 added one) and will additionally go stale on ambito/wallets after this phase.
- `client.py:684` `add_holidays` docstring — `idempotent=False` claim (G-6).
- `higyrus_client/models.py` module docstring — cites a `[tool.ruff.lint.per-file-ignores]` N815 exemption for itself that does not exist in `pyproject.toml` (only market-data's `models.py` has one). Harmless: `N` (pep8-naming) is not in the ruff `select` list at all. Also irrelevant to this phase — all 8 new market-data models use snake_case wire keys.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| **A1** | `FeedIngestor.last_error` and `FeedPipeline.last_write_error` are `str \| None` (the non-null type is `str`) | Exact Model Shapes | Low. Live capture shows only `null`. If the real type is a structured object, the walker reports a `wrong_type` divergence in Phase 33 — the designed outcome, not a break. Inherited from CONTEXT D-01. |
| **A2** | The other 7 health-feed string fields (`last_frame_at`, `started_at`, `last_write_at`, `next_transition`, `session_open`, `session_close`, `last_business_day`) are non-nullable `str` | Exact Model Shapes | **Medium.** The single capture is of a **connected, healthy** feed. If the vendor sends `null` when the ingestor is disconnected or the market is disabled, strict mode **raises** in Phase 33's driver run. See Open Question 1. |
| **A3** | `HealthFeed.newest_received_at` / `oldest_received_at` are non-nullable `str` | Exact Model Shapes | **Medium.** Same single-state-capture problem; plausibly `null` when `symbols_with_data == 0`. |
| **A4** | The `{}` fallbacks in `parse_calendar_write_response` should become `Model.from_api(None)` rather than a raise | G-4 | Medium — this is a behavior decision on a published mutation. Recommendation only; needs a planning decision. |
| **A5** | `verification/regen_snapshots.py` is the correct and sufficient tool to accept the higyrus surface change | G-1 | Low — the snapshot header names it explicitly and Phase 30 used it for iol. |
| **A6** | The 8 new market-data models will be re-exported from `__init__.py` (following the existing 13) | G-2 | Low — consistent with every prior phase; if not, G-2 is moot. |
| **A7** | Adding `@_decode._response_parser` to the health parsers has no observable effect on any existing test | G-8 | Low — reasoned through all 4 `get_health`-using decode tests plus all `.closed` assertions; none depend on the retired-vs-open distinction. Cheap to falsify: run `uv run pytest packages/market-data-client/tests/test_decode.py -q` after the decoration. |

**No `[ASSUMED]` claim in this document concerns a package name, a version, a compliance
requirement, or a security standard.** Everything else is `[VERIFIED]` by file read, grep, code
execution, or git diff in this session.

---

## Open Questions

1. **Nullability of the health-feed timestamp / reason fields (A2, A3).**
   - *What we know:* the live capture (`get-health-feed.json`, 2026-07-31) shows a connected
     ingestor with an open market: every timestamp is a `str`, both error fields are `null`. The
     capture is a **single state**.
   - *What's unclear:* whether the vendor sends `null` for `last_frame_at` / `started_at` /
     `last_write_at` before the first frame, or for `next_transition` / `session_open` /
     `session_close` / `last_business_day` / `reason` when `enabled` or `is_open` is `false`.
     `FeedMarket` in the capture has `enabled: true` and a populated `reason`, which suggests
     `reason` is always a string — but that is inference, not evidence.
   - *Recommendation:* declare the two **known-null** fields `str | None` (D-01) and the **five
     market-session** fields (`next_transition`, `session_open`, `session_close`,
     `last_business_day`, `reason`) `str | None` as well, on the reasoning that a closed/disabled
     market has no session times. Declare `last_frame_at`/`started_at`/`last_write_at` as `str` per
     the capture and let Phase 33 correct them. Record the choice in the model docstrings, following
     `CalendarDay`'s precedent of explaining each `str | None` inline. **Note:** `T | None` costs
     nothing in observability — `walk_field`'s union branch returns `None` **without** emitting a
     divergence, so an over-declared `Optional` hides a genuine `null`. That is the real tradeoff,
     and it argues for restraint. Worth a one-line operator confirmation at planning time.

2. **G-3: which of the three schema-snapshot options?**
   - *What we know:* Phase 30 hit this exact fork and chose the raw-wire capture (`_capture_raw_wire`)
     for iol's four modelled endpoints, plus an FA-09 carry-forward note.
   - *What's unclear:* whether the two market-data health probes and higyrus probe 15 warrant the
     same investment, given health payloads are small and this phase's model set is small.
   - *Recommendation:* mirror Phase 30 (option a) for market-data — `main_market_data.py` already
     has `_mutate_raw_sync` and does raw-refire for `add_holidays`, so the machinery exists. For
     higyrus, option (b) — document the FA-09-style carry-forward — is defensible given `Health` has
     a single field and its drift surface is trivially small.

3. **G-6: fix the stale `add_holidays` docstring in-phase, or defer?**
   - *Recommendation:* fix in-phase. It is a comment-only edit inside a method this phase already
     touches, and leaving it is an active trap for criterion 3.

4. **D-10: update `29-WALLETS-EXEMPTION.md` prose?**
   - *What we know:* the doc's module table is **already** stale (iol gained `models.py` in Phase 30)
     independent of anything this phase does. Nothing turns red either way.
   - *Recommendation:* a two-line amendment note at the bottom of the doc — cheaper than a Phase 32
     rewrite and it stops the table misleading the next reader. Operator's call per CONTEXT.

---

## Sources

### Primary (HIGH confidence) — this session, tool-verified

- `.planning/verification/schemas/market-data-client/{get-health,get-health-feed,add-holidays-sync-response,add-holidays-async-response,delete-holiday-sync-response,delete-holiday-async-response}.json` — all 5 response shapes, dumped verbatim
- `.planning/verification/schemas/higyrus-client/get-health.json`
- `packages/market-data-client/src/market_data_client/{_core.py,client.py,aio.py,models.py,_decode.py,__init__.py}` — parsers, builders, shells, models, decoder, surface
- `packages/higyrus-client/src/higyrus_client/{_core.py,client.py,aio.py,models.py,__init__.py}`
- `packages/iol-client/src/iol_client/models.py` — `to_dict()` template
- `packages/market-data-client/tests/{test_calendar_write.py,test_calendar_write_async.py,test_decode.py,test_mutation_gate.py,test_public_surface_market_data.py,test_transport.py,test_with_options.py,test_with_options_async.py}`
- `packages/higyrus-client/tests/{test_core.py,test_async_client.py}`
- `tools/check_decode_intactness.py` — Check D roster (lines 615-662)
- `.github/workflows/ci.yml` — `lint` / `typecheck` / `test` jobs
- `pyproject.toml` — mypy `files` (:97), importlinter `root_packages` (:141-146), pytest, ruff
- `verification/{test_public_surface.py,regen_snapshots.py,test_main_market_data_no_gate_bypass.py,snapshots/*.txt}`
- `main_market_data.py`, `main_higyrus.py`, `main_iol.py` (`_as_wire`, `_capture_raw_wire`)
- `git diff market-data-client-v0.4.0 -- packages/market-data-client/src/` — provenance proof for the byte-identical pin
- **Executed:** the real `build_add_holidays_request` / `build_delete_holiday_request` +
  `httpx.Client.build_request` path, capturing both frozen tuples
- **Executed:** `uv run pytest packages/market-data-client packages/higyrus-client -q` → 699 passed
- **Executed:** source read of installed httpx 0.28.1 (`_models.Headers.__init__`,
  `_client.Client._merge_headers`, `_models.Request.__init__`)

### Secondary (MEDIUM confidence)

- httpx 0.28.1 header determinism digest, cached via `gsd-tools query research-store put` under key
  `a2992c9e…bd930`; provider `context7`, tier MEDIUM per `classify-confidence --provider context7 --verified`.
  Corroborated by direct source read + execution, which is why the derived claims above are tagged
  `[VERIFIED]` rather than `[CITED]`.

### Project artifacts consulted

- `.planning/phases/31-endpoints-de-ops-estructura-uniforme/31-CONTEXT.md` (D-01..D-13)
- `.planning/ROADMAP.md` § Phase 31 / § Phase 32
- `.planning/REQUIREMENTS.md` (TYP-02, TYP-03)
- `.planning/STATE.md` (Phase 29/30 ratified decisions, Phase 31/32 risk entries)
- `.planning/phases/29-decoder-observable/29-WALLETS-EXEMPTION.md`
- `./CLAUDE.md` (stack, conventions, architecture, anti-patterns)

---

## Project Constraints (from CLAUDE.md)

Directives the planner must honour. Each is treated with the same authority as a CONTEXT lock.

| # | Directive | Bearing on this phase |
|---|-----------|-----------------------|
| C-1 | **Stack:** Python 3.12+, uv, httpx, pytest+pytest-httpx, ruff, mypy strict — every extension and fix must respect the stack and pass existing CI | No new dependency; `uv.lock` must not change (`uv lock --check` is the first `lint` step). |
| C-2 | **Architecture:** module-level singleton state; **no shared code between packages (by design)** — fixes apply inside each package without cross-package imports | higyrus's `Health` and market-data's `Health` are **two independent classes**. `to_dict()` is **copied verbatim** into each `SafeModel`, never imported from iol. |
| C-3 | **Dual sync/async:** any logic fix must be mirrored in `client.py` and `aio.py` of the same package | All 4 endpoint changes land on both shells. The mirroring happens through the shared `_core.py` parser; the shells' signatures still change independently. |
| C-4 | **Security:** credentials live in per-package `.env`; never commit `.env` or expose credentials in logs, reports, or tests | The byte-identical test uses the conftest-seeded `test-token`, never a real credential. |
| C-5 | **`from __future__ import annotations` is mandatory and applied uniformly** | Required in all 7 new module files, including the docstring-only ones. |
| C-6 | Ruff: line-length 100, double quotes, 4-space indent; rule sets E,W,F,I,B,UP,SIM,RUF,ASYNC,PIE,PT,RET,TID; **no relative imports** (TID), **no wildcard imports** | New models import as `from market_data_client import _decode`, never relatively. |
| C-7 | Models are `@dataclass(frozen=True, slots=True)` inheriting `SafeModel`, constructed **exclusively** via `Model.from_api(payload)` — never `Model(field=value)` | All 9 new models. Note the `slots=True` + zero-arg `super()` trap documented at `models.py:600-606` (Symbol) — only relevant if a model overrides `from_api`, which none of these may (Pitfall 4). |
| C-8 | Explicit `__all__` in `__init__.py`; `aio` importable but not flat-namespace re-exported | New model names go in `__all__`; async shims stay on `market_data_client.aio`. |
| C-9 | Public functions get a one-line summary + the endpoint path in backtick-rst | Preserve on all 20 touched signatures. |
| C-10 | Module docstrings describe purpose, usage examples, env vars, auth flow | The 7 new files need a real docstring, and the 6 stale usage examples showing `health = client.get_health()` should be reviewed. |
| C-11 | **GSD workflow enforcement:** no direct repo edits outside a GSD workflow | This research made **zero** repo edits. Implementation happens under `/gsd-execute-phase`. |
| C-12 | Wire field names are **camelCase verbatim** where the API is camelCase; Python parameters are snake_case | The market-data ops API is **snake_case on the wire** (`active_symbols`, `last_write_error`) — so the new models' field names are snake_case, matching `CalendarDay`/`CalendarConfig`. No N815 exemption needed. |

---

## Metadata

**Confidence breakdown:**

- Standard stack: **HIGH** — no new stack. Every tool version confirmed by execution (`httpx 0.28.1`, CPython 3.12.11, pytest-httpx 0.36.2 from `uv.lock`).
- Model shapes: **HIGH** — all 5 derived from committed live captures, dumped verbatim; `CalendarDay` reuse confirmed field-for-field. Nullability of 9 fields is the one soft spot (A1-A3).
- Architecture / wiring: **HIGH** — every file:line in CONTEXT D-01..D-13 re-verified against the working tree.
- Byte-identical request pin: **HIGH** — captured by executing the real code path, with a `git diff` provenance proof against the published tag.
- Guard placement + CI wiring: **HIGH** — `ci.yml`'s own inline comment and STATE.md's Phase 32 blocker both state the `verification/`-never-runs-in-CI fact.
- Pitfalls / gaps: **HIGH** for G-1..G-7 (each traced to a specific file:line or a ratified prior decision); **MEDIUM** for G-8 (reasoned from source, not executed).

**Research date:** 2026-08-23
**Valid until:** 2026-09-22 (30 days). Codebase-internal findings invalidate only on a source change
to the cited files — re-verify the line numbers if Phase 30's tail plans (30-13 and later) land
before this phase executes.
