---
phase: 30-iol-client-tipado
verified: 2026-08-22T00:00:00Z
status: gaps_found
score: 6/7 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 6/7 must-haves verified
  gaps_closed:
    - "main_iol.py::_capture_raw_wire's except branch (the ONE site named by the 2026-08-21T15:30:00Z verification's gap) no longer reports actual=repr(exc). Independently re-derived in this cycle by direct source read: main_iol.py:336 now binds status_code = getattr(exc, \"status_code\", None) and line 346 reports actual=f\"{type(exc).__name__} status_code={status_code!r}\" — confirmed by grep (no `repr(exc)` inside the _capture_raw_wire function body, lines 237-346) and by running the new section-9 regression suite (`uv run pytest verification/test_main_iol_raw_wire_drift.py -q` -> 22 passed). This is exactly and only what plan 30-08's scope_boundary authorized ('main_iol.py — only _capture_raw_wire (its docstring and its except branch)') and exactly and only what the prior VERIFICATION.md's gap named ('main_iol.py::_capture_raw_wire reports the full upstream error response body')."
  gaps_remaining:
    - "The underlying vulnerability CLASS (rendering a caught exception's message/repr into a durable, git-tracked finding) is still live at 29 other call sites in main_iol.py (actual=repr(exc), all outside _capture_raw_wire) plus 2 related sites (_auth_failure_reason = f\"...: {exc}\", stdout-only, lower severity). This was NOT a regression introduced by 30-08 and was NOT something 30-08 failed to deliver — 30-08's own scope_boundary explicitly restricted modification to _capture_raw_wire only, matching the prior verification's narrowly-scoped gap. It is a genuinely broader, pre-existing defect of the same class, newly discovered and precisely scoped by the fresh 30-REVIEW.md code review (dated 2026-08-22, after 30-08 executed) and independently re-derived by direct source inspection in this cycle (not copied from 30-REVIEW.md's prose)."
  regressions: []
