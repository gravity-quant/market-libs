"""RedactingFilter + attach() — market_data_client Phase 20 CORE-MD-01 / LOG-01 (D-11).

market-data-client uses the Auth0 ``client_credentials`` grant. The pattern set
swaps iol's baseline (D-11):

- KEEP ``Bearer`` (Authorization header) and JSON ``access_token`` (Auth0 token
  response body ``{"access_token": "...", "expires_in": ...}``).
- DROP iol's ``password`` / ``refresh_token`` / ``X-Auth-Token`` patterns — the
  client_credentials grant never sends any of those.
- ADD ``client_secret`` in BOTH shapes: URL-encoded form body
  (``grant_type=client_credentials&client_secret=<secret>&audience=<aud>``) and
  JSON (``"client_secret":"<secret>"``). Both MUST be scrubbed before any DEBUG
  record reaches a downstream handler — CORE-MD-01 zero-leak gate (SC4).

LOG-01: ``attach()`` adds ``NullHandler`` + ``RedactingFilter`` to
``logging.getLogger("market_data_client")`` ONLY — NEVER the root logger.
Idempotent: re-running ``attach()`` does not duplicate handlers/filters. The CI
LOG-01 grep gate fails the build if package src configures the root logger.

``RedactingFilter`` rewrites ``record.msg``, ``record.args`` (dict + tuple), AND
string values in ``record.__dict__`` (covers ``extra={...}`` fields) BEFORE
emission so credential substrings never reach downstream consumers (Sentry, etc.).
Phase 29 D-05 part (a): the ``record.__dict__`` scan now reaches string leaves
nested inside ``dict`` / ``list`` / ``tuple`` values, bounded per
``29-AGGREGATION-CONTRACT.md`` lock 12.

**Phase 29 D-05 part (b) — marker anchoring is deliberately UNCHANGED.**
``_redact`` is a chain of marker-anchored regexes (``Bearer <tok>``,
``client_secret=<secret>``, ``"client_secret": "<secret>"``,
``"access_token": "<tok>"``). A bare credential, a bare symbol identifier or a
bare account identifier carrying no marker matches none of them and ships intact
to every downstream handler. **No change to this filter makes a wire value safe
to log.** The guarantee for Phase 29's divergence record is carried by the record
contract in ``29-AGGREGATION-CONTRACT.md`` (lock 1 + lock 11): flat, all-str, top
level, type-not-value, never the wire value — there is no key in that schema in
which a wire value can travel. The scan fix here is defense in depth for *other*
callers' ``extra`` dicts, nothing more.

NOT importable from ``verification/`` — each paquete duplicates this module by
design (the "no shared internals between packages" constraint).
"""

from __future__ import annotations

import logging
import re
from typing import Any

__all__ = ["RedactingFilter", "attach"]


# ---------------------------------------------------------------------------
# Redaction patterns (D-11 — Bearer + access_token JSON + client_secret url/JSON)
# ---------------------------------------------------------------------------

_BEARER_RE = re.compile(r"Bearer\s+[A-Za-z0-9._\-]+")
_ACCESS_TOKEN_JSON_RE = re.compile(r'("access_token"\s*:\s*")[^"]+(")')
# D-11: the Auth0 client_credentials secret appears in BOTH URL-encoded (form
# body) and JSON shapes — scrub both.
_CLIENT_SECRET_URLENC_RE = re.compile(r"(client_secret=)[^&\s]+")
_CLIENT_SECRET_JSON_RE = re.compile(r'("client_secret"\s*:\s*")[^"]+(")')

_REDACTION_MARKERS: tuple[str, ...] = (
    "Bearer ",
    "client_secret=",
    '"client_secret"',
    '"access_token"',
)


def _redact(text: str) -> str:
    """Apply the D-11 redaction passes in order. Idempotent on already-redacted text."""
    redacted = _BEARER_RE.sub("Bearer ***", text)
    redacted = _CLIENT_SECRET_URLENC_RE.sub(r"\1***", redacted)
    redacted = _CLIENT_SECRET_JSON_RE.sub(r"\1***\2", redacted)
    return _ACCESS_TOKEN_JSON_RE.sub(r"\1***\2", redacted)


