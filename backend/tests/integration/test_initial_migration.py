import asyncio
import os
import socket
import subprocess
import sys
import uuid
from collections.abc import Iterator
from pathlib import Path

import asyncpg
import pytest

BACKEND = Path(__file__).resolve().parents[2]
ADMIN_DSN = "postgresql://postgres:postgres@localhost:5432/postgres"

EXPECTED_TABLES = {
    "users",
    "projects",
    "tasks",
    "uploaded_code",
    "code_files",
    "learning_documents",
    "practice_problems",
    "questions",
    "progress",
    "refresh_tokens",
}

EXPECTED_INDEXES = {
    "idx_users_email",
    "idx_projects_user_id",
    "idx_projects_deletion_status",
    "idx_projects_user_active",
    "idx_tasks_project_id",
    "idx_tasks_deletion_status",
    "idx_tasks_project_active",
    "idx_tasks_number_order",
    "idx_uploaded_code_task_id",
    "idx_code_files_uploaded_code_id",
    "idx_learning_documents_task_id",
    "idx_learning_documents_status",
    "idx_learning_documents_celery_task",
    "idx_practice_problems_task_id",
    "idx_practice_problems_number",
    "idx_questions_task_id",
    "idx_questions_user_id",
    "idx_questions_task_user",
    "idx_progress_task_id",
    "idx_progress_user_id",
    "idx_progress_task_user",
    "idx_refresh_tokens_user_id",
    "idx_refresh_tokens_hash",
    "idx_refresh_tokens_expires",
}

VALID_CHAPTERS = (
    '{"chapter1":{},"chapter2":{},"chapter3":{},"chapter4":{},'
    '"chapter5":{},"chapter6":{},"chapter7":{}}'
)

USER_ID = "00000000-0000-0000-0000-000000000001"
PROJECT_ID = "00000000-0000-0000-0000-000000000002"
TASK_ID = "00000000-0000-0000-0000-000000000003"


def _db_reachable() -> bool:
    try:
        with socket.create_connection(("localhost", 5432), timeout=1):
            return True
    except OSError:
        return False


pytestmark = pytest.mark.skipif(not _db_reachable(), reason="PostgreSQL(localhost:5432) 필요")


def _run(coro):
    return asyncio.run(coro)


async def _execute(dsn: str, sql: str) -> None:
    conn = await asyncpg.connect(dsn)
    try:
        await conn.execute(sql)
    finally:
        await conn.close()


async def _fetch(dsn: str, sql: str) -> list[asyncpg.Record]:
    conn = await asyncpg.connect(dsn)
    try:
        return await conn.fetch(sql)
    finally:
        await conn.close()


def _alembic(dsn: str, *args: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "DATABASE_URL": dsn}
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


@pytest.fixture()
def test_dsn() -> Iterator[str]:
    name = f"migration_test_{uuid.uuid4().hex[:8]}"
    _run(_execute(ADMIN_DSN, f'CREATE DATABASE "{name}"'))
    try:
        yield f"postgresql://postgres:postgres@localhost:5432/{name}"
    finally:
        _run(_execute(ADMIN_DSN, f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))


def _tables(dsn: str) -> set[str]:
    rows = _run(_fetch(dsn, "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"))
    return {r["tablename"] for r in rows} - {"alembic_version"}


def _seed(dsn: str) -> None:
    _run(
        _execute(
            dsn,
            f"""
            INSERT INTO users (id, email, password_hash) VALUES ('{USER_ID}', 'a@b.com', 'h');
            INSERT INTO projects (id, user_id, title) VALUES ('{PROJECT_ID}', '{USER_ID}', 'p');
            INSERT INTO tasks (id, project_id, task_number, title)
              VALUES ('{TASK_ID}', '{PROJECT_ID}', 1, 'valid title');
            """,
        )
    )


def test_upgrade_creates_all_tables_and_indexes(test_dsn):
    result = _alembic(test_dsn, "upgrade", "head")
    assert result.returncode == 0, result.stderr
    assert _tables(test_dsn) == EXPECTED_TABLES
    rows = _run(_fetch(test_dsn, "SELECT indexname FROM pg_indexes WHERE schemaname = 'public'"))
    assert EXPECTED_INDEXES <= {r["indexname"] for r in rows}


def test_downgrade_removes_all_tables(test_dsn):
    assert _alembic(test_dsn, "upgrade", "head").returncode == 0
    result = _alembic(test_dsn, "downgrade", "base")
    assert result.returncode == 0, result.stderr
    assert _tables(test_dsn) == set()


