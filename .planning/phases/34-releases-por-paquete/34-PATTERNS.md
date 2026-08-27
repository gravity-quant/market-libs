# Phase 34: Releases por paquete - Pattern Map

**Mapped:** 2026-08-27
**Files analyzed:** 6 file-artifacts + 4 git/gh artifacts
**Analogs found:** 10 / 10 (exact — Phase 28 is a literal precedent for every artifact)

> **Note on RESEARCH.md:** none exists for this phase (skipped as unnecessary). All patterns below
> come from the live codebase and from the Phase 28 release-prep phase at
> `.planning/milestones/v1.5-phases/28-release-prep-publish-v0-3-0/`, which executed the identical
> mechanics for `market-data-client v0.4.0`. Where a 28-* PLAN cites its own `28-RESEARCH.md`
> line numbers in a `read_first` block, the planner must **drop those citations** — that file is
> Phase-28-scoped and there is no Phase-34 equivalent.

## File Classification

| New/Modified artifact | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `packages/market-data-client/README.md` (extend `### v0.5.0`) | doc/changelog | transform (surface delta → prose) | same file `### v0.4.0` @125-206 + `packages/iol-client/README.md` `### v0.3.0` @112-174 | exact |
| `packages/market-data-client/pyproject.toml` (`version` 0.4.0→0.5.0) | config | static metadata | same file, bumped in 28-01 Task 1(a) | exact |
| `packages/market-data-client/src/market_data_client/__init__.py:157` (`__version__`) | config | static metadata | same file/line, 28-01 Task 1(b) | exact |
| `packages/iol-client/pyproject.toml:3` (0.2.0→0.3.0) | config | static metadata | market-data-client pyproject bump | exact |
| `packages/iol-client/src/iol_client/__init__.py:87` (`__version__`) | config | static metadata | market-data-client `__init__` bump | exact |
| `uv.lock` (2 members × 2 lines) | lockfile | generated | 28-01 Task 1(d) `uv lock` | role-match (28 bumped 1 member, this bumps 2) |
| `gh-pr:#12` (update, not create) | ops/gh | request-response | 28-02 Task 1 (`gh pr create`) | role-match — **create → update**, see § Delta |
| checkpoint gate (a) merge | checkpoint plan | human-gated | `28-02-PLAN.md` Task 2 + Task 3 | exact |
| checkpoint gate (b) tag push ×2 | checkpoint plan | human-gated | `28-03-PLAN.md` Task 1 + Task 2 | role-match — **1 tag → 2 tags in one gate** (D-08) |
| `.claude/projects/-Users-admin-development-market-libs/memory/*-releases.md` (discretionary) | memory doc | transform | `.../memory/market-data-client-releases.md` (EXISTS) | exact |

## Pattern Assignments

### `packages/market-data-client/README.md` — extend `### v0.5.0` (doc, transform)

**Analog:** the same file's own `### v0.5.0` head (lines 125-166, already written in Phase 31) and
`### v0.4.0` (lines 167-206). Do **not** rewrite; **append** the 3 new breaks inside the existing
section, then retitle.

**Section boundaries (verified live):** `## Changelog` @123, `### v0.5.0 — sin publicar todavía`
@125, `### v0.4.0` @167. The new prose goes between 166 and 167.

**Retitle at bump time (D-04):**
```
### v0.5.0 — sin publicar todavía     →     ### v0.5.0
```
…and the first paragraph (lines 127-132) must be **deleted or rewritten** — it literally says
"El bump de `pyproject.toml` y el tag los hace la Phase 34" and warns the wheel says `0.4.0`.
That paragraph becomes false the moment the bump lands. This is a phase-specific trap with no
Phase 28 analog; call it out explicitly in the plan.

**Voice / format contract** (locked by the surrounding entries — copy verbatim):
- Spanish prose, `### vX.Y.Z` H3.
- Bold lead line naming the bump class + parenthetical semver justification, e.g.
  `**Cuatro endpoints de ops dejan de devolver diccionarios…** (breaking, minor bump en línea 0.x — …)`
- Antes/después markdown table where a signature changes:
  ```markdown
  | Función | Antes | Ahora |
  |---|---|---|
  | `get_health` | `dict[str, Any]` | `Health` |
  ```
- Every identifier and endpoint path in **backticks** — the Phase 28 automated gate sliced the
  section and required each field name backticked; reuse that gate shape (see Verify pattern below).
