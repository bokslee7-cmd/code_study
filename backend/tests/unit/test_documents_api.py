import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from src import main
from src.api.dependencies import (
    get_code_upload_service,
    get_document_queue_service,
    get_task_service,
)
from src.api.exceptions import ForbiddenException, NotFoundException
from src.db.session import get_session
from src.models import CodeFile, LearningDocument, Task, User
from src.services.code_analysis.code_upload_service import CodeFileContent, CodeUploadService
from src.services.document.document_queue_service import DocumentQueueService
from src.services.task_service import TaskService
from src.utils import jwt as tokens

SECRET = "test-secret-key-that-is-at-least-32-bytes-long"
USER_ID = uuid.uuid4()
TASK_ID = uuid.uuid4()
DOCUMENT_ID = uuid.uuid4()
DOCUMENT_PATH = f"/api/v1/tasks/{TASK_ID}/document"
STATUS_PATH = f"{DOCUMENT_PATH}/status"
STARTED = datetime(2026, 11, 18, 12, 0, tzinfo=UTC)
COMPLETED = STARTED + timedelta(seconds=40)

DOCUMENT_FIELDS = {
    "id",
    "task_id",
    "status",
    "content",
    "failed_chapters",
    "generation_error",
    "generation_started_at",
    "generation_completed_at",
    "files",
}
STATUS_FIELDS = {
    "task_id",
    "status",
    "generation_started_at",
    "generation_completed_at",
    "generation_error",
    "failed_chapters",
    "estimated_remaining_seconds",
}


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", SECRET)
    monkeypatch.delenv("JWT_ACCESS_TOKEN_MINUTES", raising=False)
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)


def _document(status: str | None = "completed", **overrides: object) -> LearningDocument:
    values: dict[str, object] = {
        "id": DOCUMENT_ID,
        "task_id": TASK_ID,
        "content": {f"chapter{n}": {"title": f"챕터 {n}"} for n in range(1, 8)},
        "generation_status": status,
        "generation_started_at": STARTED,
        "generation_completed_at": COMPLETED,
        "generation_error": None,
    }
    values.update(overrides)
    return LearningDocument(**values)


class _Harness:
    def __init__(self) -> None:
        task = Task(id=TASK_ID, project_id=uuid.uuid4(), task_number=1, title="태스크 제목")
        self.tasks = MagicMock(spec=TaskService)
        self.tasks.get_owned = AsyncMock(return_value=task)

        self.queue = MagicMock(spec=DocumentQueueService)
        self.queue.get_document = AsyncMock(return_value=_document())

        stored = CodeFile(id=uuid.uuid4(), file_name="app.py", file_path="src/app.py")
        self.code = MagicMock(spec=CodeUploadService)
        self.code.get_code = AsyncMock(return_value=[CodeFileContent(stored, "x = 1\n", "python")])

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
        app.dependency_overrides[get_document_queue_service] = lambda: self.queue
        self.client = TestClient(app, raise_server_exceptions=False)

    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {tokens.create_access_token(str(USER_ID))}"}


# ---------------------------------------------------------------- wiring / auth


def test_document_routes_are_mounted_under_api_v1():
    app = main.create_app()
    routes = {
        (route.path, method) for route in app.routes for method in getattr(route, "methods", [])
    }

    assert ("/api/v1/tasks/{task_id}/document", "GET") in routes
    assert ("/api/v1/tasks/{task_id}/document/status", "GET") in routes


@pytest.mark.parametrize("path", [DOCUMENT_PATH, STATUS_PATH])
def test_both_endpoints_require_login(path: str):
    response = _Harness().client.get(path)

    assert response.status_code == 401
    assert response.json()["error"] == "unauthorized"


@pytest.mark.parametrize("path", [DOCUMENT_PATH, STATUS_PATH])
def test_malformed_task_id_is_a_validation_error(path: str):
    harness = _Harness()

    malformed = path.replace(str(TASK_ID), "not-a-uuid")
    response = harness.client.get(malformed, headers=harness.headers())

    assert response.status_code == 400
    assert response.json()["error"] == "validation_error"


# ---------------------------------------------------------------- GET /tasks/{id}/document


def test_document_returns_content_status_and_the_uploaded_files():
    harness = _Harness()

    response = harness.client.get(DOCUMENT_PATH, headers=harness.headers())

    assert response.status_code == 200
    body = response.json()
    assert set(body) == DOCUMENT_FIELDS
    assert body["id"] == str(DOCUMENT_ID)
    assert body["task_id"] == str(TASK_ID)
    assert body["status"] == "completed"
    assert set(body["content"]) == {f"chapter{n}" for n in range(1, 8)}
    assert body["content"]["chapter1"] == {"title": "챕터 1"}
    assert body["failed_chapters"] == []
    assert body["generation_error"] is None
    assert body["generation_started_at"].startswith("2026-11-18T12:00:00")
    assert body["generation_completed_at"].startswith("2026-11-18T12:00:40")
    assert body["files"] == [{"path": "src/app.py", "language": "python", "content": "x = 1\n"}]
    harness.tasks.get_owned.assert_awaited_once_with(TASK_ID, USER_ID)
    harness.queue.get_document.assert_awaited_once_with(TASK_ID)


