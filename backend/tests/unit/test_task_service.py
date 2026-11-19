import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from src.api.exceptions import AppError, ForbiddenException, NotFoundException
from src.models import Project, Task
from src.services.task_service import (
    MAX_DESCRIPTION_LENGTH,
    MAX_TITLE_LENGTH,
    MIN_TITLE_LENGTH,
    TRASH_RETENTION_DAYS,
    TaskService,
)

USER_ID = uuid.uuid4()
PROJECT_ID = uuid.uuid4()


def _result(*, one_or_none: object | None = None, one: object = 0, many: list | None = None):
    result = MagicMock()
    result.scalar_one_or_none.return_value = one_or_none
    result.scalar_one.return_value = one
    result.scalars.return_value.all.return_value = many or []
    return result


def _session(*results: MagicMock) -> MagicMock:
    """Async session double; each execute() returns the next result (the last one repeats)."""
    session = MagicMock()
    queue = list(results)
    session.execute = AsyncMock(side_effect=lambda *_: queue.pop(0) if len(queue) > 1 else queue[0])
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    return session


def _sql(session: MagicMock, call: int = -1) -> str:
    statement = session.execute.call_args_list[call].args[0]
    return str(statement.compile(compile_kwargs={"literal_binds": True}))


def _project(**overrides: object) -> Project:
    values: dict[str, object] = {
        "id": PROJECT_ID,
        "user_id": USER_ID,
        "title": "내 프로젝트",
        "deletion_status": Project.ACTIVE,
    }
    values.update(overrides)
    return Project(**values)


def _task(**overrides: object) -> Task:
    values: dict[str, object] = {
        "id": uuid.uuid4(),
        "project_id": PROJECT_ID,
        "task_number": 1,
        "title": "첫 번째 태스크",
        "description": "설명",
        "upload_method": "file",
        "deletion_status": Task.ACTIVE,
    }
    values.update(overrides)
    return Task(**values)


def _create_session(last_number: int = 0, project: Project | None = None) -> MagicMock:
    """Session for create(): 1st query = owned project, 2nd = highest task_number so far."""
    return _session(
        _result(one_or_none=project or _project()),
        _result(one=last_number),
    )


def test_constants_follow_the_data_model():
    assert MIN_TITLE_LENGTH == 5  # FR-008
    assert MAX_TITLE_LENGTH == 255  # tasks.title is VARCHAR(255)
    assert MAX_DESCRIPTION_LENGTH == 500  # FR-009
    assert TRASH_RETENTION_DAYS == 30


# ---------------------------------------------------------------- create


async def test_create_saves_task_with_the_given_fields():
    session = _create_session()
    task = await TaskService(session).create(
        USER_ID, PROJECT_ID, "할 일 앱 분석", "설명", upload_method="paste"
    )

    session.add.assert_called_once_with(task)
    assert task.project_id == PROJECT_ID
    assert task.title == "할 일 앱 분석"
    assert task.description == "설명"
    assert task.upload_method == "paste"
    session.flush.assert_awaited_once()


async def test_create_numbers_the_first_task_one():
    service = TaskService(_create_session(last_number=0))
    task = await service.create(USER_ID, PROJECT_ID, "첫 번째 태스크")

    assert task.task_number == 1


async def test_create_numbers_the_next_task_after_the_highest_existing_one():
    task = await TaskService(_create_session(last_number=7)).create(
        USER_ID, PROJECT_ID, "여덟 번째 태스크"
    )

    assert task.task_number == 8


async def test_create_counts_trashed_tasks_so_numbers_are_never_reused():
    session = _create_session()
    await TaskService(session).create(USER_ID, PROJECT_ID, "첫 번째 태스크")

    sql = _sql(session)  # the max(task_number) query
    assert "max(tasks.task_number)" in sql
    assert "deletion_status" not in sql


async def test_create_locks_the_project_row_to_serialize_numbering():
    project = _project()
    session = _create_session(project=project)
    await TaskService(session).create(USER_ID, PROJECT_ID, "첫 번째 태스크")

    session.refresh.assert_any_await(project, with_for_update=True)


async def test_create_reloads_server_generated_timestamps():
    session = _create_session()
    task = await TaskService(session).create(USER_ID, PROJECT_ID, "첫 번째 태스크")

    session.refresh.assert_any_await(task, ["created_at", "updated_at"])


async def test_create_touches_project_activity():
    project = _project(last_activity_at=datetime(2026, 1, 1, tzinfo=UTC))
    service = TaskService(_create_session(project=project))
    await service.create(USER_ID, PROJECT_ID, "첫 번째 태스크")

    assert project.last_activity_at > datetime(2026, 11, 1, tzinfo=UTC)


