# Phase 1: Safety Harness & Verification Infrastructure - Research

**Researched:** 2026-05-27
**Domain:** Python verification tooling — env/mutation gating, credential redaction, pytest live-marker, findings format, live-payload→fixture pipeline, schema-snapshot writer (all inside a repo-root `verification/` module)
**Confidence:** HIGH (the open research item — importability of `verification/` — was resolved empirically in this session; pytest `--live` mechanism proven end-to-end against the real repo config)

## Summary

This phase builds **plumbing only**: a single repo-root `verification/` module (non-published, outside `packages/`) plus a root `conftest.py`, consumed by the five `main_*.py` drivers and by future client phases. No live API is touched here. The whole point is that *before* any live run in Phases 2–5, the safety conventions (env gating, mutation gating, redaction) and the verification artifacts (findings format, capture→anonymize→fixture pipeline, schema-snapshot writer) exist and are *proven*.

The single highest-risk planning question — **how does `verification/` become importable under `uv run --package <pkg> python main_<name>.py`?** — was resolved empirically (not from training knowledge): when CPython executes a script, it prepends the script's own directory to `sys.path[0]`. Since all `main_*.py` live at the repo root, the repo root is on `sys.path` automatically, so a plain `verification/` package directory at the repo root is importable **with zero configuration** — no uv workspace member, no `sys.path` hacking, no editable install, no `pyproject.toml` change. This was verified to work under `uv run --package iol-client`, under plain `uv run`, and to leave pytest collection untouched (`testpaths = ["packages"]` means pytest never even looks at `verification/`). This is the recommended approach: it satisfies the "no shared code between *publishable* packages" constraint (the module is not a package member, never built, never published) and does not perturb the frozen CI install.

