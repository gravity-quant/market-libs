# 001a FINDING — ámbito round-trip (SPIKE-006, D-RIGOR-02 items 1/2/3/4/5/6/7/9)

**Date:** 2026-07-02 · **Canary:** ámbito `aio.py` @ v1.2-head (UN-migrated) · **Tool:** `libcst >=1.8.0,<2` (ephemeral)

## Verdict summary

| Item | GO-det | Behavior | Verdict | Evidence |
|------|:------:|----------|:-------:|----------|
| 1 | ✅ | byte-identical vs CURRENT `client.py` | **FAIL** | `diff_vs_current_client.txt` — 13 hunks / 383 lines |
| 2 | | B8 `_raise_for_response` is-triple identity | **PASS** | same object id `0x…dd00` across mod/aio/_core |
| 3 | | `ruff format --check` clean | **FAIL** | length-changing swap left aio.py wrapping (see below) |
| 4 | ✅ | `ruff check` clean (I001 + ASYNC1xx) | **PASS** | `All checks passed!` — the item unasync FAILED |
| 5 | | `mypy --strict` clean | **PASS** | `Success: no issues found` |
| 6 | ✅ | ámbito mocked suite green (no circular import) | **FAIL** | circular self-import `_validate_max_retries` |
| 7 | | `lint-imports` 4 contracts intact | **PASS** | `4 kept, 0 broken` |
| 9 | | CSTTransformer subclasses pure `CSTNode→CSTNode` | **PASS** | `vars(t)` unchanged across visit; 14/14 tests |

Plain-text verdict lines (grep-checkable):

- item 1 (GO-det): FAIL
- item 2: PASS
- item 3: FAIL
- item 4 (GO-det): PASS
- item 5: PASS
- item 6 (GO-det): FAIL
- item 7: PASS
- item 9: PASS

**Aggregate (D-04, strict "any FAIL → NO-GO"): NO-GO.** 2 of 3 GO-determining items FAIL (1, 6); item 4
improved to PASS vs SPIKE-005. Items 1 and 6 both trace to the SAME source-shape root cause SPIKE-005 found —
content absent from `aio.py` cannot be synthesized by any pure transform of `aio.py` alone. Per D-04/D-08 this
signed NO-GO for the same root cause is an explicitly valid, guaranteed milestone deliverable; it was NOT
softened (no `aio.py` edit, no `client.py`-donor read).

## Q1 — content-absent-from-source obstacle (the decisive item-1 / item-6 evidence)

**Confirmed True (VERIFIED at runtime by the driver):**

- `_validate_max_retries` is **NOT** defined at module scope in `aio.py` (driver scan of module-level defs:
  `['__getattr__', '_get_default', '_request', 'aclose', 'configure', 'get_dollar_banco_nacion']` — absent).
  `aio.py:34` only *imports* it: `from ambito_financiero_client.client import _validate_max_retries`.
  The target `client.py:41-62` *defines* it as a 22-line function. A pure transform of `aio.py` cannot invent
  that body. `ImportDirectionNormalizer` was passed the driver-computed locally-defined set (which lacks the
  name) and therefore **RETAINED the self-import verbatim** — the honest, non-bypassing choice.
- The dotenv bootstrap `from ambito_financiero_client... from dotenv import load_dotenv` (`client.py:25`) +
  `load_dotenv()` (`client.py:30`) is **absent** from `aio.py` (D-19). (The string `load_dotenv` appears only
  inside an `aio.py` docstring — "D-19: NO llama `load_dotenv()`" — which is prose, not executable content; the
  driver detects the actual `from dotenv import load_dotenv` import statement, which is absent.)

**Consequence (item 6):** swapping the generated file in for `client.py` in a `/tmp` sandbox reproduces the
EXACT SPIKE-005 failure — `ImportError: cannot import name '_validate_max_retries' from partially initialized
module 'ambito_financiero_client.client' (most likely due to a circular import)` — because generated
`client.py:36` now imports the name FROM ITSELF. This is the signed same-root-cause evidence.

