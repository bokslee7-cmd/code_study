from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.db.config import (
    engine_kwargs,
    get_database_url,
    load_pool_settings,
    to_async_url,
)

__all__ = ["get_database_url", "to_async_url", "get_engine", "get_session_factory", "get_session"]


@lru_cache
def get_engine() -> AsyncEngine:
    return create_async_engine(
        to_async_url(get_database_url()), **engine_kwargs(load_pool_settings())
    )


@lru_cache
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: commit when the request succeeds, roll back on error."""
    async with get_session_factory()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
