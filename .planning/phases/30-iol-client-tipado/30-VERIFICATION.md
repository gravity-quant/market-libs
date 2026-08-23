---
phase: 30-iol-client-tipado
verified: 2026-08-23T21:41:50Z
status: passed
score: 8/8 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 7/8 must-haves verified
  gaps_closed:
    - "Truth 8 (crash-path fail-open BLOCKER) is closed. Independently re-derived by direct subprocess execution, not trusted from 30-12-SUMMARY.md's or 30-REVIEW.md's prose: `_redacted_excepthook` (main_iol.py:2103-2166) now wraps the call to `_redacted_exc(exc)` in a `try`/`except BaseException:` that binds the static module constant `_HOOK_RENDER_FAILED` (main_iol.py:2056, a fixed string with no expression referencing `exc`/`exc_type`/`tb`), and delegates emission to `_emit_crash_report(detail, tb)` (main_iol.py:2059-2100), whose two writes each sit in their own independent `contextlib.suppress(BaseException)` block. I reproduced the exact fifth-cycle trigger myself (monkeypatch `main_iol._redacted_exc` to raise inside a real subprocess, then raise `IOLAPIError(500, 'ZZ-SECRET-BODY-ZZ-cuenta-999999')`): stderr contained only `ABORT: el render de la excepción falló; detalle suprimido a propósito` plus static traceback frames — the marker was absent from both stdout and stderr, exit code was 1, and CPython's `Error in sys.excepthook:` banner never appeared. I then went further than the documented trigger and reproduced the *worst-case combined* scenario 30-REVIEW.md's CR-01 verdict names (renderer raises AND `sys.stderr.close()` called before the raise, which the review found makes CPython fall through to a `lost sys.stderr` path that dumps the exception's raw `repr` to fd 2 by a route no Python-level redaction can intercept): the marker was absent from both captured streams and the process still exited non-zero. Both reproductions ran against the actual current `main_iol.py`, not a synthetic source."
    - "The AST regression lock's cycle-5 durability gap (getattr(exc, \"message\"/\"args\", …), exc.__dict__, %-format and print-shaped census bypasses) is closed. Independently re-derived by calling the shipped detectors directly on the same synthetic sources the fifth cycle used: `_raw_exception_renders` now returns a non-empty offender list for `getattr(exc, \"message\", \"\")`, `str(getattr(exc, \"args\"))`, and `str(exc.__dict__)` (all three were `[]` before 30-13); `_declared_exception_renderers` now returns both names, in source order, for a synthetic `%`-format renderer and a synthetic `print(exc)`-shaped renderer (both were `['_redacted_exc']` only before 30-13). The negative controls that must stay unflagged (`getattr(exc, \"status_code\", None)`, `type(exc).__name__`) still return `[]`, and the real driver still returns `_raw_exception_renders == []` / `_declared_exception_renderers == ['_redacted_exc']` — zero false positives."
  gaps_remaining: []
  regressions:
    - "30-REVIEW.md's WR-04 finding is real, independently confirmed this cycle: `uv run mypy --strict verification/test_main_iol_exception_redaction.py main_iol.py` reports 6 errors (5× func-returns-value on `assert main_iol._redacted_excepthook(...) is None`, 1× attr-defined on `main_iol.traceback`). I confirmed by checking out the pre-30-12 tree (commit ee03b9b~1) and running the identical command that it was clean before 30-12 (`Success: no issues found in 2 source files`) — this is a genuine regression introduced by 30-12, not a pre-existing condition. It is invisible to CI as configured: `pyproject.toml`'s `[tool.mypy] files` list (line 97) covers only `packages/*/src`, `.pre-commit-config.yaml` scopes the mypy hook to `^packages/.*/src/`, and CI's two mypy jobs run `uv run mypy` (which honors `files`, confirmed clean: `Success: no issues found in 56 source files`) and `uv run mypy packages/$pkg/tests` per package — neither ever touches `main_iol.py` or `verification/`. Scored WARNING, not BLOCKER — see Anti-Patterns Found and the scope-judgment note below."
