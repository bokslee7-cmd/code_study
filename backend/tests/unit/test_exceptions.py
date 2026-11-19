import logging

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel
from src import main
from src.api import exceptions

ORIGIN = "http://localhost:5173"


class Payload(BaseModel):
    title: str


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)


@pytest.fixture
def app() -> FastAPI:
    app = main.create_app()

    @app.get("/_t/app-error")
    async def app_error() -> None:
        raise exceptions.AppError(
            status_code=413,
            error="file_too_large",
            message="파일 크기가 10MB를 초과합니다.",
            details={"max_size_mb": 10, "uploaded_size_mb": 15.3},
            suggestion="더 작은 파일을 선택하세요.",
        )

    @app.get("/_t/app-error-minimal")
    async def app_error_minimal() -> None:
        raise exceptions.AppError(status_code=409, error="conflict", message="이미 존재합니다.")

    @app.get("/_t/http-404")
    async def http_404() -> None:
        raise HTTPException(status_code=404)

    @app.get("/_t/http-custom")
    async def http_custom() -> None:
        raise HTTPException(status_code=403, detail="이 프로젝트에 접근할 권한이 없습니다.")

    @app.get("/_t/http-401")
    async def http_401() -> None:
        raise HTTPException(status_code=401, headers={"WWW-Authenticate": "Bearer"})

    @app.get("/_t/http-418")
    async def http_418() -> None:
        raise HTTPException(status_code=418)

    @app.get("/_t/http-503")
    async def http_503() -> None:
        raise HTTPException(status_code=503)

    @app.get("/_t/http-599")
    async def http_599() -> None:
        raise HTTPException(status_code=599, detail="non-standard status")

    @app.get("/_t/query")
    async def query(n: int) -> dict[str, int]:
        return {"n": n}

    @app.post("/_t/body")
    async def body(payload: Payload) -> dict[str, str]:
        return {"title": payload.title}

    @app.get("/_t/boom")
    async def boom() -> None:
        raise RuntimeError("secret-db-password")

    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


def test_error_response_omits_unset_optional_fields():
    body = exceptions.ErrorResponse(error="not_found", message="없음").model_dump(exclude_none=True)
    assert body == {"error": "not_found", "message": "없음"}


def test_app_error_keeps_all_fields():
    err = exceptions.AppError(
        status_code=400, error="bad", message="m", details={"a": 1}, suggestion="s"
    )
    assert isinstance(err, Exception)
    assert (err.status_code, err.error, err.message, err.details, err.suggestion) == (
        400,
        "bad",
        "m",
        {"a": 1},
        "s",
    )


def test_app_error_is_rendered_with_full_error_format(client):
    response = client.get("/_t/app-error")
    assert response.status_code == 413
    assert response.json() == {
        "error": "file_too_large",
        "message": "파일 크기가 10MB를 초과합니다.",
        "details": {"max_size_mb": 10, "uploaded_size_mb": 15.3},
        "suggestion": "더 작은 파일을 선택하세요.",
    }


def test_app_error_without_details_omits_them(client):
    response = client.get("/_t/app-error-minimal")
    assert response.status_code == 409
    assert response.json() == {"error": "conflict", "message": "이미 존재합니다."}


def test_http_exception_gets_error_code_and_korean_message(client):
    response = client.get("/_t/http-404")
    assert response.status_code == 404
    assert response.json() == {
        "error": "not_found",
        "message": "요청한 페이지를 찾을 수 없습니다.",
    }


def test_unknown_route_uses_error_format(client):
    response = client.get("/api/v1/unknown")
    assert response.status_code == 404
    assert response.json()["error"] == "not_found"


def test_http_exception_with_custom_detail_keeps_detail_as_message(client):
    response = client.get("/_t/http-custom")
    assert response.status_code == 403
    assert response.json() == {
        "error": "forbidden",
        "message": "이 프로젝트에 접근할 권한이 없습니다.",
    }


def test_http_exception_headers_are_preserved(client):
    response = client.get("/_t/http-401")
    assert response.status_code == 401
    assert response.json()["error"] == "unauthorized"
    assert response.headers["www-authenticate"] == "Bearer"


def test_method_not_allowed_keeps_allow_header(client):
    response = client.post("/health")
    assert response.status_code == 405
    assert response.json()["error"] == "method_not_allowed"
    assert "GET" in response.headers["allow"]


@pytest.mark.parametrize(
    ("path", "status", "error"),
    [
        ("/_t/http-418", 418, "client_error"),
        ("/_t/http-503", 503, "server_error"),
        ("/_t/http-599", 599, "server_error"),
    ],
)
def test_unmapped_status_falls_back_to_class_error(client, path, status, error):
    response = client.get(path)
    assert response.status_code == status
    assert response.json()["error"] == error
    assert response.json()["message"]


def test_query_validation_error_is_400_with_field_details(client):
    response = client.get("/_t/query", params={"n": "not-a-number"})
    assert response.status_code == 400
    body = response.json()
    assert body["error"] == "validation_error"
    assert body["message"]
    assert [e["field"] for e in body["details"]["errors"]] == ["query.n"]
    assert body["details"]["errors"][0]["message"]


def test_body_validation_error_lists_field_path(client):
    response = client.post("/_t/body", json={})
    assert response.status_code == 400
    assert response.json()["details"]["errors"][0]["field"] == "body.title"


def test_validation_error_does_not_echo_submitted_value(client):
    response = client.get("/_t/query", params={"n": "leaky-value"})
    assert "leaky-value" not in response.text


def test_valid_request_is_unaffected(client):
    assert client.get("/_t/query", params={"n": 3}).json() == {"n": 3}


def test_unhandled_exception_returns_generic_500(client):
    response = client.get("/_t/boom")
    assert response.status_code == 500
    body = response.json()
    assert body["error"] == "internal_server_error"
    assert "서버 오류" in body["message"]
    assert "secret-db-password" not in response.text


def test_unhandled_exception_keeps_request_id_and_cors_headers(client):
    response = client.get("/_t/boom", headers={"Origin": ORIGIN, "X-Request-ID": "req-500"})
    assert response.status_code == 500
    assert response.headers["x-request-id"] == "req-500"
    assert response.headers["access-control-allow-origin"] == ORIGIN


def test_unhandled_exception_is_logged_with_request_id(client, caplog):
    with caplog.at_level(logging.ERROR, logger=exceptions.__name__):
        client.get("/_t/boom", headers={"X-Request-ID": "req-log"})
    record = next(r for r in caplog.records if r.name == exceptions.__name__)
    assert "req-log" in record.getMessage()
    assert record.exc_info is not None


def test_client_errors_are_not_logged_as_errors(client, caplog):
    with caplog.at_level(logging.ERROR, logger=exceptions.__name__):
        client.get("/_t/http-404")
        client.get("/_t/query", params={"n": "x"})
    assert caplog.records == []


def test_register_exception_handlers_can_be_applied_to_plain_app():
    plain = FastAPI()
    exceptions.register_exception_handlers(plain)

    @plain.get("/boom")
    async def boom() -> None:
        raise exceptions.AppError(status_code=410, error="gone", message="삭제되었습니다.")

    response = TestClient(plain).get("/boom")
    assert response.status_code == 410
    assert response.json() == {"error": "gone", "message": "삭제되었습니다."}
