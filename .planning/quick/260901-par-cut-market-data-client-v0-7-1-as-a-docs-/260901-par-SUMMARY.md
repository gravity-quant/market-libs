---
phase: quick-260901-par
plan: 01
subsystem: release
tags: [release, market-data-client, errata, documentation, publish, PUB-01]
requires:
  - "commit 6f202ac (README correction) present only on milestone/v1.8-cierre-deuda-post-v1.7"
  - "market-data-client-v0.7.0 published tag + Release"
  - ".github/workflows/release.yml (read-only, unedited)"
provides:
  - "git-tag:market-data-client-v0.7.1 (annotated, on merge commit 3bff927)"
  - "gh-release:market-data-client-v0.7.1 (public, wheel + sdist)"
  - "published wheel METADATA carrying the corrected v0.7.0 changelog"
  - "origin/main advanced to two-parent merge commit 3bff927 (all pending v1.8 work)"
affects:
  - "consumers of market-data-client reading the bundled changelog"
  - "origin/main default branch of the public repository"
tech-stack:
  added: []
  patterns:
    - "documentation errata release: version-only src/ change, proven mechanically"
    - "two independent blocking-human checkpoints on two irreversible operations"
    - "CI gate asserted by positive count (15/15), never by absence-of-fail"
    - "post-publish proof via METADATA differential against the corrected wheel"
key-files:
  created:
    - .planning/quick/260901-par-cut-market-data-client-v0-7-1-as-a-docs-/260901-par-SUMMARY.md
  modified:
    - packages/market-data-client/pyproject.toml
    - packages/market-data-client/src/market_data_client/__init__.py
    - packages/market-data-client/README.md
    - uv.lock
decisions:
  - "Released from milestone/v1.8-cierre-deuda-post-v1.7, not a fresh branch off origin/main — forced, because 6f202ac (the payload) is not an ancestor of origin/main"
  - "Task 3's verify expression (origin/main == merge-base) is stale-by-construction under the repo's locked --merge pattern; replaced with an intent-preserving assertion rather than editing the committed plan"
metrics:
  duration: "~2h 17m wall (2026-09-01T21:30:48Z → 23:48:14Z, including two operator gate waits)"
  completed: 2026-09-01
status: complete
---

# Quick Task 260901-par: market-data-client v0.7.1 Documentation Errata Release Summary

Published `market-data-client` v0.7.1 — a zero-code-change errata release whose sole payload is the
corrected `v0.7.0` changelog, proven delivered by diffing the new wheel's bundled `METADATA` against
the wheel it corrects.

## What Was Built

`market_data_client-0.7.0-py3-none-any.whl` shipped a README whose `### v0.7.0` changelog documented
only the `Instrument` / `Segment` reconciliation and silently omitted the rest of the model surface
that landed in the same bump — including two **newly required** fields on already-published classes.
Because `pyproject.toml` declares `readme = "README.md"`, hatchling embeds the README as the
distribution long description, so the defect shipped *inside* the published artifact. The repository
README was corrected in `6f202ac`, but a published wheel cannot be rewritten. This release delivers
the correction as a new version.

## Version Transition — 4 sites, 5 textual substitutions

| # | Site | Before | After |
|---|------|--------|-------|
| 1 | `packages/market-data-client/pyproject.toml` | `version = "0.7.0"` | `version = "0.7.1"` |
| 2 | `.../src/market_data_client/__init__.py` | `__version__ = "0.7.0"` | `__version__ = "0.7.1"` |
| 3 | `README.md` — `uv add` git tag pin | `@market-data-client-v0.7.0` | `@market-data-client-v0.7.1` |
| 4a | `README.md` — `pip install`, **tag path segment** | `.../download/market-data-client-v0.7.0/` | `.../download/market-data-client-v0.7.1/` |
| 4b | `README.md` — `pip install`, **wheel filename** | `market_data_client-0.7.0-py3-none-any.whl` | `market_data_client-0.7.1-py3-none-any.whl` |

**4a and 4b live on the same line.** Updating only one is the exact defect Phase 34 shipped; both were
updated. In the README region above `## Changelog`: `0.7.0` occurs **0** times, `0.7.1` **3** times,
`market-data-client-v0.7.1` **2** times, the wheel filename **1** time.

Changelog ordering: first `###` heading after `## Changelog` is `### v0.7.1`, second is `### v0.7.0`.

## Documentation-Only Proof (mechanical, on branch AND on merged tree)

