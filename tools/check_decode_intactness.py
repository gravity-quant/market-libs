#!/usr/bin/env python3
"""Intactness gate for the five verbatim copies of the decode walker (Phase 29, DEC-01).

This repository has **no shared code between packages, by design**. The Phase 29
decode walker therefore ships as five byte-verbatim copies of one canonical body,
one per in-scope package. Five copies with no gate is five copies that diverge,
and the divergence gets discovered by a production bug rather than by CI. This
script is that gate.

Run it as::

    uv run python tools/check_decode_intactness.py

It exits non-zero and prints a ``::error::``-annotated line on any failure,
matching the convention of the ``lint-logging`` gate it sits beside in the
``lint`` job of ``.github/workflows/ci.yml``. It reads every file as **text** and
never imports a package module, so no package import-time side effect (a
``load_dotenv()`` call, a network client construction) ever runs inside the gate.

WHY A NAIVE BYTE COMPARISON DOES NOT WORK
=========================================

Three independent facts make ``diff a b`` fail on day one, and each one is a real
property of the current tree rather than a hypothetical:

1. Each copy names its own package: in its import of the decode error, in
   ``_LOGGER_NAME``, and in the two ``ContextVar`` name literals.
2. One copy (``matriz-client``) legitimately carries a different ``POLICY``
   constant. ``29-SEMANTICS-MATRIX.md`` Section 2 assigns it ``None``-substitution
   and an ``empty()`` classmethod where the other four take typed zeros.
3. **Substituting the package name changes the file's LINE COUNT**, in *opposite
   directions* at the two ends of the name-length spectrum, because CI enforces
   ``ruff format --check .`` at 100 columns. ``iol_client`` is short enough that
   the three-line ``DECODE_SCOPE`` declaration collapses to one; the much longer
   ``ambito_financiero_client`` is long enough that the one-line ``STRICT_DECODE``
   declaration expands to three. ``market_data_client`` and ``matriz_client`` sit
   between the two thresholds and show neither. A normalizer that substitutes the
   package name and then compares byte-for-byte reports a **false divergence on
   two of the five copies**, in opposite directions.

Fact 3 is why this script re-formats the normalized text before hashing it,
rather than comparing the substitution output directly.

THE NORMALIZATION (Check A)
===========================

These rules are the **only sanctioned place** to record a legitimate difference
between the five copies. A red gate means a copy drifted; the fix is to revert
the drift or to add a rule here with a stated reason -- never to weaken the check
into a vacuous one.

0. Assert the single distinct hash equals the pinned `CANONICAL_DIGEST` (WR-07).
   The rules below reduce five copies to one hash; that pins them to EACH OTHER,
   not to anything reviewed. An edit applied uniformly to all five collapses to
   one hash too. The pin is what makes the canonical content itself the protected
   artifact.
1. Drop the module docstring entirely. Each copy's docstring names its own
   package and states which module (if any) imports it; two of the five copies
   are dormant and say so.
2. Replace the whole ``POLICY`` assignment statement with a placeholder. This is
   the one *semantic* per-package delta, and it is pinned per package by
   ``test_policy_constant_matches_the_semantics_matrix``, not by this gate.
3. Replace the decode-error import statement, and every reference to the
   decode-error class name, with placeholders. The class **symbol appears at two
   sites** -- the ``from ... import`` line and the ``raise`` site -- so the name
   is normalized, not just the import line.
4. Replace the ``_LOGGER_NAME`` string literal (the value handed to the logger
   factory) with a placeholder.
5. Replace the two ``ContextVar`` name string literals with placeholders.
6. Replace every remaining occurrence of the package's own import name with a
   fixed placeholder token.
7. Strip trailing whitespace per line and normalize the trailing newline.
8. Re-format the result with ``ruff format`` at a fixed line length, so the
   layout of every copy is a function of the normalized text alone and fact 3
   above cannot produce a false divergence.

Comments are deliberately **kept** in the hashed body. Two comments inside the
copied region name ``higyrus`` and read as commentary about a different package
in the other four copies; they were kept verbatim in every copy on purpose, and
keeping them inside the hash is what makes that decision enforceable instead of
merely recorded. Normalizing via ``ast.unparse`` would have discarded them and
allowed a copy's comments to drift silently.

THE FILTER SCAN REGION (Check B)
================================

D-05's ``RedactingFilter`` fix must also stay identical across the five copies,
but ``matriz-client`` carries a package-specific ``auth_basic`` pre-scan block in
the same module (D-22). That block is **outside** the comparison *by
construction*: only the text strictly between the two marker comment lines is
hashed, and matriz's pre-scan sits above the ``begin`` marker. There is
deliberately **no** hardcoded second expected hash for matriz -- such a constant
would rot on the next legitimate edit to the region.

THE BAN LIST (Check C)
======================

Two constructs would let a copy quietly stop behaving like a copy. Both patterns
are matched **call-shaped or keyword-shaped**, never as bare names, because the
decode module's own docstring legitimately discusses strictness in prose and a
name-shaped pattern would fail the build on a docstring.

Each entry also carries the **filename it applies to** (WR-07). A copy quietly
stopping behaving like a copy can only happen inside the copied file, and
`strict=False` is a keyword that stdlib calls (`zip`, `json.loads`) legitimately
use elsewhere in these packages; scanning it repo-wide made an unrelated refactor
one line away from a red build with a misleading message.

THE ROSTER (Check D)
====================

The package roster below is the machine-visible record of the copy topology.
``wallets-client`` is exempt, and the exemption -- with its evidence and the
phase that resolves it -- is written up in
``.planning/phases/29-decoder-observable/29-WALLETS-EXEMPTION.md``.
"""