- Wrapped ~95-100 columns, continuation lines indented exactly 2 spaces.
- `trailing-whitespace` + `end-of-file-fixer` pre-commit hooks run over this file in CI.

**Required new content — the 3 breaks from `33-07-SUMMARY.md:186-195`** (verbatim identities):

| Id | Break | Wording anchor |
|---|---|---|
| SC-1 | `preview_calendar_config` declarado `-> CalendarConfig` pero el wire devuelve un sobre de preview distinto (9 campos declarados ausentes, 3 reales descartados) → retorno pasa a un modelo de preview dedicado | antes/después table row |
| SC-2 | `MarketDataSnapshot.entries` / `.market_data` / `.staleness_seconds` pasan a `\| None` (llegan `null` en la fila no-data) | bold lead + 3 backticked field names |
| SC-3 | `Symbol.created_at` / `.updated_at` pasan a `str \| None` (ausentes de los tres acks de escritura) | 2 backticked field names |

All three are **source-breaking** per 33-07. The section must therefore carry a breaking callout
covering 7 items total (4 from Phase 31 + these 3), not 4.

---

### Version bumps — 3 sites × 2 packages (config, static metadata)

**Analog:** `28-01-PLAN.md` Task 1, steps (a)/(b)/(d). Ordering is **load-bearing**: pyproject
first, `__version__` second, `uv lock` last.

**Current live values (verified):**

| Site | iol-client | market-data-client |
|---|---|---|
| `pyproject.toml` line 3 | `version = "0.2.0"` → `0.3.0` | `version = "0.4.0"` → `0.5.0` |
| `__init__.py` | `:87` `__version__ = "0.2.0"` → `0.3.0` | `:157` `__version__ = "0.4.0"` → `0.5.0` |
| `uv.lock` | `:383` name / `:384` version `0.2.0` → `0.3.0` | `:487` name / `:488` version `0.4.0` → `0.5.0` |

**Why pyproject is the hard gate** (`.github/workflows/release.yml:42-51`, read-only):
```yaml
PYPROJECT_VERSION=$(awk -F\" '/^version[[:space:]]*=/{print $2; exit}' "packages/$PACKAGE/pyproject.toml")
if [[ "$PYPROJECT_VERSION" != "$TAG_VERSION" ]]; then
  echo "::error::Tag ($TAG_VERSION) ≠ pyproject.toml ($PYPROJECT_VERSION) en packages/$PACKAGE"
  exit 1
fi
```

**Why `__version__` needs a local assertion:** the pipeline does **not** validate it. Drift ships
green and is undetectable at release time. Copy 28-01's defense:
```bash
grep -qx '__version__ = "0.5.0"' packages/market-data-client/src/market_data_client/__init__.py
```

**`uv.lock` (D-11, single refresh):** never hand-edit. Run `uv lock` **after both** pyproject edits,
then `uv lock --check` (exit 0). Phase 28's churn gate was `uv.lock | 2 +-` for one member; for
**two** members expect **4 lines** (`2 insertions, 2 deletions`). A larger diff means uv re-resolved
third-party deps — STOP and surface rather than commit.

```bash
grep -A1 '^name = "market-data-client"$' uv.lock | grep -qx 'version = "0.5.0"'
grep -A1 '^name = "iol-client"$'          uv.lock | grep -qx 'version = "0.3.0"'
uv lock --check
```

**Test scoping (28-01 step (e), non-negotiable):** never a bare `uv run pytest` — root `testpaths`
includes `verification/` with known out-of-scope matriz failures. Scope per package:
```bash
uv run pytest packages/market-data-client -q
uv run pytest packages/iol-client -q
```

**Commit shape:** 28-01 committed exactly 4 files with subject
`chore(market-data-client): bump to v0.4.0 (<headline>)`. For two packages, either two `chore(<pkg>)`
commits (cleaner; matches the per-package versioning convention) or one — Claude's discretion per
CONTEXT. Exclude `.planning/` from the bump commit(s).

---

### PR #12 update (ops, request-response) — **DELTA from analog**

**Analog:** `28-02-PLAN.md` Task 1. It ran `gh pr create`; **D-05 mandates update, not create.**

