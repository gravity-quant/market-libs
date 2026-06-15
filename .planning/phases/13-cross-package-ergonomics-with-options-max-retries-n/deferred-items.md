# Phase 13 — Deferred Items

Items discovered during Phase 13 execution that are out of scope per the SCOPE BOUNDARY rule (pre-existing issues in unrelated files). Logged here for future cleanup.

## mypy strict errors in `verification/` (pre-existing, not caused by Phase 13)

Plan 13-05 ran `uv run mypy --strict packages/.../src verification/` as part of the consolidated green gate. The mypy run reported 11 pre-existing errors in `verification/` files that predate Phase 13 (all originate from Phase 8 / Phase 11 commits — `43cdda9`, `967b868`, `383d000`, `bc4acc1`). They are NOT caused by Phase 13 changes and are out of scope per Rule 1/Rule 3 SCOPE BOUNDARY.

### Files affected

| File | Errors | Source phase | First introduced (commit) |
|------|--------|--------------|---------------------------|
| `verification/test_findings_dedupe_by_title.py` | 3× `Function is missing a type annotation` | Phase 11 | `967b868` |
| `verification/test_findings_append_only.py` | 5× `Function is missing a type annotation` | Phase 11 | `967b868` |
| `verification/test_async_configure_resource_warning.py` | 1× `Dict entry 0` (incompatible type) | Phase 8 | `43cdda9` / `a8342e7` |
| `verification/test_main_matriz_schema_snapshot_alignment.py` | 1× `Unused "type: ignore" comment` | Phase 11 | `383d000` |
| `verification/test_main_matriz_login_fail_uniformity.py` | 1× generator return type | Phase 11 | `bc4acc1` |

### Per-task evidence

```bash
# All errors reproduced on HEAD~2 (before Plan 13-05 Tasks 1/2 commits):
git checkout HEAD~2 && uv run mypy --strict verification/ 2>&1 | grep "error:" | wc -l
# → 12 (same count)
```

### Decision

- **Not fixed in Plan 13-05** because:
  1. SCOPE BOUNDARY rule: Pre-existing errors in files unrelated to Phase 13 (ERG-01) are out of scope.
  2. mypy config at workspace level (`pyproject.toml`) only checks `packages/*/src` by default — these errors only surface when an executor explicitly passes `verification/` to `--strict`, which Plans 1-4 did not do.
  3. Phase 13's actual deliverables (the with_options surface in 4 packages) pass mypy strict cleanly: `uv run mypy --strict packages/ambito-financiero-client/src packages/higyrus-client/src packages/matriz-client/src packages/iol-client/src verification/test_with_options.py` exits 0.

### One Phase-13-attributable mypy fix landed in Plan 13-05

While auditing the mypy run, Plan 13-05 noticed that `verification/test_with_options.py:226` carried an `# type: ignore[attr-defined]` comment placed by Plan 13-01 (RED-in-HEAD artifact) on the matriz mutation-gate call. Plan 13-04 added matriz's `with_options`, making the ignore comment "unused" (mypy `[unused-ignore]`). Plan 13-05 removed the now-stale comment (Rule 1 auto-fix — the comment is Phase-13-attributable, not pre-existing).

Commit: `[task 3 commit hash recorded in SUMMARY.md]`

### Suggested cleanup path

- Open a future quick task (`/gsd-quick`) to add type annotations to the 8 Phase-11 `verification/test_findings_*.py` functions and fix the Phase 8 + Phase 11 type-error sites.
- Estimated effort: ~15 min (the errors are all `disallow_untyped_defs = true` violations on test functions — straightforward `def f(...) -> None:` annotations).
