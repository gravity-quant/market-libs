---
phase: quick-260901-par
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - packages/market-data-client/pyproject.toml
  - packages/market-data-client/src/market_data_client/__init__.py
  - packages/market-data-client/README.md
  - uv.lock
autonomous: false
requirements: [PUB-01]
user_setup:
  - service: github
    why: "This task opens a PR against a PUBLIC default branch with no branch protection, merges it, and pushes an annotated release tag that fires `release.yml` and creates a PUBLIC GitHub Release. Both crossings are irreversible in practice and nothing on GitHub gates either one."
    dashboard_config:
      - task: "Ensure the `gh` CLI is authenticated (asserted in Task 1 via `gh auth status`; never echo the token)"
        location: "local shell — `gh auth status`"
      - task: "Be available to answer the FIRST blocking go/no-go checkpoint before the merge, and later the SECOND before the tag push. Both are authored as human-action checkpoints precisely so that neither `auto_advance` nor yolo mode can answer them for you."
        location: "the executing terminal session"

must_haves:
  truths:
    - "`market-data-client` reads `0.7.1` at all FOUR version sites, which is FIVE textual substitutions because the wheel install line carries the version twice (tag path segment AND wheel filename) — the exact defect Phase 34 shipped by updating only one of the two"
    - "The `src/market_data_client` tree is byte-identical to the `market-data-client-v0.7.0` tag except for the single `__version__` line — this is a documentation errata release with ZERO code change, and that claim is proven mechanically, not asserted in prose"
    - "`README.md` opens its `## Changelog` with `### v0.7.1` immediately above `### v0.7.0`, and the entry states plainly that this is a documentation-only release correcting the incomplete `v0.7.0` changelog"
    - "`uv.lock` was refreshed EXACTLY ONCE, in exactly one commit, with `1 1` churn, and `uv lock --check` exits 0"
    - "The release ships from the `milestone/v1.8-cierre-deuda-post-v1.7` branch because the README correction (commit `6f202ac`) lives ONLY there — it was measured NOT to be an ancestor of `origin/main`, so a branch cut from `origin/main` would build a wheel without the fix and defeat the entire purpose of the release"
    - "The PR reports exactly 15 checks and all 15 have status `pass`, of which exactly 2 are `Tests · market-data-client · py3.1x` — asserted by positive COUNT, never by the absence of the word fail"
    - "Both of this task's blocking human checkpoints are authored as `checkpoint:human-action` tasks whose gate attribute is the human-suffixed value — the only checkpoint type that stops at BOTH the executor layer (`gsd-executor.md:314-318`) and the orchestrator layer (`execute-phase.md:1057-1061`) while `auto_advance: true` is active, and the only one exempt from `human_verify_mode: end-of-phase` suppression"
    - "The two gates are INDEPENDENT: merge approval and tag-push approval are two separate operator replies, recorded separately, never collapsed into one"
    - "`origin/main` advances to a real merge commit with TWO parents, produced by `gh pr merge <n> --merge` — never squash, never rebase"
    - "`market-data-client-v0.7.1` is an ANNOTATED tag on the merge-commit SHA RE-RESOLVED live from `git rev-parse origin/main`, pushed BY NAME, never via a bare `--tags`"
    - "The published wheel's own bundled METADATA contains `FeedSubscription` and `symbols_never_delivered` while the already-published 0.7.0 wheel's METADATA does NOT — the differential that proves the errata was both warranted and actually delivered to consumers"
    - "`.github/workflows/release.yml` is byte-identical (sha256) at `HEAD`, `origin/main`, `market-data-client-v0.7.0` and `market-data-client-v0.7.1` — the eighth reuse without an edit"
    - "The other five packages' versions and tag counts are unchanged: `iol-client` 4, `higyrus-client` 3, `matriz-client` 3, `ambito-financiero-client` 2, `wallets-client` 1; `market-data-client` moves 8 → 9"
  prohibitions:
    - "Neither blocking human checkpoint may be satisfied by the agent itself, by `auto_advance`, by yolo mode, or by inferring approval from silence or from an ambiguous reply. Only a literal operator response counts, and it is recorded verbatim."
    - "The specific auto-approve path that must not fire is `.claude/gsd-core/workflows/execute-phase.md:1057-1061`, which spawns a continuation agent with `{user_response}` preset to `approved` for a `human-verify` checkpoint and to the first option for a `decision` checkpoint, WITHOUT ever reading the gate attribute. That is why both gates here are authored as human-action checkpoints: `execute-phase.md` routes `human-action` to 'present to user' unconditionally."
    - "Never edit `.github/workflows/release.yml` or `.github/workflows/ci.yml`. If a check or a run fails, surface the failing job and step. Phase 34 hit a red mypy check and fixed it by narrowing in the test, never by touching the workflow."
    - "Never touch any file under `packages/market-data-client/src/` other than the single `__version__` line. Any other source edit turns this from a documentation errata into an untested code release."
    - "Never bump, tag, changelog or publish any package other than `market-data-client`."
    - "Never run `git push --tags`. Milestone tags and package tags exist locally; a wholesale push publishes whatever is stale. Push the single tag by name."
    - "Never run `git tag` with the tag string alone and no commit-ish argument — that tags branch HEAD, and `release.yml`'s version check runs against the TAGGED tree."
    - "Never delete or re-point a tag, and never delete a Release, to 'try again'. The remedy for a bad publish is publishing a new version."
    - "Never report a CI gate as green from anything except an exact positive count. `pending`, `skipping`, `cancelled` and a zero-check run all read as green under an absence-of-failure check, and `cancel-in-progress: true` (`ci.yml:20`) makes `cancelled` genuinely reachable."
    - "Never push a commit to the branch while checks are in flight — it cancels the run and `cancelled` is not `fail`."
    - "Never run `uv lock` more than once, and never let a second commit touch `uv.lock`."
    - "Never install by bare package name in the post-publish verification. This package is not on PyPI and a bare `uv add market-data-client` would resolve a different project entirely."
    - "Never treat a green `release.yml` run report as post-publish proof. The published wheel must be installed from its public URL outside the repository and its bundled METADATA inspected."
  artifacts:
    - path: "packages/market-data-client/pyproject.toml"
      provides: "the version site `release.yml`'s awk gate reads"
      contains: "0.7.1"
    - path: "packages/market-data-client/README.md"
      provides: "the corrected changelog that is the entire payload of this release"
      contains: "### v0.7.1"
    - path: "git-tag:market-data-client-v0.7.1"
      provides: "the annotated tag that triggers release.yml"
      contains: "market-data-client-v0.7.1"
    - path: "gh-release:market-data-client-v0.7.1"
      provides: "public Release carrying the corrected-README wheel + sdist"
      contains: "market_data_client-0.7.1-py3-none-any.whl"
  key_links:
    - from: "packages/market-data-client/README.md"
      to: "gh-release:market-data-client-v0.7.1"
      via: "`readme = \"README.md\"` in pyproject.toml makes hatchling embed the README as the distribution long description, so the corrected changelog travels inside the wheel's own METADATA"
      pattern: "FeedSubscription"
    - from: "git-ref:origin/main"
      to: "git-tag:market-data-client-v0.7.1"
      via: "annotated tag created on the re-resolved merge SHA; release.yml's awk version-match gate runs against this tagged tree"
      pattern: "market-data-client-v0.7.1"
---

<!-- planner-discipline-allow: 0.7.0 -->

<objective>
Cut `market-data-client` v0.7.1 as a documentation errata release: bump the version at all four sites,
add a `### v0.7.1` changelog entry explaining that this release exists solely to ship a corrected
README, refresh `uv.lock` once, and take it through the repository's locked release pattern — PR with
a 15/15 counted CI gate, a blocking human gate before the merge, a real two-parent merge commit, a
second INDEPENDENT blocking human gate before the tag push, an annotated tag on the re-resolved merge
SHA, and post-publication proof from the public wheel.

Purpose: the published `market_data_client-0.7.0-py3-none-any.whl` bundles a README whose `v0.7.0`
changelog documented only the `Instrument` / `Segment` reconciliation and silently omitted the other
model-surface changes that shipped in the same bump — the new public `FeedSubscription` model, the new
REQUIRED `FeedIngestor.subscription` field, the new REQUIRED `HealthFeed.symbols_never_delivered`
field, and `Symbol.note`. A consumer reading only that changelog could not know that constructing
`FeedIngestor` or `HealthFeed` directly now needs an extra argument. The repository README was already
corrected in commit `6f202ac`, but the PUBLISHED ARTIFACT does not carry the correction. Only a new
release can deliver it.

Output: a public GitHub Release `market-data-client-v0.7.1` whose wheel and sdist bundle the corrected
README, proven by installing that wheel from its public URL and reading its own METADATA — including a
differential against the 0.7.0 wheel that proves the omission was real.

This plan is `autonomous: false`. It carries TWO independent blocking human checkpoints on two
distinct irreversible operations (the merge, then the tag push). They are never collapsed and never
auto-approved.
</objective>

<gate_authoring_semantics>
## Why both gates are `checkpoint:human-action` — read before editing Task 3 or Task 5

This repository has a documented history of authoring release gates with the BARE, non-`-human` form
of the gate attribute, which silently auto-approves under `auto_advance` / yolo mode. The measured
census of prior defective instances is five: `34-02-PLAN.md:243`, `34-03-PLAN.md:168`,
`40-01-PLAN.md:305`, `40-02-PLAN.md:259` and `40-03-PLAN.md:172`. Phase 44 eliminated the defect and
this plan reuses its exact construction.

The attribute alone is not sufficient. Phase 44's research measured the installed runtime and found
two independent auto-approval layers:

| Checkpoint type | Executor layer (`gsd-executor.md:314-318`) | Orchestrator layer (`execute-phase.md:1057-1061`) |
|---|---|---|
| `checkpoint:decision` | auto-selects the first option — no gate-attribute exception clause exists at all | auto-selects the first option, never reads the gate attribute |
| `checkpoint:human-verify` | honours the human-suffixed gate value and refuses to self-approve | **auto-approves anyway**, never reads the gate attribute |
| `checkpoint:human-action` | "STOP normally" — always stops | "present to user" — always stops |

The human-suffixed attribute string never appears anywhere under `.claude/gsd-core/workflows/`; the
orchestrator is structurally unaware of it. Additionally `.planning/config.json` sets
`workflow.human_verify_mode: "end-of-phase"`, under which the planner is instructed to emit NO
`checkpoint:human-verify` tasks at all — such a gate would vanish rather than merely collapse.
`checkpoint:human-action` is exempt from that suppression and stops at both layers.

Both gates therefore carry the human-suffixed attribute value literally in their opening tag AND are
typed `human-action`. Task 2 audits this IN THIS FILE, before anything irreversible runs, and Task 6
re-audits it at close-out. The audit is written so that it cannot match its own prose: the bare form of
the attribute is never spelled literally anywhere in this document.
</gate_authoring_semantics>

<execution_context>
@/Users/admin/development/market-libs/.claude/gsd-core/workflows/execute-plan.md
@/Users/admin/development/market-libs/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/phases/44-release-market-data-client-0-7-0/44-02-PLAN.md
@.planning/phases/44-release-market-data-client-0-7-0/44-03-PLAN.md
@.planning/phases/44-release-market-data-client-0-7-0/44-REVIEW.md
@packages/market-data-client/README.md
</context>

<measured_state>
Everything below was measured at plan-write time. Re-derive each value live; none of it may be trusted
as a literal at execution time.

| Fact | Measured value | Command |
|---|---|---|
| Current branch | `milestone/v1.8-cierre-deuda-post-v1.7` | `git rev-parse --abbrev-ref HEAD` |
| Branch vs `origin/main` | 33 commits ahead, 0 behind | `git rev-list --count origin/main..HEAD` |
| Branch vs `origin/<branch>` | 31 commits ahead, 0 behind (`origin` at `a9f3f1e`) | `git rev-list --left-right --count origin/<branch>...HEAD` |
| `6f202ac` (the README fix) in `origin/main`? | **NO** — it exists only on this branch | `git merge-base --is-ancestor 6f202ac origin/main` |
| `FeedSubscription` in README at tag `market-data-client-v0.7.0` | 0 occurrences | `git show market-data-client-v0.7.0:packages/market-data-client/README.md \| grep -c` |
| `FeedSubscription` in README at `HEAD` | 2 occurrences | `grep -c` |
| Open PRs against `main` | none | `gh pr list --state open` |
| Working tree | only `.planning/config.json` modified | `git status --porcelain` |
| All six package versions on `HEAD` vs `origin/main` | identical (mdc `0.7.0`, iol `0.4.0`, higyrus `0.3.0`, matriz `0.3.0`, ambito `0.2.0`, wallets `0.2.0`) | `awk` per `pyproject.toml` |
| Tag counts | iol 4, higyrus 3, matriz 3, ambito 2, wallets 1, market-data 8 | `git tag -l "<pkg>-v*" \| wc -l` |
| `release.yml` sha256 at `HEAD` / `origin/main` / tag `v0.7.0` | identical (`7109ff0b…`) | `git show <ref>:… \| shasum -a 256` |
| CI check total | 15 = 3 non-matrix jobs (`Lint y formato (ruff)`, `pre-commit hooks`, `Type check (mypy)`) + 6 packages × 2 Python versions | `ci.yml:24,101,119,140-152` |
| `packages/market-data-client/src` diff, tag `v0.7.0`..`HEAD` | EMPTY — no source file changed since the 0.7.0 tag | `git diff --name-only` |
</measured_state>

