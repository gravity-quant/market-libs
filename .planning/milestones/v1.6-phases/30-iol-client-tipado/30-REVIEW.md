---
phase: 30-iol-client-tipado
reviewed: 2026-08-23T19:40:00Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - main_iol.py
  - verification/test_main_iol_exception_redaction.py
findings:
  critical: 0
  warning: 4
  info: 4
  total: 8
status: issues_found
---

# Phase 30: Code Review Report (re-review after 30-12 / 30-13)

**Reviewed:** 2026-08-23T19:40:00Z
**Depth:** standard
**Files Reviewed:** 2
**Status:** issues_found

## Summary

Re-review of `main_iol.py` and `verification/test_main_iol_exception_redaction.py` after plans
30-12 (fail-closed crash path: `_HOOK_RENDER_FAILED`, `_emit_crash_report`, two independent
`contextlib.suppress(BaseException)` blocks, plus a new AST lock on the crash-path region) and
30-13 (widen the regression lock: `getattr` adjudicated on its attribute-name argument,
`__dict__` added to `_LEAKY_EXC_ATTRS`, `%`-format and generic delegation added to the renderer
census via `_CENSUS_SANCTIONED_DELEGATES`).

Gates: `uv run pytest verification/test_main_iol_exception_redaction.py` → **64 passed**.
`ruff check` on both files → clean. `mypy` as CI runs it (`uv run mypy`) → clean, **but see
WR-04**: neither reviewed file is inside mypy's configured `files`, and `mypy --strict` on the
test file reports 6 errors, 6 of them on lines 30-12 added.

**Verdict on the named gaps:**

| Prior finding | Status | Evidence |
|---|---|---|
| CR-01 (hook fails open → default renderer prints `[500] <body>`) | **Closed** | Verified independently, not by re-reading the suite: a real subprocess with the renderer replaced by one that raises **and** `sys.stderr.close()` called before the raise — the worst combination of triggers (a)+(b)+(c) at once — produced no marker on either fd and `rc=1`. The structure is right: the renderer call sits in a `try` whose `except BaseException` assigns a *static* placeholder (`main_iol.py:2162-2165`), and each of the two stderr sinks sits in its own `contextlib.suppress(BaseException)` (`main_iol.py:2097-2100`). Splitting the guards is load-bearing and is falsified by a stream that fails only on the `ABORT` prefix. |
| WR-01 (`getattr` whitelisted by callee name) | **Closed** | Rules 9/10 adjudicate on `node.args[1]` **before** the `_SANCTIONED_DELEGATES` short-circuit, a non-constant attribute name is flagged conservatively, and one constant (`_LEAKY_EXC_ATTRS`) governs both the direct and indirect spellings so they cannot drift. `exc.__dict__` and `vars(exc)` both flag. One residual spelling walks past — WR-02 below. |
| WR-02 (census blind to `%`-format and delegation) | **Closed for the shapes named** | `_reads_the_exception` now mirrors rule 6 and inverts the delegation rule (everything counts except `_CENSUS_SANCTIONED_DELEGATES`). This is the strongest single change in the two plans: I confirmed that rewriting the hook to `traceback.print_exception(exc)` or to delegate to an `object`-annotated second renderer now **fails** `test_the_driver_declares_exactly_one_exception_renderer`, because the *caller* gets censused even when the callee escapes the annotation gate. Keeping the two delegate sets separate is correct and the docstring's reasoning for it holds. |
| WR-03 (only one of four interpreter sinks installed) | **Still open** | Unchanged and not deferred anywhere I can find. See WR-03 below. |
| IN-01 (container-wrapped names) | **Still open** | See IN-01. |
| IN-03 (subprocess tests inherit real credentials) | **Still open, now 3×** | 30-12 added two more copies of the `{**os.environ, ...}` pattern. See IN-03. |

There is no live leak in `main_iol.py` today. Every finding below is either a hole in a
regression lock that is supposed to keep it that way, or a control that was never installed.

## Warnings

### WR-01: three realistic edits walk straight past the new crash-path lock

**File:** `verification/test_main_iol_exception_redaction.py:1961-1967` (`_CRASH_PATH_FUNCTIONS`,
`_MUST_BE_GUARDED_CALLS`), `2021-2044` (`_has_an_enclosing_guard`)

**Issue:** `_unguarded_crash_path_calls` decides coverage from two **name allowlists** and a
guard-shape check that never asks whether the guard catches anything. All three are bypassable
by edits a maintainer would make without malice. Measured against the shipped detector:

| Edit to the crash path | `_unguarded_crash_path_calls` |
|---|---|
| sinks rewritten as `sys.stderr.write(...)` + `sys.stderr.flush()` + `traceback.print_exception(...)`, all unguarded | `[]` |
| both sinks extracted to `_write_abort` / `_write_frames`, called unguarded from `_emit_crash_report` | `[]` |
| `try: print(...) finally: pass` around each sink (no handler at all) | `[]` |

Each of the three restores exactly the CR-01 failure mode. Row 1 is the most likely of them:
`print(..., file=sys.stderr)` → `sys.stderr.write(...)` is a routine refactor, `write` is not in
`_MUST_BE_GUARDED_CALLS`, and a `BrokenPipeError` from it escapes the hook into CPython's
fallback renderer — the full upstream body. Row 3 is worse than the counter-case the suite
already defends (`test_..._does_not_accept_an_except_branch_as_a_guard`): a bare `try`/`finally`
suppresses nothing, yet is accepted as a guard.

The docstring declares "that the guard catches the right thing" as unverified and points at the
behavioural tests, which is fair for `except ValueError:`. It does not cover a guard with **zero**
handlers, and it says nothing about the region and call allowlists — which is where the real
fragility is. Restricting the *region* to two functions is well argued (avoiding noise); once
inside a two-function region, restricting further to three call names buys nothing and costs the
whole lock.

**Fix:** invert the call rule inside the region — every call must be guarded, with the region
made transitive so the current shape still passes and so an extraction cannot escape it:

```python
def _region_functions(tree: ast.AST) -> set[str]:
    """The seed names plus every function they call — an extraction cannot leave the region."""
    defs = {n.name: n for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)}
    region, queue = set(), list(_CRASH_PATH_FUNCTIONS)
    while queue:
        name = queue.pop()
        if name in region or name not in defs:
            continue
        region.add(name)
        queue += [c for c in (_called_name(n.func) for n in ast.walk(defs[name])
                              if isinstance(n, ast.Call)) if c]
    return region

# ...and in the per-call loop, replace the `_MUST_BE_GUARDED_CALLS` filter with:
if called in region:          # a call into the region carries its own guards
    continue
if _has_an_enclosing_guard(node, func, parents):
    continue
offenders.add((node.lineno, f"{called}() sin guard en {func.name}"))
```

and tighten the guard-shape check so a handler-less `try` does not qualify:

```python
if isinstance(parent, ast.Try) and any(stmt is child for stmt in parent.body):
    if parent.handlers:      # try/finally suppresses nothing
        return True
```

Add the three rows above as parametrised positive cases so they cannot regress, and keep
`_GUARDED_CRASH_PATH_SOURCE` as the negative control.

### WR-02: `exc.__getattribute__("message")` walks past the widened rule 9

**File:** `verification/test_main_iol_exception_redaction.py:921-942` (rules 9/10),
`736` (`_LEAKY_EXC_ATTRS`)

**Issue:** 30-13 correctly moved the `getattr` decision onto the attribute-name argument, but the
dunder spelling of the same read is invisible. Measured:

| Source inside a handler | `_raw_exception_renders` |
|---|---|
| `append_finding("p", actual=exc.__getattribute__("message"))` | `[]` |
| `append_finding("p", actual=object.__getattribute__(exc, "message"))` | `[(5, 'delegación de exc a __getattribute__()')]` — flagged |

The first form is not caught by rule 4 (`node.attr` is `__getattribute__`, not in
`_LEAKY_EXC_ATTRS`), not by rule 9 (`called` is `__getattribute__`, not `getattr`), and not by
rule 5 (the only `ast.Name` argument is the constant `"message"`, so `passed` is empty and
`leaked` is empty). `exc.message` is literally `resp.text`
(`packages/iol-client/src/iol_client/exceptions.py:17`), so this writes the full brokerage error
body into a git-versioned artifact while the lock reports green.

That the bound-method form escapes while the unbound form flags is an inconsistency, not a
policy — the same sentence `_LEAKY_EXC_ATTRS`' own comment uses to justify adding `__dict__`.

**Fix:** treat `<n>.__getattribute__(...)` / `<n>.__getattr__(...)` as an indirect attribute read
by routing it through the same adjudication as rule 9. Inside the `ast.Call` branch, before the
`getattr` case:

```python
if called in ("__getattribute__", "__getattr__") and isinstance(node.func, ast.Attribute):
    target = node.func.value
    if isinstance(target, ast.Name) and target.id in bound_names:
        attr_arg = node.args[0] if node.args else None
        if isinstance(attr_arg, ast.Constant) and isinstance(attr_arg.value, str):
            if attr_arg.value in _LEAKY_EXC_ATTRS:
                offenders.add((node.lineno, f'{target.id}.__getattribute__("{attr_arg.value}")'))
            continue
        offenders.add((node.lineno, f"{target.id}.__getattribute__(<dinámico>)"))
        continue
```

