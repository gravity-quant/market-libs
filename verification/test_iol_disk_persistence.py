"""Cross-cutting IOL refresh_token disk-persistence verification suite (SEC-01).

Phase 14 D-P1 / D-P2 — tests-first, RED in HEAD. These 11 tests (3 CRITICAL merge
gates + 8 BUG-03 x {sync, async} regression tests) define the contract that Plans
2-3 must satisfy. They are committed RED so that bisect/forensics has a clear
failure signal if a later plan breaks the contract (Phase 8 D-21 / Phase 13 D-P1
tests-first carry-forward).

**Tests are RED in HEAD pending Plans 2-3 implementation.** The
``iol_client._token_cache`` module and the ``Client(token_cache_path=...)`` /
``aio.AsyncClient(token_cache_path=...)`` kwargs DO NOT EXIST YET. Every test in
this file fails at RUN time with ``AttributeError`` (``module 'iol_client' has no
attribute '_token_cache'``), ``ModuleNotFoundError``, or ``TypeError``
(``unexpected keyword argument 'token_cache_path'``). Collection MUST still
succeed — the module-level ``import iol_client`` is safe and ``_token_cache`` is
referenced only inside test bodies as ``iol_client._token_cache`` so the failure
surfaces at TEST execution, not at collection.

The 3 CRITICAL merge gates map to anti-Pitfalls 7/8/9 (PITFALLS.md):

- ``test_disk_persistence_never_logs_token`` — anti-Pitfall 7: the SENTINEL must
  NEVER appear in any log record's ``message``, ``args``, or ``repr(extra)``.
- ``test_disk_token_write_under_concurrent_processes`` — anti-Pitfall 9: 20
  concurrent writer threads via ``fcntl.flock``; final file has exactly one valid
  token, byte-identical to its parsed roundtrip.
- ``test_disk_token_deleted_on_refresh_401`` — anti-Pitfall 8: stale disk token
  deleted before password fallback; disk ends with the FRESH token.

The 8 regression tests cover the 4 v1.1 BUG-03 in-instance lifecycle paths
(loaded-on-init, written-after-refresh, preserved-on-omit, rotated-on-provide)
x {sync, async} x disk.

Logger namespace ``iol_client`` is set at DEBUG so ``iol_client._token_cache``
(the Plan 2 module logger) is captured by descendant inheritance.
"""

from __future__ import annotations

import json
import logging
import secrets
from concurrent.futures import ThreadPoolExecutor

import pytest

import iol_client

SENTINEL = "REFRESH-TOKEN-SENTINEL-DO-NOT-LEAK-9876543210"


# ----------------------------------------------------------------------
# CRITICAL merge gate 1 — anti-Pitfall 7 (caplog no-leak)
# ----------------------------------------------------------------------


def test_disk_persistence_never_logs_token(tmp_path, caplog, httpx_mock):
    """Anti-Pitfall 7 — token leak via new disk-persistence log sites.

    Exercises write-on-rotate → read-on-init → write-fail OSError → corrupt-file
    read paths with caplog DEBUG. The sentinel MUST NEVER appear in any log
    record's message, args, or repr(extra).
    """
    caplog.set_level(logging.DEBUG, logger="iol_client")
    path = tmp_path / "refresh_token.json"

    # 1. write-on-rotate
    iol_client._token_cache.save(path, SENTINEL, acquired_at=1718450000.0)

    # 2. read-on-init
    loaded = iol_client._token_cache.load(path)
    assert loaded["refresh_token"] == SENTINEL

    # 3. write-fail OSError (parent dir made read-only)
    ro_dir = tmp_path / "ro"
    ro_dir.mkdir()
    ro_dir.chmod(0o500)
    try:
        iol_client._token_cache.save(ro_dir / "rt.json", SENTINEL, acquired_at=1.0)
    except OSError:
        pass  # expected
    finally:
        ro_dir.chmod(0o700)  # cleanup so pytest can delete tmp

    # 4. corrupt-file read
    path.write_text('{"version": 1, "refresh_token":')  # JSON inválido
    result = iol_client._token_cache.load(path)
    assert result is None

    # SENTINEL must not appear ANYWHERE
    for record in caplog.records:
        assert SENTINEL not in record.getMessage()
        assert SENTINEL not in repr(record.args or ())
        for v in record.__dict__.values():
            if isinstance(v, str):
                assert SENTINEL not in v


