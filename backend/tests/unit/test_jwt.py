from datetime import UTC, datetime, timedelta

import pytest
from jose import jwt as jose_jwt
from src.utils import jwt as tokens

SECRET = "test-secret-key-that-is-at-least-32-bytes-long"


@pytest.fixture(autouse=True)
def secret_env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", SECRET)
    monkeypatch.delenv("JWT_ACCESS_TOKEN_MINUTES", raising=False)
    monkeypatch.delenv("JWT_REFRESH_TOKEN_DAYS", raising=False)


def _raw(claims: dict, key: str = SECRET, algorithm: str = "HS256") -> str:
    return jose_jwt.encode(claims, key, algorithm=algorithm)


def _now() -> int:
    return int(datetime.now(UTC).timestamp())


def test_access_token_round_trip():
    token = tokens.create_access_token("user-1")
    payload = tokens.verify_token(token, tokens.ACCESS)
    assert payload["sub"] == "user-1"
    assert payload["type"] == "access"


def test_access_token_expires_in_15_minutes_by_default():
    payload = tokens.decode_token(tokens.create_access_token("u"))
    assert payload["exp"] - payload["iat"] == 15 * 60


def test_refresh_token_expires_in_7_days_by_default():
    payload = tokens.decode_token(tokens.create_refresh_token("u"))
    assert payload["type"] == "refresh"
    assert payload["exp"] - payload["iat"] == 7 * 24 * 3600


def test_lifetimes_are_configurable(monkeypatch):
    monkeypatch.setenv("JWT_ACCESS_TOKEN_MINUTES", "5")
    monkeypatch.setenv("JWT_REFRESH_TOKEN_DAYS", "1")
    access = tokens.decode_token(tokens.create_access_token("u"))
    refresh = tokens.decode_token(tokens.create_refresh_token("u"))
    assert access["exp"] - access["iat"] == 300
    assert refresh["exp"] - refresh["iat"] == 86400


def test_explicit_expires_delta_overrides_default():
    payload = tokens.decode_token(
        tokens.create_access_token("u", expires_delta=timedelta(minutes=1))
    )
    assert payload["exp"] - payload["iat"] == 60


def test_each_token_has_unique_jti():
    first = tokens.decode_token(tokens.create_refresh_token("u"))
    second = tokens.decode_token(tokens.create_refresh_token("u"))
    assert first["jti"] and first["jti"] != second["jti"]


def test_extra_claims_are_included_but_cannot_override_reserved():
    token = tokens.create_access_token(
        "u", extra_claims={"role": "admin", "sub": "attacker", "type": "refresh", "exp": 1}
    )
    payload = tokens.decode_token(token)
    assert payload["role"] == "admin"
    assert payload["sub"] == "u"
    assert payload["type"] == "access"
    assert payload["exp"] > _now()


def test_expired_token_raises_token_expired():
    token = tokens.create_access_token("u", expires_delta=timedelta(seconds=-1))
    with pytest.raises(tokens.TokenExpiredError):
        tokens.decode_token(token)


def test_tampered_token_is_invalid():
    token = tokens.create_access_token("u")
    with pytest.raises(tokens.InvalidTokenError):
        tokens.decode_token(token[:-2] + ("AA" if not token.endswith("AA") else "BB"))


def test_token_signed_with_other_key_is_invalid():
    forged = _raw(
        {"sub": "u", "type": "access", "iat": _now(), "exp": _now() + 60, "jti": "x"},
        key="another-secret-key-that-is-long-enough-123",
    )
    with pytest.raises(tokens.InvalidTokenError):
        tokens.decode_token(forged)


def test_other_algorithm_is_rejected():
    forged = _raw(
        {"sub": "u", "type": "access", "iat": _now(), "exp": _now() + 60, "jti": "x"},
        algorithm="HS512",
    )
    with pytest.raises(tokens.InvalidTokenError):
        tokens.decode_token(forged)


def test_unsigned_alg_none_token_is_rejected():
    header = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0"  # {"alg":"none","typ":"JWT"}
    body = "eyJzdWIiOiJ1IiwidHlwZSI6ImFjY2VzcyJ9"  # {"sub":"u","type":"access"}
    with pytest.raises(tokens.InvalidTokenError):
        tokens.decode_token(f"{header}.{body}.")


def test_garbage_is_invalid():
    with pytest.raises(tokens.InvalidTokenError):
        tokens.decode_token("not-a-jwt")


def test_verify_rejects_wrong_token_type():
    refresh = tokens.create_refresh_token("u")
    with pytest.raises(tokens.InvalidTokenError, match="type"):
        tokens.verify_token(refresh, tokens.ACCESS)
    access = tokens.create_access_token("u")
    with pytest.raises(tokens.InvalidTokenError, match="type"):
        tokens.verify_token(access, tokens.REFRESH)


@pytest.mark.parametrize("missing", ["sub", "type", "exp", "iat", "jti"])
def test_token_missing_required_claim_is_invalid(missing):
    claims = {"sub": "u", "type": "access", "iat": _now(), "exp": _now() + 60, "jti": "x"}
    del claims[missing]
    with pytest.raises(tokens.InvalidTokenError):
        tokens.verify_token(_raw(claims), tokens.ACCESS)


def test_errors_are_token_errors():
    assert issubclass(tokens.TokenExpiredError, tokens.TokenError)
    assert issubclass(tokens.InvalidTokenError, tokens.TokenError)


def test_secret_is_required(monkeypatch):
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        tokens.create_access_token("u")


def test_short_secret_is_rejected(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "short")
    with pytest.raises(RuntimeError, match="32"):
        tokens.create_access_token("u")


@pytest.mark.parametrize(
    ("name", "value"),
    [("JWT_ACCESS_TOKEN_MINUTES", "0"), ("JWT_REFRESH_TOKEN_DAYS", "abc")],
)
def test_invalid_lifetime_settings_raise(monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    with pytest.raises(ValueError, match=name):
        tokens.create_access_token("u")
        tokens.create_refresh_token("u")


def test_hash_token_is_sha256_hex():
    digest = tokens.hash_token("abc")
    assert digest == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
