"""RedactingFilter + attach() — matriz_client Phase 8 LOG-01/02/03 + D-22.

matriz-specific patterns extend the ámbito baseline (Bearer + URL-encoded
password) with the matriz-specific shapes per PATTERNS.md line 260:

- ``X-Auth-Token`` header — matriz Primary API token header (per
  ``_core.py:255-262``). Redacted to ``X-Auth-Token: ***``.
- ``X-Username`` header — matriz login request credential header. Operational
  field; preserved as-is per D-22 user/password split philosophy (the username
  is the operational identifier; only the password is the secret).
- ``X-Password`` header — matriz login request credential header. Redacted to
  ``X-Password: ***``.
- ``Authorization: Basic <base64>`` header — matriz Risk API §9 (HTTP Basic).
  Redacted to ``Authorization: Basic ***`` (D-22).
- ``auth_basic`` tuple in ``record.__dict__`` (extra={...}) — D-22 special:
  detected as ``(user, password)`` tuple, split into
  ``auth_basic_user=<user>`` (operational, preserved) +
  ``auth_basic_password="***"`` (redacted). The original ``auth_basic`` key is
  removed so the tuple form NEVER reaches downstream handlers.
- URL-encoded ``password=<value>`` — defensive.
- JSON ``"password":"<value>"`` — defensive.

Patterns NOT included (vs higyrus / iol):

- No ``_TOKEN_JSON_RE`` (higyrus-specific — matriz token comes via
  ``X-Auth-Token`` response header, not JSON body).
- No ``_CUIT_QUERY_RE`` (higyrus-specific PII — matriz has no cuit in URL).
- No ``_REFRESH_TOKEN_*`` (iol-specific — matriz has no OAuth refresh).

Pattern isolation between paquetes is a hard invariant.

LOG-01: ``attach()`` adds ``NullHandler`` + ``RedactingFilter`` to
``logging.getLogger("matriz_client")`` ONLY — NEVER ``logging.root``.
Idempotent: re-running ``attach()`` does not duplicate handlers/filters.

LOG-02: ``RedactingFilter`` rewrites ``record.msg``, ``record.args``, AND
string values in ``record.__dict__`` (covers ``extra={...}`` fields) BEFORE
emission so credential substrings never reach downstream consumer handlers
(Sentry, etc.). D-22 additionally splits the ``auth_basic`` tuple field.

NOT importable from ``verification/`` — each paquete duplicates this module by
design (the "no shared internals between packages" constraint).
"""

from __future__ import annotations

import logging
import re

__all__ = ["RedactingFilter", "attach"]


# ---------------------------------------------------------------------------
# Redaction patterns (matriz — D-22 auth_basic + X-Auth-Token / X-Username /
# X-Password headers + defensive password URL/JSON shapes)
# ---------------------------------------------------------------------------

_BEARER_RE = re.compile(r"Bearer\s+[A-Za-z0-9._\-]+")
# X-Auth-Token: matriz Primary API token header (per _core.py:255-262 login
# response). The token shape allows letters, digits, dots, dashes, underscores
# plus base64 padding (+/=) defensively.
_X_AUTH_TOKEN_RE = re.compile(
    r"(X-Auth-Token\s*:\s*)[A-Za-z0-9._\-+/=]+",
    re.IGNORECASE,
)
# X-Username: operational header — preserved (per D-22 split philosophy: the
# username is NOT secret, only the password is). We do NOT include an
# _X_USERNAME_RE substitution because we want the header value visible in
# logs for correlation. The pattern is defined ONLY for symmetry-completeness
# at the module level (referenced by tests) but it is NOT used in `_redact`.
_X_USERNAME_RE = re.compile(r"(X-Username\s*:\s*)[^\r\n]+", re.IGNORECASE)
# X-Password: redacted always.
_X_PASSWORD_RE = re.compile(r"(X-Password\s*:\s*)[^\r\n]+", re.IGNORECASE)
# D-22: Authorization: Basic <base64> — matriz Risk API §9 header.
_AUTH_BASIC_RE = re.compile(
    r"(Authorization\s*:\s*Basic\s+)[A-Za-z0-9+/=]+",
    re.IGNORECASE,
)
_PASSWORD_URLENC_RE = re.compile(r"(password=)[^&\s]+")
_PASSWORD_JSON_RE = re.compile(r'("password"\s*:\s*")[^"]+(")')

