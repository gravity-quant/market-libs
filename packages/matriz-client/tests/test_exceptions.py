from __future__ import annotations

import pytest

from matriz_client.exceptions import AuthenticationError, PrimaryAPIError


def test_primary_api_error_uses_description_first() -> None:
    err = PrimaryAPIError("ERROR", description="invalid symbol", message="generic")
    assert str(err) == "invalid symbol"
    assert err.status == "ERROR"
    assert err.description == "invalid symbol"
    assert err.api_message == "generic"


def test_primary_api_error_falls_back_to_message() -> None:
    err = PrimaryAPIError("ERROR", message="something broke")
    assert str(err) == "something broke"


def test_primary_api_error_falls_back_to_status() -> None:
    err = PrimaryAPIError("ERROR")
    assert str(err) == "ERROR"


def test_authentication_error_is_primary_api_error() -> None:
    err = AuthenticationError("ERROR", description="bad credentials")
    assert isinstance(err, PrimaryAPIError)
    with pytest.raises(AuthenticationError):
        raise err
