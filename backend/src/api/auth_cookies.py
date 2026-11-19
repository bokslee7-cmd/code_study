import os

from fastapi import Response

from src.utils.jwt import decode_token

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth"

_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off"}


def cookie_secure() -> bool:
    """COOKIE_SECURE: false in development (plain http), true in production."""
    raw = os.environ.get("COOKIE_SECURE", "").strip().lower()
    if raw in _TRUE:
        return True
    if raw in _FALSE or raw == "":
        return False
    raise ValueError(f"COOKIE_SECURE must be a boolean (true/false), got {raw!r}")


def token_lifetime_seconds(token: str) -> int:
    claims = decode_token(token)
    return int(claims["exp"]) - int(claims["iat"])


def set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        refresh_token,
        max_age=token_lifetime_seconds(refresh_token),
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        samesite="strict",
        secure=cookie_secure(),
    )


def delete_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        samesite="strict",
        secure=cookie_secure(),
    )