_REDACTION_MARKERS: tuple[str, ...] = (
    "Bearer ",
    "X-Auth-Token",
    "X-Password",
    "Authorization: Basic",
    "Authorization:Basic",  # tolerate missing space
    "password=",
    '"password"',
)


def _redact(text: str) -> str:
    """Apply matriz redaction passes in order. Idempotent on already-redacted text.

    Note: ``X-Username`` is INTENTIONALLY not redacted — username is operational
    metadata (D-22 split). Only the password half is a secret.
    """
    redacted = _BEARER_RE.sub("Bearer ***", text)
    redacted = _X_AUTH_TOKEN_RE.sub(r"\1***", redacted)
    redacted = _X_PASSWORD_RE.sub(r"\1***", redacted)
    redacted = _AUTH_BASIC_RE.sub(r"\1***", redacted)
    redacted = _PASSWORD_URLENC_RE.sub(r"\1***", redacted)
    return _PASSWORD_JSON_RE.sub(r"\1***\2", redacted)


def _redact_auth_basic_tuple(value: object) -> dict[str, str] | None:
    """D-22 helper — split a ``(user, password)`` tuple to user/password fields.

    Returns a dict with ``auth_basic_user`` (operational) and
    ``auth_basic_password`` (redacted to ``"***"``). Returns ``None`` for any
    malformed input (non-tuple, wrong arity, non-string members) — defensive
    against accidental misuse so the filter never crashes a log emission.
    """
    if not isinstance(value, tuple) or len(value) != 2:
        return None
    user, password = value
    if not isinstance(user, str) or not isinstance(password, str):
        return None
    return {"auth_basic_user": user, "auth_basic_password": "***"}


class RedactingFilter(logging.Filter):
    """Scrub credential substrings from log records BEFORE emission.

    D-10 + D-22: rewrites ``record.msg``/``record.args``/``record.__dict__``
    values in-place. D-22 special handling: ``record.__dict__["auth_basic"]``
    tuple is split into ``auth_basic_user`` + ``auth_basic_password="***"`` and
    the original key removed.

    Always returns ``True`` (records are always emitted; only their content is
    mutated).
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
        # D-22: detect `auth_basic` tuple in extras and split it BEFORE the
        # generic record.__dict__ scan (otherwise the tuple would survive as a
        # non-string field and leak the password).
        if "auth_basic" in record.__dict__:
            split = _redact_auth_basic_tuple(record.__dict__["auth_basic"])
            if split is not None:
                del record.__dict__["auth_basic"]
                record.__dict__.update(split)
        # Scan record.__dict__ for sentinel substrings in extra= values.
        for key, value in list(record.__dict__.items()):
            if isinstance(value, str) and any(m in value for m in _REDACTION_MARKERS):
                record.__dict__[key] = _redact(value)
        return True


def attach() -> None:
    """Attach NullHandler + RedactingFilter to the matriz package logger.

    Idempotent — calling ``attach()`` multiple times does not duplicate the
    handler or filter. The library logger convention per the Python Logging
    HOWTO: library code attaches a NullHandler so consumers see no records by
    default, but can opt in via
    ``logging.getLogger("matriz_client").setLevel(logging.DEBUG)``.
    """
    logger = logging.getLogger("matriz_client")
    if not any(isinstance(h, logging.NullHandler) for h in logger.handlers):
        logger.addHandler(logging.NullHandler())
    if not any(isinstance(f, RedactingFilter) for f in logger.filters):
        logger.addFilter(RedactingFilter())
