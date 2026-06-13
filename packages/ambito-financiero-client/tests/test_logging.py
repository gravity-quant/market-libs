"""Unit tests for ``ambito_financiero_client._logging.RedactingFilter`` + ``attach()``.

Phase 8 LOG-01/LOG-02 / D-10. Verifies redaction patterns, attach idempotency,
``record.__dict__`` scan coverage, and the always-True filter return contract.
"""

from __future__ import annotations

import logging

from ambito_financiero_client._logging import RedactingFilter, attach


def _make_record(
    msg: str, args: object = None, extra: dict[str, object] | None = None
) -> logging.LogRecord:
    record = logging.LogRecord(
        name="ambito_financiero_client",
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


def test_attach_is_idempotent() -> None:
    """LOG-01: calling attach() multiple times MUST NOT duplicate handler/filter."""
    attach()
    attach()
    attach()
    logger = logging.getLogger("ambito_financiero_client")
    null_handlers = [h for h in logger.handlers if isinstance(h, logging.NullHandler)]
    redacting_filters = [f for f in logger.filters if isinstance(f, RedactingFilter)]
    assert len(null_handlers) == 1
    assert len(redacting_filters) == 1


def test_redact_bearer_token_in_msg() -> None:
    """LOG-02: Bearer <token> in record.msg → Bearer ***."""
    f = RedactingFilter()
    record = _make_record("Authorization: Bearer abc123.tok-xyz_xx")
    assert f.filter(record) is True
    assert "abc123" not in record.msg
    assert "Bearer ***" in record.msg


def test_redact_password_urlencoded_in_msg() -> None:
    """LOG-02: ``password=...`` URL-encoded credentials redacted in record.msg."""
    f = RedactingFilter()
    record = _make_record("login form: username=u&password=secret123&grant_type=password")
    f.filter(record)
    assert "secret123" not in record.msg
    assert "password=***" in record.msg


def test_redact_password_json_in_msg() -> None:
    """LOG-02: JSON ``"password":"..."`` body redacted in record.msg."""
    f = RedactingFilter()
    record = _make_record('body={"username":"u","password":"super-s3cret"}')
    f.filter(record)
    assert "super-s3cret" not in record.msg
    assert '"password":"***"' in record.msg


def test_filter_always_returns_true() -> None:
    """LOG-02: filter never drops records — always returns True."""
    f = RedactingFilter()
    record = _make_record("nothing to redact here")
    assert f.filter(record) is True


def test_record_dict_scan_redacts_extra_field() -> None:
    """LOG-02: string values in record.__dict__ (extra={...}) get scrubbed."""
    f = RedactingFilter()
    record = _make_record("ok", extra={"weird_field": "Bearer leaky-token-xxx", "safe": "ok"})
    f.filter(record)
    assert record.__dict__["weird_field"] == "Bearer ***"
    assert record.__dict__["safe"] == "ok"


def test_redact_bearer_in_tuple_args() -> None:
    """LOG-02: tuple args with Bearer string scrubbed during interpolation."""
    f = RedactingFilter()
    record = _make_record("auth: %s", args=("Bearer xyz.tok",))
    f.filter(record)
    assert isinstance(record.args, tuple)
    assert record.args[0] == "Bearer ***"
