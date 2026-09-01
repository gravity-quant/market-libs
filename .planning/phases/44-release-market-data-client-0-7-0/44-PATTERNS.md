# Phase 44: Release `market-data-client` 0.7.0 - Pattern Map

**Mapped:** 2026-09-01
**Files analyzed:** 8 (3 plan files to author + 5 repo files to edit)
**Analogs found:** 8 / 8 (all exact — this is the fourth run of a repeated release procedure)

> **READ THIS FIRST.** Every analog in this document is a precedent *release plan*, and three of the
> four precedent checkpoint tasks carry a **defect that must not be copied**: `gate="blocking"`
> without `-human`. See § Shared Patterns → "Checkpoint gate authoring (ANTI-PATTERN + correction)".
> Copy the *shape* of those tasks; never copy the `type=`/`gate=` attribute pair verbatim.

---

## File Classification

### Plan files this phase authors

| New file | Role | Data flow | Closest analog | Match quality |
|---|---|---|---|---|
| `44-01-PLAN.md` | plan (autonomous prep) | batch / file-I/O | `40-01-PLAN.md` Tasks 3-4 | exact (same package, same 2 of 4 version sites) |
| `44-02-PLAN.md` | plan (gate a + merge) | request-response (gh/git) | `40-02-PLAN.md` (whole file) | exact — 1:1 task-for-task |
| `44-03-PLAN.md` | plan (gate b + tag + publish) | event-driven (tag → workflow) | `40-03-PLAN.md` (whole file) | exact, minus N→1 tag generalization |

### Repo files those plans edit

| Modified file | Role | Data flow | Closest analog | Match quality |
|---|---|---|---|---|
| `packages/market-data-client/pyproject.toml:3` | config (version site 1) | file-I/O | `40-01-PLAN.md:678-679`, `:735-736` | exact (same file, prior bump) |
| `packages/market-data-client/src/market_data_client/__init__.py:163` | config + exports (version site 2 + D-05 fold) | file-I/O | `40-01-PLAN.md:729-734` (version) / `models.__all__` (export list) | exact / role-match |
| `packages/market-data-client/README.md:15,:24` | doc (version sites 3-4) | file-I/O | `40-01-PLAN.md:723-728` — the *identical* two install pins, one version earlier | exact |
| `packages/market-data-client/README.md` `### v0.7.0` | doc (changelog + migration tables) | transform (6-col → 2-col) | `README.md` `### v0.6.0` (lines 127-152), authored by `40-01-PLAN.md:688-699` | exact |
| `uv.lock` (member block ~487-489) | lockfile artifact | batch | `40-01-PLAN.md` Task 4 (a) | exact |

**No file in `.github/workflows/` is modified** (D-02). **`main_market_data.py` is not touched** (D-06).

---

## Pattern Assignments

### `44-01-PLAN.md` (plan, autonomous prep)

**Analog:** `.planning/milestones/v1.7-phases/40-releases-breaking-coordinados/40-01-PLAN.md`,
Task 3 (lines 611-794) and Task 4 (lines 796-951).

**Version-bump task structure** — copy the `<files>` / `<read_first>` / lettered-`<action>` /
one-line `<verify><automated>` / long `<acceptance_criteria>` / `<done>` shape. Key excerpt of the
per-site edit prose (`40-01-PLAN.md:723-734`), which is *the same two README pins this phase moves*:

```
      - Re-pin BOTH version-pinned install commands. `packages/market-data-client/README.md` is the
        only file in the repo with version-pinned install lines: the git install at line 44 pins the
        prior tag `market-data-client-v0.5.0`, and the wheel URL at line 53 pins both that tag and
        the filename `market_data_client-0.5.0-py3-none-any.whl`. Both move to
        `market-data-client-v0.6.0` and `market_data_client-0.6.0-py3-none-any.whl`. Leaving them
        stale reproduces Phase 34's CR-01 defect verbatim.
```

For Phase 44 substitute: line 15 (git install) and line 24 (wheel URL, **two** substitutions on the
one line), `v0.6.0` → `v0.7.0`, `market_data_client-0.6.0-py3-none-any.whl` → `-0.7.0-`.

**Version-site assertion pattern** (`40-01-PLAN.md:773`, verbatim fragment) — always read
`pyproject.toml` with `release.yml`'s own awk, and pin `__version__` with `grep -qx`:

```bash
MV=$(awk -F'"' '/^version[[:space:]]*=/{print $2; exit}' packages/market-data-client/pyproject.toml) && test "$MV" = "0.6.0" \
&& grep -qx '__version__ = "0.6.0"' packages/market-data-client/src/market_data_client/__init__.py
```

**Changelog-position assertion** (`40-01-PLAN.md:773`) — proves the new section is the FIRST `###`
under `## Changelog`, and that the body survived the edit:

```bash
test "$(awk '/^## Changelog$/{f=1;next} f&&/^### /{print;exit}' packages/market-data-client/README.md)" = "### v0.6.0" \
&& MSEC=$(awk '/^### v0\.6\.0$/{f=1;next} /^### v/{f=0} f' packages/market-data-client/README.md) && test -n "$MSEC" \
&& for T in 'market_data.last.price' 'market_data.bids' 'not snapshot.market_data'; do printf '%s\n' "$MSEC" | grep -qF -- "$T" || exit 1; done
```

For Phase 44 the token list becomes the migration-table anchors from RESEARCH § Migration Table
Source: `market_id`, `marketId`, `days_to_maturity`, `active`, `segment`, `live_instruments`,
`marketSegmentId`, `if seg:`.

**Stale-survivor negative assertions** (`40-01-PLAN.md:773`) — the Phase-34 CR-01 guard:

```bash
test "$(grep -c 'market-data-client-v0.6.0' packages/market-data-client/README.md)" = "2" \
&& test "$(grep -c 'market_data_client-0.6.0-py3-none-any.whl' packages/market-data-client/README.md)" = "1" \
&& ! grep -q 'market-data-client-v0.5.0' packages/market-data-client/README.md
```

**Phase-44 correction:** the trailing `! grep -q` form breaks here, because the new `### v0.7.0`
prose legitimately mentions `0.6.0` as the "Antes" column label (RESEARCH OQ-3). Scope the survivor
grep to the region *above* `## Changelog`: `sed -n '1,/^## Changelog/p' … | grep -c 'v0\.6\.0'` == 0.

**Single `uv lock` + churn assertion** (`40-01-PLAN.md:829-846` action, `:930` verify) — for Phase 44
N is exactly 1, so the churn is `1 1`:

```bash
uv lock --check \
&& grep -A1 '^name = "market-data-client"$' uv.lock | grep -qx 'version = "0.7.0"' \
&& LOCKC=$(git log --format=%H origin/main..HEAD -- uv.lock | wc -l | tr -d ' ') && test "$LOCKC" = "1" \
&& test "$(git show --numstat --format= "$(git log --format=%H origin/main..HEAD -- uv.lock)" -- uv.lock | awk '{print $1, $2}')" = "1 1"
```

**Mandatory `uv sync` after `uv lock`** (`40-01-PLAN.md:848-856`) — this is the stale-`dist-info`
guard (RESEARCH Pitfall 3); it has no Phase-34 analog and was introduced by Phase 40. Copy the
rationale prose verbatim; it names `test_dunder_version_matches_installed_distribution_metadata`
explicitly, which is precisely the test that false-reds here.

**Branch create-then-push** (`40-01-PLAN.md:911-923`) — Phase 44's topology is identical to Phase
40's (pending commits live on local `main`), so copy this block, not Phase 34's `git push origin
<existing-branch>`:

```
    (f) Create the branch, THEN push it. HEAD currently sits on local `main`, which is where all of
    this milestone's pending commits live … Run `git checkout -b milestone/v1.7-nobj-null-objects`
    … Then `git push origin milestone/v1.7-nobj-null-objects` — a plain fast-forward, by name.

    A `git push origin main` here would publish every pending commit directly to the public default
    branch with no PR, no CI gate and no human approval. Do not run it. `--force` and
    `--force-with-lease` are FORBIDDEN …
```

