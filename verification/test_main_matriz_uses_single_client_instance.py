"""REFAC-05 -- ``main_matriz.py`` MUST construct at most one sync ``Client`` and
one async ``AsyncClient`` (the single-Client invariant, D-01/D-02).

Pre-migration every probe reached the module singleton independently via
``matriz_client.client._base_url`` / ``aio._get_default()._state`` (the sync
hostname-safety read plus the six async ``_state`` reads and the lambda-wrapped
``_ainvoke`` helper). The driver migration (Phase 15, Wave 4) replaces those with
exactly one ``Client()`` built in ``main()`` and one ``AsyncClient()`` built in
``_async_main()``, both threaded as parameters into every ``probe_*``. This AST
gate is the merge-blocking invariant: it counts constructor ``Call`` sites for the
two client classes across the whole driver and asserts ``1 <= count <= 2`` -- the
lower bound makes the gate non-vacuous (a driver that constructs ZERO classes,
i.e. the un-migrated state, FAILS RED rather than passing trivially).

The ``<= 2`` upper bound is the TokenStore-corruption mitigation (anti-Pitfall 1):
matriz's TokenStore is a 3-way concurrency primitive, so constructing more than one
``AsyncClient`` risks OAuth churn / token corruption. Capping construction at one
sync + one async client directly prevents that.

The walker matches BOTH constructor spellings per D-05: bare ``Client()`` /
``AsyncClient()`` (``ast.Name``) and module-qualified ``mod.Client()`` /
``mod.AsyncClient()`` (``ast.Attribute``). An accessor or builder method call
(e.g. ``with_options`` -- referenced here by concept only) is not a constructor:
its callee is an ``ast.Attribute`` whose ``attr`` is the accessor name, not a
class name, so it is excluded by construction because that attribute is not in
the constructor-name set.

**15-05 gap closure (WR-02):** the ``<=2``-ctor count alone was a *vacuous*
guard for the singleton-leak it claims to prevent: a regression could thread a
single ``Client()`` AND still route every sweep probe through the module
singleton path (``matriz_client.client._request`` / ``_get_default()``), spinning
up a SECOND runtime ``Client`` (separate TokenStore → second remarkets login)
that the ctor-count never sees because the singleton is constructed *inside the
package*, not in the driver. This module adds a second, complementary static
assertion: the driver SOURCE must contain ZERO singleton-path references
(``_get_default(``, the ``_request as _matriz_request`` import alias, and any
``_matriz_request(`` call site). A future regression that reintroduces the
singleton path FAILS this gate even though the ctor count stays at 2. Both
checks are pure static AST/source reads — no live calls, no credentials.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DRIVER = "main_matriz.py"

# The two client constructor names. Matched whether spelled bare (``ast.Name``)
# or module-qualified (``ast.Attribute``). Nothing else counts -- in particular
# any accessor/builder method call (an attribute access whose name is NOT one of
# these) is not a constructor and is excluded.
_CTOR_NAMES = frozenset({"Client", "AsyncClient"})

# WR-02: singleton-path source patterns that MUST NOT appear in the driver.
# Each maps the module-singleton dispatch path that the 15-05 migration
# eliminated. ``_get_default(`` is the cached-singleton accessor;
# ``_request as _matriz_request`` is the legacy shim import alias; and
# ``_matriz_request(`` is its call site. The driver now threads exactly one
# ``Client`` and routes through the instance-method helper ``_sync_matriz_request``
# instead — so none of these patterns may survive in the source.
#
# Patterns use a leading non-identifier boundary (``(?<![\w])``) so the gate does
# NOT false-positive on the NEW threaded helper ``_sync_matriz_request(``: that
# name ends in the literal substring ``_matriz_request(`` but is preceded by the
# identifier char ``c`` (``..._sync_matriz_request``), which the boundary
# excludes. The migrated driver is therefore GREEN; only a literal reintroduction
# of the bare singleton names trips the gate.
_FORBIDDEN_SINGLETON_PATTERNS = (
    re.compile(r"(?<![\w])_get_default\("),
    re.compile(r"(?<![\w])_request as _matriz_request(?![\w])"),
    re.compile(r"(?<![\w])_matriz_request\("),
)


def test_main_matriz_uses_single_client_instance() -> None:
    """AST walk: ``1 <= (Client|AsyncClient) ctor Calls <= 2`` in the driver.

    Lower bound (>=1) is the non-vacuity guard: the un-migrated driver constructs
    zero classes (all via ``_base_url`` / ``_get_default()``) and so FAILS RED.
    The migrated driver constructs exactly two (one sync ``Client`` + one async
    ``AsyncClient``) and PASSES GREEN. The upper bound (<=2) caps the async
    surface at exactly one ``AsyncClient`` -- the TokenStore-corruption mitigation.
    """
    tree = ast.parse((_REPO_ROOT / _DRIVER).read_text(encoding="utf-8"))
    ctor_sites: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id in _CTOR_NAMES:
            ctor_sites.append((node.lineno, func.id))
        elif isinstance(func, ast.Attribute) and func.attr in _CTOR_NAMES:
            ctor_sites.append((node.lineno, func.attr))
    assert 1 <= len(ctor_sites) <= 2, (
        f"{_DRIVER} constructs {len(ctor_sites)} client instance(s) (expected 1..2): {ctor_sites}"
    )


def test_main_matriz_has_no_singleton_path_references() -> None:
    """Source scan: the driver routes NO request through the module singleton.

    WR-02 non-vacuity strengthening. The ``<=2``-ctor count cannot observe a
    second ``Client`` spun up *inside the package* by the module shim
    (``matriz_client.client._request`` → ``_get_default()``). This asserts the
    complementary invariant: the driver SOURCE contains none of the
    singleton-path fragments (``_get_default(``, the ``_request as _matriz_request``
    import alias, ``_matriz_request(`` call site). A regression that reintroduces
    any of them FAILS here even with the ctor count unchanged. Pure static
    source read — no execution, no network, no credentials.
    """
    source = (_REPO_ROOT / _DRIVER).read_text(encoding="utf-8")
    offenders = [pat.pattern for pat in _FORBIDDEN_SINGLETON_PATTERNS if pat.search(source)]
    assert not offenders, (
        f"{_DRIVER} still references the module singleton path "
        f"(15-05 migration must route all probes through the threaded Client): "
        f"{offenders}"
    )
