import pytest
from passlib.context import CryptContext
from src.utils import security


def test_hash_is_bcrypt_with_cost_12_and_not_plaintext():
    hashed = security.hash_password("correct horse battery")
    assert hashed.startswith("$2b$12$")
    assert "correct horse" not in hashed
    assert len(hashed) <= 255  # users.password_hash is VARCHAR(255)


def test_same_password_gets_different_salted_hashes():
    assert security.hash_password("password123") != security.hash_password("password123")


def test_verify_password_accepts_correct_and_rejects_wrong():
    hashed = security.hash_password("password123")
    assert security.verify_password("password123", hashed) is True
    assert security.verify_password("password124", hashed) is False
    assert security.verify_password("", hashed) is False


def test_verify_password_supports_unicode():
    hashed = security.hash_password("비밀번호-테스트-123")
    assert security.verify_password("비밀번호-테스트-123", hashed) is True
    assert security.verify_password("비밀번호-테스트-124", hashed) is False


def test_verify_password_with_malformed_hash_returns_false():
    assert security.verify_password("password123", "not-a-hash") is False
    assert security.verify_password("password123", "") is False


def test_empty_password_cannot_be_hashed():
    with pytest.raises(ValueError, match="empty"):
        security.hash_password("")


def test_password_over_72_bytes_is_rejected_not_truncated():
    too_long = "a" * 73
    with pytest.raises(ValueError, match="72"):
        security.hash_password(too_long)
    # 72 bytes is the limit and is accepted
    hashed = security.hash_password("a" * 72)
    assert security.verify_password("a" * 72, hashed) is True
    # an over-long attempt never matches (bcrypt would otherwise ignore the extra bytes)
    assert security.verify_password(too_long, hashed) is False


def test_limit_counts_bytes_not_characters():
    with pytest.raises(ValueError, match="72"):
        security.hash_password("가" * 25)  # 75 bytes in UTF-8


def test_needs_rehash_detects_weaker_cost():
    weak = CryptContext(schemes=["bcrypt"], bcrypt__rounds=4).hash("password123")
    assert security.needs_rehash(weak) is True
    assert security.needs_rehash(security.hash_password("password123")) is False


@pytest.mark.parametrize("password", ["12345678", "a" * 8, "비밀번호테스트1234"])
def test_validate_password_accepts_valid(password):
    security.validate_password(password)


@pytest.mark.parametrize("password", ["", "short", "1234567"])
def test_validate_password_rejects_short(password):
    with pytest.raises(ValueError, match="8"):
        security.validate_password(password)


def test_validate_password_rejects_over_72_bytes():
    with pytest.raises(ValueError, match="72"):
        security.validate_password("a" * 73)
