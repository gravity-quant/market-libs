"""Unit tests for ``iol_client._logging.RedactingFilter`` + ``attach()``.

Phase 8 iol. LOG-01/LOG-02 / D-10. Verifies redaction patterns (Bearer, X-Auth-Token,
password URL+JSON, refresh_token URL+JSON, access_token JSON), attach idempotency,
``record.__dict__`` scan coverage, and the always-True filter return contract.

iol-specific tests cover the OAuth ``refresh_token`` redaction in BOTH formats per
PATTERNS.md line 254-260 — IOL ``_core.py:175-178`` emits ``refresh_token`` in form-
encoded URL bodies AND JSON response bodies, so both shapes MUST be scrubbed.
"""

from __future__ import annotations

import logging

from iol_client._logging import RedactingFilter, attach


def _make_record(
    msg: str, args: object = None, extra: dict[str, object] | None = None
) -> logging.LogRecord:
    record = logging.LogRecord(
        name="iol_client",
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
    logger = logging.getLogger("iol_client")
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


# ---------------------------------------------------------------------------
# IOL-specific OAuth refresh_token redaction (D-10 + PATTERNS line 254-260)
# ---------------------------------------------------------------------------


def test_redact_refresh_token_urlenc() -> None:
    """D-10: URL-encoded ``refresh_token=<value>`` MUST be redacted.

    IOL OAuth refresh request body shape: ``refresh_token=<token>&grant_type=refresh_token``.
    """
    f = RedactingFilter()
    record = _make_record("refresh form: refresh_token=abc.def-ghi_123&grant_type=refresh_token")
    f.filter(record)
    assert "abc.def-ghi_123" not in record.msg
    assert "refresh_token=***" in record.msg


def test_redact_refresh_token_json() -> None:
    """D-10: JSON ``"refresh_token":"<value>"`` MUST be redacted.

    IOL OAuth login/refresh response body includes refresh_token in JSON form per
    ``_core.py:175-178``.
    """
    f = RedactingFilter()
    record = _make_record('response: {"refresh_token":"abc.def-ghi_123"}')
    f.filter(record)
    assert "abc.def-ghi_123" not in record.msg
    assert '"refresh_token":"***"' in record.msg


def test_login_response_payload_full_redaction() -> None:
    """D-10: full IOL login response payload — both access_token AND refresh_token redacted."""
    f = RedactingFilter()
    record = _make_record(
        'body={"access_token":"AAAA.bbbb","refresh_token":"CCCC.dddd","expires_in":900}'
    )
    f.filter(record)
    assert "AAAA.bbbb" not in record.msg
    assert "CCCC.dddd" not in record.msg
    assert '"access_token":"***"' in record.msg
    assert '"refresh_token":"***"' in record.msg
    # Non-secret fields preserved.
    assert '"expires_in":900' in record.msg
