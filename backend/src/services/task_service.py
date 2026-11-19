import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.exceptions import VALIDATION_ERROR, AppError, NotFoundException
from src.models import Project, Task
from src.services.document.document_queue_service import DocumentQueueService
from src.services.project_service import TRASH_RETENTION_DAYS, UNSET, ProjectService, _Unset

logger = logging.getLogger(__name__)

MIN_TITLE_LENGTH = 5
MAX_TITLE_LENGTH = 255
MAX_DESCRIPTION_LENGTH = 500

INVALID_TITLE_MESSAGE = f"태스크 제목은 {MIN_TITLE_LENGTH}자 이상 {MAX_TITLE_LENGTH}자 이하로 입력하세요."  # noqa: E501 (Korean text is double width)
INVALID_DESCRIPTION_MESSAGE = f"태스크 설명은 {MAX_DESCRIPTION_LENGTH}자 이하로 입력하세요."
INVALID_UPLOAD_METHOD_MESSAGE = "업로드 방식은 file, folder, paste 중 하나여야 합니다."
TASK_NOT_FOUND_MESSAGE = (
    "요청한 태스크를 찾을 수 없습니다. 삭제되었거나 존재하지 않는 태스크입니다."  # noqa: E501 (Korean text is double width)
)

__all__ = [
    "MAX_DESCRIPTION_LENGTH",
    "MAX_TITLE_LENGTH",
    "MIN_TITLE_LENGTH",
    "TRASH_RETENTION_DAYS",
    "UNSET",
    "TaskService",
]


def _invalid(field: str, message: str) -> AppError:
    return AppError(400, VALIDATION_ERROR, message, details={"field": field})


def _clean_title(title: str) -> str:
    title = title.strip()
    if not MIN_TITLE_LENGTH <= len(title) <= MAX_TITLE_LENGTH:
        raise _invalid("title", INVALID_TITLE_MESSAGE)
    return title


def _clean_description(description: str | None) -> str | None:
    description = (description or "").strip() or None
    if description is not None and len(description) > MAX_DESCRIPTION_LENGTH:
        raise _invalid("description", INVALID_DESCRIPTION_MESSAGE)
    return description


def _clean_upload_method(upload_method: str | None) -> str | None:
    if upload_method is not None and upload_method not in Task.UPLOAD_METHODS:
        raise _invalid("upload_method", INVALID_UPLOAD_METHOD_MESSAGE)
    return upload_method


class TaskService:
    """Writes with flush(); the request-scoped session (get_session) commits or rolls back.

    Every method takes the acting user and checks ownership through the task's project, so a
    task of a trashed project is as invisible as a trashed task (see ProjectService.get_owned).
    """

    def __init__(
        self, session: AsyncSession, document_queue: DocumentQueueService | None = None
    ) -> None:
        self._session = session
        self._projects = ProjectService(session)
        self._documents = document_queue or DocumentQueueService(session)

    async def create(
        self,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        title: str,
        description: str | None = None,
        upload_method: str | None = None,
    ) -> Task:
        project = await self._projects.get_owned(project_id, user_id)
        task = Task(
            project_id=project_id,
            title=_clean_title(title),
            description=_clean_description(description),
            upload_method=_clean_upload_method(upload_method),
        )
        # Row lock: two concurrent creates in one project must not read the same highest number.
        await self._session.refresh(project, with_for_update=True)
        # Trashed tasks count too: numbers are immutable and never reused (FR-004).
        highest = await self._session.execute(
            select(func.coalesce(func.max(Task.task_number), 0)).where(
                Task.project_id == project_id
            )
        )
        task.task_number = highest.scalar_one() + 1
        project.last_activity_at = datetime.now(UTC)
        self._session.add(task)
        await self._session.flush()
        await self._session.refresh(task, ["created_at", "updated_at"])
        return task

    async def start_document_generation(self, task: Task) -> None:
        """Queue the learning document right after the task's code was stored (T096).

        The code is already saved, so a queue/Redis problem must not fail the upload: it is
        logged here (the queue service itself marks the document `failed` when dispatching
        breaks, so the user sees it and can retry instead of waiting forever).
        """
        try:
            await self._documents.enqueue(task.id)
        except Exception:
            logger.exception("문서 생성 시작 실패 task_id=%s", task.id)

    async def list_for_project(self, project_id: uuid.UUID, user_id: uuid.UUID) -> list[Task]:
        """The project's active tasks in task-number order (FR-003)."""
        await self._projects.get_owned(project_id, user_id)
        result = await self._session.execute(
            select(Task)
            .options(selectinload(Task.uploaded_code))
            .where(Task.project_id == project_id, Task.deletion_status == Task.ACTIVE)
            .order_by(Task.task_number.asc())
        )
        return list(result.scalars().all())

    async def get_owned(self, task_id: uuid.UUID, user_id: uuid.UUID) -> Task:
        """404 if the task (or its project) is missing or trashed, 403 if not the user's."""
        task, _ = await self._get_with_project(task_id, user_id)
        return task

    async def _get_with_project(
        self, task_id: uuid.UUID, user_id: uuid.UUID
    ) -> tuple[Task, Project]:
        result = await self._session.execute(
            select(Task)
            .options(selectinload(Task.uploaded_code))
            .where(Task.id == task_id, Task.deletion_status == Task.ACTIVE)
        )
        task = result.scalar_one_or_none()
        if task is None:
            raise NotFoundException(TASK_NOT_FOUND_MESSAGE)
        return task, await self._projects.get_owned(task.project_id, user_id)

    async def update(
        self,
        task_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        title: str | _Unset = UNSET,
        description: str | None | _Unset = UNSET,
    ) -> Task:
        task, project = await self._get_with_project(task_id, user_id)
        # Validate everything before touching the entity so a rejected field changes nothing.
        new_title = None if isinstance(title, _Unset) else _clean_title(title)
        new_description = (
            None if isinstance(description, _Unset) else _clean_description(description)
        )
        if new_title is not None:
            task.title = new_title
        if not isinstance(description, _Unset):
            task.description = new_description
        project.last_activity_at = datetime.now(UTC)
        await self._session.flush()
        await self._session.refresh(task, ["updated_at"])
        return task

    async def soft_delete(self, task_id: uuid.UUID, user_id: uuid.UUID) -> None:
        task, project = await self._get_with_project(task_id, user_id)
        now = datetime.now(UTC)
        task.deletion_status = Task.TRASHED
        task.trashed_at = now
        task.scheduled_deletion_at = now + timedelta(days=TRASH_RETENTION_DAYS)
        project.last_activity_at = now
        await self._session.flush()