<scope_decisions>
- **The release ships from the existing `milestone/v1.8-cierre-deuda-post-v1.7` branch, NOT from a
  fresh branch cut off `origin/main`.** This is forced, not stylistic: commit `6f202ac` — the README
  correction that IS the payload of this release — was measured NOT to be an ancestor of `origin/main`.
  A branch cut from `origin/main` would build a wheel whose bundled README still omits the
  FeedIngestor / HealthFeed / FeedSubscription changes, i.e. it would republish the exact defect. It
  also matches the locked precedent: PR #16 shipped v0.7.0 from this same branch.

- **CONSEQUENCE THE OPERATOR MUST SEE, and the single most important thing on this page.** Because the
  branch is 31 commits ahead of `origin/<branch>` and 33 ahead of `origin/main`, the PR does NOT carry
  only the errata. It carries all pending v1.8 work: Phase 44's close-out, Phase 45's harness cleanup
  (`ci.yml` lint allowlist 13 → 18, the `main_*.py` drift dedupe, four new `verification/` test files,
  `tools/check_surface_types.py`), commit `6f202ac`, and the `.planning/` artifacts. "Documentation-only"
  is true of the market-data-client PACKAGE — `src/` does not change — and is NOT true of the merge.
  This must be presented verbatim at the first gate so the operator authorises what is actually
  happening. Do not soften it and do not omit it.

- **This is not scope creep, it is the outstanding v1.8 work reaching CI.** `.planning/STATE.md` records
  Phase 45 as complete with one item pending: "**human check** de CI verde en GitHub Actions … tras el
  push". The 15/15 gate in Task 2 is exactly that check. Say so at the gate; do not claim it as a goal
  of this task.

- **`.planning/` stays in the diff.** Do not run `/gsd-pr-branch` and do not filter the planning
  artifacts out — they have shipped with every prior release of this repository.

- **`.github/workflows/` is read-only for this task.** `ci.yml` already differs from `origin/main` on
  this branch because of Phase 45 commit `d6b34f0`; that is pre-existing branch content, not something
  this task creates or may extend. `release.yml` is untouched — this is its eighth reuse without an
  edit, asserted by sha256 digest identity across four refs, never by the Phase-34
  `git diff --name-only <prior-release-tag>..HEAD -- .github/workflows` form, which is
  stale-by-construction and failed three times during that phase.

- **The check total 15 is structural.** `matrix.package` (`ci.yml:145-152`) lists all six packages
  unconditionally, so 6 × 2 = 12 test checks plus three non-matrix jobs is invariant to how many
  packages a PR touches. It is safe to hardcode. The PR number and every tag count are NOT — re-derive
  them live.

- **`paths-ignore` is a live hazard here and the reason the count must be 15, not merely non-zero.**
  `ci.yml:6-13` ignores `**.md` and `.gitignore`. A purely-Markdown diff would trigger ZERO checks, and
  "no checks" is not green. This release escapes that only because the version bump also touches
  `pyproject.toml`, `__init__.py` and `uv.lock`. Assert the total.

- **No new tests.** `workflow.tdd_mode` is enabled project-wide, but this task produces no production
  code: the only `src/` change is a version string, and the release is defined by the absence of code
  change. There is nothing whose input/output could be pinned by a failing test first. The assertions
  in Task 6 are acceptance probes against a published distribution and reuse behaviours Phase 43
  already pinned with real pytest suites.

- **Every automated verify block is wrapped in `bash -c`**, using only double quotes internally with
  `\"` and `\$` escapes, because zsh word-splitting was measured to break bare blocks on this machine.
</scope_decisions>

<reversibility_gates>
| Task | Operation | Reversibility | Gate |
|---|---|---|---|
| Task 1 | version bump, changelog, `uv lock`, commit, branch push | reversible — a forward commit fixes anything; the branch is not `main` | none needed |
| Task 2 | `gh pr create`, `gh pr checks --watch`, in-file gate audit | reversible / read-only | none needed |
| Task 3 | operator go/no-go | n/a — this IS the gate | **blocking human checkpoint (a)** |
| Task 4 | `gh pr merge <n> --merge` | **irreversible in practice** — publishes the whole pending v1.8 diff to the public default branch | gated by Task 3 |
| Task 5 | operator go/no-go | n/a — this IS the gate | **blocking human checkpoint (b)** |
| Task 6 | `git push origin market-data-client-v0.7.1` | **irreversible** — fires `release.yml`, creating a PUBLIC Release that cannot be cleanly un-published nor its tag cleanly re-pointed | gated by Task 5 |
| Task 6 | throwaway venv install + assertions | fully reversible — scratch directory outside the repo | none needed |

Two irreversible operations, two independent gates. Collapsing them, or adding a third, breaks the
construction this plan exists to reuse.
</reversibility_gates>

<tasks>

<task type="auto">
  <name>Task 1: Bump to 0.7.1 at all four version sites, add the `### v0.7.1` errata changelog entry, refresh `uv.lock` exactly once, mirror the CI gates locally, and push the branch</name>
  <files>packages/market-data-client/pyproject.toml, packages/market-data-client/src/market_data_client/__init__.py, packages/market-data-client/README.md, uv.lock</files>
  <read_first>
    - `packages/market-data-client/README.md` lines 7-25 (the two version-pinned install lines) and
      lines 123-205 (the `## Changelog` heading, the whole `### v0.7.0` entry including the
      `FeedIngestor` / `HealthFeed` / `Symbol` table added by `6f202ac`, and the `### v0.6.0` boundary).
      The new entry is inserted between line 123 and line 125.
    - `packages/market-data-client/pyproject.toml` line 3 and `readme = "README.md"` on line 5 — the
      second is why the README travels inside the wheel's METADATA and why a documentation errata needs
      a real release at all.
    - `packages/market-data-client/src/market_data_client/__init__.py` line 165 — the `__version__`
      assignment, which is the ONLY line of `src/` this task may touch.
    - `.github/workflows/ci.yml` lines 24-45 (the `lint` job: `uv lock --check`, `uv sync … --frozen`,
      `uv run ruff check .`, `uv run ruff format --check .`, `uv run lint-imports`) and lines 119-136
      (the `typecheck` job: `uv run mypy`, then `uv run mypy packages/<pkg>/tests`). READ-ONLY.
    - `.planning/phases/44-release-market-data-client-0-7-0/44-REVIEW.md` — CR-01, the review finding
      that produced `6f202ac` and this errata; its wording is the source for the changelog entry.
    - This plan's `<measured_state>` and `<scope_decisions>` blocks.
  </read_first>
  <action>
    (a) Preconditions. `gh auth status` exits 0 (never echo the token — the command already redacts it).
    `git rev-parse --abbrev-ref HEAD` is `milestone/v1.8-cierre-deuda-post-v1.7`.
    `git status --porcelain` shows NOTHING outside `.planning/` — a modified `.planning/config.json` is
    expected and permitted; any dirt under `packages/`, `uv.lock`, `.github/`, `main_*.py`,
    `verification/` or `tools/` means STOP and surface it. Re-derive the branch-vs-remote counts rather
    than trusting this plan's table.

    (b) Assert the release is warranted BEFORE producing it. At tag `market-data-client-v0.7.0`, the
    packaged README must contain ZERO occurrences of `FeedSubscription` and ZERO of
    `symbols_never_delivered`; at `HEAD` it must contain at least one of each. If the tagged README
    already carried them, the errata is unnecessary — STOP and surface it. Do NOT use `HealthFeed` as a
    differential token: it legitimately occurs twice in the 0.7.0 README outside the changelog.

    (c) Bump the version at FOUR sites, which is FIVE textual substitutions:
      1. `packages/market-data-client/pyproject.toml` — the `version = ` line becomes exactly
         `version = "0.7.1"`.
      2. `packages/market-data-client/src/market_data_client/__init__.py` — the `__version__` line
         becomes exactly `__version__ = "0.7.1"`. This is the ONLY line of `src/` that changes.
      3. `packages/market-data-client/README.md`, the `uv add` install line — the git tag pin becomes
         `@market-data-client-v0.7.1`.
      4. `packages/market-data-client/README.md`, the `pip install` wheel line — this line carries the
         version TWICE: once as the tag path segment `market-data-client-v0.7.1` and once as the wheel
         filename `market_data_client-0.7.1-py3-none-any.whl`. Update BOTH. Updating only one is the
         exact defect Phase 34 shipped.
    Touch no other occurrence of the prior version anywhere: every remaining one lives inside the
    changelog history, where it is correct and must stay.

    (d) Insert a new `### v0.7.1` entry immediately after the `## Changelog` heading and immediately
    above `### v0.7.0`. Write it in Spanish, matching the surrounding entries. It must state, concretely:
      - that this is a DOCUMENTATION-ONLY errata release with no code change, and that the
        `src/market_data_client` tree is byte-identical to the prior version apart from `__version__`;
      - what was wrong: the README bundled inside the PUBLISHED wheel and sdist of the prior version
        documented only the `Instrument` / `Segment` reconciliation and OMITTED the rest of the surface
        that shipped in the same bump — the new public model `FeedSubscription`, the new REQUIRED field
        `FeedIngestor.subscription`, `FeedIngestor.last_error_age_seconds`, `FeedIngestor.last_error_at`,
        the new REQUIRED field `HealthFeed.symbols_never_delivered`, and `Symbol.note`;
      - the consequence: a consumer reading only that changelog could not know that constructing
        `FeedIngestor` or `HealthFeed` directly (not via `from_api`) now requires an extra argument;
      - that the repository README was already corrected in commit `6f202ac`, that the published
        artifact does not carry the correction, and that this release exists solely to deliver it;
      - that migration from the prior version is EMPTY — no behaviour, signature or surface change —
        and that the tables that matter are the ones in the `### v0.7.0` entry below, now complete.
    Do not restate the migration tables; point at them.

    (e) Run `uv lock` EXACTLY ONCE. The workspace records each member's version, so the bump makes the
    lock stale and `ci.yml`'s `uv lock --check` step would fail without this. Expect a one-line change.
    Do not run it a second time and do not let any later commit touch `uv.lock`.

    (f) Mirror the CI gates locally, in this order, all must pass: `uv lock --check`;
    `uv sync --all-packages --all-extras --dev --frozen`; `uv run ruff check .`;
    `uv run ruff format --check .`; `uv run lint-imports`; `uv run mypy`;
    `uv run mypy packages/market-data-client/tests`; `uv run pytest packages/market-data-client`.
    The Python 3.13 legs and the other five packages' test legs are proven by CI in Task 2 — do not
    claim them here. If a gate fails, fix the code; never patch a workflow.

    (g) Commit the release change as ONE atomic commit listing the four paths EXPLICITLY, so no
    `.planning/` file rides along:
    `git commit packages/market-data-client/pyproject.toml packages/market-data-client/src/market_data_client/__init__.py packages/market-data-client/README.md uv.lock -m "release(market-data-client): 0.7.1 — errata documental del changelog 0.7.0"`.
    Then commit any pending `.planning/` changes — including this plan file and the modified
    `config.json` — in a SEPARATE `docs(quick):` commit, so the release commit stays atomic and the
    planning artifacts still ship with the PR per repository convention.

    (h) Scan the full `origin/main...HEAD` diff for credentials before pushing. Then push the branch:
    `git push origin milestone/v1.8-cierre-deuda-post-v1.7`. This is a fast-forward of ~33 commits onto
    a branch `origin` already has at `a9f3f1e`; no force flag is permitted. Do NOT create a PR, do NOT
    merge and do NOT create any tag in this task.
  </action>
  <verify>
    <automated>bash -c 'set -e; cd "$(git rev-parse --show-toplevel)"; R=packages/market-data-client/README.md; gh auth status >/dev/null 2>&1; B=$(git rev-parse --abbrev-ref HEAD); test "$B" = "milestone/v1.8-cierre-deuda-post-v1.7"; test -z "$(git status --porcelain | grep -v " .planning/" || true)"; grep -qx "version = \"0.7.1\"" packages/market-data-client/pyproject.toml; test "$(awk -F"\"" "/^version[[:space:]]*=/{print \$2; exit}" packages/market-data-client/pyproject.toml)" = "0.7.1"; grep -qx "__version__ = \"0.7.1\"" packages/market-data-client/src/market_data_client/__init__.py; REG=$(awk "/^## Changelog\$/{exit} {print}" "$R"); test "$(printf "%s\n" "$REG" | grep -o "0\.7\.0" | wc -l | tr -d " ")" = "0"; test "$(printf "%s\n" "$REG" | grep -o "0\.7\.1" | wc -l | tr -d " ")" = "3"; test "$(printf "%s\n" "$REG" | grep -o "market-data-client-v0\.7\.1" | wc -l | tr -d " ")" = "2"; test "$(printf "%s\n" "$REG" | grep -o "market_data_client-0\.7\.1-py3-none-any\.whl" | wc -l | tr -d " ")" = "1"; test "$(awk "/^## Changelog\$/{f=1; next} f && /^### /{print; exit}" "$R")" = "### v0.7.1"; test "$(awk "/^## Changelog\$/{f=1; next} f && /^### /{c++; if(c==2){print; exit}}" "$R")" = "### v0.7.0"; OLD=$(git show market-data-client-v0.7.0:"$R"); test "$(printf "%s\n" "$OLD" | grep -c "FeedSubscription" || true)" = "0"; test "$(printf "%s\n" "$OLD" | grep -c "symbols_never_delivered" || true)" = "0"; grep -q "FeedSubscription" "$R"; grep -q "symbols_never_delivered" "$R"; OTHER=$(git diff --name-only market-data-client-v0.7.0..HEAD -- packages/market-data-client/src | grep -vx "packages/market-data-client/src/market_data_client/__init__.py" | wc -l | tr -d " "); test "$OTHER" = "0" || { echo "NOT A DOCS-ONLY RELEASE: $OTHER other src files changed"; exit 1; }; test "$(git diff -U0 market-data-client-v0.7.0..HEAD -- packages/market-data-client/src/market_data_client/__init__.py | grep -c "^[+-][^+-]")" = "2"; test "$(git log --oneline market-data-client-v0.7.0..HEAD -- uv.lock | wc -l | tr -d " ")" = "1"; test "$(git diff --numstat market-data-client-v0.7.0..HEAD -- uv.lock | awk "{print \$1 \" \" \$2}")" = "1 1"; uv lock --check; uv run ruff check .; uv run ruff format --check .; uv run lint-imports; uv run mypy; uv run mypy packages/market-data-client/tests; uv run pytest packages/market-data-client -q; for P in iol-client higyrus-client matriz-client ambito-financiero-client wallets-client; do NEW=$(git show HEAD:packages/$P/pyproject.toml | awk -F"\"" "/^version[[:space:]]*=/{print \$2; exit}"); OLDV=$(git show origin/main:packages/$P/pyproject.toml | awk -F"\"" "/^version[[:space:]]*=/{print \$2; exit}"); test "$NEW" = "$OLDV" || { echo "UNCHANGED PACKAGE MOVED: $P $OLDV -> $NEW"; exit 1; }; done; test "$(for X in HEAD origin/main market-data-client-v0.7.0; do git show "$X:.github/workflows/release.yml" | shasum -a 256 | cut -d" " -f1; done | sort -u | wc -l | tr -d " ")" = "1"; git fetch origin "$B" --quiet; test "$(git rev-parse HEAD)" = "$(git rev-parse "origin/$B")"; test -z "$(git tag -l "market-data-client-v0.7.1")"; echo PASS'</automated>
  </verify>
  <acceptance_criteria>
    - `grep -qx 'version = "0.7.1"' packages/market-data-client/pyproject.toml` succeeds, and reading the same file with `release.yml`'s own expression `awk -F'"' '/^version[[:space:]]*=/{print $2; exit}'` outputs `0.7.1` — read with the pipeline's own reader so the assertion cannot disagree with the gate that decides whether the release publishes
    - `grep -qx '__version__ = "0.7.1"' packages/market-data-client/src/market_data_client/__init__.py` succeeds
    - In the README region ABOVE the `## Changelog` heading (extracted with `awk '/^## Changelog$/{exit} {print}'`, so changelog history is excluded): occurrences of the prior version string are exactly `0`, occurrences of `0.7.1` are exactly `3`, occurrences of `market-data-client-v0.7.1` are exactly `2` and occurrences of `market_data_client-0.7.1-py3-none-any.whl` are exactly `1` — proving BOTH version references on the wheel install line were updated, which is the exact defect Phase 34 shipped
    - The first `###` heading after `## Changelog` is `### v0.7.1` and the second is `### v0.7.0` — the new entry sits above the one it corrects
    - The `### v0.7.1` entry states it is documentation-only with no code change, names the omitted surface (`FeedSubscription`, `FeedIngestor.subscription`, `HealthFeed.symbols_never_delivered`, `Symbol.note`), cites commit `6f202ac`, and states that migration from the prior version is empty
    - At tag `market-data-client-v0.7.0` the packaged README contains `0` occurrences of `FeedSubscription` and `0` of `symbols_never_delivered`, while at `HEAD` both are present — the errata is warranted, measured rather than assumed
    - `git diff --name-only market-data-client-v0.7.0..HEAD -- packages/market-data-client/src` lists NOTHING except `__init__.py`, and `git diff -U0 … -- __init__.py | grep -c '^[+-][^+-]'` outputs `2` — exactly one removed and one added line. This is the mechanical proof that the release is documentation-only
    - `git log --oneline market-data-client-v0.7.0..HEAD -- uv.lock | wc -l` outputs `1` and `git diff --numstat … -- uv.lock` outputs `1 1` — `uv lock` ran exactly once, in exactly one commit, with one-line churn
    - `uv lock --check`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run lint-imports`, `uv run mypy`, `uv run mypy packages/market-data-client/tests` and `uv run pytest packages/market-data-client` all exit 0
    - For each of `iol-client`, `higyrus-client`, `matriz-client`, `ambito-financiero-client` and `wallets-client`, the `HEAD` version equals the `origin/main` version, each re-derived live rather than compared against a literal
    - The sha256 of `.github/workflows/release.yml` is identical at `HEAD`, `origin/main` and `market-data-client-v0.7.0` — `sort -u` over the three digests yields exactly one line. Phase 34's `git diff --name-only <prior-release-tag>..HEAD -- .github/workflows` form was NOT used
    - `git rev-parse HEAD` equals `git rev-parse origin/milestone/v1.8-cierre-deuda-post-v1.7` — the branch was pushed, fast-forward, with no force flag
    - `git tag -l 'market-data-client-v0.7.1'` is empty, and no `gh pr create`, `gh pr merge` or `git tag` command was executed in this task
    - The release change is one atomic commit listing exactly the four paths; `.planning/` changes are in a separate commit; a credential scan over `origin/main...HEAD` was run before the push and no secret was echoed
  </acceptance_criteria>
  <done>All four version sites read `0.7.1` with both occurrences on the wheel install line updated; the `### v0.7.1` errata entry sits directly above `### v0.7.0`; `src/` is provably unchanged apart from the single `__version__` line; `uv.lock` was refreshed exactly once with `1 1` churn; every mirrored CI gate is green locally; the other five packages are untouched; `release.yml` is byte-identical across three refs; and the branch is pushed with no PR, no merge and no tag.</done>
