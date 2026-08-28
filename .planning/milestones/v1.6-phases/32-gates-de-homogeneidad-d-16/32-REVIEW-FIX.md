---
phase: 32-gates-de-homogeneidad-d-16
fixed_at: 2026-08-25T23:52:00Z
review_path: .planning/phases/32-gates-de-homogeneidad-d-16/32-REVIEW.md
iteration: 1
findings_in_scope: 12
fixed: 12
skipped: 0
status: all_fixed
---

# Phase 32: Code Review Fix Report

**Fixed at:** 2026-08-25T23:52:00Z
**Source review:** `.planning/phases/32-gates-de-homogeneidad-d-16/32-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 12 (2 Critical + 10 Warning; the 5 Info findings were out of `fix_scope`)
- Fixed: 12
- Skipped: 0

The two new gates were the review's central complaint: both were sold on
non-vacuity and neither had a lower bound that matched the claim.
`check_surface_types.py` gained seven RED cases; `tools/surface_parity.py` had
**no** RED suite at all and gained one, with twelve cases. Every case was run
against the pre-fix code to confirm it fails there — a RED proof that passes
both before and after proves nothing.

Four live divergences in the repository were found by the repaired gates and
closed in the same commits: two `market_data_client` constructor/module surface
drifts, one parameter-order drift, and one re-export asymmetry.

## Fixed Issues

### CR-01: `check_surface_types.py` silently skips exported names it resolves but cannot locate

**Files modified:** `tools/check_surface_types.py`, `packages/iol-client/tests/test_surface_types_red.py`
**Commit:** `db7ca0e`

**Applied fix:** The candidate loop recorded nothing when zero AST nodes matched
a wanted name — the one unresolvable condition in the gate that was a silent skip
rather than a `problems` entry. All three reachable shapes closed:

1. **Alias re-export** — resolution now carries `alias.name` (the *source* name)
   alongside `alias.asname` (the *bound* name) through a new `_Binding` record,
   so `from pkg.client import Client as MDClient` finds the `ClassDef` named
   `Client`.
2. **Conditionally-defined export** — new `_module_level_statements` flattens the
   module-level statement containers (`if` / `try` / `with` / `match`) without
   descending into function bodies. Applied to `__all__` scanning, to module
   binding collection, and to class-member collection.
3. **`__all__ +=`** — `_all_names` now accumulates *every* `__all__` binding in
   the module including `ast.AugAssign`, instead of returning at the first match.
   A non-`Constant` element (`*models.__all__`) is a failure rather than a silent
   drop.

**Judgement call the review did not fully prescribe — documented per instruction.**
The review's suggested patch turns "resolved but no top-level definition" into a
problem unconditionally, with an `assigned` escape hatch for module-level
constants. Applied literally that would have **reddened the real tree**: matriz's
two live re-exported constants resolve to `ws_client`, which only re-*imports*
them from `types` (an `ImportFrom`, not an `Assign`). The review itself names the
danger of the narrow reading — "the same re-export-through-an-intermediate shape
applied to a `Client` class would silently take that class's entire method
surface out of the gate".

I took the option that preserves non-vacuity rather than the one that narrows
scope: `_resolve_export` **follows** intra-package `ImportFrom` hops
(cycle-guarded, `_MAX_RESOLUTION_HOPS = 8` deep) to the module that actually
binds the name. A chain that dead-ends is a problem; a chain ending at a
module-level assignment is a stated outcome reported through a new
`ScanResult.assignments` field (13 today). This is strictly stronger than the
suggested patch: a `Client` re-exported through an intermediate is now *scanned*,
where the literal patch would have merely *reported* it.

**Non-vacuity proof:** 7 new cases in `test_surface_types_red.py` — alias
re-export, conditional definition, `__all__ +=`, starred `__all__` element,
re-export chain followed, dead-ended chain reddens, constants counted. All 7 fail
against the pre-fix gate; all 12 pass against the fixed one.

### CR-02: `surface_parity.py` never compares `__init__`

**Files modified:** `tools/surface_parity.py`, `packages/iol-client/tests/test_surface_parity_red.py` (new), `packages/market-data-client/src/market_data_client/client.py`, `packages/market-data-client/src/market_data_client/aio.py`
**Commit:** `3617e51`

**Applied fix:** Rule 5 added to the numbered `THE NORMALIZATION` table and
applied in `class_parity_report`: `__init__` is compared explicitly and counted,
as the review prescribed. It is the only dunder so compared — every other one
implements a protocol this repo does not own, where a sync/async difference is
required correctness.

The gate immediately reported exactly the divergence the review measured, and
only that one. Closed it by giving `market_data_client.Client.__init__` the
`token`, `token_expires_at` and `http_client: httpx.Client | None` kwargs its
`configure()` already accepted, mirroring `AsyncClient.__init__` verbatim.

**Scope addition, stated rather than silent:** both constructors now reject a
wrong-flavour `http_client` with `TypeError`. The CLAUDE.md dual sync/async
constraint requires the mirror, and the only runtime check was an
`assert isinstance` that vanishes under `python -O` (this is WR-07's second half,
applied here because adding validation to one constructor and not the other would
have created a new asymmetry).

**Non-vacuity proof:** `packages/iol-client/tests/test_surface_parity_red.py`
created — the parity gate previously had only the six in-package *upper*-bound
hooks and no lower bound whatsoever. Both `__init__` cases fail against the
pre-fix gate.

### WR-01: parity compares annotations, not signatures

**Files modified:** `tools/surface_parity.py`, `packages/iol-client/tests/test_surface_parity_red.py`, `packages/market-data-client/src/market_data_client/aio.py`
**Commit:** `1cf3741`

**Applied fix:** New `signature_shape` returns the parameter list in declaration
order with each parameter's `kind` and `default`; `_diff_callable` runs both
halves for every compared callable at both axes. Annotations are still read only
from `get_type_hints` — under `from __future__ import annotations`,
`inspect.signature` yields unresolved strings — and the division of labour is
recorded in a new docstring section so it is not collapsed back into one call.

"No default" renders as its own sentinel, so a required parameter can never
compare equal to one defaulting to `None` (both annotate `str | None`, so the
hint halves agree exactly).

**Live divergence closed:** `market_data_client.aio.configure` declared
`base_url` fifth while `client.configure` declared it first. All keyword-only, so
the reorder breaks no caller.

**Non-vacuity proof:** 3 new RED cases (reorder+kind, default drift,
no-default-vs-None), all failing against the pre-fix gate.

### WR-02: `public_names`'s `__module__` filter drops package-owned constants and type aliases

**Files modified:** `tools/surface_parity.py`, `packages/iol-client/tests/test_surface_parity_red.py`, `packages/market-data-client/src/market_data_client/client.py`
**Commit:** `927f757`

**Applied fix:** `_is_package_owned` replaces the bare `__module__` equality with
three ordered tests: submodules are never surface; anything owned by the package
is (including `__module__`-less constants and package-owned re-exports); and a
foreign-owned value counts only when the foreign module does not itself publish
that same object under that same name. That identity test is what separates
`typing.Any` / `pathlib.Path` / `dotenv.main.load_dotenv` from
`InstrumentType = Literal[...]`, which carries `__module__ == 'typing'` but which
`typing` has never heard of.

**Live divergence closed:** `market_data_client.aio` bound `RequestSpec` at
module level while `client.py` used `_core.RequestSpec`. The sync side now
imports it by name, matching aio and matching iol/higyrus/matriz.

**Judgement call the review did not fully prescribe — documented per instruction.**
The review lists three live divergences the filter hid, one of which is
`matriz_client.client` binding `load_dotenv` where `aio` does not. I chose **not**
to report third-party re-export asymmetries, and stated the exclusion explicitly
in `THE METRIC, STATED ONCE` rather than leaving it implicit (which is the
review's own stated minimum for this finding). Measured reason: a filter wide
enough to catch `load_dotenv` also catches `Any`, `Self`, `Literal`, `Path`,
`Sequence`, `urlsplit` and `annotations` across twelve modules' import lists —
noise that would bury the real signal, which is the failure mode rule 1 of `THE
NORMALIZATION` exists to avoid. An import list is not a published surface. The
other two divergences the review named (`RequestSpec`, `InstrumentType`) are both
now in scope; `RequestSpec` was caught and fixed, `InstrumentType` agrees.

Two consequences handled rather than papered over:
- The hint loop narrows with `inspect.isroutine`, not `callable` — a `Literal`
  alias *is* callable and would blow up `inspect.signature`. Constants are
  name-compared and not diffed, stated rather than silent.
- Surface size and compared-callable count became different integers (matriz: 31
  names, 23 callables), so `MODULE_LOWER_BOUNDS` was re-measured and a separate
  measured `MODULE_COMPARED_LOWER_BOUNDS` table took over the `compared_hints`
  floor. Leaving them conflated would have meant either a name floor too low to
  bound anything or a compared floor no tree can satisfy.

**Non-vacuity proof:** 3 new RED cases; 2 fail against the pre-fix gate, the
third is the regression guard for the `isroutine` narrowing.

### WR-03: the class axis has a hard-coded floor of 1

**Files modified:** `tools/surface_parity.py`, `packages/iol-client/tests/test_surface_parity_red.py`
**Commit:** `e51eea4`

**Applied fix:** Two new measured tables as the review prescribed —
`CLASS_LOWER_BOUNDS` (sync_min, async_min public members) and
`CLASS_COMPARED_LOWER_BOUNDS` (members actually diffed) — both asserted in
`assert_class_parity`, replacing `compared_hints < 1`. `sync_count` /
`async_count` were already computed on this axis and are now asserted.

wallets carries an explicit `(0, 0)` / `0` entry with its reason stated inline,
so the WR-04 roster cross-check has an entry to find rather than a hole it cannot
tell from an oversight; `assert_class_parity` still raises for wallets and its
hook asserts the absence explicitly.

**Non-vacuity proof:** 2 new RED cases — the tables are measured rather than
uniform, and a lockstep collapse to a single shared method reddens. Floors for
the synthetic case are injected with `monkeypatch` rather than by borrowing a
real package name, because shadowing an already-imported package in `sys.modules`
would resolve the real module and quietly test nothing.

### WR-04: `MODULE_LOWER_BOUNDS` is a hardcoded roster with no disk cross-check

**Files modified:** `tools/surface_parity.py`, `packages/iol-client/tests/test_surface_parity_red.py`
**Commit:** `a98ecba`

**Applied fix:** `workspace_packages` enumerates `packages/*/src/<import_name>`
at run time, naming the offending candidates on every structural surprise rather
than dropping them. `assert_bounds_roster_matches_disk` requires each package
found to carry an entry in **all four** bounds tables *and* an in-package hook
file, and reconciles in both directions — a stale floor for a departed package is
as silent as a missing one.

**Departure from the review's sketch, per the non-vacuity instruction:** the
review sketched a bare test function checking `MODULE_LOWER_BOUNDS` only. The
logic lives in `tools/surface_parity.py` instead (D-07: the walker lives in one
place, the hooks are thin), covers all four tables rather than one, and asserts
the hook files exist rather than assuming them. `REPO_ROOT` is a default argument
value only, matching the D-04 injectable-root seam in `check_surface_types.py`,
which is what makes the RED cases possible at all.

**Non-vacuity proof:** 5 new RED cases — real tree satisfies the roster; a
package with no floor, a floor with no hook, a stale floor for a departed
package, an empty workspace and an absent workspace each redden.

### WR-05: `test_core_boundary_red.py` resolves `lint-imports` off `PATH`

**Files modified:** `packages/market-data-client/tests/test_core_boundary_red.py`
**Commit:** `fe463b7`

**Applied fix:** Exactly the review's patch —
`Path(sys.executable).with_name("lint-imports")` first, `shutil.which` as
fallback. The assertion message now names both places it looked instead of
blaming a broken environment. The docstring's false hermeticity claim is replaced
with a statement of what is actually guaranteed and why.

**Verification:** both tests pass with the venv on `PATH` and with
`PATH=/usr/bin:/bin`. Confirmed the pre-fix file fails both tests under the
latter.

### WR-06: a market-data-client test asserts on the boundary state of all five packages

**Files modified:** `packages/market-data-client/tests/test_core_boundary_red.py`
**Commit:** `8be685e`

**Applied fix:** The review offered two options; I took the second (keep a parsed
contract-*count* check, drop the per-contract state assertions), because it
preserves the information the first option discards. The summary line is parsed
and `kept + broken` is required to equal the number of contracts declared in
`pyproject.toml`. That still proves the run analysed the whole config rather than
collapsing to a subset — which a bare `returncode` check cannot — while saying
nothing about any other package's boundary state.

**Verification:** the coverage check was exercised directly against a truncated
summary (`Contracts: 2 kept, 0 broken.`) and against output with no summary line
at all; both redden with a specific message.

### WR-07: `aio.configure(http_client=...)` writes lock-protected state outside the lock

**Files modified:** `packages/market-data-client/src/market_data_client/aio.py`, `packages/market-data-client/src/market_data_client/client.py`, `packages/market-data-client/tests/test_transport_injection.py` (new)
**Commit:** `5c0f5fd`

**Applied fix:** Both halves as the review prescribed. `aclose()`'s final
`_state.http_client = None` is conditional on identity, so a transport injected
during its own `await` is not discarded unclosed. All four public entry points —
both `configure()`s and both `__init__`s — validate `http_client` with a
`TypeError` instead of relying on an `assert isinstance` that vanishes under
`python -O`.

Mirrored across sync and async per the CLAUDE.md dual constraint. (The sync
`close()` has no suspension point between its read and write, so the identity
guard is async-only and that asymmetry is deliberate; the *type validation* is
mirrored on both surfaces.)

**Non-vacuity proof:** new `test_transport_injection.py` materialises the race
deterministically with an `httpx.AsyncClient` subclass whose `aclose()` runs a
callback at exactly the suspension point. The interleaving test and both
`configure` type tests fail against the pre-fix source.

### WR-08: the `test_ws_decode_mode.py` mypy fix weakened what the test proves

**Files modified:** `packages/matriz-client/tests/test_ws_decode_mode.py`
**Commit:** `59556b9`

**Applied fix:** Exactly the review's patch — the bare `object()` restored behind
`cast("websocket.WebSocketApp", ...)`, with a comment recording that passing one
*is* the assertion (`_handle_message` reads nothing off `ws`, unlike
`_handle_open`). The `if TYPE_CHECKING: import websocket` guard is replaced with
a plain import: `websocket-client>=1.8.0` is a hard runtime dependency of
`matriz-client` and `ws_client.py` imports it unconditionally, so the guard
prevented no import and its comment stated a constraint that does not exist.

### WR-09: `alias.__args__` -> `get_args(alias)` made a per-alias assertion vacuous

**Files modified:** `packages/matriz-client/tests/test_decode.py`
**Commit:** `7900844`

**Applied fix:** Exactly the review's patch — bind the members, assert they are
non-empty, then assert every one is a `str`. Restores what `__args__` gave for
free (an `AttributeError` on a degenerate alias) without reintroducing it.

### WR-10: `cast(Any, cls)` is maximal widening for a narrow variance complaint

**Files modified:** `packages/matriz-client/tests/test_decode.py`
**Commit:** `711ad1c`

**Applied fix:** The review offered `cast(Hashable, cls)` or the repo's
`# type: ignore[arg-type]` idiom. I took the ignore, and recorded the reasoning
inline: it is scoped to the one error code, leaves every other check on the
argument in force, and under `strict = true` (which implies
`warn_unused_ignores`) becomes an **error** the day the upstream variance is
fixed — a cast would rot silently instead. `cast(Hashable, ...)` would also admit
a string, so it does not actually deliver the narrowing its name suggests.

The asymmetry the review flagged (the same Wave-0 batch *removed*
`# type: ignore[arg-type]` from ambito's and higyrus's `test_decode.py`) is now
explained in the comment: those two need no suppression because `cls` is a plain
`type` there, which is `Hashable`-compatible. Verified by reproducing the exact
mypy error before applying the fix.

## Skipped Issues

None.

## Info findings (out of `fix_scope`, not attempted)

`IN-01` … `IN-05` were outside `fix_scope: critical_warning` and were not
addressed. One note for whoever picks them up: **IN-02**'s suggested filtering
(skip `__pycache__` and dot-directories, name the rejected candidates) *was*
applied to the new `workspace_packages` in `tools/surface_parity.py`, because it
was written fresh under WR-04. The equivalent hardening of
`check_surface_types.py:_import_root` is still open.

## Verification run

All green on the fixed tree:

| Check | Result |
|---|---|
| `ruff check .` | All checks passed |
| `ruff format --check .` | 243 files already formatted |
| `mypy` (global, 75 source files) | Success |
| `mypy packages/<pkg>/tests` x6 | Success (20 / 12 / 16 / 30 / 25 / 4 files) |
| `uv lock --check` | Resolved, unchanged |
| `pre-commit run --all-files` | All 9 hooks passed |
| `tools/check_surface_types.py` | 6 packages, 178 `__all__` names, 319 definitions, 13 constant/alias exports, 23 exempted, 0 violations |
| `tools/check_decode_intactness.py` | Checks A–D pass |
| `tools/check_uniform_structure.py` | pass |
| `lint-imports` | Contracts: 5 kept, 0 broken |
| `pytest packages/<pkg>` x6 (the CI matrix) | 203 / 239 / 272 / 585 / 430 / 7 — **1736 passed** |
| `pytest tests` | 2 passed |
| `pytest verification/test_public_surface.py` | 4 passed (snapshots unchanged) |
| `pytest verification --collect-only` | 381 collected, no import errors |

Test count moved 1707 -> 1736: +29 net, all of them new RED/regression cases
(7 surface-types, 12 parity, 7 transport-injection, plus 3 already counted in the
parity file's growth across commits).

**One suite deliberately not executed:** `verification/test_with_options.py` and
the rest of the live-API `verification/` suite drive the real financial APIs and
hang without credentials/network. This is pre-existing and by design — the CI
`test` job passes an explicit `packages/<pkg>` path that overrides `testpaths`,
which is documented in three separate files in this phase. Collection was run to
prove no import breakage, and the one static file in that directory
(`test_public_surface.py`, a golden-file snapshot over the four non-market-data
packages) was executed and passes.

---

_Fixed: 2026-08-25T23:52:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
