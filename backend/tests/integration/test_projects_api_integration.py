import asyncio
import os
import socket
import subprocess
import sys
import uuid
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from pathlib import Path

import asyncpg
import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from src import main
from src.db import session as session_module
from src.models import Project, User
from src.utils import jwt as tokens

BACKEND = Path(__file__).resolve().parents[2]
ADMIN_DSN = "postgresql://postgres:postgres@localhost:5432/postgres"
PROJECTS = "/api/v1/projects"
SECRET = "test-secret-key-that-is-at-least-32-bytes-long"


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
    name = f"projects_api_{uuid.uuid4().hex[:8]}"
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
class Account:
    id: uuid.UUID
    headers: dict[str, str]


@dataclass
class Env:
    client: httpx.AsyncClient
    factory: async_sessionmaker[AsyncSession]
    owner: Account
    other: Account


async def _account(factory: async_sessionmaker[AsyncSession]) -> Account:
    async with factory() as db:
        user = User(email=f"{uuid.uuid4().hex[:8]}@example.com", password_hash="h")
        db.add(user)
        await db.commit()
        user_id = user.id
    token = tokens.create_access_token(str(user_id))
    return Account(id=user_id, headers={"Authorization": f"Bearer {token}"})


@pytest.fixture()
async def env(migrated_dsn: str, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[Env]:
    """The real app (real get_session with commit/rollback) on a throwaway migrated database."""
    monkeypatch.setenv("JWT_SECRET_KEY", SECRET)
    engine = create_async_engine(migrated_dsn.replace("postgresql://", "postgresql+asyncpg://"))
    factory = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(session_module, "get_session_factory", lambda: factory)
    transport = httpx.ASGITransport(app=main.create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield Env(client, factory, await _account(factory), await _account(factory))
    await engine.dispose()


async def _create(env: Env, account: Account, title: str, description: str | None = None) -> str:
    response = await env.client.post(
        PROJECTS, json={"title": title, "description": description}, headers=account.headers
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


async def test_each_user_sees_only_their_own_projects_and_gets_403_on_others(env: Env):
    mine = await _create(env, env.owner, "내 프로젝트", "비공개")
    theirs = await _create(env, env.other, "남의 프로젝트")

    listed = await env.client.get(PROJECTS, headers=env.owner.headers)
    own_detail = await env.client.get(f"{PROJECTS}/{mine}", headers=env.owner.headers)
    foreign_detail = await env.client.get(f"{PROJECTS}/{theirs}", headers=env.owner.headers)
    foreign_patch = await env.client.patch(
        f"{PROJECTS}/{theirs}", json={"title": "가로채기"}, headers=env.owner.headers
    )
    foreign_delete = await env.client.delete(f"{PROJECTS}/{theirs}", headers=env.owner.headers)

    assert [p["id"] for p in listed.json()["projects"]] == [mine]
    assert own_detail.status_code == 200 and own_detail.json()["description"] == "비공개"
    assert foreign_detail.status_code == 403
    assert foreign_patch.status_code == 403
    assert foreign_delete.status_code == 403
    still_there = await env.client.get(PROJECTS, headers=env.other.headers)
    assert [p["title"] for p in still_there.json()["projects"]] == ["남의 프로젝트"]


async def test_deleted_project_disappears_from_the_list_but_the_row_is_kept(env: Env):
    keep = await _create(env, env.owner, "남길 프로젝트")
    doomed = await _create(env, env.owner, "지울 프로젝트")

    deleted = await env.client.delete(f"{PROJECTS}/{doomed}", headers=env.owner.headers)
    listed = await env.client.get(PROJECTS, headers=env.owner.headers)
    detail = await env.client.get(f"{PROJECTS}/{doomed}", headers=env.owner.headers)
    deleted_again = await env.client.delete(f"{PROJECTS}/{doomed}", headers=env.owner.headers)

    assert deleted.status_code == 204
    assert [p["id"] for p in listed.json()["projects"]] == [keep]
    assert detail.status_code == 404
    assert deleted_again.status_code == 404
    async with env.factory() as db:
        row = (
            await db.execute(select(Project).where(Project.id == uuid.UUID(doomed)))
        ).scalar_one()
        assert row.deletion_status == Project.TRASHED
        assert row.trashed_at is not None


async def test_patch_keeps_unsent_fields_and_null_description_clears_it(env: Env):
    project_id = await _create(env, env.owner, "원래 제목", "원래 설명")
    url = f"{PROJECTS}/{project_id}"

    title_only = await env.client.patch(url, json={"title": "새 제목"}, headers=env.owner.headers)
    cleared = await env.client.patch(url, json={"description": None}, headers=env.owner.headers)
    stored = await env.client.get(url, headers=env.owner.headers)

    def pair(response: httpx.Response) -> tuple[str, str | None]:
        body = response.json()
        return body["title"], body["description"]

    assert pair(title_only) == ("새 제목", "원래 설명")
    assert pair(cleared) == ("새 제목", None)
    assert pair(stored) == ("새 제목", None)


async def test_list_is_ordered_by_recent_activity_then_creation(env: Env):
    first = await _create(env, env.owner, "첫째")
    second = await _create(env, env.owner, "둘째")
    third = await _create(env, env.owner, "셋째")
    async with env.factory() as db:
        project = (
            await db.execute(select(Project).where(Project.id == uuid.UUID(first)))
        ).scalar_one()
        project.last_activity_at = project.last_activity_at.replace(year=2099)
        await db.commit()

    listed = await env.client.get(PROJECTS, headers=env.owner.headers)

    # first was pushed to the newest activity time; the other two follow by activity time, which
    # equals their creation order here, so the later-created third comes before second.
    assert [p["id"] for p in listed.json()["projects"]] == [first, third, second]
