import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from src import main
from src.api.dependencies import get_code_upload_service, get_task_service
from src.api.exceptions import AppError, ForbiddenException, NotFoundException
from src.db.session import get_session
from src.models import CodeFile, Task, UploadedCode, User
from src.services.code_analysis.code_upload_service import (
    CodeFileContent,
    CodeUploadService,
    PreparedFile,
    PreparedUpload,
)
from src.services.task_service import TaskService
from src.utils import jwt as tokens

SECRET = "test-secret-key-that-is-at-least-32-bytes-long"
USER_ID = uuid.uuid4()
PROJECT_ID = uuid.uuid4()
TASK_ID = uuid.uuid4()
PROJECT_TASKS = f"/api/v1/projects/{PROJECT_ID}/tasks"
TASK_PATH = f"/api/v1/tasks/{TASK_ID}"
CREATED = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)
UPDATED = datetime(2026, 11, 2, 9, 0, tzinfo=UTC)

TASK_FIELDS = {
    "id",
    "project_id",
    "task_number",
    "title",
    "description",
    "upload_method",
    "created_at",
    "updated_at",
    "uploaded_code",
}
UPLOAD_FIELDS = {
    "detected_language",
    "complexity_level",
    "total_lines",
    "total_files",
    "upload_size_bytes",
}


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", SECRET)
    monkeypatch.delenv("JWT_ACCESS_TOKEN_MINUTES", raising=False)
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)


def _uploaded_code(**overrides: object) -> UploadedCode:
    values: dict[str, object] = {
        "id": uuid.uuid4(),
        "task_id": TASK_ID,
        "detected_language": "python",
        "complexity_level": "beginner",
        "total_lines": 12,
        "total_files": 2,
        "upload_size_bytes": 345,
    }
    values.update(overrides)
    return UploadedCode(**values)


def _task(with_upload: bool = True, **overrides: object) -> Task:
    values: dict[str, object] = {
        "id": TASK_ID,
        "project_id": PROJECT_ID,
        "task_number": 3,
        "title": "할 일 앱 분석",
        "description": "설명",
        "upload_method": "file",
        "created_at": CREATED,
        "updated_at": UPDATED,
        "deletion_status": Task.ACTIVE,
    }
    values.update(overrides)
    task = Task(**values)
    if with_upload:
        task.uploaded_code = _uploaded_code()
    return task


def _prepared(method: str = "file") -> PreparedUpload:
    return PreparedUpload(method, [PreparedFile("app.py", ".py", b"x = 1\n", None)])


class _Harness:
    """The real app with both services replaced by doubles; only the HTTP contract is tested."""

    def __init__(self) -> None:
        self.tasks = MagicMock(spec=TaskService)
        self.tasks.list_for_project = AsyncMock(return_value=[])
        self.tasks.create = AsyncMock(return_value=_task())
        self.tasks.get_owned = AsyncMock(return_value=_task())
        self.tasks.update = AsyncMock(return_value=_task())
        self.tasks.soft_delete = AsyncMock(return_value=None)
        self.tasks.start_document_generation = AsyncMock(return_value=None)

        self.code = MagicMock(spec=CodeUploadService)
        self.code.prepare_files.return_value = _prepared("file")
        self.code.prepare_folder.return_value = _prepared("folder")
        self.code.prepare_paste.return_value = _prepared("paste")
        self.code.store = AsyncMock(return_value=_uploaded_code())
        self.code.get_code = AsyncMock(return_value=[])

        result = MagicMock()
        result.scalar_one_or_none.return_value = User(
            id=USER_ID, email="learner@example.com", password_hash="x"
        )
        session = MagicMock()
        session.execute = AsyncMock(return_value=result)

        async def fake_get_session():
            yield session

        app = main.create_app()
        app.dependency_overrides[get_session] = fake_get_session
        app.dependency_overrides[get_task_service] = lambda: self.tasks
        app.dependency_overrides[get_code_upload_service] = lambda: self.code
        self.client = TestClient(app, raise_server_exceptions=False)

    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {tokens.create_access_token(str(USER_ID))}"}


