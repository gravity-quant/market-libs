---
phase: 31-endpoints-de-ops-estructura-uniforme
plan: 01
subsystem: market-data-client / test harness
tags: [ast-guard, mutation-gate, byte-identical-request, asvs-v4, asvs-v13, tdd, safety-net]
status: complete

requires:
  - packages/market-data-client/src/market_data_client/client.py (unchanged — subject under guard)
  - packages/market-data-client/src/market_data_client/aio.py (unchanged — subject under guard)
  - packages/market-data-client/src/market_data_client/_core.py (holiday builders + RequestSpec)
  - packages/market-data-client/tests/conftest.py (seeded `test-token` + `base_url`)
provides:
  - "AST guard proving `_ensure_mutation_allowed()` is the first executable statement of all 8 gated methods in BOTH shells, non-vacuously by set equality (criterion 3, T-31-01/T-31-04)"
  - "Direct `RequestSpec.idempotent is True` assertions on both holiday builders (criterion 3 second clause, T-31-02)"
  - "Four raw-bytes v0.4.0 request pins for `add_holidays` + `delete_holiday`, sync + async (criterion 2, T-31-03)"
affects:
  - "Plans 31-02..31-05: any request-side drift introduced while retyping responses now fails loudly instead of travelling hidden"
  - "Plan 31-05: the pin module lives outside `test_calendar_write*.py`, so its diff stays empty across that re-mock"

tech-stack:
  added: []
  patterns:
    - "In-package AST guard resolved through `pathlib.Path(market_data_client.__file__).parent` so it survives `--import-mode=importlib` and an installed wheel"
    - "Non-vacuity asserted as SET EQUALITY against a frozenset roster, never a non-empty check or a lower bound"
    - "Request pinned as a 4-tuple `(method, str(url), sorted headers, content bytes)` — single equality, never a parsed comparison"
    - "`user-agent` derived from `httpx.__version__` so the header SET stays pinned while the version decouples"

key-files:
  created:
    - packages/market-data-client/tests/test_mutation_gate_ast.py
    - packages/market-data-client/tests/test_v040_request_pin.py
  modified: []

decisions:
  - "AD-31-01-01: guard discovery is scoped to CLASS-BODY methods, not `ast.walk` over the module — both shells define module-level shims with the SAME 8 names that delegate to the default Client and correctly do not call the gate"
  - "Hazard 1 resolved: `user-agent` stays INSIDE the frozen header set with a derived value; excluding it would blind the pin to a dropped header, hard-pinning `0.28.1` would redden criterion 2 on an unrelated `uv.lock` bump"
  - "Per-endpoint header tuples are frozen, never a shared header list — the DELETE carries no Content-Length / Content-Type"
  - "Prose refers to HTTP headers by their canonical capitalized names; only the wire tuples carry the lowercase form httpx emits"

metrics:
  duration: ~14 min
  tasks: 2
  files: 2
  tests_added: 9
  completed: 2026-08-24
---

# Phase 31 Plan 01: Safety net before anything moves — Summary

Built the three criterion-2 / criterion-3 gates that did not exist, all green against
**unchanged production source**, so a later red in this phase is attributable to the change
rather than to the net.

## What was built

### Task 1 — `packages/market-data-client/tests/test_mutation_gate_ast.py` (186 lines, 5 tests)

The first AST check in this repo that targets `packages/*/src/*/client.py` and `aio.py`
(every pre-existing one targets a `main_*.py` driver or `_decode.py`). Placed **in-package**,
not under `verification/`, because `ci.yml`'s `test` job passes an explicit
`packages/${{ matrix.package }}` path that overrides `testpaths` — `verification/` has never
executed in CI (G-5). This guard travels in the 6x2 matrix.

- **Test A (×2 shells)** — non-vacuity by **set equality**: the discovered method-name set
  `==` the 8-name `frozenset` roster. Never a non-empty check, never a lower bound.
- **Test B (×2 shells)** — `_ensure_mutation_allowed()` is the first **executable** statement
  (docstring skipped) of every discovered method. Failure message names shell, method, line
  and a truncated `ast.dump` of the actual first statement.
- **Test C** — both holiday builders assert `.idempotent is True` **by identity**.

### Task 2 — `packages/market-data-client/tests/test_v040_request_pin.py` (181 lines, 4 tests)

Four single-equality pins of `_frozen(req) == <frozen literal>` where
`_frozen(req) = (req.method, str(req.url), tuple(sorted(req.headers.items())), req.content)`.
Two endpoints × two surfaces, all four asserting **the same two literals** — that identity is
the sync/async request-parity evidence (C-3).

