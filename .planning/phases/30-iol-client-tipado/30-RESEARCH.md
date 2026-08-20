# Phase 30: `iol-client` tipado - Research

**Researched:** 2026-08-19
**Domain:** Python typed response models over a verbatim-copied decode walker (stdlib dataclasses, mypy strict)
**Confidence:** HIGH — every load-bearing claim was re-verified in this session against the working tree; the four highest-risk mechanics were validated by execution, not by reading.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Diseño de modelos
- **D-01:** 4 dataclasses `frozen=True, slots=True` sobre 2 formas de wire — `Cotizacion` (compartida por `get_quote` y cada fila de `get_historical_quotes`: mismas 20 claves camelCase), `Punta` anidado, `Instrumento` (2 claves) y `Titulo` (filas de `titulos`, 21 claves) — con base `SafeModel` copiada del template **mínimo de higyrus** (`higyrus_client/models.py:41-54`, 14 líneas: `from_api` delegando a `_decode.walk_model`, sin `empty()`, sin mapping-axis, sin `received_at`). Ni el SafeModel de market-data (mapping-axis + overrides sin campo que los justifique) ni el de matriz (política missing→`None`, opuesta al `_decode.POLICY` typed-zeros de iol).
- **D-02:** `puntas` se declara **`list[Punta] | None` en `Cotizacion`** y **`Punta` singular en `Titulo`** — `Punta` = 4 campos `float` (`cantidadCompra`/`cantidadVenta`/`precioCompra`/`precioVenta`), única forma de elemento observada en todo el corpus. El elemento de la lista de `get_quote` es **inobservado** (la captura 2026-06-06 registró `[]`) — la confirmación es trabajo de la corrida estricta de F33 (postura evidencia-primero de DT-07). NO usar `list[dict[str, Any]]` pass-through (esquiva el gate de F32 por tecnicismo).
- **D-03:** Todo campo que el corpus registra como `NoneType` se declara **`T | None`**: `descripcionTitulo`/`plazo`/`puntas` en la forma histórica; `fechaVencimiento`/`precioEjercicio`/`tipoOpcion` en `Titulo`. Razón: el walker de F29 trata Optional como opt-in explícito sin divergencia (`_decode.py:436-442`); no-Optional pre-carga el censo de F33 con ~6 divergencias garantizadas que no son defectos (misma clase que S-5 de F29).
- **D-04:** `cantidadOperaciones` respeta el corpus por-modelo: `int` en `Cotizacion` (quote/histórico), `float` en `Titulo` — dos declaraciones distintas, no una unificada que reportaría divergencia en cada llamada.

#### Wiring en `_core` + decoder F29
- **D-05:** Los 4 parsers de `_core.py:327-360` se reescriben **in place** para retornar modelos, cada uno decorado con `@_decode._response_parser` (dueño del `DecodeScope` per-response: dedupe colapsa un `list[Model]` a 1 registro por campo), espejando el patrón higyrus `_core.py:457-500`. `_core` → `models` → `_decode` no viola ningún contrato de import-linter; no se necesita contrato nuevo.
- **D-06:** `parse_get_instruments_by_type_response` conserva el unwrap del envelope (`data.get("titulos", [])`) como paso raw-dict ANTES de construir modelos — el envelope `titulos` no se modela. `parse_get_instruments_response` gana guard `isinstance(raw, list)` (hoy retorna `Any` pass-through; el wire real es una lista top-level `[{instrumento, pais}]`). Los **~12 tests que mockean `get_instruments` como dict `{"instrumentos": …}`** (forma que el schema vivo contradice) se **re-mockean mecánicamente** como lista — lo usan solo como llamada autenticada barata; el payload es incidental. NO adoptar leniency dict-o-lista (reintroduce el bug del `[]` silencioso).

#### Migración del driver + harness
- **D-07:** Los "2 sitios reales" de acceso por atributo son `main_iol.py:316` y `:395` (`quote.get("ultimoPrecio")` → `quote.ultimoPrecio`). Además hay **≥5 sitios estructurales** que consumen vía `verification.schema.schema_of` y deben recibir `to_dict()` (`:918-919` parity probe, `:1066`, `:1102`, `:1164` `_write_or_check_schema`): sin eso la próxima corrida viva escribe `"schema": "Cotizacion"` en los baselines committeados y F33 arranca corrupto. Esta es la razón operativa del criterio 5.
- **D-08:** `to_dict()` = **`dataclasses.asdict(self)`** (recursivo: `Punta` anidado se aplana a dict plano), anotado `-> dict[str, Any]`. Primer `to_dict()` sobre un modelo de *response* en el monorepo (los de market-data son request models); F32 ya lo nombra en su lista de exenciones. Round-trip lossy conocido y aceptado: `null` de wire decodificado a Optional-default y claves no declaradas desaparecen del snapshot — blind spot documentado, contrastable en F33.

#### Gates, prueba RED, release
- **D-09:** El gate de intactness de F29 **no se toca** (`tools/check_decode_intactness.py` hashea solo `_decode.py`; iol ya enrolado; `models.py` nuevo no afecta el digest). Sí se **regenera `verification/snapshots/iol-client-surface.txt`** (`verification/regen_snapshots.py`) — pinnea firmas con retornos y quedaría rojo invisible en CI (verification/ no corre en CI). Ruff no necesita exención camelCase (`N` no está en `select`).
- **D-10:** La fixture RED de typecheck vive en **`packages/iol-client/tests/`** (path typechequeado por el loop mypy de `ci.yml:85-94`) como typo de atributo deliberado con `# type: ignore[attr-defined]` bajo `warn_unused_ignores = true` — no-vacua en ambas direcciones (atributo existente → ignore unused → mypy error; typo cazado → ignore lo absorbe). NUNCA en `main_iol.py` (mypy no lo typechequea: `files` = `packages/*/src`). Sin subprocess-mypy (maquinaria nueva, ~10s de CI).
- **D-11:** Phase 30 **no bumpea `__version__`** (queda `"0.2.0"`); escribe la sección de changelog `### v0.3.0` en `packages/iol-client/README.md` (precedente: `market-data-client/README.md:123-193`) registrando la ruptura dict→modelo incluido el flip de truthiness; F34 ejecuta el bump (evita desincronizar el tag pipeline y un tag 0.3.0 antes de la verificación viva de F33).
- **D-12:** El README de iol hoy documenta una API que **no existe** (`IOLClient(token=...)`, `get_portfolio()` — cero apariciones en `src/`). El callout de ruptura es ilegible contra una descripción ficticia → **se corrige la sección de Uso en el mismo commit** del changelog (scope aceptado, no expansión).

### Claude's Discretion
- Nombres exactos de las clases (`Cotizacion`/`Punta`/`Instrumento`/`Titulo` son los sugeridos), orden de campos, y si `Cotizacion` histórica amerita docstring aclarando la nulabilidad diferencial — dentro de D-01/D-03.
- Forma exacta de la fixture RED (nombre del test/archivo) dentro de D-10.
- Detalle de los re-mocks de D-06 (payload mínimo por sitio).

### Deferred Ideas (OUT OF SCOPE)
- Confirmación del elemento de `puntas` en `get_quote` (lista capturada vacía) — corrida estricta F33 con creds (D-02)
- Promoción `mercado`/`plazo` → `Literal` con censo vivo — F33 (DT-07)
- Bump `__version__` 0.2.0→0.3.0 + tag + release — F34 (PUB-TYP-01, D-11)
- Bootstrap de `types.py` en iol (estructura uniforme ×6) — F31 (TYP-03)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TYP-01 | El consumidor de `iol-client` accede a cotizaciones, series históricas e instrumentos por **atributo tipado** (models.py nuevo con shapes derivados de los schemas capturados en vivo, `puntas` polimórfico resuelto); 16 firmas migradas (4 funciones × método/shim × sync/async) + parsers de `_core.py`; `main_iol.py` migrado a acceso por atributo (2 sitios reales). `mercado`/`plazo` quedan `str` en F30; promoción a `Literal` diferida a F33 con censo vivo (DT-07). | § Model Field Tables (exact 4 shapes derived from the 4 live schemas, each round-trip-verified); § The 16 Signatures (exact file:line inventory with current and target types); § Parser Rewrite Contract (the iol-specific adaptation of the higyrus pattern, with the `IOLAPIError` signature difference called out); § RED Fixture Mechanics (empirically validated in both directions); § Blast Radius (exact file:line lists for the 18 mock lines + 23 assert lines); § Pitfalls 1-9. |
</phase_requirements>

## Summary

This is not a research-heavy phase in the usual sense — no library selection, no new dependencies, no external unknowns. The stack is frozen (Python 3.12 stdlib dataclasses over the Phase 29 walker), the wire shapes are already captured on disk, and CONTEXT.md arrives with twelve decisions that are, on inspection, all correct. The research value therefore lies almost entirely in **verifying the mechanics** that the plan will encode, and in the **exact inventories** the planner needs to write tasks against.

