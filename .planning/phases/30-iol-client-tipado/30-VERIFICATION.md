---
phase: 30-iol-client-tipado
verified: 2026-08-20T22:45:21Z
status: gaps_found
score: 6/7 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 8/10 must-haves verified
  gaps_closed:
    - "Truth 7 / CR-02 — parse_get_instruments_by_type_response fabricates rows from an unvalidated envelope value and leaks AttributeError outside IOLClientError. Closed by plan 30-05: isinstance(raw, dict) and isinstance(titulos, list) guards, both raising IOLAPIError naming the received type. Independently reproduced in this re-verification against the live _core.py source: top-level list body, string titulos, and dict titulos all now raise IOLAPIError; missing-key and empty-list paths still return []."
  gaps_remaining:
    - "Truth 6 / CR-01 — partially closed by plan 30-06, but a new failure mode was discovered and independently reproduced during this re-verification (matching 30-REVIEW.md's post-closure BLOCKER): a captured JSON `null` body (HTTP 200 with a literal null response) is indistinguishable from a failed capture because probe_field_type_map and probe_schema_snapshot test `is None` / `payload is None` instead of dict-membership against raw_wire. _capture_raw_wire's own contract states a failed capture leaves the key ABSENT (never present with value None), but neither consumer honors that distinction. Result: a null-bodied live response produces zero SHAPE findings across all four endpoints and both probes report PASS — probe_field_type_map's detail line names three endpoints as 'checked' when none were inspected. This is the exact 'probe reports PASS precisely when it's broken' failure mode CR-01 was closed to eliminate, recurring in a case the closure's own regression-lock test suite (9 tests, none covering a null body) does not exercise."
  regressions: []