Substitute a `milestone/v1.8-…` slug (Claude's discretion, D-07/A3).

**Credential scan before the public push** (`40-01-PLAN.md:900-909`) — copy verbatim; see
§ Shared Patterns.

**Phase-44-only additions with no 40-01 analog:**
- The `FeedSubscription` fold (D-05) — **two** edits (import block ~72-90 **and** `__all__`
  ~114-119), asserted by the *count* `187` from `tools/check_surface_types.py`, not merely
  "0 violations". Nearest analog for the assertion style is the positive-count doctrine in
  `40-02-PLAN.md:243-251`.
- `uv run python tools/check_surface_types.py` immediately after the edit, before push (D-05).

---

### `44-02-PLAN.md` (plan, gate a + merge)

**Analog:** `40-02-PLAN.md` — copy the whole file's skeleton; it is a 1:1 structural match.

**Frontmatter pattern** (`40-02-PLAN.md:1-60`):

```yaml
---
phase: 40-releases-breaking-coordinados
plan: 02
type: execute
wave: 2
depends_on: [40-01]
files_modified: []
autonomous: false
requirements: [PUB-NOBJ-01]
user_setup:
  - service: github
    why: "Opening a new PR against the public default branch and merging it are outward-facing GitHub operations; the merge is irreversible in practice"
    dashboard_config:
      - task: "Ensure the `gh` CLI is authenticated (asserted in Task 1 via `gh auth status`; never echo the token)"
        location: "local shell — `gh auth status`"
      - task: "Be available to answer the FIRST blocking go/no-go checkpoint before the merge (D-07a)"
        location: "the executing terminal session"
must_haves:
  truths: [...]
  prohibitions: [...]
  artifacts:
    - path: "gh-pr:<n>"
      provides: "the single release PR for v1.7, newly created against main"
      contains: "release:"
  key_links:
    - from: "git-ref:origin/main"
      to: "git-tag:market-data-client-v0.6.0"
      via: "plan 40-03 creates every annotated tag ON this merge commit so release.yml's version-match gate runs against the merged tree"
      pattern: "market-data-client-v0.6.0"
---
```

For Phase 44: `requirements: [PUB-01]`, `depends_on: [44-01]`, one `key_links` entry pointing at
`git-tag:market-data-client-v0.7.0`.

**`<reversibility_gates>` table** (`40-02-PLAN.md:113-125`) — reproduce this per-task
operation/reversibility/gate table; it is what makes the "exactly two gates" claim auditable.

**Task 1 — PR create + positive 15/15 count** (`40-02-PLAN.md:154-257`). Copy the four-precondition
block and the count assertion; drop the multi-package row loop to a single package:

```bash
gh auth status >/dev/null 2>&1 && test -z "$(git status --porcelain)" \
&& git fetch origin <branch> --quiet && test "$(git rev-parse HEAD)" = "$(git rev-parse origin/<branch>)" \
&& TOTAL=$(gh pr checks "$PR" | wc -l | tr -d ' ') \
&& PASSED=$(gh pr checks "$PR" | awk -F'\t' '$2=="pass"' | wc -l | tr -d ' ') \
&& test "$TOTAL" = "15" && test "$PASSED" = "15" \
&& C=$(gh pr checks "$PR" | grep -c "Tests · market-data-client · py3\.1[23]"); test "$C" = "2"
```

The doctrine prose to keep verbatim (`40-02-PLAN.md:220-226`): *"Statuses other than `pass` include
`fail`, `pending`, `skipping` and `cancelled` — an absence-of-failure check reads all of those as
green, and `cancelled` is genuinely reachable because `ci.yml:20` sets
`concurrency: cancel-in-progress: true`."*

**Task 2 — the FIRST gate.** Copy the element inventory of `40-02-PLAN.md:259-379`: `<name>`,
`<files>none — this task modifies no file</files>`, `<read_first>`, `<acceptance_criteria>`
(7 items), `<action>` opening with the literal token `PAUSE.`, `<what-built>`, `<how-to-verify>`
(numbered), `<resume-signal>`, `<verify><automated>` proving nothing irreversible ran, `<done>`.

**Copy the `<action>` prose verbatim — but NOT the opening tag.** The prose armour
(`40-02-PLAN.md:286`) is what actually saved the previous four occurrences:

```
<action>PAUSE. This is the first of exactly two blocking human checkpoints on irreversible operations
for this phase (`autonomous: false`). Do NOT merge the PR, do NOT create any tag, and do NOT push
anything until the operator explicitly replies "approved". This gate is never auto-approvable:
`auto_advance: true` and `mode: yolo` are both active in `.planning/config.json` and neither satisfies
it, silence does not satisfy it, an ambiguous reply does not satisfy it, and the agent may not
self-issue it. If the operator replies "abort", stop cleanly with no irreversible action taken …</action>
```

**Pre-gate "nothing happened yet" verify** (`40-02-PLAN.md:376`) — adapt to one tag:

```bash
PR=$(gh pr list --state open --base main --head <branch> --json number --jq '.[0].number') && test -n "$PR" \
&& test "$(gh pr view "$PR" --json state --jq .state)" = "OPEN" \
&& git fetch origin main --tags --quiet \
&& test -z "$(git tag -l 'market-data-client-v0.7.0')" \
&& test -z "$(git status --porcelain)" \
&& echo "PASS — nothing irreversible happened before the operator reply"
```

**Task 3 — merge + two-parent proof** (`40-02-PLAN.md:381-461`). The load-bearing excerpt
(`40-02-PLAN.md:415-421`):

```
    Assert it mechanically: `git rev-list --parents -n1 origin/main` must yield exactly three
    whitespace-separated fields. A single-parent commit means the merge was squashed or rebased:
    STOP … Reading the subject line is not sufficient — some UIs render a squash with a
    merge-looking subject; the parent count cannot lie.
```

Verify fragment (`40-02-PLAN.md:446`), reduced to one package:

```bash
git fetch origin main --tags --quiet \
&& test "$(git rev-list --parents -n1 origin/main | wc -w | tr -d ' ')" -eq 3 \
&& git log -1 --format=%s origin/main | grep -q '^Merge pull request' \
&& MDV=$(git show origin/main:packages/market-data-client/pyproject.toml | awk -F'"' '/^version[[:space:]]*=/{print $2; exit}') && test "$MDV" = "0.7.0"
```

---

### `44-03-PLAN.md` (plan, gate b + tag + publish + post-publish proof)

**Analog:** `40-03-PLAN.md` — Task 1 (172-280), Task 2 (282-397), Task 3 (399-…).

**Task 1 — the SECOND gate.** Same element inventory as gate (a). The distinguishing `<action>`
content (`40-03-PLAN.md:200`) is the live re-resolution, which Phase 44 keeps verbatim:

```
… ONE approval here authorizes ALL tags of this round — do not ask twice … Before presenting,
re-resolve the target live: `git fetch origin main --tags`, then `MERGE_SHA=$(git rev-parse
origin/main)`. Present the freshly re-resolved merge-commit SHA with its two parents, every
merged-tree version read with `release.yml`'s own awk expression, every exact tag string to be
published, and the fact that a GitHub Release cannot be cleanly un-published or re-pointed.
```

Its 6-item `<acceptance_criteria>` (`40-03-PLAN.md:192-199`) is the canonical audit-trail list —
reuse all six, with "one approval covers all tags" collapsing to "the single tag of this round"
(D-09).

**Task 2 — annotated tag on the re-resolved SHA, pushed by name** (`40-03-PLAN.md:304-377`). Copy
sub-steps (a)-(g). Load-bearing prose (`40-03-PLAN.md:321-325`, `:333-336`):

```
    Never run `git tag <name>` with no commit-ish — that tags branch HEAD, and `release.yml`'s
    version check runs against the TAGGED tree …
    (c) Push each tag BY NAME: `git push origin <tag>` … Never push a bare `--tags`: 15 package tags
    and the milestone tags `v1.1`…`v1.6` exist locally, and a wholesale push would publish whatever
    is stale. Never use a force flag.
```

Per-tag verification loop (`40-03-PLAN.md:379`), Phase-44 form (single tag):

```bash
T=market-data-client-v0.7.0
git tag | grep -qx "$T" && test "$(git cat-file -t "$T")" = "tag" \
&& git ls-remote --tags origin "$T" | grep -q . \
&& test "$(git rev-list -n1 "$T")" = "$MERGE_SHA" \
&& gh release view "$T" --json assets --jq '.assets[].name' | grep -qx "market_data_client-0.7.0-py3-none-any.whl" \
&& gh release view "$T" --json assets --jq '.assets[].name' | grep -qx "market_data_client-0.7.0.tar.gz"
```

**Tag-count invariance for the other five packages** — `40-03-PLAN.md:373-374` asserts this in prose
and `:379` in shell (`test "$(git tag -l 'ambito-financiero-client-v*' | wc -l …)" = "2"`). Phase 44
extends it to all five per D-10 (4/3/3/2/1) plus `market-data-client` → 8.

**Task 3 — post-publish install from the PUBLIC wheel** (`40-03-PLAN.md:399-…`). Copy sub-steps
(a)-(d). The two load-bearing constraints (`40-03-PLAN.md:426-431`, `:441-445`):

```
    (a) Create a throwaway working directory outside the repository (`WORK=$(mktemp -d)`) and build a
    fresh interpreter there with `uv venv --python 3.12`. The `--python 3.12` flag is load-bearing,
    not cosmetic: the system `python3` on this machine is 3.9.6 … Do not run any part of this task
    from inside the repository checkout, and do not add the workspace to the venv.

    NEVER install by bare package name. None of these packages is on PyPI, and a bare
    `uv add market-data-client` would resolve a different project entirely …
```

The deep-chain body for Phase 44 is already written in RESEARCH § Code Examples → "Post-publish proof
from the PUBLIC wheel"; transcribe it rather than re-deriving (same discipline as
`40-03-PLAN.md:403-405`).

