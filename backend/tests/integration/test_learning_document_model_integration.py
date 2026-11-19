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
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from src.models import LearningDocument, Project, Task, User

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
    name = f"learning_doc_{uuid.uuid4().hex[:8]}"
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


def _content() -> dict[str, dict[str, object]]:
    content: dict[str, dict[str, object]] = {
        key: {"title": f"챕터 {n}"} for n, key in enumerate(LearningDocument.CHAPTER_KEYS, 1)
    }
    content["chapter2"]["concepts"] = [{"name": "변수", "example": "total = 0"}]
    content["chapter7"]["mistakes"] = [{"wrong": "a", "right": "b", "why": "c", "fix": "d"}]
    return content


async def _task(db: AsyncSession) -> Task:
    user = User(email=f"{uuid.uuid4().hex[:8]}@example.com", password_hash="h")
    db.add(user)
    await db.flush()
    project = Project(user_id=user.id, title="p")
    db.add(project)
    await db.flush()
    task = Task(project_id=project.id, task_number=1, title="학습 태스크")
    db.add(task)
    await db.flush()
    return task


async def test_new_document_gets_database_defaults_and_content_round_trips(session: AsyncSession):
    task = await _task(session)
    content = _content()
    document = LearningDocument(task_id=task.id, content=content)
    session.add(document)
    await session.flush()
    document_id = document.id
    session.expire(document)

    loaded = (
        await session.execute(select(LearningDocument).where(LearningDocument.id == document_id))
    ).scalar_one()
    assert loaded.generation_status == "pending"
    assert loaded.content == content
    assert loaded.created_at and loaded.updated_at
    assert loaded.generation_error is None and loaded.celery_task_id is None


async def test_second_document_for_the_same_task_is_rejected(session: AsyncSession):
    task = await _task(session)
    session.add(LearningDocument(task_id=task.id, content=_content()))
    await session.flush()

    session.add(LearningDocument(task_id=task.id, content=_content()))
    with pytest.raises(IntegrityError, match="learning_documents_task_id_key"):
        await session.flush()


async def test_content_missing_a_chapter_is_rejected(session: AsyncSession):
    task = await _task(session)
    content = _content()
    del content["chapter7"]
    session.add(LearningDocument(task_id=task.id, content=content))
    with pytest.raises(IntegrityError, match="valid_content_structure"):
        await session.flush()


async def test_unknown_generation_status_is_rejected(session: AsyncSession):
    task = await _task(session)
    session.add(LearningDocument(task_id=task.id, content=_content(), generation_status="bogus"))
    with pytest.raises(IntegrityError, match="learning_documents_generation_status_check"):
        await session.flush()


async def test_deleting_task_cascades_to_its_document(session: AsyncSession):
    task = await _task(session)
    task_id = task.id
    session.add(LearningDocument(task_id=task_id, content=_content()))
    await session.flush()

    await session.execute(text("DELETE FROM tasks WHERE id = :id"), {"id": task_id})

    count = (await session.execute(text("SELECT count(*) FROM learning_documents"))).scalar_one()
    assert count == 0
