"""Unit tests for ``higyrus_client._logging.RedactingFilter`` + ``attach()``.

Phase 8 higyrus. LOG-01/LOG-02/LOG-03 / D-10 / D-11. Verifies redaction
patterns (Bearer, X-Auth-Token, password URL+JSON, token JSON, cuit query),
attach idempotency, ``record.__dict__`` scan coverage, and the always-True
filter return contract.

higyrus-specific tests cover (per PATTERNS.md line 254-260):

- JSON ``"password":"..."`` — Higyrus login request body (``_core.py:189-197``).
- JSON ``"token":"..."`` — Higyrus login response body (``_core.py:200-223``).
- URL query ``cuit=<digits>`` — Argentine tax ID PII redaction.

D-11 sanity: account_id (operational metadata, NOT PII) is NOT redacted by the
filter — it must survive intact in ``extra={...}`` fields.
"""

from __future__ import annotations

import logging

from higyrus_client._logging import RedactingFilter, attach


def _make_record(
    msg: str, args: object = None, extra: dict[str, object] | None = None
) -> logging.LogRecord:
    record = logging.LogRecord(
        name="higyrus_client",
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
    logger = logging.getLogger("higyrus_client")
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
# higyrus-specific patterns (D-10 + PATTERNS line 254-260)
# ---------------------------------------------------------------------------


def test_redact_password_json_login_body() -> None:
    """D-10: JSON ``"password":"..."`` (Higyrus login body) MUST be redacted.

    Higyrus login request body shape per ``_core.build_login_request``:
    ``{"clientId":..., "username":..., "password":"<secret>"}``.
    """
    f = RedactingFilter()
    record = _make_record('body={"clientId":"tenant","username":"u","password":"super-s3cret"}')
    f.filter(record)
    assert "super-s3cret" not in record.msg
    assert '"password":"***"' in record.msg


def test_redact_token_json_login_response() -> None:
    """D-10: JSON ``"token":"..."`` (Higyrus login response) MUST be redacted.

    Higyrus login response payload per ``_core.parse_login_response``:
    ``{"token":"<jwt-like>"}``. If a caller enables DEBUG-level logs, the
    response body could end up in a record before the structured token field
    is surfaced.
    """
    f = RedactingFilter()
    record = _make_record('response: {"token":"abc.def.ghi","sessionId":"X"}')
    f.filter(record)
    assert "abc.def.ghi" not in record.msg
    assert '"token":"***"' in record.msg
    # Non-secret fields preserved.
    assert '"sessionId":"X"' in record.msg


def test_redact_cuit_query() -> None:
    """D-10 + PATTERNS line 259: URL query ``cuit=<digits>`` (PII) MUST be redacted.

    Argentine tax ID — operational PII present in some Higyrus URL shapes.
    Defensive redaction beyond the locked roadmap.
    """
    f = RedactingFilter()
    record = _make_record("GET /api/cuentas?cuit=20123456789&page=1")
    f.filter(record)
    assert "20123456789" not in record.msg
    assert "cuit=***" in record.msg
    # Adjacent params preserved.
    assert "page=1" in record.msg


def test_full_login_payload_full_redaction() -> None:
    """D-10: full Higyrus login request+response cycle — both password AND token redacted."""
    f = RedactingFilter()
    record_req = _make_record(
        'login req: {"clientId":"tenant","username":"u","password":"P@SS!w0rd"}'
    )
    record_resp = _make_record('login resp: {"token":"JWT.HEADER.PAYLOAD","status":"OK"}')
    f.filter(record_req)
    f.filter(record_resp)
    assert "P@SS!w0rd" not in record_req.msg
    assert "JWT.HEADER.PAYLOAD" not in record_resp.msg
    assert '"password":"***"' in record_req.msg
    assert '"token":"***"' in record_resp.msg
    # Non-secret structural keys preserved.
    assert '"clientId":"tenant"' in record_req.msg
    assert '"status":"OK"' in record_resp.msg


def test_account_id_not_redacted() -> None:
    """D-11 sanity: account_id is operational metadata, NOT PII — MUST survive.

    The RedactingFilter scrubs PII (cuit) and secrets (token/password) but NOT
    account identifiers. account_id appears in ``extra={...}`` fields as a
    structured log surface for correlation; redacting it would defeat the
    purpose of D-09's conditional field set.
    """
    f = RedactingFilter()
    record = _make_record("processing request", extra={"account_id": "ACC-123"})
    f.filter(record)
    assert record.__dict__["account_id"] == "ACC-123"


def test_no_refresh_token_pattern_present() -> None:
    """D-10 pattern isolation: higyrus filter MUST NOT carry iol-specific OAuth shapes.

    iol's ``_REFRESH_TOKEN_*`` regexes are deliberately absent from the higyrus
    filter — Higyrus uses single-Bearer auth without OAuth refresh, so the
    pattern would never match in practice. This test guards against accidental
    cross-package coupling (someone copy-pasting the iol patterns wholesale).
    """
    from higyrus_client import _logging

    assert not hasattr(_logging, "_REFRESH_TOKEN_URLENC_RE")
    assert not hasattr(_logging, "_REFRESH_TOKEN_JSON_RE")
