import asyncio
import os
import socket
import subprocess
import sys
import uuid
from collections.abc import AsyncIterator, Iterator
from datetime import timedelta
from pathlib import Path

import asyncpg
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from src.api.exceptions import AppError, ForbiddenException, NotFoundException
from src.models import Project, User
from src.services.project_service import ProjectService

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
    """실제 마이그레이션(001)을 적용한 임시 DB."""
    name = f"project_service_{uuid.uuid4().hex[:8]}"
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


async def test_create_then_get_round_trip(session: AsyncSession):
    user = await _user(session)
    service = ProjectService(session)

    created = await service.create(user.id, "Todo 앱", "할 일 앱 분석")
    loaded = await service.get(created.id)

    assert loaded is not None
    assert loaded.user_id == user.id
    assert loaded.title == "Todo 앱"
    assert loaded.description == "할 일 앱 분석"
    assert loaded.deletion_status == Project.ACTIVE
    assert loaded.trashed_at is None and loaded.scheduled_deletion_at is None


async def test_get_unknown_project_returns_none(session: AsyncSession):
    assert await ProjectService(session).get(uuid.uuid4()) is None


async def test_update_persists_title_and_description(session: AsyncSession):
    user = await _user(session)
    service = ProjectService(session)
    project_id = (await service.create(user.id, "Todo 앱", "설명")).id

    await service.update(project_id, user.id, title="새 제목", description=None)

    session.expire_all()
    loaded = await service.get(project_id)
    assert loaded is not None
    assert loaded.title == "새 제목"
    assert loaded.description is None


async def test_update_with_invalid_title_leaves_row_unchanged(session: AsyncSession):
    user = await _user(session)
    service = ProjectService(session)
    project_id = (await service.create(user.id, "Todo 앱")).id

    with pytest.raises(AppError):
        await service.update(project_id, user.id, title="   ")

    session.expire_all()
    loaded = await service.get(project_id)
    assert loaded is not None and loaded.title == "Todo 앱"


async def test_soft_delete_keeps_row_but_hides_it_from_get(session: AsyncSession):
    user = await _user(session)
    service = ProjectService(session)
    created = await service.create(user.id, "Todo 앱")
    project_id = created.id

    await service.soft_delete(project_id, user.id)

    assert await service.get(project_id) is None
    row = (await session.execute(select(Project).where(Project.id == project_id))).scalar_one()
    assert row.deletion_status == Project.TRASHED
    assert row.trashed_at is not None
    assert row.scheduled_deletion_at == row.trashed_at + timedelta(days=30)
    total = (await session.execute(select(func.count()).select_from(Project))).scalar_one()
    assert total == 1


async def test_trashed_project_cannot_be_updated_or_deleted_again(session: AsyncSession):
    user = await _user(session)
    service = ProjectService(session)
    created = await service.create(user.id, "Todo 앱")
    await service.soft_delete(created.id, user.id)

    with pytest.raises(NotFoundException):
        await service.update(created.id, user.id, title="되살리기 시도")
    with pytest.raises(NotFoundException):
        await service.soft_delete(created.id, user.id)


async def test_title_of_255_characters_is_stored(session: AsyncSession):
    user = await _user(session)

    created = await ProjectService(session).create(user.id, "가" * 255)

    assert len(created.title) == 255


async def test_other_user_cannot_read_update_or_delete_a_project(session: AsyncSession):
    owner = await _user(session)
    intruder = await _user(session)
    service = ProjectService(session)
    project_id = (await service.create(owner.id, "내 프로젝트", "비공개")).id

    assert (await service.get_owned(project_id, owner.id)).id == project_id
    with pytest.raises(ForbiddenException):
        await service.get_owned(project_id, intruder.id)
    with pytest.raises(ForbiddenException):
        await service.update(project_id, intruder.id, title="가로채기", description=None)
    with pytest.raises(ForbiddenException):
        await service.soft_delete(project_id, intruder.id)

    session.expire_all()
    row = (await session.execute(select(Project).where(Project.id == project_id))).scalar_one()
    assert row.title == "내 프로젝트" and row.description == "비공개"
    assert row.deletion_status == Project.ACTIVE and row.trashed_at is None


async def test_trashed_project_is_404_for_other_users_too(session: AsyncSession):
    owner = await _user(session)
    intruder = await _user(session)
    service = ProjectService(session)
    project_id = (await service.create(owner.id, "삭제됨")).id
    await service.soft_delete(project_id, owner.id)

    with pytest.raises(NotFoundException):
        await service.get_owned(project_id, intruder.id)
