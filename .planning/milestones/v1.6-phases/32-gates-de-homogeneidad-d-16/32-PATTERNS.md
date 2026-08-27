# Phase 32: Gates de homogeneidad + D-16 - Pattern Map

**Mapped:** 2026-08-25
**Files analyzed:** 16 (5 new, 11 modified)
**Analogs found:** 15 / 16

> Every excerpt below was read from the working tree today. Line numbers are current.
> RESEARCH.md's corrections C-4/C-5 (line drift in CONTEXT.md) are already applied here.

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `tools/check_surface_types.py` (NEW) | CI gate / utility | file-I/O + AST transform | `tools/check_uniform_structure.py` | exact |
| `tools/surface_parity.py` (NEW) | shared test helper | runtime introspection / transform | `verification/test_public_surface.py:56-85` (`_kind`/`_stringify_signature`) + `tools/check_decode_intactness.py:44-82` (rule table) | role-match (composite) |
| `packages/<one-pkg>/tests/test_surface_types_red.py` (NEW ×1) | test (RED fixture) | file-I/O against `tmp_path` | `packages/iol-client/tests/test_typed_surface_red.py` | exact |
| `packages/<pkg>/tests/test_surface_parity.py` (NEW ×6) | test | runtime introspection | `packages/ambito-financiero-client/tests/test_harness_schema.py` (Patrón 1 import) + `verification/test_main_matriz_uses_single_client_instance.py` (bounds) | exact |
| `packages/market-data-client/tests/test_core_boundary_red.py` (NEW) | test (RED fixture) | subprocess / event-driven | `tools/check_decode_intactness.py:362-386` (fixed-argv subprocess) | partial (no import-linter RED precedent exists) |
| `packages/market-data-client/src/market_data_client/aio.py` (MOD, D-09) | client shell | request-response config | `packages/matriz-client/src/matriz_client/aio.py:805-814` | exact |
| `.github/workflows/ci.yml` (MOD) | config | CI | `ci.yml:56-60` (`uniform-structure` step) | exact |
| `pyproject.toml` (MOD, line 97) | config | declarative list | `pyproject.toml:97` itself (append one entry) | exact |
| `verification/test_public_surface.py` (MOD, comment only) | test | documentation | `packages/market-data-client/tests/test_public_surface_market_data.py:8-20` (the reciprocal comment) | exact |
| `tools/check_decode_intactness.py` (MOD, `resolved_by`) | CI gate | declarative roster | `check_decode_intactness.py:188-201` itself | exact |
| **Wave 0** `packages/matriz-client/tests/test_decode.py` | test | fix | `packages/iol-client/tests/test_decode.py:173,297,361,1092` | exact |
| **Wave 0** `packages/matriz-client/tests/test_ws_decode_mode.py` | test | fix | same | exact |
| **Wave 0** `packages/higyrus-client/tests/test_decode.py` | test | fix | `packages/iol-client/tests/test_decode.py:678,722` | exact |
| **Wave 0** `packages/ambito-financiero-client/tests/test_decode.py` | test | fix | same | exact |

---

## Pattern Assignments

### `tools/check_surface_types.py` (NEW — CI gate, AST transform)

**Analog:** `tools/check_uniform_structure.py` (166 lines, read in full). This is the
template: single-check, stdlib-only, roster-from-disk, anti-vacuity discipline.

**Module docstring skeleton** — carry over these four named sections verbatim in
structure (`check_uniform_structure.py:1-52`):

```
"""<one-line gate purpose> (Phase 32, GATE-TYP-01).

Run it as::

    uv run python tools/check_surface_types.py

WHY THIS IS A ``tools/`` SCRIPT IN THE ``lint`` JOB
===================================================
1. **It cannot live in the per-package ``test`` job.** ...cross-package by nature...
2. **It cannot live under ``verification/``.** The ``test`` job passes an explicit
   ``packages/${{ matrix.package }}`` path ... That directory has consequently
   **never executed in CI**.

STDLIB-ONLY, ON PURPOSE
=======================
``pathlib`` and ``sys`` are the only imports (D-12)...

THE ROSTER COMES FROM DISK
==========================
There is deliberately **no hardcoded list of package names** in this file...
"""
```

