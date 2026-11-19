import pytest
from fastapi.testclient import TestClient
from src import main

ORIGIN = "http://localhost:5173"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    return TestClient(main.create_app())


def test_v1_health_returns_ok(client):
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_unversioned_health_is_kept_for_infrastructure_checks(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_v1_health_includes_request_id(client):
    assert "x-request-id" in client.get("/api/v1/health").headers


def test_v1_health_allows_frontend_origin(client):
    response = client.get("/api/v1/health", headers={"Origin": ORIGIN})

    assert response.headers["access-control-allow-origin"] == ORIGIN


def test_v1_health_rejects_other_methods_with_error_format(client):
    response = client.post("/api/v1/health")

    assert response.status_code == 405
    assert response.json()["error"] == "method_not_allowed"
