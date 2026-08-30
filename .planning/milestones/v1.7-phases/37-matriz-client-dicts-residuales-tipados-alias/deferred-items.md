# Phase 37 — Deferred Items

Discoveries logged during execution that are **out of scope** for the plan that found them.
Per the executor's scope boundary: only issues directly caused by the current task's changes
are auto-fixed; pre-existing failures in files the plan does not own are recorded here.

---

## DEF-37-01 — `mypy packages/matriz-client/tests` is red on four pre-existing errors — RESOLVED

**Resolution:** commit `2e28672`, applied by the orchestrator before Wave 3's second plan
(37-05) dispatched, per the "Suggested route" below. Fixed exactly as diagnosed: explicit
`# type: ignore[comparison-overlap]` on the two `scalar_passthrough` assertions
(`lastCalculation`, `tick`), and the misplaced `# type: ignore[attr-defined]` comment moved one
line down onto the actual attribute access. No model annotation was widened. Verified:
`uv run mypy packages/matriz-client/tests` and the repo-global `uv run mypy` both report zero
errors; `uv run --package matriz-client pytest packages/matriz-client/tests -q` → 547 passed.

**Found during:** plan 37-04, Task 1 acceptance sweep
**Owner:** plans 37-01 / 37-02 / 37-03 (the retypes that made these assertions non-overlapping)
**Not owned by 37-04:** the two files 37-04 is scoped to (`tools/check_surface_types.py`,
`packages/matriz-client/tests/test_surface_types_red.py`) both typecheck clean. Confirmed by
measurement, not inference: removing the new test module from the tree and re-running mypy
still reports the same four errors (`Found 4 errors in 2 files (checked 26 source files)`).

**Why it matters:** CI runs this exact command. `.github/workflows/ci.yml`, job `typecheck`,
step "mypy (tests por paquete)" loops `uv run mypy packages/$pkg/tests` over all six packages
with `set -e`. These four errors fail that job today.

**The four errors:**

| Location | Error | Likely cause |
|----------|-------|--------------|
| `packages/matriz-client/tests/test_core.py:372` | `comparison-overlap`: `result.lastCalculation` is `str \| None`, compared to `1669996294136` | assertion not updated alongside a retype |
| `packages/matriz-client/tests/test_decode.py:666` | `comparison-overlap`: `out["0"].tick` is `float \| None`, compared to `"nope"` | `TickPriceRange.tick` typed in 37-02; the `scalar_passthrough=True` assertion still expects the raw string |
| `packages/matriz-client/tests/test_decode.py:839` | `unused-ignore`: the `# type: ignore[attr-defined]` no longer suppresses anything on that line | the ignore is on the `assert (` line, one line above the attribute access |
| `packages/matriz-client/tests/test_decode.py:840` | `attr-defined`: `LogRecord` has no attribute `field_path` | the ignore comment needs to move to this line |

The last two are one defect: the `type: ignore` sits on the `assert (` opening line while the
attribute access it was meant to cover is on the next line. Moving the comment fixes both.

The first two are genuine assertion/type mismatches introduced by the retypes — a
`scalar_passthrough` value that is deliberately off-type at runtime needs an explicit cast or
`# type: ignore[comparison-overlap]` with a stated reason, not a loosened annotation. **Do not
resolve either by widening the model annotation back**; that would undo the phase.

**Why not fixed in 37-04:** the plan's `<verification>` block states that
`git diff --name-only` for the plan must list only `tools/check_surface_types.py` and
`packages/matriz-client/tests/test_surface_types_red.py`. Editing two further test files would
have violated the plan's own stated scope check. Routing this to the plan that owns the retypes
keeps the attribution — and the fix — where the context is.

**Suggested route:** a follow-up task in this phase (before phase verification), or
`/gsd-quick`. Four line-level edits, no source change.
