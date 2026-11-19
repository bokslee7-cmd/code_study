import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import IntegrityError
from src.api.exceptions import AppError, ConflictException, UnauthorizedException
from src.models import RefreshToken, User
from src.services.auth.user_service import UserService
from src.utils import security
from src.utils.jwt import hash_token

PASSWORD = "correct-horse-battery"


@pytest.fixture(autouse=True)
def cheap_bcrypt(monkeypatch):
    """bcrypt cost 12 would make every test take ~250ms."""
    monkeypatch.setattr(
        security,
        "_pwd_context",
        security._pwd_context.copy(bcrypt__rounds=4),
    )


def _session(found: object | None = None) -> MagicMock:
    """Async session double whose every query returns `found` as the single scalar."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = found
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    return session


def _sql(session: MagicMock) -> str:
    statement = session.execute.call_args.args[0]
    return str(statement.compile(compile_kwargs={"literal_binds": True}))


def _user(password: str = PASSWORD, email: str = "learner@example.com") -> User:
    return User(id=uuid.uuid4(), email=email, password_hash=security.hash_password(password))


# ---------------------------------------------------------------- register


async def test_register_saves_user_with_hashed_password():
    session = _session(found=None)
    user = await UserService(session).register("learner@example.com", PASSWORD)

    session.add.assert_called_once_with(user)
    assert user.email == "learner@example.com"
    assert user.password_hash != PASSWORD
    assert security.verify_password(PASSWORD, user.password_hash)
    session.flush.assert_awaited_once()
    session.refresh.assert_awaited_once_with(user)


async def test_register_normalizes_email_before_lookup_and_save():
    session = _session(found=None)
    user = await UserService(session).register("  Learner@Example.COM ", PASSWORD)

    assert user.email == "learner@example.com"
    assert "learner@example.com" in _sql(session)


async def test_register_rejects_duplicate_email_with_conflict():
    session = _session(found=_user())

    with pytest.raises(ConflictException) as exc_info:
        await UserService(session).register("learner@example.com", PASSWORD)

    assert exc_info.value.status_code == 409
    session.add.assert_not_called()


async def test_register_turns_unique_violation_race_into_conflict():
    session = _session(found=None)
    session.flush.side_effect = IntegrityError("INSERT", {}, Exception("duplicate key"))

    with pytest.raises(ConflictException):
        await UserService(session).register("learner@example.com", PASSWORD)


@pytest.mark.parametrize(
    "email",
    [
        "",
        "   ",
        "no-at-sign",
        "a@b",
        "a@b.c",
        "a b@example.com",
        "a@@example.com",
        "x" * 250 + "@a.com",
    ],
)
async def test_register_rejects_invalid_email_with_400(email):
    session = _session(found=None)

    with pytest.raises(AppError) as exc_info:
        await UserService(session).register(email, PASSWORD)

    assert exc_info.value.status_code == 400
    assert exc_info.value.error == "validation_error"
    assert exc_info.value.details == {"field": "email"}
    session.add.assert_not_called()


@pytest.mark.parametrize("password", ["short", "", "가" * 25])
async def test_register_rejects_weak_or_oversized_password_with_400(password):
    session = _session(found=None)

    with pytest.raises(AppError) as exc_info:
        await UserService(session).register("learner@example.com", password)

    assert exc_info.value.status_code == 400
    assert exc_info.value.details == {"field": "password"}
    session.add.assert_not_called()


async def test_register_error_never_echoes_the_password():
    with pytest.raises(AppError) as exc_info:
        await UserService(_session()).register("learner@example.com", "short")

    assert "short" not in exc_info.value.message


# ------------------------------------------------------------------- login


async def test_login_returns_user_and_records_last_login():
    user = _user()
    session = _session(found=user)
    before = datetime.now(UTC)

    result = await UserService(session).login("learner@example.com", PASSWORD)

    assert result is user
    assert user.last_login_at is not None and before <= user.last_login_at <= datetime.now(UTC)
    session.flush.assert_awaited_once()
    session.refresh.assert_awaited_once_with(user)


async def test_login_normalizes_email():
    session = _session(found=_user())
    await UserService(session).login("  LEARNER@example.com ", PASSWORD)
    assert "learner@example.com" in _sql(session)


async def test_login_rejects_wrong_password():
    user = _user()
    session = _session(found=user)

    with pytest.raises(UnauthorizedException):
        await UserService(session).login("learner@example.com", "wrong-password-1")

    assert user.last_login_at is None
    session.flush.assert_not_awaited()


async def test_login_rejects_unknown_email_with_same_message_as_wrong_password():
    with pytest.raises(UnauthorizedException) as unknown:
        await UserService(_session(found=None)).login("ghost@example.com", PASSWORD)
    with pytest.raises(UnauthorizedException) as wrong:
        await UserService(_session(found=_user())).login("learner@example.com", "wrong-password-1")

    assert unknown.value.message == wrong.value.message
    assert unknown.value.status_code == wrong.value.status_code == 401


async def test_login_still_hashes_when_email_is_unknown(monkeypatch):
    """Skipping bcrypt for unknown emails would reveal which emails are registered by timing."""
    calls = []
    real_verify = security.verify_password
    monkeypatch.setattr(
        "src.services.auth.user_service.verify_password",
        lambda password, hashed: calls.append(hashed) or real_verify(password, hashed),
    )

    with pytest.raises(UnauthorizedException):
        await UserService(_session(found=None)).login("ghost@example.com", PASSWORD)

    assert len(calls) == 1


async def test_login_upgrades_weaker_password_hash(monkeypatch):
    user = _user()
    old_hash = user.password_hash
    monkeypatch.setattr("src.services.auth.user_service.needs_rehash", lambda _hash: True)

    await UserService(_session(found=user)).login("learner@example.com", PASSWORD)

    assert user.password_hash != old_hash
    assert security.verify_password(PASSWORD, user.password_hash)


async def test_login_keeps_hash_when_no_upgrade_is_needed():
    user = _user()
    old_hash = user.password_hash

    await UserService(_session(found=user)).login("learner@example.com", PASSWORD)

    assert user.password_hash == old_hash


# ------------------------------------------------------------------ logout


def _stored_token(raw: str, *, revoked: bool = False) -> RefreshToken:
    return RefreshToken(
        user_id=uuid.uuid4(),
        token_hash=hash_token(raw),
        expires_at=datetime.now(UTC) + timedelta(days=7),
        revoked=revoked,
    )


async def test_logout_revokes_the_matching_refresh_token():
    stored = _stored_token("raw-refresh-token")
    session = _session(found=stored)

    await UserService(session).logout("raw-refresh-token")

    assert stored.revoked is True
    assert stored.revoked_at is not None
    session.flush.assert_awaited_once()
    assert hash_token("raw-refresh-token") in _sql(session)
    assert "raw-refresh-token" not in _sql(session)


async def test_logout_is_idempotent_for_unknown_token():
    session = _session(found=None)

    await UserService(session).logout("never-issued")

    session.flush.assert_not_awaited()


async def test_logout_keeps_original_revocation_time():
    stored = _stored_token("raw", revoked=True)
    stored.revoked_at = datetime(2026, 1, 1, tzinfo=UTC)
    session = _session(found=stored)

    await UserService(session).logout("raw")

    assert stored.revoked_at == datetime(2026, 1, 1, tzinfo=UTC)
    session.flush.assert_not_awaited()


# ------------------------------------------------------------------ get_by_id


async def test_get_by_id_returns_the_user_with_that_id():
    user = _user()
    session = _session(found=user)

    result = await UserService(session).get_by_id(user.id)

    assert result is user
    assert user.id.hex in _sql(session)


async def test_get_by_id_returns_none_for_unknown_id():
    assert await UserService(_session(found=None)).get_by_id(uuid.uuid4()) is None
