"""Pure builders and parsers for the higyrus REST client.

Phase 7 REFAC-03 + D-01..D-09 — NO imports from ``higyrus_client.client`` or
``higyrus_client.aio`` (enforced by ``import-linter`` contract in
``pyproject.toml`` ``[tool.importlinter]``).

Placeholder en Plan 7-01 — Plans 7-02..7-06 lo extienden con ``RequestSpec``
per-package, builders, parsers y auth-flow primitives (D-01 + D-04).
"""

from __future__ import annotations

__all__: list[str] = []
