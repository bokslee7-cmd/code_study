import asyncio
import os
import socket
import subprocess
import sys
import uuid
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import asyncpg
import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from src.models import Project, User

BACKEND = Path(__file__).resolve().parents[2]
ADMIN_DSN = "postgresql://postgres:postgres@localhost:5432/postgres"


def _db_reachable() -> bool:
    try:
        with socket.create_connection(("localhost", 5432), timeout=1):
            return True
    except OSError:
        return False


pytestmark = pytest.mark.skipif(not _db_reachable(), reason="PostgreSQL(localhost:5432) 필요")


async def _admin(sql: str) -> None:
    conn = await asyncpg.connect(ADMIN_DSN)
    try:
        await conn.execute(sql)
    finally:
        await conn.close()


@pytest.fixture()
def migrated_dsn() -> Iterator[str]:
    """실제 마이그레이션(001)을 적용한 임시 DB. ORM 모델이 이 스키마와 맞는지 확인하는 용도."""
    name = f"project_model_{uuid.uuid4().hex[:8]}"
    asyncio.run(_admin(f'CREATE DATABASE "{name}"'))
    dsn = f"postgresql://postgres:postgres@localhost:5432/{name}"
    try:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=BACKEND,
            env={**os.environ, "DATABASE_URL": dsn},
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0, result.stderr
        yield dsn
    finally:
        asyncio.run(_admin(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))


@pytest.fixture()
async def session(migrated_dsn: str) -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(migrated_dsn.replace("postgresql://", "postgresql+asyncpg://"))
    async with AsyncSession(engine, expire_on_commit=False) as db:
        yield db
    await engine.dispose()


async def _user(db: AsyncSession) -> User:
    user = User(email=f"{uuid.uuid4().hex[:8]}@example.com", password_hash="h")
    db.add(user)
    await db.flush()
    return user


async def test_new_project_gets_database_defaults(session: AsyncSession):
    user = await _user(session)
    project = Project(user_id=user.id, title="내 첫 프로젝트")
    session.add(project)
    await session.flush()
    await session.refresh(project)

    assert isinstance(project.id, uuid.UUID)
    assert project.deletion_status == "active"
    assert project.description is None
    assert project.trashed_at is None and project.scheduled_deletion_at is None
    assert project.created_at and project.updated_at and project.last_activity_at


async def test_soft_delete_fields_round_trip(session: AsyncSession):
    user = await _user(session)
    trashed_at = datetime.now(UTC)
    project = Project(
        user_id=user.id,
        title="p",
        description="설명",
        deletion_status=Project.TRASHED,
        trashed_at=trashed_at,
        scheduled_deletion_at=trashed_at + timedelta(days=30),
    )
    session.add(project)
    await session.flush()
    project_id = project.id
    session.expire(project)

    loaded = (await session.execute(select(Project).where(Project.id == project_id))).scalar_one()
    assert loaded.deletion_status == "trashed"
    assert loaded.description == "설명"
    assert loaded.scheduled_deletion_at - loaded.trashed_at == timedelta(days=30)


async def test_empty_title_is_rejected_by_the_database(session: AsyncSession):
    user = await _user(session)
    session.add(Project(user_id=user.id, title=""))
    with pytest.raises(IntegrityError, match="title_min_length"):
        await session.flush()


async def test_unknown_deletion_status_is_rejected_by_the_database(session: AsyncSession):
    user = await _user(session)
    session.add(Project(user_id=user.id, title="p", deletion_status="archived"))
    with pytest.raises(IntegrityError, match="projects_deletion_status_check"):
        await session.flush()


async def test_deleting_user_cascades_to_projects(session: AsyncSession):
    user = await _user(session)
    session.add(Project(user_id=user.id, title="p"))
    await session.flush()

    await session.execute(text("DELETE FROM users WHERE id = :id"), {"id": user.id})

    count = (await session.execute(text("SELECT count(*) FROM projects"))).scalar_one()
    assert count == 0