---

## Shared Patterns

### Checkpoint gate authoring (ANTI-PATTERN + correction) — applies to `44-02` and `44-03`

**Defective source — DO NOT COPY THESE OPENING TAGS:**

| File:line | Verbatim (defective) |
|---|---|
| `40-01-PLAN.md:305` | `<task type="checkpoint:decision" gate="blocking">` |
| `40-02-PLAN.md:259` | `<task type="checkpoint:human-verify" gate="blocking">` |
| `40-03-PLAN.md:172` | `<task type="checkpoint:human-verify" gate="blocking">` |
| `34-02-PLAN.md:243` | `<task type="checkpoint:human-verify" gate="blocking">` |
| `34-03-PLAN.md:168` | `<task type="checkpoint:human-verify" gate="blocking">` |

Five occurrences across two phases (CONTEXT D-08 counts four; `34-02`/`34-03` are both measurable
in-file, so the census is five). All were survivable only via manual orchestrator override.

**Correct construct** (RESEARCH § Gate Authoring Semantics, recommended over D-08's two enumerated
types per OQ-1):

```xml
<task type="checkpoint:human-action" gate="blocking-human">
  <name>Task N: FIRST blocking go/no-go gate — before the IRREVERSIBLE merge (D-08a)</name>
  <files>none — this task modifies no file</files>
  <read_first>…</read_first>
  <acceptance_criteria>… (the 6-7 item audit list from 40-02:277-284 / 40-03:192-199) …</acceptance_criteria>
  <action>PAUSE. … (Phase-40 prose armour verbatim) …</action>
  <what-built>…</what-built>
  <how-to-verify>…</how-to-verify>
  <resume-signal>Reply "approved" to authorize the merge, or "abort"</resume-signal>
  <verify><automated>… proves nothing irreversible ran …</automated></verify>
  <done>…</done>
</task>
```

