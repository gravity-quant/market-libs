# Phase 1: Safety Harness & Verification Infrastructure - Pattern Map

**Mapped:** 2026-05-27
**Files analyzed:** 16 (8 new `verification/` modules, 1 root `conftest.py`, 1 aggregate runner, 5 driver edits, ≥1 live example + helper unit tests)
**Analogs found:** 13 / 16 with strong analog; 3 net-new infra (no codebase precedent — RESEARCH.md is the source)

> **Scope reminder (CONTEXT D-05/D-06):** the `verification/` file split is Claude's
> discretion. The recommended split below maps cleanly onto distinct analogs; a single
> `verification/__init__.py` is equally valid. Whichever split is chosen, every analog and
> convention below still applies per-helper.

> **Universal conventions (apply to every new file — CONVENTIONS.md / pyproject.toml):**
> - First non-docstring line is `from __future__ import annotations` (mandatory, uniform).
> - Module-level docstring in Spanish describing purpose; `::` code blocks for usage.
> - ruff: line-length 100, double quotes, 4-space indent; rule sets E/W/F/I/B/UP/SIM/RUF/ASYNC/PIE/PT/RET/TID.
> - mypy `strict = true` — every def fully typed, no untyped defs, no implicit Optional.
> - Modules `snake_case.py`; private helpers `_snake_case`; constants `SCREAMING_SNAKE_CASE`.
> - Explicit `__all__` in any module callers import from.
> - **Critical (Pitfall 2):** `verification/`, root `main_*.py`, root `conftest.py` are OUTSIDE
>   the `[tool.ruff] src` and `[tool.mypy] files` globs. The plan MUST add explicit
>   `uv run ruff check verification main_*.py conftest.py` and `uv run mypy verification`.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `verification/__init__.py` | config (barrel) | n/a | `packages/*/src/*/__init__.py` | role-match |
| `verification/env_gate.py` (`require_env`) | utility | transform/validation | `packages/higyrus-client/src/higyrus_client/_params.py` | role+flow exact |
| `verification/redaction.py` (`redact`, `safe_print`) | utility | transform | `packages/ambito-financiero-client/src/ambito_financiero_client/_parsing.py` | role+flow exact |
| `verification/mutation_gate.py` (`mutating_allowed`) | guard/middleware | request-response (gate) | `matriz_client/client.py` `_ensure_token` + `_base_url` read | role-match |
| `verification/schema.py` (`schema_of`) | utility | transform | `higyrus_client/_params.py` (recursive coerce in `models.py`) | flow-match |
| `verification/anonymize.py` (`Denylist`, `anonymize`) | utility + model | transform | `higyrus_client/models.py` (`SafeModel` recursive + frozen dataclass) | role+flow match |
| `verification/capture.py` (raw payload dump) | utility | file-I/O | `ambito_financiero_client/_parsing.py` (closest internal util) | partial (no file-I/O precedent) |
| `verification/findings.py` (writer / template) | utility | file-I/O | none — **net-new** | no analog |
| `conftest.py` (root) | config (test) | event-driven (pytest hooks) | `packages/*/tests/conftest.py` (autouse fixtures) | role-match |
| `main_verify.py` (aggregate runner) | entry point | batch/orchestration | `main_*.py` drivers + (subprocess: `uv run --package` cmd) | role-match |
| `main_iol.py` (extend) | entry point | request-response | itself + `iol-client/.env.example` | self/exact |
| `main_higyrus.py` (extend) | entry point | request-response | itself + `higyrus-client/.env.example` | self/exact |
| `main_matriz.py` (extend) | entry point | request-response + mutation gate | itself + `matriz_client/client.py:58` | self/exact |
| `main_ambito_financiero.py` (extend) | entry point | request-response (no auth) | itself (already has try/except NoData) | self/exact |
| `main_wallets.py` (extend) | entry point | request-response | itself + `wallets-client/.env.example` | self/exact |
| `packages/<pkg>/tests/test_live_probe.py` (example) | test | event-driven | `iol-client/tests/test_client.py` + RESEARCH.md §"Trivial proven live test" | exact (verbatim in RESEARCH) |
| `packages/<pkg>/tests/test_*.py` (helper units) | test | request-response | `matriz-client/tests/test_client.py`, `test_models.py` | exact |

## Pattern Assignments

### `verification/env_gate.py` — `require_env` (utility, validation/transform)

**Analog:** `packages/higyrus-client/src/higyrus_client/_params.py` (pure stdlib helper module: `__future__` import, `__all__`, fully-typed small functions, no third-party deps).

