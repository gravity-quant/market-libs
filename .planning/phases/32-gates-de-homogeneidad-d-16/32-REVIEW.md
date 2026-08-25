---
phase: 32-gates-de-homogeneidad-d-16
reviewed: 2026-08-25T22:18:07Z
depth: standard
files_reviewed: 19
files_reviewed_list:
  - .github/workflows/ci.yml
  - packages/ambito-financiero-client/tests/test_decode.py
  - packages/ambito-financiero-client/tests/test_surface_parity.py
  - packages/higyrus-client/tests/test_decode.py
  - packages/higyrus-client/tests/test_surface_parity.py
  - packages/iol-client/tests/test_surface_parity.py
  - packages/iol-client/tests/test_surface_types_red.py
  - packages/market-data-client/src/market_data_client/aio.py
  - packages/market-data-client/tests/test_core_boundary_red.py
  - packages/market-data-client/tests/test_surface_parity.py
  - packages/matriz-client/tests/test_decode.py
  - packages/matriz-client/tests/test_surface_parity.py
  - packages/matriz-client/tests/test_ws_decode_mode.py
  - packages/wallets-client/tests/test_surface_parity.py
  - pyproject.toml
  - tools/check_decode_intactness.py
  - tools/check_surface_types.py
  - tools/surface_parity.py
  - verification/test_public_surface.py
findings:
  critical: 2
  warning: 10
  info: 5
  total: 17
status: issues_found
---

# Phase 32: Code Review Report

**Reviewed:** 2026-08-25T22:18:07Z
**Depth:** standard
**Files Reviewed:** 19
**Status:** issues_found

## Summary

Phase 32 ships two new stdlib-AST/introspection gates (`tools/check_surface_types.py`,
`tools/surface_parity.py`), six per-package parity hooks, two RED-proof suites, one
public-API addition (`http_client` on `market_data_client.aio.configure`), and a
Wave-0 batch of mypy fixes in three decode test files.

The build is green as submitted: `ruff check`, `ruff format --check`, `mypy` (global
+ all six per-package test loops), `tools/check_surface_types.py`, and all 23 new
parity/red tests pass locally. That is the upper bound and it is not in dispute.

The problem is the **lower bound**. Both new gates are sold on non-vacuity — the
`check_surface_types.py` docstring promises "a problem, never a skip", and
`surface_parity.py` bills itself as "the affirmative substitute for the twice-abandoned
codegen requirement", the thing that makes divergence "impossible to **keep**". Neither
claim survives contact:

- `check_surface_types.py` reports **GREEN** on a tree carrying `-> dict[str, Any]` on
  an exported surface, in three separately reachable shapes (alias re-export,
  conditionally-defined class, `__all__ +=`). Reproduced against the real gate. One of
  those shapes is already live in `matriz-client` today on two `__all__` names.
- `surface_parity.py` never compares `__init__`, never compares parameter order,
  defaults, or positional-vs-keyword-only, and never compares module-level constants
  or type aliases. There are **three live sync/async divergences in the repo right now**
  that the gate reports green — including `market_data_client.Client.__init__` missing
  the exact `http_client` kwarg whose absence from `aio.configure` this phase was
  written to close.

Neither gate's own RED suite catches any of this, because both suites exercise only the
one shape the gate handles. The rest of the findings are secondary: an unhermetic
subprocess resolution, a per-package test coupled to five packages, an async
`configure`/`aclose` interleaving hazard on the newly-public kwarg, and two Wave-0
"mypy fixes" that changed what a test proves rather than only what the checker accepts.

No `<structural_findings>` block was supplied, so this report is narrative-only.

## Critical Issues

### CR-01: `check_surface_types.py` silently skips exported names it resolves but cannot locate — three shapes report GREEN

**File:** `tools/check_surface_types.py:395-426` (candidate collection), `tools/check_surface_types.py:240-267` (`_definition_sites`), `tools/check_surface_types.py:206-237` (`_all_names`)