</task>

<task type="auto">
  <name>Task 2: Create the v0.7.1 release PR, assert 15/15 checks pass BY COUNT with 2 market-data rows, and audit this plan's gate authorship in-file before anything irreversible</name>
  <files>(git/gh operations — no working-tree files modified)</files>
  <read_first>
    - `.planning/phases/44-release-market-data-client-0-7-0/44-02-PLAN.md` Task 1 — the four-precondition
      block, the count-based CI gate and the in-file gate-authorship audit. The delta here: a
      documentation errata instead of a surface change, and one plan file instead of two.
    - `.github/workflows/ci.yml` — READ-ONLY. The trigger and `paths-ignore` (`:6-13`),
      `concurrency: cancel-in-progress: true` (`:20`), the three non-matrix job names
      (`Lint y formato (ruff)` `:24`, `pre-commit hooks` `:101`, `Type check (mypy)` `:119`), the test
      job name template (`:140`), `matrix.package` (`:145-151`) and `matrix.python-version` (`:152`).
    - This plan's `<gate_authoring_semantics>` block — the audit in step (e) is what proves both gates
      are real, and it must run BEFORE anything irreversible.
    - This plan's `<scope_decisions>` block, second and third bullets — the PR body and the Task 3 gate
      must both state plainly that the merge publishes all pending v1.8 work, not just the errata.
  </read_first>
  <action>
    (a) Preconditions, all four must hold: `gh auth status` exits 0; `git status --porcelain` is empty
    or shows only `.planning/` paths; the branch is `milestone/v1.8-cierre-deuda-post-v1.7`; and
    `git rev-parse HEAD` equals `git rev-parse origin/<branch>`. That last assertion is what Task 1's
    push makes true — if it is false, a PR whose head does not contain the release describes nothing.

    (b) Create a NEW PR with `gh pr create --base main --head milestone/v1.8-cierre-deuda-post-v1.7`.
    Capture the returned PR number into a variable and use it everywhere below; never hardcode a number.
    Measured at plan-write time: no open PR exists, so this is a create, never a `gh pr edit`.

    Title, following the `release: <scope>` convention established by PRs #8-#16:
    `release: market-data-client v0.7.1 (errata documental del changelog 0.7.0) + cierre v1.8`.

    Body wording is Claude's discretion; supply it with `--body-file` rather than an inline argument so
    multi-line Markdown survives shell quoting. It must state, concretely:
      - the exact version transition and that it is a DOCUMENTATION ERRATA with zero code change, with
        the mechanical proof quoted: `src/` diff against the prior tag is `__init__.py` only, two lines;
      - what the published prior wheel got wrong and what the new one fixes;
      - **that the PR is NOT docs-only at the repository level** — it carries all pending v1.8 work
        (Phase 44 close-out, Phase 45 harness cleanup including the `ci.yml` lint allowlist 13 → 18, the
        `main_*.py` drift dedupe, four new `verification/` tests, `tools/check_surface_types.py`) plus
        the `.planning/` artifacts, and that this CI run is the outstanding Phase-45 green-CI check
        `.planning/STATE.md` records as pending;
      - that NO other package is bumped or published in this round.
    The body must contain no credential and no secret value.

    (c) Wait for the checks to settle with `gh pr checks <n> --watch`, then take a final snapshot with
    `gh pr checks <n>`.

    (d) Assert the gate BY COUNT, never by the absence of the word "fail". Require all of: the total row
    count is exactly 15; the number of rows whose status field is `pass` is exactly 15; and exactly 2
    rows match `Tests · market-data-client · py3.1[23]`.

    Statuses other than `pass` include `fail`, `pending`, `skipping` and `cancelled` — an
    absence-of-failure check reads all of those as green, and `cancelled` is genuinely reachable because
    `ci.yml:20` sets `cancel-in-progress: true`. A Markdown-only diff would trigger ZERO checks
    (`paths-ignore: ["**.md", ".gitignore"]`), and "no checks" is not green — which is exactly why the
    total must equal 15 rather than merely being non-zero. This release escapes the Markdown-only trap
    only because the bump also touches `pyproject.toml`, `__init__.py` and `uv.lock`.

    Also re-assert `git rev-parse HEAD` equals `git rev-parse origin/<branch>` AFTER the count, so a
    mid-run push cannot have silently cancelled the run the count was taken from.

    (e) Run the in-file gate-authorship audit over THIS plan file, HERE, before anything irreversible:
      - the count of occurrences of the gate attribute set to the bare value — that is, the eight
        characters spelling "blocking" immediately enclosed in double quotes after `gate=`, with no
        `-human` suffix — must be exactly `0`. The human-suffixed form cannot match that pattern,
        because the closing quote does not follow there;
      - the count of LINE-ANCHORED opening tags — lines whose ENTIRE content is the `human-action`
        checkpoint opening tag carrying the human-suffixed gate value, matched with `^…$` so that prose
        and acceptance-criteria mentions of the same string are not counted — must be exactly `2`: the
        merge gate and the tag-push gate.
    If either count is wrong, STOP before creating anything and surface it: a wrong count means this
    task is about to reproduce, as a sixth occurrence, the exact defect Phase 44 eliminated.

    (f) Do NOT push any further commit to the branch while checks are running — it cancels the in-flight
    run. If a fix is genuinely required, land it, re-run `gh pr checks <n> --watch` to completion and
    re-assert the full count from scratch. Never patch `ci.yml` to make a check pass.

    (g) Do NOT merge in this task. Do NOT create or push any tag anywhere in this task.
  </action>
  <verify>
    <automated>bash -c 'set -e; cd "$(git rev-parse --show-toplevel)"; gh auth status >/dev/null 2>&1; test -z "$(git status --porcelain | grep -v " .planning/" || true)"; B=$(git rev-parse --abbrev-ref HEAD); test "$B" = "milestone/v1.8-cierre-deuda-post-v1.7"; git fetch origin "$B" --quiet; test "$(git rev-parse HEAD)" = "$(git rev-parse "origin/$B")"; PR=$(gh pr list --state open --base main --head "$B" --json number --jq ".[0].number"); test -n "$PR"; test "$(gh pr list --state open --base main --json number --jq "length")" = "1"; test "$(gh pr view "$PR" --json state --jq .state)" = "OPEN"; test "$(gh pr view "$PR" --json baseRefName --jq .baseRefName)" = "main"; test "$(gh pr view "$PR" --json headRefName --jq .headRefName)" = "$B"; gh pr view "$PR" --json title --jq .title | grep -q "^release: "; gh pr view "$PR" --json files --jq ".files[].path" | grep -q "^\.planning/"; gh pr view "$PR" --json files --jq ".files[].path" | grep -qx "packages/market-data-client/README.md"; TOTAL=$(gh pr checks "$PR" | wc -l | tr -d " "); PASSED=$(gh pr checks "$PR" | awk -F"\t" "\$2==\"pass\"" | wc -l | tr -d " "); test "$TOTAL" = "15" || { echo "EXPECTED 15 CHECK ROWS, GOT: $TOTAL"; exit 1; }; test "$PASSED" = "15" || { echo "EXPECTED 15 PASSING ROWS, GOT: $PASSED"; exit 1; }; MDC=$(gh pr checks "$PR" | grep -c "Tests · market-data-client · py3\.1[23]"); test "$MDC" = "2"; test "$(git rev-parse HEAD)" = "$(git rev-parse "origin/$B")"; P=".planning/quick/260901-par-cut-market-data-client-v0-7-1-as-a-docs-/260901-par-PLAN.md"; test -f "$P"; BAD=$(grep -oE "gate=\"blocking\"" "$P" | wc -l | tr -d " "); test "$BAD" = "0" || { echo "GATE AUTHORSHIP DEFECT: $BAD bare gate attributes found"; exit 1; }; GOOD=$(grep -cE "^<task type=\"checkpoint:human-action\" gate=\"blocking-human\">\$" "$P"); test "$GOOD" = "2" || { echo "EXPECTED EXACTLY 2 BLOCKING-HUMAN CHECKPOINT TAGS, FOUND: $GOOD"; exit 1; }; git fetch origin main --tags --quiet; test -z "$(git tag -l "market-data-client-v0.7.1")"; test -z "$(git ls-remote --tags origin "market-data-client-v0.7.1")"; echo "pr=$PR"; echo PASS'</automated>
  </verify>
  <acceptance_criteria>
    - `gh pr list --state open --base main --json number --jq 'length'` outputs `1`, and that PR's head is `milestone/v1.8-cierre-deuda-post-v1.7` — a NEW PR was created; no `gh pr edit` on a pre-existing PR was attempted
    - `gh pr view <n> --json title --jq .title` starts with `release: ` and names `market-data-client` v0.7.1
    - `gh pr view <n> --json state --jq .state` is `OPEN`, `baseRefName` is `main`, `headRefName` is the milestone branch
    - The PR body states the version transition, that the package change is documentation-only with the `src/` diff proof quoted, what the published prior wheel omitted, **that the PR nonetheless carries all pending v1.8 work and is the outstanding Phase-45 green-CI check**, and that no other package is bumped or published
    - `gh pr view <n> --json files --jq '.files[].path'` includes at least one path under `.planning/` and includes `packages/market-data-client/README.md` — planning artifacts were not filtered out and the errata payload is in the diff
    - `gh pr checks <n> | wc -l` outputs exactly `15`
    - `gh pr checks <n> | awk -F'\t' '$2=="pass"' | wc -l` outputs exactly `15` — no row is `fail`, `pending`, `skipping` or `cancelled`. The gate was asserted by positive count, never by grepping for the absence of `fail`
    - `gh pr checks <n> | grep -c 'Tests · market-data-client · py3\.1[23]'` outputs exactly `2` — the bumped package's matrix cells actually ran and passed
    - `git rev-parse HEAD` still equals `git rev-parse origin/<branch>` AFTER the count was taken — no commit was pushed mid-run, so no in-flight check was cancelled by `cancel-in-progress: true`
    - Over this plan file, the count of gate attributes set to the bare non-`-human` value is exactly `0`, and the LINE-ANCHORED count of `human-action` checkpoint opening tags carrying the human-suffixed gate value — matched with `^…$` so prose mentions are excluded — is exactly `2`, one per irreversible operation. Asserted BEFORE anything irreversible ran
    - `git tag -l 'market-data-client-v0.7.1'` and `git ls-remote --tags origin 'market-data-client-v0.7.1'` are both empty
    - No `gh pr merge`, no `git tag` and no `git push` command was executed in this task, and no file under `.github/workflows/` was modified
  </acceptance_criteria>
  <done>A new PR exists against `main` from the milestone branch with a `release: …` title, it carries the corrected README and the `.planning/` artifacts, `gh pr checks` reports 15 rows of which 15 are `pass` including exactly 2 market-data matrix rows, the branch head is unchanged since the count was taken, and the in-file gate audit returns zero bare gate attributes and exactly two human-action blocking-human checkpoint tags.</done>