Add both rows above to `_FIFTH_CYCLE_BYPASS_ROWS` (the unbound form as a non-regression case).

### WR-03: three of the interpreter's four exception sinks are still uninstalled

**File:** `main_iol.py:2169-2176` (`_install_redacted_excepthook`), module docstring lines 51-66

**Issue:** Carried forward from the previous review, unclosed and, as far as I can find, not
deferred in writing anywhere. `_install_redacted_excepthook` assigns `sys.excepthook` and nothing
else. Confirmed against the current file: zero occurrences of `unraisablehook`, zero of
`threading`, zero of `set_exception_handler`. CPython's other three sinks all render the
exception **message** and none of them consult `sys.excepthook`:

- `sys.unraisablehook` — an exception escaping `__del__` during GC; prints the message, `rc=0`.
- `threading.excepthook` — an exception escaping a worker thread; prints the message, `rc=0`.
- the asyncio default loop handler — formats via `traceback.format_exception` into
  `logging.lastResort` (stderr) for a task holding an unretrieved exception at `asyncio.run`
  shutdown, and `main()` does run `asyncio.run(_async_main(today))` (`main_iol.py:1960`).

Still not reachable today with an IOL-carrying payload (`iol_client` spawns no threads; the
driver creates no bare tasks), which keeps it a WARNING. What escalates it relative to the last
review is that 30-12 rewrote the module docstring around the crash path and **strengthened** the
unconditional claim — lines 60-66 now assert the crash path "falla CERRADO" without naming the
residual boundary. A future `asyncio.TaskGroup`, `to_thread`, or streaming probe reopens the leak
silently against a docstring that says it cannot happen.

**Fix:** install all four, and state the boundary that remains:

```python
def _install_redacted_excepthook() -> None:
    sys.excepthook = _redacted_excepthook
    sys.unraisablehook = lambda u: _redacted_excepthook(
        type(u.exc_value), u.exc_value or RuntimeError(""), u.exc_traceback
    )
    threading.excepthook = lambda a: _redacted_excepthook(
        a.exc_type, a.exc_value or RuntimeError(""), a.exc_traceback
    )
```

plus `loop.set_exception_handler(...)` inside `_async_main` routing through `_redacted_exc`. If
this is deliberately deferred instead, say so in the docstring — the current text asserts more
than the code delivers. Note the three new lambdas land inside `_CRASH_PATH_FUNCTIONS`' blast
radius, so WR-01's transitive-region fix should go in first.

### WR-04: 30-12 introduced 6 `mypy --strict` errors that no gate can see

**File:** `verification/test_main_iol_exception_redaction.py:1705, 1729, 1843, 1867, 1894, 1897`

**Issue:** All six are on lines 30-12 added:

```
1705,1729,1843,1867,1897: "_redacted_excepthook" does not return a value
                          (it only ever returns None)  [func-returns-value]
1894: Module "main_iol" does not explicitly export attribute "traceback"  [attr-defined]
```

They are invisible to every gate: root `pyproject.toml:97` scopes `files` to
`packages/*/src`, and `.pre-commit-config.yaml` scopes the hook to `^packages/.*/src/`, so
neither `main_iol.py` nor `verification/` is ever type-checked. 30-12-SUMMARY.md step 14 records
`mypy packages/iol-client/src packages/iol-client/tests` → Success, i.e. the plan verified a
different file set than the one it edited. CLAUDE.md names `mypy strict` a stack constraint, and
the previous review recorded `mypy --strict` clean on these files as the baseline — so this is a
real regression, just not a CI-visible one.

The `func-returns-value` errors also flag a genuine readability defect. The assertion

```python
assert main_iol._redacted_excepthook(type(exc), exc, exc.__traceback__) is None, (
    "el hook debe retornar None; nada puede escaparse de él"
)
```

reads as if the return value carries the contract. It does not — `is None` is unconditionally
true for a `-> None` function that returns at all. The only thing being asserted is
*non-propagation*, which the bare call already gives you. That is the right contract; the
expression just misstates it.

**Fix:** make the intent the code:

```python
# El contrato es que NADA se escape: si el hook levantara, este test falla acá.
main_iol._redacted_excepthook(type(exc), exc, exc.__traceback__)
```

and for line 1894, monkeypatch the module directly instead of reaching through the driver's
namespace: `monkeypatch.setattr(traceback, "print_tb", _boom)` with a top-level
`import traceback`. Then either widen mypy's `files` to include `main_iol.py` and `verification/`,
or add a `verification/` step to the CI typecheck job — otherwise the next such regression is
equally invisible.

