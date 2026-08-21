---
phase: 30-iol-client-tipado
verified: 2026-08-21T15:30:00Z
status: gaps_found
score: 6/7 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 6/7 must-haves verified
  gaps_closed:
    - "Truth 6 / CR-01 (post-closure) — a captured JSON `null` body was indistinguishable from a failed capture, so probe_field_type_map and probe_schema_snapshot both reported PASS with zero findings on a legitimate 200-OK null response. Closed by plan 30-07: the three `is None`/`payload is None` gates inside both probes were replaced with `key in raw_wire`/`key not in raw_wire` dict-membership tests. Independently re-derived in this cycle (not copied from 30-07-SUMMARY.md): direct source read confirms `\"get_quote\" in raw_wire`, `\"get_historical_quotes\" in raw_wire`, `\"get_instruments_by_type\" in raw_wire` gates in `probe_field_type_map` (lines 1215, 1232, 1287) and `if func_name not in raw_wire: skipped.append(...)` in `probe_schema_snapshot` (line 1470). A live reproduction run against the actual `main_iol.py` module in this session — not the offline test suite — fed `{'get_quote': None, 'get_historical_quotes': None, 'get_instruments': None, 'get_instruments_by_type': None}` into `probe_field_type_map` and got `status=FINDING` with exactly 3 recorded SHAPE findings (each `actual='type=NoneType'`), and fed `{}` and got `status=PASS` with 0 findings — confirming both directions independent of the pytest fixtures. `uv run pytest verification/test_main_iol_raw_wire_drift.py -v` → 17/17 passed, including the 3 previously-red null-body cases."
  gaps_remaining: []
  regressions: []
gaps:
  - truth: "main_iol.py::_capture_raw_wire reports the full upstream error response body (via actual=repr(exc)) into a git-tracked findings file when a live capture fails, contradicting the function's own docstring, exceptions.py's T-29-36 invariant, and CLAUDE.md's constraint against exposing sensitive data in logs/reports."
    status: failed
    reason: >
      Independently confirmed in this cycle: main_iol.py:330 still reads
      \; repr() on an IOLAPIError embeds resp.text (the full
      upstream error body) verbatim via Exception.args. git ls-files
      .planning/verification/ confirms iol-client-findings.md is tracked, so the
      next live capture failure writes that body permanently into git history.
      Escalated from WARNING (prior verification cycle) to BLOCKER by the fresh
      30-REVIEW.md code review on the grounds that the sink is version-controlled
      (permanent/distributed exfiltration, not transient stdout); this
      verification independently concurs. Explicitly out of 30-07's authorized
      scope by design (its scope_boundary forbids touching _capture_raw_wire) —
      not a regression introduced by 30-07, but a pre-existing, live, reachable
      defect that was not yet closed by any plan.
    artifacts:
      - path: "main_iol.py"
        issue: "Line 330 (_capture_raw_wire except branch): actual=repr(exc) embeds the full upstream error response body into a finding written to a git-tracked file."
    missing:
      - "Replace actual=repr(exc) with type(exc).__name__ plus getattr(exc, 'status_code', None), never the exception message/args. Add an offline test asserting no append_finding kwarg from this code path contains a response-body marker string (feed a mocked failure with a marker string in the body, assert the marker appears in no recorded kwarg). 30-REVIEW.md's CR-01 (this cycle) supplies the exact proposed fix."
deferred: []
human_verification: []
---

# Phase 30: `iol-client` tipado Verification Report (second re-verification, after 30-07 gap closure)

**Phase Goal:** El consumidor de `iol-client` accede a cotizaciones, series históricas e instrumentos por **atributo tipado** — un typo lo caza mypy en el editor, no el servidor en producción.
**Verified:** 2026-08-21T15:30:00Z
**Status:** gaps_found
**Re-verification:** Yes — second cycle, after gap-closure plan 30-07

## Goal Achievement

### Observable Truths