Everything load-bearing was re-verified against the working tree, and the four riskiest mechanics were validated by **execution rather than reading**: (1) the walker builds all four model shapes from the captured schemas with **zero divergences**; (2) `to_dict()` = `dataclasses.asdict` round-trips through `verification.schema.schema_of` to a result **byte-identical to all three affected committed baselines**; (3) the D-10 RED fixture is non-vacuous in both directions exactly as specified; (4) `puntas` polymorphism resolves correctly across all three observed wire forms. All four are reported below as `[VERIFIED: measured in-session]`.

That verification also surfaced **five corrections and one genuine trap** that the plan must absorb. The trap is the most important finding in this document: the naive form of the D-10 RED fixture **turns CI red at pytest runtime** with an `AttributeError`, because `packages/iol-client` is in the CI test matrix and the deliberate typo actually executes. The corrections are smaller but sharpen the plan: D-07's stated failure mode is impossible (the D-25 no-overwrite guard makes baseline corruption unreachable) and the real failure mode is **worse** — three of the four `schema_of` sites degrade to a **vacuous green**, silently losing all their test power rather than emitting a loud finding. D-06's mock count is an undercount (16 payload sites, not ~12). And Phase 29 left Phase 30 an **explicit named obligation** that CONTEXT.md does not mention: re-ratifying iol's `DecodePolicy` constant now that models exist.

**Primary recommendation:** Execute D-01 through D-12 as written — every decision survived verification. Add three things CONTEXT.md does not cover: wrap the RED fixture's typo in `pytest.raises(AttributeError)` (Pitfall 1), record the `DecodePolicy` re-ratification demanded by `29-SEMANTICS-MATRIX.md:128` (Pitfall 2), and export the four models in `__all__` so the surface snapshot and the Phase 32 AST gate can see them (Pitfall 3).

## Corrections and Additions to CONTEXT.md

CONTEXT.md instructs that its Existing Code Insights be verified and built on, not re-litigated. All twelve decisions **stand**. The following are refinements to stated *facts and rationales*, not challenges to the decisions they support.

| # | CONTEXT claim | Verified finding | Impact on plan |
|---|---|---|---|
| C-1 | D-07: "sin eso la próxima corrida viva **escribe** `\"schema\": \"Cotizacion\"` en los baselines committeados y F33 arranca corrupto" | **Impossible.** `_write_or_check_schema` (`main_iol.py:1174-1180`) writes only under `if not file_path.exists()`; all four baselines exist. On mismatch it emits a FINDING and explicitly does **not** overwrite (D-25). `[VERIFIED: read main_iol.py:1174-1197]` | The decision (apply `to_dict()`) is unchanged and still mandatory — but for a **different and more dangerous** reason, see C-2. Do not write a verification step that asserts "baseline not corrupted"; it can never fail. |
| C-2 | D-07: implies all ≥5 `schema_of` sites fail the same way | Three distinct failure modes, and the two most common are **silent**. See § The `schema_of` Blast Radius. Sites `:1066` and `:1102` guard on `isinstance(observed, dict)`, which becomes `False` for a model — the entire field-map loop is **skipped** and the probe reports `PASS "3 endpoints checked, no drift"`. Site `:918-919` compares `"Cotizacion" == "Cotizacion"` → still equal → **vacuous PASS**. Only `_write_or_check_schema` fails loudly. `[VERIFIED: measured — isinstance(schema_of(model), dict) is False]` | Verification steps must assert the probes remain **non-vacuous**, not merely that they pass. A plan that only checks "driver still green" would ship this regression. |
| C-3 | D-07: lists `:918-919`, `:1066`, `:1102`, `:1164` as the `to_dict()` sites | Correct, but `:1164` fans out to **3 of 4** snapshot targets, not 4. `by_type_envelope` is captured from a **raw `_request`**, not from the client wrapper (`main_iol.py:995`), so `get_instruments_by_type` is **immune** to the migration. Same for the `envelope["titulos"]` check at `:1032`. `[VERIFIED: read main_iol.py:976-1062, 1200-1244]` | Do not apply `to_dict()` to `by_type_envelope`; doing so would be a no-op at best and a `AttributeError` at worst. The by-type snapshot needs no change. |
| C-4 | D-06: "**~12 tests** que mockean `get_instruments` como dict" | **16 payload sites + 2 asserts = 18 lines across 6 files.** Full list in § Blast Radius. `[VERIFIED: grep]` | Task sizing; a task written for "~12 sites" will leave 4 behind and fail the suite. |
| C-5 | D-09: "Ruff no necesita exención camelCase (`N` no está en `select`)" | **Correct** (`pyproject.toml:53-68` has no `N`). Note the adjacent inconsistency: `higyrus_client/models.py:19-21` docstring *claims* an `N815` per-file-ignore that does not exist for higyrus — only `market-data-client` has one (`pyproject.toml:74`), and it is inert. `[VERIFIED: read pyproject.toml:53-74]` | No ruff change needed. If the plan copies higyrus's module docstring as a template, **drop that sentence** rather than propagate a false claim into a third file. |
| C-6 | *(absent from CONTEXT.md)* | Phase 29 assigned Phase 30 a named obligation: "**iol's value is re-ratified when Phase 30 adds `iol_client/models.py`**: the Phase 30 planner must confirm that the models it writes actually want typed-zero substitution rather than matriz-style `None`, and record that confirmation." (`29-SEMANTICS-MATRIX.md:126-131`) `[VERIFIED: read]` | Add an explicit deliverable. See Pitfall 2 for the finding and the recommended ratification text. |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Wire shape declaration (field names, types, nullability) | `iol_client/models.py` (NEW) | — | The models module is the single declaration of the wire contract; nothing else in the package may restate a field name. |
| Payload → model coercion + divergence reporting | `iol_client/_decode.py` (untouched) | `models.SafeModel.from_api` | The walker is byte-frozen by the Phase 29 intactness gate. `models.py` may only *call* it; every behavior lives in `walk_model`/`walk_field`. |
| Envelope unwrap + shape guards + decode-scope ownership | `iol_client/_core.py` parsers | `_decode._response_parser` | Envelope structure (`titulos`) is transport-shaped, not domain-shaped — it is unwrapped as a raw dict before any model exists. The parser owns the per-response `DecodeScope`. |
| Public typed surface (16 signatures) | `client.py` / `aio.py` methods + module shims | `_core` parsers | Transport shells stay 3-liners; they only re-annotate the return type and delegate. No logic moves into them. |
| Serialization back to a wire-shaped dict | `models.SafeModel.to_dict` | — | Migration escape hatch + the harness's `schema_of` adapter. Deliberately the *only* dict-producing path. |
| Structural drift detection against the live API | `verification/` + `main_iol.py` probes | `_decode` divergence records | **Shifts this phase** — see Pitfall 5. `schema_of` loses drift power over modeled fields; the walker gains it. |
| Static typo rejection | `mypy --strict` via `ci.yml:85-94` | RED fixture in `packages/iol-client/tests/` | The phase's actual deliverable per TYP-01: the guarantee is a *typecheck* guarantee, so its proof must be a typecheck artifact. |

## Project Constraints (from CLAUDE.md)

