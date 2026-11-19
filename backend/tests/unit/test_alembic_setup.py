import configparser
import os
import socket
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[2]
LOCAL_DB_URL = "postgresql://postgres:postgres@localhost:5432/codelearning"


def _alembic(*args: str, env_url: str | None = LOCAL_DB_URL) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k != "DATABASE_URL"}
    if env_url:
        env["DATABASE_URL"] = env_url
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _db_reachable() -> bool:
    try:
        with socket.create_connection(("localhost", 5432), timeout=1):
            return True
    except OSError:
        return False


def test_alembic_scaffold_exists():
    for relative in ("alembic.ini", "alembic/env.py", "alembic/script.py.mako", "alembic/versions"):
        assert (BACKEND / relative).exists(), f"backend/{relative}가 있어야 한다"


def test_alembic_ini_points_to_alembic_dir_without_credentials():
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(BACKEND / "alembic.ini", encoding="utf-8")
    assert parser["alembic"]["script_location"].endswith("alembic")
    assert "postgres:postgres" not in (BACKEND / "alembic.ini").read_text(encoding="utf-8")


def test_env_py_reads_database_url_from_environment():
    source = (BACKEND / "alembic/env.py").read_text(encoding="utf-8")
    assert "from src.db.config import get_database_url" in source


def test_alembic_runs_offline_without_database():
    result = _alembic("upgrade", "head", "--sql")
    assert result.returncode == 0, result.stderr


def test_alembic_fails_clearly_without_database_url():
    result = _alembic("upgrade", "head", "--sql", env_url=None)
    assert result.returncode != 0
    assert "DATABASE_URL" in result.stderr


@pytest.mark.skipif(not _db_reachable(), reason="PostgreSQL(localhost:5432)이 실행 중이어야 한다")
def test_alembic_connects_to_postgres():
    result = _alembic("current")
    assert result.returncode == 0, result.stderr