`human-action` is the only type that stops at **both** the executor
(`gsd-executor.md:314-318`) and the orchestrator (`execute-phase.md:1057-1061`) layers under
`auto_advance: true`, and it is exempt from `human_verify_mode: end-of-phase` suppression.
`gate="blocking-human"` is retained so the ROADMAP criterion-4 in-file grep passes.

**Post-hoc audit** to run before closing the phase:

```bash
bash -c 'cd .planning/phases/44-release-market-data-client-0-7-0
  echo "bad (must be 0):  $(grep -ho "gate=\"blocking\"" 44-0*-PLAN.md | wc -l | tr -d " ")"
  echo "good (must be 2): $(grep -ho "gate=\"blocking-human\"" 44-0*-PLAN.md | wc -l | tr -d " ")"'
```

### Never-auto-approve prohibition line

**Source:** `40-02-PLAN.md:32` (`must_haves.prohibitions`). **Apply to:** `44-02` and `44-03`
frontmatter, verbatim:

```
"Neither of this phase's two blocking human checkpoints on irreversible operations may be satisfied
by the agent itself, by `auto_advance`, by yolo mode, or by inferring approval from silence or from
an ambiguous reply. Only a literal operator response counts, and it is recorded verbatim."
```

Add (RESEARCH OQ-1 fallback) an explicit line naming `execute-phase.md:1059` as the specific
auto-approve path that must not fire.

### History-immutability prohibition

**Source:** `40-02-PLAN.md:30`. **Apply to:** `44-02` (merge) and `44-03` (tag):

```
"Never rewrite history reachable from this branch or from `main`: `--squash` and `--rebase` are
forbidden merge strategies, and no force flag is permitted on any push. Dozens of SUMMARY files …
cite these SHAs by value, and `--rebase` would rewrite history already reachable from published tags."
```

### Positive-count prohibition

**Source:** `40-02-PLAN.md:31`. **Apply to:** `44-02` Task 1, and by extension every count in the
phase (D-11):

```
"Never report a gate as green from anything except an exact positive count. `pending`, `skipping`,
`cancelled` and a zero-check run all read as green under an absence-of-failure check, and
`cancel-in-progress: true` (ci.yml:20) makes `cancelled` genuinely reachable."
```

