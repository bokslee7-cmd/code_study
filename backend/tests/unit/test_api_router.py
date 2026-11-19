import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from src import main
from src.api import router as api_router_module


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)


def test_api_prefix_is_v1():
    assert api_router_module.API_V1_PREFIX == "/api/v1"


def test_create_api_router_returns_router_with_v1_prefix():
    router = api_router_module.create_api_router()
    assert isinstance(router, APIRouter)
    assert router.prefix == "/api/v1"


def test_create_api_router_returns_independent_instances():
    assert api_router_module.create_api_router() is not api_router_module.create_api_router()


def test_feature_router_is_served_under_v1_prefix():
    feature = APIRouter(prefix="/ping", tags=["ping"])

    @feature.get("")
    async def ping() -> dict[str, str]:
        return {"pong": "ok"}

    api_router = api_router_module.create_api_router()
    api_router.include_router(feature)
    app = FastAPI()
    app.include_router(api_router)
    client = TestClient(app)

    assert client.get("/api/v1/ping").json() == {"pong": "ok"}
    assert client.get("/ping").status_code == 404


def test_app_mounts_api_router_without_registering_routes_yet():
    client = TestClient(main.create_app())
    assert client.get("/api/v1/unknown").status_code == 404


def test_app_includes_routes_of_api_router(monkeypatch):
    feature = APIRouter(prefix="/ping")

    @feature.get("")
    async def ping() -> dict[str, str]:
        return {"pong": "ok"}

    def fake_create_api_router() -> APIRouter:
        router = APIRouter(prefix=api_router_module.API_V1_PREFIX)
        router.include_router(feature)
        return router

    monkeypatch.setattr(main, "create_api_router", fake_create_api_router)
    client = TestClient(main.create_app())

    assert client.get("/api/v1/ping").json() == {"pong": "ok"}


def test_health_is_served_both_unversioned_and_under_v1_prefix():
    client = TestClient(main.create_app())
    assert client.get("/health").status_code == 200
    assert client.get("/api/v1/health").status_code == 200


def test_versioned_404_still_gets_request_id():
    client = TestClient(main.create_app())
    assert "x-request-id" in client.get("/api/v1/unknown").headers