gaps:
  - truth: "main_iol.py contains NO call site, outside the now-fixed _capture_raw_wire, that renders a caught exception's message/repr/str into an append_finding argument written to the git-tracked .planning/verification/iol-client-findings.md — consistent with exceptions.py's T-29-36 invariant ('tipos y rutas, jamás un valor del wire') and CLAUDE.md's constraint against exposing sensitive data in reports."
    status: failed
    reason: >
      Independently re-derived in this cycle by direct source inspection (grep + manual read of
      three representative sites), not copied from 30-REVIEW.md's prose: main_iol.py still contains
      29 occurrences of `actual=repr(exc)` (lines 381, 416, 453, 468, 483, 540, 555, 570, 610, 628,
      646, 689, 707, 725, 759, 774, 789, 822, 837, 852, 899, 917, 935, 1024, 1042, 1060, 1572, 1587,
      1742) — an exact match to 30-REVIEW.md's CR-01 line list. Each is inside a probe's exception
      handler that calls append_finding, which writes verbatim into
      .planning/verification/iol-client-findings.md (confirmed git-tracked via `git ls-files`).
      packages/iol-client/src/iol_client/_core.py::raise_for_response (lines 114-127) constructs
      IOLAuthError/IOLRateLimitError/IOLAPIError with `resp.text` (the full upstream response body)
      as the `message` argument; IOLAPIError.__init__ (exceptions.py:13-15) does
      `super().__init__(f"[{status_code}] {message}")`, storing it in Exception.args — so
      `repr(exc)` at any of these 29 sites IS the upstream response body, prefixed by status.
      Manually inspected three of the named sites (probe_login_sync line 381, probe_refresh_token
      line 1587, probe_auth_401 line 1742) and confirmed each is a live, reachable except-branch
      feeding append_finding. This is the same mechanism, the same file, the same durable git-tracked
      sink that the prior verification cycle escalated to BLOCKER for the single _capture_raw_wire
      site — unaddressed at the other 29.

      Distinction from what 30-08 promised (explicit, per the task instructions): plan 30-08's own
      <scope_boundary> restricted modification to exactly "main_iol.py — only _capture_raw_wire (its
      docstring and its except branch)" and explicitly listed probe_field_type_map,
      probe_schema_snapshot, and _write_or_check_schema as forbidden-to-touch. The prior
      VERIFICATION.md's gap (2026-08-21T15:30:00Z) was itself narrowly worded to name only
      "main_iol.py::_capture_raw_wire". 30-08 fully and correctly closed exactly that narrow gap —
      its own must_haves and acceptance criteria were 100% met, confirmed by this cycle's regression
      run (22/22 tests passing, region gate `repr(` count == 0 inside _capture_raw_wire, positive
      gate `status_code` count == 5). This is NOT a 30-08 execution failure or an unmet 30-08
      promise. It IS a still-open phase-level gap: the broader vulnerability class this narrow fix
      was drawn from (rendering an exception's message into a durable git-tracked artifact) remains
      live elsewhere in the same file, discovered by 30-REVIEW.md's fresh review AFTER 30-08 was
      scoped and executed. The phase's own verification lineage (this gap's ancestor was escalated
      to BLOCKER in the prior cycle specifically because the sink is version-controlled/permanent,
      not because of which function emits it) and CLAUDE.md's file-wide constraint both apply to the
      whole driver, not to one function.

      Secondary, lower-severity, independently confirmed: 2 additional sites
      (`_auth_failure_reason = f"sync login: {exc}"` at line 371 and the async mirror at line 406)
      embed the same upstream 401 body into a variable that is NOT written to the git-tracked
      findings file (confirmed by tracing every consumer of `_auth_failure_reason`: all 13 consumers
      feed only `ProbeResult(...).detail`, and the only sink for `ProbeResult.detail` is
      `safe_print(...)` at line 1934 — stdout, not `append_finding`). This is real but is
      stdout-transient, not durable/git-tracked, so it does not independently trigger the BLOCKER
      tier; reported here as a WARNING-severity companion finding, matching 30-REVIEW.md's WR-02.
    artifacts:
      - path: "main_iol.py"
        issue: "29 sites (lines 381, 416, 453, 468, 483, 540, 555, 570, 610, 628, 646, 689, 707, 725, 759, 774, 789, 822, 837, 852, 899, 917, 935, 1024, 1042, 1060, 1572, 1587, 1742), each `actual=repr(exc)` inside an except-branch that calls append_finding, writing the exception's full args (which carry resp.text, the upstream error body) into the git-tracked .planning/verification/iol-client-findings.md."
      - path: "main_iol.py"
        issue: "2 sites (lines 371, 406), `_auth_failure_reason = f\"...: {exc}\"`, embed the upstream 401 body into a value later printed to stdout (via safe_print) for every downstream SKIPPED probe. Lower severity — not written to the git-tracked findings file — but the same root pattern."
    missing:
      - "Extract the redaction 30-08 wrote inline in _capture_raw_wire into a shared helper (e.g. `_redacted_exc(exc) -> str` returning `f\"{type(exc).__name__} status_code={getattr(exc, 'status_code', None)!r}\"`) and apply it at all 29 `actual=repr(exc)` sites plus the 2 `_auth_failure_reason` sites, replacing every raw exception render with the redacted form. Add a regression lock (e.g. a test that greps main_iol.py's source for `repr(exc)`/`str(exc)`/`{exc}` outside an explicitly allow-listed set, or a defense-in-depth check inside verification/findings.py that rejects unredacted exception-shaped values) so the pattern cannot silently return. 30-REVIEW.md's CR-01 supplies a concrete proposed fix and fix location list; this verification independently confirms the line numbers and mechanism but does not mandate 30-REVIEW.md's exact implementation."
deferred: []
human_verification: []
---

# Phase 30: `iol-client` tipado Verification Report (third re-verification, after 30-08 gap-closure)

