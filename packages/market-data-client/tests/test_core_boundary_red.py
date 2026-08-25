"""RED proof for D-02: the `_core` import boundary must actually catch a violation.

This file is the executable form of Phase 32 D-02. Five ``forbidden`` contracts
have been declared in ``pyproject.toml`` since Phase 7 (the fifth, for
``market_data_client``, since Phase 31 WR-05) and every CI run has reported them
KEPT -- but **no fixture anywhere in this repository had ever demonstrated that
any of them would fail if violated**. A contract that has only ever been observed
passing is an assertion about the linter, not about the code. These two tests
supply the missing lower bound for the market-data one.

WHY AUTOMATED, AND NOT A MANUAL DEMONSTRATION
    The Phase 30 D-10 precedent (``packages/iol-client/tests/test_typed_surface_red.py``)
    verifies non-vacuity **by hand** and records the observation in a SUMMARY, and
    ``32-CONTEXT.md`` D-02 leaned that way for this contract too -- on the explicit
    premise that a ``lint-imports`` subprocess costs "decenas de segundos". That
    premise was measured and found **wrong**: import-linter 2.11 on grimp 3.14 has a
    Rust core and analyses all 69 files in roughly six hundredths of a second, with
    no ``.grimp_cache`` in the tree. The cost objection that would have justified the
    cheaper route does not exist, so the proof is automated and re-runs on every
    push instead of ageing inside a document.

WHY IN-PACKAGE AND NOT UNDER ``verification/``
    The ``test`` job invokes pytest with an explicit ``packages/${{ matrix.package }}``
    path, which overrides ``testpaths``. ``verification/`` has therefore never
    executed in CI, and a proof placed there would prove nothing after the day it
    was written. Under ``packages/market-data-client/tests/`` it runs in both legs
    of the 6x2 matrix.

HOW THE LINTER IS INVOKED, AND WHAT IS BANNED
    A single fixed-element argv, resolved with ``shutil.which``, ``shell=False``,
    nothing interpolated from repository content -- the same discipline as
    ``tools/check_decode_intactness.py``'s ``ruff format`` subprocess. Two forms are
    deliberately rejected: ``python -m importlinter.cli`` (that module has **no**
    ``__main__`` guard, so it exits 0 having executed nothing -- both legs below
    would pass vacuously, in the worst possible way), and ``uv run lint-imports``
    (a resolver round-trip inside a test, less hermetic for no gain).

WHY THE ASSERTIONS NAME THE CONTRACT
    Asserting only ``returncode != 0`` would be satisfied by a typo in the argv, a
    missing executable, an unreadable config, or an unrelated broken contract. Both
    legs therefore assert on the contract's declared name **plus** its state marker,
    assert that every *other* declared contract is still reported KEPT, and assert
    the summary count line accounts for all five. The marker wordings encoded here
    (``KEPT`` / ``BROKEN`` suffixes, ``Contracts: N kept, M broken.``) were read off
    real runs during execution, not recalled.

THE MUTATION, AND THE OQ-3 DECISION
    The RED leg appends one import to a **tracked** source file and restores it in
    ``finally``, then asserts byte-equality with the text it read at the start and a
    green re-run of the linter -- which is what turns "we restored it" from a hope
    into a check. OQ-3 weighed this against copying the tree to ``tmp_path`` with a
    generated config (~30 lines of machinery); mutate-and-restore won on cost, and
    the residual risk is recorded rather than hidden: a ``SIGKILL`` between the write
    and the ``finally`` leaves the tree dirty. That failure is loud and is undone by
    a single ``git checkout`` of one file.

ORDER SENSITIVITY (one narrow caveat)
    This test mutates a file other tests in the session may already have imported.
    That is safe today because grimp analyses source **statically** and never
    imports the mutated module, and because pytest runs this suite sequentially. If
    parallel test execution (``pytest-xdist``) is ever introduced, this test needs
    isolation -- flagged here rather than left for someone to discover.
"""

from __future__ import annotations

import shutil
import subprocess
import tomllib
from pathlib import Path

# The contract under proof, verbatim from `pyproject.toml`'s
# `[[tool.importlinter.contracts]]` block.
_CONTRACT = "market_data_client._core does not depend on transport modules"

# The violation: `_core` importing the transport shell it is forbidden to know
# about. The appended line carries an F401 suppression suffix so that a stray
# lint pass over the mutated tree would object to nothing.
_VIOLATION = "\nfrom market_data_client import client  # noqa: F401\n"


