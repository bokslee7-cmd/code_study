import asyncio
import json
import os
import socket
import subprocess
import sys
import uuid
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Any

import asyncpg
import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from src.api.exceptions import NotFoundException
from src.models import LearningDocument, Task, User
from src.services.ai.gemini_client import GeminiAPIError
from src.services.code_analysis.code_upload_service import CodeUploadService
from src.services.document.document_generation_service import (
    FAILED_CHAPTER_MARKER,
    DocumentGenerationError,
    DocumentGenerationService,
)
from src.services.project_service import ProjectService
from src.services.task_service import TaskService

BACKEND = Path(__file__).resolve().parents[2]
ADMIN_DSN = "postgresql://postgres:postgres@localhost:5432/postgres"
CODE = "total = 0\nfor n in range(3):\n    total += n\nprint(total)\n"


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
    name = f"doc_generation_{uuid.uuid4().hex[:8]}"
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
async def engine(migrated_dsn: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    created = create_async_engine(migrated_dsn.replace("postgresql://", "postgresql+asyncpg://"))
    yield created
    await created.dispose()


@pytest.fixture()
async def session(engine: Any) -> AsyncIterator[AsyncSession]:
    async with AsyncSession(engine, expire_on_commit=False) as db:
        yield db


def _document(**overrides: Any) -> dict[str, Any]:
    document: dict[str, Any] = {
        "chapter1": {"title": "t", "summary": "합계를 구합니다."},
        "chapter2": {"title": "t", "concepts": [{"name": "변수", "explanation": "상자"}]},
        "chapter3": {"title": "t", "flowchart": "시작\n끝", "file_breakdown": {"code.py": "전부"}},
        "chapter4": {
            "title": "t",
            "explanations": [{"line_number": 1, "code": "total = 0", "what_it_does": "0 저장"}],
        },
        "chapter5": {
            "title": "t",
            "steps": [{"step_number": 1, "action": "a", "explanation": "b"}],
        },
        "chapter6": {"title": "t", "concepts": [{"concept_name": "변수", "what_it_is": "상자"}]},
        "chapter7": {
            "title": "t",
            "mistakes": [{"mistake_title": "m", "wrong_code": "x", "right_code": "y"}],
        },
    }
    document.update(overrides)
    return document


class FakeClient:
    def __init__(self, *script: str | Exception, on_call: Any = None) -> None:
        self.script, self.on_call, self.prompts = list(script), on_call, []

    async def generate(self, prompt: str, **_: Any) -> str:
        self.prompts.append(prompt)
        if self.on_call:
            await self.on_call()
        step = self.script.pop(0)
        if isinstance(step, Exception):
            raise step
        return step


async def _task_with_code(db: AsyncSession) -> Task:
    user = User(email=f"{uuid.uuid4().hex[:8]}@example.com", password_hash="h")
    db.add(user)
    await db.flush()
    project = await ProjectService(db).create(user.id, "학습 프로젝트")
    task = await TaskService(db).create(user.id, project.id, "합계 구하기 태스크")
    uploads = CodeUploadService(db)
    await uploads.store(user.id, task, uploads.prepare_paste(CODE, "python"))
    await db.commit()
    return task


async def _row(engine: Any, task_id: uuid.UUID) -> LearningDocument:
    async with AsyncSession(engine) as other:
        query = select(LearningDocument).where(LearningDocument.task_id == task_id)
        return (await other.execute(query)).scalar_one()


async def test_status_goes_in_progress_then_completed_and_content_is_saved(
    engine: Any, session: AsyncSession
):
    task = await _task_with_code(session)
    seen: list[str | None] = []

    async def peek() -> None:  # another connection sees only committed state
        seen.append((await _row(engine, task.id)).generation_status)

    client = FakeClient(json.dumps(_document()), on_call=peek)
    document = await DocumentGenerationService(client, session).generate_document(task.id)

    assert seen == ["in_progress"]
    stored = await _row(engine, task.id)
    assert stored.id == document.id
    assert stored.generation_status == "completed"
    assert set(stored.content) == set(LearningDocument.CHAPTER_KEYS)
    assert stored.content["chapter1"]["summary"] == "합계를 구합니다."
    assert stored.generation_started_at and stored.generation_completed_at
    assert stored.generation_error is None
    assert "total += n" in client.prompts[0]
    assert "python" in client.prompts[0]


async def test_unknown_task_id_raises_a_readable_not_found(session: AsyncSession):
    missing = uuid.uuid4()
    with pytest.raises(NotFoundException) as info:
        await DocumentGenerationService(FakeClient(), session).generate_document(missing)
    assert info.value.status_code == 404
    assert "태스크를 찾을 수 없습니다" in info.value.message
    assert info.value.details == {"task_id": str(missing)}


async def test_task_without_uploaded_code_is_not_found(session: AsyncSession):
    user = User(email=f"{uuid.uuid4().hex[:8]}@example.com", password_hash="h")
    session.add(user)
    await session.flush()
    project = await ProjectService(session).create(user.id, "빈 프로젝트")
    task = await TaskService(session).create(user.id, project.id, "코드 없는 태스크")
    await session.commit()
    with pytest.raises(NotFoundException):
        await DocumentGenerationService(FakeClient(), session).generate_document(task.id)
    assert (await session.execute(select(LearningDocument))).first() is None


async def test_trashed_task_is_not_found(session: AsyncSession):
    task = await _task_with_code(session)
    await session.execute(text("UPDATE tasks SET deletion_status = 'trashed'"))
    await session.commit()
    with pytest.raises(NotFoundException):
        await DocumentGenerationService(FakeClient(), session).generate_document(task.id)


async def test_failure_is_saved_as_failed_with_the_reason_and_reraised(
    engine: Any, session: AsyncSession
):
    task = await _task_with_code(session)
    client = FakeClient(GeminiAPIError("bad key", retryable=False))
    with pytest.raises(DocumentGenerationError):
        await DocumentGenerationService(client, session).generate_document(task.id)
    stored = await _row(engine, task.id)
    assert stored.generation_status == "failed"
    assert "bad key" in (stored.generation_error or "")
    assert stored.generation_completed_at is not None


async def test_partial_document_is_completed_and_names_the_failed_chapters(
    engine: Any, session: AsyncSession
):
    task = await _task_with_code(session)
    bad = json.dumps(_document(chapter4={"title": "빈 챕터"}))
    document = await DocumentGenerationService(
        FakeClient(bad, bad, bad), session
    ).generate_document(task.id)
    assert document.generation_status == "completed"
    assert document.content["chapter4"] == {FAILED_CHAPTER_MARKER: True}
    assert "chapter4" in (document.generation_error or "")


async def test_regenerating_reuses_the_single_row_and_clears_the_old_error(
    engine: Any, session: AsyncSession
):
    task = await _task_with_code(session)
    failing = FakeClient(GeminiAPIError("bad key", retryable=False))
    with pytest.raises(DocumentGenerationError):
        await DocumentGenerationService(failing, session).generate_document(task.id)

    ok = FakeClient(json.dumps(_document()))
    await DocumentGenerationService(ok, session).generate_document(task.id)

    stored = await _row(engine, task.id)  # scalar_one: still exactly one row
    assert stored.generation_status == "completed"
    assert stored.generation_error is None