```
$ git diff --name-only market-data-client-v0.7.0..HEAD -- packages/market-data-client/src
packages/market-data-client/src/market_data_client/__init__.py

$ git diff -U0 market-data-client-v0.7.0..HEAD -- .../__init__.py | grep '^[+-][^+-]'
-__version__ = "0.7.0"
+__version__ = "0.7.1"
```

One file, two lines. Re-asserted against the merged tree (`market-data-client-v0.7.0..3bff927`) —
`__init__.py` and nothing else.

## Errata Justification — Measured, Not Asserted

| Token | packaged README @ tag `v0.7.0` | @ `HEAD` |
|---|---|---|
| `FeedSubscription` | **0** | 2 |
| `symbols_never_delivered` | **0** | 1 |

`HealthFeed` was deliberately **not** used as a differential token — it legitimately occurs twice in
the 0.7.0 README outside the changelog.

## `uv.lock`

Refreshed **exactly once**. `git log --oneline market-data-client-v0.7.0..HEAD -- uv.lock` → `1` commit;
`git diff --numstat` → `1 1`. `uv lock --check` exits 0.

## Local CI Mirror (all green)

`uv lock --check` · `uv sync --all-packages --all-extras --dev --frozen` · `uv run ruff check .`
(All checks passed) · `uv run ruff format --check .` (280 files already formatted) · `uv run lint-imports`
(5 kept, 0 broken) · `uv run mypy` (75 source files) · `uv run mypy packages/market-data-client/tests`
(36 source files) · `uv run pytest packages/market-data-client -q` (**727 passed**).

## Pull Request and Counted CI Gate