</task>

<task type="checkpoint:human-action" gate="blocking-human">
  <name>Task 3: FIRST blocking go/no-go gate — before the IRREVERSIBLE merge to the public default branch</name>
  <files>none — this task modifies no file</files>
  <read_first>
    - This plan's `<gate_authoring_semantics>` block — why the task type is `human-action` and the
      two-layer measurement behind that choice.
    - This plan's `<scope_decisions>` block, second bullet — the consequence the operator must see: the
      merge publishes all pending v1.8 work, not only the errata. This is the single most important
      thing to present.
    - `.planning/phases/44-release-market-data-client-0-7-0/44-02-PLAN.md` lines 305-418 — the element
      inventory and the prose armour of the direct precedent. Copy the BODY; the precedent's own
      opening tag is correct here and is already reproduced above.
    - The Task 1 and Task 2 output already in context: the four version transitions, the docs-only
      `src/` diff proof, the `uv.lock` churn, the PR number and URL, and the literal counted check totals.
  </read_first>
  <acceptance_criteria>
    - The operator was shown: the PR URL and number, the literal `gh pr checks <n>` output with the counted totals (15 rows / 15 `pass` / 2 market-data matrix rows), the diff stat, the `0.7.1` transition at all four version sites with both occurrences on the wheel line called out, and an explicit statement that `main` has no branch protection so this approval is the only gate
    - The operator was shown, as a prominent RESOLVED read-back and not buried: that the merge publishes ALL pending v1.8 work (Phase 44 close-out, Phase 45 harness cleanup, `ci.yml` allowlist 13 → 18, `main_*.py` dedupe, four new `verification/` tests, `.planning/` artifacts) and NOT only the errata; and that "documentation-only" is a statement about the market-data-client package, whose `src/` diff against the prior tag is `__init__.py` only, two lines
    - The operator was shown the errata justification measured, not asserted: the packaged README at the prior tag contains zero occurrences of `FeedSubscription` and zero of `symbols_never_delivered`, and at `HEAD` contains both
    - No `gh pr merge`, no `git tag` and no `git push` command was executed before the operator's reply
    - The operator's reply is recorded verbatim in the SUMMARY together with its timestamp
    - The approval came from a literal operator response — not from `auto_advance`, not from yolo mode, not inferred from silence, and not self-issued by the agent. In particular the orchestrator auto-approve path at `execute-phase.md:1057-1061` did not fire, which is why this checkpoint is typed `human-action`
    - This approval is recorded SEPARATELY from the tag-push approval in Task 5 — the two gates were not collapsed into one
    - Execution continues to Task 4 ONLY if the reply is an explicit "approved"; any other reply (including silence, ambiguity, or "abort") halts the plan with the PR still open and `origin/main` unchanged
  </acceptance_criteria>
  <action>PAUSE. This is the first of exactly two blocking human checkpoints on irreversible operations for this task. Do NOT merge the PR, do NOT create any tag, and do NOT push anything until the operator explicitly replies "approved". This gate is never auto-approvable: `auto_advance` is active in `.planning/config.json` and does not satisfy it, silence does not satisfy it, an ambiguous reply does not satisfy it, and the agent may not self-issue it. If the operator replies "abort", stop cleanly with no irreversible action taken — the PR stays open and everything so far is revertible with a forward commit. Present: the PR URL and number, the literal `gh pr checks <n>` output with the counted totals, the diff stat, the four-site version transition with both wheel-line occurrences called out, the measured errata justification, the prominent statement that the merge publishes all pending v1.8 work and not only the errata, and an explicit statement that `main` has NO branch protection so this approval is the only gate.</action>
  <instructions>
    ## What has already been automated

    Task 1 bumped `market-data-client` to `0.7.1` at all four version sites — `pyproject.toml`,
    `__version__` in `__init__.py`, and the two version-pinned install lines in `README.md`, the wheel
    line carrying it twice — added the `### v0.7.1` errata entry directly above `### v0.7.0`, refreshed
    `uv.lock` exactly once with one-line churn, mirrored the CI gates locally (ruff check, ruff
    format --check, lint-imports, mypy global, mypy package tests, package pytest), scanned the diff for
    credentials, and pushed the branch.

    Task 2 created the release PR and proved the CI gate green by explicit count: 15 total check rows,
    15 with status `pass`, and exactly 2 `Tests · market-data-client · py3.1x` matrix rows. It also ran
    the in-file gate-authorship audit: zero bare gate attributes in this plan, and exactly two
    human-action blocking-human checkpoint tags — this one and the tag-push gate.

    ## What this release is, and what it is not

    **The package change is documentation-only.** `market-data-client` moves to 0.7.1 with ZERO code
    change. The proof is mechanical, not a claim: the diff of `packages/market-data-client/src` against
    the prior release tag lists exactly one file, `__init__.py`, with exactly two changed lines — the old
    and new `__version__`. Nothing else under `src/` moved.

    **Why it exists at all.** `pyproject.toml` declares `readme = "README.md"`, so hatchling embeds the
    README as the distribution long description — it travels INSIDE the wheel and sdist METADATA. The
    already-published prior wheel therefore bundles a README whose changelog documented only the
    `Instrument` / `Segment` reconciliation and OMITTED the rest of the surface that shipped in the same
    bump: the new public model `FeedSubscription`, the new REQUIRED field `FeedIngestor.subscription`,
    `FeedIngestor.last_error_age_seconds`, `FeedIngestor.last_error_at`, the new REQUIRED field
    `HealthFeed.symbols_never_delivered`, and `Symbol.note`. A consumer reading only that changelog could
    not know that constructing `FeedIngestor` or `HealthFeed` directly now needs an extra argument. The
    repository README was corrected in commit `6f202ac`, but the PUBLISHED ARTIFACT does not carry the
    correction, and only a new release can deliver it. Measured, not assumed: the packaged README at the
    prior tag contains ZERO occurrences of `FeedSubscription` and ZERO of `symbols_never_delivered`; at
    `HEAD` it contains both.

    **What is NOT documentation-only: the merge itself.** Read this part twice. The release ships from
    `milestone/v1.8-cierre-deuda-post-v1.7`, which is roughly 33 commits ahead of `origin/main`. That is
    forced, not stylistic — commit `6f202ac` exists ONLY on this branch and is not an ancestor of
    `origin/main`, so a branch cut from `origin/main` would build a wheel WITHOUT the fix and republish
    the exact defect. The consequence is that merging this PR publishes ALL pending v1.8 work to the
    public default branch, not just the errata:
      - Phase 44's close-out commits;
      - Phase 45's harness cleanup — the `ci.yml` lint allowlist widened from 13 to 18 files (`d6b34f0`),
        the intra-process drift dedupe across `main_iol.py`, `main_market_data.py`, `main_higyrus.py`,
        `main_matriz.py` and `main_ambito_financiero.py`, four new `verification/` test files, and a
        change to `tools/check_surface_types.py`;
      - commit `6f202ac` itself;
      - the `.planning/` artifacts, intentionally kept as in every prior release of this repository.

    This is not scope creep invented here: `.planning/STATE.md` records Phase 45 as complete with exactly
    one item outstanding — the human check that CI is green on GitHub Actions after the push. The 15/15
    count above IS that check. But it is your call whether to publish all of it in this merge.

    No other package is bumped, tagged or published. All five others sit at the same versions on `HEAD`
    as on `origin/main`, re-derived live.

    `.github/workflows/release.yml` has NOT been edited — its sha256 is identical at `HEAD`,
    `origin/main` and the prior release tag.

    The next task performs an operation that is irreversible in practice: merging this PR into `main`,
    the default branch of a PUBLIC repository. It will use `gh pr merge <n> --merge` — a real merge
    commit with two parents, never `--squash` and never `--rebase`. Squashing would orphan the SHAs that
    dozens of SUMMARY files across Phases 35-45 cross-reference by value; rebasing would rewrite history
    already reachable from published tags. The repository allows all three merge methods, so nothing but
    this instruction prevents the wrong one.

    CRITICAL CONTEXT: `main` has no branch protection. GitHub will merge this PR regardless of check
    status, with no required reviewers. The 15/15 count above and YOUR approval are the only things
    preventing an unverified build from landing on a public default branch.

    The release TAG and the public GitHub Release are NOT part of this approval. They are gated by a
    second, separate checkpoint later in this same plan.

    ## What you need to do

    1. Open the PR on GitHub. Confirm the title starts with `release: `, names `market-data-client`
       v0.7.1, base is `main`, head is `milestone/v1.8-cierre-deuda-post-v1.7`, and it is the ONLY open
       PR against `main`.
    2. Confirm you are willing to publish the WHOLE pending v1.8 branch in this merge, not only the
       errata. If you are not, reply "abort" — the alternative would require a different branch strategy
       and a re-plan, and cannot be improvised inside this run.
    3. Confirm `packages/market-data-client/README.md` opens its `## Changelog` with `### v0.7.1` above
       `### v0.7.0`, and that the new entry says plainly it is a documentation-only errata with no code
       change and no migration.
    4. Confirm the two install commands now pin `market-data-client-v0.7.1` and the
       `market_data_client-0.7.1-py3-none-any.whl` filename — BOTH places on the wheel line, not just
       one. This is the exact defect Phase 34 shipped.
    5. Confirm no file under `.github/workflows/` appears in the diff beyond Phase 45's pre-existing
       `ci.yml` allowlist commit, and that `release.yml` does not appear at all.
    6. Confirm the check table shows 15 rows and all 15 are `pass` — not pending, not cancelled, and not
       an empty table.
    7. Confirm you authorize the irreversible merge into public `main` NOW, and that you understand the
       tag push is a separate approval you will be asked for again.
  </instructions>
  <verification>After your reply, the agent verifies mechanically that nothing irreversible ran before it: the PR is still `OPEN`, `origin/main` is still an ancestor of the branch head, no `market-data-client-v0.7.1` tag exists locally or on `origin`, and the working tree carries nothing outside `.planning/`.</verification>
  <resume-signal>Type "approved" to proceed with `gh pr merge <n> --merge`, or "abort" (optionally describing blockers) to stop before any irreversible action. Anything other than an explicit "approved" means do not merge.</resume-signal>
  <verify>
    <automated>bash -c 'set -e; cd "$(git rev-parse --show-toplevel)"; B=$(git rev-parse --abbrev-ref HEAD); PR=$(gh pr list --state open --base main --head "$B" --json number --jq ".[0].number"); test -n "$PR"; test "$(gh pr view "$PR" --json state --jq .state)" = "OPEN"; git fetch origin main --tags --quiet; test "$(git rev-parse origin/main)" = "$(git merge-base origin/main HEAD)"; test -z "$(git tag -l "market-data-client-v0.7.1")"; test -z "$(git ls-remote --tags origin "market-data-client-v0.7.1")"; test -z "$(git status --porcelain | grep -v " .planning/" || true)"; echo "PASS — nothing irreversible happened before the operator reply"'</automated>
  </verify>
  <done>The operator was shown the PR, the counted 15/15 gate, the four-site version transition, the measured errata justification, the prominent statement that the merge publishes all pending v1.8 work, and the no-branch-protection warning; they replied with an explicit literal "approved" (or "abort"); the reply is recorded verbatim with its timestamp and with an explicit statement that it was not auto-issued; and at the moment of the reply the PR was still OPEN, `origin/main` was still un-advanced, and no tag existed locally or on `origin`.</done>