async def test_create_strips_title_and_turns_blank_description_into_none():
    service = TaskService(_create_session())
    task = await service.create(USER_ID, PROJECT_ID, "  첫 번째 태스크  ", "   ")

    assert task.title == "첫 번째 태스크"
    assert task.description is None


async def test_create_upload_method_is_optional():
    task = await TaskService(_create_session()).create(USER_ID, PROJECT_ID, "첫 번째 태스크")

    assert task.upload_method is None


@pytest.mark.parametrize("title", ["", "    ", "1234", " 1234 ", "가" * (MAX_TITLE_LENGTH + 1)])
async def test_create_rejects_invalid_title(title: str):
    session = _create_session()

    with pytest.raises(AppError) as error:
        await TaskService(session).create(USER_ID, PROJECT_ID, title)

    assert error.value.status_code == 400
    assert error.value.details == {"field": "title"}
    session.add.assert_not_called()


async def test_create_accepts_title_at_both_length_limits():
    shortest = await TaskService(_create_session()).create(
        USER_ID, PROJECT_ID, "가" * MIN_TITLE_LENGTH
    )
    longest = await TaskService(_create_session()).create(
        USER_ID, PROJECT_ID, "가" * MAX_TITLE_LENGTH
    )

    assert len(shortest.title) == MIN_TITLE_LENGTH
    assert len(longest.title) == MAX_TITLE_LENGTH


async def test_create_rejects_too_long_description():
    with pytest.raises(AppError) as error:
        await TaskService(_create_session()).create(
            USER_ID, PROJECT_ID, "첫 번째 태스크", "가" * (MAX_DESCRIPTION_LENGTH + 1)
        )

    assert error.value.status_code == 400
    assert error.value.details == {"field": "description"}


async def test_create_accepts_description_at_the_limit():
    task = await TaskService(_create_session()).create(
        USER_ID, PROJECT_ID, "첫 번째 태스크", "가" * MAX_DESCRIPTION_LENGTH
    )

    assert task.description is not None


async def test_create_rejects_unknown_upload_method():
    with pytest.raises(AppError) as error:
        await TaskService(_create_session()).create(
            USER_ID, PROJECT_ID, "첫 번째 태스크", upload_method="zip"
        )

    assert error.value.status_code == 400
    assert error.value.details == {"field": "upload_method"}


async def test_create_in_missing_project_is_not_found():
    session = _session(_result(one_or_none=None))

    with pytest.raises(NotFoundException):
        await TaskService(session).create(USER_ID, PROJECT_ID, "첫 번째 태스크")

    session.add.assert_not_called()


async def test_create_in_someone_elses_project_is_forbidden():
    session = _session(_result(one_or_none=_project(user_id=uuid.uuid4())))

    with pytest.raises(ForbiddenException):
        await TaskService(session).create(USER_ID, PROJECT_ID, "첫 번째 태스크")

    session.add.assert_not_called()


# ---------------------------------------------------------------- list


async def test_list_returns_active_tasks_in_task_number_order():
    tasks = [_task(task_number=1), _task(task_number=2)]
    session = _session(_result(one_or_none=_project()), _result(many=tasks))

    result = await TaskService(session).list_for_project(PROJECT_ID, USER_ID)

    assert result == tasks
    sql = _sql(session)
    assert "tasks.project_id = '" + str(PROJECT_ID).replace("-", "") in sql.replace("-", "")
    assert "deletion_status = 'active'" in sql
    assert "ORDER BY tasks.task_number ASC" in sql


async def test_list_checks_project_ownership():
    session = _session(_result(one_or_none=_project(user_id=uuid.uuid4())))

    with pytest.raises(ForbiddenException):
        await TaskService(session).list_for_project(PROJECT_ID, USER_ID)


async def test_list_of_missing_project_is_not_found():
    with pytest.raises(NotFoundException):
        await TaskService(_session(_result(one_or_none=None))).list_for_project(PROJECT_ID, USER_ID)


# ---------------------------------------------------------------- get_owned


async def test_get_owned_returns_the_task_with_its_upload_summary():
    task = _task()
    session = _session(_result(one_or_none=task), _result(one_or_none=_project()))

    assert await TaskService(session).get_owned(task.id, USER_ID) is task
    statement = session.execute.call_args_list[0].args[0]
    assert "deletion_status = 'active'" in _sql(session, 0)  # trashed tasks are invisible
    assert statement._with_options  # upload summary is eager-loaded for the response


async def test_get_owned_unknown_or_trashed_task_is_not_found():
    with pytest.raises(NotFoundException):
        await TaskService(_session(_result(one_or_none=None))).get_owned(uuid.uuid4(), USER_ID)


async def test_get_owned_task_of_someone_elses_project_is_forbidden():
    session = _session(
        _result(one_or_none=_task()), _result(one_or_none=_project(user_id=uuid.uuid4()))
    )

    with pytest.raises(ForbiddenException):
        await TaskService(session).get_owned(uuid.uuid4(), USER_ID)