gaps: []
deferred: []
behavior_unverified_items: []
human_verification: []
---

# Phase 30: `iol-client` tipado Verification Report (sixth cycle, after 30-12 + 30-13 gap-closure)

**Phase Goal:** El consumidor de `iol-client` accede a cotizaciones, series históricas e instrumentos por **atributo tipado** — un typo lo caza mypy en el editor, no el servidor en producción.
**Verified:** 2026-08-23T21:41:50Z
**Status:** passed
**Re-verification:** Yes — sixth cycle, after gap-closure plans 30-12 (crash-path fail-closed BLOCKER) and 30-13 (AST lock durability, cycle-5 bypasses)

## Goal Achievement

### Scope note (read this first — continuing the established precedent)

The phase's **literal, roadmap-stated goal** — typed attribute access on `iol-client`'s public
surface (quotes, historical series, instruments), mypy catching a typo in the editor — is a
**published-package** concern (`packages/iol-client/`). That goal has been fully delivered since
plan 30-04 and is re-confirmed, unaffected, this cycle: `git diff --exit-code packages/` exits 0,
`mypy --strict packages/iol-client/src packages/iol-client/tests` reports `Success: no issues
found in 25 source files`, `ruff check` is clean, and the 242-test package suite passes.

Since cycle 2, this phase's own verification lineage has treated a second, self-declared guarantee
as an in-scope BLOCKER: that `main_iol.py` (the phase's live-verification driver, the vehicle
CLAUDE.md names as the mechanism to "detectar bugs... y corregirlos en el mismo ciclo") never leaks
an upstream wire value to any observable sink. **This sixth cycle continues that precedent**, per
the verification focus explicitly restated for this run, and is the cycle in which that guarantee
is found genuinely closed with no remaining phase-blocking gap.

**What this cycle independently re-derived, not trusted from any prior report:**

1. **Crash-path fail-open (prior truth 8, the fifth cycle's BLOCKER) is now closed.** I reproduced
   the fifth cycle's exact trigger by direct subprocess execution against the current `main_iol.py`
   (not by reading 30-12-SUMMARY.md's transcript): monkeypatching `_redacted_exc` to raise inside a
   subprocess that installs the hook and raises `IOLAPIError(500, "ZZ-SECRET-BODY-ZZ-cuenta-999999")`
   now produces stderr containing only the static placeholder and traceback frames — the marker is
   absent from both stdout and stderr, exit code is 1, and CPython's `Error in sys.excepthook:`
   banner never appears. I then reproduced 30-REVIEW.md's *worst-case combined* trigger myself
   (renderer raises **and** `sys.stderr.close()` is called before the raise) and confirmed the same
   clean result — the marker never reaches either captured stream under any trigger I tried,
   including the one the fresh code review used to certify CR-01 closed.
2. **The fifth cycle's AST-lock durability gap (getattr/`__dict__`/`%`-format/print-delegation
   bypasses) is closed.** I called the shipped detectors directly on the same synthetic sources the
   fifth cycle's report used and confirmed all four previously-`[]` cases now flag, while the two
   negative controls (`getattr(exc, "status_code", None)`, `type(exc).__name__`) and the real driver
   both stay clean.
3. **A fresh code review of the 30-12/30-13 changes (30-REVIEW.md) found new bypasses in the
   *newly-shipped* locks themselves, not in previously-fixed leaks.** I independently reproduced all
   four:
   - **WR-01** (crash-path structural lock): three realistic edits — sinks rewritten as
     `sys.stderr.write`/`flush` + `traceback.print_exception`, sinks extracted to unguarded helper
     functions, and a handler-less `try`/`finally` — all pass `_unguarded_crash_path_calls` as `[]`.
     Confirmed by calling the detector directly on all three synthetic edits.
   - **WR-02** (handler-site lock): `exc.__getattribute__("message")` passes `_raw_exception_renders`
     unflagged (`[]`), while the unbound spelling `object.__getattribute__(exc, "message")` is
     flagged. Confirmed by calling the detector directly on both spellings.
   - **WR-03**: only `sys.excepthook` is installed (`main_iol.py:2176`); `sys.unraisablehook`,
     `threading.excepthook` and asyncio's default loop exception handler remain unguarded. Confirmed
     by grep: zero occurrences of `unraisablehook`/`threading`/`set_exception_handler` in `main_iol.py`.
   - **WR-04**: `uv run mypy --strict verification/test_main_iol_exception_redaction.py main_iol.py`
     reports 6 errors, all on lines 30-12 added. I confirmed this is a genuine regression (not
     pre-existing) by checking out the pre-30-12 tree and running the identical command — clean. I
     also confirmed it is invisible to CI as configured — `pyproject.toml`'s mypy `files` and CI's two
     mypy jobs never touch `main_iol.py` or `verification/`.

   **All four are scored WARNING, not BLOCKER**, consistent with this phase's own established
   precedent: no live occurrence of any of the AST-lock bypasses (WR-01, WR-02) exists in `main_iol.py`
   today (confirmed: both detectors return `[]` / `['_redacted_exc']` against the real file); WR-03 is
   not reachable with an IOL-carrying payload today (`iol_client` spawns no threads, the driver creates
   no bare async tasks); WR-04 does not touch the crash-path's actual runtime behavior (which I
   independently reproduced as fail-closed under multiple triggers) or the published package, and is
   invisible to CI as configured, though it is a real, reproducible defect and is carried forward
   below as a recommended follow-up, not silently dropped.

