# Phase 38: `iol-client` + auditoría de higyrus/ámbito/wallets - Research

**Researched:** 2026-08-29
**Domain:** Null Object retyping of two `puntas` fields + AST-gate predicate widening + static census of three near-clean packages (internal codebase archaeology — zero external dependencies)
**Confidence:** HIGH (every claim below was executed or read against the working tree at `HEAD = cf79e65`)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### iol `puntas` — shape + mirroring (NOBJ-IOL-01)

- **D-01:** `Cotizacion.puntas: list[Punta]` y `Titulo.puntas: Punta` quedan declarados
  **REQUIRED, sin default a nivel dataclass** (ni `field(default_factory=list)` ni
  `field(default_factory=Punta.empty)`). El walker (`_decode.py:447-495`, política NOBJ-02 de
  Phase 35) ya colapsa `null`/ausente a `[]`/instancia vacía **sin** emitir divergencia para
  campos no-opcionales de tipo lista/modelo — el "default `[]`" de SC-1 es ese comportamiento
  del walker, no un default de Python. Un default de dataclass es además **mecánicamente
  imposible** sin reordenar campos: `Cotizacion.puntas` es el campo 15/20 seguido de 4 campos
  sin default (`tendencia`, `ultimoPrecio`, `variacion`, `volumenNominal`); `Titulo.puntas` es
  13/20 seguido de 6 — reordenar cambiaría la firma posicional de `__init__` registrada en
  `verification/snapshots/iol-client-surface.txt:11,21`. Precedente exacto: Phase 36 D-04 hizo
  lo mismo con `MarketDataSnapshot.entries`/`market_data` (sin default de dataclass, sólo el
  walker).
- **D-02:** **Nada que mirrorear** en `client.py`/`aio.py`. Ambas superficies llaman a los
  mismos parsers compartidos de `_core.py` (`_core.parse_get_quote_response`, etc. —
  `client.py:528,548,557,572` / `aio.py:547,563,569,580`), que a su vez llaman
  `Cotizacion.from_api`/`Titulo.from_api`. El cambio queda confinado a `models.py:213,301` +
  docstrings. No editar `client.py`/`aio.py`/`_core.py`/`_decode.py` para "satisfacer D-NO-06" —
  eso duplicaría lógica de decode y reintroduciría el drift que `surface_parity.py` existe para
  prevenir.
- **D-03:** Cero clases nuevas → cero edits a `test_null_object.py`, incluido **sin** bump del
  roster floor (`>= 4` en `test_null_object.py:226`, iol ya ships exactamente 4 clases:
  `Punta`, `Cotizacion`, `Instrumento`, `Titulo`). El orden de dispatch de `_perturb` tampoco se
  ve afectado — `apertura: float` es el primer campo de ambas clases y dispara la rama
  `int | float` antes de llegar a la rama de modelo anidado.

#### Migración de tests existentes

- **D-04:** 6 aserciones rompen en runtime y requieren migración semántica:
  `test_models.py:209` (fila histórica), `:229` (dict vacío), `:235` (`from_api(None)`), `:248`
  (`test_puntas_nula_queda_nula`), `:412` (Titulo dict vacío), `:441`
  (`test_titulo_puntas_nula_no_emite_registro`). 2 aserciones quedan tautológicamente verdes sin
  cambio requerido (`:264`, `:389` — `is not None` sigue siendo cierto). El test
  `test_puntas_nula_queda_nula` (`:247`) se **renombra** (no solo se re-asertea) — el nombre
  codifica la semántica retirada. `test_decode.py:861-870` no requiere cambio (fixture local
  `puntas: list[_Leaf]` ya es non-Optional).
- **D-05:** Los dos tests "no emite registro" (`:198-210`, `:436-441`) mantienen su aserción
  `_divergences(caplog) == []` pero **sí requieren reescritura de docstring**: hoy el cero viene
  de la rama `Union`/Optional temprana de `_decode.py:438-441`; tras el cambio viene de la rama
  de colapso NOBJ-02 (`:447-495`). Las docstrings actuales citan verbatim la rama vieja
  (`:201` "D-03: la rama Optional del walker devuelve `None` sin emitir registro",
  `:437` similar) — dejarlas sería una afirmación de procedencia falsa sobre una rama que ya no
  ejecuta (misma clase de defecto que Phase 36 CR-02).
- **D-06:** Idioma de reemplazo, siguiendo Phase 36 D-07 literal: `quote.puntas == []` para
  `Cotizacion`; `bool(titulo.puntas) is False` / `titulo.puntas == Punta.empty()` para `Titulo`
  (no `not titulo.puntas` — la equivalencia contra `empty()` pinea la identidad del Null Object,
  no solo el predicado compuesto).

#### Censo de higyrus / ámbito / wallets (NOBJ-AUD-01)

- **D-07:** El censo es un **artefacto phase-local** (`38-CENSUS.md` bajo el directorio de esta
  fase), siguiendo la forma de `.planning/phases/35-.../35-RETIRED-TRIPLES.md` (tabla con columna
  de disposición + sección de método/límites + ceros declarados explícitamente por enumeración).
  **No** es una entrada en `.planning/verification/<pkg>-findings.md` — esos ledgers son
  auto-generados por el harness de verificación en vivo entre marcadores
  `<!-- BEGIN AUTO-GENERATED -->`/`<!-- END AUTO-GENERATED -->` con schema fijo de corrida real
  (ID/Class/Surface/Status); un censo estático de anotaciones no tiene contexto de corrida ni
  ciclo de vida OPEN→FIXED y corrompería ese formato.
- **D-08:** El censo enumera la **población candidata completa** (todo campo modelo/lista/mapping
  y todo retorno público, tenga o no violación), no solo violaciones — de lo contrario higyrus/
  ámbito/wallets (medido: 0 violaciones en los tres) producen tablas vacías, que SC-4 prohíbe
  explícitamente ("no reportar un verde vacuo"). Medido por introspección `get_type_hints`:
  higyrus = 15 clases / 142 campos / 0 campos modelo-lista-mapping opcionales / 0
  `dict[str, Any]`; ámbito y wallets = 0 clases (`models.py` deliberadamente vacío en ambos,
  decisión documentada de Phase 29/31).
