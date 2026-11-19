import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from src.api.exceptions import AppError, NotFoundException
from src.models import CodeFile, Task, UploadedCode
from src.services.code_analysis import code_upload_service
from src.services.code_analysis.code_upload_service import (
    PASTE_LANGUAGES,
    CodeUploadService,
)
from src.utils.file_validator import (
    MAX_FILES_PER_UPLOAD,
    MAX_UPLOAD_SIZE_BYTES,
    SUPPORTED_EXTENSIONS,
)

USER_ID = uuid.uuid4()
PY = b"def add(a, b):\n    return a + b\n"


@pytest.fixture(autouse=True)
def storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    return tmp_path


def _session(code_files: list[CodeFile] | None = None) -> MagicMock:
    result = MagicMock()
    result.scalars.return_value.all.return_value = code_files or []
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)
    session.flush = AsyncMock()
    session.add = MagicMock()
    session.add_all = MagicMock()
    return session


def _task() -> Task:
    return Task(id=uuid.uuid4(), project_id=uuid.uuid4(), task_number=1, title="첫 번째 태스크")


def _service(session: MagicMock | None = None) -> CodeUploadService:
    return CodeUploadService(session or _session())


def test_paste_languages_map_to_supported_extensions():
    assert set(PASTE_LANGUAGES.values()) <= set(SUPPORTED_EXTENSIONS)
    assert PASTE_LANGUAGES["python"] == ".py"


# ---------------------------------------------------------------- prepare: files


def test_prepare_files_validates_and_keeps_names():
    prepared = _service().prepare_files([("app.py", PY), ("README.md", b"# hi")])

    assert prepared.method == "file"
    assert [(f.name, f.extension, f.path) for f in prepared.files] == [
        ("app.py", ".py", None),
        ("README.md", ".md", None),
    ]


def test_prepare_files_drops_client_directories_from_the_name():
    prepared = _service().prepare_files([("C:\\Users\\me\\app.py", PY)])

    assert prepared.files[0].name == "app.py"


@pytest.mark.parametrize(
    ("files", "code", "status"),
    [
        ([], "no_files", 400),
        ([("a.exe", b"x")], "unsupported_extension", 400),
        ([("a.py", b"\x00\x01")], "binary_file", 400),
        ([("a.py", b"x" * (MAX_UPLOAD_SIZE_BYTES + 1))], "upload_too_large", 413),
        ([(f"f{i}.py", b"x") for i in range(MAX_FILES_PER_UPLOAD + 1)], "too_many_files", 400),
    ],
)
def test_prepare_files_maps_validation_errors_to_app_errors(files, code: str, status: int):
    with pytest.raises(AppError) as error:
        _service().prepare_files(files)

    assert error.value.status_code == status
    assert error.value.error == code
    assert error.value.message


def test_prepare_files_rejects_a_total_over_the_size_limit_with_413():
    half = MAX_UPLOAD_SIZE_BYTES // 2 + 1

    with pytest.raises(AppError) as error:
        _service().prepare_files([("a.py", b"x" * half), ("b.py", b"x" * half)])

    assert (error.value.status_code, error.value.error) == (413, "upload_too_large")


# ---------------------------------------------------------------- prepare: folder


def test_prepare_folder_keeps_relative_paths_and_skips_excluded_entries():
    prepared = _service().prepare_folder(
        [
            ("proj/src/main.py", PY),
            ("proj/node_modules/lib/index.js", b"x"),
            ("proj/.git/config.txt", b"x"),
            ("proj/__pycache__/main.py", b"x"),
            ("proj/.DS_Store", b"\x00\x00"),
        ]
    )

    assert prepared.method == "folder"
    assert [(f.name, f.path) for f in prepared.files] == [("main.py", "proj/src/main.py")]


def test_prepare_folder_normalizes_windows_separators():
    prepared = _service().prepare_folder([("proj\\src\\main.py", PY)])

    assert prepared.files[0].path == "proj/src/main.py"


@pytest.mark.parametrize("path", ["../evil.py", "proj/../../evil.py", "/etc/passwd.txt"])
def test_prepare_folder_rejects_path_escapes(path: str):
    with pytest.raises(AppError) as error:
        _service().prepare_folder([(path, PY)])

    assert (error.value.status_code, error.value.error) == (400, "invalid_path")


def test_prepare_folder_with_only_excluded_files_has_no_files():
    with pytest.raises(AppError) as error:
        _service().prepare_folder([("proj/node_modules/a.js", b"x")])

    assert error.value.error == "no_files"


def test_prepare_folder_still_rejects_unsupported_files_inside():
    with pytest.raises(AppError) as error:
        _service().prepare_folder([("proj/logo.png", b"\x89PNG....")])

    assert error.value.error == "unsupported_extension"


