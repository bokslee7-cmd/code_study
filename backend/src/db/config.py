import os
from dataclasses import dataclass
from typing import Any

_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off"}


@dataclass(frozen=True)
class PoolSettings:
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 1800
    echo: bool = False


def get_database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL environment variable is required")
    return url


def to_async_url(url: str) -> str:
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+asyncpg://" + url[len(prefix) :]
    return url


def _read_int(name: str, default: int, minimum: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ValueError(f"{name} must be an integer, got {raw!r}") from None
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}, got {value}")
    return value


def _read_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    value = raw.strip().lower()
    if value in _TRUE:
        return True
    if value in _FALSE:
        return False
    raise ValueError(f"{name} must be a boolean (true/false), got {raw!r}")


def load_pool_settings() -> PoolSettings:
    """Read pool settings from DB_* environment variables (defaults apply when unset)."""
    defaults = PoolSettings()
    return PoolSettings(
        pool_size=_read_int("DB_POOL_SIZE", defaults.pool_size, 1),
        max_overflow=_read_int("DB_MAX_OVERFLOW", defaults.max_overflow, 0),
        pool_timeout=_read_int("DB_POOL_TIMEOUT", defaults.pool_timeout, 1),
        # 0 disables recycling
        pool_recycle=_read_int("DB_POOL_RECYCLE", defaults.pool_recycle, 0),
        echo=_read_bool("DB_ECHO", defaults.echo),
    )


def engine_kwargs(settings: PoolSettings) -> dict[str, Any]:
    return {
        "pool_size": settings.pool_size,
        "max_overflow": settings.max_overflow,
        "pool_timeout": settings.pool_timeout,
        "pool_recycle": settings.pool_recycle if settings.pool_recycle > 0 else -1,
        "pool_pre_ping": True,
        "echo": settings.echo,
    }