### Observable Truths

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | `models.py` con modelos tipados de cotización/serie histórica/instrumentos, `puntas` polimórfico resuelto (SC1) | ✓ VERIFIED (regression) | `packages/iol-client/src/iol_client/models.py` present, `git diff --exit-code packages/` exits 0 this cycle — untouched since 30-04. |
| 2 | 16 firmas devuelven modelos, cero `Any`/`dict[str, Any]`, `mypy --strict` limpio, ruff verde (SC2) | ✓ VERIFIED | Re-ran this cycle: `mypy --strict packages/iol-client/src packages/iol-client/tests` → `Success: no issues found in 25 source files`; `ruff check packages/iol-client main_iol.py verification` → `All checks passed!`. |
| 3 | `main_iol.py` lee por atributo en sus 2 sitios reales; RED fixture prueba que un typo falla el typecheck (SC3) | ✓ VERIFIED (regression) | Unchanged since 30-04; `packages/` byte-identical this cycle. |
| 4 | `mercado`/`plazo` quedan `str`; ningún campo RESPONSE gana `Literal` (SC4) | ✓ VERIFIED (regression) | Unchanged since 30-04; `packages/` byte-identical this cycle. |
| 5 | `to_dict()` escape hatch en todos los modelos; README documenta la ruptura (SC5) | ✓ VERIFIED (regression) | Unchanged since 30-04. |
| 6 | `main_iol.py` never renders a caught exception's raw upstream body into the git-tracked findings file or the stdout auth-cascade detail | ✓ VERIFIED (regression) | `grep -c "actual=repr(exc)" main_iol.py` → 0; `grep -c "_redacted_exc(exc)" main_iol.py` → 33 this cycle (was 32; +1 is the new call inside the guarded `try` in `_redacted_excepthook`); `uv run pytest verification/test_main_iol_exception_redaction.py -q` → 64 passed. |
| 7 | The verification harness's finding-ID allocator never overwrites an OPEN finding or drops a FIXED one on the next run | ✓ VERIFIED (regression) | `main_iol.py:190-213` still defines `_seed_fid_counter()`; `main_iol.py:1941` still calls it before the first probe. `uv run pytest verification/test_main_iol_fid_seed.py verification/test_findings_fid_seed.py -q` → 12 passed, re-run this cycle. |
| 8 | `main_iol.py` never renders a raw exception body to any sink, including the uncaught/crash path (stderr/CI logs), **even when the redaction machinery itself fails partway through** | ✓ VERIFIED (closed this cycle) | Independently reproduced by direct subprocess execution against the live `main_iol.py`, under both the documented fifth-cycle trigger and 30-REVIEW.md's worst-case combined trigger (renderer raises + closed stderr): marker absent from both stdout and stderr in every case, exit code non-zero, CPython's excepthook-failure banner never appears. See `re_verification.gaps_closed` in the frontmatter for the full transcript. |

