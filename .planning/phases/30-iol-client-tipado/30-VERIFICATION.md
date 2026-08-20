---
phase: 30-iol-client-tipado
verified: 2026-08-20T04:15:00Z
status: gaps_found
score: 8/10 must-haves verified
behavior_unverified: 0
overrides_applied: 0
gaps:
  - truth: "Los probes que comparan formas siguen siendo no-vacuos: reciben un dict proyectado desde el modelo, no el modelo, y por lo tanto siguen discriminando (D-07/D-08, RESEARCH C-2)."
    status: failed
    reason: >
      Empirically falsified. `_as_wire()` (main_iol.py:194-223) projects a model to a
      dict via `SafeModel.to_dict()`, but by the time a model exists the walker has
      already forced every non-optional field to its declared type and discarded every
      undeclared wire key. `schema_of(_as_wire(model))` is therefore a constant function
      of the model's *declaration*, not of the wire. Verified directly against
      `.planning/verification/schemas/iol-client/get-quote.json`: a type-changed
      `ultimoPrecio`, an added `simbolo` key, and a removed `montoOperado` key are all
      invisible to the model-projection reduction (raw wire detects all three; the
      projection detects none). This defeats `probe_schema_snapshot` (3 of 4 endpoints)
      and both `probe_field_type_map` loops. The plan's own SUMMARY (30-04) verified only
      the narrower claim ("the reduction returns a dict, the raw model does not") — true,
      but insufficient to support "sigue discriminando" for the probes' actual purpose,
      which is detecting real API drift. This directly contradicts CLAUDE.md's stated
      Core Value ("cada divergencia entre el cliente y el servicio en vivo debe ser
      detectada") for 3 of iol-client's 4 endpoints.
    artifacts:
      - path: "main_iol.py"
        issue: "_as_wire() (lines 194-223) normalizes via to_dict(), collapsing schema-drift detection to a constant; probe_schema_snapshot (line 1333) and probe_field_type_map (lines 1132, 1169) both lose their discriminating power for type-drift, added-key, and removed-key classes."
    missing:
      - "Feed the snapshot/field-map probes the raw wire body (already reachable via the same Client._request path used for the by_type envelope), keeping the model exclusively for typed-access probes — OR attach a logging.Handler to the iol_client logger that converts each 'decode divergence' record into a SHAPE finding, per code review CR-01's proposed fix."
  - truth: "Blocker anti-pattern: parse_get_instruments_by_type_response fabricates rows from an unvalidated envelope value and can leak AttributeError outside IOLClientError (CR-02)."
    status: failed
    reason: >
      Empirically reproduced. `parse_get_instruments_by_type_response` (_core.py:413-431)
      was rewritten in this phase from an opaque `return titulos` to
      `[Titulo.from_api(fila) for fila in titulos]`, but never validates that `titulos`
      (unwrapped via `data.get("titulos", [])`) is actually a list. Reproduced: a string
      value for `titulos` produces 4 fabricated all-default Titulo rows
      (`['', '', '', '']`); a dict value for `titulos` produces 2 fabricated rows (one per
      key); a top-level list response body raises a bare `AttributeError:
      'list' object has no attribute 'get'`, which escapes the `IOLClientError` hierarchy
      entirely — every caller documented to catch `IOLClientError` (README, the driver's
      except-ladders) will miss it. This is exactly the "silent degradation masks a
      changed/compromised upstream" failure mode that D-06 and this same phase's sibling
      parser `_parse_list_or_raise` were hardened against in the same commit family — the
      parser's own docstring reasons about the envelope-vs-list distinction but does not
      apply the same isinstance discipline to the unwrapped value.
    artifacts:
      - path: "packages/iol-client/src/iol_client/_core.py"
        issue: "Lines 427-431: `data: dict[str, Any] = resp.json()` is an unchecked annotation (top-level list body raises AttributeError instead of IOLAPIError); `titulos: list[Any] = data.get('titulos', [])` is likewise unchecked (string/dict values fabricate plausible-looking rows instead of raising)."
    missing:
      - "isinstance(raw, dict) guard before .get(), and isinstance(titulos, list) guard before the list comprehension, both raising IOLAPIError with the received type named — mirroring the discipline already applied to _parse_list_or_raise in the same phase (code review CR-02 provides the exact fix)."
deferred: []
human_verification: []
---

# Phase 30: `iol-client` tipado Verification Report

**Phase Goal:** El consumidor de `iol-client` accede a cotizaciones, series históricas e instrumentos por **atributo tipado** — un typo lo caza mypy en el editor, no el servidor en producción.
**Verified:** 2026-08-20T04:15:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

Truths merged from ROADMAP § Phase 30 Success Criteria (5) and the 4 plans' `must_haves.truths` (deduplicated to the essential set below; per-plan truths not listed individually here were verified as sub-cases of these and are detailed in the Artifacts/Key-Links sections).

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | `models.py` nuevo con modelos de cotización, serie histórica e instrumentos derivados de los schemas capturados en vivo, `puntas` polimórfico resuelto, camelCase verbatim (SC1) | ✓ VERIFIED | `packages/iol-client/src/iol_client/models.py` — `SafeModel`, `Punta`, `Cotizacion` (20 fields), `Instrumento` (2 fields), `Titulo` (20 fields). `puntas` resolved as `list[Punta] \| None` on `Cotizacion` and `Punta \| None` (singular) on `Titulo`, both documented (D-02). |
| 2 | Las 16 firmas devuelven modelos/`list[modelo]` — cero `Any`/`dict[str, Any]`; `mypy --strict` limpio; ruff/format verdes (SC2) | ✓ VERIFIED | `grep` confirms 8 model-returning annotations in `client.py` and 8 in `aio.py` (16 total, all 4 functions × method/shim × sync/async). `uv run mypy packages/iol-client/src packages/iol-client/tests` → `Success: no issues found in 25 source files`. `ruff check`/`ruff format --check` → all green. |
| 3 | `main_iol.py` lee por acceso por atributo en sus 2 sitios reales de consumo; fixture RED prueba que un typo falla el typecheck (SC3) | ✓ VERIFIED | `grep -c 'quote\.get('` → 0; `quote.ultimoPrecio` attribute access confirmed at both real consumption sites (main_iol.py:368, 448). `test_typed_surface_red.py` exists, passes, and its forward/inverse non-vacuity (per SUMMARY 30-01) was independently re-derivable from the fixture's own `pytest.raises(AttributeError)` + `# type: ignore[attr-defined]` + `warn_unused_ignores=true` construction. |
| 4 | `mercado`/`plazo` quedan `str`; ningún campo de RESPONSE gana `Literal` (SC4) | ✓ VERIFIED | `grep -c 'Literal'` in `models.py` → 0 occurrences on any RESPONSE field; `mercado: str`, `plazo: str \| None` / `plazo: str` confirmed in `Cotizacion`/`Titulo` field declarations read directly from source. |
| 5a | Cada modelo expone `to_dict()` como escape hatch, en el mismo release que la ruptura (SC5, part A) | ✓ VERIFIED | `SafeModel.to_dict()` defined once, inherited by all 4 models; `dataclasses.asdict(cast(Any, self))`. |
| 5b | El README registra la ruptura, incluido el flip de truthiness, alimentando el bump 0.2.0→0.3.0 (SC5, part B) | ✓ VERIFIED (documentation quality caveat) | `## Changelog` / `### v0.3.0` present; truthiness flip named explicitly; 4 model types named; `__version__` still `"0.2.0"`. **Caveat (WR-05, not blocking):** the changelog states the `to_dict()` round-trip loss backwards — it claims a `null` on an Optional field does not survive the round-trip, when in fact it does (`models.py:85-86` documents the opposite, correctly); the actually-lossy case (a `null`/wrong-typed value on a non-optional field, silently zeroed) is unmentioned. This is a documentation-accuracy defect, not an absence of the required disclosure. |
| 6 | Los probes que comparan formas siguen siendo no-vacuos y por lo tanto siguen discriminando (30-04 must-have, D-07/D-08) | ✗ FAILED | See `gaps` frontmatter — empirically falsified (CR-01). The probe receives a dict (technically non-vacuous in the narrow "not a bare string" sense the SUMMARY tested), but that dict is a constant function of the model declaration, so `probe_schema_snapshot` and `probe_field_type_map` lose their actual discriminating power for type-drift/added-key/removed-key classes on 3 of 4 endpoints. |
| 7 | Ningún parser degrada silenciosamente ante una forma inesperada — principio D-06/ASVS V5, aplicado consistentemente a la superficie que esta fase reescribió | ✗ FAILED | See `gaps` frontmatter — empirically reproduced (CR-02). `parse_get_instruments_by_type_response`, rewritten in this phase to iterate `titulos`, has no shape guard on the unwrapped value: a string or dict `titulos` fabricates plausible-looking synthetic rows instead of raising, and a top-level list body raises a bare `AttributeError` outside `IOLClientError`. |

**Score:** 8/10 truths verified (5 ROADMAP success criteria hold at the letter; 2 phase-created reliability guarantees — one explicitly plan-declared as a must-have, one a direct consequence of this phase's own parser rewrite — are empirically false).

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `packages/iol-client/src/iol_client/models.py` | `SafeModel`, `Punta`, `Cotizacion`, `Titulo`, `Instrumento` | ✓ VERIFIED | All 5 classes present, frozen/slots dataclasses, `from_api`/`to_dict` on the base. |
| `packages/iol-client/src/iol_client/_core.py` | 4 parsers returning models; `_parse_list_or_raise` helper | ✓ VERIFIED (with defect) | All 4 parsers rewritten and return models. `_parse_list_or_raise` exists, owns the DecodeScope, raises on non-list. `parse_get_instruments_by_type_response` exists but has the CR-02 defect (see gaps). |
| `packages/iol-client/src/iol_client/client.py` / `aio.py` | 16 signatures re-annotated | ✓ VERIFIED | Confirmed by grep: 8+8 = 16. |
| `packages/iol-client/tests/test_models.py` | model construction/roundtrip tests | ✓ VERIFIED | 237 package tests pass, up from a 205 baseline. |
| `packages/iol-client/tests/test_typed_surface_red.py` | RED typecheck fixture | ✓ VERIFIED | Exists, 1 test, passes; construction matches D-10's validated pattern. |
| `main_iol.py` | `_as_wire` adapter | ✓ VERIFIED (functionally deficient) | `_as_wire` defined and wired at all 4 documented call sites; the adapter itself is well-formed but its premise (model projection preserves discriminating power) does not hold — see gap 1. |
| `verification/snapshots/iol-client-surface.txt` | regenerated golden file | ✓ VERIFIED | 5 class lines present (`Cotizacion`, `Instrumento`, `Punta`, `SafeModel`, `Titulo`); 8-line header intact; idempotent on re-run. |
| `packages/iol-client/README.md` | Changelog + corrected usage section | ✓ VERIFIED | `## Changelog` / `### v0.3.0` present; fictitious API removed; see WR-05 caveat above. |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `models.py` | `_decode.py` | `SafeModel.from_api` delegates to `walk_model` | ✓ WIRED | Confirmed in source; `_decode.py` byte-unchanged (`git diff --exit-code` clean). |
| `_core.py` | `models.py` | parsers construct `Cotizacion`/`Titulo`/`Instrumento` via `.from_api` | ✓ WIRED | All 4 parsers confirmed. |
| `client.py`/`aio.py` | `_core.py` | methods/shims delegate and re-annotate return | ✓ WIRED | 3-line delegation shells confirmed unchanged in shape. |
| `main_iol.py` | `models.py` | driver reads attributes + projects via `to_dict()` at the harness boundary | ⚠️ WIRED BUT FUNCTIONALLY DEFICIENT | Attribute reads are correctly wired (SC3 holds). The `to_dict()` boundary projection is wired exactly as the plan specifies, but the specified behavior itself is the source of gap 1 (CR-01) — this is a "wired as designed, design defeats the intent" case, not a missing connection. |
| `main_iol.py` | `verification/schema.py` | `schema_of(_as_wire(...))` | ⚠️ WIRED BUT FUNCTIONALLY DEFICIENT | Same as above — the call exists at all 4 documented sites; the reduction it produces has lost most of its discriminating power for 3 of 4 endpoints. |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| TYP-01 | 30-01, 30-02, 30-03, 30-04 | `iol-client` tipado — 16 firmas + `models.py` + acceso por atributo en driver | ✓ SATISFIED (with reliability caveats) | The typed-attribute-access goal (the phase's literal stated goal) is fully achieved: mypy strict is clean, 16/16 signatures migrated, `main_iol.py` reads by attribute, the RED fixture exists and holds. The two gaps above (CR-01, CR-02) are reliability defects in the *verification harness fidelity* and in an *unvalidated-input parser*, both introduced by this phase — they do not undo the typed-attribute-access delivery, but they do undermine a must-have this phase's own plan (30-04) explicitly declared and claimed as "held." |

No orphaned requirements: `.planning/REQUIREMENTS.md` maps only TYP-01 to Phase 30, and all 4 plans declare `requirements: [TYP-01]`.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| `main_iol.py` | 194-223 (`_as_wire`), 1132/1169/1333 (call sites) | Verification-harness reduction defeated by design (CR-01) | 🛑 BLOCKER | DRIFT-01 schema-snapshot and field-type-map probes lose discriminating power for type-drift/added-key/removed-key classes on 3 of 4 endpoints. |
| `packages/iol-client/src/iol_client/_core.py` | 427-431 | Unvalidated envelope value iterated into fabricated rows; bare `AttributeError` escapes `IOLClientError` (CR-02) | 🛑 BLOCKER | Silent fabrication of synthetic financial rows from a malformed/compromised upstream; uncaught exception type for callers relying on the documented error hierarchy. |
| `packages/iol-client/src/iol_client/_core.py` | 345 (`_parse_list_or_raise` signature) | `type[Any] -> list[Any]` gives no real mypy narrowing at the call boundary (WR-01) | ⚠️ WARNING | A parser wired to the wrong model class would still typecheck; undercuts TYP-01's static guarantee at exactly this one seam. Not blocking — `mypy --strict` on the actual (correct) call sites is still 0. |
| `main_iol.py` | 119-122, 1134-1164 | `_ASSUMED_QUOTE_FIELDS` still contains `"simbolo"`, which is not a `Cotizacion` field and never was in the corpus (WR-02) | ⚠️ WARNING | Will fire a permanent, un-clearable `SHAPE` finding on every future live run. Same root cause as CR-01 (model projection can never satisfy it either way) plus an un-migrated assumption dict. |
| `packages/iol-client/src/iol_client/models.py` | 145-146, 225-226 | `int`-declared `laminaMinima`/`lote` silently zeroed on a JSON float (WR-03) | ⚠️ WARNING | Divergence *is* reported to the package logger (not to the driver, per CR-01), so library consumers configuring logging see it; the driver does not. |
| `packages/iol-client/src/iol_client/_core.py` | 339-341 | `parse_get_quote_response` has no shape guard, asymmetric with its two list-shaped siblings (WR-04) | ⚠️ WARNING | Not a plan-declared must-have for this specific parser; noted for consistency. |
| `packages/iol-client/README.md` | Changelog v0.3.0 | States the `to_dict()` round-trip loss backwards (WR-05) | ⚠️ WARNING | See SC5b caveat above. |
| `main_iol.py` | 829-830, 840-842 | Empty instrument-type listing reported as a shape defect (WR-06) | ⚠️ WARNING | `cauciones`/`letras` legitimately returning `[]` outside market hours triggers a spurious `SHAPE` finding. |
| `main_iol.py` | 980-981 | `probe_parity_sync_async` retains only partial discriminating power post-projection (WR-07) | ⚠️ WARNING | Same root cause family as CR-01; narrower blast radius (only Optional-field-presence and list-cardinality differences remain detectable). |
| `client.py:460-461`, `aio.py:462-463` | — | `DecodeScope` bound but never retired on raw `_request` calls with no decorated parser (WR-08) | ⚠️ WARNING | Not reachable in current driver ordering; reachable from library code mixing raw `_request` with standalone `from_api`. |
| `models.py` | 72-78, 80-94 | `SafeModel.from_api`/`to_dict` raise a bare `TypeError` if called directly on the exported base class (IN-01) | ℹ️ INFO | `SafeModel` is in `__all__` but not itself a usable dataclass. |
| `main_iol.py` | 1091 | Stale source-line reference in a live finding's `diff` text (IN-02) | ℹ️ INFO | Cosmetic; points at `client.py:254` which no longer holds the referenced code. |
| `verification/snapshots/iol-client-surface.txt` | 11, 18-21 | `to_dict()` invisible to the surface-snapshot guard (IN-03) | ℹ️ INFO | Snapshot records constructors only, not methods. |
| `packages/iol-client/src/iol_client/_decode.py` | 138-140, 243-244 | Frozen copy still carries higyrus-provenance comments (IN-04) | ℹ️ INFO | Correct per the intactness gate; out of scope to change this phase. |

No `TBD`/`FIXME`/`XXX` debt markers found in the files modified by this phase.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| `mypy --strict` clean over src+tests | `uv run mypy packages/iol-client/src packages/iol-client/tests` | `Success: no issues found in 25 source files` | ✓ PASS |
| `ruff`/`ruff format` clean | `uv run ruff check packages/iol-client && uv run ruff format --check packages/iol-client` | All checks passed / 25 files already formatted | ✓ PASS |
| Package test suite green, grown from 205 baseline | `uv run pytest packages/iol-client -q` | `237 passed` | ✓ PASS |
| All 6 packages' suites green | `uv run pytest packages/ -q` | `1567 passed, 1 deselected` | ✓ PASS |
| 3 baselines byte-identical post-migration | `git diff --exit-code .planning/verification/schemas/iol-client/` | exit 0 | ✓ PASS |
| CR-01 reproduction: model-projection blindness to type/add/remove drift | inline python (see verification transcript) | type-change/added-key/removed-key all undetected via `_as_wire`; all 3 detected on raw wire | ✗ FAIL (confirms gap) |
| CR-02 reproduction: unvalidated `titulos` fabricates rows / leaks `AttributeError` | inline python (see verification transcript) | string `titulos` → 4 fabricated rows; dict `titulos` → 2 fabricated rows; top-level list body → bare `AttributeError` | ✗ FAIL (confirms gap) |
| Shape guard holds for `get_historical_quotes`/`get_instruments` (the two `_parse_list_or_raise` consumers) | inline python | both raise `IOLAPIError` on a non-list body | ✓ PASS |
| Driver reads by attribute, no subscript access remains | `grep -c 'quote\.get(' main_iol.py` | `0` | ✓ PASS |

### Probe Execution

Not applicable — this phase does not use `scripts/*/tests/probe-*.sh` conventional probes; its verification surface is `main_iol.py`'s own named probes, exercised via the code-review's live reproductions above and via the package test suite.

### Human Verification Required

None required to resolve status. The two gaps identified are conclusively demonstrated by direct code inspection and reproducible interpreter sessions (not matters of taste, visual appearance, or judgment calls) — they route to `gaps_found`, not `human_needed`.

### Gaps Summary

Phase 30's literal, stated goal — typed attribute access replacing dict access across `iol-client`'s public surface, with mypy catching a typo in the editor — **is fully delivered**: 16/16 signatures, mypy strict clean, RED fixture non-vacuous, `main_iol.py` migrated, README changelog present, `__version__` correctly held at `0.2.0`. Five of the five ROADMAP-level Success Criteria hold at the letter.

However, two defects — both introduced by this phase's own changes, both flagged BLOCKER by the phase's own code review, and both independently reproduced during this verification — undercut guarantees the phase's own plans explicitly claimed:

1. **CR-01** — the `_as_wire()` adapter the phase built specifically to keep the verification harness's DRIFT-01 probes "non-vacuous" (30-04-PLAN.md's own stated purpose, and a must-have truth in that plan's frontmatter) in fact renders those probes blind to the three drift classes — type change, added key, removed key — they existed to catch, on 3 of the client's 4 endpoints. This is a direct regression against CLAUDE.md's stated Core Value ("cada divergencia entre el cliente y el servicio en vivo debe ser detectada, documentada y corregida"), and it is exactly the "probe reports PASS precisely when it's broken" failure mode the plan's own prohibitions warned against.

2. **CR-02** — `parse_get_instruments_by_type_response`, rewritten by this phase from an inert pass-through to an active model-building loop, iterates an unvalidated `titulos` value. A malformed upstream response now produces silently fabricated financial rows or an uncaught `AttributeError` outside the documented `IOLClientError` hierarchy — the exact "silent degradation masks a compromised upstream" failure this same phase explicitly hardened its sibling parsers against, in the same commit family.

Both gaps have concrete, scoped fixes proposed in the code review (`30-REVIEW.md` CR-01, CR-02) and do not require re-architecting the phase's typed-model approach — they are boundary-adaptation and input-validation fixes, respectively. Recommend a closure plan targeting these two findings before Phase 33 (live strict verification) runs, since Phase 33 depends on the DRIFT-01 snapshot signal CR-01 currently defeats, and on `get_instruments_by_type` not fabricating data under live-network conditions.

---

_Verified: 2026-08-20T04:15:00Z_
_Verifier: Claude (gsd-verifier)_