async def test_get_owned_task_of_a_trashed_project_is_not_found():
    session = _session(_result(one_or_none=_task()), _result(one_or_none=None))

    with pytest.raises(NotFoundException):
        await TaskService(session).get_owned(uuid.uuid4(), USER_ID)


# ---------------------------------------------------------------- update


def _owned(task: Task) -> MagicMock:
    return _session(_result(one_or_none=task), _result(one_or_none=_project()))


async def test_update_changes_title_and_description():
    task = _task()
    session = _owned(task)

    updated = await TaskService(session).update(
        task.id, USER_ID, title="  새 제목입니다 ", description=" 새 설명 "
    )

    assert updated.title == "새 제목입니다"
    assert updated.description == "새 설명"
    session.flush.assert_awaited_once()
    session.refresh.assert_awaited_once_with(task, ["updated_at"])  # onupdate value, async-safe


async def test_update_keeps_fields_that_were_not_sent():
    task = _task(title="원래 제목입니다", description="원래 설명")

    await TaskService(_owned(task)).update(task.id, USER_ID, title="바뀐 제목입니다")

    assert task.description == "원래 설명"


async def test_update_can_clear_the_description_with_none():
    task = _task(description="원래 설명")

    await TaskService(_owned(task)).update(task.id, USER_ID, description=None)

    assert task.description is None
    assert task.title == "첫 번째 태스크"


async def test_update_never_changes_the_task_number():
    task = _task(task_number=4)

    await TaskService(_owned(task)).update(task.id, USER_ID, title="바뀐 제목입니다")

    assert task.task_number == 4


async def test_update_with_invalid_title_leaves_the_task_untouched():
    task = _task(title="원래 제목입니다", description="원래 설명")

    with pytest.raises(AppError) as error:
        service = TaskService(_owned(task))
        await service.update(task.id, USER_ID, title="짧음", description="새 설명")

    assert error.value.details == {"field": "title"}
    assert task.title == "원래 제목입니다"
    assert task.description == "원래 설명"


async def test_update_rejects_too_long_description():
    task = _task()

    with pytest.raises(AppError) as error:
        await TaskService(_owned(task)).update(
            task.id, USER_ID, description="가" * (MAX_DESCRIPTION_LENGTH + 1)
        )

    assert error.value.details == {"field": "description"}


async def test_update_of_someone_elses_task_is_forbidden():
    session = _session(
        _result(one_or_none=_task()), _result(one_or_none=_project(user_id=uuid.uuid4()))
    )

    with pytest.raises(ForbiddenException):
        await TaskService(session).update(uuid.uuid4(), USER_ID, title="바뀐 제목입니다")


# ---------------------------------------------------------------- soft delete


async def test_soft_delete_moves_the_task_to_trash_for_30_days():
    task = _task()
    session = _owned(task)
    before = datetime.now(UTC)

    await TaskService(session).soft_delete(task.id, USER_ID)

    assert task.deletion_status == Task.TRASHED
    assert task.trashed_at is not None and task.trashed_at >= before
    assert task.scheduled_deletion_at == task.trashed_at + timedelta(days=30)
    session.flush.assert_awaited_once()


async def test_soft_delete_of_someone_elses_task_is_forbidden():
    task = _task()
    session = _session(
        _result(one_or_none=task), _result(one_or_none=_project(user_id=uuid.uuid4()))
    )

    with pytest.raises(ForbiddenException):
        await TaskService(session).soft_delete(task.id, USER_ID)

    assert task.deletion_status == Task.ACTIVE


async def test_soft_delete_of_unknown_task_is_not_found():
    with pytest.raises(NotFoundException):
        await TaskService(_session(_result(one_or_none=None))).soft_delete(uuid.uuid4(), USER_ID)


# ------------------------------------------------------- document generation trigger (T096)


async def test_start_document_generation_enqueues_the_task_after_the_upload():
    queue = MagicMock()
    queue.enqueue = AsyncMock()
    task = _task()

    await TaskService(_session(), document_queue=queue).start_document_generation(task)

    queue.enqueue.assert_awaited_once_with(task.id)


async def test_start_document_generation_never_fails_the_upload_when_queueing_breaks():
    queue = MagicMock()
    queue.enqueue = AsyncMock(side_effect=ConnectionError("redis down"))

    # Must not raise: the code is already stored, only the document is delayed.
    await TaskService(_session(), document_queue=queue).start_document_generation(_task())

    queue.enqueue.assert_awaited_once()


def test_task_service_builds_its_own_queue_when_none_is_given():
    from src.services.document.document_queue_service import DocumentQueueService

    service = TaskService(_session())

    assert isinstance(service._documents, DocumentQueueService)
