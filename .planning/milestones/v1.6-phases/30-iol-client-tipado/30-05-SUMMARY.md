---
phase: 30-iol-client-tipado
plan: 05
subsystem: iol-client / _core parsers
tags: [gap-closure, CR-02, shape-guard, ASVS-V5, D-06, TYP-01, tdd]
requires:
  - "iol_client._core.parse_get_instruments_by_type_response (Phase 30-02 model-building rewrite)"
  - "iol_client.exceptions.IOLAPIError (two-positional signature)"
  - "iol_client._decode._response_parser (DecodeScope ownership)"
provides:
  - "isinstance(raw, dict) envelope guard in parse_get_instruments_by_type_response"
  - "isinstance(titulos, list) value guard in parse_get_instruments_by_type_response"
  - "5 regression tests locking shape-vs-cardinality discrimination on both surfaces"
affects:
  - "packages/iol-client/src/iol_client/_core.py"
  - "packages/iol-client/tests/test_core.py"
  - "packages/iol-client/tests/test_async_client.py"
tech-stack:
  added: []
  patterns:
    - "IOLAPIError(0, f\"shape mismatch: ...\") — status_code=0 marks a payload-shape error, not an HTTP one (convention established by _parse_list_or_raise)"
    - "Guard runs AFTER the .get(key, default) so a missing key preserves its documented [] behavior while a wrong-typed value raises"
    - "Exception message interpolates type(x).__name__ only — never a wire value (T-30-05-04)"
key-files:
  created: []
  modified:
    - "packages/iol-client/src/iol_client/_core.py"
    - "packages/iol-client/tests/test_core.py"
    - "packages/iol-client/tests/test_async_client.py"
decisions:
  - "Dropped the `data: dict[str, Any]` / `titulos: list[Any]` annotations rather than keeping them alongside the guards — they were unchecked assertions mypy believed and the runtime never enforced; the isinstance guards narrow both locals naturally and mypy strict passes with no cast and no hint"
  - "Task 2's non-vacuity was proven by execution, not by argument: the async test was run against the pre-fix parser (restored via `git checkout f29386b -- _core.py`, then reverted) and observed to fail DID NOT RAISE"
metrics:
  duration: "~25 min"
  completed: "2026-08-20"
  tasks: 2
  commits: 3
  tests_added: 5
status: complete
---

# Phase 30 Plan 05: Shape guards on the by_type envelope (CR-02) Summary

Two `isinstance` guards in `parse_get_instruments_by_type_response` stop a malformed
upstream from fabricating synthetic `Titulo` rows or leaking a bare `AttributeError`
outside the `IOLClientError` hierarchy — closing CR-02 / 30-VERIFICATION.md truth 7.

## What Was Built

**Task 1 — RED→GREEN shape guards** (`test(30-05)` `f29386b` → `fix(30-05)` `e711d29`)

`packages/iol-client/src/iol_client/_core.py:412-459` — the parser now reads:

```python
resp.read()
raise_for_response(resp)
raw = resp.json()
if not isinstance(raw, dict):
    raise IOLAPIError(0, f"shape mismatch: expected dict envelope, got {type(raw).__name__}")
titulos = raw.get("titulos", [])
if not isinstance(titulos, list):
    raise IOLAPIError(
        0, f"shape mismatch: 'titulos' expected list, got {type(titulos).__name__}"
    )
return [Titulo.from_api(fila) for fila in titulos]
```

The docstring was extended to state both guards, their `status_code=0` rationale, and to
explicitly reconcile the two adjacent-looking behaviors: **missing key yields `[]`** (the
body *is* the expected dict, it just has no rows — D-06 preserves this) versus
**wrong-typed value raises** (the body does not have the expected shape at all).

Four tests added to `packages/iol-client/tests/test_core.py:494-548`.

**Task 2 — async-surface parity proof** (`test(30-05)` `c184d70`)

`test_async_get_instruments_by_type_raises_on_malformed_titulos` in
`packages/iol-client/tests/test_async_client.py:131-165`. Both surfaces
(`client.py:572`, `aio.py:580`) dispatch into the same `_core` function; this test
converts that from a claim a reader verifies by reading two files into an executable
assertion that fails loudly if anyone reintroduces a per-surface copy of the parse logic.

## RED Evidence (non-vacuity)

Literal output of the three raising tests run against the **unmodified** parser
(`uv run pytest packages/iol-client/tests/test_core.py -q -k "by_type_response_raises or empty_titulos_list"`,
result `3 failed, 1 passed, 41 deselected`):

