# Deferred items — Phase 34

Out-of-scope discoveries logged during Phase 34 execution. **Not fixed** in this phase, per the
executor scope boundary (only issues directly caused by the current task's changes are auto-fixed).

## 1. REQUIREMENTS.md traceability table is stale for five completed requirements

**Found during:** 34-03 Task 3 state updates, while marking `PUB-TYP-01` complete.

**Issue:** the `## Traceability` table (`.planning/REQUIREMENTS.md`, rows ~66-72) still reads
`Pending` for requirements whose phases are complete and whose checkboxes above are already `[x]`:

| Requirement | Phase | Table says | Phase actually |
|---|---|---|---|
| `DEC-01` | 29 | Pending | Complete |
| `TYP-01` | 30 | Pending | Complete |
| `TYP-02` | 31 | Pending | Complete |
| `TYP-03` | 31 | Pending | Complete |
| `LIVE-TYP-01` | 33 | Pending | Complete |

Only `GATE-TYP-01` (Phase 32) reads `Complete`.

**Root cause:** `gsd-tools requirements mark-complete <ID>` short-circuits on
`already_complete` — when the checkbox is already `[x]` it returns without touching the
traceability row. So any requirement whose checkbox was set by some other path (or set, reverted and
re-set, as `PUB-TYP-01` was between 34-02 and 34-03) keeps a stale `Pending` row forever.

**Why not fixed here:** Phase 34 did not cause it, and the rows belong to Phases 29-33. Only
`PUB-TYP-01`'s row was corrected — that one *is* this phase's change. Fixing the other five is a
one-line-each edit but touches other phases' records.

**Suggested fix:** correct the five rows in a docs pass, and separately harden the handler so
`already_complete` still reconciles the traceability row rather than returning early.

## 2. The `.github/workflows` dir-wide diff assertion carries a stale baseline

**Found during:** 34-01 (Deviation 2), 34-02 (Deviation 3) and 34-03 (Deviation 1) — **three times
in one phase.**

**Issue:** the D-11 assertion form
`git diff --name-only <prior-release-tag>..<new-tag> -- .github/workflows` returns
`.github/workflows/ci.yml` rather than zero, because Phases 24/29/31/32 legitimately modified
`ci.yml` between releases. The assertion is inherited from the Phase 28 precedent, which was
single-package with no intervening CI work.

**The real invariant holds** and was asserted two other ways in 34-03: `release.yml` is byte-identical
by sha256 (`7109ff0b6819c596…`) across all four release refs, and
`git diff/log 97ccee2..origin/main -- .github/workflows` is empty (0 files, 0 commits).

**Why not fixed here:** editing `PLAN.md` mid-execution is prohibited, and patching a workflow to
satisfy a bad assertion is explicitly forbidden by D-11.

**Suggested fix:** change the pattern in `34-PATTERNS.md` (and any future release-phase plan) to
assert `-- .github/workflows/release.yml` by file, plus a phase-base-commit diff for the
"modified by this phase" invariant. Do not assert the whole `.github/workflows` directory against a
prior release tag.

## 4. `iol-client` README, memory doc, and version test are pre-existing gaps (code review WR-03/04/05)

**Found during:** `/gsd-code-review 34` (post-execution review, 2026-08-27).

`iol-client` v0.3.0 was published by this phase, but three gaps predate it and were only surfaced by
reviewing this phase's diff, not caused by it:

- **WR-03:** `packages/iol-client/README.md:7` says `uv add iol-client` with no PyPI warning and no
  working install command — the package isn't on PyPI (verified: `pypi.org/pypi/iol-client/json` →
  404) and the pipeline only creates GitHub Releases. The install as documented fails today.
- **WR-04:** no `iol-client-releases.md` memory doc exists (unlike market-data-client's), and no
  MEMORY.md index entry for iol-client.
- **WR-05:** `packages/iol-client/tests/` has no test binding `__version__` to `pyproject.toml`
  (market-data-client has `test_version_metadata.py` for this). `release.yml:47` only validates
  `pyproject.toml` against the tag — `__init__.__version__` drift would ship undetected.

**Why not fixed here:** none of these files were touched by Phase 34 (34-01 explicitly left
`iol-client/README.md` untouched per D-03 — its `### v0.3.0` changelog entry was already complete).
Fixing them is real, scoped work (mirror market-data-client's install block + memory doc + version
test) but is a new deliverable, not a correction of something this phase changed.

**Suggested fix:** a small follow-up phase or todo: (1) add the not-on-PyPI warning + git-subdir
install command to `iol-client/README.md`, mirroring market-data-client's block; (2) create
`iol-client-releases.md` + MEMORY.md index line following the market-data-client template; (3) copy
`test_version_metadata.py` into `packages/iol-client/tests/`.

## 3. `iol-client-releases.md` release memory does not exist

**Found during:** 34-03 Task 3 (a deliberate deferral, not a defect — recorded here for discovery).

`iol-client` v0.3.0 is now published, but there is no
`.claude/projects/-Users-admin-development-market-libs/memory/iol-client-releases.md`. Creating a new
memory file is the item deferred in `34-CONTEXT.md` § Deferred Ideas; no ROADMAP criterion required
it and Phase 34 deliberately did not open it. A future phase can pick it up intentionally — the
market-data-client file is the six-region template to follow.
