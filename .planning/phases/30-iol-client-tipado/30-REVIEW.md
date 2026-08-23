---
phase: 30-iol-client-tipado
reviewed: 2026-08-23T03:10:20Z
depth: deep
files_reviewed: 2
files_reviewed_list:
  - main_iol.py
  - verification/test_main_iol_exception_redaction.py
findings:
  critical: 2
  warning: 6
  info: 5
  total: 13
status: issues_found
---

# Phase 30: Code Review Report

**Reviewed:** 2026-08-23T03:10:20Z
**Depth:** deep
**Files Reviewed:** 2
**Status:** issues_found

## Summary

This run supersedes the stale 30-REVIEW.md dated 2026-08-22 (CR-01 + 7 warnings + 3 info).

**Verdict on the question the run was scoped to answer.** CR-01 is closed at all 32 exception
handler sites: every `except` in `main_iol.py` that reaches `append_finding` routes through
`_redacted_exc`, the two cascade sinks (`_auth_failure_reason` at lines 414 and 449) route through
it too, and the one handler that does not (line 992, the 6-type sanity gate) emits only
`type(exc).__name__`. `ruff check`, `ruff format --check` and `mypy --strict` all pass on both
files; all 18 tests in the new file and all 43 iol-related verification tests pass.

The `_redacted_exc` helper itself does not leak through the branches the prompt named. I traced
both exemptions to ground truth rather than to their docstrings:

- The `IOLDecodeError` exemption is genuinely sound. `_decode.py:225` is the sole raise site;
  `observed_type` is always `type(value).__name__` (`_decode.py:446/494/500/511/520/533`), and the
  one path where `field_path` can carry a wire-supplied key (`_decode.py:576`, kind `extra`) is
  gated off the strict raise by `_decode.py:209` (`kind not in _INFO_KINDS`). So a raised
  `IOLDecodeError` cannot carry a wire key, let alone a wire value.
- The non-int `status_code` guard holds. Every construction site in the package
  (`_core.py:123/125/127/156/193/211/371/454/457`) passes an `int`, and the `isinstance` guard
  covers the arbitrary-`Exception` case the guard exists for.

**What is not closed.** Two Critical findings, neither of which the phase's own tests can see:

1. **CR-01** — a live data-integrity defect: `_fid_counter` is never seeded from
   `max_existing_fid(_PKG)`, so the next live run overwrites the human-triaged `F-01` and silently
   discards any second finding against the `FIXED` `F-02`. The harness's own
   `verification/findings.py:107` and `verification/test_findings_fid_seed.py` module docstring
   describe this exact failure ("the run claims success having lost its deliverable"), and
   `main_market_data.py:275` already applies the fix. `main_iol.py` does not.
2. **CR-02** — the redaction contract has an unguarded escape: `main()` has no top-level handler, so
   any exception on the documented "propaga como crash" paths prints
   `IOLAPIError: [500] <full upstream body>` to stderr via the default traceback, bypassing
   `safe_print` and every threat control this phase installed. The test file's own WR-02 rationale
   counts CI logs as an in-scope sink, so this is the same threat, not an adjacent one.

**On the regression lock.** The AST detector is the artifact that is supposed to keep CR-01 closed
after this phase ends. I ran 11 realistic leak shapes through `_raw_exception_renders`; **10 were
missed**, including `append_finding(actual=exc.message)` — and `IOLAPIError.message` is literally
`resp.text` (`exceptions.py:16`, `_core.py:127`). The companion test
`test_the_driver_declares_exactly_one_exception_renderer` does not close that hole either: it
matches only the literal name `_redacted_exc`. So the phase's central claim — "one sanctioned
renderer, enforced" — is true of the code as written today but is **not** enforced going forward,
which is the only reason a regression lock exists. See WR-01 and WR-02.

## Critical Issues

### CR-01: `_fid_counter` is never seeded — the next live run destroys a triaged finding and silently drops another

**File:** `main_iol.py:157`, `main_iol.py:165-169`, `main_iol.py:1885`
**Issue:**
`_fid_counter` resets to `0` on every process start and `main()` never seeds it, so run N+1
re-issues `F-01`, `F-02`, ... The current committed
`.planning/verification/iol-client-findings.md` holds:

- `F-01` — `SHAPE`/`OPEN`, "missing assumed key `simbolo` in get_quote", carried forward by
  operator sign-off in Phase 17.
- `F-02` — `AUTH`/`FIXED`, with ~25 lines of human triage, resolution, regression links and an
  operator signoff line.

Two consequences on the next live run, both reachable and both destructive:

1. The first finding emitted takes `fid=F-01`. That fid is `OPEN`, so `append_finding` does **not**
   short-circuit — it rewrites the `F-01` detail block in place with unrelated content. The
   operator prose lives below `<!-- END AUTO-GENERATED -->` and survives, so the file ends up with
   a Phase 17 narrative about `simbolo` attached to a finding that is no longer about `simbolo`.
2. The second finding emitted takes `fid=F-02`. That fid is `FIXED`, so `append_finding`
   short-circuits to a no-op — while `main()` still counts it into `FINDING=N` at line 1983 and
   prints a `SUMMARY` claiming success. The deliverable is lost with no signal.

`verification/findings.py:107-130` and the `verification/test_findings_fid_seed.py` module
docstring both document this precise failure mode, and `main_market_data.py:275` already carries
the one-line fix. `main_iol.py` was rewritten across 32 call sites in this plan without picking it
up.

**Fix:**
```python
# main_iol.py — import
from verification.findings import append_finding, max_existing_fid

# main_iol.py — inside main(), immediately after write_findings(_PKG)
def main() -> None:
    ...
    write_findings(_PKG)
    # D-16/D-24: seed the allocator above every fid already recorded, otherwise
    # run N+1 re-issues F-01.. and either clobbers an OPEN finding or is silently
    # swallowed by the non-OPEN short-circuit while SUMMARY still reports FINDING=N.
    global _fid_counter
    _fid_counter = max_existing_fid(_PKG)
```
Add a regression test next to the existing lock, e.g.
`test_driver_seeds_its_fid_allocator_from_the_committed_findings_file`, that seeds a temp findings
file with a `FIXED` `F-02`, runs `main()` against a mock transport, and asserts the emitted fid is
`> F-02`.

### CR-02: uncaught exceptions print the raw upstream body to stderr, bypassing every redaction control

**File:** `main_iol.py:402-412`, `main_iol.py:1570-1634`, `main_iol.py:1871-1987`
**Issue:**
`main()` has no top-level exception handler, and several probes deliberately let non-matching
exception types propagate:

- `probe_login_sync` (line 412) catches only `IOLAuthError`. A `500` from the token endpoint raises
  `IOLAPIError` and escapes. Its docstring states this explicitly ("Cualquier otra excepción
  propaga como crash inesperado").
- `probe_login_async` (line 447) — same shape.
- `probe_refresh_token` (lines 1605/1620) catches `IOLAuthError`/`IOLAPIError` only; an
  `httpx.ConnectError` or `httpx.ReadTimeout` escapes.
- `_write_or_check_schema` (line 1460) has no handler at all around `json.loads`.

`IOLAPIError.__init__` builds its message as `f"[{status_code}] {message}"` where `message` is
`resp.text` (`exceptions.py:13-17`, `_core.py:127`). The default `sys.excepthook` renders
`str(exc)`. Verified concretely:

```
iol_client.exceptions.IOLAPIError: [500] {"cuenta":"999999","simbolo":"GGAL","detalle":"SECRETO-DEL-WIRE"}
```

That is the exact string the 32 handler-site fixes exist to prevent, emitted on a path that
bypasses `safe_print` entirely — violating this file's own module-docstring rule at line 48
("**Redacción (D-IOL-7/22):** todos los prints pasan por `safe_print`"). The test file's WR-02
rationale (lines 335-345) explicitly counts "stdout y los logs de CI" as an in-scope sink, so CI
log capture is inside the threat model, not outside it.

Note the tension with D-04 ("crash on unexpected is allowed"): the fix below preserves the crash
(non-zero exit, run aborts) and removes only the raw rendering.

**Fix:**
```python
# main_iol.py — bottom of file
def _redacted_excepthook(
    exc_type: type[BaseException],
    exc: BaseException,
    tb: TracebackType | None,
) -> None:
    """D-04 preserva el crash; lo que no puede sobrevivir es el render crudo.

    ``str(IOLAPIError)`` es ``[500] <body upstream completo>``: el default de
    ``sys.excepthook`` lo volcaría a stderr, y los logs de CI son un sink dentro
    del threat model (WR-02). Se imprime la frontera sancionada y el traceback
    SIN la última línea de mensaje.
    """
    print(f"ABORT: {_redacted_exc(exc)}", file=sys.stderr)
    traceback.print_tb(tb, file=sys.stderr)


if __name__ == "__main__":
    sys.excepthook = _redacted_excepthook
    main()
```
Requires `import sys`, `import traceback`, `from types import TracebackType`. Add a test asserting
that an escaping `IOLAPIError(500, body_with_marker)` produces stderr free of the marker.

## Warnings

### WR-01: the AST regression lock misses 10 of 11 realistic leak shapes, including `exc.message`

**File:** `verification/test_main_iol_exception_redaction.py:430-481`, `:503-512`
**Issue:**
`_raw_exception_renders` marks exactly three shapes: `repr`/`str` over the bound name, an f-string
interpolation whose `value` is the bound `ast.Name`, and the bound `ast.Name` passed as an
`append_finding` keyword. I ran candidate regressions through the detector as shipped:

| Shape | Result |
|---|---|
| `append_finding("p", actual=exc.message)` | **MISSED** |
| `append_finding("p", actual=f"{exc.message}")` | **MISSED** |
| `reason = f"login: {exc.args}"` | **MISSED** |
| `append_finding("p", actual="%s" % exc)` | **MISSED** |
| `append_finding("p", actual="{}".format(exc))` | **MISSED** |
| `print(exc)` | **MISSED** |
| `safe_print(exc, secrets=[])` | **MISSED** |
| `def _render(e): return str(e)` + `actual=_render(exc)` | **MISSED** |
| `e2 = exc; append_finding("p", actual=str(e2))` | **MISSED** |
| `except Exception:` + `str(sys.exc_info()[1])` | **MISSED** |
| `return ProbeResult("n","FINDING", f"{exc!r}")` | FLAGGED |

The first row is the one that matters: `IOLAPIError.message` (`exceptions.py:16`) holds `resp.text`
verbatim — it is precisely the raw body CR-01 is about — and it lands in
`append_finding(actual=...)` completely unflagged. The docstring's "lo que **no** marca, a
propósito" list mentions `<nombre>.status_code` as an intentional allowance, but the implementation
never inspects `ast.Attribute` at all, so it allows every attribute equally, `.message` and `.args`
included. Attribute access being unchecked is not a considered whitelist; it is an absent check.

The failure message at line 507-512 over-claims accordingly: "`main_iol.py` tiene N sitio(s) que
reportan la excepción cruda" reads as a total, when the detector covers only 3 shapes.

**Fix:** widen the detector and re-run the positive control with one planted occurrence per new
shape:
```python
_LEAKY_ATTRS = ("message", "args", "response", "request")
_STRINGIFYING = ("repr", "str", "format")

# inside the per-handler walk, alongside the existing rules:
if isinstance(node, ast.Attribute):
    if (
        isinstance(node.value, ast.Name)
        and node.value.id == bound
        and node.attr in _LEAKY_ATTRS
    ):
        offenders.add((node.lineno, f"{bound}.{node.attr}"))
if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
    if isinstance(node.right, ast.Name) and node.right.id == bound:
        offenders.add((node.lineno, f"%-format sobre {bound}"))
# and extend the existing repr/str rule to cover ``"...".format(exc)``:
#   called in _STRINGIFYING and any positional arg is Name(bound)
```
Then either narrow the "passed to another function" allowance to an explicit allow-list
(`{"_redacted_exc"}`) or state in the docstring that arbitrary delegation is unverified — the
current wording implies it is safe because it routes to the sanctioned renderer, which the detector
does not check.

### WR-02: `test_the_driver_declares_exactly_one_exception_renderer` does not enforce AD-30-09-01

**File:** `verification/test_main_iol_exception_redaction.py:515-527`
**Issue:**
The test's stated contract is "AD-30-09-01 en forma ejecutable: una decisión, no 32. Un autor
futuro que agregue un segundo renderer debe confrontar este test en vez de rodear al primero."
The implementation cannot deliver that. It filters `tree.body` for `ast.FunctionDef` whose `name ==
"_redacted_exc"` and asserts the count is 1. Three ways past it:

1. A second renderer under **any other name** (`_render_exc`, `_fmt_exc`) is not counted. Per
   WR-01 row 8, its body is also invisible to `_raw_exception_renders`, because the exception
   arrives as a *function parameter* — never bound by an `ast.ExceptHandler` — so the detector
   never inspects it. `def _fmt(e): return str(e)` plus `actual=_fmt(exc)` at 32 call sites
   passes the entire suite green.
2. `ast.AsyncFunctionDef` is not matched, so `async def _redacted_exc` alongside the existing sync
   one still yields `len(renderers) == 1`.
3. Only module-level `tree.body` is scanned; a nested or conditionally-defined renderer is invisible.

The same gap means an edit to `_redacted_exc`'s **own body** is not caught by the AST lock either —
only by the section-1 unit tests, which pin exact output for 5 concrete exception types.

**Fix:**
```python
def test_the_driver_declares_exactly_one_exception_renderer() -> None:
    tree = ast.parse(_DRIVER_PATH.read_text(encoding="utf-8"))
    fn_types = (ast.FunctionDef, ast.AsyncFunctionDef)
    # Any module-level function whose body reads the exception message surface is
    # a renderer, whatever it is called: AD-30-09-01 is about the count of
    # decisions, not about one name.
    renderers = [
        node
        for node in ast.walk(tree)
        if isinstance(node, fn_types)
        and any(
            isinstance(n, ast.Call)
            and _called_name(n.func) in ("repr", "str")
            or (isinstance(n, ast.Attribute) and n.attr in ("message", "args"))
            for n in ast.walk(node)
        )
    ]
    assert [n.name for n in renderers] == ["_redacted_exc"], (
        f"renderers no sancionados: {[n.name for n in renderers]}"
    )
```

### WR-03: 22 sites still read `exc.status_code` inline, bypassing the sanctioned renderer's int guard

**File:** `main_iol.py:425`, `:460`, `:497`, `:512`, `:584`, `:599`, `:654`, `:672`, `:733`, `:751`, `:803`, `:818`, `:866`, `:881`, `:943`, `:961`, `:1068`, `:1086`, `:1616`, `:1631` (plus `:1741`, `:1770-1771`)
**Issue:**
Every one of these is `diff=f"status_code={exc.status_code!r}"` — an inline expression that reads an
attribute off the exception and formats it into a durable finding. `_redacted_exc` guards the same
read with `isinstance(raw_status, int)` for the reason its own docstring gives at lines 259-264
(WR-06: "formatear un valor arbitrario sería una fuga a través de la mismísima expresión escrita
para evitar fugas"). That reasoning applies verbatim to these 22 sites, and none of them has the
guard.

So AD-30-09-01's "una decisión, no 32" is true of the `actual=` argument only. The `diff=` argument
is still 22 independent decisions reading exception internals — exactly the drift shape the AD says
it eliminated — and WR-01 shows the AST lock cannot see them.

Not Critical because no leak exists today: every construction site in the package
(`_core.py:123/125/127/156/193/211/371/454/457`) passes an `int`, so `status_code` is always an
`int` in practice. But `IOLAPIError.__init__(self, status_code: int, ...)` is an unchecked
annotation, not an enforced invariant, and 11 of these handlers are `except Exception` reached by
third-party types.

**Fix:** route `diff` through the same boundary. Either drop it (it is already redundant with
`actual=_redacted_exc(exc)`, which reports the identical fact), or add a second sanctioned helper:
```python
def _redacted_status(exc: BaseException) -> str:
    """Único render del status para ``diff=``. Mismo guard que ``_redacted_exc``."""
    raw = getattr(exc, "status_code", None)
    return f"status_code={raw if isinstance(raw, int) else None!r}"
```
and extend `test_the_driver_declares_exactly_one_exception_renderer` (per WR-02) to allow exactly
these two names.

### WR-04: `_redacted_exc` can itself raise, turning a reportable finding into an unredacted crash

**File:** `main_iol.py:280`
**Issue:**
`raw_status = getattr(exc, "status_code", None)` swallows only `AttributeError`. `status_code` is
commonly implemented as a property delegating to a response object; if such a property raises
anything else (`TypeError`, `KeyError`, a library-specific error on a detached response),
`_redacted_exc` propagates out of the `except` block it was called from. Every call site is inside
an exception handler with no further guard, so the probe aborts, `append_finding` is never reached,
and — via CR-02 — the escaping exception is rendered raw to stderr. The helper written to prevent a
leak becomes the trigger for one.

**Fix:**
```python
    try:
        raw_status = getattr(exc, "status_code", None)
    except Exception:
        # Un ``status_code`` que es property y levanta no puede convertir el
        # render de un finding en un crash: el status es un extra triageable,
        # no un requisito del reporte.
        raw_status = None
    status_code = raw_status if isinstance(raw_status, int) else None
```

### WR-05: the async surface has no end-to-end redaction coverage

**File:** `verification/test_main_iol_exception_redaction.py:300-378`
**Issue:**
Section 2 exercises three sync entry points only: `probe_get_quote_sync`, `probe_login_sync`,
`probe_refresh_token`. The 11 handlers in the five async probes (lines 447, 573, 588, 603, 722,
740, 758, 855, 870, 885, 1057, 1075, 1093 of `main_iol.py`) and the async cascade sink
`_auth_failure_reason = f"async login: ..."` (line 449) have no behavioral coverage — they are
pinned only by the AST lock, which WR-01 and WR-02 show is not load-bearing. CLAUDE.md's dual
sync/async rule ("cualquier fix de lógica debe espejarse en `client.py` y `aio.py`") is about the
packages, but the same mirroring discipline is what makes the async half of this driver a distinct
regression surface.

`test_probe_login_sync_redacts_both_the_finding_and_the_cascade_reason` is precisely the case that
needs a twin: it is the only test asserting the cascade-reason sink, and the async cascade writes
the same global.

**Fix:** add an async mirror using the existing marker helpers:
```python
async def test_probe_login_async_redacts_both_the_finding_and_the_cascade_reason(
    recorded: list[dict[str, Any]],
) -> None:
    """Espejo async de la cascada: mismo sink global, surface distinta."""
    inner = httpx.AsyncClient(
        transport=httpx.MockTransport(_handler_401_with_marker), base_url=_BASE_URL
    )
    aclient = AsyncClient(
        base_url=_BASE_URL, username="u", password="p",
        token="tok-de-prueba", token_expires_at=time.time() + 3600,
        http_client=inner,
    )
    try:
        result = await main_iol.probe_login_async(aclient)
    finally:
        await aclient.aclose()

    assert result.status == "FINDING"
    assert recorded[0]["actual"] == "IOLAuthError status_code=401", repr(recorded)
    assert _offending_kwargs(recorded) == []
    assert _WIRE_BODY_MARKER not in main_iol._auth_failure_reason
    assert main_iol._auth_failure_reason.startswith("async login: ")
```
(`asyncio_mode = "auto"` is already configured, so no marker is needed.)

### WR-06: a legitimately zero `ultimoPrecio` emits a permanent OPEN finding on every run

**File:** `main_iol.py:143-144`, `main_iol.py:540-553`
**Issue:**
`_PRICE_MIN = 0.0` and the gate is strict on both sides: `if not (_PRICE_MIN < ultimo < _PRICE_MAX)`.
So `ultimoPrecio == 0.0` fails the gate. The finding's own `diff` string names "instrumento sin
cotización" as a cause, i.e. the code acknowledges that a zero is a legitimate market state — an
illiquid instrument, or `GGAL` read outside market hours — and reports it as a defect anyway. Every
such run emits a new OPEN finding that no upstream change can ever close.

This is the exact failure the file argues against 400 lines earlier, in its own WR-02 comment
(lines 121-129): "un finding SHAPE OPEN en cada corrida viva que ningún cambio upstream puede
cerrar — ruido que entrena al operador a ignorar el archivo de findings, que es lo opuesto a lo que
este harness busca." It also compounds CR-01: this is the finding most likely to be emitted first
each run, so it is the one that clobbers the triaged `F-01`.

**Fix:** either treat a zero as a distinct, non-defect condition, or fold it into the PASS detail:
```python
    ultimo = quote.ultimoPrecio
    if ultimo == 0.0:
        # Cardinalidad de mercado, no forma: un instrumento sin cotización en el
        # momento del run devuelve 0.0 legítimamente. Un finding OPEN acá no lo
        # puede cerrar ningún cambio upstream (misma regla que la nota WR-02 de
        # ``_ASSUMED_QUOTE_FIELDS``).
        return (ProbeResult("get_quote_sync", "PASS", "ultimoPrecio=0.0 (sin cotización)"), quote)
    if not (_PRICE_MIN < ultimo < _PRICE_MAX):
        ...
```

## Info

### IN-01: `_redacted_exc` hardcodes the literal `"IOLDecodeError"` instead of the runtime class name

**File:** `main_iol.py:277`
**Issue:** The `IOLDecodeError` branch returns `f"IOLDecodeError model=..."` while the fallback at
line 282 uses `type(exc).__name__`. A future subclass of `IOLDecodeError` would be mislabeled in a
durable, git-versioned finding, and the operator would triage against the wrong class.
**Fix:** `return f"{type(exc).__name__} model={exc.model} path={exc.field_path} ..."`. The
section-1 test at line 285 (`rendered != "IOLDecodeError status_code=None"`) still passes; consider
tightening it to an exact-equality assertion like its three siblings.

### IN-02: `probe_get_quote_async` omits the price plausibility check its sync mirror performs

**File:** `main_iol.py:618-620` vs `main_iol.py:531-558`
**Issue:** The sync probe runs the `_PRICE_MIN`/`_PRICE_MAX` gate; the async probe reads
`quote.ultimoPrecio` and returns PASS unconditionally. The docstring says "Espejo async del probe
3", which is now inaccurate. Undocumented asymmetry in a file whose stated purpose is detecting
sync↔async divergence.
**Fix:** either mirror the check or state in the async docstring that the plausibility gate is
deliberately sync-only (one HTTP surface is enough to catch a magnitude corruption), so a future
reader does not restore it by accident.

### IN-03: `ultimoPrecio` is written verbatim into the durable findings file

**File:** `main_iol.py:550`, `main_iol.py:558`, `main_iol.py:620`
**Issue:** `actual=f"ultimoPrecio={ultimo!r}"` puts a raw wire *value* into
`.planning/verification/iol-client-findings.md`, and `ProbeResult.detail` puts it on stdout. Every
other finding in the file reports keys and type names only (`schema_of` is PII-free by
construction, `verification/schema.py:1-20`). The value here is a public equity last price, so the
exposure is benign — but it is the one deliberate exception to the file's contract and nothing
records that it was a decision.
**Fix:** add a one-line comment at line 550 stating why a public market price is exempt from the
"claves y tipos, nunca valores" rule (the finding is *about* the magnitude, so redacting it would
make it untriageable — same argument as the `IOLDecodeError` exemption at lines 266-270).

### IN-04: `main()` never closes the sync `Client`

**File:** `main_iol.py:1882`, `main_iol.py:1871-1987`
**Issue:** `client = Client()` is created and never closed, while `_async_main` correctly closes its
`AsyncClient` in a `finally` (lines 1850-1852). `Client` implements `__enter__`/`__exit__`/`close`
(`client.py:189-200`) and the new test file uses the context-manager form. The sync run leaks its
`httpx` connection pool and emits a `ResourceWarning` at interpreter shutdown.
**Fix:** wrap the probe sequence in `with Client() as client:`; note this interacts with CR-02 —
under the excepthook fix the `with` still closes the pool on the crash path.

### IN-05: `isinstance(raw_status, int)` accepts `bool`

**File:** `main_iol.py:281`
**Issue:** `bool` is a subclass of `int`, so an exception exposing `status_code = True` renders
`status_code=True` in a durable finding. Not a leak, but a meaningless status that costs an
operator a triage cycle. Same applies to `IntEnum`, which renders as
`<HTTPStatus.NOT_FOUND: 404>`.
**Fix:** `if isinstance(raw_status, int) and not isinstance(raw_status, bool)` — or normalize with
`int(raw_status)` after the guard so an `IntEnum` renders as a plain number.

---

_Reviewed: 2026-08-23T03:10:20Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