Dedicated module on purpose: `test_calendar_write.py` / `test_calendar_write_async.py` are
re-mocked in plan 31-05, and keeping the pin outside means the pin's diff stays empty across
that re-mock, which is itself evidence for criterion 2.

## Test counts added

| File | Tests | Package total |
|---|---|---|
| `test_mutation_gate_ast.py` | 5 (2 shells × 2 parametrized + 1 builder-flag) | market-data 476 → 481 |
| `test_v040_request_pin.py` | 4 (2 endpoints × 2 surfaces) | market-data 481 → 485 |

`uv run pytest packages/market-data-client packages/higyrus-client -q` → **708 passed**, exactly
the documented 699 baseline plus the 9 new tests.

## RED-proof observations (verbatim)

Three temporary source mutations were planted, observed failing, and reverted. `git diff --stat
packages/market-data-client/src/` was confirmed **empty** after each.

**1. Gate reorder — `client.py::add_holidays`, gate moved below the builder call**

```
E       AssertionError: _ensure_mutation_allowed() dejó de ser la primera sentencia ejecutable en:
E         client.py::add_holidays (línea 681) — primera sentencia: Assign(targets=[Name(id='spec', ctx=Store())],
E         value=Call(func=Attribute(value=Name(id='_core', ctx=Load()), attr='build_add_holidays_request', ctx=Load()), arg
FAILED ...::test_gate_is_first_executable_statement_in_every_mutation_method[client.py]
1 failed, 4 passed
```

Only the `client.py` leg failed; the `aio.py` leg stayed green — the guard localises the drift
to the surface that moved.

**2. Non-vacuity — `aio.py::add_holidays` renamed to `add_holidays_x`**

```
E       AssertionError: aio.py: el set de métodos mutadores descubiertos no coincide con el roster.
E       faltan=['add_holidays'] sobran=[]
FAILED ...::test_every_mutation_method_is_discovered_in_shell[aio.py]
1 failed, 4 passed
```

Note what this proves: under a "non-empty" or `>=` assertion the guard would have reported
**green** while silently no longer inspecting `add_holidays` at all. Set equality catches it.

**3. Body key-order swap — `HolidayIn.to_dict()` emitting `description` before `closed`**

```
E       assert ('POST', 'htt...sed":true}]}') == ('POST', 'htt...":"probe"}]}')
E         At index 3 diff:
E           b'{"days":[{"day":"2099-12-29","description":"probe","closed":true}]}'
E         !=
E           b'{"days":[{"day":"2099-12-29","closed":true,"description":"probe"}]}'
FAILED ...::test_add_holidays_request_is_byte_identical_to_v040
FAILED ...::test_add_holidays_request_is_byte_identical_to_v040_async
2 failed, 2 passed
```

Both `add_holidays` legs failed on the **body bytes**; both `delete_holiday` legs stayed green
(they carry `b""`). `content-length` was unchanged at `67` — the swap is length-preserving, so
a header-only comparison would also have missed it. This is exactly the drift class a
`json.loads` comparison would have swallowed.

## Resolved: the `user-agent` decision (Hazard 1)

`user-agent` **stays inside** the frozen header set, with its value **derived** as
`_UA = f"python-httpx/{httpx.__version__}"` rather than hard-pinned to `0.28.1`.

- Excluding the header would stop the pin from noticing a header being **dropped**.
- Hard-pinning the literal would redden criterion 2 on a `uv.lock` bump unrelated to this phase.
- Deriving keeps the header **SET** pinned while decoupling only the version.

**Confirmed at execution:** installed httpx is `0.28.1`, so the derived form reproduces the
captured tuple byte-for-byte (all four pins green). The backstop `must_have` is satisfied.

## Production source untouched

```
$ git status --porcelain packages/market-data-client/src/
(empty)
$ git diff --stat packages/market-data-client/src/
(empty)
```

Confirmed after every RED proof and at both commit points. This plan added tests only.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] Guard discovery scoped to class bodies instead of `ast.walk` over the module**

- **Found during:** Task 1, while reading the shells.
- **Issue:** The plan specified collecting "every function in the shell whose name is in
  `_MUTATION_METHODS`" via the verbatim-transferred `_functions(tree)` (an `ast.walk`). Both
  shells define, in addition to the 8 `Client` / `AsyncClient` methods, **module-level shims
  with the same 8 names** (`client.py:910-957`, `aio.py:916-963`) that delegate to the default
  singleton — `return _get_default().add_holidays(holidays)`. Those shims correctly do **not**
  call the gate: the gate runs inside the method they delegate to. An `ast.walk` sweep would
  have made Test B fail on healthy code, and the natural "fix" would have been to weaken the
  first-statement predicate — the exact prohibition this plan names.