Truths 1–5 and 7 are unaffected by 30-07 (which touched only `main_iol.py` and
`verification/test_main_iol_raw_wire_drift.py`) and were already independently
re-derived in the prior cycle; they receive a regression check here. Truth 6 is
fully re-derived because it is 30-07's target.

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | `models.py` con modelos tipados de cotización/serie histórica/instrumentos, `puntas` polimórfico resuelto (SC1) | ✓ VERIFIED (regression) | `git diff --exit-code packages/iol-client/src/iol_client/models.py` clean since 30-04; untouched by 30-05/30-06/30-07. |
| 2 | 16 firmas devuelven modelos, cero `Any`/`dict[str, Any]`, `mypy --strict` limpio (SC2) | ✓ VERIFIED | `uv run mypy packages/iol-client/src packages/iol-client/tests` → `Success: no issues found in 25 source files`. `uv run ruff check packages/iol-client && uv run ruff format --check packages/iol-client` → clean. |
| 3 | `main_iol.py` lee por atributo en sus 2 sitios reales; RED fixture prueba que un typo falla el typecheck (SC3) | ✓ VERIFIED (regression) | `test_typed_surface_red.py` untouched by 30-05/30-06/30-07; the attribute-access consumption sites are outside `probe_field_type_map`/`probe_schema_snapshot`/`_capture_raw_wire`, which is all 30-07 touched. |
| 4 | `mercado`/`plazo` quedan `str`; ningún campo RESPONSE gana `Literal` (SC4) | ✓ VERIFIED (regression) | `models.py` untouched; no `Literal` added by 30-07. |
| 5 | `to_dict()` escape hatch en todos los modelos; README documenta la ruptura incl. flip de truthiness (SC5) | ✓ VERIFIED (documentation caveat carried forward, non-blocking) | `SafeModel.to_dict()` and README untouched by 30-07. Prior caveats (WR-05 round-trip description, WR-09 version mismatch v0.3.0 vs `__version__`/`pyproject.toml` 0.2.0) still apply and remain non-blocking documentation warnings, unaffected by this closure round. |
| 6 | Los probes de drift (`probe_schema_snapshot`, `probe_field_type_map`) nunca son vacuos y nunca reportan PASS cuando la captura falló o el body no tiene la forma esperada — **incluyendo un body capturado como JSON `null`** (CR-01, 30-04/30-06/30-07 must-have) | ✓ VERIFIED | **Independently re-derived, not copied from 30-07-SUMMARY.md.** Direct source read of `main_iol.py` confirms all three former `is None`/`payload is None` gates are now `in raw_wire`/`not in raw_wire` membership tests (lines 1215, 1232, 1287, 1470). A fresh interpreter session in this verification (not the test suite) fed an all-null 4-endpoint `raw_wire` into the live `probe_field_type_map` and got `status=FINDING`, 3 recorded SHAPE findings, each `actual='type=NoneType'`; fed `{}` and got `status=PASS`, 0 findings, `detail='0 endpoints checked (ninguno), no drift'` — both directions hold. `uv run pytest verification/test_main_iol_raw_wire_drift.py -v` → **17 passed** (9 original + 8 new), including the 3 cases that were red pre-fix. The 3 original CR-01 drift classes (type-drift/added-key/removed-key) remain detected — no regression. |
| 7 | Ningún parser degrada silenciosamente ante una forma inesperada (CR-02, D-06/ASVS V5) | ✓ VERIFIED (regression) | `parse_get_instruments_by_type_response` untouched by 30-07 (`git diff --exit-code packages/` since 30-05 exits 0). `uv run pytest packages/iol-client -q` → `242 passed`, unchanged baseline. |