> **D-05 / OQ-2 note goes in the `WHY THIS IS A tools/ SCRIPT` slot**: record here that
> `ROADMAP.md:25` says "job de CI nuevo" but Phase 31 D-12 fixes "step en `lint`", and that
> DT-06's `_request`/`httpx.Response` exemption is *subsumed* by the `_`-prefix rule (C-6 /
> Pitfall 9), not forgotten.

**Failure primitive + `main()`** (`check_uniform_structure.py:71-76, 146-165` — verbatim shape):

```python
class CheckFailure(Exception):
    """Raised by a check with a fully formed, operator-readable message."""


def _fail(message: str) -> CheckFailure:
    return CheckFailure(message)


def main() -> int:
    checks = (check_surface_types,)
    failures = 0
    for check in checks:
        try:
            print(check())
        except CheckFailure as exc:
            failures += 1
            print(f"::error::Phase 32 GATE-TYP-01 surface types -- {exc}", file=sys.stderr)
    if failures:
        print(
            f"::error::surface-types gate FAILED ({failures} of {len(checks)} checks)",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

**Import-root resolution with `.egg-info` filter — COPY VERBATIM**
(`check_uniform_structure.py:65-97`). Per RESEARCH's Runtime State Inventory, `*.egg-info`
directories exist under `packages/*/src/` today; omitting this filter makes the gate report
every package as unresolvable:

```python
_BUILD_ARTIFACT_SUFFIX = ".egg-info"


def _import_root(package_dir: Path) -> Path | None:
    """The single ``src/<import_name>/`` directory of a package, or ``None``.

    ``None`` means "unresolvable", and the caller turns that into a problem line --
    never into a skip.
    """
    src = package_dir / "src"
    if not src.is_dir():
        return None
    candidates = [
        child
        for child in sorted(src.iterdir())
        if child.is_dir() and not child.name.endswith(_BUILD_ARTIFACT_SUFFIX)
    ]
    if len(candidates) != 1:
        return None
    return candidates[0]
```

**Problem-accumulation + empty-scan-is-a-failure** (`check_uniform_structure.py:100-143`) —
this is the anti-vacuity primitive. Note the two-space-indented `    ` prefix on every problem
line and the success string that *reports the count scanned*:

```python
def check_uniform_structure() -> str:
    problems: list[str] = []

    packages_dir = REPO_ROOT / "packages"
    package_dirs: list[Path] = []
    if not packages_dir.is_dir():
        problems.append(
            "    there is no `packages/` directory to scan -- that is a broken "
            "checkout, not a clean tree"
        )
    else:
        package_dirs = [child for child in sorted(packages_dir.iterdir()) if child.is_dir()]
        if not package_dirs:
            problems.append(
                "    `packages/` holds zero package directories -- an empty scan is a "
                "broken checkout, not a clean tree"
            )

    for package_dir in package_dirs:
        import_root = _import_root(package_dir)
        if import_root is None:
            problems.append(
                f"    package `{package_dir.name}` has no resolvable import root -- "
                f"expected exactly one package directory under "
                f"{package_dir.relative_to(REPO_ROOT)}/src/"
            )
            continue
        ...

    if problems:
        raise _fail("uniform structure is incomplete:\n" + "\n".join(problems))

    return (
        f"uniform structure: all {len(package_dirs)} packages under `packages/` carry "
        f"{required} in their import root"
    )
```

**Adaptation required (the only deltas from the analog):**

1. `REPO_ROOT` stays module-level as the **default only**, and every use of it inside the
   check body becomes a `root` parameter — D-04's injectable seam. The analog hardcodes
   `REPO_ROOT` at `check_uniform_structure.py:59` and threads it through
   `check_uniform_structure()` implicitly; the new gate must not.

   ```python
   REPO_ROOT = Path(__file__).resolve().parent.parent   # default only

   def check_surface_types(root: Path = REPO_ROOT) -> str:
       ...
   ```

2. Add `import ast`. Return-message must report **counts** (`N packages, M __all__ names,
   K defs scanned, 0 non-exempt`) so the RED fixture can assert on it and so the empty-scan
   failure mode is observable. Simulation baseline: 319 defs, 22 exempted, 0 hits.
3. Two extra empty-scan failures the analog has no counterpart for: "zero `__all__` names
   resolved" and "zero definitions scanned".
4. `ast.parse` only — never `eval`/`exec`; unparseable file is a **failure**, not a skip
   (ASVS V5, and the same rule as the analog's "unresolvable is a problem, never a skip").

**`__all__` → definition-site resolution** (verified 100% resolvable across 6 packages;
RESEARCH § Pattern 2). Use `ast.walk`, not "first match wins" — matriz and higyrus each have
**two** `ImportFrom` blocks from `.client`, and matriz imports from 8 submodules:

```python
init_tree = ast.parse((root / "packages" / d / "src" / m / "__init__.py").read_text())
site: dict[str, str] = {}
for node in ast.walk(init_tree):
    if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith(f"{m}."):
        submodule = node.module.split(".", 1)[1]
        for alias in node.names:
            site[alias.asname or alias.name] = submodule
```

**Exemption predicate** — the taxonomy is measured, not guessed (12 dunder / 1 underscore /
9 `to_dict`):

```python
def _is_exempt(name: str) -> str | None:
    if name.startswith("__") and name.endswith("__"):
        return "dunder"
    if name.startswith("_"):
        return "private-helper"   # subsumes every `_request` -- see OQ-2 note in docstring
    if name == "to_dict":
        return "serialize-out"
    return None
```

**Anti-patterns from this analog set (do NOT do):**
- Hardcode the 6-package roster (`check_uniform_structure.py:43-51` documents why).
- `import <pkg>` inside the gate — triggers `load_dotenv()` (both existing gates forbid it in
  their docstrings; `check_uniform_structure.py:17-19`).
- Walk `models.py` wholesale — reports 10 `to_dict` instead of the criterion's 9. Resolution
  must be `__all__`-scoped.

---

### `tools/surface_parity.py` (NEW — shared introspection helper, D-07/OQ-1)

**Location decision:** `tools/` (RESEARCH OQ-1 recommendation). Sits with the other two
cross-package gates; being pulled into per-package mypy runs by the importing tests is a
desirable side effect (`tools/*.py` is otherwise outside mypy's `files`).

**Analog A — the normalization rule table.** `tools/check_decode_intactness.py:44-82`. Copy the
*framing sentence* verbatim; it is what stops the rules being weakened ad hoc:

```
THE NORMALIZATION
=================

These rules are the **only sanctioned place** to record a legitimate difference
between the five copies. A red gate means a copy drifted; the fix is to revert
the drift or to add a rule here with a stated reason -- never to weaken the check
into a vacuous one.

1. ...
```

Numbered rules for this phase (RESEARCH § Sync/Async Parity, measured):

1. `httpx.Client` in a sync hint ≡ `httpx.AsyncClient` in the corresponding async hint.
2. Name `Client` on the sync side ≡ `AsyncClient` on the async side.
3. `aclose` (module and method) is async-only; `close` is sync-only.
4. Return types need no rule — no `Coroutine`/`Awaitable` annotations appear (verified).

**Analog B — `_kind()` ordering trap.** `verification/test_public_surface.py:56-71`, copy as-is
if the helper needs kind labels; the `iscoroutinefunction`-before-`isfunction` ordering is the
load-bearing part:

```python
def _kind(obj: Any) -> str:
    """Order matters: ``iscoroutinefunction`` is checked BEFORE ``isfunction``
    because async functions also satisfy ``isfunction``."""
    if inspect.isclass(obj):
        return "class"
    if inspect.iscoroutinefunction(obj):
        return "coroutine"
    if inspect.isfunction(obj) or inspect.ismethod(obj):
        return "function"
    if inspect.ismodule(obj):
        return "module"
    return type(obj).__name__
```

**Analog C — per-package literal bounds with a documented near-vacuous floor.**
Modelled on `verification/test_main_matriz_uses_single_client_instance.py:78-99`. **State the
metric once in the helper docstring and derive both columns** — this is Pitfall 4 (D-06 counts
*include* `Client`; D-08's integers *exclude* it, so pinning D-08 under a literal D-06
implementation fails by exactly 1 in 5 of 6 packages):

```python
# Per-package literal bounds (D-08). METRIC: module-level public names
# EXCLUDING the Client/AsyncClient class. The class-INCLUSIVE counts are
# each of these +1 (except wallets, which has no class pair at all).
_LOWER_BOUNDS = {
    "ambito_financiero_client": (2, 3),
    "iol_client": (6, 7),
    "higyrus_client": (7, 8),
    "matriz_client": (22, 23),
    "market_data_client": (19, 20),
    # wallets_client is a near-vacuous floor BY CONSTRUCTION: its only public
    # module-level name is `configure` (sync) / `configure` + `aclose` (async).
    # It is the one pre-Phase-7 package -- no Client/AsyncClient class pair at
    # all -- so this bound asserts almost nothing and MUST NOT be read as
    # coverage. Raising it is the job of the phase that gives wallets a Client.
    "wallets_client": (1, 2),
}
```

Docstring sentence to mirror from the analog (`:81-83`): *"Lower bound (>=1) is the
non-vacuity guard: the un-migrated driver constructs zero classes ... and so FAILS RED."*

**Anti-patterns (all measured, all in RESEARCH):**
- `__all__`-based comparison → `[] == []` in half the modules (D-06; the Phase 15 WR-01/WR-02
  failure mode).
- Raw `__annotations__` → strings under PEP 563. Always `typing.get_type_hints()`.
- `inspect.signature()` equality → false-positive on market-data's keyword-only reordering.
- Uniform numeric threshold → forbidden by D-08.

---

### `packages/<pkg>/tests/test_surface_parity.py` (NEW ×6 — thin delegating tests)

**Analog A — Patrón 1 cross-package import + the docstring that justifies it.**
`packages/ambito-financiero-client/tests/test_harness_schema.py:9-20`:

```python
"""...

Viven bajo ``packages/<pkg>/tests/`` porque ``testpaths=["packages"]`` no colecta
``verification/``; el módulo ``verification`` se resuelve porque la raíz del repo
está en ``sys.path`` (Patrón 1 de la investigación).
"""

from __future__ import annotations

from verification.capture import capture
from verification.schema import schema_of
```

Adapt the import to `from tools.surface_parity import ...` (`tools/` has no `__init__.py` but
resolves as an implicit namespace package under `pythonpath = ["."]`, `pyproject.toml:109` —
verified importable).

**Analog B — assert-with-a-message shape.**
`verification/test_main_matriz_uses_single_client_instance.py:97-99`:

```python
    assert 1 <= len(ctor_sites) <= 2, (
        f"{_DRIVER} constructs {len(ctor_sites)} client instance(s) (expected 1..2): {ctor_sites}"
    )
```

**Wallets adaptation (Pitfall 7) — assert the absence loudly, never `return` early.** Same
shape as Check D at `check_decode_intactness.py:635-641` ("exempt package has acquired a
`_decode.py`"):

```python
    # wallets is the one pre-Phase-7 package: no Client/AsyncClient pair exists.
    # Asserted, not skipped -- the day wallets GAINS a Client this fails and
    # forces enrollment on the class-parity axis.
    assert not hasattr(client_mod, "Client")
```

**Both axes.** Module-level parity *and* class-method parity (`Client` vs `AsyncClient`, equal
sized in all five class-bearing packages under the single `close`↔`aclose` rename). The
class axis is the stronger one; wallets is explicitly skipped on it, with the assertion above.

---

### `packages/<one-pkg>/tests/test_surface_types_red.py` (NEW — D-04 RED fixture)

**Analog:** `packages/iol-client/tests/test_typed_surface_red.py` (48 lines, read in full).

**Docstring pattern to mirror** (`:1-12`) — states *why the file lives under
`packages/<pkg>/tests/`* and *what machinery was deliberately rejected*:

```python
"""RED fixture for TYP-01: an attribute typo must be rejected, statically and at runtime.

This file is the executable form of the phase's guarantee. It lives under
``packages/iol-client/tests/`` because that path is what the CI mypy loop
typechecks (``ci.yml``, "mypy (tests por paquete)"); it deliberately does
**not** live in ``main_iol.py``, which mypy never sees (the global ``files``
setting covers ``packages/*/src`` only).

