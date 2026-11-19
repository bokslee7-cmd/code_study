import asyncio
import os
import socket
import subprocess
import sys
import uuid
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import asyncpg
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from src.models import Task, UploadedCode, User
from src.services.code_analysis.code_upload_service import CodeUploadService
from src.services.project_service import ProjectService
from src.services.task_service import TaskService

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
    name = f"task_service_{uuid.uuid4().hex[:8]}"
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


async def test_task_numbers_are_sequential_and_never_reused(session: AsyncSession):
    user = await _user(session)
    project = await ProjectService(session).create(user.id, "Todo 앱")
    service = TaskService(session)

    first = await service.create(user.id, project.id, "첫 번째 태스크")
    second = await service.create(user.id, project.id, "두 번째 태스크")
    await service.soft_delete(second.id, user.id)
    third = await service.create(user.id, project.id, "세 번째 태스크")

    assert [first.task_number, second.task_number, third.task_number] == [1, 2, 3]
    listed = await service.list_for_project(project.id, user.id)
    assert [t.task_number for t in listed] == [1, 3]


async def test_other_projects_start_at_one(session: AsyncSession):
    user = await _user(session)
    projects = ProjectService(session)
    first_project = await projects.create(user.id, "프로젝트 하나")
    second_project = await projects.create(user.id, "프로젝트 둘")
    service = TaskService(session)

    await service.create(user.id, first_project.id, "첫 번째 태스크")
    other = await service.create(user.id, second_project.id, "첫 번째 태스크")

    assert other.task_number == 1


async def test_upload_round_trip_stores_rows_and_files(
    session: AsyncSession, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    user = await _user(session)
    project = await ProjectService(session).create(user.id, "Todo 앱")
    tasks = TaskService(session)
    uploads = CodeUploadService(session)

    prepared = uploads.prepare_files([("app.py", b"def add(a, b):\n    return a + b\n")])
    task = await tasks.create(user.id, project.id, "덧셈 함수", upload_method="file")
    await uploads.store(user.id, task, prepared)

    task_id, user_id = task.id, user.id  # read before expire_all(): lazy loads fail in async
    session.expire_all()
    loaded = await tasks.get_owned(task_id, user_id)
    assert loaded.uploaded_code is not None
    assert loaded.uploaded_code.detected_language == "python"
    code = await uploads.get_code(loaded)
    assert [item.content for item in code] == ["def add(a, b):\n    return a + b\n"]
    stored = (await session.execute(select(UploadedCode))).scalars().all()
    assert len(stored) == 1


async def test_soft_deleted_task_is_hidden(session: AsyncSession):
    user = await _user(session)
    project = await ProjectService(session).create(user.id, "Todo 앱")
    service = TaskService(session)
    task = await service.create(user.id, project.id, "첫 번째 태스크")

    task_id, user_id, project_id = task.id, user.id, project.id
    await service.soft_delete(task_id, user_id)

    session.expire_all()
    row = (await session.execute(select(Task).where(Task.id == task_id))).scalar_one()
    assert row.deletion_status == Task.TRASHED
    assert row.scheduled_deletion_at is not None
    assert await service.list_for_project(project_id, user_id) == []