**Score:** 6/7 truths verified (roadmap's 5 SCs are fully satisfied; the phase's
own additionally-declared verification-harness reliability truth, CR-01, is now
fully closed for the null-body input class). **The 7th slot is not a truth
failure — it is a newly-escalated BLOCKER anti-pattern** (see below) discovered
by the fresh code review and independently confirmed in this cycle, which the
decision tree (Step 9, rule 1) routes to `gaps_found` regardless of the clean
truths table.

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `main_iol.py::probe_field_type_map` | 3 predicates gated by `in raw_wire` instead of `is not None` | ✓ VERIFIED | Confirmed at lines 1215, 1232, 1287 by direct read; `checked` list (line 1362-1366) already used membership, so gate and detail predicate are now the same expression. |
| `main_iol.py::probe_schema_snapshot` | loop head gated by `func_name not in raw_wire` instead of `payload is None` | ✓ VERIFIED | Confirmed at line 1470: `if func_name not in raw_wire: skipped.append(func_name); continue`. `payload = raw_wire[func_name]` only binds after the membership check passes. |
| `verification/test_main_iol_raw_wire_drift.py` | null-body regression cases for both probes | ✓ VERIFIED (present, wired) but **2 of the 5 new tests are weak** | 337 → 549 lines. 17 test functions collected and passing. Tests 1–3 (the actual RED→GREEN cases) are sound and independently reproduced above. Tests 4–5 have quality defects — see Anti-Patterns. |
| `main_iol.py::_capture_raw_wire` | absent-on-failure contract, unmodified per scope boundary | ✓ VERIFIED (unmodified) with a pre-existing BLOCKER | `git diff main_iol.py` (30-07 commits) touches only `probe_field_type_map` and `probe_schema_snapshot`; `_capture_raw_wire` (lines 237-339) is byte-identical to its 30-06 state. However, its `except` branch still reports `actual=repr(exc)` — see CR-01 (repr leak) below, out of 30-07's scope but present and BLOCKER-severity. |
| `.planning/verification/schemas/iol-client/*.json` | 4 baselines byte-identical | ✓ VERIFIED | `git diff --exit-code .planning/verification/schemas/` exits 0. |
| `packages/` (all package source) | untouched by 30-07 | ✓ VERIFIED | `git diff --exit-code packages/` exits 0 in the working tree; `git diff --stat` of the 30-07 commit range lists only `main_iol.py`, `verification/test_main_iol_raw_wire_drift.py`, and the SUMMARY doc. |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `main_iol.py::probe_field_type_map` | `raw_wire` dict | `"get_quote"/"get_historical_quotes"/"get_instruments_by_type" in raw_wire` | ✓ WIRED | Confirmed by direct source read and live reproduction: a captured-null endpoint now reaches its existing `isinstance` shape check, which fails and emits a SHAPE finding. |
| `main_iol.py::probe_schema_snapshot` | `main_iol.py::_write_or_check_schema` | membership gate at the loop head, unmodified helper | ✓ WIRED | Membership decides reachability before `_write_or_check_schema` is ever called; `schema_of(None) == "NoneType"` differs from every committed baseline, producing the SHAPE finding. Helper itself confirmed unmodified. |
| `main_iol.py::_capture_raw_wire` (except branch) | `.planning/verification/iol-client-findings.md` (git-tracked) | `append_finding(..., actual=repr(exc), ...)` | 🛑 WIRED BUT UNSAFE | Confirmed live: `repr(exc)` on an `IOLAPIError` embeds the full upstream response body (`resp.text`, per `_core.raise_for_response`) verbatim into `Exception.args`, and `append_finding` performs no redaction. `git ls-files .planning/verification/` confirms `iol-client-findings.md` is tracked; the current committed content happens to be clean, but the code path is live and reachable on the next capture failure. See CR-01 (repr leak) below. |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| TYP-01 | 30-01 … 30-07 | `iol-client` tipado — 16 firmas + `models.py` + acceso por atributo en driver, con verificación en vivo no-vacua | ✓ SATISFIED at the published-API level (roadmap SC1-SC5); ⚠️ the phase's own additionally-declared verification-harness reliability/security guarantee carries one open BLOCKER | The stated phase goal — typed attribute access, mypy catching a typo in the editor — is fully delivered and confirmed unaffected by 30-07. The CR-01 null-body vacuity gap (this phase's own self-declared closure target) is now fully closed. A separate, newly-escalated BLOCKER (repr(exc) leaking upstream response bodies into a git-tracked findings file) was surfaced by the fresh code review and independently confirmed live in this cycle; it predates 30-07, is explicitly out of 30-07's authorized scope, and requires its own narrow closure plan before TYP-01's verification-harness guarantee is fully closed. |