from __future__ import annotations

import ast
import difflib
import hashlib
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Kept in sync with `ruff format`'s effective configuration for this repo. It is
# pinned here rather than discovered so the normalization is a pure function of
# the normalized text: every copy is re-formatted identically regardless of what
# the repo config happens to be, which is the only property the hash needs.
_NORMALIZE_LINE_LENGTH = "100"
_NORMALIZE_TARGET_VERSION = "py312"

# The exemption document that explains the roster below; see Check D.
EXEMPTION_DOC = ".planning/phases/29-decoder-observable/29-WALLETS-EXEMPTION.md"


@dataclass(frozen=True, slots=True)
class Package:
    """One workspace package: its directory name and its Python import name."""

    directory: str
    module: str

    @property
    def src_root(self) -> Path:
        return REPO_ROOT / "packages" / self.directory / "src" / self.module

    @property
    def decode_path(self) -> Path:
        return self.src_root / "_decode.py"

    @property
    def logging_path(self) -> Path:
        return self.src_root / "_logging.py"


@dataclass(frozen=True, slots=True)
class ExemptPackage:
    """A workspace package deliberately outside the copy topology."""

    package: Package
    reason: str
    resolved_by: str


# The five packages that carry a copy of the walker. This tuple IS the copy
# topology; Check D fails if any of them loses `_decode.py`, if the exempt
# package acquires one, or if a package appears under `packages/` that is on
# neither list.
IN_SCOPE_PACKAGES: tuple[Package, ...] = (
    Package("higyrus-client", "higyrus_client"),
    Package("market-data-client", "market_data_client"),
    Package("matriz-client", "matriz_client"),
    Package("iol-client", "iol_client"),
    Package("ambito-financiero-client", "ambito_financiero_client"),
)

# The one package deliberately out of scope for Phase 29. See EXEMPTION_DOC for
# the evidence: wallets-client has no `_logging.py`, no `_state.py`, no `_core.py`
# and no `models.py`, so it has neither a place to hold the mode flag nor a bind
# site of the shape every other package has. Its request functions are
# module-level rather than methods.
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

CANONICAL = IN_SCOPE_PACKAGES[0]

# The sha256 of the REVIEWED canonical body, after the normalization below.
#
# Phase 29 code review, WR-07. Hashing the five copies and asserting they agree
# with EACH OTHER pins mutual agreement only: an edit applied uniformly to all
# five — exactly the shape a `sed`, a formatter rule or a well-meaning
# "harmonization" produces — collapses to one hash and passes green. The five
# copies are not the thing worth protecting; the canonical CONTENT is. This
# constant is that content, pinned.
#
# Bump it ONLY together with a reviewed change to `_decode.py`, and state the
# reason in the commit message. To read the new value, run this script: the
# failure message prints the digest it computed.
CANONICAL_DIGEST = "5749e19c9dae3b725e2eda9edea1420dc303a1a05469ab46efa58ee73b32a64a"

# --- Check A placeholders ---------------------------------------------------

_PKG_PLACEHOLDER = "__PKG__"
_DECODE_ERROR_PLACEHOLDER = "__DECODE_ERROR__"
_POLICY_PLACEHOLDER = 'POLICY = "__POLICY__"'
_LOGGER_NAME_PLACEHOLDER = "__LOGGER_NAME__"
_CONTEXTVAR_PLACEHOLDERS = {
    "STRICT_DECODE": "__STRICT_DECODE_VAR__",
    "DECODE_SCOPE": "__DECODE_SCOPE_VAR__",
}