# ----------------------------------------------------------------------
# CRITICAL merge gate 2 — anti-Pitfall 9 (multi-process race)
# ----------------------------------------------------------------------


def test_disk_token_write_under_concurrent_processes(tmp_path):
    """Anti-Pitfall 9 — 20 concurrent threads each write via fcntl.flock.

    The final file must contain EXACTLY one valid token (no interleaving,
    no truncation, no double-write corruption).
    """
    path = tmp_path / "refresh_token.json"
    tokens = [f"token-{i:02d}-{secrets.token_hex(8)}" for i in range(20)]

    with ThreadPoolExecutor(max_workers=20) as ex:
        futures = [
            ex.submit(iol_client._token_cache.save, path, t, acquired_at=float(i))
            for i, t in enumerate(tokens)
        ]
        for f in futures:
            f.result()  # propagate exceptions

    loaded = iol_client._token_cache.load(path)
    assert loaded is not None
    assert loaded["version"] == 1
    assert loaded["refresh_token"] in tokens  # exactly one winner
    # Verify file integrity: no extra bytes, no truncation
    raw = path.read_bytes()
    assert raw == json.dumps(loaded).encode("utf-8")


# ----------------------------------------------------------------------
# CRITICAL merge gate 3 — anti-Pitfall 8 (failed-refresh cleanup)
# ----------------------------------------------------------------------


def test_disk_token_deleted_on_refresh_401(tmp_path, monkeypatch, httpx_mock):
    """Anti-Pitfall 8 — stale token deleted before password fallback.

    Seeds disk with STALE-REFRESH-TOKEN. IOL returns 401 on refresh. Client
    MUST delete the stale token from disk, do password grant, write FRESH
    token to disk.
    """
    monkeypatch.setenv("CI", "false")
    path = tmp_path / "refresh_token.json"
    iol_client._token_cache.save(path, "STALE-REFRESH-TOKEN", acquired_at=1.0)

    # Mock IOL: refresh 401, password grant success
    httpx_mock.add_response(
        url="https://api.invertironline.com/token",
        method="POST",
        status_code=401,
        match_content=b"grant_type=refresh_token",
    )
    httpx_mock.add_response(
        url="https://api.invertironline.com/token",
        method="POST",
        json={
            "access_token": "fresh-access",
            "refresh_token": "FRESH-REFRESH-TOKEN",
            "expires_in": 900,
        },
        match_content=b"grant_type=password",
    )

    client = iol_client.Client(
        base_url="https://api.invertironline.com",
        username="u",
        password="p",
        token_cache_path=path,
    )
    client._ensure_token()  # triggers refresh → 401 → cleanup → password

    loaded = iol_client._token_cache.load(path)
    assert loaded is not None
    assert loaded["refresh_token"] == "FRESH-REFRESH-TOKEN"
    assert loaded["refresh_token"] != "STALE-REFRESH-TOKEN"


# ----------------------------------------------------------------------
# Regression — BUG-03 path 1: loaded-on-init skips password grant
# ----------------------------------------------------------------------


def test_disk_token_loaded_on_init_skips_password_sync(tmp_path, monkeypatch, httpx_mock):
    """BUG-03 x disk (sync): a valid disk refresh_token takes the refresh path.

    Seed disk with a valid refresh_token, mock IOL to return 200 on
    ``grant_type=refresh_token``, assert NO ``grant_type=password`` request was
    issued (the disk token short-circuited the password grant).
    """
    monkeypatch.setenv("CI", "false")
    path = tmp_path / "refresh_token.json"
    iol_client._token_cache.save(path, "SEED-REFRESH-TOKEN", acquired_at=1.0)

    httpx_mock.add_response(
        url="https://api.invertironline.com/token",
        method="POST",
        json={
            "access_token": "acc",
            "refresh_token": "ROTATED-REFRESH-TOKEN",
            "expires_in": 900,
        },
        match_content=b"grant_type=refresh_token",
    )

    client = iol_client.Client(
        base_url="https://api.invertironline.com",
        username="u",
        password="p",
        token_cache_path=path,
    )
    client._ensure_token()

    requests = httpx_mock.get_requests()
    assert not any(b"grant_type=password" in (r.content or b"") for r in requests)
    assert any(b"grant_type=refresh_token" in (r.content or b"") for r in requests)