No orphaned requirements: `.planning/REQUIREMENTS.md` maps only TYP-01 to Phase
30 (line 16, checked `[x]`); all 7 plans (30-01 through 30-07) declare
`requirements: [TYP-01]`. Note: REQUIREMENTS.md's tracking table (line 67)
still shows TYP-01 as "Pending" despite the checkbox above being marked done —
a stale tracking-table entry, not a scope or coverage problem; flagged as INFO
below.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| `main_iol.py` | 330 (`_capture_raw_wire` except branch) | `actual=repr(exc)` embeds the **full upstream error response body** (via `IOLAPIError.__str__`/`Exception.args`, sourced from `resp.text` in `_core.raise_for_response`) into a finding written to `.planning/verification/iol-client-findings.md`, a **git-tracked** file | 🛑 BLOCKER (escalated from prior WARNING; matches 30-REVIEW.md CR-01, this cycle) | Independently confirmed in this verification: `git ls-files .planning/verification/` proves the sink is tracked, so a triggered capture failure during any future live run of `main_iol.py` (auth failure, rate limit, malformed response, any exception surfacing an upstream body such as an account/instrument identifier) writes that body permanently into git history on the next commit. This directly contradicts (a) the function's own docstring ("el body crudo alimenta `schema_of` y nada más"), (b) `exceptions.py`'s own stated invariant ("tipos y rutas, jamás un valor del wire" — T-29-36), and (c) CLAUDE.md's explicit constraint ("nunca... exponer credenciales en logs, reportes o tests"). Explicitly out of 30-07's authorized scope (its `<scope_boundary>` forbids touching `_capture_raw_wire`) and not expected to be fixed by that plan — but it is a currently-live, reachable code path, not a hypothetical, and it fails the project's own security constraint. Recommend a narrowly-scoped closure plan (e.g. 30-08) reporting `type(exc).__name__` and `status_code` only, per the fix already drafted in `30-REVIEW.md`. |
| `verification/test_main_iol_raw_wire_drift.py` | 529-549 (`test_probe_field_type_map_pass_detail_never_names_an_uncaptured_endpoint`) | Tautological assertion — cannot fail for the reason its docstring claims | ⚠️ WARNING (confirmed independently, not merely trusted from 30-REVIEW.md WR-01) | **Reproduced live in this verification** against the pre-30-07 `main_iol.py` (checked out from commit `b12c4d4^`): feeding the exact pathological null-body input (`{"get_quote": None, "get_historical_quotes": None, "get_instruments_by_type": None}`) into the *pre-fix* `probe_field_type_map` returns `PASS` with detail naming all three endpoints — the exact defect the test's docstring says it prohibits — yet `named = [n for n in _FIELD_MAPPED_ENDPOINTS if n in result.detail]` evaluates to all three names, and `all(name in raw_wire for name in named)` evaluates `True` even on this broken pre-fix output, because the `checked`/`named` list was already built by a membership test (`if name in raw_wire`) *before* 30-07 — only the per-check gates were `is not None`. The test's only failure mode is `result.status == "PASS"`, and none of its 4 parametrized cases (`{}`, single clean body, clean+empty-series, non-field-mapped endpoint) include a null-bodied input, so it never exercises that branch either. It currently passes, adds no coverage beyond what tests 1–3 already lock, and would give false confidence if read as "proves the PASS-detail truthfulness invariant." |
| `verification/test_main_iol_raw_wire_drift.py` | 488-509 (`test_absent_capture_is_still_distinguishable_from_a_null_body`) | Pins a known, separate pre-existing defect as a permanent invariant | ⚠️ WARNING (confirmed independently, not merely trusted from 30-REVIEW.md WR-02) | **Reproduced by direct source read of `main_iol.py`**: `probe_schema_snapshot`'s signature (`main_iol.py:1424`) takes `(client, today, raw_wire)` — no `capture_fids` parameter, unlike `probe_field_type_map` which takes one and seeds `finding_fids` with it. So on `raw_wire == {}` (all four captures failed in a live run), probe 13 has no anti-vacuity seeding and returns `PASS` having verified zero snapshots — a real, separate gap (probe 12 has this protection, probe 13 does not). The test at line 504-505 asserts `snapshot.status == "PASS"` for exactly this input, cementing the gap as a locked invariant: a future fix threading `capture_fids` into probe 13 (the natural fix, mirroring probe 12) would break this test. A secondary defect in the same test (lines 506-507, `assert name in snapshot.detail` — substring matching where `"get_instruments"` is a prefix of `"get_instruments_by_type"`) is a fragile pattern the sibling test at line 458-460 explicitly avoids by using exact set equality; it does not currently produce a false pass in this test's 4-baseline all-present usage, but the pattern itself is the "same hazard" WR-02 names. |
| `.planning/REQUIREMENTS.md` | line 67 | Phase-tracking table still shows `TYP-01 \| Phase 30 \| ... \| Pending` while the requirement checkbox at line 16 is marked `[x]` (done) | ℹ️ INFO | Stale tracking-table row, not a coverage gap — the requirement's substantive checkbox and description are correctly marked complete. Cosmetic; does not affect this verification's coverage determination. |