# --- Check B markers --------------------------------------------------------

_SCAN_BEGIN = "# --- decode-intactness: generic-scan begin ---"
_SCAN_END = "# --- decode-intactness: generic-scan end ---"

# --- Check C ban list -------------------------------------------------------

# Both patterns are call-shaped or keyword-shaped ON PURPOSE. The decode module's
# own docstring discusses strict mode in prose ("strict mode raises on ...", "a
# strict driver run"), and `msgspec` is named in the milestone's design notes, so
# a bare-name pattern such as `strict` or `msgspec.field` would fail the build on
# a docstring rather than on a real opt-out. `\bstrict\s*=` cannot match
# `strict_decode: bool = False`: there is no word boundary between `strict` and
# the `_` that follows it.
#
# Phase 29 code review, WR-07: each entry carries the FILENAME it applies to, or
# `None` for the whole package source tree. `strict=False` used to be scanned
# repo-wide, where `\bstrict\s*=\s*False\b` matches `zip(a, b, strict=False)`,
# `json.loads(..., strict=False)` and every other stdlib keyword of that name --
# none of which has anything to do with the decode mode. The neighbouring
# `_logging.py` already uses `zip(..., strict=True)`, so the `False` variant was
# one refactor away from a red build with a badly misleading message. A copy
# "quietly stopping behaving like a copy" can only happen inside the copied file,
# which is exactly the scope this entry now has.
BAN_LIST: tuple[tuple[str, str, str, str | None], ...] = (
    (
        "strict=False",
        r"\bstrict\s*=\s*False\b",
        "a copy disabling strictness at a call site instead of through the mode carrier",
        "_decode.py",
    ),
    (
        "msgspec.field(",
        r"\bmsgspec\s*\.\s*field\s*\(",
        "a copy delegating field handling to a third-party helper instead of the walker",
        None,
    ),
)


class CheckFailure(Exception):
    """Raised by a check with a fully formed, operator-readable message."""


def _fail(message: str) -> CheckFailure:
    return CheckFailure(message)


def _read(path: Path) -> str:
    if not path.is_file():
        raise _fail(f"expected file is missing: {path.relative_to(REPO_ROOT)}")
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Check A -- decode-helper intactness
# ---------------------------------------------------------------------------


def _module_docstring_span(tree: ast.Module) -> tuple[int, int] | None:
    """1-based inclusive line span of the module docstring, if there is one."""
    if not tree.body:
        return None
    first = tree.body[0]
    if (
        isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Constant)
        and isinstance(first.value.value, str)
    ):
        return first.lineno, first.end_lineno or first.lineno
    return None


def _assignment_span(tree: ast.Module, name: str) -> tuple[int, int]:
    """1-based inclusive line span of the module-level assignment to ``name``."""
    for node in tree.body:
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            targets = list(node.targets)
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        for target in targets:
            if isinstance(target, ast.Name) and target.id == name:
                return node.lineno, node.end_lineno or node.lineno
    raise _fail(f"no module-level assignment to `{name}` found")


def _assignment_node(tree: ast.Module, name: str) -> ast.Assign | ast.AnnAssign:
    for node in tree.body:
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            targets = list(node.targets)
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        for target in targets:
            if isinstance(target, ast.Name) and target.id == name:
                return node
    raise _fail(f"no module-level assignment to `{name}` found")


def _string_value(node: ast.Assign | ast.AnnAssign) -> str:
    value = node.value
    if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
        raise _fail("expected a plain string assignment")
    return value.value


def _contextvar_name_literal(tree: ast.Module, var: str) -> str:
    """The name string handed to ``ContextVar(...)`` for ``var``."""
    node = _assignment_node(tree, var)
    call = node.value
    if not isinstance(call, ast.Call) or not call.args:
        raise _fail(f"`{var}` is not assigned from a ContextVar(...) call")
    first = call.args[0]
    if not isinstance(first, ast.Constant) or not isinstance(first.value, str):
        raise _fail(f"`{var}`'s ContextVar name is not a string literal")
    return first.value


def _decode_error_symbol(tree: ast.Module, module: str) -> tuple[str, tuple[int, int]]:
    """The decode-error class name and the 1-based span of the import that brings it in."""
    wanted = f"{module}.exceptions"
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == wanted:
            for alias in node.names:
                if alias.name.endswith("DecodeError"):
                    return alias.name, (node.lineno, node.end_lineno or node.lineno)
    raise _fail(f"no `from {wanted} import *DecodeError` statement found")


