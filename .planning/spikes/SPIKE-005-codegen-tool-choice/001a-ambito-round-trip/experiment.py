"""Spike 001a: ámbito round-trip experiment — unasync 0.6.0 + ruff format + diff + B8 identity.

Generates ``client_generated.py`` from ``aio.py`` via ``unasync.unasync_files()`` with the
prescribed ``additional_replacements`` table, post-processes with ``uv run ruff format``,
diffs against the v1.1 hand-written ``client.py``, then asserts the B8 identity invariant
(``mod._raise_for_response is aio._raise_for_response is _core.raise_for_response``).

Exits 0 on PASS (empty diff AND B8 assert passes); exits 1 on FAIL with a clear summary.

CONVENTIONS.md §"To Avoid": this script NEVER imports from ``packages/*/src/``. It uses
``shutil.copy`` + ``subprocess`` + ``importlib.util.spec_from_file_location`` to keep
the spike isolated from production code (Anti-Pitfall 2 enforcement).
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import unasync

# Path layout: experiment.py lives at depth 4 under repo root.
#   <repo>/.planning/spikes/SPIKE-005-codegen-tool-choice/001a-ambito-round-trip/experiment.py
#   parents[0] = 001a-ambito-round-trip
#   parents[1] = SPIKE-005-codegen-tool-choice
#   parents[2] = spikes
#   parents[3] = .planning
#   parents[4] = <repo>
REPO_ROOT = Path(__file__).resolve().parents[4]
SRC = REPO_ROOT / "packages/ambito-financiero-client/src/ambito_financiero_client"
SPIKE = Path(__file__).resolve().parent
WORK = SPIKE / "output"

assert WORK.exists(), f"WORK dir missing: {WORK} (Task 12-01-02 should have created it)"
assert (SRC / "aio.py").exists(), f"ámbito aio.py missing: {SRC / 'aio.py'}"
assert (SRC / "client.py").exists(), f"ámbito client.py missing: {SRC / 'client.py'}"

# ---------------------------------------------------------------------------
# Step 1 — copy aio.py into spike work area (anti-Pitfall 2: never write to packages/).
# ---------------------------------------------------------------------------
work_aio = WORK / "aio.py"
shutil.copy(SRC / "aio.py", work_aio)
print(f"[step 1] copied {SRC / 'aio.py'} -> {work_aio}")

# ---------------------------------------------------------------------------
# Step 2 — run unasync.unasync_files() with the prescribed additional_replacements.
# ---------------------------------------------------------------------------
# Token list derived from a side-by-side read of aio.py vs client.py (see 12-RESEARCH.md
# §"Recipe 1 — unasync 0.6.0 Invocation Recipe"). All entries are SINGLE TOKENS as
# tokenized by Python's tokenize module — unasync issue #74 single-token limitation.
ADDITIONAL_REPLACEMENTS: dict[str, str] = {
    # Core async→sync class + transport renames.
    "AsyncClient": "Client",
    "AsyncRetryTransport": "RetryTransport",
    "_atransport": "_transport",
    "AmbitoFinancieroAsyncClient": "AmbitoFinancieroClient",
    "_default_async_client": "_default_client",
    "aclose": "close",
}
print(f"[step 2] running unasync.unasync_files (replacements: {len(ADDITIONAL_REPLACEMENTS)} keys)")
unasync.unasync_files(
    fpath_list=[str(work_aio)],
    rules=[
        unasync.Rule(
            fromdir=str(WORK) + "/",
            todir=str(WORK) + "/",
            additional_replacements=ADDITIONAL_REPLACEMENTS,
        )
    ],
)

# ---------------------------------------------------------------------------
# Step 3 — rename output to client_generated.py.
# ---------------------------------------------------------------------------
generated = WORK / "client_generated.py"
# unasync writes to the same filename (aio.py), so rename to client_generated.py.
if generated.exists():
    generated.unlink()
work_aio.rename(generated)
print(f"[step 3] renamed -> {generated}")

# ---------------------------------------------------------------------------
# Step 4 — run uv run ruff format on the generated file.
# ---------------------------------------------------------------------------
print("[step 4] running uv run ruff format ...")
fmt_proc = subprocess.run(
    ["uv", "run", "ruff", "format", str(generated)],
    check=True,
    capture_output=True,
    text=True,
    cwd=REPO_ROOT,
)
print(fmt_proc.stdout.strip() or "(ruff format: no output)")
if fmt_proc.stderr.strip():
    print(f"(stderr) {fmt_proc.stderr.strip()}")

# ---------------------------------------------------------------------------
# Step 4b — format-stability check (Pitfall 3 / D-RIGOR-01 item 3).
# Running ruff format --check on the just-formatted file MUST exit 0
# (idempotent formatting — running format twice is a no-op).
# ---------------------------------------------------------------------------
print("[step 4b] running uv run ruff format --check (idempotency) ...")
fmt_check = subprocess.run(
    ["uv", "run", "ruff", "format", "--check", str(generated)],
    capture_output=True,
    text=True,
    cwd=REPO_ROOT,
)
format_stable = fmt_check.returncode == 0
print(f"[step 4b] format-stable: {format_stable} (exit {fmt_check.returncode})")
if fmt_check.stdout.strip():
    print(fmt_check.stdout.strip())
if fmt_check.stderr.strip():
    print(f"(stderr) {fmt_check.stderr.strip()}")

# ---------------------------------------------------------------------------
# Step 5 — diff against v1.1 hand-written client.py.
# ---------------------------------------------------------------------------
print("[step 5] diff -u <v1.1 client.py> <client_generated.py> ...")
diff_proc = subprocess.run(
    ["diff", "-u", str(SRC / "client.py"), str(generated)],
    capture_output=True,
    text=True,
    cwd=REPO_ROOT,
)
diff_output_file = SPIKE / "diff_vs_v1.1_client.txt"
diff_output_file.write_text(diff_proc.stdout + diff_proc.stderr)
diff_exit = diff_proc.returncode
diff_empty = diff_exit == 0
# Approximate hunk count: number of "@@ ... @@" markers in unified diff.
hunk_count = sum(1 for line in diff_proc.stdout.splitlines() if line.startswith("@@"))
print(f"[step 5] diff exit code: {diff_exit} ({'empty' if diff_empty else f'{hunk_count} hunks'})")
print(f"[step 5] diff transcript written to: {diff_output_file}")

# ---------------------------------------------------------------------------
# Step 6 — B8 identity check via importlib.util.spec_from_file_location.
# ---------------------------------------------------------------------------
# Load the generated file as a module WITHOUT going through `import
# ambito_financiero_client.client` (that would import the v1.1 hand-written file).
#
# `uv run --with unasync` creates an ephemeral venv that does NOT include the
# workspace packages. We add the workspace src path to sys.path so the spike can
# import `ambito_financiero_client._core` + `ambito_financiero_client.aio` without
# requiring callers to invoke `uv run --package ambito-financiero-client --with unasync`.
ambito_src = REPO_ROOT / "packages/ambito-financiero-client/src"
if str(ambito_src) not in sys.path:
    sys.path.insert(0, str(ambito_src))

print("[step 6] B8 identity check (loading generated as standalone module) ...")
b8_pass = False
b8_error: str | None = None
try:
    spec = importlib.util.spec_from_file_location(
        "ambito_financiero_client.client_generated",
        str(generated),
    )
    assert spec is not None and spec.loader is not None, "spec_from_file_location returned None"
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ambito_financiero_client.client_generated"] = mod
    spec.loader.exec_module(mod)

    # Now import the real ámbito modules from the workspace (sys.path-resolved above).
    import ambito_financiero_client._core as core  # noqa: E402
    import ambito_financiero_client.aio as aio  # noqa: E402

    if (
        mod._raise_for_response  # type: ignore[attr-defined]
        is aio._raise_for_response
        is core.raise_for_response
    ):
        b8_pass = True
        print("[step 6] B8 IDENTITY: PASS")
        print(
            f"[step 6]   mod._raise_for_response  id={id(mod._raise_for_response):x}"  # type: ignore[attr-defined]
        )
        print(f"[step 6]   aio._raise_for_response  id={id(aio._raise_for_response):x}")
        print(f"[step 6]   _core.raise_for_response id={id(core.raise_for_response):x}")
    else:
        b8_pass = False
        b8_error = (
            "B8 IDENTITY FAILED — codegen emitted a thunk wrapper "
            "(mod._raise_for_response is not aio._raise_for_response or not core.raise_for_response)"
        )
        print(f"[step 6] {b8_error}")
except Exception as exc:  # noqa: BLE001 — spike script; surface any failure with full text.
    b8_pass = False
    b8_error = f"B8 IDENTITY ERROR — exception during identity check: {exc!r}"
    print(f"[step 6] {b8_error}")

# ---------------------------------------------------------------------------
# Step 6b — cleanup the __pycache__ that importlib creates on exec_module.
# Spike artifacts must be deterministic; bytecode caches are ephemeral.
# ---------------------------------------------------------------------------
import shutil as _shutil  # noqa: E402,PLC0415 — explicit late-import for cleanup-only

_pycache = WORK / "__pycache__"
if _pycache.exists():
    _shutil.rmtree(_pycache, ignore_errors=True)
    print(f"[step 6b] removed {_pycache}")

# ---------------------------------------------------------------------------
# Step 7 — verdict + exit code.
# ---------------------------------------------------------------------------
verdict_pass = diff_empty and b8_pass and format_stable
diff_label = "empty" if diff_empty else f"{hunk_count} hunks"
b8_label = "PASS" if b8_pass else "FAIL"
fmt_label = "PASS" if format_stable else "FAIL"
summary = (
    f"SPIKE 001a VERDICT: {'PASS' if verdict_pass else 'FAIL'} "
    f"diff={diff_label} b8={b8_label} format-stable={fmt_label}"
)
print(summary)

sys.exit(0 if verdict_pass else 1)