</task>

<task type="auto">
  <name>Task 4: Merge the PR with a real merge commit and verify `origin/main` advanced to a two-parent commit carrying the 0.7.1 bump</name>
  <files>(git/gh operations — no working-tree files modified)</files>
  <read_first>
    - `.planning/phases/44-release-market-data-client-0-7-0/44-02-PLAN.md` lines 420-497 (Task 3) — the
      merge command form, the two-parent assertion and the merged-tree version assertions.
    - `.github/workflows/release.yml` — READ-ONLY. The awk version-match gate
      (`awk -F\" '/^version[[:space:]]*=/{print $2; exit}' "packages/$PACKAGE/pyproject.toml"`, line 47)
      that will run against the TAGGED tree in Task 6, which is why this task asserts the merged tree
      already carries `0.7.1`.
    - This plan's `<measured_state>` table — the pre-merge versions of the other five packages, to be
      re-derived rather than trusted.
  </read_first>
  <action>
    Execute ONLY after Task 3 returned an explicit "approved" from the operator. If it returned anything
    else — including silence, ambiguity, or an auto-advance signal — stop.

    (a) Capture the pre-merge `origin/main` SHA first: `PREMAIN=$(git rev-parse origin/main)`. It is the
    baseline for the unchanged-package and workflow-diff assertions below.

    (b) Merge with `gh pr merge <n> --merge`. The `--merge` flag is mandatory: `--squash` would collapse
    the branch into a single commit and orphan every SHA that the Phase 35-45 SUMMARYs cross-reference by
    value; `--rebase` would rewrite published history reachable from the existing
    `market-data-client-v0.7.0` tag. The repository allows all three merge methods, so nothing but this
    instruction prevents the wrong one. Do NOT pass a branch-delete flag.

    (c) Refresh local refs: `git fetch origin main --tags`. Then capture `MERGE_SHA=$(git rev-parse
    origin/main)` and assert it mechanically: `git rev-list --parents -n1 origin/main` must yield exactly
    three whitespace-separated fields (the commit plus two parents), and `git log -1 --format=%s` must
    begin with `Merge pull request`. A single-parent commit means the merge was squashed or rebased:
    STOP and surface it rather than proceeding, because Task 6 tags exactly this commit and `release.yml`
    validates the version against the tagged tree. Reading the subject line is not sufficient — some UIs
    render a squash with a merge-looking subject; the parent count cannot lie.

    (d) Assert the merged tree actually carries the bump, read with the same
    `awk -F\" '/^version[[:space:]]*=/{print $2; exit}'` expression `release.yml` uses — never a TOML
    parser, never `importlib.metadata`, never a bespoke regex, because any other reader can disagree with
    the gate that decides whether the release publishes:
    `git show origin/main:packages/market-data-client/pyproject.toml` must report `0.7.1`. If it does
    not, the tag would be rejected by the pipeline's version-match gate — STOP.

    Also assert the merged tree still reads, for each of `iol-client`, `higyrus-client`, `matriz-client`,
    `ambito-financiero-client` and `wallets-client`, the SAME version their `pyproject.toml` carried on
    `$PREMAIN` — re-derive each with `git show "$PREMAIN":…` rather than hardcoding a literal, so no
    unchanged package can be accidentally tagged in Task 6.

    Re-assert the documentation-only claim against the merged tree: the diff of
    `packages/market-data-client/src` between tag `market-data-client-v0.7.0` and `$MERGE_SHA` must list
    `__init__.py` and nothing else.

    (e) Assert `release.yml` was not touched by the merge:
    `git diff --name-only "$PREMAIN".."$MERGE_SHA" -- .github/workflows/release.yml` must be empty. Note
    that `ci.yml` legitimately DOES appear in that range because of Phase 45's pre-existing allowlist
    commit — scope the assertion to `release.yml` alone, not to the whole `.github/workflows/` directory.

    (f) Do NOT create or push any tag here. Do NOT push to `main` directly; the merge goes through the PR
    so attribution, PR closure and the merge-commit shape all match every prior release. Never echo the
    `gh` token, the SSH key or any credential.

    Record `MERGE_SHA` and both parent SHAs in the SUMMARY — Task 6 recomputes `MERGE_SHA` from
    `git rev-parse origin/main` rather than trusting a literal, but the recorded value is the cross-check.
  </action>
  <verify>
    <automated>bash -c 'set -e; cd "$(git rev-parse --show-toplevel)"; B=$(git rev-parse --abbrev-ref HEAD); PREMAIN=$(git rev-parse origin/main); git fetch origin main --tags --quiet; MERGE_SHA=$(git rev-parse origin/main); test "$(git rev-list --parents -n1 "$MERGE_SHA" | wc -w | tr -d " ")" -eq 3 || { echo "NOT A TWO-PARENT MERGE COMMIT — squash or rebase was used"; exit 1; }; git log -1 --format=%s "$MERGE_SHA" | grep -q "^Merge pull request"; MDV=$(git show "$MERGE_SHA":packages/market-data-client/pyproject.toml | awk -F"\"" "/^version[[:space:]]*=/{print \$2; exit}"); test "$MDV" = "0.7.1" || { echo "MERGED TREE VERSION IS $MDV, EXPECTED 0.7.1"; exit 1; }; for P in iol-client higyrus-client matriz-client ambito-financiero-client wallets-client; do NEW=$(git show "$MERGE_SHA":packages/$P/pyproject.toml | awk -F"\"" "/^version[[:space:]]*=/{print \$2; exit}"); OLDV=$(git show "$PREMAIN":packages/$P/pyproject.toml | awk -F"\"" "/^version[[:space:]]*=/{print \$2; exit}"); test "$NEW" = "$OLDV" || { echo "UNCHANGED PACKAGE MOVED: $P $OLDV -> $NEW"; exit 1; }; done; OTHER=$(git diff --name-only market-data-client-v0.7.0.."$MERGE_SHA" -- packages/market-data-client/src | grep -vx "packages/market-data-client/src/market_data_client/__init__.py" | wc -l | tr -d " "); test "$OTHER" = "0" || { echo "MERGED TREE IS NOT DOCS-ONLY: $OTHER other src files changed"; exit 1; }; test "$(git diff --name-only "$PREMAIN".."$MERGE_SHA" -- .github/workflows/release.yml | wc -l | tr -d " ")" = "0"; PR=$(gh pr list --state merged --base main --head "$B" --json number --jq ".[0].number"); test -n "$PR"; test "$(gh pr view "$PR" --json state --jq .state)" = "MERGED"; git ls-remote --heads origin "$B" | grep -q .; test -z "$(git tag -l "market-data-client-v0.7.1")"; test -z "$(git ls-remote --tags origin "market-data-client-v0.7.1")"; echo "merge_sha=$MERGE_SHA"; echo PASS'</automated>
  </verify>
  <acceptance_criteria>
    - `git rev-list --parents -n1 origin/main | wc -w` outputs `3` — the commit plus exactly two parents. This, not the subject line, is the proof the merge was real; a squash can render with a merge-looking subject
    - `git log -1 --format=%s origin/main` begins with `Merge pull request`
    - `git show origin/main:packages/market-data-client/pyproject.toml` parsed with `awk -F'"' '/^version[[:space:]]*=/{print $2; exit}'` outputs `0.7.1` — read with `release.yml`'s own expression, so the assertion cannot disagree with the gate that decides whether the release publishes
    - For each of the other five packages, the merged-tree version equals the version on the PRE-MERGE `origin/main`, each re-derived live rather than compared against a literal
    - `git diff --name-only market-data-client-v0.7.0..<merge-sha> -- packages/market-data-client/src` lists `__init__.py` and nothing else — the documentation-only claim re-asserted against the merged tree, not only against the local branch
    - `git diff --name-only <pre-merge-main>..<merge-sha> -- .github/workflows/release.yml | wc -l` outputs `0`. The assertion is scoped to `release.yml` alone, because `ci.yml` legitimately differs in that range due to Phase 45's pre-existing allowlist commit
    - `gh pr view <n> --json state --jq .state` is `MERGED` (not `OPEN`, not `CLOSED`)
    - `git ls-remote --heads origin <branch>` still returns a ref — the branch survived the merge; no branch-delete flag was passed
    - `git tag -l 'market-data-client-v0.7.1'` and `git ls-remote --tags origin 'market-data-client-v0.7.1'` are both empty at the end of this task
    - The command history shows `gh pr merge <n> --merge` and contains no `--squash`, no `--rebase`, no branch-delete flag and no `git push origin main`
    - `MERGE_SHA` and both parent SHAs are recorded in the SUMMARY
    - No credential, token or SSH key was echoed at any point
  </acceptance_criteria>
  <done>The PR is merged; `origin/main` points at a real merge commit with two parents whose tree reads `0.7.1` for `market-data-client` under `release.yml`'s own awk expression, leaves the other five packages at their pre-merge versions, and still shows `__init__.py` as the only changed `src/` file since the prior release tag; no tag exists yet, locally or on `origin`.</done>
</task>

