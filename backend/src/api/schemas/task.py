from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class TaskUpdate(BaseModel):
    """Request body of PATCH /tasks/{id}. Only sent fields are applied; `title` cannot be null.

    task_number and every other field are not updatable: unknown keys are ignored.
    """

    title: str | None = None
    description: str | None = None

    @field_validator("title")
    @classmethod
    def _title_is_not_null(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("제목은 비워 둘 수 없습니다.")
        return value


class UploadedCodeSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    detected_language: str | None
    complexity_level: str | None
    total_lines: int | None
    total_files: int | None
    upload_size_bytes: int | None


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    task_number: int
    title: str
    description: str | None
    upload_method: str | None
    created_at: datetime
    updated_at: datetime
    uploaded_code: UploadedCodeSummary | None


class TaskListResponse(BaseModel):
    tasks: list[TaskResponse]


class CodeFileResponse(BaseModel):
    """One uploaded file. The server-side storage_path is deliberately not part of it."""

    id: UUID
    file_name: str
    file_path: str | None
    file_extension: str | None
    file_size_bytes: int | None
    language: str
    content: str


class TaskCodeResponse(UploadedCodeSummary):
    task_id: UUID
    files: list[CodeFileResponse]