No mypy subprocess is spawned. D-10 rules that out explicitly...
"""
```

**Two-bound test structure** (upper bound = green on the real tree, lower bound = RED on an
injected regression), per RESEARCH § Injectable root:

```python
from tools.check_surface_types import CheckFailure, check_surface_types


def test_gate_is_green_on_the_real_tree() -> None:
    """Upper bound: today's tree has zero non-exempt hits."""
    assert "0 violation" in check_surface_types()


def test_gate_fails_on_an_injected_regression(tmp_path: Path) -> None:
    """Lower bound (non-vacuity): a deliberately broken tree MUST fail RED."""
    pkg = tmp_path / "packages" / "fake-client" / "src" / "fake_client"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text(
        "from fake_client.client import get_thing\n__all__ = ['get_thing']\n"
    )
    (pkg / "client.py").write_text(
        "from typing import Any\ndef get_thing() -> dict[str, Any]: ...\n"
    )
    with pytest.raises(CheckFailure, match="get_thing"):
        check_surface_types(root=tmp_path)
```

`tmp_path` over committed fixtures: nothing new lands under `packages/`, which would otherwise
trip `check_decode_intactness.py`'s Check D roster and `check_uniform_structure.py`'s
`models.py`/`types.py` requirement.

---

### `packages/market-data-client/tests/test_core_boundary_red.py` (NEW — D-02)

**No direct analog exists.** Grep confirms zero import-linter RED fixtures repo-wide. Compose
from two partial analogs.

**Partial analog A — fixed-argv subprocess, no shell** (`check_decode_intactness.py:362-386`).
Copy the security comment verbatim; it is the ASVS-relevant invariant:

```python
        # Fixed argv, no shell, no interpolated user input: the only variable
        # part is stdin, which is repository source this gate already reads.
        completed = subprocess.run(
            [sys.executable, "-m", "ruff", "format", ...],
            input=source,
            capture_output=True,
            text=True,
            check=False,
            cwd=REPO_ROOT,
        )
