"""Shared type vocabulary for the wallets client -- deliberately empty, import-free.

``wallets-client`` is still a **stub**: it has no verifiable endpoints, declares
no enum-like parameters, and is the one package carrying the Phase 29 decoder
exemption written up in
``.planning/phases/29-decoder-observable/29-WALLETS-EXEMPTION.md``. That exemption
is scoped to ``_decode.py``, which this package still does not have.

The module exists so the six packages of this workspace present the same file
layout (Phase 31, TYP-03) and the first real wallets endpoint is born with
somewhere to put its vocabulary. :mod:`matriz_client.types` is the shape it grows
into; payload shapes belong in ``models.py``.

Even once endpoints land, no :class:`~typing.Literal` alias here will close a
**response** field: ``.planning/phases/29-decoder-observable/29-DLOCK-RESPONSE-LITERAL.md``
is the signed lock under which response fields decode as ``str`` and out-of-set
wire values are reported as divergences, never rejected or coerced. The one
promotion already identified across the workspace -- ``iol_client``'s ``mercado``
and ``plazo`` -- is deferred to Phase 33 pending a live census.

**This module imports nothing** beyond the mandatory ``__future__`` flag, for the
same reason its sibling ``models.py`` does not: this package has no ``_decode.py``
to import from, and an import of one would raise ``ImportError`` the moment the
package is imported, reddening all twelve wallets CI matrix legs.
"""

from __future__ import annotations

__all__: list[str] = []