**Issue:**
The gate builds `by_submodule` (name -> submodule), opens the file, then collects
`candidates` only for AST nodes whose `.name` is in `wanted`. When **zero** candidates
match a wanted name, nothing is recorded and nothing is reported. Every other
unresolvable condition in this file appends to `problems`; this one does not. The
module docstring's contract — "a package whose `src/<import_name>/` directory cannot be
resolved, whose `__init__.py` declares no module-level `__all__`, or whose `__all__` is
not a literal, is reported as a **problem**, never skipped" — is not enforced for the
resolved-but-not-found case, which is the commonest one.

Three reachable shapes hit it. Reproduced against the shipped gate with a synthetic
three-package tree, each offender returning `dict[str, Any]` from an exported member:

```
RESULT: surface types: 3 packages, 3 `__all__` names, 1 definitions scanned, 0 exempted (none), 0 violations
```

1. **Alias re-export.** `_definition_sites` keys on `alias.asname or alias.name`
   (line 257), so `from pkg.client import Client as MDClient` maps `MDClient -> client`
   — but `client.py` contains a `ClassDef` named `Client`, not `MDClient`. Zero
   candidates. The whole class, every method, silently unscanned.
2. **Conditionally-defined export.** Candidate collection iterates `module_tree.body`
   only (line 406). A class or function defined under `if sys.version_info >= (3, 12):`
   or inside `try:` is invisible. Zero candidates, silent.
3. **`__all__ +=`.** `_all_names` handles `ast.Assign` and `ast.AnnAssign` and returns
   at the first match (line 213-233). `__all__ += [...]` is `ast.AugAssign` — never
   handled, so every name added that way is never scanned and never reported.
   Reproduced: a package whose `__all__ += ['get_b']` names a `-> dict[str, Any]`
   function scans green at "1 definitions scanned, 0 violations".

Related, same function: `_all_names` filters `value.elts` to `ast.Constant` string
elements (line 229-233) and drops everything else in silence, so
`__all__ = ["a", *models.__all__]` passes the "is a list/tuple literal" check and then
loses the starred names without a word.

**This is already live.** Scanning the real tree, two of matriz-client's 178 exported
names resolve to a module that does not define them:

```
RESOLVED-BUT-NO-TOPLEVEL-DEF: matriz-client DEFAULT_MARKET_DATA_ENTRIES -> ws_client
RESOLVED-BUT-NO-TOPLEVEL-DEF: matriz-client MARKET_DATA_ENTRIES        -> ws_client
```

`__init__.py:94-96` imports them from `ws_client`, which itself only re-imports them.
They are constants today so nothing is lost — but the same re-export-through-an-
intermediate shape applied to a `Client` class would silently take that class's entire
method surface out of the gate, with a green summary line.

`packages/iol-client/tests/test_surface_types_red.py` does not catch any of this: its
`test_empty_and_unresolvable_trees_are_failures_not_greens` covers the three conditions
the gate *does* report, and its lower-bound cases both use plain, unconditional,
non-aliased module-level definitions.

**Fix:**

```python
# in scan_surface_types, after the candidate loop for each submodule:
            matched = {qualified.split(".", 1)[0] for qualified, _, _ in candidates}
            # names legitimately bound by a module-level assignment (constants,
            # __version__) are not definitions and are not expected to match:
            assigned = {
                t.id
                for node in module_tree.body
                if isinstance(node, ast.Assign)
                for t in node.targets
                if isinstance(t, ast.Name)
            } | {
                node.target.id
                for node in module_tree.body
                if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
            }
            for missing in sorted(wanted - matched - assigned):
                problems.append(
                    f"    package `{package_dir.name}` resolves `{missing}` to "
                    f"`{submodule}`, which contains no top-level definition or "
                    f"assignment of that name -- an export the gate cannot inspect "
                    f"is a problem, never a skip"
                )
```

and in `_all_names`, accumulate across the module instead of returning at the first
binding, handling `ast.AugAssign`, and failing on non-`Constant` elements:

```python
        elif isinstance(node, ast.AugAssign):
            targets = [node.target]
        ...
            for element in value.elts:
                if not (isinstance(element, ast.Constant) and isinstance(element.value, str)):
                    raise _fail(
                        f"    package `{label}` has a non-literal element in `__all__` "
                        f"-- the exported surface is not statically readable"
                    )
```

Add the three shapes to `test_surface_types_red.py` so the RED proof actually bounds
the gate below.

### CR-02: `surface_parity.py` never compares `__init__`, and a live `Client`/`AsyncClient` constructor divergence sits undetected in the package this phase edited

**File:** `tools/surface_parity.py:238-245` (`_public_member_names`), `tools/surface_parity.py:372-391` (class axis)

**Issue:**
`_public_member_names` returns `frozenset(name for name in dir(cls) if not name.startswith("_"))`.
`__init__` starts with `_`, so the constructor — the single largest keyword surface on
either class, and the one place a `Client` and an `AsyncClient` most plausibly drift —
is excluded from both the name comparison and the hint comparison. Nothing else in the
gate covers it: the module axis skips classes entirely (`tools/surface_parity.py:321-323`).

This is not hypothetical. Measured against the current tree:

```
market_data_client | sync-only: [] | async-only: ['token', 'token_expires_at', 'http_client'] | order-drift: True

SYNC : Client.__init__(self, *, base_url, client_id, client_secret, audience,
        auth0_token_url, mutating_allowed, expected_host, strict_decode, max_retries=2)
ASYNC: AsyncClient.__init__(self, *, base_url, client_id, client_secret, audience,
        auth0_token_url, token, token_expires_at, http_client: httpx.AsyncClient | None,
        mutating_allowed, expected_host, strict_decode, max_retries=2)
```

`packages/market-data-client/tests/test_surface_parity.py` passes green on that tree.
The drift is *the same defect class* the phase set out to close: `aio.py:783-786` adds
`http_client` to `aio.configure` because "el gate de paridad `tools/surface_parity.py`
lo detectó", while the sync `Client` constructor still cannot accept an injected
transport at all and `AsyncClient.__init__` can. A consumer writing symmetric
sync/async code hits `TypeError: __init__() got an unexpected keyword argument
'http_client'` on the sync side. The gate that was added specifically to make this
class of divergence impossible to keep does not see it one call away from where it was
first found.

**Fix:** compare `__init__` explicitly at the class axis — it is the one dunder whose
signature this repo owns.

```python
# tools/surface_parity.py, in class_parity_report, after the member loop:
    # `__init__` is excluded by the underscore filter but is the largest keyword
    # surface on either class and the likeliest drift site (Phase 32 CR-02).
    compared += 1
    mismatches.extend(
        _diff_hints(
            f"{sync_cls.__name__}.__init__",
            normalized_hints(sync_cls.__init__, surface="sync"),
            normalized_hints(async_cls.__init__, surface="async"),
        )
    )
```

and record the rule in the numbered `THE NORMALIZATION` table. Then close the
divergence it reports: give `market_data_client.Client.__init__` the `token`,
`token_expires_at` and `http_client: httpx.Client | None` kwargs its `configure`
already accepts (`client.py:820-824`), or state in the table why the constructor
surfaces are allowed to differ.

## Warnings

### WR-01: parity compares annotations, not signatures — order, defaults and keyword-only drift all pass

**File:** `tools/surface_parity.py:259-296`

**Issue:** `normalized_hints` uses `typing.get_type_hints(obj)`, which returns an
unordered name->type mapping and carries no information about parameter *kind*,
*defaults*, `*args`/`**kwargs`, or ordering. Demonstrated against the shipped helper:

```python
def sync_f(a: str, b: int = 1) -> str: ...
async def async_f(b: int, *, a: str = "x") -> str: ...
_diff_hints("f", normalized_hints(sync_f, surface="sync"),
                 normalized_hints(async_f, surface="async"))
# -> []   (reordered, defaulted, and made keyword-only: reported as agreeing)
```

Live instance: `market_data_client.client.configure` declares `base_url` as the first
keyword, `market_data_client.aio.configure` declares it sixth. Harmless because both
are keyword-only, but it is exactly the drift the gate claims to freeze, and a *default
value* change (`mercado: str = "bcba"` on one surface, `"nyse"` on the other) is the
same blind spot with real consequences.

