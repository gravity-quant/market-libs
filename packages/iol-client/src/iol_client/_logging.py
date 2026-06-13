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

NOT importable from ``verification/`` — each paquete duplicates this module by
design (the "no shared internals between packages" constraint).
"""

from __future__ import annotations

import logging
import re

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
        for key, value in list(record.__dict__.items()):
            if isinstance(value, str) and any(m in value for m in _REDACTION_MARKERS):
                record.__dict__[key] = _redact(value)
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
