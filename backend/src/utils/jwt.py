import hashlib
import os
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import ExpiredSignatureError, JWTError
from jose import jwt as jose_jwt

ALGORITHM = "HS256"
ACCESS = "access"
REFRESH = "refresh"

_MIN_SECRET_LENGTH = 32
_REQUIRED_CLAIMS = ("sub", "type", "exp", "iat", "jti")


class TokenError(Exception):
    """Base class for token validation failures."""


class TokenExpiredError(TokenError):
    pass


class InvalidTokenError(TokenError):
    pass


def _get_secret() -> str:
    secret = os.environ.get("JWT_SECRET_KEY")
    if not secret:
        raise RuntimeError("JWT_SECRET_KEY environment variable is required")
    if len(secret) < _MIN_SECRET_LENGTH:
        raise RuntimeError(f"JWT_SECRET_KEY must be at least {_MIN_SECRET_LENGTH} characters")
    return secret


def _read_positive_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ValueError(f"{name} must be an integer, got {raw!r}") from None
    if value < 1:
        raise ValueError(f"{name} must be >= 1, got {value}")
    return value


def _create_token(
    subject: str,
    token_type: str,
    expires_delta: timedelta,
    extra_claims: dict[str, Any] | None,
) -> str:
    now = datetime.now(UTC)
    claims: dict[str, Any] = dict(extra_claims or {})
    claims.update(
        {
            "sub": subject,
            "type": token_type,
            "iat": int(now.timestamp()),
            "exp": int((now + expires_delta).timestamp()),
            "jti": uuid.uuid4().hex,
        }
    )
    return jose_jwt.encode(claims, _get_secret(), algorithm=ALGORITHM)


def create_access_token(
    subject: str,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Short-lived access token (default 15 minutes, JWT_ACCESS_TOKEN_MINUTES)."""
    if expires_delta is None:
        expires_delta = timedelta(minutes=_read_positive_int("JWT_ACCESS_TOKEN_MINUTES", 15))
    return _create_token(subject, ACCESS, expires_delta, extra_claims)


def create_refresh_token(
    subject: str,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Long-lived refresh token (default 7 days, JWT_REFRESH_TOKEN_DAYS)."""
    if expires_delta is None:
        expires_delta = timedelta(days=_read_positive_int("JWT_REFRESH_TOKEN_DAYS", 7))
    return _create_token(subject, REFRESH, expires_delta, extra_claims)


def decode_token(token: str) -> dict[str, Any]:
    """Verify signature and expiry, and return the claims."""
    try:
        payload: dict[str, Any] = jose_jwt.decode(
            token,
            _get_secret(),
            algorithms=[ALGORITHM],
            options={"require_exp": True, "require_iat": True, "require_sub": True},
        )
    except ExpiredSignatureError:
        raise TokenExpiredError("Token has expired") from None
    except JWTError as exc:
        raise InvalidTokenError(f"Invalid token: {exc}") from None
    missing = [claim for claim in _REQUIRED_CLAIMS if claim not in payload]
    if missing:
        raise InvalidTokenError(f"Token is missing claims: {', '.join(missing)}")
    return payload


def verify_token(token: str, expected_type: str) -> dict[str, Any]:
    """Decode a token and make sure it is of the expected type (access or refresh)."""
    payload = decode_token(token)
    if payload["type"] != expected_type:
        raise InvalidTokenError(f"Invalid token type: expected {expected_type}")
    return payload


def hash_token(token: str) -> str:
    """SHA-256 hex digest, used to store refresh tokens without keeping the plaintext."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
