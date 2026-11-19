import pytest
from fastapi.testclient import TestClient
from src import main
from src.api import exceptions


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    return TestClient(main.create_app())


def test_without_type_returns_success(client):
    response = client.get("/api/v1/test-errors")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize(
    ("error_type", "status_code", "error"),
    [
        ("notfound", 404, "not_found"),
        ("forbidden", 403, "forbidden"),
        ("conflict", 409, "conflict"),
    ],
)
def test_type_raises_matching_exception(client, error_type, status_code, error):
    response = client.get("/api/v1/test-errors", params={"type": error_type})
    assert response.status_code == status_code
    body = response.json()
    assert body["error"] == error
    assert body["message"]


def test_unknown_type_is_validation_error(client):
    response = client.get("/api/v1/test-errors", params={"type": "bogus"})
    assert response.status_code == 400
    assert response.json()["error"] == "validation_error"


@pytest.mark.parametrize(
    ("exc_class", "status_code", "error"),
    [
        (exceptions.NotFoundException, 404, "not_found"),
        (exceptions.ForbiddenException, 403, "forbidden"),
        (exceptions.ConflictException, 409, "conflict"),
    ],
)
def test_exception_classes_are_app_errors_with_defaults(exc_class, status_code, error):
    exc = exc_class()
    assert isinstance(exc, exceptions.AppError)
    assert exc.status_code == status_code
    assert exc.error == error
    assert exc.message


def test_exception_accepts_custom_message_details_and_suggestion():
    exc = exceptions.NotFoundException("프로젝트가 없습니다.", {"id": 1}, "목록을 확인하세요.")
    assert exc.message == "프로젝트가 없습니다."
    assert exc.details == {"id": 1}
    assert exc.suggestion == "목록을 확인하세요."
