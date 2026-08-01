# Phase 28: Release prep + publish v0.4.0 - Pattern Map

**Mapped:** 2026-08-01
**Files analyzed:** 7 edit sites (+ 2 plan documents to be authored)
**Analogs found:** 9 / 9

> **Nomenclature:** the phase directory says `v0-3-0`; the version this phase publishes is
> **`0.4.0`**. `v0.3.0` and `v0.3.1` are already published. Do not "correct" the directory name.

> **This is a release/ops phase.** No production source is modified. The analogs below are
> therefore **prior instances of these same edits** (the v0.3.1 and v0.3.0 release commits on this
> very branch), not architectural siblings. Every excerpt is verbatim.

---

## File Classification

| File to modify | Role | Data Flow | Closest Analog | Match Quality |
|----------------|------|-----------|----------------|---------------|
| `packages/market-data-client/pyproject.toml:3` | config (package metadata) | static declaration | same file @ `7f051ae` (0.3.0→0.3.1) | exact |
| `packages/market-data-client/src/market_data_client/__init__.py:134` | config (runtime version mirror) | static declaration | same file @ `7f051ae` | exact |
| `packages/market-data-client/README.md:60-62` | doc (changelog) | append-at-top log | `README.md:62-70` (v0.3.1 entry), `:72-88` (v0.3.0), `:90-103` (v0.2.0) | exact |
| `uv.lock:488` | config (lockfile) | generated | same file @ `7f051ae` (2-line churn) | exact |
| `.claude/projects/…/memory/market-data-client-releases.md` (6 regions) | doc (agent memory) | replace-latest + demote-prior | same file @ `ce77ed4` | exact |
| `.planning/REQUIREMENTS.md:28` + `:65` | doc (requirements) | in-place re-point | v1.4 PUB-MD-01 row pattern (same file) | role-match |
| `.planning/ROADMAP.md:19`, `:188-198`, `§ Backlog` | doc (roadmap) | in-place re-point + backlog append | `ROADMAP.md:239-245` (existing backlog bullets) | role-match |
| **`28-01-PLAN.md`** (to author) | plan doc (reversible prep) | wave-1 autonomous | `24-01-PLAN.md` @ `b07a924` | exact |
| **`28-02-PLAN.md`** (to author) | plan doc (irreversible publish) | wave-2, human-gated | `24-02-PLAN.md` @ `b07a924` | exact |

---

## Pattern Assignments

### 1. The prep commit — `7f051ae` (the exact 4-file shape to replicate)

**Analog:** `git show 7f051ae` — `chore(market-data-client): bump to v0.3.1 (get_latest_batch envelope fix)`

```
 packages/market-data-client/README.md                          | 10 ++++++++++
 packages/market-data-client/pyproject.toml                     |  2 +-
 packages/market-data-client/src/market_data_client/__init__.py |  2 +-
 uv.lock                                                        |  2 +-
 4 files changed, 13 insertions(+), 3 deletions(-)
```

Commit message shape (subject + 3-line body + trailers):

```
chore(market-data-client): bump to v0.3.1 (get_latest_batch envelope fix)

Patch — fix parse_latest_response to unwrap the batch {items:[...]} envelope
so get_latest_batch returns populated snapshots (was returning N empties).
pyproject + __version__ + README changelog + uv.lock aligned at 0.3.1.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_…
```

**Replicate as:** `chore(market-data-client): bump to v0.4.0 (calendar write + live-verified mutation fixes)`
— note the last body line is a literal inventory of the four aligned sites; keep it.

**Note (RESEARCH C-3 + C-1):** Phase 28's prep commit will additionally carry the release-memory
file and the `.planning/` re-point, and **must be followed by an explicit
`git push origin milestone/v1.5-mutations`** (the branch is 96 commits stale on origin — plain
fast-forward, `--force` forbidden).

---

### 2. `packages/market-data-client/pyproject.toml` (config, static)

**Current state** (`pyproject.toml:1-4`):

```toml
[project]
name = "market-data-client"
version = "0.3.1"
description = "Cliente HTTP (sync y async) para la API de market data (primary-extractor) con Auth0 client-credentials."
```

**Analog diff** (`7f051ae`) — single-line replace, nothing else in the file moves:

```diff
 [project]
 name = "market-data-client"
-version = "0.3.0"
+version = "0.3.1"
```

**Apply:** `version = "0.3.1"` → `version = "0.4.0"`. **Must be edited BEFORE `uv lock`** (P-2).

---

### 3. `src/market_data_client/__init__.py` (config, runtime mirror)

**Current state** (`__init__.py:130-134`):

```python
    "update_symbol",
]

# Suppress ruff F401 for the deliberate private re-export.
_ = _get_default

__version__ = "0.3.1"
```

**Analog diff** (`7f051ae`) — last line of file, no trailing content:

```diff
 _ = _get_default

-__version__ = "0.3.0"
+__version__ = "0.3.1"
```

**Apply:** → `__version__ = "0.4.0"`. `release.yml` validates **only** `pyproject.toml` (P-4), so
this site must be asserted locally.

---

### 4. `packages/market-data-client/README.md` — changelog entry (doc, append-at-top)

**Insertion point:** `README.md:60-62` — new `### v0.4.0` block goes immediately **above**
`### v0.3.1`, under the `## Changelog` H2.

**Analog diff** (`7f051ae`) — shows the exact insertion mechanics (blank line after `## Changelog`,
entry, blank line, then the previous entry):