# ---------------------------------------------------------------- wiring / auth


def test_task_routes_are_mounted_under_api_v1():
    app = main.create_app()
    routes = {
        (route.path, method) for route in app.routes for method in getattr(route, "methods", [])
    }

    assert ("/api/v1/projects/{project_id}/tasks", "GET") in routes
    assert ("/api/v1/projects/{project_id}/tasks", "POST") in routes
    assert ("/api/v1/tasks/{task_id}", "GET") in routes
    assert ("/api/v1/tasks/{task_id}", "PATCH") in routes
    assert ("/api/v1/tasks/{task_id}", "DELETE") in routes
    assert ("/api/v1/tasks/{task_id}/code", "GET") in routes


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", PROJECT_TASKS),
        ("post", PROJECT_TASKS),
        ("get", TASK_PATH),
        ("patch", TASK_PATH),
        ("delete", TASK_PATH),
        ("get", f"{TASK_PATH}/code"),
    ],
)
def test_every_task_endpoint_requires_login(method: str, path: str):
    response = getattr(_Harness().client, method)(path)

    assert response.status_code == 401
    assert response.json()["error"] == "unauthorized"


# ---------------------------------------------------------------- GET /projects/{id}/tasks


def test_list_returns_tasks_with_upload_summary():
    harness = _Harness()
    harness.tasks.list_for_project.return_value = [_task(), _task(with_upload=False, task_number=4)]

    response = harness.client.get(PROJECT_TASKS, headers=harness.headers())

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"tasks"}
    first, second = body["tasks"]
    assert set(first) == TASK_FIELDS
    assert first["task_number"] == 3
    assert set(first["uploaded_code"]) == UPLOAD_FIELDS
    assert first["uploaded_code"]["detected_language"] == "python"
    assert second["uploaded_code"] is None
    harness.tasks.list_for_project.assert_awaited_once_with(PROJECT_ID, USER_ID)


def test_list_empty_project_returns_empty_list():
    harness = _Harness()

    response = harness.client.get(PROJECT_TASKS, headers=harness.headers())

    assert response.json() == {"tasks": []}


def test_list_maps_not_found_and_forbidden():
    harness = _Harness()
    harness.tasks.list_for_project.side_effect = NotFoundException("없음")
    assert harness.client.get(PROJECT_TASKS, headers=harness.headers()).status_code == 404

    harness.tasks.list_for_project.side_effect = ForbiddenException()
    assert harness.client.get(PROJECT_TASKS, headers=harness.headers()).status_code == 403


def test_list_with_malformed_project_id_is_a_validation_error():
    harness = _Harness()

    response = harness.client.get("/api/v1/projects/not-a-uuid/tasks", headers=harness.headers())

    assert response.status_code == 400
    assert response.json()["error"] == "validation_error"


# ---------------------------------------------------------------- POST /projects/{id}/tasks


def _post(harness: _Harness, data: dict, files: list | None = None):
    return harness.client.post(PROJECT_TASKS, data=data, files=files, headers=harness.headers())


def test_create_with_file_upload_returns_201_and_the_task():
    harness = _Harness()
    files = [
        ("files", ("app.py", b"x = 1\n", "text/x-python")),
        ("files", ("util.py", b"y = 2\n", "text/x-python")),
    ]

    response = _post(
        harness,
        {"title": "할 일 앱 분석", "description": "설명", "upload_method": "file"},
        files,
    )

    assert response.status_code == 201
    body = response.json()
    assert set(body) == TASK_FIELDS
    assert body["task_number"] == 3
    assert body["uploaded_code"]["total_files"] == 2
    harness.code.prepare_files.assert_called_once_with(
        [("app.py", b"x = 1\n"), ("util.py", b"y = 2\n")]
    )
    harness.tasks.create.assert_awaited_once_with(
        USER_ID, PROJECT_ID, "할 일 앱 분석", "설명", upload_method="file"
    )
    task = harness.tasks.create.return_value
    prepared = harness.code.prepare_files.return_value
    harness.code.store.assert_awaited_once_with(USER_ID, task, prepared)