**1. `test_parse_get_instruments_by_type_response_raises_on_top_level_list_body`**

```
        resp.read()
        raise_for_response(resp)
        data: dict[str, Any] = resp.json()
>       titulos: list[Any] = data.get("titulos", [])
                             ^^^^^^^^
E       AttributeError: 'list' object has no attribute 'get'

packages/iol-client/src/iol_client/_core.py:430: AttributeError
```

**2. `test_parse_get_instruments_by_type_response_raises_on_string_titulos`**

```
        resp = httpx.Response(200, content=b'{"titulos": "GGAL"}')
>       with pytest.raises(IOLAPIError) as excinfo:
             ^^^^^^^^^^^^^^^^^^^^^^^^^^
E       Failed: DID NOT RAISE <class 'iol_client.exceptions.IOLAPIError'>

packages/iol-client/tests/test_core.py:518: Failed
```

**3. `test_parse_get_instruments_by_type_response_raises_on_dict_titulos`**

```
        resp = httpx.Response(200, content=b'{"titulos": {"a": 1, "b": 2}}')
>       with pytest.raises(IOLAPIError) as excinfo:
             ^^^^^^^^^^^^^^^^^^^^^^^^^^
E       Failed: DID NOT RAISE <class 'iol_client.exceptions.IOLAPIError'>

packages/iol-client/tests/test_core.py:532: Failed
```

**4. `test_parse_get_instruments_by_type_response_empty_titulos_list_no_levanta`** — the
one `passed` in that run. GREEN from the start by design; it is the cardinality-vs-shape
regression lock and stayed green through the fix.

All three RED signatures match the verification transcript exactly — the reproduction did
not drift, so no test was adjusted to fit.

**Task 2 RED (executed, not argued):** `_core.py` was temporarily restored to its pre-fix
state (`git checkout f29386b -- packages/iol-client/src/iol_client/_core.py`) and the new
async test run against it:

```
>       with pytest.raises(IOLAPIError) as excinfo:
             ^^^^^^^^^^^^^^^^^^^^^^^^^^
E       Failed: DID NOT RAISE <class 'iol_client.exceptions.IOLAPIError'>

packages/iol-client/tests/test_async_client.py:152: Failed
1 failed, 22 deselected
```

`_core.py` was then restored with `git checkout HEAD -- packages/iol-client/src/iol_client/_core.py`
and `git status --short` confirmed only the async test file remained modified.

## Verification

| Gate | Command | Result |
|------|---------|--------|
| Package suite | `uv run pytest packages/iol-client -q` | **241 passed** (237 baseline + 4) |
| Workspace suite | `uv run pytest packages/ -q` | **1572 passed, 1 deselected** (1567 baseline + 5), 0 failures |
| Typecheck | `uv run mypy packages/iol-client/src packages/iol-client/tests` | `Success: no issues found in 25 source files` |
| Lint | `uv run ruff check packages/iol-client` | `All checks passed!` |
| Format | `uv run ruff format --check packages/iol-client` | `25 files already formatted` |
| Import contracts | `uv run lint-imports` | `Contracts: 4 kept, 0 broken` (incl. `iol_client._core does not depend on transport modules`) |
| Schema baselines | `git diff --exit-code .planning/verification/schemas/iol-client/` | exit 0, no output — untouched |
| **`aio.py` byte-unchanged** | `git diff --exit-code packages/iol-client/src/iol_client/aio.py` | **exit 0, no output** |

mypy strict passed with **no cast and no added hint** — the runtime guards narrow both
locals naturally, which is the point: the dropped annotations were unchecked assertions,
and the guards that replaced them are checks mypy can actually follow.

## Prohibition Status

These prohibitions are descriptor-less; evidence is supplied here per the plan's output spec.

| Prohibition | Status | Evidence |
|-------------|--------|----------|
| "Ningún parser degrada silenciosamente ante una forma inesperada: un valor de forma inesperada levanta, nunca fabrica filas ni devuelve `[]` por defecto" | **HELD** | Three tests (`..._raises_on_top_level_list_body`, `..._raises_on_string_titulos`, `..._raises_on_dict_titulos`) assert `IOLAPIError` for the three reproduced shapes. Zero `Titulo` rows are constructible from a non-list value: both raises precede the comprehension, so `Titulo.from_api` is unreachable on those paths. |
| "Ninguna excepción de forma escapa la jerarquía `IOLClientError`: un body malformado nunca produce `AttributeError`, `TypeError` ni `KeyError` crudos hacia el llamador" | **HELD** | The top-level-list body raised `AttributeError: 'list' object has no attribute 'get'` pre-fix (RED evidence above) and now raises `IOLAPIError` (⊂ `IOLClientError`). Every raise inside the function is an `IOLAPIError` — no bare `assert`, no `TypeError`, no `ValueError`. Verified on both surfaces (Task 2). |
| "El guard discrimina forma, no cardinalidad: una lista vacía es una respuesta válida y nunca levanta" | **HELD** | `test_parse_get_instruments_by_type_response_empty_titulos_list_no_levanta` (`{"titulos": []}` → `[]`) and the pre-existing `..._returns_empty_list_when_missing` (`{}` → `[]`) both pass post-fix. The `.get("titulos", [])` default runs *before* the value guard, so the missing-key path is structurally unable to raise. |