```

**Partial analog B — the `try/finally` restore (OQ-3 recommendation).** Cost premise corrected:
`lint-imports` measures **~0.07 s cold** (C-1), so the automated route is affordable:

```python
def test_core_boundary_contract_is_red_when_violated(tmp_path: Path) -> None:
    """D-02: prove the market_data_client._core contract actually catches a violation."""
    core = Path("packages/market-data-client/src/market_data_client/_core.py")
    original = core.read_text(encoding="utf-8")
    try:
        core.write_text(original + "\nfrom market_data_client import client  # noqa: F401\n")
        result = subprocess.run(["uv", "run", "lint-imports"], capture_output=True, text=True)
        assert result.returncode != 0
        assert "market_data_client._core does not depend on transport modules BROKEN" in result.stdout
    finally:
        core.write_text(original, encoding="utf-8")
```

The contract being proved is at `pyproject.toml:182-186`:

```toml
[[tool.importlinter.contracts]]
name = "market_data_client._core does not depend on transport modules"
type = "forbidden"
source_modules = ["market_data_client._core"]
forbidden_modules = ["market_data_client.client", "market_data_client.aio"]
```

---

### `packages/market-data-client/src/market_data_client/aio.py` (MODIFIED — D-09 fix)

**Analog:** `packages/matriz-client/src/matriz_client/aio.py:805-814` — the exact `ResourceWarning`
shape for a non-`async def` `configure` that cannot `await aclose()`:

```python
    if http_client is not None:
        if client._state.http_client is not None and client._state.http_client is not http_client:
            warnings.warn(
                "matriz_client.aio.configure(): replacing a live httpx.AsyncClient "
                "(via http_client=) without awaiting aclose() leaks the connection "
                "pool. Call `await matriz_client.aio.aclose()` before configure(...).",
                ResourceWarning,
                stacklevel=2,
            )
        client._state.http_client = http_client