def test_create_starts_document_generation_only_after_the_code_is_stored():
    harness = _Harness()
    order: list[str] = []
    harness.code.store.side_effect = lambda *_: order.append("store") or _uploaded_code()
    harness.tasks.start_document_generation.side_effect = lambda *_: order.append("start")
    files = [("files", ("app.py", b"x = 1\n", "text/x-python"))]

    response = _post(harness, {"title": "할 일 앱 분석", "upload_method": "file"}, files)

    assert response.status_code == 201
    assert order == ["store", "start"]
    harness.tasks.start_document_generation.assert_awaited_once_with(
        harness.tasks.create.return_value
    )


def test_create_does_not_start_generation_when_the_upload_is_invalid():
    harness = _Harness()
    harness.code.prepare_files.side_effect = AppError(400, "empty_file", "빈 파일")
    files = [("files", ("app.py", b"", "text/x-python"))]

    response = _post(harness, {"title": "할 일 앱 분석", "upload_method": "file"}, files)

    assert response.status_code == 400
    harness.tasks.start_document_generation.assert_not_awaited()


def test_create_with_folder_upload_passes_relative_paths_as_file_names():
    harness = _Harness()
    files = [("files", ("proj/src/app.py", b"x = 1\n", "text/x-python"))]

    response = _post(harness, {"title": "폴더 업로드", "upload_method": "folder"}, files)

    assert response.status_code == 201
    harness.code.prepare_folder.assert_called_once_with([("proj/src/app.py", b"x = 1\n")])
    harness.code.prepare_files.assert_not_called()


def test_create_with_pasted_code():
    harness = _Harness()

    response = _post(
        harness,
        {
            "title": "붙여넣기 코드",
            "upload_method": "paste",
            "code": "print('hi')",
            "language": "python",
        },
    )

    assert response.status_code == 201
    harness.code.prepare_paste.assert_called_once_with("print('hi')", "python")
    assert harness.tasks.create.await_args.kwargs == {"upload_method": "paste"}


@pytest.mark.parametrize(
    "data",
    [
        {"title": "코드 없음 태스크", "upload_method": "paste", "language": "python"},
        {"title": "언어 없음 태스크", "upload_method": "paste", "code": "x"},
    ],
)
def test_create_paste_requires_code_and_language(data: dict):
    harness = _Harness()

    response = _post(harness, data)

    assert response.status_code == 400
    assert response.json()["error"] == "validation_error"
    harness.tasks.create.assert_not_awaited()


@pytest.mark.parametrize("method", ["file", "folder"])
def test_create_without_files_lets_the_service_report_no_files(method: str):
    harness = _Harness()
    no_files = AppError(400, "no_files", "업로드할 파일을 한 개 이상 선택하세요.")
    harness.code.prepare_files.side_effect = no_files
    harness.code.prepare_folder.side_effect = no_files

    response = _post(harness, {"title": "파일 없음 태스크", "upload_method": method})

    assert response.status_code == 400
    assert response.json()["error"] == "no_files"
    harness.tasks.create.assert_not_awaited()


def test_create_rejects_unknown_upload_method():
    harness = _Harness()

    response = _post(harness, {"title": "알 수 없는 방식", "upload_method": "zip"})

    assert response.status_code == 400
    assert response.json()["error"] == "validation_error"
    harness.tasks.create.assert_not_awaited()


def test_create_requires_title_and_upload_method():
    harness = _Harness()

    assert _post(harness, {"upload_method": "file"}).status_code == 400
    assert _post(harness, {"title": "방식 없는 태스크"}).status_code == 400


