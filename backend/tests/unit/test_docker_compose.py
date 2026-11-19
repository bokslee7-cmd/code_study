from pathlib import Path

import pytest
import yaml

COMPOSE_PATH = Path(__file__).resolve().parents[3] / "docker-compose.yml"


@pytest.fixture(scope="module")
def compose() -> dict:
    assert COMPOSE_PATH.exists(), "docker-compose.yml이 프로젝트 루트에 있어야 한다"
    return yaml.safe_load(COMPOSE_PATH.read_text(encoding="utf-8"))


def test_defines_db_and_redis_services(compose):
    assert {"db", "redis"} <= set(compose["services"])


def test_postgres_is_version_15_or_higher(compose):
    image = compose["services"]["db"]["image"]
    assert image.startswith("postgres:")
    assert int(image.split(":")[1].split("-")[0].split(".")[0]) >= 15


def test_redis_is_version_7_or_higher(compose):
    image = compose["services"]["redis"]["image"]
    assert image.startswith("redis:")
    assert int(image.split(":")[1].split("-")[0].split(".")[0]) >= 7


def test_exposes_default_ports(compose):
    assert any(str(p).endswith(":5432") for p in compose["services"]["db"]["ports"])
    assert any(str(p).endswith(":6379") for p in compose["services"]["redis"]["ports"])


def test_postgres_credentials_come_from_env(compose):
    env = compose["services"]["db"]["environment"]
    for key in ("POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB"):
        assert str(env[key]).startswith("${" + key), f"{key}는 환경변수로 주입해야 한다"


def test_data_is_persisted_with_named_volumes(compose):
    assert {"postgres_data", "redis_data"} <= set(compose["volumes"])


def test_services_have_healthchecks(compose):
    for name in ("db", "redis"):
        assert "healthcheck" in compose["services"][name]