| Directive | Source | How Phase 30 complies |
|---|---|---|
| Python 3.12+, uv, httpx, pytest+pytest-httpx, ruff, mypy strict — must pass existing CI | Constraints | No new dependency. All four gates re-run; baseline is **205 iol tests passing** `[VERIFIED: uv run pytest packages/iol-client -q]`. |
| Sin código compartido entre paquetes (por diseño); fixes dentro de cada paquete | Constraints / Architecture | `models.py` is iol-local. `SafeModel` is **copied** from higyrus, never imported — an import would violate the no-shared-internals constraint and the import-linter root-package boundary. |
| Dual sync/async: cualquier fix debe espejarse en `client.py` y `aio.py` | Constraints | All 16 signatures move together; sync and async must not land in separate commits (see Pitfall 6). |
| Nunca commitear `.env` ni exponer credenciales en logs/reportes/tests | Constraints / Security | No credential surface is touched. Divergence records carry **types and paths, never values** (`IOLDecodeError` docstring, `exceptions.py:41-43`) — the models must not add any value-carrying log line. |
| `from __future__ import annotations` mandatory in every module | Conventions / Code Style | Required in `models.py`. It is also load-bearing here — see Pitfall 8. |
| Models: `@dataclass(frozen=True, slots=True)`, inherit `SafeModel`, construct via `from_api`, wire names camelCase verbatim, `Optional` defaults `None` | Conventions / Model Design | Exactly D-01/D-02/D-03. |
| Explicit `__all__`; models re-exported from `__init__.py` | Conventions / Exports | See Pitfall 3 — the four models must be exported. |
| Every module opens with a module-level docstring stating purpose and rationale | Conventions / Comments | `29-PATTERNS.md:711-726` gives the exact convention for new modules. |
| GSD workflow enforcement — no direct edits outside a GSD command | GSD section | Research is read-only; the one scratch file written to `packages/iol-client/tests/` during RED-fixture validation was removed `[VERIFIED: rm + confirmed]`. |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `dataclasses` (stdlib) | Python 3.12.11 | `@dataclass(frozen=True, slots=True)` models + `asdict` for `to_dict()` | Already the monorepo's model mechanism in 3 of 6 packages; `asdict` recursion semantics are exactly what `schema_of` needs `[VERIFIED: measured in-session + docs.python.org/3.12/library/dataclasses.html]` |
| `typing` (stdlib) | Python 3.12.11 | `Self` for `from_api`, `Any` for `to_dict` return | Matches the higyrus/market-data template verbatim `[VERIFIED: read higyrus_client/models.py:36-54]` |
| `iol_client._decode` | in-tree, Phase 29 | `walk_model`, `POLICY`, `current_sink`, `_response_parser` | Byte-frozen by the intactness gate; Phase 30 is its first real consumer `[VERIFIED: read]` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` | >=8.3 | RED fixture runtime leg + re-mocked suite | Every test task |
| `pytest-httpx` | >=0.34 | `httpx_mock` re-mocks (D-06) | The 16 payload re-mock sites |
| `mypy` | >=1.13, `strict = true` | The phase's actual deliverable | RED fixture + all 16 signatures |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| stdlib dataclasses | `msgspec` | **Closed, NO-GO.** Signed `no-go-stdlib-only` by sebadlf 2026-08-19 (`29-DLOCK-MSGSPEC.md`). Cannot implement observable mode; would violate the D-09 RESPONSE-`Literal` lock. Do not revisit. |
| stdlib dataclasses | `pydantic` v2 | Out of scope per REQUIREMENTS.md — lenient coercion masks divergences, which is the exact failure this milestone exists to eliminate. |
| attribute models | `TypedDict` | Out of scope per REQUIREMENTS.md — mypy does not detect typos through `.get()`, which is the drivers' actual access style. |
| `dataclasses.asdict` | hand-written `to_dict` per model | market-data's precedent is hand-written, but those are **request** models that intentionally *drop* `None` keys. A response model must preserve `None` (it is the drift signal). `asdict` is correct here. |

**Installation:** None. Phase 30 adds **zero** external packages.

**Version verification:** `uv.lock` is untouched by this phase. Phase 34 refreshes it exactly once for all bumps.

## Package Legitimacy Audit

**Not applicable — this phase installs zero external packages.**

Every symbol Phase 30 uses is either Python 3.12 stdlib (`dataclasses`, `typing`) or already resident in the workspace and already locked (`httpx`, `pytest`, `pytest-httpx`, `mypy`, `ruff`). `uv.lock` must not be modified by this phase; a lockfile diff in a Phase 30 commit is a defect, not a deliverable.

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Model Field Tables

Derived directly from `.planning/verification/schemas/iol-client/*.json` (captured live 2026-06-06). Each table below was **executed** against the walker: constructing these exact shapes from the captured schemas yields **zero divergence records**, and `schema_of(model.to_dict())` reproduces the committed baseline **exactly**. `[VERIFIED: measured in-session]`

### `Punta` — 4 fields (nested, define first)

| Field | Type | Source |
|---|---|---|
| `cantidadCompra` | `float` | `get-instruments-by-type.json` → `titulos[].puntas` |
| `cantidadVenta` | `float` | ″ |
| `precioCompra` | `float` | ″ |
| `precioVenta` | `float` | ″ |

The only element shape observed anywhere in the corpus. Used as `Punta | None` in `Titulo` and as `list[Punta] | None` in `Cotizacion` (D-02).

### `Cotizacion` — 20 fields, shared by `get_quote` and each `get_historical_quotes` row

The two endpoints carry **identical key sets**; they differ only in which values arrive `null`. The `Optional` markers below are the union of both observations (D-03).

| Field | Type | quote | historical | Note |
|---|---|---|---|---|
| `apertura` | `float` | float | float | |
| `cantidadOperaciones` | `int` | int | int | **D-04** — strict leg; see Pitfall 4 |
| `cierreAnterior` | `float` | float | float | |
| `descripcionTitulo` | `str \| None` | str | **NoneType** | D-03 |
| `fechaHora` | `str` | str | str | |
| `interesesAbiertos` | `float` | float | float | |
| `laminaMinima` | `int` | int | int | |
| `lote` | `int` | int | int | |
| `maximo` | `float` | float | float | |
| `minimo` | `float` | float | float | |
| `moneda` | `str` | str | str | |
| `montoOperado` | `float` | float | float | |
| `plazo` | `str \| None` | str | **NoneType** | D-03; stays `str`, **not** `Literal` (DT-07 → F33) |
| `precioAjuste` | `float` | float | float | |
| `precioPromedio` | `float` | float | float | |
| `puntas` | `list[Punta] \| None` | `[]` | **NoneType** | D-02/D-03; element **unobserved** |
| `tendencia` | `str` | str | str | |
| `ultimoPrecio` | `float` | float | float | the attribute the drivers read |
| `variacion` | `float` | float | float | |
| `volumenNominal` | `float` | float | float | |

### `Instrumento` — 2 fields, `get_instruments` (top-level list)

| Field | Type |
|---|---|
| `instrumento` | `str` |
| `pais` | `str` |

The live wire is a **top-level list** `[{instrumento, pais}]` — not the `{"instrumentos": …}` envelope that 16 test mocks assert. This mismatch is the entire basis of D-06.

### `Titulo` — 21 fields, rows of the `titulos` envelope

| Field | Type | Note |
|---|---|---|
| `apertura` | `float` | |
| `cantidadOperaciones` | `float` | **D-04** — lenient leg; see Pitfall 4 |
| `descripcion` | `str` | |
| `fecha` | `str` | |
| `fechaVencimiento` | `str \| None` | D-03 — declared type is a guess; see Assumption A1 |
| `laminaMinima` | `int` | |
| `lote` | `int` | |
| `maximo` | `float` | |
| `mercado` | `str` | stays `str`, **not** `Literal` (DT-07 → F33) |
| `minimo` | `float` | |
| `moneda` | `str` | |
| `plazo` | `str` | non-null here, unlike `Cotizacion` |
| `precioEjercicio` | `float \| None` | D-03 — declared type is a guess; see A1 |
| `puntas` | `Punta \| None` | D-02 — **singular**, not a list |
| `simbolo` | `str` | |
| `tipoOpcion` | `str \| None` | D-03 — declared type is a guess; see A1 |
| `ultimoCierre` | `float` | |
| `ultimoPrecio` | `float` | |
| `variacionPorcentual` | `float` | |
| `volumen` | `float` | |

## The 16 Signatures

All 16 verified present at the stated locations. Current types are the **exact** strings pinned in `verification/snapshots/iol-client-surface.txt:18-21`. `[VERIFIED: read client.py, aio.py, snapshot file]`

| # | Function | Surface | Location | Current return | Target return |
|---|---|---|---|---|---|
| 1 | `get_quote` | sync method | `client.py:514-527` | `dict[str, Any]` | `Cotizacion` |
| 2 | `get_quote` | sync shim | `client.py:673-680` | `dict[str, Any]` | `Cotizacion` |
| 3 | `get_quote` | async method | `aio.py:536-546` | `dict[str, Any]` | `Cotizacion` |
| 4 | `get_quote` | async shim | `aio.py:693-699` | `dict[str, Any]` | `Cotizacion` |
| 5 | `get_historical_quotes` | sync method | `client.py:529-547` | `list[dict[str, Any]]` | `list[Cotizacion]` |
| 6 | `get_historical_quotes` | sync shim | `client.py:683-694` | `list[dict[str, Any]]` | `list[Cotizacion]` |
| 7 | `get_historical_quotes` | async method | `aio.py:548-562` | `list[dict[str, Any]]` | `list[Cotizacion]` |
| 8 | `get_historical_quotes` | async shim | `aio.py:702-713` | `list[dict[str, Any]]` | `list[Cotizacion]` |
| 9 | `get_instruments` | sync method | `client.py:549-556` | **`Any`** | `list[Instrumento]` |
| 10 | `get_instruments` | sync shim | `client.py:697-699` | **`Any`** | `list[Instrumento]` |
| 11 | `get_instruments` | async method | `aio.py:564-568` | **`Any`** | `list[Instrumento]` |
| 12 | `get_instruments` | async shim | `aio.py:715-716` | **`Any`** | `list[Instrumento]` |
| 13 | `get_instruments_by_type` | sync method | `client.py:558-571` | `list[dict[str, Any]]` | `list[Titulo]` |
| 14 | `get_instruments_by_type` | sync shim | `client.py:702-708` | `list[dict[str, Any]]` | `list[Titulo]` |
| 15 | `get_instruments_by_type` | async method | `aio.py:570-579` | `list[dict[str, Any]]` | `list[Titulo]` |
| 16 | `get_instruments_by_type` | async shim | `aio.py:719-725` | `list[dict[str, Any]]` | `list[Titulo]` |

**Untouched by design:** the four builders (`_core.py:234-319`). `ajustada: Literal["ajustada", "sinAjustar"]` is an **INPUT** literal that predates DT-07 and is preserved (`_core.py:265`); `InstrumentType` likewise. Neither is a RESPONSE field, so the D-09 lock does not reach them.

## Architecture Patterns

### System Architecture — decode data flow

```
              ┌─────────────────────────────────────────────────────────────┐
   caller ───▶│  client.get_quote(...)   /   aio.get_quote(...)             │
              │  (16 signatures — 3-liner shells, type annotation only)     │
              └───────────────┬───────────────────────┬─────────────────────┘
                              │ build                 │ parse
                              ▼                       ▼
                 _core.build_*_request()      _core.parse_*_response(resp)
                 (UNTOUCHED — 4 builders)      @_decode._response_parser
                              │                       │  ← owns ONE DecodeScope
                              │                       │    per HTTP response
                              ▼                       ▼
                        RequestSpec           resp.read() → raise_for_response()
                              │                       │
                              │                       ├─ shape guard (list? dict?)
                        transport                     │     └─ fail ▶ IOLAPIError(0, msg)
                    (client.py / aio.py)              │
                              │                       ├─ envelope unwrap  ← by-type ONLY
                              │                       │     data.get("titulos", [])
                              ▼                       │     (raw dict; NOT modeled)
                       httpx.Response ────────────────┘
                                                      ▼
                                       Model.from_api(row)   ← models.SafeModel
                                                      │
                                                      ▼
                                   _decode.walk_model(cls, payload, POLICY, sink)
                                                      │
                        ┌─────────────────────────────┼──────────────────────────┐
                        ▼                             ▼                          ▼
                  extra-key scan             per-field walk_field()        nested / list[]
                  (sorted, INFO)             ├ Optional  → None, no record  hint(**walk_model)
                        │                    ├ str/int/float → typed zero    NEVER .from_api
                        │                    │   + WARNING record            (Phase 29 WR-03)
                        │                    └ Literal → passthrough
                        │                        (literal_enforced=False)
                        └──────────────┬───────────────┘
                                       ▼
                          DecodeScope dedupe  (model, field_path, kind)
                                       │
                        ┌──────────────┴──────────────┐
                        ▼                             ▼
              strict_decode=False           strict_decode=True  ← F33, NOT F30
              logger record only            raise IOLDecodeError
                        │
                        ▼
                  typed model ──▶ caller reads  quote.ultimoPrecio   (mypy-checked)
                        │
                        └──▶ .to_dict()  ──▶  schema_of(...)  ──▶  verification baselines
                                                                   (harness path only)
```

### Recommended structure

```
packages/iol-client/src/iol_client/
├── models.py      # NEW — SafeModel + Punta, Cotizacion, Instrumento, Titulo
├── _decode.py     # UNTOUCHED — byte-frozen by the Phase 29 intactness gate
├── _core.py       # 4 parsers rewritten in place; 4 builders untouched
├── client.py      # 8 return annotations (4 methods + 4 shims)
├── aio.py         # 8 return annotations (4 methods + 4 shims)
├── exceptions.py  # UNTOUCHED
└── __init__.py    # +4 model re-exports in __all__  (see Pitfall 3)
```

### Pattern 1: the minimal `SafeModel` (D-01)

Copy from `higyrus_client/models.py:41-54` — 14 lines, no `empty()`, no mapping-axis, no `received_at` hook.

```python
# Source: packages/higyrus-client/src/higyrus_client/models.py:41-54 (VERIFIED verbatim)
class SafeModel:
    """Base class for IOL API response models.

    Subclasses must be frozen dataclasses. Construct instances via
    :meth:`from_api` to tolerate partial or missing fields.
    """

    @classmethod
    def from_api(cls, payload: Any) -> Self:
        """Build an instance from an API payload, with safe defaults."""
        kwargs = _decode.walk_model(
            cls, payload, policy=_decode.POLICY, sink=_decode.current_sink()
        )
        return cls(**kwargs)

    def to_dict(self) -> dict[str, Any]:
        """Escape hatch for the dict→model break, and the harness's schema_of adapter."""
        return dataclasses.asdict(self)  # D-08
```

Note `to_dict` on the **base**, not per-model: `asdict` is generic, so one definition covers all four models. This diverges from market-data's per-model hand-written `to_dict`, correctly — those drop `None` keys, which a response model must not do.

### Pattern 2: model declaration (D-01/D-02/D-03)

```python
# Declare Punta FIRST — see Pitfall 8 for why ordering is a soft rather than hard constraint.
@dataclass(frozen=True, slots=True)
class Punta(SafeModel):
    cantidadCompra: float
    cantidadVenta: float
    precioCompra: float
    precioVenta: float


@dataclass(frozen=True, slots=True)
class Cotizacion(SafeModel):
    """Cotización — devuelta por ``get_quote`` y por cada fila de ``get_historical_quotes``.

    Ambos endpoints traen el MISMO set de 20 claves; difieren sólo en cuáles
    llegan ``null``. ``descripcionTitulo``, ``plazo`` y ``puntas`` son
    ``Optional`` porque la serie histórica los envía ``null`` — en ``get_quote``
    los tres llegan poblados (D-03).

    ``puntas``: la captura viva registró ``[]`` en ``get_quote``, así que el
    ELEMENTO de la lista es inobservado; ``Punta`` es la única forma de elemento
    vista en el corpus (vía ``Titulo``). Se confirma en la Phase 33 (D-02).
    """

    apertura: float
    cantidadOperaciones: int   # D-04: int acá, float en Titulo — el corpus difiere
    ...
    puntas: list[Punta] | None
    ...
```

### Pattern 3: parser rewrite (D-05/D-06) — the iol adaptation

The higyrus pattern (`_core.py:457-500`) is the model, but **three adaptations are required**; it is not a verbatim copy.

```python
# Source pattern: packages/higyrus-client/src/higyrus_client/_core.py:457-500
# Adaptation 1: iol has NO `_consume_and_check`. Its parsers use the existing
#   `resp.read()` + `raise_for_response(resp)` pair (_core.py:329-330). Copying
#   higyrus's helper verbatim would ADD 204/empty-body tolerance that iol does
#   not have today — a behavior change outside this phase's scope.
# Adaptation 2: `IOLAPIError.__init__(status_code: int, message: str)` is TWO
#   POSITIONAL args (exceptions.py:13). higyrus's is `(status_code, errors=[...])`.
# Adaptation 3: the decorator goes on the shared helper (as higyrus does), so the
#   four public parsers stay undecorated one-liners and nesting stays safe.

@_decode._response_parser
def _parse_list_or_raise(resp: httpx.Response, model_cls: type[Any]) -> list[Any]:
    """Helper: parsers que retornan ``list[Model]`` sobre una lista top-level."""
    resp.read()
    raise_for_response(resp)
    raw = resp.json()
    if not isinstance(raw, list):
        raise IOLAPIError(0, f"expected list, got {type(raw).__name__}")
    return [model_cls.from_api(item) for item in raw]


@_decode._response_parser
def parse_get_quote_response(resp: httpx.Response) -> Cotizacion:
    """Pure: parse cotización response → ``Cotizacion``."""
    resp.read()
    raise_for_response(resp)
    return Cotizacion.from_api(resp.json())


def parse_get_historical_quotes_response(resp: httpx.Response) -> list[Cotizacion]:
    """Pure: parse seriehistorica response → ``list[Cotizacion]``."""
    result: list[Cotizacion] = _parse_list_or_raise(resp, Cotizacion)
    return result


def parse_get_instruments_response(resp: httpx.Response) -> list[Instrumento]:
    """Pure: parse instruments listing → ``list[Instrumento]``.

    D-06: el wire real es una lista top-level ``[{instrumento, pais}]``. El
    guard `isinstance(raw, list)` RAISES — no degrada a ``[]``, que es
    exactamente el bug del ``[]`` silencioso que este milestone elimina.
    """
    result: list[Instrumento] = _parse_list_or_raise(resp, Instrumento)
    return result


@_decode._response_parser
def parse_get_instruments_by_type_response(resp: httpx.Response) -> list[Titulo]:
    """Pure: parse instruments-by-type → ``list[Titulo]`` bajo la clave ``titulos``.

    D-06: el unwrap del envelope es un paso RAW-DICT antes de construir modelos —
    el envelope ``titulos`` no se modela.
    """
    resp.read()
    raise_for_response(resp)
    data: dict[str, Any] = resp.json()
    titulos: list[dict[str, Any]] = data.get("titulos", [])
    return [Titulo.from_api(row) for row in titulos]
```

**Import direction:** `_core` → `models` → `_decode`. The only iol import-linter contract forbids `_core` → `client`/`aio` (`pyproject.toml:163-167`); `_core` → `models` is unconstrained. **No new contract is needed** `[VERIFIED: read pyproject.toml:138-172]` — D-05 confirmed.

### Anti-patterns to avoid

- **Calling `Model.from_api(value)` for a nested field.** The walker deliberately builds nested models with `hint(**walk_model(...))`, never `from_api` (`_decode.py:475-490`, Phase 29 WR-03). Do not "helpfully" add a `from_api` override to `Punta` — an override's sink resolves through `current_sink()` and would leave the enclosing scope, breaking dedupe lock 5.
- **A dict-compat `__getitem__` shim on the models.** Explicitly out of scope (REQUIREMENTS.md) — it preserves the exact typo class the milestone eliminates.
- **`list[dict[str, Any]]` for `puntas`.** D-02 names this as evading the Phase 32 gate on a technicality.
- **Degrading a failed shape guard to `[]`.** D-06's stated reason; it reintroduces the silent-`[]` bug.
- **Touching `_decode.py`.** Byte-frozen by the intactness gate, which runs in the CI **lint** job (`29-09` decision note) — this one *does* run in CI, unlike `verification/`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---|---|---|---|
| Payload → model coercion | A per-model `__post_init__` or a local `_coerce` | `_decode.walk_model` via `SafeModel.from_api` | The walker is the entire Phase 29 deliverable, byte-frozen across 5 copies. A local coercion path is invisible to the divergence census Phase 33 depends on. |
| Recursive model → dict | A hand-written per-model `to_dict` | `dataclasses.asdict(self)` on the base class | Recurses into dataclasses, dicts, lists and tuples; deepcopies other values `[VERIFIED: docs.python.org/3.12/library/dataclasses.html + measured]`. All iol leaves are scalars, so the deepcopy leg is free. |
| Per-response divergence dedupe | A module-level `set()` of seen fields | `@_decode._response_parser` | A process-lifetime dedupe set is rejected **by name** by aggregation lock 6. |
| Type-hint resolution + caching | `cls.__annotations__` reads | `_decode.hints_for` (`@lru_cache(maxsize=512)`) | ~89% of decode cost is `get_type_hints` re-evaluation under `from __future__ import annotations`; the cache is what made the msgspec NO-GO hold at 19.37 ms/5000 rows. |
| A typecheck-failure test | `subprocess` invocation of mypy | `# type: ignore[attr-defined]` under `warn_unused_ignores = true` | D-10; ~10s of CI saved and no new machinery. Validated in both directions below. |

**Key insight:** every one of these has a Phase 29 artifact behind it. The temptation in Phase 30 is to solve a local problem locally; each such solution silently detaches iol from the shared census that Phase 33 must read.

## Runtime State Inventory

Phase 30 is a refactor/migration phase (dict→model source break), so this section is mandatory.

| Category | Items Found | Action Required |
|---|---|---|
| **Stored data** | **None** — `iol-client` persists exactly one artifact: the OAuth token cache written by `_token_cache.py` (Phase 14 SEC-01), which stores tokens and expiries only. It contains no response payloads and no model-shaped data. `[VERIFIED: grep — no models/response persistence in iol]` | None. Do not touch the token cache. |
| **Live service config** | **None.** IOL is a read-only third-party vendor API; the client registers nothing server-side. No dashboards, tags or workflows carry a model name. | None. |
| **OS-registered state** | **None.** No scheduler entries, no pm2/launchd/systemd units reference iol models (none exist yet). | None. |
| **Secrets / env vars** | **None changed.** `IOL_USERNAME`/`IOL_PASSWORD`/`IOL_BASE_URL` are consumed by `_state.py` and are untouched by a response-shape change. `.env` is never read by `models.py`. | None. |
| **Build artifacts / installed packages** | **`uv.lock` must NOT change** (no dependency delta). The workspace is installed editable via `uv sync`, so a new `models.py` is picked up without reinstall. `packages/iol-client/dist/` is not tracked. | Verify `git diff --stat uv.lock` is **empty** in every Phase 30 commit. |
| **Committed baselines (repo-internal state that survives a source edit)** | **THREE**, and this is the category that actually bites: `verification/snapshots/iol-client-surface.txt` (4 signature lines change + 4 model class lines appear) and `.planning/verification/schemas/iol-client/{get-quote,get-historical-quotes,get-instruments}.json` (unchanged **only if** `to_dict()` is applied — see § The `schema_of` Blast Radius). | Regenerate the surface snapshot in the same commit (D-09). The three JSON schemas must remain **byte-identical**; that is the phase's strongest end-to-end proof, and it is verifiable offline. |

## The `schema_of` Blast Radius

`verification.schema.schema_of` reduces a payload to keys+types and falls through to `type(payload).__name__` for anything that is not a `dict` or `list` (`verification/schema.py:36-41`). A dataclass instance therefore reduces to the **string** `"Cotizacion"`. Three distinct failure modes follow, and the two most common are silent.

| Site | Consumes | Without `to_dict()` | Severity |
|---|---|---|---|
| `main_iol.py:918-919` (parity probe) | `schema_of(sync_data) == schema_of(async_data)` | `"Cotizacion" == "Cotizacion"` → **equal** → probe reports PASS. The sync/async parity check silently loses **all** discriminating power. | **Silent — worst** |
| `main_iol.py:1066` (quote field map) | `observed = schema_of(quote)`, then `if isinstance(observed, dict)` | `isinstance("Cotizacion", dict)` is `False` `[VERIFIED: measured]` → the whole `_ASSUMED_QUOTE_FIELDS` loop is **skipped**; probe reports `PASS "3 endpoints checked, no drift"`. | **Silent** |
| `main_iol.py:1102` (historical field map) | `schema_of(historical[0])` + same guard | Same — loop skipped, vacuous PASS. | **Silent** |
| `main_iol.py:1164` via `_write_or_check_schema`, for the **3** targets `get_quote` / `get_historical_quotes` / `get_instruments` | `schema_of(raw_payload)` vs committed baseline | `"Cotizacion"` / `["Cotizacion"]` / `["Instrumento"]` vs the baseline dicts → mismatch → **3 spurious SHAPE findings**. Baseline is **not** overwritten (`if not file_path.exists()`, D-25). | Loud |
| `main_iol.py:1015-1062` (`envelope["titulos"]`) and the 4th snapshot target `get_instruments_by_type` | `by_type_envelope` from a **raw `_request`** (`main_iol.py:995`) | **Immune** — never passes through the client wrapper. | None |

**With `to_dict()` applied at the four sites, all three committed JSON baselines round-trip byte-identically.** `[VERIFIED: measured in-session against all four schema files]`

Consequence for the plan's verification steps: asserting "the driver still reports PASS" is **not sufficient** — three of the four sites report PASS precisely when they are broken. Verify non-vacuity instead: assert `isinstance(schema_of(quote.to_dict()), dict)` is `True`, and assert the regenerated schema equals the committed baseline.

## Blast Radius — exact inventories

### D-06 re-mocks: `{"instrumentos": …}` → top-level list

**16 payload sites + 2 asserts = 18 lines across 6 files** (CONTEXT.md said "~12"). `[VERIFIED: grep]`

| File | Payload lines (`json=` / `content=`) | Assert lines |
|---|---|---|
| `tests/test_refresh_token_lifecycle.py` | 66, 118, 159, 201 | — |
| `tests/test_refresh_token_lifecycle_async.py` | 71, 118, 152, 188 | — |
| `tests/test_client.py` | 87, 180, 217 | 90 |
| `tests/test_async_client.py` | 142, 177 | — |
| `tests/test_fixture_reaches_production.py` | 43, 64 | — |
| `tests/test_core.py` | 354 (`content=b'{"instrumentos": …}'`) | 356 |

**Minimal payload guidance** (Claude's Discretion per CONTEXT): 14 of the 16 sites assert only on the Authorization header or the request count — the payload is genuinely incidental, and `json=[]` is the cheapest correct re-mock. Only `test_client.py:87-90` and `test_core.py:354-356` assert on returned content; those need one element, e.g. `[{"instrumento": "acciones", "pais": "argentina"}]`. **`[]` is safe here specifically because the guard raises on non-list, not on empty** — an empty list is a valid list.

### Attribute-access migration: dict-subscript and dict-equality asserts

**23 sites.** `[VERIFIED: grep]`

| File | Lines | Notes |
|---|---|---|
| `tests/test_client.py` | 61, 70, 81, 90, 112, **114**, 113, 148, **556** | |
| `tests/test_async_client.py` | 41, 52, 61, 74, 75, **76**, 110, 343, **543** | |
| `tests/test_core.py` | **338**, 350, 356, 365, 371 | |

Four of these need more than a mechanical `["x"]` → `.x` rewrite:

- **`test_client.py:114` and `test_async_client.py:76`** assert `quote["simbolo"] == "GGAL"`. **`simbolo` is not a field of `Cotizacion`** — it is not among the 20 keys in `get-quote.json`. These asserts must be **deleted**, not rewritten; the key becomes an `extra` divergence record. This is a real decision the plan must make explicitly.
- **`test_client.py:556` and `test_async_client.py:543`** assert `quote == {"ultimoPrecio": 123.45}` — dict equality against a model. Must become an attribute assert.
- **`test_core.py:338`** asserts `data == {"simbolo": "GGAL", "precio": 1234.5}` — **neither** key is a `Cotizacion` field. Full rewrite.
- **`test_core.py:371`** asserts `data == []` (missing `titulos` key). This one **survives unchanged** — the unwrap still yields `[]`.

**Not affected:** `test_core.py:50, 140, 251` (`spec.data` asserts on login/refresh builders — builders are untouched). `tests/test_client_class.py` contains **zero** affected sites `[VERIFIED: grep returned empty]`. `tests/test_logging.py` builds synthetic `LogRecord`s and never decodes a real payload — **immune** `[VERIFIED: read]`.

### Baseline

`205 tests passing` for `packages/iol-client` before any change `[VERIFIED: uv run pytest packages/iol-client -q]`. The migrated suite must be ≥ 205 (the RED fixture adds at least one).

## Common Pitfalls

### Pitfall 1 — the naive RED fixture turns CI red at runtime *(highest severity)*

**What goes wrong:** D-10's fixture is a *static* assertion, but pytest still **executes** the file, and `packages/iol-client` is in the CI test matrix (`ci.yml:100-107`). A deliberate attribute typo raises `AttributeError` at runtime.

**Measured:**

```
FAILED tests/test_zz_red_probe.py::test_typo_is_caught_by_mypy
E   AttributeError: 'Cotizacion' object has no attribute 'ultimoPrecioo'. Did you mean: 'ultimoPrecio'?
1 failed, 1 passed
```
`[VERIFIED: measured in-session]`

**Why it happens:** the phase's guarantee is a typecheck guarantee, so the natural instinct is to write only the typecheck leg. `slots=True` guarantees the runtime leg raises too.

**How to avoid:** wrap the typo in `pytest.raises(AttributeError)`. This makes the fixture stronger, not weaker — it now pins *both* legs of the guarantee. Validated form:

```python
def test_attribute_typo_is_rejected_statically_and_at_runtime() -> None:
    """RED fixture: both legs must hold.

    Static leg: mypy flags ``ultimoPrecioo`` [attr-defined]; the ignore absorbs it.
    Under ``warn_unused_ignores = true`` the ignore becomes an ERROR the day the
    typo starts resolving, so the fixture cannot rot into a no-op.
    Runtime leg: ``slots=True`` makes the same typo an AttributeError.
    """
    q = Cotizacion.from_api({"ultimoPrecio": 1.0})
    with pytest.raises(AttributeError):
        _ = q.ultimoPrecioo  # type: ignore[attr-defined]
    assert q.ultimoPrecio == 1.0
```

**Measured on this exact form:** `mypy: Success` / `pytest: 1 passed` / `ruff: clean (modulo import order)` `[VERIFIED: measured in-session]`

**Non-vacuity, both directions — measured:**
- typo + ignore → mypy **Success** (the ignore is consumed → the error was real)
- correct attribute + same ignore → `error: Unused "type: ignore" comment [unused-ignore]`
`[VERIFIED: measured in-session]` — D-10's claim holds exactly, and it holds **only** because `warn_unused_ignores = true` (`pyproject.toml:86`).

**Warning sign:** a RED fixture that passes pytest without a `pytest.raises` is almost certainly not executing the typo.

### Pitfall 2 — the unrecorded `DecodePolicy` re-ratification

**What goes wrong:** Phase 29 explicitly deferred a decision to this phase and CONTEXT.md does not carry it forward. `29-SEMANTICS-MATRIX.md:126-131`: *"iol's value is re-ratified when Phase 30 adds `iol_client/models.py`: the Phase 30 planner must confirm that the models it writes actually want typed-zero substitution rather than matriz-style `None`, and record that confirmation."* Shipping without recording it leaves a Phase 29 acceptance criterion open.

**The finding (research recommendation — ratify, do not change):** iol's constant is `POLICY = DecodePolicy("", 0, 0.0, False, "from_api_none", False, False)` (`_decode.py:140`) — typed zeros. This is **correct** for the models D-01 through D-04 specify, for three reasons:
1. D-03 already routes every observed-nullable field to `T | None`, which the walker returns as `None` **without** a divergence record (`_decode.py:433-442`). The fields that would benefit from matriz-style `None` already get it, by declaration.
2. matriz's `None` policy travels with `scalar_passthrough=True`, which returns the wrong-typed wire value unchanged. That would put an `int` into a field annotated `float`, breaking the very mypy guarantee TYP-01 exists to provide.
3. `literal_enforced=False` is fixed by D-09 and is not a tunable in any copy.

`[VERIFIED: read 29-SEMANTICS-MATRIX.md:104-148 + _decode.py:140]`

**How to avoid:** make it a named deliverable — a short ratification paragraph in the phase artifacts (or the `models.py` module docstring) confirming typed-zeros. Do **not** edit `_decode.py`: it is byte-frozen, and the constant is already the value being ratified.

### Pitfall 3 — models absent from `__all__` silently defeat two gates

**What goes wrong:** if the four models are not re-exported from `__init__.py`, `verification/regen_snapshots.py` cannot enumerate them (it walks the public surface), and Phase 32's AST gate over `__all__` returns has nothing to check. Consumers also cannot import the annotation they now need for their own type hints.

**Why it happens:** D-01 specifies the model shapes but never says "export them"; the 16 signatures work fine without the export, so tests stay green.

**How to avoid:** follow the higyrus precedent — `higyrus/__init__.py:56-64` re-exports every model and lists each in `__all__` `[VERIFIED: read]`. The iol snapshot will then gain **4 class lines** (`Cotizacion`, `Instrumento`, `Punta`, `Titulo`) alongside the **4 modified function lines** — higyrus's snapshot shows classes rendered with their full `__init__` signature `[VERIFIED: read higyrus-client-surface.txt:9-16]`.

**Warning sign:** the regenerated `iol-client-surface.txt` diff shows 4 changed lines but no added lines.

### Pitfall 4 — `cantidadOperaciones` is the one field where the two models disagree, asymmetrically

**What goes wrong:** D-04 declares `int` in `Cotizacion` and `float` in `Titulo`, faithfully following the corpus. But the walker treats the two directions very differently, and only one of them is safe.

**Measured:** `[VERIFIED: measured in-session]`

| Declared | Wire | Result | Divergence |
|---|---|---|---|
| `int` (`Cotizacion`) | `7` | `7` | none |
| `int` (`Cotizacion`) | `7.0` | **`0`** | **`type` WARNING** |
| `float` (`Titulo`) | `7.0` | `7.0` | none |
| `float` (`Titulo`) | `7` | `7.0` | **none — silent widening** |

**Why it happens:** `walk_field`'s float branch accepts `int | float` and coerces (`_decode.py:517-522`); the int branch accepts only `int`. So `float` is lenient by construction and `int` is strict.

**Consequence:** if IOL ever serializes `cantidadOperaciones` with a decimal point in the quote/historical endpoints, `Cotizacion.cantidadOperaciones` **substitutes `0`** and reports a divergence. `Titulo` would absorb the same drift silently. D-04 is still the right call (it follows the evidence, and the strict leg is where you *want* strictness), but the asymmetry should be documented in the model docstring and flagged for the Phase 33 census.

**Warning sign:** a Phase 33 `type` divergence at `Cotizacion.cantidadOperaciones` — that is this pitfall firing, not a defect in the model.

### Pitfall 5 — `to_dict()` projects wire drift *away*; the snapshot loses power the walker gains

**What goes wrong:** D-08 acknowledges the round-trip is lossy. The measured shape of that loss is sharper than "some keys disappear": `schema_of(model.to_dict())` **always** reproduces the *declared* shape, so a real element-level drift becomes **invisible in the schema snapshot** even though the walker reports it.

**Measured** — `puntas` element with a missing key and an extra key: `[VERIFIED: measured in-session]`

```
wire:   [{"precioCompra": 3.0, "extraKey": 1}]
schema_of(to_dict()) -> [{"cantidadCompra":"float","cantidadVenta":"float",
                          "precioCompra":"float","precioVenta":"float"}]   ← MATCHES baseline
divergence records   -> .puntas[].extraKey        extra
                        .puntas[].cantidadCompra  missing
                        .puntas[].cantidadVenta   missing
                        .puntas[].precioVenta     missing
```

The snapshot says "no drift"; the walker says "four divergences". Both are running; only one still sees the truth.

**Why it happens:** `asdict` serializes the *model*, and the model is by definition the declared shape. Any wire key the model does not declare cannot survive the round trip.

**How to avoid:** do not try to fix it — this is the intended trade and D-08 accepts it. Instead **record the carry-forward**: after Phase 30, for iol's modeled endpoints, the authoritative drift signal is the **divergence census**, not the schema-snapshot diff. Phase 33 must read the census for iol. A Phase 33 run that finds "no schema drift" and stops there would be reading an instrument that this phase deliberately blunted.

### Pitfall 6 — sync/async split across commits

**What goes wrong:** the 16 signatures are 8 sync + 8 async. Landing `client.py` without `aio.py` leaves `aio` returning `dict[str, Any]` from a `_core` parser that now returns a model — mypy catches it, but only if both are typechecked in the same run.

**Why it happens:** CLAUDE.md names sync/async duplication as known debt; the natural task split is per-file.

**How to avoid:** treat the 16 signatures as one atomic unit (CLAUDE.md: *"cualquier fix de lógica debe espejarse en `client.py` y `aio.py`"*). The parity probe at `main_iol.py:918-919` is the runtime backstop — but see § The `schema_of` Blast Radius: it is **vacuous** unless `to_dict()` lands too.

### Pitfall 7 — `slots=True` rebuilds the class, breaking zero-arg `super()`

**What goes wrong:** `@dataclass(slots=True)` **replaces** the class object. A zero-arg `super()` inside a method captures the pre-slots class in its `__class__` cell and raises `TypeError: obj must be an instance or subtype of type`.

**Why it happens:** invisible until someone adds a `from_api` override.

**How to avoid:** D-01's minimal `SafeModel` has **no overrides**, so Phase 30 does not hit this — but if any override is added, use the two-arg form. In-repo precedent with the diagnosis written at the site it constrains: `market_data_client/models.py:600-605` → `return super(Symbol, cls).from_api(payload)` `[VERIFIED: read]`. Codified as a shared pattern in `29-PATTERNS.md:700-710`.

### Pitfall 8 — forward references and `get_type_hints` resolution

**What goes wrong:** `from __future__ import annotations` is mandatory repo-wide, so every annotation is a string that `_decode.hints_for` re-evaluates via `get_type_hints` (`_decode.py:399-407`). `Cotizacion.puntas: list[Punta] | None` is resolved from the **module globals at first decode**, not at class-definition time.

**Why it happens:** it looks like a definition-order problem and is not — resolution is deferred to the first `from_api` call, by which time both classes exist.

**How to avoid:** it works in any order (`[VERIFIED: measured — all four models constructed with zero errors]`), but declare `Punta` **first** anyway: it matches the higyrus file's ordering, it reads correctly top-to-bottom, and it removes the question. The real hazard is different: **do not call `hints_for` at import time**, and do not define models inside a function — `get_type_hints` resolves against module globals and would fail on a locally-scoped `Punta`.

### Pitfall 9 — partially-mocked payloads now emit divergence records

**What goes wrong:** almost every existing mock is a 1-2 key payload (`{"ultimoPrecio": 1234.5}`). Decoded as a 20-field `Cotizacion`, that emits ~19 `missing` WARNINGs per call on the `iol_client` logger.

**Why it happens:** the mocks predate the models by design; they were only ever asserting transport behavior.

**How to avoid:** confirm this is **harmless** before spending effort on it — it is:
- `strict_decode` defaults to `False` (`_state.py:101`) and **no** iol test enables it for the client surface `[VERIFIED: grep]`, so nothing raises.
- `main_iol.py` does **not** set `strict_decode` anywhere `[VERIFIED: grep across all main_*.py]` — strict driver runs are a **Phase 33** deliverable. Phase 30 must **not** enable strict mode; doing so would fail the live run on the first missing key.
- `test_logging.py` builds synthetic `LogRecord`s and never decodes `[VERIFIED: read]`.

The one thing to check per test: if any test asserts on caplog record **counts** for the `iol_client` logger, the new records will break it. None do today.

## Code Examples

### Migrating the driver's 2 real attribute sites (D-07)

```python
# main_iol.py:316 and :395 — BEFORE
ultimo = quote.get("ultimoPrecio")
if isinstance(ultimo, int | float) and not (_PRICE_MIN < float(ultimo) < _PRICE_MAX):

# AFTER — the typed access TYP-01 exists to deliver
ultimo = quote.ultimoPrecio
if not (_PRICE_MIN < ultimo < _PRICE_MAX):
```

Note the `isinstance` guard becomes **dead code**: `ultimoPrecio` is declared `float`, and the walker guarantees a `float` reaches the attribute (typed-zero on divergence). Removing it is correct and is the visible payoff of the phase. Keep the `None` guard on `quote` itself — the probe still passes `quote: Cotizacion | None`.

### Applying `to_dict()` at the harness boundary (D-07/D-08)

```python
# main_iol.py:1066 — BEFORE
observed = schema_of(quote)
# AFTER
observed = schema_of(quote.to_dict())

# main_iol.py:1102 — BEFORE
observed_row = schema_of(historical[0])
# AFTER
observed_row = schema_of(historical[0].to_dict())

# main_iol.py:918-919 (parity probe) — the payloads arrive as opaque `Any`,
# so normalize at the boundary rather than at each call site:
def _as_wire(value: Any) -> Any:
    """Harness adapter: project a model (or list of models) back to wire dicts."""
    if isinstance(value, list):
        return [_as_wire(v) for v in value]
    return value.to_dict() if hasattr(value, "to_dict") else value

schema_sync = schema_of(_as_wire(sync_data))
schema_async = schema_of(_as_wire(async_data))
```

`by_type_envelope` must **not** be routed through this adapter — it is already a raw dict (`main_iol.py:995`), and `_as_wire` correctly passes it through untouched.

### Probe annotations to update (`main_iol.py`)

`dict[str, Any] | None` → `Cotizacion | None`, `list[dict[str, Any]] | None` → `list[Cotizacion] | None`, `Any` → `list[Instrumento] | None` at: `:256`, `:340`, `:402`, `:482`, `:682`, `:804`, `:889-896`, `:953-956`, `:1203-1206`, `:1536-1542`. `by_type_envelope: dict[str, Any] | None` stays as-is. `main_iol.py` is **not** typechecked by mypy (`files` = `packages/*/src`) but **is** ruff-checked — so these annotations are documentation, and a mistake in them is invisible to CI. Review them by hand.

## State of the Art

| Old approach | Current approach | When changed | Impact |
|---|---|---|---|
| `SafeModel.from_api` with a local `_coerce` substituting silently | `_decode.walk_model`, verbatim across 5 copies, emitting a structured record per substitution | Phase 29 (2026-08-19) | `models.py` may contain **no** coercion logic; `from_api` is a 3-line delegation. |
| Two decode engines (msgspec + walker) under consideration | **stdlib-only, one engine** | `29-DLOCK-MSGSPEC.md`, signed 2026-08-19 | Closed. The 6 wheels stay a 100% pure-Python closure; `uv.lock` untouched. |
| `Literal` as a candidate for RESPONSE fields | RESPONSE fields **never** closed as `Literal` in v1.6 | `29-DLOCK-RESPONSE-LITERAL.md`, signed 2026-08-18 | `mercado`/`plazo`/`moneda`/`tendencia` stay `str`. `literal_enforced=False` is not a tunable. |
| `verification/` as the drift-detection gate | `verification/` **has never run in CI** — `ci.yml` passes an explicit package path that overrides `testpaths` | discovered Phase 29 (`29-09`) | The surface snapshot and schema baselines are **local-only** gates. Phase 30 must regenerate the snapshot deliberately; CI will not catch it. Phase 32 fixes the CI gap. |

**Deprecated/outdated:**
- The `{"instrumentos": …}` envelope for `get_instruments` — contradicted by the live capture, which shows a top-level list. Surviving only in 16 test mocks (D-06).
- `packages/iol-client/README.md` §Uso — documents `IOLClient(token=...)` and `get_portfolio()`, **neither of which exists** in `src/` `[VERIFIED: read README + grep src/]`. D-12 corrects it.

## Validation Architecture

### Test Framework

| Property | Value |
|---|---|
| Framework | pytest >=8.3 + pytest-asyncio >=0.24 (`asyncio_mode = "auto"`) + pytest-httpx >=0.34 |
| Config file | root `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest packages/iol-client -q` |
| Full suite command | `uv run pytest packages/iol-client && uv run mypy && uv run mypy packages/iol-client/tests && uv run ruff check packages/iol-client && uv run ruff format --check packages/iol-client` |
| Baseline | **205 passed** `[VERIFIED: measured]` |

### Phase Requirements → Test Map

| Req | Behavior | Test type | Automated command | File exists? |
|---|---|---|---|---|
| TYP-01 | 4 models decode the 4 live schemas with zero divergences | unit | `pytest packages/iol-client/tests/test_models.py -x` | ❌ Wave 0 |
| TYP-01 | `to_dict()` round-trips to the 3 committed JSON baselines byte-identically | integration | `pytest packages/iol-client/tests/test_models.py -k roundtrip -x` | ❌ Wave 0 |
| TYP-01 | `puntas` resolves across all 3 observed forms (`[]`, object, `null`) | unit | `pytest packages/iol-client/tests/test_models.py -k puntas -x` | ❌ Wave 0 |
| TYP-01 | 16 signatures return models; zero `Any`/`dict[str, Any]` | static | `uv run mypy` | ✅ (config) |
| TYP-01 | attribute typo fails typecheck (RED, non-vacuous both ways) | static+unit | `uv run mypy packages/iol-client/tests && pytest packages/iol-client/tests/test_typed_surface_red.py -x` | ❌ Wave 0 |
| TYP-01 | 4 parsers return models and own their decode scope | unit | `pytest packages/iol-client/tests/test_core.py -x` | ✅ (rewrite) |
| TYP-01 | `get_instruments` non-list raises, does not degrade to `[]` | unit | `pytest packages/iol-client/tests/test_core.py -k instruments -x` | ❌ Wave 0 |
| TYP-01 | sync/async return identical model types | unit | `pytest packages/iol-client/tests/test_async_client.py -x` | ✅ (migrate) |
| TYP-01 | surface snapshot matches after regen | golden | `uv run pytest verification/test_public_surface.py -k iol` | ✅ (regen) |
| TYP-01 | `uv.lock` unchanged | static | `git diff --exit-code uv.lock` | ✅ |

### Sampling rate

- **Per task commit:** `uv run pytest packages/iol-client -q`
- **Per wave merge:** full suite command above (mypy src + mypy tests + ruff + format)
- **Phase gate:** full suite green, **plus** `uv run pytest verification/ -k iol` (does **not** run in CI — must be run locally, D-09)

### Wave 0 gaps

- [ ] `packages/iol-client/tests/test_models.py` — model construction, `puntas` polymorphism, `to_dict()` round-trip vs the 4 committed schemas, `cantidadOperaciones` int/float asymmetry (Pitfall 4)
- [ ] `packages/iol-client/tests/test_typed_surface_red.py` — the RED fixture, in the `pytest.raises` form of Pitfall 1
- [ ] `test_core.py` — add the non-list-raises case for `parse_get_instruments_response`
- [ ] No framework install needed; no `conftest.py` changes needed

## Security Domain

`security_enforcement` is not disabled in `.planning/config.json`, so this section applies. Phase 30 is a **response-shape** change with no auth, transport, mutation or persistence surface.

### Applicable ASVS categories

| ASVS category | Applies | Standard control |
|---|---|---|
| V2 Authentication | **no** | OAuth flow untouched; builders and `login`/`refresh` parsers are out of scope. |
| V3 Session Management | **no** | Token cache (`_token_cache.py`, 0600 + `fcntl.flock`, Phase 14) untouched. |
| V4 Access Control | **no** | Read-only vendor API; no authorization surface in the client. |
| V5 Input Validation | **yes** | The walker is the validation layer. Phase 30's contribution is the shape guard in `parse_get_instruments_response` — it must **raise**, not degrade to `[]` (D-06). |
| V6 Cryptography | **no** | None introduced. |
| V7 Error Handling & Logging | **yes** | Divergence records carry **types and paths, never values** (`exceptions.py:41-43`, Phase 29 T-29-36). `_emit` is wrapped in `contextlib.suppress(Exception)` (lock 9) so reporting can never crash a consumer's handler. |

### Known threat patterns for this stack

| Pattern | STRIDE | Standard mitigation |
|---|---|---|
| Wire payload keys reaching a log line unsanitized | Information disclosure / log injection | Already mitigated in `_decode._safe_key` (lock 11 as amended by CR-04): every character outside a conservative identifier alphabet becomes `?`, blocking a `\n` in a key from forging a log line. **Phase 30 must not add any log line that echoes a wire value.** |
| Account/instrument identifiers in a committed artifact | Information disclosure | `schema_of` is **PII-free by construction** — keys and type names only, never values (`verification/schema.py:1-8`). `to_dict()` output must reach `schema_of` and **never** a findings file or a snapshot directly. |
| Silent shape degradation masking a compromised or changed upstream | Tampering | D-06's raise-don't-degrade guard; the divergence census. |
| Credentials in test fixtures | Information disclosure | The 16 re-mocks touch payloads only. Sentinel tokens in `test_fixture_reaches_production.py` are literals (`"SYNC-sentinel-iol"`), not real credentials — leave them unchanged. |

## Environment Availability

| Dependency | Required by | Available | Version | Fallback |
|---|---|---|---|---|
| Python | everything | ✓ | 3.12.11 (venv active) | 3.13 also in CI matrix |
| uv | workspace | ✓ | 0.9.0 | — |
| pytest / pytest-httpx / pytest-asyncio | test migration | ✓ | 8.3+ / 0.34+ / 0.24+ | — |
| mypy (strict) | the phase deliverable | ✓ | 1.13+ | — |
| ruff | lint + format | ✓ | 0.7+ | — |
| Live IOL API credentials | **not required** | ✗ | — | **Not needed.** The four schemas were captured 2026-06-06 and are on disk; live re-verification is Phase 33. |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none.

**Operational note:** STATE.md carries a stale blocker — *"El `.venv/` del repo apuntaba a un intérprete inexistente"*. **Resolved**: the venv is healthy; `uv run pytest packages/iol-client` executed 205 tests successfully in this session `[VERIFIED: measured]`. That blocker can be closed.

## Assumptions Log

| # | Claim | Section | Risk if wrong |
|---|---|---|---|
| A1 | `Titulo.fechaVencimiento`, `precioEjercicio` and `tipoOpcion` are typed `str \| None`, `float \| None` and `str \| None`. The corpus records only `NoneType` for all three — the **non-null** type is inferred from the field name, never observed. | Model Field Tables | Low and self-correcting. A wrong non-null type produces a `type` divergence in the Phase 33 census with the correct type named in the record. Choosing `str` for the two date/option fields and `float` for the price field is the conventional reading; flag all three in the model docstring as unobserved so Phase 33 recognizes them. |
| A2 | The `Punta` element inside `Cotizacion.puntas` has the same 4-float shape as `Titulo.puntas`. | D-02 | **Already owned by D-02** and deferred to Phase 33 by decision. If wrong, Phase 33 sees `extra`/`missing` records at `.puntas[].*` — exactly the signal the phase is built to produce. |
| A3 | Nothing outside this repo consumes `iol-client` 0.2.0. | Release / D-11 | Named as an open blocker in STATE.md (*"Se desconoce si algo fuera de este repo consume iol-client 0.2.0"*). **Unresolved — needs the operator.** If an external consumer exists, the dict→model break needs a transitional consideration beyond the `to_dict()` escape hatch. Does not block planning; does affect the Phase 34 release framing. |
| A4 | `python-dotenv`, `httpx` and `tenacity` versions are unchanged by this phase. | Stack | Very low. Assert via `git diff --exit-code uv.lock`. |

## Open Questions

1. **Does anything outside this repo consume `iol-client` 0.2.0?** (A3)
   - What we know: the break is source-level (dict→model, plus a truthiness flip on `get_quote`); `to_dict()` is the escape hatch and the README callout is the notification; STATE.md flags it as "Relevar antes de la Phase 30".
   - What's unclear: whether any external consumer exists at all.
   - Recommendation: a single operator question during planning. Do **not** block on it — every mitigation D-11/D-12 specifies is already the right answer under either outcome.

2. **Should the `isinstance(ultimo, int | float)` guard at `main_iol.py:317` be removed or kept?**
   - What we know: it becomes provably dead — `ultimoPrecio` is declared `float` and the walker guarantees a `float` reaches the attribute.
   - What's unclear: whether the driver's defensive style prefers keeping dead guards.
   - Recommendation: **remove it.** It is the most legible single demonstration that the phase delivered its guarantee, and leaving it implies the type is not trusted.

3. **Where should the `DecodePolicy` re-ratification be recorded?** (Pitfall 2)
   - What we know: Phase 29 requires the confirmation be *recorded*, not merely made.
   - What's unclear: artifact vs. module docstring.
   - Recommendation: the `models.py` module docstring (it travels with the code the decision constrains and survives phase-artifact archival), cross-referenced from the phase SUMMARY.

## Sources

### Primary (HIGH confidence — measured or read in this session)
- Working tree, executed: walker × 4 model shapes × 4 captured schemas → 0 divergences; `schema_of(to_dict())` == committed baseline for all affected files
- Working tree, executed: RED fixture under `mypy` (both directions) and `pytest` (both forms)
- Working tree, executed: `uv run pytest packages/iol-client -q` → 205 passed
- `.planning/verification/schemas/iol-client/*.json` — the 4 live captures (2026-06-06)
- `packages/iol-client/src/iol_client/_decode.py` — POLICY :140, `_response_parser` :312, `hints_for` :399, `walk_field` :415, Optional branch :433-442, nested-model branch :475-490, float branch :517-522, `walk_model` :541
- `packages/higyrus-client/src/higyrus_client/models.py:41-54`; `higyrus_client/_core.py:457-500`
- `packages/iol-client/src/iol_client/_core.py:112-128, 234-360`; `client.py`; `aio.py`; `exceptions.py:13, 27-60`; `__init__.py:55-75`
- `main_iol.py:316, 395, 885-950, 976-1062, 1145-1197, 1200-1244`; `verification/schema.py`; `verification/regen_snapshots.py`; `verification/test_public_surface.py:46-51`
- `pyproject.toml:53-97, 138-172`; `.github/workflows/ci.yml:75-120`
- `.planning/phases/29-decoder-observable/29-SEMANTICS-MATRIX.md:104-148`; `29-PATTERNS.md:700-726`
- `packages/market-data-client/src/market_data_client/models.py:155-180, 590-605`

### Secondary (MEDIUM confidence)
- `docs.python.org/3/library/dataclasses.html` — `asdict` recursion + `copy.deepcopy` semantics; corroborated by in-session measurement
- `.planning/STATE.md`, `.planning/REQUIREMENTS.md`, `CLAUDE.md`

### Tertiary (LOW confidence)
- None. No claim in this document rests on an unverified web search, and no external package was recommended.

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — zero new dependencies; every symbol is stdlib or already locked in the workspace.
- Model shapes: **HIGH** — derived mechanically from the live captures and validated by execution against the walker (0 divergences, exact round-trip). The three unobserved non-null types in `Titulo` are logged as A1.
- Architecture / parser wiring: **HIGH** — import-linter contracts, the `_response_parser` contract and the `IOLAPIError` signature difference all read directly from source.
- Pitfalls: **HIGH** — Pitfalls 1, 4, 5 and the D-10 mechanics were reproduced by execution; 2, 3, 7, 8, 9 by direct source and artifact reads.
- Blast-radius inventories: **HIGH** — enumerated by grep, with the four non-mechanical assert sites identified individually.
- External-consumer impact: **LOW** — A3 is unresolved and needs the operator.

**Research date:** 2026-08-19
**Valid until:** 2026-09-18 (30 days — the domain is a frozen in-tree stack; the only external input is the 2026-06-06 wire capture, which Phase 33 refreshes)