**Fix:** compare `inspect.signature(obj)` structurally alongside the resolved hints —
parameter names in order, `kind`, and `default` — and normalize `httpx.AsyncClient` on
the annotation as today. `get_type_hints` is still required for the annotation values;
`inspect.signature` supplies the shape it cannot see.

### WR-02: `public_names`'s `__module__` filter drops package-owned constants and type aliases, hiding real module-surface divergence

**File:** `tools/surface_parity.py:218-235`

**Issue:** The filter `getattr(member, "__module__", None) != module.__name__` is
documented as dropping "re-exported third-party objects (`httpx`, `asyncio`) and
imported submodules". It also drops every module-level constant (a `str`/`tuple`/`dict`
has no `__module__`), every `Literal` type alias (`__module__ == 'typing'`), and every
re-exported model or exception the module publishes. Measured differences the gate is
blind to:

- `market_data_client.aio` exposes `RequestSpec` at module level; `market_data_client.client` does **not**.
- `matriz_client.client` exposes `load_dotenv`; `matriz_client.aio` does **not**.
- `iol_client.client.InstrumentType` (a `Literal` alias the package owns and both
  surfaces re-export) is never compared on either axis.

All three are name-set divergences between `client.py` and `aio.py` that
`assert_module_parity` reports green.

**Fix:** widen the filter to also keep names the package owns but that carry a foreign
or absent `__module__` — e.g. keep a name when its value is not a `ModuleType` and the
name is either in the module's own `__all__` or absent from the module's import graph.
At minimum, state the exclusion explicitly in `THE METRIC, STATED ONCE` so a reader is
not told the filter drops only third-party objects.

### WR-03: the class axis has a hard-coded floor of 1, contradicting the module's own per-package-bounds argument

**File:** `tools/surface_parity.py:485-486`

**Issue:** `assert_class_parity` uses `if report.compared_hints < 1`. The same module
spends a whole docstring section (`THE LOWER BOUNDS ARE PER-PACKAGE INTEGERS`, lines
111-130) arguing that a shared floor is arithmetically wrong — "A shared floor set low
enough for wallets would make the matriz assertion meaningless" — and then applies a
shared floor of 1 to the class axis, where matriz's `Client` carries ~30 methods. Two
classes that collapsed in lockstep to a single shared method pass. `ParityReport.sync_count`
and `async_count` are populated on this axis (lines 399-400) and never asserted against
anything.

**Fix:** add a `CLASS_LOWER_BOUNDS: dict[str, tuple[int, int]]` beside
`MODULE_LOWER_BOUNDS`, measured the same way, and assert `report.sync_count` /
`report.async_count` against it in `assert_class_parity` — the fields are already
computed.

### WR-04: `MODULE_LOWER_BOUNDS` is a hardcoded roster with no disk cross-check; a seventh package gets zero parity coverage silently

**File:** `tools/surface_parity.py:146-156`

**Issue:** Parity coverage is the intersection of two hand-maintained lists: the six
keys of `MODULE_LOWER_BOUNDS` and the six `packages/*/tests/test_surface_parity.py`
files. Neither is derived from disk and nothing cross-checks them. A seventh package
enters the workspace with **no** parity test and **no** bounds entry, and every gate
stays green — omission by silence, the exact failure mode this phase is written against.