def _ruff_format(source: str, label: str) -> str:
    """Canonicalize layout so the package-name substitution cannot reflow the body."""
    try:
        # Fixed argv, no shell, no interpolated user input: the only variable
        # part is stdin, which is repository source this gate already reads.
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "ruff",
                "format",
                "--line-length",
                _NORMALIZE_LINE_LENGTH,
                "--target-version",
                _NORMALIZE_TARGET_VERSION,
                "--stdin-filename",
                "normalized_decode.py",
                "-",
            ],
            input=source,
            capture_output=True,
            text=True,
            check=False,
            cwd=REPO_ROOT,
        )
    except OSError as exc:  # pragma: no cover -- environment failure, not drift
        raise _fail(f"could not run `ruff format` to normalize {label}: {exc}") from exc
    if completed.returncode != 0:
        raise _fail(
            f"`ruff format` failed while normalizing {label} "
            f"(exit {completed.returncode}): {completed.stderr.strip()}"
        )
    return completed.stdout


def normalize_decode_source(source: str, pkg: Package) -> str:
    """Apply the eight normalization rules from the module docstring, in order."""
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise _fail(f"{pkg.decode_path.relative_to(REPO_ROOT)} does not parse: {exc}") from exc

    lines = source.splitlines()

    # Line-range surgery is computed against the ORIGINAL line numbering and
    # applied in one pass, so earlier edits cannot shift later spans.
    replacements: dict[int, str | None] = {}

    def blank_span(span: tuple[int, int], replacement: str | None) -> None:
        start, end = span
        replacements[start - 1] = replacement
        for index in range(start, end):
            replacements[index] = None

    # Rule 1 -- drop the module docstring.
    docstring_span = _module_docstring_span(tree)
    if docstring_span is None:
        raise _fail(f"{pkg.decode_path.relative_to(REPO_ROOT)} has no module docstring")
    blank_span(docstring_span, None)

    # Rule 2 -- replace the whole POLICY assignment statement.
    blank_span(_assignment_span(tree, "POLICY"), _POLICY_PLACEHOLDER)

    # Rule 3a -- replace the decode-error import statement.
    decode_error, import_span = _decode_error_symbol(tree, pkg.module)
    blank_span(
        import_span,
        f"from {_PKG_PLACEHOLDER}.exceptions import {_DECODE_ERROR_PLACEHOLDER}",
    )

    kept: list[str] = []
    for index, line in enumerate(lines):
        if index in replacements:
            replacement = replacements[index]
            if replacement is not None:
                kept.append(replacement)
            continue
        kept.append(line)
    text = "\n".join(kept)

    # Rule 3b -- replace every remaining reference to the decode-error class name
    # (the `raise` site, and any future one).
    text = re.sub(rf"\b{re.escape(decode_error)}\b", _DECODE_ERROR_PLACEHOLDER, text)

    # Rule 4 -- replace the _LOGGER_NAME string literal.
    logger_name = _string_value(_assignment_node(tree, "_LOGGER_NAME"))
    text = text.replace(f'"{logger_name}"', f'"{_LOGGER_NAME_PLACEHOLDER}"')

    # Rule 5 -- replace the two ContextVar name literals.
    for var, placeholder in _CONTEXTVAR_PLACEHOLDERS.items():
        literal = _contextvar_name_literal(tree, var)
        text = text.replace(f'"{literal}"', f'"{placeholder}"')

    # Rule 6 -- replace every remaining occurrence of the package's import name.
    text = re.sub(rf"\b{re.escape(pkg.module)}\b", _PKG_PLACEHOLDER, text)

    # Rule 7 -- strip trailing whitespace per line; normalize the trailing newline.
    text = "\n".join(line.rstrip() for line in text.split("\n")).rstrip("\n") + "\n"

    # Rule 8 -- canonicalize layout. Without this, `iol_client` (short) and
    # `ambito_financiero_client` (long) reflow the ContextVar declarations in
    # opposite directions and produce two false divergences.
    return _ruff_format(text, str(pkg.decode_path.relative_to(REPO_ROOT)))