def _find_repo_root() -> Path:
    """Return the workspace root: the ancestor whose pyproject declares the contracts.

    Anchoring on ``[tool.importlinter]`` rather than on the mere presence of a
    ``pyproject.toml`` matters -- this file's own package has one two levels up,
    and that is not the config ``lint-imports`` reads. Derived from ``__file__``
    rather than from the process CWD so the test is invariant to where pytest ran.
    """
    for candidate in Path(__file__).resolve().parents:
        config = candidate / "pyproject.toml"
        if config.is_file() and "[tool.importlinter]" in config.read_text(encoding="utf-8"):
            return candidate
    raise AssertionError("could not locate the workspace root from this test file")


_REPO_ROOT = _find_repo_root()
_CORE_PATH = _REPO_ROOT / "packages/market-data-client/src/market_data_client/_core.py"


def _declared_contract_names() -> tuple[str, ...]:
    """Every contract name declared in the workspace config, read from disk.

    Read rather than hardcoded so that a sixth contract cannot silently fall
    outside the "all the others stayed KEPT" assertion below.
    """
    data = tomllib.loads((_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    names = tuple(str(contract["name"]) for contract in data["tool"]["importlinter"]["contracts"])
    assert _CONTRACT in names, f"the contract under proof is not declared; found {names}"
    return names


def _other_contract_names() -> tuple[str, ...]:
    """The declared contracts except the one under proof."""
    return tuple(name for name in _declared_contract_names() if name != _CONTRACT)


def _run_lint_imports() -> subprocess.CompletedProcess[str]:
    """Run the linter from the workspace root with a fixed, shell-free argv."""
    executable = shutil.which("lint-imports")
    # A missing executable is a broken environment, never a reason to report
    # green -- so this is an assertion, and deliberately never a skip.
    assert executable is not None, (
        "`lint-imports` is not on PATH; import-linter is a locked dev dependency "
        "(pyproject.toml `[dependency-groups] dev`) and the environment is broken"
    )
    # Fixed argv, no shell, no interpolated repository content: the only input is
    # the resolved absolute path of a locked dev dependency's console script.
    return subprocess.run(
        [executable],
        capture_output=True,
        text=True,
        check=False,
        cwd=_REPO_ROOT,
    )


def test_core_boundary_contract_is_kept_on_the_clean_tree() -> None:
    """Upper bound: on today's tree the linter reports the contract KEPT.

    Observed output line::

        market_data_client._core does not depend on transport modules KEPT

    Without this leg the RED leg could be passing for the wrong reason -- a
    permanently broken contract, or a config the linter cannot read at all, would
    make "it went red under mutation" meaningless.
    """
    others = _other_contract_names()

    result = _run_lint_imports()

    assert result.returncode == 0, f"clean tree is not green:\n{result.stdout}\n{result.stderr}"
    assert f"{_CONTRACT} KEPT" in result.stdout, result.stdout
    for name in others:
        assert f"{name} KEPT" in result.stdout, result.stdout
    assert f"Contracts: {len(others) + 1} kept, 0 broken." in result.stdout, result.stdout


def test_core_boundary_contract_is_red_when_violated() -> None:
    """Lower bound: with the boundary violated, the linter names it BROKEN.

    Observed output line, and the reason this test exists::

        market_data_client._core does not depend on transport modules BROKEN

    The other declared contracts must still be reported KEPT: that is what makes
    the failure attributable to this contract and to the surgical mutation, rather
    than to a run that collapsed for an unrelated reason.
    """
    others = _other_contract_names()
    original = _CORE_PATH.read_text(encoding="utf-8")

    try:
        _CORE_PATH.write_text(original + _VIOLATION, encoding="utf-8")
        result = _run_lint_imports()
    finally:
        _CORE_PATH.write_text(original, encoding="utf-8")

    assert result.returncode != 0, f"the violation did not fail the linter:\n{result.stdout}"
    assert f"{_CONTRACT} BROKEN" in result.stdout, result.stdout
    for name in others:
        assert f"{name} KEPT" in result.stdout, result.stdout
    assert f"Contracts: {len(others)} kept, 1 broken." in result.stdout, result.stdout

    # The restore is not taken on trust: byte-equality, then a green re-run.
    assert _CORE_PATH.read_text(encoding="utf-8") == original, (
        f"{_CORE_PATH} was not restored to its original content"
    )
    restored = _run_lint_imports()
    assert restored.returncode == 0, f"tree still red after restore:\n{restored.stdout}"
    assert f"{_CONTRACT} KEPT" in restored.stdout, restored.stdout