The sibling gate two files away adopts the opposite discipline and says so in prose
(`tools/check_surface_types.py:61-70`, "THE ROSTER COMES FROM DISK ... a seventh package
entering the workspace is scanned automatically rather than silently exempted by
omission"). `tools/check_decode_intactness.py`'s Check D does the same. Only
`surface_parity.py` skipped it.

**Fix:** add a roster test — in `tools/` or as a seventh assertion in one of the hook
files:

```python
def test_every_workspace_package_has_a_parity_floor() -> None:
    on_disk = {
        next(p.iterdir()).name
        for p in sorted((_REPO_ROOT / "packages").glob("*/src"))
    }
    assert set(MODULE_LOWER_BOUNDS) == on_disk, (
        "a package entered or left the workspace without a measured parity floor; "
        "add its (client_min, aio_min) and a packages/<pkg>/tests/test_surface_parity.py"
    )
```

### WR-05: `test_core_boundary_red.py` resolves `lint-imports` off `PATH`, so its hermeticity claim is false and its failure message is misleading

**File:** `packages/market-data-client/tests/test_core_boundary_red.py:120-135`

**Issue:** The docstring states "the only input is the resolved absolute path of a
locked dev dependency's console script". `shutil.which("lint-imports")` returns
whatever is first on `PATH` — not necessarily the workspace venv's. Two consequences:

1. Any runner that does not export the venv's `bin` on `PATH` (an IDE test runner,
   `python -m pytest` against the venv interpreter directly, a `tox`-style wrapper)
   trips the `assert executable is not None` with the message "import-linter is a locked
   dev dependency ... and the environment is broken", which misdiagnoses the failure.
   Reproduced: `.venv/bin/python -m pytest packages/market-data-client/tests/test_core_boundary_red.py`
   fails both tests at line 123; the same command with `PATH=.venv/bin:$PATH` passes.
2. On a machine with a globally installed `import-linter`, a **different version** runs
   silently — against a test that asserts the exact output strings
   `"... KEPT"`, `"... BROKEN"` and `"Contracts: N kept, M broken."`, and against the
   workspace `pyproject.toml` it may not be able to resolve.

**Fix:** prefer the interpreter-adjacent script, fall back to `PATH`:

```python
candidate = Path(sys.executable).with_name("lint-imports")
executable = str(candidate) if candidate.is_file() else shutil.which("lint-imports")
```

### WR-06: a market-data-client test asserts on the boundary state of all five packages

**File:** `packages/market-data-client/tests/test_core_boundary_red.py:149-157`, `169-184`

**Issue:** Both legs iterate `_other_contract_names()` and assert every other declared
contract is `KEPT`, plus the aggregate `Contracts: 5 kept, 0 broken.` line. A developer
mid-refactor on `iol_client._core` — a package with no relationship to market-data —
sees `packages/market-data-client/tests/test_core_boundary_red.py` fail, in a repo whose
`CLAUDE.md` states "sin código compartido entre paquetes (por diseño)" and whose CI test
job is deliberately partitioned per package.

