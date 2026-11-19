import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from src import main
from src.api.dependencies import get_project_service
from src.api.exceptions import AppError, ForbiddenException, NotFoundException
from src.db.session import get_session
from src.models import Project, User
from src.services.project_service import ProjectService
from src.utils import jwt as tokens

SECRET = "test-secret-key-that-is-at-least-32-bytes-long"
USER_ID = uuid.uuid4()
PROJECTS_PATH = "/api/v1/projects"
CREATED = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)
UPDATED = datetime(2026, 11, 2, 9, 0, tzinfo=UTC)
ACTIVITY = datetime(2026, 11, 3, 9, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", SECRET)
    monkeypatch.delenv("JWT_ACCESS_TOKEN_MINUTES", raising=False)
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)


def _project(**overrides: object) -> Project:
    values: dict[str, object] = {
        "id": uuid.uuid4(),
        "user_id": USER_ID,
        "title": "Todo 앱",
        "description": "할 일 앱 분석",
        "created_at": CREATED,
        "updated_at": UPDATED,
        "last_activity_at": ACTIVITY,
        "deletion_status": Project.ACTIVE,
    }
    values.update(overrides)
    return Project(**values)


class _Harness:
    """The real app with ProjectService replaced by a double; only the HTTP contract is tested."""

    def __init__(self) -> None:
        self.projects = MagicMock(spec=ProjectService)
        self.projects.get_user_projects = AsyncMock(return_value=[])
        self.projects.create = AsyncMock(return_value=_project())
        self.projects.get_owned = AsyncMock(return_value=_project())
        self.projects.update = AsyncMock(return_value=_project())
        self.projects.soft_delete = AsyncMock(return_value=None)

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
        app.dependency_overrides[get_project_service] = lambda: self.projects
        self.client = TestClient(app, raise_server_exceptions=False)

    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {tokens.create_access_token(str(USER_ID))}"}


# ---------------------------------------------------------------- wiring


def test_project_routes_are_mounted_under_api_v1():
    app = main.create_app()
    routes = {
        (route.path, method) for route in app.routes for method in getattr(route, "methods", [])
    }

    assert (PROJECTS_PATH, "GET") in routes
    assert (PROJECTS_PATH, "POST") in routes
    assert (f"{PROJECTS_PATH}/{{project_id}}", "GET") in routes
    assert (f"{PROJECTS_PATH}/{{project_id}}", "PATCH") in routes
    assert (f"{PROJECTS_PATH}/{{project_id}}", "DELETE") in routes


def test_get_project_service_wraps_the_request_session():
    session = MagicMock()

    assert isinstance(get_project_service(session), ProjectService)


# ---------------------------------------------------------------- GET /projects


def test_list_projects_returns_projects_wrapper_with_all_contract_fields():
    harness = _Harness()
    project = _project()
    harness.projects.get_user_projects.return_value = [project]

    response = harness.client.get(PROJECTS_PATH, headers=harness.headers())

    assert response.status_code == 200
    assert response.json() == {
        "projects": [
            {
                "id": str(project.id),
                "title": "Todo 앱",
                "description": "할 일 앱 분석",
                "created_at": "2026-11-01T09:00:00Z",
                "updated_at": "2026-11-02T09:00:00Z",
                "last_activity_at": "2026-11-03T09:00:00Z",
                "task_count": 0,
                "completed_task_count": 0,
                "progress_percent": 0,
            }
        ]
    }


def test_list_projects_keeps_the_service_order_and_null_description():
    harness = _Harness()
    first, second = _project(title="최근"), _project(title="오래됨", description=None)
    harness.projects.get_user_projects.return_value = [first, second]

    response = harness.client.get(PROJECTS_PATH, headers=harness.headers())

    body = response.json()["projects"]
    assert [p["title"] for p in body] == ["최근", "오래됨"]
    assert body[1]["description"] is None


def test_list_projects_is_empty_wrapper_when_user_has_none():
    harness = _Harness()

    response = harness.client.get(PROJECTS_PATH, headers=harness.headers())

    assert response.status_code == 200
    assert response.json() == {"projects": []}


def test_list_projects_asks_the_service_for_the_authenticated_users_projects_only():
    harness = _Harness()

    harness.client.get(PROJECTS_PATH, headers=harness.headers())

    harness.projects.get_user_projects.assert_awaited_once_with(USER_ID)