<task type="checkpoint:human-action" gate="blocking-human">
  <name>Task 5: SECOND blocking go/no-go gate — before the IRREVERSIBLE tag push and the public Release</name>
  <files>none — this task modifies no file</files>
  <read_first>
    - This plan's `<gate_authoring_semantics>` block — why the task type is `human-action`.
    - This plan's `<reversibility_gates>` table — this is gate (b), independent of gate (a) in Task 3.
    - `.planning/phases/44-release-market-data-client-0-7-0/44-03-PLAN.md` lines 185-291 (Task 1) — the
      element inventory, the one-approval-covers-the-round clause and the "cannot be cleanly
      un-published" framing. Copy the BODY; the precedent's own opening tag is correct here and is
      already reproduced above.
    - The Task 4 output already in context: `MERGE_SHA`, its two parents, and the merged-tree version.
      Re-resolve `MERGE_SHA` from `git rev-parse origin/main` before presenting rather than trusting the
      recorded literal; the recorded value is the cross-check.
  </read_first>
  <acceptance_criteria>
    - The operator was shown the freshly re-resolved merge-commit SHA with its two parent SHAs, the merged-tree version read with `release.yml`'s own awk expression, and the exact tag string `market-data-client-v0.7.1` character for character
    - The operator was told the Release is public and effectively permanent, that a Release cannot be cleanly un-published nor its tag cleanly re-pointed, and that this one approval authorizes the single tag of this round
    - The operator was reminded that `market-data-client-v0.7.0` already exists on `origin` and is NOT being deleted, re-pointed or replaced — the errata ships as a NEW version, which is the only clean remedy
    - No `git tag` and no `git push` command was executed before the operator's reply, and no tag of this round exists locally or on `origin` at the moment of the reply
    - This approval is recorded SEPARATELY from the Task 3 merge approval — the two gates were not collapsed into one, and this gate was not split
    - The approval came from a literal operator response — not from `auto_advance`, not from yolo mode, not inferred from silence, and not self-issued by the agent. In particular the orchestrator auto-approve path at `execute-phase.md:1057-1061` did not fire, which is why this checkpoint is typed `human-action`
    - The operator's reply is recorded verbatim in the SUMMARY together with its timestamp
    - Execution continues to Task 6 ONLY if the reply is an explicit "approved"; any other reply halts the plan with `main` merged and nothing published
  </acceptance_criteria>
  <action>PAUSE. This is the second blocking human checkpoint, independent of the merge approval already given at Task 3. Do NOT create any tag, do NOT push anything, and do NOT trigger `release.yml` until the operator explicitly replies "approved" a second time. This gate is never auto-approvable: `auto_advance` is active in `.planning/config.json` and does not satisfy it, silence does not satisfy it, an ambiguous reply does not satisfy it, and the agent may not self-issue it. ONE approval here authorizes the single tag of this round — do not ask twice. If the operator replies "abort", stop cleanly: `main` keeps the merge commit and no public Release is created; the release can be resumed later by re-running Task 6. Before presenting, re-resolve the target live: `git fetch origin main --tags`, then `MERGE_SHA=$(git rev-parse origin/main)`. Present the freshly re-resolved merge-commit SHA with its two parents, the merged-tree version read with `release.yml`'s own awk expression, the exact tag string to be published, and the fact that a GitHub Release cannot be cleanly un-published or re-pointed.</action>
  <instructions>
    ## What has already been automated

    Task 4 merged the release PR. `origin/main` now points at a real merge commit — captured fresh with
    `git fetch origin main --tags` then `git rev-parse origin/main`, and confirmed with
    `git rev-list --parents -n1 origin/main` to list exactly TWO parent SHAs. The merged tree already
    reads `version = "0.7.1"` in `packages/market-data-client/pyproject.toml`, which is what
    `release.yml` will validate independently with its own `awk` expression against the TAGGED tree. The
    merged tree also still shows `__init__.py` as the ONLY changed file under
    `packages/market-data-client/src` since the prior release tag — the documentation-only claim, proven
    against the tree that will actually be tagged.

    The next task performs the most irreversible operation of this release: creating ONE ANNOTATED tag
    with this exact literal string —

      `market-data-client-v0.7.1`

    — on that same merge-commit SHA, and pushing it to `origin` BY NAME.

    That push fires `release.yml` (trigger `on: push: tags: ["*-client-v*"]`), which regex-validates the
    tag, checks that `packages/market-data-client` exists, asserts the tagged tree's `pyproject.toml`
    version equals the version captured from the tag, runs `uv build --package market-data-client`, and
    calls `gh release create --generate-notes` — creating a PUBLIC GitHub Release with a wheel and an
    sdist.

    Once a Release exists, its tag cannot be cleanly re-pointed: deleting the tag orphans the Release or
    forces deleting a public Release. A mislabelled tag is a permanent public artifact, and the correct
    remedy is publishing a new version — never rewriting the published one. That principle is precisely
    why this release exists: `market-data-client-v0.7.0` stays exactly where it is, untouched, and the
    documentation correction ships as a NEW version rather than as a rewrite of the old one.

    ## What is being published

    `market-data-client` **0.7.1**, a DOCUMENTATION ERRATA with zero code change. The wheel and sdist
    will be byte-equivalent in behaviour to the prior release; the only difference that matters is the
    README bundled inside their METADATA, which now documents the full surface change that shipped in
    the prior bump: `FeedSubscription`, the required `FeedIngestor.subscription`,
    `FeedIngestor.last_error_age_seconds`, `FeedIngestor.last_error_at`, the required
    `HealthFeed.symbols_never_delivered`, and `Symbol.note`.

    Consumers already on the prior version need NO code migration. The new changelog entry says so
    explicitly and points at the corrected tables in the entry below it.

    No other package is tagged or published. `market-data-client` moves from 8 published tags to 9;
    `iol-client` stays at 4, `higyrus-client` at 3, `matriz-client` at 3, `ambito-financiero-client` at 2
    and `wallets-client` at 1 — a baseline the next task re-derives live before pushing, and re-asserts
    after.

    `release.yml` has NOT been edited — the same generic workflow that published every prior release in
    this repository, and its sha256 is asserted identical at `HEAD`, `origin/main`, the prior tag and the
    new tag. This is its eighth reuse without a byte changing.

    **This single approval covers the whole tag push.** The two gates are defined by
    irreversible-operation TYPE — merge, then tag push — not one gate per artifact. You will not be asked
    again.

    After the tag is pushed and the Release exists, Task 6 downloads BOTH the prior wheel and the new one
    and compares their bundled METADATA: the prior must NOT contain `FeedSubscription` or
    `symbols_never_delivered`, and the new one MUST. That differential is what proves the errata was both
    warranted and actually delivered. That step is read-only and reversible — it proves the artifact, it
    does not change it.

    ## What you need to do

    1. Confirm `git rev-parse origin/main` resolves, and that `git log -1 --format='%H %p %s' origin/main`
       shows TWO parent SHAs and a `Merge pull request #<n> …` subject.
    2. Confirm the merged tree version: `git show origin/main:packages/market-data-client/pyproject.toml`
       reports `0.7.1`. If it does not, the tag will be rejected by the pipeline's version-match gate.
    3. Confirm the tag string to be published is EXACTLY `market-data-client-v0.7.1` — character for
       character, correct package prefix, no trailing whitespace. Note that `market-data-client-v0.7.0`
       already exists on `origin`; reusing it would be rejected outright and `release.yml` would never
       fire, and it is not to be deleted or re-pointed under any circumstances.
    4. Confirm publishing NOW is intended: this is a documentation errata, no code changed, and its whole
       purpose is to get the corrected README into a consumable artifact.
    5. Understand that this creates a PUBLIC, effectively permanent GitHub Release, and that one
       "approved" here authorizes the tag push.
    6. Confirm you authorize the irreversible tag push NOW.
  </instructions>
  <verification>After your reply, the agent verifies mechanically that nothing irreversible ran before it: `origin/main` is still the two-parent merge commit reading `0.7.1`, and `market-data-client-v0.7.1` exists neither locally nor on `origin`.</verification>
  <resume-signal>Type "approved" to proceed with creating and pushing the annotated `market-data-client-v0.7.1` tag, or "abort" (optionally describing blockers) to stop with `main` merged but nothing published. Anything other than an explicit "approved" means do not push any tag.</resume-signal>
  <verify>
    <automated>bash -c 'set -e; cd "$(git rev-parse --show-toplevel)"; git fetch origin main --tags --quiet; test "$(git rev-list --parents -n1 origin/main | wc -w | tr -d " ")" -eq 3; MDV=$(git show origin/main:packages/market-data-client/pyproject.toml | awk -F"\"" "/^version[[:space:]]*=/{print \$2; exit}"); test "$MDV" = "0.7.1"; test -z "$(git tag -l "market-data-client-v0.7.1")" || { echo "TAG CREATED BEFORE THE GATE"; exit 1; }; test -z "$(git ls-remote --tags origin "market-data-client-v0.7.1")" || { echo "TAG PUSHED BEFORE THE GATE"; exit 1; }; git ls-remote --tags origin "market-data-client-v0.7.0" | grep -q . || { echo "PRIOR RELEASE TAG MISSING — it must not be deleted"; exit 1; }; echo "PASS — merge intact, prior tag intact, no new tag created or pushed before the operator reply"'</automated>
  </verify>
  <done>The operator was shown the freshly re-resolved merge SHA with its two parents, the merged-tree version, the exact tag string and the permanence warning; they replied with an explicit literal "approved" (or "abort"); the reply is recorded verbatim with its timestamp as a SECOND approval distinct from the merge gate and with an explicit statement that it was not auto-issued; and at the moment of the reply no tag of this round existed locally or on `origin` while the prior release tag was still intact.</done>
</task>