def check_a_decode_intactness() -> str:
    normalized: dict[str, str] = {}
    digests: dict[str, str] = {}
    for pkg in IN_SCOPE_PACKAGES:
        body = normalize_decode_source(_read(pkg.decode_path), pkg)
        normalized[pkg.directory] = body
        digests[pkg.directory] = hashlib.sha256(body.encode("utf-8")).hexdigest()

    distinct = sorted(set(digests.values()))
    if len(distinct) != 1:
        canonical_digest = digests[CANONICAL.directory]
        disagreeing = [d for d, h in digests.items() if h != canonical_digest]
        first = disagreeing[0]
        diff = "\n".join(
            difflib.unified_diff(
                normalized[CANONICAL.directory].splitlines(),
                normalized[first].splitlines(),
                fromfile=f"{CANONICAL.directory} (normalized)",
                tofile=f"{first} (normalized)",
                lineterm="",
            )
        )
        roster = "\n".join(f"    {d}: {h[:16]}" for d, h in digests.items())
        raise _fail(
            "decode-helper copies have drifted -- "
            f"{len(distinct)} distinct normalized hashes across {len(digests)} copies.\n"
            f"  Copies disagreeing with `{CANONICAL.directory}`: {', '.join(disagreeing)}\n"
            f"  Normalized hashes:\n{roster}\n"
            f"  Unified diff ({CANONICAL.directory} -> {first}):\n{diff}\n"
            "  A legitimate per-package difference belongs in this script's "
            "normalization rules, with a stated reason -- never in a weakened check."
        )
    # WR-07: mutual agreement is necessary but not sufficient. The copies must
    # also agree with the body that was actually reviewed.
    if distinct[0] != CANONICAL_DIGEST:
        raise _fail(
            "the canonical decode body CHANGED -- all five copies agree with each "
            "other but not with the reviewed body.\n"
            f"  expected (CANONICAL_DIGEST): {CANONICAL_DIGEST}\n"
            f"  computed:                    {distinct[0]}\n"
            "  A uniform edit across all five copies passes the mutual check by "
            "construction; this pin is what makes it visible.\n"
            "  If the change is intended and reviewed, bump CANONICAL_DIGEST in "
            "this script to the computed value and say why in the commit message."
        )
    return (
        f"Check A  decode-helper intactness: {len(digests)} copies of `_decode.py` "
        f"reduce to one normalized hash {distinct[0][:16]}, matching CANONICAL_DIGEST"
    )


# ---------------------------------------------------------------------------
# Check B -- filter scan-region intactness
# ---------------------------------------------------------------------------


def extract_scan_region(source: str, label: str) -> str:
    """Text strictly between the two marker comment lines, exclusive of both."""
    lines = source.splitlines()
    begins = [i for i, line in enumerate(lines) if line.strip() == _SCAN_BEGIN]
    ends = [i for i, line in enumerate(lines) if line.strip() == _SCAN_END]
    if len(begins) != 1 or len(ends) != 1:
        raise _fail(
            f"{label}: expected exactly one `{_SCAN_BEGIN}` and one `{_SCAN_END}` "
            f"marker line, found {len(begins)} begin and {len(ends)} end. "
            "The marker pair is what keeps a package-specific pre-scan block "
            "outside the comparison; it must not be removed or duplicated."
        )
    if ends[0] <= begins[0]:
        raise _fail(f"{label}: the `end` marker precedes the `begin` marker")
    return "\n".join(lines[begins[0] + 1 : ends[0]])


def normalize_scan_region(region: str, pkg: Package) -> str:
    """Normalization rules 6 and 7 only -- no reformatting, no other substitution."""
    text = re.sub(rf"\b{re.escape(pkg.module)}\b", _PKG_PLACEHOLDER, region)
    return "\n".join(line.rstrip() for line in text.split("\n")).rstrip("\n") + "\n"


def check_b_filter_region_intactness() -> str:
    normalized: dict[str, str] = {}
    digests: dict[str, str] = {}
    for pkg in IN_SCOPE_PACKAGES:
        label = str(pkg.logging_path.relative_to(REPO_ROOT))
        region = extract_scan_region(_read(pkg.logging_path), label)
        body = normalize_scan_region(region, pkg)
        normalized[pkg.directory] = body
        digests[pkg.directory] = hashlib.sha256(body.encode("utf-8")).hexdigest()

    distinct = sorted(set(digests.values()))
    if len(distinct) != 1:
        canonical_digest = digests[CANONICAL.directory]
        disagreeing = [d for d, h in digests.items() if h != canonical_digest]
        first = disagreeing[0]
        diff = "\n".join(
            difflib.unified_diff(
                normalized[CANONICAL.directory].splitlines(),
                normalized[first].splitlines(),
                fromfile=f"{CANONICAL.directory} (scan region)",
                tofile=f"{first} (scan region)",
                lineterm="",
            )
        )
        raise _fail(
            "filter scan regions have drifted -- "
            f"{len(distinct)} distinct hashes across {len(digests)} copies.\n"
            f"  Copies disagreeing with `{CANONICAL.directory}`: {', '.join(disagreeing)}\n"
            f"  Unified diff ({CANONICAL.directory} -> {first}):\n{diff}"
        )
    line_count = normalized[CANONICAL.directory].count("\n")
    return (
        f"Check B  filter scan-region intactness: {len(digests)} marker-delimited regions "
        f"({line_count} lines each) reduce to one hash {distinct[0][:16]}"
    )


