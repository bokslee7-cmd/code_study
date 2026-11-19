import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from jose import jwt as jose_jwt
from src.api.exceptions import UnauthorizedException
from src.models import RefreshToken
from src.services.auth.token_service import (
    INVALID_TOKEN_MESSAGE,
    TOKEN_EXPIRED_MESSAGE,
    TokenPair,
    TokenService,
)
from src.utils import jwt as tokens

SECRET = "test-secret-key-that-is-at-least-32-bytes-long"
USER_ID = uuid.uuid4()


@pytest.fixture(autouse=True)
def secret_env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", SECRET)
    monkeypatch.delenv("JWT_ACCESS_TOKEN_MINUTES", raising=False)
    monkeypatch.delenv("JWT_REFRESH_TOKEN_DAYS", raising=False)


def _session(found: object | None = None) -> MagicMock:
    """Async session double whose every query returns `found` as the single scalar."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = found
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)
    session.flush = AsyncMock()
    session.add = MagicMock()
    return session


def _sql(session: MagicMock) -> str:
    statement = session.execute.call_args.args[0]
    return str(statement.compile(compile_kwargs={"literal_binds": True}))


def _stored(
    raw: str,
    *,
    user_id: uuid.UUID = USER_ID,
    revoked: bool = False,
    expires_at: datetime | None = None,
) -> RefreshToken:
    return RefreshToken(
        user_id=user_id,
        token_hash=tokens.hash_token(raw),
        expires_at=expires_at or datetime.now(UTC) + timedelta(days=7),
        revoked=revoked,
    )


def _added_token(session: MagicMock) -> RefreshToken:
    session.add.assert_called_once()
    added = session.add.call_args.args[0]
    assert isinstance(added, RefreshToken)
    return added


# ------------------------------------------------------------ create_tokens


async def test_create_tokens_returns_access_and_refresh_for_the_user():
    pair = await TokenService(_session()).create_tokens(USER_ID)

    assert isinstance(pair, TokenPair)
    access = tokens.verify_token(pair.access_token, tokens.ACCESS)
    refresh = tokens.verify_token(pair.refresh_token, tokens.REFRESH)
    assert access["sub"] == refresh["sub"] == str(USER_ID)


async def test_create_tokens_stores_only_the_hash_of_the_refresh_token():
    session = _session()

    pair = await TokenService(session).create_tokens(USER_ID)

    stored = _added_token(session)
    assert stored.user_id == USER_ID
    assert stored.token_hash == tokens.hash_token(pair.refresh_token)
    assert pair.refresh_token not in stored.token_hash
    session.flush.assert_awaited_once()


async def test_create_tokens_stores_the_same_expiry_as_the_refresh_token():
    session = _session()

    pair = await TokenService(session).create_tokens(USER_ID)

    exp = tokens.decode_token(pair.refresh_token)["exp"]
    assert _added_token(session).expires_at == datetime.fromtimestamp(exp, UTC)


async def test_create_tokens_expire_in_15_minutes_and_7_days():
    pair = await TokenService(_session()).create_tokens(USER_ID)

    access = tokens.decode_token(pair.access_token)
    refresh = tokens.decode_token(pair.refresh_token)
    assert access["exp"] - access["iat"] == 15 * 60
    assert refresh["exp"] - refresh["iat"] == 7 * 24 * 3600


async def test_create_tokens_issues_a_different_refresh_token_every_time():
    service = TokenService(_session())

    first = await service.create_tokens(USER_ID)
    second = await service.create_tokens(USER_ID)

    assert first.refresh_token != second.refresh_token


# -------------------------------------------------------- verify_access_token


async def test_verify_access_token_returns_the_user_id():
    token = tokens.create_access_token(str(USER_ID))

    assert TokenService(_session()).verify_access_token(token) == USER_ID


def test_verify_access_token_rejects_expired_token_with_expiry_message():
    token = tokens.create_access_token(str(USER_ID), expires_delta=timedelta(seconds=-5))

    with pytest.raises(UnauthorizedException) as exc_info:
        TokenService(_session()).verify_access_token(token)

    assert exc_info.value.status_code == 401
    assert exc_info.value.message == TOKEN_EXPIRED_MESSAGE


def test_verify_access_token_rejects_refresh_token():
    token = tokens.create_refresh_token(str(USER_ID))

    with pytest.raises(UnauthorizedException) as exc_info:
        TokenService(_session()).verify_access_token(token)

    assert exc_info.value.message == INVALID_TOKEN_MESSAGE


def test_verify_access_token_rejects_token_signed_with_another_key():
    now = int(datetime.now(UTC).timestamp())
    claims = {"sub": str(USER_ID), "type": "access", "iat": now, "exp": now + 60, "jti": "x"}
    forged = jose_jwt.encode(claims, "another-secret-key-that-is-32-bytes-long!", algorithm="HS256")

    with pytest.raises(UnauthorizedException) as exc_info:
        TokenService(_session()).verify_access_token(forged)

    assert exc_info.value.message == INVALID_TOKEN_MESSAGE


@pytest.mark.parametrize("garbage", ["", "not-a-jwt", "a.b.c"])
def test_verify_access_token_rejects_malformed_token(garbage):
    with pytest.raises(UnauthorizedException) as exc_info:
        TokenService(_session()).verify_access_token(garbage)

    assert exc_info.value.message == INVALID_TOKEN_MESSAGE


def test_verify_access_token_rejects_subject_that_is_not_a_uuid():
    token = tokens.create_access_token("user-1")

    with pytest.raises(UnauthorizedException) as exc_info:
        TokenService(_session()).verify_access_token(token)

    assert exc_info.value.message == INVALID_TOKEN_MESSAGE


# ------------------------------------------------------- verify_refresh_token


async def test_verify_refresh_token_returns_the_stored_row():
    raw = tokens.create_refresh_token(str(USER_ID))
    stored = _stored(raw)
    session = _session(found=stored)

    result = await TokenService(session).verify_refresh_token(raw)

    assert result is stored
    assert tokens.hash_token(raw) in _sql(session)
    assert raw not in _sql(session)


async def test_verify_refresh_token_rejects_access_token_without_querying():
    session = _session()

    with pytest.raises(UnauthorizedException):
        await TokenService(session).verify_refresh_token(tokens.create_access_token(str(USER_ID)))

    session.execute.assert_not_awaited()


async def test_verify_refresh_token_rejects_expired_jwt_with_expiry_message():
    raw = tokens.create_refresh_token(str(USER_ID), expires_delta=timedelta(seconds=-5))
    session = _session(found=_stored(raw))

    with pytest.raises(UnauthorizedException) as exc_info:
        await TokenService(session).verify_refresh_token(raw)

    assert exc_info.value.message == TOKEN_EXPIRED_MESSAGE
    session.execute.assert_not_awaited()


async def test_verify_refresh_token_rejects_malformed_token_without_querying():
    session = _session()

    with pytest.raises(UnauthorizedException) as exc_info:
        await TokenService(session).verify_refresh_token("not-a-jwt")

    assert exc_info.value.message == INVALID_TOKEN_MESSAGE
    session.execute.assert_not_awaited()


async def test_verify_refresh_token_rejects_token_that_was_never_stored():
    raw = tokens.create_refresh_token(str(USER_ID))

    with pytest.raises(UnauthorizedException) as exc_info:
        await TokenService(_session(found=None)).verify_refresh_token(raw)

    assert exc_info.value.message == INVALID_TOKEN_MESSAGE


async def test_verify_refresh_token_rejects_revoked_token():
    raw = tokens.create_refresh_token(str(USER_ID))

    with pytest.raises(UnauthorizedException) as exc_info:
        await TokenService(_session(found=_stored(raw, revoked=True))).verify_refresh_token(raw)

    assert exc_info.value.message == INVALID_TOKEN_MESSAGE


async def test_verify_refresh_token_rejects_row_that_expired_in_the_database():
    raw = tokens.create_refresh_token(str(USER_ID))
    stored = _stored(raw, expires_at=datetime.now(UTC) - timedelta(seconds=1))

    with pytest.raises(UnauthorizedException):
        await TokenService(_session(found=stored)).verify_refresh_token(raw)


# --------------------------------------------------------------------- rotate


async def test_rotate_revokes_the_old_token_and_issues_a_new_pair():
    raw = tokens.create_refresh_token(str(USER_ID))
    old = _stored(raw)
    session = _session(found=old)

    pair = await TokenService(session).rotate(raw)

    assert old.revoked is True
    assert old.revoked_at is not None
    assert pair.refresh_token != raw
    assert tokens.verify_token(pair.access_token, tokens.ACCESS)["sub"] == str(USER_ID)
    new = _added_token(session)
    assert new.user_id == USER_ID
    assert new.token_hash == tokens.hash_token(pair.refresh_token)


async def test_rotate_issues_tokens_for_the_owner_of_the_stored_row():
    owner = uuid.uuid4()
    raw = tokens.create_refresh_token(str(owner))
    session = _session(found=_stored(raw, user_id=owner))

    pair = await TokenService(session).rotate(raw)

    assert tokens.decode_token(pair.refresh_token)["sub"] == str(owner)


async def test_rotate_locks_the_row_so_concurrent_requests_cannot_reuse_it():
    raw = tokens.create_refresh_token(str(USER_ID))
    session = _session(found=_stored(raw))

    await TokenService(session).rotate(raw)

    assert "FOR UPDATE" in _sql(session)


async def test_rotate_rejects_a_token_that_was_already_rotated():
    raw = tokens.create_refresh_token(str(USER_ID))
    session = _session(found=_stored(raw))
    service = TokenService(session)
    await service.rotate(raw)
    session.add.reset_mock()

    with pytest.raises(UnauthorizedException):
        await service.rotate(raw)

    session.add.assert_not_called()


@pytest.mark.parametrize("found", [None, "revoked", "expired"])
async def test_rotate_issues_nothing_when_the_refresh_token_is_not_usable(found):
    raw = tokens.create_refresh_token(str(USER_ID))
    stored = {
        None: None,
        "revoked": _stored(raw, revoked=True),
        "expired": _stored(raw, expires_at=datetime.now(UTC) - timedelta(seconds=1)),
    }[found]
    session = _session(found=stored)

    with pytest.raises(UnauthorizedException):
        await TokenService(session).rotate(raw)

    session.add.assert_not_called()
    session.flush.assert_not_awaited()


async def test_rotate_rejects_access_token():
    session = _session()

    with pytest.raises(UnauthorizedException):
        await TokenService(session).rotate(tokens.create_access_token(str(USER_ID)))

    session.add.assert_not_called()