No `TBD`/`FIXME`/`XXX` debt markers found in `main_iol.py` or
`verification/test_main_iol_raw_wire_drift.py`.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Full regression lock, including 8 new 30-07 cases | `uv run pytest verification/test_main_iol_raw_wire_drift.py -v` | `17 passed` | ✓ PASS |
| Package suite unchanged | `uv run pytest packages/iol-client -q` | `242 passed` | ✓ PASS |
| `mypy --strict` clean | `uv run mypy packages/iol-client/src packages/iol-client/tests` | `Success: no issues found in 25 source files` | ✓ PASS |
| `ruff`/`ruff format` clean | `uv run ruff check packages/iol-client main_iol.py verification && uv run ruff format --check packages/iol-client main_iol.py verification` | Clean | ✓ PASS |
| **Live null-body reproduction against the actual `main_iol.py` module (not the test suite)** | inline python, this verification session, all 4 endpoints `None` | `probe_field_type_map` → `FINDING`, 3 recorded SHAPE findings, each `actual='type=NoneType'` | ✓ PASS (confirms Truth 6 closed) |
| **Live absence reproduction** | inline python, this verification session, `raw_wire={}` | `probe_field_type_map` → `PASS`, `detail='0 endpoints checked (ninguno), no drift'`, 0 findings | ✓ PASS (confirms discrimination holds both directions) |
| **WR-01 (test tautology) falsification, against actual pre-fix code checked out from `b12c4d4^`** | inline python in a detached read of the pre-fix source | Pathological PASS reproduced (`3 endpoints checked...`); the test's own assertion (`all(name in raw_wire for name in named)`) evaluates `True` even on this broken output | ✓ CONFIRMED WR-01 accurate |
| **WR-02 (probe 13 anti-vacuity gap) confirmation** | `grep -n "def probe_schema_snapshot" main_iol.py` + signature read | `def probe_schema_snapshot(client, today, raw_wire)` — no `capture_fids` param | ✓ CONFIRMED WR-02 accurate |
| **CR-01 (repr leak) confirmation** | direct source read + `git ls-files .planning/verification/` | `actual=repr(exc)` present at `main_iol.py:330`; `.planning/verification/iol-client-findings.md` confirmed tracked | ✓ CONFIRMED BLOCKER live and reachable |
| Scope containment | `git diff --stat` of 30-07 commit range (`c552e74`..`81d059d`) | `main_iol.py`, `verification/test_main_iol_raw_wire_drift.py`, `30-07-SUMMARY.md` only | ✓ PASS |
| No package/baseline drift | `git diff --exit-code packages/ .planning/verification/schemas/` | exits 0 | ✓ PASS |

### Probe Execution

Not applicable — this phase does not use `scripts/*/tests/probe-*.sh` conventional
probes; its verification surface is `main_iol.py`'s own named probes and the
`verification/test_main_iol_raw_wire_drift.py` offline regression lock, both
exercised directly above (including a live reproduction against the actual
module, not solely the test suite).

### Human Verification Required

None required to resolve status. All findings in this cycle — the null-body
closure, the repr(exc) leak, and the two test-quality warnings — are
demonstrated by direct code inspection and reproducible, credential-free
interpreter sessions, not matters of taste or visual judgment.