# ---------------------------------------------------------------- prepare: paste


def test_prepare_paste_names_the_file_after_the_language():
    prepared = _service().prepare_paste("print('hi')\n", "Python")

    assert prepared.method == "paste"
    assert [(f.name, f.extension, f.path) for f in prepared.files] == [("code.py", ".py", None)]
    assert prepared.files[0].content == b"print('hi')\n"


def test_prepare_paste_encodes_as_utf8():
    prepared = _service().prepare_paste("print('한글')", "python")

    assert prepared.files[0].content == "print('한글')".encode()


def test_prepare_paste_rejects_unknown_language():
    with pytest.raises(AppError) as error:
        _service().prepare_paste("x", "cobol")

    assert (error.value.status_code, error.value.error) == (400, "unsupported_language")


@pytest.mark.parametrize("code", ["", "  \n\t "])
def test_prepare_paste_rejects_blank_code(code: str):
    with pytest.raises(AppError) as error:
        _service().prepare_paste(code, "python")

    assert (error.value.status_code, error.value.error) == (400, "empty_code")


def test_prepare_paste_applies_the_size_limit():
    with pytest.raises(AppError) as error:
        _service().prepare_paste("x" * (MAX_UPLOAD_SIZE_BYTES + 1), "python")

    assert error.value.status_code == 413


# ---------------------------------------------------------------- store


async def test_store_saves_files_and_records_metadata(storage: Path):
    session = _session()
    task = _task()
    service = _service(session)
    prepared = service.prepare_folder([("proj/src/app.py", PY), ("proj/notes.md", b"# notes\n")])

    uploaded = await service.store(USER_ID, task, prepared)

    assert isinstance(uploaded, UploadedCode)
    assert uploaded.task is task and task.uploaded_code is uploaded
    assert uploaded.detected_language == "python"
    assert uploaded.complexity_level == "beginner"
    assert uploaded.total_files == 2
    assert uploaded.total_lines == 3  # 2 python lines + 1 markdown line
    assert uploaded.upload_size_bytes == len(PY) + len(b"# notes\n")
    session.flush.assert_awaited_once()

    session.add.assert_called_once_with(uploaded)
    (added_files,) = session.add_all.call_args.args
    assert all(isinstance(f, CodeFile) for f in added_files)
    by_name = {f.file_name: f for f in added_files}
    app = by_name["app.py"]
    assert (app.file_path, app.file_extension, app.file_size_bytes) == (
        "proj/src/app.py",
        ".py",
        len(PY),
    )
    assert app.mime_type == "text/plain"
    assert app.storage_path.startswith(f"{USER_ID}/{task.id}/")
    assert (storage / app.storage_path).read_bytes() == PY


async def test_store_single_file_has_no_relative_path():
    service = _service()
    uploaded = await service.store(USER_ID, _task(), service.prepare_files([("app.py", PY)]))

    assert uploaded.total_files == 1


async def test_store_removes_written_files_when_the_database_write_fails(storage: Path):
    session = _session()
    session.flush = AsyncMock(side_effect=RuntimeError("db down"))
    task = _task()
    service = _service(session)

    with pytest.raises(RuntimeError):
        await service.store(USER_ID, task, service.prepare_files([("app.py", PY)]))

    assert not (storage / str(USER_ID) / str(task.id)).exists()


# ---------------------------------------------------------------- get_code


async def test_get_code_returns_files_with_their_content():
    task = _task()
    service = _service()
    uploaded = await service.store(
        USER_ID, task, service.prepare_files([("app.py", PY), ("style.css", b"a { b: c }")])
    )
    files = list(uploaded.code_files)

    code = await _service(_session(files)).get_code(task)

    by_name = {item.file.file_name: item for item in code}
    assert by_name["app.py"].content == PY.decode()
    assert by_name["app.py"].language == "python"
    assert by_name["style.css"].language == "css"


async def test_get_code_without_an_upload_is_not_found():
    with pytest.raises(NotFoundException):
        await _service().get_code(_task())


async def test_get_code_with_a_missing_stored_file_is_not_found():
    task = _task()
    service = _service()
    uploaded = await service.store(USER_ID, task, service.prepare_files([("app.py", PY)]))
    files = list(uploaded.code_files)
    for stored in files:
        stored.storage_path = f"{USER_ID}/{task.id}/gone.py"

    with pytest.raises(NotFoundException):
        await _service(_session(files)).get_code(task)


def test_module_exposes_the_service_api():
    assert {"CodeUploadService", "PASTE_LANGUAGES"} <= set(code_upload_service.__all__)
