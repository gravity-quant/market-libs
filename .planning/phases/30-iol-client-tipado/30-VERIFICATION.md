---
phase: 30-iol-client-tipado
verified: 2026-08-23T19:30:00Z
status: gaps_found
score: 7/8 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 6/8 must-haves verified
  gaps_closed:
    - "Truth 7 (fid-counter allocator seeding) is closed. Independently re-derived, not copied from 30-REVIEW.md's or 30-10-SUMMARY.md's prose: `main_iol.py:175` still declares `_fid_counter: int = 0`, but `main_iol.py:183-206` now defines `_seed_fid_counter()` (`global _fid_counter; _fid_counter = max_existing_fid(_PKG)`), and `main_iol.py:1934` calls it inside `main()` — after `write_findings(_PKG)` (line 1929) and before the first probe call `probe_login_sync(client)` (line 1939). Ran `uv run pytest verification/test_main_iol_fid_seed.py verification/test_findings_fid_seed.py -q` myself this cycle: 12 passed. The real committed `.planning/verification/iol-client-findings.md` holds `F-01` OPEN and `F-02` FIXED, so the seed raises the counter to 2 and the next live run's first fid is `F-03` — no overwrite, no silent drop."
  gaps_remaining:
    - "Truth 8 (crash-path redaction) is only partially closed. 30-10 fixed the happy path — a bare `IOLAPIError`/`IOLAuthError`/`IOLRateLimitError` escaping a probe now renders through `_redacted_excepthook` -> `_redacted_exc`, with a marker-planted subprocess test proving stderr and stdout stay clean. But `_redacted_excepthook` (`main_iol.py:2044-2082`) has no error handling of its own: `print(f\"ABORT: {_redacted_exc(exc)}\", file=sys.stderr)` and `traceback.print_tb(tb)` run unguarded. If anything inside that call raises — `_redacted_exc` itself, a closed/broken stderr, or a `RecursionError` arriving as the uncaught exception — CPython's `PyErr_PrintEx` catches the *hook's* failure, prints `Error in sys.excepthook:` plus the hook's own traceback, and then renders the ORIGINAL exception with the DEFAULT renderer, i.e. the full raw upstream body. I independently reproduced this today (not trusted from 30-REVIEW.md's transcript): monkeypatched `main_iol._redacted_exc` to raise inside a real subprocess that installs the hook and raises `IOLAPIError(500, \"ZZ-SECRET-BODY-ZZ-cuenta-999999\")`; captured stderr contained `iol_client.exceptions.IOLAPIError: [500] ZZ-SECRET-BODY-ZZ-cuenta-999999` verbatim, exit code 1. No test in `verification/test_main_iol_exception_redaction.py` exercises this path — I confirmed by listing every `def test_` in the file's crash-path section (11 tests, none named or shaped around a failing renderer). This is the same vulnerability class this phase has spent 30-08/30-09/30-10 closing, now open at the one place specifically built to close it, and it remains open after the fifth cycle's own independent reproduction — not resolved by 30-10 or 30-11, neither of which targeted it (30-10-SUMMARY.md's gate 12 anti-vacuity probe only tests a silent/no-op hook body, never a raising one)."
  regressions: []