gaps:
  - truth: "Los probes de drift (probe_field_type_map, probe_schema_snapshot) nunca reportan PASS cuando la captura de un endpoint no llegó en la forma esperada — incluyendo un body capturado como JSON null — porque un insumo que llegó como null no es un insumo que 'nunca llegó' (30-06 must_haves.prohibitions #1; T-30-06-05)."
    status: failed
    reason: >
      Empirically reproduced against the live code, independent of 30-REVIEW.md's own
      reproduction. `_capture_raw_wire` (main_iol.py:237-337) stores
      `raw_by_endpoint[func_name] = resp.json()` unconditionally on a 200 response, so an
      upstream body of literal `null` is stored as Python `None` — a value indistinguishable,
      by naive `is None` testing, from "key absent because the capture raised." The function's
      own docstring states the opposite intent verbatim: "Un endpoint cuya captura levantó
      queda ausente del dict — ausente, no None, para que aguas abajo no se pueda confundir
      'no capturado' con 'capturado como null'." All three downstream consumers violate that
      contract by testing `is None` (main_iol.py:1225 `if quote_raw is not None`, :1280
      `if historical_raw is not None`, :1208 `elif envelope is not None`) or `payload is None`
      (main_iol.py:1464, probe 13) instead of `in raw_wire` / `not in raw_wire`.

      Reproduction (this verification, not copied from the review):
      `raw_wire = {"get_quote": None, "get_historical_quotes": None, "get_instruments": None,
      "get_instruments_by_type": None}` fed directly to both probe functions returns:
      `probe_field_type_map` → `PASS, "3 endpoints checked (get_quote, get_historical_quotes,
      get_instruments_by_type), no drift"` and `probe_schema_snapshot` → `PASS,
      "written=[] matched=[] skipped=['get_quote', 'get_historical_quotes', 'get_instruments',
      'get_instruments_by_type']"`. Zero findings are emitted. `schema_of(None) == "NoneType"`
      differs from every committed baseline (each a dict schema), so `_write_or_check_schema`
      — itself unmodified and correct — would emit 4 SHAPE findings if it were ever called with
      these payloads; it is never called, because the `payload is None` gate at probe-13's call
      site intercepts first. Worse, probe 12's "checked" list is built with `if name in
      raw_wire` (a different, correct predicate than the `is not None` checks that actually
      gate the per-field logic), so its PASS detail names three endpoints as inspected when
      none of their fields were examined — the "PASS names endpoints it skipped" defect
      30-REVIEW.md's fresh code review (d4ee6e5, 2026-08-20T19:45:00Z) also found and named
      CR-01 (post-closure). This is a genuine new BLOCKER, not a restatement of the original
      CR-01 (that one — model-projection blindness on 3 of 4 endpoints for 3 documented drift
      classes — is independently confirmed fixed: the 9-test regression lock in
      `verification/test_main_iol_raw_wire_drift.py` passes, and a direct reproduction of the
      original type-drift/added-key/removed-key mutations against the real committed
      `get-quote.json` baseline now correctly produces FINDING for all three and PASS for the
      unmutated body).
    artifacts:
      - path: "main_iol.py"
        issue: "Lines 1169-1173, 1208, 1225, 1280 (probe_field_type_map) and 1463-1468 (probe_schema_snapshot) test `is None` / `payload is None` against values sourced from raw_wire.get(key), conflating a legitimately captured null body with a failed/absent capture. Line 1356-1359's 'checked' list uses `in raw_wire` (membership), a different and inconsistent predicate from the `is not None` gates that determine whether any check actually ran, so the PASS detail can name endpoints that were never inspected."
    missing:
      - "Replace every `raw_wire.get(key)` + `is None`/`is not None` check in probe_field_type_map and probe_schema_snapshot with membership tests (`key in raw_wire` / `key not in raw_wire`), so a captured None is treated as a real (schema_of == 'NoneType') payload rather than as a skip. Add a null-body case to verification/test_main_iol_raw_wire_drift.py — e.g. `{'get_quote': None}` must produce a SHAPE finding from both probes, and probe_field_type_map's PASS detail must never name an endpoint whose fields were not actually examined. 30-REVIEW.md's CR-01 (post-closure, d4ee6e5) supplies the exact proposed fix."
deferred: []
human_verification: []
---

# Phase 30: `iol-client` tipado Verification Report (Re-verification after gap closure)

**Phase Goal:** El consumidor de `iol-client` accede a cotizaciones, series históricas e instrumentos por **atributo tipado** — un typo lo caza mypy en el editor, no el servidor en producción.
**Verified:** 2026-08-20T22:45:21Z
**Status:** gaps_found
**Re-verification:** Yes — after gap closure (plans 30-05, 30-06)

## Goal Achievement

### Observable Truths

Truths carried forward from the prior verification (2026-08-20T04:15:00Z), re-checked here.
Truths 1-5 were previously VERIFIED and are unaffected by the gap-closure plans (30-05 touches
only `packages/iol-client/src/iol_client/_core.py` and two test files; 30-06 touches only
`main_iol.py` and one new test file — neither touches `models.py`, `client.py`, `aio.py`, the
README, or the surface snapshot). They received a regression check (existence + re-run of the
relevant automated gates) rather than a full re-derivation.

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | `models.py` con modelos tipados de cotización/serie histórica/instrumentos, `puntas` polimórfico resuelto (SC1) | ✓ VERIFIED (regression) | `packages/iol-client/src/iol_client/models.py` untouched by 30-05/30-06 (`git diff --exit-code packages/iol-client/src/iol_client/models.py` clean since 30-04). Content unchanged from the prior verification's direct inspection. |
| 2 | 16 firmas devuelven modelos, cero `Any`/`dict[str, Any]`, `mypy --strict` limpio (SC2) | ✓ VERIFIED | Re-run: `uv run mypy packages/iol-client/src packages/iol-client/tests` → `Success: no issues found in 25 source files`. `uv run ruff check packages/iol-client && uv run ruff format --check packages/iol-client` → both clean. |
| 3 | `main_iol.py` lee por atributo en sus 2 sitios reales; RED fixture prueba que un typo falla el typecheck (SC3) | ✓ VERIFIED (regression) | `test_typed_surface_red.py` untouched by 30-05/30-06 and still present in the passing test count; attribute-access sites at the original locations are untouched (neither closure plan modified quote-consumption code). |
| 4 | `mercado`/`plazo` quedan `str`; ningún campo RESPONSE gana `Literal` (SC4) | ✓ VERIFIED (regression) | `models.py` untouched; `grep -c Literal` in models.py unaffected by this closure. |
| 5 | `to_dict()` escape hatch en todos los modelos; README documenta la ruptura incl. flip de truthiness (SC5) | ✓ VERIFIED (documentation caveat carried forward, non-blocking) | `SafeModel.to_dict()` untouched. README changelog untouched by 30-05/30-06 — the prior verification's WR-05 caveat (round-trip loss description backwards) still applies and is unresolved, and 30-REVIEW.md adds WR-09 (version mismatch: changelog says v0.3.0, `__version__`/`pyproject.toml` still say 0.2.0; CR-02's new raising behavior on `get_instruments_by_type` is undocumented). Both are documentation-accuracy warnings, not an absence of the required disclosure — not blocking. |
| 6 | Los probes de drift (`probe_schema_snapshot`, `probe_field_type_map`) nunca son vacuos y nunca reportan PASS cuando la captura falló o el body no tiene la forma esperada (CR-01, 30-04/30-06 must-have) | ✗ FAILED — new failure mode | **Major improvement, not yet closed.** Independently re-run: the 9-test offline regression lock (`verification/test_main_iol_raw_wire_drift.py`) passes, and a direct reproduction of the three original CR-01 mutations (`ultimoPrecio` float→str, added `simbolo` key, removed `montoOperado` key) against the real committed `get-quote.json` baseline now correctly produces `FINDING` for all three and `PASS` for the unmutated body — the original defect (model-projection blindness on 3/4 endpoints) is genuinely fixed. **However**, this re-verification independently reproduced 30-REVIEW.md's fresh post-closure BLOCKER: a captured JSON `null` body (a legitimate 200-OK response) is silently treated as "capture failed" by both probes because they test `is None` instead of dict membership against `raw_wire`. Feeding `{"get_quote": None, "get_historical_quotes": None, "get_instruments": None, "get_instruments_by_type": None}` to both probe functions directly returns `PASS` with zero findings from both, and `probe_field_type_map`'s PASS detail falsely names three endpoints as "checked." See `gaps` frontmatter for the full reproduction. |
| 7 | Ningún parser degrada silenciosamente ante una forma inesperada (CR-02, D-06/ASVS V5) | ✓ VERIFIED | Independently reproduced against the live `_core.py` source (not copied from 30-05-SUMMARY.md): `parse_get_instruments_by_type_response` on a top-level list body raises `IOLAPIError` (`"[0] shape mismatch: expected dict envelope, got list"`); on `{"titulos": "GGAL"}` raises `IOLAPIError` (`"...got str"`); on `{"titulos": {"a": 1, "b": 2}}` raises `IOLAPIError` (`"...got dict"`). `{}` and `{"titulos": []}` both still return `[]`. No `AttributeError`, `TypeError`, or `KeyError` escapes the function. The async-surface parity test (`test_async_get_instruments_by_type_raises_on_malformed_titulos`) confirms both surfaces share the single `_core` dispatch — `aio.py` is byte-unchanged (`git diff --exit-code packages/iol-client/src/iol_client/aio.py` exits 0). |

**Score:** 6/7 truths verified. The two prior gaps are not symmetric outcomes: CR-02 (truth 7) is
fully and cleanly closed; CR-01 (truth 6) is substantially improved (the 3 originally-reported
drift classes are now detected on all 4 endpoints, where previously 0 were) but a new,
independently-reproduced failure mode of the exact same guarantee class — a probe reporting
PASS precisely when it is broken — was found during this re-verification and remains open.

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `packages/iol-client/src/iol_client/_core.py` | `parse_get_instruments_by_type_response` with two shape guards | ✓ VERIFIED | `isinstance(raw, dict)` and `isinstance(titulos, list)` guards present at lines 452-459, both raising `IOLAPIError(0, ...)` naming the received type; confirmed by direct source read and by reproduction. |
| `packages/iol-client/tests/test_core.py` | RED tests for the 3 reproduced CR-02 failure shapes + 2 preserved-behavior tests | ✓ VERIFIED | Package suite passed 242 (baseline 237 + 5 new: 4 in test_core.py, 1 async parity test), confirmed by re-running `uv run pytest packages/iol-client -q`. |
| `packages/iol-client/tests/test_async_client.py` | async-surface parity test for the CR-02 guard | ✓ VERIFIED | Present, part of the 242-passing count; `aio.py` confirmed byte-unchanged. |
| `main_iol.py::_capture_raw_wire` | raw-wire capture helper feeding probes 12/13 | ✓ VERIFIED (present, wired) with the CR-01-new defect above | Present at lines 237-337, builds specs via `_core.build_*_request`, wraps each endpoint in its own try/except, absent-on-failure contract stated in its docstring but not honored by its consumers for the null-body case (see gap). |
| `verification/test_main_iol_raw_wire_drift.py` | offline regression lock, 7 test functions (9 cases parametrized) | ✓ VERIFIED (existing tests pass) but **incomplete** | 337 lines (min_lines: 120 satisfied). All 9 parametrized cases pass — re-run independently: `uv run pytest verification/test_main_iol_raw_wire_drift.py -v` → `9 passed`. Does not cover the null-body case that produces the new BLOCKER — this is precisely why the regression lock did not catch it. |
| `.planning/verification/schemas/iol-client/*.json` | 4 baselines byte-identical | ✓ VERIFIED | `git diff --exit-code .planning/verification/schemas/iol-client/` exits 0. |
| `packages/` (all package source) | untouched by 30-06 | ✓ VERIFIED | `git diff --exit-code packages/` exits 0 against the committed tree; 30-06 modified only `main_iol.py` and the new test file, per its own scope declaration. |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `main_iol.py::_capture_raw_wire` | `iol_client._core` builders | `_core.build_get_quote_request` etc. | ✓ WIRED | Confirmed by direct source read; four builder calls present, one per endpoint. |
| `main_iol.py::_capture_raw_wire` | `iol_client.client.Client._request` | raw authenticated request | ✓ WIRED | `client._request(spec)` present; auth-once discipline preserved (uses the threaded `client`, constructs no new instance). |
| `main_iol.py::probe_schema_snapshot` | `verification.schema.schema_of` | `schema_of(raw_wire[func_name])` inside `_write_or_check_schema` | ⚠️ WIRED BUT GATED INCORRECTLY | The link itself is correct and `_write_or_check_schema` is unmodified/correct — `schema_of(None) == "NoneType"` would be compared correctly if reached. The defect is upstream of this link: the `payload is None` gate at the probe-13 call site (main_iol.py:1464) prevents a null-bodied capture from ever reaching `_write_or_check_schema`, so the link exists but is unreachable for exactly the input class this gap-closure was built to make reachable. |
| `packages/iol-client/src/iol_client/_core.py::parse_get_instruments_by_type_response` | `client.py:572`, `aio.py:580` | single-dispatch delegation | ✓ WIRED | Both surfaces confirmed (by the async parity test and by direct source read of the delegation shells) to route through the one guarded function — no duplicated logic to diverge. |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| TYP-01 | 30-01, 30-02, 30-03, 30-04, 30-05, 30-06 | `iol-client` tipado — 16 firmas + `models.py` + acceso por atributo en driver, con verificación en vivo no-vacua | ✓ SATISFIED at the literal phase-goal level; ⚠️ the phase's own additionally-declared reliability guarantee for its verification harness is not fully closed | The stated phase goal — typed attribute access, mypy catching a typo in the editor — is fully delivered and unaffected by this gap-closure round: mypy strict clean, 16/16 signatures, RED fixture intact, `main_iol.py` reads by attribute. TYP-01 as a requirement is satisfied. The residual gap is in the verification harness's own non-vacuity guarantee (a must-have this same phase's plans 30-04 and 30-06 explicitly declared and re-declared as a closure target), which is a narrower reliability property of the drift-detection tooling, not of the published package surface. |

No orphaned requirements: `.planning/REQUIREMENTS.md` maps only TYP-01 to Phase 30; all 6 plans (30-01 through 30-06) declare `requirements: [TYP-01]`.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| `main_iol.py` | 1169-1173, 1208, 1225, 1280, 1356-1359 (`probe_field_type_map`); 1463-1468 (`probe_schema_snapshot`) | A captured JSON `null` is indistinguishable from a failed capture (`is None` vs. dict-membership); PASS detail line uses a different, inconsistent predicate than the checks that gate it | 🛑 BLOCKER | Independently reproduced (see gaps). Four SHAPE findings that should fire on a `200 + null` live response fire zero; `probe_field_type_map`'s PASS message names endpoints it never inspected. Same failure class ("probe reports PASS precisely when it's broken") the 30-06 closure was built to eliminate for the model-projection case; recurs for the null-body case. |
| `main_iol.py` | 1417-1421, 1490-1500 (`probe_schema_snapshot`) | `probe_schema_snapshot` never receives `capture_fids`; a fully-failed capture (`raw_wire == {}`) reports `PASS` with `written=[] matched=[] skipped=[...]` rather than `FINDING`/`SKIPPED` | ⚠️ WARNING (30-REVIEW.md WR-01, pre-existing, not re-fixed by this closure) | In combination with the BLOCKER above, a completely uninformative capture produces a completely clean run. |
| `main_iol.py` | 324-337 (`_capture_raw_wire` except branch) | `actual=repr(exc)` embeds the full upstream error response body (via `IOLAPIError.__str__`) into a committed findings artifact | ⚠️ WARNING (30-REVIEW.md WR-02) | Contradicts the function's own docstring ("el body crudo alimenta schema_of y nada más") and T-29-36 (type/path only, never a wire value). Pre-existing pattern elsewhere in the file, but this is a new call site whose docstring explicitly promises otherwise. |
| `verification/test_main_iol_raw_wire_drift.py:26-30` | — | The entire CR-01 regression lock (7 tests / 9 cases) is not collected by CI — only local/full-suite runs collect `verification/` | ⚠️ WARNING (30-REVIEW.md WR-04) | The only automated protection for the fixed BLOCKER cannot go red in CI; `main_iol.py` is also outside mypy's `files` list, so 427 changed driver lines are neither typechecked nor CI-tested. |
| `main_iol.py:237-339` | — | `_capture_raw_wire` itself has no direct/unit test; all 7 regression-lock tests exercise the two probes with a synthetic `raw_wire`, never the capture function | ⚠️ WARNING (30-REVIEW.md WR-05) | A regression that reintroduced the old model-projection *inside* the capture helper would be caught by only one of the seven tests. |
| `packages/iol-client/README.md` | Changelog `### v0.3.0` | Version heading does not match `__version__`/`pyproject.toml` (still `0.2.0`); CR-02's new `IOLAPIError`-raising behavior on `get_instruments_by_type` is undocumented | ⚠️ WARNING (30-REVIEW.md WR-09, carries forward prior WR-05) | A consumer catching narrow exception types around `get_instruments_by_type` migrates incorrectly; the version a consumer can actually install (`0.2.0`) does not match the documented release. |
| `main_iol.py:1187` | `diff="client.py:254 hace data.get('titulos', []) y devuelve [] silenciosamente"` | Stale source reference that now describes removed behavior post-CR-02 | ℹ️ INFO (30-REVIEW.md WR-10, escalated from a prior INFO) | Points at `client.py:254` (wrong location — the actual code is `_core.py:455`) and describes silent-degradation behavior that CR-02 already fixed for the case that matters; cosmetic but misleading to an operator reading a live finding. |

No `TBD`/`FIXME`/`XXX` debt markers found in `main_iol.py`, `packages/iol-client/src/iol_client/_core.py`, `verification/test_main_iol_raw_wire_drift.py`, or the modified test files (`test_core.py`, `test_async_client.py`).

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| `mypy --strict` clean over src+tests | `uv run mypy packages/iol-client/src packages/iol-client/tests` | `Success: no issues found in 25 source files` | ✓ PASS |
| `ruff`/`ruff format` clean | `uv run ruff check packages/iol-client && uv run ruff format --check packages/iol-client` | All checks passed / 25 files already formatted | ✓ PASS |
| Package test suite green, grown from 237 baseline | `uv run pytest packages/iol-client -q` | `242 passed` | ✓ PASS |
| CR-01 regression lock (9 cases) | `uv run pytest verification/test_main_iol_raw_wire_drift.py -v` | `9 passed` — 3 drift classes detected, unmutated body PASSes, capture-failure-by-exception produces FINDING, model-projection-blindness canary confirms the original defect's root cause | ✓ PASS |
| CR-01 original reproduction (type-drift/added-key/removed-key against real `get-quote.json`) | via the regression-lock test's parametrized cases | All 3 now `FINDING`; unmutated body `PASS` — 3/3 detected where the original verification found 0/3 | ✓ PASS (confirms this part of the gap closed) |
| **CR-01 new-BLOCKER reproduction: null-bodied `raw_wire` fed directly to both probes** | inline python, this verification session | `probe_field_type_map` → `PASS "3 endpoints checked (...), no drift"`; `probe_schema_snapshot` → `PASS "written=[] matched=[] skipped=[...]"`; **0 findings emitted from either probe on 4/4 null-bodied endpoints** | ✗ FAIL (confirms new gap) |
| CR-02 reproduction: 3 malformed `titulos` shapes | inline python against live `_core.py`, this verification session | Top-level list → `IOLAPIError` (`got list`); string `titulos` → `IOLAPIError` (`got str`); dict `titulos` → `IOLAPIError` (`got dict`); `{}` and `{"titulos": []}` still `[]` | ✓ PASS (confirms this gap closed) |
| Schema baselines untouched | `git diff --exit-code .planning/verification/schemas/iol-client/` | exit 0 | ✓ PASS |
| No package source touched by 30-06 | `git diff --exit-code packages/` | exit 0 | ✓ PASS |
| WR-02 fix: no un-supported assumed key | direct read of `_ASSUMED_QUOTE_FIELDS` (main_iol.py:129-131) | Only `ultimoPrecio` remains; `simbolo` removed | ✓ PASS |
| WR-06 fix: empty instrument-type list is not a shape defect | direct read of the sanity predicate (main_iol.py:953-956) | `isinstance(titulos, list)` + `titulos and not isinstance(titulos[0], Titulo)` — empty list no longer flagged | ✓ PASS |

### Probe Execution

Not applicable — this phase does not use `scripts/*/tests/probe-*.sh` conventional probes; its verification surface is `main_iol.py`'s own named probes and the `verification/test_main_iol_raw_wire_drift.py` offline regression lock, both exercised directly above.

### Human Verification Required

None required to resolve status. The new gap is conclusively demonstrated by direct code inspection and a reproducible, credential-free interpreter session (not a matter of taste, visual appearance, or judgment) — it routes to `gaps_found`, not `human_needed`. This finding independently corroborates 30-REVIEW.md's fresh code review (committed `d4ee6e5`, reviewed 2026-08-20T19:45:00Z), which reached the same conclusion by the same reproduction method.

### Gaps Summary

This re-verification confirms **one of the two prior gaps is fully closed** and finds that
**the other is substantially — but not completely — closed**, with a new failure mode of the
same guarantee class discovered independently (and matching 30-REVIEW.md's fresh finding).

**CR-02 (truth 7) — CLOSED.** Plan 30-05's two `isinstance` guards in
`parse_get_instruments_by_type_response` are correct, minimal, and confirmed by direct
reproduction against the live source: all three previously-reproduced failure shapes (top-level
list body, string `titulos`, dict `titulos`) now raise `IOLAPIError` naming the received type;
the missing-key and empty-list paths are unchanged; both surfaces (sync and async) are proven —
not assumed — to share the fix through the single `_core` dispatch point.

**CR-01 (truth 6) — SUBSTANTIALLY IMPROVED, NOT CLOSED.** Plan 30-06 correctly diagnosed and
fixed the original defect: `probe_schema_snapshot` and `probe_field_type_map` now read the raw
wire instead of a model projection, and the three originally-reported drift classes (type
change, added key, removed key) are detected again on all four endpoints — independently
confirmed via the 9-case regression lock and a direct reproduction against the real committed
`get-quote.json` baseline. However, this re-verification independently reproduced a new,
distinct BLOCKER: `_capture_raw_wire`'s consumers test `is None` rather than dict membership, so
a captured JSON `null` body (a legitimate, successful 200-OK capture) is treated as "not
captured." A live upstream response of `null` on any of the four endpoints would produce zero
findings from either drift probe and a false PASS — the exact "probe attests to something it
did not check" failure mode this same closure was built to eliminate, recurring in a case its
own 9-test regression lock does not cover. This is not a restatement of the original CR-01: the
original defect is fixed (confirmed above); this is a new defect in the replacement code,
independently corroborated by the fresh code review committed at `d4ee6e5`.

Recommend a second, narrowly-scoped closure plan (e.g. 30-07) before this phase is considered
fully closed for TYP-01's verification-harness reliability guarantee: replace the `is None` /
`payload is None` gates in `probe_field_type_map` and `probe_schema_snapshot` with `in raw_wire`
/ `not in raw_wire` membership tests, and add a null-body case to
`verification/test_main_iol_raw_wire_drift.py` so the regression lock actually covers the input
class that defeated it. This does not require touching any package source, any committed
baseline, or any published API — it is confined to `main_iol.py` and the one test file, exactly
as 30-06 was.

The phase's literal stated goal (typed attribute access, mypy catching a typo in the editor) is
unaffected by this gap and remains fully delivered — the residual issue is entirely within the
`main_iol.py` verification-harness tooling that this phase itself introduced to keep its own
drift signal honest, not within `iol-client`'s published API.

---

_Verified: 2026-08-20T22:45:21Z_
_Verifier: Claude (gsd-verifier)_
