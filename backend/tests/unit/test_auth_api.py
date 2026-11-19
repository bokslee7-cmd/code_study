import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from src import main
from src.api import auth_cookies
from src.api.dependencies import get_token_service, get_user_service
from src.api.exceptions import ConflictException, UnauthorizedException
from src.db.session import get_session
from src.models import User
from src.services.auth.token_service import INVALID_TOKEN_MESSAGE, TokenPair, TokenService
from src.services.auth.user_service import (
    DUPLICATE_EMAIL_MESSAGE,
    INVALID_CREDENTIALS_MESSAGE,
    UserService,
)
from src.utils import jwt as tokens

SECRET = "test-secret-key-that-is-at-least-32-bytes-long"
ORIGIN = "http://localhost:5173"
USER_ID = uuid.uuid4()
EMAIL = "learner@example.com"
PASSWORD = "S3cure-passw0rd!"
AUTH_PATH = "/api/v1/auth"
SEVEN_DAYS = 7 * 24 * 60 * 60


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", SECRET)
    monkeypatch.delenv("JWT_ACCESS_TOKEN_MINUTES", raising=False)
    monkeypatch.delenv("JWT_REFRESH_TOKEN_DAYS", raising=False)
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    monkeypatch.delenv("COOKIE_SECURE", raising=False)


def _user(skill_level: str | None = "Complete Beginner") -> User:
    return User(id=USER_ID, email=EMAIL, password_hash="x", skill_level=skill_level)


def _pair() -> TokenPair:
    return TokenPair(
        access_token=tokens.create_access_token(str(USER_ID)),
        refresh_token=tokens.create_refresh_token(str(USER_ID)),
    )


class _Harness:
    """The real app with the services replaced by doubles, so only the HTTP contract is tested."""

    def __init__(self, found: User | None = None) -> None:
        self.users = MagicMock(spec=UserService)
        self.users.register = AsyncMock(return_value=_user())
        self.users.login = AsyncMock(return_value=_user())
        self.users.logout = AsyncMock(return_value=None)
        self.tokens = MagicMock(spec=TokenService)
        self.tokens.create_tokens = AsyncMock(return_value=_pair())
        self.tokens.rotate = AsyncMock(return_value=_pair())

        result = MagicMock()
        result.scalar_one_or_none.return_value = found
        self.session = MagicMock()
        self.session.execute = AsyncMock(return_value=result)

        async def fake_get_session():
            yield self.session

        app = main.create_app()
        app.dependency_overrides[get_session] = fake_get_session
        app.dependency_overrides[get_user_service] = lambda: self.users
        app.dependency_overrides[get_token_service] = lambda: self.tokens
        self.client = TestClient(app, raise_server_exceptions=False)


def _cookie_header(token: str) -> dict[str, str]:
    return {"Cookie": f"refresh_token={token}"}


def _set_cookies(response) -> list[str]:
    return [value.lower() for value in response.headers.get_list("set-cookie")]


def _refresh_cookie(response) -> str:
    cookies = [c for c in _set_cookies(response) if c.startswith("refresh_token=")]
    assert len(cookies) == 1
    return cookies[0]


def _assert_cookie_attributes(cookie: str, max_age: int) -> None:
    assert "httponly" in cookie
    assert "samesite=strict" in cookie
    assert f"path={AUTH_PATH}" in cookie
    assert f"max-age={max_age}" in cookie


# ---------------------------------------------------------------- wiring


def test_auth_routes_are_mounted_under_api_v1():
    app = main.create_app()
    routes = {
        (route.path, method) for route in app.routes for method in getattr(route, "methods", [])
    }

    assert (f"{AUTH_PATH}/register", "POST") in routes
    assert (f"{AUTH_PATH}/login", "POST") in routes
    assert (f"{AUTH_PATH}/me", "GET") in routes
    assert (f"{AUTH_PATH}/logout", "POST") in routes
    assert (f"{AUTH_PATH}/refresh", "POST") in routes


def test_service_dependencies_wrap_the_request_session():
    session = MagicMock()

    user_service = get_user_service(session)
    token_service = get_token_service(session)

    assert isinstance(user_service, UserService)
    assert isinstance(token_service, TokenService)


