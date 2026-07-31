# Phase 24: Release prep + publish v0.1.0 - Pattern Map

**Mapped:** 2026-07-31
**Files analyzed:** 6 (2 to edit, 1 to update, 3 verify-only/reference)
**Analogs found:** 6 / 6 (all analogs are existing per-package entries for the other 5 packages)

> **Nature of this phase.** No new functional code. The "new file" being produced is the
> **6th package's row** in each shared config/doc surface. Every analog is an *existing
> sibling entry* (iol / higyrus / matriz / wallets / ambito) that the `market-data-client`
> entry must replicate verbatim in format. Be mechanical: match the existing column order,
> punctuation, and wording exactly.

## File Classification

| File | Role | Change type | Data flow | Closest analog | Match quality |
|------|------|-------------|-----------|----------------|---------------|
| `.github/workflows/ci.yml` | config (CI) | **EDIT** (D-01) | list-append | existing `matrix.package` entries (ci.yml:98-102) | exact |
| `CLAUDE.md` (Workspace Structure) | doc | **EDIT** (D-04) | list-append | existing per-package rows (CLAUDE.md:69-73) | exact |
| `CLAUDE.md` (Component Responsibilities) | doc | **EDIT** (D-04) | table-row-append | existing table rows (CLAUDE.md:167-171) | exact |
| `.claude/.../memory/MEMORY.md` (+ pointer file) | doc/index | **UPDATE** (D-05) | index-append | existing bullet + `phase-23-wave2-pending-creds.md` frontmatter | exact |
| `pyproject.toml` (root) | config | **VERIFY** (D-11) | none — already registered | `[tool.uv.sources]` block | already done |
| `packages/market-data-client/pyproject.toml` | config | **VERIFY** (SC-1) | none | — | already `0.1.0` |
| `packages/market-data-client/src/market_data_client/__init__.py` | config | **VERIFY** (SC-1) | none | — | already `0.1.0` |
| `uv.lock` | lockfile | **VALIDATE** (D-03) | none — regen-check | — | already contains entry |
| `.github/workflows/release.yml` | config (CI) | **REFERENCE ONLY** (D-02) | tag→release | — | no edit — regex already matches |

---

## Pattern Assignments

### 1. `.github/workflows/ci.yml` — add `market-data-client` to test matrix (D-01)

**This is the ONLY workflow file that gets edited.** Insertion point: the `matrix.package`
list inside the `test:` job.

**Current content** (`.github/workflows/ci.yml:91-103`):
```yaml
  test:
    name: Tests · ${{ matrix.package }} · py${{ matrix.python-version }}
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        package:
          - higyrus-client
          - wallets-client
          - matriz-client
          - iol-client
          - ambito-financiero-client
        python-version: ["3.12", "3.13"]
```

**Required change** — append one list item (2-space list indent, `- ` bullet, matching the
existing 5). Order is not enforced; appending at the end is consistent with how the list grew:
```yaml
        package:
          - higyrus-client
          - wallets-client
          - matriz-client
          - iol-client
          - ambito-financiero-client
          - market-data-client        # <-- NEW (Phase 24 D-01)
        python-version: ["3.12", "3.13"]
```

Effect: adds 2 test jobs (py3.12 + py3.13) that run `pytest packages/market-data-client`
with coverage. No other block in `ci.yml` needs edits per D-01 — **but see Watch-outs below**
for the `typecheck` job's per-package mypy loop.

---

### 2. `CLAUDE.md` — Workspace Structure list (D-04)

**Analog:** the existing 5 package bullets. Note `wallets-client` is the closest *semantic*
analog for wording but the auth descriptor differs (market-data uses Auth0 client-credentials,
not a static Bearer).

**Current content** (`CLAUDE.md:68-73`):
```markdown
## Workspace Structure
- `packages/iol-client/` — `iol-client` v0.1.1 (Invertir Online, HTTP sync+async)
- `packages/higyrus-client/` — `higyrus-client` v0.1.1 (Higyrus financial ops, HTTP sync+async)
- `packages/ambito-financiero-client/` — `ambito-financiero-client` v0.1.1 (Ámbito Financiero, HTTP sync+async, no auth)
- `packages/wallets-client/` — `wallets-client` v0.1.0 (Wallets, HTTP sync+async, static Bearer token)
- `packages/matriz-client/` — `matriz-client` v0.1.1 (MATBA ROFEX Primary API, HTTP REST + WebSocket)
```