<task type="auto">
  <name>Task 6: Tag the re-resolved merge commit, push the single tag by name, watch `release.yml`, verify wheel + sdist, and prove the errata reached consumers by installing the PUBLIC wheel and diffing its bundled METADATA against the prior release</name>
  <files>(git/gh operations plus a throwaway scratch directory outside the repository — no repo file modified)</files>
  <read_first>
    - `.github/workflows/release.yml` — READ-ONLY, DO NOT EDIT. The trigger
      (`on: push: tags: ["*-client-v*"]`, `:3-6`), the tag regex, the package-directory check, the awk
      version-match gate (`:47`) that reads `pyproject.toml` ONLY, the
      `uv build --package <pkg> --out-dir dist` step (`:60`), the `gh release create --generate-notes`
      step (`:67`), and `concurrency: group: release-${{ github.ref }}` with `cancel-in-progress: false`.
    - `.planning/phases/44-release-market-data-client-0-7-0/44-03-PLAN.md` Tasks 2 and 3 — the annotated
      tag on the re-resolved SHA pushed by name, the tag-count invariance loop, the sha256
      digest-identity form for workflow immutability, and the throwaway-venv shape with its two
      load-bearing constraints (`--python 3.12` is not cosmetic; never install by bare name).
    - `packages/market-data-client/pyproject.toml` line 5 — `readme = "README.md"`, which is why the
      corrected README travels inside the wheel's own METADATA and why the METADATA differential is the
      definitive proof for this particular release.
    - `packages/market-data-client/README.md` lines 9-11 — the already-documented slopsquat risk: this
      package is not on PyPI, and a bare `uv add market-data-client` would resolve something else.
    - This plan's `<measured_state>` table — the six tag counts to re-derive live before pushing.
  </read_first>
  <action>
    Execute ONLY after Task 5 returned an explicit "approved" from the operator. If it returned anything
    else — including silence, ambiguity, or an auto-advance signal — stop with no tag created.

    (a) Re-derive the tag baseline BEFORE anything else, so the post-push invariance assertion is made
    against a live-confirmed baseline rather than a stale literal. Count `git tag -l '<pkg>-v*'` for each
    of `iol-client`, `higyrus-client`, `matriz-client`, `ambito-financiero-client`, `wallets-client` and
    `market-data-client`. They must read 4, 3, 3, 2, 1 and 8 respectively. If ANY disagrees, STOP and
    surface it before pushing: a disagreement means either the record is stale (Phase 40 found exactly
    that — a `wallets-client` count assumed at 2 when the real value was 1) or something published a tag
    during this task. Record all six live values in the SUMMARY.

    (b) Re-resolve the tag anchor rather than trusting any literal SHA: `git fetch origin main --tags`,
    then `MERGE_SHA=$(git rev-parse origin/main)`. Cross-check it against the value Task 4 recorded and
    surface any mismatch before continuing. Re-assert BEFORE tagging that
    `git rev-list --parents -n1 "$MERGE_SHA"` yields three whitespace-separated fields and that
    `git show "$MERGE_SHA":packages/market-data-client/pyproject.toml` reads `0.7.1` under `release.yml`'s
    own awk expression. If either fails, STOP — do not tag.

    (c) Create the tag as an ANNOTATED tag on that SHA explicitly:
    `git tag -a market-data-client-v0.7.1 "$MERGE_SHA" -m "<message>"`. Never run `git tag` with the tag
    string alone and no commit-ish argument — that tags branch HEAD, and `release.yml`'s version check
    runs against the TAGGED tree, so a tag on the branch tip would produce a Release pointing at a commit
    outside `main`'s history.

    Message shape, following the prior releases in this repository:
    `market-data-client v0.7.1 — errata documental: changelog 0.7.0 completo en el artefacto publicado (PUB-01)`.

    (d) Push the tag BY NAME: `git push origin market-data-client-v0.7.1`. This is the irreversible act.
    Never push a bare `--tags`: milestone tags and package tags exist locally and a wholesale push would
    publish whatever is stale. Never use a force flag. If the push is rejected, STOP and surface it; do
    not delete or re-point any existing tag to make room.

    (e) Watch the pipeline: `gh run list --workflow=release.yml --limit 5`, then `gh run watch <run-id>`
    until it completes. It must reach `success`. Record the run ID. Do NOT edit, re-create or re-run
    `release.yml`; if the run fails, surface the exact failing step rather than patching the workflow or
    deleting the tag.

    (f) Verify the published artifacts with exact filenames:
    `gh release view market-data-client-v0.7.1 --json assets --jq '.assets[].name'` must list BOTH
    `market_data_client-0.7.1-py3-none-any.whl` and `market_data_client-0.7.1.tar.gz`. Also verify the
    tag's anchor and annotation: `git rev-list -n1 market-data-client-v0.7.1` must equal `$MERGE_SHA`,
    `git cat-file -t market-data-client-v0.7.1` must print `tag` (annotated, not lightweight), and
    `git ls-remote --tags origin market-data-client-v0.7.1` must return a ref.

    (g) Assert `release.yml` was never edited, using the sha256 digest-identity form and NOT Phase 34's
    `git diff --name-only <prior-release-tag>..HEAD -- .github/workflows` form, which is
    stale-by-construction (`ci.yml` legitimately differs across refs, and on this branch it demonstrably
    does) and failed three times during that phase. Take the sha256 of `.github/workflows/release.yml` at
    `origin/main`, at `market-data-client-v0.7.0` and at `market-data-client-v0.7.1`; `sort -u` over those
    digests must yield exactly one line. That closes the eighth-reuse-without-an-edit claim.

    (h) Assert the negative: re-count `git tag -l '<pkg>-v*'` for all six packages. The five others must
    be IDENTICAL to the values captured in step (a), and `market-data-client` must be exactly one higher
    (9). Do the same against the remote with `git ls-remote --tags origin '<pkg>-v*'` so a local-only
    discrepancy cannot hide.

    (i) POST-PUBLISH PROOF — the part that makes this release meaningful. Create a throwaway working
    directory OUTSIDE the repository (`WORK=$(mktemp -d)`) and build a fresh interpreter there with
    `uv venv --python 3.12`. The `--python 3.12` flag is load-bearing, not cosmetic: the system `python3`
    on this machine is 3.9.6 and the package requires `>=3.12`, so omitting it produces a resolution
    failure that is easy to misread as a packaging defect. Do not run any part of this from inside the
    repository checkout, and do not add the workspace to the venv.

    Install from the FULL public Release asset URL:
    `https://github.com/gravity-quant/market-libs/releases/download/market-data-client-v0.7.1/market_data_client-0.7.1-py3-none-any.whl`.
    NEVER install by bare package name — this package is not on PyPI and a bare `uv add market-data-client`
    would resolve a different project entirely. The repository is public, so this URL resolves
    unauthenticated; if the download ever fails, fall back to `gh release download market-data-client-v0.7.1`
    rather than to a name-based install.

    Then assert, all in ONE Python invocation inside the venv so a single non-zero exit fails the task:
      - three-way version identity: `market_data_client.__version__`,
        `importlib.metadata.version("market-data-client")` and the literal `0.7.1` all agree. That proves
        the wheel's metadata and its code shipped in sync — `release.yml` only ever validated
        `pyproject.toml`;
      - THE ERRATA PAYLOAD: `importlib.metadata.distribution("market-data-client").read_text("METADATA")`
        contains `FeedSubscription`, `FeedIngestor`, `HealthFeed`, `symbols_never_delivered` and the new
        changelog heading. This is the corrected README travelling inside the published artifact, which is
        the entire reason this release exists;
      - THE DIFFERENTIAL: download the PRIOR release wheel with
        `gh release download market-data-client-v0.7.0 --pattern "*.whl" --dir "$WORK/old"`, read its
        `*.dist-info/METADATA` member with `zipfile`, and assert it contains NEITHER `FeedSubscription`
        NOR `symbols_never_delivered`. Together with the previous bullet this proves the omission was real
        and is now fixed in a consumable artifact. Do NOT use `HealthFeed` as a differential token: it
        legitimately occurs in the prior README outside the changelog;
      - NO CODE REGRESSION: `from market_data_client import Instrument, Segment, FeedSubscription,
        FeedIngestor, HealthFeed` succeeds and `"FeedSubscription" in market_data_client.__all__`;
        `Segment.from_api({"segment": "DDA", "live_instruments": 3})` yields `("DDA", 3)` and is truthy
        while `Segment.empty()` is falsy; `Instrument.from_api({"symbol": "X", "market_id": "ROFX"})`
        yields `market_id == marketId == "ROFX"`; `FeedSubscription.from_api(None)` constructs. All of
        this runs through `from_api`, so it needs no network and no credentials;
      - NEGATIVE: none of `iol_client`, `higyrus_client`, `matriz_client`, `ambito_financiero_client`,
        `wallets_client` is importable in the venv.
    Print a success line so the SUMMARY can quote real output rather than a claim.

    (j) Close the gate-authorship audit one final time over this plan file: the count of gate attributes
    set to the bare non-`-human` value must be exactly `0`, and the LINE-ANCHORED count of `human-action`
    checkpoint opening tags carrying the human-suffixed gate value must be exactly `2`. This ran once
    already in Task 2 before the merge; re-running it here records the close-out value.

    (k) Remove the throwaway directory when done, and record in the SUMMARY: the exact URL installed, the
    resolved Python version inside the venv, the asserted version values, the literal script output, both
    METADATA differential results and both audit counts. Never echo a token or credential.
  </action>
  <verify>
    <automated>bash -c 'set -e; REPO=$(git rev-parse --show-toplevel); cd "$REPO"; T=market-data-client-v0.7.1; PREV=market-data-client-v0.7.0; git fetch origin main --tags --quiet; MERGE_SHA=$(git rev-parse origin/main); test "$(git rev-list --parents -n1 "$MERGE_SHA" | wc -w | tr -d " ")" -eq 3; git tag | grep -qx "$T"; test "$(git cat-file -t "$T")" = "tag"; git ls-remote --tags origin "$T" | grep -q .; test "$(git rev-list -n1 "$T")" = "$MERGE_SHA"; gh release view "$T" --json assets --jq ".assets[].name" | grep -qx "market_data_client-0.7.1-py3-none-any.whl"; gh release view "$T" --json assets --jq ".assets[].name" | grep -qx "market_data_client-0.7.1.tar.gz"; test "$(for X in origin/main "$PREV" "$T"; do git show "$X:.github/workflows/release.yml" | shasum -a 256 | cut -d" " -f1; done | sort -u | wc -l | tr -d " ")" = "1"; EXP="iol-client:4 higyrus-client:3 matriz-client:3 ambito-financiero-client:2 wallets-client:1 market-data-client:9"; for E in $EXP; do P="${E%%:*}"; N="${E##*:}"; L=$(git tag -l "${P}-v*" | wc -l | tr -d " "); R=$(git ls-remote --tags origin "${P}-v*" | grep -v "\^{}\$" | wc -l | tr -d " "); test "$L" = "$N" || { echo "LOCAL TAG COUNT DRIFT: $P local=$L expected=$N"; exit 1; }; test "$R" = "$N" || { echo "REMOTE TAG COUNT DRIFT: $P remote=$R expected=$N"; exit 1; }; done; RUN=$(gh run list --workflow=release.yml --limit 5 --json databaseId,headBranch,conclusion --jq "[.[] | select(.headBranch==\"$T\")] | .[0]"); test -n "$RUN"; test "$(printf "%s" "$RUN" | jq -r .conclusion)" = "success"; PLAN=".planning/quick/260901-par-cut-market-data-client-v0-7-1-as-a-docs-/260901-par-PLAN.md"; BAD=$(grep -oE "gate=\"blocking\"" "$PLAN" | wc -l | tr -d " "); test "$BAD" = "0" || { echo "GATE AUTHORSHIP DEFECT: $BAD bare gate attributes"; exit 1; }; GOOD=$(grep -cE "^<task type=\"checkpoint:human-action\" gate=\"blocking-human\">\$" "$PLAN"); test "$GOOD" = "2" || { echo "EXPECTED EXACTLY 2 BLOCKING-HUMAN CHECKPOINT TAGS, FOUND: $GOOD"; exit 1; }; WORK=$(mktemp -d); gh release download "$PREV" --pattern "*.whl" --dir "$WORK/old" --repo gravity-quant/market-libs; cd "$WORK"; uv venv --python 3.12; uv pip install "https://github.com/gravity-quant/market-libs/releases/download/market-data-client-v0.7.1/market_data_client-0.7.1-py3-none-any.whl"; OLDDIR="$WORK/old" ./.venv/bin/python -c "