def test_document_file_path_falls_back_to_the_file_name():
    harness = _Harness()
    stored = CodeFile(id=uuid.uuid4(), file_name="code.py", file_path=None)
    harness.code.get_code.return_value = [CodeFileContent(stored, "y = 2\n", "python")]

    body = harness.client.get(DOCUMENT_PATH, headers=harness.headers()).json()

    assert body["files"][0]["path"] == "code.py"


def test_document_lists_chapters_that_failed_to_generate():
    harness = _Harness()
    content = {f"chapter{n}": {"title": "ok"} for n in range(1, 8)}
    content["chapter4"] = {"generation_failed": True}
    harness.queue.get_document.return_value = _document(
        generation_error="일부 챕터를 만들지 못했습니다: chapter4", content=content
    )

    body = harness.client.get(DOCUMENT_PATH, headers=harness.headers()).json()

    assert body["failed_chapters"] == ["chapter4"]
    assert body["generation_error"] == "일부 챕터를 만들지 못했습니다: chapter4"


def test_document_that_is_still_generating_is_returned_with_its_status():
    harness = _Harness()
    harness.queue.get_document.return_value = _document("in_progress", generation_completed_at=None)

    response = harness.client.get(DOCUMENT_PATH, headers=harness.headers())

    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"
    assert response.json()["generation_completed_at"] is None


def test_missing_document_row_is_a_korean_404():
    harness = _Harness()
    harness.queue.get_document.return_value = None

    response = harness.client.get(DOCUMENT_PATH, headers=harness.headers())

    assert response.status_code == 404
    body = response.json()
    assert body["error"] == "not_found"
    assert "학습 문서" in body["message"]
    harness.code.get_code.assert_not_awaited()


def test_document_of_a_missing_task_is_404_and_never_touches_the_document():
    harness = _Harness()
    harness.tasks.get_owned.side_effect = NotFoundException("태스크 없음")

    response = harness.client.get(DOCUMENT_PATH, headers=harness.headers())

    assert response.status_code == 404
    harness.queue.get_document.assert_not_awaited()


def test_document_of_someone_elses_task_is_refused_like_the_other_task_endpoints():
    harness = _Harness()
    harness.tasks.get_owned.side_effect = ForbiddenException()

    response = harness.client.get(DOCUMENT_PATH, headers=harness.headers())

    assert response.status_code == 403
    harness.queue.get_document.assert_not_awaited()


# ---------------------------------------------------------------- GET /tasks/{id}/document/status


def test_status_of_a_completed_document_has_no_estimate():
    harness = _Harness()

    response = harness.client.get(STATUS_PATH, headers=harness.headers())

    assert response.status_code == 200
    body = response.json()
    assert set(body) == STATUS_FIELDS
    assert body["task_id"] == str(TASK_ID)
    assert body["status"] == "completed"
    assert body["failed_chapters"] == []
    assert body["estimated_remaining_seconds"] is None
    harness.code.get_code.assert_not_awaited()  # the status poll stays cheap


def test_status_while_in_progress_estimates_the_remaining_seconds_from_180():
    harness = _Harness()
    started = datetime.now(UTC) - timedelta(seconds=30)
    harness.queue.get_document.return_value = _document(
        "in_progress", generation_started_at=started, generation_completed_at=None
    )

    body = harness.client.get(STATUS_PATH, headers=harness.headers()).json()

    assert body["status"] == "in_progress"
    assert 148 <= body["estimated_remaining_seconds"] <= 150


def test_status_estimate_never_goes_below_zero():
    harness = _Harness()
    started = datetime.now(UTC) - timedelta(seconds=900)
    harness.queue.get_document.return_value = _document(
        "in_progress", generation_started_at=started, generation_completed_at=None
    )

    body = harness.client.get(STATUS_PATH, headers=harness.headers()).json()

    assert body["estimated_remaining_seconds"] == 0


def test_status_of_a_failed_document_carries_the_reason():
    harness = _Harness()
    harness.queue.get_document.return_value = _document(
        "failed", generation_error="문서 생성 중 오류가 발생했습니다."
    )

    body = harness.client.get(STATUS_PATH, headers=harness.headers()).json()

    assert body["status"] == "failed"
    assert body["generation_error"] == "문서 생성 중 오류가 발생했습니다."
    assert body["estimated_remaining_seconds"] is None


def test_status_treats_a_null_status_column_as_pending():
    harness = _Harness()
    harness.queue.get_document.return_value = _document(
        None, generation_started_at=None, generation_completed_at=None
    )

    body = harness.client.get(STATUS_PATH, headers=harness.headers()).json()

    assert body["status"] == "pending"


def test_status_without_a_document_row_is_404():
    harness = _Harness()
    harness.queue.get_document.return_value = None

    response = harness.client.get(STATUS_PATH, headers=harness.headers())

    assert response.status_code == 404
    assert "학습 문서" in response.json()["message"]


def test_status_of_someone_elses_task_is_refused():
    harness = _Harness()
    harness.tasks.get_owned.side_effect = ForbiddenException()

    response = harness.client.get(STATUS_PATH, headers=harness.headers())

    assert response.status_code == 403
    harness.queue.get_document.assert_not_awaited()