**Reusable verbatim — the preconditions block (28-02 Task 1(a)):**
```bash
gh auth status                        # exits 0; never echo the token — already redacted
test -z "$(git status --porcelain)"   # clean tree
test "$(git rev-parse HEAD)" = "$(git rev-parse origin/milestone/v1.5-mutations)"
```
The third assertion is currently **FALSE** — local is ahead of origin. Verified live:
`git rev-list --count origin/milestone/v1.5-mutations..HEAD` = **47** (CONTEXT says 44; 47 is
correct as of 2026-08-27, and it will grow with this phase's own commits). The plan must
**fast-forward push first** (`git push origin milestone/v1.5-mutations`, never `--force`), then
re-assert equality, then update the PR.

**Substitute for `gh pr create`:**
```bash
gh pr edit 12 --title "release: iol-client v0.3.0 + market-data-client v0.5.0 (<scope>)" \
              --body-file <file>
```
Title convention inherited from PRs #8-#11 and D-12: `release: <pkg> v<X.Y.Z> (<one-line scope>)`.
Do **not** run `/gsd-pr-branch`; do **not** filter `.planning/` out of the diff (D-06).

**Reusable verbatim — the count-based CI gate (28-02 Task 1(d)).** This is the single most
important pattern to copy: assert **by count**, never by absence of the word "fail". Statuses
other than `pass` include `pending`, `skipping`, `cancelled`; a Markdown-only diff triggers
**zero** checks (`paths-ignore: ["**.md", ".gitignore"]`) and "no checks" is not green.

```bash
gh pr checks 12 --watch
PR=12
TOTAL=$(gh pr checks "$PR" | wc -l | tr -d ' ')
PASSED=$(gh pr checks "$PR" | awk -F'\t' '$2=="pass"' | wc -l | tr -d ' ')
test "$TOTAL" = "15" && test "$PASSED" = "15"
```

**Check count is still 15** — verified against `.github/workflows/ci.yml:112-120`: `matrix.package`
already lists all 6 packages × 2 python-versions = 12, plus `Lint y formato (ruff)`,
`pre-commit hooks`, `Type check (mypy)` = 15. Two packages changing does **not** change the count.

**Phase-34 delta:** where 28-02 asserted `grep -c 'Tests · market-data-client · py3\.1[23]'` = 2,
this phase asserts **two** package greps = 2 each:
```bash
test "$(gh pr checks $PR | grep -c 'Tests · market-data-client · py3\.1[23]')" = "2"
test "$(gh pr checks $PR | grep -c 'Tests · iol-client · py3\.1[23]')" = "2"
```

Do **not** push a commit while checks are running — it cancels the in-flight run
(`concurrency: cancel-in-progress: true`). If a fix lands, re-watch and re-assert 15/15 from scratch.

---

### Checkpoint gate (a) — merge (checkpoint plan, human-gated)

**Analog:** `28-02-PLAN.md` — frontmatter, Task 2 (`checkpoint:human-verify`), Task 3 (merge).

**Frontmatter pattern (copy shape, re-point paths):**
```yaml
autonomous: false
user_setup:
  - service: github
    why: "Merging to the public default branch is irreversible in practice"
    dashboard_config:
      - task: "Ensure the `gh` CLI is authenticated (asserted in Task 1 via `gh auth status`; never echo the token)"
        location: "local shell — `gh auth status`"
      - task: "Be available to answer the blocking go/no-go checkpoint before the merge (D-08a)"
        location: "the executing terminal session"
```

**Checkpoint task tag:**
```xml
<task type="checkpoint:human-verify" gate="blocking">
```

**Checkpoint `<action>` pattern** (28-02 Task 2, adapt nouns):
> PAUSE. This is a blocking human checkpoint (`autonomous: false`). Do NOT merge the PR, do NOT
> create any tag, and do NOT push anything until the operator explicitly replies "approved". If the
> operator replies "abort", stop cleanly with no irreversible action taken — the PR stays open and
> everything so far is revertible. Present: the PR URL and number, the literal `gh pr checks`
> output with the counted totals (15 rows / 15 pass / 2 iol rows / 2 market-data rows), the diff
> stat, and an explicit statement that `main` has NO branch protection so this approval is the only
> gate.

**Merge task pattern (28-02 Task 3, D-09):**
```bash
gh pr merge 12 --merge          # --merge mandatory; never --squash, never --rebase
git fetch origin main --tags
MERGE_SHA=$(git rev-parse origin/main)
git log -1 --format='%H %p %s' "$MERGE_SHA"     # %p MUST list two parents
```
Two-parent assertion + merged-tree version assertion, generalized to both packages:
```bash
test "$(git rev-list --parents -n1 origin/main | wc -w | tr -d ' ')" -eq 3
git log -1 --format=%s origin/main | grep -q '^Merge pull request'
test "$(git show origin/main:packages/iol-client/pyproject.toml         | awk -F'"' '/^version[[:space:]]*=/{print $2; exit}')" = "0.3.0"
test "$(git show origin/main:packages/market-data-client/pyproject.toml | awk -F'"' '/^version[[:space:]]*=/{print $2; exit}')" = "0.5.0"
```
`delete_branch_on_merge` is `false`, so the branch survives — do not pass a branch-delete flag.
A single-parent commit means squash/rebase happened: STOP, do not tag.

---

### Checkpoint gate (b) — push BOTH tags (checkpoint plan, human-gated)

**Analog:** `28-03-PLAN.md` Task 1 (second checkpoint) + Task 2 (tag/push/verify).
**Delta:** one approval authorizes **both** tags (D-08); do not split into two gates.

**Second-checkpoint `<action>` pattern** (28-03 Task 1, adapt to two tags):
> PAUSE. This is the second blocking human checkpoint (`autonomous: false`), independent of the
> merge approval already given. Do NOT create either tag, do NOT push anything, and do NOT trigger
> `release.yml` until the operator explicitly replies "approved" a second time. If the operator
> replies "abort", stop cleanly: `main` keeps the merge commit and no public Release is created.
> Present the resolved merge-commit SHA with its two parents, the two exact tag strings to be
> published, and the fact that a GitHub Release cannot be cleanly un-published.

**Tag creation (28-03 Task 2(a)-(c)) — annotated, on the merge SHA, re-resolved not trusted:**
```bash
git fetch origin main --tags
MERGE_SHA=$(git rev-parse origin/main)
# re-assert two parents + both pyproject versions BEFORE tagging; STOP on failure

git tag -a iol-client-v0.3.0         "$MERGE_SHA" -m "iol-client v0.3.0 — <headline>"
git tag -a market-data-client-v0.5.0 "$MERGE_SHA" -m "market-data-client v0.5.0 — <headline>"

git push origin iol-client-v0.3.0
git push origin market-data-client-v0.5.0
```
Never `git tag <name>` with no commit-ish (tags branch HEAD; `release.yml` validates the **tagged**
tree). Push **by name only** — never a bare `--tags` (stale local `v1.1`..`v1.5` tags exist that are
unrelated to this phase), never `--force`.

Tag literals must satisfy `release.yml:28`'s regex `^([a-z][a-z0-9-]*-client)-v([0-9]+\.[0-9]+\.[0-9]+…)$`
and the `*-client-v*` push trigger. Exactly `iol-client-v0.3.0` and `market-data-client-v0.5.0`.

**Two runs, two Releases** — watch each:
```bash
gh run list --workflow=release.yml --limit 5
gh run watch <run-id>              # once per tag
```

**Release asset verification (28-03 Task 2(e)), per package:**
```bash
gh release view iol-client-v0.3.0         --json assets --jq '.assets[].name'  # iol_client-0.3.0-py3-none-any.whl + .tar.gz
gh release view market-data-client-v0.5.0 --json assets --jq '.assets[].name'  # market_data_client-0.5.0-*.whl + .tar.gz
test "$(git rev-list -n1 iol-client-v0.3.0)"         = "$(git rev-parse origin/main)"
test "$(git rev-list -n1 market-data-client-v0.5.0)" = "$(git rev-parse origin/main)"
git cat-file -t iol-client-v0.3.0    # must print `tag` (annotated, not lightweight)
```

**Workflow-untouched gate** (28-03, adapt the tag range — prior tags verified live:
`iol-client-v0.2.0`, `market-data-client-v0.4.0`):
```bash
test "$(git diff --name-only market-data-client-v0.4.0..market-data-client-v0.5.0 -- .github/workflows | wc -l | tr -d ' ')" = "0"
```

---

### Release memory files (memory doc, transform) — discretionary

**Analog:** `.claude/projects/-Users-admin-development-market-libs/memory/market-data-client-releases.md`
— it **EXISTS** (verified live). **CONTEXT § Verification/Risk Notes is wrong** on this point: it
claims no memory file exists for either package. Directory listing:
`market-data-client-releases.md`, `MEMORY.md`, `phase-23-wave2-pending-creds.md`.

So the work splits: `market-data-client-releases.md` is a **refresh** (28-03 Task 3's six-region
pattern applies literally), `iol-client-releases.md` would be **new**. Both remain discretionary.

Committed on the release branch **after** the tag push (28-03 Task 3, C-3): the memory's
`**Latest published:**` block cites the merge-commit SHA, the PR number and the `release.yml` run
ID — none of which exist before the push. Never include it in the bump commit.

## Shared Patterns

### Never echo credentials
**Source:** every 28-* PLAN task
**Apply to:** all three plans
`gh auth status` already redacts; never print the token, SSH key, or any `.env` value. Scan the
full `origin/main...HEAD` diff for credentials before pushing (28-01 T-28-01).

### Assert by count, never by absence of "fail"
**Source:** `28-02-PLAN.md` Task 1(d) + `28-PATTERNS.md` § S-2
**Apply to:** the CI gate, the asset lists, the tag-anchor checks
`awk -F'\t' '$2=="pass"' | wc -l` compared to an exact expected integer. `pending`/`skipping`/
`cancelled`/zero-checks all read as green under a naive grep.

### Re-resolve, never trust a literal SHA from a SUMMARY
**Source:** `28-03-PLAN.md` Task 2(a)
**Apply to:** every task downstream of the merge
`MERGE_SHA=$(git rev-parse origin/main)` recomputed in-task; the SUMMARY value is a cross-check only.

### `<verify><automated>` one-liner ending in `&& echo PASS`
**Source:** every 28-* `auto` task
**Apply to:** all auto tasks
Chain every assertion with `&&`, terminate with `echo PASS`. The section-slicing form is reusable
for the README gate:
```bash
SEC=$(awk '/^### v0\.5\.0$/{f=1;next} /^### v/{f=0} f' packages/market-data-client/README.md)
for T in '`preview_calendar_config`' '`entries`' '`market_data`' '`staleness_seconds`' '`created_at`' '`updated_at`'; do
  printf '%s\n' "$SEC" | grep -qF -- "$T" || { echo "CALLOUT INCOMPLETE: $T"; exit 1; }
done
```
Note the awk pattern `/^### v0\.5\.0$/` only matches **after** the "— sin publicar todavía" suffix
is removed — which is exactly what makes the retitle verifiable.

### Read-only workflow files
**Source:** D-11, 28-03 Task 2(d)
**Apply to:** all plans
`.github/workflows/release.yml` and `ci.yml` are never edited. `release.yml` is generic by tag
regex; `ci.yml` already lists all 6 packages. If `release.yml` fails, surface the failing step —
never patch the workflow.

## No Analog Found

| Artifact | Role | Data Flow | Reason |
|---|---|---|---|
| The "sin publicar todavía" → published retitle + stale-preamble deletion | doc edit | transform | Phase 28 authored its changelog entry fresh at bump time; no prior phase wrote a provisional entry that later had to be de-provisionalized. `README.md:125-132` is a phase-specific trap with no precedent. |
| Two tags on one merge commit / one approval | ops | human-gated | Every prior release (PRs #8-#11, Phase 28) published exactly one package per merge. The mechanics compose cleanly, but there is no executed precedent for two `release.yml` runs off one commit. |

## Corrections to CONTEXT.md (verified live 2026-08-27)

| CONTEXT claim | Live reality |
|---|---|
| "local está 44 commits adelante de `origin/milestone/v1.5-mutations`" (D-05) | **47** (`git rev-list --count`), and growing with this phase's own commits — the plan must recompute, not hardcode |
| "Ningún archivo de memory in-repo existe todavía para `iol-client` ni `market-data-client`" | `memory/market-data-client-releases.md` **exists**; only `iol-client-releases.md` would be new |

Neither correction changes any locked decision; both change the shape of the work the planner writes.

## Metadata

**Analog search scope:** `.planning/milestones/v1.5-phases/28-release-prep-publish-v0-3-0/` (28-01/02/03-PLAN.md, 28-CONTEXT.md), `.github/workflows/`, `packages/iol-client/`, `packages/market-data-client/`, `uv.lock`, `.claude/projects/*/memory/`, git tag + ref state
**Files scanned:** 12
**Pattern extraction date:** 2026-08-27