**Score:** 8/8 truths verified. All roadmap-stated success criteria (SC1-SC5) and all self-declared
`main_iol.py` leak-free guarantees (the finding-file/cascade leak closed in cycle 3, the fid-allocator
seeding closed in cycle 5, and the crash-path fail-open BLOCKER closed this cycle) are now met, each
independently re-derived rather than trusted from prior SUMMARYs.

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `packages/iol-client/src/iol_client/models.py` | typed models, `puntas` polymorphism resolved, `to_dict()` | ✓ VERIFIED | `git diff --exit-code packages/` exits 0 this cycle. |
| `packages/iol-client/src/iol_client/client.py` + `aio.py` | 16 typed signatures, no `Any`/`dict[str, Any]` returns | ✓ VERIFIED | mypy --strict clean; 242 tests pass. |
| `main_iol.py::_redacted_exc` + 33-site sweep | sole sanctioned exception-to-report renderer | ✓ VERIFIED | `grep -c "_redacted_exc(exc)"` → 33; 0 raw `repr(exc)`/`str(exc)`/`{exc}` renders file-wide. |
| `main_iol.py::_HOOK_RENDER_FAILED` + `main_iol.py::_emit_crash_report` + `main_iol.py::_redacted_excepthook` | crash path fails closed under a raising renderer and a broken/closed stderr, in either sink independently | ✓ VERIFIED | Structure confirmed by direct source read (main_iol.py:2056-2166); behavior confirmed by two independent subprocess reproductions this cycle (see truth 8). |
| `main_iol.py::_install_redacted_excepthook` | installs the redacted excepthook | ✓ VERIFIED, narrow scope | Installs `sys.excepthook` only. `sys.unraisablehook`/`threading.excepthook`/asyncio's default loop handler remain unguarded (WR-03) — not reachable today, carried forward as WARNING. |
| `main_iol.py::_fid_counter` seeding | seeded from `max_existing_fid(_PKG)` before allocating new fids | ✓ VERIFIED | `_seed_fid_counter()` present and correctly wired; regression suite (12 tests) passes. |
| `verification/test_main_iol_exception_redaction.py` (widened, post-30-13) | AST regression lock covering attribute reads, delegation, %-format, `getattr`-on-attribute-name, `__dict__`, generic census delegation; falsifiable renderer census; new structural lock on the crash-path guards | ✓ VERIFIED against cycle-5's gaps, ⚠️ new durability gaps found in the newly-added surface | Cycle-5's four bypasses (getattr message/args, `__dict__`, %-format/print census) are closed and independently confirmed. The two *new* detectors this cycle's plans shipped (`_unguarded_crash_path_calls` for the crash path, the `getattr`-attribute-name rule) have their own bypasses (WR-01, WR-02), independently reproduced — see Anti-Patterns Found. |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `main_iol.py` (33 caught-exception sites) | `.planning/verification/iol-client-findings.md` / stdout cascade | `_redacted_exc(exc)` | ✓ WIRED AND SAFE | Confirmed: 0 raw renders remain; all 33 sites route through the single helper. |
| `main_iol.py::main()` | `verification/findings.py::max_existing_fid` | `_seed_fid_counter()` called after `write_findings(_PKG)`, before the first probe | ✓ WIRED AND SAFE | Confirmed by direct read; unchanged since cycle 5. |
| `main_iol.py::_redacted_excepthook` (happy path) | `main_iol.py::_redacted_exc` -> stderr | direct call inside a `try` | ✓ WIRED AND SAFE | Subprocess test with a planted marker confirms stdout/stderr stay clean and exit code is non-zero. |
| `main_iol.py::_redacted_excepthook` (renderer-failure path) | `_HOOK_RENDER_FAILED` static placeholder -> `_emit_crash_report` -> stderr | `except BaseException:` binding the placeholder, then a guarded call | ✓ WIRED AND SAFE — closed this cycle | Independently reproduced by subprocess: monkeypatched `_redacted_exc` to raise, marker absent from both streams, banner absent, exit code non-zero. |
| `main_iol.py::_emit_crash_report` (sink-failure path) | stderr, guarded independently per sink | two separate `contextlib.suppress(BaseException)` blocks | ✓ WIRED AND SAFE — closed this cycle | Independently reproduced under the combined renderer-raise + closed-stderr trigger: no leak, non-zero exit. |
| `verification/test_main_iol_exception_redaction.py::_unguarded_crash_path_calls` | `main_iol.py` (source string) | AST-based structural lock, restricted to a 2-function region and a 3-callee allowlist | ⚠️ WIRED, INCOMPLETE COVERAGE | Zero false positives against the real file; but a call-name allowlist plus a handler-less-`try` acceptance bypasses the lock for 3 realistic edits (WR-01), independently reproduced this cycle. No live occurrence in the real driver. |
| `verification/test_main_iol_exception_redaction.py::_raw_exception_renders` (getattr rule) | `main_iol.py` (source string) | attribute-name adjudication, added in 30-13 | ⚠️ WIRED, INCOMPLETE COVERAGE | Closes the fifth cycle's `getattr(exc, "message", …)` gap, but the dunder spelling `exc.__getattribute__("message")` still passes unflagged (WR-02), independently reproduced this cycle. No live occurrence in the real driver. |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| TYP-01 | 30-01 … 30-13 | `iol-client` tipado — 16 firmas + `models.py` + acceso por atributo en driver, con verificación en vivo no-vacua | ✓ SATISFIED — both the published-API-level roadmap goal (SC1-SC5) and the phase's self-declared `main_iol.py` leak-free guarantee are met, with no remaining phase-blocking gap | `.planning/REQUIREMENTS.md` line 16's checkbox is flipped to `[x]` **by this verification cycle**, per the explicit deferral recorded in 30-09-SUMMARY.md deviation 3, 30-10-SUMMARY.md, 30-11-SUMMARY.md, 30-12-SUMMARY.md and 30-13-SUMMARY.md — all six declined to flip it and left the decision to "whichever verification cycle finds the crash-path guarantee genuinely closed with no remaining phase-blocking gap." This is that cycle. |