```diff
 ## Changelog

+### v0.3.1
+
+**Bugfix (patch):** `get_latest_batch` devolvía snapshots vacíos.
+
+- `parse_latest_response` asumía que `POST /marketdata/latest` (batch) devolvía una lista bare,
+  pero el servidor devuelve un envelope `{"requested", "count", "not_found", "server_time", "items": [...]}`.
+  Iteraba las claves del dict en vez de `items[]`, produciendo N `MarketDataSnapshot` vacíos. Ahora
+  desenvuelve `items` (igual que su hermano `parse_market_data_response`) preservando el path bare-list
+  del single `get_latest`; un dict sin `items` degrada a `[]`. Sync y async (fix en `_core.py` compartido).
+
 ### v0.3.0
```

**Model A — minor-with-new-surface** (`README.md:72-88`) — the closest voice match for v0.4.0
(bold lead naming the bump class, parenthetical semver justification, requirement IDs inline in
each bullet's bold lead):

```markdown
### v0.3.0

**Nueva superficie de escritura: symbols detrás de un mutating-gate de seguridad**
(features nuevas, minor bump — no rompe la superficie de lectura v0.2.0).

- **Mutating-gate opt-in (GATE-MD-01):** por default `Client()`/`AsyncClient()` rehúsan toda
  mutación con `MarketDataMutationNotAllowedError` (⊂ `MarketDataError`) **sin emitir request
  HTTP ni token Auth0**. Habilitación explícita vía `mutating_allowed=True` (constructor o
  `configure()`), más un segundo **gate de host exacto** (`expected_host`, comparación exacta
  de hostname — nunca substring) que impide mutar contra un `base_url` inesperado. El flag vive
  en el estado compartido, así que las vistas de `with_options()` lo heredan; `configure()` usa
  centinela `bool | None` para no resetear un opt-in previo al reconfigurar `base_url`.
- **Symbols write (MUT-MD-01):** `create_symbol` (`NewSymbol`), `create_symbols`
  (batch 1–500, `NewSymbols`) y `update_symbol` (`SymbolPatch`), en sync y async, con
  request-models tipados serializados a JSON y respuestas `SafeModel` tolerantes; `422`
  levanta error tipado. Las tres operaciones se despachan como idempotentes
  (`request.extensions["idempotent"]=True`) según el spec.
```

**Model B — naming a breaking model change while shipping a minor** (`README.md:90-103`) — the
precedent D-03 mandates for the `CalendarDay` callout. Reuse this voice verbatim in structure:

```markdown
### v0.2.0

**Breaking changes** (semver minor bump en línea 0.x) — reconciliación del cliente
contra la API en vivo tras la verificación `LIVE-MD-01`:

- `get_latest(symbol=...)` ahora es **requerido** (la API devuelve 422 sin él).
- `MarketDataSnapshot` reconciliado contra el wire de develop: `marketId` → `market_id`;
  agregados `active`, `market_data`, `staleness_seconds`, `note`; se retiró el
  `MarketDataEntry` inventado.
- `CalendarConfig` reconciliado: se eliminó `businessDays`; se agregaron `open`, `close`,
  `enabled`, `editable`, `env_bypass`, `pre_open_minutes`, `source`, `updated_at`,
  `updated_by`, `warnings`.
- Corregido el envelope-unwrap de `parse_market_data_response` (`get_market_data` ahora
  lee `items[]`).
```

**Model C — patch bump lead line** (`README.md:64`), for contrast on bump-class naming:

```markdown
**Bugfix (patch):** `get_latest_batch` devolvía snapshots vacíos.
```

**Conventions locked by these three entries** (hold all of them):

- Spanish prose throughout.
- `### vX.Y.Z` H3 heading, blank line, **bold lead line naming the bump class**, then a
  parenthetical semver justification (may wrap to its own line, as in v0.3.0).
- Bullets lead with `- **<Área> (<REQ-ID>):**` — requirement ID inline in the bold lead.
- Every identifier in backticks; endpoint paths in backticks.
- Wrapped ~95-100 cols; **continuation lines indented exactly 2 spaces**.
- Blank line between the heading and body, and between entries.
- `trailing-whitespace` + `end-of-file-fixer` pre-commit hooks run over this file in CI.

**Required content for `### v0.4.0`** (from RESEARCH § Public Surface Delta):

- 13 new public names — 8 flat `__all__` additions (`MarketHoursIn`, `HolidayIn`, `HolidaysIn`,
  `set_calendar_config`, `delete_calendar_config`, `preview_calendar_config`, `add_holidays`,
  `delete_holiday`) + 5 `aio` counterparts — cite `(MUT-MD-02)`.
- The Phase 27 live-verified fixes — cite `(LIVE-MUT-01)`: `update_symbol(symbol_id)` widened
  `str` → `int | str` at all 4 routes; `Symbol` gains 5 defaulted fields
  (`id`, `market_id`, `created_at`, `updated_at`, `received_at`); `Symbol.marketId` preserved as
  deprecated alias; symbols-write envelope unwrapped preserving `list[Symbol]`.
- **Non-negotiable (D-03):** an explicit `CalendarDay` field-replacement callout —
  `date` / `marketId` / `isBusinessDay` **removed**, replaced by `day` / `closed` /
  `description` / `open_time` / `close_time`. Use Model B's voice.

---

### 5. `uv.lock` (config, generated)

**Current state** (`uv.lock:486-489`):

```toml
[[package]]
name = "market-data-client"
version = "0.3.1"
source = { editable = "packages/market-data-client" }
```

**Analog diff** (`7f051ae`) — exactly 2 lines of churn, nothing else:

```diff
 [[package]]
 name = "market-data-client"
-version = "0.3.0"
+version = "0.3.1"
 source = { editable = "packages/market-data-client" }
```

**Apply:** run `uv lock` (never hand-edit), then assert `git diff --stat uv.lock` reads
`uv.lock | 2 +-` exactly (P-9). Order is strict: pyproject bump → `uv lock` → `uv lock --check`.

---

### 6. `.claude/projects/…/memory/market-data-client-releases.md` — **6 regions**

**Analog:** `ce77ed4` — `docs(memory): update market-data-client latest release to v0.3.1`
(+24/−14 across six regions). Body of that commit message:

```
get_latest_batch envelope fix; remove the now-fixed WR-01 known-gap note;
refresh install commands + demote v0.3.0 to prior releases.
```

**CRITICAL (RESEARCH C-3):** CONTEXT.md D-04 names only 2 of these regions. All 6 must change.

#### Region 1 — frontmatter `description:` (L3)

Current:
```yaml
description: market-data-client latest published release is v0.3.1 (patch — get_latest_batch envelope-unwrap fix, on top of v0.3.0 symbols write + mutating-gate). v0.2.0/v0.3.0 superseded; v0.1.0 buggy. Install via git subdirectory or the GitHub Release wheel — not on PyPI.
```
Analog transformation (`ce77ed4`) — full single-line rewrite naming the new version, its bump
class + headline, then the superseded list:
```diff
-description: market-data-client latest published release is v0.3.0 (symbols write + mutating-gate, non-breaking over v0.2.0 read surface). v0.2.0 read-only superseded; v0.1.0 buggy. Install via …
+description: market-data-client latest published release is v0.3.1 (patch — get_latest_batch envelope-unwrap fix, on top of v0.3.0 symbols write + mutating-gate). v0.2.0/v0.3.0 superseded; v0.1.0 buggy. Install via …
```

#### Region 2 — `**Latest published:**` block (L13-15)

Current:
```markdown
**Latest published: `market-data-client-v0.3.1`** (2026-08-01, tag on merge commit `7b0e0b2`,
PR #9, `release.yml` run `30674988499`). This is the release to install. It is a **patch** over
v0.3.0 — one bug fix, no API change.
```
Analog transformation:
```diff
-**Latest published: `market-data-client-v0.3.0`** (2026-07-31, tag on merge commit `ea92dd8`,
-PR #8, `release.yml` run `30673218876`). This is the release to install. It is a **non-breaking
-minor** over v0.2.0 — it only ADDS the first mutation surface behind an opt-in safety gate; the
-v0.2.0 read surface is unchanged.
+**Latest published: `market-data-client-v0.3.1`** (2026-08-01, tag on merge commit `7b0e0b2`,
+PR #9, `release.yml` run `30674988499`). This is the release to install. It is a **patch** over
+v0.3.0 — one bug fix, no API change.
```
> Cites the merge-commit SHA, the PR number, **and the `release.yml` run ID** — none of which
> exist until after the tag push. See § Sequencing below.

#### Region 3 — version-specific "what it adds/fixes" section (L17-37)

Analog transformation — a new lead section is added for the new version, and the previous lead
section is **retitled with a "carried forward into" suffix**:
```diff
-**v0.3.0 adds (v1.5 Phase 25 — GATE-MD-01 + MUT-MD-01):**
+**v0.3.1 fixes (quick task `260731-t9o`):** `get_latest_batch` returned empty `MarketDataSnapshot`s.
+`parse_latest_response` (`_core.py`, shared by sync + async) assumed the batch
+`POST /marketdata/latest` returned a bare list, but the server returns an envelope
+… Two mis-mocked client-level batch tests (which hid the bug) were corrected to the real envelope.
+
+**v0.3.0 added (v1.5 Phase 25 — GATE-MD-01 + MUT-MD-01), carried forward into v0.3.1:**
```
For v0.4.0: add a `**v0.4.0 adds (v1.5 Phases 26-27 — MUT-MD-02 + LIVE-MUT-01):**` lead section
(calendar write surface + live-verified fixes + the `CalendarDay` field swap), and retitle the
existing v0.3.1/v0.3.0 sections as "carried forward into v0.4.0". English prose in this file
(unlike the README changelog, which is Spanish).

#### Region 4 — **two** "Scope note" paragraphs (L39-46) — HIGHEST RISK

Both are **factually false after v0.4.0** (Phases 26 and 27 are complete). Current text:
```markdown
**Scope note:** v0.3.0 carries **symbols-write only**. Calendar mutations (MUT-MD-02, Phase 26) and
the live verification (LIVE-MUT-01, Phase 27) were NOT yet done when v0.3.0 shipped — it was released
early on explicit operator request, out of the planned Phase-28 order. Symbols mutations have only
been exercised against mocked tests, never live develop. Calendar write would land as a later minor.

**Scope note (still true):** the mutation surface is **symbols-write only**. Calendar mutations
(MUT-MD-02, Phase 26) and the live mutation verification (LIVE-MUT-01, Phase 27) are NOT yet done.
Symbols mutations have only been exercised against mocked tests, never live develop.
```
Precedent for replacing a stale note wholesale (`ce77ed4` retired the WR-01 known-gap paragraph):
```diff
-**Known read-path gap (pre-existing, unfixed as of v0.3.0):** `parse_latest_response` (`get_latest`)
-still lacks the dict-envelope unwrap + `isinstance` guard … fix deferred to the live reconciliation
-(Phase 27) since the correct shape needs live confirmation.
+**Scope note (still true):** the mutation surface is **symbols-write only**. Calendar mutations
+(MUT-MD-02, Phase 26) and the live mutation verification (LIVE-MUT-01, Phase 27) are NOT yet done.
+Symbols mutations have only been exercised against mocked tests, never live develop.
```
**Apply:** delete/replace both paragraphs with a single accurate scope note — the mutation surface
is now symbols **+ calendar**, and both have been exercised live against develop (LIVE-MUT-01).

#### Region 5 — `**Prior releases:**` paragraph (L48-53)

Analog transformation — the previous "latest" is **demoted into the head of this paragraph** with
its date/tag/PR, and the trailing "vX keeps all of this" sentence is re-versioned:
```diff
-**Prior releases:** `v0.2.0` (2026-07-31) = read surface reconciled against live develop (LIVE-MD-01):
+**Prior releases:** `v0.3.0` (2026-07-31, tag `ea92dd8`, PR #8) = first mutation surface (symbols
+write + mutating-gate) — superseded by v0.3.1 which fixes the `get_latest_batch` read bug.
+`v0.2.0` (2026-07-31) = read surface reconciled against live develop (LIVE-MD-01):
 `get_latest(symbol=…)` required; `MarketDataSnapshot` `marketId`→`market_id` + …
-v0.3.0 keeps all of this. **`v0.1.0` is superseded/buggy** …
+v0.3.1 keeps all of this. **`v0.1.0` is superseded/buggy** …
```

#### Region 6 — **both** install command lines (L56-57) — HIGH CONSEQUENCE

Current:
```markdown
**Install (repo is PUBLIC, no auth needed):**
- git, pinned to tag (recommended): `uv add "market-data-client @ git+https://github.com/gravity-quant/market-libs.git@market-data-client-v0.3.1#subdirectory=packages/market-data-client"` (pip: `pip install "git+…@market-data-client-v0.3.1#subdirectory=packages/market-data-client"`).
- release wheel: `pip install "https://github.com/gravity-quant/market-libs/releases/download/market-data-client-v0.3.1/market_data_client-0.3.1-py3-none-any.whl"`.
```
Analog transformation — **three** version tokens change (git tag ×2 in line 1, tag + wheel
filename in line 2):
```diff
-- git, pinned to tag (recommended): `uv add "… @market-data-client-v0.3.0#subdirectory=…"` (pip: `pip install "git+…@market-data-client-v0.3.0#subdirectory=…"`).
+- git, pinned to tag (recommended): `uv add "… @market-data-client-v0.3.1#subdirectory=…"` (pip: `pip install "git+…@market-data-client-v0.3.1#subdirectory=…"`).
-- release wheel: `pip install "…/download/market-data-client-v0.3.0/market_data_client-0.3.0-py3-none-any.whl"`.
+- release wheel: `pip install "…/download/market-data-client-v0.3.1/market_data_client-0.3.1-py3-none-any.whl"`.
```
Leaving these stale makes the memory instruct future agents to install the superseded version (P-8).

**Regions NOT touched by `ce77ed4`** (leave alone): the intro paragraph (L8-11), the "Runtime
config (env / .env)" block (L59-62), and the `Related: [[phase-23-wave2-pending-creds]]` line (L64).

#### Sequencing consequence

`ce77ed4` is a **separate commit landed AFTER the release** (`7b0e0b2`), on
`milestone/v1.5-mutations`, and shipped in the *next* PR. The memory file cannot cite a
`release.yml` run ID that does not yet exist. **Recommendation (matches precedent exactly):**
defer site 5 entirely to a final Plan 02 task, after `gh release view` succeeds, committed to
`milestone/v1.5-mutations` with message shape
`docs(memory): update market-data-client latest release to v0.4.0`.

---

### 7. `.planning/REQUIREMENTS.md` — D-02 re-point (doc, in-place)

**Site 1 — L28** (current):
```markdown
- [ ] **PUB-MUT-01**: `market-data-client` se publica como `v0.3.0` (minor bump — features nuevas, no rompe la superficie de lectura v0.2.0) por el pipeline de tags — bump `pyproject`+`__version__`, README changelog, `uv.lock` refresh, CI verde, PR → merge → tag `market-data-client-v0.3.0` → GitHub Release con wheel + sdist
```
Two `v0.3.0` tokens → `v0.4.0`; add the constancia that `v0.3.0`/`v0.3.1` shipped mid-milestone.
Sibling checked rows on the same list (L20-24) show the `- [x] **REQ-ID**: …` completion form.

**Site 2 — L65**, the mapping table (current):
```markdown
| PUB-MUT-01 | Phase 28 | Pending |
```
Same-table analogs immediately above: `| LIVE-MUT-01 | Phase 27 | Complete |`. Flip to `Complete`
at phase close.

---

### 8. `.planning/ROADMAP.md` — D-02 re-point + D-16 backlog entry (doc, in-place)

**Site 1 — L19** (current):
```markdown
- [ ] **Phase 28: Release prep + publish v0.3.0** — bump minor + README changelog + PR → tag `market-data-client-v0.3.0` → GitHub Release — PUB-MUT-01
```
Sibling completed-phase form on L15-16: `- [x] **Phase 25: …** — … — GATE-MD-01 + MUT-MD-01 (completed 2026-07-31)`.

**Site 2 — L188-198**, the Phase 28 detail block (current, with the stale `v0.3.0` in the heading,
Goal, SC#1, SC#3 and SC#4):
```markdown
### Phase 28: Release prep + publish v0.3.0

**Goal**: `market-data-client` se publica como `v0.3.0` (minor bump, no breaking sobre la superficie de lectura v0.2.0) por el pipeline de tags.
**Depends on**: Phase 27 (la superficie de mutación verificada en vivo)
**Requirements**: PUB-MUT-01
**Success Criteria** (what must be TRUE):

  1. Versión bumpeada a `0.3.0` en `pyproject` + `__version__`; README changelog documenta las nuevas mutaciones + el opt-in del gate; `uv.lock` refrescado.
  2. PR abierto; los 15 checks de CI verdes (incl. los jobs de `market-data-client` en la matrix py3.12 + py3.13).
  3. Merge a `main`; tag `market-data-client-v0.3.0` empujado → `release.yml` (unedited) → GitHub Release con wheel + sdist.
  4. El bump es minor no-breaking: la superficie de lectura v0.2.0 permanece 100% compatible.
```
> Keep the **section heading** `### Phase 28: Release prep + publish v0.3.0` decision explicit —
> the directory name is `28-release-prep-publish-v0-3-0` and GSD tooling keys off it. Re-point the
> Goal + SC#1/#3 version strings; SC#4's baseline should read against **v0.3.1**, not v0.2.0, and
> should acknowledge the D-03 `CalendarDay` carve-out.

**Site 3 — `§ Backlog` (L235+)**, D-16 entry. Existing bullet formatting to match
(`ROADMAP.md:241-245`):
```markdown
### Deferred to v1.5+ (from v1.4 — market-data-client v2 requirements)

- **MUT-MD-01 / MUT-MD-02** — market-data-client mutations: symbols (`POST /symbols`, …) + calendar (`PUT/DELETE /calendar/config`, …) — require the security mutating-gate
- **STREAM-MD-01** — market-data-client SSE streaming (`GET /marketdata/stream`, `interval` param) via a dedicated transport (matriz `ws_client` pattern)
- **SEC-MD-01** — market-data-client Auth0 token disk cache (`_token_cache.py` + platformdirs, atomic + flock + 0600)
```
Pattern: `- **<ID or short title>** — <description with backticked identifiers/paths> — <qualifier>`.
Add a **`### Deferred to v1.6+ (from v1.5)`** subsection with the D-16 item: enroll
`market-data-client` in the root mypy `files` (`pyproject.toml:97`), import-linter `root_packages`
(`pyproject.toml:141-146`), and the per-package mypy-tests loop (`ci.yml:85`) — requires authoring
an import-linter contract for `market_data_client._core`. Deferred since Phase 24; **not** a CI
failure. The `REFAC-06` bullet (L253) is the model for a long-form deferral entry with rationale.

---

### 9. Plan documents — `24-01-PLAN.md` / `24-02-PLAN.md` (recovered from `b07a924`)

> Both deleted from the working tree during milestone cleanup. Recover with
> `git show b07a924:.planning/phases/24-release-prep-publish-v0-1-0/24-0N-PLAN.md`.
> This is the **exact** two-plan shape RESEARCH § Pattern 1 prescribes for Phase 28.

#### 9a. Plan 01 frontmatter (reversible prep, wave 1, autonomous)

```yaml
---
phase: 24-release-prep-publish-v0-1-0
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .github/workflows/ci.yml
  - CLAUDE.md
  - .claude/projects/-Users-admin-development-market-libs/memory/MEMORY.md
  - .claude/projects/-Users-admin-development-market-libs/memory/market-data-client-v0.1.0-published.md
autonomous: true
requirements: [PUB-MD-01]

must_haves:
  truths:
    - "The CI test matrix runs market-data-client (2 jobs: py3.12 + py3.13) — implements PUB-MD-01, D-01"
    - "uv.lock has zero drift and the package version is aligned at 0.1.0 across pyproject + __version__ — D-03, D-11, SC-1"
  artifacts:
    - path: ".github/workflows/ci.yml"
      provides: "market-data-client entry in matrix.package"
      contains: "- market-data-client"
  key_links:
    - from: ".github/workflows/ci.yml"
      to: "packages/market-data-client"
      via: "matrix.package entry drives `pytest packages/market-data-client` with coverage in the test job"
      pattern: "market-data-client"
---
```

For Phase 28, `files_modified` becomes the 7 sites (pyproject, `__init__.py`, README, `uv.lock`,
REQUIREMENTS.md, ROADMAP.md — and NOT the memory file if site 5 is deferred to Plan 02 per § 6).

#### 9b. Plan 01 `<scope_decisions>` block — the D-16 deferral precedent

Phase 24 recorded the *identical* deferral. Reuse this block, updated to note it is now archived
in the v1.6 backlog per D-16:

```xml
<scope_decisions>
Conscious deferrals surfaced from 24-PATTERNS.md "Watch-outs" — recorded here so the executor
and verifier see the decision rather than treating it as an accidental gap. …
- Global mypy `files` (`pyproject.toml:97`) — does not list `market-data-client/src`. Skipping it
  is a typecheck COVERAGE gap, not a CI failure (the job stays green). Out of D-01/D-11 scope.
- `importlinter` `root_packages` (`pyproject.toml:141-146`) — 4-package list, unchanged. Out of scope.
- CI `typecheck` per-package tests-mypy loop (`ci.yml:85`) — hardcoded 5-package list, unchanged. …
Rationale: none of these break the CI gate for the new package; full typecheck/import-linter
parity is a scope expansion beyond CONTEXT D-01/D-11. Do not edit unless the user reopens scope.
</scope_decisions>
```

#### 9c. Plan 01 validate-only task shape (Task 3 of `24-01-PLAN.md`)

```xml
<task type="auto">
  <name>Task 3: Validate uv.lock, version alignment, and root workspace member (D-03, D-11, SC-1)</name>
  <files>uv.lock, pyproject.toml, packages/market-data-client/pyproject.toml, packages/market-data-client/src/market_data_client/__init__.py</files>
  <read_first>…</read_first>
  <action>…(a) Run `uv sync --all-packages --all-extras --dev --frozen` — must exit 0 (no lock drift).
    (b) Run `uv lock --check` — must exit 0 (exactly what ci.yml runs). …
    If (a) or (b) reports drift, STOP and surface it (do not silently regenerate)…</action>
  <verify>
    <automated>uv sync --all-packages --all-extras --dev --frozen && uv lock --check && grep -qx 'version = "0.1.0"' <(sed -n '3p' packages/market-data-client/pyproject.toml) && grep -q '__version__ = "0.1.0"' packages/market-data-client/src/market_data_client/__init__.py && grep -q 'market-data-client = { workspace = true }' pyproject.toml && grep -q '"market-data-client"' uv.lock && echo PASS</automated>
  </verify>
  <acceptance_criteria>…</acceptance_criteria>
  <done>Lockfile has no drift, package version is aligned at 0.1.0 …</done>
</task>
```

**Phase 28 differs:** this is a **regenerate** step, not validate-only — `uv lock` MUST run after
the pyproject bump. Use RESEARCH's three-way assertion instead:

```bash
V=$(awk -F\" '/^version[[:space:]]*=/{print $2; exit}' packages/market-data-client/pyproject.toml)
test "$V" = "0.4.0" \
  && grep -qx '__version__ = "0.4.0"' packages/market-data-client/src/market_data_client/__init__.py \
  && grep -A1 '^name = "market-data-client"$' uv.lock | grep -qx 'version = "0.4.0"' \
  && grep -qx '### v0.4.0' packages/market-data-client/README.md \
  && uv lock --check >/dev/null 2>&1 \
  && echo PASS
```

#### 9d. Plan 02 frontmatter (irreversible publish, wave 2, `autonomous: false`)

```yaml
---
phase: 24-release-prep-publish-v0-1-0
plan: 02
type: execute
wave: 2
depends_on: [24-01]
files_modified: []
autonomous: false
requirements: [PUB-MD-01]
user_setup:
  - service: github
    why: "Merging the PR and pushing the release tag are outward-facing GitHub operations"
    dashboard_config:
      - task: "Ensure `gh` CLI is authenticated (verified in Task 1)"
        location: "local shell — `gh auth status`"

must_haves:
  truths:
    - "A single PR release/v0.2.0-bump → main is open, carrying the whole market-data-client package (Phases 20-23) plus this phase's edits, with .planning/ artifacts kept (D-06, D-07)"
    - "All CI checks on the PR are green, including the new market-data-client test jobs (SC-3)"
    - "The PR is merged to main only after an explicit human go/no-go at the merge point (D-08, D-09)"
    - "A tag market-data-client-v0.1.0 exists on the merge commit and triggers release.yml (D-10)"
    - "A GitHub Release market-data-client-v0.1.0 exists with wheel + sdist assets (SC-4)"
  artifacts:
    - path: "git-tag:market-data-client-v0.1.0"
      provides: "per-package release tag on the merge commit (verified via `git tag` + `git rev-list`)"
      contains: "market-data-client-v0.1.0"
    - path: "gh-release:market-data-client-v0.1.0"
      provides: "GitHub Release with wheel + sdist assets (verified via `gh release view`)"
      contains: ".whl"
  key_links:
    - from: "git-tag:market-data-client-v0.1.0"
      to: ".github/workflows/release.yml"
      via: "tag matching `*-client-v*` triggers release.yml which builds wheel+sdist and creates the Release"
      pattern: "market-data-client-v0.1.0"
---
```

Note the `artifacts` entries use the pseudo-paths `git-tag:<tag>` and `gh-release:<tag>` — reuse
that convention with `market-data-client-v0.4.0`.

#### 9e. Plan 02 `<objective>` voice

```xml
<objective>
Execute the release: open the PR, confirm CI is green, and — only after an explicit human
go/no-go at the merge point — perform the two IRREVERSIBLE, outward-facing operations (merge to
main, push the release tag). The tag triggers the generic `release.yml`, producing the GitHub
Release with wheel + sdist. No package code changes; no release.yml edit (D-02).

Purpose: Ship market-data-client v0.1.0 through the same per-package pipeline as the other five
packages (D-08).
Output: Merged PR on main, tag `market-data-client-v0.1.0` on the merge commit, GitHub Release
with wheel + sdist.

This plan is `autonomous: false`: the merge and tag push are irreversible and gated by a
blocking human checkpoint (D-09). Requires a clean working tree and authenticated `gh`.
</objective>
```

#### 9f. Plan 02 blocking checkpoint task — **the template** (D-18)

```xml
<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 2: Blocking go/no-go gate before irreversible merge + tag (D-09)</name>
  <action>PAUSE. This is a blocking human checkpoint (autonomous:false). Do NOT merge the PR or push any tag until the operator explicitly replies "approved". If "abort", stop cleanly with no irreversible action taken. Present the PR link, `gh pr checks` status, and the exact tag string to be published.</action>
  <what-built>
    A PR (`release/v0.2.0-bump` → `main`) is open with ALL CI checks green, including the new
    market-data-client test matrix jobs (py3.12 + py3.13). The working tree is clean and `gh` is
    authenticated. The next task will perform two IRREVERSIBLE, outward-facing operations:
    (1) merge the PR into `main`, and (2) push the tag `market-data-client-v0.1.0` on the merge
    commit, which triggers `release.yml` and creates a public GitHub Release.
  </what-built>
  <how-to-verify>
    1. Review the open PR on GitHub (title, diff scope: whole market-data-client package + Phase 24
       edits + .planning artifacts).
    2. Confirm CI is green: `gh pr checks` shows all required checks passing, including
       `market-data-client`.
    3. Confirm the intended tag string is EXACTLY `market-data-client-v0.1.0` (per-package format,
       D-10) — this is what will be published; a wrong/malformed tag would trigger an unintended
       Release.
    4. Confirm you authorize the irreversible merge + tag push now (D-09 final go/no-go).
  </how-to-verify>
  <resume-signal>Type "approved" to proceed with merge + tag, or "abort" (optionally describe blockers) to stop before any irreversible action.</resume-signal>
</task>
```

> **D-18 splits this into TWO checkpoints** — one before `gh pr merge`, one before
> `git push origin <tag>`. Phase 24 used a single combined gate. **Do not collapse them back.**
> Checkpoint (b)'s `<what-built>` must state the captured `MERGE_SHA` and that it has two parents.

#### 9g. Plan 02 irreversible-ops task (Task 3 of `24-02-PLAN.md`)

```xml
<task type="auto">
  <name>Task 3: Merge PR, tag the merge commit, and verify the GitHub Release (D-08, D-10, SC-4)</name>
  <files>(git/gh operations — no working-tree files modified)</files>
  <action>
    Execute ONLY after Task 2 returned "approved". These are the irreversible steps (D-08):
    (a) Merge the PR into `main` via `gh pr merge` … Capture the resulting merge commit SHA on `main`.
    (b) On the merge commit SHA, create the tag with the EXACT per-package format
    `market-data-client-v0.1.0` (D-10 — no other string; it must match release.yml's
    `^([a-z][a-z0-9-]*-client)-v([0-9]+\.[0-9]+\.[0-9]+...)$` regex and the `*-client-v*` trigger).
    Push the tag to origin. This is the second irreversible action and triggers `release.yml`.
    (c) Wait for `release.yml` to complete, then confirm the GitHub Release … exists with BOTH a
    `.whl` (wheel) and a `.tar.gz` (sdist) asset via `gh release view`. Do NOT re-create or edit
    `release.yml` (D-02). Never echo the `gh` token or any credential to logs.
  </action>
  <verify>
    <automated>git fetch --tags origin >/dev/null 2>&1; git tag | grep -qx 'market-data-client-v0.1.0' && git rev-list -n1 market-data-client-v0.1.0 >/dev/null && gh release view market-data-client-v0.1.0 --json assets 2>/dev/null | grep -q '\.whl' && gh release view market-data-client-v0.1.0 --json assets 2>/dev/null | grep -q '\.tar\.gz' && echo PASS</automated>
  </verify>
  <done>PR merged to main; tag market-data-client-v0.1.0 on the merge commit; GitHub Release published with wheel + sdist.</done>
</task>
```

#### 9h. Plan 02 `<threat_model>` rows (reuse, re-numbered T-28-*)

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-24-03 | Tampering / Spoofing | git tag / release.yml trigger | mitigate | Tag string is the EXACT literal `market-data-client-v0.1.0` created on the verified merge-commit SHA; Task 3 verify asserts `git rev-list` resolves the tag and it matches release.yml regex + version-match gates — a wrong/malformed tag cannot silently publish |
| T-24-04 | Elevation of Privilege / Repudiation | PR merge + tag push (irreversible) | mitigate | Blocking human `checkpoint:human-verify` (Task 2, D-09) requires explicit "approved" before ANY irreversible action; abort path stops cleanly |
| T-24-05 | Information Disclosure | PR body / Release notes / `gh` token | mitigate | PR body carries no secrets; Release notes are `--generate-notes`; the `gh` token is never echoed to logs; clean working tree ensures no `.env` is committed |
| T-24-06 | Tampering | merge with un-green CI | mitigate | Task 1 gates on `gh pr checks` all-green before the merge checkpoint is even reached |
| T-24-SC | Tampering | uv/pip/cargo installs | accept | No new package installs — release.yml builds from the already-validated lockfile; no new dependency introduced |

> **Upgrade T-24-06 for Phase 28:** RESEARCH C-2 proved `main` has **no branch protection**
> (`protected: false`, empty rulesets). `gh pr merge --merge` succeeds against a red or pending PR.
> The 15-green gate is advisory, so the checkpoint is the only enforcement point.

#### 9i. Plan 01/02 shared boilerplate (identical in both Phase 24 plans)

```xml
<execution_context>
@/Users/admin/development/market-libs/.claude/gsd-core/workflows/execute-plan.md
@/Users/admin/development/market-libs/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/ROADMAP.md
@.planning/phases/24-release-prep-publish-v0-1-0/24-CONTEXT.md
@.planning/phases/24-release-prep-publish-v0-1-0/24-PATTERNS.md
</context>
```
…and the closing blocks, in order: `<threat_model>`, `<verification>`, `<success_criteria>`,
`<output>` (`Create .planning/phases/…/24-0N-SUMMARY.md when done.`). Plan 01 also carries
`<artifacts_this_phase_produces>` and `<scope_decisions>`.

---

## Shared Patterns

### S-1. Version-token replacement discipline

**Source:** `7f051ae` (4 sites) + `ce77ed4` (6 regions)
**Apply to:** every file in this phase

One release bump touches **10 distinct version tokens** across 5 files. Three are structurally
easy to miss and each has a real downstream consequence:

| Token | File | Missed → |
|-------|------|----------|
| `__version__` | `__init__.py:134` | `release.yml` validates only `pyproject.toml` (`:47`) — silent drift, undetectable at release time (P-4) |
| memory install lines (×3 tokens) | release memory L56-57 | future agents install the superseded version (P-8) |
| memory "Scope note" ×2 | release memory L39-46 | the artifact asserts Phases 26/27 are "NOT yet done" — false (P-8) |

### S-2. Assert, don't glance

**Source:** RESEARCH § Release Mechanics; improved over `24-02-PLAN.md` Task 1
**Apply to:** every `<verify><automated>` in both plans

Phase 24's gate was:
```bash
gh pr checks 2>/dev/null | grep -qi 'market-data-client' \
  && ! gh pr checks 2>/dev/null | grep -qiE '\bfail'
```
This passes when checks are **pending**, **cancelled**, or when `gh pr checks` returns nothing.
Given C-2 (no branch protection), replace with the explicit count assertion:
```bash
PR=$(gh pr view --json number --jq .number)
TOTAL=$(gh pr checks "$PR" | wc -l | tr -d ' ')
PASSED=$(gh pr checks "$PR" | awk -F'\t' '$2=="pass"' | wc -l | tr -d ' ')
MD=$(gh pr checks "$PR" | grep -c 'Tests · market-data-client · py3\.1[23]')
test "$TOTAL" = "15" && test "$PASSED" = "15" && test "$MD" = "2" && echo PASS
```

### S-3. Scoped test invocations only (D-14 / P-5)

**Apply to:** every test command in both plans

Never a bare `uv run pytest` — the root `testpaths` includes `verification/`, which carries 19
pre-existing matriz failures that CI never sees. Always:
```bash
uv run pytest packages/market-data-client -q     # expect: 387 passed
```

### S-4. Local mirror of the CI gate (D-15 baseline, all green 2026-08-01)

```bash
uv lock --check
uv run ruff check .            # "All checks passed!"
uv run ruff format --check .   # "201 files already formatted"
uv run lint-imports            # "Contracts: 4 kept, 0 broken"
uv run mypy                    # "Success: no issues found in 51 source files"
uv run pytest packages/market-data-client -q   # 387 passed
uv run pre-commit run --all-files
```

### S-5. Commit-message conventions on this branch

| Kind | Shape | Example |
|------|-------|---------|
| version bump | `chore(market-data-client): bump to vX.Y.Z (<scope>)` | `7f051ae` |
| memory update | `docs(memory): update market-data-client latest release to vX.Y.Z` | `ce77ed4` |
| planning artifact | `docs(NN): <what>` / `docs(state): <what>` | `773e1ca`, `6bbf2ce` |

All carry `Co-Authored-By:` + `Claude-Session:` trailers.

### S-6. Files explicitly NOT to touch

| File | Why | Decision |
|------|-----|----------|
| `.github/workflows/ci.yml` | already lists `market-data-client` in `matrix.package` (`:103`) | D-06 |
| `.github/workflows/release.yml` | regex `:28` already matches `market-data-client-v0.4.0`; generic | D-06 |
| `CLAUDE.md:74` | still says `v0.2.0`; no prior release commit touched it (`ea92dd8`, `7b0e0b2` stats confirm) — generated artifact, known doc debt | D-07 |
| `pyproject.toml` (root) mypy `files` / import-linter `root_packages` | deferred since Phase 24 | D-16 (archive in backlog only) |
| release-memory intro (L8-11), runtime-config block (L59-62), `Related:` line (L64) | untouched by `ce77ed4` | — |

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `git push origin milestone/v1.5-mutations` (C-1 step) | ops | — | No prior release plan contains a branch-push step — Phase 24 shipped from a freshly-created `release/v0.2.0-bump` branch that `gh pr create` pushed implicitly. Phase 28's branch is 96 commits stale on origin, so the push must be an **explicit named step** at the end of Plan 01, before any `gh pr create`. Plain fast-forward; `--force` forbidden. |
| Two-checkpoint split (D-18a + D-18b) | plan structure | — | Phase 24 used a **single** combined gate (§ 9f). No analog exists for splitting merge and tag into separate blocking gates; derive the second from the first, with `MERGE_SHA` + two-parent verification in `<what-built>`. |

---

## Metadata

**Analog search scope:** `git log` on `milestone/v1.5-mutations` (release commits `7f051ae`,
`ce77ed4`, merge commits `ea92dd8`, `7b0e0b2`); `git show b07a924:` and `f79d350:` for the deleted
Phase 24 plan/summary documents; `packages/market-data-client/{README.md,pyproject.toml,src/**/__init__.py}`;
`.claude/projects/…/memory/market-data-client-releases.md`; `.planning/{REQUIREMENTS,ROADMAP}.md`;
`uv.lock`.
**Files scanned:** 9 on disk + 4 recovered from git history
**Pattern extraction date:** 2026-08-01