**Primary recommendation:** Create `verification/` as a plain (non-workspace, non-published) Python package at the repo root, implemented stdlib-only (no new dependencies). Add a root `conftest.py` implementing `pytest_addoption(--live)` + `pytest_configure` (register `live` marker) + `pytest_collection_modifyitems` (deselect `live` tests unless `--live`). Wire `require_env`, `redact`/`safe_print`, the Matriz mutation guard, the findings writer, the capture→anonymize→fixture pipeline, and the schema-snapshot writer into the drivers. Ship one trivial `@pytest.mark.live` example test (network-free) to prove the marker. No external package is installed in this phase.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Env-var gating (`require_env`) | `verification/` module | drivers (call site) | Single source of truth for the exact `SKIPPED <pkg>: missing X, Y` line; drivers only supply their var list |
| Mutation gating (Matriz remarkets assert) | `verification/` module | `main_matriz.py` | Belt-and-suspenders safety net must be DRY and audited in one place |
| Redaction (`redact`, `safe_print`) | `verification/` module | all 5 drivers | Security-sensitive; duplicating it across drivers invites drift (CONTEXT D-05 rationale) |
| `live` marker + `--live` flag | root `conftest.py` | per-package `conftest.py` (autouse fixtures) | pytest hooks must be at the collection root; package conftests stay package-scoped |
| Findings format | `.planning/verification/<pkg>-findings.md` (docs) + writer in `verification/` | client phases (authors) | Format is a documented convention; writer is optional helper |
| Capture (raw payload dump) | `verification/` writer → `.planning/verification/captures/` (gitignored) | drivers | Raw PII-bearing payload must land only in the gitignored staging dir, by construction |
| Anonymize → fixture | `verification/` module | manual review gate (human) | Per-package denylist + synthetic replacement; human gate before commit |
| Schema-snapshot (keys+types) | `verification/` module | client phases (Phase 2 first commits one) | Generic infra built here, first *used* in Phase 2 (D-12) |
| Regression-test stub emission | `verification/` module | each package's `tests/` | Stub follows the documented `pytest-httpx` + `Regression: ... (issue #NNN)` convention |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib (`os`, `sys`, `json`, `pathlib`, `dataclasses`, `typing`) | 3.12+ | All gating, redaction, snapshot, anonymization logic | `[VERIFIED: pyproject.toml]` Project mandates 3.12+; verification tooling needs no third-party deps |
| `pytest` | >=8.3 (installed) | `live` marker, `--live` flag via root conftest hooks | `[VERIFIED: pyproject.toml]` already a dev dependency |
| `python-dotenv` | >=1.0 (installed transitively per package) | `.env` already loaded by each client at import; `require_env` just reads `os.getenv` after import | `[VERIFIED: CLAUDE.md + .env files present]` no new dependency |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest-httpx` | >=0.34 (installed) | Pattern the emitted regression-test *stubs* follow (`httpx_mock.add_response(url=..., json=...)`) | Stub template only — not invoked in Phase 1 |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| stdlib-only anonymization | `Faker` for synthetic values | `[ASSUMED]` Faker generates *realistic* data, but the requirement (D-10) is *format-preserving deterministic* replacement (e.g., a CUIT → a syntactically valid but fake CUIT, an account id → same-length digits). Stdlib `str`/`random`/regex covers this; adding a dev dep means a `uv.lock` change and a `--frozen` CI re-resolve for tooling that never ships. **Recommend stdlib-only.** |
| repo-root plain `verification/` package | uv workspace member; `sys.path.insert`; editable install; src-layout package | All add config and either (a) risk being treated as publishable, or (b) require per-driver boilerplate. The plain repo-root package needs none — proven below. |
| `skip` live tests by default | `deselect` live tests by default | `deselect` (recommended) yields `1 deselected / 0 selected` — zero skip-noise in CI output; `skip` yields SKIPPED lines. Both proven working. CONTEXT D-03 says "collected-but-deselected" → use deselect. |

**Installation:**
```bash
# No external packages installed in Phase 1. Tooling is stdlib + already-present dev deps.
```

**Version verification:** Performed via `uv --version` (0.9.0) and reading the committed `pyproject.toml` dependency group. No new package is added, so no registry version pin is introduced.

## Package Legitimacy Audit

> No external packages are installed in this phase. The `verification/` module is stdlib-only and the pytest hooks use the already-present `pytest` dependency.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| *(none — no installs)* | — | — | — | — | n/a | n/a |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

`Faker` was evaluated as an *alternative* for anonymization and rejected on design grounds (format-preserving deterministic replacement is better served by stdlib, and a dev-dep change forces a `--frozen` CI re-resolve). If a future phase reconsiders it, run the Package Legitimacy Gate then — `[ASSUMED]` until verified.

## Architecture Patterns

### System Architecture Diagram

```
                         ┌───────────────────────────────────────────────┐
                         │  verification/  (repo-root, non-published)      │
                         │  importable because main_*.py at root puts the  │
                         │  repo root on sys.path[0]                        │
                         │                                                  │
   ENV (.env per pkg) ──▶│  require_env([...]) ─▶ "SKIPPED <pkg>: missing  │
                         │                          X, Y"  (exit 0)         │
                         │                                                  │
   client._base_url  ───▶│  mutation_guard() ─▶ runs only if               │
   VERIFY_MUTATING   ───▶│    VERIFY_MUTATING=1 AND "remarkets" in url      │
                         │    else "SKIPPED (mutating, guard off)"          │
                         │                                                  │
   raw token/creds   ───▶│  redact(v) -> "abcd…"                            │
   any output string ───▶│  safe_print(s) -> masks known cred values in s   │
                         │                                                  │
   live payload (dict)──▶│  capture(payload) ─▶ .planning/verification/    │
                         │                        captures/<pkg>-<ep>.json   │
                         │                        (GITIGNORED staging)       │
                         │                              │                    │
                         │   anonymize(capture, denylist) ── manual review ──┼─▶ packages/<pkg>/tests/
                         │       (synthetic, format-preserving)   GATE        │   fixtures/<ep>.json  (committable)
                         │                              │                     │   + test_<ep>_regression.py (stub)
                         │   schema_snapshot(payload) ─▶ keys+types only ─────┼─▶ committed in Phase 2+
                         │                                                    │
                         │   findings writer ─────────────────────────────────┼─▶ .planning/verification/<pkg>-findings.md
                         └────────────────────────────────────────────────────┘
                                            ▲
          ┌─────────────────────────────────┼───────────────────────────────────┐
          │ main_ambito.py  main_higyrus.py  main_iol.py  main_matriz.py  …       │  (drivers: call gating, redact, capture)
          └─────────────────────────────────────────────────────────────────────┘
          ┌─────────────────────────────────────────────────────────────────────┐
          │ main_verify.py  (thin aggregate runner; RAN/SKIPPED summary; D-14)    │
          └─────────────────────────────────────────────────────────────────────┘

   root conftest.py:  pytest_addoption(--live) + register `live` marker + deselect live by default
                      (testpaths=["packages"] means pytest never collects verification/)
