"""Response models for the Ambito Financiero client -- deliberately empty.

Ambito's single endpoint returns a scraped Argentine-format decimal, and this
package parses it through
:func:`ambito_financiero_client._parsing.parse_ar_decimal` straight into a
``float``. There is no envelope to model, so this package declares **no response
models today** (Phase 31, D-11).

The module exists anyway so the six packages of this workspace present the same
file layout (Phase 31, TYP-03) and the next endpoint is born with somewhere to
declare its response shape, instead of a model class appearing in ``client.py``
or a new home being invented per package.

Deliberately absent, and not an oversight: there is no ``SafeModel`` base here
and no import of :mod:`ambito_financiero_client._decode`. The walker is dormant
in this package by Phase 29's design, and a base class with no subclass would be
dead weight on a published wheel.

This module is **not** re-exported into :mod:`ambito_financiero_client`'s
``__all__``: doing so would add rows to
``verification/snapshots/ambito-financiero-client-surface.txt``, and this phase
changes the layout, not the public surface.
"""

from __future__ import annotations

__all__: list[str] = []