### Workflow immutability by sha256 digest identity — DO NOT copy the Phase-34 form

**Source:** `40-01-PLAN.md:887-898` (the correction) and `40-03-PLAN.md:362-371`.
**Apply to:** `44-01` (pre-push) and `44-03` (post-tag).

```
    (d) Assert the workflow files are untouched — using the CORRECTED form, not Phase 34's. Phase
    34's assertion (`git diff --name-only <prior-release-tag>..HEAD -- .github/workflows` must be
    empty) is broken and failed three times during that phase, because `ci.yml` legitimately changes
    between releases …
      - `release.yml` is byte-identical everywhere. Take its sha256 at `HEAD`, at `origin/main` and
        at the last published tag …; `sort -u` over those digests must yield exactly one line.
```

Phase-44 ref set: `HEAD`, `origin/main`, `market-data-client-v0.6.0`, `market-data-client-v0.7.0`.

### Credential scan before the public push

**Source:** `40-01-PLAN.md:900-909` (action) + `:930` (shell). **Apply to:** `44-01`, immediately
before the branch push:

```bash
! git diff origin/main...HEAD | grep -qE 'eyJ[A-Za-z0-9_-]{20,}' \
&& ! git diff origin/main...HEAD | grep -qiE 'client_secret[[:space:]]*[=:][[:space:]]*.{0,2}[A-Za-z0-9_-]{20,}' \
&& test -z "$(git ls-files | grep -E '(^|/)\.env$')"
```

Prose to keep: *"Never echo a token, a secret value, the `gh` OAuth token or the SSH key into output
— report file and line only."*

### Local CI mirror, never a bare `uv run pytest`

**Source:** `40-01-PLAN.md:858-885` + `:930`. **Apply to:** `44-01` before the push.
*"NEVER run a bare `uv run pytest`: the root `testpaths` collects `verification/`, which carries
known pre-existing failures that no CI job executes (backlog `HARN-VERIF-01`)."*

### `bash -c` wrapping of every `<verify>` block (D-10)

**No analog in 40-0x** — the Phase-40 verify blocks are bare one-liners. Phase 44 must wrap each in
`bash -c '…'` per D-10 / RESEARCH Pitfall 4 (zsh word-splitting measured to fail on this machine).

### Re-derive every count at execution time (D-10)

**Source:** the pattern is present in `40-01-PLAN.md:836-838` (compute N at run time, do not hard-code
3 or 4) and `40-02-PLAN.md:181` (*"Recompute rather than trusting any literal"*). **Apply to:** every
`<verify>` block. Safe-to-hardcode literals for Phase 44 (RESEARCH Pitfall 5): the tag string
`market-data-client-v0.7.0`, the version `0.7.0`, the CI total `15`, the post-fold surface count `187`.

---

## No Analog Found

| File / concern | Role | Data flow | Reason |
|---|---|---|---|
| `44-01` `FeedSubscription` two-site export fold (D-05) | source (`__init__.py` import block + `__all__`) | file-I/O | No release phase has folded an export-surface fix into a bump task. Closest guidance is RESEARCH § "The `FeedSubscription` Fold" (measured) plus the surface-count assertion doctrine from D-11 — assert `187`, not "0 violations" |
| `44-01` two-table migration transcription (D-04) | doc (transform) | transform | `### v0.6.0` supplies the *shape* (bold callout → 2-col table → prose), but every prior changelog had a single merged table. The two-separate-tables rule and the `Segment` truthiness-flip row are Phase-44-original; source content is `43-DISPOSITION.md` §§ 1.1/1.2 and RESEARCH § Migration Table Source |
| `checkpoint:human-action` opening tag | plan | — | **Zero precedent in this repo.** All five precedent checkpoints are `human-verify`/`decision` with `gate="blocking"`. The pattern source is `.claude/agents/gsd-executor.md:207,219,316`, not a prior plan |
| `bash -c` verify wrapping | plan | — | No precedent plan uses it; D-10 introduces it |

---

## Metadata

**Analog search scope:** `.planning/milestones/v1.7-phases/40-releases-breaking-coordinados/`,
`.planning/milestones/v1.6-phases/34-releases-por-paquete/`, `packages/market-data-client/`
**Files scanned:** 6 precedent plan files (structure-grepped), 3 read in targeted ranges
(`40-01` 611-951, `40-02` 1-466, `40-03` 170-473), plus `44-CONTEXT.md` and `44-RESEARCH.md` in full
**Pattern extraction date:** 2026-09-01
