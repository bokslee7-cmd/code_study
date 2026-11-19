import uuid
from pathlib import Path

import pytest
from src.services.code_analysis import file_storage
from src.services.code_analysis.file_storage import (
    delete_task_files,
    get_storage_root,
    read_file,
    safe_relative_path,
    save_file,
)
from src.utils.file_validator import FileValidationError

USER_ID = uuid.uuid4()
TASK_ID = uuid.uuid4()


@pytest.fixture(autouse=True)
def storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    return tmp_path


# ---------------------------------------------------------------- root


def test_root_defaults_to_storage_uploads(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("UPLOAD_DIR")

    assert get_storage_root() == Path("storage/uploads").resolve()


def test_root_follows_upload_dir_env(storage: Path):
    assert get_storage_root() == storage.resolve()


# ---------------------------------------------------------------- save / read


def test_save_file_writes_under_user_and_task_directory(storage: Path):
    storage_path = save_file(USER_ID, TASK_ID, ".py", b"print('hi')\n")

    assert storage_path.startswith(f"{USER_ID}/{TASK_ID}/")
    assert storage_path.endswith(".py")
    assert (storage / storage_path).read_bytes() == b"print('hi')\n"


def test_save_file_uses_generated_names_so_same_content_does_not_collide():
    first = save_file(USER_ID, TASK_ID, ".py", b"x")
    second = save_file(USER_ID, TASK_ID, ".py", b"x")

    assert first != second


def test_read_file_returns_saved_bytes():
    storage_path = save_file(USER_ID, TASK_ID, ".txt", "한글".encode())

    assert read_file(storage_path) == "한글".encode()


@pytest.mark.parametrize("bad", ["../outside.txt", f"{USER_ID}/../../etc/passwd", "/etc/passwd"])
def test_read_file_rejects_paths_outside_the_root(bad: str):
    with pytest.raises(FileValidationError) as error:
        read_file(bad)

    assert error.value.code == "invalid_path"


def test_read_file_missing_file_raises_file_not_found():
    with pytest.raises(FileNotFoundError):
        read_file(f"{USER_ID}/{TASK_ID}/missing.py")


# ---------------------------------------------------------------- delete


def test_delete_task_files_removes_the_task_directory_only(storage: Path):
    kept = save_file(USER_ID, uuid.uuid4(), ".py", b"keep")
    save_file(USER_ID, TASK_ID, ".py", b"drop")

    delete_task_files(USER_ID, TASK_ID)

    assert not (storage / str(USER_ID) / str(TASK_ID)).exists()
    assert (storage / kept).exists()


def test_delete_task_files_without_files_is_a_noop():
    delete_task_files(USER_ID, TASK_ID)


# ---------------------------------------------------------------- relative path


@pytest.mark.parametrize(
    ("raw", "clean"),
    [
        ("src/app/main.py", "src/app/main.py"),
        ("src\\app\\main.py", "src/app/main.py"),
        ("./src//main.py", "src/main.py"),
        ("main.py", "main.py"),
    ],
)
def test_safe_relative_path_normalizes(raw: str, clean: str):
    assert safe_relative_path(raw) == clean


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "../secret.py",
        "a/../../secret.py",
        "a/..\\b.py",
        "/etc/passwd",
        "C:\\x.py",
        "a\0b",
    ],
)
def test_safe_relative_path_rejects_escapes(raw: str):
    with pytest.raises(FileValidationError) as error:
        safe_relative_path(raw)

    assert error.value.code == "invalid_path"


def test_module_exposes_only_the_documented_api():
    assert set(file_storage.__all__) == {
        "delete_task_files",
        "get_storage_root",
        "read_file",
        "safe_relative_path",
        "save_file",
    }