@pytest.mark.asyncio
async def test_disk_token_loaded_on_init_skips_password_async(tmp_path, monkeypatch, httpx_mock):
    """BUG-03 x disk (async): mirror of the sync loaded-on-init test."""
    from iol_client import aio

    monkeypatch.setenv("CI", "false")
    path = tmp_path / "refresh_token.json"
    iol_client._token_cache.save(path, "SEED-REFRESH-TOKEN", acquired_at=1.0)

    httpx_mock.add_response(
        url="https://api.invertironline.com/token",
        method="POST",
        json={
            "access_token": "acc",
            "refresh_token": "ROTATED-REFRESH-TOKEN",
            "expires_in": 900,
        },
        match_content=b"grant_type=refresh_token",
    )

    client = aio.AsyncClient(
        base_url="https://api.invertironline.com",
        username="u",
        password="p",
        token_cache_path=path,
    )
    await client._aensure_token()
    await client.aclose()

    requests = httpx_mock.get_requests()
    assert not any(b"grant_type=password" in (r.content or b"") for r in requests)
    assert any(b"grant_type=refresh_token" in (r.content or b"") for r in requests)


# ----------------------------------------------------------------------
# Regression — BUG-03 path 2: written-after-successful-refresh
# ----------------------------------------------------------------------


def test_disk_token_written_after_successful_refresh_sync(tmp_path, monkeypatch, httpx_mock):
    """BUG-03 x disk (sync): a successful refresh writes the FRESH token to disk.

    Construct a Client seeded with an in-memory refresh_token (no disk seed),
    mock IOL refresh returning a rotated token, assert the disk file now holds
    the FRESH token with a valid JSON shape and a recent ``acquired_at``.
    """
    import time

    monkeypatch.setenv("CI", "false")
    path = tmp_path / "refresh_token.json"

    httpx_mock.add_response(
        url="https://api.invertironline.com/token",
        method="POST",
        json={
            "access_token": "acc",
            "refresh_token": "FRESH-REFRESH-TOKEN",
            "expires_in": 900,
        },
        match_content=b"grant_type=refresh_token",
    )

    before = time.time()
    client = iol_client.Client(
        base_url="https://api.invertironline.com",
        username="u",
        password="p",
        refresh_token="SEED-REFRESH-TOKEN",
        token_cache_path=path,
    )
    client._ensure_token()
    after = time.time()

    loaded = iol_client._token_cache.load(path)
    assert loaded is not None
    assert loaded["version"] == 1
    assert loaded["refresh_token"] == "FRESH-REFRESH-TOKEN"
    assert before <= loaded["acquired_at"] <= after


@pytest.mark.asyncio
async def test_disk_token_written_after_successful_refresh_async(tmp_path, monkeypatch, httpx_mock):
    """BUG-03 x disk (async): mirror of the sync written-after-refresh test."""
    import time

    from iol_client import aio

    monkeypatch.setenv("CI", "false")
    path = tmp_path / "refresh_token.json"

    httpx_mock.add_response(
        url="https://api.invertironline.com/token",
        method="POST",
        json={
            "access_token": "acc",
            "refresh_token": "FRESH-REFRESH-TOKEN",
            "expires_in": 900,
        },
        match_content=b"grant_type=refresh_token",
    )

    before = time.time()
    client = aio.AsyncClient(
        base_url="https://api.invertironline.com",
        username="u",
        password="p",
        refresh_token="SEED-REFRESH-TOKEN",
        token_cache_path=path,
    )
    await client._aensure_token()
    await client.aclose()
    after = time.time()

    loaded = iol_client._token_cache.load(path)
    assert loaded is not None
    assert loaded["version"] == 1
    assert loaded["refresh_token"] == "FRESH-REFRESH-TOKEN"
    assert before <= loaded["acquired_at"] <= after


# ----------------------------------------------------------------------
# Regression — BUG-03 path 3: preserved-when-no-kwarg (anti-Pitfall 10 CI refusal)
# ----------------------------------------------------------------------


