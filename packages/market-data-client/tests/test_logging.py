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

import pytest

from market_data_client import _decode
from market_data_client._logging import RedactingFilter, attach
from market_data_client.models import Instrument


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
    rec_extra = _make_record("ok", extra={"weird": "client_secret=leaky-xxx", "safe": "ok"})
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
            "as_tuple": ("safe", 'body={"client_secret":"sup3r-s3cret"}'),
        },
    )
    assert f.filter(record) is True
    as_list = record.__dict__["as_list"]
    as_tuple = record.__dict__["as_tuple"]
    assert isinstance(as_list, list)
    assert isinstance(as_tuple, tuple)
    assert as_list == ["safe", "Bearer ***", 7]
    assert as_tuple == ("safe", 'body={"client_secret":"***"}')
    assert "list-tok" not in repr(record.__dict__)
    assert "sup3r-s3cret" not in repr(record.__dict__)


def test_untouched_containers_keep_object_identity() -> None:
    """A record whose extras carry no marker keeps the caller's objects as-is."""
    f = RedactingFilter()
    original = {"a": ["plain", "values"], "b": 3}
    record = _make_record("ok", extra={"payload": original})
    assert f.filter(record) is True
    assert record.__dict__["payload"] is original


def test_recursion_depth_bounded() -> None:
    """Lock 12: beyond ``_MAX_SCAN_DEPTH`` a container is left untouched."""
    from market_data_client._logging import _MAX_SCAN_DEPTH

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
    from market_data_client._logging import _MAX_SCAN_ENTRIES

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
# Phase 29 D-05 — decoder-path caplog sentinel (T-29-22)
# ---------------------------------------------------------------------------

# A credential-shaped literal carrying NO redaction marker: market-data's
# marker-anchored regexes (``Bearer ``, ``client_secret=``, ``"client_secret"``,
# ``"access_token"``) cannot rescue it, because part (b) of D-05 is deliberately
# unchanged. Its absence from the record is therefore evidence about the RECORD
# CONTRACT — lock 1 / lock 11 — and not about the filter. A marker-bearing
# sentinel would silently turn this into a test of ``_redact``.
_SENTINEL = "s3cr3t-decode-sentinel-9f2c4b"


def test_decode_sentinel_never_leaks_credential(caplog: pytest.LogCaptureFixture) -> None:
    """T-29-22: no credential literal reaches ANY of the three record surfaces.

    In-package relocation of the SEC-01 pattern from
    ``verification/test_logging_no_token_leak.py``: that file lives under
    ``verification/``, which CI never executes because the tests job passes an
    explicit package path that overrides ``testpaths``. This copy rides the full
    CI matrix, on the market-data decoder path specifically — the package whose
    payloads carry symbol and account identifiers.
    """
    payload: dict[str, object] = {
        # Wrong runtime type where a bool is declared → a ``type`` divergence
        # whose observed VALUE is the sentinel.
        "expired": _SENTINEL,
        # An undeclared wire key whose value is the sentinel → an ``extra``
        # divergence; the key NAME is reported, the value never is.
        "vendorSecret": _SENTINEL,
    }

    previous_scope = _decode.DECODE_SCOPE.get()
    caplog.clear()
    try:
        # Fresh scope so the dedupe set cannot swallow the records and make this
        # assertion vacuously true.
        _decode.open_request_scope()
        with caplog.at_level(logging.DEBUG, logger="market_data_client"):
            obj = Instrument.from_api(payload)
    finally:
        _decode.DECODE_SCOPE.set(previous_scope)

    # The decode really happened, really diverged, and really substituted.
    assert obj.expired is False
    divergences = [r for r in caplog.records if r.getMessage() == "decode divergence"]
    assert len(divergences) >= 2

    for record in caplog.records:
        assert _SENTINEL not in record.getMessage()
        assert _SENTINEL not in str(record.args)
        for value in record.__dict__.values():
            if isinstance(value, str):
                assert _SENTINEL not in value
        assert _SENTINEL not in repr(record.__dict__)
