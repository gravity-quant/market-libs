"""Unit tests for ``ambito_financiero_client._logging.RedactingFilter`` + ``attach()``.

Phase 8 LOG-01/LOG-02 / D-10. Verifies redaction patterns, attach idempotency,
``record.__dict__`` scan coverage, and the always-True filter return contract.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import pytest

from ambito_financiero_client import _decode
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
    from ambito_financiero_client._logging import _MAX_SCAN_DEPTH

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
    from ambito_financiero_client._logging import _MAX_SCAN_ENTRIES

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


def test_marker_tuple_and_redaction_chain_are_untouched_by_phase_29() -> None:
    """D-05(b): the ámbito baseline pattern set is byte-unchanged.

    The filter fix is a scan-reach change only. Pattern isolation is a hard
    invariant: iol's OAuth shapes and higyrus's ``cuit`` / JSON-``token``
    shapes must never leak into this baseline.
    """
    from ambito_financiero_client import _logging

    assert _logging._REDACTION_MARKERS == (
        "Bearer ",
        "password=",
        '"password"',
    )
    assert not hasattr(_logging, "_REFRESH_TOKEN_URLENC_RE")
    assert not hasattr(_logging, "_REFRESH_TOKEN_JSON_RE")
    assert not hasattr(_logging, "_CUIT_QUERY_RE")


# ---------------------------------------------------------------------------
# Phase 29 D-05 — decoder-path caplog sentinel (T-29-36)
# ---------------------------------------------------------------------------

# A credential-shaped literal carrying NO redaction marker: the filter's
# marker-anchored regexes cannot rescue it (part (b) is deliberately
# unchanged), so its absence from the record is evidence about the RECORD
# CONTRACT — lock 1 / lock 11 — and not about the filter.
_SENTINEL = "s3cr3t-decode-sentinel-9f2c4b"


@dataclass(frozen=True, slots=True)
class _SentinelModel:
    """The ``from_api`` shape a typed ámbito surface would take.

    The walker copy is dormant in this paquete, so the sentinel has to build
    its own decode path. That is the point: the tripwire must fire against the
    SHIPPED ``_decode`` module, not a stand-in.
    """

    fecha: str
    ultimoPrecio: float

    @classmethod
    def from_api(cls, payload: object) -> _SentinelModel:
        """Decode ``payload``, reporting every divergence on the package logger."""
        return cls(**_decode.walk_model(cls, payload, policy=_decode.POLICY))


def test_decode_sentinel_never_leaks_credential(caplog: pytest.LogCaptureFixture) -> None:
    """T-29-36: no credential literal reaches ANY of the three record surfaces.

    Per-package tripwire for the record contract, riding the full CI matrix
    unlike the ``verification/`` copy which CI never runs.
    """
    payload: dict[str, object] = {
        # Wrong runtime type where a float is declared → a ``type`` divergence
        # whose observed value is the sentinel.
        "ultimoPrecio": _SENTINEL,
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
        with caplog.at_level(logging.DEBUG, logger="ambito_financiero_client"):
            obj = _SentinelModel.from_api(payload)
    finally:
        _decode.DECODE_SCOPE.set(previous_scope)

    # The decode really happened, really diverged, and really substituted.
    assert obj.ultimoPrecio == 0.0
    divergences = [r for r in caplog.records if r.getMessage() == "decode divergence"]
    assert len(divergences) >= 2

    for record in caplog.records:
        assert _SENTINEL not in record.getMessage()
        assert _SENTINEL not in str(record.args)
        for value in record.__dict__.values():
            if isinstance(value, str):
                assert _SENTINEL not in value
        assert _SENTINEL not in repr(record.__dict__)