**Imports / header pattern** (from `_params.py:20-25`):
```python
from __future__ import annotations

from datetime import date
from typing import Any

__all__ = ["drop_none", "format_bool", "format_date"]
```
For `env_gate.py`: `import os`, `import sys`, `__all__ = ["require_env"]`.

**Core pattern** (RESEARCH.md §"`require_env`", VERIFIED design — copy exactly):
```python
def require_env(pkg: str, names: list[str]) -> bool:
    """True si todas las vars existen; si faltan, imprime SKIPPED y devuelve False."""
    missing = [n for n in names if not os.getenv(n)]
    if missing:
        print(f"SKIPPED {pkg}: missing {', '.join(missing)}")
        return False
    return True
```

**Conventions it must follow:** the `SKIPPED <pkg>: missing X, Y` line is verbatim from
roadmap success criteria — do not reword. `require_env` must NOT raise / `exit(1)`; the
driver decides to `sys.exit(0)` (Pitfall 6). Env-var names per package come from
`.env.example` (verified): IOL → `IOL_USER`,`IOL_PASSWORD`; HIGYRUS → `HIGYRUS_USER`,
`HIGYRUS_PASSWORD`,`HIGYRUS_BASE_URL`; PRIMARY → `PRIMARY_USER`,`PRIMARY_PASSWORD`;
WALLETS → `WALLETS_TOKEN`,`WALLETS_BASE_URL`; Ámbito → none required.

---

### `verification/redaction.py` — `redact`, `safe_print` (utility, transform)

**Analog:** `packages/ambito-financiero-client/src/ambito_financiero_client/_parsing.py`
(minimal stdlib transform module, Spanish docstring, single-line typed function).

**Core pattern** (RESEARCH.md §"Pattern 3", VERIFIED-against-pitfalls — copy exactly):
```python
from __future__ import annotations
import os


def redact(value: str | None, *, keep: int = 4) -> str:
    """Devuelve sólo un prefijo + elipsis para un valor sensible."""
    if not value:
        return "<empty>"
    if len(value) <= keep:
        return "…"
    return f"{value[:keep]}…"


def safe_print(text: str, secrets: list[str]) -> None:
    """Imprime `text` enmascarando cualquier valor de credencial conocido."""
    masked = text
    for secret in secrets:
        if secret and len(secret) >= 4:   # Pitfall 3: never replace "" or short values
            masked = masked.replace(secret, "‹REDACTED›")
    print(masked)
```

