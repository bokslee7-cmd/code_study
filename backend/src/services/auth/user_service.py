import re
import uuid
from datetime import UTC, datetime
from functools import lru_cache

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.exceptions import (
    VALIDATION_ERROR,
    AppError,
    ConflictException,
    UnauthorizedException,
)
from src.models import RefreshToken, User
from src.utils.jwt import hash_token
from src.utils.security import (
    MAX_PASSWORD_BYTES,
    MIN_PASSWORD_LENGTH,
    hash_password,
    needs_rehash,
    validate_password,
    verify_password,
)

MAX_EMAIL_LENGTH = 255
EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")

INVALID_EMAIL_MESSAGE = "올바른 이메일 형식이 아닙니다."
_PASSWORD_RULE = f"{MIN_PASSWORD_LENGTH}자 이상, {MAX_PASSWORD_BYTES}바이트 이하"
INVALID_PASSWORD_MESSAGE = f"비밀번호는 {_PASSWORD_RULE}여야 합니다."
DUPLICATE_EMAIL_MESSAGE = "이미 가입된 이메일입니다."
INVALID_CREDENTIALS_MESSAGE = "이메일 또는 비밀번호가 올바르지 않습니다."


@lru_cache
def _dummy_password_hash() -> str:
    # Verified against when the email is unknown, so both login failures cost one bcrypt check.
    return hash_password("dummy-password-for-timing")


def normalize_email(email: str) -> str:
    return email.strip().lower()


def _validation_error(field: str, message: str) -> AppError:
    return AppError(400, VALIDATION_ERROR, message, details={"field": field})


class UserService:
    """Writes with flush(); the request-scoped session (get_session) commits or rolls back."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def register(self, email: str, password: str) -> User:
        email = normalize_email(email)
        if len(email) > MAX_EMAIL_LENGTH or not EMAIL_PATTERN.match(email):
            raise _validation_error("email", INVALID_EMAIL_MESSAGE)
        try:
            validate_password(password)
        except ValueError:
            raise _validation_error("password", INVALID_PASSWORD_MESSAGE) from None

        if await self._find_by_email(email) is not None:
            raise ConflictException(DUPLICATE_EMAIL_MESSAGE)

        user = User(email=email, password_hash=hash_password(password))
        self._session.add(user)
        try:
            await self._session.flush()
        except IntegrityError:  # same email registered between the lookup and the insert
            raise ConflictException(DUPLICATE_EMAIL_MESSAGE) from None
        await self._session.refresh(user)
        return user

    async def login(self, email: str, password: str) -> User:
        user = await self._find_by_email(normalize_email(email))
        password_hash = user.password_hash if user else _dummy_password_hash()
        password_ok = verify_password(password, password_hash)
        if user is None or not password_ok:
            raise UnauthorizedException(INVALID_CREDENTIALS_MESSAGE)

        if needs_rehash(user.password_hash):
            user.password_hash = hash_password(password)
        user.last_login_at = datetime.now(UTC)
        await self._session.flush()
        await self._session.refresh(user)
        return user

    async def logout(self, refresh_token: str) -> None:
        """Revoke the refresh token. Unknown or already revoked tokens are not an error."""
        result = await self._session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == hash_token(refresh_token))
        )
        stored = result.scalar_one_or_none()
        if stored is None or stored.revoked:
            return
        stored.revoked = True
        stored.revoked_at = datetime.now(UTC)
        await self._session.flush()

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self._session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def _find_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()