- **PR #17** — https://github.com/gravity-quant/market-libs/pull/17
- Title: `release: market-data-client v0.7.1 (errata documental del changelog 0.7.0) + cierre v1.8`
- Base `main` ← head `milestone/v1.8-cierre-deuda-post-v1.7`; the only open PR against `main` at creation.
- Diff stat: **42 files changed, 7558 insertions(+), 59 deletions(-)**
- `.github/workflows/` in diff: `ci.yml` only (Phase 45's pre-existing `d6b34f0`); `release.yml` absent (0).

**Gate asserted by positive count**, workflow run `33561700610`:

| Metric | Command | Value |
|---|---|---|
| Total rows | `gh pr checks 17 \| wc -l` | **15** |
| Rows with status `pass` | `gh pr checks 17 \| awk -F'\t' '$2=="pass"' \| wc -l` | **15** |
| market-data matrix rows | `gh pr checks 17 \| grep -c 'Tests · market-data-client · py3\.1[23]'` | **2** |

Literal output — all 15 rows `pass`: `Lint y formato (ruff)`, `pre-commit hooks`, `Type check (mypy)`,
and `Tests · {ambito-financiero,higyrus,iol,market-data,matriz,wallets}-client · py3.{12,13}`.
Zero rows `fail`, `pending`, `skipping` or `cancelled`. Branch head re-asserted equal to
`origin/<branch>` **after** the count, so no mid-run push cancelled the run.

This run also satisfies the one item `.planning/STATE.md` recorded as outstanding for Phase 45 —
the human check of green CI on GitHub Actions after the push.

## Gate-Authorship Audit

Command (run over the committed plan file):
```
grep -oE 'gate="blocking"' "$PLAN" | wc -l
grep -cE '^<task type="checkpoint:human-action" gate="blocking-human">$' "$PLAN"
```

| Run | Bare gate attributes | Line-anchored `human-action` blocking-human tags |
|---|---|---|
| Task 2 (before anything irreversible) | **0** | **2** (lines 444, 654) |
| Task 6 (close-out) | **0** | **2** |

Both gates were typed `checkpoint:human-action` — the only type that stops at BOTH the executor
(`gsd-executor.md:314-318`) and the orchestrator (`execute-phase.md:1057-1061`) under `auto_advance`,
and the only one exempt from `human_verify_mode: end-of-phase` suppression.

## Operator Approvals — Two Independent Gates, Recorded Separately

### Gate (a) — Task 3, before the merge

- **Reply, verbatim:** `"approved"`
- **Timestamp:** 2026-09-01, this session, immediately after the checkpoint details were presented.
- **Not auto-issued.** A literal operator response relayed by the coordinator. Not `auto_advance`, not
  yolo mode, not inferred from silence, not self-issued by the agent. The orchestrator auto-approve path
  at `execute-phase.md:1057-1061` did not fire — it routes `human-action` to "present to user"
  unconditionally.
- **State at the moment of reply:** PR #17 `OPEN`; `origin/main` unchanged at `bca1add`; release commit
  `5ffbf1b` not reachable from `origin/main`; no `market-data-client-v0.7.1` tag locally or on `origin`;
  prior tag `v0.7.0` intact; working tree clean outside `.planning/`.
- The operator was shown the PR URL/number, the literal `gh pr checks 17` output with counted totals,
  the diff stat, the four-site version transition with **both** wheel-line occurrences called out, the
  measured errata justification, the prominent statement that the merge publishes **all pending v1.8
  work** and not only the errata, and the live-confirmed fact that `main` has **no branch protection**
  (`GET /branches/main/protection` → 404).

### Gate (b) — Task 5, before the tag push

- **Reply, verbatim:** `"approved"`
- **Timestamp:** 2026-09-01, this session, immediately after the tag-push checkpoint details were presented.
- **Separate and independent** from gate (a). The coordinator explicitly stated gate (a) did not satisfy
  gate (b), and gate (b) was requested and answered as its own reply.
- **Not auto-issued.** Same basis as gate (a); the orchestrator auto-approve path did not fire.
- **State at the moment of reply:** `origin/main` the two-parent merge commit reading `0.7.1`; no
  `market-data-client-v0.7.1` tag locally or on `origin`; prior tag `v0.7.0` intact on `origin`.
- The operator was shown the freshly re-resolved merge SHA with its two parents, the merged-tree version
  read with `release.yml`'s own awk expression, the exact tag string character for character, the
  permanence warning, and the reminder that `v0.7.0` is neither deleted nor re-pointed.

**The two gates were never collapsed and neither was split.**

## Merge

`gh pr merge 17 --merge` — no `--squash`, no `--rebase`, no branch-delete flag, no `git push origin main`.

| | |
|---|---|
| Pre-merge `origin/main` (`PREMAIN`) | `bca1add0de9336ef5ef738cb11a2bcb7623f9968` |
| **`MERGE_SHA`** | `3bff927ea1e98dfb353af0f84ef8770a5f7c1039` |
| Parent 1 | `bca1add0de9336ef5ef738cb11a2bcb7623f9968` |
| Parent 2 | `81ebe42faca4f3b90d97add2eaef479c05b6afd5` |
| `git rev-list --parents -n1 \| wc -w` | **3** — a real two-parent merge, proven by parent count |
| Subject | `Merge pull request #17 from gravity-quant/milestone/v1.8-cierre-deuda-post-v1.7` |
| PR state | `MERGED` |
| Branch after merge | survived (`git ls-remote --heads origin <branch>` returns a ref) |

Merged tree, read with `release.yml`'s own `awk -F'"' '/^version[[:space:]]*=/{print $2; exit}'`:
`market-data-client` = **0.7.1**. Other five re-derived against `PREMAIN` and unchanged: `iol-client`
0.4.0, `higyrus-client` 0.3.0, `matriz-client` 0.3.0, `ambito-financiero-client` 0.2.0, `wallets-client`
0.2.0. `git diff --name-only $PREMAIN..$MERGE_SHA -- .github/workflows/release.yml` → **0** lines.

**Task 6 re-resolution matched:** `git rev-parse origin/main` after a fresh fetch returned
`3bff927ea1e98dfb353af0f84ef8770a5f7c1039`, identical to the value Task 4 recorded.

## Tag and Release

| | |
|---|---|
| Tag string | `market-data-client-v0.7.1` |
| Type | **annotated** (`git cat-file -t` → `tag`) |
| Anchor | `3bff927ea1e98dfb353af0f84ef8770a5f7c1039` (`git rev-list -n1 <tag>` == `MERGE_SHA`) |
| Message | `market-data-client v0.7.1 — errata documental: changelog 0.7.0 completo en el artefacto publicado (PUB-01)` |
| Push | `git push origin market-data-client-v0.7.1` — **by name**, exactly once, no `--force`, no bare `--tags` |
| `release.yml` run | **`33572531127`** — conclusion **`success`** |

Published Release assets, checked by exact filename:
- `market_data_client-0.7.1-py3-none-any.whl`
- `market_data_client-0.7.1.tar.gz`

### `release.yml` immutability — eighth reuse without an edit

sha256 `7109ff0b6819c596d07cc19df63a4d8218a9ee1e64379d1aa26ca45d1f5f1113` at **all three** refs:
`origin/main`, `market-data-client-v0.7.0`, `market-data-client-v0.7.1`. `sort -u` → exactly 1 line.
Phase 34's `git diff --name-only <prior-release-tag>..HEAD -- .github/workflows` form was **not** used —
it is stale-by-construction here because `ci.yml` legitimately differs across these refs.

### Tag counts — local and remote

| Package | Pre-push (local/remote) | Post-push (local/remote) |
|---|---|---|
| `iol-client` | 4 / 4 | 4 / 4 |
| `higyrus-client` | 3 / 3 | 3 / 3 |
| `matriz-client` | 3 / 3 | 3 / 3 |
| `ambito-financiero-client` | 2 / 2 | 2 / 2 |
| `wallets-client` | 1 / 1 | 1 / 1 |
| `market-data-client` | **8 / 8** | **9 / 9** |

Only `market-data-client` moved, by exactly one. No existing tag or Release was deleted or re-pointed;
`market-data-client-v0.7.0` remains intact on `origin`.

## Post-Publish Proof — the part that makes this release meaningful

Throwaway directory created **outside** the repository via `mktemp -d`; venv built with
`uv venv --python 3.12`; `sys.version` inside it: `3.12.13 (main, Mar 25 2026, 03:16:06) [Clang 22.1.1]`,
`sys.version_info[:2] == (3, 12)`.

Installed from the **full public Release asset URL**, never by bare name:

```
https://github.com/gravity-quant/market-libs/releases/download/market-data-client-v0.7.1/market_data_client-0.7.1-py3-none-any.whl
```

Resolved as `market-data-client==0.7.1 (from https://github.com/.../market_data_client-0.7.1-py3-none-any.whl)`
with deps `httpx==0.28.1`, `idna==3.19`, `python-dotenv==1.2.3`, `tenacity==9.1.4`,
`typing-extensions==4.16.0`. The workspace was not added to the venv.

**Literal script output:**

```
three-way version identity: 0.7.1 0.7.1 0.7.1
0.7.1 METADATA contains ALL of: FeedSubscription, FeedIngestor, HealthFeed, symbols_never_delivered, ### v0.7.1
0.7.0 METADATA (market_data_client-0.7.0-py3-none-any.whl, member market_data_client-0.7.0.dist-info/METADATA) contains NEITHER FeedSubscription NOR symbols_never_delivered
no code regression: Segment/Instrument/FeedSubscription chain green; no unrelated package importable
POST-PUBLISH 0.7.1 PASS — errata present in published METADATA, absent from prior wheel, no code regression
```

### The METADATA differential

| Token | 0.7.1 published wheel METADATA | 0.7.0 published wheel METADATA |
|---|---|---|
| `FeedSubscription` | **present** | **absent** |
| `symbols_never_delivered` | **present** | **absent** |
| `FeedIngestor` | present | (not used as differential) |
| `HealthFeed` | present | (deliberately not a differential token) |
| `### v0.7.1` | present | n/a |

The prior wheel was fetched with `gh release download market-data-client-v0.7.0 --pattern '*.whl'
--repo gravity-quant/market-libs` and read via `zipfile` from its `*.dist-info/METADATA` member — by
tag against this repository, never by name resolution.

**This is the assertion that matters.** The 0.7.0 release passed every pipeline gate and still shipped
an incomplete README. Only an artifact-level check can detect that class of defect; a green pipeline is
explicitly not accepted as proof.

### No code regression

`from market_data_client import Instrument, Segment, FeedSubscription, FeedIngestor, HealthFeed`
succeeds against the installed distribution; `"FeedSubscription" in __all__`;
`Segment.from_api({"segment": "DDA", "live_instruments": 3})` → `("DDA", 3)` and truthy;
`Segment.empty()` falsy; `Instrument.from_api({"symbol": "X", "market_id": "ROFX"})` →
`market_id == marketId == "ROFX"`; `FeedSubscription.from_api(None)` constructs. None of `iol_client`,
`higyrus_client`, `matriz_client`, `ambito_financiero_client`, `wallets_client` is importable.

The throwaway directory was removed; `git status --porcelain` in the repo is clean.

## Commits

| Commit | Message |
|---|---|
| `5ffbf1b` | `release(market-data-client): 0.7.1 — errata documental del changelog 0.7.0` (4 files: `pyproject.toml`, `__init__.py`, `README.md`, `uv.lock`) |
| `81ebe42` | `docs(quick): plan 260901-par — release market-data-client 0.7.1 errata documental` |
| `3bff927` | `Merge pull request #17 …` (on `origin/main`, two parents) |

The release change is one atomic commit listing exactly the four paths; `.planning/` changes are in a
separate commit, so the release commit stayed atomic while the planning artifacts still shipped with
the PR per repository convention.

## Security

A credential scan ran over the full `origin/main...HEAD` diff before the push (GitHub token prefixes,
private-key headers, AWS keys, Slack tokens, `client_secret`/`password` assignments, and `.env` paths) —
**no match**. `gh auth status` was used for auth verification and its output redacts the token; no
token, SSH key or credential was echoed at any point. The PR body, tag message and Release notes
(`--generate-notes`) carry no secret. The post-publish download used an unauthenticated public URL.

No new third-party package was introduced: the only install-shaped operations were `uv sync --frozen`
against the existing committed `uv.lock` (churn asserted at `1 1`) and installing this repository's own
wheel from its public GitHub Release asset URL.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking issue] Task 3's `<verify>` expression is stale-by-construction; replaced with an intent-preserving assertion**