- **D-09:** La mitad de `dict[str, Any]`-en-retornos de SC-2/SC-3 ya está resuelta vía las
  exenciones existentes del gate (`to_dict()` serialize-out ×9, shims legacy `_request` ×2,
  confirmado por corrida real de `tools/check_surface_types.py`: "442 fields scanned, 24
  exempted, 0 violations"). Las filas del censo para estos casos **citan** la tabla de exención
  existente del gate — no proponen fix, no re-abren el D-08 escape hatch documentado en
  `packages/iol-client/README.md:150-161`.

#### README de iol — callout de breaking change (SC-1)

- **D-10:** Formato de sección: `## Unreleased — BREAKING` (precedente de Phase 36 en
  `packages/market-data-client/README.md:7-33`, mismo milestone v1.7) — NO
  `### v0.4.0 — sin publicar todavía` (formato v1.6 de higyrus) porque ese formato asume el
  número de versión que Phase 40 asigna. El callout incluye tabla de migración vieja→nueva con
  las dos filas asimétricas: `Cotizacion.puntas`: `None→[]` (falsy→falsy, sin flip real) y
  `Titulo.puntas`: `None→Punta.empty()` (falsy vía `__bool__`, pero ya no `None` — checks
  `is None` dejan de disparar en silencio). Filas de migración: `titulo.puntas is None` →
  `not titulo.puntas`; `quote.puntas or []` → `quote.puntas`.

#### Gate ratchet — extensión de `check_surface_types.py`

- **D-11:** El predicado de campo del gate se extiende para banear también `Model | None` y
  `list[Model] | None` en campos de dataclass exportada (no solo `dict[str, Any]`/`Any` desnudo
  como hoy) — mismo patrón que la extensión de Phase 37 D-01 (dimensión `ast.AnnAssign`), ahora
  ensanchando el predicado en vez de agregar una dimensión nueva. Se agrega un fixture RED
  espejando `packages/iol-client/tests/test_surface_types_red.py` (D-01d de Phase 37) que prueba
  que el gate detecta un campo `Model | None` reintroducido. SC-3 pasa de ser una medición
  puntual a un **ratchet permanente de CI** — el gap existía porque Phase 37 D-01b restringió el
  predicado deliberadamente a `dict[str, Any]`/`Any` para no reenrojecer los 11 leaves
  `Literal | None` de matriz; el predicado extendido debe distinguir "campo tipado como
  dataclass/lista-de-dataclass" de "campo tipado como alias `Literal`" para no reenrojecer esos
  mismos 11 sitios (`matriz_client/models.py:532,552,553,561,607,619,660,661,662,669`).
  **Decisión explícita del operador** (no auto-resuelta): extender el gate, no dejarlo como
  medición de una sola vez.

#### Contabilidad para Phase 39 — `35-RETIRED-TRIPLES.md`

- **D-12:** Phase 38 le debe a Phase 39 una actualización explícita del ledger
  `35-RETIRED-TRIPLES.md`: la fila que ya nombra los 2 links de iol (`:137-144`) tiene referencias
  de línea desactualizadas (`iol_client/models.py:154,242` → hoy `:213,301`, tras drift de código
  entre Phase 35 y 38) y debe corregirse; y la nota de `:190` (que dice explícitamente que
  Phases 36/37/38 introducen nuevos links no-`Optional` cuyas triples retiradas "no están en este
  ledger y pertenecen a la contabilidad de sus propias fases") implica que esta fase debe dejar
  registrado, en algún artefacto (el propio `38-CENSUS.md` o una nota en `35-RETIRED-TRIPLES.md`),
  cuántas triples retira el cambio de `puntas` — para que Phase 39 pueda separar "desapareció por
  política Null Object" de "desapareció por fix" sin adivinar.

### Claude's Discretion

- Nombre exacto del archivo del censo (`38-CENSUS.md` vs. variante) y organización interna de sus
  secciones — sigue la forma de `35-RETIRED-TRIPLES.md` pero el detalle de layout es libre.
- Redacción exacta de las docstrings reescritas en D-05 y del párrafo de procedencia en `models.py`
  para los dos campos `puntas` — sigue el patrón ya establecido por Phases 36/37, contenido libre.
- Alcance exacto del predicado extendido de D-11 (si distingue por `issubclass(SafeModel)` vs. por
  el roster de clases `Literal` conocidas) — decisión de implementación, no de producto.

> **Research note on the third discretion item:** `issubclass(SafeModel)` is **not viable** inside
> the gate — it is `ast`-only and must never import a package module (F-6, Pitfall 3). The viable
> reading of that discretion is "ClassDef-name set" vs. "known-`Literal`-alias roster"; research
> measured the former and recommends it (F-6).

### Deferred Ideas (OUT OF SCOPE)

- Auditoría completa de retornos públicos de `iol-client` más allá de `puntas` (Fase D completa
  del plan fuente) — explícitamente fuera del alcance angosto de NOBJ-IOL-01 en esta fase; si
  aparecen más violaciones se descubren en el propio censo de auditoría o en Phase 39.
- Bump de versión, changelog callout con número real, tabla de migración publicada — Phase 40
  (`PUB-NOBJ-01`).
- Verificación en vivo del encadenamiento profundo de `puntas` (`titulo.puntas.precioCompra`
  contra la API real) — Phase 39 (LIVE-NOBJ-01); `main_iol.py` no se toca en esta fase.
- Exención o retipado de `CalendarConfig.warnings`/`CalendarConfigPreview.warnings` de
  market-data-client (`list[Any]`) — ya deferido explícitamente por Phase 37, sigue fuera de
  alcance (paquete disjunto).

### Folded Todos

Ninguno — `todo.match-phase 38` no encontró coincidencias (`todo_count: 0`).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|---|---|---|
| **NOBJ-IOL-01** | `Cotizacion.puntas` es `list[Punta]` (nunca `None`) y `Titulo.puntas` es `Punta` Null Object — `titulo.puntas.precioCompra` siempre válido, espejado sync/async (`REQUIREMENTS.md:24`) | F-1 (walker collapse executed: `[]` / `Punta.empty()`, zero divergences), F-2 (no mirroring needed — both surfaces delegate to `_core.py`), F-3 (**the 7th breaking assertion** CONTEXT missed), F-4 (all 6 enumerated line numbers exact; `warn_unreachable` off), F-5 (`_perturb` docstring correction), F-7 (field positions 16/20 and 14/20 — 1-based; the "N no-default fields after" argument holds), F-11 (README template + placement), F-12 (snapshot regen: exactly 2 line diff) |
| **NOBJ-AUD-01** | higyrus/ámbito/wallets auditados: cero campos modelo/lista `\| None` y cero `dict[str, Any]` en campos de modelos públicos, verificable por gate/grep (hojas escalares `T \| None` permitidas por D-NO-03) (`REQUIREMENTS.md:33`) | F-6 (D-11 predicate implemented and measured: **2 hits, both iol; 0 collateral on matriz's `Literal` leaves**), F-8 (census numbers confirmed: higyrus 15/142/0/0; ámbito 0; wallets 0 + stub qualification), F-9 (**correction to D-09's exemption taxonomy** + the exact SC-3 closing greps and their current output), F-10 (the accounting `35-RETIRED-TRIPLES.md` owes Phase 39: **2 field rows added, 0 triples retired**) |

</phase_requirements>

## Summary

CONTEXT.md was written from static analysis in assumptions mode. This research **executed** its
load-bearing claims. The headline: **all twelve decisions hold**, with **one material omission**,
**three numeric corrections**, and **one scope collision** that would have bitten a planner turning
them into file-level tasks.

The omission is the important one. CONTEXT D-04 enumerates **6** breaking assertions in
`test_models.py`. There is a **7th**, and it is not an assertion about `puntas` at all:
`test_round_trip_reproduce_el_schema_committeado_de_serie_historica` (`test_models.py:353-355`)
compares `schema_of(row.to_dict())` against the committed live capture
`.planning/verification/schemas/iol-client/get-historical-quotes.json`, whose `puntas` entry reads
`"NoneType"`. After the retype, `to_dict()` re-projects `[]` and `schema_of` answers `[]`. Measured,
not suspected — see F-3. The remedy is **not** to edit the capture (it is evidence of a real
2026-06-06 wire read); it is to override that one key in the expected value with a comment naming
the now-documented lossiness of the round-trip.

The corrections: D-01's "campo 15/20" and "13/20" are **0-based indices** (`puntas` is the 16th and
14th field respectively) — the "4 and 6 no-default fields after it" half is exactly right, and it is
the half the mechanical-impossibility argument rests on. D-09's "shims legacy `_request` ×2" does
not match the gate's measured taxonomy: the gate reports `private-helper 1`, and that single hit is
`matriz-client Client._matriz_legacy_request`; every *module-level* `_request` in the workspace
never enters the candidate set at all (unreachable from any `__all__`), so it is **out of scope by
resolution, not exempted**. D-03's "cero edits a `test_null_object.py`" is right about behaviour and
wrong about prose: `_perturb`'s docstring (`test_null_object.py:113-118`) states verbatim that
*"``Titulo.puntas`` is ``Punta | None``"* — a factual claim this phase falsifies, and exactly the
false-provenance defect class D-05 exists to prevent.

The scope collision: D-11 widens the gate's **field** dimension, whose RED fixture lives in
`packages/matriz-client/tests/` — a package this phase declares disjoint. CONTEXT resolves it
correctly by naming the *iol* fixture as the mirror target; the planner must not "fix" that by
editing matriz's file.

And the decisive good news, measured rather than reasoned: the D-11 predicate, implemented with a
**ClassDef-name discriminator**, reddens **exactly 2 sites across all 6 packages** — the two fields
this phase is fixing — and spares all 11 matriz `Literal | None` leaves, because every one of those
alias names is bound by a module-level `Assign` in `types.py` and none is a `ClassDef`. The ratchet
lands with zero collateral. See F-6.

**Primary recommendation:** Plan five work units in this order — (1) migrate the 7 breaking test
assertions + 3 stale docstrings **first** (tdd_mode is on; these are the RED tests), (2) flip the two
annotations in `models.py` + rewrite the two class docstrings, (3) regenerate
`verification/snapshots/iol-client-surface.txt` in the same commit, (4) widen
`_adjudicate_field` with a ClassDef-name discriminator plus a new RED test in the **iol** fixture,
(5) write `38-CENSUS.md` from the introspection numbers in F-8 and patch `35-RETIRED-TRIPLES.md`
per D-12. Units 1-3 and 4 are independent of each other and can be separate waves; unit 5 depends on
nothing but should cite the post-change grep from F-9.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| `puntas` type declaration | Library — `iol_client/models.py` | — | Annotation is the whole change; the walker already implements the semantics (F-1) |
| Null/absent → `[]` / empty-instance collapse | Library — `iol_client/_decode.py` (frozen) | — | NOBJ-02 shipped in Phase 35; **read-only** in this phase |
| Sync/async mirroring of the change | None — no tier | — | Both surfaces delegate to `_core.py` parsers; D-02 confirmed (F-2) |
| Breaking-change disclosure | Docs — `packages/iol-client/README.md` | — | Version bump is Phase 40; only the `## Unreleased — BREAKING` callout lands here |
| Contract ratchet on future regressions | CI tooling — `tools/check_surface_types.py` (lint job) | Test — `packages/iol-client/tests/test_surface_types_red.py` | Cross-package gate; per-package matrix leg cannot host it (gate docstring, "WHY THIS IS A `tools/` SCRIPT") |
| Public-surface freeze | `verification/snapshots/iol-client-surface.txt` | `verification/test_public_surface.py` | Positional `__init__` signature is the frozen artifact |
| Census / accounting | Planning artifacts — `38-CENSUS.md`, `35-RETIRED-TRIPLES.md` | — | D-07 forbids writing into the auto-generated `.planning/verification/<pkg>-findings.md` ledgers |

## Project Constraints (from CLAUDE.md)

- **Python 3.12+, uv, httpx, pytest + pytest-httpx, ruff, mypy strict** — every edit must keep the
  existing CI green. Verified toolchain: `uv 0.11.3`, active venv `CPython 3.12.13`.
- **Dual sync/async**: *"cualquier fix de lógica debe espejarse en `client.py` y `aio.py` del mismo
  paquete."* This phase changes **no logic** (F-2), so the obligation is discharged by
  demonstration, not by a mirrored edit. Writing a mirrored edit anyway would duplicate decode logic
  and reintroduce the drift `tools/surface_parity.py` exists to prevent (CONTEXT D-02).
- **Sin código compartido entre paquetes** (DT-03) — no cross-package import may be introduced. The
  gate is `tools/`-level and already package-agnostic (roster read from disk).
- **`from __future__ import annotations` mandatory** in every module — already present in every file
  this phase touches; this is *why* the gate must reason over `ast` strings and `get_type_hints`
  must re-evaluate (`_decode.hints_for` docstring).
- **Wire-verbatim camelCase field names** — `puntas` keeps its name; only its annotation changes.
- **Nunca commitear `.env` ni exponer credenciales** — this phase touches no credential path.
- **GSD workflow enforcement** — edits must arrive through `/gsd-execute-phase`.

## Findings

### F-1 — The walker's NOBJ-02 collapse behaves exactly as D-01 claims `[VERIFIED: executed]`

Executed against the real `iol_client` package with two synthetic `SafeModel` subclasses mirroring
the post-change shapes (`puntas: list[Punta]` and `puntas: Punta`, both non-Optional):

| Payload for `puntas` | `list[Punta]` result | `Punta` result | divergence records |
|---|---|---|---|
| `null` | `[]` | `Punta(0.0, 0.0, 0.0, 0.0)` | **none** |
| key absent | `[]` | `Punta(0.0, 0.0, 0.0, 0.0)` | **none** |
| populated | `[Punta(1.0, 2.0, 3.0, 4.0)]` | n/a | **none** |
| `from_api(None)` (whole payload) | `[]` | `Punta(0.0, …)` | **1 record**, and it is the outer model's terminal `non_dict` (lock 8 / D-03a), *not* a `puntas` record |

Also verified in the same run: `bool(t.puntas) is False` and `t.puntas == Punta.empty()` both hold —
**D-06's replacement idiom is executable as written**.

Branch provenance, read from the shipped source:
- `list[Punta]` + `None` → `_decode.py:448-452`. The `sink(...)` call at `:451` is guarded by
  `if value is not None`, so a `None` returns `[]` silently.
- `Punta` + `None` → `_decode.py:504-505`, the NOBJ-02 arm, which builds the empty instance through
  `SILENT_SINK`.
- Absent key → `walk_model` does `data.get(f.name)` (`_decode.py:607`) → `None` → same two branches.

**Corollary the planner must not miss:** `_decode.py` is byte-frozen and guarded by
`tools/check_decode_intactness.py`. No task in this phase may touch it.

### F-2 — D-02 confirmed: nothing to mirror `[VERIFIED: read]`

`client.py` and `aio.py` both call the shared `_core.py` parsers, which call
`Cotizacion.from_api` / `Titulo.from_api`. Neither surface contains a `puntas` reference — a
repo-wide grep for `puntas` returns hits in exactly five files: `models.py`, `test_models.py`,
`test_decode.py` (a local `_Leaf` fixture, already non-Optional — unaffected, as CONTEXT states),
and the two snapshot lines. `client.py`, `aio.py`, `_core.py` and `main_iol.py` contain **zero**
occurrences.

### F-3 — **CONTEXT omission**: a 7th assertion breaks, and it is a round-trip, not a `puntas` check `[VERIFIED: executed]`

`packages/iol-client/tests/test_models.py:353-355`:

```python
def test_round_trip_reproduce_el_schema_committeado_de_serie_historica() -> None:
    row = Cotizacion.from_api(_HISTORICAL_ROW)
    assert schema_of(row.to_dict()) == _committed_schema("get-historical-quotes")[0]
```

`_HISTORICAL_ROW["puntas"] is None`. The committed capture records `"puntas": "NoneType"`. Measured
post-change value of `schema_of(row.to_dict())["puntas"]`: `[]`. **This test fails.**

Why it is not a `puntas`-assertion and therefore escaped the CONTEXT enumeration: the string
`puntas` does not appear on any of its three lines.

**Do not edit the capture file.** `.planning/verification/schemas/iol-client/get-historical-quotes.json`
is a 2026-06-06 live wire capture and the corpus of record; rewriting it to `[]` would falsify
evidence. The correct migration is to override the single key in the *expected* value and say why —
the README already documents `to_dict()` as *"reproduce la forma **declarada**, no la recibida"*
(`README.md:157-161`), and higyrus's `models.py:38-41` states the same caveat as a Phase 30 CR-01
pin. This phase makes that documented lossiness observable for the first time.

The two sibling round-trips are **unaffected**, verified against the committed schemas:
- `get-quote`: capture says `"puntas": []`; `_QUOTE_PAYLOAD["puntas"] = []` → still `[]`. Green.
- `get-instruments-by-type`: capture says `"puntas": {cantidadCompra: float, …}`; `_TITULO_ROW`
  carries a populated dict → still that dict. Green.

### F-4 — The 6 CONTEXT-enumerated line numbers are all exact `[VERIFIED: grep]`

| Line | Current assertion | Post-change truth |
|---|---|---|
| `209` | `assert row.puntas is None` | breaks → `== []` |
| `229` | `assert quote.puntas is None` | breaks → `== []` |
| `235` | `assert quote.puntas is None` | breaks → `== []` |
| `248` | `Cotizacion.from_api({**_QUOTE_PAYLOAD, "puntas": None}).puntas is None` | breaks → `== []`; the test **name** `test_puntas_nula_queda_nula` (`:247`) also encodes retired semantics and must be renamed |
| `412` | `assert titulo.puntas is None` | breaks → `bool(...) is False` / `== Punta.empty()` |
| `441` | `assert titulo.puntas is None` | breaks → same |

The two "stay tautologically green" claims also check out: `:264` and `:389`
(`assert x.puntas is not None`) remain true. **They are also mypy-safe**: `warn_unreachable` is
**not** set in `[tool.mypy]` (`pyproject.toml:83-97`), so a redundant `is not None` on a
non-Optional does not error. Leaving them is legal; the planner may still prefer to drop `:264` and
`:389` as dead narrowing, but that is hygiene, not a requirement.

### F-5 — **CONTEXT correction**: `test_null_object.py` needs a docstring edit after all `[VERIFIED: read]`

`packages/iol-client/tests/test_null_object.py:113-118`, inside `_perturb`'s docstring:

> *"No shipped iol class is that shape today — ``Titulo.puntas`` is ``Punta | None`` and answers on
> the first branch — but the branch is kept so the helper stays the same helper across the six
> paquetes and survives Phase 38 turning ``puntas`` non-Optional."*

D-03's **behavioural** claim is correct and re-verified: `apertura: float` is the first declared
field of both `Cotizacion` and `Titulo`, so `_perturb` dispatches on the `int | float` branch and
never reaches the `cur is None` or nested-`SafeModel` branches for these classes. Dispatch does not
move.

But the sentence above becomes **false prose about the code it annotates** — the same class of
defect as Phase 36 CR-02, which D-05 cites by name. The roster floor (`>= 4`, `:226`) genuinely
needs no bump. Plan a one-sentence docstring correction, not a logic change.

Also re-verified: `Titulo.empty()` and `Titulo.from_api(None)` still agree post-change
(`bool(T.from_api(None)) is False`), so `test_every_shipped_model_is_falsy_when_empty` and its
truthy sibling stay green.

### F-6 — D-11's predicate: the ClassDef-name discriminator reddens **exactly 2 sites**, and zero of matriz's 11 `[VERIFIED: executed]`

The gate **never imports a module** — it is stdlib-`ast`-only by design (docstring, "STDLIB-ONLY,
ON PURPOSE"), because `import <pkg>` would run `load_dotenv()` and build HTTP clients at import
time. So `get_type_hints` / `issubclass(SafeModel)` is **not available inside the gate**. The
discriminator must be static.

The static discriminator that works: **is the annotation's base name bound by a `ClassDef` anywhere
in the package's import root?**

- `Punta`, `Cotizacion` → `ast.ClassDef` → model.
- `MarketId`, `SegmentId`, `CFICode`, `Currency`, `OrderType`, `Side`, `TimeInForce`, `OrderStatus`
  → module-level `ast.Assign` in `matriz_client/types.py` (`types.py:35,38,41,44,47,50,81,95`) →
  `Literal` alias, spared.

I implemented this predicate and ran it over all six packages. Result:

```
ambito-financiero-client: exported-classes-with-fields=0  fields=0    OPTIONAL-MODEL-HITS=0
higyrus-client:           exported-classes-with-fields=15 fields=142  OPTIONAL-MODEL-HITS=0
iol-client:               exported-classes-with-fields=4  fields=46   OPTIONAL-MODEL-HITS=2
    ('Cotizacion.puntas', 'list[Punta] | None', 'list[Punta]')
    ('Titulo.puntas',     'Punta | None',       'Punta')
market-data-client:       exported-classes-with-fields=26 fields=140  OPTIONAL-MODEL-HITS=0
matriz-client:            exported-classes-with-fields=21 fields=114  OPTIONAL-MODEL-HITS=0
wallets-client:           exported-classes-with-fields=0  fields=0    OPTIONAL-MODEL-HITS=0
```

`0 + 142 + 46 + 140 + 114 + 0 = 442`, matching the gate's own `442 fields scanned`. The two hits are
precisely the two fields this phase fixes. **After the fix the extended predicate is green with zero
exemptions added.**

Implementation notes for the planner:

1. **A "was there an optional wrapper?" signal is required.** `_strip_optional` is applied
   unconditionally today; the new predicate must distinguish `Punta | None` (redden) from `Punta`
   (spare). Add a sibling that returns `(inner, was_optional)`, or compare `ast.dump` before/after.
   Do **not** change `_strip_optional`'s existing contract — the mapping predicate depends on it.
2. **Build the ClassDef-name set by walking `import_root.rglob("*.py")`**, not by resolving through
   `__all__`. Measured: every *response model* class in all four model-carrying packages is
   exported, so the `__all__` route works today — but the unexported ClassDef roster
   (`RequestSpec`, `TokenStore`, `_SafeModel`, the transports, `DecodePolicy`) shows that an
   internal model *could* be introduced, and resolving through `__all__` would silently spare it.
   The full-tree walk is used only as a **classifier**, never to add candidates, so the gate's
   "resolve from the exported surface outward" design is preserved. State that in the docstring.
3. **Match `list[Model] | None` as well as `Model | None`.** Do not descend into `dict[...]`
   value parameters for this dimension — no optional model-valued mapping exists today, and adding
   it is scope the phase does not own. If the planner wants it, it is a stated addition, not a bug
   fix.
4. **`list[Any] | None` must stay spared.** `packages/matriz-client/tests/test_surface_types_red.py:370`
   (`test_a_list_of_any_field_is_spared_keeping_the_narrow_predicate_narrow`) pins D-01b. `Any` is
   not a `ClassDef`, so the discriminator spares it structurally — but the planner should add an
   explicit RED-side assertion that this remains true.
5. **Exception classes are `ClassDef`s too.** `IOLAPIError | None` on an exported dataclass field
   would redden under this predicate. None exists today. This is arguably correct behaviour; name
   it in the docstring so nobody "discovers" it as a bug.
6. **Where the new RED test goes: the iol fixture.** The field dimension's fixture is matriz's
   (`packages/matriz-client/tests/test_surface_types_red.py`), but matriz-client is out of scope for
   Phase 38. CONTEXT D-11 already names `packages/iol-client/tests/test_surface_types_red.py` as the
   mirror target — follow it. The iol fixture already imports `CheckFailure`, `check_surface_types`
   and `scan_surface_types` and carries the `_write_fake_package` helper (`:65-83`), so a new test
   is a ~20-line addition in the established shape:

   ```python
   def test_an_optional_model_field_is_caught(tmp_path: Path) -> None:
       _write_fake_package(
           tmp_path,
           init_source="from fake_client.client import Thing\n\n__all__ = ['Thing']\n",
           client_source=(
               "class Leaf:\n    pass\n\n\n"
               "class Thing:\n"
               "    link: Leaf | None = None\n"
           ),
       )
       with pytest.raises(CheckFailure, match=r"Thing\.link"):
           check_surface_types(root=tmp_path)
   ```

   Pair it with a **sparing** test that pins the matriz shape without touching matriz:
   `Mode = Literal['a', 'b']` at module level plus `mode: Mode | None = None` on the class →
   `result.violations == ()`.
7. **`_write_fake_package` is duplicated on purpose.** Both RED fixtures carry their own copy;
   matriz's docstring (`:21`) records that factoring it out *"would be this repo's first"* shared
   test helper. Copy, do not extract.

### F-7 — Field ordering: D-01's mechanical-impossibility argument holds; its indices are 0-based `[VERIFIED: read]`

| Class | `puntas` position (1-based) | Fields after it, all no-default | Dataclass default possible? |
|---|---|---|---|
| `Cotizacion` | **16** of 20 (CONTEXT says "15/20" — 0-based) | `tendencia`, `ultimoPrecio`, `variacion`, `volumenNominal` → **4** | No |
| `Titulo` | **14** of 20 (CONTEXT says "13/20" — 0-based) | `simbolo`, `tipoOpcion`, `ultimoCierre`, `ultimoPrecio`, `variacionPorcentual`, `volumen` → **6** | No |

The load-bearing half — "followed by N fields with no default" — is exact in both cases, so
`TypeError: non-default argument follows default argument` is guaranteed and reordering is the only
escape. Reordering would move the positional `__init__` signature frozen at
`verification/snapshots/iol-client-surface.txt:11` and `:21`, which is the reason not to.

**Do not "fix" CONTEXT's indices in the plan text as if they were errors** — state the 1-based
position and the after-count, which is what a task needs.

### F-8 — Census numbers for higyrus / ámbito / wallets confirmed `[VERIFIED: executed]`

D-08's introspection numbers are exact:

| Package | Exported classes carrying fields | Fields | Optional model / list-of-model fields | `dict[str, Any]` on model fields | Public domain functions |
|---|---:|---:|---:|---:|---|
| `higyrus-client` | **15** | **142** | **0** | **0** | `get_health → Health`, `get_listado_cuentas → list[Cuenta]`, `get_movimientos → list[Movimiento]`, `get_posicion_valuada → list[PosicionValuada]`, `get_posiciones → list[Posicion]`, `login → str`, `configure → None` |
| `ambito-financiero-client` | **0** | **0** | **0** | **0** | `get_dollar_banco_nacion → float` (scalar leaf), `configure → None` |
| `wallets-client` | **0** | **0** | **0** | **0** | **none** — `__all__` is 4 exception classes + `configure` (`__init__.py:22-28`) |

The 15 higyrus classes, by declaration order in `models.py`: `Health`, `PosicionValuada`, `Parking`,
`Movimiento`, `Posicion`, `DisposicionesGenerales`, `Domicilio`, `PersonaRelacionada`,
`MedioComunicacion`, `CuentaBancaria`, `Agente`, `Operador`, `Sucursal`, `Administrador`, `Cuenta`.
(`SafeModel` is exported too but declares no fields, so it contributes 0 to the 142.)

Both empty `models.py` files are **27 lines of module docstring each**; ámbito's carries 2 `class`
tokens *in prose only*. `35-RETIRED-TRIPLES.md:184-197` already records both absences as
*"absent by enumeration, not by cleanliness"* — the census should cite that paragraph rather than
re-derive it.

**wallets stub condition (SC-4's explicit requirement):** `wallets_client.__all__` contains no
domain function; `__version__ = "0.2.0"`; the package carries the Phase 29 decoder exemption
(`29-WALLETS-EXEMPTION.md`) and has no `_decode.py`. Its 10 passing tests exercise config/exception
plumbing only. Report the green **with** that qualification, per SC-4.

### F-9 — The gate's real exemption taxonomy, and the SC-3 closing grep `[VERIFIED: executed]`

Live gate output at `HEAD = cf79e65`:

```
surface types: 6 packages, 186 `__all__` names, 336 definitions scanned, 442 fields scanned,
13 constant/alias exports, 24 exempted (dunder 13, private-helper 1, serialize-out 9,
ws-catch-all 1), 0 violations
```

**Correction to D-09.** The taxonomy is `dunder 13 / private-helper 1 / serialize-out 9 /
ws-catch-all 1`, not "9 `to_dict()` + 2 legacy `_request`". The single `private-helper` hit is
`matriz-client Client._matriz_legacy_request` (`matriz_client/client.py:496-503`, returns
`dict[str, Any]`, docstring: *"DEPRECATED back-compat wrapper for `main_matriz.py` probes"*). The
**module-level** `_request` functions — `higyrus/client.py:682-684`, `higyrus/aio.py:688-690`,
`iol/client.py:716`, `iol/aio.py:732`, `matriz/client.py:914-919`, `wallets/client.py:61`,
`wallets/aio.py:77`, `ambito/client.py:326` — are **not exemptions**: they are absent from every
`__all__`, so `_resolve_export` never reaches them and they are out of the candidate set entirely.
The gate documents this as "OQ-2 resolution ... subsumed by the underscore rule". Census rows citing
these must say **"out of the gate's candidate set"**, not "exempted".

**SC-3 closing grep — the exact command and its current output.** Run it, report the output verbatim
per SC-3's "no como afirmación":

```bash
grep -nE '^\s+[A-Za-z_][A-Za-z0-9_]*\s*:\s*.*(\| None|Optional\[|Union\[)' packages/*/src/*/models.py \
  | grep -vE ':\s*(str|int|float|bool)\s*\| None'
```

Today (12 lines): the 2 iol `puntas` lines + the 10 matriz `Literal`-alias lines
(`models.py:532,552,553,561,607,619,660,661,662,669`). **After the change: 10 lines, all matriz
`Literal` aliases**, i.e. scalar-set leaves permitted by D-NO-03.

> Note: CONTEXT says "11 leaves". The grep and the D-11 measurement both count **10** distinct
> lines. The 11th in Phase 37's prose is most likely `AccountId.id: str | None` or a second
> occurrence collapsed by dedup. The planner should write **10** and cite the grep, or re-derive
> the 11th and name it explicitly. Either way, do not carry an unsourced count into an SC-3 claim.

Companion grep for the `dict[str, Any]`-on-fields half:

```bash
grep -nE '^\s+[A-Za-z_][A-Za-z0-9_]*\s*:\s*.*dict\[' packages/*/src/*/models.py
```

Current non-local-variable hits: `matriz models.py:629` `tickPriceRanges: dict[str, TickPriceRange]`
(typed), `:902` `report: dict[str, dict[str, InstrumentPositionReport]]` (typed), `:970`
`detailedAccountReports: dict[str, DetailedAccountReport]` (typed), `:456`
`__dataclass_fields__: ClassVar[dict[str, Any]]` (dunder), `:1032` `UnknownFrame.raw`
(the one declared exemption). Everything else the grep returns is a **local variable inside
`to_dict`**, not a field — the census must distinguish these or it will over-report.

### F-10 — `35-RETIRED-TRIPLES.md` (D-12): what to patch, and the number Phase 38 owes Phase 39 `[VERIFIED: read]`

The iol row is the 12th row of the main table, and its `note` cell reads:

> *"`Cotizacion.puntas` and `Titulo.puntas` are declared `Optional` today
> (`iol_client/models.py:154`, `:242`), so they take the walker's `Union` early return at
> `_decode.py:431-435` …"*

The same claim repeats in the prose paragraph **"`iol-client` — the zero is a fact about `Optional`,
not a fact about quality"** (near `:190`), again citing `:154` / `:242` and `_decode.py:431-435`.

**Stale references measured against `HEAD = cf79e65`:**

| Cited | Actual today |
|---|---|
| `iol_client/models.py:154` (`Cotizacion.puntas`) | `:213` |
| `iol_client/models.py:242` (`Titulo.puntas`) | `:301` |
| `_decode.py:431-435` (`Union` early return) | `:440-446` |
| `_decode.py:443-445` (list branch, in the "Why every row's retired kind is `missing`" section) | `:448-452` |
| `_decode.py:482-484` (WR-02 nested-model branch, same section) | `:504-505` |
| `_decode.py:363-367` (`_kind_of`) | unverified — check before citing |

CONTEXT D-12 names only the first two. The other four are the **same** drift in the **same file**;
the planner should decide explicitly whether they are in scope (recommended: yes, one edit, same
commit) rather than leaving a half-corrected ledger.

**The accounting Phase 38 owes Phase 39 (`:190`'s open obligation).** Measured, not estimated:

- **Field rows added to the NOBJ-02 disposition: 2.** `iol-client | Cotizacion | .puntas
  (list[Punta]) | missing` and `iol-client | Titulo | .puntas (Punta) | missing`. The current
  explicit-zero row for iol must be **replaced** by these two, with the zero preserved as history.
- **Triples retired: 0.** Both columns. The floor column is `N/A — not zero` (29-SIZING.md:166:
  iol had no `models.py` at sizing time), and iol's live 33-CENSUS measurement was an inspected
  **0 distinct triples**. A field only retires a triple if that triple was actually being emitted;
  under the *pre*-Phase-38 `Optional` declaration these fields took the `Union` early return and
  emitted nothing, and under the *post*-Phase-38 declaration they take the NOBJ-02 collapse and
  still emit nothing (F-1). **The census number is unchanged, and that invariance is the finding.**
- Therefore Phase 39's middle term stays **higyrus 2, iol 0, market-data 0, matriz 5** (distinct
  triples) / matriz 6 (records) — Phase 38 changes the *roster*, not the *arithmetic*. Write that
  sentence down; a bare `0` re-reads as "iol was already clean", which is the exact misreading the
  existing paragraph was written to prevent.

### F-11 — README placement and template `[VERIFIED: read]`

`packages/market-data-client/README.md:7-33` is the D-10 template. Structure to copy:

1. `## Unreleased — BREAKING` heading, placed **after the intro paragraph and before
   `## Instalación`**.
2. A blockquote naming the last published tag and stating that `main` is not it, with the reason
   (*"el bump breaking coordinado de los seis paquetes lo hace la Fase 40 en una sola pasada"*).
3. A two-column `| Antes (X publicado) | Ahora (`main`, pendiente de bump) |` migration table.
4. A prose paragraph naming the exact runtime consequence of the type change.

For iol the anchor tag is **v0.3.0** (`README.md:112`, the only changelog entry). Insert the new
section at **line 4-5**, immediately after the one-line intro and before `## Instalación` (`:5`).
Do **not** add a `### v0.4.0` heading — D-10 forbids assuming Phase 40's number.

The migration table's two rows are asymmetric, and D-10 is right about why:

| Antes (0.3.0 publicado) | Ahora (`main`, pendiente de bump) |
|---|---|
| `quote.puntas is None` / `quote.puntas or []` | `quote.puntas == []` / `quote.puntas` |
| `titulo.puntas is None` | `not titulo.puntas` (o `titulo.puntas == Punta.empty()`) |

`Cotizacion`: `None → []`, falsy→falsy, no truthiness flip. `Titulo`: `None → Punta.empty()`, still
falsy via `SafeModel.__bool__` (verified in F-1), **but no longer `None`** — every `is None` check
stops firing silently. The existing prose block *"Flip de truthiness — la parte que el typechecker
NO atrapa"* (`README.md:140-149`) is the tone template CONTEXT names; reuse its framing.

### F-12 — Snapshot regeneration `[VERIFIED: read]`

Command: `uv run python verification/regen_snapshots.py`. It rewrites all 4 snapshot files
(`ambito-financiero`, `higyrus`, `iol`, `matriz` — there is **no** wallets or market-data snapshot)
and preserves the 8-line header bit-for-bit. Commit the diff **in the same commit** as the source
change (script docstring, D-11).

The two lines that move, current content:

- `:11` `Cotizacion : class : (…, precioPromedio: 'float', puntas: 'list[Punta] | None', tendencia: 'str', …) -> None`
- `:21` `Titulo : class : (…, precioEjercicio: 'float | None', puntas: 'Punta | None', simbolo: 'str', …) -> None`

Expected post-change diff: exactly two tokens, `'list[Punta] | None'` → `'list[Punta]'` and
`'Punta | None'` → `'Punta'`. **Field order and every other field is unchanged** — that is the
acceptance criterion the planner should write: *"the regenerated snapshot diff is exactly 2 changed
lines, and within them exactly the `puntas` annotation."* Companion assertion:
`verification/test_public_surface.py`.

### F-13 — Baselines, so "verde" is measurable `[VERIFIED: executed]`

| Suite | Baseline at `HEAD = cf79e65` |
|---|---|
| `uv run --package iol-client pytest packages/iol-client -q` | **289 passed** (14.6 s) |
| `uv run --package higyrus-client pytest packages/higyrus-client -q` | **289 passed** (35.7 s) |
| `uv run --package ambito-financiero-client pytest packages/ambito-financiero-client -q` | **208 passed, 1 deselected** (12.5 s) |
| `uv run --package wallets-client pytest packages/wallets-client -q` | **10 passed** (0.02 s) |
| `uv run python tools/check_surface_types.py` | green, `0 violations` |

The 4 gates of v1.6, and where each runs:

| Gate | How it runs |
|---|---|
| `tools/check_decode_intactness.py` | `lint` job step (`ci.yml:55`) |
| `tools/check_uniform_structure.py` | `lint` job step (`ci.yml:60`) |
| `tools/check_surface_types.py` | `lint` job step (`ci.yml:66`) |
| `tools/surface_parity.py` | **not** a lint step — a helper called from six in-package tests, `packages/<pkg>/tests/test_surface_parity.py`, all six of which exist |

SC-4's *"`surface_parity.py` asevera que cada cambio de lógica viajó a las dos superficies"* is
therefore satisfied by the six per-package tests staying green, not by adding a CI step. For iol
specifically the assertion is vacuously-but-correctly satisfied: no logic changed (F-2).

## Standard Stack

No new dependencies. This phase is pure internal refactor + tooling.

### Core (already present, versions from `uv.lock` / active venv)

| Library | Version | Purpose | Why standard |
|---|---|---|---|
| CPython | 3.12.13 (venv) / 3.13 in CI matrix | Runtime | Repo target |
| `uv` | 0.11.3 | Workspace + runner | Repo standard |
| `pytest` | >= 8.3 | Test runner | Repo standard |
| `mypy` | >= 1.13, `strict = true` | The guarantee SC-1 asserts | Repo standard |
| `ruff` | >= 0.7 | Lint + format, line-length 100 | Repo standard |
| stdlib `ast` | — | The **only** parsing tool the gate may use | Gate docstring, "STDLIB-ONLY, ON PURPOSE" (D-12) |

### Alternatives Considered

| Instead of | Could use | Tradeoff |
|---|---|---|
| `ast`-based ClassDef discriminator in the gate | `get_type_hints` + `issubclass(SafeModel)` | **Rejected — non-viable.** The gate must never import a package module; `import <pkg>` runs `load_dotenv()` and constructs HTTP clients at import time. Both sibling gates forbid it by name. |
| Full-tree `ClassDef` walk as classifier | Resolve annotation names through `__all__` | Works today (F-6 measured that every response model is exported) but silently spares a future internal model. Prefer the full walk. |
| `field(default_factory=list)` on `Cotizacion.puntas` | — | Mechanically impossible without reordering (F-7); reordering moves the frozen positional signature. |
| Editing the committed capture JSON to `[]` | — | **Forbidden.** It is live-wire evidence (F-3). |

**Installation:** none. `uv sync --all-packages --all-extras --dev --frozen` is already satisfied;
`uv.lock` must **not** move in this phase (Phase 40 refreshes it exactly once).

## Package Legitimacy Audit

**Not applicable.** This phase installs zero external packages and moves zero lockfile entries.
Every dependency it touches is already present in `uv.lock` and was vetted in earlier milestones.

**Packages removed due to [SLOP] verdict:** none.
**Packages flagged as suspicious [SUS]:** none.

## Architecture Patterns

### System Architecture Diagram

```text
            wire JSON (httpx response)
                      │
                      ▼
        ┌──────────────────────────────┐
        │ _core.parse_get_quote_...    │  ← single site; client.py AND aio.py
        │ (shared parsers)             │    both delegate here  [F-2]
        └──────────────┬───────────────┘
                       │  Cotizacion.from_api / Titulo.from_api
                       ▼
        ┌──────────────────────────────┐
        │ SafeModel.from_api           │
        │   → _decode.walk_model       │  ← BYTE-FROZEN, read-only this phase
        └──────────────┬───────────────┘
                       │ per declared field: data.get(name)
                       ▼
             ┌─────────────────────┐
             │ _decode.walk_field  │
             └──────┬──────────────┘
                    │
      ┌─────────────┼────────────────────────────┐
      │             │                            │
 origin is Union   origin is list           _is_model(hint)
 (:440-446)        (:448-452)               (:461-508)
      │             │                            │
 value None →   value None →              value None →
 return None    return []                 hint(**walk_model({}, SILENT))
 (NO record)    (NO record)               (NO record)   ← NOBJ-02
      ▲             ▲                            ▲
      │             │                            │
  BEFORE 38    ── AFTER 38 ────────────────────────
  puntas took  puntas takes these two branches
  this branch

  ══════════ independent path: CI ratchet ══════════

  packages/*/src/*/__init__.py  ──ast──▶  tools/check_surface_types.py
                                            ├─ RETURN dimension (Phase 32)
                                            └─ FIELD dimension  (Phase 37)
                                                 ├─ untyped-mapping predicate  (existing)
                                                 └─ optional-MODEL predicate   (D-11, NEW)
                                                        │ classifier: ClassDef-name set
                                                        │ from import_root.rglob("*.py")
                                                        ▼
                                                 ClassDef → redden
                                                 Assign (Literal alias) → spare
```

### Pattern 1: Null Object retype via annotation only

**What:** Change `X | None` → `X` on a declared field and let the frozen walker supply the
collapse. No default, no decode edit, no `from_api` override.
**When to use:** Any non-scalar link field whose corpus shows `null`/absent as a legitimate wire
shape.
**Example** (the whole of this phase's source change):

```python
# Source: packages/iol-client/src/iol_client/models.py:213, :301
# BEFORE
puntas: list[Punta] | None
puntas: Punta | None
# AFTER
puntas: list[Punta]
puntas: Punta
```

**Precedent:** Phase 36 D-04 did exactly this for `MarketDataSnapshot.entries` / `market_data`.

### Pattern 2: Semantic test migration, `is None` → truthiness / empty-equality

**What:** Replace retired-semantics assertions with the Phase 36 D-07 idiom, and **rename** any test
whose *name* encodes the retired semantics.
**Example:**

```python
# list-shaped link
assert quote.puntas == []
# model-shaped link — BOTH, because the pair pins identity, not just the predicate
assert bool(titulo.puntas) is False
assert titulo.puntas == Punta.empty()
```

Do **not** write `assert not titulo.puntas` alone (D-06): the compound predicate is satisfied by
values other than the Null Object.

### Pattern 3: Docstring provenance rewrite

**What:** When the branch that produces a test's observed behaviour changes, the docstring citing
the old branch must be rewritten in the same commit.
**Sites in this phase (4, not 2):**

| File:line | Current claim | Becomes |
|---|---|---|
| `test_models.py:202` | *"D-03: la rama Optional del walker devuelve `None` sin emitir registro"* | the NOBJ-02 collapse arm (`_decode.py:448-452`) |
| `test_models.py:437` | *"La rama Optional del walker devuelve `None` sin reportar"* | the NOBJ-02 nested-model arm (`_decode.py:504-505`) |
| `test_null_object.py:113-118` | *"`Titulo.puntas` is `Punta | None`"* | non-Optional; the branch is kept for the other five paquetes (F-5) |
| `models.py:182-186` (Cotizacion) and `:267-269` (Titulo) class docstrings | *"`descripcionTitulo`, `plazo` y `puntas` son `Optional`…"* | `puntas` leaves the Optional list; the D-02 polymorphism note stays |

Also update the two module docstrings that enumerate the shapes: `models.py:12` (`X | None → None`
bullet list is still correct, but the `quote.puntas[0]` sentence at `:15` and `:119` can now be
stated unconditionally) and `test_models.py:10,21`.

### Anti-Patterns to Avoid

- **Editing `_decode.py`.** Guarded by `check_decode_intactness.py`; the semantics already ship.
- **Adding a mirrored edit to `aio.py` "for D-NO-06".** There is no logic to mirror (F-2); a
  duplicated decode path is exactly the drift `surface_parity.py` exists to prevent.
- **Adding a `_FIELD_EXEMPTIONS` entry to silence a redden.** *"A red gate is never resolved by
  weakening the gate"* — narrow the predicate instead (gate docstring; D-01b).
- **Editing `packages/matriz-client/**`.** Out of scope. The new RED test goes in the iol fixture.
- **Editing the committed schema captures** under `.planning/verification/schemas/`.
- **Writing the census into `.planning/verification/<pkg>-findings.md`.** Those files are
  auto-generated between `<!-- BEGIN AUTO-GENERATED -->` markers with a run-scoped schema (D-07).
- **Reordering dataclass fields** to make a default possible (F-7).
- **Bumping any `__version__` or `pyproject.toml` version.** Phase 40 owns that.

## Don't Hand-Roll

| Problem | Don't build | Use instead | Why |
|---|---|---|---|
| Null/absent → empty collapse | A `__post_init__`, a `from_api` override, or a `default_factory` | The frozen `_decode` walker (F-1) | It already does it, silently, for both list and model shapes; anything else duplicates decode logic across two surfaces |
| Deciding "is this annotation a model?" inside the gate | A hardcoded roster of model class names, or a substring test on unparsed source | `ast.ClassDef`-name set from `import_root.rglob("*.py")` (F-6) | Gate already refuses hardcoded rosters by policy; substring tests miss `t.Any`/qualified forms — `_base_name` exists precisely for this |
| Optional-wrapper detection | A regex over `ast.unparse(...)` | A `(inner, was_optional)` variant of `_strip_optional` | All three spellings (`X \| None`, `Optional[X]`, `Union[X, None]`) are already handled structurally; CR-02 was caused by handling only two |
| Public-surface diffing | Hand-editing the snapshot | `uv run python verification/regen_snapshots.py` (F-12) | The header is bit-for-bit validated (W3) |
| Census format | A new table shape | `35-RETIRED-TRIPLES.md`'s form (D-07) | Phase 39 does a **set difference**, not a translation, against these artifacts |
| README breaking callout | A new heading convention | `market-data-client/README.md:7-33` verbatim (F-11) | Same milestone, already reviewed |

**Key insight:** every mechanism this phase needs already exists and is already gated. The failure
mode is not "we can't build it" — it is *"we built a second copy of it."*

## Runtime State Inventory

This is a refactor/rename-adjacent phase (type annotations + prose), so the inventory applies.

| Category | Items Found | Action Required |
|---|---|---|
| Stored data | **None** — verified: no database, no cache, no serialized model store in this repo; `verification/baselines/` and `.planning/verification/schemas/` hold JSON captures, and the two affected captures (`get-historical-quotes.json`, `get-quote.json`) are **live-wire evidence that must NOT be rewritten** (F-3) | none (do not migrate; adjust the *expected* value in the test instead) |
| Live service config | **None** — verified: no external service holds an iol model schema; the IOL API is read-only from this repo's perspective | none |
| OS-registered state | **None** — verified: no scheduled tasks, daemons, or pm2/launchd registrations in this repo | none |
| Secrets / env vars | **None** — `IOL_USER` / `IOL_PASSWORD` / `IOL_BASE_URL` are unaffected by a field annotation change | none |
| Build artifacts / installed packages | `packages/*/src/*.egg-info/` may exist from in-place builds — the gate already filters `.egg-info` (`_BUILD_ARTIFACT_SUFFIX`); no reinstall needed since no package metadata changes. **Committed derived artifact that DOES need regeneration:** `verification/snapshots/iol-client-surface.txt` (F-12) | run `regen_snapshots.py`, commit in the same commit |

## Common Pitfalls

### Pitfall 1: Counting only the assertions that mention `puntas`

**What goes wrong:** The plan enumerates 6 test edits, the 7th (`test_models.py:353-355`) fails at
execution time, and the executor patches it under time pressure — most likely by editing the
committed capture, destroying live-wire evidence.
**Why it happens:** The failing assertion's three lines contain no `puntas` token (F-3).
**How to avoid:** Write the 7th edit into the plan explicitly, with the "do not touch the capture"
constraint attached.
**Warning sign:** A diff touching `.planning/verification/schemas/`.

### Pitfall 2: Widening the field predicate to "any `X | None` on a dataclass field"

**What goes wrong:** All 10 matriz `Literal | None` leaves redden. Phase 37 D-01b deliberately
narrowed the predicate to avoid exactly this, and D-NO-03 permits scalar `T | None` leaves.
**Why it happens:** `MarketId | None` and `Punta | None` are the same AST shape.
**How to avoid:** The ClassDef-name discriminator (F-6), measured to redden 2 and spare 10.
**Warning sign:** `check_surface_types.py` reporting violations in `matriz-client` — an out-of-scope
red, which D-01b says is resolved by **narrowing the predicate**, never by exempting the foreign
field and never by editing the foreign package.

### Pitfall 3: Treating the gate as importable

**What goes wrong:** An implementation using `get_type_hints`/`issubclass` makes the gate import
package modules, which runs `load_dotenv()` and constructs HTTP clients during a lint step.
**Why it happens:** Runtime introspection is the obvious way to answer "is this a SafeModel?".
**How to avoid:** stdlib `ast` only (D-12; the gate's own docstring forbids `eval`/`exec` and
imports).
**Warning sign:** a new non-stdlib import at the top of `tools/check_surface_types.py`, or `uv.lock`
moving.

### Pitfall 4: Asserting `not titulo.puntas` alone

**What goes wrong:** The test passes for values that are not the Null Object, so a future regression
that substitutes some other falsy value goes unnoticed.
**How to avoid:** D-06's pair — `bool(...) is False` **and** `== Punta.empty()`.

### Pitfall 5: Reporting a vacuous green for wallets

**What goes wrong:** SC-4 explicitly forbids it. `wallets-client`'s 10 passing tests prove nothing
about model cleanliness because the package has **zero** models and **zero** domain endpoints (F-8).
**How to avoid:** Every wallets row in the census carries the stub qualification and cites
`29-WALLETS-EXEMPTION.md` and `35-RETIRED-TRIPLES.md:184-197`.

### Pitfall 6: A census that lists only violations

**What goes wrong:** higyrus/ámbito/wallets have 0 violations, so a violations-only census is three
empty tables — the "verde vacuo" SC-2/SC-4 prohibit.
**How to avoid:** D-08's full candidate population: all 142 higyrus fields (or all 15 classes with
per-class field counts and a per-class disposition), plus enumerated zeros for ámbito and wallets.

### Pitfall 7: Half-correcting `35-RETIRED-TRIPLES.md`

**What goes wrong:** The two `models.py` line refs get fixed and the four `_decode.py` refs in the
same file stay stale, leaving a ledger that is authoritative in one paragraph and wrong in another.
**How to avoid:** F-10's table; decide in the plan, in writing, whether the `_decode.py` refs are in
or out.

## Code Examples

### Extending `_adjudicate_field` (D-11) — sketch, not a spec

```python
# Source: derived from tools/check_surface_types.py:600-706, 862-896 (read at HEAD cf79e65)

def _optional_inner(annotation: ast.expr) -> ast.expr | None:
    """The inner arm iff an optional wrapper was present, else ``None``.

    Deliberately NOT ``_strip_optional``: the mapping predicate needs the
    unconditional strip, this dimension needs to know the wrapper was THERE.
    All three spellings are handled by delegating the peel itself.
    """
    inner = _strip_optional(annotation)
    return inner if ast.dump(inner) != ast.dump(annotation) else None


def _class_names(import_root: Path) -> frozenset[str]:
    """Every name bound by a ``class`` statement anywhere in the import root.

    A CLASSIFIER, never a candidate source: candidates still come from the
    exported surface outward. This is what distinguishes ``Punta | None``
    (a dataclass link -> redden) from ``MarketId | None`` (a module-level
    ``Literal`` alias -> spare, D-NO-03).
    """
    names: set[str] = set()
    for path in sorted(import_root.rglob("*.py")):
        for node in ast.walk(_parse(path)):
            if isinstance(node, ast.ClassDef):
                names.add(node.name)
    return frozenset(names)


def _field_annotation_is_optional_model(
    annotation: ast.expr, class_names: frozenset[str]
) -> bool:
    """``Model | None`` or ``list[Model] | None`` on an exported field."""
    inner = _optional_inner(annotation)
    if inner is None:
        return False
    if isinstance(inner, ast.Constant) and isinstance(inner.value, str):
        try:
            inner = ast.parse(inner.value, mode="eval").body
        except SyntaxError:
            return True  # an uninspectable annotation is not a spared one
    if _base_name(inner) in class_names:
        return True
    if isinstance(inner, ast.Subscript) and _base_name(inner.value) == "list":
        return _base_name(inner.slice) in class_names
    return False
```

`_adjudicate_field` then ORs the two predicates and reports a distinct message
(`is annotated \`{...}\` on the exported surface — a model link may not be optional (D-NO-01)`), so
a mapping violation and a link violation stay distinguishable in the failure output. `scan_surface_types`
must thread `class_names` from the per-package loop (it already has `import_root` in hand at
`:932`).

### The census row shape (D-07/D-08), following `35-RETIRED-TRIPLES.md`

```markdown
| package | class | field | annotation | category | disposition | evidence |
|---|---|---|---|---|---|---|
| higyrus-client | Cuenta | `domicilios` | `list[Domicilio]` | list link | already non-Optional — no action | `models.py:442+`; gate scan 442 fields / 0 violations |
| higyrus-client | Movimiento | `fechaLiquidacion` | `str \| None` | scalar leaf | permitted by D-NO-03 | REQUIREMENTS.md:53 |
| ambito-financiero-client | *(none)* | *(none)* | — | — | **zero by enumeration** — `models.py` is 27 lines of docstring, 0 classes | `35-RETIRED-TRIPLES.md:184-197` |
| wallets-client | *(none)* | *(none)* | — | — | **zero by enumeration** — stub, `__all__` has no domain function | `29-WALLETS-EXEMPTION.md`; `__init__.py:22-28` |
```

## State of the Art

| Old approach | Current approach | When changed | Impact |
|---|---|---|---|
| `X \| None` link + caller-side `is None` guards | Null Object: non-Optional link + falsy empty instance | Phase 35 (NOBJ-01/02) | `titulo.puntas.precioCompra` becomes statically and dynamically safe |
| Gate scans return annotations only | Gate scans returns **and** class-body fields | Phase 37 (`_field_candidates_for`) | 442 fields now inspected; the pre-37 green was blind |
| Field predicate = untyped mapping only | Field predicate also bans optional model links | **Phase 38, D-11** | SC-3 becomes a permanent CI ratchet instead of a one-time measurement |
| `to_dict()` round-trip assumed to reproduce the wire | Round-trip is **declaration-shaped**, provably lossy on collapsed links | Phase 30 D-08 documented it; Phase 38 makes it observable (F-3) | One round-trip assertion needs an explicit, commented override |

**Deprecated / outdated inside this phase's blast radius:**

- `test_puntas_nula_queda_nula` (`test_models.py:247`) — the name asserts a retired semantics.
- The `Optional`-branch provenance docstrings at `test_models.py:202` and `:437`.
- `_perturb`'s `Titulo.puntas is Punta | None` sentence (`test_null_object.py:113-118`).
- `35-RETIRED-TRIPLES.md`'s iol line refs and its `_decode.py` line refs (F-10).

## Assumptions Log

| # | Claim | Section | Risk if wrong |
|---|---|---|---|
| A1 | The 11th matriz `Literal \| None` site named in CONTEXT D-11 does not exist as a distinct `models.py` line; the grep and the AST scan both find **10** | F-9 | An SC-3 claim citing "11" would be unsourced. Mitigation: report the grep output verbatim, which is what SC-3 asks for. |
| A2 | Fixing the four stale `_decode.py` refs in `35-RETIRED-TRIPLES.md` is desirable but not mandated by D-12's letter | F-10 | If out of scope, the ledger stays half-correct. Planner decides explicitly. |
| A3 | `_kind_of` is not at `_decode.py:363-367` any more | F-10 | Low — verify before citing; the surrounding refs all drifted by ~5-20 lines. |
| A4 | Dropping the now-redundant `assert x.puntas is not None` at `test_models.py:264` / `:389` is hygiene, not a requirement | F-4 | None — `warn_unreachable` is off, so both spellings typecheck. |
| A5 | No hidden consumer of `Cotizacion.puntas is None` exists outside `packages/iol-client/` and `verification/snapshots/` | F-2 | Low — a full repo grep for `puntas` returned only the five known files. Phase 39's live drivers are the remaining surface, and they are explicitly out of scope. |

## Open Questions

1. **Does the D-11 predicate also cover `dict[str, Model] | None`?**
   - What we know: no such field exists in any of the six packages today (F-9).
   - What's unclear: whether the ratchet should pre-empt it.
   - Recommendation: **no**, and say so in the docstring — an unreachable rule is scope, and the
     gate's own precedent (F-9's blast-radius note about `RequestSpec`) is to *document* the
     reachable-tomorrow case rather than pre-ban it.

2. **Where exactly does the Phase-38 accounting note live — `38-CENSUS.md` or `35-RETIRED-TRIPLES.md`?**
   - What we know: D-12 permits either.
   - Recommendation: **both, asymmetrically.** Patch the iol row + prose paragraph in
     `35-RETIRED-TRIPLES.md` (that file is Phase 39's single source for the middle term), and
     cross-reference it from `38-CENSUS.md`. A note that exists only in a phase-local artifact
     forces Phase 39 to go looking.

3. **Should the census enumerate all 142 higyrus fields, or 15 classes × field counts?**
   - What we know: D-08 requires the full candidate population, not violations only.
   - Recommendation: **per-field for the link/mapping candidates** (which is 0 optional ones — so
     list every model/list/mapping-typed field with its disposition), plus a per-class row with the
     scalar-leaf count. A flat 142-row table is defensible but harder to review; the "no row without
     disposition" requirement of SC-2 is met either way as long as the scalar leaves are covered by
     an explicit aggregate row citing D-NO-03.

## Environment Availability

| Dependency | Required by | Available | Version | Fallback |
|---|---|---|---|---|
| `uv` | every command in the phase | ✓ | 0.11.3 | — |
| CPython 3.12 | venv, mypy target | ✓ | 3.12.13 | — |
| `pytest` | all four suites | ✓ | >= 8.3 (289/289/208/10 passing) | — |
| `mypy` (strict) | SC-1 | ✓ | >= 1.13 | — |
| `ruff` | lint/format | ✓ | >= 0.7 | — |
| `git` | commits, `regen_snapshots` diff | ✓ | — | — |
| Live IOL API | **not required** | ✗ (out of scope) | — | Phase 39 owns live verification; every claim here is mock/introspection-based |
| Network / package registry | **not required** | — | — | zero new dependencies |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none.

## Validation Architecture

### Test Framework

| Property | Value |
|---|---|
| Framework | `pytest` >= 8.3 with `pytest-asyncio` (`asyncio_mode = "auto"`), `pytest-httpx` >= 0.34 |
| Config file | root `pyproject.toml`, `[tool.pytest.ini_options]` (`--import-mode=importlib`, `--strict-markers`, `pythonpath = ["."]`) |
| Quick run command | `uv run --package iol-client pytest packages/iol-client -q` (~15 s) |
| Full suite command | `uv run --package iol-client pytest packages/iol-client -q && uv run --package higyrus-client pytest packages/higyrus-client -q && uv run --package ambito-financiero-client pytest packages/ambito-financiero-client -q && uv run --package wallets-client pytest packages/wallets-client -q && uv run python tools/check_decode_intactness.py && uv run python tools/check_uniform_structure.py && uv run python tools/check_surface_types.py && uv run mypy packages/iol-client && uv run ruff check packages/iol-client` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test type | Automated command | File exists? |
|---|---|---|---|---|
| NOBJ-IOL-01 | `Cotizacion.puntas` is `list[Punta]`, `[]` on null/absent, no divergence | unit | `uv run --package iol-client pytest packages/iol-client/tests/test_models.py -k puntas -q` | ✅ (assertions migrate; see F-4) |
| NOBJ-IOL-01 | `Titulo.puntas` is a `Punta` Null Object, falsy and `== Punta.empty()` | unit | same | ✅ |
| NOBJ-IOL-01 | `titulo.puntas.precioCompra` typechecks under `--strict` | static | `uv run mypy packages/iol-client` | ✅ (add a chained-access line to an existing test to make it *executed*, not just typechecked) |
| NOBJ-IOL-01 | Populated / empty-list / null `puntas` all still decode (the Phase-30 polymorphism) | unit | `pytest ... -k "puntas_poblada or lista_vacia or singular"` | ✅ |
| NOBJ-IOL-01 | Round-trip against the historical capture, with the documented `puntas` lossiness | unit | `pytest ... -k round_trip -q` | ✅ **needs edit** (F-3) |
| NOBJ-IOL-01 | Public surface snapshot matches source | snapshot | `uv run python verification/regen_snapshots.py && git diff --stat verification/snapshots/iol-client-surface.txt` | ✅ (`verification/test_public_surface.py`) |
| NOBJ-IOL-01 | Sync/async parity holds | unit | `pytest packages/iol-client/tests/test_surface_parity.py -q` | ✅ |
| NOBJ-AUD-01 | Gate reddens on a reintroduced `Model \| None` field | unit (RED fixture) | `pytest packages/iol-client/tests/test_surface_types_red.py -q` | ❌ **Wave 0** — new test in the existing file |
| NOBJ-AUD-01 | Gate spares a `Literal`-alias optional leaf | unit (RED fixture) | same | ❌ **Wave 0** |
| NOBJ-AUD-01 | Gate green + non-vacuous on the real tree (`fields >= 350`) | unit | `pytest packages/matriz-client/tests/test_surface_types_red.py -q` (read-only regression check; do not edit) | ✅ |
| NOBJ-AUD-01 | Census has zero rows without disposition | doc review | `checkpoint:human-verify` on `38-CENSUS.md` | ❌ manual |
| NOBJ-AUD-01 | SC-3 closing grep returns only scalar/`Literal` leaves | command + captured output | the two greps in F-9 | ✅ (evidence, not a test file) |
| NOBJ-AUD-01 | Four suites green with the 4 v1.6 gates active | integration | full suite command above | ✅ |

### Sampling Rate

- **Per task commit:** `uv run --package iol-client pytest packages/iol-client -q` (or the affected
  package's leg) + `uv run ruff check <touched paths>`.
- **Per wave merge:** all four package suites + the three `tools/` gates + `uv run mypy packages/iol-client`.
- **Phase gate:** full suite green (289 / 289 / 208+1 / 10 as the floor — any *decrease* is a
  regression, an increase is expected from the new RED test) before `/gsd-verify-work`.

### Wave 0 Gaps

- [ ] `packages/iol-client/tests/test_surface_types_red.py` — add `test_an_optional_model_field_is_caught`
      (covers NOBJ-AUD-01 D-11 lower bound)
- [ ] `packages/iol-client/tests/test_surface_types_red.py` — add
      `test_an_optional_literal_alias_field_is_spared` (covers the D-01b narrowness corollary)
- [ ] No framework install needed; no `conftest.py` changes needed.

*(tdd_mode is enabled. The 7 migrated assertions in `test_models.py` are themselves the RED step for
the source change — write them before flipping the annotations and confirm they fail for the stated
reason, not by collection error.)*

## Security Domain

`security_enforcement: true`, `security_asvs_level: 1`.

### Applicable ASVS Categories

| ASVS category | Applies | Standard control |
|---|---|---|
| V2 Authentication | no | This phase touches no auth path; iol's OAuth flow is untouched |
| V3 Session Management | no | No session state changes |
| V4 Access Control | no | No authorization surface |
| V5 Input Validation | **yes** | The decode walker is the input-validation boundary. The change **strengthens** it: a wrong-typed `puntas` (a `str` where a list/model is declared) still emits a `type`/`non_dict` divergence and is still fatal under `strict_decode` (`_decode.py:449-451`, `:506-508`) — only the `null`/absent case goes silent. Verified in F-1. |
| V6 Cryptography | no | No crypto |
| V7 Error Handling & Logging | **yes** | Divergence records flow to the `iol_client` logger. `verification/test_logging_no_token_leak.py` already pins that no credential reaches a log line; this phase emits **fewer** records, never more, so the leak surface cannot grow. |
| V14 Configuration | **yes (tooling)** | The gate must remain stdlib-only and must never `import` a package module (`load_dotenv()` at import time would read `.env` during a CI lint step). Pitfall 3. |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard mitigation |
|---|---|---|
| Silent type coercion masking upstream API drift | Tampering / Repudiation | Divergence sink + `strict_decode`; NOBJ-02 narrows silence to exactly the `null`/absent-on-non-Optional case, which is a declared policy, not an accident |
| Credential leakage via decode logs | Information Disclosure | `RedactingFilter` + `verification/test_logging_no_token_leak.py` (untouched) |
| Gate weakened to silence a red | Tampering (of the control itself) | Ratchet discipline: *"a red gate is never resolved by weakening the gate"*; `_FIELD_EXEMPTIONS` is qualified-name-keyed and holds exactly one entry |
| Supply-chain via new dependency | Tampering | N/A — zero new dependencies; `uv.lock` must not move |
| Import-time side effects during CI lint | Elevation / Info Disclosure | Gate is `ast`-only; never `eval`/`exec`/`import` |

## Sources

### Primary (HIGH confidence — executed or read at `HEAD = cf79e65`)

- `tools/check_surface_types.py` (full file, 1077 lines) — gate mechanics, D-01b reasoning, exemption taxonomy
- `packages/iol-client/src/iol_client/models.py` — field order, `Punta`, `SafeModel.__bool__`/`empty()`/`to_dict()`
- `packages/iol-client/src/iol_client/_decode.py:400-616` — walker branches, `walk_model` key lookup
- `packages/iol-client/tests/test_models.py`, `test_null_object.py`, `test_surface_types_red.py`, `test_decode.py`
- `packages/matriz-client/tests/test_surface_types_red.py` (test roster) and `src/matriz_client/models.py`, `types.py`
- `verification/snapshots/iol-client-surface.txt`, `verification/regen_snapshots.py`, `verification/schema.py`
- `.planning/verification/schemas/iol-client/{get-quote,get-historical-quotes,get-instruments-by-type}.json`
- `.planning/phases/35-.../35-RETIRED-TRIPLES.md` (full), `36-.../36-CONTEXT.md` D-07
- `packages/market-data-client/README.md:1-40`, `packages/iol-client/README.md`
- `.github/workflows/ci.yml`, root `pyproject.toml`, `.planning/config.json`, `./CLAUDE.md`
- Executed: the gate (`0 violations`, 442 fields), the four package suites, the D-11 predicate
  simulation over all six packages, and the walker-collapse + round-trip experiment (F-1, F-3)

### Secondary (MEDIUM confidence)

- `.planning/REQUIREMENTS.md`, `.planning/STATE.md` — scope and traceability (read, not executed)

### Tertiary (LOW confidence)

- None. No web search was performed and none was warranted: this phase has zero external
  dependencies and every question was answerable against the working tree.

## Metadata

**Confidence breakdown:**

- Standard stack: **HIGH** — no new dependencies; every tool version read from the live environment
- Architecture: **HIGH** — every branch, line number, and field position read from source; the
  walker behaviour executed
- Gate predicate design (D-11): **HIGH** — the proposed discriminator was implemented and run over
  all six packages; the 2-hit / 0-collateral result is measured, not projected
- Census numbers: **HIGH** — produced by the gate's own AST machinery, cross-checked against the
  gate's `442 fields scanned`
- Pitfalls: **HIGH** for 1-5 (each traced to a measured fact), **MEDIUM** for 6-7 (process risks)
- Assumptions log: 5 entries, all LOW-risk and all with a stated mitigation

**Research date:** 2026-08-29
**Valid until:** 2026-09-28 (stable — an internal-only phase; the only invalidator is a commit to
`packages/iol-client/`, `tools/check_surface_types.py`, or `.planning/phases/35-*/`)
