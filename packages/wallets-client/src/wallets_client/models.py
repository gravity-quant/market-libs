"""Response models for the wallets client -- deliberately empty, and import-free.

``wallets-client`` is still a **stub**: it has no verifiable endpoints, declares
no response shapes, and is the one package carrying the Phase 29 decoder
exemption written up in
``.planning/phases/29-decoder-observable/29-WALLETS-EXEMPTION.md``. That exemption
is scoped to ``_decode.py``, which this package still does not have.

The module exists so the six packages of this workspace present the same file
layout (Phase 31, TYP-03) and the first real wallets endpoint is born with
somewhere to declare its response shape.

**This module imports nothing** beyond the mandatory ``__future__`` flag, and
that is load-bearing rather than stylistic. There is no ``_decode.py`` in this
package to import a walker from, so a ``SafeModel`` copied here to make the
layout look more uniform than it is would raise ``ImportError`` the moment the
package is imported, reddening all twelve wallets CI matrix legs. A
cosmetically-uniform package that fails to import trades a documented gap for a
hidden outage.

Enrollment of this package into the workspace's cross-cutting package lists is
settled by Phase 32 (D-16 reconciliation), not here.
"""

from __future__ import annotations

__all__: list[str] = []