def test_list_projects_never_exposes_trash_fields():
    harness = _Harness()
    harness.projects.get_user_projects.return_value = [_project()]

    response = harness.client.get(PROJECTS_PATH, headers=harness.headers())

    keys = set(response.json()["projects"][0])
    assert not keys & {"deletion_status", "trashed_at", "scheduled_deletion_at", "user_id"}


def test_list_projects_without_authorization_is_401():
    harness = _Harness()

    response = harness.client.get(PROJECTS_PATH)

    assert response.status_code == 401
    assert response.json()["error"] == "unauthorized"
    harness.projects.get_user_projects.assert_not_awaited()


# ---------------------------------------------------------------- POST /projects


def test_create_project_returns_201_with_the_created_project():
    harness = _Harness()
    project = _project()
    harness.projects.create.return_value = project

    response = harness.client.post(
        PROJECTS_PATH,
        json={"title": "Todo 앱", "description": "할 일 앱 분석"},
        headers=harness.headers(),
    )

    assert response.status_code == 201
    assert response.json() == {
        "id": str(project.id),
        "title": "Todo 앱",
        "description": "할 일 앱 분석",
        "created_at": "2026-11-01T09:00:00Z",
        "updated_at": "2026-11-02T09:00:00Z",
        "last_activity_at": "2026-11-03T09:00:00Z",
        "task_count": 0,
        "completed_task_count": 0,
        "progress_percent": 0,
    }


def test_create_project_passes_the_authenticated_user_title_and_description_to_the_service():
    harness = _Harness()

    harness.client.post(
        PROJECTS_PATH,
        json={"title": "Todo 앱", "description": "설명"},
        headers=harness.headers(),
    )

    harness.projects.create.assert_awaited_once_with(USER_ID, "Todo 앱", "설명")


@pytest.mark.parametrize("body", [{"title": "Todo 앱"}, {"title": "Todo 앱", "description": None}])
def test_create_project_description_is_optional_and_nullable(body):
    harness = _Harness()

    response = harness.client.post(PROJECTS_PATH, json=body, headers=harness.headers())

    assert response.status_code == 201
    harness.projects.create.assert_awaited_once_with(USER_ID, "Todo 앱", None)


def test_create_project_ignores_a_user_id_sent_in_the_body():
    harness = _Harness()

    harness.client.post(
        PROJECTS_PATH,
        json={"title": "Todo 앱", "user_id": str(uuid.uuid4())},
        headers=harness.headers(),
    )

    harness.projects.create.assert_awaited_once_with(USER_ID, "Todo 앱", None)


@pytest.mark.parametrize(
    "body",
    [{}, {"description": "desc"}, {"title": None}, {"title": 1}, {"title": "a", "description": 1}],
)
def test_create_project_with_missing_or_malformed_fields_is_400(body):
    harness = _Harness()

    response = harness.client.post(PROJECTS_PATH, json=body, headers=harness.headers())

    assert response.status_code == 400
    assert response.json()["error"] == "validation_error"
    harness.projects.create.assert_not_awaited()


def test_create_project_without_a_json_body_is_400():
    harness = _Harness()

    response = harness.client.post(PROJECTS_PATH, headers=harness.headers())

    assert response.status_code == 400
    harness.projects.create.assert_not_awaited()


def test_create_project_title_rejected_by_the_service_is_400_with_field_detail():
    harness = _Harness()
    harness.projects.create.side_effect = AppError(
        400, "validation_error", "제목 오류", details={"field": "title"}
    )

    response = harness.client.post(PROJECTS_PATH, json={"title": "   "}, headers=harness.headers())

    assert response.status_code == 400
    assert response.json() == {
        "error": "validation_error",
        "message": "제목 오류",
        "details": {"field": "title"},
    }


def test_create_project_without_authorization_is_401():
    harness = _Harness()

    response = harness.client.post(PROJECTS_PATH, json={"title": "Todo 앱"})

    assert response.status_code == 401
    harness.projects.create.assert_not_awaited()


# ---------------------------------------------------------------- GET /projects/{project_id}


def test_get_project_returns_200_with_the_project():
    harness = _Harness()
    project = _project()
    harness.projects.get_owned.return_value = project

    response = harness.client.get(f"{PROJECTS_PATH}/{project.id}", headers=harness.headers())

    assert response.status_code == 200
    assert response.json() == {
        "id": str(project.id),
        "title": "Todo 앱",
        "description": "할 일 앱 분석",
        "created_at": "2026-11-01T09:00:00Z",
        "updated_at": "2026-11-02T09:00:00Z",
        "last_activity_at": "2026-11-03T09:00:00Z",
        "task_count": 0,
        "completed_task_count": 0,
        "progress_percent": 0,
    }