def test_disk_token_preserved_when_no_kwarg_sync(tmp_path, monkeypatch, httpx_mock):
    """BUG-03 x disk (sync): no kwarg + no env var + CI=true → disk untouched.

    With ``CI=true`` and neither ``token_cache_path`` kwarg nor
    ``IOL_TOKEN_CACHE_PATH`` env var, the default-path resolution is refused
    (anti-Pitfall 10). A token seeded at a separate path MUST be byte-untouched
    after ``_ensure_token()`` runs.
    """
    monkeypatch.setenv("CI", "true")
    monkeypatch.delenv("IOL_TOKEN_CACHE_PATH", raising=False)
    seeded = tmp_path / "elsewhere" / "refresh_token.json"
    seeded.parent.mkdir(parents=True)
    iol_client._token_cache.save(seeded, "UNTOUCHED-REFRESH-TOKEN", acquired_at=1.0)
    before_bytes = seeded.read_bytes()

    httpx_mock.add_response(
        url="https://api.invertironline.com/token",
        method="POST",
        json={"access_token": "acc", "refresh_token": "NEW", "expires_in": 900},
    )

    client = iol_client.Client(
        base_url="https://api.invertironline.com",
        username="u",
        password="p",
    )
    client._ensure_token()

    assert seeded.read_bytes() == before_bytes  # untouched: no read, no write


@pytest.mark.asyncio
async def test_disk_token_preserved_when_no_kwarg_async(tmp_path, monkeypatch, httpx_mock):
    """BUG-03 x disk (async): mirror of the sync preserved-when-no-kwarg test."""
    from iol_client import aio

    monkeypatch.setenv("CI", "true")
    monkeypatch.delenv("IOL_TOKEN_CACHE_PATH", raising=False)
    seeded = tmp_path / "elsewhere" / "refresh_token.json"
    seeded.parent.mkdir(parents=True)
    iol_client._token_cache.save(seeded, "UNTOUCHED-REFRESH-TOKEN", acquired_at=1.0)
    before_bytes = seeded.read_bytes()

    httpx_mock.add_response(
        url="https://api.invertironline.com/token",
        method="POST",
        json={"access_token": "acc", "refresh_token": "NEW", "expires_in": 900},
    )

    client = aio.AsyncClient(
        base_url="https://api.invertironline.com",
        username="u",
        password="p",
    )
    await client._aensure_token()
    await client.aclose()

    assert seeded.read_bytes() == before_bytes  # untouched: no read, no write


# ----------------------------------------------------------------------
# Regression — BUG-03 path 4: rotated-on-explicit-path
# ----------------------------------------------------------------------


def test_disk_token_rotated_on_explicit_path_sync(tmp_path, monkeypatch, httpx_mock):
    """BUG-03 x disk (sync): explicit path + successful refresh rotates the disk token.

    Seed disk with an OLD token, construct Client with explicit
    ``token_cache_path=path``, mock IOL refresh returning a NEW token, assert the
    disk file now contains the NEW token (NOT the old).
    """
    monkeypatch.setenv("CI", "false")
    path = tmp_path / "refresh_token.json"
    iol_client._token_cache.save(path, "OLD-REFRESH-TOKEN", acquired_at=1.0)

    httpx_mock.add_response(
        url="https://api.invertironline.com/token",
        method="POST",
        json={
            "access_token": "acc",
            "refresh_token": "NEW-REFRESH-TOKEN",
            "expires_in": 900,
        },
        match_content=b"grant_type=refresh_token",
    )

    client = iol_client.Client(
        base_url="https://api.invertironline.com",
        username="u",
        password="p",
        token_cache_path=path,
    )
    client._ensure_token()

    loaded = iol_client._token_cache.load(path)
    assert loaded is not None
    assert loaded["refresh_token"] == "NEW-REFRESH-TOKEN"
    assert loaded["refresh_token"] != "OLD-REFRESH-TOKEN"


@pytest.mark.asyncio
async def test_disk_token_rotated_on_explicit_path_async(tmp_path, monkeypatch, httpx_mock):
    """BUG-03 x disk (async): mirror of the sync rotated-on-explicit-path test."""
    from iol_client import aio

    monkeypatch.setenv("CI", "false")
    path = tmp_path / "refresh_token.json"
    iol_client._token_cache.save(path, "OLD-REFRESH-TOKEN", acquired_at=1.0)

    httpx_mock.add_response(
        url="https://api.invertironline.com/token",
        method="POST",
        json={
            "access_token": "acc",
            "refresh_token": "NEW-REFRESH-TOKEN",
            "expires_in": 900,
        },
        match_content=b"grant_type=refresh_token",
    )

    client = aio.AsyncClient(
        base_url="https://api.invertironline.com",
        username="u",
        password="p",
        token_cache_path=path,
    )
    await client._aensure_token()
    await client.aclose()

    loaded = iol_client._token_cache.load(path)
    assert loaded is not None
    assert loaded["refresh_token"] == "NEW-REFRESH-TOKEN"
    assert loaded["refresh_token"] != "OLD-REFRESH-TOKEN"
