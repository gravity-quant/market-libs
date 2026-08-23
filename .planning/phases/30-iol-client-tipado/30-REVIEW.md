---
phase: 30-iol-client-tipado
reviewed: 2026-08-23T18:55:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - main_iol.py
  - verification/test_main_iol_exception_redaction.py
  - verification/test_main_iol_fid_seed.py
findings:
  critical: 1
  warning: 5
  info: 3
  total: 9
status: issues_found
---

# Phase 30: Code Review Report (re-review after 30-10 / 30-11)

**Reviewed:** 2026-08-23T18:55:00Z
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Re-review of `main_iol.py` and its two verification suites after plans 30-10 (close CR-01
`_fid_counter` unseeded, CR-02 uncaught-exception leak) and 30-11 (widen the AST regression
lock for WR-01 / WR-02) landed. `uv run pytest` on the two suites: 47 passed. `ruff check`
and `mypy --strict` on all three files: clean.

**Verdict on the named gaps:**

| Prior finding | Status | Evidence |
|---|---|---|
| CR-01 (`_fid_counter` unseeded) | **Closed** | `_seed_fid_counter` (main_iol.py:183-206) assigns `max_existing_fid(_PKG)`; `_next_fid` pre-increments, so the first emitted fid is `max+1` — no off-by-one. It is an assignment, not an accumulation, so a double call is idempotent and monotonic. Placement in `main()` (line 1934) is after `write_findings` and before the first probe, mirroring `main_market_data.py:3217/3221`. Verified against the real committed file (F-01 OPEN, F-02 FIXED → seed = 2 → next = F-03). |
| CR-02 (uncaught exception leaks body) | **Partially closed — see CR-01 below** | The happy path is genuinely fixed: `traceback.print_tb(tb)` emits frames only, the chained-cause test falsifies the whole family of message-rendering helpers, and `_redacted_excepthook` correctly *delegates* to `_redacted_exc` rather than reimplementing redaction (so it inherits the non-int `status_code` guard and the `IOLDecodeError` exemption for free — this is right, and the census correctly classifies it as a consumer). But the hook **fails open**: any exception raised inside it hands the original exception back to CPython's default renderer, which prints the full upstream body. Reproduced below. |
| WR-01 (AST lock ignored `ast.Attribute`) | **Mostly closed, one hole** | Rule 4 works for direct `exc.message` / `exc.args` / `exc.response` / `exc.request`. It is fully bypassable via `getattr` — see WR-01 below. |
| WR-02 (renderer census name/scope-bound) | **Mostly closed, shape-bound holes remain** | The census now matches `AsyncFunctionDef` and any scope, and correctly self-detects `_redacted_exc` (the review's own proposed snippet would have returned `[]` — good catch by the implementer). Its read-predicate still misses `%`-formatting and delegation, which matters precisely on the parameter-passed code path 30-10 introduced. See WR-02. |

No live credential or wire-body leak exists in `main_iol.py` today: I grepped every handler and
every reporting site, and all 32 route through `_redacted_exc`. The findings below are (a) one
fail-open security control and (b) holes in the regression locks that are supposed to keep it
that way.

## Critical Issues

### CR-01: `_redacted_excepthook` fails open — a failure inside the hook leaks the full upstream body

**File:** `main_iol.py:2044-2082`

**Issue:** The hook has no error handling. CPython's `PyErr_PrintEx` reacts to an exception
raised inside `sys.excepthook` by printing `Error in sys.excepthook:` followed by
`Original exception was:` and rendering the original exception **with the default renderer** —
i.e. `IOLAPIError: [500] <full upstream body>`. This is exactly the leak CR-02 exists to close,
reachable through the very function that closes it.

Reproduced (writable stderr, hook body raising):

```
Error in sys.excepthook:
  File "/Users/admin/development/market-libs/main_iol.py", line 2081, in _redacted_excepthook
    print(f"ABORT: {_redacted_exc(exc)}", file=sys.stderr)
RuntimeError: hook internals failed

Original exception was:
iol_client.exceptions.IOLAPIError: [500] ZZ-SECRET-BODY-ZZ-cuenta-999999   <-- LEAKED
```

Realistic triggers, none of which the suite covers:

- **`RecursionError` as the uncaught exception.** The hook runs with a nearly exhausted stack;
  the f-string in line 2081 and `traceback.print_tb`'s `StackSummary.extract` can both re-raise.
- **Broken or closed stderr** (`... 2>&1 | head`, or a CI runner that closed the pipe):
  `print(..., file=sys.stderr)` raises `BrokenPipeError` / `ValueError: I/O operation on closed file`.
  Confirmed: with stderr closed the interpreter emits `Error in sys.excepthook:` and falls back.
- **Any exception object whose attribute access misbehaves** — `_redacted_exc` unconditionally
  reads `exc.model` / `exc.field_path` / `exc.declared_type` / `exc.observed_type` on anything
  passing `isinstance(exc, IOLDecodeError)`. A subclass or an unpickled instance that never ran
  `IOLDecodeError.__init__` raises `AttributeError` there.

A security boundary whose failure mode is "emit the thing you were built to suppress" must fail
closed. The whole file-wide redaction argument (module docstring lines 51-59) rests on this hook.

**Fix:**

```python
def _redacted_excepthook(
    exc_type: type[BaseException], exc: BaseException, tb: TracebackType | None
) -> None:
    del exc_type
    # Fail CLOSED: nothing raised in here may reach CPython's fallback renderer,
    # which prints the exception message — i.e. the full upstream error body.
    try:
        rendered = _redacted_exc(exc)
    except BaseException:  # noqa: BLE001 — the fallback IS the contract
        rendered = "<renderer failed; exception withheld>"
    try:
        print(f"ABORT: {rendered}", file=sys.stderr)
        traceback.print_tb(tb)
    except BaseException:  # noqa: BLE001
        pass
```

Add the matching falsification to section 4 of
`verification/test_main_iol_exception_redaction.py`: monkeypatch `main_iol._redacted_exc` to
raise, run the crash through a real subprocess with `_install_redacted_excepthook()`, and assert
the marker appears in neither stdout nor stderr while the exit code stays non-zero.

## Warnings

### WR-01: `getattr` in `_SANCTIONED_DELEGATES` fully defeats the new leaky-attribute rule

**File:** `verification/test_main_iol_exception_redaction.py:616` (`_SANCTIONED_DELEGATES`),
rule 4 at lines 729-736

**Issue:** The whitelist is keyed on the **callee name**, not on the attribute argument. The
docstring justifies sanctioning `getattr` by naming one specific call shape
(`getattr(<n>, "status_code", None)`), but the implementation exempts every `getattr` call on a
bound name. Rule 4 (the rule 30-11 added to close WR-01) is therefore trivially bypassed by
spelling the attribute as a string. Measured against the shipped detector:

| Source inside a handler | `_raw_exception_renders` | `_declared_exception_renderers` |
|---|---|---|
| `append_finding("p", actual=getattr(exc, "message", ""))` | `[]` | `[]` |
| `append_finding("p", actual=str(getattr(exc, "args")))` | `[]` | `[]` |
| `append_finding("p", actual=str(exc.__dict__))` | `[]` | `[]` |

`exc.message` is literally `resp.text` (see `packages/iol-client/src/iol_client/exceptions.py:17`),
so all three write the full brokerage error body into a git-versioned artifact while the lock
reports green. `__dict__` is a third spelling of the same leak and is absent from
`_LEAKY_EXC_ATTRS`.

**Fix:** Narrow the `getattr` exemption to the argument, and extend the attribute deny-list:

```python
_LEAKY_EXC_ATTRS = ("message", "args", "response", "request", "__dict__")
_SANCTIONED_DELEGATES = ("_redacted_exc", "type", "isinstance")  # getattr handled below

# inside the ast.Call branch, before the _SANCTIONED_DELEGATES short-circuit:
if called == "getattr":
    attr = node.args[1] if len(node.args) > 1 else None
    named = attr.value if isinstance(attr, ast.Constant) else None
    if not isinstance(named, str) or named in _LEAKY_EXC_ATTRS:
        # unknown or leaky attribute name -> not sanctioned
        leaked = [a for a in node.args if isinstance(a, ast.Name) and a.id in bound_names]
        if leaked:
            offenders.add((node.lineno, f"getattr({leaked[0].id}, {named!r})"))
    continue
```

Add the three rows above to `_WR01_ROWS` so the fix cannot regress.

### WR-02: neither detector guards a renderer that receives its exception as a parameter

**File:** `verification/test_main_iol_exception_redaction.py:718-723` (`_raw_exception_renders`
only walks `ast.ExceptHandler`), `906-933` (`_reads_the_exception`)

**Issue:** The two detectors are presented as complementary belts, but they leave a joint hole
sitting exactly on the code path 30-10 introduced. `_raw_exception_renders` inspects **only**
statements inside an `ast.ExceptHandler`; `_redacted_excepthook` receives its exception from
CPython as a parameter and lives outside any handler, so that detector never looks at it. The
census is the only remaining guard, and its read-predicate recognises just four shapes
(attribute read, `getattr`, a `_STRINGIFYING_CALLS` call taking the param positionally, direct
f-string interpolation). It misses `%`-formatting, delegation-to-a-printer, and any param not
annotated with an exception type. Measured:

| Renderer body | `_declared_exception_renderers` | `_raw_exception_renders` |
|---|---|---|
| `def _fmt(exc: BaseException) -> str: return "ABORT: %s" % exc` | `[]` | `[]` |
| `def _fmt(exc: BaseException) -> None: print(exc)` | `[]` | `[]` |
| `def _fmt(exc: object) -> str: return str(exc)` | `[]` | `[]` |

Concretely: rewriting line 2081 to `print("ABORT: %s" % exc, file=sys.stderr)` reintroduces the
CR-02 leak in full and **the entire 47-test suite still passes**. Note `_raw_exception_renders`
already implements the `%`-formatting rule (rule 6) — the census simply does not share it.

**Fix:** Give `_reads_the_exception` the same rule set as `_raw_exception_renders` by extracting
the shared predicate, minimally adding the `ast.BinOp`/`ast.Mod` case and treating a call to a
non-sanctioned callee that receives the param as a read:

```python
def _reads_the_exception(func, param: str) -> bool:
    for node in ast.walk(func):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
            if isinstance(node.right, ast.Name) and node.right.id == param:
                return True
        ...
        if isinstance(node, ast.Call):
            called = _called_name(node.func)
            takes = any(isinstance(a, ast.Name) and a.id == param
                        for a in [*node.args, *(kw.value for kw in node.keywords)])
            if takes and called not in _SANCTIONED_DELEGATES:
                return True
    return False
```

Then add a case asserting `_declared_exception_renderers` flags a `%`-formatting renderer, and
re-confirm `_redacted_excepthook` still censuses as a consumer (it will: `_redacted_exc` is a
sanctioned delegate).

### WR-03: only one of the interpreter's exception sinks is installed

**File:** `main_iol.py:2085-2092`, module docstring lines 51-59

**Issue:** `_install_redacted_excepthook` assigns `sys.excepthook` only. CPython has three other
sinks that render the exception **message**, none of which consult `sys.excepthook`. Both are
demonstrably leaky against a live `IOLAPIError`:

```
# sys.unraisablehook (exception escaping __del__ during GC)
Exception ignored in: <function Boom.__del__ ...>
iol_client.exceptions.IOLAPIError: [500] ZZ-UNRAISABLE-BODY-ZZ     <-- LEAKED, rc=0

# threading.excepthook (exception escaping a worker thread)
iol_client.exceptions.IOLAPIError: [500] ZZ-THREAD-BODY-ZZ         <-- LEAKED, rc=0
```

A fourth, `asyncio`'s default loop exception handler, formats `exception` via
`traceback.format_exception` into `logging.lastResort` (stderr) for any task holding an
unretrieved exception at `asyncio.run` shutdown — and `main()` does run `asyncio.run(_async_main(today))`.

Not currently reachable with an IOL-carrying payload (`iol_client` spawns no threads — grep for
`threading` in `packages/iol-client/src/` is empty — and the driver creates no bare tasks), so
this is a WARNING, not a blocker. But the module docstring asserts the crash path is closed
without qualification, and any future `asyncio.TaskGroup`, `to_thread`, or streaming use silently
reopens it.

**Fix:** Install all four in `_install_redacted_excepthook`, and state the residual boundary in
the docstring:

```python
def _install_redacted_excepthook() -> None:
    sys.excepthook = _redacted_excepthook
    sys.unraisablehook = lambda u: _redacted_excepthook(
        type(u.exc_value) if u.exc_value else RuntimeError, u.exc_value or RuntimeError(""), u.exc_traceback
    )
    threading.excepthook = lambda a: _redacted_excepthook(a.exc_type, a.exc_value or RuntimeError(""), a.exc_traceback)
```

and set an `asyncio` exception handler inside `_async_main` that routes through `_redacted_exc`.

### WR-04: the fid-seed fixture corrupts F-01's detail block, so the seed tests pass for the wrong reason

**File:** `verification/test_main_iol_fid_seed.py:112-117`

**Issue:** `_add_finding`'s promotion path does an unanchored `str.replace` with no `count`:

```python
text = text.replace(
    "**Class:** `SHAPE` . **Surface:** `both` . **Status:** `OPEN`",
    "**Class:** `SHAPE` . **Surface:** `both` . **Status:** `FIXED`",
)
```

`_seed_committed_findings_shape()` writes F-01 and F-02 with identical class/surface, so
promoting F-02 rewrites **both** detail meta lines. The produced fixture is self-inconsistent —
its index says `| F-01 | SHAPE | both | OPEN |` while F-01's detail block says
`**Status:** `FIXED``. Reproduced:

```
| F-01 | SHAPE | both | OPEN |     <-- index
### F-01 -- operator title
**Class:** `SHAPE` . **Surface:** `both` . **Status:** `FIXED`   <-- detail, wrong
```

The docstring claims it "reproduce el estado committeado real". It does not. All four tests in
sections 1-2 pass only because `_parse_findings` happens to resolve status from the index row
rather than the detail meta — an undeclared precedence the suite never asserts. If that
precedence ever flips, `test_seeded_run_files_new_findings_above_the_committed_ones` starts
passing vacuously (F-01 would short-circuit as non-OPEN and its title would survive for the
wrong reason), which is the exact class of silent-vacuity the plan set out to eliminate.

**Fix:** Anchor the replacement to the finding's own detail block, e.g. split on the
`### {fid} --` header and rewrite only that slice, or make the fixture findings distinguishable:

```python
def _add_finding(fid: str, *, title: str, promote_to_fixed: bool) -> None:
    ...
    head, sep, tail = text.partition(f"### {fid} -- ")
    tail = tail.replace("**Status:** `OPEN`", "**Status:** `FIXED`", 1)
    path.write_text(head + sep + tail, encoding="utf-8")
```

and add an assertion that the fixture round-trips to `{"F-01": "OPEN", "F-02": "FIXED"}` through
`_parse_findings`, so a fixture that lies fails at the fixture rather than downstream.

### WR-05: the seed wiring lock verifies textual line order, not execution order

**File:** `verification/test_main_iol_fid_seed.py:273-297`

**Issue:** `_call_linenos` collects `ast.Call` line numbers anywhere inside the `main`
`FunctionDef`, including inside `if`/`try`/`with` bodies, and the lock compares raw line numbers.
A `_seed_fid_counter()` placed inside a branch that never executes — or inside a `try:` whose
`except` swallows — still satisfies `bootstrap_lines[0] < seed_lines[0] < min(probe_lines)`
while the counter stays at 0 at runtime, which is precisely the CR-01 failure the lock exists to
prevent. The test docstring claims it catches "un seed definido pero nunca llamado"; it catches
"never *written*", not "never *reached*".

**Fix:** Additionally assert the call is an unconditional top-level statement of `main`:

```python
top_level = [
    n for n in main_def.body
    if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
    and isinstance(n.value.func, ast.Name) and n.value.func.id == "_seed_fid_counter"
]
assert len(top_level) == 1, "el seed debe ser una sentencia incondicional de main()"
```

Or (stronger, and cheap here) drop the AST proxy for a behavioural check: monkeypatch
`_seed_fid_counter` with a spy, run `main()` against a mocked client, and assert it was called
exactly once before any `append_finding`.

## Info

### IN-01: two undocumented bypasses in `_raw_exception_renders`' argument scan

**File:** `verification/test_main_iol_exception_redaction.py:753-755`

**Issue:** `passed` collects only direct `ast.Name` arguments, so wrapping the bound name in any
container defeats every call-based rule: `append_finding("p", actual=str([exc]))` returns `[]`.
The docstring's "Lo que queda **sin verificar**" section lists two-level aliasing and
cross-handler data flow (both confirmed accurate) but not this one.

**Fix:** Either recurse into `ast.List`/`ast.Tuple`/`ast.Set`/`ast.Dict` when collecting `passed`,
or add the container shape to the declared-boundary list in the docstring so a future reader is
not misled about coverage.

### IN-02: `max_existing_fid` seeds from detail headers only

**File:** `main_iol.py:206` → `verification/findings.py` `_DETAIL_HEADER_FID_NUM_RE`

**Issue:** The seed reads `^###\s+F-(\d+)\b` only. A fid that exists in the `## Index` table but
has no detail block — reachable via a hand-edited findings file, which the operator-owned
prefix/suffix zones explicitly invite — is invisible to the seed, and the run re-emits it,
reproducing CR-01's collision on that fid. Not currently the case for `iol-client-findings.md`
(both F-01 and F-02 have detail blocks).

**Fix:** Have `max_existing_fid` take the max over both the index rows and the detail headers.
(Out of this phase's file scope; file as a carry-forward against `verification/findings.py`.)

### IN-03: the crash-path subprocess test inherits the operator's real credentials

**File:** `verification/test_main_iol_exception_redaction.py:1208-1220`

**Issue:** `env = {**os.environ, ...}` hands the child the full parent environment, and the child
imports `main_iol` → `iol_client` → `load_dotenv()`, so real `IOL_USER` / `IOL_PASSWORD` are
resolved inside a process whose stdout and stderr are captured and interpolated into assertion
failure messages. The file header advertises the suite as "sin credenciales, sin `.env`". No
network call occurs, so nothing is exercised with them — but a failure message could print them.

**Fix:** Pass a minimal environment and neutralise the credential vars:

```python
env = {
    "PATH": os.environ.get("PATH", ""),
    "IOL_TOKEN_CACHE_PATH": str(tmp_path / "token-cache.json"),
    "IOL_USER": "u",
    "IOL_PASSWORD": "p",
}
```

---

_Reviewed: 2026-08-23T18:55:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