# ---------------------------------------------------------------------------
# Check C -- ban list
# ---------------------------------------------------------------------------


def check_c_ban_list() -> str:
    hits: list[str] = []
    scanned = 0
    for pkg in (*IN_SCOPE_PACKAGES, *(e.package for e in EXEMPT_PACKAGES)):
        root = REPO_ROOT / "packages" / pkg.directory / "src"
        if not root.is_dir():
            raise _fail(f"package source tree is missing: {root.relative_to(REPO_ROOT)}")
        for path in sorted(root.rglob("*.py")):
            scanned += 1
            source = path.read_text(encoding="utf-8")
            for label, pattern, why, filename in BAN_LIST:
                if filename is not None and path.name != filename:
                    continue
                for number, line in enumerate(source.splitlines(), start=1):
                    if re.search(pattern, line):
                        hits.append(
                            f"    {path.relative_to(REPO_ROOT)}:{number}: "
                            f"`{label}` -- {why}\n      {line.strip()}"
                        )
    if hits:
        raise _fail(
            "banned construct found in package source:\n"
            + "\n".join(hits)
            + "\n  These constructs would let a copy quietly stop behaving like a copy."
        )
    labels = ", ".join(
        f"`{label}`" + (f" (in `{filename}`)" if filename else "")
        for label, _, _, filename in BAN_LIST
    )
    return f"Check C  ban list: {labels} absent from {scanned} package source files"


# ---------------------------------------------------------------------------
# Check D -- package roster
# ---------------------------------------------------------------------------


def check_d_roster() -> str:
    problems: list[str] = []

    for pkg in IN_SCOPE_PACKAGES:
        if not pkg.decode_path.is_file():
            problems.append(
                f"    in-scope package `{pkg.directory}` has no "
                f"{pkg.decode_path.relative_to(REPO_ROOT)}"
            )

    for exempt in EXEMPT_PACKAGES:
        if exempt.package.decode_path.is_file():
            problems.append(
                f"    exempt package `{exempt.package.directory}` has acquired a "
                f"`_decode.py` -- move it into IN_SCOPE_PACKAGES and update "
                f"{EXEMPTION_DOC}"
            )

    known = {p.directory for p in IN_SCOPE_PACKAGES} | {
        e.package.directory for e in EXEMPT_PACKAGES
    }
    on_disk = {p.name for p in sorted((REPO_ROOT / "packages").iterdir()) if p.is_dir()}
    for unknown in sorted(on_disk - known):
        problems.append(
            f"    package `{unknown}` is on neither the in-scope roster nor the "
            f"exemption list -- add it to one, and to {EXEMPTION_DOC} if exempt"
        )
    for missing in sorted(known - on_disk):
        problems.append(f"    roster names `{missing}`, which is not under `packages/`")

    if problems:
        raise _fail("package roster is out of date:\n" + "\n".join(problems))

    exemptions = ", ".join(f"`{e.package.directory}`" for e in EXEMPT_PACKAGES)
    return (
        f"Check D  package roster: {len(IN_SCOPE_PACKAGES)} in-scope packages carry a "
        f"`_decode.py`; {exemptions} exempt (see {EXEMPTION_DOC})"
    )


# ---------------------------------------------------------------------------


def main() -> int:
    checks = (
        check_a_decode_intactness,
        check_b_filter_region_intactness,
        check_c_ban_list,
        check_d_roster,
    )
    failures = 0
    for check in checks:
        try:
            print(check())
        except CheckFailure as exc:
            failures += 1
            print(f"::error::Phase 29 DEC-01 decode intactness -- {exc}", file=sys.stderr)
    if failures:
        print(
            f"::error::decode-intactness gate FAILED ({failures} of {len(checks)} checks)",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