```

### Recommended Project Structure

`[CITED: STRUCTURE.md]` plus the new files this phase adds:

```
market-libs/
├── conftest.py                    # NEW — root: --live flag, live marker, deselect hook
├── main_verify.py                 # NEW — thin aggregate runner (D-14)
├── main_*.py                      # EXTEND — wrap existing logic with gating/redaction/capture
├── verification/                  # NEW — repo-root module (non-published)
│   ├── __init__.py                # re-export public helpers
│   ├── env_gate.py                # require_env([...]) -> SKIPPED line + exit(0)  (D-15)
│   ├── mutation_gate.py           # Matriz remarkets + VERIFY_MUTATING guard       (D-16)
│   ├── redaction.py               # redact(value), safe_print(s, secrets)          (D-13)
│   ├── findings.py                # findings-file writer / template                (D-07/08/09)
│   ├── capture.py                 # raw payload -> gitignored captures/            (D-11)
│   ├── anonymize.py               # denylist + synthetic format-preserving repl    (D-10)
│   └── schema.py                  # payload -> keys+types snapshot                 (D-12)
└── .planning/verification/
    ├── <pkg>-findings.md          # one per client phase (template documented here)
    └── captures/                  # GITIGNORED raw staging (add to .gitignore)
```

> The exact file split inside `verification/` is **Claude's Discretion** (CONTEXT). The split above is a recommendation, not a mandate — a single `verification/__init__.py` is also acceptable. Whatever the split, all modules must pass `ruff` + `mypy --strict` and start with `from __future__ import annotations`. **Note:** `verification/` is NOT under `packages/`, so the global mypy `files = [...]` list does not cover it — the plan must add an explicit mypy/ruff invocation for `verification/` (e.g. `uv run mypy verification` and `uv run ruff check verification`) so the new tooling is actually type-checked.

### Pattern 1: Repo-root module importable via script-dir-on-sys.path

**What:** A plain package directory at the repo root, imported by root-level driver scripts.
**When to use:** Shared non-published tooling consumed only by repo-root scripts.
**Why it works:** CPython prepends the executed script's directory to `sys.path[0]`. All `main_*.py` are at the repo root → repo root is on `sys.path` → `import verification` resolves. `uv run --package <pkg>` does not change this.

```python
# Source: VERIFIED empirically this session (uv 0.9.0, repo root)
# main_iol.py
from __future__ import annotations
from verification import require_env, redact, safe_print  # resolves with zero config
```

Empirical proof (this session):
```
$ uv run --package iol-client python main_probe.py
IMPORT OK: supe…
$ uv run python main_probe.py
IMPORT OK: supe…
$ uv run pytest --collect-only -q   # verification/ present at root
114 tests collected in 0.15s        # pytest ignores it (testpaths=["packages"])
```

### Pattern 2: Root conftest live marker (deselect-by-default)

**What:** Register `live` marker (satisfies `--strict-markers`), add `--live` flag, deselect `live` tests unless `--live`.
**When to use:** Exactly once, at the repo-root `conftest.py`.

```python
# Source: VERIFIED end-to-end this session against the real pyproject config
# conftest.py  (repo root)
from __future__ import annotations
import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--live",
        action="store_true",
        default=False,
        help="Ejecuta tests @pytest.mark.live contra APIs reales.",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "live: test que toca una API en vivo (deseleccionado salvo --live).",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if config.getoption("--live"):
        return
    selected, deselected = [], []
    for item in items:
        (deselected if "live" in item.keywords else selected).append(item)
    if deselected:
        config.hook.pytest_deselected(items=deselected)
        items[:] = selected
```

Proof: default run → `1 deselected / 0 selected`; `--live` → `1 passed`; `--strict-markers`/`--strict-config` stay green; per-package autouse fixtures still apply under `--live` (verified the autouse fixture set `_base_url == "https://api.test"` inside the live test).

### Pattern 3: Redaction with defense-in-depth (D-13)

```python
# Source: design based on VERIFIED Python redaction pitfalls (see Pitfalls 3 & 4)
from __future__ import annotations
import os


def redact(value: str | None, *, keep: int = 4) -> str:
    """Devuelve sólo un prefijo + elipsis para un valor sensible."""
    if not value:
        return "<empty>"            # never echo "", and never produce a bare "…"
    if len(value) <= keep:
        return "…"                  # too short to show a prefix safely
    return f"{value[:keep]}…"


def safe_print(text: str, secrets: list[str]) -> None:
    """Imprime `text` enmascarando cualquier valor de credencial conocido."""
    masked = text
    for secret in secrets:
        if secret and len(secret) >= 4:   # skip empty/too-short to avoid corruption
            masked = masked.replace(secret, "‹REDACTED›")
    print(masked)
```

### Pattern 4: Schema snapshot — keys + types, not values (D-12)

```python
# Source: design; format is keys+types only so it is PII-free and committable
from __future__ import annotations
from typing import Any


def schema_of(payload: Any) -> Any:
    """Reduce un payload a su estructura: claves + tipos, nunca valores."""
    if isinstance(payload, dict):
        return {k: schema_of(v) for k, v in sorted(payload.items())}
    if isinstance(payload, list):
        # tipo del primer elemento como muestra; lista vacía -> []
        return [schema_of(payload[0])] if payload else []
    return type(payload).__name__   # "str" | "int" | "float" | "bool" | "NoneType"
