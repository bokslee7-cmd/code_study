import pytest
from src.db import config as db_config
from src.db import session as db_session

POOL_ENV_VARS = (
    "DB_POOL_SIZE",
    "DB_MAX_OVERFLOW",
    "DB_POOL_TIMEOUT",
    "DB_POOL_RECYCLE",
    "DB_ECHO",
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in POOL_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    db_session.get_engine.cache_clear()
    db_session.get_session_factory.cache_clear()
    yield
    db_session.get_engine.cache_clear()
    db_session.get_session_factory.cache_clear()


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("postgresql://u:p@h:5432/d", "postgresql+asyncpg://u:p@h:5432/d"),
        ("postgres://u:p@h:5432/d", "postgresql+asyncpg://u:p@h:5432/d"),
        ("postgresql+asyncpg://u:p@h:5432/d", "postgresql+asyncpg://u:p@h:5432/d"),
    ],
)
def test_to_async_url(raw, expected):
    assert db_config.to_async_url(raw) == expected


def test_get_database_url_requires_env(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        db_config.get_database_url()


def test_get_database_url_reads_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h/d")
    assert db_config.get_database_url() == "postgresql://u:p@h/d"


def test_pool_settings_defaults():
    settings = db_config.load_pool_settings()
    assert settings == db_config.PoolSettings(
        pool_size=5, max_overflow=10, pool_timeout=30, pool_recycle=1800, echo=False
    )


def test_pool_settings_from_env(monkeypatch):
    monkeypatch.setenv("DB_POOL_SIZE", "20")
    monkeypatch.setenv("DB_MAX_OVERFLOW", "0")
    monkeypatch.setenv("DB_POOL_TIMEOUT", "5")
    monkeypatch.setenv("DB_POOL_RECYCLE", "600")
    monkeypatch.setenv("DB_ECHO", "true")
    settings = db_config.load_pool_settings()
    assert settings.pool_size == 20
    assert settings.max_overflow == 0
    assert settings.pool_timeout == 5
    assert settings.pool_recycle == 600
    assert settings.echo is True


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("DB_POOL_SIZE", "abc"),
        ("DB_POOL_SIZE", "0"),
        ("DB_MAX_OVERFLOW", "-1"),
        ("DB_POOL_TIMEOUT", "0"),
        ("DB_POOL_RECYCLE", "-5"),
        ("DB_ECHO", "maybe"),
    ],
)
def test_pool_settings_rejects_invalid_values(monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    with pytest.raises(ValueError, match=name):
        db_config.load_pool_settings()


def test_pool_recycle_zero_is_allowed_to_disable(monkeypatch):
    monkeypatch.setenv("DB_POOL_RECYCLE", "0")
    assert db_config.load_pool_settings().pool_recycle == 0


def test_engine_kwargs_maps_to_sqlalchemy_arguments():
    kwargs = db_config.engine_kwargs(db_config.load_pool_settings())
    assert kwargs == {
        "pool_size": 5,
        "max_overflow": 10,
        "pool_timeout": 30,
        "pool_recycle": 1800,
        "pool_pre_ping": True,
        "echo": False,
    }


def test_pool_recycle_zero_becomes_disabled_value():
    settings = db_config.PoolSettings(
        pool_size=1, max_overflow=0, pool_timeout=1, pool_recycle=0, echo=False
    )
    assert db_config.engine_kwargs(settings)["pool_recycle"] == -1


def test_engine_applies_pool_settings(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost:5432/d")
    monkeypatch.setenv("DB_POOL_SIZE", "7")
    monkeypatch.setenv("DB_MAX_OVERFLOW", "3")
    monkeypatch.setenv("DB_POOL_TIMEOUT", "12")
    monkeypatch.setenv("DB_POOL_RECYCLE", "900")
    engine = db_session.get_engine()
    pool = engine.pool
    assert pool.size() == 7
    assert pool._max_overflow == 3
    assert pool._timeout == 12
    assert pool._recycle == 900
    assert pool._pre_ping is True


@pytest.mark.parametrize("raw", ["0", "false", "No", "OFF"])
def test_db_echo_accepts_false_values(monkeypatch, raw):
    monkeypatch.setenv("DB_ECHO", raw)
    assert db_config.load_pool_settings().echo is False


def test_blank_values_fall_back_to_defaults(monkeypatch):
    monkeypatch.setenv("DB_POOL_SIZE", " ")
    monkeypatch.setenv("DB_ECHO", "")
    assert db_config.load_pool_settings() == db_config.PoolSettings()
