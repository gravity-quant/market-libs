"""RedactingFilter + attach() — Phase 8 LOG-01/LOG-02/LOG-03.

ámbito-specific patterns: Bearer + URL-encoded password + JSON password. ámbito
has no real auth surface (no token / no credentials in URL / no Authorization
header) — so these patterns are forward-consistency baseline. iol/higyrus/matriz
will extend with their package-specific patterns (IOL refresh_token, Higyrus JSON
password, matriz auth_basic) in their own ``_logging.py``.

LOG-01: ``attach()`` adds ``NullHandler`` + ``RedactingFilter`` to
``logging.getLogger("ambito_financiero_client")`` ONLY — NEVER ``logging.root``.
Idempotent: re-running ``attach()`` does not duplicate handlers/filters.

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
# Redaction patterns (ámbito baseline — extended per paquete in iol/higyrus/matriz)
# ---------------------------------------------------------------------------

_BEARER_RE = re.compile(r"Bearer\s+[A-Za-z0-9._\-]+")
_PASSWORD_URLENC_RE = re.compile(r"(password=)[^&\s]+")
_PASSWORD_JSON_RE = re.compile(r'("password"\s*:\s*")[^"]+(")')

_REDACTION_MARKERS: tuple[str, ...] = (
    "Bearer ",
    "password=",
    '"password"',
)


def _redact(text: str) -> str:
    """Apply the ámbito redaction passes in order. Idempotent on already-redacted text."""
    redacted = _BEARER_RE.sub("Bearer ***", text)
    redacted = _PASSWORD_URLENC_RE.sub(r"\1***", redacted)
    return _PASSWORD_JSON_RE.sub(r"\1***\2", redacted)


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
    """Attach NullHandler + RedactingFilter to the ámbito package logger.

    Idempotent — calling ``attach()`` multiple times does not duplicate the
    handler or filter. The library logger convention per the Python Logging
    HOWTO: library code attaches a NullHandler so consumers see no records by
    default, but can opt in via ``logging.getLogger("ambito_financiero_client")
    .setLevel(logging.DEBUG)``.
    """
    logger = logging.getLogger("ambito_financiero_client")
    if not any(isinstance(h, logging.NullHandler) for h in logger.handlers):
        logger.addHandler(logging.NullHandler())
    if not any(isinstance(f, RedactingFilter) for f in logger.filters):
        logger.addFilter(RedactingFilter())