### Gaps Summary

**Truth 6 / CR-01 (null-body vacuity) — CLOSED.** Independently re-derived in
this cycle by direct source inspection and a fresh live reproduction against the
actual `main_iol.py` module (not merely re-running the pytest suite, and not
copied from 30-07-SUMMARY.md): both drift probes now gate on `raw_wire`
key-membership rather than value-identity against `None`, a captured JSON `null`
body now produces `FINDING` with the correct finding counts (3 from
`probe_field_type_map`, corroborated for `probe_schema_snapshot` via its 4/4
passing dedicated test plus direct source read of its now-membership-gated loop
head), and a genuinely absent capture still correctly routes to `PASS`/`skipped`.
No regression in the three original CR-01 drift classes or in the CR-02 guards.
This gap, open since the first re-verification cycle, is resolved.

**New BLOCKER — CR-01 (repr leak, this cycle's naming) — OPEN, not closed by
30-07 (correctly, by design — out of its scope boundary).** `_capture_raw_wire`'s
exception handler reports `actual=repr(exc)`, which embeds the full upstream
error response body into a finding written to a **git-tracked** file
(`.planning/verification/iol-client-findings.md`, confirmed tracked via
`git ls-files`). This was rated a WARNING in the prior verification cycle;
30-REVIEW.md's fresh review re-classified it as a BLOCKER on the grounds that
the sink is version-controlled (permanent, distributed exfiltration on push,
unlike transient stdout) — a classification this verification independently
concurs with, given CLAUDE.md's explicit constraint against exposing
credentials/sensitive data in logs, reports, or tests, and the project's own
exception-design invariant (T-29-36: "tipos y rutas, jamás un valor del wire").
The code path is live and reachable — not hypothetical — on the next capture
failure during any live run of `main_iol.py`. This routes the phase to
`gaps_found` per Step 9 rule 1 (blocker anti-pattern found), independent of the
clean truths table.

**Two test-quality warnings, independently verified rather than trusted from
30-REVIEW.md's prose** — both confirmed accurate by direct reproduction in this
cycle:
- `test_probe_field_type_map_pass_detail_never_names_an_uncaptured_endpoint` is
  tautological (its assertion holds even on the pre-fix pathological PASS,
  because the `checked`/`named` predicate was already membership-based before
  30-07; only the per-check gates were identity-based). It currently passes and
  adds no coverage beyond tests 1–3.
- `test_absent_capture_is_still_distinguishable_from_a_null_body` cements a
  separate, real, pre-existing gap (probe 13 has no `capture_fids` anti-vacuity
  seeding, unlike probe 12) as a permanent invariant, which will make a future
  correct fix of that gap fail this test.

Neither test-quality warning blocks this verification's status on its own — the
underlying functional fix (null-body discrimination) was independently
re-derived via direct source reading and a live reproduction against the actual
module, not solely via these two tests. They are reported as WARNING-severity
findings for a follow-up plan to strengthen (per 30-REVIEW.md's proposed
fixes), not as reasons the fix itself is unproven.

**Recommendation:** a further narrowly-scoped closure plan (e.g. 30-08),
confined to `main_iol.py`'s `_capture_raw_wire` exception handler (report
`type(exc).__name__` + `status_code` only, never `repr(exc)`) plus an offline
test asserting no `append_finding` kwarg from that path contains a response-body
marker string. This does not require touching `packages/`, any committed
baseline, or the published API — the same containment discipline 30-06 and
30-07 both followed. The two test-quality warnings can be folded into the same
plan or a lighter follow-up, at the operator's discretion — they are not
BLOCKER-severity.

The phase's literal stated goal (typed attribute access, mypy catching a typo in
the editor) remains fully delivered and is unaffected by either the closed gap
or the new BLOCKER — both are confined to the `main_iol.py` verification-harness
tooling this phase introduced to keep its own drift signal honest, not to
`iol-client`'s published API.

---

_Verified: 2026-08-21T15:30:00Z_
_Verifier: Claude (gsd-verifier)_