def test_get_project_checks_ownership_for_the_authenticated_user():
    harness = _Harness()
    project_id = uuid.uuid4()

    harness.client.get(f"{PROJECTS_PATH}/{project_id}", headers=harness.headers())

    harness.projects.get_owned.assert_awaited_once_with(project_id, USER_ID)


def test_get_project_of_another_user_is_403():
    harness = _Harness()
    harness.projects.get_owned.side_effect = ForbiddenException("권한 없음")

    response = harness.client.get(f"{PROJECTS_PATH}/{uuid.uuid4()}", headers=harness.headers())

    assert response.status_code == 403
    assert response.json() == {"error": "forbidden", "message": "권한 없음"}


def test_get_missing_or_trashed_project_is_404():
    harness = _Harness()
    harness.projects.get_owned.side_effect = NotFoundException("없음")

    response = harness.client.get(f"{PROJECTS_PATH}/{uuid.uuid4()}", headers=harness.headers())

    assert response.status_code == 404
    assert response.json() == {"error": "not_found", "message": "없음"}


def test_get_project_with_a_non_uuid_id_is_400():
    harness = _Harness()

    response = harness.client.get(f"{PROJECTS_PATH}/not-a-uuid", headers=harness.headers())

    assert response.status_code == 400
    assert response.json()["error"] == "validation_error"
    harness.projects.get_owned.assert_not_awaited()


def test_get_project_without_authorization_is_401():
    harness = _Harness()

    response = harness.client.get(f"{PROJECTS_PATH}/{uuid.uuid4()}")

    assert response.status_code == 401
    harness.projects.get_owned.assert_not_awaited()


# ---------------------------------------------------------------- PATCH /projects/{project_id}


def test_update_project_returns_200_with_the_updated_project():
    harness = _Harness()
    project = _project(title="새 제목", description=None)
    harness.projects.update.return_value = project

    response = harness.client.patch(
        f"{PROJECTS_PATH}/{project.id}", json={"title": "새 제목"}, headers=harness.headers()
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": str(project.id),
        "title": "새 제목",
        "description": None,
        "created_at": "2026-11-01T09:00:00Z",
        "updated_at": "2026-11-02T09:00:00Z",
        "last_activity_at": "2026-11-03T09:00:00Z",
        "task_count": 0,
        "completed_task_count": 0,
        "progress_percent": 0,
    }


def test_update_project_with_only_title_leaves_description_unset():
    harness = _Harness()
    project_id = uuid.uuid4()

    harness.client.patch(
        f"{PROJECTS_PATH}/{project_id}", json={"title": "새 제목"}, headers=harness.headers()
    )

    harness.projects.update.assert_awaited_once_with(project_id, USER_ID, title="새 제목")


def test_update_project_with_only_description_leaves_title_unset():
    harness = _Harness()
    project_id = uuid.uuid4()

    harness.client.patch(
        f"{PROJECTS_PATH}/{project_id}", json={"description": "새 설명"}, headers=harness.headers()
    )

    harness.projects.update.assert_awaited_once_with(project_id, USER_ID, description="새 설명")


def test_update_project_with_null_description_sends_none_to_clear_it():
    harness = _Harness()
    project_id = uuid.uuid4()

    harness.client.patch(
        f"{PROJECTS_PATH}/{project_id}", json={"description": None}, headers=harness.headers()
    )

    harness.projects.update.assert_awaited_once_with(project_id, USER_ID, description=None)


def test_update_project_with_both_fields_sends_both():
    harness = _Harness()
    project_id = uuid.uuid4()

    harness.client.patch(
        f"{PROJECTS_PATH}/{project_id}",
        json={"title": "새 제목", "description": "새 설명"},
        headers=harness.headers(),
    )

    harness.projects.update.assert_awaited_once_with(
        project_id, USER_ID, title="새 제목", description="새 설명"
    )


def test_update_project_with_empty_body_changes_nothing_but_still_checks_ownership():
    harness = _Harness()
    project_id = uuid.uuid4()

    response = harness.client.patch(
        f"{PROJECTS_PATH}/{project_id}", json={}, headers=harness.headers()
    )

    assert response.status_code == 200
    harness.projects.update.assert_awaited_once_with(project_id, USER_ID)


