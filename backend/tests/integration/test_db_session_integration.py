import asyncio
import socket
import uuid
from collections.abc import Iterator

import asyncpg
import pytest
from sqlalchemy import text
from src.db import session as db_session

ADMIN_DSN = "postgresql://postgres:postgres@localhost:5432/postgres"


def _db_reachable() -> bool:
    try:
        with socket.create_connection(("localhost", 5432), timeout=1):
            return True
    except OSError:
        return False


pytestmark = pytest.mark.skipif(not _db_reachable(), reason="PostgreSQL(localhost:5432) 필요")


async def _admin(dsn: str, sql: str) -> None:
    conn = await asyncpg.connect(dsn)
    try:
        await conn.execute(sql)
    finally:
        await conn.close()


async def _count(dsn: str) -> int:
    conn = await asyncpg.connect(dsn)
    try:
        return int(await conn.fetchval("SELECT count(*) FROM items"))
    finally:
        await conn.close()


@pytest.fixture()
def dsn(monkeypatch) -> Iterator[str]:
    name = f"session_test_{uuid.uuid4().hex[:8]}"
    asyncio.run(_admin(ADMIN_DSN, f'CREATE DATABASE "{name}"'))
    url = f"postgresql://postgres:postgres@localhost:5432/{name}"
    asyncio.run(_admin(url, "CREATE TABLE items (id SERIAL PRIMARY KEY, name TEXT NOT NULL)"))
    monkeypatch.setenv("DATABASE_URL", url)
    db_session.get_engine.cache_clear()
    db_session.get_session_factory.cache_clear()
    try:
        yield url
    finally:
        db_session.get_engine.cache_clear()
        db_session.get_session_factory.cache_clear()
        asyncio.run(_admin(ADMIN_DSN, f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))


async def test_get_session_executes_queries(dsn):
    gen = db_session.get_session()
    session = await anext(gen)
    assert (await session.execute(text("SELECT 1"))).scalar_one() == 1
    await gen.aclose()
    await db_session.get_engine().dispose()


async def test_get_session_commits_on_success(dsn):
    gen = db_session.get_session()
    session = await anext(gen)
    await session.execute(text("INSERT INTO items (name) VALUES ('a')"))
    with pytest.raises(StopAsyncIteration):
        await anext(gen)
    assert await _count(dsn) == 1
    await db_session.get_engine().dispose()


async def test_get_session_rolls_back_on_error(dsn):
    gen = db_session.get_session()
    session = await anext(gen)
    await session.execute(text("INSERT INTO items (name) VALUES ('a')"))
    with pytest.raises(ValueError):
        await gen.athrow(ValueError("boom"))
    assert await _count(dsn) == 0
    await db_session.get_engine().dispose()


async def test_get_session_returns_independent_sessions(dsn):
    gen1, gen2 = db_session.get_session(), db_session.get_session()
    s1, s2 = await anext(gen1), await anext(gen2)
    assert s1 is not s2
    await gen1.aclose()
    await gen2.aclose()
    await db_session.get_engine().dispose()