**Phase Goal:** El consumidor de `iol-client` accede a cotizaciones, series históricas e instrumentos por **atributo tipado** — un typo lo caza mypy en el editor, no el servidor en producción.
**Verified:** 2026-08-22T00:00:00Z
**Status:** gaps_found
**Re-verification:** Yes — third cycle, after gap-closure plan 30-08

## Goal Achievement

### Observable Truths

Truths 1–5 and 7 are unaffected by 30-08 (which, per its own `<scope_boundary>`, touched only
`_capture_raw_wire` inside `main_iol.py` and `verification/test_main_iol_raw_wire_drift.py`); they
receive a regression check here. Truth 6 (drift-probe non-vacuity) is likewise unaffected — 30-08's
scope_boundary explicitly forbade touching `probe_field_type_map`, `probe_schema_snapshot`, and
`_write_or_check_schema` — confirmed by direct source read: those three functions are unchanged
since 30-07.

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | `models.py` con modelos tipados de cotización/serie histórica/instrumentos, `puntas` polimórfico resuelto (SC1) | ✓ VERIFIED (regression) | `git diff --exit-code packages/iol-client/src/iol_client/models.py` clean since 30-04; 30-08's scope_boundary explicitly forbids `packages/`; `git diff --exit-code packages/` exits 0 in this cycle. |
| 2 | 16 firmas devuelven modelos, cero `Any`/`dict[str, Any]`, `mypy --strict` limpio (SC2) | ✓ VERIFIED | `uv run mypy packages/iol-client/src packages/iol-client/tests` → `Success: no issues found in 25 source files` (re-run this cycle). `uv run ruff check packages/iol-client && uv run ruff format --check packages/iol-client` → clean. |
| 3 | `main_iol.py` lee por atributo en sus 2 sitios reales; RED fixture prueba que un typo falla el typecheck (SC3) | ✓ VERIFIED (regression) | `test_typed_surface_red.py` untouched by 30-08; the attribute-access consumption sites are outside `_capture_raw_wire`, the only function 30-08 was authorized to touch. |
| 4 | `mercado`/`plazo` quedan `str`; ningún campo RESPONSE gana `Literal` (SC4) | ✓ VERIFIED (regression) | `models.py` untouched; no `Literal` added by 30-08. |
| 5 | `to_dict()` escape hatch en todos los modelos; README documenta la ruptura incl. flip de truthiness (SC5) | ✓ VERIFIED (regression, documentation caveat carried forward, non-blocking) | `SafeModel.to_dict()` and README untouched by 30-08. Prior caveats (round-trip description, version-mismatch) still apply and remain non-blocking. |
| 6 | Los probes de drift (`probe_schema_snapshot`, `probe_field_type_map`) nunca son vacuos y nunca reportan PASS cuando la captura falló o el body no tiene la forma esperada, incluyendo un body capturado como JSON `null` (CR-01 post-closure, 30-04/30-06/30-07 must-have) | ✓ VERIFIED (regression) | Confirmed by direct source read: both functions byte-identical since 30-07 (30-08's scope_boundary forbade touching them). `uv run pytest verification/test_main_iol_raw_wire_drift.py -q` → 22 passed (17 pre-existing + 5 new section-9 cases), no regression in the null-body cases. |
| 7 | Ningún parser degrada silenciosamente ante una forma inesperada (CR-02, D-06/ASVS V5) | ✓ VERIFIED (regression) | `parse_get_instruments_by_type_response` untouched; `uv run pytest packages/iol-client -q` → `242 passed`, unchanged baseline. |

**Score:** 6/7 truths verified as narrowly scoped above. **This is not the full picture of the
phase's currently-open BLOCKER** — see below and the `gaps:` frontmatter. The BLOCKER from the
2026-08-21T15:30:00Z cycle was narrowly worded around `_capture_raw_wire` and is now genuinely
closed at that site (independently re-derived, not merely trusted from 30-08-SUMMARY.md). A fresh
code review (30-REVIEW.md, 2026-08-22, committed at `b31f3a0`) found — and this verification
independently re-derived via direct source inspection — that the SAME vulnerability class
(rendering a caught exception's message into a durable, git-tracked finding) is still live at 29
other call sites in the same file. This is reported as an explicit 8th observable truth in the
`gaps:` frontmatter (not folded into the 7-truth table above, because it was not one of the 7
truths any earlier verification cycle in this phase had defined) and drives the phase to
`gaps_found` regardless of the clean 7-truth regression table.

### Independent re-derivation of the CR-01 status (per task instructions)

Directly re-derived in this session, not copied from 30-REVIEW.md's claims:

```
$ grep -n "repr(exc)\|str(exc)\|{exc}" main_iol.py
371:        _auth_failure_reason = f"sync login: {exc}"
381:            actual=repr(exc),
406:        _auth_failure_reason = f"async login: {exc}"
416:            actual=repr(exc),
453/468/483/540/555/570/610/628/646/689/707/725/759/774/789/822/837/852/899/917/935/1024/1042/1060/1572/1587/1742:
            actual=repr(exc),
```

29 `actual=repr(exc)` occurrences (an exact match to 30-REVIEW.md CR-01's line list) + 2
`_auth_failure_reason = f"...: {exc}"` occurrences (matching 30-REVIEW.md WR-02). Inside
`_capture_raw_wire` (lines 237-346) `repr(` occurs **zero** times — confirmed by direct read and by
`inspect.getsource`-style grep on the function body alone — so the fix is real and scoped exactly to
that function, as 30-08 promised.

Manually opened three of the 29 sites end-to-end and traced them to a live `append_finding` call
writing to the git-tracked findings file:

- `main_iol.py:381` (`probe_login_sync`, inside `except IOLAuthError as exc:`) → `append_finding(..., actual=repr(exc), ...)`.
- `main_iol.py:1587` (`probe_refresh_token`, inside `except IOLAPIError as exc:`) → same pattern, fires after a live authenticated refresh call.
- `main_iol.py:1742` (`probe_auth_401`, inside `except Exception as exc:`) → same pattern, fires immediately after a deliberately-invalid-password login attempt.

Traced the leak mechanism at the package layer: `packages/iol-client/src/iol_client/_core.py:114-127`
(`raise_for_response`) constructs `IOLAuthError(resp.status_code, resp.text)` /
`IOLAPIError(resp.status_code, resp.text)`; `packages/iol-client/src/iol_client/exceptions.py:13-15`
(`IOLAPIError.__init__`) does `super().__init__(f"[{status_code}] {message}")`, so `resp.text` — the
full upstream response body — lands in `Exception.args`, and `repr(exc)` renders it verbatim.
Confirmed `.planning/verification/iol-client-findings.md` is git-tracked:

```
$ git ls-files .planning/verification/ | grep iol
.planning/verification/iol-client-findings.md
```

Confirmed `append_finding` (`verification/findings.py`) performs no redaction of its own —
`safe_print`'s `secrets=` list guards stdout only and is never consulted by `append_finding`.

**Conclusion, stated explicitly per the task's ask:** This is NOT a 30-08 execution failure. 30-08's
own `<scope_boundary>` restricted it to `_capture_raw_wire` only, and it fully delivered that,
verified by re-running its own acceptance gates in this cycle (22/22 tests, region gate 0, positive
gate 5). It IS a still-open, newly and more precisely scoped instance of the phase's own
previously-declared verification-harness security guarantee ("no upstream wire value crosses into a
git-tracked finding") — a guarantee this phase's verification lineage already treats as in-scope
(it blocked phase completion in the prior cycle), and which CLAUDE.md's project-wide constraint
("nunca... exponer credenciales en logs, reportes o tests") applies to the whole driver file, not
to one function. The phase is not done until this class is closed everywhere it appears, or the
scope is explicitly narrowed by the operator via an override.

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `main_iol.py::_capture_raw_wire` | redacted failure path: exception class + status_code only | ✓ VERIFIED | Lines 336, 346 confirmed by direct read; `repr(` count inside the function == 0; `status_code` count == 5 (getattr binding + f-string + 2 docstring mentions + 1 more). |
| `main_iol.py` (29 other `except`-branch sites) | same redaction discipline applied file-wide | ✗ MISSING (not addressed — out of 30-08's authorized scope, still open at the phase level) | 29 sites of `actual=repr(exc)` confirmed live and reachable, listed above. |
| `verification/test_main_iol_raw_wire_drift.py` | marker-leak regression cases for `_capture_raw_wire` | ✓ VERIFIED | `uv run pytest verification/test_main_iol_raw_wire_drift.py -q` → 22 passed (this cycle's own run, not merely trusted from SUMMARY.md). |
| `packages/` (all package source) | untouched by 30-08 | ✓ VERIFIED | `git diff --exit-code packages/` exits 0 in this cycle. |
| `.planning/verification/` (schema baselines + findings artifacts) | byte-unchanged by 30-08 | ✓ VERIFIED | `git diff --exit-code .planning/verification/` exits 0 in this cycle. |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `main_iol.py::_capture_raw_wire` (except branch) | `.planning/verification/iol-client-findings.md` (git-tracked) | `append_finding(..., actual=f"{type(exc).__name__} status_code={status_code!r}", ...)` | ✓ WIRED AND SAFE | Confirmed: only the exception class and a defensively-read `status_code` cross the boundary; the message (which carries `resp.text`) does not. |
| `main_iol.py` (29 other except branches, e.g. `probe_login_sync`, `probe_refresh_token`, `probe_auth_401`) | `.planning/verification/iol-client-findings.md` (git-tracked) | `append_finding(..., actual=repr(exc), ...)` | 🛑 WIRED BUT UNSAFE | Confirmed live and reachable at all 29 sites; `repr(exc)` embeds the full upstream response body via `Exception.args`. This is the open BLOCKER. |
| `main_iol.py:371,406` (`_auth_failure_reason`) | stdout (`safe_print`, line 1934) | 13 `ProbeResult(...).detail` consumers, traced end-to-end | ⚠️ WIRED, LOWER-SEVERITY UNSAFE | Confirmed: `_auth_failure_reason` never reaches `append_finding`/the git-tracked file — only `ProbeResult.detail` → `safe_print`. Real leak, but transient (stdout) rather than durable (git). |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| TYP-01 | 30-01 … 30-08 | `iol-client` tipado — 16 firmas + `models.py` + acceso por atributo en driver, con verificación en vivo no-vacua | ✓ SATISFIED at the published-API level (roadmap SC1-SC5, all regression-confirmed this cycle); ⚠️ the phase's own additionally-declared verification-harness reliability/security guarantee is now narrower-but-still-open | The stated phase goal (typed attribute access, mypy catching a typo in the editor) is fully delivered and confirmed unaffected by 30-08. The specific gap named by the prior verification cycle (`_capture_raw_wire`'s repr leak) is closed. A broader instance of the same class, discovered by the fresh code review after 30-08 was scoped, remains open at 29 other sites in `main_iol.py` and requires its own closure plan before this phase's verification-harness guarantee is fully closed. |

No orphaned requirements: `.planning/REQUIREMENTS.md` maps only TYP-01 to Phase 30 (line 16,
checked `[x]`); all 8 plans (30-01 through 30-08) declare `requirements: [TYP-01]`. The tracking
table (line 67) still shows TYP-01 as "Pending" despite the checkbox being marked done — a stale
tracking-table entry, carried forward unchanged from the prior cycle; cosmetic, not a coverage
problem.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| `main_iol.py` | 381, 416, 453, 468, 483, 540, 555, 570, 610, 628, 646, 689, 707, 725, 759, 774, 789, 822, 837, 852, 899, 917, 935, 1024, 1042, 1060, 1572, 1587, 1742 (29 sites) | `actual=repr(exc)` embeds the **full upstream error response body** into a finding written to `.planning/verification/iol-client-findings.md`, a **git-tracked** file | 🛑 BLOCKER (broader instance of the same class the prior verification cycle escalated for `_capture_raw_wire`; matches 30-REVIEW.md CR-01) | Independently confirmed in this cycle (grep + 3-site manual trace + package-layer trace to `_core.raise_for_response`/`IOLAPIError.__init__`). `probe_refresh_token` (1587) fires after a live authenticated call; `probe_auth_401` (1742) fires after a deliberately-invalid login attempt — both ordinary failure paths of a live verification run, not hypothetical. Contradicts `_capture_raw_wire`'s own docstring precedent, `exceptions.py`'s T-29-36 invariant, and CLAUDE.md's constraint against exposing sensitive data in reports. Explicitly out of 30-08's authorized scope (its `<scope_boundary>` restricted it to `_capture_raw_wire` only) — not a 30-08 defect, but a phase-level BLOCKER still requiring closure. |
| `main_iol.py` | 371, 406 | `_auth_failure_reason = f"...: {exc}"` embeds the upstream 401 body into a value printed to stdout (via `safe_print`) for every downstream SKIPPED probe | ⚠️ WARNING | Confirmed by tracing all 13 consumers to `ProbeResult.detail` → `safe_print` (stdout only, not the git-tracked findings file). `safe_print`'s `secrets=` list does not cover an arbitrary error body. Lower severity than the BLOCKER above because the sink is transient, not version-controlled. Matches 30-REVIEW.md WR-02. |
| `main_iol.py` | 336 (redaction over-applies to `IOLDecodeError`) | Reporting only `type(exc).__name__ status_code=None` for an `IOLDecodeError` discards its actionable, contractually-wire-safe fields (`field_path`, `declared_type`, `observed_type`, `model`) | ℹ️ INFO (not independently re-verified beyond reading 30-REVIEW.md's WR-03; latent, not on an everyday path since `_capture_raw_wire` runs no parser) | Not blocking; a future closure plan for the BLOCKER above should special-case `IOLDecodeError` per 30-REVIEW.md WR-03's proposal rather than blanket-redact it. |
| `.planning/REQUIREMENTS.md` | line 67 | Phase-tracking table still shows `TYP-01 \| Phase 30 \| ... \| Pending` while the requirement checkbox at line 16 is `[x]` | ℹ️ INFO | Stale, cosmetic, carried forward unchanged from the prior verification cycle. |

No `TBD`/`FIXME`/`XXX` debt markers found in `main_iol.py` or
`verification/test_main_iol_raw_wire_drift.py` (re-checked this cycle).

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| `_capture_raw_wire`'s own fix + regression suite | `uv run pytest verification/test_main_iol_raw_wire_drift.py -q` | `22 passed` | ✓ PASS |
| Package suite unchanged | `uv run pytest packages/iol-client -q` | `242 passed` | ✓ PASS |
| `mypy --strict` clean | `uv run mypy packages/iol-client/src packages/iol-client/tests` | `Success: no issues found in 25 source files` | ✓ PASS |
| `ruff`/`ruff format` clean | `uv run ruff check packages/iol-client main_iol.py verification && uv run ruff format --check packages/iol-client main_iol.py verification` | Clean, 72 files already formatted | ✓ PASS |
| Region gate: no exception rendering inside `_capture_raw_wire` | `grep -n "repr(" main_iol.py` filtered to lines 237-346 | 0 occurrences | ✓ PASS (confirms the narrow fix holds) |
| Positive gate: `repr(exc)` still present elsewhere in the file | `grep -c "actual=repr(exc)" main_iol.py` | `29` | 🛑 CONFIRMS OPEN BLOCKER |
| Scope containment | `git diff --exit-code packages/ .planning/verification/` | exits 0 | ✓ PASS |
| No debt markers | `grep -n -E "TBD\|FIXME\|XXX" main_iol.py verification/test_main_iol_raw_wire_drift.py` | no matches | ✓ PASS |

### Probe Execution

Not applicable — this phase does not use `scripts/*/tests/probe-*.sh` conventional probes; its
verification surface is `main_iol.py`'s own named probes and the
`verification/test_main_iol_raw_wire_drift.py` offline regression lock, exercised directly above.

### Human Verification Required

None required to resolve status. The BLOCKER, its scope-boundary origin, and the WARNING companion
finding are all demonstrated by direct code inspection, grep, and reproducible, credential-free
commands, not matters of taste or visual judgment.

### Gaps Summary

**Truth: `_capture_raw_wire`'s repr-leak (the specific site named by the prior verification cycle) —
CLOSED.** Independently re-derived in this cycle by direct source inspection (not copied from
30-08-SUMMARY.md): `main_iol.py:336,346` now bind and report only `status_code` and the exception
class; zero `repr(` occurrences remain inside the function; the region/positive gates and the full
22-test regression suite were re-run in this session and pass. 30-08 fully and correctly delivered
exactly what its own `<scope_boundary>` promised, and exactly what the prior verification's gap
named.

**New/broader BLOCKER — the same vulnerability class remains live at 29 other sites — OPEN, not in
30-08's authorized scope by design.** `30-REVIEW.md` (2026-08-22, committed at `b31f3a0`) discovered
that `actual=repr(exc)` is still present at 29 other `except`-branch sites across `main_iol.py`,
each wired to `append_finding` and therefore to the git-tracked
`.planning/verification/iol-client-findings.md`. This verification independently re-derived that
finding — the exact line list, the package-layer leak mechanism
(`_core.raise_for_response`/`IOLAPIError.__init__`), and a manual trace of three representative
sites (`probe_login_sync`, `probe_refresh_token`, `probe_auth_401`) — rather than trusting
30-REVIEW.md's prose. This is explicitly **not** a 30-08 failure: 30-08's own `<scope_boundary>`
restricted it to `_capture_raw_wire` only, mirroring the prior verification's narrowly-scoped gap
wording. It **is** a still-open phase-level defect, because the guarantee this phase's verification
lineage has been enforcing since the prior cycle ("no upstream wire value crosses into a git-tracked
finding via this driver") is a file-wide property under CLAUDE.md's constraint and `exceptions.py`'s
T-29-36 invariant, not a property scoped to one function. This routes the phase to `gaps_found` per
Step 9 rule 1 (blocker anti-pattern found), independent of the clean 7-truth regression table.

**Companion WARNING, independently confirmed** — `_auth_failure_reason` (lines 371, 406) embeds the
same upstream body but only reaches stdout via `safe_print`, never the git-tracked file. Reported for
completeness; does not independently drive the status.

**Recommendation:** a further narrowly-scoped closure plan (e.g. 30-09), extending the exact pattern
30-08 already validated (`status_code = getattr(exc, "status_code", None)`;
`actual=f"{type(exc).__name__} status_code={status_code!r}"`) — ideally factored into one shared
helper this time, given the pattern now needs to hold at 31 sites rather than 1 — to all remaining
`actual=repr(exc)` sites and the two `_auth_failure_reason` sites, plus a file-wide regression lock
(source-grep test or a defense-in-depth guard in `verification/findings.py`) so the pattern cannot
silently return at a 32nd site in the future. `30-REVIEW.md`'s CR-01 section supplies a concrete
starting point for the fix and the lock; this verification does not mandate its exact
implementation, only its scope.

The phase's literal stated goal (typed attribute access, mypy catching a typo in the editor) remains
fully delivered and is unaffected by either the closed narrow gap or the newly-scoped broader
BLOCKER — both are confined to `main_iol.py`'s verification-harness tooling, not to `iol-client`'s
published API.

---

_Verified: 2026-08-22T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
