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
Phase 29 D-05 part (a): the ``record.__dict__`` scan now reaches string leaves
nested inside ``dict`` / ``list`` / ``tuple`` values, bounded per
``29-AGGREGATION-CONTRACT.md`` lock 12.

**Ordering invariant (D-22 + Phase 29).** The ``auth_basic`` pre-scan runs
BEFORE the generic ``record.__dict__`` scan and must keep running before it.
The pre-scan turns a credential-bearing ``(user, password)`` TUPLE into two
string fields; the generic scan only redacts string leaves. Reversing the two
would leave the tuple untouched and leak the password. The generic scan lives
inside the ``decode-intactness: generic-scan`` marker region — the unit Plan 09
hashes across the five paquete copies — precisely so this package-specific
pre-scan can sit legitimately OUTSIDE that region without breaking byte
identity.

**Phase 29 D-05 part (b) — marker anchoring is deliberately UNCHANGED.**
``_redact`` is a chain of marker-anchored regexes (``Bearer <tok>``,
``X-Auth-Token: <tok>``, ``Authorization: Basic <b64>``, ``"password":
"<secret>"``). A bare credential carrying no marker matches none of them and
ships intact to every downstream handler. **No change to this filter makes a
wire value safe to log.** The guarantee for Phase 29's divergence record is
carried by the record contract in ``29-AGGREGATION-CONTRACT.md`` (lock 1 +
lock 11): flat, all-str, top level, type-not-value, never the wire value —
there is no key in that schema in which a wire value can travel. The scan fix
here is defense in depth for *other* callers' ``extra`` dicts, nothing more.

NOT importable from ``verification/`` — each paquete duplicates this module by
design (the "no shared internals between packages" constraint).
"""

from __future__ import annotations

import logging
import re
from typing import Any

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
        # The D-22 ``auth_basic`` pre-scan above MUST stay ABOVE this call: it
        # splits a credential-bearing TUPLE into redactable string fields, and
        # running the generic scan first would leave the tuple in place as a
        # non-string value and leak the password. The generic scan is therefore
        # the last thing that touches ``record.__dict__``.
        _scan_record_dict(record)
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
