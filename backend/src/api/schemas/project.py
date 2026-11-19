from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class ProjectCreate(BaseModel):
    """Request body of POST /projects. Title rules (trim, 1-255 chars) live in ProjectService."""

    title: str
    description: str | None = None


class ProjectUpdate(BaseModel):
    """Request body of PATCH /projects/{id}.

    Only fields that were sent (model_fields_set) are applied: an absent field is kept, and
    `description: null` clears the description. `title` cannot be null.
    """

    title: str | None = None
    description: str | None = None

    @field_validator("title")
    @classmethod
    def _title_is_not_null(cls, value: str | None) -> str:
        # Runs only when title was sent (defaults are not validated).
        if value is None:
            raise ValueError("제목은 비워 둘 수 없습니다.")
        return value


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None
    created_at: datetime
    updated_at: datetime
    last_activity_at: datetime
    # Task does not exist yet, so the counts are fixed at 0. T068 and later replace these with
    # real aggregates (total tasks, completed tasks, completed / total as a percentage).
    task_count: int = 0
    completed_task_count: int = 0
    progress_percent: int = 0


class ProjectListResponse(BaseModel):
    projects: list[ProjectResponse]