def test_upgrade_is_repeatable_after_downgrade(test_dsn):
    for command in (("upgrade", "head"), ("downgrade", "base"), ("upgrade", "head")):
        assert _alembic(test_dsn, *command).returncode == 0
    assert _tables(test_dsn) == EXPECTED_TABLES


def test_defaults_are_applied(test_dsn):
    assert _alembic(test_dsn, "upgrade", "head").returncode == 0
    _seed(test_dsn)
    user = _run(_fetch(test_dsn, "SELECT skill_level, created_at FROM users"))[0]
    project = _run(_fetch(test_dsn, "SELECT deletion_status FROM projects"))[0]
    assert user["skill_level"] == "Complete Beginner"
    assert user["created_at"] is not None
    assert project["deletion_status"] == "active"


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO users (email, password_hash) VALUES ('not-an-email', 'h')",
        "INSERT INTO users (email, password_hash) VALUES ('a@b.com', 'h')",
        f"INSERT INTO projects (user_id, title) VALUES ('{USER_ID}', '')",
        f"INSERT INTO projects (user_id, title, deletion_status) VALUES ('{USER_ID}', 'x', 'gone')",
        f"INSERT INTO tasks (project_id, task_number, title) VALUES ('{PROJECT_ID}', 2, 'abcd')",
        f"INSERT INTO tasks (project_id, task_number, title)"
        f" VALUES ('{PROJECT_ID}', 1, 'dup number')",
        f"INSERT INTO tasks (project_id, task_number, title, upload_method)"
        f" VALUES ('{PROJECT_ID}', 3, 'valid title', 'zip')",
        f"INSERT INTO tasks (project_id, task_number, title, description)"
        f" VALUES ('{PROJECT_ID}', 4, 'valid title', '{'x' * 501}')",
        f"INSERT INTO uploaded_code (task_id, upload_size_bytes) VALUES ('{TASK_ID}', 10485761)",
        f"INSERT INTO learning_documents (task_id, content) VALUES ('{TASK_ID}', '{{}}')",
        f"INSERT INTO practice_problems (task_id, problem_number, problem_type, problem_statement)"
        f" VALUES ('{TASK_ID}', 6, 'debug', 's')",
        f"INSERT INTO practice_problems (task_id, problem_number, problem_type, problem_statement)"
        f" VALUES ('{TASK_ID}', 1, 'quiz', 's')",
        f"INSERT INTO questions (task_id, user_id, question_text)"
        f" VALUES ('{TASK_ID}', '{USER_ID}', 'hi')",
        f"INSERT INTO progress (task_id, user_id, document_read_percentage)"
        f" VALUES ('{TASK_ID}', '{USER_ID}', 101)",
        f"INSERT INTO progress (task_id, user_id, practice_completion_count)"
        f" VALUES ('{TASK_ID}', '{USER_ID}', 6)",
    ],
)
def test_constraints_reject_invalid_rows(test_dsn, sql):
    assert _alembic(test_dsn, "upgrade", "head").returncode == 0
    _seed(test_dsn)
    with pytest.raises(asyncpg.PostgresError):
        _run(_execute(test_dsn, sql))


def test_valid_dependent_rows_and_cascade_delete(test_dsn):
    assert _alembic(test_dsn, "upgrade", "head").returncode == 0
    _seed(test_dsn)
    _run(
        _execute(
            test_dsn,
            f"""
            INSERT INTO learning_documents (task_id, content)
              VALUES ('{TASK_ID}', '{VALID_CHAPTERS}');
            INSERT INTO practice_problems (task_id, problem_number, problem_type, problem_statement)
              VALUES ('{TASK_ID}', 1, 'follow_along', 's');
            INSERT INTO questions (task_id, user_id, question_text)
              VALUES ('{TASK_ID}', '{USER_ID}', 'what is this?');
            INSERT INTO progress (task_id, user_id) VALUES ('{TASK_ID}', '{USER_ID}');
            INSERT INTO refresh_tokens (user_id, token_hash, expires_at)
              VALUES ('{USER_ID}', 'hash', now() + interval '7 days');
            """,
        )
    )
    _run(_execute(test_dsn, f"DELETE FROM users WHERE id = '{USER_ID}'"))
    for table in (
        "projects",
        "tasks",
        "learning_documents",
        "practice_problems",
        "questions",
        "progress",
        "refresh_tokens",
    ):
        assert _run(_fetch(test_dsn, f"SELECT 1 FROM {table}")) == [], table
