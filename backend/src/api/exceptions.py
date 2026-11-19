import logging
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import RequestResponseEndpoint

logger = logging.getLogger(__name__)

VALIDATION_ERROR = "validation_error"
VALIDATION_MESSAGE = "입력값이 올바르지 않습니다. 입력한 내용을 확인한 뒤 다시 시도하세요."
INTERNAL_ERROR = "internal_server_error"
INTERNAL_MESSAGE = "서버 오류가 발생했습니다. 잠시 후 다시 시도하세요. 계속되면 문의하세요."

# status -> (error code, default Korean message)
_STATUS_ERRORS: dict[int, tuple[str, str]] = {
    400: ("bad_request", "잘못된 요청입니다. 입력한 내용을 확인한 뒤 다시 시도하세요."),
    401: ("unauthorized", "로그인이 필요합니다. 로그인 페이지로 이동합니다."),
    403: ("forbidden", "이 작업을 수행할 권한이 없습니다."),
    404: ("not_found", "요청한 페이지를 찾을 수 없습니다."),
    405: ("method_not_allowed", "허용되지 않는 요청 방식입니다."),
    409: ("conflict", "요청이 현재 상태와 충돌합니다. 새로고침한 뒤 다시 시도하세요."),
    410: ("gone", "요청한 항목이 영구적으로 삭제되었습니다."),
    429: ("rate_limit_exceeded", "요청이 너무 많습니다. 잠시 후 다시 시도하세요."),
    500: (INTERNAL_ERROR, INTERNAL_MESSAGE),
}
_CLIENT_FALLBACK = ("client_error", "요청을 처리할 수 없습니다. 입력 내용을 확인하세요.")
_SERVER_FALLBACK = ("server_error", INTERNAL_MESSAGE)


class ErrorResponse(BaseModel):
    error: str
    message: str
    details: dict[str, Any] | None = None
    suggestion: str | None = None


class AppError(Exception):
    """Domain error rendered as ErrorResponse with the given HTTP status."""

    def __init__(
        self,
        status_code: int,
        error: str,
        message: str,
        details: dict[str, Any] | None = None,
        suggestion: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error = error
        self.message = message
        self.details = details
        self.suggestion = suggestion


class NotFoundException(AppError):
    def __init__(
        self,
        message: str = _STATUS_ERRORS[404][1],
        details: dict[str, Any] | None = None,
        suggestion: str | None = None,
    ) -> None:
        super().__init__(404, _STATUS_ERRORS[404][0], message, details, suggestion)


class UnauthorizedException(AppError):
    def __init__(
        self,
        message: str = _STATUS_ERRORS[401][1],
        details: dict[str, Any] | None = None,
        suggestion: str | None = None,
    ) -> None:
        super().__init__(401, _STATUS_ERRORS[401][0], message, details, suggestion)


class ForbiddenException(AppError):
    def __init__(
        self,
        message: str = _STATUS_ERRORS[403][1],
        details: dict[str, Any] | None = None,
        suggestion: str | None = None,
    ) -> None:
        super().__init__(403, _STATUS_ERRORS[403][0], message, details, suggestion)


class ConflictException(AppError):
    def __init__(
        self,
        message: str = _STATUS_ERRORS[409][1],
        details: dict[str, Any] | None = None,
        suggestion: str | None = None,
    ) -> None:
        super().__init__(409, _STATUS_ERRORS[409][0], message, details, suggestion)


def _error_response(
    status_code: int,
    body: ErrorResponse,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=body.model_dump(exclude_none=True),
        headers=headers,
    )


def _default_error(status_code: int) -> tuple[str, str]:
    if status_code in _STATUS_ERRORS:
        return _STATUS_ERRORS[status_code]
    return _SERVER_FALLBACK if status_code >= 500 else _CLIENT_FALLBACK


async def app_error_handler(request: Request, exc: Exception) -> Response:
    assert isinstance(exc, AppError)
    body = ErrorResponse(
        error=exc.error,
        message=exc.message,
        details=jsonable_encoder(exc.details) if exc.details is not None else None,
        suggestion=exc.suggestion,
    )
    return _error_response(exc.status_code, body)


async def http_exception_handler(request: Request, exc: Exception) -> Response:
    assert isinstance(exc, StarletteHTTPException)
    error, default_message = _default_error(exc.status_code)
    # Bare HTTPException(status) carries the English reason phrase; replace it with Korean.
    custom = isinstance(exc.detail, str) and exc.detail != _reason_phrase(exc.status_code)
    message = exc.detail if custom else default_message
    body = ErrorResponse(error=error, message=message)
    return _error_response(exc.status_code, body, dict(exc.headers) if exc.headers else None)


def _reason_phrase(status_code: int) -> str:
    try:
        return HTTPStatus(status_code).phrase
    except ValueError:
        return ""


async def validation_error_handler(request: Request, exc: Exception) -> Response:
    assert isinstance(exc, RequestValidationError)
    # Only location and message are exposed: pydantic's `input` would echo submitted values.
    errors = [
        {"field": ".".join(str(part) for part in err["loc"]), "message": err["msg"]}
        for err in exc.errors()
    ]
    body = ErrorResponse(
        error=VALIDATION_ERROR, message=VALIDATION_MESSAGE, details={"errors": errors}
    )
    return _error_response(400, body)


async def unhandled_exception_middleware(
    request: Request, call_next: RequestResponseEndpoint
) -> Response:
    try:
        return await call_next(request)
    except Exception:
        request_id = getattr(request.state, "request_id", "-")
        logger.exception(
            "Unhandled exception: %s %s (request_id=%s)",
            request.method,
            request.url.path,
            request_id,
        )
        body = ErrorResponse(error=INTERNAL_ERROR, message=INTERNAL_MESSAGE)
        return _error_response(500, body)


def register_exception_handlers(app: FastAPI) -> None:
    """Call before adding other middleware: the catch-all must sit innermost so that
    request-id and CORS middleware still wrap the 500 response."""
    app.middleware("http")(unhandled_exception_middleware)
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