No orphaned requirements: `.planning/REQUIREMENTS.md` maps only TYP-01 to Phase 30; all 13 plans
(30-01 through 30-13) declare `requirements: [TYP-01]`.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| `verification/test_main_iol_exception_redaction.py` | `_CRASH_PATH_FUNCTIONS`/`_MUST_BE_GUARDED_CALLS` (~1961-1967), `_has_an_enclosing_guard` (~2021-2044) | New structural lock (30-12) decides coverage from two name allowlists and a guard-shape check that never asks whether the guard catches anything | ⚠️ WARNING | Three realistic edits (sinks rewritten as `write`/`flush`/`print_exception`; sinks extracted to unguarded helpers; a handler-less `try`/`finally`) all restore the CR-01 failure mode and pass `_unguarded_crash_path_calls` as `[]`, independently reproduced this cycle. Not a live leak today — confirmed `[]` against the real driver. |
| `verification/test_main_iol_exception_redaction.py` | rules 9/10 (~921-942), `_LEAKY_EXC_ATTRS` (~736) | `getattr`-on-attribute-name rule (30-13) does not cover the dunder spelling `exc.__getattribute__("message")` | ⚠️ WARNING | Same read as the now-flagged `getattr(exc, "message", …)`, still unflagged — `exc.message` is `resp.text` verbatim. Independently reproduced this cycle. Not a live leak today. |
| `main_iol.py` | `_install_redacted_excepthook` (2169-2176), module docstring (~60-66) | Only `sys.excepthook` is installed; `sys.unraisablehook`, `threading.excepthook`, asyncio's default loop exception handler remain unguarded sinks, while the docstring now unconditionally asserts the crash path "falla CERRADO" without naming this residual boundary | ⚠️ WARNING | Confirmed by grep: zero occurrences of `unraisablehook`/`threading`/`set_exception_handler` in `main_iol.py`. Not reachable today with an IOL-carrying payload (`iol_client` spawns no threads; the driver creates no bare async tasks). Carried forward unescalated across three review passes (30-REVIEW.md's WR-03), consistent with prior cycles' scoring. |
| `verification/test_main_iol_exception_redaction.py` | lines 1705, 1729, 1843, 1867, 1894, 1897 | `uv run mypy --strict verification/test_main_iol_exception_redaction.py main_iol.py` reports 6 errors, all on lines 30-12 added — confirmed a genuine regression (clean at the pre-30-12 commit under the identical command) | ⚠️ WARNING (regression, CI-invisible) | 5× `func-returns-value` (an `assert func(...) is None` on an always-`-> None` function — misleading style, not a logic bug) and 1× `attr-defined` (`main_iol.traceback` reached through the driver's namespace instead of a direct `import traceback` in the test). Invisible to every gate: `pyproject.toml`'s mypy `files` (line 97) and both CI mypy jobs never touch `main_iol.py` or `verification/`. Does not affect the crash-path's actual runtime behavior (independently reproduced fail-closed under multiple triggers this cycle) or the published package. |
| `.planning/REQUIREMENTS.md` | line 16 | `TYP-01` checkbox flipped `[ ]` → `[x]` by this verification | ℹ️ INFO | Deliberate action of this cycle, per the explicit deferral recorded across six prior plan SUMMARYs — see Requirements Coverage above. |

No `TBD`/`FIXME`/`XXX` debt markers found in `main_iol.py` or
`verification/test_main_iol_exception_redaction.py` (re-checked this cycle via grep, exit 1 / no matches).

Carried forward, not re-scored this cycle because none were escalated to BLOCKER: WR-04/WR-05/WR-06
from the fourth cycle's numbering (unanchored `str.replace` in `test_main_iol_fid_seed.py`, the AST
line-number-only seed wiring lock, a legitimately-zero `ultimoPrecio` producing a permanent OPEN
finding), IN-01 (container-wrapped names defeat the handler-site detector's call-argument rules),
IN-02 (the census annotation gate is a real, now-documented boundary), IN-03 (subprocess tests hand
the child process the operator's real credentials — now 3 copies of the pattern after 30-12), IN-04
(a crash-path test couples to repo source text via a substring match), and the older 30-09-SUMMARY.md
carry-forwards (probe-13 anti-vacuity, PASS-detail numeral, `DecodeScope` binding).

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| SC1-SC5 unaffected by 30-12/30-13 | `git diff --exit-code packages/` | exit 0 | ✓ PASS |
| `mypy --strict` clean on the published package | `uv run mypy packages/iol-client/src packages/iol-client/tests` | `Success: no issues found in 25 source files` | ✓ PASS |
| `ruff` clean | `uv run ruff check main_iol.py verification packages/iol-client` | `All checks passed!` | ✓ PASS |
| Package suite | `uv run pytest packages/iol-client -q` | `242 passed` | ✓ PASS |
| Exception-redaction contract (post-30-12/30-13) | `uv run pytest verification/test_main_iol_exception_redaction.py -q` | `64 passed` | ✓ PASS |
| Fid-seed + sibling suites | `uv run pytest verification/test_main_iol_fid_seed.py verification/test_findings_fid_seed.py verification/test_main_iol_raw_wire_drift.py verification/test_main_iol_uses_single_client_instance.py verification/test_main_drivers_bare_except.py -q` | `37 passed` | ✓ PASS |
| **Crash-path fail-closed reproduction (documented trigger)** | Subprocess: install hook, monkeypatch `_redacted_exc` to raise, raise `IOLAPIError(500, "ZZ-SECRET-BODY-ZZ-cuenta-999999")` | marker absent from stdout/stderr; banner absent; `ABORT: el render de la excepción falló; detalle suprimido a propósito` printed instead; exit code 1 | ✓ CLOSES PRIOR BLOCKER |
| **Crash-path fail-closed reproduction (worst-case combined trigger)** | Subprocess: renderer raises **and** `sys.stderr.close()` called before the raise | marker absent from both captured streams; exit code non-zero | ✓ CLOSES PRIOR BLOCKER |
| **Cycle-5 AST-lock bypass reproduction (now closed)** | `_raw_exception_renders`/`_declared_exception_renderers` called directly on the fifth cycle's synthetic sources (`getattr(exc, "message", "")`, `str(getattr(exc, "args"))`, `str(exc.__dict__)`, `%`-format census, `print(exc)` census) | all now flagged (previously `[]`) | ✓ CLOSES PRIOR WARNING |
| **WR-01 crash-path lock bypass reproduction** | `_unguarded_crash_path_calls` called directly on 3 synthetic realistic edits | `[]` (undetected) for all 3 | ⚠️ CONFIRMS NEW DURABILITY GAP (not a live leak) |
| **WR-02 `__getattribute__` bypass reproduction** | `_raw_exception_renders` called directly on `exc.__getattribute__("message")` vs. `object.__getattribute__(exc, "message")` | bound form `[]` (undetected); unbound form flagged | ⚠️ CONFIRMS NEW DURABILITY GAP (not a live leak) |
| **WR-04 mypy regression reproduction** | `uv run mypy --strict verification/test_main_iol_exception_redaction.py main_iol.py`, then the identical command against the pre-30-12 commit | 6 errors post-30-12; 0 errors pre-30-12 | ⚠️ CONFIRMS GENUINE, CI-INVISIBLE REGRESSION |
| No debt markers | `grep -nE "TBD\|FIXME\|XXX" main_iol.py verification/test_main_iol_exception_redaction.py` | no matches | ✓ PASS |
| Git working tree clean of unrelated changes | `git status --porcelain` | only this VERIFICATION.md (being rewritten) and REQUIREMENTS.md (checkbox flip), plus pre-existing untracked `.gsd/`/research cache | ✓ PASS |

### Probe Execution

Not applicable — this phase's verification surface is `main_iol.py`'s own named probes and the
`verification/test_main_iol_exception_redaction.py` / `test_main_iol_fid_seed.py` /
`test_main_iol_raw_wire_drift.py` offline regression locks, exercised directly above, plus this
cycle's own subprocess reproductions of the (now-closed) fail-open behavior and the (still-open,
WARNING-level) AST-lock bypasses. There are no `scripts/*/tests/probe-*.sh` conventional probes for
this phase.

### Human Verification Required

None required to resolve status. Every item in this cycle — both the closed crash-path BLOCKER and
the four open WARNING-level durability/regression items (WR-01 through WR-04) — is demonstrated by
direct, reproducible, automated execution, not a matter of taste or visual judgment.

### Gaps Summary

**No phase-blocking gap remains.** This is the first cycle since the fourth in which every truth is
✓ VERIFIED and no anti-pattern rises to 🛑 BLOCKER.

**The phase's literal, roadmap-stated goal — typed attribute access on `iol-client`'s published
surface (SC1-SC5) — remains fully achieved and is unaffected by 30-12 or 30-13.**
`packages/iol-client/` has been untouched since 30-04; mypy/ruff/pytest all re-confirmed clean this
cycle.

**The fifth cycle's crash-path fail-open BLOCKER (truth 8) is genuinely closed.** I reproduced it
myself against the live `main_iol.py`, not by reading 30-12-SUMMARY.md's or 30-REVIEW.md's prose:
the documented trigger (a monkeypatched renderer raising) and the fresh review's worst-case combined
trigger (renderer raising *and* a closed stderr, which the review found makes CPython fall through
to a route that dumps the exception's raw `repr` to fd 2 by a path no Python-level redaction can
intercept) both now produce zero leakage of the planted marker to either stream, with the process
still exiting non-zero. This closes a vulnerability class this phase's verification lineage has
escalated to BLOCKER on four separate prior occasions.

**The fifth cycle's AST-lock durability WARNING (getattr/`__dict__`/`%`-format/print-delegation
bypasses) is genuinely closed.** Independently confirmed by calling the widened detectors on the
same synthetic sources the fifth cycle used to demonstrate the gap.

