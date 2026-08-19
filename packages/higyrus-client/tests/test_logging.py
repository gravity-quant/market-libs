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

import pytest

from higyrus_client import _decode
from higyrus_client._logging import RedactingFilter, attach
from higyrus_client.models import PosicionValuada


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


# ---------------------------------------------------------------------------
# Phase 29 D-05 part (a) — nested container scan, bounded per lock 12
# ---------------------------------------------------------------------------


def test_nested_container_string_leaf_redacted() -> None:
    """D-05(a): a marker-bearing string inside a dict ``extra`` value is redacted.

    Before the fix the ``record.__dict__`` scan inspected only values that were
    ALREADY strings, so this leaf shipped intact to every downstream handler.
    """
    f = RedactingFilter()
    record = _make_record(
        "ok",
        extra={"payload": {"headers": {"Authorization": "Bearer leaky-nested-tok"}, "n": 1}},
    )
    assert f.filter(record) is True
    payload = record.__dict__["payload"]
    assert payload["headers"]["Authorization"] == "Bearer ***"
    assert "leaky-nested-tok" not in repr(record.__dict__)
    # Keys and non-string values are untouched.
    assert set(payload) == {"headers", "n"}
    assert payload["n"] == 1


def test_nested_list_and_tuple_leaves_redacted() -> None:
    """D-05(a): list and tuple values are walked too, and keep their container type."""
    f = RedactingFilter()
    record = _make_record(
        "ok",
        extra={
            "as_list": ["safe", "Bearer list-tok", 7],
            "as_tuple": ("safe", 'body={"password":"s3cret"}'),
        },
    )
    assert f.filter(record) is True
    as_list = record.__dict__["as_list"]
    as_tuple = record.__dict__["as_tuple"]
    assert isinstance(as_list, list)
    assert isinstance(as_tuple, tuple)
    assert as_list == ["safe", "Bearer ***", 7]
    assert as_tuple == ("safe", 'body={"password":"***"}')
    assert "list-tok" not in repr(record.__dict__)
    assert "s3cret" not in repr(record.__dict__)


def test_untouched_containers_keep_object_identity() -> None:
    """A record whose extras carry no marker keeps the caller's objects as-is."""
    f = RedactingFilter()
    original = {"a": ["plain", "values"], "b": 3}
    record = _make_record("ok", extra={"payload": original})
    assert f.filter(record) is True
    assert record.__dict__["payload"] is original


def test_recursion_depth_bounded() -> None:
    """Lock 12: beyond ``_MAX_SCAN_DEPTH`` a container is left untouched."""
    from higyrus_client._logging import _MAX_SCAN_DEPTH

    assert _MAX_SCAN_DEPTH == 4

    f = RedactingFilter()
    record = _make_record(
        "ok",
        extra={
            # Container at depth 4 → NOT walked; its leaf survives.
            "too_deep": {"l1": {"l2": {"l3": {"l4": {"l5": "Bearer beyond-the-bound"}}}}},
            # Leaf at depth 3 → within the bound and redacted.
            "within": {"a": {"b": {"c": "Bearer within-the-bound"}}},
        },
    )
    assert f.filter(record) is True
    too_deep = record.__dict__["too_deep"]
    assert too_deep["l1"]["l2"]["l3"]["l4"]["l5"] == "Bearer beyond-the-bound"
    assert record.__dict__["within"]["a"]["b"]["c"] == "Bearer ***"


def test_wide_container_skipped() -> None:
    """Lock 12: a container with more than ``_MAX_SCAN_ENTRIES`` entries is skipped."""
    from higyrus_client._logging import _MAX_SCAN_ENTRIES

    assert _MAX_SCAN_ENTRIES == 64

    f = RedactingFilter()
    wide = {f"k{i}": "Bearer wide-tok" for i in range(_MAX_SCAN_ENTRIES + 1)}
    at_bound = {f"k{i}": "Bearer bound-tok" for i in range(_MAX_SCAN_ENTRIES)}
    record = _make_record("ok", extra={"wide": wide, "at_bound": at_bound})
    assert f.filter(record) is True
    # Over the cap: skipped wholesale, values intact.
    assert record.__dict__["wide"]["k0"] == "Bearer wide-tok"
    # Exactly at the cap: still walked.
    assert record.__dict__["at_bound"]["k0"] == "Bearer ***"


# ---------------------------------------------------------------------------
# Phase 29 D-05 — decoder-path caplog sentinel (T-29-14)
# ---------------------------------------------------------------------------

# A credential-shaped literal carrying NO redaction marker: the filter's
# marker-anchored regexes cannot rescue it (part (b) is deliberately
# unchanged), so its absence from the record is evidence about the RECORD
# CONTRACT — lock 1 / lock 11 — and not about the filter.
_SENTINEL = "s3cr3t-decode-sentinel-9f2c4b"


def test_decode_sentinel_never_leaks_credential(caplog: pytest.LogCaptureFixture) -> None:
    """T-29-14: no credential literal reaches ANY of the three record surfaces.

    In-package relocation of the SEC-01 pattern from
    ``verification/test_logging_no_token_leak.py``: that file lives under
    ``verification/``, which CI never executes because the tests job passes an
    explicit package path that overrides ``testpaths``. This copy rides the
    full CI matrix.
    """
    payload: dict[str, object] = {
        # Wrong runtime type where a float is declared → a ``type`` divergence
        # whose observed value is the sentinel.
        "precio": _SENTINEL,
        # An undeclared wire key whose value is the sentinel → an ``extra``
        # divergence; the key name itself is reported, the value never is.
        "vendorSecret": _SENTINEL,
    }

    previous_scope = _decode.DECODE_SCOPE.get()
    caplog.clear()
    try:
        # Fresh scope so the dedupe set cannot swallow the records and make
        # this assertion vacuously true.
        _decode.open_request_scope()
        with caplog.at_level(logging.DEBUG, logger="higyrus_client"):
            obj = PosicionValuada.from_api(payload)
    finally:
        _decode.DECODE_SCOPE.set(previous_scope)

    # The decode really happened, really diverged, and really substituted.
    assert obj.precio == 0.0
    divergences = [r for r in caplog.records if r.getMessage() == "decode divergence"]
    assert len(divergences) >= 2

    for record in caplog.records:
        assert _SENTINEL not in record.getMessage()
        assert _SENTINEL not in str(record.args)
        for value in record.__dict__.values():
            if isinstance(value, str):
                assert _SENTINEL not in value
        assert _SENTINEL not in repr(record.__dict__)
