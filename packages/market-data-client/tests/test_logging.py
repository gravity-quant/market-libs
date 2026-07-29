"""Unit tests for ``market_data_client._logging.RedactingFilter`` + ``attach()``.

Phase 20 market-data-client. CORE-MD-01 / LOG-01 / D-11. Verifies redaction
patterns (Bearer, access_token JSON, client_secret URL-encoded + JSON),
attach idempotency + package-logger scoping, ``record.args`` (dict + tuple) and
``record.__dict__`` scan coverage.

D-11 swaps iol's pattern set: KEEP ``Bearer`` and JSON ``access_token``; DROP
iol's password / refresh_token / X-Auth-Token patterns; ADD ``client_secret`` in
BOTH form-encoded (Auth0 client_credentials request body) and JSON shapes. Zero
credential leakage in logs is a hard CORE-MD-01 gate (SC4).
"""

from __future__ import annotations

import logging

from market_data_client._logging import RedactingFilter, attach


def _make_record(
    msg: str, args: object = None, extra: dict[str, object] | None = None
) -> logging.LogRecord:
    record = logging.LogRecord(
        name="market_data_client",
        level=logging.DEBUG,
        pathname=__file__,
        lineno=0,
        msg=msg,
        args=args,  # type: ignore[arg-type]
        exc_info=None,
    )
    if extra:
        for k, v in extra.items():
            setattr(record, k, v)
    return record


def test_redact_bearer() -> None:
    """CORE-MD-01: ``Bearer <token>`` in record.msg → ``Bearer ***``."""
    f = RedactingFilter()
    record = _make_record("Authorization: Bearer eyJabc.def-ghi")
    assert f.filter(record) is True
    assert "eyJabc.def-ghi" not in record.msg
    assert "Bearer ***" in record.msg


def test_redact_access_token_json() -> None:
    """CORE-MD-01: JSON ``"access_token":"..."`` body redacted in record.msg."""
    f = RedactingFilter()
    record = _make_record('body={"access_token":"eyJsecret"}')
    f.filter(record)
    assert "eyJsecret" not in record.msg
    assert '"access_token":"***"' in record.msg


def test_redact_client_secret_urlenc() -> None:
    """CORE-MD-01 / D-11: URL-encoded ``client_secret=<value>`` redacted.

    Auth0 client_credentials request body shape:
    ``grant_type=client_credentials&client_secret=<secret>&audience=<aud>``.
    Surrounding non-secret fields survive.
    """
    f = RedactingFilter()
    record = _make_record(
        "token form: grant_type=client_credentials&client_secret=sup3r-s3cret&audience=aud"
    )
    f.filter(record)
    assert "sup3r-s3cret" not in record.msg
    assert "client_secret=***" in record.msg
    assert "grant_type=client_credentials" in record.msg
    assert "audience=aud" in record.msg


def test_redact_client_secret_json() -> None:
    """CORE-MD-01 / D-11: JSON ``"client_secret":"..."`` body redacted."""
    f = RedactingFilter()
    record = _make_record('body={"client_secret":"sup3r-s3cret"}')
    f.filter(record)
    assert "sup3r-s3cret" not in record.msg
    assert '"client_secret":"***"' in record.msg


def test_redact_scans_args_and_dict() -> None:
    """CORE-MD-01: credentials in record.args (dict + tuple) and record.__dict__ scrubbed."""
    f = RedactingFilter()

    # Tuple args
    rec_tuple = _make_record("auth: %s", args=("Bearer eyJtok.val",))
    f.filter(rec_tuple)
    assert isinstance(rec_tuple.args, tuple)
    assert rec_tuple.args[0] == "Bearer ***"

    # Dict args — logging wraps a single mapping in a 1-tuple, then LogRecord
    # unwraps it to record.args (the raw dict). Mirror that here.
    rec_dict = _make_record("auth: %(h)s", args=({"h": "Bearer eyJtok.val"},))
    f.filter(rec_dict)
    assert isinstance(rec_dict.args, dict)
    assert rec_dict.args["h"] == "Bearer ***"

    # record.__dict__ extra field
    rec_extra = _make_record(
        "ok", extra={"weird": "client_secret=leaky-xxx", "safe": "ok"}
    )
    f.filter(rec_extra)
    assert rec_extra.__dict__["weird"] == "client_secret=***"
    assert rec_extra.__dict__["safe"] == "ok"


def test_attach_idempotent() -> None:
    """LOG-01: attach() adds NullHandler + RedactingFilter to the package logger
    exactly once each; the root logger gets neither from attach()."""
    root = logging.getLogger()
    root_null_before = [h for h in root.handlers if isinstance(h, logging.NullHandler)]
    root_filters_before = [f for f in root.filters if isinstance(f, RedactingFilter)]

    attach()
    attach()
    attach()

    logger = logging.getLogger("market_data_client")
    null_handlers = [h for h in logger.handlers if isinstance(h, logging.NullHandler)]
    redacting_filters = [f for f in logger.filters if isinstance(f, RedactingFilter)]
    assert len(null_handlers) == 1
    assert len(redacting_filters) == 1

    # Root logger untouched by attach().
    root_null_after = [h for h in root.handlers if isinstance(h, logging.NullHandler)]
    root_filters_after = [f for f in root.filters if isinstance(f, RedactingFilter)]
    assert len(root_null_after) == len(root_null_before)
    assert len(root_filters_after) == len(root_filters_before)