@pytest.mark.parametrize(
    "body", [{"title": None}, {"title": 1}, {"description": 1}, {"title": None, "description": "d"}]
)
def test_update_project_with_null_or_malformed_fields_is_400(body):
    harness = _Harness()

    response = harness.client.patch(
        f"{PROJECTS_PATH}/{uuid.uuid4()}", json=body, headers=harness.headers()
    )

    assert response.status_code == 400
    assert response.json()["error"] == "validation_error"
    harness.projects.update.assert_not_awaited()


def test_update_project_title_rejected_by_the_service_is_400_with_field_detail():
    harness = _Harness()
    harness.projects.update.side_effect = AppError(
        400, "validation_error", "제목 오류", details={"field": "title"}
    )

    response = harness.client.patch(
        f"{PROJECTS_PATH}/{uuid.uuid4()}", json={"title": "  "}, headers=harness.headers()
    )

    assert response.status_code == 400
    assert response.json()["details"] == {"field": "title"}


def test_update_project_of_another_user_is_403():
    harness = _Harness()
    harness.projects.update.side_effect = ForbiddenException("권한 없음")

    response = harness.client.patch(
        f"{PROJECTS_PATH}/{uuid.uuid4()}", json={"title": "가로채기"}, headers=harness.headers()
    )

    assert response.status_code == 403
    assert response.json() == {"error": "forbidden", "message": "권한 없음"}


def test_update_missing_or_trashed_project_is_404():
    harness = _Harness()
    harness.projects.update.side_effect = NotFoundException("없음")

    response = harness.client.patch(
        f"{PROJECTS_PATH}/{uuid.uuid4()}", json={"title": "x"}, headers=harness.headers()
    )

    assert response.status_code == 404
    assert response.json() == {"error": "not_found", "message": "없음"}


def test_update_project_with_a_non_uuid_id_is_400():
    harness = _Harness()

    response = harness.client.patch(
        f"{PROJECTS_PATH}/not-a-uuid", json={"title": "x"}, headers=harness.headers()
    )

    assert response.status_code == 400
    harness.projects.update.assert_not_awaited()


def test_update_project_without_authorization_is_401():
    harness = _Harness()

    response = harness.client.patch(f"{PROJECTS_PATH}/{uuid.uuid4()}", json={"title": "x"})

    assert response.status_code == 401
    harness.projects.update.assert_not_awaited()


# ---------------------------------------------------------------- DELETE /projects/{project_id}


def test_delete_project_returns_204_without_a_body():
    harness = _Harness()

    response = harness.client.delete(f"{PROJECTS_PATH}/{uuid.uuid4()}", headers=harness.headers())

    assert response.status_code == 204
    assert response.content == b""


def test_delete_project_soft_deletes_for_the_authenticated_user():
    harness = _Harness()
    project_id = uuid.uuid4()

    harness.client.delete(f"{PROJECTS_PATH}/{project_id}", headers=harness.headers())

    harness.projects.soft_delete.assert_awaited_once_with(project_id, USER_ID)


def test_delete_project_of_another_user_is_403():
    harness = _Harness()
    harness.projects.soft_delete.side_effect = ForbiddenException("권한 없음")

    response = harness.client.delete(f"{PROJECTS_PATH}/{uuid.uuid4()}", headers=harness.headers())

    assert response.status_code == 403
    assert response.json() == {"error": "forbidden", "message": "권한 없음"}


def test_delete_missing_or_already_trashed_project_is_404():
    harness = _Harness()
    harness.projects.soft_delete.side_effect = NotFoundException("없음")

    response = harness.client.delete(f"{PROJECTS_PATH}/{uuid.uuid4()}", headers=harness.headers())

    assert response.status_code == 404
    assert response.json() == {"error": "not_found", "message": "없음"}


def test_delete_project_with_a_non_uuid_id_is_400():
    harness = _Harness()

    response = harness.client.delete(f"{PROJECTS_PATH}/not-a-uuid", headers=harness.headers())

    assert response.status_code == 400
    harness.projects.soft_delete.assert_not_awaited()


def test_delete_project_without_authorization_is_401():
    harness = _Harness()

    response = harness.client.delete(f"{PROJECTS_PATH}/{uuid.uuid4()}")

    assert response.status_code == 401
    harness.projects.soft_delete.assert_not_awaited()