The docstring justifies naming the contract ("Asserting only `returncode != 0` would be
satisfied by a typo in the argv..."), which is right, but that goal is met by asserting
`_CONTRACT KEPT`/`_CONTRACT BROKEN` alone. The other four contracts and the aggregate
count add cross-package coupling without adding attribution.

**Fix:** keep the named-contract assertions; drop the loop over `others` and the
`Contracts: N kept, M broken.` count, or downgrade both to an assertion that the
contract count *parsed from the output* equals `len(_declared_contract_names())`
without asserting each one's state.

### WR-07: `aio.configure(http_client=...)` writes lock-protected state outside the lock and can be silently discarded by an in-flight `aclose()`

**File:** `packages/market-data-client/src/market_data_client/aio.py:850-859`, interacting with `aio.py:175-189` and `aio.py:270-292`

**Issue:** `_state.http_client` is otherwise only mutated under `_state.client_lock`
(`_ensure_http_client`, lines 281-292) or at the tail of `aclose()`. The new
`configure(http_client=...)` writes it directly, from a plain `def`, with no lock.

The concrete interleaving:

```
task A: await client.aclose()
        -> http_client = self._state.http_client        # old client
        -> await http_client.aclose()                   # <-- suspension point
task B: aio.configure(http_client=NEW)                  # _state.http_client = NEW
task A:    self._state.http_client = None               # NEW discarded, unclosed
```

The injected `NEW` is dropped on the floor and the next request lazily builds a third
client — the very connection-pool leak the accompanying `ResourceWarning` (line 852-858)
is meant to warn about, now caused by the code that emits it. The docstring's remedy
("Call `await market_data_client.aio.aclose()` before configure(...)") only covers the
opposite order.

Second, smaller problem in the same block: the new kwarg is a public, untyped-caller-
reachable entry point, and the only runtime type check on the object it stores is
`assert isinstance(http_client, httpx.AsyncClient)` at `aio.py:187` / `aio.py:279`.
Under `python -O` those asserts vanish and an `httpx.Client` handed to
`aio.configure(http_client=...)` surfaces as `AttributeError: 'Client' object has no
attribute 'aclose'` or a `TypeError` on `await http.send(req)`, far from the call that
caused it.

**Fix:** make `aclose()`'s final write conditional on identity, and validate the kwarg
where it is accepted:

```python
async def aclose(self) -> None:
    ...
    if http_client is not None:
        await http_client.aclose()
        if self._state.http_client is http_client:   # do not clobber a replacement
            self._state.http_client = None

# in configure():
    if http_client is not None:
        if not isinstance(http_client, httpx.AsyncClient):
            raise TypeError(
                f"http_client must be an httpx.AsyncClient, got {type(http_client).__name__}"
            )
```

### WR-08: the `test_ws_decode_mode.py` mypy fix weakened what the test proves

**File:** `packages/matriz-client/tests/test_ws_decode_mode.py:355-363`

**Issue:** The pre-phase line was `_ws._handle_message(object(), _DIVERGENT_FRAME)`.
Passing a bare `object()` was itself an assertion: `_handle_message` reads nothing off
its `ws` parameter (correct — `ws_client.py:164-194` never touches it, unlike
`_handle_open`, which does `getattr(ws, _DECODE_STRICT_ATTR, None)` at line 133). The
replacement constructs a `_FakeWebSocketApp` — an object with `url`, `header`, a
`queue.Queue`, a `threading.Semaphore`, a `threading.Event` and callback slots — so the
test no longer distinguishes "reads nothing" from "reads something the fake happens to
provide". The mypy error was `arg-type` and would have been silenced without touching
the object under test: `cast("websocket.WebSocketApp", object())`.

Related: the `if TYPE_CHECKING: import websocket` guard added at lines 41-42 is
unnecessary — `websocket-client>=1.8.0` is a hard runtime dependency of `matriz-client`
and `ws_client.py` imports it unconditionally — and the accompanying comment
("typing-only, never imported at runtime") states a constraint that does not exist.

**Fix:**

```python
        # `_handle_message` reads nothing off `ws`; a bare object proves it.
        _ws._handle_message(cast("websocket.WebSocketApp", object()), _DIVERGENT_FRAME)
```

and drop the `TYPE_CHECKING` block in favour of a plain `import websocket`, or keep the
guard and delete the misleading comment.

### WR-09: `alias.__args__` -> `get_args(alias)` made a per-alias assertion vacuous

**File:** `packages/matriz-client/tests/test_decode.py:621`

**Issue:** `assert all(isinstance(member, str) for member in alias.__args__)` raised
`AttributeError` if `alias` ever stopped being a parameterised generic. `get_args(alias)`
returns `()` for a non-generic, and `all(...)` over an empty iterable is `True`. The
loop body then still exercises `walk_field`, so the test does not go fully green-on-
nothing — but the specific claim "every member of all nine published aliases is a
`str`" now passes vacuously for any alias that degenerates. The surrounding
`assert len(aliases) == 9` bounds the *count* of aliases, not the membership of each.

**Fix:**

```python
    for alias in aliases:
        members = get_args(alias)
        assert members, f"{alias!r} carries no Literal members"
        assert all(isinstance(member, str) for member in members)
```

### WR-10: `cast(Any, cls)` is maximal widening for a narrow variance complaint, and diverges from the sibling files in the same wave

**File:** `packages/matriz-client/tests/test_decode.py:483`, `packages/matriz-client/tests/test_decode.py:489`

**Issue:** The error being silenced is narrow — mypy objects that
`type[_SafeModel]`'s `__hash__` signature does not match `Hashable`'s, on the
`lru_cache` wrapper of `_decode.hints_for`. `cast(Any, cls)` disables *all* checking of
that argument, so a future change that passed a non-class (an instance, a string) would
type-check silently. The same Wave-0 batch went the opposite direction in the sibling
files, *removing* `# type: ignore[arg-type]` from
`packages/ambito-financiero-client/tests/test_decode.py:872` and
`packages/higyrus-client/tests/test_decode.py:697`, so the monorepo now carries two
opposite idioms for the same call, one file apart.

**Fix:** narrow the cast to the protocol mypy actually wants, or use the repo's existing
suppression idiom so the argument type stays checked:

```python
from collections.abc import Hashable
... _decode.hints_for(cast(Hashable, cls)) ...
# or, matching the sibling files:
... _decode.hints_for(cls)  # type: ignore[arg-type]
```

## Info

### IN-01: dropping `assert SILENT_SINK(...) is None` removes a runtime check in favour of a static one

**File:** `packages/ambito-financiero-client/tests/test_decode.py:799-803`, `packages/higyrus-client/tests/test_decode.py:624-628`

**Issue:** `SILENT_SINK` is an *instance* of `_SilentScope` (`_decode.py:224-241`), not a
function, and `__call__` is annotated `-> None`, so the comment's claim that mypy proves
the leg statically is correct and the change is safe. It is still a small loss: the bare
call no longer detects an override that started returning a value. The mypy error code
was `func-returns-value`, which is suppressible in place.

**Fix (optional):** `assert _decode.SILENT_SINK(...) is None  # type: ignore[func-returns-value]`

### IN-02: `_import_root` and the package roster redden on any stray directory

**File:** `tools/check_surface_types.py:167-185`, `tools/check_surface_types.py:353`

**Issue:** `_import_root` requires **exactly one** directory under `packages/<pkg>/src/`,
filtering only `.egg-info`. A `__pycache__`, a stale `build/`, or a second editable
install artifact produces "no resolvable import root" and a red `lint` job with a
message that does not name the real cause. Likewise `package_dirs` accepts any directory
under `packages/`, including dot-directories.

**Fix:** extend the filter to skip `__pycache__` and names starting with `.` in both
places, and name the rejected candidates in the failure message.

### IN-03: `_find_repo_root` anchors on a substring instead of parsing the TOML it parses anyway

**File:** `packages/market-data-client/tests/test_core_boundary_red.py:82-94`

**Issue:** `"[tool.importlinter]" in config.read_text(...)` matches the literal text
anywhere in the file, including inside a comment or a string. `_declared_contract_names`
already does `tomllib.loads` on the same file eleven lines later.

**Fix:** anchor with `tomllib.loads(...).get("tool", {}).get("importlinter")` in the
loop, and cache the parsed document.

### IN-04: `pyproject.toml` silently enrols `market-data-client/src` in the global mypy scope

**File:** `pyproject.toml:97`

**Issue:** The phase adds `"packages/market-data-client/src"` to `[tool.mypy] files`.
This is a real improvement — that package's source had never been in the global strict
loop despite six packages being listed — but it is an undeclared scope change riding
along in a gates phase, with no comment, no CI step, and no mention in the step comments
added to `ci.yml`. Confirmed clean (`mypy` reports 75 source files, no issues).

**Fix:** add a one-line comment beside `files` recording when and why market-data joined,
matching the density of the surrounding config comments.

### IN-05: `verification/test_public_surface.py`'s new comment contradicts `testpaths`

**File:** `verification/test_public_surface.py:56-62`, `pyproject.toml:106`

**Issue:** The added block states "``verification/`` has never executed in CI", which is
true of the `test` job, while `testpaths = ["packages", "tests", "verification"]` means
it *does* run under a bare `uv run pytest` locally. A reader taking the comment at face
value could conclude the directory is dead and stop maintaining it.

**Fix:** qualify the claim — "never executed **in the CI `test` job**; still collected by
a bare `uv run pytest` locally" — so the two statements do not read as contradictory.

---

_Reviewed: 2026-08-25T22:18:07Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