def test_cors_preflight_for_login_allows_credentials_from_the_frontend_origin():
    client = _Harness().client

    response = client.options(
        f"{AUTH_PATH}/login",
        headers={
            "Origin": ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ORIGIN
    assert response.headers["access-control-allow-credentials"] == "true"


# ---------------------------------------------------------------- register


def test_register_returns_201_with_the_user_only():
    harness = _Harness()

    response = harness.client.post(
        f"{AUTH_PATH}/register", json={"email": EMAIL, "password": PASSWORD}
    )

    assert response.status_code == 201
    assert response.json() == {
        "user": {"id": str(USER_ID), "email": EMAIL, "skill_level": "Complete Beginner"}
    }
    assert response.headers.get_list("set-cookie") == []


def test_register_passes_email_and_password_to_the_user_service():
    harness = _Harness()

    harness.client.post(f"{AUTH_PATH}/register", json={"email": EMAIL, "password": PASSWORD})

    harness.users.register.assert_awaited_once_with(EMAIL, PASSWORD)


def test_register_never_echoes_the_password():
    harness = _Harness()

    response = harness.client.post(
        f"{AUTH_PATH}/register", json={"email": EMAIL, "password": PASSWORD}
    )

    assert PASSWORD not in response.text
    assert "password" not in response.text


def test_register_duplicate_email_is_409():
    harness = _Harness()
    harness.users.register.side_effect = ConflictException(DUPLICATE_EMAIL_MESSAGE)

    response = harness.client.post(
        f"{AUTH_PATH}/register", json={"email": EMAIL, "password": PASSWORD}
    )

    assert response.status_code == 409
    assert response.json() == {"error": "conflict", "message": DUPLICATE_EMAIL_MESSAGE}


@pytest.mark.parametrize("body", [{"email": EMAIL}, {"password": PASSWORD}, {}, {"email": 1}])
def test_register_with_missing_or_malformed_fields_is_400(body):
    harness = _Harness()

    response = harness.client.post(f"{AUTH_PATH}/register", json=body)

    assert response.status_code == 400
    assert response.json()["error"] == "validation_error"
    harness.users.register.assert_not_awaited()


# ---------------------------------------------------------------- login


def test_login_returns_access_token_and_user():
    harness = _Harness()
    pair = _pair()
    harness.tokens.create_tokens.return_value = pair

    response = harness.client.post(
        f"{AUTH_PATH}/login", json={"email": EMAIL, "password": PASSWORD}
    )

    assert response.status_code == 200
    assert response.json() == {
        "access_token": pair.access_token,
        "token_type": "bearer",
        "expires_in": 900,
        "user": {"id": str(USER_ID), "email": EMAIL, "skill_level": "Complete Beginner"},
    }
    harness.users.login.assert_awaited_once_with(EMAIL, PASSWORD)
    harness.tokens.create_tokens.assert_awaited_once_with(USER_ID)


def test_login_expires_in_follows_the_configured_access_token_lifetime(monkeypatch):
    monkeypatch.setenv("JWT_ACCESS_TOKEN_MINUTES", "20")
    harness = _Harness()
    harness.tokens.create_tokens.return_value = _pair()

    response = harness.client.post(
        f"{AUTH_PATH}/login", json={"email": EMAIL, "password": PASSWORD}
    )

    assert response.json()["expires_in"] == 1200


def test_login_sets_the_refresh_token_in_an_http_only_cookie_not_in_the_body():
    harness = _Harness()
    pair = _pair()
    harness.tokens.create_tokens.return_value = pair

    response = harness.client.post(
        f"{AUTH_PATH}/login", json={"email": EMAIL, "password": PASSWORD}
    )

    cookie = _refresh_cookie(response)
    assert cookie.startswith(f"refresh_token={pair.refresh_token.lower()}")
    _assert_cookie_attributes(cookie, SEVEN_DAYS)
    assert "secure" not in cookie.replace("samesite", "")
    assert pair.refresh_token not in response.text


def test_login_cookie_max_age_follows_the_configured_refresh_token_lifetime(monkeypatch):
    monkeypatch.setenv("JWT_REFRESH_TOKEN_DAYS", "3")
    harness = _Harness()
    harness.tokens.create_tokens.return_value = _pair()

    response = harness.client.post(
        f"{AUTH_PATH}/login", json={"email": EMAIL, "password": PASSWORD}
    )

    assert f"max-age={3 * 24 * 60 * 60}" in _refresh_cookie(response)


def test_login_cookie_is_secure_when_configured(monkeypatch):
    monkeypatch.setenv("COOKIE_SECURE", "true")
    harness = _Harness()

    response = harness.client.post(
        f"{AUTH_PATH}/login", json={"email": EMAIL, "password": PASSWORD}
    )

    assert "; secure" in _refresh_cookie(response)


def test_login_with_wrong_credentials_is_401_without_cookie_or_tokens():
    harness = _Harness()
    harness.users.login.side_effect = UnauthorizedException(INVALID_CREDENTIALS_MESSAGE)

    response = harness.client.post(f"{AUTH_PATH}/login", json={"email": EMAIL, "password": "wrong"})

    assert response.status_code == 401
    assert response.json() == {"error": "unauthorized", "message": INVALID_CREDENTIALS_MESSAGE}
    assert response.headers.get_list("set-cookie") == []
    harness.tokens.create_tokens.assert_not_awaited()


@pytest.mark.parametrize("body", [{"email": EMAIL}, {"password": PASSWORD}, {}])
def test_login_with_missing_fields_is_400(body):
    harness = _Harness()

    response = harness.client.post(f"{AUTH_PATH}/login", json=body)

    assert response.status_code == 400
    assert response.json()["error"] == "validation_error"
    harness.users.login.assert_not_awaited()


# ---------------------------------------------------------------- me


def test_me_returns_the_current_user_unwrapped():
    harness = _Harness(found=_user())
    token = tokens.create_access_token(str(USER_ID))

    response = harness.client.get(f"{AUTH_PATH}/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == {
        "id": str(USER_ID),
        "email": EMAIL,
        "skill_level": "Complete Beginner",
    }


def test_me_returns_null_skill_level():
    harness = _Harness(found=_user(skill_level=None))
    token = tokens.create_access_token(str(USER_ID))

    response = harness.client.get(f"{AUTH_PATH}/me", headers={"Authorization": f"Bearer {token}"})

    assert response.json()["skill_level"] is None


def test_me_never_exposes_the_password_hash():
    harness = _Harness(found=_user())
    token = tokens.create_access_token(str(USER_ID))

    response = harness.client.get(f"{AUTH_PATH}/me", headers={"Authorization": f"Bearer {token}"})

    assert set(response.json()) == {"id", "email", "skill_level"}


def test_me_without_authorization_is_401():
    harness = _Harness(found=_user())

    response = harness.client.get(f"{AUTH_PATH}/me")

    assert response.status_code == 401
    assert response.json()["error"] == "unauthorized"


def test_me_rejects_a_refresh_token():
    harness = _Harness(found=_user())
    token = tokens.create_refresh_token(str(USER_ID))

    response = harness.client.get(f"{AUTH_PATH}/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


# ---------------------------------------------------------------- logout


def test_logout_revokes_the_cookie_token_and_clears_the_cookie():
    harness = _Harness()

    response = harness.client.post(f"{AUTH_PATH}/logout", headers=_cookie_header("the-token"))

    assert response.status_code == 204
    assert response.content == b""
    harness.users.logout.assert_awaited_once_with("the-token")
    _assert_cookie_attributes(_refresh_cookie(response), 0)


def test_logout_without_cookie_is_still_204_and_clears_the_cookie():
    harness = _Harness()

    response = harness.client.post(f"{AUTH_PATH}/logout")

    assert response.status_code == 204
    harness.users.logout.assert_not_awaited()
    _assert_cookie_attributes(_refresh_cookie(response), 0)


def test_logout_with_empty_cookie_is_treated_as_no_cookie():
    harness = _Harness()

    response = harness.client.post(f"{AUTH_PATH}/logout", headers={"Cookie": "refresh_token="})

    assert response.status_code == 204
    harness.users.logout.assert_not_awaited()


def test_logout_needs_no_authorization_header():
    harness = _Harness()

    response = harness.client.post(f"{AUTH_PATH}/logout", headers=_cookie_header("anything"))

    assert response.status_code == 204


def test_logout_clearing_cookie_keeps_the_secure_flag_when_configured(monkeypatch):
    monkeypatch.setenv("COOKIE_SECURE", "true")
    harness = _Harness()

    response = harness.client.post(f"{AUTH_PATH}/logout", headers=_cookie_header("t"))

    assert "; secure" in _refresh_cookie(response)


# ---------------------------------------------------------------- refresh


def test_refresh_rotates_the_cookie_token_and_returns_a_new_access_token():
    harness = _Harness()
    pair = _pair()
    harness.tokens.rotate.return_value = pair

    response = harness.client.post(f"{AUTH_PATH}/refresh", headers=_cookie_header("old-token"))

    assert response.status_code == 200
    assert response.json() == {
        "access_token": pair.access_token,
        "token_type": "bearer",
        "expires_in": 900,
    }
    harness.tokens.rotate.assert_awaited_once_with("old-token")


def test_refresh_sets_the_new_refresh_token_cookie():
    harness = _Harness()
    pair = _pair()
    harness.tokens.rotate.return_value = pair

    response = harness.client.post(f"{AUTH_PATH}/refresh", headers=_cookie_header("old-token"))

    cookie = _refresh_cookie(response)
    assert cookie.startswith(f"refresh_token={pair.refresh_token.lower()}")
    _assert_cookie_attributes(cookie, SEVEN_DAYS)
    assert pair.refresh_token not in response.text


def test_refresh_without_cookie_is_401_and_clears_the_stale_cookie():
    harness = _Harness()

    response = harness.client.post(f"{AUTH_PATH}/refresh")

    assert response.status_code == 401
    assert response.json()["error"] == "unauthorized"
    harness.tokens.rotate.assert_not_awaited()
    _assert_cookie_attributes(_refresh_cookie(response), 0)


def test_refresh_with_empty_cookie_is_401():
    harness = _Harness()

    response = harness.client.post(f"{AUTH_PATH}/refresh", headers={"Cookie": "refresh_token="})

    assert response.status_code == 401
    harness.tokens.rotate.assert_not_awaited()


@pytest.mark.parametrize("message", [INVALID_TOKEN_MESSAGE, "로그인 시간이 만료되었습니다."])
def test_refresh_with_a_rejected_token_is_401_and_clears_the_cookie(message):
    harness = _Harness()
    harness.tokens.rotate.side_effect = UnauthorizedException(message)

    response = harness.client.post(f"{AUTH_PATH}/refresh", headers=_cookie_header("bad"))

    assert response.status_code == 401
    assert response.json() == {"error": "unauthorized", "message": message}
    _assert_cookie_attributes(_refresh_cookie(response), 0)


# ---------------------------------------------------------------- cookie settings


@pytest.mark.parametrize("raw", ["true", "TRUE", "1", "yes", "on", " True "])
def test_cookie_secure_accepts_truthy_values(monkeypatch, raw):
    monkeypatch.setenv("COOKIE_SECURE", raw)
    assert auth_cookies.cookie_secure() is True


@pytest.mark.parametrize("raw", ["false", "0", "no", "off", "", "  "])
def test_cookie_secure_accepts_falsy_values_and_blank(monkeypatch, raw):
    monkeypatch.setenv("COOKIE_SECURE", raw)
    assert auth_cookies.cookie_secure() is False


def test_cookie_secure_defaults_to_false_when_unset():
    assert auth_cookies.cookie_secure() is False


def test_cookie_secure_rejects_garbage(monkeypatch):
    monkeypatch.setenv("COOKIE_SECURE", "maybe")
    with pytest.raises(ValueError, match="COOKIE_SECURE"):
        auth_cookies.cookie_secure()
