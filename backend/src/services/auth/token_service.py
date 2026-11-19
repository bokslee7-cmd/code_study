import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.exceptions import UnauthorizedException
from src.models import RefreshToken
from src.utils.jwt import (
    ACCESS,
    REFRESH,
    TokenError,
    TokenExpiredError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_token,
    verify_token,
)

TOKEN_EXPIRED_MESSAGE = "로그인 시간이 만료되었습니다. 다시 로그인하세요."
INVALID_TOKEN_MESSAGE = "인증 정보가 올바르지 않습니다. 다시 로그인하세요."


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str


def _verify(token: str, expected_type: str) -> uuid.UUID:
    """Signature, expiry and type check; the subject must be a user id."""
    try:
        payload = verify_token(token, expected_type)
    except TokenExpiredError:
        raise UnauthorizedException(TOKEN_EXPIRED_MESSAGE) from None
    except TokenError:
        raise UnauthorizedException(INVALID_TOKEN_MESSAGE) from None
    try:
        return uuid.UUID(payload["sub"])
    except ValueError:
        raise UnauthorizedException(INVALID_TOKEN_MESSAGE) from None


class TokenService:
    """Writes with flush(); the request-scoped session (get_session) commits or rolls back."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_tokens(self, user_id: uuid.UUID) -> TokenPair:
        access_token = create_access_token(str(user_id))
        refresh_token = create_refresh_token(str(user_id))
        expires_at = datetime.fromtimestamp(decode_token(refresh_token)["exp"], UTC)
        self._session.add(
            RefreshToken(
                user_id=user_id, token_hash=hash_token(refresh_token), expires_at=expires_at
            )
        )
        await self._session.flush()
        return TokenPair(access_token=access_token, refresh_token=refresh_token)

    def verify_access_token(self, token: str) -> uuid.UUID:
        """Stateless check: access tokens are not stored, so they cannot be revoked."""
        return _verify(token, ACCESS)

    async def verify_refresh_token(self, token: str, *, lock: bool = False) -> RefreshToken:
        """The token must be signed, unexpired, and still stored as neither revoked nor expired."""
        _verify(token, REFRESH)
        query = select(RefreshToken).where(RefreshToken.token_hash == hash_token(token))
        if lock:
            query = query.with_for_update()
        stored = (await self._session.execute(query)).scalar_one_or_none()
        if stored is None or stored.revoked or stored.expires_at <= datetime.now(UTC):
            raise UnauthorizedException(INVALID_TOKEN_MESSAGE)
        return stored

    async def rotate(self, refresh_token: str) -> TokenPair:
        """Revoke the presented refresh token and issue a new pair for the same user.

        The row is locked, so two concurrent requests with the same token cannot both succeed.
        """
        stored = await self.verify_refresh_token(refresh_token, lock=True)
        stored.revoked = True
        stored.revoked_at = datetime.now(UTC)
        return await self.create_tokens(stored.user_id)
