import re

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from src import main

ORIGIN = "http://localhost:5173"


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)


@pytest.fixture
def client():
    return TestClient(main.create_app())


def test_create_app_returns_fastapi_with_metadata():
    app = main.create_app()
    assert isinstance(app, FastAPI)
    assert app.title == "AI Code Learning Platform"
    assert main.app.title == app.title


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_unknown_route_is_404(client):
    assert client.get("/nope").status_code == 404


def test_default_origins_allow_vite_dev_server():
    assert main.get_allowed_origins() == [ORIGIN]


def test_origins_parsed_from_env(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", " https://a.example.com, https://b.example.com ,,")
    assert main.get_allowed_origins() == ["https://a.example.com", "https://b.example.com"]


def test_blank_origins_env_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "  ")
    assert main.get_allowed_origins() == [ORIGIN]


def test_wildcard_origin_is_rejected(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://a.example.com,*")
    with pytest.raises(ValueError, match="ALLOWED_ORIGINS"):
        main.get_allowed_origins()


def test_cors_allows_whitelisted_origin_with_credentials(client):
    response = client.get("/health", headers={"Origin": ORIGIN})
    assert response.headers["access-control-allow-origin"] == ORIGIN
    assert response.headers["access-control-allow-credentials"] == "true"


def test_cors_does_not_allow_other_origin(client):
    response = client.get("/health", headers={"Origin": "https://evil.example.com"})
    assert "access-control-allow-origin" not in response.headers


def test_cors_preflight(client):
    response = client.options(
        "/health",
        headers={
            "Origin": ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-request-id",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ORIGIN
    assert "POST" in response.headers["access-control-allow-methods"]


def test_cors_preflight_rejects_other_origin(client):
    response = client.options(
        "/health",
        headers={"Origin": "https://evil.example.com", "Access-Control-Request-Method": "GET"},
    )
    assert response.status_code == 400


def test_cors_env_is_applied(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://app.example.com")
    client = TestClient(main.create_app())
    ok = client.get("/health", headers={"Origin": "https://app.example.com"})
    assert ok.headers["access-control-allow-origin"] == "https://app.example.com"
    assert (
        "access-control-allow-origin"
        not in client.get("/health", headers={"Origin": ORIGIN}).headers
    )


def test_response_gets_generated_request_id(client):
    response = client.get("/health")
    assert re.fullmatch(r"[0-9a-f]{32}", response.headers["x-request-id"])
    assert response.headers["x-request-id"] != client.get("/health").headers["x-request-id"]


def test_valid_incoming_request_id_is_kept(client):
    response = client.get("/health", headers={"X-Request-ID": "abc-123_DEF"})
    assert response.headers["x-request-id"] == "abc-123_DEF"


@pytest.mark.parametrize("bad", ["a" * 65, "has space", "a/b", "a;b"])
def test_invalid_incoming_request_id_is_replaced(client, bad):
    response = client.get("/health", headers={"X-Request-ID": bad})
    assert re.fullmatch(r"[0-9a-f]{32}", response.headers["x-request-id"])


def test_request_id_header_exposed_to_browsers(client):
    response = client.get("/health", headers={"Origin": ORIGIN})
    assert "x-request-id" in response.headers["access-control-expose-headers"].lower()


def test_request_id_present_on_404(client):
    assert "x-request-id" in client.get("/nope").headers
