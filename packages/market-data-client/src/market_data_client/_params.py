"""Helpers for building market-data API query params.

Package-local copy of the higyrus ``drop_none`` helper (D-07): the
no-shared-internals constraint (CLAUDE.md) forbids importing any symbol from
``higyrus_client``, so the read builders in ``_core.py`` funnel their optional
filter kwargs through this local copy before handing them to the transport
shell.

Only ``drop_none`` is copied. The higyrus ``format_date`` / ``format_bool``
serializers are intentionally NOT copied: explicit boolean wire-encoding is
deferred to Phase 23 (D-07) — market-data booleans (``active``, ``with_data``)
rely on httpx's native ``True → "true"`` param encoding for now.
"""

from __future__ import annotations

from typing import Any

__all__ = ["drop_none"]


def drop_none(params: dict[str, Any]) -> dict[str, Any]:
    """Return ``params`` without keys whose value is ``None``.

    Preserves falsy-but-not-None values (``False``, ``0``, ``""``) because
    those are legitimate API inputs.
    """
    return {k: v for k, v in params.items() if v is not None}
