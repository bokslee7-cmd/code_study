import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from src.api.exceptions import AppError, ForbiddenException, NotFoundException
from src.models import Project
from src.services.project_service import (
    MAX_TITLE_LENGTH,
    TRASH_RETENTION_DAYS,
    ProjectService,
)

USER_ID = uuid.uuid4()


def _session(found: object | None = None) -> MagicMock:
    """Async session double whose every query returns `found` as the single scalar."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = found
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    return session


def _sql(session: MagicMock) -> str:
    statement = session.execute.call_args.args[0]
    return str(statement.compile(compile_kwargs={"literal_binds": True}))


def _project(**overrides: object) -> Project:
    values: dict[str, object] = {
        "id": uuid.uuid4(),
        "user_id": USER_ID,
        "title": "내 첫 프로젝트",
        "description": "설명",
        "deletion_status": Project.ACTIVE,
    }
    values.update(overrides)
    return Project(**values)


def test_constants_follow_the_data_model():
    assert MAX_TITLE_LENGTH == 255  # projects.title is VARCHAR(255)
    assert TRASH_RETENTION_DAYS == 30  # scheduled_deletion_at = trashed_at + 30 days


# ---------------------------------------------------------------- create


async def test_create_saves_project_for_the_user():
    session = _session()
    project = await ProjectService(session).create(USER_ID, "Todo 앱", "할 일 앱 분석")

    session.add.assert_called_once_with(project)
    assert project.user_id == USER_ID
    assert project.title == "Todo 앱"
    assert project.description == "할 일 앱 분석"
    session.flush.assert_awaited_once()
    session.refresh.assert_awaited_once_with(project)


async def test_create_description_is_optional():
    project = await ProjectService(_session()).create(USER_ID, "Todo 앱")

    assert project.description is None


async def test_create_strips_surrounding_whitespace():
    project = await ProjectService(_session()).create(USER_ID, "  Todo 앱 ", "  설명\n")

    assert project.title == "Todo 앱"
    assert project.description == "설명"


async def test_create_turns_blank_description_into_none():
    project = await ProjectService(_session()).create(USER_ID, "Todo 앱", "   ")

    assert project.description is None


@pytest.mark.parametrize("title", ["", "   ", "\t\n"])
async def test_create_rejects_blank_title(title: str):
    session = _session()

    with pytest.raises(AppError) as exc_info:
        await ProjectService(session).create(USER_ID, title)

    assert exc_info.value.status_code == 400
    assert exc_info.value.error == "validation_error"
    assert exc_info.value.details == {"field": "title"}
    session.add.assert_not_called()


async def test_create_accepts_title_of_max_length():
    project = await ProjectService(_session()).create(USER_ID, "가" * MAX_TITLE_LENGTH)

    assert len(project.title) == MAX_TITLE_LENGTH


async def test_create_rejects_title_over_max_length():
    session = _session()

    with pytest.raises(AppError) as exc_info:
        await ProjectService(session).create(USER_ID, "가" * (MAX_TITLE_LENGTH + 1))

    assert exc_info.value.status_code == 400
    assert exc_info.value.details == {"field": "title"}
    session.add.assert_not_called()


# ---------------------------------------------------------------- get


async def test_get_returns_the_project():
    project = _project()
    session = _session(found=project)

    assert await ProjectService(session).get(project.id) is project
    assert project.id.hex in _sql(session).replace("-", "")


async def test_get_returns_none_when_missing():
    assert await ProjectService(_session(found=None)).get(uuid.uuid4()) is None


async def test_get_only_looks_at_active_projects():
    session = _session()
    await ProjectService(session).get(uuid.uuid4())

    assert "deletion_status = 'active'" in _sql(session)


# ---------------------------------------------------------------- update


async def test_update_changes_title_and_keeps_description():
    project = _project()
    session = _session(found=project)

    updated = await ProjectService(session).update(project.id, USER_ID, title="새 제목")

    assert updated is project
    assert project.title == "새 제목"
    assert project.description == "설명"
    session.flush.assert_awaited_once()
    session.refresh.assert_awaited_once_with(project)


async def test_update_changes_description_and_keeps_title():
    project = _project()

    await ProjectService(_session(found=project)).update(project.id, USER_ID, description="새 설명")

    assert project.title == "내 첫 프로젝트"
    assert project.description == "새 설명"


async def test_update_clears_description_with_none():
    project = _project()

    await ProjectService(_session(found=project)).update(project.id, USER_ID, description=None)

    assert project.description is None


async def test_update_turns_blank_description_into_none():
    project = _project()

    await ProjectService(_session(found=project)).update(project.id, USER_ID, description="  ")

    assert project.description is None


async def test_update_strips_whitespace():
    project = _project()

    await ProjectService(_session(found=project)).update(
        project.id, USER_ID, title="  새 제목 ", description=" 새 설명 "
    )

    assert project.title == "새 제목"
    assert project.description == "새 설명"


async def test_update_without_fields_changes_nothing():
    project = _project()

    await ProjectService(_session(found=project)).update(project.id, USER_ID)

    assert project.title == "내 첫 프로젝트"
    assert project.description == "설명"


@pytest.mark.parametrize("title", ["", "   ", "가" * (MAX_TITLE_LENGTH + 1)])
async def test_update_rejects_invalid_title_without_changing_anything(title: str):
    project = _project()
    session = _session(found=project)

    with pytest.raises(AppError) as exc_info:
        await ProjectService(session).update(
            project.id, USER_ID, title=title, description="바뀌면 안 됨"
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.details == {"field": "title"}
    assert project.title == "내 첫 프로젝트"
    assert project.description == "설명"
    session.flush.assert_not_awaited()


async def test_update_raises_not_found_for_missing_or_trashed_project():
    session = _session(found=None)

    with pytest.raises(NotFoundException) as exc_info:
        await ProjectService(session).update(uuid.uuid4(), USER_ID, title="새 제목")

    assert exc_info.value.status_code == 404
    session.flush.assert_not_awaited()


# ---------------------------------------------------------------- soft_delete


async def test_soft_delete_moves_project_to_trash_for_30_days():
    project = _project()
    session = _session(found=project)

    before = datetime.now(UTC)
    await ProjectService(session).soft_delete(project.id, USER_ID)
    after = datetime.now(UTC)

    assert project.deletion_status == Project.TRASHED
    assert project.trashed_at is not None
    assert before <= project.trashed_at <= after
    assert project.scheduled_deletion_at == project.trashed_at + timedelta(days=30)
    session.flush.assert_awaited_once()


async def test_soft_delete_keeps_the_row_and_its_content():
    project = _project()
    session = _session(found=project)
    session.delete = AsyncMock()

    await ProjectService(session).soft_delete(project.id, USER_ID)

    assert project.title == "내 첫 프로젝트"
    assert project.description == "설명"
    session.delete.assert_not_called()


async def test_soft_delete_raises_not_found_for_missing_or_already_trashed_project():
    session = _session(found=None)

    with pytest.raises(NotFoundException) as exc_info:
        await ProjectService(session).soft_delete(uuid.uuid4(), USER_ID)

    assert exc_info.value.status_code == 404
    session.flush.assert_not_awaited()


# ---------------------------------------------------------------- ownership (T045)

OTHER_USER_ID = uuid.uuid4()
FORBIDDEN_TEXT = "이 프로젝트에 접근할 권한이 없습니다."
NOT_FOUND_TEXT = "요청한 프로젝트를 찾을 수 없습니다. 삭제되었거나 존재하지 않는 프로젝트입니다."


async def test_get_owned_returns_the_project_for_its_owner():
    project = _project()

    found = await ProjectService(_session(found=project)).get_owned(project.id, USER_ID)

    assert found is project


async def test_get_owned_rejects_another_users_project_with_403():
    project = _project()

    with pytest.raises(ForbiddenException) as exc_info:
        await ProjectService(_session(found=project)).get_owned(project.id, OTHER_USER_ID)

    assert exc_info.value.status_code == 403
    assert exc_info.value.error == "forbidden"
    assert exc_info.value.message == FORBIDDEN_TEXT


async def test_get_owned_raises_404_for_missing_or_trashed_project():
    with pytest.raises(NotFoundException) as exc_info:
        await ProjectService(_session(found=None)).get_owned(uuid.uuid4(), USER_ID)

    assert exc_info.value.status_code == 404
    assert exc_info.value.message == NOT_FOUND_TEXT


async def test_missing_project_is_404_even_for_a_user_who_owns_nothing():
    # existence is checked before ownership, so "not found" never turns into "forbidden"
    with pytest.raises(NotFoundException):
        await ProjectService(_session(found=None)).get_owned(uuid.uuid4(), OTHER_USER_ID)


async def test_update_rejects_non_owner_and_changes_nothing():
    project = _project()
    session = _session(found=project)

    with pytest.raises(ForbiddenException):
        await ProjectService(session).update(
            project.id, OTHER_USER_ID, title="가로채기", description="가로채기"
        )

    assert project.title == "내 첫 프로젝트"
    assert project.description == "설명"
    session.flush.assert_not_awaited()


async def test_update_checks_ownership_before_validating_input():
    project = _project()

    with pytest.raises(ForbiddenException):  # not the 400 for the blank title
        await ProjectService(_session(found=project)).update(project.id, OTHER_USER_ID, title="")


async def test_soft_delete_rejects_non_owner_and_keeps_project_active():
    project = _project()
    session = _session(found=project)

    with pytest.raises(ForbiddenException):
        await ProjectService(session).soft_delete(project.id, OTHER_USER_ID)

    assert project.deletion_status == Project.ACTIVE
    assert project.trashed_at is None and project.scheduled_deletion_at is None
    session.flush.assert_not_awaited()


# ---------------------------------------------------------------- get_user_projects


def _list_session(rows: list[Project]) -> MagicMock:
    scalars = MagicMock()
    scalars.all.return_value = rows
    result = MagicMock()
    result.scalars.return_value = scalars
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)
    return session


async def test_get_user_projects_returns_the_rows_as_a_list():
    rows = [_project(title="A"), _project(title="B")]
    session = _list_session(rows)

    projects = await ProjectService(session).get_user_projects(USER_ID)

    assert projects == rows
    session.execute.assert_awaited_once()


async def test_get_user_projects_returns_empty_list_when_user_has_none():
    assert await ProjectService(_list_session([])).get_user_projects(USER_ID) == []


async def test_get_user_projects_filters_by_owner_and_active_status():
    session = _list_session([])

    await ProjectService(session).get_user_projects(USER_ID)

    sql = _sql(session)
    assert f"projects.user_id = '{USER_ID.hex}'" in sql
    assert "projects.deletion_status = 'active'" in sql


async def test_get_user_projects_orders_by_recent_activity_then_creation():
    session = _list_session([])

    await ProjectService(session).get_user_projects(USER_ID)

    order_by = _sql(session).split("ORDER BY")[1]
    assert order_by.split() == [
        "projects.last_activity_at",
        "DESC,",
        "projects.created_at",
        "DESC",
    ]
