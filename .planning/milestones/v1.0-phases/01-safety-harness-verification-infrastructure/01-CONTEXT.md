# Phase 1: Safety Harness & Verification Infrastructure - Context

**Gathered:** 2026-05-27
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase delivers the **safety conventions and verification plumbing** that every
later client phase (2-5) depends on. It does **not** verify any client against a live
API yet — that is Phases 2-5.

In scope (HARN-01..06 + schema-snapshot tooling):
- Credential/env-var gating in the drivers (`SKIPPED <pkg>: missing X, Y`, clean exit)
- Mutation gating for Matriz orders (`VERIFY_MUTATING=1` + remarkets base-URL assert)
- Redaction so tokens/passwords/auth values are never printed in full
- `@pytest.mark.live` marker registered in a root `conftest.py` + `--live` flag (off by default)
- The classified findings format (`.planning/verification/<pkg>-findings.md`)
- The live-payload → PII-anonymized regression-fixture pipeline
- The schema-snapshot tooling (payload → keys+types snapshot writer), built here, first
  used/committed in Phase 2

Out of scope: any live verification of a specific client, committing a real schema
snapshot, fixing client bugs. Those belong to Phases 2-5.

</domain>

<decisions>
## Implementation Decisions

### Execution Model (how live verification runs across Phases 2-5)
- **D-01:** The `main_*.py` drivers are the **live-exploration vehicle**, run **manually**.
  They exercise the surface, redact output, write findings, and capture payloads against
  live APIs. This is the established project decision (PROJECT.md) — keep it.
- **D-02:** **Mocked regression tests are the only thing that runs in CI.** Live work never
  enters CI. CI stays fully offline and deterministic.
- **D-03:** `@pytest.mark.live` is registered in a **root `conftest.py`** with a `--live`
  flag; live tests are **excluded by default** (off). The marker exists so that IF a live
  pytest test is written, it is collected-but-deselected without `--live`.
- **D-04:** To make the harness **"proven"** (per phase goal), Phase 1 adds **one trivial
  `@pytest.mark.live` test** that demonstrates the mechanism (deselected without `--live`,
  selected with `--live`) and serves as a copyable example for Phases 2-5. It must not
  touch the network.

### Harness Location (where shared verification tooling lives)
- **D-05:** Shared tooling lives in a **`verification/` module at the repo root** — NOT a
  published package, and outside `packages/`. It is imported by the drivers. The
  "no shared code between packages" constraint applies to **publishable packages only**;
  the drivers and their tooling are not published, so a single source of truth for
  redaction/gating/findings is correct and avoids drift in security-sensitive code.
- **D-06:** Expected submodules/helpers inside `verification/`: redaction (`redact`,
  `safe_print`), env gating (`require_env`), mutation gating (Matriz guard), findings
  writer, payload capture, anonymizer, and schema-snapshot writer. (Exact file split is a
  planning detail.)

### Findings Format (`.planning/verification/<pkg>-findings.md`)
- **D-07:** Structure = **run-context header + summary index table + one detailed section
  per finding**. The header records the ART run-context (timestamp, resolved base URL/env,
  market-hours note). The index table has columns like ID, class, surface (sync/async),
  status. Each detailed section carries expected-vs-actual diffs and the linked regression
  test / `issue #NNN`.
- **D-08:** Finding **status lifecycle**: `OPEN` (discrepancy observed) → `CONFIRMED`
  (reproduced, real bug, not transient/market-hours) → `FIXED` (corrected in `client.py`
  **and** `aio.py`, with a linked mocked regression test). Plus a terminal
  **`EXPECTED`/`NO-FIX`** state for correct/non-actionable behavior (e.g., NO-DATA and
  ANTI-BOT confirmations). **No separate severity field** — keep the record lean.
- **D-09:** Finding **classes are fixed by the roadmap**: SHAPE, AUTH, ERROR-MAP, PARAM,
  SYNC-ASYNC-DRIFT, NO-DATA, ANTI-BOT.