```

**The gap being closed.** Sync (`client.py:762-775`) has `http_client: httpx.Client | None = None`
at position 8; async (`aio.py:776-788`) has no such parameter at all:

```python
# client.py:762-775 -- HAS http_client
def configure(
    *,
    base_url: str | None = None,
    client_id: str | None = None,
    client_secret: str | None = None,
    audience: str | None = None,
    auth0_token_url: str | None = None,
    token: str | None = None,
    token_expires_at: float | None = None,
    http_client: httpx.Client | None = None,     # <-- absent in aio.py
    mutating_allowed: bool | None = None,
    expected_host: str | None = None,
    strict_decode: bool | None = None,
) -> None:
```

The async docstring at `aio.py:797-798` already claims parity, which is what makes this
documented-as-inexistent drift rather than a known gap:

```
    (carry-forward). Esta semántica ESPEJA exactamente la superficie sync
    ``client.configure`` (WR-01 — el constraint dual sync/async exige que ambas
```

**Blast radius (all verified, all zero-change):**
- `AsyncClient.__init__` (`aio.py:119`) already accepts `http_client: httpx.AsyncClient | None`
  and assigns at `:155-156`.
- `_ClientState.http_client` is already typed `httpx.Client | httpx.AsyncClient | None`
  (`_state.py:119`).
- `aio.aclose()` (`:184-188`) already `isinstance`-asserts `httpx.AsyncClient` and awaits.
- Keyword-only ⇒ purely additive ⇒ not source-breaking for the Phase 34 re-publish.

Place the new block in `configure`'s body alongside the existing per-field `if ... is not None`
carry-forward chain (`aio.py:805-829` shows the exact style), and update the docstring so the
"ESPEJA exactamente" claim becomes true rather than aspirational.

---

### `.github/workflows/ci.yml` (MODIFIED — new `lint` step, D-05)

**Analog:** `ci.yml:56-60`. Append immediately after line 60. Copy the three-line comment
verbatim — it is the D-05 rationale in situ:

```yaml
      - name: uniform-structure (Phase 31 TYP-03 — models.py + types.py en los 6 paquetes)
        # Cross-package por naturaleza: NO va al job `test`, que corre per-package.
        # Tampoco puede vivir bajo `verification/`: el job `test` pasa un path
        # explícito que pisa `testpaths`, así que ese directorio nunca corrió en CI.
        run: uv run python tools/check_uniform_structure.py
```

New step:

```yaml
      - name: surface-types (Phase 32 GATE-TYP-01 — cero Any/dict[str, Any] en la superficie exportada)
        # Cross-package por naturaleza: NO va al job `test`, que corre per-package.
        # Tampoco puede vivir bajo `verification/`: el job `test` pasa un path
        # explícito que pisa `testpaths`, así que ese directorio nunca corrió en CI.
        # D-05: step en `lint`, NO job nuevo (Phase 31 D-12 supersede ROADMAP.md:25).
        run: uv run python tools/check_surface_types.py
```

**`uv run python`, never bare `python`** (Pitfall 6): all five `_decode.py` copies use PEP 695
`def _response_parser[**P, R](...)`, a `SyntaxError` on ≤3.11. `ci.yml:55` and `:60` already
establish the `uv run python` form.

Adding a *step* does not rename the *job*, so no branch-protection required-check update is
implied (a further argument for D-05 over a new job).

---

### `pyproject.toml` (MODIFIED — mypy `files`, the one real D-16 code edit)

Current state, line 97 — market-data absent:

```toml
files = ["packages/higyrus-client/src", "packages/wallets-client/src", "packages/matriz-client/src", "packages/iol-client/src", "packages/ambito-financiero-client/src"]
```

Append `"packages/market-data-client/src"`. Zero-fix: verified `Success: no issues found in
75 source files` with it added. Keep the existing one-line format (ruff does not reformat TOML).

The `root_packages` list (`:147-153`) and the market-data contract (`:182-186`) are **already
complete** — do not edit.

---

### `verification/test_public_surface.py` (MODIFIED — inline comment only, D-11)

**The list is NOT edited.** Current state, `:46-51`:

```python
_PACKAGES = [
    "ambito_financiero_client",
    "iol_client",
    "higyrus_client",
    "matriz_client",
]
```

**Analog for the comment's content:** the reciprocal note already written from the other side,
`packages/market-data-client/tests/test_public_surface_market_data.py:8-12`:

```python
The cross-package ``verification/test_public_surface.py`` and
``verification/test_sync_async_isolation.py`` EXCLUDE ``market_data_client`` (its
name is absent from their ``_PACKAGES`` lists), so neither guards this package's
export surface nor its sync/async name parity. This in-package net fills that gap
```

The new comment above `_PACKAGES` must (a) state that market-data and wallets are excluded
deliberately, (b) reference
`packages/market-data-client/tests/test_public_surface_market_data.py` **by path** as the
in-matrix coverage, and (c) state that `verification/` never runs in CI so a regenerated
snapshot would be red-invisible.

---

### `tools/check_decode_intactness.py` (MODIFIED — resolve the dangling forward reference)

The exemption record at `:188-201` names *this phase* as its resolver:

```python
EXEMPT_PACKAGES: tuple[ExemptPackage, ...] = (
    ExemptPackage(
        package=Package("wallets-client", "wallets_client"),
        reason=(
            "no _state.py, no _logging.py, no _core.py and no models.py; its request "
            "functions are module-level rather than methods, so there is nowhere to "
            "hold the decode mode flag and no bind site of the shape the other five have"
        ),
        resolved_by=(
            "Phase 31 (estructura uniforme -- the six packages gain the same file "
            "layout), with enrollment settled by Phase 32's D-16 reconciliation"
        ),
    ),
)
```

D-10's decision (wallets stays out of import-linter `root_packages` — structurally, for lack of
a `_core.py` to write a `forbidden` contract against) should be written back into
`resolved_by` so the forward reference stops dangling. The typed
`ExemptPackage(package, reason, resolved_by)` dataclass at `:162-168` is also the pattern to
reuse if the new surface gate or parity helper needs its own exemption record.

---

### Wave 0 — the 33 pre-existing mypy errors (MODIFIED tests)

Reproduced today, per package (the loop at `ci.yml:92-99` runs these one at a time; running
several paths in one mypy invocation fails on duplicate `conftest` modules instead):

| File | Errors | Codes |
|------|-------:|-------|
| `packages/matriz-client/tests/test_decode.py` | 28 | `attr-defined` ×20, `comparison-overlap` ×6, `arg-type` ×2 |
| `packages/matriz-client/tests/test_ws_decode_mode.py` | 1 | `arg-type` (line 355) |
| `packages/higyrus-client/tests/test_decode.py` | 2 | `func-returns-value` (624), `unused-ignore` (693) |
| `packages/ambito-financiero-client/tests/test_decode.py` | 2 | `func-returns-value` (799), `unused-ignore` (868) |

**Analog for the `attr-defined` class — the same file family, already green in iol and
market-data.** `packages/iol-client/tests/test_decode.py` accesses the identical custom
`LogRecord` attributes and passes strict mypy because each access carries a narrow ignore:

```python
# packages/iol-client/tests/test_decode.py:173
    return [(r.field_path, r.divergence) for r in records]  # type: ignore[attr-defined]

# :297
        (r.field_path, r.divergence, r.declared_type, r.observed_type)  # type: ignore[attr-defined]

# :361
    assert records[0].field_path == ".sobrante"  # type: ignore[attr-defined]

# :1092
    paths = [r.field_path for r in _divergences(caplog)]  # type: ignore[attr-defined]
```

The matriz offender is structurally identical (`test_decode.py:158`):

```python
def _pairs(caplog: pytest.LogCaptureFixture) -> list[tuple[str, str]]:
    return [(r.field_path, r.divergence) for r in _divergences(caplog)]
```

`getattr(record, key)` (`iol_client/tests/test_decode.py:435`) is the alternative where the
attribute name is dynamic.

**Analog for the `func-returns-value` class.** higyrus `:624` asserts on a function that only
ever returns `None`:

```python
                assert _decode.SILENT_SINK("M", ".campo", kind, "str", "int") is None
```

iol calls it bare, which is the green shape (`test_decode.py:678, 722`):

```python
    walk_model(_Scalars, {}, policy=POLICY, sink=_decode.SILENT_SINK)
```

**`unused-ignore` (higyrus `:693`, ambito `:868`)** — the ignore is genuinely dead; delete it:

```python
    return {f.name: filler.get(hints[f.name], []) for f in dataclasses.fields(cls)}  # type: ignore[arg-type]
```

**`comparison-overlap` (matriz `:285-288`)** — asserting a wire-typed value against a
mismatched literal after tolerant decode:

```python
    assert obj.i == "nope"
```

Constrain per A1: fix in **test code only**. Do **not** relax `pyproject.toml` strictness — that
would be a policy change needing user sign-off, not a mechanical fix.

---

## Shared Patterns

### Every new module starts with `from __future__ import annotations`
**Source:** mandatory per CLAUDE.md; present in all six analogs read
(`check_uniform_structure.py:54`, `test_typed_surface_red.py:14`,
`test_harness_schema.py:14`, `test_public_surface.py:37`,
`test_main_matriz_uses_single_client_instance.py:42`,
`test_public_surface_market_data.py:29`).
**Apply to:** all 5 new files.
This is also the reason `get_type_hints()` and not `__annotations__` is the correct parity
primitive (Pitfall 3).

### Gate output convention: `::error::` on stderr, exit 1
**Source:** `tools/check_uniform_structure.py:154-160`, `ci.yml:48`
**Apply to:** `tools/check_surface_types.py`
```python
            print(f"::error::Phase 31 TYP-03 uniform structure -- {exc}", file=sys.stderr)
```
GitHub renders `::error::` as an annotation on the PR. Success messages go to **stdout** via
`print(check())`; failures to **stderr**.

### Never import a package module from a gate
**Source:** `tools/check_uniform_structure.py:16-19`
```
It reads the **filesystem only** and never imports a package module, so no package
import-time side effect (a ``load_dotenv()`` call, a network client construction)
ever runs inside the gate.
```
**Apply to:** `tools/check_surface_types.py` only. `tools/surface_parity.py` is the deliberate
exception — runtime parity *requires* importing both `client.py` and `aio.py`, which is why it
is a helper imported by tests and **not** a `lint`-job gate. State this distinction in its
docstring so a future reader does not "fix" it into an AST gate.

### Anti-vacuity: an empty scan is itself a failure
**Source:** `check_uniform_structure.py:106-118` and `test_main_matriz_uses_single_client_instance.py:81-83`
**Apply to:** the surface gate (zero `__all__` resolved / zero defs scanned), all 6 parity
tests (per-package lower bounds), both RED fixtures (the injected-regression leg).
This is the phase's own threat model — see `15-REVIEW.md` WR-01/WR-02 for the canonical vacuous
guard postmortem.

### Unresolvable is a *problem*, never a *skip*
**Source:** `check_uniform_structure.py:83-85, 120-127`; `check_decode_intactness.py:635-641`
**Apply to:** the surface gate's import-root and `__all__` resolution; the wallets skip on the
class-parity axis (Pitfall 7 — assert the absence, don't `return`).

### `.egg-info` filtering when resolving import roots
**Source:** `check_uniform_structure.py:65-68, 90-94`
**Apply to:** `tools/check_surface_types.py`. Build artifacts exist under `packages/*/src/`
today; without the filter the gate finds 2 candidates and reports every package unresolvable.

### Subprocess: fixed argv, `shell=False`, no interpolated repo content
**Source:** `check_decode_intactness.py:365-386`
**Apply to:** `test_core_boundary_red.py`

### Ruff/mypy constraints on every new file
line-length 100 · double quotes · 4-space indent · no relative imports (`TID`) · no wildcard
imports · `PT` pytest-style on the 8 new test files · `disallow_untyped_defs` means every test
function needs `-> None`.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `packages/market-data-client/tests/test_core_boundary_red.py` | test | subprocess | No import-linter RED fixture exists anywhere in the repo (grep of `lint-imports`/`importlinter` over non-planning code yields only `pyproject.toml`, the two `tools/` scripts, 3 `_core.py` docstrings and `ci.yml`). Compose from the two partial analogs above: fixed-argv subprocess (`check_decode_intactness.py:362-386`) + `try/finally` restore (RESEARCH § Code Examples). |

---

## Planner Notes

Four decisions this map assumes (all are RESEARCH recommendations; confirm or override in the plan):

- **OQ-1** helper lives in `tools/`, not `verification/`.
- **OQ-2** the gate implements the `Any`-only rule; DT-06's `_request`/`httpx.Response` clause is
  subsumed by the `_`-prefix exemption and said so in the docstring.
- **OQ-3** import-linter RED test uses `try/finally` mutation of `_core.py` (0.07 s measured,
  C-1 corrects CONTEXT's cost premise — the argument for the manual route has evaporated).
- **D-09** option (1): fix `aio.configure`, precedented by matriz/iol's `ResourceWarning` shape.

**Pitfall 4 is the highest-risk pattern trap for the planner:** the metric for the parity bounds
must be fixed in one place (the helper docstring) and both columns derived from it. Splitting
extraction and bounds across separate tasks/waves reproduces the off-by-one in 5 of 6 packages.

---

## Metadata

**Analog search scope:** `tools/`, `verification/`, `packages/*/tests/`,
`packages/*/src/*/{client,aio}.py`, `.github/workflows/`, `pyproject.toml`
**Files read for extraction:** 13
**Pattern extraction date:** 2026-08-25
