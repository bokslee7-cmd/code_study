import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker
from src.db import session as db_session


@pytest.fixture(autouse=True)
def clear_caches():
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
    assert db_session.to_async_url(raw) == expected


def test_get_database_url_requires_env(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        db_session.get_database_url()


def test_get_engine_uses_env_and_is_cached(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost:5432/d")
    engine = db_session.get_engine()
    assert isinstance(engine, AsyncEngine)
    assert engine.url.drivername == "postgresql+asyncpg"
    assert engine.url.database == "d"
    assert db_session.get_engine() is engine
    assert engine.pool._pre_ping is True


def test_session_factory_does_not_expire_on_commit(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost:5432/d")
    factory = db_session.get_session_factory()
    assert isinstance(factory, async_sessionmaker)
    assert factory.kw["expire_on_commit"] is False