**Required new bullet** — same shape: `` `packages/<dir>/` — `<pkg>` v<ver> (<domain>, <transport>, <auth>) ``.
Version is `v0.1.0` (from pyproject). Suggested wording following the established pattern:
```markdown
- `packages/market-data-client/` — `market-data-client` v0.1.0 (Market data / primary-extractor, HTTP sync+async, Auth0 client-credentials)
```

Also update the adjacent CI/CD line that hardcodes the package count:
- `CLAUDE.md:83` currently reads `- Test matrix: 5 packages × 2 Python versions (3.12, 3.13)` →
  must become `6 packages`. (Consistency with D-01.)

---

### 3. `CLAUDE.md` — Component Responsibilities table (D-04)

**Analog:** the existing table rows. Columns: `Component | Responsibility | Key Files`.
Rows use the Python module name (underscore form) in backticks.

**Current content** (`CLAUDE.md:164-176`):
```markdown
## Component Responsibilities
| Component | Responsibility | Key Files |
|-----------|----------------|-----------|
| `ambito_financiero_client` | Public FX rate scraping (no auth) | `packages/ambito-financiero-client/src/ambito_financiero_client/client.py` |
| `higyrus_client` | Brokerage back-office (accounts, positions, movements) | `packages/higyrus-client/src/higyrus_client/client.py` |
| `iol_client` | IOL trading platform (quotes, instruments, OAuth) | `packages/iol-client/src/iol_client/client.py` |
| `matriz_client` | MATBA ROFEX Primary API (orders, market data, WS streaming) | `packages/matriz-client/src/matriz_client/client.py` |
| `wallets_client` | Internal wallets service (Bearer token, stub) | `packages/wallets-client/src/wallets_client/client.py` |
| `<pkg>.aio` | Async counterpart for ambito, higyrus, iol, wallets clients | `*/src/*/aio.py` |
| `matriz_client.ws_client` | WebSocket streaming (market data + execution reports) | `packages/matriz-client/src/matriz_client/ws_client.py` |
| `<pkg>.models` | Frozen safe-access dataclasses for API responses | `higyrus_client/models.py`, `matriz_client/models.py` |
| `<pkg>.exceptions` | Package-scoped exception hierarchy | `*/src/*/exceptions.py` |
| `<pkg>._params` / `<pkg>._parsing` | Internal serialization helpers | `higyrus_client/_params.py`, `ambito_financiero_client/_parsing.py` |
```

**Required new row** — insert a `market_data_client` row alongside the other client rows
(before the `<pkg>.aio` meta-row), matching column shape. Suggested:
```markdown
| `market_data_client` | Market data / primary-extractor (quotes, instruments, calendar, health; Auth0 client-credentials) | `packages/market-data-client/src/market_data_client/client.py` |
```

**Two adjacent meta-rows should also be updated to acknowledge the 6th package** (Claude's
discretion per CONTEXT — the wording is not locked, but consistency matters):
- `<pkg>.aio` row (`:172`) currently says "Async counterpart for ambito, higyrus, iol, wallets
  clients" — market-data-client also ships `aio.py` (confirmed: `__init__.py:39` imports
  `AsyncClient`), so it belongs in that enumeration.
- `<pkg>.models` row (`:174`) — market-data-client ships `models.py` (confirmed: `__init__.py:61-70`
  re-exports `CalendarConfig`, `Instrument`, `MarketDataSnapshot`, etc.), so it could be added
  to the example list.

**Public-surface facts for accurate wording** (from `__init__.py`, already read):
- Endpoints/functions: `get_health`, `get_health_feed`, `get_calendar`, `get_calendar_config`,
  `get_instruments`, `get_segments`, `get_symbols`, `get_latest`, `get_latest_batch`,
  `get_market_data`.
- Models: `CalendarConfig`, `CalendarDay`, `Instrument`, `LatestRequest`, `MarketDataEntry`,
  `MarketDataSnapshot`, `Segment`, `Symbol`.
- Exceptions: `MarketDataError` → `MarketDataAPIError` → `MarketDataAuthError`,
  `MarketDataRateLimitError` (mirrors the standard `<Pkg>ClientError` hierarchy).
- Dual surface: module-level sync (`import market_data_client`), class-based sync (`Client`),
  and async (`from market_data_client import aio` → `AsyncClient`).

---

### 4. MEMORY index + pointer (D-05)

**Location:** `.claude/projects/-Users-admin-development-market-libs/memory/`

**Index file** — `MEMORY.md` is a flat bullet list of pointers.
**Current content** (entire file, `MEMORY.md:1`):
```markdown
- [Phase 23 Wave 2 pending creds](phase-23-wave2-pending-creds.md) — live market-data verification paused; needs MARKET_DATA_* Auth0 creds + develop VPN before /gsd-execute-phase 23 resumes Wave 2
```

**Pointer-file format** — each linked `.md` uses YAML frontmatter then prose.
**Analog** (`phase-23-wave2-pending-creds.md` head):
```markdown
---
name: phase-23-wave2-pending-creds
description: Phase 23 Wave 2 (live market-data-client verification) is paused pending Auth0 credentials
metadata:
  type: project
---

<prose body...>
```

**Required update** — add/refresh a pointer reflecting the **published** package. Two moves:
1. Add a new bullet to `MEMORY.md` index, e.g.
   `- [market-data-client v0.1.0 published](market-data-client-v0.1.0-published.md) — 6th monorepo package released via per-package tag market-data-client-v0.1.0; CI matrix + CLAUDE.md updated Phase 24`
   with a companion pointer file using the frontmatter shape above (`name`, `description`,
   `metadata.type: project`).
2. Note that the existing `phase-23-wave2-pending-creds.md` says Wave 2 live verification is
   *paused pending creds* — Phase 24 does NOT resolve that; the pointer stays. Its closing
   paragraph references the "uncommitted `uv.lock` change ... belongs to Phase 24 release work"
   — that is now being committed here, so the pointer text is consistent (no rewrite strictly
   required, but the new published-pointer supersedes the "out of scope" note).

> Exact filename/wording is Claude's discretion per CONTEXT — follow the frontmatter +
> single-bullet-index pattern above.

---

### 5. Root `pyproject.toml` — VERIFY workspace member (D-11)

**Finding: already registered — likely NO edit needed.** D-11 says the only root change is the
workspace-member add; that is already present two ways:

**Current content** (`pyproject.toml:11-20`):
```toml
[tool.uv.workspace]
members = ["packages/*"]          # glob — auto-includes packages/market-data-client

[tool.uv.sources]
higyrus-client = { workspace = true }
wallets-client = { workspace = true }
matriz-client = { workspace = true }
iol-client = { workspace = true }
ambito-financiero-client = { workspace = true }
market-data-client = { workspace = true }   # <-- ALREADY PRESENT (line 20)
```

Planner action: **confirm** these lines exist (they do). No append required. See Watch-outs
for two *other* root-pyproject lists that were NOT updated and are technically out of the
D-01/D-11 scope.

---

### 6. Package version alignment — VERIFY (Success Criterion 1)

Both already `0.1.0`; planner only confirms, does not edit:
- `packages/market-data-client/pyproject.toml:3` → `version = "0.1.0"`
- `packages/market-data-client/src/market_data_client/__init__.py:106` → `__version__ = "0.1.0"`

This alignment is exactly what `release.yml` validates (step "Verificar versión del pyproject
== versión del tag", `release.yml:42-51`), so `market-data-client-v0.1.0` will pass.

---

### 7. `uv.lock` — VALIDATE only, do not regenerate (D-03)

Already contains the package. **Do not re-create from scratch.**
**Current content** (`uv.lock`):
- Manifest members list (`uv.lock:10-18`) includes `"market-data-client"` at line 14.
- Package stanza (`uv.lock:486-514`): `name = "market-data-client"`, `version = "0.1.0"`,
  `source = { editable = "packages/market-data-client" }`, deps httpx / python-dotenv / tenacity.

Planner action (the "pattern" here is a validation command, not a code excerpt):
```bash
uv sync --all-packages --all-extras --dev --frozen   # must be green (no lock drift)
# and/or
uv lock --check                                        # exactly what ci.yml:33 runs
```
`uv.lock` shows as `M` in git status because this workspace-member registration was staged
across phases; committing it in this phase's PR is the intended path.

---

### 8. `.github/workflows/release.yml` — REFERENCE ONLY (D-02, NOT edited)

Confirms zero pipeline work. The tag `market-data-client-v0.1.0` is validated by:

**Tag-parsing regex** (`release.yml:28`):
```bash
if [[ ! "$TAG" =~ ^([a-z][a-z0-9-]*-client)-v([0-9]+\.[0-9]+\.[0-9]+([.+-][a-zA-Z0-9.+-]+)?)$ ]]; then
```
- `market-data-client` matches capture group 1 `([a-z][a-z0-9-]*-client)` → starts lowercase,
  contains only `[a-z0-9-]`, ends `-client`. ✓
- `0.1.0` matches group 2 `[0-9]+\.[0-9]+\.[0-9]+`. ✓

**Dir-existence check** (`release.yml:34`): `[[ ! -d "packages/$PACKAGE" ]]` → `packages/market-data-client`
exists. ✓

**Version-match check** (`release.yml:42-51`): awk-extracts `version` from
`packages/market-data-client/pyproject.toml` (= `0.1.0`) and compares to tag version. ✓ (see item 6).

**Trigger** (`release.yml:6`): `tags: - "*-client-v*"` → `market-data-client-v0.1.0` matches. ✓

No edits. This is the entire justification for D-02.

---

## Shared Patterns

### Per-package tag convention
**Source:** existing tags (`iol-client-v0.1.1`, etc.) + `release.yml:6,28`
**Apply to:** the tag created in D-10.
Format: `` <package-dir-name>-v<pyproject-version> `` → **exactly** `market-data-client-v0.1.0`,
created on the merge commit on `main`.

### "6th package" fan-out — every place that enumerates packages
When adding a package, the same conceptual edit repeats across surfaces. Inventory of every
hardcoded package enumeration found (so nothing is missed):

| Surface | Location | In D-01/D-04 scope? |
|---------|----------|---------------------|
| CI test matrix | `ci.yml:98-102` | YES (D-01) — **edit** |
| CLAUDE.md workspace list | `CLAUDE.md:69-73` | YES (D-04) — edit |
| CLAUDE.md "5 packages" count | `CLAUDE.md:83` | YES (D-04) — edit for consistency |
| CLAUDE.md component table | `CLAUDE.md:167-171` | YES (D-04) — edit |
| MEMORY index | memory/`MEMORY.md` | YES (D-05) — update |
| root `[tool.uv.sources]` | `pyproject.toml:20` | already present — verify |
| `uv.lock` members | `uv.lock:14` | already present — validate |
| **global mypy `files`** | `pyproject.toml:97` | **NO — out of decided scope** (see Watch-outs) |
| **importlinter `root_packages`** | `pyproject.toml:141-146` | **NO — out of scope** |
| **CI typecheck per-pkg loop** | `ci.yml:85` | **NO — out of scope** |

---

## Watch-outs (observations outside the decided edit scope)

These are surfaces that enumerate packages but were **deliberately left out** of the CONTEXT
decisions (D-01 = "el único cambio necesario en workflow"; D-11 = root change is only the
workspace-member add). Flagging so the planner makes a conscious call, not an accidental miss:

1. **Global mypy `files` (`pyproject.toml:97`) does NOT list `market-data-client/src`.**
   ```toml
   files = ["packages/higyrus-client/src", "packages/wallets-client/src", "packages/matriz-client/src", "packages/iol-client/src", "packages/ambito-financiero-client/src"]
   ```
   Consequence: the `typecheck` CI job's `mypy (src global)` step will NOT typecheck
   market-data-client source. Not a CI *failure* (won't break green), but a coverage gap.
   Per-file-ignore for the package already exists (`pyproject.toml:74`, N815) implying prior
   intent to include it. **Out of D-01 scope — do not edit unless user reopens scope.**

2. **`importlinter` `root_packages` (`pyproject.toml:141-146`) lists only 4 packages**, no
   `market_data_client`. If market-data-client has a `_core.py` boundary (the repo-wide REFAC-03
   pattern), it is currently unguarded by `lint-imports`. Out of scope for this release-prep phase.

3. **CI `typecheck` job's per-package tests-mypy loop (`ci.yml:85`)** iterates only the 5 old
   packages: `for pkg in higyrus-client wallets-client matriz-client iol-client ambito-financiero-client`.
   market-data-client tests are not mypy-checked in CI. D-01 explicitly scopes the workflow change
   to `matrix.package` only, so this is intentionally untouched — but note it means the new
   package's tests skip the CI mypy gate.

If the user wants full parity (typecheck + import-linter coverage), that is a scope expansion
beyond CONTEXT D-01/D-11 and should be surfaced at plan time.

---

## No Analog Found

None. Every edit target has a direct existing sibling to copy from (the other 5 packages'
rows/entries). This phase is pure replication of an established per-package pattern.

---

## Metadata

**Analog search scope:** `.github/workflows/`, `CLAUDE.md`, root `pyproject.toml`,
`packages/market-data-client/`, `uv.lock`, `.claude/projects/.../memory/`
**Files scanned:** 8
**Pattern extraction date:** 2026-07-31
