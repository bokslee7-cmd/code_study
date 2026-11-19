import enum
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.exceptions import (
    VALIDATION_ERROR,
    AppError,
    ForbiddenException,
    NotFoundException,
)
from src.models import Project

MAX_TITLE_LENGTH = 255
TRASH_RETENTION_DAYS = 30

INVALID_TITLE_MESSAGE = f"프로젝트 제목은 1자 이상 {MAX_TITLE_LENGTH}자 이하로 입력하세요."
_NOT_FOUND = "요청한 프로젝트를 찾을 수 없습니다."
_NOT_FOUND_HINT = "삭제되었거나 존재하지 않는 프로젝트입니다."
PROJECT_NOT_FOUND_MESSAGE = f"{_NOT_FOUND} {_NOT_FOUND_HINT}"
PROJECT_FORBIDDEN_MESSAGE = "이 프로젝트에 접근할 권한이 없습니다."


class _Unset(enum.Enum):
    UNSET = enum.auto()


UNSET = _Unset.UNSET  # PATCH semantics: "field not sent" differs from "set to null"


def _clean_title(title: str) -> str:
    title = title.strip()
    if not title or len(title) > MAX_TITLE_LENGTH:
        raise AppError(400, VALIDATION_ERROR, INVALID_TITLE_MESSAGE, details={"field": "title"})
    return title


def _clean_description(description: str | None) -> str | None:
    return (description or "").strip() or None


class ProjectService:
    """Writes with flush(); the request-scoped session (get_session) commits or rolls back.

    Callers acting for a user must go through get_owned/update/soft_delete, which check
    ownership; get() is the unchecked lookup. Trashed projects are invisible here and are
    handled by the trash feature (T170+).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, user_id: uuid.UUID, title: str, description: str | None = None
    ) -> Project:
        project = Project(
            user_id=user_id,
            title=_clean_title(title),
            description=_clean_description(description),
        )
        self._session.add(project)
        await self._session.flush()
        await self._session.refresh(project)
        return project

    async def get(self, project_id: uuid.UUID) -> Project | None:
        result = await self._session.execute(
            select(Project).where(
                Project.id == project_id, Project.deletion_status == Project.ACTIVE
            )
        )
        return result.scalar_one_or_none()

    async def get_user_projects(self, user_id: uuid.UUID) -> list[Project]:
        """The user's active projects, most recently active first."""
        result = await self._session.execute(
            select(Project)
            .where(Project.user_id == user_id, Project.deletion_status == Project.ACTIVE)
            .order_by(Project.last_activity_at.desc(), Project.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_owned(self, project_id: uuid.UUID, user_id: uuid.UUID) -> Project:
        """404 if the project is missing or trashed, 403 if it belongs to someone else.

        Existence is checked first so a trashed project never reveals who owned it.
        """
        project = await self.get(project_id)
        if project is None:
            raise NotFoundException(PROJECT_NOT_FOUND_MESSAGE)
        if project.user_id != user_id:
            raise ForbiddenException(PROJECT_FORBIDDEN_MESSAGE)
        return project

    async def update(
        self,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        title: str | _Unset = UNSET,
        description: str | None | _Unset = UNSET,
    ) -> Project:
        project = await self.get_owned(project_id, user_id)
        # Validate before touching the entity so a rejected title leaves nothing half-changed.
        new_title = None if isinstance(title, _Unset) else _clean_title(title)
        if new_title is not None:
            project.title = new_title
        if not isinstance(description, _Unset):
            project.description = _clean_description(description)
        await self._session.flush()
        await self._session.refresh(project)
        return project

    async def soft_delete(self, project_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """Move the project to the trash. Its tasks follow once Task exists (T068)."""
        project = await self.get_owned(project_id, user_id)
        now = datetime.now(UTC)
        project.deletion_status = Project.TRASHED
        project.trashed_at = now
        project.scheduled_deletion_at = now + timedelta(days=TRASH_RETENTION_DAYS)
        await self._session.flush()
