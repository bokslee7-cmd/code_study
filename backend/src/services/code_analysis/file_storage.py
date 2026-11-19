"""Filesystem storage of uploaded code: <root>/{user_id}/{task_id}/{uuid}{ext}.

Stored names are generated, so a client-supplied file name never reaches the filesystem. The
client-supplied *relative path* of a folder upload is only kept as metadata; safe_relative_path
rejects anything that tries to leave the folder. read_file re-checks containment anyway.
"""

import os
import re
import shutil
import uuid
from pathlib import Path

from src.utils.file_validator import FileValidationError

__all__ = [
    "delete_task_files",
    "get_storage_root",
    "read_file",
    "safe_relative_path",
    "save_file",
]

DEFAULT_UPLOAD_DIR = "storage/uploads"
_DRIVE_PREFIX = re.compile(r"^[A-Za-z]:")
_INVALID_PATH_MESSAGE = (
    "파일 경로가 올바르지 않습니다. 상위 폴더(..)나 절대 경로는 사용할 수 없습니다."  # noqa: E501 (Korean text is double width)
)


def _invalid_path() -> FileValidationError:
    return FileValidationError("invalid_path", _INVALID_PATH_MESSAGE)


def get_storage_root() -> Path:
    return Path(os.environ.get("UPLOAD_DIR") or DEFAULT_UPLOAD_DIR).resolve()


def safe_relative_path(path: str) -> str:
    """Normalize a client-supplied relative path to forward slashes; reject any escape."""
    normalized = path.strip().replace("\\", "/")
    if not normalized or "\0" in normalized or normalized.startswith("/"):
        raise _invalid_path()
    if _DRIVE_PREFIX.match(normalized):
        raise _invalid_path()
    parts = [part for part in normalized.split("/") if part not in ("", ".")]
    if not parts or ".." in parts:
        raise _invalid_path()
    return "/".join(parts)


def save_file(user_id: uuid.UUID, task_id: uuid.UUID, extension: str, content: bytes) -> str:
    """Write one file and return its storage path, relative to the storage root."""
    storage_path = f"{user_id}/{task_id}/{uuid.uuid4()}{extension}"
    target = get_storage_root() / storage_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return storage_path


def read_file(storage_path: str) -> bytes:
    root = get_storage_root()
    target = (root / storage_path).resolve()
    if not target.is_relative_to(root):
        raise _invalid_path()
    return target.read_bytes()


def delete_task_files(user_id: uuid.UUID, task_id: uuid.UUID) -> None:
    shutil.rmtree(get_storage_root() / str(user_id) / str(task_id), ignore_errors=True)