def test_create_maps_upload_validation_errors_and_never_creates_a_task():
    harness = _Harness()
    harness.code.prepare_files.side_effect = AppError(
        413, "upload_too_large", "업로드 전체 크기가 10MB를 초과합니다."
    )
    files = [("files", ("big.py", b"x", "text/plain"))]

    response = _post(harness, {"title": "큰 파일 업로드", "upload_method": "file"}, files)

    assert response.status_code == 413
    assert response.json()["error"] == "upload_too_large"
    harness.tasks.create.assert_not_awaited()
    harness.code.store.assert_not_awaited()


def test_create_maps_task_validation_errors():
    harness = _Harness()
    harness.tasks.create.side_effect = AppError(
        400, "validation_error", "제목 오류", details={"field": "title"}
    )
    files = [("files", ("a.py", b"x", "text/plain"))]

    response = _post(harness, {"title": "짧음", "upload_method": "file"}, files)

    assert response.status_code == 400
    assert response.json()["details"] == {"field": "title"}
    harness.code.store.assert_not_awaited()


def test_create_in_someone_elses_project_is_forbidden():
    harness = _Harness()
    harness.tasks.create.side_effect = ForbiddenException()
    files = [("files", ("a.py", b"x", "text/plain"))]

    response = _post(harness, {"title": "남의 프로젝트", "upload_method": "file"}, files)

    assert response.status_code == 403
    harness.code.store.assert_not_awaited()


def test_create_reads_at_most_one_byte_over_the_limit_per_file():
    """An oversized file is rejected by validation, not buffered without bound."""
    harness = _Harness()
    from src.utils.file_validator import MAX_UPLOAD_SIZE_BYTES

    files = [("files", ("big.py", b"x" * (MAX_UPLOAD_SIZE_BYTES + 100), "text/plain"))]

    _post(harness, {"title": "큰 파일 업로드", "upload_method": "file"}, files)

    ((passed,),) = harness.code.prepare_files.call_args.args
    assert len(passed[1]) == MAX_UPLOAD_SIZE_BYTES + 1


# ---------------------------------------------------------------- GET /tasks/{id}


def test_get_task_returns_the_task():
    harness = _Harness()

    response = harness.client.get(TASK_PATH, headers=harness.headers())

    assert response.status_code == 200
    body = response.json()
    assert set(body) == TASK_FIELDS
    assert body["id"] == str(TASK_ID)
    assert body["project_id"] == str(PROJECT_ID)
    harness.tasks.get_owned.assert_awaited_once_with(TASK_ID, USER_ID)


def test_get_task_without_upload_has_null_summary():
    harness = _Harness()
    harness.tasks.get_owned.return_value = _task(with_upload=False)

    body = harness.client.get(TASK_PATH, headers=harness.headers()).json()

    assert body["uploaded_code"] is None


def test_get_task_maps_not_found_and_forbidden():
    harness = _Harness()
    harness.tasks.get_owned.side_effect = NotFoundException("없음")
    assert harness.client.get(TASK_PATH, headers=harness.headers()).status_code == 404

    harness.tasks.get_owned.side_effect = ForbiddenException()
    assert harness.client.get(TASK_PATH, headers=harness.headers()).status_code == 403


# ---------------------------------------------------------------- PATCH /tasks/{id}


def test_patch_updates_only_the_sent_fields():
    harness = _Harness()
    harness.tasks.update.return_value = _task(title="바뀐 제목입니다")

    response = harness.client.patch(
        TASK_PATH, json={"title": "바뀐 제목입니다"}, headers=harness.headers()
    )

    assert response.status_code == 200
    assert response.json()["title"] == "바뀐 제목입니다"
    harness.tasks.update.assert_awaited_once_with(TASK_ID, USER_ID, title="바뀐 제목입니다")