```
Snapshot file = pretty-printed JSON of `schema_of(raw)`. It is PII-free **by construction** (no values), so it composes safely with the capture pipeline and is directly committable (first committed Phase 2, DRIFT-01).

### Anti-Patterns to Avoid
- **Making `verification/` a uv workspace member or published package** — violates the "no shared publishable code" spirit and triggers builds. It must stay a plain repo-root dir.
- **Echoing credential globals** (`print(client._token)`, `print(vars())`) — even in a "redacted" context. Redact the value, never the variable name+value pair.
- **`safe_print` masking empty/short secrets** — replacing `""` mangles every character boundary (the concourse bug). Guard `len(secret) >= 4`.
- **Putting the `live` marker / `--live` flag in a per-package conftest** — collection hooks belong at the root; package conftests keep their autouse fixtures.
- **Letting the raw capture write anywhere committable** — raw payloads with PII must land only in `.planning/verification/captures/` (gitignored) until anonymized + human-reviewed.
- **Snapshotting values** — drift detection is structural (keys+types). Including values defeats PII-safety and produces noisy diffs.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Importing repo-root tooling from drivers | `sys.path.insert(0, ...)` boilerplate in every driver | plain `verification/` dir at root (script-dir already on path) | Verified: zero config needed; less fragile |
| Live/offline test split | a custom env-var check inside each test | `@pytest.mark.live` + `--live` deselect hook | pytest's native marker + collection hook, `--strict-markers`-clean |
| Type detection for snapshots | bespoke `isinstance` ladder per endpoint | one recursive `schema_of` (above) | generic, one place, PII-free by construction |
| Reading `.env` | re-parsing `.env` in `require_env` | `os.getenv` after the client module's `load_dotenv()` runs | the client already loads it at import; just read the resolved env |

**Key insight:** Nearly every "infrastructure" need here is met by Python stdlib + pytest's existing hook surface. The temptation to add a dependency (Faker, a redaction lib, a path-config tool) is exactly what the frozen-CI / no-shared-publishable-code constraints push against. Build small, stdlib-only, in one module.

## Runtime State Inventory

> This is a tooling/greenfield phase (it *creates* the harness; it does not rename anything). The only "state" considerations are which files/dirs the new tooling touches.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — no datastore keys renamed. Phase creates `.planning/verification/` (findings + gitignored `captures/`). | Create dirs; add `captures/` to `.gitignore`. |
| Live service config | None — no external service config touched. The Matriz mutation guard *reads* `matriz_client.client._base_url` but never mutates it. | none |
| OS-registered state | None — no scheduled tasks, services, or daemons. | none |
| Secrets/env vars | `require_env` *reads* existing env var names (`IOL_USER`/`IOL_PASSWORD`; `HIGYRUS_USER`/`HIGYRUS_PASSWORD`/`HIGYRUS_BASE_URL`; `PRIMARY_USER`/`PRIMARY_PASSWORD`; Ámbito = none) and `VERIFY_MUTATING`. No secret is renamed or created. `.env` files for matriz + higyrus already exist (verified); iol/ambito/wallets `.env` absent (only `.env.example`). | Driver gating must handle absent `.env` gracefully → that *is* the `SKIPPED` path. |
| Build artifacts | None — `verification/` is never built/installed; not a wheel. `uv.lock` is **not** changed (no new deps). | none (do NOT add to workspace members) |

**Verified by:** grep for existing helpers (none found), `ls` of `.env`/`.env.example` per package, `pyproject.toml` inspection (no new dep), pytest collect-only with a stray `verification/` present.

## Common Pitfalls

### Pitfall 1: `verification/` accidentally treated as a package member
**What goes wrong:** Adding `verification` to `[tool.uv.workspace] members` or giving it a `pyproject.toml` makes uv try to build/publish it and may pull it into the frozen install.
**Why it happens:** Habit — "shared code goes in a package."
**How to avoid:** Leave it as a *plain directory* with only `__init__.py` and submodules. No `pyproject.toml`, no workspace registration. It is imported via sys.path, never installed.
**Warning signs:** `uv build` mentions `verification`; `uv.lock` diff in this phase; CI `--frozen` re-resolves.

### Pitfall 2: New tooling escapes ruff/mypy because it's outside `packages/`
**What goes wrong:** Global mypy `files = ["packages/*/src", ...]` and ruff `src = ["packages/*/src", "packages/*/tests"]` do not include `verification/` or root `main_*.py`/`conftest.py`. The strict gates silently skip the new code.
**Why it happens:** The config is package-scoped by design.
**How to avoid:** Plan an explicit verification step: `uv run ruff check verification main_*.py conftest.py` and `uv run mypy verification`. Consider adding `verification` to mypy `files` (it will still be excluded from coverage/`packages` source). Every new module starts with `from __future__ import annotations`.
**Warning signs:** mypy passes but never lists `verification/*.py` in its file count.

### Pitfall 3: `safe_print` masking empty/short secrets corrupts output
**What goes wrong:** `text.replace("", "‹REDACTED›")` inserts the marker between every character (real bug: concourse #4656). A 1–3 char "secret" produces rampant false-positive masking.
**Why it happens:** A credential env var is unset → resolves to `""` → passed into the secrets list.
**How to avoid:** `if secret and len(secret) >= 4` before replacing. Build the secrets list from the *resolved* credential globals, filtering falsy/short values. `[VERIFIED: WebSearch — concourse/concourse#4656, pythoncentral]`
**Warning signs:** Output with `‹REDACTED›` wedged between letters; mangled logs.

### Pitfall 4: Over-aggressive substring masking
**What goes wrong:** A short token that happens to be a common substring masks legitimate output.
**Why it happens:** Naive `str.replace` of a low-entropy value.
**How to avoid:** Combine the `len >= 4` guard with the primary defense (`redact()` at the *source* of each known sensitive print). `safe_print` is the second layer, not the only layer (D-13 defense-in-depth). `[VERIFIED: WebSearch — concourse, databricks community]`
**Warning signs:** Non-secret text getting redacted.

### Pitfall 5: Mutation guard reads stale or wrong base URL
**What goes wrong:** The guard checks a hard-coded URL instead of the *resolved* `matriz_client.client._base_url`, so a `configure(base_url=...)` override to prod would slip past.
**Why it happens:** Convenience.
**How to avoid:** Read the live module value at guard time: assert `"remarkets" in matriz_client.client._base_url`. Both conditions (`VERIFY_MUTATING=1` AND remarkets) required; else print `SKIPPED (mutating, guard off)`. `[CITED: CONTEXT D-16; client.py:58]`
**Warning signs:** Guard passes when `PRIMARY_BASE_URL` points at `api.primary.com.ar` (prod).

### Pitfall 6: Driver `SKIPPED` path exits non-zero and halts the aggregate runner
**What goes wrong:** `require_env` raises/`exit(1)` on missing vars → `main_verify.py` or a shell loop stops at the first incomplete package.
**Why it happens:** Treating "missing creds" as an error rather than a skip.
**How to avoid:** `require_env` prints `SKIPPED <pkg>: missing X, Y` and returns/`sys.exit(0)` (clean). The aggregate runner records SKIPPED and continues (D-14/D-15).
**Warning signs:** Running with one package's `.env` absent stops the whole batch.

## Code Examples

### `require_env` (D-15) — exact SKIPPED line, clean exit
```python
# Source: design per CONTEXT D-15 + success criterion 1
from __future__ import annotations
import os
import sys


def require_env(pkg: str, names: list[str]) -> bool:
    """True si todas las vars existen; si faltan, imprime SKIPPED y devuelve False."""
    missing = [n for n in names if not os.getenv(n)]
    if missing:
        print(f"SKIPPED {pkg}: missing {', '.join(missing)}")
        return False
    return True


# Driver usage — clean exit so the aggregate runner / shell loop continues:
# if not require_env("iol-client", ["IOL_USER", "IOL_PASSWORD"]):
#     sys.exit(0)
```

### Mutation guard (D-16)
```python
# Source: design per CONTEXT D-16; reads the resolved base_url at guard time
from __future__ import annotations
import os
import matriz_client


def mutating_allowed() -> bool:
    """Solo permite mutaciones con flag opt-in Y base URL remarkets."""
    if os.getenv("VERIFY_MUTATING") != "1":
        print("SKIPPED (mutating, guard off)")
        return False
    base = matriz_client.client._base_url  # resolved module state
    if "remarkets" not in base:
        print("SKIPPED (mutating, guard off)")  # prod URL -> never mutate
        return False
    return True
```

### Trivial proven live test (D-04) — network-free example for Phases 2–5
```python
# Source: design per CONTEXT D-04; placed under any packages/<pkg>/tests/
from __future__ import annotations
import pytest


@pytest.mark.live
def test_live_marker_is_wired() -> None:
    """Demuestra el mecanismo --live. No toca la red.

    Sin --live: deseleccionado. Con --live: corre y pasa.
    Copiar como plantilla para tests en vivo reales en fases 2-5.
    """
    assert True
```

### Anonymization data model (D-10/D-11)
```python
# Source: design per CONTEXT D-10/D-11; stdlib-only, format-preserving
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import re


@dataclass(frozen=True, slots=True)
class Denylist:
    """Claves PII por paquete + reemplazos sintéticos que preservan formato."""
    pkg: str
    keys: frozenset[str]                      # p.ej. {"idCuenta","cuit","titular"}
    # reemplazo por clave; preserva longitud/forma (no realismo)
    replacements: dict[str, str] = field(default_factory=dict)


def anonymize(payload: Any, deny: Denylist) -> Any:
    """Reemplaza valores de claves PII; conserva forma y formatos no-PII
    (p.ej. el decimal AR '1.415,00' se mantiene para reproducir el bug)."""
    if isinstance(payload, dict):
        return {
            k: (deny.replacements.get(k, _synthetic(k, v)) if k in deny.keys
                else anonymize(v, deny))
            for k, v in payload.items()
        }
    if isinstance(payload, list):
        return [anonymize(x, deny) for x in payload]
    return payload


def _synthetic(key: str, value: Any) -> Any:
    """Genera un valor sintético del mismo tipo/forma que `value`."""
    if isinstance(value, str):
        return re.sub(r"\d", "0", re.sub(r"[A-Za-z]", "x", value))  # same shape
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return 0
    if isinstance(value, float):
        return 0.0
    return value
```
**Mandatory manual review gate (D-10):** the pipeline emits the anonymized fixture to a *staging* path or prints a diff; a human confirms before it is moved/committed under `packages/<pkg>/tests/fixtures/`. The raw capture never leaves `.planning/verification/captures/` (gitignored). The format-relevant non-PII values (AR decimal `"1.415,00"`, JSON-number-vs-string, envelope keys) are preserved so the regression still reproduces.

### Findings file template (D-07/08/09)
```markdown
# Findings: <pkg>-client

## Run Context (ART)
- Timestamp: <ISO-8601>
- Resolved base URL / env: <url> (<remarkets|prod|public>)
- Market hours note: <abierto|cerrado — afecta paths sesión-dependientes>

## Index
| ID | Class | Surface | Status |
|----|-------|---------|--------|
| F-01 | SHAPE | sync | OPEN |
| F-02 | SYNC-ASYNC-DRIFT | both | CONFIRMED |

## F-01 — <título>
**Class:** SHAPE  ·  **Surface:** sync  ·  **Status:** OPEN→CONFIRMED→FIXED | EXPECTED/NO-FIX
**Expected:** <lo que el cliente asume>
**Actual:** <lo que devolvió la API en vivo>
**Diff:** <campos/tipos divergentes>
**Regression:** <test path> · `Regression: ... (issue #NNN)` | issue #NNN
```
- **Classes (fixed, D-09):** SHAPE, AUTH, ERROR-MAP, PARAM, SYNC-ASYNC-DRIFT, NO-DATA, ANTI-BOT.
- **Status lifecycle (D-08):** OPEN → CONFIRMED → FIXED (fixed in `client.py` AND `aio.py` + linked mocked regression test) — plus terminal EXPECTED/NO-FIX. No severity field.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `--import-mode=prepend` (default historically) | `--import-mode=importlib` (already set) | pytest 6+/7+ | conftest namespace collisions across monorepo packages avoided; root + package conftests coexist (verified) |
| `pytest.config` global | `config.getoption(...)` in hooks | pytest 5+ | the `--live` flag is read via the `config` arg passed to hooks (used above) |

**Deprecated/outdated:** none relevant — the stdlib + pytest hook APIs used here are stable.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | stdlib `re`-based synthetic replacement is sufficient for PII format-preservation across all packages | Anonymization / Alternatives | If a package needs realistic structured fakes (valid CUIT checksum, valid CBU), the synthetic value may not satisfy a downstream parser — but fixtures feed *mocked* tests, so a syntactically-shaped fake is generally enough. Revisit per-package in Phases 3–5. |
| A2 | Reading `matriz_client.client._base_url` (private module state) in the mutation guard is acceptable | Mutation guard | CONTEXT explicitly allows drivers/gating to *read* module state (never echo). No public getter exists (verified). If a public accessor is added later, prefer it. |
| A3 | `deselect` (not `skip`) is the intended default for live tests | conftest pattern | CONTEXT D-03 says "collected-but-deselected" → deselect chosen. If the team prefers visible SKIPPED lines, swap to `pytest.mark.skip` (also proven). Low risk — both work. |
| A4 | Faker is unnecessary | Standard Stack / Alternatives | If rejected and later needed, a dev-dep + `uv.lock` change + frozen-CI re-resolve is required. Documented for downstream. |

## Open Questions

1. **Aggregate runner: subprocess vs in-process import (Claude's Discretion per CONTEXT)**
   - What we know: `main_verify.py` must run all five drivers and never halt on SKIPPED (D-14).
   - What's unclear: in-process import shares one Python process (module-level singleton state from one client could bleed into another — though packages don't share code, they each `load_dotenv()` and hold their own globals); subprocess (`uv run --package <pkg> python main_<name>.py` per driver) gives clean isolation + matches the per-package run model but is slower.
   - Recommendation: **subprocess per driver** — it mirrors the exact command Phases 2–5 use, guarantees isolation of module-level singletons, and lets each driver `exit(0)` on SKIPPED without affecting the runner. Capture stdout per child, print the RAN/SKIPPED aggregate.

2. **Where regression fixtures live under each package's `tests/`**
   - What we know: stubs go under `packages/<pkg>/tests/` and follow the `pytest-httpx` + `Regression: ... (issue #NNN)` convention.
   - What's unclear: a `fixtures/` subdir vs inline module constants (TESTING.md shows inline constants like `ORDER_PAYLOAD`).
   - Recommendation: a `packages/<pkg>/tests/fixtures/<endpoint>.json` for large anonymized payloads + an inline stub `test_<endpoint>_regression.py` that loads it; keeps anonymized data reviewable as a discrete committed file.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| uv | building/running drivers + tests | ✓ | 0.9.0 | — |
| Python | all tooling | ✓ | 3.12+ required (CLAUDE.md); CI matrix 3.12/3.13 | — |
| pytest (+ httpx, asyncio, cov) | `--live` mechanism, regression-test stubs | ✓ | >=8.3 (dev group) | — |
| `.env` per package | live runs in Phases 2–5 (NOT Phase 1) | partial: matriz + higyrus present; iol/ambito/wallets absent | — | absent `.env` → the `SKIPPED` path (this is correct behaviour, not a blocker) |

**Missing dependencies with no fallback:** none — Phase 1 is plumbing; it does not require live credentials.
**Missing dependencies with fallback:** iol/ambito/wallets `.env` absent → exercising those drivers' SKIPPED path is itself the HARN-01 demonstration.

## Validation Architecture

> `workflow.nyquist_validation` not found disabled in config → section included.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3+ (+ pytest-httpx 0.34+, pytest-asyncio 0.24+, pytest-cov 6.0+) |
| Config file | root `pyproject.toml` `[tool.pytest.ini_options]`; NEW root `conftest.py` for `--live` |
| Quick run command | `uv run pytest packages/<pkg>/tests/<file>.py -q` |
| Full suite command | `uv run pytest` (114 tests today; +1 with the live example) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| HARN-01 | `require_env` prints exact `SKIPPED <pkg>: missing X, Y`, returns/exit 0 | unit | `uv run pytest packages/.../tests/test_env_gate.py -q` (capsys) | ❌ Wave 0 |
| HARN-02 | mutation guard: blocks unless `VERIFY_MUTATING=1` AND remarkets; prints `SKIPPED (mutating, guard off)` | unit | `uv run pytest .../test_mutation_gate.py -q` (monkeypatch env + `_base_url`) | ❌ Wave 0 |
| HARN-03 | `redact` shows ≤4-char prefix; `safe_print` masks known creds; empty/short not mangled | unit | `uv run pytest .../test_redaction.py -q` (capsys) | ❌ Wave 0 |
| HARN-04 | `live` marker registered (`--strict-markers` clean); deselected w/o `--live`, selected w/ `--live` | integration | `uv run pytest .../test_live_probe.py -q` then `--live` | ❌ Wave 0 (PROVEN this session) |
| HARN-05 | findings template exists + documented (classes, lifecycle, ART header) | doc + smoke | review `.planning/verification/<pkg>-findings.md` template; optional writer unit test | ❌ Wave 0 |
| HARN-06 | capture→anonymize→fixture: denylist replaces PII, preserves shape/format, raw stays gitignored | unit | `uv run pytest .../test_anonymize.py -q` (assert PII gone, AR decimal kept, shape equal) | ❌ Wave 0 |
| (D-12) | `schema_of` reduces payload to keys+types, no values | unit | `uv run pytest .../test_schema.py -q` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** the unit file for the helper just written (e.g. `uv run pytest packages/<pkg>/tests/test_redaction.py -q`)
- **Per wave merge:** `uv run pytest` (full offline suite) + `uv run ruff check verification main_*.py conftest.py` + `uv run mypy verification`
- **Phase gate:** full suite green (default run shows live test **deselected**), `--live` run shows it selected+passed, ruff + mypy strict green on the new tooling, before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] root `conftest.py` — registers `live` marker + `--live` + deselect hook (covers HARN-04)
- [ ] `verification/` module + `__init__.py` (+ submodules per chosen split)
- [ ] unit tests for each helper: `test_env_gate.py`, `test_mutation_gate.py`, `test_redaction.py`, `test_anonymize.py`, `test_schema.py` — placed under a package's `tests/` (so `testpaths=["packages"]` collects them) OR decide a home for tooling tests
- [ ] one `@pytest.mark.live` example test (network-free, copyable)
- [ ] `.planning/verification/<pkg>-findings.md` documented template
- [ ] `.gitignore` entry for `.planning/verification/captures/`
- [ ] ruff/mypy invocation covering `verification/`, root `main_*.py`, root `conftest.py` (they are outside the current `files`/`src` globs)

> **Tooling-test placement note:** `testpaths = ["packages"]` means pytest only collects under `packages/`. Tests for `verification/` helpers must either live under some `packages/<pkg>/tests/` (importing `verification`, which is on sys.path during pytest too — confirmed) or the plan must extend `testpaths`. Recommend placing harness tests under an existing package's `tests/` (e.g. a neutral one) or extending `testpaths` to include a root `tests/` dir — a planning decision to make explicit.

## Security Domain

> `security_enforcement` not disabled in config → section included. This phase IS a security phase (its purpose is preventing credential leakage and accidental mutation).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Phase touches no auth flow (clients own it); only *reads* env var presence |
| V3 Session Management | no | n/a |
| V4 Access Control | yes | Mutation guard = a hard gate preventing destructive ops unless explicitly + sandbox-only enabled (HARN-02) |
| V5 Input Validation | partial | `require_env` validates env presence; anonymizer validates/normalizes payload shapes |
| V6 Cryptography | no | No crypto introduced — do NOT hand-roll hashing for "redaction"; truncate-prefix only (D-13) |
| V7 Error Handling & Logging | yes | Redaction (HARN-03) = keeping secrets out of stdout/logs/reports; this is the core control |
| V8 Data Protection | yes | PII anonymization before any fixture is committed (HARN-06); raw capture stays gitignored (HARN-06) |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Token/password printed to stdout or committed in a fixture | Information Disclosure | `redact()` at source + `safe_print` second layer; PII denylist + manual review gate (D-10/D-13) |
| Raw PII payload committed to git | Information Disclosure | Two-stage pipeline: raw → gitignored `captures/`; only anonymized fixture is committable (D-11) |
| Accidental live order mutation (money/positions) | Tampering | `VERIFY_MUTATING=1` AND `"remarkets" in _base_url` double gate; default SKIPPED (HARN-02/D-16) |
| Running against prod by misconfigured base URL | Tampering / Elevation | Guard asserts resolved `_base_url` contains `remarkets` at call time, not a hard-coded constant |
| Empty-secret masking corrupting logs (DoS-ish output corruption) | — (reliability) | `len(secret) >= 4` guard in `safe_print` (VERIFIED pitfall) |

## Sources

### Primary (HIGH confidence)
- Empirical, this session (uv 0.9.0, real repo): `verification/` import under `uv run --package iol-client python main_*.py` and plain `uv run`; pytest collection unaffected (`testpaths=["packages"]`); root `conftest.py` `--live` deselect/select proven; per-package autouse fixture coexistence under `--import-mode=importlib`.
- `pyproject.toml` (root) — pytest `--strict-markers`/`--strict-config`/`testpaths`/`importlib`; ruff `src`; mypy `files`; dev deps.
- `.planning/codebase/TESTING.md`, `STRUCTURE.md`, `CONVENTIONS.md` — conventions, conftest autouse pattern, `Regression: ... (issue #NNN)`.
- `packages/matriz-client/src/matriz_client/client.py:58` — `_base_url` resolution (remarkets default) for the mutation guard.
- `packages/*/.env.example` + `.env` presence check — env var names per package; which `.env` exist.

### Secondary (MEDIUM confidence)
- WebSearch (verified against concourse #4656, pythoncentral, databricks community) — Python secret-redaction pitfalls: empty-string mangling, over-aggressive substring masking, hashing-as-obfuscation anti-pattern.

### Tertiary (LOW confidence)
- Faker package suitability (not installed/verified this session — network sandboxed). Marked `[ASSUMED]`; rejected on design grounds regardless.

## Metadata

**Confidence breakdown:**
- Importability of `verification/` (the open research item): HIGH — verified empirically against the real toolchain, not from training.
- pytest `--live` mechanism: HIGH — proven end-to-end (deselect + select + strict-markers + autouse coexistence).
- Redaction pitfalls: MEDIUM-HIGH — corroborated by multiple sources + matches stdlib behaviour.
- Anonymization / snapshot design: MEDIUM — sound stdlib design; per-package denylist specifics are a Phase 2–5 concern.
- Findings format: HIGH — fully specified by CONTEXT D-07/08/09.

**Research date:** 2026-05-27
**Valid until:** 2026-06-26 (stable stdlib + pytest APIs; re-verify only if uv major version or pytest 9 lands)