## Info

### IN-01: container-wrapped names still defeat every call-based rule

**File:** `verification/test_main_iol_exception_redaction.py:945-947`

**Issue:** Carried forward, unchanged. `passed` collects only direct `ast.Name` arguments, so
wrapping the bound name in any container clears all of rules 1/3/5. Confirmed, with a second
spelling the previous review did not list:

| Source inside a handler | `_raw_exception_renders` |
|---|---|
| `append_finding("p", actual=str([exc]))` | `[]` |
| `append_finding("p", actual=f"{[exc]}")` | `[]` |

The docstring's "Lo que queda **sin verificar**" list (lines 873-886) is otherwise accurate and
was extended thoughtfully in 30-13 — this shape is the one omission.

**Fix:** recurse into `ast.List` / `ast.Tuple` / `ast.Set` / `ast.Dict` when collecting `passed`
and into `ast.FormattedValue.value`, or add the container shape to the declared-boundary list so
a future reader is not misled about coverage.

### IN-02: the census annotation gate is a real boundary and is not declared as one

**File:** `verification/test_main_iol_exception_redaction.py:1161-1181`, `1286-1291`

**Issue:** `_annotates_an_exception` gates the whole census, so a second renderer whose parameter
is annotated `object` / `Any` / not at all is never censused. Measured — all three return
`["_redacted_exc"]` only, i.e. the duplicate is invisible:

```
def _fmt(e: object) -> str: return str(e)    -> []
def _fmt(e) -> str: return str(e)            -> []
def _fmt(e: Any) -> str: return str(e)       -> []
```

This is **not** an open leak, and 30-13 is why: the new generic-delegation rule catches the
*caller* instead. I confirmed that a hook rewritten to `_emit_crash_report(_fmt(exc), tb)` with
`_fmt(e: object)` now censuses `_redacted_excepthook` itself and fails
`test_the_driver_declares_exactly_one_exception_renderer`. The gate's noise argument
(lines 1286-1291) is also correct — dropping it would flag every probe. The gap is documentary:
the docstring explains why the gate exists but never says what it costs, and this closure
depends on a second detector rather than on this one.

**Fix:** add one bullet to `_declared_exception_renderers`' docstring naming the boundary and the
backstop, along the lines of: "un renderer anotado `object` / `Any` / sin anotar no se censa; lo
cubre la regla 4 sobre su **llamador**, no este gate."

### IN-03: the three subprocess tests hand the child the operator's real credentials

**File:** `verification/test_main_iol_exception_redaction.py:1576-1579`, `1767-1770`, `1932-1935`

**Issue:** Carried forward and now replicated: 30-12 added two more copies of

```python
env = {**os.environ, "IOL_TOKEN_CACHE_PATH": str(tmp_path / "token-cache.json")}
```

Each child imports `main_iol` → `iol_client` → `load_dotenv()`, so real `IOL_USER` /
`IOL_PASSWORD` resolve inside a process whose stdout and stderr are captured and interpolated
verbatim into assertion-failure messages. The file header advertises the suite as "sin
credenciales, sin `.env`". No network call occurs and nothing currently prints them, so exposure
is latent rather than actual — but the pattern is now the file's default for new subprocess tests,
which is how it stops being latent.

**Fix:** one shared helper so the next copy inherits the right shape:

```python
def _sealed_env(tmp_path: Path) -> dict[str, str]:
    return {
        "PATH": os.environ.get("PATH", ""),
        "IOL_TOKEN_CACHE_PATH": str(tmp_path / "token-cache.json"),
        "IOL_USER": "u",
        "IOL_PASSWORD": "p",
    }
```

### IN-04: `test_the_hook_still_prints_frames_when_the_abort_line_fails` couples to repo source text

**File:** `verification/test_main_iol_exception_redaction.py:1863`, `1874-1876`

**Issue:** `_StderrThatFailsOnWrite(fail_on="ABORT")` raises on any write whose text contains
`ABORT`. `traceback.print_tb` writes each frame's **source line** from the repo, so if any line in
a frame of `_caught` ever contains the substring `ABORT`, the frame write starts raising too and
the test fails with a message pointing at guard independence — the wrong diagnosis. Today the only
frame is `raise exc`, so it holds.

**Fix:** use a marker that cannot appear in repo source, e.g. `fail_on="\x00ABORT-SENTINEL"` is
not viable since the hook writes a literal prefix — instead assert on `writes` shape by making the
stream fail only on its *first* write, which is the ABORT line by construction, and keep the
substring assertion as the secondary check.

---

_Reviewed: 2026-08-23T19:40:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
