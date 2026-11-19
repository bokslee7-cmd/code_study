import uuid
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.api.dependencies import CurrentUser, get_current_user
from src.api.exceptions import register_exception_handlers
from src.db.session import get_session
from src.models import User
from src.services.auth.token_service import INVALID_TOKEN_MESSAGE, TOKEN_EXPIRED_MESSAGE
from src.utils import jwt as tokens

SECRET = "test-secret-key-that-is-at-least-32-bytes-long"
USER_ID = uuid.uuid4()
LOGIN_REQUIRED_MESSAGE = "로그인이 필요합니다. 로그인 페이지로 이동합니다."


@pytest.fixture(autouse=True)
def secret_env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", SECRET)
    monkeypatch.delenv("JWT_ACCESS_TOKEN_MINUTES", raising=False)
    monkeypatch.delenv("JWT_REFRESH_TOKEN_DAYS", raising=False)


class _Harness:
    """A throwaway app with one protected route, backed by a session double."""

    def __init__(self, found: User | None) -> None:
        result = MagicMock()
        result.scalar_one_or_none.return_value = found
        self.session = MagicMock()
        self.session.execute = AsyncMock(return_value=result)
        self.sessions_opened = 0

        async def fake_get_session():
            self.sessions_opened += 1
            yield self.session

        app = FastAPI()
        register_exception_handlers(app)
        app.dependency_overrides[get_session] = fake_get_session

        @app.get("/protected")
        async def protected(user: CurrentUser) -> dict[str, str]:
            return {"id": str(user.id), "email": user.email}

        self.client = TestClient(app, raise_server_exceptions=False)

    def sql(self) -> str:
        statement = self.session.execute.call_args.args[0]
        return str(statement.compile(compile_kwargs={"literal_binds": True}))


def _user() -> User:
    return User(id=USER_ID, email="learner@example.com", password_hash="x")


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_valid_access_token_gives_the_route_the_current_user():
    harness = _Harness(found=_user())
    token = tokens.create_access_token(str(USER_ID))

    response = harness.client.get("/protected", headers=_bearer(token))

    assert response.status_code == 200
    assert response.json() == {"id": str(USER_ID), "email": "learner@example.com"}


def test_user_is_looked_up_by_the_token_subject():
    harness = _Harness(found=_user())

    harness.client.get("/protected", headers=_bearer(tokens.create_access_token(str(USER_ID))))

    assert USER_ID.hex in harness.sql()


def test_the_route_and_the_dependency_share_one_session_per_request():
    harness = _Harness(found=_user())

    harness.client.get("/protected", headers=_bearer(tokens.create_access_token(str(USER_ID))))

    assert harness.sessions_opened == 1


def test_missing_authorization_header_is_401_login_required():
    harness = _Harness(found=_user())

    response = harness.client.get("/protected")

    assert response.status_code == 401
    assert response.json() == {"error": "unauthorized", "message": LOGIN_REQUIRED_MESSAGE}
    harness.session.execute.assert_not_awaited()


@pytest.mark.parametrize("header", ["Basic dXNlcjpwYXNz", "Bearer", "Bearer ", "token abc"])
def test_authorization_header_that_is_not_a_bearer_token_is_401(header):
    harness = _Harness(found=_user())

    response = harness.client.get("/protected", headers={"Authorization": header})

    assert response.status_code == 401
    assert response.json()["error"] == "unauthorized"
    harness.session.execute.assert_not_awaited()


def test_malformed_token_is_401_invalid():
    harness = _Harness(found=_user())

    response = harness.client.get("/protected", headers=_bearer("not-a-jwt"))

    assert response.status_code == 401
    assert response.json()["message"] == INVALID_TOKEN_MESSAGE
    harness.session.execute.assert_not_awaited()


def test_expired_token_is_401_with_expiry_message():
    harness = _Harness(found=_user())
    token = tokens.create_access_token(str(USER_ID), expires_delta=timedelta(seconds=-5))

    response = harness.client.get("/protected", headers=_bearer(token))

    assert response.status_code == 401
    assert response.json()["message"] == TOKEN_EXPIRED_MESSAGE


def test_refresh_token_is_not_accepted_as_an_access_token():
    harness = _Harness(found=_user())

    response = harness.client.get(
        "/protected", headers=_bearer(tokens.create_refresh_token(str(USER_ID)))
    )

    assert response.status_code == 401
    assert response.json()["message"] == INVALID_TOKEN_MESSAGE
    harness.session.execute.assert_not_awaited()


def test_valid_token_of_a_deleted_user_is_401_invalid():
    harness = _Harness(found=None)

    response = harness.client.get(
        "/protected", headers=_bearer(tokens.create_access_token(str(USER_ID)))
    )

    assert response.status_code == 401
    assert response.json()["message"] == INVALID_TOKEN_MESSAGE


def test_get_current_user_is_the_dependency_behind_current_user():
    assert CurrentUser.__metadata__[0].dependency is get_current_user