### Fixtures + PII Anonymization (HARN-06)
- **D-10:** **Anonymization = per-package PII denylist + synthetic replacement + mandatory
  manual review gate.** A per-package denylist of PII keys (account IDs, names, CUIT,
  holder data, tokens) is replaced with synthetic values that **preserve type/format**;
  shape and format-relevant non-PII values (e.g., AR decimal `"1.415,00"`) are kept so the
  regression still reproduces the bug. A manual review gate is **mandatory** before any
  fixture is committed.
- **D-11:** **Two-stage pipeline:** the driver dumps the raw payload to a **gitignored
  staging dir** (e.g., `.planning/verification/captures/`, never committed) → an
  anonymization step applies the denylist and emits the **committable** fixture (+ a
  regression-test stub) under the package's `tests/`. This guarantees the raw PII-bearing
  payload never enters git by construction.

### Schema-Snapshot Tooling (scope boundary Phase 1 vs Phase 2)
- **D-12:** The **schema-snapshot tooling** (payload → keys+types structure → snapshot
  file) is **built in Phase 1** as generic infra inside `verification/`, alongside the
  fixture pipeline and findings writer. The **first real snapshot is committed in Phase 2**
  (DRIFT-01). This keeps "Phase 1 = all plumbing built and proven" and matches the
  roadmap's Phase-1 summary line.

### Redaction (HARN-03)
- **D-13:** **Defense in depth:** an explicit `redact(value)` helper (shows a short prefix,
  ~4 chars + `…`) for known sensitive values, **plus** a `safe_print` that scans the output
  string against the credential values loaded from env and masks them — so even an
  accidental print of a raw dict/response containing a token is masked. "Tokens are never
  printed in full" becomes structural, not a matter of discipline. Credential globals are
  never echoed.

### Driver Orchestration & SKIPPED Protocol (HARN-01)
- **D-14:** **Thin aggregate runner + first-class individual drivers.** A `main_verify.py`
  (or equivalent) runs all five drivers and aggregates a RAN/SKIPPED summary per package,
  **never halting on a SKIPPED**. Each `main_*.py` remains independently runnable
  (`uv run --package <pkg> python main_<name>.py`) because the cycle proceeds
  client-by-client in Phases 2-5.
- **D-15:** Env gating is **per driver** via a `require_env([...])` helper from
  `verification/` that returns the missing vars, prints the exact `SKIPPED <pkg>: missing
  X, Y` line, and exits cleanly (code 0) so the runner and any shell loop continue.

### Mutation Gating (HARN-02)
- **D-16:** Matriz order mutations are unreachable by default: they run only when
  `VERIFY_MUTATING=1` **AND** the resolved base URL is asserted to contain `remarkets`;
  otherwise a `SKIPPED (mutating, guard off)` line is printed. The guard helper lives in
  `verification/`. (Format already fixed by the roadmap.) Note: per REQUIREMENTS/Out of
  Scope, order placement is **never** run live even in sandbox — Phase 5 verifies order
  construction/parsing by mock only; this gate is the belt-and-suspenders safety net.

### Claude's Discretion
- Exact file split inside `verification/` (one module vs several submodules).
- Exact prefix length / masking format for `redact()` (4 chars + `…` is the default intent).
- Internal structure of the schema-snapshot file format (keys + types, not values).
- Whether the aggregate runner invokes drivers via subprocess or in-process import.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope & requirements
- `.planning/ROADMAP.md` §"Phase 1: Safety Harness & Verification Infrastructure" — phase
  goal, success criteria (HARN-01..06), and the summary line that includes schema-snapshot tooling
- `.planning/REQUIREMENTS.md` §"Infraestructura de verificación (HARN)" — HARN-01..06 full text
- `.planning/REQUIREMENTS.md` §"Detección de drift y cierre (DRIFT)" — DRIFT-01 (schema
  snapshots, first committed in Phase 2) and the cross-cutting note
- `.planning/REQUIREMENTS.md` §"Out of Scope" — explicit anti-features (never fire
  403/429/5xx live; never place real orders; prod-vs-sandbox gap recorded, not closed)
- `.planning/PROJECT.md` §"Key Decisions" — `main_*.py` as the verification vehicle;
  per-fix mocked regression test; credentials in per-package `.env`, never committed

### Codebase maps (current state of the harness target)
- `.planning/codebase/TESTING.md` — pytest config, `pytest-httpx` mocking, conftest autouse
  fixture pattern, the `Regression: ... (issue #NNN)` convention to follow