- **Found during:** Task 3 (the first blocking checkpoint), before presenting to the operator.
- **Issue:** The block asserts `git rev-parse origin/main == git merge-base origin/main HEAD`, i.e.
  *"`origin/main` is an ancestor of `HEAD`."* That is **false by construction** in this repository.
  `origin/main` was `bca1add` — the two-parent merge commit of **PR #16** (the v0.7.0 release, merged
  earlier the same day). Under the repo's own locked release pattern (`--merge`, branch not deleted,
  branch reused for the next release), the merge commit lives only on `main`, so the branch is
  permanently `1 behind`. Measured: `ahead 35 / behind 1`, and `origin/main` already had 3 parent
  fields. The expression encodes a linear relationship the pattern makes impossible. `gh` reported the
  PR `MERGEABLE` / `CLEAN` throughout.
- **Fix:** The plan file was **not** edited — it is committed, inside the PR diff, and Task 6 re-audits
  it; an edit would have been a silent rewrite of a gate specification mid-flight. Instead the
  checkpoint's actual intent — *nothing irreversible ran before the operator's reply* — was asserted
  with an equivalent that holds under the real repository shape: PR #17 still `OPEN`; `origin/main`
  still exactly `bca1add`; the release commit `5ffbf1b` **not** reachable from `origin/main`; no
  `v0.7.1` tag locally or on `origin`; prior tag intact; working tree clean outside `.planning/`. All
  passed. The deviation was disclosed to the operator **in the checkpoint itself**, before the merge
  approval was given.
