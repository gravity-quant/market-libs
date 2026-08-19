"""RedactingFilter + attach() — iol_client Phase 8 LOG-01/02/03 + IOL OAuth refresh_token redaction (D-10).

iol-specific patterns extend the ámbito baseline (Bearer + URL-encoded password +
JSON password) with the OAuth ``refresh_token`` formats that the IOL ``/token``
endpoint emits per ``_core.py:175-178``:

- ``refresh_token=<value>`` in URL-encoded form (request body for OAuth grant).
- ``"refresh_token":"<value>"`` in JSON (response body for both login + refresh).

The login response payload arrives at our parser as JSON
``{"access_token": "...", "refresh_token": "...", "expires_in": 900}`` — if a
caller enables DEBUG-level logs on the package logger, the response body could
end up in a record before any structured field surfaces it. Both formats MUST be
scrubbed before emission.

LOG-01: ``attach()`` adds ``NullHandler`` + ``RedactingFilter`` to
``logging.getLogger("iol_client")`` ONLY — NEVER ``logging.root``. Idempotent:
re-running ``attach()`` does not duplicate handlers/filters.

LOG-02: ``RedactingFilter`` rewrites ``record.msg``, ``record.args``, AND string
values in ``record.__dict__`` (covers ``extra={...}`` fields) BEFORE emission so
credential substrings never reach downstream consumer handlers (Sentry, etc.).
Phase 29 D-05 part (a): the ``record.__dict__`` scan now reaches string leaves
nested inside ``dict`` / ``list`` / ``tuple`` values, bounded per
``29-AGGREGATION-CONTRACT.md`` lock 12.

**Phase 29 D-05 part (b) — marker anchoring is deliberately UNCHANGED.**
``_redact`` is a chain of marker-anchored regexes (``Bearer <tok>``,
``"password": "<secret>"``, ``refresh_token=<value>``). A bare credential or a
bare account identifier carrying no marker matches none of them and ships intact
to every downstream handler. **No change to this filter makes a wire value safe
to log.** The guarantee for Phase 29's divergence record is carried by the record
contract in ``29-AGGREGATION-CONTRACT.md`` (lock 1 + lock 11): flat, all-str, top
level, type-not-value, never the wire value — there is no key in that schema in
which a wire value can travel. The scan fix here is defense in depth for *other*
callers' ``extra`` dicts, nothing more. The iol marker tuple and the ``_redact``
pass chain — including the OAuth ``refresh_token`` / ``access_token`` shapes that
are iol-specific by design — are byte-unchanged by Phase 29.

NOT importable from ``verification/`` — each paquete duplicates this module by
design (the "no shared internals between packages" constraint).
"""

from __future__ import annotations

import logging
import re
from typing import Any

__all__ = ["RedactingFilter", "attach"]


# ---------------------------------------------------------------------------
# Redaction patterns (iol — Bearer/X-Auth-Token + password + OAuth refresh_token)
# ---------------------------------------------------------------------------

_BEARER_RE = re.compile(r"Bearer\s+[A-Za-z0-9._\-]+")
_X_AUTH_TOKEN_RE = re.compile(r"(X-Auth-Token\s*:\s*)[A-Za-z0-9._\-]+", re.IGNORECASE)
_PASSWORD_URLENC_RE = re.compile(r"(password=)[^&\s]+")
_PASSWORD_JSON_RE = re.compile(r'("password"\s*:\s*")[^"]+(")')
# D-10 + IOL-specific (per PATTERNS.md line 254-260): the OAuth refresh_token
# value appears in BOTH URL-encoded (form body) and JSON (response body) shapes.
_REFRESH_TOKEN_URLENC_RE = re.compile(r"(refresh_token=)[^&\s]+")
_REFRESH_TOKEN_JSON_RE = re.compile(r'("refresh_token"\s*:\s*")[^"]+(")')
# IOL login response payload also contains access_token in JSON form — same shape.
_ACCESS_TOKEN_JSON_RE = re.compile(r'("access_token"\s*:\s*")[^"]+(")')

_REDACTION_MARKERS: tuple[str, ...] = (
    "Bearer ",
    "X-Auth-Token",
    "password=",
    '"password"',
    "refresh_token=",
    '"refresh_token"',
    '"access_token"',
)


def _redact(text: str) -> str:
    """Apply iol redaction passes in order. Idempotent on already-redacted text."""
    redacted = _BEARER_RE.sub("Bearer ***", text)
    redacted = _X_AUTH_TOKEN_RE.sub(r"\1***", redacted)
    redacted = _PASSWORD_URLENC_RE.sub(r"\1***", redacted)
    redacted = _PASSWORD_JSON_RE.sub(r"\1***\2", redacted)
    redacted = _REFRESH_TOKEN_URLENC_RE.sub(r"\1***", redacted)
    redacted = _REFRESH_TOKEN_JSON_RE.sub(r"\1***\2", redacted)
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

    D-10: rewrites ``record.msg``/``record.args``/``record.__dict__`` values
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
    """Attach NullHandler + RedactingFilter to the iol package logger.

    Idempotent — calling ``attach()`` multiple times does not duplicate the
    handler or filter. The library logger convention per the Python Logging
    HOWTO: library code attaches a NullHandler so consumers see no records by
    default, but can opt in via
    ``logging.getLogger("iol_client").setLevel(logging.DEBUG)``.
    """
    logger = logging.getLogger("iol_client")
    if not any(isinstance(h, logging.NullHandler) for h in logger.handlers):
        logger.addHandler(logging.NullHandler())
    if not any(isinstance(f, RedactingFilter) for f in logger.filters):
        logger.addFilter(RedactingFilter())
