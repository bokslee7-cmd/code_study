import json
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]

REQUIRED_ENV_KEYS = {
    "DATABASE_URL",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_DB",
    "REDIS_URL",
    "GOOGLE_API_KEY",
    "JWT_SECRET_KEY",
    "JWT_REFRESH_SECRET",
    "ENVIRONMENT",
    "DEBUG",
    "ALLOWED_ORIGINS",
    "UPLOAD_DIR",
    "MAX_UPLOAD_SIZE_MB",
}


def _read(relative: str) -> str:
    path = ROOT / relative
    assert path.exists(), f"{relative}가 있어야 한다"
    return path.read_text(encoding="utf-8")


def _env_pairs(text: str) -> dict[str, str]:
    pairs = {}
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            pairs[key] = value
    return pairs


# T005 .env.example
def test_env_example_has_all_required_keys():
    assert REQUIRED_ENV_KEYS <= set(_env_pairs(_read(".env.example")))


def test_env_example_has_no_real_secrets():
    pairs = _env_pairs(_read(".env.example"))
    for key in ("GOOGLE_API_KEY", "JWT_SECRET_KEY", "JWT_REFRESH_SECRET"):
        assert pairs[key].startswith("change-me") or pairs[key].startswith("your-"), key


def test_frontend_env_example_has_api_base_url():
    assert "VITE_API_BASE_URL" in _env_pairs(_read("frontend/.env.example"))


# T006 lint/format
def test_backend_pyproject_configures_ruff_black_mypy_strict():
    config = tomllib.loads(_read("backend/pyproject.toml"))
    assert "ruff" in config["tool"]
    assert "black" in config["tool"]
    assert config["tool"]["mypy"]["strict"] is True


def test_frontend_has_eslint_flat_config_and_prettier():
    _read("frontend/eslint.config.js")
    _read("frontend/.prettierrc")


def test_frontend_package_has_lint_and_format_scripts():
    scripts = json.loads(_read("frontend/package.json"))["scripts"]
    assert {"lint", "format"} <= set(scripts)


# T007 .gitignore
@pytest.mark.parametrize(
    "pattern",
    [
        "node_modules/",
        ".venv/",
        "venv/",
        "__pycache__/",
        ".env",
        "storage/uploads/",
        "dist/",
        "coverage/",
    ],
)
def test_gitignore_covers_pattern(pattern):
    lines = {line.strip() for line in _read(".gitignore").splitlines()}
    assert pattern in lines


def test_gitignore_keeps_env_examples_tracked():
    lines = {line.strip() for line in _read(".gitignore").splitlines()}
    assert "!.env.example" in lines