**Conventions / guardrails (security-critical, D-13):** the `len(secret) >= 4` guard is
mandatory (Pitfall 3 — empty-string masking corrupts output, concourse #4656). `keep=4`
prefix is the default intent (Claude's discretion on exact length). Never echo credential
globals (`print(client._token)`) — redact the value at source, `safe_print` is the second
layer. Use the keyword-only `*, keep:` arg style matching CONVENTIONS.md function design.

---

### `verification/mutation_gate.py` — `mutating_allowed` (guard, request-response gate)

**Analog:** `packages/matriz-client/src/matriz_client/client.py:57-65` (module-level state
incl. `_base_url`) and its `_ensure_token` gating logic. This is the only "read resolved
module state to decide a gate" precedent.

**Source module state being read** (`client.py:58`, VERIFIED):
```python
_base_url: str = os.getenv("PRIMARY_BASE_URL", "https://api.remarkets.primary.com.ar").rstrip("/")
```

**Core pattern** (RESEARCH.md §"Mutation guard", design per D-16 — copy exactly):
```python
from __future__ import annotations
import os
import matriz_client


def mutating_allowed() -> bool:
    """Solo permite mutaciones con flag opt-in Y base URL remarkets."""
    if os.getenv("VERIFY_MUTATING") != "1":
        print("SKIPPED (mutating, guard off)")
        return False
    base = matriz_client.client._base_url  # resolved module state — read only, never echo
    if "remarkets" not in base:
        print("SKIPPED (mutating, guard off)")
        return False
    return True
```

**Conventions / guardrails (D-16, Pitfall 5):** read the LIVE resolved
`matriz_client.client._base_url` at call time — never a hard-coded constant (a
`configure(base_url=prod)` override must be caught). Both conditions required. The
`SKIPPED (mutating, guard off)` line is verbatim from roadmap criteria. Reading private
module state is explicitly allowed for gating (A2) — read, never echo.

---

### `verification/schema.py` — `schema_of` (utility, transform)

**Analog:** the recursive `_coerce` walk in `packages/higyrus-client/src/higyrus_client/models.py:48-75`
(recursive dict/list/scalar dispatch). `schema_of` mirrors its structure but emits
type-name strings, never values.

**Core pattern** (RESEARCH.md §"Pattern 4", design — copy exactly):
```python
from __future__ import annotations
from typing import Any


def schema_of(payload: Any) -> Any:
    """Reduce un payload a su estructura: claves + tipos, nunca valores."""
    if isinstance(payload, dict):
        return {k: schema_of(v) for k, v in sorted(payload.items())}
    if isinstance(payload, list):
        return [schema_of(payload[0])] if payload else []
    return type(payload).__name__   # "str" | "int" | "float" | "bool" | "NoneType"
```

**Conventions:** PII-free by construction (no values) — this is the property that lets the
snapshot be committable in Phase 2. Snapshot file = pretty-printed JSON of `schema_of(raw)`.
Anti-pattern: never include values (Pitfall / anti-pattern list).

---

### `verification/anonymize.py` — `Denylist`, `anonymize`, `_synthetic` (utility + model, transform)

**Analog:** `packages/higyrus-client/src/higyrus_client/models.py` — for (a) the frozen
`@dataclass(frozen=True, slots=True)` model convention and (b) the recursive
payload-walk (`_coerce`). `Denylist` follows the project's model design verbatim:

**Model convention** (CONVENTIONS.md "Model Design" + `models.py` style):
```python
@dataclass(frozen=True, slots=True)
class Denylist:
    pkg: str
    keys: frozenset[str]
    replacements: dict[str, str] = field(default_factory=dict)
```

**Core recursive pattern** (RESEARCH.md §"Anonymization data model", design — copy exactly):
```python
def anonymize(payload: Any, deny: Denylist) -> Any:
    if isinstance(payload, dict):
        return {
            k: (deny.replacements.get(k, _synthetic(k, v)) if k in deny.keys
                else anonymize(v, deny))
            for k, v in payload.items()
        }
    if isinstance(payload, list):
        return [anonymize(x, deny) for x in payload]
    return payload
```

**Conventions / guardrails (D-10):** format-preserving synthetic replacement (stdlib `re`,
NOT Faker — A4). Non-PII format-relevant values (AR decimal `"1.415,00"` — see the
`parse_ar_decimal` analog below) MUST be preserved so the regression still reproduces.
Mandatory manual review gate before any fixture is committed; raw capture never leaves the
gitignored staging dir (D-11).

**Format-preservation cross-reference** (`_parsing.py:6-8`, why AR decimals must survive):
```python
def parse_ar_decimal(value: str) -> float:
    """Convierte un decimal en formato argentino (`"1.415,00"`) a float."""
    return float(value.replace(".", "").replace(",", "."))
```

---

### `verification/capture.py` — raw payload dump (utility, file-I/O)

**Analog:** no file-I/O precedent in the codebase (clients are HTTP-only). Closest is the
stdlib-util style of `_parsing.py`. Use `pathlib` + `json` (RESEARCH.md Standard Stack).

**Pattern (from RESEARCH.md architecture diagram + D-11):** dump raw payload to
`.planning/verification/captures/<pkg>-<ep>.json` (the GITIGNORED staging dir). Use
`json.dumps(..., indent=2, ensure_ascii=False)` and `pathlib.Path(...).write_text(...)`.

**Guardrail (Pitfall / anti-pattern):** raw PII-bearing payloads must land ONLY in the
gitignored `.planning/verification/captures/` — never anywhere committable. The
`.gitignore` entry for `captures/` is part of this phase (see Shared Patterns).

---

### `verification/findings.py` — findings writer / template (utility, file-I/O)

**Analog:** none — **net-new infra**. Format is fully specified by CONTEXT D-07/08/09 and
RESEARCH.md §"Findings file template". The writer is an optional helper; the documented
template is the deliverable.

**Template to emit** (RESEARCH.md §"Findings file template", path `.planning/verification/<pkg>-findings.md`):
- Run-context header (Timestamp ISO-8601, resolved base URL/env, market-hours note).
- Index table: columns `ID | Class | Surface | Status`.
- One detailed section per finding: Class · Surface · Status, Expected/Actual/Diff, Regression link.
- Classes fixed (D-09): `SHAPE, AUTH, ERROR-MAP, PARAM, SYNC-ASYNC-DRIFT, NO-DATA, ANTI-BOT`.
- Status lifecycle (D-08): `OPEN → CONFIRMED → FIXED` + terminal `EXPECTED/NO-FIX`. No severity field.

---

### `conftest.py` (root) — `live` marker + `--live` flag (config, pytest hooks)

**Analog:** `packages/*/tests/conftest.py` (e.g. `iol-client/tests/conftest.py`) for the
`from __future__ import annotations` + `import pytest` + typed hook/fixture style. The root
conftest adds collection hooks (not autouse fixtures) — those package conftests stay scoped.

**Core pattern** (RESEARCH.md §"Pattern 2", VERIFIED end-to-end against real pyproject — copy exactly):
```python
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

**Conventions / guardrails:** marker MUST be registered or `--strict-markers`/`--strict-config`
fail collection (D-03). Use `deselect` not `skip` (D-03 / A3: "collected-but-deselected").
`testpaths=["packages"]` means pytest never collects `verification/` — so this conftest lives
at repo root but the harness tests live under `packages/<pkg>/tests/` (see tooling-test note).
Must coexist with per-package autouse conftests via `--import-mode=importlib` (already set).

---

### `main_verify.py` — aggregate runner (entry point, batch/orchestration)

**Analog:** the five `main_*.py` drivers (entry-point shape: module docstring with `uv run`
usage `::` block, `from __future__ import annotations`, `def main() -> None:`,
`if __name__ == "__main__": main()`).

**Header/entry shape** (from `main_iol.py:1-9, 16-25`):
```python
"""... docstring with `uv run ...` :: usage block ..."""
from __future__ import annotations
# imports

def main() -> None:
    ...

if __name__ == "__main__":
    main()
```

**Recommended core (RESEARCH.md Open Question 1):** subprocess-per-driver via
`uv run --package <pkg> python main_<name>.py` (mirrors the exact Phases 2-5 command,
isolates module-level singleton state, lets each driver `exit(0)` on SKIPPED). Capture
stdout per child; print a RAN/SKIPPED aggregate. MUST never halt on a SKIPPED (D-14).
(Subprocess vs in-process is Claude's discretion — subprocess recommended.)

---

### `main_*.py` (extend all five) — drivers (entry point, request-response)

**Analog:** each driver is its own analog — extend in place, do not rewrite. The existing
shape (docstring + `__future__` + `main()` + `__main__` guard) is preserved; gating /
redaction / capture wrap around the existing login + calls.

**Per-driver extension recipe:**
1. `from verification import require_env, redact, safe_print, ...` (zero-config import —
   repo root is on `sys.path[0]` because the script lives at root; VERIFIED, RESEARCH.md Pattern 1).
2. Gate at top of `main()`: `if not require_env("<pkg>", [...]): sys.exit(0)` (clean exit, Pitfall 6).
3. Replace raw token/cred prints with `redact(...)` and route output dicts through `safe_print(..., secrets)`.
4. Wire `capture(payload)` for the live payloads to be captured.

**Per-driver specifics:**
- `main_iol.py` — current `print(f"   token: {token[:12]}...")` (line 21) must become a
  `redact()` call. Env: `IOL_USER`, `IOL_PASSWORD`.
- `main_higyrus.py` — env `HIGYRUS_USER`, `HIGYRUS_PASSWORD`, `HIGYRUS_BASE_URL`.
- `main_matriz.py` — additionally gate any order-mutation call behind
  `verification.mutation_gate.mutating_allowed()`. Env: `PRIMARY_USER`, `PRIMARY_PASSWORD`.
  (Note: order placement is never run live even in sandbox — the guard is belt-and-suspenders.)
- `main_ambito_financiero.py` — no `require_env` (no creds). Already models the
  try/except + graceful-message pattern (lines 30-35) — keep it.
- `main_wallets.py` — env `WALLETS_TOKEN`, `WALLETS_BASE_URL`; already has try/except
  `WalletsClientError` (lines 23-27) — keep, add redaction.

---

### `packages/<pkg>/tests/test_live_probe.py` — live example (test, event-driven)

**Analog:** `iol-client/tests/test_client.py:1-11` for the test-file header/import shape;
RESEARCH.md §"Trivial proven live test" for the body (copy verbatim).

```python
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

**Conventions:** must be placed under a `packages/<pkg>/tests/` dir (so `testpaths=["packages"]`
collects it). Network-free (D-04). Serves as the copyable template for Phases 2-5.

---

### `packages/<pkg>/tests/test_*.py` — helper unit tests (test, request-response)

**Analog (capsys/output assertions + monkeypatch module state):**
`packages/matriz-client/tests/test_client.py:19-81` shows the `monkeypatch.setattr(_client, "_base_url"/"_token", ...)`
pattern needed to test `mutating_allowed` and gating; `test_models.py:172-180` shows the
`Regression: ... (issue #NNN)` docstring convention emitted stubs must carry.

**`Regression` docstring convention** (VERIFIED `test_models.py:173` — the only instance):
```python
def test_market_data_snapshot_close_is_entry_value_not_scalar() -> None:
    """Regression: CL viene como objeto {price, size, date}, no como float (issue #102)."""
```

**Test conventions:** `from pytest_httpx import HTTPXMock`; `httpx_mock.add_response(url=..., json=...)`
with full-URL assertions (TESTING.md). Use `capsys` to assert the exact `SKIPPED ...` lines
(HARN-01/02/03 test map). `monkeypatch` to isolate module state. Note: no test currently
uses `capsys` (grep confirms) — these will be the first. Place under `packages/<pkg>/tests/`.

## Shared Patterns

### Zero-config import of `verification/`
**Source:** RESEARCH.md §"Pattern 1" (VERIFIED empirically this session).
**Apply to:** all 5 drivers + `main_verify.py`.
```python
from __future__ import annotations
from verification import require_env, redact, safe_print  # resolves with zero config
```
Repo root is on `sys.path[0]` because `main_*.py` live at root. Do NOT add `verification`
to `[tool.uv.workspace] members`, do NOT give it a `pyproject.toml`, do NOT `sys.path.insert`
(Pitfall 1 / Anti-pattern: would trigger build + frozen-CI re-resolve).

### Redaction (defense-in-depth)
**Source:** `verification/redaction.py` (D-13).
**Apply to:** every driver print that could contain a token/password; build the `secrets`
list from resolved credential globals filtered to `len >= 4`.

### Mutation gate
**Source:** `verification/mutation_gate.py` (D-16), reads `matriz_client.client._base_url:58`.
**Apply to:** `main_matriz.py` order-mutation paths only.

### Module-docstring + entry-point shape
**Source:** all `main_*.py` (e.g. `main_iol.py:1-9`).
**Apply to:** `main_verify.py` and every extended driver — keep the Spanish `::` usage block
and the `if __name__ == "__main__": main()` guard.

### Stdlib-only helper module shape
**Source:** `higyrus_client/_params.py`, `ambito_financiero_client/_parsing.py`.
**Apply to:** every `verification/*.py` — `from __future__ import annotations` first,
explicit `__all__`, fully-typed functions, Spanish docstrings, no third-party deps.

### `.gitignore` + new dirs
**Source:** existing `.gitignore` (`.env`/`.env.local` already excluded).
**Apply to:** add `.planning/verification/captures/` to `.gitignore` (D-11 — raw PII staging
must be gitignored by construction). Create `.planning/verification/` for findings.

### Explicit ruff/mypy invocation for new tooling (Pitfall 2)
**Source:** `pyproject.toml` `[tool.ruff] src` and `[tool.mypy] files` (both package-scoped).
**Apply to:** the plan must add `uv run ruff check verification main_*.py conftest.py` and
`uv run mypy verification` — the new code is outside the existing globs and would otherwise
silently escape the strict gates.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `verification/findings.py` | utility | file-I/O | No findings/report writer exists; format fully specified by CONTEXT D-07/08/09 + RESEARCH.md template. Use that template, not a codebase analog. |
| `verification/capture.py` | utility | file-I/O | Clients are HTTP-only — no file-write precedent. Use stdlib `pathlib`+`json` per RESEARCH.md Standard Stack; follow `_parsing.py` for the module shape only. |
| `conftest.py` collection hooks | config | event-driven | Package conftests only define autouse fixtures; no `pytest_addoption`/`pytest_collection_modifyitems` precedent. Use RESEARCH.md Pattern 2 (VERIFIED). |

> For all three, RESEARCH.md provides VERIFIED/specified patterns — planner should reference
> those sections directly rather than a codebase file.

## Metadata

**Analog search scope:** repo root (`main_*.py`, no existing `conftest.py`/`verification/`),
`packages/*/src/*/` (client.py, models.py, _params.py, _parsing.py, __init__.py),
`packages/*/tests/` (conftest.py, test_client.py, test_models.py), root `pyproject.toml`,
`packages/*/.env.example`, `.gitignore`.
**Files scanned:** 18 read in full or in targeted ranges; ~13 distinct analog sources.
**Pattern extraction date:** 2026-05-27
**Key empirical finding (RESEARCH.md):** `verification/` is importable with zero config from
root drivers (`sys.path[0]`), and the `--live` deselect mechanism is proven against the real
`--strict-markers`/`--strict-config`/`importlib` pytest config.