# --- decode-intactness: generic-scan begin ---
# Phase 29 D-05 part (a) + ``29-AGGREGATION-CONTRACT.md`` lock 12.
#
# Both bounds are NAMED CONSTANTS and must stay that way — do not "clean up"
# the magic numbers. A log filter runs on EVERY record, on the emitting
# thread: an unbounded traversal is a latency amplifier on a hot path, and a
# hostile (or merely enormous) payload sitting in some other caller's
# ``extra`` dict turns it into a CPU sink. Beyond ``_MAX_SCAN_DEPTH`` a
# container is left untouched; a container with more than
# ``_MAX_SCAN_ENTRIES`` entries is skipped rather than walked. Neither bound
# costs anything for the Phase 29 divergence record itself, which is flat by
# lock 1 and therefore never recurses at all.
_MAX_SCAN_DEPTH = 4
_MAX_SCAN_ENTRIES = 64


def _redact_nested(value: Any, depth: int) -> Any:
    """Rebuild ``value`` with redacted string leaves, within the lock-12 bounds.

    Container type is preserved (a ``tuple`` stays a ``tuple``, a ``list``
    stays a ``list``) and ``dict`` keys are never touched — only values are
    rebuilt. When nothing beneath ``value`` changed, the ORIGINAL object is
    returned, so a record whose extras carry no marker keeps object identity
    exactly as it did before this fix.
    """
    if isinstance(value, str):
        return _redact(value) if any(m in value for m in _REDACTION_MARKERS) else value
    if depth >= _MAX_SCAN_DEPTH:
        return value
    if isinstance(value, dict):
        if len(value) > _MAX_SCAN_ENTRIES:
            return value
        rebuilt_map = {k: _redact_nested(v, depth + 1) for k, v in value.items()}
        if all(rebuilt_map[k] is v for k, v in value.items()):
            return value
        return rebuilt_map
    if isinstance(value, list | tuple):
        if len(value) > _MAX_SCAN_ENTRIES:
            return value
        rebuilt_seq = [_redact_nested(v, depth + 1) for v in value]
        if all(new is old for new, old in zip(rebuilt_seq, value, strict=True)):
            return value
        return tuple(rebuilt_seq) if isinstance(value, tuple) else rebuilt_seq
    return value


def _scan_record_dict(record: logging.LogRecord) -> None:
    """Redact string leaves anywhere in ``record.__dict__`` (covers ``extra={...}``).

    Before Phase 29 this loop inspected only values that were ALREADY strings,
    so a string leaf nested inside a dict / list / tuple value was never
    reached and shipped intact to every downstream handler.
    """
    for key, value in list(record.__dict__.items()):
        record.__dict__[key] = _redact_nested(value, 0)


# --- decode-intactness: generic-scan end ---


class RedactingFilter(logging.Filter):
    """Scrub credential substrings from log records BEFORE emission.

    D-11: rewrites ``record.msg`` / ``record.args`` / ``record.__dict__`` values
    in-place. Always returns ``True`` (records are always emitted; only their
    content is mutated).
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = _redact(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: _redact(v) if isinstance(v, str) else v for k, v in record.args.items()
                }
            else:
                record.args = tuple(_redact(a) if isinstance(a, str) else a for a in record.args)
        # Scan record.__dict__ for sentinel substrings in extra= values.
        # Any package-specific pre-scan block MUST stay ABOVE this call (cf.
        # matriz's D-22 ``auth_basic`` tuple split), so the generic scan is the
        # last thing that touches ``record.__dict__``.
        _scan_record_dict(record)
        return True


def attach() -> None:
    """Attach NullHandler + RedactingFilter to the market_data_client package logger.

    Idempotent — calling ``attach()`` multiple times does not duplicate the
    handler or filter. Per the Python Logging HOWTO: library code attaches a
    NullHandler so consumers see no records by default, but can opt in via
    ``logging.getLogger("market_data_client").setLevel(logging.DEBUG)``. Touches
    ONLY the package logger, never the root logger (CI LOG-01 gate).
    """
    logger = logging.getLogger("market_data_client")
    if not any(isinstance(h, logging.NullHandler) for h in logger.handlers):
        logger.addHandler(logging.NullHandler())
    if not any(isinstance(f, RedactingFilter) for f in logger.filters):
        logger.addFilter(RedactingFilter())
