from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Request, Response

from src.api.auth_cookies import (
    REFRESH_COOKIE_NAME,
    delete_refresh_cookie,
    set_refresh_cookie,
    token_lifetime_seconds,
)
from src.api.dependencies import CurrentUser, get_token_service, get_user_service
from src.api.exceptions import UnauthorizedException, app_error_handler
from src.api.schemas.auth import (
    Credentials,
    LoginResponse,
    RegisterResponse,
    TokenResponse,
    UserResponse,
)
from src.services.auth.token_service import TokenService
from src.services.auth.user_service import UserService

router = APIRouter(prefix="/auth", tags=["auth"])

UserServiceDep = Annotated[UserService, Depends(get_user_service)]
TokenServiceDep = Annotated[TokenService, Depends(get_token_service)]
# Alias = cookie name; empty value is treated like a missing cookie by the routes.
RefreshCookie = Annotated[str | None, Cookie(alias=REFRESH_COOKIE_NAME)]


@router.post("/register", status_code=201, response_model=RegisterResponse)
async def register(body: Credentials, users: UserServiceDep) -> RegisterResponse:
    user = await users.register(body.email, body.password)
    return RegisterResponse(user=UserResponse.model_validate(user))


@router.post("/login", response_model=LoginResponse)
async def login(
    body: Credentials, response: Response, users: UserServiceDep, token_service: TokenServiceDep
) -> LoginResponse:
    user = await users.login(body.email, body.password)
    pair = await token_service.create_tokens(user.id)
    set_refresh_cookie(response, pair.refresh_token)
    return LoginResponse(
        access_token=pair.access_token,
        expires_in=token_lifetime_seconds(pair.access_token),
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
async def me(user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(user)


@router.post("/logout", status_code=204)
async def logout(
    response: Response, users: UserServiceDep, refresh_token: RefreshCookie = None
) -> None:
    if refresh_token:
        await users.logout(refresh_token)
    delete_refresh_cookie(response)


async def _reject_refresh(request: Request, error: UnauthorizedException) -> Response:
    """401 that also clears the stale refresh cookie."""
    response = await app_error_handler(request, error)
    delete_refresh_cookie(response)
    return response


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    token_service: TokenServiceDep,
    refresh_token: RefreshCookie = None,
) -> TokenResponse | Response:
    if not refresh_token:
        return await _reject_refresh(request, UnauthorizedException())
    try:
        pair = await token_service.rotate(refresh_token)
    except UnauthorizedException as exc:
        return await _reject_refresh(request, exc)
    set_refresh_cookie(response, pair.refresh_token)
    return TokenResponse(
        access_token=pair.access_token, expires_in=token_lifetime_seconds(pair.access_token)
    )