**Guardrail honored:** the only two escape hatches (migrate `aio.py` to hold the def — forbidden by D-03; or
read `client.py` as a donor — defeats single-sourcing, D-02) were both left closed. The residual divergence IS
the honest answer.

## Q2 — item-9 purity scope (flag for operator ratification, Plan 03 DECISION.md)

Interpreted at the **CLASS level** (RESEARCH A3): each of the five `CSTTransformer` subclasses is a pure
`CSTNode → CSTNode` function — asserted as `vars(instance)` byte-identical before/after `module.visit()` (no
cross-node mutable accumulation, no I/O, no global reads). `ImportDirectionNormalizer` takes an **immutable**
`frozenset` config at `__init__` (read-only closed-over constant — not accumulation). All cross-module /
scope-aware orchestration (scanning module-level defs, dropping the module-level `close` delegator, `@generated`
marker insertion) lives ONLY in the **impure driver** `experiment.py`, never in a transformer (Pattern 2 / Q2).

**Operator decision needed:** ratify the class-level reading. If item 9 is instead read as "the whole codegen
pipeline must be pure," it is unsatisfiable given the def-relocation need — but that reading is moot here since
items 1/6 already force a NO-GO.

## Q3 — docstring byte-identity beyond mechanical localization (flag for operator ratification)

`DocstringLocalizer` performs only the mechanical swaps (`asincrónico→sincrónico`, `AsyncClient→Client`, strip
`await `). The following regions diverge as **independently hand-authored prose**, NOT label swaps, and remain
in the item-1 residual:

- **Module docstring** — `aio.py` and `client.py` have different examples / phase notes (e.g. `aio.py` describes
  `await aio.aclose()` and the B7 `AsyncClient` context; `client.py` describes the `load_dotenv()` env note).
- **`with_options` docstring** — 43 lines in `client.py` vs 19 in `aio.py` (~24-line hand-authored divergence).
- **`_request` / `configure` / `get_dollar_banco_nacion` docstrings** — per-method prose differences.
- **`__reduce__` / `__deepcopy__` TypeError strings** — the length change from the `AmbitoFinancieroAsyncClient`
  → `AmbitoFinancieroClient` swap left libcst preserving `aio.py`'s multi-line wrapping (also the item-3 cause).

Closing these would require `DocstringLocalizer` to emit the ENTIRE target literal per module — i.e. embed the
oracle `client.py` in the tool, which is not single-sourcing. **Operator decision needed:** treat residual
docstring divergence as item-1 FAIL (current strict D-02 reading → NO-GO) or accept hardcoded target literals
(rejected here as oracle-embedding).

## Notable positive: item 4 (the item unasync FAILED) PASSES under libcst

`ruff check` is clean — I001 import-order is closed by `ImportNormalizer` (sorted
`from ambito_financiero_client import _core, _transport`), and zero residual ASYNC1xx (async fully stripped by
`AsyncToSync`). This is a genuine capability gain over the token-level unasync (SPIKE-005 item 4 FAIL). It does
not change the aggregate — items 1/6 content-absence still force NO-GO — but it is recorded for the DECISION.md
per-item map.

## Integrity witnesses

- `aio.py` byte-unchanged (`git diff --exit-code .../aio.py` CLEAN — D-03).
- `packages/` byte-unchanged after the item-6 `/tmp` sandbox (`git diff --exit-code packages/` CLEAN — T-18-02).
- `uv.lock` byte-unchanged (libcst ephemeral only — D-05).
- `_raise_for_response = _core.raise_for_response` emitted verbatim; B8 is-triple holds (Pitfall 4).
- `client.py` used ONLY as the `diff` oracle, never parsed as a content donor (D-02).

## Handoff (D-08)

On this NO-GO, the five transformer classes are NOT promoted for a Phase 19 rollout — REFAC-06 is on track to be
**permanently shelved** (final aggregation + signed verdict in Plan 18-03 `DECISION.md`). The transformers remain
in-tree as the canary-proven evidence that libcst closes the *mechanical* asymmetries (items 4/5/7/9 PASS,
docstring labels localized) but cannot cross the *content-absence* boundary (items 1/6) under the un-migrated
D-03 constraint.