**A fresh code review of 30-12's and 30-13's own new surface (30-REVIEW.md) found four new items,
all independently reproduced this cycle and all scored WARNING, not BLOCKER, per this phase's own
established precedent (no live leak in the real driver, or not reachable today):**

- **WR-01**: the new crash-path structural lock (`_unguarded_crash_path_calls`) has its own bypasses
  — three realistic edits (sink rewrite, helper extraction, handler-less `try`/`finally`) all pass
  it undetected.
- **WR-02**: the widened `getattr`-attribute-name rule has one residual spelling —
  `exc.__getattribute__("message")` — that walks past it while the unbound form is caught.
- **WR-03**: three of CPython's four exception sinks remain unguarded (`sys.unraisablehook`,
  `threading.excepthook`, asyncio's default loop handler), and the module docstring's new "falla
  CERRADO" claim (30-12) does not name this residual boundary. Not reachable today.
- **WR-04**: `uv run mypy --strict` reports 6 errors on lines 30-12 added to
  `verification/test_main_iol_exception_redaction.py`, confirmed as a genuine regression (clean
  before 30-12) and confirmed invisible to CI as configured. Does not affect the crash-path's actual
  runtime behavior or the published package.

**Scope judgment (explicit, per the task's ask, continuing and closing out the established
precedent).** Neither the roadmap's literal goal nor the phase's self-declared `main_iol.py`
leak-free guarantee has an open defect today. The four WARNING items above are, respectively: two
durability gaps in locks that were *just* shipped by this same gap-closure pair (consistent with how
cycles 4 and 5 scored the equivalent pre-existing-lock gaps — WARNING, not BLOCKER, when no live leak
exists); one residual-sink gap carried forward unescalated across three review passes because it is
not reachable with any payload the driver produces today; and one CI-invisible type-check regression
that does not touch runtime behavior. None of the four blocks the phase goal.

**`.planning/REQUIREMENTS.md`'s `TYP-01` checkbox is flipped to `[x]` by this verification cycle.**
Six consecutive plan SUMMARYs (30-08 through 30-13) explicitly declined to flip it and deferred the
decision to "whichever verification cycle finds the crash-path guarantee genuinely closed with no
remaining phase-blocking gap" — this is that cycle.

**Recommendation (non-blocking, optional follow-up):** a further plan (e.g. 30-14) could (a) invert
the crash-path lock's call-allowlist to a transitive-region rule per WR-01's suggested fix, (b) route
`__getattribute__`/`__getattr__` through the same attribute-name adjudication as `getattr` per WR-02's
suggested fix, (c) install the three remaining exception sinks or explicitly narrow the module
docstring's "falla CERRADO" claim to name the residual boundary (WR-03), and (d) either widen mypy's
`files` scope to include `main_iol.py` and `verification/`, or rewrite the six affected assertions to
avoid asserting on an always-`None` return value and use a direct `import traceback` instead of
reaching through `main_iol.traceback` (WR-04). None of these block Phase 31 or later phases from
proceeding.

---

_Verified: 2026-08-23T21:41:50Z_
_Verifier: Claude (gsd-verifier)_