- **Files modified:** none.
- **Commit:** none (verification-only change).
- **Blast radius:** Task 5's verify block does not contain the defective expression and passed as
  written; Task 4's `wc -w == 3` two-parent assertion was unaffected. No other task was impacted.

No other deviations. The plan otherwise executed exactly as written.

## Authentication Gates

None. `gh auth status` exited 0 at every precondition check (account `sebadlf`, scopes `gist`,
`read:org`, `repo`, `workflow`); no re-authentication was required at any point.

## Known Stubs

None. This release changes no code — the only `src/` change is the `__version__` string, mechanically
proven at both the branch and the merged tree.

## Threat Flags

None. No new network endpoint, auth path, file-access pattern or schema change at a trust boundary was
introduced. Every mitigation in the plan's threat register (T-QP-01 … T-QP-10, T-QP-SC) was applied and
is evidenced above: the two `human-action` gates with recorded verbatim replies (T-QP-01), the counted
15/15 CI gate (T-QP-02), the parent-count-proven merge (T-QP-03), the docs-only `src/` proof on both
trees (T-QP-04), the re-resolved explicit tag anchor (T-QP-05), the by-name tag push with six tag counts
re-derived before and after (T-QP-06), `release.yml` sha256 identity across three refs (T-QP-07), the
full-URL install (T-QP-08), the METADATA differential rather than a green-pipeline inference (T-QP-09),
and the credential scan with no token echoed (T-QP-10).

## Requirements Satisfied

- **PUB-01** — `market-data-client` v0.7.1 released and published; the corrected changelog verified
  present inside the public wheel's own METADATA and provably absent from the wheel it corrects.

## Self-Check: PASSED

Files verified on disk: `260901-par-SUMMARY.md`, `packages/market-data-client/pyproject.toml`,
`packages/market-data-client/src/market_data_client/__init__.py`,
`packages/market-data-client/README.md`, `uv.lock`.

Commits verified reachable: `5ffbf1b`, `81ebe42`, `3bff927`, `bca1add`, `6f202ac`.

Artifacts verified: git tag `market-data-client-v0.7.1` resolves locally and on `origin`;
`gh release view market-data-client-v0.7.1` returns the Release. No missing items.
