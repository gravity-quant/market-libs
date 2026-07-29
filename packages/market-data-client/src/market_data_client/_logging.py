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

NOT importable from ``verification/`` — each paquete duplicates this module by
design (the "no shared internals between packages" constraint).
"""

from __future__ import annotations

import logging
import re

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
        for key, value in list(record.__dict__.items()):
            if isinstance(value, str) and any(m in value for m in _REDACTION_MARKERS):
                record.__dict__[key] = _redact(value)
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