import glob, os, zipfile
import market_data_client as m
from importlib.metadata import version, distribution
assert m.__version__ == version(\"market-data-client\") == \"0.7.1\", m.__version__
raw = distribution(\"market-data-client\").read_text(\"METADATA\") or \"\"
for tok in (\"FeedSubscription\", \"FeedIngestor\", \"HealthFeed\", \"symbols_never_delivered\", \"### v0.7.1\"):
    assert tok in raw, \"MISSING FROM PUBLISHED 0.7.1 METADATA: \" + tok
old = glob.glob(os.path.join(os.environ[\"OLDDIR\"], \"*.whl\"))
assert len(old) == 1, old
z = zipfile.ZipFile(old[0])
name = [n for n in z.namelist() if n.endswith(\".dist-info/METADATA\")][0]
prior = z.read(name).decode(\"utf-8\")
for tok in (\"FeedSubscription\", \"symbols_never_delivered\"):
    assert tok not in prior, \"PRIOR WHEEL ALREADY HAD IT — ERRATA UNWARRANTED: \" + tok
from market_data_client import Instrument, Segment, FeedSubscription, FeedIngestor, HealthFeed
assert \"FeedSubscription\" in m.__all__
s = Segment.from_api({\"segment\": \"DDA\", \"live_instruments\": 3})
assert (s.segment, s.live_instruments) == (\"DDA\", 3), s
assert bool(s) is True
assert not bool(Segment.empty())
i = Instrument.from_api({\"symbol\": \"X\", \"market_id\": \"ROFX\"})
assert i.market_id == \"ROFX\" and i.marketId == \"ROFX\", i
assert FeedSubscription.from_api(None) is not None
for absent in (\"iol_client\", \"higyrus_client\", \"matriz_client\", \"ambito_financiero_client\", \"wallets_client\"):
    try:
        __import__(absent)
    except ModuleNotFoundError:
        continue
    raise AssertionError(\"UNRELATED PACKAGE INSTALLED: \" + absent)
print(\"POST-PUBLISH 0.7.1 PASS — errata present in published METADATA, absent from prior wheel, no code regression\")
"; ./.venv/bin/python -c "import sys; assert sys.version_info[:2] == (3, 12), sys.version"; cd /; rm -rf "$WORK"; echo PASS'</automated>
  </verify>
  <acceptance_criteria>
    - The six live tag counts were re-derived BEFORE the push and read `iol-client` 4, `higyrus-client` 3, `matriz-client` 3, `ambito-financiero-client` 2, `wallets-client` 1, `market-data-client` 8; all six are recorded in the SUMMARY. No literal was trusted without live confirmation
    - `MERGE_SHA` was re-resolved live with `git rev-parse origin/main` after `git fetch origin main --tags`, cross-checked against the value Task 4 recorded, and no SHA literal from any document was used as the tag anchor
    - `git rev-list --parents -n1 "$MERGE_SHA" | wc -w` is `3` and the tagged tree reads `0.7.1` under `release.yml`'s own awk expression, both asserted BEFORE the tag was created
    - `git tag -l 'market-data-client-v0.7.1'` returns it, `git cat-file -t` reports `tag` (annotated, not lightweight), `git ls-remote --tags origin` returns a ref, and `git rev-list -n1` equals `$MERGE_SHA` — the tag sits on the merge commit, not on branch HEAD
    - `gh release view market-data-client-v0.7.1 --json assets --jq '.assets[].name'` lists BOTH `market_data_client-0.7.1-py3-none-any.whl` and `market_data_client-0.7.1.tar.gz`, checked by exact filename
    - The `release.yml` run triggered by this tag was watched to completion with `gh run watch` and its conclusion is `success`; the run ID is recorded in the SUMMARY
    - The sha256 of `.github/workflows/release.yml` is identical at `origin/main`, `market-data-client-v0.7.0` and `market-data-client-v0.7.1` — `sort -u` yields exactly one line. Phase 34's `git diff --name-only <prior-release-tag>..HEAD -- .github/workflows` form was NOT used, because `ci.yml` demonstrably differs across these refs
    - Post-push tag counts, asserted BOTH locally and against `origin`: `iol-client` 4, `higyrus-client` 3, `matriz-client` 3, `ambito-financiero-client` 2, `wallets-client` 1 — identical to the step-(a) baseline — and `market-data-client` exactly 9, one higher
    - A throwaway venv was created OUTSIDE the repository with `uv venv --python 3.12`; `sys.version_info[:2]` inside it is `(3, 12)`; the package was installed from its FULL public Release asset URL, NOT by bare name, and the workspace was not added to the venv
    - Inside the venv, `market_data_client.__version__`, `importlib.metadata.version("market-data-client")` and the literal `0.7.1` all agree
    - `importlib.metadata.distribution("market-data-client").read_text("METADATA")` contains `FeedSubscription`, `FeedIngestor`, `HealthFeed`, `symbols_never_delivered` and `### v0.7.1` — the corrected README shipped INSIDE the published artifact, which is the entire purpose of this release
    - The prior release wheel, downloaded with `gh release download market-data-client-v0.7.0 --pattern '*.whl'` and read via `zipfile` from its `*.dist-info/METADATA` member, contains NEITHER `FeedSubscription` NOR `symbols_never_delivered` — the differential proving the omission was real. `HealthFeed` was deliberately NOT used as a differential token because it legitimately occurs in the prior README
    - `from market_data_client import Instrument, Segment, FeedSubscription, FeedIngestor, HealthFeed` succeeds against the INSTALLED distribution, `"FeedSubscription" in __all__`, `Segment.from_api({"segment": "DDA", "live_instruments": 3})` yields `("DDA", 3)` and is truthy, `Segment.empty()` is falsy, and `Instrument.from_api({"symbol": "X", "market_id": "ROFX"})` yields `market_id == marketId == "ROFX"` — no behaviour regressed in a release that was supposed to change no code
    - None of `iol_client`, `higyrus_client`, `matriz_client`, `ambito_financiero_client` or `wallets_client` is importable in the venv
    - Over this plan file, the count of gate attributes set to the bare non-`-human` value is exactly `0` and the LINE-ANCHORED count of `human-action` checkpoint opening tags carrying the human-suffixed gate value is exactly `2` — matching the value Task 2 recorded before the merge
    - The command history shows exactly one `git push origin market-data-client-v0.7.1` by name, with no `--force` and no bare `git push --tags` anywhere; no existing tag or Release was deleted or re-pointed; no file under `.github/workflows/` was edited; no credential was echoed
    - The throwaway directory was removed and no repository file was modified by this task
  </acceptance_criteria>
  <done>An annotated `market-data-client-v0.7.1` tag exists on `origin`, anchored on the live-re-resolved two-parent merge commit; the `release.yml` run concluded green; the public Release carries both the wheel and the sdist under their exact expected filenames; the published wheel installs from its public URL into a fresh Python 3.12 interpreter outside the repository and its own bundled METADATA carries the corrected changelog that the prior release wheel provably lacks; no behaviour regressed; the other five packages' tag counts are unchanged both locally and on `origin`; and the gate-authorship audit returns zero bare gate attributes and exactly two human-action blocking-human checkpoint tags.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| release branch → public `main` | The merge publishes the whole pending v1.8 diff — not only the errata — to the default branch of a PUBLIC repository. Irreversible in practice. |
| CI check results → merge decision | `main` has no branch protection, so GitHub applies no gate of its own; the check status only influences the merge if the agent enforces it. |
| local tag → public GitHub Release | Pushing the tag fires `release.yml` and creates a PUBLIC, effectively permanent Release whose tag cannot be cleanly re-pointed. |
| GSD auto-mode → the human checkpoints | `auto_advance` is active. Two independent layers (executor and orchestrator) can auto-satisfy a checkpoint; only `human-action` stops at both. |
| `README.md` → published wheel METADATA | `readme = "README.md"` makes hatchling embed the README as the distribution long description; a README defect is a SHIPPED defect, which is why this release exists at all. |
| agent → `gh` OAuth token / SSH key | Ambient credentials; any echo lands in transcripts and possibly in a public PR body. |
| merge strategy → cross-referenced SHAs | Phases 35-45 SUMMARYs cite commit SHAs by value; squash or rebase orphans them. |
| local tag namespace → `origin` | Milestone tags and package tags exist locally. `git push --tags` would publish whatever is stale. |
| package name → PyPI | This package is not on PyPI. A bare-name install would resolve a different project if the name ever appears there. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-QP-01 | Elevation of Privilege / Repudiation | the two irreversible operations, and the gates authorizing them being auto-satisfied | mitigate | Tasks 3 and 5 are blocking `checkpoint:human-action` tasks with the human-suffixed gate attribute in an `autonomous: false` plan — the only construct that stops at BOTH the executor (`gsd-executor.md:314-318`) and the orchestrator (`execute-phase.md:1057-1061`) under `auto_advance`, and the only one exempt from `human_verify_mode: end-of-phase` suppression. Tasks 4 and 6 execute only on an explicit literal "approved", recorded verbatim with a timestamp. Task 2 (e) audits the authorship IN THIS FILE before anything irreversible runs; Task 6 (j) re-audits at close-out. ASVS L1 V4. |
| T-QP-02 | Tampering | merging red, pending, cancelled or zero-check code into an unprotected public `main` | mitigate | Task 2 (d) asserts the gate by COUNT — 15 total rows, 15 with status `pass`, 2 market-data matrix rows — instead of an absence-of-failure check, which passes on pending, cancelled and empty output. `cancel-in-progress: true` (`ci.yml:20`) makes `cancelled` genuinely reachable and `paths-ignore: ["**.md", ".gitignore"]` makes a zero-check run reachable — an acute hazard for a release whose payload is Markdown. The branch head is re-asserted equal to `origin/<branch>` after the count. ASVS L1 V4. |
| T-QP-03 | Tampering / Repudiation | merge strategy — squash or rebase would rewrite history | mitigate | Task 4 (b) mandates `gh pr merge <n> --merge` and forbids `--squash` / `--rebase`; the acceptance criteria assert the resulting commit has exactly two parents rather than trusting the subject line. Preserves every SHA the Phase 35-45 SUMMARYs cite. |
| T-QP-04 | Tampering | a code change smuggled into a release declared documentation-only, shipping untested behaviour under an errata label | mitigate | Task 1 and Task 4 both assert that the diff of `packages/market-data-client/src` against the prior release tag lists `__init__.py` and nothing else, with exactly two changed lines. The claim is proven against the branch AND against the merged tree that actually gets tagged. Task 6 (i) additionally exercises the installed distribution for behaviour regression. |
| T-QP-05 | Tampering | tag placed on branch HEAD instead of the merge commit, or on a tree that fails the version-match gate | mitigate | Task 6 (b) re-resolves `MERGE_SHA` live after a fetch, cross-checks it against Task 4's recorded value, re-asserts the two-parent shape and the merged-tree version before tagging, and passes the SHA explicitly to `git tag -a`. Acceptance criteria assert `git rev-list -n1 <tag>` equals `$MERGE_SHA` and `git cat-file -t` reports `tag`. |
| T-QP-06 | Information Disclosure | `git push --tags` publishing stale local tags, or an unrelated package being tagged or bumped | mitigate | The tag is pushed BY NAME in a single command; a bare `--tags` is an explicit prohibition. Task 1 asserts the other five packages' versions are unchanged versus `origin/main`; Task 4 re-asserts against the pre-merge `origin/main`; Task 6 (a) re-derives all six tag counts live before the push and (h) re-asserts them after, both locally and against `origin`. |
| T-QP-07 | Tampering | patching or re-running `release.yml` / `ci.yml` to work around a failure, or deleting a tag to retry | mitigate | `.github/workflows/` is read-only for this task; Task 6 (g) proves `release.yml` immutability by sha256 identity across `origin/main`, the prior tag and the new tag. Deleting or re-pointing a tag or a Release is an explicit prohibition — this release IS the clean remedy pattern, publishing a new version rather than rewriting `market-data-client-v0.7.0`. Phase 34's broken tag-baseline assertion form is deliberately not reused, and would be actively wrong here because `ci.yml` legitimately differs across these refs. ASVS L1 V14. |
| T-QP-08 | Spoofing / Supply Chain | a slopsquatted package resolving instead of ours during the post-publish install | mitigate | Task 6 (i) installs from the FULL public Release asset URL only; a bare package name is an explicit prohibition, a risk `packages/market-data-client/README.md` already documents. The prior wheel used for the differential is fetched with `gh release download` against this repository by tag, not by name resolution. |
| T-QP-09 | Repudiation | declaring the errata delivered from a green pipeline alone, when the whole failure mode being corrected is "the pipeline was green and the artifact was still wrong" | mitigate | Task 6 (i) asserts the corrected content INSIDE the published wheel's own METADATA and diffs it against the prior wheel's METADATA. The prior release passed every pipeline gate and still shipped an incomplete README; only an artifact-level assertion can detect that class of defect. |
| T-QP-10 | Information Disclosure | `gh` OAuth token / SSH key in agent output, or a credential in the PR body, tag message or Release notes | mitigate | `gh auth status` is used instead of ever echoing the token; a credential scan runs over the full `origin/main...HEAD` diff before the push; the tag message carries only package, version and headline; the Release uses `--generate-notes`; the post-publish download is an unauthenticated public URL. ASVS L1 V7. |
| T-QP-SC | Tampering | npm/pip/cargo installs | mitigate | The only install-shaped operations are `uv sync --frozen` against the existing committed `uv.lock` (no dependency added, `uv.lock` churn asserted at `1 1`) and Task 6's install of THIS repository's own wheel from its public GitHub Release asset URL — an artifact `release.yml` built with `uv build --package market-data-client` on the tagged tree in the same run. No new third-party package is introduced by this task, so no Package Legitimacy audit table is required and no legitimacy checkpoint applies; the full-URL rule is the standing guard rail. |
</threat_model>

<verification>
1. All four version sites read `0.7.1`, with BOTH occurrences on the wheel install line updated and zero occurrences of the prior version above the `## Changelog` heading.
2. `### v0.7.1` is the first changelog entry and `### v0.7.0` the second; the new entry states documentation-only, names the omitted surface, cites `6f202ac` and states migration is empty.
3. The `src/` diff against the prior release tag is `__init__.py` only, two lines — asserted on the branch AND on the merged tree.
4. `uv.lock` was refreshed exactly once, in one commit, with `1 1` churn; `uv lock --check` exits 0.
5. Every mirrored CI gate is green locally; the PR reports 15 rows, 15 `pass`, 2 market-data matrix rows, asserted by positive count.
6. Over this plan file, bare gate attributes count `0` and line-anchored `human-action` blocking-human checkpoint tags count `2` — asserted before the merge and again at close-out.
7. The operator explicitly replied "approved" before the merge, and a SECOND, separately recorded "approved" before the tag push; neither was auto-issued.
8. `git rev-list --parents -n1 origin/main | wc -w` equals 3; the merged tree reads `0.7.1` under `release.yml`'s own awk expression.
9. `market-data-client-v0.7.1` is annotated, sits on the re-resolved `MERGE_SHA`, reached `origin`, and was pushed by name — no bare `git push --tags` anywhere.
10. The `release.yml` run was watched to `success`; the public Release lists both `market_data_client-0.7.1-py3-none-any.whl` and `market_data_client-0.7.1.tar.gz`.
11. `release.yml`'s sha256 is identical at `origin/main`, `market-data-client-v0.7.0` and `market-data-client-v0.7.1`.
12. Tag counts, locally and on `origin`: iol 4, higyrus 3, matriz 3, ambito 2, wallets 1, market-data 9.
13. The published wheel installs from its public URL into a fresh Python 3.12 venv outside the repository; its bundled METADATA carries `FeedSubscription` and `symbols_never_delivered` while the prior release wheel's METADATA carries neither; the `Instrument` / `Segment` / `FeedSubscription` chain runs green against the installed distribution.
</verification>

<success_criteria>
- The errata actually reached consumers: the corrected changelog is inside the published wheel's own METADATA, proven by a differential against the wheel it corrects — not inferred from a green pipeline, which is the exact signal that failed last time.
- The release is provably documentation-only: one changed file under `src/`, two changed lines, asserted against both the branch and the merged tree.
- Neither irreversible operation ran without an explicit, literal human "approved", and the two approvals were independent and separately recorded — structurally impossible for `auto_advance` or yolo mode to manufacture, because both checkpoint types stop at both auto-approval layers.
- The operator was told plainly, at the first gate, that the merge publishes all pending v1.8 work and not only the errata, and authorized that specific thing.
- `market-data-client-v0.7.0` was never deleted or re-pointed — the correction shipped as a new version, which is the only clean remedy for a published artifact.
- `main` carries a real two-parent merge commit; the tag is annotated and anchored on it; `release.yml` was reused for the eighth time without a byte changing; and no other package moved.
</success_criteria>

<output>
Create `.planning/quick/260901-par-cut-market-data-client-v0-7-1-as-a-docs-/260901-par-SUMMARY.md` when done.

Record in the SUMMARY: the four version transitions with the five textual substitution sites; the
`src/` docs-only diff proof (file list and changed-line count) taken on the branch and again on the
merged tree; the `uv.lock` commit count and numstat churn; the local CI mirror results; the PR number,
URL and title with the literal counted check totals; the gate-authorship audit counts with the exact
commands, at Task 2 and again at Task 6; the operator's approval text and timestamp for EACH of the two
gates recorded verbatim and separately, each with an explicit statement that it was not auto-issued and
that the orchestrator auto-approve path did not fire; the captured `MERGE_SHA` with its two parent SHAs
and whether the Task 6 re-resolution matched it; the tag string with its annotation type, anchor SHA and
message; the `release.yml` run ID and conclusion; the Release's verified asset filenames; the
`release.yml` sha256 and the refs it was compared across; the six pre-push and six post-push tag counts,
local and remote; the exact wheel URL installed, the resolved venv Python version, both asserted version
values, the literal deep-chain output, and the two METADATA differential results (tokens present in
0.7.1, tokens absent from 0.7.0).
</output>