- `.planning/codebase/STRUCTURE.md` — repo layout; root `main_*.py` drivers; per-package
  `tests/`; where new code goes
- `.planning/codebase/CONVENTIONS.md` — naming, `from __future__ import annotations`,
  ruff/mypy-strict expectations every new helper must pass

### Current implementation touchpoints
- `main_ambito_financiero.py`, `main_higyrus.py`, `main_iol.py`, `main_matriz.py`,
  `main_wallets.py` — the five drivers to extend with gating + redaction + capture
- `pyproject.toml` §`[tool.pytest.ini_options]` — `--strict-markers`, `--strict-config`,
  `testpaths = ["packages"]`; registering `@pytest.mark.live` must satisfy strict markers,
  and a root `conftest.py` / `--live` flag must integrate with this config
- `packages/matriz-client/src/matriz_client/client.py:58` — `_base_url` from
  `PRIMARY_BASE_URL` (defaults to remarkets) — the value the mutation guard asserts against
- `packages/*/.env.example` — the required env-var names per package that `require_env`
  must check (IOL_USER/IOL_PASSWORD; HIGYRUS_USER/PASSWORD/BASE_URL; PRIMARY_USER/PASSWORD;
  Ámbito = none required)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Existing `main_*.py` drivers**: minimal today (login + 1-2 calls); they are the
  extension point — gating, redaction, and capture wrap around them rather than replacing them.
- **`pytest-httpx` mocking pattern** (TESTING.md): the regression-test stubs emitted by the
  fixture pipeline should follow the documented `httpx_mock.add_response(...)` + full-URL
  assertion pattern.
- **Per-package autouse `conftest.py` fixtures** (TESTING.md): the new **root** `conftest.py`
  for the `--live` flag must coexist with these via `--import-mode=importlib` (already set).
- **`Regression: ... (issue #NNN)` convention** (TESTING.md): emitted regression-test stubs
  must carry this docstring marker.

### Established Patterns
- **No shared code between *publishable* packages** — the `verification/` module deliberately
  sits OUTSIDE `packages/` so it does not violate this constraint while still being DRY for
  the (non-published) tooling.
- **Module-level singleton state per package** (`_base_url`, `_token`, etc.) — drivers/gating
  read these (e.g., the resolved base URL for the remarkets assert) but must never echo them.
- **`--strict-markers` / `--strict-config`** — the `live` marker MUST be registered or the
  whole suite fails to collect.

### Integration Points
- **Root `conftest.py`** (does not exist yet) — new file; registers `live` marker + `--live`
  flag and the default-deselect hook.
- **Root `pyproject.toml`** — pytest config; may also need to declare/version the
  `verification/` module so it is importable under `uv run --package <pkg>` (open research item).
- **`.planning/verification/`** — new dir for findings files + gitignored `captures/` staging.
- **`.gitignore`** — must exclude the raw-capture staging dir.

</code_context>

<specifics>
## Specific Ideas

- `SKIPPED <pkg>: missing X, Y` and `SKIPPED (mutating, guard off)` are the exact output
  lines required (verbatim from roadmap success criteria).
- `redact()` default: show ~4-char prefix + `…`; `safe_print` masks any known credential
  value found in the output string.
- Findings file path convention: `.planning/verification/<pkg>-findings.md`.
- Raw-capture staging: `.planning/verification/captures/` (gitignored), distinct from the
  committable fixtures under each package's `tests/`.

</specifics>

<deferred>
## Deferred Ideas

- **Open research item (Phase 1 planning):** how `verification/` becomes importable when a
  driver runs via `uv run --package <pkg> python main_<name>.py` — uv workspace member vs
  `sys.path` addition vs dev-only path config. Decide during planning/research, not a new
  capability.
- **prod-vs-sandbox gap for Matriz** — recorded as an explicit open question for downstream
  (per REQUIREMENTS Out of Scope); not closed in this cycle.
- v2 error-edge mock coverage (ERR-01 mocked 403/429/5xx mapping, ERR-02 token-TTL refresh)
  is explicitly deferred to v2 — not this milestone.

</deferred>

---

*Phase: 1-safety-harness-verification-infrastructure*
*Context gathered: 2026-05-27*
