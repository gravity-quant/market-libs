"""RedactingFilter + attach() — higyrus_client Phase 8 LOG-01/02/03 + Higyrus JSON password (login body) + JSON token (login response) + cuit URL query redaction (D-10).

higyrus-specific patterns extend the ámbito baseline (Bearer + URL-encoded
password + JSON password) with the Higyrus-specific shapes per PATTERNS.md
line 254-260:

- JSON ``"password":"<value>"`` — the login request body shape per
  ``_core.py:189-197`` (``POST /api/login`` with
  ``{"clientId":..., "username":..., "password":...}``).
- JSON ``"token":"<value>"`` — the login response payload per
  ``_core.py:200-223`` (``{"token":"..."}``). If a caller enables DEBUG-level
  logs on the package logger, the response body could end up in a record before
  any structured field surfaces it.
- URL query ``cuit=<digits>`` — Argentine tax ID (PII) that some Higyrus URL
  paths include as a query param. Defensive redaction beyond the locked
  roadmap; per PATTERNS line 259.

Patterns NOT included (vs iol): ``refresh_token`` shapes — Higyrus uses a
single Bearer token without OAuth refresh, so the ``_REFRESH_TOKEN_*`` regexes
are iol-specific. Pattern isolation between paquetes is a hard invariant.

LOG-01: ``attach()`` adds ``NullHandler`` + ``RedactingFilter`` to
``logging.getLogger("higyrus_client")`` ONLY — NEVER ``logging.root``.
Idempotent: re-running ``attach()`` does not duplicate handlers/filters.

LOG-02: ``RedactingFilter`` rewrites ``record.msg``, ``record.args``, AND
string values in ``record.__dict__`` (covers ``extra={...}`` fields) BEFORE
emission so credential substrings never reach downstream consumer handlers
(Sentry, etc.).

NOT importable from ``verification/`` — each paquete duplicates this module by
design (the "no shared internals between packages" constraint).
"""

from __future__ import annotations

import logging
import re

__all__ = ["RedactingFilter", "attach"]


# ---------------------------------------------------------------------------
# Redaction patterns (higyrus — Bearer/X-Auth-Token + password + JSON token + cuit query)
# ---------------------------------------------------------------------------

_BEARER_RE = re.compile(r"Bearer\s+[A-Za-z0-9._\-]+")
_X_AUTH_TOKEN_RE = re.compile(r"(X-Auth-Token\s*:\s*)[A-Za-z0-9._\-]+", re.IGNORECASE)
_PASSWORD_URLENC_RE = re.compile(r"(password=)[^&\s]+")
_PASSWORD_JSON_RE = re.compile(r'("password"\s*:\s*")[^"]+(")')
# D-10 + higyrus-specific (per PATTERNS.md line 254-260):
# - Higyrus login response body shape: ``{"token": "<jwt-like>", ...}``.
_TOKEN_JSON_RE = re.compile(r'("token"\s*:\s*")[^"]+(")')
# - Argentine tax ID (PII): URL query ``cuit=<digits>`` — present in some
#   Higyrus URL shapes. Defensive redaction.
_CUIT_QUERY_RE = re.compile(r"(cuit=)\d+")

_REDACTION_MARKERS: tuple[str, ...] = (
    "Bearer ",
    "X-Auth-Token",
    "password=",
    '"password"',
    '"token"',
    "cuit=",
)


def _redact(text: str) -> str:
    """Apply higyrus redaction passes in order. Idempotent on already-redacted text."""
    redacted = _BEARER_RE.sub("Bearer ***", text)
    redacted = _X_AUTH_TOKEN_RE.sub(r"\1***", redacted)
    redacted = _PASSWORD_URLENC_RE.sub(r"\1***", redacted)
    redacted = _PASSWORD_JSON_RE.sub(r"\1***\2", redacted)
    redacted = _TOKEN_JSON_RE.sub(r"\1***\2", redacted)
    return _CUIT_QUERY_RE.sub(r"\1***", redacted)


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
    """Attach NullHandler + RedactingFilter to the higyrus package logger.

    Idempotent — calling ``attach()`` multiple times does not duplicate the
    handler or filter. The library logger convention per the Python Logging
    HOWTO: library code attaches a NullHandler so consumers see no records by
    default, but can opt in via
    ``logging.getLogger("higyrus_client").setLevel(logging.DEBUG)``.
    """
    logger = logging.getLogger("higyrus_client")
    if not any(isinstance(h, logging.NullHandler) for h in logger.handlers):
        logger.addHandler(logging.NullHandler())
    if not any(isinstance(f, RedactingFilter) for f in logger.filters):
        logger.addFilter(RedactingFilter())