def test_patch_null_description_clears_it():
    harness = _Harness()

    harness.client.patch(TASK_PATH, json={"description": None}, headers=harness.headers())

    harness.tasks.update.assert_awaited_once_with(TASK_ID, USER_ID, description=None)


def test_patch_rejects_null_title():
    harness = _Harness()

    response = harness.client.patch(TASK_PATH, json={"title": None}, headers=harness.headers())

    assert response.status_code == 400
    harness.tasks.update.assert_not_awaited()


def test_patch_ignores_task_number_and_other_fields():
    harness = _Harness()

    harness.client.patch(
        TASK_PATH, json={"task_number": 99, "title": "바뀐 제목입니다"}, headers=harness.headers()
    )

    harness.tasks.update.assert_awaited_once_with(TASK_ID, USER_ID, title="바뀐 제목입니다")


def test_patch_maps_service_errors():
    harness = _Harness()
    harness.tasks.update.side_effect = AppError(
        400, "validation_error", "제목 오류", details={"field": "title"}
    )
    assert (
        harness.client.patch(TASK_PATH, json={"title": "x"}, headers=harness.headers()).status_code
        == 400
    )

    harness.tasks.update.side_effect = ForbiddenException()
    assert (
        harness.client.patch(TASK_PATH, json={"title": "x"}, headers=harness.headers()).status_code
        == 403
    )


# ---------------------------------------------------------------- DELETE /tasks/{id}


def test_delete_soft_deletes_and_returns_204():
    harness = _Harness()

    response = harness.client.delete(TASK_PATH, headers=harness.headers())

    assert response.status_code == 204
    assert response.content == b""
    harness.tasks.soft_delete.assert_awaited_once_with(TASK_ID, USER_ID)


def test_delete_maps_not_found_and_forbidden():
    harness = _Harness()
    harness.tasks.soft_delete.side_effect = NotFoundException("없음")
    assert harness.client.delete(TASK_PATH, headers=harness.headers()).status_code == 404

    harness.tasks.soft_delete.side_effect = ForbiddenException()
    assert harness.client.delete(TASK_PATH, headers=harness.headers()).status_code == 403


# ---------------------------------------------------------------- GET /tasks/{id}/code


def test_get_code_returns_summary_and_files_with_content():
    harness = _Harness()
    stored = CodeFile(
        id=uuid.uuid4(),
        file_name="app.py",
        file_path="proj/app.py",
        file_extension=".py",
        file_size_bytes=6,
        storage_path="u/t/f.py",
    )
    harness.code.get_code.return_value = [CodeFileContent(stored, "x = 1\n", "python")]

    response = harness.client.get(f"{TASK_PATH}/code", headers=harness.headers())

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"task_id", *UPLOAD_FIELDS, "files"}
    assert body["task_id"] == str(TASK_ID)
    assert body["total_files"] == 2
    assert body["files"] == [
        {
            "id": str(stored.id),
            "file_name": "app.py",
            "file_path": "proj/app.py",
            "file_extension": ".py",
            "file_size_bytes": 6,
            "language": "python",
            "content": "x = 1\n",
        }
    ]
    assert "storage_path" not in body["files"][0]  # server-side location is never exposed
    harness.tasks.get_owned.assert_awaited_once_with(TASK_ID, USER_ID)


def test_get_code_without_an_upload_is_not_found():
    harness = _Harness()
    harness.tasks.get_owned.return_value = _task(with_upload=False)
    harness.code.get_code.side_effect = NotFoundException("업로드된 코드가 없습니다.")

    response = harness.client.get(f"{TASK_PATH}/code", headers=harness.headers())

    assert response.status_code == 404


def test_get_code_checks_ownership_first():
    harness = _Harness()
    harness.tasks.get_owned.side_effect = ForbiddenException()

    response = harness.client.get(f"{TASK_PATH}/code", headers=harness.headers())

    assert response.status_code == 403
    harness.code.get_code.assert_not_awaited()
