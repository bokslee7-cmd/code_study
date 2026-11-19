from fastapi import APIRouter

from src.api import auth, documents, health, projects, tasks, test_errors

API_V1_PREFIX = "/api/v1"


def create_api_router() -> APIRouter:
    """Root router for /api/v1. Feature routers (auth, projects, ...) are included here."""
    router = APIRouter(prefix=API_V1_PREFIX)
    router.include_router(health.router)
    router.include_router(auth.router)
    router.include_router(projects.router)
    router.include_router(tasks.router)
    router.include_router(documents.router)
    router.include_router(test_errors.router)
    return router