- **Fix:** `_functions` was replaced by `_shell_methods(tree)`, which iterates `ClassDef` bodies
  directly (also avoiding nested-function noise). The rationale, with the shim line numbers, is
  written into the helper's docstring so a future reader cannot mistake it for laxity. `RESEARCH`'s
  16 confirmed call sites are all class methods, so this is exactly the intended subject set.
- **Files modified:** `packages/market-data-client/tests/test_mutation_gate_ast.py` (new file)
- **Commit:** `ca3d40e`

**2. [Rule 3 — Blocking] Ambiguous-character lint (`RUF002`/`RUF003`)**

- **Found during:** Task 1 lint gate.
- **Issue:** `ruff` rejected the `×` MULTIPLICATION SIGN used in "matriz 6×2" and "8 nombres × 2 shells".
- **Fix:** Replaced with ASCII `x`.
- **Commit:** `ca3d40e`

**3. [Rule 3 — Blocking] Two acceptance-criterion greps counted prose, not executable code**

- **Found during:** Task 2 acceptance verification.
- **Issue:** Two criteria were written as raw `grep -c` over the whole file and were tripped by
  explanatory prose the plan's own `<action>` block **required**:
  - `grep -c 'content-length'` expected exactly 1 but returned 3 — the POST tuple plus the two
    mandated comments (the `Content-Length` derivation note and the Hazard 3 "DELETE lacks it" note).
  - `grep -v '^\s*#' | grep -c 'req.extensions'` expected 0 but returned 1 — the Hazard 2
    explanation lives in `_frozen`'s **docstring**, which the comment filter does not strip.
- **Fix:** Prose now names HTTP headers by their canonical RFC 9110 capitalization
  (`Content-Length` / `Content-Type`) while only the wire tuples carry the lowercase form httpx
  actually emits, and the Hazard 2 note names httpx's attribute as `request.extensions`. Both
  reads are strictly more accurate than what they replaced, and both criteria now hold literally.
  The underlying invariants were never at risk: the DELETE tuple has always lacked
  `content-length`, and `extensions` has never entered a frozen tuple.
- **Commit:** `0ec1189`

**4. [Rule 1 — Bug] Reverted a premature `TYP-02` completion flip in `REQUIREMENTS.md`**

- **Found during:** state-update step.
- **Issue:** `requirements mark-complete TYP-02` (driven by this plan's frontmatter) flipped
  `TYP-02` to `[x]` after plan **01 of 5**. TYP-02's main clause — "Los 5 endpoints de ops
  devuelven modelos tipados" — is delivered by plans 31-02..31-05, not here; this plan delivers
  only the byte-identical-request half of the requirement. The flip also left the file
  self-inconsistent (checkbox `[x]`, traceability row `Pending`) and would have read as a
  false-complete to the milestone audit scanner — the precise failure mode this milestone exists
  to eliminate.
- **Fix:** Reverted `.planning/REQUIREMENTS.md` to `[ ]`. TYP-02 should be marked complete by the
  final plan of Phase 31 or by phase verification, once all 5 endpoints actually return models.
- **Commit:** `d0f70a0`

### Architectural changes

None. No Rule 4 situation arose.

## Authentication Gates

None. This plan issues no live requests — all four pins run against `pytest-httpx` with the
conftest-seeded `test-token`.

## Known Stubs

None.

## Threat Flags

None. This plan introduces no network endpoint, auth path, file access, or schema change — it
adds two read-only test modules that parse source and inspect mocked requests.

## Carried-forward open items (not resolved here)

- **TYP-02 / concurrency / unresolved** — the stock concurrency probe does not map onto this
  shape (sequential HTTP client libraries; this plan changes no concurrency primitive). Carried
  forward as an open assumption, not resolved.
- **TYP-03 / unclassified / unresolved** — addressed by plan 31-02.
- **G-6** — `client.py:684`'s `add_holidays` docstring still claims `idempotent=False` and is
  stale. Left untouched here **by design** (this plan must not move production source); Test C
  is now the authority that contradicts it, and the prose is corrected in plan 31-05.

## Self-Check: PASSED

- `packages/market-data-client/tests/test_mutation_gate_ast.py` — FOUND
- `packages/market-data-client/tests/test_v040_request_pin.py` — FOUND
- Commit `ca3d40e` — FOUND
- Commit `0ec1189` — FOUND
- `git status --porcelain packages/market-data-client/src/` — empty
- `uv run ruff check .` + `uv run ruff format --check .` — clean (223 files)
- `uv run mypy` on both new files — no issues
- `uv run pytest packages/market-data-client packages/higyrus-client -q` — 708 passed