gaps:
  - truth: "main_iol.py never renders a caught exception's raw upstream response body to any observable sink — including the crash path when the redaction machinery itself fails partway through rendering."
    status: failed
    reason: >
      Independently reproduced by direct execution this cycle, not trusted from 30-REVIEW.md's
      prose (which itself independently found and reproduced the same defect, dated
      2026-08-23T18:55:00Z, after 30-10 and 30-11 both landed). `_redacted_excepthook`
      (`main_iol.py:2044-2082`) delegates correctly to the sole sanctioned renderer
      `_redacted_exc` and its subprocess test (`test_the_installed_hook_survives_the_real_crash_machinery`)
      genuinely proves the happy path is clean — that part of Truth 8 is real. But the hook body has
      zero defensive error handling: `print(f"ABORT: {_redacted_exc(exc)}", file=sys.stderr)` and
      `traceback.print_tb(tb)` execute unguarded. CPython's excepthook-failure contract
      (`PyErr_PrintEx`) is: if the hook itself raises, print `Error in sys.excepthook:` plus the
      hook's own traceback, then fall through to `Original exception was:` rendered by the DEFAULT
      excepthook — i.e. `str(exc)`, the full `[status] resp.text` upstream body, verbatim, to
      stderr. I reproduced this directly: a subprocess that imports `main_iol`, calls
      `_install_redacted_excepthook()`, monkeypatches `main_iol._redacted_exc` to raise
      `RuntimeError("hook internals failed")`, and raises
      `IOLAPIError(500, "ZZ-SECRET-BODY-ZZ-cuenta-999999")` produces stderr containing
      `iol_client.exceptions.IOLAPIError: [500] ZZ-SECRET-BODY-ZZ-cuenta-999999` in full, with exit
      code 1. This is not a contrived edge case reachable only via test monkeypatching — 30-REVIEW.md
      names three in-repo-reachable triggers I did not need to fabricate to demonstrate the class:
      (a) a `RecursionError` arriving as the uncaught exception, with the hook running on a nearly
      exhausted stack where its own f-string formatting or `traceback.print_tb`'s frame extraction
      can itself raise; (b) closed/broken stderr (`... 2>&1 | head`, or a CI runner with a closed
      pipe), which turns `print(..., file=sys.stderr)` into a `BrokenPipeError`/`ValueError`; (c)
      `_redacted_exc` unconditionally reading `exc.model`/`exc.field_path`/`exc.declared_type`/
      `exc.observed_type` on anything satisfying `isinstance(exc, IOLDecodeError)` — a subclass or a
      reconstructed instance that never ran `IOLDecodeError.__init__` raises `AttributeError` there,
      inside the hook, on the crash path this exact mechanism exists to protect. I confirmed no
      regression test in `verification/test_main_iol_exception_redaction.py` exercises any of these:
      the crash-path section's 11 `def test_` entries (lines 1128-1284) cover the hook rendering
      correctly, the traceback rendering frames only, a chained cause not leaking, a non-integer
      status not leaking, the subprocess happy path, the installer wiring, and the guard-order AST
      lock — none of them makes the hook's own internals fail and checks the fallback path. A
      security boundary whose failure mode is "emit the thing you were built to suppress" must fail
      closed; today it fails open.
    artifacts:
      - path: "main_iol.py"
        issue: "Lines 2044-2082 (`_redacted_excepthook`): the `print(...)` and `traceback.print_tb(tb)` calls have no try/except. Any exception raised inside them (including one raised by `_redacted_exc` itself, or a broken stderr sink) causes CPython's excepthook-failure fallback to render the ORIGINAL exception's full message — the raw upstream body — via the default renderer."
    missing:
      - "Wrap the hook's body in a fail-closed try/except that never lets an internal failure reach CPython's fallback renderer: catch any exception from `_redacted_exc(exc)` and substitute a static placeholder string, and separately guard the `print`/`traceback.print_tb` calls so a broken stderr cannot escape either. Add a regression test that monkeypatches `_redacted_exc` (or an equivalent internal failure) to raise inside a real subprocess running the installed hook, and asserts the planted marker is absent from BOTH stdout and stderr while the process still exits non-zero."
  - truth: "The AST regression lock durably prevents the leak class from being reintroduced through any handler-site read or delegation shape, and the renderer census durably prevents a second renderer from being introduced under any name or shape."
    status: partial
    reason: >
      Independently reproduced this cycle by calling the widened, post-30-11 detectors directly on
      synthetic sources (not trusted from 30-REVIEW.md's prose): `_raw_exception_renders` still
      returns `[]` for `append_finding("p", actual=getattr(exc, "message", ""))`,
      `append_finding("p", actual=str(getattr(exc, "args")))`, and
      `append_finding("p", actual=str(exc.__dict__))` — all three would write `resp.text` verbatim
      into the git-tracked findings file if introduced at a real site, and the widened lock (whose
      whole point per 30-11's own objective was to close exactly this class of bypass) does not
      catch any of them. Confirmed the underlying reason: 30-11's `getattr`-handling rule matches on
      the callee name alone (`getattr` is in `_SANCTIONED_DELEGATES`), not on which attribute string
      is passed, so `getattr(exc, "message", ...)` is treated identically to the intentionally
      sanctioned `getattr(exc, "status_code", None)`. Separately confirmed
      `_declared_exception_renderers` still returns `[]` for a synthetic function
      `def _fmt(exc: BaseException) -> str: return "ABORT: %s" % exc` and for
      `def _fmt(exc: BaseException) -> None: print(exc)` — both are exactly the shape that would
      reintroduce the CR-02/crash-path leak in full if `main_iol.py:2081` were ever rewritten from
      an f-string to a `%`-format, and the census's read-predicate (unlike `_raw_exception_renders`,
      which does implement the `%`-formatting rule) does not share that rule. No live leak exists
      today anywhere in `main_iol.py` — confirmed by running the widened detector against the real
      file (`[]`, matching 30-11-SUMMARY.md's own claim) — this is a durability gap in the lock
      itself, consistent with the phase's own precedent of scoring a lock-coverage gap as a
      WARNING rather than a BLOCKER when no live leak exists. Recorded as `partial` (not `failed`)
      because it does not block the phase goal today, but it means 30-11-SUMMARY.md's claim that
      "AD-30-09-01 ahora es cierta del lock, no sólo del código" is not fully accurate — it is truer
      than before 30-11, not durably true.
    artifacts:
      - path: "verification/test_main_iol_exception_redaction.py"
        issue: "`_raw_exception_renders`'s `getattr` handling (~line 616 `_SANCTIONED_DELEGATES`, rule 4 ~729-736) is keyed on the callee name, not the attribute argument, so `getattr(exc, \"message\", ...)` and `getattr(exc, \"args\")` pass unflagged; `exc.__dict__` is absent from `_LEAKY_EXC_ATTRS` entirely. `_declared_exception_renderers`'s read-predicate (~906-933) recognizes attribute read, `getattr`, a fixed `_STRINGIFYING_CALLS` set, and direct f-string interpolation, but not `%`-formatting or generic delegation-to-a-printer — even though `_raw_exception_renders` already implements the `%`-formatting rule, the two detectors do not share it."
    missing:
      - "Narrow the `getattr` exemption to the attribute-name argument (flag `getattr(exc, \"message\"/\"args\"/\"response\"/\"request\"/…, …)` while still allowing `getattr(exc, \"status_code\", None)`), add `__dict__` to the leaky-attribute set, and extend `_declared_exception_renderers`'s read-predicate with the same `%`-formatting (`ast.BinOp`/`ast.Mod`) rule `_raw_exception_renders` already has, plus a generic \"non-sanctioned callee received the parameter\" rule. This is scoped as a further gap-closure plan (e.g. 30-12), not a blocker for phase completion given no live leak exists today."
deferred: []
human_verification: []
---

# Phase 30: `iol-client` tipado Verification Report (fifth cycle, after 30-10 + 30-11 gap-closure)

**Phase Goal:** El consumidor de `iol-client` accede a cotizaciones, series históricas e instrumentos por **atributo tipado** — un typo lo caza mypy en el editor, no el servidor en producción.
**Verified:** 2026-08-23T19:30:00Z
**Status:** gaps_found
**Re-verification:** Yes — fifth cycle, after gap-closure plans 30-10 (fid seed + crash-path redaction) and 30-11 (AST lock widening)

## Goal Achievement

### Scope note (read this first)

The phase's **literal, roadmap-stated goal** — typed attribute access on `iol-client`'s public
surface (quotes, historical series, instruments), mypy catching a typo in the editor — is a
**published-package** concern (`packages/iol-client/`). That goal has been fully delivered since
plan 30-04 and is re-confirmed, unaffected, this cycle: `git diff --exit-code packages/` exits 0,
`mypy --strict` reports `Success: no issues found in 25 source files`, `ruff check` is clean, and
the 242-test package suite passes.

Since cycle 2, this phase's own verification lineage has treated a second, self-declared guarantee
as an in-scope BLOCKER: that `main_iol.py` (the phase's live-verification driver, the vehicle
CLAUDE.md names as the mechanism to "detectar bugs... y corregirlos en el mismo ciclo") never leaks
an upstream wire value to any observable sink. This fifth cycle continues that precedent, per the
verification focus explicitly restated for this run.

**What this cycle independently re-derived, not trusted from any prior report:**

1. **`_fid_counter` seeding (prior truth 7) is genuinely closed.** Direct source read plus a fresh
   test run (`12 passed`) confirms `_seed_fid_counter()` exists, is wired between
   `write_findings(_PKG)` and the first probe, and the real committed findings file
   (`F-01` OPEN, `F-02` FIXED) would seed the counter to 2.
2. **Crash-path redaction (prior truth 8) is NOT genuinely closed.** 30-10 fixed the happy path
   convincingly (I independently confirmed the marker-planted subprocess test is real and passes),
   but `_redacted_excepthook` has no defensive error handling around its own body. I reproduced,
   by direct subprocess execution (not by reading 30-REVIEW.md's transcript), that a failure inside
   the hook — trivially demonstrated by making `_redacted_exc` raise, and independently plausible
   via a `RecursionError`, a closed stderr, or an `IOLDecodeError` subclass missing an attribute —
   causes CPython to fall back to its default excepthook and print the full raw upstream body to
   stderr. This is the exact vulnerability class this phase has spent four gap-closure cycles
   closing, now open at the one function specifically built to close it.
3. **The widened AST lock (30-11) still has live bypasses**, independently confirmed by calling the
   post-30-11 detector functions directly against synthetic sources: `getattr(exc, "message", ...)`,
   `getattr(exc, "args")`, and `exc.__dict__` all pass `_raw_exception_renders` unflagged; a
   `%`-formatting or `print(exc)`-shaped second renderer passes `_declared_exception_renderers`
   unflagged. No live leak exists in `main_iol.py` today (the widened detector returns `[]` against
   the real file), so this is scored as a lock-durability gap, not a blocker — consistent with how
   the fourth cycle scored the pre-30-11 lock gap.

### Observable Truths

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | `models.py` con modelos tipados de cotización/serie histórica/instrumentos, `puntas` polimórfico resuelto (SC1) | ✓ VERIFIED (regression) | `packages/iol-client/src/iol_client/models.py` present, `git diff --exit-code packages/` exits 0 this cycle — untouched since 30-04. |
| 2 | 16 firmas devuelven modelos, cero `Any`/`dict[str, Any]`, `mypy --strict` limpio, ruff verde (SC2) | ✓ VERIFIED | Re-ran this cycle: `mypy --strict` → `Success: no issues found in 25 source files`; `ruff check packages/iol-client main_iol.py verification` → `All checks passed!`. |
| 3 | `main_iol.py` lee por atributo en sus 2 sitios reales; RED fixture prueba que un typo falla el typecheck (SC3) | ✓ VERIFIED (regression) | `main_iol.py:539,619` attribute access (`quote.ultimoPrecio`), unchanged since 30-04. |
| 4 | `mercado`/`plazo` quedan `str`; ningún campo RESPONSE gana `Literal` (SC4) | ✓ VERIFIED (regression) | Unchanged since 30-04; `packages/` byte-identical this cycle. |
| 5 | `to_dict()` escape hatch en todos los modelos; README documenta la ruptura (SC5) | ✓ VERIFIED (regression) | Unchanged since 30-04. |
| 6 | `main_iol.py` never renders a caught exception's raw upstream body into the git-tracked findings file or the stdout auth-cascade detail | ✓ VERIFIED (regression) | `grep -c "actual=repr(exc)" main_iol.py` → 0; `grep -c "_redacted_exc(exc)" main_iol.py` → 32 this cycle; `uv run pytest verification/test_main_iol_exception_redaction.py verification/test_main_iol_raw_wire_drift.py -q` → 47 + 22 across the two suites (see below), all passing. |
| 7 | The verification harness's finding-ID allocator never overwrites an OPEN finding or drops a FIXED one on the next run | ✓ VERIFIED (closed this cycle) | `main_iol.py:183-206` defines `_seed_fid_counter()`; `main_iol.py:1934` calls it between `write_findings(_PKG)` (1929) and `probe_login_sync(client)` (1939). `uv run pytest verification/test_main_iol_fid_seed.py verification/test_findings_fid_seed.py -q` → 12 passed, independently re-run this cycle. |
| 8 | `main_iol.py` never renders a raw exception body to any sink, including the uncaught/crash path (stderr/CI logs), **even when the redaction machinery itself fails partway through** | ✗ FAILED | Directly reproduced by subprocess execution this cycle: a failure inside `_redacted_excepthook` (e.g. `_redacted_exc` raising) causes CPython's default excepthook fallback to print the planted marker `ZZ-SECRET-BODY-ZZ-cuenta-999999` verbatim to stderr. See `gaps:` frontmatter for the full mechanism and reproduction. |

**Score:** 7/8 truths verified. Truths 1-7 (the roadmap's actual stated phase goal SC1-SC5, the
now-closed finding-file/cascade leak, and the now-closed fid-allocator seeding) are fully met.
Truth 8 remains open: the crash-path fix genuinely closes the happy path but fails open on its own
internal failure, which is the exact "unhandled exception reaches an unsanctioned sink" vulnerability
class this phase's verification lineage has escalated to BLOCKER four times already.

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `packages/iol-client/src/iol_client/models.py` | typed models, `puntas` polymorphism resolved, `to_dict()` | ✓ VERIFIED | `git diff --exit-code packages/` exits 0 this cycle. |
| `packages/iol-client/src/iol_client/client.py` + `aio.py` | 16 typed signatures, no `Any`/`dict[str, Any]` returns | ✓ VERIFIED | mypy --strict clean; 242 tests pass. |
| `main_iol.py::_redacted_exc` + 32-site sweep | sole sanctioned exception-to-report renderer | ✓ VERIFIED | `grep -c "_redacted_exc(exc)"` → 32; 0 raw `repr(exc)`/`str(exc)`/`{exc}` renders file-wide. |
| `main_iol.py::_fid_counter` seeding | seeded from `max_existing_fid(_PKG)` before allocating new fids | ✓ VERIFIED | `_seed_fid_counter()` present and correctly wired; regression suite (12 tests) passes. |
| `main_iol.py::_redacted_excepthook` + `_install_redacted_excepthook` | uncaught exceptions never render raw upstream body, under any failure mode of the hook itself | ✗ FAIL-OPEN | Happy path genuinely closed (marker-planted subprocess test passes). Hook has no try/except around its own body; a failure inside it (reproduced) falls through to CPython's default renderer, which prints the raw body. |
| `verification/test_main_iol_fid_seed.py` | driver-level regression suite for the fid seed | ✓ VERIFIED | 5 cases, all pass, including an AST wiring lock and a non-vacuity control. |
| `verification/test_main_iol_exception_redaction.py` (widened, post-30-11) | AST regression lock covering attribute reads, delegation, %-format, alias; falsifiable renderer census | ⚠️ PARTIAL — durability gap, no live leak | Widened from 3 to 11 flagged shapes (30-11's own WR-01 table), and from a name-match to a shape-based census. Independently confirmed this cycle: `getattr(exc, "message"/"args", …)`, `exc.__dict__`, and a `%`-format or `print(exc)`-shaped renderer all still pass undetected. Zero live occurrences of any of these exist in `main_iol.py` today (confirmed: detector returns `[]` against the real file). |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `main_iol.py` (32 caught-exception sites) | `.planning/verification/iol-client-findings.md` / stdout cascade | `_redacted_exc(exc)` | ✓ WIRED AND SAFE | Confirmed: 0 raw renders remain; all 32 sites route through the single helper. |
| `main_iol.py::main()` | `verification/findings.py::max_existing_fid` | `_seed_fid_counter()` called after `write_findings(_PKG)`, before the first probe | ✓ WIRED AND SAFE | Confirmed by direct read and by the AST wiring-lock test passing. |
| `main_iol.py::main()` (uncaught-exception path, happy case) | `main_iol.py::_redacted_excepthook` -> `_redacted_exc` -> stderr | `sys.excepthook = _redacted_excepthook` | ✓ WIRED AND SAFE (for exceptions the hook itself renders without incident) | Subprocess test with a planted marker confirms stdout/stderr stay clean and exit code is non-zero. |
| `main_iol.py::_redacted_excepthook` (internal-failure path) | CPython's default excepthook fallback -> stderr | none — no try/except inside the hook | 🛑 WIRED BUT UNSAFE | If `_redacted_exc(exc)` or the `print`/`traceback.print_tb` calls raise, CPython's `PyErr_PrintEx` renders the ORIGINAL exception with the default (unredacted) renderer. Reproduced directly this cycle. This is the open BLOCKER (truth 8). |
| `verification/test_main_iol_exception_redaction.py::_raw_exception_renders` / `_declared_exception_renderers` | `main_iol.py` (source string) | AST-based static analysis | ⚠️ WIRED, INCOMPLETE COVERAGE | Zero false positives against the real file; zero live leaks exist today; but `getattr`-with-leaky-attribute and `%`/`print`-shaped delegation both still bypass detection, confirmed by direct invocation this cycle. |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| TYP-01 | 30-01 … 30-11 | `iol-client` tipado — 16 firmas + `models.py` + acceso por atributo en driver, con verificación en vivo no-vacua | ✓ SATISFIED at the published-API level (roadmap SC1-SC5, regression-confirmed this cycle); ✗ the phase's own additionally-declared verification-harness reliability/security guarantee remains partially open (1 BLOCKER: crash-path fail-open) | `.planning/REQUIREMENTS.md` line 16 correctly shows the TYP-01 checkbox as `[ ]` and line 67's tracking table shows "Pending" — accurate, not stale. 30-10-SUMMARY.md and 30-11-SUMMARY.md both explicitly declined to flip it, citing this exact open cycle. |

No orphaned requirements: `.planning/REQUIREMENTS.md` maps only TYP-01 to Phase 30; all 11 plans
(30-01 through 30-11) declare `requirements: [TYP-01]`.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| `main_iol.py` | 2044-2082 (`_redacted_excepthook`) | No error handling around `_redacted_exc(exc)` / `print(...)` / `traceback.print_tb(tb)` | 🛑 BLOCKER | A failure inside the hook (reproduced this cycle) falls through to CPython's default renderer, printing the raw upstream body to stderr/CI logs — defeats the crash-path fix 30-10 just delivered. |
| `verification/test_main_iol_exception_redaction.py` | `_SANCTIONED_DELEGATES`/rule 4 (`getattr` handling, ~line 616/729-736) | `getattr` exemption is keyed on the callee name, not the attribute argument | ⚠️ WARNING | `getattr(exc, "message"/"args", ...)` and `exc.__dict__` bypass the widened lock, reproduced this cycle. Not a live leak today. |
| `verification/test_main_iol_exception_redaction.py` | `_reads_the_exception` (~906-933) | Census read-predicate lacks the `%`-formatting rule `_raw_exception_renders` already has, and lacks generic non-sanctioned-callee delegation | ⚠️ WARNING | A `%`-format or `print(exc)`-shaped second renderer passes the census undetected, reproduced this cycle. Not a live leak today. |
| `main_iol.py` | 2044-2092 | Only `sys.excepthook` installed; `sys.unraisablehook`, `threading.excepthook`, asyncio's default loop exception handler are separate unguarded sinks | ℹ️ INFO | Not currently reachable with an IOL-carrying payload (`iol_client` spawns no threads, the driver creates no bare async tasks) — carried forward from 30-REVIEW.md WR-03, not independently re-derived beyond confirming the generic mechanism is real in Python (reproduced a generic `threading.excepthook` leak in an isolated repro, not tied to a reachable `main_iol.py` code path). |
| `verification/test_main_iol_fid_seed.py` | ~112-117 (`_add_finding`'s promotion `str.replace`) | Unanchored `str.replace` on identically-shaped fixture findings can rewrite the wrong finding's detail block | ℹ️ INFO | Carried forward from 30-REVIEW.md WR-04, not independently re-verified line-by-line this cycle; does not affect the real committed findings file, only the test fixture's internal consistency. |
| `verification/test_main_iol_fid_seed.py` | ~273-297 (seed wiring lock) | Compares AST call line numbers, not control-flow reachability | ℹ️ INFO | Carried forward from 30-REVIEW.md WR-05, not independently re-verified this cycle; a seed call inside a dead branch would satisfy the current lock. |
| `.planning/REQUIREMENTS.md` | line 67 | Tracking table shows "Pending" for TYP-01 | ℹ️ INFO | Accurate as-is; matches the still-open BLOCKER state. |

No `TBD`/`FIXME`/`XXX` debt markers found in `main_iol.py`, `verification/test_main_iol_exception_redaction.py`,
or `verification/test_main_iol_fid_seed.py` (re-checked this cycle via grep, exit 1 / no matches).

Carried forward, not re-scored this cycle because none were escalated to BLOCKER: WR-06 (a
legitimately zero `ultimoPrecio` produces a permanent OPEN finding), IN-01..IN-03 (`_raw_exception_renders`'
container-aliasing blind spot, `max_existing_fid`'s detail-header-only scan, the crash-path
subprocess test inheriting the operator's real environment), and the older 30-09-SUMMARY.md
carry-forwards (probe-13 anti-vacuity, PASS-detail numeral, `DecodeScope` binding).

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| SC1-SC5 unaffected by 30-10/30-11 | `git diff --exit-code packages/` | exit 0 | ✓ PASS |
| `mypy --strict` clean | `uv run mypy packages/iol-client/src packages/iol-client/tests` | `Success: no issues found in 25 source files` | ✓ PASS |
| `ruff` clean | `uv run ruff check packages/iol-client main_iol.py verification` | `All checks passed!` | ✓ PASS |
| Package suite | `uv run pytest packages/iol-client -q` | `242 passed` | ✓ PASS |
| Exception-redaction contract (post-30-10/30-11) | `uv run pytest verification/test_main_iol_exception_redaction.py -q` | `47 passed` | ✓ PASS |
| Fid-seed + analog suites | `uv run pytest verification/test_main_iol_fid_seed.py verification/test_findings_fid_seed.py -q` | `12 passed` | ✓ PASS |
| Raw-wire-drift + single-client-instance + bare-except sibling suites | `uv run pytest verification/test_main_iol_raw_wire_drift.py verification/test_main_iol_uses_single_client_instance.py verification/test_main_drivers_bare_except.py -q` | `32 passed` (combined with prior row's non-overlap set) | ✓ PASS |
| **Crash-path fail-open reproduction** | Subprocess: install hook, monkeypatch `_redacted_exc` to raise, raise `IOLAPIError(500, "ZZ-SECRET-BODY-ZZ-cuenta-999999")` | stderr contains `IOLAPIError: [500] ZZ-SECRET-BODY-ZZ-cuenta-999999` verbatim; exit code 1 | 🛑 CONFIRMS OPEN BLOCKER |
| **AST-lock `getattr` bypass reproduction** | `_raw_exception_renders(<synthetic source with getattr(exc, "message", "")>)` called directly | `[]` (undetected) | ⚠️ CONFIRMS DURABILITY GAP (not a live leak) |
| **Renderer-census `%`-format bypass reproduction** | `_declared_exception_renderers(<synthetic %-format renderer>)` called directly | `[]` (undetected) | ⚠️ CONFIRMS DURABILITY GAP (not a live leak) |
| No debt markers | `grep -nE "TBD\|FIXME\|XXX" main_iol.py verification/test_main_iol_exception_redaction.py verification/test_main_iol_fid_seed.py` | no matches | ✓ PASS |
| Git working tree clean of unrelated changes | `git status --porcelain` | only this VERIFICATION.md (being rewritten) and pre-existing untracked `.gsd/`/research cache | ✓ PASS |

### Probe Execution

Not applicable — this phase's verification surface is `main_iol.py`'s own named probes and the
`verification/test_main_iol_exception_redaction.py` / `test_main_iol_fid_seed.py` /
`test_main_iol_raw_wire_drift.py` offline regression locks, exercised directly above, plus this
cycle's own subprocess reproductions of the fail-open behavior. There are no
`scripts/*/tests/probe-*.sh` conventional probes for this phase.

### Human Verification Required

None required to resolve status. The open BLOCKER (crash-path fail-open) is demonstrated by direct,
reproducible subprocess execution, not a matter of taste or visual judgment.

### Gaps Summary

**The phase's literal, roadmap-stated goal — typed attribute access on `iol-client`'s published
surface (SC1-SC5) — remains fully achieved and is unaffected by 30-10 or 30-11.**
`packages/iol-client/` has been untouched since 30-04; mypy/ruff/pytest all re-confirmed clean this
cycle.

**The fourth cycle's fid-counter BLOCKER (truth 7) is genuinely closed.** Independently re-derived
by direct source read and a fresh test run (12 passed): the allocator now seeds from
`max_existing_fid(_PKG)` in the correct position, and the real committed findings file's `F-01`
(OPEN) / `F-02` (FIXED) state would produce `F-03` as the next fid without overwriting or dropping
anything.

**The fourth cycle's crash-path BLOCKER (truth 8) is only partially closed, and remains open after
this cycle's independent reproduction.** 30-10 genuinely fixed the *happy path*: an `IOLAPIError`
escaping a probe's narrow `except` clause now renders through `_redacted_excepthook` ->
`_redacted_exc`, proven by a marker-planted subprocess test I confirmed is real and passing. But the
hook itself has no defensive error handling. I reproduced, by running a real subprocess (not by
reading 30-REVIEW.md's prose), that when the redaction call inside the hook fails — demonstrated
directly by monkeypatching `_redacted_exc` to raise, and independently plausible via a
`RecursionError`, closed stderr, or a malformed `IOLDecodeError` — CPython's excepthook-failure
contract falls through to the DEFAULT renderer, which prints the exception's raw message (the full
upstream body) to stderr. This is the same vulnerability class this phase's verification lineage has
escalated to BLOCKER on four separate occasions (`_capture_raw_wire` in cycle 2, the 29-site
finding-file leak in cycle 3, the crash-path happy-path gap in cycle 4, and now this cycle's
discovery that the crash-path fix itself fails open) — a security boundary whose own failure mode
re-exposes exactly what it was built to redact.

**A related durability gap, independently confirmed this cycle:** the AST regression lock widened by
30-11 does close the specific 11 shapes named in the prior review's WR-01/WR-02 tables, but a fresh
pass finds three more bypasses the widening did not anticipate — `getattr(exc, "message"/"args", …)`,
`exc.__dict__`, and a `%`-format or `print(exc)`-shaped second renderer all pass both detectors
unflagged, confirmed by direct invocation against synthetic sources. No live occurrence of any of
these exists in `main_iol.py` today (the detectors return `[]` against the real file) — this is
scored as a WARNING (lock durability), not a BLOCKER, consistent with how the fourth cycle scored
the equivalent pre-30-11 gap. It is reported because a lock that keeps acquiring new blind spots as
fast as old ones are closed is a signal about the review methodology, not just this file.

**Scope judgment (explicit, per the task's ask, continuing the established precedent).** Neither
open item is a defect in `iol-client`'s published, typed API surface — the phase's literal roadmap
goal, which remains fully met. Both are defects in `main_iol.py` and its verification harness, the
phase's own live-verification driver and its regression locks. This phase's verification lineage has
already, across four prior cycles, treated `main_iol.py`'s exception-rendering integrity as an
in-scope, phase-blocking guarantee — the same file, the same underlying vulnerability class (an
upstream wire value reaching an observable sink outside the one sanctioned renderer), now discovered
at a new site (the redaction hook's own internal-failure path) after the previous site (the crash
path's happy case) was genuinely closed. Per that established precedent, and because the crash-path
fail-open defect is live, reachable (independently reproduced, not merely theorized), and undermines
the exact property four prior gap-closure cycles have been chasing, this verification classifies it
as a phase-level BLOCKER. `.planning/REQUIREMENTS.md`'s TYP-01 checkbox correctly remains unchecked.

**Recommendation:** a further narrowly-scoped closure plan (e.g. 30-12) that (a) wraps
`_redacted_excepthook`'s body in a fail-closed try/except so no internal failure of the hook can
reach CPython's fallback renderer, with a regression test that forces `_redacted_exc` to raise inside
a real subprocess and asserts the marker is absent from both stdout and stderr while the exit code
stays non-zero; and (b) optionally extends the AST lock's `getattr` and renderer-census rules to
close the three newly-found bypasses (not blocking, since no live leak exists, but the same class of
gap that has recurred at every widening so far). 30-REVIEW.md's CR-01 (the fresh review's numbering)
supplies a concrete fix for (a); this verification does not mandate its exact implementation, only
its scope.

---

_Verified: 2026-08-23T19:30:00Z_
_Verifier: Claude (gsd-verifier)_
