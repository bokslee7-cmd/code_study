import asyncio
import os
import socket
import subprocess
import sys
import uuid
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass, field
from pathlib import Path

import asyncpg
import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from src import main
from src.api.exceptions import AppError
from src.db import session as session_module
from src.models import LearningDocument, User
from src.services.document import document_queue_service
from src.services.document.document_queue_service import DocumentQueueService
from src.utils import jwt as tokens

BACKEND = Path(__file__).resolve().parents[2]
ADMIN_DSN = "postgresql://postgres:postgres@localhost:5432/postgres"
SECRET = "test-secret-key-that-is-at-least-32-bytes-long"
PROJECTS = "/api/v1/projects"
CODE = "total = 0\nprint(total)\n"


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
    name = f"doc_queue_{uuid.uuid4().hex[:8]}"
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


@dataclass
class Env:
    client: httpx.AsyncClient
    factory: async_sessionmaker[AsyncSession]
    headers: dict[str, str]
    other_headers: dict[str, str]
    dispatched: list[tuple[uuid.UUID, str]] = field(default_factory=list)
    fail_dispatch: bool = False


async def _headers(factory: async_sessionmaker[AsyncSession]) -> dict[str, str]:
    async with factory() as db:
        user = User(email=f"{uuid.uuid4().hex[:8]}@example.com", password_hash="h")
        db.add(user)
        await db.commit()
        return {"Authorization": f"Bearer {tokens.create_access_token(str(user.id))}"}


@pytest.fixture()
async def env(
    migrated_dsn: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[Env]:
    monkeypatch.setenv("JWT_SECRET_KEY", SECRET)
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    engine = create_async_engine(migrated_dsn.replace("postgresql://", "postgresql+asyncpg://"))
    factory = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(session_module, "get_session_factory", lambda: factory)
    transport = httpx.ASGITransport(app=main.create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        state = Env(client, factory, await _headers(factory), await _headers(factory))

        def fake_dispatch(task_id: uuid.UUID, celery_task_id: str) -> None:
            if state.fail_dispatch:
                raise ConnectionError("redis down")
            state.dispatched.append((task_id, celery_task_id))

        monkeypatch.setattr(document_queue_service, "_dispatch_to_celery", fake_dispatch)
        yield state
    await engine.dispose()


async def _upload_task(env: Env) -> str:
    project = await env.client.post(PROJECTS, json={"title": "학습 프로젝트"}, headers=env.headers)
    form = {
        "title": "합계 구하기 태스크",
        "upload_method": "paste",
        "language": "python",
        "code": CODE,
    }
    response = await env.client.post(
        f"{PROJECTS}/{project.json()['id']}/tasks", data=form, headers=env.headers
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


async def _row(env: Env, task_id: str) -> LearningDocument:
    async with env.factory() as db:
        query = select(LearningDocument).where(LearningDocument.task_id == uuid.UUID(task_id))
        return (await db.execute(query)).scalar_one()


async def test_upload_queues_one_generation_and_the_endpoints_report_it(env: Env):
    task_id = await _upload_task(env)

    row = await _row(env, task_id)
    assert row.generation_status == "pending"
    assert env.dispatched == [(uuid.UUID(task_id), row.celery_task_id)]

    document = await env.client.get(f"/api/v1/tasks/{task_id}/document", headers=env.headers)
    assert document.status_code == 200
    body = document.json()
    assert body["status"] == "pending"
    assert body["files"] == [{"path": "code.py", "language": "python", "content": CODE}]
    status = await env.client.get(f"/api/v1/tasks/{task_id}/document/status", headers=env.headers)
    assert status.status_code == 200
    assert status.json()["status"] == "pending"
    assert status.json()["estimated_remaining_seconds"] is None


async def test_upload_still_succeeds_and_the_document_is_failed_when_the_queue_is_down(env: Env):
    env.fail_dispatch = True

    task_id = await _upload_task(env)  # asserts 201

    row = await _row(env, task_id)
    assert row.generation_status == "failed"
    assert row.generation_error == document_queue_service.DISPATCH_FAILED_MESSAGE
    status = await env.client.get(f"/api/v1/tasks/{task_id}/document/status", headers=env.headers)
    assert status.json()["status"] == "failed"


async def test_second_enqueue_is_a_no_op_while_queued_and_regenerate_conflicts(env: Env):
    task_id = await _upload_task(env)

    async with env.factory() as db:
        queue = DocumentQueueService(db)
        await queue.enqueue(uuid.UUID(task_id))
        with pytest.raises(AppError) as info:
            await queue.regenerate(uuid.UUID(task_id))

    assert len(env.dispatched) == 1
    assert info.value.status_code == 409


async def test_finished_document_can_be_regenerated_with_a_new_celery_id(env: Env):
    task_id = await _upload_task(env)
    async with env.factory() as db:
        await DocumentQueueService(db).mark_failed(uuid.UUID(task_id), "일시 오류")
    first_id = env.dispatched[0][1]

    async with env.factory() as db:
        await DocumentQueueService(db).regenerate(uuid.UUID(task_id))

    row = await _row(env, task_id)
    assert row.generation_status == "pending"
    assert row.generation_error is None
    assert len(env.dispatched) == 2
    assert row.celery_task_id == env.dispatched[1][1] != first_id


async def test_other_users_cannot_read_the_document_or_its_status(env: Env):
    task_id = await _upload_task(env)

    for suffix in ("document", "document/status"):
        response = await env.client.get(
            f"/api/v1/tasks/{task_id}/{suffix}", headers=env.other_headers
        )
        assert response.status_code == 403


async def test_unknown_task_is_404(env: Env):
    missing = uuid.uuid4()

    response = await env.client.get(f"/api/v1/tasks/{missing}/document", headers=env.headers)

    assert response.status_code == 404
