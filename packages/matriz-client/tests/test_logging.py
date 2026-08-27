"""Unit tests for ``matriz_client._logging.RedactingFilter`` + ``attach()``.

Phase 8 matriz Plan 5. LOG-01/LOG-02/LOG-03 / D-22. Verifies redaction
patterns (Bearer, X-Auth-Token, X-Password, Authorization Basic, JSON
password, URL password), attach idempotency, ``record.__dict__`` scan
coverage, the D-22 ``auth_basic`` tuple splitting, and the always-True filter
return contract.

matriz-specific tests cover (per PATTERNS.md line 260 + D-22):

- ``X-Auth-Token`` header — Primary API token header.
- ``X-Password`` header — login credential header.
- ``Authorization: Basic <base64>`` header — Risk API §9 (D-22).
- ``auth_basic`` tuple in extras — D-22 tuple splitting.
- ``X-Username`` — INTENTIONALLY preserved (operational, NOT secret).
"""

from __future__ import annotations

import logging

import pytest

from matriz_client import _decode
from matriz_client._logging import RedactingFilter, attach
from matriz_client.models import InstrumentDetail


def _make_record(
    msg: str, args: object = None, extra: dict[str, object] | None = None
) -> logging.LogRecord:
    record = logging.LogRecord(
        name="matriz_client",
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
    logger = logging.getLogger("matriz_client")
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
# matriz-specific patterns (D-22 + PATTERNS line 260)
# ---------------------------------------------------------------------------


def test_redact_x_auth_token_header() -> None:
    """matriz Primary: ``X-Auth-Token: <token>`` MUST be redacted.

    The token is set by ``parse_login_response`` from the ``X-Auth-Token``
    response header. If a caller enables DEBUG-level logs on the package
    logger, the header could end up in a request-formatting record before
    the structured token field is surfaced.
    """
    f = RedactingFilter()
    record = _make_record("X-Auth-Token: abc.def-ghi_123-base64=")
    f.filter(record)
    assert "abc.def-ghi_123" not in record.msg
    assert "X-Auth-Token: ***" in record.msg


def test_redact_x_password_header_preserves_x_username() -> None:
    """D-22: X-Password redacted; X-Username PRESERVED (operational, NOT secret).

    matriz login per ``_core.py:255-262`` sends both ``X-Username`` and
    ``X-Password`` headers. The D-22 split: only the password is secret.
    """
    f = RedactingFilter()
    record = _make_record("headers: X-Username: admin\nX-Password: super-s3cret\n")
    f.filter(record)
    assert "super-s3cret" not in record.msg
    assert "X-Password: ***" in record.msg
    # X-Username intentionally preserved.
    assert "X-Username: admin" in record.msg


def test_redact_authorization_basic_header() -> None:
    """D-22: ``Authorization: Basic <base64>`` MUST be redacted.

    matriz Risk API §9 (per ``_core.py`` ``build_get_positions_request`` /
    ``build_get_detailed_positions_request`` / ``build_get_account_report_request``)
    uses HTTP Basic Auth — when ``auth=httpx.BasicAuth(*spec.auth_basic)`` runs,
    the resulting header lands as ``Authorization: Basic <base64>``. We must
    not let it leak into log records.
    """
    f = RedactingFilter()
    record = _make_record("Authorization: Basic YWRtaW46c2VjcmV0")
    f.filter(record)
    assert "YWRtaW46c2VjcmV0" not in record.msg
    assert "Authorization: Basic ***" in record.msg


def test_redact_auth_basic_tuple_in_extra() -> None:
    """D-22 CRITICAL: ``auth_basic`` tuple in record.__dict__ MUST be split.

    The shell ``_request()`` propagates ``spec.auth_basic`` as
    ``request.extensions["auth_basic"]`` and the transport's structured log
    record might carry it as an extra field. The filter MUST:
      1. Detect the tuple
      2. Split into ``auth_basic_user`` (preserved) + ``auth_basic_password='***'``
      3. Remove the original ``auth_basic`` key so the tuple form NEVER reaches
         downstream handlers.
    """
    f = RedactingFilter()
    record = _make_record("risk call", extra={"auth_basic": ("operator-1", "super-secret-pw")})
    f.filter(record)
    # Original `auth_basic` key removed.
    assert "auth_basic" not in record.__dict__
    # Split keys present.
    assert record.__dict__["auth_basic_user"] == "operator-1"
    assert record.__dict__["auth_basic_password"] == "***"


def test_redact_auth_basic_tuple_malformed_does_not_crash() -> None:
    """Defensive: a malformed ``auth_basic`` never crashes the filter — and never leaks.

    Phase 29 code review, WR-05. The filter used to leave a malformed value
    untouched on the theory that "the generic scan will still redact string
    credentials by substring match". It will not: ``_redact_nested`` only
    rewrites string leaves that already contain a redaction marker
    (``Bearer ``, ``Authorization: Basic``, ...), and a bare password contains
    none — so ``auth_basic=["user", "pw"]``, a 3-tuple, or a ``bytes`` password
    shipped the secret to every downstream handler. The filter now fails CLOSED:
    a value that cannot be split is redacted wholesale.
    """
    f = RedactingFilter()
    record = _make_record("risk call", extra={"auth_basic": "not-a-tuple"})
    # Should NOT raise, and MUST NOT survive as the caller supplied it.
    f.filter(record)
    assert record.__dict__.get("auth_basic") == "***"

    # Tuple of wrong arity — also tolerated, also redacted wholesale.
    record2 = _make_record("risk call", extra={"auth_basic": ("only-one-field",)})
    f.filter(record2)
    assert record2.__dict__.get("auth_basic") == "***"


def test_account_id_not_redacted() -> None:
    """D-11 sanity: account_id is operational metadata, NOT PII — MUST survive.

    The RedactingFilter scrubs secrets (token/password/auth_basic) but NOT
    account identifiers. account_id appears in ``extra={...}`` fields as a
    structured log surface for correlation; redacting it would defeat the
    purpose of D-09's conditional field set.
    """
    f = RedactingFilter()
    record = _make_record("processing request", extra={"account_id": "ACC-MATZ-1"})
    f.filter(record)
    assert record.__dict__["account_id"] == "ACC-MATZ-1"


def test_no_higyrus_or_iol_patterns_present() -> None:
    """Pattern isolation: matriz filter MUST NOT carry higyrus/iol-specific shapes.

    - No ``_TOKEN_JSON_RE`` (higyrus login response shape).
    - No ``_CUIT_QUERY_RE`` (higyrus URL query PII).
    - No ``_REFRESH_TOKEN_*`` (iol OAuth refresh).

    Guards against accidental cross-package coupling.
    """
    from matriz_client import _logging

    assert not hasattr(_logging, "_TOKEN_JSON_RE")
    assert not hasattr(_logging, "_CUIT_QUERY_RE")
    assert not hasattr(_logging, "_REFRESH_TOKEN_URLENC_RE")
    assert not hasattr(_logging, "_REFRESH_TOKEN_JSON_RE")


# ---------------------------------------------------------------------------
# Phase 29 D-05 part (a) — bounded recursive ``record.__dict__`` scan
# ---------------------------------------------------------------------------


def test_nested_container_string_leaf_redacted() -> None:
    """D-05(a): a marker-bearing string inside a dict ``extra`` value is redacted.

    Before the fix the ``record.__dict__`` scan inspected only values that were
    ALREADY strings, so this leaf shipped intact to every downstream handler.
    """
    f = RedactingFilter()
    record = _make_record(
        "ok",
        extra={"payload": {"headers": {"auth": "X-Auth-Token: leaky.nested-tok"}, "n": 1}},
    )
    assert f.filter(record) is True
    payload = record.__dict__["payload"]
    assert payload["headers"]["auth"] == "X-Auth-Token: ***"
    assert "leaky.nested-tok" not in repr(record.__dict__)
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
    from matriz_client._logging import _MAX_SCAN_DEPTH

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
    from matriz_client._logging import _MAX_SCAN_ENTRIES

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
# Phase 29 — the D-22 pre-scan ordering invariant (T-29-30)
# ---------------------------------------------------------------------------


def test_auth_basic_pre_scan_runs_before_the_generic_scan() -> None:
    """T-29-30: both redactions happen in ONE filter pass, pre-scan first.

    The pre-scan splits a credential-bearing ``(user, password)`` TUPLE into
    two string fields; the generic scan only ever redacts string leaves. If the
    generic scan ran first, the tuple would still be a tuple when it was
    reached, survive untouched, and ship the password to every downstream
    handler. This test drives one record carrying BOTH shapes and asserts both
    are handled by a single ``filter()`` call.
    """
    f = RedactingFilter()
    record = _make_record(
        "risk call",
        extra={
            # Handled by the D-22 pre-scan only.
            "auth_basic": ("operator-1", "super-secret-pw"),
            # Handled by the generic recursive scan only (nested string leaf).
            "req": {"headers": {"raw": "Authorization: Basic YWRtaW46c2VjcmV0"}},
        },
    )
    assert f.filter(record) is True

    # Pre-scan: the tuple field is GONE, replaced by the split pair.
    assert "auth_basic" not in record.__dict__
    assert record.__dict__["auth_basic_user"] == "operator-1"
    assert record.__dict__["auth_basic_password"] == "***"
    # Generic scan: the nested header leaf is redacted.
    assert record.__dict__["req"]["headers"]["raw"] == "Authorization: Basic ***"
    # Neither secret survives anywhere on the record.
    assert "super-secret-pw" not in repr(record.__dict__)
    assert "YWRtaW46c2VjcmV0" not in repr(record.__dict__)


def test_pre_scan_block_precedes_the_generic_scan_in_source() -> None:
    """The ordering invariant, asserted on the source line numbers themselves."""
    import pathlib

    from matriz_client import _logging

    lines = pathlib.Path(_logging.__file__).read_text(encoding="utf-8").splitlines()
    pre_scan = next(i for i, line in enumerate(lines) if '"auth_basic" in record.__dict__' in line)
    generic = next(i for i, line in enumerate(lines) if "_scan_record_dict(record)" in line)
    assert pre_scan < generic
    # The hashed region (Plan 09) is delimited exactly once each way, and the
    # package-specific pre-scan sits legitimately OUTSIDE it.
    begins = [i for i, line in enumerate(lines) if "decode-intactness: generic-scan begin" in line]
    ends = [i for i, line in enumerate(lines) if "decode-intactness: generic-scan end" in line]
    assert len(begins) == 1
    assert len(ends) == 1
    assert not begins[0] < pre_scan < ends[0]


# ---------------------------------------------------------------------------
# Phase 29 D-05 — decoder-path caplog sentinel (T-29-29)
# ---------------------------------------------------------------------------

# A credential-shaped literal carrying NO redaction marker: the filter's
# marker-anchored regexes cannot rescue it (part (b) is deliberately
# unchanged), so its absence from the record is evidence about the RECORD
# CONTRACT — lock 1 / lock 11 — and not about the filter.
_SENTINEL = "s3cr3t-decode-sentinel-9f2c4b"


def test_decode_sentinel_never_leaks_credential(caplog: pytest.LogCaptureFixture) -> None:
    """T-29-29: no credential literal reaches ANY of the three record surfaces.

    In-package relocation of the SEC-01 pattern from
    ``verification/test_logging_no_token_leak.py``: that file lives under
    ``verification/``, which CI never executes because the tests job passes an
    explicit package path that overrides ``testpaths``. This copy rides the
    full CI matrix.
    """
    payload: dict[str, object] = {
        # Wrong runtime type where a ``dict`` is declared → a ``type``
        # divergence whose observed value is the sentinel.
        "tickPriceRanges": _SENTINEL,
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
        with caplog.at_level(logging.DEBUG, logger="matriz_client"):
            obj = InstrumentDetail.from_api(payload)
    finally:
        _decode.DECODE_SCOPE.set(previous_scope)

    # The decode really happened, really diverged, and really substituted.
    assert obj.tickPriceRanges == {}
    divergences = [r for r in caplog.records if r.getMessage() == "decode divergence"]
    assert len(divergences) >= 2

    for record in caplog.records:
        assert _SENTINEL not in record.getMessage()
        assert _SENTINEL not in str(record.args)
        for value in record.__dict__.values():
            if isinstance(value, str):
                assert _SENTINEL not in value
        assert _SENTINEL not in repr(record.__dict__)


# ---------------------------------------------------------------------------
# Phase 29 code review, WR-05 — the auth_basic pre-scan fails CLOSED
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [
        ["operator-1", "super-secret-pw"],  # a list, not a tuple
        ("operator-1", "super-secret-pw", "extra"),  # wrong arity
        ("operator-1", b"super-secret-pw"),  # bytes password
        {"user": "operator-1", "password": "super-secret-pw"},  # a mapping
        b"operator-1:super-secret-pw",  # raw bytes
    ],
    ids=["list", "arity", "bytes-member", "mapping", "bytes"],
)
def test_malformed_auth_basic_never_ships_the_secret(value: object) -> None:
    """WR-05: every shape ``_redact_auth_basic_tuple`` cannot split is redacted."""
    record = _make_record("risk call", extra={"auth_basic": value})
    RedactingFilter().filter(record)

    assert record.__dict__.get("auth_basic") == "***"
    assert "super-secret-pw" not in repr(record.__dict__)
    assert b"super-secret-pw" not in repr(record.__dict__).encode()
