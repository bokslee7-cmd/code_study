import os
import re
import uuid

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import RequestResponseEndpoint

from src.api.exceptions import register_exception_handlers
from src.api.router import create_api_router

DEFAULT_ORIGINS = "http://localhost:5173"
REQUEST_ID_HEADER = "X-Request-ID"
_VALID_REQUEST_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")


def get_allowed_origins() -> list[str]:
    """Whitelist from ALLOWED_ORIGINS (comma-separated). Wildcard is refused: cookies are used."""
    raw = os.environ.get("ALLOWED_ORIGINS", "").strip() or DEFAULT_ORIGINS
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    if "*" in origins:
        raise ValueError("ALLOWED_ORIGINS must list explicit origins; '*' is not allowed")
    return origins


async def request_id_middleware(request: Request, call_next: RequestResponseEndpoint) -> Response:
    incoming = request.headers.get(REQUEST_ID_HEADER, "")
    request_id = incoming if _VALID_REQUEST_ID.fullmatch(incoming) else uuid.uuid4().hex
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers[REQUEST_ID_HEADER] = request_id
    return response


def create_app() -> FastAPI:
    app = FastAPI(title="AI Code Learning Platform", version="0.1.0")

    # Registered first so the catch-all sits innermost: request id and CORS then cover 500s too.
    register_exception_handlers(app)
    app.middleware("http")(request_id_middleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_allowed_origins(),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", REQUEST_ID_HEADER],
        expose_headers=[REQUEST_ID_HEADER],
    )

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(create_api_router())

    return app


app = create_app()