## Flagged Assumption — still unresolved

**`FA-EDGE-TYP-01`** is restated here **unresolved**. This plan does **not** discharge it.

The deterministic edge probe (`EDGE_ABSENT=1`) could not classify requirement TYP-01 into
an edge category and returned no verification route; TYP-01 remains `unclassified` /
`unresolved`. What this plan claims is narrower and independently verifiable: the two
shape guards above, with the tests that prove them. **A verifier must not read this plan's
PASS as evidence that TYP-01's edge coverage is complete.**

## Gap Closure

30-VERIFICATION.md truth 7 — *"Ningún parser degrada silenciosamente ante una forma
inesperada"* — flips to **VERIFIED** for this parser: verification items 1-4 pass and all
three reproductions from the verification transcript raise `IOLAPIError` naming the
received type.

## Deviations from Plan

**1. [Rule 3 - Blocking] `uv sync` required before the baseline run**

- **Found during:** Task 1, baseline capture
- **Issue:** `uv run pytest packages/iol-client -q` failed with
  `ModuleNotFoundError: No module named 'iol_client'` — the fresh worktree had no synced
  virtualenv.
- **Fix:** `uv sync --all-packages --all-extras --dev --frozen` (the documented workspace
  install from CLAUDE.md). No dependency was added, changed, or resolved anew — `--frozen`
  installs exactly the committed `uv.lock`, so no package-legitimacy gate applies
  (consistent with threat register row `T-30-05-SC`).
- **Files modified:** none (venv only, gitignored)
- **Commit:** n/a

No other deviations. The fix landed verbatim as 30-REVIEW.md CR-02 proposed it.

## Out-of-Scope Confirmations

Per the plan's `<artifacts_this_phase_produces>` "do not touch" list, these were left
untouched and are confirmed unmodified in the diff: `models.py`, `_decode.py`, `client.py`,
`aio.py`, `_parse_list_or_raise`, `parse_get_quote_response` (WR-04),
`parse_get_historical_quotes_response`, `parse_get_instruments_response`, `README.md`,
`verification/snapshots/iol-client-surface.txt`, `__version__`.

`git diff --diff-filter=D --name-only HEAD~3 HEAD` returned empty — no file deletions.

## Known Stubs

None. No placeholder, hardcoded-empty, or TODO/FIXME value was introduced.

## Threat Flags

None. This plan adds no network endpoint, no auth path, no file access pattern, and no
schema change at a trust boundary. It *removes* surface: two previously-unvalidated
crossings of the `api.invertironline.com → _core` trust boundary are now checked.
Threats `T-30-05-01`, `T-30-05-02`, `T-30-05-03` and `T-30-05-04` are mitigated as planned;
`T-30-05-05` remains accepted (type name only, no payload dump).

## Commits

| Commit | Type | Description |
|--------|------|-------------|
| `f29386b` | test | add failing shape-guard tests for by_type envelope (CR-02) — RED |
| `e711d29` | fix | guard by_type envelope and titulos value (CR-02) — GREEN |
| `c184d70` | test | assert async surface inherits the by_type shape guard (CR-02) |

TDD gate sequence satisfied: `test(...)` → `fix(...)` for Task 1 (a `fix` commit is the
GREEN gate here rather than `feat` — the plan closes a defect, it adds no feature). No
REFACTOR gate was needed; the GREEN implementation is the final shape.

## Self-Check: PASSED

- `packages/iol-client/src/iol_client/_core.py` — FOUND, contains `isinstance(titulos, list)`
- `packages/iol-client/tests/test_core.py` — FOUND
- `packages/iol-client/tests/test_async_client.py` — FOUND
- Commit `f29386b` — FOUND
- Commit `e711d29` — FOUND
- Commit `c184d70` — FOUND
